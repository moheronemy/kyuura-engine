"""対戦の進行（公式ルール 2000.02.14版）。

使い方::

    state = new_game(deck0, deck1, seed=1)
    state = apply_command(state, PlaceStartingPokemon(player=0, active=..., bench=(...)))
    ...

- ``apply_command`` は渡された状態を変えず、新しい状態を返します。操作が不正なら例外を投げ、
  渡した状態はそのまま使えます。
- ``new_game`` と ``apply_command`` は、返す状態を必ず ``check_invariants`` で確かめます。
  カードの保存則などが破れていたら、状態を返さずに ``StateIntegrityError`` を投げます。
- 乱数（山札を切る・コインを投げる（v0.2d））は ``seed`` から作った乱数だけを使います。同じデッキ・
  同じ seed・同じ操作の列なら、同じ結果になります。コインの結果を操作で指定する方法はありません。
- ジャンケンの結果は外から受け取ります（``ReportJankenResult``）。

ページ番号は『ポケモンカードオフィシャルブック2000』[P43] の公式ルールのノンブルです。
"""

from __future__ import annotations

import random
from typing import Callable, Sequence

from .cards import EVOLUTION_STAGES, CardPool, load_card_pool
from .conditions import (
    RETREAT,
    clear_special_conditions,
    paralysis_recovery_turn,
)
from .commands import (
    UNSUPPORTED_COMMANDS,
    check_command_fields,
    AttachEnergy,
    DrawMulliganCards,
    EndTurn,
    EvolvePokemon,
    PlaceStartingPokemon,
    PlayBasicToBench,
    PlayTrainer,
    PromoteActive,
    ReportJankenResult,
    ResolveDecision,
    Retreat,
    TakePrize,
    UseAttack,
    UsePokemonPower,
)
from .decisions import (
    DECISION_PHASES,
    KO_PREVENTION,
    POST_KNOCKOUT_POWER,
    PROMOTE_ACTIVE,
    TAKE_PRIZE,
    phase_for,
)
from .effects import (
    AttackKey,
    AttackUse,
    PowerKey,
    PowerUse,
    ReturnToHandOnKnockOut,
    TrainerUse,
    after_energy_attached,
    ko_prevention_power,
    ko_prevention_suppressors,
)
from .continuous import suppressors_of
from .deck import deck_problems
from .evolution import place_evolution_card, skipped_stage1_basic
from .errors import DeckValidationError, IllegalActionError, StateIntegrityError, UnsupportedError
from .persistent import KNOCK_OUT, remove_persistent_effects
from .rules import RULES_2000_02_14, RuleSet
from .state import (
    PERSISTENT_EFFECT_TYPES,
    DamageReduction,
    NextTurnAttackDamage,
    Retaliation,
    TERMINAL_PHASES,
    Asleep,
    CardInstance,
    Confused,
    DataSource,
    GameState,
    Halt,
    Paralyzed,
    Phase,
    PlayerState,
    PokemonInPlay,
    Poison,
    SpecialConditions,
    TrainerInUse,
    freeze_mapping,
    turn_owner,
)
from .zones import attach_energy_from_hand, draw_cards, shuffle_deck

# v0.15a: v0.13 まで engine.py にあった確認と共通の手続きを、engine.py を読み込まない部品に移した（docs/integration-dependencies-v0.15a.md）。
# 範囲外のコマンドの処理が使う名前を、v0.13 の名前で読み込む（v0.16b でワザ・番の終わりの処理は解決の基盤だけになった）
from .checks import PLAYERS, decision_choices
from .checks import require_not_asleep_or_paralyzed as _require_not_asleep_or_paralyzed
from .checks import require_phase as _require_phase
from .checks import require_player as _require_player
from .checks import require_turn as _require_turn
from .procedures import NEXT_TURN
from .procedures import begin_turn as _begin_turn
from .procedures import confusion_check as _confusion_check
from . import resolution  # v0.15b: 効果の解決の基盤（engine.py を読み込まない）

# PLAYERS（checks）・NEXT_TURN（procedures）は v0.15a で共通の部品に移した（上で読み込む。engine.PLAYERS・engine.NEXT_TURN のまま使える）
# 決定の再開先（v0.16b: 解決の基盤が続ける 5 つと、engine.py が続けるトレーナーの決定）
DECISION_RESUMES = resolution.RESUMES | {"trainer"}
# 対戦準備の段階（番はまだ始まっていない）
SETUP_PHASES = frozenset({Phase.SETUP_PLACEMENT, Phase.SETUP_MULLIGAN_DRAW, Phase.SETUP_FIRST_PLAYER})


# ---------------------------------------------------------------- 対戦の開始


def new_game(
    deck0: Sequence[str],
    deck1: Sequence[str],
    seed: int,
    *,
    rules: RuleSet = RULES_2000_02_14,
    pool: CardPool | None = None,
) -> GameState:
    """デッキを検査し、山札を切り、手札を 7 枚ずつ配り、切り直しまで済ませた状態を返す（p.308）。

    この後は ``PlaceStartingPokemon`` で両方のプレイヤーがポケモンを出す。
    ``seed`` は 0 以上の整数。切り直しの補償が原文で決められない場合は、``Phase.HALTED`` の状態を返す
    （例外は投げない。``state.phase`` を確かめること）。
    """
    pool = pool or load_card_pool()
    problems = [f"player {p}: {problem}" for p, deck in enumerate((deck0, deck1)) for problem in deck_problems(deck, pool, rules)]
    if problems:
        raise DeckValidationError(problems)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed は整数")
    if seed < 0:
        # random.Random は負の seed を絶対値として扱うので、-5 と 5 が同じ対戦になってしまう
        raise ValueError("seed は 0 以上の整数")

    cards: dict[int, CardInstance] = {}
    players = []
    for owner, deck in enumerate((deck0, deck1)):
        uids = []
        for card_id in deck:
            uid = len(cards)
            cards[uid] = CardInstance(uid=uid, card_id=card_id, owner=owner)
            uids.append(uid)
        players.append(PlayerState(deck=uids))

    used_ids = {c.card_id for c in cards.values()}
    state = GameState(
        rules=rules,
        card_data=DataSource(pool.source["repository"], pool.source["commit"], pool.source["path"]),
        seed=seed,
        rng=random.Random(seed),
        cards=freeze_mapping(cards),
        definitions=freeze_mapping({card_id: pool.get(card_id) for card_id in used_ids}),
        decklists=(tuple(deck0), tuple(deck1)),
        players=players,
        phase=Phase.SETUP_PLACEMENT,
        effects=pool.effects,
    )
    state.add_event("game_created", rules=rules.id, seed=seed, card_data_commit=pool.source["commit"])

    # デッキを切る（自分で切り、相手にも切ってもらう。その結果を乱数 1 回の並べ替えで表す）
    for player in PLAYERS:
        _shuffle_deck(state, player)
    _deal_opening_hands(state)
    _require_integrity(state)
    return state


def _shuffle_deck(state: GameState, player: int) -> None:
    shuffle_deck(state, player)  # v0.22 から zones（カードの効果で切る処理と共通。動き・乱数・ログは同じ）


def _draw(state: GameState, player: int, count: int) -> None:
    draw_cards(state, player, count)


def _hand_has_basic(state: GameState, player: int) -> bool:
    return any(state.card_def(uid).is_basic_pokemon for uid in state.players[player].hand)


def _deal_opening_hands(state: GameState) -> None:
    """手札 7 枚と切り直し（p.308「カードを7枚取る」）。

    - たねポケモンがなかったプレイヤーだけが、手札を見せて切り直す。来るまでくりかえす。
    - 相手は切り直し 1 回ごとに最大 2 枚引ける（サイドを置いた後。``DrawMulliganCards``）。
    - 両方ともたねポケモンがなかった場合は、どちらも引かない。

    両方が同時に切り直したあと、片方だけがさらに切り直した場合（回数が違う場合）に、相手が
    何枚引けるかは原文から決められない（kyuura docs/engine-readiness.md 4章）。その場合は
    推測で決めずに対戦を止める（Phase.HALTED）。
    """
    size = state.rules.opening_hand_size
    dealing = list(PLAYERS)
    for player in dealing:
        _draw(state, player, size)
    rounds: list[tuple[int, ...]] = []
    while True:
        lacking = tuple(p for p in dealing if not _hand_has_basic(state, p))
        if not lacking:
            break
        rounds.append(lacking)
        for player in lacking:
            p = state.players[player]
            p.mulligans += 1
            state.add_event("mulligan", player=player, revealed_hand=tuple(p.hand))
            p.deck.extend(p.hand)
            p.hand.clear()
            _shuffle_deck(state, player)
            _draw(state, player, size)
        dealing = list(lacking)
    state.mulligan_rounds = tuple(rounds)

    both_rounds = [r for r in rounds if len(r) == 2]
    single_rounds = [r for r in rounds if len(r) == 1]
    if both_rounds and single_rounds:
        state.phase = Phase.HALTED
        state.halt = Halt(
            code="UNRESOLVED_MULLIGAN_COMPENSATION",
            message=(
                "両方のプレイヤーが同時に切り直したあと、片方だけがさらに切り直した。"
                "この場合に相手が何枚引けるかは公式ルール 2000.02.14版の文面（p.308）から決められないので、v0.1 では対戦を止める。"
            ),
            references=("P43 p.308", "NEO-2000-OFFICIAL-RULES", "mulligan", "kyuura docs/engine-readiness.md 4章"),
        )
        state.add_event("halted", code=state.halt.code, mulligan_rounds=state.mulligan_rounds)
        return
    for (player,) in single_rounds:
        state.players[1 - player].mulligan_draws_remaining += 1


# ---------------------------------------------------------------- コマンドの入口


def apply_command(state: GameState, command) -> GameState:
    """コマンドを処理した新しい状態を返す。渡した ``state`` は変えない。

    - ルール上できない操作: ``IllegalActionError``
    - 未対応の操作・原典で決められない場合・終わった（止めた）対戦への操作: ``UnsupportedError`` /
      ``IllegalActionError``（GAME_OVER）
    - 処理の結果が不変条件を満たさない（エンジンの不具合か、渡した状態が壊れている）: ``StateIntegrityError``

    v0.16b: ワザ・番の終わり・きぜつのあとの決定は、効果の解決の基盤（``kyuura_engine/resolution``）だけが処理する（v0.13 の経路と、
    経路を選ぶ ``Route``・``apply_command_via`` は外した。docs/kernel-consolidation-v0.16b.md）。呼び方・戻り値・例外は変えていない。
    """
    return _apply(state, command, None)


def apply_command_with(state: GameState, command, *, preflight: str = "derived",
                       catalog: resolution.Catalog | None = None) -> GameState:
    """内部の入口（v0.16b。v0.15b の ``apply_command_via`` の、経路の引数のない形）: 解決の設定（宣言の前の先読みの方法 ``preflight``・
    効果の定義の対応表 ``catalog``）を指定してコマンドを処理する。比較・試験用。公開の ``apply_command`` と同じ約束（渡した状態を変えない・
    不変条件で確かめる）。"""
    return _apply(state, command, _context(state, preflight, catalog))


def apply_command_traced(state: GameState, command, *, preflight: str = "derived",
                         catalog: resolution.Catalog | None = None) -> tuple[GameState, resolution.Trace]:
    """内部の入口（v0.15b）: (新しい状態, 解決の記録) を返す。解決の記録（内部のトレース）は状態に保存しない（公開のログとは別のもの）。
    解決の基盤を通らないコマンド（範囲外のコマンド・トレーナーの決定への答え）なら、解決の記録は空。"""
    context = _context(state, preflight, catalog)
    return _apply(state, command, context), context.trace


def _context(state: GameState, preflight: str, catalog: resolution.Catalog | None) -> resolution.Context:
    """解決の設定（コマンドごとに作る。解決の記録はこの中に入る。``state`` はコマンドの入口に渡された状態で、変えない）。"""
    return resolution.Context(original=state, preflight=preflight, catalog=resolution.DEFAULT_CATALOG if catalog is None else catalog)


def _apply(state: GameState, command, context: resolution.Context | None) -> GameState:
    """コマンドの入口（確認・複製・不変条件）。ワザ・番の終わりは解決の基盤（``resolution.handle``）、決定への答えは ``_answer_decision``、
    範囲外のコマンドは ``engine.py`` の処理（``_HANDLERS``）。"""
    if isinstance(command, UNSUPPORTED_COMMANDS):
        raise UnsupportedError("UNSUPPORTED_ACTION", f"{type(command).__name__} は未対応")
    handler = _HANDLERS.get(type(command))
    if handler is None:
        raise IllegalActionError("UNKNOWN_COMMAND", f"知らないコマンド {command!r}")
    check_command_fields(command)
    if state.phase is Phase.GAME_OVER:
        raise IllegalActionError("GAME_OVER", "対戦は終わっている")
    if state.phase is Phase.SUDDEN_DEATH:
        raise UnsupportedError("SUDDEN_DEATH_NOT_IMPLEMENTED", "サドン・デス（延長戦）の開始は v0.1 では未実装")
    if state.phase is Phase.HALTED:
        raise UnsupportedError(state.halt.code, state.halt.message)
    new = state.clone()
    handler(new, command, context if context is not None else _context(state, "derived", None))
    _require_integrity(new)
    return new


def _require_integrity(state: GameState) -> None:
    """返す状態がカードの保存則・場の形を満たすことを確かめる。満たさなければ返さない。"""
    problems = check_invariants(state)
    if problems:
        raise StateIntegrityError(problems)


def _require_in_hand(state: GameState, player: int, uid) -> None:
    if uid not in state.players[player].hand:
        raise IllegalActionError("CARD_NOT_IN_HAND", f"カード {uid!r} はプレイヤー {player} の手札にない")


# ---------------------------------------------------------------- 対戦準備


def _place_starting_pokemon(state: GameState, cmd: PlaceStartingPokemon) -> None:
    """手札からバトル場に 1 枚、ベンチに最大 5 枚（p.308「ポケモンを場に出す」）。"""
    _require_phase(state, Phase.SETUP_PLACEMENT)
    player = _require_player(cmd.player)
    p = state.players[player]
    if p.placed_starting_pokemon:
        raise IllegalActionError("ALREADY_PLACED", "対戦準備のポケモンはもう出している")
    chosen = (cmd.active, *cmd.bench)
    if len(set(chosen)) != len(chosen):
        raise IllegalActionError("DUPLICATE_CARD", "同じカードを 2 回選んでいる")
    if len(cmd.bench) > state.rules.max_setup_bench:
        raise IllegalActionError("SETUP_BENCH_LIMIT", f"対戦準備でベンチに出せるのは {state.rules.max_setup_bench} 枚まで")
    for uid in chosen:
        _require_in_hand(state, player, uid)
        if not state.card_def(uid).is_basic_pokemon:
            raise IllegalActionError("NOT_BASIC_POKEMON", f"カード {uid} はたねポケモンではない")
    for uid in chosen:
        p.hand.remove(uid)
    p.active = _enter_play(state, cmd.active)
    p.bench = [_enter_play(state, uid) for uid in cmd.bench]
    p.placed_starting_pokemon = True
    state.add_event("place_starting_pokemon", player=player, active=cmd.active, bench=tuple(cmd.bench))

    if all(q.placed_starting_pokemon for q in state.players):
        # サイドカードをセットする: 山札の一番上から裏のまま 6 枚（p.308）
        for pl in PLAYERS:
            q = state.players[pl]
            q.prizes = q.deck[: state.rules.prize_count]
            del q.deck[: state.rules.prize_count]
            state.add_event("set_prizes", player=pl, count=len(q.prizes))
        _after_prizes(state)


def _enter_play(state: GameState, uid: int) -> PokemonInPlay:
    """カードを場のポケモンにする。場のポケモンの番号を新しく付ける（前に使った番号は使わない）。

    場に出た番（``played_turn``。対戦準備なら 0）を記録する。今の番に場に出したポケモンは、その番には進化できない
    （「その番の最初」には場にいなかった。p.310。v0.4a）。
    """
    pokemon = PokemonInPlay(uid, pokemon_id=state.next_pokemon_id, played_turn=state.turn_number)
    state.next_pokemon_id += 1
    return pokemon


def _after_prizes(state: GameState) -> None:
    if any(p.mulligan_draws_remaining for p in state.players):
        state.phase = Phase.SETUP_MULLIGAN_DRAW
    else:
        state.phase = Phase.SETUP_FIRST_PLAYER


def _draw_mulligan_cards(state: GameState, cmd: DrawMulliganCards) -> None:
    """相手の切り直し 1 回ぶん、山札から最大 2 枚（1 枚・0 枚でもよい）引く（p.308）。"""
    _require_phase(state, Phase.SETUP_MULLIGAN_DRAW)
    player = _require_player(cmd.player)
    p = state.players[player]
    if p.mulligan_draws_remaining <= 0:
        raise IllegalActionError("NO_MULLIGAN_DRAW", "相手の切り直しのぶんの引く権利がない")
    limit = state.rules.mulligan_draw_max_per_mulligan
    if not 0 <= cmd.count <= limit:
        raise IllegalActionError("INVALID_DRAW_COUNT", f"引けるのは 0〜{limit} 枚")
    if cmd.count > len(p.deck):
        raise IllegalActionError("INVALID_DRAW_COUNT", "山札の枚数より多くは引けない")
    _draw(state, player, cmd.count)
    p.mulligan_draws_remaining -= 1
    state.add_event("mulligan_draw", player=player, count=cmd.count)
    if not any(q.mulligan_draws_remaining for q in state.players):
        state.phase = Phase.SETUP_FIRST_PLAYER


def _report_janken_result(state: GameState, cmd: ReportJankenResult) -> None:
    """ジャンケンに勝った人が先攻（p.308）。場のポケモンを表にしたら先攻の番が始まる（p.309）。"""
    _require_phase(state, Phase.SETUP_FIRST_PLAYER)
    winner = _require_player(cmd.winner)
    state.first_player = winner
    state.add_event("janken", winner=winner, first_player=winner)
    state.add_event("reveal_pokemon")
    _begin_turn(state, winner)


# ---------------------------------------------------------------- 番の進行


def _play_basic_to_bench(state: GameState, cmd: PlayBasicToBench) -> None:
    """手札のたねポケモンをベンチに出す。ベンチは 5 匹まで。1 番に出す数の制限はない（p.309）。"""
    p = _require_turn(state, cmd.player)
    _require_in_hand(state, cmd.player, cmd.card)
    if not state.card_def(cmd.card).is_basic_pokemon:
        raise IllegalActionError("NOT_BASIC_POKEMON", f"カード {cmd.card} はたねポケモンではない")
    if len(p.bench) >= state.rules.max_bench:
        raise IllegalActionError("BENCH_FULL", f"ベンチは {state.rules.max_bench} 匹まで")
    p.hand.remove(cmd.card)
    p.bench.append(_enter_play(state, cmd.card))
    state.add_event("play_to_bench", player=cmd.player, card=cmd.card)


def _evolve_pokemon(state: GameState, cmd: EvolvePokemon) -> None:
    """手札の進化カードを、自分の場のポケモンに重ねて進化させる（p.309「場にいるポケモンを進化させる」・p.310。v0.4a）。

    v0.4a は、たねポケモン → 1 進化ポケモン。v0.4c で、1 進化ポケモン → 2 進化ポケモンも同じコマンド・同じ手順で
    扱う（p.319「場にいる「たねポケモン」または「進化ポケモン」に進化カードを重ねて進化させたとき」。重なりは 3 枚まで）。
    確かめること（どれも状態を変える前。拒否しても状態も乱数も変わらない）:

    - 自分の番（MAIN）。決定を待つ間（トレーナーの途中を含む）は進化させられない（p.310「進化させている最中は…」の
      裏返しで、ほかのことの最中にも進化はできない。``_require_turn``）
    - ``cmd.card`` が手札にあり、進化カード（``NOT_EVOLUTION_CARD``）。対応していない進化カード（ベイビィ・登録のない
      ワザやポケモンパワーを持つカード。2 進化の段階だからといって対応にはしない）は ``UNSUPPORTED_EVOLUTION``
      （デッキには入らないので、テストの盤面だけ）
    - ``cmd.target`` が自分の場のポケモンの番号（``TARGET_NOT_IN_PLAY``・``TARGET_NOT_YOURS``）。バトル場でもベンチでもよい
    - おたがいのプレイヤーの最初の番ではない（p.310。``FIRST_TURN_EVOLUTION``）
    - 進化カードの「○○○○から進化」の名前が、そのポケモン（いちばん上のカード）の名前と同じ（p.309・p.324「書かれて
      いない組み合わせでカードを重ねてはいけません」。``EVOLUTION_NAME_MISMATCH``）。たねポケモンに 2 進化カードを
      直接重ねること（ビードルにスピアー）も、名前が違うのでここで拒否する
    - そのポケモンが「その番の最初から場に出ていた」（p.310）: 今の番に場に出したポケモン（``PLAYED_THIS_TURN``）・
      今の番に進化したポケモン（別のポケモンとしてあつかわれ、その番の最初には場にいなかったことになる。
      ``EVOLVED_THIS_TURN``。v0.4c: 今の番に 1 進化したポケモンを同じ番に 2 進化させることもこれで拒否する）は
      進化させられない。制限は 1 匹ごとで、ほかのポケモンは進化させられる
    - 段階が合う（v0.4c。1 進化カードはたねポケモンに、2 進化カードは 1 進化ポケモンに重ねる。p.316・p.319 の
      「たね + 進化 + 進化」）。名前が合えば実際のカードの組では段階も合うので、カードのデータが名前と段階で食い違う
      テスト専用のカードだけで起こる（``EVOLUTION_STAGE_MISMATCH``。進化の重なりの不変条件を破る状態を作らない）
    - 進化したあとの HP が、のっているダメージ以下になる場合は、きぜつの扱いが原典で決められないので止める
      （``UNRESOLVED_EVOLUTION_HP``。v0.4a の対応カードでは HP が増え、v0.4c のコクーン → スピアーは HP が同じ 80
      なので、きぜつしていないポケモンでは起こらない）

    手順（p.310）: 1・2. 進化カードを手札から出して見せ、進化するポケモンの上に置く（下のカードはトラッシュしない。
    いちばん上のカードの内容がそのポケモンを表す）→ 3. 特殊状態と持続する効果から回復させる（``clear_special_conditions``
    の ``EVOLVE`` と、v0.4b の ``persistent.remove_persistent_effects`` の ``EVOLVE``。別々の処理）→ 4. マーカー・カウンター（ダメージカウンター以外）を取りのぞく
    （対応カードにない）→ 5. 進化によって引き起こされる特殊なことがら（対応カードにない）。

    受け継ぐもの: ダメージカウンター・エネルギーカード・ついているトレーナーカード（p.310）。場のポケモンの番号も変えない
    （エンジンの内部の識別子。docs/evolution-state-v0.4a.md）。下に重なったカード（2 進化ならたねポケモンと 1 進化
    ポケモンの 2 枚。下から順）と場に出た番（``played_turn``）もそのまま（v0.4c。docs/stage2-state-v0.4c.md）。
    ついているトレーナー（プラスパワー・ディフェンダー）の効果と有効期限は変わらない（カードの効果で、進化で消える
    「持続する効果」ではない。p.321 の 5・7 段階、p.322。SUPPORTED。docs/evolution-rules-v0.4a.md）。

    にげるの失敗の記録（``retreat_failed_turn``。v0.3c）: 進化したポケモンは別のポケモン（p.310）で、こんらんも消える
    （p.322）。p.311 の「一度「にげる」に失敗したこんらん状態のポケモン」をどちらの意味に読んでも、進化したポケモンは
    「にげる」を宣言できるので、記録を消す（SUPPORTED。ログ ``retreat_failure_cleared``）。特殊状態の解除とは別の処理。

    進化は乱数を使わず、決定も出さない。ログ ``evolve``（``player``・``pokemon_id``・進化前と進化後のカードの uid と
    カード id）。
    """
    p = _require_turn(state, cmd.player)
    _require_in_hand(state, cmd.player, cmd.card)
    definition = state.card_def(cmd.card)
    if definition.category != "pokemon" or definition.stage == "basic":
        raise IllegalActionError("NOT_EVOLUTION_CARD", f"カード {cmd.card}（{definition.name_ja}）は進化カードではない")
    if not definition.is_evolution_pokemon or not definition.supported:
        reasons = "; ".join(definition.unsupported_reasons) or f"{definition.stage} の進化は未実装"
        raise UnsupportedError("UNSUPPORTED_EVOLUTION", f"進化カード「{definition.name_ja}」は未対応（{reasons}）")
    target = p.find_by_pokemon_id(cmd.target)
    if target is None:
        if state.players[1 - cmd.player].find_by_pokemon_id(cmd.target) is not None:
            raise IllegalActionError("TARGET_NOT_YOURS", "相手の場のポケモンは進化させられない")
        raise IllegalActionError("TARGET_NOT_IN_PLAY", f"場のポケモンの番号 {cmd.target!r} は自分の場にいない")
    if state.turn_number <= 2:
        # 番は先攻から交互に進むので、1 番は先攻の、2 番は後攻の最初の番（p.309・p.310）
        raise IllegalActionError("FIRST_TURN_EVOLUTION", "おたがいのプレイヤーの最初の番には、ポケモンを進化させられない（p.310）")
    current = state.card_def(target.card)
    if current.name_ja != definition.evolves_from:
        raise IllegalActionError(
            "EVOLUTION_NAME_MISMATCH",
            f"「{definition.name_ja}」は「{definition.evolves_from}」から進化する。場のポケモン {target.pokemon_id} は「{current.name_ja}」",
        )
    if target.current_form_turn >= state.turn_number:
        if target.evolved_turn is not None:
            raise IllegalActionError(
                "EVOLVED_THIS_TURN", f"場のポケモン {target.pokemon_id} はこの番に進化したので、もう一度は進化させられない（p.310）"
            )
        raise IllegalActionError(
            "PLAYED_THIS_TURN", f"場のポケモン {target.pokemon_id} はこの番に場に出したので、進化させられない（p.310）"
        )
    below_stage = "basic" if definition.is_stage1_pokemon else "stage1"
    if current.stage != below_stage:
        raise IllegalActionError(
            "EVOLUTION_STAGE_MISMATCH",
            f"「{definition.name_ja}」（{definition.stage}）は {below_stage} のポケモンに重ねる。場のポケモン {target.pokemon_id} の"
            f"「{current.name_ja}」は {current.stage}（p.316・p.319）",
        )
    if target.damage >= definition.hp:
        raise UnsupportedError(
            "UNRESOLVED_EVOLUTION_HP",
            f"進化すると HP（{definition.hp}）がのっているダメージ（{target.damage}）以下になる。そのときにきぜつするか"
            "（いつきぜつの判定をするか）は『オフィシャルブック2000』（p.310・p.323）から決められないので扱わない",
        )

    # 1〜5. 手札から出して見せ、進化するポケモンの上に置き、特殊状態・持続する効果・にげるの失敗の記録を消す（v0.25 から、
    # 1 進化を飛ばして進化させるトレーナーの効果と共通の ``evolution.place_evolution_card``。動き・ログは v0.24 と同じ）
    place_evolution_card(state, cmd.player, target, cmd.card)


def _attach_energy(state: GameState, cmd: AttachEnergy) -> None:
    """エネルギーカードを 1 番に 1 枚、自分の場のポケモンにつける（p.310）。

    v0.6: この番に、ポケモンパワー（「あまごい」）の効果で手札からエネルギーをつけていて、通常の操作ではまだつけていなければ、
    この操作を受け付けるかは原典で決められない（p.310「ポケモンにつけることのできるエネルギーカードの数は、1回の自分の番ごとに
    1枚だけです」が、パワーでつけたカードも数えるのかが書かれていない。p.307・p.90。docs/rain-dance-v0.6.md の R13）。
    ほかの確認がすべて通ったあと、状態を変える前に ``UnsupportedError``（``UNRESOLVED_ATTACH_AFTER_POWER_ATTACH``）で止める。
    通常の操作でつけたあとの「あまごい」は受け付ける（どちらの読み方でも同じ。R12）。
    """
    p = _require_turn(state, cmd.player)
    _require_in_hand(state, cmd.player, cmd.energy)
    if not state.card_def(cmd.energy).is_basic_energy:
        raise IllegalActionError("NOT_BASIC_ENERGY", f"カード {cmd.energy} は基本エネルギーカードではない")
    if state.energy_attachments_this_turn >= state.rules.energy_attachments_per_turn:
        raise IllegalActionError("ENERGY_ALREADY_ATTACHED", "エネルギーカードはこの番にもうつけた（1 番に 1 枚）")
    target = p.find_in_play(cmd.target)
    if target is None:
        if state.players[1 - cmd.player].find_in_play(cmd.target) is not None:
            raise IllegalActionError("TARGET_NOT_YOURS", "相手の場のポケモンにはつけられない")
        raise IllegalActionError("TARGET_NOT_IN_PLAY", f"{cmd.target!r} は自分の場のポケモンではない")
    if state.energy_attached_by_powers_this_turn > 0:
        raise UnsupportedError(
            "UNRESOLVED_ATTACH_AFTER_POWER_ATTACH",
            f"この番にポケモンパワーの効果で手札からエネルギーを {state.energy_attached_by_powers_this_turn} 枚つけたあとで、手札から"
            "エネルギーをつける（通常の操作）ことができるかは『オフィシャルブック2000』から決められない（p.310 の「1回の自分の番ごとに"
            "1枚だけ」にパワーでつけたカードを数えるかが書かれていない）ので扱わない",
        )
    attach_energy_from_hand(state, cmd.player, cmd.energy, target)
    state.energy_attachments_this_turn += 1
    state.add_event("attach_energy", player=cmd.player, energy=cmd.energy, target=cmd.target)
    after_energy_attached(state, cmd.player, target, cmd.energy)  # v0.31: つけたときにはたらく特殊能力（ほのおでかいふく）


def _retreat(state: GameState, cmd: Retreat) -> None:
    """にげる（pp.310-311）。1 番に何度でも。控えがいなければ宣言できない。

    にげるエネルギーの数ぶん、そのポケモンについているエネルギーを選んでトラッシュし、控えと入れ替える。
    ベンチに戻ったポケモンの特殊状態はすべて消える（p.311・p.322）。どく状態でもにげられる。
    ねむり状態・マヒ状態のポケモンは「にげる」を宣言できない（p.311・p.322。v0.3b）。宣言できないので、エネルギーを
    トラッシュする前に拒否する（``POKEMON_ASLEEP``・``POKEMON_PARALYZED``）。「ポケモンいれかえ」はにげるではない
    （p.325）ので、この制限を受けない。

    こんらん状態（v0.3c。p.310〜311 の手順）: 1. 宣言 → 2. にげるエネルギーの数ぶんトラッシュ → 3. 持ち主がコインを 1 枚
    投げ、「うら」なら「にげる」は失敗（トラッシュしたエネルギーは取り戻せない）→ 4. 失敗でなければ控えと入れ替える。
    失敗したら入れ替えず（こんらん・ダメージ・ついているカードはそのまま）、そのポケモンは今の番ではもう「にげる」を宣言
    できない（``retreat_failed_turn``。番の終わりに消す）。番は終わらない。失敗は宣言した「にげる」の結果で、不正な
    コマンドではない（エネルギーのトラッシュとコインは状態に残る）。にげるエネルギーが 0 でもコインは投げる（手順 3 に
    例外がない）。入れ替える控え（手順 4 で選ぶ）はコマンドで先に指定するが、コインの結果で選べるものは変わらない。
    """
    p = _require_turn(state, cmd.player)
    active = p.active
    if not p.bench:
        raise IllegalActionError("NO_BENCH", "控えポケモンがいないので、にげるを宣言できない")
    _require_not_asleep_or_paralyzed(active, "「にげる」を宣言できない（p.311・p.322）")
    if active.retreat_failed_turn == state.turn_number:
        if active.conditions.confused:
            raise IllegalActionError(
                "RETREAT_ALREADY_FAILED",
                f"バトル場のポケモン {active.pokemon_id} は、この番にこんらんで「にげる」に失敗したので、もう宣言できない（p.311）",
            )
        # 失敗したあとにベンチに戻り（こんらんが消え）、同じ番にバトル場に戻ったポケモン。p.311 の「一度「にげる」に失敗した
        # こんらん状態のポケモン」に、こんらんでなくなったポケモンが含まれるかは原典で決められない
        raise UnsupportedError(
            "UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED",
            f"バトル場のポケモン {active.pokemon_id} は、この番にこんらんで「にげる」に失敗したあと、こんらんが消えている。"
            "p.311「一度「にげる」に失敗したこんらん状態のポケモンは、今の自分の番では、もう「にげる」を宣言することができません」が"
            "こんらんでなくなったポケモンにもかかるかは『オフィシャルブック2000』から決められないので扱わない",
        )
    index = p.bench_index(cmd.new_active)
    if index is None:
        raise IllegalActionError("NOT_ON_BENCH", f"{cmd.new_active!r} は自分のベンチにいない")
    cost = state.card_def(active.card).retreat_cost
    discard = tuple(cmd.discard)
    if len(set(discard)) != len(discard):
        raise IllegalActionError("DUPLICATE_CARD", "同じエネルギーを 2 回選んでいる")
    if any(uid not in active.energy for uid in discard):
        raise IllegalActionError("ENERGY_NOT_ATTACHED", "バトル場のポケモンについていないエネルギーを選んでいる")
    if len(discard) != cost:
        # 基本エネルギーは 1 枚 1 個なので、トラッシュする枚数 = にげるエネルギーの数
        raise IllegalActionError("WRONG_RETREAT_COST", f"にげるエネルギーは {cost} 個（{len(discard)} 枚選んでいる）")
    for uid in discard:
        active.energy.remove(uid)
        p.discard.append(uid)
    if active.conditions.confused and not _confusion_check(state, cmd.player, active, action="retreat", effect="retreat"):
        # 「にげる」は失敗。トラッシュしたエネルギーは取り戻せず、入れ替えはしない（p.311 の手順 3・4。v0.3c）
        active.retreat_failed_turn = state.turn_number
        state.add_event(
            "retreat_failed", player=cmd.player, pokemon=active.card, pokemon_id=active.pokemon_id, discarded=discard,
        )
        return
    # ついているカード・ダメージはいっしょに移動する（p.311）
    p.active, p.bench[index] = p.bench[index], active
    state.add_event("retreat", player=cmd.player, discarded=discard, old_active=active.card, new_active=cmd.new_active)
    # ベンチに戻ったら、特殊状態はすべて消える（p.311・p.322。v0.3a）
    clear_special_conditions(state, cmd.player, active, RETREAT)
    # ワザによる持続する効果も消える（p.311「…や、「持続する効果」は、すべて消えてなくなります」・p.322。v0.4b）。特殊状態とは別の処理
    remove_persistent_effects(state, cmd.player, active, RETREAT)


# ---------------------------------------------------------------- トレーナー（v0.2b）


def _play_trainer(state: GameState, cmd: PlayTrainer) -> None:
    """手札のトレーナーカードを使う（p.310「トレーナーカードを使う」）。

    - 自分の番（番の最初に引いたあと、ワザの前）に、1 番に何枚でも使える（p.309, p.310）。
      決定を待っている間（別のトレーナーの途中を含む）は使えない（p.310「その…起こることをすべて
      すませてからでないと、他のことはできません」）。
    - 効果の登録表に実装が登録されたトレーナーだけ使える。使うための条件・原典で決められない場合の
      確認（``TrainerEffect.check_playable``）を通ってから、手札から出す。
    - 手札から出して相手に見せ、名前を伝え（ログの ``play_trainer``）、説明にしたがう。説明が終わったら
      トラッシュする（``_finish_trainer``）。途中で決定を待つ間、カードは ``state.trainer_in_use`` にある。
    """
    p = _require_turn(state, cmd.player)
    _require_in_hand(state, cmd.player, cmd.card)
    definition = state.card_def(cmd.card)
    if definition.category != "trainer":
        raise IllegalActionError("NOT_TRAINER", f"カード {cmd.card} はトレーナーカードではない")
    effect = state.effects.trainer_effect(definition)
    if effect is None:
        problem = state.effects.trainer_problem(definition)
        raise UnsupportedError("UNSUPPORTED_TRAINER", f"「{definition.name_ja}」は未対応（{problem}）")
    use = TrainerUse(cmd.player, cmd.card, definition.id)
    effect.check_playable(state, use)

    # 1・2. 手札から出して相手プレイヤーに見えるようにし、名前を伝える（p.310）
    p.hand.remove(cmd.card)
    state.trainer_in_use = TrainerInUse(cmd.player, cmd.card)
    state.add_event("play_trainer", player=cmd.player, card=cmd.card, trainer=definition.name_ja)
    # 3・4. 使うための条件と、残りの説明にしたがう。決定を出したら、ここで止まり _resume_trainer から続ける
    effect.resolve(state, use)
    if state.decision is None:
        _finish_trainer(state, effect)


def _finish_trainer(state: GameState, effect) -> None:
    """トレーナーを使い終えて、番の続きにもどる。

    - 使いすて（特に記述がないかぎり。p.310）: 使ったカードをトラッシュする。
    - つけて使うトレーナー（``effect.stays_in_play``。v0.2c）: 説明にしたがってポケモンについたので、
      トラッシュしない（``resolve`` が ``zones.attach_trainer`` で使用中から場に移した）。

    今のトレーナーは、きぜつ・勝敗を起こさないので、使い終わったら自分の番（MAIN）にもどる。
    """
    used = state.trainer_in_use
    if effect.stays_in_play:
        if used is not None:
            raise RuntimeError(f"つけて使うトレーナー {used.card} が、使い終わっても場についていない（エンジンの不具合）")
    else:
        state.trainer_in_use = None
        state.players[used.player].discard.append(used.card)
        state.add_event("discard_trainer", player=used.player, card=used.card)
    state.phase = Phase.MAIN


def _resume_trainer(state: GameState, decision, choices: tuple[int, ...]) -> None:
    """トレーナーの効果の途中で出した決定の続き。決定がなくなったら、カードをトラッシュして番にもどる。"""
    player, card, card_id = decision.context_value("use")
    entry = state.effects.trainer_entry(card_id)
    entry.effect.resume(state, TrainerUse(player, card, card_id), decision, choices)
    if state.decision is None:
        _finish_trainer(state, entry.effect)


# ---------------------------------------------------------------- ポケモンパワー（特殊能力。v0.5）


def _use_pokemon_power(state: GameState, cmd: UsePokemonPower) -> None:
    """自分の場のポケモンの特殊能力（ポケモンパワー）の使用を宣言し、説明にしたがって処理する（p.311「ポケモンの特殊能力を使う」・
    p.323「14 ポケモンの特殊能力」。v0.5）。

    - 使えるのは、使用を宣言して使う特殊能力だけ（自動的にはたらく・常にはたらいている特殊能力は宣言しない。p.311・p.323）。
      効果の登録表に実装が登録された特殊能力だけ（``EffectRegistry.power_effect``。登録がなければ ``UNSUPPORTED_POKEMON_POWER``）。
    - 自分の番（``Phase.MAIN``）だけ（``_require_turn``）。番の最初に引くまでは何もできず（p.309）、ワザを使ったら番は終わり（p.309）、
      決定を待つ間（トレーナー・ワザ・きぜつのあとの決定）はほかのことをしない（p.309・p.310・p.311）。v0.5 の対応カード（エナジート
      ランス）の説明は「自分の番の中で」。相手の番・ポケモンチェック（どちらの番でもない。p.323）に使う特殊能力は未対応。
    - 特殊能力を使うポケモンは、自分の場（バトル場・ベンチ）のポケモンの番号（``cmd.pokemon``）。「特に指示されていないかぎり、
      ベンチにいるポケモンも特殊能力を使うことができます」「エネルギーカードをつけていなくても」（p.311・p.323）。どの特殊能力が
      あるかは、いちばん上のカードで決める（進化したら進化前の特殊能力は使えない。p.310）。
    - 手順（p.311）: 1. 使うポケモンを示し、名前を伝えて宣言する（ログ ``pokemon_power``）→ 2. 使うための条件にしたがう（実装の
      ``check_usable``。したがえなければ使えない）→ 3. 説明にしたがって処理する（実装の ``resolve``）。確かめることはどれも宣言の
      前に済ませるので、拒否したら状態・乱数・ログは変わらない。
    - 使っても番は終わらない（``Phase.MAIN`` のまま。ワザのあとの処理（解決の基盤の ``flow._finish_attack``）を通らない）。「特に指示されていないかぎり、特殊能力は
      いつでも、何度でも使用を宣言することができます」（p.323）ので、回数を数えない（回数の制限のある特殊能力は未対応）。
    - v0.8: 常にはたらいている特殊能力（``effects.SuppressOtherPowers``。ベトベトンの「かがくへんかガス」）は宣言しないので、使おうと
      したら ``POWER_NOT_DECLARABLE``（v0.9 の自動的にはたらく特殊能力 ``effects.AttackImmunityOnHeads``（ゴーストの「とうめい」）も
      同じ。ワザを受けるときにワザの処理の中で評価する。``effects.attack_reaches``。v0.10 のダメージを受けたときに自動的にはたらく
      特殊能力 ``effects.CounterattackDamage``（カイリキーの「はんげき」）も同じ。``effects.deal_attack_damage``・
      ``effects.finish_damage_elements``）。宣言する特殊能力は、登録の確認のあと、
      パワーごとの確認（``check_usable``）の前に、今はたらいている「かがくへんかガス」に消されていないかを今の状態から求めて
      （``continuous.suppressors_of``）、消されていれば ``POWER_SUPPRESSED``（「使えず、その力も消える」。p.48・p.323）。p.311 の
      「そのとき使うことのできるもの」を、宣言の前に確かめる（宣言もない。状態・乱数・ログは変わらない）。自分の場・相手の場の
      どちらのかがくへんかガスでも同じ（p.48 の解説）。
    - v0.7 のダメージスワップ（``effects.MoveDamageCounter``）は、のせかえでポケモンがきぜつするなら ``check_usable`` で拒否するので、
      特殊能力の処理のあとにきぜつの処理（トラッシュ・サイド・交代）はない。もし処理のあとに HP 以上のダメージのポケモンがいれば、
      ``apply_command`` の不変条件（場のポケモンのダメージは HP より小さい）が ``StateIntegrityError`` にする。
    """
    p = _require_turn(state, cmd.player)
    user = p.find_by_pokemon_id(cmd.pokemon)
    if user is None:
        if state.players[1 - cmd.player].find_by_pokemon_id(cmd.pokemon) is not None:
            raise IllegalActionError("POKEMON_NOT_YOURS", "相手の場のポケモンの特殊能力は使えない")
        raise IllegalActionError("POKEMON_NOT_IN_PLAY", f"場のポケモンの番号 {cmd.pokemon!r} は自分の場にいない")
    definition = state.card_def(user.card)
    if not 0 <= cmd.power < len(definition.powers):
        raise IllegalActionError(
            "NO_POKEMON_POWER", f"場のポケモン {user.pokemon_id}（{definition.name_ja}）に {cmd.power!r} 番目の特殊能力はない"
        )
    power = definition.powers[cmd.power]
    effect = state.effects.power_effect(definition.id, power)
    if effect is None:
        problem = state.effects.power_problem(definition.id, power)
        raise UnsupportedError("UNSUPPORTED_POKEMON_POWER", f"特殊能力「{power.name_ja}」は未対応（{problem}）")
    if not effect.declared:
        raise IllegalActionError(
            "POWER_NOT_DECLARABLE",
            f"特殊能力「{power.name_ja}」は使用を宣言しない（常にはたらく・決められたときに自動的にはたらく特殊能力。p.311・p.323）",
        )
    suppressors = suppressors_of(state, power)
    if suppressors:
        names = "・".join(f"{pid}（{state.card_def(state.find_pokemon(pid)[1].card).name_ja}）" for pid in suppressors)
        raise IllegalActionError(
            "POWER_SUPPRESSED",
            f"場のポケモン {names}の特殊能力がはたらいているので、特殊能力「{power.name_ja}」は使えず、その力も消えている（p.48・p.323）",
        )
    use = PowerUse(cmd.player, user.pokemon_id, PowerKey(definition.id, cmd.power), cmd.energy, cmd.source, cmd.target)
    effect.check_usable(state, use)

    # 1. 宣言（p.311）。2. の条件は check_usable で確かめた。3. 説明にしたがって処理する
    state.add_event(
        "pokemon_power", player=cmd.player, pokemon=user.card, pokemon_id=user.pokemon_id, power=power.name_ja, power_index=cmd.power
    )
    effect.resolve(state, use)
    if state.decision is not None or state.phase is not Phase.MAIN:
        raise RuntimeError(f"特殊能力 {use.key} の処理のあとで、番が続いていない（v0.5〜v0.7 の特殊能力は決定を出さない。エンジンの不具合）")


# ---------------------------------------------------------------- 保留中の決定に答える・コマンドの振り分け


def _answer_decision(state: GameState, cmd, context: resolution.Context) -> None:
    """保留中の決定に答える（``ResolveDecision``・v0.1 からある形の ``TakePrize``・``PromoteActive``）。確認（決定を待つ段階・決定する
    プレイヤー・決定の番号・選択）は ``checks.decision_choices``（v0.15 と同じ確認・同じ順番・同じコード）。確かめ終わった選択で、再開先が
    解決の基盤の再開先（``resolution.RESUMES``: ワザの途中・きぜつの判定・サイド・きぜつしたあとの特殊能力・バトル場に出す）なら解決の基盤、
    トレーナーの決定（``trainer``）なら ``_resume_trainer`` で続ける（決定そのものはログに残さない。選んだ結果を再開した処理がログに残す）。"""
    choices = decision_choices(state, cmd)
    decision = state.decision
    if decision.resume in resolution.RESUMES:
        resolution.resume_decision(state, choices, context)
        return
    if decision.resume != "trainer":
        raise RuntimeError(f"決定の再開先 {decision.resume!r} を続ける処理がない（不変条件で拒否するはず。エンジンの不具合）")
    state.decision = None
    _resume_trainer(state, decision, choices)


def _engine(handler: Callable[[GameState, object], None]) -> Callable[[GameState, object, resolution.Context], None]:
    """範囲外のコマンドの処理（解決の設定を使わない）。"""
    return lambda state, command, context: handler(state, command)


_HANDLERS: dict[type, Callable[[GameState, object, resolution.Context], None]] = {
    PlaceStartingPokemon: _engine(_place_starting_pokemon),
    DrawMulliganCards: _engine(_draw_mulligan_cards),
    ReportJankenResult: _engine(_report_janken_result),
    PlayBasicToBench: _engine(_play_basic_to_bench),
    AttachEnergy: _engine(_attach_energy),
    Retreat: _engine(_retreat),
    UseAttack: resolution.handle,  # ワザ（解決の基盤。v0.16b）
    EndTurn: resolution.handle,  # 番の終わり（解決の基盤。v0.16b）
    TakePrize: _answer_decision,
    PromoteActive: _answer_decision,
    ResolveDecision: _answer_decision,
    PlayTrainer: _engine(_play_trainer),
    EvolvePokemon: _engine(_evolve_pokemon),
    UsePokemonPower: _engine(_use_pokemon_power),
}


# ---------------------------------------------------------------- 検査用


def check_invariants(state: GameState) -> list[str]:
    """状態の不変条件の問題を返す。問題がなければ空のリスト。

    ``new_game`` と ``apply_command`` は、返す前に必ずこれで確かめる（StateIntegrityError）。

    - カードの保存則: 対戦のすべてのカード（``state.cards``）が、持ち主のゾーンのどこか 1 か所にだけある。
      未知の番号のカードはない。``new_game`` で作った対戦では、カードの組がデッキリストと同じ。
    - 場の形: 場のポケモンはポケモンのカード、ついているのは基本エネルギー、ダメージは 10 の倍数で HP 未満（v0.10: ワザの途中の
      決定を待つ間の、相手の「はんげき」で HP 以上になったワザを使ったポケモンだけを除く。``_counter_knocked_out_attacker_awaiting``。
      v0.11: 「こんじょう」を使うかの決定を待つ間の、その対象のポケモンと、同じワザで HP 以上になったワザを使ったポケモンを除く。
      ``_ko_prevention_awaiting``。v0.12: ワザの途中の決定を待つ間の、相手の「ほのおのかべ」で HP 以上になったワザを使ったポケモンも
      ``_counter_knocked_out_attacker_awaiting`` で除く）、
      ベンチは 5 匹まで、サイドはルールの枚数まで。
    - 「ふしちょう」を使うかの決定（v0.12。再開先 ``"post_knockout"``）を待つ間は、バトル場が空のプレイヤーがいてよい（きぜつの処理のあと、
      バトル場に出す前）。決定と、その前のサイドを取る決定の候補（``context`` の ``"post_knockout"``）は
      ``_post_knockout_decision_problems``・``_post_knockout_candidate_problems`` が確かめる。
    - 段階との対応: 番の途中は両方のバトル場にポケモンがいる。サイドを取る・バトル場に出す段階には、
      それを待っているプレイヤーがいる。終わった段階には結果か止めた理由がある。
    - 特殊状態（v0.3a）: 特殊状態があるのはバトル場のポケモンだけ。どくのダメージは 10 の倍数の正の数。
    - 進化（v0.4a）: 重なっているカードも場のカードとして数える（カードの保存則）。重なりの形・場に出た番・進化した番
      （``_evolution_problems``）。
    - ワザによる持続する効果（v0.4b）: 型・発生源・番・期限・置き場所（バトル場だけ）・重複・ログとの対応
      （``_persistent_effect_problems``）。持続する効果はカードではないので、カードの保存則には数えない。
    - 番の進行（v0.3a）: 番と番のあいだに、番の終わりとポケモンチェックがちょうど 1 回ずつ、この順にある。
      ポケモンチェックの途中の決定（続きが次の番）なら、今の番のあとに 1 回ずつ。番の途中なら、まだない。
    - ポケモンパワーで手札からつけたエネルギーの数（v0.6）: 今の番のログの ``power_attach_energy`` の数と同じ
      （``_power_attachment_problems``）。
    """
    problems: list[str] = []
    rules = state.rules
    seen: dict[int, str] = {}
    evolve_events = None  # 進化のログ（v0.4c。進化しているポケモンがいれば読む）

    for uid, card in state.cards.items():
        if card.uid != uid or card.owner not in PLAYERS:
            problems.append(f"カードの表の {uid} 番が {card} になっている")

    def place(uid: int, player: int, zone: str) -> None:
        where = f"プレイヤー {player} の {zone}"
        if uid not in state.cards:
            problems.append(f"未知のカード {uid!r} が {where} にある")
            return
        if uid in seen:
            problems.append(f"カード {uid} が {seen[uid]} と {where} の 2 か所にある")
        seen[uid] = where
        if state.cards[uid].owner != player:
            problems.append(f"カード {uid} が持ち主でない {where} にある")

    for player, p in enumerate(state.players):
        for zone in ("deck", "hand", "prizes", "discard"):
            for uid in getattr(p, zone):
                place(uid, player, zone)
        for pokemon in p.in_play():
            place(pokemon.card, player, "場")
            stack = pokemon.evolution_stack
            for uid in stack if isinstance(stack, tuple) else ():
                place(uid, player, "場（進化しているポケモンの下のカード）")  # v0.4a
            for uid in pokemon.energy:
                place(uid, player, "場（ついているエネルギー）")
                if uid in state.cards and not state.card_def(uid).is_basic_energy:
                    problems.append(f"基本エネルギーでないカード {uid} がポケモンについている")
            problems.extend(_attached_trainer_problems(state, player, pokemon, place))
            if pokemon.card not in state.cards:
                continue
            definition = state.card_def(pokemon.card)
            if definition.category != "pokemon":
                problems.append(f"ポケモンでないカード {pokemon.card} が場にポケモンとしてある")
                continue
            if pokemon.damage < 0 or pokemon.damage % 10:
                problems.append(f"ポケモン {pokemon.card} のダメージ {pokemon.damage} が 10 の倍数でない")
            if pokemon.damage >= definition.hp and not (
                _counter_knocked_out_attacker_awaiting(state, player, pokemon) or _ko_prevention_awaiting(state, player, pokemon)
                or _attack_damage_awaiting(state, player, pokemon)
            ):
                problems.append(f"ポケモン {pokemon.card} が HP 以上のダメージで場に残っている")
            if pokemon.evolution_stack and evolve_events is None:
                evolve_events = _evolve_events_by_pokemon(state)  # 進化しているポケモンがいるときだけ、ログを 1 回読む（v0.4c）
            problems.extend(_evolution_problems(state, player, pokemon, evolve_events))
            problems.extend(_condition_problems(state, player, p, pokemon))
            problems.extend(_persistent_effect_problems(state, player, p, pokemon))
        if len(p.bench) > rules.max_bench:
            problems.append(f"プレイヤー {player} のベンチが {len(p.bench)} 匹")
        if len(p.prizes) > rules.prize_count:
            problems.append(f"プレイヤー {player} のサイドが {len(p.prizes)} 枚（{rules.prize_count} 枚まで）")
        if p.mulligan_draws_remaining < 0:
            problems.append(f"プレイヤー {player} の切り直しの補償の残りが負")
    # 使っている最中のトレーナーカード（v0.2b）も、持ち主のゾーンの 1 つとして数える
    used = state.trainer_in_use
    if used is not None:
        if used.player not in PLAYERS:
            problems.append(f"使用中のトレーナーの持ち主 {used.player!r} が正しくない")
        else:
            place(used.card, used.player, "使用中のトレーナー")
            if used.card in state.cards and state.card_def(used.card).category != "trainer":
                problems.append(f"トレーナーカードでないカード {used.card} が使用中のトレーナーになっている")
    missing = set(state.cards) - set(seen)
    if missing:
        problems.append(f"どこにもないカード {sorted(missing)}")

    # 場のポケモンの番号: 付いていて、重ならず、まだ配っていない番号ではない
    pokemon_ids = [pokemon.pokemon_id for p in state.players for pokemon in p.in_play()]
    for pokemon_id in pokemon_ids:
        if type(pokemon_id) is not int or not 1 <= pokemon_id < state.next_pokemon_id:
            problems.append(f"場のポケモンの番号 {pokemon_id!r} が正しくない（次に付ける番号 {state.next_pokemon_id}）")
    if len(set(pokemon_ids)) != len(pokemon_ids):
        problems.append(f"場のポケモンの番号が重なっている {sorted(pokemon_ids)}")

    # new_game で作った対戦は、カードの組が対戦開始時のデッキリストと同じ
    if any(state.decklists):
        for owner in PLAYERS:
            ids = sorted(c.card_id for c in state.cards.values() if c.owner == owner)
            if ids != sorted(state.decklists[owner]):
                problems.append(f"プレイヤー {owner} のカードの組が対戦開始時のデッキと違う")

    phase = state.phase
    if not isinstance(phase, Phase):
        problems.append(f"段階 {phase!r} が Phase ではない")
        return problems
    problems.extend(_progress_problems(state))
    problems.extend(_power_attachment_problems(state))
    problems.extend(_turn_power_problems(state))  # v0.31
    if phase in TERMINAL_PHASES:
        if state.decision is not None:
            problems.append("対戦が終わっているのに、決定が残っている")
        if state.trainer_in_use is not None:
            problems.append("対戦が終わっているのに、使用中のトレーナーが残っている")
        if phase is Phase.HALTED and state.halt is None:
            problems.append("止めた理由がないまま HALTED になっている")
        if phase is not Phase.HALTED and state.result is None:
            problems.append("結果がないまま対戦が終わっている")
        return problems
    if state.result is not None or state.halt is not None:
        problems.append(f"結果か止めた理由があるのに {phase.value} になっている")
    if not 1 <= state.next_decision_id:
        problems.append(f"次の決定の番号 {state.next_decision_id!r} が正しくない")

    # v0.12: 「ふしちょう」を使うかの決定（きぜつの処理のあと、バトル場に出す前。再開先 "post_knockout"）を待つ間も、バトル場が空のことがある
    after_knockout = phase is Phase.DECISION and state.decision is not None and state.decision.resume == "post_knockout"
    for player, p in enumerate(state.players):
        if p.placed_starting_pokemon and p.active is None and phase not in (Phase.TAKE_PRIZE, Phase.PROMOTE_ACTIVE) and not after_knockout:
            problems.append(f"プレイヤー {player} のバトル場にポケモンがいないまま {phase.value} になっている")
    if phase is Phase.MAIN:
        if state.current_player not in PLAYERS:
            problems.append(f"番のプレイヤー {state.current_player!r} が正しくない")
        if not 0 <= state.energy_attachments_this_turn <= rules.energy_attachments_per_turn:
            problems.append(f"この番にエネルギーをつけた回数 {state.energy_attachments_this_turn} が正しくない")
    if state.first_player is not None and phase not in SETUP_PHASES:
        # 番は先攻から 1 番ずつ交互に進む（p.309）。有効期限（「次の相手の番の終わり」= 今の番 + 1）の前提（v0.2e）
        if state.first_player not in PLAYERS or not isinstance(state.turn_number, int) or state.turn_number < 1:
            problems.append(f"先攻 {state.first_player!r}・番 {state.turn_number!r} が正しくない")
        elif state.current_player != turn_owner(state, state.turn_number):
            problems.append(f"{state.turn_number} 番はプレイヤー {turn_owner(state, state.turn_number)} の番なのに、番のプレイヤーが {state.current_player!r}")
    problems.extend(_decision_problems(state))
    problems.extend(_trainer_problems(state))
    if phase is Phase.SETUP_MULLIGAN_DRAW and not any(p.mulligan_draws_remaining for p in state.players):
        problems.append("切り直しの補償を引く段階なのに、引く権利のあるプレイヤーがいない")
    return problems


def _evolution_problems(state: GameState, player: int, pokemon: PokemonInPlay, evolve_events: dict | None = None) -> list[str]:
    """場のポケモンのカードの重なりと、場に出た番・進化した番（v0.4a。v0.4c で 2 進化まで。p.309・p.310・p.316・p.319・p.324）。

    - 重なり（``evolution_stack``）: 整数のタプルで、0〜2 枚（重なったカードは全部で 3 枚まで。p.319 の「1枚のたね
      ポケモンカードと、1または2枚の進化カードの合計2枚または3枚」。ベイビィ（C・D）は未対応）。重なりの長さで、
      下から順の段階が決まる: たね → 1 進化 → 2 進化。いちばん下はたねポケモン、そこから上の各カードは決まった段階で、
      その「○○○○から進化」の名前がすぐ下のカードの名前（すべての隣り合う 2 枚を確かめる。書かれていない組み合わせで
      重ねない。p.324）
    - 場に出た番（``played_turn``）: 0（対戦準備）〜今の番
    - 進化した番（``evolved_turn``。いまの姿に進化した番）: 進化していなければ None。進化していれば、場に出た番より後・
      今の番まで・持ち主の番・おたがいの最初の番（1・2 番）ではない（p.310）
    - 2 進化しているポケモン（v0.4c）: 1 進化した番は状態に持たない（``evolved_turn`` は 2 進化した番）。1 進化は
      場に出た番より後・2 進化した番より前（同じ番に二度は進化できない。p.310）の、3 番以降の持ち主の番なので、その
      ような番があることを確かめる（状態だけで確かめられる必要条件）
    - ログとの対応（v0.4c）: このポケモンの進化のログ ``evolve``（``evolve_events``。同じ ``pokemon_id``。番号は使い回さない
      ので、ほかのポケモンのログは混ざらない）は、重なりのいちばん上の側の移り変わり（下のカード → 上のカード）と
      順番どおりに対応し、番は場に出た番より後で、同じ番に二度進化しておらず（番が増えていく）、最後のログの番が
      ``evolved_turn``。``new_game`` から始めた対戦（ログが対戦の最初からある）では、すべての移り変わりにログがある。
      テスト専用に盤面を作った状態（``build_test_state``）は、作った重なりのログがないので、あるログだけを確かめる
    - 今の番に進化したポケモンに、進化のあとで付けられていない特殊状態が残っていない（進化で消える。p.310・p.322）
    """
    where = f"ポケモン {pokemon.pokemon_id}"
    stack = pokemon.evolution_stack
    if not isinstance(stack, tuple) or any(type(uid) is not int for uid in stack):
        return [f"{where} の重なっているカード {stack!r} が整数のタプルではない"]
    played, evolved = pokemon.played_turn, pokemon.evolved_turn
    if type(played) is not int or not 0 <= played <= state.turn_number:
        return [f"{where} の場に出た番 {played!r} が正しくない（0〜今の番 {state.turn_number}）"]
    if evolved is not None and type(evolved) is not int:
        return [f"{where} の進化した番 {evolved!r} が整数ではない"]
    if any(uid not in state.cards for uid in stack) or pokemon.card not in state.cards:
        return []  # 未知のカードはカードの保存則のほうで数える
    top = state.card_def(pokemon.card)
    problems = []
    if not stack:
        if not top.is_basic_pokemon:
            problems.append(f"{where} は進化していないのに、いちばん上のカード {pokemon.card}（{top.name_ja}）がたねポケモンではない")
        if evolved is not None:
            problems.append(f"{where} は進化していないのに、進化した番 {evolved} がある")
        return problems
    if len(stack) > len(EVOLUTION_STAGES) - 1:
        problems.append(f"{where} に {len(stack) + 1} 枚のカードが重なっている（2 進化までの 3 枚まで。p.319）")
    chain = (*stack, pokemon.card)
    events = () if evolve_events is None else evolve_events.get(pokemon.pokemon_id, ())
    for position, uid in enumerate(chain):
        definition = state.card_def(uid)
        if definition.category != "pokemon" or definition.stage not in EVOLUTION_STAGES:
            problems.append(
                f"{where} の重なりが正しくない（{len(chain)} 枚のカードの下から {position + 1} 枚目 {uid}（{definition.name_ja}）が"
                f" 進化の段階のポケモンのカードではない）"
            )
            continue
        if position == 0:
            if not definition.is_basic_pokemon:
                problems.append(f"{where} のいちばん下のカード {uid} がたねポケモンではない")
            continue
        below = state.card_def(chain[position - 1])
        if below.category != "pokemon" or below.stage not in EVOLUTION_STAGES:
            continue
        step = EVOLUTION_STAGES.index(definition.stage) - EVOLUTION_STAGES.index(below.stage)
        if step == 1:
            if definition.evolves_from != below.name_ja:
                problems.append(
                    f"{where} のカードの重なりが正しくない（{below.name_ja} の上に {definition.name_ja}。{definition.name_ja} は"
                    f" {definition.evolves_from!r} から進化）"
                )
        elif step == 2 and below.is_basic_pokemon:
            # v0.25: 1 進化を飛ばした重なり（たねポケモン + 2 進化。トレーナーの効果。docs/pokemon-breeder-v0.25.md）。系統は、2 進化カードの進化元の
            # 1 進化カード（写しのカードのデータ）の進化元の名前で確かめ、その移り変わりの進化のログ（evolve の trainer_card）を要る
            # （通常の操作ではできない重ね方なので、ログのない重なりは認めない。テストの盤面（build_test_state）でも同じ）
            if skipped_stage1_basic(definition) != below.name_ja:
                problems.append(
                    f"{where} の重なりが正しくない（たねポケモン {below.name_ja} の上に 2 進化の {definition.name_ja}。"
                    f"{definition.name_ja} の進化元の 1 進化（{definition.evolves_from!r}）の進化元は {list(definition.stage1_evolves_from)}）"
                )
            elif not any((e.get("from_card"), e.get("to_card")) == (chain[position - 1], uid) and "trainer_card" in e for e in events):
                problems.append(
                    f"{where} の重なりが正しくない（たねポケモン {below.name_ja} の上に 2 進化の {definition.name_ja}。1 進化を飛ばして"
                    "重ねるトレーナーの進化のログ（evolve の trainer_card）がない）"
                )
        else:
            problems.append(
                f"{where} の重なりが正しくない（{len(chain)} 枚のカードの下から {position + 1} 枚目 {uid}（{definition.name_ja}）が"
                f" {definition.stage!r} で、すぐ下の {below.name_ja}（{below.stage}）の次の段階ではない）"
            )
    if evolved is None:
        problems.append(f"{where} は進化しているのに、進化した番がない")
        return problems
    if not played < evolved <= state.turn_number:
        problems.append(f"{where} の進化した番 {evolved} が、場に出た番 {played} より後・今の番 {state.turn_number} までではない")
    elif evolved <= 2:
        problems.append(f"{where} がおたがいの最初の番（{evolved} 番）に進化している（p.310）")
    elif state.first_player in PLAYERS and turn_owner(state, evolved) != player:
        problems.append(f"{where} が持ち主の番でない {evolved} 番に進化している")
    elif len(stack) >= 2 and state.first_player in PLAYERS:
        # 2 進化（v0.4c）: 1 進化した番は、場に出た番・2 番より後で、2 進化した番より前の持ち主の番（同じ番には進化できない）
        if not any(turn_owner(state, turn) == player for turn in range(max(played, 2) + 1, evolved)):
            problems.append(
                f"{where} は {evolved} 番に 2 進化しているが、場に出た番 {played} のあと {evolved} 番より前に、1 進化できる持ち主の番がない"
                "（同じ番に二度は進化できない。p.310）"
            )
    if evolve_events is not None:
        problems.extend(_evolution_log_problems(state, player, pokemon, chain, evolve_events.get(pokemon.pokemon_id, ())))
    if evolved == state.turn_number and pokemon.conditions.names():
        applied_after = False
        for event in _events_since_turn_start(state):
            if event.get("pokemon_id") != pokemon.pokemon_id:
                continue
            if event["kind"] == "evolve":
                break
            if event["kind"] == "special_condition":
                applied_after = True
        if not applied_after:
            problems.append(f"{where} は今の番に進化したのに、進化の前の特殊状態 {pokemon.conditions.names()} が残っている（p.310・p.322）")
    return problems


def _evolve_events_by_pokemon(state: GameState) -> dict[int, list]:
    """ログの進化のイベント ``evolve`` を、場のポケモンの番号ごとに古い順に集める（v0.4c。不変条件で 1 回だけ読む）。"""
    events: dict[int, list] = {}
    for event in state.log:
        if event["kind"] == "evolve":
            events.setdefault(event.get("pokemon_id"), []).append(event)
    return events


def _evolution_log_problems(state: GameState, player: int, pokemon: PokemonInPlay, chain: tuple, events) -> list[str]:
    """進化しているポケモンの重なりと、そのポケモンの進化のログ ``evolve`` の対応（v0.4c。``_evolution_problems`` の説明）。"""
    where = f"ポケモン {pokemon.pokemon_id}"
    transitions = len(chain) - 1
    if len(events) > transitions:
        return [f"{where} の進化のログが {len(events)} 回あるのに、重なりは {transitions} 回ぶん（{len(chain)} 枚）"]
    if any(state.decklists) and len(events) != transitions:
        # new_game から始めた対戦は、ログが対戦の最初からあるので、すべての進化にログがある
        return [f"{where} は {transitions} 回進化した重なり（{len(chain)} 枚）なのに、進化のログが {len(events)} 回"]
    problems = []
    previous_turn = pokemon.played_turn
    for offset, event in enumerate(events):
        index = len(chain) - len(events) + offset  # この進化でいちばん上になったカードの位置
        expected = (chain[index - 1], chain[index])
        if (event.get("from_card"), event.get("to_card")) != expected or event.get("player") != player:
            problems.append(
                f"{where} の進化のログ（{event.get('from_card')!r} → {event.get('to_card')!r}、プレイヤー {event.get('player')!r}）が、"
                f"重なり（{expected[0]} → {expected[1]}、プレイヤー {player}）と対応しない"
            )
        problems.extend(_skip_evolution_log_problems(state, player, where, event, expected))
        if event["turn"] <= previous_turn:
            problems.append(
                f"{where} が {event['turn']} 番に進化しているが、場に出た番・前の進化の番（{previous_turn} 番）より後ではない"
                "（同じ番に二度は進化できない。p.310）"
            )
        previous_turn = event["turn"]
    if events and events[-1]["turn"] != pokemon.evolved_turn:
        problems.append(f"{where} の最後の進化のログは {events[-1]['turn']} 番なのに、進化した番が {pokemon.evolved_turn}")
    return problems


def _skip_evolution_log_problems(state: GameState, player: int, where: str, event, transition: tuple[int, int]) -> list[str]:
    """進化のログ ``evolve`` の ``trainer_card``（v0.25）: たねポケモンの上に 2 進化カードを重ねた（1 進化を飛ばした）移り変わりだけに
    あり、そのときの番に持ち主が使った、1 進化を飛ばして進化させるトレーナー（``TrainerEffect.skips_stage1_evolution``。
    docs/pokemon-breeder-v0.25.md）のカードの uid。通常の操作（``EvolvePokemon``）の移り変わりにはない。"""
    lower, upper = (state.card_def(uid) if uid in state.cards else None for uid in transition)
    skip = lower is not None and upper is not None and lower.is_basic_pokemon and upper.is_stage2_pokemon
    trainer = event.get("trainer_card")
    if not skip:
        if "trainer_card" in event:
            return [f"{where} の進化のログ（{transition[0]} → {transition[1]}）に trainer_card {trainer!r} があるが、1 進化を飛ばした進化ではない"]
        return []
    if type(trainer) is not int or trainer not in state.cards or state.cards[trainer].owner != player:
        return [f"{where} の 1 進化を飛ばした進化のログの trainer_card {trainer!r} が、持ち主 {player} のカードではない"]
    entry = state.effects.trainer_entry(state.cards[trainer].card_id)
    if entry is None or not entry.effect.skips_stage1_evolution:
        return [f"{where} の 1 進化を飛ばした進化のログの trainer_card {trainer}（{state.cards[trainer].card_id}）が、1 進化を飛ばして進化させるトレーナーではない"]
    return []


def _condition_problems(state: GameState, player: int, p: PlayerState, pokemon: PokemonInPlay) -> list[str]:
    """場のポケモンの特殊状態（v0.3a・v0.3b）。特殊状態になるのはバトル場のポケモンだけで、ベンチに戻ったら消える（p.311・p.322）。

    - どく（``poison``）: ``Poison`` で、ダメージは 10 の倍数の正の数
    - ねむり・マヒ・こんらん（``exclusive``。v0.3b・v0.3c）: ``Asleep``・``Paralyzed``・``Confused`` の 1 つだけ
      （重複しない。p.322）
    - マヒ状態になった番は 1 以上・今の番まで。回復する番（``conditions.paralysis_recovery_turn``）が今の番より前なら、
      そのポケモンチェックで回復していないので違反（期限の過ぎたマヒが残らない。p.323 の 4）
    - こんらん状態で「にげる」に失敗した記録（``retreat_failed_turn``。v0.3c）: なければ None。あれば今の番の番号で、
      持ち主が番のプレイヤー（「今の自分の番では」。p.311）。番の終わりに消すので、対戦準備の段階・ほかの番・
      番の終わりのあと（ポケモンチェックの途中の決定）には残らない
    """
    conditions = pokemon.conditions
    if not isinstance(conditions, SpecialConditions):
        return [f"ポケモン {pokemon.pokemon_id} の特殊状態 {conditions!r} が SpecialConditions ではない"]
    problems = []
    poison = conditions.poison
    if poison is not None and (not isinstance(poison, Poison) or type(poison.damage) is not int or poison.damage <= 0 or poison.damage % 10):
        problems.append(f"ポケモン {pokemon.pokemon_id} のどく状態 {poison!r} が正しくない（ダメージは 10 の倍数の正の数）")
    problems.extend(_retreat_failure_problems(state, player, pokemon))
    exclusive = conditions.exclusive
    if exclusive is not None and type(exclusive) not in (Asleep, Paralyzed, Confused):
        return problems + [f"ポケモン {pokemon.pokemon_id} のねむり・マヒ・こんらんの項目 {exclusive!r} が Asleep・Paralyzed・Confused ではない"]
    if isinstance(exclusive, Paralyzed):
        turn = exclusive.turn
        if type(turn) is not int or not 1 <= turn <= state.turn_number:
            problems.append(f"ポケモン {pokemon.pokemon_id} がマヒ状態になった番 {turn!r} が正しくない（1〜今の番 {state.turn_number}）")
        elif state.first_player in PLAYERS and paralysis_recovery_turn(state, player, turn) < state.turn_number:
            problems.append(
                f"ポケモン {pokemon.pokemon_id} のマヒ状態（{turn} 番から）は {paralysis_recovery_turn(state, player, turn)} 番の終わりの"
                f"ポケモンチェックで回復しているはずなのに、{state.turn_number} 番に残っている（p.323）"
            )
    if conditions.names() and pokemon is not p.active:
        problems.append(f"プレイヤー {player} のベンチのポケモン {pokemon.pokemon_id} が特殊状態 {conditions.names()} になっている（p.322）")
    return problems


def _persistent_effect_problems(state: GameState, player: int, p: PlayerState, pokemon: PokemonInPlay) -> list[str]:
    """場のポケモンが受けているワザによる持続する効果（``PokemonInPlay.persistent_effects``。v0.4b。p.322・p.323）。

    - ``PERSISTENT_EFFECT_TYPES``（v0.4b は ``PreventDamage`` だけ）の値のタプルで、番の項目は整数
    - 置き場所: バトル場のポケモンだけ（ベンチに戻ったら消える。p.311・p.322。v0.4b の効果は、のせるタイプの
      カウンター・マーカーではない）。対戦準備の段階にはない
    - ``PreventDamage``（「かたまる」）は自分自身に与える効果なので、発生源はこのポケモンのいまのカード・持ち主
      （進化したら消えるので、いちばん上のカードが変わったあとに残らない。p.310・p.323）
    - 番: 効果を与えた番（``created_turn``）は持ち主の番で、いまの姿になった番以後・今の番まで。はたらく番（``active_turn``）
      は次の相手の番（``created_turn + 1``。v0.27 の ``NextTurnAttackDamage`` は次の自分の番 ``created_turn + 2``。型の
      ``turns_until_active``）。期限が過ぎていない（今の番がはたらく番より後なら、その番の終わりに
      消しているはず。はたらく番の終わり（ログ ``turn_end``）のあとにも残らない）
    - 重複: 同じ種類の効果は 1 つまで（v0.4b の対応カードでは、前の効果が消えるまで次の「かたまる」を使えない）。v0.27 の
      ``NextTurnAttackDamage`` だけは、はたらく番の違う 2 つまで（はたらく番に「つるぎのまい」をもう一度使うと、その番の終わりまで、
      今の番にはたらく効果と次の自分の番にはたらく効果がある）。同じ種類・同じはたらく番の効果は、どの型でも 1 つまで
    - ログとの対応: 同じポケモン・種類・番の ``persistent_effect_added`` があり、そのあとに、この効果を消したはずの
      イベント（``persistent_effect_removed``・``evolve``・``retreat``・``switch``・``forced_switch``（v0.4d））がない
    - v0.12 の ``Retaliation``（「ほのおのかべ」）: ``PreventDamage`` と同じ確認（自分自身・持ち主の番・次の相手の番・期限・バトル場だけ）に
      加えて、``attack_index`` がこのカードのワザの位置で、そのワザに ``DamageAndRetaliation`` が登録され、``amount`` がその実装の値
      （v0.13: 「こうらがえし」（``ReturnReceivedDamage``）も同じ確認で、決め方 ``basis`` と量（None）を登録された実装と照らす）
    """
    effects = pokemon.persistent_effects
    where = f"ポケモン {pokemon.pokemon_id} の持続する効果"
    if not isinstance(effects, tuple) or any(type(e) not in PERSISTENT_EFFECT_TYPES for e in effects):
        return [f"{where} {effects!r} が {PERSISTENT_EFFECT_TYPES} の値のタプルではない"]
    if not effects:
        return []
    if state.phase in SETUP_PHASES:
        return [f"{where} が対戦準備の段階（{state.phase.value}）にある"]
    problems = []
    if pokemon is not p.active:
        problems.append(f"プレイヤー {player} のベンチのポケモン {pokemon.pokemon_id} に持続する効果が残っている（p.311・p.322）")
    kinds = [e.kind for e in effects]
    single = [e.kind for e in effects if e.turns_until_active == 1]
    timed = [(e.kind, e.active_turn) for e in effects]
    if len(set(single)) != len(single) or len(set(timed)) != len(timed):
        problems.append(f"{where} に同じ種類の効果が重なっている {kinds}")
    recent = _events_since_turn_start(state)
    turn_ended = any(event["kind"] == "turn_end" for event in recent)
    for effect in effects:
        fields = (effect.source_card, effect.source_player, effect.created_turn, effect.active_turn)
        if any(type(value) is not int for value in fields):
            problems.append(f"{where} {effect!r} の項目が整数ではない")
            continue
        giver = 1 - player if effect.on_opponent else player  # v0.31: 相手に与える効果（しっぽをふる）は、効果を与えたのは相手
        if effect.on_opponent:
            if effect.source_player != giver or effect.source_card not in state.cards or state.cards[effect.source_card].owner != giver:
                problems.append(f"{where} {effect!r} の発生源が、相手（プレイヤー {giver}）のカードではない")
        elif effect.source_player != player or effect.source_card != pokemon.card:
            problems.append(f"{where} {effect!r} の発生源が、このポケモン（カード {pokemon.card}、プレイヤー {player}）ではない")
        if isinstance(effect, DamageReduction) and (type(effect.amount) is not int or effect.amount <= 0 or effect.amount % 10):
            problems.append(f"{where} {effect!r} の減らす量が 10 の倍数の正の数ではない")
        if effect.active_turn != effect.created_turn + effect.turns_until_active:
            what = "次の番（次の相手の番）" if effect.turns_until_active == 1 else f"{effect.turns_until_active} 番あと（次の自分の番）"
            problems.append(f"{where} {effect!r} のはたらく番が、効果を与えた番の{what}ではない")
        if not pokemon.current_form_turn <= effect.created_turn <= state.turn_number:
            problems.append(
                f"{where} {effect!r} を与えた番が、いまの姿になった番 {pokemon.current_form_turn}〜今の番 {state.turn_number} ではない"
            )
        elif state.first_player in PLAYERS and turn_owner(state, effect.created_turn) != giver:
            whose = "持ち主" if giver == player else f"効果を与えたプレイヤー {giver}"  # v0.31: 相手に与える効果（しっぽをふる）は与えたプレイヤー
            problems.append(f"{where} {effect!r} を、{whose}の番でない {effect.created_turn} 番に与えている")
        if state.turn_number > effect.active_turn or (state.turn_number == effect.active_turn and turn_ended):
            problems.append(f"{where} {effect!r} が、はたらく番 {effect.active_turn} の終わりを過ぎて残っている")
        if isinstance(effect, Retaliation):
            problems.extend(_retaliation_problems(state, pokemon, effect, where))  # v0.12
        if isinstance(effect, NextTurnAttackDamage):
            problems.extend(_next_turn_attack_damage_problems(state, pokemon, effect, where))  # v0.27
        problems.extend(_persistent_effect_log_problems(state, pokemon, effect, where))
    return problems


def _retaliation_problems(state: GameState, pokemon: PokemonInPlay, effect: Retaliation, where: str) -> list[str]:
    """「ほのおのかべ」（v0.12）・「こうらがえし」（v0.13）の持続する効果の、ワザの位置と与えるダメージの決め方・量が、このポケモンの
    カードの登録されたワザと合うか（登録された実装の ``retaliation_terms``。「ほのおのかべ」は (``fixed``, 10)、「こうらがえし」は
    (``received_damage``, None)）。"""
    if type(effect.attack_index) is not int or (effect.amount is not None and type(effect.amount) is not int):
        return [f"{where} {effect!r} のワザの位置・与えるダメージが整数ではない"]
    definition = state.card_def(pokemon.card)
    if not 0 <= effect.attack_index < len(definition.attacks):
        return [f"{where} {effect!r} のワザの位置が、カード {definition.id} のワザではない"]
    entry = state.effects.attack_entry(definition.id, effect.attack_index)
    terms = getattr(entry.effect, "retaliation_terms", None) if entry is not None else None
    if terms is None or terms() != (effect.basis, effect.amount):
        return [f"{where} {effect!r} が、カード {definition.id} の {effect.attack_index} 番目のワザ（登録された実装）の効果と合わない"]
    return []


def _next_turn_attack_damage_problems(state: GameState, pokemon: PokemonInPlay, effect: NextTurnAttackDamage, where: str) -> list[str]:
    """「つるぎのまい」（v0.27）の持続する効果の、効果を与えたワザの位置・ダメージが変わるワザの位置・変えたあとのダメージが、このポケモンの
    カードの登録されたワザと合うか（登録された実装の ``next_turn_terms``。「つるぎのまい」は (1, 60)）。"""
    fields = (effect.attack_index, effect.target_attack_index, effect.amount)
    if any(type(value) is not int for value in fields):
        return [f"{where} {effect!r} のワザの位置・ダメージが整数ではない"]
    definition = state.card_def(pokemon.card)
    if not 0 <= effect.attack_index < len(definition.attacks):
        return [f"{where} {effect!r} のワザの位置が、カード {definition.id} のワザではない"]
    entry = state.effects.attack_entry(definition.id, effect.attack_index)
    terms = getattr(entry.effect, "next_turn_terms", None) if entry is not None else None
    if terms is None or terms() != (effect.target_attack_index, effect.amount):
        return [f"{where} {effect!r} が、カード {definition.id} の {effect.attack_index} 番目のワザ（登録された実装）の効果と合わない"]
    return []


def _persistent_effect_log_problems(state: GameState, pokemon: PokemonInPlay, effect, where: str) -> list[str]:
    """持続する効果が、それを与えたログ（``persistent_effect_added``）と対応し、そのあとに消したはずのイベントがないか（v0.4b）。"""
    for event in reversed(state.log):
        kind = event["kind"]
        if kind == "persistent_effect_added":
            if (
                event.get("pokemon_id") == pokemon.pokemon_id
                and event.get("persistent_effect") == effect.kind
                and event["turn"] == effect.created_turn
                and event.get("active_turn") == effect.active_turn
                and event.get("source_card") == effect.source_card
            ):
                return []
            continue
        if (
            kind == "persistent_effect_removed"
            and event.get("pokemon_id") == pokemon.pokemon_id
            and event.get("persistent_effect") == effect.kind
            # v0.27: 同じ効果（与えた番・はたらく番）を消したログ。「つるぎのまい」は、はたらく番にもう一度使うと、新しい効果を与えたあとに
            # 前の効果が期限で消える（同じ種類の別の効果を消したログが、新しい効果を与えたログのあとにある）
            and event.get("created_turn") == effect.created_turn
            and event.get("active_turn") == effect.active_turn
        ):
            return [f"{where} {effect!r} が、消したあと（ログ persistent_effect_removed）にも残っている"]
        if kind == "evolve" and event.get("pokemon_id") == pokemon.pokemon_id:
            return [f"{where} {effect!r} が、進化（ログ evolve）の前の効果のまま残っている（p.310・p.323）"]
        if (kind == "retreat" and event.get("old_active") == pokemon.card) or (
            kind in ("switch", "forced_switch") and event.get("old_active_pokemon_id") == pokemon.pokemon_id  # forced_switch は v0.4d
        ):
            return [f"{where} {effect!r} が、ベンチに戻った（ログ {kind}）あとにも残っている（p.311・p.322）"]
    return [f"{where} {effect!r} に対応するログ persistent_effect_added がない"]


def _retreat_failure_problems(state: GameState, player: int, pokemon: PokemonInPlay) -> list[str]:
    """こんらん状態で「にげる」に失敗した記録（``PokemonInPlay.retreat_failed_turn``。v0.3c。p.311）の整合。

    v0.3d で、記録が今の番のログの ``retreat_failed``（同じ ``pokemon_id``）と対応することも確かめる（失敗していない
    ポケモンに記録が付いていない。特殊状態を消す処理（ポケモンいれかえなど）が記録を書きかえない前提の確認）。
    v0.4a で、その ``retreat_failed`` が、同じポケモンの進化（ログ ``evolve``）より後であることも確かめる（進化で記録を消す）。
    """
    failed = pokemon.retreat_failed_turn
    if failed is None:
        return []
    where = f"ポケモン {pokemon.pokemon_id} の「にげる」に失敗した番 {failed!r}"
    if state.phase in SETUP_PHASES or type(failed) is not int:
        return [f"{where} が正しくない（{state.phase.value}）"]
    if failed != state.turn_number or player != state.current_player:
        return [f"{where} が今の番（{state.turn_number} 番、プレイヤー {state.current_player!r}）の持ち主の記録ではない（番の終わりに消す）"]
    recent = _events_since_turn_start(state)
    if any(event["kind"] == "turn_end" for event in recent):
        return [f"{where} が番の終わりのあとに残っている"]
    for event in recent:  # 新しい順
        if event.get("pokemon_id") != pokemon.pokemon_id:
            continue
        if event["kind"] == "retreat_failed":
            return []
        if event["kind"] == "evolve":
            # 進化したポケモンは別のポケモンなので、進化の前の失敗の記録は消している（v0.4a。p.310）
            return [f"{where} が、進化（ログ evolve）の前の失敗の記録のまま残っている"]
    return [f"{where} に対応する、今の番の「にげる」の失敗（ログ retreat_failed）がない"]


def _counter_knocked_out_attacker_awaiting(state: GameState, player: int, pokemon: PokemonInPlay) -> bool:
    """v0.10: ワザの途中の決定（相手が答える「ふきとばし」の入れ替えなど）を待つ間だけ、そのワザを使ったポケモンは、相手の「はんげき」の
    ダメージで HP 以上になっていても場に残る（きぜつの処理はワザの要素をすべて処理したあと。p.309・p.89。docs/counterattack-v0.10.md
    の C16・C30）。ほかのポケモン・ほかの段階・決定のないときは、これまでどおり HP 以上のダメージで場に残ることを許さない。

    決定の続きの情報（``context`` の ``"use"``）がこのポケモンを指し、今の番のログで、最後のワザの宣言（``attack``）のあとに、このポケモンを
    HP 以上にした「はんげき」（``counterattack`` の ``knocked_out``）があることを確かめる（印や一覧を状態に加えない）。

    v0.12: 相手の R団のファイヤーの「ほのおのかべ」のダメージ（ログ ``damage`` の ``retaliation``。このポケモンの番号で、今のダメージ）で
    HP 以上になった場合も同じ（「ほのおのかべ」のダメージもダメージの処理のあと、効果の前。p.89 の「ふきとばし」の例。W23）。"""
    d = state.decision
    if state.phase is not Phase.DECISION or d is None or d.resume != "attack":
        return False
    use = d.context_value("use")
    if not isinstance(use, tuple) or len(use) < 2 or (use[0], use[1]) != (player, pokemon.pokemon_id):
        return False
    for event in _events_since_turn_start(state):  # 新しい順
        if event["kind"] == "attack":
            return False
        if event["kind"] == "counterattack" and event["attacker_pokemon_id"] == pokemon.pokemon_id and event["knocked_out"]:
            return True
        if (event["kind"] == "damage" and event.get("retaliation") and event.get("pokemon_id") == pokemon.pokemon_id
                and event.get("total_damage") == pokemon.damage):
            return True
    return False


def _attack_damage_awaiting(state: GameState, player: int, pokemon: PokemonInPlay) -> bool:
    """v0.31: ワザの途中の決定（再開先 ``"attack"``）を待つ間だけ、同じワザのダメージの要素で HP 以上になったポケモンは場に残る（きぜつの処理は
    ワザの要素をすべて処理したあと。p.309）。v0.30 までの対応カードでは、ダメージのあとに決定を出すワザ（ふきとばし）は、相手がきぜつすれば
    決定を出さなかったので起こらなかった。v0.31 のワザ（れんぞくファイヤーボール・ひばしら・エナジーボムなど）は、相手がきぜつしても自分の
    エネルギーをトラッシュする・つけかえるので、その決定を待つ間に起こる。

    今の番のログで、最後のワザの宣言（``attack``）のあとに、このポケモン（持ち主・いちばん上のカード）が受けたワザのダメージ（``damage``）が
    あり、その ``total_damage`` が今のダメージと同じことを確かめる（印や一覧を状態に加えない）。ほかの段階・決定のないときは許さない。"""
    d = state.decision
    if state.phase is not Phase.DECISION or d is None or d.resume != "attack":
        return False
    for event in _events_since_turn_start(state):  # 新しい順
        if event["kind"] == "attack":
            return False
        if (event["kind"] == "damage" and event.get("player") == player and event.get("pokemon") == pokemon.card
                and event.get("total_damage") == pokemon.damage):
            return True
    return False


def _ko_prevention_awaiting(state: GameState, player: int, pokemon: PokemonInPlay) -> bool:
    """v0.11: 「こんじょう」を使うかの決定（``KO_PREVENTION``。再開先 ``"knock_out"``）を待つ間だけ、HP 以上のダメージのポケモンが場に
    残る（きぜつの判定から、実際のきぜつの処理までのあいだ。docs/ko-prevention-v0.11.md）。許すのは、

    - 決定の対象のポケモン（決定するプレイヤーの、選べるもののポケモン。形・ログは ``_ko_prevention_decision_problems`` が確かめる）と、
    - 同じワザで HP 以上になったワザを使ったポケモン（決定の ``"attack"`` が指すポケモンで、今の番の最後のワザの宣言のあとの、自分への
      ダメージ（``damage`` の ``target`` が ``self``）か「はんげき」（``counterattack``）で、今のダメージになっている）。

    ほかのポケモン・ほかの段階・決定のないときは、これまでどおり許さない。"""
    d = state.decision
    if state.phase is not Phase.DECISION or d is None or d.resume != "knock_out":
        return False
    if player == d.player and pokemon.pokemon_id in d.options:
        return True
    attack = d.context_value("attack")
    if not isinstance(attack, tuple) or len(attack) != 4 or (attack[0], attack[1]) != (player, pokemon.pokemon_id):
        return False
    for event in _events_since_turn_start(state):  # 新しい順
        if event["kind"] == "attack":
            return False
        if (event["kind"] == "damage" and event.get("target") == "self" and event.get("pokemon_id") == pokemon.pokemon_id) or (
            event["kind"] == "counterattack" and event.get("attacker_pokemon_id") == pokemon.pokemon_id
        ):
            return event.get("total_damage") == pokemon.damage
    return False


def _ko_prevention_decision_problems(state: GameState, d) -> list[str]:
    """「こんじょう」を使うかの決定（v0.11。``KO_PREVENTION``・再開先 ``"knock_out"``）の整合性。

    - 種類と再開先の組、選ぶ数（0〜1）、選べるもの（ポケモン 1 匹）、決定するのはワザを使われた側（番でないプレイヤー）。v0.12 から、
      番のプレイヤーのワザを使ったポケモンが、相手の「ほのおのかべ」のダメージ（ログ ``damage`` の ``retaliation``）で HP 以上になった
      場合は、番のプレイヤーが決定する（対象はワザを使ったポケモン）。
    - ``"attack"``（ワザ）: 番のプレイヤーのバトル場のポケモンで、いちばん上のカードがそのカード。今の番にそのワザのログ ``attack`` が
      ちょうど 1 回。
    - 対象のポケモン: 決定するプレイヤーの場にいて、いちばん上のカードの ``"power"`` の位置に「こんじょう」（``PreventKnockOutOnHeads``）が
      登録され、HP 以上のダメージ、今ねむり・マヒ・こんらんでない（ダメージを受けたあとにワザの効果で特殊状態を変えるワザは、G37 で
      止めているので、今の特殊状態はダメージを受けたときと同じ）、かがくへんかガスに消されていない（G31）。
    - ログ: 今の番の最後のワザの宣言のあとに、対象のポケモンがワザのダメージを受けて今のダメージになった ``damage`` があり、そのあとに
      きぜつ・「こんじょう」の宣言や結果がない（同じきぜつの判定で 2 度決めさせない。G14）。
    """
    problems = []
    if d.kind != KO_PREVENTION or d.resume != "knock_out":
        return [f"決定 {d.kind} の再開先 {d.resume!r} が合わない（「こんじょう」の決定は ko_prevention・knock_out の組）"]
    if (d.min_choices, d.max_choices) != (0, 1) or len(d.options) != 1:
        problems.append(f"「こんじょう」の決定の選ぶ数 {d.min_choices}〜{d.max_choices}・選べるもの {d.options} が正しくない（0〜1 個・1 匹）")
    attack = d.context_value("attack")
    by_attacker = d.player == state.current_player  # v0.12: 「ほのおのかべ」のダメージで HP 以上になったワザを使ったポケモン
    if d.player not in PLAYERS or (by_attacker and not (isinstance(attack, tuple) and len(attack) == 4 and d.options == (attack[1],))):
        problems.append(
            f"「こんじょう」の決定をするのがプレイヤー {d.player}（ワザを使われた側 {1 - state.current_player!r}、または「ほのおのかべ」を"
            "受けたワザを使ったポケモンの持ち主のはず）"
        )
    power = d.context_value("power")
    if not (isinstance(attack, tuple) and len(attack) == 4 and isinstance(power, tuple) and len(power) == 2):
        return problems + [f"「こんじょう」の決定の続きの情報 {attack!r}・{power!r} が正しくない"]
    player, pokemon_id, card_id, attack_index = attack
    found = state.find_pokemon(pokemon_id)
    if player != state.current_player or found is None or found[0] != player or state.players[player].active is not found[1]:
        return problems + [f"「こんじょう」の決定のワザ {attack!r} が、番のプレイヤーのバトル場のポケモンのワザではない"]
    attacker = found[1]
    if state.cards[attacker.card].card_id != card_id:
        problems.append(f"「こんじょう」の決定のワザのカード id {card_id} が、ワザを使ったポケモン {pokemon_id} のカードと違う")
    events = _events_since_turn_start(state)  # 新しい順
    attacks = [event for event in events if event["kind"] == "attack" and event.get("player") == player]
    if len(attacks) != 1 or attacks[0].get("pokemon") != attacker.card or attacks[0].get("attack_index") != attack_index:
        problems.append(f"「こんじょう」の決定のワザ {attack!r} に対応する、今の番のワザのログ attack がない（{len(attacks)} 回）")
    target = state.find_pokemon(d.options[0]) if len(d.options) == 1 else None
    if target is None or target[0] != d.player:
        return problems + [f"「こんじょう」の決定の対象 {d.options} が、決定するプレイヤー {d.player} の場のポケモンではない"]
    pokemon = target[1]
    found_power = ko_prevention_power(state, pokemon)
    if found_power is None or found_power[0] != PowerKey(*power):
        return problems + [f"「こんじょう」の決定の特殊能力 {power!r} が、ポケモン {pokemon.pokemon_id} のいちばん上のカードの「こんじょう」ではない"]
    key, effect = found_power
    if pokemon.damage < state.card_def(pokemon.card).hp:
        problems.append(f"「こんじょう」の決定の対象のポケモン {pokemon.pokemon_id} が HP 以上のダメージを受けていない")
    if not effect.is_able(pokemon):
        problems.append(f"「こんじょう」の決定の対象のポケモン {pokemon.pokemon_id} がねむり・マヒ・こんらん（使えない。G25〜G27）")
    if ko_prevention_suppressors(state, pokemon, key):
        problems.append(f"「こんじょう」の決定の対象のポケモン {pokemon.pokemon_id} の特殊能力が、かがくへんかガスに消されている（G31）")
    received = None
    for event in events:
        if event["kind"] == "attack":
            break
        if event["kind"] in ("knock_out", "ko_prevention_declined", "ko_prevention_declared", "ko_prevented", "ko_prevention_failed"):
            problems.append(f"「こんじょう」の決定の前に、同じワザのあとの {event['kind']} がある（同じきぜつの判定で 2 度決めさせない）")
        if (received is None and event["kind"] == "damage" and event.get("player") == d.player and event.get("pokemon") == pokemon.card
                and event.get("target", "opponent_active") == "opponent_active" and bool(event.get("retaliation")) == by_attacker):
            received = event
    if received is None or received.get("total_damage") != pokemon.damage:
        problems.append(f"「こんじょう」の決定の対象のポケモン {pokemon.pokemon_id} が、今の番のワザのダメージで今のダメージになったログがない")
    return problems


def _post_knockout_candidate_problems(state: GameState, candidates) -> list[str]:
    """サイドを取る決定の ``context`` の ``"post_knockout"``（「ふしちょう」の候補。v0.12）の整合性。

    形（(持ち主, カードの uid, カード id, パワーの位置) が 1 つ）と、そのカードが持ち主のトラッシュにあり、そのパワーの位置に「ふしちょう」
    （``ReturnToHandOnKnockOut``）が登録され、直前のきぜつ（ログ ``knock_out``。サイドを取る決定の前の、きぜつ・取ったサイドの並び）の
    ポケモンのカードであること。特殊状態・かがくへんかガスはきぜつしたあとの状態からは確かめられない（ログの監査が組み立て直して確かめる）。
    """
    if not (isinstance(candidates, tuple) and len(candidates) == 1 and isinstance(candidates[0], tuple) and len(candidates[0]) == 4):
        return [f"「ふしちょう」の候補 {candidates!r} の形が正しくない（(持ち主, カード, カード id, パワーの位置) が 1 つ）"]
    owner, card, card_id, power_index = candidates[0]
    problems = _post_knockout_card_problems(state, owner, card, card_id, power_index)
    knocked = []
    for event in reversed(state.log):
        kind = event["kind"]
        if kind == "take_prize" and not knocked:
            continue
        if kind == "knock_out":
            knocked.append(event.get("pokemon"))
        elif kind == "persistent_effect_removed" and event.get("reason") == KNOCK_OUT:
            continue
        else:
            break
    if card not in knocked:
        problems.append(f"「ふしちょう」の候補のカード {card} が、直前にきぜつしたポケモン {tuple(knocked)} のカードではない")
    return problems


def _post_knockout_card_problems(state: GameState, owner, card, card_id, power_index) -> list[str]:
    """「ふしちょう」の候補・決定のカードが、持ち主のトラッシュにあり、そのパワーの位置に「ふしちょう」が登録されたカードか（v0.12）。"""
    if owner not in PLAYERS or card not in state.cards or state.cards[card].owner != owner:
        return [f"「ふしちょう」のカード {card!r} の持ち主 {owner!r} が正しくない"]
    problems = []
    if card not in state.players[owner].discard:
        problems.append(f"「ふしちょう」のカード {card} が、持ち主 {owner} のトラッシュにない")
    definition = state.card_def(card)
    if definition.id != card_id or not isinstance(power_index, int) or not 0 <= power_index < len(definition.powers):
        return problems + [f"「ふしちょう」のパワー {card_id}@power{power_index!r} が、カード {card}（{definition.id}）のパワーではない"]
    effect = state.effects.power_effect(definition.id, definition.powers[power_index])
    if not isinstance(effect, ReturnToHandOnKnockOut):
        problems.append(f"「ふしちょう」のパワー {card_id}@power{power_index} に、きぜつしたときに使える特殊能力の実装が登録されていない")
    return problems


def _post_knockout_decision_problems(state: GameState, d) -> list[str]:
    """「ふしちょう」を使うかの決定（v0.12。``POST_KNOCKOUT_POWER``・再開先 ``"post_knockout"``）の整合性。

    - 種類と再開先の組、選ぶ数（0〜1）、選べるもの（カード 1 枚）。決定するのはそのカードの持ち主（番のプレイヤーでもよい。きぜつの
      原因を問わない）。
    - ``"power"``: そのカードの、そのパワーの位置に「ふしちょう」が登録されている。カードは持ち主のトラッシュにある。
    - 対戦は続いている（勝ち負けが決まる場合は決めさせない。解決の基盤の ``flow._next_prize_or_judge``）。かがくへんかガスに消されていない（P18）。
    - ログ: 最後のきぜつ（``knock_out``）のどれかがこのカードで、そのあとは取ったサイド（``take_prize``）だけ（同じきぜつで 2 度決めさせない。
      バトル場に出すのはこの決定のあと）。
    """
    if d.kind != POST_KNOCKOUT_POWER or d.resume != "post_knockout":
        return [f"決定 {d.kind} の再開先 {d.resume!r} が合わない（「ふしちょう」の決定は post_knockout_power・post_knockout の組）"]
    problems = []
    if (d.min_choices, d.max_choices) != (0, 1) or len(d.options) != 1:
        return [f"「ふしちょう」の決定の選ぶ数 {d.min_choices}〜{d.max_choices}・選べるもの {d.options} が正しくない（0〜1 個・カード 1 枚）"]
    power = d.context_value("power")
    if not (isinstance(power, tuple) and len(power) == 2):
        return [f"「ふしちょう」の決定の続きの情報 {power!r} が正しくない"]
    card = d.options[0]
    card_id, power_index = power
    problems.extend(_post_knockout_card_problems(state, d.player, card, card_id, power_index))
    if problems:
        return problems
    definition = state.card_def(card)
    if suppressors_of(state, definition.powers[power_index]):
        problems.append(f"「ふしちょう」の決定のカード {card} の特殊能力が、かがくへんかガスに消されている（P18）")
    knocked = []
    for event in reversed(state.log):
        kind = event["kind"]
        if kind == "take_prize" and not knocked:
            continue
        if kind == "knock_out":
            knocked.append(event.get("pokemon"))
        elif kind == "persistent_effect_removed" and event.get("reason") == KNOCK_OUT:
            continue
        else:
            break
    if card not in knocked:
        problems.append(f"「ふしちょう」の決定のカード {card} が、直前にきぜつしたポケモン {tuple(knocked)} のカードではない（ログ）")
    return problems


def _events_since_turn_start(state: GameState) -> list:
    """最後の ``turn_start`` より後のログ（新しい順）。``turn_start`` がなければログ全体。"""
    recent = []
    for event in reversed(state.log):
        if event["kind"] == "turn_start":
            break
        recent.append(event)
    return recent


def _power_attachment_problems(state: GameState) -> list[str]:
    """この番にポケモンパワーで手札からつけたエネルギーの数（v0.6。``energy_attached_by_powers_this_turn``）。

    0 以上の整数で、今の番（最後の ``turn_start`` のあと）のログの ``power_attach_energy`` の数と同じ（番の最初に 0 にし、
    「あまごい」で 1 枚つけるごとに 1 増やすので）。対戦準備の段階（番がまだない）では 0。ログは記録で、エンジンはこの数を
    ログから決めない（ここでは、状態とログが食い違っていないかだけを確かめる）。
    """
    count = state.energy_attached_by_powers_this_turn
    if type(count) is not int or count < 0:
        return [f"この番にポケモンパワーでつけたエネルギーの数 {count!r} が正しくない"]
    logged = 0
    for event in reversed(state.log):
        if event["kind"] == "turn_start":
            break
        if event["kind"] == "power_attach_energy":
            logged += 1
    if count != logged:
        return [f"この番にポケモンパワーでつけたエネルギーの数 {count} が、今の番のログの power_attach_energy の数 {logged} と違う"]
    return []


def _turn_power_problems(state: GameState) -> list[str]:
    """v0.31（形式 10）: この番に使った「自分の番ごとに1回使える」特殊能力（``power_uses_this_turn``）と、「エナジーバーン」で「炎」エネルギーに
    なったエネルギーカード（``energy_burn``）の整合。

    - ``power_uses_this_turn``: (場のポケモンの番号, 特殊能力の位置) の重ならない並びで、今の番のログに、その番号・位置の ``pokemon_power`` があり、
      その特殊能力の実装が回数の制限のあるもの（``once_per_turn``）。今の番のそのような宣言のログの数と同じ。
    - ``energy_burn``: (場のポケモンの番号, エネルギーカードの uid) の重ならない並びで、今の番のログに、その番号の ``energy_burn``（uid を含む）がある。
      番の終わり（ログ ``turn_end``）のあとには残らない。
    """
    problems: list[str] = []
    uses = state.power_uses_this_turn
    burn = state.energy_burn
    if not isinstance(uses, tuple) or not isinstance(burn, tuple):
        return [f"この番の特殊能力の記録 {uses!r}・{burn!r} がタプルではない"]
    recent = _events_since_turn_start(state)
    limited = []
    for event in recent:
        if event["kind"] != "pokemon_power" or event.get("pokemon") not in state.cards:
            continue
        definition = state.card_def(event["pokemon"])  # 使ったときのいちばん上のカード（そのあと進化しても、使った記録は残る）
        index = event.get("power_index")
        if isinstance(index, int) and 0 <= index < len(definition.powers):
            effect = state.effects.power_effect(definition.id, definition.powers[index])
            if getattr(effect, "once_per_turn", False):
                limited.append((event.get("pokemon_id"), index))
    if len(set(uses)) != len(uses) or sorted(limited) != sorted(uses):
        problems.append(f"この番に使った回数の制限のある特殊能力 {uses} が、今の番のそのような宣言のログ {limited} と合わない")
    burned = {(e.get("pokemon_id"), uid) for e in recent if e["kind"] == "energy_burn" for uid in e.get("energies", ())}
    if len(set(burn)) != len(burn) or not set(burn) <= burned:
        problems.append(f"「炎」エネルギーになったエネルギー {burn} が、今の番のログの energy_burn {sorted(burned)} と合わない")
    if burn and any(e["kind"] == "turn_end" for e in recent):
        problems.append(f"「炎」エネルギーになったエネルギー {burn} が、番の終わりのあとに残っている（自分の番の終わりにもとにもどる）")
    for pid, uid in burn:
        if uid not in state.cards or not state.card_def(uid).is_basic_energy:
            problems.append(f"「炎」エネルギーになったカード {uid!r} が基本エネルギーカードではない")
    return problems


def _progress_problems(state: GameState) -> list[str]:
    """番の進行とポケモンチェックの整合（v0.3a）。ログの最後の 2 つの ``turn_start`` から後ろだけを見る。

    - 今の番の番号と番のプレイヤーが、最後の ``turn_start`` の番とプレイヤーと同じ（v0.4e）。
    - 前の番の始まりから今の番の始まりまでに、``turn_end`` → ``pokemon_check`` がちょうど 1 回ずつ（p.309。
      ポケモンチェックを二度しない・飛ばさない）。
    - 今の番の始まりのあと: 番の途中（ワザのあとのサイド・交代の決定を含む）ならどちらもない。ポケモンチェックの
      途中の決定（``context`` の ``then`` が ``NEXT_TURN``）なら 1 回ずつ（次の番はまだ始まっていない）。
      終わった対戦は、どちらでもよい（番の途中・ポケモンチェックの中のどちらでも勝敗は決まる）。
    """
    log = state.log
    starts: list[int] = []
    i = len(log) - 1
    while i >= 0 and len(starts) < 2:
        if log[i]["kind"] == "turn_start":
            starts.append(i)
        i -= 1
    if not starts:
        return []

    def marks(begin: int, end: int) -> list[str]:
        return [log[j]["kind"] for j in range(begin, end) if log[j]["kind"] in ("turn_end", "pokemon_check")]

    problems = []
    last_start = log[starts[0]]
    if last_start.get("turn") != state.turn_number or last_start.get("player") != state.current_player:
        # 番は 1 つずつ交互に進み、番の番号と番のプレイヤーは番の始まりで決まる（p.309。v0.4e。番の番号を偶数だけずらした
        # 状態は、番のプレイヤーの確認だけでは見つからなかった）
        problems.append(
            f"今の番 {state.turn_number!r}（プレイヤー {state.current_player!r}）が、最後の番の始まり（ログ turn_start の"
            f" {last_start.get('turn')!r} 番、プレイヤー {last_start.get('player')!r}）と違う"
        )
    if len(starts) == 2 and marks(starts[1] + 1, starts[0]) != ["turn_end", "pokemon_check"]:
        problems.append(f"番と番のあいだの番の終わり・ポケモンチェックが {marks(starts[1] + 1, starts[0])}（1 回ずつ、この順のはず）")
    tail = marks(starts[0] + 1, len(log))
    d = state.decision
    if state.phase in TERMINAL_PHASES:
        allowed = ([], ["turn_end", "pokemon_check"])
    elif d is not None and d.context_value("then") == NEXT_TURN:
        allowed = (["turn_end", "pokemon_check"],)
    else:
        allowed = ([],)
    if tail not in allowed:
        problems.append(f"{state.phase.value} なのに、今の番のあとの番の終わり・ポケモンチェックが {tail}")
    return problems


def _decision_problems(state: GameState) -> list[str]:
    """保留中の決定と段階・場の形の整合性。"""
    problems: list[str] = []
    phase = state.phase
    d = state.decision
    if phase not in DECISION_PHASES:
        if d is not None:
            problems.append(f"{phase.value} なのに、決定が残っている")
        return problems
    if d is None:
        if phase is Phase.TAKE_PRIZE:
            problems.append("サイドを取る段階なのに、サイドを取るプレイヤーがいない")
        elif phase is Phase.PROMOTE_ACTIVE:
            problems.append("バトル場に出す段階なのに、出すプレイヤーがいない")
        else:
            problems.append("決定を待つ段階なのに、決定がない")
        return problems
    if phase_for(d.kind) is not phase:
        problems.append(f"決定の種類 {d.kind} と段階 {phase.value} が合わない")
    if d.player not in PLAYERS:
        problems.append(f"決定するプレイヤー {d.player!r} が正しくない")
        return problems
    if not 1 <= d.id < state.next_decision_id:
        problems.append(f"決定の番号 {d.id} が正しくない（次に付ける番号 {state.next_decision_id}）")
    # 選ぶ数の上限は選べるものの数を超えてよい（「2 匹まで選ぶ」で 1 匹しかいない場合）。下限は選べる数まで
    if len(set(d.options)) != len(d.options) or not 0 <= d.min_choices <= d.max_choices or d.min_choices > len(d.options):
        problems.append(f"決定の選べるもの {d.options} と選ぶ数 {d.min_choices}〜{d.max_choices} が合わない")
    if d.resume not in DECISION_RESUMES:
        problems.append(f"決定の再開先 {d.resume!r} がない")
    remaining = d.context_value("remaining", ())
    then = d.context_value("then")
    if (d.kind in (TAKE_PRIZE, PROMOTE_ACTIVE) or d.resume in (TAKE_PRIZE, PROMOTE_ACTIVE)) and d.resume != d.kind:
        # v0.1 からある種類の決定は、その種類の再開先で続ける（v0.4e。それまではポケモンチェックの中の決定だけ確かめていた）
        problems.append(f"決定 {d.kind} の再開先 {d.resume!r} が種類と合わない")
    if d.kind in (TAKE_PRIZE, PROMOTE_ACTIVE) and (d.min_choices, d.max_choices) != (1, 1):
        problems.append(f"決定 {d.kind} で選ぶ数が {d.min_choices}〜{d.max_choices}（サイド 1 枚・ポケモン 1 匹のはず。p.312・p.313）")
    if then is not None:
        # ポケモンチェックの中のきぜつのあとの決定（v0.3a）。サイド・交代（v0.12 から「ふしちょう」も）だけで、交代は 1 人だけ
        # （両方のバトル場が空になる場合は、出す順番が決まらないので止めている）
        kinds = {TAKE_PRIZE: TAKE_PRIZE, PROMOTE_ACTIVE: PROMOTE_ACTIVE, POST_KNOCKOUT_POWER: "post_knockout"}
        if then != NEXT_TURN or kinds.get(d.kind) != d.resume:
            problems.append(f"決定 {d.kind} の続き {then!r} が正しくない")
        if d.kind == PROMOTE_ACTIVE and remaining:
            problems.append(f"ポケモンチェックのあとにバトル場に出すプレイヤーが複数いる {(d.player, *remaining)}")
    if d.kind == TAKE_PRIZE:
        prizes = state.players[d.player].prizes
        queue = (d.player, *remaining)
        if d.options != tuple(range(len(prizes))):
            problems.append(f"サイドを取る決定の選べる位置 {d.options} が、サイドの枚数 {len(prizes)} と合わない")
        for player in PLAYERS:
            if queue.count(player) > len(state.players[player].prizes):
                problems.append(f"プレイヤー {player} がサイドを取る回数が、残りのサイドより多い")
        if any(player not in PLAYERS for player in remaining):
            problems.append(f"サイドを取るプレイヤーの並び {queue} が正しくない")
        else:
            problems.extend(_prize_queue_problems(state, queue))
        candidates = d.context_value("post_knockout")
        if candidates is not None:
            problems.extend(_post_knockout_candidate_problems(state, candidates))  # v0.12
    elif d.context_value("post_knockout") is not None:
        problems.append(f"サイドを取る決定でない {d.kind} に、「ふしちょう」の候補が書かれている")
    if d.kind == PROMOTE_ACTIVE:
        queue = (d.player, *remaining)
        for player in queue:
            if player not in PLAYERS or state.players[player].active is not None or not state.players[player].bench:
                problems.append(f"バトル場に出すプレイヤー {player} の場の形が正しくない")
        if len(queue) > 1 and queue != (1 - state.current_player, state.current_player):
            # 両方が出すときは、今が番でないプレイヤーが先（pp.323〜324。解決の基盤の flow._promotions_after_judge。v0.4e）
            problems.append(f"バトル場に出す順番 {queue} が、番でないプレイヤー {1 - state.current_player!r} からではない（pp.323〜324）")
        for player in PLAYERS:
            if player not in queue and state.players[player].active is None:
                problems.append(f"プレイヤー {player} のバトル場にポケモンがいないのに、出す順番に入っていない")
        if d.options != tuple(pokemon.pokemon_id for pokemon in state.players[d.player].bench):
            problems.append(f"バトル場に出す決定の選べるもの {d.options} が、ベンチのポケモンと合わない")
    if d.resume == "attack":
        problems.extend(_attack_decision_problems(state, d))
    if d.kind == KO_PREVENTION or d.resume == "knock_out":
        problems.extend(_ko_prevention_decision_problems(state, d))  # v0.11
    if d.kind == POST_KNOCKOUT_POWER or d.resume == "post_knockout":
        problems.extend(_post_knockout_decision_problems(state, d))  # v0.12
    # 選べるもののうち原典で扱いを決められないもの（v0.2b）: 選べるものの中にあり、残りで答えられる
    unresolved = d.context_value("unresolved_choices", ())
    if unresolved:
        if not set(unresolved) <= set(d.options):
            problems.append(f"扱いを決められない選択 {unresolved} が、選べるもの {d.options} にない")
        if len(set(d.options) - set(unresolved)) < max(d.min_choices, 1):
            problems.append(f"決定 {d.kind} に、扱いを決められる選択が足りない（答えられない）")
    return problems


def _prize_queue_problems(state: GameState, queue: tuple[int, ...]) -> list[str]:
    """サイドを取るプレイヤーの並び（決定するプレイヤーと残り。v0.4e）が、直前のきぜつから決まるか。

    解決の基盤の ``flow._after_knockouts``: きぜつ 1 匹につき、きぜつしたポケモンの相手側のプレイヤーが 1 枚（p.323）。残りのサイドより多くは
    取らない。ログの終わりから、取ったサイド（``take_prize``）・きぜつ（``knock_out``。あいだの ``persistent_effect_removed`` は
    きぜつで消えた持続する効果）の順に読み、取ったサイドと今の並びをあわせたものが、きぜつから決まる「だれが何枚取るか」と
    同じかを確かめる。同時のきぜつ（p.324）で両方が取る順番は番のプレイヤーが選べる（p.325。エンジンは番のプレイヤーからに
    正規化している。v0.2f）ので、順番は確かめない（正規化と違う順番の状態も、ルール上は正しい）。ログにきぜつがない状態は、
    盤面を直接作ったテスト専用の状態（``new_game`` からの対戦では違反）だけ。
    """
    taken: list[int] = []
    knocked: list[int] = []
    for event in reversed(state.log):
        kind = event["kind"]
        if kind == "take_prize" and not knocked:
            taken.append(event.get("player"))
        elif kind == "knock_out":
            knocked.append(event.get("player"))
        elif kind == "persistent_effect_removed" and event.get("reason") == KNOCK_OUT:
            continue
        else:
            break
    if not knocked:
        if any(state.decklists):
            return [f"サイドを取る決定 {queue} の前に、きぜつ（ログ knock_out）がない"]
        return []
    taken.reverse()
    knocked.reverse()
    budget = {player: len(state.players[player].prizes) + taken.count(player) for player in PLAYERS}
    expected = []
    for owner in knocked:
        taker = 1 - owner if owner in PLAYERS else None
        if taker in budget and budget[taker] > 0:
            expected.append(taker)
            budget[taker] -= 1
    if sorted(expected) != sorted((*taken, *queue)):
        return [
            f"サイドを取るプレイヤーの並び {queue}（取ったあと {tuple(taken)}）が、きぜつしたポケモンの持ち主 {tuple(knocked)} から"
            f"決まるサイドを取るプレイヤー {tuple(expected)} と違う（きぜつしたポケモンの相手側のプレイヤーが取る。p.323・p.324）"
        ]
    return []


def _attack_decision_problems(state: GameState, d) -> list[str]:
    """ワザの効果の途中の決定（``resume`` が ``"attack"``。v0.2a。v0.4d で強めた）の整合性。

    どのワザの決定にも共通: 続きの情報（``context`` の ``"use"`` = (プレイヤー, 場のポケモンの番号, カード id, ワザの位置)）が
    あり、ワザが効果の登録表にある。ワザを使ったプレイヤーは番のプレイヤー（相手が決定していても番は変わらない。v0.4d）で、
    ワザを使ったポケモンはそのプレイヤーのバトル場にいて、いちばん上のカードが続きの情報のカード id。今の番に、そのポケモンの
    そのワザのログ ``attack`` がちょうど 1 回ある（ワザは 1 番に 1 回。決定はワザの途中なので、番の終わりのログはまだない）。
    そのあとで、効果ごとの形（決定するプレイヤー・種類・選べるもの）を、ワザの実装の ``decision_problems`` で確かめる。
    """
    use = d.context_value("use")
    if not (isinstance(use, tuple) and len(use) == 4 and state.find_pokemon(use[1]) is not None):
        return [f"ワザの決定の続きの情報 {use!r} が正しくない"]
    player, pokemon_id, card_id, attack_index = use
    entry = state.effects.attack_entry(card_id, attack_index)
    if entry is None:
        return [f"ワザの決定の続きのワザ {card_id}#{attack_index} が効果の登録表にない"]
    owner, attacker = state.find_pokemon(pokemon_id)
    if player != state.current_player or owner != player or state.players[player].active is not attacker:
        return [f"ワザの決定の続きの情報 {use!r} が、番のプレイヤー {state.current_player!r} のバトル場のポケモンのワザではない"]
    if attacker.card not in state.cards or state.cards[attacker.card].card_id != card_id:
        return [f"ワザの決定の続きのカード id {card_id} が、ワザを使ったポケモン {pokemon_id} のカード {attacker.card} と違う"]
    attacks = [
        event for event in _events_since_turn_start(state)
        if event["kind"] == "attack" and event.get("player") == player
    ]
    if len(attacks) != 1 or attacks[0].get("pokemon") != attacker.card or attacks[0].get("attack_index") != attack_index:
        return [f"ワザの決定の続き {use!r} に対応する、今の番のワザのログ attack がない（{len(attacks)} 回）"]
    return entry.effect.decision_problems(state, AttackUse(player, pokemon_id, AttackKey(card_id, attack_index)), d)


def _attached_trainer_problems(state: GameState, player: int, pokemon: PokemonInPlay, place) -> list[str]:
    """ポケモンについているトレーナーカード（v0.2c）。

    ついているトレーナーは、そのポケモンのいる場所にある（p.313）ので、ポケモンの持ち主の場のカードとして
    数える。効果の登録表に、場に残る実装（``stays_in_play``）が登録されたトレーナーだけがつく。
    有効期限が過ぎたもの（番の終わりにトラッシュしていないもの）は残らない（終わった対戦は除く）。
    """
    problems: list[str] = []
    for attached in pokemon.trainers:
        place(attached.card, player, "場（ついているトレーナー）")
        if attached.card not in state.cards:
            continue
        definition = state.card_def(attached.card)
        if definition.category != "trainer":
            problems.append(f"トレーナーカードでないカード {attached.card} がトレーナーとしてポケモンについている")
            continue
        if attached.player != player:
            problems.append(f"ついているトレーナー {attached.card} の使ったプレイヤー {attached.player} が、ポケモンの持ち主 {player} と違う")
        entry = state.effects.trainer_entry(definition.id)
        if entry is None or not entry.effect.stays_in_play:
            problems.append(f"ついているトレーナー {attached.card}（{definition.id}）に、場に残る実装が登録されていない")
        if state.phase in TERMINAL_PHASES:
            continue
        if attached.discard_at_end_of_turn < state.turn_number:
            problems.append(f"ついているトレーナー {attached.card} の有効期限（{attached.discard_at_end_of_turn} 番の終わり）が過ぎている")
        elif entry is not None and entry.effect.stays_in_play:
            # 有効期限は、使った番 + discard_turn_offset（v0.2e）。使った番は今の番より後ではなく、使ったプレイヤーの番
            offset = entry.effect.discard_turn_offset
            used_on = attached.discard_at_end_of_turn - offset
            if used_on > state.turn_number:
                problems.append(
                    f"ついているトレーナー {attached.card} の有効期限（{attached.discard_at_end_of_turn} 番の終わり）が、"
                    f"今の番 {state.turn_number} から {offset} 番より先"
                )
            elif state.first_player in PLAYERS and turn_owner(state, used_on) != attached.player:
                problems.append(
                    f"ついているトレーナー {attached.card} を使った番（{used_on} 番）が、使ったプレイヤー {attached.player} の番ではない"
                )
    return problems


def _trainer_problems(state: GameState) -> list[str]:
    """使用中のトレーナー（v0.2b）と、決定・段階の整合性。

    トレーナーカードが使用中なのは、そのトレーナーの効果が決定を待っている間だけ（決定がなければ、
    説明にしたがい終わってトラッシュしている）。共通の確認（使用中のトレーナー・続きの情報・番のプレイヤー）のあとで、
    決定の形（決定するプレイヤー・種類・選ぶ数・選べるもの）を、トレーナーの実装の ``decision_problems`` で確かめる（v0.4e。
    それまでは確かめておらず、相手の場のポケモンが選べるものに入った壊れた状態を見つけられなかった）。
    """
    problems: list[str] = []
    used = state.trainer_in_use
    d = state.decision
    waiting = d is not None and d.resume == "trainer"
    if used is None:
        if waiting:
            problems.append("トレーナーの決定を待っているのに、使用中のトレーナーがない")
        return problems
    if not waiting:
        problems.append(f"使用中のトレーナー {used.card} があるのに、その効果の決定を待っていない")
        return problems
    if used.player != state.current_player:
        problems.append(f"使用中のトレーナーの持ち主 {used.player} が、番のプレイヤー {state.current_player} ではない")
    use = d.context_value("use")
    if not (isinstance(use, tuple) and len(use) == 3):
        problems.append(f"トレーナーの決定の続きの情報 {use!r} が正しくない")
        return problems
    player, card, card_id = use
    if (player, card) != (used.player, used.card):
        problems.append(f"トレーナーの決定の続きの情報 {use!r} が、使用中のトレーナー {used} と違う")
    if card in state.cards and state.cards[card].card_id != card_id:
        problems.append(f"トレーナーの決定の続きのカード id {card_id} が、カード {card} と違う")
    entry = state.effects.trainer_entry(card_id)
    if entry is None:
        problems.append(f"トレーナーの決定の続きのカード {card_id} が効果の登録表にない")
        return problems
    if not problems:
        # 効果ごとの決定の形（決定するプレイヤー・種類・選ぶ数・選べるもの。v0.4e。ワザの決定の decision_problems と同じ考え方）
        problems.extend(entry.effect.decision_problems(state, TrainerUse(player, card, card_id), d))
    return problems

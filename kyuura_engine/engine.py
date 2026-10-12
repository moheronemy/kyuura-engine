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

from . import judge
from .cards import CardPool, can_pay_cost, load_card_pool
from .commands import (
    UNSUPPORTED_COMMANDS,
    check_command_fields,
    AttachEnergy,
    DrawMulliganCards,
    EndTurn,
    PlaceStartingPokemon,
    PlayBasicToBench,
    PlayTrainer,
    PromoteActive,
    ReportJankenResult,
    ResolveDecision,
    Retreat,
    TakePrize,
    UseAttack,
)
from .decisions import DECISION_PHASES, PROMOTE_ACTIVE, TAKE_PRIZE, check_choices, phase_for, push_decision
from .effects import AttackKey, AttackUse, TrainerUse
from .deck import deck_problems
from .errors import DeckValidationError, IllegalActionError, StateIntegrityError, UnsupportedError
from .rules import RULES_2000_02_14, RuleSet
from .state import (
    TERMINAL_PHASES,
    CardInstance,
    DataSource,
    GameResult,
    GameState,
    Halt,
    Phase,
    PlayerState,
    PokemonInPlay,
    TrainerInUse,
    freeze_mapping,
)
from .zones import draw_cards

PLAYERS = (0, 1)
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
    state.rng.shuffle(state.players[player].deck)
    state.add_event("shuffle", player=player)


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
    """
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
    handler(new, command)
    _require_integrity(new)
    return new


def _require_integrity(state: GameState) -> None:
    """返す状態がカードの保存則・場の形を満たすことを確かめる。満たさなければ返さない。"""
    problems = check_invariants(state)
    if problems:
        raise StateIntegrityError(problems)


def _require_phase(state: GameState, *phases: Phase) -> None:
    if state.phase not in phases:
        names = ", ".join(p.value for p in phases)
        raise IllegalActionError("WRONG_PHASE", f"今は {state.phase.value}。この操作は {names} のときだけ")


def _require_player(player) -> int:
    if player not in PLAYERS:
        raise IllegalActionError("INVALID_PLAYER", f"プレイヤーは 0 か 1（{player!r}）")
    return player


def _require_turn(state: GameState, player) -> PlayerState:
    _require_phase(state, Phase.MAIN)
    _require_player(player)
    if player != state.current_player:
        raise IllegalActionError("NOT_YOUR_TURN", f"今はプレイヤー {state.current_player} の番")
    return state.players[player]


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
    """カードを場のポケモンにする。場のポケモンの番号を新しく付ける（前に使った番号は使わない）。"""
    pokemon = PokemonInPlay(uid, pokemon_id=state.next_pokemon_id)
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


def _begin_turn(state: GameState, player: int) -> None:
    """番の最初に山札から必ず 1 枚引く。引けなければその時点で負け（p.309）。"""
    state.turn_number += 1
    state.current_player = player
    state.energy_attachments_this_turn = 0
    state.phase = Phase.MAIN
    state.add_event("turn_start", player=player)
    if state.turn_number == 1 and not state.rules.first_player_draws_on_first_turn:
        return
    if not state.players[player].deck:
        state.add_event("deck_out", player=player)
        _finish(state, judge.deck_out(player))
        return
    _draw(state, player, 1)


def _end_turn(state: GameState) -> None:
    """番を終え、ポケモンチェックをして、相手の番にする（p.309）。

    番の終わりに、この番の終わりにトラッシュすると決めたついているトレーナー（プラスパワーなど）を
    トラッシュする（v0.2c）。ポケモンチェックはどちらの番でもない（p.323）ので、その前に行う。
    勝敗が決まって対戦が終わったとき（``_finish``）は番の終わりが来ないので、ここは通らない。
    """
    _discard_expired_attachments(state)
    state.add_event("turn_end", player=state.current_player)
    _pokemon_check(state)
    _begin_turn(state, 1 - state.current_player)


def _discard_expired_attachments(state: GameState) -> None:
    """有効期限（``AttachedTrainer.discard_at_end_of_turn``）が今の番のついているトレーナーをトラッシュする。

    番のプレイヤーの場（バトル場 → ベンチ）、相手の場の順。トラッシュにあるカードには順番がない（p.312）。
    """
    for owner in (state.current_player, 1 - state.current_player):
        for pokemon in state.players[owner].in_play():
            expired = [t for t in pokemon.trainers if t.discard_at_end_of_turn == state.turn_number]
            for attached in expired:
                pokemon.trainers.remove(attached)
                state.players[attached.player].discard.append(attached.card)
                state.add_event(
                    "discard_attached_trainer",
                    player=attached.player,
                    card=attached.card,
                    pokemon=pokemon.card,
                    pokemon_id=pokemon.pokemon_id,
                    reason="end_of_turn",
                )


def _pokemon_check(state: GameState) -> None:
    """ポケモンチェック（p.323）: 指示されたこと → どく → ねむり → マヒ。

    v0.1 の対応カードには、特殊状態にするワザも「ポケモンチェックで〜する」効果もないので、
    ここで処理することはない。特殊状態を加えるときは、ここに順番どおりに加える。
    """
    state.add_event("pokemon_check")


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


def _attach_energy(state: GameState, cmd: AttachEnergy) -> None:
    """エネルギーカードを 1 番に 1 枚、自分の場のポケモンにつける（p.310）。"""
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
    p.hand.remove(cmd.energy)
    target.energy.append(cmd.energy)
    state.energy_attachments_this_turn += 1
    state.add_event("attach_energy", player=cmd.player, energy=cmd.energy, target=cmd.target)


def _retreat(state: GameState, cmd: Retreat) -> None:
    """にげる（pp.310-311）。1 番に何度でも。控えがいなければ宣言できない。

    にげるエネルギーの数ぶん、そのポケモンについているエネルギーを選んでトラッシュし、控えと入れ替える。
    v0.1 では特殊状態がないので、ねむり・マヒ・こんらんの確認はない。
    """
    p = _require_turn(state, cmd.player)
    active = p.active
    if not p.bench:
        raise IllegalActionError("NO_BENCH", "控えポケモンがいないので、にげるを宣言できない")
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
    # ついているカード・ダメージはいっしょに移動する（p.311）
    p.active, p.bench[index] = p.bench[index], active
    state.add_event("retreat", player=cmd.player, discarded=discard, old_active=active.card, new_active=cmd.new_active)


def _use_attack(state: GameState, cmd: UseAttack) -> None:
    """ワザを使う（p.309「バトル場にいるポケモンのワザを使う」、p.320、p.321）。

    ワザの処理は、効果の登録表（``state.effects``）に登録された実装が行う。登録がないワザは使えない。
    処理が終わったら（決定待ちがなければ）、きぜつ・サイド・交代のあと、自分の番は自動的に終わる。

    ワザを使えるかの確認（番・ワザの位置・登録・必要なエネルギー）は、ワザの処理の前にすべて済ませる。
    ワザの説明にあるコイン（v0.2d）は、処理（p.309 の手順 6）の中で投げるので、拒否した操作では乱数を
    使わない（そもそも ``apply_command`` は複製した状態で処理する）。
    """
    p = _require_turn(state, cmd.player)
    attacker = p.active
    attacker_def = state.card_def(attacker.card)
    if not 0 <= cmd.attack_index < len(attacker_def.attacks):
        raise IllegalActionError("INVALID_ATTACK", f"{attacker_def.name_ja} に {cmd.attack_index!r} 番目のワザはない")
    attack = attacker_def.attacks[cmd.attack_index]
    effect = state.effects.attack_effect(attacker_def.id, attack)
    if effect is None:
        problem = state.effects.attack_problem(attacker_def.id, attack)
        raise UnsupportedError("UNSUPPORTED_ATTACK", f"ワザ「{attack.name_ja}」は未対応（{problem}）")
    if not can_pay_cost(attack.cost, state.energy_types(attacker)):
        raise IllegalActionError("INSUFFICIENT_ENERGY", f"ワザ「{attack.name_ja}」に必要なエネルギーが足りない")

    state.add_event("attack", player=cmd.player, pokemon=attacker.card, attack=attack.name_ja, attack_index=cmd.attack_index)
    # ワザの説明にしたがって処理する（p.309 の手順 6）。実装は DamageOnly・CoinFlipDamage（v0.2d）。
    # 実装が途中で決定を出したら、ここで止まり、決定が選ばれたあと _resume_attack から続ける
    effect.resolve(state, AttackUse(cmd.player, attacker.pokemon_id, AttackKey(attacker_def.id, cmd.attack_index)))
    if state.decision is None:
        _finish_attack(state)


def _finish_attack(state: GameState) -> None:
    """ワザの処理のあと: HP 以上のダメージを受けたポケモンはきぜつ（p.315, p.319, p.323）→ サイド → 交代 → 番の終わり。

    1 つのワザで複数のポケモンがきぜつしたら「同時」（p.324）。相手のポケモン（バトル場 → ベンチ）、
    自分のポケモンの順に処理する。v0.1 のカードでは、きぜつするのは相手のバトル場のポケモンだけ。
    """
    attacker_side = state.current_player
    prize_takers = []
    for owner in (1 - attacker_side, attacker_side):
        for pokemon in state.players[owner].in_play():
            if pokemon.damage >= state.card_def(pokemon.card).hp:
                _knock_out(state, owner, pokemon)
                prize_takers.append(1 - owner)  # きぜつしたポケモンの相手側のプレイヤーがサイドを取る
    _after_knockouts(state, prize_takers)


def _knock_out(state: GameState, owner: int, pokemon: PokemonInPlay) -> None:
    """きぜつ: ダメージカウンターを取りのぞき、ポケモンとついていたカードをすべてトラッシュする（p.323）。

    場を離れたので、このポケモンの番号（pokemon_id）は無効になる。
    """
    p = state.players[owner]
    if p.active is pokemon:
        p.active = None
    else:
        p.bench.remove(pokemon)
    p.discard.append(pokemon.card)
    p.discard.extend(pokemon.energy)
    # ついていたトレーナーカードもいっしょにトラッシュする（「それについていたすべてのカード」p.323。v0.2c）
    extra = {}
    if pokemon.trainers:
        for attached in pokemon.trainers:
            state.players[attached.player].discard.append(attached.card)
        extra["discarded_trainers"] = tuple(t.card for t in pokemon.trainers)
    state.add_event("knock_out", player=owner, pokemon=pokemon.card, discarded_energy=tuple(pokemon.energy), **extra)


def _after_knockouts(state: GameState, prize_takers=()) -> None:
    """ワザの処理の後: サイドを取る → 勝ち負けの判定 → バトル場にポケモンを出す → 番の終わり。

    ``prize_takers`` はサイドを 1 枚取るプレイヤーの並び（きぜつ 1 匹につき 1 つ）。番のプレイヤーが先
    （同じタイミングのことがらの順番は番のプレイヤーが決める（p.325）が、その選択は未実装。v0.1 の
    カードでは、サイドを取るのはワザを使ったプレイヤーだけ）。残りのサイドより多くは取らない。
    """
    budget = {player: len(state.players[player].prizes) for player in PLAYERS}
    queue = []
    for player in prize_takers:
        if budget[player] > 0:
            queue.append(player)
            budget[player] -= 1
    _next_prize_or_judge(state, tuple(queue))


def _next_prize_or_judge(state: GameState, queue: tuple[int, ...]) -> None:
    if queue:
        player = queue[0]
        push_decision(
            state,
            kind=TAKE_PRIZE,
            player=player,
            options=range(len(state.players[player].prizes)),  # サイドの位置（表は見ない）
            resume="take_prize",
            context=(("remaining", queue[1:]),),
        )
        return

    result = judge.decide(
        all_prizes_taken=[not state.players[p].prizes for p in PLAYERS],
        cannot_field_active=[state.players[p].active is None and not state.players[p].bench for p in PLAYERS],
    )
    if result is not None:
        _finish(state, result)
        return

    # 両方同時なら、番でないプレイヤーが先に出す（pp.323-324）
    order = (1 - state.current_player, state.current_player)
    _next_promotion_or_end(state, tuple(p for p in order if state.players[p].active is None))


def _next_promotion_or_end(state: GameState, queue: tuple[int, ...]) -> None:
    if queue:
        player = queue[0]
        push_decision(
            state,
            kind=PROMOTE_ACTIVE,
            player=player,
            options=[pokemon.pokemon_id for pokemon in state.players[player].bench],
            resume="promote_active",
            context=(("remaining", queue[1:]),),
        )
        return
    _end_turn(state)


def _resume_take_prize(state: GameState, decision, choices: tuple[int, ...]) -> None:
    """サイドカードから表を見ないで 1 枚を選び、手札に加える（p.312, p.323）。"""
    player = decision.player
    prizes = state.players[player].prizes
    uid = prizes.pop(choices[0])
    state.players[player].hand.append(uid)
    state.add_event("take_prize", player=player, card=uid, remaining=len(prizes))
    _next_prize_or_judge(state, decision.context_value("remaining", ()))


def _resume_promote_active(state: GameState, decision, choices: tuple[int, ...]) -> None:
    """ベンチから新しいバトル場のポケモンを出す（p.313, p.323）。"""
    p = state.players[decision.player]
    index = next(i for i, pokemon in enumerate(p.bench) if pokemon.pokemon_id == choices[0])
    p.active = p.bench.pop(index)
    state.add_event("promote_active", player=decision.player, pokemon=p.active.card)
    _next_promotion_or_end(state, decision.context_value("remaining", ()))


def _resume_attack(state: GameState, decision, choices: tuple[int, ...]) -> None:
    """ワザの効果の途中で出した決定の続き。決定がなくなったら、ワザの後の処理に進む。"""
    player, pokemon_id, card_id, attack_index = decision.context_value("use")
    use = AttackUse(player, pokemon_id, AttackKey(card_id, attack_index))
    entry = state.effects.attack_entry(card_id, attack_index)
    entry.effect.resume(state, use, decision, choices)
    if state.decision is None:
        _finish_attack(state)


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


# ---------------------------------------------------------------- 保留中の決定に答える


_RESUMERS = {
    "take_prize": _resume_take_prize,
    "promote_active": _resume_promote_active,
    "attack": _resume_attack,
    "trainer": _resume_trainer,
}


def _current_decision(state: GameState):
    """決定を待つ段階の、保留中の決定。段階と決定が合わない状態（呼び出し側が書き換えた）は受け付けない。"""
    if state.decision is None:
        raise StateIntegrityError([f"{state.phase.value} なのに決定がない"])
    return state.decision


def _resolve(state: GameState, choices: tuple[int, ...]) -> None:
    """確かめ終わった選択で、保留中の決定を閉じ、再開先から処理を続ける。"""
    decision = state.decision
    state.decision = None
    # 決定そのものはログに残さない（v0.1 のログの形を保つ。選んだ結果は再開した処理がログに残す）
    _RESUMERS[decision.resume](state, decision, choices)


def _resolve_decision(state: GameState, cmd: ResolveDecision) -> None:
    """保留中の決定に答える（どの種類の決定にも使える）。"""
    _require_phase(state, *DECISION_PHASES)
    player = _require_player(cmd.player)
    decision = _current_decision(state)
    if decision.player != player:
        raise IllegalActionError("NOT_YOUR_DECISION", f"この決定をするのはプレイヤー {decision.player}")
    if cmd.decision != decision.id:
        raise IllegalActionError("WRONG_DECISION", f"今の決定の番号は {decision.id}（{cmd.decision} を指している）")
    check_choices(decision, cmd.choices)
    _resolve(state, cmd.choices)


def _take_prize(state: GameState, cmd: TakePrize) -> None:
    """サイドを取る決定に、サイドの位置で答える（v0.1 からある形。``ResolveDecision`` と同じ処理）。"""
    _require_phase(state, Phase.TAKE_PRIZE)
    player = _require_player(cmd.player)
    decision = _current_decision(state)
    if decision.player != player:
        raise IllegalActionError("NOT_YOUR_DECISION", f"プレイヤー {player} が取るサイドはない")
    if cmd.index not in decision.options:
        raise IllegalActionError("INVALID_PRIZE_INDEX", f"サイドの位置は 0〜{len(decision.options) - 1}")
    _resolve(state, (cmd.index,))


def _promote_active(state: GameState, cmd: PromoteActive) -> None:
    """バトル場に出す決定に、ベンチのポケモンのカードの uid で答える（v0.1 からある形。
    ``ResolveDecision`` では場のポケモンの番号で答える）。"""
    _require_phase(state, Phase.PROMOTE_ACTIVE)
    player = _require_player(cmd.player)
    decision = _current_decision(state)
    if decision.player != player:
        raise IllegalActionError("NOT_YOUR_DECISION", f"今バトル場にポケモンを出すのはプレイヤー {decision.player}")
    p = state.players[player]
    index = p.bench_index(cmd.pokemon)
    if index is None:
        raise IllegalActionError("NOT_ON_BENCH", f"{cmd.pokemon!r} は自分のベンチにいない")
    _resolve(state, (p.bench[index].pokemon_id,))


def _end_turn_command(state: GameState, cmd: EndTurn) -> None:
    """ワザを使わないで自分の番を終える（p.309）。"""
    _require_turn(state, cmd.player)
    state.add_event("end_turn_without_attack", player=cmd.player)
    _end_turn(state)


def _finish(state: GameState, result: GameResult) -> None:
    state.result = result
    state.phase = Phase.SUDDEN_DEATH if result.outcome == "sudden_death" else Phase.GAME_OVER
    state.decision = None
    state.add_event("game_end", outcome=result.outcome, winner=result.winner, conditions=result.conditions)


_HANDLERS: dict[type, Callable[[GameState, object], None]] = {
    PlaceStartingPokemon: _place_starting_pokemon,
    DrawMulliganCards: _draw_mulligan_cards,
    ReportJankenResult: _report_janken_result,
    PlayBasicToBench: _play_basic_to_bench,
    AttachEnergy: _attach_energy,
    Retreat: _retreat,
    UseAttack: _use_attack,
    EndTurn: _end_turn_command,
    TakePrize: _take_prize,
    PromoteActive: _promote_active,
    ResolveDecision: _resolve_decision,
    PlayTrainer: _play_trainer,
}


# ---------------------------------------------------------------- 検査用


def check_invariants(state: GameState) -> list[str]:
    """状態の不変条件の問題を返す。問題がなければ空のリスト。

    ``new_game`` と ``apply_command`` は、返す前に必ずこれで確かめる（StateIntegrityError）。

    - カードの保存則: 対戦のすべてのカード（``state.cards``）が、持ち主のゾーンのどこか 1 か所にだけある。
      未知の番号のカードはない。``new_game`` で作った対戦では、カードの組がデッキリストと同じ。
    - 場の形: 場のポケモンはポケモンのカード、ついているのは基本エネルギー、ダメージは 10 の倍数で HP 未満、
      ベンチは 5 匹まで、サイドはルールの枚数まで。
    - 段階との対応: 番の途中は両方のバトル場にポケモンがいる。サイドを取る・バトル場に出す段階には、
      それを待っているプレイヤーがいる。終わった段階には結果か止めた理由がある。
    """
    problems: list[str] = []
    rules = state.rules
    seen: dict[int, str] = {}

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
            if pokemon.damage >= definition.hp:
                problems.append(f"ポケモン {pokemon.card} が HP 以上のダメージで場に残っている")
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

    for player, p in enumerate(state.players):
        if p.placed_starting_pokemon and p.active is None and phase not in (Phase.TAKE_PRIZE, Phase.PROMOTE_ACTIVE):
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
    if d.resume not in _RESUMERS:
        problems.append(f"決定の再開先 {d.resume!r} がない")
    remaining = d.context_value("remaining", ())
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
    if d.kind == PROMOTE_ACTIVE:
        queue = (d.player, *remaining)
        for player in queue:
            if player not in PLAYERS or state.players[player].active is not None or not state.players[player].bench:
                problems.append(f"バトル場に出すプレイヤー {player} の場の形が正しくない")
        for player in PLAYERS:
            if player not in queue and state.players[player].active is None:
                problems.append(f"プレイヤー {player} のバトル場にポケモンがいないのに、出す順番に入っていない")
        if d.options != tuple(pokemon.pokemon_id for pokemon in state.players[d.player].bench):
            problems.append(f"バトル場に出す決定の選べるもの {d.options} が、ベンチのポケモンと合わない")
    if d.resume == "attack":
        use = d.context_value("use")
        if not (isinstance(use, tuple) and len(use) == 4 and state.find_pokemon(use[1]) is not None):
            problems.append(f"ワザの決定の続きの情報 {use!r} が正しくない")
        elif state.effects.attack_entry(use[2], use[3]) is None:
            problems.append(f"ワザの決定の続きのワザ {use[2]}#{use[3]} が効果の登録表にない")
    # 選べるもののうち原典で扱いを決められないもの（v0.2b）: 選べるものの中にあり、残りで答えられる
    unresolved = d.context_value("unresolved_choices", ())
    if unresolved:
        if not set(unresolved) <= set(d.options):
            problems.append(f"扱いを決められない選択 {unresolved} が、選べるもの {d.options} にない")
        if len(set(d.options) - set(unresolved)) < max(d.min_choices, 1):
            problems.append(f"決定 {d.kind} に、扱いを決められる選択が足りない（答えられない）")
    return problems


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


def turn_owner(state: GameState, turn_number: int) -> int:
    """``turn_number`` 番目の番のプレイヤー。1 番目は先攻（ジャンケンの勝者）で、交互に進む（p.308・p.309）。"""
    return state.first_player if turn_number % 2 == 1 else 1 - state.first_player


def _trainer_problems(state: GameState) -> list[str]:
    """使用中のトレーナー（v0.2b）と、決定・段階の整合性。

    トレーナーカードが使用中なのは、そのトレーナーの効果が決定を待っている間だけ（決定がなければ、
    説明にしたがい終わってトラッシュしている）。
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
    if state.effects.trainer_entry(card_id) is None:
        problems.append(f"トレーナーの決定の続きのカード {card_id} が効果の登録表にない")
    return problems

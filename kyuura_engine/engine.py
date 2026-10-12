"""対戦の進行（公式ルール 2000.02.14版）。

使い方::

    state = new_game(deck0, deck1, seed=1)
    state = apply_command(state, PlaceStartingPokemon(player=0, active=..., bench=(...)))
    ...

- ``apply_command`` は渡された状態を変えず、新しい状態を返します。操作が不正なら例外を投げ、
  渡した状態はそのまま使えます。
- 乱数（山札を切る）は ``seed`` から作った乱数だけを使います。同じデッキ・同じ seed・同じ操作の
  列なら、同じ結果になります。
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
    PromoteActive,
    ReportJankenResult,
    Retreat,
    TakePrize,
    UseAttack,
)
from .damage import calculate_attack_damage
from .deck import deck_problems
from .errors import DeckValidationError, IllegalActionError, UnsupportedError
from .rules import RULES_2000_02_14, RuleSet
from .state import (
    CardInstance,
    DataSource,
    GameResult,
    GameState,
    Halt,
    Phase,
    PlayerState,
    PokemonInPlay,
    freeze_mapping,
)

PLAYERS = (0, 1)


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
    """
    pool = pool or load_card_pool()
    problems = [f"player {p}: {problem}" for p, deck in enumerate((deck0, deck1)) for problem in deck_problems(deck, pool, rules)]
    if problems:
        raise DeckValidationError(problems)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed は整数")

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
    )
    state.add_event("game_created", rules=rules.id, seed=seed, card_data_commit=pool.source["commit"])

    # デッキを切る（自分で切り、相手にも切ってもらう。その結果を乱数 1 回の並べ替えで表す）
    for player in PLAYERS:
        _shuffle_deck(state, player)
    _deal_opening_hands(state)
    return state


def _shuffle_deck(state: GameState, player: int) -> None:
    state.rng.shuffle(state.players[player].deck)
    state.add_event("shuffle", player=player)


def _draw(state: GameState, player: int, count: int) -> None:
    p = state.players[player]
    drawn = p.deck[:count]
    del p.deck[:count]
    p.hand.extend(drawn)
    state.add_event("draw", player=player, cards=tuple(drawn))


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
    """コマンドを処理した新しい状態を返す。渡した ``state`` は変えない。"""
    if isinstance(command, UNSUPPORTED_COMMANDS):
        raise UnsupportedError("UNSUPPORTED_ACTION", f"{type(command).__name__} は v0.1 では未対応")
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
    return new


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
    p.active = PokemonInPlay(cmd.active)
    p.bench = [PokemonInPlay(uid) for uid in cmd.bench]
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
    """番を終え、ポケモンチェックをして、相手の番にする（p.309）。"""
    state.add_event("turn_end", player=state.current_player)
    _pokemon_check(state)
    _begin_turn(state, 1 - state.current_player)


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
    p.bench.append(PokemonInPlay(cmd.card))
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

    使い終わったら、自分の番は自動的に終わる。
    """
    p = _require_turn(state, cmd.player)
    attacker = p.active
    attacker_def = state.card_def(attacker.card)
    if not 0 <= cmd.attack_index < len(attacker_def.attacks):
        raise IllegalActionError("INVALID_ATTACK", f"{attacker_def.name_ja} に {cmd.attack_index!r} 番目のワザはない")
    attack = attacker_def.attacks[cmd.attack_index]
    if not attack.supported:
        raise UnsupportedError("UNSUPPORTED_ATTACK", f"ワザ「{attack.name_ja}」は v0.1 では未対応（{attack.unsupported_reason}）")
    if not can_pay_cost(attack.cost, state.energy_types(attacker)):
        raise IllegalActionError("INSUFFICIENT_ENERGY", f"ワザ「{attack.name_ja}」に必要なエネルギーが足りない")

    opponent = 1 - cmd.player
    defender = state.players[opponent].active
    defender_def = state.card_def(defender.card)
    state.add_event("attack", player=cmd.player, pokemon=attacker.card, attack=attack.name_ja, attack_index=cmd.attack_index)

    # ワザの説明がない場合は、ダメージの目安の数字ぶんのダメージを相手の対戦ポケモンに与える（p.309, p.320）
    calc = calculate_attack_damage(attack.damage, attacker_def, defender_def, state.rules)
    defender.damage += calc.final
    state.add_event(
        "damage",
        player=opponent,
        pokemon=defender.card,
        amount=calc.final,
        steps=calc.steps,
        weakness=calc.weakness_applied,
        resistance=calc.resistance_applied,
        total_damage=defender.damage,
    )

    # HP 以上のダメージを受けたら、きぜつ（p.315, p.319, p.323）
    if defender.damage >= defender_def.hp:
        _knock_out(state, opponent, defender)
    _after_knockouts(state)


def _knock_out(state: GameState, owner: int, pokemon: PokemonInPlay) -> None:
    """きぜつ: ダメージカウンターを取りのぞき、ポケモンとついていたカードをすべてトラッシュする。
    相手はサイドを 1 枚取る（p.323）。"""
    p = state.players[owner]
    if p.active is pokemon:
        p.active = None
    else:
        p.bench.remove(pokemon)
    p.discard.append(pokemon.card)
    p.discard.extend(pokemon.energy)
    state.add_event("knock_out", player=owner, pokemon=pokemon.card, discarded_energy=tuple(pokemon.energy))
    taker = 1 - owner
    state.pending_prizes[taker] = state.pending_prizes.get(taker, 0) + 1


def _after_knockouts(state: GameState) -> None:
    """ワザの処理の後: サイドを取る → 勝ち負けの判定 → バトル場にポケモンを出す → 番の終わり。"""
    for player in PLAYERS:
        remaining = len(state.players[player].prizes)
        if state.pending_prizes.get(player, 0) > remaining:
            state.pending_prizes[player] = remaining
    state.pending_prizes = {p: n for p, n in state.pending_prizes.items() if n > 0}
    if state.pending_prizes:
        state.phase = Phase.TAKE_PRIZE
        return

    result = judge.decide(
        all_prizes_taken=[not state.players[p].prizes for p in PLAYERS],
        cannot_field_active=[state.players[p].active is None and not state.players[p].bench for p in PLAYERS],
    )
    if result is not None:
        _finish(state, result)
        return

    # 両方同時なら、番でないプレイヤーが先に出す（pp.323-324）
    order = [1 - state.current_player, state.current_player]
    state.pending_promotions = [p for p in order if state.players[p].active is None]
    if state.pending_promotions:
        state.phase = Phase.PROMOTE_ACTIVE
        return
    _end_turn(state)


def _take_prize(state: GameState, cmd: TakePrize) -> None:
    """サイドカードから表を見ないで 1 枚を選び、手札に加える（p.312, p.323）。"""
    _require_phase(state, Phase.TAKE_PRIZE)
    player = _require_player(cmd.player)
    if state.pending_prizes.get(player, 0) <= 0:
        raise IllegalActionError("NOT_YOUR_DECISION", f"プレイヤー {player} が取るサイドはない")
    prizes = state.players[player].prizes
    if not 0 <= cmd.index < len(prizes):
        raise IllegalActionError("INVALID_PRIZE_INDEX", f"サイドの位置は 0〜{len(prizes) - 1}")
    uid = prizes.pop(cmd.index)
    state.players[player].hand.append(uid)
    state.pending_prizes[player] -= 1
    state.add_event("take_prize", player=player, card=uid, remaining=len(prizes))
    _after_knockouts(state)


def _promote_active(state: GameState, cmd: PromoteActive) -> None:
    """ベンチから新しいバトル場のポケモンを出す（p.313, p.323）。"""
    _require_phase(state, Phase.PROMOTE_ACTIVE)
    player = _require_player(cmd.player)
    if not state.pending_promotions or state.pending_promotions[0] != player:
        raise IllegalActionError("NOT_YOUR_DECISION", f"今バトル場にポケモンを出すのはプレイヤー {state.pending_promotions[:1]}")
    p = state.players[player]
    index = p.bench_index(cmd.pokemon)
    if index is None:
        raise IllegalActionError("NOT_ON_BENCH", f"{cmd.pokemon!r} は自分のベンチにいない")
    p.active = p.bench.pop(index)
    state.pending_promotions.pop(0)
    state.add_event("promote_active", player=player, pokemon=cmd.pokemon)
    if not state.pending_promotions:
        _end_turn(state)


def _end_turn_command(state: GameState, cmd: EndTurn) -> None:
    """ワザを使わないで自分の番を終える（p.309）。"""
    _require_turn(state, cmd.player)
    state.add_event("end_turn_without_attack", player=cmd.player)
    _end_turn(state)


def _finish(state: GameState, result: GameResult) -> None:
    state.result = result
    state.phase = Phase.SUDDEN_DEATH if result.outcome == "sudden_death" else Phase.GAME_OVER
    state.pending_prizes = {}
    state.pending_promotions = []
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
}


# ---------------------------------------------------------------- 検査用


def check_invariants(state: GameState) -> list[str]:
    """状態の整合性の問題を返す（テスト用）。各カードがちょうど 1 か所にあること、など。"""
    problems: list[str] = []
    seen: dict[int, str] = {}

    def place(uid: int, player: int, zone: str) -> None:
        where = f"プレイヤー {player} の {zone}"
        if uid in seen:
            problems.append(f"カード {uid} が {seen[uid]} と {where} の 2 か所にある")
        seen[uid] = where
        if uid in state.cards and state.cards[uid].owner != player:
            problems.append(f"カード {uid} が持ち主でない {where} にある")

    for player, p in enumerate(state.players):
        for zone in ("deck", "hand", "prizes", "discard"):
            for uid in getattr(p, zone):
                place(uid, player, zone)
        for pokemon in p.in_play():
            place(pokemon.card, player, "場")
            for uid in pokemon.energy:
                place(uid, player, "場（ついているエネルギー）")
                if not state.card_def(uid).is_basic_energy:
                    problems.append(f"エネルギーでないカード {uid} がポケモンについている")
            if pokemon.damage < 0 or pokemon.damage % 10:
                problems.append(f"ポケモン {pokemon.card} のダメージ {pokemon.damage} が 10 の倍数でない")
            if pokemon.damage >= state.card_def(pokemon.card).hp:
                problems.append(f"ポケモン {pokemon.card} が HP 以上のダメージで場に残っている")
        if len(p.bench) > state.rules.max_bench:
            problems.append(f"プレイヤー {player} のベンチが {len(p.bench)} 匹")
        if state.phase is Phase.MAIN and p.active is None:
            problems.append(f"プレイヤー {player} のバトル場にポケモンがいないまま番が進んでいる")
    missing = set(state.cards) - set(seen)
    if missing:
        problems.append(f"どこにもないカード {sorted(missing)}")
    return problems

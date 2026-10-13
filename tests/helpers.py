"""テスト用の道具。

- ``build_test_state``: 正式な対戦開始（``new_game``）を通さずに、盤面を直接作る。
  ルールの 1 か所だけを確かめたいテストで使う。デッキの枚数などの対戦準備の規定は
  通らないので、対戦準備・デッキのテストには使わない。
- ``scripted_command``: 統合テストで 1 試合を最後まで進めるための、決まった手順の操作。
  対戦相手の AI ではない（強さや戦略は考えていない）。
- ``with_coin_results``（v0.2d）: テストの中だけで、次に投げるコインの結果を決める（状態の乱数を、
  その結果になる乱数に差し替える）。エンジンの API にはコインの結果を指定する方法はない。
"""

from __future__ import annotations

import random
from typing import Iterable

from kyuura_engine import (
    AttachEnergy,
    DrawMulliganCards,
    EndTurn,
    GameState,
    Phase,
    PlaceStartingPokemon,
    PlayBasicToBench,
    PromoteActive,
    ReportJankenResult,
    TakePrize,
    UseAttack,
    apply_command,
    can_pay_cost,
    expand_decklist,
    load_card_pool,
    new_game,
)
from kyuura_engine.rules import RULES_2000_02_14
from kyuura_engine.state import (
    ASLEEP,
    AttachedTrainer,
    CONFUSED,
    PreventDamage,
    CardInstance,
    DataSource,
    Paralyzed,
    PlayerState,
    Poison,
    PokemonInPlay,
    SpecialConditions,
    freeze_mapping,
)

# カード id（kyuura data/cards.json の id）
PONYTA = "PMCG1-016"
GROWLITHE = "PMCG1-018"
STARYU = "PMCG1-025"
SEEL = "PMCG1-029"
VOLTORB = "PMCG1-037"
DIGLETT = "PMCG1-052"
MACHOP = "PMCG1-053"
HITMONCHAN = "PMCG1-058"
RATTATA = "PMCG1-060"
DRATINI = "PMCG1-065"
GRASS = "PMCG1-097"
FIRE = "PMCG1-098"
WATER = "PMCG1-099"
LIGHTNING = "PMCG1-100"
PSYCHIC = "PMCG1-101"
FIGHTING = "PMCG1-102"
CHARMANDER = "PMCG1-014"  # 対戦には使えない参照カード（「ひのこ」は未対応）
DODUO = "PMCG1-061"  # ドードー（v0.2d で対応。みだれづき: コイン 2 枚の「おもて」の数×10）
PIKACHU = "PMCG1-035"  # ピカチュウ（v0.2f で対応。かじる 10、でんげき 30・「うら」なら自分にも 10）
WEEDLE = "PMCG1-004"  # ビードル（v0.3a で対応。どくばり 10・「おもて」なら相手をどく状態に）
CATERPIE = "PMCG1-002"  # キャタピー（v0.3b で対応。いとをはく 10・「おもて」なら相手をマヒ状態に）
PARAS = "PMCG2-003"  # パラス（v0.3b で対応。ひっかく 20、キノコのほうし（ダメージなし）で相手をねむり状態に）
VULPIX = "PMCG1-015"  # ロコン（v0.3c で対応。あやしいひかり 10・「おもて」なら相手をこんらん状態に。炎・弱点 水・にげる 1）
PARASECT = "PMCG2-010"  # パラセクト（v0.4a で対応。パラスから進化する 1 進化。HP 60・草・弱点 炎・にげる 1。キノコのほうし・きりさく 30）
DEWGONG = "PMCG1-030"  # ジュゴン（v0.4a で対応。パウワウから進化する 1 進化。HP 80・水・弱点 雷・にげる 3。オーロラビーム 50・れいとうビーム 30）
METAPOD = "PMCG1-003"  # トランセル（v0.4b。キャタピーから進化。かたまる・しびれごな）
KAKUNA = "PMCG1-009"  # コクーン（v0.4b。ビードルから進化。かたまる・どくのこな）
BEEDRILL = "PMCG1-012"  # スピアー（v0.4c。コクーンから進化する 2 進化。HP 80・草・弱点 炎・抵抗力 闘 -30・にげる 0。ダブルニードル・どくばり 40）
BUTTERFREE = "PMCG2-007"  # バタフリー（v0.4d。トランセルから進化する 2 進化。HP 70・草・弱点 炎・抵抗力 闘 -30・にげる 0。ふきとばし 20・メガドレイン 40）
VENUSAUR = "PMCG1-011"  # フシギバナ（v0.5。フシギソウから進化する 2 進化。HP 100・草・弱点 炎・にげる 2。ポケモンパワー エナジートランス・ソーラービーム 60）
IVYSAUR = "PMCG1-008"  # フシギソウ（v0.5。フシギダネから進化する 1 進化。HP 60・草・弱点 炎・にげる 1。つるのムチ 30・どくのこな 20）
BULBASAUR = "PMCG1-001"  # フシギダネ（v0.5。HP 40・草・弱点 炎・にげる 1。やどりぎのタネ 20）
# カメックス（v0.6。カメールから進化する 2 進化。HP 100・水・弱点 雷・にげる 3。ポケモンパワー あまごい・ハイドロポンプ 40+）。
# v0.5 では「実装を登録していないポケモンパワーを持つので未対応」の参照カードだった（v0.6 で対応にしたので、その役はフーディンへ）
BLASTOISE = "PMCG1-032"
WARTORTLE = "PMCG1-027"  # カメール（v0.6。ゼニガメから進化する 1 進化。HP 70・水・弱点 雷・にげる 1。からにこもる・かみつく 40）
SQUIRTLE = "PMCG1-023"  # ゼニガメ（v0.6。HP 40・水・弱点 雷・にげる 1。あわ 10・からにこもる）
# フーディン（参照カード。ユンゲラーから進化する 2 進化。実装を登録していないポケモンパワー「ダメージスワップ」と、ロコンと同じ名前でも
# 登録していないワザ「あやしいひかり」を持つ。v0.4e まではフシギバナ、v0.5 ではカメックスが「ポケモンパワーを持つので未対応」の参照
# カードだった。v0.6 でカメックスを対応にしたので、その役を引き継ぐ）
ALAKAZAM = "PMCG1-049"
# トレーナー（v0.2b で対応）
POTION = "PMCG1-071"  # きずぐすり
SWITCH = "PMCG1-073"  # ポケモンいれかえ
BILL = "PMCG1-074"  # マサキ
PLUSPOWER = "PMCG1-081"  # プラスパワー（v0.2c で対応）
DEFENDER = "PMCG1-079"  # ディフェンダー（v0.2e で対応）
SUPER_POTION = "PMCG1-075"  # いいきずぐすり（参照カード。実装を登録していないトレーナー）

# 60 枚の合法なデッキ（たねポケモン 20 枚 + 基本エネルギー 40 枚）
FIRE_DECK = expand_decklist({GROWLITHE: 4, PONYTA: 4, RATTATA: 4, DRATINI: 4, VOLTORB: 4, FIRE: 40})
WATER_FIGHTING_DECK = expand_decklist({STARYU: 4, SEEL: 4, DIGLETT: 4, MACHOP: 4, HITMONCHAN: 4, WATER: 20, FIGHTING: 20})
# たねポケモン 40 枚（10 種 × 4）+ エネルギー 20 枚。手札がたねポケモンだけになる seed を探すのに使う
MANY_BASICS = expand_decklist({p: 4 for p in (PONYTA, GROWLITHE, STARYU, SEEL, VOLTORB, DIGLETT, MACHOP, HITMONCHAN, RATTATA, DRATINI)} | {FIRE: 20})
# たねポケモンが少ない 60 枚のデッキ（切り直しが起こりやすい）
ONE_BASIC = expand_decklist({MACHOP: 1, FIGHTING: 59})
FEW_BASICS = expand_decklist({SEEL: 4, WATER: 56})


def find_seed(deck0, deck1, predicate, start: int = 0, limit: int = 5000) -> int:
    """predicate(new_game(...)) が真になる最初の seed（決まった順に探すので毎回同じ seed になる）。"""
    for seed in range(start, start + limit):
        if predicate(new_game(deck0, deck1, seed)):
            return seed
    raise AssertionError("条件に合う seed が見つからない")


def uids(state: GameState, player: int, zone: str, card_id: str | None = None) -> list[int]:
    p = state.players[player]
    items = getattr(p, zone)
    return [u for u in items if card_id is None or state.cards[u].card_id == card_id]


def basics_in_hand(state: GameState, player: int) -> list[int]:
    return [u for u in state.players[player].hand if state.card_def(u).is_basic_pokemon]


def energy_in_hand(state: GameState, player: int) -> list[int]:
    return [u for u in state.players[player].hand if state.card_def(u).is_basic_energy]


def place_all(state: GameState, player: int, max_bench: int = 5) -> GameState:
    basics = basics_in_hand(state, player)
    return apply_command(state, PlaceStartingPokemon(player, basics[0], tuple(basics[1 : 1 + max_bench])))


def finish_setup(state: GameState, janken_winner: int = 0, draw_count: int = 2) -> GameState:
    """対戦準備を最後まで進める（両方がたねポケモンを全部出す → 引く権利があれば引く → ジャンケン）。"""
    for player in (0, 1):
        if not state.players[player].placed_starting_pokemon:
            state = place_all(state, player)
    while state.phase is Phase.SETUP_MULLIGAN_DRAW:
        player = 0 if state.players[0].mulligan_draws_remaining else 1
        state = apply_command(state, DrawMulliganCards(player, min(draw_count, len(state.players[player].deck))))
    return apply_command(state, ReportJankenResult(janken_winner))


# ---------------------------------------------------------------- 盤面を直接作る（テスト専用）


def build_test_state(
    players: list[dict],
    *,
    current_player: int = 0,
    turn_number: int = 3,
    seed: int = 0,
    energy_attachments_this_turn: int = 0,
    effects=None,
    pool=None,
) -> GameState:
    """テスト専用: 正式な対戦開始を通さずに MAIN の盤面を作る。

    players[i] のキー（どれも省略できる。active は必須）:
      active: カード id、または {"card": id, "damage": n, "energy": [id, ...], "poison": ダメージ, "sleep": True,
              "paralysis": マヒ状態になった番, "confusion": True, "retreat_failed_turn": 番,
              "evolved_from": 下のたねポケモンのカード id, "evolved_turn": 進化した番, "played_turn": 場に出た番,
              "prevent_damage": 効果を与えた番}
              （"poison" はバトル場のポケモンのどく状態。v0.3a。"sleep"・"paralysis" はねむり・マヒ状態。v0.3b。
              "confusion" はこんらん状態、"retreat_failed_turn" はこんらん状態で「にげる」に失敗した番。v0.3c。
              特殊状態をベンチに書くと不変条件で拒否される。"sleep"・"paralysis"・"confusion" は重複しないので
              2 つ以上は書けない。"evolved_from" は進化しているポケモン（v0.4a。"card" が 1 進化ポケモン）。v0.4c から、
              2 進化ポケモンは "evolved_from" に下のカードのリスト [たねポケモン, 1 進化ポケモン]（下から順）を書く。
              "evolved_turn" はいまの姿に進化した番で、省略すると、3 番以降の持ち主の番（2 進化ならその 2 つ目以降）の
              うち、今の番より前の最後の番（なければ今の番）。1 進化した番は書かない（状態に持たないので、不変条件は
              その前に 1 進化できる番があることだけを確かめる。進化のログは置かない）。"played_turn" の既定は 0（対戦準備で出した）。
              "prevent_damage" は、その番に「かたまる」などで受けた持続する効果 ``PreventDamage``（v0.4b。はたらく番は次の番）。
              効果を与えたログ ``persistent_effect_added`` も、その番の記録として置く（不変条件: 効果はログと対応する）。
              "trainers" は、ついているトレーナー（v0.4e）の [(カード id, トラッシュする番), ...]。使ったプレイヤーは持ち主。
              トラッシュする番は、プラスパワーなら使った番、ディフェンダーなら使った番 + 1（不変条件: 使った番は持ち主の番））
      bench:  active と同じ形のリスト
      hand / deck / discard: カード id のリスト（deck は先頭が一番上）
      prizes: カード id のリスト、または枚数（枚数なら炎エネルギーで埋める）
    pool: カードの定義を引くカードの組（省略時は同梱の写し。テスト専用のカードを使うとき）
    """
    pool = pool or load_card_pool()
    cards: dict[int, CardInstance] = {}

    def new_uid(card_id: str, owner: int) -> int:
        uid = len(cards)
        cards[uid] = CardInstance(uid, card_id, owner)
        return uid

    next_pokemon_id = [1]

    def pokemon(spec, owner: int) -> PokemonInPlay:
        if isinstance(spec, str):
            spec = {"card": spec}
        below = spec.get("evolved_from", ())
        below = (below,) if isinstance(below, str) else tuple(below)  # 2 進化（v0.4c）は [たね, 1 進化]（下から順）
        stack = tuple(new_uid(card_id, owner) for card_id in below)
        result = PokemonInPlay(new_uid(spec["card"], owner), pokemon_id=next_pokemon_id[0])
        next_pokemon_id[0] += 1
        result.played_turn = spec.get("played_turn", 0)
        if stack:
            result.evolution_stack = stack
            evolved_turn = spec.get("evolved_turn")
            if evolved_turn is None:
                # 先攻はプレイヤー 0（奇数の番）。おたがいの最初の番（1・2 番）には進化できない。今の番より前の持ち主の番の
                # うち最後の番（なければ今の番）。2 進化（v0.4c）は、その前に 1 進化した持ち主の番がいる（同じ番に二度は
                # 進化できない。p.310）ので、その 2 つ目から（場に出た番は見ない。v0.4a と同じ）
                owned = [t for t in range(3, turn_number + 1) if t % 2 == (1 if owner == 0 else 0)]
                owned = owned[len(stack) - 1:]
                if not owned:
                    raise ValueError("進化した番を決められない（turn_number を大きくするか evolved_turn を書く）")
                earlier = [t for t in owned if t < turn_number]
                evolved_turn = earlier[-1] if earlier else owned[-1]
            result.evolved_turn = evolved_turn
        result.energy = [new_uid(e, owner) for e in spec.get("energy", [])]
        result.trainers = [AttachedTrainer(new_uid(card_id, owner), owner, discard_at) for card_id, discard_at in spec.get("trainers", [])]
        result.damage = spec.get("damage", 0)
        exclusive = None
        if spec.get("sleep"):
            exclusive = ASLEEP
        if "paralysis" in spec:
            if exclusive is not None:
                raise ValueError("ねむりとマヒは重複しない（p.322）")
            exclusive = Paralyzed(turn=spec["paralysis"])
        if spec.get("confusion"):
            if exclusive is not None:
                raise ValueError("ねむり・マヒ・こんらんは重複しない（p.322）")
            exclusive = CONFUSED
        result.retreat_failed_turn = spec.get("retreat_failed_turn")
        if "prevent_damage" in spec:
            created = spec["prevent_damage"]
            result.persistent_effects = (PreventDamage(result.card, owner, created, created + 1),)
        poison = Poison(spec["poison"]) if "poison" in spec else None
        if poison is not None or exclusive is not None:
            result.conditions = SpecialConditions(poison=poison, exclusive=exclusive)
        return result

    states = []
    for owner, spec in enumerate(players):
        prizes = spec.get("prizes", 6)
        if isinstance(prizes, int):
            prizes = [FIRE] * prizes
        p = PlayerState(deck=[])
        p.active = pokemon(spec["active"], owner) if spec.get("active") else None
        p.bench = [pokemon(b, owner) for b in spec.get("bench", [])]
        p.hand = [new_uid(c, owner) for c in spec.get("hand", [])]
        p.deck = [new_uid(c, owner) for c in spec.get("deck", [FIRE] * 10)]
        p.prizes = [new_uid(c, owner) for c in prizes]
        p.discard = [new_uid(c, owner) for c in spec.get("discard", [])]
        p.placed_starting_pokemon = True
        states.append(p)

    used = {c.card_id for c in cards.values()}
    state = GameState(
        rules=RULES_2000_02_14,
        card_data=DataSource(pool.source["repository"], pool.source["commit"], pool.source["path"]),
        seed=seed,
        rng=random.Random(seed),
        cards=freeze_mapping(cards),
        definitions=freeze_mapping({c: pool.get(c) for c in used}),
        decklists=((), ()),
        players=states,
        phase=Phase.MAIN,
        turn_number=turn_number,
        current_player=current_player,
        first_player=0,
        energy_attachments_this_turn=energy_attachments_this_turn,
        next_pokemon_id=next_pokemon_id[0],
        effects=effects or pool.effects,
    )
    # "retreat_failed_turn" を書いたポケモンには、その番の「にげる」の失敗のログも置く（v0.3d の不変条件: 記録はログの
    # retreat_failed と対応する）。テスト専用の盤面なので、トラッシュしたエネルギーは空にしておく
    for owner, p in enumerate(states):
        for pokemon in p.in_play():
            if pokemon.retreat_failed_turn is not None:
                state.add_event("retreat_failed", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, discarded=())
    # "prevent_damage" を書いたポケモンには、効果を与えた番のログも置く（v0.4b の不変条件: 持続する効果はログと対応する）
    for owner, p in enumerate(states):
        for pokemon in p.in_play():
            for effect in pokemon.persistent_effects:
                current = state.turn_number
                state.turn_number = effect.created_turn  # ログの turn は効果を与えた番
                state.add_event(
                    "persistent_effect_added", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id,
                    persistent_effect=effect.kind, source_card=effect.source_card, source_player=effect.source_player,
                    active_turn=effect.active_turn, effect="test",
                )
                state.turn_number = current
    return state


def active(state: GameState, player: int) -> PokemonInPlay:
    return state.players[player].active


# ---------------------------------------------------------------- 1 試合を進める決まった手順


def best_affordable_attack(state: GameState, player: int) -> int | None:
    """使えるワザのうち、ダメージの目安の数字がいちばん大きいもの（同じなら後のワザ）。

    ダメージの目安の数字がないワザ（パラスの「キノコのほうし」。v0.3b）は 0 として比べる（それまでの対応カードには
    ないので、既存の対戦の手順は変わらない）。"""
    pokemon = state.players[player].active
    definition = state.card_def(pokemon.card)
    provided = state.energy_types(pokemon)
    best = None
    for attack in definition.attacks:
        if attack.supported and can_pay_cost(attack.cost, provided):
            if best is None or (attack.damage or 0) >= (definition.attacks[best].damage or 0):
                best = attack.index
    return best


def scripted_command(state: GameState, *, attack: bool = True, bench: bool = True, janken_winner: int = 0):
    """今の状態で次に送る操作を 1 つ返す（統合テスト用の決まった手順）。

    - 対戦準備: 手札のたねポケモンをすべて出す。引く権利があれば 2 枚引く。ジャンケンは janken_winner の勝ち。
    - 自分の番: たねポケモンをベンチに出す → エネルギーをバトル場のポケモンにつける → 使える一番強いワザを使う。
      ワザが使えなければ番を終える。
    - サイドは一番目を取る。バトル場には、ベンチの一番目のポケモンを出す。
    """
    phase = state.phase
    if phase is Phase.SETUP_PLACEMENT:
        player = 0 if not state.players[0].placed_starting_pokemon else 1
        basics = basics_in_hand(state, player)
        return PlaceStartingPokemon(player, basics[0], tuple(basics[1:6]) if bench else ())
    if phase is Phase.SETUP_MULLIGAN_DRAW:
        player = 0 if state.players[0].mulligan_draws_remaining else 1
        return DrawMulliganCards(player, min(2, len(state.players[player].deck)))
    if phase is Phase.SETUP_FIRST_PLAYER:
        return ReportJankenResult(janken_winner)
    if phase is Phase.TAKE_PRIZE:
        player = next(p for p, n in state.pending_prizes.items() if n > 0)
        return TakePrize(player, 0)
    if phase is Phase.PROMOTE_ACTIVE:
        player = state.pending_promotions[0]
        return PromoteActive(player, state.players[player].bench[0].card)
    if phase is Phase.MAIN:
        player = state.current_player
        p = state.players[player]
        if bench and len(p.bench) < 5 and basics_in_hand(state, player):
            return PlayBasicToBench(player, basics_in_hand(state, player)[0])
        if state.energy_attachments_this_turn == 0 and energy_in_hand(state, player):
            return AttachEnergy(player, energy_in_hand(state, player)[0], p.active.card)
        if attack:
            index = best_affordable_attack(state, player)
            if index is not None:
                return UseAttack(player, index)
        return EndTurn(player)
    raise AssertionError(f"操作を決められない局面 {phase}")


def play_until_end(state: GameState, *, max_steps: int = 5000, check=None, **policy) -> tuple[GameState, list]:
    """終わる（GAME_OVER / SUDDEN_DEATH / HALTED）まで scripted_command を送る。送った操作の列も返す。"""
    commands = []
    for _ in range(max_steps):
        if state.phase in (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED):
            return state, commands
        command = scripted_command(state, **policy)
        commands.append(command)
        state = apply_command(state, command)
        if check is not None:
            check(state)
    raise AssertionError("決まった手数で終わらなかった")


def replay(state: GameState, commands: Iterable) -> GameState:
    for command in commands:
        state = apply_command(state, command)
    return state


# ---------------------------------------------------------------- テスト専用のワザの効果（製品の登録表には入れない）

from kyuura_engine.decisions import push_attack_decision  # noqa: E402
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackEffect, AttackEntry, AttackKey  # noqa: E402


class TwoStepTestEffect(AttackEffect):
    """テスト専用: 2 段階の決定を出すワザの効果（保留中の決定の仕組みを確かめるため）。

    1. ワザを使ったプレイヤーが、相手の場のポケモンを 1〜2 匹選ぶ（場のポケモンの番号）
    2. 同じプレイヤーが、与えるダメージ 10 か 20 を選ぶ
    選んだポケモンに、選んだダメージをそのまま与える（弱点・抵抗力は計算しない。実在のワザではない）。
    """

    implementation_id = "test_two_step"

    def resolve(self, state, use):
        targets = [pokemon.pokemon_id for pokemon in state.players[1 - use.player].in_play()]
        push_attack_decision(state, use, kind="test_choose_targets", player=use.player, options=targets,
                             min_choices=1, max_choices=2, context=(("step", 1),))

    def resume(self, state, use, decision, choices):
        if decision.context_value("step") == 1:
            push_attack_decision(state, use, kind="test_choose_amount", player=use.player, options=(10, 20),
                                 context=(("step", 2), ("targets", tuple(choices))))
            return
        amount = choices[0]
        for pokemon_id in decision.context_value("targets"):
            _, pokemon = state.find_pokemon(pokemon_id)
            pokemon.damage += amount
        state.add_event("test_two_step", targets=decision.context_value("targets"), amount=amount)


def two_step_effects():
    """ワンリキー（PMCG1-053）の「けたぐり」を、テスト専用の 2 段階の効果に置き換えた登録表。"""
    return DEFAULT_EFFECTS.with_attacks("test-two-step", {AttackKey(MACHOP, 0): AttackEntry(TwoStepTestEffect(), "けたぐり")})


# ---------------------------------------------------------------- トレーナーを使う決まった手順（v0.2b）

from kyuura_engine import PlayTrainer, ResolveDecision  # noqa: E402


def trainer_command(state: GameState):
    """番のプレイヤーが、決まった手順でトレーナーを使うなら、そのコマンド。使わないなら None。

    - マサキ: 手札にあれば使う（山札が 0 枚でも使える。p.312）
    - きずぐすり: 自分の場にダメージカウンターののったポケモンがいれば使う
    - ポケモンいれかえ: 控えがいて、バトル場のポケモンにダメージがあり、それよりダメージの少ない控えがいれば使う
    """
    player = state.current_player
    p = state.players[player]

    def in_hand(card_id):
        return next((u for u in p.hand if state.cards[u].card_id == card_id), None)

    bill, potion, switch = in_hand(BILL), in_hand(POTION), in_hand(SWITCH)
    if bill is not None:
        return PlayTrainer(player, bill)
    if potion is not None and any(pokemon.damage for pokemon in p.in_play()):
        return PlayTrainer(player, potion)
    if switch is not None and p.bench and p.active.damage and min(b.damage for b in p.bench) < p.active.damage:
        return PlayTrainer(player, switch)
    return None


def trainer_policy_command(state: GameState, *, janken_winner: int = 0):
    """``scripted_command`` に、トレーナーを使う手順と、トレーナーの決定への答えを加えたもの（統合テスト用）。

    プラスパワー（v0.2c）は、ワザを使う直前に、手札にあるだけつける。ディフェンダー（v0.2e）は、ワザを使う・番を
    終える直前に、手札にあるだけ自分の対戦ポケモンにつける（相手の番にワザを受けるのはバトル場のポケモン）。

    決定には、扱いを決められるもののうち、きずぐすりならダメージのいちばん多いポケモン、
    それ以外は最初のものを選ぶ。
    """
    if state.phase is Phase.DECISION:
        d = state.decision
        unresolved = d.context_value("unresolved_choices", ())
        options = [o for o in d.options if o not in unresolved]
        if d.context_value("use", (None, None, None))[2] == POTION:
            options.sort(key=lambda pid: -state.find_pokemon(pid)[1].damage)
        return ResolveDecision(d.player, d.id, (options[0],))
    if state.phase is Phase.MAIN:
        command = trainer_command(state)
        if command is not None:
            return command
        scripted = scripted_command(state, janken_winner=janken_winner)
        if isinstance(scripted, (UseAttack, EndTurn)):
            # 番を終える前に、手札のディフェンダーをすべてつける（v0.2e。決定では最初の選べるもの = 対戦ポケモンを選ぶ。
            # ディフェンダーのないデッキでは何もしない）
            p = state.players[state.current_player]
            defender = next((u for u in p.hand if state.cards[u].card_id == DEFENDER), None)
            if defender is not None:
                return PlayTrainer(state.current_player, defender)
        if isinstance(scripted, UseAttack):
            # ワザを使う直前に、手札のプラスパワーをすべてつける（v0.2c。プラスパワーのないデッキでは何もしない）
            p = state.players[state.current_player]
            pluspower = next((u for u in p.hand if state.cards[u].card_id == PLUSPOWER), None)
            if pluspower is not None:
                return PlayTrainer(state.current_player, pluspower)
        return scripted
    return scripted_command(state, janken_winner=janken_winner)


# ---------------------------------------------------------------- コイン（v0.2d。テスト専用の乱数の制御）

from kyuura_engine.coins import CoinSide  # noqa: E402

H, T = CoinSide.HEADS, CoinSide.TAILS


def rng_for_coins(*sides: CoinSide, start: int = 0) -> random.Random:
    """次に ``getrandbits(1)`` を len(sides) 回使うと、その結果（1 = おもて）になる乱数（テスト専用）。

    seed を 0 から順に探すので、毎回同じ乱数になる。エンジンのコインは 1 枚につき ``getrandbits(1)`` を 1 回
    使う（kyuura_engine/coins.py）。
    """
    wanted = [1 if side is CoinSide.HEADS else 0 for side in sides]
    for seed in range(start, start + 100000):
        probe = random.Random(seed)
        if [probe.getrandbits(1) for _ in wanted] == wanted:
            return random.Random(seed)
    raise AssertionError("条件に合う乱数が見つからない")


def with_coin_results(state: GameState, *sides: CoinSide) -> GameState:
    """テスト専用: 次に投げるコインの結果を ``sides`` にした状態（複製。渡した状態は変えない）。"""
    new = state.clone()
    new.rng = rng_for_coins(*sides)
    return new


def coin_events(state: GameState, since: int = 0) -> list[dict]:
    return [dict(e) for e in state.log[since:] if e["kind"] == "coin_flip"]


def coin_results(state: GameState, since: int = 0) -> list[str]:
    return [e["result"] for e in coin_events(state, since)]


# ディフェンダー（v0.2e）を入れた 60 枚のデッキ（プラスパワー・ドードー・ほかのトレーナーと組み合わせる）
DEFENDER_DECK = expand_decklist({
    DODUO: 4, GROWLITHE: 4, RATTATA: 4, DRATINI: 4, VOLTORB: 4, BILL: 4, POTION: 2, SWITCH: 2, PLUSPOWER: 4, DEFENDER: 4,
    FIRE: 24,
})
DEFENDER_DECK_B = expand_decklist({
    STARYU: 4, SEEL: 4, DIGLETT: 4, MACHOP: 4, HITMONCHAN: 4, BILL: 2, PLUSPOWER: 2, DEFENDER: 4, WATER: 16, FIGHTING: 16,
})

# ピカチュウ（v0.2f）を入れた 60 枚のデッキ（両方にピカチュウ。プラスパワー・ディフェンダー・ドードーと組み合わせる）
PIKACHU_DECK = expand_decklist({
    PIKACHU: 4, RATTATA: 4, VOLTORB: 4, DRATINI: 4, DODUO: 4, PLUSPOWER: 4, DEFENDER: 4, BILL: 2, LIGHTNING: 30,
})
PIKACHU_DECK_B = expand_decklist({
    PIKACHU: 4, DIGLETT: 4, MACHOP: 4, HITMONCHAN: 4, RATTATA: 4, PLUSPOWER: 2, DEFENDER: 2, LIGHTNING: 18, FIGHTING: 18,
})

# ドードー（v0.2d）を入れた 60 枚のデッキ（たねポケモン 20 枚 + トレーナー + 基本エネルギー）
DODUO_DECK = expand_decklist({DODUO: 4, GROWLITHE: 4, PONYTA: 4, RATTATA: 4, VOLTORB: 4, FIRE: 40})
DODUO_TRAINER_DECK = expand_decklist({
    DODUO: 4, GROWLITHE: 4, RATTATA: 4, DRATINI: 4, VOLTORB: 4, BILL: 4, POTION: 2, SWITCH: 2, PLUSPOWER: 4, FIRE: 28,
})

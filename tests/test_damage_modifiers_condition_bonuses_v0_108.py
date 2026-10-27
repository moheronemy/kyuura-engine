"""v0.108（docs/damage-modifiers-condition-bonuses-v0.108.md）: 持続するダメージの変更・相手の特殊状態を参照するポケモンの 5 枚（ワザ 10）と、使うワザのダメージを減らす効果
（マイナスイオン・あまえる）・ダメージのあとの受けるダメージの増加（かみくだく）・相手の特殊状態で決まる追加とどく・回復（もうどく・たたきおこす）。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面。5 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録
（GR-2000-P321-DAMAGE-ORDER・GR-2000-P321-ATTACK-DAMAGE・GR-2000-P322-PERSISTENT-EFFECTS・GR-2000-P321-PREVENTED-ELEMENTS・p.322 の特殊状態・RUL-ENERGY-DISCARD-ATTACKS・
v0.92 のいやなおと・v0.103 の発生元）。英語版の文面・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。盤面は
``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.108``）。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import pickle
import unittest
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    EvolvePokemon,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UseAttack,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.continuous import power_suppressors
from kyuura_engine.decisions import (
    DAMAGE_REDUCTION,
    DAMAGE_STEP_ORDER,
    DISCARD_ENERGY,
    REACTION_SWITCH,
    SELECT_ATTACK,
    SPLIT_FROM_DECK,
)
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.persistent import (
    period_active,
    reduced_damage_to_source,
)
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.preflight import MAX_BRANCHES
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import (
    PERIOD_AMOUNT_TYPES,
    PERIOD_EFFECT_TYPES,
    AttackBarrier,
    AttackEffectGuard,
    DealtAttackDamageReduction,
    HalvedDamage,
    ReceivedAttackDamageBonus,
    ReducedDamageToSource,
    ReducedDamageToSourceNextTurn,
)
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.log_audit import LATEST_FORMAT, log_problems
from tests.release_catalog import cards_after, cards_before
from tests.test_counter_keep_energy_protection_v0_101 import attack
from tests.test_counts_coins_compositions_v0_106 import with_effects
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_power_suppression_lasting_locks_v0_92 import end, removed
from tests.test_unown_family_powers_v0_96 import TURN, board, same_answers, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "damage-modifiers-condition-bonuses-v0.108.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, F, L, G, PS, R, C2, DARK = H.WATER, H.FIGHTING, H.LIGHTNING, H.GRASS, H.PSYCHIC, H.FIRE, H.DOUBLE_COLORLESS_ENERGY, H.DARKNESS_ENERGY_NEO1
HOUNDOOM, CHINCHOU, TOGEPI, DARK_WIGGLYTUFF, ARBOK = "neo2-041", "neo3-024", "neo4-088", "neo4-091", "ES3-001"
V0108 = (HOUNDOOM, CHINCHOU, TOGEPI, DARK_WIGGLYTUFF, ARBOK)
V0108_ATTACKS = [AttackKey(card, index) for card in V0108 for index in range(2)]
HOUNDOUR, JIGGLYPUFF, EKANS = "neo2-012", "PMCG2-035", "PMCG4-001"
DARK_HOUNDOUR = "neo2-039"  # デルビル（かみつく（無）10・ごうだつ）。悪タイプ
CHANSEY, RATTATA, MACHOP, MACHOKE, MACHAMP, CLEFABLE, CLEFAIRY, HAUNTER = (H.CHANSEY, H.RATTATA, H.MACHOP, H.MACHOKE, H.MACHAMP, H.CLEFABLE, H.CLEFAIRY,
                                                                          H.HAUNTER)
MEW, PINECO, GEODUDE, SNORLAX, ONIX_SCREECH = "PR1-005", "neo2-005", "ES1-023", H.SNORLAX, "neo1-050"
KOFFING, TENTACRUEL = H.KOFFING_ES2, "GD2-004"  # ［ぶんれつ］のドガース・［にげこむ］のカスミのドククラゲ
BELOW = {HOUNDOOM: [HOUNDOUR], DARK_WIGGLYTUFF: [JIGGLYPUFF], ARBOK: [EKANS], MACHOKE: [MACHOP], MACHAMP: [MACHOP, MACHOKE], CLEFABLE: [CLEFAIRY],
         HAUNTER: [H.GASTLY], H.MUK: [H.GRIMER], TENTACRUEL: ["GD2-003"]}

# 依頼で示された固定データの日本語（写しの文面と照らす。広い正規化をしない）。(HP, タイプ, 段階, 弱点, 抵抗力, にげる, 進化元, (名前, 必要なエネルギー, ダメージの目安, 説明), ...)
CRUNCH = "次の相手の番と、次の自分の番、このワザを受けた相手が、ワザによるダメージを受けるとき、そのダメージは「+20」される。"
FLAMETHROWER = "自分についている「炎」エネルギーカードを1枚トラッシュする。トラッシュできないとき、このワザのダメージはなくなる。"
PLUS_ION = "コインを投げて「おもて」なら、10ダメージを追加する。"
MINUS_ION = "次の相手の番、このワザを受けた相手が使うワザによるダメージは「-10」される。"
CHARM = "次の相手の番、このワザを受けた相手が使うワザによるダメージは、「-10」される(ダメージ以外の効果はそのまま)。"
SPIKE_TACKLE = "自分にも10ダメージ。"
DARK_SONG = "コインを投げて「おもて」なら、相手を「ねむり」状態にする。「うら」なら、相手を「こんらん」状態にする。"
SLAP_AWAKE = "相手が「ねむり」または「こんらん」状態なら、20ダメージを追加する。その後、相手を「ねむり」または「こんらん」状態から回復させる。"
WRAP = "コインを投げて「おもて」なら、相手を「マヒ」状態にする。"
TOXIC = "相手を「どく」状態にする。このワザを受ける前から相手が「どく」状態なら、10ダメージを追加する。"
QUOTED = {
    HOUNDOOM: (70, "darkness", "stage1", None, ("psychic", 30), 1, "デルビル", ("かみくだく", ("darkness", "colorless", "colorless"), "30", CRUNCH),
               ("かえんほうしゃ", ("fire", "fire", "colorless"), "50", FLAMETHROWER)),
    CHINCHOU: (50, "lightning", "basic", "fighting", None, 1, None, ("プラスイオン", ("lightning",), "10+", PLUS_ION), ("マイナスイオン", ("water",), "10", MINUS_ION)),
    TOGEPI: (40, "colorless", "basic", None, ("psychic", 30), 1, None, ("あまえる", ("colorless",), None, CHARM),
             ("とげたまタックル", ("colorless", "colorless"), "20", SPIKE_TACKLE)),
    DARK_WIGGLYTUFF: (60, "colorless", "stage1", "fighting", ("psychic", 30), 2, "プリン", ("わるいうた", ("colorless", "colorless"), None, DARK_SONG),
                      ("たたきおこす", ("colorless",) * 3, "20+", SLAP_AWAKE)),
    ARBOK: (60, "grass", "stage1", "psychic", None, 2, "アーボ", ("まきつく", ("grass", "colorless"), "20", WRAP), ("もうどく", ("grass",) * 3, "30+", TOXIC)),
}
EXPECTED = {
    (HOUNDOOM, 0): E.DamageThenReceivedAttackDamageBonus(20, 1, 2), (HOUNDOOM, 1): E.DiscardEnergyThenDamage(E.EnergyType.FIRE),
    (CHINCHOU, 0): E.CoinBonusDamage(10), (CHINCHOU, 1): E.DamageThenDealtDamageReduction(10),
    (TOGEPI, 0): E.DealtDamageReductionWithoutDamage(10), (TOGEPI, 1): E.DamageAndSelfDamage(10),
    (DARK_WIGGLYTUFF, 0): E.StatusByCoinWithoutDamage(E.SLEEP, E.CONFUSION), (DARK_WIGGLYTUFF, 1): E.PlusIfDefenderStatusThenCure((E.SLEEP, E.CONFUSION), 20),
    (ARBOK, 0): E.ParalyzeOnHeads(), (ARBOK, 1): E.PlusIfDefenderPoisonedThenPoison(10),
}
NEW_TYPES = (E.DamageThenDealtDamageReduction, E.DealtDamageReductionWithoutDamage, E.DamageThenReceivedAttackDamageBonus, E.PlusIfDefenderPoisonedThenPoison,
             E.PlusIfDefenderStatusThenCure)
DEALT = f"（{DealtAttackDamageReduction.kind}）"
BONUS = f"（{ReceivedAttackDamageBonus.kind}）"


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def answer(state, choices, *coins, player=None):
    d = state.decision
    return apply_kernel(with_coin_results(state, *coins) if coins else state, ResolveDecision(d.player if player is None else player, d.id, tuple(choices)))


def kinds(before, after, *names):
    return [e["kind"] for e in new_events(before, after, *names)]


def pid_of(state):
    """場のポケモンのいちばん上のカード → 場のポケモンの番号（ログ ``damage`` は ``pokemon_id`` を持たないので、ワザの前の場から引く）。"""
    return {p.card: p.pokemon_id for player in state.players for p in player.in_play()}


def hits(before, after):
    """ワザのダメージの (受けたポケモンの番号, 受けた場所（target。なければ相手の対戦ポケモン）, 基本となるダメージ, 2 段階の記録, 8 段階の +20 の記録, 最終ダメージ)（ログの順）。"""
    ids = pid_of(before)
    found = []
    for e in new_events(before, after, "damage"):
        steps = [tuple(s) for s in e.get("steps") or ()]
        found.append((e.get("pokemon_id", ids.get(e["pokemon"])), e.get("target") or "opponent_active", steps[0][1] if steps else None,
                      [s for s in steps if str(s[0]).startswith("2 ")], [s for s in steps if str(s[0]).startswith("8 ") and str(s[0]).endswith(BONUS)], e["amount"]))
    return found


def conditions(before, after):
    """付けた特殊状態の (ポケモンの番号, 特殊状態, どくのダメージ)（すでにその状態だったものを含む。already は 4 つめ）。"""
    return [(e["pokemon_id"], e["condition"], e.get("damage"), bool(e.get("already"))) for e in new_events(before, after, "special_condition")]


def cured(before, after):
    """ワザの効果で回復させた (ポケモンの番号, 回復した状態, 理由)（ポケモンチェックのねむりのコインでの回復は含めない）。"""
    return [(e["pokemon_id"], tuple(e["conditions"]), e["reason"]) for e in new_events(before, after, "special_conditions_removed") if e["reason"] == "cured"]


def attack_coins(before, after):
    return [e["result"] for e in new_events(before, after, "coin_flip") if e.get("source") == "attack"]


def given(before, after, kind=None):
    return [(e["pokemon_id"], e["persistent_effect"], e["active_turn"], e.get("end_turn"), e.get("amount"), e.get("source_pokemon"))
            for e in new_events(before, after, "persistent_effect_added") if kind is None or e["persistent_effect"] == kind]


def reductions_on(pokemon):
    return [e for e in pokemon.persistent_effects if isinstance(e, DealtAttackDamageReduction)]


def uid_in_hand(state, card_id, player=0):
    return next(u for u in state.players[player].hand if state.cards[u].card_id == card_id)


def play(state, card_id, player=0):
    return apply_kernel(state, PlayTrainer(player, uid_in_hand(state, card_id, player)))


def negative_ion(opponent, **kw):
    """チョンチーのマイナスイオンを相手に使った盤面（相手の番。与えた番 + 1）。"""
    state = board(mon(CHINCHOU, (W,)), opponent=opponent, **kw)
    return state, attack(state, 1)


def reduction_of(state, pid, player=1):
    pokemon = next(p for p in state.players[player].in_play() if p.pokemon_id == pid)
    return reductions_on(pokemon)


# ---------------------------------------------------------------- 1・2・3 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        """5 枚・10 のワザの名前・必要なエネルギー・ダメージの目安・説明と、HP・タイプ・段階・弱点・抵抗力・にげる・進化元は依頼の日本語・固定データと同じ。特殊能力は 0。
        チョンチーのマイナスイオンは水のまま、トゲピーは「たね」（ベイビィではない）。"""
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_108"]), V0108)
        self.assertEqual(len(V0108_ATTACKS), 10)
        for card, (hp, color, stage, weakness, resistance, retreat, below, *attacks) in QUOTED.items():
            definition = pool.definitions[card]
            with self.subTest(card=card):
                self.assertEqual((definition.hp, definition.pokemon_type.value, definition.stage, definition.powers), (hp, color, stage, ()))
                self.assertEqual(None if definition.weakness is None else definition.weakness.value, weakness)
                self.assertEqual(None if definition.resistance is None else (definition.resistance.value, definition.resistance_value), resistance)
                self.assertEqual((definition.retreat_cost, definition.evolves_from), (retreat, below))
                self.assertIn(card, pool.playable_ids)
                self.assertEqual(len(definition.attacks), len(attacks))
            for index, (name, cost, display, text) in enumerate(attacks):
                printed = definition.attacks[index]
                with self.subTest(card=card, index=index):
                    self.assertEqual((printed.name_ja, tuple(t.value for t in printed.cost), printed.damage_display, printed.text_ja), (name, cost, display, text))
                    entry = DEFAULT_EFFECTS.attack_entry(card, index)
                    self.assertEqual(entry.effect, EXPECTED[(card, index)])
                    self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (name, text, text, "kyuura data/cards.json"))
                    self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, printed, definition.attacks))
        self.assertEqual(pool.definitions[CHINCHOU].attacks[1].cost[0].value, "water")
        self.assertEqual(pool.definitions[TOGEPI].stage, "basic")

    def test_names_sources_and_gaps(self):
        """新しい名前はヘルガー・わるいプクリン（クイズの名前の候補）。進化元のデルビル・プリン・アーボは写しにある。アーボックの図鑑番号・レベルの欠けは補わない。同じデータの組はない。"""
        pool = load_card_pool()
        cards = {c["id"]: c for c in read_extract()["cards"]}
        names = {d.name_ja for c, d in pool.definitions.items() if c in pool.playable_ids}
        for name in ("デルビル", "プリン", "アーボ", "ヘルガー", "わるいプクリン"):
            self.assertIn(name, names)
        self.assertEqual({card: cards[card]["data_gaps"] for card in V0108}, {HOUNDOOM: [], CHINCHOU: [], TOGEPI: [], DARK_WIGGLYTUFF: [], ARBOK: ["pokemon.dex", "jp_print.level"]})
        self.assertEqual({card: cards[card]["same_card_group"] for card in V0108}, dict.fromkeys(V0108))
        hosts = {card: cards[card]["ja_text_source"].split("/")[2] for card in V0108}
        self.assertEqual(hosts, {HOUNDOOM: "nazonobasho.com", CHINCHOU: "wiki.pokemonwiki.com", TOGEPI: "wiki.pokemonwiki.com", DARK_WIGGLYTUFF: "wiki.pokemonwiki.com",
                                 ARBOK: "pcg-search.com"})

    def test_programs(self):
        """新しい型の要素の並び。使うワザのダメージを減らす効果・回復は新しい要素、+20 は v0.92 の要素、どくは既存の要素。状態の確かめは並びの最初（ダメージの前）。"""
        builders = {
            E.DamageThenDealtDamageReduction(10): (P.Damage(P.OPP, P.Printed()), P.OpponentDealtDamageReduction(10)),
            E.DealtDamageReductionWithoutDamage(10): (P.OpponentDealtDamageReduction(10),),
            E.DamageThenReceivedAttackDamageBonus(20, 1, 2): (P.Damage(P.OPP, P.Printed()), P.OpponentDamageTakenBonus(20, 1, 2)),
            E.PlusIfDefenderPoisonedThenPoison(10): (P.OpponentStatusCheck("opponent_status_before", (E.POISON,)),
                                                     P.Damage(P.OPP, P.PlusIfResult("opponent_status_before", 10)), P.Status(E.POISON)),
            E.PlusIfDefenderStatusThenCure((E.SLEEP, E.CONFUSION), 20): (
                P.OpponentStatusCheck("opponent_status_before", (E.SLEEP, E.CONFUSION)), P.Damage(P.OPP, P.PlusIfResult("opponent_status_before", 20)),
                P.CureOpponentConditions((E.SLEEP, E.CONFUSION))),
            E.StatusByCoinWithoutDamage(E.SLEEP, E.CONFUSION): (P.Status(E.SLEEP, local_coin=HD, otherwise=E.CONFUSION),),
        }
        for effect, program in builders.items():
            with self.subTest(effect=effect):
                self.assertEqual(P.BUILDERS[type(effect)](effect), program)
                self.assertEqual(P.compile_attack(effect), program)
                self.assertFalse(P.program_may_fail(program))
        for cls in NEW_TYPES:
            self.assertIn(cls, H.ATTACK_TYPES_SINCE_V0_17)
            self.assertIs(cls.resolve, E.AttackEffect.resolve)
        # 相手への効果の宣言（G37 の確かめに使う）に、与えるダメージの変更・受けるダメージの変更・どく・回復を含める。並びから求めた値と同じ
        declared = {E.DamageThenDealtDamageReduction(10): (E.DEALT_DAMAGE_ELEMENT,), E.DealtDamageReductionWithoutDamage(10): (E.DEALT_DAMAGE_ELEMENT,),
                    E.DamageThenReceivedAttackDamageBonus(20, 1, 2): (E.DAMAGE_TAKEN_ELEMENT,), E.PlusIfDefenderPoisonedThenPoison(10): (E.POISON,),
                    E.PlusIfDefenderStatusThenCure((E.SLEEP, E.CONFUSION), 20): (E.CURE_ELEMENT,)}
        for effect, elements in declared.items():
            self.assertEqual(effect.opponent_effect_elements, elements)
            self.assertEqual(P.opponent_effect_elements(P.compile_attack(effect)), elements)
        self.assertIn(E.DEALT_DAMAGE_ELEMENT, E.ATTACK_ELEMENTS)
        self.assertNotEqual(E.DEALT_DAMAGE_ELEMENT, E.REDUCED_DAMAGE_ELEMENT)
        # 新しい持続する効果は期間を明示した効果の型（期間・書き出し・不変条件を共通に読む）。なきつくの型の部分型ではない（なきつくの問い合わせに拾われない）
        self.assertIn(DealtAttackDamageReduction, PERIOD_EFFECT_TYPES)
        self.assertEqual(PERIOD_AMOUNT_TYPES, (ReceivedAttackDamageBonus, DealtAttackDamageReduction))
        self.assertFalse(issubclass(DealtAttackDamageReduction, ReducedDamageToSource))
        self.assertEqual(E.DamageThenDealtDamageReduction(10).period_terms(), (DealtAttackDamageReduction, 1, 1, False, (), 10))
        self.assertEqual(E.DamageThenReceivedAttackDamageBonus(20, 1, 2).period_terms(), (ReceivedAttackDamageBonus, 1, 2, False, (), 20))

    def test_reused_types_match_the_printed_text(self):
        """既存の型の 4 つのワザ（プラスイオン・とげたまタックル・まきつく・かえんほうしゃ）は全文で照らす。かえんほうしゃは既存の書き方の「none」（ダメージはなくなる）で、「zero」（0 に
        なる）・ほかの色では受け付けない。わるいうたは (ねむり, こんらん) の組に結び付けた書き方だけで通る。"""
        pool = load_card_pool()
        flame = pool.definitions[HOUNDOOM].attacks[1]
        self.assertEqual(flame.text_ja, E.DISCARD_ENERGY_THEN_DAMAGE_TEXTS["none"][2].format(ja="炎"))
        self.assertEqual(E.DiscardEnergyThenDamage(E.EnergyType.FIRE).check(flame), [])
        for wrong in (E.DiscardEnergyThenDamage(E.EnergyType.FIRE, "zero"), E.DiscardEnergyThenDamage(E.EnergyType.WATER)):
            self.assertNotEqual(wrong.check(flame), [])
        for changed in (FLAMETHROWER.replace("1枚", "2枚"), FLAMETHROWER.replace("なくなる", "0になる"), FLAMETHROWER.replace("「炎」", "「水」")):
            self.assertNotEqual(E.DiscardEnergyThenDamage(E.EnergyType.FIRE).check(dataclasses.replace(flame, text_ja=changed)), [])
        self.assertEqual(E.CoinBonusDamage(10).check(pool.definitions[CHINCHOU].attacks[0]), [])
        self.assertNotEqual(E.CoinBonusDamage(20).check(pool.definitions[CHINCHOU].attacks[0]), [])
        # とげたまタックル: 既存の型 DamageAndSelfDamage の確かめは形だけ（説明文・自分へのダメージの数を見ない。既存の型の確かめは一括で直さない）ので、全文と登録の数を照らす
        tackle = pool.definitions[TOGEPI].attacks[1]
        self.assertEqual((E.DamageAndSelfDamage(10).check(tackle), tackle.text_ja, DEFAULT_EFFECTS.attack_entry(TOGEPI, 1).effect.self_damage), ([], SPIKE_TACKLE, 10))
        self.assertEqual(E.ParalyzeOnHeads().check(pool.definitions[ARBOK].attacks[0]), [])
        song = pool.definitions[DARK_WIGGLYTUFF].attacks[0]
        self.assertEqual(E.StatusByCoinWithoutDamage(E.SLEEP, E.CONFUSION).check(song), [])
        for wrong in (E.StatusByCoinWithoutDamage(E.CONFUSION, E.SLEEP), E.StatusByCoinWithoutDamage(E.SLEEP, E.PARALYSIS), E.DamageThenStatusByCoin(E.SLEEP, E.CONFUSION)):
            self.assertNotEqual(wrong.check(song), [])
        self.assertEqual(dict(E.DARK_SONG_TEXTS), {(E.SLEEP, E.CONFUSION): (DARK_SONG,)})
        # v0.70 のぐるぐる（ニョロゾ）の書き方は変えない
        self.assertEqual(E.StatusByCoinWithoutDamage(E.CONFUSION, E.SLEEP).check(dataclasses.replace(song, text_ja=(
            "コインを投げて「おもて」なら、相手を「こんらん」状態に、「うら」なら「ねむり」状態にする。"))), [])

    def test_new_texts_are_bound_to_their_values(self):
        """新しい型・書き方は値・形と結び付けた完全な一致だけ。取り違えた量・範囲・期間・状態・ダメージの形（なきつく・なきごえ・ダメージのないいやなおと・ゴルバットの期間・特殊などく・
        どく・マヒでの追加）を拒否する。"""
        pool = load_card_pool()
        minus, charm = pool.definitions[CHINCHOU].attacks[1], pool.definitions[TOGEPI].attacks[0]
        self.assertEqual(E.DamageThenDealtDamageReduction(10).check(minus), [])
        self.assertEqual(E.DealtDamageReductionWithoutDamage(10).check(charm), [])
        for wrong, printed in ((E.DealtDamageReductionWithoutDamage(10), minus), (E.DamageThenDealtDamageReduction(10), charm),
                               (E.ReduceDamageToSelfNextOpponentTurn(10), charm), (E.DamageThenReduceDamageToSelf(10), minus)):
            self.assertNotEqual(wrong.check(printed), [], (wrong, printed.name_ja))
        for printed, text in ((minus, MINUS_ION.replace("-10", "-20")), (minus, MINUS_ION.replace("使うワザによるダメージ", "このカードに与えるダメージ")),
                              (charm, CHARM.replace("(ダメージ以外の効果はそのまま)", "")), (minus, MINUS_ION.replace("次の相手の番", "次の自分の番"))):
            effect = EXPECTED[(CHINCHOU, 1)] if printed is minus else EXPECTED[(TOGEPI, 0)]
            self.assertNotEqual(effect.check(dataclasses.replace(printed, text_ja=text)), [])
        for amount in (20, 0):
            with self.assertRaises(ValueError):
                E.DamageThenDealtDamageReduction(amount)
        crunch = pool.definitions[HOUNDOOM].attacks[0]
        self.assertEqual(crunch.text_ja, E.SCREECH_TEXTS[(20, 1, 2)][0])
        self.assertEqual(E.DamageThenReceivedAttackDamageBonus(20, 1, 2).check(crunch), [])
        self.assertNotEqual(E.ReceivedAttackDamageBonusAttack(20, 1, 2).check(crunch), [])  # v0.92 の型（ダメージの目安なし）の形の確かめは変えない
        self.assertNotEqual(E.DamageThenReceivedAttackDamageBonus(20, 0, 2).check(crunch), [])  # ゴルバットの期間
        with self.assertRaises(ValueError):
            E.DamageThenReceivedAttackDamageBonus(20, 1, 3)
        toxic, slap = pool.definitions[ARBOK].attacks[1], pool.definitions[DARK_WIGGLYTUFF].attacks[1]
        self.assertEqual(E.PlusIfDefenderPoisonedThenPoison(10).check(toxic), [])
        self.assertNotEqual(E.PlusIfDefenderPoisonedThenPoison(10).check(slap), [])
        self.assertNotEqual(E.PlusIfDefenderPoisonedThenPoison(10).check(dataclasses.replace(toxic, text_ja=TOXIC.replace("10ダメージ", "20ダメージ"))), [])
        self.assertNotEqual(E.PlusIfDefenderPoisonedThenPoison(10).check(dataclasses.replace(toxic, damage_modifier=None)), [])
        with self.assertRaises(ValueError):
            E.PlusIfDefenderPoisonedThenPoison(20)
        self.assertEqual(E.PlusIfDefenderStatusThenCure((E.SLEEP, E.CONFUSION), 20).check(slap), [])
        self.assertNotEqual(E.PlusIfDefenderStatusThenCure((E.SLEEP, E.CONFUSION), 20).check(toxic), [])
        for changed in (SLAP_AWAKE.replace("「こんらん」状態から", "「どく」状態から"), SLAP_AWAKE.replace("20ダメージ", "30ダメージ")):
            self.assertNotEqual(E.PlusIfDefenderStatusThenCure((E.SLEEP, E.CONFUSION), 20).check(dataclasses.replace(slap, text_ja=changed)), [])
        for conditions, bonus in (((E.SLEEP, E.PARALYSIS), 20), ((E.SLEEP,), 20), ((E.CONFUSION, E.SLEEP), 20), ((E.SLEEP, E.CONFUSION), 10)):
            with self.assertRaises(ValueError):
                E.PlusIfDefenderStatusThenCure(conditions, bonus)

    def test_unregistered_without_the_v0_108_entries(self):
        """今回の登録だけを除くと、ちょうど 5 枚が未対応にもどる（ほかのカードは失われない）。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V0108_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V0108))
        self.assertEqual(set(V0108) & set(cards_before(read_extract(), "0.108")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.107")) & set(cards_before(read_extract(), "0.109")), set(V0108))

    def test_adoption_records(self):
        """5 件の採用の記録（kyuura 73a1690・外部照合なし・kyuura の記録なし）。処理に使う文面は 10 のワザとも印刷の文面。"""
        sources = json.loads((ROOT / "kyuura_engine/data/card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine/data/research_links.json").read_text(encoding="utf-8"))["latest_descriptions"]["adopted_printed_text"]
        for card in V0108:
            record = sources[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"], record["external_checks"], record["issues"],
                                  record["recorded_on"]), ("kyuura_data", "adopted", "73a169063463bbf7bcaa3137d70cbf9721d11534", [], [], [], "2026-10-27"))
                self.assertEqual(record["play_text"], {"attack/0": "kyuura_printed_text", "attack/1": "kyuura_printed_text"})
                for part in ("attack/0", "attack/1"):
                    self.assertIn(f"{card}/{part}", links)
        self.assertEqual(len([key for key in links if key.split("/")[0] in V0108]), 10)
        self.assertIn("RUL-ENERGY-DISCARD-ATTACKS", sources[HOUNDOOM]["notes"])


# ---------------------------------------------------------------- 4 章: マイナスイオン・あまえる（使うワザのダメージの -10）


class DealtReductionTest(unittest.TestCase):
    def test_given_after_damage_and_active_only_next_opponent_turn(self):
        """マイナスイオン: 相手に 10 のあと、相手の対戦ポケモンに次の相手の番（与えた番 + 1）だけはたらく効果。与えた番の続きにははたらかず、その番の終わりに消える。"""
        state, done = negative_ion(mon(RATTATA, (W,)))
        target = state.players[1].active.pokemon_id
        self.assertEqual([h[2:] for h in hits(state, done)], [(10, [], [], 10)])
        self.assertEqual(kinds(state, done, "damage", "persistent_effect_added"), ["damage", "persistent_effect_added"])
        self.assertEqual(given(state, done), [(target, DealtAttackDamageReduction.kind, TURN + 1, TURN + 1, 10, state.players[0].active.pokemon_id)])
        (effect,) = reduction_of(done, target)
        self.assertEqual((effect.created_turn, effect.source_player, effect.ends_on, effect.while_source_active), (TURN, 0, (), False))
        self.assertEqual(done.turn_number, TURN + 1)
        self.assertTrue(period_active(done, effect))
        audited(self, done)
        gone = end(done)
        self.assertEqual(removed(done, gone), [(DealtAttackDamageReduction.kind, "expired")])
        self.assertEqual(reductions_on(gone.players[1].active), [])
        audited(self, gone)

    def test_charm_has_no_damage_element(self):
        """あまえる: ダメージの要素・ログ damage はなく、効果だけを与える（括弧の「ダメージ以外の効果はそのまま」）。"""
        state = board(mon(TOGEPI, (W,)), opponent=mon(RATTATA, (W,)))
        done = attack(state, 0)
        self.assertEqual((kinds(state, done, "damage", "damage_prevented"), [g[1:5] for g in given(state, done)]),
                         ([], [(DealtAttackDamageReduction.kind, TURN + 1, TURN + 1, 10)]))
        audited(self, done)

    def test_reduces_the_holder_attack_at_step_2(self):
        """受けたポケモンが使うワザ（コラッタのかみつく 20）は p.321 の 2 段階で -10。受ける側の 8 段階の軽減ではない。"""
        for card, index in ((CHINCHOU, 1), (TOGEPI, 0)):
            state = board(mon(card, (W,)), opponent=mon(RATTATA, (W,)))
            given_state = attack(state, index)
            hit = attack(given_state, 0)
            with self.subTest(card=card):
                ((_, place, base, step2, bonus, final),) = hits(given_state, hit)
                self.assertEqual((place, base, step2, bonus, final), ("opponent_active", 20, [(f"2 {state.card_def(state.players[0].active.card).name_ja}{DEALT}", 10)], [], 10))
                audited(self, hit)

    def test_before_weakness(self):
        """2 段階なので弱点の前: ワンリキーのローキック 20 は、チョンチー（弱点 闘）に (20 - 10) × 2 = 20（弱点のあとに 10 引く 30 ではない）。"""
        _, given_state = negative_ion(mon(MACHOP, (F,)))
        hit = attack(given_state, 0)
        self.assertEqual([h[2:] for h in hits(given_state, hit)], [(20, [("2 チョンチー" + DEALT, 10)], [], 20)])
        self.assertTrue(new_events(given_state, hit, "damage")[0]["weakness"])

    def test_zero_at_step_2_is_not_revived(self):
        """2 段階までで 0 以下なら計算を終える: 悪タイプのデルビル（悪エネルギーの 5 段階の +10）のかみつく 10 は 0。受ける側のいやなおとの +20（8 段階）も加えない。"""
        _, given_state = negative_ion(mon(DARK_HOUNDOUR, (DARK,)))
        receiver = given_state.players[0].active
        bonus = ReceivedAttackDamageBonus(given_state.players[1].active.card, 1, TURN - 1, TURN, TURN + 1, given_state.players[1].active.pokemon_id, 20)
        with_effects(given_state, 0, bonus, keys=(f"{ONIX_SCREECH}#0",))
        self.assertTrue(period_active(given_state, bonus))
        hit = attack(given_state, 0)
        (event,) = new_events(given_state, hit, "damage")
        self.assertEqual((event["amount"], [tuple(s) for s in event["steps"]]), (0, [("1 基本となる計算", 10), ("2 チョンチー" + DEALT, 0)]))
        self.assertEqual(hit.players[0].active.damage, receiver.damage)

    def test_other_receivers_bench_and_self_damage(self):
        """だれが受けるかを限らない: 突風で入れ替わった別の対戦ポケモン（元の使い手のチョンチーは控え）・控え・自分へのダメージも -10（クヌギダマのとつぜんじばくの「おもて」: 相手 40 → 30、
        自分 40 → 30、おたがいの控え 10 → 0）。"""
        _, given_state = negative_ion(mon(PINECO, (G,)), bench=(RATTATA,), opponent_hand=(H.GUST,))
        gusted = play(given_state, H.GUST, player=1)
        gusted = answer(gusted, gusted.decision.options[:1])
        self.assertEqual(gusted.cards[gusted.players[0].bench[0].card].card_id, CHINCHOU)
        boom = attack(gusted, 0, HD)
        found = [(place, base, step2[0][1] if step2 else None, final) for _, place, base, step2, _, final in hits(gusted, boom)]
        self.assertEqual(found, [("opponent_active", 40, 30, 30), ("self", 40, 30, 30), ("opponent_bench", 10, 0, 0), ("self_bench", 10, 0, 0)])
        audited(self, boom)

    def test_old_growl_scope_is_unchanged_and_not_doubled(self):
        """なきごえ（「このカード」に与えるダメージだけ）は v0.76 の範囲のまま。-10 は旧問い合わせ ``reduced_damage_to_source`` に拾われない（元の使い手へのダメージを二重に減らさない）。
        両方を受けたポケモンは、なきごえの発生源のカードへは 2 つ（-20）、ほかへは -10 だけ。"""
        _, given_state = negative_ion(mon(H.MAGIKARP, (W,)))
        holder = given_state.players[1].active
        self.assertIsNone(reduced_damage_to_source(given_state, holder))
        chinchou = given_state.players[0].active
        growl = ReducedDamageToSourceNextTurn(chinchou.card, 0, TURN, TURN + 1, 10)
        trial = given_state.clone()
        trial.players[1].active.persistent_effects = (*trial.players[1].active.persistent_effects, growl)
        modifiers = E.attack_damage_modifiers(trial, trial.players[1].active, trial.players[0].active, attack=AttackKey(H.MAGIKARP, 0))
        self.assertEqual(sorted((m.step, m.amount) for m in modifiers), [(2, -10), (2, -10)])
        bench = trial.players[0].bench[0]
        modifiers = E.attack_damage_modifiers(trial, trial.players[1].active, bench, attack=AttackKey(H.MAGIKARP, 0), bench=True)
        self.assertEqual([(m.step, m.amount, m.label) for m in modifiers], [(2, -10, "チョンチー" + DEALT)])

    def test_not_for_powers_poison_or_confusion(self):
        """特殊能力のダメージ（カイリキーの［はんげき］の 10）は使うワザのダメージではないので、-10 を受けたカイリキーが与えても減らさない（仕組みの確かめのため、相手の番にはたらく -10 を
        置いた盤面）。どくのダメージも変えない。こんらんの 20 は「使うワザによるダメージ」か決まらない既存の問い（UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS。こんらんのコインの前に止める）。"""
        state = board(mon(H.MAGIKARP, (W,)), opponent=mon(MACHAMP, (F,)))
        effect = DealtAttackDamageReduction(state.players[0].active.card, 0, TURN - 1, TURN, TURN, state.players[0].active.pokemon_id, 10)
        with_effects(state, 1, effect, keys=(f"{CHINCHOU}#1",))
        hit = attack(state, 0)
        self.assertEqual([h[5] for h in hits(state, hit)], [10])  # コイキングのたいあたりは -10 を受けていない
        self.assertEqual([e["amount"] for e in new_events(state, hit, "counterattack")], [10])
        state, given_state = negative_ion(mon(RATTATA, (W,), poison=10))
        checked = end(given_state)
        self.assertEqual([e["amount"] for e in new_events(given_state, checked, "poison_damage")], [10])
        state, given_state = negative_ion(mon(RATTATA, (W,), confusion=True))
        rejects(self, given_state, UseAttack(1, 0), "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS")

    def test_source_leaving_does_not_end_it_but_receiver_leaving_does(self):
        """元の使い手が場をはなれても消えない（説明に書かれていない。今の対戦ポケモンへ移さない）。受けたポケモンがベンチにもどる（にげる）・進化すると消える。"""
        _, given_state = negative_ion(mon(RATTATA, (W,)), bench=(), opponent_bench=(RATTATA,))
        knocked = given_state.clone()
        retreated = apply_kernel(given_state, Retreat(1, (), given_state.players[1].bench[0].card))  # コラッタのにげるは 0
        self.assertEqual(removed(given_state, retreated), [(DealtAttackDamageReduction.kind, "retreat")])
        self.assertEqual(reductions_on(retreated.players[1].bench[0]), [])
        self.assertEqual(reductions_on(retreated.players[1].active), [])
        audited(self, retreated)
        _, given_state = negative_ion(mon(MACHOP, (F,)), opponent_hand=(MACHOKE,))
        evolved = apply_kernel(given_state, EvolvePokemon(1, uid_in_hand(given_state, MACHOKE, 1), given_state.players[1].active.pokemon_id))
        self.assertEqual(removed(given_state, evolved), [(DealtAttackDamageReduction.kind, "evolve")])
        self.assertEqual(len(reductions_on(knocked.players[1].active)), 1)

    def test_effect_only_protection_and_neutral_shield(self):
        """相手に与える効果なので、ワザによるダメージ以外の効果を受けない相手（ひかりのはどう）には与えない（ダメージは受ける）。ミュウの［ニュートラルシールド］は、たねのチョンチー・
        トゲピーのワザには、はたらかない（発生元の今の姿の段階）。1 進化のピクシーがゆびをふるで使うマイナスイオンの効果は、使ったピクシーが発生源。"""
        state = board(mon(CHINCHOU, (W,)), opponent=mon(CHANSEY))
        chansey = state.players[1].active
        with_effects(state, 1, AttackEffectGuard(chansey.card, 1, TURN - 1, TURN), keys=("neo4-094#0",))
        done = attack(state, 1)
        self.assertEqual(([h[5] for h in hits(state, done)], given(state, done), kinds(state, done, "effect_prevented")), ([10], [], ["effect_prevented"]))
        for card, index in ((CHINCHOU, 1), (TOGEPI, 0)):
            state = board(mon(card, (W,)), opponent=mon(MEW, (PS,)))
            done = attack(state, index)
            self.assertEqual([g[1] for g in given(state, done)], [DealtAttackDamageReduction.kind])
        state = board(mon(CLEFABLE, (W,)), opponent=mon(CHINCHOU, (W,)))
        asked = attack(state, 0)
        self.assertEqual(asked.decision.kind, SELECT_ATTACK)
        done = answer(asked, (1,))
        self.assertEqual(given(asked, done), [(state.players[1].active.pokemon_id, DealtAttackDamageReduction.kind, TURN + 1, TURN + 1, 10, state.players[0].active.pokemon_id)])
        audited(self, done)

    def test_speed_star_keeps_the_attacker_side_minus_10(self):
        """受けるポケモンの持っている効果を除くワザ（タケシのサンドパンのスピードスター。弱点・抵抗力も計算しない）でも、-10 はワザを使う側の持っている効果なので除かない（黙って消さない。
        SS1 などの除く範囲の問いは変えない）: 20 - 10 = 10。"""
        _, given_state = negative_ion(mon(H.BROCKS_SANDSLASH, (F, W), evolved_from=[H.BROCKS_SANDSHREW]))
        hit = attack(given_state, 0)
        self.assertEqual([h[2:] for h in hits(given_state, hit)], [(20, [("2 チョンチー" + DEALT, 10)], [], 10)])
        audited(self, hit)

    def test_mirror_move_cannot_return_it(self):
        """オニスズメのオウムがえし（前の相手の番に受けたダメージと効果を返す）で、受けた -10 の効果を返すのは、既存のエンジンの未対応（UNSUPPORTED_MIRROR_MOVE_EFFECT。受けた効果の返し方は
        ダメージとマヒだけ）。宣言の前に止め、状態を変えない（効果のないものとして扱わない）。"""
        _, given_state = negative_ion(mon("PMCG2-034", (W, W, W)))
        rejects(self, given_state, UseAttack(1, 1), "UNSUPPORTED_MIRROR_MOVE_EFFECT")

    def test_same_step_with_set_and_multiply(self):
        """同じ 2 段階の「その数にする」（つるぎのまい）・「数をかける」（きあいだめ）と重なると、計算の順番で結果が変わるので、ワザを使うプレイヤーが順番を選ぶ（v0.35 の決定）。加算どうしは
        決定を出さない。"""
        from kyuura_engine.cards import load_card_pool as pool_of
        from kyuura_engine.damage import (
            MULTIPLY,
            DamageModifier,
            DamageOrderRequired,
            calculate_attack_damage,
        )

        pool = pool_of()
        attacker, defender = pool.definitions[RATTATA], pool.definitions[CHANSEY]
        rules = board(mon(RATTATA)).rules  # 2000.02.14 版の決まり（状態の項目）
        minus = DamageModifier(step=2, amount=-10, label="チョンチー" + DEALT, source=1)
        double = DamageModifier(step=2, amount=2, label="きあいだめ", source=2, operation=MULTIPLY)
        with self.assertRaises(DamageOrderRequired):
            calculate_attack_damage(20, attacker, defender, rules, (minus, double))
        self.assertEqual({calculate_attack_damage(20, attacker, defender, rules, (minus, double), orders={2: order}).final for order in ((0, 1), (1, 0))}, {20, 30})
        growl = DamageModifier(step=2, amount=-10, label="なきごえ", source=3)
        self.assertEqual(calculate_attack_damage(20, attacker, defender, rules, (minus, growl)).final, 0)


# ---------------------------------------------------------------- 5 章: かみくだく（30 と受けるダメージの +20）


class CrunchTest(unittest.TestCase):
    def crunched(self, opponent, **kw):
        state = board(mon(HOUNDOOM, (DARK, W, W)), opponent=opponent, **kw)
        return state, attack(state, 0)

    def test_first_damage_has_no_bonus_and_period_is_next_two_turns(self):
        """目安 30（悪エネルギーの 5 段階の +10 で 40）のあと、与えた番 + 1〜+ 2 の +20。最初の 30 には加えない。次の自分の番のかみくだく 30 は 8 段階で +20、その番の終わりに消える。"""
        state, done = self.crunched(mon(CHANSEY))
        target = state.players[1].active.pokemon_id
        self.assertEqual([h[2:] for h in hits(state, done)], [(30, [], [], 40)])
        self.assertEqual(given(state, done), [(target, ReceivedAttackDamageBonus.kind, TURN + 1, TURN + 2, 20, state.players[0].active.pokemon_id)])
        audited(self, done)
        mine = end(done)
        again = attack(mine, 0)  # 自分の番（与えた番 + 2）。ワザのあと、その番の終わりに消える（新しく与えた効果は残る）
        ((_, _, base, _, bonus, final),) = hits(mine, again)
        self.assertEqual((base, bonus, final), (30, [("8 ヘルガー" + BONUS, 60)], 60))
        self.assertEqual(removed(mine, again), [(ReceivedAttackDamageBonus.kind, "expired")])
        self.assertEqual([(e.created_turn, e.end_turn) for e in again.players[1].active.persistent_effects], [(TURN + 2, TURN + 4)])
        audited(self, again)

    def test_receiver_own_self_damage_next_opponent_turn(self):
        """次の相手の番: 受けたラッキー自身のすてみタックルの自分へのダメージ 80（ワザによるダメージ。GR-2000-P321-ATTACK-DAMAGE）も 8 段階で +20 の 100。相手（ヘルガー）へのダメージは
        ヘルガーが受ける効果ではないので 80 のまま（+20 は受けたポケモンが受けるダメージだけ）。"""
        _, done = self.crunched(mon(CHANSEY, (W, W, W, W)))
        tackle = attack(done, 1)
        found = [(place, base, bonus, final) for _, place, base, _, bonus, final in hits(done, tackle)]
        self.assertEqual(found, [("opponent_active", 80, [], 80), ("self", 80, [("8 ヘルガー" + BONUS, 100)], 100)])

    def test_knocked_out_or_effect_protected_target_gets_no_bonus(self):
        """30（+10）で相手が HP 以上なら与えない。ワザによるダメージ以外の効果を受けない相手（ひかりのはどう）には、ダメージは与えるが効果は与えない。1 進化のヘルガーのワザは
        ミュウの［ニュートラルシールド］でダメージも効果も受けない。"""
        state, done = self.crunched(mon(RATTATA, (W,)), opponent_bench=(RATTATA,))
        self.assertEqual((kinds(state, done, "knock_out"), given(state, done)), (["knock_out"], []))
        state = board(mon(HOUNDOOM, (DARK, W, W)), opponent=mon(CHANSEY))
        with_effects(state, 1, AttackEffectGuard(state.players[1].active.card, 1, TURN - 1, TURN), keys=("neo4-094#0",))
        done = attack(state, 0)
        self.assertEqual(([h[5] for h in hits(state, done)], given(state, done)), ([40], []))
        state, done = self.crunched(mon(MEW, (PS,)))
        self.assertEqual((kinds(state, done, "damage", "damage_prevented", "effect_prevented"), given(state, done)), (["damage_prevented", "effect_prevented"], []))

    def test_source_leaving_keeps_it_and_receiver_leaving_ends_it(self):
        """発生源のヘルガーがバトル場をはなれても +20 は消えない（説明に書かれていない。次の自分の番に入れ替わったコラッタのかみつく 20 も 8 段階で 40）。受けたラッキーがベンチにもどると
        消える（理由 retreat）。"""
        _, done = self.crunched(mon(CHANSEY), bench=(mon(RATTATA, (W,)),))
        mine = end(done)
        retreated = apply_kernel(mine, Retreat(0, (mine.players[0].active.energy[1],), mine.players[0].bench[0].card))
        self.assertEqual(removed(mine, retreated), [])
        hit = attack(retreated, 0)
        self.assertEqual([(h[2], h[4], h[5]) for h in hits(retreated, hit)], [(20, [("8 ヘルガー" + BONUS, 40)], 40)])
        audited(self, hit)
        _, done = self.crunched(mon(CHANSEY, (W,)), opponent_bench=(RATTATA,))
        fled = apply_kernel(done, Retreat(1, tuple(done.players[1].active.energy[:1]), done.players[1].bench[0].card))
        self.assertEqual(removed(done, fled), [(ReceivedAttackDamageBonus.kind, "retreat")])
        audited(self, fled)

    def test_same_step_8_order_with_reflector(self):
        """受けたポケモン自身のリフレクター（8 段階の半分（切りすて））と +20 は、順番で結果が変わるので受けるポケモンの持ち主が順番を選ぶ（v0.35 の決定。いやなおとと同じ）。
        40 → 半分 20 → +20 = 40、または 40 → +20 = 60 → 半分 30。答えのあとにダメージを 1 度だけ（複製・deepcopy・pickle からも同じ）。"""
        _, done = self.crunched(mon(CHANSEY))
        chansey = done.players[1].active
        with_effects(done, 1, HalvedDamage(chansey.card, 1, TURN + 1, TURN + 2), keys=("PMCG5-012#0",))
        mine = end(done)
        asked = attack(mine, 0)
        self.assertEqual((asked.decision.kind, asked.decision.player), (DAMAGE_STEP_ORDER, 1))
        results = {o: answer(asked, (o,)).players[1].active.damage - mine.players[1].active.damage for o in asked.decision.options}
        self.assertEqual(sorted(results.values()), [30, 40])
        finished = same_answers(self, asked, asked.decision.options[:1])
        self.assertEqual(len(new_events(asked, finished, "damage")), 1)
        audited(self, finished)



# ---------------------------------------------------------------- 6.1 節: もうどく


class ToxicTest(unittest.TestCase):
    def toxic(self, opponent, **kw):
        state = board(mon(ARBOK, (G, G, G)), opponent=opponent, **kw)
        return state, attack(state, 1)

    def test_bonus_only_when_poisoned_before(self):
        """どくでなければ基本 30、このワザを受ける前から（通常・特殊のどちらでも）どくなら 30 + 10 = 40。ダメージのあとに通常のどく（特殊などくは通常のどくになる。p.322）。"""
        for extra, base, before in (({}, 30, None), ({"poison": 10}, 40, 10), ({"poison": 20}, 40, 20)):
            state, done = self.toxic(mon(CHANSEY, **extra))
            target = state.players[1].active.pokemon_id
            with self.subTest(before=before):
                self.assertEqual([h[2] for h in hits(state, done)], [base])
                self.assertEqual(conditions(state, done), [(target, E.POISON, 10, before is not None)])
                self.assertEqual(done.players[1].active.conditions.poison.damage, 10)
                self.assertEqual(kinds(state, done, "damage", "special_condition"), ["damage", "special_condition"])
                audited(self, done)

    def test_new_poison_does_not_raise_the_base(self):
        """新しくどくにしてから状態を読まない（いつも 40 にしない）。damage_profile も宣言の時点の状態で決める。"""
        state, done = self.toxic(mon(CHANSEY))
        self.assertEqual(([h[2] for h in hits(state, done)], done.players[1].active.conditions.poison is not None), ([30], True))
        use = E.AttackUse(0, state.players[0].active.pokemon_id, AttackKey(ARBOK, 1))
        self.assertEqual(EXPECTED[(ARBOK, 1)].damage_profile(state, use).opponent, (30,))
        poisoned, _ = self.toxic(mon(CHANSEY, poison=20))
        self.assertEqual(EXPECTED[(ARBOK, 1)].damage_profile(poisoned, use).opponent, (40,))

    def test_damage_prevention_keeps_the_poison_and_ko_or_immunity_does_not(self):
        """「ダメージを受けない」状態（かたまる）ならダメージの要素だけが無効で、どくは受ける判定で決める（ダメージを与えたことを条件にしない）。HP 以上の相手はどくにしない。
        ［めんえき］のカビゴンはどくにならない（special_condition_prevented）。"""
        state, done = self.toxic(mon(CHANSEY, prevent_damage=TURN - 1))
        self.assertEqual((kinds(state, done, "damage_prevented", "damage", "special_condition"), conditions(state, done)[0][1]),
                         (["damage_prevented", "special_condition"], E.POISON))
        state, done = self.toxic(mon(RATTATA, (W,)), opponent_bench=(RATTATA,))
        self.assertEqual((kinds(state, done, "knock_out"), conditions(state, done)), (["knock_out"], []))
        state, done = self.toxic(mon(SNORLAX))
        self.assertEqual((conditions(state, done), kinds(state, done, "special_condition_prevented")), ([], ["special_condition_prevented"]))

    def test_copy_and_neutral_shield_use_the_actual_user(self):
        """相手のワザとして使う（ピクシーのゆびをふる）と、条件を調べるのは使ったピクシーの相手（どくのアーボック）。1 進化のアーボックのもうどくはミュウの［ニュートラルシールド］で
        ダメージもどくも受けない。"""
        state = board(mon(CLEFABLE, (W,)), opponent=mon(ARBOK, (G, G, G), poison=10))
        done = answer(attack(state, 0), (1,))
        self.assertEqual(([h[2] for h in hits(state, done)], [c[1:3] for c in conditions(state, done)]), ([40], [(E.POISON, 10)]))
        audited(self, done)
        state, done = self.toxic(mon(MEW, (PS,)))
        self.assertEqual((kinds(state, done, "damage", "damage_prevented", "effect_prevented", "special_condition")),
                         ["damage_prevented", "effect_prevented"])

    def test_ko_with_guts_is_g37(self):
        """もうどくの 30 で HP 以上になる相手がこんじょう（サカキのカイリキー）を使えるなら、そのあとのどくを受けるかが決まらない（既存の G37。宣言の前に止める）。"""
        state = board(mon(ARBOK, (G, G, G)), opponent=mon(H.GIOVANNIS_MACHAMP, (F,), evolved_from=[H.GIOVANNIS_MACHOP, H.GIOVANNIS_MACHOKE], damage=80))
        rejects(self, state, UseAttack(0, 1), "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT")

    def test_split_and_flee_decisions_apply_the_poison_once(self):
        """相手のドガースの［ぶんれつ］（ダメージのあとの要素のあいだの決定）をまたいでも、基本となるダメージは宣言の時点（どくでない 30）のまま、どくは答えのあとに 1 度だけ。相手の
        カスミのドククラゲの［にげこむ］で入れ替えたら、そのワザの残りの効果（どく）は受けない（入れ替えたポケモンにも移さない）。入れ替えなければ 1 度だけどく。"""
        state = board(mon(ARBOK, (G, G, G)), opponent=mon(KOFFING), opponent_deck=[KOFFING, W, W])
        asked = attack(state, 1)
        self.assertEqual((asked.decision.kind, [h[2] for h in hits(state, asked)]), (SPLIT_FROM_DECK, [30]))
        for choices in ((asked.decision.options[0],), ()):
            done = same_answers(self, asked, choices)
            self.assertEqual(([c[1] for c in conditions(asked, done)], new_events(asked, done, "damage")), ([E.POISON], []))
            audited(self, done)
        state = board(mon(ARBOK, (G, G, G)), opponent=mon(TENTACRUEL, (W, W)), opponent_bench=(RATTATA,))
        asked = attack(state, 1)
        self.assertEqual(asked.decision.kind, REACTION_SWITCH)
        fled = same_answers(self, asked, asked.decision.options[:1])
        stayed = same_answers(self, asked, ())
        self.assertEqual((conditions(asked, fled), [c[1] for c in conditions(asked, stayed)]), ([], [E.POISON]))
        audited(self, fled)
        audited(self, stayed)

    def test_charity_decision_carries_the_base(self):
        """お上品攻撃の減らす量の決定をまたいでも、確定した基本となるダメージ 40（宣言の時点のどく）を運び、どくは答えのあとに 1 度だけ（複製・deepcopy・pickle からも同じ）。"""
        state = board(mon(ARBOK, (G, G, G)), opponent=mon(CHANSEY, poison=10), hand=(H.CHARITY,))
        charitable = apply_kernel(state, PlayTrainer(0, uid_in_hand(state, H.CHARITY)))
        asked = attack(charitable, 1)
        self.assertEqual(asked.decision.kind, DAMAGE_REDUCTION)
        self.assertEqual(asked.decision.context_value("base"), 40)
        done = same_answers(self, asked, (0,))
        self.assertEqual([c[1] for c in conditions(asked, done)], [E.POISON])
        self.assertEqual(len(new_events(asked, done, "damage")), 1)
        audited(self, done)


# ---------------------------------------------------------------- 6.2 節: たたきおこす


class SlapAwakeTest(unittest.TestCase):
    def slap(self, opponent, **kw):
        state = board(mon(DARK_WIGGLYTUFF, (W, W, W)), opponent=opponent, **kw)
        return state, attack(state, 1)

    def test_bonus_and_cure_by_condition(self):
        """ねむり・こんらんなら 20 + 20 = 40、そのあとその状態だけを回復させる（どくは残す）。どく・マヒ・状態なしは 20 で、回復させるものはない（マヒも残す）。"""
        cases = (({"sleep": True}, 40, [(E.SLEEP,)]), ({"confusion": True}, 40, [(E.CONFUSION,)]), ({"sleep": True, "poison": 10}, 40, [(E.SLEEP,)]),
                 ({"poison": 10}, 20, []), ({"paralysis": TURN - 1}, 20, []), ({}, 20, []))
        for extra, base, removed_conditions in cases:
            state, done = self.slap(mon(CHANSEY, **extra))
            target = state.players[1].active.pokemon_id
            with self.subTest(extra=extra):
                self.assertEqual([h[2] for h in hits(state, done)], [base])
                self.assertEqual(cured(state, done), [(target, c, "cured") for c in removed_conditions])
                after = done.players[1].active.conditions
                self.assertEqual((after.poison is not None, after.paralyzed), ("poison" in extra, "paralysis" in extra))
                self.assertFalse(after.asleep or after.confused)
                if removed_conditions:
                    self.assertEqual(kinds(state, done, "damage", "special_conditions_removed"), ["damage", "special_conditions_removed"])
                audited(self, done)

    def test_cure_without_damage_and_blocked_cure(self):
        """ダメージだけが防がれても（かたまる）回復は受ける判定で決める（「ダメージを与えたら」の条件はない）。「ワザをうけない」状態（バリアー）・効果だけを受けない相手（ひかりのはどう）・
        HP 以上の相手は回復させない。"""
        state, done = self.slap(mon(CHANSEY, sleep=True, prevent_damage=TURN - 1))
        self.assertEqual((kinds(state, done, "damage_prevented", "damage"), cured(state, done)[0][1]), (["damage_prevented"], (E.SLEEP,)))
        state = board(mon(DARK_WIGGLYTUFF, (W, W, W)), opponent=mon(CHANSEY, sleep=True))
        barrier = AttackBarrier(state.players[1].active.card, 1, TURN - 1, TURN)
        guard = AttackEffectGuard(state.players[1].active.card, 1, TURN - 1, TURN)
        for effect, key in ((barrier, "PMCG1-041#1"), (guard, "neo4-094#0")):
            trial = state.clone()
            with_effects(trial, 1, effect, keys=(key,))
            done = attack(trial, 1, TL)  # ポケモンチェックのねむりのコインは「うら」（ねむりのまま）
            with self.subTest(effect=effect.kind):
                self.assertEqual((cured(trial, done), done.players[1].active.conditions.asleep), ([], True))
        state, done = self.slap(mon(RATTATA, (W,), sleep=True), opponent_bench=(RATTATA,))
        self.assertEqual((kinds(state, done, "knock_out"), cured(state, done)), (["knock_out"], []))

    def test_cure_brings_powers_back(self):
        """回復で相手の特殊能力がまたはたらく: ねむりのベトベトン（かがくへんかガスが消えている）を回復させると、自分の控えのカイリキーの［はんげき］がまた消える（今の状態から求める。v0.8 の
        G13）。化石の秘密のゴーストの「とうめい」も、こんらんから回復させるとまたはたらく。"""
        state = board(mon(DARK_WIGGLYTUFF, (W, W, W)), bench=(mon(MACHAMP),), opponent=mon(H.MUK, sleep=True))
        machamp = state.players[0].bench[0].pokemon_id
        self.assertEqual(power_suppressors(state, machamp, 0), ())
        done = attack(state, 1)
        self.assertEqual(power_suppressors(done, machamp, 0), (done.players[1].active.pokemon_id,))
        audited(self, done)
        state, done = self.slap(mon(HAUNTER, (PS,), confusion=True))
        self.assertIsNone(E.evasion_power(state, state.players[1].active))
        self.assertIsNotNone(E.evasion_power(done, done.players[1].active))

    def test_undecidable_state_after_cure_stops_before_the_declaration(self):
        """回復させたあとの状態が受け付けられない（決められない姿など。``attack_state_stop_after``）なら、宣言の前に先読みが見つけて止める（状態・乱数・ログを変えない）。
        回復させない並び（状態なし）では確かめない。仕組みの確かめ（止める判定を試験の中だけ置きかえる）。"""
        state = board(mon(DARK_WIGGLYTUFF, (W, W, W)), opponent=mon(CHANSEY, sleep=True))
        with mock.patch.object(E, "attack_state_stop_after", lambda before, after: ("UNRESOLVED_TEST_FORM", "テストの止める理由")):
            rejects(self, state, UseAttack(0, 1), "UNRESOLVED_TEST_FORM")
            plain = board(mon(DARK_WIGGLYTUFF, (W, W, W)), opponent=mon(CHANSEY))
            self.assertEqual([h[2] for h in hits(plain, attack(plain, 1))], [20])

    def test_copy_cures_the_copier_opponent(self):
        """相手のワザとして使う（ピクシーのゆびをふる）と、条件と回復の対象は使ったピクシーの相手（こんらんのわるいプクリン）。"""
        state = board(mon(CLEFABLE, (W,)), opponent=mon(DARK_WIGGLYTUFF, (W, W, W), confusion=True))
        done = answer(attack(state, 0), (1,))
        self.assertEqual(([h[2] for h in hits(state, done)], cured(state, done)), ([40], [(state.players[1].active.pokemon_id, (E.CONFUSION,), "cured")]))
        audited(self, done)


# ---------------------------------------------------------------- 3 章: わるいうた・既存の型


class ReusedTypeTest(unittest.TestCase):
    def test_dark_song_one_coin(self):
        """1 枚のコインの「おもて」でねむり、「うら」でこんらん（ダメージなし。投げ直さない）。「ワザをうけない」相手は HC3、「とうめい」で受けないと決まりうる相手は T19b（既存）。"""
        for flip, condition in ((HD, E.SLEEP), (TL, E.CONFUSION)):
            state = board(mon(DARK_WIGGLYTUFF, (W, W)), opponent=mon(CHANSEY))
            done = attack(state, 0, flip)
            with self.subTest(flip=flip):
                self.assertEqual((attack_coins(state, done), [c[1] for c in conditions(state, done)], hits(state, done)),
                                 ([flip.value], [condition], []))
                audited(self, done)
        state = board(mon(DARK_WIGGLYTUFF, (W, W)), opponent=mon(CHANSEY))
        with_effects(state, 1, AttackBarrier(state.players[1].active.card, 1, TURN - 1, TURN), keys=("PMCG1-041#1",))
        rejects(self, state, UseAttack(0, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")

    def test_plus_ion_spike_tackle_wrap(self):
        """プラスイオン（「おもて」で 10 + 10）・とげたまタックル（相手 20 → 自分 10）・まきつく（20 →「おもて」でマヒ）。"""
        for flip, base in ((HD, 20), (TL, 10)):
            state = board(mon(CHINCHOU, (L,)), opponent=mon(CHANSEY))
            self.assertEqual([h[2] for h in hits(state, attack(state, 0, flip))], [base])
        state = board(mon(TOGEPI, (W, W)), opponent=mon(CHANSEY))
        done = attack(state, 1)
        self.assertEqual([(h[1], h[2]) for h in hits(state, done)], [("opponent_active", 20), ("self", 10)])
        state = board(mon(ARBOK, (G, G)), opponent=mon(CHANSEY))
        done = attack(state, 0, HD)
        self.assertEqual(([h[2] for h in hits(state, done)], [c[1] for c in conditions(state, done)]), ([20], [E.PARALYSIS]))

    def test_flamethrower_discards_and_copy_without_fire_stops(self):
        """かえんほうしゃ: 炎エネルギーカード 1 枚を選んでトラッシュ（決定 DISCARD_ENERGY）してから 50。相手のワザとして使ったピクシーに炎エネルギーがない場面は、既存の HC9
        （UNRESOLVED_COPIED_ATTACK。選べるが選ぶと止める）のまま（v0.108 で変えない）。"""
        state = board(mon(HOUNDOOM, (R, R, W)), opponent=mon(CHANSEY))
        asked = attack(state, 1)
        self.assertEqual(asked.decision.kind, DISCARD_ENERGY)
        done = answer(asked, asked.decision.options[:1])
        self.assertEqual(([h[2] for h in hits(asked, done)], len(done.players[0].active.energy)), ([50], 2))
        audited(self, done)
        state = board(mon(CLEFABLE, (W,)), opponent=mon(HOUNDOOM, (R, R, W)))
        asked = attack(state, 0)
        self.assertEqual(asked.decision.kind, SELECT_ATTACK)
        rejects(self, asked, lambda s: ResolveDecision(0, s.decision.id, (1,)), "UNRESOLVED_COPIED_ATTACK")


# ---------------------------------------------------------------- 6・7 章: 決定・先読み・保存


class DecisionAndRecordTest(unittest.TestCase):
    def test_invalid_answers_change_nothing(self):
        """もうどくのお上品攻撃の決定への不正な答え（選べない量・答えるプレイヤーの違い）は、状態・乱数・ログ・決定を変えずに拒否する（HALTED にしない）。"""
        state = board(mon(ARBOK, (G, G, G)), opponent=mon(CHANSEY, poison=10), hand=(H.CHARITY,))
        asked = attack(apply_kernel(state, PlayTrainer(0, uid_in_hand(state, H.CHARITY))), 1)
        for player, choices in ((0, (999,)), (1, asked.decision.options[:1])):
            before = snap(asked)
            with self.subTest(player=player, choices=choices), self.assertRaises(IllegalActionError):
                apply_kernel(asked, ResolveDecision(player, asked.decision.id, choices))
            self.assertEqual(snap(asked), before)

    def test_preflight_methods_agree(self):
        """先読みの方法（derived・derived_full・legacy）は同じ結果（新しい型は v0.13 の止める関数の確かめた型ではないので、legacy でもすべての結果を試す）。上限は変えていない。"""
        self.assertEqual(MAX_BRANCHES, 4096)
        cases = ((board(mon(CHINCHOU, (W,)), opponent=mon(MACHAMP, (F,))), 1, ()), (board(mon(TOGEPI, (W,)), opponent=mon(CHANSEY)), 0, ()),
                 (board(mon(HOUNDOOM, (DARK, W, W)), opponent=mon(MACHAMP, (F,))), 0, ()), (board(mon(ARBOK, (G, G, G)), opponent=mon(CHANSEY, poison=10)), 1, ()),
                 (board(mon(DARK_WIGGLYTUFF, (W, W, W)), opponent=mon(CHANSEY, sleep=True)), 1, ()), (board(mon(DARK_WIGGLYTUFF, (W, W)), opponent=mon(CHANSEY)), 0, (TL,)),
                 (board(mon(TOGEPI, (W,)), opponent=mon(HAUNTER, (PS,))), 0, (HD,)))
        for state, index, flips in cases:
            results = [snap(apply_kernel(with_coin_results(state, *flips), UseAttack(0, index), preflight=mode)) for mode in ("derived", "derived_full", "legacy")]
            with self.subTest(card=state.cards[state.players[0].active.card].card_id, index=index):
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0], results[2])

    def test_serialization_observation_and_copies(self):
        """新しい持続する効果は形式 8 の persistent_effects の種類の値と項目（期間の終わり・発生源の場の番号・減らす数）。形式は 26 のまま。形式 7 は持続する効果を表せないので拒否する。
        clone・deepcopy・pickle しても同じ（量と範囲が残る）。観測は種類だけを書く。"""
        _, done = negative_ion(mon(RATTATA, (W,)))
        data = state_to_dict(done, format_version=max(FORMAT_VERSIONS))
        (written,) = [e for e in data["players"][1]["active"]["persistent_effects"] if e["effect"] == DealtAttackDamageReduction.kind]
        self.assertEqual({k: written[k] for k in ("effect", "created_turn", "active_turn", "end_turn", "amount", "source_pokemon", "source_card_id")},
                         {"effect": DealtAttackDamageReduction.kind, "created_turn": TURN, "active_turn": TURN + 1, "end_turn": TURN + 1, "amount": 10,
                          "source_pokemon": done.players[0].active.pokemon_id, "source_card_id": CHINCHOU})
        self.assertNotIn("while_source_active", written)
        self.assertEqual((max(FORMAT_VERSIONS), LATEST_FORMAT), (26, 26))
        with self.assertRaises(ValueError):
            state_to_dict(done, format_version=7)
        for other in (done.clone(), copy.deepcopy(done), pickle.loads(pickle.dumps(done))):
            self.assertEqual(reductions_on(other.players[1].active), reductions_on(done.players[1].active))
            self.assertEqual(snap(other), snap(done))
        from kyuura_engine.observation import observe

        seen = observe(done, 0)
        self.assertIn(DealtAttackDamageReduction.kind, json.dumps(seen, ensure_ascii=False))

    def test_invariants_find_a_wrong_period_or_amount(self):
        """不変条件は登録の期間・数と照らす（与えた番 + 2 まで残る -10・-20 は不整合）。"""
        from kyuura_engine.engine import check_invariants

        _, done = negative_ion(mon(RATTATA, (W,)))
        for change in ({"end_turn": TURN + 2}, {"amount": 20}):
            trial = done.clone()
            holder = trial.players[1].active
            holder.persistent_effects = tuple(dataclasses.replace(e, **change) if isinstance(e, DealtAttackDamageReduction) else e for e in holder.persistent_effects)
            with self.subTest(change=change):
                self.assertTrue(check_invariants(trial))


# ---------------------------------------------------------------- 8 章: ログの監査


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v108_problems``・``attack_damage_set_problems``）は、エンジンの ``OpponentStatusCheck``・``PlusIfResult``・``CureOpponentConditions``・
    ``attack_damage_modifiers`` を読まずに、ログから組み立てた場とこのワザのログの並びで確かめる。エンジンの処理を一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の局。
    v0.108 のワザが出る組と seed）で、監査がそれを見つける（誤らせなければ、同じ局は監査を通る）。"""

    # 開発用の seed（4・5。正式な対戦の seed 0〜3 とは別）のうち、使うワザのダメージの -10（自分へのダメージを含む）・もうどく・ねむりとこんらんの回復・わるいうた・かみくだくの +20 が出る局
    GAMES = ((("G108", "L108"), 5), (("M60", "L108"), 5), (("P31", "L108"), 5), (("M60", "D108"), 5), (("P31", "G108"), 4))

    @classmethod
    def results(cls, patcher):
        from tools import existing_effect_games as games

        found = []
        with patcher:
            for labels, seed in cls.GAMES:
                result = games.play(labels, seed, keep_state=True)
                if result.get("state") is not None:
                    found.append((result, log_problems(result["state"])))
        return found

    def problems_for(self, patcher, *needles):
        return [p for _, problems in self.results(patcher) for p in problems if any(n in p for n in needles)]

    def test_the_unpatched_games_pass_the_audit(self):
        from tools import existing_effect_games as games

        for labels, seed in self.GAMES:
            result = games.play(labels, seed, keep_state=True)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual((result["outcome"], result["audit"], log_problems(result["state"])), ("game_over", {}, []))
                self.assertTrue(any(key.startswith("attack_") for key in result["v108"]))

    def test_audit_finds_a_missing_or_narrowed_minus_10(self):
        """-10 を計算しなかった・旧なきつくの範囲（元の使い手へのダメージだけ）にした。"""
        self.assertTrue(self.problems_for(mock.patch.object(E, "dealt_attack_damage_reductions", lambda state, pokemon: ()), "2 段階"))
        from kyuura_engine.resolution import kernel

        original = kernel.attack_damage_modifiers

        def narrowed(state, attacker, defender, **kw):
            mods = original(state, attacker, defender, **kw)
            sources = {e.source_card for e in reductions_on(attacker)}
            return tuple(m for m in mods if not (m.label.endswith(DEALT) and defender.card not in sources))

        self.assertTrue(self.problems_for(mock.patch.object(kernel, "attack_damage_modifiers", narrowed), "2 段階"))

    def test_audit_finds_a_base_read_after_poisoning_and_a_misplaced_cure(self):
        """もうどくの状態をどくにしたあとで読んだ（いつも 40）・たたきおこすの回復をダメージの前にした・回復させなかった。"""
        late = {E.PlusIfDefenderPoisonedThenPoison: lambda e: (P.Status(E.POISON), P.OpponentStatusCheck("opponent_status_before", (E.POISON,)),
                                                               P.Damage(P.OPP, P.PlusIfResult("opponent_status_before", e.bonus)))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, late), ARBOK))
        early = {E.PlusIfDefenderStatusThenCure: lambda e: (P.OpponentStatusCheck("opponent_status_before", e.conditions), P.CureOpponentConditions(e.conditions),
                                                            P.Damage(P.OPP, P.PlusIfResult("opponent_status_before", e.bonus)))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, early), DARK_WIGGLYTUFF))
        none = {E.PlusIfDefenderStatusThenCure: lambda e: (P.OpponentStatusCheck("opponent_status_before", e.conditions),
                                                           P.Damage(P.OPP, P.PlusIfResult("opponent_status_before", e.bonus)))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, none), DARK_WIGGLYTUFF))

    def test_audit_finds_a_wrong_period_and_a_swapped_song(self):
        """かみくだくの期間を与えた番からにした・わるいうたの面と特殊状態を逆にした。"""
        early = {E.DamageThenReceivedAttackDamageBonus: lambda e: (P.Damage(P.OPP, P.Printed()), P.OpponentDamageTakenBonus(e.amount, 0, e.end))}
        with mock.patch.object(E.DamageThenReceivedAttackDamageBonus, "period_terms", lambda self: (ReceivedAttackDamageBonus, 0, 2, False, (), 20)):
            self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, early), HOUNDOOM))
        swapped = {E.StatusByCoinWithoutDamage: lambda e: (P.Status(e.tails, local_coin=HD, otherwise=e.heads),)}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, swapped), DARK_WIGGLYTUFF))


class DocumentTest(unittest.TestCase):
    def test_document_names_the_shared_parts(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("DealtAttackDamageReduction", "DamageThenDealtDamageReduction", "DealtDamageReductionWithoutDamage", "DamageThenReceivedAttackDamageBonus",
                       "PlusIfDefenderPoisonedThenPoison", "PlusIfDefenderStatusThenCure", "OpponentDealtDamageReduction", "OpponentStatusCheck", "PlusIfResult",
                       "CureOpponentConditions", "DARK_SONG_TEXTS", "DEALT_DAMAGE_ELEMENT", "PERIOD_AMOUNT_TYPES", "attack_damage_modifiers", "attack_state_stop_after",
                       "ReducedDamageToSource", "ReceivedAttackDamageBonus", "SCREECH_TEXTS", "NK5", "SS1", "KG1", "G37", "HC3", "T19b",
                       "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "68816f8", "49e3219", "9e8ca5c", "73a1690", "RUL-ENERGY-DISCARD-ATTACKS",
                       "GR-2000-P321-DAMAGE-ORDER", "GR-2000-P321-ATTACK-DAMAGE", "GR-2000-P322-PERSISTENT-EFFECTS", "GR-2000-P321-PREVENTED-ELEMENTS"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()

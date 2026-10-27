"""v0.109（docs/timed-damage-guards-v0.109.md）: 次の相手の番に受けるときのコインでダメージを防ぐ効果（ウパーの「ぬるぬる」・エビワラーの「かわす」・ユンゲラーの「ブリンク」）と、
相手のタイプで基本となるダメージが決まるワザ（ユンゲラーの「サイコパニック」）の 3 枚（ワザ 6）。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面。3 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録（v0.60 のかげぶんしん・
v0.83 のリフレクトシールドの受けるときのコイン、v0.2d のコインを投げるプレイヤーの記録上の規約、GR-2000-P321-DAMAGE-ORDER・GR-2000-P322-PERSISTENT-EFFECTS、v0.103 の発生元）。英語版の
文面・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、
``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.109``）。
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
    EndTurn,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import (
    EnergyType,
    load_card_pool,
    pool_from_extract,
    read_extract,
)
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import DAMAGE_REDUCTION, ESP_REDO, SELECT_ATTACK
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.history import VOID_DODGED
from kyuura_engine.persistent import tails_damage_guard, timed_damage_guards
from kyuura_engine.resolution import flow as F
from kyuura_engine.resolution import kernel as K
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.events import FrameKind
from kyuura_engine.resolution.preflight import MAX_BRANCHES
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import (
    GUARD_FLIPPER_OPPONENT,
    GUARD_FLIPPER_OWNER,
    GUARD_FLIPPER_UNSTATED,
    GUARD_SCOPE_ATTACK,
    GUARD_SCOPE_OPPONENT_ATTACK,
    PERIOD_EFFECT_TYPES,
    PERSISTENT_EFFECT_TYPES,
    AttackReceived,
    ReflectShield,
    TailsDamageGuard,
    TimedDamageGuard,
)
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.log_audit import LATEST_FORMAT, log_problems
from tests.release_catalog import cards_after, cards_before
from tests.test_counter_keep_energy_protection_v0_101 import attack
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_power_suppression_lasting_locks_v0_92 import removed
from tests.test_unown_family_powers_v0_96 import TURN, board, same_answers, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "timed-damage-guards-v0.109.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, F_, L, G, PS = H.WATER, H.FIGHTING, H.LIGHTNING, H.GRASS, H.PSYCHIC
WOOPER, HITMONCHAN, KADABRA = "neo2-015", "neo4-070", "ES3-019"
V0109 = (WOOPER, HITMONCHAN, KADABRA)
V0109_ATTACKS = [AttackKey(card, index) for card in V0109 for index in range(2)]
ABRA, RATTATA, CHANSEY, HAUNTER, DITTO, CLEFABLE, CLEFAIRY = H.ABRA, H.RATTATA, H.CHANSEY, H.HAUNTER, H.DITTO, H.CLEFABLE, H.CLEFAIRY
ELECTABUZZ, ELECTABUZZ_NEO1 = H.ELECTABUZZ, "neo1-039"  # でんきショック（雷）10・「おもて」でマヒ／パンチ（無無）20・スピードスター（雷雷雷）30
ARBOK, EKANS = "ES3-001", "PMCG4-001"  # もうどく（草草草）30+（どく）
JAB = "PMCG1-058"  # エビワラー（第1弾。HP 70・闘。ジャブ（闘）20）。次の相手の番にワザで 20 を与える相手（ブリンクの 30 ではきぜつしない）
ROCKET_SNORLAX, GEODUDE_FOSSIL, ROCKET_SCYTHER = "PMCG6-073", "PMCG3-034", "PMCG5-016"  # たおれこむ（Z23）・れんぞくいしなげ・かげぶんしん
BELOW = {KADABRA: [ABRA], CLEFABLE: [CLEFAIRY], ARBOK: [EKANS], HAUNTER: [H.GASTLY]}
GUARD = TimedDamageGuard.kind

# 依頼で示された固定データの日本語（写しの文面と照らす。広い正規化をしない）。(HP, タイプ, 段階, 弱点, 抵抗力, にげる, 進化元, (名前, 必要なエネルギー, ダメージの目安, 説明), ...)
SLIME = "次の相手の番、このカードが相手のワザによるダメージを受けるとき、相手プレイヤーはコインを投げる。「うら」なら、このカードはそのダメージを受けない。(ダメージ以外の効果は受ける。)"
DODGE = "次の相手の番、このカードが相手のワザによるダメージを受けるとき、このカードの持ち主はコインを投げる。「おもて」なら、このカードはそのダメージを受けない。（ダメージ以外の効果は受ける）。"
PANIC = "このワザを受ける相手が「超」ポケモンなら、このワザのダメージは60になる。"
BLINK = "次の相手の番、このカードがワザによるダメージを受ける時、コインを投げて「おもて」なら、このカードはそのダメージを受けない。(ダメージ以外の効果は受ける)"
QUOTED = {
    WOOPER: (50, "water", "basic", "grass", ("lightning", 30), 1, None, ("ぬるぬる", ("water",), None, SLIME), ("しっぽでたたく", ("colorless", "colorless"), "20", None)),
    HITMONCHAN: (60, "fighting", "basic", "psychic", None, 1, None, ("かわす", ("fighting",), None, DODGE), ("マッハストレート", ("fighting",) * 3, "40", None)),
    KADABRA: (60, "psychic", "stage1", "psychic", None, 3, "ケーシィ", ("サイコパニック", ("psychic", "psychic"), "30", PANIC), ("ブリンク", ("psychic",) * 3, "30", BLINK)),
}
SLIME_TERMS = (TL, GUARD_FLIPPER_OPPONENT, GUARD_SCOPE_OPPONENT_ATTACK)
DODGE_TERMS = (HD, GUARD_FLIPPER_OWNER, GUARD_SCOPE_OPPONENT_ATTACK)
BLINK_TERMS = (HD, GUARD_FLIPPER_UNSTATED, GUARD_SCOPE_ATTACK)
EXPECTED = {
    (WOOPER, 0): E.SelfTimedDamageGuardWithoutDamage(*SLIME_TERMS), (WOOPER, 1): E.DAMAGE_ONLY,
    (HITMONCHAN, 0): E.SelfTimedDamageGuardWithoutDamage(*DODGE_TERMS), (HITMONCHAN, 1): E.DAMAGE_ONLY,
    (KADABRA, 0): E.DamageSetAgainstType(EnergyType.PSYCHIC, 60), (KADABRA, 1): E.DamageThenSelfTimedDamageGuard(*BLINK_TERMS),
}
NEW_TYPES = (E.SelfTimedDamageGuardWithoutDamage, E.DamageThenSelfTimedDamageGuard, E.DamageSetAgainstType)
# 3 つのワザの使い方（カード, ワザの位置, つけるエネルギー, 投げる人が持ち主か, ダメージを受けない面）
GUARDS = {"slime": (WOOPER, 0, (W,), False, TL), "dodge": (HITMONCHAN, 0, (F_,), True, HD), "blink": (KADABRA, 1, (PS, PS, PS), True, HD)}
GUARD_KEYS = {"slime": (WOOPER, 0), "dodge": (HITMONCHAN, 0), "blink": (KADABRA, 1)}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def answer(state, choices, *coins, player=None):
    d = state.decision
    return apply_kernel(with_coin_results(state, *coins) if coins else state, ResolveDecision(d.player if player is None else player, d.id, tuple(choices)))


def uid_in_hand(state, card_id, player=0):
    return next(u for u in state.players[player].hand if state.cards[u].card_id == card_id)


def play(state, card_id, player=0):
    return apply_kernel(state, PlayTrainer(player, uid_in_hand(state, card_id, player)))


def guarded(name, opponent, *, extra=(), **kw):
    """``name`` のワザをプレイヤー 0 が ``TURN`` 番に使い、相手（プレイヤー 1）の番（``TURN + 1``）になった盤面（使う前の盤面と、使ったあとの盤面）。"""
    card, index, energy, _, _ = GUARDS[name]
    state = board(mon(card, energy, **dict(extra)), opponent=opponent, **kw)
    return state, attack(state, index)


def checks(before, after):
    """受けるときのコインの判定の (ポケモンの番号, 投げた人, 面, 受けたか, 量, ワザを使ったプレイヤー)。"""
    return [(e["pokemon_id"], e["flipped_by"], e["result"], e["received"], e["amount"], e["attacker"]) for e in new_events(before, after, "timed_damage_guard_check")]


def guard_coins(before, after):
    return [(e["player"], e["result"]) for e in new_events(before, after, "coin_flip") if e["source"] == "persistent_effect"]


def damages(before, after):
    return [(e.get("pokemon_id", e["pokemon"]), e["amount"]) for e in new_events(before, after, "damage")]


def guards_on(pokemon):
    return [e for e in pokemon.persistent_effects if isinstance(e, TimedDamageGuard)]


# ---------------------------------------------------------------- 1〜3 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        """3 枚・6 つのワザの名前・必要なエネルギー・ダメージの目安・説明と、HP・タイプ・段階・弱点・抵抗力・にげる・進化元は依頼の日本語・固定データと同じ。特殊能力は 0。説明のない 2 つは
        ``DAMAGE_ONLY``（文面・出典を書かない）。"""
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_109"]), V0109)
        for card, (hp, color, stage, weakness, resistance, retreat, below, *attacks) in QUOTED.items():
            definition = pool.definitions[card]
            with self.subTest(card=card):
                self.assertEqual((definition.hp, definition.pokemon_type.value, definition.stage, definition.powers), (hp, color, stage, ()))
                self.assertEqual(None if definition.weakness is None else definition.weakness.value, weakness)
                self.assertEqual(None if definition.resistance is None else (definition.resistance.value, definition.resistance_value), resistance)
                self.assertEqual((definition.retreat_cost, definition.evolves_from), (retreat, below))
                self.assertIn(card, pool.playable_ids)
            for index, (name, cost, display, text) in enumerate(attacks):
                printed = definition.attacks[index]
                entry = DEFAULT_EFFECTS.attack_entry(card, index)
                with self.subTest(card=card, index=index):
                    self.assertEqual((printed.name_ja, tuple(t.value for t in printed.cost), printed.damage_display, printed.text_ja), (name, cost, display, text))
                    self.assertEqual(entry.effect, EXPECTED[(card, index)])
                    expected_texts = (text, text, "kyuura data/cards.json") if text is not None else (None, None, None)
                    self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (name, *expected_texts))
                    self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, printed, definition.attacks))

    def test_names_sources_and_gaps(self):
        """名前（ウパー・エビワラー・ユンゲラー）は既存のカードにあるので、クイズの名前の候補は増えない。ケーシィは写しにある。ユンゲラーの図鑑番号・レベルの欠けは補わない。"""
        pool = load_card_pool()
        cards = {c["id"]: c for c in read_extract()["cards"]}
        before = {d.name_ja for c, d in pool.definitions.items() if c in pool.playable_ids and c not in V0109 and d.category == "pokemon"}
        self.assertTrue({"ウパー", "エビワラー", "ユンゲラー", "ケーシィ"} <= before)
        self.assertEqual({card: cards[card]["data_gaps"] for card in V0109}, {WOOPER: [], HITMONCHAN: [], KADABRA: ["pokemon.dex", "jp_print.level"]})
        self.assertEqual({card: cards[card]["same_card_group"] for card in V0109}, dict.fromkeys(V0109))
        hosts = {card: cards[card]["ja_text_source"].split("/")[2] for card in V0109}
        self.assertEqual(hosts, {WOOPER: "nazonobasho.com", HITMONCHAN: "wiki.pokemonwiki.com", KADABRA: "pcg-search.com"})

    def test_programs_and_types(self):
        """新しい型の要素の並び。受けるときのコインで防ぐ効果は自分への新しい要素（ダメージ・コインはない）、サイコパニックは既存の ``Damage`` と新しい値。相手への効果の宣言はない。
        新しい持続する効果は、かげぶんしんの部分型ではなく、期間を明示した効果の型（相手に与える効果の型）にも入れない。"""
        programs = {
            EXPECTED[(WOOPER, 0)]: (P.SelfTimedDamageGuard("tails", GUARD_FLIPPER_OPPONENT, GUARD_SCOPE_OPPONENT_ATTACK),),
            EXPECTED[(HITMONCHAN, 0)]: (P.SelfTimedDamageGuard("heads", GUARD_FLIPPER_OWNER, GUARD_SCOPE_OPPONENT_ATTACK),),
            EXPECTED[(KADABRA, 1)]: (P.Damage(P.OPP, P.Printed()), P.SelfTimedDamageGuard("heads", GUARD_FLIPPER_UNSTATED, GUARD_SCOPE_ATTACK)),
            EXPECTED[(KADABRA, 0)]: (P.Damage(P.OPP, P.AmountIfDefenderType(EnergyType.PSYCHIC, 60)),),
        }
        for effect, program in programs.items():
            with self.subTest(effect=effect):
                self.assertEqual(P.BUILDERS[type(effect)](effect), program)
                self.assertEqual(P.compile_attack(effect), program)
                self.assertFalse(P.program_may_fail(program))
                self.assertEqual((effect.opponent_effect_elements, P.opponent_effect_elements(program)), ((), ()))
        for cls in NEW_TYPES:
            self.assertIn(cls, H.ATTACK_TYPES_SINCE_V0_17)
            self.assertIs(cls.resolve, E.AttackEffect.resolve)
        self.assertEqual([EXPECTED[key].guard_terms() for key in ((WOOPER, 0), (HITMONCHAN, 0), (KADABRA, 1))],
                         [(TimedDamageGuard, "tails", "opponent", "opponent_attack"), (TimedDamageGuard, "heads", "owner", "opponent_attack"),
                          (TimedDamageGuard, "heads", "unstated", "attack")])
        self.assertIn(TimedDamageGuard, PERSISTENT_EFFECT_TYPES)
        self.assertNotIn(TimedDamageGuard, PERIOD_EFFECT_TYPES)
        self.assertFalse(issubclass(TimedDamageGuard, TailsDamageGuard))
        self.assertEqual((TimedDamageGuard.turns_until_active, TimedDamageGuard.on_opponent, hasattr(TimedDamageGuard, "lasting")), (1, False, False))
        with self.assertRaises(ValueError):
            TimedDamageGuard(0, 0, 1, 2, "edge", GUARD_FLIPPER_OWNER, GUARD_SCOPE_ATTACK)

    def test_guard_texts_are_bound_to_side_flipper_and_scope(self):
        """面・投げる人・範囲・ダメージの形は文面と 1 対 1。取り違えた組・形・かげぶんしんの型・ほかの書き方（括弧の字形・「相手の」の有無・面）は受け付けない（句読点を一括で正規化しない）。"""
        pool = load_card_pool()
        slime, dodge, blink = pool.definitions[WOOPER].attacks[0], pool.definitions[HITMONCHAN].attacks[0], pool.definitions[KADABRA].attacks[1]
        for terms in ((HD, GUARD_FLIPPER_OPPONENT, GUARD_SCOPE_OPPONENT_ATTACK), (TL, GUARD_FLIPPER_OWNER, GUARD_SCOPE_OPPONENT_ATTACK),
                      (HD, GUARD_FLIPPER_OWNER, GUARD_SCOPE_ATTACK), (HD, GUARD_FLIPPER_UNSTATED, GUARD_SCOPE_OPPONENT_ATTACK), (TL, GUARD_FLIPPER_OPPONENT, GUARD_SCOPE_ATTACK)):
            with self.subTest(terms=terms), self.assertRaises(ValueError):
                E.SelfTimedDamageGuardWithoutDamage(*terms)
        for wrong, printed in ((E.SelfTimedDamageGuardWithoutDamage(*DODGE_TERMS), slime), (E.SelfTimedDamageGuardWithoutDamage(*SLIME_TERMS), dodge),
                               (E.DamageThenSelfTimedDamageGuard(*SLIME_TERMS), slime), (E.SelfTimedDamageGuardWithoutDamage(*BLINK_TERMS), blink),
                               (E.DamageThenSelfTimedDamageGuard(*DODGE_TERMS), blink), (E.SelfTailsDamageGuard(), slime), (E.SelfReflectShield(20), dodge)):
            with self.subTest(wrong=wrong, printed=printed.name_ja):
                self.assertNotEqual(wrong.check(printed), [])
        printed_of = {"slime": slime, "dodge": dodge, "blink": blink}
        for name, text in (("slime", SLIME.replace("「うら」", "「おもて」")), ("slime", SLIME.replace("(ダメージ以外の効果は受ける。)", "（ダメージ以外の効果は受ける。）")),
                           ("dodge", DODGE.replace("このカードの持ち主は", "相手プレイヤーは")), ("dodge", DODGE.replace("（ダメージ以外の効果は受ける）。", "")),
                           ("blink", BLINK.replace("ワザによるダメージ", "相手のワザによるダメージ")), ("blink", BLINK.replace("次の相手の番、", "これ以降、"))):
            with self.subTest(name=name, text=text):
                self.assertNotEqual(EXPECTED[GUARD_KEYS[name]].check(dataclasses.replace(printed_of[name], text_ja=text)), [])
        # かげぶんしん（v0.60）の書き方・型は変えない
        self.assertEqual(E.SelfTailsDamageGuard().check(dataclasses.replace(slime, text_ja=E.SHADOW_IMAGES_TEXTS[0])), [])

    def test_psychic_panic_text_is_bound_to_the_amount(self):
        """サイコパニックは「その数になる」の値と文面の数・タイプを結び付ける。v0.45 の「…倍になる」の型（2 倍）は文面を受け付けず、意味も変えない。目安 40・説明 60 の登録でも基本は 60
        （80 にしない）。"""
        pool = load_card_pool()
        panic = pool.definitions[KADABRA].attacks[0]
        self.assertEqual(E.DamageSetAgainstType(EnergyType.PSYCHIC, 60).check(panic), [])
        for wrong in (E.DamageMultipliedAgainstType(EnergyType.PSYCHIC, 2), E.DamageSetAgainstType(EnergyType.PSYCHIC, 80), E.DamageSetAgainstType(EnergyType.FIRE, 60)):
            with self.subTest(wrong=wrong):
                self.assertNotEqual(wrong.check(panic), [])
        self.assertNotEqual(E.DamageSetAgainstType(EnergyType.PSYCHIC, 60).check(dataclasses.replace(panic, text_ja=PANIC.replace("60になる", "2倍になる"))), [])
        self.assertEqual(E.DamageSetAgainstType(EnergyType.PSYCHIC, 60).check(dataclasses.replace(panic, damage=40, damage_display="40")), [])
        for amount in (0, 65):
            with self.assertRaises(ValueError):
                E.DamageSetAgainstType(EnergyType.PSYCHIC, amount)
        # v0.45 のこおりのつぶて（「2倍になる」）の確かめは変えない
        icy = pool.definitions["PMCG5-031"].attacks[0]
        self.assertEqual(DEFAULT_EFFECTS.attack_entry("PMCG5-031", 0).effect, E.DamageMultipliedAgainstType(EnergyType.FIGHTING, 2))
        self.assertEqual(DEFAULT_EFFECTS.attack_entry("PMCG5-031", 0).effect.check(icy), [])

    def test_unregistered_without_the_v0_109_entries(self):
        """今回の登録だけを除くと、ちょうど 3 枚が未対応にもどる（ほかのカードは失われない）。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V0109_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V0109))
        self.assertEqual(set(V0109) & set(cards_before(read_extract(), "0.109")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.108")) & set(cards_before(read_extract(), "0.110")), set(V0109))

    def test_adoption_records(self):
        """3 件の採用の記録（kyuura 73a1690・外部照合なし・kyuura の記録なし）。処理に使う文面は説明のある 4 つのワザの印刷の文面だけ（説明のない 2 つは書かない）。"""
        sources = json.loads((ROOT / "kyuura_engine/data/card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine/data/research_links.json").read_text(encoding="utf-8"))
        adopted = links["latest_descriptions"]["adopted_printed_text"]
        texts = {WOOPER: ("attack/0",), HITMONCHAN: ("attack/0",), KADABRA: ("attack/0", "attack/1")}
        for card in V0109:
            record = sources[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"], record["external_checks"], record["issues"],
                                  record["recorded_on"]), ("kyuura_data", "adopted", "73a169063463bbf7bcaa3137d70cbf9721d11534", [], [], [], "2026-10-27"))
                self.assertEqual(record["play_text"], dict.fromkeys(texts[card], "kyuura_printed_text"))
        self.assertEqual(sorted(key for key in adopted if key.split("/")[0] in V0109),
                         sorted(f"{card}/{part}" for card, parts in texts.items() for part in parts))
        self.assertEqual(links["stop_codes"]["UNRESOLVED_DAMAGE_GUARD_OVERLAP"]["engine_rulings"],
                         [{"version": "v0.109", "document": "docs/timed-damage-guards-v0.109.md", "ruling_id": "GO1"}])
        self.assertEqual((QUESTIONS["damage_guard_overlap"].code, QUESTIONS["damage_guard_overlap"].rulings), ("UNRESOLVED_DAMAGE_GUARD_OVERLAP", ("GO1",)))


# ---------------------------------------------------------------- 4 章: ぬるぬる・かわす・ブリンク


class GuardTest(unittest.TestCase):
    def test_given_to_the_user_without_a_coin(self):
        """使ったときにはコインを投げず、実際に使ったポケモン自身に、次の相手の番だけの効果を与える。ブリンクは目安 30 のダメージのあと。受けた相手がきぜつしても与える。"""
        for name, (card, index, energy, _, side) in GUARDS.items():
            state, done = guarded(name, mon(RATTATA))
            with self.subTest(name=name):
                self.assertEqual([e for e in new_events(state, done, "coin_flip")], [])
                added = new_events(state, done, "persistent_effect_added")
                self.assertEqual([(e["pokemon_id"], e["persistent_effect"], e["active_turn"], e["prevent_on"]) for e in added],
                                 [(state.players[0].active.pokemon_id, GUARD, TURN + 1, side.value)])
                kinds = [e["kind"] for e in new_events(state, done, "damage", "persistent_effect_added")]
                self.assertEqual(kinds, ["damage", "persistent_effect_added"] if name == "blink" else ["persistent_effect_added"])
                holder = done.players[0].active
                self.assertEqual([(g.created_turn, g.active_turn) for g in guards_on(holder)], [(TURN, TURN + 1)])
                self.assertEqual(len(timed_damage_guards(done, holder)), 1)  # 今は TURN + 1（相手の番）
                audited(self, done)
        # 相手のラッタ（HP 30）は 30 で HP 以上になるが、効果を与える
        state, done = guarded("blink", mon(RATTATA, damage=10))
        self.assertEqual([e["persistent_effect"] for e in new_events(state, done, "persistent_effect_added")], [GUARD])
        # はたらく番だけ: 与えた番・その次の自分の番には問い合わせに出ない（期限の型の値）
        holder = done.players[0].active
        for turn, count in ((TURN, 0), (TURN + 1, 1), (TURN + 2, 0)):
            trial = done.clone()
            trial.turn_number = turn
            self.assertEqual(len(timed_damage_guards(trial, holder)), count)

    def test_receive_time_coin_faces_and_flippers(self):
        """次の相手の番に相手のワザの 0 より大きいダメージを受けるとき、ぬるぬるは相手プレイヤー・かわすとブリンクは持ち主が投げ、ぬるぬるは「うら」・ほかは「おもて」で受けない。効果は
        ダメージで消えず、その番の終わりに期限で消える。"""
        for name, (_, _, _, owner_flips, side) in GUARDS.items():
            for coin in (HD, TL):
                _, given = guarded(name, mon(JAB, (F_,)))
                done = attack(given, 0, coin)
                holder = given.players[0].active
                prevented = coin is side
                flipper = 0 if owner_flips else 1
                with self.subTest(name=name, coin=coin):
                    self.assertEqual(guard_coins(given, done), [(flipper, coin.value)])
                    self.assertEqual(checks(given, done), [(holder.pokemon_id, flipper, coin.value, not prevented, 20, 1)])
                    self.assertEqual(done.players[0].active.damage, 0 if prevented else 20)
                    self.assertNotIn((GUARD, "damaged"), removed(given, done))
                    self.assertIn((GUARD, "expired"), removed(given, done))
                    audited(self, done)

    def test_damage_only_other_effects_still_apply(self):
        """防ぐのはダメージだけ: もうどくのダメージを受けなくても、どくは受ける（ワザ全体の失敗・「とうめい」の受けないではない）。ダメージのあとの効果のコイン（でんきショックのマヒ）は
        T19b で止めずに投げる。受けた記録は「ダメージだけ受けなかった」（VOID_DODGED）。"""
        _, given = guarded("slime", mon(ARBOK, (G, G, G)))
        done = attack(given, 1, TL)
        self.assertEqual((damages(given, done), [e["condition"] for e in new_events(given, done, "special_condition")]), ([], [E.POISON]))
        records = [r for r in done.players[0].active.history if isinstance(r, AttackReceived) and r.turn == TURN + 1]
        self.assertEqual([(("damage", VOID_DODGED) in r.voided, r.damage) for r in records], [(True, 0)] if records else [])
        audited(self, done)
        _, given = guarded("dodge", mon(ELECTABUZZ, (L,)))
        done = attack(given, 0, HD, HD)  # 受けるときのコイン（持ち主・「おもて」で受けない）→ でんきショックのコイン（「おもて」でマヒ）
        self.assertEqual([(e["player"], e["source"]) for e in new_events(given, done, "coin_flip")], [(0, "persistent_effect"), (1, "attack")])
        self.assertEqual((damages(given, done), [e["condition"] for e in new_events(given, done, "special_condition")]), ([], [E.PARALYSIS]))
        audited(self, done)

    def test_zero_or_ignored_damage_flips_no_coin(self):
        """最終ダメージが 0（ウパーの抵抗力 雷 -30 でエレブーのパンチ 20 → 0）ならコインを投げない。受けるポケモンの持っている効果を除くスピードスターは、この効果も除く（コインなし。効果は
        消さない）。"""
        _, given = guarded("slime", mon(ELECTABUZZ_NEO1, (L, L, L)))
        done = attack(given, 0)
        self.assertEqual((guard_coins(given, done), checks(given, done), damages(given, done)), ([], [], [(given.players[0].active.card, 0)]))
        done = attack(given, 1)
        self.assertEqual((guard_coins(given, done), checks(given, done), done.players[0].active.damage), ([], [], 30))
        self.assertNotIn((GUARD, "damaged"), removed(given, done))
        audited(self, done)

    def test_coin_uses_the_computed_final_damage(self):
        """コインの要否と量は実際の計算の結果: かみくだく（v0.108。受けるワザのダメージの 8 段階 +20）を受けたウパーがぬるぬるを使い、次の相手の番にエレブーのパンチ 20 を受けると、
        抵抗力（雷 -30）で -10 になっても 2 段階までで 0 以下ではないので 8 段階の +20 で 10。0 より大きいのでコインを投げる（量 10）。"""
        state = board(mon(WOOPER, (W,)), opponent=mon("neo2-041", (H.DARKNESS_ENERGY_NEO1, W, W), evolved_from=["neo2-012"]),
                      opponent_bench=(mon(ELECTABUZZ_NEO1, (L, L)),), opponent_hand=(H.SWITCH,), current=1, turn=TURN - 1)
        crunched = attack(state, 0)  # TURN - 1: ヘルガーのかみくだく 30 + 悪エネルギーの 10（受けたウパーに 8 段階の +20。TURN と TURN + 1）
        self.assertEqual(crunched.players[0].active.damage, 40)
        given = attack(crunched, 0)  # TURN: ぬるぬる
        switched = play(given, H.SWITCH, player=1)
        if switched.decision is not None:
            switched = answer(switched, switched.decision.options[:1])
        done = attack(switched, 0, HD)  # TURN + 1: パンチ 20 → 抵抗力で -10 → +20 で 10。相手プレイヤーの「おもて」なので受ける
        wooper = given.players[0].active
        self.assertEqual((checks(switched, done), damages(switched, done)), ([(wooper.pokemon_id, 1, "heads", True, 10, 1)], [(wooper.card, 10)]))
        self.assertIn((GUARD, "knock_out"), removed(switched, done))  # 40 + 10 で HP 50 以上
        audited(self, done)

    def test_poison_damage_keeps_the_guard(self):
        """どくのウパーがぬるぬるを使い、そのあとのポケモンチェックでどくの 10 を受けても効果は消えない（ダメージを受けると消える効果ではない。コインも投げない）。次の相手の番のワザでは投げる。"""
        state, given = guarded("slime", mon(RATTATA, (W,)), extra={"poison": 10}.items())
        self.assertEqual([e["amount"] for e in new_events(state, given, "poison_damage")], [10])
        self.assertEqual((guard_coins(state, given), removed(state, given), len(guards_on(given.players[0].active))), ([], [], 1))
        done = attack(given, 0, TL)
        # かみつく 20 は「うら」で受けない。どくは 2 回（与えた番と、相手の番のあとのポケモンチェック）
        self.assertEqual((checks(given, done)[0][3], damages(given, done), done.players[0].active.damage), (False, [], 20))
        audited(self, done)

    def test_leaving_the_active_spot_removes_the_guard(self):
        """一般の規定: 突風でベンチにもどれば消え（理由は突風の入れ替えの switch。かわりに出たポケモンにはない）、きぜつで消える。"""
        _, given = guarded("slime", mon(RATTATA, (W,)), bench=(RATTATA,), opponent_hand=(H.GUST,))
        gusted = play(given, H.GUST, player=1)
        gusted = answer(gusted, gusted.decision.options[:1])
        self.assertEqual([(kind, reason) for kind, reason in removed(given, gusted)], [(GUARD, "switch")])
        done = attack(gusted, 0)
        self.assertEqual((guard_coins(gusted, done), checks(gusted, done)), ([], []))
        audited(self, done)
        _, given = guarded("dodge", mon(H.MACHAMP, (F_, F_, F_, F_), evolved_from=[H.MACHOP, H.MACHOKE]))
        done = attack(given, 0, TL)  # ちきゅうなげ 60（エビワラーの弱点は超）。「うら」なので受けて HP 以上
        self.assertIn((GUARD, "knock_out"), removed(given, done))

    def test_shadow_images_is_unchanged_next_to_it(self):
        """隣の旧型: かげぶんしんは今までどおり「おもて」で受けて理由 damaged で消える。新しい効果とかげぶんしんの問い合わせ・ダメージで消える処理は互いに拾わない。"""
        state = board(mon(ROCKET_SCYTHER, (G,)), opponent=mon(RATTATA, (W,)))
        given = attack(state, 0)
        done = attack(given, 0, HD)
        self.assertIn((TailsDamageGuard.kind, "damaged"), removed(given, done))
        holder = given.players[0].active
        self.assertEqual(timed_damage_guards(given, holder), ())
        _, slimed = guarded("slime", mon(RATTATA, (W,)))
        self.assertIsNone(tails_damage_guard(slimed.players[0].active))
        trial = slimed.clone()
        E.remove_on_damage(trial, 0, trial.players[0].active, 30)
        self.assertEqual(len(guards_on(trial.players[0].active)), 1)

    def test_scope_follows_the_actual_user(self):
        """範囲は発生元（v0.103 の ``Incoming``）で決める: ぬるぬる・かわすは持ち主でない使い手のワザ（返す効果の枠も同じ）、ブリンクは使い手を問わない。今の番のプレイヤーでは決めない
        （仕組みの確かめ。持ち主のワザ・持ち主の返す効果のダメージを効果がはたらく番に受ける場面は、今の写しでは起こらない）。"""
        for name in GUARDS:
            _, given = guarded(name, mon(RATTATA, (W,)))
            holder = given.players[0].active
            res = K.Resolution(given)
            found = {}
            for kind in (FrameKind.ATTACK, FrameKind.RETALIATION, FrameKind.POWER_DAMAGE, FrameKind.CONFUSION):
                for user in (0, 1):
                    fs = res.open_frame(kind, parent=None, player=user, source_pid=holder.pokemon_id, attack_key=AttackKey(RATTATA, 0))
                    found[(kind, user)] = len(K.timed_guards_for(res, fs, 0, holder))
            with self.subTest(name=name):
                expected_own = 1 if name == "blink" else 0
                self.assertEqual(found, {(FrameKind.ATTACK, 0): expected_own, (FrameKind.ATTACK, 1): 1, (FrameKind.RETALIATION, 0): expected_own,
                                         (FrameKind.RETALIATION, 1): 1, (FrameKind.POWER_DAMAGE, 0): 0, (FrameKind.POWER_DAMAGE, 1): 0,
                                         (FrameKind.CONFUSION, 0): 0, (FrameKind.CONFUSION, 1): 0})


# ---------------------------------------------------------------- 4 章: 決定・先読み・重なり


class DecisionAndPreflightTest(unittest.TestCase):
    def test_charity_decision_comes_before_the_coin(self):
        """お上品攻撃の減らす量の決定はコインの前（計算の途中の決定より先に投げない）。答えのあとの最終ダメージが 0 ならコインを投げず、0 より大きければ投げる。複製・deepcopy・pickle から
        同じ。不正な答えは状態・乱数・ログ・決定を変えずに拒否する。"""
        _, given = guarded("dodge", mon(RATTATA, (W,)), opponent_hand=(H.CHARITY,))
        asked = attack(play(given, H.CHARITY, player=1), 0)
        self.assertEqual((asked.decision.kind, guard_coins(given, asked)), (DAMAGE_REDUCTION, []))
        options = asked.decision.options
        for player, choices in ((1, (999,)), (0, options[:1])):
            before = snap(asked)
            with self.subTest(player=player, choices=choices), self.assertRaises(IllegalActionError):
                apply_kernel(asked, ResolveDecision(player, asked.decision.id, choices))
            self.assertEqual(snap(asked), before)
        zero = answer(asked, (max(options),))
        self.assertEqual((guard_coins(asked, zero), checks(asked, zero)), ([], []))
        kept = same_answers(self, with_coin_results(asked, HD), (min(options),))
        self.assertEqual([c[3] for c in checks(asked, kept)], [False])
        audited(self, kept)

    def test_preflight_tries_both_faces_and_finds_z23(self):
        """先読みはコインの両面を試す: 「ダメージを与えた後」のたおれこむは、受けないと決まる面があるので宣言の前に Z23 で止まる（理由に受けるときのコイン）。状態・乱数・ログは変えない。
        先読みの方法（derived・derived_full・legacy）は同じ結果（v0.13 の止める関数はこの効果を知らないので legacy でもすべての結果を試す）。上限は変えていない。"""
        self.assertEqual(MAX_BRANCHES, 4096)
        _, given = guarded("slime", mon(ROCKET_SNORLAX, (W, W, W)))
        error = rejects(self, given, UseAttack(1, 0), "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE")
        self.assertIn("受けるときのコインで防ぐ期限つきの効果", str(error))
        self.assertIn("受けるときのコインで防ぐ期限つきの効果", F.legacy_unknown_features(given, given.players[1].active))
        for name in GUARDS:
            _, given = guarded(name, mon(RATTATA, (W,)))
            results = [snap(apply_kernel(with_coin_results(given, HD), UseAttack(1, 0), preflight=mode)) for mode in ("derived", "derived_full", "legacy")]
            with self.subTest(name=name):
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0], results[2])

    def test_counter_placement_and_esp_redo_are_not_guard_coins(self):
        """ダメージカウンターをのせる効果（ナツメのゴルダックのダメージシフト）はダメージではないので、コインを投げずにのせる（効果も消えない）。ナツメのESPでやり直せるのはそのワザの
        説明文のコイン（ウォーターシュート）だけで、受けるときのコイン（持続する効果のコイン）にはやり直しを聞かない。"""
        _, given = guarded("slime", mon(H.SABRINAS_GOLDUCK, (PS, PS, W), damage=20, evolved_from=[H.SABRINAS_PSYDUCK]))
        shifted = attack(given, 0)
        self.assertEqual((guard_coins(given, shifted), checks(given, shifted), [e["pokemon_id"] for e in new_events(given, shifted, "place_damage_counters")]),
                         ([], [], [given.players[0].active.pokemon_id]))
        self.assertGreater(shifted.players[0].active.damage, 0)
        self.assertNotIn((GUARD, "damaged"), removed(given, shifted))
        audited(self, shifted)
        _, given = guarded("slime", mon(H.SABRINAS_GOLDUCK, (W, W, W), evolved_from=[H.SABRINAS_PSYDUCK]), opponent_hand=(H.SABRINAS_ESP,))
        esp = play(given, H.SABRINAS_ESP, player=1)
        esp = answer(esp, (esp.players[1].active.pokemon_id,))
        asked = attack(esp, 1, HD)  # ウォーターシュートのコイン（ワザの説明文）→ ESPのやり直しの決定
        self.assertEqual((asked.decision.kind, guard_coins(esp, asked)), (ESP_REDO, []))
        done = answer(asked, (), TL)  # やり直さない → 40 → 受けるときのコイン（相手プレイヤー 1）の「うら」で受けない。やり直しは聞かない
        self.assertEqual((done.decision, guard_coins(asked, done), done.players[0].active.damage), (None, [(1, "tails")], 0))
        self.assertEqual(len(new_events(esp, done, "esp_redo_declined")), 1)
        audited(self, done)

    def test_unbounded_coins_then_the_guard_coin(self):
        """「うら」が出るまで投げるコイン（れんぞくいしなげ）のダメージにも、そのあとで受けるときのコインを投げる（先読みの有限の組は最終ダメージで分けるので、根拠は変わらない）。"""
        _, given = guarded("slime", mon(GEODUDE_FOSSIL, (F_, F_)))
        done = attack(given, 0, HD, HD, TL, TL)
        self.assertEqual([(e["source"], e["result"]) for e in new_events(given, done, "coin_flip")],
                         [("attack", "heads"), ("attack", "heads"), ("attack", "tails"), ("persistent_effect", "tails")])
        self.assertEqual((checks(given, done)[0][4], checks(given, done)[0][3], done.players[0].active.damage), (20, False, 0))
        audited(self, done)

    def test_serialization_observation_and_copies(self):
        """新しい持続する効果は形式 8 の persistent_effects の種類の値と項目（面・投げる人・範囲）。形式は 26 のまま。形式 7 は持続する効果を表せないので拒否する。clone・deepcopy・pickle からも
        同じ結果。観測は種類を書き、判定のログは公開。"""
        _, given = guarded("blink", mon(RATTATA, (W,)))
        data = state_to_dict(given, format_version=max(FORMAT_VERSIONS))
        (written,) = [e for e in data["players"][0]["active"]["persistent_effects"] if e["effect"] == GUARD]
        self.assertEqual({k: written[k] for k in ("effect", "created_turn", "active_turn", "prevent_on", "flipper", "scope", "source_card_id")},
                         {"effect": GUARD, "created_turn": TURN, "active_turn": TURN + 1, "prevent_on": "heads", "flipper": "unstated", "scope": "attack",
                          "source_card_id": KADABRA})
        self.assertEqual((max(FORMAT_VERSIONS), LATEST_FORMAT), (26, 26))
        with self.assertRaises(ValueError):
            state_to_dict(given, format_version=7)
        expected = attack(given, 0, HD)
        for other in (given.clone(), copy.deepcopy(given), pickle.loads(pickle.dumps(given))):
            self.assertEqual(snap(attack(other, 0, HD)), snap(expected))
        from kyuura_engine.observation import observe, visible_log

        self.assertIn(GUARD, json.dumps(observe(given, 1), ensure_ascii=False))
        self.assertEqual([e["kind"] for e in visible_log(expected, None) if e["kind"] == "timed_damage_guard_check"], ["timed_damage_guard_check"])

    def test_invariants_find_wrong_terms_or_period(self):
        """不変条件は登録の面・投げる人・範囲と与えたログ、期間（次の相手の番）と照らす。"""
        from kyuura_engine.engine import check_invariants

        _, given = guarded("slime", mon(RATTATA, (W,)))
        self.assertEqual(check_invariants(given), [])
        for change in ({"prevent_on": "heads"}, {"flipper": GUARD_FLIPPER_OWNER}, {"scope": GUARD_SCOPE_ATTACK}, {"active_turn": TURN + 2}):
            trial = given.clone()
            holder = trial.players[0].active
            holder.persistent_effects = tuple(dataclasses.replace(e, **change) if isinstance(e, TimedDamageGuard) else e for e in holder.persistent_effects)
            with self.subTest(change=change):
                self.assertTrue(check_invariants(trial))

    def test_carried_damage_results_keep_the_old_shape(self):
        """決定をまたいで運ぶダメージの結果は、受けるときのコインの効果で受けなかったときだけ効果の種類を加える（ほかは v0.108 までと同じ 9 つの値）。"""
        plain = E.DamageResult(E.OPPONENT_ACTIVE, 1, 5, False, None, False, dodged=True)
        guarded_result = dataclasses.replace(plain, guard=GUARD)
        self.assertEqual(len(plain.carried_values()), 9)
        self.assertEqual(E.DamageResult(*plain.carried_values()), plain)
        self.assertEqual(E.DamageResult(*guarded_result.carried_values()), guarded_result)


class OverlapTest(unittest.TestCase):
    def test_copied_guard_on_top_of_shadow_images_stops_with_go1(self):
        """ピクシーがゆびをふるでかげぶんしん（以後）を使い、2 番あとにぬるぬるを使うと、相手のワザのダメージに 2 つの受けるときのコインが重なる。どちらを先に投げるか・先の結果で次を投げるか・
        かげぶんしんが消えるかは決まらないので、宣言の前（どのコインの前）に GO1 で止める（状態・乱数・ログを変えない）。"""
        state = board(mon(CLEFABLE, (W,)), opponent=mon(ROCKET_SCYTHER, (G,)), opponent_bench=(mon(WOOPER, (W, W)),), opponent_hand=(H.SWITCH,))
        asked = attack(state, 0)
        self.assertEqual((asked.decision.kind, asked.decision.options), (SELECT_ATTACK, (0, 1)))
        shadow = answer(asked, (0,))  # TURN: かげぶんしん（以後。ピクシー自身）
        switched = play(shadow, H.SWITCH, player=1)  # TURN + 1: ウパーをバトル場に出し、ワザを使わずに番を終える
        if switched.decision is not None:
            switched = answer(switched, switched.decision.options[:1])
        self.assertEqual(switched.cards[switched.players[1].active.card].card_id, WOOPER)
        asked = attack(apply_kernel(switched, EndTurn(1)), 0)
        slimed = answer(asked, (0,))  # TURN + 2: ぬるぬる（次の相手の番。ピクシー自身）
        holder = slimed.players[0].active
        self.assertIsNotNone(tails_damage_guard(holder))
        self.assertEqual([(g.active_turn, g.prevent_on, g.flipper) for g in guards_on(holder)], [(TURN + 3, "tails", GUARD_FLIPPER_OPPONENT)])
        error = rejects(self, slimed, UseAttack(1, 1), "UNRESOLVED_DAMAGE_GUARD_OVERLAP")  # TURN + 3: ウパーのしっぽでたたく（相手のワザ・20）
        self.assertIn("GO1", str(error))
        audited(self, slimed)

    def test_other_overlaps_stop_before_any_coin(self):
        """仕組みの確かめ（今の写しでは同じ番に重ならない組）: 期限つきの効果とリフレクトシールドは RF1、2 つの期限つきの効果・「とうめい」との重なりは GO1。どれもコインの前に止め、
        状態・乱数・ログを変えない。片方だけなら止めない。"""
        _, given = guarded("dodge", mon(RATTATA, (W,)))
        holder = given.players[0].active
        shield = ReflectShield(holder.card, 0, TURN, TURN + 1, 0, 20)
        with mock.patch.object(K, "reflect_shield", lambda state, pokemon: shield if pokemon.pokemon_id == holder.pokemon_id else None):
            rejects(self, given, UseAttack(1, 0), "UNRESOLVED_REFLECT_SHIELD_OVERLAP")
        two = guards_on(holder) * 2
        with mock.patch.object(K, "timed_damage_guards", lambda state, pokemon: tuple(two) if pokemon.pokemon_id == holder.pokemon_id else ()):
            rejects(self, given, UseAttack(1, 0), "UNRESOLVED_DAMAGE_GUARD_OVERLAP")
        with mock.patch.object(K.E, "evasion_power", lambda state, pokemon: ("x", None) if pokemon.pokemon_id == holder.pokemon_id else None):
            rejects(self, given, UseAttack(1, 0), "UNRESOLVED_DAMAGE_GUARD_OVERLAP")
        done = attack(given, 0, HD)
        self.assertEqual(len(checks(given, done)), 1)


class CopyTest(unittest.TestCase):
    def test_copied_guard_goes_to_the_copier(self):
        """ピクシーがゆびをふるでぬるぬる・かわす・ブリンクを使うと、効果は実際に使ったピクシーに与え、受けるときのコインの投げる人はピクシーの持ち主で決める（ぬるぬるは相手のプレイヤー 1、
        かわすは持ち主のプレイヤー 0）。ブリンクを使ったあとのユンゲラーのサイコパニック 30 は、ピクシーの抵抗力 超 -30 で 0 なのでコインを投げない。"""
        for name, card, energy, index, reply, coin, flipper in (("slime", WOOPER, (W, W), 0, 1, TL, 1), ("dodge", HITMONCHAN, (F_, F_, F_), 0, 1, HD, 0),
                                                                ("blink", KADABRA, (PS, PS, PS), 1, 0, HD, None)):
            state = board(mon(CLEFABLE, (W,)), opponent=mon(card, energy))
            asked = attack(state, 0)
            self.assertEqual(asked.decision.kind, SELECT_ATTACK)
            given = answer(asked, (index,))
            pixie = given.players[0].active
            with self.subTest(name=name):
                self.assertEqual([(g.source_card, g.prevent_on, g.flipper) for g in guards_on(pixie)],
                                 [(pixie.card, EXPECTED[GUARD_KEYS[name]].prevent_on.value, EXPECTED[GUARD_KEYS[name]].flipper)])
                self.assertEqual(guards_on(given.players[1].active), [])
                done = attack(given, reply, coin)  # 相手のしっぽでたたく 20・マッハストレート 40（ピクシーの弱点 闘で 80）・サイコパニック 30（抵抗力で 0）
                expected = [] if flipper is None else [(flipper, coin.value)]
                self.assertEqual((guard_coins(given, done), [c[3] for c in checks(given, done)], done.players[0].active.damage), (expected, [False] * len(expected), 0))
                audited(self, done)


# ---------------------------------------------------------------- 3 章: サイコパニック


class PsychicPanicTest(unittest.TestCase):
    def panic(self, opponent, *coins):
        state = board(mon(KADABRA, (PS, PS)), opponent=opponent)
        done = attack(state, 0, *coins)
        (hit,) = new_events(state, done, "damage")
        audited(self, done)
        return hit["steps"][0][1], hit["amount"]

    def test_base_then_weakness_and_resistance(self):
        """受ける相手の今のタイプが「超」なら基本となるダメージ 60、ほかは目安 30。弱点・抵抗力はそのあと（最終ダメージを 60 にしない）。"""
        self.assertEqual(self.panic(mon(WOOPER)), (30, 30))  # 水・弱点 草・抵抗力 雷
        self.assertEqual(self.panic(mon(ABRA)), (60, 120))  # 超・弱点 超
        self.assertEqual(self.panic(mon(CHANSEY)), (30, 0))  # 無色・抵抗力 超 -30（コラッタ PMCG1-060 も同じ）
        self.assertEqual(self.panic(mon(HAUNTER), TL), (60, 60))  # 超・弱点なし。「とうめい」のコインは「うら」（受ける）

    def test_current_form_type_and_copies(self):
        """印刷のタイプではなく今の姿: ［へんしん］のメタモン（無色）がユンゲラー（超）の姿なら 60（弱点も今の姿の超で 120）。ゆびをふるで使ったときも、実際に受けるポケモンのタイプ。"""
        state = board(mon(KADABRA, (PS, PS)), opponent=mon(DITTO))
        done = attack(state, 0)
        (hit,) = new_events(state, done, "damage")
        self.assertEqual((hit["steps"][0][1], hit["amount"]), (60, 120))
        state = board(mon(CLEFABLE, (W,)), opponent=mon(KADABRA, (PS, PS)))
        asked = attack(state, 0)
        done = answer(asked, (0,))
        (hit,) = new_events(asked, done, "damage")
        self.assertEqual((hit["steps"][0][1], hit["amount"]), (60, 60))  # 受けるユンゲラーは超（弱点 超だが、使ったピクシーは無色）
        audited(self, done)


# ---------------------------------------------------------------- 8 章: ログの監査


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v109_problems``）は、エンジンの登録・計算を読まずに、印刷の文面から読んだ面・投げる人・範囲と、ログから組み立てた効果・色で確かめる。エンジンの処理を
    一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の局。v0.109 のワザが出る組と seed）で、監査がそれを見つける（誤らせなければ、同じ局は監査を通る）。"""

    # 開発用の seed（4〜6。正式な対戦の seed 0〜3 とは別）のうち、3 つの効果のコイン・サイコパニックの 30 と 60 が出る局
    GAMES = ((("W109", "P109"), 6), (("P109", "W109"), 4), (("P109", "P109"), 5))

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

        seen = set()
        for labels, seed in self.GAMES:
            result = games.play(labels, seed, keep_state=True)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual((result["outcome"], result["audit"], log_problems(result["state"])), ("game_over", {}, []))
            seen |= {key for key, value in result["v109"].items() if value}
        self.assertTrue({"slime_check", "dodge_check", "blink_check", "psychic_panic_base_30", "psychic_panic_base_60"} <= seen, seen)

    def test_v108_audit_counts_a_dodged_damage_element(self):
        """修正した監査の誤検出: v0.108 の確かめ（``v108_complete``）は、受けるときのコインでそのダメージを受けなかったダメージの要素を数えず、ブリンクの「おもて」で受けなかったたたきおこすを
        「ダメージの要素が 1 つではない」と報告していた（v0.109 の正式な対戦 L108 対 P109 の seed 1 で見つけた。エンジンの不具合ではない）。受けなかった要素も、その要素の結果として数える。"""
        from tools import existing_effect_games as games

        result = games.play(("L108", "P109"), 1, keep_state=True)
        state = result["state"]
        dodged = [e for e in state.log if e["kind"] == "timed_damage_guard_check" and not e["received"] and e["effect"] == "neo4-091#1"]
        self.assertTrue(dodged)
        self.assertEqual((result["outcome"], result["audit"], log_problems(state)), ("game_over", {}, []))

    def test_audit_finds_a_skipped_coin_or_a_wrong_flipper(self):
        """コインを投げずに受けた・投げる人を取り違えた（ぬるぬるを持ち主に）。"""
        self.assertTrue(self.problems_for(mock.patch.object(K, "timed_guard_passes", lambda *a, **k: True), "判定"))
        self.assertTrue(self.problems_for(mock.patch.object(K, "timed_guard_flipper", lambda guard, owner: owner), "判定"))

    def test_audit_finds_a_guard_removed_by_damage_or_a_wrong_panic_base(self):
        """ダメージで消した（かげぶんしんの扱いを持ちこんだ）・サイコパニックを印刷のタイプ・倍数で計算した。"""
        from kyuura_engine import persistent

        original = persistent.remove_on_damage

        def also_timed(state, owner, pokemon, amount):
            original(state, owner, pokemon, amount)
            if amount > 0:
                persistent.remove_persistent_effects(state, owner, pokemon, persistent.DAMAGED, tuple(e for e in pokemon.persistent_effects if isinstance(e, TimedDamageGuard)))

        self.assertTrue(self.problems_for(mock.patch.object(K, "remove_on_damage", also_timed), "消えた", "消える"))
        doubled = {E.DamageSetAgainstType: lambda e: (P.Damage(P.OPP, P.PrintedTimesIfDefenderType(e.pokemon_type, 3)),)}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, doubled), "サイコパニック"))


class DocumentTest(unittest.TestCase):
    def test_document_names_the_shared_parts(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("TimedDamageGuard", "SelfTimedDamageGuardWithoutDamage", "DamageThenSelfTimedDamageGuard", "DamageSetAgainstType", "SelfTimedDamageGuard",
                       "AmountIfDefenderType", "TIMED_DAMAGE_GUARD_TEXTS", "timed_guard_passes", "timed_guard_overlap", "timed_damage_guard_check", "GO1", "RF1",
                       "UNRESOLVED_DAMAGE_GUARD_OVERLAP", "VOID_DODGED", "T19b", "Z23", "SS1", "TailsDamageGuard", "remove_on_damage", "Incoming", "carried_values",
                       "legacy_unknown_features", "a2b56ef", "9e8ca5c", "73a1690", "v0.2d"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()

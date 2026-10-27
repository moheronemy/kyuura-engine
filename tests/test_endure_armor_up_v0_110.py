"""v0.110（docs/endure-armor-up-v0.110.md）: 使うときのコインで、残りHPがなくなっても「きぜつ」しない期間つきの効果を自分に与えるワザ（ゴマゾウの「こらえる」・わるいフォレトスの
「こうてつか」）と、だいばくはつの 2 枚（ワザ 4）。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面。2 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録（GR-2000-P321-ATTACK-DAMAGE・
GR-2000-P323-KNOCKOUT・CR-EFFECTS-AFTER-KO・CR-GUTS-REMAINING-HP（残りHPの数え方だけ）・v0.2f のきぜつの判定の時点・v0.60 のスピードスターの読み方・v0.103 の発生元）。こうてつかの英語の欄
（致死のダメージを受けるときにコインを投げる）・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。盤面は ``build_test_state`` で作った
1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.110``）。
"""

from __future__ import annotations

import contextlib
import copy
import dataclasses
import json
import pathlib
import pickle
import re
import unittest
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    EndTurn,
    EvolvePokemon,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import ESP_REDO, SELECT_ATTACK
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.persistent import knockout_survivals
from kyuura_engine.resolution import flow as F
from kyuura_engine.resolution import kernel as K
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.events import FrameKind
from kyuura_engine.resolution.preflight import MAX_BRANCHES
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import (
    ASLEEP,
    CONFUSED,
    GUARD_SCOPE_ATTACK,
    GUARD_SCOPE_OPPONENT_ATTACK,
    PERIOD_EFFECT_TYPES,
    PERSISTENT_EFFECT_TYPES,
    KnockOutSurvival,
    PreventDamage,
    SpecialConditions,
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
DOC = ROOT / "docs" / "endure-armor-up-v0.110.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, F_, G, PS, L = H.WATER, H.FIGHTING, H.GRASS, H.PSYCHIC, H.LIGHTNING
PHANPY, FORRETRESS, PINECO = "neo1-053", "neo4-008", "neo4-005"
V0110 = (PHANPY, FORRETRESS)
V0110_ATTACKS = [AttackKey(card, index) for card in V0110 for index in range(2)]
HITMONCHAN = "neo4-070"  # エビワラー（neo4。マッハストレート（闘闘闘）40）。ゴマゾウ（HP 40・弱点 草）にちょうど 40
SQUIRTLE = "PMCG1-023"  # ゼニガメ（あわ（水）10・「おもて」でマヒ）。ダメージのあとに相手への効果のコイン
ARBOK, EKANS = "ES3-001", "PMCG4-001"
DARK_GYARADOS, MAGIKARP = "PMCG4-025", "PMCG4-020"  # わるいギャラドス（［ファイナルビーム］・HP 70）
BROCKS_SANDSHREW = "PMCG5-043"
GEODUDE_FOSSIL = "PMCG3-034"  # イシツブテ（れんぞくいしなげ（闘無）10×。「うら」が出るまで投げる）
FOCUS_BAND, EXP_ALL, ROCKETS_HIDEOUT = "neo1-088", "neo4-109", "neo3-057"
BELOW = {FORRETRESS: [PINECO], DARK_GYARADOS: [MAGIKARP], H.CLEFABLE: [H.CLEFAIRY], H.MACHAMP: [H.MACHOP, H.MACHOKE], ARBOK: [EKANS],
         H.BROCKS_SANDSLASH: [BROCKS_SANDSHREW], H.SABRINAS_GOLDUCK: [H.SABRINAS_PSYDUCK]}
SURVIVAL = KnockOutSurvival.kind

# 依頼で示された固定データの日本語（写しの文面と照らす。広い正規化をしない）。(HP, タイプ, 段階, 弱点, 抵抗力, にげる, 進化元, (名前, 必要なエネルギー, ダメージの目安, 説明), ...)
ENDURE = ("コインを投げて「おもて」なら、次の相手の番、相手のワザによるダメージで、このカードの残りHPがなくなっても、このカードは「きぜつ」しない。その場合、このカードの残りHPは「10」"
          "になる。")
ARMOR_UP = ("コインを投げて「おもて」なら、次の自分の番が終わるまで、ワザによるダメージで、このカードの残りHPがなくなっても、このカードは「きぜつ」せず、このカードの残りHPは「10」"
            "になる。")
EXPLOSION = "自分にも60ダメージ。"
QUOTED = {
    PHANPY: (40, "fighting", "basic", "grass", ("lightning", 30), 1, None, ("たいあたり", ("colorless",), "10", None), ("こらえる", ("fighting",), None, ENDURE)),
    FORRETRESS: (60, "grass", "stage1", "fire", None, 2, "クヌギダマ", ("こうてつか", ("colorless",), None, ARMOR_UP), ("だいばくはつ", ("grass", "grass"), "60", EXPLOSION)),
}
ENDURE_TERMS = (1, 1, GUARD_SCOPE_OPPONENT_ATTACK, 10)
ARMOR_TERMS = (0, 2, GUARD_SCOPE_ATTACK, 10)
EXPECTED = {
    (PHANPY, 0): E.DAMAGE_ONLY, (PHANPY, 1): E.SelfKnockOutSurvivalOnHeads(*ENDURE_TERMS),
    (FORRETRESS, 0): E.SelfKnockOutSurvivalOnHeads(*ARMOR_TERMS), (FORRETRESS, 1): E.DamageAndSelfDamage(60),
}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def answer(state, choices, *coins, player=None):
    d = state.decision
    return apply_kernel(with_coin_results(state, *coins) if coins else state, ResolveDecision(d.player if player is None else player, d.id, tuple(choices)))


def endured(opponent, coin=HD, *, phanpy=None, **kw):
    """ゴマゾウ（プレイヤー 0）が ``TURN`` 番にこらえるを使い（使うときのコイン ``coin``）、相手（プレイヤー 1）の番（``TURN + 1``）になった盤面（使う前と使ったあと）。"""
    state = board(phanpy or mon(PHANPY, (F_,)), opponent=opponent, **kw)
    return state, attack(state, 1, coin)


def armored(opponent, coin=HD, *, forretress=None, **kw):
    """わるいフォレトス（プレイヤー 0）が ``TURN`` 番にこうてつかを使い、相手の番（``TURN + 1``）になった盤面（使う前と使ったあと）。"""
    state = board(forretress or mon(FORRETRESS, (G, G)), opponent=opponent, **kw)
    return state, attack(state, 0, coin)


def own_turn_again(given):
    """相手が ``TURN + 1`` 番にワザを使わずに番を終え、持ち主の次の番（``TURN + 2``）になった盤面。"""
    return apply_kernel(given, EndTurn(1))


def settle(state):
    """待っている決定（サイドを取る・バトル場に出す）に、選べる最初のものから答えて進める。"""
    while state.decision is not None:
        state = answer(state, state.decision.options[:state.decision.min_choices])
    return state


def survived(before, after):
    """「きぜつ」しなかったログの (ポケモンの番号, 前のダメージ, あとのダメージ, 与えた番, HP 以上にしたワザの使い手)。"""
    return [(e["pokemon_id"], e["damage_before"], e["total_damage"], e["created_turns"], e["attacker"]) for e in new_events(before, after, "knockout_survived")]


def damages(before, after):
    return [(e.get("pokemon_id", e["pokemon"]), e["amount"], e["total_damage"]) for e in new_events(before, after, "damage")]


def knocked(before, after):
    return [e["pokemon"] for e in new_events(before, after, "knock_out")]


def survivals_on(pokemon):
    return [e for e in pokemon.persistent_effects if isinstance(e, KnockOutSurvival)]


@contextlib.contextmanager
def both(first, second):
    """2 つの一時的な差しかえを同時に当てる（登録の期間と、要素の期間を同じに誤らせる。不変条件は登録と照らすので、監査が印刷の文面から見つける）。"""
    with first, second:
        yield


# ---------------------------------------------------------------- 1〜3 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        """2 枚・4 つのワザの名前・必要なエネルギー・ダメージの目安・説明と、HP・タイプ・段階・弱点・抵抗力・にげる・進化元は依頼の日本語・固定データと同じ。特殊能力は 0。たいあたりは
        ``DAMAGE_ONLY``（文面・出典を書かない）。わるいフォレトスは草タイプ（こうてつかの名前で鋼にしない）。"""
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_110"]), V0110)
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
        """新しい名前はわるいフォレトスだけ（ゴマゾウ・クヌギダマは既存のカードにある）。データの欠け・同じカードの組はない。転記元は nazonobasho.com とポケモンWiki。"""
        pool = load_card_pool()
        cards = {c["id"]: c for c in read_extract()["cards"]}
        before = {d.name_ja for c, d in pool.definitions.items() if c in pool.playable_ids and c not in V0110 and d.category == "pokemon"}
        self.assertEqual({pool.definitions[c].name_ja for c in V0110} - before, {"わるいフォレトス"})
        self.assertIn("クヌギダマ", before)
        self.assertEqual({card: (cards[card]["data_gaps"], cards[card]["same_card_group"]) for card in V0110}, dict.fromkeys(V0110, ([], None)))
        self.assertEqual({card: cards[card]["ja_text_source"].split("/")[2] for card in V0110}, {PHANPY: "nazonobasho.com", FORRETRESS: "wiki.pokemonwiki.com"})

    def test_programs_and_types(self):
        """こらえる・こうてつかは新しい自分への要素だけ（コインは要素の中の使うときの 1 枚）。だいばくはつは既存の ``Damage`` の並び（相手に目安、そのあと自分に 60）。相手への効果の宣言はない。
        新しい持続する効果は、期間を明示した相手に与える効果の型・v0.109 の受けるときのコインの効果・「ダメージを受けない」状態の型とは別。"""
        programs = {
            EXPECTED[(PHANPY, 1)]: (P.SelfKnockOutSurvival(*ENDURE_TERMS),),
            EXPECTED[(FORRETRESS, 0)]: (P.SelfKnockOutSurvival(*ARMOR_TERMS),),
            EXPECTED[(FORRETRESS, 1)]: (P.Damage(P.OPP, P.Printed()), P.Damage(P.SELF, P.Fixed(60), name="self_damage")),
        }
        for effect, program in programs.items():
            with self.subTest(effect=effect):
                self.assertEqual(P.BUILDERS[type(effect)](effect), program)
                self.assertEqual(effect.opponent_effect_elements, ())
        self.assertIn(KnockOutSurvival, PERSISTENT_EFFECT_TYPES)
        self.assertNotIn(KnockOutSurvival, PERIOD_EFFECT_TYPES)
        self.assertFalse(issubclass(KnockOutSurvival, (TimedDamageGuard, PreventDamage)))
        self.assertEqual(EXPECTED[(PHANPY, 1)].survival_terms(), (KnockOutSurvival, *ENDURE_TERMS))

    def test_terms_are_bound_to_the_texts(self):
        """期間・範囲・残りHPは文面と 1 対 1: 取り違えた組は作れず、こらえるの型にこうてつかの文面・ダメージのあるワザは受け付けない。v0.109 の型（受けるときのコイン）は 2 つの文面を拒否する。
        既存の ``PreventDamageOnHeads``（かたまる）の確かめは形だけなので 2 つの文面を通すが、意味が違うので使わない（登録は新しい型）。"""
        for terms in ((1, 1, GUARD_SCOPE_ATTACK, 10), (0, 2, GUARD_SCOPE_OPPONENT_ATTACK, 10), (0, 1, GUARD_SCOPE_OPPONENT_ATTACK, 10), (1, 2, GUARD_SCOPE_ATTACK, 10),
                      (1, 1, GUARD_SCOPE_OPPONENT_ATTACK, 20), (0, 2, GUARD_SCOPE_ATTACK, 0)):
            with self.subTest(terms=terms), self.assertRaises(ValueError):
                E.SelfKnockOutSurvivalOnHeads(*terms)
        pool = load_card_pool()
        endure, armor, explosion = pool.definitions[PHANPY].attacks[1], pool.definitions[FORRETRESS].attacks[0], pool.definitions[FORRETRESS].attacks[1]
        self.assertEqual((EXPECTED[(PHANPY, 1)].check(endure), EXPECTED[(FORRETRESS, 0)].check(armor)), ([], []))
        self.assertTrue(EXPECTED[(PHANPY, 1)].check(armor))
        self.assertTrue(EXPECTED[(FORRETRESS, 0)].check(endure))
        self.assertTrue(EXPECTED[(FORRETRESS, 0)].check(explosion))
        for guard in (E.SelfTimedDamageGuardWithoutDamage(HD, "owner", GUARD_SCOPE_OPPONENT_ATTACK), E.SelfTimedDamageGuardWithoutDamage(TL, "opponent", GUARD_SCOPE_OPPONENT_ATTACK)):
            self.assertTrue(guard.check(endure) and guard.check(armor))
        self.assertEqual((E.PreventDamageOnHeads().check(endure), E.PreventDamageOnHeads().check(armor)), ([], []))
        used = {type(DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect) for key in V0110_ATTACKS}
        self.assertEqual(used & {E.PreventDamageOnHeads, E.SelfTimedDamageGuardWithoutDamage, E.DamageThenSelfTimedDamageGuard}, set())

    def test_explosion_text_and_recoil(self):
        """だいばくはつ: 既存の ``DamageAndSelfDamage`` の確かめは形だけ（反動の数を文面と照らさない）なので、ここで全文「自分にも60ダメージ。」の数と登録の反動 60・目安 60 を照らす。控えへの
        ダメージ・自分を直接きぜつさせる要素はない。"""
        printed = load_card_pool().definitions[FORRETRESS].attacks[1]
        entry = DEFAULT_EFFECTS.attack_entry(FORRETRESS, 1)
        self.assertEqual(printed.text_ja, EXPLOSION)
        self.assertEqual((int(re.fullmatch(r"自分にも(\d+)ダメージ。", printed.text_ja).group(1)), entry.effect.self_damage, printed.damage), (60, 60, 60))
        self.assertEqual(E.DamageAndSelfDamage(40).check(printed), [])  # 形だけの確かめ（変えていない。数はこのテストが照らす）
        program = P.BUILDERS[E.DamageAndSelfDamage](entry.effect)
        self.assertEqual([type(element).__name__ for element in program], ["Damage", "Damage"])
        self.assertEqual([element.target for element in program], [P.OPP, P.SELF])

    def test_unregistered_without_the_v0_110_entries(self):
        """今回の登録だけを除くと、ちょうど 2 枚が未対応にもどる（ほかのカードは失われない）。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V0110_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V0110))
        self.assertEqual(set(V0110) & set(cards_before(read_extract(), "0.110")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.109")) & set(cards_before(read_extract(), "0.111")), set(V0110))

    def test_adoption_records(self):
        """2 件の採用の記録（kyuura 73a1690・外部照合なし・kyuura の記録なし）。処理に使う文面は説明のある 3 つのワザの印刷の文面だけ（たいあたりは書かない）。停止コード KS1・KS2 は
        kyuura にない問い。"""
        sources = json.loads((ROOT / "kyuura_engine/data/card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine/data/research_links.json").read_text(encoding="utf-8"))
        adopted = links["latest_descriptions"]["adopted_printed_text"]
        texts = {PHANPY: ("attack/1",), FORRETRESS: ("attack/0", "attack/1")}
        for card in V0110:
            record = sources[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"], record["external_checks"], record["issues"],
                                  record["recorded_on"]), ("kyuura_data", "adopted", "73a169063463bbf7bcaa3137d70cbf9721d11534", [], [], [], "2026-10-27"))
                self.assertEqual(record["play_text"], dict.fromkeys(texts[card], "kyuura_printed_text"))
        self.assertEqual(sorted(key for key in adopted if key.split("/")[0] in V0110), sorted(f"{card}/{part}" for card, parts in texts.items() for part in parts))
        for key, code, ruling in (("knockout_survival_timing", "UNRESOLVED_KO_SURVIVAL_TIMING", "KS1"), ("knockout_survival_overlap", "UNRESOLVED_KO_SURVIVAL_OVERLAP", "KS2")):
            self.assertEqual((QUESTIONS[key].code, QUESTIONS[key].rulings), (code, (ruling,)))
            self.assertEqual(links["stop_codes"][code], {"engine_rulings": [{"version": "v0.110", "document": "docs/endure-armor-up-v0.110.md", "ruling_id": ruling}],
                                                         "kyuura_issue": None, "kyuura_disposition": "not_in_kyuura"})


# ---------------------------------------------------------------- 3 章: 使うときのコイン


class UseTest(unittest.TestCase):
    def test_heads_gives_the_effect_with_its_period(self):
        """使うときにコインを 1 枚（ワザの説明のコイン。ワザを使ったプレイヤー）投げ、「おもて」なら実際に使ったポケモン自身に効果を与える。こらえるは与えた番 + 1 だけ、こうてつかは与えた番〜
        与えた番 + 2（はたらく番の問い合わせ）。受けるときのコイン・使う選択はない。"""
        for name, setup, start, end in (("endure", endured, 1, 1), ("armor_up", armored, 0, 2)):
            state, given = setup(mon(H.RATTATA, (W,)))
            holder = given.players[0].active
            with self.subTest(name=name):
                self.assertEqual([(e["player"], e["source"], e["result"]) for e in new_events(state, given, "coin_flip")], [(0, "attack", "heads")])
                (added,) = new_events(state, given, "persistent_effect_added")
                self.assertEqual((added["pokemon_id"], added["persistent_effect"], added["active_turn"], added["end_turn"], added["scope"], added["remaining_hp"]),
                                 (holder.pokemon_id, SURVIVAL, TURN + start, TURN + end, (ENDURE_TERMS if name == "endure" else ARMOR_TERMS)[2], 10))
                self.assertEqual([(s.created_turn, s.active_turn, s.end_turn) for s in survivals_on(holder)], [(TURN, TURN + start, TURN + end)])
                for turn in range(TURN, TURN + 4):
                    trial = given.clone()
                    trial.turn_number = turn
                    self.assertEqual(len(knockout_survivals(trial, holder)), int(TURN + start <= turn <= TURN + end))
                self.assertEqual(new_events(state, given, "attack_failed"), [])
                audited(self, given)

    def test_tails_gives_nothing_and_keeps_an_earlier_effect(self):
        """「うら」なら何もしない（ワザの失敗ではない）。次の自分の番にこうてつかをもう一度使い「うら」でも、前の効果は消さない（その番の終わりまで）。「おもて」なら置きかえずに加える
        （その番は 2 つがはたらく）。"""
        for setup in (endured, armored):
            state, given = setup(mon(H.RATTATA, (W,)), TL)
            self.assertEqual((new_events(state, given, "persistent_effect_added"), new_events(state, given, "attack_failed")), ([], []))
            self.assertEqual(survivals_on(given.players[0].active), [])
        _, given = armored(mon(H.RATTATA, (W,)))
        again = own_turn_again(given)
        tails = attack(again, 0, TL)
        self.assertEqual([(kind, reason) for kind, reason in removed(again, tails)], [(SURVIVAL, "expired")])  # TURN + 2 の終わりに期限で消える（うらで消したのではない）
        self.assertEqual(new_events(again, tails, "persistent_effect_added"), [])
        heads = attack(again, 0, HD)
        self.assertEqual([(kind, reason) for kind, reason in removed(again, heads)], [(SURVIVAL, "expired")])
        self.assertEqual([s.created_turn for s in survivals_on(heads.players[0].active)], [TURN + 2])
        audited(self, heads)

    def test_confusion_coin_comes_before_the_use_time_coin(self):
        """こんらんのコイン（宣言のあと）と使うときのコイン（ワザの説明のコイン）は別。「うら」でこんらんしたら使うときのコインは投げない。"""
        state = board(mon(PHANPY, (F_,), confusion=True), opponent=mon(H.RATTATA, (W,)))
        done = attack(state, 1, HD, HD)
        self.assertEqual([(e["source"], e["result"]) for e in new_events(state, done, "coin_flip")], [("confusion", "heads"), ("attack", "heads")])
        self.assertEqual([e["persistent_effect"] for e in new_events(state, done, "persistent_effect_added")], [SURVIVAL])
        failed = attack(state, 1, TL)
        self.assertEqual([(e["source"], e["result"]) for e in new_events(state, failed, "coin_flip")], [("confusion", "tails")])
        self.assertEqual(new_events(state, failed, "persistent_effect_added"), [])
        audited(self, failed)

    def test_esp_redo_gives_only_on_the_final_result(self):
        """使うときのコインはワザの説明のコインなので、ナツメのESPのやり直しの対象（v0.66 の規定のまま）。やり直したら確定した結果でだけ与える（決定の前に与えない）。続きは clone・deepcopy・
        pickle から同じ。不正な答えは状態・乱数・ログ・決定を変えずに拒否する。仕組みの確かめ（ESPを持てるナツメのポケモンに、このワザを使えるものは今の写しにない）。"""
        state = board(mon(PHANPY, (F_,)), opponent=mon(H.RATTATA, (W,)))
        esp = (state.players[0].active.card,)
        with mock.patch.object(E, "esp_cards", lambda s, pokemon: esp if pokemon.pokemon_id == state.players[0].active.pokemon_id else ()), \
                mock.patch.object(E, "esp_redo_problem", lambda *a, **k: None):
            asked = attack(state, 1, TL)
            self.assertEqual((asked.decision.kind, new_events(state, asked, "persistent_effect_added")), (ESP_REDO, []))
            before = snap(asked)
            with self.assertRaises(IllegalActionError):
                apply_kernel(asked, ResolveDecision(1, asked.decision.id, ()))
            self.assertEqual(snap(asked), before)
            redone = same_answers(self, with_coin_results(asked, HD), (1,))
            self.assertEqual([e["redone"] for e in new_events(asked, redone, "esp_redo")], [("heads",)])
            self.assertEqual([e["persistent_effect"] for e in new_events(asked, redone, "persistent_effect_added")], [SURVIVAL])
            kept = answer(asked, ())
            self.assertEqual(new_events(asked, kept, "persistent_effect_added"), [])


# ---------------------------------------------------------------- 4 章: ダメージは受け、残りHP 10 で生き残る


class SurvivalTest(unittest.TestCase):
    def test_lethal_damage_is_received_then_10_remains(self):
        """次の相手の番、相手のワザのダメージでちょうど HP・大きく超えても、ダメージは受けて（ログ damage の量・合計はそのまま）、きぜつの判定で残りHP 10 にする。きぜつ・サイド・交代はない。
        効果は 1 回で消えず、その番の終わりに期限で消える。"""
        for opponent, amount in ((mon(HITMONCHAN, (F_, F_, F_)), 40), (mon(H.MACHAMP, (F_, F_, F_, F_)), 60)):
            _, given = endured(opponent)
            holder = given.players[0].active
            done = attack(given, 1) if amount == 40 else attack(given, 0)
            with self.subTest(amount=amount):
                self.assertEqual(new_events(given, done, "coin_flip"), [])  # 受けるときのコインはない（こうてつかの英語の欄の書き方を持ちこまない）
                self.assertEqual(damages(given, done), [(holder.card, amount, amount)])
                self.assertEqual(survived(given, done), [(holder.pokemon_id, amount, 30, (TURN,), 1)])
                self.assertEqual((knocked(given, done), len(done.players[1].prizes), done.players[0].active.pokemon_id, done.players[0].active.damage), ([], 6, holder.pokemon_id, 30))
                self.assertEqual([(kind, reason) for kind, reason in removed(given, done)], [(SURVIVAL, "expired")])
                self.assertIsNone(done.decision)
                audited(self, done)

    def test_nonlethal_damage_is_unchanged(self):
        """致死量未満のダメージはそのまま受ける（残りHPを変えない・ログもない）。"""
        _, given = endured(mon(H.RATTATA, (W,)))
        done = attack(given, 0)
        self.assertEqual((damages(given, done), survived(given, done), done.players[0].active.damage), ([(given.players[0].active.card, 20, 20)], [], 20))

    def test_armor_up_period_and_own_explosion(self):
        """こうてつか: 次の相手の番の致死のダメージで残りHP 10。次の自分の番のだいばくはつの反動 60（自分のワザのダメージ）でも生き残り、相手はきぜつする。その番が終わると消え、そのあとは
        「きぜつ」する。"""
        _, given = armored(mon(H.MACHAMP, (F_, F_, F_, F_)))
        holder = given.players[0].active
        hit = attack(given, 0)  # TURN + 1: ちきゅうなげ 60（わるいフォレトスの弱点は炎）
        self.assertEqual(survived(given, hit), [(holder.pokemon_id, 60, 50, (TURN,), 1)])
        state = board(mon(FORRETRESS, (G, G), damage=0), opponent=mon(H.RATTATA, (W,)), opponent_bench=(mon(H.RATTATA, (W,)),))
        given = attack(state, 0, HD)
        boom = attack(own_turn_again(given), 1)  # TURN + 2: だいばくはつ（相手に 60・自分に 60）
        forretress = given.players[0].active
        self.assertEqual([(e.get("target"), e["amount"]) for e in new_events(given, boom, "damage")], [(None, 60), ("self", 60)])
        self.assertEqual(survived(given, boom), [(forretress.pokemon_id, 60, 50, (TURN,), 0)])
        self.assertEqual(knocked(given, boom), [given.players[1].active.card])
        audited(self, boom)
        settled = settle(boom)
        later = attack(settled, 0)  # TURN + 3: 期限が過ぎた（かみつく 20 は残りHP 10 に致死）
        self.assertEqual(survived(boom, later), [])
        self.assertIn(forretress.card, knocked(boom, later))

    def test_survives_again_within_the_period(self):
        """1 回はたらいても消えない: こうてつかのわるいフォレトスが次の相手の番に残りHP 10 で生き残り、次の自分の番のだいばくはつの反動でもう一度生き残る（同じ効果の与えた番）。"""
        _, given = armored(mon(HITMONCHAN, (F_, F_, F_)), forretress=mon(FORRETRESS, (G, G), damage=20))
        holder = given.players[0].active
        hit = attack(given, 1)  # TURN + 1: マッハストレート 40（20 + 40 で HP 60）→ 残りHP 10
        self.assertEqual(survived(given, hit), [(holder.pokemon_id, 60, 50, (TURN,), 1)])
        boom = attack(hit, 1)  # TURN + 2: だいばくはつ（エビワラーに 60・自分に 60。カイリキーの［はんげき］のような特殊能力のダメージのない相手）
        self.assertEqual(survived(hit, boom), [(holder.pokemon_id, 110, 50, (TURN,), 0)])
        self.assertEqual([s.created_turn for s in survivals_on(boom.players[0].active)], [TURN])
        audited(self, boom)

    def test_explosion_without_the_effect_knocks_out_both(self):
        """隣の場面: 効果のないわるいフォレトスのだいばくはつは、自分も「きぜつ」する（同じワザの同時のきぜつ）。"""
        state = board(mon(FORRETRESS, (G, G)), opponent=mon(H.RATTATA, (W,)), opponent_bench=(mon(H.RATTATA),), current=0)
        done = attack(state, 1)
        self.assertEqual(sorted(knocked(state, done)), sorted([state.players[0].active.card, state.players[1].active.card]))
        self.assertEqual(survived(state, done), [])

    def test_both_lethal_explosion_decides_with_the_survivor(self):
        """相手と自分がともに致死量のだいばくはつでも、実際に生き残った結果のきぜつの候補で勝ち負けを決める（相手の最後のポケモン・最後のサイド: 生き残った側の勝ち。効果がなければ両方が
        「きぜつ」してサドンデス）。"""
        def explode(coin):
            state = board(mon(FORRETRESS, (G, G)), bench=(), opponent=mon(H.RATTATA, (W,)), opponent_bench=(), prizes=1, opponent_prizes=1)
            given = attack(state, 0, coin)
            return given, settle(attack(own_turn_again(given), 1))
        given, done = explode(HD)
        self.assertEqual((survived(given, done)[0][2], [(e["outcome"], e.get("winner")) for e in new_events(given, done, "game_end")]), (50, [("win", 0)]))
        given, done = explode(TL)
        self.assertEqual(survived(given, done), [])
        self.assertNotIn(("win", 0), [(e["outcome"], e.get("winner")) for e in new_events(given, done, "game_end")])

    def test_current_max_hp_is_used(self):
        """残りHP 10 は今有効な最大HPから数える: ロケット団のアジト（わるいポケモンの最大HP + 20）があれば、わるいフォレトス（印刷の HP 60）の最大HP 80 から 10 を残す（ダメージ 70）。"""
        state = board(mon(FORRETRESS, (G, G), damage=30), opponent=mon(H.RATTATA, (W,)), opponent_bench=(mon(H.RATTATA),), hand=(ROCKETS_HIDEOUT,))
        hideout = apply_kernel(state, PlayTrainer(0, next(u for u in state.players[0].hand if state.cards[u].card_id == ROCKETS_HIDEOUT)))
        given = attack(hideout, 0, HD)
        boom = attack(own_turn_again(given), 1)
        self.assertEqual(survived(given, boom), [(given.players[0].active.pokemon_id, 90, 70, (TURN,), 0)])
        self.assertEqual(E.max_hp(boom, boom.players[0].active) - boom.players[0].active.damage, 10)
        audited(self, boom)

    def test_poison_counters_and_power_damage_are_not_attack_damage(self):
        """ワザのダメージだけ: どく（ポケモンチェック）・ダメージカウンターの配置（ナツメのゴルダックのダメージシフト）では「きぜつ」する（効果がはたらく番でも）。"""
        state = board(mon(FORRETRESS, (G, G), damage=50, poison=10), opponent=mon(H.RATTATA, (W,)), opponent_bench=(mon(H.RATTATA),))
        given = attack(state, 0, HD)  # TURN に与え、そのあとのポケモンチェックのどく 10 で HP 60 以上
        self.assertEqual((survived(state, given), knocked(state, given)), ([], [state.players[0].active.card]))
        _, given = endured(mon(H.SABRINAS_GOLDUCK, (PS, PS, W), damage=20), phanpy=mon(PHANPY, (F_,), damage=30))
        shifted = attack(given, 0)
        self.assertEqual([e["pokemon_id"] for e in new_events(given, shifted, "place_damage_counters")], [given.players[0].active.pokemon_id])
        self.assertEqual((survived(given, shifted), knocked(given, shifted)), ([], [given.players[0].active.card]))

    def test_status_and_gas_do_not_stop_it(self):
        """特殊能力ではないので、持つポケモンのねむり・こんらん、場のかがくへんかガスでは止まらない。"""
        for condition in (ASLEEP, CONFUSED):
            _, given = endured(mon(HITMONCHAN, (F_, F_, F_)), opponent_bench=(mon(H.MUK, evolved_from=[H.FOSSIL_GRIMER]),))
            given.players[0].active.conditions = SpecialConditions(exclusive=condition)
            done = attack(given, 1, TL)
            with self.subTest(condition=condition):
                self.assertEqual(survived(given, done)[0][2], 30)

    def test_leaving_or_evolving_removes_it(self):
        """一般の規定: 突風でベンチにもどれば消える（理由 switch）。ゆびをふるでこうてつかを使ったピッピが進化すれば消える（理由 evolve）。"""
        _, given = endured(mon(H.RATTATA, (W,)), bench=(H.RATTATA,), opponent_hand=(H.GUST,))
        gusted = apply_kernel(given, PlayTrainer(1, next(u for u in given.players[1].hand if given.cards[u].card_id == H.GUST)))
        gusted = answer(gusted, gusted.decision.options[:1])
        self.assertEqual([(kind, reason) for kind, reason in removed(given, gusted)], [(SURVIVAL, "switch")])
        state = board(mon(H.CLEFAIRY, (W, W, W)), opponent=mon(FORRETRESS, (G,)), hand=(H.CLEFABLE,))
        asked = attack(state, 1)
        copied = answer(asked, (0,), HD)  # ゆびをふる → こうてつか（ピッピ自身に。与えた番〜 + 2）
        self.assertEqual([s.created_turn for s in survivals_on(copied.players[0].active)], [TURN])
        evolved = apply_kernel(own_turn_again(copied), EvolvePokemon(0, next(u for u in copied.players[0].hand if copied.cards[u].card_id == H.CLEFABLE),
                                                                         copied.players[0].active.pokemon_id))
        self.assertIn((SURVIVAL, "evolve"), removed(copied, evolved))

    def test_scope_follows_the_actual_user(self):
        """範囲は HP 以上にしたワザの分類の枠の実際の使い手で決める（今の番のプレイヤーではない）: こらえるは持ち主でない使い手だけ、こうてつかは使い手を問わない。ワザの効果で「きぜつ」する
        ポケモン（``res.forced``）・記録のないポケモン（こんらん・特殊能力のダメージ・カウンター）は当たらない（仕組みの確かめ）。"""
        for setup, expected in ((endured, {0: 0, 1: 1}), (armored, {0: 1, 1: 1})):
            _, given = setup(mon(H.RATTATA, (W,)))
            holder = given.players[0].active
            holder.damage = 100
            found = {}
            for user in (0, 1):
                res = K.Resolution(given)
                res.damage_ko[holder.pokemon_id] = (user, holder.pokemon_id)
                found[user] = len(K.knockout_survivals_of(res, holder))
            self.assertEqual(found, expected)
            res = K.Resolution(given)
            self.assertEqual(K.knockout_survivals_of(res, holder), ())  # 記録がない（こんらん・特殊能力のダメージ・カウンター）
            res.damage_ko[holder.pokemon_id] = (1, holder.pokemon_id)
            res.forced.add(holder.pokemon_id)
            self.assertEqual(K.knockout_survivals_of(res, holder), ())
        _, given = armored(mon(H.RATTATA, (W,)))
        holder = given.players[0].active
        holder.damage = 100
        res = K.Resolution(given)
        res.damage_ko[holder.pokemon_id] = (1, 9)
        for kind in (FrameKind.ATTACK, FrameKind.RETALIATION):
            fs = res.open_frame(kind, parent=None, player=0, source_pid=holder.pokemon_id, attack_key=AttackKey(FORRETRESS, 1))
            K.knockout_survival_after_damage(res, fs, holder)  # 同じ効果の範囲のダメージは止めない


# ---------------------------------------------------------------- 5 章: 時点（KS1）・重なり（KS2）・こんらん・先読み


class TimingAndOverlapTest(unittest.TestCase):
    def test_effect_after_lethal_damage_stops_with_ks1(self):
        """HP 以上になったあとに同じワザがこのポケモンに効果を与える（あわのマヒのコイン）場面は、残りHPを 10 にする時点で結果が変わるので宣言の前に KS1。致死量でなければ・効果がなければ
        止めない。"""
        _, given = endured(mon(SQUIRTLE, (W,)), phanpy=mon(PHANPY, (F_,), damage=30))
        error = rejects(self, given, UseAttack(1, 0), "UNRESOLVED_KO_SURVIVAL_TIMING")
        self.assertIn("KS1", str(error))
        _, nonlethal = endured(mon(SQUIRTLE, (W,)))
        done = attack(nonlethal, 0, HD)
        self.assertEqual([e["condition"] for e in new_events(nonlethal, done, "special_condition")], [E.PARALYSIS])
        _, without = endured(mon(SQUIRTLE, (W,)), TL, phanpy=mon(PHANPY, (F_,), damage=30))
        done = attack(without, 0)
        self.assertEqual(knocked(without, done), [without.players[0].active.card])

    def test_power_damage_after_lethal_damage_stops_with_ks1(self):
        """だいばくはつの反動で HP 以上になったあとに、相手のカイリキーの［はんげき］（特殊能力のダメージ）を受ける場面も KS1（すぐあとに残りHP 10 にする読み方では［はんげき］で「きぜつ」）。"""
        _, given = armored(mon(H.MACHAMP, (F_, F_, F_, F_)))
        rejects(self, own_turn_again(given), UseAttack(0, 1), "UNRESOLVED_KO_SURVIVAL_TIMING")

    def test_overlaps_with_ko_check_effects_stop_with_ks2(self):
        """同じきぜつの判定の効果がこのポケモンにかかわると KS2: 持つポケモンのきあいのハチマキ・ベンチの学習装置（「きぜつ」する対戦ポケモン）・みちづれ（「きぜつ」させる相手）・［ファイナル
        ビーム］（ダメージを与える相手）。"""
        _, given = endured(mon(HITMONCHAN, (F_, F_, F_)), phanpy=mon(PHANPY, (F_,), trainers=[(FOCUS_BAND, None)]))
        rejects(self, given, UseAttack(1, 1), "UNRESOLVED_KO_SURVIVAL_OVERLAP")
        _, given = endured(mon(HITMONCHAN, (F_, F_, F_)), bench=(mon(H.RATTATA, trainers=[(EXP_ALL, None)]),))
        rejects(self, given, UseAttack(1, 1), "UNRESOLVED_KO_SURVIVAL_OVERLAP")
        _, given = armored(mon(H.BASE_GASTLY, (PS, PS)))
        bonded = attack(given, 1)  # TURN + 1: みちづれ（超を 1 枚はがす決定）
        bonded = answer(bonded, bonded.decision.options[:1])
        rejects(self, bonded, UseAttack(0, 1), "UNRESOLVED_KO_SURVIVAL_OVERLAP")
        _, given = armored(mon(DARK_GYARADOS, (W, W, W), damage=10))
        rejects(self, own_turn_again(given), UseAttack(0, 1), "UNRESOLVED_KO_SURVIVAL_OVERLAP")

    def test_guts_overlap_mechanism_and_independent_band(self):
        """こんじょうとの重なりも KS2（仕組みの確かめ。こんじょうを持つポケモンがこの効果を持つ場面は今の写しにない）。かかわらない別のポケモンの効果（相手のきあいのハチマキ）は止めずに、それぞれ
        処理する（「きぜつ」しない効果にはコインも決定もないので順番で結果が変わらない）。"""
        _, given = endured(mon(HITMONCHAN, (F_, F_, F_)))
        holder = given.players[0].active
        original = K.ko_prevention_offers
        with mock.patch.object(K, "ko_prevention_offers", lambda res, record=True: [(0, holder, None)] if not record else original(res, record=record)):
            rejects(self, given, UseAttack(1, 1), "UNRESOLVED_KO_SURVIVAL_OVERLAP")
        state = board(mon(FORRETRESS, (G, G)), opponent=mon(H.RATTATA, (W,), trainers=[(FOCUS_BAND, None)]), opponent_bench=(mon(H.RATTATA),))
        given = attack(state, 0, HD)
        boom = attack(own_turn_again(given), 1, HD)
        self.assertEqual([e["survived"] for e in new_events(given, boom, "focus_band")], [True])
        self.assertEqual(survived(given, boom)[0][2], 50)
        audited(self, boom)

    def test_confusion_20_with_armor_up(self):
        """こうてつかを持つポケモンのワザがこんらんし、自分の 20 で残りHPがなくなるなら、こんらんの 20 が「ワザによるダメージ」かで結果が変わるので、既存の問い
        （UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS）でコインの前に止める。HP 以上にならなければ止めない。"""
        for damage, stops in ((50, True), (0, False)):
            _, given = armored(mon(H.RATTATA, (W,)), forretress=mon(FORRETRESS, (G, G), damage=damage))
            again = own_turn_again(given)
            again.players[0].active.conditions = SpecialConditions(exclusive=CONFUSED)
            with self.subTest(damage=damage):
                if stops:
                    error = rejects(self, again, UseAttack(0, 0), "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS")
                    self.assertIn("こうてつか", str(error))
                else:
                    done = attack(again, 0, TL)
                    self.assertEqual([e["amount"] for e in new_events(again, done, "confusion_damage")], [20])

    def test_speed_star_and_unbounded_coins(self):
        """スピードスター（受けるポケモンの持っている効果の影響を受けないダメージ）でも、ダメージのあとのきぜつの判定の効果なので生き残る（v0.60 の読み方の当てはめ）。「うら」が出るまで投げる
        コイン（れんぞくいしなげ）の先読みの組も、HP 以上の量はどれも残りHP 10 になるので根拠は変わらない。"""
        _, given = endured(mon(H.BROCKS_SANDSLASH, (F_, F_)), phanpy=mon(PHANPY, (F_,), damage=30))
        done = attack(given, 0)
        self.assertEqual((damages(given, done)[0][1], survived(given, done)[0][2]), (20, 30))
        for coins, total in (((HD, HD, HD, HD, TL), 30), ((TL,), 0)):
            _, given = endured(mon(GEODUDE_FOSSIL, (F_, F_)))
            done = attack(given, 0, *coins)
            with self.subTest(coins=coins):
                self.assertEqual(done.players[0].active.damage, total)
                audited(self, done)

    def test_preflight_modes_agree_and_use_no_real_coins(self):
        """先読みは使うときのコインの両面を試し、実際の乱数を使わない（derived・derived_full・legacy で同じ結果。v0.13 の止める関数は新しい効果を知らないので legacy でもすべてを試す）。
        上限は変えていない。"""
        self.assertEqual(MAX_BRANCHES, 4096)
        _, given = endured(mon(HITMONCHAN, (F_, F_, F_)))
        self.assertIn("残りHPがなくなっても「きぜつ」しない効果", F.legacy_unknown_features(given, given.players[1].active))
        results = [snap(apply_kernel(with_coin_results(given, TL), UseAttack(1, 1), preflight=mode)) for mode in ("derived", "derived_full", "legacy")]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])
        state = board(mon(PHANPY, (F_,)), opponent=mon(H.RATTATA, (W,)))
        results = [snap(apply_kernel(with_coin_results(state, HD), UseAttack(0, 1), preflight=mode)) for mode in ("derived", "derived_full", "legacy")]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])


# ---------------------------------------------------------------- 6〜8 章: コピー・保存・不変条件・決定


class CopyAndStateTest(unittest.TestCase):
    def test_copied_effects_use_the_copier(self):
        """ピクシーがゆびをふるでこらえるを使うと、実際に使ったピクシーに与え（期間はピクシーの番から）、次の相手の番の致死のダメージでピクシーの今の最大HP 70 から 10 を残す。"""
        state = board(mon(H.CLEFABLE, (W,), damage=60), opponent=mon(PHANPY, (F_,)))
        asked = attack(state, 0)
        self.assertEqual((asked.decision.kind, asked.decision.options), (SELECT_ATTACK, (0, 1)))
        given = answer(asked, (1,), HD)
        pixie = given.players[0].active
        self.assertEqual([(s.source_card, s.active_turn, s.end_turn, s.scope) for s in survivals_on(pixie)], [(pixie.card, TURN + 1, TURN + 1, GUARD_SCOPE_OPPONENT_ATTACK)])
        self.assertEqual(survivals_on(given.players[1].active), [])
        done = attack(given, 0)  # ゴマゾウのたいあたり 10（ピクシーの弱点 闘で 20。60 + 20 = 80）
        self.assertEqual(survived(given, done), [(pixie.pokemon_id, 80, 60, (TURN,), 1)])
        audited(self, done)

    def test_serialization_observation_and_copies(self):
        """新しい持続する効果は形式 8 の persistent_effects の種類の値と項目（最後の番・範囲・残りHP）。形式は 26 のまま。形式 7 は持続する効果を表せないので拒否する。clone・deepcopy・pickle から
        同じ結果。観測は種類を書き、生き残ったログは公開。"""
        _, given = armored(mon(H.MACHAMP, (F_, F_, F_, F_)))
        data = state_to_dict(given, format_version=max(FORMAT_VERSIONS))
        (written,) = [e for e in data["players"][0]["active"]["persistent_effects"] if e["effect"] == SURVIVAL]
        self.assertEqual({k: written[k] for k in ("effect", "created_turn", "active_turn", "end_turn", "scope", "remaining_hp", "source_card_id")},
                         {"effect": SURVIVAL, "created_turn": TURN, "active_turn": TURN, "end_turn": TURN + 2, "scope": "attack", "remaining_hp": 10, "source_card_id": FORRETRESS})
        self.assertEqual((max(FORMAT_VERSIONS), LATEST_FORMAT), (26, 26))
        with self.assertRaises(ValueError):
            state_to_dict(given, format_version=7)
        expected = attack(given, 0)
        for other in (given.clone(), copy.deepcopy(given), pickle.loads(pickle.dumps(given))):
            self.assertEqual(snap(attack(other, 0)), snap(expected))
        from kyuura_engine.observation import observe, visible_log

        self.assertIn(SURVIVAL, json.dumps(observe(given, 1), ensure_ascii=False))
        for viewer in (None, 0, 1):
            self.assertEqual([e["kind"] for e in visible_log(expected, viewer) if e["kind"] == "knockout_survived"], ["knockout_survived"])

    def test_pending_decision_after_survival_resumes_the_same(self):
        """生き残ったあとの決定（だいばくはつで相手をきぜつさせたあとのバトル場に出す決定）は、clone・deepcopy・pickle から同じ答えで同じ続きになる。不正な答えは状態・乱数・ログ・決定を
        変えずに拒否する。生き残ったポケモンのきぜつの原因の記録は残らない。"""
        state = board(mon(FORRETRESS, (G, G)), opponent=mon(H.RATTATA, (W,)), opponent_bench=(mon(H.RATTATA), mon(H.RATTATA)))
        given = attack(state, 0, HD)
        boom = attack(own_turn_again(given), 1)
        self.assertIsNotNone(boom.decision)
        before = snap(boom)
        with self.assertRaises(IllegalActionError):
            apply_kernel(boom, ResolveDecision(boom.decision.player, boom.decision.id, (999,)))
        self.assertEqual(snap(boom), before)
        done = same_answers(self, boom, boom.decision.options[:1])
        self.assertEqual(done.players[0].active.damage, 50)
        audited(self, done)

    def test_charity_decision_then_survival_once(self):
        """計算の途中の決定（お上品攻撃の減らす量）をまたいでも、生き残らせるのはきぜつの判定の窓の 1 回だけ（使うときのコイン・残りHPの設定を重ねない）。減らさなければ 40 で生き残り、
        減らせば致死量でなくなる。clone・deepcopy・pickle から同じ答えで同じ続き。"""
        _, given = endured(mon(HITMONCHAN, (F_, F_, F_)), opponent_hand=(H.CHARITY,))
        played = apply_kernel(given, PlayTrainer(1, next(u for u in given.players[1].hand if given.cards[u].card_id == H.CHARITY)))
        asked = attack(played, 1)
        options = asked.decision.options
        kept = same_answers(self, asked, (min(options),))
        self.assertEqual([(e[1], e[2]) for e in survived(asked, kept)], [(40, 30)])
        self.assertEqual(len(new_events(given, kept, "knockout_survived")), 1)
        reduced = answer(asked, (max(options),))
        self.assertEqual(survived(asked, reduced), [])
        audited(self, kept)

    def test_invariants_find_wrong_terms_or_period(self):
        """不変条件は登録の期間・範囲・残りHPと与えたログ、期限（最後の番の終わり）と照らす。"""
        from kyuura_engine.engine import check_invariants

        _, given = armored(mon(H.RATTATA, (W,)))
        self.assertEqual(check_invariants(given), [])
        for change in ({"end_turn": TURN + 1}, {"scope": GUARD_SCOPE_OPPONENT_ATTACK}, {"active_turn": TURN + 1}, {"remaining_hp": 20}):
            trial = given.clone()
            holder = trial.players[0].active
            holder.persistent_effects = tuple(dataclasses.replace(e, **change) if isinstance(e, KnockOutSurvival) else e for e in holder.persistent_effects)
            with self.subTest(change=change):
                self.assertTrue(check_invariants(trial))


# ---------------------------------------------------------------- 8 章: ログの監査


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v110_problems`` と本体の組み立て）は、エンジンの登録・計算を読まずに、印刷の文面から読んだ期間・範囲・残りHPと、ログから組み立てた効果・ダメージ・
    最大HPで確かめる。エンジンの処理を一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の局。v0.110 のワザが出る組と開発用の seed）で、監査がそれを見つける。"""

    # 開発用の seed（正式な対戦の seed 0〜3 とは別）のうち、こうてつかで生き残る・こらえるを与える局
    GAMES = ((("G110", "F110"), 12), (("F110", "W45"), 10))

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

    def test_tool_knows_the_ks1_stop(self):
        """直した道具の不足: v0.110 の正式な対戦の 1 回目（G110 対 F110 の seed 0）で、ナゾノクサのワザがこらえるで HP 以上になったゴマゾウにマヒのコインを投げようとして宣言が KS1 で止まり、
        道具が既知の停止として知らなかったので「予期しない拒否」になっていた（エンジンの不具合ではない）。道具の既知の停止（``V031_STOPS``）に KS1・KS2 を加え、場にはたらく効果があるときだけ
        認める。"""
        from tools import existing_effect_games as games

        result = games.play(("G110", "F110"), 0)
        self.assertEqual((result["outcome"], result["audit"]), ("game_over", {}))
        self.assertGreater(result["unresolved_rejections"].get("stopped_attack_UNRESOLVED_KO_SURVIVAL_TIMING", 0), 0)
        self.assertEqual({"UNRESOLVED_KO_SURVIVAL_TIMING", "UNRESOLVED_KO_SURVIVAL_OVERLAP"} - set(games.V031_STOPS), set())

    def test_the_unpatched_games_pass_the_audit(self):
        from tools import existing_effect_games as games

        seen = set()
        for labels, seed in self.GAMES:
            result = games.play(labels, seed, keep_state=True)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual((result["outcome"], result["audit"], log_problems(result["state"])), ("game_over", {}, []))
            seen |= {key for key, value in result["v110"].items() if value}
        self.assertTrue({"armor_up_survived", "explosion_self_survived", "endure_given", "endure_coin_tails"} <= seen, seen)

    def test_audit_finds_a_missing_or_wrong_survival(self):
        """生き残らせなかった・今有効な最大HP と違う数から 10 を残した。"""
        self.assertTrue(self.problems_for(mock.patch.object(F, "_survive_knockouts", lambda res: None), "knockout_survived なし"))
        self.assertTrue(self.problems_for(mock.patch.object(F, "max_hp", lambda state, pokemon, **kw: E.max_hp(state, pokemon, **kw) - 10), "knockout_survived"))

    def test_audit_finds_a_wrong_period_or_a_tails_effect(self):
        """期間を取り違えた（こうてつかを次の相手の番だけ）・「うら」でも与えた。"""
        wrong = {E.SelfKnockOutSurvivalOnHeads: lambda e: (P.SelfKnockOutSurvival(1, 1, e.scope, e.remaining_hp),)}
        with_terms = mock.patch.object(E.SelfKnockOutSurvivalOnHeads, "survival_terms", lambda e: (KnockOutSurvival, 1, 1, e.scope, e.remaining_hp))
        self.assertTrue(self.problems_for(both(mock.patch.dict(P.BUILDERS, wrong), with_terms), "期間", "はたらく番"))
        original = P.AttackRun.flip

        def always_heads(self, count, **kw):
            flips = original(self, count, **kw)
            return type(flips)(tuple(CoinSide.HEADS for _ in flips.results))

        self.assertTrue(self.problems_for(mock.patch.object(P.AttackRun, "flip", always_heads), "使うときのコイン"))


class DocumentTest(unittest.TestCase):
    def test_document_names_the_shared_parts(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("KnockOutSurvival", "SelfKnockOutSurvivalOnHeads", "SelfKnockOutSurvival", "KNOCKOUT_SURVIVAL_TEXTS", "knockout_survivals_of", "knockout_survival_timing",
                       "knockout_survival_overlap", "_survive_knockouts", "knockout_survived", "KS1", "KS2", "UNRESOLVED_KO_SURVIVAL_TIMING", "UNRESOLVED_KO_SURVIVAL_OVERLAP",
                       "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "FB1", "G37", "G40", "HC2", "SC1", "CR-GUTS-REMAINING-HP", "GR-2000-P321-ATTACK-DAMAGE", "DamageAndSelfDamage",
                       "PreventDamageOnHeads", "TimedDamageGuard", "legacy_unknown_features", "4246296", "9e8ca5c", "73a1690"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()

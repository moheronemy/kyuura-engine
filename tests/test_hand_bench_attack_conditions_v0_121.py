"""v0.121（docs/hand-bench-attack-conditions-v0.121.md）: 手札からの登場とワザの使用条件の 9 枚（ポケモン 7・トレーナー 2。ワザ 14）。コイル（neo2-043）・ボロのつりざお
（neo3-053）・わるいヘルガー（neo4-229）・わるいリングマ（neo4-096）・ヤドラン（ES3-021）・カスミのてあて（PR1-073）・ピカチュウ（PR1-001・PR1-003・PR1-017）。

2 章（A0）: 「なきごえ」を受けたエレキッド（neo1-044）が、次の自分の番に［わんぱくパンチ］で、効果を与えたポケモンに特殊能力のダメージを与える盤面。v0.120 までは、この場面を
今の対応カードでは起こらないとして内部エラー（``RuntimeError``）にしていた（v0.114 のエレキッドで起こる）。説明はワザのダメージに限らないが、ワザ以外のダメージを減らすかは記録で
決まらないので止める（GN1）。

盤面は ``build_test_state`` と通常の操作で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import subprocess
import unittest
from typing import ClassVar

from kyuura_engine import EndTurn, ResolveDecision, Retreat, UseAttack
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe
from kyuura_engine.resolution import programs as P_
from kyuura_engine.serialize import state_to_dict
from scripts import check_card_sources as cs
from tests import helpers as H
from tests.test_fossil_basic_virtual_attacks_v0_120 import (
    TURN,
    power_use,
    spec,
    table,
    trainer,
    use,
)
from tests.test_neo_trainer_components_v0_80 import audited, new_events
from tests.test_unown_family_powers_v0_96 import snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "hand-bench-attack-conditions-v0.121.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
L, F, W, G = H.LIGHTNING, H.FIRE, H.WATER, H.GRASS
GN1 = E.GROWL_NON_ATTACK_DAMAGE_CODE
ELEKID = "neo1-044"  # エレキッド（［わんぱくパンチ］: コインの「おもて」で相手の対戦ポケモンに 20。使ったら番は終わる）
PIKACHU_IP = "IP1-040"  # ピカチュウ（なきごえ。印刷の文面も新しい書き方）
CHARMANDER = "ES1-013"  # ヒトカゲ（なきごえ）
CHIKORITA = "PF1-001"  # チコリータ（なきごえ）
TOGEPI = "PR1-065"  # トゲピー（なきつく。「-20」で、なきごえと同じ型）
GROWLERS = (PIKACHU_IP, CHARMANDER, CHIKORITA, TOGEPI)


def growled(grower, *, elekid_active=True):
    """``grower`` がバトル場で 1 つ目のワザ（なきごえ・なきつく）を使い、番が終わった盤面（相手の番）。``elekid_active`` でなければ、効果を受けるのはラッキーで、エレキッドはベンチ。"""
    opponent = spec(ELEKID) if elekid_active else spec(H.CHANSEY)
    state = table(spec(grower, (L, L, F, W, G)), opponent=opponent, opponent_bench=() if elekid_active else (spec(ELEKID),))
    after = use(state, 0)
    assert (after.current_player, after.decision) == (1, None), "なきごえのあとは相手の番"
    return after


def elekid(state):
    side = state.players[1]
    return next(p for p in (side.active, *side.bench) if state.cards[p.card].card_id == ELEKID)


class GrowlPowerDamageTest(unittest.TestCase):
    """A0（docs 2 章）: なきごえを受けたポケモンが、はたらく番に、効果を与えたポケモンへ特殊能力のダメージを与える。"""

    def test_bratty_punch_on_the_growl_source_stops_before_the_coin(self):
        """v0.120 では［わんぱくパンチ］の宣言の確かめ（「おもて」のときのダメージ）が RuntimeError にした盤面。今は宣言の前に GN1 で止め、状態・乱数・ログを変えない。
        なきごえの 3 つの書き方と、同じ型の「なきつく」（トゲピー）で同じ。"""
        for grower in GROWLERS:
            with self.subTest(grower=grower):
                state = growled(grower)
                before = snap(state)
                with self.assertRaises(UnsupportedError) as raised:
                    power_use(state, elekid(state).pokemon_id, HD)
                self.assertIs(type(raised.exception), UnsupportedError)
                self.assertEqual(raised.exception.code, GN1)
                self.assertIn("GN1", str(raised.exception))
                self.assertEqual(snap(state), before)
                key = E.PowerKey(ELEKID, 0)
                problem = E.DEFAULT_EFFECTS.power_entry(ELEKID, 0).effect.damage_problem(state, E.PowerUse(1, elekid(state).pokemon_id, key))
                self.assertEqual(problem.code, GN1)  # 「おもて」のときのダメージの問い（コインの前。状態を変えない）

    def test_neighbours(self):
        """隣の例: 効果を受けていないベンチのエレキッドの［わんぱくパンチ］は 20 のまま（ラッキーが受けた）。効果を受けたエレキッドでも、はたらく番（なきごえの次の相手の番）が
        過ぎたあとの自分の番なら 20。「うら」なら何もしない（宣言の確かめは「おもて」のダメージで決めるので、どちらの面でも同じ答え）。"""
        from kyuura_engine import EndTurn

        bench = growled(PIKACHU_IP, elekid_active=False)
        state = growled(PIKACHU_IP)
        later = H.apply_kernel(H.apply_kernel(state, EndTurn(1)), EndTurn(0))
        self.assertEqual((later.current_player, later.turn_number), (1, state.turn_number + 2))
        for label, state in (("bench", bench), ("expired", later)):
            with self.subTest(label):
                target = state.players[0].active
                done = power_use(state, elekid(state).pokemon_id, HD)
                self.assertEqual(done.players[0].active.damage - target.damage, 20)
                self.assertEqual([e["amount"] for e in new_events(state, done, "power_damage")], [20])
                missed = power_use(state, elekid(state).pokemon_id, TL)
                self.assertEqual(missed.players[0].active.damage, target.damage)

    def test_attack_damage_rules_are_unchanged(self):
        """ワザのダメージは今までどおり: 受けた相手のワザがこのカードに与えるダメージは p.321 の 2 段階で引き（v0.76）、控えのこのカードへのワザのダメージは NK5（別の問い）。
        GN1 は特殊能力のダメージだけの問い。"""
        self.assertNotEqual(GN1, "UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET")
        self.assertEqual(GN1, "UNRESOLVED_GROWL_NON_ATTACK_DAMAGE")
        self.assertIn("GN1", E.GROWL_NON_ATTACK_DAMAGE_REASON)


# ---------------------------------------------------------------- 4 章〜9 章: 9 枚

NOW, V0114 = "2fe0bc042ce187d191843819262f8036abbb343d", "e519b99e2adcc6c2cd0998569ae5ee1101de6e89"
CHANGED_13 = {"neo2-027", "neo2-028", "neo2-030", "neo3-053", "GD3-003", "ES2-011", "ES2-028", "ES2-029", "ES3-018", "PRN-030", "PRN-039", "PRN-040", "PRN-045"}
MAGNEMITE, OLD_ROD, HOUNDOOM, URSARING, SLOWBRO, MISTYS_CARE = "neo2-043", "neo3-053", "neo4-229", "neo4-096", "ES3-021", "PR1-073"
PIKACHUS = ("PR1-001", "PR1-003", "PR1-017")
V0121 = (MAGNEMITE, OLD_ROD, HOUNDOOM, URSARING, SLOWBRO, MISTYS_CARE, *PIKACHUS)
SLOWPOKE, HOUNDOUR, TEDDIURSA, LAPRAS, LAPRAS_2, ENTEI_HOWL, DARK = "PMCG3-027", "neo2-012", "neo2-048", "PMCG3-022", "ES2-010", "neo3-010", "neo1-094"
P = H.PSYCHIC
LINKS_PATH = ROOT / "kyuura_engine" / "data" / "research_links.json"
KYUURA = ROOT.parent / "kyuura"
needs_kyuura = unittest.skipUnless((KYUURA / ".git").exists(), "kyuura の clone（../kyuura）がない")
STOP_CODES = {"SQ1": E.VIRTUAL_SNORE_CODE, "LO1": E.LOCK_ON_PROTECTED_CODE, "DK1": E.DARK_FIRE_BONUS_CODE, "HB1": E.ATTACK_HAND_BENCH_REACTION_CODE,
              "OR1": E.OLD_ROD_WITHOUT_TARGET_CODE, "MQ1": E.MISTYS_CARE_SCOPE_CODE, "MQ2": E.MISTYS_CARE_WITHOUT_TARGET_CODE}


def kyuura_json(commit, path):
    return json.loads(subprocess.check_output(["git", "-C", str(KYUURA), "show", f"{commit}:{path}"]).decode("utf-8"))


def answer(state, choices, *coins):
    d = state.decision
    s = H.with_coin_results(state, *coins) if coins else state
    return H.apply_kernel(s, ResolveDecision(d.player, d.id, tuple(choices)))


def two_player(me, them, *, my_hand=(), their_hand=(), my_discard=(), turn=TURN):
    return H.build_test_state([{"active": me[0], "bench": list(me[1:]), "hand": list(my_hand), "deck": [W] * 10, "discard": list(my_discard), "prizes": 6},
                               {"active": them[0], "bench": list(them[1:]), "hand": list(their_hand), "deck": [W] * 10, "discard": [], "prizes": 6}],
                              turn_number=turn, current_player=0)


def rejected(test, state, fn, code):
    before = snap(state)
    with test.assertRaises((IllegalActionError, UnsupportedError)) as raised:
        fn(state)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(snap(state), before)
    return raised.exception


# ---------------------------------------------------------------- 3 章: 写しの元・研究の基準の移行

class MigrationTest(unittest.TestCase):
    """3 章: 写しの元・研究の基準を e519b99 → 2fe0bc0 に上げる移行。段 v0.121 を加え、過去の段・採用の記録は書き換えない。"""

    def test_chain_and_records(self):
        from tests.test_baby_rules_evolution_v0_114 import extract_module

        module = extract_module()
        # v0.123: 段 v0.123（2fe0bc0 → 74b3ceb）を加え、v0.121 の段のあとは V0_121_KYUURA_COMMIT（2fe0bc0）に固定した。今の写しの元は最後の段のあと
        # （docs/arcanine-name-migration-v0.123.md 2 章。今の値は tests/test_arcanine_name_migration_v0_123.py）
        self.assertEqual((module.V0_121_KYUURA_COMMIT, module.V0_114_KYUURA_COMMIT), (NOW, V0114))
        self.assertEqual(module.migration_problems(), [])
        steps = [(s["id"], s["from"], s["to"]) for s in module.KYUURA_MIGRATIONS]
        self.assertEqual(steps[steps.index(("v0.121", V0114, NOW)) - 1], ("v0.114", "73a169063463bbf7bcaa3137d70cbf9721d11534", V0114))
        extract = read_extract()
        self.assertEqual(extract["source"]["commit"], module.KYUURA_MIGRATIONS[-1]["to"])
        # v0.121 の写しの組までのカードの、段 v0.121 の訂正（v0.122 から、段 v0.121 で訂正された 12 枚を写しに入れたので、その訂正は v0.122 の組のカードのもの）
        from tests.release_catalog import cards_after

        later = cards_after(extract, "0.121")
        self.assertEqual([c["id"] for c in extract["kyuura_corrections"] if c["migration"] == "v0.121" and c["card_id"] not in later], ["FIX-neo3-053-TRAINER-TEXT-JA"])
        sources = cs.load_sources()
        step = sources["data_migrations"][3]  # v0.123 で 5 段目を加えた（4 段目までは書き換えない）
        self.assertEqual((step["from"], step["to"], step["on"], step["document"]), (V0114, NOW, "2026-10-30", "docs/hand-bench-attack-conditions-v0.121.md"))
        links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
        # v0.123: 研究の基準を 74b3ceb に上げ、kyuura の論点は 74 → 79（今の値は tests/test_research_links_v0_18e.py・tests/test_catalog_contract.py）
        self.assertEqual((links["research_commit"], links["card_data_commit"]), (extract["source"]["commit"],) * 2)
        # IP1-040 のなきごえは最新の説明 LD-IP1-040-ATK0（型・量・印刷の文面の照合は v0.76 のまま。採用したときのデータのコミット・記録した日は変えない）
        entry = E.DEFAULT_EFFECTS.attack_entry("IP1-040", 0)
        self.assertEqual((entry.effect, entry.play_text_ja, entry.source), (E.ReduceDamageToSelfNextOpponentTurn(10), E.GROWL_LATEST_TEXT, "LD-IP1-040-ATK0"))
        record = sources["cards"]["IP1-040"]
        self.assertEqual((record["kyuura_commit"], record["recorded_on"], record["play_text"]["attack/0"]),
                         ("7d3f4ca76c084774efb4ac6a1d3a943387e183c3", "2026-10-20", "LD-IP1-040-ATK0"))
        self.assertEqual(tuple(record["kyuura_records"]), H.V0_121_KYUURA_RECORDS_ADDED["IP1-040"])
        self.assertEqual(links["latest_descriptions"]["registered"]["IP1-040/attack/0"], "LD-IP1-040-ATK0")
        self.assertNotIn("IP1-040/attack/0", links["latest_descriptions"]["adopted_printed_text"])
        gn1 = links["stop_codes"][GN1]
        self.assertEqual((gn1["kyuura_issue"], gn1["kyuura_disposition"]), ("UQ-GROWL-NON-ATTACK-DAMAGE", "issue_not_in_index"))

    @needs_kyuura
    def test_kyuura_difference_is_thirteen_cards_outside_the_extract(self):
        """e519b99 → 2fe0bc0 の data/cards.json: 値が変わったのは写しの外の 13 枚だけ。c932625 → 2fe0bc0 のカード本体の変更は 0。"""
        old, mid, new = (kyuura_json(commit, "data/cards.json") for commit in (V0114, "c932625053f4cd4d784585f8b6144121499d85ed", NOW))
        before = {c["id"]: c for c in old["cards"]}
        changed = {c["id"] for c in new["cards"] if c != before[c["id"]]}
        self.assertEqual(changed, CHANGED_13)
        self.assertEqual([c["id"] for c in mid["cards"] if c != {x["id"]: x for x in new["cards"]}[c["id"]]], [])
        from tests.release_catalog import cards_after

        extract = read_extract()
        extract_ids = {c["id"] for c in extract["cards"]} - set(V0121) - cards_after(extract, "0.121")  # v0.121 の時点の写し（v0.122 から 12 枚を写しに入れた）
        self.assertEqual(changed & extract_ids, set())
        self.assertEqual(len(new["cards"]), 1377)


class RegistrationTest(unittest.TestCase):
    """4 章: 9 枚・14 のワザ・トレーナー 2 枚の登録、採用の記録、研究の対応表。"""

    def test_cards_and_registrations(self):
        pool = load_card_pool()
        self.assertEqual(read_extract()["pool_v0_121"], list(V0121))
        for card in V0121:
            self.assertIn(card, pool.playable_ids, card)
        registry = E.DEFAULT_EFFECTS
        self.assertEqual(sorted(key for key in registry.attack_keys() if key.card_id in V0121), sorted(E.V0_121_ATTACKS))
        self.assertEqual(len(E.V0_121_ATTACKS), 14)
        for key in E.V0_121_ATTACKS:
            attack = pool.get(key.card_id).attacks[key.attack_index]
            self.assertIsNone(registry.attack_problem(key.card_id, attack, pool.get(key.card_id).attacks), key)
        for card in (OLD_ROD, MISTYS_CARE):
            self.assertIsNone(registry.trainer_problem(pool.get(card)), card)
        kinds = {key: type(registry.attack_entry(key.card_id, key.attack_index).effect).__name__ for key in E.V0_121_ATTACKS}
        self.assertEqual(kinds[E.AttackKey(MAGNEMITE, 0)], "WaiveTailsFailureNextTurn")
        self.assertEqual(kinds[E.AttackKey(SLOWBRO, 1)], "FailUnlessAsleepDamage")
        self.assertEqual({kinds[E.AttackKey(card, 1)] for card in PIKACHUS}, {"ParalyzeOnHeads"})
        # ピカチュウ 3 枚の pokemon のデータは同じ（採用の記録は id ごと、なきごえの出典はそれぞれの LD-）
        datas = {json.dumps(next(c for c in read_extract()["cards"] if c["id"] == card)["pokemon"], ensure_ascii=False, sort_keys=True) for card in PIKACHUS}
        self.assertEqual(len(datas), 1)
        self.assertEqual([registry.attack_entry(card, 0).source for card in PIKACHUS], [f"LD-{card}-ATK0" for card in PIKACHUS])

    def test_growl_latest_text_is_bound_to_the_amount(self):
        """5 章: 印刷の短文は、最新の説明の全文と量 10 の組だけで受け付ける（ほかの量・書き方・最新の説明のない登録は拒否）。"""
        attack = load_card_pool().get("PR1-001").attacks[0]
        self.assertEqual(E.ReduceDamageToSelfNextOpponentTurn(10, latest=E.GROWL_LATEST_TEXT).check(attack), [])
        self.assertNotEqual(E.ReduceDamageToSelfNextOpponentTurn(10).check(attack), [])  # 印刷の短文を GROWL_TEXTS に加えていない
        self.assertNotEqual(E.ReduceDamageToSelfNextOpponentTurn(20, latest=E.GROWL_LATEST_TEXT).check(attack), [])
        self.assertNotEqual(E.ReduceDamageToSelfNextOpponentTurn(10, latest="次の相手の番、うけるダメージを10へらす。").check(attack), [])
        ip = load_card_pool().get("IP1-040").attacks[0]
        self.assertNotEqual(E.ReduceDamageToSelfNextOpponentTurn(10, latest=E.GROWL_LATEST_TEXT).check(ip), [])  # 新しい書き方の印刷は組にない

    def test_adoption_records_and_links(self):
        sources = cs.load_sources()["cards"]
        links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
        for card in V0121:
            record = sources[card]
            self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"], record["external_checks"]),
                             ("kyuura_data", "adopted", NOW, "2026-10-30", []), card)
        self.assertEqual(sources[SLOWBRO]["play_text"], {"attack/0": "kyuura_printed_text", "attack/1": "LD-ES3-021-ATK1"})
        self.assertEqual(sources[OLD_ROD]["kyuura_records"], ["CR-BORO-ROD-COIN-RESULTS", "CR-BORO-ROD-POKEMON-CARDS", "UQ-CARD-USE-WITHOUT-TARGET"])
        self.assertEqual(sources[URSARING]["kyuura_records"], ["CR-UNOWN-DF-SOURCE-TYPE"])
        self.assertEqual([sources[c]["kyuura_records"] for c in (MAGNEMITE, HOUNDOOM, MISTYS_CARE)], [[], [], []])
        registered = links["latest_descriptions"]["registered"]
        self.assertEqual({k: registered[k] for k in (*(f"{c}/attack/0" for c in PIKACHUS), "ES3-021/attack/1")},
                         {**{f"{c}/attack/0": f"LD-{c}-ATK0" for c in PIKACHUS}, "ES3-021/attack/1": "LD-ES3-021-ATK1"})
        printed = set(links["latest_descriptions"]["adopted_printed_text"])
        self.assertTrue({"neo2-043/attack/0", "neo2-043/attack/1", "neo4-229/attack/0", "neo4-229/attack/1", "neo4-096/attack/0", "neo4-096/attack/1",
                         "ES3-021/attack/0", "PR1-001/attack/1", "PR1-003/attack/1", "PR1-017/attack/1"} <= printed)
        # v0.124: すごいへんしんの最新の説明 LD-ES2-032-PWR0 は、登録するまで「登録のない kyuura の最新の説明」（tests/test_super_transform_dark_pulse_v0_124.py）
        self.assertEqual([x for x in links["latest_descriptions"]["kyuura_records_not_registered"] if x != "LD-ES2-032-PWR0"], [])
        cases = {(c["kyuura_issue"], c["card_id"], c["target"]): c["engine"] for c in links["kyuura_cases_without_engine_ruling"]["cases"]}
        self.assertEqual(cases[("UQ-CARD-USE-WITHOUT-TARGET", OLD_ROD, "trainer")], {"stop_codes": [STOP_CODES["OR1"]]})
        self.assertEqual(cases[("UQ-COPIED-ATTACK", SLOWBRO, "attack/1")], {"stop_codes": ["UNRESOLVED_COPIED_ATTACK", STOP_CODES["SQ1"]]})
        for ruling, code in STOP_CODES.items():
            self.assertEqual(links["stop_codes"][code]["engine_rulings"][0]["ruling_id"], ruling)

    def test_removing_the_registrations_restores_the_previous_catalog(self):
        """今回の登録だけを外すと 1,333 枚にもどる（ほかのカードは失われない）。"""
        registry = E.DEFAULT_EFFECTS.without_attacks("test-without-v0121", list(E.V0_121_ATTACKS)).without_trainers("test-without-v0121-trainers", list(E.V0_121_TRAINERS))
        from tests.release_catalog import cards_after

        extract = read_extract()
        pool = pool_from_extract(extract, registry)
        full = load_card_pool()
        self.assertEqual(full.playable_ids - pool.playable_ids, frozenset(V0121))
        self.assertEqual(len(pool.playable_ids - cards_after(extract, "0.121")), 1333)  # v0.122 からの組を除いた、v0.121 の時点の数


class GrowlTest(unittest.TestCase):
    """5 章: ピカチュウのなきごえ（最新の説明。受けた相手のワザのダメージだけ -10。選ばない）。"""

    def test_growl_reduces_only_the_receivers_attack_damage(self):
        for card in PIKACHUS:
            with self.subTest(card=card):
                state = table(spec(card, (L, L)), opponent=spec(H.HITMONCHAN, (H.FIGHTING, H.FIGHTING, H.FIGHTING)), opponent_bench=(spec(H.HITMONCHAN, (H.FIGHTING,) * 3),))
                after = use(state, 0)
                effect = after.players[1].active.persistent_effects[0]
                self.assertEqual((type(effect).__name__, effect.amount, effect.active_turn), ("ReducedDamageToSourceNextTurn", 10, TURN + 1))
                self.assertIsNone(after.decision)  # 減らすかは選ばない
                hit = H.apply_kernel(after, UseAttack(1, 0))  # エビワラーのジャブ 20: 弱点が闘 ×2 → (20 − 10) × 2 = 20
                self.assertEqual(hit.players[0].active.damage, 20)


class SnoreAndYawnTest(unittest.TestCase):
    """6 章: おおいびき（眠ったまま使える・起きていれば失敗）とおおあくび。"""

    def slowbro(self, **extra):
        return table(spec(SLOWBRO, (P, P), below=(SLOWPOKE,), **extra), opponent=spec(H.HITMONCHAN))

    def test_snore_while_asleep_hits_and_stays_asleep(self):
        state = self.slowbro(sleep=True)
        after = use(state, 1)
        self.assertEqual([dict(e["steps"])["1 基本となる計算"] for e in new_events(state, after, "damage")], [30])  # エビワラーの弱点（超 ×2）で 60
        # 宣言しても目を覚まさない（ポケモンチェックのねむりのコインはいつもどおり投げる）
        events = new_events(state, after)
        checks = [i for i, e in enumerate(events) if e["kind"] == "sleep_check" and e["pokemon_id"] == state.players[0].active.pokemon_id]
        self.assertEqual(len(checks), 1)
        self.assertFalse(any(e["kind"] == "special_conditions_removed" for e in events[:checks[0]]))
        rejected(self, state, lambda s: use(s, 0), "POKEMON_ASLEEP")  # おおあくびは宣言できない
        rejected(self, self.slowbro(paralysis=TURN - 1), lambda s: use(s, 1), "POKEMON_PARALYZED")  # マヒは免除しない

    def test_awake_snore_fails_after_declaration(self):
        state = self.slowbro()
        after = use(state, 1)
        self.assertEqual([e["reason"] for e in new_events(state, after, "attack_failed")], ["not_asleep"])
        self.assertEqual(new_events(state, after, "damage"), [])
        self.assertEqual(after.current_player, 1)  # ワザを使ったことになり番は終わる
        confused = self.slowbro(confusion=True)
        heads = use(confused, 1, HD)
        self.assertEqual([e["kind"] for e in new_events(confused, heads) if e["kind"] in ("coin_flip", "attack_failed")], ["coin_flip", "attack_failed"])
        tails = use(confused, 1, TL)
        self.assertEqual([e["kind"] for e in new_events(confused, tails, "confusion_damage")], ["confusion_damage"])
        self.assertEqual(new_events(confused, tails, "attack_failed"), [])

    def test_retreat_and_other_attack_stay_blocked(self):
        state = table(spec(SLOWBRO, (P, P, P, P), below=(SLOWPOKE,), sleep=True), bench=(spec(H.CHANSEY),), opponent=spec(H.HITMONCHAN))
        rejected(self, state, lambda s: H.apply_kernel(s, Retreat(0, tuple(s.players[0].active.energy[:3]), s.players[0].bench[0].card)), "POKEMON_ASLEEP")

    def test_copied_snore_stops(self):
        """6.2 節: ほかのカードのワザとしてのおおいびきは、写すと HC9・持つと SQ1（選ぶと止める）。"""
        effect = E.DEFAULT_EFFECTS.attack_entry(SLOWBRO, 1).effect
        program = P_.BUILDERS[type(effect)](effect)
        self.assertEqual(program[0].copy_problem(None, None, None)[0], P_.UNRESOLVED)
        self.assertEqual(STOP_CODES["SQ1"], "UNRESOLVED_VIRTUAL_ASLEEP_ONLY_ATTACK")

    def test_yawn_puts_both_to_sleep(self):
        """おおあくびは自分 → 相手をねむりにする（ダメージを条件にしない）。おたがいがねむりになると、ポケモンチェックの既存の問いで止まる（成功率のために避けない）。"""
        effect = E.DEFAULT_EFFECTS.attack_entry(SLOWBRO, 0).effect
        program = P_.BUILDERS[type(effect)](effect)
        self.assertEqual([(type(x).__name__, x.condition, x.target, x.after_damage) for x in program], [("Status", E.SLEEP, P_.SELF, None), ("Status", E.SLEEP, P_.OPP, None)])
        state = self.slowbro()
        after = use(state, 0)
        self.assertEqual((after.players[0].active.conditions.asleep, after.players[1].active.conditions.asleep), (True, True))
        self.assertEqual(new_events(state, after, "damage"), [])
        rejected(self, after, lambda s: H.apply_kernel(s, EndTurn(1)), "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER")


class LockOnBoltTest(unittest.TestCase):
    """8.2・8.3 節: でんじほう（コインの前にダメージ・マヒを与えない）とロックオン（失効・防護）。"""

    def magnemite(self):
        return table(spec(MAGNEMITE, (L, L)), opponent=spec(H.CHANSEY, (W,)), opponent_bench=(spec(H.CHANSEY),))

    def test_bolt_needs_both_heads_without_lock_on(self):
        state = self.magnemite()
        for coins, failed in (((HD, HD), False), ((HD, TL), True), ((TL, TL), True)):
            with self.subTest(coins=coins):
                after = use(state, 1, *coins)
                self.assertEqual(bool(new_events(state, after, "attack_failed")), failed)
                self.assertEqual(after.players[1].active.conditions.paralyzed, not failed)
                self.assertEqual(bool(new_events(state, after, "damage")), not failed)

    def test_lock_on_waives_tails_next_turn_and_ends_when_the_target_leaves(self):
        state = self.magnemite()
        lock = use(state, 0)
        effect = lock.players[0].active.persistent_effects[0]
        self.assertEqual((effect.kind, effect.active_turn, effect.target_pokemon), ("next_turn_failure_waiver", TURN + 2, state.players[1].active.pokemon_id))
        later = H.apply_kernel(lock, EndTurn(1))
        self.assertIsNotNone(E.failure_waiver(later, later.players[0].active, E.AttackKey(MAGNEMITE, 1)))
        bolt = use(later, 1, TL, TL)
        self.assertEqual([e["kind"] for e in new_events(later, bolt) if e["kind"] in ("coin_flip", "attack_failure_waived", "attack_failed")],
                         ["coin_flip", "coin_flip", "attack_failure_waived"])  # コインは投げ、「うら」のまま失敗しない
        self.assertEqual([e["result"] for e in new_events(later, bolt, "coin_flip")][:2], ["tails", "tails"])
        self.assertTrue(bolt.players[1].active.conditions.paralyzed)
        # 受けた相手がベンチにもどると消える（もどっても復活しない）
        switched = H.apply_kernel(lock, Retreat(1, tuple(lock.players[1].active.energy[:1]), lock.players[1].bench[0].card))
        self.assertEqual(switched.players[0].active.persistent_effects, ())
        self.assertEqual([e["reason"] for e in new_events(lock, switched, "persistent_effect_removed")], ["target_left_active"])

    def test_lock_on_against_a_protected_target_stops(self):
        state = table(spec(MAGNEMITE, (L, L)), opponent=spec("PMCG3-030"))  # ゴースト（［とうめい］）
        rejected(self, state, lambda s: use(s, 0), STOP_CODES["LO1"])


class DarkFireTest(unittest.TestCase):
    """8.4 節: じごくのほのお。"""

    def test_without_dark_energy_only_the_bonus_is_lost(self):
        state = table(spec(HOUNDOOM, (F, W), below=(HOUNDOUR,)), opponent=spec(H.HITMONCHAN))
        after = use(state, 1)
        self.assertEqual([e["amount"] for e in new_events(state, after, "damage")], [30])
        self.assertEqual(new_events(state, after, "attack_failed"), [])

    def test_discarded_dark_energy_bonus_stops(self):
        state = table(spec(HOUNDOOM, (F, DARK), below=(HOUNDOUR,)), opponent=spec(H.HITMONCHAN))
        rejected(self, state, lambda s: use(s, 1), STOP_CODES["DK1"])


class BattleFrenzyTest(unittest.TestCase):
    """8.1 節: だいらんとう（場のポケモン全員に 1 枚ずつ。面と個体の対応）。"""

    def test_each_pokemon_gets_its_own_coin(self):
        state = table(spec(URSARING, (W, W), below=(TEDDIURSA,)), bench=(spec(H.CHANSEY),), opponent=spec(H.HITMONCHAN), opponent_bench=(spec(H.CHANSEY),))
        after = use(state, 1, HD, TL, TL, HD)
        (result,) = new_events(state, after, "pokemon_coin_results")
        opponent_active, opponent_bench = state.players[1].active.pokemon_id, state.players[1].bench[0].pokemon_id
        me, my_bench = state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id
        self.assertEqual(result["targets"], (opponent_active, opponent_bench, me, my_bench))
        self.assertEqual({p.pokemon_id: p.damage for side in after.players for p in side.in_play()}, {opponent_active: 20, opponent_bench: 0, me: 0, my_bench: 20})

    def test_twelve_pokemon_fit_the_preflight_limit_but_a_confusion_coin_does_not(self):
        """場のポケモン 12 匹（おたがいに 6 匹）の 12 枚のコインは、宣言の前の先読みの上限 4,096 の内側（試す結果 4,095）。こんらんのコインが加わると上限を超え、
        ``UNSUPPORTED_PREFLIGHT_LIMIT`` で止まる（上限を上げない・選択肢を削らない。文書 14 章）。"""
        from unittest import mock

        from kyuura_engine.resolution import preflight

        def board(**extra):
            me = spec(URSARING, (W, W), below=(TEDDIURSA,), **extra)
            return table(me, bench=[spec(H.CHANSEY) for _ in range(5)], opponent=spec(H.HITMONCHAN), opponent_bench=[spec(H.CHANSEY) for _ in range(5)])

        branches = []
        original = preflight.explore

        def counting(*args, **kwargs):
            found, tried = original(*args, **kwargs)
            branches.append(tried)
            return found, tried

        with mock.patch.object(preflight, "explore", counting):
            after = use(board(), 1, *([HD] * 12))
        self.assertEqual(branches, [4095])
        self.assertEqual(len(new_events(board(), after, "pokemon_coin_results")[0]["targets"]), 12)
        with self.assertRaises(UnsupportedError) as raised:
            H.apply_kernel(board(confusion=True), UseAttack(0, 1))
        self.assertEqual(raised.exception.code, "UNSUPPORTED_PREFLIGHT_LIMIT")


class HandBenchTest(unittest.TestCase):
    """7 章: ぶきみなとおぼえ・ちょうはつ（見えない手札・選ぶ人と持ち主・出した個体・止める場面）。"""

    def howl_state(self, their_hand, *, bench=()):
        return two_player((spec(HOUNDOOM, (F, W), below=(HOUNDOUR,)),), (spec(H.CHANSEY), *bench), their_hand=their_hand)

    def test_howl_places_and_switches_the_chosen_pokemon(self):
        state = self.howl_state([HOUNDOUR, W, H.HITMONCHAN, ENTEI_HOWL])
        asked = use(state, 0)
        d = asked.decision
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices), ("opponent_hand_to_bench", 0, 1, 1))
        entei = next(uid for uid in d.options if asked.cards[uid].card_id == ENTEI_HOWL)
        self.assertEqual(d.context_value("unresolved_choices"), (entei,))  # 場に出たときの特殊能力（HB1。選ぶと止める）
        self.assertEqual(d.context_value("unresolved_code"), STOP_CODES["HB1"])
        done = answer(asked, (d.options[0],))
        placed = new_events(asked, done, "attack_bench_from_hand")[0]
        self.assertEqual((placed["player"], placed["chooser"], placed["attacker"]), (1, 0, 0))
        self.assertEqual(done.players[1].active.pokemon_id, placed["pokemon_id"])  # 出したその個体と入れ替える
        self.assertEqual([done.cards[p.card].card_id for p in done.players[1].bench], [H.CHANSEY])
        for other in (asked.clone(), copy.deepcopy(asked), pickle.loads(pickle.dumps(asked))):
            self.assertEqual(snap(answer(other, (d.options[0],))), snap(done))
        audited(self, done)

    def test_howl_full_bench_fails_before_looking_and_empty_candidates_do_nothing(self):
        full = self.howl_state([HOUNDOUR], bench=tuple(spec(H.CHANSEY) for _ in range(5)))
        failed = use(full, 0)
        self.assertEqual([e["reason"] for e in new_events(full, failed, "attack_failed")], ["opponent_bench_full"])
        self.assertEqual(new_events(full, failed, "look_at_hand"), [])
        empty = self.howl_state([W, W])
        none = use(empty, 0)
        self.assertEqual([e["kind"] for e in new_events(empty, none) if e["kind"] in ("look_at_hand", "attack_bench_from_hand_none", "attack_failed")],
                         ["look_at_hand", "attack_bench_from_hand_none"])

    def test_heat_plate_stops_before_looking_regardless_of_the_hand(self):
        for hand in ([HOUNDOUR], [W]):
            with self.subTest(hand=hand):
                state = two_player((spec(HOUNDOOM, (F, W), below=(HOUNDOUR,)),), (spec("neo4-023", below=("neo3-008",)),), their_hand=hand)
                rejected(self, state, lambda s: use(s, 0), STOP_CODES["HB1"])

    def test_provoke_each_player_chooses_from_the_other_hand(self):
        state = two_player((spec(URSARING, (W, W), below=(TEDDIURSA,)),), (spec(H.CHANSEY),), my_hand=[TEDDIURSA, W], their_hand=[HOUNDOUR, H.HITMONCHAN])
        first = use(state, 0)
        d = first.decision
        self.assertEqual((d.player, d.min_choices, d.max_choices, d.context_value("owner"), d.context_value("stage")), (0, 0, 2, 1, 1))
        self.assertEqual([e["player"] for e in new_events(state, first, "look_at_hand")], [0, 1])  # 見るのは両方
        second = answer(first, ())  # 0 枚は出さないこと（相手の選択は省かない）
        d2 = second.decision
        self.assertEqual((d2.player, d2.context_value("owner"), d2.context_value("stage"), d2.max_choices), (1, 0, 2, 1))
        done = answer(second, d2.options)
        placed = new_events(second, done, "attack_bench_from_hand")
        self.assertEqual([(e["player"], e["chooser"]) for e in placed], [(0, 1)])
        self.assertEqual([done.cards[p.card].card_id for p in done.players[0].bench], [TEDDIURSA])
        self.assertEqual([e["kind"] for e in new_events(first, second, "attack_bench_from_hand_declined")], ["attack_bench_from_hand_declined"])
        audited(self, done)


class TrainerTest(unittest.TestCase):
    """9 章: ボロのつりざお・カスミのてあて。"""

    def rod_state(self, discard):
        return two_player((spec(H.CHANSEY),), (spec(H.CHANSEY),), my_hand=[OLD_ROD], my_discard=discard)

    def test_old_rod_faces(self):
        state = self.rod_state([H.HITMONCHAN, MISTYS_CARE])
        hh = trainer(state, OLD_ROD, HD, HD)
        self.assertEqual((hh.decision.kind, [hh.cards[u].card_id for u in hh.decision.options]), ("recover_pokemon", [H.HITMONCHAN]))
        tt = trainer(state, OLD_ROD, TL, TL)
        self.assertEqual((tt.decision.kind, [tt.cards[u].card_id for u in tt.decision.options]), ("recover_trainer", [MISTYS_CARE]))
        ht = trainer(state, OLD_ROD, HD, TL)
        self.assertIsNone(ht.decision)
        self.assertEqual([e["reason"] for e in new_events(state, ht, "trainer_take_none")], ["declined"])
        got = answer(hh, hh.decision.options)
        self.assertIn(hh.decision.options[0], got.players[0].hand)

    def test_old_rod_without_one_face_stops_before_the_coins(self):
        for discard in ([H.HITMONCHAN], [MISTYS_CARE], []):
            with self.subTest(discard=discard):
                rejected(self, self.rod_state(discard), lambda s: trainer(s, OLD_ROD, HD, HD), STOP_CODES["OR1"])

    def test_mistys_care(self):
        state = two_player((spec(LAPRAS, damage=50), spec(LAPRAS_2)), (spec("SI-018", damage=30),), my_hand=[MISTYS_CARE])
        asked = trainer(state, MISTYS_CARE)
        d = asked.decision
        theirs = state.players[1].active.pokemon_id
        self.assertEqual((d.kind, d.min_choices, d.max_choices, d.context_value("unresolved_choices"), d.context_value("unresolved_code")),
                         ("select_pokemon", 0, 1, (theirs,), STOP_CODES["MQ1"]))
        amount = answer(asked, (state.players[0].active.pokemon_id,))
        self.assertEqual(amount.decision.options, (0, 1, 2, 3))
        self.assertEqual(answer(amount, (3,)).players[0].active.damage, 20)
        with self.assertRaises(UnsupportedError) as raised:
            answer(asked, (theirs,))
        self.assertEqual(raised.exception.code, STOP_CODES["MQ1"])
        none = two_player((spec(LAPRAS),), (spec("SI-018", damage=30),), my_hand=[MISTYS_CARE])
        rejected(self, none, lambda s: trainer(s, MISTYS_CARE), STOP_CODES["MQ2"])


class SaveAndObservationTest(unittest.TestCase):
    """11 章: 形式 28 のまま。ロックオンの効果の書き出し・決定の観測。"""

    def test_lock_on_is_written_in_format_28(self):
        lock = use(table(spec(MAGNEMITE, (L, L)), opponent=spec(H.CHANSEY)), 0)
        data = state_to_dict(lock, format_version=28)
        effect = data["players"][0]["active"]["persistent_effects"][0]
        self.assertEqual({k: effect[k] for k in ("effect", "attack_index", "target_attack_index", "target_player", "target_pokemon")},
                         {"effect": "next_turn_failure_waiver", "attack_index": 0, "target_attack_index": 1, "target_player": 1,
                          "target_pokemon": lock.players[1].active.pokemon_id})
        audited(self, lock)

    def test_hand_choice_is_hidden_from_the_other_player(self):
        state = two_player((spec(HOUNDOOM, (F, W), below=(HOUNDOUR,)),), (spec(H.CHANSEY),), their_hand=[HOUNDOUR, W])
        asked = use(state, 0)
        self.assertIn("options", observe(asked, 0)["decision"])
        self.assertNotIn("options", observe(asked, 1)["decision"])
        self.assertNotIn("option_count", observe(asked, 1)["decision"])


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v121_problems``・``v121_close``）は、エンジンの登録・計算を読まずに、処理したワザ・トレーナーの印刷の文面と、ログから組み立てた場・
    コインで確かめる。正式な開始からの対戦（tools/existing_effect_games.py の局。開発用の seed 70〜73。正式な対戦の seed 0〜3 とは別）のログを 1 か所書き換える・エンジンの処理を
    一時的に誤らせると、監査が見つける。

    正式な対戦の Y121 対 U121（seed 2）は、こんらんのコインの「うら」で起きなかったちょうはつを、監査が「手札を見ていない」と誤って指摘した局（文書 13 章。エンジンの処理は正しい）。
    監査を直したあとの回帰の確かめに使う（正式な対戦の seed を選び直すためではない）。"""

    GAMES = ((("C121", "U121"), 71), (("H121", "Y121"), 73))
    _played: ClassVar[dict] = {}

    @classmethod
    def game(cls, labels, seed):
        from tools import existing_effect_games as games

        if (labels, seed) not in cls._played:
            cls._played[(labels, seed)] = games.play(labels, seed, keep_state=True)
        return cls._played[(labels, seed)]

    def rewritten(self, labels, seed, find, change=None, *, drop=False, after=None):
        """局のログの、``find`` に当たる最初のログを書き換えた（``change``）・除いた・そのあとに ``after`` で作ったログを加えた状態の監査の問題。"""
        from tests.log_audit import log_problems

        state = self.game(labels, seed)["state"].clone()
        log = list(state.log)
        index = next(i for i, e in enumerate(log) if find(log, i, e))
        event = dict(log[index])
        if change is not None:
            change(event)
        log[index:index + 1] = [] if drop else [event] if after is None else [event, after(event)]
        state.log = tuple(log)
        return log_problems(state)

    def test_the_games_pass_the_audit_and_use_the_new_mechanics(self):
        from tests.log_audit import log_problems

        used = set()
        for labels, seed in self.GAMES:
            result = self.game(labels, seed)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual((result["audit"], log_problems(result["state"])), ({}, []))
            used |= {k for k, v in result["v121"].items() if v}
        self.assertTrue({"lock_on_added", "lock_on_removed_target_left_active", "bolt_waived", "bolt_failed", "frenzy_heads", "provoke_placed_by_attacker",
                         "care_healed_2", "old_rod_HH", "howl_failed", "snore_failed", "yawn_status"} <= used)

    def test_confused_provoke_that_did_not_happen_is_not_reported(self):
        from tests.log_audit import log_problems

        result = self.game(("Y121", "U121"), 2)
        state = result["state"]
        log = state.log
        confused = [e["turn"] for i, e in enumerate(log) if e["kind"] == "attack" and state.cards[e["pokemon"]].card_id == URSARING and e["attack_index"] == 0
                    and any(x["kind"] == "confusion_damage" for x in log[i + 1:i + 4])]
        self.assertEqual(confused, [10, 16, 32])
        self.assertEqual((result["audit"], log_problems(state)), ({}, []))

    def test_audit_finds_bolt_tails_that_did_not_fail(self):
        found = self.rewritten(("C121", "U121"), 71, lambda log, i, e: e["kind"] == "attack_failed" and e.get("effect") == f"{MAGNEMITE}#1", drop=True)
        self.assertTrue([p for p in found if "失敗していない" in p])

    def test_audit_finds_a_lock_on_against_the_wrong_pokemon(self):
        found = self.rewritten(("C121", "U121"), 71, lambda log, i, e: e["kind"] == "persistent_effect_added" and e.get("persistent_effect") == "next_turn_failure_waiver",
                               lambda e: e.update(target_pokemon=e["pokemon_id"]))
        self.assertTrue([p for p in found if "受けた相手のバトル場のポケモンではない" in p])

    def test_audit_finds_battle_frenzy_coins_not_starting_from_the_defender(self):
        found = self.rewritten(("C121", "U121"), 71, lambda log, i, e: e["kind"] == "pokemon_coin_results" and e.get("effect") == f"{URSARING}#1",
                               lambda e: e.update(targets=tuple(reversed(e["targets"])), owners=tuple(reversed(e["owners"]))))
        self.assertTrue([p for p in found if "1 枚ずつではない" in p])

    def test_audit_finds_a_provoke_choice_by_the_owner(self):
        found = self.rewritten(("C121", "U121"), 71, lambda log, i, e: e["kind"] == "attack_bench_from_hand" and e.get("effect") == f"{URSARING}#0",
                               lambda e: e.update(chooser=e["player"]))
        self.assertTrue([p for p in found if "持ち主の相手ではない" in p])

    def test_audit_finds_mistys_care_removing_more_than_three(self):
        found = self.rewritten(("C121", "U121"), 71, lambda log, i, e: e["kind"] == "remove_damage_counters" and e.get("trainer_card") is not None,
                               lambda e: e.update(counters=4))
        self.assertTrue([p for p in found if "カスミのてあて" in p])

    def test_audit_finds_eerie_howl_looking_after_a_full_bench_failure(self):
        found = self.rewritten(("H121", "Y121"), 73, lambda log, i, e: e["kind"] == "attack_failed" and e.get("reason") == "opponent_bench_full",
                               after=lambda e: {"kind": "look_at_hand", "turn": e["turn"], "player": e["player"], "owner": 1 - e["player"], "cards": (),
                                                "effect": e["effect"]})
        self.assertTrue([p for p in found if "相手の手札を見ている" in p])

    def test_audit_finds_snore_that_did_not_fail_while_awake(self):
        found = self.rewritten(("H121", "Y121"), 73, lambda log, i, e: e["kind"] == "attack_failed" and e.get("reason") == "not_asleep", drop=True)
        self.assertTrue([p for p in found if "おおいびきの失敗" in p])

    def test_audit_finds_bolt_tails_waived_without_lock_on(self):
        """エンジンがロックオンの効果がなくても「うら」の失敗をなくすと、でんじほうの「うら」と、はたらくロックオンの組が合わないことを監査が見つける。"""
        from types import SimpleNamespace
        from unittest import mock

        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        def always(state, pokemon, key):
            return SimpleNamespace(kind="next_turn_failure_waiver", target_pokemon=None)

        found = []
        with mock.patch.object(E, "failure_waiver", always):
            result = games.play(("C121", "U121"), 71, keep_state=True)
        found += [p for p in log_problems(result["state"]) if "ロックオンで失敗しなかった記録" in p]
        self.assertTrue(found)


class DocumentTest(unittest.TestCase):
    def test_document_records_the_version(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("## 1. 開始点と範囲", "## 2. A0", "## 3. 写しの元・研究の基準の移行", "GN1", "SQ1", "LO1", "DK1", "HB1", "OR1", "MQ1", "MQ2",
                       "LD-ES3-021-ATK1", "CR-PIKACHU-GROWL-OPPONENT-EFFECT", "IMG-neo2-014", "0.121.0", "## 13. 検証", "## 14. 残る制限", "lockstep", "単体のテストだけ",
                       "UNSUPPORTED_PREFLIGHT_LIMIT", "4,095", "外部照合・カード画像・ガイドブックの読み直しをしていません"):
            self.assertIn(needle, text)
        v120 = (ROOT / "docs" / "fossil-basic-virtual-attacks-v0.120.md").read_text(encoding="utf-8")
        self.assertIn("IMG-neo2-035", v120)
        self.assertLess(len((ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines()), 200)


if __name__ == "__main__":
    unittest.main()

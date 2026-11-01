"""v0.125（docs/wigglytuff-helping-hand-v0.125.md）: 写しの元・研究の基準の移行（kyuura b9e7cff → 134a664。データの値は全欄が同じ）。

2 章: 移行だけの段。kyuura のプクリンの最新の説明・コインで決まる枚数の不足の調査の記録（最新の説明 4・照合 3・裁定 8・論点 2 と、既存の論点の事例）を研究の対応表・採用の記録に
結ぶ。エンジンは原典・画像を見ていない（kyuura の記録を再利用しただけ）。この段ではカードを登録せず、処理も変えない。
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import unittest

from kyuura_engine.cards import load_card_pool, read_extract
from scripts import check_card_sources as cs
from scripts import check_research_links as rl
from tests import helpers as HP
from tests.release_catalog import cards_after, cards_before
from tests.test_baby_rules_evolution_v0_114 import extract_module

ROOT = pathlib.Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
LINKS_PATH = ROOT / "kyuura_engine" / "data" / "research_links.json"
NOW, V0124 = "134a664c6adf67d5604148a31b58e1a7d26d4d6d", "b9e7cff6d2b2c6b4539ec45e61bf453879adab3a"
RESEARCH_PARENT = "6681d5c9e48eec8c4fc3a35be4caff94634067da"  # kyuura の不足の研究のコミット（134a664 の親）
ECB, V069, V097, V0114, V0121, V0123 = ("ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3",
                                        "73a169063463bbf7bcaa3137d70cbf9721d11534", "e519b99e2adcc6c2cd0998569ae5ee1101de6e89",
                                        "2fe0bc042ce187d191843819262f8036abbb343d", "74b3ceb883dd815495d13b9987433fb14b36e44d")
BASE_ENGINE = "e165fe0fb3de0e73129135f8cbaa34e2aae0eb64"  # この版の基点（v0.124 の最後のコミット。main 84bf94f を祖先に持つ）
V0125_FINAL = "19c22051d10ec2a7610e7c7641b2c6053bd5c3f1"  # v0.126: この版の最後のコミット（v0.126 で写しの元・研究の基準を 57d01f4 に上げたので、v0.125 の値はこのコミットで確かめる）
WIGGLYTUFF = "ES1-027"
NEW_LDS = ("LD-ES1-027-ATK0", "LD-ES1-027-PWR0", "LD-ES2-005-ATK0", "LD-QSG-055-ATK0")
NEW_CCS = {"ES1-027": ["CC-ES1-027-P226"], "ES2-005": ["CC-ES2-005-P82"], "QSG-055": ["CC-QSG-055-P82"]}
NEW_ISSUES = ("UQ-HELPING-HAND-CHOICE", "UQ-DESTRUCTIVE-FIRE-FAILURE")
NEW_RULINGS = {"CR-DESTRUCTIVE-FIRE-TEXT": "CONFIRMED", "CR-DRY-UP-PROCEDURE": "CONFIRMED", "CR-HELPING-HAND-USE": "CONFIRMED", "CR-INFLATE-LATEST": "CONFIRMED",
               "CR-MOUNTAIN-CRUSH-PROCEDURE": "CONFIRMED", "CR-THOUGHT-WAVE-MACHINE-PROCEDURE": "CONFIRMED", "CR-INFLATE-DAMAGE-STEP": "SUPPORTED",
               "CR-UNTIL-TAILS-NOT-CAPPED": "SUPPORTED"}
# 研究の基準を上げて加わった、エンジンの裁定 id のない事例（論点・カード・対象）。kyuura の同じ対象の事例（はかいのほのおの 5 つ・［てだすけ］の 2 つ）は 1 つの組
NEW_CASES = {
    ("UQ-CARD-USE-WITHOUT-TARGET", "ES1-027", "power/0"), ("UQ-CARD-USE-WITHOUT-TARGET", "neo4-108", "trainer"),
    ("UQ-DESTRUCTIVE-FIRE-FAILURE", "neo4-082", "attack/1"), ("UQ-HELPING-HAND-CHOICE", "ES1-027", "power/0"),
    ("UQ-NON-ATTACK-DAMAGE-MODIFIERS", "ES1-027", "attack/0"), ("UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY", "neo4-082", "attack/1"),
    ("UQ-STATED-COUNT-SHORT", "neo4-082", "attack/0"), ("UQ-STATED-COUNT-SHORT", "neo4-082", "attack/1"), ("UQ-STATED-COUNT-SHORT", "neo4-108", "trainer"),
    ("UQ-STATED-COUNT-SHORT", "ES2-005", "attack/0"), ("UQ-STATED-COUNT-SHORT", "QSG-055", "attack/0"),
}
MIGRATION_TAG = "v0.125 で研究の基準を 134a664 に上げて結んだ"
OUT_OF_SCOPE = ("neo4-082", "neo4-108", "ES2-005", "QSG-055")  # 7 章: 登録しない


def needs_kyuura(test):
    return unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")(test)


def needs_history(test):
    return unittest.skipUnless((ROOT / ".git").exists(), "このリポジトリの git の履歴がない（取り出した木）")(test)


def kyuura_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(KYUURA), "show", f"{commit}:{path}"])


def kyuura_json(commit: str, path: str):
    return json.loads(kyuura_bytes(commit, path))


def engine_json(commit: str, path: str):
    return json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"]))


# ---------------------------------------------------------------- 2 章: 移行

class MigrationChainTest(unittest.TestCase):
    """2.1 節: 段 v0.125（b9e7cff → 134a664）。過去の段の値・採用の記録の移行は書き換えない。この段に訂正はない。"""

    def test_chain(self):
        module = extract_module()
        # v0.126: 段 v0.126（134a664 → 57d01f4）を加え、v0.125 の段のあとは V0_125_KYUURA_COMMIT（134a664）に固定した。今の写しの元は最後の段のあと
        # （docs/flash-faceup-deck-v0.126.md 2 章。今の値は tests/test_flash_faceup_deck_v0_126.py）
        self.assertEqual((module.V0_125_KYUURA_COMMIT, module.V0_124_KYUURA_COMMIT, module.V0_123_KYUURA_COMMIT), (NOW, V0124, V0123))
        self.assertEqual(module.migration_problems(), [])
        self.assertEqual([(s["id"], s["from"], s["to"]) for s in module.KYUURA_MIGRATIONS][:7],
                         [("v0.69", ECB, V069), ("v0.97", V069, V097), ("v0.114", V097, V0114), ("v0.121", V0114, V0121), ("v0.123", V0121, V0123),
                          ("v0.124", V0123, V0124), ("v0.125", V0124, NOW)])
        self.assertEqual(module.KYUURA_MIGRATIONS[6]["document"], "docs/wigglytuff-helping-hand-v0.125.md")
        extract = read_extract()
        self.assertEqual((extract["source"]["commit"], extract["previous_source"]["commit"]), (module.KYUURA_MIGRATIONS[-1]["to"], ECB))
        self.assertEqual(extract["source_migrations"][6], {"id": "v0.125", "from": V0124, "to": NOW, "document": "docs/wigglytuff-helping-hand-v0.125.md", "corrections": []})
        self.assertFalse([c for c in extract["kyuura_corrections"] if c["migration"] == "v0.125"])
        # v0.124 の段のあとを写しの元の定数にもどすと、写しの元を上げたときに過去の段のあとまで変わる（連鎖が切れて止まる）
        steps = module.KYUURA_MIGRATIONS
        try:
            module.KYUURA_MIGRATIONS = (*steps[:5], {**steps[5], "to": module.KYUURA_COMMIT}, *steps[6:])
            self.assertTrue(any("その前の段のあと" in p for p in module.migration_problems()))
        finally:
            module.KYUURA_MIGRATIONS = steps
        self.assertEqual([c["card_id"] for c in extract["engine_user_corrections"]], ["PR1-069"])

    def test_adoption_migrations_are_appended(self):
        sources = cs.load_sources()
        # v0.126: 8 段目（134a664 → 57d01f4）が加わった（今の値は tests/test_flash_faceup_deck_v0_126.py）。v0.125 までの 7 段は書き換えない
        self.assertEqual([(m["from"], m["to"], m["on"]) for m in sources["data_migrations"]][:7],
                         [(ECB, V069, "2026-10-19"), (V069, V097, "2026-10-25"), (V097, V0114, "2026-10-28"), (V0114, V0121, "2026-10-30"),
                          (V0121, V0123, "2026-10-31"), (V0123, V0124, "2026-10-31"), (V0124, NOW, "2026-10-31")])
        self.assertEqual(sources["data_migrations"][6]["document"], "docs/wigglytuff-helping-hand-v0.125.md")
        self.assertEqual(cs.data_migrations(sources, read_extract())[1], [])
        # 採用したときのデータのコミットが 134a664 の記録は、この版で写しに加えたカード（pool_v0_125）だけ（移行の段では採用し直していない）
        self.assertEqual({card for card, record in sources["cards"].items() if record.get("kyuura_commit") == NOW}, set(read_extract().get("pool_v0_125", ())))

    @needs_history
    def test_extract_is_unchanged_for_the_base_cards(self):
        """基点の写しの 1,360 枚（と参照のカード）は同じ値。変わったのは写しの元の記録と、移行の段だけ。"""
        before = engine_json(BASE_ENGINE, "kyuura_engine/data/kyuura_cards.json")
        now = read_extract()
        old = {card["id"]: card for card in before["cards"]}
        new = {card["id"]: card for card in now["cards"]}
        self.assertLessEqual(set(old), set(new))
        self.assertEqual({card for card in old if old[card] != new[card]}, set())
        # v0.126: v0.126 で写しに加えたカード（pool_v0_126）も基点にない。段 v0.126 の訂正（写しの外の PR1-027）が台帳の写しに加わった（tests/test_flash_faceup_deck_v0_126.py）
        # v0.127: v0.127 で写しに加えたカード（pool_v0_127。段は加えていない）も基点にない
        # v0.129: カツラのクイズ その1（pool_v0_129）も基点にない
        self.assertEqual(set(new) - set(old), set(now.get("pool_v0_125", ())) | set(now.get("pool_v0_126", ())) | set(now.get("pool_v0_127", ()))
                         | set(now.get("pool_v0_129", ())) | set(now.get("pool_v0_130", ()))  # v0.130: とりかえっこプリーズ（pool_v0_130）も基点にない
                         | set(now.get("pool_v0_131", ()))  # v0.131: ナッシー[Exeggutor]（pool_v0_131）も基点にない
                         | set(now.get("pool_v0_132", ())))  # v0.132: ヤドキング（pool_v0_132）も基点にない
        self.assertNotIn(WIGGLYTUFF, old)
        self.assertEqual(before["kyuura_corrections"], [c for c in now["kyuura_corrections"] if c["migration"] != "v0.126"])

    @needs_kyuura
    def test_kyuura_card_data_is_identical(self):
        """b9e7cff → 134a664 の data/cards.json: バイト列が同じ（1,377 件の全欄が同じ）。台帳は ES1-027 の候補の later_notes だけが加わり、訂正の数・候補の状態は同じ。"""
        self.assertEqual(kyuura_bytes(V0124, "data/cards.json"), kyuura_bytes(NOW, "data/cards.json"))
        self.assertEqual(len(kyuura_json(NOW, "data/cards.json")["cards"]), 1377)
        old, new = (kyuura_json(commit, "data/curation/card_corrections.json") for commit in (V0124, NOW))
        self.assertEqual(old["corrections"], new["corrections"])
        old_candidates = {(c["card_id"], c["field"]): c for c in old["candidates"]}
        new_candidates = {(c["card_id"], c["field"]): c for c in new["candidates"]}
        self.assertEqual(set(old_candidates), set(new_candidates))
        changed = {key for key in new_candidates if new_candidates[key] != old_candidates[key]}
        self.assertEqual(changed, {(WIGGLYTUFF, "pokemon.attacks[0].text.ja")})
        candidate = new_candidates[(WIGGLYTUFF, "pokemon.attacks[0].text.ja")]
        self.assertEqual(candidate["status"], "held_illegible_print")  # 最新の説明を読んでも、印刷の 1 字が読めたことにはしない
        self.assertEqual({k: v for k, v in candidate.items() if k != "later_notes"}, old_candidates[(WIGGLYTUFF, "pokemon.attacks[0].text.ja")])


class AdoptionRecordTest(unittest.TestCase):
    """2.3 節: 採用の記録。登録済みのカードの kyuura_records に加わったのは、ゴローン（ES2-023）の CR-UNTIL-TAILS-NOT-CAPPED だけ。採用したときのコミット・日付は書き換えない。"""

    def test_records_added_by_the_research_commit(self):
        cards = cs.load_sources()["cards"]
        self.assertEqual(HP.V0_125_KYUURA_RECORDS_ADDED, {"ES2-023": ("CR-UNTIL-TAILS-NOT-CAPPED",)})
        record = cards["ES2-023"]
        self.assertEqual((record["kyuura_records"], record["kyuura_commit"], record["recorded_on"]),
                         (["CR-UNTIL-TAILS-NOT-CAPPED"], V069, "2026-10-19"))

    def test_registered_until_tails_coins_are_not_capped(self):
        """CR-UNTIL-TAILS-NOT-CAPPED（SUPPORTED）: 登録済みのれんぞくいわなげ（ES2-023）は v0.64 の型のまま「うら」が出るまで投げる（コインの数・ダメージに上限を置かない）。"""
        from kyuura_engine.effects import DEFAULT_EFFECTS, CoinsUntilTailsDamage

        entry = DEFAULT_EFFECTS.attack_entry("ES2-023", 0)
        self.assertIsInstance(entry.effect, CoinsUntilTailsDamage)
        self.assertNotIn("max", {f for f in vars(entry.effect)})


class ResearchLinksTest(unittest.TestCase):
    """2.4 節: 研究の対応表。論点 88 → 90。研究の論点の数を停止コード・未解決の数にそろえない。"""

    @classmethod
    def setUpClass(cls):
        cls.links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))

    def test_commits_and_counts(self):
        # v0.126: 研究の基準を 57d01f4 に上げた（今の値は tests/test_flash_faceup_deck_v0_126.py・tests/test_catalog_contract.py）。v0.125 の値は、その版の最後のコミットの対応表で確かめる
        if not (ROOT / ".git").exists():
            self.skipTest("このリポジトリの git の履歴がない（取り出した木）")
        links = engine_json(V0125_FINAL, "kyuura_engine/data/research_links.json")
        self.assertEqual((links["research_commit"], links["card_data_commit"], links["research_branch"]), (NOW, NOW, "claude/eloquent-lamport-5xyv5r"))
        self.assertEqual(links["counts"]["kyuura_issues"], 90)
        self.assertEqual(links["engine_import_id"], "ENGINE-46A3E2E")
        # v0.125 の最後のコミットではプクリンを登録した
        self.assertEqual(links["latest_descriptions"]["kyuura_records_not_registered"], ["LD-ES2-005-ATK0", "LD-QSG-055-ATK0"])
        self.assertIn(WIGGLYTUFF, load_card_pool().playable_ids)
        # v0.127: ファイヤー 2 枚を登録して、ドライアップの最新の説明を registered に移した（tests/test_deferred_shortage_user_promos_v0_127.py）
        self.assertEqual(self.links["latest_descriptions"]["kyuura_records_not_registered"], [])
        not_in_engine = self.links["card_checks"]["not_in_engine"]
        for card, ids in NEW_CCS.items():
            self.assertEqual(not_in_engine.get(card), ids, card)

    def test_new_cases(self):
        added = [c for c in self.links["kyuura_cases_without_engine_ruling"]["cases"] if MIGRATION_TAG in c.get("note", "")]
        self.assertEqual({(c["kyuura_issue"], c["card_id"], c["target"]) for c in added}, NEW_CASES)
        self.assertEqual(len(added), 11)
        # 登録しないカード（7 章）の事例は、登録のあとも unregistered のまま。v0.127 で、怪電波マシーン・ファイヤー 2 枚を途中停止の基盤とともに登録し、その事例を
        # DU1・TW1・TW2 に結んだ（tests/test_deferred_shortage_user_promos_v0_127.py）。ひかるバンギラスは登録していない（unregistered のまま）
        later = set(cards_after(read_extract(), "0.126"))
        for case in added:
            if case["card_id"] in OUT_OF_SCOPE and case["card_id"] not in later:
                self.assertEqual(case["engine"], {"unregistered": True}, case)
            elif case["card_id"] in OUT_OF_SCOPE:
                self.assertTrue(case["engine"]["stop_codes"], case)
        self.assertEqual(set(OUT_OF_SCOPE) & load_card_pool().playable_ids, set(OUT_OF_SCOPE) & later)
        self.assertFalse(set(OUT_OF_SCOPE) & cards_before(read_extract(), "0.127"))

    @needs_kyuura
    def test_links_agree_with_kyuura(self):
        self.assertEqual(rl.check(KYUURA), [])

    @needs_kyuura
    def test_research_records(self):
        self.assertEqual(subprocess.check_output(["git", "-C", str(KYUURA), "rev-parse", f"{NOW}^"]).decode().strip(), RESEARCH_PARENT)
        old, new = (kyuura_json(commit, "data/sidecar/rulings.json") for commit in (V0124, NOW))
        rulings = {r["id"]: r["status"] for r in new["rulings"]}
        self.assertEqual({k: v for k, v in rulings.items() if k not in {r["id"] for r in old["rulings"]}}, NEW_RULINGS)
        self.assertEqual((len(new["rulings"]), len(new["issues"]), len(new["rule_clauses"])), (345, 90, 41))
        self.assertEqual(sorted({i["id"] for i in new["issues"]} - {i["id"] for i in old["issues"]}), sorted(NEW_ISSUES))
        self.assertTrue(all(i["status"] == "UNRESOLVED" for i in new["issues"] if i["id"] in NEW_ISSUES))  # 研究の取り込みは論点の解決ではない
        descriptions = {r["id"] for r in kyuura_json(NOW, "data/sidecar/latest_descriptions.json")["records"]}
        old_descriptions = {r["id"] for r in kyuura_json(V0124, "data/sidecar/latest_descriptions.json")["records"]}
        self.assertEqual((len(descriptions), sorted(descriptions - old_descriptions)), (52, sorted(NEW_LDS)))
        checks = {r["id"] for r in kyuura_json(NOW, "data/sidecar/card_checks.json")["records"]}
        old_checks = {r["id"] for r in kyuura_json(V0124, "data/sidecar/card_checks.json")["records"]}
        self.assertEqual((len(checks), sorted(checks - old_checks)), (88, sorted(i for ids in NEW_CCS.values() for i in ids)))


# ---------------------------------------------------------------- 3 章以降: 登録・ふくらむ・［てだすけ］（処理）

import copy as _copy
import dataclasses
import pickle as _pickle

from kyuura_engine import (
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    current_form,
    powers_of,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import Poison
from tests.helpers import (
    FIGHTING,
    GRIMER,
    GUST,
    HITMONCHAN,
    JIGGLYPUFF,
    MACHOP,
    MUK,
    PSYCHIC,
    RATTATA,
    SABRINAS_ABRA,
    SABRINAS_ESP,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_virtual_attacks_transformation_v0_49 import audited, snapshot

W = WIGGLYTUFF
INFLATE_KEY, HELP_KEY = "ES1-027#0", "ES1-027@power0"
CLASSIC_DITTO, BROCKS_NINETALES, BROCKS_VULPIX = "PMCG3-042", "PMCG5-019", "PMCG5-018"
POLYGON = "PMCG6-066"  # ナツメのポリゴン（バリアアタック（無無）20。「次の相手の番、このカードがワザによって受けるダメージは「-10」される。」）
DROWZEE, ABRA = "PMCG1-045", "PMCG1-043"  # スリープ（さいみんじゅつ: ねむり）・ケーシィ（ねんりき 10）
HH1, HH2, IF1 = "UNRESOLVED_HELPING_HAND_WITHOUT_CONDITION", "UNRESOLVED_HELPING_HAND_CHOICE", "UNRESOLVED_INFLATE_NON_ATTACK_DAMAGE"
TK1 = "UNRESOLVED_TRANSFORM_REVERT_KNOCKOUT_TIMING"
ELEKID = "neo1-044"  # エレキッド（ベイビィ。［わんぱくパンチ］: 自分の番ごとに 1 回、コインで相手の対戦ポケモンに 20 の特殊能力のダメージ）
TURN = 5  # 先攻（プレイヤー 0）の 3 回目の番


def wig(**extra):
    return {"card": W, "evolved_from": JIGGLYPUFF, **extra}


def two_sides(mine, theirs, *, turn=TURN, current=0):
    sides = []
    for side in (mine, theirs):
        sides.append({"hand": [], "deck": [WATER] * 8, **side})
    return build_test_state(sides, turn_number=turn, current_player=current)


def helping_board(active, *, bench=None, opponent=None, hand=()):
    return two_sides({"active": active, "bench": bench if bench is not None else [wig()], "hand": list(hand)},
                     {"active": opponent or {"card": RATTATA}, "bench": [{"card": RATTATA}]})


def bench_pid(state, card=W, player=0):
    return next(p.pokemon_id for p in state.players[player].bench if state.cards[p.card].card_id == card)


def helping(state, *coins, pokemon=None, mode="derived"):
    pid = bench_pid(state) if pokemon is None else pokemon
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UsePokemonPower(0, pid, 0), preflight=mode)


def new_events(before, after, kind=None):
    return [dict(e) for e in after.log[len(before.log):] if kind is None or e["kind"] == kind]


def assert_stops(test, state, command, code, *coins):
    """どの先読みの方法でも ``code`` で拒否し、状態・乱数・ログが変わらない（使用済みの記録も変えない）。"""
    seeded = with_coin_results(state, *coins) if coins else state
    before = snapshot(seeded)
    for mode in PREFLIGHT_MODES:
        with test.subTest(mode=mode), test.assertRaises(UnsupportedError) as raised:
            apply_kernel(seeded, command, preflight=mode)
        test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(seeded), before)
    test.assertEqual(seeded.power_uses_this_turn, state.power_uses_this_turn)


class RegistrationTest(unittest.TestCase):
    """3 章・8 章: 登録・写しの組・採用の記録・研究の対応表。登録だけを除くと、カードの集合は基点の 1,360 枚にもどる。"""

    def test_entries_bind_the_latest_text(self):
        attack = E.DEFAULT_EFFECTS.attack_entry(W, 0)
        self.assertEqual((type(attack.effect), attack.effect.amount, attack.effect.on_heads, attack.effect.latest),
                         (E.DamageThenReduceDamageNextTurn, 10, False, E.INFLATE_LATEST_TEXT))
        self.assertEqual(E.INFLATE_LATEST_TEXT, "次の相手の番、このカードが受けるダメージは「-10」される。（ダメージ以外の効果はそのまま）")
        self.assertEqual((attack.name_ja, attack.text_ja, attack.play_text_ja, attack.source),
                         ("ふくらむ", "このカードが次の相手に受けるダメージは「-10」される。", E.INFLATE_LATEST_TEXT, "LD-ES1-027-ATK0"))
        self.assertTrue(attack.effect.non_attack_unresolved)
        power = E.DEFAULT_EFFECTS.power_entry(W, 0)
        self.assertIsInstance(power.effect, E.CureOneActiveConditionOnHeadsFromBench)
        self.assertEqual((power.name_ja, power.text_ja, power.play_text_ja, power.source),
                         ("てだすけ", E.HELPING_HAND_PRINTED_TEXT, E.HELPING_HAND_LATEST_TEXT, "LD-ES1-027-PWR0"))
        self.assertEqual(power.effect.texts(), (E.HELPING_HAND_LATEST_TEXT,))
        self.assertTrue(power.effect.once_per_turn)
        definition = load_card_pool().get(W)
        self.assertEqual((definition.hp, definition.evolves_from, definition.retreat_cost), (90, "プリン", 3))
        self.assertIsNone(E.DEFAULT_EFFECTS.attack_problem(W, definition.attacks[0], definition.attacks))
        self.assertIsNone(E.DEFAULT_EFFECTS.power_problem(W, definition.powers[0]))

    @needs_kyuura
    def test_latest_texts_are_the_kyuura_records(self):
        records = {r["id"]: r for r in kyuura_json(NOW, "data/sidecar/latest_descriptions.json")["records"]}
        attack, power = records["LD-ES1-027-ATK0"], records["LD-ES1-027-PWR0"]
        self.assertEqual(attack["latest_description"]["text_ja"], E.INFLATE_LATEST_TEXT)
        self.assertEqual(power["latest_description"]["text_ja"], E.HELPING_HAND_LATEST_TEXT)
        self.assertEqual((attack["latest_description"]["page"], attack["latest_description"]["pdf_page"]), ("226", 228))
        # 印刷の文面の写しは kyuura の値のまま（未読の字を「番」と補った値ではない）。画像の読みは「相手の■に」で、訂正の候補のまま
        self.assertEqual(attack["printed_text"]["text_ja"], E.DEFAULT_EFFECTS.attack_entry(W, 0).text_ja)
        self.assertIn("■", attack["printed_text"]["image_text_ja"])
        self.assertEqual(power["printed_text"]["text_ja"], E.HELPING_HAND_PRINTED_TEXT)

    def test_text_checks_are_bound_not_relaxed(self):
        definition = load_card_pool().get(W)
        attack = definition.attacks[0]
        self.assertEqual(E.DamageThenReduceDamageNextTurn(10, latest=E.INFLATE_LATEST_TEXT).check(attack), [])
        # 量・コイン・最新の説明の全文を結んだ組だけ（ほかの量、コインつき、別の最新の説明、最新の説明なしの印刷の文面では受け付けない）
        self.assertTrue(E.DamageThenReduceDamageNextTurn(20, latest=E.INFLATE_LATEST_TEXT).check(attack))
        self.assertTrue(E.DamageThenReduceDamageNextTurn(10, on_heads=True, latest=E.INFLATE_LATEST_TEXT).check(attack))
        self.assertTrue(E.DamageThenReduceDamageNextTurn(10, latest="次の相手の番、このカードが受けるダメージは「-10」される。").check(attack))
        self.assertTrue(E.DamageThenReduceDamageNextTurn(10).check(attack))
        # 句読点を落とした・未読の字を補った・最新の説明そのものの文面は、印刷の文面として受け付けない（一般的な句読点の除去や部分一致にしない）
        for text in ("このカードが次の相手に受けるダメージは「-10」される", "このカードが次の相手の番に受けるダメージは「-10」される。", E.INFLATE_LATEST_TEXT):
            with self.subTest(text=text):
                self.assertTrue(E.DamageThenReduceDamageNextTurn(10, latest=E.INFLATE_LATEST_TEXT).check(dataclasses.replace(attack, text_ja=text)))
        # 既存の登録（プリン neo4-085・ナツメのポリゴン・エアームド）は印刷の文面のまま、印はない
        for card, index in (("neo4-085", 0), (POLYGON, 1), ("neo1-058", 1)):
            entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
            self.assertIsNone(entry.effect.latest, card)
            self.assertFalse(entry.effect.non_attack_unresolved, card)
        power = definition.powers[0]
        self.assertEqual(E.CureOneActiveConditionOnHeadsFromBench().check(power), [])
        self.assertTrue(E.CureOneActiveConditionOnHeadsFromBench().check(dataclasses.replace(power, text_ja=E.HELPING_HAND_LATEST_TEXT)))

    def test_pool_and_removal(self):
        from kyuura_engine.cards import pool_from_extract
        from tests.release_catalog import cards_after, cards_before

        extract = read_extract()
        self.assertEqual(extract["pool_v0_125"], [W])
        self.assertEqual(cards_after(extract, "0.124") - cards_after(extract, "0.125"), frozenset({W}))  # v0.126: 後の版のカード（フラッシュ）を除いて比べる
        self.assertNotIn(W, cards_before(extract, "0.125"))
        trimmed = dict(extract, cards=[c for c in extract["cards"] if c["id"] != W], pool_v0_125=[])
        playable = pool_from_extract(trimmed, E.DEFAULT_EFFECTS).playable_ids
        playable = playable - cards_after(extract, "0.125")  # v0.126: 後の版で加えたカード（フラッシュ）を除いて比べる
        self.assertEqual(len(playable), 1360)
        self.assertEqual(set(load_card_pool().playable_ids) - set(playable) - cards_after(extract, "0.125"), {W})
        if (ROOT / ".git").exists():
            base_ids = {c["id"] for c in engine_json(BASE_ENGINE, "kyuura_engine/data/kyuura_cards.json")["cards"]}
            self.assertLessEqual(set(playable), base_ids)

    def test_adoption_records_and_links(self):
        record = cs.load_sources()["cards"][W]
        self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"]), ("kyuura_data", "adopted", NOW, "2026-10-31"))
        self.assertEqual(record["play_text"], {"attack/0": "LD-ES1-027-ATK0", "power/0": "LD-ES1-027-PWR0"})
        self.assertEqual(record["kyuura_records"], ["CC-ES1-027-P226", "CR-HELPING-HAND-USE", "CR-INFLATE-DAMAGE-STEP", "CR-INFLATE-LATEST", "LD-ES1-027-ATK0",
                                                    "LD-ES1-027-PWR0", "UQ-CARD-USE-WITHOUT-TARGET", "UQ-HELPING-HAND-CHOICE", "UQ-NON-ATTACK-DAMAGE-MODIFIERS"])
        [issue] = record["issues"]
        self.assertEqual((issue["fields"], issue["affects_behavior"]), (["pokemon.attacks[0].text.ja"], False))
        self.assertEqual(record["external_checks"], [])
        links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
        registered = links["latest_descriptions"]["registered"]
        self.assertEqual((registered["ES1-027/attack/0"], registered["ES1-027/power/0"]), ("LD-ES1-027-ATK0", "LD-ES1-027-PWR0"))
        self.assertEqual(links["card_checks"]["not_in_engine"]["ES1-027"], ["CC-ES1-027-P226"])  # エンジンの照合の記録ではない（v0.124 の ES2-032 と同じ）
        codes = {code: (links["stop_codes"][code]["kyuura_issue"], links["stop_codes"][code]["engine_rulings"][0]["ruling_id"]) for code in (HH1, HH2, IF1)}
        self.assertEqual(codes, {HH1: ("UQ-CARD-USE-WITHOUT-TARGET", "HH1"), HH2: ("UQ-HELPING-HAND-CHOICE", "HH2"), IF1: ("UQ-NON-ATTACK-DAMAGE-MODIFIERS", "IF1")})
        cases = {(c["kyuura_issue"], c["target"]): c["engine"] for c in links["kyuura_cases_without_engine_ruling"]["cases"] if c["card_id"] == W}
        self.assertEqual(cases, {("UQ-CARD-USE-WITHOUT-TARGET", "power/0"): {"stop_codes": [HH1]}, ("UQ-HELPING-HAND-CHOICE", "power/0"): {"stop_codes": [HH2]},
                                 ("UQ-NON-ATTACK-DAMAGE-MODIFIERS", "attack/0"): {"stop_codes": [IF1]}})

    @needs_kyuura
    def test_harmless_data_error_needs_the_latest_text_of_that_field(self):
        """3 章: CC- のデータの誤り（ふくらむの印刷の欠け）を「挙動に影響しない」とした採用は、その対象の処理に使う文面が、その欄を印刷の文面に持つ最新の説明のときだけ。"""
        sources = cs.load_sources()["cards"]
        self.assertFalse([p for p in rl.check(KYUURA, sources=sources) if W in p])
        for change, expected in ((lambda r: r["play_text"].__setitem__("attack/0", "kyuura_printed_text"), "最新の説明（LD-）ではない"),
                                 (lambda r: r["play_text"].__setitem__("attack/0", "LD-ES1-027-PWR0"), "対象が attack/0 ではない")):
            changed = _copy.deepcopy(sources)
            change(changed[W])
            with self.subTest(expected=expected):
                self.assertTrue(any(expected in p for p in rl.check(KYUURA, sources=changed) if W in p))
        # 挙動に影響する論点として書けば、採用（adopted）の記録にできない（check_card_sources が拒否する）
        changed = _copy.deepcopy(cs.load_sources())
        changed["cards"][W]["issues"][0]["affects_behavior"] = True
        self.assertTrue([p for p in cs.problems(changed) if W in p])


class InflateTest(unittest.TestCase):
    """4 章: ふくらむ。相手に 20 のあと、実際に使ったポケモン自身に、次の相手の番に受けるワザのダメージを p.321 の 8 段階で 10 減らす効果（v0.31 の ``DamageReduction``）。"""

    def board(self, opponent, *, mine=None, opponent_hand=()):
        return two_sides({"active": mine or wig(energy=[WATER] * 4), "bench": [{"card": RATTATA}]},
                         {"active": opponent, "bench": [{"card": RATTATA}], "hand": list(opponent_hand)})

    def test_damage_then_effect_on_the_user(self):
        state = self.board({"card": HITMONCHAN, "energy": [FIGHTING] * 3})
        done = audited(self, apply_kernel(state, UseAttack(0, 0)))
        self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [20])
        [added] = new_events(state, done, "persistent_effect_added")
        user = done.players[0].active
        self.assertEqual((added["persistent_effect"], added["pokemon_id"], added["source_card"], added["active_turn"], added["effect"]),
                         ("damage_reduction", user.pokemon_id, user.card, TURN + 1, INFLATE_KEY))
        [effect] = user.persistent_effects
        self.assertEqual((effect.amount, effect.non_attack_unresolved, effect.source_card), (10, True, user.card))
        self.assertFalse(done.players[1].active.persistent_effects)  # 相手に与える効果（なきごえ）ではない

    def test_after_weakness_and_resistance(self):
        """8 段階: 弱点（エビワラー・ワンリキーの闘。20 × 2 = 40）・抵抗力（ケーシィの超 10 - 30）のあとで -10。弱点・抵抗力のないコラッタの 20 は 10。0 以下なら 0（ダメージを受けなかった）。"""
        for card, energy, expected in ((HITMONCHAN, [FIGHTING] * 3, 30), (MACHOP, [FIGHTING], 30), (RATTATA, [WATER], 10), (ABRA, [PSYCHIC], 0)):
            with self.subTest(card=card):
                after = apply_kernel(self.board({"card": card, "energy": energy}), UseAttack(0, 0))  # ふくらむ。番が終わる
                hit = audited(self, apply_kernel(after, UseAttack(1, 0)))
                [received] = [e for e in new_events(after, hit, "damage") if e["player"] == 0]
                self.assertEqual(received["amount"], expected)
                self.assertIn((8, received["pokemon"], -10), [tuple(m) for m in received["modifiers"]])
                self.assertEqual(received["steps"][-1][0], "8 プクリン（damage_reduction）")  # 弱点（3）・抵抗力（4）より後

    def test_expires_and_lost_when_switched(self):
        after = apply_kernel(self.board({"card": HITMONCHAN, "energy": [FIGHTING] * 3}), UseAttack(0, 0))
        hit = apply_kernel(after, UseAttack(1, 0))
        self.assertFalse(hit.players[0].active.persistent_effects)  # 次の相手の番の終わりに期限で消える
        self.assertIn("expired", [e["reason"] for e in new_events(after, hit, "persistent_effect_removed")])
        # 相手の突風でベンチにもどると消える（p.322）。ベンチのあいだもどって来ない
        after = apply_kernel(self.board({"card": HITMONCHAN, "energy": [FIGHTING] * 3}, opponent_hand=[GUST]), UseAttack(0, 0))
        gust = next(u for u in after.players[1].hand if after.cards[u].card_id == GUST)
        played = apply_kernel(after, PlayTrainer(1, gust))
        switched = apply_kernel(played, ResolveDecision(1, played.decision.id, played.decision.options[:1]))
        moved = next(p for p in switched.players[0].bench if switched.cards[p.card].card_id == W)
        self.assertFalse(moved.persistent_effects)
        self.assertTrue([e for e in new_events(after, switched, "persistent_effect_removed") if e["persistent_effect"] == "damage_reduction"])

    def test_damage_other_effects_still_apply(self):
        """「（ダメージ以外の効果はそのまま）」: 相手のワザのこんらん（スリープのあやしいひかり。コインの「おもて」）は受ける。ダメージ 10 は 0。"""
        after = apply_kernel(self.board({"card": DROWZEE, "energy": [PSYCHIC] * 2}), UseAttack(0, 0))
        hit = audited(self, apply_kernel(with_coin_results(after, H), UseAttack(1, 1)))
        self.assertTrue(hit.players[0].active.conditions.confused)
        self.assertEqual([e["amount"] for e in new_events(after, hit, "damage") if e["player"] == 0], [0])

    def test_copied_inflate_goes_to_the_actual_user(self):
        """化石のメタモンが相手のプクリンを写して使ったふくらむ: 効果は実際に使ったメタモン自身に付き、供給元（相手のプクリン）には付かない。"""
        state = two_sides({"active": {"card": CLASSIC_DITTO, "energy": [WATER] * 4}, "bench": [{"card": RATTATA}]}, {"active": wig(), "bench": [{"card": RATTATA}]})
        ditto = state.players[0].active
        option = next(o for o in E.available_attacks(state, ditto) if o.card_id == W and o.attack_index == 0)
        done = audited(self, apply_kernel(state, UseAttack(0, 0, card=option.card)))
        [effect] = done.players[0].active.persistent_effects
        self.assertEqual((effect.source_card, effect.non_attack_unresolved), (ditto.card, True))
        self.assertFalse(done.players[1].active.persistent_effects)

    def test_power_damage_on_the_next_turn_stops(self):
        """IF1: 次の相手の番に特殊能力のダメージ（エレキッドの［わんぱくパンチ］）を受ける。当てはめるかが決まらないので、コインの前に止める（状態・乱数・ログを変えない）。"""
        after = apply_kernel(self.board({"card": ELEKID}), UseAttack(0, 0))
        command = UsePokemonPower(1, after.players[1].active.pokemon_id, 0)
        seeded = with_coin_results(after, H)
        before = snapshot(seeded)
        for mode in PREFLIGHT_MODES:
            with self.subTest(mode=mode), self.assertRaises(UnsupportedError) as raised:
                apply_kernel(seeded, command, preflight=mode)
            self.assertEqual(raised.exception.code, IF1)
        self.assertEqual(snapshot(seeded), before)
        # ふくらむでない「-10」（ナツメのポリゴンのバリアアタックは「ワザによって受けるダメージ」）では止めない（既存の扱いのまま）
        polygon = two_sides({"active": {"card": POLYGON, "energy": [WATER] * 2}, "bench": [{"card": RATTATA}]}, {"active": {"card": ELEKID}, "bench": [{"card": RATTATA}]})
        polygon = apply_kernel(polygon, UseAttack(0, 1))
        self.assertTrue(polygon.players[0].active.persistent_effects)
        punched = apply_kernel(with_coin_results(polygon, H), UsePokemonPower(1, polygon.players[1].active.pokemon_id, 0))
        self.assertEqual(punched.players[0].active.damage, 20)

    def test_format_and_copies(self):
        done = apply_kernel(self.board({"card": HITMONCHAN, "energy": [FIGHTING] * 3}), UseAttack(0, 0))
        self.assertEqual(serialization_problems(done), [])
        # v0.126: 形式 31（おもての山札）を加えた。印のある効果を表せないのは形式 1〜29（docs/flash-faceup-deck-v0.126.md 7 章）
        for version in (v for v in FORMAT_VERSIONS if v < 30):
            with self.subTest(version=version), self.assertRaises(ValueError):
                state_to_dict(done, format_version=version)
        [item] = state_to_dict(done, format_version=30)["players"][0]["active"]["persistent_effects"]
        self.assertEqual((item["effect"], item["amount"], item["non_attack_unresolved"], item["source_card_id"]), ("damage_reduction", 10, True, W))
        for copied in (done.clone(), _copy.deepcopy(done), _pickle.loads(_pickle.dumps(done))):
            self.assertEqual(state_to_dict(copied, format_version=30), state_to_dict(done, format_version=30))
        # 印のない効果（ほかの登録）は形式 29 でも書き出せる（v0.124 と同じ）
        polygon = two_sides({"active": {"card": POLYGON, "energy": [WATER] * 2}, "bench": [{"card": RATTATA}]}, {"active": {"card": RATTATA}, "bench": [{"card": RATTATA}]})
        polygon = apply_kernel(polygon, UseAttack(0, 1))
        self.assertNotIn("non_attack_unresolved", state_to_dict(polygon, format_version=29)["players"][0]["active"]["persistent_effects"][0])


class HelpingHandTest(unittest.TestCase):
    """5 章: ［てだすけ］。ベンチ限定・自分の番ごとに 1 回・特殊能力のコイン 1 枚・「おもて」で対戦ポケモンの状態を 1 つだけ回復。0 個は HH1、2 個は HH2 で宣言の前に止める。"""

    def test_one_condition_each_kind_heads_and_tails(self):
        specs = {"poison": {"poison": 10}, "sleep": {"sleep": True}, "paralysis": {"paralysis": TURN - 1}, "confusion": {"confusion": True}}
        for name, spec in specs.items():
            for coin in (H, T):
                with self.subTest(condition=name, coin=coin):
                    state = helping_board({"card": RATTATA, "damage": 10, **spec})
                    done = audited(self, helping(state, coin))
                    kinds = [e["kind"] for e in new_events(state, done)]
                    [flip] = new_events(state, done, "coin_flip")
                    self.assertEqual((flip["source"], flip["effect"], flip["player"], flip["count"]), ("power", HELP_KEY, 0, 1))
                    self.assertIn((bench_pid(state), 0), done.power_uses_this_turn)  # 場のポケモンごとの記録（いちばん上のカードの特殊能力）
                    active = done.players[0].active
                    if coin is H:
                        self.assertEqual(kinds, ["pokemon_power", "coin_flip", "special_conditions_removed"])
                        [removed] = new_events(state, done, "special_conditions_removed")
                        self.assertEqual((removed["conditions"], removed["reason"], removed["effect"], removed["pokemon_id"]), ((name,), "cured", HELP_KEY, active.pokemon_id))
                        self.assertEqual(active.conditions.names(), ())
                    else:
                        self.assertEqual(kinds, ["pokemon_power", "coin_flip"])
                        self.assertEqual(active.conditions.names(), (name,))
                    self.assertEqual(active.damage, 10)  # ダメージは変えない
                    with self.assertRaises(Exception) as raised:  # 同じ番の 2 回目は使えない（「うら」でも使ったことになる）
                        helping(done, H)
                    self.assertEqual(raised.exception.code, "POWER_ALREADY_USED")

    def test_cures_poison_with_multiplier_only(self):
        state = helping_board({"card": RATTATA})
        active = state.players[0].active
        active.conditions = dataclasses.replace(active.conditions, poison=Poison(10, multiplier=2))
        done = audited(self, helping(state, H))
        self.assertIsNone(done.players[0].active.conditions.poison)
        self.assertEqual(done.players[0].active.conditions.names(), ())

    def test_zero_and_two_conditions_stop_without_side_effects(self):
        state = helping_board({"card": RATTATA})
        assert_stops(self, state, UsePokemonPower(0, bench_pid(state), 0), HH1, H)
        for exclusive in ({"sleep": True}, {"paralysis": TURN - 1}, {"confusion": True}):
            with self.subTest(exclusive=exclusive):
                state = helping_board({"card": RATTATA, "poison": 10, **exclusive})
                assert_stops(self, state, UsePokemonPower(0, bench_pid(state), 0), HH2, T)

    def test_bench_only_and_per_individual(self):
        state = helping_board(wig(poison=10), bench=[{"card": RATTATA}])
        with self.assertRaises(Exception) as raised:
            apply_kernel(with_coin_results(state, H), UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        self.assertEqual(raised.exception.code, "POKEMON_NOT_ON_BENCH")
        # ベンチの 2 匹のプクリンは、それぞれ 1 回（場のポケモンごと）。1 匹目の「うら」のあと、2 匹目の「おもて」で回復
        state = helping_board({"card": RATTATA, "poison": 10}, bench=[wig(), wig()])
        first, second = (p.pokemon_id for p in state.players[0].bench)
        done = helping(state, T, pokemon=first)
        done = audited(self, helping(done, H, pokemon=second))
        self.assertEqual(done.players[0].active.conditions.names(), ())

    def test_markers_persistent_effects_and_attachments_stay(self):
        state = helping_board({"card": RATTATA, "poison": 10, "damage": 20, "markers": ["char"], "energy": [WATER, PSYCHIC]})
        before = state.players[0].active
        done = audited(self, helping(state, H))
        after = done.players[0].active
        self.assertEqual((after.damage, after.markers, after.persistent_effects, after.energy, after.trainers),
                         (before.damage, before.markers, before.persistent_effects, before.energy, before.trainers))

    def test_suppressed_by_chemical_gas(self):
        """かがくへんかガス（相手のバトル場のベトベトン）で特殊能力は使えない（共通の確かめ）。"""
        state = two_sides({"active": {"card": RATTATA, "poison": 10}, "bench": [wig()]}, {"active": {"card": MUK, "evolved_from": GRIMER}, "bench": [{"card": RATTATA}]})
        with self.assertRaises(Exception) as raised:
            helping(state, H)
        self.assertEqual(raised.exception.code, "POWER_SUPPRESSED")

    def test_power_coin_is_not_an_esp_target(self):
        """ナツメのESP（対戦ポケモンのナツメのケーシィについている）はワザの説明文のコインのやり直し。［てだすけ］のコインはやり直しの対象にならない（決定を出さない）。"""
        state = helping_board({"card": SABRINAS_ABRA, "poison": 10, "energy": [PSYCHIC], "trainers": [(SABRINAS_ESP, TURN)]})
        done = audited(self, helping(state, T))
        self.assertIsNone(done.decision)
        self.assertEqual([e["source"] for e in new_events(state, done, "coin_flip")], ["power"])

    def test_cure_that_restores_a_transform_form(self):
        """6 章: ねむりで［へんしん］の消えた化石のメタモンを回復すると、処理の終わりの共通の経路（``release_frozen_forms``）で姿がもどる。HP がのっているダメージ以下になる隣の場面は、
        既存の TK1 で止める（v0.124 の問いを維持）。"""
        state = two_sides({"active": {"card": CLASSIC_DITTO, "sleep": True}, "bench": [wig()]}, {"active": {"card": HITMONCHAN}, "bench": [{"card": RATTATA}]})
        self.assertEqual(current_form(state, state.players[0].active).card, state.players[0].active.card)
        done = audited(self, helping(state, H))
        self.assertEqual(done.cards[current_form(done, done.players[0].active).card].card_id, HITMONCHAN)
        state = two_sides({"active": {"card": CLASSIC_DITTO, "sleep": True, "damage": 40}, "bench": [wig()]}, {"active": {"card": RATTATA}, "bench": [{"card": RATTATA}]})
        assert_stops(self, state, UsePokemonPower(0, bench_pid(state), 0), TK1, H)

    def test_copies_and_serialization(self):
        """使用回数・コイン・回復は既存の状態とログで表す（形式 29 でも書き出せる。新しい決定はない）。"""
        done = helping(helping_board({"card": RATTATA, "poison": 10}), H)
        self.assertEqual(serialization_problems(done), [])
        self.assertEqual({**state_to_dict(done, format_version=29), "format_version": 30}, state_to_dict(done, format_version=30))
        for copied in (done.clone(), _copy.deepcopy(done), _pickle.loads(_pickle.dumps(done))):
            self.assertEqual(state_to_dict(copied, format_version=30), state_to_dict(done, format_version=30))


class CopiedHelpingHandTest(unittest.TestCase):
    """6 章: 写した・のせたカードの［てだすけ］。両メタモンはバトル場でだけ変身を保つので、ベンチで宣言する経路はない。タケシのキュウコンの「ばける」はベンチでも使え、のせたカードの
    特殊能力を持つ（2000.02.14 版の基準。v0.49）ので、ベンチで宣言できる（持ち主はキュウコン・供給元はのせたカード・番ごとに 1 回）。"""

    def test_ninetales_disguised_on_the_bench(self):
        state = two_sides({"active": {"card": RATTATA, "poison": 10}, "bench": [{"card": BROCKS_NINETALES, "evolved_from": BROCKS_VULPIX}], "hand": [W]},
                          {"active": {"card": RATTATA}, "bench": [{"card": RATTATA}]})
        ninetales = state.players[0].bench[0]
        shifted = apply_kernel(state, UsePokemonPower(0, ninetales.pokemon_id, 0))
        shifted = apply_kernel(shifted, ResolveDecision(0, shifted.decision.id, shifted.decision.options[:1]))
        holder = shifted.players[0].bench[0]
        self.assertEqual(shifted.cards[holder.disguise].card_id, W)
        slot = next(s for s in powers_of(shifted, holder) if s.key.card_id == W)
        self.assertEqual(slot.card, holder.disguise)
        done = audited(self, apply_kernel(with_coin_results(shifted, H), UsePokemonPower(0, holder.pokemon_id, 0, card=slot.card)))
        self.assertEqual(done.players[0].active.conditions.names(), ())
        self.assertIn((holder.pokemon_id, 0, holder.disguise), done.power_uses_this_turn)
        [flip] = new_events(shifted, done, "coin_flip")
        self.assertEqual((flip["player"], flip["pokemon_id"], flip["card"], flip["effect"]), (0, holder.pokemon_id, holder.card, HELP_KEY))  # 投げるのは持ち主のキュウコン
        with self.assertRaises(Exception) as raised:
            apply_kernel(with_coin_results(done, H), UsePokemonPower(0, holder.pokemon_id, 0, card=slot.card))
        self.assertEqual(raised.exception.code, "POWER_ALREADY_USED")

    def test_ditto_holds_but_cannot_declare(self):
        """バトル場の化石のメタモンは相手のプクリンの［てだすけ］を持つ（CR-TRANSFORM-COPIES-TOP-CARD）が、ベンチ限定の力をバトル場で宣言する経路はない。写した宣言する特殊能力は
        確かめた実装（``COPY_VERIFIED_DECLARED``）だけ使えるので、未対応で止める（この型を加えていない）。ベンチのメタモンは変身しないので持たない。"""
        state = two_sides({"active": {"card": CLASSIC_DITTO, "poison": 10}, "bench": [{"card": CLASSIC_DITTO}]}, {"active": wig(), "bench": [{"card": RATTATA}]})
        ditto = state.players[0].active
        slot = next(s for s in powers_of(state, ditto) if s.key.card_id == W)
        self.assertNotIsInstance(slot.effect, E.COPY_VERIFIED_DECLARED)
        with self.assertRaises(Exception) as raised:
            apply_kernel(with_coin_results(state, H), UsePokemonPower(0, ditto.pokemon_id, 0, card=slot.card))
        self.assertEqual(raised.exception.code, "UNSUPPORTED_TRANSFORM_COPIED_POWER")
        self.assertFalse([s for s in powers_of(state, state.players[0].bench[0]) if s.key.card_id == W])


class AuditTest(unittest.TestCase):
    """11 章: ログの監査（v125_problems）は、エンジンの登録を読まずに、ログから組み立てた場・特殊状態で［てだすけ］を確かめる。誤りを入れると見つけ、正しい経路を誤って見つけない。"""

    @classmethod
    def setUpClass(cls):
        from tools import existing_effect_games as games

        cls.done = games.play(("W125", "P109"), 90, keep_state=True)["state"]  # 開発用の seed（正式な対戦の seed 0〜3 とは別）

    def test_real_game_passes(self):
        self.assertTrue([e for e in self.done.log if e["kind"] == "special_conditions_removed" and e.get("effect") == HELP_KEY])
        self.assertEqual(log_problems(self.done), [])

    def test_tampered_logs_are_found(self):
        from types import MappingProxyType

        cured = next(e for e in self.done.log if e["kind"] == "special_conditions_removed" and e.get("effect") == HELP_KEY)
        other = "poison" if tuple(cured["conditions"]) != ("poison",) else "sleep"
        changes = {
            "回復した状態": lambda e: MappingProxyType(dict(e, conditions=(other,))) if e is cured else e,
            "回復した相手": lambda e: MappingProxyType(dict(e, pokemon_id=-1)) if e is cured else e,
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                bad = self.done.clone()
                bad.log = tuple(change(e) for e in self.done.log)
                self.assertTrue(any("てだすけ" in p for p in log_problems(bad)), name)
        bad = self.done.clone()  # 「おもて」のあとの回復を落とす
        bad.log = tuple(e for e in self.done.log if e is not cured)
        self.assertTrue(any("てだすけ" in p for p in log_problems(bad)))


if __name__ == "__main__":
    unittest.main()

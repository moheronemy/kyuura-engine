"""v0.124（docs/super-transform-dark-pulse-v0.124.md）: 写しの元・研究の基準の移行（kyuura 74b3ceb → b9e7cff。写しの外のメタモン ES2-032 の文面の 1 字の訂正）。

2 章: 移行だけの段。kyuura が同じカードの画像で確かめて直した ES2-032 の pokemon.powers[0].text.ja の「カ」→「力」（訂正の種類は転記の誤り ``transcription_error``）を写しの移行の段
v0.124 で受け付け、採用の記録・研究の対応表をそろえる。エンジンは画像を見ていない（kyuura の画像の照合を再利用しただけ）。この段ではカードを登録せず、処理も変えない。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import subprocess
import unittest

from kyuura_engine.cards import load_card_pool, read_extract
from scripts import check_card_sources as cs
from scripts import check_research_links as rl
from tests import helpers as HP
from tests.test_baby_rules_evolution_v0_114 import extract_module

ROOT = pathlib.Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
LINKS_PATH = ROOT / "kyuura_engine" / "data" / "research_links.json"
NOW, V0123 = "b9e7cff6d2b2c6b4539ec45e61bf453879adab3a", "74b3ceb883dd815495d13b9987433fb14b36e44d"
RESEARCH_LAST = "9731354f7e5c6bca08c88bbe98f9449ae96ea7a7"  # kyuura の研究の最後のコミット（b9e7cff と木が同じ）
ECB, V069, V097, V0114, V0121 = ("ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3", "73a169063463bbf7bcaa3137d70cbf9721d11534",
                                 "e519b99e2adcc6c2cd0998569ae5ee1101de6e89", "2fe0bc042ce187d191843819262f8036abbb343d")
BASE_ENGINE = "84bf94f013238472c34687533f8aec3018797cc9"  # この版の基点（main。木は v0.123 の最後 25552b8 と同じ）
V0124_FINAL = "e165fe0fb3de0e73129135f8cbaa34e2aae0eb64"  # v0.125: この版の最後のコミット（v0.125 で写しの元・研究の基準を 134a664 に上げたので、v0.124 の値はこのコミットで確かめる）
DITTO, GR_MEWTWO, CLASSIC_DITTO = "ES2-032", "PRN-041", "PMCG3-042"
FIX = "FIX-ES2-032-POWER0-TEXT-JA"
NEW_ISSUES = ("UQ-TRANSFORM-ENERGY-COLOR-LIST", "UQ-SUPER-TRANSFORM-TARGETS", "UQ-SUPER-TRANSFORM-SOURCE-CHANGES", "UQ-SUPER-TRANSFORM-COPIED-POWERS",
              "UQ-SUPER-TRANSFORM-SUPPRESSED-FORM", "UQ-SUPER-TRANSFORM-ENERGY-COLORS", "UQ-TRANSFORM-REVERT-KNOCKOUT-TIMING", "UQ-TRANSFORM-BABY-AND-BASIC",
              "UQ-DARK-PULSE-TIMING")
MIGRATION_TAG = "v0.124 で研究の基準を b9e7cff に上げて結んだ"


def needs_kyuura(test):
    return unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")(test)


def needs_history(test):
    return unittest.skipUnless((ROOT / ".git").exists(), "このリポジトリの git の履歴がない（取り出した木）")(test)


def kyuura_json(commit: str, path: str):
    return json.loads(subprocess.check_output(["git", "-C", str(KYUURA), "show", f"{commit}:{path}"]))


def engine_json(commit: str, path: str):
    return json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"]))


# ---------------------------------------------------------------- 2 章: 移行

class MigrationChainTest(unittest.TestCase):
    """2.1 節: 段 v0.124（74b3ceb → b9e7cff）。過去の段の値・採用の記録の移行は書き換えない。"""

    def test_chain(self):
        module = extract_module()
        # v0.125: 段 v0.125（b9e7cff → 134a664）を加え、v0.124 の段のあとは V0_124_KYUURA_COMMIT（b9e7cff）に固定した。今の写しの元は最後の段のあと
        # （docs/wigglytuff-helping-hand-v0.125.md 2 章。今の値は tests/test_wigglytuff_helping_hand_v0_125.py）
        self.assertEqual((module.V0_124_KYUURA_COMMIT, module.V0_123_KYUURA_COMMIT, module.V0_121_KYUURA_COMMIT), (NOW, V0123, V0121))
        self.assertEqual(module.migration_problems(), [])
        self.assertEqual([(s["id"], s["from"], s["to"]) for s in module.KYUURA_MIGRATIONS][:6],
                         [("v0.69", ECB, V069), ("v0.97", V069, V097), ("v0.114", V097, V0114), ("v0.121", V0114, V0121), ("v0.123", V0121, V0123),
                          ("v0.124", V0123, NOW)])
        self.assertEqual(module.KYUURA_MIGRATIONS[5]["document"], "docs/super-transform-dark-pulse-v0.124.md")
        extract = read_extract()
        self.assertEqual((extract["source"]["commit"], extract["previous_source"]["commit"]), (module.KYUURA_MIGRATIONS[-1]["to"], ECB))
        self.assertEqual(extract["source_migrations"][5]["corrections"], [FIX])
        # v0.123 の段のあとを写しの元の定数にもどすと、写しの元を上げたときに過去の段のあとまで変わる（連鎖が切れて止まる）
        steps = module.KYUURA_MIGRATIONS
        try:
            module.KYUURA_MIGRATIONS = (*steps[:4], {**steps[4], "to": module.KYUURA_COMMIT}, *steps[5:])
            self.assertTrue(any("その前の段のあと" in p for p in module.migration_problems()))
        finally:
            module.KYUURA_MIGRATIONS = steps

    def test_adoption_migrations_are_appended(self):
        sources = cs.load_sources()
        # v0.125: 7 段目（b9e7cff → 134a664）が加わった（今の値は tests/test_wigglytuff_helping_hand_v0_125.py）。v0.124 までの 6 段は書き換えない
        self.assertEqual([(m["from"], m["to"], m["on"]) for m in sources["data_migrations"]][:6],
                         [(ECB, V069, "2026-10-19"), (V069, V097, "2026-10-25"), (V097, V0114, "2026-10-28"), (V0114, V0121, "2026-10-30"),
                          (V0121, V0123, "2026-10-31"), (V0123, NOW, "2026-10-31")])
        self.assertEqual(sources["data_migrations"][5]["document"], "docs/super-transform-dark-pulse-v0.124.md")
        self.assertEqual(cs.data_migrations(sources, read_extract())[1], [])
        # 採用したときのデータのコミットが b9e7cff の記録は、この版で写しに加えたカード（pool_v0_124）だけ（移行の段では採用し直していない）
        self.assertEqual({card for card, record in sources["cards"].items() if record.get("kyuura_commit") == NOW}, set(read_extract().get("pool_v0_124", ())))

    def test_correction_in_the_extract(self):
        corrections = {c["id"]: c for c in read_extract()["kyuura_corrections"] if c["migration"] == "v0.124"}
        self.assertEqual(sorted(corrections), [FIX])
        c = corrections[FIX]
        self.assertEqual((c["card_id"], c["field"], c["basis"], c["kind"], c["image_check"], c["decided_on"]),
                         (DITTO, "pokemon.powers[0].text.ja", "card_image_check", "transcription_error", "IMG-ES2-032", "2026-10-31"))
        self.assertEqual((c["kyuura_saw_image"], c["engine_saw_image"], c["applied_in_source"], c["previous_source"]), (True, False, NOW, V0123))
        self.assertFalse({"record", "commit", "kyuura_record"} & set(c))  # CC-・LD- の照合の記録ではない（公式エラッタ・最新の説明とも混ぜない）
        # 前とあとの違いは「カ」→「力」の 1 字だけ（括弧・句読点を整形しない）
        before, after = c["before"], c["after"]
        self.assertEqual(len(before), len(after))
        diff = [(i, x, y) for i, (x, y) in enumerate(zip(before, after)) if x != y]
        self.assertEqual([(x, y) for _, x, y in diff], [("カ", "力")])
        self.assertIn("この「すごいへんしん」の力は使えず", after)
        self.assertIn("(ただし「進化・退化」はできず", after)  # 半角の括弧のまま

    @needs_history
    def test_extract_is_unchanged_for_the_base_cards(self):
        """基点の写しの 1,358 枚（と参照のカード）は同じ値。変わったのは写しの元の記録と、移行の段・訂正の一覧だけ。"""
        before = engine_json(BASE_ENGINE, "kyuura_engine/data/kyuura_cards.json")
        now = read_extract()
        old = {card["id"]: card for card in before["cards"]}
        new = {card["id"]: card for card in now["cards"]}
        self.assertLessEqual(set(old), set(new))
        self.assertEqual({card for card in old if old[card] != new[card]}, set())
        self.assertNotIn(DITTO, old)

    @needs_kyuura
    def test_kyuura_difference_is_one_character(self):
        """74b3ceb → b9e7cff の data/cards.json 全 1,377 件: 値が変わったのは未登録の ES2-032 の pokemon・notes・corrections だけ。pokemon の中では特殊能力の文面の 1 字だけ。"""
        old, new = (kyuura_json(commit, "data/cards.json") for commit in (V0123, NOW))
        self.assertEqual({k: v for k, v in old.items() if k != "cards"}, {k: v for k, v in new.items() if k != "cards"})
        self.assertEqual([c["id"] for c in old["cards"]], [c["id"] for c in new["cards"]])
        self.assertEqual(len(new["cards"]), 1377)
        before = {c["id"]: c for c in old["cards"]}
        changed = {c["id"]: {k for k in set(c) | set(before[c["id"]]) if c.get(k) != before[c["id"]].get(k)} for c in new["cards"] if c != before[c["id"]]}
        self.assertEqual(changed, {DITTO: {"pokemon", "notes", "corrections"}})
        after = {c["id"]: c for c in new["cards"]}
        module = extract_module()
        used = [f for f in module.FIELDS_USED_BY_ENGINE if "[" not in f and module.field_or_absent(before[DITTO], f) != module.field_or_absent(after[DITTO], f)]
        self.assertEqual(used, ["pokemon.powers"])
        self.assertEqual({k: v for k, v in before[DITTO]["pokemon"].items() if k != "powers"}, {k: v for k, v in after[DITTO]["pokemon"].items() if k != "powers"})
        self.assertEqual(before[GR_MEWTWO], after[GR_MEWTWO])  # GR団のミュウツーの値は同じ（公式大会の補足の文は play_scope を変えていない）
        self.assertEqual(after[GR_MEWTWO].get("play_scope"), "standard")


class SameStepCardCheckTest(unittest.TestCase):
    """2.2 節: 同じ段で kyuura が作った照合の記録（CC-ES2-032-P239）が、訂正のあとの値で同じ欄を照らしているときの受け付け。画像の照合を CC- の代わりにしたことにはしない。"""

    @needs_kyuura
    def test_ledger_and_image_checks(self):
        module = extract_module()
        source = module.read_kyuura_cards(KYUURA)
        previous = json.loads(module._show(KYUURA, module.PREVIOUS_KYUURA_COMMIT, module.KYUURA_PATH).decode("utf-8"))
        pool = module.all_pool_cards() + module.REFERENCE_ONLY
        self.assertEqual(module.kyuura_correction_problems(KYUURA, source, previous, pool), [])
        original = list(module.KYUURA_CORRECTIONS)
        index = next(i for i, c in enumerate(original) if c["id"] == FIX)

        def problems_with(**changes):
            module.KYUURA_CORRECTIONS[:] = [*original[:index], {**original[index], **changes}, *original[index + 1:]]
            try:
                return module.kyuura_correction_problems(KYUURA, source, previous, pool)
            finally:
                module.KYUURA_CORRECTIONS[:] = original

        # 種類を生成の値の誤りに書きかえると台帳と合わない。画像の照合の記録・画像が違えば受け付けない
        self.assertTrue(any("台帳の kind" in p for p in problems_with(kind="generated_value_error")))
        self.assertTrue(any("画像の照合の記録" in p for p in problems_with(image_check="IMG-PRN-041")))
        self.assertTrue(any("evidence" in p for p in problems_with(evidence=[dict(original[index]["evidence"][0], image_sha256="0" * 64)])))
        # 段が違えば受け付けない（v0.123 の段の訂正にしない）
        self.assertTrue(any("移行の段 v0.123" in p for p in problems_with(migration="v0.123")))
        # あとの値を前の値にすると、同じ段の照合の記録の値とも違う（照合の記録を画像の確認の代わりにしない確かめが、もう一度はたらく）
        self.assertTrue(any("CC-" in p for p in problems_with(after=original[index]["before"])))


class AdoptionRecordTest(unittest.TestCase):
    """2.3 節: 採用の記録。登録済みのカードの kyuura_records に、新しい裁定・論点の id を加えた。採用したときのコミット・日付は書き換えない。"""

    def test_records_added_by_the_research_commit(self):
        cards = cs.load_sources()["cards"]
        for card_id, added in HP.V0_124_KYUURA_RECORDS_ADDED.items():
            self.assertLessEqual(set(added), set(cards[card_id]["kyuura_records"]), card_id)
            self.assertNotEqual(cards[card_id]["kyuura_commit"], NOW, card_id)
        self.assertEqual(len(HP.V0_124_KYUURA_RECORDS_ADDED), 21)
        self.assertEqual(len(HP.V0_124_KYUURA_RECORDS_ADDED[CLASSIC_DITTO]), 12)


class ResearchLinksTest(unittest.TestCase):
    """2.4 節: 研究の対応表。論点 79 → 88。研究の論点の数を停止コード・未解決の数にそろえない。"""

    @classmethod
    def setUpClass(cls):
        cls.links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))

    def test_commits_and_counts(self):
        # v0.125: 研究の基準を 134a664 に上げた（今の値は tests/test_wigglytuff_helping_hand_v0_125.py・tests/test_catalog_contract.py）。v0.124 の値は、その版の最後のコミットの対応表で確かめる
        if not (ROOT / ".git").exists():
            self.skipTest("このリポジトリの git の履歴がない（取り出した木）")
        links = engine_json(V0124_FINAL, "kyuura_engine/data/research_links.json")
        self.assertEqual((links["research_commit"], links["card_data_commit"], links["research_branch"]), (NOW, NOW, "main"))
        self.assertEqual(links["counts"]["kyuura_issues"], 88)
        # すごいへんしんの最新の説明は、登録するまで「登録のない kyuura の最新の説明」（v0.123 までは空。v0.124 の最後のコミットでは登録した）
        self.assertEqual(links["latest_descriptions"]["kyuura_records_not_registered"], [])
        self.assertNotIn("LD-ES2-032-PWR0", self.links["latest_descriptions"]["kyuura_records_not_registered"])
        self.assertIn(DITTO, load_card_pool().playable_ids)

    def test_new_cases_cover_the_new_issues(self):
        added = [c for c in self.links["kyuura_cases_without_engine_ruling"]["cases"] if MIGRATION_TAG in c.get("note", "")]
        self.assertEqual({c["kyuura_issue"] for c in added}, set(NEW_ISSUES))
        self.assertEqual(len(added), 31)

    def test_energy_registration_counts_as_card_target(self):
        from kyuura_engine.effects import DEFAULT_EFFECTS

        self.assertIn("card", rl._registered_targets(DEFAULT_EFFECTS, "PMCG1-096"))  # 無色2個エネルギー（特殊エネルギーの登録）
        self.assertIn("card", rl._registered_targets(DEFAULT_EFFECTS, "PMCG4-065"))  # レインボーエネルギー
        # 登録していないカード（v0.133 で対象のカードはすべて登録したので、対象外の PR1-038（catalog の special_rule・excluded）で確かめる）
        self.assertEqual(rl._registered_targets(DEFAULT_EFFECTS, "PR1-038"), set())

    @needs_kyuura
    def test_links_agree_with_kyuura(self):
        self.assertEqual(rl.check(KYUURA), [])

    @needs_kyuura
    def test_research_commit_tree_is_the_research_branch(self):
        trees = [subprocess.check_output(["git", "-C", str(KYUURA), "rev-parse", f"{c}^{{tree}}"]).strip() for c in (NOW, RESEARCH_LAST)]
        self.assertEqual(trees[0], trees[1])
        rulings = kyuura_json(NOW, "data/sidecar/rulings.json")
        statuses = {}
        for ruling in rulings["rulings"]:
            statuses[ruling["status"]] = statuses.get(ruling["status"], 0) + 1
        self.assertEqual((len(rulings["rulings"]), statuses.get("CONFIRMED"), statuses.get("SUPPORTED")), (337, 237, 100))
        self.assertEqual(len(rulings["issues"]), 88)
        self.assertEqual(len(rulings["rule_clauses"]), 41)


# ---------------------------------------------------------------- 3 章以降: 変身の共通ルール・すごいへんしん・わるいはどう（処理）

import copy as _copy
import pickle as _pickle

from kyuura_engine import (
    EndTurn,
    EvolvePokemon,
    IllegalActionError,
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
from kyuura_engine.resolution.programs import SCOPE_OWN_BENCH, counted_pokemon
from tests.helpers import (
    CHANSEY,
    CHARMANDER,
    CHARMELEON,
    FIRE,
    GRIMER,
    GUST,
    LAPRAS,
    MUK,
    PSYCHIC,
    RATTATA,
    SNORLAX,
    WATER,
    H,
    T,
    apply_kernel,
    with_coin_results,
)
from tests.log_audit import serialization_problems
from tests.test_virtual_attacks_transformation_v0_49 import (
    board,
    card_of,
    mon,
    snapshot,
)

W, R, P = WATER, FIRE, PSYCHIC
SNEASEL = "neo1-056"  # ニューラ（neo1。たね・悪タイプ。名前に「わるい」はつかない。ふくろだたき（悪悪）20）
DARK_ENERGY = "neo1-094"  # 悪エネルギー（特殊エネルギー。「悪」を 1 個出す）
DARK_RAPIDASH, PONYTA = "PMCG4-014", "PMCG4-013"  # わるいギャロップ（ポニータから進化。うしろげり（無無）20）
BABY = "NIP1X-002"  # ブビィ（ベイビィポケモン）
BUMPY_GYM = "neo4-110"
TC1, TK1, BX2 = "UNRESOLVED_TRANSFORM_ENERGY_COLOR_LIST", "UNRESOLVED_TRANSFORM_REVERT_KNOCKOUT_TIMING", "UNRESOLVED_TRANSFORM_BABY_AND_BASIC"
SV1, SV2, SV4 = "UNRESOLVED_SUPER_TRANSFORM_TARGET", "UNRESOLVED_SUPER_TRANSFORM_SOURCE_CHANGE", "UNRESOLVED_SUPER_TRANSFORM_SUPPRESSED_FORM"
DP1, DF1 = "UNRESOLVED_DARK_PULSE_TIMING", "UNRESOLVED_SELF_EXCLUDING_POWER_COPIES"


def stops(test, state, command, code):
    before = snapshot(state)
    for mode in PREFLIGHT_MODES:
        with test.subTest(mode=mode), test.assertRaises(UnsupportedError) as raised:
            apply_kernel(state, command, preflight=mode)
        test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)  # 止めたときに状態・乱数・ログを変えない


def super_transform(state, target_pid, *, player=0):
    """自分のバトル場の［すごいへんしん］を「おもて」で使い、``target_pid`` を選ぶ。"""
    ditto = state.players[player].active
    state = apply_kernel(with_coin_results(state, H), UsePokemonPower(player, ditto.pokemon_id, 0, card=ditto.card))
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, (target_pid,)))


class CopiedPowerTest(unittest.TestCase):
    """3.1 節: 変身したポケモンは、変身の対象のいちばん上のカードの特殊能力も持つ（CR-TRANSFORM-COPIES-TOP-CARD）。持つのは変身したポケモンで、相手の個体の状態を使わない。"""

    def test_copied_continuous_power_works_for_the_holder(self):
        state = board(mon(CLASSIC_DITTO, (W,)), mon(SNORLAX, (W,)))
        ditto, snorlax = state.players[0].active, state.players[1].active
        names = [(s.power.name_ja, s.card) for s in powers_of(state, ditto)]
        self.assertEqual(names, [("へんしん", ditto.card), ("めんえき", snorlax.card)])  # 自分の力が先。写した力の供給元は相手のカード
        self.assertEqual(E.copied_form_problems(state, 0, ditto), [])  # v0.123 までは TF1
        self.assertIsNotNone(E.status_immunity(state, 0, ditto))  # ［めんえき］はメタモン自身にはたらく
        self.assertEqual(E.form_problems(state), [])

    def test_two_transform_powers(self):
        """化石のメタモンどうしは、写した［へんしん］が同じ姿を指すので止めない（v0.49 からの読み方のまま）。［すごいへんしん］で変身していない化石のメタモンを選ぶと、変身する力を
        2 つ持つことになるので SV3（UQ-SUPER-TRANSFORM-COPIED-POWERS）。"""
        state = board(mon(CLASSIC_DITTO, (W,)), mon(CLASSIC_DITTO, (W,)))
        self.assertEqual(E.copied_form_problems(state, 0, state.players[0].active), [])
        sup = board(mon(DITTO_SUPER, (W,)), mon(LAPRAS, (W,)), bench=(mon(CLASSIC_DITTO),))
        ditto = sup.players[0].active
        heads = apply_kernel(with_coin_results(sup, H), UsePokemonPower(0, ditto.pokemon_id, 0))
        stops(self, heads, ResolveDecision(0, heads.decision.id, (sup.players[0].bench[0].pokemon_id,)), "UNRESOLVED_SUPER_TRANSFORM_COPIED_POWER")

    def test_entry_power_is_held_but_not_fired(self):
        """場に出たときの特殊能力を写しても、変身は新しく場に出たことではない（CR-TRANSFORM-NOT-NEWLY-PLAYED）。決定を出さず、止めない。"""
        state = board(mon(CLASSIC_DITTO, (W,)), mon("PF2-002"))
        ditto = state.players[0].active
        self.assertIn("PF2-002", {s.key.card_id for s in powers_of(state, ditto)})
        self.assertEqual(E.copied_form_problems(state, 0, ditto), [])
        self.assertIsNone(state.decision)


class NameAndKindTest(unittest.TestCase):
    """3.3 節: 名前と種類は両方（CR-TRANSFORM-NAME-AND-KIND）。1 匹を 2 匹と数えない。"""

    def test_names_both_and_counted_once(self):
        state = board(mon(CLASSIC_DITTO, (W,)), mon(LAPRAS, (W,)), bench=(RATTATA,))
        ditto = state.players[0].active
        self.assertEqual(E.field_names(state, ditto), ("ラプラス", "メタモン"))
        self.assertEqual(E.form_def(state, ditto).name_ja, "ラプラス")  # 表示の名前は今の姿
        self.assertEqual(len(counted_pokemon(state, 0, "own_in_play", ("ラプラス", "メタモン"))), 1)
        self.assertTrue(E.field_name_matches(state, ditto, ("メタモン",)))

    def test_basic_and_evolved(self):
        state = board(mon(CLASSIC_DITTO, (W,)), mon(CHARMELEON, (R,), evolved_from=CHARMANDER))
        ditto = state.players[0].active
        self.assertEqual(E.field_kinds(state, ditto), frozenset({E.FIELD_EVOLVED, E.FIELD_BASIC}))
        self.assertTrue(E.is_evolution_in_play(state, ditto))
        self.assertIs(E.field_is_basic_in_text(state, ditto, E.TEXT_PRE_NEO), True)
        self.assertEqual(E.field_stage(state, ditto), E.FIELD_EVOLVED)  # 今の姿の段階（表示）は 1 つ

    def test_baby_rule_applies_and_baby_and_basic_split_stops(self):
        """ベイビィに変身したメタモンにはベイビィのルールが当たる（v0.123 までは BX1 で止めた）。ベイビィとたねで結果が分かれる効果は BX2。"""
        state = board(mon(BABY), mon(CLASSIC_DITTO, (W,)), current=1)
        ditto = state.players[1].active
        self.assertTrue(E.is_baby_in_play(state, ditto))
        self.assertTrue(E.baby_rule_applies(state, 0))
        self.assertEqual(E.field_kinds(state, ditto), frozenset({E.FIELD_BABY, E.FIELD_BASIC}))
        self.assertEqual(E.transform_baby_question(state, ditto).code, BX2)


class FrozenFormTest(unittest.TestCase):
    """3.5 節: 処理のあいだ変身の状態を変えない（CR-TRANSFORM-FROZEN-DURING-ACTION）。固定するのは姿だけ。"""

    def test_freeze_and_release(self):
        state = board(mon(CLASSIC_DITTO, (W,)), mon(LAPRAS, (W,)), opponent_bench=(CHARMANDER,))
        ditto = state.players[0].active
        lapras = state.players[1].active
        E.freeze_forms(state)
        E._switch_active_with_bench(state, 1, state.players[1].bench[0].pokemon_id)
        self.assertEqual(current_form(state, ditto).card, lapras.card)  # 途中の入れ替えでも姿は変わらない（RX1 の中心）
        ditto.damage = 10  # ダメージは固定しない
        self.assertEqual(ditto.damage, 10)
        E.release_frozen_forms(state)
        self.assertEqual(state.cards[current_form(state, ditto).card].card_id, CHARMANDER)

    def test_release_that_changes_knockout_stops(self):
        """解除で姿が変わり、HP がのっているダメージ以下になるなら TK1（v0.123 までの MH1 の場面のうち、変身の姿が変わるもの）。安全な答えのある突風は使え、その答えだけを止める。
        どの答えも止まるなら、使う前に止める（トレーナーの答えのない決定を残さない）。"""
        state = board(mon(CLASSIC_DITTO, (W,), damage=60), mon(LAPRAS, (W,)), opponent_bench=(CHARMANDER, CHANSEY), hand=(GUST,))
        played = apply_kernel(state, PlayTrainer(0, card_of(state, 0, GUST)))
        self.assertEqual(played.frozen_forms[0].kind, E.FORM_TRANSFORM)  # 決定を待つあいだ固定している
        charmander, chansey = played.players[1].bench
        stops(self, played, ResolveDecision(0, played.decision.id, (charmander.pokemon_id,)), TK1)
        done = apply_kernel(played, ResolveDecision(0, played.decision.id, (chansey.pokemon_id,)))
        self.assertEqual((done.frozen_forms, done.cards[current_form(done, done.players[0].active).card].card_id), ((), CHANSEY))
        only = board(mon(CLASSIC_DITTO, (W,), damage=60), mon(LAPRAS, (W,)), opponent_bench=(CHARMANDER,), hand=(GUST,))
        stops(self, only, PlayTrainer(0, card_of(only, 0, GUST)), TK1)


class ClassicColorTest(unittest.TestCase):
    """3.7 節: 化石のメタモンの 6 色・8 色（UQ-TRANSFORM-ENERGY-COLOR-LIST）。読みで払えるかが変わるときだけ止める。"""

    def test_dark_symbol_with_basic_energy_stops(self):
        state = board(mon(CLASSIC_DITTO, (W, W)), mon(SNEASEL, (DARK_ENERGY,)))
        stops(self, state, UseAttack(0, 1, card=state.players[1].active.card), TC1)

    def test_payable_in_both_readings(self):
        state = board(mon(CLASSIC_DITTO, (DARK_ENERGY, DARK_ENERGY)), mon(SNEASEL, (DARK_ENERGY,)))
        after = apply_kernel(with_coin_results(state, H, H, T), UseAttack(0, 1, card=state.players[1].active.card))
        self.assertTrue([e for e in after.log[len(state.log):] if e["kind"] == "damage"])  # 悪エネルギーは 6 色の読みでも「悪」を出すので、止めずに払う


class SuperTransformTest(unittest.TestCase):
    """5 章: ［すごいへんしん］。"""

    def state(self, **extra):
        return board(mon(DITTO_SUPER, (W, W)), mon(LAPRAS, (W,)), bench=(RATTATA,), opponent_bench=(CHARMANDER,), **extra)

    def test_heads_from_either_side_and_tails(self):
        state = self.state()
        ditto = state.players[0].active
        lapras, rattata = state.players[1].active, state.players[0].bench[0]
        mine = super_transform(state, rattata.pokemon_id)
        self.assertEqual(state.cards[current_form(mine, mine.players[0].active).card].card_id, RATTATA)
        theirs = super_transform(state, lapras.pokemon_id)
        form = current_form(theirs, theirs.players[0].active)
        self.assertEqual((form.kind, form.defender), (E.FORM_SUPER_TRANSFORM, lapras.pokemon_id))
        # 「うら」なら変身していなくても何も起こらず、使ったことになる（同じ番にもう一度は使えない）
        tails = apply_kernel(with_coin_results(state, T), UsePokemonPower(0, ditto.pokemon_id, 0))
        self.assertIsNone(tails.decision)
        with self.assertRaises(IllegalActionError) as raised:
            apply_kernel(with_coin_results(tails, H), UsePokemonPower(0, ditto.pokemon_id, 0))
        self.assertEqual(raised.exception.code, "POWER_ALREADY_USED")

    def test_keeps_power_next_turn_and_tails_reverts(self):
        state = self.state()
        lapras = state.players[1].active
        mine = super_transform(state, lapras.pokemon_id)
        ditto = mine.players[0].active
        own = [s for s in powers_of(mine, ditto) if s.card == ditto.card]
        self.assertEqual([s.power.name_ja for s in own], ["すごいへんしん"])  # 写した力が自分の力を上書きしない
        later = apply_kernel(apply_kernel(mine, EndTurn(0)), EndTurn(1))  # 次の自分の番
        ditto = later.players[0].active
        self.assertEqual(current_form(later, ditto).kind, E.FORM_SUPER_TRANSFORM)
        reverted = apply_kernel(with_coin_results(later, T), UsePokemonPower(0, ditto.pokemon_id, 0, card=ditto.card))
        self.assertEqual(current_form(reverted, reverted.players[0].active).kind, E.FORM_PRINTED)
        self.assertEqual([e["reason"] for e in reverted.log if e["kind"] == "super_transform_reverted"], ["tails"])

    def test_source_moves_and_leaves(self):
        state = self.state()
        lapras = state.players[1].active
        mine = super_transform(state, lapras.pokemon_id)
        E._switch_active_with_bench(mine, 1, mine.players[1].bench[0].pokemon_id)  # 変身のもとがベンチに動く（場をはなれない）
        E.settle_super_transforms(mine)
        self.assertEqual(current_form(mine, mine.players[0].active).defender, lapras.pokemon_id)
        # 自分がバトル場をはなれたらもどる
        moved = _copy.deepcopy(mine)
        E._switch_active_with_bench(moved, 0, moved.players[0].bench[0].pokemon_id)
        E.settle_super_transforms(moved)
        self.assertIsNone(moved.players[0].bench[0].super_transform)

    def test_targets_that_stop(self):
        state = self.state()
        ditto = state.players[0].active
        heads = apply_kernel(with_coin_results(state, H), UsePokemonPower(0, ditto.pokemon_id, 0))
        self.assertEqual(tuple(heads.decision.context_value("unresolved_choices")), (ditto.pokemon_id,))  # 自分自身は選べるが選ぶと止める
        self.assertEqual(heads.decision.context_value("unresolved_code"), SV1)

    def test_source_evolution_stops(self):
        """変身のもと（自分のベンチのヒトカゲ）を進化させると、選んだときのカードと違う姿になるので SV2（そのコマンドを受け付けない）。"""
        state = board(mon(DITTO_SUPER, (W,)), mon(LAPRAS, (W,)), bench=(CHARMANDER,), hand=(CHARMELEON,))
        charmander = state.players[0].bench[0]
        mine = super_transform(state, charmander.pokemon_id)
        self.assertEqual(E.copied_form_problems(mine, 0, mine.players[0].active), [])
        stops(self, mine, EvolvePokemon(0, card_of(mine, 0, CHARMELEON), charmander.pokemon_id), SV2)

    def test_knocking_out_the_source_with_its_attack_is_tk1(self):
        """写したワザで変身のもと（相手の対戦ポケモン）をきぜつさせ、もどって HP40 がのっているダメージ以下になる（kyuura の UQ-TRANSFORM-REVERT-KNOCKOUT-TIMING の ES2-032 の事例）。
        2 匹のきぜつが同時かは決まらないので TK1（v0.48 の MH1 とは別のコード）。ダメージが 40 より少なければ、もどるだけで止めない。"""
        state = board(mon(DITTO_SUPER, (W, W), damage=30), mon(LAPRAS, (W,), damage=70), bench=(RATTATA,), opponent_bench=(RATTATA,))
        mine = super_transform(state, state.players[1].active.pokemon_id)
        mine.players[0].active.damage = 40  # 盤面を直接作る（ラプラスの姿の HP80 のあいだに受けたダメージ）
        stops(self, mine, UseAttack(0, 0, card=current_form(mine, mine.players[0].active).card), TK1)
        light = board(mon(DITTO_SUPER, (W, W), damage=30), mon(LAPRAS, (W,), damage=70), bench=(RATTATA,), opponent_bench=(RATTATA,))
        mine = super_transform(light, light.players[1].active.pokemon_id)
        done = apply_kernel(mine, UseAttack(0, 0, card=current_form(mine, mine.players[0].active).card))
        self.assertEqual(current_form(done, done.players[0].active).kind, E.FORM_PRINTED)  # もとがきぜつしたのでもどる（記録は次の区切りでログを書いて消す）
        self.assertEqual(E.super_transform_reason(done, done.players[0].active), "source_left")
        settled = done.clone()
        E.settle_super_transforms(settled)  # 決定（サイドを取る・バトル場に出す）のない区切りで、コマンドの終わりに消す処理
        self.assertEqual([e["reason"] for e in settled.log if e["kind"] == "super_transform_reverted"], ["source_left"])

    def test_cannot_evolve_while_transformed(self):
        state = board(mon(DITTO_SUPER, (R,)), mon(CHARMANDER, (R,)), hand=(CHARMELEON,))
        mine = super_transform(state, state.players[1].active.pokemon_id)
        with self.assertRaises(IllegalActionError) as raised:
            apply_kernel(mine, EvolvePokemon(0, card_of(mine, 0, CHARMELEON), mine.players[0].active.pokemon_id))
        self.assertEqual(raised.exception.code, "EVOLUTION_PREVENTED")

    def test_super_pays_dark_with_basic_energy(self):
        """変身しているときは悪・鋼をふくむ 8 色で払える（CR-SUPER-TRANSFORM-ENERGY-PAYMENT）。化石のメタモンの TC1 とは別。"""
        state = board(mon(DITTO_SUPER, (W, W)), mon(SNEASEL, (DARK_ENERGY,)))
        mine = super_transform(state, state.players[1].active.pokemon_id)
        ditto = mine.players[0].active
        self.assertIsNone(E.attack_cost_problem(mine, ditto, E.attack_of(mine, E.AttackKey(SNEASEL, 1))))
        self.assertTrue(E.attack_cost_payable(mine, ditto, E.attack_of(mine, E.AttackKey(SNEASEL, 1))))

    def test_chemical_gas_stops(self):
        """変身しているメタモンの［すごいへんしん］がかがくへんかガスで消える状態（相手がベトベターをベトベトンに進化させる）は SV4 で受け付けない（姿のままか、もどるかを決めない）。"""
        state = board(mon(DITTO_SUPER, (W,)), mon(LAPRAS, (W,)), opponent_bench=(GRIMER,), opponent_hand=(MUK,))
        mine = super_transform(state, state.players[1].active.pokemon_id)
        theirs = apply_kernel(mine, EndTurn(0))
        grimer = theirs.players[1].bench[0]
        stops(self, theirs, EvolvePokemon(1, card_of(theirs, 1, MUK), grimer.pokemon_id), SV4)

    def test_state_survives_copy_pickle_and_export(self):
        state = self.state()
        mine = super_transform(state, state.players[1].active.pokemon_id)
        for copied in (mine.clone(), _copy.deepcopy(mine), _pickle.loads(_pickle.dumps(mine))):
            self.assertEqual(copied.players[0].active.super_transform, mine.players[0].active.super_transform)
        data = state_to_dict(mine, format_version=29)
        self.assertEqual(data["players"][0]["active"]["super_transform"]["source"], state.players[1].active.pokemon_id)
        with self.assertRaises(ValueError):
            state_to_dict(mine, format_version=28)
        self.assertEqual(serialization_problems(mine), [])


class DarkCostumeTest(unittest.TestCase):
    """5 章（わるいぞうふく）: 自分のベンチの「わるい」ポケモンの数ぶんコイン（CR-DARK-COSTUME-COINS・CR-DARK-POKEMON-CATEGORY）。"""

    def test_counts_only_dark_named_own_bench(self):
        dark = mon(DARK_RAPIDASH, evolved_from=PONYTA)
        state = board(mon(GR_MEWTWO, (P, P)), mon(LAPRAS, (W,)), bench=(dark, mon(SNEASEL)), opponent_bench=(dark,))
        self.assertEqual(len(counted_pokemon(state, 0, SCOPE_OWN_BENCH, E.DARK_POKEMON)), 1)  # 悪タイプのニューラ・相手の場は数えない
        after = apply_kernel(with_coin_results(state, H), UseAttack(0, 0))
        self.assertEqual(after.players[1].active.damage, 40)

    def test_zero_dark_pokemon_does_not_flip(self):
        state = board(mon(GR_MEWTWO, (P, P)), mon(LAPRAS, (W,)), bench=(RATTATA,))
        after = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(after.players[1].active.damage, 20)
        self.assertFalse([e for e in after.log if e["kind"] == "coin_flip"])  # 0 匹ならコインを投げない（失敗にしない）


class DarkPulseTest(unittest.TestCase):
    """6 章: ［わるいはどう］。"""

    def state(self, *bench, attacker=None):
        attacker = attacker or mon(DARK_RAPIDASH, (R, R), evolved_from=PONYTA)
        return board(attacker, mon(LAPRAS, (W,)), bench=bench or (mon(GR_MEWTWO),))

    def test_coin_groups(self):
        for sides, damage in (((H, H), 40), ((H, T), 30), ((T,), 20)):
            with self.subTest(sides=sides):
                after = apply_kernel(with_coin_results(self.state(), *sides), UseAttack(0, 0))
                self.assertEqual(after.players[1].active.damage, damage)
                pulse = [e for e in after.log if e["kind"] == "dark_pulse"]
                self.assertEqual(len(pulse), 1)
                flips = [e for e in after.log if e["kind"] == "coin_flip"]
                self.assertEqual({e["source"] for e in flips}, {"power"})  # 特殊能力のコイン（ワザのコインではない。ESP の対象にならない）
                self.assertEqual(len(flips), len(sides))  # 1 枚目が「うら」なら 2 枚目を投げない

    def test_not_for_non_dark_attacker(self):
        state = board(mon(LAPRAS, (W,)), mon(LAPRAS, (W,)), bench=(mon(GR_MEWTWO),))
        after = apply_kernel(state, UseAttack(0, 0))
        self.assertFalse([e for e in after.log if e["kind"] == "dark_pulse"])

    def test_two_holders_stop(self):
        stops(self, self.state(mon(GR_MEWTWO), mon(GR_MEWTWO)), UseAttack(0, 0), DF1)


DITTO_SUPER = "ES2-032"
GR_MEWTWO = "PRN-041"


class DarkPulseStopTest(unittest.TestCase):
    """6 章: 読みで結果・決定が分かれる場面は、コインの前に止める（DP1）。隣の正常例は処理する（DarkPulseTest）。"""

    def test_multiple_damages_stop(self):
        """わるいアーボックのどくのきり（相手の対戦ポケモンと控え全員）: 複数のダメージで結果を共有するかが決まらない。"""
        from kyuura_engine.cards import load_card_pool

        pool = load_card_pool()
        ekans = next(c for c in sorted(pool.playable_ids) if pool.get(c).name_ja == pool.get("PMCG4-008").evolves_from and pool.get(c).is_basic_pokemon)
        state = board(mon("PMCG4-008", ("PMCG1-097",) * 3, evolved_from=ekans), mon(LAPRAS, (W,)), bench=(mon(GR_MEWTWO),), opponent_bench=(RATTATA,))
        stops(self, state, UseAttack(0, 1), DP1)

    def test_optional_bench_damage_is_a_second_damage(self):
        """わるいギャロップのひばしら（相手の対戦ポケモンへのダメージのあと、のぞむなら相手の控えにも）: 控えへのダメージを与える答えは、同じワザの 2 つめのダメージでコインの結果を
        共有するかが決まらないので、選べるが選ぶと止める（DP1）。与えない答えは残り、相手の対戦ポケモンへのダメージは 30 + 20。"""
        state = board(mon(DARK_RAPIDASH, (R, R), evolved_from=PONYTA), mon(LAPRAS, (W,)), bench=(mon(GR_MEWTWO),), opponent_bench=(RATTATA,))
        asked = apply_kernel(with_coin_results(state, H, H), UseAttack(0, 1))
        d = asked.decision
        self.assertEqual((d.kind, set(d.context_value("unresolved_choices")), d.context_value("unresolved_code")), ("discard_energy", set(d.options), DP1))
        stops(self, asked, ResolveDecision(0, d.id, (d.options[0],)), DP1)
        done = apply_kernel(asked, ResolveDecision(0, d.id, ()))
        self.assertEqual(done.players[1].active.damage, 50)
        for copied in (asked.clone(), _copy.deepcopy(asked), _pickle.loads(_pickle.dumps(asked))):  # コインの結果を運び、投げ直さない
            again = apply_kernel(copied, ResolveDecision(0, d.id, ()))
            self.assertEqual((again.players[1].active.damage, len([e for e in again.log if e["kind"] == "dark_pulse"])), (50, 1))


class AuditTest(unittest.TestCase):
    """10 章: ログの監査（v124_problems）は、エンジンの登録・計算を読まずに［わるいはどう］のコインと量を照らす。誤りを入れると見つける。"""

    def test_tampered_amount_is_found(self):
        from types import MappingProxyType

        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        result = games.play(("W123", "G124"), 90, keep_state=True)  # 開発用の seed（正式な対戦の seed 0〜3 とは別）
        done = result["state"]
        self.assertTrue([e for e in done.log if e["kind"] == "dark_pulse" and e["amount"]])
        self.assertEqual(log_problems(done), [])
        changed = next(e for e in done.log if e["kind"] == "dark_pulse" and e["amount"])
        bad = done.clone()
        bad.log = tuple(MappingProxyType(dict(e, amount=30 - e["amount"])) if e is changed else e for e in done.log)
        self.assertTrue(any("わるいはどう" in p for p in log_problems(bad)))

    def test_copied_powers_and_baby_form_in_the_audit(self):
        """3.1 節・3.4 節: ログの監査も、変身したポケモンの写した特殊能力（v0.50 の組の、ゴースに変身したメタモンの「とうめい」の判定）と、ベイビィに変身したメタモンへの
        ベイビィポケモンのルールのコインを、ログから組み立てた今の姿で確かめる（v0.123 までの監査は、いちばん上のカードだけを見ていた。前の版の組の比べで見つけた）。"""
        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        result = games.play(("D49", "M50"), 3, keep_state=True)
        done = result["state"]
        self.assertTrue([e for e in done.log if e["kind"] == "evade_check" and done.cards[e["pokemon"]].card_id == CLASSIC_DITTO])  # 写した「とうめい」の判定
        self.assertEqual(log_problems(done), [])
        result = games.play(("D49", "L114"), 2, keep_state=True)  # v0.114 の組
        done = result["state"]
        self.assertTrue([e for e in done.log if e["kind"] == "baby_rule_coin" and done.cards[e["baby"]].card_id == CLASSIC_DITTO])  # ベイビィに変身したメタモンへのワザ
        self.assertEqual(log_problems(done), [])


class RegistrationTest(unittest.TestCase):
    """4 章・8 章: 登録・写しの組・採用の記録・研究の対応表。登録だけを除くとカードの集合は基点の 1,358 枚にもどる。"""

    def test_entries(self):
        power = E.DEFAULT_EFFECTS.power_entry(DITTO_SUPER, 0)
        self.assertIsInstance(power.effect, E.SuperTransformPower)
        self.assertEqual((power.name_ja, power.play_text_ja, power.source), ("すごいへんしん", E.SUPER_TRANSFORM_LATEST_TEXT, "LD-ES2-032-PWR0"))
        self.assertIn("この「すごいへんしん」の力は使えず", power.text_ja)  # 印刷の文面は訂正のあとの値で照らす
        self.assertIn("「草・炎・水・雷・超・闘・悪・鋼」", power.play_text_ja)
        pulse = E.DEFAULT_EFFECTS.power_entry(GR_MEWTWO, 0)
        self.assertEqual((type(pulse.effect), pulse.effect.per_heads, pulse.effect.per_tails, pulse.effect.self_excluding), (E.DarkPulse, 20, 10, True))
        costume = E.DEFAULT_EFFECTS.attack_entry(GR_MEWTWO, 0)
        self.assertEqual((type(costume.effect), costume.effect.per, costume.text_ja), (E.CoinsPerOwnBenchDarkBonusDamage, 20, E.DARK_COSTUME_TEXT))
        pool = load_card_pool()
        self.assertEqual(costume.effect.check(pool.get(GR_MEWTWO).attacks[0]), [])
        self.assertTrue(costume.effect.check(dataclasses.replace(pool.get(GR_MEWTWO).attacks[0], damage=30)))  # 目安 20 と結ぶ

    def test_pool_and_removal(self):
        from kyuura_engine.cards import pool_from_extract
        from tests.release_catalog import cards_after, cards_before

        extract = read_extract()
        self.assertEqual(extract["pool_v0_124"], [DITTO_SUPER, GR_MEWTWO])
        # v0.125: 後の版のカード（pool_v0_125 から）は cards_after(…, "0.124") で除く（tests/release_catalog.py）。除いた残りは、今の対応カードからこの 2 枚を除いたものと同じ
        self.assertEqual(cards_after(extract, "0.123") - cards_after(extract, "0.124"), frozenset({DITTO_SUPER, GR_MEWTWO}))
        self.assertTrue({DITTO_SUPER, GR_MEWTWO}.isdisjoint(cards_before(extract, "0.124")))
        trimmed = dict(extract, cards=[c for c in extract["cards"] if c["id"] not in (DITTO_SUPER, GR_MEWTWO)], pool_v0_124=[])
        self.assertEqual(pool_from_extract(trimmed, E.DEFAULT_EFFECTS).playable_ids, load_card_pool().playable_ids - {DITTO_SUPER, GR_MEWTWO})
        ditto = next(c for c in extract["cards"] if c["id"] == DITTO_SUPER)
        self.assertEqual([x["id"] for x in ditto["corrections"]], [FIX])

    def test_adoption_records_and_links(self):
        cards = cs.load_sources()["cards"]
        self.assertEqual((cards[DITTO_SUPER]["play_text"], cards[DITTO_SUPER]["kyuura_commit"]), ({"power/0": "LD-ES2-032-PWR0"}, NOW))
        self.assertEqual(cards[GR_MEWTWO]["play_text"], {"attack/0": "kyuura_printed_text", "power/0": "kyuura_printed_text"})
        self.assertIn("公式大会", cards[GR_MEWTWO]["notes"])
        links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(links["latest_descriptions"]["registered"]["ES2-032/power/0"], "LD-ES2-032-PWR0")
        self.assertTrue({"PRN-041/attack/0", "PRN-041/power/0"} <= set(links["latest_descriptions"]["adopted_printed_text"]))
        added = [c for c in links["kyuura_cases_without_engine_ruling"]["cases"] if MIGRATION_TAG in c.get("note", "")]
        self.assertFalse([c for c in added if "unregistered" in c["engine"] or "requires_unregistered" in c["engine"]])  # 2 枚を登録したので、どの事例も止め方に結んだ
        codes = {code for c in added for code in c["engine"]["stop_codes"]}
        self.assertEqual(codes, {TC1, TK1, BX2, SV1, SV2, "UNRESOLVED_SUPER_TRANSFORM_COPIED_POWER", SV4, "UNRESOLVED_SUPER_TRANSFORM_ENERGY_COLORS", DP1, DF1,
                                 "UNRESOLVED_TRANSFORM_SPECIAL_ENERGY"})
        # v0.125: 停止コード・未解決の数は v0.125 で増えた（今の値は tests/test_catalog_contract.py）。v0.124 の値は、その版の最後のコミットの対応表で確かめる
        if (ROOT / ".git").exists():
            final = engine_json(V0124_FINAL, "kyuura_engine/data/research_links.json")
            self.assertEqual((final["counts"]["engine_stop_codes"], final["counts"]["engine_unresolved_rulings"]), (301, 302))


if __name__ == "__main__":
    unittest.main()

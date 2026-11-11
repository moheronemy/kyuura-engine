"""検証用 AI のバッチの明示的なデッキリスト・方式 boundary・観測の記録の失敗時の停止のテスト（docs/verification-ai-decklist.md）。

主に偽物の adapter と一時ディレクトリで確かめる。本物のエンジンを使うのは、デッキの合法性（deck_problems）・固定デッキの並び・計画の照合と、テストの中の短い局
（操作 40〜80。対戦バッチの実績ではない）だけ。
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.verification_ai import batch as B
from tools.verification_ai import decklist as DL

from tests.test_verification_ai_batch import FakeAdapter, no_memory, summary

# 0.179.0 の C1・C2 の計画（vai-batch-c1/plan.json）に記録した固定デッキの展開の sha256（固定デッキの並びが変わっていないことの照合）
C1_PRESET_SHA256 = {"hitmonchan-dewgong-v2": "66e569289363117ecc7f978ac994818116e04707a5b506fb90c653b22716ba1e",
                    "venusaur-parasect-v2": "a0831f9d5ac0c094b2a20709c7ca128d544ac8ef51160d59de3e08bb4e9cbd38"}


def preset_list(name: str, label: str = "test", reorder: bool = False) -> dict:
    from kyuura_engine import preset_deck

    cards = [list(e) for e in preset_deck(name).entries]
    if reorder:
        cards = list(reversed(cards))
    return {"format": DL.FORMAT, "label": label, "source": {"description": f"固定デッキ {name} の項目をそのまま写したテスト用のリスト"},
            "cards": cards, "content_sha256": DL.content_sha256(cards)}


def with_sha(obj: dict) -> dict:
    obj = json.loads(json.dumps(obj))
    if isinstance(obj.get("cards"), list):
        try:
            obj["content_sha256"] = DL.content_sha256(obj["cards"])
        except (TypeError, ValueError):
            pass
    return obj


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vai-decklist-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)


# ---------------------------------------------------------------- 形式（エンジンを使わない）


class FormTest(unittest.TestCase):
    BASE = {"format": DL.FORMAT, "label": "x", "source": {"description": "テスト", "reference": "tests"}, "cards": [["PMCG1-058", 4], ["PMCG1-097", 56]]}

    def ok(self):
        return with_sha(self.BASE)

    def test_valid_list_and_digests(self):
        obj = self.ok()
        self.assertEqual(DL.problems_of(obj), [])
        self.assertEqual(DL.validate(obj), obj)
        self.assertEqual(DL.expand(obj["cards"]), ["PMCG1-058"] * 4 + ["PMCG1-097"] * 56)
        swapped = [obj["cards"][1], obj["cards"][0]]
        self.assertEqual(DL.content_sha256(swapped), obj["content_sha256"])  # 内容の確認値は並びに依らない
        self.assertNotEqual(DL.expanded_sha256(DL.expand(swapped)), DL.expanded_sha256(DL.expand(obj["cards"])))  # 初期配列の確認値は並びで変わる
        d = DL.describe(obj)
        self.assertEqual((d["kind"], d["expansion"], d["cards"], d["entries"]), ("decklist", DL.EXPANSION, 60, obj["cards"]))

    def test_invalid_forms_are_refused(self):
        cases = {
            "unknown_key": dict(self.ok(), extra=1),
            "missing_label": {k: v for k, v in self.ok().items() if k != "label"},
            "format": dict(self.ok(), format="kyuura-vai-decklist/2"),
            "label_type": dict(self.ok(), label=3),
            "label_empty": dict(self.ok(), label="  "),
            "label_long": dict(self.ok(), label="x" * (DL.MAX_LABEL + 1)),
            "label_control": dict(self.ok(), label="a\nb"),
            "source_type": dict(self.ok(), source="text"),
            "source_unknown": dict(self.ok(), source={"description": "d", "trust": "high"}),
            "source_missing_description": dict(self.ok(), source={"reference": "r"}),
            "cards_type": with_sha(dict(self.BASE, cards={"PMCG1-058": 4})),
            "cards_empty": dict(self.ok(), cards=[]),
            "cards_too_many_entries": dict(self.ok(), cards=[[f"X-{i}", 1] for i in range(DL.MAX_ENTRIES + 1)]),
            "item_not_pair": dict(self.ok(), cards=[["PMCG1-058", 4, 1]]),
            "item_object": dict(self.ok(), cards=[{"id": "PMCG1-058", "count": 4}]),
            "bad_id": dict(self.ok(), cards=[["PMCG1 058", 4]]),
            "fullwidth_id": dict(self.ok(), cards=[["ＰＭＣＧ1-058", 4]]),
            "duplicate_id": with_sha(dict(self.BASE, cards=[["PMCG1-058", 2], ["PMCG1-058", 2]])),
            "duplicate_id_case": with_sha(dict(self.BASE, cards=[["PMCG1-058", 2], ["pmcg1-058", 2]])),
            "count_bool": dict(self.ok(), cards=[["PMCG1-058", True]]),
            "count_float": dict(self.ok(), cards=[["PMCG1-058", 4.0]]),
            "count_zero": dict(self.ok(), cards=[["PMCG1-058", 0]]),
            "count_negative": dict(self.ok(), cards=[["PMCG1-058", -1]]),
            "count_text": dict(self.ok(), cards=[["PMCG1-058", "4"]]),
            "too_many_cards": with_sha(dict(self.BASE, cards=[["PMCG1-097", DL.MAX_TOTAL_CARDS + 1]])),
            "sha_wrong": dict(self.ok(), content_sha256="0" * 64),
            "sha_upper": dict(self.ok(), content_sha256=self.ok()["content_sha256"].upper()),
            "not_object": [["PMCG1-058", 4]],
        }
        for name, obj in cases.items():
            with self.subTest(name):
                self.assertNotEqual(DL.problems_of(obj), [])
                with self.assertRaises(DL.DecklistError):
                    DL.validate(obj)

    def test_strict_json_reading(self):
        good = json.dumps(self.ok()).encode()
        self.assertEqual(DL.parse_bytes(good), self.ok())
        bad = {
            "duplicate_key": b'{"format": "a", "format": "b"}',
            "nan": good.replace(b'56]', b'NaN]'),
            "infinity": good.replace(b'56]', b'Infinity]'),
            "float_count": good.replace(b'56]', b'56.0]'),
            "not_utf8": good.replace(b'"x"', b'"\xff"'),
            "not_json": b"{",
            "oversize": b" " * (DL.MAX_FILE_BYTES + 1),
        }
        for name, data in bad.items():
            with self.subTest(name), self.assertRaises(DL.DecklistError):
                DL.parse_bytes(data)


# ---------------------------------------------------------------- 計画（本物の adapter。対戦はしない）


class PlanDeckTest(Tmp):
    def make(self, batch="p", modes=("uniform-stage",), **kw):
        kw.setdefault("observation", True)
        return B.make_plan(self.tmp, batch, engine_commit="test", tool_commit="test", seeds=[12], modes=list(modes), adapter=self.a,
                           game_limits={"operations": 40, "seconds": 60}, **kw)

    def setUp(self):
        super().setUp()
        self.a = B.EngineAdapter("test")

    def test_preset_order_and_digest_are_unchanged(self):
        from kyuura_engine import preset_deck

        for name, sha in C1_PRESET_SHA256.items():
            with self.subTest(name):
                record, cards = self.a.deck_record({"kind": "preset", "preset": name})
                self.assertEqual(cards, preset_deck(name).cards())
                self.assertEqual(record["sha256"], sha)  # C1 の計画と同じ展開の並び
                self.assertEqual((record["kind"], record["expansion"], record["legality"]["ok"]), ("preset", B.PRESET_EXPANSION, True))
        plan = self.make(deck0="hitmonchan-dewgong-v2", deck1="venusaur-parasect-v2")
        entry = plan["games"][0]
        self.assertIsNone(entry["config"]["decklists"])  # 固定デッキだけの局は、これまでどおり runner が固定デッキを読む
        self.assertEqual({s: d["sha256"] for s, d in entry["decks"].items()}, {"0": C1_PRESET_SHA256["hitmonchan-dewgong-v2"],
                                                                              "1": C1_PRESET_SHA256["venusaur-parasect-v2"]})

    def test_explicit_list_is_embedded_with_source_digests_and_order(self):
        same = preset_list("hitmonchan-dewgong")
        plan = self.make(decklists={"0": {"decklist": same, "input": None}}, deck1="venusaur-parasect")
        entry = plan["games"][0]
        d0 = entry["decks"]["0"]
        preset0, cards0 = self.a.deck_record({"kind": "preset", "preset": "hitmonchan-dewgong"})
        self.assertEqual((d0["kind"], d0["label"], d0["source"], d0["expansion"]), ("decklist", "test", same["source"], DL.EXPANSION))
        self.assertEqual(d0["entries"], same["cards"])
        self.assertEqual((d0["sha256"], d0["content_sha256"]), (preset0["sha256"], preset0["content_sha256"]))  # 同じ内容・同じ並びなら同じ確認値
        self.assertEqual(d0["legality"]["checked_by"], "kyuura_engine.deck.deck_problems")
        self.assertEqual(d0["legality"]["engine"]["version"], self.a.identity()["engine"]["version"])
        self.assertEqual(entry["config"]["deck0"], "decklist:" + same["content_sha256"][:12])
        self.assertEqual(entry["config"]["decklists"][0], cards0)  # 実行用の並びは計画に固定
        self.assertEqual(plan["decks"]["explicit_sides"], ["0"])
        self.assertEqual(B.load_plan(B.batch_dir(self.tmp, "p"), self.a)[0], plan)
        # 並びを変えたリスト: 内容の確認値は同じ・展開の確認値と実行用の並びは別
        rev = preset_list("hitmonchan-dewgong", reorder=True)
        record, cards = self.a.deck_record({"kind": "decklist", "decklist": rev})
        self.assertEqual(record["content_sha256"], preset0["content_sha256"])
        self.assertNotEqual(record["sha256"], preset0["sha256"])
        self.assertNotEqual(cards, cards0)

    def test_illegal_deck_is_refused_before_any_game(self):
        lists = {
            "deck_size": with_sha({**preset_list("hitmonchan-dewgong"), "cards": [["PMCG1-058", 4], ["PMCG1-097", 55]]}),
            "no_basic": with_sha({**preset_list("hitmonchan-dewgong"), "cards": [["PMCG1-077", 4], ["PMCG1-097", 56]]}),
            "too_many_copies": with_sha({**preset_list("hitmonchan-dewgong"), "cards": [["PMCG1-058", 5], ["PMCG1-097", 55]]}),
            "unknown_card": with_sha({**preset_list("hitmonchan-dewgong"), "cards": [["PMCG1-058", 4], ["NOPE-999", 1], ["PMCG1-097", 55]]}),
        }
        for name, obj in lists.items():
            with self.subTest(name):
                with self.assertRaises(B.BatchRefused) as caught:
                    self.make(batch=f"bad-{name}", decklists={"1": {"decklist": obj}})
                self.assertTrue(any("deck_problems" in p for p in caught.exception.problems))
                self.assertFalse(B.batch_dir(self.tmp, f"bad-{name}").exists())  # 計画も証跡のディレクトリも作らない

    def test_ambiguous_or_malformed_deck_specs_are_refused(self):
        good = preset_list("hitmonchan-dewgong")
        for name, kw in {"both": {"deck0": "hitmonchan-dewgong", "decklists": {"0": {"decklist": good}}},
                         "side": {"decklists": {"2": {"decklist": good}}},
                         "extra": {"decklists": {"0": {"decklist": good, "path": "x"}}},
                         "form": {"decklists": {"0": {"decklist": dict(good, label="")}}}}.items():
            with self.subTest(name), self.assertRaises(B.BatchRefused):
                self.make(batch=f"amb-{name}", **kw)

    def test_external_file_is_read_once_and_later_changes_do_not_affect_the_plan(self):
        path = self.tmp / "deck.json"
        path.write_bytes(json.dumps(preset_list("venusaur-parasect"), ensure_ascii=False).encode("utf-8"))
        loaded = DL.load_file(path)
        self.assertEqual((loaded["input"]["file_name"], loaded["input"]["bytes"]), ("deck.json", path.stat().st_size))
        plan = self.make(decklists={"1": loaded})
        bdir = B.batch_dir(self.tmp, "p")
        before = (bdir / "plan.json").read_bytes()
        path.write_bytes(json.dumps(preset_list("hitmonchan-dewgong"), ensure_ascii=False).encode("utf-8"))  # 元のファイルを変える
        reloaded, _ = B.load_plan(bdir, self.a)
        self.assertEqual((bdir / "plan.json").read_bytes(), before)
        self.assertEqual(reloaded["games"][0]["decks"]["1"]["input"]["sha256"], loaded["input"]["sha256"])
        self.assertEqual(reloaded, plan)
        path.unlink()  # 元のファイルがなくても照合・再開できる
        self.assertEqual(self.a.check_entry(reloaded["games"][0]), [])

    def tamper(self, bdir, change):
        plan = json.loads((bdir / "plan.json").read_bytes())
        change(plan)
        data = B.json_bytes(plan)
        (bdir / "plan.json").write_bytes(data)
        (bdir / "plan.sha256").write_text(B.sha256_bytes(data) + "  plan.json\n", encoding="utf-8")

    def test_resume_detects_changed_decks_settings_and_legality(self):
        same = preset_list("hitmonchan-dewgong")
        changes = {
            "entries": lambda p: p["games"][0]["decks"]["0"]["entries"].__setitem__(0, ["PMCG1-058", 3]),
            "order": lambda p: p["games"][0]["config"]["decklists"][0].reverse(),
            "expanded_sha": lambda p: p["games"][0]["decks"]["0"].__setitem__("sha256", "0" * 64),
            "legality": lambda p: p["games"][0]["decks"]["0"]["legality"].__setitem__("problems", ["x"]),
            "preset_side": lambda p: p["games"][0]["decks"]["1"].__setitem__("preset", "venusaur-parasect-v2"),
            "drop_decklists": lambda p: p["games"][0]["config"].__setitem__("decklists", None),
            "profile": lambda p: p["games"][0]["config"].__setitem__("profile", "boundary"),
            "conventions": lambda p: p["games"][0]["conventions"].__setitem__("digest", "sha256:x"),
            "policy": lambda p: p["games"][0]["policies"]["0"].__setitem__("seed", "x"),
        }
        for name, change in changes.items():
            with self.subTest(name):
                batch = f"t-{name}"
                self.make(batch=batch, decklists={"0": {"decklist": same}}, deck1="venusaur-parasect")
                bdir = B.batch_dir(self.tmp, batch)
                self.assertEqual(B.load_plan(bdir, self.a)[0]["format"], B.PLAN_FORMAT)
                self.tamper(bdir, change)
                with self.assertRaises(B.BatchRefused):
                    B.load_plan(bdir, self.a)
                with self.assertRaises(B.BatchRefused):
                    B.run_batch(self.tmp, batch, adapter=self.a, memory=no_memory)
                self.assertFalse((bdir / "games").exists())  # 対戦を始めない

    def test_provenance_fields_are_guarded_by_the_plan_sha256(self):
        """label・source は内容の確認値に入れない来歴。改変は plan.json の sha256（計画を作ったときの値）と、完了局のマーカーの plan_sha256 で見つける。"""
        same = preset_list("hitmonchan-dewgong")
        for name, change in {"label": lambda p: p["games"][0]["decks"]["0"].__setitem__("label", "other"),
                             "source": lambda p: p["games"][0]["decks"]["0"]["source"].__setitem__("description", "other"),
                             "input": lambda p: p["games"][0]["decks"]["0"].__setitem__("input", None)}.items():
            with self.subTest(name):
                batch = f"v-{name}"
                path = self.tmp / f"{name}.json"
                path.write_bytes(json.dumps(same).encode())
                self.make(batch=batch, decklists={"0": DL.load_file(path)})
                bdir = B.batch_dir(self.tmp, batch)
                plan = json.loads((bdir / "plan.json").read_bytes())
                change(plan)
                (bdir / "plan.json").write_bytes(B.json_bytes(plan))  # plan.sha256 は計画を作ったときのまま
                with self.assertRaises(B.BatchRefused):
                    B.load_plan(bdir, self.a)

    def test_deck_problems_at_run_time_stop_before_the_game(self):
        self.make(decklists={"0": {"decklist": preset_list("hitmonchan-dewgong")}})
        bdir = B.batch_dir(self.tmp, "p")

        class Changed(B.EngineAdapter):  # エンジンの deck_problems の結果が変わった場合（識別は同じとして）
            def legality(self, cards):
                out = super().legality(cards)
                return dict(out, ok=False, problems=["DECK_SIZE: test"])

        with self.assertRaises(B.BatchRefused) as caught:
            B.run_batch(self.tmp, "p", adapter=Changed("test"), memory=no_memory)
        self.assertTrue(any("deck_problems" in p or "legality" in p for p in caught.exception.problems))
        self.assertFalse((bdir / "games").exists())
        # 開始の直前（play の中）でも照らし、run_game を呼ばない
        plan, _ = B.load_plan(bdir, self.a)
        import tools.verification_ai.runner as runner

        called = []
        original = runner.run_game
        runner.run_game = lambda *a, **k: called.append(1)
        try:
            with self.assertRaises(B.BatchRefused):
                Changed("test").play(plan["games"][0], plan)
        finally:
            runner.run_game = original
        self.assertEqual(called, [])

    def test_old_plan_formats_are_not_resumed(self):
        self.make()
        bdir = B.batch_dir(self.tmp, "p")
        for fmt in ("kyuura-vai-batch-plan/4", "kyuura-vai-batch-plan/3"):
            with self.subTest(fmt):
                self.tamper(bdir, lambda p: p.__setitem__("format", fmt))
                with self.assertRaises(B.BatchRefused):
                    B.load_plan(bdir, self.a)

    def test_cli_requires_an_explicit_observation_choice_and_refuses_ambiguous_decks(self):
        path = self.tmp / "d.json"
        path.write_bytes(json.dumps(preset_list("hitmonchan-dewgong")).encode())
        base = ["plan", "--out", str(self.tmp), "--engine-commit", "test", "--tool-commit", "test", "--seeds", "12", "--modes", "boundary"]
        quiet = contextlib.redirect_stdout(io.StringIO())
        quiet_err = contextlib.redirect_stderr(io.StringIO())
        quiet.__enter__(), quiet_err.__enter__()
        self.addCleanup(quiet_err.__exit__, None, None, None)
        self.addCleanup(quiet.__exit__, None, None, None)
        with self.assertRaises(SystemExit):
            B.main(base + ["--batch", "c1"])  # --observation か --no-observation が必要
        self.assertEqual(B.main(base + ["--batch", "c2", "--observation", "--decklist0", str(path), "--deck0", "hitmonchan-dewgong"]), 2)
        self.assertFalse(B.batch_dir(self.tmp, "c2").exists())
        self.assertEqual(B.main(base + ["--batch", "c3", "--observation", "--decklist0", str(path)]), 0)
        plan = json.loads((B.batch_dir(self.tmp, "c3") / "plan.json").read_bytes())
        self.assertEqual((plan["observation"]["enabled"], plan["games"][0]["decks"]["0"]["kind"], plan["games"][0]["mode"]), (True, "decklist", "boundary"))
        self.assertEqual(B.main(["decklist", "--file", str(path)]), 0)


# ---------------------------------------------------------------- boundary の接続


class BoundaryTest(Tmp):
    def test_boundary_mode_reaches_the_runner_with_the_defined_setting(self):
        from tools.verification_ai.policies import STAGE, TUPLE, BoundaryPolicy
        from tools.verification_ai.runner import HOST, make_policies

        self.assertEqual((B.STAGE_DISTRIBUTION, B.TUPLE_DISTRIBUTION), (STAGE, TUPLE))
        a = B.EngineAdapter("test")
        entry = a.entry(game_id="b", mode="boundary", seed=12, deck0="hitmonchan-dewgong", deck1="venusaur-parasect", conventions=None, group="g")
        self.assertEqual((entry["config"]["policy"], entry["config"]["profile"], entry["config"]["distribution"]), ("boundary", "boundary", STAGE))
        self.assertEqual(a.check_entry(entry), [])
        config = a.config_of(entry)
        policies = make_policies(config)
        self.assertIsInstance(policies[0], BoundaryPolicy)
        self.assertEqual(type(policies[HOST]).__name__, "UniformPolicy")
        self.assertEqual(entry["policies"]["0"]["distribution"], "boundary-class-uniform+uniform-stage")
        for mode in ("uniform-stage", "uniform-tuple", "rules-v1", "rules-v2", "mixed"):  # deep の方式は profile deep のまま
            with self.subTest(mode):
                self.assertEqual(a.entry(game_id="d", mode=mode, seed=1, deck0="hitmonchan-dewgong", deck1="venusaur-parasect", conventions=None,
                                         group="g")["config"]["profile"], "deep")

    def test_undefined_combinations_are_refused(self):
        for combo in ({"policy": "rules", "profile": "boundary", "distribution": B.STAGE_DISTRIBUTION},
                      {"policy": "mixed", "profile": "boundary", "distribution": B.STAGE_DISTRIBUTION},
                      {"policy": "uniform", "profile": "boundary", "distribution": B.STAGE_DISTRIBUTION},
                      {"policy": "boundary", "profile": "deep", "distribution": B.STAGE_DISTRIBUTION},
                      {"policy": "boundary", "profile": "boundary", "distribution": B.TUPLE_DISTRIBUTION},
                      {"policy": "rules", "profile": "deep", "distribution": B.TUPLE_DISTRIBUTION}):
            with self.subTest(combo):
                self.assertNotEqual(B.setting_problems(combo), [])
        original = dict(B.MODES)
        B.MODES["rules-boundary"] = {"policy": "rules", "rules_version": 2, "profile": "boundary"}
        try:
            with self.assertRaises(B.BatchRefused):
                B.make_plan(self.tmp, "u", engine_commit="test", tool_commit="test", seeds=[1], modes=["rules-boundary"], adapter=B.EngineAdapter("test"))
        finally:
            B.MODES.clear()
            B.MODES.update(original)
        self.assertFalse(B.batch_dir(self.tmp, "u").exists())

    def scope(self, profile, candidates, display=()):
        from tools.verification_ai.runner import Config, Runner

        runner = Runner(Config(policy="boundary" if profile == "boundary" else "uniform", profile=profile))
        cands = {"candidates": candidates, "coverage": {"display_only_kinds": list(display), "residual": {"present": []}}}
        chosen, scope, reasons = runner._scope(cands, {})
        return [c["id"] for c in chosen], scope, reasons, runner.counters

    def test_scope_keeps_unverified_and_drops_display_withheld_and_unexecutable(self):
        def c(i, proc, kind="use_attack", disclosure="confirmed"):
            return {"id": i, "kind": kind, "processability": proc, "input_disclosure": disclosure, "input_stages": 0}

        cands = [c("c1", "supported"), c("c2", "unverified"), c("c3", "may_stop_later"), c("c4", "not_implemented"), c("c5", "unresolved_ruling"),
                 c("c6", "technical_limit"), c("c7", "supported", kind="show"), c("c8", "unverified", disclosure="unconfirmed")]
        chosen, scope, reasons, _ = self.scope("boundary", cands, display=("show",))
        self.assertEqual(chosen, ["c1", "c2", "c3"])
        self.assertEqual(scope["profile"], "boundary")
        self.assertEqual((reasons["c7"], reasons["c8"]), ("display_only", "input_withheld"))
        self.assertEqual({reasons[i] for i in ("c4", "c5", "c6")},
                         {"processability:not_implemented", "processability:unresolved_ruling", "processability:technical_limit"})
        # deep は変えない: supported・may_stop_later があれば unverified を入れない。なければ unverified に代える（deep_fallback_unverified）
        chosen, scope, _, counters = self.scope("deep", cands, display=("show",))
        self.assertEqual((chosen, scope["fallback_unverified"], counters["deep_fallback_unverified"]), (["c1", "c3"], False, 0))
        chosen, scope, _, counters = self.scope("deep", [c("c2", "unverified"), c("c4", "not_implemented")])
        self.assertEqual((chosen, scope["fallback_unverified"], counters["deep_fallback_unverified"]), (["c2"], True, 1))

    def test_boundary_policy_chooses_a_class_then_a_candidate(self):
        from tools.verification_ai.policies import BoundaryPolicy, player_seed

        items = [{"processability": "supported"}, {"processability": "supported"}, {"processability": "unverified"}]
        picked = {BoundaryPolicy(player_seed(s, 0)).choose("candidate", items, {})[0] for s in range(40)}
        self.assertIn(2, picked)  # unverified の区分も選ばれる
        self.assertTrue(picked & {0, 1})
        p = BoundaryPolicy(player_seed(1, 0))
        index, reason = p.choose("candidate", [{"processability": "unverified"}], {})
        self.assertEqual((index, p.draws, reason), (0, 0, "boundary:class:unverified:1classes:1in_class"))  # 1 区分・1 候補は乱数を使わない


# ---------------------------------------------------------------- 本物の短い局（テストの中の小さな実行。対戦バッチの実績ではない）


class ShortRealGameTest(Tmp):
    def test_explicit_list_equal_to_presets_keeps_the_golden_actions(self):
        from tests.test_verification_ai_v2_repeat import ACTION_GOLDEN
        from tools.verification_ai import records as R
        from tools.verification_ai.runner import run_game

        a = B.EngineAdapter("test")
        lists = {"0": {"decklist": preset_list("hitmonchan-dewgong")}, "1": {"decklist": preset_list("venusaur-parasect")}}
        names, lists = B.resolve_decks(None, None, lists)
        entry = a.entry(game_id="uniform-stage-s12", mode="uniform-stage", seed=12, deck0=names["0"], deck1=names["1"], conventions=None, group="g",
                        game_limits={"operations": 80, "seconds": 60}, decklists=lists)
        self.assertEqual(a.check_entry(entry), [])
        result = run_game(a.config_of(entry))
        digest = R.sequence_digest(R.action_sequence(result["trace"]), R.ACTION_FORMAT)
        self.assertEqual((digest["length"], digest["sha256"]), ACTION_GOLDEN["uniform-stage-s12"])  # 明示リストの経路でも同じ初期配列・同じ行動

    def test_boundary_batch_game_records_classes_and_sends_only_executable_inputs(self):
        from kyuura_engine import legal_actions as L

        a = B.EngineAdapter("test")
        B.make_plan(self.tmp, "bd", engine_commit="test", tool_commit="test", seeds=[12], modes=["boundary"], adapter=a,
                    game_limits={"operations": 40, "seconds": 60}, observation=True)
        report = B.run_batch(self.tmp, "bd", adapter=a, memory=no_memory)
        adir = B.batch_dir(self.tmp, "bd") / "games" / "g001-boundary-s12" / "attempt-001"
        marker = json.loads((adir / B.MARKER).read_text(encoding="utf-8"))
        self.assertIn(report.status, ("completed", "stopped_policy"))
        self.assertEqual(marker["evidence"], B.evidence_verdict(marker["stop"]))
        self.assertEqual(marker["summary"]["observation"]["status"], "complete")
        header = json.loads((adir / "header.json").read_text(encoding="utf-8"))
        self.assertEqual((header["policy"], header["profile"], header["policies"]["0"]["name"]), ("boundary", "boundary", "boundary"))
        trace = [json.loads(x) for x in (adir / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
        attempts = [e for e in trace if e.get("type") == "attempt" and e.get("actor") in (0, 1)]
        built = [e for e in attempts if e.get("build") == "ok" or e.get("check")]
        self.assertTrue(built)
        for e in attempts:
            self.assertEqual(e["scope"].get("profile"), "boundary")
            self.assertIn(e["candidate"]["processability"], L.EXECUTABLE)
            self.assertNotEqual(e["candidate"]["input_disclosure"], L.DISCLOSURE_UNCONFIRMED)
        for e in built:
            self.assertEqual(e["candidate_class"], e["candidate"]["processability"])  # 候補の区分と完成した入力の区分を分けて記録
            self.assertIn("class", e["input_processability"])
            self.assertTrue(all(i["processability"] in L.EXECUTABLE or i["processability"] is None for i in e["input_processability"]["items"]))


# ---------------------------------------------------------------- 観測の記録の失敗・欠落での停止（偽物）


class ObservingFake(FakeAdapter):
    def __init__(self, statuses=None, **kw):
        super().__init__(**kw)
        self.statuses = statuses or {}

    def entry(self, **kw):
        kw.pop("decklists", None)
        return super().entry(**kw)

    def play(self, entry, plan):
        from tools.verification_ai import observe as O

        out = super().play(entry, plan)
        status = self.statuses.get(entry["game_id"], O.COMPLETE)
        obs = {"format": O.FORMAT, "status": status, "rows": 1, "by_kind": {}, "problem_codes": {} if status == O.COMPLETE else {f"{status}:x": 1},
               "problems_total": 0 if status == O.COMPLETE else 1, "failure": None}
        for name in O.FILES:
            out.files.append((name, json.dumps(obs if name == O.SUMMARY and status is not None else {"n": name}).encode() + b"\n"))
        if status is not None:  # None: ファイルはあるが、局の要約に観測の状態がない（要約の欠け）
            out.summary["observation"] = obs
        return out


class ObservationStopTest(Tmp):
    def plan(self, adapter, seeds=(1, 2, 3)):
        return B.make_plan(self.tmp, "o", engine_commit="e", tool_commit="t", seeds=list(seeds), modes=["uniform-stage"], deck0="d0", deck1="d1",
                           adapter=adapter, observation=True)

    def run_(self, adapter, **kw):
        return B.run_batch(self.tmp, "o", adapter=adapter, memory=no_memory, **kw)

    def test_failed_incomplete_inconsistent_or_missing_observation_stops_and_is_not_success(self):
        for status in ("recorder_failed", "incomplete", "inconsistent", None):
            with self.subTest(status):
                shutil.rmtree(B.batch_dir(self.tmp, "o"), True)
                fake = ObservingFake(statuses={"g002-uniform-stage-s2": status})
                self.plan(fake)
                report = self.run_(fake)
                self.assertEqual(report.status, "stopped_policy")
                self.assertEqual(fake.calls, ["g001-uniform-stage-s1", "g002-uniform-stage-s2"])  # 次局へ進まない
                adir = B.batch_dir(self.tmp, "o") / "games" / "g002-uniform-stage-s2" / "attempt-001"
                marker = json.loads((adir / B.MARKER).read_text(encoding="utf-8"))
                self.assertEqual(marker["evidence"], "complete_with_stop")
                self.assertEqual(marker["stop"], [f"observation:{status}:{status}:x" if status else "observation:missing"])
                agg = B.aggregate(self.tmp, "o", adapter=fake)["verifier"]["games"]
                self.assertEqual((agg["complete_without_stop"], agg["complete_with_stop"]), (1, 1))
                # 再開: 確認（--acknowledge-stop）がなければ拒否。自動で確認済みにしない
                for _ in range(2):
                    with self.assertRaises(B.BatchRefused):
                        self.run_(fake)
                events, _ = B.Ledger(B.batch_dir(self.tmp, "o") / B.LEDGER).read()
                self.assertFalse([e for e in events if e.get("event") == "stop_acknowledged"])
                self.assertEqual(fake.calls, ["g001-uniform-stage-s1", "g002-uniform-stage-s2"])
                # 確認したあとも、集計では停止つきの完了のまま（成功した局と区別する）
                report = self.run_(fake, acknowledge=["g002-uniform-stage-s2"])
                self.assertEqual(report.skipped_complete, ["g001-uniform-stage-s1", "g002-uniform-stage-s2"])
                agg = B.aggregate(self.tmp, "o", adapter=fake)["verifier"]
                self.assertEqual((agg["games"]["complete_without_stop"], agg["games"]["complete_with_stop"]), (2, 1))
                self.assertEqual(sum(agg["observation"]["status"].values()), 3 if status else 2)

    def test_marker_that_hides_an_observation_problem_is_not_adopted(self):
        fake = ObservingFake(statuses={"g001-uniform-stage-s1": "incomplete"})
        self.plan(fake, seeds=(1,))
        self.assertEqual(self.run_(fake).status, "stopped_policy")
        bdir = B.batch_dir(self.tmp, "o")
        adir = bdir / "games" / "g001-uniform-stage-s1" / "attempt-001"
        path = adir / B.MARKER
        marker = json.loads(path.read_text(encoding="utf-8"))
        plan, plan_sha = B.load_plan(bdir, fake)
        entry = plan["games"][0]
        cases = {
            "stop_cleared": dict(marker, stop=[], evidence="complete_without_stop"),
            "evidence_only": dict(marker, evidence="complete_without_stop"),
            "status_rewritten": dict(marker, stop=[], evidence="complete_without_stop",
                                     summary=dict(marker["summary"], observation=dict(marker["summary"]["observation"], status="complete"))),
            "observation_removed": dict(marker, stop=[], evidence="complete_without_stop",
                                        summary={k: v for k, v in marker["summary"].items() if k != "observation"}),
        }
        for name, bad in cases.items():
            with self.subTest(name):
                path.write_bytes(B.json_bytes(bad))
                problems = B.verify_complete(adir, plan=plan, plan_sha=plan_sha, entry=entry)[1]
                self.assertTrue(problems)
                with self.assertRaises(B.BatchRefused):
                    self.run_(fake, acknowledge=["g001-uniform-stage-s1"])
        path.write_bytes(B.json_bytes(marker))
        self.assertEqual(B.verify_complete(adir, plan=plan, plan_sha=plan_sha, entry=entry)[1], [])

    def test_adapter_failure_leaves_no_marker_and_is_retried_as_a_new_attempt(self):
        fake = ObservingFake(script={"g001-uniform-stage-s1": RuntimeError("recorder files failed")})
        self.plan(fake, seeds=(1,))
        self.assertEqual(self.run_(fake).status, "stopped_error")
        gdir = B.batch_dir(self.tmp, "o") / "games" / "g001-uniform-stage-s1"
        self.assertFalse((gdir / "attempt-001" / B.MARKER).exists())
        self.assertTrue((gdir / "attempt-001" / B.NOTE).exists())
        fake.script = {}
        self.assertEqual(self.run_(fake).status, "completed")
        self.assertTrue((gdir / "attempt-002" / B.MARKER).exists())  # 失敗した attempt を採用しない（別の attempt で最初から）
        self.assertFalse((gdir / "attempt-001" / B.MARKER).exists())

    def test_stop_reasons_requires_observation_only_when_enabled(self):
        policy = B._policy_dict(B.StopPolicy())
        s = summary()
        self.assertEqual(B.stop_reasons(s, policy), ([], []))
        self.assertEqual(B.stop_reasons(s, policy, True), (["observation:missing"], []))
        self.assertEqual(B.StopPolicy().on_observation_problem, "stop")


if __name__ == "__main__":
    unittest.main()

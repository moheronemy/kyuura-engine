"""v0.152（docs/diagnostics-adapter-v0.152.md）: 診断の型と情報境界（U1）・コマンド実行結果のアダプタ（U2）。

盤面の種類（docs 5 章）:
- 構築盤面（``build_test_state`` と、v0.127・v0.134・v0.2f・v0.147〜v0.151 のテストの盤面）からの合法な操作
- 双子（テストだけの操作）: ``swap_hidden``・``swap_set_aside``
- 例外を差し込む確かめ（``adapter.apply_command`` を置きかえる）: 分類・内部エラー・対応漏れ。エンジンの処理の経路の確かめではない

停止コードの文字列は、テストの中に書かない（コード表・テストの盤面の定数から引く。停止の方針の台帳の走査が、テストの中の言及として数えないように）。
"""

from __future__ import annotations

import copy
import dataclasses
import importlib.util
import json
import pathlib
import unittest
from contextlib import contextmanager
from unittest import mock

from kyuura_engine import (
    EndTurn,
    IllegalActionError,
    ResolveDecision,
    StartSuddenDeath,
    UnsupportedError,
    UseAttack,
    apply_command,
    new_game,
    observe,
    state_to_dict,
)
from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests import helpers as H
from tests import test_attack_deck_evolution_preflight_v0_148 as V148
from tests import test_deck_content_prechecks_v0_147 as V147
from tests import test_deck_search_decision_presence_v0_150 as V150
from tests import test_deck_search_stop_oracles_v0_151 as V151
from tests import test_simultaneous_ko as SK
from tests.helpers import with_coin_bits
from tests.test_deferred_shortage_user_promos_v0_127 import dry_board, run
from tests.test_optional_deck_evolution_presence_v0_149 import swap_set_aside
from tests.test_sudden_death_v0_134 import constructed_sudden_death, with_decklists

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "diagnostics-adapter-v0.152.md"
SPEC = ROOT / "docs" / "diagnostics-replay-api-design.json"
VIEWERS = (0, 1, None)
P = H.POTION
# 閲覧用の結果に入ってはいけない項目の名前（検証者用の記録の項目と、秘密を含む値）
FORBIDDEN_KEYS = {"engine_code", "exception_type", "raw_message", "traceback", "problems", "halt_code", "halt_message", "halt_references", "command",
                  "exception", "verifier", "seed", "rng", "rng_state", "rng_fingerprint", "rng_state_sha256", "state_digest", "state", "deck", "prizes", "hand",
                  "options", "context", "resume", "log", "mapped"}
ACTOR_KEYS = {"kyuura_diagnostic_schema", "role", "viewer", "outcome", "status", "stage", "continuable", "next", "diagnostic_id", "category", "subkind",
              "case_id", "case_status", "message", "halt", "operation_id", "convention_set"}
NOTICE_KEYS = {"kyuura_diagnostic_schema", "role", "viewer", "status", "continuable", "next", "halt", "convention_set"}


def snapshot(state):
    return repr(state_to_dict(state, format_version=max(FORMAT_VERSIONS))), state.rng.getstate(), tuple(dict(e) for e in state.log)


def views(result):
    return [None if (v := result.view_for(viewer)) is None else v.to_dict() for viewer in VIEWERS]


def leaks(payload, path="") -> list[str]:
    """閲覧用の結果（辞書）の中の、入ってはいけない項目の名前。"""
    found = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in FORBIDDEN_KEYS:
                found.append(f"{path}.{key}")
            found += leaks(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for i, value in enumerate(payload):
            found += leaks(value, f"{path}[{i}]")
    return found


@contextmanager
def raising(error):
    """``adapter.apply_command`` を、``error`` を投げる関数に置きかえる（分類の確かめ。エンジンの経路の確かめではない）。"""
    def fake(state, command):
        raise error
    with mock.patch.object(A, "apply_command", fake):
        yield


def catalog_code(category, raised_as=None):
    for code, entry in sorted(D.default_catalog().codes.items()):
        if entry.category == category and (raised_as is None or raised_as in entry.raised_as):
            return code
    raise AssertionError(category)


# ---------------------------------------------------------------- 盤面


def fc1_board():
    """はらだいこ（v0.151）: 山札に基本エネルギーカードが 1 枚、うらのサイド 6 枚。配分を読まない下限が 2 より小さいので、宣言の前に FC1 で止める。"""
    return V151.belly_drum([H.FIRE] + [P] * 4)


def dry_up_asked():
    s = dry_board(1)
    return apply_command(s, UseAttack(s.current_player, 0))


def dry_up_halting():
    """ドライアップ（v0.127）: 「おもて」3 回・「水」1 枚で、答えのあとに途中停止（受理した結果として停止）。"""
    asked = dry_up_asked()
    d = asked.decision
    return with_coin_bits(asked, *run(3)), ResolveDecision(d.player, d.id, (asked.players[1].active.pokemon_id,))


def last_answer(prizes, their_prizes):
    """v0.2f の同時のきぜつ: 最後の決定の前の状態と、その答え。"""
    x, _ = SK.jolt(SK.board(prizes=prizes, their_prizes=their_prizes))
    while True:
        d = x.decision
        command = ResolveDecision(d.player, d.id, (x.current_player if d.kind == "prize_first" else d.options[0],))
        nxt = apply_command(x, command)
        if nxt.decision is None:
            return x, command
        x = nxt


def sudden_death_state():
    return constructed_sudden_death(with_decklists(H.build_test_state([{"active": H.PIKACHU, "prizes": 1}, {"active": H.RATTATA, "prizes": 1}])))


SCENARIOS = {
    "fc1 宣言の拒否": lambda: (fc1_board(), UseAttack(0, 0)),
    "番でない操作の拒否": lambda: (fc1_board(), EndTurn(1)),
    "決定待ち": lambda: (dry_board(1), UseAttack(0, 0)),
    "答えのあとの途中停止": dry_up_halting,
    "延長戦の開始待ち": lambda: last_answer(1, 1),
    "終局": lambda: last_answer(1, 6),
    "延長戦の開始": lambda: (sudden_death_state(), StartSuddenDeath()),
    "延長戦の開始待ちでの拒否": lambda: (sudden_death_state(), EndTurn(0)),
}


class CompatibilityTest(unittest.TestCase):
    """既存の API と同じ: 受理の条件・返す状態・乱数・ログ・観測が ``apply_command`` と同じで、渡した状態を変えない。"""

    def test_same_as_apply_command(self):
        for name, build in SCENARIOS.items():
            with self.subTest(name):
                state, command = build()
                before = snapshot(state)
                result = A.submit(state, command)
                self.assertEqual(snapshot(state), before)
                try:
                    expected = apply_command(state, command)
                except (IllegalActionError, UnsupportedError) as error:
                    self.assertEqual(result.outcome, D.REJECTED)
                    self.assertIs(result.state, state)
                    self.assertEqual((result.verifier.exception_type, result.verifier.engine_code, result.verifier.raw_message),
                                     (type(error).__name__, error.code, str(error)))
                else:
                    self.assertEqual(result.outcome, D.ACCEPTED)
                    self.assertEqual(snapshot(result.state), snapshot(expected))
                    for viewer in VIEWERS:
                        self.assertEqual(observe(result.state, viewer), observe(expected, viewer))

    def test_engine_api_is_unchanged(self):
        # 既存の入口の名前・戻り値の型は同じ（新しい関数はモジュールを分けた）
        state, command = SCENARIOS["決定待ち"]()
        self.assertEqual(type(apply_command(state, command)).__name__, "GameState")
        import kyuura_engine
        self.assertNotIn("submit", kyuura_engine.__all__)


EXPECTED = {
    "fc1 宣言の拒否": (D.REJECTED, D.IN_PROGRESS, True, D.NEXT_TURN_ACTION),
    "番でない操作の拒否": (D.REJECTED, D.IN_PROGRESS, True, D.NEXT_TURN_ACTION),
    "決定待ち": (D.ACCEPTED, D.AWAITING_DECISION, True, D.NEXT_ANSWER_DECISION),
    "答えのあとの途中停止": (D.ACCEPTED, D.HALTED, False, None),
    "延長戦の開始待ち": (D.ACCEPTED, D.SUDDEN_DEATH_PENDING, True, D.NEXT_START_SUDDEN_DEATH),
    "終局": (D.ACCEPTED, D.GAME_OVER, False, None),
    "延長戦の開始": (D.ACCEPTED, D.IN_PROGRESS, True, D.NEXT_PLACE_STARTING),
    "延長戦の開始待ちでの拒否": (D.REJECTED, D.SUDDEN_DEATH_PENDING, True, D.NEXT_START_SUDDEN_DEATH),
}


class OutcomeStatusTest(unittest.TestCase):
    """結果と状態の組: 拒否・受理のあとの停止・決定待ち・終局・延長戦の開始待ちを区別する。"""

    def test_each_scenario(self):
        for name, build in SCENARIOS.items():
            with self.subTest(name):
                result = A.submit(*build())
                outcome, status, cont, next_kind = EXPECTED[name]
                self.assertEqual((result.outcome, result.status, result.continuable), (outcome, status, cont))
                self.assertEqual([a.kind for a in result.next], [] if next_kind is None else [next_kind])
                self.assertEqual(result.halt is not None, status == D.HALTED)
                self.assertEqual(result.diagnosis is not None, outcome != D.ACCEPTED)

    def test_halt_is_public_and_not_a_rejection(self):
        result = A.submit(*dry_up_halting())
        self.assertEqual((result.outcome, result.halt.category, result.halt.interrupted), (D.ACCEPTED, D.RULING_UNRESOLVED, True))
        self.assertEqual(result.halt.diagnostic_id, result.state.halt.code)  # ログ halted のコード（全員に見える）
        self.assertNotIn("受け付けません", result.halt.message)  # 停止の文（拒否の文ではない）
        for viewer in VIEWERS:
            self.assertEqual(result.view_for(viewer).halt, result.halt)

    def test_decision_answer_rejection(self):
        asked = dry_up_asked()
        result = A.submit(asked, ResolveDecision(asked.decision.player, asked.decision.id + 1, ()))
        self.assertEqual((result.outcome, result.status, result.stage, result.diagnosis.subkind), (D.REJECTED, D.AWAITING_DECISION, D.STAGE_DECISION_ANSWER, "answer"))
        self.assertEqual(result.next, (D.NextAction(D.NEXT_ANSWER_DECISION, asked.decision.player),))

    def test_game_over_rejects(self):
        state, command = last_answer(1, 6)
        over = apply_command(state, command)
        result = A.submit(over, EndTurn(1))
        self.assertEqual((result.outcome, result.status, result.continuable, result.next), (D.REJECTED, D.GAME_OVER, False, ()))

    def test_contradicting_combinations_are_refused(self):
        good = A.submit(*SCENARIOS["決定待ち"]())
        bad = [
            {"outcome": D.ACCEPTED, "status": D.UNAVAILABLE},
            {"outcome": D.REJECTED, "diagnosis": None},
            {"outcome": D.FAILED},
            {"outcome": D.ACCEPTED, "status": D.HALTED},
            {"continuable": True, "status": D.GAME_OVER},
            {"outcome": "maybe"},
            {"outcome": D.REJECTED, "diagnosis": D.internal_error()},
        ]
        for change in bad:
            with self.subTest(change=change), self.assertRaises(ValueError):
                dataclasses.replace(good, **change)


class ClassificationTest(unittest.TestCase):
    """分類: 未裁定・未対応・技術的制限・不正な操作・互換性・状態の不整合・内部エラー・対応漏れ。例外の型の名前・接頭辞からは推測しない。"""

    def test_real_paths(self):
        rejected = A.submit(fc1_board(), UseAttack(0, 0))
        self.assertEqual((rejected.diagnosis.category, rejected.diagnosis.diagnostic_id), (D.RULING_UNRESOLVED, V150.FC1))
        self.assertEqual(rejected.diagnosis.case_status, D.CASE_NOT_IDENTIFIED)  # 事例が 2 つあるコード: 根拠なく選ばない
        self.assertIsNone(rejected.diagnosis.case_id)
        illegal = A.submit(fc1_board(), EndTurn(1))
        self.assertEqual((illegal.diagnosis.category, illegal.diagnosis.subkind, illegal.diagnosis.case_status), (D.INVALID_INPUT, "command", D.CASE_NOT_APPLICABLE))

    def test_injected_categories(self):
        for category in (D.RULING_UNRESOLVED, D.UNSUPPORTED, D.TECHNICAL_LIMIT, D.COMPATIBILITY):
            code = catalog_code(category, "unsupported")
            with self.subTest(category=category), raising(UnsupportedError(code, "x")):
                result = A.submit(fc1_board(), UseAttack(0, 0))
                self.assertEqual((result.outcome, result.diagnosis.category, result.diagnosis.diagnostic_id), (D.REJECTED, category, code))
                self.assertTrue(result.verifier.mapped)

    def test_compatibility_state_check(self):
        asked = dry_up_asked()
        broken = asked.clone()
        broken.decision = dataclasses.replace(asked.decision, resume="resume_not_known_for_test")
        result = A.submit(broken, ResolveDecision(asked.decision.player, asked.decision.id, ()))
        self.assertEqual((result.outcome, result.diagnosis.category, result.stage, result.continuable), (D.REJECTED, D.COMPATIBILITY, D.STAGE_STATE_CHECK, False))

    def test_state_integrity(self):
        broken = dry_board(1).clone()
        uid = broken.players[1].deck.pop()  # 呼び出し側が状態を書きかえた（カードの保存則が崩れる）
        result = A.submit(broken, UseAttack(0, 0))
        self.assertEqual((result.outcome, result.status, result.diagnosis.category, result.continuable, result.state), (D.FAILED, D.UNAVAILABLE, D.STATE_INTEGRITY, False, None))
        actor = result.view_for(0).to_dict()
        self.assertEqual(actor["message"], D.default_catalog().category_texts[D.STATE_INTEGRITY])  # 一般的な説明だけ
        self.assertNotIn(str(uid), json.dumps(actor, ensure_ascii=False))
        self.assertTrue(result.verifier.problems)  # 内部の値は検証者用の記録に
        self.assertNotEqual(result.diagnosis.category, D.UNSUPPORTED)

    def test_internal_error(self):
        with raising(RuntimeError("secret uid 4242")):
            result = A.submit(fc1_board(), UseAttack(0, 0))
        self.assertEqual((result.outcome, result.diagnosis.category, result.continuable, result.state), (D.FAILED, D.INTERNAL_ERROR, False, None))
        for view in views(result):
            self.assertNotIn("4242", json.dumps(view, ensure_ascii=False))
            self.assertEqual(leaks(view), [])
        self.assertIn("RuntimeError", result.verifier.traceback)
        self.assertIn("4242", result.verifier.raw_message)
        self.assertIsInstance(result.verifier.exception, RuntimeError)

    def test_exits_are_not_caught(self):
        for error in (KeyboardInterrupt(), SystemExit(1), MemoryError()):
            with self.subTest(type(error).__name__), raising(error), self.assertRaises(type(error)):
                A.submit(fc1_board(), UseAttack(0, 0))

    def test_unknown_codes_are_not_guessed(self):
        # 表にないコード: 接頭辞が研究上の停止・未対応に見えても、推測で分類しない（対応漏れ）。元のコードは検証者用の記録だけ
        lookalike = "UNRESOLVED" + "_NOT_IN_TABLE_FOR_TEST"
        for error in (UnsupportedError(lookalike, "x"), UnsupportedError("NOT_IN_TABLE_FOR_TEST", "x"), IllegalActionError("NOT_IN_TABLE_FOR_TEST", "x")):
            with self.subTest(error.code), raising(error):
                result = A.submit(fc1_board(), UseAttack(0, 0))
                self.assertEqual((result.outcome, result.diagnosis.category, result.diagnosis.diagnostic_id), (D.REJECTED, D.UNMAPPED, D.UNMAPPED_ID))
                self.assertFalse(result.verifier.mapped)
                self.assertEqual(result.verifier.engine_code, error.code)
                for view in views(result):
                    self.assertNotIn(error.code, json.dumps(view, ensure_ascii=False))
                self.assertTrue(result.continuable)  # 続けられるかは状態から（元の状態は変わっていない）

    def test_wrong_exception_type_for_a_known_code_is_unmapped(self):
        code = catalog_code(D.RULING_UNRESOLVED)
        with raising(IllegalActionError(code, "x")):
            result = A.submit(fc1_board(), UseAttack(0, 0))
        self.assertEqual(result.diagnosis.category, D.UNMAPPED)

    def test_halt_codes_outside_the_table_are_unmapped(self):
        diagnosis, mapped = D.classify_halt_code("NOT_IN_TABLE_FOR_TEST")
        self.assertEqual((diagnosis.category, mapped), (D.UNMAPPED, False))
        diagnosis, mapped = D.classify_halt_code(catalog_code(D.INVALID_INPUT))  # 不正な操作のコードで停止することはない
        self.assertEqual((diagnosis.category, mapped), (D.UNMAPPED, False))


class CatalogTest(unittest.TestCase):
    """コード表: エンジンが投げうるコードの漏れを見つける。表を壊すと見つける。"""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("build_diagnostic_catalog", ROOT / "scripts" / "build_diagnostic_catalog.py")
        cls.B = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.B)

    def test_catalog_is_up_to_date_and_complete(self):
        catalog, problems = self.B.build()
        self.assertEqual(problems, [])
        self.assertEqual(json.loads(self.B.OUTPUT.read_text(encoding="utf-8")), catalog)

    def test_every_known_code_is_in_the_catalog(self):
        ledger = json.loads((ROOT / "docs" / "stop-policy-classification.json").read_text(encoding="utf-8"))
        illegal, unknown = self.B.illegal_codes()
        self.assertEqual(unknown, [])
        known = set(illegal) | {e["id"] for e in ledger["entries"] if e["entry_kind"] in ("research_stop_code", "runtime_stop_code") and e["status"] == "active"}
        known -= set(self.B.LEDGER_E_EXCLUDED)
        known -= {e["id"] for e in ledger["entries"] if {m["mechanism"] for m in e.get("current_stop") or []} == {"not_raised"}}
        self.assertEqual(sorted(known - set(D.default_catalog().codes)), [])

    def test_removed_code_and_unlisted_dynamic_site_are_detected(self):
        original = self.B.DYNAMIC_SITES
        try:
            self.B.DYNAMIC_SITES = dict(list(original.items())[1:])
            _, problems = self.B.build()
            self.assertTrue(any("動的な呼び出し箇所が表にない" in p for p in problems), problems)
        finally:
            self.B.DYNAMIC_SITES = original
        catalog, _ = self.B.build()
        broken = copy.deepcopy(catalog)
        removed = min(broken["codes"])
        del broken["codes"][removed]
        self.assertNotEqual(self.B.dump(broken), self.B.dump(catalog))  # --check が違いを見つける
        with mock.patch.object(D, "default_catalog", return_value=D.Catalog(broken)):
            self.assertEqual(D.classify_error(UnsupportedError(removed, "x") if removed.startswith("UN") else IllegalActionError(removed, "x"))[0].category, D.UNMAPPED)

    def test_texts_have_no_embedded_values(self):
        catalog = D.default_catalog()
        texts = [e.text for e in catalog.codes.values()] + list(catalog.category_texts.values()) + list(catalog.subkind_texts.values()) + list(catalog.halt_texts.values())
        texts += list(D.ADAPTER_TEXTS.values())
        for text in texts:
            self.assertNotRegex(text, r"[{}%]")  # 書式の埋め込みがない（決まった文）
            self.assertNotRegex(text, r"\b\d{2,}\b")  # uid・枚数のような数を書かない

    def test_same_code_with_several_scenes_is_not_identified(self):
        for entry in D.default_catalog().codes.values():
            if entry.case_status == D.CASE_NOT_IDENTIFIED:
                self.assertIsNone(entry.case_id)
            if entry.case_status == D.CASE_IDENTIFIED:
                self.assertIsNotNone(entry.case_id)


class InformationBoundaryTest(unittest.TestCase):
    """閲覧用の結果は公開を許した項目だけ。拒否は本人だけ。見る人の値で検証者にならない。対戦が終わっても広げない。"""

    def test_view_types_carry_only_allowed_fields(self):
        for name, build in SCENARIOS.items():
            result = A.submit(*build())
            for viewer, view in zip(VIEWERS, views(result)):
                with self.subTest(name, viewer=viewer):
                    if view is None:
                        continue
                    self.assertEqual(set(view), ACTOR_KEYS if view["role"] == "actor" else NOTICE_KEYS)
                    self.assertEqual(leaks(view), [])
        self.assertEqual({f.name for f in dataclasses.fields(D.ActorDiagnostic)} | {"kyuura_diagnostic_schema", "role"}, ACTOR_KEYS)
        self.assertEqual({f.name for f in dataclasses.fields(D.StatusNotice)} | {"kyuura_diagnostic_schema", "role"}, NOTICE_KEYS)

    def test_leak_check_detects_injected_fields(self):
        view = A.submit(*SCENARIOS["fc1 宣言の拒否"]()).view_for(0).to_dict()
        view["halt"] = {"halt_message": "x"}
        view["raw_message"] = "x"
        self.assertEqual(sorted(leaks(view)), [".halt.halt_message", ".raw_message"])

    def test_rejections_go_to_the_actor_only(self):
        for name in ("fc1 宣言の拒否", "番でない操作の拒否", "延長戦の開始待ちでの拒否"):
            result = A.submit(*SCENARIOS[name]())
            for viewer in VIEWERS:
                with self.subTest(name, viewer=viewer):
                    view = result.view_for(viewer)
                    if viewer == result.actor:
                        self.assertEqual(view.outcome, D.REJECTED)
                    else:
                        self.assertIsNone(view)  # 拒否があったことも知らせない

    def test_finished_games_do_not_widen(self):
        state, command = last_answer(1, 6)
        over = apply_command(state, command)
        result = A.submit(over, EndTurn(1))
        self.assertEqual([result.view_for(v) is None for v in VIEWERS], [True, False, True])
        self.assertEqual(set(result.view_for(1).to_dict()), ACTOR_KEYS)

    def test_viewer_values(self):
        result = A.submit(*SCENARIOS["決定待ち"]())
        for viewer in ("verifier", True, 2, -1, "0"):
            with self.subTest(viewer=viewer), self.assertRaises(ValueError):
                result.view_for(viewer)
        self.assertFalse(hasattr(result.view_for(0), "verifier"))

    def test_submitter_mismatch_is_rejected_without_the_engine(self):
        state = fc1_board()
        with raising(AssertionError("エンジンを呼んだ")):
            result = A.submit(state, EndTurn(0), submitter=1)
        self.assertEqual((result.outcome, result.diagnosis.diagnostic_id, result.actor, result.stage), (D.REJECTED, D.SUBMITTER_MISMATCH_ID, 1, D.STAGE_SUBMISSION))
        self.assertIsNone(result.view_for(0))  # 名前を使われたプレイヤーにも知らせない


class TwinTest(unittest.TestCase):
    """v0.147〜v0.151 の代表の双子（見る人に同じ情報が見えて、見えない配分だけが違う）で、どの見る人の結果も同じ（診断から配分を区別できない）。"""

    def assertSameViews(self, states, commands):
        states = list(states)
        for step, command in enumerate(commands):
            results = [A.submit(s, command(s) if callable(command) else command) for s in states]
            self.assertEqual([r.outcome for r in results], [results[0].outcome] * len(results), f"段 {step}")
            for viewer in VIEWERS:
                self.assertEqual({json.dumps(None if (v := r.view_for(viewer)) is None else v.to_dict(), ensure_ascii=False, sort_keys=True) for r in results}.__len__(),
                                 1, f"段 {step}・見る人 {viewer}")
            if results[0].outcome != D.ACCEPTED:
                return results
            states = [r.state for r in results]
        return results

    def test_v151_stop_oracles(self):
        for case in V151.RB2_CASES:
            with self.subTest(case.name):
                s = V151.board(case, [V151.RAINBOW] + [P] * 5)
                results = self.assertSameViews([s, V147.swap_hidden(s, V151.RAINBOW)], [UseAttack(0, 0)])
                self.assertEqual(results[0].diagnosis.diagnostic_id, V150.RB2)
                s = V151.set_aside_board(case, [V151.RAINBOW] + [P] * 4)
                self.assertSameViews([s, swap_set_aside(s, V151.RAINBOW)], [UseAttack(0, 0)])
        s = fc1_board()
        self.assertSameViews([s, V147.swap_hidden(s, H.FIRE)], [UseAttack(0, 0)])
        s = V151.trick([H.GRASS] + [P] * 4, hand=(P, P))
        self.assertSameViews([s, V147.swap_hidden(s, H.GRASS)], [UseAttack(0, 0), V151.returning(2)])

    def test_v150_decision_presence(self):
        for path in V150.PATHS:
            with self.subTest(path.name):
                s = V150.board(path)
                results = self.assertSameViews([s, V147.swap_hidden(s, path.target)], V150.steps_to_search(path))
                self.assertEqual(results[0].status, D.AWAITING_DECISION)

    def test_v147_and_v148_prechecks(self):
        for name, card, build, steps, check, _code in (*V147.LOWER_BOUND, *V147.POSSIBLE):
            with self.subTest(name):
                s = build(1)
                self.assertSameViews([s, V147.swap_hidden(s, card)], [*steps, check])
        for name, build, card, index, _code, patch in V148.DECLARATIONS:
            with self.subTest(name), patch():
                s = build()
                self.assertSameViews([s, V147.swap_hidden(s, card)], [UseAttack(0, index)])

    def test_three_convention_sets(self):
        # 既存の 3 つの集合（今の挙動・S2a・PO）で、代表の双子の結果が同じ。結果の規約集合の識別は、その集合の値（照合値を変えていない）
        for conventions in V147.SETS:
            with self.subTest(conventions=conventions):
                s = V151.belly_drum([H.FIRE] + [P] * 4, conventions=conventions)
                results = self.assertSameViews([s, V147.swap_hidden(s, H.FIRE)], [UseAttack(0, 0)])
                case = V151.RB2_CASES[0]
                s = V151.board(case, [V151.RAINBOW] + [P] * 5, conventions=conventions)
                self.assertSameViews([s, V147.swap_hidden(s, V151.RAINBOW)], [UseAttack(0, 0)])
                identity = observe(s, None)["convention_set"]
                self.assertEqual(results[0].convention_set.to_dict(), {k: identity[k] for k in ("id", "version", "digest")})

    def test_twin_check_would_see_a_leaky_view(self):
        # 双子は実際に配分が違う（配分を書いた結果なら違いが出る）。比べ方が違いを見落とさないこと
        s = fc1_board()
        twin = V147.swap_hidden(s, H.FIRE)
        leaky = [sorted(x.cards[u].card_id for u in x.players[0].deck) for x in (s, twin)]
        self.assertNotEqual(leaky[0], leaky[1])


class HostedGameTest(unittest.TestCase):
    """ホストの境界: 受理したときだけ進む。拒否は前の状態。処理できない結果のあとは操作を受け付けない。"""

    def test_flow(self):
        game = A.HostedGame(dry_board(1))
        first = game.state
        self.assertEqual(game.submit(EndTurn(1)).outcome, D.REJECTED)
        self.assertIs(game.state, first)
        accepted = game.submit(UseAttack(0, 0), submitter=0, operation_id="op-1")
        self.assertIs(game.state, accepted.state)
        self.assertEqual(accepted.view_for(0).operation_id, "op-1")
        self.assertEqual(game.view(1), observe(game.state, 1))
        with raising(RuntimeError("x")):
            failed = game.submit(EndTurn(0))
        self.assertEqual(failed.outcome, D.FAILED)
        self.assertIs(game.state, accepted.state)
        with self.assertRaises(A.HostStoppedError):
            game.submit(EndTurn(0))


class StartGameTest(unittest.TestCase):
    def test_start(self):
        result = A.start_game(H.PIKACHU_DECK, H.PIKACHU_DECK_B, 3)
        self.assertEqual((result.outcome, result.stage, result.actor), (D.ACCEPTED, D.STAGE_SETUP, None))
        self.assertEqual(snapshot(result.state), snapshot(new_game(H.PIKACHU_DECK, H.PIKACHU_DECK_B, 3)))
        self.assertEqual(result.next, (D.NextAction(D.NEXT_PLACE_STARTING, None),))

    def test_rejections(self):
        for seed in (-1, True, "1", 1.0):
            with self.subTest(seed=seed):
                result = A.start_game(H.PIKACHU_DECK, H.PIKACHU_DECK_B, seed)
                self.assertEqual((result.outcome, result.status, result.diagnosis.diagnostic_id), (D.REJECTED, D.NOT_STARTED, D.INVALID_SEED_ID))
        deck = A.start_game(H.PIKACHU_DECK[:-1], H.PIKACHU_DECK_B, 0)
        self.assertEqual((deck.diagnosis.category, deck.diagnosis.subkind, deck.diagnosis.diagnostic_id), (D.INVALID_INPUT, "setup", "INVALID_DECK"))
        conventions = A.start_game(H.PIKACHU_DECK, H.PIKACHU_DECK_B, 0, conventions="CS-NOT-REGISTERED-FOR-TEST@1")
        self.assertEqual((conventions.outcome, conventions.diagnosis.category), (D.REJECTED, D.INVALID_INPUT))
        self.assertTrue(all(v is None or v.to_dict()["role"] == "observer" for v in (deck.view_for(x) for x in VIEWERS)))


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("submit", "start_game", "HostedGame", "view_for", "VerifierReport", "DIAGNOSTIC_UNMAPPED", "build_diagnostic_catalog.py"):
            self.assertIn(needle, text)

    def test_spec_records_only_the_adopted_policies(self):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        adopted = {d["id"] for d in spec["decisions"] if d["status"] == "adopted"}
        self.assertEqual(adopted, {"D-MESSAGE", "D-REJECTED", "D-POSTGAME", "D-STATE-INTEGRITY-VIEW"})
        for d in spec["decisions"]:
            if d["id"] not in adopted:
                self.assertEqual(d["status"], "pending", d["id"])
        self.assertEqual(spec["approval"], "not_approved")


if __name__ == "__main__":
    unittest.main()

"""検証用 AI の試験の方策 rules-v9 のテスト（docs/tr8-rainbow-as-basic-energy-stop-analysis.md 8 章・docs/tr8-rules-v9-refused-input-experiment.md）。

rules-v9 は rules-v8 に、submit の拒否のうち公開の結果の分類が未裁定で continuable のものを、同じ主体・同じエピソード（局面）の (候補, 入力の意味の署名) で
記録し、拒否済みの入力を除いた作れる入力から選び、作れる入力がすべて拒否済みの候補を順位 8 にする規則を加える。エンジンの拒否（RB3）・judge・停止方針は
変えない。構築盤面（エンジンの状態から始める ``FixtureRunner``）で、RB3 で拒否される場面を作り、次を確かめる。
v0.199 から、ミュウツー（PR1-022）の［エナジーコントロール］は場のレインボーエネルギーを選べるものから外すので RB3 で止まらない
（docs/energy-control-rainbow-v0.199.md）。0.199.0 の盤面は、今も RB3 で止まるミュウ（SI-004）の［レインボーウェーブ］（ついているのがレインボーエネルギーだけ。
入力 1 つ）と、わるいレアコイル（PMCG4-030）の［じりょくせん］（相手の対戦ポケモンにレインボーエネルギー・控えあり。同じ候補に［ソニックブーム］）にした。

- ① 入力が 1 つの RB3 のワザが拒否されたあと、通常の順位で別の候補（にげる）を送り、受理される。拒否の前後で状態・確かめの値・乱数・公開の更新が変わらず、
  拒否の通知は送った本人への応答だけ
- ② 同じ候補（ワザの宣言）の別の入力（ソニックブーム）が残り、受理される。候補は下げない
- ③ 別の手が受理されて局面が変わると、以前の拒否を引き継がず、同じワザを通常の順位で評価し直す（もう一度送って拒否される）
- ④ 別の手がない（試験の中で API の候補の応答から拒否される候補以外を外した。メインの段では番の終わりが必ずあるので、エンジンの盤面では作れない）と、
  拒否済みの入力を送り直さず、既存の上限（draws_per_position）の no_progress で終わる
- 記録しない拒否（未裁定でない・続けられない）、同じワザの別の宣言入力（合成した段の組。エンジンの盤面は見つからなかった）、rules-v2〜rules-v8 の列が
  基点と同じで、拒否のない局では rules-v9 の列が rules-v8 と同じこと
"""

from __future__ import annotations

import dataclasses
import unittest

from kyuura_engine import conventions as C
from kyuura_engine import diagnostics as D
from kyuura_engine.replay_record import checks
from tests.helpers import build_test_state
from tests.test_verification_ai_rules_v3 import V2_GOLDEN, small
from tools.verification_ai import batch as B
from tools.verification_ai import records as R
from tools.verification_ai import runner as V
from tools.verification_ai.fixtures_observe import FixtureRunner
from tools.verification_ai.policies import (REFUSED_ALL, REFUSED_INPUT_AVOIDANCE, REFUSED_RANK, RULES9_DISTRIBUTION, RULING_UNRESOLVED,
                                            EnergyTransProgressRulePolicy, RefusedInputRulePolicy, RulePolicy, candidate_identity)

MEW, DARK_MAGNETON, MAGNEMITE, BUL, P, G, F, L, DCE, RAINBOW, POTION = ("SI-004", "PMCG4-030", "PMCG1-036", "PMCG1-001", "PMCG1-101", "PMCG1-097", "PMCG1-102",
                                                                      "PMCG1-100", "PMCG1-096", "PMCG4-065", "PMCG1-071")
RB3 = "UNRESOLVED_RAINBOW_AS_BASIC_ENERGY_CARD"
ALLOWED = frozenset({"supported", "may_stop_later"})


def board_state(seat0, seat1):
    s = build_test_state([seat0, seat1], turn_number=7)
    return dataclasses.replace(s, conventions=C.registered_identity(C.parse_key("CS-KYUURA-PLAY-TR8@1")))


def side(active, bench=(), hand=()):
    return {"active": active, "bench": list(bench), "hand": list(hand), "deck": [F] * 10, "prizes": 6}


# 相手（主体 1）: バトル場にエネルギーなし、ベンチに無色2個エネルギーとレインボーエネルギー（seed 9083 の局面と同じ形）
OPPONENT = side({"card": BUL}, [{"card": BUL}])
RAINBOW_ACTIVE = side({"card": BUL, "energy": [RAINBOW]}, [{"card": BUL}])  # じりょくせんの RB3（相手の対戦ポケモンのレインボーエネルギー・控えあり）
B1 = (side({"card": MEW, "energy": [RAINBOW]}, [{"card": BUL}]), OPPONENT)  # ①: レインボーウェーブだけ（入力 1 つ）・にげる（0 個）・番の終わり
B2 = (side({"card": DARK_MAGNETON, "energy": [L, L], "evolved_from": MAGNEMITE}), RAINBOW_ACTIVE)  # ②: ソニックブームとじりょくせん（同じ候補の 2 つの入力）・番の終わり
B3 = (side({"card": MEW, "energy": [RAINBOW], "damage": 10}, hand=[POTION]), OPPONENT)  # ③: きずぐすり（受理で局面が変わる）・番の終わり


def attempts(result, actor=0):
    return [e for e in result["trace"] if e.get("type") == "attempt" and e.get("actor") == actor]


def outcome(e):
    return (e.get("submit") or {}).get("outcome")


def name_of(e):
    return [m["option"].get("name_ja") for m in e.get("meaning") or [] if m.get("stage") == 1 and "option" in m]


def run_board(spec, version, seed=1, until=None, wrap=None, limits=None):
    cfg = V.Config(policy="rules", rules_version=version, policy_seed=seed, host_seed=seed, profile="deep",
                   limits=limits or V.Limits(operations=40, accepted=20, turns=2, seconds=60.0), run_id=f"t9-{version}-{seed}")
    runner = FixtureRunner(board_state(*spec), cfg, until=until or (lambda r, e: r.game.state.current_player != 0),
                           **({"wrap_endpoint": wrap} if wrap else {}))
    return runner, runner.run()


class Board1Test(unittest.TestCase):
    """①: 入力が 1 つの RB3 のワザの拒否のあと、別の候補（にげる）を送って受理される。"""

    def test_v9_moves_to_retreat_and_v8_loops(self):
        for seed in (1, 2, 3, 4):
            _r, v9 = run_board(B1, 9, seed)
            a = attempts(v9)
            refused = [e for e in a if outcome(e) == "rejected"]
            self.assertEqual(len(refused), 1, seed)
            e = refused[0]
            self.assertEqual((name_of(e), e["submit"]["result"]["diagnostic_id"], e["submit"]["result"]["category"], e["submit"]["result"]["continuable"]),
                             (["レインボーウェーブ"], RB3, RULING_UNRESOLVED, True), seed)
            self.assertEqual(e["refused_input"], {"result": "recorded", "refused_for_candidate": 1, "buildable": 1, "remaining": 0, "all_refused": True})
            after = a[a.index(e) + 1]
            self.assertEqual((after["candidate"]["kind"], after["build"], outcome(after)), ("retreat", "ok", "accepted"), seed)
            self.assertIn(f":refused_excluded1", after["candidate_reason"])
            self.assertEqual(sum(1 for x in a if x["build"] == "ok_already_tried"), 0, seed)
            self.assertEqual(v9["anomalies"], [], seed)
            _r, v8 = run_board(B1, 8, seed)
            a8 = attempts(v8)
            self.assertEqual(sum(1 for x in a8 if outcome(x) == "rejected"), 1, seed)
            self.assertEqual(sum(1 for x in a8 if x["build"] == "ok_already_tried"), 63, seed)
            self.assertEqual((v8["termination"]["class"], v8["termination"]["detail"]["reason"]), ("no_progress", "draws_per_position"), seed)
            all8 = [x for x in v8["trace"] if x.get("type") == "attempt"]
            k = next(i for i, x in enumerate(all8) if outcome(x) == "rejected") + 1
            self.assertEqual(R.action_sequence(v8["trace"])[:k], R.action_sequence(v9["trace"])[:k], seed)  # 拒否までの試みの列は rules-v8 と同じ

    def test_refusal_rewinds_and_is_told_only_to_the_submitter(self):
        seen = []
        holder = {}

        class Spy:
            def __init__(self, actor, endpoint):
                self.actor, self.endpoint = actor, endpoint

            def handle(self, req):
                runner = holder.get("runner")
                if runner is None or req.get("type") != "submit":
                    return self.endpoint.handle(req)
                game, hub = runner.game, runner.hub
                before = (game.state, checks(game.state), hub._seq, {k: len(v) for k, v in hub._outbox.items()}, len(game.state.log), game.state.rng.getstate())
                out = self.endpoint.handle(req)
                after = (game.state, checks(game.state), hub._seq, {k: len(v) for k, v in hub._outbox.items()}, len(game.state.log), game.state.rng.getstate())
                if (out.get("outcome")) == D.REJECTED:
                    seen.append((before == after, self.actor, (out.get("result") or {}).get("role"), (out.get("result") or {}).get("viewer")))
                return out
        cfg = V.Config(policy="rules", rules_version=9, policy_seed=1, host_seed=1, profile="deep",
                       limits=V.Limits(operations=40, accepted=20, turns=2, seconds=60.0), run_id="t9-rewind")
        runner = FixtureRunner(board_state(*B1), cfg, wrap_endpoint=lambda actor, endpoint: Spy(actor, endpoint),
                               until=lambda r, e: r.game.state.current_player != 0)
        holder["runner"] = runner
        result = runner.run()
        self.assertEqual(seen, [(True, 0, "actor", 0)])  # 状態・確かめの値・更新の番号・送り先ごとの更新・ログ・乱数が同じ。通知は本人（主体 0）の応答だけ
        self.assertEqual(result["anomalies"], [])  # update_after_rejection・state_changed_on_rejection なし


class Board2Test(unittest.TestCase):
    """②: 同じ候補の別の入力（ソニックブーム）が残り、受理される。"""

    def test_other_input_of_the_same_candidate(self):
        for seed in (1, 2, 3, 4):
            _r, v9 = run_board(B2, 9, seed, until=lambda r, e: e.get("actor") == 0 and outcome(e) == "accepted")
            a = attempts(v9)
            names = [(name_of(e), outcome(e) or e["build"]) for e in a if e["candidate"]["kind"] == "use_attack"]
            first = next(i for i, x in enumerate(names) if x[1] == "rejected") if any(x[1] == "rejected" for x in names) else None
            if first is None:  # 最初にソニックブームを選んだ（拒否なし）
                self.assertEqual(names[-1], (["ソニックブーム"], "accepted"), seed)
                continue
            self.assertEqual(names[first], (["じりょくせん"], "rejected"), seed)
            self.assertEqual(names[first + 1], (["ソニックブーム"], "accepted"), seed)
            e = [x for x in a if outcome(x) == "rejected"][0]
            self.assertEqual((e["refused_input"]["buildable"], e["refused_input"]["remaining"], e["refused_input"]["all_refused"]), (2, 1, False))
            nxt = a[a.index(e) + 1]
            self.assertEqual((nxt["refused_filter"]["result"], nxt["refused_filter"]["remaining"]), ("chosen_from_remaining", 1))
            self.assertNotIn("refused_excluded", nxt["candidate_reason"])  # 候補は下げない
            self.assertEqual(v9["anomalies"], [], seed)

    def test_seeds_reach_the_refusal(self):
        """4 つの seed のどれかで、拒否のあとの別の入力の受理を通る（乱数の都合で最初にソニックブームを選ぶ seed は数えない）。"""
        hits = 0
        for seed in range(1, 9):
            _r, v9 = run_board(B2, 9, seed, until=lambda r, e: e.get("actor") == 0 and outcome(e) == "accepted")
            hits += any(outcome(e) == "rejected" for e in attempts(v9))
        self.assertGreater(hits, 0)


class Board3Test(unittest.TestCase):
    """③: 局面が変わると以前の拒否を引き継がず、評価し直す。"""

    def test_reevaluated_after_acceptance(self):
        for seed in (1, 2, 3, 4):
            _r, v9 = run_board(B3, 9, seed)
            a = attempts(v9)
            sent = [(x["candidate"]["kind"], outcome(x)) for x in a if outcome(x)]
            refusals = [i for i, x in enumerate(sent) if x[1] == "rejected"]
            self.assertGreaterEqual(len(refusals), 2, (seed, sent))
            self.assertEqual(sent[refusals[0] + 1], ("play_trainer", "accepted"), (seed, sent))  # 拒否のあと別の手（きずぐすり）
            self.assertEqual(sent[refusals[1]], ("use_attack", "rejected"), (seed, sent))  # 新しい局面で同じワザを送り直して拒否
            recs = [x["refused_input"] for x in a if outcome(x) == "rejected"]
            self.assertTrue(all(r["refused_for_candidate"] == 1 for r in recs), (seed, recs))  # 前の局面の記録を引き継がない
            episodes = [e for e in v9["trace"] if e.get("type") == "episode" and e.get("actor") == 0]
            self.assertTrue(any(e.get("refused_inputs_cleared") == 1 for e in episodes), seed)
            self.assertEqual(sent[-1], ("end_turn", "accepted"), (seed, sent))
            self.assertEqual(sum(1 for x in a if x["build"] == "ok_already_tried"), 0, seed)
            self.assertEqual(v9["anomalies"], [], seed)


def only_refused_attack(actor, endpoint):
    """④（試験の中だけ）: 主体 0 の候補の応答から use_attack 以外を外す（番の終わり・にげるがない場面を作る。エンジンの盤面では作れない）。"""
    class Only:
        def handle(self, req):
            out = endpoint.handle(req)
            if actor == 0 and req.get("type") == "candidates" and out.get("ok"):
                out["response"]["candidates"] = [c for c in out["response"]["candidates"] if c["kind"] == "use_attack"]
            return out
    return Only()


class Board4Test(unittest.TestCase):
    """④: 別の手がなければ、拒否済みの入力を送り直さず、既存の上限で終わる。"""

    def test_no_alternative_ends_without_resending(self):
        _r, v9 = run_board(B1, 9, 1, wrap=only_refused_attack)
        a = attempts(v9)
        self.assertEqual(sum(1 for x in a if "submit" in x), 1)
        self.assertEqual(sum(1 for x in a if "check" in x), 1)
        rest = a[1:]  # 順位 8 の候補しかなく選ばれるが、組み立ての前の列挙で全部が拒否済みなので組み立てず、check・submit をしない
        self.assertTrue(rest and all(x["build"] == REFUSED_ALL and ":refused_no_alternative" in x["candidate_reason"] for x in rest))
        self.assertEqual((len(rest), sum(1 for x in a if x["build"] == "ok_already_tried")), (63, 0))
        self.assertEqual((v9["termination"]["class"], v9["termination"]["detail"]["reason"], v9["termination"]["detail"]["rejections"]),
                         ("no_progress", "draws_per_position", 1))
        self.assertEqual(v9["anomalies"], [])


class PolicyUnitTest(unittest.TestCase):
    def test_category_constant_and_records(self):
        self.assertEqual(RULING_UNRESOLVED, D.RULING_UNRESOLVED)
        p = RefusedInputRulePolicy("s")
        p.begin_episode()
        c = {"id": "c3", "kind": "use_attack"}
        self.assertEqual(p.input_refused(c, "x", {"category": "illegal", "continuable": True}, ["x"])["result"], "not_recorded")
        self.assertEqual(p.input_refused(c, "x", {"category": RULING_UNRESOLVED, "continuable": False}, ["x"])["result"], "not_recorded")
        self.assertEqual(p.refused_signatures(c), frozenset())
        r = p.input_refused(c, "x", {"category": RULING_UNRESOLVED, "continuable": True}, None)
        self.assertEqual((r["result"], r["all_refused"]), ("recorded", None))  # 列挙できなければ候補は下げない
        self.assertEqual(p.refused_signatures({"id": "c7", "kind": "use_attack"}), frozenset({"x"}))  # 番号が振り直されても同じ候補
        ranks, _p, note = p._adjust_ranks([c, {"id": "c1", "kind": "end_turn"}], [4, 6], "rule7")
        self.assertEqual((ranks, note), ([4, 6], ""))
        p.mark_refused_all({"id": "c9", "kind": "use_attack"})
        ranks, _p, note = p._adjust_ranks([c, {"id": "c1", "kind": "end_turn"}], [4, 6], "rule7")
        self.assertEqual((ranks, note), ([REFUSED_RANK, 6], ":refused_excluded1"))
        info = p.begin_episode()
        self.assertEqual((info.get("refused_inputs_cleared"), p.refused_signatures(c)), (1, frozenset()))

    def test_filter_keeps_other_declaration_inputs(self):
        """同じワザの別の宣言入力（合成した段: ワザ 1 つ・宣言といっしょに選ぶもの 0〜1 個）。拒否済みの組だけを外し、残りから選ぶ。"""
        stages = [{"stage": 1, "input": "choose_option", "count": {"min": 1, "max": 1}, "order": "not_applicable",
                   "options": [{"id": "o1", "name_ja": "わざ", "processability": "may_stop_later"}]},
                  {"stage": 2, "input": "choose_option", "count": {"min": 0, "max": 1}, "depends_on_stage": 1, "order": "significant",
                   "options": [{"id": "d1", "name_ja": "いっしょ", "processability": "may_stop_later"}], "options_by_choice": {"o1": [{"option": "d1"}]}}]
        cand = {"id": "c3", "kind": "use_attack"}
        tuples, why = V.Runner._input_tuples(cand, stages, ALLOWED)
        self.assertEqual((len(tuples), why), (2, None))
        p = RefusedInputRulePolicy("s")
        p.begin_episode()
        refused = tuples[0][2]
        r = p.input_refused(cand, refused, {"category": RULING_UNRESOLVED, "continuable": True}, [s for _c, _m, s in tuples])
        self.assertEqual((r["buildable"], r["remaining"], r["all_refused"]), (2, 1, False))
        entry = {}
        choices, picks, meaning = V.Runner._refused_filter(V.Runner, cand, stages, ALLOWED, p.refused_signatures(cand), None, p, None, entry)
        self.assertEqual((choices, meaning), (tuples[1][0], tuples[1][1]))
        self.assertEqual((entry["refused_filter"]["result"], picks), ("chosen_from_remaining", []))
        p.input_refused(cand, tuples[1][2], {"category": RULING_UNRESOLVED, "continuable": True}, [s for _c, _m, s in tuples])
        self.assertEqual(V.Runner._refused_filter(V.Runner, cand, stages, ALLOWED, p.refused_signatures(cand), None, p, None, {}), REFUSED_ALL)
        self.assertIsNone(V.Runner._refused_filter(V.Runner, cand, stages, ALLOWED, p.refused_signatures(cand), frozenset(), p, None, {}))  # 制限があれば今までどおり


class RunnerAndBatchTest(unittest.TestCase):
    def test_make_policies_and_batch_records(self):
        result = V.run_game(small(policy="rules", rules_version=9, limits={"operations": 120}))
        p0 = result["policies"]["0"]
        self.assertEqual((p0["name"], p0["version"], p0["distribution"], p0["repeat_threshold"]), ("rules", 9, RULES9_DISTRIBUTION, 2))
        self.assertEqual(p0["loop"]["refused_input_avoidance"], REFUSED_INPUT_AVOIDANCE)
        for policy in V.make_policies(small(policy="rules", rules_version=9)).values():
            if policy.name == "rules":
                self.assertIsInstance(policy, RefusedInputRulePolicy)
        for version in (2, 3, 4, 5, 6, 7, 8):
            for policy in V.make_policies(small(policy="rules", rules_version=version)).values():
                self.assertFalse(isinstance(policy, RefusedInputRulePolicy) or hasattr(policy, "input_refused"))
        with self.assertRaises(ValueError):
            RulePolicy("s", version=9)
        self.assertEqual(B.MODES["rules-v9"], {"policy": "rules", "rules_version": 9, "repeat_threshold": 2})
        self.assertEqual(B.MODES["rules-v8"], {"policy": "rules", "rules_version": 8, "repeat_threshold": 2})
        self.assertIsInstance(RefusedInputRulePolicy("s"), EnergyTransProgressRulePolicy)
        adapter = B.EngineAdapter()
        v9 = adapter.policies_of(small(policy="rules", rules_version=9))
        v8 = adapter.policies_of(small(policy="rules", rules_version=8))
        self.assertEqual((v9["0"]["version"], v9["0"]["refused_input_avoidance"]), (9, REFUSED_INPUT_AVOIDANCE))
        self.assertNotIn("refused_input_avoidance", v8["0"])
        self.assertEqual(B.TOOL_VERSION, 21)
        self.assertEqual(candidate_identity({"id": "c1", "kind": "end_turn"}), candidate_identity({"id": "c5", "kind": "end_turn"}))


# rules-v6〜rules-v8 の列（基点 10e203d の道具で求めた値。rules-v9 の追加で変わらないこと。拒否のない局なので rules-v9 は rules-v8 と同じ列）
BASE_SEQUENCES = {("rules-v2-s13", 6): (352, "0b15ec368b0c13fd84b13b8c33e4500df847d3f383a8c0bb976e153e858e7752"),
                  ("rules-v2-s13", 7): (272, "63690f203d9db8b3f4f95adc056e33785d5a321165bad9dfbbf7bee45d9d6efc"),
                  ("rules-v2-s13", 8): (207, "cad49b2091e13b99bebe9d145aa945ec7ec274aa40c2f954c0a6208ac42b0104"),
                  ("rules-v2-l67u-s9023", 6): (185, "4fb6dcae64112c3f8c9525cf1566ebef564cdd835e6b0e302d5697d1035941e8"),
                  ("rules-v2-l67u-s9023", 7): (322, "243b4703572502e7c611b0e9493d5f83ed5f981e46bc44e965c54b5c20cdf98e"),
                  ("rules-v2-l67u-s9023", 8): (322, "243b4703572502e7c611b0e9493d5f83ed5f981e46bc44e965c54b5c20cdf98e")}


class SequenceTest(unittest.TestCase):
    def test_existing_policies_unchanged_and_v9_equal_without_refusals(self):
        for name in ("rules-v2-s13", "rules-v2-l67u-s9023"):
            kw, _golden, _swaps = V2_GOLDEN[name]
            for v in (6, 7, 8, 9):
                run = V.run_game(V.Config(policy="rules", rules_version=v, **kw))
                d = R.sequence_digest(R.action_sequence(run["trace"]), R.ACTION_FORMAT)
                self.assertEqual((d["length"], d["sha256"]), BASE_SEQUENCES[(name, min(v, 8))], (name, v))
                self.assertEqual(run["anomalies"], [], (name, v))


if __name__ == "__main__":
    unittest.main()

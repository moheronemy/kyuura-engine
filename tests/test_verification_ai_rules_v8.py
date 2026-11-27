"""検証用 AI の試験の方策 rules-v8 のテスト（docs/tr8-energy-trans-progress-policy-design.md・docs/tr8-energy-trans-progress-policy-experiment.md）。

rules-v8 は rules-v7 に、既存の順位で［エナジートランス］を選んだあとの入力を、バトル場のワザ・「にげる」の費用を満たす組（優先 1）・到達できる費用の不足を
減らす組（優先 2）から選ぶ規則を加える。小さな JSON の観測・段で、支払いの規則（色と無色・二重に数えない・にげるの組）、優先の段、rules-v6 の除外との関係
（到達は除外の前、選ぶのは除外のあと）、D4（払える費用を保つ）、D5（特殊エネルギー）、評価しない場合（観測なし・単位が決まらない・ねむり・マヒ・
にげるの inputs がない）、ランナーの読み取り専用の取得（状態・乱数・ログを変えない）・再利用、バッチの記録、rules-v2〜rules-v7 の列が変わらないことを確かめる。
"""

from __future__ import annotations

import dataclasses
import unittest

from kyuura_engine import conventions as C
from kyuura_engine.cards import EnergyType, can_pay_with_units
from kyuura_engine.replay_record import checks
from tests.helpers import build_test_state
from tests.test_verification_ai_rules_v3 import V2_GOLDEN, end_turn, small
from tests.test_verification_ai_rules_v6 import et
from tools.verification_ai import batch as B
from tools.verification_ai import records as R
from tools.verification_ai import runner as V
from tools.verification_ai.fixtures_observe import FixtureRunner
from tools.verification_ai.policies import (DEFER_ALL, ENERGY_TRANS_PROGRESS, RULES8_DISTRIBUTION, EnergyTransProgressRulePolicy, RetreatDeferralRulePolicy,
                                            RulePolicy, can_pay_units, retreat_payable)

VEN, BUL, IVY, TAN, G, F, HIT, DCE = "PMCG1-011", "PMCG1-001", "PMCG1-008", "PMCG1-007", "PMCG1-097", "PMCG1-102", "PMCG1-058", "PMCG1-096"
CARDS = V.progress_card_table()


def mon(pid, card_id=VEN, energy=(), status=(), units=None, determined=True, attacks=None, form="printed"):
    """本人の場のポケモン。energy は (カードの番号, カード ID) の並び。"""
    cards = [{"card": c, "card_id": cid} for c, cid in energy]
    units = units if units is not None else [[CARDS[cid]["provides"]] for _c, cid in energy]
    attacks = attacks if attacks is not None else [{"card": 900 + pid, "card_id": card_id, "attack_index": i, "route": "form", "provider": None, "problem": None}
                                                   for i in range(len(CARDS[card_id]["attacks"]))]
    return {"pokemon_id": pid, "card_id": card_id, "energy": cards, "energy_units": units, "energy_units_determined": determined,
            "special_conditions": list(status), "form": {"kind": form, "card_id": card_id}, "attacks": attacks}


def view(active, bench=(), ok=True):
    me = {"player": 0, "active": active, "bench": list(bench)}
    return {"ok": ok, "type": "view", "viewer": 0, "status": {"segment": 0}, "observation": {"turn": 7, "viewer": 0, "players": [me, {"player": 1}]}}


def et_stages(moves):
    """［エナジートランス］の inputs の 3 段（移動元 → エネルギー → 移動先）。moves は (移動元, エネルギーのカードの番号, カード ID, 移動先) の並び。"""
    sources = sorted({m[0] for m in moves})
    energies = sorted({(m[0], m[1], m[2]) for m in moves})
    s1 = {"stage": 1, "input": "choose_option", "role": "source", "count": {"min": 1, "max": 1}, "options": [{"id": f"s{s}", "pokemon": s} for s in sources]}
    s2 = {"stage": 2, "input": "choose_option", "role": "energy", "count": {"min": 1, "max": 1}, "depends_on_stage": 1,
          "options": [{"id": f"e{c}", "card": c, "card_id": cid} for _s, c, cid in energies],
          "options_by_choice": {f"s{s}": [{"option": f"e{c}"} for s2_, c, _cid in energies if s2_ == s] for s in sources}}
    targets = sorted({m[3] for m in moves})
    s3 = {"stage": 3, "input": "choose_option", "role": "target", "count": {"min": 1, "max": 1}, "depends_on_stage": 2,
          "options": [{"id": f"t{t}", "pokemon": t} for t in targets],
          "options_by_choice": {f"e{c}": [{"option": f"t{t}"} for s, c2, _cid, t in moves if c2 == c] for _s, c, _cid in energies}}
    return [s1, s2, s3]


def retreat_item(cards_units, total, status="ok"):
    """同じ応答の「にげる」の inputs（評価用）。cards_units はバトル場のカードの番号 → 単位の数。"""
    discard = {"stage": 2, "role": "discard", "input": "choose_option", "count": {"min": 0, "max": len(cards_units)}, "total_units": {"min": total, "max": total},
               "options": [{"id": f"o{c}", "card": c, "units": u} for c, u in cards_units.items()]}
    return {"candidate": {"id": "c9", "kind": "retreat"}, "stages": [{"stage": 1, "role": "new_active"}, discard], "status": status, "source": "fetched"}


def run_policy(v, stages, items=(), policy=None, excluded=None):
    p = policy or EnergyTransProgressRulePolicy("s", cards=CARDS)
    p.observe_view(v, 0)
    p.begin_episode()
    if excluded is not None:  # rules-v6 の後回しの組を外から与える（入力の制限の結果だけを差し替える）
        p._et_deferred = {(p._sig, *m) for m in excluded}
    p.progress_retreat_inputs(list(items))
    restriction = p.input_restriction(et(), stages, frozenset({"supported", "may_stop_later"}))
    return p, restriction


def allowed_after(stages, restriction):
    from tools.verification_ai.actions import transfer_moves
    moves = transfer_moves(stages)
    return moves if restriction is None else moves - restriction


class PaymentTest(unittest.TestCase):
    def test_attack_assignment_matches_the_engine(self):
        cases = [(["grass", "colorless"], [["grass"]]), (["grass", "colorless"], [["grass"], ["grass"]]), (["grass", "colorless"], [["colorless"], ["colorless"]]),
                 (["fighting", "colorless"], [["grass"], ["grass"]]), (["colorless", "colorless"], [["colorless"], ["colorless"]]),
                 (["grass", "grass"], [["grass", "fire"], ["fire"]]), (["grass", "fire"], [["grass", "fire"], ["grass"]]), (["grass"] * 4, [["grass"]] * 3)]
        for cost, units in cases:
            want = can_pay_with_units([EnergyType(c) for c in cost], [frozenset(EnergyType(x) for x in u) for u in units])
            self.assertEqual(can_pay_units(cost, units), want, (cost, units))
        self.assertFalse(can_pay_units(["grass", "colorless"], [["grass"]]))  # 色の記号と無色を同じ 1 個で二重に払わない
        self.assertFalse(can_pay_units(["fighting"], [["colorless"], ["colorless"]]))  # 無色は色の記号を払えない

    def test_retreat_needs_a_payment_set(self):
        self.assertTrue(retreat_payable((2, 2), [1, 1]))
        self.assertFalse(retreat_payable((1, 1), [2]))  # 2 個のカードは分けない
        self.assertTrue(retreat_payable((3, 3), [2, 1]))
        self.assertTrue(retreat_payable((0, 0), []))
        self.assertFalse(retreat_payable((3, 3), [2, 2]))  # 合計 4 は足りるが、ちょうど 3 の組がない


E1_MOVES = ([(3, c, G, t) for c in (31, 32, 33) for t in (1, 4, 5, 6, 7)] + [(4, c, G, t) for c in (41, 42, 43) for t in (1, 3, 5, 6, 7)]
            + [(5, 51, G, t) for t in (1, 3, 4, 6, 7)])


class TierTest(unittest.TestCase):
    def test_e1_type_moves_onto_the_active_are_tier2(self):
        """9056 の n124 の型: 35 組のうち、バトル場（フシギバナ・草 0）への 7 組が優先 2（にげるの不足 2・ソーラービームの不足 4）。"""
        v = view(mon(1, VEN), [mon(3, BUL, [(c, G) for c in (31, 32, 33)]), mon(4, BUL, [(c, G) for c in (41, 42, 43)]), mon(5, TAN, [(51, G)])])
        st = et_stages(E1_MOVES)
        p, restriction = run_policy(v, st, [retreat_item({}, 2)])
        rec = p.last_progress
        self.assertEqual((rec["result"], rec["moves"], rec["tier_sizes"], rec["chosen_set"], rec["restricted"]), ("tier2", 35, [0, 7, 28], 7, True))
        self.assertEqual(allowed_after(st, restriction), frozenset((s, c, 1) for s, c, _g, t in E1_MOVES if t == 1))
        self.assertEqual({g["kind"]: g["deficit"] for g in rec["goals"]}, {"retreat": 2, "attack": 4})

    def test_tier1_completes_a_goal_and_tier3_falls_back(self):
        v = view(mon(1, VEN, [(11, G)]), [mon(3, BUL, [(31, G)])])
        st = et_stages([(3, 31, G, 1), (1, 11, G, 3)])
        p, restriction = run_policy(v, st, [retreat_item({11: 1}, 2)])
        self.assertEqual(p.last_progress["result"], "tier1")
        self.assertEqual(allowed_after(st, restriction), frozenset({(3, 31, 1)}))
        # E5 の型: 草の合計 1 < にげる 2、払えるワザなし → 到達不能で優先 3、絞らない（rules-v7 と同じ選び方）
        v5 = view(mon(1, VEN), [mon(3, BUL), mon(4, TAN, [(41, G)])])
        st5 = et_stages([(4, 41, G, 1), (4, 41, G, 3)])
        p5, r5 = run_policy(v5, st5, [retreat_item({}, 2)])
        self.assertEqual((p5.last_progress["result"], p5.last_progress["state"], p5.last_progress["restricted"], r5), ("tier3", "unreachable", False, None))

    def test_reachability_before_the_rules_v6_exclusion(self):
        """到達は rules-v6 の除外の前の全組で判定し、選ぶのは除外のあとの組から（外した組は選ばない）。"""
        v = view(mon(1, VEN), [mon(3, BUL, [(31, G)]), mon(4, BUL, [(41, G)])])
        st = et_stages([(3, 31, G, 1), (4, 41, G, 1), (3, 31, G, 4)])
        p, restriction = run_policy(v, st, [retreat_item({}, 2)], excluded={(4, 41, 1)})
        rec = p.last_progress
        self.assertEqual((rec["result"], rec["excluded_v6"], rec["choosable"]), ("tier2", 1, 2))
        self.assertEqual({g["kind"]: g["deficit"] for g in rec["goals"]}["retreat"], 2)  # 除外した組のカードも到達の判定に数える
        self.assertEqual(allowed_after(st, restriction), frozenset({(3, 31, 1)}))

    def test_defer_all_passes_through(self):
        v = view(mon(1, VEN), [mon(3, BUL, [(31, G)])])
        st = et_stages([(3, 31, G, 1)])
        p, restriction = run_policy(v, st, [retreat_item({}, 2)], excluded={(3, 31, 1)})
        self.assertEqual(restriction, DEFER_ALL)
        self.assertIsNone(p.last_progress)

    def test_d4_keeps_a_payable_cost(self):
        """D4: にげるが払え、ワザに届かない（優先 3）。払える費用を保つ組（ベンチの間）があれば、バトル場から外す組を選ばない。"""
        v = view(mon(1, BUL, [(11, G)], attacks=[]), [mon(3, IVY, [(31, G)]), mon(4, TAN)])
        st = et_stages([(1, 11, G, 3), (3, 31, G, 4)])
        p, restriction = run_policy(v, st, [retreat_item({11: 1}, 1)])
        rec = p.last_progress
        self.assertEqual((rec["result"], rec["state"], rec["d4"], rec["restricted"]), ("tier3", "goal_met_only", "kept", True))
        self.assertEqual(allowed_after(st, restriction), frozenset({(3, 31, 4)}))
        # 保つ組がなければ、その段の組を残す
        st2 = et_stages([(1, 11, G, 3)])
        p2, r2 = run_policy(v, st2, [retreat_item({11: 1}, 1)])
        self.assertEqual((p2.last_progress["d4"], r2), ("none_keep", None))

    def test_c1_colour_symbol_unreachable_with_grass(self):
        """C1: 闘の記号のワザ（ワンリキー）。草は無色だけを払い、色の記号には届かない → そのワザで優先 2 にしない。"""
        mac = "PMCG1-053"
        v = view(mon(1, mac), [mon(3, BUL, [(31, G), (32, G)])])
        st = et_stages([(3, 31, G, 1), (3, 32, G, 1)])
        p, restriction = run_policy(v, st)  # にげるの候補なし: ワザの目標だけ
        self.assertEqual((p.last_progress["result"], p.last_progress["state"], restriction), ("tier3", "unreachable", None))
        self.assertIsNone(p.last_progress["goals"][0]["deficit"])

    def test_c2_special_energy_on_the_active(self):
        """C2: バトル場に無色2個エネルギー（2 個）。ワザは評価しない。にげるは inputs のカードごとの単位で評価する（まとめた単位だけで段を付けない）。"""
        v = view(mon(1, TAN, [(11, DCE)], units=[["colorless"], ["colorless"]]), [mon(3, BUL, [(31, G)])])
        st = et_stages([(3, 31, G, 1)])
        p, restriction = run_policy(v, st)
        self.assertEqual(p.last_progress["result"], "unevaluable:no_evaluable_goal")
        self.assertEqual(p.last_progress["skipped"], {"attack_special_energy_on_active": 2})
        self.assertIsNone(restriction)
        # にげる 3: 無色2個（2）+ 草 1 でちょうど 3 → 優先 1。DCE だけでは 3 にならない
        p3, r3 = run_policy(v, st, [retreat_item({11: 2}, 3)])
        self.assertEqual(p3.last_progress["result"], "tier1")

    def test_c3_c4_and_missing_inputs_fall_back(self):
        st = et_stages([(3, 31, G, 1)])
        bench = [mon(3, BUL, [(31, G)])]
        for v, why in ((view(mon(1, VEN), bench, ok=False), "view_unavailable"), (view(mon(1, VEN, determined=False), bench), "active_units_undetermined"),
                       (view(mon(1, VEN, status=["sleep"]), bench), "sleep_or_paralysis"), (view(mon(1, VEN, status=["paralysis"]), bench), "sleep_or_paralysis")):
            p, restriction = run_policy(v, st, [retreat_item({}, 2)])
            self.assertEqual((p.last_progress["result"], restriction), ("unevaluable:" + why, None), why)
        for status in ("withheld", "inputs_refused"):
            p, restriction = run_policy(view(mon(1, VEN, attacks=[]), bench), st, [retreat_item({}, 2, status=status)])
            self.assertEqual((p.last_progress["result"], restriction), ("unevaluable:no_evaluable_goal", None), status)
        # 写したワザ・供給するポケモンのあるワザは評価しない
        copied = [{"card": 9, "card_id": BUL, "attack_index": 0, "route": "form", "provider": None, "problem": None}]
        p, _r = run_policy(view(mon(1, VEN, attacks=copied), bench), st)
        self.assertEqual(p.last_progress["skipped"], {"attack_not_own_printed": 1})
        provider = [{"card": 9, "card_id": VEN, "attack_index": 0, "route": "form", "provider": 4, "problem": None}]
        p, _r = run_policy(view(mon(1, VEN, attacks=provider), bench), st)
        self.assertEqual(p.last_progress["skipped"], {"attack_provider_payer_or_problem": 1})

    def test_moved_card_not_basic_is_unevaluable(self):
        v = view(mon(1, VEN), [mon(3, BUL, [(31, DCE)], units=[["colorless"], ["colorless"]])])
        p, restriction = run_policy(v, et_stages([(3, 31, DCE, 1)]), [retreat_item({}, 2)])
        self.assertEqual((p.last_progress["result"], restriction), ("unevaluable:moved_card_not_basic", None))

    def test_other_candidates_and_versions_unchanged(self):
        p = EnergyTransProgressRulePolicy("s", cards=CARDS)
        p7 = RetreatDeferralRulePolicy("s")
        for q in (p, p7):
            q.observe_view(view(mon(1, VEN)), 0)
            q.begin_episode()
        for items in ([end_turn(), et()], [end_turn()], [et(), et("c5", 3)]):
            i8, r8 = p.choose("candidate", items, {})
            i7, r7 = p7.choose("candidate", items, {})
            self.assertEqual((i8, r8), (i7, r7))
        self.assertEqual((p.version, p.distribution, p.energy_trans_progress), (8, RULES8_DISTRIBUTION, ENERGY_TRANS_PROGRESS))


def board_state(spec):
    s = build_test_state([dict(x) for x in spec], turn_number=7)
    return dataclasses.replace(s, conventions=C.registered_identity(C.parse_key("CS-KYUURA-PLAY-TR8@1")))


def side(active, bench=()):
    return {"active": active, "bench": list(bench), "hand": [], "deck": [F] * 10, "prizes": 6}


E2 = [side({"card": VEN, "evolved_from": [BUL, IVY]}, [{"card": IVY, "evolved_from": BUL, "energy": [G]}, {"card": BUL, "energy": [G]}]), side({"card": HIT})]


class RunnerTest(unittest.TestCase):
    def _run(self, version, seed=1, wrap=None):
        cfg = V.Config(policy="rules", rules_version=version, policy_seed=seed, host_seed=seed, profile="deep",
                       limits=V.Limits(operations=200, accepted=80, turns=2, seconds=60.0), run_id=f"t8-{version}-{seed}")

        def until(r, e):
            return e.get("actor") == 0 and (e["candidate"]["kind"] in ("end_turn", "use_attack") or r.game.state.current_player != 0)
        runner = FixtureRunner(board_state(E2), cfg, until=until, **({"wrap_endpoint": wrap} if wrap else {}))
        return runner, runner.run()

    def test_fetch_is_read_only_and_not_a_selection(self):
        """D1: 評価用の inputs は読み取り専用（状態・確かめの値・公開の更新・ログを変えない）。方策の乱数を使わない。「にげる」の選択・送信に数えない。"""
        seen = []
        holder = {}

        class Spy:
            def __init__(self, actor, endpoint):
                self.actor, self.endpoint = actor, endpoint

            def handle(self, req):
                runner = holder.get("runner")
                if runner is None or req.get("type") != "inputs" or not runner._in_fetch:
                    return self.endpoint.handle(req)
                game, hub = runner.game, runner.hub
                before = (game.state, checks(game.state), hub._seq, {k: len(v) for k, v in hub._outbox.items()}, runner.policies[0]._rng.getstate())
                out = self.endpoint.handle(req)
                after = (game.state, checks(game.state), hub._seq, {k: len(v) for k, v in hub._outbox.items()}, runner.policies[0]._rng.getstate())
                seen.append(before == after)
                return out

        def wrap(actor, endpoint):
            return Spy(actor, endpoint)
        orig = FixtureRunner._progress_fetch

        def tracked(self, *a, **k):
            self._in_fetch = True
            rng = self.policies[0]._rng.getstate()
            try:
                return orig(self, *a, **k)
            finally:
                self._in_fetch = False
                seen.append(rng == self.policies[0]._rng.getstate())
        FixtureRunner._progress_fetch = tracked
        try:
            cfg = V.Config(policy="rules", rules_version=8, policy_seed=1, host_seed=1, profile="deep",
                           limits=V.Limits(operations=200, accepted=80, turns=2, seconds=60.0), run_id="t8-ro")
            runner = FixtureRunner(board_state(E2), cfg, wrap_endpoint=wrap,
                                   until=lambda r, e: e.get("actor") == 0 and (e["candidate"]["kind"] in ("end_turn", "use_attack") or r.game.state.current_player != 0))
            runner._in_fetch = False
            holder["runner"] = runner
            result = runner.run()
        finally:
            FixtureRunner._progress_fetch = orig
        self.assertTrue(seen and all(seen))
        attempts = [e for e in result["trace"] if e.get("type") == "attempt" and e.get("actor") == 0]
        fetches = [e["progress_fetch"] for e in attempts if "progress_fetch" in e]
        self.assertTrue(fetches)
        self.assertEqual(result["anomalies"], [])
        all_attempts = [e for e in result["trace"] if e.get("type") == "attempt"]
        selected_retreats = sum(1 for e in all_attempts if e["candidate"]["kind"] == "retreat")
        self.assertEqual(result["metrics"]["kinds"].get("retreat", {}).get("selected", 0), selected_retreats)  # 評価用の取得は「にげる」の選択に数えない
        self.assertEqual(result["counters"]["attempts"], len(all_attempts))
        sources = [i["source"] for f in fetches for i in f["items"]]
        self.assertIn("fetched", sources)
        self.assertTrue(all(s in ("fetched", "reused_fetched", "reused_attempt") for s in sources))

    def test_e2_retreat_payable_after_two_moves(self):
        """E2 の型: 1 回目は優先 2、2 回目は優先 1（にげる）。2 回の移動で「にげる」が払え、支払えない「にげる」の同じ条件での選び直しがない。"""
        for seed in (1, 2, 3, 4):
            _runner, result = self._run(8, seed)
            attempts = [e for e in result["trace"] if e.get("type") == "attempt" and e.get("actor") == 0]
            tiers = [e["energy_trans_progress"]["result"] for e in attempts if (e.get("submit") or {}).get("outcome") == "accepted" and "energy_trans_progress" in e]
            self.assertEqual(tiers[:2], ["tier2", "tier1"], seed)
            again = [e for e in attempts if (e.get("retreat_deferral") or {}).get("result") == "already_recorded" and ":retreat_no_alternative" not in e["candidate_reason"]]
            self.assertEqual(again, [], seed)
            self.assertEqual(result["anomalies"], [], seed)


class RunnerAndBatchTest(unittest.TestCase):
    def test_runner_builds_rules_v8_and_records_it(self):
        result = V.run_game(small(policy="rules", rules_version=8, limits={"operations": 120}))
        p0 = result["policies"]["0"]
        self.assertEqual((p0["name"], p0["version"], p0["distribution"], p0["repeat_threshold"]), ("rules", 8, RULES8_DISTRIBUTION, 2))
        self.assertEqual((p0["loop"]["energy_trans_progress"]["version"], p0["loop"]["retreat_deferral"]["failure"], p0["loop"]["swap_cap"]["cap"]),
                         (1, "total_units_unreachable", 6))

    def test_make_policies_and_batch_records(self):
        for policy in V.make_policies(small(policy="rules", rules_version=8)).values():
            if policy.name == "rules":
                self.assertIsInstance(policy, EnergyTransProgressRulePolicy)
        for version in (2, 3, 4, 5, 6, 7):
            for policy in V.make_policies(small(policy="rules", rules_version=version)).values():
                self.assertFalse(isinstance(policy, EnergyTransProgressRulePolicy) or hasattr(policy, "wants_retreat_inputs"))
        with self.assertRaises(ValueError):
            RulePolicy("s", version=8)
        self.assertEqual(B.MODES["rules-v8"], {"policy": "rules", "rules_version": 8, "repeat_threshold": 2})
        self.assertEqual(B.MODES["rules-v7"], {"policy": "rules", "rules_version": 7, "repeat_threshold": 2})
        adapter = B.EngineAdapter()
        v8 = adapter.policies_of(small(policy="rules", rules_version=8))
        v7 = adapter.policies_of(small(policy="rules", rules_version=7))
        self.assertEqual((v8["0"]["version"], v8["0"]["energy_trans_progress"], v8["0"]["retreat_deferral"]["version"]), (8, ENERGY_TRANS_PROGRESS, 1))
        self.assertNotIn("energy_trans_progress", v7["0"])
        self.assertEqual(B.TOOL_VERSION, 20)  # 20: rules-v9（旧の期待は 19）

    def test_card_table_from_the_engine_registry(self):
        self.assertEqual(CARDS[VEN]["attacks"], [["grass"] * 4])
        self.assertEqual(CARDS[TAN]["attacks"][0], ["grass", "colorless"])
        self.assertEqual((CARDS[G]["basic_energy"], CARDS[G]["provides"]), (True, "grass"))
        self.assertEqual((CARDS[DCE]["basic_energy"], CARDS[DCE]["provides"]), (False, None))


# rules-v6・rules-v7 の列（基点 4bd65f9 の道具で求めた値。rules-v8 の追加で変わらないこと）
BASE_SEQUENCES = {("rules-v2-s13", 6): (352, "0b15ec368b0c13fd84b13b8c33e4500df847d3f383a8c0bb976e153e858e7752"),
                  ("rules-v2-s13", 7): (272, "63690f203d9db8b3f4f95adc056e33785d5a321165bad9dfbbf7bee45d9d6efc"),
                  ("rules-v2-l67u-s9023", 6): (185, "4fb6dcae64112c3f8c9525cf1566ebef564cdd835e6b0e302d5697d1035941e8"),
                  ("rules-v2-l67u-s9023", 7): (322, "243b4703572502e7c611b0e9493d5f83ed5f981e46bc44e965c54b5c20cdf98e")}


class SequenceTest(unittest.TestCase):
    def test_existing_policies_unchanged_and_v8_equal_until_first_restriction(self):
        for name in ("rules-v2-s13", "rules-v2-l67u-s9023"):
            kw, _golden, _swaps = V2_GOLDEN[name]
            runs = {v: V.run_game(V.Config(policy="rules", rules_version=v, **kw)) for v in (6, 7, 8)}
            for v in (6, 7):
                d = R.sequence_digest(R.action_sequence(runs[v]["trace"]), R.ACTION_FORMAT)
                self.assertEqual((d["length"], d["sha256"]), BASE_SEQUENCES[(name, v)], (name, v))
            a7, a8 = R.action_sequence(runs[7]["trace"]), R.action_sequence(runs[8]["trace"])
            t8 = [e for e in runs[8]["trace"] if e.get("type") == "attempt"]
            hit = [i for i, e in enumerate(t8) if (e.get("energy_trans_progress") or {}).get("restricted")]
            if not hit:
                self.assertEqual(a7, a8, name)
            else:
                before = sum(1 for e in t8[:hit[0]] if (e.get("submit") or {}).get("outcome") == "accepted")
                self.assertEqual(a7[:before], a8[:before], name)
            self.assertEqual(runs[8]["anomalies"], [], name)


if __name__ == "__main__":
    unittest.main()

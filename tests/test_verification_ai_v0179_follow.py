"""検証用 AI の 0.179.0（PT-5t-C1）への追従のテスト（docs/verification-ai-v0179-follow.md）。

PT-5t-C1: トレーナーの候補の確かめが相手のうらのカードの本当のカードを使ったら、その結果を使わず、その選べるものを unverified（face_down_reveal_not_evaluated）にする。
確認された秘密依存の判定を候補の側で採用しない補強で、修正の前の構築盤面でも外へ出る差は再現していない（docs/legal-actions-up5t-d-trainer-audit.md 12 章）。

play_trainer は手札のカードごとの選べるものを持ち、一部だけが unverified になりうる。AI の区分を 3 つに分けて確かめる:
- 候補の区分: ランナーの ``_scope``（候補の処理可能性。選べるものの中でいちばん進めやすい区分）
- 選べるものの区分: ``actions.option_allowed``・``build_choices``・``build_choices_tuple``（選べるもの自身の eligible・処理可能性）
- 完成入力の区分: ``actions.input_processability``（選んだものの中でいちばん進めにくい区分）
盤面はエンジンのテスト ``tests/test_legal_actions_pt5t_c1_v0_179.py`` の構築盤面（new_game からの到達ではない）。AI のコード（方策・入力生成・範囲・判定）は変えていない。
"""

from __future__ import annotations

import copy
import unittest

from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from tests import helpers as H
from tests.test_legal_actions_pt5t_c1_v0_179 import IMAKUNI, REALS, REQ, TRAINERS, opponent_face_down, opponent_face_up, own_face_down, with_allergy_pollen
from tools.verification_ai import actions as B
from tools.verification_ai import judge as J
from tools.verification_ai import records as R
from tools.verification_ai import runner as V
from tools.verification_ai.policies import UniformPolicy, action_key

GUARDED_REASONS = sorted([J.FACE_DOWN_REASON, "preflight_not_evaluated", "continuation_not_evaluated"])


def query(state, actor=1):
    hub = ClientHub.from_state(state)
    me = hub.player(actor)
    return hub, me, me.handle({**REQ, "type": "candidates"})["response"]


def trainer(cands):
    return next(c for c in cands["candidates"] if c["kind"] == L.KIND_PLAY_TRAINER)


def stages_of(me, cands, c):
    return me.handle({**REQ, "type": "inputs", "game": cands["game"], "revision": cands["revision"], "candidate": c["id"]})["response"]["stages"]


def scope(cands, profile="deep"):
    runner = V.Runner(V.Config(profile=profile))
    chosen, info, reasons = runner._scope(cands, {})
    return [c["id"] for c in chosen], info, reasons, runner.counters["deep_fallback_unverified"]


def card_option(state, stages, card_id, player=1):
    uid = next(u for u in state.players[player].hand if state.cards[u].card_id == card_id)
    return next(o for o in stages[0]["options"] if o["card"] == uid)


def attempt(candidate, stages, meaning, submit):
    return {"type": "attempt", "n": 1, "actor": 1, "operation_id": "v0-000001", "build": "ok", "candidate": candidate, "stages": stages, "meaning": meaning,
            "check": {"response": {"valid": True}}, "submit": submit}


class OptionClassTest(unittest.TestCase):
    def test_guarded_option_controls_and_public_refusal(self):
        for name, card in TRAINERS.items():
            seen = set()
            for real in REALS.values():
                s = opponent_face_down(card, real)
                _hub, me, cands = query(s)
                c = trainer(cands)
                o = card_option(s, stages_of(me, cands, c), card)
                self.assertEqual((o["processability"], o["reasons"], o["eligible"]), (L.UNVERIFIED, GUARDED_REASONS, True))
                self.assertEqual((c["processability"], c["input_disclosure"]), (L.UNVERIFIED, L.DISCLOSURE_CONFIRMED))  # 選べるものが 1 つだけなら候補も unverified
                seen.add(str({k: v for k, v in o.items() if k not in ("id", "card")}))
            self.assertEqual(len(seen), 1)  # 本当のカードによらない
            s = opponent_face_up(card)
            _hub, me, cands = query(s)
            o = card_option(s, stages_of(me, cands, trainer(cands)), card)
            self.assertEqual(o["processability"], L.MAY_STOP_LATER)  # おもての対照は使うための条件を評価する
            for real in REALS.values():
                _hub, _me, cands = query(with_allergy_pollen(card, real))
                self.assertEqual([c for c in cands["candidates"] if c["kind"] == L.KIND_PLAY_TRAINER], [])  # 公開の条件で使えない: 候補に出ない
        for real in REALS.values():
            s = own_face_down(real)
            _hub, me, cands = query(s, 0)
            o = card_option(s, stages_of(me, cands, trainer(cands)), IMAKUNI, player=0)
            self.assertNotIn(J.FACE_DOWN_REASON, o.get("reasons", []))  # 本人のうらだけを読む対照は未評価にしない


class MixedScopeTest(unittest.TestCase):
    """同じ play_trainer の候補に、may_stop_later（イマクニ？。自分のおもてのバトル場）と unverified（ねむれ!ねむれ!）の選べるものが混ざる盤面。"""

    def setUp(self):
        self.state = opponent_face_down(H.SLEEP_TRAINER, H.KADABRA, extra_hand=(IMAKUNI,))
        self.hub, self.me, self.cands = query(self.state)
        self.original = copy.deepcopy(self.cands)
        self.c = trainer(self.cands)
        self.stages = stages_of(self.me, self.cands, self.c)
        self.guarded = card_option(self.state, self.stages, H.SLEEP_TRAINER)
        self.other = card_option(self.state, self.stages, IMAKUNI)

    def test_candidate_class_is_the_best_option_and_deep_keeps_the_candidate(self):
        self.assertEqual((self.guarded["processability"], self.other["processability"]), (L.UNVERIFIED, L.MAY_STOP_LATER))
        self.assertEqual(self.c["processability"], L.MAY_STOP_LATER)  # 候補の区分は選べるものの中でいちばん進めやすい区分
        chosen, info, _reasons, fallbacks = scope(self.cands)
        self.assertIn(self.c["id"], chosen)  # 候補全体を一律に除かない
        self.assertEqual((info["fallback_unverified"], fallbacks), (False, 0))
        self.assertIn(self.c["id"], scope(self.cands, "boundary")[0])
        self.assertEqual(self.cands, self.original)

    def test_deep_never_picks_the_guarded_option_but_boundary_can(self):
        self.assertFalse(B.option_allowed(self.guarded, B.DEEP_PROCESSABILITY))
        self.assertTrue(B.option_allowed(self.other, B.DEEP_PROCESSABILITY))
        self.assertTrue(B.option_allowed(self.guarded, B.FALLBACK_PROCESSABILITY))
        deep_picks, boundary_picks = set(), set()
        for seed in range(12):
            ctx = {"candidate": self.c}
            choices, _p, _m = B.build_choices(self.stages, UniformPolicy(f"d{seed}"), ctx, B.DEEP_PROCESSABILITY)
            deep_picks.add(tuple(choices))
            tchoices, _p, _m, _method = B.build_choices_tuple(self.stages, UniformPolicy(f"t{seed}"), ctx, B.DEEP_PROCESSABILITY)
            deep_picks.add(tuple(tchoices))
            bchoices, _p, _m = B.build_choices(self.stages, UniformPolicy(f"b{seed}"), ctx, B.FALLBACK_PROCESSABILITY)
            boundary_picks.add(tuple(bchoices))
        self.assertEqual(deep_picks, {(self.other["id"],)})  # deep は unverified の選べるものだけを除く（ほかの選べるものは残る）
        self.assertEqual(boundary_picks, {(self.other["id"],), (self.guarded["id"],)})  # boundary（と代替）は入力の公開された unverified も選べる
        self.assertEqual({tuple(t[0]) for t in B.enumerate_inputs(self.stages, B.DEEP_PROCESSABILITY)}, {(self.other["id"],)})
        self.assertEqual(self.cands, self.original)

    def test_completed_input_class_is_separate_from_the_candidate_class(self):
        guarded = B.input_processability(self.stages, [self.guarded["id"]])
        other = B.input_processability(self.stages, [self.other["id"]])
        self.assertEqual((guarded["class"], other["class"]), (L.UNVERIFIED, L.MAY_STOP_LATER))  # 候補は may_stop_later のまま
        self.assertEqual(guarded["items"][0]["from"], "option")

    def test_check_and_submit_through_the_common_path(self):
        for picked in (self.guarded, self.other):
            hub, me, cands = query(self.state)
            c = trainer(cands)
            stages = stages_of(me, cands, c)
            option = next(o for o in stages[0]["options"] if o["card"] == picked["card"])
            choices = [option["id"]]
            meaning = [{"stage": 1, "option": option}]
            handle = {"game": cands["game"], "revision": cands["revision"], "candidate": c["id"]}
            self.assertIs(me.handle({**REQ, "type": "check", **handle, "choices": choices})["response"]["valid"], True)  # 構造の検査だけ
            sent = me.handle({**REQ, "type": "submit", **handle, "choices": choices})
            with self.subTest(card=option["card_id"]):
                self.assertIn(sent["outcome"], (D.ACCEPTED, D.REJECTED))
                verdict, _notes = J.judge_normal(c, meaning, {"ok": sent["ok"], "outcome": sent["outcome"], "verifier": sent.get("result", {}).get("verifier")},
                                                 stages=stages)
                if sent["outcome"] == D.ACCEPTED:
                    self.assertEqual(verdict, J.EXPECTED)
                self.assertEqual(hub.take_updates(0) != [], sent["outcome"] == D.ACCEPTED)  # 受理だけが公開の更新


class FallbackAndExclusionTest(unittest.TestCase):
    """小さな JSON 例（実際の応答の写しから作る）。代替・表示だけ・入力を返さない・実行できない区分。"""

    def setUp(self):
        s = opponent_face_down(H.SLEEP_TRAINER, H.RATTATA)
        _hub, me, self.cands = query(s)
        self.c = trainer(self.cands)
        self.stages = stages_of(me, self.cands, self.c)

    def test_deep_fallback_only_when_nothing_else_is_in_scope(self):
        chosen, info, reasons, fallbacks = scope(self.cands)
        self.assertNotIn(self.c["id"], chosen)  # 選べるものが unverified だけの候補は deep の範囲の外（ほかの候補があるので代替は起きない）
        self.assertEqual((reasons[self.c["id"]], info["fallback_unverified"], fallbacks), ("processability:unverified", False, 0))
        only = copy.deepcopy(self.cands)
        only["candidates"] = [copy.deepcopy(self.c)]
        chosen, info, _reasons, fallbacks = scope(only)
        self.assertEqual((chosen, info["fallback_unverified"], fallbacks), ([self.c["id"]], True, 1))  # 代替は数える（deep_fallback_unverified）
        choices, _p, _m = B.build_choices(self.stages, UniformPolicy("f"), {"candidate": self.c}, B.FALLBACK_PROCESSABILITY)
        self.assertEqual(len(choices), 1)  # 代替（と boundary）の allowed では選べる
        with self.assertRaises(B.Unbuildable):
            B.build_choices(self.stages, UniformPolicy("f"), {"candidate": self.c}, B.DEEP_PROCESSABILITY)  # deep の allowed では作れない

    def test_display_only_withheld_and_not_executable_are_not_sent(self):
        withheld = copy.deepcopy(self.cands)
        withheld["candidates"] = [{**copy.deepcopy(self.c), "input_disclosure": L.DISCLOSURE_UNCONFIRMED}]
        display = copy.deepcopy(withheld)
        display["candidates"][0]["input_disclosure"] = L.DISCLOSURE_CONFIRMED
        display["coverage"]["display_only_kinds"] = [L.KIND_PLAY_TRAINER]
        stop = copy.deepcopy(display)
        stop["coverage"]["display_only_kinds"] = []
        stop["candidates"][0]["processability"] = L.NOT_IMPLEMENTED
        for label, cands in (("withheld", withheld), ("display_only", display), ("not_executable", stop)):
            for profile in ("deep", "boundary"):
                with self.subTest(label=label, profile=profile):
                    self.assertEqual(scope(cands, profile)[0], [])
        stages = copy.deepcopy(self.stages)
        stages[0]["options"][0] = {**stages[0]["options"][0], "eligible": False, "processability": L.NOT_IMPLEMENTED}
        for allowed in (B.DEEP_PROCESSABILITY, B.FALLBACK_PROCESSABILITY):
            self.assertFalse(B.option_allowed(stages[0]["options"][0], allowed))

    def test_scope_and_options_do_not_read_card_names_or_ids(self):
        renamed = copy.deepcopy(self.cands)
        for profile in ("deep", "boundary"):
            self.assertEqual(scope(renamed, profile)[:2], scope(self.cands, profile)[:2])
        stages = copy.deepcopy(self.stages)
        stages[0]["options"] = [{**o, "card_id": "X-000"} for o in stages[0]["options"]]
        self.assertEqual([B.option_allowed(o, B.FALLBACK_PROCESSABILITY) for o in stages[0]["options"]],
                         [B.option_allowed(o, B.FALLBACK_PROCESSABILITY) for o in self.stages[0]["options"]])


class JudgeTest(unittest.TestCase):
    def test_unverified_is_not_all_normal_and_unknowns_are_not_known_stops(self):
        _hub, _me, cands = query(opponent_face_down(H.SLEEP_TRAINER, H.DITTO))
        c = trainer(cands)
        self.assertNotIn(c["kind"], J.PRECHECK_KINDS)

        def rejected(code, category):
            return {"ok": True, "outcome": D.REJECTED, "verifier": {"diagnostic_id": code, "category": category, "engine_code": code}}

        stop = "UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT"
        cases = {
            "refused": ({"ok": True, "outcome": "refused", "refusal": {"code": L.CANDIDATES_STALE}}, J.SUSPECT),  # ホストの段の断り（エンジンの拒否ではない）
            "failed": ({"ok": False, "outcome": D.FAILED}, J.SUSPECT),
            "unknown": ({"ok": True, "outcome": "something_new"}, J.UNDETERMINED),
            "unmapped": (rejected("X", D.UNMAPPED), J.SUSPECT),
            "mismatch": (rejected("INSUFFICIENT_CARDS_IN_HAND", D.UNSUPPORTED), J.SUSPECT),
            "engine_rejected": (rejected("INSUFFICIENT_CARDS_IN_HAND", D.INVALID_INPUT), J.NORMAL_REJECTION),  # 覆われた公開の拒否もエンジンの拒否として読む
            "stop_without_evidence": (rejected(stop, D.default_catalog().get(stop).category), J.UNDETERMINED),
            "stop_not_in_catalog": (rejected("UNRESOLVED_NOT_IN_TABLE", D.RULING_UNRESOLVED), J.UNDETERMINED),
        }
        for label, (submit, verdict) in cases.items():
            with self.subTest(label):
                self.assertEqual(J.judge_normal(c, [], submit, stages=[])[0], verdict)
        self.assertEqual(J.JUDGE_RULES_VERSION, 7)  # この追従では判定の規則を変えていない（規則 6 はあとの C1 の確認、規則 7 はあとの LOST_TARGET の P1）


class FingerprintTest(unittest.TestCase):
    def test_guarantee_text_is_the_0178_text_plus_one_sentence(self):
        """v2_repeat の契約の値の固定値 4 つの更新の根拠: 0.179.0 の play_trainer の preconditions は 0.178.0 の文に 1 文を足したもの。行動の列・反復の鍵は保証の文によらない。"""
        text = L.GUARANTEE_TRAINER["preconditions"]
        old, sep, added = text.partition("。v0.179:")
        self.assertTrue(sep and old and added)
        self.assertIn("unverified", added)
        s = opponent_face_up(H.SLEEP_TRAINER)
        _hub, me, cands = query(s)
        c = trainer(cands)
        self.assertEqual(c["guarantees"]["preconditions"], text)
        stages = stages_of(me, cands, c)
        meaning = [{"stage": 1, "option": stages[0]["options"][0]}]
        older = {**c, "guarantees": {**c["guarantees"], "preconditions": old}}
        accepted = {"ok": True, "outcome": D.ACCEPTED, "refusal": None, "verifier": None}
        self.assertEqual(R.action_sequence([attempt(c, stages, meaning, accepted)]), R.action_sequence([attempt(older, stages, meaning, accepted)]))
        self.assertNotEqual(R.contract_sequence([attempt(c, stages, meaning, accepted)]), R.contract_sequence([attempt(older, stages, meaning, accepted)]))
        self.assertEqual(action_key(1, c, stages, meaning), action_key(1, older, stages, meaning))

    def test_guarded_option_changes_contract_rows_not_action_rows(self):
        """ガードが働く選べるものとおもての対照の差（処理可能性・理由）は契約の列にだけ出て、行動の列・反復の鍵には出ない。"""
        down_state, up_state = opponent_face_down(H.SLEEP_TRAINER, H.RATTATA), opponent_face_up(H.SLEEP_TRAINER)
        _h, me_d, down = query(down_state)
        _h, me_u, up = query(up_state)
        cd, cu = trainer(down), trainer(up)
        sd, su = stages_of(me_d, down, cd), stages_of(me_u, up, cu)
        od, ou = card_option(down_state, sd, H.SLEEP_TRAINER), card_option(up_state, su, H.SLEEP_TRAINER)
        ou_same = {**ou, "id": od["id"], "card": od["card"]}  # 2 つの盤面はカードの番号が違うので、行動の対象をそろえ、評価の値の差だけを残す
        self.assertEqual({k for k in od if od[k] != ou_same.get(k)}, {"processability", "reasons"})
        su_same = [{**su[0], "options": [ou_same]}]
        cu_same = {**cu, "id": cd["id"], "processability": cu["processability"]}
        accepted = {"ok": True, "outcome": D.ACCEPTED, "refusal": None, "verifier": None}
        a = attempt(cd, [{**sd[0], "options": [od]}], [{"stage": 1, "option": od}], accepted)
        b = attempt(cu_same, su_same, [{"stage": 1, "option": ou_same}], accepted)
        self.assertEqual(R.action_sequence([a]), R.action_sequence([b]))
        self.assertNotEqual(R.contract_sequence([a]), R.contract_sequence([b]))
        self.assertEqual(action_key(1, a["candidate"], a["stages"], a["meaning"]), action_key(1, b["candidate"], b["stages"], b["meaning"]))


if __name__ == "__main__":
    unittest.main()

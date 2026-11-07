"""v0.162（docs/legal-actions-decision-audit.md）: U7 の決定の入力の監査（情報境界と答えの並び）の回帰テスト。

確かめの種類を分ける:

- 監査の一覧とコードの照らし（走査の組・種類の分類・legal_actions の集合）: --check と同じ関数を、わざと壊した値で
- 構築盤面（``build_test_state`` と既存のテストの盤面）: 新しく公開した種類の情報源と表示、同じ種類の別の出し方、双子、検索の前後、相手の番の決定、
  複数選択・数・重なり・並び、直接の送信との一致、取得での不変
- new_game からの合法な操作の列: 3 つの規約集合で、決定の入力を返すこと

停止コードの文字列はテストの中に書かない。
"""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.commands import PlayTrainer, ResolveDecision, UseAttack
from kyuura_engine.observation import OPTION_MEANINGS
from tests import helpers as H
from tests import test_haunter_line_v0_9 as T9
from tests import test_reactive_decisions_v0_65 as T65
from tests.log_audit import owned_card_ids, public_view
from tests.test_legal_actions_u7_1 import drive, fetch, snap, without_handles

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("build_legal_actions_api_design", ROOT / "scripts" / "build_legal_actions_api_design.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)
SETS = (None, "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1")


def board(hand, *, bench=(H.PONYTA, H.SEEL), deck=(H.WATER, H.SEEL, H.BILL, H.FIRE), prizes=(H.POTION, H.WATER), discard=(), active=None, their_active=None):
    return H.build_test_state([
        {"active": active or H.GROWLITHE, "bench": list(bench), "hand": list(hand), "deck": list(deck), "prizes": list(prizes), "discard": list(discard)},
        {"active": their_active or H.STARYU, "bench": [H.SEEL], "hand": [H.WATER], "deck": [H.WATER, H.WATER], "prizes": [H.WATER, H.WATER]},
    ], turn_number=3)


def after(state, command, submitter):
    host = L.ActionHost.from_state(state)
    result = host.game.submit(command, submitter=submitter)
    assert result.outcome == D.ACCEPTED, result
    return host


def play_first(state):
    return after(state, PlayTrainer(0, state.players[0].hand[0]), 0)


def stage_of(host, actor):
    r, inputs = fetch(host.session(actor))
    assert "withheld" not in inputs, inputs
    return r, inputs["stages"][0]


def submit_same(test, host, actor, ids):
    """U7 で送った結果と、同じ選択を直接送った結果が同じ（状態・本人の結果）。"""
    state = host.game.state
    d = state.decision
    values = tuple(d.options[int(i[1:]) - 1] for i in ids)
    direct = A.submit(state, ResolveDecision(actor, d.id, values), submitter=actor)
    r = host.session(actor).candidates()
    result = host.session(actor).submit(r["game"], r["revision"], "c1", ids)
    test.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(actor)))
    if direct.outcome == D.ACCEPTED:
        test.assertEqual(snap(host.game.state), snap(direct.state))
    return result


class AuditCheckTest(unittest.TestCase):
    def test_written_files_match_and_sites_are_covered(self):
        written = json.loads(B.OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(B.check(written, B.DESIGN.read_text(encoding="utf-8"), B.PLAN.read_text(encoding="utf-8")), [])

    def test_added_or_removed_site_is_detected(self):
        spec = B.build()
        scanned = B.SITES.site_keys(B.SITES.scan(ROOT))
        added = scanned | {("select_pokemon", "kyuura_engine/effects.py", "FutureEffectForTest", "resolve")}
        self.assertIn("決定の出し方 ('select_pokemon', 'kyuura_engine/effects.py', 'FutureEffectForTest', 'resolve') に監査の判定がない（コードに加わった出し方）",
                      B.site_problems(spec, added))
        removed = set(scanned)
        removed.remove(next(iter(sorted(scanned, key=str))))
        self.assertTrue(any(p.startswith("監査の判定の出し方") for p in B.site_problems(spec, removed)))

    def test_order_classification_must_follow_the_sites(self):
        spec = copy.deepcopy(B.build())
        spec["order"]["bench_guard"]["status"] = "not_significant"
        problems = B.site_problems(spec)
        self.assertTrue(any("bench_guard" in p for p in problems), problems)
        code = B.code_vocabulary()
        code["order_not_significant"] = set(code["order_not_significant"]) - {"retrieve_energy"}
        self.assertIn("答えの並びに意味がない種類が、legal_actions.ORDER_NOT_SIGNIFICANT_KINDS と違う", B.coverage_problems(B.build(), code))

    def test_every_kind_is_disclosed_by_an_explicit_list(self):
        self.assertEqual(set(OPTION_MEANINGS), set(L.DISCLOSURE_CONFIRMED_KINDS))
        code = B.code_vocabulary()
        code["plain_kinds"] = list(code["plain_kinds"]) + ["future_kind_for_test"]
        self.assertIn("決定 future_kind_for_test の情報境界の分類がない（D-U7-DECISION-UID）", B.coverage_problems(B.build(), code))


class NewlyDisclosedTest(unittest.TestCase):
    """v0.161 で入力を返さなかった種類（構築盤面）。選べるもの・表示・数・並び・直接の送信との一致。"""

    def test_select_pokemon_from_switch(self):
        host = play_first(board((H.SWITCH, H.FIRE)))
        r, stage = stage_of(host, 0)
        state = host.game.state
        self.assertEqual((stage["decision_kind"], stage["meaning"], r["candidates"][0]["input_disclosure"]), ("select_pokemon", "pokemon", L.DISCLOSURE_CONFIRMED))
        self.assertEqual([o["value"] for o in stage["options"]], [p.pokemon_id for p in state.players[0].bench])
        submit_same(self, host, 0, ["o2"])

    def test_select_pokemon_from_potion_is_another_route(self):
        state = board((H.POTION,), active={"card": H.GROWLITHE, "damage": 20})
        host = play_first(state)
        _, stage = stage_of(host, 0)
        self.assertEqual(stage["decision_kind"], "select_pokemon")
        own = host.game.state.players[0].in_play()
        self.assertEqual([o["value"] for o in stage["options"]], [p.pokemon_id for p in own])  # 自分の場のポケモン（公開）
        # ダメージのないポケモンは候補から消さず、選ぶと止める選択として示す（ゲーム上の禁止ではない）
        self.assertEqual([o["processability"] for o in stage["options"]], [L.MAY_STOP_LATER if p.damage else L.RULING_UNRESOLVED for p in own])

    def test_super_energy_removal_routes_and_unordered_multi_choice(self):
        state = board((H.SUPER_ENERGY_REMOVAL,), active={"card": H.GROWLITHE, "energy": [H.FIRE]},
                      their_active={"card": H.STARYU, "energy": [H.WATER, H.WATER, H.WATER]})
        host = play_first(state)
        _, stage = stage_of(host, 0)
        self.assertEqual(stage["decision_kind"], "discard_energy")  # トレーナーの出し方（ワザの出し方とは別）
        submit_same(self, host, 0, ["o1"])
        _, stage = stage_of(host, 0)
        self.assertEqual(stage["decision_kind"], "select_pokemon")  # 相手の場のポケモン
        submit_same(self, host, 0, ["o1"])
        _, stage = stage_of(host, 0)
        self.assertEqual((stage["decision_kind"], stage["count"], stage["order"]), ("discard_opponent_energy", {"min": 2, "max": 2}, L.ORDER_NOT_SIGNIFICANT))
        finals = []
        for ids in (["o1", "o2"], ["o2", "o1"]):
            twin = L.ActionHost.from_state(host.game.state)
            submit_same(self, twin, 0, ids)
            finals.append(snap(twin.game.state))
        self.assertEqual(finals[0], finals[1])  # 並びに意味がない（ついている並びの順にトラッシュする）
        r = host.session(0).candidates()
        for bad in (["o1"], ["o1", "o1"], ["o1", "o9"], ["o1", "o2", "o3"]):
            self.assertEqual(host.session(0).check(r["game"], r["revision"], "c1", bad)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)

    def test_bench_from_discard_and_retrieve_energy(self):
        host = play_first(board((H.REVIVE,), discard=(H.PONYTA, H.FIRE, H.CHARMANDER), bench=(H.SEEL,)))
        _, stage = stage_of(host, 0)
        state = host.game.state
        self.assertEqual(stage["decision_kind"], "bench_from_discard")
        self.assertTrue(all(o["card"] in state.players[0].discard for o in stage["options"]))
        state = board((H.ENERGY_RETRIEVAL, H.PONYTA), discard=(H.FIRE, H.WATER, H.PSYCHIC))
        host = play_first(state)
        submit_same(self, host, 0, ["o1"])
        _, stage = stage_of(host, 0)
        self.assertEqual((stage["decision_kind"], stage["count"]["max"], stage["order"]), ("retrieve_energy", 2, L.ORDER_NOT_SIGNIFICANT))
        finals = []
        for ids in (["o1", "o2"], ["o2", "o1"]):
            twin = L.ActionHost.from_state(host.game.state)
            submit_same(self, twin, 0, ids)
            finals.append(snap(twin.game.state))
        self.assertEqual(finals[0], finals[1])

    def test_return_to_deck_then_started_search(self):
        """ポケモン交換おじさん: 手札のポケモンを選ぶ（本人の手札）→ 山札をさがす（始まった検索。実際の山札）。"""
        host = play_first(board((H.POKEMON_TRADER, H.PONYTA)))
        _, stage = stage_of(host, 0)
        state = host.game.state
        self.assertEqual(stage["decision_kind"], "return_to_deck")
        self.assertTrue(all(o["card"] in state.players[0].hand for o in stage["options"]))
        submit_same(self, host, 0, ["o1"])
        _, stage = stage_of(host, 0)
        self.assertIn(stage["decision_kind"], ("search_deck",))
        self.assertTrue(all(o["card"] in host.game.state.players[0].deck for o in stage["options"]))


class OrderTest(unittest.TestCase):
    def test_recover_energy_order_matters(self):
        """エナジーへんかん（ワザの RecoverEnergy）: 選んだ順に手札に加える。並びを変えると手札の並びが変わり、どちらも直接の送信と同じ。"""
        state = T9.EnergyConversionTest("test_decision_shape").board()
        host = after(state, UseAttack(0, 1), 0)
        _, stage = stage_of(host, 0)
        self.assertEqual((stage["decision_kind"], stage["order"], stage["order_preserved"]), ("recover_energy", L.ORDER_SIGNIFICANT, True))
        finals = []
        for ids in (["o1", "o2"], ["o2", "o1"]):
            twin = L.ActionHost.from_state(host.game.state)
            submit_same(self, twin, 0, ids)
            finals.append(snap(twin.game.state))
        self.assertNotEqual(finals[0], finals[1])

    def test_bench_guard_on_the_opponents_turn(self):
        """［ベンチガード］（相手の番。決めるのはダメージを受ける側）: 2 匹を選ぶ並びがログの並びに入る。"""
        state = T65.table(T65.mon(H.FOSSIL_MAGNETON, (H.LIGHTNING,) * 4), T65.mon(H.HITMONCHAN), bench=[H.RATTATA],
                          opponent_bench=[H.RATTATA, T65.mon(T65.BROCKS_RHYDON), T65.mon(T65.BROCKS_RHYDON)])
        host = after(state, UseAttack(0, 1), 0)
        self.assertEqual((host.game.state.current_player, host.game.state.decision.player), (0, 1))
        r0 = host.session(0).candidates()
        self.assertEqual((r0["situation"], r0["empty_reason"]), (L.WAITING_FOR_PLAYER, L.EMPTY_NOT_ACTOR))
        _, stage = stage_of(host, 1)
        self.assertEqual((stage["decision_kind"], stage["order"], stage["count"]), ("bench_guard", L.ORDER_SIGNIFICANT, {"min": 0, "max": 2}))
        finals = []
        for ids in (["o1", "o2"], ["o2", "o1"]):
            twin = L.ActionHost.from_state(host.game.state)
            submit_same(self, twin, 1, ids)
            finals.append(snap(twin.game.state))
        self.assertNotEqual(finals[0], finals[1])

    def test_ninja_trick_answered_on_the_opponents_turn(self):
        state, _ = T65.trick_board()
        host = after(state, UseAttack(1, 1), 1)
        self.assertEqual((host.game.state.current_player, host.game.state.decision.player), (1, 0))
        _, stage = stage_of(host, 0)
        self.assertEqual((stage["decision_kind"], stage["decline"]), ("ninja_trick", True))
        submit_same(self, host, 0, [])


class TwinTest(unittest.TestCase):
    """山札とサイドの配分だけが違う双子: 新しく公開した種類の候補・入力・入力の検査・不正な問い合わせの答えが同じ（取っ手の文字列は比べない）。"""

    def responses(self, host):
        out = []
        before = snap(host.game.state)
        for actor in (0, 1):
            session = host.session(actor)
            r = session.candidates()
            item = [without_handles(r)]
            for cand in ("c1", "c9"):
                item.append(session.inputs(r["game"], r["revision"], cand))
                item += [session.check(r["game"], r["revision"], cand, c) for c in ([], ["o1"], ["o1", "o2"], ["o1", "o1"], ["o7"], "x")]
            out.append(item)
        assert snap(host.game.state) == before
        return out

    def test_twins_before_any_search(self):
        for hand in ((H.SWITCH, H.FIRE), (H.SUPER_ENERGY_REMOVAL,), (H.POKEMON_TRADER, H.PONYTA)):
            with self.subTest(hand=hand):
                extra = {"active": {"card": H.GROWLITHE, "energy": [H.FIRE]}, "their_active": {"card": H.STARYU, "energy": [H.WATER, H.WATER]}}
                a = board(hand, deck=(H.WATER, H.SEEL, H.BILL, H.FIRE), prizes=(H.POTION, H.WATER), **extra)
                b = board(hand, deck=(H.WATER, H.SEEL, H.POTION, H.FIRE), prizes=(H.BILL, H.WATER), **extra)
                for viewer in (0, 1, None):
                    self.assertEqual(public_view(a, viewer), public_view(b, viewer))
                self.assertEqual(owned_card_ids(a, 0), owned_card_ids(b, 0))
                ha, hb = play_first(a), play_first(b)
                self.assertEqual(self.responses(ha), self.responses(hb))


class ConventionSetsTest(unittest.TestCase):
    def test_decision_inputs_are_returned_in_each_set(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                host = drive(4, use_u7=True, conventions=conventions, until=lambda s: s.decision is not None and s.turn_number >= 3)
                state = host.game.state
                if state.decision is None:
                    continue
                r, inputs = fetch(host.session(state.decision.player))
                self.assertNotIn("withheld", inputs)
                self.assertEqual(r["candidates"][0]["input_disclosure"], L.DISCLOSURE_CONFIRMED)


class DocumentTest(unittest.TestCase):
    def test_document_records_the_audit(self):
        text = (ROOT / "docs" / "legal-actions-decision-audit.md").read_text(encoding="utf-8")
        for phrase in ("不具合 39 件という意味ではありません", "B（確かめた条件の下だけ公開できる）", "ホストが直接送って進められることを、U7 の対応として数えない",
                       "operation_id", "完全な `GameState` ではなく", "v0.161"):
            self.assertTrue(phrase in text, phrase)


if __name__ == "__main__":
    unittest.main()

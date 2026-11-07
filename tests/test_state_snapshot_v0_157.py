"""v0.157（docs/state-snapshot-v0.157.md）: 状態スナップショット（U6 の S1〜S4・S6）。

盤面の種類（docs 6 章）:
- new_game からの合法な操作の列: ピカチュウのデッキの方策（seed 9 はサドン・デスから延長戦、seed 0 は終局）を 3 つの規約集合で、たねポケモン 1 枚のデッキ（seed 1 は準備で停止）、
  ファイヤー対ラッキー（seed 0 はドライアップの答えを受理した結果として途中停止）、たねの少ないデッキの S2a の切り直しの補償
- 構築盤面（tests.helpers.build_test_state。new_game から合法に到達できることは保証しない）: マチスの秘策・とりかえっこプリーズ・挑戦状・かたまる・マーカー・
  S2a の両方ねむり・PO の［ポイズンミスト］
- 書きかえた入力（F9）と、例外を差し込む確かめ
保存しない状態と、保存して復元した状態へ同じ操作を送り、各境界で比べる（JSON の往復だけを完了の基準にしない）。停止コードの文字列はテストの中に書かない。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import unittest
from types import MappingProxyType
from unittest import mock

from kyuura_engine import (
    EndTurn,
    PlayTrainer,
    ResolveDecision,
    StartSuddenDeath,
    new_game,
    observe,
)
from kyuura_engine import adapter as A
from kyuura_engine import conventions as C
from kyuura_engine import diagnostics as D
from kyuura_engine import replay_record as R
from kyuura_engine import snapshot as SN
from kyuura_engine import view_record as V
from kyuura_engine.conventions import UNRECORDED
from kyuura_engine.engine import check_invariants
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import Phase
from tests import helpers as H
from tests.test_replay_record_v0_153 import DECKS, HALT_DECK
from tests.test_replay_run_v0_154 import DRY_DECKS, dry_command

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "state-snapshot-v0.157.md"
VIEWERS = (0, 1, None)
SETS = (None, "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1")
ENDED = (Phase.GAME_OVER, Phase.HALTED)


# ---------------------------------------------------------------- 比べる値


def full(state):
    """保存しない状態と復元した状態で比べる値: 保存した全項目（スナップショットの state）・U3 の確認値・乱数・今と過去の区間のログ・3 者の観測。"""
    return {"snapshot": SN.save_snapshot(state).data["state"], "check": R.checks(state), "rng": state.rng.getstate(),
            "log": [dict(e) for e in state.log], "segments": [[dict(e) for e in s.log] for s in state.segments],
            "observe": {v: observe(state, v) for v in VIEWERS}}


def result_items(result):
    """操作の結果のうち比べるもの（outcome・status・診断・停止の公開の診断・次の操作・規約・本人と相手と観戦者への結果・検証者用の停止コードと文）。"""
    v = result.verifier
    return (result.outcome, result.status, result.stage, result.diagnosis, result.halt, result.continuable, result.next, result.convention_set,
            {viewer: result.view_for(viewer) for viewer in VIEWERS}, v.engine_code, v.raw_message, v.halt_code, v.halt_message)


def roundtrip(test, state):
    snapshot = SN.save_snapshot(state)
    report = SN.restore_snapshot(SN.dumps_snapshot(snapshot))
    test.assertEqual((report.status, report.problems), (SN.RESTORED, ()))
    test.assertIsNot(report.state, state)
    return report.state


def submitter(command):
    player = getattr(command, "player", None)
    return player if player in (0, 1) else None


def continue_both(test, state, policy, steps):
    """``state`` を保存して復元し、元の状態と復元した状態へ同じ操作を送って、各境界で比べる。最後の (元, 復元) を返す。"""
    restored = roundtrip(test, state)
    test.assertEqual(full(restored), full(state))
    a, b = state, restored
    for step in range(steps):
        command = policy(a, step)
        if command is None:
            break
        ra = A.submit(a, command, submitter=submitter(command))
        rb = A.submit(b, command, submitter=submitter(command))
        test.assertEqual(result_items(ra), result_items(rb), step)
        if ra.outcome == D.ACCEPTED:
            a, b = ra.state, rb.state
        test.assertEqual(full(a), full(b), step)
    return a, b


def pikachu_policy(seed, *, probe=True):
    """ピカチュウの方策。``probe`` なら、ときどき番でないプレイヤーの番の終わりと、決定に違う id の答えを混ぜる（拒否。F3）。"""
    def policy(state, step):
        if state.phase in ENDED:
            return EndTurn(0) if step % 2 == 0 else None  # 終局・停止のあとも 1 度だけ送る（拒否）
        if state.phase == Phase.SUDDEN_DEATH:
            return StartSuddenDeath()
        if probe and step % 7 == 3 and state.phase == Phase.MAIN:
            return EndTurn(1 - state.current_player)
        if probe and step % 11 == 5 and state.decision is not None:
            d = state.decision
            return ResolveDecision(d.player, d.id + 7, d.options[:d.min_choices])
        return H.trainer_policy_command(state, janken_winner=seed % 2)
    return policy


def advance(state, policy, steps, *, until=None):
    """保存しないで ``steps`` 回だけ（``until`` が真になれば止める）受理した操作で進める。"""
    for step in range(steps):
        if until is not None and until(state):
            break
        if state.phase in ENDED:
            break
        command = policy(state, step)
        result = A.submit(state, command, submitter=submitter(command))
        if result.outcome == D.ACCEPTED:
            state = result.state
    return state


def start(deck0, deck1, seed, conventions=None):
    options = {} if conventions is None else {"conventions": conventions}
    return new_game(deck0, deck1, seed, **options)


# ---------------------------------------------------------------- F1・F3・F5・F6・F7: new_game からの合法な操作の列


class LegalSequenceTest(unittest.TestCase):
    def test_f1_f3_f7_normal_play_in_three_sets(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                policy = pikachu_policy(9)
                state = start(*DECKS, 9, conventions)
                a, _b = continue_both(self, state, policy, 12)  # 準備から（ジャンケン・ポケモンを出す）
                for steps in (40, 80):
                    state = advance(a, policy, steps)
                    a, _b = continue_both(self, state, policy, 15)
                self.assertEqual(a.conventions, C.registered_identity(C.parse_key(conventions or "CS-KYUURA-CURRENT@1")))

    def test_f6_sudden_death_and_segments(self):
        policy = pikachu_policy(9, probe=False)
        state = advance(start(*DECKS, 9), policy, 6000, until=lambda s: s.phase == Phase.SUDDEN_DEATH)
        self.assertIs(state.phase, Phase.SUDDEN_DEATH)
        self.assertEqual(D.status_of(roundtrip(self, state)), D.SUDDEN_DEATH_PENDING)
        a, _ = continue_both(self, state, policy, 20)  # StartSuddenDeath（保存した乱数の続きで切る）と延長戦の準備
        self.assertEqual(a.segment_index, 1)
        self.assertEqual(a.initial_prize_count, a.rules.sudden_death_prize_count)
        middle = advance(a, policy, 30)
        a, b = continue_both(self, middle, policy, 20)  # 延長戦の途中（過去の区間のログ・結果・初期の所有者）
        self.assertEqual(len(b.segments), 1)
        self.assertEqual([dict(e) for e in b.segments[0].log], [dict(e) for e in a.segments[0].log])

    def test_f5_game_over_rejects_everything(self):
        policy = pikachu_policy(0, probe=False)
        state = advance(start(*DECKS, 0), policy, 6000)
        self.assertIs(state.phase, Phase.GAME_OVER)
        _a, b = continue_both(self, state, lambda s, step: (EndTurn(0), EndTurn(1), StartSuddenDeath())[step] if step < 3 else None, 3)
        self.assertIs(b.phase, Phase.GAME_OVER)

    def test_same_name_cards_keep_their_uids(self):
        # 同名のカードが複数ある山札から、手札・場・トラッシュへ動いたあとも、uid と card_id・owner・origin の対応が同じ
        state = advance(start(*DECKS, 9), pikachu_policy(9, probe=False), 60)
        names = [c.card_id for c in state.cards.values()]
        self.assertGreater(len(names), len(set(names)))
        restored = roundtrip(self, state)
        self.assertEqual(list(restored.cards.items()), list(state.cards.items()))
        for player in (0, 1):
            for zone in ("deck", "hand", "prizes", "discard"):
                self.assertEqual(getattr(restored.players[player], zone), getattr(state.players[player], zone))


# ---------------------------------------------------------------- F2: 決定待ち


class DecisionTest(unittest.TestCase):
    def test_setup_phases(self):
        # 準備の各段階（ポケモンを出す・切り直しの引く数・ジャンケン）。たねの少ないデッキで切り直しの補償の段階を探す（少数の seed だけ）
        few = H.expand_decklist({H.DRATINI: 1, H.LIGHTNING: 59})
        seen = set()
        for seed in range(40):
            state = new_game(few, list(DECKS[0]), seed)
            if state.phase is Phase.HALTED or state.phase in seen:
                continue
            seen.add(state.phase)
            continue_both(self, state, lambda s, step: H.trainer_policy_command(s, janken_winner=0), 6)
        self.assertIn(Phase.SETUP_PLACEMENT, seen)

    def test_attack_decision_dry_up(self):
        state = advance(start(*DRY_DECKS, 0), lambda s, step: dry_command(s), 100, until=lambda s: s.decision is not None and s.phase == Phase.DECISION)
        self.assertIsNotNone(state.decision)
        self.assertEqual(D.status_of(state), D.AWAITING_DECISION)
        continue_both(self, state, lambda s, step: dry_command(s), 12)

    def test_trainer_decision_with_continuation_context(self):
        # 構築盤面: 挑戦状（使用中のトレーナー・相手の受けるかの決定・置いておくカード）
        from tests.test_hidden_card_trainers_v0_63 import CHALLENGE, challenge_board

        state = challenge_board()
        played = A.submit(state, PlayTrainer(0, next(u for u in state.players[0].hand if state.cards[u].card_id == CHALLENGE)))
        self.assertEqual(played.outcome, D.ACCEPTED)
        waiting = played.state
        self.assertIsNotNone(waiting.decision)
        self.assertIsNotNone(waiting.trainer_in_use)
        self.assertNotEqual(waiting.decision.context, ())  # 処理の続きの情報

        def policy(s, step):
            d = s.decision
            if d is not None and step == 0:
                return ResolveDecision(d.player, d.id, d.options[:d.max_choices])  # 受ける
            return H.trainer_policy_command(s) if s.phase not in ENDED else None
        continue_both(self, waiting, policy, 8)


# ---------------------------------------------------------------- F4: 途中停止・HALTED


class HaltTest(unittest.TestCase):
    def check_halted(self, state):
        self.assertIs(state.phase, Phase.HALTED)
        restored = roundtrip(self, state)
        self.assertEqual((restored.halt, D.status_of(restored)), (state.halt, D.HALTED))  # 停止の文・参照・途中停止の記録を保つ（DS-HALT-TEXT）
        commands = [EndTurn(0), EndTurn(1), StartSuddenDeath(), ResolveDecision(0, 1, ())]
        continue_both(self, state, lambda s, step: commands[step] if step < len(commands) else None, len(commands))
        game = SN.RestoredGame(SN.restore_snapshot(SN.save_snapshot(state)))
        self.assertEqual((game.status, game.continuable), (D.HALTED, False))
        result = game.submit(EndTurn(0))
        self.assertEqual(result.outcome, D.REJECTED)
        self.assertIs(game.state.phase, Phase.HALTED)
        for viewer in VIEWERS:  # 停止の診断用の文は閲覧者へ出さない
            self.assertNotIn(state.halt.message, repr(result.view_for(viewer)))
            self.assertNotIn(state.halt.message, repr(game.view(viewer)))

    def test_interruption_after_accepted_answer(self):
        from tests.test_replay_run_v0_154 import dry_up_halt

        state = dry_up_halt().state
        self.assertIsNotNone(state.halt.interruption)
        self.check_halted(state)

    def test_setup_halt(self):
        self.check_halted(new_game(HALT_DECK, HALT_DECK, 1))


# ---------------------------------------------------------------- F7・F8: 構築盤面


class ConstructedBoardTest(unittest.TestCase):
    """構築盤面（new_game から合法に到達できることは保証しない。DS-CONSTRUCTED）。"""

    def test_f8_face_down_card(self):
        from kyuura_engine import AttachEnergy, RevealFaceDown
        from tests.test_secret_plan_v0_67 import (
            DIGLETT,
            LT_SURGES_SECRET_PLAN,
            board,
            face_down,
            uid_of,
        )

        state = board(hand=(DIGLETT, H.FIGHTING))
        state = A.submit(state, PlayTrainer(0, uid_of(state, LT_SURGES_SECRET_PLAN))).state
        state = A.submit(state, ResolveDecision(0, state.decision.id, (uid_of(state, DIGLETT),))).state
        self.assertTrue(state.face_down_cards)
        hidden = state.face_down_cards[0]
        commands = [AttachEnergy(0, uid_of(state, H.FIGHTING), hidden), RevealFaceDown(0, face_down(state)[0].pokemon_id), EndTurn(0)]
        a, b = continue_both(self, state, lambda s, step: commands[step] if step < len(commands) else None, len(commands))
        self.assertEqual(b.face_down_cards, a.face_down_cards)

    def test_f8_ownership_exchange(self):
        from tests.test_trade_please_v0_130 import swap, swap_board

        state = swap(swap_board(), H.RATTATA, H.RATTATA, True)  # 同名のカード（コラッタ）どうしの交換
        self.assertTrue(state.ownership_changes)
        self.assertTrue(any(c.origin is not None for c in state.cards.values()))
        restored = roundtrip(self, state)
        self.assertEqual(list(restored.cards.items()), list(state.cards.items()))
        continue_both(self, state, lambda s, step: H.trainer_policy_command(s) if s.phase not in ENDED else None, 8)

    def test_f8_persistent_effect_and_markers(self):
        import tests.test_markers_counters_v0_90 as M
        from tests.test_harden_v0_4b import protected

        boards = {"persistent_effect": protected(H.RATTATA),
                  "markers": M.board(M.mon(H.CHANSEY, markers=[M.MARKER_CURSE, M.MARKER_CURSE, (M.MARKER_COLOR, M.EnergyType.FIRE)]))}
        for label, state in boards.items():
            with self.subTest(label):
                self.assertEqual(check_invariants(state), [])
                pokemon = [p for player in state.players for p in player.in_play()]
                self.assertTrue(any(p.persistent_effects or p.markers for p in pokemon))
                continue_both(self, state, lambda s, step: H.trainer_policy_command(s) if s.phase not in ENDED else None, 6)

    def test_f7_side_order_convention(self):
        from tests.test_play_policy_s2a_v0_143 import HD, TL, as_play, both_asleep

        base = as_play(H.with_coin_results(both_asleep(0), HD, TL))
        _a, b = continue_both(self, base, lambda s, step: EndTurn(0) if step == 0 else None, 1)
        self.assertTrue(any(e["kind"] == "convention_applied" for e in b.log[len(base.log):]))

    def test_f7_po_convention(self):
        from tests.test_poison_mist_play_po_v0_145 import PO, earlier_poison, with_set

        base = with_set(earlier_poison(), PO)
        _a, b = continue_both(self, base, lambda s, step: EndTurn(0) if step == 0 else None, 1)
        self.assertTrue(any(e["kind"] == "convention_applied" for e in b.log[len(base.log):]))
        self.assertEqual(b.conventions, C.registered_identity(PO))

    def test_f7_s2a_mulligan_compensation_from_new_game(self):
        few = H.expand_decklist({H.DRATINI: 1, H.LIGHTNING: 59})
        found = 0
        for seed in range(60):
            state = new_game(few, few, seed, conventions="CS-KYUURA-PLAY-S2A@1")
            if not any(e["kind"] == "convention_applied" for e in state.log) or state.phase is Phase.HALTED:
                continue
            found += 1
            continue_both(self, state, lambda s, step: H.trainer_policy_command(s, janken_winner=0) if s.phase not in ENDED else None, 8)
            if found == 2:
                break
        self.assertGreater(found, 0)


# ---------------------------------------------------------------- 保存の境界（S1）


def simple_state():
    return start(*DECKS, 9)


def assert_save_refused(test, state, code):
    before = (repr(state_to_dict(state, format_version=max(FORMAT_VERSIONS))) if not hasattr(state, "_history_probe") else None, state.rng.getstate(),
              tuple(dict(e) for e in state.log))
    with test.assertRaises(SN.SnapshotSaveError) as caught:
        SN.save_snapshot(state)
    test.assertEqual(caught.exception.code, code)
    after = (repr(state_to_dict(state, format_version=max(FORMAT_VERSIONS))) if not hasattr(state, "_history_probe") else None, state.rng.getstate(),
             tuple(dict(e) for e in state.log))
    test.assertEqual(before, after)
    return caught.exception


class SaveBoundaryTest(unittest.TestCase):
    def test_refused_states(self):
        base = advance(simple_state(), pikachu_policy(9, probe=False), 30)
        cases = []
        moves = base.clone()
        moves.pending_moves = ("left_play",)
        cases.append((moves, "pending_moves"))
        probe = base.clone()
        probe._history_probe = object()
        cases.append((probe, "transient_attribute"))
        dup = base.clone()
        dup.players[0].hand.append(dup.players[1].deck[0])
        cases.append((dup, "invariants"))
        legacy = base.clone()
        legacy.conventions = UNRECORDED
        cases.append((legacy, "conventions"))
        foreign = base.clone()
        foreign.effects = copy.copy(base.effects)  # 既定のカードプールの登録表でない登録表（中身が同じでも、入力から作った登録表とは扱わない）
        cases.append((foreign, "effects"))
        float_log = base.clone()
        float_log.log = base.log + (MappingProxyType({"kind": "note", "turn": base.turn_number, "value": 0.5}),)
        cases.append((float_log, "unrepresentable_value"))
        listed = base.clone()
        listed.log = base.log + (MappingProxyType({"kind": "note", "turn": base.turn_number, "value": [1]}),)
        cases.append((listed, "unrepresentable_value"))
        deep = base.clone()
        nested = ()
        for _ in range(SN.MAX_DEPTH):
            nested = (nested,)
        deep.log = base.log + (MappingProxyType({"kind": "note", "turn": base.turn_number, "value": nested}),)
        cases.append((deep, "too_deep"))
        for state, code in cases:
            with self.subTest(code=code):
                error = assert_save_refused(self, state, code)
                self.assertNotIn(str(state.seed), str(error).replace(code, ""))

    def test_unknown_resume_is_refused(self):
        state = advance(start(*DRY_DECKS, 0), lambda s, step: dry_command(s), 100, until=lambda s: s.decision is not None and s.phase == Phase.DECISION)
        bad = state.clone()
        bad.decision = dataclasses.replace(state.decision, resume="resume_not_known_to_this_version")
        assert_save_refused(self, bad, "decision_resume")

    def test_save_does_not_change_the_state(self):
        state = advance(simple_state(), pikachu_policy(9, probe=False), 50)
        before = (repr(state_to_dict(state, format_version=max(FORMAT_VERSIONS))), state.rng.getstate(), tuple(dict(e) for e in state.log), dict(vars(state)))
        snapshot = SN.save_snapshot(state)
        SN.dumps_snapshot(snapshot)
        after = (repr(state_to_dict(state, format_version=max(FORMAT_VERSIONS))), state.rng.getstate(), tuple(dict(e) for e in state.log), dict(vars(state)))
        self.assertEqual(before, after)
        data = snapshot.data
        report = SN.restore_snapshot(snapshot)
        self.assertTrue(report.restored)
        self.assertEqual(snapshot.data, data)  # 復元が入力を変えない

    def test_writer_and_reader_use_the_same_limits(self):
        # 実際の状態の入れ子の深さは上限より十分に浅い。書き出せたものは、読み取りの上限で拒まれない
        for state in (advance(simple_state(), pikachu_policy(9, probe=False), 6000),):
            snapshot = SN.save_snapshot(state)
            self.assertLessEqual(SN._depth(snapshot.data), SN.MAX_DEPTH // 2)
            self.assertTrue(SN.restore_snapshot(SN.dumps_snapshot(snapshot)).restored)
        self.assertEqual((SN.MAX_DEPTH, SN.MAX_RECORD_BYTES), (R.MAX_DEPTH, R.MAX_RECORD_BYTES))


# ---------------------------------------------------------------- F9: 不正・非対応・不整合の入力（S2・S3）


def snapshot_data(state=None):
    return SN.save_snapshot(state or advance(simple_state(), pikachu_policy(9, probe=False), 40)).data


def restore_data(data):
    return SN.restore_snapshot(json.dumps(data, ensure_ascii=False))


SECRET = "SECRET-INPUT-VALUE-7731"


class InvalidInputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_state = advance(simple_state(), pikachu_policy(9, probe=False), 40)
        cls.base = SN.save_snapshot(cls.base_state).data

    def edited(self, edit):
        data = copy.deepcopy(self.base)
        edit(data)
        return restore_data(data)

    def assert_status(self, report, status, code=None):
        self.assertEqual(report.status, status, report.problems)
        self.assertIsNone(report.state)
        if code is not None:
            self.assertIn(code, [p.code for p in report.problems])
        text = repr(report) + " ".join(f"{p.kind} {p.code} {p.path}" for p in report.problems) + report.message
        self.assertNotIn(SECRET, text)

    def test_read_errors(self):
        for text in ("not json", '{"a": NaN}', '{"a": 1, "a": 2}', "[1]", b"\xff\xfe", "[" * 80 + "]" * 80):
            with self.subTest(text=text[:10]):
                self.assert_status(SN.restore_snapshot(text), SN.READ_ERROR)
        with mock.patch.object(R, "MAX_RECORD_BYTES", 100):
            self.assert_status(SN.restore_snapshot(SN.dumps_snapshot(SN.save_snapshot(self.base_state))), SN.READ_ERROR, "too_large")

    def test_malformed(self):
        state = self.base["state"]
        hand = next(i for i, p in enumerate(state["players"]) if p["fields"]["hand"])
        cases = [
            (lambda d: d.update(extra_field=SECRET), "unknown_field"),
            (lambda d: d.pop("check"), "missing_field"),
            (lambda d: d["state"].pop("turn_number"), "missing_field"),
            (lambda d: d["state"].update(future_field=SECRET), "unknown_field"),
            (lambda d: d["state"].update(turn_number=True), "type"),  # bool を int として受けない
            (lambda d: d["state"].update(turn_number=1.0), "type"),
            (lambda d: d["state"].update(phase=SECRET), "enum_value"),
            (lambda d: d["state"]["players"][hand]["fields"].update(hand={"0": 1}), "type"),
            (lambda d: d["state"]["players"][0].update(type="os.system"), "record_type_unknown"),
            (lambda d: d["state"]["players"][0].update(type="CardInstance"), "record_type_not_allowed"),
            (lambda d: d["state"]["players"][0]["fields"].update(secret_field=SECRET), "unknown_field"),
            (lambda d: d["state"]["cards"].append(copy.deepcopy(d["state"]["cards"][0])), "duplicate_uid"),
            (lambda d: d["state"]["rng"]["internal"].pop(), "rng"),
            (lambda d: d["state"]["rng"].update(format=SECRET), "rng"),
            (lambda d: d["state"]["log"].append({"kind": "note", "turn": 1, "value": 0.25}), "type"),
            (lambda d: d["state"]["log"].append({"kind": "note", "turn": 1, "value": {"type": SECRET, "fields": {}}}), "record_type_unknown"),
            (lambda d: d["state"]["log"].append({"kind": "note", "turn": 1, "value": {"enum": "Phase", "value": SECRET}}), "enum_value"),
            (lambda d: d["check"].update(log_length="1"), "check"),
            (lambda d: d.update(origin={"game_id": 1}), "origin"),
            (lambda d: d["engine"].update(behavior_digest=SECRET), "engine"),
        ]
        for edit, code in cases:
            with self.subTest(code=code):
                self.assert_status(self.edited(edit), SN.MALFORMED, code)

    def test_unsupported(self):
        cases = [
            (lambda d: d.update({SN.FORMAT_KEY: 2}), "format_version"),
            (lambda d: d["engine"].update(behavior_digest="0" * 64), "implementation_differs"),
            (lambda d: d["engine"].update(instrumentation_digest="0" * 64), "instrumentation_differs"),  # DS-INSTRUMENTATION
            (lambda d: d["engine"].update(version="0.0.1"), "engine_version_differs"),
            (lambda d: d["runtime"].update(python_version=[d["runtime"]["python_version"][0], d["runtime"]["python_version"][1] + 1, 0]), "runtime_differs"),
            (lambda d: d["runtime"]["rng"].update(state_version=99), "rng_scheme_differs"),
            (lambda d: d["dependencies"].update(rules="RULES-OTHER"), "rules_unknown"),
            (lambda d: d["dependencies"].update(card_pool="custom"), "card_pool_not_default"),
            (lambda d: d["dependencies"]["card_data"].update(commit="0" * 40), "card_data_differs"),
            (lambda d: d["dependencies"].update(effects="other-effects"), "effects_differs"),
            (lambda d: d["convention_set"].update(digest="0" * 64), "convention_set_unsupported"),
            (lambda d: d["convention_set"].update(id="CS-NOT-REGISTERED"), "convention_set_unsupported"),
            (lambda d: d["formats"].update(state_export=34), "formats_differ"),
            (lambda d: d["state"]["definitions"].append("CARD-NOT-IN-POOL"), "card_unknown"),
        ]
        for edit, code in cases:
            with self.subTest(code=code):
                self.assert_status(self.edited(edit), SN.NOT_SUPPORTED, code)

    def test_unknown_resume_is_unsupported(self):
        state = advance(start(*DRY_DECKS, 0), lambda s, step: dry_command(s), 100, until=lambda s: s.decision is not None and s.phase == Phase.DECISION)
        data = SN.save_snapshot(state).data
        data["state"]["decision"]["fields"]["resume"] = SECRET
        self.assert_status(restore_data(data), SN.NOT_SUPPORTED, "decision_resume")

    def test_inconsistent(self):
        cases = [
            (lambda d: d["check"].update(state="0" * 64), "check_differs"),
            (lambda d: d["check"].update(rng="0" * 64), "check_differs"),
            (lambda d: d["check"].update(log_length=d["check"]["log_length"] + 1), "check_differs"),
            (lambda d: d["state"].update(rules="RULES-OTHER"), "dependencies_state_mismatch"),
            (lambda d: d["state"]["rng"]["internal"].__setitem__(5, (d["state"]["rng"]["internal"][5] + 1) % 2 ** 32), "check_differs"),
        ]
        for edit, code in cases:
            with self.subTest(code=code):
                self.assert_status(self.edited(edit), SN.INCONSISTENT, code)

    def test_rebuilt_check_does_not_hide_a_broken_state(self):
        # 確認値は作り直せる: 壊した状態から確認値を作り直しても、構造・不変条件の確かめで拒む
        broken_cases = []
        dup = self.base_state.clone()
        dup.players[0].hand.append(dup.players[1].deck[0])  # 同じカードが 2 か所
        broken_cases.append((dup, "invariants"))
        orphan = self.base_state.clone()
        orphan.definitions = MappingProxyType({**orphan.definitions, H.FIRE: SN.load_card_pool().get(H.FIRE)})  # cards にないカードの定義
        broken_cases.append((orphan, "structure"))
        ids = self.base_state.clone()
        ids.next_pokemon_id = 1  # 場のポケモンの番号が採番の状態と合わない
        broken_cases.append((ids, "structure"))
        for state, code in broken_cases:
            with self.subTest(code=code):
                data = copy.deepcopy(self.base)
                data["state"] = SN._encode_state(state)
                data["check"] = R.checks(state)
                self.assert_status(restore_data(data), SN.INCONSISTENT, code)

    def test_internal_error_is_not_converted(self):
        text = SN.dumps_snapshot(SN.save_snapshot(self.base_state))
        with mock.patch.object(SN, "_assemble", side_effect=KeyError("boom")):
            report = SN.restore_snapshot(text)
        self.assertEqual((report.status, report.state, report.exception_type), (SN.INTERNAL_ERROR, None, "KeyError"))
        self.assertIn("boom", report.traceback)
        self.assertNotIn("boom", repr(report))
        for error in (MemoryError(), KeyboardInterrupt(), SystemExit(3)):
            with self.subTest(error=type(error).__name__), mock.patch.object(SN, "_assemble", side_effect=error), self.assertRaises(type(error)):
                SN.restore_snapshot(text)

    def test_non_snapshot_input_is_a_usage_error(self):
        with self.assertRaises(TypeError):
            SN.restore_snapshot(self.base)


# ---------------------------------------------------------------- 情報境界・ホストへの接続（S6）


class HostAndBoundaryTest(unittest.TestCase):
    def test_repr_and_errors_have_no_secrets(self):
        state = advance(simple_state(), pikachu_policy(9, probe=False), 40)
        snapshot = SN.save_snapshot(state)
        report = SN.restore_snapshot(snapshot)
        rng_text = str(state.rng.getstate()[1][3])
        for text in (repr(snapshot), str(snapshot), repr(report)):
            self.assertNotIn(rng_text, text)
            self.assertNotIn("PMCG", text)
            self.assertNotIn("seed", text)

    def test_restored_game_continues_like_the_original(self):
        policy = pikachu_policy(9)
        state = advance(simple_state(), policy, 40)
        game = SN.RestoredGame(SN.restore_snapshot(SN.dumps_snapshot(SN.save_snapshot(state))), viewers=VIEWERS)
        recorders = {v: V.ViewRecorder.attach(v, state) for v in VIEWERS}  # 保存しなかった場合の閲覧用記録（同じ時点から）
        self.assertIsNone(game.full_record)
        self.assertEqual(game.state.conventions, state.conventions)
        original = state
        for step in range(25):
            command = policy(original, step)
            if command is None:
                break
            expected = A.submit(original, command, submitter=submitter(command))
            for r in recorders.values():
                r.add(expected)
            actual = game.submit(command, submitter=submitter(command))
            self.assertEqual(result_items(actual), result_items(expected))
            if expected.outcome == D.ACCEPTED:
                original = expected.state
            self.assertEqual(full(game.state), full(original))
        closed = game.close()
        for viewer in VIEWERS:
            record = closed[viewer]
            self.assertEqual(record.data, recorders[viewer].close().data)
            self.assertEqual(record.data["header"]["origin"], V.ORIGIN_ATTACHED)  # 復元の前の各イベントの時点の知識を復元したとはしない
            self.assertEqual(V.validate_view_record(record).status, V.STRUCTURE_VALID)
            text = json.dumps(record.data, ensure_ascii=False)
            for key in ("rng", "kyuura_snapshot_format", "behavior_digest", '"check"'):
                self.assertNotIn(key, text)

    def test_only_restored_reports_can_start_a_game(self):
        bad = SN.restore_snapshot("not json")
        with self.assertRaises(SN.SnapshotNotRestoredError):
            SN.RestoredGame(bad)
        with self.assertRaises(SN.SnapshotNotRestoredError):
            SN.RestoredGame(SN.RestoreReport(status=SN.RESTORED, problems=()))  # 状態のない結果

    def test_no_api_to_swap_conventions_or_resume_a_full_record(self):
        names = set(dir(SN.RestoredGame))
        self.assertFalse({n for n in names if "convention" in n or "resume" in n or "unhalt" in n})
        self.assertFalse(hasattr(R.ReplayCollector, "from_state"))
        self.assertFalse(hasattr(R.ReplayCollector, "attach"))

    def test_halted_view_after_restore_has_no_diagnostic_text(self):
        state = new_game(HALT_DECK, HALT_DECK, 1)
        game = SN.RestoredGame(SN.restore_snapshot(SN.save_snapshot(state)), viewers=VIEWERS)
        for viewer in VIEWERS:
            self.assertNotIn(state.halt.message, json.dumps(game.view_record(viewer).data, ensure_ascii=False))


# ---------------------------------------------------------------- 対応表・文書


class CodecTest(unittest.TestCase):
    def test_codec_has_no_gaps(self):
        self.assertEqual(SN.codec_problems(), [])

    def test_power_use_records_with_three_values(self):
        # 監査で見つけた注釈と値の違い: のせたカードの特殊能力の記録は 3 つの値（v0.49）。2 つか 3 つだけを受け、ほかの長さ・リストは表さない
        t = SN._CODEC["GameState"]["power_uses_this_turn"]
        value = ((3, 0), (4, 1, 17))
        encoded = SN._encode(value, t, "$")
        self.assertEqual(encoded, [[3, 0], [4, 1, 17]])
        self.assertEqual(SN._decode(encoded, t, "$"), value)
        for bad in (((3,),), ((1, 2, 3, 4),), ([3, 0],), ((True, 0),)):
            with self.subTest(bad=bad), self.assertRaises(SN._Unrepresentable):
                SN._encode(bad, t, "$")
        with self.assertRaises(SN._Stop):
            SN._decode([[1, 2, 3, 4]], t, "$")

    def test_new_field_or_type_is_detected(self):
        from kyuura_engine import state as S

        @dataclasses.dataclass(frozen=True)
        class FutureRecordForTest:
            value: float

        with mock.patch.object(S, "FutureRecordForTest", FutureRecordForTest, create=True):
            FutureRecordForTest.__module__ = S.__name__
            _table, gaps = SN._build_codec()  # 浮動小数の項目は対応表にない
        self.assertTrue(any("FutureRecordForTest" in g for g in gaps), gaps)
        with mock.patch.object(SN, "RESOLVED_FIELDS", ("rules", "definitions", "effects")):
            self.assertIn("GameState.conventions の扱いが型の対応表にない", SN.codec_problems())

    def test_codec_matches_the_classification(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("build_state_snapshot_design", ROOT / "scripts" / "build_state_snapshot_design.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        SPEC = module.SPEC
        codec = SN.codec_fields()
        for type_name, fields in SPEC["explicit_types"].items():
            if type_name == "RuleSet":  # GameState.rules の識別から解決する（値の型の対応表に入れない）
                continue
            for name, item in fields.items():
                with self.subTest(field=f"{type_name}.{name}"):
                    self.assertEqual(codec[type_name][name], item["category"])
        for type_name, fields in SPEC["value_record_types"].items():
            self.assertEqual(set(codec[type_name]), set(fields))

    def test_document(self):
        text = DOC.read_text(encoding="utf-8")
        for word in ("save_snapshot", "restore_snapshot", "RestoredGame", "S5", "F9", "DS-DEPTH"):
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()

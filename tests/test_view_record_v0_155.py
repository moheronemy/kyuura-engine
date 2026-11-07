"""v0.155（docs/view-record-v0.155.md）: 閲覧用記録（U5）。

盤面の種類（docs 7 章）:
- new_game からの合法な操作の列（``ViewHost``）: ピカチュウのデッキの方策（seed 9 はサドン・デスから延長戦、seed 0 は終局）、ファイヤー対ラッキー（seed 0 は受理した結果の途中停止）
- 構築盤面からの合法な操作（``ViewRecorder.attach``）: v0.150・v0.151 の双子（山札とうらのサイドの配分だけが違う）
- 補助関数だけの確かめ: 構造の検証・読み取り
- 例外を差し込む確かめ: 内部エラー（``adapter.apply_command`` を置きかえる）
停止コードの文字列はテストの中に書かない。
"""

from __future__ import annotations

import copy
import json
import pathlib
import unittest
from unittest import mock

from kyuura_engine import EndTurn, ResolveDecision, StartSuddenDeath, UseAttack, observe
from kyuura_engine import adapter as A
from kyuura_engine import conventions as C
from kyuura_engine import diagnostics as D
from kyuura_engine import replay_record as R
from kyuura_engine import replay_run as RR
from kyuura_engine import view_record as V
from kyuura_engine.state import Phase
from tests import helpers as H
from tests import test_deck_content_prechecks_v0_147 as V147
from tests import test_deck_search_decision_presence_v0_150 as V150
from tests import test_deck_search_stop_oracles_v0_151 as V151
from tests.test_replay_run_v0_154 import DRY_DECKS, dry_command

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "view-record-v0.155.md"
SPEC = ROOT / "docs" / "diagnostics-replay-api-design.json"
DECKS = (H.PIKACHU_DECK, H.PIKACHU_DECK_B)
VIEWERS = (0, 1, None)
SETS = (None, "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1")
P = H.POTION


def play(seed, *, probe_player=None, full_record=True, max_steps=6000, snapshots=None, conventions=None):
    """ViewHost でピカチュウの方策の操作を送る（サドン・デスなら延長戦を 1 回始める）。``probe_player`` なら、そのプレイヤーだけが、番でないときの番の終わりと、自分の決定への違う id の
    答えを送る（拒否）。``snapshots`` には、ステップごとに (閲覧者 1 の記録, ホストの状態) を入れる。"""
    host, start = V.ViewHost.start(*DECKS, seed, full_record=full_record, conventions=conventions)
    assert start.outcome == D.ACCEPTED
    segments = 1
    for step in range(max_steps):
        state = host.state
        if state.phase in (Phase.GAME_OVER, Phase.HALTED) or (state.phase == Phase.SUDDEN_DEATH and segments >= 2):
            break
        if state.phase == Phase.SUDDEN_DEATH:
            host.submit(StartSuddenDeath())
            segments += 1
            continue
        if probe_player is not None and step % 7 == 3:
            if state.phase == Phase.MAIN and state.decision is None and state.current_player != probe_player:
                assert host.submit(EndTurn(probe_player), submitter=probe_player).outcome == D.REJECTED
            d = state.decision
            if d is not None and d.player == probe_player:
                assert host.submit(ResolveDecision(d.player, d.id + 9, ()), submitter=d.player).outcome == D.REJECTED
        command = H.trainer_policy_command(state, janken_winner=seed % 2)
        player = getattr(command, "player", None)
        assert host.submit(command, submitter=player if player in (0, 1) else None).outcome == D.ACCEPTED
        if snapshots is not None:
            snapshots.append((host.view_record(1), host.state))
    return host


def setUpModule():
    global PLAIN, PROBED, PROBED_FULL, OVER, SNAPSHOTS
    SNAPSHOTS = []
    PLAIN = play(9, snapshots=SNAPSHOTS).close()
    PROBED_FULL, PROBED = play(9, probe_player=0).close()
    _, OVER = play(0).close()
    PLAIN = PLAIN[1]


def without_rejections(record):
    data = copy.deepcopy(record.data)
    data["entries"] = [e for e in data["entries"] if e["kind"] != V.KIND_OWN_REJECTION]
    for n, e in enumerate(data["entries"], 1):
        e["n"] = n
    data["end"]["entries"] = len(data["entries"])
    return data


class CollectionTest(unittest.TestCase):
    def test_each_viewer_round_trip_and_validation(self):
        for viewer in VIEWERS:
            with self.subTest(viewer=viewer):
                record = PLAIN[viewer]
                back = V.loads_view_record(V.dumps_view_record(record))
                self.assertEqual(back.data, record.data)
                rep = V.validate_view_record(back)
                self.assertEqual((rep.status, rep.complete, rep.end_state, rep.replay_verified), (V.STRUCTURE_VALID, True, V.END_CLOSED, False), rep.problems)
                header = record.data["header"]
                self.assertEqual((header["viewer"], header["origin"], header["role"]), (viewer, V.ORIGIN_NEW_GAME, "spectator" if viewer is None else "player"))
                self.assertEqual(header["own_decklist"], None if viewer is None else sorted(DECKS[viewer]))
                self.assertEqual([e["n"] for e in record.data["entries"]], list(range(1, len(record.data["entries"]) + 1)))

    def test_rejections_only_for_the_sender(self):
        # 本人（プレイヤー 0）だけが拒否を試した対戦: 相手・観戦者の記録は、拒否のない対戦の記録と連番・件数を含めて同じ
        for viewer in (1, None):
            self.assertEqual(PROBED[viewer].data, PLAIN[viewer].data)
        own = [e for e in PROBED[0].data["entries"] if e["kind"] == V.KIND_OWN_REJECTION]
        self.assertTrue(own)
        self.assertEqual(without_rejections(PROBED[0]), PLAIN[0].data)
        for entry in own:
            notice = entry["notice"]
            self.assertEqual((notice["outcome"], notice["role"], notice["category"]), (D.REJECTED, "actor", D.INVALID_INPUT))
            self.assertNotIn("operation_id", notice)
            self.assertIn(notice["message"], {e.text for e in D.default_catalog().codes.values()} | set(D.default_catalog().subkind_texts.values()))

    def test_no_forbidden_fields(self):
        for record in (*PLAIN.values(), *PROBED.values(), *OVER.values()):
            found = []
            V._forbidden(record.data, "$", found)
            self.assertEqual(found, [])
            text = V.dumps_view_record(record)
            for word in ('"seed"', '"rng_state_sha256"', '"decklists"', '"seq"', '"accepted_index"', '"operation_id"', '"command":', "traceback"):  # 項目名として
                self.assertNotIn(word, text.replace('"hidden":{"seed"', ""))

    def test_conversion_from_full_record_matches_runtime(self):
        report, views = V.view_records_from_replay(PROBED_FULL)
        self.assertEqual(report.status, RR.SUCCEEDED)
        for viewer in VIEWERS:
            self.assertEqual(views[viewer].data, PROBED[viewer].data)

    def test_conversion_refuses_unverified_records(self):
        data = copy.deepcopy(PROBED_FULL.data)
        next(o for o in data["operations"] if o["outcome"] == D.ACCEPTED and o["seq"] > 20)["check"]["rng"] = "0" * 64
        report, views = V.view_records_from_replay(data)
        self.assertEqual((report.status, views), (RR.DIVERGED, None))
        data = copy.deepcopy(PROBED_FULL.data)
        data["end"] = None
        report, views = V.view_records_from_replay(data)
        self.assertEqual((report.status, views), (RR.INCOMPLETE, None))

    def test_viewer_is_fixed_and_not_a_verifier(self):
        host, _ = V.ViewHost.start(*DECKS, 3, viewers=(1,), full_record=False)
        for bad in ("verifier", True, 2):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                host.view_record(bad)
        with self.assertRaises(KeyError):
            host.view_record(0)  # 作るときに決めた閲覧者のほかは作らない
        with self.assertRaises(TypeError):
            V.ViewRecorder(object(), 0, host.state, V.ORIGIN_NEW_GAME, {})
        with self.assertRaises(ValueError):
            V.ViewRecorder.attach("verifier", host.state)
        self.assertFalse(hasattr(V.ViewRecord, "viewer_setter"))
        text = repr(host.view_record(1))
        self.assertNotIn("decklist", text)


class KnowledgeTest(unittest.TestCase):
    """各時点の知識: 記録した項目は、あとで公開されても・元の状態が変わっても変わらない。"""

    def test_past_entries_are_frozen(self):
        final = PLAIN[1].data["entries"]
        for snapshot, _state in SNAPSHOTS[::25]:
            entries = snapshot.data["entries"]
            self.assertEqual(final[:len(entries)], entries)

    def test_later_public_cards_are_not_backfilled(self):
        # プレイヤー 0 の手札にあった（閲覧者 1 には見えない）カードが、同じ区間のあとで場・トラッシュ（公開）に出る
        def public_uids(state):
            p = state.players[0]
            uids = set(p.discard)
            for pokemon in p.in_play():
                uids |= set(pokemon.cards()) | set(pokemon.energy)
            return uids
        early_index = next(i for i, (_r, s) in enumerate(SNAPSHOTS) if s.turn_number >= 1 and s.players[0].hand)
        early_state = SNAPSHOTS[early_index][1]
        later_index = next(i for i in range(early_index + 1, len(SNAPSHOTS))
                           if SNAPSHOTS[i][1].segment_index == early_state.segment_index and set(early_state.players[0].hand) & public_uids(SNAPSHOTS[i][1]))
        moved = sorted(set(early_state.players[0].hand) & public_uids(SNAPSHOTS[later_index][1]))
        entries = PLAIN[1].data["entries"]
        early_entry = entries[len(SNAPSHOTS[early_index][0].data["entries"]) - 1]
        later_entry = entries[len(SNAPSHOTS[later_index][0].data["entries"]) - 1]
        self.assertIsNone(early_entry["observation"]["players"][0]["hand"]["cards"])  # その時点は枚数だけ（あとで公開されても埋めない）
        self.assertEqual(early_entry, SNAPSHOTS[early_index][0].data["entries"][-1])
        self.assertIn(f'"card": {moved[0]}', json.dumps(later_entry["observation"]["players"][0], ensure_ascii=False))  # あとの項目では見える

    def test_source_changes_do_not_change_records(self):
        host, _ = V.ViewHost.start(*DECKS, 9, viewers=(1,), full_record=False)
        for _ in range(12):
            host.submit(H.trainer_policy_command(host.state, janken_winner=1))
        before = host.view_record(1).data
        host.state.log = ()  # 元の状態のログを書きかえる（テストだけの操作）
        self.assertEqual(host.view_record(1).data, before)
        copy_ = host.view_record(1).data
        copy_["entries"][0]["observation"]["turn"] = 999
        self.assertEqual(host.view_record(1).data, before)

    def test_events_continue_without_duplication(self):
        # 途中から始めた記録（構築盤面）: 始まりの項目は今の区間のログの写しを持ち、次の項目はその続きの位置から始まる（重ならない・欠けない）
        state = V151.belly_drum([H.FIRE] + [P] * 4)
        recorder = V.ViewRecorder.attach(1, state)
        result = A.submit(state, EndTurn(0))
        recorder.add(result)
        entries = recorder.record().data["entries"]
        self.assertEqual(entries[1]["events"][0]["log_index"], len(state.log))


class PastLogBoundaryTest(unittest.TestCase):
    """v0.156（docs/state-snapshot-design.md 2 章）: うらのカードがあとでおもてになると、visible_log は過去のイベントの uid も見せる（v0.67）。閲覧用記録は、初めて記録した
    ログの位置の内容を固定し、同じ位置を後の項目に出し直さない（構築盤面から合法な操作。マチスの秘策）。"""

    def run_secret_plan(self, viewers=VIEWERS):
        from kyuura_engine import AttachEnergy, PlayTrainer, RevealFaceDown
        from tests.test_secret_plan_v0_67 import (
            DIGLETT,
            LT_SURGES_SECRET_PLAN,
            board,
            face_down,
            uid_of,
        )

        state = board(hand=(DIGLETT, H.FIGHTING))
        recorders = {v: V.ViewRecorder.attach(v, state) for v in viewers}

        def send(command):
            nonlocal state
            result = A.submit(state, command)
            self.assertEqual(result.outcome, D.ACCEPTED)
            for r in recorders.values():
                r.add(result)
            state = result.state
        send(PlayTrainer(0, uid_of(state, LT_SURGES_SECRET_PLAN)))
        send(ResolveDecision(0, state.decision.id, (uid_of(state, DIGLETT),)))
        hidden = state.face_down_cards[0]
        send(AttachEnergy(0, uid_of(state, H.FIGHTING), hidden))  # うらのポケモンにつける: 相手のログの写しでは target の uid を伏せる（v0.67 の _mask_face_down）
        attach_index = next(i for i, e in enumerate(state.log) if e["kind"] == "attach_energy" and e["target"] == hidden)
        send(RevealFaceDown(0, face_down(state)[0].pokemon_id))
        return state, recorders, hidden, attach_index

    def test_revealed_face_down_card_is_not_backfilled(self):
        state, recorders, hidden, placed_index = self.run_secret_plan()
        from kyuura_engine import visible_log
        # 今の visible_log は過去のイベントでも uid を見せる（取り直すと漏れる経路が実際にある）
        self.assertIn(hidden, [v for v in visible_log(state, 1)[placed_index].values() if type(v) is int])
        for viewer in (1, None):
            data = recorders[viewer].close().data
            positions = [(item["segment"], item["log_index"]) for e in data["entries"] for item in e.get("events", [])]
            self.assertEqual(len(positions), len(set(positions)))  # 同じ位置を 2 回出さない
            self.assertEqual(sorted(positions), [(0, i) for i in range(len(state.log))])
            first = next(item["event"] for e in data["entries"] for item in e.get("events", []) if item["log_index"] == placed_index)
            self.assertNotIn(hidden, [v for v in first.values() if type(v) is int])  # 記録した時点は伏せたまま
            reveal_entry = data["entries"][-1]
            self.assertTrue(all(item["log_index"] > placed_index for item in reveal_entry["events"]))
            self.assertIn(f'"card": {hidden}', json.dumps(reveal_entry["events"], ensure_ascii=False))  # おもてにしたイベント自体はその時点で見える
        owner = recorders[0].close().data
        first = next(item["event"] for e in owner["entries"] for item in e.get("events", []) if item["log_index"] == placed_index)
        self.assertIn(hidden, [v for v in first.values() if type(v) is int])  # 持ち主は記録した時点から見える

    def test_attached_start_fixes_the_projection_at_the_start(self):
        # 途中から始めた記録: 始まりの項目の過去のログは、始めた時点の投影（イベントが起きた時点の投影ではない）
        state, _, _hidden, placed_index = self.run_secret_plan(viewers=())
        from kyuura_engine import visible_log
        late = V.ViewRecorder.attach(1, state).close().data
        start_events = late["entries"][0]["events"]
        self.assertEqual(start_events[placed_index]["event"], visible_log(state, 1)[placed_index])
        self.assertEqual(late["header"]["origin"], V.ORIGIN_ATTACHED)


class TwinTest(unittest.TestCase):
    """構築盤面の双子（見る人に同じ情報が見えて、見えない配分だけが違う）で、閲覧用記録も同じ。本人が正当に山札を見たあとは比べない。"""

    def records(self, states, commands, viewers):
        recorders = [{v: V.ViewRecorder.attach(v, s) for v in viewers} for s in states]
        for command in commands:
            for i, s in enumerate(states):
                result = A.submit(s, command(s) if callable(command) else command)
                for r in recorders[i].values():
                    r.add(result)
                if result.outcome == D.ACCEPTED:
                    states[i] = result.state
        return [{v: r.close().data for v, r in rs.items()} for rs in recorders], states

    def test_v151_stop_oracles(self):
        for case in V151.RB2_CASES[:4]:
            with self.subTest(case.name):
                s = V151.board(case, [V151.RAINBOW] + [P] * 5)
                records, _ = self.records([s, V147.swap_hidden(s, V151.RAINBOW)], [UseAttack(0, 0)], VIEWERS)
                self.assertEqual(records[0], records[1])
        s = V151.belly_drum([H.FIRE] + [P] * 4)
        records, _ = self.records([s, V147.swap_hidden(s, H.FIRE)], [UseAttack(0, 0)], VIEWERS)
        self.assertEqual(records[0], records[1])

    def test_v150_search_decision(self):
        for path in V150.PATHS[:6]:
            with self.subTest(path.name):
                s = V150.board(path)
                records, states = self.records([s, V147.swap_hidden(s, path.target)], V150.steps_to_search(path), VIEWERS)
                for viewer in (1, None):
                    self.assertEqual(records[0][viewer], records[1][viewer])
                    decision = records[0][viewer]["entries"][-1]["observation"]["decision"]
                    self.assertEqual(decision, observe(states[0], viewer)["decision"])  # 観測が許す範囲だけ
                    self.assertNotIn("options", decision)
                own = records[0][0]["entries"][-1]["observation"]["decision"]
                self.assertIn("options", own)  # 正当に山札をさがす本人だけが実際の候補を見る


class StatusTest(unittest.TestCase):
    def test_halt_after_accepted_operation(self):
        host, _ = V.ViewHost.start(*DRY_DECKS, 0)
        for _ in range(100):
            if host.state.phase is Phase.HALTED:
                break
            host.submit(dry_command(host.state))
        full, views = host.close()
        self.assertEqual(RR.replay(full).status, RR.SUCCEEDED)
        for viewer in VIEWERS:
            last = views[viewer].data["entries"][-1]["notice"]
            self.assertEqual((last["status"], last["halt"]["category"], last["halt"]["interrupted"]), (D.HALTED, D.RULING_UNRESOLVED, True))
            self.assertEqual((views[viewer].data["end"]["state"], views[viewer].data["end"]["status"]), (V.END_CLOSED, D.HALTED))

    def test_game_over_and_decision_close(self):
        for viewer in VIEWERS:
            self.assertEqual(OVER[viewer].data["end"]["status"], D.GAME_OVER)
        host, _ = V.ViewHost.start(*DECKS, 9, full_record=False)
        while host.state.decision is None:
            host.submit(H.trainer_policy_command(host.state, janken_winner=1))
        _, views = host.close()
        decider = host.state.decision.player
        for viewer in VIEWERS:
            notice = views[viewer].data["entries"][-1]["notice"]
            self.assertEqual((notice["status"], notice["next"]), (D.AWAITING_DECISION, [{"kind": D.NEXT_ANSWER_DECISION, "player": decider}]))

    def test_sudden_death_segments(self):
        record = PLAIN[None].data
        segments = [e["segment"] for e in record["entries"]]
        self.assertEqual(sorted(set(segments)), [0, 1])
        boundary = next(e for e in record["entries"] if e["segment"] == 1)
        self.assertEqual(boundary["events"][-1]["segment"], 1)
        indexes = {}
        for e in record["entries"]:
            for item in e["events"]:
                indexes.setdefault(item["segment"], []).append(item["log_index"])
        for seg, values in indexes.items():
            self.assertEqual(values, list(range(len(values))), seg)
        pending = [e for e in record["entries"] if e["notice"]["status"] == D.SUDDEN_DEATH_PENDING]
        self.assertTrue(pending)

    def test_internal_error_and_abort(self):
        host, _ = V.ViewHost.start(*DECKS, 9, full_record=False)
        for _ in range(10):
            host.submit(H.trainer_policy_command(host.state, janken_winner=1))

        def boom(state, command):
            raise RuntimeError("secret 31337")
        with mock.patch.object(A, "apply_command", boom):
            result = host.submit(H.trainer_policy_command(host.state, janken_winner=1))
        self.assertEqual(result.outcome, D.FAILED)
        _, views = host.close()
        for viewer in VIEWERS:
            data = views[viewer].data
            text = V.dumps_view_record(views[viewer])
            self.assertNotIn("31337", text)
            self.assertNotIn("RuntimeError", text)
            self.assertEqual((data["entries"][-1]["kind"], data["end"]["state"], data["end"]["status"]), (V.KIND_UNAVAILABLE, V.END_ABORTED, D.UNAVAILABLE))
            self.assertEqual(V.validate_view_record(data).status, V.STRUCTURE_VALID)

    def test_three_convention_sets(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                host = play(5, conventions=conventions, full_record=False, max_steps=40)
                _, views = host.close()
                key = C.parse_key(conventions) if conventions else C.DEFAULT_SET
                expected = C.registered_identity(key).record()
                for viewer in VIEWERS:
                    self.assertEqual(views[viewer].data["header"]["convention_set"], {k: expected[k] for k in ("id", "version", "digest")})
                    self.assertEqual(V.validate_view_record(views[viewer]).status, V.STRUCTURE_VALID)


def entries(d):
    return d["entries"]


class BrokenTest(unittest.TestCase):
    def check(self, edit, status, code):
        data = copy.deepcopy(PROBED[0].data)
        edit(data)
        rep = V.validate_view_record(data)
        self.assertEqual(rep.status, status, rep.problems)
        self.assertIn(code, {p.code for p in rep.problems})

    def test_detected(self):
        self.check(lambda d: entries(d)[3]["observation"].update(seed=9), V.MALFORMED, "forbidden_field")
        self.check(lambda d: entries(d)[3]["events"][0]["event"].update(operation_id="x") if entries(d)[3]["events"] else entries(d)[3].update(command=1),
                   V.MALFORMED, "forbidden_field")
        self.check(lambda d: d.update(extra=1), V.MALFORMED, "unknown_field")
        self.check(lambda d: entries(d)[5].update(extra=1), V.MALFORMED, "entry_fields")
        self.check(lambda d: entries(d).pop(4), V.INCONSISTENT, "n_out_of_order")
        self.check(lambda d: entries(d)[6]["notice"].update(viewer=1), V.INCONSISTENT, "notice_viewer_or_status")
        self.check(lambda d: entries(d)[7].update(segment=3), V.INCONSISTENT, "segment_jump")
        self.check(lambda d: d["end"].update(entries=1), V.INCONSISTENT, "end_entry_count")
        self.check(lambda d: d.update(kyuura_view_format=2), V.UNSUPPORTED, "format_unknown")
        self.check(lambda d: d.update(end=None), V.INCOMPLETE, "end_missing")
        self.check(lambda d: d["header"].update(viewer=None), V.INCONSISTENT, "header_role_or_origin")

        def duplicate_event(d):
            target = next(e for e in entries(d) if e.get("events"))
            target["events"].append(copy.deepcopy(target["events"][-1]))
        self.check(duplicate_event, V.INCONSISTENT, "log_index_gap_or_duplicate")

    def test_reading_errors(self):
        secret = "SECRET-77"
        for code, text in {"duplicate_key": '{"a": 1, "a": "' + secret + '"}', "non_finite_number": '{"a": NaN, "b": "' + secret + '"}',
                           "not_object": '["' + secret + '"]', "too_deep": '{"a":' * 100 + '"' + secret + '"' + "}" * 100}.items():
            with self.subTest(code), self.assertRaises(R.RecordFormatError) as ctx:
                V.loads_view_record(text)
            self.assertEqual(ctx.exception.code, code)
            self.assertNotIn(secret, str(ctx.exception))
        with mock.patch.object(R, "MAX_RECORD_BYTES", 10), self.assertRaises(R.RecordFormatError):
            V.loads_view_record(V.dumps_view_record(PLAIN[1]))


class ContractTest(unittest.TestCase):
    """U1〜U4 の約束と既存の API: 完全な記録は再現でき、閲覧用記録とは別の形式。"""

    def test_full_record_still_replays(self):
        self.assertEqual(R.validate_record(PROBED_FULL).status, R.STRUCTURE_VALID)
        self.assertEqual(RR.replay(PROBED_FULL).status, RR.SUCCEEDED)
        self.assertNotIn(V.VIEW_FORMAT_KEY, PROBED_FULL.data)
        self.assertNotIn(R.FORMAT_KEY, PLAIN[1].data)
        import kyuura_engine
        self.assertNotIn("ViewHost", kyuura_engine.__all__)


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("ViewHost", "view_records_from_replay", "validate_view_record", "own_rejection", "kyuura_view_format", "合法手"):
            self.assertIn(needle, text)

    def test_spec(self):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        units = {u["id"]: u["status"] for u in spec["units"]}
        self.assertEqual((units["U5"], units["U7"]), ("implemented", "planned"))  # v0.158: U6 の状態は後の版で変わる（partial・implemented。test_state_snapshot_design が見る）
        # v0.156: D-SNAPSHOT-BASE・D-HALT-SNAPSHOT は、後の原則の採用（ADOPT-U6-PRINCIPLES）だけで決まった（この版の採用では決めていない）
        later = next(a for a in spec["adoptions"] if a["id"] == "ADOPT-U6-PRINCIPLES")
        decided = {d["id"]: d for d in spec["decisions"]}
        for key in ("D-SNAPSHOT-BASE", "D-HALT-SNAPSHOT"):
            self.assertEqual((decided[key]["status"], decided[key]["adoption"]), ("adopted", "ADOPT-U6-PRINCIPLES"))
            self.assertIn(key, later["decisions"])


if __name__ == "__main__":
    unittest.main()

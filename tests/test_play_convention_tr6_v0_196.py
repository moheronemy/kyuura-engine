"""v0.196（docs/play-convention-tr6-v0.196.md）: エナジーへんかんの回収の決定で 0 枚と答えたときのプレイ用の続行規約 PC-ENERGY-CONVERSION-ZERO@1（開発用の集合 CS-KYUURA-PLAY-TR6@1）。

利用者の採用（2026-11-21。設計 docs/h4-recover-zero-design.md の案 B）: 化石の秘密のゴース（PMCG3-029）自身の［エナジーへんかん］と、ピッピ・ピクシーの［ゆびをふる］で相手のゴース自身の
［エナジーへんかん］を使う経路で、回収の答えが空なら、受理して何も手札に加えずに次の要素（自分への 10 ダメージ）へ進む。明示的に選んだ TR6 の集合だけで有効。プレイ用の取り決めで、
史実の裁定の確定ではない（H4 の停止コードは厳密側・既存の集合・対象の外の経路で active のまま）。

確かめの種類を分ける（設計 6 章の S1〜S9）:

- 構築盤面（tests.helpers.build_test_state。規約集合だけを置きかえた写し ``with_set``）: 登録・照会・厳密側と TR6 側の差・受理のあとの状態と公開ログ・1 枚・2 枚の対照・コピーの経路・
  メタモンの［へんしん］（対象の外）・H5・ポケモンタワー・［アレルギーほうし］・自分へのダメージのきぜつ・ほかの場面・合法手 API・ログの監査
- 本物の runner（スナップショットから復元した構築盤面）と逐次バッチの判定の入口（``batch.judge_trace``）: 受理した 0 枚の答えは expected、厳密側は規則 10 の known_stop
- new_game: TR6 を明示して対戦を作れること・既定の集合が変わらないこと（回収の決定への到達は確かめていない。到達の実績とは区別する）
"""

from __future__ import annotations

import copy
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import conventions as C
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine import load_card_pool
from kyuura_engine.commands import ResolveDecision, UseAttack
from kyuura_engine.decisions import RECOVER_ENERGY
from kyuura_engine.engine import apply_command, check_invariants, new_game
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import visible_log
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from tests import helpers as H
from tests.log_audit import s2a_problems

LATEST = max(FORMAT_VERSIONS)
TR6 = ("CS-KYUURA-PLAY-TR6", 1)
TR4 = ("CS-KYUURA-PLAY-TR4", 1)
TR3 = ("CS-KYUURA-PLAY-TR3", 1)
ZERO_ID = "PC-ENERGY-CONVERSION-ZERO"
H4 = "UNRESOLVED_RECOVER_ZERO_ENERGY"
ER9 = "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE"
ER10 = "UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET"
SR2 = "UNRESOLVED_SUPER_ENERGY_RETRIEVAL_ZERO_CHOICE"
STRICT_SETS = (C.DEFAULT_SET, TR3, TR4)  # 厳密側（今の挙動の集合）と、この規約を持たない既存の開発用の集合
OTHER_SETS = (C.DEFAULT_SET, (C.S2A_SET_ID, 1), (C.PO_SET_ID, 1), TR3, TR4)
TURN = 7
# 既存の集合の照合値（v0.142〜v0.195 の固定の値。この版で変えない）
EXISTING_SET_DIGESTS = {
    ("CS-KYUURA-CURRENT", 1): "sha256:9a9b95c689d86fa01a5b710984560efda3c08f4dbf1d7c6218094ac8666f3cee",
    ("CS-KYUURA-LEGACY-UNRECORDED", 1): "sha256:abf39e6d87755507a9169537608596246f4ed9a9bf0c2e8794ffa44a97742407",
    ("CS-KYUURA-PLAY-S2A", 1): "sha256:b317a3f050206577bff35ac05c87fdb4224ee28c6c0222e4e7f8460b5e9410c4",
    ("CS-KYUURA-PLAY-PO", 1): "sha256:06d512194feee1857319f0c765ab2162d5259e4519895ed057d176d15fc43528",
    ("CS-KYUURA-PLAY-TR3", 1): "sha256:a7b800cff2a8614d7b181cc3a8a39f68ec4e17be9ceab0a04e75a48c4358ffb4",
    ("CS-KYUURA-PLAY-TR4", 1): "sha256:15af975a643c8d5844bf76e0a85ab20020ca331b01c463aeb344047806435552",
}


def with_set(state, key):
    """盤面を直接作った状態（今の挙動の集合）を、同じ盤面・同じ乱数の別の集合の状態にする（constructed。規約集合だけを置きかえる）。"""
    new = state.clone()
    new.conventions = C.registered_identity(key)
    return new


def snap(state):
    """拒否で変わらないことを確かめる値: 書き出しの全体・乱数・ログ・決定の通し番号。"""
    return repr(state_to_dict(state, format_version=LATEST)), rng_fingerprint(state.rng), tuple(map(repr, state.log)), state.next_decision_id


def answer(state, choices, player=0):
    return apply_command(state, ResolveDecision(player, state.decision.id, tuple(choices)))


def kinds_since(state, n):
    return [e["kind"] for e in state.log[n:]]


def gastly_board(discard=(H.FIRE, H.WATER), damage=0, bench=(H.RATTATA,)):
    return H.build_test_state([{"active": {"card": H.GASTLY, "energy": [H.PSYCHIC, H.PSYCHIC], "damage": damage}, "bench": list(bench), "discard": list(discard)},
                               {"active": H.GROWLITHE, "bench": [H.RATTATA]}], turn_number=TURN)


def metronome_board(copier, discard=(H.FIRE, H.WATER)):
    me = {"card": copier, "energy": [H.PSYCHIC, H.PSYCHIC, H.PSYCHIC]}
    if copier == H.CLEFABLE:
        me["evolved_from"] = H.CLEFAIRY
    return H.build_test_state([{"active": me, "bench": [H.RATTATA], "discard": list(discard)}, {"active": {"card": H.GASTLY, "energy": [H.PSYCHIC, H.PSYCHIC]}}],
                              turn_number=TURN)


def ditto_board():
    return H.build_test_state([{"active": {"card": H.DITTO, "energy": [H.PSYCHIC, H.PSYCHIC]}, "bench": [H.RATTATA], "discard": [H.FIRE, H.WATER]},
                               {"active": {"card": H.GASTLY, "energy": [H.PSYCHIC]}}], turn_number=TURN)


def metronome_index(copier):
    return next(i for i, a in enumerate(load_card_pool().get(copier).attacks) if a.name_ja == "ゆびをふる")


def at_recover(path="gastly", key=C.DEFAULT_SET, **kw):
    """回収の決定（recover_energy）まで進めた状態。path: gastly（元のワザ）・ピッピ・ピクシー（ゆびをふるで相手のゴースのエナジーへんかん）・ditto（へんしん）。"""
    if path == "gastly":
        state = apply_command(with_set(gastly_board(**kw), key), UseAttack(0, 1))
    elif path == "ditto":
        state = apply_command(with_set(ditto_board(), key), UseAttack(0, 1))
    else:
        selecting = apply_command(with_set(metronome_board(path, **kw), key), UseAttack(0, metronome_index(path)))
        assert selecting.decision.kind == "select_attack"
        state = answer(selecting, (1,))  # 相手のゴースのエナジーへんかん
    assert state.decision is not None and state.decision.kind == RECOVER_ENERGY, state.decision
    return state


PATHS = ("gastly", H.CLEFAIRY, H.CLEFABLE)


class RegistrationTest(unittest.TestCase):
    def test_tr6_set_members_and_digests(self):
        spec = C.SETS[TR6]
        self.assertEqual((spec.usage, spec.completeness), (C.USAGE_DEVELOPMENT, C.COMPLETENESS_HALTS))  # 完成したプレイ用の集合ではない
        tr4 = C.SETS[TR4]
        self.assertEqual(len(tr4.members), 24)
        self.assertEqual(spec.members, tr4.members + ((ZERO_ID, 1),))  # TR4@1 の 24 規約と、新しい 1 規約
        self.assertEqual(C.validate(spec), [])
        identity = C.identity_of(spec)
        self.assertEqual(identity.digest, C.PINNED_SET_DIGESTS[TR6])
        for member, version, digest in identity.members:
            self.assertEqual(digest, C.PINNED_CONVENTION_DIGESTS[(member, version)], member)
            self.assertEqual(digest, C.convention_digest(C.CONVENTIONS[(member, version)]), member)
        convention = C.CONVENTIONS[(ZERO_ID, 1)]
        self.assertEqual((convention.layer, convention.approval, convention.scenes), (C.LAYER_CONTINUATION, C.APPROVAL_USER_AGREED, (H4,)))
        self.assertIn("2026-11-21", convention.content["adoption"])
        self.assertIn((ZERO_ID, 1), C.DEFAULT_REGISTRY.implemented_continuations)
        self.assertIn(H4, {s["id"] for s in C.scene_index()["scenes"]})
        self.assertNotIn(("CS-KYUURA-PLAY-TR5", 1), C.SETS)  # TR5 は ER10 の設計の案で使った名前（登録しない）

    def test_existing_sets_and_default_are_unchanged(self):
        for key, digest in EXISTING_SET_DIGESTS.items():
            with self.subTest(key=key):
                self.assertEqual(C.PINNED_SET_DIGESTS[key], digest)
                if key[0] != C.LEGACY_SET_ID:
                    self.assertEqual(C.identity_of(C.SETS[key]).digest, digest)
                self.assertNotIn(ZERO_ID, {m for m, _ in C.SETS[key].members})
        self.assertEqual(C.DEFAULT_SET, (C.CURRENT_SET_ID, 1))
        self.assertEqual(C.default_identity().key, C.DEFAULT_SET)

    def test_lookup_only_in_tr6(self):
        state = gastly_board()
        for key in OTHER_SETS:
            with self.subTest(key=key):
                self.assertIsNone(C.continuation_for(with_set(state, key), H4))
        found = C.continuation_for(with_set(state, TR6), H4)
        self.assertEqual((found.scene, found.convention), (H4, (ZERO_ID, 1)))
        self.assertEqual(C.continuation_for(with_set(state, TR6), ER9).convention, ("PC-ENERGY-RETRIEVAL-ZERO", 1))  # TR4 の規約はそのまま
        for code in (ER10, SR2, "UNRESOLVED_TRAINER_UP_TO_ZERO_CHOICE", "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE"):
            self.assertIsNone(C.continuation_for(with_set(state, TR6), code), code)

    def test_new_game_only_when_selected(self):
        deck = H.expand_decklist({H.DRATINI: 4, H.LIGHTNING: 56})
        self.assertEqual(new_game(deck, deck, 1).conventions.key, C.DEFAULT_SET)
        self.assertEqual(new_game(deck, deck, 1, conventions="CS-KYUURA-PLAY-TR6@1").conventions, C.registered_identity(TR6))


class StrictTest(unittest.TestCase):
    """S1: 厳密側（CURRENT@1）と TR3@1・TR4@1 は今と同じ H4（決定は待ったまま・状態・乱数・ログは変わらない・同じ決定に 1 枚以上で答え直せる）。"""

    def test_strict_sets_keep_h4_on_both_paths(self):
        for key in STRICT_SETS:
            for path in PATHS:
                with self.subTest(key=key, path=path):
                    state = at_recover(path, key)
                    decision, before = state.decision, snap(state)
                    with self.assertRaises(UnsupportedError) as caught:
                        answer(state, ())
                    self.assertEqual(caught.exception.code, H4)
                    self.assertEqual(D.default_catalog().get(H4).category, D.RULING_UNRESOLVED)
                    self.assertEqual(snap(state), before)
                    self.assertIs(state.decision, decision)
                    again = answer(state, decision.options[:1])  # 同じ決定に答え直せる
                    self.assertIn("recover_energy", kinds_since(again, len(state.log)))


class ZeroAcceptedTest(unittest.TestCase):
    """S2・S4: TR6 では 0 枚を受理して、何も手札に加えずに自分への 10 ダメージへ進む（元のワザと、ゆびをふるの経路）。"""

    def test_zero_is_accepted_and_the_attack_continues(self):
        for path in PATHS:
            with self.subTest(path=path):
                state = at_recover(path, TR6)
                d = state.decision
                me = state.players[0]
                hand, discard, n, damage = list(me.hand), list(me.discard), len(state.log), me.active.damage
                done = answer(state, ())
                kinds = kinds_since(done, n)
                self.assertEqual(kinds[:2], ["convention_applied", "damage"])  # recover_energy は書かない
                self.assertNotIn("recover_energy", kinds)
                self.assertEqual(kinds[2:], kinds_since(answer(state, d.options[:1]), n)[2:])  # 自分へのダメージのあとは 1 枚の答えと同じ（番の終わり・相手の番）
                applied, hurt = done.log[n], done.log[n + 1]
                self.assertEqual(applied, {"kind": "convention_applied", "turn": TURN, "convention": ZERO_ID, "version": 1, "scene": H4, "code": H4, "player": 0,
                                           "available": len(d.options)})
                self.assertEqual((hurt["target"], hurt["player"], hurt["amount"], hurt["effect"]), ("self", 0, 10, f"{H.GASTLY}#1"))
                self.assertIsNone(done.decision)
                self.assertEqual(done.current_player, 1)  # ワザのあと番が移る
                self.assertEqual(done.players[0].hand, hand)  # 手札に加えない
                self.assertEqual(done.players[0].discard, discard)  # 選べたエネルギーはトラッシュのまま
                self.assertEqual(done.players[0].active.damage, damage + 10)  # ワザを使った（コピーした）ポケモンに 10
                self.assertEqual(check_invariants(done), [])
                self.assertEqual(s2a_problems(done), [])

    def test_strict_and_tr6_differ_only_in_the_zero_answer(self):
        """同じ構築盤面で、回収の決定までは同じ（ログ・乱数・決定）。差は 0 枚の答えの submit だけ。"""
        for path in PATHS:
            with self.subTest(path=path):
                strict, tr6 = at_recover(path, C.DEFAULT_SET), at_recover(path, TR6)
                self.assertEqual(strict.log, tr6.log)
                self.assertEqual(rng_fingerprint(strict.rng), rng_fingerprint(tr6.rng))
                self.assertEqual((strict.decision.kind, strict.decision.options, strict.decision.min_choices, strict.decision.max_choices, strict.decision.resume),
                                 (tr6.decision.kind, tr6.decision.options, tr6.decision.min_choices, tr6.decision.max_choices, tr6.decision.resume))
                self.assertEqual(strict.decision.context_value("copied"), None if path == "gastly" else (H.GASTLY, 1))

    def test_one_or_two_cards_are_unchanged(self):
        """S3: 1 枚・2 枚の答えは両方の集合で同じ（同じ出来事・同じ手札とトラッシュ・convention_applied なし）。不正な答えは同じコード。"""
        for path in PATHS:
            for count in (1, 2):
                with self.subTest(path=path, count=count):
                    strict, tr6 = at_recover(path, C.DEFAULT_SET), at_recover(path, TR6)
                    a, b = answer(strict, strict.decision.options[:count]), answer(tr6, tr6.decision.options[:count])
                    self.assertEqual(a.log, b.log)
                    self.assertNotIn("convention_applied", kinds_since(b, len(tr6.log)))
                    self.assertEqual((a.players[0].hand, a.players[0].discard), (b.players[0].hand, b.players[0].discard))
            tr6 = at_recover(path, TR6)
            d = tr6.decision
            for choices, code in (((d.options[0],) * 2, "DUPLICATE_CHOICE"), (d.options + (d.options[0],), "INVALID_CHOICE_COUNT")):
                with self.assertRaises(IllegalActionError) as bad:
                    answer(tr6, choices)
                self.assertEqual(bad.exception.code, code)
            self.assertIn("convention_applied", kinds_since(answer(tr6, ()), len(tr6.log)))  # 不正な答えのあとも同じ決定に 0 枚で答えられる


class OutOfScopeTest(unittest.TestCase):
    """メタモンの［へんしん］・H5・ポケモンタワー・［アレルギーほうし］（S5）とほかの場面（S8）。"""

    def test_ditto_transform_keeps_h4_in_tr6(self):
        state = at_recover("ditto", TR6)
        before = snap(state)
        with self.assertRaises(UnsupportedError) as caught:
            answer(state, ())
        self.assertEqual(caught.exception.code, H4)
        self.assertEqual(snap(state), before)
        self.assertIsNone(state.decision.context_value("copied"))

    def test_no_energy_in_the_discard_has_no_decision(self):
        for key in (C.DEFAULT_SET, TR6):
            with self.subTest(key=key):
                state = with_set(gastly_board(discard=()), key)
                done = apply_command(state, UseAttack(0, 1))
                self.assertIsNone(done.decision)
                kinds = kinds_since(done, len(state.log))
                self.assertNotIn("convention_applied", kinds)
                self.assertIn("damage", kinds)

    def test_pokemon_tower_and_allergy_spores_skip_the_element(self):
        from tests.test_damage_reactions_poison_sleep_v0_119 import AllergySporesTest, board as allergy_board, mon as allergy_mon
        from tests.test_remaining_stadiums_v0_74 import mon, placed

        for key in (C.DEFAULT_SET, TR6):
            with self.subTest(key=key, scene="tower"):
                state = with_set(placed(H.POKEMON_TOWER, active=mon(H.GASTLY, (H.PSYCHIC, H.PSYCHIC)), discard=[H.FIRE, H.GRASS]), key)
                done = apply_command(state, UseAttack(0, 1))
                self.assertIsNone(done.decision)
                self.assertNotIn("convention_applied", kinds_since(done, len(state.log)))
            with self.subTest(key=key, scene="allergy"):
                state = with_set(allergy_board(allergy_mon(H.GASTLY, (H.PSYCHIC, H.PSYCHIC)), discard=(H.PSYCHIC, H.PSYCHIC), opponent=allergy_mon(H.HITMONCHAN),
                                               opponent_bench=(AllergySporesTest.PARASECT_BENCH,)), key)
                done = apply_command(state, UseAttack(0, 1))
                self.assertIsNone(done.decision)
                kinds = kinds_since(done, len(state.log))
                self.assertIn("discard_protected", kinds)
                self.assertNotIn("convention_applied", kinds)

    def test_self_damage_knockout_is_the_same_as_one_card(self):
        """S6: ダメージ 40 のゴース（HP 50）。0 枚（TR6）でも 1 枚でも、自分への 10 できぜつし、そのあとの処理（きぜつ・サイド・入れ替えの決定）は同じ。"""
        zero_state = at_recover("gastly", TR6, damage=40)
        n = len(zero_state.log)
        zero = answer(zero_state, ())
        one = answer(zero_state, zero_state.decision.options[:1])
        z, o = kinds_since(zero, n), kinds_since(one, n)
        self.assertEqual(z[0], "convention_applied")
        self.assertEqual(o[0], "recover_energy")
        self.assertEqual(z[1:], o[1:])
        self.assertIn("knock_out", z)
        self.assertEqual((zero.decision.kind if zero.decision else None), (one.decision.kind if one.decision else None))
        self.assertEqual(check_invariants(zero), [])

    def test_other_scenes_are_unchanged_in_tr6(self):
        """S8: エネルギー回収の 0 枚（TR4 の規約で受理）と ER10 は TR6 でも TR4 と同じ。"""
        from tests.test_play_convention_tr4_v0_195 import answer as er_answer, at_retrieve, board as er_board, uid as er_uid
        from kyuura_engine.commands import PlayTrainer

        for key in (TR4, TR6):
            with self.subTest(key=key):
                done = er_answer(at_retrieve(key), 0, ())
                self.assertEqual([e["convention"] for e in done.log if e["kind"] == "convention_applied"], ["PC-ENERGY-RETRIEVAL-ZERO"])
                empty = with_set(er_board(discard=(H.POTION,)), key)
                with self.assertRaises(UnsupportedError) as caught:
                    apply_command(empty, PlayTrainer(0, er_uid(empty, 0, H.ENERGY_RETRIEVAL)))
                self.assertEqual(caught.exception.code, ER10)


class ApiTest(unittest.TestCase):
    """S9: 合法手 API の候補・入力・check は両方の集合で同じ。submit だけが違う（TR6 は受理・全員に見える記録、厳密側は拒否・観測の変化なし）。"""

    def flow(self, path, key):
        host = L.ActionHost(A.HostedGame(at_recover(path, key)))
        session = host.session(0)
        r = session.candidates()
        (cand,) = [c for c in r["candidates"] if c["kind"] == "answer_decision"]
        inputs = session.inputs(r["game"], r["revision"], cand["id"])
        checked = session.check(r["game"], r["revision"], cand["id"], [])
        return host, session, r, cand, inputs, checked

    def strip(self, value):
        value = copy.deepcopy(value)
        if isinstance(value, dict):
            for k in ("game", "revision"):
                value.pop(k, None)
        return value

    def test_candidates_inputs_check_same_submit_differs(self):
        for path in PATHS:
            with self.subTest(path=path):
                s_host, s_session, s_r, s_cand, s_inputs, s_check = self.flow(path, C.DEFAULT_SET)
                t_host, t_session, t_r, t_cand, t_inputs, t_check = self.flow(path, TR6)
                self.assertEqual(self.strip(s_r), self.strip(t_r))
                self.assertEqual(self.strip(s_inputs), self.strip(t_inputs))
                self.assertEqual(self.strip(s_check), self.strip(t_check))
                self.assertTrue(t_check["valid"])
                stage = t_inputs["stages"][0]
                self.assertEqual((stage["decision_kind"], stage["count"], stage["decline"]), (RECOVER_ENERGY, {"min": 0, "max": 2}, True))
                viewers = (0, 1, None)
                s_before = [visible_log(s_host.game.state, v) for v in viewers]
                sent = s_session.submit(s_r["game"], s_r["revision"], s_cand["id"], [])
                self.assertEqual((sent.outcome, sent.view.diagnostic_id, sent.view.status), (D.REJECTED, H4, "awaiting_decision"))
                self.assertEqual([visible_log(s_host.game.state, v) for v in viewers], s_before)
                t_before = [len(visible_log(t_host.game.state, v)) for v in viewers]
                sent = t_session.submit(t_r["game"], t_r["revision"], t_cand["id"], [])
                self.assertEqual(sent.outcome, D.ACCEPTED)
                for v, n in zip(viewers, t_before):
                    with self.subTest(viewer=v):
                        added = visible_log(t_host.game.state, v)[n:]
                        self.assertEqual([e["kind"] for e in added][:2], ["convention_applied", "damage"])
                        self.assertEqual(added[0]["available"], 2)


class AuditTest(unittest.TestCase):
    """ログの監査（s2a_problems）は規約の記録を、監査が独立に持つ表とログの並びで照らす（エンジンの登録を信じない）。"""

    def test_audit_accepts_the_record_and_detects_tampering(self):
        for path in PATHS:
            done = answer(at_recover(path, TR6), ())
            self.assertEqual(s2a_problems(done), [], path)
        i = next(i for i, e in enumerate(done.log) if e["kind"] == "convention_applied")
        for label, change in (("extra_field", lambda e: e.update(hand=1)), ("wrong_player", lambda e: e.update(player=1)),
                              ("zero_available", lambda e: e.update(available=0))):
            with self.subTest(label):
                bad = done.clone()
                record = dict(bad.log[i])
                change(record)
                bad.log = bad.log[:i] + (record,) + bad.log[i + 1:] if isinstance(bad.log, tuple) else bad.log[:i] + [record] + bad.log[i + 1:]
                self.assertNotEqual(s2a_problems(bad), [])
        moved = done.clone()
        log = list(moved.log)
        log.insert(i + 1, log.pop(i))  # 自分へのダメージのあとに置く
        moved.log = type(moved.log)(log) if isinstance(moved.log, tuple) else log
        self.assertNotEqual(s2a_problems(moved), [])


class JudgeTest(unittest.TestCase):
    """本物の runner（構築盤面のスナップショットから）と逐次バッチの判定の入口。受理した 0 枚の答えは expected（H4 の既知の停止に数えない）。厳密側は規則 10 の known_stop。"""

    def run_zero(self, path, key, negative=None):
        from tools.verification_ai import fixtures_u_r3a as F
        from tools.verification_ai import runner as V
        from tools.verification_ai.policies import UniformPolicy
        from tests.test_verification_ai_lost_target_p1 import RecordedFixtureRunner

        class ZeroOnce(UniformPolicy):
            name, version = "scripted-test", 0

            def __init__(self):
                super().__init__("scripted-test")
                self.zero = True

            def choose(self, purpose, items, context):
                if purpose == "candidate":
                    kinds = [c.get("kind") for c in items]
                    for kind in ("answer_decision", "use_attack"):
                        if kind in kinds:
                            return kinds.index(kind), "scripted"
                    return 0, "scripted"
                if purpose == "option":
                    stage = context["stage"]
                    by_id = {o["id"]: o for o in stage.get("options", [])}
                    want = "エナジーへんかん" if stage.get("decision_kind") == "select_attack" or path == "gastly" else "ゆびをふる"
                    for i, oid in enumerate(items):
                        o = by_id.get(oid, {})
                        if (o.get("name_ja") or (o.get("attack") or {}).get("name_ja")) == want:
                            return i, "scripted"
                    return 0, "scripted"
                if purpose == "count":
                    zero, self.zero = self.zero, False
                    return (0 if zero else 1), "scripted"
                return 0, "scripted"

        state = with_set(gastly_board() if path == "gastly" else metronome_board(path), key)
        text, error = F.snapshot_text(state, f"tr6-{path}-{key[0]}")
        self.assertIsNotNone(text, error)
        steps = 1 if path == "gastly" else 2  # ワザ（・ゆびをふるの選択）
        operations = steps + (1 if key == TR6 else 2)  # TR6: 0 枚の受理まで。厳密側: 0 枚の拒否と 1 枚の受理まで
        config = V.Config(profile="boundary", limits=V.Limits(operations=operations, seconds=60), run_id=f"test-tr6-{key[0]}")
        return RecordedFixtureRunner(config, text, policy_factory=lambda seed, dist: ZeroOnce(), negative=negative).run()

    def test_accepted_zero_is_expected_and_strict_is_rule10_known_stop(self):
        from tools.verification_ai import batch as B
        from tools.verification_ai import judge as J
        from tests.test_verification_ai_batch_judge import NoNegative

        for path in PATHS:
            for key, outcome, verdict in ((TR6, D.ACCEPTED, J.EXPECTED), (C.DEFAULT_SET, D.REJECTED, J.KNOWN_STOP)):
                with self.subTest(path=path, key=key):
                    result = self.run_zero(path, key)
                    entries = [e for e in result["trace"] if e.get("type") == "attempt" and e.get("submit") is not None]
                    zero = [e for e in entries if e["candidate"]["kind"] == "answer_decision" and e["choices"] == [] and
                            any(s.get("decision_kind") == RECOVER_ENERGY for s in e.get("stages") or [])]
                    self.assertEqual(len(zero), 1)
                    entry = zero[0]
                    self.assertEqual(entry["submit"]["outcome"], outcome)
                    judged = B.judge_trace(result)
                    self.assertEqual(judged["undetermined"], [])
                    row = next(r for r in judged["rows"] if r["attempt"] == entry["n"])
                    self.assertEqual(row["verdict"], verdict)
                    if key == TR6:
                        self.assertEqual((row["engine_code"], judged["known_stop"]), (None, []))
                    else:
                        self.assertEqual(row["engine_code"], H4)
                        self.assertIn("evidence:" + J.KNOWN_STOP_EVIDENCE[H4]["condition"], row["reasons"])
                        self.assertEqual(judged["known_stop"], [entry["n"]])
                    single = self.run_zero(path, key, negative=NoNegative())
                    (s_entry,) = [e for e in single["trace"] if e.get("type") == "attempt" and e.get("submit") is not None and e["n"] == entry["n"]]
                    self.assertEqual(s_entry["judge"]["verdict"], verdict)  # 単局の runner の判定（変異の実行の中）も同じ


if __name__ == "__main__":
    unittest.main()

"""v0.186（docs/play-convention-tr3-v0.186.md）: 突風・ポケモンいれかえ・きずぐすりのプレイ用の続行規約（開発用の集合 CS-KYUURA-PLAY-TR3@1）。

利用者の採用（2026-11-15）: 3 つの条件（相手のベンチが空・自分のベンチが空・自分の場にダメージのあるポケモンがいない）では使えない（カードを消費しない）。通常の使用と代用の使用
（錯乱ジム・サイキックコントロール）に同じ条件。明示的に選んだ TR3 の集合だけで有効。プレイ用の取り決めで、史実の裁定の確定ではない（厳密側の停止コードは active のまま）。

確かめの種類を分ける:

- 構築盤面（tests.helpers.build_test_state。規約集合だけを TR3 に置きかえた写し ``as_tr3``。コインはテストの乱数の仕込み）: 登録・照会・3 条件の厳密側と TR3 側・状態の不変・
  対象がいる場合・代用の使用・対象外の未裁定（AL2・MG1・UNDAMAGED_TARGET）・候補・check・submit・方策・秘密への非依存・記録
- new_game: TR3 を明示して対戦を作れること・既定の集合が変わらないこと（3 条件の場面への到達は確かめていない。到達の実績とは区別する）
"""

from __future__ import annotations

import copy
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import conventions as C
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import PlayTrainer, ResolveDecision
from kyuura_engine.engine import apply_command, new_game
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from tests import helpers as H
from tests.test_active_leave_locks_v0_93 import locked
from tools.verification_ai.actions import option_allowed

HD, TL = CoinSide.HEADS, CoinSide.TAILS
LATEST = max(FORMAT_VERSIONS)
TR3 = ("CS-KYUURA-PLAY-TR3", 1)
GUST_ID, SWITCH_ID, POTION_ID = "PC-GUST-WITHOUT-OPPONENT-BENCH", "PC-SWITCH-WITHOUT-BENCH", "PC-POTION-WITHOUT-DAMAGE"
GW5, SWB, PWD = "UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH", "UNRESOLVED_SWITCH_WITHOUT_BENCH", "UNRESOLVED_POTION_WITHOUT_DAMAGE"
AL2, MG1, UNDAMAGED = "UNRESOLVED_LEAVE_LOCK_NO_EFFECT", "UNRESOLVED_MIND_GAMES_CHAOS_GYM_ORDER", "UNRESOLVED_POTION_UNDAMAGED_TARGET"
# 条件 → (カード, 厳密側の停止コード, TR3 の拒否のコード, 規約 ID)
CASES = {"gust": (H.GUST, GW5, "NO_OPPONENT_BENCH", GUST_ID), "switch": (H.SWITCH, SWB, "NO_BENCH", SWITCH_ID), "potion": (H.POTION, PWD, "NO_DAMAGE_COUNTERS", POTION_ID)}
OTHER_SETS = (C.DEFAULT_SET, (C.S2A_SET_ID, 1), (C.PO_SET_ID, 1))  # 旧状態用の集合（LEGACY）は新しい状態に置けないので、照合値の不変だけを確かめる
# 既存の集合の照合値（v0.142〜v0.145 の固定の値。この版で変えない）
EXISTING_SET_DIGESTS = {
    ("CS-KYUURA-CURRENT", 1): "sha256:9a9b95c689d86fa01a5b710984560efda3c08f4dbf1d7c6218094ac8666f3cee",
    ("CS-KYUURA-LEGACY-UNRECORDED", 1): "sha256:abf39e6d87755507a9169537608596246f4ed9a9bf0c2e8794ffa44a97742407",
    ("CS-KYUURA-PLAY-S2A", 1): "sha256:b317a3f050206577bff35ac05c87fdb4224ee28c6c0222e4e7f8460b5e9410c4",
    ("CS-KYUURA-PLAY-PO", 1): "sha256:06d512194feee1857319f0c765ab2162d5259e4519895ed057d176d15fc43528",
}


def with_set(state, key):
    """盤面を直接作った状態（今の挙動の集合）を、同じ盤面・同じ乱数の別の集合の状態にする（constructed。規約集合だけを置きかえる）。"""
    new = state.clone()
    new.conventions = C.registered_identity(key)
    return new


def as_tr3(state):
    return with_set(state, TR3)


def snap(state):
    """拒否で変わらないことを確かめる値: 書き出しの全体（手札・場・トラッシュ・決定・使用中のカード）・乱数・ログ・決定の通し番号。"""
    return repr(state_to_dict(state, format_version=LATEST)), rng_fingerprint(state.rng), tuple(map(repr, state.log)), state.next_decision_id


def uid(state, player, card_id, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def board(kind, *, met=True, hand=()):
    """自分（プレイヤー 0）の番の MAIN。手札の先頭が対象のカード。``met`` なら未裁定の条件が成り立つ盤面、偽なら対象がいる盤面（隣の場面）。"""
    card = CASES[kind][0]
    me = {"active": {"card": H.GROWLITHE, "energy": [H.FIRE]}, "bench": [H.PONYTA], "hand": [card, *hand], "deck": [H.FIRE] * 8}
    them = {"active": H.STARYU, "bench": [H.SEEL], "hand": [H.WATER], "deck": [H.WATER] * 8}
    if kind == "gust" and met:
        them["bench"] = []
    if kind == "switch" and met:
        me["bench"] = []
    if kind == "potion" and not met:
        me["active"]["damage"] = 20
    return H.build_test_state([me, them], turn_number=5)


def play(state, card_id, player=0):
    return apply_command(state, PlayTrainer(player, uid(state, player, card_id)))


class RegistrationTest(unittest.TestCase):
    def test_tr3_set_members_and_digests(self):
        spec = C.SETS[TR3]
        self.assertEqual((spec.usage, spec.completeness), (C.USAGE_DEVELOPMENT, C.COMPLETENESS_HALTS))  # 完成したプレイ用の集合ではない
        po = C.SETS[(C.PO_SET_ID, 1)]
        new = ((GUST_ID, 1), (SWITCH_ID, 1), (POTION_ID, 1))
        self.assertEqual(spec.members, po.members + new)  # PO@1 の 20 規約と、新しい 3 規約
        self.assertEqual(len(po.members), 20)
        self.assertEqual(C.validate(spec), [])
        identity = C.identity_of(spec)
        self.assertEqual(identity.digest, C.PINNED_SET_DIGESTS[TR3])
        for member, version, digest in identity.members:
            self.assertEqual(digest, C.PINNED_CONVENTION_DIGESTS[(member, version)], member)
            self.assertEqual(digest, C.convention_digest(C.CONVENTIONS[(member, version)]), member)
        for key, (_, code, illegal, cid) in zip(new, CASES.values()):
            convention = C.CONVENTIONS[key]
            self.assertEqual((convention.layer, convention.approval, convention.scenes), (C.LAYER_CONTINUATION, C.APPROVAL_USER_AGREED, (code,)))
            self.assertEqual(convention.content["rejection_code"], illegal)
            self.assertIn("2026-11-15", convention.content["adoption"])
            self.assertIn(key, C.DEFAULT_REGISTRY.implemented_continuations)
        known = {s["id"] for s in C.scene_index()["scenes"]}
        self.assertLessEqual({GW5, SWB, PWD}, known)

    def test_existing_sets_and_default_are_unchanged(self):
        for key, digest in EXISTING_SET_DIGESTS.items():
            with self.subTest(key=key):
                self.assertEqual(C.PINNED_SET_DIGESTS[key], digest)
                if key[0] != C.LEGACY_SET_ID:  # 旧状態用の集合は identity_of で作れない（新しい対戦に使わない）。固定の値と中身で確かめる
                    self.assertEqual(C.identity_of(C.SETS[key]).digest, digest)
                self.assertFalse({GUST_ID, SWITCH_ID, POTION_ID} & {m for m, _ in C.SETS[key].members})
        self.assertEqual(C.SETS[(C.LEGACY_SET_ID, 1)].members, C.SETS[C.DEFAULT_SET].members)
        self.assertEqual(C.DEFAULT_SET, (C.CURRENT_SET_ID, 1))
        self.assertEqual(C.default_identity().key, C.DEFAULT_SET)

    def test_lookup_only_in_tr3(self):
        state = board("gust")
        for code in (GW5, SWB, PWD):
            for key in OTHER_SETS:
                with self.subTest(code=code, key=key):
                    self.assertIsNone(C.continuation_for(with_set(state, key), code))
            found = C.continuation_for(as_tr3(state), code)
            self.assertEqual(found.scene, code)
            with self.assertRaises(RuntimeError):  # 続ける分岐を通らずに止めようとしたらエンジンの不具合
                C.stop_without_continuation(as_tr3(state), code)
        for code in (AL2, MG1, UNDAMAGED, "UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH", "UNRESOLVED_ROCKET_GRUNT_WITHOUT_BENCH"):
            self.assertIsNone(C.continuation_for(as_tr3(state), code), code)

    def test_new_game_only_when_selected(self):
        deck = H.expand_decklist({H.DRATINI: 4, H.LIGHTNING: 56})
        self.assertEqual(new_game(deck, deck, 1).conventions.key, C.DEFAULT_SET)
        self.assertEqual(new_game(deck, deck, 1, conventions="CS-KYUURA-PLAY-TR3@1").conventions, C.registered_identity(TR3))


class StrictTest(unittest.TestCase):
    def test_other_sets_keep_the_unresolved_stop(self):
        for kind, (card, code, _, _) in CASES.items():
            for key in OTHER_SETS:
                with self.subTest(kind=kind, key=key):
                    state = with_set(board(kind), key)
                    before = snap(state)
                    with self.assertRaises(UnsupportedError) as caught:
                        play(state, card)
                    self.assertEqual(caught.exception.code, code)
                    self.assertEqual(snap(state), before)


class Tr3Test(unittest.TestCase):
    def test_rejected_by_convention_without_change(self):
        for kind, (card, _, illegal, cid) in CASES.items():
            with self.subTest(kind=kind):
                state = as_tr3(board(kind))
                before = snap(state)
                for _ in range(2):
                    with self.assertRaises(IllegalActionError) as caught:
                        play(state, card)
                    self.assertEqual(caught.exception.code, illegal)
                    self.assertIn(f"{cid}@1", caught.exception.message)
                    self.assertEqual(caught.exception.convention, f"{cid}@1")
                    self.assertEqual(snap(state), before)
                self.assertIn(uid(state, 0, card), state.players[0].hand)
                self.assertIsNone(state.trainer_in_use)
                game = A.HostedGame(state.clone())
                result = game.submit(PlayTrainer(0, uid(state, 0, card)), submitter=0)
                self.assertEqual(result.outcome, D.REJECTED)
                self.assertEqual(snap(game.state), before)

    def test_targets_present_are_unchanged(self):
        for kind, (card, _, _, _) in CASES.items():
            with self.subTest(kind=kind):
                strict = board(kind, met=False)
                after_strict, after_tr3 = play(strict, card), play(as_tr3(strict), card)
                self.assertEqual(rng_fingerprint(after_strict.rng), rng_fingerprint(after_tr3.rng))
                self.assertEqual(after_strict.log, after_tr3.log)
                self.assertEqual((after_strict.decision.kind, after_strict.decision.options), (after_tr3.decision.kind, after_tr3.decision.options))
                answered = [apply_command(s, ResolveDecision(0, s.decision.id, (s.decision.options[0],))) for s in (after_strict, after_tr3)]
                self.assertEqual(answered[0].log, answered[1].log)

    def test_other_unresolved_are_not_hidden(self):
        # AL2: 相手の控えがいても、相手の対戦ポケモンがはなれられない（突風）。自分の控えがいても、自分の対戦ポケモンがはなれられない（ポケモンいれかえ）
        for kind, owner in (("gust", 1), ("switch", 0)):
            with self.subTest(kind=kind):
                state = locked(board(kind, met=False), owner)
                for s in (state, as_tr3(state)):
                    with self.assertRaises(UnsupportedError) as caught:
                        play(s, CASES[kind][0])
                    self.assertEqual(caught.exception.code, AL2)
        # きずぐすりでダメージのないポケモンを選ぶ（受理のあとの未裁定）
        state = as_tr3(board("potion", met=False))
        state = play(state, H.POTION)
        bench = state.players[0].bench[0].pokemon_id
        self.assertIn(bench, state.decision.options)
        with self.assertRaises(UnsupportedError) as caught:
            apply_command(state, ResolveDecision(0, state.decision.id, (bench,)))
        self.assertEqual(caught.exception.code, UNDAMAGED)

    def test_mind_games_chaos_gym_is_not_hidden(self):
        from tests import test_slowking_mind_games_v0_132 as MG
        for damage, code, error in ((20, MG1, UnsupportedError), (0, "NO_DAMAGE_COUNTERS", IllegalActionError)):
            with self.subTest(damage=damage):
                state = H.build_test_state([{"active": {"card": MG.HITMONCHAN, "energy": [MG.FIGHTING], "damage": damage}, "hand": [H.CHAOS_GYM, H.POTION],
                                             "deck": [MG.FIGHTING] * 8},
                                            {"active": MG.slowking(), "deck": [MG.FIGHTING] * 8}], turn_number=7, current_player=0)
                state = MG.respond(MG.play(as_tr3(state), H.CHAOS_GYM), True, TL)
                self.assertEqual(state.cards[state.stadium.card].card_id, H.CHAOS_GYM)
                with self.assertRaises(error) as caught:
                    play(state, H.POTION)
                self.assertEqual(caught.exception.code, code)  # ダメージがあれば MG1 のまま。なければ TR3 の条件が先（厳密側も条件が先）


class SubstituteTest(unittest.TestCase):
    """通常の使用と代用の使用に同じ条件（check_playable）。代用の使用では、使う人から見た条件。"""

    def chaos(self, kind, key):
        """プレイヤー 0 が錯乱ジムを出し、手札の対象のカードを使って「うら」。かわりに使う人（プレイヤー 1）から見て条件が成り立つ盤面。"""
        card = CASES[kind][0]
        me = {"active": {"card": H.CHARMANDER, "energy": [H.FIRE], "damage": 20}, "bench": [H.RATTATA] if kind != "gust" else [],
              "hand": [H.CHAOS_GYM, card], "deck": [H.FIRE] * 8}
        them = {"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": [] if kind == "switch" else [H.RATTATA], "hand": [H.WATER], "deck": [H.FIRE] * 8}
        state = with_set(H.build_test_state([me, them], turn_number=5), key)
        state = play(state, H.CHAOS_GYM)
        return apply_command(H.with_coin_results(state, TL), PlayTrainer(0, uid(state, 0, card)))

    def test_chaos_gym_borrow(self):
        for kind, (card, code, illegal, cid) in CASES.items():
            with self.subTest(kind=kind):
                strict = self.chaos(kind, C.DEFAULT_SET)
                d = strict.decision
                self.assertEqual((d.player, d.context_value("unresolved_choices"), d.context_value("unresolved_code")), (1, (1,), code))
                with self.assertRaises(UnsupportedError):
                    apply_command(strict, ResolveDecision(1, d.id, (1,)))
                tr3 = self.chaos(kind, TR3)
                d = tr3.decision
                self.assertEqual((d.player, d.context_value("unresolved_choices")), (1, None))  # 選ぶと止める選択ではない（使うための条件を満たせない扱い）
                before = snap(tr3)
                with self.assertRaises(IllegalActionError) as caught:
                    apply_command(tr3, ResolveDecision(1, d.id, (1,)))
                self.assertEqual((caught.exception.code, caught.exception.convention), (illegal, f"{cid}@1"))
                self.assertEqual(snap(tr3), before)
                declined = apply_command(tr3, ResolveDecision(1, d.id, ()))
                self.assertIn(tr3.trainer_in_use.card, declined.players[0].discard)  # 錯乱ジムの「うら」の処理のトラッシュ（規約による消費ではない）

    def test_psychic_control(self):
        for kind, (card, code, illegal, cid) in CASES.items():
            with self.subTest(kind=kind):
                me = {"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": [] if kind == "switch" else [H.RATTATA],
                      "hand": [H.SABRINAS_PSYCHIC_CONTROL, H.WATER], "deck": [H.FIRE] * 8}
                them = {"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": [] if kind == "gust" else [H.RATTATA], "hand": [H.WATER],
                        "deck": [H.FIRE] * 8, "discard": [card]}
                base = H.build_test_state([me, them], turn_number=5)
                for key in (C.DEFAULT_SET, TR3):
                    state = apply_command(H.with_coin_results(with_set(base, key), HD), PlayTrainer(0, uid(base, 0, H.SABRINAS_PSYCHIC_CONTROL)))
                    chosen = uid(state, 1, card, "discard")
                    self.assertIn(chosen, state.decision.options)
                    before = snap(state)
                    with self.assertRaises(UnsupportedError if key != TR3 else IllegalActionError) as caught:
                        apply_command(state, ResolveDecision(0, state.decision.id, (chosen,)))
                    self.assertEqual(caught.exception.code, code if key != TR3 else illegal)
                    self.assertEqual(snap(state), before)


class CandidateTest(unittest.TestCase):
    def response(self, state, actor=0):
        host = L.ActionHost(A.HostedGame(state))
        session = host.session(actor)
        r = session.candidates()
        found = [c for c in r["candidates"] if c["kind"] == L.KIND_PLAY_TRAINER]
        return host, session, r, (found[0] if found else None)

    def trainer_stage(self, session, r, cand):
        return session.inputs(r["game"], r["revision"], cand["id"])["stages"][0]

    def mixed(self):
        """手札: 突風（相手のベンチが空）・きずぐすり（ダメージなし）・ポケモンいれかえ（自分の控えあり。実行できる）。"""
        return H.build_test_state([{"active": {"card": H.GROWLITHE, "energy": [H.FIRE]}, "bench": [H.PONYTA], "hand": [H.GUST, H.POTION, H.SWITCH],
                                    "deck": [H.FIRE] * 8},
                                   {"active": H.STARYU, "hand": [H.WATER], "deck": [H.WATER] * 8}], turn_number=5)

    def test_mixed_candidate(self):
        strict = self.mixed()
        _, s_session, s_r, s_cand = self.response(strict)
        s_options = {o["card"]: o for o in self.trainer_stage(s_session, s_r, s_cand)["options"]}
        host, session, r, cand = self.response(as_tr3(strict))
        options = {o["card"]: o for o in self.trainer_stage(session, r, cand)["options"]}
        gust, potion, switch = (uid(strict, 0, c) for c in (H.GUST, H.POTION, H.SWITCH))
        self.assertEqual(set(options), {gust, potion, switch})  # 規約で除外したカードも選べるものに残す
        for card, cid in ((gust, GUST_ID), (potion, POTION_ID)):
            self.assertEqual(s_options[card]["processability"], L.RULING_UNRESOLVED)  # 厳密側は未裁定のまま
            self.assertEqual(options[card]["eligible"], False)
            self.assertEqual(options[card]["convention"], f"{cid}@1")
            self.assertNotIn("processability", options[card])  # 規約による除外は処理可能性の区分ではない（v0.143 の配置と同じ）
            self.assertFalse(option_allowed(options[card], frozenset(L.EXECUTABLE)))  # 方策は選ばない
        self.assertEqual(options[switch], s_options[switch])  # 実行できる別のカードは巻き込まない
        self.assertTrue(options[switch]["eligible"])
        self.assertEqual((cand["processability"], cand["reasons"]), (s_options[switch]["processability"], s_options[switch].get("reasons", [])))
        state = host.game.state
        before = snap(state)
        by_card = {o["card"]: o["id"] for o in self.trainer_stage(session, r, cand)["options"]}
        for card in (gust, potion):
            self.assertEqual(session.check(r["game"], r["revision"], cand["id"], [by_card[card]])["refusal"]["code"], L.CANDIDATE_NOT_EXECUTABLE)
            sent = session.submit(r["game"], r["revision"], cand["id"], [by_card[card]])
            self.assertEqual(sent.refusal.code, L.CANDIDATE_NOT_EXECUTABLE)
            self.assertEqual(snap(host.game.state), before)
        self.assertTrue(session.check(r["game"], r["revision"], cand["id"], [by_card[switch]])["valid"])

    def test_all_excluded_candidate(self):
        state = as_tr3(H.build_test_state([{"active": {"card": H.GROWLITHE, "energy": [H.FIRE]}, "hand": [H.GUST, H.POTION], "deck": [H.FIRE] * 8},
                                           {"active": H.STARYU, "hand": [H.WATER], "deck": [H.WATER] * 8}], turn_number=5))
        _, session, r, cand = self.response(state)
        self.assertEqual((cand["processability"], cand["reasons"]), (L.NOT_IMPLEMENTED, ["no_eligible_card"]))  # v0.143 の配置の前例と同じ
        stage = self.trainer_stage(session, r, cand)
        self.assertTrue(all(o["eligible"] is False and "convention" in o for o in stage["options"]))
        self.assertEqual(session.check(r["game"], r["revision"], cand["id"], [stage["options"][0]["id"]])["refusal"]["code"], L.CANDIDATE_NOT_EXECUTABLE)

    def test_other_reasons_are_not_converted(self):
        # AL2（相手の控えがいる・はなれられない）は TR3 でも未裁定のまま（規約による除外にしない）
        state = as_tr3(locked(board("gust", met=False), 1))
        _, session, r, cand = self.response(state)
        (option,) = [o for o in self.trainer_stage(session, r, cand)["options"] if o["card"] == uid(state, 0, H.GUST)]
        self.assertEqual((option["eligible"], option["processability"]), (False, L.RULING_UNRESOLVED))
        self.assertNotIn("convention", option)

    def test_secret_independence(self):
        """相手の手札・山札の中身だけが違う双子で、候補・入力が同じ（判定は公開の値だけ）。"""
        outs = []
        for hand, deck in (([H.WATER], [H.WATER] * 8), ([H.GUST, H.SEEL], [H.SEEL] * 8)):
            state = as_tr3(H.build_test_state([{"active": {"card": H.GROWLITHE, "energy": [H.FIRE]}, "hand": [H.GUST, H.POTION], "deck": [H.FIRE] * 8},
                                               {"active": H.STARYU, "hand": hand, "deck": deck}], turn_number=5))
            _, session, r, cand = self.response(state)
            stage = self.trainer_stage(session, r, cand)
            data = copy.deepcopy(r)
            for k in ("game", "revision"):
                data.pop(k, None)
            outs.append((data, stage))
        self.assertEqual(outs[0], outs[1])


class RecordTest(unittest.TestCase):
    def test_selection_and_basis_are_recorded(self):
        state = as_tr3(board("gust"))
        record = C.state_conventions(state)[0].record()
        self.assertEqual((record["id"], record["version"]), TR3)
        self.assertIn({"id": GUST_ID, "version": 1, "digest": C.PINNED_CONVENTION_DIGESTS[(GUST_ID, 1)]}, record["members"])
        self.assertEqual(state_to_dict(state, format_version=LATEST)["convention_set"]["id"], TR3[0])
        with self.assertRaises(IllegalActionError) as caught:
            play(state, H.GUST)
        self.assertNotIn("convention_applied", [e["kind"] for e in state.log])  # 受理の前の拒否はログを書かない
        self.assertIn(f"{GUST_ID}@1", caught.exception.message)


if __name__ == "__main__":
    unittest.main()

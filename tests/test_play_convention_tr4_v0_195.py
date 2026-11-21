"""v0.195（docs/play-convention-tr4-v0.195.md）: エネルギー回収の回収の決定で 0 枚と答えたときのプレイ用の続行規約 PC-ENERGY-RETRIEVAL-ZERO@1（開発用の集合 CS-KYUURA-PLAY-TR4@1）。

利用者の採用（2026-11-21。設計 docs/er9-energy-retrieval-zero-design.md の案 B）: 手札から通常に使ったエネルギー回収（再録の版をふくむ）の回収の答えが空なら、受理して使い終える
（費用はもどさない・手札に加えない・このカードは持ち主のトラッシュ・番にもどる）。明示的に選んだ TR4 の集合だけで有効。プレイ用の取り決めで、史実の裁定の確定ではない
（ER9 の停止コードは厳密側・既存の集合・初回の範囲の外の経路で active のまま）。

確かめの種類を分ける（設計 5 章の V1〜V12）:

- 構築盤面（tests.helpers.build_test_state。規約集合だけを置きかえた写し ``with_set``。コインはテストの乱数の仕込み）: 登録・照会・厳密側と TR4 側の差・受理のあとの状態と公開ログ・
  1 枚・2 枚の対照・不正な入力からの答え直し・合法手 API・ER10・ポケモンタワー・ワザの H4・超エネルギー回収・初回の範囲の外の経路・再録の版・ログの監査
- 本物の runner（スナップショットから復元した構築盤面）と逐次バッチの判定の入口（``batch.judge_trace``）: 受理した 0 枚の答えの判定と、厳密側の規則 6
- new_game: TR4 を明示して対戦を作れること・既定の集合が変わらないこと（回収の決定への到達は確かめていない。到達の実績とは区別する）
"""

from __future__ import annotations

import copy
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import conventions as C
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine import effects as E
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import AttachEnergy, PlayTrainer, ResolveDecision, UseAttack
from kyuura_engine.decisions import DISCARD_FROM_HAND, RETRIEVE_ENERGY
from kyuura_engine.engine import apply_command, check_invariants, new_game
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import visible_log
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from tests import helpers as H
from tests.log_audit import s2a_problems

HD, TL = CoinSide.HEADS, CoinSide.TAILS
LATEST = max(FORMAT_VERSIONS)
TR4 = ("CS-KYUURA-PLAY-TR4", 1)
TR3 = ("CS-KYUURA-PLAY-TR3", 1)
ZERO_ID = "PC-ENERGY-RETRIEVAL-ZERO"
ER9 = "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE"
ER10 = "UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET"
SR2 = "UNRESOLVED_SUPER_ENERGY_RETRIEVAL_ZERO_CHOICE"
H4 = "UNRESOLVED_RECOVER_ZERO_ENERGY"
STRICT_SETS = (C.DEFAULT_SET, TR3)  # 厳密側（今の挙動の集合）と、この規約を持たない既存の開発用の集合
OTHER_SETS = (C.DEFAULT_SET, (C.S2A_SET_ID, 1), (C.PO_SET_ID, 1), TR3)
REPRINTS = ("GD1-014", "GD4-014", "GD6-014", "QSG-047")
# 既存の集合の照合値（v0.142〜v0.186 の固定の値。この版で変えない）
EXISTING_SET_DIGESTS = {
    ("CS-KYUURA-CURRENT", 1): "sha256:9a9b95c689d86fa01a5b710984560efda3c08f4dbf1d7c6218094ac8666f3cee",
    ("CS-KYUURA-LEGACY-UNRECORDED", 1): "sha256:abf39e6d87755507a9169537608596246f4ed9a9bf0c2e8794ffa44a97742407",
    ("CS-KYUURA-PLAY-S2A", 1): "sha256:b317a3f050206577bff35ac05c87fdb4224ee28c6c0222e4e7f8460b5e9410c4",
    ("CS-KYUURA-PLAY-PO", 1): "sha256:06d512194feee1857319f0c765ab2162d5259e4519895ed057d176d15fc43528",
    ("CS-KYUURA-PLAY-TR3", 1): "sha256:a7b800cff2a8614d7b181cc3a8a39f68ec4e17be9ceab0a04e75a48c4358ffb4",
}


def with_set(state, key):
    """盤面を直接作った状態（今の挙動の集合）を、同じ盤面・同じ乱数の別の集合の状態にする（constructed。規約集合だけを置きかえる）。"""
    new = state.clone()
    new.conventions = C.registered_identity(key)
    return new


def snap(state):
    """拒否で変わらないことを確かめる値: 書き出しの全体（手札・場・トラッシュ・決定・使用中のカード）・乱数・ログ・決定の通し番号。"""
    return repr(state_to_dict(state, format_version=LATEST)), rng_fingerprint(state.rng), tuple(map(repr, state.log)), state.next_decision_id


def uid(state, player, card_id, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def answer(state, player, choices):
    return apply_command(state, ResolveDecision(player, state.decision.id, tuple(choices)))


def board(card=H.ENERGY_RETRIEVAL, *, hand=(H.FIRE, H.WATER), discard=(H.WATER, H.FIRE, H.GRASS), extra_hand=(), me=None, them=None):
    """自分（プレイヤー 0）の番の MAIN。手札は extra_hand・エネルギー回収・hand の順。トラッシュは discard。"""
    me = me or {"active": {"card": H.GROWLITHE, "energy": [H.FIRE]}, "bench": [H.PONYTA], "hand": [*extra_hand, card, *hand], "deck": [H.FIRE] * 8,
                "discard": list(discard)}
    them = them or {"active": H.STARYU, "bench": [H.SEEL], "hand": [H.WATER, H.GRASS], "deck": [H.WATER] * 8, "discard": [H.WATER, H.GRASS]}
    return H.build_test_state([me, them], turn_number=5)


def at_retrieve(key=C.DEFAULT_SET, card=H.ENERGY_RETRIEVAL, **kw):
    """手札から使い、費用に手札の先頭（炎エネルギー）を選んで、回収の決定まで進める。"""
    state = with_set(board(card, **kw), key)
    state = apply_command(state, PlayTrainer(0, uid(state, 0, card)))
    assert state.decision.kind == DISCARD_FROM_HAND
    state = answer(state, 0, (uid(state, 0, H.FIRE),))
    assert state.decision.kind == RETRIEVE_ENERGY
    return state


def kinds_since(state, n):
    return [e["kind"] for e in state.log[n:]]


class RegistrationTest(unittest.TestCase):
    def test_tr4_set_members_and_digests(self):
        spec = C.SETS[TR4]
        self.assertEqual((spec.usage, spec.completeness), (C.USAGE_DEVELOPMENT, C.COMPLETENESS_HALTS))  # 完成したプレイ用の集合ではない
        tr3 = C.SETS[TR3]
        self.assertEqual(len(tr3.members), 23)
        self.assertEqual(spec.members, tr3.members + ((ZERO_ID, 1),))  # TR3@1 の 23 規約と、新しい 1 規約
        self.assertEqual(C.validate(spec), [])
        identity = C.identity_of(spec)
        self.assertEqual(identity.digest, C.PINNED_SET_DIGESTS[TR4])
        for member, version, digest in identity.members:
            self.assertEqual(digest, C.PINNED_CONVENTION_DIGESTS[(member, version)], member)
            self.assertEqual(digest, C.convention_digest(C.CONVENTIONS[(member, version)]), member)
        convention = C.CONVENTIONS[(ZERO_ID, 1)]
        self.assertEqual((convention.layer, convention.approval, convention.scenes), (C.LAYER_CONTINUATION, C.APPROVAL_USER_AGREED, (ER9,)))
        self.assertIn("2026-11-21", convention.content["adoption"])
        self.assertIn((ZERO_ID, 1), C.DEFAULT_REGISTRY.implemented_continuations)
        self.assertIn(ER9, {s["id"] for s in C.scene_index()["scenes"]})

    def test_existing_sets_and_default_are_unchanged(self):
        for key, digest in EXISTING_SET_DIGESTS.items():
            with self.subTest(key=key):
                self.assertEqual(C.PINNED_SET_DIGESTS[key], digest)
                if key[0] != C.LEGACY_SET_ID:
                    self.assertEqual(C.identity_of(C.SETS[key]).digest, digest)
                self.assertNotIn(ZERO_ID, {m for m, _ in C.SETS[key].members})
        self.assertEqual(C.DEFAULT_SET, (C.CURRENT_SET_ID, 1))
        self.assertEqual(C.default_identity().key, C.DEFAULT_SET)

    def test_lookup_only_in_tr4(self):
        state = board()
        for key in OTHER_SETS:
            with self.subTest(key=key):
                self.assertIsNone(C.continuation_for(with_set(state, key), ER9))
        found = C.continuation_for(with_set(state, TR4), ER9)
        self.assertEqual((found.scene, found.convention), (ER9, (ZERO_ID, 1)))
        for code in (ER10, SR2, H4, "UNRESOLVED_TRAINER_UP_TO_ZERO_CHOICE", "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE"):
            self.assertIsNone(C.continuation_for(with_set(state, TR4), code), code)

    def test_new_game_only_when_selected(self):
        deck = H.expand_decklist({H.DRATINI: 4, H.LIGHTNING: 56})
        self.assertEqual(new_game(deck, deck, 1).conventions.key, C.DEFAULT_SET)
        self.assertEqual(new_game(deck, deck, 1, conventions="CS-KYUURA-PLAY-TR4@1").conventions, C.registered_identity(TR4))


class StrictTest(unittest.TestCase):
    """V1: 厳密側（CURRENT@1）と TR3@1 は今と同じ ER9（決定は待ったまま・状態・乱数・ログは変わらない・費用のトラッシュは残る）。"""

    def test_strict_sets_keep_er9(self):
        for key in STRICT_SETS:
            with self.subTest(key=key):
                state = at_retrieve(key)
                cost = state.decision.context_value("discarded")
                before = snap(state)
                with self.assertRaises(UnsupportedError) as caught:
                    answer(state, 0, ())
                self.assertEqual(caught.exception.code, ER9)
                self.assertEqual(D.default_catalog().get(ER9).category, D.RULING_UNRESOLVED)
                self.assertEqual(snap(state), before)
                self.assertEqual(state.decision.kind, RETRIEVE_ENERGY)
                self.assertTrue(set(cost) <= set(state.players[0].discard))


class ZeroAcceptedTest(unittest.TestCase):
    """V2・V3: TR4 では 0 枚を受理して使い終える。"""

    def test_zero_is_accepted_and_the_use_ends(self):
        state = at_retrieve(TR4)
        d = state.decision
        card = state.trainer_in_use.card
        cost = d.context_value("discarded")
        hand, discard, n = list(state.players[0].hand), list(state.players[0].discard), len(state.log)
        done = answer(state, 0, ())
        self.assertEqual(kinds_since(done, n), ["convention_applied", "discard_trainer"])  # retrieve_energy は書かない
        applied, trashed = done.log[n], done.log[n + 1]
        self.assertEqual(applied, {"kind": "convention_applied", "turn": 5, "convention": ZERO_ID, "version": 1, "scene": ER9, "code": ER9, "player": 0,
                                   "available": len(d.options)})
        self.assertEqual((trashed["player"], trashed["card"]), (0, card))
        self.assertIsNone(done.decision)
        self.assertIsNone(done.trainer_in_use)
        self.assertEqual((done.phase.value, done.current_player, done.turn_number), ("main", 0, 5))
        self.assertEqual(done.players[0].hand, hand)  # 回収の答えでは手札は変わらない
        self.assertEqual(done.players[0].discard, discard + [card])  # このカードの分だけ増える
        self.assertTrue(set(cost) <= set(done.players[0].discard))  # 費用はもどさない
        self.assertTrue(set(d.options) <= set(done.players[0].discard))  # 選べたエネルギーはトラッシュのまま
        self.assertEqual(rng_fingerprint(done.rng), rng_fingerprint(state.rng))
        self.assertEqual(check_invariants(done), [])
        self.assertEqual(s2a_problems(done), [])
        # 同じ番の操作ができる（その番にまだつけていないエネルギーをつける）
        water = uid(done, 0, H.WATER)
        attached = apply_command(done, AttachEnergy(0, water, done.players[0].active.card))
        self.assertIn(water, attached.players[0].active.energy)

    def test_strict_and_tr4_differ_only_in_the_zero_answer(self):
        """同じ構築盤面で、回収の決定までは同じ（ログ・乱数・決定）。差は 0 枚の答えの submit だけ。"""
        strict, tr4 = at_retrieve(C.DEFAULT_SET), at_retrieve(TR4)
        self.assertEqual(strict.log, tr4.log)
        self.assertEqual(rng_fingerprint(strict.rng), rng_fingerprint(tr4.rng))
        self.assertEqual((strict.decision.kind, strict.decision.options, strict.decision.min_choices, strict.decision.max_choices),
                         (tr4.decision.kind, tr4.decision.options, tr4.decision.min_choices, tr4.decision.max_choices))
        with self.assertRaises(UnsupportedError):
            answer(strict, 0, ())
        self.assertIsNone(answer(tr4, 0, ()).decision)

    def test_one_or_two_cards_are_unchanged(self):
        """V4: 1 枚・2 枚の答えは両方の集合で同じ処理（同じ出来事・手札・トラッシュ）。規約の記録はない。"""
        for count in (1, 2):
            with self.subTest(count=count):
                outs = []
                for key in (C.DEFAULT_SET, TR4):
                    state = at_retrieve(key)
                    n = len(state.log)
                    done = answer(state, 0, state.decision.options[:count])
                    self.assertEqual(kinds_since(done, n), ["retrieve_energy", "discard_trainer"])
                    self.assertEqual(len(done.log[n]["cards"]), count)
                    self.assertNotIn("convention_applied", kinds_since(done, 0))
                    self.assertEqual(check_invariants(done), [])
                    outs.append((done.log, done.players[0].hand, done.players[0].discard, rng_fingerprint(done.rng)))
                self.assertEqual(outs[0], outs[1])

    def test_invalid_answers_then_zero(self):
        """V5: 不正な答え（上限を超える数・重複・費用にしたカード・選べないもの・相手の答え）は今と同じ拒否。決定は待ったまま。そのあと 0 枚が受理される。"""
        state = at_retrieve(TR4)
        d = state.decision
        discarded = d.context_value("discarded")[0]
        wrong = [(0, tuple(d.options[:3]), "INVALID_CHOICE_COUNT"), (0, (d.options[0], d.options[0]), "DUPLICATE_CHOICE"),
                 (0, (discarded,), "INVALID_CHOICE"), (0, (state.players[0].hand[0],), "INVALID_CHOICE"),
                 (0, (state.players[1].discard[0],), "INVALID_CHOICE"), (1, (), "NOT_YOUR_DECISION")]
        before = snap(state)
        for player, choices, code in wrong:
            with self.subTest(choices=choices, player=player):
                with self.assertRaises(IllegalActionError) as caught:
                    answer(state, player, choices)
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(snap(state), before)
        self.assertNotIn(discarded, d.options)  # 費用にしたカードは選べないまま
        self.assertLessEqual(d.max_choices, 2)
        self.assertEqual(answer(state, 0, ()).log[-2]["kind"], "convention_applied")
        strict = at_retrieve(C.DEFAULT_SET)
        with self.assertRaises(IllegalActionError):
            answer(strict, 0, tuple(strict.decision.options[:3]))
        with self.assertRaises(UnsupportedError) as caught:
            answer(strict, 0, ())
        self.assertEqual(caught.exception.code, ER9)

    def test_reprints_behave_the_same(self):
        """V10: 再録の版（同じ登録の型）も PMCG1-076 と同じ（カードの uid・ID のほかは同じ出来事・同じ手札とトラッシュ）。"""
        def shape(card):
            state = at_retrieve(TR4, card)
            done = answer(state, 0, ())
            log = [{k: v for k, v in e.items() if k not in ("card", "trainer")} for e in done.log]
            return log, len(done.players[0].hand), len(done.players[0].discard)
        expected = shape(H.ENERGY_RETRIEVAL)
        for card in REPRINTS:
            with self.subTest(card=card):
                self.assertIsInstance(E.DEFAULT_EFFECTS.trainer_entry(card).effect, E.DiscardFromHandThenRetrieveEnergy)
                self.assertEqual(shape(card), expected)
                with self.assertRaises(UnsupportedError):
                    answer(at_retrieve(C.DEFAULT_SET, card), 0, ())


class ApiTest(unittest.TestCase):
    """V6: 合法手 API の候補・入力・check は両方の集合で同じ。submit だけが違う（TR4 は受理・全員に見える記録、厳密側は拒否・観測の変化なし）。"""

    def flow(self, key):
        host = L.ActionHost(A.HostedGame(at_retrieve(key)))
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
        s_host, s_session, s_r, s_cand, s_inputs, s_check = self.flow(C.DEFAULT_SET)
        t_host, t_session, t_r, t_cand, t_inputs, t_check = self.flow(TR4)
        self.assertEqual(self.strip(s_r), self.strip(t_r))
        self.assertEqual(self.strip(s_inputs), self.strip(t_inputs))
        self.assertEqual(self.strip(s_check), self.strip(t_check))
        self.assertTrue(t_check["valid"])
        self.assertEqual((t_cand["processability"], t_cand["reasons"]), (L.MAY_STOP_LATER, ["continuation_not_evaluated"]))
        stage = t_inputs["stages"][0]
        self.assertEqual((stage["count"], stage["decline"]), ({"min": 0, "max": 2}, True))
        viewers = (0, 1, None)
        s_before = [visible_log(s_host.game.state, v) for v in viewers]
        sent = s_session.submit(s_r["game"], s_r["revision"], s_cand["id"], [])
        self.assertEqual(sent.outcome, D.REJECTED)
        self.assertEqual([visible_log(s_host.game.state, v) for v in viewers], s_before)
        t_before = [len(visible_log(t_host.game.state, v)) for v in viewers]
        sent = t_session.submit(t_r["game"], t_r["revision"], t_cand["id"], [])
        self.assertEqual(sent.outcome, D.ACCEPTED)
        for v, n in zip(viewers, t_before):
            with self.subTest(viewer=v):
                added = visible_log(t_host.game.state, v)[n:]
                self.assertEqual([e["kind"] for e in added], ["convention_applied", "discard_trainer"])
                self.assertEqual(added[0]["available"], len(at_retrieve(TR4).decision.options))


class OtherScenesTest(unittest.TestCase):
    """V7・V8: 使う前の停止（ER10・ポケモンタワー）、ワザの H4、超エネルギー回収の SR2 は、両方の集合で今と同じ。"""

    def test_er10_and_pokemon_tower(self):
        for key in (C.DEFAULT_SET, TR4):
            with self.subTest(key=key):
                state = with_set(board(discard=(H.POTION, H.PONYTA)), key)
                with self.assertRaises(UnsupportedError) as caught:
                    apply_command(state, PlayTrainer(0, uid(state, 0, H.ENERGY_RETRIEVAL)))
                self.assertEqual(caught.exception.code, ER10)
                state = with_set(board(extra_hand=(H.POKEMON_TOWER,)), key)
                state = apply_command(state, PlayTrainer(0, uid(state, 0, H.POKEMON_TOWER)))
                with self.assertRaises(UnsupportedError) as caught:
                    apply_command(state, PlayTrainer(0, uid(state, 0, H.ENERGY_RETRIEVAL)))
                self.assertEqual(caught.exception.code, E.POKEMON_TOWER_TRAINER_CODE)

    def test_recover_zero_energy_attack(self):
        for key in (C.DEFAULT_SET, TR4):
            with self.subTest(key=key):
                state = with_set(H.build_test_state([{"active": {"card": H.GASTLY, "energy": [H.PSYCHIC, H.PSYCHIC]}, "bench": [H.RATTATA],
                                                      "discard": [H.FIRE, H.POTION, H.PSYCHIC, H.WATER]},
                                                     {"active": H.GROWLITHE, "bench": [H.PONYTA], "discard": [H.FIRE]}], turn_number=5), key)
                waiting = apply_command(state, UseAttack(0, 1))
                with self.assertRaises(UnsupportedError) as caught:
                    answer(waiting, 0, ())
                self.assertEqual(caught.exception.code, H4)

    def test_super_energy_retrieval(self):
        for key in (C.DEFAULT_SET, TR4):
            with self.subTest(key=key):
                state = with_set(board(H.SUPER_ENERGY_RETRIEVAL, hand=(H.FIRE, H.PONYTA, H.WATER)), key)
                state = apply_command(state, PlayTrainer(0, uid(state, 0, H.SUPER_ENERGY_RETRIEVAL)))
                state = answer(state, 0, (uid(state, 0, H.FIRE), uid(state, 0, H.PONYTA)))
                self.assertEqual(state.decision.kind, RETRIEVE_ENERGY)
                with self.assertRaises(UnsupportedError) as caught:
                    answer(state, 0, ())
                self.assertEqual(caught.exception.code, SR2)


class PathTest(unittest.TestCase):
    """V9: 回収の決定を再開する時点で、使用の経路を状態（使用中の記録 ``TrainerInUse`` の ``user``・``via``・外側の使用 ``trainer_stack``・この使用の ``play_trainer`` のあとの
    出来事）で区別する。初回の範囲の外の経路（錯乱ジムの「おもて」・「うら」でかわりに使う・サイキックコントロール・［ちえくらべ］を聞いた使用）は、TR4 でも ER9 のまま。
    リムーブ禁止ジムはエネルギー回収に追加の条件を加えないので、場にあっても通常の使用（受理される）。"""

    def chaos(self, key, coin):
        state = with_set(board(extra_hand=(H.CHAOS_GYM,)), key)
        state = apply_command(state, PlayTrainer(0, uid(state, 0, H.CHAOS_GYM)))
        state = apply_command(H.with_coin_results(state, coin), PlayTrainer(0, uid(state, 0, H.ENERGY_RETRIEVAL)))
        if coin is TL:
            state = answer(state, 1, (1,))  # 相手がかわりに使う
        player = 0 if coin is HD else 1
        state = answer(state, player, state.decision.options[:1])
        self.assertEqual(state.decision.kind, RETRIEVE_ENERGY)
        return state, player

    def psychic(self, key):
        them = {"active": H.STARYU, "bench": [H.SEEL], "hand": [H.WATER], "deck": [H.WATER] * 8, "discard": [H.ENERGY_RETRIEVAL, H.WATER]}
        me = {"active": {"card": H.GROWLITHE, "energy": [H.FIRE]}, "bench": [H.PONYTA], "hand": [H.SABRINAS_PSYCHIC_CONTROL, H.FIRE], "deck": [H.FIRE] * 8,
              "discard": [H.WATER, H.FIRE]}
        state = with_set(H.build_test_state([me, them], turn_number=5), key)
        state = apply_command(H.with_coin_results(state, HD), PlayTrainer(0, uid(state, 0, H.SABRINAS_PSYCHIC_CONTROL)))
        state = answer(state, 0, (uid(state, 1, H.ENERGY_RETRIEVAL, "discard"),))
        state = answer(state, 0, state.decision.options[:1])
        self.assertEqual(state.decision.kind, RETRIEVE_ENERGY)
        self.assertIsNotNone(state.trainer_in_use.via)
        return state, 0

    def mind_games(self, key):
        from tests import test_slowking_mind_games_v0_132 as MG
        state = with_set(H.build_test_state([{"active": {"card": MG.HITMONCHAN, "energy": [MG.FIGHTING]}, "hand": [H.ENERGY_RETRIEVAL, H.PONYTA],
                                              "deck": [MG.FIGHTING] * 8, "discard": [H.WATER, H.FIRE]},
                                             {"active": MG.slowking(), "deck": [MG.FIGHTING] * 8}], turn_number=7, current_player=0), key)
        state = apply_command(state, PlayTrainer(0, uid(state, 0, H.ENERGY_RETRIEVAL)))
        state = answer(state, 1, ())  # ［ちえくらべ］を使わない
        state = answer(state, 0, state.decision.options[:1])
        self.assertEqual(state.decision.kind, RETRIEVE_ENERGY)
        return state, 0

    def test_excluded_paths_keep_er9(self):
        builders = {"chaos_heads": lambda k: self.chaos(k, HD), "chaos_borrowed": lambda k: self.chaos(k, TL), "psychic_control": self.psychic,
                    "mind_games_declined": self.mind_games}
        for name, build in builders.items():
            for key in (C.DEFAULT_SET, TR4):
                with self.subTest(path=name, key=key):
                    state, player = build(key)
                    before = snap(state)
                    with self.assertRaises(UnsupportedError) as caught:
                        answer(state, player, ())
                    self.assertEqual(caught.exception.code, ER9)
                    self.assertEqual(snap(state), before)
                    done = answer(state, player, state.decision.options[:1])  # 1 枚以上は今までどおり
                    self.assertNotIn("convention_applied", kinds_since(done, 0))

    def test_chaos_heads_survives_snapshot(self):
        """錯乱ジムの「おもて」は使用中の記録が手札からの使用と同じ（user・via が None）。区別は状態のログ（この使用の chaos_check）で、書き出し・復元のあとも同じ。"""
        from kyuura_engine import snapshot as SN
        state, _ = self.chaos(TR4, HD)
        self.assertEqual((state.trainer_in_use.user, state.trainer_in_use.via), (None, None))
        report = SN.restore_snapshot(SN.dumps_snapshot(SN.save_snapshot(state, label="tr4 chaos heads")))
        self.assertEqual(report.status, SN.RESTORED)
        restored = SN.RestoredGame(report).state
        with self.assertRaises(UnsupportedError) as caught:
            answer(restored, 0, ())
        self.assertEqual(caught.exception.code, ER9)

    def test_no_removal_gym_in_play_is_a_normal_use(self):
        state = with_set(board(extra_hand=(H.NO_REMOVAL_GYM,)), TR4)
        state = apply_command(state, PlayTrainer(0, uid(state, 0, H.NO_REMOVAL_GYM)))
        state = apply_command(state, PlayTrainer(0, uid(state, 0, H.ENERGY_RETRIEVAL)))
        self.assertEqual((state.decision.kind, state.decision.min_choices), (DISCARD_FROM_HAND, 1))  # 追加の条件（2 枚）はない
        state = answer(state, 0, (uid(state, 0, H.FIRE),))
        n = len(state.log)
        done = answer(state, 0, ())
        self.assertEqual(kinds_since(done, n), ["convention_applied", "discard_trainer"])
        strict = with_set(state, C.DEFAULT_SET)
        with self.assertRaises(UnsupportedError):
            answer(strict, 0, ())


class AuditTest(unittest.TestCase):
    """V12: ログの監査（s2a_problems。構築盤面なので、対戦の初めからログを組み立てる log_problems は使わない）は規約の記録を、監査が独立に持つ表とログの並びで照らす（エンジンの登録を信じない）。"""

    def test_audit_accepts_the_record_and_detects_tampering(self):
        done = answer(at_retrieve(TR4), 0, ())
        self.assertEqual(s2a_problems(done), [])
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
        log.insert(i + 1, log.pop(i))  # discard_trainer のあとに置く
        moved.log = type(moved.log)(log) if isinstance(moved.log, tuple) else log
        self.assertNotEqual(s2a_problems(moved), [])


class JudgeTest(unittest.TestCase):
    """V11: 本物の runner（構築盤面のスナップショットから）と逐次バッチの判定の入口。受理した 0 枚の答えは expected（ER9 の既知の停止に数えない）。厳密側は今の規則 6 のまま。"""

    def run_zero(self, key, negative=None):
        from tools.verification_ai import fixtures_u_r3a as F
        from tools.verification_ai import runner as V
        from tools.verification_ai.policies import UniformPolicy
        from tests.test_verification_ai_batch_judge import FixtureRunner

        class ZeroScripted(UniformPolicy):
            name, version = "scripted-test", 0

            def __init__(self):
                super().__init__("scripted-test")

            def choose(self, purpose, items, context):
                if purpose == "candidate":
                    return next(i for i, c in enumerate(items) if c["kind"] == "answer_decision"), "scripted"
                if purpose == "count":
                    return items.index(0), "scripted"
                return 0, "scripted"

        text, error = F.snapshot_text(at_retrieve(key), f"tr4-zero-{key[0]}")
        self.assertIsNotNone(text, error)
        config = V.Config(limits=V.Limits(operations=1, seconds=60), run_id=f"test-tr4-{key[0]}")
        return FixtureRunner(config, text, policy_factory=lambda seed, dist: ZeroScripted(), negative=negative).run()

    def test_accepted_zero_and_strict_rule6(self):
        from tools.verification_ai import batch as B
        from tools.verification_ai import judge as J
        from tests.test_verification_ai_batch_judge import NoNegative

        for key, outcome, verdict in ((TR4, D.ACCEPTED, J.EXPECTED), (C.DEFAULT_SET, D.REJECTED, J.KNOWN_STOP)):
            with self.subTest(key=key):
                result = self.run_zero(key)
                entries = [e for e in result["trace"] if e.get("type") == "attempt" and e.get("submit") is not None]
                self.assertEqual(len(entries), 1)
                entry = entries[0]
                self.assertEqual((entry["candidate"]["kind"], entry["choices"], entry["submit"]["outcome"]), ("answer_decision", [], outcome))
                judged = B.judge_trace(result)
                self.assertEqual(judged["counts"], {verdict: 1})
                self.assertEqual(judged["undetermined"], [])
                row = judged["rows"][0]
                if key == TR4:
                    self.assertIsNone(J.recorded_stop_evidence(entry["candidate"], entry.get("meaning") or [], entry.get("stages"), entry["submit"]))
                    self.assertEqual((row["engine_code"], row["reasons"], judged["known_stop"]), (None, [], []))
                else:
                    self.assertEqual(row["engine_code"], ER9)
                    self.assertIn("evidence:" + J.KNOWN_STOP_EVIDENCE[ER9]["condition"], row["reasons"])
                    self.assertEqual(judged["known_stop"], [entry["n"]])
                single = self.run_zero(key, negative=NoNegative())
                (s_entry,) = [e for e in single["trace"] if e.get("type") == "attempt" and e.get("submit") is not None]
                self.assertEqual(s_entry["judge"]["verdict"], verdict)  # 単局の runner の判定（変異の実行の中）も同じ


if __name__ == "__main__":
    unittest.main()

"""v0.176（PT-5e。docs/legal-actions-pt5e-audit.md 9 章）: 山札から引いて試すトレーナー 6 枚の使うための条件を、候補の作成で呼ぶ補完の限定の検証。

対象（登録で確かめる）: カツラのクイズ その1（GD5-016。BlainesHeightQuiz）・その2（GD5-017。SetAsideGuessKindQuiz）・その3（PMCG6-082。BlainesQuiz）・ポケモン性格判定
（neo4-105。SetAsideGuessKindQuiz）・カードめくりゲーム（neo1-080。GuessOpponentPrizeKind）・とりかえっこプリーズ（PR1-027。SwapPleaseTrainer）。

確かめの種類を分ける:

- 前提 A（おもての山札の並びの不変条件）: 通常の進行・スナップショットの復元・``ClientHub.from_state`` での扱い（v0.177 から崩れた状態を拒否する）。不変条件の崩れた
  状態（テスト専用の改変。信頼された内部の組み立てでだけ包む）では、引いて試す結果が本人に見えない並びで変わりうること、そのため候補では呼ばない（unverified のまま）こと
- 前提 B（浅い複製の共有）: ``GameState.clone`` が元と共有する可変の値と、引いて試す処理が変える場所。試しても元の状態・乱数・ログ・決定が変わらない
- 双子（T1 山札の順序・T2 本人の山札とサイドの配分・T3 相手の秘密）: 比べる前に、本人と観戦者の観測・公開のログが同じで、完全な状態が違うことを確かめる。候補・件数・並び・
  eligible・処理可能性・理由・保証・inputs・check の答えが同じ。候補・inputs・check の前後で状態・乱数・ログ・決定が変わらず、更新が 0 件
- 対照例（T4）: 公開の枚数・本人の手札を変えると、予想どおりに変わる（Illegal は選べるものから消え、未裁定・未対応は実行できない区分）
- 3 経路の一致: U7（ActorSession）・client_api（ClientHub）・直接のコマンド（HostedGame.submit）。U7 が送る前に断る場合と、直接のコマンドをエンジンが拒否する場合を分ける

盤面はどれも構築盤面（tests.helpers.build_test_state と、v0.135 のテストの合法な経路 play_flash・end_turns）。new_game からの到達ではない。
"""

from __future__ import annotations

import pathlib
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import effects as E
from kyuura_engine import faceup as FU
from kyuura_engine import legal_actions as L
from kyuura_engine import snapshot as SN
from kyuura_engine.client_api import ClientHub
from kyuura_engine.commands import PlayTrainer, ResolveDecision
from kyuura_engine.decisions import QUIZ_ANSWER, QUIZ_CARD, QUIZ_HEIGHT_ANSWER, SELECT_EXCHANGE_CARD, SELECT_OPPONENT_PRIZE
from kyuura_engine.effects import TrainerUse
from kyuura_engine.engine import apply_command, check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe, visible_log
from tests.helpers import BILL, HITMONCHAN, POTION, build_test_state
from tests.test_legal_actions_u7_1 import snap, without_handles
from tests.test_quiz_answer_rejection_v0_135 import (
    DRATINI,
    ENERGIES,
    FLASH,
    GYARADOS,
    card_in_hand,
    end_turns,
    fingerprint,
    play_flash,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "legal-actions-pt5e-audit.md"
CONTRACT = {"contract": "kyuura-client-api", "format": 1}

QUIZ1, QUIZ2, QUIZ3, PERSONALITY, CARD_FLIP, SWAP = "GD5-016", "GD5-017", "PMCG6-082", "neo4-105", "neo1-080", "PR1-027"
# カードごとの (型, 手札にいっしょに置くカード（条件を満たす）)
TARGETS = {
    QUIZ1: (E.BlainesHeightQuiz, HITMONCHAN),  # 図鑑番号・身長のあるポケモン
    QUIZ2: (E.SetAsideGuessKindQuiz, POTION),  # このカードを除く手札
    QUIZ3: (E.BlainesQuiz, DRATINI),  # ワザを持つポケモン
    PERSONALITY: (E.SetAsideGuessKindQuiz, GYARADOS),  # 進化カード
    CARD_FLIP: (E.GuessOpponentPrizeKind, POTION),  # （条件は相手のうらのサイド）
    SWAP: (E.SwapPleaseTrainer, POTION),  # このカードを除く手札（相手の手札は既定で 2 枚）
}
HERE_COMES_TEAM_ROCKET = "PMCG4-062"  # ロケット団参上!（お互いのサイドをすべておもてにする）
PORYGON_NO_DEX = "ES1-033"  # ポリゴン（記録に図鑑番号がない。カツラのクイズ その1 で選ぶと止める）
GRASS, FIRE_E, WATER_E, LIGHTNING_E = ENERGIES[0], ENERGIES[1], ENERGIES[2], ENERGIES[3]
QZ1, FC1, FU3 = E.BLAINES_QUIZ_WITHOUT_POKEMON_CODE, E.STATED_CARDS_SHORT_CODE, FU.FACE_UP_DECK_HIDDEN_TAKE_CODE
MODES = ("none", "top_only", "both")  # フラッシュを使わない・いちばん上だけがおもて（番の最初のドロー 4 回ずつ）・フラッシュの直後（上から 5 枚がおもて）
PASSING = {"processability": L.MAY_STOP_LATER, "eligible": True, "reasons": sorted([L.REASON_PREFLIGHT, L.REASON_CONTINUATION])}
STOPPED = {"processability": L.RULING_UNRESOLVED, "eligible": False, "reasons": [L.REASON_STOPS]}
NOT_EVALUATED = {"processability": L.UNVERIFIED, "eligible": True, "reasons": sorted([L.REASON_USE_CONDITION, L.REASON_PREFLIGHT, L.REASON_CONTINUATION])}


def table(card, *, hand=None, opponent_hand=(POTION, BILL), deck0=None, deck1=None, prizes0=None, prizes1=None, flash=True, turn_number=3):
    """プレイヤー 0 の番の MAIN。手札は（フラッシュ・）対象のカード・いっしょに置くカード。山札は基本エネルギー 12 枚ずつ（並びはプレイヤーで逆）、サイドは 6 枚ずつ。"""
    hand = list(hand if hand is not None else (TARGETS[card][1],))
    deck0 = list(ENERGIES) * 2 if deck0 is None else list(deck0)
    deck1 = list(reversed(ENERGIES)) * 2 if deck1 is None else list(deck1)
    prizes0 = [GRASS] * 6 if prizes0 is None else list(prizes0)
    prizes1 = [FIRE_E] * 6 if prizes1 is None else list(prizes1)
    return build_test_state([{"active": HITMONCHAN, "hand": ([FLASH] if flash else []) + [card] + hand, "deck": deck0, "prizes": prizes0},
                             {"active": HITMONCHAN, "hand": list(opponent_hand), "deck": deck1, "prizes": prizes1}],
                            current_player=0, turn_number=turn_number)


def staged(state, mode):
    """合法な実カードの経路でおもての山札を作る（v0.135 のテストの play_flash・end_turns）。"""
    if mode == "none":
        return state
    state = play_flash(state)
    if mode == "top_only":
        state = end_turns(state, 8)
    assert state.current_player == 0 and state.decision is None and check_invariants(state) == [], check_invariants(state)
    return state


def swapped(values, i, j):
    values = list(values)
    values[i], values[j] = values[j], values[i]
    return values


def twin_pair(card, mode, kind):
    """(元, 秘密だけを変えた双子)。T1: 山札の順序（おもてでない範囲。none は上の 2 枚、ほかは 8 枚目と 11 枚目。本人・相手の両方）。T2: 本人の山札とサイドの配分（同じ枚数）。
    T3: 相手の手札の中身（同じ枚数）・相手のサイドの中身・相手の山札の順序。"""
    deck0, deck1 = list(ENERGIES) * 2, list(reversed(ENERGIES)) * 2
    i, j = (1, 2) if mode == "none" else (7, 10)  # none は 2 枚目と 3 枚目（引く 2 枚の境目をまたぐ）。top_only は上の 4 枚を引いたあと、おもては 1 枚。both はおもてが上の 5 枚
    if kind == "T1":
        variant = {"deck0": swapped(deck0, i, j), "deck1": swapped(deck1, i, j)}
    elif kind == "T2":
        d0, p0 = list(deck0), [GRASS] * 6
        k = i if mode == "none" else 9
        assert d0[k] != p0[2]  # 違うカードを入れかえる
        d0[k], p0[2] = p0[2], d0[k]
        variant = {"deck0": d0, "prizes0": p0}
    else:
        variant = {"opponent_hand": (BILL, DRATINI), "prizes1": [WATER_E, FIRE_E, LIGHTNING_E, FIRE_E, FIRE_E, FIRE_E], "deck1": swapped(deck1, i, j)}
    return staged(table(card), mode), staged(table(card, **variant), mode)


def queries(state, actor=0, *, internal=False):
    """client_api の入口で、本人の候補・すべての候補の inputs・選べるものごとと不正な入力への check の答え（取っ手を除く）。前後の状態・乱数・ログ・決定と、全員への更新。

    ``internal``（v0.177）: 不変条件の崩れた状態の低層の振る舞いを確かめるときだけ、信頼された内部の組み立て ``ClientHub(A.HostedGame(state.clone()))`` を使う
    （検証者専用。通常の使い方ではない。``ClientHub.from_state`` は崩れた状態を拒否する）。"""
    original = fingerprint(state)
    hub = ClientHub(A.HostedGame(state.clone())) if internal else ClientHub.from_state(state)
    me = hub.player(actor)
    before = (snap(hub._host.game.state), fingerprint(hub._host.game.state))
    r = me.handle({**CONTRACT, "type": "candidates"})["response"]
    out = [without_handles(r)]
    for c in r["candidates"]:
        fields = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        found = me.handle({**CONTRACT, "type": "inputs", **fields})["response"]
        out.append(found)
        ids = [o["id"] for stage in found.get("stages") or [] for o in stage.get("options") or []]
        for choices in [[x] for x in ids] + [[], ["o99"], [1]]:
            out.append(me.handle({**CONTRACT, "type": "check", **fields, "choices": choices})["response"])
    after = (snap(hub._host.game.state), fingerprint(hub._host.game.state))
    updates = [hub.take_updates(a) for a in (0, 1, "spectator", "host")]
    return out, before == after and fingerprint(state) == original, updates


def trainer_option(state, card, actor=0):
    """本人の play_trainer の候補で、``card`` のカードの選べるもの（なければ None）と、候補（なければ None）。"""
    session = L.ActionHost(A.HostedGame(state.clone())).session(actor)
    r = session.candidates()
    c = next((x for x in r["candidates"] if x["kind"] == L.KIND_PLAY_TRAINER), None)
    if c is None:
        return None, None
    stage = session.inputs(r["game"], r["revision"], c["id"])["stages"][0]
    option = next((o for o in stage["options"] if o["card_id"] == card), None)
    return option, c


def status(option):
    return None if option is None else {"processability": option["processability"], "eligible": option["eligible"], "reasons": sorted(option["reasons"])}


def broken_marks(state, owner, position):
    """テスト専用の改変（合法な経路ではない。不変条件を崩す）: ``owner`` の山札のおもての印を、上から ``position`` 枚目（0 から）の 1 枚だけにする。"""
    state = state.clone()
    deck = state.players[owner].deck
    state.face_up_deck = tuple(uid for uid in state.face_up_deck if uid not in deck) + (deck[position],)
    return state


class RegistrationTest(unittest.TestCase):
    """対象の 5 つの型・6 枚を、実際の登録で確かめる（名前から推測しない）。"""

    def test_registered_cards_and_classification(self):
        registry = E.DEFAULT_EFFECTS
        owners = {}
        for card_id in registry._trainers:
            effect = registry.trainer_entry(card_id).effect
            owner = L._use_condition_owner(effect)
            if owner is not None and owner.__name__ in L.PLAYABLE_FACE_UP_PREFIX_TRIALS:
                owners[card_id] = owner.__name__
        self.assertEqual(owners, {card: cls.__name__ for card, (cls, _) in TARGETS.items()})
        self.assertEqual(L.PLAYABLE_NOT_EVALUATED, frozenset())
        self.assertEqual(L.PLAYABLE_FACE_UP_PREFIX_TRIALS, frozenset(cls.__name__ for cls, _ in TARGETS.values()))
        self.assertEqual(L.PLAYABLE_FACE_UP_PREFIX_TRIALS & L.PLAYABLE_BOARD_TRIALS, frozenset())
        for card, (cls, _) in TARGETS.items():
            self.assertEqual(L._use_condition_owner(registry.trainer_entry(card).effect).__module__, "kyuura_engine.effects", card)


class PrefixPremiseTest(unittest.TestCase):
    """前提 A: おもての山札の並びの不変条件（faceup.prefix_problems）。"""

    def test_normal_progress_keeps_the_invariant(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                state = staged(table(QUIZ3), mode)
                self.assertEqual(FU.prefix_problems(state), [])
                self.assertEqual(check_invariants(state), [])

    def test_snapshot_restore_rejects_a_broken_invariant(self):
        state = staged(table(QUIZ3), "top_only")
        text = SN.dumps_snapshot(SN.save_snapshot(state, label="pt5e"))
        restored = SN.restore_snapshot(text)
        self.assertTrue(restored.restored)
        self.assertEqual(FU.prefix_problems(restored.state), [])
        broken = broken_marks(state, 1, 2)
        self.assertNotEqual(FU.prefix_problems(broken), [])
        with self.assertRaises(SN.SnapshotSaveError):
            SN.save_snapshot(broken, label="pt5e-broken")

    def test_from_state_rejects_a_broken_invariant_and_the_condition_is_not_evaluated_internally(self):
        """独立した課題 PT5E-FROM-STATE-INVARIANT（docs/pt5e-from-state-invariant-audit.md）: v0.177 から ClientHub.from_state・ActionHost.from_state は、不変条件の崩れた
        状態を、hub・セッション・取っ手を作る前に UnusableStateError（STATE_INTEGRITY。固定の文）で拒否する。v0.176 では受け付けていた（契約の変更）。

        崩れた状態の低層の振る舞い（検証者専用。信頼された内部の組み立て ``HostedGame``）: 引いて試す結果は本人に見えない相手のおもての位置で変わる（本人の観測は同じ）。
        候補は条件を呼ばず unverified のまま（位置によらない。PT-5e の候補の側のガードは残す）。"""
        base = staged(table(QUIZ3), "top_only")
        far, near = broken_marks(base, 1, 6), broken_marks(base, 1, 1)  # 相手の山札の 7 枚目・2 枚目だけがおもて（いちばん上はうら）
        rejected = []
        for state in (far, near):
            self.assertNotEqual(FU.prefix_problems(state), [])
            for entry in (ClientHub.from_state, L.ActionHost.from_state):
                with self.assertRaises(A.UnusableStateError) as caught:
                    entry(state)
                rejected.append((type(caught.exception), caught.exception.code, str(caught.exception)))
        self.assertEqual(len(set(rejected)), 1)  # 秘密の位置・入口によらず、型・code・文が同じ
        self.assertEqual(rejected[0][1], A.STATE_INTEGRITY_CODE)
        self.assertEqual(observe(far, 0), observe(near, 0))
        use = TrainerUse(0, card_in_hand(far, QUIZ3, 0), QUIZ3)
        self.assertIsNone(E.quiz_draw_outcome_stop(far, 0, 3))
        self.assertEqual(E.quiz_draw_outcome_stop(near, 0, 3)[0], FU3)  # 正解なら相手が 3 枚引く: 2 枚目のおもてで止まる
        with self.assertRaises(UnsupportedError):
            E.BlainesQuiz(E.BLAINES_QUIZ_3_TEXT).check_playable(near, use)
        self.assertEqual([status(trainer_option(s, QUIZ3)[0]) for s in (far, near)], [NOT_EVALUATED, NOT_EVALUATED])
        self.assertEqual(queries(far, internal=True)[0], queries(near, internal=True)[0])
        # 送ったときの結果は、崩れた状態ではエンジンの経路で位置によって分かれる（near: 使う前の FU3 の拒否、far: 受理のあとのコマンドの終わりの不変条件の確かめで failed）。
        # 候補の補完とは別の、構築盤面の入口の課題として記録する（9.2 節）
        outcomes = []
        for state in (far, near):
            result = A.HostedGame(state.clone()).submit(PlayTrainer(0, card_in_hand(state, QUIZ3, 0)), submitter=0)
            outcomes.append((result.outcome, result.diagnosis.diagnostic_id))
        self.assertEqual(outcomes, [(D.FAILED, "STATE_INTEGRITY"), (D.REJECTED, FU3)])

    def test_broken_invariant_keeps_the_engine_rejection_private(self):
        """不変条件の崩れた状態（評価しない）では、使えないカードも unverified で示し、送るとエンジンが本人にだけ拒否する（v0.175 までと同じ）。

        v0.177: ClientHub.from_state は崩れた状態を拒否するので、低層の振る舞いを確かめるこのテストは、信頼された内部の組み立て ``ClientHub(A.HostedGame(...))`` を使う
        （検証者専用。通常の使い方ではない）。主張は変えていない。"""
        state = broken_marks(staged(table(SWAP, hand=()), "both"), 1, 2)  # フラッシュを使ったあと、手札はとりかえっこプリーズだけ
        self.assertEqual([state.cards[u].card_id for u in state.players[0].hand], [SWAP])
        option, c = trainer_option(state, SWAP)
        self.assertEqual(status(option), NOT_EVALUATED)
        hub = ClientHub(A.HostedGame(state.clone()))  # 信頼された内部の組み立て（検証者専用）
        me = hub.player(0)
        r = me.handle({**CONTRACT, "type": "candidates"})["response"]
        fields = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        before = snap(hub._host.game.state)
        sent = me.handle({**CONTRACT, "type": "submit", **fields, "choices": [option["id"]]})
        self.assertEqual(sent["outcome"], D.REJECTED)
        self.assertEqual((sent["result"]["role"], sent["result"]["diagnostic_id"]), ("actor", "NO_OTHER_CARDS_IN_HAND"))  # 診断は送った本人だけ
        self.assertEqual(snap(hub._host.game.state), before)
        self.assertEqual([hub.take_updates(a) for a in (1, "spectator")], [[], []])
        self.assertTrue(me.handle({**CONTRACT, "type": "check", **fields, "choices": [option["id"]]})["response"]["valid"])


class ClonePremiseTest(unittest.TestCase):
    """前提 B: GameState.clone は __dict__ の浅い写しで、players（山札・手札・サイド・トラッシュ・場の配列）と乱数だけを写し直す。引いて試す処理が変えるのは、写した山札・手札の配列と、
    付け替えるログ・おもての印（どちらも不変のタプル）だけ。共有する可変の値は変えない。"""

    def shared_mutables(self, state):
        trial = state.clone()
        return trial, {k: v for k, v in state.__dict__.items() if k not in ("players", "rng") and trial.__dict__.get(k) is v and isinstance(v, (list, dict, set, bytearray))}

    def test_clone_copies_the_zones(self):
        state = staged(table(QUIZ3), "both")
        trial, _shared = self.shared_mutables(state)
        for a, b in zip(state.players, trial.players):
            for zone in ("deck", "hand", "prizes", "discard", "bench"):
                self.assertIsNot(getattr(a, zone), getattr(b, zone))
        self.assertIsNot(state.rng, trial.rng)
        self.assertIsInstance(state.log, tuple)
        self.assertIsInstance(state.face_up_deck, tuple)

    def test_trial_draws_leave_the_original_and_shared_values(self):
        for mode in MODES:
            for card in TARGETS:
                with self.subTest(mode=mode, card=card):
                    state = staged(table(card), mode)
                    _trial, shared = self.shared_mutables(state)
                    shared_before = {k: repr(v) for k, v in shared.items()}
                    before = fingerprint(state)
                    effect = E.DEFAULT_EFFECTS.trainer_entry(card).effect
                    use = TrainerUse(0, card_in_hand(state, card, 0), card)
                    for _ in range(2):
                        try:
                            effect.check_playable(state, use)
                        except (IllegalActionError, UnsupportedError):
                            pass
                        for drawer in (0, 1):  # 試しの複製で引く（2 枚目より下がおもてなら FU3 で止まる）
                            try:
                                E._draw_up_to(state.clone(), drawer, 3)
                            except UnsupportedError:
                                pass
                    self.assertEqual(fingerprint(state), before)
                    self.assertEqual({k: repr(v) for k, v in shared.items()}, shared_before)


class TwinTest(unittest.TestCase):
    """T1〜T3: 秘密の配分だけが違う双子で、本人の候補・inputs・check の答えが同じ。候補・inputs・check は状態を変えず、更新を作らない。"""

    def assert_twin(self, a, b):
        self.assertNotEqual(fingerprint(a)[0], fingerprint(b)[0])  # 完全な状態は違う
        for viewer in (0, None):  # 比べる前に: 本人と観戦者（公開）の観測・ログが同じ
            self.assertEqual(observe(a, viewer), observe(b, viewer))
            self.assertEqual(visible_log(a, viewer), visible_log(b, viewer))
        qa, qb = queries(a), queries(b)
        self.assertEqual(qa[0], qb[0])
        self.assertEqual((qa[1], qb[1]), (True, True))
        self.assertEqual((qa[2], qb[2]), ([[], [], [], []], [[], [], [], []]))

    def test_twins(self):
        for kind in ("T1", "T2", "T3"):
            for mode in (MODES if kind == "T1" else ("none", "top_only")):
                for card in TARGETS:
                    with self.subTest(kind=kind, mode=mode, card=card):
                        a, b = twin_pair(card, mode, kind)
                        self.assert_twin(a, b)
                        expected = STOPPED if mode == "both" else PASSING
                        self.assertEqual([status(trainer_option(s, card)[0]) for s in (a, b)], [expected, expected])

    def test_results_after_acceptance_may_differ(self):
        """候補の段階の一致と別に、受理のあとの結果は秘密で正当に違う（本人の山札の順序の双子で、正解でない答えで本人が引くカード）。"""
        a, b = twin_pair(QUIZ2, "none", "T1")
        hands = []
        for state in (a, b):
            state = apply_command(state, PlayTrainer(0, card_in_hand(state, QUIZ2, 0)))
            state = apply_command(state, ResolveDecision(0, state.decision.id, (card_in_hand(state, POTION, 0),)))
            self.assertEqual(state.decision.kind, QUIZ_ANSWER)
            state = apply_command(state, ResolveDecision(1, state.decision.id, (0,)))  # 「ポケモン」（置いたのはトレーナー。正解でない → 使ったプレイヤーが 2 枚引く）
            hands.append(sorted(state.cards[u].card_id for u in state.players[0].hand))
        self.assertNotEqual(hands[0], hands[1])


class ControlTest(unittest.TestCase):
    """T4: 公開の枚数・本人の手札を変えると、予想どおりに変わる。"""

    def test_controls(self):
        team_rocket = table(CARD_FLIP, hand=(HERE_COMES_TEAM_ROCKET,))
        team_rocket = apply_command(team_rocket, PlayTrainer(0, card_in_hand(team_rocket, HERE_COMES_TEAM_ROCKET, 0)))  # 相手のサイドがすべておもて
        cases = [
            ("QUIZ1 図鑑番号のないポケモンだけ", QUIZ1, table(QUIZ1, hand=(PORYGON_NO_DEX,), flash=False), {**STOPPED, "processability": L.NOT_IMPLEMENTED}),
            ("QUIZ1 ポケモンなし", QUIZ1, table(QUIZ1, hand=(POTION,), flash=False), STOPPED),
            ("QUIZ2 ほかの手札なし", QUIZ2, table(QUIZ2, hand=(), flash=False), STOPPED),
            ("QUIZ3 ワザを持つポケモンなし", QUIZ3, table(QUIZ3, hand=(POTION,), flash=False), STOPPED),
            ("性格判定 進化カードなし", PERSONALITY, table(PERSONALITY, hand=(POTION,)), None),
            ("カードめくり うらの相手のサイドなし", CARD_FLIP, team_rocket, STOPPED),
            ("とりかえっこ 相手の手札なし", SWAP, table(SWAP, opponent_hand=()), None),
            ("とりかえっこ ほかの手札なし", SWAP, table(SWAP, hand=(), flash=False), None),
        ]
        for name, card, state, expected in cases:
            with self.subTest(case=name):
                option, c = trainer_option(state, card)
                self.assertEqual(status(option), expected)
                _out, quiet, updates = queries(state)
                self.assertTrue(quiet)
                self.assertEqual(updates, [[], [], [], []])
        for mode, expected in (("none", PASSING), ("top_only", PASSING), ("both", STOPPED)):  # おもての枚数（公開）
            with self.subTest(mode=mode):
                self.assertEqual(status(trainer_option(staged(table(SWAP), mode), SWAP)[0]), expected)


class SameAsDirectTest(unittest.TestCase):
    """U7・client_api・直接のコマンド: 条件を通るカードは同じ受理・状態・決定。使えない・止まるカードは、U7 が送る前に断り（意図した API 上の差）、直接のコマンドはエンジンが拒否する。"""

    def u7_submit(self, state, card):
        host = L.ActionHost(A.HostedGame(state.clone()))
        session = host.session(0)
        r = session.candidates()
        c = next(x for x in r["candidates"] if x["kind"] == L.KIND_PLAY_TRAINER)
        stage = session.inputs(r["game"], r["revision"], c["id"])["stages"][0]
        option = next(o["id"] for o in stage["options"] if o["card_id"] == card)
        return host, session.check(r["game"], r["revision"], c["id"], [option]), session.submit(r["game"], r["revision"], c["id"], [option])

    def client_submit(self, state, card):
        hub = ClientHub.from_state(state)
        me = hub.player(0)
        r = me.handle({**CONTRACT, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == L.KIND_PLAY_TRAINER)
        fields = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        stage = me.handle({**CONTRACT, "type": "inputs", **fields})["response"]["stages"][0]
        option = next(o["id"] for o in stage["options"] if o["card_id"] == card)
        return hub, me.handle({**CONTRACT, "type": "submit", **fields, "choices": [option]})

    def test_passing_cards_match_the_direct_command(self):
        expected_next = {QUIZ1: QUIZ_CARD, QUIZ2: QUIZ_CARD, QUIZ3: QUIZ_CARD, PERSONALITY: QUIZ_CARD, CARD_FLIP: SELECT_OPPONENT_PRIZE, SWAP: SELECT_EXCHANGE_CARD}
        for card in TARGETS:
            with self.subTest(card=card):
                state = table(card)
                host, checked, result = self.u7_submit(state, card)
                hub, sent = self.client_submit(state, card)
                game = A.HostedGame(state.clone())
                direct = game.submit(PlayTrainer(0, card_in_hand(state, card, 0)), submitter=0)
                self.assertTrue(checked["valid"])
                self.assertEqual((result.outcome, sent["outcome"], direct.outcome), (D.ACCEPTED,) * 3)
                self.assertEqual(result.view, direct.view_for(0))
                self.assertEqual(snap(host.game.state), snap(game.state))
                self.assertEqual(snap(hub._host.game.state), snap(game.state))
                self.assertEqual(game.state.decision.kind, expected_next[card])

    def test_continuation_after_acceptance_matches(self):
        """受理のあとの決定（置くカード・相手の答え）も、U7 の answer_decision と直接の ResolveDecision で同じ状態になる（その2・その1）。"""
        for card, companion, answer in ((QUIZ2, POTION, (0,)), (QUIZ1, HITMONCHAN, None)):
            with self.subTest(card=card):
                state = table(card)
                host, _checked, _result = self.u7_submit(state, card)
                game = A.HostedGame(state.clone())
                game.submit(PlayTrainer(0, card_in_hand(state, card, 0)), submitter=0)
                for _ in range(2):
                    d = game.state.decision
                    if d.kind == QUIZ_CARD:
                        choices = (card_in_hand(game.state, companion, 0),)
                    elif d.kind == QUIZ_HEIGHT_ANSWER:
                        choices = (1,)
                    else:
                        choices = answer
                    session = host.session(d.player)
                    r = session.candidates()
                    c = next(x for x in r["candidates"] if x["kind"] == L.KIND_ANSWER_DECISION)
                    found = session.inputs(r["game"], r["revision"], c["id"])
                    stage = found["stages"][0]
                    if stage["input"] == L.INPUT_CHOOSE_OPTION:
                        ids = [o["id"] for o in stage["options"] if o.get("value", o.get("card")) in choices]
                    else:
                        ids = list(choices)
                    sent = session.submit(r["game"], r["revision"], c["id"], ids)
                    direct = game.submit(ResolveDecision(d.player, d.id, choices), submitter=d.player)
                    self.assertEqual((sent.outcome, direct.outcome), (D.ACCEPTED, D.ACCEPTED))
                    self.assertEqual(snap(host.game.state), snap(game.state))
                self.assertIsNone(game.state.decision)

    def test_unusable_and_stopping_cards(self):
        cases = [
            ("Illegal（性格判定・進化カードなし）", PERSONALITY, table(PERSONALITY, hand=(POTION,)), "absent", IllegalActionError, "NO_EVOLUTION_CARD_IN_HAND"),
            ("Illegal（とりかえっこ・相手の手札なし）", SWAP, table(SWAP, opponent_hand=()), "absent", IllegalActionError, "OPPONENT_HAND_EMPTY"),
            ("未裁定（その3・QZ1）", QUIZ3, table(QUIZ3, hand=(POTION,), flash=False), "not_executable", UnsupportedError, QZ1),
            ("未裁定（その2・FC1）", QUIZ2, table(QUIZ2, hand=(), flash=False), "not_executable", UnsupportedError, FC1),
            ("未裁定（カードめくり・FU3）", CARD_FLIP, staged(table(CARD_FLIP), "both"), "not_executable", UnsupportedError, FU3),
            ("未対応（その1・図鑑番号なし）", QUIZ1, table(QUIZ1, hand=(PORYGON_NO_DEX,), flash=False), "not_executable", UnsupportedError, E.QUIZ_HEIGHT_WITHOUT_DEX_CODE),
        ]
        for name, card, state, api, error, code in cases:
            with self.subTest(case=name):
                game = A.HostedGame(state.clone())
                direct = game.submit(PlayTrainer(0, card_in_hand(state, card, 0)), submitter=0)
                self.assertEqual((direct.outcome, direct.diagnosis.diagnostic_id), (D.REJECTED, code))
                with self.assertRaises(error):
                    apply_command(state, PlayTrainer(0, card_in_hand(state, card, 0)))
                option, _c = trainer_option(state, card)
                if api == "absent":
                    self.assertIsNone(option)
                    continue
                self.assertFalse(option["eligible"])
                before = fingerprint(state)
                host, checked, result = self.u7_submit(state, card)
                self.assertEqual((checked["valid"], checked["refusal"]["code"]), (False, L.CANDIDATE_NOT_EXECUTABLE))
                self.assertEqual(result.refusal.code, L.CANDIDATE_NOT_EXECUTABLE)
                self.assertEqual(snap(host.game.state), snap(state))
                self.assertEqual(fingerprint(state), before)
                hub, sent = self.client_submit(state, card)
                self.assertEqual(sent["refusal"]["code"], L.CANDIDATE_NOT_EXECUTABLE)
                self.assertEqual([hub.take_updates(a) for a in (0, 1, "spectator", "host")], [[], [], [], []])


class GuaranteeTest(unittest.TestCase):
    def test_guarantee_text_states_the_scope(self):
        text = L.GUARANTEE_TRAINER["preconditions"]
        self.assertIn("PLAYABLE_FACE_UP_PREFIX_TRIALS", text)
        self.assertIn("不変条件", text)
        self.assertNotIn("PLAYABLE_NOT_EVALUATED", text)
        self.assertIn("supported にしない", L.GUARANTEE_TRAINER["supported_scope"])
        self.assertIn("保証しない", L.GUARANTEE_TRAINER["acceptance"])


if __name__ == "__main__":
    unittest.main()

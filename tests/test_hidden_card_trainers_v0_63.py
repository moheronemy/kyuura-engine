"""v0.63: 公開・非公開の状態を扱うトレーナー 4 枚（docs/hidden-card-trainers-v0.63.md）。

4 枚: ロケット団参上!（PMCG4-062）・くすぐりマシーン（PMCG6-084）・たたきつけろ!挑戦状（PMCG4-058）・カツラのクイズ その3（PMCG6-082）。
どれも kyuura データの採用（処理に使う文面は kyuura の印刷の文面。採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合（3 枚 match、
挑戦状は名前の空白と文面の空行だけの違い）。kyuura の研究の基準のコミット（3f34908）に、4 枚の最新の説明・エラッタ・裁定・論点の記録はない。
ガイドブックは読んでいない。英語版の文面・現代のルール・のちの版の規定で、日本語版の条件を補わない。

共通の仕組み: カードが物理的にある場所（一時的に置いておくカード ``GameState.set_aside``。手札・山札・ベンチとは別の場所）・いまだれが中身を見られるか
（``SetAsideCards.visible_to``・おもてのサイド ``GameState.face_up_prizes``）・確定した選択ともどす期限（置いた場所・決定の続きの情報・``return_turn``）を分けて持つ。
新しい停止コード: QZ1（カツラのクイズ その3の手札にワザを持つポケモンのカードがない）。再利用: HC5（挑戦状の「好きなだけ」の 0 枚）・GG1・CH1。
"""

from __future__ import annotations

import json
import pathlib
import pickle
import unittest

from kyuura_engine import (
    EndTurn,
    IllegalActionError,
    Phase,
    PlayTrainer,
    UsePokemonPower,
    check_invariants,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.decisions import (
    ACCEPT_REQUEST,
    CHALLENGE_BENCH,
    QUIZ_ANSWER,
    QUIZ_ATTACK,
    QUIZ_CARD,
    SELECT_PRIZE_CARD,
)
from kyuura_engine.observation import (
    HIDDEN_COUNT_KINDS,
    OPTION_MEANINGS,
    PRIVATE_FIELDS,
    PUBLIC_EVENTS,
)
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import (
    SET_ASIDE_FACE_DOWN_BENCH,
    SET_ASIDE_HAND,
    SET_ASIDE_QUIZ,
)
from tests.helpers import (
    ALAKAZAM,
    ARBOK,
    BLAINES_QUIZ_3,
    CHALLENGE,
    CHAOS_GYM,
    CHARIZARD,
    CHARMELEON,
    DARK_ARBOK,
    DITTO,
    FIGHTING,
    GOOP_GAS_ATTACK,
    HERE_COMES_TEAM_ROCKET,
    HITMONCHAN,
    JUNGLE_PIKACHU,
    LT_SURGES_TREATY,
    MISTYS_WISH,
    MR_MIME,
    MYSTERIOUS_FOSSIL,
    NARROW_GYM,
    PIKACHU,
    POTION,
    RATTATA,
    ROCKET_GRUNT,
    ROCKET_RATTATA,
    SABRINAS_PSYCHIC_CONTROL,
    SECRET_MISSION,
    TICKLING_MACHINE,
    V0_63_CARDS,
    VULPIX,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import LATEST_FORMAT
from tests.test_instant_trainers_v0_55 import (
    answer,
    assert_answer_stops,
    assert_use_stops,
    audited,
    board,
    card_of,
    kinds,
    mon,
    use,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "hidden-card-trainers-v0.63.md"
TURN = 7
F = FIGHTING
QZ1 = "UNRESOLVED_BLAINES_QUIZ_WITHOUT_POKEMON"
HC5 = "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO"


def all_views(state):
    """観測（プレイヤー 0・1・観戦者）とログの写し。見えない情報の比較に使う。"""
    return [(observe(state, viewer), visible_log(state, viewer)) for viewer in (0, 1, None)]


def without_uids(value):
    """観測から、カードの uid だけを除いた形（uid は見えるカードにだけ付く。中身の違う 2 つの盤面で、見えるカードの番号の付き方だけが違うことがある）。"""
    if isinstance(value, dict):
        return {k: without_uids(v) for k, v in value.items() if k not in ("card", "cards", "trainer_card", "pokemon", "seed")}
    if isinstance(value, list):
        return [without_uids(v) for v in value]
    return value


def rocket_board(hand=(), *, opponent_hand=(), prizes=6, opponent_prizes=6, **kw):
    me = {"active": kw.pop("active", mon(HITMONCHAN, (F,))), "bench": list(kw.pop("bench", [RATTATA])), "hand": list(hand), "prizes": prizes}
    if "deck" in kw:
        me["deck"] = list(kw.pop("deck"))
    them = {"active": mon(HITMONCHAN, (F, F)), "bench": [RATTATA], "hand": list(opponent_hand), "prizes": opponent_prizes}
    return build_test_state([me, them], turn_number=TURN, current_player=0)


# ---------------------------------------------------------------- 登録・資料


class RegistrationTest(unittest.TestCase):
    def test_pool_registrations_and_types(self):
        pool = load_card_pool()
        expected = {HERE_COMES_TEAM_ROCKET: E.RevealAllPrizesTrainer, TICKLING_MACHINE: E.CoinSetAsideOpponentHandElseEndTurn,
                    CHALLENGE: E.ChallengeBenchFromDecks, BLAINES_QUIZ_3: E.BlainesQuiz}
        for card_id, cls in expected.items():
            with self.subTest(card=card_id):
                self.assertTrue(pool.get(card_id).supported)
                entry = E.DEFAULT_EFFECTS.trainer_entry(card_id)
                self.assertIsInstance(entry.effect, cls)
                self.assertEqual(entry.play_text_ja, pool.get(card_id).trainer_text_ja)  # 処理に使う文面は kyuura の印刷の文面
                self.assertEqual(entry.source, "kyuura data/cards.json")
                self.assertEqual(entry.effect.check(pool.get(card_id)), [])
        self.assertEqual(tuple(sorted(expected)), tuple(sorted(V0_63_CARDS)))
        self.assertTrue(E.DEFAULT_EFFECTS.trainer_entry(TICKLING_MACHINE).effect.refers_to_user_turn)  # 「次の相手の番」「あなたの番」: 錯乱ジムで借りると CH1
        self.assertFalse(any(E.DEFAULT_EFFECTS.trainer_entry(c).effect.refers_to_user_turn for c in (HERE_COMES_TEAM_ROCKET, CHALLENGE, BLAINES_QUIZ_3)))

    def test_counts_from_the_registry(self):
        pool = load_card_pool()
        counts = {"pokemon": 0, "trainer": 0, "energy": 0}
        for card_id in pool.playable_ids:
            counts[pool.get(card_id).category] += 1
        self.assertEqual((counts["pokemon"], counts["trainer"], counts["energy"]), (350, 93, 10))  # v0.64 でポケモン 3 枚を加えた  # v0.65 でポケモン 2 枚・トレーナー 1 枚を加えた  # v0.66 でトレーナー 3 枚を加えた
        self.assertEqual(sum(counts.values()), 454)  # v0.64 でポケモン 3 枚を加えた  # v0.65 で 3 枚を加えた  # v0.66 で 3 枚を加えた  # v0.67 で 1 枚を加えた
        self.assertEqual(len(E.DEFAULT_EFFECTS.attack_keys()), 593)  # v0.63 ではワザ・特殊能力を変えていない。v0.64 でワザ 5 つ、v0.65 でワザ 2 つを加えた
        self.assertEqual(len(E.DEFAULT_EFFECTS.power_keys()), 56)  # v0.65 で 2 つを加えた

    def test_registration_rejects_text_mismatches(self):
        pool = load_card_pool()
        for card_id in V0_63_CARDS:
            effect = E.DEFAULT_EFFECTS.trainer_entry(card_id).effect
            with self.subTest(card=card_id):
                changed = type(effect)(effect.text + "。")
                self.assertTrue(changed.check(pool.get(card_id)))
        # くすぐりマシーンは kyuura の種類 rockets_secret_machine だけを受け付ける。ほかのトレーナーは種類のないものだけ
        self.assertEqual(pool.get(TICKLING_MACHINE).trainer_kinds, ("rockets_secret_machine",))
        self.assertEqual(pool.get(CHALLENGE).trainer_kinds, ())

    def test_card_sources_and_research_links(self):
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        results = {HERE_COMES_TEAM_ROCKET: "match", TICKLING_MACHINE: "match", CHALLENGE: "differences", BLAINES_QUIZ_3: "match"}
        for card_id, result in results.items():
            record = sources[card_id]
            with self.subTest(card=card_id):
                self.assertEqual((record["basis"], record["status"], record["kyuura_records"]), ("kyuura_data", "adopted", []))
                self.assertEqual(record["play_text"], {"trainer": "kyuura_printed_text"})
                check = record["external_checks"][0]
                self.assertEqual((check["site"], check["result"]), ("pcg-search.com", result))
                self.assertTrue(all(not d["affects_behavior"] for d in check["differences"]))
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (147, 149))  # v0.65 で NT1〜NT3・RX1・FL1・BG1・BG2・KD1 を加えた。v0.66 で CA1・ES1〜ES3 を加えた  # v0.67 で FD1・FD2 を加えた
        self.assertEqual(links["stop_codes"][QZ1]["kyuura_disposition"], "not_in_kyuura")
        self.assertIn({"version": "v0.63", "document": "docs/hidden-card-trainers-v0.63.md", "ruling_id": "HC5"},
                      links["stop_codes"][HC5]["engine_rulings"])

    def test_observation_tables_and_format(self):
        for kind in (CHALLENGE_BENCH, QUIZ_CARD, QUIZ_ATTACK, QUIZ_ANSWER):
            self.assertIn(kind, OPTION_MEANINGS)
        self.assertEqual(HIDDEN_COUNT_KINDS, frozenset({CHALLENGE_BENCH, QUIZ_CARD, QUIZ_ATTACK}))
        for event in ("set_aside_hand", "set_aside_returned", "face_down_bench", "challenge_bench_skipped", "quiz_card_set"):
            self.assertIn(event, PRIVATE_FIELDS)
        for event in ("prizes_revealed", "face_down_revealed", "quiz_hint", "quiz_answer", "quiz_reveal"):
            self.assertIn(event, PUBLIC_EVENTS)
        self.assertEqual((max(FORMAT_VERSIONS), LATEST_FORMAT), (21, 21))

    def test_no_card_id_branches_in_engine_or_resolution(self):
        texts = [(ROOT / "kyuura_engine" / "engine.py").read_text(encoding="utf-8")]
        texts += [p.read_text(encoding="utf-8") for p in (ROOT / "kyuura_engine" / "resolution").glob("*.py")]
        for card_id in V0_63_CARDS:
            self.assertFalse(any(card_id in text for text in texts), card_id)

    def test_document_lists_the_cards_and_codes(self):
        text = DOC.read_text(encoding="utf-8")
        for word in (*V0_63_CARDS, "QZ1", QZ1, "HC5", "GG1", "CH1", "公式ガイドブック"):
            self.assertIn(word, text)


# ---------------------------------------------------------------- ロケット団参上!


class HereComesTeamRocketTest(unittest.TestCase):
    def test_reveals_every_prize_to_everyone(self):
        state = rocket_board([HERE_COMES_TEAM_ROCKET])
        before = all_views(state)
        for viewer in (0, 1, None):
            self.assertEqual(before[0 if viewer is None else viewer][0]["players"][1]["prizes"]["face_up"], [])  # 使う前は見えない
        after = use(state, HERE_COMES_TEAM_ROCKET)
        self.assertEqual(kinds(after), ["play_trainer", "prizes_revealed", "prizes_revealed", "discard_trainer"])
        self.assertEqual(set(after.face_up_prizes), set(after.players[0].prizes) | set(after.players[1].prizes))
        for viewer in (0, 1, None):
            view = observe(after, viewer)
            for owner in (0, 1):
                self.assertEqual([f["card"] for f in view["players"][owner]["prizes"]["face_up"]], list(after.players[owner].prizes))
        audited(self, after)

    def test_taking_a_face_up_prize_does_not_make_the_hand_public(self):
        """マチスの交渉でおもてのサイドを取る: 取ったカードはおもての記録から除き、取ったログは全員に見える（おもてだった）が、手札は公開にならない。"""
        state = use(rocket_board([HERE_COMES_TEAM_ROCKET, LT_SURGES_TREATY]), HERE_COMES_TEAM_ROCKET)
        state = use(state, LT_SURGES_TREATY)
        state = answer(state, (1,))
        self.assertEqual(state.decision.kind, SELECT_PRIZE_CARD)
        options = observe(state, 0)["decision"]["options"]
        self.assertTrue(all("card_id" in o for o in options))  # おもての位置はカードが見えている
        taken = state.players[0].prizes[0]
        state = answer(state, (0,))
        self.assertNotIn(taken, state.face_up_prizes)
        event = [e for e in state.log if e["kind"] == "trainer_take_prize"][-1]
        self.assertEqual(event["face_up"], ("card",))
        self.assertEqual(visible_log(state, 1)[-1 - next(i for i, e in enumerate(reversed(state.log)) if e is event)]["card"], taken)
        self.assertIsNone(observe(state, 1)["players"][0]["hand"]["cards"])  # 手札は公開にならない
        audited(self, state)

    def test_cards_put_into_prizes_later_stay_face_down(self):
        """カスミのわがままでサイドに置いた手札のカードは裏（おもてにする指示がない）。おもてだったカードは手札に来る（ログに印）。"""
        state = use(rocket_board([HERE_COMES_TEAM_ROCKET, MISTYS_WISH, POTION]), HERE_COMES_TEAM_ROCKET)
        state = use(state, MISTYS_WISH)
        state = answer(state, (2,))
        state = answer(state, (1,))
        potion = card_of(state, POTION)
        old = state.players[0].prizes[2]
        state = answer(state, (potion,))
        self.assertEqual(state.players[0].prizes[2], potion)
        self.assertNotIn(potion, state.face_up_prizes)
        self.assertNotIn(old, state.face_up_prizes)
        self.assertEqual([f["position"] for f in observe(state, 1)["players"][0]["prizes"]["face_up"]], [0, 1, 3, 4, 5])
        swap = [e for e in state.log if e["kind"] == "swap_prize_with_hand"][-1]
        self.assertEqual(swap["face_up"], ("to_hand",))
        shown = [e for e in visible_log(state, 1) if e["kind"] == "swap_prize_with_hand"][-1]
        self.assertEqual((shown["to_hand"], "to_prize" in shown), (old, False))  # おもてだったカードは見え、サイドに置いた手札のカードは見えない
        audited(self, state)

    def test_swap_with_deck_top_turns_the_new_prize_face_down(self):
        """［わるふざけ］でおもてのサイドを山札の一番上と入れかえる: 山札にもどったカードはおもての記録から除き、サイドに来たカードは裏。"""
        me = {"active": mon(ROCKET_RATTATA), "bench": [], "hand": [HERE_COMES_TEAM_ROCKET], "prizes": 6, "deck": [POTION, RATTATA]}
        them = {"active": mon(HITMONCHAN, (F, F)), "bench": [RATTATA], "hand": [], "prizes": 6}
        state = use(build_test_state([me, them], turn_number=TURN, current_player=0), HERE_COMES_TEAM_ROCKET)
        old = state.players[0].prizes[1]
        top = state.players[0].deck[0]
        state = apply_kernel(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        state = answer(state, (1,))
        self.assertEqual((state.players[0].prizes[1], state.players[0].deck[0]), (top, old))
        self.assertNotIn(top, state.face_up_prizes)
        self.assertNotIn(old, state.face_up_prizes)
        self.assertEqual([e for e in state.log if e["kind"] == "swap_prize_with_deck_top"][-1]["face_up_card"], old)
        audited(self, state)

    def test_reuse_reveals_only_the_new_face_down_cards_and_format(self):
        state = use(rocket_board([HERE_COMES_TEAM_ROCKET, HERE_COMES_TEAM_ROCKET]), HERE_COMES_TEAM_ROCKET)
        again = use(state, HERE_COMES_TEAM_ROCKET)
        self.assertEqual([e["cards"] for e in again.log if e["kind"] == "prizes_revealed"][-2:], [(), ()])
        self.assertEqual(again.face_up_prizes, state.face_up_prizes)
        for version in FORMAT_VERSIONS[:-1]:
            with self.assertRaises(ValueError):
                state_to_dict(again, format_version=version)
        self.assertEqual(state_to_dict(again, format_version=21)["face_up_prizes"], list(again.face_up_prizes))
        restored = pickle.loads(pickle.dumps(again))
        self.assertEqual(state_to_dict(restored, format_version=21), state_to_dict(again, format_version=21))

    def test_borrowed_through_chaos_gym(self):
        """錯乱ジムで相手が借りて使っても同じ（「お互い」。使ったプレイヤーの番を書かない）。"""
        state = use(board([CHAOS_GYM, HERE_COMES_TEAM_ROCKET]), CHAOS_GYM)
        state = use(state, HERE_COMES_TEAM_ROCKET, coins=(T,))
        self.assertEqual((state.decision.kind, state.decision.player), (ACCEPT_REQUEST, 1))
        state = answer(state, (1,))
        self.assertEqual(len(state.face_up_prizes), len(state.players[0].prizes) + len(state.players[1].prizes))
        audited(self, state)


# ---------------------------------------------------------------- くすぐりマシーン


class TicklingMachineTest(unittest.TestCase):
    def test_heads_sets_the_hand_aside_until_the_end_of_the_opponents_next_turn(self):
        state = board([TICKLING_MACHINE], opponent_hand=[POTION, RATTATA, HITMONCHAN], opponent_deck=[RATTATA, POTION, POTION])
        hand = list(state.players[1].hand)
        after = use(state, TICKLING_MACHINE, coins=(H,))
        self.assertEqual(after.players[1].hand, [])
        group = after.set_aside[0]
        self.assertEqual((group.kind, group.owner, group.cards, group.visible_to, group.user, group.return_turn), (SET_ASIDE_HAND, 1, tuple(hand), (), 0, TURN + 1))
        for viewer in (0, 1, None):  # だれも中身を見られない（持ち主も）。枚数は見える
            shown = observe(after, viewer)["players"][1]
            self.assertEqual((shown["hand"]["count"], shown["set_aside"][0]["count"], shown["set_aside"][0]["cards"]), (0, 3, None))
            self.assertNotIn("cards", next(e for e in visible_log(after, viewer) if e["kind"] == "set_aside_hand"))
        audited(self, after)
        turn = apply_kernel(after, EndTurn(0))  # 相手の番: 引いたカードはふつうの手札
        self.assertEqual(len(turn.players[1].hand), 1)
        self.assertEqual(len(turn.set_aside), 1)
        audited(self, turn)
        back = apply_kernel(turn, EndTurn(1))  # 相手の番の終わりに、同じカードを置いた順に手札の最後にもどす
        self.assertEqual(back.set_aside, ())
        self.assertEqual(back.players[1].hand[-3:], hand)
        returned = next(e for e in back.log if e["kind"] == "set_aside_returned")
        self.assertEqual((returned["reason"], returned["cards"]), ("expired", tuple(hand)))
        self.assertEqual(visible_log(back, 0)[back.log.index(returned)].get("hidden"), {"cards": 3})
        audited(self, back)

    def test_set_aside_cards_are_not_hand_for_hand_effects(self):
        """置いたカードは手札とはみなされない: そのあとに手札を見る効果（スパイ作戦）は置いたカードを見ず、手札の枚数にも数えない。"""
        state = board([TICKLING_MACHINE, SECRET_MISSION], opponent_hand=[POTION, POTION])
        state = use(use(state, TICKLING_MACHINE, coins=(H,)), SECRET_MISSION)
        looked = [e for e in state.log if e["kind"] == "look_at_hand"][-1]
        self.assertEqual((looked["owner"], looked["cards"]), (1, ()))
        self.assertEqual(observe(state, 0)["players"][1]["hand"]["count"], 0)
        while state.decision is not None:
            state = answer(state, ())
        audited(self, state)

    def test_empty_hand_and_tails(self):
        state = board([TICKLING_MACHINE])
        empty = use(state, TICKLING_MACHINE, coins=(H,))
        self.assertEqual(empty.set_aside, ())
        self.assertEqual([e["count"] for e in empty.log if e["kind"] == "set_aside_hand"], [0])
        audited(self, empty)
        tails = use(board([TICKLING_MACHINE], opponent_hand=[POTION]), TICKLING_MACHINE, coins=(T,))
        self.assertEqual(tails.set_aside, ())
        self.assertIn(card_of(board([TICKLING_MACHINE]), TICKLING_MACHINE), tails.players[0].discard)
        self.assertEqual((tails.current_player, tails.phase), (1, Phase.MAIN))  # あなたの番は終わりになる
        self.assertIn("trainer_turn_end", [e["kind"] for e in tails.log])
        audited(self, tails)

    def test_two_uses_keep_their_own_groups(self):
        """2 回使うと、それぞれのときの手札を別のまとまりとして置く（出どころ・もどす番をそれぞれ持つ）。マチスの交渉で相手がサイドを手札に加えたあとに 2 回目を使う。"""
        state = board([TICKLING_MACHINE, TICKLING_MACHINE, LT_SURGES_TREATY], opponent_hand=[POTION], opponent_deck=[RATTATA, RATTATA])
        first, second = [u for u in state.players[0].hand if state.cards[u].card_id == TICKLING_MACHINE]
        state = apply_kernel(with_coin_results(state, H),
                             PlayTrainer(0, first))
        state = use(state, LT_SURGES_TREATY)
        state = answer(answer(answer(state, (1,)), (0,)), (0,))  # 相手がオーケー → お互いにサイドを 1 枚取る（相手の手札に 1 枚）
        state = apply_kernel(with_coin_results(state, H), PlayTrainer(0, second))
        self.assertEqual([(g.trainer_card, len(g.cards), g.return_turn) for g in state.set_aside], [(first, 1, TURN + 1), (second, 1, TURN + 1)])
        audited(self, state)
        back = apply_kernel(apply_kernel(state, EndTurn(0)), EndTurn(1))
        self.assertEqual(back.set_aside, ())
        self.assertEqual([e["trainer_card"] for e in back.log if e["kind"] == "set_aside_returned"], [first, second])
        audited(self, back)

    def test_game_end_before_the_return_keeps_the_cards_aside(self):
        state = board([TICKLING_MACHINE], opponent_hand=[POTION, POTION], opponent_deck=[])
        state = apply_kernel(use(state, TICKLING_MACHINE, coins=(H,)), EndTurn(0))  # 相手は番の最初に引けずに負け
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertEqual(len(state.set_aside), 1)
        audited(self, state)

    def test_borrowed_is_ch1_and_psychic_control_tails_cleans_up(self):
        state = use(board([CHAOS_GYM, TICKLING_MACHINE]), CHAOS_GYM)
        state = use(state, TICKLING_MACHINE, coins=(T,))
        assert_answer_stops(self, state, (1,), "UNRESOLVED_CHAOS_GYM_BORROWED_TURN")
        me = {"active": mon(HITMONCHAN, (F,)), "bench": [RATTATA], "hand": [SABRINAS_PSYCHIC_CONTROL]}
        them = {"active": mon(HITMONCHAN, (F, F)), "bench": [RATTATA], "hand": [POTION], "discard": [TICKLING_MACHINE]}
        pc = build_test_state([me, them], turn_number=TURN, current_player=0)
        machine = card_of(pc, TICKLING_MACHINE, zone="discard", player=1)
        pc = use(pc, SABRINAS_PSYCHIC_CONTROL, coins=(H, T))
        pc = answer(pc, (machine,))
        self.assertEqual((pc.trainer_in_use, pc.trainer_stack, pc.current_player), (None, (), 1))  # 内側・外側のカードをトラッシュしてから番を終えた
        self.assertIn(machine, pc.players[1].discard)
        self.assertIn(card_of(build_test_state([me, them], turn_number=TURN, current_player=0), SABRINAS_PSYCHIC_CONTROL), pc.players[0].discard)
        audited(self, pc)

    def test_rocket_grunt_through_psychic_control_ends_the_users_turn(self):
        """v0.63 で直した v0.62 までの不具合: サイキックコントロールで相手のトラッシュから使った「番を終える」トレーナー（ロケット団員の「うら」）は、番の終わりに
        持ち主（相手）を渡していて NOT_YOUR_TURN になっていた。番を終えるのは使ったプレイヤー（``TrainerInUse.using_player``）。"""
        me = {"active": mon(HITMONCHAN, (F,)), "bench": [RATTATA], "hand": [SABRINAS_PSYCHIC_CONTROL]}
        them = {"active": mon(HITMONCHAN, (F, F)), "bench": [RATTATA], "hand": [], "discard": [ROCKET_GRUNT]}
        state = build_test_state([me, them], turn_number=TURN, current_player=0)
        grunt = card_of(state, ROCKET_GRUNT, zone="discard", player=1)
        state = answer(use(state, SABRINAS_PSYCHIC_CONTROL, coins=(H, T, T)), (grunt,))
        self.assertEqual((state.current_player, state.trainer_in_use, state.trainer_stack), (1, None, ()))
        self.assertEqual([e["player"] for e in state.log if e["kind"] == "trainer_turn_end"], [0])
        self.assertIn(grunt, state.players[1].discard)
        audited(self, state)

    def test_hidden_cards_are_indistinguishable(self):
        """置いたカードの中身だけが違う 2 つの盤面は、どのプレイヤー・観戦者の観測とログの写しでも区別できない（uid の付き方を除く）。"""
        a = use(board([TICKLING_MACHINE], opponent_hand=[POTION, RATTATA]), TICKLING_MACHINE, coins=(H,))
        b = use(board([TICKLING_MACHINE], opponent_hand=[HITMONCHAN, POTION]), TICKLING_MACHINE, coins=(H,))
        for (view_a, log_a), (view_b, log_b) in zip(all_views(a), all_views(b)):
            self.assertEqual(without_uids(view_a["players"][1]), without_uids(view_b["players"][1]))
            self.assertEqual(without_uids([e for e in log_a if e["kind"] == "set_aside_hand"]), without_uids([e for e in log_b if e["kind"] == "set_aside_hand"]))


# ---------------------------------------------------------------- たたきつけろ!挑戦状


def challenge_board(*, deck=(RATTATA, HITMONCHAN, CHARMELEON, POTION, F), opponent_deck=(HITMONCHAN, MYSTERIOUS_FOSSIL, F, RATTATA), bench=(RATTATA,),
                    opponent_bench=(RATTATA,), hand=(), seed=0):
    me = {"active": mon(HITMONCHAN, (F,)), "bench": list(bench), "hand": [CHALLENGE, *hand], "deck": list(deck)}
    them = {"active": mon(HITMONCHAN, (F, F)), "bench": list(opponent_bench), "hand": [], "deck": list(opponent_deck)}
    return build_test_state([me, them], turn_number=TURN, current_player=0, seed=seed)


class ChallengeTest(unittest.TestCase):
    def test_declined_draws_two_and_short_deck(self):
        state = use(challenge_board(), CHALLENGE)
        self.assertEqual((state.decision.kind, state.decision.player), (ACCEPT_REQUEST, 1))
        declined = answer(state, ())
        self.assertEqual(len(declined.players[0].hand), 2)
        audited(self, declined)
        short = answer(use(challenge_board(deck=(RATTATA,)), CHALLENGE), ())
        self.assertEqual(len(short.players[0].hand), 1)  # 引けるだけ（p.312）
        audited(self, short)

    def test_accepted_both_place_face_down_then_reveal_and_shuffle(self):
        state = answer(use(challenge_board(), CHALLENGE), (1,))
        d = state.decision
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices), (CHALLENGE_BENCH, 0, 0, 2))
        names = sorted(state.card_def(u).name_ja for u in d.options)
        self.assertEqual(names, ["エビワラー", "コラッタ"])  # 進化カード・トレーナー・エネルギーは入らない
        self.assertEqual(observe(state, 1)["decision"], {"kind": CHALLENGE_BENCH, "player": 0})  # 選ぶ数・選べるものの数も見せない
        mine = d.options[0]
        state = answer(state, (mine,))
        group = state.set_aside[0]
        self.assertEqual((group.kind, group.owner, group.cards, group.visible_to), (SET_ASIDE_FACE_DOWN_BENCH, 0, (mine,), (0,)))
        self.assertIsNone(observe(state, 1)["players"][0]["set_aside"][0]["cards"])  # あとで選ぶ相手は、先のカードを見ない
        self.assertEqual(observe(state, 0)["players"][0]["set_aside"][0]["cards"][0]["card"], mine)
        self.assertEqual(len(state.players[0].bench), 1)  # うらのあいだは場のポケモンではない
        audited(self, state)
        self.assertEqual(state.decision.player, 1)
        self.assertEqual([state.card_def(u).name_ja for u in state.decision.options], ["エビワラー", "コラッタ"])  # なにかの化石は山札ではトレーナーカード
        theirs = state.decision.options[1]
        done = answer(state, (theirs,))
        self.assertEqual(kinds(done), ["play_trainer", "request_answered", "face_down_bench", "face_down_bench", "face_down_revealed", "face_down_revealed",
                                        "shuffle", "shuffle", "discard_trainer"])
        self.assertEqual(done.set_aside, ())
        placed = [done.players[0].bench[-1], done.players[1].bench[-1]]
        self.assertEqual([p.card for p in placed], [mine, theirs])
        self.assertTrue(all(p.played_turn == TURN for p in placed))  # 今の番に場に出た（この番には進化できない）
        audited(self, done)

    def test_zero_choice_is_hc5_and_illegal_answers_keep_the_state(self):
        state = answer(use(challenge_board(), CHALLENGE), (1,))
        assert_answer_stops(self, state, (), HC5)
        assert_answer_stops(self, state, (state.players[0].deck[0] if state.players[0].deck[0] not in state.decision.options else -1,), "INVALID_CHOICE",
                            IllegalActionError)
        assert_answer_stops(self, state, (state.decision.options[0],), "NOT_YOUR_DECISION", IllegalActionError, player=1)

    def test_full_benches_and_no_targets_place_nothing(self):
        full = [RATTATA] * 5
        state = answer(use(challenge_board(bench=full, opponent_bench=full), CHALLENGE), (1,))
        self.assertIsNone(state.decision)
        self.assertEqual([e["reason"] for e in state.log if e["kind"] == "challenge_bench_skipped"], ["bench_full", "bench_full"])
        self.assertEqual([e["player"] for e in state.log if e["kind"] == "shuffle"][-2:], [0, 1])
        self.assertEqual(visible_log(state, 1)[[e["kind"] for e in state.log].index("challenge_bench_skipped")].get("hidden"), {"reason": None})
        audited(self, state)
        none = answer(use(challenge_board(deck=(POTION, CHARMELEON)), CHALLENGE), (1,))
        self.assertEqual(none.decision.player, 1)  # 使ったプレイヤーは選べるカードがないので次へ
        audited(self, none)

    def test_narrow_gym_limits_the_space(self):
        state = use(challenge_board(hand=(NARROW_GYM,), bench=(RATTATA, RATTATA)), NARROW_GYM)
        state = answer(use(state, CHALLENGE), (1,))
        self.assertEqual(state.decision.max_choices, 2)  # 4 匹まで
        audited(self, state)

    def test_goop_gas_makes_power_pokemon_stop(self):
        state = use(challenge_board(hand=(GOOP_GAS_ATTACK,), deck=(MR_MIME, RATTATA)), GOOP_GAS_ATTACK)
        state = answer(use(state, CHALLENGE), (1,))
        mime = next(u for u in state.decision.options if state.cards[u].card_id == MR_MIME)
        assert_answer_stops(self, state, (mime,), "UNRESOLVED_GOOP_GAS_NEW_POKEMON")

    def test_save_and_restore_mid_way(self):
        state = answer(use(challenge_board(), CHALLENGE), (1,))
        state = answer(state, (state.decision.options[0],))
        restored = pickle.loads(pickle.dumps(state))
        self.assertEqual(state_to_dict(restored, format_version=21), state_to_dict(state, format_version=21))
        for version in FORMAT_VERSIONS[:-1]:
            with self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        a = answer(state, (state.decision.options[0],))
        b = answer(restored, (restored.decision.options[0],))
        self.assertEqual(state_to_dict(a, format_version=21), state_to_dict(b, format_version=21))

    def test_face_down_cards_are_indistinguishable_for_the_opponent(self):
        a = answer(use(challenge_board(deck=(RATTATA, HITMONCHAN)), CHALLENGE), (1,))
        b = answer(use(challenge_board(deck=(HITMONCHAN, RATTATA)), CHALLENGE), (1,))
        a = answer(a, (next(u for u in a.decision.options if a.cards[u].card_id == RATTATA),))
        b = answer(b, (next(u for u in b.decision.options if b.cards[u].card_id == HITMONCHAN),))
        self.assertEqual(without_uids(observe(a, 1)["players"][0]), without_uids(observe(b, 1)["players"][0]))
        self.assertEqual(without_uids(visible_log(a, 1)), without_uids(visible_log(b, 1)))

    def test_borrowed_through_chaos_gym(self):
        state = use(challenge_board(hand=(CHAOS_GYM,)), CHAOS_GYM)
        state = use(state, CHALLENGE, coins=(T,))
        state = answer(state, (1,))  # 相手が借りて使う
        self.assertEqual((state.decision.kind, state.decision.player), (ACCEPT_REQUEST, 0))  # 借りたプレイヤーの相手（番のプレイヤー）が答える
        declined = answer(state, ())
        self.assertEqual(len(declined.players[1].hand), 2)  # 借りたプレイヤーが引く
        audited(self, declined)


# ---------------------------------------------------------------- カツラのクイズ その3


def quiz_board(hand=(HITMONCHAN,), *, deck=(POTION, POTION, POTION, POTION), opponent_deck=(RATTATA, RATTATA, RATTATA, RATTATA)):
    me = {"active": mon(HITMONCHAN, (F,)), "bench": [RATTATA], "hand": [BLAINES_QUIZ_3, *hand], "deck": list(deck)}
    them = {"active": mon(HITMONCHAN, (F, F)), "bench": [RATTATA], "hand": [], "deck": list(opponent_deck)}
    return build_test_state([me, them], turn_number=TURN, current_player=0)


def play_quiz(state, card_id, attack=0, answer_name=None):
    state = use(state, BLAINES_QUIZ_3)
    state = answer(state, (card_of(state, card_id),))
    state = answer(state, (attack,))
    if answer_name is None:
        return state
    return answer(state, (state.decision.context_value("names").index(answer_name),))


class BlainesQuizTest(unittest.TestCase):
    def test_correct_and_wrong_answers(self):
        right = play_quiz(quiz_board(), HITMONCHAN, 0, "エビワラー")
        self.assertEqual((len(right.players[1].hand), len(right.players[0].hand)), (3, 1))  # 正解なら相手が 3 枚。置いたカードは手札にもどる
        self.assertEqual(kinds(right), ["play_trainer", "quiz_card_set", "quiz_hint", "quiz_answer", "quiz_reveal", "draw", "set_aside_returned", "discard_trainer"])
        audited(self, right)
        wrong = play_quiz(quiz_board(), HITMONCHAN, 0, "コラッタ")
        self.assertEqual((len(wrong.players[1].hand), len(wrong.players[0].hand)), (0, 4))
        self.assertFalse(next(e for e in wrong.log if e["kind"] == "quiz_reveal")["correct"])
        audited(self, wrong)

    def test_hint_is_the_attack_name_only_and_fixed(self):
        state = play_quiz(quiz_board(hand=(CHARIZARD,)), CHARIZARD, 0)
        d = state.decision
        self.assertEqual((d.kind, d.player), (QUIZ_ANSWER, 1))
        hint = next(e for e in state.log if e["kind"] == "quiz_hint")
        self.assertEqual(set(hint), {"kind", "turn", "player", "attack_name", "trainer_card"})  # カードの id・収録・HP は伝えない
        self.assertEqual(observe(state, 1)["decision"]["hint"], hint["attack_name"])
        self.assertIsNone(observe(state, 1)["players"][0]["set_aside"][0]["cards"])
        self.assertEqual(state.set_aside[0].kind, SET_ASIDE_QUIZ)
        assert_answer_stops(self, state, (len(d.options),), "INVALID_CHOICE", IllegalActionError)  # 候補にない答えは不正な操作（正解でない答えとは別）
        audited(self, state)

    def test_candidates_do_not_depend_on_the_secret_card_or_the_hand(self):
        a = play_quiz(quiz_board(hand=(HITMONCHAN,)), HITMONCHAN)
        b = play_quiz(quiz_board(hand=(CHARMELEON, VULPIX)), VULPIX)
        self.assertEqual(a.decision.context_value("names"), b.decision.context_value("names"))
        self.assertIn("リザードン", a.decision.context_value("names"))  # 手札にない名前も答えられる

    def test_same_name_other_edition_is_right_and_adjectives_differ(self):
        right = play_quiz(quiz_board(hand=(JUNGLE_PIKACHU,)), JUNGLE_PIKACHU, 0, "ピカチュウ")
        self.assertTrue(next(e for e in right.log if e["kind"] == "quiz_reveal")["correct"])
        self.assertEqual(load_card_pool().get(PIKACHU).name_ja, "ピカチュウ")
        wrong = play_quiz(quiz_board(hand=(DARK_ARBOK,)), DARK_ARBOK, 0, load_card_pool().get(ARBOK).name_ja)
        self.assertFalse(next(e for e in wrong.log if e["kind"] == "quiz_reveal")["correct"])  # 「わるい」の付いた名前は別の名前

    def test_basic_stage1_stage2_multiple_attacks_and_no_attacks(self):
        state = use(quiz_board(hand=(HITMONCHAN, CHARMELEON, CHARIZARD, DITTO)), BLAINES_QUIZ_3)
        options = {state.cards[u].card_id for u in state.decision.options}
        self.assertEqual(options, {HITMONCHAN, CHARMELEON, CHARIZARD})  # たね・1 進化・2 進化。ワザを持たないメタモンは選べない
        self.assertEqual(observe(state, 1)["decision"], {"kind": QUIZ_CARD, "player": 0})
        two = answer(state, (card_of(state, CHARMELEON),))
        self.assertEqual(two.decision.options, (0, 1))  # ワザが 2 つ
        self.assertEqual(observe(two, 1)["decision"], {"kind": QUIZ_ATTACK, "player": 0})  # ワザの数を見せない
        self.assertEqual([o["attack_name"] for o in observe(two, 0)["decision"]["options"]], ["きりさく", "かえんほうしゃ"])
        one = answer(state, (card_of(state, CHARIZARD),))
        self.assertEqual(one.decision.options, (0,))
        audited(self, two)
        audited(self, state)

    def test_qz1(self):
        assert_use_stops(self, quiz_board(hand=(DITTO, POTION)), BLAINES_QUIZ_3, QZ1)
        assert_use_stops(self, quiz_board(hand=(MYSTERIOUS_FOSSIL,)), BLAINES_QUIZ_3, QZ1)  # なにかの化石は手札ではトレーナーカード

    def test_short_deck_draws_what_is_left(self):
        state = play_quiz(quiz_board(deck=(POTION,)), HITMONCHAN, 0, "コラッタ")
        self.assertEqual(len(state.players[0].hand), 2)
        audited(self, state)

    def test_secret_card_is_indistinguishable_until_revealed(self):
        """ワザの名前が同じ 2 枚（ロコン・フーディンの「あやしいひかり」。たねポケモンと 2 進化）を置いた盤面は、答えの前の相手・観戦者の観測とログで区別できない。"""
        a = play_quiz(quiz_board(hand=(VULPIX,)), VULPIX)
        b = play_quiz(quiz_board(hand=(ALAKAZAM,)), ALAKAZAM)
        for viewer in (1, None):
            self.assertEqual(without_uids(observe(a, viewer)), without_uids(observe(b, viewer)))
            self.assertEqual(without_uids(visible_log(a, viewer)), without_uids(visible_log(b, viewer)))

    def test_save_and_restore_keeps_the_card_and_hint(self):
        state = play_quiz(quiz_board(), HITMONCHAN, 0)
        restored = pickle.loads(pickle.dumps(state))
        self.assertEqual(state_to_dict(restored, format_version=21), state_to_dict(state, format_version=21))
        self.assertEqual(restored.decision.context_value("hint"), state.decision.context_value("hint"))
        self.assertEqual(check_invariants(restored), [])


class GamesTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.63 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.63 の 3 組を 2 seed ずつ（席を入れかえて 12 局）。どれも監査の失敗（やり直し・不変条件・ログ・書き出し・観測）・想定外の拒否・内部エラー・手数の上限がなく、
        4 枚の処理（サイドをおもてにしたあとのサイドを取る・置いた手札が期限にもどる・「うら」で番が終わる・挑戦状を受ける・受けない・うらのたねポケモンを出す・
        クイズの正解・不正解）が起こる（勝敗は判断に使わない）。"""
        from tools import existing_effect_games as games

        results = games.run(range(2), pairings=games.PAIRINGS_V0_63)
        totals = {}
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                if game["outcome"] == "halted":
                    self.assertEqual(game["halt_code"], "UNRESOLVED_MULLIGAN_COMPENSATION")
                for key, count in game.get("v063", {}).items():
                    totals[key] = totals.get(key, 0) + count
        for key in ("prizes_revealed", "face_up_prize_taken", "tickle_heads", "set_aside_returned_expired", "tickle_tails_turn_end",
                    "challenge_accepted", "challenge_refused", "face_down_revealed", "quiz_correct", "quiz_wrong", "set_aside_returned_quiz"):
            self.assertGreater(totals.get(key, 0), 0, key)


if __name__ == "__main__":
    unittest.main()

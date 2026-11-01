"""v0.130: とりかえっこプリーズ（PR1-027）と、利用者が指定した交換したカードの所有者（docs/trade-please-ownership-v0.130.md）。

- 登録・記録（処理に使う文面は最新の説明。所有者の規則は文面の区分と別の利用者の指定。UQ-SWAP-PLEASE-OWNERSHIP は解決済みにしない）・カード id の分岐がない
- 使うための条件（このカードしか手札にない・相手の手札がない）は、状態を変えずに拒否する
- 説明の順（見る → 選ぶ → 見せて選ばせる → たずねる → 交換か引く）と、オーケー・オーケーでないときの手札・引く枚数・所有者。山札が足りないとき
- 不正な答えは状態・乱数・ログを変えずに拒否する。決定をまたぐ保存と復元
- 交換したカードの再交換・使う・トラッシュ・山札・サイド・場（進化の重なり・つけたカード・きぜつ・退化・手札にもどす）。あとから重ねたカードの所有者は変えない
- 見える範囲（両プレイヤー・観戦者の観測とログ。交換と関係のない手札の中身・uid・出所を漏らさない）
- 錯乱ジムで相手がかわりに使うことを選ぶと止める（UQ-CHAOS-GYM-BORROWED-TURN）・おもての山札
- ログの監査が、所有者・行き先・交換の記録をわざと誤らせた状態を見つける。正式な開始からの対戦
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import pickle
import re
import unittest

from kyuura_engine import (
    AttachEnergy,
    EndTurn,
    EvolvePokemon,
    IllegalActionError,
    PlayBasicToBench,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    check_invariants,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, read_extract
from kyuura_engine.decisions import ACCEPT_REQUEST, SELECT_EXCHANGE_CARD, TAKE_PRIZE
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import Phase, freeze_mapping
from kyuura_engine.zones import deck_top_to_prizes
from tests.helpers import (
    BILL,
    CHAOS_GYM,
    DEVOLUTION_SPRAY,
    FIGHTING,
    HITMONCHAN,
    POTION,
    RATICATE,
    RATTATA,
    SCOOP_UP,
    SWITCH,
    H,
    T,
    apply_kernel,
    build_test_state,
)
from tests.log_audit import log_problems, observation_problems, v130_problems
from tests.release_catalog import cards_after
from tests.test_instant_trainers_v0_55 import (
    answer,
    assert_stops,
    audited,
    card_of,
    kinds,
    mon,
    snapshot,
    use,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "trade-please-ownership-v0.130.md"
F = FIGHTING
SWAP = "PR1-027"
IMPOSTOR_OAK = "PMCG1-089"  # にせオーキドはかせ（相手の手札を山札にもどして切り、7 枚引かせる）
CH1 = "UNRESOLVED_CHAOS_GYM_BORROWED_TURN"
FU3 = "UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE"


def swap_board(hand=(RATTATA, POTION), *, opponent_hand=(RATTATA, POTION, F), deck=(F,) * 6, opponent_deck=(F,) * 6, active=None, opponent_active=None,
               bench=(RATTATA,), opponent_bench=(RATTATA,), prizes=6):
    me = {"active": active or mon(HITMONCHAN, (F,)), "bench": list(bench), "hand": [SWAP, *hand], "deck": list(deck), "prizes": prizes}
    them = {"active": opponent_active or mon(HITMONCHAN, (F,)), "bench": list(opponent_bench), "hand": list(opponent_hand), "deck": list(opponent_deck)}
    return build_test_state([me, them], turn_number=7, current_player=0)


def swap(state, take, give, accept, player=0):
    """プレイヤー ``player`` がとりかえっこプリーズを使い、相手の手札の ``take``（カードの id か uid）を選び、相手が ``give`` を選び、相手が ``accept`` で答えた状態。"""
    state = use(state, SWAP, player=player)
    take_uid = take if isinstance(take, int) else card_of(state, take, player=1 - player)
    state = answer(state, (take_uid,))
    give_uid = give if isinstance(give, int) else card_of(state, give, player=player)
    state = answer(state, (give_uid,))
    return answer(state, (1,) if accept else ())


def owners(state, uid):
    card = state.cards[uid]
    return card.owner, card.origin


class RegistrationTest(unittest.TestCase):
    def test_entry_texts_and_record(self):
        entry = E.DEFAULT_EFFECTS.trainer_entry(SWAP)
        definition = load_card_pool().get(SWAP)
        self.assertIsInstance(entry.effect, E.SwapPleaseTrainer)
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                         ("とりかえっこプリーズ", definition.trainer_text_ja, E.SWAP_PLEASE_LATEST_TEXT, "LD-PR1-027-TRAINER"))
        self.assertEqual(definition.name_ja, "とりかえっこプリーズ")  # 印刷の「！」は kyuura の報告事項。写し・登録では加えていない
        self.assertEqual(entry.effect.check(definition), [])
        record = E.USER_SPECIFIED_RULES["PR1-027/trainer"]
        self.assertEqual((record.rule, record.printed_text, record.play_text, record.kyuura_issue, record.specified_by),
                         (E.USER_SWAP_OWNERSHIP, definition.trainer_text_ja, entry.play_text_ja, "UQ-SWAP-PLEASE-OWNERSHIP", "user"))
        self.assertEqual(entry.effect.ownership_rule, record.rule)
        # 利用者の指定の 3 つの記録は別の区分（重ならない）
        # v0.132: 同じ記録に［ちえくらべ］の使うかの選択と投げる時点（別の種類）が加わった。所有者の規則はこの 1 つだけ
        self.assertEqual({key for key, r in E.USER_SPECIFIED_RULES.items() if r.rule == E.USER_SWAP_OWNERSHIP}, {"PR1-027/trainer"})
        self.assertFalse(set(E.USER_SPECIFIED_RULES) & (set(E.USER_SIMPLIFICATIONS) | set(E.USER_SPECIFIED_REFERENCES)))
        self.assertIn(f"「{record.instruction}」", DOC.read_text(encoding="utf-8"))
        # 記録の規則を持たない登録は受け付けない（知らない文面・カードに当てはめない）
        self.assertTrue(E.SwapPleaseTrainer(E.SWAP_PLEASE_LATEST_TEXT, ownership_rule="OTHER").check(definition))

    def test_pool_counts_and_no_card_branch(self):
        extract = read_extract()
        self.assertEqual(extract["pool_v0_130"], [SWAP])
        self.assertEqual(cards_after(extract, "0.129") - cards_after(extract, "0.130"), {SWAP})  # v0.131: 後の版のカード（ナッシー[Exeggutor]）を除く
        pool = load_card_pool()
        self.assertIn(SWAP, pool.playable_ids)
        self.assertEqual(len(pool.playable_ids - cards_after(extract, "0.130")), 1370)
        for path in [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]:
            self.assertNotIn(SWAP, path.read_text(encoding="utf-8"), path.name)

    def test_adoption_and_research_records(self):
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"][SWAP]
        self.assertEqual(sources["play_text"], {"trainer": "LD-PR1-027-TRAINER"})  # 文面の採用は最新の説明（利用者の指定ではない）
        self.assertEqual(sources["user_specified_rule"], {"trainer": E.USER_SPECIFIED_RULE_SOURCE})
        self.assertIn("UQ-SWAP-PLEASE-OWNERSHIP", sources["kyuura_records"])
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        section = links["latest_descriptions"]
        self.assertEqual(section["registered_trainers"][SWAP], "LD-PR1-027-TRAINER")
        self.assertEqual(section["trainer_records_not_registered"], {})
        self.assertEqual(section["user_specified_rules"]["PR1-027/trainer"], E.USER_SPECIFIED_RULE_SOURCE)  # v0.132: ［ちえくらべ］の規則も同じ区分にある
        self.assertNotIn("PR1-027/trainer", section.get("user_specified_references", {}))
        cases = {(c["kyuura_issue"], c["card_id"], c["target"]): c["engine"] for c in links["kyuura_cases_without_engine_ruling"]["cases"]}
        self.assertEqual(cases[("UQ-CHAOS-GYM-BORROWED-TURN", SWAP, "trainer")], {"stop_codes": [CH1]})
        self.assertEqual(cases[("UQ-SWAP-PLEASE-OWNERSHIP", SWAP, "trainer")], {"user_specified_rule": "PR1-027/trainer"})
        self.assertEqual(cases[("UQ-SWAP-PLEASE-OWNERSHIP", CHAOS_GYM, "trainer")], {"user_specified_rule": "PR1-027/trainer"})
        # v0.132 で［ちえくらべ］を登録した: 交換で受け取ったカードの「相手の山札」は、この所有者の規則の山札（docs/slowking-mind-games-v0.132.md 7 章）
        self.assertEqual(cases[("UQ-SWAP-PLEASE-OWNERSHIP", "neo1-049", "power/0")], {"user_specified_rule": "PR1-027/trainer"})


class UseConditionTest(unittest.TestCase):
    def test_only_this_card_in_hand_is_rejected_without_change(self):
        state = swap_board(hand=())
        assert_stops(self, state, PlayTrainer(0, card_of(state, SWAP)), "NO_OTHER_CARDS_IN_HAND", IllegalActionError)

    def test_opponent_without_hand_is_rejected_without_change(self):
        state = swap_board(opponent_hand=())
        assert_stops(self, state, PlayTrainer(0, card_of(state, SWAP)), "OPPONENT_HAND_EMPTY", IllegalActionError)

    def test_one_card_each_is_enough(self):
        state = swap(swap_board(hand=(POTION,), opponent_hand=(RATTATA,)), RATTATA, POTION, True)
        self.assertEqual([state.cards[u].card_id for u in state.players[0].hand], [RATTATA])
        self.assertEqual([state.cards[u].card_id for u in state.players[1].hand], [POTION])
        audited(self, state)


class FlowTest(unittest.TestCase):
    def test_order_of_steps_and_deciders(self):
        state = use(swap_board(), SWAP)
        d = state.decision
        self.assertEqual((d.kind, d.player, d.options, d.context_value("stage")), (SELECT_EXCHANGE_CARD, 0, tuple(state.players[1].hand), "take"))
        self.assertEqual(kinds(state), ["play_trainer", "look_at_hand"])
        taken = card_of(state, POTION, player=1)
        state = answer(state, (taken,))
        d = state.decision
        self.assertEqual((d.kind, d.player, d.options, d.context_value("stage")), (SELECT_EXCHANGE_CARD, 1, tuple(state.players[0].hand), "give"))
        self.assertEqual(kinds(state), ["play_trainer", "look_at_hand", "exchange_selected", "look_at_hand"])
        given = card_of(state, RATTATA)
        state = answer(state, (given,))
        d = state.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (ACCEPT_REQUEST, 1, (1,), 0, 1))
        self.assertEqual(set(dict(d.context)), {"use", "stage", "taken", "given"})
        for state_ in (state,):
            audited(self, state_)

    def test_accept_exchanges_the_two_cards_and_their_owners(self):
        state = swap_board()
        swap_card = card_of(state, SWAP)
        taken, given = card_of(state, POTION, player=1), card_of(state, RATTATA)
        before_hands = (list(state.players[0].hand), list(state.players[1].hand))
        done = swap(state, taken, given, True)
        self.assertEqual(done.players[0].hand, [u for u in before_hands[0] if u not in (swap_card, given)] + [taken])
        self.assertEqual(done.players[1].hand, [u for u in before_hands[1] if u != taken] + [given])
        self.assertEqual((owners(done, taken), owners(done, given)), ((0, 1), (1, 0)))
        self.assertEqual(owners(done, swap_card), (0, None))  # とりかえっこプリーズ自身の所有者は変えない
        self.assertIn(swap_card, done.players[0].discard)
        self.assertEqual(len(done.players[0].deck), 6)  # オーケーなら引かない
        self.assertEqual(kinds(done), ["play_trainer", "look_at_hand", "exchange_selected", "look_at_hand", "exchange_selected", "request_answered",
                                       "cards_exchanged", "discard_trainer"])
        self.assertEqual(len(done.ownership_changes), 2)
        self.assertEqual((done.phase, done.current_player, done.trainer_in_use), (Phase.MAIN, 0, None))
        audited(self, done)
        self.assertEqual(v130_problems(done), [])

    def test_decline_draws_two_and_keeps_owners(self):
        state = swap_board()
        taken, given = card_of(state, POTION, player=1), card_of(state, RATTATA)
        done = swap(state, taken, given, False)
        self.assertEqual(done.ownership_changes, ())
        self.assertEqual((owners(done, taken), owners(done, given)), ((1, None), (0, None)))
        self.assertIn(given, done.players[0].hand)
        self.assertIn(taken, done.players[1].hand)
        draws = [e for e in done.log if e["kind"] == "draw"]
        self.assertEqual([(e["player"], len(e["cards"])) for e in draws], [(0, 2)])
        self.assertEqual(len(done.players[0].hand), 1 + 1 + 2)  # 選んだが渡さなかったカード・残りのカード・引いた 2 枚
        self.assertFalse(any(e["kind"] == "cards_exchanged" for e in done.log))
        audited(self, done)
        self.assertEqual(v130_problems(done), [])

    def test_decline_with_a_short_deck_draws_what_is_left(self):
        for size in (1, 0):
            with self.subTest(deck=size):
                done = swap(swap_board(deck=(F,) * size), POTION, RATTATA, False)
                self.assertEqual(sum(len(e["cards"]) for e in done.log if e["kind"] == "draw"), size)
                self.assertEqual(done.phase, Phase.MAIN)  # 山札がなくても負けではない（効果で引く。p.312）
                audited(self, done)


class InvalidAnswerTest(unittest.TestCase):
    def assert_rejected(self, state, player, choices):
        before = snapshot(state)
        with self.assertRaises(IllegalActionError):
            apply_kernel(state, ResolveDecision(player, state.decision.id, tuple(choices)))
        self.assertEqual(snapshot(state), before)

    def test_each_stage_rejects_bad_answers_without_change(self):
        state = use(swap_board(), SWAP)
        own = card_of(state, RATTATA)
        self.assert_rejected(state, 1, (state.decision.options[0],))  # 決めるのは使ったプレイヤー
        self.assert_rejected(state, 0, (own,))  # 自分の手札のカード
        self.assert_rejected(state, 0, ())
        self.assert_rejected(state, 0, tuple(state.decision.options[:2]))
        state = answer(state, (card_of(state, POTION, player=1),))
        self.assert_rejected(state, 0, (state.decision.options[0],))  # 2 つ目を決めるのは相手
        self.assert_rejected(state, 1, (card_of(state, RATTATA, player=1),))  # 相手自身の手札のカード
        self.assert_rejected(state, 1, (10_000,))  # どこにもないカード
        state = answer(state, (own,))
        self.assert_rejected(state, 0, (1,))  # 答えるのは相手
        self.assert_rejected(state, 1, (2,))
        self.assert_rejected(state, 1, (1, 1))


class PersistenceTest(unittest.TestCase):
    def test_save_and_restore_at_each_decision(self):
        stages = []
        state = use(swap_board(), SWAP)
        stages.append(state)
        state = answer(state, (card_of(state, POTION, player=1),))
        stages.append(state)
        state = answer(state, (card_of(state, RATTATA),))
        stages.append(state)
        expected = {True: state_to_dict(answer(state, (1,)), 33), False: state_to_dict(answer(state, ()), 33)}
        for stage in stages:
            for restored in (pickle.loads(pickle.dumps(stage)), copy.deepcopy(stage), stage.clone()):
                self.assertEqual(state_to_dict(restored, 33), state_to_dict(stage, 33))
                for version in FORMAT_VERSIONS[2:]:
                    state_to_dict(restored, version)  # 交換の前は所有者が変わっていないので形式 3〜32 でも書ける
                current = restored
                while current.decision.kind != ACCEPT_REQUEST:
                    pick = card_of(current, POTION, player=1) if current.decision.context_value("stage") == "take" else card_of(current, RATTATA)
                    current = answer(current, (pick,))
                for accept in (True, False):
                    self.assertEqual(state_to_dict(answer(current, (1,) if accept else ()), 33), expected[accept])
        accepted = answer(state, (1,))
        for version in FORMAT_VERSIONS[:-1]:
            with self.assertRaises(ValueError):
                state_to_dict(accepted, version)
        self.assertEqual(len(state_to_dict(accepted, 33)["ownership_changes"]), 2)
        self.assertEqual(state_to_dict(accepted, 33)["user_ownership_rules"], ["PR1-027/trainer"])


class ReExchangeTest(unittest.TestCase):
    def test_a_received_card_is_exchanged_again_under_the_same_rule(self):
        state = swap_board(hand=(RATTATA, POTION, SWAP))
        taken, given = card_of(state, POTION, player=1), card_of(state, RATTATA)
        state = swap(state, taken, given, True)
        # 2 回目: 使ったプレイヤーが、さっき渡したコラッタ（今の所有者は相手）を選び、相手は、さっき渡したきずぐすり（今の所有者は使ったプレイヤー）を選ぶ
        state = swap(state, given, taken, True)
        self.assertEqual((owners(state, given), owners(state, taken)), ((0, 0), (1, 1)))  # 所有者は出所にもどったが、それは同じ規則の結果（隠れた特例ではない）
        # 2 回目は、使ったプレイヤーが渡したきずぐすり・受け取ったコラッタの順に記録する
        self.assertEqual([(c.card, c.previous, c.owner, c.exchange) for c in state.ownership_changes],
                         [(given, 0, 1, 1), (taken, 1, 0, 1), (taken, 0, 1, 2), (given, 1, 0, 2)])
        self.assertIn(given, state.players[0].hand)
        self.assertIn(taken, state.players[1].hand)
        audited(self, state)
        self.assertEqual(v130_problems(state), [])


class AfterExchangeTest(unittest.TestCase):
    """交換したあとの移動は、新しい所有者を基準にする。あとから重ねた進化カード・つけたカードの所有者は変えない。"""

    def test_used_trainer_goes_to_the_new_owners_discard(self):
        state = swap_board(active=mon(HITMONCHAN, (F,), damage=20))
        potion = card_of(state, POTION, player=1)
        state = swap(state, potion, RATTATA, True)
        state = apply_kernel(state, PlayTrainer(0, potion))  # 受け取ったきずぐすり（自分のきずぐすりではない）を使う
        if state.decision is not None:
            state = answer(state, (state.decision.options[0],))
        self.assertIn(potion, state.players[0].discard)
        self.assertNotIn(potion, state.players[1].discard)
        self.assertEqual(owners(state, potion), (0, 1))
        audited(self, state)

    def test_evolution_stack_and_attachments_keep_each_cards_owner(self):
        """受け取ったラッタで自分のコラッタを進化させ、受け取ったエネルギーをつける。重なり・ついたカードはどれも受け取ったプレイヤーの場にあり、所有者は交換した 2 枚だけが変わる
        （自分のコラッタは出所なし）。ポケモン回収で、たねポケモンは受け取ったプレイヤーの手札に、ほかのカード（受け取ったラッタ・エネルギー）は受け取ったプレイヤーのトラッシュに行く。"""
        state = swap_board(hand=(SWAP, POTION, F, SCOOP_UP), opponent_hand=(RATICATE, F, BILL))
        raticate, energy = card_of(state, RATICATE, player=1), card_of(state, F, player=1)
        state = swap(state, raticate, POTION, True)
        state = swap(state, energy, card_of(state, F), True)
        base = state.players[0].bench[0]
        own_rattata, pid = base.card, base.pokemon_id
        state = apply_kernel(state, EvolvePokemon(0, raticate, pid))
        state = apply_kernel(state, AttachEnergy(0, energy, state.find_pokemon(pid)[1].card))
        pokemon = state.find_pokemon(pid)[1]
        self.assertEqual((pokemon.card, pokemon.evolution_stack, list(pokemon.energy)), (raticate, (own_rattata,), [energy]))
        self.assertEqual((owners(state, own_rattata), owners(state, raticate), owners(state, energy)), ((0, None), (0, 1), (0, 1)))
        audited(self, state)
        self.assertEqual(v130_problems(state), [])
        state = use(state, SCOOP_UP)
        while state.decision is not None:
            state = answer(state, (pid,) if pid in state.decision.options else state.decision.options[:1])
        self.assertIn(own_rattata, state.players[0].hand)
        self.assertTrue({raticate, energy} <= set(state.players[0].discard))
        self.assertFalse({raticate, energy} & set(state.players[1].discard))
        audited(self, state)
        self.assertEqual(v130_problems(state), [])

    def test_knocked_out_swapped_pokemon_goes_to_the_new_owner_and_the_opponent_takes_a_prize(self):
        state = swap_board(hand=(SWITCH, POTION), opponent_hand=(RATTATA, POTION), bench=(), opponent_active=mon(HITMONCHAN, (F, F, F)))
        rattata = card_of(state, RATTATA, player=1)
        state = swap(state, rattata, POTION, True)
        state = apply_kernel(state, PlayBasicToBench(0, rattata))
        state = use(state, SWITCH)
        if state.decision is not None:
            state = answer(state, (state.decision.options[0],))
        self.assertEqual(state.players[0].active.card, rattata)
        state = apply_kernel(state, EndTurn(0))
        prizes_before = len(state.players[1].prizes)
        state = apply_kernel(state, UseAttack(1, 1))  # 相手のエビワラーの「メガトンパンチ」でコラッタ（HP 30）をきぜつさせる
        while state.decision is not None and state.decision.kind == TAKE_PRIZE:
            state = answer(state, (state.decision.options[0],))
        self.assertIn(rattata, state.players[0].discard)  # 受け取ったプレイヤーのトラッシュ
        self.assertNotIn(rattata, state.players[1].discard)
        self.assertEqual(len(state.players[1].prizes), prizes_before - 1)  # サイドを取るのは、きぜつしたポケモンの持ち主（受け取ったプレイヤー）の相手
        self.assertEqual(owners(state, rattata), (0, 1))
        audited(self, state)
        self.assertEqual(v130_problems(state), [])

    def test_return_to_deck_by_the_opponents_effect_uses_the_new_owners_deck(self):
        state = swap_board(opponent_hand=(RATTATA, POTION, IMPOSTOR_OAK))
        potion = card_of(state, POTION, player=1)
        state = swap(state, potion, RATTATA, True)
        state = apply_kernel(state, EndTurn(0))
        state = use(state, IMPOSTOR_OAK, player=1)  # 相手が、使ったプレイヤーの手札を山札にもどさせる
        self.assertIn(potion, state.players[0].deck + state.players[0].hand)
        self.assertNotIn(potion, state.players[1].deck + state.players[1].hand)
        audited(self, state)
        self.assertEqual(v130_problems(state), [])

    def test_deck_to_prizes_and_prize_to_hand(self):
        """受け取ったカードを山札からサイドに置き（効果）、サイドから手札に加える（きぜつさせて取る）。どれも新しい所有者のゾーン。"""
        state = swap_board(opponent_hand=(RATTATA, POTION), opponent_active=mon(RATTATA, (), damage=20), active=mon(HITMONCHAN, (F,)), prizes=5)
        potion = card_of(state, POTION, player=1)
        state = swap(state, potion, RATTATA, True)
        p = state.players[0]
        p.hand.remove(potion)
        p.deck.insert(0, potion)  # テストの準備: 受け取ったカードを自分の山札のいちばん上に置く（ゾーンは同じ持ち主のまま）
        before = len(p.prizes)
        deck_top_to_prizes(state, 0, 1, trainer=card_of(state, SWAP, zone="discard"))
        self.assertIn(potion, state.players[0].prizes)
        self.assertEqual(len(state.players[0].prizes), before + 1)
        self.assertEqual(check_invariants(state), [])
        state = apply_kernel(state, UseAttack(0, 0))  # ジャブ 20 で相手のコラッタ（のこり 10）をきぜつさせる
        self.assertEqual(state.decision.kind, TAKE_PRIZE)
        position = state.players[0].prizes.index(potion)
        state = answer(state, (position,))
        self.assertIn(potion, state.players[0].hand)
        self.assertEqual(owners(state, potion), (0, 1))
        self.assertEqual(check_invariants(state), [])

    def test_devolution_discards_the_received_evolution_card_to_the_new_owner(self):
        state = swap_board(hand=(SWAP, POTION, DEVOLUTION_SPRAY), opponent_hand=(RATICATE, BILL))
        raticate = card_of(state, RATICATE, player=1)
        state = swap(state, raticate, POTION, True)
        pid = state.players[0].bench[0].pokemon_id
        state = apply_kernel(state, EvolvePokemon(0, raticate, pid))
        state = use(state, DEVOLUTION_SPRAY)
        state = answer(state, (pid,))  # 退化させるポケモン
        state = answer(state, (1,))  # 取りのぞく進化カードの数（1 枚）
        self.assertIsNone(state.decision)
        self.assertIn(raticate, state.players[0].discard)  # 退化スプレーで取りのぞいた進化カードは、受け取ったプレイヤーのトラッシュ
        self.assertNotIn(raticate, state.players[1].discard)
        self.assertEqual(owners(state, raticate), (0, 1))
        audited(self, state)
        self.assertEqual(v130_problems(state), [])


class ObservationTest(unittest.TestCase):
    def test_spectator_sees_no_cards_of_the_exchange(self):
        state = swap(swap_board(), POTION, RATTATA, True)
        spectator = json.dumps([observe(state, None), visible_log(state, None)], ensure_ascii=False)
        for event in visible_log(state, None):
            if event["kind"] in ("look_at_hand", "exchange_selected", "cards_exchanged"):
                self.assertTrue(event.get("hidden"), event)
                self.assertFalse({"card", "card_id", "cards", "given_card", "taken_card", "card_ids", "ownership"} & set(event), event)
        self.assertNotIn("origin", spectator)
        self.assertEqual(observation_problems(state), [])

    def test_players_see_what_they_looked_at_and_received(self):
        state = swap_board()
        taken, given = card_of(state, POTION, player=1), card_of(state, RATTATA)
        done = swap(state, taken, given, True)
        for viewer in (0, 1):
            exchanged = next(e for e in visible_log(done, viewer) if e["kind"] == "cards_exchanged")
            self.assertEqual((exchanged["given_card"], exchanged["taken_card"]), (given, taken))
        # 相手の観測の使ったプレイヤーの手札は枚数だけ（交換のあとも、受け取ったカードの uid・id を手札の中に見せない）
        for viewer, other in ((0, 1), (1, 0)):
            view = observe(done, viewer)
            self.assertIsNone(view["players"][other]["hand"]["cards"])
            self.assertEqual(view["players"][other]["hand"]["count"], len(done.players[other].hand))
        self.assertNotIn("origin", json.dumps([observe(done, 0), observe(done, 1)], ensure_ascii=False))

    def test_non_decider_sees_only_the_kind_of_the_decision(self):
        state = use(swap_board(), SWAP)
        self.assertEqual(set(observe(state, None)["decision"]), {"kind", "player", "min_choices", "max_choices", "option_count"})
        mine = observe(state, 0)["decision"]
        self.assertEqual({o["card_id"] for o in mine["options"]}, {RATTATA, POTION, F})  # 決めるプレイヤーは見た相手の手札を見ている
        self.assertNotIn("options", observe(state, 1)["decision"])

    def test_unrelated_hand_contents_do_not_reach_the_spectator(self):
        """使ったプレイヤーの手札の交換と関係のないカードだけが違う 2 つの盤面は、観戦者の観測・ログで区別できない（uid を除いて比べる）。"""
        views = []
        for extra in (BILL, F):
            done = swap(swap_board(hand=(RATTATA, POTION, extra)), POTION, RATTATA, True)
            views.append(_without_uids([observe(done, None), visible_log(done, None)]))
        self.assertEqual(views[0], views[1])


def _without_uids(value):
    if isinstance(value, dict):
        return {k: _without_uids(v) for k, v in value.items() if k not in ("card", "cards", "trainer_card", "pokemon", "seed", "energy")}
    if isinstance(value, (list, tuple)):
        return [_without_uids(v) for v in value]
    return value


class ChaosGymTest(unittest.TestCase):
    def test_borrowing_stops_without_deciding_who_is_you(self):
        state = swap_board(hand=(CHAOS_GYM, RATTATA, POTION))
        state = use(state, CHAOS_GYM)
        state = use(state, SWAP, coins=(T,))
        d = state.decision
        self.assertEqual((d.kind, d.player), (ACCEPT_REQUEST, 1))
        self.assertEqual(tuple(d.context_value("unresolved_choices", ())), (1,))
        assert_stops(self, state, ResolveDecision(1, d.id, (1,)), CH1)  # 相手が使うことを選ぶと止める（所有者の簡略化を理由に進めない）
        declined = answer(state, ())
        swap_card = card_of(declined, SWAP, zone="discard")
        self.assertEqual(owners(declined, swap_card), (0, None))  # 使わなかったカードは持ち主のトラッシュ
        self.assertEqual(declined.ownership_changes, ())
        audited(self, declined)

    def test_heads_uses_it_normally(self):
        state = swap_board(hand=(CHAOS_GYM, RATTATA, POTION))
        state = use(state, CHAOS_GYM)
        state = use(state, SWAP, coins=(H,))
        self.assertEqual((state.decision.kind, state.decision.player), (SELECT_EXCHANGE_CARD, 0))


class FaceUpDeckTest(unittest.TestCase):
    def test_deep_face_up_deck_stops_before_use(self):
        from tests.test_flash_faceup_deck_v0_126 import board, card_in_hand, play_flash

        flashed = play_flash(board(hand=("ES2-035", SWAP, HITMONCHAN)))
        # テストの準備: 相手の山札のいちばん下（おもての印のないカード）を相手の手札に移す（使うための条件の「相手の手札が1枚以上」を満たす盤面）
        bottom = flashed.players[1].deck.pop()
        self.assertNotIn(bottom, flashed.face_up_deck)
        flashed.players[1].hand.append(bottom)
        before = snapshot(flashed)
        try:
            apply_kernel(flashed, PlayTrainer(0, card_in_hand(flashed, SWAP)))
        except UnsupportedError as error:
            self.assertEqual(error.code, FU3)
            self.assertEqual(snapshot(flashed), before)
        else:
            self.fail("おもての山札で、オーケーでないときに引く手順が止まるのに、使えた")
        top_only = flashed.clone()
        top_only.face_up_deck = tuple(u for u in flashed.face_up_deck if u in (flashed.players[0].deck[0], flashed.players[1].deck[0]))
        state = apply_kernel(top_only, PlayTrainer(0, card_in_hand(top_only, SWAP)))
        self.assertEqual(state.decision.kind, SELECT_EXCHANGE_CARD)


class AuditTamperingTest(unittest.TestCase):
    """ログの監査は、エンジンの所有者の値を読まず、対戦開始時の持ち主（デッキリストの並び）と交換のログから組み立て直す。わざと誤らせた状態を見つける。"""

    @classmethod
    def setUpClass(cls):
        from tools import existing_effect_games as G

        result = G.play(("T130", "W28"), 90, keep_state=True)
        cls.state = result["state"]
        assert cls.state.ownership_changes, "開発用の seed 90 の T130 対 W28 で交換が起こらなかった"

    def test_real_game_passes(self):
        self.assertEqual(v130_problems(self.state), [])
        self.assertEqual(log_problems(self.state), [])
        self.assertEqual(check_invariants(self.state), [])

    def test_wrong_owner_value_is_found(self):
        state = copy.deepcopy(self.state)
        uid = state.ownership_changes[-1].card
        card = state.cards[uid]
        state.cards = freeze_mapping({**state.cards, uid: dataclasses.replace(card, owner=1 - card.owner)})
        self.assertTrue(any("組み立て直した持ち主" in p for p in v130_problems(state)))

    def test_wrong_destination_is_found(self):
        state = copy.deepcopy(self.state)
        moved = None
        for change in reversed(state.ownership_changes):
            for player, p in enumerate(state.players):
                for zone in ("discard", "hand", "deck", "prizes"):
                    if change.card in getattr(p, zone):
                        getattr(p, zone).remove(change.card)
                        getattr(state.players[1 - player], zone).append(change.card)  # 出所のプレイヤーのゾーンへ（わざと誤った行き先）
                        moved = change.card
                        break
                if moved is not None:
                    break
            if moved is not None:
                break
        if moved is None:
            self.skipTest("交換したカードが場の外にない")
        self.assertTrue(any("ゾーンにある" in p for p in v130_problems(state)))

    def test_wrong_exchange_record_is_found(self):
        state = copy.deepcopy(self.state)
        index = max(i for i, e in enumerate(state.log) if e["kind"] == "cards_exchanged")
        event = dict(state.log[index])
        (card, previous, new, origin), second = event["ownership"]
        event["ownership"] = ((card, new, previous, origin), second)
        state.log = (*state.log[:index], freeze_mapping(event), *state.log[index + 1:])
        self.assertTrue(v130_problems(state))
        state = copy.deepcopy(self.state)
        state.ownership_changes = state.ownership_changes[:-2]
        self.assertTrue(any("変更の記録" in p for p in v130_problems(state)))


class GamesTest(unittest.TestCase):
    def test_development_seeds_run_without_audit_failures(self):
        from tools import existing_effect_games as G

        uses = 0
        for seat in (("T130", "T130"), ("T130", "W28"), ("F45", "T130")):
            result = G.play(seat, 91)
            self.assertIn(result["outcome"], ("game_over", "sudden_death", "halted"), seat)
            self.assertEqual(result["audit"], {}, seat)
            uses += result["v130"].get("played", 0)
        self.assertGreater(uses, 0)

    def test_game_without_the_card_keeps_owners(self):
        from tools import existing_effect_games as G

        result = G.play(("W28", "F45"), 90, keep_state=True)
        state = result["state"]
        self.assertEqual(state.ownership_changes, ())
        self.assertTrue(all(card.origin is None for card in state.cards.values()))
        self.assertEqual(state_to_dict(state, 33)["ownership_changes"], [])
        self.assertEqual(state_to_dict(state, 33)["user_ownership_rules"], [])
        self.assertEqual(result["audit"], {})


class BorrowedDevolutionAuditTest(unittest.TestCase):
    """10.3 節: 正式な対戦で見つかった監査の不足。錯乱ジムで相手が借りて使った退化スプレー（借りたプレイヤーが相手の番に自分のポケモンを退化させる。v0.57 からの既存の処理）を、監査が
    番のプレイヤーでないとして誤って報告していた。借りたことをログから組み立てたときだけ受け付け、ほかの食い違いは今までどおり見つける。"""

    def test_borrowed_devolution_spray_passes_and_tampering_is_found(self):
        from tools import existing_effect_games as G

        result = G.play(("W28", "T130"), 0, keep_state=True)
        state = result["state"]
        index = next(i for i, e in enumerate(state.log) if e["kind"] == "devolve")
        self.assertTrue(any(e["kind"] == "chaos_answered" and e["accepted"] for e in state.log[index - 3:index]))
        self.assertEqual(result["audit"], {})
        self.assertEqual(log_problems(state), [])
        tampered = copy.deepcopy(state)
        event = dict(tampered.log[index])
        event["by_player"] = event["player"] = 1 - event["player"]  # 借りていない番のプレイヤーが、相手の番の退化スプレーで退化させたことにする
        tampered.log = (*tampered.log[:index], freeze_mapping(event), *tampered.log[index + 1:])
        self.assertTrue(any("の退化（ポケモン" in p for p in log_problems(tampered)))


class DocumentTest(unittest.TestCase):
    def test_document_states_the_limits(self):
        text = DOC.read_text(encoding="utf-8")
        for phrase in ("利用者の指定", "UQ-SWAP-PLEASE-OWNERSHIP", "UQ-CHAOS-GYM-BORROWED-TURN", "未解決", "公式の裁定ではない"):
            self.assertIn(phrase, text)
        self.assertIsNone(re.search(r"UQ-SWAP-PLEASE-OWNERSHIP[^。]*解決した", text))


if __name__ == "__main__":
    unittest.main()

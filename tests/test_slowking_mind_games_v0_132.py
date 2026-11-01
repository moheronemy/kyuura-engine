"""v0.132: ヤドキング（neo1-049）の［ちえくらべ］・マッドインパクトと、利用者が指定した［ちえくらべ］の使うかの選択・投げる時点（docs/slowking-mind-games-v0.132.md）。

- 登録・記録（印刷の文面。使うかの選択と時点は利用者の指定の規則で、UQ-MIND-GAMES-OPTIONAL・UQ-MIND-GAMES-TRAINER-STEP は解決済みにしない）・カード id の分岐がない
- 使わない・「おもて」・「うら」の 3 つの経路。「おもて」は条件を払わず効果もない。「うら」・使わないは条件・効果が 1 回だけ。使えないカードでは選択もコインもない
- はたらかない場面（ベンチ・ねむり・マヒ・こんらん・かがくへんかガス・自分のトレーナー・手札以外から使うカード）
- スタジアム・どうぐ（場に出さない・つけない。前のスタジアムは残る）・ポケモンとして出すトレーナー（MG2）・使ったら番が終わるトレーナー（MG3）・錯乱ジム（MG1）・おもての山札（FU4）
- ナツメのESPは特殊能力のコインに当たらない。写した力（［へんしん］・「ばける」）は持っている今のポケモンで判定する
- 決定をまたぐ保存と復元・不正な答え・同じ答えのやり直し・見える範囲。使わない枝で進めない使用は、手札から出す前に拒否する
- マッドインパクトの「おもて」「うら」。交換で所有者の変わったカードの山札
- ログの監査（v132_problems・log_problems）が、わざと誤らせたログを見つける。正式な開始からの対戦
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import pickle
import unittest

from kyuura_engine import (
    EndTurn,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    check_invariants,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import REACTION_POWER
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import Phase
from tests.helpers import (
    BILL,
    BROCKS_NINETALES,
    BROCKS_VULPIX,
    CHAOS_GYM,
    FIGHTING,
    FOSSIL_GRIMER,
    HITMONCHAN,
    MUK,
    MYSTERIOUS_FOSSIL,
    POTION,
    RATTATA,
    SABRINAS_PSYCHIC_CONTROL,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import (
    log_problems,
    observation_problems,
    serialization_problems,
    v130_problems,
    v132_problems,
)
from tests.release_catalog import cards_after
from tests.test_instant_trainers_v0_55 import answer, assert_stops, card_of, snapshot

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "slowking-mind-games-v0.132.md"
SLOWKING, SLOWPOKE = "neo1-049", "neo1-045"
DITTO = "PMCG3-042"
SUPER_RETRIEVAL, SPROUT_TOWER, FOCUS_BAND = "neo1-092", "neo1-085", "neo1-088"
COMPUTER_ERROR, FLASH, SWAP = "PR1-026", "ES2-035", "PR1-027"
OTHER_STADIUM = "neo3-057"
P = "PMCG1-101"  # 超エネルギー
MG1, MG2, MG3, FU4 = E.MIND_GAMES_CHAOS_GYM_CODE, E.MIND_GAMES_PLAY_AS_POKEMON_CODE, E.MIND_GAMES_BLOCKED_TURN_END_CODE, "UNRESOLVED_FACE_UP_DECK_PLACE_TOP"
HEADS, TAILS = CoinSide.HEADS, CoinSide.TAILS


def slowking(**extra):
    return {"card": SLOWKING, "energy": [P, P, P], "evolved_from": SLOWPOKE, **extra}


def board(hand=(BILL, POTION), *, deck=(FIGHTING,) * 8, discard=(FIGHTING, FIGHTING), opponent=None, opponent_bench=(RATTATA,), opponent_hand=(), active=None, bench=(RATTATA,),
          opponent_deck=(FIGHTING,) * 8, stadium=None):
    """プレイヤー 0 の番（7 番）。相手（プレイヤー 1）のバトル場はヤドキング（既定）。"""
    me = {"active": active or {"card": HITMONCHAN, "energy": [FIGHTING], "damage": 20}, "bench": list(bench), "hand": list(hand), "deck": list(deck), "discard": list(discard)}
    them = {"active": opponent or slowking(), "bench": list(opponent_bench), "hand": list(opponent_hand), "deck": list(opponent_deck)}
    return build_test_state([me, them], turn_number=7, current_player=0)


def play(state, card_id, player=0):
    return apply_kernel(state, PlayTrainer(player, card_of(state, card_id, player=player)))


def respond(state, use_power, coin=None):
    """待っている［ちえくらべ］の決定に答える（``use_power`` なら使う。``coin`` はそのコインの結果）。"""
    d = state.decision
    if coin is not None:
        state = with_coin_results(state, coin)
    return apply_kernel(state, ResolveDecision(d.player, d.id, d.options if use_power else ()))


def kinds_since(state, start):
    return [e["kind"] for e in state.log[start:]]


def is_reaction(state):
    d = state.decision
    return d is not None and d.resume == "trainer" and d.context_value("trainer_reaction") is not None


class RegistrationTest(unittest.TestCase):
    def test_entries_texts_and_record(self):
        definition = load_card_pool().get(SLOWKING)
        power = E.DEFAULT_EFFECTS.power_entry(SLOWKING, 0)
        attack = E.DEFAULT_EFFECTS.attack_entry(SLOWKING, 0)
        self.assertIsInstance(power.effect, E.BlockOpponentHandTrainerOnHeads)
        self.assertEqual((power.name_ja, power.text_ja, power.play_text_ja, power.source),
                         ("ちえくらべ", definition.powers[0].text_ja, E.MIND_GAMES_TEXT, "kyuura data/cards.json"))
        self.assertEqual(power.effect.check(definition.powers[0]), [])
        self.assertIsInstance(attack.effect, E.CoinBonusDamageAndConfuse)
        self.assertEqual((attack.effect.bonus, attack.text_ja, attack.play_text_ja, definition.attacks[0].damage, definition.attacks[0].damage_modifier),
                         (10, E.MUD_IMPACT_TEXT, E.MUD_IMPACT_TEXT, 20, "+"))
        self.assertEqual(attack.effect.check(definition.attacks[0]), [])
        # 型名だけで同じとしない: 数・特殊状態・「うら」の書き方が違えば受け付けない
        for text in (E.MUD_IMPACT_TEXT.replace("10ダメージ", "20ダメージ"), E.MUD_IMPACT_TEXT.replace("こんらん", "マヒ"), E.MUD_IMPACT_TEXT + "「うら」なら、何もしない。"):
            self.assertTrue(attack.effect.check(dataclasses.replace(definition.attacks[0], text_ja=text)), text)
        record = E.USER_SPECIFIED_RULES["neo1-049/power/0"]
        self.assertEqual((record.rule, record.printed_text, record.play_text, record.issues, record.specified_by, record.source),
                         (E.USER_MIND_GAMES_OPTIONAL, definition.powers[0].text_ja, E.MIND_GAMES_TEXT, ("UQ-MIND-GAMES-OPTIONAL", "UQ-MIND-GAMES-TRAINER-STEP"),
                          "user", E.USER_MIND_GAMES_RULE_SOURCE))
        self.assertIn("公式の裁定", record.not_recorded_as)
        self.assertIn("錯乱ジム", record.not_decided)
        self.assertIn(f"「{record.instruction}」", DOC.read_text(encoding="utf-8"))
        self.assertEqual(E.USER_SPECIFIED_RULES["PR1-027/trainer"].source, E.USER_SPECIFIED_RULE_SOURCE)  # v0.130 の記録は変えていない
        # 記録の規則の種類が違う登録は受け付けない
        self.assertTrue(E.BlockOpponentHandTrainerOnHeads(trigger_rule="OTHER").check(definition.powers[0]))

    def test_pool_counts_and_no_card_branch(self):
        extract = read_extract()
        self.assertEqual(extract["pool_v0_132"], [SLOWKING])
        self.assertEqual(cards_after(extract, "0.131") - cards_after(extract, "0.132"), {SLOWKING})
        pool = load_card_pool()
        self.assertIn(SLOWKING, pool.playable_ids)
        self.assertEqual(len(pool.playable_ids - cards_after(extract, "0.132")), 1373)
        for path in [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]:
            self.assertNotIn(SLOWKING, path.read_text(encoding="utf-8"), path.name)

    def test_adoption_and_research_records(self):
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"][SLOWKING]
        self.assertEqual(sources["play_text"], {"attack/0": "kyuura_printed_text", "power/0": "kyuura_printed_text"})
        self.assertEqual(sources["user_specified_rule"], {"power/0": E.USER_MIND_GAMES_RULE_SOURCE})
        self.assertLessEqual({"UQ-MIND-GAMES-OPTIONAL", "UQ-MIND-GAMES-TRAINER-STEP", "CR-MIND-GAMES-SCOPE", "CR-MIND-GAMES-STADIUM-TOOL"}, set(sources["kyuura_records"]))
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        self.assertEqual(links["latest_descriptions"]["user_specified_rules"]["neo1-049/power/0"], E.USER_MIND_GAMES_RULE_SOURCE)
        cases = {(c["kyuura_issue"], c["card_id"], c["target"]): c["engine"] for c in links["kyuura_cases_without_engine_ruling"]["cases"]}
        rule = {"user_specified_rule": "neo1-049/power/0"}
        self.assertEqual(cases[("UQ-MIND-GAMES-OPTIONAL", SLOWKING, "power/0")], rule)
        self.assertEqual(cases[("UQ-MIND-GAMES-TRAINER-STEP", SLOWKING, "power/0")], rule)
        for card in ("PMCG5-094", SPROUT_TOWER, FOCUS_BAND, SUPER_RETRIEVAL):
            self.assertEqual(cases[("UQ-MIND-GAMES-TRAINER-STEP", card, "trainer")], rule, card)
        self.assertEqual(cases[("UQ-MIND-GAMES-TRAINER-STEP", CHAOS_GYM, "trainer")], {"stop_codes": [MG1]})
        for card in (MYSTERIOUS_FOSSIL, "PMCG1-091"):
            self.assertEqual(cases[("UQ-MIND-GAMES-TRAINER-STEP", card, "trainer")], {"stop_codes": [MG2]})
        self.assertEqual(cases[("UQ-FLASH-FACE-UP-DECK", SLOWKING, "power/0")], {"stop_codes": [FU4]})
        self.assertEqual(cases[("UQ-SWAP-PLEASE-OWNERSHIP", SLOWKING, "power/0")], {"user_specified_rule": "PR1-027/trainer"})
        stops = links["stop_codes"]
        self.assertEqual([(stops[c]["engine_rulings"][0]["ruling_id"], stops[c]["kyuura_issue"], stops[c]["kyuura_disposition"]) for c in (MG1, MG2, MG3)],
                         [("MG1", "UQ-MIND-GAMES-TRAINER-STEP", "issue_not_in_index"), ("MG2", "UQ-MIND-GAMES-TRAINER-STEP", "issue_not_in_index"),
                          ("MG3", None, "not_in_kyuura")])

    def test_not_declarable(self):
        turn = build_test_state([{"active": slowking(), "hand": []}, {"active": HITMONCHAN}], turn_number=7, current_player=0)
        pid = turn.players[0].active.pokemon_id
        assert_stops(self, turn, UsePokemonPower(0, pid, 0), "POWER_NOT_DECLARABLE", IllegalActionError)


class ThreePathsTest(unittest.TestCase):
    def setUp(self):
        self.state = board(hand=(SUPER_RETRIEVAL, BILL, POTION), discard=(FIGHTING, FIGHTING))
        self.card = card_of(self.state, SUPER_RETRIEVAL)
        self.offered = play(self.state, SUPER_RETRIEVAL)

    def test_offer_before_cost_after_presentation(self):
        s = self.offered
        self.assertTrue(is_reaction(s))
        d = s.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (REACTION_POWER, 1, (s.players[1].active.pokemon_id,), 0, 1))
        self.assertEqual(kinds_since(s, len(self.state.log)), ["play_trainer"])  # 見せて名前を伝えただけ。手札のトラッシュ・コインはまだ
        self.assertEqual(s.trainer_in_use.card, self.card)
        self.assertEqual(sorted(s.players[0].hand), sorted(u for u in self.state.players[0].hand if u != self.card))
        self.assertEqual(s.players[0].discard, self.state.players[0].discard)
        self.assertEqual(repr(s.rng.getstate()), repr(self.state.rng.getstate()))  # 乱数を使っていない
        self.assertEqual(check_invariants(s), [])
        self.assertEqual(serialization_problems(s), [])
        self.assertEqual(observation_problems(s), [])

    def test_heads_blocks_without_cost_or_effect(self):
        s = respond(self.offered, True, HEADS)
        self.assertEqual(kinds_since(s, len(self.state.log)), ["play_trainer", "trainer_reaction_answered", "coin_flip", "trainer_reaction_check", "trainer_blocked"])
        self.assertEqual(s.players[0].deck[0], self.card)
        self.assertEqual(len(s.players[0].deck), len(self.state.players[0].deck) + 1)
        self.assertEqual(sorted(s.players[0].hand), sorted(u for u in self.state.players[0].hand if u != self.card))  # 手札の 2 枚は払っていない
        self.assertEqual(s.players[0].discard, self.state.players[0].discard)  # トラッシュに置いていない・回収もない
        self.assertIsNone(s.trainer_in_use)
        self.assertIsNone(s.decision)
        self.assertEqual((s.phase, s.current_player), (Phase.MAIN, 0))
        coin = next(e for e in s.log if e["kind"] == "coin_flip")
        self.assertEqual((coin["player"], coin["source"], coin["effect"]), (1, "power", "neo1-049@power0"))
        self.assertEqual(v132_problems(s), [])
        self.assertEqual(check_invariants(s), [])

    def _finish_retrieval(self, s):
        d = s.decision
        self.assertEqual(d.context_value("trainer_reaction"), None)
        hand = [u for u in s.players[0].hand][:2]
        s = apply_kernel(s, ResolveDecision(0, d.id, tuple(hand)))
        d = s.decision
        return apply_kernel(s, ResolveDecision(0, d.id, tuple(d.options[:d.max_choices])))

    def test_tails_and_decline_pay_and_resolve_once(self):
        for label, s in (("tails", respond(self.offered, True, TAILS)), ("decline", respond(self.offered, False))):
            with self.subTest(label):
                kinds = kinds_since(s, len(self.state.log))
                expected = ["play_trainer", "trainer_reaction_answered"] + (["coin_flip", "trainer_reaction_check"] if label == "tails" else [])
                self.assertEqual(kinds, expected)
                self.assertEqual(s.decision.kind, "discard_from_hand")  # 通常の条件の支払いへ（選ぶのは使ったプレイヤー）
                done = self._finish_retrieval(s)
                kinds = kinds_since(done, len(self.state.log))
                self.assertEqual(kinds.count("discard_from_hand"), 1)
                self.assertEqual(kinds.count("trainer_reaction_answered"), 1)
                self.assertEqual(kinds.count("coin_flip"), 1 if label == "tails" else 0)
                self.assertEqual(kinds[-1], "discard_trainer")
                self.assertIn(self.card, done.players[0].discard)
                self.assertEqual(v132_problems(done), [])
                self.assertEqual(check_invariants(done), [])

    def test_unusable_trainer_has_no_choice_or_coin(self):
        state = board(hand=(SUPER_RETRIEVAL, BILL))  # このカードのほかに手札が 1 枚（2 枚トラッシュできない）
        assert_stops(self, state, PlayTrainer(0, card_of(state, SUPER_RETRIEVAL)), "INSUFFICIENT_CARDS_IN_HAND", IllegalActionError)
        swap = board(hand=(SWAP, POTION), opponent_hand=())
        assert_stops(self, swap, PlayTrainer(0, card_of(swap, SWAP)), "OPPONENT_HAND_EMPTY", IllegalActionError)


class ScopeTest(unittest.TestCase):
    def no_offer(self, state, card_id=BILL):
        s = play(state, card_id)
        self.assertFalse(is_reaction(s))
        self.assertNotIn("trainer_reaction_answered", [e["kind"] for e in s.log])
        return s

    def test_bench_status_and_suppression(self):
        bench = board(opponent={"card": HITMONCHAN}, opponent_bench=(slowking(),))
        self.no_offer(bench)
        for status in ({"sleep": True}, {"paralysis": 6}, {"confusion": True}):
            with self.subTest(status):
                self.no_offer(board(opponent=slowking(**status)))
        self.assertTrue(is_reaction(play(board(opponent=slowking(poison=10)), BILL)))  # どくは説明に挙げられていない
        gas = board(opponent_bench=({"card": MUK, "evolved_from": FOSSIL_GRIMER},))
        self.no_offer(gas)
        own_gas = board(bench=({"card": MUK, "evolved_from": FOSSIL_GRIMER},))
        self.no_offer(own_gas)

    def test_owner_and_non_hand_routes(self):
        # 持ち主自身のトレーナーには当たらない（自分の場のヤドキング）
        own = build_test_state([{"active": slowking(), "hand": [BILL], "deck": [FIGHTING] * 6}, {"active": HITMONCHAN, "deck": [FIGHTING] * 6}],
                               turn_number=7, current_player=0)
        self.no_offer(own)
        # ナツメのサイキックコントロール: 手札から使う外側のカードには当たる。相手のトラッシュから使う内側のカードには当たらない
        state = board(hand=(SABRINAS_PSYCHIC_CONTROL,), opponent=slowking())
        state = build_test_state([{"active": {"card": HITMONCHAN, "energy": [FIGHTING]}, "hand": [SABRINAS_PSYCHIC_CONTROL], "deck": [FIGHTING] * 6},
                                  {"active": slowking(), "discard": [BILL], "deck": [FIGHTING] * 6}], turn_number=7, current_player=0)
        s = respond(play(state, SABRINAS_PSYCHIC_CONTROL), False)
        while s.decision is not None:
            d = s.decision
            self.assertIsNone(d.context_value("trainer_reaction"), d.kind)
            s = apply_kernel(s, ResolveDecision(d.player, d.id, d.options[:max(d.min_choices, 1)]))
        self.assertEqual([e["kind"] for e in s.log].count("trainer_reaction_answered"), 1)

    def test_stadium_heads_keeps_old_stadium_and_tails_places(self):
        base = board(hand=(SPROUT_TOWER,))
        old = build_test_state([{"active": {"card": HITMONCHAN, "energy": [FIGHTING]}, "hand": [SPROUT_TOWER, OTHER_STADIUM], "deck": [FIGHTING] * 6},
                                {"active": slowking(), "deck": [FIGHTING] * 6}], turn_number=5, current_player=0)
        old = respond(play(old, OTHER_STADIUM), False)
        self.assertEqual(old.cards[old.stadium.card].card_id, OTHER_STADIUM)
        blocked = respond(play(old, SPROUT_TOWER), True, HEADS)
        self.assertEqual(blocked.cards[blocked.stadium.card].card_id, OTHER_STADIUM)  # 前のスタジアムは残る
        self.assertNotIn(card_of(old, SPROUT_TOWER), blocked.players[0].discard)
        self.assertEqual(blocked.players[0].deck[0], card_of(old, SPROUT_TOWER))
        placed = respond(play(old, SPROUT_TOWER), True, TAILS)
        self.assertEqual(placed.cards[placed.stadium.card].card_id, SPROUT_TOWER)
        self.assertEqual(v132_problems(blocked) + v132_problems(placed), [])
        self.assertTrue(is_reaction(play(base, SPROUT_TOWER)))

    def test_tool_heads_not_attached(self):
        state = board(hand=(FOCUS_BAND,))
        blocked = respond(play(state, FOCUS_BAND), True, HEADS)
        self.assertTrue(all(not p.trainers for p in blocked.players[0].in_play()))
        self.assertEqual(blocked.players[0].deck[0], card_of(state, FOCUS_BAND))
        declined = respond(play(state, FOCUS_BAND), False)
        while declined.decision is not None:
            d = declined.decision
            declined = apply_kernel(declined, ResolveDecision(d.player, d.id, d.options[:1]))
        self.assertEqual(sum(len(p.trainers) for p in declined.players[0].in_play()), 1)

    def test_play_as_pokemon_use_stops_and_decline_places(self):
        state = board(hand=(MYSTERIOUS_FOSSIL,))
        offered = play(state, MYSTERIOUS_FOSSIL)
        self.assertTrue(is_reaction(offered))
        d = offered.decision
        assert_stops(self, offered, ResolveDecision(1, d.id, d.options), MG2)
        placed = respond(offered, False)
        self.assertEqual(len(placed.players[0].bench), 2)
        self.assertEqual(check_invariants(placed), [])

    def test_turn_ending_trainer_use_stops(self):
        state = board(hand=(COMPUTER_ERROR, POTION))
        offered = play(state, COMPUTER_ERROR)
        d = offered.decision
        assert_stops(self, offered, ResolveDecision(1, d.id, d.options), MG3)
        declined = respond(offered, False)
        self.assertIsNotNone(declined.decision)  # 通常どおり引く枚数の決定へ

    def test_chaos_gym_stops_before_presentation(self):
        state = board(hand=(BILL, SPROUT_TOWER))
        chaos = build_test_state([{"active": {"card": HITMONCHAN, "energy": [FIGHTING]}, "hand": [BILL, SPROUT_TOWER, CHAOS_GYM, POTION], "deck": [FIGHTING] * 8},
                                  {"active": slowking(), "deck": [FIGHTING] * 8}], turn_number=7, current_player=0)
        chaos = respond(play(chaos, CHAOS_GYM), True, TAILS)
        self.assertEqual(chaos.cards[chaos.stadium.card].card_id, CHAOS_GYM)
        assert_stops(self, chaos, PlayTrainer(0, card_of(chaos, BILL)), MG1)
        self.assertTrue(is_reaction(play(chaos, SPROUT_TOWER)))  # スタジアムカードには錯乱ジムのコインがない（前後の問いがない）
        self.assertTrue(is_reaction(play(state, BILL)))

    def test_chaos_gym_borrow_by_the_opponent_of_the_holder_stops(self):
        # ［ちえくらべ］を持つ側（プレイヤー 0）が錯乱ジムの「うら」で使えなかったカードを、相手がかわりに使うことを選ぶと MG1（「手札から出して使う」に当たるかが決まらない）
        state = build_test_state([{"active": slowking(), "hand": [BILL, CHAOS_GYM], "deck": [FIGHTING] * 8}, {"active": HITMONCHAN, "deck": [FIGHTING] * 8}],
                                 turn_number=7, current_player=0)
        state = play(state, CHAOS_GYM)
        tails = apply_kernel(with_coin_results(state, TAILS), PlayTrainer(0, card_of(state, BILL)))
        d = tails.decision
        self.assertEqual((d.kind, d.player, d.context_value("unresolved_code")), ("accept_request", 1, MG1))
        assert_stops(self, tails, ResolveDecision(1, d.id, (1,)), MG1)
        declined = apply_kernel(tails, ResolveDecision(1, d.id, ()))
        self.assertIn(card_of(state, BILL), declined.players[0].discard)

    def test_face_up_deck_use_stops(self):
        from kyuura_engine import faceup

        s = board(hand=(BILL, POTION)).clone()
        faceup.set_marks(s, 0, s.players[0].deck[:2])  # フラッシュでおもてにした山札の上 2 枚（既存の印の付け方とログ）
        s.add_event("flash_face_up", player=0, owner=0, count=5, top_card_id=s.cards[s.players[0].deck[0]].card_id, trainer_card=None)
        self.assertTrue(faceup.has_face_up(s, 0))
        offered = play(s, POTION)
        d = offered.decision
        assert_stops(self, offered, ResolveDecision(1, d.id, d.options), FU4)
        self.assertEqual(respond(offered, False).decision.kind, "select_pokemon")  # 使わない答えは受け付ける（きずぐすりの対象を選ぶ）
        # マサキは使わない・「うら」の枝で 2 枚まとめて引く（FU3）ので、見せる前に拒否する（「おもて」なら起こらない処理でも、答えのあとに拒否へ変えない）
        assert_stops(self, s, PlayTrainer(0, card_of(s, BILL)), "UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE")


class DeclineLookaheadTest(unittest.TestCase):
    def test_trainer_stopped_in_the_decline_branch_is_rejected_before_presentation(self):
        class StopsInEffect(E.TrainerEffect):
            implementation_id = "test_stops_in_effect"

            def check(self, definition):
                return []

            def resolve(self, state, use):
                raise UnsupportedError("UNRESOLVED_TEST_EFFECT", "効果の途中で止まる（テスト）")

        entry = E.DEFAULT_EFFECTS.trainer_entry(POTION)
        registry = E.DEFAULT_EFFECTS.without_trainers("test-v132", [POTION]).with_trainers("test-v132b", {POTION: dataclasses.replace(entry, effect=StopsInEffect())})
        me = {"active": {"card": HITMONCHAN, "energy": [FIGHTING]}, "hand": [POTION], "deck": [FIGHTING] * 6}
        for opponent in (slowking(), HITMONCHAN):
            state = build_test_state([me, {"active": opponent, "deck": [FIGHTING] * 6}], turn_number=7, current_player=0, effects=registry)
            assert_stops(self, state, PlayTrainer(0, card_of(state, POTION)), "UNRESOLVED_TEST_EFFECT")


class CopyAndEspTest(unittest.TestCase):
    def test_transformed_ditto_holds_the_copied_power(self):
        state = build_test_state([{"active": {"card": DITTO, "energy": [FIGHTING]}, "hand": [BILL], "deck": [FIGHTING] * 6},
                                  {"active": slowking(), "hand": [BILL], "deck": [FIGHTING] * 6}], turn_number=8, current_player=1)
        s = play(state, BILL, player=1)
        self.assertTrue(is_reaction(s))
        self.assertEqual((s.decision.player, s.decision.options), (0, (s.players[0].active.pokemon_id,)))  # 持つのは今のメタモン
        blocked = respond(s, True, HEADS)
        self.assertEqual(blocked.players[1].deck[0], card_of(state, BILL, player=1))
        self.assertEqual(next(e for e in blocked.log if e["kind"] == "coin_flip")["player"], 0)
        asleep = build_test_state([{"active": {"card": DITTO, "energy": [FIGHTING], "sleep": True}, "hand": [BILL], "deck": [FIGHTING] * 6},
                                   {"active": slowking(), "hand": [BILL], "deck": [FIGHTING] * 6}], turn_number=8, current_player=1)
        self.assertFalse(is_reaction(play(asleep, BILL, player=1)))  # ねむりのメタモンは［へんしん］も消える

    def test_shapeshift_card_power_works_on_ninetales(self):
        state = build_test_state([{"active": {"card": BROCKS_NINETALES, "energy": [FIGHTING], "evolved_from": BROCKS_VULPIX}, "hand": [SLOWKING], "deck": [FIGHTING] * 6},
                                  {"active": HITMONCHAN, "hand": [BILL], "deck": [FIGHTING] * 6}], turn_number=7, current_player=0)
        pid = state.players[0].active.pokemon_id
        s = apply_kernel(state, UsePokemonPower(0, pid, 0))
        s = answer(s, (card_of(s, SLOWKING),))
        s = apply_kernel(s, EndTurn(0))
        while s.current_player != 1 or s.phase is not Phase.MAIN:
            d = s.decision
            s = apply_kernel(s, ResolveDecision(d.player, d.id, d.options[:1]))
        offered = play(s, BILL, player=1)
        self.assertTrue(is_reaction(offered))
        self.assertEqual(offered.decision.options, (pid,))

    def test_esp_does_not_touch_the_power_coin(self):
        s = respond(play(board(), BILL), True, TAILS)
        kinds = [e["kind"] for e in s.log]
        self.assertNotIn("esp_redo", kinds)
        coins = [e for e in s.log if e["kind"] == "coin_flip"]
        self.assertEqual([c["source"] for c in coins], ["power"])
        self.assertFalse(isinstance(E.DEFAULT_EFFECTS.power_entry(SLOWKING, 0).effect, E.TrainerEffect))


class PersistenceAndAnswersTest(unittest.TestCase):
    def setUp(self):
        self.state = play(board(hand=(SUPER_RETRIEVAL, BILL, POTION)), SUPER_RETRIEVAL)

    def test_save_and_restore_at_the_decision(self):
        expected = {c: state_to_dict(respond(self.state, True, c), max(FORMAT_VERSIONS)) for c in (HEADS, TAILS)}
        expected[None] = state_to_dict(respond(self.state, False), max(FORMAT_VERSIONS))
        for restored in (pickle.loads(pickle.dumps(self.state)), copy.deepcopy(self.state), self.state.clone()):
            self.assertEqual(state_to_dict(restored, max(FORMAT_VERSIONS)), state_to_dict(self.state, max(FORMAT_VERSIONS)))
            for version in [v for v in FORMAT_VERSIONS if v >= 7]:  # 形式 1〜6 は進化したポケモンの重なり（ヤドキング）を表せない（既存の制限）
                data = state_to_dict(restored, version)
                self.assertEqual(data["decision"]["context"]["trainer_reaction"], "neo1-049@power0")  # 古い形式でも決定の続きを落とさない
                self.assertEqual(data["decision"]["context"]["use"], [0, card_of(board(hand=(SUPER_RETRIEVAL, BILL, POTION)), SUPER_RETRIEVAL), SUPER_RETRIEVAL])
            for coin in (HEADS, TAILS):
                self.assertEqual(state_to_dict(respond(restored, True, coin), max(FORMAT_VERSIONS)), expected[coin])
            self.assertEqual(state_to_dict(respond(restored, False), max(FORMAT_VERSIONS)), expected[None])
        self.assertEqual(state_to_dict(self.state, max(FORMAT_VERSIONS))["user_ownership_rules"], [])

    def test_invalid_answers_are_rejected_without_change(self):
        d = self.state.decision
        for command, error in ((ResolveDecision(0, d.id, d.options), IllegalActionError), (ResolveDecision(1, d.id + 1, d.options), IllegalActionError),
                               (ResolveDecision(1, d.id, (999,)), IllegalActionError), (ResolveDecision(1, d.id, d.options * 2), IllegalActionError),
                               (PlayTrainer(0, card_of(self.state, BILL)), IllegalActionError), (EndTurn(0), IllegalActionError)):
            before = snapshot(self.state)
            with self.assertRaises(error):
                apply_kernel(self.state, command)
            self.assertEqual(snapshot(self.state), before)

    def test_same_answer_does_not_redraw_or_repeat(self):
        d = self.state.decision
        first = apply_kernel(self.state, ResolveDecision(1, d.id, d.options))
        again = apply_kernel(self.state, ResolveDecision(1, d.id, d.options))
        self.assertEqual(snapshot(first), snapshot(again))  # 同じ状態への同じ答えは同じコイン（引き直せない）
        with self.assertRaises(IllegalActionError):
            apply_kernel(first, ResolveDecision(1, d.id, d.options))  # 答えた決定にもう一度答えられない（重ねて使えない）
        self.assertEqual([e["kind"] for e in first.log].count("trainer_reaction_answered"), 1)

    def test_visibility(self):
        state = self.state
        for viewer in (0, 1, None):
            view = observe(state, viewer)
            self.assertEqual(view["decision"]["kind"], REACTION_POWER)
            text = json.dumps(view, ensure_ascii=False, default=str)
            if viewer != 0:
                for uid in state.players[0].hand:
                    self.assertNotIn(f'"card_id": "{state.cards[uid].card_id}", "uid": {uid}', text)
        self.assertEqual(observation_problems(state), [])
        blocked = respond(state, True, HEADS)
        for viewer in (1, None):
            shown = visible_log(blocked, viewer)
            self.assertEqual(shown[-1]["kind"], "trainer_blocked")  # 見せたカードを山札の上に置いた（公開）
            draws = [e for e in shown if e["kind"] == "draw" and e["player"] == 0]
            self.assertTrue(all("cards" not in e for e in draws))
        self.assertEqual(observation_problems(blocked), [])


class MudImpactTest(unittest.TestCase):
    def test_heads_and_tails(self):
        state = build_test_state([{"active": slowking(), "deck": [FIGHTING] * 6}, {"active": {"card": HITMONCHAN}, "deck": [FIGHTING] * 6}],
                                 turn_number=7, current_player=0)
        target = state.players[1].active
        for coin, damage, confused in ((HEADS, 60, True), (TAILS, 40, False)):  # エビワラーの弱点は超（×2）: 「おもて」(20+10)×2・「うら」20×2
            with self.subTest(coin):
                s = apply_kernel(with_coin_results(state, coin), UseAttack(0, 0))
                defender = s.players[1].active
                self.assertEqual(defender.damage - target.damage, damage)
                self.assertEqual(defender.conditions.confused, confused)


class OwnershipTest(unittest.TestCase):
    def test_received_trainer_goes_to_the_receivers_deck(self):
        state = build_test_state([{"active": {"card": HITMONCHAN, "energy": [FIGHTING], "damage": 20}, "bench": [RATTATA], "hand": [SWAP, RATTATA], "deck": [FIGHTING] * 6},
                                  {"active": slowking(), "bench": [RATTATA], "hand": [POTION, RATTATA], "deck": [FIGHTING] * 6}], turn_number=7, current_player=0)
        s = respond(play(state, SWAP), False)
        s = answer(s, (card_of(s, POTION, player=1),))
        s = answer(s, (card_of(s, RATTATA),))
        s = answer(s, (1,))
        potion = card_of(s, POTION)
        self.assertEqual(s.cards[potion].owner, 0)
        blocked = respond(play(s, POTION), True, HEADS)
        self.assertEqual(blocked.players[0].deck[0], potion)
        self.assertEqual(blocked.cards[potion].owner, 0)
        self.assertEqual(v130_problems(blocked), [])
        self.assertEqual(v132_problems(blocked), [])
        self.assertEqual(check_invariants(blocked), [])


class AuditTamperingTest(unittest.TestCase):
    def setUp(self):
        self.blocked = respond(play(board(hand=(SUPER_RETRIEVAL, BILL, POTION)), SUPER_RETRIEVAL), True, HEADS)

    def tampered(self, change):
        s = self.blocked.clone()
        log = [dict(e) for e in s.log]
        change(log)
        s.log = tuple(log) if isinstance(s.log, tuple) else log
        return s

    def index(self, kind):
        return next(i for i, e in enumerate(self.blocked.log) if e["kind"] == kind)

    def test_real_log_passes(self):
        self.assertEqual(v132_problems(self.blocked), [])

    def test_each_tampering_is_found(self):
        coin, check, blocked = self.index("coin_flip"), self.index("trainer_reaction_check"), self.index("trainer_blocked")
        answered = self.index("trainer_reaction_answered")
        cases = {
            "coin result": lambda log: log[coin].update(result="tails"),
            "check result": lambda log: log[check].update(result="tails"),
            "missing block": lambda log: log.pop(blocked),
            "wrong decider": lambda log: log[answered].update(player=0),
            "coin by user": lambda log: log[coin].update(player=0),
            "cost paid": lambda log: log.insert(blocked, {"kind": "discard_from_hand", "turn": 7, "player": 0, "cards": []}),
            "destination": lambda log: log[blocked].update(destination="discard"),
            "discarded later": lambda log: log.append({"kind": "discard_trainer", "turn": 7, "player": 0, "card": log[blocked]["card"]}),
            "draw mismatch": lambda log: log.append({"kind": "draw", "turn": 9, "player": 0, "cards": [self.blocked.players[0].deck[1]]}),
            "second coin": lambda log: log.insert(check, dict(log[coin])),
        }
        for label, change in cases.items():
            with self.subTest(label):
                self.assertTrue(v132_problems(self.tampered(change)), label)

    def test_missing_offer_is_found_by_the_general_audit(self):
        from tools import existing_effect_games as G

        result = G.play(("X132", "X132"), 90, keep_state=True)
        state = result["state"]
        self.assertEqual(log_problems(state), [])
        self.assertEqual(v132_problems(state), [])
        log = [dict(e) for e in state.log]
        i = next((i for i, e in enumerate(log) if e["kind"] == "trainer_reaction_answered"), None)
        self.assertIsNotNone(i)
        tampered = state.clone()
        tampered.log = log[:i] + log[i + 1:]
        self.assertTrue(any("ちえくらべ" in p for p in log_problems(tampered)))


class DocumentTest(unittest.TestCase):
    def test_document_states_the_limits(self):
        text = DOC.read_text(encoding="utf-8")
        for phrase in ("利用者の指定", "公式の裁定ではない", "UQ-MIND-GAMES-OPTIONAL", "UQ-MIND-GAMES-TRAINER-STEP", MG1, MG2, MG3, FU4, "kyuura への報告事項"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()

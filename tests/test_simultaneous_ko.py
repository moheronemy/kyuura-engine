"""同時のきぜつ（v0.2f）: ピカチュウの「でんげき」で、相手の対戦ポケモンと自分のピカチュウが同じワザできぜつする。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES・knockout_timing・sudden_death）:

- p.323「16 ポケモンの「きぜつ」」: HP 以上のダメージできぜつ。ついていたすべてのカードもトラッシュ。1 匹きぜつしたら、
  その相手側のプレイヤーがサイドを 1 枚取る。サイドをすべて取り終えたら勝ち（両方のプレイヤーが同時に取り終えた
  ときなど、対戦が終了しないこともある）。対戦ポケモンがきぜつしたら新しい対戦ポケモンを出す。出せなければ負け。
  両方の対戦ポケモンが同時にきぜつしたら、番でないプレイヤーが先に出し、番のプレイヤーはそれを見てから出す
- p.324: 1 つのワザなどで複数のポケモンがきぜつしたら「同時に『きぜつ』した」
- p.311「勝ち負けが決まるとき」と表: 両方が同時にサイドを取り終えたら・両方が出せないならサドン・デス。表の 9 行
- p.325「23」: 同じタイミングで起こったことの順番は、番のプレイヤーが決める
- p.309: ワザの途中で対象がいなくなった内容は無視し、それ以降の内容は無視しない

基本の盤面: プレイヤー 0（番）のピカチュウ（HP40・ダメージ 30）が「でんげき」。相手のコラッタ（HP30）は 30 で
きぜつし、コインが「うら」ならピカチュウも自分への 10 できぜつする。
"""

import unittest

from kyuura_engine import (
    EndTurn, EngineError, IllegalActionError, Phase, PlayTrainer, PromoteActive, ResolveDecision, Retreat, TakePrize,
    UnsupportedError, UseAttack, apply_command, check_invariants, state_to_dict,
)
from kyuura_engine.resolution import flow
from kyuura_engine.resolution.kernel import Resolution
from kyuura_engine.rng import rng_fingerprint

from tests.helpers import (
    DEFENDER, DIGLETT, FIRE, GROWLITHE, H, LIGHTNING, PIKACHU, PLUSPOWER, PONYTA, RATTATA, T, build_test_state,
    with_coin_results,
)
from tests.test_judge import TABLE_P311

THUNDER_JOLT = 1


def full(state):
    return state_to_dict(state, format_version=4)


def board(side=T, *, bench=(PONYTA,), their_bench=(GROWLITHE,), prizes=6, their_prizes=6, pikachu_damage=30,
          defender=RATTATA, hand=(), current_player=0, turn_number=3):
    state = build_test_state([
        {"active": {"card": PIKACHU, "energy": [LIGHTNING, FIRE], "damage": pikachu_damage}, "bench": list(bench),
         "prizes": prizes, "hand": list(hand)},
        {"active": defender, "bench": list(their_bench), "prizes": their_prizes},
    ], current_player=current_player, turn_number=turn_number)
    return with_coin_results(state, side)


def jolt(state):
    start = len(state.log)
    new = apply_command(state, UseAttack(0, THUNDER_JOLT))
    return new, [dict(e) for e in new.log[start:]]


def answer_all(state, choose=lambda d: d.options[0]):
    """残りの決定（サイド・バトル場に出す）に、決まった選び方で答える。答えた決定の (種類, プレイヤー) の並びも返す。"""
    answered = []
    while state.decision is not None:
        d = state.decision
        answered.append((d.kind, d.player))
        state = apply_command(state, ResolveDecision(d.player, d.id, (choose(d),)))
        assert check_invariants(state) == []
    return state, answered


class BothKnockedOutTest(unittest.TestCase):
    def test_full_sequence(self):
        state = board()
        pikachu, rattata = state.players[0].active, state.players[1].active
        state, events = jolt(state)
        kinds = [e["kind"] for e in events]
        self.assertEqual(kinds[:6], ["attack", "damage", "coin_flip", "damage", "knock_out", "knock_out"])
        ko = [e for e in events if e["kind"] == "knock_out"]
        self.assertEqual([(e["player"], e["pokemon"], e["simultaneous"]) for e in ko], [(1, rattata.card, True), (0, pikachu.card, True)])
        # 両方のバトル場が空のまま、サイドを取る決定を待つ（ほかの段階ではありえない形。不変条件は満たす）
        self.assertEqual((state.players[0].active, state.players[1].active), (None, None))
        self.assertIsNone(state.find_pokemon(pikachu.pokemon_id))
        self.assertIsNone(state.find_pokemon(rattata.pokemon_id))
        self.assertEqual(check_invariants(state), [])
        state, answered = answer_all(state)
        # サイド: 番のプレイヤー → 相手（正規化した順番。p.325）。バトル場: 番でないプレイヤー → 番のプレイヤー（pp.323〜324）
        self.assertEqual(answered, [("take_prize", 0), ("take_prize", 1), ("promote_active", 1), ("promote_active", 0)])
        self.assertEqual((len(state.players[0].prizes), len(state.players[1].prizes)), (5, 5))
        self.assertEqual((state.phase, state.current_player, state.turn_number), (Phase.MAIN, 1, 4))
        self.assertEqual(state.players[0].discard.count(pikachu.card), 1)
        self.assertEqual(state.players[1].discard.count(rattata.card), 1)

    def test_heads_only_the_opponent(self):
        state, events = jolt(board(H))
        ko = [e for e in events if e["kind"] == "knock_out"]
        self.assertEqual([e["player"] for e in ko], [1])
        self.assertNotIn("simultaneous", ko[0])
        state, answered = answer_all(state)
        self.assertEqual(answered, [("take_prize", 0), ("promote_active", 1)])

    def test_only_self(self):
        state, events = jolt(board(T, defender=GROWLITHE))
        self.assertEqual([e["player"] for e in events if e["kind"] == "knock_out"], [0])
        state, answered = answer_all(state)
        self.assertEqual(answered, [("take_prize", 1), ("promote_active", 0)])
        self.assertEqual((len(state.players[0].prizes), len(state.players[1].prizes)), (6, 5))

    def test_neither(self):
        state, events = jolt(board(T, pikachu_damage=20, defender=GROWLITHE))
        self.assertNotIn("knock_out", [e["kind"] for e in events])
        self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 1))

    def test_attached_cards_go_with_each_pokemon(self):
        """プラスパワー（ピカチュウ）とディフェンダー（相手。相手の番に使った）は、それぞれのきぜつでトラッシュする（p.323）。"""
        state = build_test_state([
            {"active": {"card": PIKACHU, "energy": [LIGHTNING, FIRE], "damage": 20}, "bench": [PONYTA], "hand": [PLUSPOWER]},
            {"active": {"card": GROWLITHE, "damage": 20}, "bench": [RATTATA], "hand": [DEFENDER]},
        ], current_player=1, turn_number=4)
        defender = state.players[1].hand[0]
        state = apply_command(state, PlayTrainer(1, defender))
        state = apply_command(state, ResolveDecision(1, state.decision.id, (state.players[1].active.pokemon_id,)))
        state = apply_command(state, EndTurn(1))
        pluspower = next(u for u in state.players[0].hand if state.cards[u].card_id == PLUSPOWER)
        state = apply_command(state, PlayTrainer(0, pluspower))
        state, events = jolt(with_coin_results(state, T))
        # 相手: 30 + 10 - 20 = 20 → ガーディ（HP60、ダメージ 20）は 40。きぜつしない
        self.assertNotIn(1, [e["player"] for e in events if e["kind"] == "knock_out"])
        # 自分: 10 + 10 = 20 → ピカチュウ（HP40、ダメージ 20）は 40 できぜつ。プラスパワーもいっしょにトラッシュ
        ko = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual((ko["player"], ko["discarded_trainers"]), (0, (pluspower,)))
        state, _ = answer_all(state)
        self.assertEqual(state.players[0].discard.count(pluspower), 1)  # 番の終わりに 2 回目のトラッシュはしない
        self.assertEqual([t.card for t in state.players[1].active.trainers], [])  # ディフェンダーは相手の番の終わり（今）にトラッシュ
        self.assertEqual(state.players[1].discard.count(defender), 1)


class PrizeOrderTest(unittest.TestCase):
    """同時のきぜつで両方がサイドを取る順番は、番のプレイヤーが決める（p.325）。エンジンは番のプレイヤーからに正規化する。
    どちらの順番でも、選べるもの・結果が同じことを、順番を入れ替えて確かめる（エンジンの内部の関数を直接呼ぶ）。"""

    def finish(self, order):
        state, _ = jolt(board())
        state = state.clone()
        state.decision = None
        flow._next_prize_or_judge(Resolution(state), tuple(order), None, ())  # v0.16b: 解決の基盤（v0.15 までは engine._next_prize_or_judge）
        options = []
        while state.decision is not None:
            d = state.decision
            options.append((d.kind, d.player, d.options))
            state = apply_command(state, ResolveDecision(d.player, d.id, (d.options[-1] if d.kind == "take_prize" else d.options[0],)))
        return state, options

    def test_order_does_not_change_the_result(self):
        normal, normal_options = self.finish((0, 1))
        swapped, swapped_options = self.finish((1, 0))
        self.assertEqual(sorted(normal_options[:2]), sorted(swapped_options[:2]))  # どちらが先でも、選べるサイドの位置は同じ
        for key in ("players", "phase", "turn_number", "current_player", "result", "rng_state_sha256"):
            self.assertEqual(full(normal)[key], full(swapped)[key], key)


class PrizeAndPromotionDecisionTest(unittest.TestCase):
    """サイド・バトル場に出す決定を待つ途中の状態では、ほかの操作は通らない。決定する人も順番も決まっている。"""

    def assert_rejected(self, state, command, code, error=EngineError):
        before, fingerprint = full(state), rng_fingerprint(state.rng)
        with self.assertRaises(error) as ctx:
            apply_command(state, command)
        self.assertEqual(ctx.exception.code, code, command)
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))

    def test_intermediate_states(self):
        state, _ = jolt(board())
        d = state.decision
        self.assertEqual((d.kind, d.player), ("take_prize", 0))
        for command, code in ((UseAttack(0, THUNDER_JOLT), "WRONG_PHASE"), (EndTurn(0), "WRONG_PHASE"),
                              (Retreat(0, (), 0), "WRONG_PHASE"), (TakePrize(1, 0), "NOT_YOUR_DECISION"),
                              (ResolveDecision(1, d.id, (0,)), "NOT_YOUR_DECISION"), (ResolveDecision(0, d.id + 1, (0,)), "WRONG_DECISION"),
                              (ResolveDecision(0, d.id, (6,)), "INVALID_CHOICE")):
            with self.subTest(command=command):
                self.assert_rejected(state, command, code)
        state = apply_command(state, TakePrize(0, 0))
        # 二度目は通らない（今の決定は相手のもの）。2 枚目も取れない（きぜつさせたのは 1 匹）
        self.assert_rejected(state, ResolveDecision(0, d.id, (0,)), "NOT_YOUR_DECISION")
        self.assert_rejected(state, TakePrize(0, 0), "NOT_YOUR_DECISION")
        self.assert_rejected(state, ResolveDecision(1, d.id, (0,)), "WRONG_DECISION")  # 古い決定の番号
        state = apply_command(state, TakePrize(1, 0))
        self.assertEqual((state.decision.kind, state.decision.player), ("promote_active", 1))
        self.assert_rejected(state, PromoteActive(0, state.players[0].bench[0].card), "NOT_YOUR_DECISION")  # 番のプレイヤーは後
        self.assert_rejected(state, EndTurn(1), "WRONG_PHASE")
        state = apply_command(state, PromoteActive(1, state.players[1].bench[0].card))
        self.assertEqual((state.decision.kind, state.decision.player), ("promote_active", 0))
        self.assertIsNotNone(state.players[1].active)  # 番のプレイヤーは、相手が出したポケモンを見てから出す

    def test_no_randomness_after_the_coin(self):
        state, _ = jolt(board())
        fingerprint = rng_fingerprint(state.rng)
        state, _ = answer_all(state)
        self.assertEqual(rng_fingerprint(state.rng), fingerprint)


class WinTableTest(unittest.TestCase):
    """同時のきぜつのあとの勝ち負け（p.311 の表・本文。すべてのサイドを取ってから判定する）。"""

    def outcome(self, **kwargs):
        state, _ = jolt(board(**kwargs))
        state, answered = answer_all(state)
        return state, answered

    def assert_result(self, state, outcome, winner, conditions):
        self.assertEqual((state.result.outcome, state.result.winner, set(state.result.conditions)), (outcome, winner, set(conditions)))
        self.assertEqual(state.phase, Phase.GAME_OVER if outcome == "win" else Phase.SUDDEN_DEATH)
        self.assertEqual(check_invariants(state), [])

    def test_attacker_takes_the_last_prize(self):
        """番のプレイヤーだけが最後のサイド: 番のプレイヤーの勝ち（p.311 本文「サイドカードを取り終えた」。表にない 1 条件だけの
        場合）。相手がサイドを取ってから判定する。"""
        state, answered = self.outcome(prizes=1)
        self.assertEqual(answered, [("take_prize", 0), ("take_prize", 1)])
        self.assert_result(state, "win", 0, [(0, "ALL_PRIZES_TAKEN")])
        self.assertEqual(len(state.players[1].prizes), 5)

    def test_opponent_takes_the_last_prize(self):
        """相手だけが最後のサイド（ピカチュウの自分へのダメージのぶん）: 相手の勝ち（p.311 本文。1 条件だけの場合）。"""
        state, _ = self.outcome(their_prizes=1)
        self.assert_result(state, "win", 1, [(1, "ALL_PRIZES_TAKEN")])

    def test_both_take_the_last_prize(self):
        """両方が同時にサイドを取り終えた: サドン・デス（p.311）。延長戦は未実装なので、対戦を止める。"""
        state, _ = self.outcome(prizes=1, their_prizes=1)
        self.assert_result(state, "sudden_death", None, [(0, "ALL_PRIZES_TAKEN"), (1, "ALL_PRIZES_TAKEN")])
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, EndTurn(1))
        self.assertEqual(ctx.exception.code, "SUDDEN_DEATH_NOT_IMPLEMENTED")

    def test_one_side_cannot_field(self):
        state, answered = self.outcome(bench=())
        self.assertEqual(answered, [("take_prize", 0), ("take_prize", 1)])  # 判定のあとはバトル場に出さない
        self.assert_result(state, "win", 1, [(1, "OPPONENT_CANNOT_FIELD_ACTIVE")])
        state, _ = self.outcome(their_bench=())
        self.assert_result(state, "win", 0, [(0, "OPPONENT_CANNOT_FIELD_ACTIVE")])

    def test_both_cannot_field(self):
        """両方とも控えポケモンが出せない: サドン・デス（p.311 本文、p.324）。"""
        state, _ = self.outcome(bench=(), their_bench=())
        self.assert_result(state, "sudden_death", None, [(0, "OPPONENT_CANNOT_FIELD_ACTIVE"), (1, "OPPONENT_CANNOT_FIELD_ACTIVE")])

    def test_both_last_prizes_and_one_cannot_field(self):
        """両方がサイドを取り終え、相手が出せない: 番のプレイヤーの勝ち（表 4 行目）。逆は負け（表 7 行目）。"""
        state, _ = self.outcome(prizes=1, their_prizes=1, their_bench=())
        self.assert_result(state, "win", 0, [(0, "ALL_PRIZES_TAKEN"), (1, "ALL_PRIZES_TAKEN"), (0, "OPPONENT_CANNOT_FIELD_ACTIVE")])
        state, _ = self.outcome(prizes=1, their_prizes=1, bench=())
        self.assert_result(state, "win", 1, [(0, "ALL_PRIZES_TAKEN"), (1, "ALL_PRIZES_TAKEN"), (1, "OPPONENT_CANNOT_FIELD_ACTIVE")])

    def test_everything_at_once(self):
        """両方がサイドを取り終え、両方が出せない: サドン・デス（表 3 行目）。"""
        state, _ = self.outcome(prizes=1, their_prizes=1, bench=(), their_bench=())
        self.assertEqual((state.result.outcome, state.phase), ("sudden_death", Phase.SUDDEN_DEATH))

    def test_last_prize_and_own_cannot_field(self):
        """番のプレイヤーが最後のサイドを取り、自分は出せない（相手は出せる）: サドン・デス（表 1 行目）。"""
        state, _ = self.outcome(prizes=1, bench=())
        self.assert_result(state, "sudden_death", None, [(0, "ALL_PRIZES_TAKEN"), (1, "OPPONENT_CANNOT_FIELD_ACTIVE")])

    def test_every_row_of_the_table(self):
        """p.311 の表の 9 行が、同時のきぜつのあとにすべて起こる（表は tests/test_judge.py の写し）。

        あなた = 番のプレイヤー 0。「サイドを取った」は残りのサイドを 1 枚にしておく、「出せない」はベンチを空にしておく。
        """
        expected = {"サドン・デス": ("sudden_death", None), "あなたの勝ち": ("win", 0), "あなたの負け": ("win", 1)}
        for you_prizes, opp_prizes, you_cannot, opp_cannot, outcome in TABLE_P311:
            row = (you_prizes, opp_prizes, you_cannot, opp_cannot)
            with self.subTest(row=row):
                state, answered = self.outcome(prizes=1 if you_prizes else 6, their_prizes=1 if opp_prizes else 6,
                                               bench=() if you_cannot else (PONYTA,),
                                               their_bench=() if opp_cannot else (GROWLITHE,))
                self.assertEqual(answered, [("take_prize", 0), ("take_prize", 1)])  # 判定はすべてのサイドを取ってから
                self.assertEqual((state.result.outcome, state.result.winner), expected[outcome])
                self.assertEqual(([not state.players[p].prizes for p in (0, 1)],
                                  [state.players[p].active is None and not state.players[p].bench for p in (0, 1)]),
                                 ([you_prizes, opp_prizes], [you_cannot, opp_cannot]))
                self.assertEqual(state.phase, Phase.GAME_OVER if outcome != "サドン・デス" else Phase.SUDDEN_DEATH)
                self.assertEqual(check_invariants(state), [])

    def test_finished_games_reject_commands(self):
        state, _ = self.outcome(prizes=1)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, EndTurn(1))
        self.assertEqual(ctx.exception.code, "GAME_OVER")


class PromotionOrderOnOpponentTurnTest(unittest.TestCase):
    """番がプレイヤー 1 でも、番でないプレイヤー（0）が先にバトル場に出す（pp.323〜324）。"""

    def test_when_player_1_attacks(self):
        state = build_test_state([
            {"active": RATTATA, "bench": [GROWLITHE]},
            {"active": {"card": PIKACHU, "energy": [LIGHTNING, FIRE], "damage": 30}, "bench": [DIGLETT]},
        ], current_player=1, turn_number=4)
        state = with_coin_results(state, T)
        state = apply_command(state, UseAttack(1, THUNDER_JOLT))
        state, answered = answer_all(state)
        self.assertEqual(answered, [("take_prize", 1), ("take_prize", 0), ("promote_active", 0), ("promote_active", 1)])
        self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 0))


if __name__ == "__main__":
    unittest.main()

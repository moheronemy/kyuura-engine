"""ポケモンチェック（v0.3a）: 番と番のあいだの自動の処理、どくのダメージ、ポケモンチェックの中のきぜつ。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES・knockout_timing）:

- p.309「3 対戦の流れ」: 先攻の番 → ポケモンチェック → 後攻の番 → ポケモンチェック …。「先攻プレイヤーの番が
  終わったら、ポケモンチェックをおこない、後攻プレイヤーの番になります」。ワザを使ったら、それによって起こる
  ことがらがすべてすんでから番は自動的に終わる
- p.323「15 ポケモンチェック」: どちらのプレイヤーの番でもない。おたがいのすべてのポケモンが対象。順番は
  1 指示されたこと → 2「どく」のダメージ（どく状態のポケモンに、それぞれ 10）→ 3 ねむり → 4 マヒ。きぜつの段階はない
- p.322: どくのダメージは弱点・抵抗力に関係なく 10。どく状態にしたポケモンのプラスパワー、そのポケモン自身の
  ディフェンダーがあっても 10。p.321「8」: どくのダメージはワザによるダメージではない
- p.323「16」: HP 以上のダメージできぜつ。きぜつしたポケモンの相手側のプレイヤーがサイドを取る。対戦ポケモンが
  きぜつしたらベンチから出す。出せなければ負け。両方の対戦ポケモンが同時にきぜつしたら「今が自分の番でない
  プレイヤー」が先に出す（pp.323〜324）。p.324: 1 つのワザ・特殊能力などによるきぜつは「同時」
- p.325「23」: 同じタイミングのことがらの順番は「そのとき番をおこなっているプレイヤー」が決める
- p.257: プラスパワーは自分の番の終わり、ディフェンダーは次の相手の番の終わりにトラッシュ（番の終わりは
  ポケモンチェックの前）

両方のプレイヤーのポケモンがどくできぜつする場合は、原典で決められない（同時か・出す順番・サイドの順番を決める
人）ので、ダメージを与える前に止める（``UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT``）。テストは止まることと状態を確かめる。
"""

import copy
import pickle
import unittest

from kyuura_engine import (
    EndTurn, EngineError, Phase, PlayTrainer, PromoteActive, ResolveDecision, Retreat, TakePrize, UnsupportedError, UseAttack,
    apply_command, check_invariants, new_game, state_to_dict,
)
from kyuura_engine.cards import pool_from_extract, read_extract
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import Poison

from tests.helpers import (
    BILL, DEFENDER, DIGLETT, FIRE, FIRE_DECK, GRASS, GROWLITHE, PLUSPOWER, PONYTA, POTION, RATTATA, WATER_FIGHTING_DECK,
    WEEDLE, build_test_state, finish_setup, with_coin_results, H,
)

RESISTS_GRASS = "TEST-GROWLITHE-RESISTS-GRASS"


def full(state):
    return state_to_dict(state, format_version=5)


def hand(state, player, card_id):
    return [u for u in state.players[player].hand if state.cards[u].card_id == card_id]


def board(p0, p1, *, current_player=0, turn_number=3, pool=None, **kwargs):
    """``p0``・``p1`` は build_test_state のプレイヤーの指定。デッキは 10 枚（番の最初のドローで負けない）。"""
    return build_test_state([p0, p1], current_player=current_player, turn_number=turn_number, pool=pool, **kwargs)


def end_turn(state):
    start = len(state.log)
    new = apply_command(state, EndTurn(state.current_player))
    return new, [dict(e) for e in new.log[start:]]


def kinds(events):
    return [e["kind"] for e in events]


def answer_all(state):
    answered = []
    while state.decision is not None:
        d = state.decision
        answered.append((d.kind, d.player))
        state = apply_command(state, ResolveDecision(d.player, d.id, (d.options[0],)))
    return state, answered


def resistant_pool():
    """ガーディの記録を写して、抵抗力を草 −30 にしたテスト専用のカード（実在しない）。"""
    extract = copy.deepcopy(read_extract())
    source = next(c for c in extract["cards"] if c["id"] == GROWLITHE)
    card = copy.deepcopy(source)
    card["id"] = RESISTS_GRASS
    card["pokemon"]["resistances"] = [{"type": "grass", "operator": "-", "value": 30}]
    extract["cards"].append(card)
    return pool_from_extract(extract)


# ---------------------------------------------------------------- いつ行うか


class TimingTest(unittest.TestCase):
    def test_after_end_turn(self):
        """ワザを使わずに番を終えても、番の終わり → ポケモンチェック → 次の番（p.309）。"""
        state = board({"active": GROWLITHE}, {"active": {"card": RATTATA, "poison": 10}})
        new, events = end_turn(state)
        self.assertEqual(kinds(events), ["end_turn_without_attack", "turn_end", "pokemon_check", "poison_damage", "turn_start", "draw"])
        self.assertEqual((new.turn_number, new.current_player), (4, 1))

    def test_after_an_attack(self):
        """ワザで番が終わったときも同じ。ワザのダメージ（damage）と、どくのダメージ（poison_damage）は別のイベント。"""
        state = board({"active": {"card": GROWLITHE, "energy": [FIRE, FIRE]}}, {"active": {"card": PONYTA, "poison": 10}})
        new = apply_command(state, UseAttack(0, 0))
        events = [dict(e) for e in new.log]
        self.assertEqual(kinds(events)[:5], ["attack", "damage", "turn_end", "pokemon_check", "poison_damage"])
        self.assertEqual((events[1]["amount"], events[4]["amount"], new.players[1].active.damage), (20, 10, 30))

    def test_after_a_trainer(self):
        """トレーナーを使ってから番を終えても、ポケモンチェックは 1 回（マサキで引いても変わらない）。"""
        state = board({"active": GROWLITHE, "hand": [BILL]}, {"active": {"card": RATTATA, "poison": 10}})
        state = apply_command(state, PlayTrainer(0, hand(state, 0, BILL)[0]))
        new, events = end_turn(state)
        self.assertEqual(kinds(events).count("pokemon_check"), 1)
        self.assertEqual(kinds(events).count("poison_damage"), 1)

    def test_first_players_first_turn(self):
        """先攻の最初の番のあとにもポケモンチェックをする（p.309 に例外はない）。正式な対戦開始から。"""
        state = finish_setup(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 1))
        self.assertEqual(state.turn_number, 1)
        new, events = end_turn(state)
        self.assertEqual(kinds(events)[:4], ["end_turn_without_attack", "turn_end", "pokemon_check", "turn_start"])

    def test_without_poison_the_log_is_the_same_as_v0_2f(self):
        """どく状態のポケモンがいなければ、ポケモンチェックのログは ``pokemon_check`` だけ（v0.1〜v0.2f と同じ）。"""
        new, events = end_turn(board({"active": GROWLITHE}, {"active": RATTATA}))
        self.assertEqual(kinds(events), ["end_turn_without_attack", "turn_end", "pokemon_check", "turn_start", "draw"])

    def test_exactly_one_check_between_turns(self):
        state = board({"active": GROWLITHE}, {"active": {"card": GROWLITHE, "poison": 10}})
        for _ in range(4):
            state, _ = end_turn(state)
        log = kinds([dict(e) for e in state.log])
        self.assertEqual((log.count("turn_end"), log.count("pokemon_check"), log.count("poison_damage"), log.count("turn_start")), (4, 4, 4, 4))
        self.assertEqual(state.players[1].active.damage, 40)

    def test_draw_comes_after_the_check(self):
        """次の番のドローは、ポケモンチェックが終わってから（p.309）。"""
        _, events = end_turn(board({"active": GROWLITHE}, {"active": {"card": RATTATA, "poison": 10}}))
        self.assertLess(kinds(events).index("poison_damage"), kinds(events).index("draw"))


# ---------------------------------------------------------------- どくのダメージ


class PoisonDamageTest(unittest.TestCase):
    def check_damage(self, state):
        _, events = end_turn(state)
        return [(e["player"], e["amount"], e["total_damage"]) for e in events if e["kind"] == "poison_damage"]

    def test_both_players_poisoned(self):
        """おたがいのすべてのポケモンが対象（p.323）。それぞれ 10。ログは番を終えたプレイヤーの場から。"""
        state = board({"active": {"card": GROWLITHE, "poison": 10}}, {"active": {"card": PONYTA, "damage": 10, "poison": 10}})
        self.assertEqual(self.check_damage(state), [(0, 10, 10), (1, 10, 20)])
        state = board({"active": {"card": GROWLITHE, "poison": 10}}, {"active": {"card": PONYTA, "poison": 10}}, current_player=1, turn_number=4)
        self.assertEqual(self.check_damage(state), [(1, 10, 10), (0, 10, 10)])

    def test_only_one_side(self):
        state = board({"active": {"card": GROWLITHE, "poison": 10}}, {"active": PONYTA})
        self.assertEqual(self.check_damage(state), [(0, 10, 10)])

    def test_weakness_and_resistance_do_not_apply(self):
        """弱点・抵抗力に関係なく 10（p.322）。ディグダ（弱点 草）、テスト専用の草に抵抗力のあるポケモン。"""
        self.assertEqual(self.check_damage(board({"active": GROWLITHE}, {"active": {"card": DIGLETT, "poison": 10}})), [(1, 10, 10)])
        pool = resistant_pool()
        state = board({"active": WEEDLE}, {"active": {"card": RESISTS_GRASS, "poison": 10}}, pool=pool)
        self.assertEqual(self.check_damage(state), [(1, 10, 10)])

    def test_defender_on_the_poisoned_pokemon_does_not_reduce(self):
        """どく状態のポケモンについているディフェンダー（相手の次の番の終わりまで残る）があっても 10（p.322）。"""
        state = board({"active": {"card": GROWLITHE, "poison": 10}, "hand": [DEFENDER]}, {"active": WEEDLE})
        state = apply_command(state, PlayTrainer(0, hand(state, 0, DEFENDER)[0]))
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].active.pokemon_id,)))
        state, events = end_turn(state)
        self.assertEqual(len(state.players[0].active.trainers), 1)  # 次の相手の番の終わりまで残っている
        self.assertEqual([e["amount"] for e in events if e["kind"] == "poison_damage"], [10])
        self.assertNotIn("modifiers", next(e for e in events if e["kind"] == "poison_damage"))

    def test_pluspower_is_gone_before_the_check(self):
        """プラスパワーは使った番の終わりにトラッシュする（p.257）。番の終わり → ポケモンチェックの順なので、
        どく状態にしたポケモンのプラスパワーはポケモンチェックのときにはない。どくのダメージは 10（p.322）。"""
        state = board({"active": {"card": WEEDLE, "energy": [GRASS]}, "hand": [PLUSPOWER]}, {"active": GROWLITHE})
        state = apply_command(state, PlayTrainer(0, hand(state, 0, PLUSPOWER)[0]))
        state = with_coin_results(state, H)
        start = len(state.log)
        state = apply_command(state, UseAttack(0, 0))
        events = [dict(e) for e in state.log[start:]]
        order = kinds(events)
        self.assertLess(order.index("discard_attached_trainer"), order.index("turn_end"))
        self.assertLess(order.index("turn_end"), order.index("pokemon_check"))
        damage = next(e for e in events if e["kind"] == "damage")
        self.assertEqual(damage["amount"], 20)  # ワザのダメージにはプラスパワー
        self.assertEqual([e["amount"] for e in events if e["kind"] == "poison_damage"], [10])

    def test_defender_expiring_this_turn_is_discarded_first(self):
        """期限の来たディフェンダーは番の終わりにトラッシュしてから、ポケモンチェック（p.257・p.309・p.323）。"""
        state = board({"active": GROWLITHE}, {"active": {"card": RATTATA, "poison": 10}, "hand": [DEFENDER]},
                      current_player=1, turn_number=4)
        state = apply_command(state, PlayTrainer(1, hand(state, 1, DEFENDER)[0]))
        state = apply_command(state, ResolveDecision(1, state.decision.id, (state.players[1].active.pokemon_id,)))
        state, _ = end_turn(state)  # プレイヤー 1 の番（4）の終わり: ディフェンダーは残る
        state, events = end_turn(state)  # プレイヤー 0 の番（5）の終わり: ディフェンダーをトラッシュしてからチェック
        order = kinds(events)
        self.assertLess(order.index("discard_attached_trainer"), order.index("turn_end"))
        self.assertLess(order.index("pokemon_check"), order.index("poison_damage"))
        self.assertEqual(state.players[1].active.damage, 20)

    def test_hp_thresholds(self):
        """HP 未満なら残り、HP ちょうどできぜつ（p.323）。HP をこえる量（テスト専用のどくのダメージ 20）でもきぜつ。"""
        for damage, poison_damage, knocked in ((10, 10, False), (20, 10, True), (30, 20, True)):
            with self.subTest(damage=damage, poison=poison_damage):
                state = board({"active": GROWLITHE}, {"active": {"card": RATTATA, "damage": damage, "poison": poison_damage}, "bench": [PONYTA]})
                state, events = end_turn(state)
                self.assertEqual("knock_out" in kinds(events), knocked)

    def test_potion_then_poison(self):
        """きずぐすりでとりのぞいたあとも、どく状態なのでポケモンチェックで 10（p.254・p.322）。"""
        state = board({"active": {"card": GROWLITHE, "damage": 30, "poison": 10}, "hand": [POTION]}, {"active": WEEDLE})
        state = apply_command(state, PlayTrainer(0, hand(state, 0, POTION)[0]))
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].active.pokemon_id,)))
        state, _ = end_turn(state)
        self.assertEqual(state.players[0].active.damage, 20)

    def test_benched_pokemon_take_no_poison_damage(self):
        """ベンチのポケモンは特殊状態にならない（p.322）。にげてベンチに戻ったら、ポケモンチェックでダメージを受けない。"""
        state = board({"active": {"card": GROWLITHE, "energy": [FIRE], "poison": 10}, "bench": [PONYTA]}, {"active": WEEDLE})
        state = apply_command(state, Retreat(0, (state.players[0].active.energy[0],), state.players[0].bench[0].card))
        state, events = end_turn(state)
        self.assertNotIn("poison_damage", kinds(events))


# ---------------------------------------------------------------- ポケモンチェックの中のきぜつ


class KnockOutInCheckTest(unittest.TestCase):
    def test_next_players_pokemon(self):
        """番を終えたプレイヤー（0）の相手（1）のポケモンがきぜつ: プレイヤー 0 がサイドを取り、1 が出してから、1 の番（p.323）。"""
        state = board({"active": GROWLITHE}, {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA]})
        rattata = state.players[1].active
        state, events = end_turn(state)
        self.assertEqual(kinds(events)[-2:], ["poison_damage", "knock_out"])
        knock_out = events[-1]
        self.assertEqual((knock_out["player"], knock_out["pokemon"], knock_out["timing"]), (1, rattata.card, "pokemon_check"))
        self.assertNotIn("simultaneous", knock_out)
        self.assertEqual((state.phase, state.decision.player, state.decision.context_value("then")), (Phase.TAKE_PRIZE, 0, "next_turn"))
        self.assertEqual((state.turn_number, state.current_player), (3, 0))  # 次の番はまだ始まっていない
        self.assertEqual(check_invariants(state), [])
        state, answered = answer_all(state)
        self.assertEqual(answered, [("take_prize", 0), ("promote_active", 1)])
        self.assertEqual((state.phase, state.turn_number, state.current_player), (Phase.MAIN, 4, 1))
        log = kinds([dict(e) for e in state.log])
        self.assertEqual((log.count("turn_end"), log.count("pokemon_check"), log.count("turn_start")), (1, 1, 1))
        self.assertEqual(log[-4:], ["take_prize", "promote_active", "turn_start", "draw"])

    def test_own_pokemon(self):
        """番を終えたプレイヤー（0）自身のポケモンがきぜつ: サイドを取るのは相手（1）。番のプレイヤーに固定しない。"""
        state = board({"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA]}, {"active": GROWLITHE})
        state, _ = end_turn(state)
        state, answered = answer_all(state)
        self.assertEqual(answered, [("take_prize", 1), ("promote_active", 0)])
        self.assertEqual((len(state.players[0].prizes), len(state.players[1].prizes)), (6, 5))
        self.assertEqual((state.turn_number, state.current_player), (4, 1))

    def test_no_bench_loses(self):
        """代わりを出せないプレイヤーの負け（p.311・p.323）。対戦は終わり、次の番は来ない。"""
        state = board({"active": GROWLITHE}, {"active": {"card": RATTATA, "damage": 20, "poison": 10}})
        state, _ = end_turn(state)
        state, answered = answer_all(state)
        self.assertEqual(answered, [("take_prize", 0)])
        self.assertEqual((state.phase, state.result.winner, state.result.conditions), (Phase.GAME_OVER, 0, ((0, "OPPONENT_CANNOT_FIELD_ACTIVE"),)))
        self.assertEqual(kinds([dict(e) for e in state.log])[-1], "game_end")
        self.assertEqual(state.turn_number, 3)
        self.assertEqual(check_invariants(state), [])

    def test_last_prize_wins(self):
        state = board({"active": GROWLITHE, "prizes": 1}, {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA]})
        state, _ = end_turn(state)
        state, answered = answer_all(state)
        self.assertEqual(answered, [("take_prize", 0)])
        self.assertEqual((state.phase, state.result.winner, state.result.conditions), (Phase.GAME_OVER, 0, ((0, "ALL_PRIZES_TAKEN"),)))

    def test_own_last_prize_goes_to_the_opponent(self):
        """どくで自分のポケモンがきぜつし、相手が最後のサイドを取る: 相手の勝ち（自分の番のあとでも）。"""
        state = board({"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA]}, {"active": GROWLITHE, "prizes": 1})
        state, _ = end_turn(state)
        state, _ = answer_all(state)
        self.assertEqual((state.result.winner, state.result.conditions), (1, ((1, "ALL_PRIZES_TAKEN"),)))

    def test_attached_trainers_go_with_the_pokemon(self):
        """ついているディフェンダーは、きぜつしたポケモンといっしょにトラッシュ（p.323）。期限の処理と重ならない。"""
        state = board({"active": GROWLITHE}, {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA], "hand": [DEFENDER]},
                      current_player=1, turn_number=4)
        defender = hand(state, 1, DEFENDER)[0]
        state = apply_command(state, PlayTrainer(1, defender))
        state = apply_command(state, ResolveDecision(1, state.decision.id, (state.players[1].active.pokemon_id,)))
        state, events = end_turn(state)  # 番 4 の終わり: 20 + 10 = 30 できぜつ（ディフェンダーは番 5 まで）
        knock_out = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual(knock_out["discarded_trainers"], (defender,))
        state, _ = answer_all(state)
        self.assertEqual(state.players[1].discard.count(defender), 1)
        state, events = end_turn(state)
        self.assertNotIn("discard_attached_trainer", kinds(events))

    def test_deck_out_after_the_check(self):
        """ポケモンチェックの交代のあとに次の番が始まり、山札がなければその時点で負け（p.309）。"""
        state = board({"active": GROWLITHE}, {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA], "deck": []})
        state, _ = end_turn(state)
        state, answered = answer_all(state)
        self.assertEqual(answered, [("take_prize", 0), ("promote_active", 1)])
        self.assertEqual((state.phase, state.result.winner, state.turn_number), (Phase.GAME_OVER, 0, 4))
        self.assertEqual(kinds([dict(e) for e in state.log])[-3:], ["turn_start", "deck_out", "game_end"])

    def test_decisions_in_the_check(self):
        """決定を待つ間は、決定に答えるコマンドだけ。答える人も選べるものも決まっている。拒否は状態も乱数も変えない。"""
        state = board({"active": GROWLITHE, "hand": [BILL]}, {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA, DIGLETT]})
        state, _ = end_turn(state)

        def rejected(command, code):
            before, fingerprint = full(state), rng_fingerprint(state.rng)
            with self.assertRaises(EngineError) as ctx:
                apply_command(state, command)
            self.assertEqual(ctx.exception.code, code, command)
            self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))

        d = state.decision
        for command, code in ((EndTurn(0), "WRONG_PHASE"), (EndTurn(1), "WRONG_PHASE"), (UseAttack(0, 0), "WRONG_PHASE"),
                              (PlayTrainer(0, hand(state, 0, BILL)[0]), "WRONG_PHASE"), (TakePrize(1, 0), "NOT_YOUR_DECISION"),
                              (ResolveDecision(0, d.id + 1, (0,)), "WRONG_DECISION"), (ResolveDecision(0, d.id, (6,)), "INVALID_CHOICE")):
            with self.subTest(command=command):
                rejected(command, code)
        state = apply_command(state, TakePrize(0, 0))
        d = state.decision
        self.assertEqual((d.kind, d.player, d.context_value("then")), ("promote_active", 1, "next_turn"))
        for command, code in ((PromoteActive(0, state.players[0].active.card), "NOT_YOUR_DECISION"),
                              (ResolveDecision(1, d.id, (state.players[0].active.pokemon_id,)), "INVALID_CHOICE"),
                              (ResolveDecision(1, d.id, (999,)), "INVALID_CHOICE"), (EndTurn(1), "WRONG_PHASE")):
            with self.subTest(command=command):
                rejected(command, code)
        diglett = state.players[1].bench[1]
        state = apply_command(state, ResolveDecision(1, d.id, (diglett.pokemon_id,)))
        self.assertEqual((state.players[1].active.pokemon_id, state.phase, state.current_player), (diglett.pokemon_id, Phase.MAIN, 1))

    def test_copies_during_the_check_give_the_same_result(self):
        state = board({"active": GROWLITHE}, {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA]})
        state, _ = end_turn(state)
        results = []
        for copied in (state, state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            results.append(full(answer_all(copied)[0]))
        self.assertTrue(all(r == results[0] for r in results))

    def test_formats_during_the_check(self):
        """ポケモンチェックの中の決定は、形式 2 以上で書き出せる（決定の context に続きがある）。形式 1 は表せないので拒否。"""
        state = board({"active": GROWLITHE}, {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA]})
        state, _ = end_turn(state)
        with self.assertRaises(ValueError):
            state_to_dict(state, format_version=1)
        for version in (2, 3, 4, 5):
            data = state_to_dict(state, format_version=version)
            self.assertEqual(data["decision"]["context"]["then"], "next_turn")
        # ワザのあとの決定（v0.2f と同じ）は形式 1 でも書き出せる
        attacked = apply_command(board({"active": {"card": GROWLITHE, "energy": [FIRE, FIRE]}},
                                       {"active": {"card": RATTATA, "damage": 10}, "bench": [PONYTA]}), UseAttack(0, 0))
        self.assertIsNone(attacked.decision.context_value("then"))
        state_to_dict(attacked, format_version=1)


# ---------------------------------------------------------------- 両方のポケモンがどくできぜつ（原典で決められない）


class DoubleKnockOutTest(unittest.TestCase):
    """両方のプレイヤーのポケモンが同じポケモンチェックの「どく」できぜつする場合（p.322〜325 で決められない）。"""

    def both(self, *, bench0=(PONYTA,), bench1=(PONYTA,), prizes0=6, prizes1=6, current_player=0):
        return board({"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": list(bench0), "prizes": prizes0},
                     {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": list(bench1), "prizes": prizes1},
                     current_player=current_player, turn_number=3 if current_player == 0 else 4)

    def test_halts_before_the_damage(self):
        for name, kwargs in (("両方ベンチあり", {}), ("片方だけベンチあり", {"bench1": ()}), ("両方ベンチなし", {"bench0": (), "bench1": ()}),
                             ("両方が最後のサイド", {"prizes0": 1, "prizes1": 1}), ("最後のサイドと出せない", {"prizes0": 1, "bench0": ()}),
                             ("番がプレイヤー 1", {"current_player": 1})):
            with self.subTest(name):
                state = self.both(**kwargs)
                damages = [p.active.damage for p in state.players]
                new, events = end_turn(state)
                self.assertEqual(kinds(events)[-3:], ["turn_end", "pokemon_check", "halted"])
                self.assertEqual((new.phase, new.halt.code, new.result), (Phase.HALTED, "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT", None))
                self.assertEqual([p.active.damage for p in new.players], damages)  # どくのダメージを与える前
                self.assertEqual([len(p.prizes) for p in new.players], [kwargs.get("prizes0", 6), kwargs.get("prizes1", 6)])
                self.assertNotIn(new.phase, (Phase.GAME_OVER, Phase.SUDDEN_DEATH))
                self.assertEqual(check_invariants(new), [])
                with self.assertRaises(UnsupportedError) as ctx:
                    apply_command(new, EndTurn(1 - state.current_player))
                self.assertEqual(ctx.exception.code, "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT")

    def test_one_knocked_out_and_one_survives(self):
        """両方どく状態でも、きぜつするのが片方だけなら決まる。両方に 10 を与えてから、きぜつを処理する。"""
        state = board({"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA]},
                      {"active": {"card": GROWLITHE, "damage": 20, "poison": 10}, "bench": [PONYTA]})
        state, events = end_turn(state)
        self.assertEqual([(e["player"], e["total_damage"]) for e in events if e["kind"] == "poison_damage"], [(0, 30), (1, 30)])
        self.assertEqual([e["player"] for e in events if e["kind"] == "knock_out"], [0])
        state, answered = answer_all(state)
        self.assertEqual(answered, [("take_prize", 1), ("promote_active", 0)])
        self.assertEqual((state.players[1].active.damage, state.players[1].active.conditions.poison), (30, Poison(10)))


# ---------------------------------------------------------------- 番の進行の不変条件


class ProgressInvariantTest(unittest.TestCase):
    def played(self):
        state = board({"active": GROWLITHE}, {"active": {"card": RATTATA, "poison": 10}})
        for _ in range(2):
            state, _ = end_turn(state)
        return state

    def with_log(self, state, log):
        broken = state.clone()
        broken.log = tuple(log)
        return check_invariants(broken)

    def test_valid(self):
        self.assertEqual(check_invariants(self.played()), [])

    def test_a_second_check_is_detected(self):
        state = self.played()
        log = list(state.log)
        i = max(j for j, e in enumerate(log) if e["kind"] == "pokemon_check")
        self.assertTrue(self.with_log(state, log[:i + 1] + [log[i]] + log[i + 1:]))

    def test_a_missing_check_is_detected(self):
        state = self.played()
        log = list(state.log)
        i = max(j for j, e in enumerate(log) if e["kind"] == "pokemon_check")
        self.assertTrue(self.with_log(state, log[:i] + log[i + 1:]))

    def test_check_before_turn_end_is_detected(self):
        state = self.played()
        log = list(state.log)
        i = max(j for j, e in enumerate(log) if e["kind"] == "pokemon_check")
        log[i - 1], log[i] = log[i], log[i - 1]
        self.assertTrue(self.with_log(state, log))

    def test_turn_end_in_the_middle_of_a_turn_is_detected(self):
        state = self.played()
        self.assertTrue(self.with_log(state, list(state.log) + [{"kind": "turn_end", "turn": state.turn_number}]))

    def test_check_decision_must_be_after_the_check(self):
        """ポケモンチェックの中の決定（続きが次の番）なのに、今の番のあとに番の終わり・ポケモンチェックがなければ壊れている。"""
        state = board({"active": {"card": RATTATA, "damage": 10, "poison": 10}, "bench": [PONYTA]}, {"active": GROWLITHE})
        state, _ = end_turn(state)  # 20。番 4（プレイヤー 1）が始まる
        state, _ = end_turn(state)  # 30 できぜつ。サイドの決定（続きは次の番）
        self.assertEqual((state.decision.kind, state.decision.context_value("then")), ("take_prize", "next_turn"))
        self.assertEqual(check_invariants(state), [])
        log = list(state.log)
        last_start = max(j for j, e in enumerate(log) if e["kind"] == "turn_start")
        tail = [e for e in log[last_start + 1:] if e["kind"] not in ("turn_end", "pokemon_check")]
        self.assertTrue(self.with_log(state, log[:last_start + 1] + tail))

    def test_wrong_continuation_is_detected(self):
        state = board({"active": GROWLITHE}, {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA]})
        state, _ = end_turn(state)
        broken = state.clone()
        d = broken.decision
        broken.decision = type(d)(d.id, d.kind, d.player, d.options, d.min_choices, d.max_choices, d.resume,
                                  (("remaining", ()), ("then", "something_else")))
        self.assertTrue(check_invariants(broken))


if __name__ == "__main__":
    unittest.main()

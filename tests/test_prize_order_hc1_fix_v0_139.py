"""v0.139（docs/prize-order-hc1-fix-v0.139.md）: 同時のきぜつでサイドを取る順番（2 章）と、HC1 の止める範囲（3 章）の修正。

サイドを取る順番: 両方がサイドを取り、どちらかのサイドにおもてのカードがあるとき、番のプレイヤーが次に取るプレイヤーを選ぶ（決定 ``prize_order``。p.325）。
どのサイドもうらなら v0.2f の正規化（番のプレイヤーから）のまま（決定を出さない）。

HC1: 「はがしてすてる」（トラッシュが条件か効果か決められない）ワザを、p.309 の手順 4 のコイン（すなかけなど・［はんこう］）があるときに使うなら、こんらん・ベイビィポケモンの
ルールのコインと同じく、宣言を受け付けずに止める（``UNRESOLVED_DISCARD_ENERGY_TIMING``。コインの前。状態・乱数・ログを変えない）。

再現の種類:
- ``LegalPrizeOrderTest``: new_game(seed=473) からの合法な操作の列（固定。seed を選び直さない）
- ``PartialFaceUpTest``・``SuddenDeathPrizeOrderTest``: 盤面を直接作った状態（``build_test_state``。おもてにするのは ``zones.reveal_prize``／ロケット団参上!を使う合法なコマンド）
- ``LegalHc1Test``: new_game(seed=0) からの合法な操作の列（ミュウツー対サンド。seed は 0 から順に試して、この操作の列が通る最初のもの）
- ``ConstructedHc1Test``: 盤面を直接作った状態から、相手の合法なワザ（すなかけ・えんまく）→ 自分のワザ。［はんこう］は補助関数だけ（HC1 のワザを使う［はんこう］のポケモンは作っていない）
"""

from __future__ import annotations

import pickle
import unittest

from kyuura_engine import (
    EngineError,
    UnsupportedError,
    apply_command,
    check_invariants,
    expand_decklist,
    new_game,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine.commands import (
    AttachEnergy,
    EndTurn,
    PlayTrainer,
    ResolveDecision,
    TakePrize,
    UseAttack,
)
from kyuura_engine.persistent import attack_coin_checks
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.resolution.programs import attack_step4_coin
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import Phase
from kyuura_engine.zones import reveal_prize
from tests.helpers import (
    ABRA,
    BASE_GASTLY,
    BLAINES_ARCANINE,
    CHARIZARD,
    FIGHTING,
    FIRE,
    HERE_COMES_TEAM_ROCKET,
    HORSEA,
    KADABRA,
    LIGHTNING,
    MAGNEMITE,
    MEWTWO,
    MISTYS_GYARADOS,
    MOLTRES,
    PSYCHIC,
    RATTATA,
    SABRINAS_ABRA,
    SANDSHREW,
    SCYTHER,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    finish_setup,
    with_coin_results,
)
from tests.test_held_cards_v0_31 import mon

SELFDESTRUCT = 1  # コイルの「じばく」（相手の対戦ポケモンに 40・自分に 40・お互いのベンチに 10）
SEED = 473  # 正規化の再検証（docs/normalization-revalidation.json の IA-PRIZE-TAKE-ORDER-SIMULTANEOUS-KO の repro）で記録した seed
DECK0 = {MAGNEMITE: 4, HERE_COMES_TEAM_ROCKET: 4, LIGHTNING: 52}
DECK1 = {RATTATA: 4, WATER: 56}


def _cid(state, uid):
    return state.cards[uid].card_id


def _attach(state, player):
    energy = next(u for u in state.players[player].hand if _cid(state, u) == LIGHTNING)
    return apply_command(state, AttachEnergy(player, energy, state.players[player].active.card))


def legal_double_knockout(*, rocket=True):
    """seed 473: 1 番 P0 雷をつける → 2 番 P1 番を終える → 3 番 P0 雷をつけ、（ロケット団参上!）→ じばく。両方のバトル場のポケモンがきぜつする。"""
    state = finish_setup(new_game(expand_decklist(DECK0), expand_decklist(DECK1), SEED), janken_winner=0)
    state = apply_command(_attach(state, 0), EndTurn(0))
    state = _attach(apply_command(state, EndTurn(1)), 0)
    if rocket:
        state = apply_command(state, PlayTrainer(0, next(u for u in state.players[0].hand if _cid(state, u) == HERE_COMES_TEAM_ROCKET)))
    return apply_command(state, UseAttack(0, SELFDESTRUCT))


def full(state):
    return state_to_dict(state, format_version=34)


def takes_seen(state, viewer):
    """``viewer`` に見えている take_prize（プレイヤー・カード（見えなければ None））。"""
    return [(e["player"], e.get("card")) for e in visible_log(state, viewer) if e.get("kind") == "take_prize"]


def answer(state, d, choice):
    new = apply_command(state, ResolveDecision(d.player, d.id, (choice,)))
    assert check_invariants(new) == [], check_invariants(new)
    return new


class LegalPrizeOrderTest(unittest.TestCase):
    """new_game からの合法な操作で、ロケット団参上!のあと両方がきぜつする（全部のサイドがおもて）。"""

    @classmethod
    def setUpClass(cls):
        cls.state = legal_double_knockout()
        cls.plain = legal_double_knockout(rocket=False)

    def test_turn_player_chooses_the_order(self):
        state = self.state
        self.assertEqual(check_invariants(state), [])
        d = state.decision
        self.assertEqual((d.kind, d.player, d.options, d.resume, state.phase), ("prize_order", 0, (0, 1), "prize_order", Phase.DECISION))
        self.assertEqual(d.context_value("remaining"), (0, 1))
        self.assertEqual(state.current_player, 0)
        # 決めるプレイヤーには選べるもの（プレイヤーの番号）だけ。相手には種類と数だけ。どちらにもカードの情報はない
        mine, theirs = observe(state, 0)["decision"], observe(state, 1)["decision"]
        self.assertEqual(mine["options"], [{"value": 0}, {"value": 1}])
        self.assertEqual(mine["meaning"], "number")
        self.assertNotIn("options", theirs)
        # まだだれもサイドを取っていない
        self.assertEqual(takes_seen(state, 0) + takes_seen(state, 1), [])

    def test_face_down_prizes_keep_the_normalized_order(self):
        """ロケット団参上!を使わない同じ対戦（すべてうら）: 決定を出さず、番のプレイヤーから（v0.2f と同じ）。後に取るプレイヤーには、先に取られたカードが見えない。"""
        state = self.plain
        d = state.decision
        self.assertEqual((d.kind, d.player, d.context_value("remaining")), ("take_prize", 0, (1,)))
        state = answer(state, d, 0)
        d = state.decision
        self.assertEqual((d.kind, d.player), ("take_prize", 1))
        self.assertEqual(takes_seen(state, 1), [(0, None)])

    def run_order(self, first, pick):
        """番のプレイヤーが ``first`` を先にする。各サイドの決定の時点で、決めるプレイヤーに見えている take_prize と相手のおもてのサイドを記録する。"""
        state = answer(self.state, self.state.decision, first)
        seen = []
        while state.decision is not None and state.decision.kind == "take_prize":
            d = state.decision
            view = observe(state, d.player)
            seen.append({"player": d.player, "takes": takes_seen(state, d.player),
                         "opponent_face_up": [c["card"] for c in view["players"][1 - d.player]["prizes"]["face_up"]]})
            state = answer(state, d, pick(state, d, view))
        return state, seen

    def test_later_player_sees_the_earlier_take(self):
        before = {p: tuple(self.state.players[p].prizes) for p in (0, 1)}
        for first in (0, 1):
            with self.subTest(first=first):
                state, seen = self.run_order(first, lambda s, d, v: 0)
                later = 1 - first
                self.assertEqual([s["player"] for s in seen], [first, later])
                self.assertEqual(seen[0]["takes"], [])  # 先に取るプレイヤーは、相手の取ったカードの情報を持たない
                taken = before[first][0]
                self.assertEqual(seen[1]["takes"], [(first, taken)])  # 後に取るプレイヤーには、先に取られたおもてのカードが見える
                self.assertNotIn(taken, seen[1]["opponent_face_up"])
                self.assertIn(taken, self.state.face_up_prizes)  # 取ったのはおもてのカード（だから見える）
                self.assertEqual(state.decision.kind, "promote_active")  # そのあとはバトル場に出す（番でないプレイヤーから。v0.2f と同じ）
                self.assertEqual(state.decision.player, 1)

    def test_information_can_change_the_later_choice(self):
        """後に取るプレイヤーが、先に取られたカードを見てから選び方を変えられる例（この seed の P1 のサイドはすべて水なので、変えられるのは P0）。
        P0 の選び方: 「P1 が取ったカードが見えていればおもてのロケット団参上!を取る、見えていなければ位置 0」。P1 を先にすると P0 はそれを見て選び、P0 を先にすると見ていない。"""
        prizes = self.state.players[0].prizes
        rocket = next(i for i, u in enumerate(prizes) if _cid(self.state, u) == HERE_COMES_TEAM_ROCKET)
        self.assertNotEqual(_cid(self.state, prizes[0]), HERE_COMES_TEAM_ROCKET, "盤面の前提: P0 のサイドの位置 0 はロケット団参上!ではない")

        def pick(state, d, view):
            if d.player == 1:
                return 0
            saw = any(player == 1 and card is not None for player, card in takes_seen(state, 0))
            return rocket if saw else 0

        hands = {}
        for first in (0, 1):
            state, _ = self.run_order(first, pick)
            hands[first] = sorted(_cid(state, u) for u in state.players[0].hand)
        self.assertNotEqual(hands[0], hands[1])
        self.assertEqual(hands[1].count(HERE_COMES_TEAM_ROCKET) - hands[0].count(HERE_COMES_TEAM_ROCKET), 1)

    def test_same_choices_give_the_same_board(self):
        """同じ位置を選べば、順番によらず場・手札・サイド・乱数は同じ（違うのはログの順番と決定の番号）。"""
        results = [self.run_order(first, lambda s, d, v: len(d.options) - 1)[0] for first in (0, 1)]
        a, b = (full(s) for s in results)
        for key in ("players", "phase", "turn_number", "current_player", "result", "rng_state_sha256", "face_up_prizes"):
            self.assertEqual(a.get(key), b.get(key), key)

    def test_invalid_answers_change_nothing(self):
        state = self.state
        d = state.decision
        for command, code in ((ResolveDecision(1, d.id, (0,)), "NOT_YOUR_DECISION"), (ResolveDecision(0, d.id + 1, (0,)), "WRONG_DECISION"),
                              (ResolveDecision(0, d.id, (2,)), "INVALID_CHOICE"), (ResolveDecision(0, d.id, ()), "INVALID_CHOICE_COUNT"),
                              (ResolveDecision(0, d.id, (0, 1)), "INVALID_CHOICE_COUNT"), (TakePrize(0, 0), "WRONG_PHASE"), (EndTurn(0), "WRONG_PHASE")):
            with self.subTest(command=command):
                before, fingerprint, log = full(state), rng_fingerprint(state.rng), len(state.log)
                with self.assertRaises(EngineError) as ctx:
                    apply_command(state, command)
                self.assertEqual(ctx.exception.code, code)
                self.assertEqual((full(state), rng_fingerprint(state.rng), len(state.log)), (before, fingerprint, log))

    def test_no_randomness_and_save_restore(self):
        state = self.state
        fingerprint = rng_fingerprint(state.rng)
        restored = pickle.loads(pickle.dumps(state))
        self.assertEqual(full(restored), full(state))
        a, _ = self.run_order(1, lambda s, d, v: 0)
        self.assertEqual(rng_fingerprint(a.rng), fingerprint)  # 順番の決定・サイドは乱数を使わない
        # 復元した状態から同じ答えで続けると、同じ結果
        b = answer(restored, restored.decision, 1)
        while b.decision is not None and b.decision.kind == "take_prize":
            b = answer(b, b.decision, 0)
        self.assertEqual(full(a), full(b))
        # 決定を待つ途中（2 人目のサイドの前）でも保存・復元できる
        first = answer(state, state.decision, 1)
        mid = answer(first, first.decision, 0)
        self.assertEqual(mid.decision.kind, "take_prize")
        self.assertEqual(full(pickle.loads(pickle.dumps(mid))), full(mid))
        self.assertEqual(state_to_dict(state, format_version=34)["decision"]["kind"], "prize_order")
        with self.assertRaises(ValueError):
            state_to_dict(state, format_version=20)  # おもてのサイドを表せない形式（v0.63 から 21 以上）


def partial_board(*, reveal_owner, reveal_position=1, prizes=(3, 3), rocket_in_hand=False):
    """盤面を直接作った状態: P0（番）のコイル（雷 2）と P1 のコラッタ。どちらもベンチに 1 匹。``reveal_owner`` のサイドの 1 枚だけをおもてにする（カードめくりゲームと同じ記録）。"""
    hand = [HERE_COMES_TEAM_ROCKET] if rocket_in_hand else []
    state = build_test_state([
        {"active": {"card": MAGNEMITE, "energy": [LIGHTNING, LIGHTNING]}, "bench": [MAGNEMITE], "prizes": [LIGHTNING, RATTATA, WATER][:prizes[0]],
         "hand": hand, "deck": [LIGHTNING] * 5},
        {"active": RATTATA, "bench": [RATTATA], "prizes": [WATER, RATTATA, LIGHTNING][:prizes[1]], "deck": [WATER] * 5},
    ])
    if reveal_owner is not None:
        reveal_prize(state, reveal_owner, reveal_position, trainer=0)
    return state


class PartialFaceUpTest(unittest.TestCase):
    """おもてのカードが一方のサイドの 1 枚だけ（構築した盤面）。うらのサイドの中身は、順番の決定でも、取ったあとでも漏れない。"""

    def test_one_face_up_card_is_enough_and_face_down_cards_stay_hidden(self):
        for owner in (0, 1):
            with self.subTest(owner=owner):
                state = apply_command(partial_board(reveal_owner=owner), UseAttack(0, SELFDESTRUCT))
                self.assertEqual(check_invariants(state), [])
                d = state.decision
                self.assertEqual((d.kind, d.player, d.options), ("prize_order", 0, (0, 1)))
                for first in (0, 1):
                    s = answer(state, d, first)
                    s = answer(s, s.decision, 0)  # 先のプレイヤーは位置 0（うら）を取る
                    later = 1 - first
                    self.assertEqual(s.decision.player, later)
                    self.assertEqual(takes_seen(s, later), [(first, None)])  # うらのカードは、後のプレイヤーに見えない
                    view = observe(s, later)
                    self.assertTrue(all(o.get("card_id") is None or s.players[later].prizes[o["value"]] in s.face_up_prizes
                                        for o in view["decision"]["options"]))

    def test_two_knockouts_ask_again(self):
        """じばくで相手のバトル場とダメージののった控え（コラッタ 20）、自分のコイルがきぜつする（P0 が 2 枚・P1 が 1 枚。並び (0, 0, 1)）。P1 のサイドの 1 枚がおもて。
        P0 を先にすると、1 枚取ったあとまだ両方が残り、おもてのカードもあるので、もう一度聞く。P1 を先にすると、残りは P0 だけなので聞かない。"""
        def knockouts():
            state = build_test_state([
                {"active": {"card": MAGNEMITE, "energy": [LIGHTNING, LIGHTNING]}, "bench": [MAGNEMITE], "prizes": [LIGHTNING, RATTATA, WATER], "deck": [LIGHTNING] * 5},
                {"active": RATTATA, "bench": [{"card": RATTATA, "damage": 20}, RATTATA], "prizes": [WATER, RATTATA, LIGHTNING], "deck": [WATER] * 5},
            ])
            reveal_prize(state, 1, 1, trainer=0)
            return apply_command(state, UseAttack(0, SELFDESTRUCT))

        expected = {0: [("prize_order", 0, (0, 0, 1)), ("take_prize", 0, (0, 1)), ("prize_order", 0, (0, 1)), ("take_prize", 0, (1,)), ("take_prize", 1, ())],
                    1: [("prize_order", 0, (0, 0, 1)), ("take_prize", 1, (0, 0)), ("take_prize", 0, (0,)), ("take_prize", 0, ())]}
        for first, sequence in expected.items():
            with self.subTest(first=first):
                state, seen = knockouts(), []
                while state.decision is not None and state.decision.kind in ("prize_order", "take_prize"):
                    d = state.decision
                    seen.append((d.kind, d.player, d.context_value("remaining")))
                    state = answer(state, d, first if len(seen) == 1 else d.options[0])
                self.assertEqual(seen, sequence)
                self.assertEqual((len(state.players[0].hand), len(state.players[1].hand)), (2, 1))
                self.assertEqual((state.decision.kind, state.decision.player), ("promote_active", 1))

    def test_no_face_up_card_no_decision(self):
        state = apply_command(partial_board(reveal_owner=None), UseAttack(0, SELFDESTRUCT))
        self.assertEqual((state.decision.kind, state.decision.player, state.decision.context_value("remaining")), ("take_prize", 0, (1,)))

    def test_one_player_takes_no_decision(self):
        """一方だけがサイドを取るなら、おもてのカードがあっても順番の決定はない: 相手のストライク（HP 70）はじばくの 40 で残り、自分のコイルだけがきぜつする。"""
        state = build_test_state([
            {"active": {"card": MAGNEMITE, "energy": [LIGHTNING, LIGHTNING]}, "bench": [MAGNEMITE], "prizes": 3, "deck": [LIGHTNING] * 5},
            {"active": SCYTHER, "bench": [RATTATA], "prizes": [WATER, RATTATA, LIGHTNING], "deck": [WATER] * 5},
        ])
        reveal_prize(state, 1, 0, trainer=0)
        state = apply_command(state, UseAttack(0, SELFDESTRUCT))
        self.assertEqual(check_invariants(state), [])
        d = state.decision
        self.assertEqual((d.kind, d.player, d.context_value("remaining")), ("take_prize", 1, ()))


class SuddenDeathPrizeOrderTest(unittest.TestCase):
    """両方が最後のサイドを同時に取る（構築した盤面。サイド 1 枚ずつ。ロケット団参上!は合法なコマンド）: 順番の決定のあと、どちらの順でもサドン・デス（p.311・p.324）。"""

    def test_both_orders_reach_sudden_death(self):
        state = partial_board(reveal_owner=None, prizes=(1, 1), rocket_in_hand=True)
        state = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        state = apply_command(state, UseAttack(0, SELFDESTRUCT))
        d = state.decision
        self.assertEqual((d.kind, d.player), ("prize_order", 0))
        outcomes = []
        for first in (0, 1):
            s = answer(state, d, first)
            self.assertEqual(s.decision.player, first)
            s = answer(s, s.decision, 0)
            self.assertEqual(s.decision.player, 1 - first)
            self.assertEqual(s.result, None)  # 1 人目が取り終えても判定しない（v0.2f 2 章 #5）
            s = answer(s, s.decision, 0)
            outcomes.append((s.phase, s.result.outcome))
        self.assertEqual(outcomes, [(Phase.SUDDEN_DEATH, "sudden_death")] * 2)


# ---------------------------------------------------------------- HC1（3 章）

HC1_CODE = "UNRESOLVED_DISCARD_ENERGY_TIMING"
BARRIER, PSYCHIC_ATTACK = 1, 0  # ミュウツーの「バリアー」（「超」エネルギーカードを 1 枚はがしてすてる。HC1）・「サイコキネシス」（HC1 ではない）
COINS = ((H,) * 6, (T,) * 6, (H, T) * 3)


def snapshot(state):
    return full(state), rng_fingerprint(state.rng), len(state.log)


def legal_sand_attack():
    """seed 0: 1 番 P0（ミュウツー）超をつけて番を終える → 2 番 P1（サンド）闘をつけて「すなかけ」→ 3 番 P0 超をつける。P0 のミュウツーは、この番にワザを使うと手順 4 のコインを投げる。"""
    deck0, deck1 = expand_decklist({MEWTWO: 4, PSYCHIC: 56}), expand_decklist({SANDSHREW: 4, FIGHTING: 56})
    state = finish_setup(new_game(deck0, deck1, 0), janken_winner=0)

    def attach(state, player, energy_id):
        energy = next(u for u in state.players[player].hand if _cid(state, u) == energy_id)
        return apply_command(state, AttachEnergy(player, energy, state.players[player].active.card))

    state = apply_command(attach(state, 0, PSYCHIC), EndTurn(0))
    state = apply_command(attach(state, 1, FIGHTING), UseAttack(1, 0))
    return attach(state, 0, PSYCHIC)


class StopAssertions(unittest.TestCase):
    def assert_stops(self, state, command, code=HC1_CODE, *, coins=COINS):
        """コインの結果・先読みの方法によらず ``code`` で止め、状態・ログ・乱数を変えない（tests/test_held_cards_v0_31_stops.py と同じ確かめ）。"""
        for sides in coins:
            seeded = with_coin_results(state, *sides)
            for mode in PREFLIGHT_MODES:
                before = snapshot(seeded)
                with self.subTest(coins=sides[:3], mode=mode):
                    with self.assertRaises(UnsupportedError) as ctx:
                        apply_kernel(seeded, command, preflight=mode)
                    self.assertEqual(ctx.exception.code, code)
                    self.assertEqual(snapshot(seeded), before)

    def assert_proceeds(self, state, command, *, coins=COINS):
        for sides in coins:
            for mode in PREFLIGHT_MODES:
                with self.subTest(coins=sides[:3], mode=mode):
                    apply_kernel(with_coin_results(state, *sides), command, preflight=mode)


class LegalHc1Test(StopAssertions):
    """new_game からの合法な操作で、すなかけを受けたこんらんでないミュウツーがバリアーを使う（v0.138 までは止めず、「うら」ならトラッシュしないで失敗していた）。"""

    @classmethod
    def setUpClass(cls):
        cls.state = legal_sand_attack()

    def test_preconditions(self):
        state = self.state
        attacker = state.players[0].active
        self.assertEqual((state.current_player, state.turn_number, _cid(state, attacker.card)), (0, 3, MEWTWO))
        self.assertFalse(attacker.conditions.confused)
        self.assertEqual(len(attack_coin_checks(state, attacker)), 1)
        self.assertEqual(len(attacker.energy), 2)
        self.assertEqual(check_invariants(state), [])

    def test_barrier_stops_before_the_coin(self):
        self.assert_stops(self.state, UseAttack(0, BARRIER))
        restored = pickle.loads(pickle.dumps(self.state))  # 保存・復元した状態でも同じ
        self.assert_stops(restored, UseAttack(0, BARRIER), coins=((T,),))

    def test_other_actions_are_not_stopped(self):
        """HC1 のワザでない「サイコキネシス」は手順 4 のコインを投げて進む（止めるのは HC1 の問いに当たるワザだけ）。番を終えることもできる。"""
        self.assert_proceeds(self.state, UseAttack(0, PSYCHIC_ATTACK))
        for side, failed in ((T, True), (H, False)):
            after = apply_command(with_coin_results(self.state, side), UseAttack(0, PSYCHIC_ATTACK))
            new = [e["kind"] for e in after.log[len(self.state.log):]]
            self.assertEqual("attack_failed" in new, failed)
        apply_command(self.state, EndTurn(0))


def sand_attacked(active, *, attacker=SANDSHREW, attacker_energy=(FIGHTING,)):
    """盤面を直接作り、相手（P1。8 番）の合法なワザ（すなかけ・えんまくなど。位置 0）のあと、P0 の 9 番にする。"""
    state = build_test_state([
        {"active": active, "bench": [RATTATA]},
        {"active": mon(attacker, attacker_energy), "bench": [RATTATA]},
    ], turn_number=8, current_player=1)
    state = apply_command(with_coin_results(state, H), UseAttack(1, 0))
    assert state.current_player == 0 and attack_coin_checks(state, state.players[0].active), state.phase
    return state


class ConstructedHc1Test(StopAssertions):
    """HC1 のワザ（「はがしてすてる」「はがして手札にもどす」・トランスダメージ）を、手順 4 のコインがあるときに使う。"""

    CASES = ((BASE_GASTLY, 1, (PSYCHIC, PSYCHIC)), (MEWTWO, BARRIER, (PSYCHIC, PSYCHIC)), (CHARIZARD, 0, (FIRE,) * 4), ("PMCG1-042", 1, (LIGHTNING,) * 4),
             ("PMCG3-027", 1, (PSYCHIC, PSYCHIC)), (MOLTRES, 0, (FIRE,)), (SABRINAS_ABRA, 0, (PSYCHIC,)), ("PR1-055", 1, (PSYCHIC,) * 3, {"evolved_from": [ABRA, KADABRA]}))

    def test_hc1_attacks_stop_with_a_step4_coin(self):
        for card, index, energy, *extra in self.CASES:
            with self.subTest(card=card):
                self.assert_stops(sand_attacked(mon(card, energy, **(extra[0] if extra else {}))), UseAttack(0, index))

    def test_smokescreen_too(self):
        self.assert_stops(sand_attacked(mon(MEWTWO, (PSYCHIC, PSYCHIC)), attacker=HORSEA, attacker_energy=(WATER,)), UseAttack(0, BARRIER))

    def test_without_a_step4_coin_hc1_attacks_proceed(self):
        """手順 4 のコインがなく、こんらんでもなければ、v0.31 のとおり止めない（どちらの読み方でも結果は同じ）。"""
        for card, index, energy, *extra in self.CASES:
            with self.subTest(card=card):
                state = build_test_state([{"active": mon(card, energy, **(extra[0] if extra else {})), "bench": [RATTATA]}, {"active": RATTATA, "bench": [RATTATA]}], turn_number=7)
                self.assertIsNone(attack_step4_coin(state, state.players[0].active))
                self.assert_proceeds(state, UseAttack(0, index), coins=((H,) * 6,))

    def test_effect_timing_attacks_are_not_stopped(self):
        """RUL-ENERGY-DISCARD-ATTACKS の範囲（効果。コインのあとにトラッシュする）のワザ（カツラのウインディの「ほのおのあらし」）は、手順 4 のコインがあっても止めない。"""
        self.assert_proceeds(sand_attacked(mon(BLAINES_ARCANINE, (FIRE,) * 4)), UseAttack(0, 1))

    def test_rebellion_is_a_step4_coin(self):
        """補助関数だけの確かめ: ［はんこう］（カスミのギャラドス）を持つポケモンには手順 4 のコインがある。HC1 のワザを使う［はんこう］のポケモンの盤面は作っていない。"""
        state = build_test_state([{"active": mon(MISTYS_GYARADOS, (WATER,) * 3), "bench": [RATTATA]}, {"active": RATTATA, "bench": [RATTATA]}], turn_number=7)
        self.assertIsNotNone(attack_step4_coin(state, state.players[0].active))
        self.assertEqual(attack_coin_checks(state, state.players[0].active), ())


if __name__ == "__main__":
    unittest.main()

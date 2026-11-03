"""v0.139（docs/prize-order-hc1-fix-v0.139.md）: 同時のきぜつでサイドを取る順番（2 章）と、HC1 の止める範囲（3 章）の修正。

サイドを取る順番: v0.139 は、両方がサイドを取り、どちらかのサイドにおもてのカードがあるとき、番のプレイヤーが次に取るプレイヤーを 1 枚ごとに選ぶ（決定 ``prize_order``）とした。
v0.140 の利用者の指定（docs/prize-order-user-rule-v0.140.md）で、両方が取るときはいつも先に取るプレイヤーを 1 回選び、そのプレイヤーがまとめて取る（決定 ``prize_first``）に改めたので、
v0.139 の順番のテスト（``LegalPrizeOrderTest``・``PartialFaceUpTest``・``SuddenDeathPrizeOrderTest``）は tests/test_prize_order_user_rule_v0_140.py に移した（今の規約で書き直した）。
この file には、盤面を作る関数（ほかのテスト・検証スクリプトが使う）と HC1 のテストを残す。

HC1: 「はがしてすてる」（トラッシュが条件か効果か決められない）ワザを、p.309 の手順 4 のコイン（すなかけなど・［はんこう］）があるときに使うなら、こんらん・ベイビィポケモンの
ルールのコインと同じく、宣言を受け付けずに止める（``UNRESOLVED_DISCARD_ENERGY_TIMING``。コインの前。状態・乱数・ログを変えない）。

再現の種類:
- ``legal_double_knockout``: new_game(seed=473) からの合法な操作の列（固定。seed を選び直さない）
- ``partial_board``: 盤面を直接作った状態（``build_test_state``。おもてにするのは ``zones.reveal_prize``）
- ``LegalHc1Test``: new_game(seed=0) からの合法な操作の列（ミュウツー対サンド。seed は 0 から順に試して、この操作の列が通る最初のもの）
- ``ConstructedHc1Test``: 盤面を直接作った状態から、相手の合法なワザ（すなかけ・えんまく）→ 自分のワザ。［はんこう］は補助関数だけ（HC1 のワザを使う［はんこう］のポケモンは作っていない）
"""

from __future__ import annotations

import pickle
import unittest

from kyuura_engine import (
    UnsupportedError,
    apply_command,
    check_invariants,
    expand_decklist,
    new_game,
    state_to_dict,
    visible_log,
)
from kyuura_engine.commands import (
    AttachEnergy,
    EndTurn,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
)
from kyuura_engine.persistent import attack_coin_checks
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.resolution.programs import attack_step4_coin
from kyuura_engine.rng import rng_fingerprint
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

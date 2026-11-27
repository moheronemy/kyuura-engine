"""v0.193（C-TF1。docs/r2-transform-hydro-design.md 10 章）: 変身で写した、ワザといっしょに宣言する特殊能力に、v0.124 の既存の確かめ（``copied_declared_power_problem``）を当てる。

v0.124（docs/super-transform-dark-pulse-v0.124.md 3.1 節）の方針: 変身したポケモンは写したカードの特殊能力を持つ（CR-TRANSFORM-COPIES-TOP-CARD）が、写すことをエンジンが確かめた
宣言する特殊能力（``COPY_VERIFIED_DECLARED``）でなければ、使う宣言を未対応（``UNSUPPORTED_TRANSFORM_COPIED_POWER``。研究上の未解決ではない）で止める。0.192.0 まで、この確かめを
呼ぶのは ``UsePokemonPower`` の経路だけで、ワザといっしょに使う力（``UseAttack.attack_power``・``with_power``・``with_powers``）は通っていた（C-TF0 の SF1）。新しい裁定ではなく、
既存の制限の適用漏れの修正。

- 直接のコマンド: ``attack_power_check``（使い手自身の［すいりょくはつでん］）と ``group_attack_power_check``（持ち主の［XXXXX］・［ANGER］）が、力の型ごとの確かめの前、使えない・
  消える効果の確かめのあとに ``copied_declared_power_problem`` を呼ぶ（``UsePokemonPower`` と同じ位置づけ）。本来のカードの力・写していない別の持ち主の力は変えない
- 入力 API: おもての使い手の 2 段目で、同じ確かめが止める組（未検証の写した力）を示さない（番号は欠番のまま。ほかの選択肢は変えない）。うらのメタモンは今の
  ``no_printed_attack`` の保留のまま（変身のあとのワザ・2 段目を示さない）

構築盤面（``tests.helpers.build_test_state``・``test_secret_plan_v0_67`` の盤面。new_game からの到達ではない）。持ち主・写す相手はどれも登録された実在のカード。人工の差しかえは
名前に ``artificial``、到達できる状態を直接入れたものは ``injected`` をつける。今、写すことを確かめた宣言する力（``COPY_VERIFIED_DECLARED``）に、ワザといっしょに使う力の実在の例はない
（``RegistryTest``）。確かめた経路が通ることは、その一覧を人工に広げて確かめる（``VerifiedGateTest``）。
"""

from __future__ import annotations

import unittest
from unittest import mock

from kyuura_engine import UseAttack, UsePokemonPower, check_invariants, current_form, powers_of
from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import effects as E
from kyuura_engine import legal_actions as L
from kyuura_engine.cards import load_card_pool
from kyuura_engine.client_api import ClientHub
from kyuura_engine.coins import CoinSide
from kyuura_engine.observation import observe
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.serialize import rng_fingerprint
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_bits
from tests.log_audit import observation_problems, serialization_problems
from tests.test_legal_actions_r2_stadium_coin_v0_188 import attack_of, check_code
from tests.test_legal_actions_r2_unown_v0_191 import REQ, with_injected_prevented
from tests.test_legal_actions_u7_1 import snap
from tests.test_legal_actions_u7_4 import via_direct, via_u7
from tests.test_r2_transform_preconditions_v0_192 import fd as fd_ditto

HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, L_, P, F = H.WATER, H.LIGHTNING, H.PSYCHIC, H.FIGHTING
DITTO, LANTURN = H.DITTO, H.LANTURN_NEO1
UNOWN_X, UNOWN_A = "neo4-065", "neo2-030"  # ［XXXXX］・［ANGER］
COINS_X = (HD, HD, TL, *[TL] * 6)  # ［XXXXX］: 「おもて」2 枚
COPY_UNSUPPORTED = E.TRANSFORM_COPIED_UNSUPPORTED_CODE  # 既存の未対応のコード（v0.124）


def mon(card, energy=(), **extra):
    return {"card": card, "energy": list(energy), **extra}


def lanturn(energy=(L_, L_)):
    return mon(LANTURN, energy, evolved_from=H.CHINCHOU_NEO1)


def up(active, *, opponent, bench=(), hand=()):
    """おもてのバトル場（``active`` は mon の辞書）。番はプレイヤー 0 の main。"""
    return H.build_test_state([{"active": active, "bench": list(bench), "hand": list(hand), "deck": [H.FIRE] * 10},
                               {"active": opponent, "bench": [], "hand": [], "deck": [H.FIRE] * 10}], turn_number=9, current_player=0)


def fd(energies, *, opponent, bench=()):
    """うらのメタモン（マチスの秘策。C-TF0 の盤面）。"""
    return fd_ditto(DITTO, energies, opponent=opponent, bench=bench)


def me(state):
    return state.players[0].active.pokemon_id


def bench_of(state, card):
    return next(p.pokemon_id for p in state.players[0].bench if state.cards[p.card].card_id == card)


def valid(test, state):
    test.assertEqual((check_invariants(state), serialization_problems(state), observation_problems(state)), ([], [], []))
    return state


def rejects(test, state, command, code, coins=()):
    """どの先読みの方法でも ``code`` で拒否し、状態・乱数・ログ・決定・うらのままを変えない。"""
    state = with_coin_bits(state, *coins) if coins else state
    before = snap(state)
    face_down = state.is_face_down(state.players[0].active)
    for mode in PREFLIGHT_MODES:
        with test.subTest(mode=mode):
            with test.assertRaises(Exception) as raised:
                apply_kernel(state, command, preflight=mode)
            test.assertEqual(getattr(raised.exception, "code", None), code)
    test.assertEqual(snap(state), before)
    test.assertEqual(state.is_face_down(state.players[0].active), face_down)


def accepted(test, state, command, coins=()):
    """どの先読みの方法でも同じ状態で受け付ける。受け付けた状態を返す。"""
    state = with_coin_bits(state, *coins) if coins else state
    results = [apply_kernel(state, command, preflight=mode) for mode in PREFLIGHT_MODES]
    test.assertEqual(len({repr(snap(r)) for r in results}), 1)
    done = results[0]
    test.assertEqual((check_invariants(done), serialization_problems(done), observation_problems(done)), ([], [], []))
    return state, done


def damages(before, after):
    return [e["amount"] for e in after.log[len(before.log):] if e["kind"] == "damage"]


class CopiedAttackPowerTest(unittest.TestCase):
    """メタモンが写した［すいりょくはつでん］を ``attack_power`` で宣言すると、既存の未対応（0.192.0 は受け付けて 20 → 50）。"""

    def test_face_up_and_face_down_with_and_without_card(self):
        for name, build in (("face_up", lambda e: up(mon(DITTO, e), opponent=lanturn())), ("face_down", lambda e: fd(e, opponent=lanturn()))):
            for energies in ((W, W, W), (W, W, F)):  # W・W・F は SF2（TE1 を聞かない）の盤面。数える前に止まる
                with self.subTest(attacker=name, energies=energies):
                    state = valid(self, build(energies))
                    rejects(self, state, UseAttack(0, 0, attack_power=True), COPY_UNSUPPORTED, (TL,))
                    rejects(self, state, UseAttack(0, 0, card=state.players[1].active.card, attack_power=True), COPY_UNSUPPORTED, (TL,))

    def test_without_the_power_the_copied_attack_is_unchanged(self):
        for name, state in (("face_up", up(mon(DITTO, (W, W, W)), opponent=lanturn())), ("face_down", fd((W, W, W), opponent=lanturn()))):
            with self.subTest(attacker=name):
                before, done = accepted(self, valid(self, state), UseAttack(0, 0), (TL,))
                self.assertEqual(damages(before, done), [20])

    def test_existing_rejections_keep_their_priority_injected(self):
        """使えない効果（ショックアイ。到達できる状態を直接入れた injected）は、写した力の確かめより先（0.192.0 と同じコード）。"""
        state = valid(self, up(mon(DITTO, (W, W, W)), opponent=lanturn()))
        rejects(self, with_injected_prevented(state, me(state)), UseAttack(0, 0, attack_power=True), "POWER_USE_PREVENTED", (TL,))

    def test_original_lanturn_is_unchanged(self):
        state = valid(self, up(lanturn((L_, L_, W)), opponent=mon(H.ONIX)))
        before, done = accepted(self, state, UseAttack(0, 0, attack_power=True), (TL,))
        self.assertEqual(damages(before, done), [30])
        self.assertIn("attack_power", [e["kind"] for e in done.log[len(before.log):]])

    def test_use_pokemon_power_path_is_unchanged(self):
        state = valid(self, up(mon(DITTO, (W, W, W)), opponent=lanturn()))
        rejects(self, state, UsePokemonPower(0, me(state), 0, card=state.players[1].active.card), COPY_UNSUPPORTED)


class CopiedGroupPowerTest(unittest.TestCase):
    """写した持ち主の［XXXXX］・［ANGER］を ``with_power``・``with_powers`` で宣言すると、既存の未対応（0.192.0 は受け付けて 60・20）。"""

    def test_self_holder_face_up_and_face_down(self):
        for opponent in (UNOWN_X, UNOWN_A):
            for name, state in (("face_up", up(mon(DITTO, (P,)), opponent=mon(opponent, (P,)))), ("face_down", fd((P,), opponent=mon(opponent, (P,))))):
                with self.subTest(copied=opponent, attacker=name):
                    state = valid(self, state)
                    rejects(self, state, UseAttack(0, 0, with_power=me(state)), COPY_UNSUPPORTED, COINS_X)
                    before, done = accepted(self, state, UseAttack(0, 0), COINS_X)  # 力なしの写したワザは変えない
                    self.assertEqual(damages(before, done), [20])

    def test_other_real_holder_still_usable(self):
        """複数の持ち主: 写した力を含む並びは、並びの順によらず未対応。写していない別の持ち主（ベンチのアンノーンA）だけなら 0.192.0 と同じく受け付ける。"""
        for name, state in (("face_up", up(mon(DITTO, (P,)), opponent=mon(UNOWN_X, (P,)), bench=(mon(UNOWN_A),))),
                            ("face_down", fd((P,), opponent=mon(UNOWN_X, (P,)), bench=(mon(UNOWN_A),)))):
            with self.subTest(attacker=name):
                state = valid(self, state)
                other = bench_of(state, UNOWN_A)
                rejects(self, state, UseAttack(0, 0, with_powers=(me(state), other)), COPY_UNSUPPORTED, COINS_X)
                rejects(self, state, UseAttack(0, 0, with_powers=(other, me(state))), COPY_UNSUPPORTED, COINS_X)
                before, done = accepted(self, state, UseAttack(0, 0, with_power=other), COINS_X)
                self.assertEqual(damages(before, done), [20])
                self.assertIn("group_attack_power_counters", [e["kind"] for e in done.log[len(before.log):]])

    def test_existing_rejections_keep_their_priority_injected(self):
        state = valid(self, up(mon(DITTO, (P,)), opponent=mon(UNOWN_X, (P,))))
        rejects(self, with_injected_prevented(state, me(state)), UseAttack(0, 0, with_power=me(state)), "POWER_USE_PREVENTED", COINS_X)

    def test_original_unown_is_unchanged(self):
        for real, damage in ((UNOWN_X, 30), (UNOWN_A, 10)):
            with self.subTest(real=real):
                state = valid(self, up(mon(real, (P,)), opponent=mon(H.ONIX)))
                before, done = accepted(self, state, UseAttack(0, 0, with_power=me(state)), COINS_X)
                self.assertEqual(damages(before, done), [damage])
        state = valid(self, up(mon(UNOWN_X, (P,)), opponent=mon(H.ONIX), bench=(mon(UNOWN_A),)))
        before, done = accepted(self, state, UseAttack(0, 0, with_powers=(me(state), bench_of(state, UNOWN_A))), COINS_X)
        self.assertEqual(damages(before, done), [30])


class VerifiedGateTest(unittest.TestCase):
    """止めるかは共通の確かめ（``COPY_VERIFIED_DECLARED``）で決まり、カード・力の名前の例外ではない。"""

    def test_artificial_verified_list_lets_the_copied_powers_through(self):
        """artificial: 確かめた一覧にワザといっしょに使う力の型を足すと、写した力は 0.192.0 と同じ結果で通る（確かめた経路を巻き込まない）。"""
        widened = (*E.COPY_VERIFIED_DECLARED, E.ExtraEnergyDamageWithAttack, E.CoinsUntilTailsBonusToGroupAttack)
        with mock.patch.object(E, "COPY_VERIFIED_DECLARED", widened):
            state = valid(self, up(mon(DITTO, (W, W, W)), opponent=lanturn()))
            before, done = accepted(self, state, UseAttack(0, 0, attack_power=True), (TL,))
            self.assertEqual(damages(before, done), [50])
            state = valid(self, up(mon(DITTO, (P,)), opponent=mon(UNOWN_X, (P,))))
            before, done = accepted(self, state, UseAttack(0, 0, with_power=me(state)), COINS_X)
            self.assertEqual(damages(before, done), [60])

    def test_transformed_but_own_or_not_copied_is_not_rejected(self):
        """変身していることだけでは拒否しない: 写した力でない（自分のカードの力・ほかのポケモンの力）なら、確かめは None。"""
        state = up(mon(DITTO, (P,)), opponent=mon(UNOWN_X, (P,)), bench=(mon(UNOWN_A),))
        ditto = state.players[0].active
        own = next(s for s in powers_of(state, ditto) if s.card == ditto.card)
        self.assertIsNone(E.copied_declared_power_problem(state, ditto, own))
        holder = state.find_pokemon(bench_of(state, UNOWN_A))[1]
        self.assertIsNone(E.copied_declared_power_problem(state, holder, E.group_attack_power_slot(state, holder)))
        copied = E.group_attack_power_slot(state, ditto)
        self.assertEqual(copied.card, state.players[1].active.card)
        self.assertEqual(E.copied_declared_power_problem(state, ditto, copied)[0], COPY_UNSUPPORTED)
        self.assertIn(current_form(state, ditto).kind, E.COPIED_FORMS)


class RegistryTest(unittest.TestCase):
    """今の登録に、写すことを確かめた（``COPY_VERIFIED_DECLARED``）ワザといっしょに使う力はない（確かめた経路の実在例は ``UsePokemonPower`` の 4 つの型だけ）。"""

    def test_no_with_attack_power_is_verified(self):
        pool = load_card_pool()
        with_attack = set()
        for card_id, definition in pool.definitions.items():
            for power in definition.powers if definition.category == "pokemon" else ():
                entry = E.DEFAULT_EFFECTS.power_entry(card_id, power.index)
                if entry is not None and (isinstance(entry.effect, (E.ExtraEnergyDamageWithAttack, E.AttackDeclaredPower))):
                    with_attack.add(type(entry.effect))
        self.assertTrue(with_attack)
        self.assertEqual([t.__name__ for t in sorted(with_attack, key=lambda t: t.__name__) if issubclass(t, E.COPY_VERIFIED_DECLARED)], [])


def stage2(inputs):
    return [(o["id"], o["addon"], o.get("pokemon"), o.get("power")) for o in inputs["stages"][1]["options"]]


class InputApiTest(unittest.TestCase):
    """入力 API: おもての使い手の 2 段目に、未検証の写した力を示さない（0.192.0 は示した）。ほかの選択肢・本来の持ち主は変えない。"""

    def test_copied_powers_are_not_offered(self):
        for state in (up(mon(DITTO, (W, W, W)), opponent=lanturn()), up(mon(DITTO, (P,)), opponent=mon(UNOWN_X, (P,))),
                      up(mon(DITTO, (P,)), opponent=mon(UNOWN_A, (P,)))):
            with self.subTest(copied=state.cards[state.players[1].active.card].card_id):
                _h, session, r, c, inputs = attack_of(state)
                self.assertEqual(c["processability"], L.MAY_STOP_LATER)
                self.assertEqual((stage2(inputs), inputs["stages"][1]["options_by_choice"]), ([], {"o1": []}))
                self.assertIsNone(check_code(session, r, c, ["o1"]))
                self.assertEqual(check_code(session, r, c, ["o1", "o2"]), L.CANDIDATE_INPUT_INVALID)

    def test_other_real_holder_is_offered_with_its_number(self):
        """写した力（使い手自身。0.192.0 の o2）は欠番、別の持ち主（ベンチのアンノーンA）は 0.192.0 と同じ o3。送信は直接のコマンドと同じ結果。"""
        state = with_coin_bits(up(mon(DITTO, (P,)), opponent=mon(UNOWN_X, (P,)), bench=(mon(UNOWN_A),)), *COINS_X)
        _h, session, r, c, inputs = attack_of(state)
        other = bench_of(state, UNOWN_A)
        self.assertEqual(stage2(inputs), [("o3", L.ADDON_WITH_POWER, other, "ANGER[アンガー]")])
        self.assertEqual([(x["option"], x["processability"]) for x in inputs["stages"][1]["options_by_choice"]["o1"]], [("o3", L.MAY_STOP_LATER)])
        self.assertEqual([check_code(session, r, c, ch) for ch in (["o1"], ["o1", "o3"], ["o1", "o2"], ["o1", "o3", "o2"])],
                         [None, None, L.CANDIDATE_INPUT_INVALID, L.CANDIDATE_INPUT_INVALID])
        host, result = via_u7(state, lambda stages: ["o1", "o3"])
        game, direct = via_direct(state, UseAttack(0, 0, with_power=other))
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual((result.outcome, snap(host.game.state)), (D.ACCEPTED, snap(game.state)))

    def test_original_holders_are_unchanged(self):
        state = up(lanturn((L_, L_, W)), opponent=mon(H.ONIX))
        self.assertEqual(stage2(attack_of(state)[4]), [("o2", L.ADDON_ATTACK_POWER, me(state), None)])
        state = up(mon(UNOWN_X, (P,)), opponent=mon(H.ONIX), bench=(mon(UNOWN_A),))
        self.assertEqual(stage2(attack_of(state)[4]), [("o2", L.ADDON_WITH_POWER, me(state), "XXXXX[?????]"),
                                                      ("o3", L.ADDON_WITH_POWER, bench_of(state, UNOWN_A), "ANGER[アンガー]")])

    def test_face_down_ditto_keeps_the_no_printed_attack_hold(self):
        for opponent in (lanturn(), mon(UNOWN_X, (P,))):
            with self.subTest(opponent=opponent["card"]):
                state = fd((W, W, W) if opponent["card"] == LANTURN else (P,), opponent=opponent, bench=(mon(UNOWN_A),))
                _h, _s, _r, c, inputs = attack_of(state)
                self.assertEqual((c["processability"], c["reasons"]), (L.NOT_IMPLEMENTED, [L.REASON_FACE_DOWN, L.REASON_NO_PRINTED_ATTACK]))
                self.assertEqual(inputs["stages"], [])

    def test_reading_candidates_inputs_and_check_changes_nothing(self):
        state = up(mon(DITTO, (P,)), opponent=mon(UNOWN_X, (P,)), bench=(mon(UNOWN_A),))
        hub = ClientHub(A.HostedGame(state.clone()))
        hub.take_updates(1), hub.take_updates("spectator")
        player = hub.player(0)
        before = snap(state)
        r = player.handle({**REQ, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == L.KIND_USE_ATTACK)
        player.handle({**REQ, "type": "inputs", "game": r["game"], "revision": r["revision"], "candidate": c["id"]})
        for choices in (["o1", "o2"], ["o1", "o3"], ["o1"]):
            player.handle({**REQ, "type": "check", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": choices})
        self.assertEqual(snap(state), before)
        self.assertEqual(rng_fingerprint(state.rng), before[1])
        self.assertEqual([hub.take_updates(a) for a in (0, 1, "spectator")], [[], [], []])


class BoundaryTest(unittest.TestCase):
    """拒否は本人にだけ返り、相手・観戦者に拒否の診断・公開の前の正体を伝えない（うらのメタモンはうらのまま）。"""

    def test_rejection_reaches_only_the_submitter(self):
        for name, state, command in (("face_down_attack_power", fd((W, W, W), opponent=lanturn()), lambda s: UseAttack(0, 0, attack_power=True)),
                                     ("face_down_with_power", fd((P,), opponent=mon(UNOWN_X, (P,))), lambda s: UseAttack(0, 0, with_power=me(s))),
                                     ("face_up_attack_power", up(mon(DITTO, (W, W, W)), opponent=lanturn()), lambda s: UseAttack(0, 0, attack_power=True))):
            with self.subTest(case=name):
                views = [observe(state, v) for v in (1, None)]
                game, direct = via_direct(state, command(state))
                self.assertEqual((direct.outcome, direct.diagnosis.case_id), (D.REJECTED, COPY_UNSUPPORTED))
                self.assertEqual(snap(game.state), snap(state))
                self.assertEqual([observe(game.state, v) for v in (1, None)], views)
                self.assertEqual(game.state.is_face_down(game.state.players[0].active), state.is_face_down(state.players[0].active))

    def test_opponent_secrets_do_not_change_the_rejection(self):
        rows = []
        for extra in ((H.FIRE,), (H.GRASS,)):
            state = fd_ditto(DITTO, (W, W, W), opponent=lanturn(), opponent_hand=extra)
            game, direct = via_direct(state, UseAttack(0, 0, attack_power=True))
            rows.append((direct.outcome, direct.diagnosis.case_id, direct.diagnosis.message, snap(game.state) == snap(state)))
        self.assertEqual(rows[0], rows[1])


if __name__ == "__main__":
    unittest.main()

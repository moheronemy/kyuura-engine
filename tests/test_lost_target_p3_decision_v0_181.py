"""LOST_TARGET の P3s（決定への回答で、本人のうらのカードを指定する経路）のエンジンの動作の根拠（docs/verification-ai-lost-target-p3-decision-design.md 6.2 の
E7〜E11。エンジン 0.181.0）。エンジンの動作・裁定・カードデータは変えない（テストだけ）。

経路: ディフェンダー（効果の型 ``AttachedDamageReduction``。``ends_on_lost_target`` は偽）は、本人の場のポケモン（バトル場 → ベンチ）を選べるものにした ``select_pokemon`` の
決定を出す（再開先 ``trainer``・文脈なし）。答えは ``engine._answer_decision_once`` → ``_designate_answer``（``can_lose=False``）→ ``zones.designate_face_down`` に入り、
選んだうらのカードの本当のカードが「たねポケモン」（ベイビィをふくむ）でなければ、状態を変える前に ``UNSUPPORTED_SECRET_PLAN_LOST_TARGET`` で止まる。持ち主が答えた
プレイヤーなので ``IDENTITY_CONSULTED`` に記録せず、本当のカードによらない確かめ（``engine._identity_independent``）には入らない。

E11 は対象を失ったら効果を終える入れ替え（``ends_on_lost_target`` が真）との違い。

E12（相手のうら P3o の対照・v0.180 の内部の例外の回帰）は P3s の正の根拠ではなく、0.181.0 の
``tests/test_keep_designated_energy_removal_v0_181.py``（``EnergyRemovalDesignatedKeepTest.test_opponent_face_down_energy_is_kp1_for_every_identity``・``ClientApiTwinTest``）が
同じ場面を確かめているので、ここでは重ねない。期待値は 0.180.0 の設計の LOST_TARGET から、どの本当のカードでも KP1（``UNRESOLVED_KEEP_PROTECTED_TARGET``）に変わった
（docs/keep-designated-energy-removal-v0.181.md 4 章）。

出典: 停止した作業（claude/lost-target-p3s-judge-rule8・1eed4d1）の未追跡のテストの証跡の写し（SHA-256 79d45767…。E12 のクラスを除き、ほかは同じ）。
盤面は ``tests/test_secret_plan_v0_67.py`` の ``board``・``place``・``full``・``face_down``・``uid_of``・``opponent_turn`` と ``build_test_state`` で作る（new_game からの対戦ではない）。
"""

from __future__ import annotations

import json
import unittest

from kyuura_engine import PlayTrainer, ResolveDecision
from kyuura_engine import engine as _engine
from kyuura_engine import zones as _zones
from kyuura_engine.cards import load_card_pool
from kyuura_engine.effects import DEFAULT_EFFECTS, TEXT_PRE_NEO, AttachedDamageReduction, card_is_basic_in_text
from kyuura_engine.engine import TRAINER_REACTION, apply_command, check_invariants
from kyuura_engine.errors import UnsupportedError
from kyuura_engine.observation import observe, visible_log
from kyuura_engine.zones import SECRET_PLAN_LOST_TARGET_CODE
from tests.helpers import DEFENDER, DIGLETT, FIRE, KADABRA, LT_SURGES_SECRET_PLAN, PSYCHIC, SWITCH
from tests.test_secret_plan_v0_67 import board, face_down, full, opponent_turn, place, uid_of

PICHU = "neo1-042"  # ピチュー（ネオ。ベイビィポケモン）。ネオより前の説明の「たねポケモン」に当たる（GR-2000-P325-PRE-NEO-BABY）
NOT_BASIC = (FIRE, PSYCHIC, KADABRA)  # エネルギー 2 種・1 進化（どれも「たねポケモン」でない）


def public(state):
    """答えたプレイヤーの相手・観戦者の観測とログの写し（本当のカードが出ていないことの比べ）。"""
    return {str(v): (observe(state, v), visible_log(state, v)) for v in (1, None)}


def own_face_down(state, card_id):
    """``card_id`` を本人（プレイヤー 0）のうらのカードとしてベンチに出す。(状態, うらの場のポケモン)。"""
    state = place(state, card_id)
    return state, next(q for q in face_down(state) if state.cards[q.card].card_id == card_id)


def defender_decision(state):
    """ディフェンダーを使い、決定を出した状態を返す。"""
    state = apply_command(state, PlayTrainer(0, uid_of(state, DEFENDER)))
    assert state.decision is not None
    return state


def answer(state, pokemon_id):
    return ResolveDecision(state.decision.player, state.decision.id, (pokemon_id,))


def assert_no_secret(case, error, card_id):
    definition = load_card_pool().get(card_id)
    text = json.dumps([error.code, error.message], ensure_ascii=False)
    case.assertNotIn(card_id, text)
    case.assertNotIn(definition.name_ja, text)


class P3sRejectionTest(unittest.TestCase):
    def rejected(self, state, command):
        before, seen, decision = full(state), public(state), state.decision
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, command)
        self.assertEqual(ctx.exception.code, SECRET_PLAN_LOST_TARGET_CODE)
        self.assertEqual(full(state), before)  # 状態（ログ・決定・番・場）と乱数が変わらない
        self.assertEqual(public(state), seen)  # 相手・観戦者への公開が変わらない
        self.assertIs(state.decision, decision)  # 同じ決定が残る（渡した状態は変わらない）
        self.assertEqual(check_invariants(state), [])
        self.assertIsNone(_zones.IDENTITY_CONSULTED)
        return ctx.exception

    def test_e7_decision_shape_and_own_non_basic_face_down(self):
        """E7: ディフェンダーの決定（本人の場のポケモン、バトル場 → ベンチ。再開先 trainer・文脈なし）で、本人のたねでないうらを答えると、指定の時点でこのコードで止まり、
        同じ決定が残る。別の対象（バトル場）を選び直せば受理してつける。"""
        entry = DEFAULT_EFFECTS.trainer_entry(DEFENDER)
        self.assertIsInstance(entry.effect, AttachedDamageReduction)
        self.assertEqual(entry.effect.implementation_id, "attached_damage_reduction")
        self.assertIs(entry.effect.ends_on_lost_target, False)
        for card_id in NOT_BASIC:
            with self.subTest(card=card_id):
                self.assertIs(card_is_basic_in_text(load_card_pool().get(card_id), TEXT_PRE_NEO), False)
                state, fd = own_face_down(board(hand=(card_id, DEFENDER)), card_id)
                state = defender_decision(state)
                d = state.decision
                self.assertEqual((d.kind, d.player, d.resume, d.min_choices, d.max_choices), ("select_pokemon", 0, "trainer", 1, 1))
                self.assertEqual(tuple(d.options), tuple(q.pokemon_id for q in state.players[0].in_play()))
                self.assertEqual([d.context_value(k) for k in ("chaos", "stadium_cost", TRAINER_REACTION)], [None, None, None])
                self.assertEqual(observe(state, 0)["trainer_in_use"]["card_id"], DEFENDER)
                error = self.rejected(state, answer(state, fd.pokemon_id))
                assert_no_secret(self, error, card_id)
                active = state.players[0].active
                after = apply_command(state, answer(state, active.pokemon_id))
                self.assertIsNone(after.decision)
                self.assertEqual([after.cards[t.card].card_id for t in after.players[0].active.trainers], [DEFENDER])
                self.assertTrue(after.is_face_down(after.players[0].find_by_pokemon_id(fd.pokemon_id)))
                self.assertEqual(check_invariants(after), [])

    def test_e10_opponent_face_down_elsewhere_does_not_change_it(self):
        """E10: 相手の場にも別のうらがあるが、答えで指定するのは本人のうらだけ。同じコード・状態は変わらない（相手のうらの確かめに入らない）。"""
        state, fd = own_face_down(board(hand=(KADABRA, DEFENDER), opponent_hand=(LT_SURGES_SECRET_PLAN, DIGLETT)), KADABRA)
        state = opponent_turn(place(opponent_turn(state), DIGLETT, player=1))
        self.assertEqual((state.current_player, len(face_down(state, 0)), len(face_down(state, 1))), (0, 1, 1))
        state = defender_decision(state)
        calls = []
        original = _engine._identity_independent
        try:
            _engine._identity_independent = lambda *a, **k: calls.append(1) or original(*a, **k)
            error = self.rejected(state, answer(state, fd.pokemon_id))
        finally:
            _engine._identity_independent = original
        self.assertEqual(calls, [])
        assert_no_secret(self, error, KADABRA)


class P3sContrastTest(unittest.TestCase):
    def test_e8_basic_and_baby_are_revealed_and_attached(self):
        """E8: 本人のたね・ベイビィのうらなら、おもてにしてディフェンダーをつける（このコードにならない）。"""
        for card_id in (DIGLETT, PICHU):
            with self.subTest(card=card_id):
                self.assertIs(card_is_basic_in_text(load_card_pool().get(card_id), TEXT_PRE_NEO), True)
                state, fd = own_face_down(board(hand=(card_id, DEFENDER)), card_id)
                state = defender_decision(state)
                after = apply_command(state, answer(state, fd.pokemon_id))
                revealed = [e for e in after.log[len(state.log):] if e["kind"] == "secret_plan_revealed"]
                self.assertEqual([(e["cause"], e["pokemon_id"]) for e in revealed], [("effect", fd.pokemon_id)])
                kept = after.players[0].find_by_pokemon_id(fd.pokemon_id)
                self.assertFalse(after.is_face_down(kept))
                self.assertEqual([after.cards[t.card].card_id for t in kept.trainers], [DEFENDER])
                self.assertEqual(check_invariants(after), [])

    def test_e9_face_up_target_designates_nothing(self):
        """E9: うらのカードがあっても、おもてのポケモンを選べば指定はなく受理する。"""
        state, fd = own_face_down(board(hand=(PSYCHIC, DEFENDER)), PSYCHIC)
        state = defender_decision(state)
        after = apply_command(state, answer(state, state.players[0].active.pokemon_id))
        self.assertNotIn("secret_plan_revealed", [e["kind"] for e in after.log[len(state.log):]])
        self.assertTrue(after.is_face_down(after.players[0].find_by_pokemon_id(fd.pokemon_id)))

    def test_e11_switch_ends_when_the_target_is_lost(self):
        """E11: 対象を失ったら効果を終える入れ替え（ends_on_lost_target が真）なら、本人のたねでないうらを選んでも受理し、トラッシュして効果を終える（このコードにならない）。"""
        self.assertIs(DEFAULT_EFFECTS.trainer_entry(SWITCH).effect.ends_on_lost_target, True)
        state, fd = own_face_down(board(hand=(PSYCHIC, SWITCH)), PSYCHIC)
        active = state.players[0].active.pokemon_id
        state = apply_command(state, PlayTrainer(0, uid_of(state, SWITCH)))
        after = apply_command(state, answer(state, fd.pokemon_id))
        self.assertIn("secret_plan_target_lost", [e["kind"] for e in after.log[len(state.log):]])
        self.assertIsNone(after.players[0].find_by_pokemon_id(fd.pokemon_id))
        self.assertEqual(after.players[0].active.pokemon_id, active)
        self.assertEqual(check_invariants(after), [])


if __name__ == "__main__":
    unittest.main()

"""LOST_TARGET の P1（おもての使い手の特殊能力で、本人のうらのカードを指定する経路）のエンジンの動作の根拠（docs/verification-ai-lost-target-own-face-down-design.md 8.1 の
E1〜E6）。エンジンの動作・裁定・カードデータは変えない（テストだけ。版 0.180.0 のまま）。

経路: ``engine._reveal_for_action`` は、使い手がおもてなら、source・target の場のポケモン、energy のついている場のポケモンの順に ``zones.designate_face_down``
（``can_lose=False``）を呼ぶ。指定したうらのカードの本当のカードが「たねポケモン」（``zones._secret_plan_keeps``。ネオより前の説明なのでベイビィをふくむ）でなければ、状態を
変える前に ``UNSUPPORTED_SECRET_PLAN_LOST_TARGET`` で止まる。持ち主が操作したプレイヤーなので ``IDENTITY_CONSULTED`` に記録せず、本当のカードによらない確かめ
（``engine._identity_independent``）には入らない。相手のうらのカードの指定（P2）は ``tests/test_secret_plan_v0_67.py`` の
``test_power_target_on_a_face_down_card_is_refused_for_every_identity``（変えない）。

盤面は ``tests/test_secret_plan_v0_67.py`` の ``place``・``full``・``face_down``・``uid_of``・``opponent_turn`` と ``build_test_state`` で作る（new_game からの対戦ではない）。
使い手はロケット団のヒトカゲ（［ほのおをもらう］。段は source → energy）。
"""

from __future__ import annotations

import json
import unittest

from kyuura_engine import AttachEnergy, UsePokemonPower
from kyuura_engine import engine as _engine
from kyuura_engine import zones as _zones
from kyuura_engine.cards import load_card_pool
from kyuura_engine.effects import TEXT_PRE_NEO, card_is_basic_in_text
from kyuura_engine.engine import apply_command, check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe, visible_log
from kyuura_engine.zones import SECRET_PLAN_LOST_TARGET_CODE
from tests.helpers import (
    DIGLETT,
    FIRE,
    HITMONCHAN,
    KADABRA,
    LT_SURGES_SECRET_PLAN,
    PSYCHIC,
    RATTATA,
    ROCKET_CHARMANDER,
    FIGHTING,
    build_test_state,
)
from tests.test_secret_plan_v0_67 import face_down, full, opponent_turn, place, uid_of

PICHU = "neo1-042"  # ピチュー（ネオ。ベイビィポケモン）。ネオより前の説明の「たねポケモン」に当たる（GR-2000-P325-PRE-NEO-BABY）
NOT_BASIC = (FIRE, PSYCHIC, KADABRA)  # エネルギー 2 種・1 進化（どれも「たねポケモン」でない）


def board(hand=(), opponent_hand=()):
    """自分（プレイヤー 0）のバトル場にロケット団のヒトカゲ（エネルギーなし）、ベンチに炎エネルギー 1 枚のコラッタ。手札にマチスの秘策 2 枚と ``hand``。
    相手のバトル場は闘エネルギー 1 枚のエビワラー、手札にマチスの秘策と ``opponent_hand``。"""
    return build_test_state([
        {"active": {"card": ROCKET_CHARMANDER, "energy": []}, "bench": [{"card": RATTATA, "energy": [FIRE]}],
         "hand": [LT_SURGES_SECRET_PLAN, LT_SURGES_SECRET_PLAN, *hand], "deck": [FIRE] * 10},
        {"active": {"card": HITMONCHAN, "energy": [FIGHTING]}, "bench": [], "hand": [LT_SURGES_SECRET_PLAN, *opponent_hand], "deck": [FIRE] * 10},
    ], turn_number=3, current_player=0)


def own_face_down(state, card_id, energy=None):
    """``card_id`` を本人のうらのカードとしてベンチに出し、手札の ``energy`` をそれにつける。(状態, うらの場のポケモン, ついたエネルギーの uid)。"""
    state = place(state, card_id)
    pokemon = next(q for q in face_down(state) if state.cards[q.card].card_id == card_id)
    attached = None
    if energy is not None:
        attached = uid_of(state, energy)
        state = apply_command(state, AttachEnergy(0, attached, pokemon.card))
    pokemon = state.players[0].find_by_pokemon_id(pokemon.pokemon_id)
    return state, pokemon, attached


def charmander(state):
    return state.players[0].active.pokemon_id


def public(state):
    """相手・観戦者の観測とログの写し（本当のカードが出ていないことの比べ）。"""
    return {str(v): (observe(state, v), visible_log(state, v)) for v in (1, None)}


class P1RejectionTest(unittest.TestCase):
    def rejected(self, state, command):
        before, seen = full(state), public(state)
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, command)
        self.assertEqual(ctx.exception.code, SECRET_PLAN_LOST_TARGET_CODE)
        self.assertEqual(full(state), before)  # 状態（ログ・決定・番・場）と乱数が変わらない
        self.assertEqual(public(state), seen)
        self.assertEqual(check_invariants(state), [])
        self.assertIsNone(state.decision)
        self.assertIsNone(_zones.IDENTITY_CONSULTED)  # 確かめのための記録を残さない
        return ctx.exception

    def assert_no_secret(self, error, card_id):
        definition = load_card_pool().get(card_id)
        text = json.dumps([error.code, error.message], ensure_ascii=False)
        self.assertNotIn(card_id, text)
        self.assertNotIn(definition.name_ja, text)

    def test_e1_source_is_own_non_basic_face_down(self):
        """E1: おもての使い手の source に、本人のたねでないうらのカード（energy もそのうらについている。保存済みの s1 の 2 件と同じ形）。"""
        for card_id in NOT_BASIC:
            with self.subTest(card=card_id):
                state, fd, energy = own_face_down(board(hand=(card_id, FIRE)), card_id, FIRE)
                self.assertIs(card_is_basic_in_text(load_card_pool().get(card_id), TEXT_PRE_NEO), False)
                error = self.rejected(state, UsePokemonPower(0, charmander(state), 0, source=fd.pokemon_id, energy=energy))
                self.assert_no_secret(error, card_id)

    def test_e2_only_the_energy_holder_is_own_non_basic_face_down(self):
        """E2: source はおもてのコラッタ、energy だけが本人のたねでないうらについたカード（energy のついているポケモンの指定）。"""
        state, _fd, energy = own_face_down(board(hand=(PSYCHIC, FIRE)), PSYCHIC, FIRE)
        rattata = state.players[0].bench[0]
        self.assertFalse(state.is_face_down(rattata))
        error = self.rejected(state, UsePokemonPower(0, charmander(state), 0, source=rattata.pokemon_id, energy=energy))
        self.assert_no_secret(error, PSYCHIC)

    def test_e5_opponent_face_down_elsewhere_does_not_change_it(self):
        """E5: 相手の場にも別のうらのカードがあるが、指定は本人のうらだけ。同じコード・状態は変わらない（相手のうらの確かめに入らない）。"""
        state, fd, energy = own_face_down(board(hand=(KADABRA, FIRE), opponent_hand=(DIGLETT,)), KADABRA, FIRE)
        state = place(opponent_turn(state), DIGLETT, player=1)
        state = opponent_turn(state)
        self.assertEqual((state.current_player, len(face_down(state, 0)), len(face_down(state, 1))), (0, 1, 1))
        calls = []
        original = _engine._identity_independent
        try:
            _engine._identity_independent = lambda *a, **k: calls.append(1) or original(*a, **k)
            error = self.rejected(state, UsePokemonPower(0, charmander(state), 0, source=fd.pokemon_id, energy=energy))
        finally:
            _engine._identity_independent = original
        self.assertEqual(calls, [])
        self.assert_no_secret(error, KADABRA)

    def test_e6_basic_first_then_non_basic(self):
        """E6: source に本人のたねのうら（先に指定。おもてにする）、energy に本人のたねでないうらについたカード（後に指定）。このコードで、先におもてにしたたねもふくめ
        状態は変わらない。"""
        state, basic, _ = own_face_down(board(hand=(DIGLETT, PSYCHIC, FIRE)), DIGLETT)
        state, non_basic, energy = own_face_down(state, PSYCHIC, FIRE)
        self.assertEqual(len(face_down(state)), 2)
        self.rejected(state, UsePokemonPower(0, charmander(state), 0, source=basic.pokemon_id, energy=energy))


class P1BasicContrastTest(unittest.TestCase):
    """E3・E4: 本人のうらのカードがたね・ベイビィなら、このコードにならない（おもてにして特殊能力の確かめへ進む）。"""

    def used(self, card_id):
        state, fd, energy = own_face_down(board(hand=(card_id, FIRE)), card_id, FIRE)
        self.assertIs(card_is_basic_in_text(load_card_pool().get(card_id), TEXT_PRE_NEO), True)
        after = apply_command(state, UsePokemonPower(0, charmander(state), 0, source=fd.pokemon_id, energy=energy))
        revealed = [e for e in after.log[len(state.log):] if e["kind"] == "secret_plan_revealed"]
        self.assertEqual([(e["cause"], e["pokemon_id"]) for e in revealed], [("power", fd.pokemon_id)])
        kept = after.players[0].find_by_pokemon_id(fd.pokemon_id)
        self.assertFalse(after.is_face_down(kept))
        self.assertEqual(after.players[0].active.energy, [energy])  # ［ほのおをもらう］で炎エネルギーがヒトカゲに移った
        self.assertEqual(check_invariants(after), [])

    def wrong_type(self, card_id):
        state, fd, energy = own_face_down(board(hand=(card_id, PSYCHIC)), card_id, PSYCHIC)
        before = full(state)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, UsePokemonPower(0, charmander(state), 0, source=fd.pokemon_id, energy=energy))
        self.assertEqual(ctx.exception.code, "WRONG_ENERGY_TYPE")
        self.assertEqual(full(state), before)

    def test_e3_basic(self):
        self.used(DIGLETT)
        self.wrong_type(DIGLETT)

    def test_e4_baby(self):
        self.used(PICHU)
        self.wrong_type(PICHU)


if __name__ == "__main__":
    unittest.main()

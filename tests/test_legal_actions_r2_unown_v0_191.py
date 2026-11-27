"""v0.191（R-2 のアンノーンの［XXXXX］・［ANGER］。docs/r2-unown-design.md）: 本人のうらのバトル場のアンノーンのワザの宣言に、自分の場の別のおもての持ち主の
［XXXXX］（``CoinsUntilTailsBonusToGroupAttack``）・［ANGER］（``CounterBonusToGroupAttack``）を示す。

0.190.0 まで、うらの分岐（``_face_down_attack_candidate``）は、本当のカードが特殊能力を持てば 2 段目に何も示さなかった（アンノーンは 26 枚とも特殊能力を持つ）。
0.191.0 では、次のすべてを満たすとき、2 段目にその力（``with_power``。持ち主ごとに 1 つ・場の並び）を、その力の対象のワザにだけ示す（unverified・face_down_reveal_not_evaluated）:

- 番のプレイヤーの main の段階で、本人のバトル場のポケモンがうら（候補を作る呼び出し元の条件）
- 本当のカード（``printed_def``）の名前のグループが、力の対象のグループ（``group``）と同じ
- 本当のカードの特殊能力の型が、すべて分類済みの 22 型（``FACE_DOWN_GROUP_POWER_ATTACKER_TYPES``。docs/r2-unown-design.json の ``types``）のどれか
- ワザの印刷の名前が、力の対象のワザ（``attack_name``。めざめるパワー）と同じ（ワザごとの ``options_by_choice``・組）
- 持ち主は自分の場のおもてのポケモンで、使い手と別。力が消えていない・使えない効果を受けていない・この番のほかの個体の使用の記録がない

自己持ち主（R3）・変身の経路（メタモン）・分類にない型は示さない。check は形と、同じ力（``exclusive_key``）を 2 つ指す組の拒否だけ（エンジンを呼ばない）。送信のあとの順
（おもてにする → 確かめ・先読み・処理）と、XP1・NT1・v0.4b の既存の停止は変えない。

構築盤面（``test_secret_plan_v0_67`` の ``board``・``place``・``to_active`` を再利用。new_game からの到達ではない）。本当のカード・持ち主はどれも登録された実在のカード
（アンノーン N・Y・I・X・A・P・メタモン 2 種・サカキのニドラン♂・ベトベトン・ピチュー・キョウのポッポ・キョウ秘伝,変わり身の術）。実在しない登録・組み合わせは次の 3 つだけを
人工的に作り、名前に ``artificial`` をつけて区別する:

- 「めざめるパワー」でない 2 つめのワザを持つアンノーン（印刷の定義のワザだけを差しかえる。登録にない）
- 分類済みの型の集合から 1 型を除いた範囲（閉じた範囲の確かめ）
- 分類にない型を持つ、名前のグループがアンノーンのカード（登録の検査が見つけることの確かめ。プール・登録表を差しかえない）

使えない効果（``CannotUsePowers``）・この番のほかの X の使用の記録・相手のダメージを受けない状態（``PreventDamage``）は、到達できる状態を直接入れて作る（``injected``）。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest
from unittest import mock

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import effects as E
from kyuura_engine import engine as EN
from kyuura_engine import legal_actions as L
from kyuura_engine.cards import load_card_pool
from kyuura_engine.client_api import ClientHub
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import AttachEnergy, UseAttack
from kyuura_engine.observation import observe
from kyuura_engine.serialize import rng_fingerprint
from kyuura_engine.state import GROUP_ATTACK_POWER_USED, CannotUsePowers, GameState, PreventDamage, TrainerTurnEffect
from tests import helpers as H
from tests import test_damage_reactions_poison_sleep_v0_119 as T119
from tests import test_secret_plan_v0_67 as S
from tests.test_legal_actions_r2_stadium_coin_v0_188 import OLD_NOTE, attack_of, check_code, host_candidates
from tests.test_legal_actions_u7_1 import snap, without_handles
from tests.test_legal_actions_u7_4 import attack_stages, via_direct, via_u7

ROOT = pathlib.Path(__file__).resolve().parent.parent
DESIGN = ROOT / "docs" / "r2-unown-design.json"
REQ = {"contract": "kyuura-client-api", "format": 1}
HD, TL = CoinSide.HEADS, CoinSide.TAILS
COINS = (HD, HD, TL, *[TL] * 6)  # ［XXXXX］: 「おもて」2 枚
UNOWN_X, UNOWN_A = "neo4-065", "neo2-030"  # ［XXXXX］・［ANGER］の持ち主
UNOWN_N, UNOWN_Y, UNOWN_I, UNOWN_P = "PF2-001", "neo3-033", "neo2-023", "neo4-058"  # 常にはたらく・宣言して使う・場に出したとき・［PERFORM］
DITTO_SUPER = "ES2-032"  # メタモン（SuperTransformPower）
PICHU = "neo1-042"  # ピチュー（ベイビィ）
X_POWER, A_POWER = "XXXXX[?????]", "ANGER[アンガー]"


def mon(card, energy=(), **extra):
    return {"card": card, "energy": list(energy), **extra}


def fd(real=UNOWN_N, *, bench=(mon(UNOWN_X),), opponent=None, opponent_bench=(), opponent_hand=(), energies=1, extra_hand=()):
    """プレイヤー 0 の番の main。バトル場はうらの ``real``（マチスの秘策）で超エネルギーが ``energies`` 枚。相手のバトル場は既定でイワーク（超の弱点・抵抗力なし）。"""
    state = S.board(hand=(real, *([H.PSYCHIC] * max(energies, 1)), *extra_hand), bench=bench, opponent=opponent or mon(H.ONIX),
                    opponent_bench=opponent_bench, opponent_hand=opponent_hand, turn_number=7)
    state = S.place(state, real)
    state = S.to_active(state, S.face_down(state)[0])
    state = S.opponent_turn(S.opponent_turn(state))
    for _ in range(energies):
        state = S.apply_command(state, AttachEnergy(0, S.uid_of(state, H.PSYCHIC), state.players[0].active.card))
    active = state.players[0].active
    assert state.is_face_down(active) and len(active.energy) == energies and state.current_player == 0 and state.decision is None
    return state


def face_up(real=UNOWN_N, *, bench=(mon(UNOWN_X),)):
    """おもての対照（同じ本当のカードがおもてでバトル場）。"""
    return H.build_test_state([{"active": mon(real, (H.PSYCHIC,)), "bench": list(bench), "hand": [], "deck": [H.FIRE] * 10},
                               {"active": mon(H.ONIX), "bench": [], "hand": [], "deck": [H.FIRE] * 10}], turn_number=9, current_player=0)


def holders(state, card, player=0):
    return [p.pokemon_id for p in state.players[player].bench if not state.is_face_down(p) and state.cards[p.card].card_id == card]


def powers_of(stages):
    return [o for o in stages[1]["options"] if o["addon"] == L.ADDON_WITH_POWER]


def attack_ids(stages):
    return [o["id"] for o in stages[0]["options"]]


def registry_unown():
    """登録の全件から、名前のグループがアンノーンのカード（カード id → 特殊能力の効果の型の名前の並び。登録がない特殊能力は None）。"""
    pool = load_card_pool()
    found = {}
    for card_id, definition in pool.definitions.items():
        if definition.category == "pokemon" and definition.name_group == "アンノーン":
            entries = [E.DEFAULT_EFFECTS.power_entry(card_id, power.index) for power in definition.powers]
            found[card_id] = [None if entry is None else type(entry.effect).__name__ for entry in entries]
    return pool, found


def unclassified(found, classified):
    """分類にない（または登録のない）特殊能力を持つカード id（登録の検査）。"""
    return sorted(card_id for card_id, types in found.items() if not types or any(t is None or t not in classified for t in types))


def with_injected_use_record(state, used_holder):
    state = state.clone()
    state.trainer_effects = (*state.trainer_effects, TrainerTurnEffect(kind=GROUP_ATTACK_POWER_USED, player=0, source_card=state.find_pokemon(used_holder)[1].card,
                                                                       card_id=UNOWN_X, created_turn=state.turn_number, expires_turn=state.turn_number,
                                                                       pokemon_id=used_holder))
    return state


def with_injected_prevented(state, holder_id):
    state = state.clone()
    holder = state.find_pokemon(holder_id)[1]
    holder.persistent_effects = (*holder.persistent_effects, CannotUsePowers(source_card=state.players[1].active.card, source_player=1,
                                                                              created_turn=state.turn_number - 1, active_turn=state.turn_number))
    return state


class OfferTest(unittest.TestCase):
    """示す条件を満たすとき、2 段目に持ち主ごとに［XXXXX］・［ANGER］を示す（対象のワザにだけ）。"""

    def assert_offered(self, state, expected, note=None):
        """``expected``: [(持ち主の場の番号, 力の名前), ...]（場の並び）。``note``: v0.192 から、使い手自身の力を示すときは NOTE_FACE_DOWN_SELF_GROUP_POWERS。"""
        _h, session, r, c, inputs = attack_of(state)
        self.assertEqual((c["processability"], c["reasons"], c["input_disclosure"]), (L.UNVERIFIED, [L.REASON_FACE_DOWN], L.DISCLOSURE_CONFIRMED))
        self.assertEqual(c["guarantees"], L.GUARANTEE_FACE_DOWN_ATTACK)
        first, second = inputs["stages"]
        ids = attack_ids(inputs["stages"])
        powers = powers_of(inputs["stages"])
        self.assertEqual([(o["pokemon"], o["power"]) for o in powers], expected)
        self.assertEqual([o["id"] for o in second["options"]], [f"o{len(ids) + i + 1}" for i in range(len(expected))])
        for o in powers:
            self.assertEqual((o["processability"], o["reasons"]), (L.UNVERIFIED, [L.REASON_FACE_DOWN]))
        self.assertEqual(second["count"], {"min": 0, "max": len(second["options"])})
        self.assertEqual(second["options_by_choice"],
                         {aid: [{"option": o["id"], "eligible": True, "processability": L.UNVERIFIED, "reasons": [L.REASON_FACE_DOWN]} for o in second["options"]]
                          for aid in ids})
        self.assertEqual((second["distinct"], second["decline"], second["depends_on_stage"], second["order"], second["order_preserved"], second["note"]),
                         (True, True, 1, L.ORDER_SIGNIFICANT, True, note or L.NOTE_FACE_DOWN_GROUP_POWERS))
        self.assertEqual(c["choices_format"], "[ワザの番号, 宣言といっしょに選ぶものの番号, ...]（いっしょに選ぶものは選んだ順。0 個でもよい）")
        return session, r, c, inputs, ids, powers

    def test_xxxxx_offered(self):
        state = fd()
        _s, _r, _c, inputs, ids, _p = self.assert_offered(state, [(holders(state, UNOWN_X)[0], X_POWER)])
        self.assertEqual(len(ids), 1)
        self.assertEqual(inputs["stages"][0]["options"][0]["name_ja"], "めざめるパワー")

    def test_anger_offered(self):
        state = fd(bench=(mon(UNOWN_A, damage=20),))
        self.assert_offered(state, [(holders(state, UNOWN_A)[0], A_POWER)])
        state = fd(bench=(mon(UNOWN_A),))  # ダメージカウンター 0 個でも示す（量は予告しない）
        self.assert_offered(state, [(holders(state, UNOWN_A)[0], A_POWER)])

    def test_every_classified_cause_group_is_offered(self):
        """使い手の本当のカードの型の原因群（常にはたらく N・宣言して使う Y・場に出したとき I・［XXXXX］の X・［ANGER］の A・［PERFORM］の P）。どれも別の持ち主を示す。
        v0.192 から、本当のカードが X・A なら、使い手自身の力を先頭に示す（tests/test_legal_actions_r2_unown_self_v0_192.py。0.191.0 では示さなかった）。"""
        own = {UNOWN_X: X_POWER, UNOWN_A: A_POWER}
        for real in (UNOWN_N, UNOWN_Y, UNOWN_I, UNOWN_X, UNOWN_A, UNOWN_P):
            with self.subTest(real=real):
                state = fd(real, bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X)))
                others = [(holders(state, UNOWN_A)[0], A_POWER), (holders(state, UNOWN_X)[0], X_POWER)]
                if real in own:
                    self.assert_offered(state, [(state.players[0].active.pokemon_id, own[real]), *others], note=L.NOTE_FACE_DOWN_SELF_GROUP_POWERS)
                else:
                    self.assert_offered(state, others)

    def test_multiple_holders_in_field_order_and_the_same_power_twice_is_refused(self):
        state = fd(bench=(mon(UNOWN_X), mon(UNOWN_A, damage=20), mon(UNOWN_X), mon(UNOWN_A, damage=10)))  # ベンチは 5 匹まで（うらの使い手の場所を残す）
        x1, x2 = holders(state, UNOWN_X)
        a1, a2 = holders(state, UNOWN_A)
        session, r, c, inputs, ids, powers = self.assert_offered(state, [(x1, X_POWER), (a1, A_POWER), (x2, X_POWER), (a2, A_POWER)])
        self.assertEqual([o["bench_index"] for o in powers], [0, 1, 2, 3])
        ox1, oa1, ox2, oa2 = (o["id"] for o in powers)
        for choices, code in (([ids[0]], None), ([ids[0], ox1], None), ([ids[0], oa2], None), ([ids[0], ox1, oa1], None), ([ids[0], oa1, ox2], None),
                              ([ids[0], ox1, ox2], L.CANDIDATE_INPUT_INVALID), ([ids[0], oa1, oa2], L.CANDIDATE_INPUT_INVALID),
                              ([ids[0], ox1, oa1, ox2], L.CANDIDATE_INPUT_INVALID), ([ids[0], ox1, ox1], L.CANDIDATE_INPUT_INVALID)):
            with self.subTest(choices=choices):
                self.assertEqual(check_code(session, r, c, choices), code)
        # おもての宣言（エンジンの確かめ）も、同じ力を 2 つ指す組を同じ区分で拒否する
        up = face_up(bench=(mon(UNOWN_X), mon(UNOWN_A, damage=20), mon(UNOWN_X), mon(UNOWN_A, damage=10)))
        _h, up_session, up_r, up_c, up_inputs = attack_of(up)
        up_x1, _a1, up_x2, _a2 = (o["id"] for o in powers_of(up_inputs["stages"]))
        self.assertEqual(check_code(up_session, up_r, up_c, [attack_ids(up_inputs["stages"])[0], up_x1, up_x2]), L.CANDIDATE_INPUT_INVALID)

    def test_same_shape_as_the_face_up_declaration(self):
        """段・選べるもの・組の項目の名前と、力の選べるものの値（持ち主・力の名前・場所）は、おもてのワザの宣言と同じ。"""
        bench = (mon(UNOWN_A, damage=20), mon(UNOWN_X))
        _fc, up = attack_stages(face_up(bench=bench))
        state = fd(bench=bench)
        _s, _r, c, inputs, ids, powers = self.assert_offered(state, [(holders(state, UNOWN_A)[0], A_POWER), (holders(state, UNOWN_X)[0], X_POWER)])
        down = inputs["stages"]
        self.assertEqual(set(down[1]) - {"note"}, set(up[1]) - {"note"})
        self.assertEqual({k: v for k, v in down[1].items() if k not in ("note", "options", "options_by_choice", "count")},
                         {k: v for k, v in up[1].items() if k not in ("note", "options", "options_by_choice", "count")})
        up_powers = powers_of(up)
        self.assertEqual([set(o) for o in powers], [set(o) for o in up_powers])
        for key in ("addon", "power", "zone", "bench_index", "card_id"):
            self.assertEqual([o[key] for o in powers], [o[key] for o in up_powers], key)
        self.assertEqual(set(up[1]["options_by_choice"][up[0]["options"][0]["id"]][0]), set(down[1]["options_by_choice"][ids[0]][0]))
        self.assertEqual(c["choices_format"], next(x for x in host_candidates(face_up(bench=bench)) if x["kind"] == L.KIND_USE_ATTACK)["choices_format"])

    def test_check_is_shape_only(self):
        state = fd(energies=0)  # 必要なエネルギーが足りなくても、check は形だけ（エンジンを呼ばない）
        _h, session, r, c, inputs = attack_of(state)
        ids = attack_ids(inputs["stages"])
        x = powers_of(inputs["stages"])[0]["id"]
        for choices, code in (([ids[0]], None), ([ids[0], x], None), ([x], L.CANDIDATE_INPUT_INVALID), ([x, ids[0]], L.CANDIDATE_INPUT_INVALID),
                              ([ids[0], "o9"], L.CANDIDATE_INPUT_INVALID), ([ids[0], 3], L.CANDIDATE_INPUT_INVALID), ([], L.CANDIDATE_INPUT_INVALID)):
            with self.subTest(choices=choices):
                self.assertEqual(check_code(session, r, c, choices), code)

    def test_only_the_power_used_by_another_x_this_turn_is_hidden_injected(self):
        """この番のほかの X の使用の記録（注入）: 記録のない側の X だけが使えない（other_use_problem）。記録を持つ個体自身は示す（エンジンと同じ読み方）。"""
        state = fd(bench=(mon(UNOWN_X), mon(UNOWN_X)))
        x1, x2 = holders(state, UNOWN_X)
        self.assert_offered(with_injected_use_record(state, x1), [(x1, X_POWER)])

    def test_artificial_second_attack_depends_on_the_attack_name(self):
        """人工: 「めざめるパワー」でない 2 つめのワザを持つアンノーン（登録にない）。力はめざめるパワーにだけ示し、ほかのワザとの組は形の検査で拒否する。"""
        state = fd()
        card = state.players[0].active.card
        extra = dataclasses.replace(load_card_pool().get(UNOWN_N).attacks[0], index=1, name_ja="ひっかく")
        original = GameState.printed_def

        def printed(self, uid):
            found = original(self, uid)
            return dataclasses.replace(found, attacks=(*found.attacks, extra)) if uid == card else found
        with mock.patch.object(GameState, "printed_def", printed):
            _h, session, r, c, inputs = attack_of(state)
        first, second = inputs["stages"]
        self.assertEqual([o["name_ja"] for o in first["options"]], ["めざめるパワー", "ひっかく"])
        (power,) = powers_of(inputs["stages"])
        self.assertEqual(second["options_by_choice"], {"o1": [{"option": power["id"], "eligible": True, "processability": L.UNVERIFIED, "reasons": [L.REASON_FACE_DOWN]}],
                                                       "o2": []})
        with mock.patch.object(GameState, "printed_def", printed):
            for choices, code in ((["o1", power["id"]], None), (["o2"], None), (["o2", power["id"]], L.CANDIDATE_INPUT_INVALID)):
                with self.subTest(choices=choices):
                    self.assertEqual(check_code(session, r, c, choices), code)


class NotOfferedTest(unittest.TestCase):
    """条件を満たさないときは、0.190.0 と同じ 2 段目（空）のまま。"""

    def assert_not_offered(self, state):
        _h, session, r, c, inputs = attack_of(state)
        self.assertEqual((c["processability"], c["reasons"], c["choices_format"]), (L.UNVERIFIED, [L.REASON_FACE_DOWN], "[ワザの番号]"))
        first, second = inputs["stages"]
        ids = [o["id"] for o in first["options"]]
        self.assertEqual((second["count"], second["options"], second["options_by_choice"], second["order"], second["note"]),
                         ({"min": 0, "max": 0}, [], {oid: [] for oid in ids}, L.ORDER_NOT_APPLICABLE, OLD_NOTE))
        self.assertEqual(check_code(session, r, c, [ids[0], f"o{len(ids) + 1}"]), L.CANDIDATE_INPUT_INVALID)
        self.assertIsNone(check_code(session, r, c, [ids[0]]))

    def test_self_holder_is_offered_from_v0_192(self):
        """自己持ち主（R3。本当のカードが X・A で、ほかに持ち主がいない）: 0.191.0 では示さなかった（対象外）。v0.192 から示す（条件・値・check・送信・情報境界は
        tests/test_legal_actions_r2_unown_self_v0_192.py）。"""
        for real, power in ((UNOWN_X, X_POWER), (UNOWN_A, A_POWER)):
            with self.subTest(real=real):
                state = fd(real, bench=(mon(H.RATTATA),))
                _h, _s, _r, _c, inputs = attack_of(state)
                self.assertEqual([(o["pokemon"], o["zone"], o["power"]) for o in powers_of(inputs["stages"])],
                                 [(state.players[0].active.pokemon_id, "active", power)])

    def test_transform_route_is_not_offered(self):
        """変身の経路（本当のカードがメタモン 2 種。相手のバトル場がアンノーンでも）は示さない（TF・R4）。メタモンは印刷のワザがないので、うらの分岐の候補は 0.180.0 からの
        「印刷のワザなし」（段なし）のまま（直接のコマンドでは、公開のあと変身の姿のワザで受け付けうる。前提確認の記録）。"""
        for real in (H.DITTO, DITTO_SUPER):
            with self.subTest(real=real):
                state = fd(real, bench=(mon(UNOWN_X),), opponent=mon(UNOWN_X, (H.PSYCHIC,)))
                _h, _s, _r, c, inputs = attack_of(state)
                self.assertEqual((c["processability"], c["reasons"]), (L.NOT_IMPLEMENTED, [L.REASON_FACE_DOWN, L.REASON_NO_PRINTED_ATTACK]))
                self.assertNotIn(L.ADDON_WITH_POWER, json.dumps(inputs, ensure_ascii=False))
                self.assertEqual(L._face_down_addon_specs(state, 0, state.printed_def(state.players[0].active.card)), [])

    def test_not_unown(self):
        self.assert_not_offered(fd(H.GIOVANNIS_NIDORAN_M, bench=(mon(UNOWN_X), mon(UNOWN_A, damage=20))))

    def test_artificial_unclassified_type_is_not_offered(self):
        """人工: 分類済みの型の集合から使い手の型（N の ReduceOwnGroupDamageFromType）を除くと示さない（未知の型を自動で安全としない）。"""
        narrowed = L.FACE_DOWN_GROUP_POWER_ATTACKER_TYPES - {"ReduceOwnGroupDamageFromType"}
        with mock.patch.object(L, "FACE_DOWN_GROUP_POWER_ATTACKER_TYPES", narrowed):
            self.assert_not_offered(fd(UNOWN_N))
            _h, _s, _r, _c, inputs = attack_of(fd(UNOWN_Y))  # ほかの型の使い手は示す
            self.assertEqual(len(powers_of(inputs["stages"])), 1)

    def test_holder_face_down(self):
        state = fd(bench=(mon(H.RATTATA),), extra_hand=(H.LT_SURGES_SECRET_PLAN, UNOWN_X))
        state = S.place(state, UNOWN_X)
        self.assertEqual(sum(1 for p in state.players[0].bench if state.is_face_down(p)), 1)
        self.assert_not_offered(state)

    def test_holder_on_the_opponents_field(self):
        self.assert_not_offered(fd(bench=(mon(H.RATTATA),), opponent_bench=(mon(UNOWN_X), mon(UNOWN_A, damage=20))))

    def test_holder_power_suppressed(self):
        self.assert_not_offered(fd(bench=(mon(UNOWN_X), T119.mon(H.MUK))))  # 自分のベンチのベトベトンのかがくへんかガス
        self.assert_not_offered(fd(bench=(mon(UNOWN_A, damage=20),), opponent_bench=(T119.mon(H.MUK),)))  # 相手の場のかがくへんかガス

    def test_injected_holder_use_prevented(self):
        state = fd(bench=(mon(UNOWN_X),))
        self.assert_not_offered(with_injected_prevented(state, holders(state, UNOWN_X)[0]))

    def test_injected_other_x_used_this_turn(self):
        state = fd(bench=(mon(UNOWN_X), mon(UNOWN_X)))
        x1, x2 = holders(state, UNOWN_X)
        used = with_injected_use_record(state, x1)
        hidden = with_injected_prevented(used, x1)  # 記録を持つ個体は使えない効果で外し、記録で外れる側だけを残す
        self.assert_not_offered(hidden)

    def test_no_holder(self):
        self.assert_not_offered(fd(bench=(mon(H.RATTATA),)))

    def test_not_the_actors_turn(self):
        self.assertEqual([c["kind"] for c in host_candidates(fd(), actor=1)], [])


class SubmitTest(unittest.TestCase):
    """送信は既存のコマンド（UseAttack(with_power / with_powers)）と同じ結果。処理の順と既存の停止は変えない。"""

    def assert_same(self, state, choices, command, outcome):
        host, result = via_u7(state, lambda s: choices)
        game, direct = via_direct(state, command)
        self.assertEqual(result.outcome, outcome, result)
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual(snap(host.game.state), snap(game.state))
        return host, result

    def test_xxxxx_and_anger_same_as_direct(self):
        state = H.with_coin_bits(fd(bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X))), *COINS)
        a, x = holders(state, UNOWN_A)[0], holders(state, UNOWN_X)[0]
        cases = ((["o1"], UseAttack(0, 0), 10), (["o1", "o3"], UseAttack(0, 0, with_power=x), 30), (["o1", "o2"], UseAttack(0, 0, with_power=a), 30),
                 (["o1", "o2", "o3"], UseAttack(0, 0, with_powers=(a, x)), 50), (["o1", "o3", "o2"], UseAttack(0, 0, with_powers=(x, a)), 50))
        for choices, command, damage in cases:
            with self.subTest(choices=choices):
                host, _ = self.assert_same(state, choices, command, D.ACCEPTED)
                after = host.game.state
                self.assertEqual(after.players[1].active.damage, damage)
                self.assertFalse(after.is_face_down(after.players[0].active))
                if damage > 10:
                    self.assertEqual({m[0] for m in T119.last(after, "damage")["modifiers"]}, {6})

    def test_face_down_matches_face_up_values(self):
        """同じ本当のカード・同じ持ち主・同じコインで、うらからの送信とおもての宣言のダメージが同じ（［PERFORM］の P も、公開の直後の追加は 0）。"""
        for real in (UNOWN_N, UNOWN_P):
            with self.subTest(real=real):
                bench = (mon(UNOWN_A, damage=20), mon(UNOWN_X))
                down = H.with_coin_bits(fd(real, bench=bench), *COINS)
                up = H.with_coin_bits(face_up(real, bench=bench), *COINS)
                host, _ = via_u7(down, lambda s: ["o1", "o2", "o3"])
                up_host, up_result = via_u7(up, lambda s: [s[0]["options"][0]["id"], *(o["id"] for o in powers_of(s))])
                self.assertEqual(up_result.outcome, D.ACCEPTED)
                self.assertEqual(host.game.state.players[1].active.damage, up_host.game.state.players[1].active.damage)
                self.assertEqual(host.game.state.players[1].active.damage, 50)

    def test_second_holder_same_as_direct(self):
        state = H.with_coin_bits(fd(bench=(mon(UNOWN_X), mon(UNOWN_X))), *COINS)
        x1, x2 = holders(state, UNOWN_X)
        self.assert_same(state, ["o1", "o3"], UseAttack(0, 0, with_power=x2), D.ACCEPTED)
        self.assert_same(state, ["o1", "o2"], UseAttack(0, 0, with_power=x1), D.ACCEPTED)

    def test_existing_stops_are_kept_and_change_nothing(self):
        """XP1（相手のバトル場のベイビィ）・NT1（相手の変わり身の術）・v0.4b（相手のダメージを受けない状態。注入）: ［XXXXX］を選ぶと check は valid、送信は既存の停止で
        拒否（状態・乱数・ログ・決定が不変、ほかの人に知らせない）。［ANGER］だけ・力なしは止めない（既存の処理）。"""
        bench = (mon(UNOWN_X), mon(UNOWN_A, damage=20))
        baby = fd(bench=bench, opponent=mon(PICHU), opponent_bench=(mon(H.RATTATA),))
        trick = fd(bench=bench, opponent=mon(H.KOGAS_PIDGEY, trainers=[(H.KOGAS_NINJA_TRICK, None)]), opponent_bench=(mon(H.RATTATA),))
        prevented = fd(bench=bench).clone()
        opp = prevented.players[1].active
        opp.persistent_effects = (*opp.persistent_effects, PreventDamage(opp.card, 1, prevented.turn_number - 1, prevented.turn_number))
        for name, state, code in (("baby", baby, "UNRESOLVED_GROUP_POWER_COIN_ORDER"), ("ninja_trick", trick, "UNRESOLVED_NINJA_TRICK_ATTACK_COIN_ORDER"),
                                  ("prevented_injected", prevented, "UNRESOLVED_PREVENTED_COIN_DAMAGE")):
            with self.subTest(name=name):
                state = H.with_coin_bits(state, HD, *COINS)
                x, a = holders(state, UNOWN_X)[0], holders(state, UNOWN_A)[0]
                hosted = A.HostedGame(state.clone())
                hub = ClientHub(hosted)
                me = hub.player(0)
                r = me.handle({**REQ, "type": "candidates"})["response"]
                c = next(x_ for x_ in r["candidates"] if x_["kind"] == L.KIND_USE_ATTACK)
                stages = me.handle({**REQ, "type": "inputs", "game": r["game"], "revision": r["revision"], "candidate": c["id"]})["response"]["stages"]
                self.assertEqual([(o["pokemon"], o["power"]) for o in powers_of(stages)], [(x, X_POWER), (a, A_POWER)])
                checked = me.handle({**REQ, "type": "check", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o1", "o2"]})
                self.assertTrue(checked["response"]["valid"])
                hub.take_updates(1), hub.take_updates("spectator")
                before = snap(hosted.state)
                sent = me.handle({**REQ, "type": "submit", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o1", "o2"]})
                self.assertEqual(sent["outcome"], D.REJECTED)
                self.assertEqual(snap(hosted.state), before)
                self.assertEqual([hub.take_updates(v) for v in (1, "spectator")], [[], []])
                game, direct = via_direct(state, UseAttack(0, 0, with_power=x))
                self.assertEqual(direct.outcome, D.REJECTED)
                self.assertEqual(direct.diagnosis.case_id, code)
                self.assertEqual(snap(game.state), snap(state))
                self.assert_same(state, ["o1", "o3"], UseAttack(0, 0, with_power=a), D.ACCEPTED)
                self.assert_same(state, ["o1"], UseAttack(0, 0), D.ACCEPTED)

    def test_rejection_after_reveal_same_as_direct(self):
        """必要なエネルギーが足りない: おもてにしたあとエンジンが拒否（状態・乱数・ログ・決定が不変）。"""
        state = fd(energies=0)
        self.assert_same(state, ["o1", "o2"], UseAttack(0, 0, with_power=holders(state, UNOWN_X)[0]), D.REJECTED)
        self.assertEqual(snap(via_direct(state, UseAttack(0, 0, with_power=holders(state, UNOWN_X)[0]))[0].state), snap(state))

    def test_api_submit_same_as_direct(self):
        state = H.with_coin_bits(fd(bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X))), *COINS)
        hosted = A.HostedGame(state.clone())
        me = ClientHub(hosted).player(0)
        r = me.handle({**REQ, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == L.KIND_USE_ATTACK)
        sent = me.handle({**REQ, "type": "submit", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o1", "o3", "o2"]})
        game, direct = via_direct(state, UseAttack(0, 0, with_powers=(holders(state, UNOWN_X)[0], holders(state, UNOWN_A)[0])))
        self.assertEqual((sent["outcome"], direct.outcome), (D.ACCEPTED, D.ACCEPTED))
        self.assertEqual(snap(hosted.state), snap(game.state))


class RegistryTest(unittest.TestCase):
    """登録と分類: 今の登録（26 枚・能力名 26・効果型 22）と、分類済みの型の閉じた範囲が一致する。"""

    def test_current_registry_counts(self):
        pool, found = registry_unown()
        self.assertEqual(len(found), 26)
        names = {power.name_ja for card_id in found for power in pool.get(card_id).powers}
        self.assertEqual(len(names), 26)
        self.assertEqual(len({t for types in found.values() for t in types}), 22)
        self.assertTrue(all(len(types) == 1 for types in found.values()))
        self.assertTrue(all([a.name_ja for a in pool.get(card_id).attacks] == ["めざめるパワー"] for card_id in found))

    def test_every_registered_unown_is_classified_and_the_range_matches(self):
        _pool, found = registry_unown()
        self.assertEqual(unclassified(found, L.FACE_DOWN_GROUP_POWER_ATTACKER_TYPES), [])
        self.assertEqual({t for types in found.values() for t in types}, set(L.FACE_DOWN_GROUP_POWER_ATTACKER_TYPES))
        design = json.loads(DESIGN.read_text(encoding="utf-8"))
        self.assertEqual({t["type"] for t in design["types"]}, set(L.FACE_DOWN_GROUP_POWER_ATTACKER_TYPES))
        self.assertTrue(all(t["class_as_attacker_r2"] == "A" for t in design["types"]))
        for name in L.FACE_DOWN_GROUP_POWER_ATTACKER_TYPES:
            self.assertTrue(issubclass(getattr(E, name), E.PowerEffect), name)
            for risky in ("SuppressOtherPowers", "ScareOpponentBabies", "FailAndReturnOnAttack", "TransformIntoDefender", "SuperTransformPower"):
                self.assertFalse(issubclass(getattr(E, name), getattr(E, risky)), (name, risky))

    def test_artificial_new_or_unregistered_type_is_detected(self):
        """人工: 分類にない型・登録のない特殊能力を持つアンノーンが加わったら、登録の検査が見つける（プール・登録表は差しかえない）。"""
        _pool, found = registry_unown()
        added = {**found, "artificial-unown-1": ["SuppressOtherPowers"], "artificial-unown-2": [None], "artificial-unown-3": []}
        self.assertEqual(unclassified(added, L.FACE_DOWN_GROUP_POWER_ATTACKER_TYPES), ["artificial-unown-1", "artificial-unown-2", "artificial-unown-3"])

    def test_holder_types_are_the_two_group_attack_powers(self):
        _pool, found = registry_unown()
        holders_found = sorted(card_id for card_id, types in found.items() if any(issubclass(getattr(E, t), E.AttackDeclaredPower) for t in types))
        self.assertEqual(holders_found, [UNOWN_A, UNOWN_X])


class BoundaryTest(unittest.TestCase):
    """情報境界: 候補・入力・check は本人の知識と公開の状態だけで決まり、ほかの人への応答・通知を変えない。"""

    def own_view(self, state):
        _h, session, r, c, inputs = attack_of(state)
        checks = [check_code(session, r, c, ch) for ch in (["o1"], ["o1", "o2"], ["o1", "o3"], ["o1", "o2", "o3"], ["o2"])]
        return without_handles(r), inputs, checks

    def test_opponent_secrets_do_not_change_the_actors_inputs(self):
        bench = (mon(UNOWN_A, damage=20), mon(UNOWN_X))
        views = [self.own_view(fd(bench=bench, opponent_hand=hand)) for hand in ((H.FIRE, H.FIRE), (H.RATTATA, H.POTION), ())]
        self.assertEqual(views[0], views[1])
        self.assertEqual([v[1] for v in views], [views[0][1]] * 3)
        self.assertEqual([v[2] for v in views], [views[0][2]] * 3)

    def test_the_actors_real_card_does_not_reach_others(self):
        others = []
        for real in (UNOWN_N, UNOWN_X, UNOWN_A, UNOWN_P, H.GIOVANNIS_NIDORAN_M, H.DITTO):
            state = fd(real, bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X)))
            hub = ClientHub(A.HostedGame(state.clone()))
            hub.player(0).handle({**REQ, "type": "candidates"})
            others.append(([observe(state, v) for v in (1, None)], without_handles(hub.player(1).handle({**REQ, "type": "candidates"})["response"]),
                           [hub.take_updates(a) for a in (1, "spectator")]))
        for other in others[1:]:
            self.assertEqual(other, others[0])

    def test_reading_candidates_inputs_and_check_changes_nothing(self):
        state = fd(bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X)))
        hub = ClientHub(A.HostedGame(state.clone()))
        hub.take_updates(1), hub.take_updates("spectator")
        me = hub.player(0)
        before = snap(state)
        r = me.handle({**REQ, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == L.KIND_USE_ATTACK)
        me.handle({**REQ, "type": "inputs", "game": r["game"], "revision": r["revision"], "candidate": c["id"]})
        for choices in (["o1", "o2", "o3"], ["o1", "o3"]):
            me.handle({**REQ, "type": "check", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": choices})
        self.assertEqual(snap(state), before)
        self.assertEqual(rng_fingerprint(state.rng), before[1])
        self.assertEqual([hub.take_updates(a) for a in (0, 1, "spectator")], [[], [], []])

    def test_no_reveal_or_engine_check_while_building(self):
        def boom(*_a, **_k):
            raise AssertionError("候補の作成・入力の検査から呼んではいけない")
        probe = L._probe

        def probe_without_attacks(check, *args):  # ほかの種類の候補の確かめは今までどおり。ワザの確かめだけを禁じる
            if any(isinstance(a, UseAttack) for a in args):
                boom()
            return probe(check, *args)
        state = fd(bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X), mon(UNOWN_X)))
        with mock.patch.object(EN, "_reveal_for_action", boom), mock.patch.object(EN, "reveal_face_down", boom), \
                mock.patch.object(L, "check_use_attack", boom), mock.patch.object(E, "group_attack_power_check", boom), \
                mock.patch.object(E, "group_attack_powers_check", boom), mock.patch.object(L, "_probe", probe_without_attacks), \
                mock.patch.object(E.CoinsUntilTailsBonusToGroupAttack, "usable_for", boom), mock.patch.object(E.CounterBonusToGroupAttack, "usable_for", boom):
            _h, session, r, c, inputs = attack_of(state)
            self.assertEqual(len(powers_of(inputs["stages"])), 3)
            self.assertIsNone(check_code(session, r, c, ["o1", "o2", "o3"]))
            self.assertEqual(check_code(session, r, c, ["o1", "o3", "o4"]), L.CANDIDATE_INPUT_INVALID)


class RegressionTest(unittest.TestCase):
    def test_command_and_coin_paths_are_unchanged(self):
        """［めいれい］（0.190.0）・クチバシティジムのコイン（0.188.0）の提示と note は変えない。アンノーンの力は、アンノーンでない使い手には示さない。"""
        from tests.test_legal_actions_r2_with_power_v0_190 import fd as fd190, king, kings
        state = fd190(bench=(T119.mon(UNOWN_X), king()))
        _h, _s, _r, _c, inputs = attack_of(state)
        self.assertEqual([(o["addon"], o["power"], o["pokemon"]) for o in inputs["stages"][1]["options"]], [(L.ADDON_WITH_POWER, "めいれい", kings(state)[0])])
        self.assertEqual(inputs["stages"][1]["note"], L.NOTE_FACE_DOWN_ADDONS)
        from tests.test_legal_actions_r2_stadium_coin_v0_188 import face_down_board
        coin = face_down_board(H.LT_SURGES_MAGNEMITE)  # マチスのコイル（特殊能力なし）
        _h, _s, _r, _c, inputs = attack_of(coin)
        self.assertEqual([o["addon"] for o in inputs["stages"][1]["options"]], [L.ADDON_STADIUM_COIN])
        self.assertEqual(inputs["stages"][1]["note"], L.NOTE_FACE_DOWN_COIN)

    def test_face_up_declaration_unchanged(self):
        c, stages = attack_stages(face_up(bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X))))
        self.assertNotIn(L.REASON_FACE_DOWN, c["reasons"])
        self.assertEqual([o["power"] for o in powers_of(stages)], [A_POWER, X_POWER])
        self.assertTrue(all(o["processability"] != L.UNVERIFIED for o in stages[1]["options"]))
        c, stages = attack_stages(face_up(UNOWN_X, bench=(mon(H.RATTATA),)))  # おもての分岐は今どおりバトル場の持ち主も示す
        self.assertEqual([o["power"] for o in powers_of(stages)], [X_POWER])

    def test_guarantee_is_the_same_for_every_real_card(self):
        seen = {str(attack_of(fd(real))[3]["guarantees"]) for real in (UNOWN_N, UNOWN_X, UNOWN_A, H.GIOVANNIS_NIDORAN_M, H.DITTO)}
        seen.add(str(attack_of(fd(bench=(mon(H.RATTATA),)))[3]["guarantees"]))
        self.assertEqual(seen, {str(L.GUARANTEE_FACE_DOWN_ATTACK)})


if __name__ == "__main__":
    unittest.main()

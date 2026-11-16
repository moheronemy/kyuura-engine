"""v0.190（R-2 の［めいれい］。docs/r2-with-power-design.md）: 本人のうらのバトル場のポケモンのワザの宣言に、自分の場のおもてのポケモンの［めいれい］を示す。

0.189.0 まで、うらの分岐（``_face_down_attack_candidate``）の 2 段目は、クチバシティジムのコイン（v0.188）だけを示した。0.190.0 では、次のすべてを満たすとき、
2 段目に［めいれい］（``with_power``。持ち主ごとに 1 つ）を示す（どのワザにも同じ。unverified・face_down_reveal_not_evaluated のまま）:

- 番のプレイヤーの main の段階で、本人のバトル場のポケモンがうら（候補を作る呼び出し元の条件）
- 本人が知る本当のカード（``printed_def``）が特殊能力を持たない
- 自分の場のおもてのポケモン（使い手と別）が ``CommandBonusToNamedAttackers`` の力を持つ（``group_attack_power_slot``）
- 本当のカードの印刷の名前が、その力の ``names`` のどれかと完全に同じ
- 持ち主の力が消えていない（``power_suppressed``）・使えない効果を受けていない（``powers_use_prevented``）

値・表示はおもての宣言（``_addon_specs``）と同じ。並びは コイン → 場の並び。check は形と、同じ力（``exclusive_key``）を 2 つ指す組の拒否だけ（エンジンを呼ばない）。
送信のあとの順（おもてにする → 確かめ・先読み・処理）は変えない。

構築盤面（``test_secret_plan_v0_67`` の ``board``・``place``・``to_active`` を再利用。new_game からの到達ではない）。本当のカード・持ち主はどれも登録された実在のカード
（サカキのニドラン♂ PMCG6-004・サカキのニドリーノ PMCG6-013・ニドラン♂ PMCG1-005・サカキのニドキング PR1-068・ベトベトン PMCG3-007・アンノーンX neo4-065・
マチスのコイル PMCG5-037・クチバシティジム）。実在しない組み合わせ・効果は、次の 2 つだけを人工的に作り、名前に ``artificial`` をつけて区別する:

- 「サカキのニドラン♂」の名前で特殊能力を持つ本当のカード（登録にない。印刷の定義の特殊能力だけを差しかえる）
- ［めいれい］とクチバシティジムのコインを同時に示す組（「マチスの」で始まり「サカキの」の名前を対象にする登録はない。``_owner_named`` を差しかえる）

使えない効果（``CannotUsePowers``）は、相手のショックアイを前の番に受けた状態を持ち主に直接入れて作る（到達できる効果の注入。``injected`` と名前につける）。
"""

from __future__ import annotations

import dataclasses
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
from kyuura_engine.commands import AttachEnergy, PlayTrainer, UseAttack
from kyuura_engine.observation import observe
from kyuura_engine.serialize import rng_fingerprint
from kyuura_engine.state import CannotUsePowers, GameState
from tests import helpers as H
from tests import test_damage_reactions_poison_sleep_v0_119 as T119
from tests import test_secret_plan_v0_67 as S
from tests import test_unbounded_coins_heal_allocation_v0_118 as T118
from tests.test_legal_actions_r2_stadium_coin_v0_188 import OLD_NOTE, attack_of, check_code, host_candidates
from tests.test_legal_actions_u7_1 import snap, without_handles
from tests.test_legal_actions_u7_4 import attack_stages, via_direct, via_u7

REQ = {"contract": "kyuura-client-api", "format": 1}
HD, TL = CoinSide.HEADS, CoinSide.TAILS
KING = T119.NIDOKING  # PR1-068 サカキのニドキング（2 進化。［めいれい］: 自分の「サカキのニドラン♂」「サカキのニドリーノ」のワザのダメージ +10）
TARGET = H.GIOVANNIS_NIDORAN_M  # PMCG6-004 サカキのニドラン♂（たね・特殊能力なし。にどげり（無）10×・いかりのいちげき（草）30）
TARGET_NON_BASIC = H.GIOVANNIS_NIDORINO  # PMCG6-013 サカキのニドリーノ（1 進化・特殊能力なし。公開のあとトラッシュ）
NOT_NAMED = H.NIDORAN_M  # PMCG1-005 ニドラン♂（たね・特殊能力なし。名前が対象と違う）
MUK = H.MUK  # PMCG3-007 ベトベトン（かがくへんかガス）
POWERED = H.LT_SURGES_MAGNETON  # 特殊能力の差しかえ元（人工のケースだけ）


def king():
    return T119.mon(KING)


def fd(real=TARGET, *, bench=None, stadium=None, energies=1, extra_hand=(), opponent_hand=(), opponent_bench=(), face_down_holder=False):
    """プレイヤー 0 の番の main。バトル場はうらの ``real``（マチスの秘策）で草エネルギーが ``energies`` 枚。ベンチは ``bench``（既定はおもてのサカキのニドキング 1 匹）。
    2 進化の持ち主を置くため、始まりの番を 7 にする（S.board の turn_number）。``face_down_holder`` なら、サカキのニドキングをうらにしてベンチに出す（2 枚目のマチスの秘策）。"""
    bench = (king(),) if bench is None else bench
    hand = (real, *([H.GRASS] * energies), *extra_hand, *(() if stadium is None else (stadium,)),
            *((H.LT_SURGES_SECRET_PLAN, KING) if face_down_holder else ()))
    state = S.board(hand=hand, bench=bench, opponent_hand=opponent_hand, opponent_bench=opponent_bench, turn_number=7)
    state = S.place(state, real)
    state = S.to_active(state, S.face_down(state)[0])
    state = S.opponent_turn(S.opponent_turn(state))
    for _ in range(energies):
        state = S.apply_command(state, AttachEnergy(0, S.uid_of(state, H.GRASS), state.players[0].active.card))
        if energies > 1:
            state = S.opponent_turn(S.opponent_turn(state))
    if face_down_holder:
        state = S.place(state, KING)
    if stadium is not None:
        state = S.apply_command(state, PlayTrainer(0, S.uid_of(state, stadium)))
        assert state.stadium is not None and state.decision is None
    active = state.players[0].active
    assert state.is_face_down(active) and len(active.energy) == energies and state.current_player == 0 and state.decision is None
    return state


def kings(state, player=0):
    return [p.pokemon_id for p in state.players[player].in_play() if not state.is_face_down(p) and state.cards[p.card].card_id == KING]


def with_power_of(stages):
    return [o for o in stages[1]["options"] if o["addon"] == L.ADDON_WITH_POWER]


def attack_ids(stages):
    return [o["id"] for o in stages[0]["options"]]


class OfferTest(unittest.TestCase):
    """示す条件を満たすとき、2 段目に持ち主ごとに［めいれい］を示す（どのワザにも同じ）。"""

    def assert_offered(self, state, holders):
        _h, session, r, c, inputs = attack_of(state)
        self.assertEqual((c["processability"], c["reasons"], c["input_disclosure"]), (L.UNVERIFIED, [L.REASON_FACE_DOWN], L.DISCLOSURE_CONFIRMED))
        self.assertEqual(c["guarantees"], L.GUARANTEE_FACE_DOWN_ATTACK)
        first, second = inputs["stages"]
        ids = attack_ids(inputs["stages"])
        powers = with_power_of(inputs["stages"])
        self.assertEqual([o["pokemon"] for o in powers], holders)  # 場の並び
        self.assertEqual([o["id"] for o in powers], [f"o{len(ids) + i + 1}" for i in range(len(holders))])
        for o in powers:
            self.assertEqual((o["power"], o["processability"], o["reasons"]), ("めいれい", L.UNVERIFIED, [L.REASON_FACE_DOWN]))
        self.assertEqual(second["count"], {"min": 0, "max": len(second["options"])})
        self.assertEqual(second["options_by_choice"],
                         {aid: [{"option": o["id"], "eligible": True, "processability": L.UNVERIFIED, "reasons": [L.REASON_FACE_DOWN]} for o in second["options"]]
                          for aid in ids})
        self.assertEqual((second["distinct"], second["decline"], second["depends_on_stage"], second["order"], second["order_preserved"]),
                         (True, True, 1, L.ORDER_SIGNIFICANT, True))
        return session, r, c, inputs, ids, powers

    def test_offered_for_every_printed_attack(self):
        state = fd()
        _s, _r, _c, inputs, ids, powers = self.assert_offered(state, kings(state))
        self.assertEqual(len(ids), 2)  # 複数のワザに同じ選択肢
        self.assertEqual(len(inputs["stages"][1]["options"]), 1)

    def test_same_shape_as_the_face_up_declaration(self):
        """段・選べるもの・組の項目の名前と、［めいれい］の選べるものの値（持ち主・力の名前・場所）は、おもてのワザの宣言と同じ。"""
        face_up = T119.board(T119.mon(TARGET, (T119.G,)), bench=(king(),), opponent=T119.mon(H.HITMONCHAN, (T119.F,)))
        _fc, up = attack_stages(face_up)
        state = fd()
        _s, _r, c, inputs, ids, powers = self.assert_offered(state, kings(state))
        down = inputs["stages"]
        self.assertEqual(set(down[1]) - {"note"}, set(up[1]) - {"note"})
        self.assertEqual({k: v for k, v in down[1].items() if k not in ("note", "options", "options_by_choice", "count")},
                         {k: v for k, v in up[1].items() if k not in ("note", "options", "options_by_choice", "count")})
        up_power = with_power_of(up)[0]
        self.assertEqual(set(powers[0]), set(up_power))
        self.assertEqual({k: powers[0][k] for k in ("addon", "power", "zone", "bench_index", "card_id")},
                         {k: up_power[k] for k in ("addon", "power", "zone", "bench_index", "card_id")})
        self.assertEqual(set(up[1]["options_by_choice"][up[0]["options"][0]["id"]][0]), set(down[1]["options_by_choice"][ids[0]][0]))
        self.assertEqual(c["choices_format"], next(x for x in host_candidates(face_up) if x["kind"] == L.KIND_USE_ATTACK)["choices_format"])

    def test_two_holders_in_field_order_and_the_same_power_twice_is_refused(self):
        state = fd(bench=(king(), T119.mon(H.RATTATA), king()))
        session, r, c, inputs, ids, powers = self.assert_offered(state, kings(state))
        self.assertEqual([o["bench_index"] for o in powers], [0, 2])
        k1, k2 = (o["id"] for o in powers)
        for choices, code in (([ids[0], k1], None), ([ids[0], k2], None), ([ids[1], k2], None), ([ids[0]], None),
                              ([ids[0], k1, k2], L.CANDIDATE_INPUT_INVALID), ([ids[0], k2, k1], L.CANDIDATE_INPUT_INVALID),
                              ([ids[0], k1, k1], L.CANDIDATE_INPUT_INVALID)):
            with self.subTest(choices=choices):
                self.assertEqual(check_code(session, r, c, choices), code)
        # おもての宣言（エンジンの確かめ）も、同じ力を 2 つ指す組を同じ区分で拒否する
        face_up = T119.board(T119.mon(TARGET, (T119.G,)), bench=(king(), T119.mon(H.RATTATA), king()), opponent=T119.mon(H.HITMONCHAN, (T119.F,)))
        _h, up_session, up_r, up_c, up_inputs = attack_of(face_up)
        up_k1, up_k2 = (o["id"] for o in with_power_of(up_inputs["stages"]))
        self.assertEqual(check_code(up_session, up_r, up_c, [attack_ids(up_inputs["stages"])[0], up_k1, up_k2]), L.CANDIDATE_INPUT_INVALID)

    def test_non_basic_target_is_offered_the_same_way(self):
        state = fd(TARGET_NON_BASIC, bench=(T119.mon(H.RATTATA), king()))
        _s, _r, _c, inputs, _ids, _powers = self.assert_offered(state, kings(state))
        for word in ("トラッシュ", "たねポケモン"):  # 公開のあとの結果を予告しない
            self.assertNotIn(word, str(inputs))

    def test_check_is_shape_only(self):
        state = fd(energies=0)  # 必要なエネルギーが足りなくても、check は形だけ（エンジンを呼ばない）
        _h, session, r, c, inputs = attack_of(state)
        ids = attack_ids(inputs["stages"])
        k = with_power_of(inputs["stages"])[0]["id"]
        for choices, code in (([ids[0]], None), ([ids[0], k], None), ([ids[1], k], None), ([k], L.CANDIDATE_INPUT_INVALID), ([k, ids[0]], L.CANDIDATE_INPUT_INVALID),
                              ([ids[0], ids[1]], L.CANDIDATE_INPUT_INVALID), ([ids[0], "o9"], L.CANDIDATE_INPUT_INVALID), ([ids[0], 3], L.CANDIDATE_INPUT_INVALID),
                              ([], L.CANDIDATE_INPUT_INVALID), ([ids[0], None], L.CANDIDATE_INPUT_INVALID)):
            with self.subTest(choices=choices):
                self.assertEqual(check_code(session, r, c, choices), code)


class NotOfferedTest(unittest.TestCase):
    """条件を満たさないときは、0.189.0 と同じ 2 段目（空）のまま。"""

    def assert_not_offered(self, state):
        _h, session, r, c, inputs = attack_of(state)
        self.assertEqual((c["processability"], c["reasons"], c["choices_format"]), (L.UNVERIFIED, [L.REASON_FACE_DOWN], "[ワザの番号]"))
        first, second = inputs["stages"]
        ids = [o["id"] for o in first["options"]]
        self.assertEqual((second["count"], second["options"], second["options_by_choice"], second["order"], second["note"]),
                         ({"min": 0, "max": 0}, [], {oid: [] for oid in ids}, L.ORDER_NOT_APPLICABLE, OLD_NOTE))
        self.assertEqual(check_code(session, r, c, [ids[0], f"o{len(ids) + 1}"]), L.CANDIDATE_INPUT_INVALID)
        self.assertIsNone(check_code(session, r, c, [ids[0]]))

    def test_name_mismatch(self):
        self.assert_not_offered(fd(NOT_NAMED))

    def test_artificial_real_card_with_a_power(self):
        """「サカキのニドラン♂」の名前で特殊能力を持つカードは登録にない。印刷の定義の特殊能力だけを差しかえた人工のケース。"""
        state = fd()
        card = state.players[0].active.card
        powers = load_card_pool().get(POWERED).powers
        original = GameState.printed_def

        def printed(self, uid):
            found = original(self, uid)
            return dataclasses.replace(found, powers=powers) if uid == card else found
        with mock.patch.object(GameState, "printed_def", printed):
            self.assertTrue(state.printed_def(card).powers)
            self.assert_not_offered(state)

    def test_holder_face_down(self):
        state = fd(bench=(T119.mon(H.RATTATA),), face_down_holder=True)
        self.assertEqual(kings(state), [])
        self.assertEqual(sum(1 for p in state.players[0].bench if state.is_face_down(p)), 1)
        self.assert_not_offered(state)

    def test_holder_power_suppressed(self):
        self.assert_not_offered(fd(bench=(king(), T119.mon(MUK))))  # 自分のベンチのベトベトンのかがくへんかガス
        self.assert_not_offered(fd(bench=(king(),), opponent_bench=(T119.mon(MUK),)))  # 相手の場のかがくへんかガス

    def test_injected_holder_use_prevented(self):
        state = fd().clone()
        holder = next(p for p in state.players[0].bench if p.pokemon_id == kings(state)[0])
        holder.persistent_effects = (*holder.persistent_effects, CannotUsePowers(source_card=state.players[1].active.card, source_player=1,
                                                                                  created_turn=state.turn_number - 1, active_turn=state.turn_number))
        self.assert_not_offered(state)

    def test_holder_on_the_opponents_field(self):
        self.assert_not_offered(fd(bench=(T119.mon(H.RATTATA),), opponent_bench=(king(),)))

    def test_no_holder(self):
        self.assert_not_offered(fd(bench=(T119.mon(H.RATTATA),)))

    def test_not_the_actors_turn_or_not_main(self):
        state = fd()
        self.assertEqual([c["kind"] for c in host_candidates(state, actor=1)], [])  # 相手（番でない）には候補がない
        pending = fd(extra_hand=(H.LT_SURGES_SECRET_PLAN, H.FIRE))
        pending = S.apply_command(pending, PlayTrainer(0, S.uid_of(pending, H.LT_SURGES_SECRET_PLAN)))
        self.assertIsNotNone(pending.decision)
        self.assertNotIn(L.KIND_USE_ATTACK, [c["kind"] for c in host_candidates(pending)])  # 決定待ち（main の操作を選べない）


class SubmitTest(unittest.TestCase):
    """送信は既存のコマンド（UseAttack(with_power=...)）と同じ結果。処理の順は変えない。"""

    def assert_same(self, state, choices, command, outcome):
        host, result = via_u7(state, lambda s: choices)
        game, direct = via_direct(state, command)
        self.assertEqual(result.outcome, outcome, result)
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual(snap(host.game.state), snap(game.state))
        return host, result

    def test_with_and_without_the_power_same_as_direct(self):
        """にどげり（コイン 2 枚 × 10）。［めいれい］で 6 段階に +10（「おもて」0 枚は 2 段階までで終わるので加えない。既存の処理）。"""
        state = fd()
        k = kings(state)[0]
        for bits, plain, used in (((HD, HD), 20, 30), ((HD, TL), 10, 20), ((TL, TL), 0, 0)):
            with self.subTest(bits=bits):
                rigged = H.with_coin_bits(state, *bits, *[TL] * 6)
                with_power, _ = self.assert_same(rigged, ["o1", "o3"], UseAttack(0, 0, with_power=k), D.ACCEPTED)
                without, _ = self.assert_same(rigged, ["o1"], UseAttack(0, 0), D.ACCEPTED)
                self.assertEqual((with_power.game.state.players[1].active.damage, without.game.state.players[1].active.damage), (used, plain))
                self.assertFalse(with_power.game.state.is_face_down(with_power.game.state.players[0].active))
                if used:
                    self.assertEqual([m[0] for m in T119.last(with_power.game.state, "damage")["modifiers"]], [6])

    def test_second_holder_same_as_direct(self):
        state = fd(bench=(king(), king()))
        k1, k2 = kings(state)
        rigged = H.with_coin_bits(state, HD, HD, *[TL] * 6)
        self.assert_same(rigged, ["o1", "o4"], UseAttack(0, 0, with_power=k2), D.ACCEPTED)
        self.assert_same(rigged, ["o1", "o3"], UseAttack(0, 0, with_power=k1), D.ACCEPTED)

    def test_attack_rejected_by_the_engine_same_as_direct(self):
        """いかりのいちげきは、自分にダメージカウンターがないとワザの条件で拒否される（［めいれい］とは別の理由。おもてでも同じ）。"""
        state = fd()
        self.assert_same(state, ["o2", "o3"], UseAttack(0, 1, with_power=kings(state)[0]), D.REJECTED)
        self.assert_same(state, ["o2"], UseAttack(0, 1), D.REJECTED)

    def test_non_basic_target_is_trashed_same_as_direct(self):
        state = fd(TARGET_NON_BASIC)
        host, result = self.assert_same(state, ["o1", "o2"], UseAttack(0, 0, with_power=kings(state)[0]), D.ACCEPTED)
        self.assertIn(state.players[0].active.card, host.game.state.players[0].discard)
        plain, _ = via_u7(state, lambda s: ["o1"])
        self.assertEqual(snap(plain.game.state), snap(host.game.state))

    def test_rejection_leaves_state_rng_log_and_is_not_announced(self):
        state = fd(energies=0)  # 必要なエネルギーが足りない: おもてにしたあとエンジンが拒否
        hosted = A.HostedGame(state.clone())
        hub = ClientHub(hosted)
        me = hub.player(0)
        r = me.handle({**REQ, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == L.KIND_USE_ATTACK)
        before = snap(hosted.state)
        sent = me.handle({**REQ, "type": "submit", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o1", "o3"]})
        self.assertEqual(sent["outcome"], D.REJECTED)
        self.assertEqual([hub.take_updates(a) for a in (1, "spectator")], [[], []])
        game, direct = via_direct(state, UseAttack(0, 0, with_power=kings(state)[0]))
        self.assertEqual(direct.outcome, D.REJECTED)
        self.assertEqual(snap(game.state), snap(state))  # 状態・乱数・ログ・決定の通し番号は変わらない
        self.assertEqual(snap(hosted.state), before)

    def test_api_submit_same_as_direct(self):
        state = H.with_coin_bits(fd(), HD, HD, *[TL] * 6)
        hosted = A.HostedGame(state.clone())
        me = ClientHub(hosted).player(0)
        r = me.handle({**REQ, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == L.KIND_USE_ATTACK)
        sent = me.handle({**REQ, "type": "submit", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o1", "o3"]})
        game, direct = via_direct(state, UseAttack(0, 0, with_power=kings(state)[0]))
        self.assertEqual((sent["outcome"], direct.outcome), (D.ACCEPTED, D.ACCEPTED))
        self.assertEqual(snap(hosted.state), snap(game.state))


class StadiumCoinTest(unittest.TestCase):
    def test_vermilion_gym_in_play_offers_only_the_command(self):
        """場にクチバシティジムがあっても、サカキのニドラン♂（「マチスの」でない）にはコインを示さない（v0.188 の条件）。［めいれい］だけを示し、番号・送信は同じ。"""
        state = fd(stadium=H.VERMILION_CITY_GYM)
        _h, _s, _r, _c, inputs = attack_of(state)
        self.assertEqual([o["addon"] for o in inputs["stages"][1]["options"]], [L.ADDON_WITH_POWER])
        rigged = H.with_coin_bits(state, HD, HD, *[TL] * 6)
        host, result = via_u7(rigged, lambda s: ["o1", "o3"])
        game, direct = via_direct(rigged, UseAttack(0, 0, with_power=kings(state)[0]))
        self.assertEqual((result.outcome, direct.outcome), (D.ACCEPTED, D.ACCEPTED))
        self.assertEqual(snap(host.game.state), snap(game.state))

    def test_artificial_coin_and_command_together_keep_order_and_values(self):
        """人工: ``_owner_named`` を差しかえ、コインと［めいれい］を同時に示す。並びは コイン → 場の並び（おもての宣言と同じ）、選んだ順の値、check は形だけ。エンジンには送らない。"""
        state = fd(stadium=H.VERMILION_CITY_GYM, bench=(king(), king()))
        k1, k2 = kings(state)
        with mock.patch.object(L, "_owner_named", lambda *_a: True):
            _h, session, r, c, inputs = attack_of(state)
            found = L._face_down_attack_candidate(state, 0, state.players[0].active, dict(L.GUARANTEE_FACE_DOWN_ATTACK))
        second = inputs["stages"][1]
        self.assertEqual([(o["addon"], o.get("pokemon")) for o in second["options"]],
                         [(L.ADDON_STADIUM_COIN, None), (L.ADDON_WITH_POWER, k1), (L.ADDON_WITH_POWER, k2)])
        self.assertEqual([o["id"] for o in second["options"]], ["o3", "o4", "o5"])
        self.assertEqual(second["count"], {"min": 0, "max": 3})
        for choices, code in ((["o1", "o4", "o3"], None), (["o1", "o3", "o5"], None), (["o1", "o4", "o5"], L.CANDIDATE_INPUT_INVALID),
                              (["o1", "o3", "o4", "o5"], L.CANDIDATE_INPUT_INVALID)):
            with self.subTest(choices=choices):
                self.assertEqual(check_code(session, r, c, choices), code)
        _code, values = L._attack_input_problem(found, ("o1", "o4", "o3"))
        self.assertEqual(L._attack_command(0, values), UseAttack(0, 0, stadium_coin=True, with_power=k1))
        _code, values = L._attack_input_problem(found, ("o1",))
        self.assertEqual(L._attack_command(0, values), UseAttack(0, 0))


class BoundaryTest(unittest.TestCase):
    """情報境界: 候補・入力・check は本人の知識と公開の状態だけで決まり、ほかの人への応答・通知を変えない。"""

    def own_view(self, state):
        _h, session, r, c, inputs = attack_of(state)
        checks = [check_code(session, r, c, ch) for ch in (["o1"], ["o1", "o3"], ["o2", "o3"], ["o3"])]
        return without_handles(r), inputs, checks

    def test_opponent_secrets_do_not_change_the_actors_inputs(self):
        twins = [self.own_view(fd(opponent_hand=hand)) for hand in ((H.FIRE, H.FIRE), (H.RATTATA, H.POTION))]
        self.assertEqual(twins[0], twins[1])
        views = [self.own_view(fd(opponent_hand=hand)) for hand in ((H.FIRE,), (H.RATTATA, H.POTION), ())]
        self.assertEqual([v[1] for v in views], [views[0][1]] * 3)
        self.assertEqual([v[2] for v in views], [views[0][2]] * 3)

    def test_the_actors_real_card_does_not_reach_others(self):
        others = []
        for real in (TARGET, TARGET_NON_BASIC, NOT_NAMED):
            state = fd(real)
            hub = ClientHub(A.HostedGame(state.clone()))
            hub.player(0).handle({**REQ, "type": "candidates"})
            others.append(([observe(state, v) for v in (1, None)], without_handles(hub.player(1).handle({**REQ, "type": "candidates"})["response"]),
                           [hub.take_updates(a) for a in (1, "spectator")]))
        for other in others[1:]:
            self.assertEqual(other, others[0])

    def test_reading_candidates_inputs_and_check_changes_nothing(self):
        state = fd()
        hub = ClientHub(A.HostedGame(state.clone()))
        hub.take_updates(1), hub.take_updates("spectator")
        me = hub.player(0)
        before = snap(state)
        r = me.handle({**REQ, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == L.KIND_USE_ATTACK)
        me.handle({**REQ, "type": "inputs", "game": r["game"], "revision": r["revision"], "candidate": c["id"]})
        me.handle({**REQ, "type": "check", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o1", "o3"]})
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
        state = fd(bench=(king(), king()))
        with mock.patch.object(EN, "_reveal_for_action", boom), mock.patch.object(EN, "reveal_face_down", boom), \
                mock.patch.object(L, "check_use_attack", boom), mock.patch.object(E, "group_attack_power_check", boom), \
                mock.patch.object(E, "group_attack_powers_check", boom), mock.patch.object(L, "_probe", probe_without_attacks):
            _h, session, r, c, inputs = attack_of(state)
            self.assertEqual(len(with_power_of(inputs["stages"])), 2)
            self.assertIsNone(check_code(session, r, c, ["o1", "o3"]))
            self.assertEqual(check_code(session, r, c, ["o1", "o3", "o4"]), L.CANDIDATE_INPUT_INVALID)


class RegressionTest(unittest.TestCase):
    def test_group_powers_stay_unoffered(self):
        """アンノーンの力（［XXXXX］など）は、うらの使い手には示さない（R-2 の残り。別の単位）。"""
        state = fd(bench=(T118.mon(T118.UNOWN_X),))
        _h, _s, _r, _c, inputs = attack_of(state)
        self.assertEqual(inputs["stages"][1]["options"], [])
        state = fd(bench=(T118.mon(T118.UNOWN_X), king()))
        _h, _s, _r, _c, inputs = attack_of(state)
        self.assertEqual([(o["addon"], o["power"]) for o in inputs["stages"][1]["options"]], [(L.ADDON_WITH_POWER, "めいれい")])

    def test_face_up_declaration_unchanged(self):
        face_up = T119.board(T119.mon(TARGET, (T119.G,)), bench=(king(),), opponent=T119.mon(H.HITMONCHAN, (T119.F,)))
        c, stages = attack_stages(face_up)
        self.assertNotIn(L.REASON_FACE_DOWN, c["reasons"])
        self.assertEqual([o["addon"] for o in stages[1]["options"]], [L.ADDON_WITH_POWER])
        self.assertTrue(all(o["processability"] != L.UNVERIFIED for o in stages[1]["options"]))

    def test_guarantee_is_the_same_for_every_real_card(self):
        seen = {str(attack_of(fd(real))[3]["guarantees"]) for real in (TARGET, TARGET_NON_BASIC, NOT_NAMED)}
        seen.add(str(attack_of(fd(bench=(T119.mon(H.RATTATA),)))[3]["guarantees"]))
        self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main()

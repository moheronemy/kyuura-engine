"""v0.188（R-2 の初回対応。docs/legal-actions-r2-face-down-declaration-design.md 10 章）: 本人のうらのバトル場のポケモンのワザの宣言に、クチバシティジムのコインを示す。

0.187.0 まで、うらの分岐（``_face_down_attack_candidate``）は宣言といっしょに選ぶものを示さなかった（2 段目が空。R-2）。0.188.0 では、次のすべてを満たすときだけ、
2 段目にクチバシティジムのコイン（``stadium_coin``）を 1 つ示す（どのワザにも同じ。unverified・face_down_reveal_not_evaluated のまま）:

- 番のプレイヤーの main の段階で、本人のバトル場のポケモンがうら（候補を作る呼び出し元の条件）
- 場のスタジアムが ``AttackCoinStadium``（``stadium_of``）
- 本人が知る本当のカード（``printed_def``）の名前が「(owner)の」で始まる（``_owner_named``）
- 本当のカードが特殊能力を持たない（公開のあとに今の姿を変えうるカードを除く）

たねでない本当のカードにも同じ条件で示す（公開のあとのトラッシュを予告しない）。候補の作成・入力の検査は、おもてにする処理・エンジンの確かめ・乱数を使わない。送信の
あとの順（おもてにする → たねでなければトラッシュして受理 → 確かめ・先読み・処理）は変えない。

構築盤面（``test_secret_plan_v0_67`` の ``board``・``place``・``to_active`` を再利用。new_game からの到達ではない）。本当のカードはどれも登録された実在のカード
（マチスのコイル PMCG5-037・マチスのラッタ PMCG5-059・マチスのレアコイル PMCG5-040（特殊能力［エナジーチャージ］）・コラッタ）。人工的な組み合わせは使わない
（「マチスの」で始まり特殊能力を持つ「たねポケモン」は登録にない。特殊能力の除外は実在の 1 進化のカードで確かめる）。
"""

from __future__ import annotations

import unittest
from unittest import mock

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import effects as E
from kyuura_engine import engine as EN
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import AttachEnergy, PlayTrainer, UseAttack
from kyuura_engine.observation import observe
from kyuura_engine.serialize import rng_fingerprint
from tests import helpers as H
from tests import test_secret_plan_v0_67 as S
from tests import test_stadiums_v0_57 as T57
from tests import test_unbounded_coins_heal_allocation_v0_118 as T118
from tests.test_legal_actions_u7_1 import snap, without_handles
from tests.test_legal_actions_u7_4 import attack_stages, via_direct, via_u7

REQ = {"contract": "kyuura-client-api", "format": 1}
HD, TL = CoinSide.HEADS, CoinSide.TAILS
TARGET_BASIC = H.LT_SURGES_MAGNEMITE  # PMCG5-037 マチスのコイル（たね・特殊能力なし。でんきショック（雷）・たいあたり（無無））
TARGET_NON_BASIC = H.LT_SURGES_RATICATE  # PMCG5-059 マチスのラッタ（1 進化・特殊能力なし）
POWERED = H.LT_SURGES_MAGNETON  # PMCG5-040 マチスのレアコイル（1 進化・特殊能力［エナジーチャージ］）
NOT_OWNER = H.RATTATA  # コラッタ（たね・「マチスの」でない）
ACCEPTED_WITH_COIN = H.LT_SURGES_ELECTABUZZ  # PMCG5-041 マチスのエレブー（たね・特殊能力なし。1 つ目のワザはコインつきでもエンジンが受理する）
OLD_NOTE = "うらのカードのワザといっしょに選ぶものは示さない（おもてにする前に確かめられない）"


def face_down_board(real, *, stadium=H.VERMILION_CITY_GYM, energies=2, energy=H.LIGHTNING, bench=(), extra_hand=(), opponent_hand=()):
    """プレイヤー 0 の番の main。バトル場はうらの ``real``（マチスの秘策）で ``energy`` が ``energies`` 枚、場のスタジアムは ``stadium``（None なら出さない）。"""
    hand = (real, *([energy] * energies), *extra_hand, *(() if stadium is None else (stadium,)))
    state = S.board(hand=hand, bench=bench, opponent_hand=opponent_hand)
    state = S.place(state, real)
    state = S.to_active(state, S.face_down(state)[0])
    for _ in range(energies):
        state = S.opponent_turn(S.opponent_turn(state))
        state = S.apply_command(state, AttachEnergy(0, S.uid_of(state, energy), state.players[0].active.card))
    if energies == 0:
        state = S.opponent_turn(S.opponent_turn(state))
    if stadium is not None:
        state = S.apply_command(state, PlayTrainer(0, S.uid_of(state, stadium)))
        assert state.stadium is not None and state.decision is None
    active = state.players[0].active
    assert state.is_face_down(active) and len(active.energy) == energies and state.current_player == 0 and state.decision is None
    return state


def attack_of(state, actor=0):
    host = L.ActionHost(A.HostedGame(state.clone()))
    session = host.session(actor)
    r = session.candidates()
    c = next((c for c in r["candidates"] if c["kind"] == L.KIND_USE_ATTACK), None)
    inputs = None if c is None else session.inputs(r["game"], r["revision"], c["id"])
    return host, session, r, c, inputs


def check_code(session, r, c, choices):
    answer = session.check(r["game"], r["revision"], c["id"], choices)
    return None if answer["valid"] else answer["refusal"]["code"]


def coin_of(stages):
    return [o for o in stages[1]["options"] if o["addon"] == L.ADDON_STADIUM_COIN]


class OfferTest(unittest.TestCase):
    """示す条件を満たす本当のカード（たね・たねでない）では、2 段目にコインを 1 つ示す。"""

    def assert_offered(self, real):
        state = face_down_board(real)
        _h, session, r, c, inputs = attack_of(state)
        self.assertEqual((c["processability"], c["reasons"], c["input_disclosure"]), (L.UNVERIFIED, [L.REASON_FACE_DOWN], L.DISCLOSURE_CONFIRMED))
        self.assertEqual(c["guarantees"], L.GUARANTEE_FACE_DOWN_ATTACK)
        first, second = inputs["stages"]
        attack_ids = [o["id"] for o in first["options"]]
        self.assertTrue(all(o["processability"] == L.UNVERIFIED and o["reasons"] == [L.REASON_FACE_DOWN] for o in first["options"]))
        coins = coin_of(inputs["stages"])
        self.assertEqual(len(second["options"]), 1)
        self.assertEqual(len(coins), 1)
        coin = coins[0]
        self.assertEqual(coin["id"], f"o{len(attack_ids) + 1}")
        self.assertEqual((coin["card"], coin["card_id"], coin["processability"], coin["reasons"]),
                         (state.stadium.card, H.VERMILION_CITY_GYM, L.UNVERIFIED, [L.REASON_FACE_DOWN]))
        self.assertEqual(second["count"], {"min": 0, "max": 1})
        self.assertEqual(second["options_by_choice"],
                         {aid: [{"option": coin["id"], "eligible": True, "processability": L.UNVERIFIED, "reasons": [L.REASON_FACE_DOWN]}] for aid in attack_ids})
        self.assertEqual((second["distinct"], second["decline"], second["depends_on_stage"], second["order"], second["order_preserved"]),
                         (True, True, 1, L.ORDER_SIGNIFICANT, True))
        return state, session, r, c, inputs, attack_ids, coin

    def test_basic_target_offers_the_coin_for_every_printed_attack(self):
        _s, _session, _r, _c, _i, attack_ids, _coin = self.assert_offered(TARGET_BASIC)
        self.assertEqual(len(attack_ids), 2)  # 複数のワザに同じ選択肢

    def test_non_basic_target_is_offered_the_same_way(self):
        _s, _session, _r, _c, inputs, attack_ids, _coin = self.assert_offered(TARGET_NON_BASIC)
        self.assertEqual(len(attack_ids), 2)
        for word in ("トラッシュ", "たねポケモン"):  # 公開のあとの結果を予告しない
            self.assertNotIn(word, str(inputs))

    def test_same_shape_as_the_face_up_declaration(self):
        """段・選べるもの・組の項目の名前は、おもてのワザの宣言（クチバシティジムのコイン）と同じ。"""
        face_up = T57.placed(H.VERMILION_CITY_GYM, active={"card": H.LT_SURGES_VOLTORB, "energy": [H.LIGHTNING, H.LIGHTNING]})
        _fc, up = attack_stages(face_up)
        _s, _session, _r, c, inputs, attack_ids, coin = self.assert_offered(TARGET_BASIC)
        down = inputs["stages"]
        self.assertEqual(set(down[1]) - {"note"}, set(up[1]) - {"note"})
        self.assertEqual({k: v for k, v in down[1].items() if k not in ("note", "options", "options_by_choice", "count")},
                         {k: v for k, v in up[1].items() if k not in ("note", "options", "options_by_choice", "count")})
        up_coin = coin_of(up)[0]
        self.assertEqual(set(coin), set(up_coin))
        self.assertEqual((coin["addon"], coin["card_id"]), (up_coin["addon"], up_coin["card_id"]))
        self.assertEqual(set(up[1]["options_by_choice"][up[0]["options"][0]["id"]][0]), set(down[1]["options_by_choice"][attack_ids[0]][0]))
        self.assertEqual(c["choices_format"], next(x for x in host_candidates(face_up) if x["kind"] == L.KIND_USE_ATTACK)["choices_format"])

    def test_check_is_shape_only(self):
        state = face_down_board(TARGET_BASIC, energies=0)  # 必要なエネルギーが足りなくても、check は形だけ（エンジンを呼ばない）
        _h, session, r, c, _inputs = attack_of(state)
        for choices, code in ((["o1"], None), (["o2"], None), (["o1", "o3"], None), (["o2", "o3"], None),
                              ([], L.CANDIDATE_INPUT_INVALID), (["o3"], L.CANDIDATE_INPUT_INVALID), (["o3", "o1"], L.CANDIDATE_INPUT_INVALID),
                              (["o1", "o3", "o3"], L.CANDIDATE_INPUT_INVALID), (["o1", "o2"], L.CANDIDATE_INPUT_INVALID),
                              (["o1", "o3", "o2"], L.CANDIDATE_INPUT_INVALID), (["o1", "o4"], L.CANDIDATE_INPUT_INVALID),
                              (["o1", 3], L.CANDIDATE_INPUT_INVALID), ([1], L.CANDIDATE_INPUT_INVALID), (["o1", None], L.CANDIDATE_INPUT_INVALID)):
            with self.subTest(choices=choices):
                self.assertEqual(check_code(session, r, c, choices), code)


def host_candidates(state, actor=0):
    return L.ActionHost(A.HostedGame(state.clone())).session(actor).candidates()["candidates"]


class NotOfferedTest(unittest.TestCase):
    """条件を満たさないときは、0.187.0 と同じ 2 段目（空）のまま。"""

    def assert_not_offered(self, state):
        _h, session, r, c, inputs = attack_of(state)
        self.assertEqual((c["processability"], c["reasons"], c["choices_format"]), (L.UNVERIFIED, [L.REASON_FACE_DOWN], "[ワザの番号]"))
        first, second = inputs["stages"]
        ids = [o["id"] for o in first["options"]]
        self.assertEqual((second["count"], second["options"], second["options_by_choice"], second["order"], second["note"]),
                         ({"min": 0, "max": 0}, [], {oid: [] for oid in ids}, L.ORDER_NOT_APPLICABLE, OLD_NOTE))
        self.assertNotIn("order_preserved", second)
        self.assertEqual(check_code(session, r, c, [ids[0], f"o{len(ids) + 1}"]), L.CANDIDATE_INPUT_INVALID)
        self.assertIsNone(check_code(session, r, c, [ids[0]]))

    def test_no_stadium(self):
        self.assert_not_offered(face_down_board(TARGET_BASIC, stadium=None))

    def test_another_stadium(self):
        self.assert_not_offered(face_down_board(TARGET_BASIC, stadium=H.PEWTER_CITY_GYM))

    def test_not_an_owner_pokemon(self):
        self.assert_not_offered(face_down_board(NOT_OWNER))

    def test_real_card_with_a_power(self):
        state = face_down_board(POWERED)
        self.assertTrue(state.printed_def(state.players[0].active.card).powers)
        self.assertTrue(state.printed_def(state.players[0].active.card).name_ja.startswith("マチスの"))
        self.assert_not_offered(state)

    def test_not_the_actors_turn_or_not_main(self):
        state = face_down_board(TARGET_BASIC)
        self.assertEqual([c["kind"] for c in host_candidates(state, actor=1)], [])  # 相手（番でない）には候補がない
        pending = face_down_board(TARGET_BASIC, extra_hand=(H.LT_SURGES_SECRET_PLAN, H.FIRE))
        pending = S.apply_command(pending, PlayTrainer(0, S.uid_of(pending, H.LT_SURGES_SECRET_PLAN)))
        self.assertIsNotNone(pending.decision)
        self.assertNotIn(L.KIND_USE_ATTACK, [c["kind"] for c in host_candidates(pending)])  # 決定待ち（main の操作を選べない）


class SubmitTest(unittest.TestCase):
    """送信は既存のコマンド（UseAttack(stadium_coin=True)）と同じ結果。処理の順は変えない。"""

    def assert_same(self, state, choices, command, outcome):
        host, result = via_u7(state, lambda s: choices)
        game, direct = via_direct(state, command)
        self.assertEqual(result.outcome, outcome, result)
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual(snap(host.game.state), snap(game.state))
        return host, result

    def test_basic_target_accepted_same_as_direct_for_each_coin_side(self):
        """エンジンがコインつきで受理するワザ（マチスのエレブーの 1 つ目のワザ。probe_engine_coin の結果）: U7 と直接のコマンドで結果・状態が同じ。コインを投げる。"""
        state = face_down_board(ACCEPTED_WITH_COIN)
        for side in (HD, TL):
            with self.subTest(side=side):
                rigged = H.with_coin_bits(state, *[side] * 8)
                with_coin, _ = self.assert_same(rigged, ["o1", "o3"], UseAttack(0, 0, stadium_coin=True), D.ACCEPTED)
                without, _ = self.assert_same(rigged, ["o1"], UseAttack(0, 0), D.ACCEPTED)
                self.assertNotEqual(rng_fingerprint(with_coin.game.state.rng), rng_fingerprint(without.game.state.rng))  # コインを投げた

    def test_basic_target_rejected_by_the_engine_same_as_direct(self):
        """マチスのコイルのたいあたり（コインつき）。0.188.0 では、既存の先読みが、ほかのコインの結果をコマンドの入口の状態（おもてにする前）の複製で試し、うらのカードの項目を読んで
        UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY で拒否した（U7 でも同じ拒否・状態不変）。v0.189 でその不整合を直した（docs/r2-coin-preflight-design.md。
        tests/test_preflight_face_down_attacker_v0_189.py）ので、U7 と直接のコマンドで同じく受理する（テストの名前は 0.188.0 のまま）。コインを選ばなくても受理される。"""
        state = face_down_board(TARGET_BASIC)
        for side in (HD, TL):
            with self.subTest(side=side):
                rigged = H.with_coin_bits(state, *[side] * 8)
                self.assert_same(rigged, ["o2", "o3"], UseAttack(0, 1, stadium_coin=True), D.ACCEPTED)  # v0.189: 0.188.0 は REJECTED（FD1）
                self.assert_same(rigged, ["o2"], UseAttack(0, 1), D.ACCEPTED)

    def test_non_basic_target_is_trashed_without_a_coin(self):
        state = face_down_board(TARGET_NON_BASIC)
        before_rng = rng_fingerprint(state.rng)
        host, result = via_u7(state, lambda s: ["o1", "o3"])
        game, direct = via_direct(state, UseAttack(0, 0, stadium_coin=True))
        self.assertEqual(result.outcome, D.ACCEPTED, result)
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual(snap(host.game.state), snap(game.state))
        after = host.game.state
        self.assertEqual(rng_fingerprint(after.rng), before_rng)  # コインを投げていない
        self.assertIn(state.players[0].active.card, after.players[0].discard)
        plain, _ = via_u7(state, lambda s: ["o1"])
        self.assertEqual(snap(plain.game.state)[1:3], snap(after)[1:3])  # コインを選ばない送信と乱数・ログの数が同じ

    def test_rejection_leaves_state_rng_log_and_is_not_announced(self):
        state = face_down_board(TARGET_BASIC, energies=0)  # たね・必要なエネルギーが足りない: おもてにしたあとエンジンが拒否
        hosted = A.HostedGame(state.clone())
        hub = ClientHub(hosted)
        me = hub.player(0)
        r = me.handle({**REQ, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == L.KIND_USE_ATTACK)
        before = snap(hosted.state)
        sent = me.handle({**REQ, "type": "submit", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o1", "o3"]})
        self.assertEqual(sent["outcome"], D.REJECTED)
        self.assertEqual([hub.take_updates(a) for a in (1, "spectator")], [[], []])
        game, direct = via_direct(state, UseAttack(0, 0, stadium_coin=True))
        self.assertEqual(direct.outcome, D.REJECTED)
        self.assertEqual(snap(game.state), snap(state))  # 状態・乱数・ログ・決定の通し番号は変わらない
        self.assertEqual(snap(hosted.state), before)


class BoundaryTest(unittest.TestCase):
    """情報境界: 候補・入力・check は本人の知識と公開の状態だけで決まり、ほかの人への応答・通知を変えない。"""

    def own_view(self, state):
        _h, session, r, c, inputs = attack_of(state)
        checks = [check_code(session, r, c, ch) for ch in (["o1"], ["o1", "o3"], ["o2", "o3"], ["o3"])]
        return without_handles(r), inputs, checks

    def test_opponent_secrets_do_not_change_the_actors_inputs(self):
        views = [self.own_view(face_down_board(TARGET_BASIC, opponent_hand=hand)) for hand in ((H.FIRE,), (H.RATTATA, H.POTION), ())]
        hands = [len(face_down_board(TARGET_BASIC, opponent_hand=hand).players[1].hand) for hand in ((H.FIRE,), (H.RATTATA, H.POTION), ())]
        # 相手の手札の枚数は公開（応答に出うる）。枚数が同じ双子で、中身だけを変えた比較もする
        twins = [self.own_view(face_down_board(TARGET_BASIC, opponent_hand=hand)) for hand in ((H.FIRE, H.FIRE), (H.RATTATA, H.POTION))]
        self.assertEqual(twins[0], twins[1])
        self.assertEqual([v[1] for v in views], [views[0][1]] * 3)
        self.assertEqual([v[2] for v in views], [views[0][2]] * 3)
        self.assertEqual(len(set(hands)), 3)

    def test_the_actors_real_card_does_not_reach_others(self):
        reals = (TARGET_BASIC, TARGET_NON_BASIC, POWERED, NOT_OWNER)
        others = []
        for real in reals:
            state = face_down_board(real)
            hub = ClientHub(A.HostedGame(state.clone()))
            hub.player(0).handle({**REQ, "type": "candidates"})
            others.append(([observe(state, v) for v in (1, None)], without_handles(hub.player(1).handle({**REQ, "type": "candidates"})["response"]),
                           [hub.take_updates(a) for a in (1, "spectator")]))
        for other in others[1:]:
            self.assertEqual(other, others[0])

    def test_reading_candidates_inputs_and_check_changes_nothing(self):
        state = face_down_board(TARGET_BASIC)
        hub = ClientHub(A.HostedGame(state.clone()))
        hub.take_updates(1), hub.take_updates("spectator")
        me = hub.player(0)
        before = snap(state)
        r = me.handle({**REQ, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == L.KIND_USE_ATTACK)
        me.handle({**REQ, "type": "inputs", "game": r["game"], "revision": r["revision"], "candidate": c["id"]})
        me.handle({**REQ, "type": "check", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o1", "o3"]})
        self.assertEqual(snap(state), before)
        self.assertEqual([hub.take_updates(a) for a in (0, 1, "spectator")], [[], [], []])

    def test_no_reveal_or_engine_check_while_building(self):
        def boom(*_a, **_k):
            raise AssertionError("候補の作成・入力の検査から呼んではいけない")
        probe = L._probe

        def probe_without_attacks(check, *args):  # ほかの種類の候補（たねを出す・エネルギーをつけるなど）の確かめは今までどおり。ワザの確かめだけを禁じる
            if any(isinstance(a, UseAttack) for a in args):
                boom()
            return probe(check, *args)
        state = face_down_board(TARGET_BASIC)
        with mock.patch.object(EN, "_reveal_for_action", boom), mock.patch.object(EN, "reveal_face_down", boom), \
                mock.patch.object(L, "check_use_attack", boom), mock.patch.object(E, "stadium_attack_coin_available", boom), \
                mock.patch.object(L, "_probe", probe_without_attacks):
            _h, session, r, c, inputs = attack_of(state)
            self.assertEqual(len(coin_of(inputs["stages"])), 1)
            self.assertIsNone(check_code(session, r, c, ["o1", "o3"]))


class RegressionTest(unittest.TestCase):
    def test_other_declaration_options_stay_unoffered(self):
        """場のおもてのポケモンの特殊能力（with_power）は、うらの使い手には示さない（R-2 の残り）。"""
        bench = (T118.mon(T118.UNOWN_X),)
        state = face_down_board(TARGET_BASIC, bench=bench)
        _h, _s, _r, _c, inputs = attack_of(state)
        self.assertEqual([o["addon"] for o in inputs["stages"][1]["options"]], [L.ADDON_STADIUM_COIN])
        state = face_down_board(NOT_OWNER, bench=bench)
        _h, _s, _r, _c, inputs = attack_of(state)
        self.assertEqual(inputs["stages"][1]["options"], [])

    def test_guarantee_is_the_same_for_every_real_card(self):
        seen = {str(attack_of(face_down_board(real))[3]["guarantees"]) for real in (TARGET_BASIC, TARGET_NON_BASIC, POWERED, NOT_OWNER)}
        seen.add(str(attack_of(face_down_board(TARGET_BASIC, stadium=None))[3]["guarantees"]))
        self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main()

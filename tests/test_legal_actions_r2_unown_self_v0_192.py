"""v0.192（R-2 のアンノーンの自己持ち主。docs/r2-unown-self-holder-design.md 5 章）: 本人のうらのバトル場のアンノーンX・A のワザの宣言に、使い手自身の
［XXXXX］（``CoinsUntilTailsBonusToGroupAttack``）・［ANGER］（``CounterBonusToGroupAttack``）を示す。

0.191.0 まで、うらの分岐は自分の場の別のおもての持ち主の力だけを示した（使い手自身はうらなので場の力を持たない）。0.192.0 では、次のすべてを満たすとき、2 段目の先頭に
使い手自身の力（``with_power``。値は使い手の場の番号）を、その力の対象のワザにだけ示す（unverified・face_down_reveal_not_evaluated）:

- 番のプレイヤーの main の段階で、本人のバトル場のポケモンがうら（候補を作る呼び出し元の条件）
- 本当のカード（``printed_def``）がたねポケモン（ベイビィでない）で、特殊能力の型がすべて分類済みの 22 型（v0.191 と同じ閉じた範囲）
- 本当のカードの印刷の特殊能力のうち、最初のワザといっしょに使う力（登録の ``AttackDeclaredPower``）が［XXXXX］・［ANGER］で、その ``group`` が本当のカードの名前のグループ、
  印刷のワザにその ``attack_name`` のワザがある
- 使い手が力を止める・使えない持続する効果を受けていない（うらの間は受けない不変条件。念のため確かめる）、その力が場の効果で消えていない（``power_suppressed`` を持ち主の
  プレイヤーで）、この番のほかの個体の使用の記録がない（``other_use_problem``）

公開・エンジンの確かめ・状態の複製の上の試行・乱数は使わない。［ANGER］の追加が 0 になる（うらの間はダメージカウンターがのらない）ことでは除かず、note でも量を予告しない。
check は形と、同じ力（``exclusive_key``）を 2 つ指す組の拒否だけ（自己持ち主の力は本当のカードの登録から読む）。送信のあとの順（おもてにする → 確かめ・先読み・処理）と、
XP1・NT1・v0.4b の既存の停止は変えない。

構築盤面（``test_secret_plan_v0_67`` の ``board``・``place``・``to_active``。new_game からの到達ではない）。本当のカード・持ち主・抑止の発生源はどれも登録された実在のカード。
人工の登録・状態は名前に ``artificial`` をつけて区別する（印刷の段階の差しかえ・分類の範囲や示す力の型の差しかえ・うらの使い手への持続する効果（不変条件を崩す））。
期限のある効果（まきちらせ!ベトベトガス・ふしぎなガス・やみのはどう）・この番のほかの X の使用の記録・相手のダメージを受けない状態は、到達できる状態を直接入れて作る（``injected``）。
"""

from __future__ import annotations

import dataclasses
import json
import unittest
from unittest import mock

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import effects as E
from kyuura_engine import engine as EN
from kyuura_engine import legal_actions as L
from kyuura_engine.cards import BABY_STAGE, load_card_pool
from kyuura_engine.client_api import ClientHub
from kyuura_engine.commands import UseAttack
from kyuura_engine.observation import observe
from kyuura_engine.serialize import rng_fingerprint
from kyuura_engine.state import (ATTACK_FIELD_POWER_SUPPRESSION, OPPONENT_POWER_SUPPRESSION, POWER_SUPPRESSION, CannotUsePowers, GameState, PreventDamage,
                                 TrainerTurnEffect)
from tests import helpers as H
from tests import test_damage_reactions_poison_sleep_v0_119 as T119
from tests.test_legal_actions_r2_stadium_coin_v0_188 import OLD_NOTE, attack_of, check_code, host_candidates
from tests.test_legal_actions_r2_unown_v0_191 import (A_POWER, COINS, HD, PICHU, REQ, UNOWN_A, UNOWN_N, UNOWN_X, X_POWER, attack_ids, fd, holders, mon,
                                                      powers_of, registry_unown, with_injected_use_record)
from tests.test_legal_actions_u7_1 import snap, without_handles
from tests.test_legal_actions_u7_4 import via_direct, via_u7

RATTATA_ONLY = (mon(H.RATTATA),)


def me(state):
    return state.players[0].active.pokemon_id


def injected(state, kind, player, created_delta, expires_delta):
    """期限のある効果（TrainerTurnEffect）を直接入れる（injected）。発生源はそのプレイヤーのバトル場のカード（記録の項目だけ）。"""
    state = state.clone()
    src = state.players[player].active.card
    state.trainer_effects = (*state.trainer_effects, TrainerTurnEffect(kind=kind, player=player, source_card=src, card_id=state.cards[src].card_id,
                                                                       created_turn=state.turn_number + created_delta,
                                                                       expires_turn=state.turn_number + expires_delta))
    return state


def printed_replaced(state, **changes):
    """人工: 使い手の本当のカードの印刷の定義だけを差しかえる（登録にない）。"""
    card = state.players[0].active.card
    original = GameState.printed_def

    def printed(self, uid):
        found = original(self, uid)
        return dataclasses.replace(found, **changes) if uid == card else found
    return mock.patch.object(GameState, "printed_def", printed)


class OfferTest(unittest.TestCase):
    """自己持ち主の力を、2 段目の先頭に示す（そのあとに v0.191 の別の持ち主を場の並びで）。"""

    def assert_offered(self, state, expected, note=None):
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
                         (True, True, 1, L.ORDER_SIGNIFICANT, True, note or L.NOTE_FACE_DOWN_SELF_GROUP_POWERS))
        return session, r, c, inputs, ids, powers

    def test_self_xxxxx_offered(self):
        state = fd(UNOWN_X, bench=RATTATA_ONLY)
        _s, _r, _c, inputs, ids, powers = self.assert_offered(state, [(me(state), X_POWER)])
        self.assertEqual(len(ids), 1)
        self.assertEqual(inputs["stages"][0]["options"][0]["name_ja"], "めざめるパワー")
        (own,) = powers
        # 値・表示は v0.191 の with_power と同じ形（使い手の場の番号・バトル場・face_down。カード id は出さない）
        self.assertEqual({k: v for k, v in own.items() if k not in ("id", "eligible", "processability", "reasons")},
                         {"addon": L.ADDON_WITH_POWER, "pokemon": me(state), "card": state.players[0].active.card, "zone": "active", "face_down": True,
                          "power": X_POWER})

    def test_self_anger_offered_with_zero_counters(self):
        """［ANGER］の追加は 0（うらの間はダメージカウンターがのらない）だが、それを理由に除かない（量は予告しない）。"""
        state = fd(UNOWN_A, bench=RATTATA_ONLY)
        self.assertEqual(state.players[0].active.damage, 0)
        _s, _r, _c, _i, _ids, powers = self.assert_offered(state, [(me(state), A_POWER)])
        self.assertNotIn("0", L.NOTE_FACE_DOWN_SELF_GROUP_POWERS.replace("0 個でもよい", ""))
        self.assertEqual(powers[0]["zone"], "active")

    def test_self_first_then_other_holders_in_field_order(self):
        for real, own in ((UNOWN_X, X_POWER), (UNOWN_A, A_POWER)):
            with self.subTest(real=real):
                state = fd(real, bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X)))
                _s, _r, _c, _i, _ids, powers = self.assert_offered(
                    state, [(me(state), own), (holders(state, UNOWN_A)[0], A_POWER), (holders(state, UNOWN_X)[0], X_POWER)])
                self.assertEqual([o["zone"] for o in powers], ["active", "bench", "bench"])
                self.assertEqual([o.get("bench_index") for o in powers], [None, 0, 1])

    def test_check_combinations(self):
        """自己 X ＋ 別の X、自己 A ＋ 別の A、同じ参照の重複、組にない選択は CANDIDATE_INPUT_INVALID。違う力の組は valid（エンジンは呼ばない）。"""
        for real in (UNOWN_X, UNOWN_A):
            with self.subTest(real=real):
                state = fd(real, bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X)))
                _h, session, r, c, inputs = attack_of(state)
                (aid,) = attack_ids(inputs["stages"])
                own, other_a, other_x = (o["id"] for o in powers_of(inputs["stages"]))
                same = other_x if real == UNOWN_X else other_a
                different = other_a if real == UNOWN_X else other_x
                for choices, code in (([aid], None), ([aid, own], None), ([aid, own, different], None), ([aid, different, own], None),
                                      ([aid, own, same], L.CANDIDATE_INPUT_INVALID), ([aid, same, own], L.CANDIDATE_INPUT_INVALID),
                                      ([aid, own, own], L.CANDIDATE_INPUT_INVALID), ([own], L.CANDIDATE_INPUT_INVALID), ([own, aid], L.CANDIDATE_INPUT_INVALID),
                                      ([aid, "o9"], L.CANDIDATE_INPUT_INVALID), ([aid, 2], L.CANDIDATE_INPUT_INVALID), ([], L.CANDIDATE_INPUT_INVALID)):
                    with self.subTest(choices=choices):
                        self.assertEqual(check_code(session, r, c, choices), code)

    def test_check_is_shape_only_without_energy(self):
        state = fd(UNOWN_X, bench=RATTATA_ONLY, energies=0)  # 必要なエネルギーが足りなくても、check は形だけ
        _h, session, r, c, inputs = attack_of(state)
        (own,) = powers_of(inputs["stages"])
        self.assertIsNone(check_code(session, r, c, ["o1", own["id"]]))

    def test_other_x_used_this_turn_hides_only_the_self_x_injected(self):
        """この番のほかの X（ベンチ）の使用の記録（注入）: 自己 X は示さない（other_use_problem）。記録を持つ個体自身は示す。自己 A は記録で止まらない。"""
        state = fd(UNOWN_X, bench=(mon(UNOWN_X),))
        x = holders(state, UNOWN_X)[0]
        self.assert_offered(with_injected_use_record(state, x), [(x, X_POWER)], note=L.NOTE_FACE_DOWN_GROUP_POWERS)
        state = fd(UNOWN_A, bench=(mon(UNOWN_X),))
        x = holders(state, UNOWN_X)[0]
        self.assert_offered(with_injected_use_record(state, x), [(me(state), A_POWER), (x, X_POWER)])

    def test_effect_on_the_other_side_only_does_not_hide(self):
        """相手の場にだけはたらくふしぎなガス（注入）・期限の過ぎた効果（なし）では示す（持ち主のプレイヤーで問い合わせる）。"""
        state = injected(fd(UNOWN_X, bench=RATTATA_ONLY), OPPONENT_POWER_SUPPRESSION, 0, -2, 0)
        self.assert_offered(state, [(me(state), X_POWER)])


class NotOfferedTest(unittest.TestCase):
    """条件を満たさないときは、自己持ち主を示さない（ほかに示すものがなければ 0.187.0 と同じ空の 2 段目）。"""

    def assert_not_offered(self, state, patch=None):
        with patch or mock.patch.object(L, "_not_checked", L._not_checked):
            _h, session, r, c, inputs = attack_of(state)
            first, second = inputs["stages"]
            ids = [o["id"] for o in first["options"]]
            self.assertEqual((c["processability"], c["reasons"], c["choices_format"]), (L.UNVERIFIED, [L.REASON_FACE_DOWN], "[ワザの番号]"))
            self.assertEqual((second["count"], second["options"], second["options_by_choice"], second["order"], second["note"]),
                             ({"min": 0, "max": 0}, [], {oid: [] for oid in ids}, L.ORDER_NOT_APPLICABLE, OLD_NOTE))
            self.assertEqual(check_code(session, r, c, [ids[0], f"o{len(ids) + 1}"]), L.CANDIDATE_INPUT_INVALID)

    def test_suppressed_by_chemical_gas(self):
        for real in (UNOWN_X, UNOWN_A):
            with self.subTest(real=real):
                self.assert_not_offered(fd(real, bench=(T119.mon(H.MUK),)))  # 自分のベンチのかがくへんかガス
                self.assert_not_offered(fd(real, bench=RATTATA_ONLY, opponent_bench=(T119.mon(H.MUK),)))  # 相手の場のかがくへんかガス

    def test_suppressed_by_field_effects_injected(self):
        for real in (UNOWN_X, UNOWN_A):
            for name, kind, player, created, expires in (("goop_gas", POWER_SUPPRESSION, 1, -1, 0), ("goop_gas_mine", POWER_SUPPRESSION, 0, 0, 1),
                                                         ("strange_gas_on_me", OPPONENT_POWER_SUPPRESSION, 1, -1, 0),
                                                         ("dark_pulse", ATTACK_FIELD_POWER_SUPPRESSION, 1, -1, 0)):
                with self.subTest(real=real, name=name):
                    self.assert_not_offered(injected(fd(real, bench=RATTATA_ONLY), kind, player, created, expires))

    def test_other_x_used_this_turn_injected(self):
        state = fd(UNOWN_X, bench=(mon(UNOWN_X),))
        x = holders(state, UNOWN_X)[0]
        used = with_injected_use_record(state, x).clone()
        holder = used.find_pokemon(x)[1]
        holder.persistent_effects = (*holder.persistent_effects, CannotUsePowers(source_card=used.players[1].active.card, source_player=1,
                                                                                  created_turn=used.turn_number - 1, active_turn=used.turn_number))
        self.assert_not_offered(used)  # ベンチの X は使えない効果で外し、記録で外れる自己 X だけを見る

    def test_artificial_use_prevented_on_the_face_down_attacker(self):
        """人工（不変条件を崩す。うらの間は持続する効果を受けない）: 使い手に使えない効果があれば示さない（エンジンも POWER_USE_PREVENTED で拒否する）。"""
        for real in (UNOWN_X, UNOWN_A):
            with self.subTest(real=real):
                state = fd(real, bench=RATTATA_ONLY).clone()
                a = state.players[0].active
                a.persistent_effects = (*a.persistent_effects, CannotUsePowers(source_card=state.players[1].active.card, source_player=1,
                                                                                created_turn=state.turn_number - 1, active_turn=state.turn_number))
                self.assert_not_offered(state)

    def test_artificial_baby_or_not_basic(self):
        for real in (UNOWN_X, UNOWN_A):
            for stage in (BABY_STAGE, "stage1"):
                with self.subTest(real=real, stage=stage):
                    state = fd(real, bench=RATTATA_ONLY)
                    self.assert_not_offered(state, printed_replaced(state, stage=stage))

    def test_artificial_unclassified_attacker_type(self):
        """人工: 分類済みの型の集合から使い手の型を除くと、自己持ち主も別の持ち主も示さない（未知の型を自動で安全としない）。"""
        for real, kind in ((UNOWN_X, "CoinsUntilTailsBonusToGroupAttack"), (UNOWN_A, "CounterBonusToGroupAttack")):
            with self.subTest(real=real):
                state = fd(real, bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X)))
                self.assert_not_offered(state, mock.patch.object(L, "FACE_DOWN_GROUP_POWER_ATTACKER_TYPES", L.FACE_DOWN_GROUP_POWER_ATTACKER_TYPES - {kind}))

    def test_artificial_power_type_not_offered(self):
        """人工: 示す力の型を［XXXXX］だけにすると、自己 A は示さない（型で決める。名前では決めない）。"""
        state = fd(UNOWN_A, bench=RATTATA_ONLY)
        self.assert_not_offered(state, mock.patch.object(L, "_FACE_DOWN_GROUP_POWERS", (E.CoinsUntilTailsBonusToGroupAttack,)))

    def test_artificial_other_name_group(self):
        state = fd(UNOWN_X, bench=RATTATA_ONLY)
        self.assert_not_offered(state, printed_replaced(state, name_group="アンノーンでない"))

    def test_not_holder_cards(self):
        """自己持ち主の力を持たないアンノーン（N）・アンノーンでない使い手・変身の経路（メタモン。印刷のワザなし）は自己持ち主を示さない。"""
        self.assert_not_offered(fd(UNOWN_N, bench=RATTATA_ONLY))
        self.assert_not_offered(fd(H.GIOVANNIS_NIDORAN_M, bench=RATTATA_ONLY))
        state = fd(H.DITTO, bench=RATTATA_ONLY, opponent=mon(UNOWN_X, (H.PSYCHIC,)))
        _h, _s, _r, c, inputs = attack_of(state)
        self.assertEqual((c["processability"], c["reasons"]), (L.NOT_IMPLEMENTED, [L.REASON_FACE_DOWN, L.REASON_NO_PRINTED_ATTACK]))
        self.assertNotIn(L.ADDON_WITH_POWER, json.dumps(inputs, ensure_ascii=False))

    def test_not_the_actors_turn(self):
        self.assertEqual([c["kind"] for c in host_candidates(fd(UNOWN_X, bench=RATTATA_ONLY), actor=1)], [])


class SubmitTest(unittest.TestCase):
    """送信は既存のコマンド（UseAttack(with_power / with_powers)）と同じ結果。処理の順と既存の停止は変えない。"""

    def assert_same(self, state, choices, command, outcome):
        host, result = via_u7(state, lambda s: choices)
        game, direct = via_direct(state, command)
        self.assertEqual(result.outcome, outcome, result)
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual(snap(host.game.state), snap(game.state))
        return host, result

    def test_self_powers_same_as_direct(self):
        for real, damage in ((UNOWN_X, 30), (UNOWN_A, 10)):
            with self.subTest(real=real):
                state = H.with_coin_bits(fd(real, bench=RATTATA_ONLY), *COINS)
                host, _ = self.assert_same(state, ["o1", "o2"], UseAttack(0, 0, with_power=me(state)), D.ACCEPTED)
                after = host.game.state
                self.assertEqual(after.players[1].active.damage, damage)
                self.assertFalse(after.is_face_down(after.players[0].active))
                event = [e for e in after.log if e["kind"] in ("group_attack_power_coins", "group_attack_power_counters")][-1]
                self.assertEqual(event["step"], 2)  # 発生源がワザを使うポケモン（p.321 の 2 段階）
                if real == UNOWN_A:
                    self.assertEqual((event["counters"], event["amount"]), (0, 0))
                self.assert_same(state, ["o1"], UseAttack(0, 0), D.ACCEPTED)

    def test_self_and_other_holders_same_as_direct(self):
        state = H.with_coin_bits(fd(UNOWN_X, bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X))), *COINS)
        own, a, x = me(state), holders(state, UNOWN_A)[0], holders(state, UNOWN_X)[0]
        for choices, command, damage in ((["o1", "o2", "o3"], UseAttack(0, 0, with_powers=(own, a)), 50),
                                         (["o1", "o3", "o2"], UseAttack(0, 0, with_powers=(a, own)), 50),
                                         (["o1", "o4"], UseAttack(0, 0, with_power=x), 30)):
            with self.subTest(choices=choices):
                host, _ = self.assert_same(state, choices, command, D.ACCEPTED)
                self.assertEqual(host.game.state.players[1].active.damage, damage)
        state = H.with_coin_bits(fd(UNOWN_A, bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X))), *COINS)
        own, x = me(state), holders(state, UNOWN_X)[0]
        host, _ = self.assert_same(state, ["o1", "o2", "o4"], UseAttack(0, 0, with_powers=(own, x)), D.ACCEPTED)
        self.assertEqual(host.game.state.players[1].active.damage, 30)

    def test_existing_stops_are_kept_and_the_answer_can_be_redone(self):
        """XP1（ベイビィ）・NT1（変わり身の術）・v0.4b（ダメージを受けない状態。注入）: 自己［XXXXX］を選ぶと check は valid、送信は既存の停止で拒否（状態・乱数・ログ・決定・
        使い手のうらが不変、ほかの人に知らせない）。拒否のあと、同じ版で力なし・自己［ANGER］に答え直せる。"""
        prevented = fd(UNOWN_X, bench=RATTATA_ONLY).clone()
        opp = prevented.players[1].active
        opp.persistent_effects = (*opp.persistent_effects, PreventDamage(opp.card, 1, prevented.turn_number - 1, prevented.turn_number))
        for name, state, code in (("baby", fd(UNOWN_X, bench=RATTATA_ONLY, opponent=mon(PICHU), opponent_bench=(mon(H.RATTATA),)), "UNRESOLVED_GROUP_POWER_COIN_ORDER"),
                                  ("ninja_trick", fd(UNOWN_X, bench=RATTATA_ONLY, opponent=mon(H.KOGAS_PIDGEY, trainers=[(H.KOGAS_NINJA_TRICK, None)]),
                                                     opponent_bench=(mon(H.RATTATA),)), "UNRESOLVED_NINJA_TRICK_ATTACK_COIN_ORDER"),
                                  ("prevented_injected", prevented, "UNRESOLVED_PREVENTED_COIN_DAMAGE")):
            with self.subTest(name=name):
                state = H.with_coin_bits(state, HD, *COINS)
                hosted = A.HostedGame(state.clone())
                hub = ClientHub(hosted)
                player = hub.player(0)
                r = player.handle({**REQ, "type": "candidates"})["response"]
                c = next(x_ for x_ in r["candidates"] if x_["kind"] == L.KIND_USE_ATTACK)
                stages = player.handle({**REQ, "type": "inputs", "game": r["game"], "revision": r["revision"], "candidate": c["id"]})["response"]["stages"]
                self.assertEqual([(o["pokemon"], o["power"]) for o in powers_of(stages)], [(me(state), X_POWER)])
                checked = player.handle({**REQ, "type": "check", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o1", "o2"]})
                self.assertTrue(checked["response"]["valid"])
                hub.take_updates(1), hub.take_updates("spectator")
                before = snap(hosted.state)
                sent = player.handle({**REQ, "type": "submit", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o1", "o2"]})
                self.assertEqual(sent["outcome"], D.REJECTED)
                self.assertEqual(snap(hosted.state), before)
                self.assertTrue(hosted.state.is_face_down(hosted.state.players[0].active))  # 公開も元に戻る
                self.assertEqual([hub.take_updates(v) for v in (1, "spectator")], [[], []])
                game, direct = via_direct(state, UseAttack(0, 0, with_power=me(state)))
                self.assertEqual((direct.outcome, direct.diagnosis.case_id), (D.REJECTED, code))
                self.assertEqual(snap(game.state), snap(state))
                again = player.handle({**REQ, "type": "submit", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o1"]})
                self.assertEqual(again["outcome"], D.ACCEPTED)
                game, direct = via_direct(state, UseAttack(0, 0))
                self.assertEqual(snap(hosted.state), snap(game.state))
        for name, state in (("baby", fd(UNOWN_A, bench=RATTATA_ONLY, opponent=mon(PICHU), opponent_bench=(mon(H.RATTATA),))),):
            with self.subTest(name=f"anger_{name}"):
                state = H.with_coin_bits(state, HD, *COINS)
                self.assert_same(state, ["o1", "o2"], UseAttack(0, 0, with_power=me(state)), D.ACCEPTED)

    def test_rejection_after_reveal_rolls_back(self):
        """必要なエネルギーが足りない: おもてにしたあとエンジンが拒否（状態・乱数・ログ・決定・使い手のうらが不変）。"""
        state = fd(UNOWN_X, bench=RATTATA_ONLY, energies=0)
        host, _ = self.assert_same(state, ["o1", "o2"], UseAttack(0, 0, with_power=me(state)), D.REJECTED)
        self.assertEqual(snap(host.game.state), snap(state))
        self.assertTrue(host.game.state.is_face_down(host.game.state.players[0].active))

    def test_same_power_twice_rejected_by_check_and_engine(self):
        state = H.with_coin_bits(fd(UNOWN_X, bench=(mon(UNOWN_X),)), *COINS)
        _h, session, r, c, _inputs = attack_of(state)
        self.assertEqual(check_code(session, r, c, ["o1", "o2", "o3"]), L.CANDIDATE_INPUT_INVALID)
        game, direct = via_direct(state, UseAttack(0, 0, with_powers=(me(state), holders(state, UNOWN_X)[0])))
        self.assertEqual((direct.outcome, direct.diagnosis.diagnostic_id), (D.REJECTED, "POWER_ALREADY_USED"))
        self.assertEqual(snap(game.state), snap(state))


class BoundaryTest(unittest.TestCase):
    """情報境界: 候補・入力・check は本人の知識と公開の状態だけで決まり、ほかの人への応答・通知を変えない。"""

    def own_view(self, state):
        _h, session, r, c, inputs = attack_of(state)
        checks = [check_code(session, r, c, ch) for ch in (["o1"], ["o1", "o2"], ["o1", "o3"], ["o1", "o2", "o3"], ["o2"])]
        return without_handles(r), inputs, checks

    def test_opponent_secrets_do_not_change_the_actors_inputs(self):
        for real in (UNOWN_X, UNOWN_A):
            with self.subTest(real=real):
                views = [self.own_view(fd(real, bench=(mon(UNOWN_X),), opponent_hand=hand)) for hand in ((H.FIRE, H.FIRE), (H.RATTATA, H.POTION), ())]
                self.assertEqual(views[0], views[1])
                self.assertEqual([v[1:] for v in views], [views[0][1:]] * 3)

    def test_the_actors_real_card_does_not_reach_others(self):
        others = []
        for real in (UNOWN_X, UNOWN_A, UNOWN_N, H.GIOVANNIS_NIDORAN_M, H.DITTO):
            state = fd(real, bench=RATTATA_ONLY)
            hub = ClientHub(A.HostedGame(state.clone()))
            mine = hub.player(0)
            r = mine.handle({**REQ, "type": "candidates"})["response"]
            c = next(x for x in r["candidates"] if x["kind"] == L.KIND_USE_ATTACK)
            mine.handle({**REQ, "type": "inputs", "game": r["game"], "revision": r["revision"], "candidate": c["id"]})
            mine.handle({**REQ, "type": "check", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o1"]})
            others.append(([observe(state, v) for v in (1, None)], without_handles(hub.player(1).handle({**REQ, "type": "candidates"})["response"]),
                           [hub.take_updates(a) for a in (1, "spectator")]))
        for other in others[1:]:
            self.assertEqual(other, others[0])

    def test_reading_candidates_inputs_and_check_changes_nothing(self):
        state = fd(UNOWN_X, bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X)))
        hub = ClientHub(A.HostedGame(state.clone()))
        hub.take_updates(1), hub.take_updates("spectator")
        player = hub.player(0)
        before = snap(state)
        r = player.handle({**REQ, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == L.KIND_USE_ATTACK)
        player.handle({**REQ, "type": "inputs", "game": r["game"], "revision": r["revision"], "candidate": c["id"]})
        for choices in (["o1", "o2", "o3"], ["o1", "o2", "o4"], ["o1", "o2"]):
            player.handle({**REQ, "type": "check", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": choices})
        self.assertEqual(snap(state), before)
        self.assertEqual(rng_fingerprint(state.rng), before[1])
        self.assertEqual([hub.take_updates(a) for a in (0, 1, "spectator")], [[], [], []])

    def test_no_reveal_or_engine_check_while_building(self):
        """公開・エンジンの確かめ（力の確かめ・使い手の条件・ワザの確かめ）を呼ばない。乱数を使わないことは test_reading_candidates_inputs_and_check_changes_nothing の
        rng_fingerprint で確かめる。"""
        def boom(*_a, **_k):
            raise AssertionError("候補の作成・入力の検査から呼んではいけない")
        probe = L._probe

        def probe_without_attacks(check, *args):
            if any(isinstance(a, UseAttack) for a in args):
                boom()
            return probe(check, *args)
        state = fd(UNOWN_X, bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X)))
        with mock.patch.object(EN, "_reveal_for_action", boom), mock.patch.object(EN, "reveal_face_down", boom), \
                mock.patch.object(L, "check_use_attack", boom), mock.patch.object(E, "group_attack_power_check", boom), \
                mock.patch.object(E, "group_attack_powers_check", boom), mock.patch.object(L, "_probe", probe_without_attacks), \
                mock.patch.object(E.CoinsUntilTailsBonusToGroupAttack, "usable_for", boom), mock.patch.object(E.CounterBonusToGroupAttack, "usable_for", boom):
            _h, session, r, c, inputs = attack_of(state)
            self.assertEqual(len(powers_of(inputs["stages"])), 3)
            self.assertIsNone(check_code(session, r, c, ["o1", "o2", "o3"]))
            self.assertEqual(check_code(session, r, c, ["o1", "o2", "o4"]), L.CANDIDATE_INPUT_INVALID)


class RegistryTest(unittest.TestCase):
    """登録: 自己持ち主の力を持つアンノーンは、どれもたね・ベイビィでない・分類済みで、最初のワザといっしょに使う力が示す型。"""

    @staticmethod
    def self_holder_problems(definitions):
        problems = []
        for card_id, definition in sorted(definitions.items()):
            declared = [type(E.DEFAULT_EFFECTS.power_entry(card_id, p.index).effect) for p in definition.powers
                        if E.DEFAULT_EFFECTS.power_entry(card_id, p.index) is not None
                        and isinstance(E.DEFAULT_EFFECTS.power_entry(card_id, p.index).effect, E.AttackDeclaredPower)]
            if not declared or declared[0] not in L._FACE_DOWN_GROUP_POWERS:
                continue
            if not definition.is_basic_pokemon or definition.is_baby_pokemon:
                problems.append(card_id)
        return problems

    def test_every_holder_card_is_basic_and_not_baby(self):
        pool, found = registry_unown()
        definitions = {card_id: pool.get(card_id) for card_id in found}
        self.assertEqual(self.self_holder_problems(definitions), [])
        holders_found = sorted(card_id for card_id in definitions if card_id in (UNOWN_X, UNOWN_A))
        self.assertEqual(holders_found, [UNOWN_A, UNOWN_X])
        for card_id in holders_found:
            self.assertTrue(L._classified_group_attacker(fd(card_id, bench=RATTATA_ONLY), pool.get(card_id)))

    def test_artificial_baby_holder_is_detected(self):
        pool, found = registry_unown()
        definitions = {card_id: pool.get(card_id) for card_id in found}
        definitions[UNOWN_X] = dataclasses.replace(definitions[UNOWN_X], stage=BABY_STAGE)
        self.assertEqual(self.self_holder_problems(definitions), [UNOWN_X])


class RegressionTest(unittest.TestCase):
    def test_other_holder_only_keeps_the_v0_191_note_and_values(self):
        state = fd(UNOWN_N, bench=(mon(UNOWN_A, damage=20), mon(UNOWN_X)))
        _h, _s, _r, _c, inputs = attack_of(state)
        self.assertEqual([(o["pokemon"], o["power"]) for o in powers_of(inputs["stages"])],
                         [(holders(state, UNOWN_A)[0], A_POWER), (holders(state, UNOWN_X)[0], X_POWER)])
        self.assertEqual(inputs["stages"][1]["note"], L.NOTE_FACE_DOWN_GROUP_POWERS)

    def test_guarantee_is_the_same_for_every_real_card(self):
        seen = {str(attack_of(fd(real, bench=RATTATA_ONLY))[3]["guarantees"]) for real in (UNOWN_N, UNOWN_X, UNOWN_A, H.GIOVANNIS_NIDORAN_M, H.DITTO)}
        self.assertEqual(seen, {str(L.GUARANTEE_FACE_DOWN_ATTACK)})
        self.assertIn("v0.192 から", L.GUARANTEE_FACE_DOWN_ATTACK["preconditions"])

    def test_face_up_declaration_unchanged(self):
        from tests.test_legal_actions_r2_unown_v0_191 import face_up
        from tests.test_legal_actions_u7_4 import attack_stages
        c, stages = attack_stages(face_up(UNOWN_X, bench=(mon(UNOWN_A, damage=20),)))
        self.assertNotIn(L.REASON_FACE_DOWN, c["reasons"])
        self.assertEqual([o["power"] for o in powers_of(stages)], [X_POWER, A_POWER])


if __name__ == "__main__":
    unittest.main()

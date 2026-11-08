"""v0.166（U7-4。docs/legal-actions-u7-4.md）: ワザの候補・宣言の入力・検査・送信の回帰テスト。

確かめの種類を分ける:

- 構築盤面（tests.helpers.build_test_state と、既存の版のテストの盤面の作り）: 通常のワザ・エネルギー不足・特殊状態・使う条件・宣言といっしょに選ぶもの
  （クチバシティジムのコイン・［すいりょくはつでん］・［XXXXX］）・コピーと変身・エネルギーを捨てるワザの HC1・山札を見るワザと双子・取っ手
- 構築盤面からの合法な操作: 宣言のあとの決定（ひのこのトラッシュ・ドライアップの対象）に U7 の answer_decision で答える。コインはテストの乱数の仕込み（with_coin_bits）
- new_game からの合法な操作の列: 準備・エネルギー・ワザの宣言・決定への答え・番の移り（3 つの規約集合。直接のコマンドと同じ状態）

停止コードの文字列はテストの中に書かない（区分とホストの段のコード・診断の分類で確かめる）。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import ResolveDecision, UseAttack
from kyuura_engine.observation import observe
from kyuura_engine.state import Phase
from kyuura_engine.view_record import FORBIDDEN_KEYS
from tests import helpers as H
from tests import test_deferred_shortage_user_promos_v0_127 as T127
from tests import test_instant_trainers_v0_55 as T55
from tests import test_shining_gentle_v0_83 as T83
from tests import test_stadiums_v0_57 as T57
from tests import test_type_energy_colors_v0_88 as T88
from tests import test_unbounded_coins_heal_allocation_v0_118 as T118
from tests.log_audit import owned_card_ids, public_view
from tests.test_legal_actions_u7_1 import keys, snap, without_handles
from tests.test_legal_actions_u7_3 import (
    CONNECT_DECK,
    SETS,
    Recording,
    cand,
    host_of,
    inputs_of,
    setup_with_u7,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
HD, TL = CoinSide.HEADS, CoinSide.TAILS
CHARIZARD = "PMCG1-021"  # リザードン（ほのおのうず: 炎エネルギー 2 枚をはがしてすてる。こんらんで使うと HC1 で止める）
DITTO = "PMCG3-042"  # メタモン（［へんしん］: 相手の対戦ポケモンの姿・ワザ）
FARFETCHD = "PMCG1-063"  # カモネギ（ネギでたたく: 場に出てから 1 回しか使えない）
NIDORAN_F = "PMCG2-001"  # ニドラン♀（なかまをよぶ: 山札からたねポケモンをベンチに出す。ベンチに空きがなければ使えない）
SLOWPOKE = "PMCG3-027"  # ヤドン（ぼーっとする: ダメージカウンターがなければ使えない）
CONTRACT = {"contract": "kyuura-client-api", "format": 1}
OPPONENT = {"active": H.STARYU, "hand": [H.WATER], "deck": [H.WATER] * 5, "prizes": 2}


def board(p0, p1=None, *, turn=3):
    return H.build_test_state([{"deck": [H.FIRE] * 5, "prizes": 2, **p0}, dict(p1 or OPPONENT)], turn_number=turn)


def attack_stages(state, actor=0):
    _r, c, inputs = inputs_of(host_of(state).session(actor), L.KIND_USE_ATTACK)
    return c, (None if inputs is None else inputs["stages"])


def attack_id(stages, name):
    return next(o["id"] for o in stages[0]["options"] if o["name_ja"] == name)


def via_u7(state, pick, *, actor=None):
    host = host_of(state.clone())
    session = host.session(state.current_player if actor is None else actor)
    r, c, inputs = inputs_of(session, L.KIND_USE_ATTACK)
    choices = pick(inputs["stages"])
    return host, session.submit(r["game"], r["revision"], c["id"], choices)


def via_direct(state, command):
    game = A.HostedGame(state.clone())
    return game, game.submit(command, submitter=command.player)


def answer_with_u7(host, pick=None):
    """今の決定に、U7 の answer_decision の候補で答える（選べるものの先頭から下限の数。pick があればそれ）。"""
    state = host.game.state
    session = host.session(state.decision.player)
    r = session.candidates()
    c = r["candidates"][0]
    assert c["kind"] in (L.KIND_ANSWER_DECISION, L.KIND_TAKE_PRIZE, L.KIND_PROMOTE_ACTIVE), c
    stage = session.inputs(r["game"], r["revision"], c["id"])["stages"][0]
    if pick is not None:
        choices = pick(stage)
    elif stage["input"] == L.INPUT_CHOOSE_VALUE:
        choices = [stage["range"]["min"]]
    else:
        choices = [o["id"] for o in stage["options"] if o["processability"] in L.EXECUTABLE][:max(1, stage["count"]["min"])]
    return session.submit(r["game"], r["revision"], c["id"], choices)


class Same:
    def assert_same_as_direct(self, state, pick, command):
        host, result = via_u7(state, pick)
        game, direct = via_direct(state, command)
        self.assertEqual(result.outcome, D.ACCEPTED, result)
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(command.player)))
        self.assertEqual(snap(host.game.state), snap(game.state))
        return host, game


class MappingTest(unittest.TestCase):
    """対応表（docs/legal-actions-u7-4.md 2 章）: use_attack は UseAttack だけ。ほかの入口（トレーナー・特殊能力・スタジアムなど）は対応しない種類のまま。"""

    def test_kind_and_coverage(self):
        r = host_of(board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}})).session(0).candidates()
        cov = r["coverage"]
        self.assertEqual(cov["completeness"], L.PARTIAL)
        self.assertEqual(cov["offered_kinds"], [L.KIND_END_TURN, L.KIND_USE_ATTACK])
        self.assertEqual(cov["scope_kinds"], list(L.MAIN_KINDS))
        self.assertEqual(cov["not_covered_kinds"], ["use_power",  # v0.167（U7-5a・U7-5b）: 3 種類は対応した種類。v0.169（U7-5c）: play_trainer、v0.170（U7-5d）: use_stadium も
                                                    "check_face_up_deck"])
        self.assertIn(L.KIND_USE_ATTACK, cov["implemented_kinds"])
        c = cand(r, L.KIND_USE_ATTACK)
        self.assertEqual((c["id"], c["processability"], c["reasons"]), ("c2", L.MAY_STOP_LATER, [L.REASON_CONTINUATION, L.REASON_PREFLIGHT]))
        self.assertEqual([s["input"] for s in c["input_stages"]], [L.INPUT_CHOOSE_OPTION, L.INPUT_CHOOSE_OPTION])

    def test_option_display(self):
        _c, stages = attack_stages(board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE, H.FIRE]}}))
        first = stages[0]["options"][1]
        self.assertEqual({k: first[k] for k in ("card_id", "attack_index", "route", "name_ja", "cost", "damage", "eligible", "processability")},
                         {"card_id": H.CHARMANDER, "attack_index": 1, "route": "form", "name_ja": "ひのこ", "cost": ["fire", "colorless"], "damage": "30",
                          "eligible": True, "processability": L.MAY_STOP_LATER})
        self.assertEqual(stages[1]["options"], [])
        self.assertEqual(stages[1]["options_by_choice"], {"o1": [], "o2": []})
        self.assertEqual((stages[1]["count"], stages[1]["decline"]), ({"min": 0, "max": 0}, True))


class NormalAttackTest(Same, unittest.TestCase):
    def test_normal_attack_same_as_direct(self):
        state = board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}})
        host, _ = self.assert_same_as_direct(state, lambda s: [attack_id(s, "ひっかく")], UseAttack(0, 0))
        self.assertEqual(host.game.state.current_player, 1)  # ワザのあと番が移る

    def test_energy_shortage(self):
        _c, stages = attack_stages(board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}}))
        self.assertEqual([o["name_ja"] for o in stages[0]["options"]], ["ひっかく"])  # ひのこ（炎無）は足りない（ゲーム上できない）
        c, _ = attack_stages(board({"active": H.CHARMANDER}))
        self.assertIsNone(c)  # どのワザも足りない: 候補なし（scope には use_attack がある）

    def test_special_conditions(self):
        for condition in ({"sleep": True}, {"paralysis": 3}):
            with self.subTest(condition=condition):
                c, _ = attack_stages(board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE], **condition}}))
                self.assertIsNone(c)
        c, stages = attack_stages(board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE], "confusion": True}}))
        self.assertEqual((c["processability"], [o["name_ja"] for o in stages[0]["options"]]), (L.MAY_STOP_LATER, ["ひっかく"]))  # こんらんのコインは宣言のあと

    def test_usage_condition(self):
        damaged = board({"active": {"card": SLOWPOKE, "energy": [H.PSYCHIC, H.PSYCHIC], "damage": 10}})
        plain = board({"active": {"card": SLOWPOKE, "energy": [H.PSYCHIC, H.PSYCHIC]}})
        self.assertIn("ぼーっとする", [o["name_ja"] for o in attack_stages(damaged)[1][0]["options"]])
        self.assertNotIn("ぼーっとする", [o["name_ja"] for o in attack_stages(plain)[1][0]["options"]])  # ダメージカウンターがない: 使えない

    def test_not_my_turn(self):
        r = host_of(board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}})).session(1).candidates()
        self.assertEqual((r["candidates"], r["situation"]), ([], L.WAITING_FOR_PLAYER))


class DecisionAfterDeclarationTest(unittest.TestCase):
    """宣言のあとの決定は、宣言の入力に移さない（受理のあと answer_decision で答える）。"""

    def test_ember_discard_is_a_decision(self):
        state = board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE, H.FIRE]}})
        host, result = via_u7(state, lambda s: [attack_id(s, "ひのこ")])
        self.assertEqual((result.outcome, result.view.status), (D.ACCEPTED, D.AWAITING_DECISION))
        r = host.session(0).candidates()
        c = r["candidates"][0]
        self.assertEqual(c["kind"], L.KIND_ANSWER_DECISION)
        stage = host.session(0).inputs(r["game"], r["revision"], c["id"])["stages"][0]
        self.assertEqual(len(stage["options"]), 2)  # どちらの炎エネルギーをトラッシュするか（宣言の前には聞かない）
        done = answer_with_u7(host)
        self.assertEqual(done.outcome, D.ACCEPTED)
        direct = A.HostedGame(state.clone())
        direct.submit(UseAttack(0, 1), submitter=0)
        d = direct.state.decision
        direct.submit(ResolveDecision(0, d.id, (d.options[0],)), submitter=0)
        self.assertEqual(snap(direct.state), snap(host.game.state))

    def test_target_choice_after_declaration(self):
        state = T127.dry_board(2)
        _c, stages = attack_stages(state)
        self.assertEqual(stages[1]["options"], [])  # 対象は宣言といっしょに選ばない
        _host, result = via_u7(state, lambda s: [s[0]["options"][0]["id"]])
        self.assertEqual(result.view.status, D.AWAITING_DECISION)


class CoinAttackTest(Same, unittest.TestCase):
    def test_coins_are_not_inputs(self):
        state = board({"active": {"card": H.DODUO, "energy": [H.FIRE, H.FIRE]}})
        _c, stages = attack_stages(state)
        self.assertEqual([s["role"] for s in stages], ["attack", "declaration_options"])  # コインの結果を選ばせない
        for side in (HD, TL):
            with self.subTest(side=side):
                rigged = H.with_coin_bits(state, side, side)
                self.assert_same_as_direct(rigged, lambda s: [s[0]["options"][0]["id"]], UseAttack(0, 0))


class DeclarationOptionTest(Same, unittest.TestCase):
    """宣言といっしょに選ぶもの（UseAttack の stadium_coin・attack_power・with_power・with_powers）。"""

    def test_stadium_coin(self):
        state = T57.placed(H.VERMILION_CITY_GYM, active=T55.mon(H.LT_SURGES_VOLTORB, (H.LIGHTNING, H.LIGHTNING)))
        _c, stages = attack_stages(state)
        coin = next(o for o in stages[1]["options"] if o["addon"] == L.ADDON_STADIUM_COIN)
        aid = stages[0]["options"][0]["id"]
        self.assertIn(coin["id"], [p["option"] for p in stages[1]["options_by_choice"][aid]])
        for side in (HD, TL):
            rigged = H.with_coin_bits(state, side, side, side, side)
            self.assert_same_as_direct(rigged, lambda s: [aid, coin["id"]], UseAttack(0, 0, stadium_coin=True))
            self.assert_same_as_direct(rigged, lambda s: [aid], UseAttack(0, 0))  # 選ばない（0 個）
        other = T57.placed(H.VERMILION_CITY_GYM, active=T55.mon(H.RATTATA, (H.FIRE,)))
        self.assertEqual(attack_stages(other)[1][1]["options"], [])  # 「マチスのポケモン」でない: 選べない

    def test_attack_power(self):
        state = T83.board(T88.lanturn1((T88.L, T88.L, T88.W, T88.W)), opponent=T83.mon(H.CHANSEY))
        _c, stages = attack_stages(state)
        power = next(o for o in stages[1]["options"] if o["addon"] == L.ADDON_ATTACK_POWER)
        aid = attack_id(stages, "まぶしいひかり")
        self.assertIn(power["id"], [p["option"] for p in stages[1]["options_by_choice"][aid]])
        rigged = H.with_coin_results(state, TL)
        self.assert_same_as_direct(rigged, lambda s: [aid, power["id"]], UseAttack(0, 0, attack_power=True))

    def test_with_power_order(self):
        state = T118.board(T118.mon(T118.UNOWN_X, (T118.PS,)), bench=(T118.mon(T118.UNOWN_X),), opponent=T118.mon(H.ONIX))
        _c, stages = attack_stages(state)
        powers = [o for o in stages[1]["options"] if o["addon"] == L.ADDON_WITH_POWER]
        self.assertEqual([o["pokemon"] for o in powers], [state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id])
        aid = stages[0]["options"][0]["id"]
        bench_id = state.players[0].bench[0].pokemon_id
        rigged = H.with_coin_bits(state, HD, TL)
        self.assert_same_as_direct(rigged, lambda s: [aid, powers[1]["id"]], UseAttack(0, 0, with_power=bench_id))
        host = host_of(state)
        session = host.session(0)
        r, c, _ = inputs_of(session, L.KIND_USE_ATTACK)
        both = session.check(r["game"], r["revision"], c["id"], [aid, powers[0]["id"], powers[1]["id"]])
        direct = A.HostedGame(state.clone()).submit(UseAttack(0, 0, with_powers=(powers[0]["pokemon"], powers[1]["pokemon"])), submitter=0)
        # 同じ力（［XXXXX］）を 2 つ: エンジンの確かめが拒否する組み合わせは入力の検査で不正（直接のコマンドも拒否）
        self.assertEqual((both["valid"], both["refusal"]["code"], direct.outcome), (False, L.CANDIDATE_INPUT_INVALID, D.REJECTED))


class CopyAndTransformTest(Same, unittest.TestCase):
    def test_metronome_choice_is_after_declaration(self):
        state = board({"active": {"card": H.CLEFABLE, "energy": [H.FIRE], "evolved_from": _below(H.CLEFABLE)}},
                      {**OPPONENT, "active": {"card": H.CHARMANDER, "energy": [H.FIRE]}})
        _c, stages = attack_stages(state)
        aid = attack_id(stages, "ゆびをふる")
        host, result = via_u7(state, lambda s: [aid])
        self.assertEqual((result.outcome, result.view.status), (D.ACCEPTED, D.AWAITING_DECISION))  # 写すワザは宣言のあとの決定で選ぶ
        game, _direct = via_direct(state, UseAttack(0, 0))
        self.assertEqual(snap(host.game.state), snap(game.state))

    def test_transform_attacks_and_copied_once_attack_stop(self):
        state = board({"active": {"card": DITTO, "energy": [H.FIRE]}}, {**OPPONENT, "active": FARFETCHD})
        c, stages = attack_stages(state)
        options = stages[0]["options"]
        copied = next(o for o in options if o["name_ja"] == "ネギでたたく")
        self.assertEqual((copied["card"], copied["eligible"], copied["processability"]), (state.players[1].active.card, False, L.RULING_UNRESOLVED))
        self.assertEqual(copied["reasons"], [L.REASON_STOPS])
        host = host_of(state)
        session = host.session(0)
        r, c, _ = inputs_of(session, L.KIND_USE_ATTACK)
        before = snap(host.game.state)
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], [copied["id"]]).refusal.code, L.CANDIDATE_NOT_EXECUTABLE)
        self.assertEqual(snap(host.game.state), before)
        _game, direct = via_direct(state, UseAttack(0, copied["attack_index"], copied["card"]))
        self.assertEqual(direct.outcome, D.REJECTED)  # 直接送ればエンジンの拒否（候補は消さず、送らない）
        self.assertEqual(direct.view_for(0).category, D.RULING_UNRESOLVED)
        other = board({"active": {"card": DITTO, "energy": [H.FIRE]}}, {**OPPONENT, "active": H.CHARMANDER})
        _c, stages = attack_stages(other)
        transformed = stages[0]["options"][0]
        self.assertEqual((transformed["card"], transformed["card_id"], transformed["name_ja"]), (other.players[1].active.card, H.CHARMANDER, "ひっかく"))
        self.assert_same_as_direct(other, lambda s: [transformed["id"]], UseAttack(0, transformed["attack_index"], transformed["card"]))


def _below(card_id):
    from kyuura_engine.cards import load_card_pool

    pool = load_card_pool()
    return next(c for c in sorted(pool.playable_ids) if pool.get(c).name_ja == pool.get(card_id).evolves_from)


class EnergyDiscardStopTest(unittest.TestCase):
    """エネルギーを捨てるワザの既存の停止（HC1）は外さない: こんらんの「ほのおのうず」は、エンジンが宣言の前の先読みで拒否する（状態は変わらない）。"""

    def test_hc1_is_refused_by_the_engine_not_the_candidates(self):
        confused = board({"active": {"card": CHARIZARD, "evolved_from": [H.CHARMANDER, H.CHARMELEON], "energy": [H.FIRE] * 4, "confusion": True}}, turn=7)
        c, stages = attack_stages(confused)
        self.assertEqual((c["processability"], stages[0]["options"][0]["processability"]), (L.MAY_STOP_LATER, L.MAY_STOP_LATER))  # 先読みを呼ばないので区分は変わらない
        host = host_of(confused)
        session, other = host.session(0), host.session(1)
        r, c, _ = inputs_of(session, L.KIND_USE_ATTACK)
        r1 = other.candidates()
        before = snap(host.game.state)
        result = session.submit(r["game"], r["revision"], c["id"], [stages[0]["options"][0]["id"]])
        _game, direct = via_direct(confused, UseAttack(0, 0))
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual((result.outcome, result.view.category), (D.REJECTED, D.RULING_UNRESOLVED))
        self.assertEqual(snap(host.game.state), before)
        self.assertTrue(session.check(r["game"], r["revision"], c["id"], [stages[0]["options"][0]["id"]])["valid"])  # 拒否では取っ手を失効させない
        self.assertEqual(other.check(r1["game"], r1["revision"], "c1", [])["refusal"]["code"], L.CANDIDATE_UNKNOWN)  # 相手の取っ手も失効しない（STALE ではない）
        plain = board({"active": {"card": CHARIZARD, "evolved_from": [H.CHARMANDER, H.CHARMELEON], "energy": [H.FIRE] * 4}}, turn=7)
        _host2, accepted = via_u7(plain, lambda s: [s[0]["options"][0]["id"]])
        self.assertEqual(accepted.outcome, D.ACCEPTED)

    def test_rejected_vs_stop_after_acceptance(self):
        """宣言の拒否（状態は同じ）と、受理のあとの決定の答えで止まる（ドライアップの「おもて」が多い。DU1）を区別する。"""
        state = H.with_coin_bits(T127.dry_board(2), *T127.run(3))  # テストの乱数の仕込み（宣言ではコインを投げない。答えのあとの「おもて」3 枚）
        host, declared = via_u7(state, lambda s: [s[0]["options"][0]["id"]])
        self.assertEqual((declared.outcome, declared.view.status), (D.ACCEPTED, D.AWAITING_DECISION))
        answered = answer_with_u7(host, lambda stage: [next(o["id"] for o in stage["options"] if o["value"] == host.game.state.players[1].active.pokemon_id)])
        self.assertEqual((answered.outcome, answered.view.status), (D.ACCEPTED, D.HALTED))
        r = host.session(0).candidates()
        self.assertEqual((r["situation"], r["candidates"]), (L.HALTED, []))


class SearchAttackTwinTest(unittest.TestCase):
    """山札を見るワザ（なかまをよぶ）と、山札・サイド・相手の手札の配分だけが違う双子: 候補・数・並び・制約・理由・不正な入力への答えが同じ。"""

    def twins(self):
        mine = {"active": {"card": NIDORAN_F, "energy": [H.GRASS, H.GRASS]}, "bench": [H.RATTATA], "hand": [H.FIRE]}
        a = board({**mine, "deck": [H.FIRE, NIDORAN_F, H.PONYTA], "prizes": [H.WATER, H.FIRE]},
                  {**OPPONENT, "hand": [H.WATER, H.CHARMELEON], "deck": [H.WATER, H.FIRE, H.SEEL], "prizes": [H.FIRE, H.WATER]})
        b = board({**mine, "deck": [H.FIRE, H.WATER, H.FIRE], "prizes": [NIDORAN_F, H.PONYTA]},
                  {**OPPONENT, "hand": [H.SEEL, H.FIRE], "deck": [H.CHARMELEON, H.WATER, H.WATER], "prizes": [H.WATER, H.WATER]})
        for viewer in (0, None):
            self.assertEqual(public_view(a, viewer), public_view(b, viewer))
        self.assertEqual(owned_card_ids(a, 0), owned_card_ids(b, 0))
        return a, b

    def responses(self, state):
        host = host_of(state)
        out = []
        for actor in (0, 1):
            session = host.session(actor)
            r = session.candidates()
            out.append(without_handles(r))
            for cid in [c["id"] for c in r["candidates"]] + ["c9"]:
                out.append(session.inputs(r["game"], r["revision"], cid))
                for choices in ([], ["o1"], ["o2"], ["o1", "o2"], ["o2", "o1"], ["o1", "o1"], ["o9"], [3], ["o1", "o3"]):
                    out.append(session.check(r["game"], r["revision"], cid, choices))
                out.append(dataclasses.asdict(session.submit("other", r["revision"], cid, ["o1"])))
        return out

    def test_twins_get_the_same_answers(self):
        a, b = self.twins()
        self.assertEqual(self.responses(a), self.responses(b))
        self.assertIn("なかまをよぶ", [o["name_ja"] for o in attack_stages(a)[1][0]["options"]])

    def test_bench_full_is_not_offered(self):
        full = board({"active": {"card": NIDORAN_F, "energy": [H.GRASS, H.GRASS]}, "bench": [H.RATTATA] * 5})
        self.assertNotIn("なかまをよぶ", [o["name_ja"] for o in attack_stages(full)[1][0]["options"]])


class SessionContractTest(unittest.TestCase):
    def state(self):
        return board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE, H.FIRE]}, "bench": [H.GROWLITHE], "hand": [H.FIRE]})

    def test_queries_change_nothing(self):
        host = host_of(self.state())
        before = snap(host.game.state)
        session = host.session(0)
        for _ in range(2):
            r = session.candidates()
            for c in r["candidates"]:
                session.inputs(r["game"], r["revision"], c["id"])
                for choices in ([], ["o1"], ["o2"], ["o1", "o2"], ["o2", "o1"], ["o1", "o1"], ["o9"], [1]):
                    session.check(r["game"], r["revision"], c["id"], choices)
        self.assertEqual(snap(host.game.state), before)

    def test_invalid_inputs_and_handles(self):
        host = host_of(self.state())
        session, other = host.session(0), host.session(1)
        r, c, _ = inputs_of(session, L.KIND_USE_ATTACK)
        for choices, code in (([], L.CANDIDATE_INPUT_INVALID), (["o9"], L.CANDIDATE_INPUT_INVALID), (["o1", "o1"], L.CANDIDATE_INPUT_INVALID),
                              (["o1", "o2"], L.CANDIDATE_INPUT_INVALID), ([0], L.CANDIDATE_INPUT_INVALID), ("o1", L.CANDIDATE_INPUT_INVALID)):
            with self.subTest(choices=choices):
                self.assertEqual(session.check(r["game"], r["revision"], c["id"], choices)["refusal"]["code"], code)
        self.assertEqual(other.check(r["game"], r["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATES_WRONG_ACTOR)
        self.assertEqual(session.check("other", r["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATES_WRONG_GAME)
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], ["o9"]).refusal.code, L.CANDIDATE_INPUT_INVALID)
        self.assertTrue(session.check(r["game"], r["revision"], c["id"], ["o1"])["valid"])  # 拒否では失効しない
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], ["o1"]).outcome, D.ACCEPTED)
        self.assertEqual(session.check(r["game"], r["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATES_STALE)  # 受理で失効

    def test_no_verifier_values(self):
        host = host_of(self.state())
        session = host.session(0)
        r = session.candidates()
        payload = [r] + [session.inputs(r["game"], r["revision"], c["id"]) for c in r["candidates"]]
        self.assertFalse(set(keys(payload)) & (FORBIDDEN_KEYS - {"operation_id"}))
        self.assertNotIn("seed", json.dumps(payload))

    def test_face_down_active_is_unverified(self):
        state = board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}})
        state.face_down_cards = frozenset({state.players[0].active.card}) if isinstance(state.face_down_cards, frozenset) else {state.players[0].active.card}
        c = L._attack_candidate(state, 0)  # 補助関数だけの確かめ（うらのバトル場は合法な対戦ではマチスの秘策のあとの入れ替えで起こる）
        self.assertEqual((c.public["processability"], c.public["reasons"]), (L.UNVERIFIED, [L.REASON_FACE_DOWN]))
        self.assertEqual([o["name_ja"] for o in c.inputs[0]["options"]], ["ひっかく", "ひのこ"])  # 本人が知る本当のカードの印刷のワザ（エンジンの確かめは呼ばない）


class ClientApiTest(unittest.TestCase):
    def test_attack_through_client_api(self):
        state = board({"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}})
        hub = ClientHub.from_state(state)
        me, spectator = hub.player(0), hub.spectator()
        r = me.handle({**CONTRACT, "type": "candidates"})["response"]
        c = cand(r, L.KIND_USE_ATTACK)
        fields = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        stages = me.handle({**CONTRACT, "type": "inputs", **fields})["response"]["stages"]
        choices = [stages[0]["options"][0]["id"]]
        self.assertTrue(me.handle({**CONTRACT, "type": "check", **fields, "choices": choices})["response"]["valid"])
        bad = me.handle({**CONTRACT, "type": "submit", **fields, "choices": ["o9"]})
        self.assertEqual((bad["outcome"], bad["refusal"]["code"]), (L.REFUSED, L.CANDIDATE_INPUT_INVALID))
        self.assertEqual([hub.take_updates(a) for a in (0, 1, "spectator")], [[], [], []])  # 拒否は更新を作らない
        sent = me.handle({**CONTRACT, "type": "submit", **fields, "choices": choices})
        self.assertEqual((sent["outcome"], sent["refetch_required"]), (D.ACCEPTED, True))
        updates = {a: hub.take_updates(a) for a in (0, 1, "spectator")}
        game, _ = via_direct(state, UseAttack(0, 0))
        self.assertEqual(updates["spectator"][-1]["observation"], observe(game.state, None))
        self.assertEqual(updates[1][-1]["observation"], observe(game.state, 1))
        self.assertEqual(spectator.handle({**CONTRACT, "type": "candidates"})["error"]["code"], "CLIENT_REQUEST_UNKNOWN")

    def test_engine_rejection_through_client_api_is_private(self):
        confused = board({"active": {"card": CHARIZARD, "evolved_from": [H.CHARMANDER, H.CHARMELEON], "energy": [H.FIRE] * 4, "confusion": True}}, turn=7)
        hub = ClientHub.from_state(confused)
        me = hub.player(0)
        r = me.handle({**CONTRACT, "type": "candidates"})["response"]
        c = cand(r, L.KIND_USE_ATTACK)
        sent = me.handle({**CONTRACT, "type": "submit", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o1"]})
        self.assertEqual(sent["outcome"], D.REJECTED)
        self.assertEqual([hub.take_updates(a) for a in (1, "spectator")], [[], []])  # 拒否の存在を相手・観戦者へ知らせない


def play_attack_turn(host, done):
    """番のプレイヤーが U7 だけで エネルギーをつける → 実行できる最初のワザを宣言 → 決定に答える。ワザがなければ番を終える。"""
    session = host.session(host.game.state.current_player)
    r, c, inputs = inputs_of(session, L.KIND_ATTACH_ENERGY)
    if c is not None:
        stages = inputs["stages"]
        option = stages[0]["options"][0]["id"]
        pair = next(p["option"] for p in stages[1]["options_by_choice"][option] if p["eligible"] and
                    next(o for o in stages[1]["options"] if o["id"] == p["option"])["zone"] == "active")
        assert session.submit(r["game"], r["revision"], c["id"], [option, pair]).outcome == D.ACCEPTED
    r, c, inputs = inputs_of(session, L.KIND_USE_ATTACK)
    if c is None:
        r = session.candidates()
        session.submit(r["game"], r["revision"], cand(r, L.KIND_END_TURN)["id"])
        return
    choices = [next(o["id"] for o in inputs["stages"][0]["options"] if o["eligible"])]
    result = session.submit(r["game"], r["revision"], c["id"], choices)
    assert result.outcome == D.ACCEPTED, result
    done.append(L.KIND_USE_ATTACK)
    for _ in range(10):
        if host.game.state.decision is None:
            break
        assert answer_with_u7(host).outcome == D.ACCEPTED
        done.append(L.KIND_ANSWER_DECISION)


class ConnectionTest(unittest.TestCase):
    """new_game からの合法な操作の列（固定の seed・少数の番）: 準備・エネルギー・ワザの宣言・決定への答え・番の移り。同じコマンドを直接送った対戦と同じ状態。"""

    def test_from_new_game_with_three_sets(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                options = {} if conventions is None else {"conventions": conventions}
                start = A.start_game(CONNECT_DECK, CONNECT_DECK, 0, **options)
                recording = Recording(start.state.clone())
                host = L.ActionHost(recording)
                setup_with_u7(host)
                done, turns = [], []
                for _ in range(4):
                    state = host.game.state
                    if state.phase is not Phase.MAIN:
                        break
                    turns.append(state.current_player)
                    play_attack_turn(host, done)
                self.assertIn(L.KIND_USE_ATTACK, done)
                self.assertEqual(turns[:2], [0, 1])  # 番が移った
                direct = A.HostedGame(start.state.clone())
                for command, submitter in recording.sent:
                    self.assertEqual(direct.submit(command, submitter=submitter).outcome, D.ACCEPTED, command)
                self.assertEqual(snap(direct.state), snap(host.game.state))
                self.assertTrue(any(isinstance(command, UseAttack) for command, _ in recording.sent))


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = (ROOT / "docs" / "legal-actions-u7-4.md").read_text(encoding="utf-8")
        for phrase in ("UseAttack", "attack_index", "stadium_coin", "attack_power", "with_powers", "check_use_attack", "options_by_choice", "preflight_not_evaluated",
                       "may_stop_later", "unverified", "partial", "kyuura-client-api", "HC1"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()

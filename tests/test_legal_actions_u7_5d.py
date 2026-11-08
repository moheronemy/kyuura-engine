"""v0.170（U7-5d。docs/legal-actions-u7-5d.md）: 場のスタジアム（UseStadium）の候補・入力・検査・送信の回帰テスト。

確かめの種類を分ける:

- コードの上の網羅（補助関数の確かめ）: 登録したすべてのスタジアムの型で、使ってよい効果（activated）・選ばせるもの（energy_choice）が check_activation と食い違わない。
  使ってよい効果のないスタジアムは候補がなく、エンジンも受け付けない。check_use_stadium とコマンドの処理の拒否の一致
- 構築盤面（tests.helpers.build_test_state。手札から PlayTrainer でスタジアムを出す。コインはテストの乱数の仕込み with_coin_results）: 代表のスタジアムの候補・入力・
  処理可能性・使う主体・回数・コインの両面・受理のあとの決定・取っ手・不正な入力・状態の不変・キョウの忍者ジムの双子（v0.146 の盤面）
- new_game からの合法な操作の列（固定の seed。3 つの規約集合）: 準備を U7 で終え、ラッキースタジアムを U7 の play_trainer で場に出し、U7 の use_stadium で使う。直接の列と
  同じ状態。完全な再現用記録の収集・U4 の再実行・閲覧用記録の構造。キョウの忍者ジムの v0.146 の列（seed 1・17。双子ではなく、別の対戦による合法な到達例）

停止コードの文字列はテストの中に書かない（区分・ホストの段のコード・エンジンの例外の型で確かめる）。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import effects as E
from kyuura_engine import legal_actions as L
from kyuura_engine.cards import load_card_pool
from kyuura_engine.client_api import ClientHub
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import EndTurn, PlayTrainer, ResolveDecision, UseStadium
from kyuura_engine.engine import apply_command, check_use_stadium
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe, visible_log
from kyuura_engine.stadiums import stadium_in_play
from kyuura_engine.view_record import FORBIDDEN_KEYS
from tests import helpers as H
from tests import test_ninja_gym_oracle_v0_146 as N
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
from tests.test_legal_actions_u7_5c import answer_u7, play_with_u7, uid, via_direct

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = {"contract": "kyuura-client-api", "format": 1}
HD, TL = CoinSide.HEADS, CoinSide.TAILS


def placed(stadium, *, owner=0, active=None, bench=(H.RATTATA,), discard=(), them_active=None, deck=None):
    """``owner`` が手札から ``stadium`` を出したあと、プレイヤー 0 の番（5 番）。``owner`` が 1 なら、1 の番（4 番）に出して番を終えた盤面。"""
    me = {"active": active or {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": list(bench), "hand": [stadium] if owner == 0 else [H.FIRE],
          "deck": list(deck or [H.FIRE] * 8), "prizes": [H.FIRE] * 2, "discard": list(discard)}
    them = {"active": them_active or {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": [H.RATTATA], "hand": [stadium] if owner == 1 else [H.WATER],
            "deck": [H.FIRE] * 8}
    state = H.build_test_state([me, them], turn_number=5 if owner == 0 else 4, current_player=owner)
    state = apply_command(state, PlayTrainer(owner, uid(state, stadium, owner)))
    if owner == 1:
        state = apply_command(state, EndTurn(1))
        while state.decision is not None:  # ポケモンチェックのあとの決定はない盤面（念のため、下限の数で答える）
            d = state.decision
            state = apply_command(state, ResolveDecision(d.player, d.id, d.options[:d.min_choices]))
    assert state.stadium is not None and state.current_player == 0 and state.decision is None
    return state


def stadium_cand(state, actor=0):
    host = host_of(state)
    r = host.session(actor).candidates()
    return host, r, cand(r, L.KIND_USE_STADIUM)


def send_u7(state, choices, *, actor=0):
    host = host_of(state.clone())
    session = host.session(actor)
    r, c, inputs = inputs_of(session, L.KIND_USE_STADIUM)
    picked = [] if not choices else [next(o["id"] for o in inputs["stages"][0]["options"] if o["card"] == choices[0])]
    return host, session.submit(r["game"], r["revision"], c["id"], picked)


class Same:
    def assert_same_as_direct(self, state, energy=None):
        host, result = send_u7(state, [] if energy is None else [energy])
        game, direct = via_direct(state, UseStadium(0, energy))
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual(snap(host.game.state), snap(game.state))
        return host, game, result


def registered_stadiums():
    """登録したスタジアムの型ごとに 1 枚（カード id の並びの最初）。"""
    out = {}
    for cid, definition in sorted(load_card_pool().definitions.items()):
        effect = E.DEFAULT_EFFECTS.trainer_effect(definition) if definition.category == "trainer" else None
        if effect is not None and effect.is_stadium:
            out.setdefault(type(effect), cid)
    return out


class CodeCoverageTest(unittest.TestCase):
    """コードの上の網羅（補助関数の確かめ）: すべての登録スタジアムの型。"""

    def test_activated_and_energy_choice_match_check_activation(self):
        spec = json.loads((ROOT / "docs" / "legal-actions-u7-5-design.json").read_text(encoding="utf-8"))
        shapes = spec["stadium_shapes"]
        types = registered_stadiums()
        self.assertEqual(len(types), 24)  # 使ってよい効果のある 8・常時の効果だけの 16
        for cls in types:
            overrides = "check_activation" in vars(cls) or any("check_activation" in vars(b) for b in cls.__mro__[1:] if b is not E.StadiumEffect and issubclass(b, E.StadiumEffect))
            self.assertEqual(cls.activated, overrides, cls.__name__)  # 使ってよい効果の登録と、確かめの実装が対応する
            if cls.activated:
                expected = "E(attached, own)" if cls.energy_choice == E.ENERGY_CHOICE_OWN_ATTACHED else "none"
                self.assertIn(cls.__name__, shapes[expected], cls.__name__)  # 設計の選ばせるものの形の表と同じ
            else:
                self.assertIsNone(cls.energy_choice, cls.__name__)

    def test_declared_choice_is_checked_first(self):
        """宣言どおり: 選ばせる効果は energy なしで STADIUM_CHOICE_REQUIRED、選ばせない効果は energy ありで STADIUM_CHOICE_NOT_USED（どれも check_activation の最初の確かめ）。"""
        for cls, cid in registered_stadiums().items():
            if not cls.activated:
                continue
            with self.subTest(stadium=cls.__name__):
                state = placed(cid)
                energy = state.players[0].active.energy[0]
                cmd = UseStadium(0) if cls.energy_choice else UseStadium(0, energy)
                with self.assertRaises(IllegalActionError) as caught:
                    check_use_stadium(state, cmd)
                self.assertEqual(caught.exception.code, "STADIUM_CHOICE_REQUIRED" if cls.energy_choice else "STADIUM_CHOICE_NOT_USED")

    def test_constant_only_stadiums_have_no_candidate(self):
        """常時の効果だけのスタジアム（16 の型）:use_stadium の候補はなく、エンジンも受け付けない（ゲーム上できない）。"""
        count = 0
        for cls, cid in registered_stadiums().items():
            if cls.activated:
                continue
            count += 1
            with self.subTest(stadium=cls.__name__):
                state = placed(cid)
                self.assertIsNone(stadium_cand(state)[2])
                with self.assertRaises(IllegalActionError):
                    apply_command(state, UseStadium(0))
        self.assertEqual(count, 16)

    def test_check_function_matches_command(self):
        """check_use_stadium がコマンドの処理と同じ拒否（型・コード）になる。"""
        states = [placed(cid) for cls, cid in registered_stadiums().items() if cls.activated] + [H.build_test_state([{"active": H.CHARMANDER}, {"active": H.CHARMANDER}], turn_number=3)]
        for state in states:
            for actor in (0, 1):
                for energy in [None, *[u for side in state.players for q in side.in_play() for u in q.energy], 999]:
                    cmd = UseStadium(actor, energy)
                    expected = found = None
                    try:
                        check_use_stadium(state, cmd)
                    except (IllegalActionError, UnsupportedError) as error:
                        expected = (type(error), error.code)
                    try:
                        apply_command(H.with_coin_results(state, TL), cmd)
                    except (IllegalActionError, UnsupportedError) as error:
                        found = (type(error), error.code)
                    self.assertEqual(found, expected, cmd)


class MappingTest(unittest.TestCase):
    def test_kind_fields_and_coverage(self):
        self.assertEqual([f.name for f in dataclasses.fields(UseStadium)], ["player", "energy"])  # player は主体、energy だけが宣言の入力（選ばせる効果だけ）
        self.assertIn(L.KIND_USE_STADIUM, L.IMPLEMENTED_KINDS)
        host, r, c = stadium_cand(placed(H.LUCKY_STADIUM))
        cov = r["coverage"]
        self.assertEqual((cov["completeness"], cov["scope_kinds"]), (L.PARTIAL, list(L.MAIN_KINDS)))
        self.assertEqual(cov["not_covered_kinds"], ["check_face_up_deck"])  # v0.171（U7-5e）: use_power は対応した種類
        kinds = [x["kind"] for x in r["candidates"]]
        self.assertEqual(kinds, sorted(kinds, key=L.MAIN_KINDS.index))
        self.assertEqual((c["processability"], c["input_disclosure"], c["input_stages"], c["choices_format"]), (L.MAY_STOP_LATER, L.DISCLOSURE_NONE, [], "[]"))
        self.assertEqual(c["stadium"], {"card": host.game.state.stadium.card, "card_id": H.LUCKY_STADIUM, "owner": 0})
        self.assertIn("supported にしない", c["guarantees"]["supported_scope"])

    def test_no_stadium_and_not_the_turn(self):
        state = H.build_test_state([{"active": H.CHARMANDER, "hand": [H.FIRE]}, {"active": H.CHARMANDER}], turn_number=3)
        self.assertIsNone(stadium_cand(state)[2])
        with self.assertRaises(IllegalActionError):
            apply_command(state, UseStadium(0))
        r = host_of(placed(H.LUCKY_STADIUM)).session(1).candidates()
        self.assertEqual((r["situation"], r["candidates"]), (L.WAITING_FOR_PLAYER, []))  # 持ち主でも、番でなければ使えない

    def test_opponent_stadium_used_by_turn_player(self):
        state = placed(H.LUCKY_STADIUM, owner=1)
        _host, _r, c = stadium_cand(state)
        self.assertEqual(c["stadium"]["owner"], 1)  # 場のスタジアムの持ち主（1）と、使うプレイヤー（番のプレイヤー 0）は別
        host, result = send_u7(H.with_coin_results(state, HD), [])
        self.assertEqual(result.outcome, D.ACCEPTED)
        self.assertIn((0, state.stadium.card), host.game.state.stadium_uses_this_turn)  # 回数は使ったプレイヤーとカードの組


class CountAndCoinTest(Same, unittest.TestCase):
    def test_once_per_turn_and_coin_sides(self):
        for coin in (HD, TL):
            with self.subTest(coin=coin):
                state = H.with_coin_results(placed(H.LUCKY_STADIUM), coin)
                host, _game, result = self.assert_same_as_direct(state)
                self.assertEqual(result.outcome, D.ACCEPTED)
                self.assertEqual(len(host.game.state.players[0].hand), len(state.players[0].hand) + (1 if coin is HD else 0))  # 「うら」でも使ったことになる
                self.assertIsNone(stadium_cand(host.game.state)[2])  # 同じ番の 2 回目はゲーム上できない（候補を作らない）

    def test_unstated_count_second_use_is_unresolved(self):
        state = H.with_coin_results(placed(H.LUCKY_STADIUM_027), TL)
        host, _ = send_u7(state, [])
        _h, _r, c = stadium_cand(host.game.state)
        self.assertEqual(c["processability"], L.RULING_UNRESOLVED)  # 回数の書かれていない版の同じ番の再使用（LK1）: 示して、実行できない
        session = host.session(0)
        r = session.candidates()
        self.assertEqual(session.check(r["game"], r["revision"], cand(r, L.KIND_USE_STADIUM)["id"], [])["refusal"]["code"], L.CANDIDATE_NOT_EXECUTABLE)

    def test_next_turn_other_player_can_use(self):
        state = H.with_coin_results(placed(H.LUCKY_STADIUM), TL)
        host, _ = send_u7(state, [])
        after = apply_command(host.game.state, EndTurn(0))
        while after.decision is not None:
            d = after.decision
            after = apply_command(after, ResolveDecision(d.player, d.id, d.options[:d.min_choices]))
        self.assertEqual(after.current_player, 1)
        self.assertIsNotNone(stadium_cand(after, 1)[2])

    def test_decision_after_coin(self):
        state = H.with_coin_results(placed(H.ENERGY_STADIUM, discard=[H.FIRE, H.WATER]), HD)
        host, game, _ = self.assert_same_as_direct(state)
        d = game.state.decision
        self.assertEqual(d.player, 0)  # 「おもて」: トラッシュの基本エネルギーを選ぶ決定（受理のあと。answer_decision で答える）
        sent = answer_u7(host, lambda stage: [stage["options"][0]["id"]])
        direct = game.submit(ResolveDecision(0, d.id, (d.options[0],)), submitter=0)
        self.assertEqual((sent.outcome, direct.outcome), (D.ACCEPTED, D.ACCEPTED))
        self.assertEqual(snap(host.game.state), snap(game.state))

    def test_fuchsia_pokemon_decision_and_promote(self):
        koga = {"card": H.KOGAS_KOFFING, "energy": [H.GRASS]}
        state = H.with_coin_results(placed(H.FUCHSIA_CITY_GYM, active=koga, bench=(H.RATTATA,)), HD)
        host, game, _ = self.assert_same_as_direct(state)
        d = game.state.decision
        sent = answer_u7(host, lambda stage: [stage["options"][0]["id"]])  # バトル場のキョウのドガースを山札にもどす → 空いたバトル場に出す決定
        self.assertEqual((sent.outcome, game.submit(ResolveDecision(0, d.id, (d.options[0],)), submitter=0).outcome), (D.ACCEPTED, D.ACCEPTED))
        self.assertEqual(snap(host.game.state), snap(game.state))
        self.assertIsNotNone(host.game.state.decision)


class EnergyChoiceTest(Same, unittest.TestCase):
    def test_celadon_offers_only_energy_on_erikas_pokemon(self):
        state = placed(H.CELADON_CITY_GYM, active={"card": H.ERIKAS_BELLSPROUT, "energy": [H.GRASS, H.DOUBLE_COLORLESS_ENERGY], "poison": 10},
                       bench=({"card": H.RATTATA, "energy": [H.GRASS]},))
        host = host_of(state)
        _r, c, inputs = inputs_of(host.session(0), L.KIND_USE_STADIUM)
        stage = inputs["stages"][0]
        self.assertEqual((stage["role"], stage["meaning"], stage["count"], c["input_disclosure"]), ("energy", "card", {"min": 1, "max": 1}, L.DISCLOSURE_CONFIRMED))
        active = state.players[0].active
        self.assertEqual([o["card"] for o in stage["options"]], list(active.energy))  # コラッタのエネルギーは選べない（「エリカのポケモン」でない）。特殊エネルギーは選べる
        self.assertEqual({o["holder"]["pokemon"] for o in stage["options"]}, {active.pokemon_id})
        host2, _game, result = self.assert_same_as_direct(state, active.energy[1])
        self.assertEqual(result.outcome, D.ACCEPTED)
        self.assertFalse(host2.game.state.players[0].active.conditions.names())

    def test_celadon_without_condition_is_unresolved(self):
        state = placed(H.CELADON_CITY_GYM, active={"card": H.ERIKAS_BELLSPROUT, "energy": [H.GRASS]})
        _h, _r, c = stadium_cand(state)
        self.assertEqual(c["processability"], L.RULING_UNRESOLVED)

    def test_saffron_basic_only_and_invalid_inputs(self):
        state = placed(H.SAFFRON_CITY_GYM, active={"card": H.SABRINAS_ABRA, "energy": [H.PSYCHIC, H.DOUBLE_COLORLESS_ENERGY]})
        host = host_of(state)
        session = host.session(0)
        r, c, inputs = inputs_of(session, L.KIND_USE_STADIUM)
        self.assertEqual([o["card"] for o in inputs["stages"][0]["options"]], [state.players[0].active.energy[0]])  # 特殊エネルギーは選べない（基本エネルギーだけ）
        for choices in ([], ["o9"], ["o1", "o1"], [state.players[0].active.energy[1]], None):
            self.assertEqual(session.check(r["game"], r["revision"], c["id"], choices)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID, choices)
        _h, _g, result = self.assert_same_as_direct(state, state.players[0].active.energy[0])
        self.assertEqual(result.outcome, D.ACCEPTED)

    def test_no_target_energy_means_no_candidate(self):
        state = placed(H.SAFFRON_CITY_GYM, active={"card": H.SABRINAS_ABRA, "energy": [H.DOUBLE_COLORLESS_ENERGY]})
        self.assertIsNone(stadium_cand(state)[2])


class NinjaGymTest(unittest.TestCase):
    """キョウの忍者ジム（持ち主の知識の下限。v0.146）: 山札とサイドの配分だけを変えた双子で、候補・入力・件数・並び・理由・不正な入力への応答が同じ。"""

    def responses(self, state):
        host = host_of(state)
        session = host.session(0)
        r = session.candidates()
        out = [without_handles(r)]
        for c in r["candidates"]:
            out.append(session.inputs(r["game"], r["revision"], c["id"]))
            for choices in ([], ["o1"], [1]):
                out.append(session.check(r["game"], r["revision"], c["id"], choices))
        return out + [observe(state, 1), observe(state, None), visible_log(state, 1), visible_log(state, None), observe(state, 0)]

    def test_twins_constructed(self):
        for koga in (1, 7):  # 1 枚: 下限 0 で NJ1（保守的な停止）。7 枚: 下限 1 で使える
            with self.subTest(koga=koga):
                state = N.board(koga)
                twin = N.swap_hidden(state, H.KOGAS_KOFFING)
                self.assertEqual(self.responses(state), self.responses(twin))
                c = stadium_cand(state)[2]
                self.assertEqual(c["processability"], L.RULING_UNRESOLVED if koga == 1 else L.MAY_STOP_LATER)

    def test_legal_reach_examples_from_new_game(self):
        """v0.146 の合法な列（seed 1 はキョウのドガースが山札、seed 17 はサイド。直接のコマンドで準備を終える）。2 つは別の対戦で、手札・場が違う（本人の知識と公開の情報が一致する双子ではない）。
        別の対戦による合法な到達例として、use_stadium の候補（番号を除く）・入力・入力の検査の応答が同じ
        （ほかの手札は seed で違うので、候補の全体は比べない）。"""

        def stadium_part(state):
            session = host_of(state).session(0)
            r = session.candidates()
            c = cand(r, L.KIND_USE_STADIUM)
            checks = [session.check(r["game"], r["revision"], c["id"], choices) for choices in ([], ["o1"], [1])]
            return {k: v for k, v in c.items() if k not in ("id", "stadium")}, session.inputs(r["game"], r["revision"], c["id"])["stages"], checks

        a, b = N.legal_first_turn(1), N.legal_first_turn(17)
        self.assertEqual(stadium_part(a), stadium_part(b))
        self.assertEqual(stadium_cand(a)[2]["processability"], L.RULING_UNRESOLVED)

    def test_heads_uses_the_real_deck_after_search_starts(self):
        state = H.with_coin_results(N.board(7), HD)
        host, result = send_u7(state, [])
        self.assertEqual(result.outcome, D.ACCEPTED)
        d = host.game.state.decision
        self.assertTrue(set(d.options) <= set(host.game.state.players[0].deck))  # 正当に検索が始まったあとは、実際の山札から選ぶ
        self.assertEqual(answer_u7(host, lambda stage: [stage["options"][0]["id"]] if stage["count"]["min"] else []).outcome, D.ACCEPTED)


class SessionContractTest(unittest.TestCase):
    STATES = (lambda: placed(H.LUCKY_STADIUM), lambda: placed(H.SAFFRON_CITY_GYM, active={"card": H.SABRINAS_ABRA, "energy": [H.PSYCHIC]}), lambda: N.board(1))

    def test_queries_change_nothing(self):
        for make in self.STATES:
            host = host_of(make())
            before = snap(host.game.state)
            session = host.session(0)
            for _ in range(2):
                r = session.candidates()
                for c in r["candidates"]:
                    session.inputs(r["game"], r["revision"], c["id"])
                    for choices in ([], ["o1"], ["o2"], ["o1", "o1"], ["o9"], [1]):
                        session.check(r["game"], r["revision"], c["id"], choices)
            self.assertEqual(snap(host.game.state), before)

    def test_invalid_inputs_and_handles(self):
        host = host_of(H.with_coin_results(placed(H.LUCKY_STADIUM), TL))
        session, other = host.session(0), host.session(1)
        r = session.candidates()
        c = cand(r, L.KIND_USE_STADIUM)
        for choices in (["o1"], [0], "o1", None):
            self.assertEqual(session.check(r["game"], r["revision"], c["id"], choices)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID, choices)
        self.assertEqual(other.check(r["game"], r["revision"], c["id"], [])["refusal"]["code"], L.CANDIDATES_WRONG_ACTOR)
        self.assertEqual(session.check("other", r["revision"], c["id"], [])["refusal"]["code"], L.CANDIDATES_WRONG_GAME)
        r1 = other.candidates()
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], ["o1"]).refusal.code, L.CANDIDATE_INPUT_INVALID)
        self.assertEqual(other.check(r1["game"], r1["revision"], "c1", [])["refusal"]["code"], L.CANDIDATE_UNKNOWN)  # 拒否では相手の取っ手を失効させない
        self.assertTrue(session.check(r["game"], r["revision"], c["id"], [])["valid"])
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], []).outcome, D.ACCEPTED)
        self.assertEqual(session.check(r["game"], r["revision"], c["id"], [])["refusal"]["code"], L.CANDIDATES_STALE)  # 受理で失効

    def test_no_verifier_values(self):
        for make in self.STATES:
            session = host_of(make()).session(0)
            r = session.candidates()
            payload = [r] + [session.inputs(r["game"], r["revision"], c["id"]) for c in r["candidates"]]
            self.assertFalse(set(keys(payload)) & (FORBIDDEN_KEYS - {"operation_id"}))
            self.assertNotIn("seed", json.dumps(payload))


class ClientApiTest(unittest.TestCase):
    def test_stadium_through_client_api(self):
        state = H.with_coin_results(placed(H.SAFFRON_CITY_GYM, active={"card": H.SABRINAS_ABRA, "energy": [H.PSYCHIC]}), HD)
        energy = state.players[0].active.energy[0]
        hub = ClientHub.from_state(state.clone())
        me = hub.player(0)
        self.assertFalse(hub.spectator().handle({**CONTRACT, "type": "candidates"}).get("ok", False))  # 観戦者には候補の入口がない
        r = me.handle({**CONTRACT, "type": "candidates"})["response"]
        c = cand(r, L.KIND_USE_STADIUM)
        fields = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        stage = me.handle({**CONTRACT, "type": "inputs", **fields})["response"]["stages"][0]
        choices = [next(o["id"] for o in stage["options"] if o["card"] == energy)]
        self.assertTrue(me.handle({**CONTRACT, "type": "check", **fields, "choices": choices})["response"]["valid"])
        bad = me.handle({**CONTRACT, "type": "submit", **fields, "choices": ["o9"]})
        self.assertEqual((bad["outcome"], bad["refusal"]["code"]), (L.REFUSED, L.CANDIDATE_INPUT_INVALID))
        self.assertEqual([hub.take_updates(a) for a in (1, "spectator")], [[], []])  # 断りは相手・観戦者へ知らせない
        sent = me.handle({**CONTRACT, "type": "submit", **fields, "choices": choices})
        self.assertEqual((sent["outcome"], sent["refetch_required"]), (D.ACCEPTED, True))
        game, _ = via_direct(state, UseStadium(0, energy))
        updates = {a: hub.take_updates(a) for a in (1, "spectator")}
        self.assertEqual(updates["spectator"][-1]["observation"], observe(game.state, None))
        self.assertEqual(updates[1][-1]["observation"], observe(game.state, 1))
        self.assertNotIn("Traceback", json.dumps(sent, ensure_ascii=False))


def _lucky_deck():
    deck = list(CONNECT_DECK)
    for _ in range(4):
        deck.remove(H.FIRE)
    return deck + [H.LUCKY_STADIUM] * 4


LUCKY_DECK = _lucky_deck()  # U7-3 の接続のデッキの炎エネルギー 4 枚をラッキースタジアムにした（60 枚）
LUCKY_SEED = 1  # 事前に固定した seed: 準備を U7 で終えた先攻（0）の最初の番の手札にラッキースタジアムがある（3 つの規約集合で同じ）


class ConnectionTest(unittest.TestCase):
    """new_game からの合法な操作の列: 準備を U7 で終え、ラッキースタジアムを U7 の play_trainer で場に出し、U7 の use_stadium で使い、番を終える。直接の列と同じ状態。"""

    def test_play_then_use_from_new_game(self):
        from kyuura_engine import replay_run, view_record
        from kyuura_engine.replay_record import ReplayCollector

        self.assertEqual(len(LUCKY_DECK), 60)
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                options = {} if conventions is None else {"conventions": conventions}
                start = A.start_game(LUCKY_DECK, CONNECT_DECK, LUCKY_SEED, **options)
                recording = Recording(start.state.clone())
                host = L.ActionHost(recording)
                setup_with_u7(host)
                lucky = uid(host.game.state, H.LUCKY_STADIUM)
                self.assertEqual(play_with_u7(host, lucky).outcome, D.ACCEPTED)
                self.assertEqual(stadium_in_play(host.game.state)[0].card, lucky)
                session = host.session(0)
                r = session.candidates()
                self.assertEqual(session.submit(r["game"], r["revision"], cand(r, L.KIND_USE_STADIUM)["id"], []).outcome, D.ACCEPTED)
                self.assertIn((0, lucky), host.game.state.stadium_uses_this_turn)
                r = session.candidates()
                self.assertIsNone(cand(r, L.KIND_USE_STADIUM))
                self.assertEqual(session.submit(r["game"], r["revision"], cand(r, L.KIND_END_TURN)["id"], []).outcome, D.ACCEPTED)
                direct = A.HostedGame(start.state.clone())
                for command, submitter in recording.sent:
                    self.assertEqual(direct.submit(command, submitter=submitter).outcome, D.ACCEPTED, command)
                self.assertEqual(snap(direct.state), snap(host.game.state))
                self.assertTrue(any(isinstance(command, UseStadium) for command, _ in recording.sent))
                collector, _ = ReplayCollector.start(LUCKY_DECK, CONNECT_DECK, LUCKY_SEED, include_git=False, **options)
                for command, submitter in recording.sent:
                    self.assertEqual(collector.submit(command, submitter=submitter).outcome, D.ACCEPTED, command)
                record = collector.close()
                report = replay_run.replay(record)
                self.assertEqual(report.status, replay_run.SUCCEEDED, report.mismatch)
                view_report, views = view_record.view_records_from_replay(record)
                self.assertEqual(view_report.status, replay_run.SUCCEEDED)
                for viewer, rec in views.items():
                    self.assertEqual(view_record.validate_view_record(rec).problems, (), viewer)


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = (ROOT / "docs" / "legal-actions-u7-5d.md").read_text(encoding="utf-8")
        for phrase in ("UseStadium", "check_use_stadium", "use_stadium", "energy_choice", "activated", "may_stop_later", "partial", "kyuura-client-api", "NJ1",
                       "play_trainer", "R-1", "R-2", "U7-5e", "3649946"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()

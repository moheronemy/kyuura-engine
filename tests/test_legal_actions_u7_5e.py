"""v0.171（U7-5e。docs/legal-actions-u7-5e.md）: 宣言する特殊能力（UsePokemonPower）の候補・型ごとの宣言の入力・依存する段・検査・送信の回帰テスト。

確かめの種類を分ける:

- コードの上の網羅（補助関数の確かめ）: 型ごとの宣言（effects.POWER_INPUT_STAGES）が登録の UsePokemonPower で使う 56 の型と同じで、設計の入力の形の表（power_shapes）と同じ。
  宣言の項目が check_usable の読む項目と同じ。依存する段の形の確かめ（stage_dependency_problems）が、壊した段を見つける
- 構築盤面（tests.helpers.build_test_state。コインはテストの乱数の仕込み with_coin_results）: 入力なし・1 段・2 段・3 段、上流を変えた古い下流の入力の拒否、使う主体、回数、
  特殊状態、消す効果、写した特殊能力、コインと受理のあとの決定、相手のうらのカードの双子（本当のカードだけが違う）、取っ手、不正な入力、状態の不変、client_api
- new_game からの合法な操作の列（固定の seed。3 つの規約集合）: 準備を U7 で終え、エネルギーをつけ、特殊能力を U7 で使う。直接の列と同じ状態、完全な再現用記録の収集・U4 の再実行・
  閲覧用記録の構造

停止コードの文字列はテストの中に書かない（区分・ホストの段のコード・エンジンの例外の型で確かめる）。
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import pathlib
import textwrap
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import effects as E
from kyuura_engine import legal_actions as L
from kyuura_engine.cards import load_card_pool
from kyuura_engine.client_api import ClientHub
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import (
    EndTurn,
    PlayTrainer,
    ResolveDecision,
    UsePokemonPower,
)
from kyuura_engine.engine import apply_command, check_use_pokemon_power
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe, visible_log
from kyuura_engine.view_record import FORBIDDEN_KEYS
from tests import helpers as H
from tests.test_legal_actions_u7_1 import keys, snap, without_handles
from tests.test_legal_actions_u7_3 import (
    SETS,
    Recording,
    cand,
    host_of,
    inputs_of,
    setup_with_u7,
)
from tests.test_legal_actions_u7_5c import answer_u7, uid, via_direct

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = {"contract": "kyuura-client-api", "format": 1}
HD, TL = CoinSide.HEADS, CoinSide.TAILS
POOL = load_card_pool()
ODDISH = next(cid for cid, d in sorted(POOL.definitions.items()) if d.name_ja == "ナゾノクサ" and cid.startswith("PMCG2"))  # ラフレシアの進化元（第2弾）
IGGLYBUFF = "neo2-050"  # ププリン（ベイビィ。［じっとみる］: 相手のベンチのポケモン 1 匹）


def mon(card, energy=(), **extra):
    return {"card": card, "energy": list(energy), **extra}


def board(active, bench=(), *, hand=(), them=None, turn=5):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": [H.FIRE] * 8, "prizes": [H.FIRE] * 2}
    them = them or {"active": mon(H.CHARMANDER, (H.FIRE,)), "bench": [H.RATTATA], "hand": [H.WATER], "deck": [H.FIRE] * 8}
    return H.build_test_state([me, them], turn_number=turn)


def venusaur_board(**kw):
    """フシギバナ（エナジートランス: 自分の場の「草」エネルギー → 別の自分の場のポケモン）。ベンチのコラッタに草と炎、ヒトカゲ。"""
    return board(mon(H.VENUSAUR, (H.GRASS, H.GRASS), evolved_from=[H.BULBASAUR, H.IVYSAUR]), [mon(H.RATTATA, (H.GRASS, H.FIRE)), H.CHARMANDER], **kw)


def power_cand(state, actor=0, name=None):
    host = host_of(state)
    r = host.session(actor).candidates()
    found = [c for c in r["candidates"] if c["kind"] == L.KIND_USE_POWER and (name is None or c["power"]["name_ja"] == name)]
    return host, r, (found[0] if found else None)


def stages_of(state, name=None, actor=0):
    host, r, c = power_cand(state, actor, name)
    return host, r, c, host.session(actor).inputs(r["game"], r["revision"], c["id"])["stages"]


def path_for(stages, *values):
    """段の順の値（場のポケモンの番号・カードの uid）から、依存をたどった選ぶものの番号の並び。"""
    chosen, parent = [], None
    for stage, value in zip(stages, values):
        key = "pokemon" if stage["meaning"] == "pokemon" else "card"
        option = next(o for o in stage["options"] if o[key] == value and o.get("after") == parent)
        chosen.append(option["id"])
        parent = option["id"]
    return chosen


def send_u7(state, values, name=None, actor=0):
    host = host_of(state.clone())
    session = host.session(actor)
    r = session.candidates()
    c = next(c for c in r["candidates"] if c["kind"] == L.KIND_USE_POWER and (name is None or c["power"]["name_ja"] == name))
    stages = session.inputs(r["game"], r["revision"], c["id"])["stages"]
    return host, session.submit(r["game"], r["revision"], c["id"], path_for(stages, *values))


class Same:
    def assert_same_as_direct(self, state, command, values, name=None):
        host, result = send_u7(state, values, name)
        game, direct = via_direct(state, command)
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual(snap(host.game.state), snap(game.state))
        return host, game, result


class DeclarationTest(unittest.TestCase):
    """コードの上の網羅（補助関数の確かめ）。"""

    def test_declarations_cover_command_usable_types(self):
        usable = {type(entry.effect) for entry in E.DEFAULT_EFFECTS._powers.values() if E.power_by_command(entry.effect)}
        self.assertEqual(set(E.POWER_INPUT_STAGES), usable)
        self.assertEqual(len(usable), 56)
        spec = json.loads((ROOT / "docs" / "legal-actions-u7-5-design.json").read_text(encoding="utf-8"))
        shape_of = {"none": (), "S(own)": E._POWER_S, "T(opp bench)": E._POWER_OBT, "E(hand)": E._POWER_EH, "S(own)+T(own)": E._POWER_S_T,
                    "S(opp)+T(opp)": E._POWER_OS_OT, "E(hand)+T(own)": E._POWER_EH_T, "E(attached)+S(own)": E._POWER_E_S, "E(attached)+S(own)+T(own)": E._POWER_E_S_T}
        self.assertEqual(set(shape_of), set(spec["power_shapes"]))
        for shape, names in spec["power_shapes"].items():
            for name in names:
                self.assertEqual(E.POWER_INPUT_STAGES[getattr(E, name)], shape_of[shape], name)  # 設計の 9 通りの表と同じ
        excluded = {getattr(E, name) for name in spec["power_not_by_command"]}
        self.assertEqual(excluded, set(E.POWER_NOT_BY_COMMAND))  # 反応・ワザといっしょに使う力は候補にしない

    def test_declared_fields_match_what_check_usable_reads(self):
        """宣言の項目（energy・source・target）が、check_usable（とそれが呼ぶ self のメソッド）の読む use の項目と同じ（選ばせない型は、読むなら指定を拒否するだけ）。"""
        for cls, decl in E.POWER_INPUT_STAGES.items():
            source = textwrap.dedent(inspect.getsource(cls.check_usable)) if "check_usable" in vars(cls) else ""
            read = {n.attr for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "use"
                    and n.attr in ("energy", "source", "target")} if source else set()
            declared = {field_name for field_name, _ in decl}
            self.assertLessEqual(declared, read, cls.__name__)  # 宣言した項目は確かめが読む
            if read - declared:
                self.assertIn("POWER_CHOICE_NOT_USED", source, cls.__name__)  # 宣言しない項目を読むのは、指定を拒否するためだけ

    def test_dependency_checker_finds_broken_stages(self):
        _h, _r, _c, stages = stages_of(venusaur_board())
        self.assertEqual(L.stage_dependency_problems(stages), [])
        broken = json.loads(json.dumps(stages))
        broken[2]["depends_on_stage"] = 3  # 自分に依存（循環）
        self.assertTrue(L.stage_dependency_problems(broken))
        broken = json.loads(json.dumps(stages))
        broken[2]["options_by_choice"]["o99"] = [{"option": "o98"}]  # 存在しない参照
        self.assertTrue(L.stage_dependency_problems(broken))
        broken = json.loads(json.dumps(stages))
        broken[1]["options"][0]["after"] = "o99"
        self.assertTrue(L.stage_dependency_problems(broken))

    def test_check_function_matches_command(self):
        state = venusaur_board()
        ids = [q.pokemon_id for side in state.players for q in side.in_play()] + [None, 999]
        energies = [u for q in state.players[0].in_play() for u in q.energy] + [None]
        for actor in (0, 1):
            for pid in ids[:3] + [999]:
                for source in ids[:4]:
                    for energy in energies[:3]:
                        for target in ids[:4]:
                            cmd = UsePokemonPower(actor, pid if pid is not None else 999, 0, energy=energy, source=source, target=target)
                            expected = found = None
                            try:
                                check_use_pokemon_power(state, cmd)
                            except (IllegalActionError, UnsupportedError) as error:
                                expected = (type(error), error.code)
                            try:
                                apply_command(state, cmd)
                            except (IllegalActionError, UnsupportedError) as error:
                                found = (type(error), error.code)
                            self.assertEqual(found, expected, cmd)


class ThreeStageTest(Same, unittest.TestCase):
    def test_energy_trans_stages_and_dependency(self):
        state = venusaur_board()
        _h, _r, c, stages = stages_of(state)
        self.assertEqual([s["role"] for s in stages], ["source", "energy", "target"])
        self.assertEqual((c["input_disclosure"], c["power"]["name_ja"], c["processability"]), (L.DISCLOSURE_CONFIRMED, "エナジートランス", L.MAY_STOP_LATER))
        self.assertEqual((stages[1]["depends_on_stage"], stages[1]["upstream_stages"], stages[2]["depends_on_stage"], stages[2]["upstream_stages"]), (1, [1], 2, [1, 2]))
        rattata = state.players[0].bench[0]
        self.assertEqual({o["card"] for o in stages[1]["options"] if o["after"] == path_for(stages, rattata.pokemon_id)[0]}, {rattata.energy[0]})  # 炎は選べない
        targets = {o["pokemon"] for o in stages[2]["options"] if o["after"] == path_for(stages, rattata.pokemon_id, rattata.energy[0])[1]}
        self.assertNotIn(rattata.pokemon_id, targets)  # 別のポケモンにだけ

    def test_mixed_upstream_and_stale_downstream_are_rejected(self):
        state = venusaur_board()
        host = host_of(state)
        session = host.session(0)
        r = session.candidates()
        c = cand(r, L.KIND_USE_POWER)
        stages = session.inputs(r["game"], r["revision"], c["id"])["stages"]
        active, rattata = state.players[0].active, state.players[0].bench[0]
        good = path_for(stages, active.pokemon_id, active.energy[0], rattata.pokemon_id)
        other = path_for(stages, rattata.pokemon_id, rattata.energy[0], active.pokemon_id)
        self.assertTrue(session.check(r["game"], r["revision"], c["id"], good)["valid"])
        for bad in ([other[0], good[1], good[2]],  # 1 段目を変えたのに古い 2・3 段目（ほかの上流の番号を混ぜた）
                    [good[0], good[1], other[2]],  # 3 段目がほかの上流の番号
                    [good[1], good[0], good[2]], good[:2], [*good, good[2]], [good[0], good[0], good[2]], ["o99", good[1], good[2]]):
            self.assertEqual(session.check(r["game"], r["revision"], c["id"], bad)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID, bad)

    def test_same_as_direct(self):
        state = venusaur_board()
        active, rattata = state.players[0].active, state.players[0].bench[0]
        cmd = UsePokemonPower(0, active.pokemon_id, 0, energy=active.energy[0], source=active.pokemon_id, target=rattata.pokemon_id)
        host, _game, result = self.assert_same_as_direct(state, cmd, (active.pokemon_id, active.energy[0], rattata.pokemon_id))
        self.assertEqual(result.outcome, D.ACCEPTED)
        self.assertIn(active.energy[0], host.game.state.players[0].bench[0].energy)

    def test_asleep_user_and_suppression_remove_the_candidate(self):
        asleep = board(mon(H.VENUSAUR, (H.GRASS,), evolved_from=[H.BULBASAUR, H.IVYSAUR], sleep=True), [mon(H.RATTATA, (H.GRASS,))])
        self.assertIsNone(power_cand(asleep)[2])  # ねむり: ゲーム上できない
        with self.assertRaises(IllegalActionError):
            apply_command(asleep, UsePokemonPower(0, asleep.players[0].active.pokemon_id, 0, energy=asleep.players[0].active.energy[0],
                                                  source=asleep.players[0].active.pokemon_id, target=asleep.players[0].bench[0].pokemon_id))
        muk = {"active": mon(H.MUK, (H.GRASS,), evolved_from=H.FOSSIL_GRIMER), "bench": [H.RATTATA], "hand": [], "deck": [H.FIRE] * 8}
        self.assertIsNone(power_cand(venusaur_board(them=muk))[2])  # 相手のかがくへんかガス: 使えず、その力も消える


class TwoAndOneStageTest(Same, unittest.TestCase):
    def test_rain_dance_hand_energy_to_water_pokemon(self):
        state = board(mon(H.BLASTOISE, (H.WATER,), evolved_from=[H.SQUIRTLE, H.WARTORTLE]), [H.SQUIRTLE, H.CHARMANDER], hand=[H.WATER, H.FIRE])
        _h, _r, _c, stages = stages_of(state)
        self.assertEqual([s["role"] for s in stages], ["energy", "target"])
        water = uid(state, H.WATER)
        self.assertEqual([o["card"] for o in stages[0]["options"]], [water])  # 手札の「水」エネルギーだけ（炎は選べない。本人の手札）
        self.assertNotIn(state.players[0].bench[1].pokemon_id, {o["pokemon"] for o in stages[1]["options"]})  # ヒトカゲは「水」ポケモンでない
        squirtle = state.players[0].bench[0].pokemon_id
        cmd = UsePokemonPower(0, state.players[0].active.pokemon_id, 0, energy=water, target=squirtle)
        _host, _game, result = self.assert_same_as_direct(state, cmd, (water, squirtle))
        self.assertEqual(result.outcome, D.ACCEPTED)

    def test_damage_swap_source_target(self):
        state = board(mon(H.ALAKAZAM, (H.PSYCHIC,), evolved_from=[H.ABRA, H.KADABRA]), [mon(H.RATTATA, damage=20), H.CHARMANDER])
        _h, _r, _c, stages = stages_of(state)
        self.assertEqual([s["role"] for s in stages], ["source", "target"])
        self.assertEqual([o["pokemon"] for o in stages[0]["options"]], [state.players[0].bench[0].pokemon_id])  # ダメージのあるポケモンだけ
        src, dst = state.players[0].bench[0].pokemon_id, state.players[0].bench[1].pokemon_id
        cmd = UsePokemonPower(0, state.players[0].active.pokemon_id, 0, source=src, target=dst)
        self.assertEqual(self.assert_same_as_direct(state, cmd, (src, dst))[2].outcome, D.ACCEPTED)

    def test_opponent_field_source_target(self):
        them = {"active": mon(H.CHARMANDER, (H.FIRE,), damage=20), "bench": [H.RATTATA], "hand": [], "deck": [H.FIRE] * 8}
        state = board(mon(H.GENGAR, (H.PSYCHIC,), evolved_from=[H.GASTLY, H.HAUNTER]), them=them)
        _h, _r, _c, stages = stages_of(state)
        self.assertEqual([s["role"] for s in stages], ["source", "target"])
        src, dst = state.players[1].active.pokemon_id, state.players[1].bench[0].pokemon_id
        cmd = UsePokemonPower(0, state.players[0].active.pokemon_id, 0, source=src, target=dst)
        self.assertEqual(self.assert_same_as_direct(state, cmd, (src, dst))[2].outcome, D.ACCEPTED)

    def test_no_input_coin_decision_and_once_per_turn(self):
        state = board(mon(H.VILEPLUME, (H.GRASS,), evolved_from=[ODDISH, H.GLOOM]), [mon(H.RATTATA, damage=20)])
        _h, _r, c = power_cand(state)
        self.assertEqual((c["input_disclosure"], c["input_stages"], c["choices_format"]), (L.DISCLOSURE_NONE, [], "[]"))
        for coin in (HD, TL):
            with self.subTest(coin=coin):
                s = H.with_coin_results(state, coin)
                host, game, result = self.assert_same_as_direct(s, UsePokemonPower(0, s.players[0].active.pokemon_id, 0), ())
                self.assertEqual(result.outcome, D.ACCEPTED)
                if coin is HD:
                    d = game.state.decision
                    self.assertIsNotNone(d)  # 「おもて」: 回復するポケモンを選ぶ決定（受理のあと。answer_decision で答える）
                    self.assertEqual(answer_u7(host, lambda stage: [stage["options"][0]["id"]]).outcome, D.ACCEPTED)
                    self.assertEqual(game.submit(ResolveDecision(0, d.id, (d.options[0],)), submitter=0).outcome, D.ACCEPTED)
                    self.assertEqual(snap(host.game.state), snap(game.state))
                self.assertIsNone(power_cand(host.game.state)[2])  # 自分の番ごとに 1 回（2 回目はゲーム上できない）

    def test_not_the_turn_player(self):
        r = host_of(venusaur_board()).session(1).candidates()
        self.assertEqual((r["situation"], r["candidates"]), (L.WAITING_FOR_PLAYER, []))


class CopyTest(Same, unittest.TestCase):
    def test_ditto_copied_power_route(self):
        """写した特殊能力（メタモンの［へんしん］で相手のフシギバナを写す）: 候補は印刷したカード（相手のバトル場のカード）で特殊能力を指す。エンジンと同じ区分・結果。"""
        them = {"active": mon(H.VENUSAUR, (H.GRASS,), evolved_from=[H.BULBASAUR, H.IVYSAUR], evolved_turn=6), "bench": [], "hand": [], "deck": [H.FIRE] * 8}
        state = board(mon(H.DITTO, (H.GRASS,)), [mon(H.RATTATA)], them=them, turn=7)  # 相手が 2 進化できる番（4・6 番）のあと（構築盤面の整合）
        _h, _r, c = power_cand(state, name="エナジートランス")
        self.assertEqual((c["power"]["card"], c["power"]["card_id"], c["processability"]), (state.players[1].active.card, H.VENUSAUR, L.MAY_STOP_LATER))
        active, rattata = state.players[0].active, state.players[0].bench[0]
        cmd = UsePokemonPower(0, active.pokemon_id, 0, energy=active.energy[0], source=active.pokemon_id, target=rattata.pokemon_id, card=state.players[1].active.card)
        check_use_pokemon_power(state, cmd)  # エンジンも同じ組を受け付ける前の確かめで通す
        _host, _game, result = self.assert_same_as_direct(state, cmd, (active.pokemon_id, active.energy[0], rattata.pokemon_id), name="エナジートランス")
        self.assertEqual(result.outcome, D.ACCEPTED)

    def test_shapeshift_power_has_no_declaration_input(self):
        from tests import test_virtual_attacks_transformation_v0_49 as V
        state = V.ninetales_board()
        _h, _r, c = power_cand(state, name="ばける")
        self.assertEqual((c["input_stages"], c["choices_format"]), ([], "[]"))  # のせるカードは受理のあとの決定


def opponent_face_down(real):
    """相手（1）が自分の番にマチスの秘策で ``real`` をうらにしてベンチに出し、番を終えた盤面（プレイヤー 0 の番）。"""
    me = {"active": mon(H.VENOMOTH, (H.GRASS,), evolved_from=H.VENONAT), "bench": [mon(IGGLYBUFF)], "hand": [], "deck": [H.FIRE] * 8, "prizes": [H.FIRE] * 2}
    them = {"active": mon(H.HITMONCHAN, (H.FIGHTING,)), "bench": [H.RATTATA], "hand": [H.LT_SURGES_SECRET_PLAN, real], "deck": [H.FIRE] * 8}
    state = H.build_test_state([me, them], turn_number=4, current_player=1)
    state = apply_command(state, PlayTrainer(1, uid(state, H.LT_SURGES_SECRET_PLAN, 1)))
    state = apply_command(state, ResolveDecision(1, state.decision.id, (uid(state, real, 1),)))
    state = apply_command(state, EndTurn(1))
    while state.decision is not None:
        d = state.decision
        state = apply_command(state, ResolveDecision(d.player, d.id, d.options[:d.min_choices]))
    assert state.current_player == 0 and state.face_down_cards
    return state


class FaceDownTwinTest(unittest.TestCase):
    """相手のうらのカード（本当のカードだけが違う双子）: 本人の候補・入力・件数・並び・制約・理由・不正な入力への応答が同じ。公開された位置だけを示す（F-4・D-U75-POWER-FACE-DOWN）。"""

    def responses(self, state):
        host = host_of(state)
        session = host.session(0)
        r = session.candidates()
        out = [without_handles(r)]
        for c in r["candidates"]:
            out.append(session.inputs(r["game"], r["revision"], c["id"]))
            for choices in ([], ["o1"], ["o2"], ["o1", "o2"], ["o9"], [1]):
                out.append(session.check(r["game"], r["revision"], c["id"], choices))
        return out + [observe(state, 0), observe(state, None), visible_log(state, 0), visible_log(state, None)]

    def test_twins(self):
        a, b = opponent_face_down(H.DIGLETT), opponent_face_down(H.KADABRA)
        self.assertEqual(self.responses(a), self.responses(b))

    def test_face_down_target_is_unverified_and_hides_identity(self):
        state = opponent_face_down(H.DIGLETT)
        fd = next(q for q in state.players[1].bench if state.is_face_down(q))
        _h, _r, _c, stages = stages_of(state, "じっとみる")
        option = next(o for o in stages[0]["options"] if o["pokemon"] == fd.pokemon_id)
        self.assertEqual((option["processability"], option.get("face_down")), (L.UNVERIFIED, True))
        self.assertFalse({"card", "card_id", "name_ja"} & set(option))  # 隠れた定義・カード id・uid を出さない
        text = json.dumps(stages, ensure_ascii=False)
        self.assertNotIn(H.DIGLETT, text)


class SessionContractTest(unittest.TestCase):
    STATES = (venusaur_board, lambda: board(mon(H.VILEPLUME, (H.GRASS,), evolved_from=[ODDISH, H.GLOOM]), [mon(H.RATTATA, damage=20)]),
              lambda: opponent_face_down(H.DIGLETT))

    def test_queries_change_nothing(self):
        for make in self.STATES:
            host = host_of(make())
            before = snap(host.game.state)
            session = host.session(0)
            for _ in range(2):
                r = session.candidates()
                for c in r["candidates"]:
                    session.inputs(r["game"], r["revision"], c["id"])
                    for choices in ([], ["o1"], ["o1", "o3"], ["o1", "o3", "o6"], ["o9"], [1]):
                        session.check(r["game"], r["revision"], c["id"], choices)
            self.assertEqual(snap(host.game.state), before)

    def test_handles(self):
        host = host_of(venusaur_board())
        session, other = host.session(0), host.session(1)
        r = session.candidates()
        c = cand(r, L.KIND_USE_POWER)
        stages = session.inputs(r["game"], r["revision"], c["id"])["stages"]
        state = host.game.state
        good = path_for(stages, state.players[0].active.pokemon_id, state.players[0].active.energy[0], state.players[0].bench[0].pokemon_id)
        self.assertEqual(other.check(r["game"], r["revision"], c["id"], good)["refusal"]["code"], L.CANDIDATES_WRONG_ACTOR)
        self.assertEqual(session.check("other", r["revision"], c["id"], good)["refusal"]["code"], L.CANDIDATES_WRONG_GAME)
        r1 = other.candidates()
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], good[:2]).refusal.code, L.CANDIDATE_INPUT_INVALID)
        self.assertEqual(other.check(r1["game"], r1["revision"], "c1", [])["refusal"]["code"], L.CANDIDATE_UNKNOWN)  # 拒否で相手の取っ手を失効させない
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], good).outcome, D.ACCEPTED)
        self.assertEqual(session.check(r["game"], r["revision"], c["id"], good)["refusal"]["code"], L.CANDIDATES_STALE)

    def test_no_verifier_values(self):
        for make in self.STATES:
            session = host_of(make()).session(0)
            r = session.candidates()
            payload = [r] + [session.inputs(r["game"], r["revision"], c["id"]) for c in r["candidates"]]
            self.assertFalse(set(keys(payload)) & (FORBIDDEN_KEYS - {"operation_id"}))
            self.assertNotIn("seed", json.dumps(payload))


class ClientApiTest(unittest.TestCase):
    def test_three_stage_through_client_api(self):
        state = venusaur_board()
        active, rattata = state.players[0].active, state.players[0].bench[0]
        hub = ClientHub.from_state(state.clone())
        me = hub.player(0)
        r = me.handle({**CONTRACT, "type": "candidates"})["response"]
        c = cand(r, L.KIND_USE_POWER)
        fields = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        stages = me.handle({**CONTRACT, "type": "inputs", **fields})["response"]["stages"]
        choices = path_for(stages, active.pokemon_id, active.energy[0], rattata.pokemon_id)
        self.assertTrue(me.handle({**CONTRACT, "type": "check", **fields, "choices": choices})["response"]["valid"])
        bad = me.handle({**CONTRACT, "type": "submit", **fields, "choices": choices[:2]})
        self.assertEqual((bad["outcome"], bad["refusal"]["code"]), (L.REFUSED, L.CANDIDATE_INPUT_INVALID))
        self.assertEqual([hub.take_updates(a) for a in (1, "spectator")], [[], []])
        sent = me.handle({**CONTRACT, "type": "submit", **fields, "choices": choices})
        self.assertEqual((sent["outcome"], sent["refetch_required"]), (D.ACCEPTED, True))
        game, _ = via_direct(state, UsePokemonPower(0, active.pokemon_id, 0, energy=active.energy[0], source=active.pokemon_id, target=rattata.pokemon_id))
        updates = {a: hub.take_updates(a) for a in (1, "spectator")}
        self.assertEqual(updates["spectator"][-1]["observation"], observe(game.state, None))
        self.assertEqual(updates[1][-1]["observation"], observe(game.state, 1))
        self.assertNotIn("Traceback", json.dumps(sent, ensure_ascii=False))


# new_game からの合法な操作の列（事前に固定した seed）: ロケット団のヒトカゲ（［ほのおをもらう］: 自分の場のほかのポケモンの炎エネルギー 1 枚をこのカードにつけかえる。2 段）
RC_DECK = [H.ROCKET_CHARMANDER] * 4 + [H.RATTATA] * 4 + [H.PONYTA] * 4 + [H.FIRE] * 48
RC_SEED = 1  # 事前に固定した seed: 準備を U7 で終えた先攻（0）の場にポニータとロケット団のヒトカゲがいて、手札に炎エネルギーがある


class ConnectionTest(unittest.TestCase):
    def test_power_from_new_game(self):
        from kyuura_engine import replay_run, view_record
        from kyuura_engine.replay_record import ReplayCollector

        self.assertEqual(len(RC_DECK), 60)
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                options = {} if conventions is None else {"conventions": conventions}
                start = A.start_game(RC_DECK, RC_DECK, RC_SEED, **options)
                recording = Recording(start.state.clone())
                host = L.ActionHost(recording)
                setup_with_u7(host)
                state = host.game.state
                rc = next(q for q in state.players[0].in_play() if state.cards[q.card].card_id == H.ROCKET_CHARMANDER)
                other = next(q for q in state.players[0].in_play() if q is not rc)
                session = host.session(0)
                r, c, inputs = inputs_of(session, L.KIND_ATTACH_ENERGY)
                stage1, stage2 = inputs["stages"]
                fire = next(o["id"] for o in stage1["options"] if o["card_id"] == H.FIRE)
                target = next(p["option"] for p in stage2["options_by_choice"][fire]
                              if next(o for o in stage2["options"] if o["id"] == p["option"])["pokemon"] == other.pokemon_id)
                self.assertEqual(session.submit(r["game"], r["revision"], c["id"], [fire, target]).outcome, D.ACCEPTED)
                state = host.game.state
                other = state.find_pokemon(other.pokemon_id)[1]
                r = session.candidates()
                c = next(x for x in r["candidates"] if x["kind"] == L.KIND_USE_POWER and x["pokemon"]["pokemon"] == rc.pokemon_id)
                stages = session.inputs(r["game"], r["revision"], c["id"])["stages"]
                self.assertEqual([s["role"] for s in stages], ["source", "energy"])
                self.assertEqual(session.submit(r["game"], r["revision"], c["id"], path_for(stages, other.pokemon_id, other.energy[-1])).outcome, D.ACCEPTED)
                r = session.candidates()
                self.assertEqual(session.submit(r["game"], r["revision"], cand(r, L.KIND_END_TURN)["id"], []).outcome, D.ACCEPTED)
                direct = A.HostedGame(start.state.clone())
                for command, submitter in recording.sent:
                    self.assertEqual(direct.submit(command, submitter=submitter).outcome, D.ACCEPTED, command)
                self.assertEqual(snap(direct.state), snap(host.game.state))
                self.assertTrue(any(isinstance(command, UsePokemonPower) for command, _ in recording.sent))
                collector, _ = ReplayCollector.start(RC_DECK, RC_DECK, RC_SEED, include_git=False, **options)
                for command, submitter in recording.sent:
                    self.assertEqual(collector.submit(command, submitter=submitter).outcome, D.ACCEPTED, command)
                record = collector.close()
                report = replay_run.replay(record)
                self.assertEqual(report.status, replay_run.SUCCEEDED, report.mismatch)
                view_report, views = view_record.view_records_from_replay(record)
                self.assertEqual(view_report.status, replay_run.SUCCEEDED)
                for viewer, rec in views.items():
                    self.assertEqual(view_record.validate_view_record(rec).problems, (), viewer)


class MappingTest(unittest.TestCase):
    def test_kind_fields_and_coverage(self):
        self.assertEqual([f.name for f in dataclasses.fields(UsePokemonPower)], ["player", "pokemon", "power", "energy", "source", "target", "card"])
        self.assertIn(L.KIND_USE_POWER, L.IMPLEMENTED_KINDS)
        _h, r, _c = power_cand(venusaur_board())
        cov = r["coverage"]
        self.assertEqual((cov["completeness"], cov["scope_kinds"], cov["not_covered_kinds"]), (L.PARTIAL, list(L.MAIN_KINDS), []))  # （v0.172（U7-5f）: check_face_up_deck も評価した種類（表示だけ。display_only_kinds）。未対応の種類はない）
        kinds = [c["kind"] for c in r["candidates"]]
        self.assertEqual(kinds, sorted(kinds, key=L.MAIN_KINDS.index))


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = (ROOT / "docs" / "legal-actions-u7-5e.md").read_text(encoding="utf-8")
        for phrase in ("UsePokemonPower", "check_use_pokemon_power", "use_power", "POWER_INPUT_STAGES", "upstream_stages", "after", "options_by_choice", "depends_on_stage",
                       "may_stop_later", "unverified", "partial", "kyuura-client-api", "F-4", "F-5", "R-1", "R-2", "U7-5f", "U7-5g", "3649946"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()

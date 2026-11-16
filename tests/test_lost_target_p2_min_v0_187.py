"""LOST_TARGET の P2-min（ゲンガーの［のろい］の target に相手のうらを 1 匹だけ指定する経路）のエンジンの動作の前提（docs/verification-ai-lost-target-p2-p3o-design.md
2 章の S1〜S3 と、実装の単位の追加の確かめ）。エンジンの動作・裁定・カードデータは変えない（テストだけ。版 0.187.0 のまま）。

経路: 相手（送る主体の相手）のうらが場にある送信は ``engine._apply_checked`` が ``zones.IDENTITY_CONSULTED`` を記録して 1 回試し、相手のうらを指定したら
``engine._identity_independent`` が公開のカードの一覧（``_public_pool``）のたね・ベイビィの代表ごとと「たねでない」の代表（``_NONBASIC``）で試し直す。
``_reveal_for_action`` は、使い手がおもてなら source → target の順に ``can_lose=False`` で指定する（handler の ``check_usable`` より前）。
［のろい］（``effects.MoveOpponentDamageCounter``）の target に相手のうらを指定すると、たねの代表の試しは受け付け、``_NONBASIC`` の試しが入口の指定で
``UNSUPPORTED_SECRET_PLAN_LOST_TARGET`` を出す。source に相手のうらを指定すると、たねの代表の試しが handler の ``NO_DAMAGE_COUNTERS``（うらのあいだはダメージ 0）で
先に拒否するので、このコードにならない（P2-min を target の指定に限る理由）。

盤面は ``tests/test_secret_plan_v0_67.py`` の ``board``・``place``・``full``・``face_down``・``opponent_turn`` で作る（new_game からの対戦ではない）。送信は公開の入口
（``adapter.submit``・``legal_actions.ActionHost``）を通す。テストの中で読む内部の値（``state.cards`` の本当のカード・``zones.IDENTITY_CONSULTED``）は盤面の準備と
前提の確かめにだけ使い、判定の根拠（本人の観測・選んだ入力・診断）とは別にする。
"""

from __future__ import annotations

import unittest
from unittest import mock

from kyuura_engine import UsePokemonPower
from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import engine as _engine
from kyuura_engine import legal_actions as L
from kyuura_engine.effects import DEFAULT_EFFECTS, POWER_CHOICE_OPPONENT_POKEMON, POWER_INPUT_STAGES, TEXT_PRE_NEO, MoveOpponentDamageCounter, card_is_basic_in_text
from kyuura_engine.engine import apply_command
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe
from kyuura_engine.zones import SECRET_PLAN_LOST_TARGET_CODE
from tests.helpers import DIGLETT, FIGHTING, FIRE, GASTLY, GENGAR, GUST, HAUNTER, HITMONCHAN, KADABRA, PSYCHIC
from tests.test_secret_plan_v0_67 import board, face_down, full, opponent_turn, place

PICHU = "neo1-042"  # ベイビィポケモン（ネオより前の説明の「たねポケモン」に当たる）
REALS = (DIGLETT, PICHU, KADABRA, FIRE, PSYCHIC, GUST)  # たね・ベイビィ・1 進化・エネルギー 2 種・トレーナー
CURSE_ID = "move_opponent_damage_counter"


def curse_board(real):
    """プレイヤー 0 が ``real`` をうらにしてベンチに出し、プレイヤー 1 の番。プレイヤー 1 のバトル場はゲンガー（［のろい］）、プレイヤー 0 のバトル場はダメージ 10 の
    エビワラー（おもて。source にできる）。(状態, ゲンガーの場のポケモンの番号, エビワラーの番号, うらの番号)。"""
    state = place(board(hand=(real,), active={"card": HITMONCHAN, "energy": [FIGHTING], "damage": 10},
                        opponent={"card": GENGAR, "evolved_from": [GASTLY, HAUNTER]}, turn_number=7), real)
    state = opponent_turn(state)
    (fd,) = face_down(state, 0)
    return state, state.players[1].active.pokemon_id, state.players[0].active.pokemon_id, fd.pokemon_id


def _no_identity_check(state, command, context, acting, result, error):
    """テストだけ: ありうるカードの確かめを外す（本当のカードの 1 回の処理の結果をそのまま返す）。製品の経路ではない。"""
    if error is not None:
        raise error
    return result


def curse(state, user, source, target):
    return UsePokemonPower(1, user, 0, source=source, target=target)


class RegistrationTest(unittest.TestCase):
    def test_curse_is_the_only_registered_power_of_its_type(self):
        """効果の型 MoveOpponentDamageCounter の登録は［のろい］（PMCG3-031 の 0 番目）だけ。宣言の段は source・target（どちらも相手の場のポケモン）。"""
        keys = [k for k in DEFAULT_EFFECTS.power_keys() if isinstance(DEFAULT_EFFECTS.power_entry(k.card_id, k.power_index).effect, MoveOpponentDamageCounter)]
        self.assertEqual([(k.card_id, k.power_index) for k in keys], [(GENGAR, 0)])
        self.assertEqual(DEFAULT_EFFECTS.power_entry(GENGAR, 0).effect.implementation_id, CURSE_ID)
        self.assertEqual([role for role, _domain in POWER_INPUT_STAGES[MoveOpponentDamageCounter]], ["source", "target"])
        self.assertEqual({domain for _role, domain in POWER_INPUT_STAGES[MoveOpponentDamageCounter]}, {POWER_CHOICE_OPPONENT_POKEMON})


class IdentityIndependenceTest(unittest.TestCase):
    def test_s2_target_face_down_is_refused_with_the_same_code_for_every_identity(self):
        """S2（E-P2-1）: target に相手のうらを指定すると、本当のカードがたね・ベイビィ・1 進化・エネルギー・トレーナーのどれでも、同じコード・同じ文で拒否。状態・乱数・
        ログ・決定は変わらない（E-P2-3）。"""
        results = []
        for real in REALS:
            with self.subTest(real=real):
                state, user, source, fd = curse_board(real)
                before = (full(state), len(state.log), state.decision, state.next_decision_id)
                with self.assertRaises(UnsupportedError) as ctx:
                    apply_command(state, curse(state, user, source, fd))
                self.assertEqual((full(state), len(state.log), state.decision, state.next_decision_id), before)
                results.append((ctx.exception.code, ctx.exception.message))
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(results[0][0], SECRET_PLAN_LOST_TARGET_CODE)
        self.assertIn("ありうるカードのどれかのとき", results[0][1])  # 本当のカードによらない確かめ（_identity_independent）を通った文。判定では使わない

    def test_basic_real_is_refused_only_through_the_identity_check(self):
        """受理が相手の real によらない: たねの本当のカードでも、ありうるカードの確かめがなければ受け付ける（たねなら入口の指定はおもてにして続ける）。"""
        state, user, source, fd = curse_board(DIGLETT)
        with mock.patch.object(_engine, "_identity_independent", _no_identity_check):
            after = apply_command(state, curse(state, user, source, fd))
        self.assertFalse(after.is_face_down(after.players[0].find_by_pokemon_id(fd)))  # おもてにして、ダメージカウンターをのせた
        with self.assertRaises(UnsupportedError):
            apply_command(state, curse(state, user, source, fd))  # 本物の経路（確かめあり）は拒否

    def test_source_face_down_is_rejected_before_the_lost_target_trial(self):
        """source に相手のうらを指定すると、たねの代表の試しが handler の NO_DAMAGE_COUNTERS で先に拒否する（本当のカードによらない）。このコードにならない。"""
        codes = set()
        for real in (DIGLETT, KADABRA, FIRE):
            state, user, _source, fd = curse_board(real)
            other = state.players[0].active.pokemon_id
            with self.assertRaises(IllegalActionError) as ctx:
                apply_command(state, curse(state, user, fd, other))
            codes.add(ctx.exception.code)
        self.assertEqual(codes, {"NO_DAMAGE_COUNTERS"})

    def test_s1_entry_designation_with_can_lose_false(self):
        """S1（E-P2-2）: 入口の指定は handler より前で、can_lose=False（本当のカードがたねでない場合、確かめなしの 1 回の処理でもこのコード）。"""
        from kyuura_engine import zones as Z

        state, user, source, fd = curse_board(KADABRA)
        calls = []
        original = Z.designate_face_down

        def spy(st, owner, pokemon, *, by_player, cause, can_lose):
            calls.append((owner, cause, can_lose))
            return original(st, owner, pokemon, by_player=by_player, cause=cause, can_lose=can_lose)
        with mock.patch.object(_engine, "designate_face_down", spy), \
                mock.patch.object(_engine, "_identity_independent", _no_identity_check):
            with self.assertRaises(UnsupportedError) as ctx:
                apply_command(state, curse(state, user, source, fd))
        self.assertEqual(ctx.exception.code, SECRET_PLAN_LOST_TARGET_CODE)
        self.assertEqual(calls, [(0, "power", False)])

    def test_s3_public_pool_has_a_non_basic_candidate(self):
        """S3（E-P2-4）: 公開のカードの一覧に、たねでもベイビィでもないカードがある（_NONBASIC の試しがいつもある）。"""
        state, *_ = curse_board(DIGLETT)
        pool = _engine._public_pool(state)
        candidates = _engine._identity_candidates(pool)
        nonbasic = [c for c in candidates if not pool.get(c).is_baby_or_basic_pokemon]
        self.assertTrue(nonbasic)
        self.assertTrue(all(card_is_basic_in_text(pool.get(c), TEXT_PRE_NEO) is not True for c in nonbasic))


class PublicEntryTest(unittest.TestCase):
    def test_public_result_and_views_are_the_same_for_every_identity(self):
        """公開の入口（adapter.submit）: 本人への診断（コード・分類・文・status・next）・相手と観戦者への知らせ・検証者の報告のコードが、本当のカードによらず同じ。"""
        seen = []
        for real in REALS:
            state, user, source, fd = curse_board(real)
            result = A.submit(state, curse(state, user, source, fd), submitter=1)
            self.assertEqual(result.outcome, D.REJECTED)
            actor_view = result.view_for(1).to_dict()
            others = tuple(None if v is None else v.to_dict() for v in (result.view_for(0), result.view_for(None)))  # 相手・観戦者（拒否は知らせない）
            seen.append((result.diagnosis.diagnostic_id, result.diagnosis.category, result.verifier.engine_code, actor_view["status"], actor_view["next"],
                         actor_view["message"], actor_view["continuable"], str(others)))
        self.assertEqual(len(set(map(str, seen))), 1)
        code, category, engine_code, status, next_, _message, continuable, _others = seen[0]
        self.assertEqual((code, category, engine_code, status, continuable), (SECRET_PLAN_LOST_TARGET_CODE, D.UNSUPPORTED, SECRET_PLAN_LOST_TARGET_CODE, D.IN_PROGRESS, True))
        self.assertEqual(next_, [{"kind": "turn_action", "player": 1}])

    def test_observation_and_input_reference_link_without_the_real_card(self):
        """本人の観測と入力の参照が、場のポケモンの番号で結べる。相手のうらの観測の行・選べるものに本当のカードはない。使い手はおもて（限定の経路）。"""
        for real in (DIGLETT, KADABRA):
            with self.subTest(real=real):
                state, user, source, fd = curse_board(real)
                view = observe(state, 1)
                rows = [z for z in [view["players"][0]["active"], *view["players"][0]["bench"]] if z.get("pokemon_id") == fd]
                self.assertEqual(len(rows), 1)
                self.assertTrue(rows[0]["face_down"])
                self.assertNotIn("real", rows[0])
                host = L.ActionHost(A.HostedGame(state.clone()))
                s = host.session(1)
                r = s.candidates()
                cand = next(c for c in r["candidates"] if c["kind"] == L.KIND_USE_POWER and c["power"]["card_id"] == GENGAR)
                self.assertEqual(cand["pokemon"]["pokemon"], user)
                self.assertEqual(cand["pokemon"]["card_id"], GENGAR)
                self.assertNotIn("face_down", cand["pokemon"])
                self.assertEqual((cand["power"]["index"], cand["power"]["card"]), (0, cand["pokemon"]["card"]))  # 写した力ではない
                stages = s.inputs(r["game"], r["revision"], cand["id"])["stages"]
                self.assertEqual([st["role"] for st in stages], ["source", "target"])
                target_stage = stages[1]
                options = target_stage.get("options") or [o for by in (target_stage.get("options_by_choice") or {}).values() for o in by]
                found = [o for o in options if o.get("pokemon") == fd]
                self.assertTrue(found)
                for o in found:
                    self.assertTrue(o.get("face_down"))
                    self.assertNotIn("card", o)
                    self.assertNotIn("card_id", o)
                    self.assertIn("face_down_reveal_not_evaluated", o.get("reasons") or [])


if __name__ == "__main__":
    unittest.main()

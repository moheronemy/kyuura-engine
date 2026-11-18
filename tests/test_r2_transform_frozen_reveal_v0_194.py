"""R-2 の変身の経路 C-TF2（v0.194。docs/r2-transform-frozen-reveal-design.md の案 A）: ワザの宣言でうらの使い手をおもてにしたら、公開の直後のその姿を既存の固定へ足す。

0.193.0 までは、入口の固定（``engine._apply_once`` の ``freeze_forms``）が公開の前で、うらの使い手（変身の特殊能力を持たない）を入れず、ワザの始めの固定（``flow._use_attack`` の
``body``）は固定が空でなければ何もしなかった。そのため、場にほかの変身できるポケモンがいると、公開したメタモンの姿を固定せず、きつねびの入れ替え（相手の答え）で RX1
（``UNRESOLVED_REACTIVE_SWITCH_TRANSFORMED_ATTACKER``）になった（SF3）。v0.194 から、攻撃者を先に公開した対照（おもて）と同じ姿・ダメージで処理する（CR-TRANSFORM-FROZEN-DURING-ACTION）。

盤面はすべて構築盤面（``test_r2_transform_preconditions_v0_192`` の ``fd``・``up``。new_game からの到達ではない）。合格の条件は、停止が消えることではなく、うらから公開した使い手の
結果（受理・決定・答えごとのダメージ・固定・解除）が、同じ盤面のおもての対照と一致すること。対照の値は修正の前の 0.193.0 で記録した（証跡 r2-transform-c-tf2-impl の probe_before.json）。

ここで確かめないもの: SF3-b（あとにダメージのない入れ替えで TK1 の境をまたぐ）は、うらのカードにダメージがのらない（不変条件）ので、妥当な構築盤面では、うらの使い手が宣言の時点で
ダメージを持てない。固定の項目がおもての対照と同じになること（``WhirlwindTest``）だけを確かめる。独立の監査の ``log_problems`` は new_game から進めたログ用で、構築盤面には使えない
（TC20 はここで確かめない）。SF3-P・SF5・O-REV・SF4 は別の単位。
"""

from __future__ import annotations

import unittest

from kyuura_engine import ResolveDecision, UseAttack
from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import effects as E
from kyuura_engine import legal_actions as L
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.snapshot import dumps_snapshot, loads_snapshot, restore_snapshot, save_snapshot
from tests import helpers as H
from tests.helpers import apply_kernel
from tests.log_audit import observation_problems, serialization_problems
from tests.test_legal_actions_r2_stadium_coin_v0_188 import attack_of
from tests.test_legal_actions_u7_1 import snap
from tests.test_legal_actions_u7_4 import via_direct, via_u7
from tests.test_r2_transform_preconditions_v0_192 import COPY_UNSUPPORTED, FD1, accepted_once, damages, fd, lanturn, mon, rejects, up, valid

DITTO, DITTO_SUPER, VULPIX = H.DITTO, "ES2-032", "ES3-009"
W, L_, R, F = H.WATER, H.LIGHTNING, H.FIRE, H.FIGHTING
OPP_V = mon(VULPIX, (R,))
V_BENCH = (mon(H.BULBASAUR), mon(H.SQUIRTLE))
OB_DITTO = (mon(H.BULBASAUR), mon(DITTO))
OTHER_DITTO = (mon(DITTO),)


def frozen_rows(state):
    """固定の項目を、番号によらない形（持ち主・場所・カード・種類）で並びのまま。"""
    rows = []
    for f in state.frozen_forms:
        owner, pokemon = state.find_pokemon(f.pokemon)
        place = "active" if state.players[owner].active is pokemon else "bench"
        rows.append((owner, place, state.cards[f.card].card_id, f.kind))
    return rows


def bench_id(state, player, card_id):
    return next(p.pokemon_id for p in state.players[player].bench if state.cards[p.card].card_id == card_id)


def answer(test, asked, card_id):
    """決定（相手が選ぶ入れ替えはプレイヤー 1、きつねびは攻撃者）に ``card_id`` の控えで答える（None なら入れ替えない）。3 つの先読みの方法で同じ状態。"""
    d = asked.decision
    owner = 1
    choice = () if card_id is None else (bench_id(asked, owner, card_id),)
    results = [apply_kernel(asked, ResolveDecision(d.player, d.id, choice), preflight=mode) for mode in PREFLIGHT_MODES]
    test.assertEqual(len({repr(snap(r)) for r in results}), 1)
    done = results[0]
    test.assertEqual((observation_problems(done), serialization_problems(done)), ([], []))
    return done


def attacker_form(state):
    a = state.players[0].active
    return state.cards[E.current_form(state, a).card].card_id


class VulpixSwitchTest(unittest.TestCase):
    """TC1・TC2・TC3・TC4・TC5・TC6・TC13: きつねび（のぞむなら入れ替えてからダメージ）。うら（ほかの変身できるポケモンあり）がおもての対照と同じ。"""

    BOARDS = {
        "own_bench_ditto": (dict(bench=OTHER_DITTO, opponent_bench=V_BENCH), (H.BULBASAUR, H.SQUIRTLE, None), {H.BULBASAUR: 20, H.SQUIRTLE: 10, None: 10}),
        "opponent_bench_ditto": (dict(opponent_bench=OB_DITTO), (H.BULBASAUR, DITTO, None), {H.BULBASAUR: 20, DITTO: 10, None: 10}),
        "no_other": (dict(opponent_bench=V_BENCH), (H.BULBASAUR, H.SQUIRTLE, None), {H.BULBASAUR: 20, H.SQUIRTLE: 10, None: 10}),
    }

    def _asked(self, maker, extra):
        state = valid(self, maker(DITTO, (W, W), opponent=OPP_V, **extra))
        return state, (accepted_once(self, state, UseAttack(0, 0)) if state.is_face_down(state.players[0].active) else apply_kernel(state, UseAttack(0, 0)))

    def test_face_down_matches_the_face_up_control(self):
        for name, (extra, choices, expected) in self.BOARDS.items():
            with self.subTest(board=name):
                _s, asked_fd = self._asked(fd, extra)
                _s, asked_up = self._asked(up, extra)
                self.assertEqual(asked_fd.decision.kind, "forced_switch")
                self.assertEqual(asked_fd.decision.context_value("unresolved_choices", ()), ())
                self.assertEqual(frozen_rows(asked_fd), frozen_rows(asked_up))
                self.assertEqual(frozen_rows(asked_fd)[0], (0, "active", VULPIX, "transform"))
                for card_id in choices:
                    with self.subTest(answer=card_id):
                        done_fd, done_up = answer(self, asked_fd, card_id), answer(self, asked_up, card_id)
                        self.assertEqual(damages(asked_fd, done_fd), [expected[card_id]])
                        self.assertEqual(damages(asked_fd, done_fd), damages(asked_up, done_up))
                        self.assertEqual((done_fd.frozen_forms, done_up.frozen_forms), ((), ()))
                        self.assertEqual(attacker_form(done_fd), attacker_form(done_up))

    def test_other_entries_keep_their_values_and_order(self):
        """TC16: 自分のベンチ・相手のベンチのメタモンの項目は printed のまま。並びはプレイヤー → in_play()（おもての対照と同じ）。"""
        extra = dict(bench=OTHER_DITTO, opponent_bench=OB_DITTO)
        state, asked = self._asked(fd, extra)
        self.assertEqual(frozen_rows(asked), [(0, "active", VULPIX, "transform"), (0, "bench", DITTO, "printed"), (1, "bench", DITTO, "printed")])
        self.assertEqual(frozen_rows(asked), frozen_rows(self._asked(up, extra)[1]))
        done = answer(self, asked, H.BULBASAUR)
        self.assertEqual(damages(asked, done), [20])


class RamTest(unittest.TestCase):
    """サイドンの「げきとつ」（入れ替えのあと自分にも 20。相手が選ぶ。控えが 1 匹）。0.193.0 では、うら（ほかのメタモンあり）はどの答えも RX1 なのでワザの宣言ごと拒否した。"""

    def test_face_down_matches_the_face_up_control(self):
        rhydon = mon(H.RHYDON, evolved_from=H.RHYHORN)
        results = {}
        for name, maker in (("fd", fd), ("up", up)):
            state = valid(self, maker(DITTO, (F,) * 4, bench=OTHER_DITTO, opponent=rhydon, opponent_bench=(mon(H.BULBASAUR),)))
            asked = accepted_once(self, state, UseAttack(0, 1)) if name == "fd" else apply_kernel(state, UseAttack(0, 1))
            done = answer(self, asked, H.BULBASAUR)
            results[name] = (damages(state, asked), damages(asked, done), frozen_rows(asked), done.players[0].active.damage, done.frozen_forms)
        self.assertEqual(results["fd"], results["up"])
        self.assertEqual(results["fd"][:2], ([50], [20]))


class WhirlwindTest(unittest.TestCase):
    """TC7 の関連: ピジョンの「ふきとばし」（あとにダメージのない入れ替え）。固定の項目がおもての対照と同じ（解除のときの TK1 の確かめが同じ項目を見る）。"""

    def test_frozen_entries_match_the_face_up_control(self):
        pidgeotto = mon(H.PIDGEOTTO, evolved_from=H.PIDGEY)
        rows = {}
        for name, maker in (("fd", fd), ("up", up)):
            state = valid(self, maker(DITTO, (W, W), bench=OTHER_DITTO, opponent=pidgeotto, opponent_bench=(mon(H.BULBASAUR),)))
            asked = apply_kernel(state, UseAttack(0, 0))
            done = answer(self, asked, H.BULBASAUR)
            rows[name] = (frozen_rows(asked), damages(state, asked), done.frozen_forms, attacker_form(done))
        self.assertEqual(rows["fd"], rows["up"])
        self.assertEqual(rows["fd"][0][0], (0, "active", H.PIDGEOTTO, "transform"))


class DecisionLifetimeTest(unittest.TestCase):
    """TC11: 決定をまたぐ固定。保存した snapshot から続けても同じ。解除は既存の位置（ワザの終わり・決定のないコマンドの終わり）。

    TC12（0.193.0 で作った決定待ちの snapshot）は、既存の識別の検査（``restore_snapshot`` の implementation_differs・engine_version_differs）で復元しない。固定を補修しない。
    0.193.0 の決定は、作ったときの ``unresolved_choices`` を持つので、ここで項目を消した状態を作っても旧状態と同じにならない（証跡の probe で実際の 0.193.0 の snapshot を確かめる）。"""

    def _asked(self):
        state = valid(self, fd(DITTO, (W, W), bench=OTHER_DITTO, opponent=OPP_V, opponent_bench=V_BENCH))
        return apply_kernel(state, UseAttack(0, 0))

    def test_snapshot_round_trip_keeps_the_added_entry(self):
        asked = self._asked()
        report = restore_snapshot(loads_snapshot(dumps_snapshot(save_snapshot(asked))))
        self.assertEqual(report.status, "restored")
        restored = report.state
        self.assertEqual(frozen_rows(restored), frozen_rows(asked))
        self.assertEqual(damages(restored, answer(self, restored, H.BULBASAUR)), [20])

    def test_released_after_a_command_without_a_decision(self):
        """ほかのメタモンありで、決定のないワザ（入れ替えない盤面: 相手の控えなし）。コマンドの終わりに固定が残らない。"""
        state = valid(self, fd(DITTO, (W, W), bench=OTHER_DITTO, opponent=OPP_V))
        done = accepted_once(self, state, UseAttack(0, 0))
        self.assertEqual((done.decision, done.frozen_forms, damages(state, done)), (None, (), [10]))


class KeptStopsTest(unittest.TestCase):
    """TC9・TC15・TC17・TC18・TC19: 固定の追加と関係のない停止・拒否は今のまま（状態・乱数・ログ・決定は不変）。"""

    def test_face_down_defender_is_still_fd1(self):
        for bench in ((), OTHER_DITTO):
            with self.subTest(other=bool(bench)):
                rejects(self, valid(self, fd(DITTO, (W, W), bench=bench, opponent_active_face_down=H.RATTATA)), UseAttack(0, 0), FD1)

    def test_copied_power_stop_is_unchanged(self):
        for bench in ((), OTHER_DITTO):
            with self.subTest(other=bool(bench)):
                rejects(self, valid(self, fd(DITTO, (W, W, W), bench=bench, opponent=lanturn())), UseAttack(0, 0, attack_power=True), COPY_UNSUPPORTED)

    def test_non_basic_is_discarded_without_freezing(self):
        state = valid(self, fd(H.LANTURN_NEO1, (L_, L_), bench=OTHER_DITTO, opponent=mon(H.ONIX)))
        done = accepted_once(self, state, UseAttack(0, 0))
        self.assertEqual((done.frozen_forms, damages(state, done)), ((), []))
        self.assertEqual([e["kind"] for e in done.log[len(state.log):]].count("attack"), 0)

    def test_super_transform_ditto_has_no_attack(self):
        for maker in (fd, up):
            with self.subTest(attacker=maker.__name__):
                rejects(self, valid(self, maker(DITTO_SUPER, (W, W), bench=OTHER_DITTO, opponent=OPP_V, opponent_bench=V_BENCH)), UseAttack(0, 0), "INVALID_ATTACK")


class ApiTest(unittest.TestCase):
    """TC14: 公開 API は変えない。おもての対照は API と直接のコマンドで同じ。うらのメタモンの候補は ``no_printed_attack`` の保留のまま。"""

    def test_face_up_control_api_equals_direct(self):
        state = valid(self, up(DITTO, (W, W), bench=OTHER_DITTO, opponent=OPP_V, opponent_bench=V_BENCH))
        host, result = via_u7(state, lambda stages: [o["id"] for o in stages[0]["options"] if o["processability"] in L.EXECUTABLE][:1])
        game, direct = via_direct(state, UseAttack(0, 0))
        self.assertEqual((result["outcome"] if isinstance(result, dict) else result.outcome), D.ACCEPTED)
        self.assertEqual(snap(host.game.state), snap(game.state))

    def test_face_down_ditto_candidate_is_still_held(self):
        state = valid(self, fd(DITTO, (W, W), bench=OTHER_DITTO, opponent=OPP_V, opponent_bench=V_BENCH))
        _h, _s, _r, c, inputs = attack_of(state)
        self.assertEqual((c["processability"], c["reasons"]), (L.NOT_IMPLEMENTED, [L.REASON_FACE_DOWN, L.REASON_NO_PRINTED_ATTACK]))
        self.assertEqual(inputs["stages"], [])

    def test_direct_command_through_the_host(self):
        state = valid(self, fd(DITTO, (W, W), bench=OTHER_DITTO, opponent=OPP_V, opponent_bench=V_BENCH))
        game = A.HostedGame(state.clone())
        result = game.submit(UseAttack(0, 0), submitter=0)
        self.assertEqual(result.outcome, D.ACCEPTED)
        d = game.state.decision
        result = game.submit(ResolveDecision(d.player, d.id, (bench_id(game.state, 1, H.BULBASAUR),)), submitter=d.player)
        self.assertEqual(result.outcome, D.ACCEPTED)
        self.assertEqual(game.state.frozen_forms, ())


if __name__ == "__main__":
    unittest.main()

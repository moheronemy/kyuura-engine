"""R-2 の変身の経路の前提確認（C-TF0。docs/r2-transform-hydro-design.md 9 章）。0.192.0 のまま、エンジンは変えない。

構築盤面（マチスの秘策でうらにしてバトル場へ。new_game からの到達ではない）から直接のコマンドを送り、既存の仕様から決まる結果と、結果に依存しない性質だけを確かめる。
候補・入力 API は対象外（変身の経路は今も示さない。``test_legal_actions_r2_unown_v0_191.test_transform_route_is_not_offered``）。

ここで確かめないもの（9 章の分類。証跡の再現スクリプトに残す）:
- SF1: ［へんしん］で写した［すいりょくはつでん］・［XXXXX］を、ワザといっしょに使うと受け付けられる（v0.124 の 3.1 節の未対応の範囲との差。不具合候補）
- SF2: 写した［すいりょくはつでん］の「水」の数で TE1 を聞かない・支払いに使う「水」を多い数に入れる（SF1 に従属。後者は未裁定）
- SF3: 場にほかの変身できるポケモンがいると、公開したメタモンの姿をワザのあいだ固定しない（不具合候補）
今の動きをこれらの期待値として固定しない。

v0.193（C-TF1。設計の 10 章）: SF1 を直した（写した力の宣言は既存の ``UNSUPPORTED_TRANSFORM_COPIED_POWER``。0.192.0 では受け付けて 20 → 50・60・20）。修正の後の期待は
``test_r2_transform_copied_power_v0_193`` に置く。このモジュールは SF1 の旧動作を期待値にしていなかったので、期待は変えない（``CopiedPowerExistingStopTest`` は前から
``UsePokemonPower`` の側の既存の停止）。SF2 の写した［すいりょくはつでん］の経路は宣言で止まり、数えるところに着かない（数え方の裁定は未決のまま）。SF3（姿の固定）は直していない
（きつねびの再現はワザといっしょに使う力を使わないので、この修正では隠れない。証跡に残す）。
"""

from __future__ import annotations

import unittest

from kyuura_engine import AttachEnergy, ResolveDecision, UseAttack, UsePokemonPower, check_invariants, current_form
from kyuura_engine import effects as E
from kyuura_engine.coins import CoinSide
from kyuura_engine.errors import SECRET_PLAN_HIDDEN_CODE
from kyuura_engine.observation import visible_log
from kyuura_engine.resolution import PREFLIGHT_MODES
from tests import helpers as H
from tests import test_secret_plan_v0_67 as S
from tests.helpers import apply_kernel, with_coin_bits
from tests.log_audit import observation_problems, serialization_problems
from tests.test_legal_actions_u7_1 import snap

TL = CoinSide.TAILS
DITTO, DITTO_SUPER, LANTURN = H.DITTO, "ES2-032", H.LANTURN_NEO1
VULPIX, FERALIGATR = "ES3-009", "neo4-039"  # ロコン（きつねび: のぞむなら入れ替えてからダメージ）・わるいオーダイル（［いあつ］）
W, L, F, R = H.WATER, H.LIGHTNING, H.FIGHTING, H.FIRE
# 停止のコードはエンジンの定数で参照する（FD1・TF1 の残る部分・写すことを確かめていない特殊能力）
FD1, TF1_REST, COPY_UNSUPPORTED = SECRET_PLAN_HIDDEN_CODE, E.TRANSFORM_POWER_CODE, E.TRANSFORM_COPIED_UNSUPPORTED_CODE


def mon(card, energy=(), **extra):
    return {"card": card, "energy": list(energy), **extra}


def lanturn(energy=(L, L)):
    return mon(LANTURN, energy, evolved_from=H.CHINCHOU_NEO1)


def fd(real=DITTO, energies=(W,), *, bench=(), opponent=None, opponent_bench=(), opponent_hand=(), opponent_face_down=None, opponent_active_face_down=None):
    """プレイヤー 0 の番の main。バトル場はうらの ``real``（マチスの秘策）で ``energies`` を 1 番に 1 枚ずつ。相手は ``opponent_face_down`` をベンチに、``opponent_active_face_down`` を
    バトル場に、最初の番にうらで出す（マチスの秘策。バトル場は闘エネルギー 2 枚のエビワラーのにげるで入れ替える）。"""
    hidden = opponent_face_down or opponent_active_face_down
    o_hand = (H.LT_SURGES_SECRET_PLAN, hidden, *opponent_hand) if hidden else tuple(opponent_hand)
    o_active = mon(H.HITMONCHAN, (F, F)) if opponent_active_face_down else opponent
    state = S.board(hand=(real, *energies), bench=bench, opponent=o_active or mon(H.ONIX), opponent_bench=opponent_bench, opponent_hand=o_hand, turn_number=7)
    state = S.place(state, real)
    state = S.to_active(state, S.face_down(state)[0])
    state = S.opponent_turn(state)
    if hidden:
        state = S.place(state, hidden, player=1)
        if opponent_active_face_down:
            state = S.to_active(state, S.face_down(state, 1)[0], player=1)
    state = S.opponent_turn(state)
    for i, energy in enumerate(energies):
        if i:
            state = S.opponent_turn(S.opponent_turn(state))
        state = S.apply_command(state, AttachEnergy(0, S.uid_of(state, energy), state.players[0].active.card))
    assert state.is_face_down(state.players[0].active) and state.current_player == 0 and state.decision is None
    return state


def up(real=DITTO, energies=(W,), *, bench=(), opponent=None, opponent_bench=()):
    """攻撃者を先に公開した対照（同じ本当のカードがおもてでバトル場）。"""
    return H.build_test_state([{"active": mon(real, energies), "bench": list(bench), "hand": [], "deck": [H.FIRE] * 10},
                               {"active": opponent or mon(H.ONIX), "bench": list(opponent_bench), "hand": [], "deck": [H.FIRE] * 10}],
                              turn_number=9, current_player=0)


def valid(test, state):
    """実行の前の盤面の確かめ（不変条件・書き出し・観測）。不正な盤面を製品の不具合として扱わない。"""
    test.assertEqual((check_invariants(state), serialization_problems(state), observation_problems(state)), ([], [], []))
    return state


def rejects(test, state, command, code):
    """どの先読みの方法でも ``code`` で拒否し、状態・乱数・ログ・決定の通し番号を変えない。"""
    before = snap(state)
    for mode in PREFLIGHT_MODES:
        with test.subTest(mode=mode):
            with test.assertRaises(Exception) as raised:
                apply_kernel(state, command, preflight=mode)
            test.assertEqual(getattr(raised.exception, "code", None), code)
    test.assertEqual(snap(state), before)


def accepted_once(test, state, command):
    """どの先読みの方法でも同じ状態で受け付け、うらの使い手の公開は 1 回（相手にも 1 回見える）。受け付けた状態を返す。"""
    results = [apply_kernel(state, command, preflight=mode) for mode in PREFLIGHT_MODES]
    test.assertEqual(len({repr(snap(r)) for r in results}), 1)
    done = results[0]
    new = done.log[len(state.log):]
    test.assertEqual(sum(1 for e in new if e["kind"] == "secret_plan_revealed"), 1)
    seen = visible_log(done, 1)[len(visible_log(state, 1)):]
    test.assertEqual(sum(1 for e in seen if e["kind"] == "secret_plan_revealed"), 1)
    test.assertLessEqual(sum(1 for e in new if e["kind"] == "damage"), 1)
    test.assertEqual((check_invariants(done), serialization_problems(done), observation_problems(done)), ([], [], []))
    return done


def damages(before, after):
    return [e["amount"] for e in after.log[len(before.log):] if e["kind"] == "damage"]


class CopiedAttackIndexTest(unittest.TestCase):
    """PT2: 公開のあとの ``attack_index`` は今の姿（写す相手のカード）のワザの位置。``card`` を省く（None）と、写す相手の uid を入れたときと同じワザ（v0.49 の ``UseAttack.card``）。"""

    def test_card_none_and_copied_card_point_to_the_same_attack(self):
        for idx in (0, 1):
            with self.subTest(index=idx):
                state = valid(self, with_coin_bits(fd(DITTO, (W, W), opponent=mon(H.LAPRAS, (W,))), TL, TL))
                lapras = state.players[1].active.card
                plain = accepted_once(self, state, UseAttack(0, idx))
                named = accepted_once(self, state, UseAttack(0, idx, card=lapras))
                self.assertEqual(snap(plain), snap(named))
                self.assertEqual(state.cards[current_form(plain, plain.players[0].active).card].card_id, H.LAPRAS)
                control = up(DITTO, (W, W), opponent=mon(H.LAPRAS, (W,)))
                self.assertEqual(damages(state, plain), damages(control, apply_kernel(with_coin_bits(control, TL, TL), UseAttack(0, idx))))

    def test_index_past_the_copied_attacks_and_other_cards_are_invalid(self):
        state = valid(self, fd(DITTO, (W, W), opponent=mon(H.LAPRAS, (W,)), opponent_bench=(mon(H.LAPRAS),)))
        rejects(self, state, UseAttack(0, 2), "INVALID_ATTACK")
        rejects(self, state, UseAttack(0, 0, card=state.players[0].active.card), "INVALID_ATTACK")  # 印刷のカード（メタモン）にワザはない
        rejects(self, state, UseAttack(0, 0, card=state.players[1].bench[0].card), "INVALID_ATTACK")  # 写す相手でないカード
        one = valid(self, fd(DITTO, (W, W), opponent=lanturn()))
        rejects(self, one, UseAttack(0, 1), "INVALID_ATTACK")  # ワザ 1 つのカードを写すと、位置 1 はない


class CopyTargetStopsTest(unittest.TestCase):
    """PT3・PT4: 写す相手がうら（FD1）・［へんしん］が消える・写す力が抑止の力（TF1 の残る部分）は、既存の停止・拒否のまま。"""

    def test_face_down_defender_is_fd1_whatever_its_identity(self):
        for hidden in (H.RATTATA, H.LAPRAS):
            with self.subTest(hidden=hidden):
                state = valid(self, fd(DITTO, (W,), opponent_active_face_down=hidden))
                rejects(self, state, UseAttack(0, 0), FD1)

    def test_suppressed_transform_has_no_attacks(self):
        muk = mon(H.MUK, evolved_from=H.GRIMER)
        for state in (fd(DITTO, (W, W), bench=(muk,), opponent=lanturn()), up(DITTO, (W, W), bench=(muk,), opponent=lanturn())):
            rejects(self, valid(self, state), UseAttack(0, 0), "INVALID_ATTACK")

    def test_copying_a_scaring_power_stops(self):
        state = valid(self, fd(DITTO, (W, W, W), opponent=mon(FERALIGATR, evolved_from=["neo4-028", "neo4-036"])))
        rejects(self, state, UseAttack(0, 0), TF1_REST)

    def test_super_transform_face_down_has_no_attacks(self):
        state = valid(self, fd(DITTO_SUPER, (W, W, W), opponent=lanturn()))
        rejects(self, state, UseAttack(0, 0), "INVALID_ATTACK")
        rejects(self, state, UseAttack(0, 0, attack_power=True), "INVALID_ATTACK")


class CopiedPowerExistingStopTest(unittest.TestCase):
    """SF1 の既存の停止の側: 写した［すいりょくはつでん］を ``UsePokemonPower`` で使うと、写すことを確かめていない宣言する特殊能力として未対応（v0.124 の 3.1 節）。"""

    def test_use_pokemon_power_with_the_copied_card(self):
        state = valid(self, up(DITTO, (W, W, W), opponent=lanturn()))
        ditto = state.players[0].active
        rejects(self, state, UsePokemonPower(0, ditto.pokemon_id, 0, card=state.players[1].active.card), COPY_UNSUPPORTED)


class FrozenAfterRevealTest(unittest.TestCase):
    """PT5 の対照: 場にほかの変身できるポケモンがいなければ、うらから公開したメタモンの姿はワザの始め（``flow._use_attack`` の body）に固定され、ワザの途中の入れ替えのあとも
    宣言のときの姿で処理する（CR-TRANSFORM-FROZEN-DURING-ACTION。攻撃者を先に公開した対照と同じ）。ほかの変身できるポケモンがいる盤面（SF3）は、ここで期待値を決めない。"""

    def test_switch_during_the_attack_uses_the_declared_form(self):
        opponent, bench = mon(VULPIX, (R,)), (mon(H.BULBASAUR), mon(H.SQUIRTLE))
        for name, state in (("face_down", fd(DITTO, (W, W), opponent=opponent, opponent_bench=bench)), ("face_up", up(DITTO, (W, W), opponent=opponent, opponent_bench=bench))):
            with self.subTest(attacker=name):
                state = valid(self, state)
                asked = apply_kernel(state, UseAttack(0, 0))
                attacker = asked.players[0].active
                self.assertEqual(asked.decision.kind, "forced_switch")
                self.assertEqual([(f.pokemon, asked.cards[f.card].card_id) for f in asked.frozen_forms if f.pokemon == attacker.pokemon_id],
                                 [(attacker.pokemon_id, VULPIX)])
                bulbasaur = next(p.pokemon_id for p in asked.players[1].bench if asked.cards[p.card].card_id == H.BULBASAUR)
                done = apply_kernel(asked, ResolveDecision(0, asked.decision.id, (bulbasaur,)))
                self.assertEqual(damages(asked, done), [20])  # 炎（宣言のときの姿）で、フシギダネの弱点（炎）
                self.assertEqual(done.frozen_forms, ())


class RevealDiscardTest(unittest.TestCase):
    """L1・D1: 本当のカードがたねでない（ランターン・タケシのキュウコン）なら、公開してトラッシュし、ワザも力も使わない（v0.67）。``attack_power`` は結果を変えない。"""

    def test_non_basic_is_discarded(self):
        for real, energies in ((LANTURN, (L, L)), (H.BROCKS_NINETALES, (R, R))):
            with self.subTest(real=real):
                state = valid(self, fd(real, energies, opponent=lanturn()))
                plain = accepted_once(self, state, UseAttack(0, 0))
                self.assertEqual([e["kind"] for e in plain.log[len(state.log):]], ["secret_plan_revealed", "secret_plan_discarded"])
                self.assertEqual((plain.players[0].active, plain.decision.kind, snap(plain)[1]), (None, "promote_active", snap(state)[1]))
                if real == LANTURN:
                    self.assertEqual(snap(accepted_once(self, state, UseAttack(0, 0, attack_power=True))), snap(plain))


class InformationBoundaryTest(unittest.TestCase):
    """公開のカードが同じで、相手の秘密（手札・うらのベンチの正体）だけが違うとき、本人の結果と本人に見えるログは同じ（結果の値には依らない性質）。"""

    def test_opponent_secret_does_not_change_the_result(self):
        variants = (dict(opponent_hand=(H.FIRE,)), dict(opponent_hand=(H.GRASS,)), dict(opponent_face_down=H.RATTATA), dict(opponent_face_down=H.LAPRAS))
        rows = []
        for extra in variants:
            state = valid(self, with_coin_bits(fd(DITTO, (W, W), opponent=mon(H.LAPRAS, (W,)), **extra), TL, TL))
            done = accepted_once(self, state, UseAttack(0, 1))
            rows.append((damages(state, done), [e["kind"] for e in visible_log(done, 0)[len(visible_log(state, 0)):]], snap(done)[1]))
        self.assertEqual(rows[0], rows[1])
        self.assertEqual(rows[2], rows[3])


if __name__ == "__main__":
    unittest.main()

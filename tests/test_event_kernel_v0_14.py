"""v0.14: 汎用のイベント・効果の解決の仕組みのプロトタイプ（v0.14 は experiments/event_kernel。v0.15b から本番の解決の基盤
``kyuura_engine.resolution``。v0.16d で v0.14 の名前の互換の層を外した）の単体テスト（docs/event-prototype-verification-v0.14.md）。

どのテストも、同じ状態・同じ乱数・同じコマンドを v0.13 のエンジン（v0.15 からは経路 ``Route.LEGACY``）とプロトタイプ（v0.15 からは本番の解決の基盤。経路 ``KERNEL``）に渡し、状態（形式 9。
ログ・乱数の指紋・決定を含む）か拒否（例外の種類とコード）が同じことを確かめる（``Both``）。v0.16a から、v0.13 の結果は、旧経路がある木で
記録した参照データ（tests/legacy_reference.py。呼び出しごとの盤面の指紋と旧経路の結果）と比べる（v0.16 で旧経路を外しても比べられる）。そのうえで、プロトタイプの解決の記録（内部の
イベント）で、共通の仕組みが窓・枠・候補を管理したことを確かめる。原典の根拠は v0.9〜v0.13 の各文書（裁定の番号）で、プロトタイプは
裁定を変えない。

- 5 系統の効果: とうめい（ダメージ・効果を受ける前。p.159・p.160。T1〜）、はんげき（ダメージを受けたあと。p.192。C1〜）、こんじょう
  （きぜつの前の任意の効果。p.193。G1〜）、ふしちょう（きぜつのあとの任意の効果。p.82。P1〜）、こうらがえし（番をまたぐ効果と返す
  ダメージ。p.89。S1〜）と、ほのおのかべ（p.82。W1〜）・かたまる（p.18）・かがくへんかガス（p.48。G1〜）。
"""

from __future__ import annotations

import copy
import pickle
import random
import sys
import unittest
from pathlib import Path

from kyuura_engine import (
    DEFAULT_EFFECTS, EndTurn, EngineError, Phase, PromoteActive, ResolveDecision, TakePrize, UseAttack,
    check_invariants, state_to_dict,
)
from kyuura_engine.decisions import FORCED_SWITCH, KO_PREVENTION, POST_KNOCKOUT_POWER
from kyuura_engine.effects import AttackKey
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    BUTTERFREE, DARK_WARTORTLE, DODUO, FIGHTING, FIRE, GASTLY, GIOVANNIS_MACHAMP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHOP, GRASS, H,
    HAUNTER, LIGHTNING, MACHAMP, MACHOKE, MACHOP, METAPOD, MUK, PARAS, PIKACHU, PLUSPOWER, PONYTA, PSYCHIC, RATTATA,
    ROCKET_SQUIRTLE, ROCKETS_MOLTRES, T, WEEDLE, ATTACK_TYPES_SINCE_V0_17, build_test_state, with_coin_results,
)
from tests import legacy_reference
from tests.log_audit import log_problems, serialization_problems

# v0.16d: v0.14 の名前の互換の層（experiments.event_kernel）を外したので、本番の解決の基盤と内部の入口を直接使う
from kyuura_engine.engine import apply_command_traced, apply_command_with
from kyuura_engine.resolution import BUILDERS, PREFLIGHT_MODES
from kyuura_engine.resolution import catalog as C
from kyuura_engine.resolution import codec
from kyuura_engine.resolution import events as EV
from kyuura_engine.resolution import kernel as KN
from kyuura_engine.resolution.questions import QUESTIONS

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

TURN = 7  # プレイヤー 0 の番（先攻はプレイヤー 0）。プレイヤー 1 は 6 番に効果を受けた
CATERPIE_ = "PMCG1-002"
GRIMER_ = "PMCG4-004"
MUK_ON_BENCH = {"card": MUK, "evolved_from": GRIMER_}
HAUNTER_ = {"card": HAUNTER, "evolved_from": GASTLY}
MACHAMP_ = {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE]}
GIOVANNI_ = {"card": GIOVANNIS_MACHAMP, "evolved_from": [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE]}
DARK_ = {"card": DARK_WARTORTLE, "evolved_from": ROCKET_SQUIRTLE}
BUTTERFREE_ = {"card": BUTTERFREE, "evolved_from": [CATERPIE_, METAPOD]}
METAPOD_ = {"card": METAPOD, "evolved_from": CATERPIE_}
PONYTA_ = {"card": PONYTA, "energy": [FIRE, FIRE]}  # けりとばす 20・ほのおのしっぽ 30（炎。弱点 水）


def full(state):
    return state_to_dict(state, format_version=9)


def board(attacker, defender, *, attacker_bench=(RATTATA,), defender_bench=(RATTATA,), turn=TURN, **kwargs):
    return build_test_state([
        {"active": attacker, "bench": list(attacker_bench)},
        {"active": defender, "bench": list(defender_bench)},
    ], turn_number=turn, **kwargs)


class Both(unittest.TestCase):
    """v0.13 とプロトタイプに同じコマンドを渡して比べる。"""

    def both(self, state, command, *, mode="derived"):
        before, rng = full(state), rng_fingerprint(state.rng)
        expected = legacy_reference.expected(self, state, command)  # v0.13 の結果（v0.16a から参照データ）
        try:
            (actual, trace), actual_error = apply_command_traced(state, command, preflight=mode), None
        except EngineError as error:
            actual, trace, actual_error = None, None, error
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, rng), "渡した状態が変わった")
        if expected[0] == "error":
            self.assertIsNotNone(actual_error, f"v0.13 は {expected[2]} で拒否したが、プロトタイプは受け付けた")
            # 例外の種類・コード・理由の文（v0.15b から理由の文も同じ。止める理由の文を effects の共通の関数で作る。
            # docs/kernel-integration-v0.15b.md 5 章）
            self.assertEqual(legacy_reference.error_outcome(actual_error), expected)
            return None, None, actual_error
        self.assertIsNone(actual_error, f"v0.13 は受け付けたが、プロトタイプは {actual_error!r}")
        self.assertEqual(("ok", legacy_reference.digest(actual)), expected)  # 形式 9 の全体（ログ・乱数の指紋・決定を含む）
        return actual, trace, None

    def activated(self, trace, window=None):
        return [(e.window.value, e.definition) for e in trace.of(EV.Activated) if window is None or e.window is window]

    def frames(self, trace):
        return [(e.frame.kind.value, None if e.frame.parent is None else e.frame.parent) for e in trace.of(EV.FrameOpened)]


# ---------------------------------------------------------------- 5 系統の効果とほのおのかべ・かたまる・かがくへんかガス


class FamilyTest(Both):
    def test_transparency_before_damage(self):
        """とうめい（T2・T4・T5）: ダメージを受ける前の窓で、ゴースト側のコイン。「おもて」なら受けない。"""
        for side in (H, T):
            with self.subTest(side=side):
                state = with_coin_results(board(PONYTA_, HAUNTER_), side)
                new, trace, _ = self.both(state, UseAttack(0, 0))
                self.assertEqual(self.activated(trace), [("before_damage", "transparency")])
                self.assertEqual(len(trace.of(EV.DamageEvaded)), 1 if side is H else 0)

    def test_transparency_before_effect(self):
        """とうめい（T22）: ダメージのないワザ（キノコのほうし）の効果の要素の前の窓。"""
        for side in (H, T):
            with self.subTest(side=side):
                # 2 枚目はポケモンチェックのねむりのコイン（「うら」でねむりのまま）
                state = with_coin_results(board({"card": PARAS, "energy": [GRASS, GRASS]}, HAUNTER_), side, T)
                new, trace, _ = self.both(state, UseAttack(0, 1))
                self.assertEqual(self.activated(trace), [("before_effect", "transparency")])
                self.assertEqual(new.players[1].active.conditions.asleep, side is T)

    def test_strikes_back_after_damage_elements(self):
        """はんげき（C2・C3・C13）: 受けたときに候補 → ダメージの要素のあとの窓で、特殊能力のダメージの枠を起こす。"""
        new, trace, _ = self.both(board(PONYTA_, MACHAMP_), UseAttack(0, 1))
        self.assertEqual(self.activated(trace), [("after_damage_elements", "strikes_back")])
        self.assertEqual([k for k, _ in self.frames(trace)], ["attack", "power_damage"])
        self.assertEqual(new.players[0].active.damage, 10)

    def test_guts_offer_before_knock_out(self):
        """こんじょう（G2・G10・G32）: ワザの要素のあと・きぜつの処理の前の窓で、持ち主に決定（v0.13 と同じ形の決定）。"""
        new, trace, _ = self.both(board(PONYTA_, {**GIOVANNI_, "damage": 80}), UseAttack(0, 1))
        self.assertEqual(new.decision.kind, KO_PREVENTION)
        self.assertEqual([(e.resume, e.kind) for e in trace.of(EV.Suspended)], [("knock_out", KO_PREVENTION)])
        pid = new.decision.options[0]
        for choices, side in (((pid,), H), ((pid,), T), ((), H)):
            with self.subTest(choices=choices, side=side):
                answered, _, _ = self.both(with_coin_results(new, side), ResolveDecision(1, new.decision.id, choices))
                survived = any(e["kind"] == "ko_prevented" for e in answered.log)
                self.assertEqual(survived, bool(choices) and side is H)

    def test_rebirth_after_judge(self):
        """ふしちょう（P1・P2・P27〜P30 の正規化）: きぜつの処理の前に写し、サイド → 勝ち負け → 決定 → 交代。"""
        state, trace, _ = self.both(board(PONYTA_, {"card": ROCKETS_MOLTRES, "damage": 40}), UseAttack(0, 1))
        self.assertEqual([e.definition for e in trace.of(EV.CandidateFound) if e.window is EV.Window.KO_PROCESS], ["rebirth"])
        state, _, _ = self.both(state, TakePrize(0, 0))
        self.assertEqual(state.decision.kind, POST_KNOCKOUT_POWER)
        for choices in ((state.decision.options[0],), ()):
            with self.subTest(choices=choices):
                answered, _, _ = self.both(state, ResolveDecision(1, state.decision.id, choices))
                moltres = next(uid for uid in answered.cards if answered.cards[uid].card_id == ROCKETS_MOLTRES)
                self.assertEqual(moltres in answered.players[1].hand, bool(choices))
                self.both(answered, PromoteActive(1, answered.players[1].bench[0].card))

    def test_fire_wall_fixed_retaliation(self):
        """ほのおのかべ（W11・W20）: 返す効果の枠（ワザの分類）で 10 を与える。"""
        new, trace, _ = self.both(board(PONYTA_, {"card": ROCKETS_MOLTRES, "retaliation": TURN - 1}), UseAttack(0, 1))
        self.assertEqual(self.activated(trace), [("after_damage_elements", "retaliation")])
        self.assertEqual([k for k, _ in self.frames(trace)], ["attack", "retaliation"])

    def test_shell_attack_returns_received_damage(self):
        """こうらがえし（S9・S10・S20〜S22）: 受けたダメージ（最終ダメージ。弱点のあと）を基本となるダメージにして返す。"""
        pikachu = {"card": PIKACHU, "energy": [LIGHTNING, LIGHTNING]}
        new, trace, _ = self.both(board(pikachu, {**DARK_, "retaliation_received": TURN - 1}), UseAttack(0, 0))
        event = next(e for e in new.log if e["kind"] == "retaliation")
        self.assertEqual((event["received_damage"], event["amount"]), (20, 20))  # かじる 10 × 弱点 2
        self.assertEqual([k for k, _ in self.frames(trace)], ["attack", "retaliation"])

    def test_harden_voids_damage(self):
        """かたまる（p.321）: ダメージの適用の前の窓で、要素を無効にする（計算しない）。"""
        new, trace, _ = self.both(board(PONYTA_, {**METAPOD_, "prevent_damage": TURN - 1}), UseAttack(0, 1))
        self.assertEqual(len(trace.of(EV.DamageVoided)), 1)
        self.assertEqual(new.players[1].active.damage, 0)

    def test_chemical_gas_suppresses_automatic_powers(self):
        """かがくへんかガス（G4・C24・T14）: 印刷された特殊能力から来る候補を、同じ 1 か所で今の状態から抑止する（ベンチのベトベトンでも）。"""
        new, trace, _ = self.both(board(PONYTA_, MACHAMP_, attacker_bench=(MUK_ON_BENCH,)), UseAttack(0, 1))
        self.assertEqual(self.activated(trace), [])
        new, trace, _ = self.both(board(PONYTA_, HAUNTER_, attacker_bench=(MUK_ON_BENCH,)), UseAttack(0, 1))
        self.assertEqual(self.activated(trace), [])

    def test_persistent_effects_are_not_suppressed_by_gas(self):
        """ほのおのかべはワザの効果なので、かがくへんかガスでは止まらない（W7・W18）。"""
        holder = {"card": ROCKETS_MOLTRES, "retaliation": TURN - 1}
        new, trace, _ = self.both(board(PONYTA_, holder, attacker_bench=(MUK_ON_BENCH,)), UseAttack(0, 1))
        self.assertEqual(self.activated(trace), [("after_damage_elements", "retaliation")])


# ---------------------------------------------------------------- 特殊状態・かがくへんかガスと、効果の発生源


STATUSES = {"sleep": {"sleep": True}, "paralysis": {"paralysis": TURN - 1}, "confusion": {"confusion": True}, "poison": {"poison": 10}}


class StatusAndSourceTest(Both):
    """特殊状態（ねむり・マヒ・こんらんで止まり、どくは関係しない）と、かがくへんかガス・効果の発生源（印刷された特殊能力・ワザの効果）の
    扱いが v0.13 と同じで、同じ 1 か所（catalog の定義の項目と共通の判定）で決まること。"""

    def test_status_at_the_window_for_transparency_and_strikes_back(self):
        """とうめい（T9〜T12）・はんげき（C19〜C22）: ねむり・マヒ・こんらんならはたらかない。どくは関係しない。"""
        for status, spec in STATUSES.items():
            for holder, name in ((MACHAMP_, "strikes_back"), (HAUNTER_, "transparency")):
                with self.subTest(status=status, effect=name):
                    new, trace, _ = self.both(with_coin_results(board(PONYTA_, {**holder, **spec}), H, H), UseAttack(0, 1))
                    self.assertEqual([d for _, d in self.activated(trace)], [name] if status == "poison" else [])

    def test_status_when_damaged_for_guts(self):
        """こんじょう（G25〜G29）: 「ダメージを受けるとき、すでに」ねむり・マヒ・こんらんなら使えない（決定を出さない）。どくは関係しない。"""
        for status, spec in STATUSES.items():
            with self.subTest(status=status):
                new, trace, _ = self.both(board(PONYTA_, {**GIOVANNI_, "damage": 80, **spec}), UseAttack(0, 1))
                offered = new.decision is not None and new.decision.kind == KO_PREVENTION
                self.assertEqual(offered, status == "poison")
                found = [e.definition for e in trace.of(EV.CandidateFound) if e.window is EV.Window.KO_CHECK]
                self.assertEqual(found, ["guts"] if status == "poison" else [])

    def test_status_when_knocked_out_for_rebirth(self):
        """ふしちょう（P13〜P16）: ねむり・マヒ・こんらんのまま「きぜつ」したら使えない（きぜつの処理の前の写し）。どくは関係しない。"""
        for status, spec in STATUSES.items():
            with self.subTest(status=status):
                new, trace, _ = self.both(board(PONYTA_, {"card": ROCKETS_MOLTRES, "damage": 40, **spec}), UseAttack(0, 1))
                found = [e.definition for e in trace.of(EV.CandidateFound) if e.window is EV.Window.KO_PROCESS]
                self.assertEqual(found, ["rebirth"] if status == "poison" else [])
                answered, _, _ = self.both(new, TakePrize(0, 0))
                self.assertEqual(answered.decision.kind == POST_KNOCKOUT_POWER, status == "poison")

    def test_gas_stops_optional_powers(self):
        """かがくへんかガス（G31・P17）: こんじょう・ふしちょうも、同じ 1 か所の抑止で使えない（ベンチのベトベトン）。"""
        new, trace, _ = self.both(board(PONYTA_, {**GIOVANNI_, "damage": 80}, attacker_bench=(MUK_ON_BENCH,)), UseAttack(0, 1))
        self.assertNotEqual(getattr(new.decision, "kind", None), KO_PREVENTION)
        new, trace, _ = self.both(board(PONYTA_, {"card": ROCKETS_MOLTRES, "damage": 40}, attacker_bench=(MUK_ON_BENCH,)), UseAttack(0, 1))
        self.assertEqual([e for e in trace.of(EV.CandidateFound) if e.window is EV.Window.KO_PROCESS], [])

    def test_persistent_effects_ignore_status(self):
        """ほのおのかべ・こうらがえし（W7・S28）はワザの効果なので、持つポケモンの特殊状態では止まらない（発生源の分類）。"""
        for status, spec in STATUSES.items():
            for holder in ({"card": ROCKETS_MOLTRES, "retaliation": TURN - 1}, {**DARK_, "retaliation_received": TURN - 1}):
                with self.subTest(status=status, holder=holder["card"]):
                    new, trace, _ = self.both(board(PONYTA_, {**holder, **spec}), UseAttack(0, 0))
                    self.assertEqual(self.activated(trace), [("after_damage_elements", "retaliation")])

    def test_damage_class_decides_triggers(self):
        """こんらんの 20（こんらんの分類の枠）は、どの「ワザのダメージを受けたとき」の効果も起こさない（C5・W9）。"""
        for side in (T,):
            with self.subTest(side=side):
                attacker = {**MACHAMP_, "energy": [FIGHTING] * 4, "confusion": True}
                state = with_coin_results(board(attacker, {"card": ROCKETS_MOLTRES, "retaliation": TURN - 1}), side)
                new, trace, _ = self.both(state, UseAttack(0, 0))
                self.assertEqual([k for k, _ in self.frames(trace)], ["confusion"])
                self.assertEqual(self.activated(trace), [])


class SharedFilterTest(unittest.TestCase):
    """共通の判定を直接確かめる（今の対応カードでは、コマンドから起こらない場合）。v0.13 との比較ではなく、定義の項目の意味のテスト。"""

    def test_own_attack_damage_is_not_a_trigger(self):
        """「相手のワザによって」（by_opponent。C4・W8）: 自分のワザのダメージでは候補にならない。今の対応カードでは、自分のワザで自分に
        ダメージを与えるポケモン（ピカチュウ・ゴーリキー・サカキのゴーリキー・ゴース）は、はんげき・返す効果を持たない。"""
        state = board({**MACHAMP_, "energy": [FIGHTING] * 4}, RATTATA)
        machamp, rattata = state.players[0].active, state.players[1].active
        res = KN.Resolution(state)
        own = res.open_frame(EV.FrameKind.ATTACK, parent=None, player=0, source_pid=machamp.pokemon_id, attack_key=AttackKey(MACHAMP, 0))
        self.assertEqual(KN.receiving(res, own, 0, machamp, 20), [])
        opponents = res.open_frame(EV.FrameKind.ATTACK, parent=None, player=1, source_pid=rattata.pokemon_id, attack_key=AttackKey(RATTATA, 0))
        self.assertEqual([d.instance.name for d in KN.receiving(res, opponents, 0, machamp, 20)], ["strikes_back"])

    def test_persistent_effect_works_only_on_its_turn(self):
        """持続する効果は、はたらく番（active_turn）だけはたらく（p.82・p.89「次の相手の番」）。効果を与えた番のうちに、持つポケモンが
        相手のワザのダメージを受けることは対戦では起こらない。"""
        import dataclasses
        state = board(PONYTA_, {"card": ROCKETS_MOLTRES, "retaliation": TURN - 1})
        moltres = state.players[1].active
        [instance] = [i for i in C.instances(state, 1, moltres) if i.definition is C.RETALIATION]
        self.assertTrue(C.working(state, instance, moltres))
        later = dataclasses.replace(instance, implementation=dataclasses.replace(instance.implementation, active_turn=TURN + 1))
        self.assertFalse(C.working(state, later, moltres))


# ---------------------------------------------------------------- 組み合わせ・順番


class CombinationTest(Both):
    def test_retaliation_triggers_strikes_back_in_a_nested_frame(self):
        """ほのおのかべのダメージ（ワザの分類）を受けたカイリキーのはんげき（W20）: 返す効果の枠の中で、特殊能力のダメージの枠を起こす。"""
        attacker = {**MACHAMP_, "energy": [FIGHTING] * 4}
        new, trace, _ = self.both(board(attacker, {"card": ROCKETS_MOLTRES, "retaliation": TURN - 1}), UseAttack(0, 0))
        frames = self.frames(trace)
        self.assertEqual([k for k, _ in frames], ["attack", "retaliation", "power_damage"])
        self.assertEqual(frames[2][1], 2)  # はんげきの枠の親は返す効果の枠

    def test_transparency_of_the_attacker_against_returned_damage(self):
        """返すダメージを受けるゴーストのとうめい（W19）: 返す効果の枠で 1 回（ワザの枠とは別の記録）。"""
        haunter = {**HAUNTER_, "energy": [PSYCHIC, PSYCHIC]}
        for side in (H, T):
            with self.subTest(side=side):
                state = with_coin_results(board(haunter, {"card": ROCKETS_MOLTRES, "retaliation": TURN - 1}), side)
                new, trace, _ = self.both(state, UseAttack(0, 0))
                self.assertIn(("before_damage", "transparency"), self.activated(trace))

    def test_window_opens_before_the_effect_element(self):
        """どくばり（ダメージ → コイン → どく）: はんげきは、どくの要素のコインの前（p.89。要素の分類から仕組みが窓を開く）。"""
        weedle = {"card": WEEDLE, "energy": [GRASS]}
        for side in (H, T):
            with self.subTest(side=side):
                new, trace, _ = self.both(with_coin_results(board(weedle, MACHAMP_), side), UseAttack(0, 0))
                order = [type(e).__name__ for e in trace.events if isinstance(e, (EV.WindowOpened, EV.ElementStarted))]
                window = next(i for i, e in enumerate(trace.events)
                              if isinstance(e, EV.WindowOpened) and e.window is EV.Window.AFTER_DAMAGE_ELEMENTS)
                effect = next(i for i, e in enumerate(trace.events) if isinstance(e, EV.ElementStarted) and e.phase == "effect")
                self.assertLess(window, effect, order)
                kinds = [e["kind"] for e in new.log]
                self.assertLess(kinds.index("counterattack"), max(i for i, k in enumerate(kinds) if k == "coin_flip"))

    def test_window_at_the_end_after_self_damage(self):
        """でんげき（相手へのダメージ → コイン → 自分へのダメージ）: はんげきは自分へのダメージのあと（C29。コインは自分へのダメージの要素）。"""
        pikachu = {"card": PIKACHU, "energy": [LIGHTNING, LIGHTNING]}
        for side in (H, T):
            with self.subTest(side=side):
                new, trace, _ = self.both(with_coin_results(board(pikachu, MACHAMP_), side), UseAttack(0, 1))
                log = new.log
                counter = next(i for i, e in enumerate(log) if e["kind"] == "counterattack")
                damage = [i for i, e in enumerate(log) if e["kind"] == "damage" and i < counter]
                coin = max(i for i, e in enumerate(log) if e["kind"] == "coin_flip")
                self.assertLess(coin, counter)  # ワザのコインのあと
                self.assertEqual(len(damage), 2 if side is T else 1)  # 「うら」なら自分への 10 のあと
                if side is T:
                    self.assertEqual(log[damage[-1]]["player"], 0)
                windows = [e for e in trace.of(EV.WindowOpened) if e.window is EV.Window.AFTER_DAMAGE_ELEMENTS]
                self.assertEqual(len(windows), 1)

    def test_forced_switch_after_strikes_back_and_resume(self):
        """ふきとばし（C16）: はんげきを与えてから決定（決定を出す前に送る効果は空）。決定のあとは決定を出した要素の続きから。"""
        butterfree = {**BUTTERFREE_, "energy": [GRASS, GRASS]}
        new, trace, _ = self.both(board(butterfree, MACHAMP_), UseAttack(0, 0))
        self.assertEqual(new.decision.kind, FORCED_SWITCH)
        self.assertEqual(self.activated(trace), [("after_damage_elements", "strikes_back")])
        self.both(new, ResolveDecision(1, new.decision.id, (new.decision.options[0],)))

    def test_drain_is_skipped_when_the_attacker_is_knocked_out_by_strikes_back(self):
        """メガドレイン（C16）: はんげきできぜつしたワザを使ったポケモンの回復は処理しない。"""
        butterfree = {**BUTTERFREE_, "energy": [GRASS] * 4, "damage": 60}
        new, _, _ = self.both(board(butterfree, MACHAMP_), UseAttack(0, 1))
        self.assertIn("drain_heal_skipped", [e["kind"] for e in new.log])


# ---------------------------------------------------------------- 持続する効果の失効・きぜつの前後


class TimingTest(Both):
    def test_retaliation_expires_at_the_end_of_the_turn(self):
        """ほのおのかべは次の相手の番の終わりに消える（p.89 の解説。番の終わりの窓）。"""
        new, trace, _ = self.both(board(PONYTA_, {"card": ROCKETS_MOLTRES, "retaliation": TURN - 1}), EndTurn(0))
        self.assertIn(EV.Window.TURN_END, [e.window for e in trace.of(EV.WindowOpened)])
        self.assertEqual(new.players[1].active.persistent_effects, ())

    def test_game_ending_knock_out_offers_no_rebirth(self):
        """勝ち負けが決まるなら、ふしちょうを決めさせない（v0.12 の正規化）。"""
        state = build_test_state([
            {"active": PONYTA_, "bench": [RATTATA], "prizes": 1},
            {"active": {"card": ROCKETS_MOLTRES, "damage": 40}, "bench": [RATTATA]},
        ], turn_number=TURN)
        state, _, _ = self.both(state, UseAttack(0, 1))
        state, _, _ = self.both(state, TakePrize(0, 0))
        self.assertIs(state.phase, Phase.GAME_OVER)

    def test_poison_knock_out_in_pokemon_check_goes_through_the_same_window(self):
        """どくのきぜつでも、ふしちょうを使える（P9・P16）。ポケモンチェックの中のきぜつも、同じきぜつの処理の窓を通る。"""
        state = build_test_state([
            {"active": PONYTA_, "bench": [RATTATA]},
            {"active": {"card": ROCKETS_MOLTRES, "damage": 50, "poison": 10}, "bench": [RATTATA]},
        ], turn_number=TURN)
        new, trace, _ = self.both(state, EndTurn(0))
        self.assertEqual([e.definition for e in trace.of(EV.CandidateFound) if e.window is EV.Window.KO_PROCESS], ["rebirth"])


# ---------------------------------------------------------------- 中断・再開・保存


class SuspendResumeTest(Both):
    def decision_states(self):
        forced, _, _ = self.both(board({**BUTTERFREE_, "energy": [GRASS, GRASS]}, MACHAMP_), UseAttack(0, 0))
        guts, _, _ = self.both(board(PONYTA_, {**GIOVANNI_, "damage": 80}), UseAttack(0, 1))
        rebirth, _, _ = self.both(board(PONYTA_, {"card": ROCKETS_MOLTRES, "damage": 40}), UseAttack(0, 1))
        rebirth, _, _ = self.both(rebirth, TakePrize(0, 0))
        return {"forced_switch": forced, "ko_prevention": guts, "post_knockout_power": rebirth}

    def test_codec_round_trip(self):
        """続きの情報は v0.13 の決定と同じ形で、決定から作り直せる（書き出しの形式 9 のまま）。"""
        for name, state in self.decision_states().items():
            with self.subTest(name=name):
                cont = codec.decode(state.decision)
                self.assertIsNotNone(cont)
                data = full(state)["decision"]
                self.assertEqual(data["resume"], state.decision.resume)

    def test_save_and_resume_with_either_engine(self):
        """pickle・deepcopy・clone で保存した決定の状態を、どちらのエンジンで再開しても同じ。"""
        for name, state in self.decision_states().items():
            d = state.decision
            for label, saved in (("pickle", pickle.loads(pickle.dumps(state))), ("deepcopy", copy.deepcopy(state)), ("clone", state.clone())):
                with self.subTest(name=name, saved=label):
                    choices = (d.options[0],) if d.max_choices else ()
                    self.both(saved, ResolveDecision(d.player, d.id, choices))


# ---------------------------------------------------------------- 原典で決められない場合（先読み）


class UnresolvedTest(Both):
    """既知の問いは、v0.13 の止める関数（legacy）と、仕組みの共通の検出（derived）のどちらでも、v0.13 と同じコードで宣言の前に止まる。"""

    CASES = {
        "C18": (lambda: board({**PONYTA_, "damage": 30}, {**MACHAMP_, "damage": 80}), UseAttack(0, 1), "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT"),
        "W24": (lambda: board({**PONYTA_, "damage": 30}, {"card": ROCKETS_MOLTRES, "damage": 30, "retaliation": TURN - 1}), UseAttack(0, 1),
                "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT"),
        "S37": (lambda: board(PONYTA_, {**DARK_, "damage": 30, "retaliation_received": TURN - 1}), UseAttack(0, 1),
                "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT"),
        "G37": (lambda: board({"card": WEEDLE, "energy": [GRASS]}, {**GIOVANNI_, "damage": 90}), UseAttack(0, 0),
                "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT"),
        "T19b": (lambda: board({"card": WEEDLE, "energy": [GRASS]}, HAUNTER_), UseAttack(0, 0), "UNRESOLVED_EVADED_EFFECT_COIN"),
        "prevented_coin": (lambda: board({"card": DODUO, "energy": [FIRE]}, {**METAPOD_, "prevent_damage": TURN - 1}), UseAttack(0, 0),
                           "UNRESOLVED_PREVENTED_COIN_DAMAGE"),
        "confusion_modifiers": (lambda: board({**PONYTA_, "confusion": True, "trainers": [(PLUSPOWER, TURN)]}, RATTATA), UseAttack(0, 1),
                                "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS"),
    }

    def test_same_code_in_both_modes(self):
        for name, (make, command, code) in self.CASES.items():
            for mode in PREFLIGHT_MODES:
                with self.subTest(case=name, mode=mode):
                    _, _, error = self.both(make(), command, mode=mode)
                    self.assertIsNotNone(error)
                    self.assertEqual(error.code, code)

    def test_derived_preflight_reports_the_question(self):
        """先読みは、コインのすべての結果を試し、当たった問いを解決の記録に残す（勝者・順番を推測で決めない）。"""
        make, command, code = self.CASES["C18"]
        with self.assertRaises(EngineError):
            apply_command_traced(make(), command)
        from kyuura_engine.resolution import preflight as P
        state = make()

        def body(res):
            from kyuura_engine.resolution.flow import _attack_body
            from kyuura_engine.resolution.programs import compile_attack
            attacker = res.state.players[0].active
            attack = res.state.card_def(attacker.card).attacks[1]
            effect = res.state.effects.attack_effect(PONYTA, attack)
            _attack_body(res, 0, attacker, AttackKey(PONYTA, 1), attack, compile_attack(effect))

        found, branches = P.explore(state, body, C.DEFAULT_CATALOG)
        self.assertEqual(set(found), {"counterattack_double_knockout"})
        self.assertGreaterEqual(branches, 1)
        self.assertEqual(QUESTIONS["counterattack_double_knockout"].code, code)

    def test_two_questions_use_the_v0_13_order(self):
        """2 つの問いに当たる（こんらんの「うら」でこんらんの変更効果、「おもて」で C18）ときは、v0.13 の確認の順番（こんらんの変更効果が
        先）のコードで止める。勝者・順番を決めるための優先ではなく、どのコードで止めるかだけを決める。"""
        attacker = {**PONYTA_, "damage": 30, "confusion": True, "trainers": [(PLUSPOWER, TURN)]}
        for mode in PREFLIGHT_MODES:
            with self.subTest(mode=mode):
                _, _, error = self.both(board(attacker, {**MACHAMP_, "damage": 80}), UseAttack(0, 1), mode=mode)
                self.assertEqual(error.code, "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS")
        from kyuura_engine.resolution import preflight as P
        from kyuura_engine.resolution.flow import _attack_body
        from kyuura_engine.resolution.programs import compile_attack
        state = board(attacker, {**MACHAMP_, "damage": 80})

        def body(res):
            pokemon = res.state.players[0].active
            attack = res.state.card_def(pokemon.card).attacks[1]
            _attack_body(res, 0, pokemon, AttackKey(PONYTA, 1), attack, compile_attack(res.state.effects.attack_effect(PONYTA, attack)))

        found, _ = P.explore(state, body, C.DEFAULT_CATALOG)
        self.assertEqual(set(found), {"confusion_damage_modifiers", "counterattack_double_knockout"})

    def test_not_stopped_when_only_one_is_knocked_out(self):
        """片方だけのきぜつは止めない（過剰に止めない）。"""
        self.both(board({**PONYTA_, "damage": 30}, {**MACHAMP_, "damage": 0}), UseAttack(0, 1))
        self.both(board(PONYTA_, {**MACHAMP_, "damage": 80}), UseAttack(0, 1))


# ---------------------------------------------------------------- 連鎖・原子性・記録


class ChainAndAtomicityTest(Both):
    def test_power_damage_triggers_nothing(self):
        """はんげきのダメージ（特殊能力の分類）は、相手のカイリキーのはんげきを起こさない（C13・C14。発生源の分類で止まる）。"""
        attacker = {**MACHAMP_, "energy": [FIGHTING] * 4}
        new, trace, _ = self.both(board(attacker, MACHAMP_), UseAttack(0, 0))
        self.assertEqual(self.activated(trace), [("after_damage_elements", "strikes_back")])

    def test_chain_outside_the_spawn_table_is_refused(self):
        """枠の表（events.SPAWNS）にない連鎖は、回数の上限ではなく表で止める（S45・C14）。返す効果の枠からは返す効果の枠を開けない。"""
        res = KN.Resolution(board(PONYTA_, MACHAMP_), catalog=C.DEFAULT_CATALOG, trace=EV.Trace())
        key = AttackKey(PONYTA, 1)
        attack = res.open_frame(EV.FrameKind.ATTACK, parent=None, player=0, source_pid=1, attack_key=key)
        returned = res.open_frame(EV.FrameKind.RETALIATION, parent=attack.frame.id, player=1, source_pid=2, attack_key=key)
        power = res.open_frame(EV.FrameKind.POWER_DAMAGE, parent=returned.frame.id, player=0, source_pid=1, attack_key=key)
        for parent, kind in ((returned, EV.FrameKind.RETALIATION), (power, EV.FrameKind.POWER_DAMAGE), (power, EV.FrameKind.RETALIATION)):
            with self.subTest(parent=parent.frame.kind, kind=kind), self.assertRaises(RuntimeError):
                res.open_frame(kind, parent=parent.frame.id, player=0, source_pid=1, attack_key=key)

    def test_the_spawn_table_governs_the_real_flow(self):
        """表から 1 つの組を除くと、その連鎖の起こる盤面（ほのおのかべのダメージで、はんげき）が RuntimeError になり、渡した状態は変わらない。"""
        attacker = {**MACHAMP_, "energy": [FIGHTING] * 4}
        state = board(attacker, {"card": ROCKETS_MOLTRES, "retaliation": TURN - 1})
        before = full(state)
        original = EV.SPAWNS[EV.FrameKind.RETALIATION]
        EV.SPAWNS[EV.FrameKind.RETALIATION] = frozenset()
        try:
            with self.assertRaises(RuntimeError):
                apply_command_with(state, UseAttack(0, 0))
        finally:
            EV.SPAWNS[EV.FrameKind.RETALIATION] = original
        self.assertEqual(full(state), before)
        apply_command_with(state, UseAttack(0, 0))  # 表をもどせば受け付ける

    def test_illegal_commands_are_atomic(self):
        """不正なコマンドは、v0.13 と同じコードで拒否し、状態・乱数・ログを変えない。"""
        state = board(PONYTA_, MACHAMP_)
        for command in (UseAttack(1, 0), UseAttack(0, 5), UseAttack(0, "x"), EndTurn(1), TakePrize(0, 0),
                        ResolveDecision(0, 1, ())):
            with self.subTest(command=command):
                _, _, error = self.both(state, command)
                self.assertIsNotNone(error)
        decision, _, _ = self.both(board(PONYTA_, {**GIOVANNI_, "damage": 80}), UseAttack(0, 1))
        d = decision.decision
        for command in (ResolveDecision(0, d.id, ()), ResolveDecision(1, d.id + 1, ()), ResolveDecision(1, d.id, (999,)),
                        ResolveDecision(1, d.id, (d.options[0], d.options[0])), PromoteActive(1, 0), UseAttack(0, 1)):
            with self.subTest(command=command):
                _, _, error = self.both(decision, command)
                self.assertIsInstance(error, EngineError)

    def test_internal_error_leaves_the_state_unchanged(self):
        """処理の途中の誤り（注入）でも、渡した状態は変わらない（複製の上で処理する）。"""
        state = board(PONYTA_, MACHAMP_)
        before, rng = full(state), rng_fingerprint(state.rng)
        original = KN.ACTIONS["power_damage_to_damage_source"]

        def broken(res, fs, deferred):
            res.state.players[0].active.damage += 10
            raise RuntimeError("注入した誤り")

        KN.ACTIONS["power_damage_to_damage_source"] = broken
        try:
            with self.assertRaises(RuntimeError):
                apply_command_with(state, UseAttack(0, 1))
        finally:
            KN.ACTIONS["power_damage_to_damage_source"] = original
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, rng))

    def test_trace_is_not_part_of_the_state(self):
        """解決の記録（内部のイベント）は状態に入らない。公開のログは v0.13 と同じ。"""
        state = board(PONYTA_, MACHAMP_)
        a = apply_command_with(state, UseAttack(0, 1))
        b, trace = apply_command_traced(state, UseAttack(0, 1))
        self.assertEqual(full(a), full(b))
        self.assertGreater(len(trace), 0)
        self.assertNotIn("trace", full(a))
        self.assertFalse(any(isinstance(e, EV.Activated) for e in a.log))


# ---------------------------------------------------------------- 対応表


class CatalogTest(unittest.TestCase):
    def test_every_registered_attack_has_a_program(self):
        """登録表のワザの実装（v0.13 の 24 種類と、v0.17 から加えた型）はすべて要素の並びに置きかえられる（効果のないワザとして処理する
        ものはない）。"""
        kinds = {type(entry.effect) for key in DEFAULT_EFFECTS.attack_keys() for entry in [DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)]}
        self.assertEqual(len(kinds), 24 + len(ATTACK_TYPES_SINCE_V0_17))
        self.assertTrue(set(ATTACK_TYPES_SINCE_V0_17) <= kinds)
        self.assertEqual(kinds - set(BUILDERS), set())

    def test_automatic_optional_and_continuous_powers_are_in_the_catalog(self):
        """宣言しない・決められたときに使う特殊能力は、対応表の 1 か所にある。宣言して使う特殊能力（v0.13 のエンジンが扱う）はない。

        v0.31 のカツラのキュウコンの「ほのおでかいふく」（``HealOnEnergyAttach``）は宣言しないが、はたらくのはエネルギーカードをつけたとき
        （``effects.after_energy_attached``）で、解決の基盤の窓（ワザ・きぜつ・番の終わり）の中ではないので、対応表に入れていない
        （docs/held-cards-v0.31.md）。v0.46 の常にはたらく特殊能力 8 つ（``effects.ContinuousPower``）も宣言しないが、窓の中ではたらく反応ではなく、ダメージの計算・
        「にげる」・トレーナーを使う・特殊状態にする処理が、その時点の場から問い合わせる（``effects.continuous_powers``。docs/continuous-powers-v0.46.md 2 章）ので、
        対応表に入れていない。v0.47 の常にはたらく特殊能力 3 つ（おみとおし・カブトアーマー・げんしのちから。観測・ダメージの計算・進化の入口が問い合わせる。
        docs/fossil-hidden-info-v0.47.md 4 章）も同じ。v0.48 のナツメのゴースの［ガスのからだ］（最大HP。HP を使う処理が ``effects.max_hp`` で問い合わせる。
        docs/effective-pokemon-properties-v0.48.md 2 章）も同じ。v0.49 のナツメのフーディンの［サイコリンク］（ワザの一覧。ワザを使う処理が
        ``effects.available_attacks`` で問い合わせる）・メタモンの［へんしん］（今の姿。``effects.current_form`` で問い合わせる。docs/virtual-attacks-transformation-v0.49.md
        2 章）も同じ。v0.60 のカスミのギャラドスの［はんこう］（ワザを使う時。p.309 の手順 4 として ``flow._attack_check_failed`` が問い合わせる。窓の中の反応ではない。
        docs/coins-defense-rebellion-v0.60.md 4 章）も同じ。ほかの宣言しない特殊能力は今までどおり対応表にあることを確かめる。"""
        outside_windows = ("heal_on_energy_attach",
                           # v0.46
                           "zero_large_damage_received", "cap_damage_from_basic", "halve_active_attack_damage", "bonus_damage_while_confused",
                           "reduce_own_active_retreat_cost", "increase_opponent_active_retreat_cost", "prevent_trainer_use", "special_condition_immunity",
                           # v0.47
                           "reveal_opponent_hand", "halve_damage_received", "prevent_evolution",
                           # v0.48
                           "max_hp_per_attached_energy_cards",
                           # v0.49
                           "attacks_of_own_type_pokemon", "transform_into_defender",
                           # v0.60
                           "fail_and_return_on_attack")
        for key in DEFAULT_EFFECTS.power_keys():
            effect = DEFAULT_EFFECTS.power_entry(key.card_id, key.power_index).effect
            definition = C.definition_for(effect, C.POWER_DEFINITIONS)
            with self.subTest(power=str(key)):
                expected = ((not effect.declared and effect.implementation_id not in outside_windows)
                            or effect.implementation_id in ("prevent_knock_out_on_heads", "return_to_hand_on_knock_out"))
                self.assertEqual(definition is not None, expected)
        self.assertEqual([str(k) for k in DEFAULT_EFFECTS.power_keys()
                          if DEFAULT_EFFECTS.power_entry(k.card_id, k.power_index).effect.implementation_id in outside_windows],
                         ["PMCG2-027@power0", "PMCG2-040@power0", "PMCG2-047@power0", "PMCG3-015@power0", "PMCG3-035@power0", "PMCG3-041@power0",
                          "PMCG3-042@power0", "PMCG4-007@power0", "PMCG4-010@power0", "PMCG4-041@power0", "PMCG5-035@power0", "PMCG5-063@power0", "PMCG6-010@power0",
                          "PMCG6-033@power0", "PMCG6-049@power0", "PMCG6-053@power0"])


# ---------------------------------------------------------------- 対戦（new_game から）: 再現性・ログの監査


class GameTest(unittest.TestCase):
    def play(self, scenario, seed, steps=400, *, chain=None):
        """``chain`` を渡すと、1 歩ごとの結果を v0.13 の結果の連なり（参照データ。v0.16a）と比べる（記録するときは旧経路で進めて記録する）。"""
        import compat_driver as driver
        import stress_engine as stress
        rng = random.Random(f"kyuura-stress:{scenario}:{seed}")
        spec = next(s for s in stress.ALL_SCENARIOS if s.name == scenario)
        state = __import__("kyuura_engine").new_game(driver._deck(spec.deck0), driver._deck(spec.deck1), seed)
        apply = legacy_reference.legacy_apply_for_recording if chain is not None and legacy_reference.recording() else apply_command_with
        for _ in range(steps):
            if state.phase in (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED):
                break
            command = stress.choose_command(state, rng, 0.05)
            try:
                new = apply(state, command)
            except EngineError as error:
                if chain is not None:
                    chain.add(state, command, legacy_reference.error_outcome(error))
                continue
            if chain is not None:
                chain.add(state, command, ("ok", legacy_reference.digest(new)))
            state = new
        if chain is not None:
            chain.finish()
        return state

    def test_reproducible_and_audited(self):
        """同じ seed で同じ結果（プロトタイプだけで進めても v0.13 と同じ。v0.16a から、v0.13 の 1 歩ごとの結果は参照データ）。ログの監査・
        書き出しの監査・不変条件に問題がない。"""
        for scenario, seed in (("machamp_mixed", 1), ("moltres_mixed", 2), ("wartortle_mixed", 3), ("giovanni_mixed", 4), ("haunter_muk", 5)):
            with self.subTest(scenario=scenario, seed=seed):
                a, b = self.play(scenario, seed), self.play(scenario, seed)
                self.assertEqual(full(a), full(b))
                reference = self.play(scenario, seed, chain=legacy_reference.Chain(f"{self.id()}:{scenario}:{seed}"))
                self.assertEqual(full(a), full(reference))
                self.assertEqual(log_problems(a), [])
                self.assertEqual(serialization_problems(a), [])
                self.assertEqual(check_invariants(a), [])


if __name__ == "__main__":
    unittest.main()

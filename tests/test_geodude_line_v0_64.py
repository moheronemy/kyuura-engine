"""v0.64: 化石の秘密のイシツブテの系統 3 枚と、「うら」が出るまで投げるコインの共通の処理・先読みの有限の組（docs/geodude-line-unbounded-coins-v0.64.md）。

根拠は kyuura データの採用（kyuura の印刷の文面。kyuura_engine/data/card_sources.json の PMCG3-034・037・038）と、v0.39 の SelfDestruct・v0.45 の
ZeroDamageBelowNextTurn・v0.2d の「おもて」の数 × のダメージの扱い（1 枚目が「うら」なら 0 で、ワザの失敗ではない）。誌面のページは読んでいない。
コインは ``with_coin_bits``（乱数の内部の状態を直接決める。seed を探さない）で決める。
"""

from __future__ import annotations

import pickle
import unittest
from typing import ClassVar
from unittest import mock

import kyuura_engine.effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.commands import ResolveDecision, UseAttack
from kyuura_engine.damage import (
    ADD,
    HALVE_DOWN,
    HALVE_UP,
    SET,
    ZERO_IF_BELOW,
    DamageModifier,
)
from kyuura_engine.decisions import KO_PREVENTION, SELECT_ATTACK
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackKey
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.resolution import kernel as K
from kyuura_engine.resolution import preflight, unbounded, v013_checks
from kyuura_engine.serialize import state_to_dict
from kyuura_engine.state import ZeroDamageBelow
from tests.helpers import (
    ATTACK_TYPES_SINCE_V0_17,
    BROCKS_MANKEY,
    BROCKS_PRIMEAPE,
    CLEFAIRY,
    DARK_WARTORTLE,
    DEFENDER,
    FIGHTING,
    FIRE,
    FOSSIL_GEODUDE,
    FOSSIL_GOLEM,
    FOSSIL_GRAVELER,
    GIOVANNIS_MACHAMP,
    GIOVANNIS_MACHOKE,
    GIOVANNIS_MACHOP,
    GRASS,
    KAKUNA,
    MR_MIME,
    ONIX,
    PIDGEOTTO,
    PIDGEY,
    PLUSPOWER,
    RATTATA,
    ROCKET_SQUIRTLE,
    WEEDLE,
    H,
    T,
    apply_kernel,
    build_test_state,
    rng_with_coin_bits,
    with_coin_bits,
)

MODES = ("derived", "derived_full", "legacy")
BELOW = {FOSSIL_GRAVELER: FOSSIL_GEODUDE, FOSSIL_GOLEM: [FOSSIL_GEODUDE, FOSSIL_GRAVELER], PIDGEOTTO: PIDGEY,
         GIOVANNIS_MACHAMP: [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], BROCKS_PRIMEAPE: BROCKS_MANKEY, DARK_WARTORTLE: ROCKET_SQUIRTLE}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active=None, opponent=None, *, bench=(), opponent_bench=(), turn=7):
    active = active or mon(FOSSIL_GEODUDE, (FIGHTING, FIGHTING))
    opponent = opponent or mon(ONIX)
    return build_test_state([{"active": active, "bench": list(bench)}, {"active": opponent, "bench": list(opponent_bench)}], turn_number=turn)


def coins(*heads_then_tail):
    return heads_then_tail


def run(state, heads, command=None, mode="derived", extra=()):
    command = command or UseAttack(0, 0)
    return apply_kernel(with_coin_bits(state, *([H] * heads + [T]), *extra), command, preflight=mode)


def events(state, since, kind):
    return [dict(e) for e in state.log[since:] if e["kind"] == kind]


def written(state):
    return state_to_dict(state, format_version=21), [dict(e) for e in state.log], repr(state.rng.getstate())


def captured_classes(state, command=None):
    """実際の処理（``derived``）が求めた「おもて」の数の組（先読みの範囲を記録する乱数が求める）。"""
    got = []
    real = unbounded.head_classes

    def wrap(*args, **kwargs):
        found = real(*args, **kwargs)
        got.append(found)
        return found

    with mock.patch.object(unbounded, "head_classes", wrap):
        try:
            apply_kernel(with_coin_bits(state, T), command or UseAttack(0, 0), preflight="derived")
        except UnsupportedError:
            pass
    return got[0]


def outcome(state, heads, mode, *, brute=None, command=None):
    """``heads`` 枚の「おもて」のあと「うら」で処理した結果。``brute`` なら、先読みが組の代表ではなく 0 〜 brute − 1 のすべての「おもて」の数を試す。"""
    patches = [mock.patch.object(preflight, "MAX_BRANCHES", 10 ** 6)]
    if brute is not None:
        patches.append(mock.patch.object(preflight.Oracle, "coin_run", lambda self, classes: self._next(brute)))
    for patch in patches:
        patch.start()
    try:
        new = run(state, heads, command, mode)
        return ("ok", [e["amount"] for e in events(new, len(state.log), "damage")])
    except UnsupportedError as error:
        return ("stop", error.code, str(error))
    finally:
        for patch in patches:
            patch.stop()


class synthetic_modifiers:
    """テスト専用: れんぞくいしなげのダメージ（相手の対戦ポケモンへ）に、変更効果 ``modifiers`` を足す（盤面を直接作った。今の写しにない計算の組み合わせ・
    順番の決定の確かめ）。実際の処理・先読み・不変条件が同じ ``effects.attack_damage_modifiers`` を読むので、両方に当てはめる。"""

    def __init__(self, *modifiers):
        self.modifiers = modifiers

    def __enter__(self):
        real = E.attack_damage_modifiers
        extra = self.modifiers

        def fake(state, attacker, defender, *, attack=None, **kwargs):
            found = real(state, attacker, defender, attack=attack, **kwargs)
            if attack is not None and attack.card_id == FOSSIL_GEODUDE and attacker is not defender:
                return tuple(found) + extra
            return found

        self.patches = [mock.patch.object(E, "attack_damage_modifiers", fake), mock.patch.object(K, "attack_damage_modifiers", fake)]
        for patch in self.patches:
            patch.start()
        return self

    def __exit__(self, *exc):
        for patch in self.patches:
            patch.stop()


class RegistrationTest(unittest.TestCase):
    def test_counts(self):
        """対応ポケモン 345 → 348、トレーナー 89、特殊エネルギーを含むエネルギー 10（447 枚）。ワザの登録 586 → 591、特殊能力 54。"""
        pool = load_card_pool()
        playable = [pool.get(c) for c in pool.definitions if pool.is_playable(c)]
        by = {k: sum(1 for d in playable if d.category == k) for k in ("pokemon", "trainer", "energy")}
        self.assertEqual(by, {"pokemon": 783, "trainer": 260, "energy": 37})  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚を含む）を加えた  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.74 で拡張パック以外の商品のスタジアム 13 枚  # v0.73 で拡張パック以外の商品のトレーナー 18 枚  # v0.72 で拡張パック以外の商品のポケモン 43 枚  # v0.71 で拡張パック以外の商品の再録 78 枚（ポケモン 11・トレーナー 67）  # v0.70 で拡張パック以外の商品のポケモン 82 枚  # v0.69 で拡張パック以外の商品の同じカード 96 枚  # v0.68 でポケモン 3 枚  # v0.65 でポケモン 2 枚・トレーナー 1 枚を加えた  # v0.66 でトレーナー 3 枚を加えた  # v0.67 でトレーナー 1 枚  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた
        self.assertEqual((len(DEFAULT_EFFECTS._attacks), len(DEFAULT_EFFECTS._powers), len(DEFAULT_EFFECTS._trainers)), (1312, 114, 260))  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚（ワザ 14・特殊能力 12）を加えた  # v0.85 でポケモン 13 枚（ワザ 17・特殊能力 9）・ミラクルエネルギーを加えた  # v0.82 でポケモン 18 枚（ワザ 33）・リサイクルエネルギー・エコロジムを加えた  # v0.81 でトレーナー 15 枚（ポケモンのどうぐ 11 枚・スタジアム 3 枚を含む）を加えた  # v0.80 でトレーナー 30 枚（スタジアム 4 枚を含む）を加えた  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.74 でトレーナー 13 枚  # v0.73 でトレーナー 18 枚  # v0.72 でワザ 77（拡張パック以外の商品のポケモン 43 枚）  # v0.71 でワザ 15・特殊能力 6・トレーナー 67（拡張パック以外の商品の再録）  # v0.70 でワザ 136（拡張パック以外の商品のポケモン 82 枚）  # v0.69 でワザ 92・特殊能力 10・トレーナー 19（拡張パック以外の商品の同じカードの写し）  # v0.68 でワザ 4・特殊能力 2  # v0.65 でワザ 2・特殊能力 2・トレーナー 1  # v0.66 でトレーナー 3 枚  # v0.67 でトレーナー 1 枚  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた
        for card in (FOSSIL_GEODUDE, FOSSIL_GRAVELER, FOSSIL_GOLEM):
            self.assertTrue(pool.is_playable(card))

    def test_types(self):
        """れんぞくいしなげは CoinsUntilTailsDamage(10)、かたくなるはイワークと同じ ZeroDamageBelowNextTurn(40)（「ダメージを受けない」状態の
        PreventDamage の型にしない）、じばくは化石の秘密のレアコイルと同じ SelfDestruct(100, 20, True)。"""
        effect = lambda card, i: DEFAULT_EFFECTS.attack_entry(card, i).effect
        self.assertEqual(effect(FOSSIL_GEODUDE, 0), E.CoinsUntilTailsDamage(10))
        self.assertEqual(effect(FOSSIL_GRAVELER, 0), E.ZeroDamageBelowNextTurn(40))
        self.assertNotIsInstance(effect(FOSSIL_GRAVELER, 0), E.PreventDamageOnHeads)
        self.assertEqual(effect(FOSSIL_GRAVELER, 1), E.DAMAGE_ONLY)
        self.assertEqual(effect(FOSSIL_GOLEM, 0), E.DAMAGE_ONLY)
        self.assertEqual(effect(FOSSIL_GOLEM, 1), E.SelfDestruct(self_damage=100, bench_damage=20, weakness_resistance_stated=True))
        self.assertEqual(effect(ONIX, 1), E.ZeroDamageBelowNextTurn(40))  # イワークの登録は変えていない
        self.assertIn(E.CoinsUntilTailsDamage, ATTACK_TYPES_SINCE_V0_17)
        self.assertNotIn(E.CoinsUntilTailsDamage, v013_checks.VERIFIED)
        with self.assertRaises(NotImplementedError):
            effect(FOSSIL_GEODUDE, 0).damage_profile(board(), None)

    def test_text_variants_are_limited(self):
        """かたくなる・じばくの書き方の違いは、明示的に加えた 1 通りずつだけを受け付ける（読点・かっこを一律に取り除いて比べない）。"""
        pool = load_card_pool()
        harden = pool.get(FOSSIL_GRAVELER).attacks[0]
        boom = pool.get(FOSSIL_GOLEM).attacks[1]
        self.assertEqual(E.ZeroDamageBelowNextTurn(40).check(harden), [])
        self.assertEqual(E.ZeroDamageBelowNextTurn(40).check(pool.get(ONIX).attacks[1]), [])
        self.assertEqual(E.SelfDestruct(100, 20, True).check(boom), [])
        import dataclasses
        for text in ("次の相手の番にこのカードが受ける30以下のダメージは0になる。40以上のダメージはそのまま受ける。",
                     "次の相手の番にこのカードが受ける20以下のダメージは0になる。(ダメージ以外の効果はそのまま)。40以上のダメージはそのまま受ける。",
                     "次の相手の番にこのカードが受ける30以下のダメージは0になる。（ダメージ以外の効果はそのまま）。40以上のダメージはそのまま受ける。"):
            self.assertTrue(E.ZeroDamageBelowNextTurn(40).check(dataclasses.replace(harden, text_ja=text)), text)
        for text in ("自分にも100ダメージ。お互いの控えポケモン全員にも「弱点・抵抗力」に関係なくそれぞれ20ダメージ。",
                     "自分にも100ダメージ。お互いの控えポケモン全員にも、「弱点・抵抗力」に関係なく それぞれ20ダメージ。"):
            self.assertTrue(E.SelfDestruct(100, 20, True).check(dataclasses.replace(boom, text_ja=text)), text)
        # スタジアムをトラッシュする書き方（タケシのゴローン）には、読点のない書き方を加えていない
        stadium = dataclasses.replace(boom, text_ja="自分にも100ダメージ。お互いの控えポケモン全員にも、「弱点・抵抗力」に関係なくそれぞれ20ダメージ。"
                                                    + E.DISCARD_STADIUM_TEXT)
        self.assertTrue(E.SelfDestructThenDiscardStadium(100, 20, True).check(stadium))

    def test_no_card_id_branches(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parent.parent / "kyuura_engine"
        for path in [root / "engine.py", *sorted((root / "resolution").glob("*.py"))]:
            text = path.read_text(encoding="utf-8")
            for card in (FOSSIL_GEODUDE, FOSSIL_GRAVELER, FOSSIL_GOLEM):
                self.assertNotIn(card, text, path.name)


class StoneBarrageTest(unittest.TestCase):
    def test_heads_then_tail(self):
        """「うら」が出るまで 1 枚ずつ投げ、「おもて」の数 × 10 が 1 段階。1 枚目が「うら」なら 0（2 段階で終える。ワザの失敗ではない）。コインの数・
        ログ（1 枚ごとの coin_flip。count は投げた枚数・until は tails）・乱数の使い方（1 枚 1 回 getrandbits(1)）。どの先読みの方法でも同じ。"""
        state = board(opponent=mon(ONIX))
        for heads in (0, 1, 2, 7, 8, 9, 30):
            for mode in MODES:
                with self.subTest(heads=heads, mode=mode):
                    new = run(state, heads, mode=mode)
                    flips = events(new, len(state.log), "coin_flip")
                    self.assertEqual([e["result"] for e in flips], ["heads"] * heads + ["tails"])
                    self.assertEqual({(e["count"], e["until"]) for e in flips}, {(heads + 1, "tails")})
                    self.assertEqual([e["number"] for e in flips], list(range(1, heads + 2)))
                    damage = events(new, len(state.log), "damage")
                    self.assertEqual([e["amount"] for e in damage], [10 * heads])
                    self.assertEqual(bool(damage[0].get("stopped_after_step_2")), heads == 0)
                    self.assertEqual(events(new, len(state.log), "attack_failed"), [])
                    reference = rng_with_coin_bits(*([H] * heads + [T]))
                    for _ in range(heads + 1):
                        reference.getrandbits(1)
                    self.assertEqual(new.rng.getstate(), reference.getstate())  # 投げたのは h + 1 枚だけ

    def test_long_heads_run(self):
        """長い「おもて」の並び（250 枚）のあとの「うら」: 上限で打ち切らない。代表（組の最大の値より大きい）を実際のダメージにしない。"""
        state = board(opponent=mon(ONIX))
        classes = captured_classes(state)
        heads = 250
        self.assertGreater(heads, max(classes.representatives))
        new = run(state, heads)
        self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage")], [2500])
        self.assertEqual(len(events(new, len(state.log), "coin_flip")), heads + 1)
        self.assertEqual(classes.index_of_heads(heads), classes.index_of_heads(classes.bound + (heads - classes.bound) % classes.period))

    def test_calculation_after_base(self):
        """1 段階のあとの計算は、ほかのダメージの要素と同じ: 弱点（草のポケモンは受けない）・プラスパワー（5 段階 +10）・ディフェンダー（7 段階 −20）・
        なぞのかべ（30 以上は 0）。"""
        cases = [
            (board(opponent=mon(ONIX)), {2: 20, 3: 30}),
            (board(active=mon(FOSSIL_GEODUDE, (FIGHTING, FIGHTING), trainers=[(PLUSPOWER, 7)]), opponent=mon(ONIX)), {0: 0, 2: 30}),
            (board(opponent=mon(ONIX, trainers=[(DEFENDER, 7)])), {1: 0, 3: 10}),
            (board(opponent=mon(MR_MIME)), {2: 20, 3: 0, 9: 0}),
        ]
        for state, expected in cases:
            for heads, amount in expected.items():
                with self.subTest(defender=state.players[1].active.card, heads=heads):
                    new = run(state, heads)
                    self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage")], [amount])

    def test_prevented_defender_stops_before_coins(self):
        """「ダメージを受けない」状態の相手には、コインがダメージの量だけを決めるので、コインの前に v0.4b の問い（状態・乱数・ログは変わらない）。"""
        state = with_coin_bits(board(opponent=mon(KAKUNA, prevent_damage=6)), H, T)
        before = written(state)
        for mode in MODES:
            with self.assertRaises(UnsupportedError) as raised:
                apply_kernel(state, UseAttack(0, 0), preflight=mode)
            self.assertEqual(raised.exception.code, "UNRESOLVED_PREVENTED_COIN_DAMAGE")
            self.assertEqual(written(state), before)

    def test_confusion_tails_flips_no_barrage_coins(self):
        """こんらんの「うら」でワザが止まったら、「うら」が出るまでのコインは投げない（こんらんのコイン 1 枚だけ）。"""
        state = board(active=mon(FOSSIL_GEODUDE, (FIGHTING, FIGHTING), confusion=True), opponent=mon(ONIX))
        new = apply_kernel(with_coin_bits(state, T, H, H), UseAttack(0, 0))
        self.assertEqual([e["source"] for e in events(new, len(state.log), "coin_flip")], ["confusion"])
        new = apply_kernel(with_coin_bits(state, H, H, T), UseAttack(0, 0))
        self.assertEqual([e["source"] for e in events(new, len(state.log), "coin_flip")], ["confusion", "attack", "attack"])
        self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage")], [10])

    def test_history_records_actual_damage(self):
        """ワザの履歴（ピジョンがいるときだけ記録する）は実際のダメージ（代表の値ではない）。ピジョンは抵抗力 闘 −30。"""
        state = board(opponent=mon(PIDGEOTTO, (FIRE, FIRE, FIRE)))
        for heads, amount in ((2, 0), (5, 20), (8, 50)):
            new = run(state, heads)
            received = [r for r in new.players[1].active.history if type(r).__name__ == "AttackReceived"]
            self.assertEqual([r.damage for r in received], [amount])


class PreflightFinitenessTest(unittest.TestCase):
    """先読みの有限の組（docs 3 章）: h ≥ h_s で key(h) = key(h + P)、組の代表だけを試した先読みと、0 〜 N − 1 のすべての「おもて」の数を試した先読みが
    同じ答え（受け付けるか・止める問いと理由の文）になること。"""

    BOARDS: ClassVar[dict] = {
        "onix": lambda: board(opponent=mon(ONIX)),
        "mr_mime": lambda: board(opponent=mon(MR_MIME)),
        "defender": lambda: board(opponent=mon(ONIX, trainers=[(DEFENDER, 7)])),
        "pluspower": lambda: board(active=mon(FOSSIL_GEODUDE, (FIGHTING, FIGHTING), trainers=[(PLUSPOWER, 7)]), opponent=mon(ONIX)),
        "shell_attack": lambda: board(opponent=mon(DARK_WARTORTLE, retaliation_received=6)),
        "shell_attack_damaged": lambda: board(active=mon(FOSSIL_GEODUDE, (FIGHTING, FIGHTING), damage=20),
                                              opponent=mon(DARK_WARTORTLE, retaliation_received=6, damage=30)),
        "guts": lambda: board(opponent=mon(GIOVANNIS_MACHAMP)),
        "scram": lambda: board(opponent=mon(BROCKS_PRIMEAPE)),
    }

    def assert_finite(self, state, *, extra=4, limit=80):
        classes = captured_classes(state)
        for heads in range(classes.bound, classes.bound + classes.period * 30):
            self.assertEqual(classes.key_of(heads), classes.key_of(heads + classes.period), heads)
        n = min(classes.bound + classes.period * extra, limit)
        for mode in ("derived", "derived_full"):
            for heads in (0, 1, 2, min(classes.bound + 3, 200)):
                self.assertEqual(outcome(state, heads, mode), outcome(state, heads, mode, brute=n), (mode, heads))
        return classes

    def test_boards(self):
        for name, make in self.BOARDS.items():
            with self.subTest(board=name):
                self.assert_finite(make())

    def test_scram_representative(self):
        """［ずらかる］: 残りの HP がちょうど 10 になる数（60）は組を分ける（KO の量でまとめない）。"""
        classes = captured_classes(board(opponent=mon(BROCKS_PRIMEAPE)))
        self.assertIn(6, classes.representatives)
        new = run(board(opponent=mon(BROCKS_PRIMEAPE)), 6)
        self.assertEqual(len(events(new, 0, "scram")), 1)

    def test_shell_attack_keeps_returned_amounts(self):
        """こうらがえし: 受けたダメージで返す量が決まるので、受けるポケモンがきぜつする量を超えても、返す量で組を分ける（KO の量だけでまとめない）。"""
        classes = captured_classes(board(opponent=mon(DARK_WARTORTLE, retaliation_received=6, damage=30)))
        # わるいカメールの残りの HP は 30（3 枚できぜつ）。返すダメージはイシツブテ（HP 50）が 5 枚ぶんまで分ける
        self.assertEqual(max(classes.representatives), 5)
        for mode in MODES:
            self.assertEqual(outcome(board(opponent=mon(DARK_WARTORTLE, retaliation_received=6)), 0, mode)[1], "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT")

    def test_synthetic_calculations(self):
        """今の写しにない計算の組み合わせ（盤面を直接作った）: その数にする・加える（2 段階。順番の決定）、半分（切り上げ）としきい値より小さければ 0（8 段階。
        順番の決定）、2 つの半分（周期 4）。"""
        cases = (
            (DamageModifier(2, 60, "s", operation=SET), DamageModifier(2, 20, "a")),
            (DamageModifier(8, 2, "h", operation=HALVE_UP), DamageModifier(8, 40, "z", operation=ZERO_IF_BELOW)),
            (DamageModifier(6, 2, "h1", operation=HALVE_DOWN), DamageModifier(8, 2, "h2", operation=HALVE_UP), DamageModifier(8, -20, "d", operation=ADD)),
        )
        for modifiers in cases:
            with self.subTest(modifiers=[m.label for m in modifiers]), synthetic_modifiers(*modifiers):
                classes = self.assert_finite(board(opponent=mon(ONIX)), extra=2, limit=48)
                self.assertEqual(classes.period, 2 ** sum(1 for m in modifiers if m.operation in (HALVE_UP, HALVE_DOWN)))

    def test_unsupported_board_stops(self):
        """根拠の前提を満たさない計算（ダメージカウンターの単位の倍数でない数）は推測せずに止める（エンジンの未対応。状態は変わらない）。"""
        state = with_coin_bits(board(opponent=mon(ONIX)), H, T)
        before = written(state)
        with synthetic_modifiers(DamageModifier(6, 5, "odd")):
            for mode in MODES:
                with self.assertRaises(UnsupportedError) as raised:
                    apply_kernel(state, UseAttack(0, 0), preflight=mode)
                self.assertEqual(raised.exception.code, "UNSUPPORTED_UNBOUNDED_COIN_PREFLIGHT")
        self.assertEqual(written(state), before)

    def test_preflight_does_not_change_input(self):
        state = with_coin_bits(board(opponent=mon(DARK_WARTORTLE, retaliation_received=6)), H, H, T)
        before = written(state)
        for mode in MODES:
            with self.assertRaises(UnsupportedError):
                apply_kernel(state, UseAttack(0, 0), preflight=mode)
        self.assertEqual(written(state), before)


class InteractionTest(unittest.TestCase):
    def test_guts_decision_save_restore_and_rejection(self):
        """こんじょう: 100 以上で決定。保存と復元で同じに続く。不正な答えは状態・乱数・ログを変えず、決定を残す。"""
        state = board(opponent=mon(GIOVANNIS_MACHAMP))
        new = run(state, 10, extra=(H,))
        decision = new.decision
        self.assertEqual(decision.kind, KO_PREVENTION)
        restored = pickle.loads(pickle.dumps(new))
        before = written(new)
        with self.assertRaises(IllegalActionError):
            apply_kernel(new, ResolveDecision(decision.player, decision.id, (999,)))
        self.assertEqual(written(new), before)
        answer = ResolveDecision(decision.player, decision.id, tuple(decision.options))
        self.assertEqual(written(apply_kernel(new, answer)), written(apply_kernel(restored, answer)))
        self.assertEqual(apply_kernel(new, answer).players[1].active.damage, 90)  # 「おもて」なら HP − 10
        self.assertLess(run(state, 9).players[1].active.damage, 100)

    def test_copied_by_metronome(self):
        """ピッピの「ゆびをふる」でれんぞくいしなげを使う: ワザを使うのはピッピ（無色。イシツブテは弱点 草なので弱点なし）。コインは新しく投げる。"""
        state = build_test_state([{"active": mon(CLEFAIRY, (FIRE, FIRE, FIRE))}, {"active": mon(FOSSIL_GEODUDE)}], turn_number=7)
        new = apply_kernel(with_coin_bits(state, H, H, H, T), UseAttack(0, 1))
        self.assertEqual(new.decision.kind, SELECT_ATTACK)
        new = apply_kernel(new, ResolveDecision(0, new.decision.id, (0,)))
        self.assertEqual([e["copied"] for e in events(new, len(state.log), "copy_attack")], [str(AttackKey(FOSSIL_GEODUDE, 0))])
        self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage")], [30])
        self.assertEqual(len(events(new, len(state.log), "coin_flip")), 4)

    def test_mirror_move(self):
        """ピジョンの「オウムがえし」で、受けたれんぞくいしなげを出す: ピジョンのワザとしてコインを新しく投げる（前の結果を使わない）。"""
        state = board(opponent=mon(PIDGEOTTO, (FIGHTING, FIRE, FIRE)))
        first = apply_kernel(with_coin_bits(state, H, H, H, H, H, T, H, H, T), UseAttack(0, 0))
        self.assertEqual(first.players[1].active.damage, 20)
        second = apply_kernel(first, UseAttack(1, 1))  # ワザで番が終わり、ピジョンの番
        since = len(first.log)
        self.assertEqual([e["amount"] for e in events(second, since, "damage")], [20])  # 2 枚の「おもて」× 10（イシツブテは無色に弱点・抵抗力なし）
        self.assertEqual(len(events(second, since, "coin_flip")), 3)
        # 出すワザに必要なエネルギー（闘無）をピジョンで払えなければ MM2（既存の問い。コインの前）
        unpaid = apply_kernel(with_coin_bits(board(opponent=mon(PIDGEOTTO, (FIRE, FIRE, FIRE))), H, H, H, H, H, T, H, T), UseAttack(0, 0))
        with self.assertRaises(UnsupportedError) as raised:
            apply_kernel(unpaid, UseAttack(1, 1))
        self.assertEqual(raised.exception.code, "UNRESOLVED_MIRROR_MOVE_ATTACK_CONDITIONS")


class GravelerTest(unittest.TestCase):
    def test_harden_boundary(self):
        """かたくなる: 次の相手の番、30 以下は 0、40 以上はそのまま（8 段階）。ダメージ以外の効果は受ける（ビードルのどくばりの「おもて」でどく）。"""
        state = build_test_state([{"active": mon(FOSSIL_GRAVELER, (FIGHTING, FIGHTING))},
                                  {"active": mon(FOSSIL_GEODUDE, (FIGHTING, FIGHTING)), "bench": [mon(WEEDLE, (GRASS,))]}], turn_number=7)
        hardened = apply_kernel(state, UseAttack(0, 0))  # ワザで番が終わり、相手の番
        effects = hardened.players[0].active.persistent_effects
        self.assertEqual([(type(e), e.threshold) for e in effects], [(ZeroDamageBelow, 40)])
        for heads, amount in ((3, 0), (4, 40), (5, 50)):
            new = run(hardened, heads, UseAttack(1, 0))
            self.assertEqual([e["amount"] for e in events(new, len(hardened.log), "damage")], [amount], heads)

    def test_harden_keeps_effects(self):
        state = build_test_state([{"active": mon(FOSSIL_GRAVELER, (FIGHTING, FIGHTING))}, {"active": mon(WEEDLE, (GRASS,))}], turn_number=7)
        hardened = apply_kernel(state, UseAttack(0, 0))  # ワザで番が終わり、相手の番
        new = apply_kernel(with_coin_bits(hardened, H), UseAttack(1, 0))
        self.assertEqual([e["amount"] for e in events(new, len(hardened.log), "damage")], [0])
        self.assertIsNotNone(new.players[0].active.conditions.poison)


class GolemTest(unittest.TestCase):
    def test_selfdestruct(self):
        """じばく: 相手に 100、自分に 100（ワザによる自分へのダメージ。ディフェンダーがあれば 80 で計算する）、お互いの控え全員に 20（弱点・抵抗力に関係なく）。
        同時にきぜつしたポケモンは、ワザのあとにまとめてトラッシュし、サイドを取る。"""
        golem = mon(FOSSIL_GOLEM, (FIGHTING,) * 4)
        state = board(active=golem, opponent=mon(ONIX), bench=[mon(RATTATA, damage=10), mon(ONIX)], opponent_bench=[mon(RATTATA), mon(RATTATA, damage=10)])
        new = apply_kernel(state, UseAttack(0, 1))
        damage = [(e["player"], e["amount"]) for e in events(new, len(state.log), "damage")]
        self.assertEqual(damage, [(1, 100), (0, 100), (1, 20), (1, 20), (0, 20), (0, 20)])
        knocked = events(new, len(state.log), "knock_out")
        # 相手のイワーク（100 ≥ 90）・ゴローニャ（100 ≥ 80）・ダメージ 10 のコラッタ 2 匹（30 ≥ 30）。ダメージのないコラッタ（20）は残る
        self.assertEqual(len(knocked), 4)
        self.assertIsNotNone(new.decision)
        defended = board(active=mon(FOSSIL_GOLEM, (FIGHTING,) * 4, trainers=[(DEFENDER, 6)]), opponent=mon(ONIX))
        new = apply_kernel(defended, UseAttack(0, 1))
        self.assertEqual([e["amount"] for e in events(new, len(defended.log), "damage") if e["player"] == 0], [80])


class GamesTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.64 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.64 の 4 組を 2 seed ずつ（席を入れかえて 16 局）。監査の失敗・想定外の拒否・内部エラー・手数の上限がなく、5 つのワザ（れんぞくいしなげ（0 枚と 1 枚以上）・
        かたくなる（受けたダメージを 0 にした）・いわおとし・いわころがり・じばく）が使われる（勝敗は判断に使わない）。"""
        from tools import existing_effect_games as games

        results = games.run(range(2), pairings=games.PAIRINGS_V0_64)
        totals = {}
        for run_ in results.values():
            for game in run_["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                if game["outcome"] == "halted":
                    self.assertEqual(game["halt_code"], "UNRESOLVED_MULLIGAN_COMPENSATION")
                for key, count in game.get("v064", {}).items():
                    totals[key] = totals.get(key, 0) + count
        for key in ("barrage", "barrage_zero", "barrage_heads_1", "harden", "rock_throw", "selfdestruct"):
            self.assertGreater(totals.get(key, 0), 0, key)


if __name__ == "__main__":
    unittest.main()

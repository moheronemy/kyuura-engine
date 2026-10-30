"""v0.118 の A0（docs/unbounded-coins-heal-allocation-v0.118.md 2 章）: ナツメのESPと「うら」が出るまで投げるコイン。

v0.117 までは、ナツメのESPのついたポケモンが「うら」が出るまで投げるコインのワザを使うと、``HeadsUntilTails.flip_until_tails`` が「v0.66 では起こらない組み合わせ」の ``RuntimeError``
（内部エラー）にしていた。この前提は誤りで、ナツメのフーディン（PMCG6-053）の［サイコリンク］で、超の色マーカーをのせた控えの化石の秘密のイシツブテ（PMCG3-034）の「れんぞくいしなげ」を
使えば、通常の登録・操作（``PlayTrainer``・``ResolveDecision``・``UseAttack``。ESPの関数・解決の部品を差しかえない）で届く。

確かめる性質: やり直しは「うら」が出るまでの一まとまりを投げ終えたあとに 1 回だけ聞く・やり直すなら最初から「うら」が出るまで投げ直す（枚数は最初と違いうる）・最後の並びだけを
ダメージに使い、最初の並びで先に処理しない・実際のコインに上限はない（先読みの代表の値を実際のログ・ダメージ・乱数に使わない）・先読みはやり直しの層を加えて試す・決定の答えの
原子性と保存。盤面は 1 か所の規定を確かめるために直接作ったもので、``new_game`` からの自然な対戦の結果ではない。旧テストの「必ず RuntimeError」（v0.66 の
``test_until_tails_coins_with_esp_stop_as_engine_bug``）は、この性質を確かめるテストに置きかえた（期待を弱めたのではない）。
"""

from __future__ import annotations

import copy
import dataclasses
import pickle
import unittest
from unittest import mock

from kyuura_engine import ResolveDecision, UseAttack
from kyuura_engine.cards import EnergyType
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import ESP_REDO
from kyuura_engine.effects import ESP_HOLDER_CODE, ESP_MULTIPLE_CODE, AttackKey
from kyuura_engine.engine import apply_command_traced, check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.resolution import kernel as K
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution import unbounded
from kyuura_engine.resolution.contract import program_for
from kyuura_engine.resolution.events import FrameKind, PreflightResult
from kyuura_engine.state import MARKER_COLOR
from tests import helpers as H
from tests import test_variable_coins_search_attachments_v0_113 as V113
from tests.helpers import apply_kernel, with_coin_bits
from tests.test_neo_trainer_components_v0_80 import audited, new_events
from tests.test_unown_family_powers_v0_96 import TURN, snap
from tests.test_variable_coins_search_attachments_v0_113 import (
    ALAKAZAM,
    ESP_CARD,
    board,
    esp_board,
    mon,
    provider_card,
    same_answers,
)

HD, TL = CoinSide.HEADS, CoinSide.TAILS
F, W, M = H.FIGHTING, H.WATER, H.METAL_ENERGY_NEO1
GEODUDE, SCIZOR, SCYTHER = H.FOSSIL_GEODUDE, H.SCIZOR_PRN, "PMCG2-017"  # れんぞくいしなげ（10×）・メタルニッパー（30+。30 + 10 × おもての数）・ストライク


def run(heads: int) -> tuple[CoinSide, ...]:
    return (HD,) * heads + (TL,)


def attack(state, card, coins, index=0):
    return apply_kernel(with_coin_bits(state, *coins), UseAttack(0, index, card=card))


def answer(state, choices, coins=()):
    d = state.decision
    return apply_kernel(with_coin_bits(state, *coins) if coins else state, ResolveDecision(d.player, d.id, tuple(choices)))


def attack_flips(before, after):
    return [e for e in new_events(before, after, "coin_flip") if e.get("source") == "attack"]


def bases(before, after):
    return [dict(e["steps"]).get("1 基本となる計算") for e in new_events(before, after, "damage")]


def geodude_board(*, esp=True, opponent=None):
    if esp:
        return esp_board(GEODUDE, (F, W), opponent=opponent or mon(H.CHANSEY))
    return board(mon(ALAKAZAM, (F, W)), bench=(mon(GEODUDE, markers=[(MARKER_COLOR, EnergyType.PSYCHIC)]),), opponent=opponent or mon(H.CHANSEY))


def preflight_branches(state, command, mode="derived_full"):
    _, trace = apply_command_traced(state, command, preflight=mode)
    return [r.branches for r in trace.of(PreflightResult)]


def representatives(state, card_id, attack_index=0):
    """``state`` の場で、ナツメのフーディンが ``card_id`` のワザを使うときの「おもて」の数の組の代表（v0.64 の ``head_classes``。状態を変えない）。"""
    res = K.Resolution(state.clone())
    attacker = res.state.players[0].active
    fs = res.open_frame(FrameKind.ATTACK, parent=None, player=0, source_pid=attacker.pokemon_id, attack_key=AttackKey(card_id, attack_index))
    element = program_for(res.state.effects.attack_entry(card_id, attack_index).effect, res.state.definitions[card_id].attacks[attack_index].name_ja)[0]
    run_ = P.AttackRun(res, fs, (element,), res.state.definitions[card_id].attacks[attack_index])
    return unbounded.head_classes(run_, element, element.base.per).representatives


class RealPathTest(unittest.TestCase):
    """通常の登録・操作で届く経路（v0.117 では内部エラー）。"""

    def test_redo_is_offered_after_the_whole_run(self):
        """ESPのついたナツメのフーディンが［サイコリンク］でれんぞくいしなげを使うと、「うら」が出るまで投げ終えたあとに 1 回だけやり直しを聞く（v0.117 では RuntimeError）。決定の前は
        ダメージを与えていない（最初の並びで先に処理しない）。続きの情報の 7 つめは ``("until", "tails")``・枚数は最初の並びの長さ。"""
        state = geodude_board()
        card = provider_card(state, GEODUDE)
        asked = attack(state, card, run(2))
        self.assertEqual(asked.decision.kind, ESP_REDO)
        esp = asked.decision.context_value("esp")
        self.assertEqual(esp[1:], (3, False, 0, ("heads", "heads", "tails"), (asked.players[0].active.trainers[0].card,), ("until", "tails")))
        self.assertEqual([e["result"] for e in attack_flips(state, asked)], ["heads", "heads", "tails"])
        self.assertEqual({e.get("until") for e in attack_flips(state, asked)}, {"tails"})
        self.assertEqual(new_events(state, asked, "damage"), [])
        self.assertEqual(asked.players[1].active.damage, 0)
        audited(self, asked)

    def test_without_esp_the_same_board_attacks_at_once(self):
        """ESPのない対応する盤面では、今までどおり決定を出さずに「おもて」の数 × 10（ラッキーの抵抗力 超 -30）。"""
        state = geodude_board(esp=False)
        after = attack(state, provider_card(state, GEODUDE), run(4))
        self.assertIsNone(after.decision)
        self.assertEqual(bases(state, after), [40])
        self.assertEqual(after.players[1].active.damage, 10)

    def test_keep_and_redo_with_different_lengths(self):
        """やり直さない（最初の 2 枚の「おもて」）・やり直して最初から投げ直す（0 枚・8 枚・1 枚の「おもて」。枚数は最初と違う）。最後の並びだけをダメージに使い、ダメージは 1 回。
        clone・deepcopy・pickle からも同じ答えで同じ結果。"""
        state = geodude_board()
        asked = attack(state, provider_card(state, GEODUDE), run(2))
        for redo, coins, base in (((), (), 20), ((1,), run(0), 0), ((1,), run(8), 80), ((1,), run(1), 10)):
            with self.subTest(redo=redo, coins=coins):
                after = same_answers(self, asked, redo, *coins) if not coins else self._same(asked, redo, coins)
                self.assertEqual(len(attack_flips(asked, after)), len(coins))
                self.assertEqual(bases(asked, after), [base])
                self.assertIsNone(after.decision)
                if redo:
                    redone = new_events(asked, after, "esp_redo")
                    self.assertEqual(len(redone), 1)
                    self.assertEqual((redone[0]["original"], redone[0]["redone"]), (("heads", "heads", "tails"), tuple(c.value for c in coins)))
                    self.assertEqual(new_events(asked, after, "esp_redo_declined"), [])
                else:
                    self.assertEqual(len(new_events(asked, after, "esp_redo_declined")), 1)
                audited(self, after)

    def _same(self, asked, redo, coins):
        expected = answer(asked, redo, coins)
        for other in (asked.clone(), copy.deepcopy(asked), pickle.loads(pickle.dumps(asked))):
            self.assertEqual(snap(answer(other, redo, coins)), snap(expected))
        return expected

    def test_first_tails_is_still_a_toss(self):
        """1 枚目が「うら」（0 枚の「おもて」）でも説明文のコイントスなので、やり直しを聞く。やり直さなければ 0（2 段階で終える。ワザの失敗ではない）。"""
        state = geodude_board()
        asked = attack(state, provider_card(state, GEODUDE), run(0))
        self.assertEqual(asked.decision.context_value("esp")[1:5], (1, False, 0, ("tails",)))
        kept = answer(asked, ())
        self.assertEqual(bases(asked, kept), [0])
        self.assertEqual(new_events(asked, kept, "attack_failed"), [])
        redone = answer(asked, (1,), run(3))
        self.assertEqual(bases(asked, redone), [30])

    def test_long_runs_use_real_coins(self):
        """長い「おもて」の並び（40 枚・25 枚）は、実際のコインの枚数をそのまま使う（先読みの代表の値にしない）。ログは 1 枚ずつ、最後のダメージは 400・250。"""
        state = geodude_board()
        asked = attack(state, provider_card(state, GEODUDE), run(40))
        self.assertEqual(len(attack_flips(state, asked)), 41)
        self.assertEqual({e["count"] for e in attack_flips(state, asked)}, {41})
        kept = answer(asked, ())
        self.assertEqual(bases(asked, kept), [400])
        redone = answer(asked, (1,), run(25))
        self.assertEqual(bases(asked, redone), [250])
        self.assertEqual(len(attack_flips(asked, redone)), 26)
        self.assertGreater(40, max(representatives(state, GEODUDE)))  # 実際の数は、先読みの代表のどれよりも大きい

    def test_fixed_part_with_redo(self):
        """ハッサム（PRN-025）のメタルニッパー（30 + 10 × おもての数）も同じ経路。最後の並びで 30 + 10h。"""
        with mock.patch.dict(V113.BELOW, {SCIZOR: [SCYTHER]}):  # ハッサムの進化元のストライク（v0.113 の ``mon`` の表にない）
            state = esp_board(SCIZOR, (M, W, W), opponent=mon(H.CHANSEY))
        card = provider_card(state, SCIZOR)
        asked = attack(state, card, run(1), index=1)
        self.assertEqual(asked.decision.kind, ESP_REDO)
        self.assertEqual(bases(asked, answer(asked, ())), [40])
        self.assertEqual(bases(asked, answer(asked, (1,), run(5))), [80])

    def test_invalid_answers_keep_the_decision(self):
        """不正な答え（決めるプレイヤーの違い・選べない値・重複）は、状態・乱数・ログ・決定を変えない。"""
        state = geodude_board()
        asked = attack(state, provider_card(state, GEODUDE), run(2))
        before = snap(asked)
        for player, choices in ((1, ()), (0, (2,)), (0, (1, 1)), (0, (0,))):
            with self.subTest(player=player, choices=choices), self.assertRaises(IllegalActionError):
                apply_kernel(asked, ResolveDecision(player, asked.decision.id, choices))
        self.assertEqual(snap(asked), before)

    def test_broken_continuation_is_rejected_by_invariants(self):
        """続きの情報の最初の並びが「うら」で終わらない・7 つめが違う・ログのコインと違うなら、不変条件の違反（作り変えた決定）。"""
        state = geodude_board()
        asked = attack(state, provider_card(state, GEODUDE), run(2))
        esp = asked.decision.context_value("esp")
        for broken in (esp[:4] + (("heads", "heads", "heads"),) + esp[5:], esp[:6] + (("until", "heads"),), esp[:4] + (("heads", "tails", "tails"),) + esp[5:],
                       esp[:2] + (True,) + esp[3:]):
            with self.subTest(broken=broken):
                copy_ = asked.clone()
                copy_.decision = dataclasses.replace(copy_.decision, context=tuple(("esp", broken) if k == "esp" else (k, v) for k, v in copy_.decision.context))
                self.assertNotEqual(check_invariants(copy_), [])
        self.assertEqual(check_invariants(asked), [])

    def test_two_esps_stop_only_the_redo(self):
        """ESPが 2 枚（ES2）: やり直すは選べるが選ぶと止める（状態を変えない）。やり直さないは処理する。"""
        twice = self.two_esp_board()
        asked = attack(twice, provider_card(twice, GEODUDE), run(2))
        self.assertEqual(asked.decision.context_value("unresolved_choices"), (1,))
        self.assertEqual(asked.decision.context_value("unresolved_code"), ESP_MULTIPLE_CODE)
        before = snap(asked)
        with self.assertRaises(UnsupportedError) as raised:
            answer(asked, (1,), run(0))
        self.assertEqual(raised.exception.code, ESP_MULTIPLE_CODE)
        self.assertEqual(snap(asked), before)
        self.assertEqual(bases(asked, answer(asked, ())), [20])

    @staticmethod
    def two_esp_board():
        """ナツメのESPを 2 枚、通常の操作でナツメのフーディンにつけた盤面。"""
        from kyuura_engine import PlayTrainer
        from tests.test_variable_coins_search_attachments_v0_113 import uid

        state = board(mon(ALAKAZAM, (F, W)), bench=(mon(GEODUDE, markers=[(MARKER_COLOR, EnergyType.PSYCHIC)]),), opponent=mon(H.CHANSEY), hand=(ESP_CARD, ESP_CARD))
        for _ in range(2):
            played = apply_kernel(state, PlayTrainer(0, uid(state, ESP_CARD)))
            state = apply_kernel(played, ResolveDecision(0, played.decision.id, (played.players[0].active.pokemon_id,)))
        if len(state.players[0].active.trainers) != 2:
            raise AssertionError(f"ナツメのESPが 2 枚つかない {state.players[0].active.trainers}")
        return state

    def test_holder_not_sabrinas_stops_only_the_redo(self):
        """ESPがナツメのポケモンでないポケモンについている盤面（直接作った。ES3）: やり直すを選ぶと止め、やり直さないは処理する（v0.66 の盤面）。"""
        state = H.build_test_state([
            {"active": mon(GEODUDE, (F, F), trainers=[(ESP_CARD, TURN)]), "bench": [], "hand": [], "deck": [W] * 10, "discard": [], "prizes": 6},
            {"active": mon(H.CHANSEY), "bench": [], "hand": [], "deck": [W] * 10, "discard": [], "prizes": 6},
        ], turn_number=TURN, current_player=0)
        asked = apply_kernel(with_coin_bits(state, *run(1)), UseAttack(0, 0))
        self.assertEqual(asked.decision.kind, ESP_REDO)
        self.assertEqual(asked.decision.context_value("unresolved_code"), ESP_HOLDER_CODE)
        with self.assertRaises(UnsupportedError):
            answer(asked, (1,), run(0))
        self.assertEqual(bases(asked, answer(asked, ())), [10])


class PreflightTest(unittest.TestCase):
    """先読み: やり直しの層（やり直さない・やり直す）と、最初とやり直しの「おもて」の数の組の代表。代表の値は先読みの複製の上だけで使う。"""

    def test_branches_add_the_redo_layer(self):
        """ESPのない盤面は代表の数 R、ESPのある盤面は R（やり直さない）+ R × R（やり直す。最初の数ごとに、やり直したあとの数）。上限 4,096 は増やしていない。"""
        plain = geodude_board(esp=False)
        with_esp = geodude_board()
        reps = representatives(plain, GEODUDE)
        self.assertEqual(reps, representatives(with_esp, GEODUDE))
        r = len(reps)
        self.assertGreater(r, 1)
        self.assertEqual(preflight_branches(plain, UseAttack(0, 0, card=provider_card(plain, GEODUDE))), [r])
        self.assertEqual(preflight_branches(with_esp, UseAttack(0, 0, card=provider_card(with_esp, GEODUDE))), [r + r * r])
        twice = RealPathTest.two_esp_board()
        self.assertEqual(preflight_branches(twice, UseAttack(0, 0, card=provider_card(twice, GEODUDE))), [r])  # ES2: やり直すは試さない（選べるが選ぶと止める）

    def test_modes_agree_and_do_not_change_the_given_state(self):
        """3 つの方法（derived・derived_full・legacy）で受け付けと結果（状態・ログ・乱数）が同じ。渡した状態は変えない。"""
        state = geodude_board()
        command = UseAttack(0, 0, card=provider_card(state, GEODUDE))
        given = with_coin_bits(state, *run(3))
        before = snap(given)
        results = {mode: snap(apply_command_traced(given, command, preflight=mode)[0]) for mode in ("derived", "derived_full", "legacy")}
        self.assertEqual(snap(given), before)
        self.assertEqual(results["derived"], results["derived_full"])
        self.assertEqual(results["derived"], results["legacy"])

    def test_small_enumeration_matches_the_direct_damage(self):
        """小さい全列挙: 最初の「おもて」の数 0〜3 × （やり直さない・やり直したあとの数 0〜3）の最後のダメージは、ESPのない盤面でその数を投げたダメージと同じ（ログのダメージの量・
        受けたポケモンのダメージ・きぜつ）。"""
        state = geodude_board()
        plain = geodude_board(esp=False)
        card, plain_card = provider_card(state, GEODUDE), provider_card(plain, GEODUDE)

        def outcome(before, after):
            damage = new_events(before, after, "damage")
            return [(e["amount"], e["total_damage"]) for e in damage], after.players[1].active is None or after.players[1].active.damage

        direct = {h: outcome(plain, attack(plain, plain_card, run(h))) for h in range(4)}
        for first in range(4):
            asked = attack(state, card, run(first))
            with self.subTest(first=first, redo=False):
                self.assertEqual(outcome(asked, answer(asked, ())), direct[first])
            for second in range(4):
                with self.subTest(first=first, second=second):
                    self.assertEqual(outcome(asked, answer(asked, (1,), run(second))), direct[second])

    def test_knockout_boundary_with_representatives(self):
        """きぜつの境目（残りHP 10 のラッキー: 「おもて」1 枚の 10 − 抵抗力 30 では 0、4 枚の 40 − 30 = 10 できぜつ）でも、代表は境目の両側を含み、実際の数の組は代表の組のどれかと同じ key
        （v0.64 の根拠。ESPのやり直しのあとの数にも同じ組を使う）。"""
        state = geodude_board(opponent=mon(H.CHANSEY, damage=110))
        reps = representatives(state, GEODUDE)
        res = K.Resolution(state.clone())
        attacker = res.state.players[0].active
        fs = res.open_frame(FrameKind.ATTACK, parent=None, player=0, source_pid=attacker.pokemon_id, attack_key=AttackKey(GEODUDE, 0))
        element = P.Damage(P.OPP, P.HeadsUntilTails(10))
        classes = unbounded.head_classes(P.AttackRun(res, fs, (element,), res.state.definitions[GEODUDE].attacks[0]), element, 10)
        self.assertEqual(classes.representatives, reps)
        self.assertNotEqual(classes.key_of(3), classes.key_of(4))
        self.assertEqual(classes.key_of(4), classes.key_of(60))
        for heads in range(80):
            self.assertIn(classes.key_of(heads), classes.keys)
        asked = attack(state, provider_card(state, GEODUDE), run(0))
        knocked = answer(asked, (1,), run(30))
        self.assertEqual(bases(asked, knocked), [300])
        self.assertTrue(any(e["kind"] == "knock_out" for e in new_events(asked, knocked)))

    def test_preflight_uses_representatives_only_on_copies(self):
        """先読みの乱数（``Oracle.coin_run``）は代表だけを返し、実際の処理（記録する乱数）は 1 枚ずつ投げる。代表の値を実際のログに使わない（実際の数が代表にない 40 枚でも、
        ログは 41 枚）。"""
        state = geodude_board()
        seen = []
        original = P.AttackRun._until_flips

        def spy(self, classes, flipper):
            flips = original(self, classes, flipper)
            seen.append((self.res.dry_run, len(flips.results) - 1))
            return flips

        with mock.patch.object(P.AttackRun, "_until_flips", spy):
            asked = attack(state, provider_card(state, GEODUDE), run(40))
        reps = set(representatives(state, GEODUDE))
        self.assertIn((False, 40), seen)
        self.assertTrue(all(heads in reps for dry, heads in seen if dry))
        self.assertEqual(len(attack_flips(state, asked)), 41)


if __name__ == "__main__":
    unittest.main()

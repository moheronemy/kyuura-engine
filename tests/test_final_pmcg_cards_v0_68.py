"""v0.68（docs/final-pmcg-cards-v0.68.md）: PMCG1〜PMCG6 の残りのポケモン 3 枚（ガルーラ・キョウのベトベトン・イマクニ？のドードー）と、マチスの秘策の
受け付けるかが見えない情報で変わる問題の修正。

- ガルーラの「こどものおつかい」の文面は、利用者が示した修正（実物のカード画像で確かめた、と利用者が示した。エンジンは画像を見ていない）を写しに当てはめた値
- キョウのベトベトンの［だつりょくえき］は、この特殊能力に限った採用の仕様（自動的にはたらく。ダメージの要素のあと・ダメージ以外の効果の前）。2000.02.14 版の裁定ではない
- イマクニ？のドードーは、エンジンの簡略化した仕様（ハモるはすぐに 30・［にげまくり］の投げる動作は処理にふくめない）。公式の裁定・エラッタではない
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

from kyuura_engine import apply_command
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import (
    EndTurn,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine.decisions import ENERGY_DRAIN_DISCARD
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.serialize import state_to_dict
from tests.helpers import (
    CLEFAIRY,
    DIGLETT,
    DODUO,
    FIGHTING,
    FIRE,
    FOSSIL_MAGNETON,
    GRASS,
    GUST,
    HITMONCHAN,
    JUNGLE_PIKACHU,
    KANGASKHAN,
    KOGAS_GRIMER,
    KOGAS_MUK,
    LIGHTNING,
    LT_SURGES_SECRET_PLAN,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MAGNEMITE,
    MUK,
    RATTATA,
    ROCKETS_MOLTRES,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems

ROOT = Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
IMAKUNI_DODUO = "PMCG6-074"
FOSSIL_GRIMER = "PMCG3-003"
GASTLY = "PMCG3-029"
V0_68_POKEMON = (KANGASKHAN, KOGAS_MUK, IMAKUNI_DODUO)


def full(state):
    return (state_to_dict(state, format_version=22), rng_fingerprint(state.rng))


def kinds(state, since=0):
    return [e["kind"] for e in state.log[since:]]


def muk_board(attacker=None, muk=None, muk_bench=(), attacker_bench=(), turn_number=5, current_player=0):
    """プレイヤー 0 がワザを使い、プレイヤー 1 の場にキョウのベトベトン（草 1 枚）がいる盤面。"""
    return build_test_state([
        {"active": attacker or {"card": HITMONCHAN, "energy": [FIGHTING, FIGHTING]}, "bench": list(attacker_bench), "deck": [FIRE] * 10},
        {"active": muk or {"card": KOGAS_MUK, "evolved_from": KOGAS_GRIMER, "energy": [GRASS]}, "bench": list(muk_bench), "deck": [FIRE] * 10},
    ], turn_number=turn_number, current_player=current_player)


class RegistrationTest(unittest.TestCase):
    def test_counts_from_the_registry(self):
        pool = load_card_pool()
        counts = {"pokemon": 0, "trainer": 0, "energy": 0}
        for card_id in pool.playable_ids:
            counts[pool.get(card_id).category] += 1
        self.assertEqual((counts["pokemon"], counts["trainer"], counts["energy"]), (585, 211, 30))  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.74 で拡張パック以外の商品のスタジアム 13 枚  # v0.73 で拡張パック以外の商品のトレーナー 18 枚  # v0.72 で拡張パック以外の商品のポケモン 43 枚  # v0.71 で拡張パック以外の商品の再録 78 枚（ポケモン 11・トレーナー 67）  # v0.70 で拡張パック以外の商品のポケモン 82 枚  # v0.69 で拡張パック以外の商品の同じカード 96 枚（ポケモン 57・トレーナー 19・エネルギー 20）
        self.assertEqual(len(pool.playable_ids), 826)  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.74 で 13 枚、v0.73 で 18 枚、v0.72 で 43 枚、v0.71 で 78 枚、v0.70 で 82 枚を加えた（v0.69 は 553、v0.68 は 457）
        extract = read_extract()
        self.assertEqual(len(extract["cards"]), 826)  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.74 で 13 枚、v0.73 で 18 枚を加えた。写しのカードはすべて対応（参照カードは残っていない）
        self.assertEqual(extract["reference_only"], [])
        self.assertEqual(len(E.DEFAULT_EFFECTS.attack_keys()), 995)  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.72 でワザ 77（拡張パック以外の商品のポケモン 43 枚）  # v0.71 でワザ 15（再録のカード）  # v0.70 でワザ 136（拡張パック以外の商品のポケモン 82 枚）  # v0.69 でワザ 92（拡張パック以外の商品の同じカード。元のカードの登録を写した）
        self.assertEqual(len(E.DEFAULT_EFFECTS.power_keys()), 74)  # v0.71 で 6（再録のカード）。v0.69 で 10

    def test_three_cards_are_supported_with_their_types(self):
        pool = load_card_pool()
        for card_id in V0_68_POKEMON:
            self.assertTrue(pool.get(card_id).supported, card_id)
        self.assertIsInstance(E.DEFAULT_EFFECTS.attack_entry(KANGASKHAN, 0).effect, E.DrawCardsAttack)
        self.assertEqual(E.DEFAULT_EFFECTS.attack_entry(KANGASKHAN, 1).effect, E.CoinFlipDamage(coins=4, damage_per_heads=20))
        self.assertIsInstance(E.DEFAULT_EFFECTS.attack_entry(KOGAS_MUK, 0).effect, E.DamageOnly)
        self.assertIsInstance(E.DEFAULT_EFFECTS.attack_entry(IMAKUNI_DODUO, 0).effect, E.SimplifiedSongDamage)
        muk_power = E.DEFAULT_EFFECTS.power_entry(KOGAS_MUK, 0)
        self.assertIsInstance(muk_power.effect, E.DiscardAttackerEnergyOnDamage)
        self.assertFalse(muk_power.effect.declared)
        self.assertEqual((muk_power.play_text_ja, muk_power.source), (E.ENERGY_DRAIN_LATEST, "P43 p.49"))
        doduo_power = E.DEFAULT_EFFECTS.power_entry(IMAKUNI_DODUO, 0)
        self.assertIsInstance(doduo_power.effect, E.SimplifiedRunAway)
        self.assertEqual(doduo_power.source, E.SIMPLIFIED_SPEC_SOURCE)
        # 印刷の文面はデータのまま（照合に使う）。処理に使う文面は簡略化した仕様で、印刷の文面ではない
        self.assertEqual(pool.get(IMAKUNI_DODUO).attacks[0].text_ja, E.HARMONIZE_TEXT)
        self.assertNotEqual(E.DEFAULT_EFFECTS.attack_entry(IMAKUNI_DODUO, 0).play_text_ja, E.HARMONIZE_TEXT)

    def test_simplified_types_only_accept_their_printed_text(self):
        """簡略化した仕様の型は、イマクニ？のドードーの文面のときだけ登録できる（未対応の特殊能力・ワザを効果のないものとして受け付ける一般の仕組みではない）。"""
        pool = load_card_pool()
        for card_id in pool.playable_ids:
            definition = pool.get(card_id)
            for power in definition.powers:
                if card_id != IMAKUNI_DODUO:
                    self.assertTrue(E.SimplifiedRunAway().check(power), card_id)
            for attack in definition.attacks:
                if card_id != IMAKUNI_DODUO:
                    self.assertTrue(E.SimplifiedSongDamage().check(attack), card_id)

    def test_kangaskhan_text_is_the_user_provided_correction(self):
        """v0.68 はエンジンが写しの元（ecb2d69）の値に利用者が示した修正を当てはめていた。v0.69 から kyuura が同じ訂正を data/cards.json に当てはめた
        （台帳 FIX-PMCG2-046-ATK0-TEXT。根拠は user_provided、kyuura は画像を見ていない）。エンジンは当てはめ直さず、出どころを確かめる。"""
        extract = read_extract()
        card = next(c for c in extract["cards"] if c["id"] == KANGASKHAN)
        self.assertEqual(card["pokemon"]["attacks"][0]["text"]["ja"], "自分の山札の上からカードを1枚ひいて、手札に加える。")
        self.assertEqual(card["pokemon"]["attacks"][1]["text"]["ja"], "コインを4枚投げて「おもて」の数×20のダメージ。")
        self.assertNotIn("user_provided_corrections", extract)
        (correction,) = [c for c in extract["kyuura_corrections"] if c["card_id"] == KANGASKHAN]
        self.assertEqual((correction["id"], correction["field"], correction["basis"], correction["kyuura_saw_image"], correction["engine_saw_image"]),
                         ("FIX-PMCG2-046-ATK0-TEXT", "pokemon.attacks[0].text.ja", "user_provided", False, False))
        self.assertTrue(correction["before"].startswith("コインを投げて「おもて」なら、"))
        self.assertNotIn("record", correction)  # kyuura の照合の記録（CC-）・最新の説明（LD-）・修正のコミットはない
        self.assertEqual([x["id"] for x in card["corrections"]], ["FIX-PMCG2-046-ATK0-TEXT"])

    def test_extraction_rejects_a_bad_user_correction(self):
        if not (KYUURA / ".git").exists():
            self.skipTest("../kyuura がない")
        spec = importlib.util.spec_from_file_location("extract_v068", ROOT / "scripts" / "extract_kyuura_cards.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = module.read_kyuura_cards(KYUURA)
        previous = json.loads(module._show(KYUURA, module.PREVIOUS_KYUURA_COMMIT, module.KYUURA_PATH).decode("utf-8"))
        pool = module.all_pool_cards()
        self.assertEqual(module.kyuura_correction_problems(KYUURA, source, previous, pool), [])
        original = list(module.KYUURA_CORRECTIONS)
        index = next(i for i, c in enumerate(original) if c["card_id"] == KANGASKHAN)
        try:
            for bad in (dict(original[index], before="ちがう文面"), dict(original[index], basis="kyuura_source_check"),
                        dict(original[index], engine_saw_image=True), dict(original[index], kyuura_saw_image=True),
                        dict(original[index], record="CC-PMCG2-046-P1")):
                module.KYUURA_CORRECTIONS[:] = [*original[:index], bad, *original[index + 1:]]
                self.assertTrue(module.kyuura_correction_problems(KYUURA, source, previous, pool), bad)
        finally:
            module.KYUURA_CORRECTIONS[:] = original


class KangaskhanTest(unittest.TestCase):
    def board(self, deck=10, energy=4):
        return build_test_state([
            {"active": {"card": KANGASKHAN, "energy": [FIRE] * energy}, "deck": [FIRE] * deck},
            {"active": {"card": HITMONCHAN, "energy": [FIGHTING]}, "deck": [FIRE] * 10},
        ], turn_number=3, current_player=0)

    def test_fetch_draws_one_card_without_a_coin(self):
        state = self.board()
        before_hand = len(state.players[0].hand)
        after = apply_command(state, UseAttack(0, 0))
        events = after.log[len(state.log):]
        self.assertNotIn("coin_flip", [e["kind"] for e in events])
        self.assertIn("draw", [e["kind"] for e in events])
        self.assertEqual(len(after.players[0].hand), before_hand + 1)
        # 乱数を使わない（コインを投げない）。相手の番の最初に引くのは乱数を使わない
        self.assertEqual(rng_fingerprint(after.rng), rng_fingerprint(state.rng))

    def test_fetch_with_an_empty_deck_draws_nothing_and_does_not_lose(self):
        """効果で引くときに山札がなければ引けるだけ（0 枚）。負けになるのは番の最初に引けないときだけ（p.309・p.312）。"""
        state = self.board(deck=0)
        after = apply_command(state, UseAttack(0, 0))
        self.assertEqual(after.phase.name, "MAIN")  # 相手の番になる（対戦は続く）
        self.assertEqual(len(after.players[0].hand), len(state.players[0].hand))
        # 自分の次の番の最初に引けないので負ける（通常の山札切れ）
        later = apply_command(after, EndTurn(1))
        self.assertEqual((later.phase.name, later.result.winner), ("GAME_OVER", 1))

    def test_comet_punch_counts_heads(self):
        for heads in range(5):
            with self.subTest(heads=heads):
                sides = [CoinSide.HEADS] * heads + [CoinSide.TAILS] * (4 - heads)
                state = with_coin_results(self.board(), *sides)
                after = apply_command(state, UseAttack(0, 1))
                self.assertEqual(after.players[1].active.damage if after.players[1].active else None, heads * 20 if heads * 20 < 70 else None)
                self.assertEqual(sum(1 for e in after.log[len(state.log):] if e["kind"] == "coin_flip"), 4)


class EnergyDrainTest(unittest.TestCase):
    def test_tails_discards_nothing(self):
        state = with_coin_results(muk_board(), CoinSide.TAILS)
        after = apply_command(state, UseAttack(0, 0))
        self.assertIsNone(after.decision)
        check = next(e for e in after.log if e["kind"] == "energy_drain_check")
        self.assertEqual((check["player"], check["result"]), (1, "tails"))
        self.assertEqual(len(after.players[0].active.energy), 2)

    def test_heads_lets_the_owner_choose_and_trash(self):
        state = with_coin_results(muk_board(), CoinSide.HEADS)
        pending = apply_command(state, UseAttack(0, 0))
        d = pending.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (ENERGY_DRAIN_DISCARD, 1, tuple(state.players[0].active.energy), 1, 1))
        self.assertEqual(kinds(pending)[-4:], ["attack", "damage", "coin_flip", "energy_drain_check"])
        self.assertEqual(serialization_problems(pending), [])
        self.assertEqual(observation_problems(pending), [])
        chosen = d.options[1]
        after = apply_command(pending, ResolveDecision(1, d.id, (chosen,)))
        self.assertIn(chosen, after.players[0].discard)
        self.assertEqual(after.players[0].active.energy, [d.options[0]])
        self.assertEqual(kinds(after, len(pending.log))[:2], ["energy_drain_discard", "turn_end"])
        # 答えのあとでコインを投げ直さない・ダメージをくり返さない
        self.assertNotIn("coin_flip", kinds(after, len(pending.log))[:2])
        self.assertEqual(after.players[1].active.damage, 20)

    def test_invalid_answers_leave_the_state_unchanged(self):
        pending = apply_command(with_coin_results(muk_board(), CoinSide.HEADS), UseAttack(0, 0))
        d = pending.decision
        before = full(pending)
        for player, choices in ((1, ()), (1, d.options), (1, (999,)), (0, d.options[:1])):
            with self.subTest(player=player, choices=choices):
                with self.assertRaises((IllegalActionError, UnsupportedError)):
                    apply_command(pending, ResolveDecision(player, d.id, choices))
                self.assertEqual(full(pending), before)

    def test_works_when_the_muk_is_knocked_out(self):
        """そのダメージで「きぜつ」しても（CR-ENERGY-DRAIN-EVEN-IF-KO）。きぜつの処理はワザのあと。"""
        state = with_coin_results(muk_board(muk={"card": KOGAS_MUK, "evolved_from": KOGAS_GRIMER, "energy": [GRASS], "damage": 70}), CoinSide.HEADS)
        pending = apply_command(state, UseAttack(0, 0))
        self.assertEqual(pending.decision.kind, ENERGY_DRAIN_DISCARD)
        self.assertEqual(pending.players[1].active.damage, 90)
        after = apply_command(pending, ResolveDecision(1, pending.decision.id, pending.decision.options[:1]))
        self.assertIn("knock_out", kinds(after, len(pending.log)))

    def test_works_on_the_bench(self):
        """ベンチで受けたダメージでもはたらく（CR-ENERGY-DRAIN-BENCH）。ピカチュウのスパークの控えへのダメージ。"""
        state = muk_board(attacker={"card": JUNGLE_PIKACHU, "energy": [LIGHTNING, LIGHTNING]}, muk=HITMONCHAN,
                          muk_bench=[{"card": KOGAS_MUK, "evolved_from": KOGAS_GRIMER}])
        state = apply_command(with_coin_results(state, CoinSide.HEADS), UseAttack(0, 0))
        self.assertEqual(state.decision.kind, "select_pokemon")
        muk = state.players[1].bench[0]
        state = apply_command(state, ResolveDecision(0, state.decision.id, (muk.pokemon_id,)))
        self.assertEqual(state.decision.kind, ENERGY_DRAIN_DISCARD)
        self.assertEqual(state.decision.player, 1)

    def test_status_at_the_time_of_damage(self):
        """ダメージを受けるときにねむり・マヒ・こんらんなら使えない。どくは関係しない（CR-ENERGY-DRAIN-STATUS）。"""
        for spec, works in (({"sleep": True}, False), ({"confusion": True}, False), ({"poison": 10}, True)):
            with self.subTest(spec=spec):
                state = with_coin_results(muk_board(muk={"card": KOGAS_MUK, "evolved_from": KOGAS_GRIMER, "energy": [GRASS], **spec}), CoinSide.TAILS)
                after = apply_command(state, UseAttack(0, 0))
                self.assertEqual("energy_drain_check" in kinds(after, len(state.log)), works)

    def test_chemical_gas_stops_it(self):
        state = muk_board(muk_bench=[{"card": MUK, "evolved_from": FOSSIL_GRIMER}])
        after = apply_command(state, UseAttack(0, 0))
        self.assertNotIn("energy_drain_check", kinds(after, len(state.log)))

    def test_not_for_power_damage(self):
        """特殊能力のダメージ（カイリキーの［はんげき］）でははたらかない（CR-ENERGY-DRAIN-POWER-DAMAGE）。"""
        state = muk_board(attacker={"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], "energy": [FIGHTING]},
                          muk={"card": KOGAS_MUK, "evolved_from": KOGAS_GRIMER, "energy": [GRASS, GRASS, GRASS]}, current_player=1, turn_number=6)
        after = apply_command(state, UseAttack(1, 0))
        self.assertIn("counterattack", kinds(after, len(state.log)))
        self.assertNotIn("energy_drain_check", kinds(after, len(state.log)))

    def test_return_damage_targets_the_effect_holder(self):
        """ほのおのかべの返すダメージでも、ダメージを与えたポケモン（効果を持つ R団のファイヤー）のエネルギーカードを選ぶ（CR-ENERGY-DRAIN-RETURN-DAMAGE）。"""
        state = muk_board(attacker={"card": ROCKETS_MOLTRES, "energy": [FIRE, FIRE], "retaliation": 5},
                          muk={"card": KOGAS_MUK, "evolved_from": KOGAS_GRIMER, "energy": [GRASS, GRASS, GRASS]}, current_player=1, turn_number=6)
        pending = apply_command(with_coin_results(state, CoinSide.HEADS), UseAttack(1, 0))
        self.assertEqual((pending.decision.kind, pending.decision.player), (ENERGY_DRAIN_DISCARD, 1))
        self.assertEqual(pending.decision.options, tuple(state.players[0].active.energy))
        after = apply_command(pending, ResolveDecision(1, pending.decision.id, pending.decision.options[:1]))
        self.assertEqual(len(after.players[0].active.energy), 1)

    def test_dr8_and_dr13_stop_before_the_attack(self):
        cases = (
            # DR8: ダメージを与えたポケモンが同じワザの自分へのダメージで HP 以上（じごくぐるま）
            (muk_board(attacker={"card": MACHOKE, "evolved_from": MACHOP, "energy": [FIGHTING] * 4, "damage": 60}), UseAttack(0, 1),
             E.ENERGY_DRAIN_ATTACKER_KO_CODE),
            # DR8: 返す効果を持つポケモンが、そのワザのダメージで HP 以上
            (muk_board(attacker={"card": ROCKETS_MOLTRES, "energy": [FIRE], "retaliation": 5, "damage": 30},
                       muk={"card": KOGAS_MUK, "evolved_from": KOGAS_GRIMER, "energy": [GRASS, GRASS, GRASS]}, current_player=1, turn_number=6),
             UseAttack(1, 0), E.ENERGY_DRAIN_ATTACKER_KO_CODE),
            # DR13: ダメージを与えたポケモンにエネルギーカードがない
            (muk_board(attacker={"card": ROCKETS_MOLTRES, "retaliation": 5},
                       muk={"card": KOGAS_MUK, "evolved_from": KOGAS_GRIMER, "energy": [GRASS, GRASS, GRASS]}, current_player=1, turn_number=6),
             UseAttack(1, 0), E.ENERGY_DRAIN_NO_ENERGY_CODE),
        )
        for state, command, code in cases:
            with self.subTest(code=code):
                before = full(state)
                with self.assertRaises(UnsupportedError) as ctx:
                    apply_command(state, command)
                self.assertEqual((ctx.exception.code, full(state)), (code, before))

    def test_dr18_two_damage_triggers_reuse_the_existing_question(self):
        """ベトベトンと、控えのカイリキー（［はんげき］）が 1 つのワザでダメージを受けうる（スパークで控えを選ぶ）。宣言の前の先読みが、選ぶ答えのどれかで当たる既存の問い
        （C34・C35）で止める。新しいコードにしない。"""
        state = muk_board(attacker={"card": JUNGLE_PIKACHU, "energy": [LIGHTNING, LIGHTNING]},
                          muk_bench=[{"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE]}], turn_number=9)
        before = full(state)
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual((ctx.exception.code, full(state)), ("UNRESOLVED_MULTIPLE_DAMAGE_TRIGGERS", before))


class ImakuniDoduoTest(unittest.TestCase):
    def board(self, doduo=None, defender=None):
        return build_test_state([
            {"active": doduo or {"card": IMAKUNI_DODUO, "energy": [FIRE, FIRE]}, "bench": [HITMONCHAN], "deck": [FIRE] * 10},
            {"active": defender or {"card": HITMONCHAN, "energy": [FIGHTING]}, "deck": [FIRE] * 10},
        ], turn_number=3, current_player=0)

    def test_harmonize_is_an_ordinary_30_damage_attack(self):
        state = self.board()
        after = apply_command(state, UseAttack(0, 0))
        self.assertEqual(after.players[1].active.damage, 30)
        self.assertEqual(after.current_player, 1)  # 番はふつうに終わる（歌の状態・通知はない）
        # 弱点もふつうに計算する（エレブー? ではなく雷に弱い相手はいないので、弱点 闘のピカチュウで抵抗力・弱点の計算がふつうであることを見る）
        weak = apply_command(self.board(defender={"card": JUNGLE_PIKACHU}), UseAttack(0, 0))
        self.assertEqual(weak.players[1].active.damage, 30)  # 無色のワザ。ピカチュウの弱点は闘

    def test_harmonize_needs_its_energy_and_respects_confusion(self):
        with self.assertRaises(IllegalActionError):
            apply_command(self.board(doduo={"card": IMAKUNI_DODUO, "energy": [FIRE]}), UseAttack(0, 0))
        state = with_coin_results(self.board(doduo={"card": IMAKUNI_DODUO, "energy": [FIRE, FIRE], "confusion": True}), CoinSide.TAILS)
        after = apply_command(state, UseAttack(0, 0))
        self.assertIn("confusion_damage", kinds(after, len(state.log)))
        self.assertEqual(after.players[1].active.damage, 0)

    def test_copied_harmonize_is_also_30(self):
        state = build_test_state([
            {"active": {"card": CLEFAIRY, "energy": [FIRE, FIRE, FIRE]}, "deck": [FIRE] * 10},
            {"active": {"card": IMAKUNI_DODUO}, "deck": [FIRE] * 10},
        ], turn_number=3, current_player=0)
        state = apply_command(state, UseAttack(0, 1))
        self.assertEqual(state.decision.kind, "select_attack")
        after = apply_command(state, ResolveDecision(0, state.decision.id, state.decision.options[:1]))
        self.assertEqual(after.players[1].active.damage, 30)

    def test_run_away_is_not_declarable_and_retreat_is_ordinary(self):
        state = self.board(doduo={"card": IMAKUNI_DODUO})
        doduo = state.players[0].active.pokemon_id
        before = full(state)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, UsePokemonPower(0, doduo, 0))
        self.assertEqual((ctx.exception.code, full(state)), ("POWER_NOT_DECLARABLE", before))
        bench = state.players[0].bench[0].card
        after = apply_command(state, Retreat(0, (), bench))
        self.assertEqual(after.players[0].bench[0].pokemon_id, doduo)
        added = kinds(after, len(state.log))
        self.assertNotIn("pokemon_power", added)
        self.assertEqual(rng_fingerprint(after.rng), rng_fingerprint(state.rng))
        asleep = self.board(doduo={"card": IMAKUNI_DODUO, "sleep": True})
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(asleep, Retreat(0, (), asleep.players[0].bench[0].card))
        self.assertEqual(ctx.exception.code, "POKEMON_ASLEEP")
        self.assertEqual(observation_problems(after), [])


def secret_plan_board(extra_hidden=None, opponent=None, turn_number=3):
    """利用者の再現例（docs/final-pmcg-cards-v0.68.md 5 章）。デッキ A は山札にコラッタ 1 枚と炎 44 枚、デッキ B は炎 1 枚をドードーに置きかえたもの。"""
    deck = [RATTATA] + [FIRE] * 44 if extra_hidden is None else [RATTATA, extra_hidden] + [FIRE] * 43
    state = build_test_state([
        {"active": {"card": HITMONCHAN, "energy": [FIGHTING, FIGHTING]}, "hand": [LT_SURGES_SECRET_PLAN] * 3 + [DIGLETT] * 3, "prizes": [FIRE] * 6,
         "deck": deck},
        {"active": opponent or {"card": HITMONCHAN, "energy": [FIGHTING]}, "hand": [GUST], "prizes": [FIRE] * 6, "deck": [FIRE] * (52 - len((opponent or {"energy": [1]})["energy"]))},
    ], turn_number=turn_number, current_player=0)
    for _ in range(3):
        plan = next(u for u in state.players[0].hand if state.cards[u].card_id == LT_SURGES_SECRET_PLAN)
        state = apply_command(state, PlayTrainer(0, plan))
        diglett = next(u for u in state.players[0].hand if state.cards[u].card_id == DIGLETT)
        state = apply_command(state, ResolveDecision(0, state.decision.id, (diglett,)))
    return apply_command(state, EndTurn(0))


class SecretPlanLeakTest(unittest.TestCase):
    def test_gust_is_accepted_for_both_hidden_decks(self):
        """公開の情報が同じなら、山札の中身（見えない情報）によらず受け付けるかが同じ。v0.67 はデッキ B（カードの種類 7）で 7³ = 343 > 256 になり拒否していた。"""
        results = []
        for extra in (None, DODUO):
            with self.subTest(extra=extra):
                state = secret_plan_board(extra)
                gust = next(u for u in state.players[1].hand if state.cards[u].card_id == GUST)
                state = apply_command(state, PlayTrainer(1, gust))
                target = state.decision.options[0]
                after = apply_command(state, ResolveDecision(1, state.decision.id, (target,)))
                self.assertEqual(after.players[0].active.pokemon_id, target)  # ディグダ（たねポケモン）なので入れ替わる
                self.assertEqual(observation_problems(after), [])
                results.append(observe(state, 1)["players"][0]["deck"])
        self.assertEqual(results[0], results[1])  # 相手から見える山札の情報（枚数）は同じ

    def test_candidates_do_not_depend_on_the_hidden_deck(self):
        """ありうるカードは公開の情報（対応しているカードの一覧）から作る（デッキの中身を使わない）。"""
        from kyuura_engine import engine

        a, b = secret_plan_board(), secret_plan_board(DODUO)
        self.assertIs(engine._public_pool(a), engine._public_pool(b))
        self.assertEqual(len(engine._public_pool(a).playable_ids), 826)  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.74 で 13 枚、v0.73 で 18 枚、v0.72 で 43 枚、v0.71 で 78 枚、v0.70 で 82 枚、v0.69 で 96 枚を加えた（v0.68 は 457）
        # v0.69: 試すカードは、処理の同じカードを 1 枚で代表する（v0.68 と同じ 457 枚。どちらのデッキでも同じ）。v0.70: 拡張パック以外の商品のポケモン 82 枚で
        # ありうるカードの種類が増えた（同じデータの 12 枚は 1 枚で代表するので 527 枚。どちらのデッキでも同じ。tests/test_non_pack_effect_reuse_v0_70.py）
        self.assertEqual(engine._identity_candidates(engine._public_pool(a)), engine._identity_candidates(engine._public_pool(b)))
        # v0.72: 試すカードの数はカードを加えるたびに変わるので固定しない。v0.72 の 43 枚（処理の違う 33 種類）を除いた数が v0.71 の 572
        self.assertEqual(len(set(engine._identity_candidates(engine._public_pool(a))) - set(read_extract()["pool_v0_72"]) - set(read_extract()["pool_v0_73"]) - set(read_extract()["pool_v0_74"]) - set(read_extract()["pool_v0_75"]) - set(read_extract()["pool_v0_76"])), 572)  # v0.73 の 18 枚（トレーナー）も除く

    def test_two_face_down_targets_are_refused_for_both_hidden_decks(self):
        """相手のうらのカードを 2 枚以上、効果の対象にするコマンドは、試す回数が上限を超えるので受け付けない（エンジンの未対応。化石の秘密のレアコイルのじばく。
        「弱点・抵抗力」に関係なく）。第1弾のコイルのじばくは、JS1 の確かめがおもてにする前に HP を読むので FD1（v0.67 から）。どちらもデッキによらず同じ。"""
        cases = (
            ({"card": FOSSIL_MAGNETON, "evolved_from": MAGNEMITE, "evolved_turn": 4, "played_turn": 0, "energy": [LIGHTNING] * 4},
             UnsupportedError, "UNSUPPORTED_SECRET_PLAN_IDENTITIES"),
            ({"card": MAGNEMITE, "energy": [LIGHTNING, LIGHTNING]}, UnsupportedError, "UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY"),
        )
        for opponent, error, code in cases:
            with self.subTest(opponent=opponent["card"]):
                results = []
                for extra in (None, DODUO):
                    state = secret_plan_board(extra, opponent=opponent, turn_number=5)
                    before = full(state)
                    with self.assertRaises(error) as ctx:
                        apply_command(state, UseAttack(1, 1))
                    self.assertEqual(full(state), before)
                    results.append((type(ctx.exception), ctx.exception.code, ctx.exception.message))
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0][1], code)

if __name__ == "__main__":
    unittest.main()

"""ロケット団のベトベター（PMCG4-004。v0.8）の「どくガス」「ねばりつく」と、ベトベトン（PMCG3-007）の「ヘドロこうげき」・進化。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES）。照合の記録は kyuura_engine/data/card_verification.json
（300dpi。カードの図版の説明文は 600dpi）。裁定は docs/grimer-line-v0.8.md（M1〜M9）。

- p.45: 「たねポケモン ベトベター LV.10／HP40」「ポケモンカード第4弾ロケット団」。「●どくガス 相手を「どく」状態にする。」「●ねばりつく
  コインを投げて「おもて」なら、20ダメージを追加して、相手を「マヒ」状態にする。」（目安「10+」）。解説「「どくガス」は、コイントスなしで
  相手の対戦ポケモンを必ずどく状態にします。」「（ねばりつくで）6個のダメージカウンター」（「おもて」で 10 + 20 = 30）
- p.47: 化石の秘密のベトベター（参照カード。「ちいさくなる」が未実装）
- p.48: ベトベトン「●ヘドロこうげき コインを投げて「おもて」なら、相手を「どく」状態にする。」（目安 30）
- p.320: 「「＋」がある場合、書かれている数字よりもダメージが大きくなることがあります」「「ワザの説明」の最初に書かれているはずの「相手（太字）に
  ○○ダメージ。」ということばが省略されています」。p.321: 基本となるダメージ（1 段階）のあとに弱点・抵抗力
- p.309・p.323: ワザのダメージできぜつしたら、その後の対象のいない内容は無視する。p.322: 特殊状態の重複
"""

import unittest

from kyuura_engine import EvolvePokemon, Phase, UseAttack, apply_command, check_invariants, validate_deck, DeckValidationError
from kyuura_engine.cards import EnergyType, load_card_pool, read_verification
from kyuura_engine.effects import DEFAULT_EFFECTS, CoinBonusDamageAndParalyze, PoisonOnHeads, PoisonWithoutDamage
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    DIGLETT,
    FOSSIL_GRIMER,
    no_fossil_grimer_pool,
    GRASS,
    GRIMER,
    HITMONCHAN,
    METAPOD,
    CATERPIE,
    MUK,
    RATTATA,
    H,
    T,
    build_test_state,
    coin_results,
    expand_decklist,
    with_coin_results,
)

POISON_GAS = "相手を「どく」状態にする。"
STICKY = "コインを投げて「おもて」なら、20ダメージを追加して、相手を「マヒ」状態にする。"
SLUDGE = "コインを投げて「おもて」なら、相手を「どく」状態にする。"
TURN = 7


def board(active, opponent, *, turn=TURN, **kwargs):
    return build_test_state([{"active": active, "deck": [GRASS] * 5}, {"active": opponent, "deck": [GRASS] * 5}],
                            current_player=0, turn_number=turn, **kwargs)


def events(old, new, kind=None):
    found = [dict(e) for e in new.log[len(old.log):]]
    return found if kind is None else [e for e in found if e["kind"] == kind]


def attack(state, index, *coins):
    """ワザを使う（``coins`` はワザの説明のコイン）。番の終わりまで進むので、ワザの範囲のログ（attack から turn_end の前まで）も返す。"""
    new = apply_command(with_coin_results(state, *coins) if coins else state, UseAttack(0, index))
    found = events(state, new)
    end = next((i for i, e in enumerate(found) if e["kind"] in ("turn_end", "knock_out")), len(found))
    return new, found[:end]


class CardValuesTest(unittest.TestCase):
    def test_grimer(self):
        """p.45: たね、HP 40、草、弱点 超（×2）、抵抗力なし、にげる 1、どくガス（草。目安なし）・ねばりつく（草草。10+）。"""
        pool = load_card_pool()
        d = pool.get(GRIMER)
        self.assertTrue(pool.is_playable(GRIMER) and d.is_basic_pokemon)
        self.assertEqual((d.name_ja, d.hp, d.pokemon_type, d.weakness, d.resistance, d.retreat_cost, d.powers),
                         ("ベトベター", 40, EnergyType.GRASS, EnergyType.PSYCHIC, None, 1, ()))
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage, a.damage_modifier, a.text_ja) for a in d.attacks],
                         [("どくガス", ["grass"], None, None, POISON_GAS), ("ねばりつく", ["grass", "grass"], 10, "+", STICKY)])

    def test_registrations(self):
        """登録は照合した最新の説明（p.45・p.48）と同じ。どくガスはダメージのない ``PoisonWithoutDamage``（v0.5 の ``PoisonOpponent`` とは
        別の実装）、ねばりつくは ``CoinBonusDamageAndParalyze(20)``、ヘドロこうげきはビードルの「どくばり」と同じ ``PoisonOnHeads``。"""
        expected = {
            (GRIMER, 0): (PoisonWithoutDamage(), "どくガス", POISON_GAS, "P43 p.45"),
            (GRIMER, 1): (CoinBonusDamageAndParalyze(bonus=20), "ねばりつく", STICKY, "P43 p.45"),
            (MUK, 0): (PoisonOnHeads(), "ヘドロこうげき", SLUDGE, "P43 p.48"),
        }
        records = read_verification()["cards"]
        for (card, index), (effect, name, text, source) in expected.items():
            entry = DEFAULT_EFFECTS.attack_entry(card, index)
            self.assertEqual((entry.effect, entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (effect, name, text, text, source))
            latest = records[card]["latest_description_ja"]
            self.assertEqual(latest[str(index)] if isinstance(latest, dict) else latest, text)
        self.assertEqual((records[GRIMER]["page"], records[GRIMER]["status"]), (45, "一致"))

    def test_checks(self):
        """``check`` は、ダメージの目安のあるワザへのどくガスの実装・「+」のないワザへのねばりつくの実装を問題にする。"""
        pool = load_card_pool()
        sticky, gas = pool.get(GRIMER).attacks[1], pool.get(GRIMER).attacks[0]
        self.assertEqual(PoisonWithoutDamage().check(gas), [])
        self.assertTrue(PoisonWithoutDamage().check(sticky))
        self.assertEqual(CoinBonusDamageAndParalyze(bonus=20).check(sticky), [])
        self.assertTrue(CoinBonusDamageAndParalyze(bonus=20).check(gas))
        self.assertTrue(CoinBonusDamageAndParalyze(bonus=20).check(pool.get(MUK).attacks[0]))
        with self.assertRaises(ValueError):
            CoinBonusDamageAndParalyze(bonus=15)

    def test_fossil_grimer_is_a_reference_card(self):
        """化石の秘密のベトベター（p.47）は、ワザの登録がなければデッキに入らない（v0.8〜v0.36 は「ちいさくなる」の実装を登録していない
        参照カードだった。v0.37 で登録したので、その 2 つの登録を除いた登録表 ``NO_FOSSIL_GRIMER_EFFECTS`` で確かめる。製品の登録表では対戦に
        使える。docs/fifteen-reused-effects-v0.37.md）。"""
        pool = no_fossil_grimer_pool()
        self.assertFalse(pool.is_playable(FOSSIL_GRIMER))
        self.assertTrue(any("ちいさくなる" in r for r in pool.get(FOSSIL_GRIMER).unsupported_reasons))
        with self.assertRaises(DeckValidationError):
            validate_deck(expand_decklist({FOSSIL_GRIMER: 4, GRASS: 56}), pool)
        self.assertTrue(load_card_pool().is_playable(FOSSIL_GRIMER))  # v0.37
        validate_deck(expand_decklist({FOSSIL_GRIMER: 4, GRASS: 56}), load_card_pool())


class PoisonGasTest(unittest.TestCase):
    def test_poison_gas(self):
        """どくガス: ダメージを与えず（damage のログなし）、コインを投げず（乱数を使わない）、相手をどく状態にする（M1）。もうどくなら重ならない。"""
        state = board({"card": GRIMER, "energy": [GRASS]}, HITMONCHAN)
        fingerprint = rng_fingerprint(state.rng)
        new, found = attack(state, 0)
        self.assertEqual([e["kind"] for e in found], ["attack", "special_condition"])
        self.assertEqual(found[1]["condition"], "poison")
        self.assertEqual(rng_fingerprint(state.rng), fingerprint)
        self.assertNotIn("coin_flip", [e["kind"] for e in events(state, new)])
        again = board({"card": GRIMER, "energy": [GRASS]}, {"card": HITMONCHAN, "poison": 10})
        _, found = attack(again, 0)
        self.assertTrue(found[1].get("already"))

    def test_poison_gas_against_prevented_damage(self):
        """「ダメージを受けない」相手（「かたまる」。v0.4b）にも、どく状態にする（ダメージ以外の効果は受ける）。"""
        state = board({"card": GRIMER, "energy": [GRASS]}, {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1})
        _, found = attack(state, 0)
        self.assertEqual([e["kind"] for e in found][:2], ["attack", "special_condition"])  # そのあと番の終わりに「かたまる」の効果が消える


class StickyHandsTest(unittest.TestCase):
    def test_heads_and_tails(self):
        """ねばりつく（M2〜M5）: コインはダメージの計算の前。「おもて」なら 10 + 20 = 30（基本となるダメージ）でマヒ、「うら」なら 10 でマヒなし。
        弱点（ディグダ。草 ×2。HP 30）は追加のあと: 60（きぜつするのでマヒにしない）・20。"""
        for opponent, heads_damage, tails_damage in ((HITMONCHAN, 30, 10), ({"card": DIGLETT}, 60, 20)):
            state = board({"card": GRIMER, "energy": [GRASS, GRASS]}, opponent)
            for coin, amount, paralyzed in ((H, heads_damage, True), (T, tails_damage, False)):
                with self.subTest(opponent=opponent, coin=coin):
                    new, found = attack(state, 1, coin)
                    kinds = [e["kind"] for e in found]
                    self.assertEqual(kinds[:3], ["attack", "coin_flip", "damage"])
                    self.assertEqual(found[2]["amount"], amount)
                    if amount >= 30 and opponent != HITMONCHAN:
                        self.assertIn("knock_out", [e["kind"] for e in events(state, new)])
                        self.assertNotIn("special_condition", kinds)
                        continue
                    self.assertEqual("special_condition" in kinds, paralyzed)
                    self.assertEqual(new.players[1].active.conditions.paralyzed, paralyzed)
                    self.assertEqual(check_invariants(new), [])

    def test_knock_out_skips_paralysis(self):
        """「おもて」の 30 で相手がきぜつしたら、マヒにしない（対象がいない。p.309・p.323。コインは投げたあと）。"""
        state = build_test_state([{"active": {"card": GRIMER, "energy": [GRASS, GRASS]}, "deck": [GRASS] * 5, "prizes": 2},
                                  {"active": {"card": RATTATA, "damage": 10}, "bench": [RATTATA], "deck": [GRASS] * 5, "prizes": 2}],
                                 current_player=0, turn_number=TURN)
        new = apply_command(with_coin_results(state, H), UseAttack(0, 1))
        kinds = [e["kind"] for e in events(state, new)]
        self.assertIn("knock_out", kinds)
        self.assertNotIn("special_condition", kinds)
        self.assertEqual(coin_results(new, len(state.log)), ["heads"])

    def test_prevented_target_still_flips_and_paralyzes(self):
        """「ダメージを受けない」相手（M6）: ダメージの要素は無効（damage_prevented）だが、コインはマヒにするかも決めるので投げ、「おもて」なら
        マヒ（「ダメージ以外の効果は受ける」）。``CoinFlipDamage`` の UNRESOLVED_PREVENTED_COIN_DAMAGE（コインがダメージの量だけを決める）
        には当たらない。"""
        defender = {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1}
        state = board({"card": GRIMER, "energy": [GRASS, GRASS]}, defender)
        for coin, paralyzed in ((H, True), (T, False)):
            with self.subTest(coin=coin):
                new, found = attack(state, 1, coin)
                kinds = [e["kind"] for e in found]
                self.assertEqual(kinds[:3], ["attack", "coin_flip", "damage_prevented"])
                self.assertEqual(new.players[1].active.conditions.paralyzed, paralyzed)

    def test_confused_grimer(self):
        """こんらんのベトベターのねばりつく: こんらんのコインが「うら」なら、ワザのコインは投げず、自分に 20（M7。v0.3c）。"""
        state = board({"card": GRIMER, "energy": [GRASS, GRASS], "confusion": True}, HITMONCHAN)
        new = apply_command(with_coin_results(state, T), UseAttack(0, 1))
        found = events(state, new)
        self.assertEqual([e["result"] for e in found if e["kind"] == "coin_flip"], ["tails"])
        self.assertEqual([e["amount"] for e in found if e["kind"] == "confusion_damage"], [20])


class SludgeTest(unittest.TestCase):
    def test_sludge(self):
        """ヘドロこうげき（M8）: 相手に 30 → コイン →「おもて」ならどく。相手がきぜつしたらコインを投げない。"""
        state = board({"card": MUK, "evolved_from": GRIMER, "energy": [GRASS] * 3}, HITMONCHAN)
        for coin, poisoned in ((H, True), (T, False)):
            with self.subTest(coin=coin):
                new, found = attack(state, 0, coin)
                self.assertEqual([e["kind"] for e in found][:3], ["attack", "damage", "coin_flip"])
                self.assertEqual(found[1]["amount"], 30)
                self.assertEqual(new.players[1].active.conditions.poison is not None, poisoned)


class EvolutionTest(unittest.TestCase):
    def test_grimer_to_muk(self):
        """ロケット団のベトベターからベトベトンに進化できる（名前で決まる。p.310。M9）。ダメージはそのまま、HP は 70。"""
        state = build_test_state([{"active": {"card": GRIMER, "damage": 20}, "hand": [MUK]}, {"active": HITMONCHAN}],
                                 current_player=0, turn_number=TURN)
        muk = next(u for u in state.players[0].hand if state.cards[u].card_id == MUK)
        new = apply_command(state, EvolvePokemon(0, muk, state.players[0].active.pokemon_id))
        self.assertEqual((new.cards[new.players[0].active.card].card_id, new.players[0].active.damage, new.phase), (MUK, 20, Phase.MAIN))
        self.assertEqual(new.card_def(new.players[0].active.card).hp, 70)


if __name__ == "__main__":
    unittest.main()

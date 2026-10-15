"""v0.28: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、既存の効果の型で加えたポケモン 10 枚の対戦（docs/existing-effect-pokemon-v0.28.md 6 章）。

検証用デッキ ``W28``（ラプラス・ヒトデマン/スターミー・トサキント/アズマオウ・シェルダー・ラッキー・水）と ``G28``（カイロス・タマタマ・プリン・
スリープ・草・超）の対戦を、tools/existing_effect_games.py の手順（v0.26 の手順に、v0.28 のカードがまだ使っていないワザを選ぶ手順だけを重ねた
もの）で進める。seed は 0・1 を席を入れかえて使う（4 局。seed を探し回っていない。この 4 局で 10 枚の 19 のワザがすべて使われ、スターミー・
アズマオウへの進化が起こる）。第2版の固定のデッキとの組（W28 対 B2・G28 対 A2）も seed 0 を 1 局ずつ。

どの局も、通常の勝敗で終わり、受け付けた操作の列を ``new_game`` からやり直したログが元の対戦と同じで、不変条件・ログの監査・書き出しの監査・
トレーナーのログの並び・決定ごとの持ち主と使用中のカードの確かめが通る（``audit``）。勝敗は終わり方の確かめにだけ使う（カードの強さを判断しない）。
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS, preset_deck
from kyuura_engine.cards import load_card_pool
from tests.helpers import CHANSEY, EXEGGCUTE, LAPRAS, SEAKING, SHELLDER, STARMIE, V0_28_POKEMON
from tests.test_existing_effect_pokemon_v0_28 import EXPECTED
from tools import existing_effect_games as games

NEW_PAIR = (("W28", "G28"), ("G28", "W28"))
SEEDS = (0, 1)
MIXED = ((("W28", "B2"), 0), (("G28", "A2"), 0))


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class NewCardGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed, keep_state=True) for seat in NEW_PAIR for seed in SEEDS]
        cls.mixed = [games.play(seat, seed, keep_state=True) for seat, seed in MIXED]

    def test_games_end_normally_and_pass_the_audits(self):
        for r in self.results + self.mixed:
            with self.subTest(decks=r["decks"], seed=r["seed"]):
                self.assertEqual(r["outcome"], "game_over")
                self.assertEqual(r["audit"], {})
                self.assertEqual(r["trainer_sequence_problems"], [])

    def test_every_attack_is_used_from_new_game(self):
        """4 局で、10 枚がどれも場に出て（スターミー・アズマオウは進化で）、19 のワザがどれも宣言され、相手へのダメージ・効果のログがある。"""
        counted = totals(self.results)
        for card_id in V0_28_POKEMON:
            uses = counted.get(card_id, Counter())
            self.assertGreater(uses["evolved_to" if card_id in (STARMIE, SEAKING) else "in_play"], 0, card_id)
        for card_id, index in EXPECTED:
            self.assertGreater(counted[card_id][f"attack#{index}"], 0, (card_id, index))

    def test_attack_results_in_the_log(self):
        """ワザごとの結果のログ: ラプラスの「みずでっぽう」は多い「水」で基本となるダメージが 10 より大きくなり、30 を超えない。スターミーは
        「水」をトラッシュしてすべてとりのぞく。ラッキーの「すてみタックル」は自分に 80。タマタマの「やどりぎのタネ」は回復のログ。シェルダーの
        「ちょうおんぱ」はダメージのログなしでこんらん。"""
        counted = totals(self.results)
        lapras_bases = {int(k.split("=")[1]) for k in counted[LAPRAS] if k.startswith("base#0=")}
        self.assertTrue(lapras_bases & {20, 30})
        self.assertLessEqual(max(lapras_bases), 30)
        self.assertEqual(counted[STARMIE]["discard_energy#0"], counted[STARMIE]["remove_all_damage_counters#0"])
        self.assertGreater(counted[STARMIE]["discard_energy#0"], 0)
        self.assertEqual(counted[CHANSEY]["self_damage#1"], counted[CHANSEY]["damage#1"])
        self.assertGreater(counted[CHANSEY]["self_damage#1"], 0)
        self.assertGreater(counted[EXEGGCUTE]["drain_heal#1"], 0)
        self.assertGreater(counted[SHELLDER]["special_condition_confusion#0"], 0)
        self.assertEqual(counted[SHELLDER]["damage#0"], 0)
        for r in self.results:
            state = r["state"]
            for e in state.log:
                if e["kind"] == "damage" and e.get("target") == "self" and state.cards[e["pokemon"]].card_id == CHANSEY:
                    self.assertEqual(e["steps"][0], ("1 基本となる計算", 80))
                if e["kind"] == "discard_energy" and state.cards[e["pokemon"]].card_id == STARMIE:
                    self.assertEqual(state.card_def(e["energy"]).provides.name, "WATER")

    def test_counts_match_the_log(self):
        """数えた宣言の回数は、ログの ``attack`` の数と同じ（数え方の確かめ）。"""
        for r in self.results:
            state = r["state"]
            logged = Counter((state.cards[e["pokemon"]].card_id, e["attack_index"]) for e in state.log if e["kind"] == "attack")
            for (card_id, index), n in logged.items():
                if card_id in V0_28_POKEMON:
                    self.assertEqual(r["card_uses"][card_id][f"attack#{index}"], n)


class ToolTest(unittest.TestCase):
    def test_verification_decks(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える（対応済みのカードと基本エネルギーだけ）。公開の固定のデッキには入れていない。"""
        pool = load_card_pool()
        for label in games.DECKS:
            cards = games.deck_cards(label)
            self.assertEqual(len(cards), 60)
            self.assertTrue(all(pool.is_playable(c) for c in cards), label)
        self.assertTrue(set(V0_28_POKEMON) <= set(games.deck_cards("W28")) | set(games.deck_cards("G28")))
        self.assertEqual(games.deck_cards("B2"), preset_deck(games.PRESETS["B2"]).cards())
        self.assertFalse(any(set(V0_28_POKEMON) & set(deck.cards()) for deck in PRESET_DECKS.values()))
        with self.assertRaises(ValueError):
            games.deck_cards("X")


if __name__ == "__main__":
    unittest.main()

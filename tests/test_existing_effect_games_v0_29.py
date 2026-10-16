"""v0.29: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、既存の効果の型で加えたポケモン 14 枚（kyuura データの採用）の対戦
（docs/existing-effect-pokemon-v0.29.md 4.2）。

検証用デッキ ``GW29``（アーボ・ズバット・ナゾノクサ・ドガース・タケシのズバット・ニョロモ・カスミのトサキント・草・水）と ``LF29``（ビリリダマ・
マチスのコイル・マチスのビリリダマ・ワンリキー・タケシのイシツブテ・ミニリュウ・タケシのベロリンガ・雷・闘）の対戦を、tools/existing_effect_games.py の
手順（v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順だけを重ねたもの）で進める。seed は 0・1・2 を席を入れかえて
使う（6 局。最初の 3 つの seed で、14 枚の 24 のワザがすべて使われる。seed を探し回っていない）。第2版の固定のデッキとの組（GW29 対 B2・LF29 対
A2）も seed 0 を 1 局ずつ。

どの局も、通常の勝敗で終わり、受け付けた操作の列を ``new_game`` からやり直したログが元の対戦と同じで、不変条件・ログの監査・書き出しの監査・
トレーナーのログの並び・決定ごとの持ち主と使用中のカードの確かめが通る（``audit``）。勝敗は終わり方の確かめにだけ使う（カードの強さを判断しない）。
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS, preset_deck
from kyuura_engine.cards import load_card_pool
from kyuura_engine.effects import DAMAGE_ONLY, CoinFlipDamage
from tests.helpers import MISTYS_GOLDEEN, POLIWAG, ROCKET_ODDISH, V0_29_POKEMON
from tests.test_existing_effect_pokemon_v0_29 import EXPECTED
from tools import existing_effect_games as games

NEW_PAIR = (("GW29", "LF29"), ("LF29", "GW29"))
SEEDS = (0, 1, 2)
MIXED = ((("GW29", "B2"), 0), (("LF29", "A2"), 0))
STATUS = {  # 特殊状態のワザと、与える特殊状態
    ("PMCG4-001", 1): "poison", ("PMCG4-005", 1): "poison", ("PMCG5-001", 1): "poison", ("PMCG4-051", 0): "paralysis",
    ("PMCG5-037", 0): "paralysis", (ROCKET_ODDISH, 0): "sleep", (ROCKET_ODDISH, 1): "poison", (MISTYS_GOLDEEN, 1): "confusion",
}
NO_DAMAGE = ((ROCKET_ODDISH, 0), (ROCKET_ODDISH, 1), (MISTYS_GOLDEEN, 1))
NO_COIN = ((ROCKET_ODDISH, 0), (ROCKET_ODDISH, 1))


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
                self.assertEqual({k for k in r["observed"] if "unexpected" in k}, set())

    def test_every_attack_is_used_from_new_game(self):
        """6 局で、14 枚がどれも場に出て、24 のワザがどれも宣言される。"""
        counted = totals(self.results)
        for card_id in V0_29_POKEMON:
            self.assertGreater(counted.get(card_id, Counter())["in_play"], 0, card_id)
        for card_id, index in EXPECTED:
            self.assertGreater(counted[card_id][f"attack#{index}"], 0, (card_id, index))

    def test_attack_results_in_the_log(self):
        """ワザごとの結果のログ: コインのダメージの基本となるダメージは「おもて」の数 × 1 枚あたりのダメージ（0 からコインの枚数ぶんまで）。説明文の
        ないワザは目安の数字。ニョロモの「みずでっぽう」は 10〜30 で、多い「水」で 10 より大きくなる。特殊状態のワザが与えた回数は宣言の回数まで
        で、コインのないねむりごな・どくのこなは与えている（コインの特殊状態は単体テストと 60 局の実行で確かめる）。ダメージのないワザ
        （ねむりごな・どくのこな・ちょうおんぱ）はダメージのログがない。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for (card_id, index), (_, effect, _) in EXPECTED.items():
            with self.subTest(card=card_id, attack=index):
                bases = {int(k.split("=")[1]) for k in counted[card_id] if k.startswith(f"base#{index}=")}
                if isinstance(effect, CoinFlipDamage):
                    self.assertTrue(bases)
                    self.assertLessEqual(bases, {h * effect.damage_per_heads for h in range(effect.coins + 1)})
                elif effect is DAMAGE_ONLY:
                    self.assertEqual(bases, {pool.get(card_id).attacks[index].damage})
                if (card_id, index) in NO_DAMAGE:
                    self.assertEqual(counted[card_id][f"damage#{index}"], 0)
                if (card_id, index) in STATUS:
                    given = counted[card_id][f"special_condition_{STATUS[(card_id, index)]}#{index}"]
                    self.assertLessEqual(given, counted[card_id][f"attack#{index}"])
                    if (card_id, index) in NO_COIN:  # コインのない特殊状態は、使えば与える（コインのワザは 6 局で「おもて」が出るとは限らない）
                        self.assertGreater(given, 0)
        poliwag = {int(k.split("=")[1]) for k in counted[POLIWAG] if k.startswith("base#0=")}
        self.assertTrue(poliwag & {20, 30})
        self.assertLessEqual(poliwag, {10, 20, 30})

    def test_counts_match_the_log(self):
        """数えた宣言の回数は、ログの ``attack`` の数と同じ（数え方の確かめ）。"""
        for r in self.results:
            state = r["state"]
            logged = Counter((state.cards[e["pokemon"]].card_id, e["attack_index"]) for e in state.log if e["kind"] == "attack")
            for (card_id, index), n in logged.items():
                if card_id in V0_29_POKEMON:
                    self.assertEqual(r["card_uses"][card_id][f"attack#{index}"], n)


class ToolTest(unittest.TestCase):
    def test_verification_decks(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える（対応済みのカードと基本エネルギーだけ）。公開の固定のデッキには入れていない。"""
        pool = load_card_pool()
        for label in ("GW29", "LF29"):
            cards = games.deck_cards(label)
            self.assertEqual(len(cards), 60)
            self.assertTrue(all(pool.is_playable(c) for c in cards), label)
        self.assertEqual(set(V0_29_POKEMON), (set(games.deck_cards("GW29")) | set(games.deck_cards("LF29"))) & set(V0_29_POKEMON))
        self.assertEqual(games.deck_cards("A2"), preset_deck(games.PRESETS["A2"]).cards())
        self.assertFalse(any(set(V0_29_POKEMON) & set(deck.cards()) for deck in PRESET_DECKS.values()))
        self.assertEqual(games.BATCHES["v0.29"], games.PAIRINGS_V0_29)
        self.assertFalse(set(V0_29_POKEMON) & {c for label in ("W28", "G28") for c in games.deck_cards(label)})


if __name__ == "__main__":
    unittest.main()

"""v0.32: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、13 枚の対戦（docs/bench-search-counter-drain-v0.32.md 6 章）。

検証用デッキ 2 つ（tools/existing_effect_games.py の ``G32``: 草（ニドラン♀・ニドリーナ・ナゾノクサ（第2弾）と第4弾のナゾノクサ・マダツボミ・ウツドン・
コンパン・ズバット（化石の秘密）・ゴルバット）、``W32``: 水・超（コイキング・ギャラドス・クラブ・キングラー・ルージュラ））を、互いと第2版の固定のデッキに
当てる 3 組（``PAIRINGS_V0_32``）に分け、席を入れかえて seed 0〜5（36 局。最初の 6 つの seed。seed を探し回っていない）で進める。手順は v0.26 から
変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順を重ねたもの（対戦相手の AI ではない）。

36 局で、13 枚がどれも場に出て（進化先 5 枚は通常の進化の操作で）、26 のワザがどれも使われ、山札からベンチに出すワザでカードがベンチに出て、
きゅうけつで回復する。終わり方は通常の勝敗か、対戦準備の既知の未解決（``UNRESOLVED_MULLIGAN_COMPENSATION``）による停止だけで、受け付けた操作の列を
``new_game`` からやり直したログが元の対戦と同じで、不変条件・ログの監査（山札からベンチに出したカード・すぐあとの山札を切る処理・回復の数も）・書き出しの
監査が通る（``audit``）。原典で決められない場面（CD4）と使えないワザ（ベンチに空きがない）で拒否されたワザは、場から止まるのが正しいことを確かめてから
（``V031_STOPS``）別の操作を続ける。勝敗は終わり方の確かめにだけ使う（カードの強さ・デッキの釣り合いを判断しない）。
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS
from kyuura_engine.cards import load_card_pool
from tests.helpers import (
    BELLSPROUT,
    FOSSIL_ZUBAT,
    GOLBAT,
    JUNGLE_ODDISH,
    KRABBY,
    NIDORAN_F,
    V0_32_POKEMON,
    VENONAT,
)
from tools import existing_effect_games as games

SEEDS = range(6)


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class BenchSearchCounterDrainGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed) for a, b in games.PAIRINGS_V0_32 for seat in ((a, b), (b, a)) for seed in SEEDS]

    def test_games_end_normally_and_pass_the_audits(self):
        self.assertEqual(len(self.results), 36)
        outcomes = Counter()
        for r in self.results:
            outcomes[r["outcome"]] += 1
            with self.subTest(decks=r["decks"], seed=r["seed"]):
                self.assertIn(r["outcome"], ("game_over", "halted"))
                if r["outcome"] == "halted":
                    self.assertEqual(r["halt_code"], "UNRESOLVED_MULLIGAN_COMPENSATION")  # 対戦準備の既知の未解決（v0.20 から。避けるためにデッキを変えない）
                self.assertEqual(r["audit"], {})
                self.assertEqual(r["trainer_sequence_problems"], [])
                self.assertEqual({k for k in r["observed"] if "unexpected" in k}, set())
        self.assertGreater(outcomes["game_over"], 30)

    def test_every_card_and_attack_is_used(self):
        """36 局で、13 枚がどれも場に出て、26 のワザがどれも使われる。山札からベンチに出すワザの 4 枚はどれもカードをベンチに出し、きゅうけつの 3 枚は
        どれも回復する。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for card_id in V0_32_POKEMON:
            uses = counted.get(card_id, Counter())
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                key = "in_play" if definition.stage == "basic" else "evolved_to"
                self.assertGreater(uses[key], 0)
                for attack in definition.attacks:
                    self.assertGreater(uses[f"attack#{attack.index}"], 0, attack.name_ja)
        for card_id, index in ((NIDORAN_F, 1), (JUNGLE_ODDISH, 1), (BELLSPROUT, 1), (KRABBY, 0)):
            self.assertGreater(counted[card_id][f"bench_from_deck#{index}"], 0, card_id)
        for card_id in (VENONAT, FOSSIL_ZUBAT, GOLBAT):
            self.assertGreater(counted[card_id]["drain_heal#1"], 0, card_id)
        self.assertGreater(sum(counted[c]["benched_from_deck"] for c in counted), 0)

    def test_stops_are_the_documented_ones(self):
        """止まったワザ・拒否されたワザは、原典で決められない場面（v0.32 の CD4 と、v0.30 までのこんらんの 20 の変更効果・コインのダメージの要素の
        無効）と、ベンチに空きがなくて使えないワザだけ。場から止まるのが正しいことは、対戦の中で確かめている（``V031_STOPS``）。"""
        found = Counter()
        for r in self.results:
            found.update(r["unresolved_rejections"])
        allowed = {f"stopped_attack_{code}" for code in games.V031_STOPS} | {
            "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE"}
        self.assertTrue(set(found) <= allowed, set(found) - allowed)


class ToolTest(unittest.TestCase):
    def test_verification_decks(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える。13 枚はどれかのデッキに入る。公開の固定のデッキ・前の版の検証用デッキには入れていない。"""
        pool = load_card_pool()
        cards = set()
        for label in ("G32", "W32"):
            deck = games.deck_cards(label)
            self.assertEqual(len(deck), 60)
            self.assertTrue(all(pool.is_playable(c) for c in deck))
            cards |= set(deck)
        self.assertTrue(set(V0_32_POKEMON) <= cards)
        self.assertFalse(any(set(V0_32_POKEMON) & set(deck.cards()) for deck in PRESET_DECKS.values()))
        self.assertFalse(set(V0_32_POKEMON) & {c for label in ("W28", "G28", "GW29", "LF29", "F30", "R31", "K31", "E31", "P31")
                                               for c in games.deck_cards(label)})
        self.assertEqual(games.BATCHES["v0.32"], games.PAIRINGS_V0_32)


if __name__ == "__main__":
    unittest.main()

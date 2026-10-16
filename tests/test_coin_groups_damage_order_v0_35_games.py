"""v0.35: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、5 枚の対戦（docs/coin-groups-damage-order-v0.35.md 6 章）。

検証用デッキ ``S35``（tools/existing_effect_games.py。マチスのコラッタ・マチスのラッタ・カスミのニョロモ・カスミのニョロゾ・カツラのケンタロスと水エネルギー）を、
前の版の検証用デッキ ``C34``（カラカラの「なきつく」を含む）・``G34``・公開の固定のデッキ ``A2`` と 3 組（``PAIRINGS_V0_35``）に分け、席を入れかえて seed 0〜5
（36 局。最初の 6 つの seed。seed を探し回っていない）で進める。手順は v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順を重ねたもの
（対戦相手の AI ではない）。

36 局で、5 枚がどれも場に出て（進化先 2 枚は通常の進化の操作で）、10 のワザがどれも使われ、きあいだめの 2 倍（自分へのダメージも）・あわあわとドわすれの
持続する効果・はかいのうずのトラッシュ・ウォーターパンチのコイン・ぜんりょくとっしんの自分へのダメージが起こる。きあいだめとなきつくの順番の決定も、自然な対戦で
起こる（めずらしい場面の境界は単体テスト。seed を探し回らない）。終わり方は次の分類で数える（勝敗・カードの強さ・デッキの釣り合いは評価しない）:

- 通常の勝敗（``game_over``）
- 既知の裁定による停止（``halted``）
- ``UNRESOLVED_…``・``UNSUPPORTED_…`` でワザの宣言を拒否されたあと、別の操作で続けた回数（終わり方とは別に数える）
- 手数の上限・想定外の拒否・内部エラー・監査の失敗（どれも 0）
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS
from kyuura_engine.cards import load_card_pool
from tests.helpers import BLAINES_TAUROS, LT_SURGES_RATICATE, LT_SURGES_RATTATA, MISTYS_POLIWAG, MISTYS_POLIWHIRL, V0_35_POKEMON
from tools import existing_effect_games as games

SEEDS = range(6)
KNOWN_REJECTIONS = {f"stopped_attack_{code}" for code in games.V031_STOPS} | {
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE"}
KNOWN_HALTS = {"UNRESOLVED_MULLIGAN_COMPENSATION", "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"}


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class CoinGroupsDamageOrderGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed) for a, b in games.PAIRINGS_V0_35 for seat in ((a, b), (b, a)) for seed in SEEDS]

    def test_endings_are_classified_and_pass_the_audits(self):
        """終わり方は通常の勝敗か、既知の未解決による停止だけ（手数の上限・想定外の拒否・内部エラーはない）。どの局も、受け付けた操作の列を ``new_game`` から
        やり直したログが同じで、不変条件・ログの監査（2 段階の「数をかける」効果と順番の決定の記録・あわあわとドわすれで使えないワザを使っていないこと）・
        書き出しの監査が通る。"""
        self.assertEqual(len(self.results), 36)
        outcomes = Counter(r["outcome"] for r in self.results)
        self.assertEqual(set(outcomes) - {"game_over", "halted"}, set())
        for r in self.results:
            with self.subTest(decks=r["decks"], seed=r["seed"]):
                if r["outcome"] == "halted":
                    self.assertIn(r["halt_code"], KNOWN_HALTS)
                self.assertEqual(r["audit"], {})
                self.assertEqual(r["trainer_sequence_problems"], [])
                self.assertEqual({k for k in r["observed"] if "unexpected" in k}, set())
        self.assertGreater(outcomes["game_over"], 30)

    def test_rejections_are_counted_apart_from_halts(self):
        """ワザの宣言を拒否されたあと続けた回数は、停止と分けて数える。拒否のコードは既知のものだけ（あわあわ・ドわすれで使えないワザは ``ATTACK_LOCKED``
        として場から確かめる）。"""
        found = Counter()
        for r in self.results:
            found.update(r["unresolved_rejections"])
        self.assertTrue(set(found) <= KNOWN_REJECTIONS, set(found) - KNOWN_REJECTIONS)

    def test_every_card_and_attack_is_used(self):
        """36 局で、5 枚がどれも場に出て、10 のワザがどれも使われ、それぞれの効果が起こる。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for card_id in V0_35_POKEMON:
            uses = counted.get(card_id, Counter())
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertGreater(uses["in_play" if definition.stage == "basic" else "evolved_to"], 0)
                for attack in definition.attacks:
                    self.assertGreater(uses[f"attack#{attack.index}"], 0, attack.name_ja)
        expected = {
            LT_SURGES_RATTATA: ("persistent_effect_added#0", "damage_multiplied#1"),
            LT_SURGES_RATICATE: ("persistent_effect_added#0", "damage_multiplied#1", "self_damage_multiplied#1", "step_order#1"),
            MISTYS_POLIWAG: ("persistent_effect_added#0", "persistent_effect_added#1"),
            MISTYS_POLIWHIRL: ("discard_attached_energy#0",),
            BLAINES_TAUROS: ("self_damage#1",),
        }
        for card_id, keys in expected.items():
            for key in keys:
                with self.subTest(card=card_id, key=key):
                    self.assertGreater(counted[card_id][key], 0)
        # ウォーターパンチは水エネルギーの数でダメージが変わる（30 + 「おもて」の数 × 10 の 2 つ以上の値）
        self.assertGreater(len([k for k in counted[MISTYS_POLIWHIRL] if k.startswith("base#1=")]), 2)


class ToolTest(unittest.TestCase):
    def test_verification_deck(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える。5 枚はどれも入る。公開の固定のデッキ・前の版の検証用デッキには入れていない。"""
        pool = load_card_pool()
        deck = games.deck_cards("S35")
        self.assertEqual(len(deck), 60)
        self.assertTrue(all(pool.is_playable(c) for c in deck))
        self.assertTrue(set(V0_35_POKEMON) <= set(deck))
        self.assertFalse(any(set(V0_35_POKEMON) & set(d.cards()) for d in PRESET_DECKS.values()))
        for label in ("F34", "G34", "C34"):
            self.assertFalse(set(V0_35_POKEMON) & set(games.deck_cards(label)))


if __name__ == "__main__":
    unittest.main()

"""v0.33: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、15 枚の対戦（docs/cd4-opponent-energy-coins-v0.33.md 6 章）。

検証用デッキ 3 つ（tools/existing_effect_games.py の ``N33``: 草・闘（ニドラン♂・ニドリーノ・サカキのニドラン♀・ナツメのコンパン・タケシのディグダ・
タケシのサイホーン・カツラのサイホーン）、``W33``: 水（コダック・ゴルダック・イーブイ・わるいシャワーズ・シェルダー・パルシェン）、``C33``: 無色・雷（第1弾と
ロケット団のミニリュウ・ハクリュー・コラッタ・わるいラッタ・マチスのコイル・マチスのオニスズメ・カツラのドードー））を 3 組（``PAIRINGS_V0_33``）に分け、
席を入れかえて seed 0〜5（36 局。最初の 6 つの seed。seed を探し回っていない）で進める。手順は v0.26 から変えていない手順に、対象のカードがまだ使って
いないワザを選ぶ手順を重ねたもの（対戦相手の AI ではない）。

36 局で、15 枚がどれも場に出て（進化先 6 枚は通常の進化の操作で）、28 のワザがどれも使われ、相手のエネルギーカードをトラッシュする 5 つのワザがどれも
トラッシュし、控えポケモンへのダメージ（ミニじしん・かけぬける）と、ワザの失敗（コインの「うら」）が起こる。終わり方は、次の分類で数える（勝敗・カードの
強さ・デッキの釣り合いは評価しない）:

- 通常の勝敗（``game_over``）
- 既知の裁定による停止（``halted``。対戦準備の ``UNRESOLVED_MULLIGAN_COMPENSATION`` だけ）
- ``UNRESOLVED_…``（と ``UNSUPPORTED_…``）でワザの宣言を拒否されたあと、別の操作で続けた回数（終わり方とは別に数える。``unresolved_rejections``）
- 手数の上限・想定外の拒否・内部エラー・監査の失敗（どれも 0）
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS
from kyuura_engine.cards import load_card_pool
from tests.helpers import (
    BLAINES_RHYHORN,
    BROCKS_DIGLETT,
    DARK_VAPOREON,
    DRAGONAIR,
    FOSSIL_GOLDUCK,
    LT_SURGES_MAGNEMITE_30,
    SABRINAS_VENONAT,
    V0_33_POKEMON,
)
from tools import existing_effect_games as games

SEEDS = range(6)
# ``UNRESOLVED_…`` で拒否されたあと続けてよいもの: v0.32 までの既知の止める場面（場から確かめる ``V031_STOPS`` と、こんらんの 20 の変更効果・
# コインのダメージの要素の無効（v0.4b。失敗するワザ・つのでつつくを「ダメージを受けない」相手に使ったとき））
KNOWN_REJECTIONS = {f"stopped_attack_{code}" for code in games.V031_STOPS} | {
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE"}


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class OpponentEnergyCoinGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed) for a, b in games.PAIRINGS_V0_33 for seat in ((a, b), (b, a)) for seed in SEEDS]

    def test_endings_are_classified_and_pass_the_audits(self):
        """終わり方は通常の勝敗か、対戦準備の既知の未解決による停止だけ（手数の上限・想定外の拒否・内部エラーはない）。どの局も、受け付けた操作の列を
        ``new_game`` からやり直したログが同じで、不変条件・ログの監査（自分の控えへのダメージ・相手のエネルギーのトラッシュも）・書き出しの監査が通る。"""
        self.assertEqual(len(self.results), 36)
        outcomes = Counter(r["outcome"] for r in self.results)
        self.assertEqual(set(outcomes) - {"game_over", "halted"}, set())
        for r in self.results:
            with self.subTest(decks=r["decks"], seed=r["seed"]):
                if r["outcome"] == "halted":
                    self.assertEqual(r["halt_code"], "UNRESOLVED_MULLIGAN_COMPENSATION")  # 対戦準備の既知の未解決（v0.20 から。避けるためにデッキを変えない）
                self.assertEqual(r["audit"], {})
                self.assertEqual(r["trainer_sequence_problems"], [])
                self.assertEqual({k for k in r["observed"] if "unexpected" in k}, set())
        self.assertGreater(outcomes["game_over"], 30)

    def test_rejections_are_counted_apart_from_halts(self):
        """ワザの宣言を ``UNRESOLVED_…`` で拒否されたあと続けた回数は、停止（``halted``）と分けて数える。拒否のコードは既知のものだけで、拒否された局も
        終わり方は通常の勝敗か既知の停止。"""
        found = Counter()
        for r in self.results:
            found.update(r["unresolved_rejections"])
            if r["unresolved_rejections"]:
                self.assertIn(r["outcome"], ("game_over", "halted"))
                if r["outcome"] == "halted":
                    self.assertEqual(r["halt_code"], "UNRESOLVED_MULLIGAN_COMPENSATION")
        self.assertTrue(set(found) <= KNOWN_REJECTIONS, set(found) - KNOWN_REJECTIONS)

    def test_every_card_and_attack_is_used(self):
        """36 局で、15 枚がどれも場に出て、28 のワザがどれも使われる。相手のエネルギーカードをトラッシュする 5 つのワザはどれもトラッシュし、ミニじしんは
        自分の控えに、かけぬけるは相手の控えにダメージを与える。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for card_id in V0_33_POKEMON:
            uses = counted.get(card_id, Counter())
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                key = "in_play" if definition.stage == "basic" else "evolved_to"
                self.assertGreater(uses[key], 0)
                for attack in definition.attacks:
                    self.assertGreater(uses[f"attack#{attack.index}"], 0, attack.name_ja)
        for card_id, index in ((DRAGONAIR, 1), (FOSSIL_GOLDUCK, 1), (DARK_VAPOREON, 1), (LT_SURGES_MAGNEMITE_30, 0), (SABRINAS_VENONAT, 1)):
            self.assertGreater(counted[card_id][f"discard_attached_energy#{index}"], 0, card_id)
        self.assertGreater(counted[BROCKS_DIGLETT]["self_bench_damage#1"], 0)
        self.assertGreater(counted[BLAINES_RHYHORN]["opponent_bench_damage#1"], 0)
        self.assertGreater(sum(counted[c].get(k, 0) for c in counted for k in counted[c] if k.startswith("attack_failed")), 0)


class ToolTest(unittest.TestCase):
    def test_verification_decks(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える。15 枚はどれかのデッキに入る。公開の固定のデッキ・前の版の検証用デッキには入れていない。"""
        pool = load_card_pool()
        cards = set()
        for label in ("N33", "W33", "C33"):
            deck = games.deck_cards(label)
            self.assertEqual(len(deck), 60)
            self.assertTrue(all(pool.is_playable(c) for c in deck))
            cards |= set(deck)
        self.assertTrue(set(V0_33_POKEMON) <= cards)
        self.assertFalse(any(set(V0_33_POKEMON) & set(deck.cards()) for deck in PRESET_DECKS.values()))
        self.assertFalse(set(V0_33_POKEMON) & {c for label in ("W28", "G28", "GW29", "LF29", "F30", "R31", "K31", "E31", "P31", "G32", "W32")
                                               for c in games.deck_cards(label)})
        self.assertEqual(games.BATCHES["v0.33"], games.PAIRINGS_V0_33)


if __name__ == "__main__":
    unittest.main()

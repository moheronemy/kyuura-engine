"""v0.34: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、14 枚の対戦（docs/barrier-resume-coin-bonus-v0.34.md 7 章）。

検証用デッキ 3 つ（tools/existing_effect_games.py の ``F34``: 炎・雷（ポニータ・ギャロップ・イーブイ・ブースター・サンダース・タケシのロコン・エレブー）、
``G34``: 草・超（ドガース・ニドラン♂・ニドリーノ・ニドキング・タマタマ・ナッシー・サカキのカイロス）、``C34``: 無色・闘・水（ケンタロス・カツラのガルーラ・
カラカラ・ガラガラ・イーブイ・シャワーズ・ディグダ））を 3 組（``PAIRINGS_V0_34``）に分け、席を入れかえて seed 0〜5（36 局。最初の 6 つの seed。seed を
探し回っていない）で進める。手順は v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順を重ねたもの（対戦相手の AI ではない）。

36 局で、14 枚がどれも場に出て（進化先 7 枚は通常の進化の操作で）、27 のワザがどれも使われ、うしろなげの自分の控えへのダメージ・テレポートの入れ替え・
たすけをよぶ・どくどくの特殊などく・こうそくいどうとなきつくの持続する効果・くさいガスのどくとこんらん・こどもパンチの失敗・かえんほうしゃのトラッシュが
起こる。終わり方は、次の分類で数える（勝敗・カードの強さ・デッキの釣り合いは評価しない）:

- 通常の勝敗（``game_over``）
- 既知の裁定による停止（``halted``。対戦準備の ``UNRESOLVED_MULLIGAN_COMPENSATION`` などの既知のもの）
- ``UNRESOLVED_…``（と ``UNSUPPORTED_…``）でワザの宣言を拒否されたあと、別の操作で続けた回数（終わり方とは別に数える。``unresolved_rejections``）
- 手数の上限・想定外の拒否・内部エラー・監査の失敗（どれも 0）
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS
from kyuura_engine.cards import load_card_pool
from tests.helpers import (
    BLAINES_KANGASKHAN,
    CUBONE,
    EXEGGUTOR,
    FLAREON,
    GIOVANNIS_PINSIR,
    KOFFING,
    MAROWAK,
    NIDOKING,
    RAPIDASH,
    TAUROS,
    V0_34_POKEMON,
)
from tools import existing_effect_games as games

SEEDS = range(6)
# ``UNRESOLVED_…`` で拒否されたあと続けてよいもの: 既知の止める場面（場から確かめる ``V031_STOPS`` と、こんらんの 20 の変更効果・コインのダメージの要素の
# 無効（v0.4b。失敗するワザ・コインのダメージのワザを「ダメージを受けない」「ワザをうけない」相手に使ったとき））
KNOWN_REJECTIONS = {f"stopped_attack_{code}" for code in games.V031_STOPS} | {
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE"}
KNOWN_HALTS = {"UNRESOLVED_MULLIGAN_COMPENSATION", "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"}


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class BarrierResumeCoinBonusGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed) for a, b in games.PAIRINGS_V0_34 for seat in ((a, b), (b, a)) for seed in SEEDS]

    def test_endings_are_classified_and_pass_the_audits(self):
        """終わり方は通常の勝敗か、既知の未解決による停止だけ（手数の上限・想定外の拒否・内部エラーはない）。どの局も、受け付けた操作の列を ``new_game`` から
        やり直したログが同じで、不変条件・ログの監査（特殊などくの量・なきつくの 2 段階と期限・テレポートの入れ替え・たすけをよぶのタイプも）・書き出しの
        監査が通る。"""
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
        """ワザの宣言を ``UNRESOLVED_…`` で拒否されたあと続けた回数は、停止（``halted``）と分けて数える。拒否のコードは既知のものだけ。"""
        found = Counter()
        for r in self.results:
            found.update(r["unresolved_rejections"])
            if r["unresolved_rejections"]:
                self.assertIn(r["outcome"], ("game_over", "halted"))
        self.assertTrue(set(found) <= KNOWN_REJECTIONS, set(found) - KNOWN_REJECTIONS)

    def test_every_card_and_attack_is_used(self):
        """36 局で、14 枚がどれも場に出て、27 のワザがどれも使われ、それぞれの効果が起こる。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for card_id in V0_34_POKEMON:
            uses = counted.get(card_id, Counter())
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                key = "in_play" if definition.stage == "basic" else "evolved_to"
                self.assertGreater(uses[key], 0)
                for attack in definition.attacks:
                    self.assertGreater(uses[f"attack#{attack.index}"], 0, attack.name_ja)
        expected = {
            GIOVANNIS_PINSIR: "self_bench_damage#1", EXEGGUTOR: "switch#0", MAROWAK: "bench_from_deck#1", NIDOKING: "special_condition_poison#1",
            RAPIDASH: "persistent_effect_added#1", CUBONE: "persistent_effect_added#0", KOFFING: "special_condition_confusion#0",
            BLAINES_KANGASKHAN: "attack_failed#0", FLAREON: "discard_energy#1", TAUROS: "special_condition_confusion#1",
        }
        for card_id, key in expected.items():
            with self.subTest(card=card_id, key=key):
                self.assertGreater(counted[card_id][key], 0)
        self.assertGreater(counted[KOFFING]["special_condition_poison#0"], 0)


class ToolTest(unittest.TestCase):
    def test_verification_decks(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える。14 枚はどれかのデッキに入る。公開の固定のデッキ・前の版の検証用デッキには入れていない。"""
        pool = load_card_pool()
        cards = set()
        for label in ("F34", "G34", "C34"):
            deck = games.deck_cards(label)
            self.assertEqual(len(deck), 60)
            self.assertTrue(all(pool.is_playable(c) for c in deck))
            cards |= set(deck)
        self.assertTrue(set(V0_34_POKEMON) <= cards)
        self.assertFalse(any(set(V0_34_POKEMON) & set(deck.cards()) for deck in PRESET_DECKS.values()))
        self.assertFalse(set(V0_34_POKEMON) & {c for label in ("W28", "G28", "GW29", "LF29", "F30", "R31", "K31", "E31", "P31", "G32", "W32", "N33",
                                                              "W33", "C33") for c in games.deck_cards(label)})
        self.assertEqual(games.BATCHES["v0.34"], games.PAIRINGS_V0_34)


if __name__ == "__main__":
    unittest.main()

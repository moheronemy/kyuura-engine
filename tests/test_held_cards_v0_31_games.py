"""v0.31: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、v0.30 で保留した 22 枚と進化元 7 枚の対戦（docs/held-cards-v0.31.md 7 章）。

検証用デッキ 4 つ（tools/existing_effect_games.py の ``R31``: 炎の進化系統（リザードン・わるいリザードン・キュウコン・わるいギャロップ・わるいブースター・
ファイヤー）、``K31``: カツラのポケモン、``E31``: 雷・超（サンダー・マチスのポケモン・わるいマルマイン・ゴース・ミュウツー）、``P31``: 超・水（ヤドン・
ピッピとピクシー・コダックとわるいゴルダック・カスミのポケモン））を、効果を確かめられる 4 組（``PAIRINGS_V0_31``）に分け、席を入れかえて seed 0〜5
（48 局。最初の 6 つの seed。seed を探し回っていない）で進める。手順は v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順・
v0.31 のワザの決定への答え・特殊能力の使用・エネルギーをためるために番を終える手順を重ねたもの（対戦相手の AI ではない）。

48 局で、29 枚がどれも場に出て（1 進化・2 進化は通常の進化の操作で）、52 のワザと 3 つの特殊能力がどれも使われる。どの局も通常の勝敗で終わり、
受け付けた操作の列を ``new_game`` からやり直したログが元の対戦と同じで、不変条件・ログの監査（v0.31 のワザのエネルギーのトラッシュ・カードの移動・
特殊能力のログも）・書き出しの監査・決定ごとの持ち主の確かめが通る（``audit``）。原典で決められない場面で止まったワザは、場から止まるのが正しいことを
確かめてから（``V031_STOPS``）別の操作を続ける。勝敗は終わり方の確かめにだけ使う（カードの強さ・デッキの釣り合いを判断しない）。
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS
from kyuura_engine.cards import load_card_pool
from tests.helpers import CHARIZARD, BLAINES_NINETALES, BLAINES_VULPIX, V0_31_POKEMON
from tools import existing_effect_games as games

SEEDS = range(6)


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class HeldCardGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed) for a, b in games.PAIRINGS_V0_31 for seat in ((a, b), (b, a)) for seed in SEEDS]

    def test_games_end_normally_and_pass_the_audits(self):
        self.assertEqual(len(self.results), 48)
        for r in self.results:
            with self.subTest(decks=r["decks"], seed=r["seed"]):
                self.assertEqual(r["outcome"], "game_over")
                self.assertEqual(r["audit"], {})
                self.assertEqual(r["trainer_sequence_problems"], [])
                self.assertEqual({k for k in r["observed"] if "unexpected" in k}, set())

    def test_every_card_attack_and_power_is_used(self):
        """48 局で、29 枚がどれも場に出て、52 のワザと 3 つの特殊能力がどれも使われる。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for card_id in V0_31_POKEMON:
            uses = counted.get(card_id, Counter())
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                key = "in_play" if definition.stage == "basic" else "evolved_to"
                self.assertGreater(uses[key], 0)
                for attack in definition.attacks:
                    self.assertGreater(uses[f"attack#{attack.index}"], 0, attack.name_ja)
        self.assertGreater(counted[CHARIZARD]["energy_burn"], 0)
        self.assertGreater(counted[BLAINES_VULPIX]["power_heal"], 0)
        self.assertGreater(counted[BLAINES_NINETALES]["power_heal_on_attach"], 0)

    def test_stops_are_the_documented_ones(self):
        """止まったワザ・拒否されたワザは、原典で決められない場面（v0.31 の HC4・HC6・HC9 と、v0.30 までのこんらんの 20 の変更効果・コインのダメージの
        要素の無効）だけ。場から止まるのが正しいことは、対戦の中で確かめている（``V031_STOPS``・``extra_stop``）。"""
        found = Counter()
        for r in self.results:
            found.update(r["unresolved_rejections"])
        allowed = {f"stopped_attack_{code}" for code in games.V031_STOPS} | {
            "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE"}
        self.assertTrue(set(found) <= allowed, set(found) - allowed)

    def test_decisions_were_answered(self):
        """v0.31 のワザの決定（トラッシュ・相手のエネルギー・控えにつける・トラッシュからつける・トレーナーの回収・相手のワザ・入れ替え）にどれも答えた。"""
        policy = Counter()
        for r in self.results:
            policy.update(r["policy"])
        for kind in ("discard_energy", "discard_opponent_energy", "attach_to_bench", "attach_from_discard", "recover_trainer", "forced_switch",
                     "select_pokemon"):
            self.assertTrue(any(k.startswith(f"v031_decision_{kind}_") for k in policy), kind)
        self.assertGreater(policy["v031_select_attack"], 0)


class ToolTest(unittest.TestCase):
    def test_verification_decks(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える。29 枚はどれかのデッキに入る。公開の固定のデッキ・前の版の検証用デッキには入れていない。"""
        pool = load_card_pool()
        cards = set()
        for label in ("R31", "K31", "E31", "P31"):
            deck = games.deck_cards(label)
            self.assertEqual(len(deck), 60)
            self.assertTrue(all(pool.is_playable(c) for c in deck))
            cards |= set(deck)
        self.assertTrue(set(V0_31_POKEMON) <= cards)
        self.assertFalse(any(set(V0_31_POKEMON) & set(deck.cards()) for deck in PRESET_DECKS.values()))
        self.assertFalse(set(V0_31_POKEMON) & {c for label in ("W28", "G28", "GW29", "LF29", "F30") for c in games.deck_cards(label)})
        self.assertEqual(games.BATCHES["v0.31"], games.PAIRINGS_V0_31)


if __name__ == "__main__":
    unittest.main()

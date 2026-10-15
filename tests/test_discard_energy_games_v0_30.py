"""v0.30: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、エネルギーをトラッシュしてダメージを与えるワザで加えたポケモン 5 枚の対戦
（docs/discard-energy-attacks-v0.30.md 6 章）。

検証用デッキ ``F30``（ヒトカゲ・リザード・ガーディ・ウインディ・ブーバー・第4弾ロケット団のポニータ・炎エネルギー）と、第2版の固定のデッキ
（``B2``: フシギバナ・パラセクト。``A2``: エビワラー・ジュゴン）・v0.28 の検証用デッキ ``G28`` の対戦を、tools/existing_effect_games.py の手順
（v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順だけを重ねたもの）で進める。3 組を席を入れかえて seed 0・1・2 で
（18 局。最初の 3 つの seed。seed を探し回っていない）。18 局で、5 枚が場に出て（リザード・ウインディは通常の進化の操作で）、9 のワザがどれも
宣言される。

どの局も、通常の勝敗で終わり、受け付けた操作の列を ``new_game`` からやり直したログが元の対戦と同じで、不変条件・ログの監査（v0.30 からワザの
エネルギーのトラッシュの数・順番・種類も）・書き出しの監査・トレーナーのログの並び・決定ごとの持ち主と使用中のカードの確かめが通る（``audit``）。
勝敗は終わり方の確かめにだけ使う（カードの強さ・デッキの釣り合いを判断しない）。
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS, preset_deck
from kyuura_engine.cards import EnergyType, load_card_pool
from kyuura_engine.effects import DiscardEnergyThenDamage
from tests.helpers import ARCANINE, CHARMANDER, CHARMELEON, V0_30_POKEMON
from tests.test_discard_energy_attacks_v0_30 import DISCARD_ATTACKS, EXPECTED
from tools import existing_effect_games as games

SEATS = (("F30", "B2"), ("B2", "F30"), ("F30", "A2"), ("A2", "F30"), ("F30", "G28"), ("G28", "F30"))
SEEDS = (0, 1, 2)


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class FireGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed, keep_state=True) for seat in SEATS for seed in SEEDS]

    def test_games_end_normally_and_pass_the_audits(self):
        for r in self.results:
            with self.subTest(decks=r["decks"], seed=r["seed"]):
                self.assertEqual(r["outcome"], "game_over")
                self.assertEqual(r["audit"], {})
                self.assertEqual(r["trainer_sequence_problems"], [])
                self.assertEqual({k for k in r["observed"] if "unexpected" in k}, set())

    def test_every_card_and_attack_is_used_from_new_game(self):
        """18 局で、5 枚がどれも場に出て（リザード・ウインディは進化で）、9 のワザがどれも宣言される。"""
        counted = totals(self.results)
        for card_id in V0_30_POKEMON:
            uses = counted.get(card_id, Counter())
            self.assertGreater(uses["in_play"] + uses["evolved_to"], 0, card_id)
        self.assertGreater(counted[CHARMELEON]["evolved_to"], 0)
        self.assertGreater(counted[ARCANINE]["evolved_to"], 0)
        for card_id, index in EXPECTED:
            self.assertGreater(counted[card_id][f"attack#{index}"], 0, (card_id, index))
        self.assertGreater(counted[CHARMANDER]["in_play"], 0)

    def test_discard_then_damage_in_the_log(self):
        """エネルギーをトラッシュするワザは、宣言（こんらんで「うら」を除く）ごとにトラッシュが 1 回で、そのあとにそのワザのダメージの要素が
        続く。基本となるダメージは目安の数字。ほかのワザはトラッシュしない。とっしんは自分にもダメージ。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for (card_id, index), (_, effect, _, _) in EXPECTED.items():
            with self.subTest(card=card_id, attack=index):
                uses = counted[card_id]
                declared = uses[f"attack#{index}"] - uses[f"confused_failed#{index}"]
                bases = {int(k.split("=")[1]) for k in uses if k.startswith(f"base#{index}=")}
                self.assertEqual(bases, {pool.get(card_id).attacks[index].damage})
                if isinstance(effect, DiscardEnergyThenDamage):
                    self.assertEqual(uses[f"discard_energy#{index}"], declared)
                    self.assertEqual(uses[f"discard_then_damage#{index}"], declared)
                else:
                    self.assertEqual(uses[f"discard_energy#{index}"], 0)
        self.assertEqual(counted[ARCANINE]["self_damage#1"], counted[ARCANINE]["attack#1"] - counted[ARCANINE]["confused_failed#1"])

    def test_discarded_cards_are_attached_fire_energy(self):
        """トラッシュしたカードは、ワザを使ったポケモンについていた「炎」の基本エネルギーカードで、トラッシュに 1 枚だけ増える（ログの監査
        でも確かめる）。"""
        attacks = {f"{card_id}#{index}" for card_id, index, _, _ in DISCARD_ATTACKS}
        seen = 0
        for r in self.results:
            state = r["state"]
            for e in state.log:
                if e["kind"] == "discard_energy" and e["effect"] in attacks:
                    seen += 1
                    definition = state.card_def(e["energy"])
                    self.assertTrue(definition.is_basic_energy)
                    self.assertIs(definition.provides, EnergyType.FIRE)
                    self.assertEqual(state.cards[e["energy"]].owner, e["player"])
        self.assertEqual(seen, sum(totals(self.results)[c][f"discard_energy#{i}"] for c, i, _, _ in DISCARD_ATTACKS))
        self.assertGreater(seen, 0)


class ToolTest(unittest.TestCase):
    def test_verification_deck(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える（対応済みのカードと基本エネルギーだけ）。公開の固定のデッキ・v0.28・v0.29 の
        検証用デッキには入れていない。"""
        pool = load_card_pool()
        cards = games.deck_cards("F30")
        self.assertEqual(len(cards), 60)
        self.assertTrue(all(pool.is_playable(c) for c in cards))
        self.assertEqual(set(V0_30_POKEMON), set(cards) & set(V0_30_POKEMON))
        self.assertFalse(any(set(V0_30_POKEMON) & set(deck.cards()) for deck in PRESET_DECKS.values()))
        self.assertFalse(set(V0_30_POKEMON) & {c for label in ("W28", "G28", "GW29", "LF29") for c in games.deck_cards(label)})
        self.assertEqual(games.BATCHES["v0.30"], games.PAIRINGS_V0_30)
        self.assertEqual(games.deck_cards("B2"), preset_deck(games.PRESETS["B2"]).cards())


if __name__ == "__main__":
    unittest.main()

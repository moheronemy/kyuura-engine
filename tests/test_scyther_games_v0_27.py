"""v0.27: 正式な開始（``new_game``）からのストライク（PMCG2-017）の対戦。docs/scyther-v0.27.md 6〜8 章。

- 構成 B（検証用のデッキ）: 第2版のデッキ B2 のモンジャラ 2 枚をストライク 2 枚に置き換えた B2S（草エネルギー 19 枚。``tools/preset_deck_games.py`` の
  変種 ``scyther_grass``）と A2 の対戦。「つるぎのまい」→ 次の自分の番の強化した「きりさく」（p.321 の 2 段階で 60）・プラスパワーとの順番・
  相手の突風で効果が消える（p.57 のワザ解説の例）・はたらく番にもう一度「つるぎのまい」を使う場面が、手順を変えずに起こる。
- 構成 A: 第2版のデッキ A2 のコラッタ 2 枚をストライク 2 枚に置き換えた A2S（闘・水のエネルギーだけ。変種 ``scyther``）と B2 の対戦。「つるぎのまい」は
  使えず（草エネルギーがない）、「きりさく」は 30。

どの局も、通常の勝敗で終わり、やり直したログが元の対戦と同じで、不変条件・ログの監査・書き出しの監査・トレーナーのログの並び・決定ごとの
持ち主と使用中のカードの確かめが通る（``tools/preset_deck_comparison.game_record``）。seed は比べる道具の seed 0〜9 のうち、その場面が起こった局
（docs/scyther-v0.27.md 7 章。seed を探し回っていない）。公開の固定のデッキは変えていない。
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS, preset_deck
from tests.helpers import GUST, SCYTHER
from tools import preset_deck_comparison as comparison
from tools import preset_deck_games as driver
from tools.scyther_games import scyther_uses

A2, B2 = driver.DECK_A2, driver.DECK_B2
KIND = "next_turn_attack_damage"
# (席, seed): 構成 B（A2 対 B2S）と構成 A（A2S 対 B2）
CONFIG_B = {"boosted": ((A2, B2), 0), "pluspower": ((A2, B2), 8), "gust": ((A2, B2), 6), "again": ((B2, A2), 8)}
CONFIG_A = {"first": ((A2, B2), 0), "second": ((B2, A2), 3)}


def play(seat, seed, variant):
    r = driver.play(seat, seed, keep_state=True, observe=True, variant=variant)
    return r, comparison.game_record(r)


def scyther_cards(state):
    return {uid for uid, card in state.cards.items() if card.card_id == SCYTHER}


def boosted_slashes(state):
    """強化した「きりさく」: (番, ワザを使ったカード, ダメージのログ)。ワザを使ったポケモンはダメージのログの直前の attack のログ。"""
    found, attack = [], None
    for e in state.log:
        if e["kind"] == "attack":
            attack = e
        elif e["kind"] == "damage" and e.get("damage_set"):
            found.append((e["turn"], attack["pokemon"], attack["attack_index"], e))
    return found


class ConfigBGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {name: play(seat, seed, "scyther_grass") for name, (seat, seed) in CONFIG_B.items()}

    def test_games_end_normally_and_pass_the_audits(self):
        for name, (r, record) in self.games.items():
            with self.subTest(game=name):
                self.assertEqual(r["outcome"], "game_over")
                self.assertEqual(record["audit"], {})
                self.assertIn("per_deck", record)  # やり直しと監査をした（一時的なデッキも同じ 60 枚でやり直す）
                self.assertIn("B2S", record["labels"])

    def test_swords_dance_then_boosted_slash(self):
        """「つるぎのまい」を使ったストライクが、次の自分の番（2 番あと）に使った「きりさく」だけが 60（2 段階の記録）。強化したダメージには、
        どれも 2 番前の同じカードの「つるぎのまい」と、その番がはたらく番の効果のログがある。"""
        r, _ = self.games["boosted"]
        state = r["state"]
        found = boosted_slashes(state)
        self.assertTrue(found)
        for turn, card, index, damage in found:
            self.assertEqual((state.cards[card].card_id, index), (SCYTHER, 1))
            self.assertEqual(damage["damage_set"], ((2, card, 60),))
            self.assertIn(("2 つるぎのまい", 60), damage["steps"])
            dances = [e for e in state.log if e["kind"] == "attack" and e["pokemon"] == card and e["attack_index"] == 0 and e["turn"] == turn - 2]
            added = [e for e in state.log if e["kind"] == "persistent_effect_added" and e["persistent_effect"] == KIND
                     and e["pokemon"] == card and e["turn"] == turn - 2 and e["active_turn"] == turn]
            self.assertEqual((len(dances), len(added)), (1, 1))
        # 効果のない「きりさく」（ストライクのワザの位置 1 の、2 段階の記録のないダメージ）は 30 から計算した
        plain = []
        attack = None
        for e in state.log:
            if e["kind"] == "attack":
                attack = e
            elif e["kind"] == "damage" and attack["pokemon"] in scyther_cards(state) and attack["attack_index"] == 1 and not e.get("damage_set"):
                plain.append(e)
        self.assertTrue(plain)
        self.assertTrue(all(e["steps"][0] == ("1 基本となる計算", 30) and len(e["steps"]) == 1 + e["weakness"] + e["resistance"]
                            + len(e.get("modifiers", ())) for e in plain))

    def test_pluspower_after_step_2(self):
        """プラスパワーをつけた強化した「きりさく」: 2 段階の 60 のあとに 5 段階の +10（70）。"""
        r, _ = self.games["pluspower"]
        found = boosted_slashes(r["state"])
        self.assertTrue(any(d["amount"] == 70 and [m[0] for m in d.get("modifiers", ())] == [5] and
                            [s[0] for s in d["steps"]][:3] == ["1 基本となる計算", "2 つるぎのまい", "5 プラスパワー"] for _, _, _, d in found))

    def test_opponent_gust_removes_the_effect(self):
        """相手の突風でベンチのポケモンと入れ替えられて、効果が消える（理由 switch。p.57 のワザ解説の例）。"""
        r, _ = self.games["gust"]
        log = r["state"].log
        removed = []
        for i, e in enumerate(log):
            if e["kind"] == "persistent_effect_removed" and e["persistent_effect"] == KIND and e["reason"] == "switch":
                trainer = next(x for x in reversed(log[:i]) if x["kind"] == "play_trainer")
                if r["state"].cards[trainer["card"]].card_id == GUST and trainer["player"] != e["player"] and e["turn"] < e["active_turn"]:
                    removed.append(e)
        self.assertTrue(removed)
        self.assertGreaterEqual(scyther_uses(r["state"])[str(removed[0]["player"])]["gusted_from"], 1)

    def test_swords_dance_again_on_the_active_turn(self):
        """前の効果がはたらく番に、もう一度「つるぎのまい」: 新しい効果を与え、前の効果はその番の終わりに期限で消える（重ねて大きくならない）。"""
        r, _ = self.games["again"]
        log = r["state"].log
        added = [e for e in log if e["kind"] == "persistent_effect_added" and e["persistent_effect"] == KIND]
        again = [(old, new) for old in added for new in added if new["pokemon_id"] == old["pokemon_id"] and new["turn"] == old["active_turn"]]
        self.assertTrue(again)
        for old, new in again:
            expired = [e for e in log if e["kind"] == "persistent_effect_removed" and e["pokemon_id"] == old["pokemon_id"]
                       and e["created_turn"] == old["turn"]]
            self.assertEqual([(e["reason"], e["turn"]) for e in expired], [("expired", new["turn"])])
            self.assertLess(log.index(new), log.index(expired[0]))

    def test_counts_match_the_log(self):
        for name, (r, _) in self.games.items():
            with self.subTest(game=name):
                uses = scyther_uses(r["state"])
                self.assertEqual(sum(u.get("slash_boosted", 0) for u in uses.values()), len(boosted_slashes(r["state"])))
                self.assertEqual(sum(u.get("effect_added", 0) for u in uses.values()),
                                 sum(e["kind"] == "persistent_effect_added" and e["persistent_effect"] == KIND for e in r["state"].log))


class ConfigAGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {name: play(seat, seed, "scyther") for name, (seat, seed) in CONFIG_A.items()}

    def test_scyther_plays_slash_without_swords_dance(self):
        """A2S（闘・水のエネルギーだけ）: ストライクを場に出し、「きりさく」（30 から計算）を使う。「つるぎのまい」（草）は使えないので、効果はない。"""
        for name, (r, record) in self.games.items():
            with self.subTest(game=name):
                self.assertEqual((r["outcome"], record["audit"]), ("game_over", {}))
                self.assertIn("A2S", record["labels"])
                state = r["state"]
                uses = scyther_uses(state)
                self.assertEqual(len(uses), 1)
                (counts,) = uses.values()
                self.assertGreater(counts["in_play"], 0)
                self.assertNotIn("swords_dance", counts)
                self.assertFalse(any(e["kind"] == "persistent_effect_added" and e["persistent_effect"] == KIND for e in state.log))
                self.assertEqual(boosted_slashes(state), [])
        self.assertTrue(any(scyther_uses(r["state"]).get(str(r["decks"].index(A2)), {}).get("slash", 0) > 0 for r, _ in self.games.values()))


class ToolTest(unittest.TestCase):
    def test_temporary_decks(self):
        """一時的なデッキ: A2S は A2 のコラッタ 2 枚 → ストライク 2 枚、B2S は B2 のモンジャラ 2 枚 → ストライク 2 枚（ほかのカード・並びの位置は同じ。
        もう一方のデッキは変えない）。第1版・ほかの変種には使えない。公開の固定のデッキにストライクはない。"""
        for variant, deck, removed in (("scyther", A2, driver.RATTATA), ("scyther_grass", B2, driver.TANGELA)):
            with self.subTest(variant=variant):
                cards, original = driver.deck_cards(deck, variant), preset_deck(deck).cards()
                self.assertEqual(len(cards), 60)
                changed = [i for i, (a, b) in enumerate(zip(cards, original)) if a != b]
                self.assertEqual(len(changed), 2)
                self.assertTrue(all(original[i] == removed and cards[i] == SCYTHER for i in changed))
                other = B2 if deck == A2 else A2
                self.assertEqual(driver.deck_cards(other, variant), preset_deck(other).cards())
                self.assertEqual(comparison.label_of(deck, variant), comparison.LABELS[deck] + "S")
                self.assertEqual(comparison.label_of(other, variant), comparison.LABELS[other])
                for v1 in (driver.DECK_A, driver.DECK_B):
                    with self.assertRaises(ValueError):
                        driver.deck_cards(v1, variant)
        for old in ("gust", "breeder"):
            with self.assertRaises(ValueError):
                driver.deck_cards(A2, old)
        self.assertFalse(any(SCYTHER in Counter(deck.cards()) for deck in PRESET_DECKS.values()))


if __name__ == "__main__":
    unittest.main()

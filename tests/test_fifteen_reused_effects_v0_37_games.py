"""v0.37: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、15 枚の対戦（docs/fifteen-reused-effects-v0.37.md 6 章）。

検証用デッキ ``F37``（闘）・``W37``（水）・``L37``（雷・無色）・``G37``（草・超）（tools/existing_effect_games.py）を、4 組（``PAIRINGS_V0_37``: ``F37`` 対
``L37``・``W37`` 対 ``G37``・``L37`` 対 ``W37``・``G37`` 対 ``F37``）に分け、席を入れかえて seed 0〜5（48 局。最初の 6 つの seed。seed を探し回っていない）で
進める。手順は v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順と、v0.36 の「にげる」の 1 度だけの宣言を重ねたもの（対戦相手の
AI ではない）。

48 局で、15 枚がどれも場に出て（進化先 5 枚は通常の進化の操作で）、28 のワザがどれも使われ、ワザを使えない効果・使えないワザ・「にげる」の拒否・手順 4 の
コイン・8 段階と 2 段階でへったダメージ・自分の控えへのダメージ・コインで引いたカード・相手のエネルギーのトラッシュ・自分の「ワザをうけない」状態が起こる
（めずらしい場面の境界は単体テスト。seed を探し回らない）。終わり方は次の分類で数える（勝敗・カードの強さ・デッキの釣り合いは評価しない）:

- 通常の勝敗（``game_over``）
- 既知の裁定による停止（``halted``）
- ``UNRESOLVED_…``・``UNSUPPORTED_…`` でワザの宣言を拒否されたあと、別の操作で続けた回数（終わり方とは別に数える。HC4・HC3 はここに入る。F37 は
  闘に弱点・抵抗力を持つポケモンがいないので JS1 は起こらない。JS1 の境界は単体テスト）
- 手数の上限・想定外の拒否・内部エラー・監査の失敗（どれも 0）
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS
from kyuura_engine.cards import load_card_pool
from tests.helpers import (
    BROCKS_ONIX,
    BROCKS_SANDSHREW,
    DUGTRIO,
    FOSSIL_EKANS,
    FOSSIL_GRIMER,
    KOGAS_TANGELA,
    MEOWTH,
    MISTYS_MAGIKARP,
    PERSIAN,
    POLIWHIRL,
    POLIWRATH,
    RAICHU,
    RHYHORN,
    ROCKET_EEVEE,
    SABRINAS_DROWZEE,
    V0_37_POKEMON,
)
from tools import existing_effect_games as games

SEEDS = range(6)
LABELS = ("F37", "W37", "L37", "G37")
KNOWN_REJECTIONS = {f"stopped_attack_{code}" for code in games.V031_STOPS} | {
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE"}
KNOWN_HALTS = {"UNRESOLVED_MULLIGAN_COMPENSATION", "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"}


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class FifteenReusedEffectsGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed, keep_state=True) for a, b in games.PAIRINGS_V0_37 for seat in ((a, b), (b, a)) for seed in SEEDS]

    def test_endings_are_classified_and_pass_the_audits(self):
        """終わり方は通常の勝敗か、既知の未解決による停止だけ（手数の上限・想定外の拒否・内部エラーはない）。どの局も、受け付けた操作の列を ``new_game`` から
        やり直したログが同じで、不変条件・ログの監査・書き出しの監査が通る。"""
        self.assertEqual(len(self.results), 48)
        outcomes = Counter(r["outcome"] for r in self.results)
        self.assertEqual(set(outcomes) - {"game_over", "halted"}, set())
        for r in self.results:
            with self.subTest(decks=r["decks"], seed=r["seed"]):
                if r["outcome"] == "halted":
                    self.assertIn(r["halt_code"], KNOWN_HALTS)
                self.assertEqual(r["audit"], {})
                self.assertEqual(r["trainer_sequence_problems"], [])
                self.assertEqual({k for k in r["observed"] if "unexpected" in k}, set())
        self.assertGreater(outcomes["game_over"], 40)

    def test_rejections_are_counted_apart_from_halts(self):
        """ワザの宣言を拒否されたあと続けた回数は、停止と分けて数える。拒否のコードは既知のものだけで、場から確かめる（``V031_STOPS``）。ワザを使えない
        効果（``ATTACK_PREVENTED``）・使えないワザ（``ATTACK_LOCKED``）・ニョロボンのみずでっぽうの HC4・「ワザをうけない」相手へのコインの HC3・「にげる」
        ことができない効果の「にげる」（``RETREAT_PREVENTED``）が起こる。JS1 は起こらない（F37 の控えは闘に弱点・抵抗力を持たない）。"""
        found = Counter()
        observed = Counter()
        for r in self.results:
            found.update(r["unresolved_rejections"])
            observed.update(r["observed"])
            self.assertEqual(r["observed"].get("stopped_retreat_RETREAT_PREVENTED", 0), r["policy"].get("v036_retreat_probe", 0))
        self.assertTrue(set(found) <= KNOWN_REJECTIONS, set(found) - KNOWN_REJECTIONS)
        for key in ("stopped_attack_ATTACK_PREVENTED", "stopped_attack_ATTACK_LOCKED", "stopped_attack_UNRESOLVED_EXTRA_ENERGY_COLORLESS",
                    "stopped_attack_UNRESOLVED_PREVENTED_EFFECT_COIN", "stopped_retreat_RETREAT_PREVENTED"):
            with self.subTest(key=key):
                self.assertGreater(observed[key], 0)
        self.assertEqual(observed["stopped_attack_UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE"], 0)

    def test_every_card_and_attack_is_used(self):
        """48 局で、15 枚がどれも場に出て（進化先は進化の操作で）、28 のワザがどれも使われ、それぞれの効果が起こる。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for card_id in V0_37_POKEMON:
            uses = counted.get(card_id, Counter())
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertGreater(uses["in_play" if definition.stage == "basic" else "evolved_to"], 0)
                for attack in definition.attacks:
                    self.assertGreater(uses[f"attack#{attack.index}"], 0, attack.name_ja)
        expected = {
            RHYHORN: ("persistent_effect_added#0",),  # にらみつける（ワザを使えない）
            SABRINAS_DROWZEE: ("persistent_effect_added#0",),  # あんじをかける
            FOSSIL_GRIMER: ("special_condition_paralysis#0", "persistent_effect_added#1", "reduced_step8"),  # ベトベト・ちいさくなる
            ROCKET_EEVEE: ("gave_attack_coin_check", "attack_check_heads", "attack_check_tails"),  # すなかけ
            BROCKS_SANDSHREW: ("gave_cannot_retreat",),  # すなじごく
            RAICHU: ("persistent_effect_added#0", "self_damage#1"),  # こうそくいどう・かみなり
            DUGTRIO: ("self_bench_damage#1",),  # じしん
            POLIWHIRL: ("persistent_effect_added#0",),  # ドわすれ
            POLIWRATH: ("discard_attached_energy#1",),  # うずしお
            FOSSIL_EKANS: ("special_condition_poison#0", "special_condition_paralysis#1"),  # どくえき・まきつく
            BROCKS_ONIX: ("special_condition_paralysis#0",),  # うなりごえ
            MEOWTH: ("draw#0",),  # ねこにこばん
            KOGAS_TANGELA: ("special_condition_sleep#0", "draw#1"),  # ねむりごな・つるでさがす
            MISTYS_MAGIKARP: ("persistent_effect_added#0", "protected_by_own_effect"),  # しんだふり
            PERSIAN: ("persistent_effect_added#1", "reduced_step2"),  # かみつく
        }
        for card_id, keys in expected.items():
            for key in keys:
                with self.subTest(card=card_id, key=key):
                    self.assertGreater(counted[card_id][key], 0)

    def test_draw_and_damage_logs_are_in_order(self):
        """ねこにこばんのログは、どの局でも ``attack`` → ``damage``（または ``damage_prevented``）→ ``coin_flip`` →（「おもて」なら）``draw`` の順。
        どくえき・うなりごえ・つるでさがす・しんだふりのワザの中に、相手へのダメージのログはない。"""
        no_damage = {(FOSSIL_EKANS, 0), (BROCKS_ONIX, 0), (KOGAS_TANGELA, 1), (MISTYS_MAGIKARP, 0)}
        seen = Counter()
        for r in self.results:
            state = r["state"]
            log = state.log
            for i, e in enumerate(log):
                if e["kind"] != "attack":
                    continue
                key = (state.cards[e["pokemon"]].card_id, e["attack_index"])
                end = next((j for j in range(i + 1, len(log)) if log[j]["kind"] in ("attack", "turn_end", "knock_out", "take_prize")), len(log))
                kinds = [x["kind"] for x in log[i + 1:end]]
                if key == (MEOWTH, 0) and "confusion_check" not in kinds and "attack_check" not in kinds:
                    seen["meowth"] += 1
                    self.assertIn(kinds[:2], (["damage", "coin_flip"], ["damage_prevented", "coin_flip"]), kinds)
                    self.assertEqual(kinds[2:3] == ["draw"], log[i + 2]["result"] == "heads", kinds)  # 「おもて」のときだけ引く
                if key in no_damage:
                    seen["no_damage"] += 1
                    self.assertNotIn("damage", kinds, key)
        self.assertGreater(seen["meowth"], 0)
        self.assertGreater(seen["no_damage"], 0)


class ToolTest(unittest.TestCase):
    def test_verification_decks(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える。15 枚はどれも入る。公開の固定のデッキ・前の版の検証用デッキには入れていない。F37 の
        ポケモンは闘に弱点・抵抗力を持たない（じしんの JS1 が起こらない）。"""
        pool = load_card_pool()
        decks = {label: games.deck_cards(label) for label in LABELS}
        for label, deck in decks.items():
            with self.subTest(deck=label):
                self.assertEqual(len(deck), 60)
                self.assertTrue(all(pool.is_playable(c) for c in deck))
        self.assertTrue(set(V0_37_POKEMON) <= set().union(*decks.values()))
        self.assertFalse(any(set(V0_37_POKEMON) & set(d.cards()) for d in PRESET_DECKS.values()))
        for label in games.DECKS:
            if label not in LABELS:
                self.assertFalse(set(V0_37_POKEMON) & set(games.deck_cards(label)), label)
        from kyuura_engine.cards import EnergyType

        for card in set(decks["F37"]):
            definition = pool.get(card)
            if definition.category == "pokemon":
                self.assertNotIn(EnergyType.FIGHTING, (definition.weakness, definition.resistance), card)


if __name__ == "__main__":
    unittest.main()

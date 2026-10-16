"""v0.41: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、15 枚の対戦（docs/heal-counter-status-v0.41.md 7 章）。

検証用デッキ ``G41``（草）・``P41``（超・水）・``C41``（無色・水）・``R41``（炎・草・超）（tools/existing_effect_games.py）を、6 組（``PAIRINGS_V0_41``:
``G41`` 対 ``P41``・``P41`` 対 ``C41``・``C41`` 対 ``R41``・``R41`` 対 ``G41``・``G41`` 対 ``P31``（ピッピ・ピクシー・カスミのコダックが v0.41 のワザを自分の
ワザとして使う）・``R41`` 対 ``F37``（タケシのイワーク。カツラのファイヤーの 90 で HP 以上にならない相手））に分け、席を入れかえて seed 0〜5（72 局。最初の
6 つの seed。seed を探し回っていない）で進める。手順は v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順と、使っていないワザのために
エネルギーをためる手順（v0.38 と同じ）と、ミラクルかふんの選び方（ねむり・マヒ・こんらん・どく を順に）・ひなたぼっこの選び方（つける・つける・つけない を
順に）を重ねたもの（対戦相手の AI ではない）。

72 局で、15 枚がどれも場に出て（進化先は通常の進化の操作で）、29 のワザがどれも使われ、回復（自分・自分の場の全員・お互いの場の全員）・ダメージシフトでのせる・
チェンジダメージで取り替える・ミラクルかふんの 4 つの状態・くさいにおいとこまったねんりきの自分のこんらん・へんなこなのこんらんとねむり・ようかいえきの
「にげる」ことができない効果・さそうかおりとゆうわくの入れ替え・ひのとりで山札にもどす・ひなたぼっこで山札からつける（つけない・つけるものがないも）・
きあいずつきのワザの宣言の拒否（``ATTACK_LOCKED``）が起こる（めずらしい場面の境界は単体テスト）。終わり方は次の分類で数える（勝敗・カードの強さ・デッキの
釣り合いは評価しない）:

- 通常の勝敗（``game_over``）・サドンデス（``sudden_death``）
- 既知の裁定による停止（``halted``。対戦準備の ``UNRESOLVED_MULLIGAN_COMPENSATION``）
- ``UNRESOLVED_…``・``UNSUPPORTED_…``・使うための条件でワザの宣言を拒否されたあと、別の操作で続けた回数（終わり方とは別に数える。ひのとりの RD9・ナツメのヤドンの
  ぐうたらこうげきの Z23（抵抗力 超）・シードラのみずでっぽうの HC4・きあいずつきの ``ATTACK_LOCKED`` はここに入る）
- 手数の上限・想定外の拒否・内部エラー・監査の失敗（どれも 0）
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS
from kyuura_engine.cards import load_card_pool
from tests.helpers import (
    BLAINES_MOLTRES,
    DARK_PERSIAN,
    ERIKAS_GLOOM,
    ERIKAS_JIGGLYPUFF,
    ERIKAS_ODDISH,
    ERIKAS_ODDISH_40,
    GLOOM,
    ROCKET_SLOWPOKE,
    ROCKETS_MEWTWO,
    SABRINAS_GOLDUCK,
    SABRINAS_PSYDUCK,
    SABRINAS_SLOWBRO,
    SABRINAS_VENOMOTH,
    SEADRA,
    V0_41_POKEMON,
    VICTREEBEL,
)
from tests.test_bench_switch_combined_v0_38_games import earlier_batch_decks
from tools import existing_effect_games as games

SEEDS = range(6)
LABELS = ("G41", "P41", "C41", "R41")
KNOWN_REJECTIONS = {f"stopped_attack_{code}" for code in games.V031_STOPS} | {
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE"}
KNOWN_HALTS = {"UNRESOLVED_MULLIGAN_COMPENSATION", "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"}


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class HealCounterStatusGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed, keep_state=True) for a, b in games.PAIRINGS_V0_41 for seat in ((a, b), (b, a)) for seed in SEEDS]

    def test_endings_are_classified_and_pass_the_audits(self):
        """終わり方は通常の勝敗・サドンデスか、既知の未解決による停止だけ（手数の上限・想定外の拒否・内部エラーはない）。どの局も、受け付けた操作の列を
        ``new_game`` からやり直したログが同じで、不変条件・ログの監査（v0.41 の回復・ダメージカウンターをのせる／取り替える・山札からつけるログの組み立て直しを
        含む）・書き出しの監査が通る。"""
        self.assertEqual(len(self.results), 72)
        outcomes = Counter(r["outcome"] for r in self.results)
        self.assertEqual(set(outcomes) - {"game_over", "sudden_death", "halted"}, set())
        for r in self.results:
            with self.subTest(decks=r["decks"], seed=r["seed"]):
                if r["outcome"] == "halted":
                    self.assertIn(r["halt_code"], KNOWN_HALTS)
                self.assertEqual(r["audit"], {})
                self.assertEqual(r["trainer_sequence_problems"], [])
                self.assertEqual({k for k in r["observed"] if "unexpected" in k}, set())
        self.assertGreater(outcomes["game_over"], 60)

    def test_rejections_are_counted_apart_from_halts(self):
        """ワザの宣言を拒否されたあと続けた回数は、停止と分けて数える。拒否のコードは既知のものだけで、場から確かめる（``V031_STOPS``）。ひのとりの RD9（相手が
        90 で HP 以上になる）・きあいずつきの ``ATTACK_LOCKED`` が起こる。"""
        found = Counter()
        observed = Counter()
        for r in self.results:
            found.update(r["unresolved_rejections"])
            observed.update(r["observed"])
        self.assertTrue(set(found) <= KNOWN_REJECTIONS, set(found) - KNOWN_REJECTIONS)
        self.assertGreater(observed["stopped_attack_UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT"], 0)
        self.assertGreater(observed["stopped_attack_ATTACK_LOCKED"], 0)

    def test_every_card_and_attack_is_used(self):
        """72 局で、15 枚がどれも場に出て（進化先は進化の操作で）、29 のワザがどれも使われ、それぞれの効果が起こる。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for card_id in V0_41_POKEMON:
            uses = counted.get(card_id, Counter())
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertGreater(uses["in_play" if definition.stage == "basic" else "evolved_to"], 0)
                for attack in definition.attacks:
                    self.assertGreater(uses[f"attack#{attack.index}"], 0, attack.name_ja)
        expected = {
            GLOOM: ("special_condition_poison#0", "special_condition_confusion#1", "self_special_condition_confusion#1"),  # どくのこな・くさいにおい
            VICTREEBEL: ("forced_switch#0", "gave_cannot_retreat"),  # さそうかおり・ようかいえき
            SEADRA: ("base#0=40", "persistent_effect_added#1"),  # みずでっぽう（水 2 つぶん追加）・こうそくいどう
            DARK_PERSIAN: ("forced_switch#0", "special_condition_poison#1"),  # ゆうわく・どくのつめ
            BLAINES_MOLTRES: ("base#0=90", "return_in_play_to_deck#0"),  # ひのとり（「うら」で山札にもどす）
            ROCKET_SLOWPOKE: ("attach_energy_from_deck#0", "attach_energy_from_deck_none#0", "shuffle#0"),  # ひなたぼっこ
            ERIKAS_ODDISH: ("attack_heal_own#0", "attack_heal_own#1"),  # ちょっとすいとる・たまにすいとる
            ERIKAS_ODDISH_40: ("special_condition_confusion#0", "special_condition_sleep#0"),  # へんなこな
            ERIKAS_GLOOM: ("attack_heal_own#0", "special_condition_sleep#1", "special_condition_paralysis#1", "special_condition_confusion#1",
                           "special_condition_poison#1"),  # ヒーリングかふん・ミラクルかふん
            SABRINAS_PSYDUCK: ("special_condition_confusion#1", "self_special_condition_confusion#1"),  # こまったねんりき（「おもて」・「うら」）
            SABRINAS_GOLDUCK: ("attack_heal_own#0", "place_damage_counters#0", "base#1=40"),  # ダメージシフト・ウォーターシュート
            SABRINAS_VENOMOTH: ("attack_heal_own#0", "special_condition_confusion#1"),  # かいふくりんぷん・げんかくおんぱ
            SABRINAS_SLOWBRO: ("attack_heal_own#0", "self_special_condition_sleep#0", "persistent_effect_added#1"),  # いねむり・きあいずつき
            ERIKAS_JIGGLYPUFF: ("attack_heal_own#0", "attack_heal_opponent#0", "base#1=10", "base#1=40"),  # みんなでかいふく・やさしいパンチ
            ROCKETS_MEWTWO: ("swap_damage_counters#0", "special_condition_sleep#1", "base#2=60"),  # チェンジダメージ・さいみんはどう
        }
        for card_id, keys in expected.items():
            for key in keys:
                with self.subTest(card=card_id, key=key):
                    self.assertGreater(counted[card_id][key], 0)

    def test_counter_logs_match_the_board(self):
        """ダメージシフトでのせた数は、同じワザでとりのぞいた数と同じ（``attack_heal`` の数）。チェンジダメージの取り替えたあとの数は、取り替える前の相手と自分の
        数。どちらもダメージのログ（``damage``）を出さない（カウンターの移動はダメージではない）。"""
        checked = Counter()
        for r in self.results:
            log = r["state"].log
            cards = r["state"].cards
            for i, e in enumerate(log):
                if e["kind"] != "attack" or cards[e["pokemon"]].card_id not in (SABRINAS_GOLDUCK, ROCKETS_MEWTWO) or e["attack_index"] != 0:
                    continue
                end = next((j for j in range(i + 1, len(log)) if log[j]["kind"] in ("turn_end", "game_end")), len(log))
                window = log[i + 1:end]
                placed = [x for x in window if x["kind"] == "place_damage_counters"]
                swapped = [x for x in window if x["kind"] == "swap_damage_counters"]
                if placed:
                    removed = sum(x["counters"] for x in window if x["kind"] == "attack_heal")
                    self.assertEqual(placed[0]["counters"], removed)
                    checked["placed"] += 1
                if swapped:
                    x = swapped[0]
                    self.assertEqual((x["total_damage"], x["opponent_total_damage"]), (x["opponent_damage_before"], x["damage_before"]))
                    checked["swapped"] += 1
                if placed or swapped:
                    self.assertFalse([x for x in window if x["kind"] == "damage" and not x.get("retaliation")])
        self.assertTrue(checked["placed"] and checked["swapped"], checked)


class ToolTest(unittest.TestCase):
    def test_verification_decks(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える（同じ名前のエリカのナゾノクサは合わせて 4 枚まで）。15 枚はどれも入る。公開の固定のデッキ・前の版の
        検証用デッキには入れていない。"""
        pool = load_card_pool()
        decks = {label: games.deck_cards(label) for label in LABELS}
        for label, deck in decks.items():
            with self.subTest(deck=label):
                self.assertEqual(len(deck), 60)
                self.assertTrue(all(pool.is_playable(c) for c in deck))
                names = Counter(pool.get(c).name_ja for c in deck if not pool.get(c).is_basic_energy)
                self.assertLessEqual(max(names.values()), 4)
        self.assertEqual(Counter(decks["G41"])[ERIKAS_ODDISH] + Counter(decks["G41"])[ERIKAS_ODDISH_40], 4)
        self.assertTrue(set(V0_41_POKEMON) <= set().union(*decks.values()))
        self.assertFalse(any(set(V0_41_POKEMON) & set(d.cards()) for d in PRESET_DECKS.values()))
        for label in sorted(earlier_batch_decks("v0.41")):
            self.assertFalse(set(V0_41_POKEMON) & set(games.deck_cards(label)), label)


if __name__ == "__main__":
    unittest.main()

"""v0.39: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、15 枚の対戦（docs/selfdestruct-spread-count-v0.39.md 7 章）。

検証用デッキ ``L39``（雷）・``G39``（草）・``C39``（無色・水）・``N39``（草）（tools/existing_effect_games.py）を、4 組（``PAIRINGS_V0_39``: ``L39`` 対 ``C39``・
``C39`` 対 ``G39``・``G39`` 対 ``N39``・``N39`` 対 ``L39``）に分け、席を入れかえて seed 0〜5（48 局。最初の 6 つの seed。seed を探し回っていない）で進める。
手順は v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順と、使っていないワザのためにエネルギーをためる手順（v0.38 と同じ）と、
スパーク・ギガスパークの控えの選び方（JS1 の選択を避け、ギガスパークは 1〜3 匹を順に選ぶ）を重ねたもの（対戦相手の AI ではない）。

48 局で、15 枚がどれも場に出て（進化先 9 枚は通常の進化の操作で）、25 のワザがどれも使われ、じばくの自分へのダメージとお互いの控えへのダメージ・スパークと
ギガスパーク（1・2・3 匹）の控えへのダメージ・ビリビリ・おならガス・ウォーターリングの控えへのダメージ・場のポケモンの数で変わる基本となるダメージ・
とつぜんばくはつの両面・特殊などく・きけんなほうしの控えへのダメージとどく・かぜおこしの入れ替えが起こる（めずらしい場面の境界は単体テスト。seed を探し
回らない）。終わり方は次の分類で数える（勝敗・カードの強さ・デッキの釣り合いは評価しない）:

- 通常の勝敗（``game_over``）・サドンデス（``sudden_death``）
- 既知の裁定による停止（``halted``）
- ``UNRESOLVED_…``・``UNSUPPORTED_…``・使うための条件でワザの宣言を拒否されたあと、別の操作で続けた回数（終わり方とは別に数える。``L39`` 対 ``C39`` の
  ポッポ（雷に弱点）が控えにいるときの第1弾のじばくの JS1 はここに入る）
- 手数の上限・想定外の拒否・内部エラー・監査の失敗（どれも 0）
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS
from kyuura_engine.cards import load_card_pool
from tests.helpers import (
    ELECTRODE,
    ERIKAS_PARAS,
    FOSSIL_MAGNETON,
    FOSSIL_RAICHU,
    FOSSIL_WEEZING,
    JUNGLE_PIKACHU,
    KOGAS_KOFFING_40,
    KOGAS_WEEZING,
    MAGNEMITE,
    MAGNETON,
    MISTYS_POLIWRATH,
    NIDOQUEEN,
    PIDGEY,
    V0_39_POKEMON,
    WIGGLYTUFF,
)
from tests.test_bench_switch_combined_v0_38_games import earlier_batch_decks
from tools import existing_effect_games as games

SEEDS = range(6)
LABELS = ("L39", "G39", "C39", "N39")
KNOWN_REJECTIONS = {f"stopped_attack_{code}" for code in games.V031_STOPS} | {
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE"}
KNOWN_HALTS = {"UNRESOLVED_MULLIGAN_COMPENSATION", "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"}


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class SelfDestructSpreadCountGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed, keep_state=True) for a, b in games.PAIRINGS_V0_39 for seat in ((a, b), (b, a)) for seed in SEEDS]

    def test_endings_are_classified_and_pass_the_audits(self):
        """終わり方は通常の勝敗・サドンデスか、既知の未解決による停止だけ（手数の上限・想定外の拒否・内部エラーはない）。どの局も、受け付けた操作の列を
        ``new_game`` からやり直したログが同じで、不変条件・ログの監査（v0.39 の特殊などくの量を含む）・書き出しの監査が通る。"""
        self.assertEqual(len(self.results), 48)
        outcomes = Counter(r["outcome"] for r in self.results)
        self.assertEqual(set(outcomes) - {"game_over", "sudden_death", "halted"}, set())
        for r in self.results:
            with self.subTest(decks=r["decks"], seed=r["seed"]):
                if r["outcome"] == "halted":
                    self.assertIn(r["halt_code"], KNOWN_HALTS)
                self.assertEqual(r["audit"], {})
                self.assertEqual(r["trainer_sequence_problems"], [])
                self.assertEqual({k for k in r["observed"] if "unexpected" in k}, set())
        self.assertGreater(outcomes["game_over"], 40)

    def test_rejections_are_counted_apart_from_halts(self):
        """ワザの宣言を拒否されたあと続けた回数は、停止と分けて数える。拒否のコードは既知のものだけで、場から確かめる（``V031_STOPS``）。``L39`` 対 ``C39`` で、
        控えのポッポ（雷に弱点）があるときの第1弾のじばく・ビリビリの JS1 が起こる。GS1 は起こらない（手順が 0 匹を選ばない。GS1 の境界は単体テスト）。"""
        found = Counter()
        observed = Counter()
        for r in self.results:
            found.update(r["unresolved_rejections"])
            observed.update(r["observed"])
        self.assertTrue(set(found) <= KNOWN_REJECTIONS, set(found) - KNOWN_REJECTIONS)
        self.assertGreater(observed["stopped_attack_UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE"], 0)
        self.assertEqual(observed["stopped_attack_UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE"], 0)

    def test_every_card_and_attack_is_used(self):
        """48 局で、15 枚がどれも場に出て（進化先は進化の操作で）、25 のワザがどれも使われ、それぞれの効果が起こる。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for card_id in V0_39_POKEMON:
            uses = counted.get(card_id, Counter())
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertGreater(uses["in_play" if definition.stage == "basic" else "evolved_to"], 0)
                for attack in definition.attacks:
                    self.assertGreater(uses[f"attack#{attack.index}"], 0, attack.name_ja)
        expected = {
            MAGNEMITE: ("self_damage#1", "self_bench_damage#1"),  # じばく
            MAGNETON: ("special_condition_paralysis#0", "self_damage#1", "opponent_bench_damage#1", "self_bench_damage#1"),  # でんじは・じばく
            FOSSIL_WEEZING: ("special_condition_poison#0", "self_damage#1", "opponent_bench_damage#1", "self_bench_damage#1"),  # スモッグ・じばく
            FOSSIL_MAGNETON: ("damage#0", "self_damage#1", "opponent_bench_damage#1", "self_bench_damage#1"),  # ソニックブーム・じばく
            JUNGLE_PIKACHU: ("opponent_bench_damage#0",),  # スパーク
            FOSSIL_RAICHU: ("opponent_bench_damage#0",),  # ギガスパーク
            ELECTRODE: ("opponent_bench_damage#1",),  # ビリビリ
            KOGAS_KOFFING_40: ("opponent_bench_damage#0", "self_bench_damage#0"),  # おならガス
            MISTYS_POLIWRATH: ("opponent_bench_damage#0", "self_bench_damage#0"),  # ウォーターリング
            WIGGLYTUFF: ("special_condition_sleep#0", "base#1=20", "base#1=60"),  # こもりうた・ともだちのわ（控えの数で変わる）
            NIDOQUEEN: ("base#0=20", "base#0=40"),  # ラブラブアタック（ニドキングの数で変わる）
            KOGAS_WEEZING: ("base#0=10", "base#0=40", "self_damage#0", "special_condition_poison#1"),  # とつぜんばくはつの両面・どくどくガス
            PIDGEY: ("forced_switch#0",),  # かぜおこし
            ERIKAS_PARAS: ("opponent_bench_damage#1", "special_condition_poison#1"),  # きけんなほうし
        }
        for card_id, keys in expected.items():
            for key in keys:
                with self.subTest(card=card_id, key=key):
                    self.assertGreater(counted[card_id][key], 0)

    def test_giga_spark_chooses_one_two_and_three_targets(self):
        """ギガスパークの決定で、1・2・3 匹を選んだ回がどれもある（手順が順に選ぶ）。選んだ数だけ、相手の控えにダメージのログがある。"""
        sizes = Counter()
        for r in self.results:
            state = r["state"]
            log = state.log
            for i, e in enumerate(log):
                if e["kind"] != "attack" or state.cards[e["pokemon"]].card_id != FOSSIL_RAICHU:
                    continue
                end = next((j for j in range(i + 1, len(log)) if log[j]["kind"] in ("turn_end", "game_end")), len(log))
                if any(x["kind"] == "confusion_damage" for x in log[i + 1:end]):
                    continue
                bench = [x for x in log[i + 1:end] if x["kind"] == "damage" and x.get("target") == "opponent_bench"]
                sizes[len(bench)] += 1
        self.assertTrue({1, 2, 3} <= set(sizes), sizes)

    def test_special_poison_takes_twenty_in_the_pokemon_check(self):
        """どくどくガスでどく状態になったポケモンは、ポケモンチェックで 20 を受ける（ログ ``poison_damage`` の量）。どのどくのダメージも、そのポケモンを最後に
        どく状態にしたログの量と同じ（特殊などくのあとに通常のどくを受けたら 10 にもどる。v0.3a の 14）。"""
        amounts = Counter()
        for r in self.results:
            state = r["state"]
            latest = {}
            for e in state.log:
                if e["kind"] == "special_condition" and e.get("condition") == "poison":
                    latest[e["pokemon_id"]] = (e["damage"], e.get("effect"))
                elif e["kind"] == "poison_damage":
                    damage, effect = latest[e["pokemon_id"]]
                    self.assertEqual(e["amount"], damage)
                    if effect == f"{KOGAS_WEEZING}#1":
                        amounts[e["amount"]] += 1
        self.assertGreater(amounts[20], 0)
        self.assertEqual(set(amounts), {20})


class ToolTest(unittest.TestCase):
    def test_verification_decks(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える（同じ名前のコイル・レアコイルは合わせて 4 枚まで）。15 枚はどれも入る。公開の固定のデッキ・前の版の
        検証用デッキには入れていない。"""
        pool = load_card_pool()
        decks = {label: games.deck_cards(label) for label in LABELS}
        for label, deck in decks.items():
            with self.subTest(deck=label):
                self.assertEqual(len(deck), 60)
                self.assertTrue(all(pool.is_playable(c) for c in deck))
                names = Counter(pool.get(c).name_ja for c in deck if not pool.get(c).is_basic_energy)
                self.assertLessEqual(max(names.values()), 4)
        self.assertTrue(set(V0_39_POKEMON) <= set().union(*decks.values()))
        self.assertFalse(any(set(V0_39_POKEMON) & set(d.cards()) for d in PRESET_DECKS.values()))
        for label in sorted(earlier_batch_decks("v0.39")):
            self.assertFalse(set(V0_39_POKEMON) & set(games.deck_cards(label)), label)


if __name__ == "__main__":
    unittest.main()

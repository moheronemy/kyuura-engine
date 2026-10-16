"""v0.38: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、15 枚の対戦（docs/bench-switch-combined-v0.38.md 7 章）。

検証用デッキ ``F38``（闘・炎・無色）・``G38``（草）・``C38``（無色・水・超）（tools/existing_effect_games.py）を、4 組（``PAIRINGS_V0_38``: ``F38`` 対 ``G38``・
``G38`` 対 ``C38``・``C38`` 対 ``F38``・``C38`` 対 ``P31``）に分け、席を入れかえて seed 0〜5（48 局。最初の 6 つの seed。seed を探し回っていない）で進める。
手順は v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順と、使っていないワザのためにエネルギーをためる手順（v0.38 のカードだけ）を
重ねたもの（対戦相手の AI ではない）。``C38`` 対 ``P31`` では、ピッピ・ピクシー・カスミのコダックが v0.38 のワザを自分のワザとして使う。

48 局で、15 枚がどれも場に出て（進化先 6 枚は通常の進化の操作で）、29 のワザがどれも使われ、控えへのダメージ（相手の控えを選ぶ・控え全員・自分の控え全員）・
相手が選ぶ入れ替え・自分の控えとの入れ替え・同じコインの効果（どく／マヒ・バリアー）・8 段階でへったダメージ・いなくなるのトラッシュと山札・でんれいの山札を
さがす処理が起こる（めずらしい場面の境界は単体テスト。seed を探し回らない）。終わり方は次の分類で数える（勝敗・カードの強さ・デッキの釣り合いは評価しない）:

- 通常の勝敗（``game_over``）・サドンデス（``sudden_death``）
- 既知の裁定による停止（``halted``）
- ``UNRESOLVED_…``・``UNSUPPORTED_…``・使うための条件でワザの宣言を拒否されたあと、別の操作で続けた回数（終わり方とは別に数える。のびるキックの
  ``NO_OPPONENT_BENCH`` はここに入る。どのデッキにも「ダメージを受けたとき」の効果を持つポケモンはいないので GK1 は起こらない。GK1 の境界は単体テスト）
- 手数の上限・想定外の拒否・内部エラー・監査の失敗（どれも 0）
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS
from kyuura_engine.cards import load_card_pool
from tests.helpers import (
    ARBOK,
    ARTICUNO,
    BLAINES_PONYTA,
    BLAINES_RAPIDASH,
    BROCKS_GOLBAT,
    BROCKS_VULPIX_50,
    ERIKAS_TANGELA,
    GIOVANNIS_NIDORINA,
    HITMONLEE,
    KOGAS_PIDGEOTTO,
    KOGAS_PIDGEY_40,
    KOGAS_WEEDLE,
    RHYDON,
    ROCKET_ABRA,
    SABRINAS_PORYGON,
    V0_38_POKEMON,
)
from tools import existing_effect_games as games

SEEDS = range(6)
LABELS = ("F38", "G38", "C38")
KNOWN_REJECTIONS = {f"stopped_attack_{code}" for code in games.V031_STOPS} | {
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE"}
KNOWN_HALTS = {"UNRESOLVED_MULLIGAN_COMPENSATION", "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"}


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class BenchSwitchCombinedGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed, keep_state=True) for a, b in games.PAIRINGS_V0_38 for seat in ((a, b), (b, a)) for seed in SEEDS]

    def test_endings_are_classified_and_pass_the_audits(self):
        """終わり方は通常の勝敗・サドンデスか、既知の未解決による停止だけ（手数の上限・想定外の拒否・内部エラーはない）。どの局も、受け付けた操作の列を
        ``new_game`` からやり直したログが同じで、不変条件・ログの監査（v0.38 の discard_attached_cards・でんれいの山札をさがしてから 1 回だけ切る並びを含む）・
        書き出しの監査が通る。"""
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
        """ワザの宣言を拒否されたあと続けた回数は、停止と分けて数える。拒否のコードは既知のものだけで、場から確かめる（``V031_STOPS``）。のびるキックの使うための
        条件（``NO_OPPONENT_BENCH``）が起こる。GK1 は起こらない（「ダメージを受けたとき」の効果を持つポケモンがいない）。"""
        found = Counter()
        observed = Counter()
        for r in self.results:
            found.update(r["unresolved_rejections"])
            observed.update(r["observed"])
        self.assertTrue(set(found) <= KNOWN_REJECTIONS, set(found) - KNOWN_REJECTIONS)
        self.assertGreater(observed["stopped_attack_NO_OPPONENT_BENCH"], 0)
        self.assertEqual(observed["stopped_attack_UNRESOLVED_DAMAGE_TRIGGER_TIMING"], 0)

    def test_every_card_and_attack_is_used(self):
        """48 局で、15 枚がどれも場に出て（進化先は進化の操作で）、29 のワザがどれも使われ、それぞれの効果が起こる。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for card_id in V0_38_POKEMON:
            uses = counted.get(card_id, Counter())
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertGreater(uses["in_play" if definition.stage == "basic" else "evolved_to"], 0)
                for attack in definition.attacks:
                    self.assertGreater(uses[f"attack#{attack.index}"], 0, attack.name_ja)
        expected = {
            ARTICUNO: ("special_condition_paralysis#0", "opponent_bench_damage#1", "self_bench_damage#1"),  # フリーズドライ・ふぶきの両面
            HITMONLEE: ("opponent_bench_damage#0",),  # のびるキック
            ERIKAS_TANGELA: ("opponent_bench_damage#1",),  # のびるつる
            BROCKS_VULPIX_50: ("special_condition_sleep#0", "opponent_bench_damage#1"),  # みつめる・ほのおのわ
            BROCKS_GOLBAT: ("opponent_bench_damage#1",),  # かいてんひこう
            ARBOK: ("forced_switch#0", "forced_switch_skipped#0", "special_condition_poison#1"),  # いかくこうげき・どくのきば
            RHYDON: ("forced_switch#1", "self_damage#1"),  # げきとつ
            BLAINES_PONYTA: ("switch#0",),  # けりにげ
            BLAINES_RAPIDASH: ("opponent_bench_damage#1",),  # ふみあらす
            KOGAS_PIDGEOTTO: ("persistent_effect_added#1",),  # こうそくひこう（バリアー）
            KOGAS_WEEDLE: ("special_condition_poison#1", "special_condition_paralysis#1"),  # きけんなはりの両面
            GIOVANNIS_NIDORINA: ("self_damage#0", "special_condition_poison#0", "special_condition_paralysis#1"),  # どくばりタックル・のしかかり
            SABRINAS_PORYGON: ("persistent_effect_added#1", "reduced_step8"),  # バリアアタック
            ROCKET_ABRA: ("remove_all_damage_counters#0", "discard_attached_cards#0", "return_in_play_to_deck#0"),  # いなくなる
            KOGAS_PIDGEY_40: ("return_in_play_to_deck#0", "reveal_from_deck#0"),  # でんれい
        }
        for card_id, keys in expected.items():
            for key in keys:
                with self.subTest(card=card_id, key=key):
                    self.assertGreater(counted[card_id][key], 0)

    def test_messenger_and_vanish_logs_are_in_order(self):
        """でんれいのログは、どの局でも ``attack`` → ``return_in_play_to_deck`` →（控えがいれば）``promote_active`` → ``reveal_from_deck``（または
        ``reveal_from_deck_none``）→ ``shuffle`` の順で、山札を切るのは 1 回。いなくなるは ``remove_all_damage_counters`` → ``discard_attached_cards`` →
        ``return_in_play_to_deck`` → ``shuffle``（1 回）。どちらもきぜつ（``knock_out``）はない。"""
        seen = Counter()
        for r in self.results:
            state = r["state"]
            log = state.log
            for i, e in enumerate(log):
                if e["kind"] != "attack" or state.cards[e["pokemon"]].card_id not in (KOGAS_PIDGEY_40, ROCKET_ABRA) or e["attack_index"] != 0:
                    continue
                end = next((j for j in range(i + 1, len(log)) if log[j]["kind"] in ("turn_end", "game_end")), len(log))
                kinds = [x["kind"] for x in log[i + 1:end] if x["kind"] not in ("persistent_effect_removed", "confusion_check", "coin_flip")]
                if "confusion_damage" in kinds:
                    continue
                if state.cards[e["pokemon"]].card_id == KOGAS_PIDGEY_40:
                    seen["messenger"] += 1
                    search = "reveal_from_deck" if "reveal_from_deck" in kinds else "reveal_from_deck_none"
                    self.assertIn(kinds[:4], (["return_in_play_to_deck", "promote_active", search, "shuffle"], ["return_in_play_to_deck", search, "shuffle"]),
                                  kinds)
                else:
                    seen["vanish"] += 1
                    self.assertEqual(kinds[:4], ["remove_all_damage_counters", "discard_attached_cards", "return_in_play_to_deck", "shuffle"], kinds)
                self.assertEqual(kinds.count("shuffle"), 1, kinds)
                self.assertNotIn("knock_out", kinds[:kinds.index("shuffle")])
        self.assertGreater(seen["messenger"], 0)
        self.assertGreater(seen["vanish"], 0)

    def test_copied_attacks_occur(self):
        """``C38`` 対 ``P31`` で、ピッピ・ピクシー・カスミのコダックが v0.38 のワザを自分のワザとして使う（まねたワザのログ copy_attack の copied が v0.38 の
        ワザ）。"""
        copied = Counter()
        for r in self.results:
            state = r["state"]
            for e in state.log:
                if e["kind"] == "copy_attack" and e["copied"].split("#")[0] in V0_38_POKEMON:
                    copied[e["copied"]] += 1
        self.assertGreater(sum(copied.values()), 0)


def earlier_batch_decks(version: str) -> set[str]:
    """``version`` より前の版の組（``games.BATCHES``）で使う検証用デッキ（v0.38: 後の版の検証用デッキは、前の版のカードを進化元などに使ってよい）。"""
    def key(batch: str) -> tuple[int, ...]:
        return tuple(int(part) for part in batch[1:].split("."))
    return {label for batch, pairings in games.BATCHES.items() if key(batch) < key(version) for pair in pairings for label in pair}


class ToolTest(unittest.TestCase):
    def test_verification_decks(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える（同じ名前のキョウのポッポは合わせて 4 枚まで）。15 枚はどれも入る。公開の固定のデッキ・前の版の
        検証用デッキには入れていない。"""
        pool = load_card_pool()
        decks = {label: games.deck_cards(label) for label in LABELS}
        for label, deck in decks.items():
            with self.subTest(deck=label):
                self.assertEqual(len(deck), 60)
                self.assertTrue(all(pool.is_playable(c) for c in deck))
                names = Counter(pool.get(c).name_ja for c in deck if not pool.get(c).is_basic_energy)
                self.assertLessEqual(max(names.values()), 4)
        self.assertTrue(set(V0_38_POKEMON) <= set().union(*decks.values()))
        self.assertFalse(any(set(V0_38_POKEMON) & set(d.cards()) for d in PRESET_DECKS.values()))
        for label in sorted(earlier_batch_decks("v0.38")):  # 前の版の検証用デッキ（後の版のデッキは進化元などに使ってよい。v0.38）
            self.assertFalse(set(V0_38_POKEMON) & set(games.deck_cards(label)), label)


if __name__ == "__main__":
    unittest.main()

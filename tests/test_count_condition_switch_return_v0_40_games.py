"""v0.40: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、15 枚の対戦（docs/count-condition-switch-return-v0.40.md 7 章）。

検証用デッキ ``G40``（草）・``N40``（草。わるいマタドガスとドガースの系統）・``F40``（闘）・``P40``（超・水）（tools/existing_effect_games.py）を、4 組
（``PAIRINGS_V0_40``: ``G40`` 対 ``N40``・``N40`` 対 ``F40``・``F40`` 対 ``P40``・``P40`` 対 ``G40``）に分け、席を入れかえて seed 0〜5（48 局。最初の 6 つの
seed。seed を探し回っていない）で進める。手順は v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順と、使っていないワザのために
エネルギーをためる手順（v0.38 と同じ）と、むれでおそうの出す数（番の番号で 選べるだけ・0 枚・1 枚）・ひきずりだすとさそってとかすの控えの選び方を重ねた
もの（対戦相手の AI ではない）。

48 局で、15 枚がどれも場に出て（進化先 11 枚は通常の進化の操作で）、28 のワザがどれも使われ、むれでおそうで山札からベンチに出す（出さない選択も）・
みんなでばくはつの数と名前の合うポケモンへのダメージ・ベンチをあやつるの相手のコイン・いかりのいちげきの使うための条件・つのでえぐるの追加・すごむの効果と
それによるワザの宣言の拒否・ラブラリアットの失敗・ひきずりだすとさそってとかすの入れ替え・つまみだす・きぜつばりの追加・ひまつぶしといたずらの山札を切る・
あばれまわるのこんらんが起こる（めずらしい場面の境界は単体テスト。seed を探し回らない）。終わり方は次の分類で数える（勝敗・カードの強さ・デッキの釣り合いは
評価しない）:

- 通常の勝敗（``game_over``）・サドンデス（``sudden_death``）
- 既知の裁定による停止（``halted``。対戦準備の ``UNRESOLVED_MULLIGAN_COMPENSATION``）
- ``UNRESOLVED_…``・``UNSUPPORTED_…``・使うための条件でワザの宣言を拒否されたあと、別の操作で続けた回数（終わり方とは別に数える。いかりのいちげきの
  ``NOT_ENOUGH_DAMAGE_COUNTERS``・すごむの効果を受けたポケモンの ``ATTACK_PREVENTED`` はここに入る）
- 手数の上限・想定外の拒否・内部エラー・監査の失敗（どれも 0）
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS
from kyuura_engine.cards import load_card_pool
from tests.helpers import (
    BROCKS_MANKEY,
    DARK_HYPNO,
    DARK_MACHAMP,
    DARK_MACHOKE,
    DARK_WEEZING,
    ERIKAS_WEEPINBELL,
    GIOVANNIS_NIDOKING,
    GIOVANNIS_NIDOQUEEN,
    GIOVANNIS_NIDORAN_M,
    GIOVANNIS_NIDORINO,
    KOGAS_GOLBAT,
    KOGAS_ZUBAT,
    MANKEY,
    MISTYS_SEADRA,
    PRIMEAPE,
    V0_40_POKEMON,
)
from tests.test_bench_switch_combined_v0_38_games import earlier_batch_decks
from tools import existing_effect_games as games

SEEDS = range(6)
LABELS = ("G40", "N40", "F40", "P40")
KNOWN_REJECTIONS = {f"stopped_attack_{code}" for code in games.V031_STOPS} | {
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE"}
KNOWN_HALTS = {"UNRESOLVED_MULLIGAN_COMPENSATION", "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"}


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class CountConditionSwitchReturnGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed, keep_state=True) for a, b in games.PAIRINGS_V0_40 for seat in ((a, b), (b, a)) for seed in SEEDS]

    def test_endings_are_classified_and_pass_the_audits(self):
        """終わり方は通常の勝敗・サドンデスか、既知の未解決による停止だけ（手数の上限・想定外の拒否・内部エラーはない）。どの局も、受け付けた操作の列を
        ``new_game`` からやり直したログが同じで、不変条件・ログの監査（v0.40 のむれでおそうの出す数と切る回数・つまみだすの相手のポケモンを山札にもどす処理を
        含む）・書き出しの監査が通る。"""
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
        """ワザの宣言を拒否されたあと続けた回数は、停止と分けて数える。拒否のコードは既知のものだけで、場から確かめる（``V031_STOPS``）。いかりのいちげきの
        ``NOT_ENOUGH_DAMAGE_COUNTERS``（自分のカウンターが 2 つ未満）と、すごむの効果を受けたポケモンの ``ATTACK_PREVENTED`` が起こる。SG1 は起こらない
        （すごむの効果を受けた番に、2 枚目の突風で効果を与えたポケモンをバトル場にもどす場面がない。SG1 の境界は単体テスト）。"""
        found = Counter()
        observed = Counter()
        for r in self.results:
            found.update(r["unresolved_rejections"])
            observed.update(r["observed"])
        self.assertTrue(set(found) <= KNOWN_REJECTIONS, set(found) - KNOWN_REJECTIONS)
        self.assertGreater(observed["stopped_attack_NOT_ENOUGH_DAMAGE_COUNTERS"], 0)
        self.assertGreater(observed["stopped_attack_ATTACK_PREVENTED"], 0)
        self.assertNotIn("UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED", " ".join(found))

    def test_every_card_and_attack_is_used(self):
        """48 局で、15 枚がどれも場に出て（進化先は進化の操作で）、28 のワザがどれも使われ、それぞれの効果が起こる。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for card_id in V0_40_POKEMON:
            uses = counted.get(card_id, Counter())
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertGreater(uses["in_play" if definition.stage == "basic" else "evolved_to"], 0)
                for attack in definition.attacks:
                    self.assertGreater(uses[f"attack#{attack.index}"], 0, attack.name_ja)
        expected = {
            KOGAS_ZUBAT: ("bench_from_deck#0", "bench_from_deck_declined#0", "shuffle#0"),  # むれでおそう（出す・出さない）
            KOGAS_GOLBAT: ("special_condition_confusion#1",),  # ひどいおんぱ
            DARK_WEEZING: ("self_damage#0", "opponent_bench_damage#0", "self_bench_damage#0",  # みんなでばくはつ
                           "special_condition_poison#1", "special_condition_paralysis#1"),  # しびれガス
            DARK_HYPNO: ("opponent_coin_heads#1", "opponent_coin_tails#1", "base#1=0"),  # ベンチをあやつる（相手が投げる）
            GIOVANNIS_NIDORINO: ("base#0=20", "base#0=40"),  # つのでえぐる（相手にカウンターがあれば + 20）
            GIOVANNIS_NIDOKING: ("persistent_effect_added#0",),  # すごむ
            GIOVANNIS_NIDOQUEEN: ("attack_failed#1", "base#1=50"),  # ラブラリアット（失敗・ベンチにサカキのニドキングがいない）
            DARK_MACHOKE: ("forced_switch#0", "forced_switch#1"),  # ひきずりだす・なぐりとばす
            DARK_MACHAMP: ("return_in_play_to_deck#1", "shuffle#1"),  # つまみだす
            ERIKAS_WEEPINBELL: ("forced_switch#1",),  # さそってとかす
            MISTYS_SEADRA: ("base#1=30", "base#1=90"),  # きぜつばり
            BROCKS_MANKEY: ("shuffle#0",),  # ひまつぶし
            MANKEY: ("shuffle#0",),  # いたずら
            PRIMEAPE: ("special_condition_confusion#1",),  # あばれまわる
        }
        for card_id, keys in expected.items():
            for key in keys:
                with self.subTest(card=card_id, key=key):
                    self.assertGreater(counted[card_id][key], 0)
        self.assertGreater(counted[GIOVANNIS_NIDORAN_M]["attack#1"], 0)  # いかりのいちげき（カウンター 2 つ以上のとき）

    def test_group_attack_counts_after_placing(self):
        """むれでおそうのダメージは、ベンチに出したあとの自分の場の「キョウのズバット」の数 × 10（ワザのログのあとの ``bench_from_deck`` の数 + ワザの前から場に
        いた数）。出したら山札を 1 回だけ切り、出さなかったら切らない。"""
        checked = Counter()
        for r in self.results:
            state = r["state"]
            log = state.log
            for i, e in enumerate(log):
                if e["kind"] != "attack" or state.cards[e["pokemon"]].card_id != KOGAS_ZUBAT:
                    continue
                end = next((j for j in range(i + 1, len(log)) if log[j]["kind"] in ("turn_end", "game_end")), len(log))
                window = log[i + 1:end]
                if any(x["kind"] == "confusion_damage" for x in window):
                    continue
                placed = sum(1 for x in window if x["kind"] == "bench_from_deck")
                shuffles = [x for x in window if x["kind"] == "shuffle" and x.get("effect") == f"{KOGAS_ZUBAT}#0"]
                self.assertEqual(len(shuffles), 1 if placed else 0)
                damage = next(x for x in window if x["kind"] == "damage" and "target" not in x)
                self.assertEqual(damage["steps"][0][1] % 10, 0)
                self.assertGreaterEqual(damage["steps"][0][1], 10 * (1 + placed))
                checked["placed" if placed else "none"] += 1
        self.assertTrue(checked["placed"] and checked["none"], checked)


class ToolTest(unittest.TestCase):
    def test_verification_decks(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える（同じ名前のカードは合わせて 4 枚まで）。15 枚はどれも入る。公開の固定のデッキ・前の版の検証用デッキには
        入れていない。"""
        pool = load_card_pool()
        decks = {label: games.deck_cards(label) for label in LABELS}
        for label, deck in decks.items():
            with self.subTest(deck=label):
                self.assertEqual(len(deck), 60)
                self.assertTrue(all(pool.is_playable(c) for c in deck))
                names = Counter(pool.get(c).name_ja for c in deck if not pool.get(c).is_basic_energy)
                self.assertLessEqual(max(names.values()), 4)
        self.assertTrue(set(V0_40_POKEMON) <= set().union(*decks.values()))
        self.assertFalse(any(set(V0_40_POKEMON) & set(d.cards()) for d in PRESET_DECKS.values()))
        for label in sorted(earlier_batch_decks("v0.40")):
            self.assertFalse(set(V0_40_POKEMON) & set(games.deck_cards(label)), label)


if __name__ == "__main__":
    unittest.main()

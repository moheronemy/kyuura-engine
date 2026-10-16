"""v0.36: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、11 枚の対戦（docs/sand-attack-retreat-lock-v0.36.md 7 章）。

検証用デッキ ``W36``（水・闘・無色）・``K36``（草・炎・雷）（tools/existing_effect_games.py）を、3 組（``PAIRINGS_V0_36``: ``W36`` 対 ``K36``・``K36`` 対
``P31``（ピッピ・ピクシー・カスミのコダックが v0.36 のワザをまねる）・``W36`` 対 ``A2``）に分け、席を入れかえて seed 0〜5（36 局。最初の 6 つの seed。
seed を探し回っていない）で進める。手順は v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順と、「にげる」ことができない効果を
受けたはたらく番に 1 度だけ「にげる」を宣言する手順（拒否 ``RETREAT_PREVENTED`` を起こす）を重ねたもの（対戦相手の AI ではない）。

36 局で、11 枚がどれも場に出て（進化先 3 枚は通常の進化の操作で）、19 のワザがどれも使われ、手順 4 のコインの「おもて」と「うら」（「うら」で失敗した
ワザ）・「1回できえる」効果の消去・「にげる」の拒否・くもがくれガスの山札にもどす処理とバトル場に出す決定が起こる（めずらしい場面の境界は単体テスト。
seed を探し回らない）。終わり方は次の分類で数える（勝敗・カードの強さ・デッキの釣り合いは評価しない）:

- 通常の勝敗（``game_over``）
- 既知の裁定による停止（``halted``）
- ``UNRESOLVED_…``・``UNSUPPORTED_…`` でワザの宣言を拒否されたあと、別の操作で続けた回数（終わり方とは別に数える。RD9 はここに入る）
- 手数の上限・想定外の拒否・内部エラー・監査の失敗（どれも 0）
"""

from __future__ import annotations

import unittest
from collections import Counter

from kyuura_engine import PRESET_DECKS
from kyuura_engine.cards import load_card_pool
from tests.helpers import DARK_JOLTEON, KOGAS_KOFFING, LT_SURGES_FEAROW, MISTYS_SEEL, SANDSHREW, SANDSLASH, V0_36_POKEMON
from tests.log_audit import log_problems
from tools import existing_effect_games as games

SEEDS = range(6)
KNOWN_REJECTIONS = {f"stopped_attack_{code}" for code in games.V031_STOPS} | {
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE"}
KNOWN_HALTS = {"UNRESOLVED_MULLIGAN_COMPENSATION", "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"}


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class SandAttackRetreatLockGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed, keep_state=True) for a, b in games.PAIRINGS_V0_36 for seat in ((a, b), (b, a)) for seed in SEEDS]

    def test_endings_are_classified_and_pass_the_audits(self):
        """終わり方は通常の勝敗か、既知の未解決による停止だけ（手数の上限・想定外の拒否・内部エラーはない）。どの局も、受け付けた操作の列を ``new_game`` から
        やり直したログが同じで、不変条件・ログの監査（手順 4 のコインの並び・「1回できえる」効果の消去・「にげる」ことができないポケモンが「にげる」を
        宣言していないこと・山札にもどしたカードとそのあとの山札を切る処理）・書き出しの監査が通る。"""
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
        """ワザの宣言を拒否されたあと続けた回数は、停止と分けて数える。拒否のコードは既知のものだけ（RD9 は場から確かめる）。「にげる」の拒否
        （``RETREAT_PREVENTED``）は、効果を受けたはたらく番の 1 度だけの宣言で起こり、場から確かめる。"""
        found = Counter()
        retreat = 0
        for r in self.results:
            found.update(r["unresolved_rejections"])
            retreat += r["observed"].get("stopped_retreat_RETREAT_PREVENTED", 0)
            self.assertEqual(r["observed"].get("stopped_retreat_RETREAT_PREVENTED", 0), r["policy"].get("v036_retreat_probe", 0))
        self.assertTrue(set(found) <= KNOWN_REJECTIONS, set(found) - KNOWN_REJECTIONS)
        self.assertGreater(retreat, 0)

    def test_every_card_and_attack_is_used(self):
        """36 局で、11 枚がどれも場に出て、19 のワザがどれも使われ、それぞれの効果が起こる。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for card_id in V0_36_POKEMON:
            uses = counted.get(card_id, Counter())
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertGreater(uses["in_play" if definition.stage == "basic" else "evolved_to"], 0)
                for attack in definition.attacks:
                    self.assertGreater(uses[f"attack#{attack.index}"], 0, attack.name_ja)
        expected = {
            SANDSHREW: ("gave_attack_coin_check", "attack_check_heads", "attack_check_tails"),
            MISTYS_SEEL: ("gave_cannot_retreat", "gave_attack_coin_check"),
            LT_SURGES_FEAROW: ("gave_cannot_retreat",),
            DARK_JOLTEON: ("gave_attack_coin_check", "special_condition_paralysis#1", "self_damage#1"),
            KOGAS_KOFFING: ("gave_attack_coin_check", "return_in_play_to_deck#1"),
            SANDSLASH: ("damage#1",),
        }
        for card_id, keys in expected.items():
            for key in keys:
                with self.subTest(card=card_id, key=key):
                    self.assertGreater(counted[card_id][key], 0)
        # 手順 4 のコインの「うら」（ワザの失敗）は、効果を与えたカードの側で数える（効果を受けたポケモンはどのカードでもよい）。「1回できえる」効果の
        # 消去（used）は、効果を受けたポケモンの側で数える
        self.assertGreater(sum(c["attack_check_tails"] for c in counted.values()), 0)
        self.assertGreater(sum(c["effect_removed_used"] for c in counted.values()), 0)


    def test_log_audit_detects_broken_sequences(self):
        """ログの監査は、v0.36 の並びが崩れたログを見つける（対戦のログから 1 つずつ取りのぞく）: 手順 4 のコインの「うら」のあとの ``attack_failed``・
        手順 4 のコイン（``attack_check``）・「1回できえる」効果を消したログ・山札にもどしたあとの ``shuffle``。"""
        def first_index(predicate):
            for r in self.results:
                for i, e in enumerate(r["state"].log):
                    if predicate(e):
                        return r["state"], i
            self.fail("対戦のログに、その場面がない")

        cases = {
            "attack_failed": lambda e: e["kind"] == "attack_failed" and e.get("reason") == "attack_check",
            "attack_check": lambda e: e["kind"] == "attack_check",
            "used": lambda e: e["kind"] == "persistent_effect_removed" and e["reason"] == "used",
            "shuffle_after_return": None,
        }
        for name, predicate in cases.items():
            with self.subTest(case=name):
                if predicate is None:
                    state, i = first_index(lambda e: e["kind"] == "return_in_play_to_deck")
                    i = next(j for j in range(i + 1, len(state.log)) if state.log[j]["kind"] == "shuffle")
                else:
                    state, i = first_index(predicate)
                self.assertEqual(log_problems(state), [])
                broken = state.clone()
                broken.log = state.log[:i] + state.log[i + 1:]
                self.assertNotEqual(log_problems(broken), [])


class ToolTest(unittest.TestCase):
    def test_verification_decks(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える。11 枚はどれも入る。公開の固定のデッキ・前の版の検証用デッキには入れていない。"""
        pool = load_card_pool()
        decks = {label: games.deck_cards(label) for label in ("W36", "K36")}
        for label, deck in decks.items():
            with self.subTest(deck=label):
                self.assertEqual(len(deck), 60)
                self.assertTrue(all(pool.is_playable(c) for c in deck))
        self.assertTrue(set(V0_36_POKEMON) <= set(decks["W36"]) | set(decks["K36"]))
        self.assertFalse(any(set(V0_36_POKEMON) & set(d.cards()) for d in PRESET_DECKS.values()))
        for label in games.DECKS:
            if label not in ("W36", "K36"):
                self.assertFalse(set(V0_36_POKEMON) & set(games.deck_cards(label)), label)


if __name__ == "__main__":
    unittest.main()

"""v0.26: 固定のデッキの第2版（``hitmonchan-dewgong-v2``・``venusaur-parasect-v2``。docs/preset-decks-v0.26.md）。

- 第1版（v0.20）の識別子・中身は変えない（別の識別子で第2版を並べる）。第1版の中身は v0.20 の記録（docs/preset-decks-v0.20.md 2・3 章）と
  同じことを、カードの名前ごとの枚数で確かめる（decks.py の並びを写した値ではなく、v0.20 の文書の表の値）。
- 第2版も構築の規定（p.308。60 枚・同じ名前は 4 枚まで・たねポケモンを含む）を満たし、どのカードも対応済み（v0.20 のテストが
  ``PRESET_DECKS`` のすべてを確かめる。ここでは第2版の考え方に関わる性質を確かめる）。
- 正式な対戦開始（``new_game``）から、tools/preset_deck_games.py の決まった手順（第1版と同じ手順）で第2版どうしを対戦させ、終わり方・監査・
  第2版で入れたカードの使用（パソコン通信・エネルギー回収・突風・ポケモン交換おじさん・ポケモン育て屋さん）と、フシギバナへの 2 つの
  進化の道（フシギソウ経由・ポケモン育て屋さん経由）を確かめる。勝率は確かめない。
- 開始の例（examples/start_preset_game.py）・対戦の道具（tools/preset_deck_games.py）・比べる道具（tools/preset_deck_comparison.py）から
  第2版を選べ、知らない識別子は対戦を 1 局も始めずに拒否する（0 局の成功として扱わない）。既定は第1版のまま。
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import subprocess
import sys
import unittest
from collections import Counter

from kyuura_engine import (
    Phase, check_invariants, deck_problems, load_card_pool, new_game, preset_deck, preset_deck_ids,
)
from tests.log_audit import log_problems, serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import preset_deck_comparison as comparison  # noqa: E402
from tools import preset_deck_games as driver  # noqa: E402

POOL = load_card_pool()
V1 = ("hitmonchan-dewgong", "venusaur-parasect")
V2 = ("hitmonchan-dewgong-v2", "venusaur-parasect-v2")

# v0.20 の文書（docs/preset-decks-v0.20.md 2・3 章）の表のとおりの第1版（名前ごとの枚数）
V1_BY_NAME = {
    "hitmonchan-dewgong": {
        "エビワラー": 4, "パウワウ": 4, "ジュゴン": 3, "コラッタ": 3, "オーキドはかせ": 4, "マサキ": 4, "きずぐすり": 4, "ポケモンいれかえ": 4,
        "プラスパワー": 4, "ディフェンダー": 4, "闘エネルギー": 12, "水エネルギー": 10,
    },
    "venusaur-parasect": {
        "フシギダネ": 4, "フシギソウ": 4, "フシギバナ": 3, "パラス": 4, "パラセクト": 3, "オーキドはかせ": 3, "マサキ": 4, "きずぐすり": 4,
        "ポケモンいれかえ": 4, "プラスパワー": 3, "ディフェンダー": 4, "草エネルギー": 20,
    },
}


def by_name(deck_id):
    return dict(Counter(POOL.get(c).name_ja for c in preset_deck(deck_id).cards()))


class FirstVersionKeptTest(unittest.TestCase):
    def test_first_version_ids_and_contents_are_unchanged(self):
        """第1版の識別子は登録の最初の 2 つのまま、中身は v0.20 の文書の表と同じ。"""
        self.assertEqual(preset_deck_ids()[:2], V1)
        for deck_id, expected in V1_BY_NAME.items():
            with self.subTest(deck=deck_id):
                self.assertEqual(by_name(deck_id), expected)
                self.assertEqual(preset_deck(deck_id).name_ja, {"hitmonchan-dewgong": "エビワラー・ジュゴン",
                                                                "venusaur-parasect": "フシギバナ・パラセクト"}[deck_id])

    def test_defaults_still_select_the_first_version(self):
        """開始の例・対戦の道具の既定は第1版のまま（黙って第2版に切りかえない）。"""
        self.assertEqual((driver.DECK_A, driver.DECK_B), V1)
        sys.path.insert(0, str(ROOT / "examples"))
        import start_preset_game as example
        with contextlib.redirect_stdout(io.StringIO()) as out:
            example.main([])
        self.assertIn("エビワラー・ジュゴン）", out.getvalue())
        self.assertNotIn("第2版", out.getvalue())


class SecondVersionTest(unittest.TestCase):
    def test_second_version_is_registered_and_legal(self):
        """第2版は別の識別子で、第1版と違う 60 枚の合法なデッキ（p.308）。名前に「第2版」を含む。"""
        self.assertEqual(set(preset_deck_ids()), set(V1) | set(V2))
        for v1, v2 in zip(V1, V2):
            with self.subTest(deck=v2):
                cards = preset_deck(v2).cards()
                self.assertEqual(len(cards), 60)
                self.assertEqual(deck_problems(cards), [])
                self.assertNotEqual(sorted(cards), sorted(preset_deck(v1).cards()))
                self.assertIn("第2版", preset_deck(v2).name_ja)

    def test_second_version_follows_its_design(self):
        """第2版の考え方（docs/preset-decks-v0.26.md 2・3 章）: どちらも探す・回収するトレーナーを入れ、ディフェンダーは入れない。デッキ B は
        たねポケモンが第1版より多く、フシギソウとポケモン育て屋さんの両方の道でフシギバナに進化できる。デッキ A は 2 進化ポケモンがいないので
        ポケモン育て屋さんを入れない。"""
        for deck_id in V2:
            names = by_name(deck_id)
            with self.subTest(deck=deck_id):
                for trainer in ("パソコン通信", "エネルギー回収", "突風"):
                    self.assertGreater(names.get(trainer, 0), 0, trainer)
                self.assertNotIn("ディフェンダー", names)
        a, b = (preset_deck(d).cards() for d in V2)
        self.assertFalse(any(POOL.get(c).is_stage2_pokemon for c in a))
        self.assertNotIn("ポケモン育て屋さん", by_name(V2[0]))
        basics = lambda cards: sum(POOL.get(c).is_basic_pokemon for c in cards)  # noqa: E731
        self.assertGreater(basics(b), basics(preset_deck(V1[1]).cards()))
        names_b = by_name(V2[1])
        self.assertGreater(names_b.get("フシギソウ", 0), 0)
        self.assertGreater(names_b.get("ポケモン育て屋さん", 0), 0)
        venusaur = next(POOL.get(c) for c in b if POOL.get(c).name_ja == "フシギバナ")
        self.assertEqual(venusaur.stage1_evolves_from, ("フシギダネ",))  # 育て屋さんの系統（v0.25）: 写しの 1 進化カードから求める
        self.assertIn("フシギダネ", names_b)

    def test_reading_one_deck_does_not_change_another(self):
        """読み出した一覧を変えても、ほかの取得（同じデッキ・別の版）は変わらない。"""
        before = {d: preset_deck(d).cards() for d in preset_deck_ids()}
        for deck_id in V2:
            cards = preset_deck(deck_id).cards()
            cards[:] = ["PMCG1-097"] * 60
            counts = preset_deck(deck_id).counts()
            counts.clear()
        self.assertEqual({d: preset_deck(d).cards() for d in preset_deck_ids()}, before)

    def test_new_game_starts_with_the_second_version(self):
        """正式な開始（new_game）にそのまま渡せ、デッキの記録は渡したカードと同じ。"""
        for seat in (V2, tuple(reversed(V2)), (V2[0], V1[1]), (V1[0], V2[1])):
            with self.subTest(seat=seat):
                decks = tuple(preset_deck(d).cards() for d in seat)
                state = new_game(*decks, seed=5)
                self.assertEqual([sorted(d) for d in state.decklists], [sorted(d) for d in decks])
                self.assertEqual(check_invariants(state), [])


class SelectionTest(unittest.TestCase):
    def test_example_selects_the_second_version_and_rejects_unknown_ids(self):
        sys.path.insert(0, str(ROOT / "examples"))
        import start_preset_game as example
        state = example.start(V2[0], V2[1], seed=2, first=1)
        self.assertEqual((state.phase, state.turn_number, state.current_player), (Phase.MAIN, 1, 1))
        listing = subprocess.run([sys.executable, str(ROOT / "examples" / "start_preset_game.py"), "--list"], capture_output=True, text=True)
        self.assertEqual(listing.returncode, 0, listing.stderr)
        for deck_id in V1 + V2:
            self.assertIn(deck_id, listing.stdout)
        unknown = subprocess.run([sys.executable, str(ROOT / "examples" / "start_preset_game.py"), "--deck0", "no-such-deck"],
                                 capture_output=True, text=True)
        self.assertNotEqual(unknown.returncode, 0)
        self.assertEqual(unknown.stdout, "")
        self.assertIn("no-such-deck", unknown.stderr)

    def test_driver_rejects_unknown_ids_and_variants_before_any_game(self):
        """知らない識別子・第2版に使えない変種は、1 局も始める前に拒否する（0 局の成功として扱わない）。"""
        with self.assertRaises(KeyError):
            driver.run(1, decks=("no-such-deck", V2[1]))
        with self.assertRaises(ValueError):
            driver.run(1, decks=V2, variant="gust")  # 変種は第1版のカードを置き換える一時的なデッキ
        for argv in (["--deck-a", "no-such-deck"], ["--games", "0"], ["--deck-a", V2[0], "--variant", "trader"],
                     ["--deck-a", V1[1], "--deck-b", V1[1]]):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    driver.main(argv)
                self.assertNotEqual(ctx.exception.code, 0)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            comparison.main(["--seeds", "0"])
        self.assertNotEqual(ctx.exception.code, 0)

    def test_driver_runs_a_chosen_pairing(self):
        """--deck-a・--deck-b の組み合わせで、席を入れかえて対戦する（結果の席の並びが選んだデッキ）。"""
        results = driver.run(1, decks=(V2[0], V1[1]))
        self.assertEqual([r["decks"] for r in results], [[V2[0], V1[1]], [V1[1], V2[0]]])
        summary = driver.summarize(results)
        self.assertEqual(set(summary["per_deck"]), {V2[0], V1[1]})


class SecondVersionGamesTest(unittest.TestCase):
    """第2版どうしの 2 局（A2 がプレイヤー 0 の seed 9、B2 がプレイヤー 0 の seed 6。比べた 80 局のうち、第2版で入れたカードと
    フシギバナへの 2 つの道がそろって起こる局）。"""

    @classmethod
    def setUpClass(cls):
        cls.games = [driver.play(V2, 9, keep_state=True, observe=True), driver.play(tuple(reversed(V2)), 6, keep_state=True, observe=True)]

    def test_games_end_and_pass_the_audits(self):
        for r in self.games:
            state = r["state"]
            with self.subTest(seed=r["seed"], decks=r["decks"]):
                self.assertEqual(r["outcome"], "game_over")
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])
                self.assertEqual(r["trainer_sequence_problems"], [])
                for key in comparison.CHECK_FAILURES:
                    self.assertEqual(r["policy"].get(key, 0), 0, key)

    def test_added_trainers_and_both_evolution_routes_happen(self):
        """第2版で入れたトレーナーを使い、フシギバナにフシギソウ経由とポケモン育て屋さん経由の両方で進化する（ログの evolve の trainer_card）。"""
        for r in self.games:
            state = r["state"]
            with self.subTest(seed=r["seed"], decks=r["decks"]):
                for deck_id in V2:
                    player = r["decks"].index(deck_id)
                    played = Counter(state.cards[e["card"]].card_id for e in state.log if e["kind"] == "play_trainer" and e["player"] == player)
                    for card in ("PMCG1-090", "PMCG1-076", "PMCG1-072"):
                        self.assertGreater(played[card], 0, (deck_id, card))
                b = r["decks"].index(V2[1])
                to_venusaur = [e for e in state.log if e["kind"] == "evolve" and e["player"] == b and e["to_card_id"] == "PMCG1-011"]
                self.assertTrue(any("trainer_card" in e for e in to_venusaur))
                self.assertTrue(any("trainer_card" not in e and e["from_card_id"] == "PMCG1-008" for e in to_venusaur))

    def test_observe_only_counts(self):
        """observe（v0.26）は数えるだけで、選ぶ操作を変えない（observe なしと同じ手数・終わり方・各デッキの動き）。"""
        for r in self.games:
            plain = driver.play(tuple(r["decks"]), r["seed"])
            with self.subTest(seed=r["seed"], decks=r["decks"]):
                for key in ("outcome", "steps", "turns", "per_deck", "conditions"):
                    self.assertEqual(plain.get(key), r.get(key))


class ComparisonToolTest(unittest.TestCase):
    """tools/preset_deck_comparison.py を 1 seed（4 組 × 2 席 = 8 局）で走らせる。"""

    @classmethod
    def setUpClass(cls):
        cls.results = comparison.compare(range(9, 10))

    def test_every_pairing_is_played_with_swapped_seats_and_classified(self):
        self.assertEqual(list(self.results), ["A1-B1", "A2-B1", "A1-B2", "A2-B2"])
        for name, result in self.results.items():
            with self.subTest(pairing=name):
                a, b = name.split("-")
                self.assertEqual([g["labels"] for g in result["games"]], [[a, b], [b, a]])
                summary = result["summary"]
                self.assertEqual(sum(summary["outcomes"].values()), 2)
                self.assertLessEqual(set(summary["outcomes"]), set(comparison.OUTCOMES))
                self.assertEqual(summary["audit_failures"], {})
                self.assertEqual(summary["audited_games"], 2)

    def test_turn_end_probe_uses_the_engine_and_replays_the_game(self):
        """番の終わりの確かめは、やり直した状態でエンジンにワザを渡す（受け付けたら could_attack、拒否ならそのコード）。ワザを使わずに
        終えた番の数は、ログの end_turn_without_attack と同じ。"""
        r = driver.play(V2, 9, keep_state=True, observe=True)
        probes, _, _, same = comparison.replay(r)
        self.assertTrue(same)
        state = r["state"]
        for player in (0, 1):
            ended = sum(1 for e in state.log if e["kind"] == "end_turn_without_attack" and e["player"] == player)
            self.assertEqual(len(probes[player]), ended)
            for probe in probes[player]:
                self.assertEqual(probe["class"] == "could_attack", "ok" in probe["codes"])
                self.assertTrue(all(c == "ok" or c.isupper() for c in probe["codes"]))


if __name__ == "__main__":
    unittest.main()

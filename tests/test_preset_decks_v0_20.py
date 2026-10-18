"""v0.20: 固定のデッキ（kyuura_engine.decks）の構築の合法性・読み出しの独立性・正式な対戦開始・対戦の中の動き。

- 構築の規定は p.308「対戦の前に」（60 枚・同じ名前は 4 枚まで（基本エネルギーカードは制限なし）・たねポケモンを入れる）と、進化の規定
  p.309・p.310（進化カードは「○○から進化」の名前のポケモンに重ねる）。どれも既存の記録（docs/rules-2000-02-14.md）を再利用している。
- デッキのカードは、どれもエンジンの照合の記録（kyuura_engine/data/card_verification.json）があるカード（v0.1〜v0.19 で照合済み）。
- 正式な対戦開始（``new_game``）から、決まった手順（tools/preset_deck_games.py。既存の統合テストの手順を再利用）で対戦させ、終わり方を
  分類し、各デッキの狙った動き（ベンチ・エネルギー・進化・トレーナー・ワザ・エナジートランス）が起こったことを数える。勝率は確かめない。
"""

from __future__ import annotations

import copy
import pathlib
import re
import subprocess
import sys
import unittest
from collections import Counter

import kyuura_engine
from kyuura_engine import (
    DEFAULT_EFFECTS, PRESET_DECKS, Phase, PresetDeck, check_invariants, deck_problems, load_card_pool, new_game, preset_deck, preset_deck_ids,
)
from kyuura_engine.cards import read_verification
from tests.log_audit import log_problems, serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import preset_deck_games as driver  # noqa: E402

STAGES = {"stage1": "basic", "stage2": "stage1"}
POOL = load_card_pool()


class DeckConstructionTest(unittest.TestCase):
    """壊れると対戦に使えなくなる条件（構築の規定・対応済み・進化の関係）。"""

    def test_every_preset_is_legal(self):
        """60 枚・同じ名前は 4 枚まで（基本エネルギーは制限なし）・たねポケモンを含む（p.308）。エンジンの検査（deck_problems）でも問題がない。"""
        for deck in PRESET_DECKS.values():
            with self.subTest(deck=deck.deck_id):
                cards = deck.cards()
                self.assertEqual(len(cards), 60)
                names = Counter(POOL.get(c).name_ja for c in cards if not POOL.get(c).is_basic_energy)
                self.assertLessEqual(max(names.values()), 4, names)
                self.assertTrue(any(POOL.get(c).is_basic_pokemon for c in cards))
                self.assertEqual(deck_problems(cards), [])
                self.assertEqual(len({c for c, _ in deck.entries}), len(deck.entries))  # 同じカード id を 2 行に分けない
                self.assertTrue(all(n > 0 for _, n in deck.entries))

    def test_every_card_attack_and_power_is_supported(self):
        """どのカードも対戦に使え、どのポケモンのどのワザ・特殊能力にも実装が登録されている（効果のないワザとして扱っていない）。"""
        for deck in PRESET_DECKS.values():
            for card_id, _ in deck.entries:
                definition = POOL.get(card_id)
                with self.subTest(deck=deck.deck_id, card=card_id):
                    self.assertTrue(POOL.is_playable(card_id), definition.unsupported_reasons)
                    if definition.category == "pokemon":
                        for index, _ in enumerate(definition.attacks):
                            self.assertIsNotNone(DEFAULT_EFFECTS.attack_entry(card_id, index))
                        for index, _ in enumerate(definition.powers):
                            self.assertIsNotNone(DEFAULT_EFFECTS.power_entry(card_id, index))
                    elif definition.category == "trainer":
                        self.assertIsNotNone(DEFAULT_EFFECTS.trainer_entry(card_id))

    def test_evolution_lines_are_complete(self):
        """進化カードは、デッキの中に「○○から進化」の名前の、1 つ前の段階のポケモンがいる（p.309・p.310）。"""
        for deck in PRESET_DECKS.values():
            pokemon = [POOL.get(c) for c, _ in deck.entries if POOL.get(c).category == "pokemon"]
            for d in pokemon:
                if d.stage in STAGES:
                    with self.subTest(deck=deck.deck_id, card=d.id):
                        sources = [s for s in pokemon if s.name_ja == d.evolves_from]
                        self.assertTrue(sources, d.evolves_from)
                        self.assertTrue(all(s.stage == STAGES[d.stage] for s in sources))

    def test_every_card_has_a_verification_record(self):
        """照合済みの記録の再利用の前提: どのカードにもエンジンの照合の記録がある（原典を読み直さずに使う）。"""
        records = read_verification()["cards"]
        for deck in PRESET_DECKS.values():
            for card_id, _ in deck.entries:
                with self.subTest(deck=deck.deck_id, card=card_id):
                    self.assertIn(card_id, records)


class ReadIndependenceTest(unittest.TestCase):
    def test_reading_returns_fresh_values(self):
        """読み出した側がリスト・辞書を変えても、次の読み出しは変わらない。"""
        for deck_id in preset_deck_ids():
            with self.subTest(deck=deck_id):
                deck = preset_deck(deck_id)
                first = deck.cards()
                expected = list(first)
                first.clear()
                counts = deck.counts()
                counts.clear()
                self.assertEqual(deck.cards(), expected)
                self.assertEqual(sum(deck.counts().values()), 60)

    def test_registry_and_decks_cannot_be_changed(self):
        with self.assertRaises(TypeError):
            PRESET_DECKS["x"] = PRESET_DECKS["hitmonchan-dewgong"]
        with self.assertRaises(AttributeError):
            preset_deck("hitmonchan-dewgong").entries = ()
        self.assertIsInstance(preset_deck("venusaur-parasect"), PresetDeck)

    def test_unknown_id_names_the_choices(self):
        with self.assertRaises(KeyError) as ctx:
            preset_deck("no-such-deck")
        self.assertIn("hitmonchan-dewgong", str(ctx.exception))

    def test_user_decks_are_separate_from_test_decks(self):
        """利用者向けのデッキはパッケージにあり、tests/ を読み込まない（テスト用のデッキと混ぜない）。"""
        source = (ROOT / "kyuura_engine" / "decks.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"^\s*(from|import)\s+tests", source, re.M))
        # v0.26 で第2版（-v2）を加えた。第1版の 2 つは残す（tests/test_preset_decks_v0_26.py が中身も確かめる）
        self.assertEqual(set(preset_deck_ids()), {"hitmonchan-dewgong", "venusaur-parasect", "hitmonchan-dewgong-v2", "venusaur-parasect-v2"})


class StartGameTest(unittest.TestCase):
    def test_new_game_accepts_every_pairing(self):
        """正式な開始（new_game）にそのまま渡せる。デッキの記録（decklists）は渡したカードと同じ。渡したリストは変わらない。"""
        for a in preset_deck_ids():
            for b in preset_deck_ids():
                with self.subTest(a=a, b=b):
                    decks = (preset_deck(a).cards(), preset_deck(b).cards())
                    before = copy.deepcopy(decks)
                    state = new_game(*decks, seed=3)
                    self.assertIn(state.phase, (Phase.SETUP_PLACEMENT, Phase.SETUP_MULLIGAN_DRAW))
                    self.assertEqual([sorted(d) for d in state.decklists], [sorted(d) for d in decks])
                    self.assertEqual(decks, before)
                    self.assertEqual(check_invariants(state), [])

    def test_example_script_reaches_the_first_turn(self):
        """examples/start_preset_game.py は、先攻の最初の番（MAIN）まで進める（対戦の開始だけの例）。"""
        sys.path.insert(0, str(ROOT / "examples"))
        import start_preset_game as example
        for first in (0, 1):
            for a, b in (("hitmonchan-dewgong", "venusaur-parasect"), ("venusaur-parasect", "hitmonchan-dewgong")):
                with self.subTest(first=first, a=a):
                    state = example.start(a, b, seed=first + 4, first=first)
                    self.assertEqual((state.phase, state.turn_number, state.current_player), (Phase.MAIN, 1, first))
        result = subprocess.run([sys.executable, str(ROOT / "examples" / "start_preset_game.py"), "--list"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("venusaur-parasect", result.stdout)

    def test_version(self):
        """版は pyproject.toml と同じ。v0.20 で 0.20.0、v0.21（突風）で 0.21.0、v0.22（パソコン通信）で 0.22.0、v0.23（エネルギー回収）で 0.23.0、v0.24（ポケモン交換おじさん）で 0.24.0、v0.25（ポケモン育て屋さん）で 0.25.0、v0.26（固定のデッキの第2版）で 0.26.0、v0.27（ストライク）で 0.27.0、v0.28（既存の効果の型で加えたポケモン 10 枚）で 0.28.0、v0.29（既存の効果の型で加えたポケモン 14 枚。kyuura データの採用）で 0.29.0、v0.30（エネルギーをトラッシュしてダメージを与えるワザの共通化とポケモン 5 枚）で 0.30.0、v0.31（v0.30 で保留した 22 枚の一括実装）で 0.31.0、v0.32（山札からベンチに出す・ダメージカウンターでダメージが決まる・与えたぶん回復するワザの 13 枚）で 0.32.0、v0.33（CD4 の再検討と、相手のエネルギーをトラッシュする・コインで失敗する／ダメージを与えられない・控えにもダメージを与えるワザの 15 枚）で 0.33.0、v0.34（バリアーに対するコインの見直し・ダメージのあとの決定をまたぐ処理と 14 枚）で 0.34.0、v0.35（可変枚数のコインの先読み・ダメージの計算の順番の決定と 5 枚）で 0.35.0、v0.36（手順 4 のコイン・「にげる」ことができない効果・自分を山札にもどす効果と 11 枚）で 0.36.0、v0.37（既存の効果の再利用を中心にした 15 枚）で 0.37.0、v0.38（控えへのダメージ・入れ替え・同じコインの複数の効果の 15 枚）で 0.38.0、v0.39（じばく・控えへのダメージ・場のポケモンの数でダメージが決まるワザの 15 枚）で 0.39.0、v0.40（場の数・条件付きの効果・入れ替え・カードの移動の 15 枚）で 0.40.0、v0.41（回復・ダメージカウンターの移動・特殊状態の変化を中心とする 15 枚）で 0.41.0、v0.42（回復・カウンター操作と特殊能力を持つ進化系統を中心とする 15 枚・特殊能力の決定と再開と使用後の処理）で 0.42.0、v0.43（宣言して使う特殊能力 6 つと場に出たときに使う特殊能力 3 つを持つ 9 枚）で 0.43.0、v0.44（検索・進化・1 度だけ使えるワザの 14 枚とトレーナーのサカキ）で 0.44.0、v0.45（条件つきのダメージ・エネルギーの移動とトラッシュ・受けたダメージを返す効果などの 15 枚と GV1 の停止コード）で 0.45.0、v0.46（常にはたらく特殊能力を持つ 8 枚と関連する 3 枚）で 0.46.0、v0.47（なにかの化石・ピッピ人形と化石のポケモン・見えない情報・トレーナーの使用の禁止の 13 枚）で 0.47.0、v0.48（場のポケモンの今有効な最大HP・タイプ・弱点・抵抗力を参照する仕組みと 7 枚）で 0.48.0、v0.49（ワザの出どころを区別する共通の処理と、ナツメのフーディン・メタモン・タケシのキュウコン・思い出させる）で 0.49.0、v0.50（退化の共通の処理と、ミュウ・退化スプレー）で 0.50.0、v0.51（トラッシュのたねポケモンを持ち主のベンチに出す共通の処理と、ナツメのスリーパー・元気のかけら・ポケモンの笛）で 0.51.0、v0.52（場のポケモンを場から手札・山札にもどす共通の処理と、フジろうじん・ポケモン回収・エリカのハクリュー）で 0.52.0、v0.53（山札・トラッシュからカードを選ぶトレーナー 10 枚）で 0.53.0、v0.54（手札の入れ替え・ドロー・情報の確認のトレーナー 10 枚）で 0.54.0 にした。"""
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertEqual(re.search(r'^version = "([^"]+)"', text, re.M).group(1), kyuura_engine.__version__)
        self.assertEqual(kyuura_engine.__version__, "0.54.0")


class PresetDeckGamesTest(unittest.TestCase):
    """正式な対戦開始から、席を入れかえて 10 局ずつ（合計 20 局）。tools/preset_deck_games.py の手順。"""

    GAMES = 10
    KNOWN = {"game_over", "sudden_death", "halted", "step_limit", "unexpected_rejection", "internal_error"}

    @classmethod
    def setUpClass(cls):
        cls.results = driver.run(cls.GAMES, keep_state=True)
        cls.summary = driver.summarize([{k: v for k, v in r.items() if k not in ("state", "commands")} for r in cls.results])

    def test_every_game_is_classified_and_none_failed_internally(self):
        """どの局も分類のどれかに入り（落とさない）、内部エラー・想定外の拒否はない。"""
        outcomes = Counter(r["outcome"] for r in self.results)
        self.assertEqual(sum(outcomes.values()), 2 * self.GAMES)
        self.assertLessEqual(set(outcomes), self.KNOWN)
        self.assertEqual(outcomes["internal_error"], 0, [r.get("error") for r in self.results])
        self.assertEqual(outcomes["unexpected_rejection"], 0, [r.get("error") for r in self.results])

    def test_intended_moves_happen(self):
        """各デッキの狙った動きが起こる（1 回も起こらない試験を成功と数えない）。"""
        games_with = self.summary["games_with"]
        expected = {
            driver.DECK_A: ["bench_played", "attach_FIGHTING", "attach_WATER", "evolve_PMCG1-030", "attack_PMCG1-058#0", "attack_PMCG1-058#1",
                            "attack_PMCG1-030#0", "attack_PMCG1-030#1"],
            driver.DECK_B: ["bench_played", "attach_GRASS", "evolve_PMCG1-008", "evolve_PMCG1-011", "evolve_PMCG2-010", "energy_trans",
                            "attack_PMCG2-010#0", "attack_PMCG1-011#0"],
        }
        trainers = ["PMCG1-077", "PMCG1-074", "PMCG1-071", "PMCG1-073", "PMCG1-081", "PMCG1-079"]
        for deck, keys in expected.items():
            for key in keys + [f"trainer_{t}" for t in trainers]:
                with self.subTest(deck=deck, key=key):
                    self.assertGreater(games_with[deck].get(key, 0), 0)
        self.assertGreater(self.summary["policy"].get("attach_bench_growing", 0), 0)

    def test_final_states_pass_the_audits(self):
        for r in self.results:
            state = r["state"]
            with self.subTest(seed=r["seed"], decks=r["decks"]):
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_games_are_reproducible(self):
        """同じ席・同じ seed なら同じ結果（終わり方・手数・各デッキの動き）。"""
        for r in self.results[:: self.GAMES // 2]:
            again = driver.play(tuple(r["decks"]), r["seed"])
            with self.subTest(seed=r["seed"], decks=r["decks"]):
                for key in ("outcome", "steps", "turns", "per_deck", "conditions"):
                    self.assertEqual(again.get(key), r.get(key))


if __name__ == "__main__":
    unittest.main()

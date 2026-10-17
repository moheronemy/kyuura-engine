"""v0.43: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、9 枚の対戦（docs/declared-entry-powers-v0.43.md 7 章）。

検証用デッキ ``G43``（草）・``R43``（炎・超）・``L43``（雷・無色。ポケモン育て屋さん 2 枚）（tools/existing_effect_games.py）を、4 組（``PAIRINGS_V0_43``: ``G43`` 対
``R43``・``R43`` 対 ``L43``・``L43`` 対 ``G43``・``G43`` 対 ``P31``（ピッピ・ピクシー・カスミのコダックが v0.43 のワザを自分のワザとして使う））に分け、席を入れかえて
seed 0〜5（48 局。最初の 6 つの seed。seed を探し回っていない）で進める。手順は v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを選ぶ手順と、使っていない
ワザのためにエネルギーをためる手順（v0.38 と同じ）と、v0.42 の特殊能力を使う手順に、v0.43 の宣言する特殊能力を使う手順（``_v043_power``）と決定の答え方
（``_v043_decision``。場に出たときの特殊能力の使う機会は 4 回に 1 回使わない）を重ねたもの（対戦相手の AI ではない）。

48 局で、9 枚がどれも場に出て、9 のワザがどれも使われ、9 つの特殊能力がどれも使われる（場に出たときの 3 つは、使う・使わないの両方）。こっそりかみつくのきぜつ
（ログ ``knock_out`` の ``timing`` が ``power``）とサイド・バトル場に出す処理、ポケモン育て屋さんで重ねたわるいカイリューの使う機会（トレーナーの処理にもどる）が起こり、
どれも番のプレイヤーの番にもどる。終わり方は次の分類で数える（勝敗・カードの強さ・デッキの釣り合いは評価しない）:

- 通常の勝敗（``game_over``）・サドンデス（``sudden_death``）
- 既知の裁定による停止（``halted``。対戦準備の ``UNRESOLVED_MULLIGAN_COMPENSATION``）
- ``UNRESOLVED_…``・``UNSUPPORTED_…``・使うための条件でワザの宣言を拒否されたあと、別の操作で続けた回数（終わり方とは別に数える）
- 手数の上限・想定外の拒否・内部エラー・監査の失敗（どれも 0）
"""

from __future__ import annotations

import copy
import unittest
from collections import Counter
from types import MappingProxyType

from kyuura_engine import PRESET_DECKS, Phase
from kyuura_engine.cards import load_card_pool
from tests.helpers import (
    DARK_DRAGONAIR,
    DARK_DRAGONITE,
    DARK_GLOOM,
    DARK_GOLBAT,
    DARK_SLOWBRO,
    ERIKAS_BELLSPROUT_40,
    LT_SURGES_MAGNETON,
    POKEMON_BREEDER,
    ROCKET_CHARMANDER,
    ROCKET_DROWZEE,
    V0_43_POKEMON,
)
from tests.log_audit import log_problems
from tests.test_bench_switch_combined_v0_38_games import earlier_batch_decks
from tools import existing_effect_games as games

SEEDS = range(6)
LABELS = ("G43", "R43", "L43")
KNOWN_REJECTIONS = {f"stopped_attack_{code}" for code in games.V031_STOPS} | {
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE",
    "stopped_attack_UNRESOLVED_EVADED_EFFECT_COIN"}
KNOWN_HALTS = {"UNRESOLVED_MULLIGAN_COMPENSATION", "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"}
EVOLVE_CHAIN = {"special_conditions_removed", "persistent_effect_removed", "retreat_failure_cleared"}


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class DeclaredEntryPowersGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed, keep_state=True) for a, b in games.PAIRINGS_V0_43 for seat in ((a, b), (b, a)) for seed in SEEDS]

    def test_endings_are_classified_and_pass_the_audits(self):
        """終わり方は通常の勝敗・サドンデスか、既知の未解決による停止だけ（手数の上限・想定外の拒否・内部エラーはない）。どの局も、受け付けた操作の列を
        ``new_game`` からやり直したログが同じで、不変条件・ログの監査（v0.43 の特殊能力の宣言のあとの処理・コインの結果・使う機会と答え・特殊能力のダメージと
        きぜつ・トラッシュから手札に加える・山札からベンチに出す処理の組み立て直しを含む）・書き出しの監査・トレーナーの使用の並びが通る。"""
        self.assertEqual(len(self.results), 48)
        outcomes = Counter(r["outcome"] for r in self.results)
        self.assertEqual(set(outcomes) - {"game_over", "sudden_death", "halted"}, set())
        for r in self.results:
            with self.subTest(decks=r["decks"], seed=r["seed"]):
                if r["outcome"] == "halted":
                    self.assertIn(r["halt_code"], KNOWN_HALTS)
                self.assertEqual(r["audit"], {})
                self.assertEqual(r["trainer_sequence_problems"], [])
                self.assertEqual({k for k in r["observed"] if "unexpected" in k or k.startswith("rejected_power")}, set())
        self.assertGreater(outcomes["game_over"], 40)

    def test_rejections_are_counted_apart_from_halts(self):
        """ワザの宣言を拒否されたあと続けた回数は、停止と分けて数える。拒否のコードは既知のものだけで、場から確かめる（``V031_STOPS``）。特殊能力の使用は拒否されない
        （手順が使える場面でだけ使う）。"""
        found = Counter()
        for r in self.results:
            found.update(r["unresolved_rejections"])
        self.assertTrue(set(found) <= KNOWN_REJECTIONS, set(found) - KNOWN_REJECTIONS)

    def test_every_card_attack_and_power_is_used(self):
        """48 局で、9 枚がどれも場に出て（進化先は進化の操作で）、9 のワザがどれも使われ、9 つの特殊能力がどれも使われ、それぞれの効果が起こる。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for card_id in V0_43_POKEMON:
            uses = counted.get(card_id, Counter())
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertGreater(uses["in_play" if definition.stage == "basic" else "evolved_to"], 0)
                for attack in definition.attacks:
                    self.assertGreater(uses[f"attack#{attack.index}"], 0, attack.name_ja)
                self.assertGreater(uses["power_declared"], 0)
        expected = {
            DARK_GLOOM: ("power_coin_heads", "power_coin_tails", "power_special_condition_opponent", "power_special_condition_own",
                         "special_condition_poison#0"),  # くさいかふん・どくのこな
            ROCKET_DROWZEE: ("power_special_condition_opponent", "power_special_condition_own", "special_condition_sleep#0"),  # えんかくさいみん・あくむ
            ROCKET_CHARMANDER: ("power_move_energy", "damage#0"),  # ほのおをもらう・ほのおのしっぽ
            ERIKAS_BELLSPROUT_40: ("power_move_energy", "opponent_bench_damage#0"),  # ようぶんきゅうしゅう・のびるつる
            LT_SURGES_MAGNETON: ("power_move_energy", "self_damage#0"),  # エナジーチャージ・メガショック
            DARK_DRAGONAIR: ("power_reveal_from_deck", "power_shuffle", "base#0=40"),  # しんかのひかり・しっぽでつく
            DARK_GOLBAT: ("power_entry_used", "power_entry_declined", "power_power_damage", "opponent_bench_damage#0", "damage#0"),  # こっそりかみつく・ふらふらとぶ
            DARK_SLOWBRO: ("power_entry_used", "power_entry_declined", "power_recover_pokemon", "power_recover_pokemon_none", "attack_failed#0"),  # つりあげる
            DARK_DRAGONITE: ("power_entry_used", "power_entry_declined", "power_bench_from_deck", "power_shuffle", "attack_failed#0"),  # てしたをよぶ
        }
        for card_id, keys in expected.items():
            for key in keys:
                with self.subTest(card=card_id, key=key):
                    self.assertGreater(counted[card_id][key], 0)

    def test_soak_up_moves_two_cards_in_one_use_and_energy_charge_repeats(self):
        """ようぶんきゅうしゅうは 1 回の使用で 2 枚つけかえることがあり（宣言のあとの ``move_energy`` が 2 つ）、エナジーチャージは 1 回で 2 枚以上つけかえることが
        ある（同じ番に 2 回使うことは、手順が番ごとに 1 度しか試さないので対戦では起こらない。tests/test_declared_entry_powers_v0_43.py の EnergyChargeTest）。"""
        seen = Counter()
        for r in self.results:
            log = r["state"].log
            for i, e in enumerate(log):
                if e["kind"] != "pokemon_power" or "power" not in e:
                    continue
                moved = 0
                for x in log[i + 1:]:
                    if x["kind"] != "move_energy" or x.get("pokemon_id") != e["pokemon_id"]:
                        break
                    moved += 1
                card = r["state"].cards[e["pokemon"]].card_id
                seen[(card, min(moved, 2))] += 1
        self.assertGreater(seen[(ERIKAS_BELLSPROUT_40, 2)], 0, seen)
        self.assertGreater(seen[(LT_SURGES_MAGNETON, 2)], 0, seen)

    def test_entry_opportunity_comes_right_after_the_evolution_and_is_answered_once(self):
        """場に出たときの特殊能力を持つカードを手札から進化させたら、すぐ次のログがその答え（``pokemon_power``（``entry``）か ``entry_power_declined``）で、
        同じポケモンの答えはそれ 1 つだけ（2 度の機会・``MAIN`` からの使用はない）。"""
        entry_cards = {DARK_GOLBAT, DARK_SLOWBRO, DARK_DRAGONITE}
        checked = Counter()
        for r in self.results:
            state = r["state"]
            log = state.log
            for i, e in enumerate(log):
                if e["kind"] == "evolve" and state.cards[e["to_card"]].card_id in entry_cards:
                    # 進化の手順のログ（特殊状態・持続する効果・にげるの失敗の記録を消す）のすぐあと
                    nxt = next(x for x in log[i + 1:] if x["kind"] not in EVOLVE_CHAIN)
                    with self.subTest(decks=r["decks"], seed=r["seed"], turn=e["turn"]):
                        self.assertIn(nxt["kind"], ("pokemon_power", "entry_power_declined"))
                        self.assertEqual(nxt["pokemon_id"], e["pokemon_id"])
                        if nxt["kind"] == "pokemon_power":
                            self.assertEqual(nxt["entry"], "hand")
                    checked[nxt["kind"]] += 1
                if e["kind"] == "pokemon_power" and state.cards[e["pokemon"]].card_id in entry_cards:
                    self.assertIn("entry", e)
        self.assertTrue(checked["pokemon_power"] and checked["entry_power_declined"], checked)

    def test_sneak_attack_knock_outs_return_to_the_turn(self):
        """こっそりかみつくで HP 以上になったポケモンは、すぐに ``timing`` が ``power`` のきぜつになり、サイドを取り、（バトル場なら）相手が出したあと、同じ番の
        プレイヤーの番が続く（次の番の終わりは同じ番）。"""
        checked = 0
        for r in self.results:
            log = r["state"].log
            for i, e in enumerate(log):
                if e["kind"] == "knock_out" and e.get("timing") == "power":
                    self.assertEqual(log[i - 1]["kind"], "power_damage")
                    self.assertTrue(log[i - 1]["knocked_out"])
                    later = [x for x in log[i + 1:] if x["kind"] in ("turn_end", "game_end")][:1]
                    self.assertTrue(later)
                    if later[0]["kind"] == "turn_end":
                        self.assertEqual(later[0]["turn"], e["turn"])
                    checked += 1
        self.assertGreater(checked, 0)

    def test_breeder_route_returns_to_the_trainer(self):
        """ポケモン育て屋さんでわるいカイリューを重ねたら、使う機会の答え（使う・使わない）と特殊能力の処理（山札からベンチに出す・切る）のあとで、同じ番に
        ポケモン育て屋さんをトラッシュする（ログ ``discard_trainer``。そのあいだにほかの操作はない）。"""
        checked = Counter()
        for r in self.results:
            state = r["state"]
            log = state.log
            for i, e in enumerate(log):
                if e["kind"] == "evolve" and e.get("trainer_card") is not None and state.cards[e["to_card"]].card_id == DARK_DRAGONITE:
                    self.assertEqual(state.cards[e["trainer_card"]].card_id, POKEMON_BREEDER)
                    answer = log[i + 1]
                    self.assertIn(answer["kind"], ("pokemon_power", "entry_power_declined"))
                    end = next(j for j in range(i + 1, len(log)) if log[j]["kind"] == "discard_trainer")
                    self.assertEqual((log[end]["card"], log[end]["turn"]), (e["trainer_card"], e["turn"]))
                    between = {x["kind"] for x in log[i + 2:end]}
                    self.assertLessEqual(between, {"bench_from_deck", "shuffle"})
                    checked[answer["kind"]] += 1
        self.assertTrue(checked["pokemon_power"] and checked["entry_power_declined"], checked)

    def test_power_use_never_ends_the_turn(self):
        """特殊能力の宣言・使う機会の答えのあと、同じ番にワザ・番の終わりが続く（こんらんのコインを投げない）。"""
        for r in self.results:
            state = r["state"]
            log = state.log
            for i, e in enumerate(log):
                if e["kind"] in ("pokemon_power", "entry_power_declined"):
                    nxt = log[i + 1] if i + 1 < len(log) else None
                    with self.subTest(decks=r["decks"], seed=r["seed"], turn=e["turn"]):
                        self.assertTrue(nxt is None or nxt["kind"] not in ("turn_end", "confusion_check"))
            self.assertTrue(state.phase in (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED))

    def test_the_log_audit_catches_broken_v043_logs(self):
        """ログの監査は、v0.43 の特殊能力・ワザのログを壊すと問題を報告する（監査が素通りしていない）: 使う機会の答えを消す・宣言の ``entry`` を消す、
        特殊能力のダメージの量を変える、トラッシュから手札に加えたログを消す、山札からベンチに出したあとの切る処理を消す、つけかえの行き先を変える、コインの
        特殊状態の側を変える、しんかのひかりの切る処理を消す、特殊能力のあとのきぜつの時点を変える。"""
        def tampered(state, pred, change):
            log = list(state.log)
            for i, e in enumerate(log):
                if pred(e, log, i):
                    new = change(dict(e))
                    if new is None:
                        del log[i]
                    else:
                        log[i] = MappingProxyType(new)
                    broken = copy.deepcopy(state)
                    broken.log = tuple(log)
                    return broken
            return None

        def after(kind, **match):
            return lambda e, log, i: e["kind"] == kind and all(e.get(k) == v for k, v in match.items())

        def follows(kind, previous):
            return lambda e, log, i: e["kind"] == kind and "power" in e and log[i - 1]["kind"] == previous

        cases = {
            "drop entry_power_declined": (after("entry_power_declined"), lambda e: None),
            "drop entry": (lambda e, log, i: e["kind"] == "pokemon_power" and "entry" in e, lambda e: {k: v for k, v in e.items() if k != "entry"}),
            "power damage amount": (after("power_damage"), lambda e: {**e, "amount": 20, "total_damage": e["total_damage"] + 10}),
            "drop recover_pokemon": (after("recover_pokemon"), lambda e: None),
            "drop shuffle after summon": (follows("shuffle", "bench_from_deck"), lambda e: None),
            "move energy target": (lambda e, log, i: e["kind"] == "move_energy" and "power" in e and log[i - 1]["kind"] == "pokemon_power",
                                   lambda e: {**e, "to_pokemon_id": e["from_pokemon_id"]}),
            "coin condition side": (lambda e, log, i: e["kind"] == "special_condition" and "@power" in str(e.get("effect")),
                                    lambda e: {**e, "player": 1 - e["player"]}),
            "drop light shuffle": (follows("shuffle", "reveal_from_deck"), lambda e: None),
            "knock out timing": (after("knock_out", timing="power"), lambda e: {**e, "timing": "attack"}),
        }
        for name, (pred, change) in cases.items():
            with self.subTest(case=name):
                found = None
                for r in self.results:
                    found = tampered(r["state"], pred, change)
                    if found is not None:
                        break
                self.assertIsNotNone(found, name)
                self.assertTrue(log_problems(found), name)
        for r in self.results:
            self.assertEqual(log_problems(r["state"]), [])


class ToolTest(unittest.TestCase):
    def test_verification_decks(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える。9 枚はどれも入る。公開の固定のデッキ・前の版の検証用デッキには入れていない。"""
        pool = load_card_pool()
        decks = {label: games.deck_cards(label) for label in LABELS}
        for label, deck in decks.items():
            with self.subTest(deck=label):
                self.assertEqual(len(deck), 60)
                self.assertTrue(all(pool.is_playable(c) for c in deck))
                names = Counter(pool.get(c).name_ja for c in deck if not pool.get(c).is_basic_energy)
                self.assertLessEqual(max(names.values()), 4)
        self.assertTrue(set(V0_43_POKEMON) <= set().union(*decks.values()))
        self.assertIn(POKEMON_BREEDER, decks["L43"])
        self.assertFalse(any(set(V0_43_POKEMON) & set(d.cards()) for d in PRESET_DECKS.values()))
        for label in sorted(earlier_batch_decks("v0.43")):
            self.assertFalse(set(V0_43_POKEMON) & set(games.deck_cards(label)), label)


if __name__ == "__main__":
    unittest.main()

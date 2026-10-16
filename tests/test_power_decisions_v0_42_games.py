"""v0.42: 正式な開始（``new_game``・60 枚・サイド 6 枚）からの、15 枚の対戦（docs/power-decisions-v0.42.md 7 章）。

検証用デッキ ``G42``（草）・``P42``（超）・``D42``（超）・``W42``（水・無色）（tools/existing_effect_games.py）を、5 組（``PAIRINGS_V0_42``: ``G42`` 対 ``P42``・
``P42`` 対 ``D42``・``D42`` 対 ``W42``・``W42`` 対 ``G42``・``D42`` 対 ``P31``（ピッピ・ピクシー・カスミのコダックが v0.42 のワザを自分のワザとして使う））に分け、
席を入れかえて seed 0〜5（60 局。最初の 6 つの seed。seed を探し回っていない）で進める。手順は v0.26 から変えていない手順に、対象のカードがまだ使っていないワザを
選ぶ手順と、使っていないワザのためにエネルギーをためる手順（v0.38 と同じ）と、v0.42 の宣言する特殊能力を使う手順（``_v042_power``。使えない特殊状態・この番に
使ったものは使わない）と、ワザ・特殊能力の決定の答え方（``_v042_decision``）を重ねたもの（対戦相手の AI ではない）。

60 局で、15 枚がどれも場に出て、21 のワザがどれも使われ、8 つの特殊能力がどれもはたらく（宣言する 7 つは宣言され、ぼうぎょかふんは「おもて」・「うら」の両方）。
特殊能力の処理のあとのきぜつ（のろい。ログ ``knock_out`` の ``timing`` が ``power``）とサイド・バトル場に出す処理、おくびょうでバトル場が空いたあとのバトル場に出す
処理が起こり、どれも番のプレイヤーの番にもどる。終わり方は次の分類で数える（勝敗・カードの強さ・デッキの釣り合いは評価しない）:

- 通常の勝敗（``game_over``）・サドンデス（``sudden_death``）
- 既知の裁定による停止（``halted``。対戦準備の ``UNRESOLVED_MULLIGAN_COMPENSATION``）
- ``UNRESOLVED_…``・``UNSUPPORTED_…``・使うための条件でワザの宣言を拒否されたあと、別の操作で続けた回数（終わり方とは別に数える。テレポートブラストの Z23・
  とうめいの T19b などはここに入る）
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
    DARK_ALAKAZAM,
    DARK_KADABRA,
    DRAGONITE,
    ERIKAS_CLEFABLE,
    ERIKAS_CLEFAIRY,
    ERIKAS_VICTREEBEL,
    ERIKAS_VILEPLUME,
    GENGAR,
    SABRINAS_ABRA,
    SABRINAS_JYNX,
    SABRINAS_KADABRA,
    SLOWBRO,
    TENTACOOL,
    TENTACRUEL,
    V0_42_POKEMON,
    VILEPLUME,
)
from tests.log_audit import log_problems
from tests.test_bench_switch_combined_v0_38_games import earlier_batch_decks
from tools import existing_effect_games as games

SEEDS = range(6)
LABELS = ("G42", "P42", "D42", "W42")
# T19b（P42 のゴースト（化石の秘密）の「とうめい」。tests/v017_games.py の play_game が場から確かめる）も既知
KNOWN_REJECTIONS = {f"stopped_attack_{code}" for code in games.V031_STOPS} | {
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE",
    "stopped_attack_UNRESOLVED_EVADED_EFFECT_COIN"}
KNOWN_HALTS = {"UNRESOLVED_MULLIGAN_COMPENSATION", "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"}


def totals(results):
    counted = {}
    for r in results:
        for card_id, uses in r["card_uses"].items():
            counted.setdefault(card_id, Counter()).update(uses)
    return counted


class PowerDecisionsGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [games.play(seat, seed, keep_state=True) for a, b in games.PAIRINGS_V0_42 for seat in ((a, b), (b, a)) for seed in SEEDS]

    def test_endings_are_classified_and_pass_the_audits(self):
        """終わり方は通常の勝敗・サドンデスか、既知の未解決による停止だけ（手数の上限・想定外の拒否・内部エラーはない）。どの局も、受け付けた操作の列を
        ``new_game`` からやり直したログが同じで、不変条件・ログの監査（v0.42 の特殊能力の宣言のあとの処理・コインの結果・手札にもどす・山札から進化させる・
        特殊能力のあとのきぜつのログの組み立て直しを含む）・書き出しの監査が通る。"""
        self.assertEqual(len(self.results), 60)
        outcomes = Counter(r["outcome"] for r in self.results)
        self.assertEqual(set(outcomes) - {"game_over", "sudden_death", "halted"}, set())
        for r in self.results:
            with self.subTest(decks=r["decks"], seed=r["seed"]):
                if r["outcome"] == "halted":
                    self.assertIn(r["halt_code"], KNOWN_HALTS)
                self.assertEqual(r["audit"], {})
                self.assertEqual(r["trainer_sequence_problems"], [])
                self.assertEqual({k for k in r["observed"] if "unexpected" in k or k.startswith("rejected_power")}, set())
        self.assertGreater(outcomes["game_over"], 50)

    def test_rejections_are_counted_apart_from_halts(self):
        """ワザの宣言を拒否されたあと続けた回数は、停止と分けて数える。拒否のコードは既知のものだけで、場から確かめる（``V031_STOPS``）。特殊能力の使用は拒否されない
        （手順が使える場面でだけ使う）。"""
        found = Counter()
        for r in self.results:
            found.update(r["unresolved_rejections"])
        self.assertTrue(set(found) <= KNOWN_REJECTIONS, set(found) - KNOWN_REJECTIONS)

    def test_every_card_attack_and_power_is_used(self):
        """60 局で、15 枚がどれも場に出て（進化先は進化の操作で）、21 のワザがどれも使われ、8 つの特殊能力がどれもはたらき、それぞれの効果が起こる。"""
        counted = totals(self.results)
        pool = load_card_pool()
        for card_id in V0_42_POKEMON:
            uses = counted.get(card_id, Counter())
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertGreater(uses["in_play" if definition.stage == "basic" else "evolved_to"], 0)
                for attack in definition.attacks:
                    self.assertGreater(uses[f"attack#{attack.index}"], 0, attack.name_ja)
        expected = {
            SABRINAS_JYNX: ("attack_heal#0", "draw#0", "gave_cannot_retreat"),  # よいおこない・だきつく
            VILEPLUME: ("power_declared", "power_coin_heads", "power_coin_tails", "power_power_heal", "special_condition_confusion#0"),  # ヒーリング・はなびらのまい
            SLOWBRO: ("power_move_damage_counter", "special_condition_paralysis#0"),  # へんなこうどう・ねんりき
            GENGAR: ("power_move_damage_counter", "damage#0"),  # のろい・ナイトヘッド
            ERIKAS_VILEPLUME: ("power_power_confusion_True", "power_power_confusion_False", "drain_heal#0"),  # ぼうぎょかふん・メガドレイン
            SABRINAS_ABRA: ("return_energy_to_hand#0",),  # エネループ
            SABRINAS_KADABRA: ("place_damage_counters#0", "damage#1"),  # ライフダウン・サイコショット
            DRAGONITE: ("power_switch", "base#0=80"),  # かけつける・たたきつける
            ERIKAS_VICTREEBEL: ("power_coin_heads", "power_coin_tails", "power_switch"),  # かおりのわな
            DARK_KADABRA: ("power_discard_from_hand",),  # ぶっしつこうかん
            DARK_ALAKAZAM: ("switch#0", "switch_declined#0", "damage#1"),  # テレポートブラスト（入れ替える・入れ替えない）・マインドショック
            TENTACOOL: ("power_return_in_play_to_hand",),  # おくびょう
            TENTACRUEL: ("special_condition_confusion#0", "special_condition_poison#1"),  # ちょうおんぱ・クラゲばり
            ERIKAS_CLEFAIRY: ("evolve#0", "evolve_from_deck_none#0", "shuffle#0"),  # つきのちから
            ERIKAS_CLEFABLE: ("return_in_play_to_hand#0",),  # ようせいのきせき
        }
        for card_id, keys in expected.items():
            for key in keys:
                with self.subTest(card=card_id, key=key):
                    self.assertGreater(counted[card_id][key], 0)

    def test_after_power_knock_outs_and_promotions_return_to_the_turn(self):
        """のろいで HP 以上になったポケモンは、すぐに ``timing`` が ``power`` のきぜつになり、サイドを取り、（バトル場なら）相手が出したあと、同じ番のプレイヤーの
        番が続く（次のログは同じ番）。おくびょうでバトル場をもどしたら、きぜつ・サイドなしに控えを出す。"""
        checked = Counter()
        for r in self.results:
            log = r["state"].log
            for i, e in enumerate(log):
                if e["kind"] == "knock_out" and e.get("timing") == "power":
                    self.assertEqual(log[i - 1]["kind"], "move_damage_counter")
                    later = [x for x in log[i + 1:] if x["kind"] in ("turn_end", "game_end")][:1]
                    self.assertTrue(later)
                    if later[0]["kind"] == "turn_end":
                        self.assertEqual(later[0]["turn"], e["turn"])
                    checked["power_knock_out"] += 1
                if e["kind"] == "return_in_play_to_hand" and "power" in e:
                    window = log[i + 1:i + 4]
                    self.assertFalse([x for x in window if x["kind"] in ("knock_out", "take_prize")])
                    checked["cowardice"] += 1
        self.assertTrue(checked["power_knock_out"] and checked["cowardice"], checked)

    def test_power_use_never_ends_the_turn(self):
        """特殊能力の宣言のあと、同じ番にワザ・番の終わりが続く（特殊能力の宣言そのものが番を終えない。こんらんのコインを投げない）。"""
        for r in self.results:
            state = r["state"]
            log = state.log
            for i, e in enumerate(log):
                if e["kind"] == "pokemon_power":
                    nxt = log[i + 1] if i + 1 < len(log) else None
                    with self.subTest(decks=r["decks"], seed=r["seed"], turn=e["turn"]):
                        self.assertTrue(nxt is None or nxt["kind"] not in ("turn_end", "confusion_check"))
            self.assertTrue(state.phase in (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED))

    def test_the_log_audit_catches_broken_v042_logs(self):
        """ログの監査は、v0.42 の特殊能力・ワザのログを壊すと問題を報告する（監査が素通りしていない）: ヒーリングの結果を消す・数を変える、のろいの
        持ち主（owner）を消す、のろいのあとのきぜつの時点を変える、手札にもどすログを消す、ぶっしつこうかんのトラッシュ・そのあとの引く処理を消す、
        ぼうぎょかふんの結果を変える、エネループのもどすログを消す、山札からの進化を手札からの進化にする、ライフダウンの数を変える、かおりのわなの入れ替えの
        特殊能力を消す。"""
        def tampered(state, pred, change):
            log = list(state.log)
            for i, e in enumerate(log):
                if pred(e):
                    new = change(dict(e))
                    if new is None:
                        del log[i]
                    else:
                        log[i] = MappingProxyType(new)
                    broken = copy.deepcopy(state)
                    broken.log = tuple(log)
                    return broken
            return None

        cases = {
            "drop power_heal": (lambda e: e["kind"] == "power_heal" and "user_pokemon_id" in e, lambda e: None),
            "power_heal more": (lambda e: e["kind"] == "power_heal" and "user_pokemon_id" in e,
                                lambda e: {**e, "counters": 2, "amount": 20, "total_damage": e["total_damage"] - 10}),
            "curse owner": (lambda e: e["kind"] == "move_damage_counter" and "owner" in e, lambda e: {k: v for k, v in e.items() if k != "owner"}),
            "knock out timing": (lambda e: e["kind"] == "knock_out" and e.get("timing") == "power", lambda e: {**e, "timing": "attack"}),
            "drop return_in_play_to_hand": (lambda e: e["kind"] == "return_in_play_to_hand", lambda e: None),
            "drop discard_from_hand": (lambda e: e["kind"] == "discard_from_hand" and "power" in e, lambda e: None),
            "drop draw after the discard": None,
            "pollen result": (lambda e: e["kind"] == "power_confusion", lambda e: {**e, "confused": not e["confused"]}),
            "drop return_energy_to_hand": (lambda e: e["kind"] == "return_energy_to_hand", lambda e: None),
            "evolve from the hand": (lambda e: e["kind"] == "evolve" and e.get("source_zone") == "deck",
                                     lambda e: {k: v for k, v in e.items() if k != "source_zone"}),
            "life down count": (lambda e: e["kind"] == "place_damage_counters",
                                lambda e: {**e, "total_damage": e["total_damage"] - 10, "amount": e["amount"] - 10, "counters": e["counters"] - 1}),
            "sweet trap switch": (lambda e: e["kind"] == "switch" and "@power" in str(e.get("effect")) and e["player"] != e.get("turn_player", -1)
                                  and e["effect"].startswith(ERIKAS_VICTREEBEL), lambda e: {**e, "effect": None}),
        }
        for name, case in cases.items():
            with self.subTest(case=name):
                found = None
                for r in self.results:
                    state = r["state"]
                    if case is None:
                        index = next((i for i, e in enumerate(state.log) if e["kind"] == "discard_from_hand" and "power" in e), None)
                        if index is not None:
                            found = copy.deepcopy(state)
                            found.log = state.log[:index + 1] + state.log[index + 2:]
                    else:
                        found = tampered(state, *case)
                    if found is not None:
                        break
                self.assertIsNotNone(found, name)
                self.assertTrue(log_problems(found), name)
        for r in self.results:
            self.assertEqual(log_problems(r["state"]), [])


class ToolTest(unittest.TestCase):
    def test_verification_decks(self):
        """検証用デッキは 60 枚で、どのカードも対戦に使える。15 枚はどれも入る。公開の固定のデッキ・前の版の検証用デッキには入れていない。"""
        pool = load_card_pool()
        decks = {label: games.deck_cards(label) for label in LABELS}
        for label, deck in decks.items():
            with self.subTest(deck=label):
                self.assertEqual(len(deck), 60)
                self.assertTrue(all(pool.is_playable(c) for c in deck))
                names = Counter(pool.get(c).name_ja for c in deck if not pool.get(c).is_basic_energy)
                self.assertLessEqual(max(names.values()), 4)
        self.assertTrue(set(V0_42_POKEMON) <= set().union(*decks.values()))
        self.assertFalse(any(set(V0_42_POKEMON) & set(d.cards()) for d in PRESET_DECKS.values()))
        for label in sorted(earlier_batch_decks("v0.42")):
            self.assertFalse(set(V0_42_POKEMON) & set(games.deck_cards(label)), label)


if __name__ == "__main__":
    unittest.main()

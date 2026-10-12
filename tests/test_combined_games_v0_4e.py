"""v0.4a〜v0.4d のすべての対応カードを混ぜた 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで（v0.4e の総合監査。
docs/integration-audit-v0.4e.md 6 章・8 章・9 章）。

パラス → パラセクト・パウワウ → ジュゴン・キャタピー → トランセル → バタフリー・ビードル → コクーン → スピアー・ドードー・ロコン・
ピカチュウ・ガーディと、プラスパワー・ディフェンダー・ポケモンいれかえ・マサキ・きずぐすりを 2 つのデッキに分けて入れる。
手順は tests/test_butterfree_games_v0_4d.py の ``policy_command``（v0.4a〜v0.4d の手順を重ねたもの。対戦相手の AI ではない）。

確かめること:

- どの状態も不変条件を満たす（``apply_command`` が確かめる）。
- 対戦のあとのログだけから組み立て直した場のポケモンのダメージ・エネルギー・トラッシュ・サイドが状態と同じ（ログと状態の整合。
  tests/log_audit.py。ログは記録で、状態の正本ではない）。番の進行・ワザ 1 回の要素の数・サイドの重複・持続する効果の付与と
  解除の対応も確かめる。
- 書き出し: 対戦の途中のどの状態でも、形式 1〜8 は表せる状態だけを書き出し（表せなければ ValueError）、書き出したものは形式 8 から
  後の項目を除いたものと同じ（黙って情報を落とさない）。形式 9 はない。
- 組み合わせの表（docs/interaction-matrix-v0.4e.md）の「自然な対戦で起こる」マスが、実際に起こる回数を数えて固定する。

根拠のページは、それぞれの規定のテスト（tests/test_combined_state_v0_4e.py ほか）に書いた。
"""

import unittest
from collections import Counter

from kyuura_engine import (
    EvolvePokemon, IllegalActionError, Phase, UnsupportedError, UseAttack, apply_command, check_invariants, new_game,
)
from kyuura_engine.decisions import FORCED_SWITCH
from kyuura_engine.rng import copy_rng, rng_fingerprint

from tests.helpers import (
    BEEDRILL, BILL, BUTTERFREE, CATERPIE, DEFENDER, DEWGONG, DODUO, FIRE, GRASS, GROWLITHE, KAKUNA, LIGHTNING, METAPOD, PARAS,
    PARASECT, PIKACHU, PLUSPOWER, POTION, SEEL, SWITCH, VULPIX, WATER, WEEDLE, coin_events, expand_decklist,
)
from tests.log_audit import TERMINAL, log_problems, serialization_problems
from tests.test_butterfree_games_v0_4d import policy_command
from tests.test_evolution_games_v0_4a import EVOLUTION_REJECTIONS
from tests.test_harden_games_v0_4b import REJECTIONS
from tests.test_stage2_games_v0_4c import STAGE2_REJECTIONS

ALL_CARDS_DECK_A = expand_decklist({
    CATERPIE: 4, METAPOD: 3, BUTTERFREE: 2, SEEL: 3, DEWGONG: 2, DODUO: 2, VULPIX: 2, PLUSPOWER: 2, DEFENDER: 2, SWITCH: 2,
    BILL: 3, POTION: 2, GRASS: 17, WATER: 10, FIRE: 4,
})
ALL_CARDS_DECK_B = expand_decklist({
    WEEDLE: 4, KAKUNA: 3, BEEDRILL: 2, PARAS: 3, PARASECT: 2, PIKACHU: 2, GROWLITHE: 2, PLUSPOWER: 2, DEFENDER: 2, SWITCH: 2,
    BILL: 2, POTION: 2, GRASS: 20, LIGHTNING: 6, FIRE: 6,
})
SEEDS = tuple(range(24)) + tuple(range(500, 524))
# 書き出しの監査は、すべての状態で行う局（重いので一部だけ）。ほかの局は対戦の終わりの状態だけ
SERIALIZE_EVERY_STEP = (0, 1, 2, 500, 501, 502)


def decks(seed):
    return (ALL_CARDS_DECK_A, ALL_CARDS_DECK_B) if seed % 2 == 0 else (ALL_CARDS_DECK_B, ALL_CARDS_DECK_A)


def play_game(seed, *, max_steps=8000, audit_each_step=False):
    """終わるまで進める（cure は seed で切り替える）。受け付けた操作の列と、拒否された操作・書き出しの問題などの観測を返す。"""
    cure = seed % 3 != 0
    state = new_game(*decks(seed), seed)
    commands, observed, tried = [], Counter(), {}
    for _ in range(max_steps):
        if audit_each_step:
            problems = serialization_problems(state)
            if problems:
                raise AssertionError((seed, len(commands), problems))
            observed["serialization_audited_states"] += 1
        if state.phase in TERMINAL:
            return state, commands, observed
        while True:
            turn_tried = tried.setdefault(state.turn_number, set())
            command = policy_command(state, janken_winner=seed % 2, cure=cure, tried=turn_tried)
            try:
                new = apply_command(state, command)
                break
            except (IllegalActionError, UnsupportedError) as error:
                if isinstance(command, EvolvePokemon):
                    stage2 = state.card_def(command.card).is_stage2_pokemon
                    if error.code in (STAGE2_REJECTIONS if stage2 else EVOLUTION_REJECTIONS):
                        observed[f"rejected_{'evolve2' if stage2 else 'evolve'}_{error.code}"] += 1
                        turn_tried.add("evolve2" if stage2 else "evolve")
                        continue
                if error.code not in REJECTIONS:
                    raise
                kind = "attack" if isinstance(command, UseAttack) else "retreat"
                observed[f"rejected_{kind}_{error.code}"] += 1
                turn_tried.add(kind)
        if state.phase is Phase.DECISION and state.decision.kind == FORCED_SWITCH:
            observed["forced_switch_chosen_by_opponent"] += 1
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def count_combinations(state):
    """組み合わせの表のマスを、ログから数える（自然な対戦で起こった回数）。"""
    counted = Counter()
    log = [dict(e) for e in state.log]
    last_evolve = {}
    defenders_on = {}  # 場のポケモンの番号 → ついているディフェンダーのカード（ログの attach_trainer から）
    for index, e in enumerate(log):
        kind = e["kind"]
        if kind == "evolve":
            counted[f"evolve_{state.cards[e['from_card']].card_id}_to_{e['to_card_id']}"] += 1
            last_evolve[e["pokemon_id"]] = index
        elif kind == "special_conditions_removed":
            counted[f"conditions_removed_by_{e['reason']}"] += 1
            if e["reason"] == "evolve":
                counted[f"evolve_cleared_{'+'.join(e['conditions'])}"] += 1
        elif kind == "persistent_effect_removed":
            counted[f"persistent_removed_by_{e['reason']}"] += 1
        elif kind == "retreat_failure_cleared":
            counted["evolve_cleared_retreat_failure"] += 1
        elif kind == "attach_trainer" and state.cards[e["card"]].card_id == DEFENDER:
            defenders_on.setdefault(e["pokemon_id"], set()).add(e["card"])
        elif kind == "discard_attached_trainer":
            for cards in defenders_on.values():
                cards.discard(e["card"])
        elif kind == "forced_switch":
            counted["forced_switch"] += 1
            if defenders_on.get(e["old_active_pokemon_id"]):
                counted["forced_switch_with_defender"] += 1
            if e["old_active_pokemon_id"] in last_evolve:
                counted["forced_switch_of_evolved"] += 1
        elif kind == "forced_switch_skipped":
            counted[f"forced_switch_skipped_{e['reason']}"] += 1
        elif kind == "knock_out":
            stack = e.get("evolution_stack", ())
            counted[f"knock_out_{len(stack) + 1}_cards"] += 1
            if e.get("discarded_trainers"):
                counted["knock_out_with_trainers"] += 1
            if e.get("timing"):
                counted["knock_out_pokemon_check"] += 1
            if e.get("simultaneous"):
                counted["knock_out_simultaneous"] += 1
        elif kind == "drain_heal":
            counted["drain_heal" if e["counters"] else "drain_heal_zero"] += 1
        elif kind in ("damage_prevented", "retreat_failed", "switch", "retreat", "take_prize", "confusion_damage", "sleep_check"):
            counted[kind] += 1
        elif kind == "damage" and e.get("target") == "self":
            counted["self_damage"] += 1
        elif kind == "special_condition":
            counted[f"applied_{e['condition']}"] += 1
    counted = Counter({k: v for k, v in counted.items() if v})
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    return counted


class CombinedGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_game(seed, audit_each_step=seed in SERIALIZE_EVERY_STEP) for seed in SEEDS}

    def test_games_end_and_states_are_consistent(self):
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_serialization_was_audited_at_every_step(self):
        for seed in SERIALIZE_EVERY_STEP:
            _, commands, observed = self.games[seed]
            self.assertEqual(observed["serialization_audited_states"], len(commands) + 1)

    def test_only_coins_use_randomness_after_setup(self):
        for seed, (state, _, _) in self.games.items():
            expected = copy_rng(new_game(*decks(seed), seed).rng)
            for event in coin_events(state):
                self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
            self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected), seed)

    def test_replay_gives_the_same_state(self):
        from kyuura_engine import state_to_dict

        for seed in (0, 7, 505):
            state, commands, _ = self.games[seed]
            replayed = new_game(*decks(seed), seed)
            for command in commands:
                replayed = apply_command(replayed, command)
            self.assertEqual(state_to_dict(replayed, format_version=8), state_to_dict(state, format_version=8))

    def test_counts(self):
        """組み合わせの表の「自然な対戦で起こる」マスが実際に起こる（docs/interaction-matrix-v0.4e.md 3 章）。"""
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(count_combinations(state))
            counted.update({k: v for k, v in observed.items() if k != "serialization_audited_states"})
        for key in ("forced_switch", "forced_switch_skipped_knocked_out", "drain_heal", "damage_prevented",
                    "conditions_removed_by_evolve", "conditions_removed_by_forced_switch", "conditions_removed_by_retreat",
                    "conditions_removed_by_switch", "knock_out_3_cards", "knock_out_2_cards", "knock_out_with_trainers",
                    "knock_out_pokemon_check", "persistent_removed_by_expired", "evolve_PMCG1-029_to_PMCG1-030",
                    "evolve_PMCG2-003_to_PMCG2-010", "evolve_PMCG1-003_to_PMCG2-007", "evolve_PMCG1-009_to_PMCG1-012", "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertEqual(dict(counted), EXPECTED_COUNTS)


class LogAuditSelfTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py）が、壊したログ・壊した書き出しを見つけること（監査が何でも通すのではないことの確認）。"""

    @classmethod
    def setUpClass(cls):
        cls.state = next(state for seed in SEEDS[:6] for state, _, _ in [play_game(seed)]
                         if any(e["kind"] == "forced_switch" for e in state.log)
                         and any(e["kind"] == "persistent_effect_removed" for e in state.log))

    def broken(self, change):
        state = self.state.clone()
        log = [dict(e) for e in state.log]
        change(log)
        state.log = tuple(log)
        return log_problems(state)

    def index(self, kind, log=None):
        return next(i for i, e in enumerate(log or self.state.log) if e["kind"] == kind)

    def test_original_passes(self):
        self.assertEqual(log_problems(self.state), [])

    def test_detects_broken_logs(self):
        def drop(kind):
            return lambda log: log.pop(self.index(kind, log))

        def duplicate(kind):
            return lambda log: log.insert(self.index(kind, log), dict(log[self.index(kind, log)]))

        def amount(log):
            log[self.index("damage", log)]["amount"] += 10

        def drop_damage(log):
            log.pop(next(i for i, e in enumerate(log) if e["kind"] == "damage" and e["amount"] > 0))

        for name, change in (
            ("ダメージのログを消す", drop_damage),
            ("ダメージの量を変える", amount),
            ("サイドを 2 回取る", duplicate("take_prize")),
            ("番の終わりを 2 回", duplicate("turn_end")),
            ("ポケモンチェックを飛ばす", drop("pokemon_check")),
            ("ふきとばしを 2 回", duplicate("forced_switch")),
            ("持続する効果を 2 回消す", duplicate("persistent_effect_removed")),
            ("エネルギーをつけたログを消す", drop("attach_energy")),
            ("トレーナーのトラッシュを消す", drop("discard_trainer")),
            ("きぜつのログを消す", drop("knock_out")),
            ("番の始まりを消す", drop("turn_start")),
        ):
            with self.subTest(change=name):
                try:
                    problems = self.broken(change)
                except (KeyError, ValueError, StopIteration):
                    problems = ["組み立て直せない"]
                self.assertTrue(problems)

    def test_detects_silently_dropped_serialization(self):
        """形式 7 の書き出しが持続する効果を黙って落としたら見つかる（書き出しの関数を差し替えて確かめる）。"""
        import kyuura_engine.serialize as serialize
        from tests import log_audit

        state = next(state for seed in SEEDS[:12] for state, _, _ in [play_game(seed)]
                     if any(pokemon.evolution_stack for p in state.players for pokemon in p.in_play()))
        original = log_audit.state_to_dict

        def lenient(target, format_version=1):
            if format_version in (5, 6):
                return original(target, format_version=8) | {"format_version": format_version}
            return original(target, format_version=format_version)

        log_audit.state_to_dict = lenient
        try:
            self.assertTrue(serialization_problems(state))
        finally:
            log_audit.state_to_dict = original
        self.assertIs(serialize.state_to_dict, original)


class StressSmokeTest(unittest.TestCase):
    """大規模なストレス実行（tools/stress_engine.py。段階 C。ふだんは走らせない）と同じ処理を、小さく 1 回だけ走らせる（段階 B）。
    でたらめな操作（不正な操作を 25%）を混ぜても、内部の誤り・拒否で変わる状態・ログと書き出しの問題がない。"""

    def test_small_stress_run(self):
        import importlib.util
        import pathlib

        path = pathlib.Path(__file__).resolve().parent.parent / "tools" / "stress_engine.py"
        spec = importlib.util.spec_from_file_location("stress_engine", path)
        stress = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stress)
        result = stress.run(stress.driver.SCENARIOS, range(1), steps=150, illegal_rate=0.25, serialize_every=10)
        self.assertEqual(result["failures"], [])
        counts = result["counts"]
        self.assertEqual(counts["games"], len(stress.driver.SCENARIOS))
        for key in ("accepted", "rejected_illegal", "serialization_audits"):
            self.assertGreater(counts.get(key, 0), 0, (key, counts))
        self.assertEqual(counts.get("internal_error", 0) + counts.get("internal_state_integrity", 0), 0)


# 自然な対戦（SEEDS の 48 局）で数えた回数（v0.4e）。手順・デッキ・乱数の使い方が変わると変わる。止まった 3 局は対戦準備の
# 切り直しの補償（v0.1 からの未解決）。進化した対戦ポケモンが特殊状態を持ったまま進化した 10 回（ねむり 7・どく 2・マヒ 1）・
# ディフェンダーのついた相手をふきとばした 4 回・持続する効果をふきとばしで消した 6 回・ついていたトレーナーごときぜつした 6 回・
# 同時のきぜつ 8 回など。こんらんで「にげる」に失敗した記録を進化で消す場面・「かたまる」の番の終わりのどくのきぜつ（効果は
# きぜつで消える）は、この 48 局では起こらなかった（tests/test_combined_state_v0_4e.py で盤面を直接作って確かめた）
EXPECTED_COUNTS = {
    "applied_confusion": 21, "applied_paralysis": 154, "applied_poison": 114, "applied_sleep": 296,
    "conditions_removed_by_evolve": 10, "conditions_removed_by_forced_switch": 1, "conditions_removed_by_paralysis_end": 139,
    "conditions_removed_by_retreat": 63, "conditions_removed_by_sleep_coin": 255, "conditions_removed_by_switch": 33,
    "confusion_damage": 6, "damage_prevented": 30, "drain_heal": 33, "drain_heal_zero": 10, "evolve_PMCG1-002_to_PMCG1-003": 86,
    "evolve_PMCG1-003_to_PMCG2-007": 57, "evolve_PMCG1-004_to_PMCG1-009": 75, "evolve_PMCG1-009_to_PMCG1-012": 49,
    "evolve_PMCG1-029_to_PMCG1-030": 61, "evolve_PMCG2-003_to_PMCG2-010": 58, "evolve_cleared_paralysis": 1,
    "evolve_cleared_poison": 2, "evolve_cleared_sleep": 7, "forced_switch": 135, "forced_switch_chosen_by_opponent": 135,
    "forced_switch_of_evolved": 58, "forced_switch_skipped_knocked_out": 38, "forced_switch_skipped_no_bench": 9,
    "forced_switch_with_defender": 4, "halted_UNRESOLVED_MULLIGAN_COMPENSATION": 3, "knock_out_1_cards": 212,
    "knock_out_2_cards": 58, "knock_out_3_cards": 34, "knock_out_pokemon_check": 31, "knock_out_simultaneous": 8,
    "knock_out_with_trainers": 6, "persistent_removed_by_expired": 66, "persistent_removed_by_forced_switch": 6,
    "phase_game_over": 45, "phase_halted": 3, "rejected_attack_POKEMON_ASLEEP": 103, "rejected_attack_POKEMON_PARALYZED": 92,
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS": 1, "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE": 6,
    "rejected_evolve2_EVOLVED_THIS_TURN": 63, "rejected_evolve_FIRST_TURN_EVOLUTION": 31,
    "rejected_evolve_PLAYED_THIS_TURN": 94, "rejected_retreat_POKEMON_ASLEEP": 140, "rejected_retreat_POKEMON_PARALYZED": 144,
    "rejected_retreat_RETREAT_ALREADY_FAILED": 7, "retreat": 243, "retreat_failed": 8, "self_damage": 16, "sleep_check": 493,
    "switch": 126, "take_prize": 304,
}


if __name__ == "__main__":
    unittest.main()

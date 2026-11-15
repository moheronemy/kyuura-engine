"""到達目的の方策 reach 版 2（docs/verification-ai-reach-policy.md 14 章・15 章）。

- 人工の API の応答（JSON）: V2-a（P6 の対象 2 種・対象がないときの通常の経路）・V2-c（炎エネルギーの準備の有無が順位だけに出る）・V2-d（エネルギーとポケモンの依存する
  2 段・同じカードの複数の個体の参照による区別・参照が欠ける・一致しないときに推測しない）・保護の期限・情報境界・版 1 の同じ条件の選び方と乱数の消費
- バッチ: 方式 reach2-p6・reach2-u-r3a の設定の計画への固定・改変と不一致の拒否・TOOL_VERSION 7 の計画の再開の拒否・短い本物の 1 局で記録への伝播（到達を狙わない）
- fixture（構築盤面。new_game からの到達ではない）: 秘策の盤面で R2 → 置く → R1 → P6 のおもてにしてにげた受理、UR3A-RC でおもてにして特殊能力を使った受理、
  炎でないエネルギーの WRONG_ENERGY_TYPE の正常な拒否（入力はケースの選び手）、公開ログ・共通 judge との対応、局全体で 1 回の実送信と両方の主体の復帰
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.test_verification_ai_reach import END, P6, RETREAT, REVEAL, TRAINER, UR3A, _hosted, _scope, cand, drive, pair, pick, stage
from tools.verification_ai import batch as B
from tools.verification_ai import reach as RP
from tools.verification_ai.policies import RulePolicy

ROOT = Path(__file__).resolve().parents[1]
FD = RP.FACE_DOWN_REASON
SECRET, DIGLETT, ABRA, KADABRA = "PMCG5-093", "PMCG1-052", "PMCG1-043", "PMCG1-046"
ROCKET_CHARMANDER, FIRE, WATER, FIGHTING = "PMCG4-012", "PMCG1-098", "PMCG1-099", "PMCG1-102"
HITMONCHAN, RATTATA = "PMCG1-058", "PMCG1-060"
P6_V2 = B.MODES["reach2-p6"]["reach"]
UR_V2 = B.MODES["reach2-u-r3a"]["reach"]
P6_V1 = B.MODES["reach-p6"]["reach"]
UR_V1 = B.MODES["reach-u-r3a"]["reach"]


def mon(pid, card, card_id, energy=(), face_down=False, real=None):
    """観測の場のポケモン（本人の観測の形）。``energy`` は (カードの参照, card_id) の並び。うらは real だけを持ちうる（方策は読まない）。"""
    if face_down:
        return {"pokemon_id": pid, "face_down": True, "damage": 0, "energy": [{"card": c, "card_id": i} for c, i in energy],
                **({"real": real} if real else {})}
    return {"pokemon_id": pid, "card": card, "card_id": card_id, "energy": [{"card": c, "card_id": i} for c, i in energy]}


def view2(*, active, bench=(), hand=(), actor=0, current=0, turn=3, opponent=None, opponent_hand=None):
    me = {"active": active, "bench": list(bench), "hand": {"cards": [{"card": 100 + i, "card_id": c} for i, c in enumerate(hand)], "count": len(hand)}}
    other = {"active": opponent or {"pokemon_id": 50, "card": 50, "card_id": HITMONCHAN, "energy": []}, "bench": [],
             "hand": {"count": 3, **({"cards": opponent_hand} if opponent_hand is not None else {})}}
    players = [me, other] if actor == 0 else [other, me]
    return {"status": {"segment": 1}, "viewer": actor, "observation": {"current_player": current, "turn": turn, "phase": "main", "players": players}}


# UR3A-RC と同じ形の自分の場（バトル場: 闘エネルギー 2 枚のエビワラー、ベンチ: 炎・水エネルギーのコラッタ、うらのカード）
def rc_view(*, fire_on_rattata=True, fire_on_face_down=False, real=None, **kw):
    rattata_energy = ((4, FIRE), (5, WATER)) if fire_on_rattata else ((5, WATER),)
    return view2(active=mon(1, 0, HITMONCHAN, ((1, FIGHTING), (2, FIGHTING))),
                 bench=(mon(2, 3, RATTATA, rattata_energy), mon(4, None, None, ((9, FIRE),) if fire_on_face_down else (), face_down=True, real=real)), **kw)


SOURCE = {"stage": 1, "input": "choose_option", "role": "source", "meaning": "pokemon", "count": {"min": 1, "max": 1},
          "options": [{"id": "o1", "pokemon": 1, "card": 0, "zone": "active", "card_id": HITMONCHAN},
                      {"id": "o2", "pokemon": 2, "card": 3, "zone": "bench", "bench_index": 0, "card_id": RATTATA}]}
ENERGY = {"stage": 2, "input": "choose_option", "role": "energy", "meaning": "card", "count": {"min": 1, "max": 1}, "depends_on_stage": 1,
          "options": [{"id": "o3", "card": 1, "card_id": FIGHTING, "after": "o1"}, {"id": "o4", "card": 2, "card_id": FIGHTING, "after": "o1"},
                      {"id": "o5", "card": 4, "card_id": FIRE, "after": "o2"}, {"id": "o6", "card": 5, "card_id": WATER, "after": "o2"}]}


def r0_inputs(policy, v, source=SOURCE, energy=ENERGY, source_items=None, energy_items=None):
    """R0（U-R3a）を選んだあとの 2 段の選択（行動生成が渡す選べるものの番号の並びを ``*_items`` で与える）。"""
    chosen, reason = pick(policy, [END, UR3A], v)
    assert chosen is UR3A and ":R0:" in reason, reason
    s_items = source_items or [o["id"] for o in source["options"]]
    i, r1 = stage(policy, UR3A, source, "option", s_items, v)
    picked = next(o for o in source["options"] if o["id"] == s_items[i])
    e_items = energy_items or [o["id"] for o in energy["options"] if o.get("after") == picked["id"]]
    j, r2 = stage(policy, UR3A, energy, "option", e_items, v)
    return (s_items[i], r1), (e_items[j], r2)


class SettingsV2Test(unittest.TestCase):
    def test_modes_and_card_ids_match_the_card_definitions(self):
        from kyuura_engine.cards import load_card_pool
        from kyuura_engine.effects import DEFAULT_EFFECTS

        self.assertEqual((P6_V2["version"], P6_V2["goal"], P6_V2["place_cards"], P6_V2["target_input_cards"], P6_V2["move_to_active"]),
                         (2, "p6", [DIGLETT, ABRA], [], True))
        self.assertEqual((UR_V2["version"], UR_V2["goal"], UR_V2["place_cards"], UR_V2["target_input_cards"], UR_V2["move_to_active"]),
                         (2, "u_r3a", [ROCKET_CHARMANDER], [FIRE], False))
        for s in (P6_V2, UR_V2):
            self.assertEqual((s["protect_own_turns"], s["tries_per_game"], s["base"], s["place_trainers"]), (3, 1, "rules-v2", [SECRET]))
            self.assertEqual(RP.validate_settings(s), s)
        for mode in ("reach2-p6", "reach2-u-r3a"):
            self.assertEqual({k: v for k, v in B.MODES[mode].items() if k != "reach"},
                             {"policy": "reach", "profile": "boundary", "rules_version": 2, "repeat_threshold": 2})
        pool = load_card_pool().definitions
        for cid in (DIGLETT, ABRA):  # P6 の対象: にげる 0 のたねポケモン（設計 14 章）
            self.assertTrue(pool[cid].is_basic_pokemon and pool[cid].retreat_cost == 0, cid)
        self.assertTrue(pool[ROCKET_CHARMANDER].is_basic_pokemon)
        self.assertEqual(type(DEFAULT_EFFECTS.power_entry(ROCKET_CHARMANDER, 0).effect).__name__, "TakeEnergyToSelf")
        self.assertTrue(pool[FIRE].is_basic_energy)

    def test_version_1_modes_are_unchanged(self):
        self.assertEqual(B.MODES["reach-p6"]["reach"], {"goal": "p6", "version": 1, "place_trainers": [SECRET], "place_cards": [], "move_to_active": True,
                                                         "protect_own_turns": 3, "tries_per_game": 1, "base": "rules-v2"})
        self.assertEqual(B.MODES["reach-u-r3a"]["reach"], {"goal": "u_r3a", "version": 1, "place_trainers": [SECRET], "place_cards": ["PMCG1-049"],
                                                            "move_to_active": False, "protect_own_turns": 3, "tries_per_game": 1, "base": "rules-v2"})

    def test_bad_settings_are_refused_not_reinterpreted(self):
        bad = {
            "v2_without_target_input_cards": {k: v for k, v in UR_V2.items() if k != "target_input_cards"},
            "v1_with_target_input_cards": {**P6_V1, "target_input_cards": []},
            "version_3": {**UR_V2, "version": 3},
            "version_text": {**UR_V2, "version": "2"},
            "version_bool": {**UR_V2, "version": True},
            "p6_target_inputs": {**P6_V2, "target_input_cards": [FIRE]},
            "p6_no_place_cards": {**P6_V2, "place_cards": []},
            "duplicate_inputs": {**UR_V2, "target_input_cards": [FIRE, FIRE]},
            "not_list": {**UR_V2, "target_input_cards": FIRE},
            "empty_id": {**UR_V2, "target_input_cards": [""]},
            "unknown_key": {**UR_V2, "extra": 1},
            "u_r3a_move": {**UR_V2, "move_to_active": True},
            "tries_2": {**UR_V2, "tries_per_game": 2},
            "protect_0": {**P6_V2, "protect_own_turns": 0},
        }
        for name, s in bad.items():
            with self.subTest(name), self.assertRaises(RP.ReachSettingsError):
                RP.validate_settings(s)

    def test_policy_records_version_and_distribution(self):
        budget = RP.ReachBudget(1)
        v1 = RP.ReachPolicy("x", actor=0, settings=P6_V1, budget=budget)
        v2 = RP.ReachPolicy("x", actor=0, settings=UR_V2, budget=budget)
        self.assertEqual((v1.version, v1.distribution, v2.version, v2.distribution),
                         (1, RP.REACH_DISTRIBUTION, 2, RP.REACH_DISTRIBUTION_2))
        self.assertNotIn("version", v1.state())  # 版 1 の状態の記録の形は変えない
        self.assertEqual({k: v2.state()[k] for k in ("version", "input_ready", "input_cards_seen")}, {"version": 2, "input_ready": False, "input_cards_seen": 0})


# ---------------------------------------------------------------- P6（V2-a）


def secret_stage(cards):
    return {"stage": 1, "decision_kind": "secret_plan_card", "options": [{"id": f"o{i}", "card": 200 + i, "card_id": c} for i, c in enumerate(cards, 1)]}


class P6PreferenceTest(unittest.TestCase):
    def test_secret_plan_is_preferred_only_with_a_target_in_hand(self):
        for target in (DIGLETT, ABRA):
            with self.subTest(target):
                ps, _ = pair(P6_V2)
                v = view2(active=mon(1, 0, HITMONCHAN), hand=(SECRET, target, FIGHTING))
                chosen, reason = pick(ps[0], [END, cand("c3", "attach_energy"), TRAINER], v)
                self.assertEqual((chosen["id"], reason.split(":")[:3]), ("c6", ["reach", "p6", "R2"]))

    def test_without_a_target_the_normal_path_is_used(self):
        """対象（ディグダ・ケーシィ）が手札になければ R2 を当てず、rules-v2 の順位（同じ乱数の消費）。版 1（place_cards が空）は R2 を当てる。"""
        hand = (SECRET, KADABRA, FIGHTING)
        items = [END, cand("c3", "attach_energy"), TRAINER]
        ps, _ = pair(P6_V2, seed="same")
        rules = RulePolicy("same:0", version=2)
        v = view2(active=mon(1, 0, HITMONCHAN), hand=hand)
        chosen, reason = pick(ps[0], items, v)
        rules.begin_episode()
        expect = rules.choose("candidate", items, {"view": v})
        self.assertEqual((items.index(chosen), reason), (expect[0], "reach:base:" + expect[1]))
        self.assertEqual(ps[0].draws, rules.draws)
        p1, _ = pair(P6_V1, seed="same")
        self.assertIn(":R2:", pick(p1[0], items, v)[1])

    def test_placement_prefers_the_two_targets(self):
        ps, _ = pair(P6_V2)
        v = view2(active=mon(1, 0, HITMONCHAN), hand=(KADABRA, DIGLETT, FIGHTING, ABRA))
        pick(ps[0], [END], v)
        st = secret_stage([KADABRA, DIGLETT, FIGHTING, ABRA])
        dec = cand("c1", "answer_decision")
        self.assertEqual(stage(ps[0], dec, st, "count", [0, 1], v)[0], 1)
        ids = ["o1", "o2", "o3", "o4"]
        chosen = {st["options"][stage(ps[0], dec, st, "option", ids, v)[0]]["card_id"] for _ in range(20)}
        self.assertEqual(chosen, {DIGLETT, ABRA})
        st2 = secret_stage([KADABRA, FIGHTING])  # 対象がなければ 0 枚（置かない）を選べる
        self.assertEqual(stage(ps[0], dec, st2, "count", [0, 1], v)[0], 0)

    def test_p6_target_and_its_inputs_are_unchanged(self):
        """P6 の目標の操作は R0、入力（トラッシュするエネルギー）は版 1 と同じ均等（費用を方策で計算しない）。"""
        ps, _ = pair(P6_V2)
        v = view2(active=mon(1, None, None, face_down=True), hand=())
        v["observation"]["players"][0]["active"] = {"pokemon_id": 1, "face_down": True, "energy": []}
        chosen, reason = pick(ps[0], [END, REVEAL, P6], v)
        self.assertEqual((chosen["id"], reason.split(":")[:3]), ("c9", ["reach", "p6", "R0"]))
        st = {"stage": 2, "role": "discard", "options": [{"id": "o1", "card": 1, "card_id": FIRE}, {"id": "o2", "card": 2, "card_id": FIGHTING}]}
        self.assertTrue(stage(ps[0], P6, st, "option", ["o1", "o2"], v)[1].startswith("reach:stage:uniform"))


# ---------------------------------------------------------------- U-R3a（V2-c・V2-d）


class UR3APreferenceTest(unittest.TestCase):
    def test_readiness_changes_only_the_rank(self):
        """炎エネルギーがおもての自分のポケモンについていなければ、目標の候補は end_turn より後ろ（除かない。それしかなければ選ぶ）。ついていれば R0。"""
        attach = cand("c3", "attach_energy")
        for kw, ready in (({"fire_on_rattata": True}, True), ({"fire_on_rattata": False}, False),
                          ({"fire_on_rattata": False, "fire_on_face_down": True}, False)):  # うらのポケモンについているものは数えない
            with self.subTest(kw=kw):
                ps, _ = pair(UR_V2)
                v = rc_view(**kw)
                chosen, reason = pick(ps[0], [END, attach, UR3A], v)
                self.assertEqual(ps[0].input_ready(), ready)
                if ready:
                    self.assertEqual((chosen["id"], reason.split(":")[:3]), ("c8", ["reach", "u_r3a", "R0"]))
                else:
                    self.assertEqual(chosen["id"], "c3")
                    self.assertEqual(pick(ps[0], [UR3A, END], v)[0]["id"], "c1")  # end_turn より後ろ
                    only, why = pick(ps[0], [UR3A], v)
                    self.assertEqual(only["id"], "c8")  # 候補を消さない
                    self.assertIn("priority7", why)

    def test_hold_without_protection_ranks_behind_end_turn(self):
        """保護の期間でないとき（うらのカードを見ていない番）も、準備のない目標の候補は end_turn より後ろ（reach:hold）。"""
        ps, _ = pair(UR_V2)
        v = rc_view(fire_on_rattata=False, current=1)  # 相手の番（保護の期間を始めない）
        chosen, reason = pick(ps[0], [UR3A, END], v)
        self.assertEqual((chosen["id"], reason.split(":")[:2]), ("c1", ["reach", "hold"]))

    def test_two_dependent_stages_pick_the_fire_and_its_host(self):
        for seed in range(8):
            with self.subTest(seed=seed):
                ps, _ = pair(UR_V2, seed=f"s{seed}")
                (src, r1), (eng, r2) = r0_inputs(ps[0], rc_view())
                self.assertEqual((src, eng), ("o2", "o5"))
                self.assertIn("R0:input_host", r1)
                self.assertIn("R0:input_card", r2)

    def test_same_card_individuals_are_told_apart_by_reference(self):
        """同じカード（コラッタ 2 匹）のうち炎エネルギーがついた個体だけ。同じ炎エネルギー 2 枚は、前の段で選んだポケモンについているものだけ。"""
        v = view2(active=mon(1, 0, HITMONCHAN, ((1, FIGHTING),)),
                  bench=(mon(2, 3, RATTATA, ((5, WATER),)), mon(3, 8, RATTATA, ((9, FIRE),)), mon(6, 11, RATTATA, ((12, FIRE),))))
        source = {"stage": 1, "meaning": "pokemon", "options": [{"id": "o1", "pokemon": 2, "card": 3, "card_id": RATTATA},
                                                                {"id": "o2", "pokemon": 3, "card": 8, "card_id": RATTATA},
                                                                {"id": "o3", "pokemon": 1, "card": 0, "card_id": HITMONCHAN}]}
        energy = {"stage": 2, "meaning": "card", "options": [{"id": "o4", "card": 9, "card_id": FIRE}, {"id": "o5", "card": 12, "card_id": FIRE},
                                                             {"id": "o6", "card": 5, "card_id": WATER}]}
        for seed in range(8):
            ps, _ = pair(UR_V2, seed=f"d{seed}")
            (src, _r1), (eng, _r2) = r0_inputs(ps[0], v, source, energy, source_items=["o1", "o2", "o3"], energy_items=["o4", "o5", "o6"])
            self.assertEqual((src, eng), ("o2", "o4"), seed)  # o5 は別のコラッタ（6）の炎: 選んだポケモンについていない

    def test_missing_or_mismatched_references_are_not_guessed(self):
        """選べるものの参照が欠ける・観測と一致しない・観測の参照があいまいなら優先せず均等（既存の通常の入力生成）。"""
        cases = {
            "option_without_pokemon": ({**SOURCE, "options": [{"id": "o1", "card": 0, "card_id": HITMONCHAN}, {"id": "o2", "card": 3, "card_id": RATTATA}]},
                                       rc_view()),
            "card_mismatch": ({**SOURCE, "options": [SOURCE["options"][0], {**SOURCE["options"][1], "card": 30}]}, rc_view()),
            "card_id_mismatch": ({**SOURCE, "options": [SOURCE["options"][0], {**SOURCE["options"][1], "card_id": "PMCG1-061"}]}, rc_view()),
        }
        for name, (src, v) in cases.items():
            with self.subTest(name):
                ps, _ = pair(UR_V2)
                pick(ps[0], [END, UR3A], v)
                _i, reason = stage(ps[0], UR3A, src, "option", ["o1", "o2"], v)
                self.assertTrue(":R0:input_" in reason and ":none:uniform" in reason, reason)  # ポケモンの段と分からなくても優先しない
        # カードの段: 観測にない参照・card_id の違う参照は優先しない
        ps, _ = pair(UR_V2)
        v = rc_view()
        pick(ps[0], [END, UR3A], v)
        stage(ps[0], UR3A, SOURCE, "option", ["o1", "o2"], v)
        bad_energy = {**ENERGY, "options": [{"id": "o5", "card": 40, "card_id": FIRE, "after": "o2"}, {"id": "o6", "card": 4, "card_id": WATER, "after": "o2"}]}
        self.assertIn("R0:input_card:none:uniform", stage(ps[0], UR3A, bad_energy, "option", ["o5", "o6"], v)[1])
        # 観測の参照があいまい（同じエネルギーの参照が 2 つ）・欠けるなら準備として数えない
        dup = view2(active=mon(1, 0, HITMONCHAN, ((4, FIRE),)), bench=(mon(2, 3, RATTATA, ((4, FIRE),)),))
        noref = view2(active=mon(1, 0, HITMONCHAN), bench=({"pokemon_id": 2, "card_id": RATTATA, "energy": [{"card": 4, "card_id": FIRE}]},))
        noenergyref = view2(active=mon(1, 0, HITMONCHAN), bench=({"pokemon_id": 2, "card": 3, "card_id": RATTATA, "energy": [{"card_id": FIRE}]},))
        for name, v in (("duplicate", dup), ("pokemon_without_card", noref), ("energy_without_card", noenergyref)):
            with self.subTest(name):
                ps, _ = pair(UR_V2)
                self.assertNotIn(":R0:", pick(ps[0], [END, UR3A], v)[1])
                self.assertFalse(ps[0].input_ready())

    def test_a_host_less_pick_does_not_prefer_later_cards(self):
        """前の段で準備のないポケモンを選んだ（均等の結果）なら、あとの段のカードも優先しない（上流の選択を保つ）。"""
        ps, _ = pair(UR_V2)
        v = rc_view()
        pick(ps[0], [END, UR3A], v)
        src = {**SOURCE, "options": [SOURCE["options"][0]]}  # エビワラーしか渡されない
        stage(ps[0], UR3A, src, "option", ["o1"], v)
        energy = {**ENERGY, "options": [{"id": "o3", "card": 4, "card_id": FIRE, "after": "o1"}, {"id": "o4", "card": 2, "card_id": FIGHTING, "after": "o1"}]}
        self.assertIn("R0:input_card:none", stage(ps[0], UR3A, energy, "option", ["o3", "o4"], v)[1])

    def test_options_are_never_removed(self):
        """選好は位置を選ぶだけ: 返す位置は常に渡された並びの中。準備がなくても目標の操作の入力の段は均等で、どの選べるものも選ばれうる。"""
        ps, _ = pair(UR_V2)
        v = rc_view(fire_on_rattata=False)
        ps[0].scope_profile(v)
        seen = set()
        for _ in range(30):
            ps[0].step = ("R0", "c8")
            i, _r = stage(ps[0], UR3A, SOURCE, "option", ["o1", "o2"], v)
            seen.add(i)
        self.assertEqual(seen, {0, 1})


class ProtectionAndBudgetTest(unittest.TestCase):
    def test_protection_counts_own_turns_and_does_not_restart(self):
        ps, _ = pair(P6_V2)
        p = ps[0]
        fd = lambda turn: view2(active=mon(1, 0, HITMONCHAN), bench=(mon(4, None, None, face_down=True),), turn=turn)  # noqa: E731
        gone = lambda turn: view2(active=mon(1, 0, HITMONCHAN), turn=turn)  # noqa: E731
        p.scope_profile(fd(3))
        self.assertEqual((p.protect_turns, p.active()), (1, True))
        p.scope_profile(fd(3))
        self.assertEqual(p.protect_turns, 1)  # 同じ番では増えない
        p.scope_profile(gone(5))  # うらのカードが消えても数え直さない
        self.assertEqual(p.protect_turns, 2)
        p.scope_profile(fd(7))
        self.assertEqual((p.protect_turns, p.active()), (3, True))
        self.assertEqual(p.scope_profile(fd(9)), "deep")
        self.assertTrue(p.expired and not p.active())
        self.assertTrue(ps[1].active())  # 期限は主体ごと

    def test_one_submit_per_game_returns_both(self):
        ps, budget = pair(UR_V2)
        v = rc_view()
        pick(ps[0], [END, UR3A], v)
        ps[0].notify_submit(UR3A, "k")
        self.assertEqual((budget.used, ps[0].active(), ps[1].active()), (1, False, False))
        self.assertEqual((ps[0].scope_profile(v), ps[1].scope_profile(v)), ("deep", "deep"))
        ps[1].notify_submit(UR3A, "k")
        self.assertEqual(budget.used, 1)
        chosen, reason = pick(ps[0], [END, UR3A], v)
        self.assertTrue(reason.startswith("reach:off:rule2:"))


class InformationV2Test(unittest.TestCase):
    def test_twins_differing_in_secrets_choose_the_same(self):
        """本人のうらのカードの real・相手の手札・相手の場の中身だけが違う双子で、選び方と乱数の消費が同じ。"""
        seqs = []
        for real, opp_hand, opp in (({"card_id": ROCKET_CHARMANDER}, [{"card_id": FIRE}], mon(50, 50, HITMONCHAN, ((60, FIRE),))),
                                    ({"card_id": "PMCG1-011"}, [{"card_id": SECRET}], mon(50, 51, RATTATA, ((61, WATER),)))):
            ps, _ = pair(UR_V2, seed="twin")
            out = []
            for kw in ({"fire_on_rattata": False}, {"fire_on_rattata": True}):
                v = rc_view(real=real, opponent_hand=opp_hand, opponent=opp, **kw)
                out.append(pick(ps[0], [END, cand("c3", "attach_energy"), UR3A, REVEAL], v))
                out.append(stage(ps[0], UR3A, SOURCE, "option", ["o1", "o2"], v))
            out.append(ps[0].draws)
            seqs.append(out)
        self.assertEqual(seqs[0], seqs[1])

    def test_policy_does_not_read_real_or_import_the_engine(self):
        tree = ast.parse((ROOT / "tools" / "verification_ai" / "reach.py").read_text(encoding="utf-8"))
        mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)] + [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        self.assertFalse([m for m in mods if "kyuura_engine" in m])
        docstrings = {id(n.body[0].value) for n in ast.walk(tree) if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
                      and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
        strings = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings}
        self.assertNotIn("real", strings)  # 観測の real を読まない（説明の文だけに出る）
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertFalse(attrs & {"check", "submit", "state_usable", "rng_state", "getstate"})  # check・submit の結果・エンジンの状態・乱数を読まない


# ---------------------------------------------------------------- 版 1 の同じ条件


def scripted_sequence(module, settings, seed="script"):
    """版 1 の代表的な同じ条件: 候補・段の選択・送る前の評価・submit の通知・復帰を並べ、選択・理由・乱数の消費・状態を返す（版 1 の前後の比べに使う）。"""
    budget = module.ReachBudget(1)
    ps = {a: module.ReachPolicy(f"{seed}:{a}", actor=a, settings=copy.deepcopy(settings), budget=budget) for a in (0, 1)}
    out = []
    plain = view2(active=mon(1, 0, HITMONCHAN, ((1, FIGHTING),)), bench=(mon(2, 3, RATTATA, ((4, FIRE),)),), hand=(SECRET, DIGLETT, "PMCG1-049"), turn=3)
    fd_bench = view2(active=mon(1, 0, HITMONCHAN, ((1, FIGHTING),)), bench=(mon(2, 3, RATTATA), mon(4, None, None, face_down=True)), turn=5)
    fd_active = view2(active={"pokemon_id": 4, "face_down": True, "energy": []}, bench=(mon(1, 0, HITMONCHAN),), turn=7)
    attach = cand("c3", "attach_energy")
    for v, items in ((plain, [END, attach, TRAINER]), (plain, [END, attach]), (fd_bench, [END, attach, RETREAT, REVEAL, UR3A]),
                     (fd_bench, [END, REVEAL]), (fd_active, [END, P6, REVEAL, UR3A]), (fd_active, [END, attach, UR3A, P6])):
        for actor in (0, 1):
            p = ps[actor]
            p.begin_episode()
            profile = p.scope_profile(v)
            i, r = p.choose("candidate", items, {"view": v})
            st = {"stage": 1, "role": "new_active", "options": [{"id": "o1", "pokemon": 1}, {"id": "o2", "pokemon": 4, "face_down": True}]}
            j, r2 = p.choose("option", ["o1", "o2"], {"view": v, "candidate": items[i], "stage": st})
            k, r3 = p.choose("count", [0, 1, 2], {"view": v, "candidate": items[i], "stage": {"stage": 2}})
            review = p.review(items[i], json.dumps({"input": []}), (1, 3))
            out.append([actor, profile, i, r, j, r2, k, r3, review])
    ps[0].notify_submit(UR3A if settings["goal"] == "u_r3a" else P6, "k")
    for actor in (0, 1):
        ps[actor].begin_episode()
        out.append([actor, ps[actor].scope_profile(fd_active), ps[actor].choose("candidate", [END, attach, P6, UR3A], {"view": fd_active})])
    out.append([ps[0].draws, ps[1].draws, ps[0].state(), ps[1].state()])
    return out


def digest(seq) -> str:
    return hashlib.sha256(json.dumps(seq, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


# 1106e18（版 2 を加える前の reach.py）で scripted_sequence を実行した値（証跡 vai-reach-r2-impl の compare_v1_old_new.py で、前の版と今の版の両方から同じ値を確かめた）
V1_SCRIPT_GOLDEN = {"reach-p6": "6f1bd13e9740441d8b8c192a444ca976f8629249a9c1b775a010b393223c1f8e",
                    "reach-u-r3a": "228d096f16e5730f9b8d4894b3e04031a19d0835d44673f1605210b24537b249"}


class Version1UnchangedTest(unittest.TestCase):
    def test_version_1_choices_draws_and_return_are_unchanged(self):
        for mode in ("reach-p6", "reach-u-r3a"):
            with self.subTest(mode):
                self.assertEqual(digest(scripted_sequence(RP, B.MODES[mode]["reach"])), V1_SCRIPT_GOLDEN[mode])


# ---------------------------------------------------------------- バッチ


class PlanV2Test(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vai-reach2-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.a = B.EngineAdapter("test")

    def plan(self, name, modes=("reach2-p6", "reach2-u-r3a"), **kw):
        return B.make_plan(self.tmp, name, engine_commit="test", tool_commit="test", seeds=[12], modes=list(modes), deck0="hitmonchan-dewgong",
                           deck1="venusaur-parasect", adapter=self.a, game_limits={"operations": 40, "seconds": 60}, **kw)

    def test_plan_fixes_version_2_settings_and_identity(self):
        plan = self.plan("p")
        self.assertEqual((plan["format"], B.COMPLETE_FORMAT, B.TOOL_VERSION, plan["identity"]["tool"]["version"]),
                         ("kyuura-vai-batch-plan/6", "kyuura-vai-batch-complete/6", 10, 10))  # 10: 判定の規則 8。9: 判定の規則 7（reach 版 2 の設定・選び方は同じ）
        for entry, settings in zip(plan["games"], (P6_V2, UR_V2)):
            self.assertEqual((entry["config"]["policy"], entry["config"]["profile"], entry["config"]["rules_version"], entry["config"]["reach"]),
                             ("reach", "boundary", 2, settings))
            for side in ("0", "1"):
                p = entry["policies"][side]
                self.assertEqual((p["name"], p["version"], p["rules_version"], p["reach"], p["distribution"]), ("reach", 2, 2, settings, RP.REACH_DISTRIBUTION_2))
        loaded, digest_ = B.load_plan(B.batch_dir(self.tmp, "p"), self.a)
        self.assertEqual(loaded["games"][1]["config"]["reach"]["target_input_cards"], [FIRE])
        self.assertEqual(digest_, (B.batch_dir(self.tmp, "p") / "plan.sha256").read_text(encoding="utf-8").split()[0])

    def _rewrite(self, name, edit):
        bdir = B.batch_dir(self.tmp, name)
        plan = json.loads((bdir / "plan.json").read_bytes())
        edit(plan)
        data = B.json_bytes(plan)
        (bdir / "plan.json").write_bytes(data)
        (bdir / "plan.sha256").write_bytes((B.sha256_bytes(data) + "  plan.json\n").encode())
        return bdir

    def test_tampered_or_mismatched_plans_are_refused(self):
        cases = {
            "target_input_cards": lambda p: p["games"][1]["config"]["reach"].update(target_input_cards=[FIGHTING]),
            "place_cards": lambda p: p["games"][0]["config"]["reach"].update(place_cards=[DIGLETT]),
            "drop_target_input_cards": lambda p: p["games"][1]["config"]["reach"].pop("target_input_cards"),
            "version_1_with_v2_keys": lambda p: p["games"][0]["config"]["reach"].update(version=1),
            "version_1_mode_name": lambda p: p["games"][0].update(mode="reach-p6"),
            "swap_modes": lambda p: p["games"][1].update(mode="reach2-p6"),
            "protect": lambda p: p["games"][1]["config"]["reach"].update(protect_own_turns=4),
            "tool_version_7": lambda p: p["identity"]["tool"].update(version=7),
        }
        for name, edit in cases.items():
            with self.subTest(name):
                self.plan(name)
                with self.assertRaises(B.BatchRefused) as ctx:
                    B.load_plan(self._rewrite(name, edit), self.a)
                if name == "tool_version_7":
                    self.assertIn("実装識別", str(ctx.exception))

    def test_short_real_game_records_version_2(self):
        """本物の 1 局（操作 40。固定デッキ。秘策・ヒトカゲはない）: 版 2 の設定と状態が runner・記録・観測の記録・到達の段の集計へ届く（到達を狙わない）。"""
        from tools.verification_ai import reach_report as RR

        self.plan("real", modes=("reach2-u-r3a",), observation=True)
        out = B.run_batch(self.tmp, "real", adapter=self.a)
        self.assertEqual(out.status, "completed")
        adir = B.batch_dir(self.tmp, "real") / "games" / "g001-reach2-u-r3a-s12" / "attempt-001"
        result = json.loads((adir / "result.json").read_text(encoding="utf-8"))
        state = result["policies"]["0"]["reach_state"]
        self.assertEqual((result["policies"]["0"]["reach"], state["version"], state["budget_used"]), (UR_V2, 2, 0))
        self.assertIn("input_ready", state)
        trace = [json.loads(line) for line in (adir / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
        attempts = [e for e in trace if e.get("type") == "attempt" and e["actor"] in (0, 1)]
        self.assertTrue(attempts and all(e["candidate_reason"].startswith("reach:") for e in attempts))
        self.assertEqual(json.loads((adir / "observe" / "summary.json").read_text(encoding="utf-8"))["status"], "complete")
        report = RR.game_report(adir)
        self.assertEqual(report["goals"]["u_r3a"]["target"]["0"]["submitted"], 0)
        self.assertEqual(report["policy"]["final_state"]["0"]["version"], 2)


# ---------------------------------------------------------------- fixture（構築盤面。new_game からの到達ではない）


def fixture_p6_secret_plan_chain():
    """秘策の盤面（tests/test_secret_plan_v0_67 の board。手札に秘策・ディグダ・闘エネルギー）: R2（秘策）→ 置く（ディグダを選ぶ）→ R1（通常のにげるでうらの控えへ）→ R0（P6）。"""
    from tests import test_secret_plan_v0_67 as S

    case = _hosted(S.board(hand=(S.DIGLETT, S.FIGHTING)))
    policies, budget = pair(P6_V2, seed="fixture-v2-p6")
    steps = [drive(case, policies, 0, expect_rule="R2")]
    steps.append(drive(case, policies, 0, expect_rule="rule2"))  # 秘策の決定（answer_decision）の回答: 置くカードの段で対象を選ぶ
    steps.append(drive(case, policies, 0, expect_rule="R1"))
    steps.append(drive(case, policies, 0, expect_rule="R0"))
    return {"fixture": "secret_plan_board(hand=DIGLETT,FIGHTING)", "origin": "constructed_fixture", "new_game": False, "steps": steps, "budget": budget.used}


def fixture_p6_no_target():
    from tests import test_secret_plan_v0_67 as S

    case = _hosted(S.board(hand=(S.FIGHTING,)))
    policies, _ = pair(P6_V2, seed="fixture-v2-p6-none")
    return drive(case, policies, 0, expect_rule="rule2")


def fixture_u_r3a_rc():
    from tools.verification_ai import fixtures_u_r3a as F

    state, record = F.build("UR3A-RC")
    case = _hosted(state)
    policies, budget = pair(UR_V2, seed="fixture-v2-ur3a")
    step = drive(case, policies, 0, expect_rule="R0")
    return {"fixture": "UR3A-RC", "origin": "constructed_fixture", "new_game": False, "source": [s["file"] for s in record["source"]], "steps": [step],
            "budget": budget.used, "public_events": [e["kind"] for e in case.game.state.log if e["kind"] in ("secret_plan_revealed", "pokemon_power", "move_energy")]}


def fixture_u_r3a_wrong_energy():
    """UR3A-RC: 候補は reach 版 2 が R0 で選び、入力はケースの選び手（fixtures_u_r3a.hitmonchan_fighting。方策ではない）でエビワラーの闘エネルギー。"""
    from kyuura_engine.observation import visible_log

    from tools.verification_ai import actions as A
    from tools.verification_ai import fixtures_u_r3a as F
    from tools.verification_ai.judge import judge_normal
    from tools.verification_ai.policies import action_key
    from tools.verification_ai.runner import request, submit_checked

    state, _record = F.build("UR3A-RC")
    case = _hosted(state)
    policies, budget = pair(UR_V2, seed="fixture-v2-ur3a-wrong")
    policy, endpoint = policies[0], case.endpoints[0]
    v = request(endpoint, "view")
    policy.begin_episode()
    profile = policy.scope_profile(v)
    cands = request(endpoint, "candidates")["response"]
    in_scope, _info, _ = _scope(cands, profile)
    index, reason = policy.choose("candidate", in_scope, {"view": v, "candidates": cands})
    candidate = in_scope[index]
    handle = {"game": cands["game"], "revision": cands["revision"], "candidate": candidate["id"]}
    stages = request(endpoint, "inputs", **handle)["response"]["stages"]
    tuples = A.enumerate_inputs(stages, A.FALLBACK_PROCESSABILITY, kind=candidate["kind"])
    choices, meaning = tuples[F.hitmonchan_fighting(tuples)]
    key = action_key(0, candidate, stages, meaning)
    review = policy.review(candidate, key, None)["reason"]
    checked = request(endpoint, "check", **handle, choices=choices)
    checked["_handle"], checked["_choices"] = handle, choices
    before = len(visible_log(case.game.state, None))
    sent = submit_checked(endpoint, handle, choices, checked, operation_id="reach2-fixture-wrong")
    policy.notify_submit(candidate, key)
    submit = {"ok": sent.get("ok"), "outcome": sent.get("outcome"), "refusal": sent.get("refusal"), "result": sent.get("result")}
    result = case.results[-1] if case.results else None  # 検証者の側の診断（方策には渡さない。drive と同じ）
    if result is not None and result.diagnosis is not None:
        submit["verifier"] = {"diagnostic_id": result.diagnosis.diagnostic_id, "category": result.diagnosis.category, "engine_code": result.verifier.engine_code}
    verdict, why = judge_normal(candidate, meaning, submit, stages=stages)
    return {"profile": profile, "rule": reason.split(":")[2], "chosen": candidate["kind"], "review": review, "check_valid": checked["response"]["valid"],
            "outcome": sent.get("outcome"), "judge": [verdict, why[:2]], "budget": budget.used, "public_events_after": len(visible_log(case.game.state, None)) - before,
            "after": {str(a): {"active": p.active(), "profile": p.scope_profile(request(case.endpoints[a], "view"))} for a, p in policies.items()}}


class FixtureV2Test(unittest.TestCase):
    def test_p6_secret_plan_chain_revealed_and_retreated(self):
        out = fixture_p6_secret_plan_chain()
        r2, answer, r1, r0 = out["steps"]
        self.assertEqual((r2["chosen"], r2["outcome"], r2["budget_after_submit"]), ("play_trainer", "accepted", 0))
        self.assertTrue(any("R2:trainer" in p or p.startswith("reach:stage:") for p in r2["picks"]) or not r2["picks"])
        self.assertEqual((answer["chosen"], answer["outcome"]), ("answer_decision", "accepted"))
        self.assertTrue(any(":place:card" in p for p in answer["picks"]), answer["picks"])
        self.assertEqual((r1["chosen"], r1["target"], r1["outcome"], r1["budget_after_submit"]), ("retreat", False, "accepted", 0))
        self.assertTrue(any("R1:face_down_new_active" in p for p in r1["picks"]))
        self.assertEqual((r0["chosen"], r0["target"], r0["profile"], r0["check_valid"], r0["review"], r0["outcome"]),
                         ("retreat", True, "boundary", True, "reach:target_send", "accepted"))
        self.assertEqual((r0["budget_before_submit"], r0["budget_after_submit"], out["budget"]), (0, 1, 1))
        self.assertEqual(r0["judge"][0], "expected")
        self.assertEqual(r0["accepted_content"], ["expected", "p6_revealed_and_retreated"])
        self.assertEqual(r0["after"], {"0": {"active": False, "profile": "deep"}, "1": {"active": False, "profile": "deep"}})

    def test_p6_without_target_in_hand_uses_the_normal_path(self):
        step = fixture_p6_no_target()
        self.assertNotEqual(step["chosen"], "play_trainer")
        self.assertEqual(step["budget_after_submit"], 0)

    def test_u_r3a_rc_revealed_and_used(self):
        out = fixture_u_r3a_rc()
        step = out["steps"][0]
        self.assertEqual((step["chosen"], step["target"], step["profile"], step["check_valid"], step["review"], step["outcome"]),
                         ("use_power", True, "boundary", True, "reach:target_send", "accepted"))
        self.assertTrue(any("R0:input_host" in p for p in step["picks"]) and any("R0:input_card" in p for p in step["picks"]), step["picks"])
        self.assertEqual(step["judge"][0], "expected")
        self.assertEqual(step["accepted_content"], ["expected", "face_down_power_revealed_and_used"])
        self.assertEqual(out["public_events"], ["secret_plan_revealed", "pokemon_power", "move_energy"])
        self.assertEqual((step["budget_after_submit"], out["budget"]), (1, 1))
        self.assertEqual(step["after"], {"0": {"active": False, "profile": "deep"}, "1": {"active": False, "profile": "deep"}})

    def test_u_r3a_non_fire_is_a_normal_rejection(self):
        out = fixture_u_r3a_wrong_energy()
        self.assertEqual((out["rule"], out["chosen"], out["review"], out["check_valid"], out["outcome"]), ("R0", "use_power", "reach:target_send", True, "rejected"))
        self.assertEqual(out["judge"], ["normal_rejection", ["invalid_input", "WRONG_ENERGY_TYPE"]])
        self.assertEqual(out["budget"], 1)
        self.assertEqual(out["after"], {"0": {"active": False, "profile": "deep"}, "1": {"active": False, "profile": "deep"}})


if __name__ == "__main__":
    unittest.main()

"""特殊状態の共通基盤とどく（v0.3a）: ビードル（PMCG1-004）の「どくばり」、どく状態の付与・解除・状態の保存。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES。カードの記録 PMCG1-004）:

- p.19 のビードル（LV.12/HP40、第1弾）。最新の説明「●どくばり コインを投げて「おもて」なら、相手を「どく」状態にする。」
- p.322「10 ポケモンの特殊状態」: 特殊状態になるのはバトル場のポケモンだけ。バトル場をはなれたら（ベンチに戻ったら）
  すべて消え、復活しない。与えたポケモンが場をはなれても消えない。どく状態は積み重ならない。どくのダメージは
  ポケモンチェックのたびに弱点・抵抗力に関係なく 10。プラスパワー・ディフェンダーは関係しない。自然に回復しない
- p.311: にげるのは、ねむり・マヒでなければできる。ベンチに戻ったら「どく」…状態はすべて消える（2 回にげて
  どく状態を直す例）
- p.309・p.320: ワザの要素は書かれている順番（相手へのダメージ → コイン → どく）。対象がいなくなった内容は無視する
- p.321: 太字の「相手」は相手の対戦ポケモン。どくのダメージはワザによるダメージではない

ポケモンチェックそのもの（時点・きぜつ・サイド・交代）は test_pokemon_check.py、正式な対戦開始からは test_weedle_games.py。
"""

import copy
import json
import pickle
import unittest

from kyuura_engine import (
    EndTurn, EngineError, Phase, PlayTrainer, ResolveDecision, Retreat, UseAttack, apply_command, check_invariants,
    load_card_pool, state_to_dict,
)
from kyuura_engine.cards import read_extract, read_verification
from kyuura_engine.conditions import NORMAL_POISON, poison
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackKey, PoisonOnHeads
from kyuura_engine.rng import copy_rng, rng_fingerprint
from kyuura_engine.state import NO_SPECIAL_CONDITIONS, Poison, SpecialConditions

from tests.helpers import (
    DEFENDER, DIGLETT, FIRE, GRASS, GROWLITHE, H, PLUSPOWER, PONYTA, POTION, RATTATA, SWITCH, T, WEEDLE,
    build_test_state, with_coin_results,
)

POISON_STING = 0


def full(state):
    return state_to_dict(state, format_version=5)


def hand(state, player, card_id):
    return [u for u in state.players[player].hand if state.cards[u].card_id == card_id]


def weedle_vs(defender, *sides, damage=0, poisoned=None, hand_cards=(), bench=(PONYTA,), their_bench=(GROWLITHE,),
              their_hand=(), their_energy=(), energy=(GRASS,), prizes=6, their_prizes=6):
    """プレイヤー 0（番）のビードル（草エネルギー 1）と、プレイヤー 1 の対戦ポケモン ``defender``。"""
    spec = {"card": defender, "damage": damage, "energy": list(their_energy)}
    if poisoned is not None:
        spec["poison"] = poisoned
    state = build_test_state([
        {"active": {"card": WEEDLE, "energy": list(energy)}, "bench": list(bench), "hand": list(hand_cards), "prizes": prizes},
        {"active": spec, "bench": list(their_bench), "hand": list(their_hand), "prizes": their_prizes},
    ])
    return with_coin_results(state, *sides) if sides else state


def sting(state, player=0):
    start = len(state.log)
    new = apply_command(state, UseAttack(player, POISON_STING))
    return new, [dict(e) for e in new.log[start:]]


def kinds(events):
    return [e["kind"] for e in events]


# ---------------------------------------------------------------- 登録と照合


class WeedleRegistrationTest(unittest.TestCase):
    def test_registered_attack(self):
        entry = DEFAULT_EFFECTS.attack_entry(WEEDLE, POISON_STING)
        self.assertIsInstance(entry.effect, PoisonOnHeads)
        self.assertEqual((entry.name_ja, entry.source), ("どくばり", "P43 p.19"))
        self.assertEqual(entry.text_ja, "コインを投げて「おもて」なら、相手を「どく」状態にする。")
        record = read_verification()["cards"][WEEDLE]
        self.assertEqual((record["status"], record["page"], record["pdf_page"]), ("一致", 19, 21))
        self.assertEqual(entry.play_text_ja, record["latest_description_ja"])
        self.assertTrue(load_card_pool().is_playable(WEEDLE))

    def test_card_data_matches_the_book(self):
        """p.19: たねポケモン、LV.12/HP40、草、どくばり（草 1）10、にげる 1、弱点 炎（抵抗力なし）。"""
        weedle = load_card_pool().get(WEEDLE)
        self.assertEqual((weedle.name_ja, weedle.hp, weedle.pokemon_type.value, weedle.retreat_cost), ("ビードル", 40, "grass", 1))
        self.assertEqual((weedle.weakness.value, weedle.resistance), ("fire", None))
        (attack,) = weedle.attacks
        self.assertEqual((attack.name_ja, attack.damage, attack.damage_modifier), ("どくばり", 10, None))
        self.assertEqual([c.value for c in attack.cost], ["grass"])
        self.assertEqual(read_extract()["pool_v0_3a"], [WEEDLE])

    def test_wrong_registrations_are_detected(self):
        pool = load_card_pool()
        rattata_bite = pool.get(RATTATA).attacks[0]  # 説明文のないワザ
        self.assertTrue(PoisonOnHeads().check(rattata_bite))
        self.assertEqual(PoisonOnHeads().check(pool.get(WEEDLE).attacks[0]), [])
        unregistered = DEFAULT_EFFECTS.without_attacks("test-no-sting", [AttackKey(WEEDLE, POISON_STING)])
        self.assertIsNone(unregistered.attack_entry(WEEDLE, POISON_STING))


# ---------------------------------------------------------------- どくばり


class PoisonStingTest(unittest.TestCase):
    def test_heads_poisons_after_the_damage(self):
        """相手に 10 → コイン 1 枚 → 「おもて」ならどく（p.309・p.320 の順）。番が終わり、ポケモンチェックで 10（p.323）。"""
        state = weedle_vs(GROWLITHE, H)
        target = state.players[1].active
        new, events = sting(state)
        self.assertEqual(kinds(events)[:7], ["attack", "damage", "coin_flip", "special_condition", "turn_end", "pokemon_check", "poison_damage"])
        damage, coin, poisoned, check_damage = events[1], events[2], events[3], events[6]
        self.assertEqual((damage["player"], damage["amount"]), (1, 10))
        self.assertEqual((coin["player"], coin["effect"], coin["result"], coin["count"]), (0, "PMCG1-004#0", "heads", 1))
        self.assertEqual(
            {k: poisoned[k] for k in ("player", "pokemon", "pokemon_id", "condition", "damage", "effect")},
            {"player": 1, "pokemon": target.card, "pokemon_id": target.pokemon_id, "condition": "poison", "damage": 10, "effect": "PMCG1-004#0"},
        )
        self.assertNotIn("already", poisoned)
        self.assertEqual((check_damage["player"], check_damage["pokemon_id"], check_damage["amount"], check_damage["total_damage"]),
                         (1, target.pokemon_id, 10, 20))
        growlithe = new.players[1].active
        self.assertEqual((growlithe.pokemon_id, growlithe.damage, growlithe.conditions.poison), (target.pokemon_id, 20, NORMAL_POISON))
        self.assertEqual((new.phase, new.current_player), (Phase.MAIN, 1))
        self.assertEqual(check_invariants(new), [])

    def test_tails_does_not_poison(self):
        new, events = sting(weedle_vs(GROWLITHE, T))
        self.assertEqual(kinds(events)[:5], ["attack", "damage", "coin_flip", "turn_end", "pokemon_check"])
        self.assertNotIn("special_condition", kinds(events))
        self.assertNotIn("poison_damage", kinds(events))
        self.assertEqual((new.players[1].active.damage, new.players[1].active.conditions), (10, NO_SPECIAL_CONDITIONS))

    def test_one_coin(self):
        """コインは 1 枚（乱数を 1 回）。番の終わり・ポケモンチェック・次の番のドローは乱数を使わない。"""
        for side in (H, T):
            with self.subTest(side=side):
                state = weedle_vs(GROWLITHE, side)
                expected = copy_rng(state.rng)
                expected.getrandbits(1)
                new, events = sting(state)
                self.assertEqual(kinds(events).count("coin_flip"), 1)
                self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(expected))

    def test_poison_does_not_depend_on_the_damage(self):
        """どくにするのは「効果」で、ダメージではない。ディフェンダーでダメージが 0 でも「おもて」ならどく（p.320・p.321）。"""
        state = weedle_vs(GROWLITHE, their_hand=[DEFENDER])
        state = apply_command(state, EndTurn(0))
        state = apply_command(state, PlayTrainer(1, hand(state, 1, DEFENDER)[0]))
        state = apply_command(state, ResolveDecision(1, state.decision.id, (state.players[1].active.pokemon_id,)))
        state = apply_command(state, EndTurn(1))
        new, events = sting(with_coin_results(state, H))
        damage = next(e for e in events if e["kind"] == "damage")
        self.assertEqual((damage["amount"], [m[0] for m in damage["modifiers"]]), (0, [7]))
        self.assertIn("special_condition", kinds(events))
        # ディフェンダーは今の番（相手の次の番）の終わりにトラッシュ（p.257）。どくのダメージは 10（p.322）
        check = next(e for e in events if e["kind"] == "poison_damage")
        self.assertEqual(check["amount"], 10)

    def test_weakness_applies_to_the_attack_damage_only(self):
        """ディグダ（HP30、弱点 草）: どくばりのダメージは 20（p.321 の 3 段階）。どくのダメージは 10 のまま（p.322）で、
        合わせて 30 になり、ポケモンチェックできぜつする（p.323）。"""
        new, events = sting(weedle_vs(DIGLETT, H))
        damage = next(e for e in events if e["kind"] == "damage")
        check = next(e for e in events if e["kind"] == "poison_damage")
        knock_out = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual((damage["amount"], damage["weakness"], check["amount"], check["total_damage"]), (20, True, 10, 30))
        self.assertEqual((knock_out["player"], knock_out["timing"]), (1, "pokemon_check"))

    def test_knocked_out_target_is_not_poisoned_and_no_coin(self):
        """どくばりの 10 で相手がきぜつしたら、どくにする内容は対象がいないので無視する（p.309・p.323）。コインも投げない。"""
        state = weedle_vs(RATTATA, H, damage=20)
        before = rng_fingerprint(state.rng)
        new, events = sting(state)
        self.assertNotIn("coin_flip", kinds(events))
        self.assertNotIn("special_condition", kinds(events))
        self.assertEqual(kinds(events)[:3], ["attack", "damage", "knock_out"])
        self.assertEqual(rng_fingerprint(new.rng), before)

    def test_already_poisoned(self):
        """どく状態のポケモンが再びどくを受けても、二重のどく状態にはならない（p.322）。ポケモンチェックのダメージは 10 だけ。"""
        new, events = sting(weedle_vs(GROWLITHE, H, poisoned=10))
        poisoned = next(e for e in events if e["kind"] == "special_condition")
        self.assertTrue(poisoned["already"])
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(poison=Poison(10)))
        self.assertEqual([e["amount"] for e in events if e["kind"] == "poison_damage"], [10])

    def test_tails_keeps_the_poison(self):
        """どく状態は自然に回復しない（p.322）。「うら」でも、もとのどくは残る。"""
        new, events = sting(weedle_vs(GROWLITHE, T, poisoned=10))
        self.assertEqual(new.players[1].active.conditions.poison, NORMAL_POISON)
        self.assertEqual([e["amount"] for e in events if e["kind"] == "poison_damage"], [10])

    def test_rejections_change_nothing(self):
        for state, command, code in (
            (weedle_vs(GROWLITHE, H, energy=()), UseAttack(0, POISON_STING), "INSUFFICIENT_ENERGY"),
            (weedle_vs(GROWLITHE, H, energy=(FIRE,)), UseAttack(0, POISON_STING), "INSUFFICIENT_ENERGY"),
            (weedle_vs(GROWLITHE, H), UseAttack(0, 1), "INVALID_ATTACK"),
            (weedle_vs(GROWLITHE, H), UseAttack(1, POISON_STING), "NOT_YOUR_TURN"),
        ):
            with self.subTest(code=code):
                before, fingerprint = full(state), rng_fingerprint(state.rng)
                with self.assertRaises(EngineError) as ctx:
                    apply_command(state, command)
                self.assertEqual(ctx.exception.code, code)
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
        unregistered = build_test_state(
            [{"active": {"card": WEEDLE, "energy": [GRASS]}}, {"active": GROWLITHE}],
            effects=DEFAULT_EFFECTS.without_attacks("test-no-sting", [AttackKey(WEEDLE, POISON_STING)]),
        )
        with self.assertRaises(EngineError) as ctx:
            apply_command(unregistered, UseAttack(0, POISON_STING))
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_ATTACK")


# ---------------------------------------------------------------- どく状態の性質


class PoisonStateTest(unittest.TestCase):
    def test_only_the_active_pokemon(self):
        """特殊状態になるのはバトル場のポケモンだけ（p.322）。ベンチのポケモンをどくにしようとしたらエンジンの不具合として止める。"""
        state = weedle_vs(GROWLITHE)
        with self.assertRaises(RuntimeError):
            poison(state, 1, state.players[1].bench[0], effect="test")

    def test_poison_persists_and_accumulates(self):
        """自然に回復しない（p.322）。ポケモンチェックのたびに 10（p.323）。"""
        state = weedle_vs(GROWLITHE, poisoned=10)
        for turn in range(4):
            state = apply_command(state, EndTurn(state.current_player))
            self.assertEqual(state.players[1].active.damage, 10 * (turn + 1))
            self.assertEqual(state.players[1].active.conditions.poison, NORMAL_POISON)

    def test_potion_removes_counters_not_the_poison(self):
        """きずぐすりはダメージカウンターをとりのぞくだけ（p.254）。どく状態は消えない（回復の手段ではない）。"""
        state = weedle_vs(GROWLITHE, damage=20, poisoned=10, their_hand=[POTION])
        state = apply_command(state, EndTurn(0))  # どくで 30
        state = apply_command(state, PlayTrainer(1, hand(state, 1, POTION)[0]))
        state = apply_command(state, ResolveDecision(1, state.decision.id, (state.players[1].active.pokemon_id,)))
        self.assertEqual(state.players[1].active.damage, 10)
        self.assertEqual(state.players[1].active.conditions.poison, NORMAL_POISON)
        state = apply_command(state, EndTurn(1))
        self.assertEqual(state.players[1].active.damage, 20)

    def test_source_leaving_play_does_not_cure(self):
        """どく状態にしたポケモン（ビードル）がきぜつしても、相手のどくは消えない（p.322）。"""
        state = weedle_vs(GROWLITHE, poisoned=10, their_energy=[FIRE, FIRE])
        state.players[0].active.damage = 30
        state = apply_command(state, EndTurn(0))
        state = apply_command(state, UseAttack(1, 0))  # ガーディの「ほのお」20 でビードルがきぜつ
        while state.decision is not None:
            d = state.decision
            state = apply_command(state, ResolveDecision(d.player, d.id, (d.options[0],)))
        self.assertNotIn(WEEDLE, [state.cards[p.card].card_id for p in state.players[0].in_play()])
        self.assertEqual(state.players[1].active.conditions.poison, NORMAL_POISON)


# ---------------------------------------------------------------- にげる・ポケモンいれかえ


class CureTest(unittest.TestCase):
    """バトル場からベンチに戻ったら、特殊状態はすべて消える（p.311・p.322）。ダメージ・ついているカード・番号はそのまま（p.311）。"""

    def poisoned_board(self, hand_cards=()):
        state = build_test_state([
            {"active": {"card": GROWLITHE, "damage": 20, "energy": [FIRE, FIRE], "poison": 10}, "bench": [PONYTA, RATTATA],
             "hand": list(hand_cards)},
            {"active": {"card": WEEDLE, "energy": [GRASS]}, "bench": [DIGLETT]},
        ], current_player=0)
        return state

    def test_retreat_cures_and_keeps_everything_else(self):
        state = self.poisoned_board(hand_cards=[PLUSPOWER])
        state = apply_command(state, PlayTrainer(0, hand(state, 0, PLUSPOWER)[0]))
        growlithe = state.players[0].active
        start = len(state.log)
        state = apply_command(state, Retreat(0, (growlithe.energy[0],), state.players[0].bench[0].card))
        events = [dict(e) for e in state.log[start:]]
        self.assertEqual(kinds(events), ["retreat", "special_conditions_removed"])
        self.assertEqual({k: events[1][k] for k in ("player", "pokemon_id", "conditions", "reason")},
                         {"player": 0, "pokemon_id": growlithe.pokemon_id, "conditions": ("poison",), "reason": "retreat"})
        benched = state.players[0].bench[0]
        self.assertEqual((benched.pokemon_id, benched.damage, len(benched.energy), [t.card for t in benched.trainers]),
                         (growlithe.pokemon_id, 20, 1, [t.card for t in growlithe.trainers]))
        self.assertEqual(benched.conditions, NO_SPECIAL_CONDITIONS)
        self.assertEqual(check_invariants(state), [])

    def test_retreat_twice_to_cure(self):
        """p.311 の例: 1 回目のにげるで入れ替え、2 回目で元にもどす。もどったポケモンのどく状態は消えている（復活しない。p.322）。

        ガーディ（にげる 1）→ コラッタ（にげる 0）→ ガーディ。
        """
        state = build_test_state([
            {"active": {"card": GROWLITHE, "energy": [FIRE, FIRE], "poison": 10}, "bench": [RATTATA]},
            {"active": WEEDLE},
        ])
        rattata_card = state.players[0].bench[0].card
        growlithe = state.players[0].active
        state = apply_command(state, Retreat(0, (growlithe.energy[0],), rattata_card))
        state = apply_command(state, Retreat(0, (), growlithe.card))
        self.assertEqual(state.players[0].active.pokemon_id, growlithe.pokemon_id)
        self.assertEqual(state.players[0].active.conditions, NO_SPECIAL_CONDITIONS)
        start = len(state.log)
        state = apply_command(state, EndTurn(0))
        self.assertNotIn("poison_damage", [e["kind"] for e in state.log[start:]])

    def test_switch_cures(self):
        """ポケモンいれかえ（p.254）でベンチに戻ったポケモンも同じ（p.322・p.325）。にげると同じ処理（reason は switch）。"""
        state = self.poisoned_board(hand_cards=[SWITCH])
        growlithe = state.players[0].active
        state = apply_command(state, PlayTrainer(0, hand(state, 0, SWITCH)[0]))
        start = len(state.log)
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].bench[1].pokemon_id,)))
        events = [dict(e) for e in state.log[start:]]
        removed = next(e for e in events if e["kind"] == "special_conditions_removed")
        self.assertLess(kinds(events).index("switch"), kinds(events).index("special_conditions_removed"))
        self.assertEqual((removed["pokemon_id"], removed["reason"]), (growlithe.pokemon_id, "switch"))
        benched = next(p for p in state.players[0].bench if p.pokemon_id == growlithe.pokemon_id)
        self.assertEqual((benched.damage, len(benched.energy), benched.conditions), (20, 2, NO_SPECIAL_CONDITIONS))
        self.assertEqual(state.players[0].active.conditions, NO_SPECIAL_CONDITIONS)

    def test_no_event_without_conditions(self):
        """特殊状態のないポケモンがにげても、v0.2f と同じログ（新しいイベントは出ない）。"""
        state = build_test_state([{"active": {"card": GROWLITHE, "energy": [FIRE]}, "bench": [PONYTA]}, {"active": WEEDLE}])
        start = len(state.log)
        state = apply_command(state, Retreat(0, (state.players[0].active.energy[0],), state.players[0].bench[0].card))
        self.assertEqual(kinds([dict(e) for e in state.log[start:]]), ["retreat"])

    def test_promoted_pokemon_is_not_poisoned(self):
        """きぜつしたどく状態のポケモンの特殊状態は、場をはなれていっしょになくなる。代わりに出たポケモンは特殊状態ではない。"""
        state = build_test_state([
            {"active": {"card": WEEDLE, "energy": [GRASS]}},
            {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [DIGLETT]},
        ])
        state = apply_command(state, UseAttack(0, POISON_STING))  # 10 できぜつ
        while state.decision is not None:
            d = state.decision
            state = apply_command(state, ResolveDecision(d.player, d.id, (d.options[0],)))
        self.assertEqual(state.cards[state.players[1].active.card].card_id, DIGLETT)
        self.assertEqual(state.players[1].active.conditions, NO_SPECIAL_CONDITIONS)


# ---------------------------------------------------------------- 状態の複製・書き出し・不変条件


class StateTest(unittest.TestCase):
    def poisoned(self):
        new, _ = sting(weedle_vs(GROWLITHE, H))
        return new

    def test_clone_deepcopy_pickle(self):
        state = self.poisoned()
        for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            with self.subTest(copy=type(copied)):
                self.assertEqual(full(copied), full(state))
                self.assertEqual(copied.players[1].active.conditions.poison, NORMAL_POISON)
                # 複製したほうを変えても、もとは変わらない（特殊状態は frozen で、変えるときは置きかえる）
                copied.players[1].active.conditions = NO_SPECIAL_CONDITIONS
                self.assertEqual(state.players[1].active.conditions.poison, NORMAL_POISON)
                # 同じコマンドで同じ結果
                a = apply_command(state, EndTurn(1))
                b = apply_command(pickle.loads(pickle.dumps(state)), EndTurn(1))
                self.assertEqual(full(a), full(b))

    def test_format_5(self):
        data = full(self.poisoned())
        self.assertEqual(data["format_version"], 5)
        self.assertEqual(data["players"][1]["active"]["special_conditions"], {"poison": {"damage": 10}})
        self.assertEqual(data["players"][0]["active"]["special_conditions"], {})
        self.assertEqual([b["special_conditions"] for b in data["players"][1]["bench"]], [{}])
        json.dumps(data)

    def test_older_formats_refuse_conditions(self):
        """形式 1〜4 は特殊状態を表せないので、黙って落とさずに ValueError（v0.2c の、ついているトレーナーと同じ方針）。"""
        state = self.poisoned()
        for version in (1, 2, 3, 4):
            with self.subTest(version=version), self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        cured = state.clone()
        cured.players[1].active.conditions = NO_SPECIAL_CONDITIONS
        for version in (1, 2, 3, 4):
            state_to_dict(cured, format_version=version)  # 特殊状態がなければ今までどおり書き出せる

    def test_format_5_without_conditions_extends_format_4(self):
        state = weedle_vs(GROWLITHE)
        v4, v5 = state_to_dict(state, format_version=4), full(state)
        self.assertEqual(v5.pop("format_version"), 5)
        v4.pop("format_version")
        for p4, p5 in zip(v4["players"], v5["players"]):
            for a, b in zip([p4["active"], *p4["bench"]], [p5["active"], *p5["bench"]]):
                self.assertEqual(b.pop("special_conditions"), {})
        self.assertEqual(v4, v5)


class ConditionInvariantTest(unittest.TestCase):
    def test_bench_pokemon_cannot_have_conditions(self):
        state = weedle_vs(GROWLITHE)
        state.players[1].bench[0].conditions = SpecialConditions(poison=NORMAL_POISON)
        self.assertTrue(any("ベンチ" in p for p in check_invariants(state)))

    def test_poison_damage_must_be_positive_multiple_of_ten(self):
        for bad in (0, -10, 15, "10", None):
            with self.subTest(damage=bad):
                state = weedle_vs(GROWLITHE)
                state.players[1].active.conditions = SpecialConditions(poison=Poison(bad))
                self.assertTrue(check_invariants(state))
        state = weedle_vs(GROWLITHE)
        state.players[1].active.conditions = "poison"
        self.assertTrue(check_invariants(state))

    def test_valid_poison(self):
        state = weedle_vs(GROWLITHE, poisoned=10)
        self.assertEqual(check_invariants(state), [])


if __name__ == "__main__":
    unittest.main()

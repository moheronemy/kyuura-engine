"""化石の秘密のゴース（PMCG3-029）・ゴースト（PMCG3-030）のカードとワザ（v0.9。docs/haunter-line-v0.9.md の H1〜H13）。

- ゴース（p.158）: したでなめる（超）10「コインを投げて「おもて」なら、相手を「マヒ」状態にする。」・エナジーへんかん（超超）「自分の
  トラッシュから、「エネルギーカード」を最大2枚選び出し、手札に加える。その後、自分に10ダメージ。」（最新の説明）。
- ゴースト（p.160）: 特殊能力「とうめい」（tests/test_transparency_v0_9.py）・あくむ（超無）10「相手を「ねむり」状態にする。」。

盤面は ``build_test_state`` で直接作る（1 つの規定を確かめるテスト）。「最大2枚」が 0 枚を含むか（H4）は原典で決められないので、
「止まること・状態が変わらないこと」だけを確かめる（裁定をテストで決めない）。
"""

import pickle
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS, EnergyType, EvolvePokemon, IllegalActionError, ResolveDecision, Retreat, UnsupportedError, UseAttack, apply_command,
    check_invariants, load_card_pool, state_to_dict,
)
from kyuura_engine.cards import read_extract, read_verification
from kyuura_engine.effects import AttackImmunityOnHeads, ParalyzeOnHeads, RecoverEnergyAndSelfDamage, SleepOpponent
from kyuura_engine.rng import rng_fingerprint

from tests.helpers import (
    BASE_HAUNTER, CATERPIE, FIRE, GASTLY, GROWLITHE, H, HAUNTER, METAPOD, PONYTA, POTION, PSYCHIC, RATTATA, T, WATER,
    build_test_state, coin_events, no_base_haunter_pool, uids, with_coin_results,
)

TURN = 7
ENERGY_CONVERSION_LATEST = "自分のトラッシュから、「エネルギーカード」を最大2枚選び出し、手札に加える。その後、自分に10ダメージ。"
ENERGY_CONVERSION_PRINTED = "自分のトラッシュから最大2枚のエネルギーカードを選び、手札に加える。その後、自分に10ダメージ。"
LICK = "コインを投げて「おもて」なら、相手を「マヒ」状態にする。"
NIGHTMARE = "相手を「ねむり」状態にする。"


def written(state):
    return state_to_dict(state, format_version=9)


def events_since(state, start):
    return [dict(e) for e in state.log[start:]]


class CardDataTest(unittest.TestCase):
    """カードの値（kyuura の写し。p.158・p.160 の図版と見出しで照合した）と、登録（照合した文面・最新の説明・出典）。"""

    def test_values(self):
        pool = load_card_pool()
        gastly, haunter = pool.get(GASTLY), pool.get(HAUNTER)
        for d in (gastly, haunter):
            self.assertTrue(d.supported and pool.is_playable(d.id))
            self.assertEqual((d.hp, d.pokemon_type, d.weakness, d.resistance, d.retreat_cost),
                             (50, EnergyType.PSYCHIC, None, EnergyType.FIGHTING, 0))
        self.assertTrue(gastly.is_basic_pokemon)
        self.assertEqual((haunter.is_stage1_pokemon, haunter.evolves_from), (True, "ゴース"))
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage, a.damage_modifier, a.text_ja) for a in gastly.attacks], [
            ("したでなめる", ["psychic"], 10, None, LICK), ("エナジーへんかん", ["psychic", "psychic"], None, None, ENERGY_CONVERSION_PRINTED),
        ])
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage, a.damage_modifier, a.text_ja) for a in haunter.attacks],
                         [("あくむ", ["psychic", "colorless"], 10, None, NIGHTMARE)])
        self.assertEqual([(w.name_ja, w.kind, w.supported) for w in haunter.powers], [("とうめい", "pokemon_power", True)])
        extract = read_extract()
        self.assertEqual(extract["pool_v0_9"], [GASTLY, HAUNTER])
        # 第1弾のゴースト（同じ名前の別のカード）は v0.44 まで参照カード（ゆめくいが未実装）。v0.45 で写しの組 pool_v0_45 に移して対応にした。
        # 登録のないワザを持つカードが対応にならない性質は、その登録を除いた登録表で確かめる
        self.assertNotIn(BASE_HAUNTER, extract["reference_only"])
        self.assertIn(BASE_HAUNTER, extract["pool_v0_45"])
        self.assertTrue(pool.is_playable(BASE_HAUNTER))
        self.assertFalse(no_base_haunter_pool().is_playable(BASE_HAUNTER))

    def test_registration_follows_the_verified_latest_description(self):
        """登録の文面（照合用の kyuura の写し・実装がしたがう最新の説明・出典）が、照合の記録（card_verification.json）と同じ。"""
        records = read_verification()["cards"]
        gastly, haunter = records[GASTLY], records[HAUNTER]
        expected = {
            (GASTLY, 0): (ParalyzeOnHeads(), "したでなめる", gastly["card_image_text_ja"]["0"], gastly["latest_description_ja"]["0"], "P43 p.158"),
            (GASTLY, 1): (RecoverEnergyAndSelfDamage(max_cards=2, self_damage=10), "エナジーへんかん", gastly["card_image_text_ja"]["1"],
                          gastly["latest_description_ja"]["1"], "P43 p.158"),
            (HAUNTER, 0): (SleepOpponent(), "あくむ", haunter["card_image_text_ja"], haunter["latest_description_ja"], "P43 p.160"),
        }
        for (card, index), (effect, name, printed, latest, source) in expected.items():
            entry = DEFAULT_EFFECTS.attack_entry(card, index)
            self.assertEqual((entry.effect, entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (effect, name, printed, latest, source))
        self.assertEqual(gastly["latest_description_ja"]["1"], ENERGY_CONVERSION_LATEST)
        power = DEFAULT_EFFECTS.power_entry(HAUNTER, 0)
        self.assertEqual((power.effect, power.name_ja, power.text_ja, power.play_text_ja, power.source),
                         (AttackImmunityOnHeads(), "とうめい", haunter["power_card_image_text_ja"]["0"],
                          haunter["power_latest_description_ja"]["0"], "P43 p.160"))
        self.assertEqual(haunter["power_rules_example_ja"]["0"], power.play_text_ja)  # p.323 の例も同じ文面

    def test_implementation_arguments_are_checked(self):
        for kwargs in ({"max_cards": 0, "self_damage": 10}, {"max_cards": True, "self_damage": 10}, {"max_cards": 2, "self_damage": 15},
                       {"max_cards": 2, "self_damage": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                RecoverEnergyAndSelfDamage(**kwargs)


class LickTest(unittest.TestCase):
    """したでなめる（H1）: ダメージ 10 のあと、ワザのコインが「おもて」なら相手をマヒ（v0.3b の ``ParalyzeOnHeads`` と同じ）。"""

    def board(self, defender=GROWLITHE):
        return build_test_state([{"active": {"card": GASTLY, "energy": [PSYCHIC]}, "bench": [PONYTA]}, {"active": defender, "bench": [RATTATA]}],
                                turn_number=TURN)

    def test_heads_and_tails(self):
        for side, paralyzed in ((H, True), (T, False)):
            with self.subTest(side=side):
                state = with_coin_results(self.board(), side)
                new = apply_command(state, UseAttack(0, 0))
                events = events_since(new, len(state.log))
                self.assertEqual([(e["source"], e["result"]) for e in coin_events(new, len(state.log))][:1], [("attack", side.value)])
                self.assertEqual(next(e for e in events if e["kind"] == "damage")["amount"], 10)
                self.assertEqual("paralysis" in [e.get("condition") for e in events if e["kind"] == "special_condition"], paralyzed)

    def test_resisted_damage_still_paralyzes(self):
        """コラッタ（抵抗力 超 −30）には 0 ダメージ（「ダメージを受けなかった」）だが、マヒは効果なので受ける（p.321）。"""
        state = with_coin_results(self.board(RATTATA), H)
        new = apply_command(state, UseAttack(0, 0))
        events = events_since(new, len(state.log))
        self.assertEqual(next(e for e in events if e["kind"] == "damage")["amount"], 0)
        self.assertTrue(new.players[1].active.conditions.paralyzed)


class EnergyConversionTest(unittest.TestCase):
    """エナジーへんかん（H2〜H11）。"""

    def board(self, discard=(FIRE, POTION, PSYCHIC, WATER), *, damage=0, confusion=False, opponent_discard=(FIRE,)):
        gastly = {"card": GASTLY, "energy": [PSYCHIC, PSYCHIC], "damage": damage, **({"confusion": True} if confusion else {})}
        return build_test_state([
            {"active": gastly, "bench": [RATTATA], "discard": list(discard)},
            {"active": GROWLITHE, "bench": [PONYTA], "discard": list(opponent_discard)},
        ], turn_number=TURN)

    def test_decision_shape(self):
        """選ぶのはワザを使ったプレイヤー（「自分のトラッシュから…選び出し」。H2）。選べるのは、自分のトラッシュのエネルギーカード（種類を
        問わない。トラッシュの順。トレーナー・相手のトラッシュは選べない）。0〜2 枚（トラッシュにある枚数まで。H3）。決定を出すまでに
        乱数を使わない。"""
        state = self.board()
        new = apply_command(state, UseAttack(0, 1))
        decision = new.decision
        energies = [uid for uid in state.players[0].discard if state.card_def(uid).category == "energy"]
        self.assertEqual((decision.kind, decision.player, decision.options, decision.min_choices, decision.max_choices),
                         ("recover_energy", 0, tuple(energies), 0, 2))
        self.assertEqual(len(energies), 3)
        self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(state.rng))
        one = apply_command(self.board((POTION, WATER)), UseAttack(0, 1))
        self.assertEqual((one.decision.min_choices, one.decision.max_choices), (0, 1))

    def test_recover_then_self_damage(self):
        """選んだカードを手札に加え、その後、自分に 10 ダメージ（「その後」。H6）。自分へのダメージは p.321 の順番で計算する（ゴースの
        抵抗力は闘なので、超のワザで 10。H7）。番は終わる。"""
        state = self.board()
        waiting = apply_command(state, UseAttack(0, 1))
        for choices in (waiting.decision.options[:1], waiting.decision.options[1:]):
            with self.subTest(choices=choices):
                done = apply_command(waiting, ResolveDecision(0, waiting.decision.id, choices))
                self.assertEqual(check_invariants(done), [])
                events = events_since(done, len(waiting.log))
                self.assertEqual([e["kind"] for e in events[:2]], ["recover_energy", "damage"])
                self.assertEqual(events[0]["cards"], choices)
                self.assertEqual((events[1]["target"], events[1]["amount"]), ("self", 10))
                self.assertTrue(set(choices) <= set(done.players[0].hand))
                self.assertFalse(set(choices) & set(done.players[0].discard))
                self.assertEqual([uid for uid in done.players[0].discard], [uid for uid in state.players[0].discard if uid not in choices])
                self.assertEqual(done.players[0].active.damage, 10)
                self.assertEqual(done.current_player, 1)

    def test_zero_cards_is_unresolved(self):
        """トラッシュにエネルギーカードがあるのに 0 枚を選ぶのは原典で決められない（H4。UNRESOLVED_RECOVER_ZERO_ENERGY）。状態・乱数・
        ログは変わらず、決定は待ったまま（1 枚以上を選び直せる）。"""
        waiting = apply_command(self.board(), UseAttack(0, 1))
        before, fingerprint, log = written(waiting), rng_fingerprint(waiting.rng), waiting.log
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(waiting, ResolveDecision(0, waiting.decision.id, ()))
        self.assertEqual(ctx.exception.code, "UNRESOLVED_RECOVER_ZERO_ENERGY")
        self.assertEqual((written(waiting), rng_fingerprint(waiting.rng)), (before, fingerprint))
        self.assertIs(waiting.log, log)
        self.assertIsNotNone(apply_command(waiting, ResolveDecision(0, waiting.decision.id, waiting.decision.options[:1])))

    def test_invalid_choices(self):
        waiting = apply_command(self.board(), UseAttack(0, 1))
        decision = waiting.decision
        potion = uids(waiting, 0, "discard", POTION)[0]
        for player, choices, code in ((0, decision.options, "INVALID_CHOICE_COUNT"), (0, decision.options[:1] * 2, "DUPLICATE_CHOICE"),
                                      (0, (potion,), "INVALID_CHOICE"), (0, (waiting.players[1].discard[0],), "INVALID_CHOICE"),
                                      (1, decision.options[:1], "NOT_YOUR_DECISION")):
            with self.subTest(code=code, choices=choices):
                with self.assertRaises(IllegalActionError) as ctx:
                    apply_command(waiting, ResolveDecision(player, decision.id, choices))
                self.assertEqual(ctx.exception.code, code)

    def test_no_energy_in_the_discard(self):
        """トラッシュにエネルギーカードがなければ、手札に加える内容は対象がないので無視して、自分へのダメージを処理する（p.309。H5）。
        決定を出さない。"""
        state = self.board((POTION,))
        new = apply_command(state, UseAttack(0, 1))
        self.assertIsNone(new.decision)
        events = events_since(new, len(state.log))
        self.assertNotIn("recover_energy", [e["kind"] for e in events])
        self.assertEqual(next(e for e in events if e["kind"] == "damage")["target"], "self")
        self.assertEqual(new.players[0].active.damage, 10)

    def test_self_knock_out_after_recovering(self):
        """自分へのダメージできぜつしても、手札に加えたカードは手札のまま。きぜつはワザの要素をすべて処理したあと（p.309・p.324。H8）。"""
        waiting = apply_command(self.board(damage=40), UseAttack(0, 1))
        choices = waiting.decision.options[:2]
        done = apply_command(waiting, ResolveDecision(0, waiting.decision.id, choices))
        kinds = [e["kind"] for e in events_since(done, len(waiting.log))]
        self.assertLess(kinds.index("recover_energy"), kinds.index("knock_out"))
        self.assertTrue(set(choices) <= set(done.players[0].hand))
        self.assertEqual(done.decision.kind, "take_prize")
        self.assertEqual(done.decision.player, 1)

    def test_confused_tails(self):
        """こんらんの「うら」なら、ワザの効果の処理（エナジーへんかん）をせずに 20（ゴースに弱点はない）。決定は出ない。"""
        state = with_coin_results(self.board(confusion=True), T)
        new = apply_command(state, UseAttack(0, 1))
        kinds = [e["kind"] for e in events_since(new, len(state.log))]
        self.assertIn("confusion_damage", kinds)
        self.assertNotIn("recover_energy", kinds)
        self.assertEqual(new.players[0].active.damage, 20)

    def test_decision_invariants(self):
        """決定の形（種類・決定するプレイヤー・選ぶ数・選べるもの）を壊すと、不変条件（``decision_problems``）が見つける。"""
        import dataclasses

        waiting = apply_command(self.board(), UseAttack(0, 1))
        self.assertEqual(check_invariants(waiting), [])
        for change in ({"options": waiting.decision.options[:2]}, {"min_choices": 1}, {"max_choices": 3}, {"player": 1},
                       {"kind": "discard_energy"}):
            with self.subTest(change=change):
                broken = waiting.clone()
                broken.decision = dataclasses.replace(broken.decision, **change)
                self.assertTrue(check_invariants(broken))

    def test_save_and_restore_in_the_decision(self):
        waiting = apply_command(self.board(), UseAttack(0, 1))
        restored = pickle.loads(pickle.dumps(waiting))
        command = ResolveDecision(0, waiting.decision.id, waiting.decision.options[:2])
        self.assertEqual(written(apply_command(waiting, command)), written(apply_command(restored, command)))
        self.assertEqual(written(restored), written(waiting))


class NightmareTest(unittest.TestCase):
    """あくむ（H12）: 相手に 10 のあと、コインを投げずに相手をねむり（p.160 の解説「必ず相手をねむり状態にすることができます」）。"""

    def board(self, defender):
        return build_test_state([
            {"active": {"card": HAUNTER, "evolved_from": GASTLY, "energy": [PSYCHIC, FIRE]}, "bench": [PONYTA]},
            {"active": defender, "bench": [RATTATA]},
        ], turn_number=TURN)

    def attack(self, defender):
        state = self.board(defender)
        new = apply_command(state, UseAttack(0, 0))
        events = events_since(new, len(state.log))
        return state, new, events

    def test_damage_then_sleep_without_a_coin(self):
        state, new, events = self.attack(GROWLITHE)
        turn_events = events[:events.index(next(e for e in events if e["kind"] == "turn_end"))]
        self.assertEqual([e["kind"] for e in turn_events], ["attack", "damage", "special_condition"])
        self.assertEqual((turn_events[1]["amount"], turn_events[2]["condition"]), (10, "sleep"))
        self.assertEqual([e["source"] for e in coin_events(new, len(state.log))], ["pokemon_check"])  # ねむりのコインだけ

    def test_sleep_is_an_effect(self):
        """ねむりは効果なので、最終ダメージが 0（コラッタの抵抗力 超 −30）でも、「ダメージを受けない」状態でも受ける（p.321）。"""
        for defender, kind in ((RATTATA, "damage"), ({"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1}, "damage_prevented")):
            with self.subTest(defender=defender):
                _, _, events = self.attack(defender)
                self.assertIn(kind, [e["kind"] for e in events])
                self.assertIn("sleep", [e.get("condition") for e in events if e["kind"] == "special_condition"])

    def test_knocked_out_target_is_not_put_to_sleep(self):
        """ダメージできぜつしたら、ねむりにする内容は対象がいないので無視する（p.309・p.323）。"""
        _, _, events = self.attack({"card": GROWLITHE, "damage": 50})
        kinds = [e["kind"] for e in events]
        self.assertIn("knock_out", kinds)
        self.assertNotIn("special_condition", kinds)

    def test_replaces_paralysis(self):
        """マヒの相手はねむりに置きかわる（p.322 の特殊状態の重複）。"""
        _, new, events = self.attack({"card": GROWLITHE, "paralysis": TURN - 1})
        self.assertIn("replaced", [e.get("reason") for e in events if e["kind"] == "special_conditions_removed"])


class EvolutionTest(unittest.TestCase):
    """ゴース → ゴースト（H13。p.310）。にげるエネルギー 0。"""

    def test_evolve_and_retreat_for_free(self):
        state = build_test_state([
            {"active": {"card": GASTLY, "damage": 20, "energy": [PSYCHIC]}, "bench": [RATTATA], "hand": [HAUNTER]}, {"active": GROWLITHE},
        ], turn_number=TURN)
        gastly = state.players[0].active
        evolved = apply_command(state, EvolvePokemon(0, uids(state, 0, "hand", HAUNTER)[0], gastly.pokemon_id))
        ghost = evolved.players[0].active
        self.assertEqual((ghost.pokemon_id, ghost.damage, ghost.energy, evolved.card_def(ghost.card).id), (gastly.pokemon_id, 20, gastly.energy, HAUNTER))
        retreated = apply_command(evolved, Retreat(0, (), evolved.players[0].bench[0].card))
        self.assertEqual(retreated.players[0].bench[0].pokemon_id, gastly.pokemon_id)
        self.assertEqual(retreated.players[0].bench[0].energy, gastly.energy)


if __name__ == "__main__":
    unittest.main()

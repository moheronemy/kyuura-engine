"""v0.17a: 既存のワザの要素だけで実装したカード（モンジャラ・サカキのニャース）。docs/card-selection-v0.17a.md・docs/card-implementation-v0.17a.md。

- モンジャラ（PMCG1-007。p.55）: しめつける（草無）20「コインを投げて「おもて」なら、相手を「マヒ」状態にする。」・どくのこな（草草草）20
  「相手を「どく」状態にする。」。既存の実装（``ParalyzeOnHeads``・``PoisonOpponent``）の登録だけで、解決の基盤・エンジンを変えていない。
- サカキのニャース（PMCG6-063。p.229）: ねこノミ（無。ダメージなし）「コインを投げて「おもて」なら、相手を「こんらん」状態にする。」・ねこキック
  （無無無）30（説明文なし）。ねこノミは既存の要素 ``Status(CONFUSION, local_coin=HEADS)`` の新しい並び（``ConfuseOnHeadsWithoutDamage``。
  ``programs.BUILDERS`` に 1 行）。

順番の根拠: p.309（ワザの手順）・p.320（ワザの要素は書かれた順に処理する。ダメージと効果）・p.321（「ダメージを受けない」状態でもダメージ
以外の効果の要素は有効。ダメージの計算の順番）・p.322（特殊状態の重なり）・p.89（「ダメージを受けたとき」の効果はダメージの処理のあと、
ダメージ以外の効果の前。v0.10 の C-裁定）・p.159・p.160（「とうめい」。v0.9 の T19・T19b・T22）。kyuura の記録 id: PMCG1-007・PMCG6-063
（NEO-2000-OFFICIAL-RULES）。新しい裁定は加えていない（docs/card-implementation-v0.17a.md 3 章）。
"""

from __future__ import annotations

import hashlib
import json
import pickle
import unittest
from collections import Counter

from kyuura_engine import (
    IllegalActionError, Phase, UnsupportedError, UseAttack, apply_command, check_invariants, new_game, state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, read_verification
from kyuura_engine.conditions import CONFUSION, PARALYSIS, POISON
from kyuura_engine.resolution import contract, programs
from kyuura_engine.rng import copy_rng, rng_fingerprint
from tests.helpers import (
    ABRA, BILL, BULBASAUR, DEFENDER, DIGLETT, FIGHTING, FIRE, GASTLY, GIOVANNIS_MEOWTH, GRASS, H, HAUNTER, IVYSAUR, KADABRA, MACHAMP,
    MACHOKE, MACHOP, PLUSPOWER, POTION, PSYCHIC, RATTATA, SWITCH, T, TANGELA, build_test_state, coin_events, coin_results, expand_decklist,
    with_coin_results,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_confusion_games import TERMINAL
from tests.test_dark_wartortle_games_v0_13 import WARTORTLE_DECK
from tests.test_moltres_games_v0_12 import MOLTRES_DECK_A, MOLTRES_DECK_B
from tests.v017_games import full, play_game

SQUEEZE = (TANGELA, 0)  # しめつける
POISON_POWDER = (TANGELA, 1)  # どくのこな
FLEA = (GIOVANNIS_MEOWTH, 0)  # ねこノミ
CAT_KICK = (GIOVANNIS_MEOWTH, 1)  # ねこキック


def tangela(**extra):
    return {"card": TANGELA, "energy": [GRASS, GRASS, GRASS], **extra}


def meowth(**extra):
    return {"card": GIOVANNIS_MEOWTH, "energy": [FIRE, FIRE, FIRE], **extra}


def haunter(**extra):
    return {"card": HAUNTER, "evolved_from": GASTLY, **extra}


def machamp(**extra):
    return {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], **extra}


def board(attacker, defender, turn_number=7, **kwargs):
    return build_test_state([{"active": attacker}, {"active": defender}], turn_number=turn_number, **kwargs)


def kinds(state, since):
    return [e["kind"] for e in state.log[since:] if e["kind"] not in ("turn_end", "pokemon_check", "turn_start", "draw")]


def snapshot(state):
    return state_to_dict(state, format_version=9), rng_fingerprint(state.rng), len(state.log)


class RegistrationTest(unittest.TestCase):
    """登録・分類・要素の並び（新しいカードを v0.13 の約束（resolve・resume）だけで実装していない）。"""

    def test_cards_are_supported_and_playable(self):
        pool = load_card_pool()
        for card in (TANGELA, GIOVANNIS_MEOWTH):
            definition = pool.get(card)
            self.assertTrue(definition.supported, definition.unsupported_reasons)
            self.assertTrue(pool.is_playable(card))
            self.assertTrue(all(a.supported for a in definition.attacks))

    def test_registration_follows_the_latest_description(self):
        """登録の照合（kyuura の写しの文面 text_ja）と、実装がしたがう最新の説明（p.55・p.229）・照合の記録。"""
        records = read_verification()["cards"]
        expected = {
            SQUEEZE: (E.ParalyzeOnHeads, "コインを投げて「おもて」なら、相手を「マヒ」状態にする。", "P43 p.55"),
            POISON_POWDER: (E.PoisonOpponent, "相手を「どく」状態にする。", "P43 p.55"),
            FLEA: (E.ConfuseOnHeadsWithoutDamage, "コインを投げて「おもて」なら、相手を「こんらん」状態にする。", "P43 p.229"),
        }
        for (card, index), (kind, latest, source) in expected.items():
            entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
            self.assertIs(type(entry.effect), kind)
            self.assertEqual((entry.play_text_ja, entry.source), (latest, source))
        self.assertIs(E.DEFAULT_EFFECTS.attack_entry(*CAT_KICK).effect, E.DAMAGE_ONLY)
        self.assertEqual((records[TANGELA]["page"], records[GIOVANNIS_MEOWTH]["page"]), (55, 229))
        self.assertEqual(records[TANGELA]["status"], "一致")
        self.assertEqual(records[GIOVANNIS_MEOWTH]["status"], "一致")

    def test_programs_are_existing_elements(self):
        """要素の並びは既存の要素だけ（Damage・Status）。v0.13 の約束のアダプタ（Contract）ではない。"""
        def program(key):
            return programs.compile_attack(E.DEFAULT_EFFECTS.attack_entry(*key).effect)

        self.assertEqual(program(SQUEEZE), (programs.Damage(programs.OPP, programs.Printed()),
                                            programs.Status(PARALYSIS, local_coin=H, reparalysis_check=True)))
        self.assertEqual(program(POISON_POWDER), (programs.Damage(programs.OPP, programs.Printed()), programs.Status(POISON)))
        self.assertEqual(program(FLEA), (programs.Status(CONFUSION, local_coin=H),))
        self.assertEqual(program(CAT_KICK), (programs.Damage(programs.OPP, programs.Printed()),))
        for key in (SQUEEZE, POISON_POWDER, FLEA, CAT_KICK):
            effect = E.DEFAULT_EFFECTS.attack_entry(*key).effect
            self.assertFalse(contract.is_contract(contract.program_for(effect)))

    def test_new_type_has_no_v0_13_contract(self):
        """ConfuseOnHeadsWithoutDamage は resolve・resume を上書きしない（解決の基盤の要素の並びだけで処理する）。v0.13 の止める関数の型
        （VERIFIED）にも入れない（v0.16c）。"""
        cls = E.ConfuseOnHeadsWithoutDamage
        self.assertIs(cls.resolve, E.AttackEffect.resolve)
        self.assertIs(cls.resume, E.AttackEffect.resume)
        from kyuura_engine.resolution import v013_checks
        self.assertNotIn(cls, v013_checks.VERIFIED)
        self.assertEqual(cls.opponent_effect_elements, programs.opponent_effect_elements(programs.compile_attack(cls())))

    def test_check_rejects_wrong_data(self):
        """ねこノミの実装は、ダメージの目安のあるワザ・説明文のないワザには登録できない。"""
        pool = load_card_pool()
        self.assertEqual(E.ConfuseOnHeadsWithoutDamage().check(pool.get(GIOVANNIS_MEOWTH).attacks[0]), [])
        self.assertTrue(E.ConfuseOnHeadsWithoutDamage().check(pool.get(GIOVANNIS_MEOWTH).attacks[1]))  # ねこキック（30・説明文なし）


class TangelaTest(unittest.TestCase):
    """しめつける・どくのこな（p.55）。ダメージ → コイン → マヒ、ダメージ → どく（p.320 の順番）。"""

    def test_squeeze_heads_and_tails(self):
        for side, paralyzed in ((H, True), (T, False)):
            state = board(tangela(), RATTATA)
            new = apply_command(with_coin_results(state, side), UseAttack(0, 0))
            self.assertEqual(kinds(new, len(state.log))[:3], ["attack", "damage", "coin_flip"])
            self.assertEqual(new.players[1].active.damage, 20)
            self.assertEqual(new.players[1].active.conditions.paralyzed, paralyzed)
            self.assertEqual(coin_results(new, len(state.log)), [side.value])

    def test_poison_powder_has_no_coin(self):
        state = board(tangela(), MACHOP)
        new = apply_command(state, UseAttack(0, 1))
        self.assertEqual(kinds(new, len(state.log))[:3], ["attack", "damage", "special_condition"])
        self.assertEqual(coin_events(new, len(state.log)), [])
        self.assertIsNotNone(new.players[1].active.conditions.poison)

    def test_insufficient_energy_is_rejected_without_change(self):
        state = board({"card": TANGELA, "energy": [GRASS, GRASS]}, RATTATA)  # どくのこなは草 3 個
        before = snapshot(state)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, UseAttack(0, 1))
        self.assertEqual(ctx.exception.code, "INSUFFICIENT_ENERGY")
        self.assertEqual(snapshot(state), before)

    def test_asleep_or_paralyzed_attacker_cannot_declare(self):
        """ねむり・マヒのモンジャラはワザを宣言できない（p.309・p.311。エネルギー・コインの前）。"""
        for status, code in (({"sleep": True}, "POKEMON_ASLEEP"), ({"paralysis": 6}, "POKEMON_PARALYZED")):
            state = board(tangela(**status), RATTATA)
            before = snapshot(state)
            with self.assertRaises(IllegalActionError) as ctx:
                apply_command(state, UseAttack(0, 0))
            self.assertEqual(ctx.exception.code, code)
            self.assertEqual(snapshot(state), before)

    def test_weakness_and_target_knock_out(self):
        """ディグダ（弱点 草）: 20 × 2 = 40 で HP 30 以上になり、効果の対象がいないのでコインを投げない（p.309・p.321）。"""
        state = board(tangela(), DIGLETT)
        new = apply_command(with_coin_results(state, H), UseAttack(0, 0))
        damage = next(e for e in new.log[len(state.log):] if e["kind"] == "damage")
        self.assertEqual((damage["amount"], damage["weakness"]), (40, True))
        self.assertEqual(coin_events(new, len(state.log)), [])
        self.assertIn("knock_out", kinds(new, len(state.log)))

    def test_pluspower_and_defender(self):
        """プラスパワー（p.257。5 段階）で 30。相手のディフェンダー（7 段階）で 0（ダメージを与えなかった）でも、マヒ・どくは効果の要素
        なので与える（p.321。ConfuseOnHeads（v0.3c）と同じ）。"""
        state = board(tangela(trainers=[(PLUSPOWER, 7)]), MACHOP)
        new = apply_command(with_coin_results(state, T), UseAttack(0, 0))
        self.assertEqual(new.players[1].active.damage, 30)
        state = board(tangela(), {"card": MACHOP, "trainers": [(DEFENDER, 7)]})  # 相手が 6 番に使った（次の相手の番 7 の終わりまで）
        new = apply_command(with_coin_results(state, H), UseAttack(0, 0))
        self.assertEqual((new.players[1].active.damage, new.players[1].active.conditions.paralyzed), (0, True))
        new = apply_command(state, UseAttack(0, 1))
        damage = next(e for e in new.log[len(state.log):] if e["kind"] == "damage")
        self.assertEqual((damage["amount"], new.players[1].active.conditions.poison is not None), (0, True))  # 10 はポケモンチェックのどく

    def test_transparency_stops_squeeze_before_any_coin(self):
        """「とうめい」のゴーストに、ダメージ → ワザのコイン → マヒ のワザは T19b（UNRESOLVED_EVADED_EFFECT_COIN）で宣言の前に止まる（v0.9）。"""
        state = board(tangela(), haunter())
        before = snapshot(state)
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, "UNRESOLVED_EVADED_EFFECT_COIN")
        self.assertEqual(snapshot(state), before)

    def test_transparency_with_poison_powder(self):
        """どくのこな（コインなし）は「とうめい」のコイン 1 回（T4）: 「おもて」ならダメージもどくも受けない、「うら」なら両方（A4-1）。"""
        for side, damaged in ((H, False), (T, True)):
            state = board(tangela(), haunter())
            new = apply_command(with_coin_results(state, side), UseAttack(0, 1))
            target = new.players[1].active
            self.assertEqual((target.damage > 0, target.conditions.poison is not None), (damaged, damaged))
            self.assertEqual(len(coin_events(new, len(state.log))), 1)

    def test_counterattack_comes_before_paralysis(self):
        """カイリキーの「はんげき」の 10 は、ダメージのあと、ワザのコイン・マヒの前（p.89。v0.10）。"""
        state = board(tangela(), machamp())
        new = apply_command(with_coin_results(state, H), UseAttack(0, 0))
        self.assertEqual(kinds(new, len(state.log))[:5], ["attack", "damage", "counterattack", "coin_flip", "special_condition"])
        self.assertEqual(new.players[0].active.damage, 10)

    def test_double_knock_out_with_counterattack_stops(self):
        """モンジャラ（HP 50）が 40、カイリキー（HP 100）が 80: 20 でカイリキー、はんげきの 10 でモンジャラがきぜつしうるので C18
        （UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT）で宣言の前に止まる。"""
        state = board(tangela(damage=40), machamp(damage=80))
        before = snapshot(state)
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, UseAttack(0, 1))
        self.assertEqual(ctx.exception.code, "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")
        self.assertEqual(snapshot(state), before)

    def test_reparalysis_keeps_the_recovery_turn(self):
        """しめつけるは既存の ParalyzeOnHeads（マヒの再付与の確認つき。v0.3b）。相手の番（6）にマヒ状態になった相手を、この番（7）に再び
        マヒにしても回復する番（8）は変わらないので止めず、二重のマヒにはならない（p.322）。回復する番が変わる場合は相手のワザでは起こらない
        （v0.3b の paralysis_problem の説明。マヒ状態のポケモンは次の自分の番の終わりに回復する）。"""
        state = board(tangela(), {"card": MACHOP, "paralysis": 6})
        new = apply_command(with_coin_results(state, H), UseAttack(0, 0))
        self.assertTrue(new.players[1].active.conditions.paralyzed)
        self.assertEqual(new.players[1].active.conditions.exclusive.turn, 6)


class GiovannisMeowthTest(unittest.TestCase):
    """ねこノミ（p.229）。ダメージの要素はなく、コイン → 「おもて」なら（「とうめい」の評価 →）こんらん。"""

    def test_heads_and_tails(self):
        for side, confused in ((H, True), (T, False)):
            state = board(meowth(), RATTATA)
            new = apply_command(with_coin_results(state, side), UseAttack(0, 0))
            self.assertNotIn("damage", kinds(new, len(state.log)))
            self.assertEqual(new.players[1].active.damage, 0)
            self.assertEqual(new.players[1].active.conditions.confused, confused)

    def test_condition_replacement_and_poison(self):
        """ねむりはこんらんに置きかわり、どくはそのまま（p.322）。"""
        state = board(meowth(), {"card": RATTATA, "sleep": True, "poison": 10})
        new = apply_command(with_coin_results(state, H), UseAttack(0, 0))
        conditions = new.players[1].active.conditions
        self.assertEqual((conditions.confused, conditions.asleep, conditions.poison is not None), (True, False, True))

    def test_transparency_coin_order(self):
        """ゴースト: ワザのコインを先に投げ、「おもて」のときだけ、こんらんを与える直前に「とうめい」のコイン（ゴースト側。T19・T22・T33）。
        ダメージの要素がないので T19b は起こらない（宣言は止まらない）。"""
        for sides, confused, coins in (((H, H), False, 2), ((H, T), True, 2), ((T,), False, 1)):
            state = board(meowth(), haunter())
            new = apply_command(with_coin_results(state, *sides), UseAttack(0, 0))
            events = coin_events(new, len(state.log))
            self.assertEqual([e["player"] for e in events], [0, 1][:coins])
            self.assertEqual(new.players[1].active.conditions.confused, confused)

    def test_prevented_damage_does_not_stop_the_effect(self):
        """「ダメージを受けない」状態（かたまる）の相手でも、ダメージ以外の効果の要素は有効（p.321）。"""
        state = board(meowth(), {"card": RATTATA, "prevent_damage": 6})
        new = apply_command(with_coin_results(state, H), UseAttack(0, 0))
        self.assertTrue(new.players[1].active.conditions.confused)

    def test_no_damage_means_no_counterattack(self):
        state = board(meowth(), machamp())
        new = apply_command(with_coin_results(state, H), UseAttack(0, 0))
        self.assertNotIn("counterattack", kinds(new, len(state.log)))
        self.assertTrue(new.players[1].active.conditions.confused)

    def test_confused_meowth(self):
        """こんらんのサカキのニャース: こんらんのコインが「うら」なら自分に 20（無色・弱点 闘なので 20。p.322）で、ねこノミのコインは投げない。"""
        state = board(meowth(confusion=True), RATTATA)
        new = apply_command(with_coin_results(state, T), UseAttack(0, 0))
        self.assertEqual((new.players[0].active.damage, len(coin_events(new, len(state.log)))), (20, 1))
        new = apply_command(with_coin_results(state, H, H), UseAttack(0, 0))
        self.assertTrue(new.players[1].active.conditions.confused)

    def test_meowth_weakness_and_resistance_as_defender(self):
        """サカキのニャース（弱点 闘・抵抗力 超 −30）が受けるダメージ（カードのデータの値。p.321 の 3・4 段階）。"""
        state = board({"card": MACHOP, "energy": [FIGHTING]}, GIOVANNIS_MEOWTH)
        new = apply_command(state, UseAttack(0, 0))
        self.assertEqual(new.players[1].active.damage, 40)
        state = board({"card": KADABRA, "evolved_from": ABRA, "energy": [PSYCHIC, PSYCHIC, PSYCHIC]}, GIOVANNIS_MEOWTH)
        new = apply_command(state, UseAttack(0, 1))  # ちょうねんりき 50 − 30
        self.assertEqual(new.players[1].active.damage, 20)

    def test_illegal_commands_are_atomic(self):
        state = board(meowth(), RATTATA)
        before = snapshot(state)
        for command in (UseAttack(1, 0), UseAttack(0, 2)):
            with self.assertRaises(IllegalActionError):
                apply_command(state, command)
            self.assertEqual(snapshot(state), before)


# ---------------------------------------------------------------- 正式な開始（new_game）からの対戦

NEW_CARDS_DECK = expand_decklist({
    TANGELA: 4, GIOVANNIS_MEOWTH: 4, BULBASAUR: 3, IVYSAUR: 2, SWITCH: 2, POTION: 2, BILL: 4, DEFENDER: 2, PLUSPOWER: 2, GRASS: 35,
})
SEEDS = tuple(range(80))
HALTED = {14: "UNRESOLVED_MULLIGAN_COMPENSATION", 27: "UNRESOLVED_MULLIGAN_COMPENSATION"}  # 対戦準備の既存の未解決の裁定（v0.1 から）


def decks(seed):
    """seed を 4 で割った余りで相手（炎（モンジャラの弱点）・いろいろなワザ（はんげき・とうめい・かがくへんかガス・こんじょう…）・わるいカメール）、
    2 で割った余りで席を決める。"""
    opponent = (MOLTRES_DECK_A, MOLTRES_DECK_B, MOLTRES_DECK_B, WARTORTLE_DECK)[seed % 4]
    return (NEW_CARDS_DECK, opponent) if seed % 2 == 0 else (opponent, NEW_CARDS_DECK)


def count(state):
    counted = Counter()
    for e in state.log:
        if e["kind"] == "special_condition" and e.get("effect") in ("PMCG1-007#0", "PMCG1-007#1", "PMCG6-063#0"):
            counted[f"condition_{e['effect']}_{e['condition']}"] += 1
        elif e["kind"] == "evade_check" and e.get("effect") in ("PMCG1-007#1", "PMCG6-063#0"):
            counted[f"evade_check_{e['effect']}_{e['element']}"] += 1
        elif e["kind"] == "counterattack" and e.get("effect", "").startswith(("PMCG1-007", "PMCG6-063")):
            counted["counterattack_on_new_cards"] += 1
    counted[f"phase_{state.phase.value}"] += 1
    return counted


class NaturalGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_game(decks(seed), seed, cure=seed % 3 != 0) for seed in SEEDS}

    def test_new_attacks_are_used_and_every_game_ends(self):
        """自然な対戦の中で、4 つのワザを使い、マヒ・どく・こんらんを与え、「とうめい」の評価・「はんげき」・T19b の停止が起こる（1 回も
        起こらない試験を成功と数えない）。どの対戦も勝敗が決まる。"""
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(observed)
            counted.update(count(state))
        for key in ("attack_PMCG1-007#0", "attack_PMCG1-007#1", "attack_PMCG6-063#0", "attack_PMCG6-063#1",
                    "condition_PMCG1-007#0_paralysis", "condition_PMCG1-007#1_poison", "condition_PMCG6-063#0_confusion",
                    "evade_check_PMCG6-063#0_confusion", "evade_check_PMCG1-007#1_damage", "counterattack_on_new_cards",
                    "stopped_attack_UNRESOLVED_EVADED_EFFECT_COIN"):
            self.assertGreater(counted[key], 0, (key, dict(counted)))
        self.assertEqual(counted["phase_game_over"], len(SEEDS) - len(HALTED), dict(counted))
        halted = {seed: state.halt.code for seed, (state, _, _) in self.games.items() if state.phase is Phase.HALTED}
        self.assertEqual(halted, HALTED)

    def test_invariants_logs_and_serialization(self):
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_randomness_is_only_coins(self):
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                expected = copy_rng(new_game(*decks(seed), seed).rng)
                for event in coin_events(state):
                    self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
                self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected))

    def test_replay_and_save_restore(self):
        """同じ seed・同じ操作の列で同じ結果。新しいカードのワザを使う直前に保存（pickle）して再開しても同じ。"""
        restored = 0
        for seed, (state, commands, _) in self.games.items():
            replayed = new_game(*decks(seed), seed)
            for command in commands:
                if isinstance(command, UseAttack) and replayed.card_def(replayed.players[command.player].active.card).id in (TANGELA, GIOVANNIS_MEOWTH):
                    replayed = pickle.loads(pickle.dumps(replayed))
                    restored += 1
                replayed = apply_command(replayed, command)
            with self.subTest(seed=seed):
                self.assertEqual(full(replayed), full(state))
        self.assertGreater(restored, 0)


# しめつける・どくのこな・ねこノミ・ねこキックをすべて使う対戦（v0.17a）。(受け付けた操作の数, 最後の番, 段階, 書き出しの指紋)
GOLDEN_SEED = 3
GOLDEN = (77, 21, Phase.GAME_OVER, "08c3ced3c24048b25a4cbc6901a2ff5e493da2acf2bd34a527ea502a1bbc292e")


class GoldenGameTest(unittest.TestCase):
    """GOLDEN_SEED の対戦の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.17a）。手順・デッキ・乱数の使い方が変わると変わる。"""

    def test_seed(self):
        state, commands, observed = play_game(decks(GOLDEN_SEED), GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)
        self.assertTrue(all(observed[f"attack_{key}"] > 0 for key in ("PMCG1-007#0", "PMCG1-007#1", "PMCG6-063#0", "PMCG6-063#1")))
        data = full(state)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.13")
        digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        self.assertEqual((len(commands), state.turn_number, state.phase, digest), GOLDEN)


if __name__ == "__main__":
    unittest.main()

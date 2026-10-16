"""v0.27: ストライク（PMCG2-017。第2弾ポケモンジャングル）の「つるぎのまい」と「きりさく」。docs/scyther-v0.27.md（SC1〜SC22）。

- 「つるぎのまい」（草）: 最新の説明「次の自分の番、このカードが使う「きりさく」のダメージは「60」になる。」（p.56・p.321）。ワザを使ったポケモン
  自身に与える持続する効果（``state.NextTurnAttackDamage``）。はたらくのは次の自分の番（与えた番 + 2）で、その番の終わりに消える（p.57 のワザ解説
  「効果の持続：次の自分の番の最後」）。ベンチにもどると消える（p.57「突風」などで入れ替えられると消える・p.311・p.322）。
- ダメージは p.321 の 2 段階（「ワザを使うポケモンの持っている「ダメージを変更する効果」」。例に「「ストライク」のワザ「つるぎのまい」」、図に
  「ワザを使うポケモンの持続する状態の効果」）で 60 にする（``damage.SET``）。弱点・抵抗力・プラスパワー・ディフェンダーはそのあとの段階。
  印刷の文面（kyuura の写し）の「2倍」・英語版の文面では処理を決めない。
- 「きりさく」（無無無）30: 説明文なし（``DamageOnly``）。

根拠のページ: p.56（カード・最新の説明・解説）・p.57（ワザ解説）・p.321（ダメージ計算の順番の 2 段階）。一般の規定は既存の記録を再利用した
（持続する効果の消える契機 p.310・p.311・p.322・p.323（docs/persistent-effects-v0.4b.md）、こんらん p.309・p.322（v0.3c）、ねむり・マヒ
p.309・p.311（v0.3b）、p.321 の 3〜8 段階・「ダメージを受けない」状態（v0.2c・v0.2e・v0.4b））。kyuura の記録 id: PMCG2-017
（NEO-2000-OFFICIAL-RULES）。
"""

from __future__ import annotations

import dataclasses
import unittest

from kyuura_engine import (
    EndTurn, IllegalActionError, PlayTrainer, ResolveDecision, Retreat, UnsupportedError, UseAttack, apply_command, check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, pool_from_extract, read_extract, read_verification
from kyuura_engine.coins import CoinSide
from kyuura_engine.damage import ADD, SET, DamageModifier, calculate_attack_damage
from kyuura_engine.persistent import next_turn_attack_damage
from kyuura_engine.resolution import PREFLIGHT_MODES, contract, programs
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import NextTurnAttackDamage
from tests.helpers import (
    BUTTERFREE, CATERPIE, DEFENDER, DIGLETT, FIGHTING, FIRE, GRASS, GUST, HITMONCHAN, KAKUNA, MACHAMP, MACHOKE, MACHOP, METAPOD, PARAS, PARASECT,
    PLUSPOWER, RATTATA, SCYTHER, SWITCH, WEEDLE, apply_kernel, build_test_state, with_coin_results,
)
from tests.log_audit import serialization_problems

SWORDS_DANCE = E.AttackKey(SCYTHER, 0)
SLASH = E.AttackKey(SCYTHER, 1)
TURN = 7  # プレイヤー 0 の番（先攻はプレイヤー 0）
DOUBLE_KO = "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT"


def scyther(**extra):
    """「つるぎのまい」（草）と「きりさく」（無無無）のどちらも使えるストライク。"""
    return {"card": SCYTHER, "energy": [GRASS, FIGHTING, FIGHTING], **extra}


def boosted(**extra):
    """TURN の 2 番前（TURN - 2）に「つるぎのまい」を使ったストライク（効果は TURN にはたらく）。"""
    return scyther(next_turn_attack_damage=(TURN - 2, 0, 1, 60), **extra)


def board(mine, theirs, *, mine_bench=None, theirs_bench=None, mine_hand=(), theirs_hand=(), turn=TURN, **kwargs):
    return build_test_state([
        {"active": mine, "bench": list(mine_bench) if mine_bench is not None else [RATTATA], "hand": list(mine_hand)},
        {"active": theirs, "bench": list(theirs_bench) if theirs_bench is not None else [RATTATA], "hand": list(theirs_hand)},
    ], turn_number=turn, current_player=(turn + 1) % 2, **kwargs)


def events(state, since, kind):
    return [dict(e) for e in state.log[since:] if e["kind"] == kind]


def snapshot(state):
    return state_to_dict(state, format_version=9), rng_fingerprint(state.rng), len(state.log)


def last_damage(state, since):
    damage = events(state, since, "damage")
    return damage[-1] if damage else None


def in_hand(state, player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)


def effects_of(pokemon):
    return [e for e in pokemon.persistent_effects if isinstance(e, NextTurnAttackDamage)]


def swords_dance_then_opponent_turn(state):
    """TURN に「つるぎのまい」、相手の番（TURN + 1）は何もしないで終える。"""
    state = apply_command(state, UseAttack(0, 0))
    return apply_command(state, EndTurn(1))


class RegistrationTest(unittest.TestCase):
    def test_card_data_matches_the_book(self):
        """p.56 の図版: たね・HP 70・草・弱点 炎・抵抗力 闘 -30・にげる 0。つるぎのまい（草。ダメージなし）・きりさく（無無無）30。"""
        definition = load_card_pool().get(SCYTHER)
        self.assertTrue(definition.supported and load_card_pool().is_playable(SCYTHER))
        self.assertEqual((definition.stage, definition.hp, definition.pokemon_type, definition.weakness, definition.resistance,
                          definition.resistance_value, definition.retreat_cost),
                         ("basic", 70, EnergyType.GRASS, EnergyType.FIRE, EnergyType.FIGHTING, 30, 0))
        dance, slash = definition.attacks
        self.assertEqual((dance.name_ja, dance.cost, dance.damage), ("つるぎのまい", (EnergyType.GRASS,), None))
        self.assertEqual((slash.name_ja, slash.cost, slash.damage, slash.text_ja), ("きりさく", (EnergyType.COLORLESS,) * 3, 30, None))

    def test_registration_follows_the_latest_description(self):
        """「つるぎのまい」の登録は最新の説明（p.56）・ダメージが変わるワザの位置（1）と名前・変えたあとのダメージ（60）を持つ。印刷の文面（「2倍」）
        は照合（text_ja）だけ。「きりさく」は説明文のないワザ。要素の並びは新しい要素 1 つ（v0.13 の約束のアダプタではない）。"""
        record = read_verification()["cards"][SCYTHER]
        entry = E.DEFAULT_EFFECTS.attack_entry(SCYTHER, 0)
        self.assertEqual(entry.effect, E.SetNextTurnAttackDamage(target_attack_index=1, target_attack_name="きりさく", damage=60))
        self.assertEqual((entry.play_text_ja, entry.source), (record["latest_description_ja"], "P43 p.56"))
        self.assertIn("「60」になる", entry.play_text_ja)
        self.assertIn("2倍", entry.text_ja)
        self.assertEqual(entry.effect.next_turn_terms(), (1, 60))
        self.assertIs(E.DEFAULT_EFFECTS.attack_entry(SCYTHER, 1).effect, E.DAMAGE_ONLY)
        program = programs.compile_attack(entry.effect)
        self.assertEqual(program, (programs.SelfNextTurnAttackDamage(1, 60),))
        self.assertFalse(contract.is_contract(contract.program_for(entry.effect)))
        self.assertIs(E.SetNextTurnAttackDamage.resolve, E.AttackEffect.resolve)
        self.assertEqual(programs.opponent_effect_elements(program), ())
        self.assertEqual(record["status"], "不一致あり")
        self.assertEqual((record["page"], record["pdf_page"], record["rules_page"], record["commentary_page"]), (56, 58, 321, 57))

    def test_registration_must_point_at_the_right_attack(self):
        """ダメージが変わるワザは位置で指し、名前と形（説明のない、ダメージの目安の数字だけのワザ）を登録のときに確かめる（card_problems）。
        合わない登録のカードは未対応（効果のないものとして扱わない）。名前で探して、ほかのワザを変えることはない。"""
        cases = {
            "自分自身": E.SetNextTurnAttackDamage(0, "つるぎのまい", 60),
            "ない位置": E.SetNextTurnAttackDamage(5, "きりさく", 60),
            "名前が違う": E.SetNextTurnAttackDamage(1, "スラッシュダウン", 60),
        }
        for name, effect in cases.items():
            with self.subTest(case=name):
                entry = dataclasses.replace(E.DEFAULT_EFFECTS.attack_entry(SCYTHER, 0), effect=effect)
                registry = E.DEFAULT_EFFECTS.with_attacks("test", {SWORDS_DANCE: entry})
                definition = pool_from_extract(read_extract(), registry).get(SCYTHER)
                self.assertFalse(definition.supported)
                self.assertFalse(definition.attacks[0].supported)
                self.assertIn("ダメージが変わるワザ", definition.attacks[0].unsupported_reason)
        # パラセクトの「きりさく」（同じ名前の説明のないワザ）は、DamageOnly のまま（「つるぎのまい」の効果の対象はストライク自身だけ）
        self.assertIs(E.DEFAULT_EFFECTS.attack_entry(PARASECT, 1).effect, E.DAMAGE_ONLY)
        self.assertEqual(load_card_pool().get(PARASECT).attacks[1].name_ja, "きりさく")

    def test_invalid_terms_are_rejected(self):
        for kwargs in ({"target_attack_index": -1}, {"damage": 55}, {"damage": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                E.SetNextTurnAttackDamage(**{"target_attack_index": 1, "target_attack_name": "きりさく", "damage": 60, **kwargs})


class SwordsDanceTest(unittest.TestCase):
    def test_slash_without_the_effect(self):
        """効果がなければ「きりさく」は 30（2 段階の記録はない）。"""
        state = board(scyther(), {"card": RATTATA})
        after = apply_command(state, UseAttack(0, 1))
        damage = last_damage(after, len(state.log))
        self.assertEqual((damage["amount"], damage["steps"]), (30, (("1 基本となる計算", 30),)))
        self.assertNotIn("damage_set", damage)

    def test_swords_dance_gives_the_effect_for_the_next_own_turn(self):
        """「つるぎのまい」: ダメージはなく、自分に効果（与えた番 TURN、はたらく番 TURN + 2）。番は終わる（p.309）。"""
        state = board(scyther(), {"card": RATTATA})
        after = apply_command(state, UseAttack(0, 0))
        mine = after.players[0].active
        self.assertEqual(mine.persistent_effects, (NextTurnAttackDamage(mine.card, 0, TURN, TURN + 2, 0, 1, 60),))
        added = events(after, len(state.log), "persistent_effect_added")
        self.assertEqual([(e["turn"], e["active_turn"], e["persistent_effect"], e["effect"]) for e in added],
                         [(TURN, TURN + 2, "next_turn_attack_damage", str(SWORDS_DANCE))])
        self.assertEqual(events(after, len(state.log), "damage"), [])
        self.assertEqual((after.turn_number, after.current_player), (TURN + 1, 1))
        self.assertEqual(after.players[1].active.damage, 0)

    def test_nothing_happens_on_the_opponent_turn(self):
        """あいだの相手の番には効果ははたらかない（問い合わせは None）が、残っている（「自分の番、相手の番、自分の番と持続」。p.57）。"""
        state = apply_command(board(scyther(), {"card": RATTATA}), UseAttack(0, 0))
        mine = state.players[0].active
        self.assertIsNone(next_turn_attack_damage(state, mine, 1))
        self.assertEqual(E.attack_damage_modifiers(state, mine, state.players[1].active, attack=SLASH), ())
        after = apply_command(state, EndTurn(1))
        self.assertEqual(len(effects_of(after.players[0].active)), 1)
        self.assertEqual(events(after, len(state.log), "persistent_effect_removed"), [])

    def test_boosted_slash_on_the_next_own_turn(self):
        """次の自分の番の「きりさく」は、p.321 の 2 段階で 60（30 に足す・掛けるのではなく「60」にする）。その番の終わりに効果は消える（p.57）。
        相手はきぜつしないエビワラー（HP 70。弱点・抵抗力は草でない）にして、番の終わりまで進める。"""
        state = swords_dance_then_opponent_turn(board(scyther(), {"card": HITMONCHAN}))
        self.assertEqual(state.turn_number, TURN + 2)
        mine = state.players[0].active
        self.assertIsNotNone(next_turn_attack_damage(state, mine, 1))
        after = apply_command(state, UseAttack(0, 1))
        damage = last_damage(after, len(state.log))
        self.assertEqual(damage["amount"], 60)
        self.assertEqual(damage["steps"], (("1 基本となる計算", 30), ("2 つるぎのまい", 60)))
        self.assertEqual(damage["damage_set"], ((2, mine.card, 60),))
        self.assertNotIn("modifiers", damage)
        removed = events(after, len(state.log), "persistent_effect_removed")
        self.assertEqual([(e["turn"], e["reason"], e["created_turn"]) for e in removed], [(TURN + 2, "expired", TURN)])
        self.assertEqual(after.players[0].active.persistent_effects, ())

    def test_effect_expires_when_not_attacking(self):
        """次の自分の番にワザを使わなくても、その番の終わりに消える。その次の自分の番の「きりさく」は 30。"""
        state = swords_dance_then_opponent_turn(board(scyther(), {"card": RATTATA}))
        state = apply_command(state, EndTurn(0))
        self.assertEqual(state.players[0].active.persistent_effects, ())
        self.assertEqual([e["reason"] for e in events(state, 0, "persistent_effect_removed")], ["expired"])
        state = apply_command(state, EndTurn(1))
        before = len(state.log)
        after = apply_command(state, UseAttack(0, 1))
        self.assertEqual(last_damage(after, before)["amount"], 30)

    def test_swords_dance_again_on_the_boosted_turn(self):
        """はたらく番にもう一度「つるぎのまい」を使うと、新しい効果（はたらく番 + 2）を与え、前の効果はその番の終わりに消える。重ねて大きく
        ならない（どの番にもはたらく効果は 1 つ）。その次の自分の番の「きりさく」は 60。"""
        state = swords_dance_then_opponent_turn(board(scyther(), {"card": RATTATA}))
        before = len(state.log)
        state = apply_command(state, UseAttack(0, 0))
        log = [(e["kind"], e.get("turn"), e.get("created_turn")) for e in state.log[before:]
               if e["kind"] in ("persistent_effect_added", "persistent_effect_removed")]
        self.assertEqual(log, [("persistent_effect_added", TURN + 2, None), ("persistent_effect_removed", TURN + 2, TURN)])
        mine = state.players[0].active
        self.assertEqual([(e.created_turn, e.active_turn) for e in mine.persistent_effects], [(TURN + 2, TURN + 4)])
        self.assertEqual(check_invariants(state), [])
        state = apply_command(state, EndTurn(1))
        before = len(state.log)
        after = apply_command(state, UseAttack(0, 1))
        self.assertEqual(last_damage(after, before)["amount"], 60)

    def test_two_effects_with_different_turns_are_allowed(self):
        """はたらく番に 2 つ目を使った直後の形（同じ種類・はたらく番が違う 2 つ）は不変条件に合う。同じはたらく番の 2 つは違反（盤面を直接作った）。"""
        state = board(boosted(), {"card": RATTATA})
        mine = state.players[0].active
        second = NextTurnAttackDamage(mine.card, 0, TURN, TURN + 2, 0, 1, 60)
        mine.persistent_effects = (*mine.persistent_effects, second)
        state.add_event("persistent_effect_added", player=0, pokemon=mine.card, pokemon_id=mine.pokemon_id, persistent_effect=second.kind,
                        source_card=mine.card, source_player=0, active_turn=TURN + 2, effect=str(SWORDS_DANCE))
        self.assertEqual(check_invariants(state), [])
        duplicate = NextTurnAttackDamage(mine.card, 0, TURN, TURN + 2, 0, 1, 60)
        mine.persistent_effects = (*mine.persistent_effects, duplicate)
        self.assertTrue(any("同じ種類の効果が重なっている" in p for p in check_invariants(state)))

    def test_only_this_scythers_slash_is_changed(self):
        """変わるのは、効果を与えたカードの 1 番目のワザ（きりさく）だけ。同じポケモンの「つるぎのまい」・同じ名前のパラセクトの「きりさく」
        （ワザのカード id が違う）は変えない（名前で探さない）。"""
        state = board(boosted(), {"card": RATTATA})
        mine, theirs = state.players[0].active, state.players[1].active
        found = E.attack_damage_modifiers(state, mine, theirs, attack=SLASH)
        self.assertEqual(found, (DamageModifier(2, 60, "つるぎのまい", mine.card, SET),))
        self.assertEqual(E.attack_damage_modifiers(state, mine, theirs, attack=SWORDS_DANCE), ())
        self.assertEqual(E.attack_damage_modifiers(state, mine, theirs, attack=E.AttackKey(PARASECT, 1)), ())
        self.assertEqual(E.attack_damage_modifiers(state, mine, theirs), ())  # ワザを渡さない呼び出し（こんらんの確認）は v0.26 と同じ

    def test_other_scyther_does_not_get_the_effect(self):
        """効果はワザを使ったポケモン自身だけ（p.57「効果の対象：ワザを使ったポケモン自身」）。にげてベンチにもどると消え（p.311・p.322）、
        かわりにバトル場に出た別のストライクの「きりさく」は 30。"""
        state = swords_dance_then_opponent_turn(board(scyther(), {"card": RATTATA}, mine_bench=[scyther()]))
        old, other = state.players[0].active, state.players[0].bench[0]
        before = len(state.log)
        state = apply_command(state, Retreat(0, (), other.card))  # にげる 0
        removed = events(state, before, "persistent_effect_removed")
        self.assertEqual([(e["pokemon_id"], e["reason"]) for e in removed], [(old.pokemon_id, "retreat")])
        self.assertTrue(all(not p.persistent_effects for p in state.players[0].in_play()))
        self.assertIs(state.players[0].active.card, other.card)
        before = len(state.log)
        after = apply_command(state, UseAttack(0, 1))
        self.assertEqual(last_damage(after, before)["amount"], 30)

    def test_switch_removes_the_effect(self):
        """ポケモンいれかえでベンチにもどると消える（理由 switch。p.322）。"""
        state = swords_dance_then_opponent_turn(board(scyther(), {"card": RATTATA}, mine_hand=[SWITCH]))
        state = apply_command(state, PlayTrainer(0, in_hand(state, 0, SWITCH)))
        before = len(state.log)
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.decision.options[0],)))
        self.assertEqual([e["reason"] for e in events(state, before, "persistent_effect_removed")], ["switch"])
        self.assertTrue(all(not effects_of(p) for p in state.players[0].in_play()))

    def test_opponent_gust_removes_the_effect(self):
        """次の相手の番に、相手の突風で相手のベンチのポケモンと入れ替えられると消える（p.57 のワザ解説の例そのもの）。ログの持ち主はストライクの
        持ち主（v0.21）。"""
        state = apply_command(board(scyther(), {"card": RATTATA}, theirs_hand=[GUST]), UseAttack(0, 0))
        state = apply_command(state, PlayTrainer(1, in_hand(state, 1, GUST)))
        target = state.decision.options[0]
        before = len(state.log)
        state = apply_command(state, ResolveDecision(1, state.decision.id, (target,)))
        removed = events(state, before, "persistent_effect_removed")
        self.assertEqual([(e["player"], e["reason"]) for e in removed], [(0, "switch")])
        self.assertTrue(all(not effects_of(p) for p in state.players[0].in_play()))

    def test_forced_switch_removes_the_effect(self):
        """相手のワザの効果（バタフリーの「ふきとばし」）でベンチにもどされても消える（理由 forced_switch。p.311・p.322）。"""
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}
        state = apply_command(board(scyther(), butterfree), UseAttack(0, 0))
        state = apply_command(state, UseAttack(1, 0))
        if state.decision is not None:  # 相手（ストライクの持ち主）が控えを選ぶ
            state = apply_command(state, ResolveDecision(0, state.decision.id, (state.decision.options[0],)))
        reasons = [e["reason"] for e in events(state, 0, "persistent_effect_removed")]
        self.assertEqual(reasons, ["forced_switch"])
        self.assertTrue(all(not effects_of(p) for p in state.players[0].in_play()))

    def test_knock_out_removes_the_effect(self):
        """次の相手の番にきぜつしたら、効果も消える（p.322）。"""
        state = apply_command(board(scyther(damage=60), {"card": RATTATA, "energy": [FIRE]}), UseAttack(0, 0))
        state = apply_command(state, UseAttack(1, 0))  # かみつく 20
        reasons = [e["reason"] for e in events(state, 0, "persistent_effect_removed")]
        self.assertEqual(reasons, ["knock_out"])


class ConditionTest(unittest.TestCase):
    def test_sleep_and_paralysis_block_the_boosted_slash(self):
        """ねむり・マヒでワザを宣言できない（p.309・p.311）。拒否で状態・乱数・ログは変わらない。効果は消えず（特殊状態では消えない。p.322）、
        その番の終わりに期限で消える。"""
        for extra, code in (({"sleep": True}, "POKEMON_ASLEEP"), ({"paralysis": TURN - 1}, "POKEMON_PARALYZED")):
            with self.subTest(code=code):
                state = board(boosted(**extra), {"card": RATTATA})
                before = snapshot(state)
                with self.assertRaises(IllegalActionError) as ctx:
                    apply_command(state, UseAttack(0, 1))
                self.assertEqual(ctx.exception.code, code)
                self.assertEqual(snapshot(state), before)
                after = apply_command(state, EndTurn(0))
                self.assertEqual([e["reason"] for e in events(after, len(state.log), "persistent_effect_removed")], ["expired"])

    def test_poison_does_not_matter(self):
        state = board(boosted(poison=10), {"card": RATTATA})
        after = apply_command(state, UseAttack(0, 1))
        self.assertEqual(last_damage(after, len(state.log))["amount"], 60)

    def test_confused_boosted_slash(self):
        """こんらんの「きりさく」: 「おもて」なら 60。「うら」ならワザの処理をせず、自分に 20（弱点・抵抗力だけ。「きりさく」のダメージではない
        ので「つるぎのまい」は関係しない。p.309 の手順 5）。どちらでも効果はその番の終わりに消える。効果があっても、こんらんの 20 の
        プラスパワー・ディフェンダーの問い（UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS）にはならない。"""
        state = board(boosted(confusion=True), {"card": HITMONCHAN})  # 60 できぜつしない相手（番の終わりまで進む）
        heads = apply_command(with_coin_results(state, CoinSide.HEADS), UseAttack(0, 1))
        self.assertEqual(last_damage(heads, len(state.log))["amount"], 60)
        tails = apply_command(with_coin_results(state, CoinSide.TAILS), UseAttack(0, 1))
        self.assertIsNone(last_damage(tails, len(state.log)))
        self.assertEqual([e["amount"] for e in events(tails, len(state.log), "confusion_damage")], [20])
        for after in (heads, tails):
            self.assertEqual([e["reason"] for e in events(after, len(state.log), "persistent_effect_removed")], ["expired"])

    def test_confused_swords_dance(self):
        """こんらんの「つるぎのまい」: 「うら」ならワザの処理をしないので効果はない（成立しなかったワザで効果だけを付けない。p.309 の手順 5）。
        「おもて」なら効果を与える。"""
        state = board(scyther(confusion=True), {"card": RATTATA})
        tails = apply_command(with_coin_results(state, CoinSide.TAILS), UseAttack(0, 0))
        self.assertEqual(events(tails, len(state.log), "persistent_effect_added"), [])
        self.assertEqual(tails.players[0].active.persistent_effects, ())
        self.assertEqual(len(events(tails, len(state.log), "confusion_damage")), 1)
        heads = apply_command(with_coin_results(state, CoinSide.HEADS), UseAttack(0, 0))
        self.assertEqual(len(effects_of(heads.players[0].active)), 1)

    def test_rejected_swords_dance_gives_nothing(self):
        """宣言できない「つるぎのまい」（エネルギー不足・ねむり・マヒ）は拒否し、効果を与えない。状態・乱数・ログは変わらない。"""
        cases = (({"energy": [FIGHTING] * 3}, "INSUFFICIENT_ENERGY"), ({"sleep": True}, "POKEMON_ASLEEP"),
                 ({"paralysis": TURN - 1}, "POKEMON_PARALYZED"))
        for extra, code in cases:
            with self.subTest(code=code):
                state = board(scyther(**extra), {"card": RATTATA})
                before = snapshot(state)
                with self.assertRaises(IllegalActionError) as ctx:
                    apply_command(state, UseAttack(0, 0))
                self.assertEqual(ctx.exception.code, code)
                self.assertEqual(snapshot(state), before)

    def test_caller_state_is_not_changed(self):
        state = board(scyther(), {"card": RATTATA})
        before = snapshot(state)
        apply_command(state, UseAttack(0, 0))
        self.assertEqual(snapshot(state), before)
        boosted_state = board(boosted(), {"card": RATTATA})
        before = snapshot(boosted_state)
        apply_command(boosted_state, UseAttack(0, 1))
        self.assertEqual(snapshot(boosted_state), before)


class DamageOrderTest(unittest.TestCase):
    def test_weakness_after_step_2(self):
        """弱点（3 段階）は 2 段階の 60 のあと: 60 × 2 = 120（ディグダの弱点は草）。最終ダメージ全体を 2 倍にする計算ではない。"""
        state = board(boosted(), {"card": DIGLETT})
        after = apply_command(state, UseAttack(0, 1))
        damage = last_damage(after, len(state.log))
        self.assertEqual(damage["steps"], (("1 基本となる計算", 30), ("2 つるぎのまい", 60), ("3 弱点", 120)))
        self.assertEqual((damage["amount"], damage["weakness"]), (120, True))

    def test_pluspower_and_defender(self):
        """プラスパワー（5 段階 +10）・ディフェンダー（7 段階 -20）は 2 段階のあと。弱点なし: 60 + 10 - 20 = 50、弱点あり: 120 + 10 - 20 = 110。"""
        for defender_card, expected in ((RATTATA, 50), (DIGLETT, 110)):
            with self.subTest(defender=defender_card):
                state = board(boosted(trainers=[(PLUSPOWER, TURN)]), {"card": defender_card, "trainers": [(DEFENDER, TURN)]})
                after = apply_command(state, UseAttack(0, 1))
                damage = last_damage(after, len(state.log))
                self.assertEqual(damage["amount"], expected)
                self.assertEqual([step for step, _ in damage["steps"]][:2], ["1 基本となる計算", "2 つるぎのまい"])
                self.assertEqual([m[0] for m in damage["modifiers"]], [5, 7])
                self.assertEqual(damage["damage_set"], ((2, state.players[0].active.card, 60),))

    def test_resistance_after_step_2(self):
        """抵抗力（4 段階）も 2 段階のあと: 60 - 30 = 30（今の対応カードに草の抵抗力を持つポケモンはないので、テスト専用の定義で計算だけを確かめる）。
        効果がなければ 30 - 30 = 0（ダメージを与えなかった）。"""
        state = board(boosted(), {"card": RATTATA})
        mine, theirs = state.players[0].active, state.players[1].active
        resisting = dataclasses.replace(state.card_def(theirs.card), weakness=None, resistance=EnergyType.GRASS, resistance_value=30)
        modifiers = E.attack_damage_modifiers(state, mine, theirs, attack=SLASH)
        calc = calculate_attack_damage(30, state.card_def(mine.card), resisting, state.rules, modifiers)
        self.assertEqual((calc.final, calc.steps[-1]), (30, ("4 抵抗力", 30)))
        self.assertEqual(calculate_attack_damage(30, state.card_def(mine.card), resisting, state.rules).final, 0)

    def test_prevented_damage_is_not_calculated(self):
        """「ダメージを受けない」状態（コクーンの「かたまる」）の相手には、ダメージの要素が無効（計算しない。p.321）。効果はその番の終わりに消える。"""
        kakuna = {"card": KAKUNA, "evolved_from": WEEDLE, "prevent_damage": TURN - 1}
        state = board(boosted(), kakuna)
        after = apply_command(state, UseAttack(0, 1))
        self.assertIsNone(last_damage(after, len(state.log)))
        self.assertEqual(len(events(after, len(state.log), "damage_prevented")), 1)
        removed = events(after, len(state.log), "persistent_effect_removed")
        self.assertIn((0, "expired"), [(e["player"], e["reason"]) for e in removed])

    def test_preview_matches_the_damage(self):
        """宣言の前の計算（preview_attack_damage）と、実際に与えたダメージが同じ（同じ attack_damage_modifiers を使う）。"""
        boards = {
            "通常": board(boosted(), {"card": RATTATA}),
            "弱点": board(boosted(), {"card": DIGLETT}),
            "プラスパワーとディフェンダー": board(boosted(trainers=[(PLUSPOWER, TURN)]), {"card": DIGLETT, "trainers": [(DEFENDER, TURN)]}),
            "効果なし": board(scyther(), {"card": DIGLETT}),
        }
        for name, state in boards.items():
            with self.subTest(board=name):
                mine = state.players[0].active
                use = E.AttackUse(0, mine.pokemon_id, SLASH)
                preview = E.preview_attack_damage(state, use, E.OPPONENT_ACTIVE, 30)
                after = apply_command(state, UseAttack(0, 1))
                self.assertEqual(preview, last_damage(after, len(state.log))["amount"])

    def test_set_with_another_effect_on_the_same_step_stops(self):
        """加算でない「その数にする」効果と同じ段階にほかの効果があると、計算の順番を決める決定（p.321。ワザを使うプレイヤー）がないので
        RuntimeError（今の対応カードでは起こらない）。1 つだけ・加算どうしは計算できる。"""
        definition = load_card_pool().get(SCYTHER)
        target = load_card_pool().get(RATTATA)
        rules = board(scyther(), {"card": RATTATA}).rules
        sets = DamageModifier(2, 60, "つるぎのまい", operation=SET)
        adds = DamageModifier(2, 10, "test")
        self.assertEqual(calculate_attack_damage(30, definition, target, rules, (sets,)).final, 60)
        # 「その数にする」は、1 段階の数によらず 60（「きりさく」は 1 段階がいつも 30 なので、実際の対戦では「2倍」と同じ数になる。違いは
        # 1 段階が 30 でないときにだけ現れるので、計算そのものを確かめる）
        for base in (10, 20, 40, 50):
            with self.subTest(base=base):
                calc = calculate_attack_damage(base, definition, target, rules, (sets,))
                self.assertEqual((calc.final, calc.steps[1]), (60, ("2 つるぎのまい", 60)))
        self.assertEqual(calculate_attack_damage(30, definition, target, rules, (adds, adds)).final, 50)
        with self.assertRaisesRegex(RuntimeError, "順番"):
            # v0.35: 順番の決定に対応し、この場合は ``DamageOrderRequired``（RuntimeError の部分型）で呼ぶ側に順番を求める（解決の基盤のダメージの
            # 要素が決定を出す。tests/test_coin_groups_damage_order_v0_35.py）。順番を渡さない計算は、今までどおり順番を決めずに止める
            calculate_attack_damage(30, definition, target, rules, (sets, adds))
        with self.assertRaises(ValueError):
            # v0.35 で「数をかける」効果（``MULTIPLY``。「きあいだめ」）を加えたので、知らない計算の例を "multiply" から "divide" にした（確かめる性質は同じ）
            DamageModifier(2, 60, "x", operation="divide")
        self.assertEqual(ADD, DamageModifier(5, 10, "x").operation)


class PreflightTest(unittest.TestCase):
    def _machamp_board(self, mine):
        machamp = {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], "energy": [FIGHTING] * 4, "damage": 40}
        return board(mine, machamp)

    def test_double_knockout_question_uses_the_boost(self):
        """宣言の前の確かめ（C18。v0.10）が「つるぎのまい」の 60 で計算する: カイリキー（HP 100・ダメージ 40）は 60 できぜつし、「はんげき」の
        10 でストライク（HP 70・ダメージ 60）もきぜつするので、こんらんのコインの前に止める（どの先読みの方法でも）。効果がなければ 30 なので
        カイリキーはきぜつせず、受け付ける。"""
        for mode in PREFLIGHT_MODES:
            with self.subTest(mode=mode):
                state = self._machamp_board(boosted(damage=60))
                before = snapshot(state)
                with self.assertRaises(UnsupportedError) as ctx:
                    apply_kernel(state, UseAttack(0, 1), preflight=mode)
                self.assertEqual(ctx.exception.code, DOUBLE_KO)
                self.assertEqual(snapshot(state), before)
                plain = self._machamp_board(scyther(damage=60))
                after = apply_kernel(plain, UseAttack(0, 1), preflight=mode)
                self.assertEqual(last_damage(after, len(plain.log))["amount"], 30)

    def test_damage_profile_is_the_printed_damage(self):
        """ダメージの候補（damage_profile）は印刷の 30（1 段階）。2 段階の 60 は preview_attack_damage が計算する（候補に効果を重ねて数えない）。"""
        state = board(boosted(), {"card": RATTATA})
        use = E.AttackUse(0, state.players[0].active.pokemon_id, SLASH)
        self.assertEqual(E.DAMAGE_ONLY.damage_profile(state, use).opponent, (30,))
        self.assertEqual(E.preview_attack_damage(state, use, E.OPPONENT_ACTIVE, 30), 60)
        dance = E.AttackUse(0, state.players[0].active.pokemon_id, SWORDS_DANCE)
        self.assertEqual(E.DEFAULT_EFFECTS.attack_entry(SCYTHER, 0).effect.damage_profile(state, dance).pairs(), ((None, 0),))


class StateAndFormatTest(unittest.TestCase):
    def test_serialization(self):
        """形式 8・9 は効果を書き出す（種類 next_turn_attack_damage・効果を与えたワザ・変わるワザの位置・変えたあとのダメージ）。形式 1〜7 は
        書き出せない（ValueError。黙って落とさない）。書き出しの監査も通る。"""
        state = apply_command(board(scyther(), {"card": RATTATA}), UseAttack(0, 0))
        mine = state.players[0].active
        expected = {"effect": "next_turn_attack_damage", "source_card": mine.card, "source_card_id": SCYTHER, "source_player": 0,
                    "created_turn": TURN, "active_turn": TURN + 2, "attack_index": 0, "target_attack_index": 1, "amount": 60}
        for version in (8, 9):
            self.assertEqual(state_to_dict(state, format_version=version)["players"][0]["active"]["persistent_effects"], [expected])
        for version in range(1, 8):
            with self.subTest(version=version), self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        self.assertEqual(serialization_problems(state), [])

    def test_invariants_check_the_effect(self):
        """不変条件: はたらく番は与えた番 + 2、バトル場だけ、登録された実装の値と同じ（盤面を直接作って壊した）。"""
        broken = {
            # 与えた番 TURN - 2、はたらく番 TURN + 1（期限は過ぎていないので、はたらく番の確かめだけで見つかる）
            "はたらく番が与えた番 + 2 でない": (lambda e: dataclasses.replace(e, active_turn=TURN + 1), "2 番あと（次の自分の番）ではない"),
            "変えたあとのダメージが違う": (lambda e: dataclasses.replace(e, amount=50), "登録された実装）の効果と合わない"),
            "変わるワザの位置が違う": (lambda e: dataclasses.replace(e, target_attack_index=0), "登録された実装）の効果と合わない"),
        }
        for name, (change, message) in broken.items():
            with self.subTest(case=name):
                state = board(boosted(), {"card": RATTATA})
                mine = state.players[0].active
                mine.persistent_effects = tuple(change(e) for e in mine.persistent_effects)
                self.assertTrue(any(message in p for p in check_invariants(state)), check_invariants(state))
        state = board(boosted(), {"card": RATTATA})
        state.players[0].active, state.players[0].bench[0] = state.players[0].bench[0], state.players[0].active
        self.assertTrue(any("ベンチ" in p for p in check_invariants(state)))

    def test_parasect_slash_is_not_changed_in_play(self):
        """パラセクトの「きりさく」（同じ名前・同じ 30）は、ストライクの効果があっても 30（効果は使ったストライク自身のもの。パラセクトは効果を持てない）。"""
        parasect = {"card": PARASECT, "evolved_from": PARAS, "energy": [GRASS] * 3}
        state = board(parasect, {"card": RATTATA}, mine_bench=[RATTATA])
        after = apply_command(state, UseAttack(0, 1))
        self.assertEqual(last_damage(after, len(state.log))["amount"], 30)


if __name__ == "__main__":
    unittest.main()

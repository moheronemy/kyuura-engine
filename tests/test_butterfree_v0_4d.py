"""バタフリー（PMCG2-007。v0.4d）: カードの照合・キャタピー → トランセル → バタフリーの 2 進化・3 枚のカード・きぜつ。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES）。カードの照合は
docs/butterfree-v0.4d.md、ワザの処理は tests/test_forced_switch_v0_4d.py（ふきとばし）・tests/test_damage_drain_v0_4d.py
（メガドレイン）。

- p.19: 見出し「トランセルから進化 バタフリー LV.28／HP70」「ポケモンカード第2弾ポケモンジャングル」。図版: 2 進化・草・
  ふきとばし（無無）20・メガドレイン（草草草草）40・にげる 0・弱点 炎・抵抗力 闘 −30。同じページの LV.37／HP80 は別のカード
- p.310: 進化の条件（その番の最初から場にいた・おたがいの最初の番は不可・その番に進化したポケモンはもう進化できない）。
  受け継ぐもの（エネルギー・つけて使うトレーナー・ダメージカウンター）。特殊状態・持続する効果は進化で消える（p.322・p.323）
- p.313・p.319: 2 進化ポケモンは 3 枚のカード（たね + 進化カード 2 枚）。きぜつしたらすべてトラッシュ（p.323）、サイドは 1 枚

盤面を直接作るテスト（``build_test_state``）は 1 か所の規定を確かめるためのもので、自然な対戦の結果ではない。
"""

import copy
import json
import pickle
import unittest

from kyuura_engine import (
    EndTurn, EvolvePokemon, IllegalActionError, Phase, PlayTrainer, ResolveDecision, UseAttack, apply_command, check_invariants,
    state_to_dict,
)
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract, read_verification
from kyuura_engine.deck import deck_problems
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackKey, DamageAndDrain, DamageAndForceSwitch
from kyuura_engine.rng import rng_fingerprint

from tests.helpers import (
    BUTTERFREE, CATERPIE, FIRE, GRASS, GROWLITHE, KAKUNA, METAPOD, PLUSPOWER, PONYTA, RATTATA, T, WEEDLE,
    build_test_state, expand_decklist, with_coin_results,
)

WHIRLWIND_PRINTED = "相手を控えポケモンと入れ替える。控えポケモンは相手プレイヤーがえらぶ。相手プレイヤーに控えポケモンがいないときには入れ替えはおこらない。"
WHIRLWIND_LATEST = "相手を控えポケモンと入れ替える。入れ替わるポケモンは、相手が選ぶ。（相手に控えがいないとき、入れ替えはおこらない）"
MEGA_DRAIN_PRINTED = "相手に与えたダメージの半分(切り上げ)のダメージカウンターを自分からとりのぞく。"
MEGA_DRAIN_LATEST = "相手にダメージを与えたら、その半分（切り上げ）のダメージカウンターを、自分からとりのぞく。"


def full(state):
    return state_to_dict(state, format_version=8)


def run(state, command):
    new = apply_command(state, command)
    return new, [dict(e) for e in new.log[len(state.log):]]


def uid_of(state, player, card_id, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def card_ids(state, uids):
    return [state.cards[u].card_id for u in uids]


def assert_rejected(test, state, command, code):
    before, fingerprint, log = full(state), rng_fingerprint(state.rng), state.log
    with test.assertRaises(IllegalActionError) as ctx:
        apply_command(state, command)
    test.assertEqual(ctx.exception.code, code)
    test.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
    test.assertIs(state.log, log)


def butterfree(**extra):
    return {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], **extra}


class ButterfreeCardTest(unittest.TestCase):
    def test_card_values(self):
        """p.19 で照合した値（400dpi）: 「トランセルから進化」の 2 進化、HP 70、草、弱点 炎（×2）、抵抗力 闘 −30、にげる 0、
        ポケモンパワーなし、ワザ 2 つ。"""
        pool = load_card_pool()
        d = pool.get(BUTTERFREE)
        self.assertTrue(d.supported and pool.is_playable(BUTTERFREE) and d.is_stage2_pokemon)
        self.assertEqual((d.name_ja, d.evolves_from, d.hp, d.pokemon_type.value, d.weakness.value, d.resistance.value,
                          d.resistance_value, d.retreat_cost, d.powers if hasattr(d, "powers") else ()),
                         ("バタフリー", "トランセル", 70, "grass", "fire", "fighting", 30, 0, ()))
        self.assertEqual(pool.get(METAPOD).name_ja, d.evolves_from)
        attacks = [(a.name_ja, [c.value for c in a.cost], a.damage, a.damage_modifier, a.text_ja) for a in d.attacks]
        self.assertEqual(attacks, [
            ("ふきとばし", ["colorless"] * 2, 20, None, WHIRLWIND_PRINTED),
            ("メガドレイン", ["grass"] * 4, 40, None, MEGA_DRAIN_PRINTED),
        ])
        self.assertEqual(read_extract()["pool_v0_4d"], [BUTTERFREE])

    def test_registered_attacks_follow_the_verified_latest_description(self):
        """ふきとばしは DamageAndForceSwitch、メガドレインは DamageAndDrain。照合した説明文（kyuura の写し。印刷の文面）・
        最新の説明・出典（p.19）が照合の記録（ワザの位置ごと）と合う。"""
        whirlwind, drain = DEFAULT_EFFECTS.attack_entry(BUTTERFREE, 0), DEFAULT_EFFECTS.attack_entry(BUTTERFREE, 1)
        self.assertEqual((type(whirlwind.effect), whirlwind.name_ja, whirlwind.text_ja, whirlwind.play_text_ja, whirlwind.source),
                         (DamageAndForceSwitch, "ふきとばし", WHIRLWIND_PRINTED, WHIRLWIND_LATEST, "P43 p.19"))
        self.assertEqual((type(drain.effect), drain.name_ja, drain.text_ja, drain.play_text_ja, drain.source),
                         (DamageAndDrain, "メガドレイン", MEGA_DRAIN_PRINTED, MEGA_DRAIN_LATEST, "P43 p.19"))
        record = read_verification()["cards"][BUTTERFREE]
        self.assertEqual((record["status"], record["page"], record["pdf_page"]), ("不一致あり", 19, 21))
        self.assertEqual(record["latest_description_ja"], {"0": WHIRLWIND_LATEST, "1": MEGA_DRAIN_LATEST})
        self.assertEqual([m["field"] for m in record["mismatches"]], ["pokemon.attacks[0].text.ja", "pokemon.attacks[1].text.ja"])
        self.assertEqual([m["kyuura"] for m in record["mismatches"]], [WHIRLWIND_PRINTED, MEGA_DRAIN_PRINTED])

    def test_supported_only_with_both_attacks(self):
        """2 つのワザの両方を登録したときだけ対応（どちらかの登録がなければ未対応で、デッキに入らない）。"""
        deck = expand_decklist({CATERPIE: 4, METAPOD: 4, BUTTERFREE: 4, GRASS: 48})
        self.assertEqual(deck_problems(deck, load_card_pool()), [])
        for index, name in ((0, "ふきとばし"), (1, "メガドレイン")):
            with self.subTest(attack=name):
                effects = DEFAULT_EFFECTS.without_attacks(f"test-no-{index}", [AttackKey(BUTTERFREE, index)])
                pool = pool_from_extract(read_extract(), effects)
                self.assertFalse(pool.is_playable(BUTTERFREE))
                self.assertIn(name, " ".join(pool.get(BUTTERFREE).unsupported_reasons))
                self.assertTrue(any(BUTTERFREE in problem for problem in deck_problems(deck, pool)))


class ButterfreeEvolutionTest(unittest.TestCase):
    def test_caterpie_metapod_butterfree_over_two_turns(self):
        """3 番にキャタピー → トランセル、同じ番のバタフリーは拒否（EVOLVED_THIS_TURN。p.310）、5 番にトランセル → バタフリー。
        場のポケモンの番号・ダメージ・エネルギー・場に出た番は受け継ぐ（p.310）。重なりは下から キャタピー・トランセル。"""
        state = build_test_state([
            {"active": {"card": CATERPIE, "energy": [GRASS], "damage": 10}, "hand": [METAPOD, BUTTERFREE]},
            {"active": GROWLITHE, "bench": [RATTATA]},
        ], turn_number=3)
        caterpie = state.players[0].active
        state, _ = run(state, EvolvePokemon(0, uid_of(state, 0, METAPOD), caterpie.pokemon_id))
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, BUTTERFREE), caterpie.pokemon_id), "EVOLVED_THIS_TURN")
        state, _ = run(state, EndTurn(0))
        state, _ = run(state, EndTurn(1))
        metapod_card = state.players[0].active.card
        state, events = run(state, EvolvePokemon(0, uid_of(state, 0, BUTTERFREE), caterpie.pokemon_id))
        me = state.players[0].active
        self.assertEqual(card_ids(state, me.cards()), [CATERPIE, METAPOD, BUTTERFREE])
        self.assertEqual(me.evolution_stack, (caterpie.card, metapod_card))
        self.assertEqual((me.pokemon_id, me.damage, me.energy, me.played_turn, me.evolved_turn),
                         (caterpie.pokemon_id, 10, caterpie.energy, 0, 5))
        self.assertEqual([e["to_card_id"] for e in state.log if e["kind"] == "evolve"], [METAPOD, BUTTERFREE])
        top = state.card_def(me.card)
        self.assertEqual((top.hp, top.retreat_cost, [a.name_ja for a in top.attacks]), (70, 0, ["ふきとばし", "メガドレイン"]))
        self.assertEqual(check_invariants(state), [])

    def test_wrong_evolutions_are_rejected(self):
        """キャタピー（たね）に直接バタフリーは重ねられない（名前が合わない。たね → 2 進化はない）。コクーンにも重ねられない。
        自分の最初の番には進化できない。今の番に場に出したポケモンは進化できない（v0.4a・v0.4c の確認と同じ）。"""
        state = build_test_state([
            {"active": CATERPIE, "bench": [{"card": KAKUNA, "evolved_from": WEEDLE}], "hand": [BUTTERFREE, CATERPIE, METAPOD]},
            {"active": GROWLITHE},
        ], turn_number=5)
        caterpie, kakuna = state.players[0].in_play()
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, BUTTERFREE), caterpie.pokemon_id), "EVOLUTION_NAME_MISMATCH")
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, BUTTERFREE), kakuna.pokemon_id), "EVOLUTION_NAME_MISMATCH")
        first = build_test_state([{"active": CATERPIE, "hand": [METAPOD]}, {"active": GROWLITHE}], turn_number=1)
        assert_rejected(self, first, EvolvePokemon(0, uid_of(first, 0, METAPOD), first.players[0].active.pokemon_id), "FIRST_TURN_EVOLUTION")

    def test_evolution_clears_conditions_and_effects_but_keeps_trainers(self):
        """どく・こんらん状態でプラスパワーをつけたトランセルがバタフリーに進化: 特殊状態は消え、ついているトレーナーは残る
        （p.310・p.322）。自分の持続する効果（「かたまる」）は相手の番にしか残らないので、自分の番の進化と重なるのは盤面を直接
        作ったときだけ（v0.4b・v0.4c のテストで確かめた）。"""
        state = build_test_state([
            {"active": {"card": METAPOD, "evolved_from": CATERPIE, "energy": [GRASS], "poison": 10, "confusion": True},
             "hand": [BUTTERFREE, PLUSPOWER]},
            {"active": GROWLITHE},
        ], turn_number=5)
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, PLUSPOWER)))
        metapod = state.players[0].active
        state, events = run(state, EvolvePokemon(0, uid_of(state, 0, BUTTERFREE), metapod.pokemon_id))
        me = state.players[0].active
        self.assertEqual((me.conditions.names(), me.persistent_effects, len(me.trainers), me.energy), ((), (), 1, metapod.energy))
        reasons = [(e["kind"], e.get("reason")) for e in events if e["kind"] != "evolve"]
        self.assertEqual(reasons, [("special_conditions_removed", "evolve")])


class ButterfreeKnockOutTest(unittest.TestCase):
    def test_three_cards_are_discarded_and_one_prize(self):
        """バタフリーがきぜつしたら、キャタピー・トランセル・バタフリーの 3 枚とエネルギーをトラッシュし、相手はサイドを 1 枚取る
        （p.313・p.319・p.323）。"""
        state = build_test_state([
            {"active": butterfree(energy=[GRASS, GRASS], damage=40), "bench": [PONYTA]},
            {"active": {"card": GROWLITHE, "energy": [FIRE, FIRE]}, "bench": [RATTATA]},
        ], current_player=1, turn_number=8)
        me = state.players[0].active
        new, events = run(state, UseAttack(1, 0))  # ほのお 20 × 2（弱点 炎）= 40。合計 80 ≥ 70
        knock = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual((knock["pokemon"], knock["evolution_stack"]), (me.card, me.evolution_stack))
        self.assertTrue(set(me.cards()) | set(me.energy) <= set(new.players[0].discard))
        self.assertEqual(card_ids(new, new.players[0].discard).count(BUTTERFREE), 1)
        self.assertEqual((new.phase, new.decision.kind, new.decision.player), (Phase.TAKE_PRIZE, "take_prize", 1))
        done = apply_command(new, ResolveDecision(1, new.decision.id, (0,)))
        self.assertEqual(len(done.players[1].prizes), 5)
        self.assertEqual(check_invariants(done), [])


class ButterfreeCopyTest(unittest.TestCase):
    def states(self):
        """通常のバタフリー・ふきとばしの選択待ち・選択後・メガドレインのあと・バタフリーのきぜつのあと。"""
        base = build_test_state([
            {"active": butterfree(energy=[GRASS] * 4, damage=30), "bench": [PONYTA]},
            {"active": GROWLITHE, "bench": [RATTATA, PONYTA]},
        ], turn_number=7)
        pending = apply_command(base, UseAttack(0, 0))
        switched = apply_command(pending, ResolveDecision(1, pending.decision.id, (pending.decision.options[1],)))
        drained = apply_command(base, UseAttack(0, 1))
        knocked = build_test_state([
            {"active": butterfree(energy=[GRASS], damage=60), "bench": [PONYTA]},
            {"active": {"card": GROWLITHE, "energy": [FIRE, FIRE]}, "bench": [RATTATA]},
        ], current_player=1, turn_number=8)
        knocked = apply_command(knocked, UseAttack(1, 0))
        return {"normal": base, "pending": pending, "switched": switched, "drained": drained, "knocked": knocked}

    def test_copies_match_and_continue_the_same_way(self):
        for name, state in self.states().items():
            for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
                with self.subTest(name=name, copied=type(copied)):
                    self.assertEqual((full(copied), rng_fingerprint(copied.rng)), (full(state), rng_fingerprint(state.rng)))
                    self.assertEqual(json.loads(json.dumps(full(copied))), full(state))
                    self.assertEqual(check_invariants(copied), [])
                    if copied.decision is not None:
                        d = copied.decision
                        after = apply_command(copied, ResolveDecision(d.player, d.id, (d.options[0],)))
                        expected = apply_command(state, ResolveDecision(d.player, d.id, (d.options[0],)))
                        self.assertEqual(full(after), full(expected))

    def test_confusion_rng_with_butterfree(self):
        """こんらん状態のバタフリーのワザの乱数はこんらんのコイン 1 枚だけ（ふきとばし・メガドレインはコインを使わない）。"""
        state = build_test_state([
            {"active": butterfree(energy=[GRASS] * 4, confusion=True), "bench": [PONYTA]},
            {"active": GROWLITHE, "bench": [RATTATA]},
        ], turn_number=7)
        for index in (0, 1):
            with self.subTest(index=index):
                new = apply_command(with_coin_results(state, T), UseAttack(0, index))
                self.assertEqual(sum(e["kind"] == "coin_flip" for e in new.log), 1)


if __name__ == "__main__":
    unittest.main()

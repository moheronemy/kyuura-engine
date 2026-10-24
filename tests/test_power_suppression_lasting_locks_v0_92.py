"""v0.92（docs/power-suppression-lasting-locks-v0.92.md）: 能力の消去・続く制限のポケモン 8 枚（ワザ 16）と、持続する効果の期間・消える契機の共通の扱い・受けるワザのダメージの +20・
回復のあとのどく・持っている効果だけを除くだましうち・おたがいの場の特殊能力の抑止・固定の値を加える「うら」が出るまでのコイン。

根拠は kyuura データの採用（kyuura ``7d3f4ca`` の data/cards.json の日本語の印刷の文面）と、既存の規定の記録（GR-2000-P309-ATTACK-PROCEDURE・GR-2000-P310-EVOLUTION・
GR-2000-P311-RETREAT・GR-2000-P321-DAMAGE-ORDER・GR-2000-P322-PERSISTENT-EFFECTS・GR-2000-P324-DEVOLUTION・CR-CHEMICAL-GAS-USE-VS-POWER・CR-CHEMICAL-GAS-ALL-POWERS・
CR-POWER-BACK-AFTER-RECOVERY。docs 各章）。英語版の文面・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像・pcg-search.com との照合はしていない。
盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.92``）。
"""

from __future__ import annotations

import copy
import pathlib
import pickle
import unittest
from typing import ClassVar
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    EndTurn,
    EvolvePokemon,
    PlayBasicToBench,
    ResolveDecision,
    Retreat,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.damage import (
    ADD,
    MULTIPLY,
    SET,
    ZERO_IF_BELOW,
    DamageModifier,
)
from kyuura_engine.decisions import DAMAGE_STEP_ORDER, SELECT_ATTACK, SELECT_POKEMON
from kyuura_engine.engine import check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe
from kyuura_engine.persistent import SOURCE_LEFT_ACTIVE, end_turn, period_active
from kyuura_engine.resolution import kernel as K
from kyuura_engine.resolution import preflight, programs, unbounded
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import (
    ATTACK_FIELD_POWER_SUPPRESSION,
    ATTACK_POWER_SUPPRESSION,
    PERIOD_EFFECT_TYPES,
    SOURCE_LEAVES_ACTIVE,
    CannotAttack,
    CannotRetreat,
    PeriodAttackLock,
    PeriodRetreatLock,
    ReceivedAttackDamageBonus,
)
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_bits, with_coin_results
from tests.release_catalog import cards_before
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_shining_gentle_v0_83 import board as _board

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "power-suppression-lasting-locks-v0.92.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
TURN = 7
G, R, W, L, P, F = H.GRASS, H.FIRE, H.WATER, H.LIGHTNING, H.PSYCHIC, H.FIGHTING
DK, MT = H.DARKNESS_ENERGY_NEO1, H.METAL_ENERGY_NEO1
SPINARAK, ARIADOS, ONIX, MURKROW = H.SPINARAK_NEO1, H.ARIADOS_NEO1, H.ONIX_NEO1, H.MURKROW_NEO1
GOLBAT, LARVITAR, GENGAR, SCIZOR = H.GOLBAT_NEO3, H.LARVITAR_NEO4, H.SABRINAS_GENGAR_GD6, H.SCIZOR_PRN
ZUBAT, SCYTHER, SABRINAS_GASTLY, SABRINAS_HAUNTER = "neo3-001", H.SCYTHER, "GD6-006", H.SABRINAS_HAUNTER_GD6
V092_ATTACKS = [AttackKey(c, i) for c in H.V0_92_POKEMON for i in range(len(load_card_pool().definitions[c].attacks))]
Z23 = "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE"
G37 = "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT"
SG1 = "UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED"
DW1, DW2, DW3, ML2 = E.DARK_WAVE_SCOPE_CODE, E.DARK_WAVE_PROTECTED_CODE, E.DARK_WAVE_KNOCKED_OUT_CODE, E.MEAN_LOOK_SOURCE_FORM_CODE
BELOW = {ARIADOS: SPINARAK, GOLBAT: ZUBAT, GENGAR: [SABRINAS_GASTLY, SABRINAS_HAUNTER], SCIZOR: SCYTHER}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, **kw):
    return _board(active, **kw)


def declare(state, index, *coins, player=None):
    player = state.current_player if player is None else player
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UseAttack(player, index))


def end(state, *coins):
    return apply_kernel(with_coin_results(state, *coins) if coins else state, EndTurn(state.current_player))


def answer(state, choices):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)))


def uid(state, card_id, player=0, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def play(state, card_id, player=None):
    from kyuura_engine import PlayTrainer

    player = state.current_player if player is None else player
    return apply_kernel(state, PlayTrainer(player, uid(state, card_id, player)))


def effects_of(pokemon, kind=None):
    return [e for e in pokemon.persistent_effects if kind is None or isinstance(e, kind)]


def removed(before, after):
    return [(e["persistent_effect"], e["reason"]) for e in new_events(before, after, "persistent_effect_removed")]


def retreat_cmd(state, player=None):
    player = state.current_player if player is None else player
    p = state.players[player]
    return Retreat(player, tuple(p.active.energy[:1]), p.bench[0].card)


def damages(before, after):
    return [e["amount"] for e in new_events(before, after, "damage")]


# ---------------------------------------------------------------- 1〜3 章: 対象・登録・文面の検査


class RegistrationTest(unittest.TestCase):
    def test_every_attack_is_registered(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_92"]), H.V0_92_CARDS)
        self.assertEqual(len(V092_ATTACKS), 16)
        for key in V092_ATTACKS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
                attack = pool.definitions[key.card_id].attacks[key.attack_index]
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja), (attack.name_ja, attack.text_ja, attack.text_ja))
                self.assertEqual(entry.effect.check(attack), [])
                self.assertIsNone(DEFAULT_EFFECTS.attack_problem(key.card_id, attack, pool.definitions[key.card_id].attacks))
        for card in H.V0_92_CARDS:
            self.assertIn(card, pool.playable_ids)
            self.assertEqual(pool.definitions[card].powers, ())

    def test_types(self):
        effect = lambda card, i: DEFAULT_EFFECTS.attack_entry(card, i).effect
        self.assertEqual(effect(SPINARAK, 0), E.CoinAttackAndRetreatLock())
        self.assertEqual(effect(SPINARAK, 1), E.ParalyzeOnHeads())
        self.assertEqual(effect(ARIADOS, 0), E.PeriodLockAttack(E.LOCK_RETREAT, True, 0, None))
        self.assertEqual(effect(ARIADOS, 1), E.DamageDrainThenPoison())
        self.assertEqual(effect(ONIX, 0), E.ReceivedAttackDamageBonusAttack(20, 1, 2))
        self.assertEqual(effect(ONIX, 1), E.DamagePlusOwnCounters(10))
        self.assertEqual(effect(MURKROW, 0), E.PeriodLockAttack(E.LOCK_RETREAT, False, 0, None, True, (SOURCE_LEAVES_ACTIVE,)))
        self.assertEqual(effect(MURKROW, 1), E.ChooseOpponentPokemonDamageIgnoringHeldEffects(20))
        self.assertEqual(effect(GOLBAT, 0), E.ReceivedAttackDamageBonusAttack(20, 0, 2))
        self.assertEqual(effect(GOLBAT, 1), E.DamageDrainThenPoison())
        self.assertEqual(effect(LARVITAR, 0), E.PeriodLockAttack(E.LOCK_ATTACK, True, 1, 1, False, (SOURCE_LEAVES_ACTIVE,)))
        self.assertIs(effect(LARVITAR, 1), E.DAMAGE_ONLY)
        self.assertEqual(effect(GENGAR, 0), E.DamageThenFieldPowerSuppression())
        self.assertEqual(effect(GENGAR, 1), E.DamageThenRetreatLock())
        self.assertEqual(effect(SCIZOR, 0), E.AttackLockWhileSourceActiveOnHeads())
        self.assertEqual(effect(SCIZOR, 1), E.CoinsUntilTailsBonusDamage(30, 10))
        self.assertIsNone(DEFAULT_EFFECTS.attack_entry(LARVITAR, 1).text_ja)
        # 相手の対戦ポケモンへの効果の要素の宣言（G37 の理由の文・tests/test_guts_v0_11.py）
        self.assertEqual(E.DamageDrainThenPoison.opponent_effect_elements, (E.POISON,))
        self.assertEqual(E.CoinAttackAndRetreatLock.opponent_effect_elements, (E.ATTACK_LOCK_ELEMENT, E.RETREAT_LOCK_ELEMENT))

    def test_unregistered_without_the_v0_92_entries(self):
        """今回の登録を除くと対戦に使えなくなるのは、ちょうど 8 枚（ほかのカードは失われない）。過去の範囲は ``cards_before`` で切り出す。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V092_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(H.V0_92_CARDS))
        self.assertEqual(set(H.V0_92_CARDS) & set(cards_before(read_extract(), "0.92")), set())

    def test_evolution_bases(self):
        pool = load_card_pool()
        self.assertEqual(pool.definitions[ARIADOS].evolves_from, "イトマル")
        for base in (SPINARAK, "neo2-003"):  # 今回のイトマルと既存の写しのイトマル（名前で進化する）
            state = board(mon(base, played_turn=3), hand=(ARIADOS,))
            evolved = apply_kernel(state, EvolvePokemon(0, uid(state, ARIADOS), state.players[0].active.pokemon_id))
            self.assertEqual(evolved.cards[evolved.players[0].active.card].card_id, ARIADOS)
            audited(self, evolved)
        self.assertEqual((pool.definitions[GOLBAT].evolves_from, pool.definitions[GENGAR].evolves_from, pool.definitions[SCIZOR].evolves_from),
                         ("ズバット", "ナツメのゴースト", "ストライク"))


class TextCheckTest(unittest.TestCase):
    """3 章: 回復だけの型（``DamageAndDrain``）は既存の全文だけを受け付け、きゅうけつどくを回復だけの型として通さない。正しい組み合わせの型（``DamageDrainThenPoison``）は全文を通す。"""

    def test_drain_only_type_accepts_exactly_the_existing_texts(self):
        pool = load_card_pool()
        registered = [(k, DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index)) for k in DEFAULT_EFFECTS.attack_keys()
                      if type(DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect) is E.DamageAndDrain]
        self.assertEqual(len(registered), 8)
        self.assertEqual(len({entry.play_text_ja for _, entry in registered}), 5)  # 処理に使う文面 5 通り（最新の説明・印刷の文面の採用は v0.91 のまま）
        self.assertEqual({entry.text_ja for _, entry in registered}, set(E.DamageAndDrain.TEXTS))
        for key, entry in registered:
            attack = pool.definitions[key.card_id].attacks[key.attack_index]
            self.assertEqual(E.DamageAndDrain().check(attack), [])
        play_texts = {k.card_id: entry.play_text_ja for k, entry in registered}
        self.assertEqual(play_texts["PMCG2-007"], "相手にダメージを与えたら、その半分（切り上げ）のダメージカウンターを、自分からとりのぞく。")  # p.19 の最新の説明

    def test_poison_bite_is_not_a_drain_only_attack(self):
        pool = load_card_pool()
        for card in (ARIADOS, GOLBAT):
            attack = pool.definitions[card].attacks[1]
            with self.subTest(card=card):
                self.assertTrue(E.DamageAndDrain().check(attack))  # 末尾のどくを無視して通さない
                self.assertEqual(E.DamageDrainThenPoison().check(attack), [])
                registry = DEFAULT_EFFECTS.with_attacks("test", {AttackKey(card, 1): E.AttackEntry(E.DamageAndDrain(), attack.name_ja, attack.text_ja,
                                                                                                   attack.text_ja, "kyuura data/cards.json")})
                self.assertIsNotNone(registry.attack_problem(card, attack, pool.definitions[card].attacks))
        drain = pool.definitions["neo1-001"].attacks[1]  # すいとる（回復だけ）
        self.assertTrue(E.DamageDrainThenPoison().check(drain))

    def test_similar_texts_are_not_interchanged(self):
        pool = load_card_pool()
        attack = lambda card, i: pool.definitions[card].attacks[i]
        # メタルニッパー（30+）を「×」の型に読み替えない。だましうち（持っている）を FA1 の型で通さない
        self.assertTrue(E.CoinsUntilTailsDamage(10).check(attack(SCIZOR, 1)))
        self.assertTrue(E.CoinsUntilTailsBonusDamage(30, 10).check(attack("neo3-015", 1)))
        self.assertTrue(E.ChooseOpponentPokemonDamageIgnoringEffects(20).check(attack(MURKROW, 1)))
        self.assertTrue(E.ChooseOpponentPokemonDamageIgnoringHeldEffects(30).check(attack("neo2-040", 1)))
        # いやなおと: イワークとゴルバットの文面を入れかえない
        self.assertTrue(E.ReceivedAttackDamageBonusAttack(20, 0, 2).check(attack(ONIX, 0)))
        self.assertTrue(E.ReceivedAttackDamageBonusAttack(20, 1, 2).check(attack(GOLBAT, 0)))
        # 期間を明示した禁止: 文面と期間・消える契機の組を入れかえない。ハッサムのにらみつける（SG1 の型）とヨーギラスのにらみつけるを混ぜない
        self.assertTrue(E.PeriodLockAttack(E.LOCK_RETREAT, True, 0, None).check(attack(MURKROW, 0)))
        self.assertTrue(E.PeriodLockAttack(E.LOCK_ATTACK, True, 1, 1, False, (SOURCE_LEAVES_ACTIVE,)).check(attack(SCIZOR, 0)))
        self.assertTrue(E.AttackLockWhileSourceActiveOnHeads().check(attack(LARVITAR, 0)))
        with self.assertRaises(ValueError):
            E.PeriodLockAttack(E.LOCK_RETREAT, True, 0, None, True, (SOURCE_LEAVES_ACTIVE,))  # 文面のない組
        with self.assertRaises(ValueError):
            E.ReceivedAttackDamageBonusAttack(20, 1, 1)


# ---------------------------------------------------------------- 5 章: イトマル・アリアドス


class ScaryFaceTest(unittest.TestCase):
    """こわいかお: 1 枚のコインの「おもて」で、次の相手の番のワザとにげるの両方を止める（要素ごとに投げ直さない）。「うら」は効果がないだけ。"""

    def test_one_coin_locks_attack_and_retreat_for_the_next_turn(self):
        state = board(mon(SPINARAK, (G,)), opponent=mon(H.HITMONCHAN, (F, F)), opponent_hand=(H.SWITCH,))
        done = declare(state, 0, HD)
        self.assertEqual(len(new_events(state, done, "coin_flip")), 1)
        target = done.players[1].active
        self.assertEqual(sorted(type(e).__name__ for e in target.persistent_effects), ["CannotAttack", "CannotRetreat"])
        self.assertEqual({e.active_turn for e in target.persistent_effects}, {TURN + 1})
        audited(self, done)
        # 次の相手の番: ワザもにげるも宣言できない（エネルギーのトラッシュ・こんらんのコインの前に拒否。状態は変わらない）
        rejects(self, done, UseAttack(1, 0), "ATTACK_PREVENTED", IllegalActionError)
        rejects(self, done, retreat_cmd(done), "RETREAT_PREVENTED", IllegalActionError)
        # 入れ替え（ポケモンいれかえ）は止めない。ベンチにもどったポケモンの効果は消える
        chosen = play(done, H.SWITCH)
        switched = answer(chosen, (chosen.decision.options[0],))
        self.assertEqual(sorted(removed(chosen, switched)), [("cannot_attack", "switch"), ("cannot_retreat", "switch")])
        audited(self, switched)
        # 期限: 次の相手の番の終わりに両方消える
        expired = end(done)
        self.assertEqual(sorted(removed(done, expired)), [("cannot_attack", "expired"), ("cannot_retreat", "expired")])
        audited(self, expired)

    def test_tails_gives_nothing_and_is_not_a_failure(self):
        state = board(mon(SPINARAK, (G,)), opponent=mon(H.HITMONCHAN, (F, F)))
        done = declare(state, 0, TL)
        self.assertEqual((done.players[1].active.persistent_effects, new_events(state, done, "attack_failed")), ((), []))
        self.assertEqual(len(new_events(state, done, "coin_flip")), 1)
        audited(self, done)

    def test_barrier_stops_before_the_coin(self):
        """「ワザをうけない」相手（バリアー）には、効果だけを決めるコインを投げるかが決まらない（HC3。コインの前。状態は変わらない）。"""
        mewtwo = board(mon(SPINARAK, (G,)), opponent=mon(H.MEWTWO, (P, P)), current=1, turn=TURN - 1)
        barrier = declare(mewtwo, 1)
        barrier = answer(barrier, (barrier.decision.options[0],))  # トラッシュする超エネルギー
        self.assertEqual(barrier.current_player, 0)
        rejects(self, barrier, UseAttack(0, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")


class StringShotTest(unittest.TestCase):
    def test_paralysis_on_heads(self):
        for coin, paralyzed in ((HD, True), (TL, False)):
            state = board(mon(SPINARAK, (G,)), opponent=mon(H.CHANSEY))
            done = declare(state, 1, coin)
            self.assertEqual((damages(state, done), done.players[1].active.conditions.paralyzed), ([10], paralyzed))
            audited(self, done)


class SpiderWebTest(unittest.TestCase):
    """クモのす: 「おもて」なら「以後」にげることができない。受けたポケモンがバトル場をはなれる・進化・退化で消える。発生源（アリアドス）がはなれても消えない。"""

    def webbed(self, **kw):
        state = board(mon(ARIADOS, (G,), played_turn=1), opponent=mon(H.HITMONCHAN, (F, F)), **kw)
        done = declare(state, 0, HD)
        lock = effects_of(done.players[1].active, PeriodRetreatLock)
        self.assertEqual([(e.active_turn, e.end_turn, e.while_source_active, e.ends_on, e.source_pokemon) for e in lock],
                         [(TURN, None, False, (), state.players[0].active.pokemon_id)])
        audited(self, done)
        return done

    def test_lasting_lock_survives_turn_ends(self):
        done = self.webbed()
        later = end(end(done))  # 相手の番の終わり → 自分の番の終わり → 相手の番（与えた番 + 3）
        self.assertEqual(later.turn_number, TURN + 3)
        self.assertEqual(len(effects_of(later.players[1].active, PeriodRetreatLock)), 1)
        rejects(self, later, retreat_cmd(later), "RETREAT_PREVENTED", IllegalActionError)
        audited(self, later)

    def test_tails_gives_nothing(self):
        state = board(mon(ARIADOS, (G,), played_turn=1), opponent=mon(H.HITMONCHAN, (F, F)))
        done = declare(state, 0, TL)
        self.assertEqual(done.players[1].active.persistent_effects, ())

    def test_source_leaving_does_not_end_it(self):
        done = end(self.webbed())  # 自分の番（与えた番 + 2）
        moved = apply_kernel(done, retreat_cmd(done))  # アリアドスがにげる（発生源がはなれても消えると書かれていない）
        self.assertEqual(removed(done, moved), [])
        self.assertEqual(len(effects_of(moved.players[1].active, PeriodRetreatLock)), 1)
        audited(self, moved)

    def test_receiver_leaving_or_evolving_ends_it_and_it_does_not_return(self):
        done = self.webbed(opponent_hand=(H.SWITCH, H.SWITCH))
        chosen = play(done, H.SWITCH)
        first = chosen.players[1].active.pokemon_id
        switched = answer(chosen, (chosen.decision.options[0],))
        self.assertEqual(removed(chosen, switched), [("period_retreat_lock", "switch")])
        back = play(switched, H.SWITCH)
        back = answer(back, (first,))
        self.assertEqual(back.players[1].active.pokemon_id, first)
        self.assertEqual(back.players[1].active.persistent_effects, ())  # 一度消えた効果は、バトル場にもどっても復活しない（p.322）
        audited(self, back)
        # 進化: 受けたポケモンの効果は消える（p.310・p.323）
        spinarak = board(mon(ARIADOS, (G,), played_turn=1), opponent=mon(SPINARAK, (G,), played_turn=2), opponent_hand=(ARIADOS,))
        webbed = declare(spinarak, 0, HD)
        evolved = apply_kernel(webbed, EvolvePokemon(1, uid(webbed, ARIADOS, 1), webbed.players[1].active.pokemon_id))
        self.assertEqual(removed(webbed, evolved), [("period_retreat_lock", "evolve")])
        audited(self, evolved)


class PoisonBiteTest(unittest.TestCase):
    """きゅうけつどく: ダメージ → 与えたダメージの半分（カウンターの単位で切り上げ）を自分から回復 → 相手をどく。"""

    def test_order_and_amounts(self):
        for card, energy, dealt in ((ARIADOS, (G, G, G), 20), (GOLBAT, (G, W), 10)):
            state = board(mon(card, energy, played_turn=1, damage=30), opponent=mon(H.CHANSEY))
            done = declare(state, 1)
            with self.subTest(card=card):
                kinds = [e["kind"] for e in new_events(state, done) if e["kind"] in ("damage", "drain_heal", "special_condition")]
                self.assertEqual(kinds, ["damage", "drain_heal", "special_condition"])
                heal = new_events(state, done, "drain_heal")[0]
                self.assertEqual((heal["dealt"], heal["drain_counters"], heal["counters"]), (dealt, 1, 1))
                self.assertEqual(done.players[0].active.damage, 20)
                self.assertIsNotNone(done.players[1].active.conditions.poison)
                audited(self, done)

    def test_heal_uses_dealt_damage_not_remaining_hp_and_heals_even_if_the_defender_is_knocked_out(self):
        """与えたダメージは最終ダメージ（弱点で 40）。相手の残りの HP（10）で上限をつけない。相手が HP 以上ならどくにしない（p.309）が、回復は相手の不在で止めない。"""
        state = board(mon(ARIADOS, (G, G, G), played_turn=1, damage=30), opponent=mon(H.ONIX, damage=80), opponent_bench=(H.RATTATA,))
        done = declare(state, 1)
        heal = new_events(state, done, "drain_heal")[0]
        self.assertEqual((heal["dealt"], heal["drain_counters"], heal["counters"]), (40, 2, 2))
        self.assertEqual(new_events(state, done, "special_condition"), [])
        self.assertEqual(len(new_events(state, done, "knock_out")), 1)
        audited(self, done)

    def test_heal_does_not_exceed_own_counters(self):
        state = board(mon(ARIADOS, (G, G, G), played_turn=1, damage=10), opponent=mon(H.ONIX))
        done = declare(state, 1)
        heal = new_events(state, done, "drain_heal")[0]
        self.assertEqual((heal["drain_counters"], heal["counters"], done.players[0].active.damage), (2, 1, 0))

    def test_no_damage_stops_on_the_poison_after_heal(self):
        """ダメージを与えなかった（ディフェンダーで 0）とき、回復はしない。「その後、」のどくを与えるか（回復の条件の中か順番だけか）は決まらない（Z23。宣言の前）。どくにならない
        相手（めんえき）なら、どちらでも同じなので止めない。"""
        defended = board(mon(GOLBAT, (G, W), played_turn=1, damage=30), opponent=mon(H.CHANSEY, trainers=[(H.DEFENDER, TURN)]))
        rejects(self, defended, UseAttack(0, 1), Z23)
        immune = board(mon(GOLBAT, (G, W), played_turn=1, damage=30), opponent=mon(H.SNORLAX, trainers=[(H.DEFENDER, TURN)]))
        done = declare(immune, 1)
        self.assertEqual((damages(immune, done), new_events(immune, done, "drain_heal"), done.players[1].active.conditions.poison), ([0], [], None))
        audited(self, done)

    def test_damage_result_is_carried_across_a_decision(self):
        """ダメージのあとの要素のあいだの決定（相手のドガースの［ぶんれつ］）をまたいでも、最終ダメージの結果を続きの情報で運び、回復とどくはその結果で決める。"""
        state = board(mon(ARIADOS, (G, G, G), played_turn=1, damage=30), opponent=mon(H.KOFFING_ES2), opponent_deck=[H.KOFFING_ES2, W, W])
        asked = declare(state, 1)
        self.assertEqual(asked.decision.kind, "split_from_deck")
        self.assertIn("damage_results", dict(asked.decision.context))
        for restored in (asked, copy.deepcopy(asked), pickle.loads(pickle.dumps(asked)), asked.clone()):
            done = answer(restored, (restored.decision.options[0],))
            self.assertEqual([e["counters"] for e in new_events(asked, done, "drain_heal")], [1])
            self.assertIsNotNone(done.players[1].active.conditions.poison)
            audited(self, done)


# ---------------------------------------------------------------- 6 章: いやなおと


BONUS_LABEL = f"（{ReceivedAttackDamageBonus.kind}）"


def bonus_steps(event):
    return [tuple(step) for step in event.get("steps") or () if str(step[0]).startswith("8 ") and str(step[0]).endswith(BONUS_LABEL)]


class ScreechTest(unittest.TestCase):
    """いやなおと: 決まった期間、受けたポケモンが受けるワザによるダメージの p.321 の 8 段階で +20（イワークは次の相手の番と次の自分の番、ゴルバットは次の自分の番が終わるまで）。"""

    def test_periods_differ_by_text(self):
        for card, energy, start in ((ONIX, (F,), TURN + 1), (GOLBAT, (G,), TURN)):
            state = board(mon(card, energy, played_turn=1), opponent=mon(H.CHANSEY))
            done = declare(state, 0)
            with self.subTest(card=card):
                bonus = effects_of(done.players[1].active, ReceivedAttackDamageBonus)
                self.assertEqual([(e.created_turn, e.active_turn, e.end_turn, e.amount, e.ends_on) for e in bonus], [(TURN, start, TURN + 2, 20, ())])
                added = new_events(state, done, "persistent_effect_added")[0]
                self.assertEqual((added["active_turn"], added["end_turn"], added["amount"], added["source_pokemon"]),
                                 (start, TURN + 2, 20, state.players[0].active.pokemon_id))
                self.assertEqual(done.turn_number, TURN + 1)
                self.assertTrue(period_active(done, bonus[0]))  # どちらも次の相手の番にはたらく（ゴルバットは与えた番から）
                audited(self, done)
                later = end(done)  # 自分の番（与えた番 + 2）。その番の終わりに消える
                self.assertTrue(period_active(later, effects_of(later.players[1].active, ReceivedAttackDamageBonus)[0]))
                gone = end(later)
                self.assertEqual(removed(later, gone), [("received_attack_damage_bonus", "expired")])
                audited(self, gone)

    def test_attack_damage_including_own_self_damage_gets_plus_20_at_step_8(self):
        """次の相手の番: 受けたピカチュウ自身のでんげきの「うら」の自分へのダメージ（ワザによるダメージ）も +20。次の自分の番: イワークのいかりも +20（8 段階）。その番の終わりに消える。"""
        state = board(mon(ONIX, (F, F)), opponent=mon(H.PIKACHU, (L, L)))
        screeched = declare(state, 0)
        zapped = declare(screeched, 1, TL)  # 相手の番（与えた番 + 1）: でんげき 30・「うら」で自分にも 10
        (own,) = [e for e in new_events(screeched, zapped, "damage") if e.get("target") == "self"]
        self.assertEqual((own["amount"], len(bonus_steps(own))), (30, 1))
        mine = declare(zapped, 1)  # 自分の番（与えた番 + 2）: いかり 10 + でんげきの 30 ぶん（3 個 × 10）→ 弱点 ×2 → 8 段階 +20
        hit = new_events(zapped, mine, "damage")[0]
        self.assertEqual((hit["amount"], len(bonus_steps(hit))), (100, 1))
        self.assertEqual(removed(zapped, mine), [("received_attack_damage_bonus", "knock_out")])  # 100 でピカチュウがきぜつ
        audited(self, mine)

    def test_same_step_order_decision_with_zero_below(self):
        """受けたポケモン自身の「かたくなる」（8 段階のしきい値より小さければ 0）と +20 は、順番で結果が変わるので受けるポケモンの持ち主が順番を選ぶ（v0.35 の決定）。"""
        state = board(mon(ONIX, (F, F)), opponent=mon(H.ONIX, (F, F)))
        screeched = declare(state, 0)
        hardened = declare(screeched, 1)  # 相手のイワークの「かたくなる」（次の相手の番に受けるダメージが 40 より小さければ 0）
        asked = declare(hardened, 1)
        self.assertEqual((asked.decision.kind, asked.decision.player), (DAMAGE_STEP_ORDER, 1))
        results = set()
        for option in asked.decision.options:
            done = answer(asked, (option,))
            results.add(tuple(damages(asked, done)))
            audited(self, done)
        self.assertEqual(results, {(0,), (20,)})

    def test_prevented_damage_and_no_damage_element_get_no_bonus(self):
        """「ダメージを受けない」状態（かたまる）ではダメージの要素が無効なので +20 も起こらない。どくのダメージ（ワザによるダメージではない）にも加えない。"""
        state = board(mon(ONIX, (F, F)), opponent=mon(H.METAPOD, (G, G), evolved_from=H.CATERPIE, poison=10))
        screeched = declare(state, 0)
        self.assertEqual([e["amount"] for e in new_events(state, screeched, "poison_damage")], [10])
        hardened = declare(screeched, 0, HD)  # トランセルの「かたまる」（おもて）
        hit = declare(hardened, 1)
        self.assertEqual([e["amount"] for e in new_events(hardened, hit, "damage") if e["amount"] > 0], [])
        self.assertTrue(new_events(hardened, hit, "damage_prevented"))
        audited(self, hit)

    def test_confused_receiver_stops_before_the_coin(self):
        """こんらんの 20 が「ワザによるダメージ」かは決まらない（既存の問い。こんらんのコインの前）。"""
        state = board(mon(ONIX, (F, F)), opponent=mon(H.HITMONCHAN, (F, F), confusion=True))
        screeched = declare(state, 0)
        rejects(self, screeched, UseAttack(1, 0), "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS")

    def test_receiver_leaving_ends_it_but_source_leaving_does_not(self):
        state = board(mon(GOLBAT, (G, W), played_turn=1), opponent=mon(H.CHANSEY, (W,)), opponent_hand=(H.SWITCH,))
        screeched = declare(state, 0)
        moved = end(screeched)  # 自分の番（与えた番 + 2）
        retreated = apply_kernel(moved, Retreat(0, (), moved.players[0].bench[0].card))  # ゴルバット（にげる 0）がはなれても消えない
        self.assertEqual(removed(moved, retreated), [])
        self.assertEqual(len(effects_of(retreated.players[1].active, ReceivedAttackDamageBonus)), 1)
        audited(self, retreated)
        chosen = play(screeched, H.SWITCH)
        switched = answer(chosen, (chosen.decision.options[0],))
        self.assertEqual(removed(chosen, switched), [("received_attack_damage_bonus", "switch")])

    def test_overlapping_effects_each_add(self):
        """重なった効果はそれぞれはたらく（p.323）。加算なので順番の決定は出ない（問い合わせの値で確かめる）。"""
        state = declare(board(mon(GOLBAT, (G,), played_turn=1), opponent=mon(H.CHANSEY)), 0)
        receiver = state.players[1].active
        first = effects_of(receiver, ReceivedAttackDamageBonus)[0]
        trial = state.clone()
        holder = trial.players[1].active
        holder.persistent_effects = (*holder.persistent_effects, ReceivedAttackDamageBonus(first.source_card, 0, TURN - 1, TURN - 1, TURN + 1, first.source_pokemon, 20))
        modifiers = E.attack_damage_modifiers(trial, trial.players[0].active, holder, attack=AttackKey(GOLBAT, 1))
        self.assertEqual([(m.step, m.amount, m.operation) for m in modifiers if m.label.endswith(BONUS_LABEL)], [(8, 20, ADD), (8, 20, ADD)])


# ---------------------------------------------------------------- 7 章: ヤミカラス・ヨーギラス（とハッサムの SG1）


class MeanLookTest(unittest.TestCase):
    """くろいまなざし: 「以後」、発生源がバトル場にいるかぎりにげることができない。自分（発生源）か相手がバトル場をはなれた時点で消え、同じ番にもどっても復活しない。"""

    def looked(self, **kw):
        state = board(mon(MURKROW, (DK,)), opponent=mon(H.CHANSEY, (W, W)), **kw)
        done = declare(state, 0)
        lock = effects_of(done.players[1].active, PeriodRetreatLock)
        self.assertEqual([(e.end_turn, e.while_source_active, e.ends_on) for e in lock], [(None, True, (SOURCE_LEAVES_ACTIVE,))])
        audited(self, done)
        return done

    def test_lasting_while_the_source_is_active(self):
        done = self.looked()
        rejects(self, done, retreat_cmd(done), "RETREAT_PREVENTED", IllegalActionError)
        later = end(end(done))
        rejects(self, later, retreat_cmd(later), "RETREAT_PREVENTED", IllegalActionError)

    def test_source_leaving_ends_it_and_return_does_not_restore(self):
        done = end(self.looked(hand=(H.SWITCH,)))  # 自分の番（与えた番 + 2）
        murkrow = done.players[0].active.pokemon_id
        retreated = apply_kernel(done, Retreat(0, (), done.players[0].bench[0].card))  # ヤミカラス（にげる 0）がはなれた
        self.assertEqual(removed(done, retreated), [("period_retreat_lock", SOURCE_LEFT_ACTIVE)])
        chosen = play(retreated, H.SWITCH)
        back = answer(chosen, (murkrow,))
        self.assertEqual((back.players[0].active.pokemon_id, back.players[1].active.persistent_effects), (murkrow, ()))
        audited(self, back)
        opponent = end(back)
        self.assertEqual(opponent.current_player, 1)
        audited(self, apply_kernel(opponent, retreat_cmd(opponent)))  # 復活しないので、にげられる

    def test_source_knocked_out_ends_it(self):
        state = board(mon(MURKROW, (DK,), damage=40), opponent=mon(H.HITMONCHAN, (F, F)))
        done = declare(state, 0)
        punched = declare(done, 0)  # 相手のエビワラーの 20 でヤミカラスがきぜつ
        self.assertIn(("period_retreat_lock", SOURCE_LEFT_ACTIVE), removed(done, punched))
        self.assertEqual(punched.players[1].active.persistent_effects, ())

    def test_receiver_switch_ends_it(self):
        done = self.looked(opponent_hand=(H.SWITCH,))
        chosen = play(done, H.SWITCH)
        switched = answer(chosen, (chosen.decision.options[0],))
        self.assertEqual(removed(chosen, switched), [("period_retreat_lock", "switch")])

    def test_copied_source_is_the_copier_and_its_evolution_is_ml2(self):
        """ゆびをふるでまねたくろいまなざしの発生源は、まねたピッピ。発生源の進化で「このカード」がバトル場にいることになるかは決まらない（ML2。状態を変える前）。"""
        state = board(mon(H.CLEFAIRY, (R, R, R), played_turn=1), opponent=mon(MURKROW, (DK,)), hand=(H.CLEFABLE,))
        asked = declare(state, 1)
        self.assertEqual(asked.decision.kind, SELECT_ATTACK)
        done = answer(asked, (0,))
        lock = effects_of(done.players[1].active, PeriodRetreatLock)[0]
        self.assertEqual((lock.source_pokemon, lock.source_card), (state.players[0].active.pokemon_id, state.players[0].active.card))
        self.assertEqual(new_events(asked, done, "persistent_effect_added")[0]["effect"], f"{MURKROW}#0")
        audited(self, done)
        mine = end(done)
        rejects(self, mine, EvolvePokemon(0, uid(mine, H.CLEFABLE), mine.players[0].active.pokemon_id), ML2)


class FeintAttackHeldTest(unittest.TestCase):
    """ヤミカラスのだましうち: 選んだポケモン自身の持っている「弱点・抵抗力・特殊能力・その他の効果」だけを除く。ほかのポケモン・ワザを使う側・プレイヤーの効果は除かない（FA1 の比べはしない）。"""

    def test_only_the_receivers_own_effects_are_ignored(self):
        charmander = mon(H.CHARMANDER, trainers=[(H.DEFENDER, TURN)])
        state = board(mon(MURKROW, (DK, W)), opponent=mon(H.CHANSEY), opponent_bench=(charmander,))
        choosing = declare(state, 1)
        self.assertEqual(choosing.decision.kind, SELECT_POKEMON)
        self.assertEqual(choosing.decision.context_value("unresolved_choices", ()), ())  # FA1 で止める選択はない
        active, bench = state.players[1].active.pokemon_id, state.players[1].bench[0].pokemon_id
        hits = {}
        for target in (active, bench):
            done = answer(choosing, (target,))
            hit = new_events(choosing, done, "damage")[0]
            hits[target] = (hit["amount"], hit.get("ignore_defender_effects"), hit.get("ignore_effects_scope"))
            audited(self, done)
        # 相手の対戦ポケモンには、ワザを使うポケモンについている悪エネルギーの +10（受けるポケモンの持っていない効果）がかかる。控えのディフェンダー・弱点は除く
        self.assertEqual(hits, {active: (30, True, None), bench: (20, True, None)})

    def test_other_pokemons_bench_guard_is_not_ignored(self):
        rhydon = mon(H.BROCKS_RHYDON, played_turn=2, evolved_from="PMCG5-049", evolved_turn=4)
        state = board(mon(MURKROW, (DK, W)), opponent=mon(H.CHANSEY), opponent_bench=(mon(H.RATTATA), rhydon))
        choosing = declare(state, 1)
        rattata = state.players[1].bench[0].pokemon_id
        guarded = answer(choosing, (rattata,))
        self.assertEqual((guarded.decision.kind, guarded.decision.player), ("bench_guard", 1))  # ほかのポケモンの［ベンチガード］は除かない
        audited(self, guarded)


class LeerUntilLeaveTest(unittest.TestCase):
    """ヨーギラスのにらみつける: 「おもて」なら次の相手の番ワザを使えない。発生源か受けたポケモンがバトル場をはなれた時点で消える（同じ番にもどっても SG1 にしない）。"""

    def leered(self, **kw):
        state = board(mon(LARVITAR, (F,)), opponent=mon(H.CHANSEY, (W, W)), **kw)
        done = declare(state, 0, HD)
        lock = effects_of(done.players[1].active, PeriodAttackLock)
        self.assertEqual([(e.active_turn, e.end_turn, e.while_source_active, e.ends_on) for e in lock], [(TURN + 1, TURN + 1, False, (SOURCE_LEAVES_ACTIVE,))])
        audited(self, done)
        return done

    def test_attack_is_locked_but_retreat_is_not(self):
        done = self.leered()
        rejects(self, done, UseAttack(1, 0), "ATTACK_PREVENTED", IllegalActionError)
        retreated = apply_kernel(done, retreat_cmd(done))
        self.assertEqual(removed(done, retreated), [("period_attack_lock", "retreat")])
        audited(self, retreated)
        expired = end(done)
        self.assertEqual(removed(done, expired), [("period_attack_lock", "expired")])

    def test_tails_gives_nothing(self):
        state = board(mon(LARVITAR, (F,)), opponent=mon(H.CHANSEY, (W, W)))
        self.assertEqual(declare(state, 0, TL).players[1].active.persistent_effects, ())

    def test_source_gusted_away_ends_it_and_returning_does_not_restore(self):
        done = self.leered(bench=(H.RATTATA, H.RATTATA), opponent_hand=(H.GUST, H.GUST))
        larvitar = done.players[0].active.pokemon_id
        chosen = play(done, H.GUST)
        gusted = answer(chosen, (chosen.decision.options[0],))
        self.assertEqual(removed(chosen, gusted), [("period_attack_lock", SOURCE_LEFT_ACTIVE)])
        again = play(gusted, H.GUST)
        self.assertNotIn(larvitar, again.decision.context_value("unresolved_choices", ()))  # SG1 で止めない（消えた効果はもどらない）
        back = answer(again, (larvitar,))
        self.assertEqual(back.players[0].active.pokemon_id, larvitar)
        attacked = declare(back, 0)  # 相手のラッキーの「まるまる」を受け付ける（ワザを使えない効果は消えたまま）
        self.assertTrue(new_events(back, attacked, "attack"))
        audited(self, attacked)

    def test_scizor_leer_keeps_the_sg1_reading(self):
        """ハッサムのにらみつける（「このカードがバトル場にいるかぎり」。v0.76 の型）: 発生源がはなれると使えるが、効果は残り、同じ番にもどす選択は SG1。"""
        state = board(mon(SCIZOR, (MT,), played_turn=1), bench=(H.RATTATA, H.RATTATA), opponent=mon(H.CHANSEY, (W, W)), opponent_hand=(H.GUST, H.GUST))
        done = declare(state, 0, HD)
        self.assertEqual([type(e).__name__ for e in done.players[1].active.persistent_effects], ["CannotAttackWhileSourceActive"])
        scizor = done.players[0].active.pokemon_id
        chosen = play(done, H.GUST)
        gusted = answer(chosen, (chosen.decision.options[0],))
        self.assertEqual(removed(chosen, gusted), [])
        again = play(gusted, H.GUST)
        self.assertIn(scizor, again.decision.context_value("unresolved_choices", ()))
        rejects(self, again, ResolveDecision(1, again.decision.id, (scizor,)), SG1)


# ---------------------------------------------------------------- 8 章: ナツメのゲンガー


def gengar(energy=(P, P, P), **extra):
    return mon(GENGAR, energy, played_turn=1, **extra)


BLASTOISE = mon(H.BLASTOISE, (W,), evolved_from=[H.SQUIRTLE, H.WARTORTLE], played_turn=1)
MACHAMP = mon(H.MACHAMP, (F,), evolved_from=[H.MACHOP, H.MACHOKE], played_turn=1)


def records(state):
    return [r for r in state.trainer_effects if r.kind == ATTACK_FIELD_POWER_SUPPRESSION]


class DarkWaveTest(unittest.TestCase):
    """やみのはどう: 20 ダメージのあと、次の相手の番の終わりまで、おたがいの場のすべてのポケモンは特殊能力を使えず、その力も消える。"""

    def test_record_and_both_sides_are_suppressed(self):
        from kyuura_engine.continuous import power_suppressed

        state = board(gengar(), bench=(BLASTOISE,), opponent=dict(BLASTOISE), opponent_hand=(W,))
        done = declare(state, 0)
        self.assertEqual(damages(state, done), [20])
        (record,) = records(done)
        attacker = state.players[0].active
        self.assertEqual((record.player, record.source_card, record.pokemon_id, record.card_id, record.attack_index, record.created_turn, record.expires_turn),
                         (0, attacker.card, attacker.pokemon_id, GENGAR, 0, TURN, TURN + 1))
        self.assertEqual([r for r in done.trainer_effects if r.kind == ATTACK_POWER_SUPPRESSION], [])  # オールクリアのワザの処理のあとに消える記録は使わない
        rain = load_card_pool().get(H.BLASTOISE).powers[0]
        for side in (0, 1):
            holder = done.players[side].bench[0] if side == 0 else done.players[1].active
            self.assertTrue(power_suppressed(done, rain, holder))
        b = done.players[1].active
        rejects(self, done, UsePokemonPower(1, b.pokemon_id, 0, energy=uid(done, W, 1), target=b.pokemon_id), "POWER_SUPPRESSED", IllegalActionError)
        audited(self, done)

    def test_lasts_until_the_end_of_the_opponents_turn_even_if_the_source_leaves(self):
        from kyuura_engine.continuous import power_suppressed

        state = board(gengar(), bench=(H.RATTATA,), opponent=mon(H.CHANSEY, (W,)), opponent_bench=(BLASTOISE,), opponent_hand=(H.GUST,))
        done = declare(state, 0)
        chosen = play(done, H.GUST)
        gusted = answer(chosen, (chosen.decision.options[0],))  # ナツメのゲンガーがベンチにもどっても消えない（説明に書かれていない）
        self.assertEqual(len(records(gusted)), 1)
        back = end(gusted)
        self.assertEqual(records(back), [])
        self.assertEqual([e["reason"] for e in new_events(gusted, back, "trainer_effect_removed")], ["expired"])
        rain = load_card_pool().get(H.BLASTOISE).powers[0]
        self.assertFalse(power_suppressed(back, rain, back.players[1].bench[0]))
        audited(self, back)

    def test_damage_time_reactions_still_happen(self):
        """ダメージの時点ではまだ特殊能力ははたらく: カイリキーの［はんげき］は 20 を受けて、効果の要素の前にゲンガーへ 10。"""
        state = board(gengar(), opponent=dict(MACHAMP), opponent_bench=(H.RATTATA,))
        done = declare(state, 0)
        kinds = [e["kind"] for e in new_events(state, done) if e["kind"] in ("counterattack", "trainer_effect_added")]
        self.assertEqual(kinds, ["counterattack", "trainer_effect_added"])
        self.assertEqual(done.players[0].active.damage, 10)
        audited(self, done)

    def test_new_pokemon_with_powers_is_dw1(self):
        state = board(gengar(), opponent=mon(H.CHANSEY, (W,)), opponent_bench=(mon(H.WARTORTLE, evolved_from=H.SQUIRTLE, played_turn=1),),
                      opponent_hand=(H.MR_MIME, H.RATTATA, H.BLASTOISE))
        done = declare(state, 0)
        rejects(self, done, PlayBasicToBench(1, uid(done, H.MR_MIME, 1)), DW1)
        rejects(self, done, EvolvePokemon(1, uid(done, H.BLASTOISE, 1), done.players[1].bench[0].pokemon_id), DW1)
        audited(self, apply_kernel(done, PlayBasicToBench(1, uid(done, H.RATTATA, 1))))  # 特殊能力を持たないたねポケモンは出せる

    def test_protected_pokemon_with_powers_is_dw2(self):
        """相手の対戦ポケモンのフリーザーの［オーロラヴェール］で守られた控えのカメックス（特殊能力を持つ）も止まるかは決まらない（DW2。宣言の前）。守られた控えが特殊能力を
        持たないなら、止まるかどうかで結果が変わらないので止めない。ねむりのフリーザーの［オーロラヴェール］ははたらかない。"""
        state = board(gengar(), opponent=mon(H.ARTICUNO_ES2), opponent_bench=(dict(BLASTOISE),))
        rejects(self, state, UseAttack(0, 0), DW2)
        powerless = board(gengar(), opponent=mon(H.ARTICUNO_ES2), opponent_bench=(H.RATTATA,))
        audited(self, declare(powerless, 0))
        asleep = board(gengar(), opponent=mon(H.ARTICUNO_ES2, sleep=True), opponent_bench=(dict(BLASTOISE),))
        audited(self, declare(asleep, 0))

    def test_knocked_out_defender_guts_is_g37_and_final_beam_is_dw3(self):
        guts = board(gengar(), opponent=mon(H.GIOVANNIS_MACHAMP, (F,), evolved_from=[H.GIOVANNIS_MACHOP, H.GIOVANNIS_MACHOKE], played_turn=1, damage=90),
                     opponent_bench=(H.RATTATA,))
        rejects(self, guts, UseAttack(0, 0), G37)
        beam = board(gengar(), opponent=mon(H.DARK_GYARADOS, (W,), evolved_from=H.ROCKET_MAGIKARP, played_turn=1, damage=50), opponent_bench=(H.RATTATA,))
        rejects(self, beam, UseAttack(0, 0), DW3)
        alive = board(gengar(), opponent=mon(H.DARK_GYARADOS, (W,), evolved_from=H.ROCKET_MAGIKARP, played_turn=1), opponent_bench=(H.RATTATA,))
        audited(self, declare(alive, 0))  # HP 以上にならなければ止めない

    def test_max_hp_query_uses_the_suppression(self):
        """［ガスのからだ］（最大HP + 超エネルギーカード × 10）は抑止で消える。抑止はワザのあとも続くので、きぜつの判定は消えた最大HP で行う（ワザの効果で最大HP が下がった
        ポケモンは、ワザのあとのきぜつの判定がきぜつにする。v0.81・v0.91 と同じ既存の処理）。"""
        gastly = mon("PMCG6-049", (P, P), damage=30, played_turn=2)  # ナツメのゴース（HP 40 + 20。抑止がなければ 20 を受けても 50 で残る）
        state = board(gengar(), opponent=gastly, opponent_bench=(H.RATTATA,))
        self.assertEqual(E.max_hp(state, state.players[1].active), 60)
        done = declare(state, 0)
        self.assertEqual([done.cards[e["pokemon"]].card_id for e in new_events(state, done, "knock_out")], ["PMCG6-049"])
        audited(self, done)

    def test_copied_by_metronome_records_the_actual_user(self):
        state = board(mon(H.CLEFAIRY, (R, R, R), played_turn=1), opponent=gengar())
        asked = declare(state, 1)
        done = answer(asked, (0,))
        (record,) = records(done)
        self.assertEqual((record.source_card, record.pokemon_id, record.card_id, record.attack_index),
                         (state.players[0].active.card, state.players[0].active.pokemon_id, GENGAR, 0))
        audited(self, done)

    def test_strange_gas_now_refuses_declared_powers(self):
        """v0.87 のドガースの「ふしぎなガス」がはたらいている側の、宣言して使う特殊能力の使用を拒否する（v0.91 までは受け付けていた。8 章）。"""
        state = board(mon(H.KOFFING_ES2, (G, G)), opponent=dict(BLASTOISE), opponent_hand=(W,))
        gassed = declare(state, 0, HD)
        b = gassed.players[1].active
        rejects(self, gassed, UsePokemonPower(1, b.pokemon_id, 0, energy=uid(gassed, W, 1), target=b.pokemon_id), "POWER_SUPPRESSED", IllegalActionError)


class ShadowBindTest(unittest.TestCase):
    def test_retreat_lock_only(self):
        state = board(gengar(), opponent=mon(H.CHANSEY, (W, W)), opponent_hand=(H.SWITCH,))
        done = declare(state, 1)
        self.assertEqual((damages(state, done), [type(e) for e in done.players[1].active.persistent_effects]), ([10], [CannotRetreat]))  # 40 − 抵抗力 30
        rejects(self, done, retreat_cmd(done), "RETREAT_PREVENTED", IllegalActionError)
        chosen = play(done, H.SWITCH)  # 入れ替えは止めない
        audited(self, answer(chosen, (chosen.decision.options[0],)))


# ---------------------------------------------------------------- 9 章: ハッサムのメタルニッパー（固定の値を加える「うら」が出るまでのコイン）


def scizor(**extra):
    return mon(SCIZOR, (MT, W, W), played_turn=1, **extra)


def pincer(state, heads, mode="derived"):
    return apply_kernel(with_coin_bits(state, *([H.H] * heads + [H.T])), UseAttack(0, 1), preflight=mode)


def captured_classes(state):
    got = []
    real = unbounded.head_classes

    def wrap(*args, **kwargs):
        found = real(*args, **kwargs)
        got.append(found)
        return found

    with mock.patch.object(unbounded, "head_classes", wrap):
        try:
            apply_kernel(with_coin_bits(state, H.T), UseAttack(0, 1), preflight="derived")
        except UnsupportedError:
            pass
    return got[0]


def outcome(state, heads, mode, *, brute=None):
    """``heads`` 枚の「おもて」のあと「うら」で処理した結果。``brute`` なら、先読みが組の代表ではなく 0 〜 brute − 1 のすべての「おもて」の数を試す。"""
    patches = [mock.patch.object(preflight, "MAX_BRANCHES", 10 ** 6)]
    if brute is not None:
        patches.append(mock.patch.object(preflight.Oracle, "coin_run", lambda self, classes: self._next(brute)))
    for patch in patches:
        patch.start()
    try:
        new = pincer(state, heads, mode)
        return ("ok", [e["amount"] for e in new_events(state, new, "damage")])
    except UnsupportedError as error:
        return ("stop", error.code, str(error))
    finally:
        for patch in patches:
            patch.stop()


class MetalPincerTest(unittest.TestCase):
    """メタルニッパー: 基本となるダメージは 30 + 10 × おもての数（1 枚目が「うら」でも 30）。実際は「うら」が出るまで 1 枚ずつ投げる。先読みの組のキー・有限の境界・実際のダメージは同じ式。"""

    BOARDS: ClassVar[dict] = {
        "plain": lambda: board(scizor(), opponent=mon(H.CHANSEY)),
        "remaining_hp": lambda: board(scizor(), opponent=mon(H.CHANSEY, damage=80), opponent_bench=(H.RATTATA,)),
        "weakness_resistance": lambda: board(scizor(), opponent=mon(H.CHARMANDER), opponent_bench=(H.RATTATA,)),
        "defender": lambda: board(scizor(), opponent=mon(H.CHANSEY, trainers=[(H.DEFENDER, TURN)])),
        "doubled": lambda: board(scizor(), opponent=mon(H.CHANSEY)),
        "shell_attack": lambda: board(scizor(), opponent=mon(H.DARK_WARTORTLE, evolved_from=H.ROCKET_SQUIRTLE, played_turn=1, retaliation_received=6)),
        "scram": lambda: board(scizor(), opponent=mon(H.BROCKS_PRIMEAPE, evolved_from=H.BROCKS_MANKEY, played_turn=1)),
        "guts": lambda: board(scizor(), opponent=mon(H.GIOVANNIS_MACHAMP, evolved_from=[H.GIOVANNIS_MACHOP, H.GIOVANNIS_MACHOKE], played_turn=1)),
    }

    def test_actual_damage_is_30_plus_10_per_heads(self):
        for heads in (0, 1, 3, 7):
            state = board(scizor(), opponent=mon(H.CHANSEY))
            done = pincer(state, heads)
            with self.subTest(heads=heads):
                flips = new_events(state, done, "coin_flip")
                self.assertEqual(([e["result"] for e in flips][-1], len(flips)), ("tails", heads + 1))
                self.assertEqual(new_events(state, done, "damage")[0]["steps"][0], ("1 基本となる計算", 30 + 10 * heads))
                audited(self, done)

    def test_key_and_bound_use_the_same_formula(self):
        """残りの HP 40 のラッキー: 0 枚（30）と 1 枚（40）は結果が違うので別の組（``per × h`` のままのキーだと 0 と 10 で分け、代表の 0 枚（実際は 30）と 3 枚（実際は 60）をまとめてしまう）。"""
        classes = captured_classes(self.BOARDS["remaining_hp"]())
        self.assertNotEqual(classes.key_of(0), classes.key_of(1))
        self.assertEqual(classes.key_of(1), classes.key_of(5))  # 40 以上はどれもきぜつ（残りの HP にまとめる）
        # B = 抵抗力 30 + 残りの HP 40 + 10 = 80。b(h) = 30 + 10h ≥ B になる最小の h は 5（固定の値がなければ 8）
        self.assertEqual(classes.bound, 5)
        for heads in range(40):
            self.assertIn(classes.key_of(heads), classes.keys)

    def test_representatives_agree_with_enumeration(self):
        for name, make in self.BOARDS.items():
            state = make()
            with self.subTest(board=name):
                if name == "doubled":
                    with _doubled():
                        self._compare(state)
                else:
                    self._compare(state)

    def _compare(self, state):
        classes = captured_classes(state)
        for heads in range(classes.bound, classes.bound + classes.period * 20):
            self.assertEqual(classes.key_of(heads), classes.key_of(heads + classes.period), heads)
        n = min(classes.bound + classes.period * 4, 60)
        for mode in ("derived", "derived_full"):
            for heads in (0, 1, 2, min(classes.bound + 3, 40)):
                self.assertEqual(outcome(state, heads, mode), outcome(state, heads, mode, brute=n), (mode, heads))

    def test_order_decision_is_not_reflipped_and_survives_restore(self):
        """同じ段階の順番の決定（その数にする・加える）をまたいでも投げ直さない。基本となるダメージは続きの情報で運ぶ。"""
        state = board(scizor(), opponent=mon(H.CHANSEY))
        with _synthetic(DamageModifier(2, 60, "s", operation=SET), DamageModifier(2, 20, "a")):
            asked = pincer(state, 2)
            self.assertEqual(asked.decision.kind, DAMAGE_STEP_ORDER)
            self.assertEqual(asked.decision.context_value("base"), 50)
            for restored in (asked, pickle.loads(pickle.dumps(asked)), copy.deepcopy(asked)):
                done = answer(restored, (restored.decision.options[0],))
                self.assertEqual(new_events(asked, done, "coin_flip"), [])

    def test_unsupported_fixed_value_stops(self):
        """前提（固定の値がダメージカウンターの単位の倍数）を満たさない組はエンジンの未対応として止める（今の写しでは起こらない）。"""
        state = board(scizor(), opponent=mon(H.CHANSEY))
        res = K.Resolution(state.clone())
        attacker = res.state.players[0].active
        fs = res.open_frame(K.FrameKind.ATTACK, parent=None, player=0, source_pid=attacker.pokemon_id, attack_key=AttackKey(SCIZOR, 1))
        element = programs.Damage(programs.OPP, programs.HeadsUntilTails(10, fixed=35))
        run = programs.AttackRun(res, fs, (element,), res.state.definitions[SCIZOR].attacks[1])
        with self.assertRaises(Exception) as raised:
            unbounded.head_classes(run, element, 10)
        self.assertIn("unbounded_coin_preflight", str(raised.exception))


class _synthetic:
    """テスト専用: メタルニッパーのダメージ（相手の対戦ポケモンへ）に変更効果を足す（盤面を直接作った。今の写しにない計算の組み合わせ・順番の決定の確かめ）。"""

    def __init__(self, *modifiers):
        self.modifiers = modifiers

    def __enter__(self):
        real = E.attack_damage_modifiers
        extra = self.modifiers

        def fake(state, attacker, defender, *, attack=None, **kwargs):
            found = real(state, attacker, defender, attack=attack, **kwargs)
            if attack is not None and attack.card_id == SCIZOR and attacker is not defender:
                return tuple(found) + extra
            return found

        self.patches = [mock.patch.object(E, "attack_damage_modifiers", fake), mock.patch.object(K, "attack_damage_modifiers", fake)]
        for patch in self.patches:
            patch.start()
        return self

    def __exit__(self, *exc):
        for patch in self.patches:
            patch.stop()


def _doubled():
    return _synthetic(DamageModifier(8, 2, "x2", operation=MULTIPLY), DamageModifier(8, 40, "z", operation=ZERO_IF_BELOW))


# ---------------------------------------------------------------- 4・10 章: 期間と消える契機の共通の扱い・状態・書き出し・不変条件


class LifetimeTest(unittest.TestCase):
    def test_existing_types_keep_their_expiry(self):
        """既存の型（v0.91 まで）の期限は既定の値のまま（最後の番ははたらく番、「それ以後」は期限なし）。"""
        lock = CannotRetreat(1, 0, TURN, TURN + 1)
        self.assertEqual(end_turn(lock), TURN + 1)
        from kyuura_engine.state import AttackCoinCheck, CannotAttackWhileSourceActive

        self.assertIsNone(end_turn(AttackCoinCheck(1, 0, TURN, TURN + 1, lasting=True)))
        self.assertEqual(end_turn(CannotAttackWhileSourceActive(1, 0, TURN, TURN + 1)), TURN + 1)
        period = PeriodRetreatLock(1, 0, TURN, TURN, None, 3)
        self.assertIsNone(end_turn(period))
        with self.assertRaises(ValueError):
            PeriodAttackLock(1, 0, TURN, TURN + 1, TURN, 3)  # 最後の番がはたらき始める番より前
        with self.assertRaises(ValueError):
            PeriodRetreatLock(1, 0, TURN, TURN, None, 3, ends_on=("unknown",))

    def test_source_left_effect_left_behind_is_an_invariant_problem(self):
        """発生源がバトル場をはなれたら消える効果を、はなれたあとに残すのはエンジンの不具合（不変条件が見つける）。"""
        done = declare(board(mon(MURKROW, (DK,)), opponent=mon(H.CHANSEY, (W, W))), 0)
        self.assertEqual(check_invariants(done), [])
        broken = done.clone()
        p = broken.players[0]
        p.active, p.bench[0] = p.bench[0], p.active  # 受けた効果を消さずに発生源をベンチへ（呼び忘れの再現）
        self.assertTrue(any("発生源のポケモン" in problem for problem in check_invariants(broken)))

    def test_state_copies_keep_effects_and_answers(self):
        done = declare(board(mon(MURKROW, (DK,)), opponent=mon(H.CHANSEY, (W, W))), 0)
        for copied in (done.clone(), copy.deepcopy(done), pickle.loads(pickle.dumps(done))):
            self.assertEqual(copied.players[1].active.persistent_effects, done.players[1].active.persistent_effects)
            self.assertEqual(state_to_dict(copied, format_version=24), state_to_dict(done, format_version=24))
            rejects(self, copied, retreat_cmd(copied), "RETREAT_PREVENTED", IllegalActionError)

    def test_export_format_24_carries_the_new_kinds(self):
        """新しい種類は形式 24 の持続する効果・期限のある効果の値で表す（種類ごとの項目。v0.84・v0.86 と同じく形式は増やさない）。形式 1〜7 は持続する効果を表せないので拒否する。"""
        self.assertEqual(max(FORMAT_VERSIONS), 24)
        looked = declare(board(mon(MURKROW, (DK,)), opponent=mon(H.CHANSEY, (W, W))), 0)
        written = state_to_dict(looked, format_version=24)["players"][1]["active"]["persistent_effects"]
        self.assertEqual([(w["effect"], w["end_turn"], w["source_pokemon"], w.get("while_source_active"), w.get("ends_on")) for w in written],
                         [("period_retreat_lock", None, looked.players[0].active.pokemon_id, True, [SOURCE_LEAVES_ACTIVE])])
        screeched = declare(board(mon(ONIX, (F,)), opponent=mon(H.CHANSEY)), 0)
        written = state_to_dict(screeched, format_version=8)["players"][1]["active"]["persistent_effects"]
        self.assertEqual([(w["effect"], w["active_turn"], w["end_turn"], w["amount"], "ends_on" in w) for w in written],
                         [("received_attack_damage_bonus", TURN + 1, TURN + 2, 20, False)])
        with self.assertRaises(ValueError):
            state_to_dict(screeched, format_version=7)
        waved = declare(board(gengar(), opponent=mon(H.CHANSEY)), 0)
        record = state_to_dict(waved, format_version=24)["trainer_effects"][0]
        self.assertEqual((record["kind"], record["pokemon_id"], record["attack_index"], record["expires_turn"]),
                         (ATTACK_FIELD_POWER_SUPPRESSION, waved.players[0].active.pokemon_id, 0, TURN + 1))
        for state in (looked, screeched, waved):
            audited(self, state)

    def test_observation_shows_kinds_to_both_players(self):
        looked = declare(board(mon(MURKROW, (DK,)), opponent=mon(H.CHANSEY, (W, W))), 0)
        for viewer in (0, 1):
            self.assertEqual(observe(looked, viewer)["players"][1]["active"]["persistent_effects"], ["period_retreat_lock"])

    def test_legacy_preflight_does_not_claim_to_know_the_new_effects(self):
        from kyuura_engine.resolution.flow import legacy_unknown_features

        looked = declare(board(mon(MURKROW, (DK,)), opponent=mon(H.CHANSEY, (W, W))), 0)
        self.assertIn("v0.92 の持続する効果", legacy_unknown_features(looked, looked.players[1].active))
        waved = declare(board(gengar(), opponent=mon(H.CHANSEY)), 0)
        self.assertIn("やみのはどう", legacy_unknown_features(waved, waved.players[1].active))

    def test_period_effects_are_registered_types(self):
        from kyuura_engine.state import PERSISTENT_EFFECT_TYPES

        self.assertTrue(set(PERIOD_EFFECT_TYPES) <= set(PERSISTENT_EFFECT_TYPES))
        self.assertIn(CannotAttack, PERSISTENT_EFFECT_TYPES)


class NoCardIdBranchTest(unittest.TestCase):
    def test_engine_and_resolution_have_no_card_id_branches(self):
        for path in [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]:
            text = path.read_text(encoding="utf-8")
            for card in H.V0_92_CARDS:
                with self.subTest(path=path.name, card=card):
                    self.assertNotIn(f'"{card}"', text)


class DocumentTest(unittest.TestCase):
    def test_document_lists_the_cards_rulings_and_counts(self):
        text = DOC.read_text(encoding="utf-8")
        for card in H.V0_92_CARDS:
            self.assertIn(card, text)
        for ruling, code in (("DW1", DW1), ("DW2", DW2), ("DW3", DW3), ("ML2", ML2)):
            self.assertIn(ruling, text)
            self.assertIn(code, text)
        for word in ("1,127", "SOURCE_LEAVES_ACTIVE", "damage_for", "Z23", "G37", "SG1", "FA1", "POWER_SUPPRESSED"):
            self.assertIn(word, text)


class HiddenCardTest(unittest.TestCase):
    """10 章: 相手のうらのカード（マチスの秘策）について、受け付けるか・選べるものの数・相手の見るログが本当のカードによらない。"""

    def setUp(self):
        from tests import test_secret_plan_v0_67 as SP

        self.SP = SP

    def hidden(self, hidden, opponent):
        return self.SP.opponent_turn(self.SP.place(self.SP.board(hand=(hidden,), opponent=opponent, turn_number=TURN), hidden))

    def test_dark_wave_does_not_read_the_face_down_card(self):
        """やみのはどうは全体にはたらく効果なので、うらのカードはおもてにしない。本当のカードが特殊能力を持つか（バリヤード）で受け付けるか（DW2 の比べ）を変えない。"""
        from kyuura_engine.observation import visible_log

        views = []
        for hidden in (H.MR_MIME, H.RATTATA):
            state = self.hidden(hidden, mon(GENGAR, (P, P), played_turn=1))
            done = apply_kernel(state, UseAttack(1, 0))
            self.assertEqual(len(self.SP.face_down(done)), 1)
            self.assertNotIn("secret_plan_revealed", [e["kind"] for e in done.log])
            views.append(visible_log(done, 1)[len(state.log):])
            audited(self, done)
        self.assertEqual(views[0], views[1])

    def test_feint_attack_choices_do_not_depend_on_the_face_down_card(self):
        """だましうちの選べるものの数・止める選択は本当のカードによらない。選んだうらのカードはダメージを受ける時におもてにし、たねポケモンでなければトラッシュする。"""
        asked = {}
        for hidden in (H.PLUSPOWER, H.RATTATA):
            state = self.hidden(hidden, mon(MURKROW, (DK, W)))
            asking = apply_kernel(state, UseAttack(1, 1))
            pid = self.SP.face_down(state)[0].pokemon_id
            asked[hidden] = (asking.decision.options, asking.decision.context_value("unresolved_choices", ()))
            self.assertIn(pid, asking.decision.options)
            done = answer(asking, (pid,))
            self.assertEqual([e["cause"] for e in done.log if e["kind"] == "secret_plan_revealed"], ["damage"])
            self.assertEqual(done.players[0].find_by_pokemon_id(pid) is not None, hidden == H.RATTATA)
            audited(self, done)
        self.assertEqual(asked[H.PLUSPOWER], asked[H.RATTATA])

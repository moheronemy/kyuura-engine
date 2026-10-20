"""v0.59: 特殊能力を止める効果とエネルギーの扱いを変える 6 枚（docs/energy-control-power-suppression-v0.59.md）。

6 枚: マルマイン（第1弾。PMCG1-040。［エネエネ］・でんげき）・カツラ（PMCG6-093）・タケシの保護（PMCG5-090）・カスミのメノクラゲ（PMCG5-030。クリスタルビーム）・
わるいアーボック（PMCG4-008。ショックアイ・どくのきり）・まきちらせ!ベトベトガス（PMCG4-056）。どれも kyuura データの採用（採用したデータのコミット ecb2d69）と
pcg-search.com の同じ版のページとの照合（まきちらせ!ベトベトガスはサイトの説明文に「おたがいの場の」がない。kyuura への報告事項）。ガイドブックは読んでいない。

再利用した kyuura の記録: CR-CHEMICAL-GAS-USE-VS-POWER（「使えず」は宣言して使う特殊能力、「その力も消える」は常にはたらく・自動的にはたらく特殊能力。SUPPORTED）・
CR-CHEMICAL-GAS-ALL-POWERS（すべての特殊能力。CONFIRMED）・CR-POWER-BACK-AFTER-RECOVERY（p.265 のまきちらせ!ベトベトガスの解説「［かがくへんかガス］の力を一時的に消す」。
SUPPORTED）・CR-ENERGY-TRANS-NOT-ATTACHMENT（場のエネルギーのつけかえは手札からつけることではない）。

新しい停止コード: GG1・BL1・CB1・BZ1・BZ2・BZ3・BZ4。再利用: TR1（タケシの保護のつける先がない）・EM1（エネルギー・リムーブではがせるカードがない）・CH1・RB2。
"""

from __future__ import annotations

import pathlib
import unittest

from kyuura_engine import (
    AttachEnergy,
    EndTurn,
    EvolvePokemon,
    IllegalActionError,
    PlayBasicToBench,
    ResolveDecision,
    Retreat,
    UseAttack,
    UsePokemonPower,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool
from kyuura_engine.commands import command_to_dict
from kyuura_engine.continuous import goop_gas_effects, power_suppressed
from kyuura_engine.effects import COLORS, energy_unit_count
from kyuura_engine.persistent import energy_attach_blocked, powers_use_prevented
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import CannotAttachEnergy, CannotUsePowers, EnergyRole
from tests.helpers import (
    BLAINE_TRAINER,
    BLAINES_GROWLITHE,
    BLAINES_NINETALES,
    BLAINES_VULPIX,
    BLASTOISE,
    BROCKS_GEODUDE,
    BROCKS_PROTECTION,
    BULBASAUR,
    BUZZAP_ELECTRODE,
    DARK_ARBOK,
    ENERGY_REMOVAL,
    FIGHTING,
    FIRE,
    GOOP_GAS_ATTACK,
    GRASS,
    GROWLITHE,
    HITMONCHAN,
    IVYSAUR,
    LIGHTNING,
    MISTYS_TENTACOOL,
    MR_MIME,
    RATTATA,
    ROCKET_EKANS,
    SQUIRTLE,
    V0_59_CARDS,
    V0_59_POKEMON,
    V0_59_TRAINERS,
    VENUSAUR,
    VOLTORB,
    WARTORTLE,
    WATER,
    CoinSide,
    apply_kernel,
    with_coin_results,
)
from tests.log_audit import LATEST_FORMAT
from tests.test_instant_trainers_v0_55 import answer, board, card_of, pid, pokemon, use
from tests.test_stadium_reuse_special_energy_v0_58 import (
    assert_stops,
    audited,
    events,
    mon,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "energy-control-power-suppression-v0.59.md"
H, T = CoinSide.HEADS, CoinSide.TAILS
F, W, G, L = FIGHTING, WATER, GRASS, LIGHTNING
NEW_CODES = {
    "GG1": "UNRESOLVED_GOOP_GAS_NEW_POKEMON",
    "BL1": "UNRESOLVED_BLAINE_SECOND_ATTACH",
    "CB1": "UNRESOLVED_ATTACH_BLOCK_SCOPE",
    "BZ1": "UNRESOLVED_BUZZAP_OPPONENT_TARGET",
    "BZ2": "UNRESOLVED_BUZZAP_ENERGY_CARD_TYPE",
    "BZ3": "UNRESOLVED_BUZZAP_COLOR",
    "BZ4": "UNRESOLVED_BUZZAP_DISGUISED",
}
BLASTOISE_MON = {"card": BLASTOISE, "evolved_from": [SQUIRTLE, WARTORTLE]}
VENUSAUR_MON = {"card": VENUSAUR, "evolved_from": [BULBASAUR, IVYSAUR]}


def electrode(energy=(), **extra):
    return {"card": BUZZAP_ELECTRODE, "evolved_from": VOLTORB, "energy": list(energy), **extra}


def arbok(energy=(G, G, G)):
    return {"card": DARK_ARBOK, "evolved_from": ROCKET_EKANS, "energy": list(energy)}


def end_turns(state, count):
    """``count`` 回、番のプレイヤーの番を終える（決定があれば最初の選べるもので答える）。"""
    for _ in range(count):
        state = apply_kernel(state, EndTurn(state.current_player))
        while state.decision is not None:
            state = answer(state, (state.decision.options[0],))
    return state


class CardDataTest(unittest.TestCase):
    def test_six_cards_are_supported_and_counted(self):
        pool = load_card_pool()
        for card_id in V0_59_CARDS:
            self.assertTrue(pool.get(card_id).supported, card_id)
            self.assertTrue(pool.is_playable(card_id), card_id)
        self.assertEqual({pool.get(c).category for c in V0_59_POKEMON}, {"pokemon"})
        self.assertEqual({pool.get(c).category for c in V0_59_TRAINERS}, {"trainer"})
        counts = {}
        for definition in pool.definitions.values():
            if definition.supported:
                counts[definition.category] = counts.get(definition.category, 0) + 1
        # v0.58 の 329・81・10（420）から、ポケモン 3 枚・トレーナー 3 枚を加えた（332・84・10）。v0.60 でポケモン 4 枚を加えた
        self.assertEqual((counts["pokemon"], counts["trainer"], counts["energy"]), (585, 211, 30))  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.74 で拡張パック以外の商品のスタジアム 13 枚  # v0.73 で拡張パック以外の商品のトレーナー 18 枚  # v0.72 で拡張パック以外の商品のポケモン 43 枚  # v0.71 で拡張パック以外の商品の再録 78 枚（ポケモン 11・トレーナー 67）  # v0.70 で拡張パック以外の商品のポケモン 82 枚  # v0.69 で拡張パック以外の商品の同じカード 96 枚（ポケモン 57・トレーナー 19・エネルギー 20）  # v0.68 でポケモン 3 枚  # v0.67 でトレーナー 1 枚  # v0.61 でポケモン 3 枚・トレーナー 1 枚を加えた  # v0.62 でポケモン 6 枚を加えた  # v0.63 でトレーナー 4 枚を加えた  # v0.64 でポケモン 3 枚を加えた  # v0.65 でポケモン 2 枚・トレーナー 1 枚を加えた  # v0.66 でトレーナー 3 枚を加えた

    def test_registrations(self):
        reg = E.DEFAULT_EFFECTS
        self.assertIsInstance(reg.power_entry(BUZZAP_ELECTRODE, 0).effect, E.ConvertSelfToEnergy)
        self.assertEqual(reg.attack_entry(BUZZAP_ELECTRODE, 0).effect, E.SelfDamageOnTails(10))
        self.assertIsInstance(reg.attack_entry(MISTYS_TENTACOOL, 0).effect, E.DamageThenAttachLockOnHeads)
        self.assertIsInstance(reg.attack_entry(DARK_ARBOK, 0).effect, E.ChooseOpponentPokemonDamageAndPowerLock)
        self.assertIsInstance(reg.attack_entry(DARK_ARBOK, 1).effect, E.DamagePoisonAndBenchDamage)
        self.assertIsInstance(reg.trainer_entry(BROCKS_PROTECTION).effect, E.ProtectAttachedEnergy)
        blaine, goop = reg.trainer_entry(BLAINE_TRAINER).effect, reg.trainer_entry(GOOP_GAS_ATTACK).effect
        self.assertEqual(blaine.turn_effect_terms()[:2], ("fire_double_attach", 0))
        self.assertEqual(goop.turn_effect_terms()[:2], ("power_suppression", 1))
        # 錯乱ジムで相手が使うと「次の相手の番」が決まらない（CH1）。カツラは「この番だけ」で、使ったプレイヤーの番
        self.assertTrue(goop.refers_to_user_turn)

    def test_ruling_ids_are_in_the_document(self):
        text = DOC.read_text(encoding="utf-8")
        for ruling, code in NEW_CODES.items():
            self.assertIn(ruling, text)
            self.assertIn(code, text)
        self.assertEqual(LATEST_FORMAT, 22)  # v0.67 で 22
        self.assertEqual(max(FORMAT_VERSIONS), 22)  # v0.67 で 22（face_down_cards）


class GoopGasTest(unittest.TestCase):
    """まきちらせ!ベトベトガス: 使った番から次の相手の番の終わりまで、場のすべての特殊能力を使えず、その力も消える（CR-CHEMICAL-GAS-USE-VS-POWER・
    CR-CHEMICAL-GAS-ALL-POWERS）。"""

    def used(self, **kwargs):
        state = use(board((GOOP_GAS_ATTACK,), **kwargs), GOOP_GAS_ATTACK)
        audited(self, state)
        return state

    def test_declared_power_cannot_be_used(self):
        """使ったプレイヤー自身のポケモンも止まる（「おたがいの場の」）。あまごいは POWER_SUPPRESSED（状態・ログ・乱数は変わらない）。"""
        state = use(board((GOOP_GAS_ATTACK, W), active=mon(BLASTOISE, (W,), evolved_from=[SQUIRTLE, WARTORTLE])), GOOP_GAS_ATTACK)
        self.assertTrue(goop_gas_effects(state))
        b = state.players[0].active
        assert_stops(self, state, UsePokemonPower(0, b.pokemon_id, 0, energy=card_of(state, W), target=b.pokemon_id), "POWER_SUPPRESSED",
                     error=IllegalActionError)

    def test_continuous_power_also_vanishes(self):
        """［なぞのかべ］（30 以上のダメージを 0 にする）も消える。スペシャルパンチ 40 で相手のバリヤード（HP 40）がきぜつする。"""
        base = {"active": mon(HITMONCHAN, (F, F, F)), "opponent_active": mon(MR_MIME, ())}
        without = apply_kernel(board((), **base), UseAttack(0, 1))
        self.assertEqual(pokemon(without, without.players[1].active.pokemon_id).damage, 0)
        state = self.used(**base)
        after = apply_kernel(state, UseAttack(0, 1))
        self.assertTrue(any(e["kind"] == "knock_out" for e in after.log))
        audited(self, after)

    def test_chemical_gas_is_also_stopped_and_power_returns_after_expiry(self):
        """かがくへんかガスも止まる（除かない）。効果は次の相手の番の終わりに消え、特殊能力の力がもどる（CR-POWER-BACK-AFTER-RECOVERY の読み方）。"""
        state = self.used(active=mon(BLASTOISE, (W,), evolved_from=[SQUIRTLE, WARTORTLE]))
        power = load_card_pool().get(BLASTOISE).powers[0]
        self.assertTrue(power_suppressed(state, power))
        opponent_turn = end_turns(state, 1)
        self.assertEqual(opponent_turn.turn_number, 8)
        self.assertTrue(goop_gas_effects(opponent_turn))
        back = end_turns(opponent_turn, 1)
        self.assertEqual(back.turn_number, 9)
        self.assertFalse(goop_gas_effects(back))
        self.assertFalse(power_suppressed(back, power))
        self.assertTrue(any(e["kind"] == "trainer_effect_removed" for e in back.log))
        audited(self, back)

    def test_gg1_new_pokemon_with_powers(self):
        """GG1: 効果のはたらく間に、特殊能力を持つポケモンが場に出る・進化する（使った時点で場にいたポケモンだけを止めるかが決まらない）。特殊能力を持たない
        ポケモンは止めない。"""
        state = use(board((GOOP_GAS_ATTACK, BLASTOISE, MR_MIME, RATTATA), active=mon(HITMONCHAN, (F,)),
                          bench=({"card": WARTORTLE, "evolved_from": SQUIRTLE},)), GOOP_GAS_ATTACK)
        wartortle = state.players[0].bench[0]
        assert_stops(self, state, EvolvePokemon(0, card_of(state, BLASTOISE), wartortle.pokemon_id), NEW_CODES["GG1"])
        assert_stops(self, state, PlayBasicToBench(0, card_of(state, MR_MIME)), NEW_CODES["GG1"])
        bench = apply_kernel(state, PlayBasicToBench(0, card_of(state, RATTATA)))  # 特殊能力を持たないたねポケモンは出せる
        audited(self, bench)


class ShockEyeTest(unittest.TestCase):
    """わるいアーボックのショックアイ・どくのきり。"""

    def test_bench_target_cannot_use_declared_power(self):
        state = board(active=arbok((G, G)), opponent_active=mon(HITMONCHAN, (F,)), opponent_bench=(dict(BLASTOISE_MON, energy=[W]),), opponent_hand=(W,))
        chosen = apply_kernel(state, UseAttack(0, 0))
        target = chosen.players[1].bench[0].pokemon_id
        self.assertIn(target, chosen.decision.options)
        after = answer(chosen, (target,))
        audited(self, after)
        hit = pokemon(after, target)
        self.assertEqual(hit.damage, 10)  # 弱点・抵抗力に関係なく 10
        self.assertTrue(any(isinstance(e, CannotUsePowers) for e in hit.persistent_effects))
        self.assertIsNotNone(powers_use_prevented(after, hit))
        self.assertFalse(power_suppressed(after, load_card_pool().get(BLASTOISE).powers[0]))  # 力は消さない（使うことだけができない）
        opponent = after  # ワザのあと、番は相手（8 番）に移っている
        self.assertEqual((opponent.turn_number, opponent.current_player), (8, 1))
        b = pokemon(opponent, target)
        assert_stops(self, opponent, UsePokemonPower(1, b.pokemon_id, 0, energy=card_of(opponent, W, player=1), target=b.pokemon_id),
                     "POWER_USE_PREVENTED", error=IllegalActionError)
        later = end_turns(opponent, 1)
        self.assertIsNone(powers_use_prevented(later, pokemon(later, target)))
        audited(self, later)

    def test_poison_vapor(self):
        state = board(active=arbok(), opponent_active=mon(HITMONCHAN, ()), opponent_bench=(RATTATA, RATTATA))
        after = apply_kernel(state, UseAttack(0, 1))
        audited(self, after)
        self.assertIsNotNone(after.players[1].active.conditions.poison)
        self.assertEqual([p.damage for p in after.players[1].bench], [10, 10])


class CrystalBeamTest(unittest.TestCase):
    def beamed(self, coin=H):
        state = board(active=mon(MISTYS_TENTACOOL, (W, W)), opponent_active=dict(BLASTOISE_MON, energy=[W]),
                      opponent_bench=(dict(VENUSAUR_MON, energy=[G]),), opponent_hand=(W, W))
        after = apply_kernel(with_coin_results(state, coin), UseAttack(0, 0))
        audited(self, after)
        return after

    def test_heads_blocks_attaching_during_next_opponent_turn(self):
        after = self.beamed(H)
        self.assertTrue(any(isinstance(e, CannotAttachEnergy) for e in after.players[1].active.persistent_effects))
        turn = after  # ワザのあと、番は相手（8 番）に移っている
        self.assertEqual((turn.turn_number, turn.current_player), (8, 1))
        active = turn.players[1].active
        self.assertIsNotNone(energy_attach_blocked(turn, active))
        assert_stops(self, turn, AttachEnergy(1, card_of(turn, W, player=1), active.card), "ENERGY_ATTACH_PREVENTED", error=IllegalActionError)
        # あまごい（手札からつける特殊能力）も止まる
        assert_stops(self, turn, UsePokemonPower(1, active.pokemon_id, 0, energy=card_of(turn, W, player=1), target=active.pokemon_id),
                     "ENERGY_ATTACH_PREVENTED", error=IllegalActionError)
        # エナジートランス（場のエネルギーのつけかえ）が「つける」に当たるかは決まらない（CB1）
        venusaur = turn.players[1].bench[0]
        assert_stops(self, turn, UsePokemonPower(1, venusaur.pokemon_id, 0, energy=venusaur.energy[0], source=venusaur.pokemon_id,
                                                 target=active.pokemon_id), NEW_CODES["CB1"])
        # 受けていないポケモンにはつけられる
        ok = apply_kernel(turn, AttachEnergy(1, card_of(turn, W, player=1), venusaur.card))
        audited(self, ok)
        later = end_turns(turn, 1)
        self.assertIsNone(energy_attach_blocked(later, later.players[1].active))

    def test_tails_has_no_effect(self):
        after = self.beamed(T)
        self.assertFalse(after.players[1].active.persistent_effects)


class BlaineTest(unittest.TestCase):
    def setUp(self):
        self.base = board((BLAINE_TRAINER, FIRE, FIRE, FIRE, WATER), active=mon(BLAINES_GROWLITHE, ()), bench=(GROWLITHE,))
        self.used = use(self.base, BLAINE_TRAINER)

    def fires(self, state):
        return [u for u in state.players[0].hand if state.cards[u].card_id == FIRE]

    def test_two_fire_cards_in_one_operation(self):
        state = self.used
        fire = self.fires(state)
        target = state.players[0].active
        after = apply_kernel(state, AttachEnergy(0, fire[0], target.card, energy2=fire[1]))
        audited(self, after)
        self.assertEqual(after.players[0].active.energy, [fire[0], fire[1]])
        self.assertEqual(after.energy_attachments_this_turn, 2)
        log = events(after, "attach_energy")[-1]
        self.assertEqual((log["energy2"], log["trainer_card"]), (fire[1], card_of(self.base, BLAINE_TRAINER)))
        with self.assertRaises(IllegalActionError) as caught:
            apply_kernel(after, AttachEnergy(0, fire[2], target.card))
        self.assertEqual(caught.exception.code, "ENERGY_ALREADY_ATTACHED")

    def test_illegal_double_attaches(self):
        fire = self.fires(self.used)
        active, bench = self.used.players[0].active, self.used.players[0].bench[0]
        cases = [
            (self.base, AttachEnergy(0, card_of(self.base, FIRE), active.card, energy2=self.fires(self.base)[1]), "DOUBLE_ATTACH_NOT_ALLOWED"),
            (self.used, AttachEnergy(0, fire[0], bench.card, energy2=fire[1]), "DOUBLE_ATTACH_NOT_ALLOWED"),  # 「カツラのポケモン」でない
            (self.used, AttachEnergy(0, fire[0], active.card, energy2=card_of(self.used, WATER)), "NOT_FIRE_ENERGY"),
            (self.used, AttachEnergy(0, fire[0], active.card, energy2=fire[0]), "DUPLICATE_CHOICE"),
        ]
        for state, command, code in cases:
            with self.subTest(code=code):
                assert_stops(self, state, command, code, error=IllegalActionError)

    def test_second_operation_after_one_card_is_bl1(self):
        fire = self.fires(self.used)
        one = apply_kernel(self.used, AttachEnergy(0, fire[0], self.used.players[0].active.card))
        audited(self, one)
        assert_stops(self, one, AttachEnergy(0, fire[1], one.players[0].active.card), NEW_CODES["BL1"])

    def test_effect_lasts_only_this_turn(self):
        after = end_turns(self.used, 1)
        self.assertFalse(E.blaine_effects(after, 0))

    def test_command_dict_omits_energy2(self):
        self.assertNotIn("energy2", command_to_dict(AttachEnergy(0, 1, 2)))
        self.assertEqual(command_to_dict(AttachEnergy(0, 1, 2, energy2=3))["energy2"], 3)


class BrocksProtectionTest(unittest.TestCase):
    def attached(self):
        state = board((BROCKS_PROTECTION,), active=mon(BROCKS_GEODUDE, (F, F)), bench=(mon(RATTATA, (F,)),),
                      opponent_hand=(ENERGY_REMOVAL,), opponent_active=mon(HITMONCHAN, (F,)))
        state = use(state, BROCKS_PROTECTION)
        while state.decision is not None:
            state = answer(state, (pid(state, 0, BROCKS_GEODUDE),))
        audited(self, state)
        return state

    def test_stays_attached_and_blocks_opponent_trainer_removal(self):
        state = self.attached()
        geodude = state.players[0].active
        self.assertEqual([state.cards[t.card].card_id for t in geodude.trainers], [BROCKS_PROTECTION])
        self.assertIsNone(geodude.trainers[0].discard_at_end_of_turn)
        turn = end_turns(state, 1)
        self.assertEqual(len(turn.players[0].active.trainers), 1)  # 番の終わりにトラッシュしない
        removal = use(turn, ENERGY_REMOVAL, player=1)
        options = set(removal.decision.options) if removal.decision is not None else set()
        self.assertFalse(options & set(turn.players[0].active.energy))  # 守られているカードは選べない
        audited(self, removal)

    def test_only_protected_energy_is_em1(self):
        state = board((BROCKS_PROTECTION,), active=mon(BROCKS_GEODUDE, (F, F)), bench=(RATTATA,), opponent_hand=(ENERGY_REMOVAL,))
        state = use(state, BROCKS_PROTECTION)
        while state.decision is not None:
            state = answer(state, (state.decision.options[0],))
        turn = end_turns(state, 1)
        assert_stops(self, turn, card_play(turn, ENERGY_REMOVAL, 1), "UNRESOLVED_ENERGY_REMOVAL_WITHOUT_TARGET")

    def test_without_brocks_pokemon_is_tr1(self):
        state = board((BROCKS_PROTECTION,), active=mon(HITMONCHAN, (F,)))
        assert_stops(self, state, card_play(state, BROCKS_PROTECTION, 0), "UNRESOLVED_TRAINER_WITHOUT_TARGET")


def card_play(state, card_id, player):
    from kyuura_engine import PlayTrainer

    return PlayTrainer(player, card_of(state, card_id, player=player))


class BuzzapTest(unittest.TestCase):
    """マルマインの［エネエネ］: みずから「きぜつ」し、自分の場のほかのポケモンに、選んだ色のエネルギー 2 個分としてつく。"""

    def board(self, **kwargs):
        defaults = {"active": mon(HITMONCHAN, (F,)), "bench": (electrode(), RATTATA)}
        defaults.update(kwargs)
        return board(**defaults)

    def declare(self, state):
        e = next(p for p in state.players[0].in_play() if state.cards[p.card].card_id == BUZZAP_ELECTRODE)
        return apply_kernel(state, UsePokemonPower(0, e.pokemon_id, 0)), e

    def test_full_flow(self):
        state = self.board()
        declared, e = self.declare(state)
        hitmonchan = state.players[0].active
        self.assertIn(hitmonchan.pokemon_id, declared.decision.options)
        opponent = declared.players[1].active.pokemon_id
        self.assertIn(opponent, declared.decision.context_value("unresolved_choices"))  # BZ1
        colored = answer(declared, (hitmonchan.pokemon_id,))
        self.assertEqual(colored.decision.options, tuple(range(len(COLORS))))
        after = answer(colored, (COLORS.index(EnergyType.FIGHTING),))
        audited(self, after)
        card = e.card
        knock = events(after, "knock_out")[-1]
        self.assertEqual((knock["timing"], knock["to_energy"]), ("power", card))
        self.assertEqual(after.energy_roles, (EnergyRole(card, EnergyType.FIGHTING, 2, 0, state.turn_number),))
        self.assertIn(card, after.players[0].active.energy)
        self.assertNotIn(card, after.players[0].discard)
        self.assertEqual(after.card_def(card).category, "energy")
        self.assertEqual(energy_unit_count(after, after.players[0].active.energy, after.players[0].active), 3)
        self.assertEqual(after.decision.kind, "take_prize")  # 相手がサイドを取る
        self.assertEqual(after.decision.player, 1)
        taken = answer(after, (0,))
        attack = apply_kernel(taken, UseAttack(0, 1))  # スペシャルパンチ（闘闘無）を、闘 1 枚とエネエネの 2 個で払える
        self.assertEqual(events(attack, "attack")[-1]["attack"], "スペシャルパンチ")
        audited(self, attack)
        # 書き出しの形式 19。形式 1〜18 は ValueError
        self.assertEqual(state_to_dict(taken, format_version=19)["energy_roles"][0]["energy_type"], "fighting")
        with self.assertRaises(ValueError):
            state_to_dict(taken, format_version=18)

    def test_role_ends_when_the_card_leaves(self):
        """エネルギーとしての役割は、カードが場のポケモンについているあいだだけ（実装上の判断）。トラッシュしたら印刷のポケモンのカードにもどり、記録も消える。"""
        state = self.board(active=mon(HITMONCHAN, ()))
        declared, e = self.declare(state)
        after = answer(answer(answer(declared, (state.players[0].active.pokemon_id,)), (COLORS.index(EnergyType.FIGHTING),)), (0,))
        retreat = apply_kernel(after, Retreat(0, (e.card,), after.players[0].bench[0].card))
        audited(self, retreat)
        self.assertIn(e.card, retreat.players[0].discard)
        self.assertEqual(retreat.energy_roles, ())
        self.assertEqual(retreat.card_def(e.card).category, "pokemon")

    def test_stops(self):
        state = self.board()
        declared, _ = self.declare(state)
        opponent = declared.players[1].active.pokemon_id
        assert_stops(self, declared, ResolveDecision(0, declared.decision.id, (opponent,)), NEW_CODES["BZ1"])
        colored = answer(declared, (state.players[0].active.pokemon_id,))
        for color in (EnergyType.COLORLESS,):
            assert_stops(self, colored, ResolveDecision(0, colored.decision.id, (COLORS.index(color),)), NEW_CODES["BZ3"])
        # BZ2: つける先がエネルギーカードをつけたときにはたらく特殊能力（ほのおでかいふく）を持ち、その色
        ninetales = self.board(active={"card": BLAINES_NINETALES, "evolved_from": BLAINES_VULPIX, "energy": []})
        declared2, _ = self.declare(ninetales)
        colored2 = answer(declared2, (ninetales.players[0].active.pokemon_id,))
        assert_stops(self, colored2, ResolveDecision(0, colored2.decision.id, (COLORS.index(EnergyType.FIRE),)), NEW_CODES["BZ2"])

    def test_cannot_use(self):
        asleep = self.board(active=electrode(sleep=True), bench=(RATTATA,))
        e = asleep.players[0].active
        assert_stops(self, asleep, UsePokemonPower(0, e.pokemon_id, 0), "POKEMON_ASLEEP", error=IllegalActionError)
        alone = board(active=electrode(), bench=())
        assert_stops(self, alone, UsePokemonPower(0, alone.players[0].active.pokemon_id, 0), NEW_CODES["BZ1"])
        gas = use(board((GOOP_GAS_ATTACK,), active=mon(HITMONCHAN, ()), bench=(electrode(),)), GOOP_GAS_ATTACK)
        e = gas.players[0].bench[0]
        assert_stops(self, gas, UsePokemonPower(0, e.pokemon_id, 0), "POWER_SUPPRESSED", error=IllegalActionError)


class InteractionTest(unittest.TestCase):
    def test_buzzap_onto_crystal_beamed_pokemon_is_cb1(self):
        """クリスタルビームを受けたポケモンに［エネエネ］でつけることが「エネルギーカードをつける」に当たるかは決まらない（CB1）。選べるが選ぶと止める。
        自分の場のほかのポケモンがどれも止まるなら宣言の前に止める。"""
        state = board(active=mon(MISTYS_TENTACOOL, (W, W)), opponent_active=mon(HITMONCHAN, ()), opponent_bench=(electrode(),))
        beamed = apply_kernel(with_coin_results(state, H), UseAttack(0, 0))
        e = beamed.players[1].bench[0]
        assert_stops(self, beamed, UsePokemonPower(1, e.pokemon_id, 0), NEW_CODES["CB1"])

    def test_shock_eye_on_guts_target_is_g37(self):
        """ショックアイのダメージで、こんじょうを使える相手の対戦ポケモンが HP 以上になりうるとき、そのあとの効果（特殊能力を使えなくする）を受けるかは既存の
        G37（``UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT``）の問い。新しいコードにしない。"""
        from tests.helpers import GIOVANNIS_MACHAMP

        machamp = {"card": GIOVANNIS_MACHAMP, "evolved_from": ["PMCG6-057", "PMCG6-059"], "damage": 90}
        state = board(active=arbok(), opponent_active=machamp, opponent_bench=(RATTATA,))
        assert_stops(self, state, UseAttack(0, 0), "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT")  # 宣言の前（相手のどのポケモンを選ぶかによらない）

    def test_shock_eye_blocks_rebirth_offer(self):
        """ショックアイを受けた R団のファイヤーが、効果のはたらく間（ポケモンチェックのどく）にきぜつしても、ふしちょう（宣言して使う特殊能力）を使うかの決定を
        出さない（使うことができない。``catalog.offer_stopped``）。効果のないどくのきりでは出す。"""
        from tests.helpers import ROCKETS_MOLTRES

        for locked in (False, True):
            with self.subTest(locked=locked):
                moltres = {"card": ROCKETS_MOLTRES, "damage": 40, "poison": 10}
                state = board(active=arbok(), opponent_active=moltres, opponent_bench=(RATTATA,))
                if locked:
                    chosen = apply_kernel(state, UseAttack(0, 0))
                    after = answer(chosen, (chosen.players[1].active.pokemon_id,))
                else:
                    after = apply_kernel(state, UseAttack(0, 1))
                self.assertTrue(any(e["kind"] == "knock_out" for e in after.log))  # ポケモンチェックのどくで HP 60 以上
                while after.decision is not None and after.decision.kind == "take_prize":
                    after = answer(after, (after.decision.options[0],))
                offered = after.decision is not None and after.decision.kind == "post_knockout_power"
                self.assertEqual(offered, not locked)
                audited(self, after)


class InvariantTest(unittest.TestCase):
    def test_energy_roles_are_checked(self):
        state = board(active=mon(HITMONCHAN, ()), bench=(electrode(), RATTATA))
        e = state.players[0].bench[0]
        declared = apply_kernel(state, UsePokemonPower(0, e.pokemon_id, 0))
        after = answer(answer(declared, (state.players[0].active.pokemon_id,)), (COLORS.index(EnergyType.FIGHTING),))
        self.assertEqual(check_invariants(after), [])
        broken = after.clone()
        broken.energy_roles = (EnergyRole(e.card, EnergyType.FIGHTING, 3, 0, after.turn_number),)
        self.assertTrue(check_invariants(broken))


if __name__ == "__main__":
    unittest.main()

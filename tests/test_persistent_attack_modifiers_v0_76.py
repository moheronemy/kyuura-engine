"""v0.76: 拡張パック以外の商品の、持続する効果・ワザの使用の制限を中心とするポケモン 24 枚（ワザ 48）（docs/persistent-attack-modifiers-v0.76.md）。

24 枚: マチスのコラッタ（GD3-011）・ニドラン♂（ES1-007・QSG-005）・ゼニガメ（ES1-015・QSG-013・IP2-018）・マリル（PRN-028）・ヒトカゲ（ES1-013・QSG-007）・ドードー
（ES1-028・QSG-041）・パウワウ（ES2-006・QSG-017）・ピカチュウ（IP1-040）・チコリータ（PF1-001）・ヤドン（PR1-006）・コンパン（ES3-004）・ワンリキー（ES2-021・QSG-035）・
ヒノアラシ（PF1-004）・ウパー（PRN-003）・ワニノコ（PRN-008・PRN-011）・ガーディ（IP2-026）。どれも kyuura データの採用（採用したデータのコミット 7d3f4ca。処理に使う文面は
kyuura の印刷の文面）。ガイドブックは読んでいない。kyuura の日本語の文面は pcg-search.com の転記なので外部照合はしていない。根拠は一般の規定の記録（kyuura の
GR-2000-P309-ATTACK-PROCEDURE・GR-2000-P321-DAMAGE-ORDER・GR-2000-P322-PERSISTENT-EFFECTS・GR-2000-P321-PREVENTED-ELEMENTS・RUL-ENERGY-DISCARD-ATTACKS）と
エンジンの過去の版の処理（v0.27 のつるぎのまい・v0.34 のなきつく・v0.35 のきあいだめ・あわあわ・ドわすれ・v0.40 のすごむ・v0.49 のワザの出どころ）。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import subprocess
import unittest

from kyuura_engine import (
    EndTurn,
    EvolvePokemon,
    IllegalActionError,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import (
    Retreat as RetreatCommand,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    DAMAGE_STEP_ORDER,
    SELECT_ATTACK,
    SELECT_OPPONENT_ATTACK,
)
from kyuura_engine.persistent import expires_at_turn_start, reduced_damage_to_source
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.resolution import programs as PG
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import (
    PERSISTENT_EFFECT_TYPES,
    CannotAttackWhileSourceActive,
    CannotUseAttack,
    CannotUseOwnAttack,
    NextTurnAttackDamage,
    ReducedDamageToSource,
    ReducedDamageToSourceNextTurn,
)
from tests.helpers import (
    ATTACK_TYPES_SINCE_V0_17,
    CHARMANDER_ES1,
    CHARMANDER_QSG,
    CHIKORITA_PF1,
    CLEFAIRY,
    CUBONE,
    CYNDAQUIL_PF1,
    DODUO_ES1,
    DODUO_QSG,
    FIGHTING,
    FIRE,
    GASTLY,
    GRASS,
    GROWLITHE_ES3,
    GROWLITHE_IP2,
    GUST,
    HAUNTER,
    HITMONCHAN,
    HITMONLEE,
    JYNX,
    LT_SURGES_RATTATA,
    LT_SURGES_RATTATA_GD3,
    MACHOKE,
    MACHOP_ES2,
    MACHOP_QSG,
    MARILL_PRN,
    MISTYS_POLIWAG,
    MYSTERIOUS_FOSSIL,
    NIDORAN_M_ES1,
    NIDORAN_M_QSG,
    PIKACHU_IP1,
    PLUSPOWER,
    PSYCHIC,
    RATTATA,
    SABRINAS_ABRA,
    SABRINAS_ALAKAZAM,
    SABRINAS_KADABRA,
    SEEL_ES2,
    SEEL_QSG,
    SLOWPOKE_PR1,
    SQUIRTLE_ES1,
    SQUIRTLE_IP2,
    SQUIRTLE_QSG,
    TOTODILE_PRN,
    TOTODILE_PRN_B,
    V0_76_POKEMON,
    VENONAT_ES3,
    WATER,
    WOOPER_PRN,
    apply_kernel,
    with_coin_results,
)
from tests.log_audit import (
    coin_gated_effect_problems,
    observation_problems,
    serialization_problems,
)
from tests.test_barrier_resume_coin_bonus_v0_34 import with_barrier
from tests.test_instant_trainers_v0_55 import TURN, board, mon, use

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "persistent-attack-modifiers-v0.76.md"
H, T = CoinSide.HEADS, CoinSide.TAILS
DECK = [WATER] * 12


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])
    test.assertEqual(coin_gated_effect_problems(state, [dict(e) for e in state.log]), [])


def snapshot(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


def attack(state, index, *coins, player=None, **options):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, UseAttack(state.current_player if player is None else player, index), **options)


def answer(state, choices):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)))


def end(state):
    return apply_kernel(state, EndTurn(state.current_player))


def rejects(test, state, command, code, error=UnsupportedError):
    before = snapshot(state)
    with test.assertRaises(error) as caught:
        apply_kernel(state, command)
    test.assertEqual(caught.exception.code, code)
    test.assertEqual(snapshot(state), before)  # 状態・ログ・乱数・決定は変わらない
    return caught.exception


def last_damage(state):
    return [e for e in state.log if e["kind"] == "damage"][-1]


def coins_of(state, before):
    return [e["result"] for e in state.log[len(before.log):] if e["kind"] == "coin_flip"]


def effects_of(state, player, kind=None):
    active = state.players[player].active
    return [e for e in active.persistent_effects if kind is None or isinstance(e, kind)]


def game(active, opponent_active=None, *, hand=(), bench=(RATTATA,), opponent_bench=(RATTATA,), opponent_hand=()):
    return board(list(hand), active=active, bench=bench, deck=DECK, opponent_active=opponent_active or mon(HITMONCHAN, (FIGHTING, FIGHTING)),
                 opponent_bench=opponent_bench, opponent_deck=DECK, opponent_hand=opponent_hand)


class RegistrationTest(unittest.TestCase):
    def test_registered_and_classified(self):
        """24 枚とも写しの組 pool_v0_76 にあり、どのワザも登録した（48。登録の照合と型）。すべてたねポケモン・ワザ 2 つ・特殊能力なし。"""
        extract = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text(encoding="utf-8"))
        self.assertEqual(tuple(extract["pool_v0_76"]), V0_76_POKEMON)
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS
        count = 0
        for card_id in V0_76_POKEMON:
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertIn(card_id, pool.playable_ids)
                self.assertEqual((definition.stage, len(definition.attacks), len(definition.powers)), ("basic", 2, 0))
                for index, attack_def in enumerate(definition.attacks):
                    entry = registry.attack_entry(card_id, index)
                    self.assertIsNotNone(entry)
                    self.assertEqual(entry.effect.check(attack_def), [])
                    self.assertEqual(entry.effect.card_problems(attack_def, definition.attacks), [])
                    count += 1
                    if attack_def.text_ja is not None:
                        self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (attack_def.text_ja, attack_def.text_ja, "kyuura data/cards.json"))
        self.assertEqual(count, 48)
        kinds = {(c, i): type(registry.attack_entry(c, i).effect) for c in V0_76_POKEMON for i in range(2)}
        self.assertEqual(kinds[(LT_SURGES_RATTATA_GD3, 0)], E.MultiplyNextTurnAttackDamage)
        self.assertEqual(kinds[(NIDORAN_M_ES1, 1)], E.FailOnTailsDamage)
        self.assertEqual(kinds[(MARILL_PRN, 0)], E.SetNextTurnAttackDamage)
        self.assertEqual(kinds[(MARILL_PRN, 1)], E.ParalyzeOnHeads)
        for growl in (CHARMANDER_ES1, DODUO_ES1, SEEL_ES2, PIKACHU_IP1, CHIKORITA_PF1):
            self.assertEqual(kinds[(growl, 0)], E.ReduceDamageToSelfNextOpponentTurn)
        self.assertEqual(kinds[(SLOWPOKE_PR1, 1)], E.LockOpponentAttack)
        self.assertEqual(kinds[(VENONAT_ES3, 0)], E.LockOpponentAttackOnHeads)
        self.assertEqual(kinds[(VENONAT_ES3, 1)], E.ConfuseOnHeads)
        self.assertEqual(kinds[(MACHOP_ES2, 0)], E.CoinNextTurnMultiplyElseLockAttack)
        for leer in (CYNDAQUIL_PF1, WOOPER_PRN, TOTODILE_PRN):
            self.assertEqual(kinds[(leer, 0)], E.AttackLockWhileSourceActiveOnHeads)
        self.assertEqual(kinds[(CYNDAQUIL_PF1, 1)], E.DamageIgnoringDefenderEffects)
        self.assertEqual(kinds[(WOOPER_PRN, 1)], E.ExtraEnergyDamage)
        self.assertEqual(kinds[(TOTODILE_PRN, 1)], E.CoinFlipDamage)
        self.assertEqual((kinds[(GROWLITHE_IP2, 0)], kinds[(GROWLITHE_IP2, 1)]), (E.FailOnTailsDamage, E.DiscardEnergyBeforeDamage))
        # 倍数・位置・名前は登録の値（GD3-011 の対象は「かじる」。PMCG5-056 のマチスのコラッタの「でんこうせっか」の登録ではない）
        self.assertEqual(registry.attack_entry(LT_SURGES_RATTATA_GD3, 0).effect, E.MultiplyNextTurnAttackDamage(1, "かじる", 2))
        self.assertEqual(registry.attack_entry(LT_SURGES_RATTATA, 0).effect.target_attack_name, "でんこうせっか")
        self.assertEqual(registry.attack_entry(SQUIRTLE_ES1, 0).effect, E.MultiplyNextTurnAttackDamage(1, "はたく", 3))
        self.assertFalse(registry.attack_entry(NIDORAN_M_ES1, 0).effect.includes_self_damage)
        self.assertEqual(registry.attack_entry(GROWLITHE_IP2, 1), registry.attack_entry(GROWLITHE_ES3, 1))  # v0.75 のガーディと同じ登録（同じ文面）
        for new_type in (E.ReduceDamageToSelfNextOpponentTurn, E.LockOpponentAttackOnHeads, E.CoinNextTurnMultiplyElseLockAttack, E.AttackLockWhileSourceActiveOnHeads):
            self.assertIn(new_type, ATTACK_TYPES_SINCE_V0_17)
            self.assertIn(new_type, PG.BUILDERS)

    def test_same_data_cards_share_one_registration(self):
        """日本語のゲーム用データが同じ 7 組（15 枚）は、HP・タイプ・弱点・抵抗力・にげる・段階・名前・全ワザが同じで、登録の値を共有する（id は消さない）。"""
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS

        def view(card):
            d = pool.get(card)
            return (d.name_ja, d.hp, d.pokemon_type, d.weakness, d.resistance, d.resistance_value, d.retreat_cost, d.stage, d.evolves_from,
                    [(a.name_ja, a.cost, a.damage, a.damage_modifier, a.text_ja) for a in d.attacks])

        for new, original in E.SAME_DATA_CARDS_V0_76.items():
            with self.subTest(card=new):
                self.assertEqual(view(new), view(original))
                for index in range(2):
                    self.assertIs(registry.attack_entry(new, index), registry.attack_entry(original, index))
        self.assertEqual(dict(E.SAME_DATA_CARDS_V0_76), {
            NIDORAN_M_QSG: NIDORAN_M_ES1, SQUIRTLE_QSG: SQUIRTLE_ES1, SQUIRTLE_IP2: SQUIRTLE_ES1, CHARMANDER_QSG: CHARMANDER_ES1, DODUO_QSG: DODUO_ES1,
            SEEL_QSG: SEEL_ES2, MACHOP_QSG: MACHOP_ES2, TOTODILE_PRN_B: TOTODILE_PRN})
        groups = {original for original in E.SAME_DATA_CARDS_V0_76.values()}
        self.assertEqual(len(groups), 7)
        self.assertEqual(len(V0_76_POKEMON) - len(E.SAME_DATA_CARDS_V0_76), 16)  # 24 枚で、日本語のゲーム用データは 16 通り

    def test_counts_from_the_registry(self):
        """対応するカード 826（ポケモン 585・トレーナー 211・エネルギー 30）、ワザ 995・特殊能力 74（登録から数える）。v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・
        ワザ 77・トレーナー 2）、v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）、v0.79 でポケモン 52 枚（ワザ 94）を加えたので、
        今の数は 943（695・213・35）、ワザ 1,182。"""
        pool = load_card_pool()
        categories = [pool.get(card).category for card in pool.playable_ids]
        self.assertEqual((len(categories), categories.count("pokemon"), categories.count("trainer"), categories.count("energy")), (973, 695, 243, 35))  # v0.80 でトレーナー 30 枚（スタジアム 4 枚）・停止コード 9 件を加えた
        registry = E.DEFAULT_EFFECTS
        self.assertEqual((len(registry.attack_keys()), len(registry.power_keys()), len(registry.trainer_ids())), (1182, 74, 243))  # v0.80 でトレーナー 30 枚（スタジアム 4 枚を含む）を加えた

    def test_non_pack_unsupported_count(self):
        """kyuura data/engine_targets.json（7d3f4ca）の対象のうち、拡張パック以外の商品で対応していないカードは 228 枚（v0.75 は 252 枚）。"""
        raw = subprocess.run(["git", "-C", str(ROOT.parent / "kyuura"), "show", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3:data/engine_targets.json"],
                             capture_output=True, text=True, check=False)
        if raw.returncode != 0:
            self.skipTest("../kyuura がない")
        data = json.loads(raw.stdout)
        targets = data["cards"] if isinstance(data, dict) else data
        pool = load_card_pool()
        self.assertEqual(sum(1 for x in targets if x["product_group"] != "expansion_pack" and x["id"] not in pool.playable_ids), 202)  # v0.80 でトレーナー 30 枚（スタジアム 4 枚）・停止コード 9 件を加えた  # v0.79 で拡張パック以外の 16 枚を加えた  # v0.78 で拡張パック以外の 5 枚（イントロパック・プロモ）を加えた（v0.76・v0.77 は 228）

    def test_text_variants_are_narrow(self):
        """既存の型に加えた書き方は、意味を確かめたものだけで、登録の値（倍数・名前・位置・数）と結びつく。違う値・違う書き方は受け付けない。"""
        pool = load_card_pool()
        rattata = pool.get(LT_SURGES_RATTATA_GD3).attacks
        self.assertEqual(E.MultiplyNextTurnAttackDamage(1, "かじる", 2).check(rattata[0]), [])
        self.assertNotEqual(E.MultiplyNextTurnAttackDamage(1, "かじる", 3).check(rattata[0]), [])
        self.assertNotEqual(E.MultiplyNextTurnAttackDamage(1, "でんこうせっか", 2).check(rattata[0]), [])
        self.assertNotEqual(E.MultiplyNextTurnAttackDamage(1, "かみつく", 2).card_problems(rattata[0], rattata), [])
        squirtle = pool.get(SQUIRTLE_ES1).attacks
        self.assertNotEqual(E.MultiplyNextTurnAttackDamage(1, "はたく", 2).check(squirtle[0]), [])
        self.assertNotEqual(E.MultiplyNextTurnAttackDamage(0, "はたく", 3).card_problems(squirtle[0], squirtle), [])
        # 「その数にする」（SET）とは別の型。マリルの「はずむ」は「数をかける」で登録できない
        marill = pool.get(MARILL_PRN).attacks
        self.assertNotEqual(E.MultiplyNextTurnAttackDamage(1, "とびのる", 3).check(marill[0]), [])
        self.assertEqual(E.SetNextTurnAttackDamage(1, "とびのる", 30, target_text="コインを投げて「おもて」なら、相手を「マヒ」状態にする。").card_problems(marill[0], marill), [])
        # 説明のある対象ワザは、説明を登録で指定したときだけ。位置・名前・説明・数が違えば受け付けない（「説明がある」だけで拒否しない・何でも受け付けない）
        self.assertNotEqual(E.SetNextTurnAttackDamage(1, "とびのる", 30).card_problems(marill[0], marill), [])
        self.assertNotEqual(E.SetNextTurnAttackDamage(1, "とびのる", 30, target_text="相手を「マヒ」状態にする。").card_problems(marill[0], marill), [])
        self.assertNotEqual(E.SetNextTurnAttackDamage(1, "はたく", 30, target_text="コインを投げて「おもて」なら、相手を「マヒ」状態にする。").card_problems(marill[0], marill), [])
        self.assertNotEqual(E.SetNextTurnAttackDamage(0, "とびのる", 30, target_text="コインを投げて「おもて」なら、相手を「マヒ」状態にする。").card_problems(marill[0], marill), [])
        self.assertNotEqual(E.SetNextTurnAttackDamage(1, "とびのる", 40, target_text="コインを投げて「おもて」なら、相手を「マヒ」状態にする。").check(marill[0]), [])
        # なきごえ: 減らす数の違う登録・なきつくの型は受け付けない。なきつくの型もなきごえの文面を受け付けない
        growl = pool.get(CHARMANDER_ES1).attacks[0]
        self.assertNotEqual(E.ReduceDamageToSelfNextOpponentTurn(20).check(growl), [])
        self.assertNotEqual(E.ReduceDamageToSelf(10).check(growl), [])
        self.assertNotEqual(E.ReduceDamageToSelfNextOpponentTurn(20).check(pool.get(CUBONE).attacks[0]), [])
        # ドわすれ・かなしばり
        self.assertEqual(E.LockOpponentAttack().check(pool.get(SLOWPOKE_PR1).attacks[1]), [])
        self.assertNotEqual(E.LockOpponentAttack().check(pool.get(VENONAT_ES3).attacks[0]), [])
        self.assertNotEqual(E.LockOpponentAttackOnHeads().check(pool.get(SLOWPOKE_PR1).attacks[1]), [])
        # きあいいっぱつ: 位置・名前・倍数
        machop = pool.get(MACHOP_ES2).attacks
        self.assertNotEqual(E.CoinNextTurnMultiplyElseLockAttack(1, "どつく", 3).check(machop[0]), [])
        self.assertNotEqual(E.CoinNextTurnMultiplyElseLockAttack(1, "はたく", 2).check(machop[0]), [])
        self.assertNotEqual(E.CoinNextTurnMultiplyElseLockAttack(0, "どつく", 2).card_problems(machop[0], machop), [])
        # にらみつける: 最大HPの条件のある「すごむ」の型とは書き方が違う
        leer = pool.get(CYNDAQUIL_PF1).attacks[0]
        self.assertNotEqual(E.AttackLockWhileSourceActive(50).check(leer), [])
        self.assertNotEqual(E.AttackLockWhileSourceActiveOnHeads().check(pool.get(SLOWPOKE_PR1).attacks[1]), [])

    def test_records(self):
        """採用の記録（24 件。外部照合なし。kyuura の記録の id なし）と、研究の対応表の印刷の文面の一覧（説明文のあるワザ）。"""
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        adopted = set(links["latest_descriptions"]["adopted_printed_text"])
        pool = load_card_pool()
        for card in V0_76_POKEMON:
            with self.subTest(card=card):
                record = sources[card]
                self.assertEqual((record["basis"], record["status"], record["external_checks"], record["kyuura_records"]), ("kyuura_data", "adopted", [], []))
                for index, attack_def in enumerate(pool.get(card).attacks):
                    key = f"attack/{index}"
                    self.assertEqual(key in record["play_text"], attack_def.text_ja is not None)
                    self.assertEqual(f"{card}/{key}" in adopted, attack_def.text_ja is not None)
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (175, 177))  # v0.80 でトレーナー 30 枚（スタジアム 4 枚）・停止コード 9 件を加えた  # v0.79 で PK1 を加えた  # v0.78 で MT1・DE1 を加えた（v0.77 は 163・165）

    def test_state_type_and_expiry_are_explicit(self):
        """なきごえの状態は「なきつく」の部分型で、種類と期限だけが違う（「次の相手の番」= はたらく番の終わり）。なきつくの期限は変えない。"""
        self.assertIn(ReducedDamageToSourceNextTurn, PERSISTENT_EFFECT_TYPES)
        self.assertTrue(issubclass(ReducedDamageToSourceNextTurn, ReducedDamageToSource))
        self.assertEqual((ReducedDamageToSource.kind, ReducedDamageToSourceNextTurn.kind), ("reduced_damage_to_source", "reduced_damage_to_source_next_turn"))
        self.assertTrue(ReducedDamageToSource.expires_at_turn_start)
        self.assertFalse(ReducedDamageToSourceNextTurn.expires_at_turn_start)
        effect = ReducedDamageToSourceNextTurn(source_card=1, source_player=0, created_turn=3, active_turn=4, amount=10)
        self.assertFalse(expires_at_turn_start(effect))


class MultiplyNextTurnTest(unittest.TestCase):
    """2 倍・3 倍（p.321 の 2 段階の「数をかける」）。作った番・あいだの相手の番にははたらかず、次の自分の番の、指定したワザだけにはたらく。"""

    def test_squirtle_three_times_then_pluspower(self):
        """ゼニガメ: ウォーターパワー → 相手の番 → はたく 10 × 3 = 30（2 段階）。そのあとプラスパワー（5 段階 + 10）で 40。"""
        state = attack(game(mon(SQUIRTLE_ES1, (WATER,))), 0)
        effect = effects_of(state, 0, NextTurnAttackDamage)[0]
        self.assertEqual((effect.kind, effect.amount, effect.target_attack_index, effect.active_turn), ("next_turn_attack_damage_multiplier", 3, 1, TURN + 2))
        mine = end(state)
        self.assertEqual(mine.turn_number, TURN + 2)
        hit = attack(mine, 1)
        self.assertEqual((last_damage(hit)["amount"], last_damage(hit)["steps"][:2]), (30, (("1 基本となる計算", 10), ("2 ウォーターパワー", 30))))
        audited(self, hit)
        powered = game(mon(SQUIRTLE_ES1, (WATER,)), hand=[PLUSPOWER])
        powered = end(attack(powered, 0))
        powered = attack(use(powered, PLUSPOWER), 1)
        self.assertEqual(last_damage(powered)["amount"], 40)
        audited(self, powered)

    def test_only_the_named_attack_and_only_next_own_turn(self):
        """マチスのコラッタ（GD3-011）: きあいだめの効果は「かじる」だけ。きあいだめ自身（ダメージなし）・あいだの相手の番には関係しない。次の自分の番の終わりに消える。"""
        state = attack(game(mon(LT_SURGES_RATTATA_GD3, (FIRE, FIRE))), 0)
        between = state  # 相手の番（効果ははたらかない。はたらく番は TURN + 2）
        self.assertEqual(between.turn_number, TURN + 1)
        self.assertEqual(effects_of(between, 0, NextTurnAttackDamage)[0].active_turn, TURN + 2)
        hit = attack(end(between), 1)
        self.assertEqual(last_damage(hit)["amount"], 40)  # かじる 20 × 2（ヒトカゲではないので弱点なし）
        later = attack(end(hit), 1)  # TURN + 4: 効果は TURN + 2 の終わりに消えた
        self.assertEqual(last_damage(later)["amount"], 20)
        removed = [e for e in hit.log if e["kind"] == "persistent_effect_removed" and e["persistent_effect"] == "next_turn_attack_damage_multiplier"]
        self.assertEqual([(e["reason"], e["turn"]) for e in removed], [("expired", TURN + 2)])
        audited(self, later)

    def test_nidoran_horn_attack_coin_and_fail(self):
        """ニドラン♂: 強化した「つのでとっしん」も、コインの「うら」なら失敗（80 は出ない）。「おもて」なら 40 × 2 = 80。"""
        mine = end(attack(game(mon(NIDORAN_M_ES1, (GRASS, GRASS))), 0))
        failed = attack(mine, 1, T)
        self.assertFalse([e for e in failed.log[len(mine.log):] if e["kind"] == "damage"])
        self.assertIn("attack_failed", [e["kind"] for e in failed.log[len(mine.log):]])
        hit = attack(mine, 1, H)
        self.assertEqual(last_damage(hit)["amount"], 80)
        audited(self, hit)

    def test_removed_by_evolution_and_switch(self):
        """進化・ベンチにもどる（突風）で消える（p.322・p.310。v0.27 と同じ消える契機）。"""
        state = end(attack(game(mon(MACHOP_ES2, (FIGHTING, FIGHTING)), hand=[MACHOKE]), 0, H))
        machop = state.players[0].active
        self.assertTrue(effects_of(state, 0, NextTurnAttackDamage))
        evolved = apply_kernel(state, EvolvePokemon(0, card_in_hand(state, MACHOKE), machop.pokemon_id))
        self.assertFalse(effects_of(evolved, 0, NextTurnAttackDamage))
        self.assertEqual([e["reason"] for e in evolved.log if e["kind"] == "persistent_effect_removed"][-1], "evolve")
        audited(self, evolved)
        growled = attack(game(mon(CHARMANDER_ES1, (FIRE,)), mon(HITMONCHAN, (FIGHTING, FIGHTING)), opponent_hand=[GUST]), 0)
        # 受けた相手（プレイヤー 1。かくとうのエビワラー、にげる 2）が、はたらく番に「にげる」でベンチにもどると、なきごえの効果は消える
        target = growled.players[1].active
        retreated = apply_kernel(growled, RetreatCommand(1, tuple(target.energy), growled.players[1].bench[0].card))
        self.assertFalse([e for p in retreated.players[1].in_play() for e in p.persistent_effects])
        self.assertEqual([e["reason"] for e in retreated.log if e["kind"] == "persistent_effect_removed"][-1], "retreat")
        audited(self, retreated)


def card_in_hand(state, card_id):
    return next(uid for uid in state.players[0].hand if state.cards[uid].card_id == card_id)


class SetNextTurnWithEffectTest(unittest.TestCase):
    """マリルの「はずむ」: 次の自分の番の「とびのる」のダメージを 2 段階で「30」にする。とびのるのマヒのコインと効果は消さず、コインを足さない。"""

    def test_bounce_then_hop_paralyzes_on_heads(self):
        mine = end(attack(game(mon(MARILL_PRN, (WATER, WATER, WATER))), 0))
        heads = attack(mine, 1, H)
        self.assertEqual((last_damage(heads)["amount"], last_damage(heads)["steps"][:2]), (30, (("1 基本となる計算", 10), ("2 はずむ", 30))))
        self.assertEqual(coins_of(heads, mine), ["heads"])  # コインは 1 枚だけ
        self.assertTrue([e for e in heads.log[len(mine.log):] if e["kind"] == "special_condition" and e["condition"] == "paralysis"])
        tails = attack(mine, 1, T)
        self.assertEqual((last_damage(tails)["amount"], coins_of(tails, mine)), (30, ["tails"]))
        self.assertFalse([e for e in tails.log[len(mine.log):] if e["kind"] == "special_condition"])
        audited(self, heads)

    def test_set_is_not_multiply(self):
        """「30 にする」は 2 段階で、そのあと弱点（ヒトカゲは弱点 水 × 2）で 60。登録は「その数にする」（SET）で、「数をかける」ではない。"""
        self.assertEqual(load_card_pool().get(CHARMANDER_ES1).weakness, E.EnergyType.WATER)
        mine = end(attack(game(mon(MARILL_PRN, (WATER, WATER, WATER)), mon(CHARMANDER_ES1, (FIRE,))), 0))
        hit = attack(mine, 1, T)
        self.assertEqual(last_damage(hit)["steps"][:3], (("1 基本となる計算", 10), ("2 はずむ", 30), ("3 弱点", 60)))
        self.assertEqual(last_damage(hit)["damage_set"], ((2, mine.players[0].active.card, 30),))
        effect = effects_of(mine, 0, NextTurnAttackDamage)[0]
        self.assertEqual((effect.kind, effect.amount), ("next_turn_attack_damage", 30))


class GrowlTest(unittest.TestCase):
    """なきごえ: 相手に与える持続する効果。受けた相手が、次の相手の番にこのカードへ与えるダメージを 2 段階で 10 減らす。期限は次の相手の番の終わり。"""

    def test_reduces_damage_to_the_source_at_step_two(self):
        """受けた相手（ゼニガメ。水）がヒトカゲ（弱点 水）にはたく 10: 2 段階で 0 → 弱点で 0。（受け手の 8 段階の軽減なら 10 × 2 − 10 = 10）"""
        state = attack(game(mon(CHARMANDER_ES1, (FIRE,)), mon(SQUIRTLE_ES1, (WATER,))), 0)
        effect = effects_of(state, 1, ReducedDamageToSourceNextTurn)[0]
        self.assertEqual((effect.amount, effect.active_turn, effect.source_card), (10, TURN + 1, state.players[0].active.card))
        self.assertIs(reduced_damage_to_source(state, state.players[1].active), effect)
        hit = attack(state, 1)
        self.assertEqual(last_damage(hit)["steps"][:2], (("1 基本となる計算", 10), ("2 ヒトカゲ（reduced_damage_to_source_next_turn）", 0)))
        self.assertEqual(last_damage(hit)["amount"], 0)
        audited(self, hit)

    def test_only_damage_to_the_source(self):
        """効果を与えたポケモン以外へのダメージは減らさない（突風で入れ替えたラッタ）。受けた相手がベンチにもどると消える。"""
        state = attack(game(mon(DODUO_ES1, (FIRE,)), mon(HITMONCHAN, (FIGHTING, FIGHTING)), opponent_hand=[GUST]), 0)
        gusted = use(state, GUST, player=1)
        gusted = answer(gusted, (gusted.decision.options[0],))
        self.assertNotEqual(gusted.players[0].active.card, state.players[0].active.card)
        hit = attack(gusted, 0, player=1)
        self.assertFalse([s for s in last_damage(hit)["steps"] if s[0].startswith("2 ")])
        audited(self, hit)

    def test_expires_at_end_of_opponent_turn_unlike_cry(self):
        """なきごえは相手の番の終わり（turn_end の前の期限の処理）で消え、ポケモンチェックの間・次の番には残らない。なきつく（カラカラ）は次の自分の番の始めまで残る。"""
        growled = end(attack(game(mon(SEEL_ES2, (FIRE,)), mon(HITMONCHAN, (FIGHTING, FIGHTING))), 0))
        self.assertEqual(growled.turn_number, TURN + 2)
        self.assertFalse(effects_of(growled, 1, ReducedDamageToSource))
        kinds = [(e["kind"], e.get("persistent_effect")) for e in growled.log if e["turn"] == TURN + 1]
        self.assertLess(kinds.index(("persistent_effect_removed", "reduced_damage_to_source_next_turn")), kinds.index(("turn_end", None)))
        cried = end(attack(game(mon(CUBONE, (FIGHTING,)), mon(HITMONCHAN, (FIGHTING, FIGHTING))), 0))
        self.assertFalse(effects_of(cried, 1, ReducedDamageToSource))
        removed = [e for e in cried.log if e["kind"] == "persistent_effect_removed"][-1]
        self.assertEqual((removed["turn"], removed["persistent_effect"]), (TURN + 2, "reduced_damage_to_source"))  # 次の番の始め
        audited(self, growled)
        audited(self, cried)

    def test_barrier_and_prevent_damage(self):
        """「ワザをうけない」相手は効果を受けない。「ダメージを受けない」相手（かたまる）は効果を受ける（ダメージ以外の効果）。"""
        barrier = attack(with_barrier(mon(PIKACHU_IP1, (FIRE,))), 0, player=1)
        self.assertFalse(effects_of(barrier, 0, ReducedDamageToSource))
        state = board([], active=mon(CHIKORITA_PF1, (FIRE,)), deck=DECK, opponent_active=mon(HITMONCHAN, (FIGHTING,), prevent_damage=TURN - 1), opponent_deck=DECK)
        prevented = attack(state, 0)
        self.assertTrue(effects_of(prevented, 1, ReducedDamageToSourceNextTurn))
        audited(self, prevented)

    def test_bench_target_keeps_nk5(self):
        """効果を与えたポケモンが控えにいるときの、控えへのダメージ（のびるキック）は NK5 のまま止める（説明の書き方は違うが、記録で決まらない）。理由の文は v0.75 までの
        「なきつく」の文のままで、補足になきごえの効果だと書く。選ぶ答えのどれかが問いに当たれば宣言の前に止める（v0.15c からの先読み。v0.34 のなきつくと同じ）。"""
        state = attack(game(mon(CHARMANDER_ES1, (FIRE,)), mon(HITMONLEE, (FIGHTING, FIGHTING)), bench=(RATTATA, RATTATA), opponent_hand=[GUST]), 0)
        gusted = use(state, GUST, player=1)
        gusted = answer(gusted, (gusted.decision.options[0],))
        self.assertIn(CHARMANDER_ES1, [gusted.cards[p.card].card_id for p in gusted.players[0].bench])
        error = rejects(self, gusted, UseAttack(1, 0), "UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET")
        self.assertIn("「なきごえ」（このカードにダメージを与える時、そのダメージが「-10」）の効果。", str(error))
        self.assertIn("「なきつく」の「このカードにワザを使う時、与えるダメージが20へる」", str(error))

    def test_order_decision_with_multiplier(self):
        """同じ 2 段階の「数をかける」（相手のウォーターパワー × 3）と「−10」（なきごえ）が重なり、順番で結果が変わるとき、ワザを使うプレイヤー（相手）が順番を選ぶ。
        再開でコインを投げ直さない（はたくにコインはない）。"""
        state = end(game(mon(CHARMANDER_ES1, (FIRE,)), mon(SQUIRTLE_ES1, (WATER,))))  # TURN + 1: 相手の番
        state = attack(state, 0, player=1)  # 相手のウォーターパワー
        state = attack(state, 0, player=0)  # TURN + 2: なきごえ
        waiting = attack(state, 1, player=1)  # TURN + 3: はたく
        self.assertEqual((waiting.decision.kind, waiting.decision.player), (DAMAGE_STEP_ORDER, 1))
        results = {}
        for option in waiting.decision.options:
            done = answer(waiting, (option,))
            results[option] = last_damage(done)["amount"]
            self.assertEqual(coins_of(done, waiting), [])
            audited(self, done)
        self.assertEqual(sorted(results.values()), [0, 40])  # (10 − 10) × 3 × 弱点 2 = 0、(10 × 3 − 10) × 2 = 40


class FocusPunchTest(unittest.TestCase):
    """きあいいっぱつ: 1 枚のコインの同じ結果で、「おもて」なら次の自分の番の「どつく」を 2 倍、「うら」なら次の自分の番の「どつく」だけを使えない。"""

    def test_heads_doubles_punch_only(self):
        state = attack(game(mon(MACHOP_ES2, (FIGHTING, FIGHTING))), 0, H)
        self.assertEqual(coins_of(state, game(mon(MACHOP_ES2, (FIGHTING, FIGHTING)))), ["heads"])
        self.assertEqual([type(e) for e in state.players[0].active.persistent_effects], [NextTurnAttackDamage])
        mine = end(state)
        hit = attack(mine, 1)
        self.assertEqual((last_damage(hit)["amount"], last_damage(hit)["steps"][1]), (60, ("2 きあいいっぱつ", 60)))
        audited(self, hit)

    def test_tails_locks_punch_only(self):
        """「うら」: 「どつく」だけ使えない（ATTACK_LOCKED）。「きあいいっぱつ」は使える。ワザの失敗ではない。"""
        state = attack(game(mon(MACHOP_ES2, (FIGHTING, FIGHTING))), 0, T)
        self.assertNotIn("attack_failed", [e["kind"] for e in state.log])
        lock = effects_of(state, 0, CannotUseOwnAttack)[0]
        self.assertEqual((lock.attack_index, lock.target_attack_index, lock.active_turn), (0, 1, TURN + 2))
        self.assertEqual([type(e) for e in state.players[0].active.persistent_effects], [CannotUseOwnAttack])
        mine = end(state)
        rejects(self, mine, UseAttack(0, 1), "ATTACK_LOCKED", IllegalActionError)
        again = attack(mine, 0, H)
        self.assertEqual(len(effects_of(again, 0, NextTurnAttackDamage)), 1)
        audited(self, again)

    def test_reuse_keeps_old_and_new_apart(self):
        """次の自分の番にもう一度使うと、前の効果（その番にはたらく）と新しい効果（次の自分の番にはたらく）は別。前の効果はその番の終わりに消える。"""
        mine = end(attack(game(mon(MACHOP_ES2, (FIGHTING, FIGHTING))), 0, T))
        again = attack(mine, 0, H)  # TURN + 2 で使った。前の「うら」の効果はこの番の終わりに消える
        self.assertFalse(effects_of(again, 0, CannotUseOwnAttack))
        later = end(again)  # TURN + 4
        hit = attack(later, 1)
        self.assertEqual(last_damage(hit)["amount"], 60)
        audited(self, hit)

    def test_bubble_lock_unchanged(self):
        """v0.35 の「あわあわ」は、使ったワザ自身が次の自分の番に使えなくなるまま（登録の位置 None）。"""
        self.assertEqual(E.DamageThenLockSelfOnTails().attack_lock_terms(), (CannotUseOwnAttack, None))
        state = attack(game(mon(MISTYS_POLIWAG, (WATER,))), 0, T)
        lock = effects_of(state, 0, CannotUseOwnAttack)[0]
        self.assertEqual((lock.attack_index, lock.target_attack_index), (0, 0))

    def test_audit_rejects_mismatched_effect(self):
        """監査（coin_gated_effect_problems）は、コインの面と違う効果・2 つの効果を見つける。"""
        state = attack(game(mon(MACHOP_ES2, (FIGHTING, FIGHTING))), 0, H)
        log = [dict(e) for e in state.log]
        coin = next(e for e in log if e["kind"] == "coin_flip")
        coin["result"] = "tails"
        self.assertTrue(coin_gated_effect_problems(state, log))


class OpponentAttackLockTest(unittest.TestCase):
    """ドわすれ（ヤドン）・かなしばり（コンパン）: 選ぶのはワザを使ったプレイヤー。選んだワザだけを次の相手の番に使えなくする。"""

    def test_amnesia(self):
        state = attack(game(mon(SLOWPOKE_PR1, (PSYCHIC, PSYCHIC))), 1)
        self.assertEqual((state.decision.kind, state.decision.player, state.decision.options), (SELECT_OPPONENT_ATTACK, 0, (0, 1)))
        locked = answer(state, (0,))
        effect = effects_of(locked, 1, CannotUseAttack)[0]
        self.assertEqual((effect.target_attack_index, effect.active_turn), (0, TURN + 1))
        rejects(self, locked, UseAttack(1, 0), "ATTACK_LOCKED", IllegalActionError)
        self.assertEqual(apply_kernel(locked, EndTurn(1)).turn_number, TURN + 2)  # にげる・ほかの操作は止めない
        audited(self, locked)

    def test_disable_heads_chooses_tails_does_nothing(self):
        before = game(mon(VENONAT_ES3, (GRASS,)))
        heads = attack(before, 0, H)
        self.assertEqual((heads.decision.kind, heads.decision.player), (SELECT_OPPONENT_ATTACK, 0))
        self.assertEqual(coins_of(heads, before), ["heads"])
        locked = answer(heads, (1,))
        self.assertEqual(coins_of(locked, before), ["heads"])  # 決定のあとで投げ直さない
        self.assertEqual(effects_of(locked, 1, CannotUseAttack)[0].target_attack_index, 1)
        attacked = attack(locked, 0, player=1)  # ほかのワザは使える
        self.assertEqual(attacked.turn_number, TURN + 2)
        tails = attack(before, 0, T)
        self.assertIsNone(tails.decision)
        self.assertFalse(effects_of(tails, 1))
        self.assertNotIn("attack_failed", [e["kind"] for e in tails.log])
        audited(self, locked)
        audited(self, tails)

    def test_one_attack_and_held_attacks(self):
        """相手のワザが 1 つでも決定を出す（v0.35 と同じ実装上の仮定）。選べるものは相手の対戦ポケモンが今持つワザで、［サイコリンク］で持つワザ（出どころの
        カード id と位置）も選べる。選んだワザだけを使えなくする。"""
        single = attack(game(mon(VENONAT_ES3, (GRASS,)), mon(RATTATA, (FIGHTING,))), 0, H)
        self.assertEqual(single.decision.options, (0,))
        linked = board([], active=mon(VENONAT_ES3, (GRASS,)), deck=DECK, opponent_deck=DECK, opponent_bench=(JYNX,),
                       opponent_active=mon(SABRINAS_ALAKAZAM, (PSYCHIC,) * 4, evolved_from=[SABRINAS_ABRA, SABRINAS_KADABRA]))
        waiting = attack(linked, 0, H)
        self.assertEqual(waiting.decision.context_value("lock_attacks"), ((SABRINAS_ALAKAZAM, 0), (JYNX, 0), (JYNX, 1)))
        locked = answer(waiting, (1,))
        effect = effects_of(locked, 1, CannotUseAttack)[0]
        self.assertEqual((effect.target_attack_index, effect.target_attack_card), (0, JYNX))
        self.assertEqual([e["kind"] for e in attack(locked, 0, player=1).log[len(locked.log):]][:1], ["attack"])  # メガバーンは使える
        audited(self, locked)

    def test_invalid_answer_keeps_everything(self):
        heads = attack(game(mon(VENONAT_ES3, (GRASS,))), 0, H)
        before = snapshot(heads)
        with self.assertRaises(IllegalActionError):
            apply_kernel(heads, ResolveDecision(0, heads.decision.id, (5,)))
        with self.assertRaises(IllegalActionError):
            apply_kernel(heads, ResolveDecision(1, heads.decision.id, (0,)))  # 相手は答えない
        self.assertEqual(snapshot(heads), before)

    def test_no_attacks_no_coin(self):
        """ワザを持たない相手の対戦ポケモン（ポケモンとして出したなにかの化石）には、選ぶワザがないのでコインを投げない（p.309）。"""
        state = board([], active=mon(VENONAT_ES3, (GRASS,)), deck=DECK, opponent_active={"card": MYSTERIOUS_FOSSIL}, opponent_deck=DECK)
        done = attack(state, 0, H)
        self.assertEqual(coins_of(done, state), [])
        self.assertIsNone(done.decision)

    def test_barrier_prevent_damage_and_transparency(self):
        """「ワザをうけない」相手には、効果だけを決めるコインなので HC3（宣言の前。状態は変わらない）。「ダメージを受けない」相手には投げて効果を与える。
        「とうめい」の相手は、かなしばりのコイン → 「とうめい」のコインの順で、受けなければ選ばない。"""
        rejects(self, with_barrier(mon(VENONAT_ES3, (GRASS,))), UseAttack(1, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")
        state = board([], active=mon(VENONAT_ES3, (GRASS,)), deck=DECK, opponent_active=mon(HITMONCHAN, (FIGHTING,), prevent_damage=TURN - 1), opponent_deck=DECK)
        self.assertEqual(attack(state, 0, H).decision.kind, SELECT_OPPONENT_ATTACK)
        ghost = board([], active=mon(VENONAT_ES3, (GRASS,)), deck=DECK, opponent_active=mon(HAUNTER, (PSYCHIC,), evolved_from=GASTLY), opponent_deck=DECK)
        evaded = attack(ghost, 0, H, H)
        self.assertEqual(coins_of(evaded, ghost), ["heads", "heads"])
        self.assertIsNone(evaded.decision)
        self.assertIn("attack_evaded", [e["kind"] for e in evaded.log])

    def test_copied_effects_are_rejected_before_state_changes(self):
        """ゆびをふるで「きあいいっぱつ」「かなしばり」「きあいだめ」「はずむ」「ドわすれ」を選ぶと、既存と同じエンジンの未対応（状態を変える前）。「なきごえ」「にらみつける」は選べる。"""
        for opponent, index, allowed in ((mon(MACHOP_ES2, (FIGHTING,)), 0, False), (mon(VENONAT_ES3, (GRASS,)), 0, False),
                                         (mon(NIDORAN_M_ES1, (GRASS,)), 0, False), (mon(MARILL_PRN, (WATER,)), 0, False),
                                         (mon(SLOWPOKE_PR1, (PSYCHIC,)), 1, False), (mon(CHARMANDER_ES1, (FIRE,)), 0, True),
                                         (mon(CYNDAQUIL_PF1, (FIRE,)), 0, True)):
            with self.subTest(card=opponent["card"]):
                state = board([], active=mon(CLEFAIRY, (WATER, WATER, WATER)), deck=DECK, opponent_active=opponent, opponent_deck=DECK)
                waiting = attack(state, 1)
                self.assertEqual(waiting.decision.kind, SELECT_ATTACK)
                unsupported = waiting.decision.context_value("unsupported_choices", ())
                if allowed:
                    self.assertNotIn(index, unsupported)
                    done = answer(waiting, (index,)) if index in waiting.decision.options else None
                    self.assertIsNotNone(done)
                else:
                    self.assertIn(index, unsupported)
                    rejects(self, waiting, ResolveDecision(0, waiting.decision.id, (index,)), "UNSUPPORTED_COPIED_ATTACK")


class LockWhileSourceActiveTest(unittest.TestCase):
    """にらみつける・しっぽをふる: コインの「おもて」で、次の相手の番、このカードがバトル場にいる限り、受けた相手はワザを使えない。最大HPの条件はない。"""

    def test_heads_locks_any_hp_tails_does_not(self):
        before = game(mon(CYNDAQUIL_PF1, (FIRE,)), mon(HITMONCHAN, (FIGHTING, FIGHTING)))  # HP 70（すごむの 50 以下の条件はない）
        heads = attack(before, 0, H)
        self.assertTrue(effects_of(heads, 1, CannotAttackWhileSourceActive))
        rejects(self, heads, UseAttack(1, 0), "ATTACK_PREVENTED", IllegalActionError)
        tails = attack(before, 0, T)
        self.assertFalse(effects_of(tails, 1))
        self.assertEqual(attack(tails, 0, player=1).turn_number, TURN + 2)
        audited(self, heads)

    def test_source_on_bench_and_sg1(self):
        """効果を与えたポケモンがベンチにいれば、受けたポケモンはワザを使える。突風でそのポケモンをバトル場にもどす選択は SG1（既存の境界）。"""
        state = attack(game(mon(WOOPER_PRN, (WATER,)), mon(HITMONCHAN, (FIGHTING, FIGHTING)), bench=(RATTATA, RATTATA), opponent_hand=[GUST, GUST]), 0, H)
        gusted = use(state, GUST, player=1)
        gusted = answer(gusted, (gusted.decision.options[0],))
        self.assertNotEqual(gusted.cards[gusted.players[0].active.card].card_id, WOOPER_PRN)
        source = next(p for p in gusted.players[0].bench if gusted.cards[p.card].card_id == WOOPER_PRN)
        again = use(gusted, GUST, player=1)
        self.assertIn(source.pokemon_id, again.decision.context_value("unresolved_choices", ()))
        rejects(self, again, ResolveDecision(1, again.decision.id, (source.pokemon_id,)), "UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED")
        attacked = attack(gusted, 0, player=1)  # 効果を与えたポケモンがベンチにいる間は、ワザを使える
        self.assertEqual([e["kind"] for e in attacked.log[len(gusted.log):]][:2], ["attack", "damage"])

    def test_barrier_stops_coin(self):
        rejects(self, with_barrier(mon(TOTODILE_PRN, (WATER,))), UseAttack(1, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")


class GrowlitheAndOthersTest(unittest.TestCase):
    def test_ember_discard_timing(self):
        """ガーディ（IP2-026）のひのこ: v0.75 と同じ。こんらんの「うら」ではトラッシュしない。"""
        state = board([], active=mon(GROWLITHE_IP2, (FIRE, FIRE), confusion=True), deck=DECK, opponent_deck=DECK)
        confused = attack(state, 1, T)
        self.assertFalse([e for e in confused.log if e["kind"] == "discard_energy"])
        waiting = attack(state, 1, H)
        self.assertEqual(waiting.decision.kind, "discard_energy")  # 1 枚を選ぶ（v0.7 の K2。1 枚しか選べなくても決定を出す）
        hit = answer(waiting, (waiting.decision.options[0],))
        self.assertEqual(len([e for e in hit.log if e["kind"] == "discard_energy"]), 1)
        audited(self, hit)

    def test_water_gun_and_fury_swipes(self):
        """ウパーのみずでっぽう（必要な水 1 つより多い水 1 つにつき + 10。2 つまで）・ワニノコのみだれひっかき（3 枚の「おもて」× 10）。"""
        wooper = attack(board([], active=mon(WOOPER_PRN, (WATER,) * 4), deck=DECK, opponent_deck=DECK), 1)
        self.assertEqual(last_damage(wooper)["steps"][0], ("1 基本となる計算", 30))
        swipes = attack(board([], active=mon(TOTODILE_PRN_B, (WATER,)), deck=DECK, opponent_deck=DECK), 1, H, T, H)
        self.assertEqual(last_damage(swipes)["steps"][0], ("1 基本となる計算", 20))


class SaveAndPreflightTest(unittest.TestCase):
    def test_copies_continue_the_same(self):
        """途中の決定（かなしばり）・持続する効果のある盤面は、clone・deepcopy・pickle のあとも同じ続き（状態・ログ・乱数）になる。"""
        waiting = attack(game(mon(VENONAT_ES3, (GRASS,))), 0, H)
        expected = snapshot(answer(waiting, (1,)))
        for copied in (waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting))):
            self.assertEqual(snapshot(answer(copied, (1,))), expected)
        growled = attack(game(mon(CHARMANDER_ES1, (FIRE,)), mon(SQUIRTLE_ES1, (WATER,))), 0)
        expected = snapshot(attack(growled, 1))
        for copied in (growled.clone(), copy.deepcopy(growled), pickle.loads(pickle.dumps(growled))):
            self.assertEqual(snapshot(attack(copied, 1)), expected)

    def test_preflight_modes_agree(self):
        """3 つの先読みの方法で、代表の分岐の結果が同じ。"""
        cases = ((game(mon(MACHOP_ES2, (FIGHTING, FIGHTING))), 0, (H,)), (game(mon(MACHOP_ES2, (FIGHTING, FIGHTING))), 0, (T,)),
                 (game(mon(VENONAT_ES3, (GRASS,))), 0, (H,)), (game(mon(CYNDAQUIL_PF1, (FIRE,))), 0, (H,)),
                 (game(mon(CHARMANDER_ES1, (FIRE,))), 0, ()), (game(mon(MARILL_PRN, (WATER, WATER))), 1, (H,)))
        for state, index, coins in cases:
            with self.subTest(card=state.cards[state.players[0].active.card].card_id, coins=coins):
                results = {mode: snapshot(attack(state, index, *coins, preflight=mode)) for mode in PREFLIGHT_MODES}
                self.assertEqual(len({repr(r) for r in results.values()}), 1)


class DocumentTest(unittest.TestCase):
    def test_document_exists_and_names_the_cards(self):
        text = DOC.read_text(encoding="utf-8")
        for card in V0_76_POKEMON:
            self.assertIn(card, text)
        for word in ("ReducedDamageToSourceNextTurn", "CoinNextTurnMultiplyElseLockAttack", "LockOpponentAttackOnHeads", "AttackLockWhileSourceActiveOnHeads",
                     "SG1", "NK5", "HC3", "書き出しの形式は 22"):
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()

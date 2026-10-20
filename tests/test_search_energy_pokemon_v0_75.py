"""v0.75: 拡張パック以外の商品のポケモン 15 枚（ワザ 30）と、ポケモンタワーでの P19 の過剰な停止の修正（docs/search-energy-pokemon-v0.75.md）。

15 枚: タケシのズバット（GD1-001）・カスミのコダック（GD2-001）・カスミのメノクラゲ（GD2-003）・カツラのロコン（GD5-003）・カツラのガーディ（GD5-006）・ナツメのスリープ
（GD6-009）・パラス（ES1-010）・ガーディ（ES3-010・QSG-009）・キングラー（ES3-014）・ピカチュウ（QSG-021・PR1-020）・ミュウツー（PR1-007・PR1-008）・ヒマナッツ（PRN-032）。
どれも kyuura データの採用（採用したデータのコミット 7d3f4ca。処理に使う文面は kyuura の印刷の文面）。ガイドブックは読んでいない。kyuura の日本語の文面は pcg-search.com の転記
なので外部照合はしていない。英語の欄と日本語の文面が違うとき（エナジーサポート）は日本語にしたがう。

新しい停止コードは 2: RB5（トラッシュのレインボーエネルギーを「「炎」エネルギーカード」として手札に加えるか）・DB1（「もろばバサミ」の 2 倍を特殊能力のダメージに当てはめるか）。
"""

from __future__ import annotations

import collections
import json
import pathlib
import subprocess
import unittest

from kyuura_engine import (
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    check_invariants,
    observe,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    ATTACH_FROM_DECK,
    ATTACH_FROM_DISCARD,
    ATTACH_TO_BENCH,
    RECOVER_ENERGY,
    SEARCH_DECK,
    SELECT_ATTACK,
)
from kyuura_engine.observation import HIDDEN_COUNT_KINDS, PUBLIC_EVENTS
from kyuura_engine.resolution import programs as PG
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import DoubledDamage
from tests.helpers import (
    ATTACK_TYPES_SINCE_V0_17,
    BLAINES_GROWLITHE_GD5,
    BLAINES_VULPIX_GD5,
    BROCKS_ZUBAT_GD1,
    CHANSEY,
    CLEFAIRY,
    DIGGER,
    DOUBLE_COLORLESS_ENERGY,
    FIGHTING,
    FIRE,
    FOSSIL_GEODUDE,
    FOSSIL_GOLEM,
    FOSSIL_GRAVELER,
    GRASS,
    GRIMER,
    GROWLITHE_ES3,
    GROWLITHE_QSG,
    HAUNTER,
    HITMONCHAN,
    KINGLER_ES3,
    KRABBY,
    LIGHTNING,
    MEWTWO_PR1,
    MEWTWO_PR1_B,
    MISTYS_PSYDUCK,
    MISTYS_PSYDUCK_GD2,
    MISTYS_TENTACOOL_GD2,
    MUK,
    PARAS_ES1,
    PIKACHU_PR1,
    PIKACHU_QSG,
    POKEMON_TOWER,
    POTION,
    PSYCHIC,
    RAINBOW_ENERGY,
    RATTATA,
    ROCKETS_MOLTRES,
    SABRINAS_DROWZEE_GD6,
    SUNKERN_PRN,
    V0_75_POKEMON,
    WATER,
    apply_kernel,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems
from tests.test_instant_trainers_v0_55 import board, mon, use

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "search-energy-pokemon-v0.75.md"
H, T = CoinSide.HEADS, CoinSide.TAILS
TENTACOOL, TENTACRUEL = "PMCG3-011", "PMCG3-017"  # 化石の秘密のメノクラゲ・ドククラゲ
MISTYS_TENTACOOL, MISTYS_TENTACRUEL = "PMCG5-030", "PMCG5-033"
ERIKAS_PARAS = "PMCG5-004"  # エリカのパラス（名前が「パラス」と違う）
BELOW = {KINGLER_ES3: KRABBY, MUK: GRIMER}


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def snapshot(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


def attack(state, index=0, *coins, player=0):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, UseAttack(player, index))


def answer(state, choices):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)))


def rejects(test, state, command, code, error=UnsupportedError):
    before = snapshot(state)
    with test.assertRaises(error) as caught:
        apply_kernel(state, command)
    test.assertEqual(caught.exception.code, code)
    test.assertEqual(snapshot(state), before)  # 状態・ログ・乱数・決定は変わらない
    return caught.exception


def since(state, kind):
    start = max(i for i, e in enumerate(state.log) if e["kind"] == kind)
    return [e["kind"] for e in state.log[start:]]


def kinds_after(state, before):
    return [e["kind"] for e in state.log[len(before.log):]]


def ids(state, uids):
    return [state.cards[u].card_id for u in uids]


def m(card, energy=(), **extra):
    if card in BELOW and "evolved_from" not in extra:
        extra["evolved_from"] = BELOW[card]
    return mon(card, energy, **extra)


class RegistrationTest(unittest.TestCase):
    def test_registered_and_classified(self):
        """15 枚とも写しの組 pool_v0_75 にあり、どのワザも登録した（登録の照合と型）。"""
        extract = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text(encoding="utf-8"))
        self.assertEqual(tuple(extract["pool_v0_75"]), V0_75_POKEMON)
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS
        for card_id in V0_75_POKEMON:
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertIn(card_id, pool.playable_ids)
                for index, attack_def in enumerate(definition.attacks):
                    entry = registry.attack_entry(card_id, index)
                    self.assertIsNotNone(entry)
                    self.assertEqual(entry.effect.check(attack_def), [])
                    if attack_def.text_ja is not None:
                        self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (attack_def.text_ja, attack_def.text_ja, "kyuura data/cards.json"))
        types = {(c, i): type(registry.attack_entry(c, i).effect) for c in V0_75_POKEMON for i in range(2)}
        self.assertEqual(types[(BROCKS_ZUBAT_GD1, 0)], E.DrawThenSwitchSelf)
        self.assertEqual(types[(MISTYS_PSYDUCK_GD2, 1)], E.PutOwnerBasicFromDeckOntoBenchOnHeads)
        self.assertEqual(types[(MISTYS_TENTACOOL_GD2, 1)], E.RevealNamedPokemonFromDeckAny)
        self.assertEqual(types[(BLAINES_VULPIX_GD5, 1)], E.CoinsRecoverEnergyByHeads)
        self.assertEqual(types[(BLAINES_GROWLITHE_GD5, 0)], E.AttachEnergyFromDeckToSelfExactly)
        self.assertEqual(types[(SABRINAS_DROWZEE_GD6, 0)], E.AttachEnergyFromDeckToBench)
        self.assertEqual(types[(PARAS_ES1, 1)], E.PutBasicFromDeckOntoBench)
        self.assertEqual(types[(GROWLITHE_ES3, 0)], E.SearchTrainerOnHeads)
        self.assertEqual(types[(GROWLITHE_ES3, 1)], E.DiscardEnergyBeforeDamage)
        self.assertEqual(types[(KINGLER_ES3, 0)], E.CoinAttachEnergyFromDeckToSelf)
        self.assertEqual(types[(KINGLER_ES3, 1)], E.DamageThenDoubleDamageNextTurn)
        self.assertEqual(types[(PIKACHU_QSG, 0)], E.AttachEnergyFromDeckToSelf)
        self.assertEqual(types[(MEWTWO_PR1, 0)], E.AttachDiscardEnergyCardsToSelf)
        self.assertEqual(types[(SUNKERN_PRN, 0)], E.AttachEnergyFromHandOnHeads)
        self.assertEqual(types[(SUNKERN_PRN, 1)], E.DamageAndDrain)
        ember = registry.attack_entry(GROWLITHE_ES3, 1).effect
        self.assertEqual((ember.energy_type, ember.count, ember.timing, ember.when_lacking), (E.EnergyType.FIRE, 1, "effect", "cannot_use"))
        bolt = registry.attack_entry(PIKACHU_QSG, 1).effect
        self.assertEqual((bolt.energy_type, bolt.count, bolt.timing, bolt.when_lacking), (None, None, "unresolved", "condition"))
        for new_type in (E.DrawThenSwitchSelf, E.RevealNamedPokemonFromDeckAny, E.CoinsRecoverEnergyByHeads, E.AttachEnergyFromDeckToSelfExactly,
                         E.AttachEnergyFromDeckToBench, E.CoinAttachEnergyFromDeckToSelf, E.DamageThenDoubleDamageNextTurn, E.AttachDiscardEnergyCardsToSelf):
            self.assertIn(new_type, ATTACK_TYPES_SINCE_V0_17)
            self.assertIn(new_type, PG.BUILDERS)

    def test_same_data_cards_share_one_registration(self):
        """同じデータの 3 組（ガーディ・ピカチュウ・ミュウツー）は写しのワザが同じで、登録の値を共有する（id は消さない）。"""
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS
        for new, original in E.SAME_DATA_CARDS_V0_75.items():
            with self.subTest(card=new):
                fields = [[(a.name_ja, a.cost, a.damage, a.damage_modifier, a.text_ja) for a in pool.get(c).attacks] for c in (new, original)]
                self.assertEqual(fields[0], fields[1])  # 処理に使う欄（日本語）。英語の欄は版で違う
                self.assertEqual((pool.get(new).hp, pool.get(new).name_ja), (pool.get(original).hp, pool.get(original).name_ja))
                for index in range(2):
                    self.assertIs(registry.attack_entry(new, index), registry.attack_entry(original, index))
        self.assertEqual(dict(E.SAME_DATA_CARDS_V0_75), {GROWLITHE_QSG: GROWLITHE_ES3, PIKACHU_PR1: PIKACHU_QSG, MEWTWO_PR1_B: MEWTWO_PR1})

    def test_counts_from_the_registry(self):
        """対応するカード 826（ポケモン 585・トレーナー 211・エネルギー 30）、ワザ 995・特殊能力 74（登録から数える。v0.75 は 802・561・947。v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた）。"""
        pool = load_card_pool()
        categories = [pool.get(card).category for card in pool.playable_ids]
        self.assertEqual((len(categories), categories.count("pokemon"), categories.count("trainer"), categories.count("energy")), (826, 585, 211, 30))  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた
        registry = E.DEFAULT_EFFECTS
        self.assertEqual((len(registry.attack_keys()), len(registry.power_keys()), len(registry.trainer_ids())), (995, 74, 211))  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた

    def test_non_pack_unsupported_count(self):
        """kyuura data/engine_targets.json（7d3f4ca）の対象のうち、拡張パック以外の商品で対応していないカードは 228 枚（v0.75 は 252 枚・v0.74 は 267 枚。v0.76 で 24 枚を加えた）。"""
        raw = subprocess.run(["git", "-C", str(ROOT.parent / "kyuura"), "show", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3:data/engine_targets.json"],
                             capture_output=True, text=True, check=False)
        if raw.returncode != 0:
            self.skipTest("../kyuura がない")
        data = json.loads(raw.stdout)
        targets = data["cards"] if isinstance(data, dict) else data
        pool = load_card_pool()
        self.assertEqual(sum(1 for x in targets if x["product_group"] != "expansion_pack" and x["id"] not in pool.playable_ids), 228)

    def test_text_variants_are_narrow(self):
        """既存の型に加えた書き方（ほうしをとばす・おつかい・せいちょう）は、意味を確かめた 1 通りだけ。値の違う登録・書き方の違う文面は受け付けない。"""
        pool = load_card_pool()
        paras = pool.get(PARAS_ES1).attacks[1]
        self.assertEqual(E.PutBasicFromDeckOntoBench(("パラス",)).check(paras), [])
        self.assertNotEqual(E.PutBasicFromDeckOntoBench(("エリカのパラス",)).check(paras), [])
        self.assertNotEqual(E.PutBasicFromDeckOntoBench(("パラス", "パラセクト")).check(paras), [])
        sunkern = pool.get(SUNKERN_PRN).attacks[0]
        self.assertEqual(E.AttachEnergyFromHandOnHeads(E.EnergyType.GRASS, 2).check(sunkern), [])
        self.assertNotEqual(E.AttachEnergyFromHandOnHeads(E.EnergyType.GRASS, 3).check(sunkern), [])
        self.assertNotEqual(E.AttachEnergyFromHandOnHeads(E.EnergyType.WATER, 2).check(sunkern), [])
        jelly = pool.get(MISTYS_TENTACOOL_GD2).attacks[1]
        self.assertNotEqual(E.RevealNamedPokemonFromDeckAny(("メノクラゲ", "ドククラゲ")).check(jelly), [])
        wisp = pool.get(BLAINES_VULPIX_GD5).attacks[1]
        self.assertNotEqual(E.CoinsRecoverEnergyByHeads(E.EnergyType.FIRE, 2).check(wisp), [])
        self.assertNotEqual(E.CoinsRecoverEnergyByHeads(E.EnergyType.WATER, 3).check(wisp), [])
        call = pool.get(KINGLER_ES3).attacks[0]
        self.assertNotEqual(E.CoinAttachEnergyFromDeckToSelf(E.EnergyType.WATER, 2).check(call), [])
        # しらせる・もえあがる・エナジーサポートの型は、ほかのワザの文面を受け付けない
        self.assertNotEqual(E.DrawThenSwitchSelf(1).check(paras), [])
        self.assertNotEqual(E.AttachEnergyFromDeckToSelfExactly(E.EnergyType.FIRE).check(pool.get(PIKACHU_QSG).attacks[0]), [])
        self.assertNotEqual(E.AttachEnergyFromDeckToBench(E.EnergyType.PSYCHIC).check(pool.get(PIKACHU_QSG).attacks[0]), [])
        # エナジーサポートの英語の欄は日本語と処理が違う（手札に加える）。登録は日本語の文面で照らす
        drowzee = pool.get(SABRINAS_DROWZEE_GD6).attacks[0]
        self.assertIn("控えポケモンにつける", drowzee.text_ja)

    def test_records(self):
        """採用の記録（15 件。外部照合なし）と、研究の対応表の印刷の文面の一覧・停止コード（RB5・DB1）。"""
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        adopted = set(links["latest_descriptions"]["adopted_printed_text"])
        pool = load_card_pool()
        for card in V0_75_POKEMON:
            with self.subTest(card=card):
                record = sources[card]
                self.assertEqual((record["basis"], record["status"], record["external_checks"]), ("kyuura_data", "adopted", []))
                for index, attack_def in enumerate(pool.get(card).attacks):
                    key = f"attack/{index}"
                    self.assertEqual(key in record["play_text"], attack_def.text_ja is not None)
                    self.assertEqual(f"{card}/{key}" in adopted, attack_def.text_ja is not None)
        for code, ruling in (("UNRESOLVED_RAINBOW_RECOVER_AS_TYPE", "RB5"), ("UNRESOLVED_DOUBLED_DAMAGE_POWER_DAMAGE", "DB1")):
            entry = links["stop_codes"][code]
            self.assertEqual(entry["engine_rulings"], [{"version": "v0.75", "document": "docs/search-energy-pokemon-v0.75.md", "ruling_id": ruling}])
            self.assertEqual(entry["kyuura_disposition"], "not_in_kyuura")

    def test_observation_tables(self):
        """山札のカードを選ぶ決定（search_deck・attach_from_deck）は、選べるものの数を決めるプレイヤーでない人に見せない。新しいログのイベントは公開。"""
        self.assertIn(SEARCH_DECK, HIDDEN_COUNT_KINDS)
        self.assertIn(ATTACH_FROM_DECK, HIDDEN_COUNT_KINDS)
        self.assertIn("deck_energy_evaded", PUBLIC_EVENTS)


class PhoenixGasTowerTest(unittest.TestCase):
    """v0.74 の過剰な停止の修正: ポケモンタワーの場では、ふしちょう（トラッシュから手札に加える効果。CR-PHOENIX-RETURN）は使っても状態が同じなので、ガスの発生源（ベトベトン）が
    いっしょにきぜつしても P19 に当たらない。P19 の問い・分類・コードは変えない（タワーがない場・タワーがはなれた場は今までどおり止める）。"""

    def board(self, stadium):
        state = board([POKEMON_TOWER] if stadium else [], active=m(FOSSIL_GOLEM, (FIGHTING,) * 4, evolved_from=[FOSSIL_GEODUDE, FOSSIL_GRAVELER]),
                      bench=(RATTATA,), opponent_active=m(ROCKETS_MOLTRES, damage=50),
                      opponent_bench=({"card": MUK, "damage": 60, "evolved_from": GRIMER}, RATTATA))
        return use(state, POKEMON_TOWER) if stadium else state

    def test_tower_selfdestruct_knocks_out_three(self):
        """じばく（相手に 100・自分に 100・控えにそれぞれ 20）で、ゴローニャ・R団のファイヤー・ベトベトンの 3 匹がきぜつ。サイドは 3 枚（相手 2・自分 1）、どちらも
        バトル場に出して MAIN にもどる。ふしちょうの機会はなく、R団のファイヤーはトラッシュに残る（手札にもどらない）。"""
        state = attack(self.board(True), 1)
        while state.decision is not None:
            self.assertIn(state.decision.kind, ("take_prize", "promote_active"))
            state = answer(state, (state.decision.options[0],))
        self.assertEqual(state.phase.name, "MAIN")
        self.assertEqual(len([e for e in state.log if e["kind"] == "knock_out"]), 3)
        self.assertEqual(collections.Counter(e["player"] for e in state.log if e["kind"] == "take_prize"), {0: 2, 1: 1})
        self.assertFalse([e for e in state.log if e["kind"] in ("return_to_hand", "post_knockout_power_declared")])
        self.assertIn(ROCKETS_MOLTRES, ids(state, state.players[1].discard))
        self.assertNotIn(ROCKETS_MOLTRES, ids(state, state.players[1].hand))
        audited(self, state)

    def test_without_tower_p19_stays(self):
        """同じ盤面でタワーがなければ、今までどおり P19（UNRESOLVED_PHOENIX_GAS_SOURCE_KNOCKOUT）で止める（宣言の前。状態は変わらない）。"""
        rejects(self, self.board(False), UseAttack(0, 1), "UNRESOLVED_PHOENIX_GAS_SOURCE_KNOCKOUT")


class AlertTest(unittest.TestCase):
    """しらせる: 1 枚引く → 自分の控えと入れ替える。控えがいなければワザを使えない（NO_BENCH。引く前）。"""

    def test_draw_then_switch(self):
        state = board([], active=m(BROCKS_ZUBAT_GD1, (GRASS,)), bench=(RATTATA, HITMONCHAN), deck=[FIRE, WATER])
        waiting = attack(state, 0)
        self.assertEqual(kinds_after(waiting, state), ["attack", "draw"])
        self.assertEqual((waiting.decision.kind, waiting.decision.min_choices), ("select_pokemon", 1))
        after = answer(waiting, (waiting.decision.options[1],))
        self.assertEqual(ids(after, [after.players[0].active.card]), [HITMONCHAN])
        self.assertIn(BROCKS_ZUBAT_GD1, ids(after, [p.card for p in after.players[0].bench]))
        audited(self, after)

    def test_without_bench_is_rejected_before_draw(self):
        rejects(self, board([], active=m(BROCKS_ZUBAT_GD1, (GRASS,)), bench=()), UseAttack(0, 0), "NO_BENCH", IllegalActionError)

    def test_empty_deck_is_not_a_loss(self):
        state = board([], active=m(BROCKS_ZUBAT_GD1, (GRASS,)), bench=(RATTATA,), deck=[])
        after = answer(attack(state, 0), (state.players[0].bench[0].pokemon_id,))
        self.assertEqual(after.phase.name, "MAIN")  # 相手の番（相手は引ける）
        self.assertFalse([e for e in after.log if e["kind"] == "game_end"])

    def test_copied_without_bench(self):
        """相手のワザとして使う（ゆびをふる）とき、控えがいなければピッピでは選べない（説明にしたがう）。カスミのコダックの「ちょうのうりょく」は HC9。"""
        state = board([], active=m(CLEFAIRY, (WATER, WATER, WATER)), bench=(), opponent_active=m(BROCKS_ZUBAT_GD1, (GRASS,)))
        waiting = attack(state, 1)
        self.assertEqual(waiting.decision.kind, SELECT_ATTACK)
        self.assertNotIn(0, waiting.decision.options)
        with_bench = board([], active=m(CLEFAIRY, (WATER, WATER, WATER)), bench=(RATTATA,), opponent_active=m(BROCKS_ZUBAT_GD1, (GRASS,)), deck=[FIRE])
        chosen = answer(attack(with_bench, 1), (0,))
        self.assertEqual(chosen.decision.kind, "select_pokemon")
        psyduck = board([], active=m(MISTYS_PSYDUCK, (PSYCHIC,)), bench=(), opponent_active=m(BROCKS_ZUBAT_GD1, (GRASS,)))
        waiting = attack(psyduck, 0, H, H, H)
        self.assertEqual(waiting.decision.context_value("unresolved_choices"), (0,))
        rejects(self, waiting, ResolveDecision(0, waiting.decision.id, (0,)), "UNRESOLVED_COPIED_ATTACK")


class BenchFromDeckTest(unittest.TestCase):
    def test_call_for_friend_heads_may_choose_none(self):
        """たすけをよぶ: 「おもて」なら「カスミのポケモン」（たねポケモン）を 0〜1 枚。0 枚でも山札を切る。「うら」なら何もしない。ベンチに空きがなければ BENCH_FULL。"""
        state = board([], active=m(MISTYS_PSYDUCK_GD2, (WATER,)), deck=[MISTYS_TENTACOOL, MISTYS_TENTACRUEL, RATTATA])
        waiting = attack(state, 1, H)
        self.assertEqual((waiting.decision.min_choices, waiting.decision.max_choices), (0, 1))
        self.assertEqual(ids(waiting, waiting.decision.options), [MISTYS_TENTACOOL])
        declined = answer(waiting, ())
        self.assertEqual(since(declined, "bench_from_deck_declined")[:2], ["bench_from_deck_declined", "shuffle"])
        tails = attack(state, 1, T)
        self.assertEqual(kinds_after(tails, state)[:2], ["attack", "coin_flip"])
        self.assertNotIn("shuffle", kinds_after(tails, state))
        full = board([], active=m(MISTYS_PSYDUCK_GD2, (WATER,)), bench=(RATTATA,) * 5)
        rejects(self, full, UseAttack(0, 1), "BENCH_FULL", IllegalActionError)

    def test_spore_spread_exact_name(self):
        """ほうしをとばす: 名前が「パラス」と完全に同じたねポケモンだけ（エリカのパラスは選べない）。ちょうど 1 枚。ベンチに空きがなければ BENCH_FULL。"""
        state = board([], active=m(PARAS_ES1, (GRASS,)), deck=[ERIKAS_PARAS, PARAS_ES1, RATTATA])
        waiting = attack(state, 1)
        self.assertEqual(ids(waiting, waiting.decision.options), [PARAS_ES1])
        self.assertEqual(waiting.decision.min_choices, 1)
        after = answer(waiting, waiting.decision.options)
        self.assertEqual(ids(after, [after.players[0].bench[-1].card]), [PARAS_ES1])
        rejects(self, board([], active=m(PARAS_ES1, (GRASS,)), bench=(RATTATA,) * 5), UseAttack(0, 1), "BENCH_FULL", IllegalActionError)


class JellyfishPodTest(unittest.TestCase):
    """くらげのむれ: 名前が 4 つのどれかと同じポケモンのカードを好きなだけ（0・一部・すべて）。選んだカードだけを見せる。山札は 1 回切る。"""

    DECK = (TENTACOOL, MISTYS_TENTACOOL, TENTACRUEL, MISTYS_TENTACRUEL, MISTYS_TENTACOOL_GD2, ERIKAS_PARAS, RATTATA, FIRE)

    def board(self, deck=None):
        return board([], active=m(MISTYS_TENTACOOL_GD2, (WATER, GRASS)), deck=list(self.DECK if deck is None else deck))

    def test_candidates_and_any_number(self):
        state = self.board()
        waiting = attack(state, 1)
        self.assertEqual(sorted(ids(waiting, waiting.decision.options)), sorted([TENTACOOL, MISTYS_TENTACOOL, TENTACRUEL, MISTYS_TENTACRUEL, MISTYS_TENTACOOL_GD2]))
        self.assertEqual((waiting.decision.kind, waiting.decision.min_choices, waiting.decision.max_choices), (SEARCH_DECK, 0, 5))
        for chosen in ((), waiting.decision.options[:2], waiting.decision.options):
            with self.subTest(count=len(chosen)):
                after = answer(waiting, chosen)
                revealed = [e["card"] for e in after.log[len(waiting.log):] if e["kind"] == "reveal_from_deck"]
                self.assertEqual(sorted(revealed), sorted(chosen))
                self.assertEqual(sorted(after.players[0].hand[-len(chosen):] if chosen else []), sorted(chosen))
                self.assertEqual([e["kind"] for e in after.log[len(waiting.log):]].count("shuffle"), 1)
                audited(self, after)
        other = observe(waiting, 1)["decision"]
        self.assertEqual(other, {"kind": SEARCH_DECK, "player": 0})  # 選べるものの数（山札の中身）を見せない

    def test_rejects_duplicates_and_other_cards(self):
        waiting = attack(self.board(), 1)
        option = waiting.decision.options[0]
        rejects(self, waiting, ResolveDecision(0, waiting.decision.id, (option, option)), "DUPLICATE_CHOICE", IllegalActionError)
        not_option = next(u for u in waiting.players[0].deck if u not in waiting.decision.options)
        with self.assertRaises(IllegalActionError):
            apply_kernel(waiting, ResolveDecision(0, waiting.decision.id, (not_option,)))

    def test_no_candidates(self):
        state = self.board([RATTATA, FIRE])
        after = attack(state, 1)
        self.assertIsNone(after.decision)
        self.assertEqual(kinds_after(after, state)[:3], ["attack", "reveal_from_deck_none", "shuffle"])

    def test_preflight_grouping_matches_full_enumeration(self):
        """先読みの答え（card_id_answers）は、すべての答え（all_answers）と同じ結果の集まりを作る（同じカード id のカードの uid を入れかえた形・選んだ順によらない）。"""
        waiting = attack(self.board([TENTACOOL, TENTACOOL, MISTYS_TENTACOOL, RATTATA]), 1)
        decision = waiting.decision

        def outcome(choice):
            after = answer(waiting, choice)
            return tuple(sorted(ids(after, after.players[0].hand))), tuple(sorted(ids(after, after.players[0].deck)))

        full = {outcome(c) for c in PG.all_answers(decision)}
        grouped = [outcome(c) for c in PG.card_id_answers(waiting, decision, range(decision.max_choices + 1))]
        self.assertEqual(set(grouped), full)
        self.assertEqual(len(grouped), len(set(grouped)))  # まとめた答えどうしは別の結果

    def test_many_candidates_are_legal(self):
        """選べるものが多い（4 つの名前 × 4 枚 = 16 枚）ときも宣言でき（先読みの上限を上げない・選ぶ数を制限しない）、すべてを選べる。"""
        deck = [TENTACOOL] * 4 + [MISTYS_TENTACOOL] * 2 + [MISTYS_TENTACOOL_GD2] * 2 + [TENTACRUEL] * 4 + [MISTYS_TENTACRUEL] * 4 + [RATTATA]
        waiting = attack(self.board(deck), 1)
        self.assertEqual(waiting.decision.max_choices, 16)
        after = answer(waiting, waiting.decision.options)
        self.assertEqual(len([e for e in after.log if e["kind"] == "reveal_from_deck"]), 16)
        audited(self, after)


class CallWillOTheWispTest(unittest.TestCase):
    """おにびあつめ: コイン 3 枚の「おもて」の数ぶんの「炎」エネルギーカードをトラッシュから手札へ（「最大」ではない）。"""

    def board(self, discard, hand=()):
        return board(list(hand), active=m(BLAINES_VULPIX_GD5, (FIRE,)), discard=discard)

    def test_exact_heads(self):
        waiting = attack(self.board([FIRE, FIRE, FIRE, WATER]), 1, H, T, H)
        self.assertEqual((waiting.decision.kind, waiting.decision.min_choices, waiting.decision.max_choices), (RECOVER_ENERGY, 2, 2))
        rejects(self, waiting, ResolveDecision(0, waiting.decision.id, waiting.decision.options[:1]), "INVALID_CHOICE_COUNT", IllegalActionError)
        after = answer(waiting, waiting.decision.options[:2])
        self.assertEqual(ids(after, after.players[0].hand)[-2:], [FIRE, FIRE])
        audited(self, after)

    def test_zero_heads_is_not_a_failure(self):
        state = self.board([FIRE, FIRE, FIRE])
        after = attack(state, 1, T, T, T)
        self.assertEqual(kinds_after(after, state)[:4], ["attack", "coin_flip", "coin_flip", "coin_flip"])
        self.assertFalse([e for e in after.log if e["kind"] in ("attack_failed", "recover_energy")])

    def test_shortfall_stops_before_declaration(self):
        """「炎」エネルギーカードが 1 枚以上で「おもて」の数より少なくなりうるなら FC1（宣言の前。コインを投げない）。"""
        rejects(self, self.board([FIRE, WATER]), UseAttack(0, 1), "UNRESOLVED_STATED_CARDS_SHORT")

    def test_no_target_no_coins(self):
        state = self.board([WATER])
        after = attack(state, 1)
        self.assertEqual(kinds_after(after, state)[:2], ["attack", "turn_end"])

    def test_rainbow_stops(self):
        rejects(self, self.board([FIRE, FIRE, FIRE, RAINBOW_ENERGY]), UseAttack(0, 1), "UNRESOLVED_RAINBOW_RECOVER_AS_TYPE")

    def test_tower_suppresses_without_coins(self):
        """ポケモンタワーの場では効果が消える（処理の対象がないのでコインを投げない。ログ discard_to_hand_suppressed）。レインボーエネルギーがあっても止めない。"""
        state = use(self.board([FIRE, FIRE, FIRE, RAINBOW_ENERGY], hand=[POKEMON_TOWER]), POKEMON_TOWER)
        after = attack(state, 1)
        self.assertEqual(kinds_after(after, state)[:3], ["attack", "discard_to_hand_suppressed", "turn_end"])
        audited(self, after)


class AttachFromDeckTest(unittest.TestCase):
    def test_stoke_exactly_one(self):
        """もえあがる: 選べるものがあればちょうど 1 枚（0 枚は選べない）。なければつけずに山札を切る。手札からつける回数に数えない。"""
        state = board([], active=m(BLAINES_GROWLITHE_GD5, (FIRE,)), deck=[FIRE, FIRE, WATER])
        waiting = attack(state, 0)
        self.assertEqual((waiting.decision.kind, waiting.decision.min_choices, waiting.decision.max_choices), (ATTACH_FROM_DECK, 1, 1))
        rejects(self, waiting, ResolveDecision(0, waiting.decision.id, ()), "INVALID_CHOICE_COUNT", IllegalActionError)
        after = answer(waiting, waiting.decision.options[:1])
        self.assertEqual(ids(after, after.players[0].active.energy), [FIRE, FIRE])
        self.assertEqual(after.players[0].energy_attachments_this_turn if hasattr(after.players[0], "energy_attachments_this_turn") else 0, 0)
        none = attack(board([], active=m(BLAINES_GROWLITHE_GD5, (FIRE,)), deck=[WATER]), 0)
        self.assertEqual(since(none, "attach_energy_from_deck_none")[:2], ["attach_energy_from_deck_none", "shuffle"])

    def test_recharge_optional(self):
        """じゅうでん: 「つけてよい」（0〜1 枚。v0.41 のひなたぼっこと同じ）。"""
        waiting = attack(board([], active=m(PIKACHU_QSG, (LIGHTNING,)), deck=[LIGHTNING]), 0)
        self.assertEqual((waiting.decision.min_choices, waiting.decision.max_choices), (0, 1))
        after = answer(waiting, ())
        self.assertEqual(since(after, "attach_energy_from_deck_none")[:2], ["attach_energy_from_deck_none", "shuffle"])

    def test_crabhammer_call(self):
        """しおまねき: 「おもて」なら山札の「水」エネルギーカードを最大 3 枚（0 枚は HC7。決定は待ったまま）。山札は切らない。「うら」なら何もしない。"""
        state = board([], active=m(KINGLER_ES3, (WATER,)), deck=[WATER, FIRE, WATER, WATER, WATER])
        waiting = attack(state, 0, H)
        self.assertEqual((waiting.decision.min_choices, waiting.decision.max_choices), (0, 3))
        rejects(self, waiting, ResolveDecision(0, waiting.decision.id, ()), "UNRESOLVED_ATTACH_FROM_DISCARD_ZERO")
        order = list(waiting.players[0].deck)
        after = answer(waiting, waiting.decision.options[:3])
        self.assertEqual(ids(after, after.players[0].active.energy), [WATER] * 4)
        self.assertNotIn("shuffle", kinds_after(after, waiting)[:5])
        self.assertEqual(after.players[0].deck, [u for u in order if u not in waiting.decision.options[:3]])  # 残りの並びのまま（切っていない）
        self.assertEqual(observe(waiting, 1)["decision"], {"kind": ATTACH_FROM_DECK, "player": 0})
        tails = attack(state, 0, T)
        self.assertNotIn("shuffle", kinds_after(tails, state))
        self.assertFalse([e for e in tails.log if e["kind"].startswith("attach_energy_from_deck")])

    def test_energy_support_to_bench(self):
        """エナジーサポート: 山札の「超」エネルギーカード → 自分の控え（日本語の文面。手札には加えない）。控えがいなければつけずに切る。"""
        state = board([], active=m(SABRINAS_DROWZEE_GD6, (PSYCHIC,)), bench=(RATTATA, HITMONCHAN), deck=[PSYCHIC, FIRE])
        waiting = attack(state, 0)
        self.assertEqual((waiting.decision.kind, waiting.decision.context_value("stage")), (ATTACH_FROM_DECK, "card"))
        card = waiting.decision.options[0]
        bench = answer(waiting, (card,))
        self.assertEqual((bench.decision.kind, bench.decision.context_value("card")), (ATTACH_TO_BENCH, card))
        after = answer(bench, (bench.decision.options[1],))
        self.assertEqual(after.players[0].bench[1].energy, [card])
        self.assertNotIn(card, after.players[0].hand)
        audited(self, after)
        none = attack(board([], active=m(SABRINAS_DROWZEE_GD6, (PSYCHIC,)), bench=(), deck=[PSYCHIC]), 0)
        self.assertEqual(since(none, "attach_energy_from_deck_none")[:2], ["attach_energy_from_deck_none", "shuffle"])

    def test_energy_support_evaded_goes_to_discard(self):
        """つける控えが「とうめい」で受けなければ、カードは持ち主のトラッシュ（v0.45 の「じりょくせん」と同じ読み方。実装上の判断）。"""
        state = board([], active=m(SABRINAS_DROWZEE_GD6, (PSYCHIC,)), bench=({"card": HAUNTER, "evolved_from": "PMCG3-029"},), deck=[PSYCHIC])
        bench = answer(attack(state, 0), (state.players[0].deck[0],))
        after = answer(with_coin_results(bench, H), bench.decision.options)
        self.assertIn("deck_energy_evaded", kinds_after(after, bench))
        self.assertEqual(ids(after, after.players[0].discard)[-1:], [PSYCHIC])
        self.assertEqual(after.players[0].bench[0].energy, [])
        audited(self, after)


class DiscardEnergyAttackTest(unittest.TestCase):
    def test_ember_is_an_attack_effect(self):
        """ひのこ（ガーディ）: 炎エネルギーカード 1 枚のトラッシュはワザの効果（RUL-ENERGY-DISCARD-ATTACKS の範囲）。こんらんの「うら」ならトラッシュしない。"""
        state = board([], active=m(GROWLITHE_ES3, (FIRE, FIRE)))
        waiting = attack(state, 1)
        self.assertEqual(waiting.decision.kind, "discard_energy")
        after = answer(waiting, waiting.decision.options[:1])
        self.assertEqual(kinds_after(after, state)[:3], ["attack", "discard_energy", "damage"])
        confused = board([], active=m(GROWLITHE_ES3, (FIRE, FIRE), confusion=True))
        failed = attack(confused, 1, T)
        self.assertEqual(len(failed.players[0].active.energy) if failed.players[0].active else 0, 2)
        self.assertFalse([e for e in failed.log if e["kind"] == "discard_energy"])

    def test_thunderbolt_discards_every_energy_card(self):
        """10まんボルト: ついているエネルギーカードをすべて（種類を問わない。無色2個エネルギーも）トラッシュして 50。こんらん状態で使うときは HC1。"""
        state = board([], active=m(PIKACHU_QSG, (LIGHTNING, LIGHTNING, LIGHTNING, DOUBLE_COLORLESS_ENERGY, FIRE)), opponent_active=m(CHANSEY))
        after = attack(state, 1)
        self.assertEqual(after.players[0].active.energy, [])
        self.assertEqual([e["amount"] for e in after.log if e["kind"] == "damage"][-1], 50)
        confused = board([], active=m(PIKACHU_QSG, (LIGHTNING,) * 3, confusion=True))
        rejects(self, confused, UseAttack(0, 1), "UNRESOLVED_DISCARD_ENERGY_TIMING")


class EnergyAbsorptionTest(unittest.TestCase):
    def test_any_energy_cards(self):
        """エネルギーきゅうしゅう: トラッシュのエネルギーカード（特殊エネルギー・レインボーエネルギーも。色を選ばないので RB2 は当たらない）を最大 2 枚。0 枚は HC7。"""
        state = board([], active=m(MEWTWO_PR1, (PSYCHIC,)), discard=[FIRE, DOUBLE_COLORLESS_ENERGY, RAINBOW_ENERGY, POTION])
        waiting = attack(state, 0)
        self.assertEqual((waiting.decision.kind, waiting.decision.max_choices), (ATTACH_FROM_DISCARD, 2))
        self.assertEqual(sorted(ids(waiting, waiting.decision.options)), sorted([FIRE, DOUBLE_COLORLESS_ENERGY, RAINBOW_ENERGY]))
        rejects(self, waiting, ResolveDecision(0, waiting.decision.id, ()), "UNRESOLVED_ATTACH_FROM_DISCARD_ZERO")
        after = answer(waiting, waiting.decision.options[1:3])
        self.assertEqual(sorted(ids(after, after.players[0].active.energy)), sorted([PSYCHIC, DOUBLE_COLORLESS_ENERGY, RAINBOW_ENERGY]))
        self.assertFalse([e for e in after.log if e["kind"] == "energy_damage"])  # 手札から出していないので、レインボーエネルギーの 10 はない
        audited(self, after)
        none = attack(board([], active=m(MEWTWO_PR1, (PSYCHIC,)), discard=[POTION]), 0)
        self.assertIsNone(none.decision)

    def test_tower_does_not_suppress(self):
        """トラッシュから場のポケモンにつける効果なので、ポケモンタワーでは消えない。"""
        state = use(board([POKEMON_TOWER], active=m(MEWTWO_PR1, (PSYCHIC,)), discard=[FIRE]), POKEMON_TOWER)
        waiting = attack(state, 0)
        self.assertEqual(waiting.decision.kind, ATTACH_FROM_DISCARD)


class DoubleEdgedTest(unittest.TestCase):
    """もろばバサミ: 次の相手の番、受けるワザのダメージは p.321 の 8 段階で 2 倍。ワザでないダメージは推測で広げない（特殊能力 DB1・トレーナー TD1）。"""

    def kingler(self, **extra):
        return board([DIGGER], active=m(KINGLER_ES3, (WATER,) * 4), opponent_active=m(CHANSEY, (FIGHTING,) * 4), opponent_hand=[DIGGER], **extra)

    def test_doubled_attack_damage_in_the_next_opponent_turn(self):
        state = attack(self.kingler(), 1)
        effect = next(e for e in state.players[0].active.persistent_effects if isinstance(e, DoubledDamage))
        self.assertEqual((effect.created_turn + 1, effect.active_turn), (state.turn_number, state.turn_number))
        hit = attack(state, 0, player=1)  # まるまる（ダメージなし）ではなく、すてみタックル
        hit = attack(state, 1, player=1)
        damage = [e for e in hit.log if e["kind"] == "damage" and e["player"] == 0][-1]
        self.assertEqual((damage["amount"], damage["damage_multiplied"]), (160, ((8, effect.source_card, 2),)))
        audited(self, hit)

    def test_not_active_in_own_turn_and_expires(self):
        """自分の番にははたらかない。次の相手の番の終わりに消える（相手がワザを使わずに番を終えても消える）。"""
        state = attack(self.kingler(), 1)
        ended = apply_kernel(state, __import__("kyuura_engine").EndTurn(1))
        self.assertFalse([e for e in ended.players[0].active.persistent_effects if isinstance(e, DoubledDamage)])

    def test_trainer_damage_is_td1(self):
        """相手の番のバトル場は穴だらけ!（トレーナーのダメージ）に 2 倍を当てはめるかは TD1（使う前。コインの前）。"""
        state = attack(self.kingler(), 1)
        rejects(self, state, PlayTrainer(1, next(u for u in state.players[1].hand if state.cards[u].card_id == DIGGER)), "UNRESOLVED_TRAINER_DAMAGE_REDUCTION")

    def test_power_damage_is_db1(self):
        """特殊能力のダメージに 2 倍を当てはめるかは DB1（量を変える前に止める）。"""
        state = attack(self.kingler(), 1)
        with self.assertRaises(UnsupportedError) as caught:
            E.received_power_damage(state, 0, state.players[0].active, state.players[1].active, 10)
        self.assertEqual(caught.exception.code, "UNRESOLVED_DOUBLED_DAMAGE_POWER_DAMAGE")
        self.assertEqual(E.received_power_damage(state, 0, state.players[0].active, state.players[1].active, 0)[0], 0)


class OtherAttacksTest(unittest.TestCase):
    def test_errand_variant_and_growth_variant(self):
        """おつかい（ガーディ）は v0.44 の型の書き方の違い。せいちょう（ヒマナッツ）は v0.46 の型の書き方の違い（「自分につける」）。"""
        waiting = attack(board([], active=m(GROWLITHE_QSG, (FIRE, FIRE)), deck=[POTION, FIRE]), 0, H)
        self.assertEqual(ids(waiting, waiting.decision.options), [POTION])
        hand = board([GRASS, GRASS, GRASS], active=m(SUNKERN_PRN, (GRASS,)))
        growth = attack(hand, 0, H)
        self.assertEqual((growth.decision.kind, growth.decision.max_choices), ("attach_from_hand", 2))
        after = answer(growth, growth.decision.options[:2])
        self.assertEqual(ids(after, after.players[0].active.energy), [GRASS] * 3)


if __name__ == "__main__":
    unittest.main()

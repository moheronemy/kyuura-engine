"""v0.122（docs/unown-fossil-retreat-reactions-v0.122.md）: アンノーンの併用・化石の進化履歴・退却時の反応の 13 枚（ポケモン 13。ワザ 17・特殊能力 8）。アンノーンM（neo2-027）・
U（neo2-028）・A（neo2-030）・W（neo4-064）・マチスのライチュウ（GD3-003）・オムナイト（ES2-011・ES3-018）・カブト（ES2-028）・プテラ（ES2-029）・カポエラー（PRN-030）・
わるいフシギソウ（PRN-039）・わるいフシギバナ（PRN-040）・わるいオニドリル（PRN-045）。

盤面は ``build_test_state`` と通常の操作で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（自然な対戦は ``AuditTest`` と文書 13 章）。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import unittest
from typing import ClassVar

from kyuura_engine import EndTurn, EvolvePokemon, ResolveDecision, Retreat, UseAttack
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import command_from_dict, command_to_dict
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe
from kyuura_engine.serialize import state_to_dict
from scripts import check_card_sources as cs
from tests import helpers as H
from tests.test_fossil_basic_virtual_attacks_v0_120 import (
    TURN,
    power_use,
    spec,
    trainer,
)
from tests.test_neo_trainer_components_v0_80 import audited, new_events
from tests.test_unown_family_powers_v0_96 import snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "unown-fossil-retreat-reactions-v0.122.md"
LINKS_PATH = ROOT / "kyuura_engine" / "data" / "research_links.json"
NOW = "2fe0bc042ce187d191843819262f8036abbb343d"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
P, L, G, F, W = H.PSYCHIC, H.LIGHTNING, H.GRASS, H.FIGHTING, H.WATER

UNOWN_M, UNOWN_U, UNOWN_A, UNOWN_W = "neo2-027", "neo2-028", "neo2-030", "neo4-064"
RAICHU, OMANYTE, KABUTO, AERODACTYL, OMANYTE_GUIDE = "GD3-003", "ES2-011", "ES2-028", "ES2-029", "ES3-018"
HITMONTOP, IVYSAUR, VENUSAUR, FEAROW = "PRN-030", "PRN-039", "PRN-040", "PRN-045"
V0122 = (UNOWN_M, UNOWN_U, UNOWN_A, UNOWN_W, RAICHU, OMANYTE, KABUTO, AERODACTYL, OMANYTE_GUIDE, HITMONTOP, IVYSAUR, VENUSAUR, FEAROW)
UNOWN_N, UNOWN_X, UNOWN_D, UNOWN_O, UNOWN_T = "PF2-001", "neo4-065", "neo2-025", "PF2-003", "neo4-052"
FOSSIL, KABUTO_REVIVER, KABUTOPS = H.MYSTERIOUS_FOSSIL, "neo2-014", "neo2-018"
SURGES_PIKACHU, BULBASAUR, SPEAROW = "GD3-001", "PMCG1-001", "PMCG2-034"
DIGLETT = "PMCG1-052"  # ディグダ（HP 30・闘・弱点 草・抵抗力 雷。超の弱点なし）
SKARMORY = "neo1-058"  # エアームド（鋼。かぎづめ（無）20）
MISTYS_CLOYSTER, MISTYS_SHELLDER = "GD2-007", "GD2-006"  # カスミのパルシェン（［シェルアーマー］: ワザのダメージを受けるたびに使うかを持ち主が選ぶ）
FLAAFFY_DARK, MAREEP = "neo4-044", "NIP2-018"  # わるいモココ（スタンウェーブ: 次の相手の番、受けたポケモンの特殊能力をなくす）
STOP_CODES = {"FE3": E.FOSSIL_EVOLVED_READING_CODE, "PM1": E.PRIMAL_DREAM_SUPPRESSED_CODE, "PM2": E.PRIMAL_DREAM_DAMAGE_STEP_CODE,
              "WT1": E.WANT_WITHOUT_TARGET_CODE, "GU1": E.FOSSIL_GUIDE_WITHOUT_TARGET_CODE, "FS1": E.FOSSILIZE_WITHOUT_TARGET_CODE,
              "PW5": E.TOWER_POWER_WITHOUT_EFFECT_CODE, "VL1": E.VINE_PULL_TIMING_CODE}
DF1 = "UNRESOLVED_SELF_EXCLUDING_POWER_COPIES"


def board(active, *, bench=(), hand=(), discard=(), opponent=None, opponent_bench=(), turn=TURN, current=0):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": [W] * 10, "discard": list(discard), "prizes": 6}
    them = {"active": opponent or spec(H.CHANSEY), "bench": list(opponent_bench), "hand": [], "deck": [W] * 10, "discard": [], "prizes": 6}
    players = [me, them] if current == 0 else [them, me]
    return H.build_test_state(players, turn_number=turn, current_player=current)


def pid(state, player, card):
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card)


def run(state, command, *coins):
    return H.apply_kernel(H.with_coin_results(state, *coins) if coins else state, command)


def answer(state, choices, *coins):
    d = state.decision
    return run(state, ResolveDecision(d.player, d.id, tuple(choices)), *coins)


def rejected(test, state, fn, code):
    before = snap(state)
    with test.assertRaises((IllegalActionError, UnsupportedError)) as raised:
        fn(state)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(snap(state), before)
    return raised.exception


def resumed(test, state, fn):
    """決定の途中の状態 ``state`` を、複製・deepcopy・pickle のそれぞれから ``fn`` で続けた結果が、元から続けた結果と同じこと（支払い・移動・コイン・ダメージが 1 回だけ）。"""
    done = fn(state)
    for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
        test.assertEqual(snap(fn(other)), snap(done))
    return done


def damages(before, after):
    """新しいダメージのログの (量, 変更効果の記録 (段階, 発生源のカード, 量))。"""
    return [(e["amount"], e.get("modifiers")) for e in new_events(before, after, "damage")]


# ---------------------------------------------------------------- 2 章: 13 枚の登録・採用の記録・研究の対応表

class RegistrationTest(unittest.TestCase):
    """2 章: 13 枚・17 のワザ・8 の特殊能力の登録、写しの組、採用の記録、研究の対応表。"""

    def test_cards_and_registrations(self):
        pool = load_card_pool()
        extract = read_extract()
        self.assertEqual(extract["pool_v0_122"], list(V0122))
        for card in V0122:
            self.assertIn(card, pool.playable_ids, card)
        registry = E.DEFAULT_EFFECTS
        self.assertEqual(sorted(key for key in registry.attack_keys() if key.card_id in V0122), sorted(E.V0_122_ATTACKS))
        self.assertEqual(sorted(key for key in registry.power_keys() if key.card_id in V0122), sorted(E.V0_122_POWERS))
        self.assertEqual((len(E.V0_122_ATTACKS), len(E.V0_122_POWERS)), (17, 8))
        for key in E.V0_122_ATTACKS:
            definition = pool.get(key.card_id)
            self.assertIsNone(registry.attack_problem(key.card_id, definition.attacks[key.attack_index], definition.attacks), key)
        for key in E.V0_122_POWERS:
            self.assertIsNone(registry.power_problem(key.card_id, pool.get(key.card_id).powers[key.power_index]), key)
        # 印刷の段階はたね 5・1 進化 7・2 進化 1。進化元は登録済みか今回の対象（なにかの化石はトレーナー）
        stages = [pool.get(card).stage for card in V0122]
        self.assertEqual((stages.count("basic"), stages.count("stage1"), stages.count("stage2")), (5, 7, 1))
        self.assertEqual({card: pool.get(card).evolves_from for card in V0122 if pool.get(card).evolves_from},
                         {RAICHU: "マチスのピカチュウ", OMANYTE: "なにかの化石", KABUTO: "なにかの化石", AERODACTYL: "なにかの化石", OMANYTE_GUIDE: "なにかの化石",
                          IVYSAUR: "フシギダネ", VENUSAUR: "わるいフシギソウ", FEAROW: "オニスズメ"})
        self.assertEqual(pool.get(FOSSIL).category, "trainer")
        self.assertEqual([(pool.get(c).name_group, pool.get(c).name_letter) for c in (UNOWN_M, UNOWN_U, UNOWN_A, UNOWN_W)],
                         [("アンノーン", "M"), ("アンノーン", "U"), ("アンノーン", "A"), ("アンノーン", "W")])

    def test_reused_types_are_bound_to_their_numbers(self):
        """2 章: 再利用した型は数値・範囲・順序も照らす。形の検査だけでは通る誤った数値（きりもみアタックの自分へ 20、10まんボルトのダメージのあとのトラッシュ）を登録しない。"""
        registry = E.DEFAULT_EFFECTS
        pool = load_card_pool()
        entry = {key: registry.attack_entry(key.card_id, key.attack_index).effect for key in E.V0_122_ATTACKS}
        self.assertEqual(entry[E.AttackKey(FEAROW, 0)], E.SetNextTurnAttackDamage(1, "ドリルダイブ", 80, target_text=E.DRILL_DIVE_TEXT))
        self.assertEqual(entry[E.AttackKey(KABUTO, 0)], E.CoinBonusDamage(30))
        self.assertEqual(entry[E.AttackKey(HITMONTOP, 0)], E.CoinsUntilTailsDamage(20))
        self.assertEqual(entry[E.AttackKey(AERODACTYL, 1)], E.DamageAndSelfDamageIgnoringWeaknessResistance(10))
        self.assertEqual(entry[E.AttackKey(IVYSAUR, 0)], E.OpponentChoosesRepeatedTargetsDamage(3, 10))
        self.assertEqual(type(entry[E.AttackKey(RAICHU, 1)]), E.DiscardAllEnergyCardsThenDamageZeroIfLacking)
        self.assertEqual(registry.power_entry(UNOWN_M, 0).effect, E.ReduceOwnGroupDamageFromType(E.EnergyType.METAL, "M", "METAL df"))
        spin = pool.get(AERODACTYL).attacks[1]
        self.assertNotEqual(E.DamageAndSelfDamageIgnoringWeaknessResistance(20).check(spin), [])
        strike = pool.get(IVYSAUR).attacks[0]
        self.assertNotEqual(E.OpponentChoosesRepeatedTargetsDamage(2, 10).check(strike), [])
        bolt = pool.get(RAICHU).attacks[1]
        self.assertEqual(E.DiscardAllEnergyCardsThenDamageZeroIfLacking().check(bolt), [])
        old_bolt = pool.get("IP1-003").attacks[1]  # v0.82 の「ダメージのあとにすべて捨てる」10まんボルト（文面も時点も違う）
        self.assertNotEqual(E.DiscardAllEnergyCardsThenDamageZeroIfLacking().check(old_bolt), [])
        self.assertIsInstance(registry.attack_entry("IP1-003", 1).effect, E.DamageThenDiscardAllEnergyCards)

    def test_adoption_records_and_links(self):
        sources = cs.load_sources()["cards"]
        links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
        for card in V0122:
            record = sources[card]
            self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"], record["external_checks"]),
                             ("kyuura_data", "adopted", NOW, "2026-10-30", []), card)
        self.assertEqual(sources[UNOWN_M]["kyuura_records"], ["CR-UNOWN-DF-AT-MOST-ONE", "CR-UNOWN-DF-PROTECTS-OWN-UNOWN", "UQ-SELF-EXCLUDING-POWER-COPIES"])
        self.assertEqual([sources[c]["kyuura_records"] for c in V0122 if c != UNOWN_M], [[]] * 12)
        self.assertIn("M 自身の独立した裁定として引かない", sources[UNOWN_M]["notes"])
        printed = set(links["latest_descriptions"]["adopted_printed_text"])
        expected = {f"{key.card_id}/attack/{key.attack_index}" for key, entry in E.V0_122_ATTACKS.items() if entry.text_ja is not None} | {
            f"{key.card_id}/power/{key.power_index}" for key in E.V0_122_POWERS}
        self.assertEqual(len(expected), 18)
        self.assertLessEqual(expected, printed)
        cases = {(c["kyuura_issue"], c["card_id"], c["target"]): c["engine"] for c in links["kyuura_cases_without_engine_ruling"]["cases"]}
        self.assertEqual(cases[("UQ-SELF-EXCLUDING-POWER-COPIES", UNOWN_M, "power/0")], {"stop_codes": [DF1]})
        for ruling, code in STOP_CODES.items():
            link = links["stop_codes"][code]
            self.assertEqual((link["engine_rulings"][0]["ruling_id"], link["kyuura_disposition"], link["kyuura_issue"]), (ruling, "not_in_kyuura", None))
            self.assertTrue(code.startswith("UNRESOLVED_"), code)

    def test_removing_the_registrations_restores_the_previous_catalog(self):
        """今回の登録だけを外すと 1,342 枚にもどる（ほかのカードは失われない）。"""
        registry = E.DEFAULT_EFFECTS.without_attacks("test-without-v0122", list(E.V0_122_ATTACKS)).without_powers("test-without-v0122-powers", list(E.V0_122_POWERS))
        pool = pool_from_extract(read_extract(), registry)
        full = load_card_pool()
        self.assertEqual(full.playable_ids - pool.playable_ids, frozenset(V0122))
        from tests.release_catalog import cards_after

        self.assertEqual(len(pool.playable_ids - cards_after(read_extract(), "0.122")), 1342)  # v0.123 からの組を除いた、v0.122 の時点の数


# ---------------------------------------------------------------- 3 章: アンノーン（［ANGER］と［XXXXX］の併用・［METAL df］・［UNDO］・［WANT］）

def unown_board(opponent=DIGLETT, *, anger_damage=20):
    """バトル場のアンノーン[N]（超 1）、ベンチのアンノーンA（ダメージ ``anger_damage``）・X。デッキの上限（文字を問わず 4 枚）の内側の 3 枚。"""
    return board(spec(UNOWN_N, (P,)), bench=(spec(UNOWN_A, damage=anger_damage), spec(UNOWN_X)),
                 opponent=spec(opponent, below=(MISTYS_SHELLDER,)) if opponent == MISTYS_CLOYSTER else spec(opponent))


class AngerAndXxxxxTest(unittest.TestCase):
    """3.1〜3.3 節: 1 つの「めざめるパワー」の宣言で、ベンチの［ANGER］と［XXXXX］をいっしょに使う。"""

    def test_both_powers_in_one_declaration(self):
        state = unown_board()
        a, x = pid(state, 0, UNOWN_A), pid(state, 0, UNOWN_X)
        after = run(state, UseAttack(0, 0, with_powers=(a, x)), HD, HD, TL)
        self.assertEqual(damages(state, after), [(50, ((6, state.players[0].bench[0].card, 20), (6, state.players[0].bench[1].card, 20)))])
        kinds = [e["kind"] for e in new_events(state, after) if e["kind"].startswith("group_attack_power")]
        self.assertEqual(kinds, ["group_attack_power", "group_attack_power", "group_attack_power_counters", "group_attack_power_coins"])
        (counters,) = new_events(state, after, "group_attack_power_counters")
        self.assertEqual((counters["pokemon_id"], counters["counters"], counters["amount"], counters["step"]), (a, 2, 20, 6))
        coins = [e for e in new_events(state, after, "coin_flip")]
        self.assertEqual([(e["source"], e["result"]) for e in coins], [("power", "heads"), ("power", "heads"), ("power", "tails")])  # 特殊能力のコイン（ESP の対象ではない）
        # 並びの順で結果は変わらない（どちらも加算）
        swapped = run(state, UseAttack(0, 0, with_powers=(x, a)), HD, HD, TL)
        self.assertEqual([e["amount"] for e in new_events(state, swapped, "damage")], [50])
        audited(self, after)

    def test_old_single_power_command_is_unchanged(self):
        """``with_power`` の古いコマンド・辞書・再開はそのまま。1 つだけの ``with_powers`` は ``with_power`` と同じ処理・同じログ。空の ``with_powers`` は辞書に書かない。"""
        state = unown_board()
        a, x = pid(state, 0, UNOWN_A), pid(state, 0, UNOWN_X)
        old = run(state, UseAttack(0, 0, with_power=x), HD, TL)
        new = run(state, UseAttack(0, 0, with_powers=(x,)), HD, TL)
        self.assertEqual(snap(old), snap(new))
        self.assertEqual([e["amount"] for e in new_events(state, old, "damage")], [20])
        self.assertNotIn("with_powers", command_to_dict(UseAttack(0, 0)))
        self.assertNotIn("with_powers", command_to_dict(UseAttack(0, 0, with_power=x)))
        both = UseAttack(0, 0, with_powers=(a, x))
        self.assertEqual(command_to_dict(both)["with_powers"], [a, x])
        self.assertEqual(command_from_dict(command_to_dict(both)), both)
        self.assertEqual(command_from_dict(command_to_dict(UseAttack(0, 0, with_power=x))), UseAttack(0, 0, with_power=x))

    def test_bad_declarations_are_rejected_without_changes(self):
        state = unown_board()
        a, x = pid(state, 0, UNOWN_A), pid(state, 0, UNOWN_X)
        rejected(self, state, lambda s: run(s, UseAttack(0, 0, with_power=x, with_powers=(a,))), "BAD_COMMAND")
        rejected(self, state, lambda s: run(s, UseAttack(0, 0, with_powers=(a, a))), "DUPLICATE_POWER")
        rejected(self, state, lambda s: run(s, UseAttack(0, 0, with_powers=(a, state.players[1].active.pokemon_id))), "ATTACK_POWER_NOT_AVAILABLE")
        two = board(spec(UNOWN_N, (P,)), bench=(spec(UNOWN_A, damage=20), spec(UNOWN_A, damage=10)), opponent=spec(DIGLETT))
        first, second = (p.pokemon_id for p in two.players[0].bench)
        rejected(self, two, lambda s: run(s, UseAttack(0, 0, with_powers=(first, second))), "POWER_ALREADY_USED")  # このカード以外の A が使っている
        # 使えない力（相手のバトル場のベトベトンの［かがくへんかガス］で消えている）
        gas = board(spec(UNOWN_N, (P,)), bench=(spec(UNOWN_A, damage=20), spec(UNOWN_X)), opponent=spec(H.MUK, below=(H.GRIMER,)))
        rejected(self, gas, lambda s: run(s, UseAttack(0, 0, with_powers=(pid(s, 0, UNOWN_A), pid(s, 0, UNOWN_X)))), "POWER_SUPPRESSED")

    def test_anger_counts_the_holder_and_allows_zero(self):
        """追加はカウンターをのせた A の個体の数 × 10（ワザを使う個体ではない）。0 個でも使える。A 自身がワザを使えば p.321 の 2 段階。"""
        zero = unown_board(anger_damage=0)
        after = run(zero, UseAttack(0, 0, with_powers=(pid(zero, 0, UNOWN_A),)))
        self.assertEqual([e["amount"] for e in new_events(zero, after, "damage")], [10])
        self.assertEqual([(e["counters"], e["amount"]) for e in new_events(zero, after, "group_attack_power_counters")], [(0, 0)])
        self_use = board(spec(UNOWN_A, (P,), damage=20), bench=(spec(UNOWN_X),), opponent=spec(DIGLETT))
        a = self_use.players[0].active.pokemon_id
        done = run(self_use, UseAttack(0, 0, with_powers=(a,)))
        self.assertEqual(damages(self_use, done), [(30, ((2, self_use.players[0].active.card, 20),))])
        # ワザだけを借りたアンノーンでないポケモン・「めざめるパワー」でないワザには使えない
        other = board(spec(H.CHANSEY, (P, P)), bench=(spec(UNOWN_A, damage=20),), opponent=spec(DIGLETT))
        anger = E.DEFAULT_EFFECTS.power_entry(UNOWN_A, 0).effect
        self.assertIsNotNone(anger.usable_for(other, other.players[0].active, E.AttackKey(H.CHANSEY, 0)))
        self.assertIsNone(anger.usable_for(self_use, self_use.players[0].active, E.AttackKey(UNOWN_A, 0)))

    def test_anger_and_xxxxx_have_different_limits(self):
        """［ANGER］は「ほかの A が使っている」（同じ宣言）だけを禁じ、番の使用の記録は持たない。［XXXXX］は「この番に、すでにほかの X を使った」（記録する）。"""
        anger = E.DEFAULT_EFFECTS.power_entry(UNOWN_A, 0).effect
        xxxxx = E.DEFAULT_EFFECTS.power_entry(UNOWN_X, 0).effect
        self.assertFalse(anger.records_turn_use)
        self.assertTrue(xxxxx.records_turn_use)
        self.assertNotEqual(anger.exclusive_key(), xxxxx.exclusive_key())
        self.assertTrue(anger.counts_holder_counters)
        self.assertFalse(anger.uses_coins)
        self.assertTrue(xxxxx.uses_coins)

    def test_metal_df_protects_own_unown_by_attacker_type(self):
        """3.4 節: ［METAL df］は自分の場のアンノーン（M 自身も）が鋼ポケモン（ダメージを与える個体の今のタイプ）から受けるダメージを -30。2 匹の M は DF1（読み方で受けるダメージが
        変わる。-60 にしない）。鋼でないポケモンからのダメージは変わらない。"""
        def hit(bench, active=UNOWN_N, attacker=SKARMORY, energy=(P,)):
            """相手（プレイヤー 1）の ``attacker`` が、プレイヤー 0 のバトル場の ``active``（ベンチ ``bench``）にワザを使う。"""
            state = board(spec(attacker, energy), opponent=spec(active), opponent_bench=bench, turn=TURN + 1, current=1)
            return state, lambda s: run(s, UseAttack(1, 0))

        state, attack = hit((spec(UNOWN_M),))
        self.assertEqual([(e["amount"], e["modifiers"]) for e in new_events(state, attack(state), "damage")], [(0, ((6, state.players[0].bench[0].card, -30),))])
        state, attack = hit((), active=UNOWN_M)
        self.assertEqual([e["amount"] for e in new_events(state, attack(state), "damage")], [0])
        state, attack = hit((spec(UNOWN_M), spec(UNOWN_M)))
        rejected(self, state, attack, DF1)
        state, attack = hit((spec(UNOWN_M),), attacker=H.MACHOP, energy=(F,))
        self.assertEqual([e["amount"] for e in new_events(state, attack(state), "damage")], [20])


class UndoWantTest(unittest.TestCase):
    """3.5・3.6 節: ［UNDO］（N・D・O）・［WANT］（A・N・T）。どちらも U・W 自身と 3 つの文字が自分のベンチにそろうとき、自分の番ごとに 1 回。"""

    def undo_board(self, *, letters=(UNOWN_N, UNOWN_D, UNOWN_O), hand=()):
        active = spec(H.MACHOP, (F, F), damage=20, trainers=[(H.PLUSPOWER, TURN)])
        return board(active, bench=(spec(UNOWN_U), *(spec(c) for c in letters)), hand=hand, opponent=spec(H.CHANSEY))

    def test_undo_returns_the_active_and_all_attached_cards(self):
        state = self.undo_board()
        active = state.players[0].active
        cards = {active.card, *active.energy, *(t.card for t in active.trainers)}
        after = power_use(state, pid(state, 0, UNOWN_U))
        (returned,) = new_events(state, after, "return_in_play_to_hand")
        self.assertEqual((returned["pokemon_id"], returned["damage"], returned["power"]), (active.pokemon_id, 20, f"{UNOWN_U}@power0"))
        self.assertEqual(set(returned["cards"]), cards)
        self.assertLessEqual(cards, set(after.players[0].hand))
        self.assertEqual((after.decision.kind, after.decision.player), ("promote_active", 0))  # 対戦ポケモンの補充（きぜつ・サイドではない）
        self.assertEqual(new_events(state, after, "knock_out", "take_prize"), [])
        audited(self, after)

    def test_undo_needs_every_letter_and_is_not_a_discard_recovery(self):
        missing = self.undo_board(letters=(UNOWN_N, UNOWN_D, UNOWN_T))
        rejected(self, missing, lambda s: power_use(s, pid(s, 0, UNOWN_U)), "REQUIRED_BENCH_POKEMON_MISSING")
        tower = trainer(self.undo_board(hand=(H.POKEMON_TOWER,)), H.POKEMON_TOWER)  # ポケモンタワー（トラッシュからの回収を消す）は［UNDO］を止めない
        after = power_use(tower, pid(tower, 0, UNOWN_U))
        self.assertEqual(len(new_events(tower, after, "return_in_play_to_hand")), 1)

    def want_board(self, discard, *, hand=(), letters=(UNOWN_A, UNOWN_N, UNOWN_T)):
        return board(spec(H.MACHOP), bench=(spec(UNOWN_W), *(spec(c) for c in letters)), hand=hand, discard=discard, opponent=spec(H.CHANSEY))

    def test_want_heads_recovers_a_revealed_trainer_and_tails_uses_it(self):
        state = self.want_board([H.PLUSPOWER, H.MACHOP, FOSSIL])
        w = pid(state, 0, UNOWN_W)
        heads = power_use(state, w, HD)
        d = heads.decision
        self.assertEqual((d.kind, d.player, sorted(heads.cards[u].card_id for u in d.options)), ("recover_trainer", 0, sorted([H.PLUSPOWER, FOSSIL])))
        done = resumed(self, heads, lambda s: answer(s, (d.options[0],)))
        (got,) = new_events(heads, done, "power_recover_from_discard")
        self.assertEqual((got["card"], got["revealed"]), (d.options[0], True))
        self.assertIn(d.options[0], done.players[0].hand)
        tails = power_use(state, w, TL)
        self.assertIsNone(tails.decision)
        rejected(self, tails, lambda s: power_use(s, w, HD), "POWER_ALREADY_USED")  # 「うら」でも使ったことになる
        audited(self, done)

    def test_want_stops_before_the_coin(self):
        rejected(self, self.want_board([H.MACHOP]), lambda s: power_use(s, pid(s, 0, UNOWN_W), HD), STOP_CODES["WT1"])
        tower = trainer(self.want_board([H.PLUSPOWER], hand=(H.POKEMON_TOWER,)), H.POKEMON_TOWER)
        rejected(self, tower, lambda s: power_use(s, pid(s, 0, UNOWN_W), HD), STOP_CODES["PW5"])
        rejected(self, self.want_board([H.PLUSPOWER], letters=(UNOWN_A, UNOWN_N, UNOWN_D)), lambda s: power_use(s, pid(s, 0, UNOWN_W), HD),
                 "REQUIRED_BENCH_POKEMON_MISSING")

    def test_unown_deck_limit_counts_every_letter(self):
        """「アンノーン」はデッキに 4 枚まで（文字を問わず合わせて）。U 用・W 用・A+X 用の組は別のデッキに分ける。"""
        from kyuura_engine.deck import deck_problems

        base = [P] * 52 + [H.MACHOP] * 4
        self.assertEqual(deck_problems(base + [UNOWN_U, UNOWN_N, UNOWN_D, UNOWN_O]), [])
        self.assertTrue([p for p in deck_problems(base[:-1] + [UNOWN_U, UNOWN_N, UNOWN_D, UNOWN_O, UNOWN_W]) if "アンノーン" in p])


# ---------------------------------------------------------------- 4 章: 化石の進化履歴（［げんしのゆめ］・［かせきか］・［かせきのみちびき］）

def kabuto(**extra):
    return spec(KABUTO, extra.pop("energy", (F, F)), below=(FOSSIL,), **extra)


class FossilEvolutionReadingTest(unittest.TestCase):
    """4.1 節: 「「なにかの化石」から進化したポケモン」の 5 つの盤面（と、かかわりのないポケモン）。"""

    def test_five_boards(self):
        state = board(kabuto(), bench=(spec(KABUTOPS, below=(FOSSIL, KABUTO_REVIVER)), spec(KABUTO_REVIVER, revived=True),
                                       spec(KABUTOPS, below=(KABUTO_REVIVER,), revived=True), spec(H.MACHOP)), opponent=spec(H.CHANSEY))
        answers = [E.fossil_evolution(state, p) for p in state.players[0].in_play()]
        self.assertEqual([a for a, _ in answers], ["yes", "undecided", "undecided", "undecided", "no"])
        self.assertIn("直前の進化元では当たらない・重なりの根元で当たる", answers[1][1])
        self.assertIn("直前の進化元では当たらない・重なりの根元では当たらない・今の姿の印刷の進化元で当たる", answers[2][1])
        self.assertIn("今の姿の印刷の進化元では当たらない・印刷の系統で当たる", answers[3][1])
        # 別の系統から化石の姿になった個体: 相手のカブト（化石に直接重ねた）を写すメタモン（［へんしん］）
        ditto = board(spec(H.DITTO), opponent=kabuto())
        reading, detail = E.fossil_evolution(ditto, ditto.players[0].active)
        self.assertEqual(reading, "undecided")
        self.assertIn("今の姿の印刷の進化元で当たる", detail)
        self.assertEqual(E.fossil_evolution(ditto, ditto.players[1].active), ("yes", None))


class PrimalDreamTest(unittest.TestCase):
    """4.2 節: ［げんしのゆめ］（この番だけ、化石から進化したポケモンのワザが相手に与えるダメージ +10）。"""

    def test_each_omanyte_adds_ten_at_step_six_to_the_defender_only(self):
        state = board(kabuto(), bench=(spec(OMANYTE, below=(FOSSIL,)), spec(OMANYTE, below=(FOSSIL,))), opponent=spec(H.MACHOP))
        first, second = (p.pokemon_id for p in state.players[0].bench)
        once = power_use(state, first, HD)
        self.assertEqual([e["effect_kind"] for e in new_events(state, once, "trainer_effect_added")], ["fossil_attack_bonus"])
        twice = power_use(once, second, HD)
        hit = run(twice, UseAttack(0, 0), TL)  # するどいツメの「うら」: 10
        self.assertEqual(damages(twice, hit), [(30, ((6, state.players[0].bench[0].card, 10), (6, state.players[0].bench[1].card, 10)))])
        rejected(self, twice, lambda s: power_use(s, first, HD), "POWER_ALREADY_USED")
        tails = power_use(state, first, TL)
        self.assertEqual(new_events(state, tails, "trainer_effect_added"), [])
        confused = board(kabuto(confusion=True), bench=(spec(OMANYTE, below=(FOSSIL,)),), opponent=spec(H.MACHOP))
        dreamt = power_use(confused, pid(confused, 0, OMANYTE), HD)
        missed = run(dreamt, UseAttack(0, 0), TL)  # こんらんの 20（相手に与えるダメージではない）は変わらない
        self.assertEqual([e["amount"] for e in new_events(dreamt, missed, "confusion_damage")], [20])

    def test_the_same_card_on_another_fossil_can_dream_again(self):
        """不具合の回帰（v0.122 の実装中に見つけた。文書 4.2 節・13 章）: ［げんしのゆめ］を使ったオムナイトのカードが、同じ番に［かせきか］で手札にもどり、前の番から場にいる別のなにかの化石に
        重ねられると、別のポケモンとしてもう一度使える。同じカード・同じ消える番の 2 つの効果を、使ったポケモンの番号で分ける（直す前は状態の不変条件の内部エラー）。"""
        from kyuura_engine import check_invariants

        state = board(kabuto(), bench=(spec(OMANYTE, below=(FOSSIL,)), spec(FOSSIL)), opponent=spec(H.MACHOP))
        omanyte, fossil = state.players[0].bench
        dreamt = power_use(state, omanyte.pokemon_id, HD)
        returned = answer(power_use(dreamt, state.players[0].active.pokemon_id), (omanyte.pokemon_id,), HD)
        again = power_use(run(returned, EvolvePokemon(0, omanyte.card, fossil.pokemon_id)), fossil.pokemon_id, HD)
        self.assertEqual(sorted((r.source_card, r.pokemon_id) for r in again.trainer_effects), [(omanyte.card, omanyte.pokemon_id), (omanyte.card, fossil.pokemon_id)])
        hit = run(again, UseAttack(0, 0), TL)  # するどいツメの「うら」10 + 2 つの効果
        self.assertEqual(damages(again, hit), [(30, ((6, omanyte.card, 10), (6, omanyte.card, 10)))])
        self.assertEqual(check_invariants(hit), [])
        audited(self, again)

    def test_omanyte_itself_stops_only_when_the_step_matters(self):
        """使ったオムナイト自身のワザ: 2 段階か 6 段階かで受けるダメージが変わるときだけ PM2（弱点のある相手）。変わらなければ 6 段階で計算する。"""
        same = board(spec(OMANYTE, (W, W), below=(FOSSIL,)), opponent=spec(H.MACHOP))
        dreamt = power_use(same, same.players[0].active.pokemon_id, HD)
        self.assertEqual(damages(dreamt, run(dreamt, UseAttack(0, 0))), [(30, ((6, same.players[0].active.card, 10),))])
        weak = board(spec(OMANYTE, (W, W), below=(FOSSIL,)), opponent=spec(H.CHARMANDER))
        dreamt = power_use(weak, weak.players[0].active.pokemon_id, HD)
        rejected(self, dreamt, lambda s: run(s, UseAttack(0, 0)), STOP_CODES["PM2"])

    def test_undecided_attackers_and_suppressed_sources_stop(self):
        stage2 = board(spec(KABUTOPS, (W,) * 4, below=(FOSSIL, KABUTO_REVIVER)), bench=(spec(OMANYTE, below=(FOSSIL,)),), opponent=spec(H.CHANSEY))
        dreamt = power_use(stage2, pid(stage2, 0, OMANYTE), HD)
        rejected(self, dreamt, lambda s: run(s, UseAttack(0, 0)), STOP_CODES["FE3"])
        self.assertEqual(len(new_events(stage2, run(stage2, UseAttack(0, 0)), "damage")), 1)  # はたらく効果がなければ止めない
        # 使ったあとに自分のベトベターをベトベトンに進化させ（［かがくへんかガス］）、使ったオムナイトの特殊能力が消えている
        gas = board(kabuto(), bench=(spec(OMANYTE, below=(FOSSIL,)), spec(H.GRIMER)), hand=(H.MUK,), opponent=spec(H.CHANSEY))
        dreamt = power_use(gas, pid(gas, 0, OMANYTE), HD)
        muk = next(u for u in dreamt.players[0].hand if dreamt.cards[u].card_id == H.MUK)
        evolved = run(dreamt, EvolvePokemon(0, muk, pid(dreamt, 0, H.GRIMER)))
        rejected(self, evolved, lambda s: run(s, UseAttack(0, 0), TL), STOP_CODES["PM1"])


class FossilizeTest(unittest.TestCase):
    """4.3 節: ［かせきか］（選んでからコイン。「おもて」で進化カードをすべて手札に）。"""

    def test_choose_then_coin_then_return_every_evolution_card(self):
        state = board(kabuto(damage=10), bench=(spec(H.MACHOP),), opponent=spec(H.CHANSEY))
        me = state.players[0].active
        asked = power_use(state, me.pokemon_id)
        d = asked.decision
        self.assertEqual((d.kind, d.player, d.options), ("select_pokemon", 0, (me.pokemon_id,)))
        self.assertEqual(new_events(state, asked, "coin_flip"), [])  # 選ぶのはコインの前
        heads = resumed(self, asked, lambda s: answer(s, (me.pokemon_id,), HD))
        kinds = [e["kind"] for e in new_events(asked, heads)]
        self.assertEqual(kinds[:4], ["fossilize_target", "coin_flip", "devolve", "knock_out"])  # なにかの化石（HP 10）にダメージ 10 → きぜつ
        self.assertIn(me.card, heads.players[0].hand)
        tails = answer(asked, (me.pokemon_id,), TL)
        self.assertEqual([e["kind"] for e in new_events(asked, tails)][:2], ["fossilize_target", "coin_flip"])
        self.assertEqual(new_events(asked, tails, "devolve"), [])
        audited(self, heads)

    def test_undecided_targets_and_conditions(self):
        mixed = board(kabuto(), bench=(spec(KABUTOPS, below=(FOSSIL, KABUTO_REVIVER)),), opponent=spec(H.CHANSEY))
        asked = power_use(mixed, mixed.players[0].active.pokemon_id)
        stage2 = pid(mixed, 0, KABUTOPS)
        self.assertEqual((asked.decision.context_value("unresolved_choices"), asked.decision.context_value("unresolved_code")), ((stage2,), STOP_CODES["FE3"]))
        with self.assertRaises(UnsupportedError) as raised:
            answer(asked, (stage2,), HD)
        self.assertEqual(raised.exception.code, STOP_CODES["FE3"])
        asleep = board(kabuto(sleep=True), opponent=spec(H.CHANSEY))
        with self.assertRaises(IllegalActionError):
            power_use(asleep, asleep.players[0].active.pokemon_id)

    def test_without_targets_is_fs1(self):
        """FS1: 自分の場に化石から進化したポケモンがいない（カブト自身がいるので、今のカードでは起こらない。単体の確かめ）。"""
        from unittest import mock

        state = board(kabuto(), opponent=spec(H.CHANSEY))
        with mock.patch.object(E, "fossil_evolution", lambda s, p: (E.FOSSIL_EVOLVED_NO, None)):
            rejected(self, state, lambda s: power_use(s, s.players[0].active.pokemon_id), STOP_CODES["FS1"])


class FossilGuideTest(unittest.TestCase):
    """4.4 節: ［かせきのみちびき］（名前がちょうど「なにかの化石」のカードだけ）。"""

    def guide(self, discard, *, hand=(), **extra):
        return board(spec(OMANYTE_GUIDE, (W,), below=(FOSSIL,), **extra), hand=hand, discard=discard, opponent=spec(H.CHANSEY))

    def test_only_the_exact_name(self):
        state = self.guide([FOSSIL, H.PLUSPOWER, KABUTO])
        asked = power_use(state, state.players[0].active.pokemon_id, HD)
        self.assertEqual([asked.cards[u].card_id for u in asked.decision.options], [FOSSIL])
        done = answer(asked, asked.decision.options)
        (got,) = new_events(asked, done, "power_recover_from_discard")
        self.assertEqual((got["card_id"], got["revealed"]), (FOSSIL, False))
        self.assertIsNone(power_use(state, state.players[0].active.pokemon_id, TL).decision)

    def test_stops(self):
        rejected(self, self.guide([H.PLUSPOWER]), lambda s: power_use(s, s.players[0].active.pokemon_id, HD), STOP_CODES["GU1"])
        tower = trainer(self.guide([FOSSIL], hand=(H.POKEMON_TOWER,)), H.POKEMON_TOWER)
        rejected(self, tower, lambda s: power_use(s, s.players[0].active.pokemon_id, HD), STOP_CODES["PW5"])
        with self.assertRaises(IllegalActionError):
            power_use(self.guide([FOSSIL], confusion=True), 1, HD)


# ---------------------------------------------------------------- 5 章: 退却時の反応（［つるでひっぱる］）と相手が決める配分（みだれうち）

def ivysaur(**extra):
    return spec(IVYSAUR, extra.pop("energy", (G, G)), below=(BULBASAUR,), **extra)


def retreat(state):
    me = state.players[0]
    return Retreat(0, tuple(me.active.energy), me.bench[0].card)


class VinePullTest(unittest.TestCase):
    """5.1 節: ［つるでひっぱる］（成功した「にげる」でベンチにもどったとき。入れ替える相手の控えは相手プレイヤーが選ぶ。番ごとに 1 回）。"""

    def state(self, *, opponent_bench=None, **extra):
        bench = (spec(H.CHARMANDER), spec(H.CHANSEY)) if opponent_bench is None else opponent_bench
        return board(ivysaur(**extra), bench=(spec(DIGLETT),), opponent=spec(H.MACHOP), opponent_bench=bench)

    def test_successful_retreat_lets_the_opponent_choose(self):
        state = self.state()
        asked = run(state, retreat(state))
        kinds = [e["kind"] for e in new_events(state, asked)]
        self.assertEqual(kinds[-2:], ["retreat", "pokemon_power"])
        power = new_events(state, asked, "pokemon_power")[0]
        self.assertEqual((power["forced"], power["on_retreat"]), (True, True))
        d = asked.decision
        self.assertEqual((d.kind, d.player, d.resume, d.options), ("select_pokemon", 1, "reaction", tuple(p.pokemon_id for p in state.players[1].bench)))
        chansey = state.players[1].bench[1].pokemon_id
        done = resumed(self, asked, lambda s: answer(s, (chansey,)))
        self.assertEqual(done.players[1].active.pokemon_id, chansey)
        self.assertEqual(done.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id)
        self.assertEqual(len(new_events(state, done, "retreat")), 1)  # にげるの支払い・移動は 1 回だけ（再開でくり返さない）
        self.assertEqual(sorted(done.players[0].discard), sorted(state.players[0].active.energy))
        self.assertEqual(state_to_dict(asked, format_version=28)["decision"]["kind"], "select_pokemon")
        self.assertIn("options", observe(asked, 1)["decision"])
        audited(self, done)

    def test_no_trigger_without_bench_switch_or_failed_retreat(self):
        lonely = self.state(opponent_bench=())
        after = run(lonely, retreat(lonely))
        self.assertEqual((new_events(lonely, after, "pokemon_power"), after.decision), ([], None))
        swap = board(ivysaur(), bench=(spec(DIGLETT),), hand=(H.SWITCH,), opponent=spec(H.MACHOP), opponent_bench=(spec(H.CHANSEY),))
        moved = trainer(swap, H.SWITCH)
        if moved.decision is not None:
            moved = answer(moved, (moved.decision.options[0],))
        self.assertEqual(new_events(swap, moved, "pokemon_power"), [])  # ポケモンいれかえは「にげる」ではない
        confused = self.state(confusion=True)
        failed = run(confused, retreat(confused), TL)
        self.assertEqual(new_events(confused, failed, "pokemon_power"), [])
        self.assertEqual(failed.players[0].active.pokemon_id, confused.players[0].active.pokemon_id)
        succeeded = run(confused, retreat(confused), HD)
        self.assertEqual(succeeded.decision.player, 1)

    def test_timing_question_vl1(self):
        """相手のわるいモココのスタンウェーブ（次の相手の番、受けたポケモンの特殊能力をなくす）を受けたわるいフシギソウが「にげる」: バトル場では消えていて、ベンチにもどると
        持続する効果が消える。どちらの時点で決めるかで結果が変わる（VL1。エネルギーのトラッシュの前）。"""
        state = board(spec(FLAAFFY_DARK, (L, L), below=(MAREEP,)), bench=(spec(H.MACHOP),), opponent=ivysaur(), opponent_bench=(spec(DIGLETT),),
                      turn=TURN + 1, current=1)
        stunned = run(state, UseAttack(1, 1))
        self.assertEqual(stunned.current_player, 0)
        rejected(self, stunned, lambda s: run(s, retreat(s)), STOP_CODES["VL1"])


class RandomStrikeTest(unittest.TestCase):
    """5.2 節: みだれうち（相手プレイヤーが 3 回選ぶ。同じポケモンの数は合算し、1 回のダメージ。弱点・抵抗力なし）。"""

    def test_opponent_allocates_and_damage_is_merged(self):
        state = board(ivysaur(), opponent=spec(DIGLETT), opponent_bench=(spec(H.CHARMANDER),))
        asked = run(state, UseAttack(0, 0))
        d = asked.decision
        self.assertEqual((d.kind, d.player, len(d.options)), ("allocate_damage", 1, 4))
        diglett, charmander = state.players[1].active.card, state.players[1].bench[0].card
        outcomes = {}
        for option in d.options:
            trial = answer(asked, (option,))
            (allocated,) = new_events(asked, trial, "damage_allocated")
            outcomes[allocated["counts"]] = (option, trial)
        self.assertEqual(sorted(outcomes), [(0, 3), (1, 2), (2, 1), (3, 0)])  # 同じポケモンを 2 回以上選べる（3 回の配分）
        option, done = outcomes[(2, 1)]
        # ディグダ（弱点 草）に 2 回 → 20（×2 しない）・ヒトカゲに 1 回 → 10。ポケモンごとに 1 回のダメージ（3 回の 10 にしない）
        self.assertEqual(sorted((e["pokemon"], e["amount"]) for e in new_events(asked, done, "damage")), sorted([(diglett, 20), (charmander, 10)]))
        (allocated,) = new_events(asked, done, "damage_allocated")
        self.assertEqual((allocated["chooser"], allocated["player"], allocated["units"], allocated["per"]), (1, 0, 3, 10))
        resumed(self, asked, lambda s: answer(s, (option,)))
        audited(self, done)


# ---------------------------------------------------------------- 6 章: 残るワザ

class RemainingAttacksTest(unittest.TestCase):
    """6 章: 10まんボルト・きりもみアタック・いやなかふん・たかくとぶ／ドリルダイブ・再利用の型。"""

    def test_thunderbolt_discards_every_energy_card_before_damage(self):
        state = board(spec(RAICHU, (L, L, L, L, W), below=(SURGES_PIKACHU,)), opponent=spec(H.MACHOP))
        after = run(state, UseAttack(0, 1))
        kinds = [e["kind"] for e in new_events(state, after) if e["kind"] in ("discard_energy", "damage")]
        self.assertEqual(kinds, ["discard_energy"] * 5 + ["damage"])
        self.assertEqual(after.players[0].active.energy, [])
        self.assertEqual([e["amount"] for e in new_events(state, after, "damage")], [100])

    def test_thunderbolt_without_energy_cards_has_zero_base_damage(self):
        """「トラッシュできない時、このワザのダメージは 0」: 基本となるダメージを 0 にする（ダメージの要素は残る）。p.321 の 2 段階までに 0 なので計算を終え「ダメージを与えなかった」
        （5 段階のプラスパワーは加わらない）。今のカードでは、エネルギーカードが 1 枚もついていないポケモンがこのワザを使う場面を見つけていないので、ワザのコストだけを空にした
        テスト専用の写しで確かめる（単体のテストだけ）。"""
        extract = copy.deepcopy(read_extract())
        card = next(c for c in extract["cards"] if c["id"] == RAICHU)
        card["pokemon"]["attacks"][1]["cost"] = []
        pool = pool_from_extract(extract, E.DEFAULT_EFFECTS)
        state = H.build_test_state([{"active": spec(RAICHU, (), below=(SURGES_PIKACHU,), trainers=[(H.PLUSPOWER, TURN)]), "deck": [W] * 10, "prizes": 6},
                                    {"active": spec(H.MACHOP), "deck": [W] * 10, "prizes": 6}], turn_number=TURN, pool=pool)
        after = run(state, UseAttack(0, 1))
        (failed,) = new_events(state, after, "discard_energy_failed")
        self.assertEqual((failed["attached"], failed["outcome"]), (0, "zero"))
        (hit,) = new_events(state, after, "damage")
        self.assertEqual((hit["steps"], hit["amount"], hit["stopped_after_step_2"]), ((("1 基本となる計算", 0),), 0, True))
        self.assertEqual(new_events(state, after, "discard_energy"), [])

    def test_spin_attack_self_damage_ignores_weakness_and_resistance(self):
        """プテラは自分のタイプ（闘）に抵抗力 -30 を持つ。自分への 10 は弱点・抵抗力なし（v0.10 の型の既定は変えない）。"""
        state = board(spec(AERODACTYL, (F, F, F), below=(FOSSIL,)), opponent=spec(H.MACHOP))
        after = run(state, UseAttack(0, 1))
        self.assertEqual([(e.get("target"), e["amount"]) for e in new_events(state, after, "damage")], [(None, 40), ("self", 10)])
        self.assertEqual(E.DamageAndSelfDamage(20).implementation_id, "damage_and_self_damage")

    def test_nasty_pollen_poison_and_status_by_two_coins(self):
        state = board(spec(VENUSAUR, (G, G, G), below=(BULBASAUR, IVYSAUR)), opponent=spec(H.MACHOP))
        for coins, second in (((HD, TL), "sleep"), ((TL, HD), "sleep"), ((HD, HD), "confusion"), ((TL, TL), "paralysis")):
            with self.subTest(coins=coins):
                after = run(state, UseAttack(0, 0), *coins)
                self.assertEqual([e["condition"] for e in new_events(state, after, "special_condition")][:2], ["poison", second])
                self.assertEqual(len([e for e in new_events(state, after, "coin_flip") if e.get("source") == "attack"]), 2)

    def test_fly_high_then_drill_dive_and_the_two_locks(self):
        state = board(spec(FEAROW, (G, G, G), below=(SPEAROW,)), bench=(spec(DIGLETT),), hand=(H.SWITCH,), opponent=spec(H.CHANSEY))
        dived = run(state, UseAttack(0, 1))
        self.assertEqual([e["amount"] for e in new_events(state, dived, "damage")], [40])
        effects = sorted(type(x).__name__ for x in dived.players[0].active.persistent_effects)
        self.assertEqual(effects, ["CannotAttackNextOwnTurn", "CannotRetreatNextOwnTurn"])
        mine = run(dived, EndTurn(1))
        rejected(self, mine, lambda s: run(s, UseAttack(0, 0)), "ATTACK_PREVENTED")
        rejected(self, mine, lambda s: run(s, retreat(s)), "RETREAT_PREVENTED")
        self.assertEqual(len(new_events(mine, trainer(mine, H.SWITCH), "play_trainer")), 1)  # ポケモンいれかえは「にげる」ではない
        later = run(run(mine, EndTurn(0)), EndTurn(1))
        self.assertEqual(tuple(later.players[0].active.persistent_effects), ())
        flown = run(run(state, UseAttack(0, 0)), EndTurn(1))
        self.assertEqual([e["amount"] for e in new_events(flown, run(flown, UseAttack(0, 1)), "damage")], [80])  # 2 段階で 80（ラッキーは弱点 闘）
        prevented = board(spec(FEAROW, (G, G, G), below=(SPEAROW,)), opponent={"card": H.CHANSEY, "prevent_damage": TURN - 1})
        guarded = run(prevented, UseAttack(0, 1))
        self.assertEqual(len(guarded.players[0].active.persistent_effects), 2)  # 相手へのダメージが防がれても、自分への効果は与える

    def test_reused_attacks(self):
        kick = board(spec(HITMONTOP, (F, F)), opponent=spec(H.CHANSEY))  # ラッキーは弱点 闘
        self.assertEqual([e["amount"] for e in new_events(kick, run(kick, UseAttack(0, 0), HD, HD, TL), "damage")], [80])  # 「おもて」2 枚 × 20 → ×2
        claw = board(kabuto(), opponent=spec(H.CHANSEY))
        self.assertEqual([e["amount"] for e in new_events(claw, run(claw, UseAttack(0, 0), HD), "damage")], [80])  # 10 + 30 → ×2


# ---------------------------------------------------------------- 7 章・8 章: 保存・再開・先読み

class SaveResumeTest(unittest.TestCase):
    """7 章: 形式 28 のまま。決定をまたぐ続き（2 つの力の発生元・数えた量・コイン）を明示して運び、再開しても 1 回だけ。"""

    def test_anger_and_xxxxx_across_the_shell_armor_decision(self):
        state = unown_board(MISTYS_CLOYSTER)
        a, x = pid(state, 0, UNOWN_A), pid(state, 0, UNOWN_X)
        asked = run(state, UseAttack(0, 0, with_powers=(a, x)), HD, TL)
        d = asked.decision
        self.assertEqual((d.kind, d.player), ("damage_option", 1))
        carried = d.context_value("group_powers")
        self.assertEqual([(entry[0], entry[4]) for entry in carried], [(a, 2), (x, 1)])  # A は数えたカウンター 2 個、X は「おもて」1 枚
        data = state_to_dict(asked, format_version=28)
        self.assertEqual([entry[0] for entry in data["decision"]["context"]["group_powers"]], [a, x])
        done = resumed(self, asked, lambda s: answer(s, (d.options[0],)))
        self.assertEqual(len([e for e in new_events(state, done, "coin_flip") if e.get("source") == "power"]), 2)  # 再開でコインを投げ直さない
        self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [30])  # 10 + 20 + 10 − 10（シェルアーマー）
        audited(self, done)

    def test_turn_effect_source_returned_to_hand_is_not_observed(self):
        """観測の不具合の回帰（正式な対戦の B122 対 F122・F122 対 A122 の seed 1 で見つけた。文書 13 章）: ［げんしのゆめ］を使ったオムナイトが、その番のうちに［かせきか］で手札に
        もどると、番の効果の記録の発生源のカードの uid は、相手・観戦者の観測に書かない（持ち主には見える。カードの id は公開）。"""
        from tests.log_audit import observation_problems

        state = board(kabuto(), bench=(spec(OMANYTE, below=(FOSSIL,)),), opponent=spec(H.CHANSEY))
        omanyte = state.players[0].bench[0]
        dreamt = power_use(state, omanyte.pokemon_id, HD)
        returned = answer(power_use(dreamt, state.players[0].active.pokemon_id), (omanyte.pokemon_id,), HD)
        self.assertIn(omanyte.card, returned.players[0].hand)
        self.assertEqual([(e["kind"], e["card"]) for e in observe(returned, 0)["trainer_effects"]], [("fossil_attack_bonus", omanyte.card)])
        for viewer in (1, None):
            self.assertEqual([(e["card"], e["card_id"]) for e in observe(returned, viewer)["trainer_effects"]], [(None, OMANYTE)])
        self.assertEqual(observation_problems(returned), [])


class PreflightTest(unittest.TestCase):
    """8 章: 宣言の前の先読みで試す結果の数（上限 4,096 は増やさない）。"""

    def test_measured_branches(self):
        from unittest import mock

        from kyuura_engine.resolution import preflight

        branches = []
        original = preflight.explore

        def counting(*args, **kwargs):
            found, tried = original(*args, **kwargs)
            branches.append(tried)
            return found, tried

        def measured(state, command, *coins):
            branches.clear()
            with mock.patch.object(preflight, "explore", counting):
                run(state, command, *coins)
            return list(branches)

        both = unown_board(H.HITMONCHAN)
        a, x = pid(both, 0, UNOWN_A), pid(both, 0, UNOWN_X)
        self.assertEqual(measured(both, UseAttack(0, 0, with_powers=(a, x)), HD, TL), [3])  # ［XXXXX］の「うら」が出るまで（きぜつまでの結果ごと）
        self.assertEqual(measured(both, UseAttack(0, 0, with_power=x), HD, TL), [5])
        self.assertEqual(measured(unown_board(MISTYS_CLOYSTER), UseAttack(0, 0, with_powers=(a, x)), HD, TL), [12])  # ［シェルアーマー］の決定がある
        six = board(ivysaur(), opponent=spec(DIGLETT), opponent_bench=[spec(H.CHANSEY) for _ in range(5)])
        self.assertEqual(measured(six, UseAttack(0, 0)), [56])  # 6 匹に 3 単位の配分（8C3 = 56）
        pollen = board(spec(VENUSAUR, (G, G, G), below=(BULBASAUR, IVYSAUR)), opponent=spec(H.MACHOP))
        self.assertEqual(measured(pollen, UseAttack(0, 0), HD, TL), [2])
        self.assertEqual(preflight.MAX_BRANCHES, 4096)


# ---------------------------------------------------------------- 11 章: ログの監査

class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v122_problems``・``v122_close``）は、エンジンの登録・計算を読まずに、印刷の文面と、ログから組み立てた場・コインで確かめる。正式な開始からの
    対戦（tools/existing_effect_games.py の局。開発用の seed 80〜83。正式な対戦の seed 0〜3 とは別）のログを 1 か所書き換えると、監査が見つける。

    A122 対 C121（seed 82）は、なきごえで 2 段階のあとに 0 になって計算が止まったワザ（stopped_after_step_2）の 6 段階の［ANGER］の記録がないことを、監査が誤って指摘した局
    （文書 13 章。エンジンの処理は正しい）。監査を直したあとの回帰の確かめに使う。"""

    GAMES = ((("U122", "W122"), 80), (("W122", "A122"), 80), (("A122", "C121"), 82), (("B122", "F122"), 80), (("F122", "L122"), 83),
             (("B122", "L122"), 81), (("L122", "B122"), 80), (("L122", "B122"), 81))
    _played: ClassVar[dict] = {}

    @classmethod
    def game(cls, labels, seed):
        from tools import existing_effect_games as games

        if (labels, seed) not in cls._played:
            cls._played[(labels, seed)] = games.play(labels, seed, keep_state=True)
        return cls._played[(labels, seed)]

    def rewritten(self, labels, seed, find, change=None, *, drop=False):
        from tests.log_audit import log_problems

        state = self.game(labels, seed)["state"].clone()
        log = list(state.log)
        index = next(i for i, e in enumerate(log) if find(log, i, e))
        event = dict(log[index])
        if change is not None:
            change(event)
        log[index:index + 1] = [] if drop else [event]
        state.log = tuple(log)
        return log_problems(state)

    def test_the_games_pass_the_audit_and_use_the_new_mechanics(self):
        from tests.log_audit import log_problems

        used = set()
        for labels, seed in self.GAMES:
            result = self.game(labels, seed)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual((result["audit"], log_problems(result["state"])), ({}, []))
            used |= {k for k, v in result["v122"].items() if v}
        self.assertTrue({"undo_returned", "want_recovered", "want_tails", "anger_with_xxxxx", "anger_used_self", "vine_pull_switched", "fossilize_devolved",
                         "primal_dream_bonus_added", "fossil_guide_recovered", "random_strike_targets_2", "thunderbolt_discarded", "spin_attack_self",
                         "drill_dive_locks", "fly_high_set"} <= used)

    def test_anger_stopped_after_step_two_is_not_reported(self):
        from tests.log_audit import log_problems

        state = self.game(("A122", "C121"), 82)["state"]
        stopped = [e for e in state.log if e["kind"] == "damage" and e.get("stopped_after_step_2") and e["turn"] in
                   {x["turn"] for x in state.log if x["kind"] == "group_attack_power_counters" and x["amount"]}]
        self.assertTrue(stopped)
        self.assertEqual(log_problems(state), [])

    def test_xxxxx_stopped_after_step_two_is_not_reported(self):
        """v0.118 の監査（``v118_close``）の誤りの回帰（正式な対戦の C121 対 A122・seed 0 で見つけた。エンジンの処理は正しい。文書 13 章）: なきごえを受けたアンノーンの
        「めざめるパワー」が 2 段階で 0 になって計算を終えると、6 段階の［XXXXX］の追加は記録されない。正式な対戦の局の再生（seed を選び直すためではない）。"""
        from tests.log_audit import log_problems

        result = self.game(("C121", "A122"), 0)
        state = result["state"]
        coins = {x["turn"] for x in state.log if x["kind"] == "group_attack_power_coins" and x["amount"]}
        self.assertTrue([e for e in state.log if e["kind"] == "damage" and e.get("stopped_after_step_2") and e["turn"] in coins])
        self.assertEqual((result["audit"], log_problems(state)), ({}, []))

    def test_audit_finds_anger_counted_on_the_wrong_pokemon(self):
        found = self.rewritten(("A122", "C121"), 82, lambda log, i, e: e["kind"] == "group_attack_power_counters" and e["counters"],
                               lambda e: e.update(counters=e["counters"] + 1, amount=e["amount"] + 10))
        self.assertTrue([p for p in found if "［ANGER］のカウンター" in p])

    def test_audit_finds_undo_without_the_letters(self):
        def without_letters(log, i, e):
            return e["kind"] == "pokemon_power" and e.get("power", "").startswith("UNDO")

        found = self.rewritten(("U122", "W122"), 80, without_letters, lambda e: e.update(turn=e["turn"]))
        self.assertEqual([p for p in found if "ベンチにアンノーン" in p], [])  # 書き換えない局は通る
        from unittest import mock

        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        # エンジンがベンチの文字を確かめなくなると、手順は文字がそろう前に［UNDO］を使い、監査が見つける
        with mock.patch.object(E, "require_bench_letters", lambda *args, **kwargs: None):
            result = games.play(("U122", "W122"), 80, keep_state=True)
        self.assertTrue([p for p in log_problems(result["state"]) if "ベンチにアンノーン" in p])

    def test_audit_finds_want_recovering_a_pokemon(self):
        state = self.game(("W122", "A122"), 80)["state"]
        pokemon_card = next(uid for uid, c in state.cards.items() if state.card_def(uid).category == "pokemon" and c.owner == 0)
        found = self.rewritten(("W122", "A122"), 80, lambda log, i, e: e["kind"] == "power_recover_from_discard", lambda e: e.update(card=pokemon_card))
        self.assertTrue([p for p in found if "トラッシュから手札に加えたカード" in p])

    def test_audit_finds_a_vine_pull_switch_on_the_wrong_side(self):
        found = self.rewritten(("B122", "F122"), 80, lambda log, i, e: e["kind"] == "switch" and str(e.get("power", "")).startswith("PRN-039@"),
                               lambda e: e.update(player=1 - e["player"]))
        self.assertTrue([p for p in found if "［つるでひっぱる］の入れ替え" in p])

    def test_audit_finds_random_strike_chosen_by_the_attacker(self):
        found = self.rewritten(("B122", "L122"), 81, lambda log, i, e: e["kind"] == "damage_allocated" and e.get("effect") == f"{IVYSAUR}#0",
                               lambda e: e.update(chooser=e["player"]))
        self.assertTrue([p for p in found if "の配分" in p])

    def test_audit_finds_a_missing_drill_dive_lock(self):
        found = self.rewritten(("L122", "B122"), 80, lambda log, i, e: e["kind"] == "persistent_effect_added" and e.get("effect") == f"{FEAROW}#1", drop=True)
        self.assertTrue([p for p in found if "次の自分の番のワザとにげるの禁止" in p])

    def test_audit_finds_thunderbolt_keeping_an_energy(self):
        found = self.rewritten(("L122", "B122"), 81, lambda log, i, e: e["kind"] == "discard_energy" and e.get("effect") == f"{RAICHU}#1", drop=True)
        self.assertTrue([p for p in found if "宣言のときについていたエネルギーカードすべて" in p])

    def test_audit_finds_a_primal_dream_without_heads(self):
        found = self.rewritten(("F122", "L122"), 83, lambda log, i, e: e["kind"] == "coin_flip" and e.get("source") == "power" and e["result"] == "heads"
                               and i + 1 < len(log) and log[i + 1].get("effect_kind") == "fossil_attack_bonus", lambda e: e.update(result="tails"))
        self.assertTrue([p for p in found if "［げんしのゆめ］の効果" in p])


class DocumentTest(unittest.TestCase):
    def test_document_records_the_version(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("## 1. 開始点と範囲", "## 3. アンノーン", "## 4. 化石", "## 5. 退却時の反応", "## 10. 停止コード", "## 12. kyuura への報告事項",
                       *STOP_CODES, *STOP_CODES.values(), "0.122.0", "## 13. 検証", "## 14. 残る制限", "lockstep", "単体のテストだけ", "with_powers", "4,096",
                       "CR-UNOWN-DF-PROTECTS-OWN-UNOWN", "外部照合・カード画像・ガイドブックの読み直しをしていません"):
            self.assertIn(needle, text)
        v121 = (ROOT / "docs" / "hand-bench-attack-conditions-v0.121.md").read_text(encoding="utf-8")
        self.assertIn("GN1", v121)
        # README の「今のエンジンの版」と対応状況の題の範囲は版を上げるたびに変わるので、v0.122 の項目があることだけを確かめる
        self.assertRegex((ROOT / "README.md").read_text(encoding="utf-8"),
                         r"\n- v0\.122（(今のエンジンの版。)?`kyuura_engine` の版は 0\.122\.0）: アンノーンの併用・化石の進化履歴・退却時の反応の 13 枚")
        self.assertIn("## v0.122: アンノーンの併用・化石の進化履歴・退却時の反応\n", (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8"))
        self.assertIn("### v0.122: アンノーンの併用・化石の進化履歴・退却時の反応", (ROOT / "docs" / "rules-2000-02-14.md").read_text(encoding="utf-8"))
        self.assertIn("## v0.122: アンノーンの併用・化石の進化履歴・退却時の反応の 13 枚", (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8"))
        self.assertLess(len((ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines()), 200)


if __name__ == "__main__":
    unittest.main()

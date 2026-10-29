"""v0.117（docs/retreat-return-active-powers-v0.117.md）: 場の移動・「にげる」時の反応・条件付きの特殊能力のポケモン 13 枚（ワザ 18・特殊能力 8）。
ヘラクロス（neo1-017）・エイパム（neo1-067）・ニョロトノ（neo2-019）・セレビィ（neo3-036）・オドシシ（neo3-049）・アンノーンC（neo4-057）・アンノーンQ（neo4-059）・ナツメのゴース
（GD6-005）・ブラッキー（PF2-006）・ライコウ（PF3-004）・エンテイ（PF3-005）・スイクン（PF3-006）・ヤミカラス（PRN-001）。

根拠は kyuura データの採用（kyuura ``e519b99`` の data/cards.json の日本語の印刷の文面。オドシシは UQ-NEO-TEXT-BABY-CATEGORIES の事例。ほかの 12 枚を指す LD-・CC-・CR-・UQ-・
エラッタはない）と、既存の規定と読み方の記録（GR-2000-P325-SAME-TIMING・GR-2000-P320-COUNTER-MOVE・GR-2000-P315-EVOLVED-BABY・NB1・T19b・HC3・v0.36 のくもがくれガス・v0.82 の
ヒートフレイム）。英語の欄・現代のルール・後年の裁定（2002 年からのポケボディーの分類）は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合・外部照合はしていない。
盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.117``）。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import re
import unittest
from collections import Counter
from types import MappingProxyType
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS,
    EndTurn,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine import movement as M
from kyuura_engine.cards import EnergyType, load_card_pool, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import DISCARD_TO_DECK, REACTION_ORDER
from kyuura_engine.engine import check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import PUBLIC_EVENTS, observe
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import GROUP_ATTACK_IMMUNITY, QUICKEN_USED, PursuitOnRetreat
from tests import helpers as H
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.log_audit import LATEST_FORMAT
from tests.release_catalog import cards_after, cards_before
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_unown_family_powers_v0_96 import TURN, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "retreat-return-active-powers-v0.117.md"
COMMIT = "e519b99e2adcc6c2cd0998569ae5ee1101de6e89"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, FR, L, PS, G, F = H.WATER, H.FIRE, H.LIGHTNING, H.PSYCHIC, H.GRASS, H.FIGHTING
DARK, DCE = H.DARKNESS_ENERGY_NEO1, H.DOUBLE_COLORLESS_ENERGY
HERACROSS, AIPOM, POLITOED, CELEBI, STANTLER = "neo1-017", "neo1-067", "neo2-019", "neo3-036", "neo3-049"
UNOWN_C, UNOWN_Q, SABRINAS_GASTLY, UMBREON = "neo4-057", "neo4-059", "GD6-005", "PF2-006"
RAIKOU, ENTEI, SUICUNE, MURKROW = "PF3-004", "PF3-005", "PF3-006", "PRN-001"
V0117 = (HERACROSS, AIPOM, POLITOED, CELEBI, STANTLER, UNOWN_C, UNOWN_Q, SABRINAS_GASTLY, UMBREON, RAIKOU, ENTEI, SUICUNE, MURKROW)
LEGENDS = (RAIKOU, ENTEI, SUICUNE)
EEVEE_PF2, POLIWAG, POLIWHIRL, PICHU = "PF2-005", "neo2-013", "neo2-016", "neo1-042"
BELOW = {UMBREON: [EEVEE_PF2], POLITOED: [POLIWAG, POLIWHIRL], POLIWHIRL: [POLIWAG], H.HAUNTER: [H.GASTLY]}
EXPECTED = {
    (HERACROSS, 0): E.FailOnTailsDamage(),
    (AIPOM, 0): E.ReturnSelfToDeckThenCoinDiscardCardToDeck(), (AIPOM, 1): E.CoinFlipDamage(2, 10),
    (POLITOED, 0): E.CoinFlipDamage(2, 40),
    (CELEBI, 0): E.CoinsCountersOnOpponent(3),
    (STANTLER, 0): E.LockOpponentAttackIfBasic(), (STANTLER, 1): E.DamageThenCoinOwnBenchDamage(10),
    (UNOWN_C, 0): E.DAMAGE_ONLY, (UNOWN_Q, 0): E.DAMAGE_ONLY,
    (SABRINAS_GASTLY, 0): E.ParalyzeOnHeads(), (SABRINAS_GASTLY, 1): E.DamageThenReturnSelfAndEnergyToHand(),
    (UMBREON, 0): E.CoinBonusDamage(20), (UMBREON, 1): E.DamageThenPursuitOnRetreat(10),
    (RAIKOU, 0): E.DamageThenCoinBenchDamage(20),
    (ENTEI, 0): E.CoinsDiscardTailsEnergyThenDamage(EnergyType.FIRE, 2),
    (SUICUNE, 0): E.CoinBonusDamageElseForceSwitch(10),
    (MURKROW, 0): E.DAMAGE_ONLY, (MURKROW, 1): E.DamageThenPursuitOnRetreat(10),
}
POWERS = {
    HERACROSS: E.NamedAttackDamageSetWhileLowHp("メガホーン", 120, 20),
    POLITOED: E.AttackDamageBonusWithNamedFieldCount(E.FROG_SONG_NAMES, 3, 40),
    CELEBI: E.ReturnToDeckOnHeadsInsteadOfKnockOut(),
    UNOWN_C: E.CountersOnOpponentRetreatWhileActive(1),
    UNOWN_Q: E.CoinGroupAttackImmunityNextTurn("Q", "QUICKEN"),
    **{card: E.ImmuneToTrainersWhileActive() for card in LEGENDS},
}
NEW_CODES = {
    "UNRESOLVED_RETREAT_REACTION_TIMING": "RR1", "UNRESOLVED_QUICKEN_EFFECT_SUPPRESSED": "QK1", "UNRESOLVED_TIME_TRAVEL_TIMING": "TW1",
    "UNRESOLVED_TIME_TRAVEL_OVERLAP": "TW2", "UNRESOLVED_LEGEND_BODY_TRAINER_TARGET": "LB1", "UNRESOLVED_LEGEND_BODY_GOOP_GAS": "LB2",
    "UNRESOLVED_VANISH_OTHER_ATTACHED": "VH1", "UNRESOLVED_ESP_LEFT_BEFORE_COIN": "ES4",
}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, *, bench=(H.RATTATA,), opponent=None, opponent_bench=(H.RATTATA,), hand=(), opponent_hand=(), deck=None, discard=(), opponent_deck=None,
          opponent_discard=(), current=0, turn=TURN):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": list(deck if deck is not None else [W] * 10), "discard": list(discard), "prizes": 6}
    them = {"active": opponent or mon(H.HITMONCHAN), "bench": list(opponent_bench), "hand": list(opponent_hand),
            "deck": list(opponent_deck if opponent_deck is not None else [W] * 10), "discard": list(opponent_discard), "prizes": 6}
    return build_test_state([me, them], turn_number=turn, current_player=current)


def attack(state, index=0, *coins):
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UseAttack(state.current_player, index))


def answer(state, choices, *coins):
    d = state.decision
    return apply_kernel(with_coin_results(state, *coins) if coins else state, ResolveDecision(d.player, d.id, tuple(choices)))


def same_answers(test, state, choices, *coins):
    """待っている決定のある状態を clone・deepcopy・pickle しても、同じ答え（と同じコインの結果）で同じ結果になる。"""
    expected = answer(state, choices, *coins)
    for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
        test.assertEqual(snap(answer(other, choices, *coins)), snap(expected))
    return expected


def uid(state, card_id, player=0, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def play(state, card_id, *coins, player=None):
    player = state.current_player if player is None else player
    state = with_coin_results(state, *coins) if coins else state
    return apply_kernel(state, PlayTrainer(player, uid(state, card_id, player)))


def retreat(state, *coins, to=0):
    """番のプレイヤーのバトル場のポケモンが、にげるエネルギーぶん、ついている順にトラッシュして、ベンチの ``to`` 番目と入れ替わる。"""
    p = state.players[state.current_player]
    cost = state.card_def(p.active.card).retreat_cost
    state = with_coin_results(state, *coins) if coins else state
    return apply_kernel(state, Retreat(state.current_player, tuple(p.active.energy[:cost]), p.bench[to].card))


def kinds(before, after, *names):
    return [e["kind"] for e in new_events(before, after, *names)]


def pursued(defender=None, *, attacker=MURKROW, bench=(H.RATTATA,), hand=(H.ENERGY_REMOVAL,), extra=(), coins=()):
    """自分（プレイヤー 0）のヤミカラス（悪エネルギー・水）が相手の ``defender`` に「おいうち」を使い、相手の番になった盤面（相手の手札 ``hand``）。

    悪エネルギーの「+10」は対戦ポケモンへのダメージだけなので、そのままでは「にげる」で RR1 になる。``hand`` のエネルギー・リムーブで、相手がその悪エネルギーをはがせる。"""
    energy = (DARK, W) if attacker == MURKROW else (DARK, W, W)
    state = board(mon(attacker, energy + tuple(extra)), opponent=defender or mon(H.HITMONCHAN, (F, F)), opponent_bench=bench, opponent_hand=hand)
    after = attack(state, 1, *coins)
    if after.current_player != 1:
        raise AssertionError("ワザのあとに相手の番になっていない")
    return after


def without_dark(state):
    """相手（番のプレイヤー 1）がエネルギー・リムーブで、ヤミカラスの悪エネルギーをはがした盤面。"""
    played = play(state, H.ENERGY_REMOVAL)
    dark = next(u for u in played.decision.options if played.cards[u].card_id == DARK)
    return answer(played, (dark,))


# ---------------------------------------------------------------- 1. 登録と文面


class RegistrationTest(unittest.TestCase):
    """2 章: 13 枚の 18 ワザ・8 特殊能力の登録・全文・引数、写し・採用の記録・研究の対応表。"""

    def test_attack_registrations_are_exactly_the_expected_types(self):
        pool = load_card_pool()
        for (card, index), effect in EXPECTED.items():
            with self.subTest(card=card, index=index):
                definition = pool.definitions[card]
                self.assertEqual(DEFAULT_EFFECTS.attack_entry(card, index).effect, effect)
                self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, definition.attacks[index], definition.attacks))
                self.assertTrue(definition.supported)
        self.assertEqual({key.card_id for key in DEFAULT_EFFECTS.attack_keys() if key.card_id in V0117}, set(V0117))
        self.assertEqual(sum(1 for key in DEFAULT_EFFECTS.attack_keys() if key.card_id in V0117), 18)

    def test_power_registrations_and_the_shared_legend_body(self):
        pool = load_card_pool()
        for card, effect in POWERS.items():
            definition = pool.definitions[card]
            power = definition.powers[0]
            with self.subTest(card=card):
                entry = DEFAULT_EFFECTS.power_entry(card, power.index)
                self.assertEqual(entry.effect, effect)
                self.assertEqual(entry.text_ja, power.text_ja)
                self.assertEqual(effect.check(power), [])
        self.assertEqual(sum(1 for card in V0117 for power in pool.definitions[card].powers if DEFAULT_EFFECTS.power_entry(card, power.index) is not None), 8)
        shared = {id(DEFAULT_EFFECTS.power_entry(card, 0).effect) for card in LEGENDS}
        self.assertEqual(len(shared), 1)  # 3 枚で同じ実装の値（カードの記録は別）
        self.assertFalse(POWERS[UNOWN_C].blocked_by_status)
        self.assertTrue(POWERS[HERACROSS].blocked_by_status and POWERS[POLITOED].blocked_by_status)

    def test_new_attack_types_are_kernel_programs(self):
        """新しいワザの型 6 つは解決の基盤の要素の並び（``programs.BUILDERS``）で処理し、v0.13 の約束（``resolve``・``resume``）を上書きしない（tests/helpers.py の
        ``ATTACK_TYPES_SINCE_V0_17`` に加えた。v0.13 の止める関数で確かめる型に入れない）。"""
        from kyuura_engine.resolution import v013_checks

        new = (E.LockOpponentAttackIfBasic, E.CoinsCountersOnOpponent, E.DamageThenReturnSelfAndEnergyToHand, E.ReturnSelfToDeckThenCoinDiscardCardToDeck,
               E.CoinsDiscardTailsEnergyThenDamage, E.DamageThenPursuitOnRetreat)
        start = H.ATTACK_TYPES_SINCE_V0_17.index(new[0])
        self.assertEqual(H.ATTACK_TYPES_SINCE_V0_17[start:start + len(new)], new)  # v0.118 から、あとの版の型が続く
        for cls in new:
            with self.subTest(cls=cls.__name__):
                self.assertIn(cls, P.BUILDERS)
                self.assertNotIn(cls, v013_checks.VERIFIED)
                self.assertIs(cls.resolve, E.AttackEffect.resolve)
                self.assertIs(cls.resume, E.AttackEffect.resume)

    def test_play_text_is_the_printed_text(self):
        pool = load_card_pool()
        for card, index in EXPECTED:
            entry = DEFAULT_EFFECTS.attack_entry(card, index)
            text = pool.definitions[card].attacks[index].text_ja
            with self.subTest(card=card, index=index):
                self.assertEqual(entry.text_ja, text)
                self.assertEqual(entry.play_text_ja, text)
                self.assertEqual(entry.source, None if text is None else "kyuura data/cards.json")

    def test_nearby_texts_are_not_accepted(self):
        """名前の近い既存の型に渡すと拒否され、既存の型に加えた書き方は 1 通りだけ（クリスタルウェーブの PF3-006 の全文）。"""
        pool = load_card_pool()
        megaflame = pool.definitions[ENTEI].attacks[0]
        self.assertTrue(E.CoinsDiscardTailsEnergyThenDamage(EnergyType.WATER, 2).check(megaflame))
        self.assertTrue(E.CoinsDiscardTailsEnergyThenDamage(EnergyType.FIRE, 3).check(megaflame))
        self.assertTrue(E.CoinsCountersOnOpponent(2).check(pool.definitions[CELEBI].attacks[0]))
        self.assertTrue(E.DamageThenPursuitOnRetreat(20).check(pool.definitions[MURKROW].attacks[1]))
        self.assertEqual(E.CoinBonusDamageElseForceSwitch(10).check(pool.definitions[SUICUNE].attacks[0]), [])
        self.assertTrue(E.ImmuneToTrainersWhileActive().check(pool.definitions[CELEBI].powers[0]))
        self.assertTrue(E.CoinGroupAttackImmunityNextTurn("C", "CHASE").check(pool.definitions[UNOWN_Q].powers[0]))

    def test_adoption_records_and_research_links(self):
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        for card in V0117:
            record = sources[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), ("kyuura_data", "adopted", COMMIT))
                self.assertEqual(record["kyuura_records"], ["UQ-NEO-TEXT-BABY-CATEGORIES"] if card == STANTLER else [])
                self.assertEqual(record["external_checks"], [])
        for code, ruling in NEW_CODES.items():
            with self.subTest(code=code):
                self.assertEqual(links["stop_codes"][code],
                                 {"engine_rulings": [{"version": "v0.117", "document": "docs/retreat-return-active-powers-v0.117.md", "ruling_id": ruling}],
                                  "kyuura_issue": None, "kyuura_disposition": "not_in_kyuura"})
        case = next(c for c in links["kyuura_cases_without_engine_ruling"]["cases"] if c["card_id"] == STANTLER)
        self.assertEqual(case["engine"], {"stop_codes": ["UNRESOLVED_NEO_TEXT_BASIC_BABY"]})
        printed = set(links["latest_descriptions"]["adopted_printed_text"])
        texts = {f"{card}/attack/{index}" for (card, index), effect in EXPECTED.items() if load_card_pool().definitions[card].attacks[index].text_ja}
        self.assertEqual(len(texts), 15)
        self.assertTrue(texts <= printed)
        self.assertTrue({f"{card}/power/0" for card in POWERS} <= printed)

    def test_the_new_block_does_not_rebind_earlier_names(self):
        """v0.117 の定義（effects.py の v0.117 の節）は、前の版の名前（文面の定数・型・関数）を定義し直さない（開発中に、つれさる・［VANISH］の文面の定数と同じ名前で、もちさる・
        ぱっときえるの文面を定義し、読み込みのあとに前の型の確かめが新しい文面を読んで 2 枚が使えなくなった。名前を変えて直した）。登録表 ``DEFAULT_EFFECTS`` の積み重ねは除く。"""
        import ast

        source = (ROOT / "kyuura_engine" / "effects.py").read_text(encoding="utf-8")
        lines = source.split("\n")
        start = next(i for i, line in enumerate(lines, 1) if line.startswith("# ----") and "v0.117" in line)
        earlier, block = set(), set()
        for node in ast.parse(source).body:
            if isinstance(node, ast.Assign):
                names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names = {node.target.id}
            elif isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                names = {node.name}
            else:
                continue
            (block if node.lineno > start else earlier).update(names)
        self.assertEqual(sorted(block & earlier - {"DEFAULT_EFFECTS"}), [])

    def test_question_codes_are_new_and_distinct(self):
        """新しい問いは既存の問い（SH1・KS1・KS2・VS1・ES1〜ES3）のコードを使わない。研究上の未解決（UNRESOLVED_）とエンジンの未対応（UNSUPPORTED_）を分ける。"""
        for code in NEW_CODES:
            self.assertTrue(code.startswith("UNRESOLVED_"))
        for code in (E.LEGEND_BODY_PENDING_CODE, E.PURSUIT_UNSUPPORTED_CODE):
            self.assertTrue(code.startswith("UNSUPPORTED_"))
        self.assertNotIn(E.RETREAT_REACTION_TIMING_CODE, ("UNRESOLVED_SINKHOLE_TIMING",))
        self.assertTrue({"quicken_suppressed", "time_travel_timing", "time_travel_overlap"} <= set(QUESTIONS))

    def test_text_eras_and_catalog_slices(self):
        self.assertEqual(E.TEXT_ERAS[STANTLER], E.TEXT_NEO)
        extract = read_extract()
        self.assertEqual(set(extract["pool_v0_117"]), set(V0117))
        self.assertEqual(cards_after(extract, "0.116") - cards_after(extract, "0.117"), set(V0117))
        self.assertFalse(set(V0117) & cards_before(extract, "0.117"))


# ---------------------------------------------------------------- 2. ［CHASE］（3 章）


class ChaseTest(unittest.TestCase):
    """3 章: 相手のバトル場のアンノーンC の［CHASE］。コインは持ち主が投げ、「おもて」ならにげたポケモン（ベンチにもどった）にダメージカウンター 1 個（ダメージではない）。"""

    def chased(self, active=None, *, bench=(H.RATTATA,), chaser_bench=()):
        """自分（プレイヤー 0。番のプレイヤー）のバトル場 ``active`` と、相手のバトル場のアンノーンC。"""
        return board(active or mon(H.HITMONCHAN, (F, F)), bench=bench, opponent=mon(UNOWN_C, (PS,)), opponent_bench=chaser_bench)

    def test_heads_puts_one_counter_on_the_retreated_pokemon(self):
        state = self.chased()
        hitmonchan = state.players[0].active
        after = retreat(state, HD)
        coin = new_events(state, after, "coin_flip")
        self.assertEqual([(e["player"], e["source"], e["effect"]) for e in coin], [(1, "power", f"{UNOWN_C}@power0")])
        moved = after.players[0].bench[0]
        self.assertIs(moved.card, hitmonchan.card)
        self.assertEqual(moved.damage, 10)  # 弱点 超の「×2」は当てはめない（ダメージカウンター）
        counters = new_events(state, after, "chase_counters")
        self.assertEqual([(e["counters"], e["amount"], e["target_pokemon_id"]) for e in counters], [(1, 10, hitmonchan.pokemon_id)])
        self.assertEqual((after.current_player, after.phase.value), (0, "main"))
        audited(self, after)

    def test_tails_does_nothing(self):
        state = self.chased()
        after = retreat(state, TL)
        self.assertEqual(kinds(state, after, "chase_check", "chase_counters"), ["chase_check"])
        self.assertEqual(after.players[0].bench[0].damage, 0)
        audited(self, after)

    def test_counters_ignore_damage_reducers(self):
        """ディフェンダー（受けるワザのダメージ -20）がついていても、ダメージカウンターはそのまま 1 個。"""
        state = self.chased(mon(H.HITMONCHAN, (F, F), trainers=[(H.DEFENDER, TURN + 1)]))
        after = retreat(state, HD)
        self.assertEqual(after.players[0].bench[0].damage, 10)

    def test_counters_can_knock_out_the_benched_pokemon_and_the_turn_continues(self):
        state = self.chased(mon(H.HITMONCHAN, (F, F), damage=60))
        knocked = retreat(state, HD)
        self.assertEqual(kinds(state, knocked, "chase_counters", "knock_out"), ["chase_counters", "knock_out"])
        self.assertEqual((knocked.decision.kind, knocked.decision.player), ("take_prize", 1))  # サイドを取るのはアンノーンC の持ち主
        after = answer(knocked, (0,))
        self.assertEqual(len(after.players[1].prizes), 5)
        self.assertEqual((after.current_player, after.phase.value, after.decision), (0, "main", None))
        audited(self, after)

    def test_confused_retreat_stops_before_the_cost(self):
        """こんらんの「にげる」は、コインの「うら」で失敗した「にげる」にも当たるかが決まらない（RR1）。エネルギーのトラッシュ・コインの前に止める。"""
        state = self.chased(mon(H.HITMONCHAN, (F, F), confusion=True))
        p = state.players[0]
        rejects(self, state, Retreat(0, tuple(p.active.energy[:2]), p.bench[0].card), E.RETREAT_REACTION_TIMING_CODE)

    def test_only_a_declared_retreat_from_the_opponent_side(self):
        """効果による入れ替え（ポケモンいれかえ）・ベンチのアンノーンC・自分の場のアンノーンC では、はたらかない。"""
        switched =board(mon(H.HITMONCHAN, (F, F)), opponent=mon(UNOWN_C, (PS,)), hand=(H.SWITCH,))
        after = play(switched, H.SWITCH)
        if after.decision is not None:
            after = answer(after, (after.decision.options[0],))
        self.assertEqual(kinds(switched, after, "chase_check"), [])
        benched = board(mon(H.HITMONCHAN, (F, F)), opponent=mon(H.RATTATA), opponent_bench=(mon(UNOWN_C, (PS,)),))
        self.assertEqual(kinds(benched, retreat(benched), "chase_check"), [])
        own = board(mon(UNOWN_C, (PS,)), bench=(H.RATTATA,))
        self.assertEqual(kinds(own, retreat(own), "chase_check"), [])

    def test_suppressed_by_muk(self):
        state = self.chased(chaser_bench=(mon(H.MUK, evolved_from=[H.GRIMER]),))
        self.assertEqual(kinds(state, retreat(state), "chase_check"), [])


# ---------------------------------------------------------------- 3. おいうち（3 章・4 章）


class PursuitTest(unittest.TestCase):
    """3 章・4 章: 「おいうち」の持続する効果。次の相手の番に、受けた相手が「にげる」と、入れ替えのあと（ベンチにもどったポケモン）に、弱点・抵抗力に関係なくワザの分類の 10 ダメージ。"""

    def test_the_attack_gives_the_effect(self):
        after = pursued()
        defender = after.players[1].active
        effects = [e for e in defender.persistent_effects if isinstance(e, PursuitOnRetreat)]
        self.assertEqual([(e.amount, e.attack, e.created_turn, e.active_turn) for e in effects], [(10, f"{MURKROW}#1", TURN, TURN + 1)])
        self.assertEqual(defender.damage, 30)  # 20 と悪エネルギーの +10
        audited(self, after)

    def test_dark_energy_makes_the_place_matter(self):
        """悪エネルギーの「+10」は対戦ポケモンへのダメージだけ。入れ替えの前（バトル場）なら 20、後（ベンチ）なら 10 で、どちらで受けるか決まらない（RR1）。"""
        state = pursued()
        p = state.players[1]
        rejects(self, state, Retreat(1, tuple(p.active.energy[:2]), p.bench[0].card), E.RETREAT_REACTION_TIMING_CODE)

    def test_damage_after_the_switch_without_weakness(self):
        state = without_dark(pursued(mon(H.HITMONCHAN, (F, F))))
        hitmonchan = state.players[1].active
        after = retreat(state)
        events = new_events(state, after, "pursuit_damage")
        self.assertEqual([(e["amount"], e["target_pokemon_id"], e["attack"]) for e in events], [(10, hitmonchan.pokemon_id, f"{MURKROW}#1")])
        self.assertEqual(after.players[1].bench[0].damage, 40)
        self.assertFalse([e for e in after.players[1].bench[0].persistent_effects if isinstance(e, PursuitOnRetreat)])
        self.assertEqual((after.current_player, after.phase.value), (1, "main"))
        audited(self, after)

    def test_damage_knocks_out_the_benched_pokemon_then_the_turn_continues(self):
        state = without_dark(pursued(mon(H.HITMONCHAN, (F, F), damage=30)))
        knocked = retreat(state)
        self.assertEqual(kinds(state, knocked, "pursuit_damage", "knock_out"), ["pursuit_damage", "knock_out"])
        self.assertEqual((knocked.decision.kind, knocked.decision.player), ("take_prize", 0))
        after = answer(knocked, (0,))
        self.assertEqual(len(after.players[0].prizes), 5)
        self.assertEqual((after.current_player, after.phase.value), (1, "main"))
        audited(self, after)

    def test_the_effect_expires_and_is_removed_by_a_switch(self):
        state = pursued()
        ended = apply_kernel(state, EndTurn(1))
        removed = new_events(state, ended, "persistent_effect_removed")
        self.assertEqual([(e["persistent_effect"], e["reason"]) for e in removed], [("pursuit_on_retreat", "expired")])
        switched = board(mon(MURKROW, (DARK, W)), opponent=mon(H.HITMONCHAN, (F, F)), opponent_hand=(H.SWITCH,))
        switched = attack(switched, 1)
        after = play(switched, H.SWITCH)
        if after.decision is not None:
            after = answer(after, (after.decision.options[0],))
        self.assertEqual([(e["persistent_effect"], e["reason"]) for e in new_events(switched, after, "persistent_effect_removed")], [("pursuit_on_retreat", "switch")])
        self.assertEqual(kinds(after, retreat(after), "pursuit_damage", "pursuit_skipped"), [])

    def test_evaded_attack_gives_no_effect(self):
        """「とうめい」の「おもて」はワザを受けない（ダメージも効果もない）。"""
        evaded = pursued(mon(H.HAUNTER, (PS,)), coins=(HD,))
        self.assertFalse([e for e in evaded.players[1].active.persistent_effects if isinstance(e, PursuitOnRetreat)])

    def test_coin_replacing_receivers_are_unsupported(self):
        """受けるときにコインを投げる「とうめい」（REPLACE）は「にげる」の中では扱えない（エンジンの未対応）。にげる前に止める。"""
        state = without_dark(pursued(mon(H.HAUNTER, (PS,)), coins=(TL,)))
        p = state.players[1]
        rejects(self, state, Retreat(1, (), p.bench[0].card), E.PURSUIT_UNSUPPORTED_CODE)

    def test_a_reduction_that_is_the_same_on_both_spots_is_used(self):
        """ディフェンダー（受けるワザのダメージ -20。場所の条件なし）は入れ替えの前と後で同じなので止めず、10 ダメージは 0 になる（ワザの分類のダメージ）。"""
        state = without_dark(pursued(mon(H.HITMONCHAN, (F, F)), hand=(H.ENERGY_REMOVAL, H.DEFENDER)))
        defended = play(state, H.DEFENDER)
        state = answer(defended, (state.players[1].active.pokemon_id,))
        after = retreat(state)
        self.assertEqual([e["amount"] for e in new_events(state, after, "pursuit_damage")], [0])
        self.assertEqual(after.players[1].bench[0].damage, 30)

    def test_the_effect_is_saved_and_restored(self):
        """持続する効果の量とワザは保存の形式 26 に書かれ、clone・deepcopy・pickle しても「にげる」の結果は同じ。"""
        state = without_dark(pursued())
        written = state_to_dict(state, format_version=26)
        effects = [e for e in written["players"][1]["active"]["persistent_effects"] if e["effect"] == "pursuit_on_retreat"]
        self.assertEqual([(e["amount"], e["attack"]) for e in effects], [(10, f"{MURKROW}#1")])
        expected = snap(retreat(state))
        for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(snap(retreat(other)), expected)


class ReactionOrderTest(unittest.TestCase):
    """4 章: 「にげる」の事実への反応（［CHASE］・おいうち・相手の［おとしあな］）は同じ時点の反応（GR-2000-P325-SAME-TIMING）。番のプレイヤー（にげたプレイヤー）が順番を決める。"""

    def ordered(self):
        """相手（プレイヤー 0）のバトル場のアンノーンC（突風で出した）と、ベンチのヤミカラスが与えたおいうちの効果を受けている、番のプレイヤー 1 のエビワラー。"""
        state = board(mon(MURKROW, (DARK, W)), bench=(mon(UNOWN_C, (PS,)),), opponent=mon(H.HITMONCHAN, (F, F)), opponent_hand=(H.ENERGY_REMOVAL, H.GUST))
        state = without_dark(attack(state, 1))
        gusted = play(state, H.GUST)
        return answer(gusted, (gusted.decision.options[0],))

    def test_the_turn_player_orders_and_both_orders_are_kept(self):
        """待つ状態は clone・deepcopy・pickle で同じ答えに同じ結果。どちらの順番でも 10 ダメージと 1 個のダメージカウンター。"""
        state = self.ordered()
        self.assertEqual(state.cards[state.players[0].active.card].card_id, UNOWN_C)
        p = state.players[1]
        asked = apply_kernel(state, Retreat(1, tuple(p.active.energy[:2]), p.bench[0].card))
        d = asked.decision
        self.assertEqual((d.kind, d.player), (REACTION_ORDER, 1))
        order = [r[0] for r in d.context_value("reaction")[2]]
        self.assertEqual(sorted(order), sorted([M.CHASE, M.PURSUIT]))
        for choice in d.options:
            with self.subTest(choice=choice):
                after = same_answers(self, asked, (choice,), HD)
                self.assertEqual(after.players[1].bench[0].damage, 30 + 20)  # おいうちの 30 に、10 のダメージと 1 個のダメージカウンター
                self.assertEqual((after.current_player, after.phase.value), (1, "main"))
                audited(self, after)

    def test_sinkhole_joins_the_same_stage(self):
        """相手の［おとしあな］（わるいダグトリオ）と［CHASE］も同じ時点の反応。順番の決定に両方がある。"""
        state = board(mon(H.HITMONCHAN, (F, F)), opponent=mon(UNOWN_C, (PS,)), opponent_bench=(mon(H.DARK_DUGTRIO, evolved_from=[H.DIGLETT]),))
        asked = retreat(state)
        d = asked.decision
        self.assertEqual((d.kind, d.player), (REACTION_ORDER, 0))
        self.assertEqual(sorted(r[0] for r in d.context_value("reaction")[2]), sorted([M.CHASE, "sinkhole"]))
        after = same_answers(self, asked, (d.options[0],), HD, TL)
        self.assertEqual(sorted(kinds(asked, after, "chase_check", "sinkhole_check")), ["chase_check", "sinkhole_check"])
        audited(self, after)


# ---------------------------------------------------------------- 4. ［でんせつのからだ］（5 章）


class LegendBodyTest(unittest.TestCase):
    """5 章: ライコウ・エンテイ・スイクンの［でんせつのからだ］。バトル場にいるかぎり「トレーナーカード」（スタジアム以外）の効果を受けず、ついているトレーナーはコマンドの終わりにトラッシュ。"""

    def test_a_trainer_whose_effect_reaches_the_immune_pokemon_stops(self):
        """突風（相手のバトル場の効果を受けないポケモンを入れ替える）・ポケモンいれかえ・プラスパワー・なんでもなおし（自分のバトル場）は LB1。状態・乱数・ログはもどる。"""
        for card in LEGENDS:
            with self.subTest(card=card):
                gust = board(mon(H.HITMONCHAN, (F,)), opponent=mon(card), hand=(H.GUST,))
                rejects(self, gust, lambda s: PlayTrainer(0, uid(s, H.GUST)), E.LEGEND_BODY_TARGET_CODE)
        for trainer, extra in ((H.SWITCH, {}), (H.PLUSPOWER, {}), (H.FULL_HEAL, {"confusion": True})):
            with self.subTest(trainer=trainer):
                state = board(mon(RAIKOU, (L,), **extra), hand=(trainer,))
                rejects(self, state, lambda s, t=trainer: PlayTrainer(0, uid(s, t)), E.LEGEND_BODY_TARGET_CODE)

    def test_on_the_bench_the_power_does_not_work(self):
        state = board(mon(H.HITMONCHAN, (F,)), opponent=mon(H.RATTATA), opponent_bench=(mon(RAIKOU, (L,)),), hand=(H.GUST,))
        played = play(state, H.GUST)
        after = answer(played, (played.decision.options[0],))
        self.assertEqual(after.cards[after.players[1].active.card].card_id, RAIKOU)
        audited(self, after)

    def test_suppressed_by_muk_the_trainer_works(self):
        state = board(mon(H.HITMONCHAN, (F,)), bench=(mon(H.MUK, evolved_from=[H.GRIMER]),), opponent=mon(RAIKOU, (L,)), hand=(H.GUST,))
        played = play(state, H.GUST)
        after = answer(played, (played.decision.options[0],)) if played.decision else played
        self.assertNotEqual(after.cards[after.players[1].active.card].card_id, RAIKOU)

    def test_choices_on_the_immune_pokemon_are_stopped_choices(self):
        """きずぐすり・エネルギー・リムーブの決定では、効果を受けないポケモン・そのカードは選べるが選ぶと止める（LB1）。ほかを選べば今までどおり。"""
        state = board(mon(RAIKOU, (L,), damage=20), bench=(mon(H.RATTATA, damage=10),), hand=(H.POTION,))
        asked = play(state, H.POTION)
        raikou, rattata = state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id
        d = asked.decision
        self.assertEqual((d.options, d.context_value("unresolved_choices", ())), ((raikou, rattata), (raikou,)))
        rejects(self, asked, ResolveDecision(0, d.id, (raikou,)), E.LEGEND_BODY_TARGET_CODE)
        healed = answer(asked, (rattata,))
        self.assertEqual(healed.players[0].bench[0].damage, 0)
        audited(self, healed)
        removal = board(mon(H.HITMONCHAN, (F,)), opponent=mon(SUICUNE, (W,)), opponent_bench=(mon(H.RATTATA, (W,)),), hand=(H.ENERGY_REMOVAL,))
        asked = play(removal, H.ENERGY_REMOVAL)
        immune_energy = removal.players[1].active.energy[0]
        self.assertEqual(asked.decision.context_value("unresolved_choices", ()), (immune_energy,))
        rejects(self, asked, ResolveDecision(0, asked.decision.id, (immune_energy,)), E.LEGEND_BODY_TARGET_CODE)

    def test_no_decision_is_left_when_every_choice_stops(self):
        """選べるものがすべて止める選択（ダメージを受けているのが効果を受けないポケモンだけのきずぐすり・エネルギーがついているのがそのポケモンだけのエネルギー・リムーブ）なら、
        答えのない決定を残さず、使う前に LB1 で止める（状態・乱数・ログはもどる）。"""
        potion = board(mon(RAIKOU, (L,), damage=20), bench=(H.RATTATA,), hand=(H.POTION,))
        rejects(self, potion, lambda s: PlayTrainer(0, uid(s, H.POTION)), E.LEGEND_BODY_TARGET_CODE)
        removal = board(mon(H.HITMONCHAN, (F,)), opponent=mon(RAIKOU, (L,)), hand=(H.ENERGY_REMOVAL,))
        rejects(self, removal, lambda s: PlayTrainer(0, uid(s, H.ENERGY_REMOVAL)), E.LEGEND_BODY_TARGET_CODE)

    def test_effects_on_several_pokemon_skip_only_the_immune_one(self):
        """ポケモンセンター: 効果を受けないバトル場のポケモンは回復せず（ログ trainer_effect_blocked。公開）、ベンチは今までどおり回復してエネルギーをトラッシュする。"""
        state = board(mon(ENTEI, (FR,), damage=20), bench=(mon(H.RATTATA, (W,), damage=10),), hand=(H.POKEMON_CENTER,))
        after = play(state, H.POKEMON_CENTER)
        self.assertEqual(kinds(state, after, "trainer_effect_blocked", "remove_damage_counters", "trainer_discard_energy"),
                         ["trainer_effect_blocked", "remove_damage_counters", "trainer_discard_energy"])
        self.assertEqual((after.players[0].active.damage, len(after.players[0].active.energy)), (20, 1))
        self.assertEqual((after.players[0].bench[0].damage, after.players[0].bench[0].energy), (0, []))
        audited(self, after)

    def test_attached_trainers_are_discarded_when_it_becomes_active(self):
        """ベンチでついたディフェンダーは、「にげる」でバトル場に出たコマンドの終わりにトラッシュする（ログ legend_body_discard・discard_attached_trainer。理由 legend_body）。"""
        state = board(mon(H.HITMONCHAN, (F, F)), bench=(mon(RAIKOU, trainers=[(H.DEFENDER, TURN + 1)]),))
        defender = state.players[0].bench[0].trainers[0].card
        after = retreat(state)
        self.assertEqual(kinds(state, after, "legend_body_discard", "discard_attached_trainer"), ["legend_body_discard", "discard_attached_trainer"])
        self.assertEqual([e["reason"] for e in new_events(state, after, "discard_attached_trainer")], ["legend_body"])
        self.assertEqual(after.players[0].active.trainers, [])
        self.assertIn(defender, after.players[0].discard)
        audited(self, after)

    def test_goop_gas_stops_with_lb2(self):
        state = board(mon(H.HITMONCHAN, (F,)), opponent=mon(RAIKOU, (L,)), hand=(H.GOOP_GAS_ATTACK,))
        rejects(self, state, lambda s: PlayTrainer(0, uid(s, H.GOOP_GAS_ATTACK)), E.LEGEND_BODY_GOOP_GAS_CODE)

    def test_a_switch_that_can_only_bring_out_a_legend_under_goop_gas_is_refused(self):
        """相手のまきちらせ!ベトベトガスの効果のあいだに、控えが［でんせつのからだ］のポケモンだけでポケモンいれかえを使うと、どの答えでもバトル場に出たポケモンが LB2 になる。
        答えのない決定を残さず、使う前に止める（v0.117 の正式な対戦の 1 回目の L117 対 Z59 の seed 2 で、決定を受け付けてから答えがなかった。直した）。ガスがなければ今までどおり。"""
        state = board(mon(H.RATTATA), bench=(mon(RAIKOU),), hand=(H.SWITCH,), opponent=mon(H.HITMONCHAN), opponent_hand=(H.GOOP_GAS_ATTACK,), current=1, turn=TURN - 1)
        gassed = apply_kernel(play(state, H.GOOP_GAS_ATTACK), EndTurn(1))
        rejects(self, gassed, lambda s: PlayTrainer(0, uid(s, H.SWITCH)), E.LEGEND_BODY_GOOP_GAS_CODE)
        plain = board(mon(H.RATTATA), bench=(mon(RAIKOU),), hand=(H.SWITCH,))
        asked = play(plain, H.SWITCH)
        after = answer(asked, (asked.decision.options[0],)) if asked.decision else asked
        self.assertEqual(after.cards[after.players[0].active.card].card_id, RAIKOU)

    def test_player_level_trainers_and_stadiums_are_outside(self):
        """マサキ（引く）・スタジアムは止めない。スタジアムカードは範囲の外（``trainer_card_effect``）。"""
        state = board(mon(RAIKOU, (L,)), hand=(H.BILL, H.POKEMON_TOWER))
        drawn = play(state, H.BILL)
        self.assertEqual(len(drawn.players[0].hand), len(state.players[0].hand) - 1 + 2)
        placed = play(drawn, H.POKEMON_TOWER)
        self.assertIsNotNone(placed.stadium)
        self.assertFalse(E.trainer_card_effect(placed, placed.stadium.card))
        self.assertTrue(E.trainer_card_effect(state, uid(state, H.BILL)))


# ---------------------------------------------------------------- 5. ［ときわたり］（7 章）


class TimeTravelTest(unittest.TestCase):
    """7 章: セレビィの［ときわたり］。相手のワザのダメージで残りHPがなくなったとき、持ち主のコインの「おもて」で、きぜつせず山札にもどる。"""

    def hit(self, *coins, damage=30, index=1, **extra):
        state = board(mon(H.HITMONCHAN, (F, F, F)), opponent=mon(CELEBI, (PS,), damage=damage, **extra))
        return state, attack(state, index, *coins)

    def test_heads_returns_to_the_deck_without_a_knock_out(self):
        state, after = self.hit(HD)
        celebi = state.players[1].active
        coin = new_events(state, after, "coin_flip")
        self.assertEqual([(e["player"], e["source"]) for e in coin], [(1, "power")])
        self.assertEqual(kinds(state, after, "time_travel", "return_in_play_to_deck", "shuffle", "knock_out"), ["time_travel", "return_in_play_to_deck", "shuffle"])
        self.assertTrue({celebi.card, *celebi.energy} <= set(after.players[1].deck))
        self.assertEqual(len(after.players[0].prizes), 6)  # サイドは取られない
        self.assertEqual((after.decision.kind, after.decision.player), ("promote_active", 1))
        audited(self, after)

    def test_tails_knocks_out_normally(self):
        state, after = self.hit(TL)
        self.assertEqual(kinds(state, after, "time_travel", "knock_out"), ["time_travel", "knock_out"])
        self.assertEqual(after.decision.kind, "take_prize")

    def test_no_coin_without_lethal_damage_or_with_a_condition_at_damage(self):
        state, after = self.hit(HD, damage=0)
        self.assertEqual(kinds(state, after, "time_travel"), [])
        state, after = self.hit(HD, sleep=True)
        self.assertEqual(kinds(state, after, "time_travel", "knock_out"), ["knock_out"])

    def test_counters_are_not_damage(self):
        state = board(mon(CELEBI, (PS,)), opponent=mon(CELEBI, (PS,), damage=20))
        after = attack(state, 0, HD, HD, HD)
        self.assertEqual(kinds(state, after, "place_damage_counters", "time_travel", "knock_out"), ["place_damage_counters", "knock_out"])

    def test_works_on_the_bench(self):
        """ライコウのライトニングスパークの控えへの 20 で HP 以上になった控えのセレビィにもはたらく（場所はバトル場に限らない）。"""
        state = board(mon(RAIKOU, (L, L, L)), opponent=mon(H.RATTATA), opponent_bench=(mon(CELEBI, (PS,), damage=30),))
        asked = attack(state, 0, HD)
        after = answer(asked, (asked.decision.options[0],), HD)
        self.assertEqual(kinds(asked, after, "time_travel", "return_in_play_to_deck"), ["time_travel", "return_in_play_to_deck"])
        self.assertFalse(after.players[1].bench)

    def test_later_parts_of_the_same_attack_stop_with_tw1(self):
        """クリスタルウェーブの「うら」（ダメージのあとに相手を入れ替える）は、山札にもどる時点で結果が変わる（TW1）。宣言の前に止める。"""
        state = board(mon(SUICUNE, (W, W, W)), opponent=mon(CELEBI, (PS,), damage=20))
        rejects(self, with_coin_results(state, TL), UseAttack(0, 0), E.TIME_TRAVEL_TIMING_CODE)

    def test_overlap_with_focus_band_stops_with_tw2(self):
        state = board(mon(H.HITMONCHAN, (F, F, F)), opponent=mon(CELEBI, (PS,), damage=30, trainers=[("neo1-088", None)]))
        rejects(self, with_coin_results(state, HD, HD), UseAttack(0, 1), E.TIME_TRAVEL_OVERLAP_CODE)


# ---------------------------------------------------------------- 6. もちさる・ぱっときえる（7 章）


class TakeAwayTest(unittest.TestCase):
    """7 章: エイパムの「もちさる」。自分とついているカードを山札にもどしたあとも、コイン・トラッシュから 1 枚・山札を切ることを続ける。"""

    def test_heads_returns_one_card_from_the_discard_then_shuffles(self):
        state = board(mon(AIPOM, (W,)), discard=(G, FR))
        asked = attack(state, 0, HD)
        d = asked.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (DISCARD_TO_DECK, 0, tuple(state.players[0].discard), 1, 1))
        self.assertIsNone(asked.players[0].active)
        chosen = state.players[0].discard[1]
        after = same_answers(self, asked, (chosen,))
        self.assertIn(chosen, after.players[0].deck)
        self.assertEqual(kinds(asked, after, "shuffle"), ["shuffle"])
        self.assertEqual(after.decision.kind, "promote_active")
        audited(self, after)

    def test_tails_or_an_empty_discard_shuffles_without_a_choice(self):
        for coins, discard in (((TL,), (G,)), ((HD,), ())):
            with self.subTest(coins=coins, discard=discard):
                state = board(mon(AIPOM, (W,)), discard=discard)
                after = attack(state, 0, *coins)
                self.assertEqual(kinds(state, after, "return_in_play_to_deck", "coin_flip", "shuffle"), ["return_in_play_to_deck", "coin_flip", "shuffle"])
                self.assertEqual(after.decision.kind, "promote_active")

    def test_esp_leaving_before_the_coin_stops_with_es4(self):
        """ナツメのESPがついたポケモンがもちさるを使う（今の札の組では［サイコリンク］で「超」のワザしか使えないので、起こりうるのは別のワザを借りる経路）。ESPが場にない
        あとのコインのやり直しは決まらない（ES4）。宣言の前に止める。"""
        state = board(mon(AIPOM, (W,)))
        with mock.patch.object(E, "esp_cards", lambda s, pokemon: (999,)):
            rejects(self, state, UseAttack(0, 0), E.ESP_LEFT_BEFORE_COIN_CODE)


class VanishTest(unittest.TestCase):
    """7 章: ナツメのゴースの「ぱっときえる」。ダメージのあと自分とエネルギーカードを手札にもどす（きぜつではない）。ほかのカードがついていれば VH1。"""

    def test_damage_then_the_pokemon_and_energy_go_to_the_hand(self):
        state = board(mon(SABRINAS_GASTLY, (PS, PS)))
        gastly = state.players[0].active
        after = attack(state, 1)
        self.assertEqual(kinds(state, after, "damage", "return_in_play_to_hand"), ["damage", "return_in_play_to_hand"])
        self.assertTrue({gastly.card, *gastly.energy} <= set(after.players[0].hand))
        self.assertEqual(after.decision.kind, "promote_active")
        audited(self, after)

    def test_an_attached_trainer_stops_with_vh1(self):
        state = board(mon(SABRINAS_GASTLY, (PS, PS), trainers=[(H.PLUSPOWER, TURN)]))
        rejects(self, state, UseAttack(0, 1), E.VANISH_OTHER_ATTACHED_CODE)


# ---------------------------------------------------------------- 7. ［QUICKEN］（6 章）


class QuickenTest(unittest.TestCase):
    """6 章: アンノーンQ の［QUICKEN］。コインの前に使った記録、「おもて」なら次の相手の番に自分の場の「アンノーン」全員がワザのダメージ・効果を受けない。"""

    def used(self, *coins, bench=(UNOWN_C, UNOWN_Q, H.RATTATA), active=UNOWN_Q, opponent=None, opponent_bench=(H.RATTATA,), opponent_hand=()):
        state = board(mon(active, (PS,)), bench=bench, opponent=opponent or mon(H.HITMONCHAN, (F,)), opponent_bench=opponent_bench, opponent_hand=opponent_hand)
        q = next(p for p in state.players[0].in_play() if state.cards[p.card].card_id == UNOWN_Q)
        return state, apply_kernel(with_coin_results(state, *coins), UsePokemonPower(0, q.pokemon_id, 0))

    def test_heads_protects_every_unown_on_the_next_turn(self):
        state, after = self.used(HD)
        records = [(r.kind, r.created_turn, r.expires_turn) for r in after.trainer_effects]
        self.assertEqual(records, [(QUICKEN_USED, TURN, TURN), (GROUP_ATTACK_IMMUNITY, TURN, TURN + 1)])
        self.assertEqual(new_events(state, after)[1]["kind"], "trainer_effect_added")  # コインの前に使った記録
        nxt = apply_kernel(after, EndTurn(0))
        hit = attack(nxt, 0)  # エビワラーのジャブ（20）
        self.assertEqual(hit.players[0].active.damage, 0)
        self.assertEqual([e["persistent_effect"] for e in new_events(nxt, hit, "damage_prevented")], [GROUP_ATTACK_IMMUNITY])
        self.assertEqual([e["effect_kind"] for e in new_events(nxt, hit, "trainer_effect_removed")], [GROUP_ATTACK_IMMUNITY])  # ワザで番が終わり、消える
        self.assertEqual(hit.trainer_effects, ())
        audited(self, hit)

    def test_an_effect_coin_on_a_protected_unown_is_the_existing_hc3(self):
        """「おもて」でマヒにする効果だけを決めるコイン（ナツメのゴースのしたでなめる）を、ワザを受けない状態の相手に投げるかは既存の HC3（新しい問いにしない）。"""
        _, after = self.used(HD, opponent=mon(SABRINAS_GASTLY, (PS,)))
        rejects(self, with_coin_results(apply_kernel(after, EndTurn(0)), HD), UseAttack(1, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")

    def test_tails_only_records_the_use(self):
        _, after = self.used(TL)
        self.assertEqual([r.kind for r in after.trainer_effects], [QUICKEN_USED])
        nxt = apply_kernel(after, EndTurn(0))
        self.assertEqual(attack(nxt, 0).players[0].active.damage, 20)

    def test_other_pokemon_are_not_protected(self):
        """名前のグループが「アンノーン」でないポケモン（ラプラス）は受ける。"""
        _, after = self.used(HD, active=H.LAPRAS, bench=(mon(UNOWN_Q, (PS,)),))
        hit = attack(apply_kernel(after, EndTurn(0)), 0)
        self.assertEqual(hit.players[0].active.damage, 20)

    def test_once_per_turn_across_the_two_unown_q(self):
        _, after = self.used(TL)
        first = next(p for p in after.players[0].in_play() if after.cards[p.card].card_id == UNOWN_Q)
        other = next(p for p in after.players[0].in_play() if after.cards[p.card].card_id == UNOWN_Q and p is not first)
        rejects(self, after, UsePokemonPower(0, other.pokemon_id, 0), "POWER_ALREADY_USED", error=IllegalActionError)
        with self.assertRaises(IllegalActionError):
            apply_kernel(after, UsePokemonPower(0, first.pokemon_id, 0))

    def test_suppressed_source_stops_with_qk1(self):
        """効果がはたらく番に、使ったアンノーンQ の特殊能力が消えている（相手がベトベターをベトベトンに進化させた）と、続くかは決まらない（QK1）。"""
        from kyuura_engine import EvolvePokemon

        _, after = self.used(HD, opponent_bench=(H.GRIMER,), opponent_hand=(H.MUK,))
        nxt = apply_kernel(after, EndTurn(0))
        evolved = apply_kernel(nxt, EvolvePokemon(1, uid(nxt, H.MUK, 1), nxt.players[1].bench[0].pokemon_id))
        rejects(self, evolved, UseAttack(1, 0), E.QUICKEN_SUPPRESSED_CODE)
        # 使ったアンノーンQ が場にいない（場をはなれた）なら問いにならず、効果は続く（ほのおのまもりと同じ読み方）
        import dataclasses

        record = next(r for r in evolved.trainer_effects if r.kind == GROUP_ATTACK_IMMUNITY)
        self.assertIsNotNone(E.quicken_suppressed_question(evolved, record))
        self.assertIsNone(E.quicken_suppressed_question(evolved, dataclasses.replace(record, pokemon_id=999)))

    def test_the_unown_deck_rule_counts_c_and_q_together(self):
        """ルール文「「アンノーン」はデッキに4枚までしか入れることができません。」は、C・Q をほかのアンノーンと合わせて数える（v0.96 の共通の確かめ）。"""
        from kyuura_engine.deck import deck_problems

        filler = [PS] * 55
        self.assertEqual(deck_problems([UNOWN_C, UNOWN_C, UNOWN_Q, UNOWN_Q, H.RATTATA] + filler), [])
        problems = deck_problems([UNOWN_C, UNOWN_C, UNOWN_Q, UNOWN_Q, "neo4-053"] + filler)
        self.assertTrue(any("アンノーン" in p for p in problems))

    def test_records_are_saved(self):
        _, after = self.used(HD)
        written = state_to_dict(after, format_version=26)
        self.assertEqual(sorted(r["kind"] for r in written["trainer_effects"]), sorted([QUICKEN_USED, GROUP_ATTACK_IMMUNITY]))
        nxt = apply_kernel(after, EndTurn(0))
        expected = snap(attack(nxt, 0))
        for other in (nxt.clone(), copy.deepcopy(nxt), pickle.loads(pickle.dumps(nxt))):
            self.assertEqual(snap(attack(other, 0)), expected)


# ---------------------------------------------------------------- 8. ［きしかいせい］・［かえるのうた］（8 章）


class DamagePowersTest(unittest.TestCase):
    """8 章: 常にはたらく 2 段階の特殊能力。［きしかいせい］は「その数にする」、［かえるのうた］は加算。ねむり・マヒ・こんらんで使えない。"""

    def hit(self, active, *coins, bench=(H.RATTATA,), opponent=None, opponent_bench=(H.RATTATA,)):
        state = board(active, bench=bench, opponent=opponent or mon(H.LAPRAS), opponent_bench=opponent_bench)
        after = attack(state, 0, *coins)
        return new_events(state, after, "damage")[0]

    def test_desperation_sets_120_at_remaining_hp_20(self):
        damage = self.hit(mon(HERACROSS, (G, G, G), damage=40), HD)
        self.assertEqual((damage["amount"], damage["steps"], damage["damage_set"]), (120, (("1 基本となる計算", 60), ("2 ヘラクロス［きしかいせい］", 120)), ((2, 0, 120),)))
        self.assertEqual(self.hit(mon(HERACROSS, (G, G, G), damage=30), HD)["amount"], 60)
        self.assertEqual(self.hit(mon(HERACROSS, (G, G, G), damage=40, confusion=True), HD, HD)["amount"], 60)  # こんらんで使えない

    def test_desperation_does_not_change_a_failed_megahorn(self):
        state = board(mon(HERACROSS, (G, G, G), damage=40))
        after = attack(state, 0, TL)
        self.assertEqual(kinds(state, after, "damage"), [])

    def test_frog_song_counts_names_on_both_fields(self):
        two = self.hit(mon(POLITOED, (W, W, W, W)), HD, TL, bench=(POLIWAG,))
        self.assertEqual(two["amount"], 40)
        three = self.hit(mon(POLITOED, (W, W, W, W)), HD, TL, bench=(POLIWAG,), opponent_bench=(mon(POLIWHIRL),))
        self.assertEqual((three["amount"], three["modifiers"]), (80, ((2, three["modifiers"][0][1], 40),)))
        misty = self.hit(mon(POLITOED, (W, W, W, W)), HD, TL, bench=(POLIWAG, H.MISTYS_POLIWAG))
        self.assertEqual(misty["amount"], 40)  # 「カスミのニョロモ」は名前が違う

    def test_frog_song_is_step_two_and_off_while_confused(self):
        weak = self.hit(mon(POLITOED, (W, W, W, W)), HD, HD, bench=(POLIWAG, POLIWAG), opponent=mon(H.CHARMANDER))
        self.assertEqual(weak["steps"], (("1 基本となる計算", 80), ("2 ニョロトノ［かえるのうた］", 120), ("3 弱点", 240)))
        zero = self.hit(mon(POLITOED, (W, W, W, W)), TL, TL, bench=(POLIWAG, POLIWAG))
        self.assertEqual(zero["steps"], (("1 基本となる計算", 0), ("2 ニョロトノ［かえるのうた］", 40)))
        confused = self.hit(mon(POLITOED, (W, W, W, W), confusion=True), HD, HD, TL, bench=(POLIWAG, POLIWAG))
        self.assertEqual(confused["amount"], 40)


# ---------------------------------------------------------------- 9. ほかのワザ（8 章）


class OtherAttacksTest(unittest.TestCase):
    def test_intimidate_locks_only_a_basic(self):
        """いかく: 相手がたねポケモンならワザを 1 つ選ぶ。進化ポケモンなら何もしない。ベイビィは NB1（neo の説明）。"""
        state = board(mon(STANTLER, (W,)), opponent=mon(H.LAPRAS, (W,)))
        asked = attack(state)
        self.assertEqual((asked.decision.kind, asked.decision.player, asked.decision.options), ("select_opponent_attack", 0, (0, 1)))
        locked = answer(asked, (1,))
        self.assertEqual(kinds(asked, locked, "persistent_effect_added"), ["persistent_effect_added"])
        audited(self, locked)
        evolved = board(mon(STANTLER, (W,)), opponent=mon(H.HAUNTER, (PS,)))
        after = attack(evolved)
        self.assertEqual((after.decision, kinds(evolved, after, "persistent_effect_added")), (None, []))
        rejects(self, board(mon(STANTLER, (W,)), opponent=mon(PICHU)), UseAttack(0, 0), "UNRESOLVED_NEO_TEXT_BASIC_BABY")

    def test_mega_flame_discards_the_tails_count(self):
        for coins, count in (((HD, HD), 0), ((HD, TL), 1), ((TL, TL), 2)):
            with self.subTest(coins=coins):
                state = board(mon(ENTEI, (FR, FR, FR)))
                after = attack(state, 0, *coins)
                if count:
                    d = after.decision
                    self.assertEqual((d.kind, d.min_choices, d.max_choices), ("discard_energy", count, count))
                    after = answer(after, d.options[:count])
                self.assertEqual((len(after.players[0].active.energy), after.players[1].active.damage), (3 - count, 50))
                audited(self, after)

    def test_mega_flame_with_rainbow_energy_is_the_existing_rb1(self):
        """炎炎炎を基本エネルギー以外（レインボーエネルギー）で払うと、「炎エネルギーカード」に数えるかは既存の RB1。足りない場合の「ダメージはなくなる」は v0.82 のヒートフレイムと共通。"""
        state = board(mon(ENTEI, (FR, H.RAINBOW_ENERGY, H.RAINBOW_ENERGY)))
        rejects(self, with_coin_results(state, TL, TL), UseAttack(0, 0), "UNRESOLVED_RAINBOW_ENERGY_TYPE")

    def test_crystal_wave_one_coin_decides_bonus_or_switch(self):
        heads = board(mon(SUICUNE, (W, W, W)), opponent=mon(H.HITMONCHAN))
        self.assertEqual(attack(heads, 0, HD).players[1].active.damage, 40)
        tails = attack(heads, 0, TL)
        self.assertEqual((tails.decision.kind, tails.decision.player), ("forced_switch", 1))
        lonely = board(mon(SUICUNE, (W, W, W)), opponent=mon(H.HITMONCHAN), opponent_bench=())
        after = attack(lonely, 0, TL)
        self.assertEqual([e["reason"] for e in new_events(lonely, after, "forced_switch_skipped")], ["no_bench"])

    def test_psychic_damage_through_psycho_link_uses_the_redone_heads(self):
        """ナツメのフーディンが［サイコリンク］で控えのセレビィ（超）のサイキックダメージを使い、ナツメのESPでやり直すと、のせるのはやり直したあとの最後の「おもて」の数
        （v0.113 の ``esp_board`` と同じ手順。待つ状態は clone・deepcopy・pickle で同じ）。"""
        from kyuura_engine.decisions import ESP_REDO
        from tests import test_variable_coins_search_attachments_v0_113 as V113

        state = board(mon(V113.ALAKAZAM, (PS, PS, PS, PS), evolved_from=V113.BELOW[V113.ALAKAZAM]), bench=(mon(CELEBI),), opponent=mon(H.LAPRAS),
                      hand=(V113.ESP_CARD,))
        played = apply_kernel(state, PlayTrainer(0, uid(state, V113.ESP_CARD)))
        state = answer(played, (played.players[0].active.pokemon_id,))
        asked = V113.attack(state, 0, HD, HD, HD, card=V113.provider_card(state, CELEBI))
        self.assertEqual(asked.decision.kind, ESP_REDO)
        for redo, coins, counters in (((), (), 3), ((1,), (TL, HD, TL), 1), ((1,), (TL, TL, TL), 0)):
            with self.subTest(redo=redo, coins=coins):
                after = same_answers(self, asked, redo, *coins)
                self.assertEqual([e["counters"] for e in new_events(asked, after, "place_damage_counters")] or [0], [counters])
                audited(self, after)

    def test_psychic_damage_places_counters_without_weakness(self):
        state = board(mon(CELEBI, (PS,)), opponent=mon(H.HITMONCHAN))
        after = attack(state, 0, HD, HD, TL)
        self.assertEqual([(e["counters"], e["amount"]) for e in new_events(state, after, "place_damage_counters")], [(2, 20)])
        self.assertEqual(after.players[1].active.damage, 20)  # 弱点 超の「×2」は当てはめない
        none = attack(state, 0, TL, TL, TL)
        self.assertEqual(kinds(state, none, "place_damage_counters"), [])


# ---------------------------------------------------------------- 10. 保存・公開・不変条件


class SaveAndObservationTest(unittest.TestCase):
    def test_format_unchanged_and_public_logs(self):
        """保存の形式は 26 のまま（新しい持続する効果・プレイヤーの記録の種類は ``effect``・``kind`` と項目を書く。形式を上げない）。新しいログは公開。"""
        self.assertEqual((max(FORMAT_VERSIONS), LATEST_FORMAT), (26, 26))
        self.assertTrue({"chase_check", "chase_counters", "chase_skipped", "pursuit_damage", "pursuit_skipped", "pursuit_prevented", "time_travel",
                         "legend_body_discard", "trainer_effect_blocked"} <= PUBLIC_EVENTS)

    def test_reaction_order_is_visible_to_both_players(self):
        state = ReactionOrderTest().ordered()
        p = state.players[1]
        asked = apply_kernel(state, Retreat(1, tuple(p.active.energy[:2]), p.bench[0].card))
        for viewer in (0, 1, None):
            self.assertEqual(observe(asked, viewer)["decision"]["kind"], REACTION_ORDER)
        audited(self, asked)

    def test_invariants_reject_a_wrong_pursuit_effect(self):
        """不変条件: 登録のワザ・ログと合わない持続する効果（量の違うおいうち）を見つける。"""
        import dataclasses

        after = pursued()
        broken = after.clone()
        defender = broken.players[1].active
        defender.persistent_effects = tuple(dataclasses.replace(e, amount=20) if isinstance(e, PursuitOnRetreat) else e for e in defender.persistent_effects)
        self.assertTrue(check_invariants(broken))
        quicken = QuickenTest().used(HD)[1].clone()
        quicken.trainer_effects = tuple(dataclasses.replace(r, expires_turn=r.expires_turn + 1) for r in quicken.trainer_effects)
        self.assertTrue(check_invariants(quicken))


# ---------------------------------------------------------------- 11. ログの監査


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v117_problems``・``v117_close``）は、エンジンの登録・計算を読まずに、処理したワザの印刷の文面と、ログから組み立てた場・コイン・カードの
    動きで確かめる。エンジンの処理を一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の局。開発用の seed 50・51。正式な対戦の seed 0〜3 とは別）で、監査が
    それを見つける。"""

    GAMES = ((("D117", "U117"), 50), (("U117", "L117"), 51), (("D117", "N117"), 50), (("L117", "G61"), 51))

    @classmethod
    def problems_for(cls, patcher, *needles, games_=None):
        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        found = []
        with patcher:
            for labels, seed in games_ or cls.GAMES:
                try:
                    result = games.play(labels, seed, keep_state=True)
                except Exception as error:  # noqa: BLE001  誤らせた処理が不変条件で止まっても、監査とは別の理由（ここでは数えない）
                    found.append(f"stopped: {error}") if "stopped" in needles else None
                    continue
                if result.get("state") is not None:
                    found += [p for p in log_problems(result["state"]) if any(n in p for n in needles)]
        return found

    def test_the_unpatched_games_pass_the_audit_and_use_the_new_mechanics(self):
        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        used = Counter()
        for labels, seed in self.GAMES:
            result = games.play(labels, seed, keep_state=True)
            with self.subTest(labels=labels, seed=seed):
                self.assertIn(result["outcome"], ("game_over", "sudden_death"))
                self.assertEqual((result["audit"], log_problems(result["state"])), ({}, []))
            used.update({k for k, v in result["v117"].items() if v})
        self.assertTrue({"chase_counters", "pursuit_given", "take_away_recovered", "intimidate_locked", "psychic_damage_counters_2", "time_travel_heads",
                         "time_travel_tails", "quicken_heads", "quicken_prevented_damage", "mega_flame_discarded_card"} <= set(used))

    def test_audit_finds_extra_chase_counters(self):
        original = M.chase_counters

        def two(state, reaction):
            original(state, reaction)
            last = state.log[-1]
            if last["kind"] == "chase_counters":
                state.find_pokemon(last["target_pokemon_id"])[1].damage += 10
                state.log = state.log[:-1] + (MappingProxyType({**last, "counters": 2, "amount": 20, "total_damage": last["total_damage"] + 10}),)

        self.assertTrue(self.problems_for(mock.patch.object(M, "chase_counters", two), "［CHASE］のダメージカウンター"))

    def test_audit_finds_the_wrong_flipper_and_a_second_chase(self):
        """［CHASE］のコインをにげたプレイヤーが投げた（持ち主ではない）・同じ「にげる」で 2 度処理した。"""
        original_flip = M.flip_coins

        def retreating_player_flips(state, player, count, **options):
            if options.get("source") == "power" and str(options.get("effect", "")).startswith(UNOWN_C):
                player = 1 - player
            return original_flip(state, player, count, **options)

        self.assertTrue(self.problems_for(mock.patch.object(M, "flip_coins", retreating_player_flips), "持ち主のコインのすぐあと"))
        original = M.chase_counters

        def twice(state, reaction):
            original(state, reaction)
            original(state, reaction)

        self.assertTrue(self.problems_for(mock.patch.object(M, "chase_counters", twice), "1 度目の判定ではない"))

    @staticmethod
    def without_place_question():
        """試験だけ: 「にげる」の RR1 のうち、おいうちのダメージが入れ替えの前と後で違う場面を止めずに、入れ替えのあと（ベンチ）の値で処理する（こんらんの RR1 は残す）。
        対戦のデッキのおいうちの使い手には悪エネルギーがつき、その「+10」は対戦ポケモンへのダメージだけなので、そのままでは「にげる」ときのダメージが対戦で起こらない。
        ログの監査がおいうちのダメージを確かめる道筋を、正式な開始からの対戦で通すために使う（エンジンの読み方ではない）。"""
        from kyuura_engine import engine as EN

        original = EN._retreat_reaction_check

        def check(state, player, active, index, chases, pursuits):
            try:
                return original(state, player, active, index, chases, pursuits)
            except UnsupportedError as error:
                if error.code == E.RETREAT_REACTION_TIMING_CODE and not active.conditions.confused:
                    return None
                raise

        return mock.patch.object(EN, "_retreat_reaction_check", check)

    PURSUIT_GAMES = ((("D117", "P31"), 50), (("P31", "D117"), 50), (("D117", "U117"), 50))

    def test_pursuit_damage_in_games_passes_and_errors_are_found(self):
        """おいうちのダメージ（ベンチのきぜつ・サイドをふくむ）を通した局は監査を通り、2 倍の量・2 度の処理を加えると監査が見つける。"""
        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        used = Counter()
        with self.without_place_question():
            for labels, seed in self.PURSUIT_GAMES:
                result = games.play(labels, seed, keep_state=True)
                with self.subTest(labels=labels, seed=seed):
                    self.assertEqual((result["outcome"], result["audit"], log_problems(result["state"])), ("game_over", {}, []))
                used.update({k: v for k, v in result["v117"].items() if v})
        self.assertGreaterEqual(used["pursuit_damage_10"], 3)
        self.assertGreaterEqual(used["pursuit_knocked_out"], 1)
        original = M.pursuit_damage

        def doubled(state, reaction):
            original(state, reaction)
            last = state.log[-1]
            if last["kind"] == "pursuit_damage":
                state.find_pokemon(last["target_pokemon_id"])[1].damage += last["amount"]
                state.log = state.log[:-1] + (MappingProxyType({**last, "amount": last["amount"] * 2, "total_damage": last["total_damage"] + last["amount"]}),)

        def twice(state, reaction):
            original(state, reaction)
            original(state, reaction)

        for patcher, needle in ((mock.patch.object(M, "pursuit_damage", doubled), "おいうちのダメージ"), (mock.patch.object(M, "pursuit_damage", twice), "2 度目")):
            with self.subTest(needle=needle), self.without_place_question():
                self.assertTrue(self.problems_for(patcher, needle, games_=self.PURSUIT_GAMES))

    def test_audit_finds_extra_psychic_damage_counters(self):
        original = P.OpponentCountersByHeads.run

        def one_more(self, run):
            placed = original(self, run)
            state = run.state
            last = state.log[-1]
            if last["kind"] == "place_damage_counters":
                run.opponent_active().damage += 10
                state.log = state.log[:-1] + (MappingProxyType({**last, "counters": last["counters"] + 1, "amount": last["amount"] + 10,
                                                                 "total_damage": last["total_damage"] + 10}),)
            return placed

        self.assertTrue(self.problems_for(mock.patch.object(P.OpponentCountersByHeads, "run", one_more), "でのせたダメージカウンター"))

    def test_audit_finds_a_missing_shuffle_after_take_away(self):
        original = P.shuffle_in_attack

        def skip(run, element, player):
            if isinstance(element, P.CoinDiscardCardToDeckThenShuffle):
                return None
            return original(run, element, player)

        self.assertTrue(self.problems_for(mock.patch.object(P, "shuffle_in_attack", skip), "山札を切らないまま"))

    def test_audit_finds_intimidate_on_an_evolved_pokemon(self):
        """D117 対 M87（進化ポケモンの多いデッキ）の seed 50 で、いかくを進化ポケモンにも当てる。"""
        locks = {E.LockOpponentAttackIfBasic: lambda e: (P.OpponentAttackLock(),)}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, locks), "場の「たねポケモン」ではない", games_=((("D117", "M87"), 50),)))


class DocumentTest(unittest.TestCase):
    def test_document_records(self):
        text = DOC.read_text(encoding="utf-8")
        for word in ("RR1", "QK1", "TW1", "TW2", "LB1", "LB2", "VH1", "ES4", *NEW_CODES, E.LEGEND_BODY_PENDING_CODE, E.PURSUIT_UNSUPPORTED_CODE,
                     "GR-2000-P325-SAME-TIMING", "GR-2000-P320-COUNTER-MOVE", "UQ-NEO-TEXT-BABY-CATEGORIES", "NB1", "HC3", "RB1", "1,302", "(75, 28, 47)", "492",
                     "## 12. 検証", "lockstep", "単体のテストだけ", "外部照合・カード画像・ガイドブックの読み直しをしていません"):
            self.assertIn(word, text)
        for card in V0117:
            self.assertIn(card, text)
        v0116 = (ROOT / "docs" / "energy-movement-attachment-devolution-v0.116.md").read_text(encoding="utf-8")
        self.assertIn("6,474", v0116)  # v0.116 の全体のテストの記録（失敗 1 のあと関係 2 モジュール）はそのまま
        status = (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(int(re.search(r"^# 実装状況（v0\.1〜v0\.(\d+)）", status, re.MULTILINE).group(1)), 117)
        self.assertIn("## v0.117: 場の移動・にげる時の反応・条件付きの特殊能力", status)
        self.assertRegex((ROOT / "README.md").read_text(encoding="utf-8"), r"\n- v0\.117（(今のエンジンの版。)?`kyuura_engine` の版は 0\.117\.0）: 場の移動")
        self.assertIn("### v0.117: 場の移動", (ROOT / "docs" / "rules-2000-02-14.md").read_text(encoding="utf-8"))
        self.assertIn("## v0.117: 場の移動", (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

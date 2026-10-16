"""v0.35: 可変枚数のコインの先読み・ダメージの計算の順番の決定と、5 枚（docs/coin-groups-damage-order-v0.35.md）。

共通の仕組みの境界（``CoinGroupTest``・``ExeggutorBoundaryTest``・``DamageCalculationOrderTest``・``StepOrderDecisionTest``）と、カードごとの処理
（``FocusEnergyTest`` ほか）と、カードごとの登録の確かめ（``CardDataTest``）と、すべてのワザの先読みの方法ごとの一致（``PreflightParityTest``）に分けた。

根拠はどれも kyuura データの採用（kyuura の印刷の文面。``card_sources.json``）と、既存の記録（p.309 の手順と「処理の対象がなくなってしまっている場合」、
p.310・p.322・p.323 の持続する効果の消える契機、p.321 のダメージの計算の段階と「ダメージを変更する効果」の順番を選ぶプレイヤー（docs/scyther-v0.27.md の
SC15）、v0.3d の自分へのダメージの計算、v0.4b の ``UNRESOLVED_PREVENTED_COIN_DAMAGE``、v0.10 の C18、v0.34 の ``void_coin_question``）の再利用。
ガイドブックは読んでいない。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import pickle
import random
import time
import types
import unittest
from unittest import mock

from kyuura_engine import (
    EndTurn,
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UnsupportedError,
    UseAttack,
    apply_command,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, read_extract
from kyuura_engine.coins import flip_coins
from kyuura_engine.damage import ADD, MULTIPLY, SET, DamageModifier, DamageOrderRequired, calculate_attack_damage, step_orders
from kyuura_engine.decisions import DAMAGE_STEP_ORDER, DISCARD_OPPONENT_ENERGY, SELECT_OPPONENT_ATTACK
from kyuura_engine.engine import apply_command_traced, check_invariants
from kyuura_engine.persistent import attack_locked, next_turn_attack_damage
from kyuura_engine.resolution import PREFLIGHT_MODES, open_attack, preflight
from kyuura_engine.resolution import events as resolution_events
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.questions import OpenQuestion
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.rules import RULES_2000_02_14
from kyuura_engine.state import PERSISTENT_EFFECT_TYPES, CannotUseAttack, CannotUseOwnAttack, NextTurnAttackDamage
from scripts import check_card_sources as cs
from scripts.extract_kyuura_cards import KYUURA_COMMIT
from tests.helpers import (
    BLAINES_TAUROS,
    BROCKS_RHYHORN,
    CHARMANDER,
    CLEFAIRY,
    CUBONE,
    DARK_CHARIZARD,
    DARK_CHARMELEON,
    EXEGGCUTE,
    EXEGGUTOR,
    FIGHTING,
    FIRE,
    GRASS,
    HAUNTER,
    GASTLY,
    HITMONCHAN,
    JOLTEON,
    EEVEE,
    KANGASKHAN,
    LIGHTNING,
    LT_SURGES_ELECTABUZZ,
    LT_SURGES_RATICATE,
    LT_SURGES_RATTATA,
    MACHAMP,
    MACHOKE,
    MACHOP,
    METAPOD,
    CATERPIE,
    MISTYS_POLIWAG,
    MISTYS_POLIWHIRL,
    NIDORAN_M,
    NIDOKING,
    NIDORINO,
    PSYCHIC,
    RATTATA,
    SCYTHER,
    SWITCH,
    V0_35_POKEMON,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import serialization_problems
from tests.test_barrier_resume_coin_bonus_v0_34 import assert_stops, coins, events, first, full, kinds, play

ROOT = pathlib.Path(__file__).resolve().parent.parent
TURN = 7
DOC = ROOT / "docs" / "coin-groups-damage-order-v0.35.md"
# 進化しているカードの下のカード
BELOW = {LT_SURGES_RATICATE: LT_SURGES_RATTATA, MISTYS_POLIWHIRL: MISTYS_POLIWAG, EXEGGUTOR: EXEGGCUTE, MACHAMP: [MACHOP, MACHOKE],
         HAUNTER: GASTLY, METAPOD: CATERPIE, NIDORINO: NIDORAN_M, JOLTEON: EEVEE, DARK_CHARIZARD: [CHARMANDER, DARK_CHARMELEON]}
# 登録の実装の型（カード id, ワザの位置）
EXPECTED = {
    (LT_SURGES_RATTATA, 0): (E.MultiplyNextTurnAttackDamage, {"target_attack_index": 1, "target_attack_name": "でんこうせっか", "factor": 2,
                                                              "includes_self_damage": False}),
    (LT_SURGES_RATTATA, 1): (E.CoinBonusDamage, {"bonus": 20}),
    (LT_SURGES_RATICATE, 0): (E.MultiplyNextTurnAttackDamage, {"target_attack_index": 1, "target_attack_name": "すてみタックル", "factor": 2,
                                                               "includes_self_damage": True}),
    (LT_SURGES_RATICATE, 1): (E.DamageAndSelfDamage, {"self_damage": 20}),
    (MISTYS_POLIWAG, 0): (E.DamageThenLockSelfOnTails, {}),
    (MISTYS_POLIWAG, 1): (E.LockOpponentAttack, {}),
    (MISTYS_POLIWHIRL, 0): (E.DamageThenDiscardOpponentEnergy, {"on_heads": True}),
    (MISTYS_POLIWHIRL, 1): (E.CoinsPerAttachedTypeBonusDamage, {"energy_type": EnergyType.WATER, "per": 10}),
    (BLAINES_TAUROS, 0): (E.CoinFlipDamage, {"coins": 3, "damage_per_heads": 10}),
    (BLAINES_TAUROS, 1): (E.CoinsHeadsDamageTailsSelfDamage, {"coins": 4, "per": 20, "self_per": 20}),
}
# pcg-search.com の対象の版（サイトの一覧の番号）
EDITIONS = {LT_SURGES_RATTATA: "057/096", LT_SURGES_RATICATE: "058/096", MISTYS_POLIWAG: "023/096", MISTYS_POLIWHIRL: "024/096",
            BLAINES_TAUROS: "070/098"}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) is not None and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), hand=(), opponent_hand=(), turn=TURN):
    me = {"active": active, "bench": list(bench), "hand": list(hand)}
    them = {"active": opponent or mon(HITMONCHAN, (FIGHTING,)), "bench": list(opponent_bench), "hand": list(opponent_hand)}
    return build_test_state([me, them], turn_number=turn)


def end(state, player):
    return apply_kernel(state, EndTurn(player))


def opponent_damage(state, since):
    return [e["amount"] for e in events(state, since, "damage") if e.get("target") is None]


def self_damage(state, since):
    return [e["amount"] for e in events(state, since, "damage") if e.get("target") == "self"]


def snapshot(state):
    return full(state), rng_fingerprint(state.rng), [dict(e) for e in state.log]


def traced(state, command, mode="derived_full", *, grouped=True):
    """(結果, 試した結果の数) を返す。結果は受け付けたら (形式 10, 乱数)、拒否したら (例外の型, コード, 理由の文)。``grouped`` が False なら、先読みの
    乱数の ``coin_group`` を 1 枚ずつの値にする（v0.34 までの先読みと同じ数え方。比べるため）。"""

    def per_bit(self, count):
        return tuple(self._next(2) for _ in range(count))

    patch = mock.patch.object(preflight.Oracle, "coin_group", per_bit) if not grouped else mock.patch.object(preflight, "MAX_BRANCHES", preflight.MAX_BRANCHES)
    with patch:
        try:
            new, trace = apply_command_traced(state, command, preflight=mode)
            result = (full(new), rng_fingerprint(new.rng))
            branches = [r.branches for r in trace.of(resolution_events.PreflightResult)]
        except EngineError as error:
            result, branches = (type(error).__name__, error.code, str(error)), None
    return result, branches


class CardDataTest(unittest.TestCase):
    """5 枚の登録・写し・採用の記録・進化の関係と、保留を続けるガルーラ。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_five_requested_cards(self):
        """対象は依頼の 5 枚（ほかの候補に広げていない）。写しの組 pool_v0_35 は 5 枚で、どれも対戦に使える。v0.34 で保留したガルーラ（PMCG2-046）は
        保留のまま（登録しない・対戦に使えない）。"""
        self.assertEqual(len(V0_35_POKEMON), 5)
        self.assertEqual(list(read_extract()["pool_v0_35"]), list(V0_35_POKEMON))
        for card in V0_35_POKEMON:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))
        self.assertFalse(self.pool.is_playable(KANGASKHAN))
        self.assertFalse([k for k in E.DEFAULT_EFFECTS.attack_keys() if k.card_id == KANGASKHAN])

    def test_every_attack_is_registered_with_the_expected_type(self):
        """10 のワザがどれも登録され、型と値が表のとおり。名前・文面は写しと同じで、処理に使う文面は kyuura の印刷の文面。特殊能力を持つカードはない。"""
        seen = set()
        for card in V0_35_POKEMON:
            definition = self.pool.get(card)
            self.assertEqual(definition.powers, ())
            for attack in definition.attacks:
                key = (card, attack.index)
                seen.add(key)
                entry = E.DEFAULT_EFFECTS.attack_entry(card, attack.index)
                expected_type, values = EXPECTED[key]
                with self.subTest(card=card, attack=attack.name_ja):
                    self.assertIs(type(entry.effect), expected_type)
                    for name, value in values.items():
                        self.assertEqual(getattr(entry.effect, name), value)
                    self.assertEqual(entry.name_ja, attack.name_ja)
                    self.assertIsNone(E.DEFAULT_EFFECTS.attack_problem(card, attack, definition.attacks))
                    self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (attack.text_ja, attack.text_ja, cs.PRINTED_TEXT_SOURCE))
        self.assertEqual(seen, set(EXPECTED))

    def test_focus_energy_registration_follows_the_text(self):
        """「きあいだめ」の登録は、同じカードのほかのワザ（位置と名前）を指し、自分へのダメージの有無が説明の「(自分へのダメージも2倍)」と、変わるワザの
        「自分にも」と合う（合わなければ未対応。``card_problems``）。「つるぎのまい」の「その数にする」（``SetNextTurnAttackDamage``）とは別の型。"""
        rattata = self.pool.get(LT_SURGES_RATTATA).attacks
        raticate = self.pool.get(LT_SURGES_RATICATE).attacks
        wrong = [(E.MultiplyNextTurnAttackDamage(1, "でんこうせっか", includes_self_damage=True), rattata),
                 (E.MultiplyNextTurnAttackDamage(1, "すてみタックル"), raticate),
                 (E.MultiplyNextTurnAttackDamage(0, "きあいだめ"), rattata),
                 (E.MultiplyNextTurnAttackDamage(1, "ひっかく"), rattata)]
        for effect, attacks in wrong:
            with self.subTest(effect=effect):
                self.assertTrue(effect.check(attacks[0]) or effect.card_problems(attacks[0], attacks))
        with self.assertRaises(ValueError):
            E.MultiplyNextTurnAttackDamage(1, "でんこうせっか", factor=1)
        self.assertIsNot(E.MultiplyNextTurnAttackDamage, E.SetNextTurnAttackDamage)
        self.assertFalse(issubclass(E.MultiplyNextTurnAttackDamage, E.SetNextTurnAttackDamage))

    def test_adoption_records(self):
        """5 枚はどれも kyuura データの採用の記録（adopted。研究の基準のコミットにこれらのカードを指す kyuura の記録はない）と pcg-search.com の照合
        （同じ版の一覧の番号。どれも ``match``）を持ち、過去の原典照合の記録には加えていない。ガルーラは v0.34 の保留のまま（記録は変えていない）。"""
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        verification = (ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8")
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        adopted = set(links["latest_descriptions"]["adopted_printed_text"])
        for card in V0_35_POKEMON:
            record = sources[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]), ("kyuura_data", "adopted", KYUURA_COMMIT))
                self.assertEqual(record["kyuura_records"], [])
                self.assertNotIn(f'"{card}"', verification)
                [check] = record["external_checks"]
                self.assertEqual((check["site"], check["edition"]["list_number"], check["result"]), ("pcg-search.com", EDITIONS[card], "match"))
                self.assertEqual(check["differences"], [])
                for attack in self.pool.get(card).attacks:
                    key = f"attack/{attack.index}"
                    self.assertEqual(record["play_text"][key], "kyuura_printed_text")
                    self.assertIn(f"{card}/{key}", adopted)
        hold = sources[KANGASKHAN]
        self.assertEqual((hold["status"], hold["play_text"]), ("on_hold", {}))
        self.assertEqual([i["fields"] for i in hold["issues"]], [["pokemon.attacks[0].text.ja"]])

    def test_evolution_by_exact_name(self):
        """マチスのラッタはマチスのコラッタから、カスミのニョロゾはカスミのニョロモからだけ、通常の進化の操作で進化する（名前の完全な一致）。第1弾の
        コラッタ（名前が違う）からは進化できない。"""
        for upper, below in ((LT_SURGES_RATICATE, LT_SURGES_RATTATA), (MISTYS_POLIWHIRL, MISTYS_POLIWAG)):
            with self.subTest(upper=upper):
                self.assertEqual(self.pool.get(upper).evolves_from, self.pool.get(below).name_ja)
                state = board(mon(HITMONCHAN), bench=[mon(below, played_turn=1)], hand=[upper])
                new = apply_command(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].bench[0].pokemon_id))
                self.assertEqual(new.cards[new.players[0].bench[0].card].card_id, upper)
        state = board(mon(HITMONCHAN), bench=[mon(RATTATA, played_turn=1)], hand=[LT_SURGES_RATICATE])
        with self.assertRaises(IllegalActionError) as raised:
            apply_command(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].bench[0].pokemon_id))
        self.assertEqual(raised.exception.code, "EVOLUTION_NAME_MISMATCH")

    def test_new_persistent_effect_types(self):
        """持続する効果の型: 「あわあわ」は自分自身（はたらく番は次の自分の番）、「ドわすれ」は相手に与える（次の相手の番）。「きあいだめ」は v0.27 の
        ``NextTurnAttackDamage`` の「数をかける」決め方（種類 ``next_turn_attack_damage_multiplier``。「つるぎのまい」の種類は変えていない）。"""
        self.assertIn(CannotUseOwnAttack, PERSISTENT_EFFECT_TYPES)
        self.assertIn(CannotUseAttack, PERSISTENT_EFFECT_TYPES)
        self.assertEqual((CannotUseOwnAttack.turns_until_active, CannotUseOwnAttack.on_opponent), (2, False))
        self.assertEqual((CannotUseAttack.turns_until_active, CannotUseAttack.on_opponent), (1, True))
        common = {"source_card": 1, "source_player": 0, "created_turn": 3, "active_turn": 5, "attack_index": 0, "target_attack_index": 1}
        self.assertEqual(NextTurnAttackDamage(**common, amount=60).kind, "next_turn_attack_damage")
        self.assertEqual(NextTurnAttackDamage(**common, amount=2, operation="multiply").kind, "next_turn_attack_damage_multiplier")
        with self.assertRaises(ValueError):
            NextTurnAttackDamage(**common, amount=60, includes_self_damage=True)  # 「その数にする」に自分へのダメージの印はない


class CoinGroupTest(unittest.TestCase):
    """1 部: 結果を「おもて」の数だけで使うコインを、先読みが「おもて」の数でまとめる（枚数 + 1 通り）。実際の対戦の投げ方・乱数・ログは変えない。"""

    def test_oracle_returns_the_first_sequence_for_a_heads_count(self):
        """先読みの乱数は、台本の 1 つの値を「おもて」の数とし、同じ「おもて」の数の並びのうち 1 枚ずつ試すときに最初に試す並び（「うら」→「おもて」）を
        返す。まとめないとき（比べるため）は 1 枚ずつ値を使う。足りなければ「おもて」の数（枚数 + 1 通り）で分かれる。"""
        self.assertEqual(preflight.Oracle((2,)).coin_group(3), (0, 1, 1))
        self.assertEqual(preflight.Oracle((0,)).coin_group(3), (0, 0, 0))
        self.assertEqual(preflight.Oracle((3,)).coin_group(3), (1, 1, 1))
        self.assertEqual(preflight.Oracle((1, 0, 1), group=False).coin_group(3), (1, 0, 1))
        with self.assertRaises(preflight.NeedToken) as raised:
            preflight.Oracle(()).coin_group(4)
        self.assertEqual(raised.exception.n, 5)

    def test_recording_random_flips_one_by_one_and_records_the_heads_count(self):
        """実際の処理の乱数の前に置く記録は、元の乱数で 1 枚ずつ投げ（乱数の使い方は ``getrandbits(1)`` を枚数回と同じ）、(「おもて」の数, 枚数 + 1) を
        1 つ記録する。"""
        rng, twin = random.Random(35), random.Random(35)
        holder = types.SimpleNamespace(rng=rng)
        recorder = preflight.RecordingRandom(holder)
        bits = recorder.coin_group(7)
        self.assertEqual(bits, tuple(twin.getrandbits(1) for _ in range(7)))
        self.assertEqual(recorder.tokens, [(sum(bits), 8)])
        self.assertEqual(rng.getstate(), twin.getstate())
        self.assertFalse(recorder.opaque)

    def test_sibling_roots_cover_every_other_value(self):
        """試していない結果の台本は、値ごとの選べる数で作る（コイン 1 枚だけなら v0.34 までと同じ）。"""
        self.assertEqual(preflight.sibling_roots(((1, 2), (0, 2))), ((0,), (1, 1)))
        self.assertEqual(preflight.sibling_roots(((2, 4),)), ((0,), (1,), (3,)))
        self.assertEqual(preflight.sibling_roots(((1, 2), (2, 4))), ((0,), (1, 0), (1, 1), (1, 3)))

    def test_flip_coins_by_heads_keeps_rng_and_log_in_real_games(self):
        """実際の対戦の乱数（``random.Random``）は ``coin_group`` を持たないので、``by_heads`` でも 1 枚ずつ ``getrandbits(1)`` で投げる（結果・ログ・
        乱数は ``by_heads`` なしと同じ）。"""
        state = board(mon(EXEGGUTOR, (GRASS,) * 5))
        results = []
        for by_heads in (False, True):
            s = state.clone()
            flips = flip_coins(s, 0, 5, source="attack", effect="test", card=s.players[0].active.card, by_heads=by_heads)
            results.append((flips.results, snapshot(s)))
        self.assertEqual(results[0], results[1])

    def test_grouped_and_ungrouped_enumeration_agree(self):
        """少ない枚数で、まとめた先読みと、1 枚ずつの先読み（v0.34 までの数え方）の答え（受け付けるか・拒否のコード・理由の文・結果の状態と乱数）が同じ。
        試した結果の数はまとめたほうが少ないか同じ。対象は、まとめるコインを使う製品のワザ（たまなげMAX・ウォーターパンチ・ぜんりょくとっしん・ドリル
        タックル・ほうでん・れんぞくファイヤーボール）。問いに当たる盤面（「ダメージを受けない」相手・はんげきの C18）も含める。"""
        cases = []
        for n in (1, 2, 3, 5):
            cases += [(f"たまなげMAX {n}", board(mon(EXEGGUTOR, (GRASS,) * n)), 1),
                      (f"たまなげMAX {n} かたまる", board(mon(EXEGGUTOR, (GRASS,) * n), mon(METAPOD, prevent_damage=TURN - 1)), 1),
                      (f"ウォーターパンチ 水 {n}", board(mon(MISTYS_POLIWHIRL, (WATER,) * n + (FIGHTING,) * max(0, 3 - n))), 1)]
        cases += [("たまなげMAX C18", board(mon(EXEGGUTOR, (GRASS,) * 4, damage=70), mon(MACHAMP, (FIGHTING,), damage=40)), 1),
                  ("たまなげMAX はんげき", board(mon(EXEGGUTOR, (GRASS,) * 4), mon(MACHAMP, (FIGHTING,))), 1),
                  ("ぜんりょくとっしん", board(mon(BLAINES_TAUROS, (FIRE,) * 3)), 1),
                  ("ぜんりょくとっしん かたまる", board(mon(BLAINES_TAUROS, (FIRE,) * 3), mon(METAPOD, prevent_damage=TURN - 1)), 1),
                  ("ぜんりょくとっしん C18 なし", board(mon(BLAINES_TAUROS, (FIRE,) * 3), mon(MACHAMP, (FIGHTING,), damage=40)), 1),
                  ("ぜんりょくとっしん C18", board(mon(BLAINES_TAUROS, (FIRE,) * 3), mon(MACHAMP, (FIGHTING,), damage=80)), 1),
                  ("ドリルタックル", board(mon(BROCKS_RHYHORN, (FIGHTING, FIGHTING))), 0),
                  ("ドリルタックル C18", board(mon(BROCKS_RHYHORN, (FIGHTING, FIGHTING), damage=60), mon(MACHAMP, (FIGHTING,), damage=40)), 0),
                  ("ほうでん", board(mon(LT_SURGES_ELECTABUZZ, (LIGHTNING,) * 3)), 1),
                  ("れんぞくファイヤーボール", board(mon(DARK_CHARIZARD, (FIRE,) * 4)), 1)]
        for label, state, index in cases:
            with self.subTest(case=label):
                grouped, grouped_branches = traced(state, UseAttack(0, index))
                ungrouped, ungrouped_branches = traced(state, UseAttack(0, index), grouped=False)
                self.assertEqual(grouped, ungrouped)
                if grouped_branches is not None:
                    self.assertLessEqual(grouped_branches[0], ungrouped_branches[0])
        # 問いに当たる盤面は、まとめても同じコード・同じ理由の文で止まる
        found = {label: traced(state, UseAttack(0, index))[0] for label, state, index in cases}
        for label, code in (("たまなげMAX C18", "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT"), ("ぜんりょくとっしん C18", "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT"),
                            ("たまなげMAX 3 かたまる", "UNRESOLVED_PREVENTED_COIN_DAMAGE"), ("ドリルタックル C18", "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")):
            with self.subTest(case=label):
                self.assertEqual(found[label][1], code)
        self.assertIsInstance(found["ぜんりょくとっしん C18 なし"][0], dict)  # 受け付けた（形式 10, 乱数）

    def test_full_speed_charge_keeps_opponent_and_self_damage_as_pairs(self):
        """ぜんりょくとっしん: 同じ 4 枚のコインの「おもて」の数で相手へのダメージ、「うら」の数で自分へのダメージ（組）。先読みも組で試すので、相手への
        ダメージと自分へのダメージを別々の結果として組み合わせない:

        - カイリキー（ダメージ 40。HP 100）: きぜつさせるには「おもて」3 枚以上（60）。ケンタロス（HP 70）がはんげきの 10 できぜつする（自分への 60 と
          10）のは「おもて」1 枚のときで、そのときカイリキーは 20 でぎぜつしない → C18 に当たらない（組にしないと、「おもて」3 枚の 60 と「おもて」
          1 枚の自分への 60 を組み合わせて当たってしまう）
        - カイリキー（ダメージ 80）: 「おもて」1 枚でカイリキーが 20 できぜつし、ケンタロスがはんげきできぜつする → C18 で止める
        """
        accepted = board(mon(BLAINES_TAUROS, (FIRE,) * 3), mon(MACHAMP, (FIGHTING,), damage=40))
        for mode in PREFLIGHT_MODES:
            with self.subTest(mode=mode):
                play(accepted, UseAttack(0, 1), mode=mode)
        assert_stops(self, board(mon(BLAINES_TAUROS, (FIRE,) * 3), mon(MACHAMP, (FIGHTING,), damage=80)), UseAttack(0, 1),
                     "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")
        _, branches = traced(accepted, UseAttack(0, 1))
        self.assertEqual(branches, [5])  # 「おもて」0〜4 枚

    def test_coin_flip_damage_stays_per_coin(self):
        """``CoinFlipDamage``（3ぼんのしっぽ・ミサイルばり）は、結果の使い道は「おもて」の数だけ（まとめても答えは変わらない）だが、枚数が登録で決まった
        2〜4 枚で上限に届かないので、まとめない（v0.15c・v0.16c の上限のテストが基準にする 1 枚ずつの木のまま）。"""
        self.assertFalse(P.HeadsTimes.by_heads)
        self.assertEqual(traced(board(mon(BLAINES_TAUROS, (FIRE,))), UseAttack(0, 0))[1], [8])
        self.assertEqual(traced(board(mon(JOLTEON, (LIGHTNING,) * 3)), UseAttack(0, 1))[1], [16])

    def test_order_dependent_coins_are_not_grouped(self):
        """2 枚以上のワザ全体のコインのうち、あとの要素が 1 枚目の面（並び）を使うものはまとめられない。製品の登録には、そのような並びはない（あれば
        先読みの前に RuntimeError。並びで処理が変わるコインを「おもて」の数でまとめない）。"""
        for key in E.DEFAULT_EFFECTS.attack_keys():
            program = P.compile_attack(E.DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect)
            for element in program:
                if isinstance(element, P.Coin) and (element.count > 1 or element.per_attached is not None):
                    gated = [e for e in program if isinstance(getattr(e, "gate", None), tuple) and e.gate[0] == element.name
                             and isinstance(e.gate[1], type(H))]
                    with self.subTest(key=str(key)):
                        self.assertEqual(gated, [])
        broken = (P.Coin("coin", count=2), P.Damage(P.OPP, P.Printed(), gate=("coin", H)))
        state = board(mon(BLAINES_TAUROS, (FIRE,) * 3))
        with mock.patch.dict(P.BUILDERS, {E.CoinsHeadsDamageTailsSelfDamage: lambda e: broken}), self.assertRaises(RuntimeError):
            apply_kernel(state, UseAttack(0, 1))

    def test_card_selection_after_coins_is_still_enumerated(self):
        """コインのあとの決定（れんぞくファイヤーボールのトラッシュするカード）は、まとめずにすべての答えを試す（カードの選び方の違いを同じものとみなさない）。
        そのため、炎エネルギー n 枚のれんぞくファイヤーボールは「おもて」k 枚ごとに C(n, k) 通りで、合わせて 2 の n 乗通り（12 枚 4,096 通りまで受け付け、
        13 枚から ``UNSUPPORTED_PREFLIGHT_LIMIT`` のまま。docs 2 章の残る制限）。"""
        _, branches = traced(board(mon(DARK_CHARIZARD, (FIRE,) * 4)), UseAttack(0, 1))
        self.assertEqual(branches, [16])
        play(board(mon(DARK_CHARIZARD, (FIRE,) * 12)), UseAttack(0, 1), [first] * 0)
        assert_stops(self, board(mon(DARK_CHARIZARD, (FIRE,) * 13)), UseAttack(0, 1), "UNSUPPORTED_PREFLIGHT_LIMIT")


class ExeggutorBoundaryTest(unittest.TestCase):
    """たまなげMAX の境界: v0.34 の上限（12 枚まで受け付け、13 枚から ``UNSUPPORTED_PREFLIGHT_LIMIT``）を、上限の数を上げずに解消した。"""

    def test_branches_are_energies_plus_one(self):
        """試す結果の数はエネルギーの数 + 1（12 枚 13 通り・13 枚 14 通り・20 枚 21 通り・40 枚 41 通り）。v0.34 の数え方では 12 枚で 4,096 通り。"""
        for n in (12, 13, 20, 40):
            with self.subTest(n=n):
                state = board(mon(EXEGGUTOR, (GRASS,) * n))
                self.assertEqual(traced(state, UseAttack(0, 1))[1], [n + 1])
                self.assertEqual(traced(state, UseAttack(0, 1), "derived")[1], [n + 1])
        self.assertEqual(traced(board(mon(EXEGGUTOR, (GRASS,) * 12)), UseAttack(0, 1), grouped=False)[1], [4096])
        self.assertEqual(traced(board(mon(EXEGGUTOR, (GRASS,) * 13)), UseAttack(0, 1), grouped=False)[0][1], "UNSUPPORTED_PREFLIGHT_LIMIT")
        self.assertEqual(preflight.MAX_BRANCHES, 4096)  # 上限の数は変えていない

    def test_real_run_flips_every_coin_with_the_same_rng(self):
        """実際の処理はエネルギーの数だけ 1 枚ずつコインを投げ、乱数の使い方・結果・ログは、元の乱数で ``getrandbits(1)`` を枚数回使ったものと同じ
        （先読みの方法によらない）。「おもて」の数 × 20 のダメージ。"""
        for n in (12, 13, 20, 40):
            state = board(mon(EXEGGUTOR, (GRASS,) * n))
            twin = copy.deepcopy(state.rng)
            expected = ["heads" if twin.getrandbits(1) else "tails" for _ in range(n)]
            outcomes = []
            for mode in PREFLIGHT_MODES:
                new = play(state, UseAttack(0, 1), mode=mode)
                outcomes.append(snapshot(new))
                with self.subTest(n=n, mode=mode):
                    self.assertEqual(coins(new, len(state.log)), expected)
                    self.assertEqual(opponent_damage(new, len(state.log)), [expected.count("heads") * 20])
                    self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(twin))
            self.assertTrue(all(o == outcomes[0] for o in outcomes))

    def test_same_result_as_per_coin_processing(self):
        """12 枚（v0.34 でも受け付けた最大）で、まとめる印を外した処理（1 枚ずつの先読み・1 枚ずつの実際の処理）と、結果の状態・乱数・ログが同じ。"""
        state = board(mon(EXEGGUTOR, (GRASS,) * 12))
        with mock.patch.object(P.HeadsTimesAttachedEnergy, "by_heads", False):
            reference = snapshot(play(state, UseAttack(0, 1), mode="derived_full"))
        for mode in PREFLIGHT_MODES:
            with self.subTest(mode=mode):
                self.assertEqual(snapshot(play(state, UseAttack(0, 1), mode=mode)), reference)

    def test_preflight_does_not_change_the_input(self):
        """先読み（どの方法でも）は、渡した状態・乱数・ログを変えない（受け付けても拒否しても）。"""
        cases = [board(mon(EXEGGUTOR, (GRASS,) * 13)), board(mon(BLAINES_TAUROS, (FIRE,) * 3), mon(MACHAMP, (FIGHTING,), damage=80)),
                 board(mon(MISTYS_POLIWHIRL, (WATER,) * 3), mon(METAPOD, prevent_damage=TURN - 1))]
        for state in cases:
            before = snapshot(state)
            for mode in PREFLIGHT_MODES:
                with self.subTest(card=state.cards[state.players[0].active.card].card_id, mode=mode):
                    try:
                        apply_kernel(state, UseAttack(0, 1), preflight=mode)
                    except EngineError:
                        pass
                    self.assertEqual(snapshot(state), before)

    def test_time_and_branches_are_small(self):
        """小さな時間の比べ（再現できる範囲。性能の保証ではない）: 40 枚のまとめた先読みは、v0.34 の数え方の 12 枚（4,096 通り）より速い。"""
        start = time.perf_counter()
        traced(board(mon(EXEGGUTOR, (GRASS,) * 40)), UseAttack(0, 1))
        grouped = time.perf_counter() - start
        start = time.perf_counter()
        traced(board(mon(EXEGGUTOR, (GRASS,) * 12)), UseAttack(0, 1), grouped=False)
        ungrouped = time.perf_counter() - start
        self.assertLess(grouped, ungrouped)


def assert_copy_choice_unsupported(test, opponent):
    """ピッピ（プレイヤー 0）の「ゆびをふる」で ``opponent`` のワザ 0 を選ぶと ``UNSUPPORTED_COPIED_ATTACK``（状態・乱数・ログは変わらず、決定は待ったまま）。
    決定を待つ状態を返す。"""
    state = board(mon(CLEFAIRY, (WATER, WATER, WATER)), opponent)
    waiting = play(state, UseAttack(0, 1))
    d = waiting.decision
    test.assertEqual((d.kind, d.options), ("select_attack", (0, 1)))
    test.assertIn(0, dict(d.context)["unsupported_choices"])
    before = snapshot(waiting)
    with test.assertRaises(UnsupportedError) as raised:
        apply_kernel(waiting, ResolveDecision(0, d.id, (0,)))
    test.assertEqual(raised.exception.code, "UNSUPPORTED_COPIED_ATTACK")
    test.assertEqual(snapshot(waiting), before)
    return waiting


def growl_board(attacker, *, attacker_bench=(RATTATA,)):
    """プレイヤー 0 の ``attacker`` が「きあいだめ」を使い（TURN）、相手のカラカラが「なきつく」を使って（TURN + 1）、TURN + 2 のプレイヤー 0 の番に
    する。ワザを使うポケモンに、p.321 の 2 段階の「数をかける」効果と「へらす」効果がそろう。"""
    state = board(attacker, mon(CUBONE, (FIGHTING,)), bench=attacker_bench)
    focused = play(state, UseAttack(0, 0))
    return play(focused, UseAttack(1, 0))


class DamageCalculationOrderTest(unittest.TestCase):
    """2 部: p.321 の同じ段階の変更効果の計算の順番（``damage.calculate_attack_damage``）。"""

    @classmethod
    def setUpClass(cls):
        pool = load_card_pool()
        cls.attacker, cls.defender = pool.get(LT_SURGES_RATTATA), pool.get(CUBONE)

    def calc(self, base, modifiers, orders=None):
        return calculate_attack_damage(base, self.attacker, self.defender, RULES_2000_02_14, modifiers, orders=orders)

    def test_operations(self):
        """加える（ADD）・その数にする（SET）・数をかける（MULTIPLY。2 以上の整数）を区別する。"""
        self.assertEqual(DamageModifier(2, 2, "x", operation=MULTIPLY).apply(30), 60)
        self.assertEqual(DamageModifier(2, 60, "x", operation=SET).apply(30), 60)
        self.assertEqual(DamageModifier(2, -20, "x", operation=ADD).apply(30), 10)
        for amount in (1, 0, 1.5):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                DamageModifier(2, amount, "x", operation=MULTIPLY)
        with self.assertRaises(ValueError):
            DamageModifier(2, 2, "x", operation="divide")

    def test_order_dependent_step_requires_the_order(self):
        """2 段階に「2 倍」と「−20」: 30 → 40（2 倍が先）か 20（−20 が先）。順番を渡さなければ ``DamageOrderRequired``（選ぶのはワザを使うプレイヤー）。
        順番の番号は集めた順番の並べかえ（辞書順）。"""
        modifiers = (DamageModifier(2, 2, "きあいだめ", operation=MULTIPLY), DamageModifier(2, -20, "なきつく"))
        with self.assertRaises(DamageOrderRequired) as raised:
            self.calc(30, modifiers)
        self.assertEqual((raised.exception.step, raised.exception.chooser, raised.exception.modifiers), (2, "attacker", modifiers))
        self.assertEqual(step_orders(2), ((0, 1), (1, 0)))
        self.assertEqual(len(step_orders(3)), 6)
        self.assertEqual(self.calc(30, modifiers, {2: (0, 1)}).final, 40)
        self.assertEqual(self.calc(30, modifiers, {2: (1, 0)}).final, 20)
        self.assertEqual([m.label for m in self.calc(30, modifiers, {2: (1, 0)}).modifiers], ["なきつく", "きあいだめ"])

    def test_no_decision_when_every_order_gives_the_same_result(self):
        """どの順番でも結果（最終ダメージと 2 段階で終えるか）が同じなら決めさせない: 10 は 2 倍 −20 で 0、−20 2 倍で −20（どちらも 2 段階で 0 以下
        → ダメージを与えない）。効果が 1 つ・加算だけも決めさせない。"""
        modifiers = (DamageModifier(2, 2, "きあいだめ", operation=MULTIPLY), DamageModifier(2, -20, "なきつく"))
        calc = self.calc(10, modifiers)
        self.assertEqual((calc.final, calc.stopped_after_step_2), (0, True))
        self.assertEqual(self.calc(30, modifiers[:1]).final, 60)
        self.assertEqual(self.calc(30, (DamageModifier(5, 10, "プラスパワー"), DamageModifier(7, -20, "ディフェンダー"))).final, 20)

    def test_chooser_follows_the_step(self):
        """順番を選ぶプレイヤーは段階で決まる（2・5・6 段階はワザを使うプレイヤー、7・8 段階は受けるプレイヤー。p.321・SC15）。"""
        for step, chooser in ((2, "attacker"), (5, "attacker"), (6, "attacker"), (7, "defender"), (8, "defender")):
            modifiers = (DamageModifier(step, 50, "a", operation=SET), DamageModifier(step, 10, "b"))
            with self.subTest(step=step), self.assertRaises(DamageOrderRequired) as raised:
                self.calc(30, modifiers)
            self.assertEqual(raised.exception.chooser, chooser)

    def test_invalid_orders_are_rejected(self):
        modifiers = (DamageModifier(2, 2, "きあいだめ", operation=MULTIPLY), DamageModifier(2, -20, "なきつく"))
        for orders in ({2: (0, 0)}, {2: (0,)}, {5: (0, 1)}, {3: (0, 1)}):
            with self.subTest(orders=orders), self.assertRaises(ValueError):
                self.calc(30, modifiers, orders)


class StepOrderDecisionTest(unittest.TestCase):
    """2 部: 順番によって結果が変わる場面で、ダメージの要素が順番の決定（``damage_step_order``）を出す。v0.34 の ``UNSUPPORTED_DAMAGE_STEP_ORDER`` を、
    決定を出せる場面で解消した。"""

    def waiting(self, side=H):
        state = with_coin_results(growl_board(mon(LT_SURGES_RATTATA, (FIRE, FIRE))), side)
        return state, play(state, UseAttack(0, 1))

    def test_heads_gives_a_decision_to_the_attacking_player(self):
        """マチスのコラッタの「きあいだめ」とカラカラの「なきつく」: でんこうせっかの「おもて」30 は、順番で 40 か 20 になるので、ワザを使うプレイヤー（2 段階）
        に決定を出す。選べるものは順番の番号（0: きあいだめ → なきつく、1: なきつく → きあいだめ）。決定の前に投げたコインは 1 枚で、ダメージはまだない。"""
        state, waiting = self.waiting()
        d = waiting.decision
        self.assertEqual((d.kind, d.player, d.options, d.resume, d.min_choices, d.max_choices), (DAMAGE_STEP_ORDER, 0, (0, 1), "attack", 1, 1))
        context = dict(d.context)
        self.assertEqual((context["step"], context["base"], context["permutations"]), (2, 30, ((0, 1), (1, 0))))
        self.assertEqual([(m[0], m[2], m[3]) for m in context["modifiers"]], [("きあいだめ", MULTIPLY, 2), ("カラカラ（reduced_damage_to_source）", ADD, -20)])
        self.assertEqual(kinds(waiting, len(state.log)), ["attack", "coin_flip"])
        self.assertEqual(serialization_problems(waiting), [])
        self.assertEqual(check_invariants(waiting), [])
        results = {}
        for choice, expected in ((0, 40), (1, 20)):
            done = play(waiting, ResolveDecision(0, d.id, (choice,)))
            [damage] = [e for e in events(done, len(waiting.log), "damage") if e.get("target") is None]
            results[choice] = damage
            with self.subTest(choice=choice):
                self.assertEqual(damage["amount"], expected)  # 40 なら HP 40 のカラカラはきぜつする
                self.assertEqual(coins(done, len(waiting.log)), [])  # コインを投げ直さない
        self.assertEqual(results[0]["step_orders"], ((2, ("きあいだめ", "カラカラ（reduced_damage_to_source）")),))
        self.assertEqual(results[1]["step_orders"], ((2, ("カラカラ（reduced_damage_to_source）", "きあいだめ")),))
        self.assertEqual(results[0]["steps"][:3], (("1 基本となる計算", 30), ("2 きあいだめ", 60), ("2 カラカラ（reduced_damage_to_source）", 40)))
        self.assertEqual(results[0]["damage_multiplied"], ((2, state.players[0].active.card, 2),))

    def test_tails_has_no_decision(self):
        """「うら」10 は、どの順番でも 2 段階で 0 以下（ダメージを与えない）なので決めさせない。"""
        state, done = self.waiting(T)
        self.assertIsNone(done.decision)
        [damage] = [e for e in events(done, len(state.log), "damage") if e.get("target") is None]
        self.assertEqual((damage["amount"], damage.get("stopped_after_step_2"), damage.get("step_orders")), (0, True, None))

    def test_invalid_answers_keep_the_decision_waiting(self):
        """不正な答え（相手のプレイヤー・範囲外の番号・2 つ・0 個・古い決定 id）は拒否し、決定はそのまま（状態・乱数・ログが変わらない）。"""
        _, waiting = self.waiting()
        d = waiting.decision
        before = snapshot(waiting)
        for command in (ResolveDecision(1, d.id, (0,)), ResolveDecision(0, d.id, (2,)), ResolveDecision(0, d.id, (0, 1)), ResolveDecision(0, d.id, ()),
                        ResolveDecision(0, d.id + 1, (0,)), UseAttack(0, 1), EndTurn(0)):
            with self.subTest(command=command), self.assertRaises(EngineError):
                apply_kernel(waiting, command)
            self.assertEqual(snapshot(waiting), before)

    def test_resume_after_copy_and_pickle_is_identical(self):
        """決定を待つ状態を複製・pickle で保存して再開しても、結果（形式 10 の全体・乱数・ログ）は同じ。"""
        _, waiting = self.waiting()
        answer = ResolveDecision(0, waiting.decision.id, (1,))
        results = [snapshot(play(s, answer)) for s in (waiting, waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting)))]
        self.assertTrue(all(r == results[0] for r in results))

    def test_preflight_modes_agree(self):
        """先読みの方法（derived・derived_full・legacy）で、決定・答えごとの結果が同じ。"""
        state, _ = self.waiting()
        outcomes = []
        for mode in PREFLIGHT_MODES:
            waiting = play(state, UseAttack(0, 1), mode=mode)
            d = waiting.decision
            outcomes.append((snapshot(waiting), [snapshot(play(waiting, ResolveDecision(0, d.id, (c,)), mode=mode)) for c in d.options]))
        self.assertTrue(all(o == outcomes[0] for o in outcomes))

    def test_raticate_self_damage_is_doubled_without_a_second_decision(self):
        """マチスのラッタ: 相手へのすてみタックル 40 は順番で 60 か 40（決定）。自分への 20 は「きあいだめ」だけ（「なきつく」は受けたポケモンがカラカラに
        与えるダメージだけ）なので、決定なしで 40（「(自分へのダメージも2倍)」）。"""
        state = growl_board(mon(LT_SURGES_RATICATE, (FIRE, FIRE)))
        waiting = play(state, UseAttack(0, 1))
        self.assertEqual(waiting.decision.kind, DAMAGE_STEP_ORDER)
        for choice, expected in ((0, 60), (1, 40)):
            done = play(waiting, ResolveDecision(0, waiting.decision.id, (choice,)))
            with self.subTest(choice=choice):
                self.assertEqual(opponent_damage(done, len(state.log)), [expected])
                [own] = [e for e in events(done, len(state.log), "damage") if e.get("target") == "self"]
                self.assertEqual((own["amount"], own.get("step_orders"), own["damage_multiplied"]), (40, None, ((2, state.players[0].active.card, 2),)))
                self.assertNotEqual(getattr(done.decision, "kind", None), DAMAGE_STEP_ORDER)  # 2 つめの順番の決定はない（HP 40 のカラカラはきぜつする）

    def test_swords_dance_and_growl(self):
        """ストライクの「つるぎのまい」（その数にする 60）と「なきつく」: きりさく 30 は 60 → 40 か 10 → 60。カラカラの弱点（草）で 80 か 120（v0.34 では
        ``UNSUPPORTED_DAMAGE_STEP_ORDER`` で止めていた）。"""
        state = board(mon(CUBONE, (FIGHTING,)), mon(SCYTHER, (GRASS, GRASS, GRASS), next_turn_attack_damage=(TURN - 1, 0, 1, 60)))
        growled = play(state, UseAttack(0, 0))
        waiting = play(growled, UseAttack(1, 1))
        self.assertEqual((waiting.decision.kind, waiting.decision.player), (DAMAGE_STEP_ORDER, 1))
        for choice, expected in ((0, 80), (1, 120)):
            done = play(waiting, ResolveDecision(1, waiting.decision.id, (choice,)))
            with self.subTest(choice=choice):
                self.assertEqual([e["amount"] for e in events(done, len(growled.log), "damage")], [expected])

    def test_broken_decision_is_an_invariant_violation(self):
        """順番の決定の形が場と合わなければ不変条件の違反（選ぶプレイヤー・選べるもの・選べる順番・段階・受けるポケモン・基本となるダメージで順番が
        要らない）。"""
        _, waiting = self.waiting()
        d = waiting.decision

        def with_context(name, value):
            return dataclasses.replace(d, context=tuple((k, value if k == name else v) for k, v in d.context))

        broken = {"player": dataclasses.replace(d, player=1), "options": dataclasses.replace(d, options=(0,)),
                  "permutations": with_context("permutations", ((1, 0), (0, 1))), "step": with_context("step", 5),
                  "receiver": with_context("receiver", waiting.players[0].active.pokemon_id), "base": with_context("base", 10)}
        for name, decision in broken.items():
            with self.subTest(broken=name):
                bad = waiting.clone()
                bad.decision = decision
                self.assertTrue(check_invariants(bad))

    def test_callers_that_cannot_decide_stop_explicitly(self):
        """決定を出せない呼ぶ側（v0.13 の約束の補助関数 ``deal_attack_damage`` など。今の対応カードでは起こらない）は、順番を決めずに問い
        ``damage_step_order``（``UNSUPPORTED_DAMAGE_STEP_ORDER``）で止める。"""
        state, _ = self.waiting()
        sim = state.clone()
        use = open_attack(sim, 0, attack_index=1)
        with self.assertRaises(OpenQuestion) as raised:
            E.deal_attack_damage(sim, use, E.OPPONENT_ACTIVE, 30)
        self.assertEqual(raised.exception.key, "damage_step_order")

    def test_no_decision_without_order_dependence(self):
        """順番で結果が変わらない場面では決定を出さない: 「きあいだめ」だけ（でんこうせっか 60）・「つるぎのまい」だけ・プラスパワーとディフェンダー（別の
        段階の加算）。"""
        state = board(mon(LT_SURGES_RATTATA, (FIRE, FIRE)))
        focused = end(play(state, UseAttack(0, 0)), 1)
        done = play(with_coin_results(focused, H), UseAttack(0, 1))
        self.assertIsNone(done.decision)
        self.assertEqual(opponent_damage(done, len(focused.log)), [60])
        scyther = board(mon(SCYTHER, (GRASS, GRASS, GRASS), next_turn_attack_damage=(TURN - 2, 0, 1, 60)))
        done = play(scyther, UseAttack(0, 1))
        self.assertIsNone(done.decision)
        self.assertEqual(opponent_damage(done, len(scyther.log)), [60])


class FocusEnergyTest(unittest.TestCase):
    """きあいだめ: 次の自分の番、このカードのでんこうせっか（すてみタックル）のダメージは 2 倍（p.321 の 2 段階の「数をかける」効果）。"""

    def focused(self, card=LT_SURGES_RATTATA, **opponent):
        state = board(mon(card, (FIRE, FIRE)), mon(HITMONCHAN, (FIGHTING,), **opponent), hand=(LT_SURGES_RATICATE,))
        return state, play(state, UseAttack(0, 0))

    def test_effect_and_next_own_turn(self):
        """使った番（TURN）に効果を与え、はたらくのは次の自分の番（TURN + 2）だけ。相手の番（TURN + 1）にははたらかない。でんこうせっかの「おもて」30 → 60、
        「うら」10 → 20（弱点・抵抗力はそのあと）。"""
        state, focused = self.focused()
        [added] = events(focused, len(state.log), "persistent_effect_added")
        self.assertEqual((added["persistent_effect"], added["active_turn"]), ("next_turn_attack_damage_multiplier", TURN + 2))
        rattata = focused.players[0].active
        self.assertIsNone(next_turn_attack_damage(focused, rattata, 1))  # 相手の番
        mine = end(focused, 1)
        self.assertIsNotNone(next_turn_attack_damage(mine, mine.players[0].active, 1))
        self.assertIsNone(next_turn_attack_damage(mine, mine.players[0].active, 0))  # きあいだめ自身は変わらない
        for side, expected in ((H, 60), (T, 20)):
            done = play(with_coin_results(mine, side), UseAttack(0, 1))
            with self.subTest(side=side):
                self.assertEqual(opponent_damage(done, len(mine.log)), [expected])

    def test_expires_at_the_end_of_the_next_own_turn(self):
        """次の自分の番に使わなければ、その番の終わりに消え（``expired``）、その次の自分の番（TURN + 4）のでんこうせっかは 2 倍にならない。"""
        _, focused = self.focused()
        mine = end(focused, 1)
        later = end(end(mine, 0), 1)
        removed = [e for e in events(later, len(mine.log), "persistent_effect_removed")]
        self.assertEqual([e["reason"] for e in removed], ["expired"])
        done = play(with_coin_results(later, H), UseAttack(0, 1))
        self.assertEqual(opponent_damage(done, len(later.log)), [30])

    def test_consecutive_use_does_not_stack(self):
        """次の自分の番にもう一度きあいだめを使うと、前の効果はその番の終わりに消え、新しい効果がその次の自分の番にはたらく（2 倍のまま。4 倍にしない）。"""
        _, focused = self.focused()
        again = play(end(focused, 1), UseAttack(0, 0))
        effects = [e for e in again.players[0].active.persistent_effects if isinstance(e, NextTurnAttackDamage)]
        self.assertEqual([e.active_turn for e in effects], [TURN + 4])
        done = play(with_coin_results(end(again, 1), H), UseAttack(0, 1))
        self.assertEqual(opponent_damage(done, len(again.log) + 2), [60])
        self.assertEqual(len(events(done, 0, "persistent_effect_removed")), 2)

    def test_retreat_evolve_and_knock_out_clear_it(self):
        """ベンチにもどる（にげる）・進化・きぜつで消える（v0.4b と同じ消える契機）。進化したマチスのラッタのすてみタックルは 2 倍にならない。"""
        _, focused = self.focused()
        mine = end(focused, 1)
        bench_card = mine.players[0].bench[0].card
        retreated = apply_kernel(mine, Retreat(0, (), bench_card))
        self.assertEqual([e["reason"] for e in events(retreated, len(mine.log), "persistent_effect_removed")], ["retreat"])
        evolved = apply_kernel(mine, EvolvePokemon(0, mine.players[0].hand[0], mine.players[0].active.pokemon_id))
        self.assertEqual([e["reason"] for e in events(evolved, len(mine.log), "persistent_effect_removed")], ["evolve"])
        done = play(evolved, UseAttack(0, 1))
        self.assertEqual((opponent_damage(done, len(evolved.log)), self_damage(done, len(evolved.log))), ([40], [20]))
        state = board(mon(LT_SURGES_RATTATA, (FIRE, FIRE), damage=10), mon(HITMONCHAN, (FIGHTING,)))
        focused = play(state, UseAttack(0, 0))
        knocked = play(focused, UseAttack(1, 0))
        removed = events(knocked, len(focused.log), "persistent_effect_removed")
        self.assertEqual([e["reason"] for e in removed], ["knock_out"])

    def test_raticate_doubles_self_damage(self):
        """マチスのラッタ: 次の自分の番のすてみタックルは、相手へ 40 → 80、自分へ 20 → 40（「(自分へのダメージも2倍)」。自分へのダメージは自分のタイプ・
        自分の弱点・抵抗力で、別に計算する）。"""
        state = board(mon(LT_SURGES_RATICATE, (FIRE, FIRE)), mon(HITMONCHAN, (FIGHTING,)))
        mine = end(play(state, UseAttack(0, 0)), 1)
        done = play(mine, UseAttack(0, 1))
        self.assertEqual((opponent_damage(done, len(mine.log)), self_damage(done, len(mine.log))), ([80], [40]))

    def test_copying_focus_energy_is_unsupported(self):
        """ピッピの「ゆびをふる」で「きあいだめ」を選ぶのは、番をまたぐ効果をワザを使ったポケモンのワザの位置で表せないので、エンジンの未対応（v0.31 の
        「つるぎのまい」と同じ ``UNSUPPORTED_COPIED_ATTACK``。決定の ``unsupported_choices`` に挙げ、選ぶと拒否して決定は待ったまま）。でんこうせっかは選べる。"""
        assert_copy_choice_unsupported(self, mon(LT_SURGES_RATTATA, (FIRE, FIRE)))


class BubblesTest(unittest.TestCase):
    """あわあわ: 20 ダメージのあとコイン。「うら」なら、次の自分の番、このカードは「あわあわ」を使えない（持続する効果 ``CannotUseOwnAttack``）。"""

    def bubbled(self, side, **opponent):
        state = with_coin_results(board(mon(MISTYS_POLIWAG, (WATER, WATER)), mon(HITMONCHAN, (FIGHTING,), **opponent)), side)
        return state, play(state, UseAttack(0, 0))

    def test_tails_locks_bubbles_on_the_next_own_turn_only(self):
        state, done = self.bubbled(T)
        self.assertEqual(opponent_damage(done, len(state.log)), [20])
        [added] = events(done, len(state.log), "persistent_effect_added")
        self.assertEqual((added["persistent_effect"], added["active_turn"], added["target_attack_index"]), ("cannot_use_own_attack", TURN + 2, 0))
        mine = end(done, 1)
        self.assertTrue(attack_locked(mine, mine.players[0].active, 0))
        assert_stops(self, mine, UseAttack(0, 0), "ATTACK_LOCKED", exception=IllegalActionError)
        other = play(mine, UseAttack(0, 1), [first])  # ドわすれは使える
        self.assertEqual(events(other, len(mine.log), "persistent_effect_removed")[0]["reason"], "expired")
        later = end(other, 1)
        self.assertFalse(attack_locked(later, later.players[0].active, 0))
        play(later, UseAttack(0, 0))

    def test_heads_gives_nothing(self):
        state, done = self.bubbled(H)
        self.assertEqual(events(done, len(state.log), "persistent_effect_added"), [])
        self.assertEqual(len(coins(done, len(state.log))), 1)

    def test_coin_is_flipped_against_prevented_damage(self):
        """コインは自分への効果だけを決めるので、「ダメージを受けない」相手にも投げる（相手へのダメージは無効）。"""
        state = with_coin_results(board(mon(MISTYS_POLIWAG, (WATER, WATER)), mon(METAPOD, prevent_damage=TURN - 1)), T)
        done = play(state, UseAttack(0, 0))
        self.assertEqual(len(coins(done, len(state.log))), 1)
        self.assertEqual(len(events(done, len(state.log), "damage_prevented")), 1)
        self.assertEqual(len(events(done, len(state.log), "persistent_effect_added")), 1)

    def test_evolution_clears_the_lock(self):
        evolved_state = build_test_state([{"active": mon(MISTYS_POLIWAG, (WATER, WATER)), "hand": [MISTYS_POLIWHIRL]},
                                          {"active": mon(HITMONCHAN, (FIGHTING,))}], turn_number=TURN)
        bubbled = play(with_coin_results(evolved_state, T), UseAttack(0, 0))
        mine = end(bubbled, 1)
        evolved = apply_kernel(mine, EvolvePokemon(0, mine.players[0].hand[0], mine.players[0].active.pokemon_id))
        self.assertEqual([e["reason"] for e in events(evolved, len(mine.log), "persistent_effect_removed")], ["evolve"])

    def test_copying_bubbles_is_unsupported(self):
        """「あわあわ」をまねるのも未対応（自分への番をまたぐ効果）。v0.36 から「ドわすれ」も未対応（効果 ``CannotUseAttack`` は、効果を与えたワザを効果を
        与えたポケモンのカードのワザの位置で記録するので、まねた効果を表せない。v0.35 は選べて、効果を与えたところで不変条件の違反（内部エラー）になって
        いた。docs/sand-attack-retreat-lock-v0.36.md 5 章）。ニョロモのワザはどちらも処理できないので、ゆびをふるの宣言の前に止まる（状態は変わらない）。"""
        state = board(mon(CLEFAIRY, (WATER, WATER, WATER)), mon(MISTYS_POLIWAG, (WATER, WATER)))
        assert_stops(self, state, UseAttack(0, 1), "UNSUPPORTED_COPIED_ATTACK")


class AmnesiaTest(unittest.TestCase):
    """ドわすれ: ワザを使ったプレイヤーが相手の対戦ポケモンのワザを 1 つ選び、次の相手の番、そのポケモンはそのワザを使えない（``CannotUseAttack``）。"""

    def waiting(self, opponent=None, **kw):
        state = board(mon(MISTYS_POLIWAG, (WATER, WATER)), opponent or mon(HITMONCHAN, (FIGHTING, FIGHTING, FIGHTING)), **kw)
        return state, play(state, UseAttack(0, 1))

    def test_attacker_chooses_an_attack_of_the_top_card(self):
        state, waiting = self.waiting()
        d = waiting.decision
        target = state.players[1].active.pokemon_id
        self.assertEqual((d.kind, d.player, d.options, d.context_value("target")), (SELECT_OPPONENT_ATTACK, 0, (0, 1), target))
        for choice in (0, 1):
            done = play(waiting, ResolveDecision(0, d.id, (choice,)))
            with self.subTest(choice=choice):
                [added] = events(done, len(waiting.log), "persistent_effect_added")
                self.assertEqual((added["persistent_effect"], added["active_turn"], added["target_attack_index"], added["pokemon_id"]),
                                 ("cannot_use_attack", TURN + 1, choice, target))
                assert_stops(self, done, UseAttack(1, choice), "ATTACK_LOCKED", exception=IllegalActionError)
                play(done, UseAttack(1, 1 - choice))

    def test_expires_at_the_end_of_the_next_opponent_turn(self):
        _, waiting = self.waiting()
        done = play(waiting, ResolveDecision(0, waiting.decision.id, (0,)))
        passed = end(done, 1)
        self.assertEqual([e["reason"] for e in events(passed, len(done.log), "persistent_effect_removed")], ["expired"])
        back = end(passed, 0)
        play(back, UseAttack(1, 0))

    def test_switch_and_evolution_clear_it(self):
        """受けたポケモンがベンチにもどる（ポケモンいれかえ）・進化すると消える（v0.4b と同じ消える契機。``target_attack_index`` はいちばん上のカードのワザの位置なので、
        進化したら使えるワザが変わる）。"""
        _, waiting = self.waiting(opponent_hand=(SWITCH,))
        done = play(waiting, ResolveDecision(0, waiting.decision.id, (0,)))
        switched = play(done, PlayTrainer(1, done.players[1].hand[0]), [first])
        self.assertEqual([e["reason"] for e in events(switched, len(done.log), "persistent_effect_removed")], ["switch"])
        state, waiting = self.waiting(mon(NIDORINO, (GRASS, GRASS, GRASS), played_turn=1), opponent_hand=(NIDOKING,))
        done = play(waiting, ResolveDecision(0, waiting.decision.id, (0,)))
        evolved = apply_kernel(done, EvolvePokemon(1, done.players[1].hand[0], done.players[1].active.pokemon_id))
        self.assertEqual([e["reason"] for e in events(evolved, len(done.log), "persistent_effect_removed")], ["evolve"])
        play(with_coin_results(evolved, H), UseAttack(1, 0))

    def test_barrier_and_transparency_prevent_the_choice(self):
        """相手に与える効果なので、選ぶ前に「ワザをうけない」状態・「とうめい」を評価する（受けないなら決定を出さない）。"""
        from tests.test_barrier_resume_coin_bonus_v0_34 import with_barrier

        barred = with_barrier(mon(MISTYS_POLIWAG, (WATER, WATER)))
        done = play(barred, UseAttack(1, 1))
        self.assertIsNone(done.decision)
        self.assertTrue(events(done, len(barred.log), "effect_prevented"))
        state = with_coin_results(board(mon(MISTYS_POLIWAG, (WATER, WATER)), mon(HAUNTER, (PSYCHIC,))), H)
        evaded = play(state, UseAttack(0, 1))
        self.assertIsNone(evaded.decision)
        self.assertEqual(len(events(evaded, len(state.log), "attack_evaded")), 1)
        state = with_coin_results(board(mon(MISTYS_POLIWAG, (WATER, WATER)), mon(HAUNTER, (PSYCHIC,))), T)
        waiting = play(state, UseAttack(0, 1))
        self.assertEqual((waiting.decision.kind, waiting.decision.options), (SELECT_OPPONENT_ATTACK, (0,)))

    def test_invalid_answers_and_pickle(self):
        _, waiting = self.waiting()
        d = waiting.decision
        before = snapshot(waiting)
        for command in (ResolveDecision(1, d.id, (0,)), ResolveDecision(0, d.id, (2,)), ResolveDecision(0, d.id, (0, 1)), ResolveDecision(0, d.id, ())):
            with self.subTest(command=command), self.assertRaises(EngineError):
                apply_kernel(waiting, command)
            self.assertEqual(snapshot(waiting), before)
        answer = ResolveDecision(0, d.id, (1,))
        results = [snapshot(play(s, answer)) for s in (waiting, pickle.loads(pickle.dumps(waiting)))]
        self.assertEqual(results[0], results[1])


class PoliwhirlTest(unittest.TestCase):
    """はかいのうず・ウォーターパンチ。"""

    def test_whirlpool_discards_on_heads_only(self):
        """「おもて」なら、相手についているエネルギーカードを 1 枚、ワザを使ったプレイヤーが選んでトラッシュする（v0.33 の要素の再利用）。「うら」・相手に
        エネルギーカードがなければトラッシュしない（エネルギーカードがなければコインも投げない。p.309）。"""
        state = with_coin_results(board(mon(MISTYS_POLIWHIRL, (WATER, WATER)), mon(HITMONCHAN, (FIGHTING, FIGHTING))), H)
        waiting = play(state, UseAttack(0, 0))
        self.assertEqual((waiting.decision.kind, waiting.decision.player), (DISCARD_OPPONENT_ENERGY, 0))
        done = play(waiting, ResolveDecision(0, waiting.decision.id, first(waiting.decision)))
        self.assertEqual(len(done.players[1].active.energy), 1)
        tails = play(with_coin_results(state, T), UseAttack(0, 0))
        self.assertIsNone(tails.decision)
        self.assertEqual(len(tails.players[1].active.energy), 2)
        empty = board(mon(MISTYS_POLIWHIRL, (WATER, WATER)), mon(HITMONCHAN))
        done = play(empty, UseAttack(0, 0))
        self.assertEqual(coins(done, len(empty.log)), [])

    def test_water_punch_counts_water_energy(self):
        """ウォーターパンチ: ついている「水」エネルギーの数だけコイン（水 2・闘 1 なら 2 枚）。30 +「おもて」の数 × 10。水がなければコインなしで 30。"""
        state = with_coin_results(board(mon(MISTYS_POLIWHIRL, (WATER, FIGHTING, WATER))), H, T)
        done = play(state, UseAttack(0, 1))
        self.assertEqual((coins(done, len(state.log)), opponent_damage(done, len(state.log))), (["heads", "tails"], [40]))
        dry = board(mon(MISTYS_POLIWHIRL, (FIGHTING, FIGHTING, FIGHTING)))
        done = play(dry, UseAttack(0, 1))
        self.assertEqual((coins(done, len(dry.log)), opponent_damage(done, len(dry.log))), ([], [30]))
        self.assertEqual(traced(board(mon(MISTYS_POLIWHIRL, (WATER,) * 6)), UseAttack(0, 1))[1], [7])

    def test_water_punch_against_prevented_damage_is_v0_4b(self):
        """コインはダメージの量だけを決めるので、「ダメージを受けない」相手には v0.4b の ``UNRESOLVED_PREVENTED_COIN_DAMAGE``（水がなくコインを投げない
        ときは止めない）。"""
        assert_stops(self, board(mon(MISTYS_POLIWHIRL, (WATER,) * 3), mon(METAPOD, prevent_damage=TURN - 1)), UseAttack(0, 1),
                     "UNRESOLVED_PREVENTED_COIN_DAMAGE")
        play(board(mon(MISTYS_POLIWHIRL, (FIGHTING,) * 3), mon(METAPOD, prevent_damage=TURN - 1)), UseAttack(0, 1))


class BlainesTaurosTest(unittest.TestCase):
    """3ぼんのしっぽ（コイン 3 枚の「おもて」の数 × 10）・ぜんりょくとっしん（同じ 4 枚のコインの「おもて」の数 × 20 を相手、「うら」の数 × 20 を自分）。"""

    def test_three_tails(self):
        state = with_coin_results(board(mon(BLAINES_TAUROS, (FIRE,))), H, T, H)
        done = play(state, UseAttack(0, 0))
        self.assertEqual((len(coins(done, len(state.log))), opponent_damage(done, len(state.log))), (3, [20]))

    def test_full_speed_charge_uses_one_set_of_coins(self):
        """4 枚を 1 回投げる（別々に投げない）。相手へのダメージ → 自分へのダメージ（説明の「その後」）。"""
        cases = [((H, T, H, T), [40], [40]), ((H, H, H, H), [80], [0]), ((T, H, T, T), [20], [60])]
        for sides, opponent, own in cases:
            state = with_coin_results(board(mon(BLAINES_TAUROS, (FIRE,) * 3)), *sides)
            done = play(state, UseAttack(0, 1))
            with self.subTest(sides=sides):
                self.assertEqual(len(coins(done, len(state.log))), 4)
                self.assertEqual(opponent_damage(done, len(state.log)), opponent)
                self.assertEqual(self_damage(done, len(state.log)), own)
                order = [e.get("target") for e in events(done, len(state.log), "damage")]
                self.assertEqual(order, [None, "self"])

    def test_all_tails_knocks_out_tauros_itself(self):
        """「うら」4 枚: 相手へのダメージは 0（与えなかった）、自分へ 80 で HP 70 のケンタロスがきぜつする（自分のワザのダメージ。相手がサイドを取る）。"""
        state = with_coin_results(board(mon(BLAINES_TAUROS, (FIRE,) * 3)), T, T, T, T)
        done = play(state, UseAttack(0, 1))
        self.assertEqual([e["pokemon"] for e in events(done, len(state.log), "knock_out")], [state.players[0].active.card])

    def test_flips_against_prevented_damage(self):
        """コインは自分へのダメージも決めるので、「ダメージを受けない」相手にも投げる（相手へのダメージは無効、自分へのダメージは与える）。"""
        state = with_coin_results(board(mon(BLAINES_TAUROS, (FIRE,) * 3), mon(METAPOD, prevent_damage=TURN - 1)), H, T, T, H)
        done = play(state, UseAttack(0, 1))
        self.assertEqual(len(coins(done, len(state.log))), 4)
        self.assertEqual(len(events(done, len(state.log), "damage_prevented")), 1)
        self.assertEqual(self_damage(done, len(state.log)), [40])


class PreflightParityTest(unittest.TestCase):
    def test_every_attack_agrees_across_preflight_modes(self):
        """10 のワザのどれも、先読みの方法（derived・derived_full・legacy）で、受け付けるか・拒否のコード・結果（形式 10・乱数）が同じ（コインの両方の
        結果で。決定には最初の選べるもので答える）。v0.35 の型は v013_checks.VERIFIED に入れていないので、legacy でもすべての結果を試す。"""
        energy = {LT_SURGES_RATTATA: (FIRE, FIRE), LT_SURGES_RATICATE: (FIRE, FIRE), MISTYS_POLIWAG: (WATER, WATER),
                  MISTYS_POLIWHIRL: (WATER, WATER, FIGHTING), BLAINES_TAUROS: (FIRE, FIRE, FIRE)}
        for card in V0_35_POKEMON:
            for attack in load_card_pool().get(card).attacks:
                for side in (H, T):
                    state = with_coin_results(board(mon(card, energy[card]), mon(HITMONCHAN, (FIGHTING, FIGHTING))), *(side,) * 4)
                    results = []
                    for mode in PREFLIGHT_MODES:
                        try:
                            new = play(state, UseAttack(0, attack.index), mode=mode)
                            while new.decision is not None and new.decision.resume == "attack":
                                new = play(new, ResolveDecision(new.decision.player, new.decision.id, first(new.decision)), mode=mode)
                            results.append((full(new), rng_fingerprint(new.rng)))
                        except EngineError as error:
                            results.append(("rejected", error.code))
                    with self.subTest(card=card, attack=attack.name_ja, side=side):
                        self.assertTrue(all(r == results[0] for r in results))
                        self.assertNotEqual(results[0][0], "rejected")


class DocumentTest(unittest.TestCase):
    def test_document_records_the_changes(self):
        text = DOC.read_text(encoding="utf-8")
        for word in ("たまなげMAX", "ウォーターパンチ", "ぜんりょくとっしん", "れんぞくファイヤーボール", "UNSUPPORTED_DAMAGE_STEP_ORDER", "damage_step_order",
                     "きあいだめ", "あわあわ", "ドわすれ", "はかいのうず", "3ぼんのしっぽ", "ガルーラ", "CD4", "UNSUPPORTED_PREFLIGHT_LIMIT"):
            with self.subTest(word=word):
                self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()

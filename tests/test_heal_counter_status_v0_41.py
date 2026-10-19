"""v0.41: 回復・ダメージカウンターの移動・特殊状態の変化を中心とする 15 枚（docs/heal-counter-status-v0.41.md）。

クサイハナ（PMCG2-009）・ウツボット（PMCG2-016）・シードラ（PMCG3-020）・わるいペルシアン（PMCG4-048）・カツラのファイヤー（PMCG6-035）・ヤドン（PMCG4-032）・
エリカのナゾノクサ（PMCG5-002・PMCG5-003）・エリカのクサイハナ（PMCG5-009）・ナツメのコダック（PMCG6-036）・ナツメのゴルダック（PMCG6-038）・
ナツメのモルフォン（PMCG6-022）・ナツメのヤドラン（PMCG6-048）・エリカのプリン（PMCG5-058）・R団のミュウツー（PMCG6-055）。どれも kyuura データの採用
（処理に使う文面は kyuura の印刷の文面。採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合。ガイドブックは読んでいない。

根拠にした既存の記録（kyuura の研究の基準のコミット 3f34908 の一般の規定・裁定）: GR-2000-P320-RECOVERY（回復はダメージカウンターをとりのぞくこと・とりのぞいたら
それ以上の回復はできない）・GR-2000-P320-COUNTER-MOVE（ダメージカウンターの移動は「ダメージを受けた」ことにならない。エンジンの v0.7 の S19）・
GR-2000-P321-PREVENTED-ELEMENTS（「ダメージを受けない」状態は、ダメージの要素だけを無効にする）・GR-2000-P309-ATTACK-PROCEDURE（書かれた順に処理し、処理の
対象がいなくなった内容は無視して次の内容を処理する）・GR-2000-P323-KNOCKOUT（1 つのワザによるきぜつは同時）・CR-COUNTERATTACK-TIMING（「ダメージを受けたとき」の
効果は、ダメージの処理のあと・ダメージ以外の効果（効果を決めるコインを含む）の前）と、エンジンの v0.9（とうめい。T4・T8・T27）・v0.11（こんじょう。G3〜G7）・
v0.31（バリアー・HC3・HC4・HC9）・v0.36（RD9・CannotRetreat）・v0.17b（Z23）の記録。新しい未解決は CX1（``UNRESOLVED_COUNTER_TRANSFER_PROTECTED``）だけ。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import unittest
from typing import ClassVar
from unittest import mock

from kyuura_engine import (
    EndTurn,
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    ResolveDecision,
    Retreat,
    UnsupportedError,
    UseAttack,
    check_invariants,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, read_extract
from kyuura_engine.conditions import CONFUSION, PARALYSIS, POISON, SLEEP
from kyuura_engine.decisions import ATTACH_FROM_DECK, FORCED_SWITCH, KO_PREVENTION, PROMOTE_ACTIVE, SELECT_ATTACK, SELECT_SPECIAL_CONDITION, TAKE_PRIZE
from kyuura_engine.errors import UnsupportedError as Unsupported
from kyuura_engine.resolution import PREFLIGHT_MODES, programs, v013_checks
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import CannotRetreat, CannotUseOwnAttack
from scripts import check_card_sources as cs
from scripts.extract_kyuura_cards import PREVIOUS_KYUURA_COMMIT as ADOPTED_COMMIT  # v0.69: 採用したときのデータのコミット（採用の記録は書き換えない）
from tests.helpers import (
    V0_69_STOP_CODE_ISSUES,
    kyuura_records_since_v0_69,
    ATTACK_TYPES_SINCE_V0_17,
    BELLSPROUT,
    BLAINES_MOLTRES,
    BULBASAUR,
    CHARMANDER,
    CLEFABLE,
    CLEFAIRY,
    DARK_PERSIAN,
    DEFENDER,
    ERIKAS_BELLSPROUT,
    ERIKAS_GLOOM,
    ERIKAS_JIGGLYPUFF,
    ERIKAS_ODDISH,
    ERIKAS_ODDISH_40,
    ERIKAS_WEEPINBELL,
    FIGHTING,
    FIRE,
    GASTLY,
    GIOVANNIS_MACHAMP,
    GIOVANNIS_MACHOKE,
    GIOVANNIS_MACHOP,
    GIOVANNIS_MEOWTH,
    GIOVANNIS_NIDOKING,
    GIOVANNIS_NIDORAN_M,
    GIOVANNIS_NIDORINO,
    GLOOM,
    GRASS,
    HAUNTER,
    HITMONCHAN,
    HORSEA,
    JIGGLYPUFF,
    JUNGLE_ODDISH,
    LIGHTNING,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MEOWTH,
    MEWTWO,
    MISTYS_HORSEA,
    MISTYS_PSYDUCK,
    MISTYS_SEADRA,
    MOLTRES,
    PERSIAN,
    PLUSPOWER,
    PSYCHIC,
    PSYDUCK,
    RATTATA,
    ROCKET_ODDISH,
    ROCKET_SLOWPOKE,
    ROCKETS_MEWTWO,
    ROCKETS_MOLTRES,
    SABRINAS_GOLDUCK,
    SABRINAS_PSYDUCK,
    SABRINAS_SLOWBRO,
    SABRINAS_SLOWPOKE,
    SABRINAS_VENOMOTH,
    SABRINAS_VENONAT,
    SEADRA,
    SLOWPOKE,
    V0_41_POKEMON,
    VICTREEBEL,
    WATER,
    WEEPINBELL,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.test_barrier_resume_coin_bonus_v0_34 import assert_stops, events, first, full, play

ROOT = pathlib.Path(__file__).resolve().parent.parent
TURN = 7
DOC = ROOT / "docs" / "heal-counter-status-v0.41.md"
F, W, G, P, R, L = FIGHTING, WATER, GRASS, PSYCHIC, FIRE, LIGHTNING
BELOW = {GLOOM: JUNGLE_ODDISH, VICTREEBEL: [BELLSPROUT, WEEPINBELL], SEADRA: HORSEA, DARK_PERSIAN: MEOWTH, ERIKAS_GLOOM: ERIKAS_ODDISH,
         SABRINAS_GOLDUCK: SABRINAS_PSYDUCK, SABRINAS_VENOMOTH: SABRINAS_VENONAT, SABRINAS_SLOWBRO: SABRINAS_SLOWPOKE, HAUNTER: GASTLY,
         MACHAMP: [MACHOP, MACHOKE], GIOVANNIS_MACHAMP: [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], CLEFABLE: CLEFAIRY,
         GIOVANNIS_NIDOKING: [GIOVANNIS_NIDORAN_M, GIOVANNIS_NIDORINO]}
# どのワザも使えるエネルギー（無色は別のタイプで払う。シードラの「みずでっぽう」は「水」1 つ・ほか 2 つで、HC4 にならない）
ENERGY = {GLOOM: (G, G), VICTREEBEL: (G, G), SEADRA: (W, F, F), DARK_PERSIAN: (F, F), BLAINES_MOLTRES: (R,) * 5, ROCKET_SLOWPOKE: (P,),
          ERIKAS_ODDISH: (G, F), ERIKAS_ODDISH_40: (G,), ERIKAS_GLOOM: (G, G, G), SABRINAS_PSYDUCK: (P,), SABRINAS_GOLDUCK: (P, P, W),
          SABRINAS_VENOMOTH: (G, P), SABRINAS_SLOWBRO: (P, F, F), ERIKAS_JIGGLYPUFF: (F, F), ROCKETS_MEWTWO: (P, P, P, F)}
# 登録の実装の型と値（カード id, ワザの位置）
EXPECTED = {
    (GLOOM, 0): (E.PoisonWithoutDamage, {}),
    (GLOOM, 1): (E.DamageThenConfuseBoth, {}),
    (VICTREEBEL, 0): (E.SwitchOpponentActive, {}),
    (VICTREEBEL, 1): (E.DamageThenRetreatLockOnHeads, {}),
    (SEADRA, 0): (E.ExtraEnergyDamageMixed, {"energy_type": EnergyType.WATER, "per_energy": 10, "max_extra": 2}),
    (SEADRA, 1): (E.DamageThenSelfBarrierOnHeads, {}),
    (DARK_PERSIAN, 0): (E.SwitchOpponentActiveOnHeads, {}),
    (DARK_PERSIAN, 1): (E.PoisonOnHeads, {}),
    (BLAINES_MOLTRES, 0): (E.DamageThenReturnSelfToDeckOnTails, {}),
    (ROCKET_SLOWPOKE, 0): (E.AttachEnergyFromDeckToSelf, {"energy_type": EnergyType.PSYCHIC}),
    (ROCKET_SLOWPOKE, 1): (E.DamageOnly, {}),
    (ERIKAS_ODDISH, 0): (E.DamageThenHealSelf, {"counters": 1, "on_heads": False}),
    (ERIKAS_ODDISH, 1): (E.DamageThenHealSelf, {"counters": 1, "on_heads": True}),
    (ERIKAS_ODDISH_40, 0): (E.DamageThenStatusByCoin, {"heads": CONFUSION, "tails": SLEEP}),
    (ERIKAS_GLOOM, 0): (E.CoinHealSelf, {"counters": 4, "then_sleep": False}),
    (ERIKAS_GLOOM, 1): (E.DamageThenChosenStatusOnHeads, {}),
    (SABRINAS_PSYDUCK, 0): (E.DamageOnly, {}),
    (SABRINAS_PSYDUCK, 1): (E.CoinDamageAndConfuseElseSelfConfuse, {}),
    (SABRINAS_GOLDUCK, 0): (E.MoveOwnCountersToOpponent, {}),
    (SABRINAS_GOLDUCK, 1): (E.CoinBonusDamage, {"bonus": 20}),
    (SABRINAS_VENOMOTH, 0): (E.CoinsHealOwnPokemon, {"coins": 3}),
    (SABRINAS_VENOMOTH, 1): (E.DamageThenConfuseOnAnyHeads, {"coins": 2}),
    (SABRINAS_SLOWBRO, 0): (E.CoinHealSelf, {"counters": 3, "then_sleep": True}),
    (SABRINAS_SLOWBRO, 1): (E.DamageThenLockSelf, {}),
    (ERIKAS_JIGGLYPUFF, 0): (E.HealAllPokemonBothSides, {"counters": 1}),
    (ERIKAS_JIGGLYPUFF, 1): (E.DamageMinusIfDefenderDamaged, {"reduction": 30}),
    (ROCKETS_MEWTWO, 0): (E.SwapCountersOnHeads, {}),
    (ROCKETS_MEWTWO, 1): (E.DamageThenSleepOnHeads, {}),
    (ROCKETS_MEWTWO, 2): (E.DamageOnly, {}),
}
NEW_TYPES = {E.DamageThenHealSelf, E.CoinHealSelf, E.CoinsHealOwnPokemon, E.HealAllPokemonBothSides, E.MoveOwnCountersToOpponent, E.SwapCountersOnHeads,
             E.DamageThenConfuseBoth, E.DamageThenStatusByCoin, E.DamageThenChosenStatusOnHeads, E.CoinDamageAndConfuseElseSelfConfuse,
             E.DamageThenConfuseOnAnyHeads, E.DamageThenSleepOnHeads, E.DamageThenRetreatLockOnHeads, E.SwitchOpponentActiveOnHeads,
             E.DamageThenReturnSelfToDeckOnTails, E.AttachEnergyFromDeckToSelf, E.DamageThenLockSelf, E.DamageMinusIfDefenderDamaged}
# pcg-search.com の対象の版（サイトの一覧の番号。kyuura の id の番号とは違うことがある）と、違いのあった欄
EDITIONS = {GLOOM: "006/048", VICTREEBEL: "014/048", SEADRA: "019/048", DARK_PERSIAN: "048/065", BLAINES_MOLTRES: "035/098", ROCKET_SLOWPOKE: "034/065",
            ERIKAS_ODDISH: "006/096", ERIKAS_ODDISH_40: "005/096", ERIKAS_GLOOM: "007/096", SABRINAS_PSYDUCK: "037/098", SABRINAS_GOLDUCK: "038/098",
            SABRINAS_VENOMOTH: "004/098", SABRINAS_SLOWBRO: "048/098", ERIKAS_JIGGLYPUFF: "064/096", ROCKETS_MEWTWO: "043/098"}
DIFFERENCES = {SEADRA: ["pokemon.attacks[0].text.ja"]}


def mon(card, energy=None, **extra):
    spec = {"card": card, "energy": list(ENERGY.get(card, ()) if energy is None else energy), **extra}
    if BELOW.get(card) is not None and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), deck=None, hand=(), opponent_hand=(), turn=TURN):
    def spec(b):
        return mon(b, ()) if isinstance(b, str) and b in BELOW else b

    me = {"active": active, "bench": [spec(b) for b in bench], "hand": list(hand)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (F, F)), "bench": [spec(b) for b in opponent_bench], "hand": list(opponent_hand)}
    return build_test_state([me, them], turn_number=turn)


def snapshot(state):
    return full(state), rng_fingerprint(state.rng), [dict(e) for e in state.log]


def attack(state, index, *sides, answers=(), player=0, mode="derived"):
    return play(with_coin_results(state, *sides), UseAttack(player, index), answers, mode=mode)


def pid_of(state, player, card):
    """プレイヤー ``player`` の場の ``card``（カード id）のポケモンの番号（最初の 1 匹）。"""
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card)


def damage_of(state, player, card):
    return next(p.damage for p in state.players[player].in_play() if state.cards[p.card].card_id == card)


def card_of(state, player, card, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card)


def assert_rejected(test, state, command, code, exception=EngineError):
    before = snapshot(state)
    with test.assertRaises(exception) as raised:
        apply_kernel(state, command)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def card_count(state, player):
    """プレイヤーのカードの枚数（ゾーンのすべて。カードの保存則）。"""
    p = state.players[player]
    in_play = sum(len(x.cards()) + len(x.energy) + len(x.trainers) for x in p.in_play())
    return len(p.hand) + len(p.deck) + len(p.discard) + len(p.prizes) + in_play


def answer(state, choices):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)))


def condition_of(state, player):
    return state.players[player].active.conditions


def haunter(**extra):
    return mon(HAUNTER, (), **extra)


class CardDataTest(unittest.TestCase):
    """15 枚の登録・写し・採用の記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_fifteen_requested_cards(self):
        """対象は依頼の 15 枚（ほかの候補に広げていない）。写しの組 pool_v0_41 は 15 枚で、どれも対戦に使える。同じ名前の別のカード（エリカのナゾノクサ 2 枚・
        ロケット団のヤドンと化石の秘密のヤドン）は別の id・別のワザ。名前の似た別のカード（クサイハナとエリカのクサイハナ・シードラとカスミのシードラ・
        わるいペルシアンとペルシアン・カツラのファイヤーとファイヤー・R団のファイヤー・ナツメのコダックとコダック・カスミのコダック・エリカのプリンとプリン・
        R団のミュウツーとミュウツー）は別の名前。"""
        self.assertEqual(len(V0_41_POKEMON), 15)
        self.assertEqual(list(read_extract()["pool_v0_41"]), list(V0_41_POKEMON))
        for card in V0_41_POKEMON:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))
                self.assertEqual(self.pool.get(card).powers, ())
        for ours, other in ((ERIKAS_ODDISH, ERIKAS_ODDISH_40), (ROCKET_SLOWPOKE, SLOWPOKE)):
            with self.subTest(card=ours, other=other):
                self.assertEqual(self.pool.get(ours).name_ja, self.pool.get(other).name_ja)
                self.assertNotEqual([a.name_ja for a in self.pool.get(ours).attacks], [a.name_ja for a in self.pool.get(other).attacks])
        self.assertEqual((self.pool.get(ERIKAS_ODDISH).hp, self.pool.get(ERIKAS_ODDISH_40).hp), (50, 40))
        for ours, other in ((GLOOM, ERIKAS_GLOOM), (SEADRA, MISTYS_SEADRA), (DARK_PERSIAN, PERSIAN), (BLAINES_MOLTRES, MOLTRES),
                            (BLAINES_MOLTRES, ROCKETS_MOLTRES), (SABRINAS_PSYDUCK, PSYDUCK), (SABRINAS_PSYDUCK, MISTYS_PSYDUCK),
                            (ERIKAS_JIGGLYPUFF, JIGGLYPUFF), (ROCKETS_MEWTWO, MEWTWO)):
            with self.subTest(card=ours, other=other):
                self.assertNotEqual(self.pool.get(ours).name_ja, self.pool.get(other).name_ja)

    def test_every_attack_is_registered_with_the_expected_implementation(self):
        """29 のワザがどれも登録され、型と値が説明に合う。説明文のあるワザは、写しの文面（照合用）と処理に使う文面（kyuura の印刷の文面）が同じ。"""
        attacks = [(card, a.index) for card in V0_41_POKEMON for a in self.pool.get(card).attacks]
        self.assertEqual(sorted(attacks), sorted(EXPECTED))
        self.assertEqual(len(attacks), 29)
        for (card, index), (cls, values) in EXPECTED.items():
            with self.subTest(card=card, index=index):
                entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
                self.assertIs(type(entry.effect), cls)
                for name, value in values.items():
                    self.assertEqual(getattr(entry.effect, name), value)
                printed = self.pool.get(card).attacks[index]
                self.assertEqual(entry.name_ja, printed.name_ja)
                self.assertEqual(entry.text_ja, printed.text_ja)
                if printed.text_ja:
                    self.assertEqual(entry.play_text_ja, printed.text_ja)
                self.assertEqual(entry.effect.check(printed), [])

    def test_new_types_are_kernel_programs_outside_the_v013_contract(self):
        """v0.41 の型（18）は解決の基盤の要素の並び（``programs.BUILDERS``）で処理し、v0.13 の約束（``resolve``・``resume``）を上書きしない。``v013_checks.VERIFIED``
        に入れない（tests/helpers.py の ``ATTACK_TYPES_SINCE_V0_17`` に加えた）。"""
        self.assertEqual(len(NEW_TYPES), 18)
        for cls in NEW_TYPES:
            with self.subTest(cls=cls.__name__):
                self.assertIn(cls, programs.BUILDERS)
                self.assertIn(cls, ATTACK_TYPES_SINCE_V0_17)
                self.assertNotIn(cls, v013_checks.VERIFIED)
                self.assertIs(cls.resolve, E.AttackEffect.resolve)
                self.assertIs(cls.resume, E.AttackEffect.resume)

    def test_opponent_effect_elements_match_the_programs(self):
        """実装が宣言する相手の対戦ポケモンへの効果の要素（G37 の確かめに使う）は、要素の並びの相手への効果と同じ。"""
        for (card, index), _ in EXPECTED.items():
            effect = E.DEFAULT_EFFECTS.attack_entry(card, index).effect
            with self.subTest(card=card, index=index):
                program = programs.BUILDERS[type(effect)](effect)
                self.assertEqual(set(effect.opponent_effect_elements), set(programs.opponent_effect_elements(program)))

    def test_adoption_records_and_external_checks(self):
        """15 枚はどれも kyuura データの採用の記録（写しの元のコミット・説明文のあるワザの処理に使う文面の根拠）を持ち、pcg-search.com の同じ版のページと照合した。
        違いはシードラの「みずでっぽう」のかっこ（全角・半角）だけで、処理に影響しない。同じ名前のエリカのナゾノクサは、HP とワザでサイトの版（005/096 は
        HP 40、006/096 は HP 50）を決めた。研究の基準のコミットで 15 枚を指す kyuura の記録はない（カツラのファイヤーは CC-PMCG5-020-P82 の not_confused_with に
        名前が出るだけ）。過去の原典照合の記録には入れない。"""
        sources = cs.load_sources()["cards"]
        verification = json.loads((ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8"))["cards"]
        links = cs.load_links()["latest_descriptions"]["adopted_printed_text"]
        for card in V0_41_POKEMON:
            with self.subTest(card=card):
                record = sources[card]
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"]),
                                 ("kyuura_data", "adopted", ADOPTED_COMMIT, kyuura_records_since_v0_69(card)))  # v0.69: 研究の基準を上げて加わった kyuura の記録（tests/helpers.py の V0_69_KYUURA_RECORDS_ADDED）
                with_text = {f"attack/{a.index}" for a in self.pool.get(card).attacks if a.text_ja}
                self.assertEqual(set(record["play_text"]), with_text)
                self.assertTrue(all(v == "kyuura_printed_text" for v in record["play_text"].values()))
                self.assertTrue(with_text <= {k.split("/", 1)[1] for k in links if k.startswith(card + "/")})
                [check] = record["external_checks"]
                self.assertEqual(check["site"], "pcg-search.com")
                self.assertEqual(check["edition"]["list_number"], EDITIONS[card])
                if card in DIFFERENCES:
                    self.assertEqual(check["result"], "differences")
                    self.assertEqual([d["field"] for d in check["differences"]], DIFFERENCES[card])
                    self.assertFalse(any(d["affects_behavior"] for d in check["differences"]))
                else:
                    self.assertEqual((check["result"], check["differences"]), ("match", []))
                self.assertNotIn(card, verification)

    def test_no_card_specific_branch_in_the_engine(self):
        """engine.py・resolution/ に v0.41 のカード id での分岐を加えていない（効果の型と要素の項目で表す）。"""
        for path in [ROOT / "kyuura_engine" / "engine.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]:
            text = path.read_text(encoding="utf-8")
            for card in V0_41_POKEMON:
                with self.subTest(path=path.name, card=card):
                    self.assertNotIn(card, text)

    def test_cx1_is_the_only_new_stop_code_and_existing_questions_are_reused(self):
        """CX1（相手がダメージカウンターをのせる・取り替える効果を受けないとき、自分の側を処理するか）は新しい停止コード 1 つ。研究の対応表では kyuura の未解決の
        一覧にない（not_in_kyuura）。ほかは既存の問い（Z23・RD9・T19b・HC3・HC4・HC9・T27・v0.3b のマヒの再付与・v0.4b）を使う。"""
        question = QUESTIONS["counter_transfer_protected"]
        self.assertEqual((question.code, question.rulings), ("UNRESOLVED_COUNTER_TRANSFER_PROTECTED", ("CX1",)))
        codes = {q.code for q in QUESTIONS.values()}
        for code in ("UNRESOLVED_EFFECT_AFTER_NO_DAMAGE", "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT", "UNRESOLVED_EVADED_EFFECT_COIN",
                     "UNRESOLVED_PREVENTED_EFFECT_COIN", "UNRESOLVED_EXTRA_ENERGY_COLORLESS", "UNRESOLVED_TRANSPARENCY_COIN_ORDER",
                     "UNRESOLVED_REPARALYSIS_RECOVERY_TURN"):
            self.assertIn(code, codes)
        entry = cs.load_links()["stop_codes"]["UNRESOLVED_COUNTER_TRANSFER_PROTECTED"]
        self.assertEqual((entry["kyuura_disposition"], entry["kyuura_issue"]), ("issue", V0_69_STOP_CODE_ISSUES["UNRESOLVED_COUNTER_TRANSFER_PROTECTED"]))  # v0.69: kyuura が論点に結んだ（v0.68 までは not_in_kyuura。tests/helpers.py の V0_69_STOP_CODE_ISSUES）
        self.assertEqual(entry["engine_rulings"][0]["ruling_id"], "CX1")


class TextTest(unittest.TestCase):
    """既存の型が受け付ける書き方（v0.37 の約束。意味が同じと記録で確かめた書き方だけ）。"""

    def attack(self, text, damage=None, modifier=None, cost=(EnergyType.GRASS,), name="ワザ"):
        from kyuura_engine.cards import Attack

        return Attack(index=0, name_ja=name, name_en="", cost=tuple(cost), damage=damage, damage_modifier=modifier,
                      damage_display=None if damage is None else f"{damage}{modifier or ''}", text_ja=text, text_en=None,
                      supported=True, unsupported_reason=None)

    def test_switch_opponent_active_accepts_both_ways_of_writing(self):
        """かどわかす（「選んで」）とさそうかおり（「選び」）は同じ型。相手が選ぶ・入れ替えない書き方は受け付けない（v0.40 までは形だけを確かめていた）。"""
        effect = E.SwitchOpponentActive()
        for text in E.SWITCH_OPPONENT_ACTIVE_TEXTS:
            self.assertEqual(effect.check(self.attack(text)), [])
        for text in ("相手の控えポケモンを相手が選び、相手の対戦ポケモンと入れ替える。", "自分の控えポケモンを選び、自分の対戦ポケモンと入れ替える。"):
            self.assertTrue(effect.check(self.attack(text)))

    def test_seadra_agility_is_the_attack_barrier(self):
        """「ワザによるダメージや効果を受けない」は、v0.37 のしんだふり（``SelfBarrierOnHeads``）と同じ書き方で、ギャロップの「こうそくいどう」と同じ効果。"""
        effect = E.DamageThenSelfBarrierOnHeads()
        self.assertEqual(effect.check(self.attack("コインを投げて「おもて」なら、このカードは次の相手の番に、ワザによるダメージや効果を受けない。", 20)), [])
        for text in ("コインを投げて「おもて」なら、このカードは次の相手の番に、ワザによるダメージを受けない。",
                     "コインを投げて「うら」なら、このカードは次の相手の番に、ワザによるダメージや効果を受けない。"):
            self.assertTrue(effect.check(self.attack(text, 20)))

    def test_seadra_water_gun_is_the_existing_extra_energy_type(self):
        """シードラの「みずでっぽう」は v0.31 の ``ExtraEnergyDamageMixed``（必要なエネルギーに無色。HC4）。追加の数・上限の違う書き方は受け付けない。"""
        effect = E.ExtraEnergyDamageMixed(EnergyType.WATER, 10, 2)
        cost = (EnergyType.WATER, EnergyType.COLORLESS)
        ok = "ワザに必要なぶんよりも多く「水」エネルギーカードがついている時、多いエネルギー1つにつき10ダメージを追加する。（ダメージ追加は2つぶんまで）"
        self.assertEqual(effect.check(self.attack(ok, 20, "+", cost)), [])
        self.assertTrue(effect.check(self.attack(ok.replace("10ダメージ", "20ダメージ"), 20, "+", cost)))
        self.assertTrue(effect.check(self.attack(ok.replace("2つぶん", "3つぶん"), 20, "+", cost)))

    def test_new_types_reject_other_texts(self):
        """新しい型は、登録したワザの印刷の文面だけを受け付ける（数・面・対象の違う書き方は受け付けない）。"""
        cases = [
            (E.DamageThenHealSelf(1), "自分にのっているダメージカウンターを、2つとりのぞく。", 10),
            (E.DamageThenHealSelf(1), "ダメージを与えたら、自分にのっているダメージカウンターを、1つとりのぞく。", 10),
            (E.CoinHealSelf(4), "コインを投げて「うら」なら、自分にのっているダメージカウンターを、4つとりのぞく。", None),
            (E.CoinHealSelf(3, then_sleep=True), "コインを投げて「おもて」なら、自分にのっているダメージカウンターを3つとりのぞく。", None),
            (E.DamageThenConfuseBoth(), "相手を「こんらん」状態にする。", 20),
            (E.DamageThenStatusByCoin(CONFUSION, SLEEP), "コインを投げて「おもて」なら、相手を「ねむり」状態に、「うら」なら「こんらん」状態にする。", 10),
            (E.DamageThenConfuseOnAnyHeads(2), "コインを2枚投げ、2枚とも「おもて」なら、相手を「こんらん」状態にする。", 10),
            (E.SwapCountersOnHeads(), "自分にのっているダメージカウンターすべてと、相手にのっているダメージカウンターすべてを、取り替える。", None),
            (E.HealAllPokemonBothSides(1), "自分の場にいるポケモン全員から、それぞれダメージカウンターを1つずつ、とりのぞく。", None),
        ]
        for effect, text, damage in cases:
            with self.subTest(effect=type(effect).__name__, text=text):
                self.assertTrue(effect.check(self.attack(text, damage)))

    def test_existing_registrations_still_pass(self):
        """書き方の一覧を広げたあとも、v0.40 までに登録した同じ型のワザはどれも受け付ける。"""
        pool = load_card_pool()
        for key in E.DEFAULT_EFFECTS.attack_keys():
            entry = E.DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
            if type(entry.effect) in (E.SwitchOpponentActive, E.DamageThenSelfBarrierOnHeads, E.ExtraEnergyDamageMixed):
                with self.subTest(key=str(key)):
                    self.assertEqual(entry.effect.check(pool.get(key.card_id).attacks[key.attack_index]), [])


class EvolutionTest(unittest.TestCase):
    """進化先 8 枚（1 進化 7 枚・2 進化 1 枚）は、通常の進化の操作（``EvolvePokemon``）で、進化元の名前（完全一致）のポケモンから進化する。"""

    PAIRS = ((GLOOM, JUNGLE_ODDISH), (GLOOM, ROCKET_ODDISH), (SEADRA, HORSEA), (DARK_PERSIAN, MEOWTH), (ERIKAS_GLOOM, ERIKAS_ODDISH),
             (ERIKAS_GLOOM, ERIKAS_ODDISH_40), (SABRINAS_GOLDUCK, SABRINAS_PSYDUCK), (SABRINAS_VENOMOTH, SABRINAS_VENONAT),
             (SABRINAS_SLOWBRO, SABRINAS_SLOWPOKE))

    def evolve(self, base, card, below=None):
        spec = {"card": base, "energy": []}
        if below:
            spec["evolved_from"] = below
            spec["evolved_turn"] = 3
        state = board(spec, hand=[card])
        return apply_kernel(state, EvolvePokemon(0, card_of(state, 0, card), state.players[0].active.pokemon_id))

    def test_evolves_from_every_card_with_the_exact_name(self):
        for card, base in self.PAIRS:
            with self.subTest(card=card, base=base):
                done = self.evolve(base, card)
                self.assertEqual(done.cards[done.players[0].active.card].card_id, card)
        done = self.evolve(WEEPINBELL, VICTREEBEL, BELLSPROUT)
        self.assertEqual(done.cards[done.players[0].active.card].card_id, VICTREEBEL)
        self.assertEqual(len(done.players[0].active.evolution_stack), 2)

    def test_names_that_only_look_alike_are_rejected(self):
        """エリカのナゾノクサからクサイハナ・ナゾノクサからエリカのクサイハナ・カスミのタッツーからシードラ・サカキのニャースからわるいペルシアン・
        コダックからナツメのゴルダック・化石の秘密のヤドンとロケット団のヤドンからナツメのヤドランへは進化できない（名前が違う）。"""
        for card, base in ((GLOOM, ERIKAS_ODDISH), (ERIKAS_GLOOM, JUNGLE_ODDISH), (SEADRA, MISTYS_HORSEA), (DARK_PERSIAN, GIOVANNIS_MEOWTH),
                           (SABRINAS_GOLDUCK, PSYDUCK), (SABRINAS_SLOWBRO, SLOWPOKE), (SABRINAS_SLOWBRO, ROCKET_SLOWPOKE)):
            with self.subTest(card=card, base=base):
                state = board({"card": base, "energy": []}, hand=[card])
                assert_rejected(self, state, EvolvePokemon(0, card_of(state, 0, card), state.players[0].active.pokemon_id),
                                "EVOLUTION_NAME_MISMATCH", IllegalActionError)
        state = board({"card": ERIKAS_WEEPINBELL, "energy": [], "evolved_from": ERIKAS_BELLSPROUT, "evolved_turn": 3}, hand=[VICTREEBEL])
        assert_rejected(self, state, EvolvePokemon(0, card_of(state, 0, VICTREEBEL), state.players[0].active.pokemon_id),
                        "EVOLUTION_NAME_MISMATCH", IllegalActionError)


def barrier_board(attacker, *, mewtwo_damage=0, attacker_bench=(RATTATA,), mewtwo_bench=(RATTATA,)):
    """プレイヤー 0 のミュウツー（ダメージ ``mewtwo_damage``）が「バリアー」（v0.31 の ``AttackBarrier``。「ワザをうけない」状態）を使ったあと、プレイヤー 1 の
    ``attacker`` がワザを使う番（v0.34 の ``with_barrier`` に、ミュウツーのダメージと控えを加えたもの）。"""
    state = build_test_state([
        {"active": mon(MEWTWO, (P, P, P), damage=mewtwo_damage), "bench": list(mewtwo_bench)},
        {"active": attacker, "bench": list(attacker_bench)},
    ], turn_number=TURN)
    return play(state, UseAttack(0, 1), [first])


def heals(done, since):
    """回復のログ（カード id, とりのぞいた数, 持ち主）。"""
    return [(done.cards[e["pokemon"]].card_id, e["counters"], e["player"]) for e in events(done, since, "attack_heal")]


def coin_count(done, since):
    """ワザのコインの枚数（番の終わりのポケモンチェックのねむりのコインは数えない）。"""
    return len([e for e in events(done, since, "coin_flip") if e["source"] != "pokemon_check"])


class HealTest(unittest.TestCase):
    """回復（ダメージカウンターをとりのぞく。GR-2000-P320-RECOVERY「すべてのダメージカウンターをとりのぞいたら、それ以上の回復はできない」）。説明に書かれた
    条件だけで回復し、やどりぎのタネの「ダメージを与えたら」の条件を付けない（説明に書かれていない）。"""

    def test_little_drain_removes_one_after_the_damage(self):
        """ちょっとすいとる（エリカのナゾノクサ PMCG5-002）: 相手に 10 → 自分のカウンターを 1 つとりのぞく（0 個なら何もしない・1 個・複数）。"""
        for damage, after in ((0, 0), (10, 0), (30, 20)):
            with self.subTest(damage=damage):
                state = board(mon(ERIKAS_ODDISH, damage=damage))
                done = attack(state, 0)
                self.assertEqual((damage_of(done, 0, ERIKAS_ODDISH), damage_of(done, 1, HITMONCHAN)), (after, 10))
                self.assertEqual(heals(done, len(state.log)), [(ERIKAS_ODDISH, 1, 0)] if damage else [])
                self.assertEqual(coin_count(done, len(state.log)), 0)

    def test_little_drain_does_not_need_to_deal_damage(self):
        """「ダメージを与えたら」の条件はない（説明に書かれていない。やどりぎのタネの ``Drain`` と区別する）: 相手が「ダメージを受けない」状態（かたまる）・
        「ワザをうけない」状態（バリアー）でダメージを与えなくても、自分のカウンターはとりのぞく（自分への効果。GR-2000-P321-PREVENTED-ELEMENTS）。"""
        state = board(mon(ERIKAS_ODDISH, damage=20), mon(HITMONCHAN, (F, F), prevent_damage=TURN - 1))
        done = attack(state, 0)
        self.assertEqual(len(events(done, len(state.log), "damage_prevented")), 1)
        self.assertEqual((damage_of(done, 0, ERIKAS_ODDISH), damage_of(done, 1, HITMONCHAN)), (10, 0))
        state = barrier_board(mon(ERIKAS_ODDISH, damage=20))
        done = play(state, UseAttack(1, 0))
        self.assertEqual((damage_of(done, 1, ERIKAS_ODDISH), damage_of(done, 0, MEWTWO)), (10, 0))
        self.assertEqual(heals(done, len(state.log)), [(ERIKAS_ODDISH, 1, 1)])

    def test_no_heal_when_the_attacker_is_knocked_out_by_counterattack(self):
        """相手のカイリキーの「はんげき」（ダメージの処理のあと・効果の前。CR-COUNTERATTACK-TIMING）で自分が HP 以上になったら、処理の対象がいないので
        とりのぞかない（p.309。ログ ``effect_skipped``）。そのあと、きぜつする。"""
        state = board(mon(ERIKAS_ODDISH, damage=40), mon(MACHAMP, (F,)))
        done = attack(state, 0)
        kinds = [e["kind"] for e in events(done, len(state.log))]
        self.assertLess(kinds.index("counterattack"), kinds.index("effect_skipped"))
        self.assertEqual(heals(done, len(state.log)), [])
        self.assertEqual([done.cards[e["pokemon"]].card_id for e in events(done, len(state.log), "knock_out")], [ERIKAS_ODDISH])

    def test_occasional_drain_only_on_heads_and_flips_against_a_barrier(self):
        """たまにすいとる: コインが「おもて」なら 1 つとりのぞく。自分への効果だけを決めるコインなので、相手が「ワザをうけない」状態でも投げる
        （v0.34 の ``void_coin_question`` は相手への効果だけを決めるコインのときだけ止める）。"""
        for side, after in ((H, 10), (T, 20)):
            with self.subTest(side=side):
                state = board(mon(ERIKAS_ODDISH, damage=20))
                done = attack(state, 1, side)
                self.assertEqual((damage_of(done, 0, ERIKAS_ODDISH), damage_of(done, 1, HITMONCHAN)), (after, 20))
                self.assertEqual(coin_count(done, len(state.log)), 1)
        state = barrier_board(mon(ERIKAS_ODDISH, damage=20))
        done = play(with_coin_results(state, H), UseAttack(1, 1))
        self.assertEqual((coin_count(done, len(state.log)), damage_of(done, 1, ERIKAS_ODDISH)), (1, 10))

    def test_healing_pollen_removes_up_to_four(self):
        """ヒーリングかふん（エリカのクサイハナ）: 「おもて」なら 4 つまで（のっている数まで。50 → 10・20 → 0・0 → 何もしない）。「うら」なら何もしない。"""
        for damage, side, after in ((50, H, 10), (20, H, 0), (0, H, 0), (50, T, 50)):
            with self.subTest(damage=damage, side=side):
                state = board(mon(ERIKAS_GLOOM, damage=damage))
                done = attack(state, 0, side)
                self.assertEqual(damage_of(done, 0, ERIKAS_GLOOM), after)
                self.assertEqual(heals(done, len(state.log)), [(ERIKAS_GLOOM, (damage - after) // 10, 0)] if damage != after else [])

    def test_doze_heals_three_then_sleeps(self):
        """いねむり（ナツメのヤドラン）: 「おもて」なら 3 つとりのぞき（のっている数まで）、そのあと自分をねむりにする。カウンターがのっていなくても、
        回復できないことは「ねむり」の要素の処理を止めない（GR-2000-P309-ATTACK-PROCEDURE。処理の対象がいなくなったのは回復の内容だけ）。
        「うら」ならどちらもしない。もとのどくは残る（p.322）。"""
        for damage, side, after, asleep in ((40, H, 10, True), (20, H, 0, True), (0, H, 0, True), (40, T, 40, False)):
            with self.subTest(damage=damage, side=side):
                state = board(mon(SABRINAS_SLOWBRO, damage=damage, poison=10))
                done = attack(state, 0, side, T)  # 2 枚目は番の終わりのポケモンチェックのねむりのコイン（「うら」ならねむりのまま）
                active = done.players[0].active
                self.assertEqual(active.damage, after + 10)  # 番の終わりのポケモンチェックのどくの 10
                self.assertEqual(type(active.conditions.exclusive).__name__ == "Asleep", asleep)
                self.assertIsNotNone(active.conditions.poison)

    def test_healing_scales_same_heads_for_every_own_pokemon(self):
        """かいふくりんぷん（ナツメのモルフォン）: コイン 3 枚を 1 度だけ投げ、「おもて」の数ぶんを、自分と自分の控え全員から、それぞれとりのぞく（のっている数
        まで。ポケモンごとに投げ直さない）。相手のポケモンはとりのぞかない。"""
        bench = (mon(RATTATA, damage=10), mon(BULBASAUR, damage=30))
        for sides, expected in (((H, H, T), (20, 0, 10)), ((H, H, H), (10, 0, 0)), ((T, T, T), (40, 10, 30))):
            with self.subTest(sides=sides):
                state = board(mon(SABRINAS_VENOMOTH, damage=40), mon(HITMONCHAN, (F, F), damage=20), bench=bench)
                done = attack(state, 0, *sides)
                own = done.players[0]
                self.assertEqual((own.active.damage, own.bench[0].damage, own.bench[1].damage), expected)
                self.assertEqual(damage_of(done, 1, HITMONCHAN), 20)
                self.assertEqual(coin_count(done, len(state.log)), 3)

    def test_transparency_of_an_own_pokemon_is_evaluated_only_when_healing(self):
        """自分の控えのゴースト（化石の秘密。「とうめい」）も、自分のワザの効果を受けるときにはたらく（v0.9 の T8）。とりのぞくカウンターがあるときだけ
        判定する（のっていなければ効果を受けない）。2 匹以上なら判定の順番が決まらない（T27）。"""
        state = board(mon(SABRINAS_VENOMOTH, damage=40), bench=(haunter(damage=20),))
        for transparency, after in ((H, 20), (T, 0)):
            with self.subTest(transparency=transparency):
                done = attack(state, 0, H, H, T, transparency)
                self.assertEqual(done.players[0].bench[0].damage, after)
                self.assertEqual(len(events(done, len(state.log), "evade_check")), 1)
        done = attack(board(mon(SABRINAS_VENOMOTH, damage=40), bench=(haunter(),)), 0, H, H, T)
        self.assertEqual(len(events(done, 0, "evade_check")), 0)
        assert_stops(self, board(mon(SABRINAS_VENOMOTH, damage=40), bench=(haunter(damage=20), haunter(damage=10))), UseAttack(0, 0),
                     "UNRESOLVED_TRANSPARENCY_COIN_ORDER")

    def test_heal_everyone_removes_one_from_both_sides(self):
        """みんなでかいふく（エリカのプリン）: お互いの場のポケモン全員から 1 つずつ（ワザを使ったプレイヤーの場 → 相手の場。0 個のポケモンは何もしない）。
        相手のポケモンの回復のログには ``attacker``。相手の「ダメージを受けない」状態（ダメージの要素だけを無効にする）は関係しない。"""
        state = board(mon(ERIKAS_JIGGLYPUFF, damage=20), mon(HITMONCHAN, (F, F), damage=30, prevent_damage=TURN - 1),
                      bench=(mon(RATTATA, damage=10), RATTATA), opponent_bench=(mon(BULBASAUR, damage=20), RATTATA))
        done = attack(state, 0)
        self.assertEqual(heals(done, len(state.log)), [(ERIKAS_JIGGLYPUFF, 1, 0), (RATTATA, 1, 0), (HITMONCHAN, 1, 1), (BULBASAUR, 1, 1)])
        self.assertEqual([e.get("attacker") for e in events(done, len(state.log), "attack_heal")], [None, None, 0, 0])
        self.assertEqual((damage_of(done, 0, ERIKAS_JIGGLYPUFF), damage_of(done, 1, HITMONCHAN), damage_of(done, 1, BULBASAUR)), (10, 20, 10))

    def test_heal_everyone_and_protection(self):
        """相手の対戦ポケモンが「ワザをうけない」状態なら、そのポケモンだけとりのぞかない（効果の要素。ほかのポケモンはとりのぞく）。相手のゴースト
        （「とうめい」）は、持ち主がコインを投げる。お互いに 1 匹ずつなら T27 で止める。"""
        state = barrier_board(mon(ERIKAS_JIGGLYPUFF, damage=20), mewtwo_damage=20, mewtwo_bench=(mon(RATTATA, damage=10),))
        done = play(state, UseAttack(1, 0))
        self.assertEqual(heals(done, len(state.log)), [(ERIKAS_JIGGLYPUFF, 1, 1), (RATTATA, 1, 0)])
        self.assertEqual(damage_of(done, 0, MEWTWO), 20)
        state = board(mon(ERIKAS_JIGGLYPUFF), mon(HITMONCHAN, (F, F)), opponent_bench=(haunter(damage=20),))
        done = attack(state, 0, H)
        [check] = events(done, len(state.log), "evade_check")
        self.assertEqual(check["player"], 1)
        self.assertEqual(done.players[1].bench[0].damage, 20)
        assert_stops(self, board(mon(ERIKAS_JIGGLYPUFF), bench=(haunter(damage=10),), opponent_bench=(haunter(damage=20),)), UseAttack(0, 0),
                     "UNRESOLVED_TRANSPARENCY_COIN_ORDER")


class CounterShiftTest(unittest.TestCase):
    """ダメージシフト（ナツメのゴルダック）: 自分と自分の控え全員から 1 つずつとりのぞき、とりのぞいたぶんを相手の対戦ポケモンにのせる。のせるのは
    ダメージカウンターの移動で、ワザのダメージではない（GR-2000-P320-COUNTER-MOVE。v0.7 の S19）。"""

    def test_removes_one_from_each_and_places_the_total(self):
        state = board(mon(SABRINAS_GOLDUCK, damage=20), bench=(mon(RATTATA, damage=10), RATTATA))
        done = attack(state, 0)
        own = done.players[0]
        self.assertEqual((own.active.damage, own.bench[0].damage, own.bench[1].damage), (10, 0, 0))
        self.assertEqual(heals(done, len(state.log)), [(SABRINAS_GOLDUCK, 1, 0), (RATTATA, 1, 0)])
        [placed] = events(done, len(state.log), "place_damage_counters")
        self.assertEqual((placed["counters"], placed["amount"], placed["player"], placed["attacker"]), (2, 20, 1, 0))
        self.assertEqual(damage_of(done, 1, HITMONCHAN), 20)
        self.assertFalse(events(done, len(state.log), "damage"))

    def test_nothing_to_move(self):
        """自分の場のどのポケモンにもカウンターがなければ、とりのぞかず、のせない（ログもない）。"""
        state = board(mon(SABRINAS_GOLDUCK), mon(HITMONCHAN, (F, F), damage=10))
        done = attack(state, 0)
        self.assertFalse(events(done, len(state.log), "attack_heal") + events(done, len(state.log), "place_damage_counters"))
        self.assertEqual(damage_of(done, 1, HITMONCHAN), 10)

    def test_not_damage_so_no_damage_calculation_or_trigger(self):
        """弱点（ヒトカゲは水に弱い）・プラスパワー・ディフェンダー・「ダメージを受けない」状態を計算しない。カイリキーの「はんげき」ははたらかない
        （「ダメージを受けた」ことにならない）。"""
        state = board(mon(SABRINAS_GOLDUCK, damage=20, trainers=[(PLUSPOWER, TURN)]),
                      mon(CHARMANDER, (), trainers=[(DEFENDER, TURN)], prevent_damage=TURN - 1))
        done = attack(state, 0)
        self.assertEqual(damage_of(done, 1, CHARMANDER), 10)
        state = board(mon(SABRINAS_GOLDUCK, damage=20), mon(MACHAMP, (F,)))
        done = attack(state, 0)
        self.assertEqual((damage_of(done, 1, MACHAMP), damage_of(done, 0, SABRINAS_GOLDUCK)), (10, 10))
        self.assertFalse(events(done, len(state.log), "counterattack"))

    def test_knock_out_after_the_attack_without_guts(self):
        """のせたカウンターで HP 以上になった相手は、ワザのあとにきぜつし、ワザを使ったプレイヤーがサイドを取る。ワザのダメージで HP 以上になったのでは
        ないので、サカキのカイリキーの「こんじょう」は使えない（v0.11 の G3〜G7）。"""
        state = board(mon(SABRINAS_GOLDUCK, damage=10), mon(HITMONCHAN, (F, F), damage=50), bench=(mon(RATTATA, damage=10),))
        done = attack(state, 0)
        self.assertEqual([done.cards[e["pokemon"]].card_id for e in events(done, len(state.log), "knock_out")], [HITMONCHAN])
        self.assertEqual((done.decision.kind, done.decision.player), (TAKE_PRIZE, 0))
        state = board(mon(SABRINAS_GOLDUCK, damage=10), mon(GIOVANNIS_MACHAMP, (F,), damage=90))
        done = attack(state, 0)
        self.assertEqual([done.cards[e["pokemon"]].card_id for e in events(done, len(state.log), "knock_out")], [GIOVANNIS_MACHAMP])
        self.assertNotEqual(done.decision.kind, KO_PREVENTION)
        self.assertFalse(events(done, len(state.log), "ko_prevention_declined"))

    def test_cx1_when_the_opponent_does_not_receive_the_counters(self):
        """相手が「ワザをうけない」状態（バリアー）・「とうめい」なら、相手にのせない。そのとき自分の側をとりのぞくかは決められない（CX1。とりのぞいてのせない・
        どちらもしない、のどちらとも記録で決まらない）ので、宣言の前に止める。移すカウンターがなければ止めない（効果を受けるポケモンがない）。"""
        assert_stops(self, barrier_board(mon(SABRINAS_GOLDUCK, damage=20)), UseAttack(1, 0), "UNRESOLVED_COUNTER_TRANSFER_PROTECTED")
        assert_stops(self, board(mon(SABRINAS_GOLDUCK, damage=20), haunter()), UseAttack(0, 0), "UNRESOLVED_COUNTER_TRANSFER_PROTECTED")
        done = play(barrier_board(mon(SABRINAS_GOLDUCK)), UseAttack(1, 0))
        self.assertEqual(damage_of(done, 0, MEWTWO), 0)
        done = attack(board(mon(SABRINAS_GOLDUCK), haunter()), 0)
        self.assertFalse(events(done, 0, "evade_check"))

    def test_own_transparency_is_evaluated_before_removing(self):
        """自分の控えのゴーストからとりのぞく前に、そのゴーストの「とうめい」を判定する（「おもて」なら、そのゴーストからはとりのぞかず、のせる数にも数えない）。"""
        state = board(mon(SABRINAS_GOLDUCK, damage=20), bench=(haunter(damage=10),))
        done = attack(state, 0, H)
        self.assertEqual((done.players[0].bench[0].damage, damage_of(done, 1, HITMONCHAN)), (10, 10))
        done = attack(state, 0, T)
        self.assertEqual((done.players[0].bench[0].damage, damage_of(done, 1, HITMONCHAN)), (0, 20))


class SwapTest(unittest.TestCase):
    """チェンジダメージ（R団のミュウツー）: 「おもて」なら、自分と相手の対戦ポケモンのカウンターすべてを取り替える。取り替える前の双方の数で処理する。"""

    def test_swaps_the_values_before_the_swap(self):
        state = board(mon(ROCKETS_MEWTWO, damage=30), mon(HITMONCHAN, (F, F), damage=10))
        done = attack(state, 0, H)
        self.assertEqual((damage_of(done, 0, ROCKETS_MEWTWO), damage_of(done, 1, HITMONCHAN)), (10, 30))
        [swap] = events(done, len(state.log), "swap_damage_counters")
        self.assertEqual((swap["damage_before"], swap["total_damage"], swap["opponent_damage_before"], swap["opponent_total_damage"]), (30, 10, 10, 30))
        self.assertFalse(events(done, len(state.log), "damage") + events(done, len(state.log), "attack_heal"))
        done = attack(state, 0, T)
        self.assertEqual((damage_of(done, 0, ROCKETS_MEWTWO), damage_of(done, 1, HITMONCHAN)), (30, 10))
        self.assertFalse(events(done, len(state.log), "swap_damage_counters"))

    def test_equal_counters_change_nothing(self):
        """数が同じなら何もしない（ログもない）。相手が「ワザをうけない」状態でも、場が変わらないので止めない。"""
        done = attack(board(mon(ROCKETS_MEWTWO, damage=20), mon(HITMONCHAN, (F, F), damage=20)), 0, H)
        self.assertFalse(events(done, 0, "swap_damage_counters"))
        state = barrier_board(mon(ROCKETS_MEWTWO))
        done = play(with_coin_results(state, H), UseAttack(1, 0))
        self.assertEqual(coin_count(done, len(state.log)), 1)

    def test_knock_out_of_either_side(self):
        """取り替えたあと HP 以上のポケモンは、ワザのあとにきぜつする（相手なら自分がサイドを取る。自分なら相手がサイドを取る）。カイリキーの「はんげき」は
        はたらかない（ダメージではない）。両方がそろって HP 以上になることはない（自分の HP ≤ 相手の取り替える前の数 < 相手の HP ≤ 自分の取り替える前の数
        < 自分の HP は成り立たない）。"""
        state = board(mon(ROCKETS_MEWTWO, damage=60), mon(RATTATA, ()))
        done = attack(state, 0, H)
        self.assertEqual([done.cards[e["pokemon"]].card_id for e in events(done, len(state.log), "knock_out")], [RATTATA])
        self.assertEqual((done.decision.kind, done.decision.player), (TAKE_PRIZE, 0))
        state = board(mon(ROCKETS_MEWTWO), mon(MACHAMP, (F,), damage=80))
        done = attack(state, 0, H)
        self.assertEqual([done.cards[e["pokemon"]].card_id for e in events(done, len(state.log), "knock_out")], [ROCKETS_MEWTWO])
        self.assertEqual(damage_of(done, 1, MACHAMP), 0)
        self.assertFalse(events(done, len(state.log), "counterattack"))
        self.assertEqual((done.decision.kind, done.decision.player), (TAKE_PRIZE, 1))

    def test_not_blocked_by_damage_prevention(self):
        """「ダメージを受けない」状態（ダメージの要素だけを無効にする）・ディフェンダーは関係しない。"""
        state = board(mon(ROCKETS_MEWTWO, damage=30), mon(HITMONCHAN, (F, F), prevent_damage=TURN - 1, trainers=[(DEFENDER, TURN)]))
        done = attack(state, 0, H)
        self.assertEqual((damage_of(done, 0, ROCKETS_MEWTWO), damage_of(done, 1, HITMONCHAN)), (0, 30))

    def test_cx1_when_the_opponent_does_not_receive_the_swap(self):
        assert_stops(self, barrier_board(mon(ROCKETS_MEWTWO, damage=30)), UseAttack(1, 0), "UNRESOLVED_COUNTER_TRANSFER_PROTECTED")
        assert_stops(self, board(mon(ROCKETS_MEWTWO, damage=30), haunter()), UseAttack(0, 0), "UNRESOLVED_COUNTER_TRANSFER_PROTECTED")


def conditions_kinds(conditions):
    """特殊状態の名前（ねむり・マヒ・こんらんの 1 つと、どく）。"""
    names = set()
    if conditions.exclusive is not None:
        names.add(type(conditions.exclusive).__name__)
    if conditions.poison is not None:
        names.add("Poisoned")
    return names


class StatusTest(unittest.TestCase):
    """特殊状態の分岐と選択。どれも p.322 の重なり・置きかえ（ねむり・マヒ・こんらんは置きかわり、どくは重なる）にしたがう。"""

    def test_foul_odor_confuses_both(self):
        """くさいにおい（クサイハナ）: 相手 → 自分の順にこんらん。相手がこのワザのダメージで HP 以上なら相手の効果だけを飛ばし、自分はこんらんになる
        （p.309）。相手が「ワザをうけない」状態でも、自分の効果は処理する。"""
        state = board(mon(GLOOM))
        done = attack(state, 1)
        self.assertEqual((conditions_kinds(condition_of(done, 1)), conditions_kinds(condition_of(done, 0))), ({"Confused"}, {"Confused"}))
        state = board(mon(GLOOM), mon(RATTATA, ()))
        done = attack(state, 1)
        self.assertEqual(conditions_kinds(done.players[0].active.conditions), {"Confused"})
        state = barrier_board(mon(GLOOM))
        done = play(state, UseAttack(1, 1))
        self.assertEqual((conditions_kinds(condition_of(done, 0)), conditions_kinds(condition_of(done, 1))), (set(), {"Confused"}))

    def test_strange_powder_one_coin_decides_which(self):
        """へんなこな（エリカのナゾノクサ PMCG5-003）: 1 枚のコインで、「おもて」ならこんらん・「うら」ならねむり（投げ直さない）。相手が「ワザをうけない」
        状態なら HC3、「とうめい」で受けないと決まったら T19b（相手への効果だけを決めるコイン）。"""
        for side, expected in ((H, {"Confused"}), (T, {"Asleep"})):
            with self.subTest(side=side):
                state = board(mon(ERIKAS_ODDISH_40))
                done = attack(state, 0, side, T)  # 2 枚目は相手の番の前のポケモンチェックのねむりのコイン
                self.assertEqual(conditions_kinds(condition_of(done, 1)), expected)
                self.assertEqual(coin_count(done, len(state.log)), 1)
        assert_stops(self, barrier_board(mon(ERIKAS_ODDISH_40)), UseAttack(1, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")
        assert_stops(self, board(mon(ERIKAS_ODDISH_40), haunter()), UseAttack(0, 0), "UNRESOLVED_EVADED_EFFECT_COIN")

    def test_miracle_pollen_tails_has_no_choice(self):
        state = board(mon(ERIKAS_GLOOM))
        done = attack(state, 1, T)
        self.assertIsNone(done.decision)
        self.assertEqual(conditions_kinds(condition_of(done, 1)), set())

    def test_miracle_pollen_each_choice(self):
        """ミラクルかふん（エリカのクサイハナ）: 「おもて」なら、ワザを使ったプレイヤーが 4 つの中から 1 つを選ぶ（決定 ``select_special_condition``。選べるもの
        は説明の並びの番号 0〜3）。選んだ状態にする。すでにどくなら重なり、ねむりなら置きかわる。"""
        state = board(mon(ERIKAS_GLOOM))
        waiting = attack(state, 1, H, T)  # 2 枚目はねむりを選んだときのポケモンチェックのコイン
        d = waiting.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices, d.resume), (SELECT_SPECIAL_CONDITION, 0, (0, 1, 2, 3), 1, 1, "attack"))
        self.assertEqual(E.CHOSEN_CONDITIONS, (SLEEP, PARALYSIS, CONFUSION, POISON))
        self.assertEqual(damage_of(waiting, 1, HITMONCHAN), 30)
        for choice, expected in ((0, {"Asleep"}), (1, {"Paralyzed"}), (2, {"Confused"}), (3, {"Poisoned"})):
            with self.subTest(choice=choice):
                done = answer(waiting, (choice,))
                self.assertEqual(conditions_kinds(condition_of(done, 1)), expected)
        state = board(mon(ERIKAS_GLOOM), mon(HITMONCHAN, (F, F), poison=10, sleep=True))
        done = answer(attack(state, 1, H), (2,))
        self.assertEqual(conditions_kinds(condition_of(done, 1)), {"Confused", "Poisoned"})

    def test_miracle_pollen_invalid_answers_and_save_restore(self):
        """不正な答え（番号の外・0 個・2 個・ほかのプレイヤー）は状態を変えずに拒否し、決定は待ったまま。決定を待つ状態を書き出し・pickle で保存して再開
        しても同じ結果。"""
        waiting = attack(board(mon(ERIKAS_GLOOM)), 1, H)
        d = waiting.decision
        for player, choices, code in ((0, (4,), "INVALID_CHOICE"), (0, (), "INVALID_CHOICE_COUNT"), (0, (0, 1), "INVALID_CHOICE_COUNT"),
                                      (1, (0,), "NOT_YOUR_DECISION")):
            with self.subTest(choices=choices, player=player):
                assert_rejected(self, waiting, ResolveDecision(player, d.id, choices), code, IllegalActionError)
        self.assertEqual(check_invariants(waiting), [])
        restored = pickle.loads(pickle.dumps(waiting))
        self.assertEqual(snapshot(answer(restored, (1,))), snapshot(answer(waiting, (1,))))

    def test_miracle_pollen_receives_once_per_attack(self):
        """相手が「ワザをうけない」状態なら HC3（コインの前）。相手のゴーストの「とうめい」はダメージの要素で 1 度だけ判定し（T4）、受けると決まったら選んだ
        状態を与える。受けないと決まったら T19b（宣言の前に止める）。"""
        assert_stops(self, barrier_board(mon(ERIKAS_GLOOM)), UseAttack(1, 1), "UNRESOLVED_PREVENTED_EFFECT_COIN")
        assert_stops(self, board(mon(ERIKAS_GLOOM), haunter()), UseAttack(0, 1), "UNRESOLVED_EVADED_EFFECT_COIN")

    def test_miracle_pollen_reparalysis_choice_is_held(self):
        """マヒの再付与で回復する番が変わる場合（v0.3b の ``UNRESOLVED_REPARALYSIS_RECOVERY_TURN``）は、マヒを選べるが選ぶと止める（ほかの 3 つは選べる）。
        自然な対戦では起こらない（マヒ状態のポケモンは次の自分の番の終わりに回復する）ので、判定（``paralysis_problem``）を差しかえて確かめた。"""
        problem = Unsupported("UNRESOLVED_REPARALYSIS_RECOVERY_TURN", "テスト専用の再付与の問い")
        state = board(mon(ERIKAS_GLOOM))
        with mock.patch.object(programs, "paralysis_problem", return_value=problem):
            waiting = attack(state, 1, H)
            d = waiting.decision
            self.assertEqual(d.context_value("unresolved_choices"), (1,))
            assert_rejected(self, waiting, ResolveDecision(0, d.id, (1,)), "UNRESOLVED_REPARALYSIS_RECOVERY_TURN", UnsupportedError)
            done = answer(waiting, (0,))
        self.assertEqual(conditions_kinds(condition_of(done, 1)), {"Asleep"})

    def test_troubled_telekinesis(self):
        """こまったねんりき（ナツメのコダック）: 「おもて」なら相手に 20 とこんらん、「うら」なら相手にダメージを与えず、自分をこんらんにする（1 枚のコイン）。
        相手が「ワザをうけない」状態でも、自分への効果を決めるコインなので投げる。相手の「ダメージを受けない」状態はダメージの要素だけを無効にする。"""
        state = board(mon(SABRINAS_PSYDUCK))
        done = attack(state, 1, H)
        self.assertEqual((damage_of(done, 1, HITMONCHAN), conditions_kinds(condition_of(done, 1)), conditions_kinds(condition_of(done, 0))),
                         (20, {"Confused"}, set()))  # ナツメのコダックは水（エビワラーの弱点の超ではない）
        done = attack(state, 1, T)
        self.assertEqual((damage_of(done, 1, HITMONCHAN), conditions_kinds(condition_of(done, 1)), conditions_kinds(condition_of(done, 0))),
                         (0, set(), {"Confused"}))
        self.assertFalse(events(done, len(state.log), "damage"))
        state = board(mon(SABRINAS_PSYDUCK), mon(HITMONCHAN, (F, F), prevent_damage=TURN - 1))
        done = attack(state, 1, H)
        self.assertEqual((damage_of(done, 1, HITMONCHAN), conditions_kinds(condition_of(done, 1))), (0, {"Confused"}))
        state = barrier_board(mon(SABRINAS_PSYDUCK))
        done = play(with_coin_results(state, T), UseAttack(1, 1))
        self.assertEqual(conditions_kinds(condition_of(done, 1)), {"Confused"})

    def test_troubled_telekinesis_against_transparency(self):
        """相手のゴーストの「とうめい」はダメージの要素で 1 度だけ判定し、受けないと決まったら同じワザのこんらんも受けない（T4）。"""
        state = board(mon(SABRINAS_PSYDUCK), haunter())
        done = attack(state, 1, H, H)
        self.assertEqual((len(events(done, len(state.log), "evade_check")), conditions_kinds(condition_of(done, 1))), (1, set()))
        done = attack(state, 1, H, T)
        self.assertEqual(conditions_kinds(condition_of(done, 1)), {"Confused"})

    def test_illusion_wave_any_heads_of_two(self):
        """げんかくおんぱ（ナツメのモルフォン）: 2 枚のうち 1 枚でも「おもて」ならこんらん（2 枚とも投げる）。"""
        for sides, confused in (((T, T), False), ((H, T), True), ((T, H), True), ((H, H), True)):
            with self.subTest(sides=sides):
                state = board(mon(SABRINAS_VENOMOTH))
                done = attack(state, 1, *sides)
                self.assertEqual(coin_count(done, len(state.log)), 2)
                self.assertEqual("Confused" in conditions_kinds(condition_of(done, 1)), confused)
        assert_stops(self, barrier_board(mon(SABRINAS_VENOMOTH)), UseAttack(1, 1), "UNRESOLVED_PREVENTED_EFFECT_COIN")

    def test_illusion_wave_flips_no_coin_without_a_target(self):
        """相手がこのワザのダメージで HP 以上になったら、こんらんの対象がいないので 2 枚とも投げない（p.309。v0.41 の ``Status.has_target``。ダメージの要素の
        あとのワザ全体のコインは、決める要素のどれにも対象がなければ投げない（v0.38 の ``Coin``））。"""
        state = board(mon(SABRINAS_VENOMOTH), mon(RATTATA, (), damage=20))
        done = attack(state, 1)
        self.assertEqual(coin_count(done, len(state.log)), 0)
        self.assertEqual([done.cards[e["pokemon"]].card_id for e in events(done, len(state.log), "knock_out")], [RATTATA])

    def test_hypnotic_wave(self):
        """さいみんはどう（R団のミュウツー）: 「おもて」ならねむり。"""
        for side, expected in ((H, {"Asleep"}), (T, set())):
            with self.subTest(side=side):
                done = attack(board(mon(ROCKETS_MEWTWO), mon(MACHAMP, (F,))), 1, side, T)  # 2 枚目はポケモンチェックのねむりのコイン
                self.assertEqual(conditions_kinds(condition_of(done, 1)), expected)


class CoinAfterDamageTest(unittest.TestCase):
    """ダメージのあとの、ダメージ以外の効果だけを決めるワザ全体のコイン（げんかくおんぱ・v0.37 のねこにこばん）は、相手の「ダメージを受けたとき」の効果（カイリキー
    の「はんげき」）のあとに投げる（CR-COUNTERATTACK-TIMING。効果を決めるコインは効果の側）。v0.40 までは、ねこにこばんをカイリキーに使うと内部エラー
    （RuntimeError）になっていた（docs/heal-counter-status-v0.41.md 3.5）。"""

    def order(self, done, since):
        kinds = [e["kind"] for e in events(done, since)]
        return kinds.index("counterattack"), kinds.index("coin_flip")

    def test_illusion_wave_after_counterattack(self):
        state = board(mon(SABRINAS_VENOMOTH), mon(MACHAMP, (F,)))
        done = attack(state, 1, H, T)
        counter, coin = self.order(done, len(state.log))
        self.assertLess(counter, coin)
        self.assertEqual(conditions_kinds(condition_of(done, 1)), {"Confused"})

    def test_pay_day_after_counterattack(self):
        state = board(mon(MEOWTH, (F, F)), mon(MACHAMP, (F,)), deck=[RATTATA, FIRE])
        done = attack(state, 0, H)
        counter, coin = self.order(done, len(state.log))
        self.assertLess(counter, coin)
        self.assertEqual(len(events(done, len(state.log), "draw")), 2)  # ねこにこばんで 1 枚・相手の番の最初に相手が 1 枚

    def test_counterattack_knocks_out_the_attacker_before_the_coin(self):
        """「はんげき」でワザを使ったポケモンが HP 以上になっても、相手への効果のコインは投げる（効果の対象は相手。p.309）。"""
        state = board(mon(SABRINAS_VENOMOTH, damage=50), mon(MACHAMP, (F,)))
        done = attack(state, 1, H, H)
        self.assertEqual(coin_count(done, len(state.log)), 2)
        self.assertEqual("Confused" in conditions_kinds(condition_of(done, 1)), True)


class RetreatLockOnHeadsTest(unittest.TestCase):
    """ようかいえき（ウツボット）: 「おもて」なら、相手の対戦ポケモンは次の相手の番に「にげる」ことができない（v0.36 の ``CannotRetreat``）。"""

    def test_heads_locks_retreat_next_turn(self):
        state = board(mon(VICTREEBEL))
        done = attack(state, 1, H)
        hitmonchan = done.players[1].active
        self.assertTrue(any(isinstance(e, CannotRetreat) for e in hitmonchan.persistent_effects))
        command = Retreat(1, tuple(hitmonchan.energy[:2]), done.players[1].bench[0].card)
        assert_rejected(self, done, command, "RETREAT_PREVENTED", IllegalActionError)
        done = attack(state, 1, T)
        self.assertFalse(done.players[1].active.persistent_effects)
        apply_kernel(done, Retreat(1, tuple(done.players[1].active.energy[:2]), done.players[1].bench[0].card))

    def test_coin_is_not_flipped_without_a_target_and_stops_when_protected(self):
        """相手がこのワザのダメージで HP 以上なら投げない（p.309）。「ワザをうけない」状態なら HC3、「とうめい」で受けないと決まったら T19b。"""
        state = board(mon(VICTREEBEL), mon(RATTATA, (), damage=10))
        done = attack(state, 1)
        self.assertEqual(coin_count(done, len(state.log)), 0)
        assert_stops(self, barrier_board(mon(VICTREEBEL)), UseAttack(1, 1), "UNRESOLVED_PREVENTED_EFFECT_COIN")
        assert_stops(self, board(mon(VICTREEBEL), haunter()), UseAttack(0, 1), "UNRESOLVED_EVADED_EFFECT_COIN")


class LureTest(unittest.TestCase):
    """さそうかおり（ウツボット。コインなし）・ゆうわく（わるいペルシアン。「おもて」なら）: ワザを使ったプレイヤーが相手の控えを選び、相手の対戦ポケモンと
    入れ替える（v0.31 のかどわかすと同じ要素 ``ForceSwitch(chooser="attacker")``）。"""

    def test_sweet_scent_attacker_chooses(self):
        state = board(mon(VICTREEBEL), opponent_bench=(RATTATA, BULBASAUR))
        waiting = attack(state, 0)
        d = waiting.decision
        self.assertEqual((d.kind, d.player), (FORCED_SWITCH, 0))
        done = answer(waiting, (d.options[1],))
        self.assertEqual(done.cards[done.players[1].active.card].card_id, BULBASAUR)
        [switch] = events(done, len(state.log), "forced_switch")
        self.assertEqual(switch["chosen_by"], "attacker")
        done = attack(board(mon(VICTREEBEL), opponent_bench=()), 0)
        self.assertEqual(done.cards[done.players[1].active.card].card_id, HITMONCHAN)

    def test_lure_requires_bench_and_heads(self):
        """ゆうわく: 説明の「(相手に控えがいない時、このワザは使えない)」はワザを使うための条件（コインの前に拒否）。「うら」なら何もしない。「ワザをうけない」
        相手には HC3（入れ替えだけを決めるコイン）。"""
        assert_rejected(self, board(mon(DARK_PERSIAN), opponent_bench=()), UseAttack(0, 0), "NO_OPPONENT_BENCH", IllegalActionError)
        state = board(mon(DARK_PERSIAN))
        waiting = attack(state, 0, H)
        self.assertEqual((waiting.decision.kind, waiting.decision.player), (FORCED_SWITCH, 0))
        done = answer(waiting, first(waiting.decision))
        self.assertEqual(done.cards[done.players[1].active.card].card_id, RATTATA)
        done = attack(state, 0, T)
        self.assertIsNone(done.decision)
        self.assertEqual(done.cards[done.players[1].active.card].card_id, HITMONCHAN)
        assert_stops(self, barrier_board(mon(DARK_PERSIAN)), UseAttack(1, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")

    def test_poison_claws(self):
        """どくのつめ（わるいペルシアン）: v0.2 からの ``PoisonOnHeads``。"""
        for side, expected in ((H, {"Poisoned"}), (T, set())):
            with self.subTest(side=side):
                done = attack(board(mon(DARK_PERSIAN)), 1, side)
                self.assertEqual(conditions_kinds(condition_of(done, 1)), expected)


class PhoenixFlameTest(unittest.TestCase):
    """ひのとり（カツラのファイヤー）: 相手に 90。「うら」なら、ダメージを与えた後、自分とついているすべてのカードを山札にもどし、山札を切る（v0.36 の
    ``ReturnSelfToDeck``。きぜつではない）。"""

    def test_tails_returns_everything_and_promotes(self):
        state = board(mon(BLAINES_MOLTRES), mon(MACHAMP, (F,)), deck=[RATTATA] * 5)
        done = attack(state, 0, T)
        self.assertEqual(len(done.players[0].deck), 5 + 1 + 5)
        self.assertEqual((done.decision.kind, done.decision.player), (PROMOTE_ACTIVE, 0))
        self.assertEqual(damage_of(done, 1, MACHAMP), 90)
        self.assertFalse(events(done, len(state.log), "knock_out"))
        self.assertEqual(len(events(done, len(state.log), "shuffle")), 1)
        self.assertEqual(card_count(done, 0), card_count(state, 0))
        done = attack(state, 0, H)
        self.assertEqual(done.cards[done.players[0].active.card].card_id, BLAINES_MOLTRES)

    def test_no_bench_loses_after_returning(self):
        done = attack(board(mon(BLAINES_MOLTRES), mon(MACHAMP, (F,)), bench=()), 0, T)
        [end] = events(done, 0, "game_end")
        self.assertEqual(end["winner"], 1)

    def test_existing_questions(self):
        """相手がこのワザで HP 以上になる（RD9）・ダメージを与えない（Z23）場合は、既存の問いで宣言の前に止める。"""
        assert_stops(self, board(mon(BLAINES_MOLTRES)), UseAttack(0, 0), "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT")
        assert_stops(self, board(mon(BLAINES_MOLTRES), mon(MACHAMP, (F,), prevent_damage=TURN - 1)), UseAttack(0, 0),
                     "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE")


class SunbathTest(unittest.TestCase):
    """ひなたぼっこ（ロケット団のヤドン）: 自分の山札から「超」エネルギーカードを 1 枚選び出し、このカードにつけてよい。その後、山札を切る。手札からつける通常の操作・
    特殊能力でつけた枚数には数えない。"""

    DECK = (PSYCHIC, RATTATA, PSYCHIC, GRASS)

    def test_choose_one(self):
        state = board(mon(ROCKET_SLOWPOKE), deck=self.DECK)
        waiting = attack(state, 0)
        d = waiting.decision
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices), (ATTACH_FROM_DECK, 0, 0, 1))
        self.assertEqual([waiting.cards[u].card_id for u in d.options], [PSYCHIC, PSYCHIC])
        self.assertEqual(list(d.options), sorted(d.options))
        done = answer(waiting, (d.options[1],))
        self.assertIn(d.options[1], done.players[0].active.energy)
        self.assertEqual((done.energy_attachments_this_turn, done.energy_attached_by_powers_this_turn), (0, 0))
        [attached] = events(done, len(state.log), "attach_energy_from_deck")
        self.assertEqual(attached["card"], d.options[1])
        [shuffle] = events(done, len(state.log), "shuffle")
        self.assertEqual(shuffle["effect"], f"{ROCKET_SLOWPOKE}#0")
        self.assertEqual(card_count(done, 0), card_count(state, 0))

    def test_decline_and_no_candidates_still_shuffle(self):
        state = board(mon(ROCKET_SLOWPOKE), deck=self.DECK)
        done = answer(attack(state, 0), ())
        [none] = events(done, len(state.log), "attach_energy_from_deck_none")
        self.assertEqual(none["reason"], "declined")
        self.assertEqual(len(done.players[0].active.energy), 1)
        state = board(mon(ROCKET_SLOWPOKE), deck=(RATTATA, GRASS))
        done = attack(state, 0)
        self.assertIsNone(done.decision)
        [none] = events(done, len(state.log), "attach_energy_from_deck_none")
        self.assertEqual(none["reason"], "no_candidates")
        self.assertEqual(len(events(done, len(state.log), "shuffle")), 1)

    def test_invalid_answers(self):
        waiting = attack(board(mon(ROCKET_SLOWPOKE), deck=self.DECK), 0)
        d = waiting.decision
        grass = card_of(waiting, 0, GRASS, "deck")
        assert_rejected(self, waiting, ResolveDecision(0, d.id, (grass,)), "INVALID_CHOICE", IllegalActionError)
        assert_rejected(self, waiting, ResolveDecision(0, d.id, tuple(d.options)), "INVALID_CHOICE_COUNT", IllegalActionError)
        self.assertEqual(snapshot(answer(pickle.loads(pickle.dumps(waiting)), (d.options[0],))), snapshot(answer(waiting, (d.options[0],))))

    def test_headbutt(self):
        """ずつき（ロケット団のヤドン）は説明のないワザ（``DamageOnly``）。"""
        done = attack(board(mon(ROCKET_SLOWPOKE)), 1)
        self.assertEqual(damage_of(done, 1, HITMONCHAN), 20)  # エビワラーの弱点は超


class HeadbuttLockTest(unittest.TestCase):
    """きあいずつき（ナツメのヤドラン）: 次の自分の番、このカードは「きあいずつき」を使えない（v0.35 の ``CannotUseOwnAttack``。コインなし）。"""

    def test_locked_on_the_next_own_turn_only(self):
        state = board(mon(SABRINAS_SLOWBRO), mon(MACHAMP, (F,)), deck=[FIRE] * 10)
        done = attack(state, 1)
        lock = [e for e in done.players[0].active.persistent_effects if isinstance(e, CannotUseOwnAttack)]
        self.assertEqual(len(lock), 1)
        turn9 = apply_kernel(done, EndTurn(1))
        assert_rejected(self, turn9, UseAttack(0, 1), "ATTACK_LOCKED", IllegalActionError)
        apply_kernel(with_coin_results(turn9, T), UseAttack(0, 0))  # いねむりは使える
        turn11 = apply_kernel(apply_kernel(turn9, EndTurn(0)), EndTurn(1))
        apply_kernel(turn11, UseAttack(0, 1))

    def test_psychic_burn(self):
        state = board(mon(ROCKETS_MEWTWO))
        done = attack(state, 2)
        self.assertEqual([e["amount"] for e in events(done, len(state.log), "damage")], [120])  # エビワラーの弱点は超


class PulledPunchTest(unittest.TestCase):
    """やさしいパンチ（エリカのプリン）: 相手の対戦ポケモンにカウンターがのっていれば 40 − 30（p.321 の 1 段階）。控えのカウンターは見ない。"""

    def test_reduction(self):
        for damage, expected in ((0, 40), (10, 10)):
            with self.subTest(damage=damage):
                state = board(mon(ERIKAS_JIGGLYPUFF), mon(MACHAMP, (F,), damage=damage), opponent_bench=(mon(RATTATA, damage=10),))
                done = attack(state, 1)
                self.assertEqual([e["amount"] for e in events(done, len(state.log), "damage")], [expected])


class SeadraTest(unittest.TestCase):
    """シードラ: みずでっぽう（v0.31 の ``ExtraEnergyDamageMixed``。必要なエネルギーに無色があるので、無色を払える「水」が多いと HC4）・こうそくいどう
    （v0.34 の ``DamageThenSelfBarrierOnHeads``。「ワザをうけない」状態）。"""

    def test_water_gun(self):
        done = attack(board(mon(SEADRA)), 0)
        self.assertEqual(damage_of(done, 1, HITMONCHAN), 20)
        assert_stops(self, board(mon(SEADRA, (W, W, F))), UseAttack(0, 0), "UNRESOLVED_EXTRA_ENERGY_COLORLESS")

    def test_agility(self):
        state = board(mon(SEADRA), deck=[FIRE] * 5)
        done = attack(state, 1, H)
        hit = apply_kernel(done, UseAttack(1, 0))
        self.assertEqual(damage_of(hit, 0, SEADRA), 0)
        done = attack(state, 1, T)
        hit = apply_kernel(done, UseAttack(1, 0))
        self.assertEqual(damage_of(hit, 0, SEADRA), 20)


class CopyTest(unittest.TestCase):
    """相手のワザを自分のワザとして使う効果（ピクシー・ピッピの「ゆびをふる」・カスミのコダックの「ちょうのうりょく」）での v0.41 のワザ。"""

    COPIERS: ClassVar[dict] = {CLEFABLE: ((P,), 0, ()), CLEFAIRY: ((P, P, P), 1, ()), MISTYS_PSYDUCK: ((P,), 0, (H, H, H))}

    def copier(self, card, target, *, damage=0, opponent_bench=(RATTATA, BULBASAUR)):
        return board(mon(card, self.COPIERS[card][0], damage=damage), mon(target, ()), bench=(mon(RATTATA, damage=10),),
                     opponent_bench=opponent_bench, deck=(PSYCHIC, FIRE, RATTATA))

    def test_every_attack_can_be_copied_without_internal_errors(self):
        """29 のワザのどれをまねても、エンジンの内部のエラーにならない（処理するか、決まったコードで拒否する）。処理のあとも不変条件が通る。"""
        for (card, index) in EXPECTED:
            for copier, (energy, attack_index, sides) in self.COPIERS.items():
                with self.subTest(card=card, index=index, copier=copier):
                    state = self.copier(copier, card, damage=20)
                    try:
                        current = play(with_coin_results(state, *sides, H, H, H, H), UseAttack(0, attack_index), [])
                        if current.decision is not None and current.decision.kind == SELECT_ATTACK:
                            self.assertIn(index, current.decision.options)
                            current = apply_kernel(current, ResolveDecision(0, current.decision.id, (index,)))
                        while current.decision is not None and current.decision.resume == "attack":
                            d = current.decision
                            current = apply_kernel(current, ResolveDecision(d.player, d.id, first(d)))
                    except EngineError as error:
                        self.assertTrue(error.code.startswith(("UNRESOLVED_", "UNSUPPORTED_")), error.code)
                        continue
                    self.assertEqual(check_invariants(current), [])

    def test_headbutt_lock_is_an_engine_limitation(self):
        """きあいずつきは、番をまたぐ効果をワザを使ったポケモンのカードのワザの位置で記録するので、相手のワザとして使えない（v0.35 からのエンジンの未対応
        ``UNSUPPORTED_COPIED_ATTACK``。選べるが選ぶと止める。原典の問いではない）。"""
        state = self.copier(CLEFABLE, SABRINAS_SLOWBRO)
        waiting = attack(state, 0)
        self.assertEqual(waiting.decision.context_value("unsupported_choices"), (1,))
        assert_rejected(self, waiting, ResolveDecision(0, waiting.decision.id, (1,)), "UNSUPPORTED_COPIED_ATTACK", UnsupportedError)

    def test_lure_copied_follows_the_copier_clause(self):
        """ゆうわくの「(相手に控えがいない時、このワザは使えない)」: ピクシー・ピッピは選べない、カスミのコダックは選べるが選ぶと HC9。"""
        for copier, (energy, attack_index, sides) in self.COPIERS.items():
            with self.subTest(copier=copier):
                waiting = attack(self.copier(copier, DARK_PERSIAN, opponent_bench=()), attack_index, *sides)
                d = waiting.decision
                if copier == MISTYS_PSYDUCK:
                    self.assertIn(0, d.context_value("unresolved_choices", ()))
                    self.assertEqual(d.context_value("unresolved_code"), "UNRESOLVED_COPIED_ATTACK")
                else:
                    self.assertNotIn(0, d.options)

    def test_copied_heal_and_sunbath_act_on_the_copier(self):
        """まねたワザの「自分」は、まねたポケモン（ちょっとすいとるの回復・ひなたぼっこのエネルギー）。"""
        state = self.copier(CLEFABLE, ERIKAS_ODDISH, damage=20)
        done = answer(attack(state, 0), (0,))
        self.assertEqual(damage_of(done, 0, CLEFABLE), 10)
        state = self.copier(CLEFABLE, ROCKET_SLOWPOKE)
        waiting = answer(attack(state, 0), (0,))
        self.assertEqual(waiting.decision.kind, ATTACH_FROM_DECK)
        done = answer(waiting, first(waiting.decision))
        self.assertEqual(len(done.players[0].active.energy), 2)


class IntegrityTest(unittest.TestCase):
    """不変条件・書き出し・拒否で状態が変わらないこと・渡した状態を変えないこと。"""

    CASES = (
        (GLOOM, 0, (), ()), (GLOOM, 1, (), ()), (VICTREEBEL, 0, (), (first,)), (VICTREEBEL, 1, (H,), ()), (SEADRA, 0, (), ()), (SEADRA, 1, (H,), ()),
        (DARK_PERSIAN, 0, (H,), (first,)), (DARK_PERSIAN, 1, (H,), ()), (BLAINES_MOLTRES, 0, (T,), ()), (ROCKET_SLOWPOKE, 0, (), (first,)),
        (ROCKET_SLOWPOKE, 1, (), ()), (ERIKAS_ODDISH, 0, (), ()), (ERIKAS_ODDISH, 1, (H,), ()), (ERIKAS_ODDISH_40, 0, (T,), ()),
        (ERIKAS_GLOOM, 0, (H,), ()), (ERIKAS_GLOOM, 1, (H,), (lambda d: (3,),)), (SABRINAS_PSYDUCK, 0, (), ()), (SABRINAS_PSYDUCK, 1, (T,), ()),
        (SABRINAS_GOLDUCK, 0, (), ()), (SABRINAS_GOLDUCK, 1, (H,), ()), (SABRINAS_VENOMOTH, 0, (H, T, H), ()), (SABRINAS_VENOMOTH, 1, (T, H), ()),
        (SABRINAS_SLOWBRO, 0, (H,), ()), (SABRINAS_SLOWBRO, 1, (), ()), (ERIKAS_JIGGLYPUFF, 0, (), ()), (ERIKAS_JIGGLYPUFF, 1, (), ()),
        (ROCKETS_MEWTWO, 0, (H,), ()), (ROCKETS_MEWTWO, 1, (H,), ()), (ROCKETS_MEWTWO, 2, (), ()),
    )

    def state(self, card):
        # カツラのファイヤーの 90 でカイリキーが HP 以上になると RD9 で止まるので、そのときだけカイリキーのカウンターをのせない
        machamp = mon(MACHAMP, (F,), damage=0 if card == BLAINES_MOLTRES else 10)
        return board(mon(card, damage=20), machamp, bench=(mon(RATTATA, damage=10), BULBASAUR),
                     opponent_bench=(mon(RATTATA, damage=10), BULBASAUR), deck=(PSYCHIC, FIRE, PSYCHIC, RATTATA))

    def test_cases_cover_every_attack(self):
        self.assertEqual(sorted((card, index) for card, index, _, _ in self.CASES), sorted(EXPECTED))

    def test_every_step_keeps_invariants_and_does_not_mutate_the_input(self):
        """どのワザも、途中の決定ごとに不変条件が通り、書き出し（形式 10）と pickle で同じ状態にもどる。``apply_command`` は渡した状態を変えない。相手の
        カイリキー（「はんげき」）がいる盤面で、ダメージのあとの効果がはんげきのあとに来る。"""
        for card, index, sides, answers in self.CASES:
            with self.subTest(card=card, index=index):
                state = self.state(card)
                before = copy.deepcopy(full(state))
                current = apply_kernel(with_coin_results(state, *sides), UseAttack(0, index))
                self.assertEqual(full(state), before)
                for answer_of in answers:
                    self.assertEqual(check_invariants(current), [])
                    self.assertEqual(full(pickle.loads(pickle.dumps(current))), full(current))
                    d = current.decision
                    current = apply_kernel(current, ResolveDecision(d.player, d.id, answer_of(d)))
                self.assertEqual(check_invariants(current), [])
                self.assertTrue(current.decision is None or current.decision.resume != "attack")


class PreflightParityTest(unittest.TestCase):
    """先読みの方法（derived・derived_full・legacy）によらず、同じコインの結果で同じ結果になる（v0.41 の型はどれも ``VERIFIED`` に入れていないので、legacy も
    すべての結果を試す方法）。山札を切る要素は先読みでは切らない。止める場合（CX1 など）は、どの方法でも同じコードで宣言の前に止める（上のテストの
    ``assert_stops``）。"""

    def test_same_result_in_every_mode(self):
        for card, index, sides, answers in IntegrityTest.CASES:
            with self.subTest(card=card, index=index):
                state = IntegrityTest().state(card)
                results = set()
                for mode in PREFLIGHT_MODES:
                    done = play(with_coin_results(state, *sides), UseAttack(0, index), answers, mode=mode)
                    results.add(repr(snapshot(done)))
                self.assertEqual(len(results), 1)


class DocumentTest(unittest.TestCase):
    def test_document_records_the_decisions(self):
        """文書に、カードごとの結果・CX1 の根拠と影響の範囲・既存の問いの再利用・ねこにこばんの直し・照合の違いを書いた。"""
        text = DOC.read_text(encoding="utf-8")
        for needle in ("CX1", "UNRESOLVED_COUNTER_TRANSFER_PROTECTED", "GR-2000-P320-COUNTER-MOVE", "GR-2000-P320-RECOVERY", "CR-COUNTERATTACK-TIMING",
                       "RD9", "Z23", "HC3", "HC4", "HC9", "T19b", "T27", "pcg-search.com", "ねこにこばん", "ダメージシフト", "チェンジダメージ",
                       "ミラクルかふん", "ひなたぼっこ", "みんなでかいふく", "かいふくりんぷん", "いねむり", "きあいずつき", "UNSUPPORTED_COPIED_ATTACK"):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()

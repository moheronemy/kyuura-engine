"""v0.93（docs/active-leave-locks-v0.93.md）: 「バトル場をはなれられない」効果と、続くワザの制限のポケモン 9 枚（ワザ 17）。

根拠は kyuura データの採用（kyuura ``7d3f4ca`` の data/cards.json の日本語の印刷の文面）と、既存の規定の記録（GR-2000-P309-ATTACK-PROCEDURE・GR-2000-P310-EVOLUTION・
GR-2000-P311-RETREAT・GR-2000-P321-DAMAGE-ORDER・GR-2000-P322-PERSISTENT-EFFECTS・GR-2000-P323-KNOCKOUT・GR-2000-P324-DEVOLUTION・GR-2000-P307-CARD-OVER-RULE。docs 各章）。
英語版の文面・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像・pcg-search.com との照合はしていない。盤面は ``build_test_state`` で作った
1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.93``）。自然な対戦で起こらない盤面（自分の番に
相手の対戦ポケモンがはなれられない）は ``locked`` でログつきの効果をのせて作る。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttachEnergy,
    AttackKey,
    EvolvePokemon,
    ResolveDecision,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import DiscardFromPlay
from kyuura_engine.decisions import FORCED_SWITCH
from kyuura_engine.engine import LEAVE_ACTIVE_PREVENTED
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe
from kyuura_engine.persistent import add_persistent_effect, leave_lock, leave_locks
from kyuura_engine.resolution.flow import legacy_unknown_features
from kyuura_engine.resolution.programs import period_log_fields
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import (
    PERIOD_EFFECT_TYPES,
    PERSISTENT_EFFECT_TYPES,
    SOURCE_LEAVES_ACTIVE,
    AttackCoinCheck,
    PeriodAttackCoinCheck,
    PeriodAttackLock,
    PeriodLeaveLock,
    Phase,
)
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.release_catalog import cards_before
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_power_suppression_lasting_locks_v0_92 import (
    answer,
    board,
    declare,
    effects_of,
    end,
    mon,
    play,
    retreat_cmd,
    uid,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "active-leave-locks-v0.93.md"
DOC_V092 = ROOT / "docs" / "power-suppression-lasting-locks-v0.92.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
TURN = 7
G, R, W, L, P, F = H.GRASS, H.FIRE, H.WATER, H.LIGHTNING, H.PSYCHIC, H.FIGHTING
CATERPIE, CATERPIE_QSG, TANGELA = H.CATERPIE_ES1, H.CATERPIE_QSG, H.TANGELA_ES2
GLOOM, CROCONAW, DARK_ARIADOS = H.GLOOM_NEO1, H.CROCONAW_NEO1, H.DARK_ARIADOS_NEO4
PILOSWINE, DARK_CROCONAW, OCTILLERY = H.PILOSWINE_NEO1, H.DARK_CROCONAW_NEO4, H.OCTILLERY_NEO3
ONIX = "PMCG1-054"  # イワーク（第1弾。HP 90。いわおとし（闘）10。受ける側の丈夫なたねポケモン）
PIDGEY_WHIRLWIND = "PMCG1-059"  # ポッポ（かぜおこし。入れ替えは相手が行う）
PONYTA_KICK = "GD5-009"  # カツラのポニータ（けりにげ。おもてで自分を入れ替える）
KOFFING_SMOG = "PMCG6-015"  # キョウのドガース（くもがくれガス。おもてで自分を山札にもどす）
EXEGGUTOR = "PMCG2-012"  # ナッシー（テレポート。自分を入れ替える）
TENTACOOL = "PMCG3-011"  # メノクラゲ（［おくびょう］）
DRAGONITE = "PMCG3-043"  # カイリュー（［かけつける］）
RAIKOU = "neo3-029"  # ライコウ（［いなびかり］）
BROCKS_PRIMEAPE = "PMCG5-051"  # タケシのオコリザル（［ずらかる］）
BELOW = {GLOOM: H.ODDISH_NEO1, CROCONAW: H.TOTODILE_NEO1, DARK_ARIADOS: H.SPINARAK_NEO1, PILOSWINE: H.SWINUB_NEO1, DARK_CROCONAW: H.TOTODILE_NEO4,
         OCTILLERY: H.REMORAID_NEO3, EXEGGUTOR: H.EXEGGCUTE}
V093_ATTACKS = [AttackKey(c, i) for c in H.V0_93_POKEMON for i in range(len(load_card_pool().definitions[c].attacks))]
AL1, AL2, AL3 = E.LEAVE_LOCK_KNOCKOUT_CODE, E.LEAVE_LOCK_NO_EFFECT_CODE, E.LEAVE_LOCK_SCRAM_CODE
JC1, JC2, CJ1 = E.JAW_CLAMP_SOURCE_RETURNED_CODE, E.JAW_CLAMP_SOURCE_EVOLVED_CODE, E.CLAMPING_JAW_SOURCE_DEVOLVED_CODE
HC3 = "UNRESOLVED_PREVENTED_EFFECT_COIN"
AC6, AC13 = "UNRESOLVED_ATTACK_CHECK_CONFUSION", "UNRESOLVED_MULTIPLE_ATTACK_CHECKS"
NEW_RULINGS = (("AL1", AL1), ("AL2", AL2), ("AL3", AL3), ("JC1", JC1), ("JC2", JC2), ("CJ1", CJ1))


def m(card, energy=(), **extra):
    """場のポケモンの指定（1 進化には進化元を付ける）。"""
    spec = mon(card, energy, **extra)
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def caterpie_locked(*, opponent_bench=(H.RATTATA,), hand=(), active=None, bench=(H.RATTATA,), card=CATERPIE, coin=HD, **kw):
    """相手（プレイヤー 1）のキャタピー（またはモンジャラ）の禁止を受けた、自分（プレイヤー 0）の番の盤面（自然な対戦の流れ: 相手の番のワザ → 自分の番）。"""
    index = 1 if card in (CATERPIE, CATERPIE_QSG) else 0
    state = board(active or m(ONIX, (F, F, F)), bench=bench, hand=hand, opponent=m(card, (G, G)), opponent_bench=opponent_bench, current=1, turn=TURN - 1, **kw)
    done = declare(state, index, coin)
    assert done.current_player == 0, done.phase
    return done


def locked(state, owner, *, exception=False):
    """プレイヤー ``owner`` の対戦ポケモンに、相手の対戦ポケモンが与えた「バトル場をはなれられない」効果（からまるいと・からみつくの組）をログつきでのせた写し（自然な対戦で起こらない
    盤面を作るため。与えた番は、発生源の持ち主の番になるように選ぶ）。"""
    state = state.clone()
    source = state.players[1 - owner].active
    target = state.players[owner].active
    turn = state.turn_number if state.current_player == 1 - owner else state.turn_number - 1
    effect = PeriodLeaveLock(source_card=source.card, source_player=1 - owner, created_turn=turn, active_turn=turn, end_turn=turn + 1,
                             source_pokemon=source.pokemon_id, knockout_exception=exception)
    created = state.turn_number
    state.turn_number = turn
    add_persistent_effect(state, owner, target, effect, attack=f"{TANGELA}#0" if exception else f"{CATERPIE}#1", **period_log_fields(effect))
    state.turn_number = created
    return state


def stopped(test, state, command, code, error=UnsupportedError):
    return rejects(test, state, command, code, error)


# ---------------------------------------------------------------- 1〜3 章: 対象・登録・文面の検査


class RegistrationTest(unittest.TestCase):
    def test_every_attack_is_registered(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_93"]), H.V0_93_CARDS)
        self.assertEqual(len(V093_ATTACKS), 17)
        for key in V093_ATTACKS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
                attack = pool.definitions[key.card_id].attacks[key.attack_index]
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja), (attack.name_ja, attack.text_ja, attack.text_ja))
                self.assertEqual(entry.effect.check(attack), [])
                self.assertIsNone(DEFAULT_EFFECTS.attack_problem(key.card_id, attack, pool.definitions[key.card_id].attacks))
        for card in H.V0_93_CARDS:
            self.assertIn(card, pool.playable_ids)
            self.assertEqual(pool.definitions[card].powers, ())

    def test_types(self):
        effect = lambda card, i: DEFAULT_EFFECTS.attack_entry(card, i).effect
        self.assertIs(effect(CATERPIE, 0), E.DAMAGE_ONLY)
        self.assertEqual(effect(CATERPIE, 1), E.DamageThenPeriodLock(E.LOCK_LEAVE, True, 0, 1))
        self.assertEqual(effect(TANGELA, 0), E.DamageThenPeriodLock(E.LOCK_LEAVE, True, 0, 1, knockout_exception=True))
        self.assertIs(effect(TANGELA, 1), E.DAMAGE_ONLY)
        self.assertEqual(effect(GLOOM, 0), E.DamageThenStatusByCoin(E.CONFUSION, E.SLEEP))
        self.assertEqual(effect(GLOOM, 1), E.CoinBonusDamageThenLeaveLock(10))
        self.assertEqual(effect(CROCONAW, 0), E.ReceivedAttackDamageBonusAttack(20, 1, 2))
        self.assertEqual(effect(CROCONAW, 1), E.DamageThenPeriodLock(E.LOCK_LEAVE, False, 1, 1, True, knockout_exception=True))
        self.assertEqual(effect(DARK_ARIADOS, 0), E.SwitchOpponentThenParalyzeNewOnHeads())
        self.assertEqual(effect(DARK_ARIADOS, 1), E.DamageThenPoisonThenLeaveLockOnHeads())
        self.assertEqual(effect(PILOSWINE, 0), E.DamageThenPeriodLock(E.LOCK_ATTACK, True, 0, None))
        self.assertEqual(effect(PILOSWINE, 1), E.DamageThenCoinBenchDamageEitherSide(10))
        self.assertEqual(effect(DARK_CROCONAW, 0), E.DamageThenRetreatLockAndAttackCoinCheck())
        self.assertEqual(effect(OCTILLERY, 0), E.ParalyzeOnHeads())
        self.assertEqual(effect(OCTILLERY, 1), E.DamageThenLastingAttackCoinCheckOnHeads())
        self.assertEqual(E.DamageThenPoisonThenLeaveLockOnHeads.opponent_effect_elements, (E.POISON, E.LEAVE_LOCK_ELEMENT))
        self.assertEqual(E.DamageThenRetreatLockAndAttackCoinCheck.opponent_effect_elements, (E.RETREAT_LOCK_ELEMENT, E.ATTACK_CHECK_ELEMENT))

    def test_the_two_caterpies_share_one_registration(self):
        """キャタピーの 2 枚（ES1-002・QSG-002）はゲーム用データが同じ組（SC-ES1-002）。id ごとに登録し、同じ登録の値を使う。"""
        self.assertEqual(dict(E.SAME_DATA_CARDS_V0_93), {CATERPIE_QSG: CATERPIE})
        for i in range(2):
            self.assertIs(DEFAULT_EFFECTS.attack_entry(CATERPIE_QSG, i), DEFAULT_EFFECTS.attack_entry(CATERPIE, i))
        extract = {c["id"]: c for c in read_extract()["cards"]}
        self.assertEqual(extract[CATERPIE]["same_card_group"], extract[CATERPIE_QSG]["same_card_group"])
        self.assertEqual(extract[CATERPIE]["pokemon"], extract[CATERPIE_QSG]["pokemon"])

    def test_unregistered_without_the_v0_93_entries(self):
        """今回の登録を除くと対戦に使えなくなるのは、ちょうど 9 枚（ほかのカードは失われない）。過去の範囲は ``cards_before`` で切り出す。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V093_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(H.V0_93_CARDS))
        self.assertEqual(set(H.V0_93_CARDS) & set(cards_before(read_extract(), "0.93")), set())

    def test_evolution_bases_exist(self):
        pool = load_card_pool()
        for card, base in ((GLOOM, "ナゾノクサ"), (CROCONAW, "ワニノコ"), (DARK_ARIADOS, "イトマル"), (PILOSWINE, "ウリムー"), (DARK_CROCONAW, "ワニノコ"),
                           (OCTILLERY, "テッポウオ")):
            with self.subTest(card=card):
                self.assertEqual(pool.definitions[card].evolves_from, base)
                state = board(mon(BELOW[card], played_turn=3), hand=(card,))
                evolved = apply_kernel(state, EvolvePokemon(0, uid(state, card), state.players[0].active.pokemon_id))
                self.assertEqual(evolved.cards[evolved.players[0].active.card].card_id, card)
                audited(self, evolved)


class TextCheckTest(unittest.TestCase):
    """3 章: 既存の型に加えた全文は 1 通りずつ。似た文面を取りちがえない。"""

    def test_strange_powder_comma_text_is_one_exact_form(self):
        pool = load_card_pool()
        attack = pool.definitions[GLOOM].attacks[0]
        self.assertEqual(E.DamageThenStatusByCoin(E.CONFUSION, E.SLEEP).check(attack), [])
        self.assertEqual(dict(E.STRANGE_POWDER_COMMA_TEXTS), {(E.CONFUSION, E.SLEEP): (attack.text_ja,)})
        self.assertTrue(E.DamageThenStatusByCoin(E.SLEEP, E.CONFUSION).check(attack))  # 面を入れかえた組では通さない
        self.assertTrue(E.DamageThenStatusByCoin(E.POISON, E.SLEEP).check(attack))

    def test_octazooka_and_blizzard_use_existing_types(self):
        pool = load_card_pool()
        self.assertEqual(E.LASTING_ATTACK_COIN_CHECK_TEXTS, (E.LASTING_ATTACK_COIN_CHECK_TEXT, pool.definitions[OCTILLERY].attacks[1].text_ja))
        self.assertTrue(E.DamageThenAttackCoinCheck().check(pool.definitions[OCTILLERY].attacks[1]))  # 「次の相手の番」の型（えんまく）では通さない
        self.assertEqual(E.DamageThenCoinBenchDamageEitherSide(10).check(pool.definitions[PILOSWINE].attacks[1]), [])
        self.assertEqual(E.ReceivedAttackDamageBonusAttack(20, 1, 2).check(pool.definitions[CROCONAW].attacks[0]), [])
        self.assertEqual(E.ParalyzeOnHeads().check(pool.definitions[OCTILLERY].attacks[0]), [])

    def test_similar_texts_are_not_interchanged(self):
        pool = load_card_pool()
        attack = lambda card, i: pool.definitions[card].attacks[i]
        # きぜつの例外のある・ない文面、発生源がバトル場にいるかぎりの文面を入れかえない（別のカードの括弧書きを補わない）
        self.assertTrue(E.DamageThenPeriodLock(E.LOCK_LEAVE, True, 0, 1, knockout_exception=True).check(attack(CATERPIE, 1)))
        self.assertTrue(E.DamageThenPeriodLock(E.LOCK_LEAVE, True, 0, 1).check(attack(TANGELA, 0)))
        self.assertTrue(E.DamageThenPeriodLock(E.LOCK_LEAVE, True, 0, 1).check(attack(CROCONAW, 1)))
        self.assertTrue(E.DamageThenPeriodLock(E.LOCK_ATTACK, True, 0, None).check(attack(OCTILLERY, 1)))
        with self.assertRaises(ValueError):
            E.DamageThenPeriodLock(E.LOCK_LEAVE, True, 0, 1, True, (SOURCE_LEAVES_ACTIVE,))  # 文面のない組（発生源に追従する消去を足さない）
        # にげるの禁止の型（v0.36・v0.92）で、はなれられない効果を通さない
        for card, i in ((CATERPIE, 1), (TANGELA, 0), (CROCONAW, 1), (GLOOM, 1)):
            with self.subTest(card=card):
                self.assertTrue(E.DamageThenRetreatLockOnHeads().check(attack(card, i)))
                self.assertTrue(E.PeriodLockAttack(E.LOCK_RETREAT, True, 0, None).check(attack(card, i)))
        # かぶりつく（ワザを使うときのコイン）を「ワザを使えない」・えんまくの型で通さない
        self.assertTrue(E.DamageThenAttackCoinCheck().check(attack(DARK_CROCONAW, 0)))
        self.assertTrue(E.DamageThenPeriodLock(E.LOCK_ATTACK, True, 0, None).check(attack(DARK_CROCONAW, 0)))
        # からめとる（ワザを使ったプレイヤーが選ぶ・新しく出てきたポケモン）を、コインで入れ替える型・ふきとばしの型で通さない
        self.assertTrue(E.CoinSwitchOpponentThenStatus(E.PARALYSIS).check(attack(DARK_ARIADOS, 0)))
        self.assertTrue(E.SwitchOpponentThenParalyzeNewOnHeads().check(pool.definitions["PMCG6-007"].attacks[0]))


class MeanLookLabelTest(unittest.TestCase):
    """2 章: くろいまなざしの短い論点名を ML1 から ML2 に訂正した（v0.73 のマスターボールの ML1 と重なっていた）。公開コード・論点・止める時点・件数は変えていない。"""

    def test_labels_are_unique_for_the_two_codes(self):
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        by_ruling: dict[str, set[str]] = {}
        for code, item in links["stop_codes"].items():
            for ruling in item["engine_rulings"]:
                by_ruling.setdefault(ruling["ruling_id"], set()).add(code)
        self.assertEqual(by_ruling["ML1"], {"UNRESOLVED_MASTER_BALL_SHORT_DECK"})
        self.assertEqual(by_ruling["ML2"], {E.MEAN_LOOK_SOURCE_FORM_CODE})
        self.assertEqual(E.MEAN_LOOK_SOURCE_FORM_CODE, "UNRESOLVED_MEAN_LOOK_SOURCE_EVOLVED")
        for ruling, code in NEW_RULINGS:
            self.assertEqual(by_ruling[ruling], {code})
            self.assertEqual(links["stop_codes"][code]["kyuura_disposition"], "not_in_kyuura")

    def test_v0_92_text_and_documents_use_ml2(self):
        self.assertIn("ML2", E.MEAN_LOOK_SOURCE_FORM_REASON)
        self.assertNotIn("ML1", E.MEAN_LOOK_SOURCE_FORM_REASON)
        text = DOC_V092.read_text(encoding="utf-8")
        self.assertNotIn("ML1 |", text)
        self.assertIn("ML2", text)
        self.assertIn("ML1 から ML2 に訂正", text)
        self.assertIn("UNRESOLVED_MASTER_BALL_SHORT_DECK", (ROOT / "docs" / "search-recovery-trainers-v0.73.md").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 4 章: はなれられない効果の期間・にげるの禁止との違い


class LeaveLockTest(unittest.TestCase):
    def test_tangle_thread_locks_from_now_until_the_end_of_the_next_opponent_turn(self):
        state = board(m(CATERPIE, (G,)), opponent=m(ONIX, (F,)))
        done = declare(state, 1, HD)
        lock = effects_of(done.players[1].active, PeriodLeaveLock)
        self.assertEqual([(e.created_turn, e.active_turn, e.end_turn, e.while_source_active, e.ends_on, e.knockout_exception) for e in lock],
                         [(TURN, TURN, TURN + 1, False, (), False)])
        self.assertEqual(len(new_events(state, done, "coin_flip")), 1)
        audited(self, done)
        rejects(self, done, retreat_cmd(done), LEAVE_ACTIVE_PREVENTED, IllegalActionError)  # エネルギーのトラッシュ・こんらんのコインの前
        later = end(done)
        self.assertEqual(effects_of(later.players[1].active, PeriodLeaveLock), [])
        self.assertIn(("period_leave_lock", "expired"), [(e["persistent_effect"], e["reason"]) for e in new_events(done, later, "persistent_effect_removed")])
        tails = declare(state, 1, TL)
        self.assertEqual(effects_of(tails.players[1].active, PeriodLeaveLock), [])

    def test_source_leaving_does_not_end_tangle_or_constrict(self):
        """発生源がはなれたら消えるとは書かれていない（からまるいと・からみつく）。発生源のキャタピーが突風でベンチに移っても、受けたポケモンははなれられない。"""
        for card in (CATERPIE, TANGELA):
            with self.subTest(card=card):
                done = caterpie_locked(card=card, hand=(H.GUST,))
                gusted = answer(play(done, H.GUST), (done.players[1].bench[0].pokemon_id,))
                self.assertEqual(len(effects_of(gusted.players[0].active, PeriodLeaveLock)), 1)
                rejects(self, gusted, retreat_cmd(gusted), LEAVE_ACTIVE_PREVENTED, IllegalActionError)
                audited(self, gusted)

    def test_retreat_lock_only_still_allows_switching(self):
        """にげるの禁止（v0.36・v0.92）は入れ替えを止めない（p.325）。はなれられない効果は止める（AL2）。"""
        retreat_only = board(m(DARK_CROCONAW, (W, W)), opponent=m(ONIX, (F,)), opponent_hand=(H.SWITCH,))
        done = declare(retreat_only, 0)
        rejects(self, done, retreat_cmd(done), "RETREAT_PREVENTED", IllegalActionError)
        switched = answer(play(done, H.SWITCH), (done.players[1].bench[0].pokemon_id,))
        self.assertTrue(new_events(done, switched, "switch"))
        leave = caterpie_locked(hand=(H.SWITCH,))
        stopped(self, leave, lambda s: _play_command(s, H.SWITCH), AL2)

    def test_queries(self):
        done = caterpie_locked()
        active = done.players[0].active
        self.assertEqual(len(leave_locks(done, active)), 1)
        self.assertIsNotNone(leave_lock(done, 0, active))
        self.assertIsNotNone(leave_lock(done, 0, active, knock_out=True))  # きぜつの例外を書いていない
        self.assertIsNone(leave_lock(done, 0, done.players[0].bench[0]))  # ベンチのポケモンは受けていない
        exception = caterpie_locked(card=TANGELA)
        self.assertIsNone(leave_lock(exception, 0, exception.players[0].active, knock_out=True))

    def test_lock_types_are_period_types(self):
        self.assertTrue({PeriodLeaveLock, PeriodAttackCoinCheck} <= set(PERIOD_EFFECT_TYPES) <= set(PERSISTENT_EFFECT_TYPES))
        with self.assertRaises(ValueError):
            PeriodLeaveLock(1, 0, TURN, TURN, TURN + 1, 3, source_left=True)  # 印は「かぎり」の、はなれても消えない効果だけ
        with self.assertRaises(ValueError):
            PeriodLeaveLock(1, 0, TURN, TURN, TURN + 1, 3, knockout_exception=1)


def _play_command(state, card_id, player=None):
    from kyuura_engine import PlayTrainer

    player = state.current_player if player is None else player
    return PlayTrainer(player, uid(state, card_id, player))


# ---------------------------------------------------------------- 4.3 節: きぜつ（例外のある・ない効果）


class KnockOutTest(unittest.TestCase):
    def test_pokemon_check_knockout_with_and_without_the_exception(self):
        """ポケモンチェックのどくで HP 以上になる受けたポケモン: 例外を書いた効果（からみつく）はきぜつの処理を止めない。書いていない効果（からまるいと）は AL1 で、どくのダメージを
        与える前に対戦を止める（別のカードの括弧書きを補わない）。"""
        hp = load_card_pool().definitions[H.RATTATA].hp
        for card, index, halted in ((CATERPIE, 1, True), (TANGELA, 0, False)):
            with self.subTest(card=card):
                state = board(m(card, (G, G)), opponent=m(H.RATTATA, (W,), damage=hp - 20, poison=10))
                done = declare(state, index, HD)
                if halted:
                    self.assertEqual((done.phase, done.halt.code), (Phase.HALTED, AL1))
                    self.assertFalse(new_events(state, done, "poison_damage", "knock_out"))
                else:
                    self.assertTrue(new_events(state, done, "knock_out"))
                audited(self, done)

    def test_attack_knockout_without_the_exception_is_stopped_before_declaration(self):
        """受けたポケモン自身のワザ（でんげきの「うら」の自分へのダメージ）で HP 以上になるなら、きぜつの判定の窓の問い（AL1。先読みが宣言の前に見つける）。HP 以上になったまま
        ワザの途中で効果が動かそうとするのは、きぜつの処理ではない（AL1 の例外の判定に使わない）。"""
        hp = load_card_pool().definitions[H.PIKACHU].hp
        done = caterpie_locked(active=m(H.PIKACHU, (L, L), damage=hp - 20))  # 相手のワザの 10 のあと、残りHP 10
        stopped(self, done, lambda s: _attack(s, 1), AL1)
        exception = caterpie_locked(card=TANGELA, active=m(H.PIKACHU, (L, L), damage=hp - 20))
        knocked = apply_kernel(with_coin_results(exception, TL), _attack(exception, 1))
        self.assertTrue(new_events(exception, knocked, "knock_out"))
        audited(self, knocked)


def _attack(state, index):
    from kyuura_engine import UseAttack

    return UseAttack(state.current_player, index)


# ---------------------------------------------------------------- 4.4 節: バトル場からの移動の共通の経路（代表）


class MovePathTest(unittest.TestCase):
    def test_trainers_whose_only_effect_is_the_move_are_stopped_before_play(self):
        """ポケモンいれかえ・マチス: 効果のすべてが、はなれられない対戦ポケモンの移動。使えるかが決まらない（AL2。手札から出す前）。"""
        for card in (H.SWITCH, H.LT_SURGE_TRAINER):
            with self.subTest(card=card):
                done = caterpie_locked(hand=(card, H.RATTATA))
                stopped(self, done, lambda s, card=card: _play_command(s, card), AL2)

    def test_scoop_up_choice_of_the_locked_active_is_unresolved(self):
        """ポケモン回収: はなれられない対戦ポケモンは選べるが選ぶと止める（AL2。手札にもどせないのに、ついているカードだけをトラッシュする途中の変更を残さない）。控えは選べる。"""
        done = caterpie_locked(hand=(H.SCOOP_UP,))
        asked = play(done, H.SCOOP_UP)
        active, bench = asked.players[0].active.pokemon_id, asked.players[0].bench[0].pokemon_id
        self.assertIn(active, asked.decision.context_value("unresolved_choices"))
        error = rejects(self, asked, ResolveDecision(0, asked.decision.id, (active,)), AL2)
        self.assertIn("バトル場をはなれられない", error.message)
        returned = answer(asked, (bench,))
        self.assertTrue(new_events(asked, returned, "return_basic_to_hand"))
        audited(self, returned)

    def test_super_scoop_up_with_only_the_locked_active_is_stopped_before_the_coin(self):
        done = caterpie_locked(hand=(H.SUPER_SCOOP_UP,), bench=())
        before = len(done.log)
        stopped(self, done, lambda s: _play_command(s, H.SUPER_SCOOP_UP), AL2)
        self.assertEqual(len(done.log), before)

    def test_warp_point_switches_only_the_side_that_can_leave(self):
        """ワープポイント: 相手（プレイヤー 1）の入れ替えは書かれたとおり。使ったプレイヤーの対戦ポケモンははなれられないので、その側の入れ替えは起こらない（選ばせない・移動のログ・
        持続する効果の消去・変わり身の術のトラッシュを起こさない）。"""
        done = caterpie_locked(hand=(H.WARP_POINT,), opponent_bench=(H.RATTATA, H.RATTATA))
        asked = play(done, H.WARP_POINT)
        self.assertEqual(asked.decision.player, 1)
        finished = answer(asked, (asked.decision.options[0],))
        self.assertIsNone(finished.decision)
        switches = new_events(asked, finished, "switch")
        self.assertEqual([e["player"] for e in switches], [1])
        prevented = new_events(asked, finished, "leave_prevented")
        self.assertEqual([(e["player"], e["cause"], e["trainer_card"]) for e in prevented], [(0, E.LEAVE_SWITCH, uid(done, H.WARP_POINT))])
        self.assertEqual(len(effects_of(finished.players[0].active, PeriodLeaveLock)), 1)
        audited(self, finished)

    def test_double_gust_skips_only_the_locked_side(self):
        """ポケモンぎゃくしめい（neo1-075）: 使ったプレイヤーの対戦ポケモンがはなれられないなら、その側の入れ替え（相手が選ぶ）は起こらず、相手の側の入れ替え（使ったプレイヤーが
        選ぶ）は書かれたとおり。"""
        double_gust = "neo1-075"
        done = caterpie_locked(hand=(double_gust,), opponent_bench=(H.RATTATA, H.RATTATA))
        asked = play(done, double_gust)
        self.assertEqual(asked.decision.player, 0)  # 段階 0（相手が選ぶ）は起こらず、段階 1 の使ったプレイヤーの選択
        self.assertEqual([(e["player"], e["cause"]) for e in new_events(done, asked, "leave_prevented")], [(0, E.LEAVE_SWITCH)])
        finished = answer(asked, (asked.decision.options[1],))
        self.assertIsNone(finished.decision)
        self.assertEqual([e["player"] for e in new_events(asked, finished, "switch")], [1])
        self.assertEqual(len(effects_of(finished.players[0].active, PeriodLeaveLock)), 1)
        audited(self, finished)

    def test_fossil_discard_is_refused_while_active_and_locked(self):
        """なにかの化石（HP 10）は相手のワザのダメージで受けたまま残れないので、効果をログつきでのせた盤面で確かめる（すてる前に拒否）。ベンチの化石はすてられる。"""
        state = locked(board(mon(H.MYSTERIOUS_FOSSIL), bench=(mon(H.MYSTERIOUS_FOSSIL), H.RATTATA), opponent=m(CATERPIE, (G,))), 0)
        audited(self, state)
        rejects(self, state, DiscardFromPlay(0, state.players[0].active.pokemon_id), LEAVE_ACTIVE_PREVENTED, IllegalActionError)
        discarded = apply_kernel(state, DiscardFromPlay(0, state.players[0].bench[0].pokemon_id))
        self.assertTrue(new_events(state, discarded, "discard_from_play"))

    def test_attack_moves_of_the_locked_attacker_do_nothing_or_stop_the_coin(self):
        """自分のワザの移動の部分: テレポート（コインなし）は起こらない（選ぶ決定を出さない。ほかの部分は続ける）。けりにげ・くもがくれガス（移動だけを決めるこの要素のコイン）は AL2
        （先読みが宣言の前に見つける）。"""
        teleport = caterpie_locked(active=m(EXEGGUTOR, (P,)))
        done = apply_kernel(teleport, _attack(teleport, 0))
        self.assertIsNone(done.decision)
        self.assertEqual([e["cause"] for e in new_events(teleport, done, "leave_prevented")], [E.LEAVE_SWITCH])
        self.assertFalse(new_events(teleport, done, "switch"))
        audited(self, done)
        for card, index in ((PONYTA_KICK, 0), (KOFFING_SMOG, 1)):
            with self.subTest(card=card):
                state = caterpie_locked(active=m(card, (G, G, R, R)))
                stopped(self, state, lambda s, index=index: _attack(s, index), AL2)

    def test_whirlwind_on_a_locked_target_does_not_ask_and_continues(self):
        """ポッポのかぜおこし（入れ替えは相手が行う）: 相手の対戦ポケモンがはなれられないなら、ダメージは与え、入れ替えの部分は起こらない（選ぶ決定を出さない）。"""
        state = locked(board(mon(PIDGEY_WHIRLWIND, (W, W)), opponent=m(ONIX, (F,))), 1)
        audited(self, state)
        done = apply_kernel(state, _attack(state, 0))
        self.assertIsNone(done.decision)
        self.assertEqual(len(new_events(state, done, "damage")), 1)
        self.assertEqual([e["cause"] for e in new_events(state, done, "leave_prevented")], [E.LEAVE_FORCED_SWITCH])
        self.assertFalse(new_events(state, done, "forced_switch"))

    def test_drag_out_on_a_locked_target_damages_the_unchanged_active(self):
        """わるいゴーリキーのひきずりだす（入れ替えてから「新しい対戦ポケモン」にダメージ）: 入れ替えが起こらないなら、ダメージはそのままのバトル場のポケモンに与える（v0.40 の、入れ替えの
        効果を受けないときの既存の読み方と同じ。選ぶ決定を出さない）。"""
        state = locked(board(m(H.DARK_MACHOKE, (F, F, F), evolved_from=H.ROCKET_MACHOP), opponent=m(ONIX, (F,)), opponent_bench=(H.RATTATA,)), 1)
        audited(self, state)
        target = state.players[1].active.card
        done = apply_kernel(state, _attack(state, 0))
        self.assertIsNone(done.decision)
        self.assertEqual([(e["player"], e["pokemon"], e["amount"]) for e in new_events(state, done, "damage")], [(1, target, 20)])
        self.assertEqual(done.players[1].active.card, target)
        self.assertEqual([e["cause"] for e in new_events(state, done, "leave_prevented")], [E.LEAVE_FORCED_SWITCH])
        self.assertFalse(new_events(state, done, "forced_switch"))
        audited(self, done)

    def test_forced_lightning_burst_does_not_switch_a_locked_opponent(self):
        """［いなびかり］（かならずはたらく）: 相手の対戦ポケモンがはなれられないなら、入れ替える部分は起こらない（相手に選ばせない。止めない）。自然な対戦では起こらない盤面なので、
        効果をログつきでのせて作る。"""
        state = locked(board(mon(RAIKOU), hand=(L,), opponent=m(ONIX, (F,)), opponent_bench=(H.RATTATA,)), 1)
        audited(self, state)
        done = apply_kernel(state, AttachEnergy(0, uid(state, L), state.players[0].active.card))
        self.assertIsNone(done.decision)
        self.assertTrue(new_events(state, done, "pokemon_power")[0]["forced"])
        self.assertEqual([(e["player"], e["cause"]) for e in new_events(state, done, "leave_prevented")], [(1, E.LEAVE_SWITCH)])
        self.assertFalse(new_events(state, done, "switch"))
        audited(self, done)

    def test_powers(self):
        """特殊能力: かけつける・おくびょう（効果のすべてが移動）は AL2（宣言の前）。"""
        done = caterpie_locked(bench=(m(DRAGONITE, evolved_from=[H.DRATINI, H.DRAGONAIR]),))
        stopped(self, done, UsePokemonPower(0, done.players[0].bench[0].pokemon_id, 0), AL2)
        cowardice = caterpie_locked(active=mon(TENTACOOL, (W,), played_turn=1))
        stopped(self, cowardice, UsePokemonPower(0, cowardice.players[0].active.pokemon_id, 0), AL2)

    def test_scram_on_a_locked_pokemon_is_stopped(self):
        """［ずらかる］: からまるいとのダメージで残りHPが「10」になり、そのあと禁止を受けたタケシのオコリザルは、山札にもどれない。もどれないまま、あとではたらくかが決まらない（AL3。
        先読みが宣言の前に見つける）。"""
        hp = load_card_pool().definitions[BROCKS_PRIMEAPE].hp
        # ワザの途中で残りHPが「10」になるなら、既存の SC1（はたらく時点が決まらない）が先に止める（からまるいとの禁止の要素が残っている）
        state = board(m(CATERPIE, (G,)), opponent=mon(BROCKS_PRIMEAPE, (F,), damage=hp - 20, evolved_from=H.BROCKS_MANKEY))
        stopped(self, state, lambda s: _attack(s, 1), "UNRESOLVED_SCRAM_TIMING")
        # ポケモンチェックのどくで残りHPが「10」になる禁止を受けたオコリザル: どくのダメージを与える前に対戦を止める（AL3）
        poisoned = board(m(CATERPIE, (G,)), opponent=mon(BROCKS_PRIMEAPE, (F,), damage=hp - 30, poison=10, evolved_from=H.BROCKS_MANKEY))
        done = declare(poisoned, 1, HD)
        self.assertEqual((done.phase, done.halt.code), (Phase.HALTED, AL3))
        self.assertFalse(new_events(poisoned, done, "poison_damage", "scram"))
        audited(self, done)

    def test_receiver_evolution_and_devolution_end_the_lock(self):
        """受けたポケモンの進化・退化はバトル場をはなれることではない（止めない）。持続する効果は一般の規定（p.310・p.324）で消える。"""
        state = caterpie_locked(active=mon(H.TOTODILE_NEO1, (W,), played_turn=1), hand=(CROCONAW,))
        evolved = apply_kernel(state, EvolvePokemon(0, uid(state, CROCONAW), state.players[0].active.pokemon_id))
        self.assertEqual(effects_of(evolved.players[0].active, PeriodLeaveLock), [])
        self.assertIn(("period_leave_lock", "evolve"), [(e["persistent_effect"], e["reason"]) for e in new_events(state, evolved, "persistent_effect_removed")])
        audited(self, evolved)


# ---------------------------------------------------------------- 5 章: ねばるみつ・へんなこな


class StickyNectarTest(unittest.TestCase):
    def test_one_coin_adds_ten_to_the_base_and_locks(self):
        state = board(m(GLOOM, (G, G, G)), opponent=m(ONIX, (F,)))
        heads = declare(state, 1, HD)
        tails = declare(state, 1, TL)
        self.assertEqual(len(new_events(state, heads, "coin_flip")), 1)
        self.assertEqual([e["amount"] for e in new_events(state, heads, "damage")], [60])  # (20 + 10) × 弱点 2（草。イワークの弱点は草）
        self.assertEqual([e["amount"] for e in new_events(state, tails, "damage")], [40])
        self.assertEqual(len(effects_of(heads.players[1].active, PeriodLeaveLock)), 1)
        self.assertEqual(effects_of(tails.players[1].active, PeriodLeaveLock), [])
        for done in (heads, tails):
            audited(self, done)

    def test_damage_prevented_still_flips_and_locks_but_barrier_is_hc3(self):
        """「ダメージを受けない」相手でも禁止は有効なのでコインを投げる。「ワザをうけない」相手はどちらの要素も無効なので HC3（v0.34）。"""
        shielded = board(m(GLOOM, (G, G, G)), opponent=m(ONIX, (F,), prevent_damage=TURN - 1))
        done = declare(shielded, 1, HD)
        self.assertFalse([e for e in new_events(shielded, done, "damage") if e["amount"]])
        self.assertEqual(len(effects_of(done.players[1].active, PeriodLeaveLock)), 1)
        audited(self, done)

    def test_knocked_out_target_gets_no_lock(self):
        hp = load_card_pool().definitions[ONIX].hp
        state = board(m(GLOOM, (G, G, G)), opponent=m(ONIX, (F,), damage=hp - 60))
        done = declare(state, 1, HD)
        self.assertFalse(new_events(state, done, "persistent_effect_added"))


class StrangePowderTest(unittest.TestCase):
    def test_heads_confuses_tails_sleeps(self):
        state = board(m(GLOOM, (G, G)), opponent=m(ONIX, (F,)))
        heads = declare(state, 0, HD)
        tails = declare(state, 0, TL)
        condition = lambda done: [e["condition"] for e in new_events(state, done, "special_condition")]
        self.assertEqual((condition(heads), condition(tails)), (["confusion"], ["sleep"]))  # ねむりはポケモンチェックのコインで回復しうるので、ログで確かめる
        self.assertEqual([e["source"] for e in new_events(state, heads, "coin_flip")][:1], ["attack"])


# ---------------------------------------------------------------- 6 章: くいつく・からめとる・どくしばり


class JawClampTest(unittest.TestCase):
    def test_lock_is_for_the_next_opponent_turn_while_the_source_is_active(self):
        state = board(m(CROCONAW, (W, W, W)), opponent=m(ONIX, (F,)))
        done = declare(state, 1)
        lock = effects_of(done.players[1].active, PeriodLeaveLock)
        self.assertEqual([(e.active_turn, e.end_turn, e.while_source_active, e.ends_on, e.knockout_exception) for e in lock],
                         [(TURN + 1, TURN + 1, True, (), True)])
        self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [30])
        rejects(self, done, retreat_cmd(done), LEAVE_ACTIVE_PREVENTED, IllegalActionError)
        audited(self, done)

    def test_source_gusted_away_marks_and_returning_is_jc1(self):
        """発生源がはなれても効果は消えない（書かれていない）。はなれているあいだははたらかず、同じ番にもどったら、またはたらくかが決まらない（JC1。すごむの SG1 と同じ形の別のカードの
        問い）。印はログ ``persistent_effect_source_left``。"""
        state = board(m(CROCONAW, (W, W, W)), opponent=m(ONIX, (F, F, F)), opponent_hand=(H.GUST, H.GUST))
        done = declare(state, 1)
        source = done.players[0].active.pokemon_id
        gusted = answer(play(done, H.GUST), (done.players[0].bench[0].pokemon_id,))
        lock = effects_of(gusted.players[1].active, PeriodLeaveLock)
        self.assertEqual([e.source_left for e in lock], [True])
        self.assertEqual(len(new_events(done, gusted, "persistent_effect_source_left")), 1)
        audited(self, gusted)
        retreated = apply_kernel(gusted, _retreat_all(gusted))  # 発生源がバトル場にいないあいだは、はたらかない
        self.assertTrue(new_events(gusted, retreated, "retreat"))
        back = play(gusted, H.GUST)
        back = answer(back, (source,))
        self.assertEqual(back.players[0].active.pokemon_id, source)
        stopped(self, back, _retreat_all(back), JC1)
        audited(self, back)

    def test_source_form_change_is_jc2(self):
        """発生源の姿が与えたときと違う（進化・退化）なら、「このカード」がバトル場にいることになるかが決まらない（JC2。くろいまなざしの ML2 と同じ形の別のカードの問い）。発生源の
        進化・退化そのものは止めない（その時点では結果が変わらない）。"""
        state = board(m(CROCONAW, (W, W, W)), opponent=m(ONIX, (F, F, F)))
        done = declare(state, 1)
        changed = done.clone()
        source = changed.players[0].active
        source.card, source.evolution_stack = source.evolution_stack[-1], source.evolution_stack[:-1]  # 退化したのと同じいちばん上のカード（盤面を作る）
        with self.assertRaises(UnsupportedError) as caught:
            leave_lock(changed, 1, changed.players[1].active)
        self.assertEqual(caught.exception.code, JC2)

    def test_knockout_exception(self):
        hp = load_card_pool().definitions[H.PIKACHU].hp
        state = board(m(CROCONAW, (W, W, W)), opponent=m(H.PIKACHU, (L, L), damage=hp - 40))
        done = declare(state, 1)
        attacked = apply_kernel(with_coin_results(done, TL), _attack(done, 1))  # でんげきの「うら」で自分に 10（例外のある効果。きぜつの処理を止めない）
        self.assertTrue(new_events(done, attacked, "knock_out"))
        audited(self, attacked)


def _retreat_all(state):
    from kyuura_engine import Retreat

    p = state.players[state.current_player]
    return Retreat(state.current_player, tuple(p.active.energy), p.bench[0].card)


class EntangleTest(unittest.TestCase):
    def test_attacker_chooses_then_coin_paralyzes_the_new_active(self):
        state = board(m(DARK_ARIADOS, (G,)), opponent=m(ONIX, (F,)), opponent_bench=(H.RATTATA, H.CHANSEY))
        asked = declare(state, 0)
        self.assertEqual((asked.decision.kind, asked.decision.player, asked.decision.options),
                         (FORCED_SWITCH, 0, tuple(p.pokemon_id for p in state.players[1].bench)))
        chosen = asked.decision.options[1]
        for coin, paralyzed in ((HD, True), (TL, False)):
            with self.subTest(coin=coin):
                done = apply_kernel(with_coin_results(asked, coin), ResolveDecision(0, asked.decision.id, (chosen,)))
                self.assertEqual(done.players[1].active.pokemon_id, chosen)
                self.assertEqual(done.players[1].active.conditions.paralyzed, paralyzed)
                self.assertFalse(any(b.conditions.names() for b in done.players[1].bench))  # もとの対戦ポケモンをマヒにしない
                events = [e["kind"] for e in new_events(asked, done, "forced_switch", "coin_flip", "special_condition")]
                self.assertEqual(events[:2], ["forced_switch", "coin_flip"])
                audited(self, done)

    def test_no_bench_fails_without_coin(self):
        """相手に控えがいないとき、このワザは失敗する（ワザの失敗。宣言でき、コインを投げない）。別のカードの「このワザは使えない」（使うための条件）とは違う。"""
        state = board(m(DARK_ARIADOS, (G,)), opponent=m(ONIX, (F,)), opponent_bench=())
        done = declare(state, 0)
        self.assertEqual([e["reason"] for e in new_events(state, done, "attack_failed")], [E.ENTANGLE_NO_BENCH])
        self.assertFalse(new_events(state, done, "coin_flip"))

    def test_unswitched_target_is_not_the_new_pokemon(self):
        """入れ替わらなかった（相手の対戦ポケモンがはなれられない）なら、もとの相手を「新しく出てきたポケモン」にしない（コインを投げず、マヒにしない。決定も出さない）。"""
        state = locked(board(m(DARK_ARIADOS, (G,)), opponent=m(ONIX, (F,))), 1)
        done = apply_kernel(state, _attack(state, 0))
        self.assertIsNone(done.decision)
        self.assertFalse(new_events(state, done, "coin_flip", "special_condition", "forced_switch"))
        self.assertEqual([e["cause"] for e in new_events(state, done, "leave_prevented")], [E.LEAVE_FORCED_SWITCH])


class PoisonBindTest(unittest.TestCase):
    def test_poison_then_separate_coin_for_the_lock(self):
        state = board(m(DARK_ARIADOS, (G, G, G)), opponent=m(ONIX, (F,)))
        for coin, locks in ((HD, 1), (TL, 0)):
            with self.subTest(coin=coin):
                done = declare(state, 1, coin)
                self.assertIsNotNone(done.players[1].active.conditions.poison)  # どくはコインによらない
                self.assertEqual(len(new_events(state, done, "coin_flip")), 1)
                self.assertEqual([e.knockout_exception for e in effects_of(done.players[1].active, PeriodLeaveLock)], [True] * locks)
                audited(self, done)

    def test_knocked_out_target_gets_neither_and_no_coin(self):
        hp = load_card_pool().definitions[ONIX].hp
        state = board(m(DARK_ARIADOS, (G, G, G)), opponent=m(ONIX, (F,), damage=hp - 60))
        done = declare(state, 1)
        self.assertFalse(new_events(state, done, "coin_flip", "special_condition", "persistent_effect_added"))


# ---------------------------------------------------------------- 7 章: こおりつかせる・かぶりつく・オクタンほう


class FreezeTest(unittest.TestCase):
    def test_lasting_attack_lock_ends_only_with_the_receiver(self):
        state = board(m(PILOSWINE, (W, W)), opponent=m(ONIX, (F,)), opponent_hand=(H.SWITCH,), opponent_bench=(H.RATTATA,))
        done = declare(state, 0, HD)
        lock = effects_of(done.players[1].active, PeriodAttackLock)
        self.assertEqual([(e.active_turn, e.end_turn, e.ends_on) for e in lock], [(TURN, None, ())])
        rejects(self, done, _attack(done, 0), "ATTACK_PREVENTED", IllegalActionError)
        two_later = end(end(done))
        self.assertEqual(len(effects_of(two_later.players[1].active, PeriodAttackLock)), 1)  # 次の相手の番だけで期限切れにしない
        rejects(self, two_later, _attack(two_later, 0), "ATTACK_PREVENTED", IllegalActionError)
        switched = answer(play(done, H.SWITCH), (done.players[1].bench[0].pokemon_id,))
        self.assertEqual(effects_of(switched.players[1].bench[0], PeriodAttackLock), [])
        audited(self, two_later)

    def test_source_leaving_does_not_end_it(self):
        state = board(m(PILOSWINE, (W, W)), opponent=m(ONIX, (F,)), opponent_hand=(H.GUST,))
        done = declare(state, 0, HD)
        gusted = answer(play(done, H.GUST), (done.players[0].bench[0].pokemon_id,))
        self.assertEqual(len(effects_of(gusted.players[1].active, PeriodAttackLock)), 1)


class ClampingJawTest(unittest.TestCase):
    def test_retreat_lock_and_attack_coin_without_a_giving_coin(self):
        state = board(m(DARK_CROCONAW, (W, W)), opponent=m(ONIX, (F, F)))
        done = declare(state, 0)
        self.assertFalse(new_events(state, done, "coin_flip"))
        kinds = sorted(type(e).__name__ for e in done.players[1].active.persistent_effects)
        self.assertEqual(kinds, ["PeriodAttackCoinCheck", "PeriodRetreatLock"])
        self.assertEqual({(e.active_turn, e.end_turn, e.ends_on) for e in done.players[1].active.persistent_effects}, {(TURN + 1, TURN + 1, (SOURCE_LEAVES_ACTIVE,))})
        rejects(self, done, retreat_cmd(done), "RETREAT_PREVENTED", IllegalActionError)
        heads = declare(done, 0, HD)
        tails = declare(done, 0, TL)
        self.assertTrue(new_events(done, heads, "damage"))
        self.assertEqual([e["reason"] for e in new_events(done, tails, "attack_failed")], ["attack_check"])
        self.assertEqual([e["persistent_effect"] for e in new_events(done, heads, "attack_check")], ["period_attack_coin_check"])
        for state_ in (done, heads, tails):
            audited(self, state_)

    def test_confusion_is_ac6_and_two_checks_are_ac13(self):
        state = board(m(DARK_CROCONAW, (W, W)), opponent=m(ONIX, (F, F), confusion=True))
        done = declare(state, 0)
        stopped(self, done, _attack(done, 0), AC6)

    def test_source_or_receiver_leaving_ends_both_and_returning_does_not_restore(self):
        state = board(m(DARK_CROCONAW, (W, W)), opponent=m(ONIX, (F, F)), opponent_hand=(H.GUST, H.GUST))
        done = declare(state, 0)
        source = done.players[0].active.pokemon_id
        gusted = answer(play(done, H.GUST), (done.players[0].bench[0].pokemon_id,))
        self.assertEqual(gusted.players[1].active.persistent_effects, ())
        self.assertEqual(sorted((e["persistent_effect"], e["reason"]) for e in new_events(done, gusted, "persistent_effect_removed")),
                         [("period_attack_coin_check", "source_left_active"), ("period_retreat_lock", "source_left_active")])
        back = answer(play(gusted, H.GUST), (source,))
        self.assertEqual(back.players[1].active.persistent_effects, ())
        audited(self, back)

    def test_source_card_peeled_by_devolution_is_cj1(self):
        state = board(m(DARK_CROCONAW, (W, W)), opponent=m(ONIX, (F, F)))
        done = declare(state, 0)
        changed = done.clone()
        source = changed.players[0].active
        source.card, source.evolution_stack = source.evolution_stack[-1], source.evolution_stack[:-1]
        with self.assertRaises(UnsupportedError) as caught:
            apply_kernel(changed, _attack(changed, 0))
        self.assertEqual(caught.exception.code, CJ1)

    def test_old_attack_coin_checks_keep_their_terms(self):
        self.assertEqual(E.DamageThenAttackCoinCheck().attack_check_terms(), (AttackCoinCheck, False))
        self.assertEqual(E.DamageThenLastingAttackCoinCheckOnHeads().attack_check_terms(), (AttackCoinCheck, False, True))


class OctazookaTest(unittest.TestCase):
    def test_giving_coin_and_later_attack_coins_are_separate_and_lasting(self):
        state = board(m(OCTILLERY, (W, W, W)), opponent=m(ONIX, (F, F)))
        done = declare(state, 1, HD)
        checks = effects_of(done.players[1].active, AttackCoinCheck)
        self.assertEqual([(e.lasting, e.single_use, e.active_turn) for e in checks], [(True, False, TURN + 1)])
        first = declare(done, 0, HD)
        self.assertEqual([e["persistent_effect"] for e in new_events(done, first, "attack_check")], ["attack_coin_check"])
        mine = end(first)
        again = end(mine)
        self.assertEqual(len(effects_of(again.players[1].active, AttackCoinCheck)), 1)  # 1 回で消えない
        audited(self, again)


# ---------------------------------------------------------------- 11 章: 保存・書き出し・観測・先読み


class StateTest(unittest.TestCase):
    def test_copies_and_export(self):
        done = caterpie_locked()
        jaw = declare(board(m(CROCONAW, (W, W, W)), opponent=m(ONIX, (F, F, F)), opponent_hand=(H.GUST,)), 1)
        marked = answer(play(jaw, H.GUST), (jaw.players[0].bench[0].pokemon_id,))
        for state in (done, marked):
            for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
                self.assertEqual(state_to_dict(copied, format_version=24), state_to_dict(state, format_version=24))
        written = state_to_dict(marked, format_version=24)["players"][1]["active"]["persistent_effects"]
        self.assertEqual([(w["effect"], w.get("knockout_exception"), w.get("source_left"), w.get("while_source_active")) for w in written],
                         [("period_leave_lock", True, True, True)])
        self.assertIn(24, FORMAT_VERSIONS)  # v0.99: 今の最新の形式（25）は tests/test_catalog_contract.py。この版の項目は形式 24 で表す（形式を増やしていない）
        with self.assertRaises(ValueError):
            state_to_dict(done, format_version=7)
        for viewer in (0, 1):
            self.assertEqual(observe(done, viewer)["players"][0]["active"]["persistent_effects"], ["period_leave_lock"])
        self.assertIn("v0.93 のバトル場をはなれられない効果・手順 4 のコイン", legacy_unknown_features(done, done.players[0].active))
        audited(self, marked)

    def test_rejected_answer_keeps_state_log_and_rng(self):
        asked = play(caterpie_locked(hand=(H.SCOOP_UP,)), H.SCOOP_UP)
        rejects(self, asked, ResolveDecision(0, asked.decision.id, (asked.players[0].active.pokemon_id,)), AL2)

    def test_question_table(self):
        self.assertEqual((QUESTIONS["leave_locked_coin"].code, QUESTIONS["leave_lock_knockout"].code, QUESTIONS["leave_lock_scram"].code), (AL2, AL1, AL3))


class EntangleResumeTest(unittest.TestCase):
    """8 章: 決定をまたぐ保存（clone・deepcopy・pickle）から再開しても、入れ替え・コイン・マヒを繰り返さず、同じ結果になる。不正な答えは状態・ログ・乱数を変えない。"""

    def test_resume_from_copies(self):
        state = board(m(DARK_ARIADOS, (G,)), opponent=m(ONIX, (F,)), opponent_bench=(H.RATTATA, H.CHANSEY))
        asked = with_coin_results(declare(state, 0), HD)
        chosen = asked.decision.options[0]
        expected = state_to_dict(apply_kernel(asked, ResolveDecision(0, asked.decision.id, (chosen,))), format_version=24)
        for copied in (asked.clone(), copy.deepcopy(asked), pickle.loads(pickle.dumps(asked))):
            self.assertEqual(state_to_dict(apply_kernel(copied, ResolveDecision(0, copied.decision.id, (chosen,))), format_version=24), expected)
        rejects(self, asked, ResolveDecision(0, asked.decision.id, (asked.players[1].active.pokemon_id,)), "INVALID_CHOICE", IllegalActionError)
        rejects(self, asked, ResolveDecision(1, asked.decision.id, (chosen,)), "NOT_YOUR_DECISION", IllegalActionError)


class OpponentLockedTrainerTest(unittest.TestCase):
    """自然な対戦では起こらない盤面（自分の番に相手の対戦ポケモンがはなれられない）: 突風は効果のすべてが移動なので AL2（手札から出す前）。"""

    def test_gust_is_stopped(self):
        state = locked(board(m(ONIX, (F,)), hand=(H.GUST,), opponent=m(CATERPIE, (G,))), 1)
        audited(self, state)
        stopped(self, state, lambda s: _play_command(s, H.GUST), AL2)


class HiddenCardTest(unittest.TestCase):
    """8 章: 相手のうらのカード（マチスの秘策）について、選べるものの数・止める選択・コインは本当のカードによらない。入れ替えで呼び出すことではおもてにせず（v0.67 の既存の扱い）、
    新しく出てきたポケモンとしてマヒの効果を受ける時におもてにし、たねポケモンでなければトラッシュする。"""

    def setUp(self):
        from tests import test_secret_plan_v0_67 as SP

        self.SP = SP

    def test_entangle_choice_does_not_depend_on_the_face_down_card(self):
        asked = {}
        for hidden in (H.PLUSPOWER, H.RATTATA):
            with self.subTest(hidden=hidden):
                state = self.SP.opponent_turn(self.SP.place(self.SP.board(hand=(hidden,), opponent=m(DARK_ARIADOS, (G,)), turn_number=TURN), hidden))
                asking = apply_kernel(state, _attack(state, 0))
                pid = self.SP.face_down(state)[0].pokemon_id
                asked[hidden] = (asking.decision.options, asking.decision.context_value("unresolved_choices", ()))
                done = apply_kernel(with_coin_results(asking, HD), ResolveDecision(1, asking.decision.id, (pid,)))
                kinds = [e["kind"] for e in new_events(asking, done, "forced_switch", "coin_flip", "secret_plan_revealed")]
                self.assertEqual(kinds, ["forced_switch", "coin_flip", "secret_plan_revealed"])
                self.assertEqual([e["cause"] for e in new_events(asking, done, "secret_plan_revealed")], ["paralysis"])
                self.assertEqual(done.players[0].find_by_pokemon_id(pid) is not None, hidden == H.RATTATA)
                audited(self, done)
        self.assertEqual(asked[H.PLUSPOWER], asked[H.RATTATA])


class NoCardIdBranchTest(unittest.TestCase):
    def test_engine_and_resolution_have_no_card_id_branches(self):
        for path in [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]:
            text = path.read_text(encoding="utf-8")
            for card in H.V0_93_CARDS:
                with self.subTest(path=path.name, card=card):
                    self.assertNotIn(f'"{card}"', text)


class DocumentTest(unittest.TestCase):
    def test_document_lists_the_cards_rulings_and_counts(self):
        text = DOC.read_text(encoding="utf-8")
        for card in H.V0_93_CARDS:
            self.assertIn(card, text)
        for ruling, code in (*NEW_RULINGS, ("ML2", E.MEAN_LOOK_SOURCE_FORM_CODE)):
            self.assertIn(ruling, text)
            self.assertIn(code, text)
        for word in ("1,136", "LEAVE_ACTIVE_PREVENTED", "leave_prevented", "persistent_effect_source_left", "SG1", "HC3", "AC6", "AC13", "Z23"):
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()

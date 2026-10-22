"""v0.82: 場からトラッシュに置かれたエネルギーカードの共通の処理と、リサイクルエネルギー・エコロジム・エネルギーカードをトラッシュするワザを持つポケモン 18 枚
（docs/energy-discard-return-v0.82.md）。

- 場からトラッシュに置く経路（ワザ・特殊能力・トレーナー・スタジアム・にげる・きぜつ・ルールの処理）は、どれも動かす前に ``effects.energy_discard_plan``（その時点の場で、
  手札にもどすカードと理由を決める）を、置いてログを残したあとに ``effects.return_discarded_energy`` を呼ぶ。原因と、実際に使ったプレイヤーは記録で運ぶ（ログを読み直さない）
- リサイクルエネルギーは、どの原因でも、場からトラッシュに置かれたら持ち主の手札にもどす。手札・山札からのトラッシュ・もとからトラッシュにあったカードには当たらない
- エコロジムは、相手のワザ・特殊能力・トレーナーでトラッシュされた「無色」以外のエネルギーカードだけ（きぜつ・にげる・自分のワザは当たらない）
- ひかるリザードンのルール文「デッキに1枚まで」は、そのカードの名前の枚数の上限（ほかのルール文のあるポケモンは今までどおり未対応）

カードはどれも kyuura データの採用（採用したデータのコミット 7d3f4ca。処理に使う文面は kyuura の印刷の文面）。公式ガイドブックは読んでいない。
"""

from __future__ import annotations

import copy
import pathlib
import pickle
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy,
    IllegalActionError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UseAttack,
    check_invariants,
    new_game,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    ATTACH_FROM_DECK,
    ATTACH_TO_BENCH,
    DISCARD_ENERGY,
    OPTIONAL_DISCARD_ALL,
    SELECT_POKEMON,
)
from kyuura_engine.deck import deck_problems
from kyuura_engine.observation import (
    HIDDEN_COUNT_KINDS,
    OPTION_MEANINGS,
    PUBLIC_EVENTS,
    observe,
)
from tests import helpers as H
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.test_neo_trainer_components_v0_80 import (
    audited,
    mon,
    new_events,
    rejects,
    snapshot,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "energy-discard-return-v0.82.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
TURN = 7
W, F, L, P, G, FT = H.WATER, H.FIRE, H.LIGHTNING, H.PSYCHIC, H.GRASS, H.FIGHTING
RE, ECO = H.RECYCLE_ENERGY, H.ECOGYM
DCE, RAINBOW = H.DOUBLE_COLORLESS_ENERGY, H.RAINBOW_ENERGY
CYNDAQUIL, PONYTA, MAGMAR, RAPIDASH = "neo1-018", "ES3-011", "ES3-012", "QSG-011"
RAICHU_IP, PIKACHU_PR, RAICHU_NEO, FLAAFFY, LUGIA = "IP1-003", "PR1-062", "neo3-025", "neo1-041", "neo1-072"
SHINING_CHARIZARD, FLAREON, MOLTRES_PR, QUILAVA, QUAGSIRE = "neo4-025", "neo4-019", "PR1-071", "PF1-005", "neo3-014"
WOOPER, MAREEP, EEVEE = "neo3-069", "neo1-062", H.EEVEE


def board(active, *, bench=(H.RATTATA,), opponent=None, opponent_bench=(H.RATTATA,), hand=(), opponent_hand=(), deck=None, discard=(), current=0):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": list(deck if deck is not None else [W] * 10), "discard": list(discard), "prizes": 6}
    them = {"active": opponent or mon(H.RATTATA), "bench": list(opponent_bench), "hand": list(opponent_hand), "deck": [W] * 10, "prizes": 6}
    return build_test_state([me, them], turn_number=TURN, current_player=current)


def answer(state, choices, **options):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)), **options)


def attack(state, index, coins=(), **options):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, UseAttack(state.current_player, index), **options)


def play(state, card_id, player=0):
    uid = next(u for u in state.players[player].hand if state.cards[u].card_id == card_id)
    return apply_kernel(state, PlayTrainer(player, uid))


def returned(before, after):
    return [(e["card"], tuple(e["reasons"]), e["cause"], e.get("by_player")) for e in new_events(before, after, "energy_returned_to_hand")]


def card_total(state):
    return sorted(state.cards)


def uid_of(state, card_id, player=0, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def all_uids(state):
    found = []
    for p in state.players:
        found += p.hand + p.deck + p.discard + [c for c in p.prizes]
        for pokemon in p.in_play():
            found += list(pokemon.cards()) + list(pokemon.energy) + [t.card for t in pokemon.trainers]
    if state.stadium is not None:
        found.append(state.stadium.card)
    return sorted(found)


def actual_name(card_id):
    return load_card_pool().get(card_id).name_ja


def wooper_id():
    pool = load_card_pool()
    return next(c for c in pool.playable_ids if pool.get(c).name_ja == "ウパー")


def mareep_id():
    pool = load_card_pool()
    return next(c for c in pool.playable_ids if pool.get(c).name_ja == "メリープ")


# ---------------------------------------------------------------- 登録・数・写し


class RegistrationTest(unittest.TestCase):
    def test_all_twenty_are_supported(self):
        pool = load_card_pool()
        for card in H.V0_82_CARDS:
            with self.subTest(card=card):
                self.assertIn(card, pool.playable_ids)
        self.assertEqual(read_extract()["pool_v0_82"], list(H.V0_82_CARDS))
        attacks = [k for k in E.DEFAULT_EFFECTS.attack_keys() if k.card_id in H.V0_82_POKEMON]
        self.assertEqual(len(attacks), 33)
        self.assertIsInstance(E.DEFAULT_EFFECTS.energy_entry(RE).effect, E.RecycleEnergy)
        self.assertIsInstance(E.DEFAULT_EFFECTS.trainer_entry(ECO).effect, E.EnergyReturnStadium)

    def test_counts(self):
        pool = load_card_pool()
        categories = Counter(pool.get(c).category for c in pool.playable_ids)
        self.assertEqual((len(pool.playable_ids), categories["pokemon"], categories["trainer"], categories["energy"]), (1039, 743, 260, 36))  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた
        self.assertEqual(len(E.DEFAULT_EFFECTS.attack_keys()), 1267)  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた
        self.assertEqual(len(E.DEFAULT_EFFECTS.power_keys()), 79)  # v0.84 でポケモン 12 枚・ポケモン育て屋夫婦を加えた
        stadiums = [c for c in E.DEFAULT_EFFECTS.trainer_ids() if getattr(E.DEFAULT_EFFECTS.trainer_entry(c).effect, "is_stadium", False)]
        self.assertEqual(len(stadiums), 41)
        self.assertEqual(len(read_extract()["cards"]), 1039)  # v0.83 でポケモン 18 枚（ワザ 33）を加えた  # v0.84 でポケモン 12 枚（ワザ 19・特殊能力 5）・ポケモン育て屋夫婦を加えた

    def test_new_pokemon_names(self):
        pool = load_card_pool()
        before = {pool.get(c).name_ja for c in pool.playable_ids if c not in H.V0_82_CARDS}
        self.assertEqual({pool.get(c).name_ja for c in H.V0_82_POKEMON} - before, {"ひかるリザードン", "やさしいブースター"})

    def test_unregistered_without_the_v0_82_entries(self):
        keys = [k for k in E.DEFAULT_EFFECTS.attack_keys() if k.card_id in H.V0_82_POKEMON]
        registry = E.DEFAULT_EFFECTS.without_attacks(E.DEFAULT_EFFECTS.id, keys)
        registry = registry.without_energies(registry.id, (RE,)).without_trainers(registry.id, (ECO,))
        from kyuura_engine.cards import pool_from_extract

        pool = pool_from_extract(read_extract(), registry)
        for card in H.V0_82_CARDS:
            with self.subTest(card=card):
                self.assertNotIn(card, pool.playable_ids)
        self.assertEqual(len(pool.playable_ids), 1019)  # v0.84 でポケモン 12 枚・ポケモン育て屋夫婦を加えた  # v0.83 でポケモン 18 枚を加えた（v0.82 の時点は 988）

    def test_same_data_groups_share_entries(self):
        groups = {"PRN-007": CYNDAQUIL, "PRN-010": CYNDAQUIL, "QSG-010": PONYTA, "QSG-012": MAGMAR}
        self.assertEqual(dict(E.SAME_DATA_CARDS_V0_82), groups)
        for new, original in groups.items():
            for index in (0, 1):
                self.assertIs(E.DEFAULT_EFFECTS.attack_entry(new, index), E.DEFAULT_EFFECTS.attack_entry(original, index))
        # ほかの版のポニータ（第1弾・第4弾）とはまとめない
        self.assertIsNot(E.DEFAULT_EFFECTS.attack_entry("PMCG1-016", 0), E.DEFAULT_EFFECTS.attack_entry(PONYTA, 0))

    def test_no_card_id_branches_in_engine(self):
        for path in ("kyuura_engine/engine.py", *sorted(str(p.relative_to(ROOT)) for p in (ROOT / "kyuura_engine" / "resolution").glob("*.py"))):
            text = (ROOT / path).read_text(encoding="utf-8")
            for card in H.V0_82_CARDS:
                self.assertNotIn(f'"{card}"', text, path)

    def test_observation_tables(self):
        self.assertEqual(OPTION_MEANINGS[OPTIONAL_DISCARD_ALL], "number")
        for event in ("energy_returned_to_hand", "discard_energy_declined"):
            self.assertIn(event, PUBLIC_EVENTS)
        self.assertIn(ATTACH_FROM_DECK, HIDDEN_COUNT_KINDS)


class TightenedChecksTest(unittest.TestCase):
    """v0.81 までの型の確かめが形だけで、ルギアの「エレメンタルブラスト」を炎 1 枚の型（``DiscardEnergyThenDamage``）にしても通っていた。説明の全文を照らす。"""

    def attack(self, card_id, index=0):
        return load_card_pool().get(card_id).attacks[index]

    def test_lugia_is_not_a_single_fire_discard(self):
        self.assertNotEqual(E.DiscardEnergyThenDamage(EnergyType.FIRE).check(self.attack(LUGIA)), [])
        self.assertNotEqual(E.DiscardEnergyThenDamage(EnergyType.FIRE).check(self.attack(SHINING_CHARIZARD)), [])
        self.assertEqual(E.DiscardEnergyThenDamage(EnergyType.FIRE).check(self.attack(QUILAVA)), [])

    def test_existing_registrations_still_pass(self):
        pool = load_card_pool()
        for key in E.DEFAULT_EFFECTS.attack_keys():
            entry = E.DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
            if isinstance(entry.effect, (E.DiscardEnergyThenDamage, E.DiscardAllThenCoinDamage, E.DamageThenMoveOneEnergyToBench)):
                with self.subTest(key=key):
                    self.assertEqual(entry.effect.check(pool.get(key.card_id).attacks[key.attack_index]), [])

    def test_wrong_registrations_are_rejected(self):
        # 枚数・色・扱い・ダメージの数が登録と違う
        self.assertNotEqual(E.DiscardEnergyThenDamage(EnergyType.FIRE, "zero").check(self.attack(QUILAVA)), [])
        self.assertNotEqual(E.DiscardEnergyThenDamage(EnergyType.LIGHTNING).check(self.attack(QUILAVA)), [])
        self.assertNotEqual(E.DiscardAllThenCoinDamage(EnergyType.LIGHTNING, 20).check(self.attack(FLAAFFY)), [])
        self.assertNotEqual(E.DiscardAllThenCoinDamage(EnergyType.FIRE, 30).check(self.attack(FLAAFFY)), [])
        # 10まんボルト（すべて・コインなし）を、コインの「うら」ですべてトラッシュする型にしない
        self.assertNotEqual(E.DamageThenDiscardAllOnTails(None).check(self.attack(PIKACHU_PR, 1)), [])
        self.assertNotEqual(E.DamageThenDiscardAllEnergyCards().check(load_card_pool().get("PMCG5-032").attacks[0]), [])
        # ひばなの 2 つの書き方を取りちがえない
        self.assertNotEqual(E.CoinDiscardEnergyCardThenDamage("fail").check(self.attack(CYNDAQUIL)), [])
        self.assertNotEqual(E.CoinDiscardEnergyCardThenDamage("none").check(self.attack(PONYTA, 1)), [])
        # 色ごとの型の組・ダメージの数
        self.assertNotEqual(E.DiscardEachTypeThenDamage((EnergyType.FIRE, EnergyType.LIGHTNING)).check(self.attack(LUGIA)), [])
        self.assertNotEqual(E.DiscardEachTypeThenDamage((EnergyType.FIRE, EnergyType.LIGHTNING), 20).check(self.attack(SHINING_CHARIZARD)), [])
        self.assertNotEqual(E.OptionalDiscardEnergyBonusDamage(EnergyType.FIRE, 20, True, None).check(self.attack(MAGMAR)), [])
        self.assertNotEqual(E.OptionalDiscardEnergyBonusDamage(EnergyType.FIRE, 20, False, 3).check(self.attack(RAPIDASH)), [])
        self.assertNotEqual(E.OptionalDiscardAllSetDamage(EnergyType.LIGHTNING, 40).check(self.attack(RAICHU_NEO, 1)), [])
        self.assertNotEqual(E.CoinsDiscardThenBonusDamage(EnergyType.FIRE, 3, 20).check(self.attack(FLAREON, 1)), [])
        self.assertNotEqual(E.DamageThenChosenBenchCoinDamage(2, 20).check(self.attack(QUILAVA, 1)), [])
        self.assertNotEqual(E.ChooseBenchThenAttachFromDeck(EnergyType.WATER).check(self.attack(FLAREON)), [])


class ShiningCharizardDeckTest(unittest.TestCase):
    """ルール文「「ひかるリザードン」はデッキに1枚までしか入れることができません。」（同じ名前の枚数の上限。ひかるポケモン全体の上限にしない）。"""

    def deck(self, copies):
        return [SHINING_CHARIZARD] * copies + [H.RATTATA] * 4 + [F] * (56 - copies)

    def test_zero_and_one_are_legal_two_is_not(self):
        pool = load_card_pool()
        self.assertEqual(pool.get(SHINING_CHARIZARD).deck_limit, 1)
        self.assertEqual(deck_problems(self.deck(0)), [])
        self.assertEqual(deck_problems(self.deck(1)), [])
        problems = deck_problems(self.deck(2))
        self.assertEqual(len(problems), 1)
        self.assertIn("TOO_MANY_COPIES", problems[0])
        self.assertIn("1 枚まで", problems[0])

    def test_it_is_a_basic_and_not_the_stage2_charizard(self):
        pool = load_card_pool()
        definition = pool.get(SHINING_CHARIZARD)
        self.assertTrue(definition.is_basic_pokemon)
        self.assertNotEqual(definition.name_ja, pool.get("PMCG1-021").name_ja)
        self.assertIsNone(pool.get("PMCG1-021").deck_limit)
        # ひかるリザードン 1 枚と、ふつうのリザードン 4 枚は別の名前（いっしょに数えない）
        cards = [SHINING_CHARIZARD] + ["PMCG1-021"] * 4 + ["PMCG1-017"] * 4 + ["PMCG1-014"] * 4 + [F] * 47
        self.assertEqual(deck_problems(cards), [])

    def test_other_rule_texts_stay_unsupported(self):
        from kyuura_engine.cards import _deck_limit_rule

        self.assertEqual(_deck_limit_rule("ひかるリザードン", "「ひかるリザードン」はデッキに1枚までしか入れることができません。"), 1)
        self.assertIsNone(_deck_limit_rule("ひかるリザードン", "「ひかるギャラドス」はデッキに1枚までしか入れることができません。"))
        self.assertIsNone(_deck_limit_rule("ひかるリザードン", "「ひかるリザードン」はデッキに2枚までしか入れることができません。"))
        from kyuura_engine.cards import classify_record

        record = copy.deepcopy(next(c for c in read_extract()["cards"] if c["id"] == SHINING_CHARIZARD))
        record["pokemon"]["rules_text"]["ja"] = "「ひかるリザードン」はデッキに1枚までしか入れることができません。このカードは進化できない。"
        self.assertIn("ルール文のあるポケモンは未実装", classify_record(record).unsupported_reasons)

    def test_new_game_with_one_copy(self):
        cards = [SHINING_CHARIZARD] + [H.RATTATA] * 4 + [F] * 30 + [L] * 25
        state = new_game(cards, list(H.FIRE_DECK), seed=3)
        self.assertEqual(check_invariants(state), [])


# ---------------------------------------------------------------- リサイクルエネルギー


class RecycleEnergyTest(unittest.TestCase):
    def test_units_and_not_basic(self):
        state = board(mon(H.RATTATA, (RE,)))
        active = state.players[0].active
        self.assertEqual(E.attached_units(state, active), [frozenset({EnergyType.COLORLESS})])
        self.assertFalse(state.card_def(active.energy[0]).is_basic_energy)
        self.assertIsNone(state.card_def(active.energy[0]).provides)

    def test_attach_once_per_turn(self):
        state = board(mon(H.RATTATA), hand=(RE, RE))
        after = apply_kernel(state, AttachEnergy(0, state.players[0].hand[0], state.players[0].active.card))
        self.assertEqual(len(after.players[0].active.energy), 1)
        rejects(self, after, AttachEnergy(0, after.players[0].hand[0], after.players[0].active.card), "ENERGY_ALREADY_ATTACHED", IllegalActionError)

    def test_own_attack_discard_returns_to_hand(self):
        state = board(mon(CYNDAQUIL, (F, RE)))
        choosing = attack(state, 0, (TL,))
        recycle = state.players[0].active.energy[1]
        done = answer(choosing, (recycle,))
        self.assertEqual(returned(choosing, done), [(recycle, ("recycle_energy",), "attack", 0)])
        self.assertIn(recycle, done.players[0].hand)
        self.assertNotIn(recycle, done.players[0].discard)
        self.assertEqual(all_uids(done), card_total(done))
        audited(self, done)
        # トラッシュに置いたことは消さない（ログ discard_energy のあとに手札にもどす）
        kinds = [e["kind"] for e in new_events(choosing, done)]
        self.assertLess(kinds.index("discard_energy"), kinds.index("energy_returned_to_hand"))

    def test_knock_out_returns_recycle_but_not_basic(self):
        state = board(mon(H.HITMONCHAN, (FT,)), opponent=mon(H.RATTATA, (RE, W), damage=20))
        done = attack(state, 0)
        recycle = state.players[1].active.energy[0]
        self.assertEqual(returned(state, done), [(recycle, ("recycle_energy",), "knock_out", None)])
        self.assertIn(recycle, done.players[1].hand)
        self.assertIn(state.players[1].active.energy[1], done.players[1].discard)
        audited(self, done)

    def test_retreat_returns_recycle(self):
        state = board(mon(H.CHARMANDER, (RE, F)))
        active = state.players[0].active
        done = apply_kernel(state, Retreat(0, (active.energy[0],), state.players[0].bench[0].card))
        self.assertEqual(returned(state, done), [(active.energy[0], ("recycle_energy",), "retreat", None)])
        self.assertIn(active.energy[0], done.players[0].hand)
        audited(self, done)

    def test_returned_card_can_be_attached_again(self):
        state = board(mon(H.CHARMANDER, (RE, F)))
        active = state.players[0].active
        done = apply_kernel(state, Retreat(0, (active.energy[0],), state.players[0].bench[0].card))
        again = apply_kernel(done, AttachEnergy(0, active.energy[0], done.players[0].active.card))
        self.assertIn(active.energy[0], again.players[0].active.energy)
        audited(self, again)

    def test_hand_discard_is_not_a_target(self):
        """手札からトラッシュしたリサイクルエネルギー（オーキドはかせ）はもどさない（場からトラッシュに置かれたのではない）。"""
        state = board(mon(H.RATTATA), hand=(H.PROFESSOR_OAK, RE))
        recycle = uid_of(state, RE)
        done = play(state, H.PROFESSOR_OAK)
        self.assertIn(recycle, done.players[0].discard)
        self.assertEqual(returned(state, done), [])

    def test_already_in_discard_is_not_a_target(self):
        state = board(mon(CYNDAQUIL, (F, F)), discard=(RE,))
        done = answer(attack(state, 0, (TL,)), (state.players[0].active.energy[0],))
        self.assertEqual(returned(state, done), [])
        self.assertIn(uid_of(state, RE, zone="discard"), done.players[0].discard)

    def test_opponent_trainer_discard_returns(self):
        state = board(mon(H.RATTATA), hand=(H.ENERGY_REMOVAL,), opponent=mon(H.RATTATA, (RE,)))
        recycle = state.players[1].active.energy[0]
        done = answer(play(state, H.ENERGY_REMOVAL), (recycle,))
        self.assertEqual(returned(state, done), [(recycle, ("recycle_energy",), "trainer", 0)])
        self.assertIn(recycle, done.players[1].hand)
        audited(self, done)

    def test_scoop_up_discards_and_returns(self):
        state = board(mon(H.RATTATA), bench=(mon(H.RATTATA, (RE, W)),), hand=(H.SCOOP_UP,))
        bench = state.players[0].bench[0]
        choosing = play(state, H.SCOOP_UP)
        done = answer(choosing, (bench.pokemon_id,))
        self.assertEqual(returned(choosing, done), [(bench.energy[0], ("recycle_energy",), "trainer", 0)])
        self.assertIn(bench.energy[0], done.players[0].hand)
        self.assertIn(bench.energy[1], done.players[0].discard)
        audited(self, done)

    def test_pokemon_tower_does_not_stop_recycle_energy(self):
        state = board(mon(CYNDAQUIL, (F, RE)), hand=(H.POKEMON_TOWER,))
        state = play(state, H.POKEMON_TOWER)
        recycle = state.players[0].active.energy[1]
        done = answer(attack(state, 0, (TL,)), (recycle,))
        self.assertIn(recycle, done.players[0].hand)
        self.assertEqual(new_events(state, done, "discard_to_hand_suppressed"), [])


# ---------------------------------------------------------------- エコロジム


class EcogymTest(unittest.TestCase):
    def quagsire(self, opponent_energy, **extra):
        state = board(mon(QUAGSIRE, (W, W, W, W), evolved_from=wooper_id()), opponent=mon(H.HITMONCHAN, opponent_energy), hand=(ECO,), **extra)
        return play(state, ECO)

    def test_opponent_attack_returns_non_colorless(self):
        state = self.quagsire((F, DCE))
        choosing = attack(state, 1)
        basic, dce = state.players[1].active.energy
        done = answer(choosing, (basic,))
        self.assertEqual(returned(choosing, done), [(basic, ("ecogym",), "attack", 0)])
        self.assertIn(basic, done.players[1].hand)
        audited(self, done)
        # 無色2個エネルギーは「無色」なのでもどさない
        done = answer(choosing, (dce,))
        self.assertEqual(returned(choosing, done), [])
        self.assertIn(dce, done.players[1].discard)

    def test_rainbow_and_darkness_are_not_colorless(self):
        state = self.quagsire((RAINBOW, H.DARKNESS_ENERGY_NEO1))
        choosing = attack(state, 1)
        for card in state.players[1].active.energy:
            done = answer(choosing, (card,))
            self.assertEqual(returned(choosing, done), [(card, ("ecogym",), "attack", 0)])

    def test_own_attack_and_own_retreat_do_not_return(self):
        state = play(board(mon(CYNDAQUIL, (F, F)), hand=(ECO,)), ECO)
        done = answer(attack(state, 0, (TL,)), (state.players[0].active.energy[0],))
        self.assertEqual(returned(state, done), [])
        state = play(board(mon(H.CHARMANDER, (F, F)), hand=(ECO,)), ECO)
        active = state.players[0].active
        done = apply_kernel(state, Retreat(0, (active.energy[0],), state.players[0].bench[0].card))
        self.assertEqual(returned(state, done), [])
        self.assertIn(active.energy[0], done.players[0].discard)

    def test_knock_out_does_not_return(self):
        state = play(board(mon(H.HITMONCHAN, (FT,)), hand=(ECO,), opponent=mon(H.RATTATA, (W,), damage=20)), ECO)
        done = attack(state, 0)
        self.assertEqual(returned(state, done), [])
        self.assertIn(state.players[1].active.energy[0], done.players[1].discard)

    def test_opponent_power_returns(self):
        """相手の特殊能力（キョウのベトベトンの［だつりょくえき］。原因 power・使ったプレイヤーは特殊能力の持ち主）でトラッシュされた「無色」以外のカードはもどし、
        無色2個エネルギーはもどさない。"""
        muk = mon(H.KOGAS_MUK, (G,), evolved_from=H.KOGAS_GRIMER)
        state = play(board(mon(H.HITMONCHAN, (FT, DCE)), hand=(ECO,), opponent=muk, opponent_bench=()), ECO)
        fighting, dce = state.players[0].active.energy
        choosing = attack(state, 0, (HD,))
        self.assertEqual((choosing.decision.kind, choosing.decision.player), ("energy_drain_discard", 1))
        done = answer(choosing, (fighting,))
        self.assertEqual(returned(choosing, done), [(fighting, ("ecogym",), "power", 1)])
        self.assertIn(fighting, done.players[0].hand)
        audited(self, done)
        done = answer(choosing, (dce,))
        self.assertEqual(returned(choosing, done), [])
        self.assertIn(dce, done.players[0].discard)

    def test_opponent_trainer_returns_but_own_cost_does_not(self):
        state = play(board(mon(H.RATTATA, (F,)), hand=(ECO, H.SUPER_ENERGY_REMOVAL), opponent=mon(H.HITMONCHAN, (W, W))), ECO)
        own = state.players[0].active.energy[0]
        paying = play(state, H.SUPER_ENERGY_REMOVAL)
        selecting = answer(paying, (own,))
        self.assertEqual(returned(paying, selecting), [])
        choosing = answer(selecting, (selecting.players[1].active.pokemon_id,))
        done = answer(choosing, tuple(choosing.players[1].active.energy))
        self.assertEqual([r[1:] for r in returned(choosing, done)], [(("ecogym",), "trainer", 0)] * 2)
        self.assertEqual(Counter(state.cards[u].card_id for u in done.players[1].hand)[W], 2)
        self.assertIn(own, done.players[0].discard)
        audited(self, done)

    def test_transformed_ditto_colorless_special_energy_is_te2(self):
        """［へんしん］のメタモンの「どの色としても使える」が無色の特殊エネルギーに当てはまるかで、「「無色」以外」かが変わる（TE2 と同じ問い）。"""
        state = play(board(mon(H.RATTATA), hand=(ECO, H.ENERGY_REMOVAL), opponent=mon(H.DITTO, (DCE,))), ECO)
        # 選べるカードがそれだけなので、使う前に止める（答えのない決定を残さない。v0.49 の ``engine._trainer_dead_end``）
        rejects(self, state, PlayTrainer(0, uid_of(state, H.ENERGY_REMOVAL)), E.TRANSFORM_SPECIAL_ENERGY_CODE)
        # ほかのカード（基本エネルギー）もあれば使え、無色の特殊エネルギーを選ぶ答えだけを受け付けない
        state = play(board(mon(H.RATTATA), hand=(ECO, H.ENERGY_REMOVAL), opponent=mon(H.DITTO, (DCE, W))), ECO)
        choosing = play(state, H.ENERGY_REMOVAL)
        dce, water = choosing.players[1].active.energy
        rejects(self, choosing, ResolveDecision(0, choosing.decision.id, (dce,)), E.TRANSFORM_SPECIAL_ENERGY_CODE)
        done = answer(choosing, (water,))
        self.assertEqual(returned(choosing, done), [(water, ("ecogym",), "trainer", 0)])


# ---------------------------------------------------------------- 33 のワザ


class SparkTest(unittest.TestCase):
    def test_cyndaquil_tails_discards_any_energy_card(self):
        state = board(mon(CYNDAQUIL, (F, DCE)))
        choosing = attack(state, 0, (TL,))
        d = choosing.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (DISCARD_ENERGY, 0, tuple(state.players[0].active.energy), 1, 1))
        done = answer(choosing, (state.players[0].active.energy[1],))
        self.assertEqual([e["amount"] for e in new_events(choosing, done, "damage")], [20])
        heads = attack(state, 0, (HD,))
        self.assertEqual(new_events(state, heads, "discard_energy"), [])
        self.assertEqual([e["amount"] for e in new_events(state, heads, "damage")], [20])

    def test_invalid_choices_change_nothing(self):
        state = board(mon(CYNDAQUIL, (F, F)))
        choosing = attack(state, 0, (TL,))
        d = choosing.decision
        rejects(self, choosing, ResolveDecision(0, d.id, ()), "INVALID_CHOICE_COUNT", IllegalActionError)
        rejects(self, choosing, ResolveDecision(0, d.id, tuple(d.options)), "INVALID_CHOICE_COUNT", IllegalActionError)
        rejects(self, choosing, ResolveDecision(0, d.id, (999,)), "INVALID_CHOICE", IllegalActionError)
        rejects(self, choosing, ResolveDecision(1, d.id, (d.options[0],)), "NOT_YOUR_DECISION", IllegalActionError)

    def test_lacking_none_and_fail_programs(self):
        """トラッシュできないとき（相手のワザとして使うときなど）の扱い: ヒノアラシはダメージがなくなり、ポニータはワザが失敗する。名前でまとめない。"""
        from kyuura_engine.resolution import programs

        for card, index, lacking in ((CYNDAQUIL, 0, programs.LACKING_NONE), (PONYTA, 1, programs.LACKING_FAIL)):
            entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
            program = programs.BUILDERS[type(entry.effect)](entry.effect)
            with self.subTest(card=card):
                self.assertEqual((program[0].energy_type, program[0].local_coin, program[0].when_lacking), (None, TL, lacking))
                self.assertEqual(program[1].requires, "discard")

    def test_ponyta_tails_discards(self):
        state = board(mon(PONYTA, (F, W)))
        choosing = attack(state, 1, (TL,))
        done = answer(choosing, (state.players[0].active.energy[1],))
        self.assertEqual([e["amount"] for e in new_events(choosing, done, "damage")], [20])
        self.assertEqual(new_events(choosing, done, "attack_failed"), [])


class OptionalBonusTest(unittest.TestCase):
    def test_magmar_from_self_and_bench(self):
        state = board(mon(MAGMAR, (F, F, RE)), bench=(mon(H.RATTATA, (F, F)),))
        choosing = attack(state, 0)
        d = choosing.decision
        active, bench = state.players[0].active, state.players[0].bench[0]
        self.assertEqual((d.kind, d.options, d.min_choices, d.max_choices), (DISCARD_ENERGY, (*active.energy[:2], *bench.energy), 0, 4))
        done = answer(choosing, (active.energy[0], bench.energy[0], bench.energy[1]))
        self.assertEqual([e["amount"] for e in new_events(choosing, done, "damage")], [40])
        self.assertEqual(done.players[0].bench[0].energy, [])
        audited(self, done)
        declined = answer(choosing, ())
        self.assertEqual([e["kind"] for e in new_events(choosing, declined, "discard_energy_declined")], ["discard_energy_declined"])
        self.assertEqual([e["amount"] for e in new_events(choosing, declined, "damage")], [10])

    def test_transparent_bench_keeps_its_energy(self):
        state = board(mon(MAGMAR, (F,)), bench=(mon(H.HAUNTER, (F,), evolved_from=H.GASTLY),))
        choosing = attack(state, 0)
        bench_card = state.players[0].bench[0].energy[0]
        done = answer(with_coin_results(choosing, HD), (bench_card,))
        self.assertIn(bench_card, done.players[0].bench[0].energy)
        self.assertEqual([e["amount"] for e in new_events(choosing, done, "damage")], [10])
        done = answer(with_coin_results(choosing, TL), (bench_card,))
        self.assertEqual(done.players[0].bench[0].energy, [])
        self.assertEqual([e["amount"] for e in new_events(choosing, done, "damage")], [20])

    def test_rapidash_up_to_two(self):
        state = board(mon(RAPIDASH, (F, F, F), evolved_from=PONYTA))
        choosing = attack(state, 0)
        self.assertEqual((choosing.decision.min_choices, choosing.decision.max_choices), (0, 2))
        rejects(self, choosing, ResolveDecision(0, choosing.decision.id, tuple(choosing.decision.options)), "INVALID_CHOICE_COUNT", IllegalActionError)
        done = answer(choosing, choosing.decision.options[:2])
        self.assertEqual([e["amount"] for e in new_events(choosing, done, "damage")], [50])

    def test_rapidash_kick_switch(self):
        state = board(mon(RAPIDASH, (F, W), evolved_from=PONYTA), opponent_bench=(H.RATTATA, H.RATTATA))
        choosing = attack(state, 1)
        self.assertEqual(choosing.decision.player, 1)


class ThunderboltTest(unittest.TestCase):
    def test_discards_all_energy_cards(self):
        for card, index, damage in ((PIKACHU_PR, 1, 40), (RAICHU_IP, 1, 60)):
            extra = {} if card == PIKACHU_PR else {"evolved_from": PIKACHU_PR}
            state = board(mon(card, (L, L, L, DCE, RE), **extra))
            done = attack(state, index)
            with self.subTest(card=card):
                self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [damage])
                self.assertEqual(done.players[0].active.energy, [])
                self.assertEqual(len(new_events(state, done, "discard_energy")), 5)
                self.assertEqual(len(returned(state, done)), 1)
                audited(self, done)

    def test_raigeki_all_or_nothing(self):
        state = board(mon(RAICHU_NEO, (L, L, L, F), evolved_from=PIKACHU_PR))
        choosing = attack(state, 1)
        d = choosing.decision
        self.assertEqual((d.kind, d.options, d.min_choices, d.max_choices), (OPTIONAL_DISCARD_ALL, (1,), 0, 1))
        none = answer(choosing, ())
        self.assertEqual([e["amount"] for e in new_events(choosing, none, "damage")], [40])
        all_ = answer(choosing, (1,))
        self.assertEqual([e["amount"] for e in new_events(choosing, all_, "damage")], [80])
        self.assertEqual([state.cards[u].card_id for u in all_.players[0].active.energy], [F])
        rejects(self, choosing, ResolveDecision(0, d.id, (2,)), "INVALID_CHOICE", IllegalActionError)


class FlaaffyTest(unittest.TestCase):
    def test_discharge_reuses_the_existing_processing(self):
        state = board(mon(FLAAFFY, (L, L, RE), evolved_from=mareep_id()))
        done = attack(state, 0, (HD, TL))
        self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [30])
        self.assertEqual([state.cards[u].card_id for u in done.players[0].active.energy], [RE])

    def test_electric_toss_without_bench_discards_through_the_return(self):
        state = board(mon(FLAAFFY, (L, L), evolved_from=mareep_id()), bench=())
        choosing = attack(state, 1)
        done = answer(choosing, (choosing.decision.options[0],))
        self.assertEqual([e.get("reason") for e in new_events(choosing, done, "discard_energy")], ["no_bench"])


class ElementTypesTest(unittest.TestCase):
    def test_lugia_each_type_one_card(self):
        state = board(mon(LUGIA, (F, W, L, F)))
        current = attack(state, 0)
        seen = []
        while current.decision and current.decision.kind == DISCARD_ENERGY:
            seen.append(current.decision.options)
            current = answer(current, (current.decision.options[-1],))
        active = state.players[0].active
        self.assertEqual(seen, [(active.energy[0], active.energy[3]), (active.energy[1],), (active.energy[2],)])
        self.assertEqual([e["amount"] for e in new_events(state, current, "damage")], [90])
        self.assertEqual(current.players[0].active.energy if current.players[0].active else None, [active.energy[0]])

    def test_lugia_lacking_type_discards_nothing(self):
        """どれかの色のカードがなければ 1 枚もトラッシュせず、ダメージはなくなる（要素を直接試す。ふつうは必要なエネルギーで起こらない）。"""
        state = board(mon(H.CLEFAIRY, (W, W, W)), opponent=mon(LUGIA, (F, W, L)))
        choosing = attack(state, 1)
        done = answer(choosing, (choosing.decision.options[0],))
        self.assertEqual(new_events(choosing, done, "discard_energy"), [])
        self.assertEqual(new_events(choosing, done, "damage"), [])
        self.assertEqual([(e["outcome"], e["missing_types"]) for e in new_events(choosing, done, "discard_energy_failed")], [("none", ("fire", "lightning"))])
        self.assertEqual(len(done.players[0].active.energy), 3)

    def test_shining_charizard_self_damage_only_on_tails(self):
        state = board(mon(SHINING_CHARIZARD, (F, F, F, L, L)))
        for side, self_damage in ((TL, [30]), (HD, [])):
            current = attack(state, 0, (side,))
            while current.decision and current.decision.kind == DISCARD_ENERGY:
                current = answer(current, (current.decision.options[0],))
            with self.subTest(side=side):
                self.assertEqual([e["amount"] for e in new_events(state, current, "damage") if e.get("target") == "self"], self_damage)
                self.assertEqual(len(new_events(state, current, "discard_energy")), 2)


class WarmUpTest(unittest.TestCase):
    def test_bench_then_deck_card(self):
        state = board(mon(FLAREON, (F,), evolved_from=EEVEE), bench=(H.RATTATA, H.RATTATA), deck=[W, F, W, F])
        choosing = attack(state, 0)
        d = choosing.decision
        self.assertEqual((d.kind, d.context_value("stage")), (ATTACH_TO_BENCH, "bench"))
        second = answer(choosing, (d.options[1],))
        d2 = second.decision
        self.assertEqual((d2.kind, d2.context_value("stage"), d2.min_choices, d2.max_choices), (ATTACH_FROM_DECK, "card", 1, 1))
        self.assertNotIn("options", observe(second, 1)["decision"] or {})
        done = answer(second, (d2.options[0],))
        self.assertIn(d2.options[0], done.players[0].bench[1].energy)
        self.assertEqual(len(new_events(second, done, "shuffle")), 1)
        audited(self, done)

    def test_without_bench_the_attack_fails(self):
        state = board(mon(FLAREON, (F,), evolved_from=EEVEE), bench=())
        done = attack(state, 0)
        self.assertEqual([e["reason"] for e in new_events(state, done, "attack_failed")], ["no_bench"])
        self.assertIs(done.phase, Phase.MAIN)
        self.assertEqual(done.current_player, 1)

    def test_no_fire_in_deck_attaches_nothing_but_shuffles(self):
        state = board(mon(FLAREON, (F,), evolved_from=EEVEE), deck=[W, W])
        choosing = attack(state, 0)
        done = answer(choosing, (choosing.decision.options[0],))
        self.assertEqual([e["reason"] for e in new_events(choosing, done, "attach_energy_from_deck_none")], ["no_candidates"])
        self.assertEqual(len(new_events(choosing, done, "shuffle")), 1)

    def test_waiting_states_survive_copy_and_pickle(self):
        state = board(mon(FLAREON, (F,), evolved_from=EEVEE), deck=[W, F, F])
        waiting = answer(attack(state, 0), (state.players[0].bench[0].pokemon_id,))
        choice = (waiting.decision.options[0],)
        for restored in (waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting))):
            self.assertEqual(snapshot(answer(restored, choice)), snapshot(answer(waiting, choice)))
        audited(self, waiting)


class HeatFlameTest(unittest.TestCase):
    def test_heads_count_decides_both(self):
        state = board(mon(FLAREON, (F, F, F), evolved_from=EEVEE))
        for coins, discards, damage in (((HD, HD), 2, 70), ((HD, TL), 1, 50), ((TL, TL), 0, 30)):
            current = attack(state, 1, coins)
            if current.decision and current.decision.kind == DISCARD_ENERGY:
                self.assertEqual((current.decision.min_choices, current.decision.max_choices), (discards, discards))
                current = answer(current, current.decision.options[:discards])
            with self.subTest(coins=coins):
                self.assertEqual(len(new_events(state, current, "discard_energy")), discards)
                self.assertEqual([e["amount"] for e in new_events(state, current, "damage")], [damage])

    def test_lacking_means_no_damage_when_copied(self):
        """ピッピの「ゆびをふる」でヒートフレイムを使うと、必要なエネルギーはいらないので、「おもて」の数より炎のカードが少ないことがある。1 枚もトラッシュせず、ダメージはない。"""
        state = board(mon(H.CLEFAIRY, (W, W, W)), opponent=mon(FLAREON, (F, F, F), evolved_from=EEVEE))
        choosing = attack(state, 1)
        heat = next(i for i, option in enumerate(choosing.decision.options) if option == choosing.decision.options[-1])
        done = answer(with_coin_results(choosing, HD, TL), (choosing.decision.options[heat],))
        self.assertEqual(new_events(choosing, done, "discard_energy"), [])
        self.assertEqual(new_events(choosing, done, "damage"), [])
        self.assertEqual([e["outcome"] for e in new_events(choosing, done, "discard_energy_failed")], ["none"])
        done = answer(with_coin_results(choosing, TL, TL), (choosing.decision.options[heat],))
        self.assertEqual([e["amount"] for e in new_events(choosing, done, "damage")], [30])


class HyperFlameTest(unittest.TestCase):
    def test_tails_discards_all_and_heads_one(self):
        state = board(mon(MOLTRES_PR, (F, F, F, RE)))
        tails = attack(state, 0, (TL,))
        self.assertEqual(tails.players[0].active.energy, [])
        self.assertEqual(len(returned(state, tails)), 1)
        self.assertEqual([e["amount"] for e in new_events(state, tails, "damage")], [60])
        heads = attack(state, 0, (HD,))
        self.assertEqual(heads.decision.kind, DISCARD_ENERGY)
        done = answer(heads, (heads.decision.options[0],))
        self.assertEqual(len(done.players[0].active.energy), 3)
        self.assertEqual(len(new_events(state, done, "coin_flip")), 1)  # 投げ直さない


class FireWindTest(unittest.TestCase):
    def test_choose_then_two_coins(self):
        state = board(mon(QUILAVA, (F, F), evolved_from=CYNDAQUIL), opponent_bench=(H.RATTATA, H.RATTATA))
        choosing = attack(state, 1)
        self.assertEqual(choosing.decision.kind, SELECT_POKEMON)
        self.assertEqual(new_events(state, choosing, "coin_flip"), [])  # 選ぶ前にコインを投げない
        done = answer(with_coin_results(choosing, HD, HD), (choosing.decision.options[1],))
        bench_damage = [e for e in new_events(choosing, done, "damage") if e.get("target") == "opponent_bench"]
        self.assertEqual([e["amount"] for e in bench_damage], [20])
        self.assertEqual(done.players[1].bench[1].damage, 20)

    def test_no_bench_no_coins(self):
        state = board(mon(QUILAVA, (F, F), evolved_from=CYNDAQUIL), opponent_bench=())
        done = attack(state, 1)
        self.assertEqual(new_events(state, done, "coin_flip"), [])
        self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [20])


class QuagsireTest(unittest.TestCase):
    def test_whirlpool_discards_opponent_energy(self):
        state = board(mon(QUAGSIRE, (W, W, W, W), evolved_from=wooper_id()), opponent=mon(H.HITMONCHAN, (F,)))
        done = answer(attack(state, 1), (state.players[1].active.energy[0],))
        self.assertIn(state.players[1].active.energy[0], done.players[1].discard)


if __name__ == "__main__":
    unittest.main()

"""v0.90（docs/markers-counters-v0.90.md）: マーカー・ダメージカウンター以外のカウンターの 7 枚（ワザ 13）と、のせる・数える・消費する・取りのぞく共通の処理。

根拠は kyuura データの採用（kyuura ``7d3f4ca`` の data/cards.json の日本語の印刷の文面）と、既存の規定の記録（GR-2000-P310-EVOLUTION・GR-2000-P311-RETREAT・
GR-2000-P322-PERSISTENT-EFFECTS・GR-2000-P324-DEVOLUTION・GR-2000-P321-DAMAGE-ORDER など。docs 各章）。2000 年 5 月の RUL-CHAR-MARKER は持ち込まない。公式ガイドブックの新しい
読み直し・カードの画像・pcg-search.com との照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない
（対戦は tools/existing_effect_games.py の ``--batch v0.90``）。
"""

from __future__ import annotations

import copy
import pathlib
import pickle
import unittest
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    EvolvePokemon,
    ResolveDecision,
    Retreat,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import (
    EnergyType,
    load_card_pool,
    pool_from_extract,
    read_extract,
)
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import ESP_REDO, SELECT_COLOR, SELECT_MARKER_COUNT
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.markers import add_marker, color_marker, marker_count, remove_markers
from kyuura_engine.observation import observe
from kyuura_engine.resolution import programs
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import (
    COUNTER_BONE,
    COUNTER_FOOD,
    MARKER_COLOR,
    MARKER_CURSE,
    MARKER_STICKY,
    Marker,
)
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.test_entry_powers_energy_lifecycle_v0_85 import stage1
from tests.test_neo_trainer_components_v0_80 import (
    audited,
    mon,
    new_events,
    rejects,
    snapshot,
)
from tests.test_shining_gentle_v0_83 import answer, board, play

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "markers-counters-v0.90.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
TURN = 7
W, G, L, P, F = H.WATER, H.GRASS, H.LIGHTNING, H.PSYCHIC, H.FIGHTING
CM1 = "UNRESOLVED_COLOR_MARKER_PRECEDENCE"
KR1 = "UNRESOLVED_FULL_RECOVERY_COUNTERS"
CONFUSION_MODIFIERS = "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS"
HC3 = "UNRESOLVED_PREVENTED_EFFECT_COIN"
BALLOON_BERRY = "neo3-055"  # ふうせんのみ（v0.81。tests/test_pokemon_tools_stadiums_v0_81.py の BALLOON_BERRY）
V090_ATTACKS = [AttackKey(c, i) for c in H.V0_90_POKEMON for i in range(len(load_card_pool().definitions[c].attacks))]


def marks(pokemon):
    """のっているマーカー・カウンターの (種類, 色)（のせた順）。"""
    return [(m.kind, None if m.color is None else m.color) for m in pokemon.markers]


def declare(state, index, *coins, player=0):
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UseAttack(player, index))


def damages(before, after):
    return [(e["amount"], e.get("weakness_multiplier")) for e in new_events(before, after, "damage")]


def marowak(energy=(F, F), *, opponent=False, **extra):
    """カラカラ（PR1-034）から進化したガラガラ（ES2-025）。``opponent`` なら相手の番（6 番）に進化した盤面。"""
    if opponent:
        return mon(H.MAROWAK_ES2, energy, played_turn=2, evolved_from=H.CUBONE_PR1, evolved_turn=6, **extra)
    return stage1(H.MAROWAK_ES2, energy, base=H.CUBONE_PR1, **extra)


# ---------------------------------------------------------------- 1 章: 対象と登録


class RegistrationTest(unittest.TestCase):
    def test_every_attack_is_registered(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_90"]), H.V0_90_CARDS)
        self.assertEqual(len(V090_ATTACKS), 13)
        for key in V090_ATTACKS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
                attack = pool.definitions[key.card_id].attacks[key.attack_index]
                self.assertEqual((entry.name_ja, entry.text_ja), (attack.name_ja, attack.text_ja))
                self.assertEqual(entry.effect.check(attack), [])
                self.assertEqual(entry.play_text_ja, attack.text_ja)  # 処理に使う文面は kyuura の印刷の文面（LD-・エラッタはない）
        for card in H.V0_90_CARDS:
            self.assertIn(card, pool.playable_ids)
            self.assertEqual(pool.definitions[card].powers, ())

    def test_types(self):
        effect = lambda card, i: DEFAULT_EFFECTS.attack_entry(card, i).effect
        self.assertEqual(effect(H.GRIMER_ES2, 0), E.MarkOpponentIfAbsent(MARKER_STICKY))
        self.assertIsInstance(effect(H.GRIMER_ES2, 1), E.PoisonOnHeads)
        self.assertEqual(effect(H.MAROWAK_ES2, 0), E.MarkSelfIfAbsent(COUNTER_BONE))
        self.assertEqual(effect(H.CUBONE_PR1, 0), E.MarkSelfIfAbsent(COUNTER_BONE))  # 「このカードの上に」も同じ型
        self.assertEqual(effect(H.MAROWAK_ES2, 1), E.DamageThenRemoveOwnMarkerParalyzeOnHeads(COUNTER_BONE))
        self.assertEqual(effect(H.CUBONE_PR1, 1), E.OptionalRemoveOwnMarkersBonusDamage(COUNTER_BONE, 30, 1))
        self.assertEqual(effect(H.HUNGRY_SNORLAX, 0), E.MarkSelfUpToLimit(COUNTER_FOOD, 2))
        self.assertEqual(effect(H.HUNGRY_SNORLAX, 1), E.OptionalRemoveOwnMarkersBonusDamage(COUNTER_FOOD, 30, None))
        self.assertEqual(effect(H.JYNX_PR1, 0), E.CoinMarkOpponent(MARKER_CURSE))
        self.assertIs(effect(H.JYNX_PR1, 1), E.DAMAGE_ONLY)
        self.assertEqual(effect(H.SMEARGLE_PRN, 0), E.CoinPaintOpponent())
        self.assertEqual(effect(H.MEWTWO_ES3, 0), E.DiscardAllEnergyThenFullRecovery())
        self.assertEqual(effect(H.MEWTWO_ES3, 1), E.DamageThenDiscardOpponentEnergy(True))

    def test_unregistered_without_the_v0_90_entries(self):
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V090_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(before.playable_ids, load_card_pool().playable_ids - set(H.V0_90_CARDS))

    def test_texts_are_matched_exactly(self):
        """似た説明を広い正規化で通さない（ほねさがしは 2 枚の書き方だけ・サイコブラストは全文 1 つだけを加えた。v0.33 からの書き方も変わらない）。"""
        pool = load_card_pool()
        attack = pool.definitions[H.MEWTWO_ES3].attacks[1]
        self.assertEqual(E.DamageThenDiscardOpponentEnergy(True).check(attack), [])
        changed = attack.__class__(**{**attack.__dict__, "text_ja": attack.text_ja.replace("トラッシュさせる", "手札にもどさせる")})
        self.assertNotEqual(E.DamageThenDiscardOpponentEnergy(True).check(changed), [])
        bone = pool.definitions[H.CUBONE_PR1].attacks[0]
        for text in E.BONE_SEARCH_TEXTS:
            self.assertEqual(E.MarkSelfIfAbsent(COUNTER_BONE).check(bone.__class__(**{**bone.__dict__, "text_ja": text})), [])
        self.assertNotEqual(E.MarkSelfIfAbsent(COUNTER_BONE).check(bone.__class__(**{**bone.__dict__, "text_ja": "このカードに「ほねカウンター」を1つのせる。"})), [])
        self.assertNotEqual(E.MarkSelfIfAbsent(COUNTER_FOOD).check(bone), [])  # 種類と文面の組
        self.assertNotEqual(E.OptionalRemoveOwnMarkersBonusDamage(COUNTER_BONE, 30, None).check(pool.definitions[H.CUBONE_PR1].attacks[1]), [])

    def test_evolution_base_is_an_existing_cubone(self):
        pool = load_card_pool()
        self.assertEqual((pool.get(H.MAROWAK_ES2).stage, pool.get(H.MAROWAK_ES2).evolves_from), ("stage1", "カラカラ"))
        self.assertIn(H.CUBONE_ES3, pool.playable_ids)  # 依存のための追加カードはない（既存のカラカラ）


# ---------------------------------------------------------------- 3 章: 共通の状態


class MarkerStateTest(unittest.TestCase):
    """マーカー・カウンターは、ダメージ・特殊状態・ついているカード・持続する効果・特殊能力の記録とは別の項目。書き出しは形式 24、観測は全員に見える。"""

    def test_separate_field_and_format_24(self):
        state = board(mon(H.CHANSEY, markers=[MARKER_CURSE, MARKER_CURSE, (MARKER_COLOR, EnergyType.FIRE)]))
        audited(self, state)  # のろいマーカー 2 つは不正な状態ではない（「2つ以上のっていても、効果は同じ」）
        chansey = state.players[0].active
        self.assertEqual((chansey.damage, chansey.persistent_effects, chansey.conditions.names(), chansey.type_shift), (0, (), (), None))
        self.assertIn(24, FORMAT_VERSIONS)  # v0.99: 今の最新の形式（25）は tests/test_catalog_contract.py。マーカーは形式 24 から
        with self.assertRaises(ValueError):
            state_to_dict(state, format_version=23)
        written = state_to_dict(state, format_version=24)["players"][0]["active"]["markers"]
        self.assertEqual([(m["kind"], m.get("color")) for m in written], [("curse", None), ("curse", None), ("color", "fire")])
        plain = board(mon(H.CHANSEY))
        self.assertEqual(state_to_dict(plain, format_version=23)["players"][0]["active"], {k: v for k, v in state_to_dict(plain, format_version=24)["players"][0]["active"].items() if k != "markers"})
        for viewer in (0, 1, None):
            self.assertEqual([m["kind"] for m in observe(state, viewer)["players"][0]["active"]["markers"]], ["curse", "curse", "color"])

    def test_invariants(self):
        from kyuura_engine.engine import check_invariants

        def broken(**changes):
            state = board(mon(H.CHANSEY, markers=[MARKER_CURSE]))
            marker = state.players[0].active.markers[0]
            state.players[0].active.markers = (Marker(**{**marker.__dict__, **changes}),)
            return check_invariants(state)

        self.assertNotEqual(broken(kind="burned"), [])  # 対応していない種類（くろこげなど）
        self.assertNotEqual(broken(kind=MARKER_COLOR), [])  # 色を持たない色マーカー
        self.assertNotEqual(broken(color=EnergyType.FIRE), [])  # 色を持つのろいマーカー
        self.assertNotEqual(broken(turn=TURN + 1), [])  # 今の番より後
        self.assertNotEqual(broken(player=2), [])
        two = board(mon(H.CHANSEY, markers=[(MARKER_COLOR, EnergyType.FIRE), (MARKER_COLOR, EnergyType.WATER)]))
        self.assertNotEqual(check_invariants(two), [])  # 色マーカーは 1 つまで
        unlogged = board(mon(H.CHANSEY))
        unlogged.players[0].active.markers = (Marker(MARKER_CURSE, 1, unlogged.players[0].active.card, "test", TURN - 1),)
        self.assertNotEqual(check_invariants(unlogged), [])  # ログ marker_added と対応しない

    def test_copy_and_pickle_keep_markers(self):
        state = board(mon(H.CHANSEY, markers=[MARKER_STICKY, (MARKER_COLOR, EnergyType.METAL)]))
        for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(snapshot(other), snapshot(state))
            other.players[0].active.markers = ()
            self.assertEqual(len(state.players[0].active.markers), 2)  # 複製を変えても元は変わらない

    def test_common_operations(self):
        state = board(mon(H.CHANSEY))
        chansey = state.players[0].active
        add_marker(state, 0, chansey, Marker(COUNTER_FOOD, 0, chansey.card, "test", TURN))
        add_marker(state, 0, chansey, Marker(COUNTER_FOOD, 0, chansey.card, "test", TURN))
        self.assertEqual(marker_count(chansey, COUNTER_FOOD), 2)
        self.assertEqual(remove_markers(state, 0, chansey, "used", kinds=(COUNTER_FOOD,), count=1, effect="test"), 1)
        self.assertEqual(new_events(board(mon(H.CHANSEY)), state, "marker_removed")[-1]["remaining"], 1)
        with self.assertRaises(RuntimeError):
            remove_markers(state, 0, chansey, "used", kinds=(COUNTER_FOOD,), count=2)  # のっている数より多くは取りのぞけない
        with self.assertRaises(ValueError):
            add_marker(state, 0, chansey, Marker(MARKER_COLOR, 1, chansey.card, "test", TURN))  # 色のない色マーカー
        self.assertIsNone(color_marker(chansey))


class LifecycleTest(unittest.TestCase):
    """にげる・入れ替え・バトル場に出すでは消えない（p.311・p.322）。進化（p.310）・退化（p.324）で取りのぞき、場をはなれたらなくなる。特殊状態・かがくへんかガス・発生源が
    場をはなれたことでは消えない。"""

    def test_retreat_and_switch_keep(self):
        state = board(mon(H.CHANSEY, (W, W), markers=[MARKER_CURSE, MARKER_STICKY]), hand=(H.SWITCH,))
        active = state.players[0].active
        retreated = apply_kernel(state, Retreat(0, tuple(active.energy), state.players[0].bench[0].card))
        self.assertEqual(marks(retreated.players[0].bench[0]), [(MARKER_CURSE, None), (MARKER_STICKY, None)])
        switched = play(state, H.SWITCH)
        if switched.decision is not None:
            switched = answer(switched, (switched.decision.options[0],))
        self.assertEqual(marks(switched.players[0].bench[0]), [(MARKER_CURSE, None), (MARKER_STICKY, None)])
        back = play(board(mon(H.RATTATA), bench=(mon(H.CHANSEY, markers=[MARKER_CURSE]),), hand=(H.SWITCH,)), H.SWITCH)
        if back.decision is not None:
            back = answer(back, (back.decision.options[0],))
        self.assertEqual(marks(back.players[0].active), [(MARKER_CURSE, None)])  # 控えからバトル場に出しても消えない
        for result in (retreated, switched, back):
            self.assertEqual(new_events(state, result, "marker_removed"), [])
            audited(self, result)

    def test_evolution_and_devolution_remove(self):
        state = board(mon(H.CUBONE_PR1, (F,), markers=[COUNTER_BONE, MARKER_CURSE, (MARKER_COLOR, EnergyType.FIRE)], played_turn=3), hand=(H.MAROWAK_ES2,))
        card = next(u for u in state.players[0].hand if state.cards[u].card_id == H.MAROWAK_ES2)
        evolved = apply_kernel(state, EvolvePokemon(0, card, state.players[0].active.pokemon_id))
        self.assertEqual(evolved.players[0].active.markers, ())
        self.assertEqual({e["marker"] for e in new_events(state, evolved, "marker_removed") if e["reason"] == "evolve"}, {COUNTER_BONE, MARKER_CURSE, MARKER_COLOR})
        audited(self, evolved)
        sprayed = board(marowak(markers=[COUNTER_BONE, MARKER_STICKY]), hand=(H.DEVOLUTION_SPRAY,))
        asking = play(sprayed, H.DEVOLUTION_SPRAY)
        done = answer(answer(asking, (asking.decision.options[0],)), (1,))
        self.assertEqual(done.players[0].active.markers, ())
        self.assertEqual({e["reason"] for e in new_events(sprayed, done, "marker_removed")}, {"devolve"})
        audited(self, done)

    def test_every_evolution_and_devolution_goes_through_the_common_functions(self):
        """進化・退化で重なりを変えるのは ``evolution.place_evolution_card``・``devolve`` だけで、どちらもマーカー・カウンターを取りのぞく（手札・ポケモン育て屋さん・ワザ・特殊能力・
        反応の特殊能力の進化、たいかビーム・退化スプレー・退化スプレーHYPER の退化は、どれもこの 2 つを呼ぶ）。"""
        import re

        sources = list((ROOT / "kyuura_engine").glob("*.py")) + list((ROOT / "kyuura_engine" / "resolution").glob("*.py"))
        writers = {p.name for p in sources if re.search(r"\.evolution_stack = ", p.read_text(encoding="utf-8"))}
        self.assertEqual(writers, {"evolution.py"})
        text = (ROOT / "kyuura_engine" / "evolution.py").read_text(encoding="utf-8")
        for name in ("place_evolution_card", "devolve"):
            body = text.split(f"def {name}(")[1].split("\ndef ")[0]
            self.assertIn("remove_markers(", body, name)

    def test_conditions_gas_and_source_do_not_remove(self):
        """特殊状態・かがくへんかガスはマーカーを消さない（特殊能力の効果ではない）。のせたベトベターがきぜつしても、受け手のマーカーは残る（p.322）。"""
        from tests.test_type_energy_colors_v0_88 import muk

        state = board(mon(H.GRIMER_ES2, (G,)), opponent=mon(H.CHANSEY, (W,), markers=[MARKER_STICKY, MARKER_CURSE]))
        poisoned = declare(state, 1, HD)  # どくえき（どく）
        self.assertEqual(len(poisoned.players[1].active.markers), 2)
        gas = board(mon(H.CHANSEY, markers=[(MARKER_COLOR, EnergyType.WATER)]), opponent=muk())
        self.assertEqual(E.type_readings(gas, gas.players[0].active), (EnergyType.WATER,))  # ペイント単独は力の消える効果で止めない
        healed = play(board(mon(H.CHANSEY, poison=10, confusion=True, markers=[MARKER_CURSE]), hand=(H.FULL_HEAL,)), H.FULL_HEAL)
        self.assertEqual((healed.players[0].active.conditions.names(), marks(healed.players[0].active)), ((), [(MARKER_CURSE, None)]))  # なんでもなおしは特殊状態だけ
        knocked = declare(board(mon(H.CHANSEY, (W, W, W, W)), opponent=mon(H.GRIMER_ES2, damage=40), opponent_bench=(mon(H.RATTATA, markers=[MARKER_STICKY]),)), 1)
        self.assertEqual(marks(knocked.players[1].bench[0]), [(MARKER_STICKY, None)])
        for result in (poisoned, gas, healed, knocked):
            audited(self, result)

    def test_shapeshift_and_transform_are_not_evolution(self):
        """ばける・［へんしん］は進化・退化ではないので、マーカーを取りのぞかない。色マーカーの色は今の姿（のせたカード・写した相手のカード）のタイプより先に読む（色を変える効果が
        色マーカーだけのときは決まる。実装上の読み方）。相手の対戦ポケモンの色マーカーは、［へんしん］で写さない（写すのはカード）。"""
        ninetales = stage1(H.BROCKS_NINETALES, (H.FIRE, H.FIRE), base=H.BROCKS_VULPIX, markers=[(MARKER_COLOR, EnergyType.WATER)])
        state = board(ninetales, hand=(H.CHARMELEON,))
        asking = apply_kernel(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        done = answer(asking, (asking.decision.options[0],))
        self.assertIsNotNone(done.players[0].active.disguise)
        self.assertEqual(marks(done.players[0].active), [(MARKER_COLOR, EnergyType.WATER)])
        self.assertEqual(E.type_readings(done, done.players[0].active), (EnergyType.WATER,))
        audited(self, done)
        ditto = board(mon(H.DITTO, markers=[(MARKER_COLOR, EnergyType.FIRE)]), opponent=mon(H.CHANSEY, markers=[(MARKER_COLOR, EnergyType.WATER)]))
        self.assertEqual(E.current_form(ditto, ditto.players[0].active).kind, "transform")
        self.assertEqual(E.type_readings(ditto, ditto.players[0].active), (EnergyType.FIRE,))
        plain = board(mon(H.DITTO), opponent=mon(H.CHANSEY, markers=[(MARKER_COLOR, EnergyType.WATER)]))
        self.assertEqual(E.type_readings(plain, plain.players[0].active), (EnergyType.COLORLESS,))

    def test_knocked_out_pokemon_takes_its_markers_with_it(self):
        state = board(mon(H.CHANSEY, (W, W, W, W)), opponent=mon(H.RATTATA, markers=[MARKER_CURSE]))
        done = declare(state, 1)
        self.assertNotIn(state.players[1].active.pokemon_id, [p.pokemon_id for p in done.players[1].in_play()])
        audited(self, done)


# ---------------------------------------------------------------- 4 章: ベトベター（ベトベトえき・にげる）


class StickyFluidTest(unittest.TestCase):
    def test_places_once(self):
        state = board(mon(H.GRIMER_ES2, (G,)), opponent=mon(H.CHANSEY))
        first = declare(state, 0)
        self.assertEqual(marks(first.players[1].active), [(MARKER_STICKY, None)])
        again = board(mon(H.GRIMER_ES2, (G,)), opponent=mon(H.CHANSEY, markers=[MARKER_STICKY]))
        second = declare(again, 0)
        self.assertEqual((new_events(again, second, "marker_added"), len(second.players[1].active.markers)), ([], 1))  # のっていれば増やさない
        for result in (first, second):
            audited(self, result)

    def test_attack_barrier_prevents_the_effect(self):
        """「ワザをうけない」状態（バリアー）の相手には、のせない（ワザの効果の防止は既存の問い合わせ）。"""
        from kyuura_engine.state import AttackBarrier

        state = board(mon(H.GRIMER_ES2, (G,)), opponent=mon(H.CHANSEY))
        chansey = state.players[1].active
        chansey.persistent_effects = (AttackBarrier(chansey.card, 1, TURN - 1, TURN),)
        state.turn_number, saved = TURN - 1, state.turn_number
        state.add_event("persistent_effect_added", player=1, pokemon=chansey.card, pokemon_id=chansey.pokemon_id, persistent_effect="attack_barrier",
                        source_card=chansey.card, source_player=1, active_turn=TURN, effect="test")
        state.turn_number = saved
        done = declare(state, 0)
        self.assertEqual((done.players[1].active.markers, [e["element"] for e in new_events(state, done, "effect_prevented")]), ((), [E.MARKER_ELEMENT]))

    def test_retreat_needs_one_more_energy_unit(self):
        state = board(mon(H.CHANSEY, (W, W), markers=[MARKER_STICKY]))
        cost = E.retreat_cost(state, 0)
        self.assertEqual((cost.printed, cost.minimum, cost.maximum, cost.marker_increases), (1, 2, 2, ((MARKER_STICKY, 1),)))
        active, new = state.players[0].active, state.players[0].bench[0].card
        rejects(self, state, Retreat(0, (active.energy[0],), new), "WRONG_RETREAT_COST", error=IllegalActionError)
        done = apply_kernel(state, Retreat(0, tuple(active.energy), new))
        self.assertEqual(new_events(state, done, "retreat")[0]["retreat_cost_markers"], ((MARKER_STICKY, 1),))
        dce = board(mon(H.CHANSEY, (H.DOUBLE_COLORLESS_ENERGY,), markers=[MARKER_STICKY]))
        paid = apply_kernel(dce, Retreat(0, tuple(dce.players[0].active.energy), dce.players[0].bench[0].card))  # エネルギーの個数で数える（無色2個は 2 個）
        for result in (done, paid):
            audited(self, result)

    def test_same_terms_as_sticky_goo(self):
        """［ねんちゃくえき］と同じ「…トラッシュするエネルギーが…多く必要になる」なので、同じ増やす数として当てはめる（にげるサポートとの先に 0 で止める読み方は CP2）。"""
        dodrio = mon(H.DODRIO, played_turn=2, evolved_from=H.DODUO, evolved_turn=5)
        cost = E.retreat_cost(board(mon(H.CHANSEY, markers=[MARKER_STICKY]), bench=(dodrio,)), 0)
        self.assertEqual((cost.minimum, cost.maximum), (1, 2))  # 印刷 1 + 1、にげるサポートで 1 少なくできる
        zero = E.retreat_cost(board(mon(H.RATTATA, markers=[MARKER_STICKY]), bench=(dodrio,)), 0)
        self.assertTrue(zero.floor_ambiguous(0))  # 印刷 0: にげるサポートを先に当てて 0 で止めるかで 0 個が足りるかが変わる（CP2）
        balloon = E.retreat_cost(board(mon(H.CHANSEY, (W, W), markers=[MARKER_STICKY], trainers=[(BALLOON_BERRY, None)])), 0)
        self.assertEqual((balloon.readings[0], balloon.floor_ambiguous(0), balloon.floor_ambiguous(1), balloon.allows(2)), ((0, 0), True, True, False))  # 「すべてなくなる」を先か後か（CP2。v0.81）


# ---------------------------------------------------------------- 4 章: ほねカウンター（ほねさがし・ほねこんぼう・ボーンキラー）


class BoneCounterTest(unittest.TestCase):
    def test_bone_search_both_texts(self):
        for card in (H.CUBONE_PR1, H.MAROWAK_ES2):
            state = board(marowak() if card == H.MAROWAK_ES2 else mon(card, (F,)))
            first = declare(state, 0)
            self.assertEqual(marks(first.players[0].active), [(COUNTER_BONE, None)])
            again = declare(board(marowak(markers=[COUNTER_BONE]) if card == H.MAROWAK_ES2 else mon(card, (F,), markers=[COUNTER_BONE])), 0)
            self.assertEqual(marker_count(again.players[0].active, COUNTER_BONE), 1)
            audited(self, first)

    def test_bone_club_requires_a_counter(self):
        rejects(self, board(marowak()), UseAttack(0, 1), "MARKER_REQUIRED", error=IllegalActionError)

    def test_bone_club_removes_then_flips(self):
        state = board(marowak(markers=[COUNTER_BONE]), opponent=mon(H.CHANSEY))
        heads = declare(state, 1, HD)
        kinds = [e["kind"] for e in new_events(state, heads) if e["kind"] in ("damage", "marker_removed", "coin_flip", "special_condition")]
        self.assertEqual(kinds, ["damage", "marker_removed", "coin_flip", "special_condition"])
        self.assertEqual((heads.players[0].active.markers, heads.players[1].active.conditions.names()), ((), ("paralysis",)))
        tails = declare(state, 1, TL)
        self.assertEqual((tails.players[0].active.markers, tails.players[1].active.conditions.names()), ((), ()))
        for result in (heads, tails):
            audited(self, result)

    def test_confusion_failure_keeps_the_counter(self):
        """こんらんの「うら」でワザが失敗したら取りのぞかない（存在の確かめは宣言の前、消費はワザの効果）。"""
        state = board(marowak(markers=[COUNTER_BONE], confusion=True))
        failed = declare(state, 1, TL)
        self.assertEqual((marks(failed.players[0].active), new_events(state, failed, "marker_removed")), ([(COUNTER_BONE, None)], []))
        audited(self, failed)

    def test_sand_attack_failure_keeps_the_counter(self):
        """すなかけ（手順 4 のコイン）の「うら」でワザが失敗したら、取りのぞかない。"""
        from kyuura_engine.state import AttackCoinCheck

        state = board(marowak(markers=[COUNTER_BONE]), opponent=mon(H.CHANSEY))
        sandshrew = state.players[1].active
        attacker = state.players[0].active
        attacker.persistent_effects = (AttackCoinCheck(sandshrew.card, 1, TURN - 1, TURN, single_use=True),)
        saved, state.turn_number = state.turn_number, TURN - 1
        state.add_event("persistent_effect_added", player=0, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, persistent_effect="attack_coin_check",
                        source_card=sandshrew.card, source_player=1, active_turn=TURN, effect="test")
        state.turn_number = saved
        failed = declare(state, 1, TL)
        self.assertEqual((marks(failed.players[0].active), new_events(state, failed, "marker_removed")), ([(COUNTER_BONE, None)], []))
        self.assertTrue(new_events(state, failed, "attack_failed"))

    def test_knocked_out_defender_no_coin_but_counter_removed(self):
        state = board(marowak(markers=[COUNTER_BONE]), opponent=mon(H.RATTATA))
        done = declare(state, 1)
        self.assertEqual((done.players[0].active.markers, [e for e in new_events(state, done, "coin_flip")]), ((), []))
        audited(self, done)

    def test_attack_barrier_stops_before_the_paralysis_coin(self):
        """相手が「ワザをうけない」状態なら、ダメージも無効で、コインはマヒだけを決めるので HC3（v0.31 と同じ。状態・乱数を変えない）。"""
        from kyuura_engine.state import AttackBarrier

        state = board(marowak(markers=[COUNTER_BONE]), opponent=mon(H.CHANSEY))
        chansey = state.players[1].active
        chansey.persistent_effects = (AttackBarrier(chansey.card, 1, TURN - 1, TURN),)
        saved, state.turn_number = state.turn_number, TURN - 1
        state.add_event("persistent_effect_added", player=1, pokemon=chansey.card, pokemon_id=chansey.pokemon_id, persistent_effect="attack_barrier",
                        source_card=chansey.card, source_player=1, active_turn=TURN, effect="test")
        state.turn_number = saved
        rejects(self, state, UseAttack(0, 1), HC3)

    def test_esp_redo_reflips_only_the_paralysis_coin(self):
        """ナツメのESPのやり直しは、コインを投げた要素（マヒ）だけをもう一度処理する（取りのぞき直さない）。ESP はナツメのポケモンにだけつき、このワザを持つナツメのポケモンは
        写しにないので、ESP があるとして要素の並びの組み立てだけを確かめる。"""
        state = board(marowak(markers=[COUNTER_BONE]), opponent=mon(H.CHANSEY))
        with mock.patch.object(E, "esp_cards", lambda s, p: (p.card,)), mock.patch.object(E, "esp_redo_problem", lambda *a: None):
            asking = declare(state, 1, TL)
            self.assertEqual(asking.decision.kind, ESP_REDO)
            redone = apply_kernel(with_coin_results(asking, HD), ResolveDecision(0, asking.decision.id, (1,)))
        self.assertEqual(len(new_events(state, redone, "marker_removed")), 1)
        self.assertEqual(redone.players[1].active.conditions.names(), ("paralysis",))

    def test_bone_killer_optional(self):
        state = board(mon(H.CUBONE_PR1, (F,), markers=[COUNTER_BONE]), opponent=mon(H.CHANSEY))
        asking = declare(state, 1)
        self.assertEqual((asking.decision.kind, asking.decision.options, asking.decision.context_value("marker")), (SELECT_MARKER_COUNT, (0, 1), COUNTER_BONE))
        used = answer(asking, (1,))
        kept = answer(asking, (0,))
        self.assertEqual(damages(asking, used), [(80, None)])  # (10 + 30) × 2（ラッキーの弱点は闘）
        self.assertEqual((damages(asking, kept), marks(kept.players[0].active)), ([(20, None)], [(COUNTER_BONE, None)]))
        self.assertEqual(new_events(asking, kept, "marker_removal_declined")[0]["marker"], COUNTER_BONE)
        none = declare(board(mon(H.CUBONE_PR1, (F,)), opponent=mon(H.CHANSEY)), 1)
        self.assertEqual((none.decision is None or none.decision.kind != SELECT_MARKER_COUNT, damages(state, none)), (True, [(20, None)]))  # カウンターなしでも使える
        for result in (used, kept, none):
            audited(self, result)


# ---------------------------------------------------------------- 4 章: たべものカウンター（たべる・ころがる）


class FoodCounterTest(unittest.TestCase):
    def test_eat_until_two(self):
        state = board(mon(H.HUNGRY_SNORLAX, (W,)))
        once = declare(state, 0)
        twice = board(mon(H.HUNGRY_SNORLAX, (W,), markers=[COUNTER_FOOD]))
        self.assertEqual(marker_count(declare(twice, 0).players[0].active, COUNTER_FOOD), 2)
        rejects(self, board(mon(H.HUNGRY_SNORLAX, (W,), markers=[COUNTER_FOOD, COUNTER_FOOD])), UseAttack(0, 0), "MARKER_LIMIT", error=IllegalActionError)
        audited(self, once)

    def test_rollout_any_number_adds_to_the_base(self):
        """取りのぞいた数 × 30 を基本となるダメージ 20 に加える（p.321 の 1 段階。そのあとで弱点）。選べる数を相手の残りHPでしぼらない。"""
        state = board(mon(H.HUNGRY_SNORLAX, (W, W, W), markers=[COUNTER_FOOD, COUNTER_FOOD]), opponent=mon(H.MACHOP, damage=40))
        asking = declare(state, 1)
        self.assertEqual(asking.decision.options, (0, 1, 2))  # ワンリキーの残りHP 10 でも 0〜2
        for count, expected in ((0, 20), (1, 50), (2, 80)):
            done = answer(asking, (count,))
            self.assertEqual([e["steps"][0] for e in new_events(asking, done, "damage")], [("1 基本となる計算", expected)])
            self.assertEqual(marker_count(done.players[0].active, COUNTER_FOOD), 2 - count)
            audited(self, done)

    def test_copy_reads_the_copiers_counters(self):
        """ピッピの「ゆびをふる」でまねたワザは、まねたピッピのカウンターを読む（くいしんぼカビゴンのものではない。ほねカウンターをたべものカウンターのかわりにしない）。"""
        state = board(mon(H.CLEFAIRY, (W, W, W), markers=[COUNTER_BONE]), opponent=mon(H.HUNGRY_SNORLAX, markers=[COUNTER_FOOD, COUNTER_FOOD]))
        selecting = declare(state, 1)
        self.assertEqual(selecting.decision.kind, "select_attack")
        ate = answer(selecting, (0,))
        self.assertEqual((marker_count(ate.players[0].active, COUNTER_FOOD), marker_count(ate.players[1].active, COUNTER_FOOD)), (1, 2))
        rolled = answer(selecting, (1,))
        self.assertEqual(rolled.decision, None)  # まねたピッピにたべものカウンターはない（ほねカウンターでは代わりにしない）
        self.assertEqual([e["steps"][0][1] for e in new_events(selecting, rolled, "damage")], [20])
        for result in (ate, rolled):
            audited(self, result)

    def test_copied_usage_conditions(self):
        """まねるワザの使うための条件は、まねたポケモンの数で確かめる（ピッピは説明にしたがうので選べない。v0.31 の ``copy_problem``）。"""
        full = board(mon(H.CLEFAIRY, (W, W, W), markers=[COUNTER_FOOD, COUNTER_FOOD]), opponent=mon(H.HUNGRY_SNORLAX))
        selecting = declare(full, 1)
        self.assertNotIn(0, selecting.decision.options)  # たべる（2 つのっている）は選べない
        boneless = board(mon(H.CLEFAIRY, (W, W, W)), opponent=marowak(opponent=True))
        selecting = declare(boneless, 1)
        self.assertNotIn(1, selecting.decision.options)  # ほねこんぼう（のっていない）は選べない


# ---------------------------------------------------------------- 5 章: のろいマーカー（あくまののろい）


class CurseTest(unittest.TestCase):
    def test_places_on_heads(self):
        state = board(mon(H.JYNX_PR1, (P,)), opponent=mon(H.CHANSEY, markers=[MARKER_CURSE]))
        heads = declare(state, 0, HD)
        self.assertEqual(marker_count(heads.players[1].active, MARKER_CURSE), 2)  # のっていてものせる（効果は同じ）
        tails = declare(state, 0, TL)
        self.assertEqual(marker_count(tails.players[1].active, MARKER_CURSE), 1)
        for result in (heads, tails):
            audited(self, result)

    def test_weakness_is_times_four(self):
        """弱点のタイプのポケモンからのワザのダメージは、弱点の計算が「×4」（2 つでも ×4。最終ダメージを 2 倍にしない）。弱点でないタイプ・弱点のないポケモン・
        弱点・抵抗力に関係ないダメージは変わらない。全体のルールの数は変えない。"""
        cubone = mon(H.CUBONE_PR1, (F,))
        cases = (
            (mon(H.CHANSEY, markers=[MARKER_CURSE]), [(40, 4)]),  # 闘 → 弱点 闘: 10 × 4
            (mon(H.CHANSEY, markers=[MARKER_CURSE, MARKER_CURSE]), [(40, 4)]),
            (mon(H.CHANSEY), [(20, None)]),
            (mon(H.GASTLY, markers=[MARKER_CURSE]), [(0, None)]),  # 弱点なし・抵抗力 闘 -30
            (mon(H.SCYTHER, markers=[MARKER_CURSE]), [(0, None)]),  # 弱点 炎（闘のワザでは弱点の計算をしない）・抵抗力 闘 -30
        )
        for opponent, expected in cases:
            state = board(cubone, opponent=opponent)
            done = declare(state, 1)
            self.assertEqual(damages(state, done), expected, opponent)
            self.assertEqual(done.rules.weakness_multiplier, 2)
            audited(self, done)
        ignored = board(mon(H.BROCKS_SANDSLASH, (F, F), played_turn=2, evolved_from=H.BROCKS_SANDSHREW, evolved_turn=5), opponent=mon(H.CHANSEY, markers=[MARKER_CURSE]))
        self.assertEqual(damages(ignored, declare(ignored, 0)), [(20, None)])  # スピードスター（弱点を計算しない）

    def test_defender_after_weakness(self):
        """p.321 の順番: 3 段階の「×4」のあとに 7 段階のディフェンダー（-20）。"""
        state = board(mon(H.CUBONE_PR1, (F,)), opponent=mon(H.CHANSEY, markers=[MARKER_CURSE], trainers=[(H.DEFENDER, TURN)]))
        done = declare(state, 1)
        self.assertEqual(next(e["steps"] for e in new_events(state, done, "damage"))[:2], (("1 基本となる計算", 10), ("3 弱点", 40)))
        self.assertEqual(damages(state, done), [(20, 4)])

    def test_confusion_self_damage_is_unresolved_only_when_self_weak(self):
        """こんらんの 20 が「ワザによるダメージ」かは決まらない（既存の UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS）。自分の弱点が当てはまるときだけ、コインの前に止める。"""
        rejects(self, board(mon(H.JYNX_PR1, (P, W), confusion=True, markers=[MARKER_CURSE])), UseAttack(0, 1), CONFUSION_MODIFIERS)
        state = board(mon(H.CHANSEY, (W, W, W, W), confusion=True, markers=[MARKER_CURSE]))
        done = declare(state, 1, TL)
        self.assertEqual([e["amount"] for e in new_events(state, done, "confusion_damage")], [20])

    def test_unbounded_coins_use_the_same_multiplier(self):
        """れんぞくいしなげ（「うら」が出るまで）の先読みの組は、実際の計算と同じ「×4」で分ける（上限を広げるだけにしない）。組の代表で試した結果は、すべての「おもて」の数を
        試した結果と同じ。"""
        from tests.test_geodude_line_v0_64 import board as geodude_board
        from tests.test_geodude_line_v0_64 import captured_classes, outcome

        geodude = H.FOSSIL_GEODUDE
        cursed = geodude_board(mon(geodude, (F, F)), mon(H.CHANSEY, markers=[MARKER_CURSE]))
        plain = geodude_board(mon(geodude, (F, F)), mon(H.CHANSEY))
        cursed_classes, plain_classes = captured_classes(cursed), captured_classes(plain)
        self.assertEqual([cursed_classes.key_of(h)[1] for h in range(5)], [0, 40, 80, 120, 120])  # 「おもて」1 枚 10 × 4。3 枚で残りの HP 120 にまとめる
        self.assertEqual([plain_classes.key_of(h)[1] for h in range(5)], [0, 20, 40, 60, 80])
        self.assertEqual(cursed_classes.representatives, (0, 1, 2, 3))
        for heads in (0, 1, 2, 3, 5):
            self.assertEqual(outcome(cursed, heads, "derived"), outcome(cursed, heads, "derived", brute=8))


# ---------------------------------------------------------------- 6 章: 色マーカー（ペイント）


class PaintTest(unittest.TestCase):
    def test_choose_a_non_colorless_color_and_replace(self):
        state = board(mon(H.SMEARGLE_PRN, (W,)), opponent=mon(H.CHANSEY, markers=[(MARKER_COLOR, EnergyType.FIRE)]))
        asking = declare(state, 0, HD)
        self.assertEqual((asking.decision.kind, asking.decision.options), (SELECT_COLOR, E.NON_COLORLESS_CHOICES))
        self.assertIn(E.COLORS.index(EnergyType.DARKNESS), asking.decision.options)
        self.assertIn(E.COLORS.index(EnergyType.METAL), asking.decision.options)
        done = answer(asking, (E.COLORS.index(EnergyType.METAL),))
        self.assertEqual(marks(done.players[1].active), [(MARKER_COLOR, EnergyType.METAL)])
        self.assertEqual([e["reason"] for e in new_events(asking, done, "marker_removed")], ["replaced"])
        self.assertEqual(E.type_readings(done, done.players[1].active), (EnergyType.METAL,))
        chansey = done.players[1].active
        self.assertEqual((E.weakness_of(done, chansey), E.resistance_of(done, chansey)[0]), (EnergyType.FIGHTING, EnergyType.PSYCHIC))  # 弱点・抵抗力は変えない
        tails = declare(state, 0, TL)
        self.assertEqual((tails.decision, marks(tails.players[1].active)), (None, [(MARKER_COLOR, EnergyType.FIRE)]))
        for result in (done, tails):
            audited(self, result)

    def test_painted_type_is_used_for_weakness(self):
        """色マーカーの色のポケモンとしてあつかう（ワザを使うポケモンのタイプ）。ついているエネルギーの色は変えない。"""
        state = board(mon(H.CHANSEY, (W, W, W, W), markers=[(MARKER_COLOR, EnergyType.WATER)]), opponent=mon(H.CHARMANDER))
        done = declare(state, 1)
        self.assertTrue(new_events(state, done, "damage")[0]["weakness"])
        self.assertEqual(state.energy_types(state.players[0].active), [EnergyType.WATER] * 4)

    def test_color_marker_and_shift_color_is_cm1(self):
        """色マーカーと［へんしょく］で変えた色が同じポケモンにあるときは、どちらの色か決まらない（CM1）。読み方で結果が変わる処理だけを止める。"""
        venomoth = mon(H.VENOMOTH, (G, G), played_turn=2, evolved_from=H.VENONAT, evolved_turn=5, markers=[(MARKER_COLOR, EnergyType.FIRE)])
        state = board(venomoth, bench=(mon(H.STARYU),), opponent=mon(H.CHARMANDER))
        self.assertEqual(E.type_readings(state, state.players[0].active), (EnergyType.FIRE,))
        asking = apply_kernel(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        shifted = answer(asking, (E.COLORS.index(EnergyType.WATER),))
        self.assertEqual(E.type_readings(shifted, shifted.players[0].active), (EnergyType.FIRE, EnergyType.WATER))
        self.assertEqual(E.type_reading_cause(shifted, shifted.players[0].active), "cm1")
        rejects(self, shifted, UseAttack(0, 0), CM1)  # ヒトカゲの弱点 水: 読み方で弱点の計算が変わる
        audited(self, shifted)
        calm = board(venomoth, bench=(mon(H.STARYU),), opponent=mon(H.RATTATA))  # コラッタ（弱点 闘・抵抗力 超）: どちらの色でも同じ
        calm = answer(apply_kernel(calm, UsePokemonPower(0, calm.players[0].active.pokemon_id, 0)), (E.COLORS.index(EnergyType.WATER),))
        done = declare(calm, 0)
        self.assertEqual(damages(calm, done), [(10, None)])
        audited(self, done)


# ---------------------------------------------------------------- 7 章: ミュウツー（かんぜんかいふく・サイコブラスト）


class FullRecoveryTest(unittest.TestCase):
    def test_discard_then_clear_then_cure(self):
        state = board(mon(H.MEWTWO_ES3, (P, P, H.RECYCLE_ENERGY), damage=30, poison=10, confusion=True,
                          markers=[MARKER_STICKY, MARKER_CURSE, (MARKER_COLOR, EnergyType.FIRE)], prevent_damage=TURN))
        done = declare(state, 0, HD)
        mewtwo = done.players[0].active
        self.assertEqual((mewtwo.energy, mewtwo.damage, mewtwo.markers, mewtwo.conditions.names()), ([], 0, (), ()))
        self.assertEqual([type(e).__name__ for e in mewtwo.persistent_effects], ["PreventDamage"])  # 「その他の効果」は取りのぞかない
        kinds = [e["kind"] for e in new_events(state, done) if e["kind"] in ("discard_energy", "energy_returned_to_hand", "remove_all_damage_counters",
                                                                            "marker_removed", "special_conditions_removed")]
        self.assertEqual(kinds, ["discard_energy"] * 3 + ["energy_returned_to_hand", "remove_all_damage_counters"] + ["marker_removed"] * 3
                         + ["special_conditions_removed"])
        self.assertIn(state.players[0].active.energy[2], done.players[0].hand)  # リサイクルエネルギーは共通の経路で手札にもどる
        self.assertEqual(new_events(state, done, "special_conditions_removed")[0]["conditions"], ("poison", "confusion"))
        audited(self, done)

    def test_confused_tails_does_nothing(self):
        state = board(mon(H.MEWTWO_ES3, (P, P), damage=30, confusion=True, markers=[MARKER_STICKY]))
        failed = declare(state, 0, TL)
        self.assertEqual((len(failed.players[0].active.energy), new_events(state, failed, "marker_removed")), (2, []))

    def test_other_counters_are_fr1(self):
        """ほね・たべものカウンターも「ダメージカウンターやマーカー」に含むかは決まらない（KR1）。状態・乱数を変えずに止める（こんらんのコインも投げない）。メタモンの［へんしん］で
        くいしんぼカビゴンの「たべる」を使ったあと、ミュウツーと同じカードになると起こる。"""
        state = board(mon(H.DITTO, (P, P), markers=[COUNTER_FOOD]), opponent=mon(H.MEWTWO_ES3))
        rejects(self, state, UseAttack(0, 0, card=state.players[1].active.card), KR1)
        # ピッピの「ゆびをふる」: まねたピッピのカウンターで決まらないワザは、選べるが選ぶと止める（宣言のすべては止めない。v0.31 の HC9 の書き方の理由に KR1）
        copying = declare(board(mon(H.CLEFAIRY, (W, W, W), markers=[COUNTER_BONE]), opponent=mon(H.MEWTWO_ES3)), 1)
        self.assertEqual((copying.decision.options, copying.decision.context_value("unresolved_choices")), ((0, 1), (0,)))
        self.assertIn("KR1", copying.decision.context_value("unresolved_reason"))
        rejects(self, copying, ResolveDecision(0, copying.decision.id, (0,)), "UNRESOLVED_COPIED_ATTACK")

    def test_psychic_blast(self):
        state = board(mon(H.MEWTWO_ES3, (P, P, P)), opponent=mon(H.CHANSEY, (W, W)))
        asking = declare(state, 1, HD)
        self.assertEqual(asking.decision.kind, "discard_opponent_energy")
        done = answer(asking, (asking.decision.options[0],))
        self.assertEqual(len(done.players[1].active.energy), 1)
        audited(self, done)


# ---------------------------------------------------------------- 8 章: 決定・保存


class DecisionPersistenceTest(unittest.TestCase):
    def waiting_states(self):
        rollout = declare(board(mon(H.HUNGRY_SNORLAX, (W, W, W), markers=[COUNTER_FOOD, COUNTER_FOOD]), opponent=mon(H.CHANSEY)), 1)
        paint = declare(board(mon(H.SMEARGLE_PRN, (W,)), opponent=mon(H.CHANSEY)), 0, HD)
        return rollout, paint

    def test_resume_after_copy_and_pickle_is_identical(self):
        for waiting in self.waiting_states():
            with self.subTest(kind=waiting.decision.kind):
                audited(self, waiting)
                d = waiting.decision
                choice = ResolveDecision(d.player, d.id, (d.options[-1],))
                results = [apply_kernel(s, choice) for s in (waiting, waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting)))]
                for other in results[1:]:
                    self.assertEqual(snapshot(other), snapshot(results[0]))
                self.assertEqual(new_events(waiting, results[0], "coin_flip"), [])  # 決定の前に投げたコインを投げ直さない
                self.assertLessEqual(len(new_events(waiting, results[0], "marker_removed")), 1)  # 取りのぞきは 1 回
                audited(self, results[0])

    def test_invalid_answers_change_nothing(self):
        for waiting in self.waiting_states():
            with self.subTest(kind=waiting.decision.kind):
                d = waiting.decision
                before = snapshot(waiting)
                for bad in ((999,), (d.options[0], d.options[-1]), ()):
                    with self.assertRaises((IllegalActionError, UnsupportedError)):
                        apply_kernel(waiting, ResolveDecision(d.player, d.id, bad))
                    self.assertEqual(snapshot(waiting), before)

    def test_preflight_tries_every_count(self):
        """先読みは取りのぞく数のすべての答えを試す（``legacy`` の止める関数にまかせない。のろいマーカー・色マーカーのある盤面は知らない選択として扱う）。"""
        state = board(mon(H.CHANSEY, (W, W, W, W)), opponent=mon(H.CHANSEY, markers=[MARKER_CURSE]))
        self.assertIn("のろいマーカー・色マーカー", __import__("kyuura_engine.resolution.flow", fromlist=["x"]).legacy_unknown_features(state, state.players[0].active))
        element = programs.OptionalRemoveOwnMarkers(COUNTER_FOOD)
        decision = declare(board(mon(H.HUNGRY_SNORLAX, (W, W, W), markers=[COUNTER_FOOD, COUNTER_FOOD]), opponent=mon(H.CHANSEY)), 1).decision
        self.assertEqual(element.dry_choices(None, decision), [(0,), (1,), (2,)])


class RuffFixTest(unittest.TestCase):
    """v0.89 の ruff の指摘（TRY004）2 件: 型の誤りは TypeError（組み立てる時・読む時）。正常な処理の結果・公開のエラーコードは変えない。"""

    def test_target_damage_rejects_a_non_fixed_base_at_construction(self):
        with self.assertRaises(TypeError):
            programs.TargetDamage(programs.HeadsTimes(3, 10), wr_unstated=True)
        with self.assertRaises(TypeError):
            programs.TargetDamage(programs.HeadsTimes(3, 10), defender_effects=False, ignore_scope=programs.IGNORE_UNSTATED)
        programs.TargetDamage(programs.Fixed(20), wr_unstated=True)

    def test_chosen_pokemon_wrong_record_type(self):
        run = mock.Mock()
        run.fs.results = {"target": programs.ChosenColor(None)}
        with self.assertRaises(TypeError):
            programs.chosen_pokemon(run, "target")
        run.fs.results = {}
        with self.assertRaises(RuntimeError):
            programs.chosen_pokemon(run, "target")


class DocumentTest(unittest.TestCase):
    def test_document_lists_cards_codes_and_counts(self):
        text = DOC.read_text(encoding="utf-8")
        for card in H.V0_90_CARDS:
            self.assertIn(card, text)
        for key in V090_ATTACKS:
            self.assertIn(DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).name_ja, text)
        for code in (CM1, KR1, "CM1", "KR1", "形式 24", "1,115", "1,366", "262"):
            self.assertIn(code, text)

    def test_no_card_id_branches_in_engine_or_resolution(self):
        texts = [(ROOT / "kyuura_engine" / "engine.py").read_text(encoding="utf-8")]
        texts += [p.read_text(encoding="utf-8") for p in (ROOT / "kyuura_engine" / "resolution").glob("*.py")]
        texts.append((ROOT / "kyuura_engine" / "markers.py").read_text(encoding="utf-8"))
        for card_id in H.V0_90_CARDS:
            self.assertFalse(any(card_id in text for text in texts), card_id)


if __name__ == "__main__":
    unittest.main()

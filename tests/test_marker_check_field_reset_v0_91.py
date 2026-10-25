"""v0.91（docs/marker-check-field-reset-v0.91.md）: 残りのマーカーのポケモン 3 枚とヒノアラシ（ワザ 7）と、くろこげマーカーのポケモンチェック・選んだ個体のマーカー・
マーカーのポケモンへのダメージ・オールクリア（場のトレーナー・特殊状態・その他の効果・マーカーとカウンター・ワザを使っているあいだの特殊能力の抑止）。

根拠は kyuura データの採用（kyuura ``7d3f4ca`` の data/cards.json の日本語の印刷の文面）と、既存の規定の記録（GR-2000-P323-POKEMON-CHECK・GR-2000-P325-SAME-TIMING・
GR-2000-P320-DAMAGE-FIGURE・GR-2000-P321-DAMAGE-ORDER・GR-2000-P322-PERSISTENT-EFFECTS・GR-2000-P324-DEVOLUTION など。docs 各章）。2000 年 5 月の RUL-CHAR-MARKER は持ち込まない。
公式ガイドブックの新しい読み直し・カードの画像・pcg-search.com との照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの
自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.91``）。
"""

from __future__ import annotations

import copy
import pathlib
import pickle
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    EndTurn,
    EvolvePokemon,
    ResolveDecision,
    Retreat,
    UseAttack,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import (
    EnergyType,
    load_card_pool,
    pool_from_extract,
    read_extract,
)
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import SELECT_COLOR, SELECT_POKEMON
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import (
    ATTACK_POWER_SUPPRESSION,
    COUNTER_BONE,
    MARKER_AND_COUNTER_KINDS,
    MARKER_CHAR,
    MARKER_COLOR,
    MARKER_CURSE,
    MARKER_KINDS,
    MARKER_LIGHTNING_ROD,
    MARKER_STICKY,
    Phase,
)
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.release_catalog import cards_before
from tests.test_entry_powers_energy_lifecycle_v0_85 import stage1
from tests.test_neo_trainer_components_v0_80 import audited, mon, new_events, rejects
from tests.test_shining_gentle_v0_83 import answer, board, play

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "marker-check-field-reset-v0.91.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
TURN = 7
R, W, L, F, C, P = H.FIRE, H.WATER, H.LIGHTNING, H.FIGHTING, H.WATER, H.PSYCHIC
KK1 = "UNRESOLVED_POKEMON_CHECK_CHAR_COIN_ORDER"
HR1 = "UNRESOLVED_LIGHTNING_BOLT_DEFENDER_UNITS"
HX1 = "UNRESOLVED_HYPER_TEXTURE_UNMARKED_TARGET"
ZC1 = "UNRESOLVED_ALL_CLEAR_OTHER_EFFECTS"
ZC2 = "UNRESOLVED_ALL_CLEAR_ATTACK_SOURCE"
ZC3 = "UNRESOLVED_ALL_CLEAR_FOSSIL_IN_PLAY"
FA1 = "UNRESOLVED_IGNORED_EFFECTS_SCOPE"
BY1 = "UNRESOLVED_POKEMON_CHECK_BERRY_ORDER"
SC1 = "UNRESOLVED_SCRAM_TIMING"
DOUBLE_KO = "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"
MH1 = "UNRESOLVED_MAX_HP_DROP"
BERRY = "neo1-073"  # きのみ（ダメージカウンターが 2 個以上なら 2 個とりのぞく。v0.81）
QUILAVA, ELECTABUZZ, POLYGON, CYNDAQUIL = H.QUILAVA_NEO1, H.ELECTABUZZ_ES2, H.POLYGON_PRN, H.CYNDAQUIL_NEO4
V091_ATTACKS = [AttackKey(c, i) for c in H.V0_91_POKEMON for i in range(len(load_card_pool().definitions[c].attacks))]


def marks(pokemon):
    return [(m.kind, m.color) for m in pokemon.markers]


def declare(state, index, *coins, player=0):
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UseAttack(player, index))


def end_turn(state, *coins, player=0):
    return apply_kernel(with_coin_results(state, *coins) if coins else state, EndTurn(player))


def quilava(energy=(R, R, R), **extra):
    return stage1(QUILAVA, energy, base=CYNDAQUIL, **extra)


def kinds_since(before, after):
    return [e["kind"] for e in after.log[len(before.log):]]


def damage_amounts(before, after):
    return [(e.get("target"), e["amount"]) for e in new_events(before, after, "damage")]


# ---------------------------------------------------------------- 1 章: 対象と登録


class RegistrationTest(unittest.TestCase):
    def test_every_attack_is_registered(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_91"]), H.V0_91_CARDS)
        self.assertEqual(len(V091_ATTACKS), 7)
        for key in V091_ATTACKS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
                attack = pool.definitions[key.card_id].attacks[key.attack_index]
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja), (attack.name_ja, attack.text_ja, attack.text_ja))
                self.assertEqual(entry.effect.check(attack), [])
        for card in H.V0_91_CARDS:
            self.assertIn(card, pool.playable_ids)
            self.assertEqual(pool.definitions[card].powers, ())

    def test_types(self):
        effect = lambda card, i: DEFAULT_EFFECTS.attack_entry(card, i).effect
        self.assertEqual(effect(QUILAVA, 0), E.DamageThenAttackCoinCheck(single_use=False))
        self.assertEqual(effect(CYNDAQUIL, 0), E.DamageThenAttackCoinCheck(single_use=False))
        self.assertEqual(effect(QUILAVA, 1), E.DamageThenCoinMarkOpponentIfAbsent(MARKER_CHAR))
        self.assertEqual(effect(ELECTABUZZ, 0), E.ChooseOpponentPokemonMarkIfAbsent(MARKER_LIGHTNING_ROD))
        self.assertEqual(effect(ELECTABUZZ, 1), E.DamageThenMarkedPokemonDamage(MARKER_LIGHTNING_ROD, 20))
        self.assertEqual(effect(POLYGON, 0), E.AllClear())
        self.assertEqual(effect(POLYGON, 1), E.ChooseOpponentPokemonReplaceColorMarker())
        # えんまくの全文検査: 効果が 1 回で消える書き方（すなかけ）としては受け付けない
        attack = load_card_pool().definitions[QUILAVA].attacks[0]
        self.assertTrue(E.DamageThenAttackCoinCheck(single_use=True).check(attack))
        self.assertEqual([(a.cost, a.damage) for a in (attack, load_card_pool().definitions[CYNDAQUIL].attacks[0])],
                         [((EnergyType.FIRE, EnergyType.FIRE), 20), ((EnergyType.FIRE,), 10)])

    def test_unregistered_without_the_v0_91_entries(self):
        """今回の登録を除くと対戦に使えなくなるのは、ちょうど 4 枚（ほかのカードは失われない）。過去の範囲は ``cards_before`` で切り出す。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V091_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(H.V0_91_CARDS))
        self.assertEqual(set(H.V0_91_CARDS) & set(cards_before(read_extract(), "0.91")), set())

    def test_quilava_evolves_from_either_cyndaquil(self):
        pool = load_card_pool()
        self.assertEqual(pool.definitions[QUILAVA].evolves_from, "ヒノアラシ")
        for base in (CYNDAQUIL, "neo1-018"):
            state = board(mon(base, played_turn=3), hand=(QUILAVA,))
            card = next(u for u in state.players[0].hand if state.cards[u].card_id == QUILAVA)
            evolved = apply_kernel(state, EvolvePokemon(0, card, state.players[0].active.pokemon_id))
            self.assertEqual(evolved.cards[evolved.players[0].active.card].card_id, QUILAVA)
            audited(self, evolved)


# ---------------------------------------------------------------- 2 章: マーカーの状態


class MarkerKindsTest(unittest.TestCase):
    def test_kinds_and_format(self):
        self.assertIn(MARKER_CHAR, MARKER_KINDS)
        self.assertIn(MARKER_LIGHTNING_ROD, MARKER_KINDS)
        self.assertEqual(MARKER_AND_COUNTER_KINDS[-2:], (COUNTER_BONE, "food"))
        state = board(mon(H.CHANSEY, markers=[MARKER_CHAR, MARKER_LIGHTNING_ROD]))
        self.assertIn(24, FORMAT_VERSIONS)  # 新しい種類は形式 24 の markers の値（形式を増やさない。v0.99: 今の最新の形式（25）は tests/test_catalog_contract.py）
        data = state_to_dict(state, format_version=24)
        self.assertEqual([m["kind"] for m in data["players"][0]["active"]["markers"]], [MARKER_CHAR, MARKER_LIGHTNING_ROD])
        with self.assertRaises(ValueError):
            state_to_dict(state, format_version=23)
        audited(self, state)

    def test_bench_keeps_and_evolution_removes(self):
        state = board(mon(CYNDAQUIL, (R, R), markers=[MARKER_CHAR, MARKER_LIGHTNING_ROD], played_turn=3), hand=(QUILAVA,))
        active = state.players[0].active
        retreated = apply_kernel(state, Retreat(0, (active.energy[0],), state.players[0].bench[0].card))
        self.assertEqual(marks(retreated.players[0].bench[0]), [(MARKER_CHAR, None), (MARKER_LIGHTNING_ROD, None)])
        card = next(u for u in state.players[0].hand if state.cards[u].card_id == QUILAVA)
        evolved = apply_kernel(state, EvolvePokemon(0, card, active.pokemon_id))
        self.assertEqual(evolved.players[0].active.markers, ())
        self.assertEqual({(e["marker"], e["reason"]) for e in new_events(state, evolved, "marker_removed")}, {(MARKER_CHAR, "evolve"), (MARKER_LIGHTNING_ROD, "evolve")})
        healed = play(board(mon(H.CHANSEY, poison=10, markers=[MARKER_CHAR]), hand=(H.FULL_HEAL,)), H.FULL_HEAL)
        self.assertEqual((healed.players[0].active.conditions.names(), marks(healed.players[0].active)), ((), [(MARKER_CHAR, None)]))
        for result in (retreated, evolved, healed):
            audited(self, result)


# ---------------------------------------------------------------- 3 章: えんまく


class SmokescreenTest(unittest.TestCase):
    def test_effect_is_not_single_use(self):
        for card, energy, damage in ((CYNDAQUIL, (R,), 10), (QUILAVA, (R, R), 20)):
            with self.subTest(card=card):
                state = board(quilava((R, R)) if card == QUILAVA else mon(card, energy), opponent=mon(H.CHANSEY, (W, W)))
                done = declare(state, 0)
                self.assertEqual(damage_amounts(state, done), [(None, damage)])
                check = done.players[1].active.persistent_effects[0]
                self.assertEqual((type(check).__name__, check.single_use), ("AttackCoinCheck", False))
                # 次の相手の番: 「うら」ならワザは失敗する。使ったあとも効果は残る（すなかけのように 1 回で消えない）
                failed = declare(done, 0, TL, player=1)
                self.assertTrue(new_events(done, failed, "attack_failed"))
                self.assertEqual(new_events(done, failed, "persistent_effect_removed")[:1] and new_events(done, failed, "persistent_effect_removed")[0]["reason"], "expired")
                audited(self, failed)


# ---------------------------------------------------------------- 4 章: くろこげマーカー


class CharPlacementTest(unittest.TestCase):
    def test_heads_tails_and_present(self):
        state = board(quilava(), opponent=mon(H.CHANSEY))
        heads = declare(state, 1, HD, TL)  # ワザの「おもて」→ ポケモンチェックのくろこげのコインは「うら」
        self.assertEqual(damage_amounts(state, heads), [(None, 30)])
        self.assertEqual(marks(heads.players[1].active), [(MARKER_CHAR, None)])
        self.assertEqual([(e["player"], e["damaged"]) for e in new_events(state, heads, "char_check")], [(1, True)])
        self.assertEqual(heads.players[1].active.damage, 30 + 20)
        tails = declare(state, 1, TL)
        self.assertEqual(marks(tails.players[1].active), [])
        present = board(quilava(), opponent=mon(H.CHANSEY, markers=[MARKER_CHAR]))
        again = declare(present, 1, HD)  # のっていればワザのコインは投げない（HD はポケモンチェックのコイン）
        self.assertEqual([e["source"] for e in new_events(present, again, "coin_flip")], ["pokemon_check"])
        self.assertEqual(marks(again.players[1].active), [(MARKER_CHAR, None)])
        for result in (heads, tails, again):
            audited(self, result)

    def test_knocked_out_by_damage_no_coin(self):
        state = board(quilava(), opponent=mon(H.RATTATA), opponent_bench=(H.RATTATA,))
        done = declare(state, 1)
        self.assertEqual([e for e in new_events(state, done, "coin_flip") if e["source"] == "attack"], [])
        audited(self, done)

    def test_damage_prevented_effect_still_applies(self):
        """「ダメージを受けない」状態（かたまる）でも効果の要素は有効（p.321）。ダメージの防止と効果の防止を混ぜない。"""
        state = board(quilava(), opponent=mon(H.CHANSEY, prevent_damage=TURN - 1))
        done = declare(state, 1, HD, HD)
        self.assertEqual(done.players[1].active.damage, 0)
        self.assertEqual(marks(done.players[1].active), [(MARKER_CHAR, None)])
        audited(self, done)


class CharCheckTest(unittest.TestCase):
    """ポケモンチェックの 1 の「指示されたこと」で、持ち主がくろこげマーカーのポケモンそれぞれにコインを投げ、「うら」なら弱点・抵抗力・特殊能力・その他の効果に関係なく 20。"""

    def test_tails_twenty_ignoring_everything_heads_nothing(self):
        state = board(mon(H.CHANSEY), opponent=mon(H.CHARMANDER if hasattr(H, "CHARMANDER") else H.CHANSEY, (H.METAL_ENERGY_NIP1X,), markers=[MARKER_CHAR]),
                      opponent_bench=(mon(H.RATTATA, markers=[MARKER_CHAR]),))
        done = end_turn(state, TL, HD)
        self.assertEqual([(e["pokemon_id"], e["result"], e["damaged"]) for e in new_events(state, done, "char_check")],
                         [(state.players[1].active.pokemon_id, "tails", True), (state.players[1].bench[0].pokemon_id, "heads", False)])
        self.assertEqual([e["amount"] for e in new_events(state, done, "char_damage")], [20])  # 鋼エネルギー（NIP1X-010）の「-10」も当てはめない
        self.assertEqual([e["source"] for e in new_events(state, done, "coin_flip")], ["pokemon_check", "pokemon_check"])
        self.assertEqual(kinds_since(state, done)[:8], ["end_turn_without_attack", "turn_end", "pokemon_check", "coin_flip", "char_check", "coin_flip", "char_check", "char_damage"])
        audited(self, done)

    def test_order_before_poison_and_knock_out(self):
        state = board(mon(H.CHANSEY), opponent=mon(H.RATTATA, poison=10, damage=10, markers=[MARKER_CHAR]))
        done = end_turn(state, TL)
        kinds = kinds_since(state, done)
        self.assertLess(kinds.index("char_damage"), kinds.index("poison_damage"))  # 指示されたこと → どく（p.323）
        self.assertEqual([e.get("timing") for e in new_events(state, done, "knock_out")], ["pokemon_check"])
        audited(self, done)

    def test_both_players_flip_stops_before_coins(self):
        state = board(mon(H.CHANSEY, markers=[MARKER_CHAR]), opponent=mon(H.CHANSEY, markers=[MARKER_CHAR]))
        done = end_turn(state)
        self.assertEqual((done.phase, done.halt.code), (Phase.HALTED, KK1))
        self.assertEqual(new_events(state, done, "coin_flip"), [])

    def test_berry_order_stops_before_coins(self):
        """くろこげの 20 ときのみ（2 個以上なら 2 個とりのぞく）の順番で結果が変わる（BY1）。コインの前に止める。きのみの条件に届かなければ止めない。"""
        state = board(mon(H.CHANSEY), opponent=mon(H.CHANSEY, trainers=[(BERRY, None)], markers=[MARKER_CHAR]))
        done = end_turn(state)
        self.assertEqual((done.phase, done.halt.code), (Phase.HALTED, BY1))
        self.assertEqual(new_events(state, done, "coin_flip"), [])
        far = board(mon(H.CHANSEY), opponent=mon(H.CHANSEY, damage=30, trainers=[(BERRY, None)], markers=[MARKER_CHAR]))
        ok = end_turn(far, TL)  # すでに 3 個: どちらの順番でもきのみがはたらき、20 を受ける（30 + 20 - 20 = 30 と 30 - 20 + 20 = 30）
        self.assertEqual(ok.players[1].active.damage, 30)
        audited(self, ok)

    def test_double_knock_out_possible_stops_before_coins(self):
        state = board(mon(H.RATTATA, damage=20, markers=[]), opponent=mon(H.RATTATA, damage=20, markers=[MARKER_CHAR]))
        state = board(mon(H.RATTATA, poison=10, damage=20), opponent=mon(H.RATTATA, damage=20, markers=[MARKER_CHAR]))
        done = end_turn(state)
        self.assertEqual((done.phase, done.halt.code), (Phase.HALTED, DOUBLE_KO))  # 「うら」なら両方がきぜつする
        self.assertEqual(new_events(state, done, "coin_flip"), [])

    def test_bench_guard_is_fa1(self):
        rhydon = mon(H.BROCKS_RHYDON, played_turn=2, evolved_from=H.BROCKS_RHYHORN, evolved_turn=4)  # 相手の番に進化した［ベンチガード］のサイドン
        state = board(mon(H.CHANSEY), opponent=mon(H.CHANSEY), opponent_bench=(mon(H.RATTATA, markers=[MARKER_CHAR]), rhydon))
        done = end_turn(state)
        self.assertEqual((done.phase, done.halt.code), (Phase.HALTED, FA1))
        self.assertEqual(new_events(state, done, "coin_flip"), [])


# ---------------------------------------------------------------- 5 章: ひらいしん・かみなりショック


class LightningRodTest(unittest.TestCase):
    def test_choose_any_opponent_pokemon(self):
        state = board(mon(ELECTABUZZ, (L,)), opponent=mon(H.CHANSEY, markers=[MARKER_LIGHTNING_ROD]), opponent_bench=(H.RATTATA,))
        asking = declare(state, 0)
        self.assertEqual((asking.decision.kind, asking.decision.player), (SELECT_POKEMON, 0))
        self.assertEqual(asking.decision.options, tuple(p.pokemon_id for p in state.players[1].in_play()))
        self.assertIsNone(asking.decision.context_value("unresolved_choices"))  # のっているポケモンも選べる
        bench = answer(asking, (state.players[1].bench[0].pokemon_id,))
        self.assertEqual(marks(bench.players[1].bench[0]), [(MARKER_LIGHTNING_ROD, None)])
        active = answer(asking, (state.players[1].active.pokemon_id,))
        self.assertEqual(marks(active.players[1].active), [(MARKER_LIGHTNING_ROD, None)])  # 重ねない
        self.assertEqual(new_events(asking, active, "marker_added"), [])
        for result in (asking, bench, active):
            audited(self, result)

    def test_bolt_hits_every_marked_pokemon_with_weakness(self):
        state = board(mon(ELECTABUZZ, (L, L), markers=[MARKER_LIGHTNING_ROD]), bench=(mon(H.MAGIKARP, markers=[MARKER_LIGHTNING_ROD]), H.RATTATA),
                      opponent=mon(H.CHANSEY), opponent_bench=(mon(H.MAGIKARP, markers=[MARKER_LIGHTNING_ROD]), H.RATTATA))
        done = declare(state, 1)
        # 目安の 10 → 自分（雷・弱点 闘）20 → 相手の控えのコイキング（弱点 雷）40 → 自分の控えのコイキング 40。マーカーのないポケモンは受けない
        self.assertEqual(damage_amounts(state, done), [(None, 10), ("self", 20), ("opponent_bench", 40), ("self_bench", 40)])
        self.assertEqual([e.get("timing") for e in new_events(state, done, "knock_out")], [None, None])  # コイキング（HP 30）2 匹は同じワザのきぜつ
        audited(self, done)

    def test_no_marker_keeps_the_figure(self):
        state = board(mon(ELECTABUZZ, (L, L)), opponent=mon(H.CHANSEY))
        done = declare(state, 1)
        self.assertEqual(damage_amounts(state, done), [(None, 10)])
        audited(self, done)

    def test_defender_marked_units(self):
        """相手の対戦ポケモンにマーカー: 目安と 20 の 2 つ。合わせても別々でも同じなら止めない。プラスパワー・ディフェンダーで変わるなら HR1。"""
        plain = board(mon(ELECTABUZZ, (L, L)), opponent=mon(H.CHANSEY, markers=[MARKER_LIGHTNING_ROD]))
        done = declare(plain, 1)
        self.assertEqual(damage_amounts(plain, done), [(None, 10), (None, 20)])
        audited(self, done)
        weak = board(mon(ELECTABUZZ, (L, L)), opponent=mon(H.MAGIKARP, markers=[MARKER_LIGHTNING_ROD]))
        self.assertEqual(damage_amounts(weak, declare(weak, 1)), [(None, 20), (None, 40)])  # 弱点 ×2 は別々でも合わせても 60
        pluspower = board(mon(ELECTABUZZ, (L, L), trainers=[(H.PLUSPOWER, TURN)]), opponent=mon(H.CHANSEY, markers=[MARKER_LIGHTNING_ROD]))
        rejects(self, pluspower, UseAttack(0, 1), HR1)
        defender = board(mon(ELECTABUZZ, (L, L)), opponent=mon(H.CHANSEY, markers=[MARKER_LIGHTNING_ROD], trainers=[(H.DEFENDER, TURN)]))
        rejects(self, defender, UseAttack(0, 1), HR1)
        bench_only = board(mon(ELECTABUZZ, (L, L), trainers=[(H.PLUSPOWER, TURN)]), opponent=mon(H.CHANSEY), opponent_bench=(mon(H.RATTATA, markers=[MARKER_LIGHTNING_ROD]),))
        moved = declare(bench_only, 1)
        self.assertEqual(damage_amounts(bench_only, moved), [(None, 20), ("opponent_bench", 20)])  # プラスパワーは控えへのダメージを変えない
        audited(self, moved)


# ---------------------------------------------------------------- 6 章: ハイパーテクスチャー


class HyperTextureTest(unittest.TestCase):
    def marked(self):
        return board(mon(POLYGON, (W, W)), opponent=mon(H.CHANSEY, markers=[(MARKER_COLOR, EnergyType.FIRE)]), opponent_bench=(H.RATTATA,))

    def test_remove_choose_then_place(self):
        state = self.marked()
        asking = declare(state, 1)
        target = state.players[1].active.pokemon_id
        self.assertEqual(asking.decision.context_value("unresolved_choices"), (state.players[1].bench[0].pokemon_id,))
        coloring = answer(asking, (target,))
        self.assertEqual((coloring.decision.kind, marks(coloring.players[1].active)), (SELECT_COLOR, []))  # 色を選ぶあいだは色マーカーがない
        self.assertEqual([(e["marker"], e["reason"]) for e in new_events(asking, coloring, "marker_removed")], [(MARKER_COLOR, "replaced")])
        done = answer(coloring, (E.COLORS.index(EnergyType.METAL),))
        self.assertEqual(marks(done.players[1].active), [(MARKER_COLOR, EnergyType.METAL)])
        self.assertEqual(E.type_readings(done, done.players[1].active), (EnergyType.METAL,))
        self.assertEqual(new_events(coloring, done, "marker_removed"), [])  # とりのぞき直さない
        for result in (asking, coloring, done):
            audited(self, result)

    def test_invalid_answer_keeps_the_removal_and_resumes_after_copy(self):
        coloring = answer(declare(self.marked(), 1), (self.marked().players[1].active.pokemon_id,))
        with self.assertRaises(IllegalActionError):
            apply_kernel(coloring, ResolveDecision(0, coloring.decision.id, (E.COLORS.index(EnergyType.COLORLESS),)))
        self.assertEqual(marks(coloring.players[1].active), [])
        results = []
        for restored in (copy.deepcopy(coloring), pickle.loads(pickle.dumps(coloring)), coloring.clone()):
            results.append(answer(restored, (E.COLORS.index(EnergyType.DARKNESS),)))
        self.assertEqual({tuple(marks(r.players[1].active)) for r in results}, {((MARKER_COLOR, EnergyType.DARKNESS),)})
        self.assertEqual({len(r.log) for r in results}, {len(results[0].log)})
        self.assertTrue(state_to_dict(coloring, format_version=24)["decision"])
        audited(self, coloring)

    def test_unmarked_target_is_hx1(self):
        state = board(mon(POLYGON, (W, W)), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA,))
        rejects(self, state, UseAttack(0, 1), HX1)  # どれものっていなければ宣言の前に止める
        asking = declare(self.marked(), 1)
        rejects(self, asking, ResolveDecision(0, asking.decision.id, (asking.players[1].bench[0].pokemon_id,)), HX1)


# ---------------------------------------------------------------- 7 章: オールクリア


class AllClearTest(unittest.TestCase):
    def test_trainers_conditions_effects_and_markers(self):
        state = board(mon(POLYGON, (W,), trainers=[(H.PLUSPOWER, TURN)], markers=[MARKER_LIGHTNING_ROD]), bench=(mon(H.RATTATA, damage=10, markers=[COUNTER_BONE]),),
                      opponent=mon(H.CHANSEY, (W,), damage=30, poison=10, confusion=True, prevent_damage=TURN - 1, trainers=[(H.DEFENDER, TURN - 1)],
                                   markers=[MARKER_CHAR, MARKER_CURSE]),
                      opponent_bench=(mon(H.RATTATA, markers=[MARKER_STICKY, (MARKER_COLOR, EnergyType.FIRE)]),))
        done = declare(state, 0)
        for player in done.players:
            for pokemon in player.in_play():
                self.assertEqual((pokemon.trainers, pokemon.markers, pokemon.conditions.names(), pokemon.persistent_effects), ([], (), (), ()))
        self.assertEqual([(p.damage, len(p.energy)) for p in done.players[1].in_play()], [(30, 1), (0, 0)])  # ダメージカウンター・エネルギーはそのまま
        self.assertEqual(done.players[0].bench[0].damage, 10)
        discarded = new_events(state, done, "discard_attached_trainer")
        self.assertEqual({(e["player"], done.cards[e["card"]].card_id, e["reason"]) for e in discarded}, {(0, H.PLUSPOWER, "attack"), (1, H.DEFENDER, "attack")})
        self.assertEqual({e["reason"] for e in new_events(state, done, "persistent_effect_removed")}, {"cured"})
        self.assertEqual({e["reason"] for e in new_events(state, done, "marker_removed")}, {"cleared"})
        kinds = kinds_since(state, done)
        self.assertLess(kinds.index("trainer_effect_added"), kinds.index("discard_attached_trainer"))
        self.assertLess(kinds.index("marker_removed"), kinds.index("trainer_effect_removed"))
        self.assertEqual([e["reason"] for e in new_events(state, done, "trainer_effect_removed")], ["attack_end"])
        self.assertEqual([r for r in done.trainer_effects if r.kind == ATTACK_POWER_SUPPRESSION], [])
        audited(self, done)

    def test_stadium_doll_and_face_down(self):
        state = board(mon(POLYGON, (W,)), bench=(H.CLEFAIRY_DOLL,), hand=(H.NARROW_GYM,), opponent=mon(H.CHANSEY))
        state = play(state, H.NARROW_GYM)
        done = declare(state, 0)
        self.assertIsNone(done.stadium)
        self.assertEqual([(e["player"], e["reason"]) for e in new_events(state, done, "stadium_discarded")], [(0, "attack")])
        self.assertEqual([done.cards[p.card].card_id for p in done.players[0].bench], [H.CLEFAIRY_DOLL])  # 場のピッピ人形はトレーナーカードとしてあつかわない
        audited(self, done)

    def test_fossil_is_zc3(self):
        state = board(mon(POLYGON, (W,)), bench=(H.MYSTERIOUS_FOSSIL,), opponent=mon(H.CHANSEY))
        rejects(self, state, UseAttack(0, 0), ZC3)

    def test_powers_off_while_used(self):
        """抑止のあいだは「とうめい」のコインを投げない（ゴースト）。かがくへんかガスも含めて止まり、ワザのあと（きぜつの判定の前）にもどる。"""
        haunter = mon(H.HAUNTER, played_turn=2, evolved_from=H.GASTLY, evolved_turn=4, markers=[MARKER_STICKY])
        state = board(mon(POLYGON, (W,)), opponent=haunter)
        done = declare(state, 0)
        self.assertEqual(new_events(state, done, "coin_flip"), [])
        self.assertEqual(done.players[1].active.markers, ())
        audited(self, done)

    def test_transform_source_is_zc2(self):
        ditto = mon(H.DITTO, (W,))
        state = board(ditto, opponent=mon(POLYGON))
        rejects(self, state, UseAttack(0, 0), ZC2)

    def test_type_shift_or_lasting_goop_is_zc1(self):
        state = board(mon(POLYGON, (W,)), bench=(H.CHANSEY,), opponent=mon(H.CHANSEY), hand=(H.GOOP_GAS_ATTACK,))
        gassed = play(state, H.GOOP_GAS_ATTACK)
        rejects(self, gassed, UseAttack(0, 0), ZC1)


class AllClearBoundaryTest(unittest.TestCase):
    def test_stadium_hp_drop_is_the_knock_out_check(self):
        """ロケット団のアジト（わるいポケモンの最大HP + 20）をトラッシュして最大HP がのっているダメージ以下になったら、ワザのあとのきぜつの判定がきぜつにする（v0.81 と同じ。MH1 で止めない）。"""
        hideout = "neo3-057"
        dark = mon(H.DARK_RATICATE, played_turn=2, evolved_from=H.RATTATA, evolved_turn=4, damage=60)  # HP 50 + 20
        state = play(board(mon(POLYGON, (W,)), hand=(hideout,), opponent=dark, opponent_bench=(H.RATTATA,)), hideout)
        done = declare(state, 0)
        self.assertEqual([(e["player"], done.cards[e["pokemon"]].card_id) for e in new_events(state, done, "knock_out")], [(1, H.DARK_RATICATE)])
        audited(self, done)

    def test_barrier_keeps_everything_on_that_pokemon(self):
        """「ワザをうけない」状態（バリアー）のポケモンには、どの効果も届かない（``reaches``）。"""
        from kyuura_engine.state import AttackBarrier

        state = board(mon(POLYGON, (W,)), opponent=mon(H.CHANSEY, markers=[MARKER_CHAR], trainers=[(H.DEFENDER, TURN)]))
        target = state.players[1].active
        target.persistent_effects = (AttackBarrier(target.card, 1, TURN - 1, TURN),)
        saved, state.turn_number = state.turn_number, TURN - 1
        state.add_event("persistent_effect_added", player=1, pokemon=target.card, pokemon_id=target.pokemon_id, persistent_effect="attack_barrier",
                        source_card=target.card, source_player=1, active_turn=TURN, effect="test")
        state.turn_number = saved
        done = declare(state, 0)
        self.assertEqual([e["element"] for e in new_events(state, done, "effect_prevented")], [E.TRAINER_DISCARD_ELEMENT, E.CURE_ELEMENT, E.MARKER_ELEMENT])
        self.assertEqual([e["reason"] for e in new_events(state, done, "discard_attached_trainer")], ["end_of_turn"])  # ワザではトラッシュしない（番の終わりの期限）
        self.assertEqual([e["reason"] for e in new_events(state, done, "persistent_effect_removed")], ["expired"])
        self.assertEqual(marks(done.players[1].active), [(MARKER_CHAR, None)])


class CharBoundaryTest(unittest.TestCase):
    def test_scram_passing_ten_is_sc1_before_coins(self):
        primeape = mon(H.BROCKS_PRIMEAPE, played_turn=2, evolved_from="PMCG5-045", evolved_turn=4, damage=40, poison=10, markers=[MARKER_CHAR])  # 残り 30
        state = board(mon(H.CHANSEY), opponent=primeape)
        done = end_turn(state)
        self.assertEqual((done.phase, done.halt.code), (Phase.HALTED, SC1))  # 「うら」なら 20 で残り 10、どくで 0
        self.assertEqual(new_events(state, done, "coin_flip"), [])

    def test_mid_check_knock_out_changes_the_poison_step_pk1(self):
        """くろこげマーカーで 1 のあいだに HP 以上になったかがくへんかガスのベトベトンが、2 の前に場をはなれるかで、どく状態の［ずらかる］が変わる（PK1）。コインの前に止める。"""
        from tests.test_type_energy_colors_v0_88 import muk

        gas = muk()
        gas.update(damage=60, markers=[MARKER_CHAR])  # HP 70
        primeape = mon(H.BROCKS_PRIMEAPE, played_turn=2, evolved_from="PMCG5-045", evolved_turn=4, damage=50, poison=10)  # どくで残り 10
        state = board(mon(H.CHANSEY), opponent=primeape, opponent_bench=(gas,))
        done = end_turn(state)
        self.assertEqual((done.phase, done.halt.code), (Phase.HALTED, "UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT"))
        self.assertEqual(new_events(state, done, "coin_flip"), [])


class HiddenCardTest(unittest.TestCase):
    def setUp(self):
        from tests import test_secret_plan_v0_67 as SP

        self.SP = SP

    def test_all_clear_does_not_reveal_face_down(self):
        """全体にはたらく効果なので、うらのカードはおもてにしない（たねポケモンとしてあつかわれ、トレーナーカードとしてトラッシュしない。本当のカードを読まない）。"""
        from kyuura_engine.observation import visible_log

        views = []
        for hidden in (H.PLUSPOWER, H.RATTATA):
            state = self.SP.opponent_turn(self.SP.place(self.SP.board(hand=(hidden,), opponent={"card": POLYGON, "energy": [W]}, turn_number=5), hidden))
            done = apply_kernel(state, UseAttack(1, 0))
            self.assertEqual(len(self.SP.face_down(done)), 1)
            self.assertNotIn("secret_plan_revealed", [e["kind"] for e in done.log])
            views.append(visible_log(done, 1)[len(state.log):])
            audited(self, done)
        self.assertEqual(views[0], views[1])  # 相手の見るログは本当のカードによらない

    def test_lightning_rod_reveals_the_chosen_face_down(self):
        for hidden, kept in ((H.RATTATA, True), (H.PLUSPOWER, False)):
            with self.subTest(hidden=hidden):
                state = self.SP.opponent_turn(self.SP.place(self.SP.board(hand=(hidden,), opponent={"card": ELECTABUZZ, "energy": [L]}, turn_number=5), hidden))
                pid = self.SP.face_down(state)[0].pokemon_id
                asking = apply_kernel(state, UseAttack(1, 0))
                self.assertIn(pid, asking.decision.options)
                done = answer(asking, (pid,))
                self.assertEqual([e["cause"] for e in done.log if e["kind"] == "secret_plan_revealed"], [E.MARKER_ELEMENT])  # 効果の要素の種類
                found = done.players[0].find_by_pokemon_id(pid)
                self.assertEqual(found is not None, kept)
                if kept:
                    self.assertEqual(marks(found), [(MARKER_LIGHTNING_ROD, None)])
                audited(self, done)


class CopyTest(unittest.TestCase):
    """ピッピの「ゆびをふる」でまねても内部エラーにしない（まねたポケモンのワザとして処理する）。"""

    def test_metronome_copies(self):
        cases = [
            (mon(POLYGON, (W,), markers=[MARKER_STICKY]), 0),
            (mon(QUILAVA, played_turn=2, evolved_from=CYNDAQUIL, evolved_turn=4), 1),
            (mon(ELECTABUZZ, markers=[MARKER_LIGHTNING_ROD]), 1),
            (mon(ELECTABUZZ), 0),
        ]
        for opponent, index in cases:
            with self.subTest(opponent=opponent["card"], index=index):
                state = board(mon(H.CLEFAIRY, (W, W, W), markers=[MARKER_LIGHTNING_ROD]), opponent=opponent)
                selecting = declare(state, 1, HD, HD, HD)
                self.assertEqual(selecting.decision.kind, "select_attack")
                done = answer(selecting, (index,))
                while done.decision is not None and done.decision.kind == SELECT_POKEMON and done.decision.player == 0:
                    done = answer(done, (done.decision.options[0],))
                audited(self, done)


class DecisionPersistenceTest(unittest.TestCase):
    def test_lightning_rod_choice_survives_copy_and_rejects_bad_answers(self):
        state = board(mon(ELECTABUZZ, (L,)), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA,))
        asking = declare(state, 0)
        with self.assertRaises(IllegalActionError):
            apply_kernel(asking, ResolveDecision(0, asking.decision.id, (asking.players[0].active.pokemon_id,)))
        bench = asking.players[1].bench[0].pokemon_id
        outcomes = {tuple(marks(answer(restored, (bench,)).players[1].bench[0])) for restored in (copy.deepcopy(asking), pickle.loads(pickle.dumps(asking)), asking.clone())}
        self.assertEqual(outcomes, {((MARKER_LIGHTNING_ROD, None),)})
        self.assertTrue(state_to_dict(asking, format_version=24)["decision"])


class SuppressionPeriodTest(unittest.TestCase):
    def test_suppression_includes_chemical_gas_itself(self):
        from kyuura_engine.continuous import power_suppressed
        from kyuura_engine.state import TrainerTurnEffect
        from tests.test_type_energy_colors_v0_88 import muk

        state = board(mon(POLYGON, (W,)), opponent=muk())
        gas = state.players[1].active
        power = state.card_def(gas.card).powers[0]
        self.assertFalse(power_suppressed(state, power, gas))
        state.trainer_effects += (TrainerTurnEffect(kind=ATTACK_POWER_SUPPRESSION, player=0, source_card=state.players[0].active.card, card_id=POLYGON,
                                                    created_turn=TURN, expires_turn=TURN, attack_index=0),)
        self.assertTrue(power_suppressed(state, power, gas))  # かがくへんかガスも除かない（「すべてのポケモン」）

    def test_max_hp_and_form_return_before_the_knock_out_check(self):
        """［ガスのからだ］（最大HP + 超エネルギーカード × 10）は抑止のあいだ消えるが、きぜつの判定は抑止が終わったあと（最大HP はもどる）。［へんしん］の姿も、ワザのあとはもどる。"""
        gastly = mon("PMCG6-049", (P, P), damage=50, played_turn=2)  # ナツメのゴース
        state = board(mon(POLYGON, (W,)), opponent=gastly, opponent_bench=(H.RATTATA,))
        hp = E.max_hp(state, state.players[1].active)
        done = declare(state, 0)
        self.assertEqual(new_events(state, done, "knock_out"), [])
        self.assertEqual(E.max_hp(done, done.players[1].active), hp)
        audited(self, done)
        ditto = board(mon(POLYGON, (W,)), opponent=mon(H.DITTO, (W,), damage=30, played_turn=2))
        self.assertEqual(E.current_form(ditto, ditto.players[1].active).kind, "transform")
        after = declare(ditto, 0)
        self.assertEqual(E.current_form(after, after.players[1].active).kind, "transform")
        self.assertEqual(after.players[1].active.damage, 30)
        audited(self, after)

    def test_sleeping_gas_is_cured_and_works_after_the_attack(self):
        """回復させたベトベトン（ねむり）のかがくへんかガスは、抑止のあいだは消え、ワザのあとにはたらく（ワザのあとの場で、ほかの特殊能力が消える）。"""
        from kyuura_engine.continuous import working_power_suppressors
        from tests.test_type_energy_colors_v0_88 import muk

        gas = muk()
        gas.update(sleep=True)
        state = board(mon(POLYGON, (W,)), opponent=gas)
        self.assertEqual(working_power_suppressors(state), ())
        done = declare(state, 0)
        self.assertEqual(working_power_suppressors(done), (done.players[1].active.pokemon_id,))
        audited(self, done)


class CharDarknessTest(unittest.TestCase):
    def test_darkness_energy_and_char_both_apply(self):
        """悪エネルギーの効果とくろこげマーカーのダメージは、どちらもほかの効果の対象・量を変えないので、順番で結果が変わらなければ止めずに両方を処理する（悪エネルギーが先）。"""
        state = board(mon(H.CHANSEY), opponent=mon(H.CHANSEY, (H.DARKNESS_ENERGY_NEO1,), markers=[MARKER_CHAR]))
        done = end_turn(state, TL)
        kinds = kinds_since(state, done)
        self.assertLess(kinds.index("darkness_energy_damage"), kinds.index("char_damage"))
        self.assertEqual(done.players[1].active.damage, 10 + 20)
        audited(self, done)


class DocumentTest(unittest.TestCase):
    def test_document_lists_cards_codes_and_counts(self):
        text = DOC.read_text(encoding="utf-8")
        for card in H.V0_91_CARDS:
            self.assertIn(card, text)
        for key in V091_ATTACKS:
            self.assertIn(DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).name_ja, text)
        for code in (KK1, HR1, HX1, ZC1, ZC2, ZC3, "KK1", "HR1", "HX1", "ZC1", "ZC2", "ZC3", "1,119", "1,373", "258"):
            self.assertIn(code, text)

    def test_no_card_id_branches_in_engine_or_resolution(self):
        texts = [(ROOT / "kyuura_engine" / "engine.py").read_text(encoding="utf-8"), (ROOT / "kyuura_engine" / "procedures.py").read_text(encoding="utf-8")]
        texts += [p.read_text(encoding="utf-8") for p in (ROOT / "kyuura_engine" / "resolution").glob("*.py")]
        for card_id in H.V0_91_CARDS:
            self.assertFalse(any(card_id in text for text in texts), card_id)

    def test_v0_90_document_states_what_the_mutant_check_does(self):
        text = (ROOT / "docs" / "markers-counters-v0.90.md").read_text(encoding="utf-8")
        self.assertNotIn("証人のテストが見つけました", text)
        self.assertIn("定義の適用検査", text)

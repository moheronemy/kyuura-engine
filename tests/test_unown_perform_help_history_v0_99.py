"""v0.99（docs/unown-perform-help-history-v0.99.md）: アンノーンP・H とタッツーの 3 枚（ワザ 3・特殊能力 2）と、受けたダメージの場所の履歴。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面・ルール文。3 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録
（v0.62 の履歴・v0.46 の常にはたらく特殊能力の 2 段階・v0.27 の「つるぎのまい」のこんらんの分類・v0.54 の HD2・v0.96 の名前のグループ・v0.97 のベンチの文字・v0.67 の FD1）。
英語版の文面・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。
盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.99``）。
受けた記録は、盤面の前の番（相手の番）に実際にワザを使って作る（記録を手で作るのは、今の写しで起こらない境界・前の版の記録の写しの確かめだけ）。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import pickle
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    EndTurn,
    PlayTrainer,
    PowerKey,
    ResolveDecision,
    Retreat,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.continuous import power_suppressed
from kyuura_engine.deck import deck_problems
from kyuura_engine.errors import (
    HiddenPropertyRead,
    IllegalActionError,
    UnsupportedError,
)
from kyuura_engine.history import (
    DAMAGE_PLACE_UNKNOWN_CODE,
    damage_places,
    history_needed,
    received_on,
)
from kyuura_engine.observation import observe
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import AttackReceived
from tests import helpers as H
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.release_catalog import cards_after, cards_before
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_power_suppression_lasting_locks_v0_92 import mon, uid
from tests.test_unown_family_powers_v0_96 import board, deck_of, kinds
from tests.test_unown_idfnj_powers_v0_97 import snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "unown-perform-help-history-v0.99.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, PS, G, F = H.WATER, H.PSYCHIC, H.GRASS, H.FIRE
UP, UH, HORSEA = "neo4-058", "neo4-063", "neo1-023"
UE, UL, UI = H.UNOWN_E, H.UNOWN_L, "neo2-023"
V099 = (UP, UH, HORSEA)
V099_ATTACKS = [AttackKey(c, 0) for c in V099]
V099_POWERS = [PowerKey(UP, 0), PowerKey(UH, 0)]
PFM1, FD1 = "UNRESOLVED_PERFORM_DAMAGE_PLACES", "UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY"
RULE_TEXT = "「アンノーン」はデッキに4枚までしか入れることができません。"
# 依頼で示された固定データの日本語（写しの文面と照らす。広い正規化をしない）
QUOTED = {
    UP: ("この力は、このカードが「めざめるパワー」を使うとき、はたらく。前の相手の番、このカードが、バトル場で相手のワザによるダメージを受けていたなら、その受けたダメージと同じダメージを、"
         "このカードが使う「めざめるパワー」のダメージに追加する。"),
    UH: ("この力は、自分のベンチに、このカードとアンノーン「E」「L」「P」がいるとき、自分の番ごとに1回使うことができる。自分の手札の枚数を数え、それらをすべて山札にもどし、その山札を"
         "よく切る。その後、その山札から、もどした枚数ぶんのカードを引いて、手札にする。"),
}
FIN_SLAP = "前の相手の番、このカードがワザによるダメージを受けていたなら、10ダメージを追加する。"
NAMES = {UP: "PERFORM[パフォーム]", UH: "HELP[ヘルプ]"}
TURN = 7
GOLBAT = mon(H.BROCKS_GOLBAT, (W, W, W), evolved_from=H.BROCKS_ZUBAT)  # かいてんひこう（無無無）: 相手と相手の控え全員に 10（弱点・抵抗力なし）


def attack(state, index=0, *coins, player=None):
    player = state.current_player if player is None else player
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UseAttack(player, index))


def pid(state, card_id, player=0):
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card_id)


def pokemon(state, card_id, player=0):
    return state.find_pokemon(pid(state, card_id, player))[1]


def damages(before, after):
    """ダメージのログの (受けたポケモンの番号, 量, 段階の記録)。"""
    return [(e.get("pokemon_id", None), e["amount"], tuple(tuple(s) for s in e["steps"])) for e in new_events(before, after, "damage")]


def hit(me_active, *, bench=(H.RATTATA,), attacker=None, index=0, coins=()):
    """前の番（6 番。相手の番）に相手が ``attacker`` でワザを使い、7 番（自分の番）になった盤面。"""
    state = board(me_active, bench=bench, opponent=attacker or mon(HORSEA, (W, W)), current=1, turn=TURN - 1)
    done = attack(state, index, *coins)
    assert done.current_player == 0 and done.turn_number == TURN and done.decision is None, (done.current_player, done.turn_number, done.decision)
    return done


def record(state, card_id):
    return received_on(pokemon(state, card_id), TURN - 1)


# ---------------------------------------------------------------- 1〜2 章: 対象・登録・文面・デッキの規定


class RegistrationTest(unittest.TestCase):
    def test_every_attack_and_power_is_registered_with_the_printed_text(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_99"]), V099)
        for card in (UP, UH):
            with self.subTest(card=card):
                entry = DEFAULT_EFFECTS.attack_entry(card, 0)
                printed = pool.definitions[card].attacks[0]
                self.assertIs(entry.effect, E.DAMAGE_ONLY)
                self.assertEqual((entry.name_ja, printed.name_ja, printed.text_ja, entry.text_ja, printed.damage, tuple(t.value for t in printed.cost)),
                                 ("めざめるパワー", "めざめるパワー", None, None, 10, ("psychic",)))
                power = DEFAULT_EFFECTS.power_entry(card, 0)
                printed_power = pool.definitions[card].powers[0]
                self.assertEqual((printed_power.name_ja, printed_power.text_ja), (NAMES[card], QUOTED[card]))
                self.assertEqual((power.name_ja, power.text_ja, power.play_text_ja, power.source),
                                 (printed_power.name_ja, printed_power.text_ja, printed_power.text_ja, "kyuura data/cards.json"))
                self.assertEqual(power.effect.check(printed_power), [])
                definition = pool.definitions[card]
                self.assertEqual((definition.stage, definition.hp, definition.pokemon_type, definition.weakness, definition.resistance, definition.retreat_cost),
                                 ("basic", 40, E.EnergyType.PSYCHIC, E.EnergyType.PSYCHIC, None, 1))
                self.assertEqual((definition.name_group, definition.deck_group_limit, definition.name_letter), ("アンノーン", 4, card[-1:] and {UP: "P", UH: "H"}[card]))
        entry = DEFAULT_EFFECTS.attack_entry(HORSEA, 0)
        printed = pool.definitions[HORSEA].attacks[0]
        self.assertEqual(entry.effect, E.PlusIfDamagedByAttackLastOpponentTurn(10))
        self.assertEqual((printed.name_ja, printed.text_ja, printed.damage, printed.damage_modifier, tuple(t.value for t in printed.cost)),
                         ("ひれがえし", FIN_SLAP, 20, "+", ("water", "water")))
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), ("ひれがえし", FIN_SLAP, FIN_SLAP, "kyuura data/cards.json"))
        self.assertIsNone(DEFAULT_EFFECTS.attack_problem(HORSEA, printed, pool.definitions[HORSEA].attacks))
        horsea = pool.definitions[HORSEA]
        self.assertEqual((horsea.stage, horsea.hp, horsea.pokemon_type, horsea.weakness, horsea.resistance, horsea.retreat_cost, horsea.name_group),
                         ("basic", 50, E.EnergyType.WATER, E.EnergyType.LIGHTNING, None, 0, None))
        for card in V099:
            self.assertIn(card, pool.playable_ids)

    def test_texts_are_not_normalized(self):
        """引用と 1 字ずつ同じ文面だけを受け付ける（ワザの名前・文字・数・回数の書き方を変えた文面は受け付けない）。"""
        pool = load_card_pool()
        perform = pool.definitions[UP].powers[0]
        help_ = pool.definitions[UH].powers[0]
        for effect, printed, changed in (
            (DEFAULT_EFFECTS.power_entry(UP, 0).effect, perform, perform.text_ja.replace("めざめるパワー", "サイコキネシス")),
            (DEFAULT_EFFECTS.power_entry(UP, 0).effect, perform, perform.text_ja.replace("バトル場で", "")),
            (DEFAULT_EFFECTS.power_entry(UH, 0).effect, help_, help_.text_ja.replace("「E」「L」「P」", "「E」「L」「I」")),
            (DEFAULT_EFFECTS.power_entry(UH, 0).effect, help_, help_.text_ja.replace("「E」", "｢E｣")),
            (DEFAULT_EFFECTS.power_entry(UH, 0).effect, help_, help_.text_ja.replace("1回", "一回")),
        ):
            with self.subTest(changed=changed):
                self.assertNotEqual(effect.check(dataclasses.replace(printed, text_ja=changed)), [])
        self.assertNotEqual(DEFAULT_EFFECTS.power_entry(UP, 0).effect.check(help_), [])
        fin = pool.definitions[HORSEA].attacks[0]
        self.assertNotEqual(E.PlusIfDamagedByAttackLastOpponentTurn(10).check(dataclasses.replace(fin, text_ja=fin.text_ja.replace("ワザによる", "相手のワザによる"))), [])
        self.assertNotEqual(E.PlusIfDamagedByAttackLastOpponentTurn(20).check(fin), [])

    def test_types(self):
        perform = DEFAULT_EFFECTS.power_entry(UP, 0).effect
        help_ = DEFAULT_EFFECTS.power_entry(UH, 0).effect
        self.assertEqual(perform, E.AddActiveDamageReceivedToNamedAttack("めざめるパワー"))
        self.assertIsInstance(perform, E.ContinuousPower)
        self.assertEqual((perform.declared, perform.once_per_turn, perform.blocked_by_status, perform.reads_history, perform.location),
                         (False, False, False, True, E.CONTINUOUS_IN_PLAY))  # 宣言しない・回数の制限なし・文面にない特殊状態の禁止を加えない
        self.assertEqual((help_.letters, help_.group), (("E", "L", "P"), "アンノーン"))
        self.assertEqual((help_.declared, help_.once_per_turn, help_.reads_history), (True, True, False))
        self.assertTrue(E.PlusIfDamagedByAttackLastOpponentTurn.reads_history)

    def test_unregistered_without_the_v0_99_entries(self):
        """今回の登録を除くと対戦に使えなくなるのは、ちょうど 3 枚。過去の範囲は ``cards_before``・``cards_after`` で切り出す。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V099_ATTACKS)
        registry = registry.without_powers(registry.id, V099_POWERS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V099))
        self.assertEqual(set(V099) & set(cards_before(read_extract(), "0.99")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.98")) & set(cards_before(read_extract(), "0.100")), set(V099))

    def test_extract_values(self):
        cards = {c["id"]: c for c in read_extract()["cards"]}
        for card in (UP, UH):
            self.assertEqual(cards[card]["pokemon"]["rules_text"]["ja"], RULE_TEXT)
            self.assertEqual(cards[card]["pokemon"]["attacks"][0]["text"]["ja"], None)  # 説明文のないワザ（文面の出典を作らない）
        self.assertIsNone(cards[HORSEA]["pokemon"]["rules_text"])
        for card in V099:
            self.assertNotIn("corrections", cards[card])
        self.assertEqual({c: cards[c]["jp_print"]["level"] for c in V099}, {UP: 13, UH: 16, HORSEA: 22})
        self.assertEqual(read_extract()["source"]["commit"], "73a169063463bbf7bcaa3137d70cbf9721d11534")  # 写しの元は v0.97 のまま

    def test_adoption_records_and_research_links(self):
        data = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        for card, part in ((UP, "power/0"), (UH, "power/0"), (HORSEA, "attack/0")):
            with self.subTest(card=card):
                item = data[card]
                self.assertEqual((item["basis"], item["status"], item["kyuura_commit"], item["recorded_on"], item["external_checks"], item["issues"],
                                  item["kyuura_records"], item["play_text"]),
                                 ("kyuura_data", "adopted", "73a169063463bbf7bcaa3137d70cbf9721d11534", "2026-10-25", [], [], [], {part: "kyuura_printed_text"}))
        for card in (UP, UH):
            self.assertIn("このカードを直接確かめた記録ではない", data[card]["notes"])  # デッキの規定は共通の規定の再利用
        self.assertIn("後年の分類で、2000.02.14 版の規定としては使わない", data[UP]["notes"])  # rule_history.json の poke_body の一覧
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        self.assertEqual([k for k in links["latest_descriptions"]["adopted_printed_text"] if k.split("/")[0] in V099],
                         [f"{UP}/power/0", f"{UH}/power/0", f"{HORSEA}/attack/0"])
        entry = links["stop_codes"][PFM1]
        self.assertEqual((entry["kyuura_issue"], entry["kyuura_disposition"], [r["ruling_id"] for r in entry["engine_rulings"]]), (None, "not_in_kyuura", ["PFM1"]))
        self.assertEqual([c for c in links["kyuura_cases_without_engine_ruling"]["cases"] if c["card_id"] in V099], [])


class DeckLimitTest(unittest.TestCase):
    """文字にかかわらず、デッキのアンノーンは合わせて 4 枚まで（v0.96 の ``deck_problems``。共通の規定の再利用）。タッツーは名前のグループを持たない。"""

    def test_mixed_letters(self):
        self.assertEqual(deck_problems(deck_of(UH, UE, UL, UP, HORSEA, HORSEA, HORSEA, HORSEA)), [])  # ［HELP］の 4 文字
        self.assertTrue(any(p.startswith("TOO_MANY_GROUP_COPIES") for p in deck_problems(deck_of(UH, UE, UL, UP, UI))))
        self.assertIn("TOO_MANY_COPIES: 「アンノーンP」が 5 枚（同じ名前は 4 枚まで）", deck_problems(deck_of(*([UP] * 5))))
        self.assertIn("TOO_MANY_COPIES: 「タッツー」が 5 枚（同じ名前は 4 枚まで）", deck_problems(deck_of(*([HORSEA] * 5))))


# ---------------------------------------------------------------- 3 章: 受けたダメージの場所の履歴（共通の処理）


class DamagePlaceHistoryTest(unittest.TestCase):
    def test_history_is_needed_when_only_a_power_reads_it(self):
        """［PERFORM］だけが履歴を読む対戦でも記録する。履歴を読む効果のない対戦（H だけ）では記録しない（v0.98 までと同じ状態）。"""
        only_power = board(mon(UP, (PS,)), opponent=mon(H.RATTATA, (G,)))
        self.assertTrue(history_needed(only_power))
        self.assertFalse(any(getattr(DEFAULT_EFFECTS.attack_entry(d.id, a.index).effect, "reads_history", False)
                             for d in only_power.definitions.values() for a in d.attacks if DEFAULT_EFFECTS.attack_entry(d.id, a.index) is not None))
        without = board(mon(UH, (PS,)), opponent=mon(H.RATTATA, (G,)))
        self.assertFalse(history_needed(without))
        quiet = attack(board(mon(UH, (PS,)), opponent=mon(H.RATTATA, (G,)), current=1, turn=TURN - 1))
        self.assertTrue(all(not p.history for side in quiet.players for p in side.in_play()))
        self.assertIsInstance(state_to_dict(quiet, 20), dict)  # 記録がないので、前の形式でも書き出せる
        recorded = attack(board(mon(UP, (PS,)), opponent=mon(H.RATTATA, (G,)), current=1, turn=TURN - 1))
        self.assertEqual(record(recorded, UP).active_damage, record(recorded, UP).damage)

    def test_place_is_the_place_when_the_damage_was_placed(self):
        """かいてんひこう（相手と相手の控え全員に 10）: バトル場のポケモンはバトル場で、控えはベンチで受けた（合計とは別に、受けた時の場所で分ける）。"""
        state = hit(mon(H.RATTATA), bench=(mon(UP, (PS,)), mon(HORSEA, (W, W))), attacker=GOLBAT, index=1)
        self.assertEqual([damage_places(received_on(p, TURN - 1)) for p in state.players[0].in_play()], [(10, 0), (0, 10), (0, 10)])
        self.assertEqual([received_on(p, TURN - 1).damage for p in state.players[0].in_play()], [10, 10, 10])
        audited(self, state)

    def test_heal_and_moves_do_not_change_the_record(self):
        """受けた量はのせた最終ダメージ。あとで回復しても減らさない・入れ替えても場所を書きかえない（今の場所・今のダメージから逆算しない）。"""
        with_potion = board(mon(UP, (PS,)), bench=(mon(H.RATTATA),), hand=(H.POTION,), opponent=mon(HORSEA, (W, W)), current=1, turn=TURN - 1)
        taken = attack(with_potion)
        potion = apply_kernel(taken, PlayTrainer(0, uid(taken, H.POTION)))
        if potion.decision is not None:
            potion = apply_kernel(potion, ResolveDecision(0, potion.decision.id, (pid(potion, UP),)))
        self.assertEqual(pokemon(potion, UP).damage, 0)
        self.assertEqual(record(potion, UP), record(taken, UP))
        self.assertEqual(damage_places(record(potion, UP)), (20, 0))
        moved = apply_kernel(taken, Retreat(0, (pokemon(taken, UP).energy[0],), pokemon(taken, H.RATTATA).card))
        self.assertIs(moved.players[0].active, moved.find_pokemon(pid(taken, H.RATTATA))[1])
        self.assertEqual(damage_places(record(moved, UP)), (20, 0))  # ベンチにもどっても、バトル場で受けた事実は消えない
        audited(self, moved)

    def test_zero_final_damage_is_recorded_but_not_received(self):
        """ディフェンダー（-20）で最終ダメージ 0: 受けた要素としては記録する（v0.62）が、0 は「受けなかった」（p.319）。"""
        state = hit(mon(UP, (PS,), trainers=[(H.DEFENDER, TURN - 1)]))
        self.assertEqual((record(state, UP).damage, record(state, UP).reached, damage_places(record(state, UP))), (0, ("damage",), (0, 0)))

    def test_records_without_a_place_are_not_guessed(self):
        """場所の分からない記録（v0.98 までの記録の写し。``active_damage`` が None）は、合計をバトル場の分・0 にしない（エンジンの情報の不足）。合計 0 なら (0, 0)。"""
        old = AttackReceived(TURN - 1, 0, 1, 9, (HORSEA, 0), (HORSEA, 0), damage=20, reached=("damage",))
        self.assertIsNone(old.active_damage)
        with self.assertRaises(UnsupportedError) as caught:
            damage_places(old)
        self.assertEqual(caught.exception.code, DAMAGE_PLACE_UNKNOWN_CODE)
        self.assertEqual(damage_places(dataclasses.replace(old, damage=0)), (0, 0))
        self.assertEqual(damage_places(dataclasses.replace(old, active_damage=0)), (0, 20))

    def test_serialization_formats(self):
        """形式 25 は受けた記録に場所（``active_damage``）を書く。形式 20〜24 は、場所の分かる 0 より大きいダメージの記録があると書き出さない（合計 0・場所の分からない記録だけなら書ける）。"""
        state = hit(mon(UP, (PS,)))
        latest = state_to_dict(state, 25)
        self.assertIn(25, FORMAT_VERSIONS)  # 今の最新の形式は tests/test_catalog_contract.py（docs/testing.md）
        received = [r for r in latest["players"][0]["active"]["history"] if r["kind"] == "received"]
        self.assertEqual([(r["damage"], r["active_damage"]) for r in received], [(20, 20)])
        for version in (20, 24):
            with self.subTest(version=version), self.assertRaises(ValueError):
                state_to_dict(state, version)

        def received_of(data):
            return next(r for r in data["players"][0]["active"]["history"] if r["kind"] == "received")

        zero = hit(mon(UP, (PS,), trainers=[(H.DEFENDER, TURN - 1)]))
        written = received_of(state_to_dict(zero, 24))
        self.assertEqual(written["damage"], 0)
        self.assertNotIn("active_damage", written)
        unknown = state.clone()
        target = unknown.players[0].active
        target.history = tuple(dataclasses.replace(r, active_damage=None) if isinstance(r, AttackReceived) else r for r in target.history)
        self.assertEqual(received_of(state_to_dict(unknown, 24))["damage"], 20)
        self.assertIsNone(received_of(state_to_dict(unknown, 25))["active_damage"])
        for viewer in (0, 1, None):
            history = observe(state, viewer)["players"][0]["active"]["history"]
            self.assertEqual([(r["damage"], r["active_damage"]) for r in history if r["kind"] == "received"], [(20, 20)])  # 場の表の情報
        audited(self, state)
        audited(self, zero)

    def test_invariants_reject_impossible_places(self):
        from kyuura_engine.engine import _history_problems

        state = hit(mon(UP, (PS,)))
        broken = state.clone()
        target = broken.players[0].active
        target.history = tuple(dataclasses.replace(r, active_damage=30) if isinstance(r, AttackReceived) else r for r in target.history)
        self.assertTrue(any("バトル場で受けたダメージ" in p for p in _history_problems(broken)))
        self.assertEqual(_history_problems(state), [])

    def test_this_card_is_the_same_pokemon(self):
        """手札にもどして出し直したポケモンは別のポケモン（新しい番号。記録はない）。前の前の相手の番の記録は読まない（2 つ前の番までだけ残す）。"""
        state = hit(mon(UP, (PS,)))
        self.assertIsNone(received_on(pokemon(state, UP), TURN - 3))
        later = apply_kernel(apply_kernel(state, EndTurn(0)), EndTurn(1))  # 9 番: 前の相手の番（8 番）には受けていない
        self.assertEqual(later.turn_number, TURN + 2)
        self.assertIsNone(received_on(pokemon(later, UP), TURN + 1))
        self.assertEqual(damages(later, attack(later)), [(None, 10, (("1 基本となる計算", 10),))])


# ---------------------------------------------------------------- 4 章: ［PERFORM］・「ひれがえし」のダメージ


class BasicExamplesTest(unittest.TestCase):
    """基本例（実装前の文面の読み方の例。独立した新しい公式裁定の記録ではない）: 受傷なしならタッツー 20・P 10、バトル場で 20 受けていれば 30・30、ベンチでだけ受けていれば 30・10。"""

    def test_no_damage(self):
        for card, energy, expected in ((UP, (PS,), 10), (HORSEA, (W, W), 20)):
            with self.subTest(card=card):
                state = board(mon(card, energy), opponent=mon(HORSEA, (W, W)))
                self.assertEqual(damages(state, attack(state))[0][1], expected)

    def test_damage_received_in_the_active_spot(self):
        for card, energy in ((UP, (PS,)), (HORSEA, (W, W))):
            with self.subTest(card=card):
                state = hit(mon(card, energy))
                self.assertEqual(damage_places(record(state, card)), (20, 0))
                done = attack(state)
                self.assertEqual(damages(state, done)[0][1], 30)
                audited(self, done)
        state = hit(mon(UP, (PS,)))
        self.assertEqual(damages(state, attack(state))[0][2], (("1 基本となる計算", 10), ("2 アンノーンP［PERFORM[パフォーム]］", 30)))  # 2 段階
        horsea = hit(mon(HORSEA, (W, W)))
        self.assertEqual(damages(horsea, attack(horsea))[0][2], (("1 基本となる計算", 30),))  # ワザの基本となるダメージ（1 段階）

    def test_damage_received_only_on_the_bench(self):
        """ベンチでだけ受けた 10（かいてんひこう）: 自分の番に入れ替えてから使う。タッツーは追加し（場所を問わない）、P は追加しない。"""
        # 相手はタケシのゴルバット（弱点 超）: P は 10 × 2 = 20（追加していれば (10 + 10) × 2 = 40）、タッツーは 20 + 10 = 30
        for card, energy, expected in ((UP, (PS, PS), 20), (HORSEA, (W, W), 30)):
            with self.subTest(card=card):
                state = hit(mon(H.RATTATA), bench=(mon(card, energy),), attacker=GOLBAT, index=1)
                self.assertEqual(damage_places(record(state, card)), (0, 10))
                moved = apply_kernel(state, Retreat(0, (), pokemon(state, card).card))  # 入れ替える控えはカードの uid
                self.assertIs(moved.players[0].active, pokemon(moved, card))
                done = attack(moved)
                self.assertEqual(damages(moved, done)[0][1], expected)
                audited(self, done)

    def test_conditions_are_not_declaration_requirements(self):
        """条件を満たさなくても使える（ドリルホールの宣言の拒否にしない）。［PERFORM］は宣言しない（使うかを聞かない）。"""
        state = board(mon(UP, (PS,)), opponent=mon(HORSEA, (W, W)))
        self.assertIsNone(DEFAULT_EFFECTS.attack_entry(HORSEA, 0).effect.usage_problem(state, state.players[0].active))
        rejects(self, state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0), "POWER_NOT_DECLARABLE", error=IllegalActionError)
        rejects(self, state, UseAttack(0, 0, attack_power=True), "ATTACK_POWER_NOT_AVAILABLE", error=IllegalActionError)  # ワザといっしょに使う特殊能力（v0.88）ではない
        done = attack(state)
        self.assertEqual(new_events(state, done, "pokemon_power"), [])


class PerformTest(unittest.TestCase):
    def test_healed_damage_is_still_added(self):
        state = board(mon(UP, (PS,)), hand=(H.POTION,), opponent=mon(HORSEA, (W, W)), current=1, turn=TURN - 1)
        taken = attack(state)
        healed = apply_kernel(taken, PlayTrainer(0, uid(taken, H.POTION)))
        if healed.decision is not None:
            healed = apply_kernel(healed, ResolveDecision(0, healed.decision.id, (pid(healed, UP),)))
        self.assertEqual(pokemon(healed, UP).damage, 0)
        self.assertEqual(damages(healed, attack(healed))[0][1], 30)  # 残りHP・今のダメージで丸めない

    def test_zero_damage_is_not_added(self):
        for card, energy, expected in ((UP, (PS,), 10), (HORSEA, (W, W), 20)):
            with self.subTest(card=card):
                state = hit(mon(card, energy, trainers=[(H.DEFENDER, TURN - 1)]))
                self.assertEqual(damages(state, attack(state))[0][1], expected)

    def test_other_pokemon_do_not_get_the_bonus(self):
        """P が場にいるだけでは、ほかのポケモン（ほかのアンノーン・P のワザを借りたポケモン）のワザに加えない。"""
        other = hit(mon(UI, (PS,)), bench=(mon(UP),))
        self.assertEqual(damage_places(record(other, UI)), (20, 0))
        self.assertEqual(damages(other, attack(other))[0][1], 10)  # アンノーンI の「めざめるパワー」（このカードではない）
        # ゆびをふるで相手のバトル場の P の「めざめるパワー」を使う（P はバトル場で前の番に受けていない。受けていても P の力は使うポケモンのものではない）
        state = board(mon(H.CLEFAIRY, (W, W, W)), opponent=mon(UP, (PS,)), opponent_bench=(H.RATTATA,), current=0, turn=TURN)
        choosing = attack(state, 1)
        self.assertEqual(choosing.decision.kind, "select_attack")
        done = apply_kernel(choosing, ResolveDecision(0, choosing.decision.id, (choosing.decision.options[0],)))
        self.assertEqual(damages(choosing, done)[0][1], 10)

    def test_copied_fin_slap_reads_the_user(self):
        """ゆびをふるで相手のタッツーの「ひれがえし」を使うと、「このカード」は使うピッピ（印刷したタッツーの記録は読まない）。"""
        for label, me_hit, expected in (("ピッピが受けていた", True, 30), ("ピッピは受けていない", False, 20)):
            with self.subTest(label=label):
                if me_hit:
                    state = hit(mon(H.CLEFAIRY, (W, W, W)), attacker=mon(HORSEA, (W, W)))
                else:
                    state = board(mon(H.CLEFAIRY, (W, W, W)), opponent=mon(HORSEA, (W, W), damage=10))
                choosing = attack(state, 1)
                fin = choosing.decision.options[0]
                done = apply_kernel(choosing, ResolveDecision(0, choosing.decision.id, (fin,)))
                self.assertEqual(damages(choosing, done)[0][1], expected)

    def test_gas_at_damage_time_does_not_prevent_later_use(self):
        """受けた時にかがくへんかガスで P の力が消えていても記録する。使う時にガスがなければはたらく（文面にない受けた時の条件を加えない）。使う時にガスがあれば加えない。"""
        muk = mon(H.MUK, (G, G, G), evolved_from=H.GRIMER, damage=60, poison=10)
        state = board(mon(UP, (PS,)), opponent=muk, opponent_bench=(mon(HORSEA, (W, W)),), current=1, turn=TURN - 1)
        p = state.players[0].active
        self.assertTrue(power_suppressed(state, state.card_def(p.card).powers[0], p))  # 受ける時、P の力はガスで消えている
        hit_by_muk = attack(state, 0, TL)  # ヘドロこうげき 30（コインの「うら」でどくにしない）。番の終わりのポケモンチェックのどくでベトベトンはきぜつ
        while hit_by_muk.decision is not None:
            d = hit_by_muk.decision
            hit_by_muk = apply_kernel(hit_by_muk, ResolveDecision(d.player, d.id, d.options[:max(1, d.min_choices)]))
        self.assertEqual((hit_by_muk.turn_number, hit_by_muk.current_player), (TURN, 0))
        self.assertEqual(damage_places(record(hit_by_muk, UP)), (30, 0))
        self.assertEqual(hit_by_muk.cards[hit_by_muk.players[1].active.card].card_id, HORSEA)
        done = attack(hit_by_muk)
        self.assertEqual(damages(hit_by_muk, done)[0][1], 40)
        audited(self, done)
        still = board(mon(UP, (PS,)), opponent=mon(H.MUK, (G, G, G), evolved_from=H.GRIMER), opponent_bench=(mon(HORSEA, (W, W)),), current=1, turn=TURN - 1)
        hit_again = attack(still, 0, TL)
        self.assertEqual(damage_places(record(hit_again, UP)), (30, 0))
        self.assertEqual(damages(hit_again, attack(hit_again))[0][1], 20)  # 使う時にガスで消えている（ベトベトンの弱点 超で 10 × 2。消えていなければ (10 + 30) × 2）

    def test_confusion(self):
        """こんらんの P（文面に特殊状態の禁止はない）。「おもて」ならワザで加える。「うら」の 20 は「めざめるパワー」のダメージではない（もとのワザの内容に関わらない。止めない）。"""
        state = hit(mon(UP, (PS,)))
        confused = state.clone()
        from kyuura_engine.state import CONFUSED, SpecialConditions

        confused.players[0].active.conditions = SpecialConditions(exclusive=CONFUSED)
        heads = attack(confused, 0, HD)
        self.assertEqual(damages(confused, heads)[0][1], 30)
        tails = attack(confused, 0, TL)
        self.assertEqual(new_events(confused, tails, "damage"), [])
        self.assertEqual([e["amount"] for e in new_events(confused, tails, "confusion_damage")], [40])  # 20 に自分の弱点 超（p.322）。P の追加はない

    def test_damage_places_question_only_when_both_places(self):
        """同じ相手のワザで、バトル場とベンチの両方で受けていたら PFM1（今の写しでは起こらない。記録を手で作った盤面）。片方だけなら止めない。"""
        state = hit(mon(UP, (PS,)))
        mixed = state.clone()
        target = mixed.players[0].active
        target.history = tuple(dataclasses.replace(r, damage=30, active_damage=20) if isinstance(r, AttackReceived) else r for r in target.history)
        rejects(self, mixed, UseAttack(0, 0), PFM1)
        horsea = hit(mon(HORSEA, (W, W)))
        both = horsea.clone()
        both.players[0].active.history = tuple(dataclasses.replace(r, damage=30, active_damage=20) if isinstance(r, AttackReceived) else r
                                               for r in both.players[0].active.history)
        self.assertEqual(damages(both, attack(both))[0][1], 30)  # タッツーは場所を問わない

    def test_unknown_place_is_an_engine_limit(self):
        state = hit(mon(UP, (PS,)))
        unknown = state.clone()
        unknown.players[0].active.history = tuple(dataclasses.replace(r, active_damage=None) if isinstance(r, AttackReceived) else r
                                                  for r in unknown.players[0].active.history)
        rejects(self, unknown, UseAttack(0, 0), DAMAGE_PLACE_UNKNOWN_CODE)

    def test_step_2_is_before_weakness_and_copies_agree(self):
        """2 段階の追加は弱点（3 段階）の前: 弱点 超 のアンノーンI に (10 + 20) × 2 = 60（10 × 2 + 20 ではない）。同じ履歴の盤面を写して計算し直しても同じ結果。"""
        state = hit(mon(UP, (PS,)), attacker=mon(UI, (PS,)))
        self.assertEqual(damage_places(record(state, UP)), (20, 0))  # アンノーンI の 10 × 2（P の弱点 超）
        expected = attack(state)
        self.assertEqual(damages(state, expected)[0][1:], (60, (("1 基本となる計算", 10), ("2 アンノーンP［PERFORM[パフォーム]］", 30), ("3 弱点", 60))))
        for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(snap(attack(other)), snap(expected))
        audited(self, expected)

    def test_modifier_only_for_the_named_attack_held_by_this_card(self):
        state = hit(mon(UP, (PS,)), bench=(mon(UI),))
        p = state.players[0].active
        perform = DEFAULT_EFFECTS.power_entry(UP, 0).effect
        defender = state.players[1].active
        self.assertEqual(perform.attack_damage_modifiers(state, p, "P", p, defender, attack=None), ())  # こんらんの 20 の問い合わせ
        self.assertEqual(perform.attack_damage_modifiers(state, p, "P", defender, p, attack=AttackKey(HORSEA, 0)), ())  # 受ける側
        found = perform.attack_damage_modifiers(state, p, "P", p, defender, attack=AttackKey(UP, 0))
        self.assertEqual([(m.step, m.amount, m.operation) for m in found], [(2, 20, "add")])
        with self.assertRaises(RuntimeError):
            perform.attack_damage_modifiers(state, p, "P", p, defender, attack=AttackKey(UI, 0))  # 今持たない「めざめるパワー」（今の写しでは起こらない）


# ---------------------------------------------------------------- 5 章: ［HELP］


class HelpTest(unittest.TestCase):
    def help_board(self, *, active=None, bench=None, hand=(W, PS, F), deck=None, **kw):
        bench = bench if bench is not None else (mon(UH), mon(UE), mon(UL), mon(UP))
        return board(active or mon(H.RATTATA), bench=bench, hand=hand, deck=deck if deck is not None else [G] * 6, **kw)

    def test_returns_the_hand_then_draws_the_same_number(self):
        state = self.help_board()
        h = pid(state, UH)
        hand_before = list(state.players[0].hand)
        done = apply_kernel(state, UsePokemonPower(0, h, 0))
        self.assertEqual(kinds(state, done), ["pokemon_power", "hand_to_deck", "shuffle", "draw"])
        back, shuffled, drawn = new_events(state, done, "hand_to_deck", "shuffle", "draw")
        self.assertEqual((list(back["cards"]), back["power"], shuffled["power"], len(drawn["cards"])), (hand_before, f"{UH}@power0", f"{UH}@power0", 3))
        self.assertEqual((len(done.players[0].hand), len(done.players[0].deck)), (3, 6))
        self.assertEqual(done.players[1].hand, state.players[1].hand)  # 相手の手札は動かさない
        self.assertEqual(done.players[1].deck, state.players[1].deck)
        for viewer in (1, None):
            log = observe(done, viewer)
            self.assertIsNone(log["players"][0]["hand"]["cards"])
        audited(self, done)
        rejects(self, done, UsePokemonPower(0, h, 0), "POWER_ALREADY_USED", error=IllegalActionError)

    def test_empty_hand_shuffles_and_draws_zero(self):
        """手札 0 枚: 必ずもどす効果なので v0.54 の HD2 の読み方（もどすカードがなくても切る）。0 枚引き、回数を使う（EG1・PW2 を当てはめない）。"""
        state = self.help_board(hand=())
        h = pid(state, UH)
        done = apply_kernel(state, UsePokemonPower(0, h, 0))
        self.assertEqual(kinds(state, done), ["pokemon_power", "shuffle", "draw"])
        self.assertEqual(new_events(state, done, "draw")[0]["cards"], ())
        self.assertEqual((done.players[0].hand, len(done.players[0].deck)), ([], 6))
        audited(self, done)
        rejects(self, done, UsePokemonPower(0, h, 0), "POWER_ALREADY_USED", error=IllegalActionError)

    def test_conditions_use_this_card_and_the_letters_on_the_own_bench(self):
        active = self.help_board(active=mon(UH), bench=(mon(UE), mon(UL), mon(UP)))
        rejects(self, active, UsePokemonPower(0, active.players[0].active.pokemon_id, 0), "POKEMON_NOT_ON_BENCH", error=IllegalActionError)
        cases = {
            "P がバトル場": self.help_board(active=mon(UP), bench=(mon(UH), mon(UE), mon(UL))),
            "P が相手の場": self.help_board(bench=(mon(UH), mon(UE), mon(UL)), opponent_bench=(mon(UP),)),
            "L がいない（別の文字）": self.help_board(bench=(mon(UH), mon(UE), mon(UI), mon(UP))),
        }
        for label, state in cases.items():
            with self.subTest(label=label):
                rejects(self, state, UsePokemonPower(0, pid(state, UH), 0), "REQUIRED_BENCH_POKEMON_MISSING", error=IllegalActionError)

    def test_invalid_commands_change_nothing(self):
        state = self.help_board()
        h = pid(state, UH)
        rejects(self, state, UsePokemonPower(0, h, 0, target=pid(state, UE)), "POWER_CHOICE_NOT_USED", error=IllegalActionError)
        rejects(self, state, UsePokemonPower(1, h, 0), "NOT_YOUR_TURN", error=IllegalActionError)
        gas = self.help_board(opponent=mon(H.MUK, evolved_from=H.GRIMER))
        rejects(self, gas, UsePokemonPower(0, pid(gas, UH), 0), "POWER_SUPPRESSED", error=IllegalActionError)

    def test_status_of_the_active_does_not_matter_and_history_stays(self):
        """手札の入れ替えは場の P の受けた記録を変えない（ベンチの P。前の番に受けた記録が残る）。"""
        state = hit(mon(H.RATTATA), bench=(mon(UH), mon(UE), mon(UL), mon(UP)), attacker=GOLBAT, index=1)
        history = pokemon(state, UP).history
        done = apply_kernel(state, UsePokemonPower(0, pid(state, UH), 0))
        self.assertEqual(pokemon(done, UP).history, history)

    def test_face_down_bench_card_is_read_only_when_needed(self):
        from tests.test_secret_plan_v0_67 import place

        def secret(bench, hidden):
            return place(build_test_state([
                {"active": mon(H.RATTATA), "bench": list(bench), "hand": [H.LT_SURGES_SECRET_PLAN, hidden, W], "deck": [W, PS], "prizes": 6},
                {"active": mon(H.RATTATA), "deck": [W] * 10, "prizes": 6}], turn_number=TURN), hidden)

        missing = secret((mon(UH), mon(UE), mon(UL)), UP)
        rejects(self, missing, UsePokemonPower(0, pid(missing, UH), 0), FD1, error=HiddenPropertyRead)
        enough = secret((mon(UH), mon(UE), mon(UL), mon(UP)), H.RATTATA)
        self.assertEqual(kinds(enough, apply_kernel(enough, UsePokemonPower(0, pid(enough, UH), 0)))[:2], ["pokemon_power", "hand_to_deck"])


class DocumentTest(unittest.TestCase):
    def test_document_lists_the_cards_codes_and_unhit_boundaries(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in (*V099, *NAMES.values(), "ひれがえし", PFM1, DAMAGE_PLACE_UNKNOWN_CODE, "HD2", "EG1", "PW2", "FD1", "73a1690", "形式 25",
                       "対戦で一度も起こらなかったもの"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()

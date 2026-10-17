"""v0.48: 場のポケモンの今有効な最大HP・タイプ（色）・弱点・抵抗力を一か所で求める仕組みと、それを変える 7 枚（docs/effective-pokemon-properties-v0.48.md）。

7 枚: ポリゴン（第1弾。PMCG1-064。テクスチャー1・テクスチャー2）・ポリゴン（ロケット団。PMCG4-050。テクスチャー1・サイケこうせん）・モルフォン（PMCG2-015。
［へんしょく］・りんぷん）・ナツメのゴース（PMCG6-049。［ガスのからだ］・ガスでつつむ）・ナツメのゴースト（PMCG6-050。ナイトスピリッツ）・ナツメのゲンガー
（PMCG6-054。ダメージぞうふく・やみのこえ）・キョウのメタモン（PMCG6-072。きょだいか・はたく）。どれも kyuura データの採用（処理に使う文面は kyuura の印刷の文面。
採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合。ガイドブックは読んでいない。

根拠にした既存の記録: GR-2000-P321-DAMAGE-ORDER（弱点・抵抗力は 3・4 段階で、受けるポケモンの弱点・抵抗力とワザを使うポケモンのタイプで計算する）・
GR-2000-P322-PERSISTENT-EFFECTS（ワザによる持続する効果はベンチにもどる・進化・きぜつで消える）・GR-2000-P323-KNOCKOUT（ワザのあとのきぜつの判定）・
GR-2000-P320-COUNTER-MOVE（ダメージカウンターをのせることはダメージではない）・GR-2000-P309-ATTACK-PROCEDURE・p.310（進化）・p.311（特殊能力）・p.322（特殊状態）と、
エンジンの v0.4a（H1）・v0.8（かがくへんかガス）・v0.35（「おもて」の数でまとめる先読み）・v0.36（相手を山札にもどす）・v0.40（ReturnOpponentToDeck）・v0.42
（特殊能力の決定と再開）・v0.46（常にはたらく特殊能力）の記録。

新しい停止コードは 3 つ: VS1（``UNRESOLVED_SHIFT_COLOR_DURATION``）・PG1（``UNRESOLVED_CHANGE_ABSENT_WEAKNESS_RESISTANCE``）・MH1（``UNRESOLVED_MAX_HP_DROP``）。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest

from kyuura_engine import (
    EndTurn,
    EngineError,
    EvolvePokemon,
    Phase,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    check_invariants,
    max_hp,
    observe,
    resistance_of,
    state_to_dict,
    type_readings,
    weakness_of,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, pool_from_extract, read_extract
from kyuura_engine.decisions import SELECT_COLOR
from kyuura_engine.observation import PUBLIC_EVENTS
from kyuura_engine.resolution import PREFLIGHT_MODES, contract, programs, v013_checks
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import MaxHpSet, ResistanceChange, WeaknessChange
from scripts import check_card_sources as cs
from tests.helpers import (
    GIOVANNIS_NIDOKING,
    GIOVANNIS_NIDORAN_M,
    GIOVANNIS_NIDORINO,
    RATICATE,
    SABRINAS_ABRA,
    SABRINAS_KADABRA,
    ATTACK_TYPES_SINCE_V0_17,
    CHANSEY,
    CLEFABLE,
    CLEFAIRY,
    FIGHTING,
    FOSSIL_GOLDUCK,
    FOSSIL_PSYDUCK,
    GASTLY,
    GRASS,
    GRIMER,
    GUST,
    HAUNTER,
    HITMONCHAN,
    KOGAS_DITTO,
    MISTYS_PSYDUCK,
    MUK,
    PORYGON,
    PSYCHIC,
    RATTATA,
    ROCKET_PORYGON,
    SABRINAS_GASTLY,
    SABRINAS_GENGAR,
    SABRINAS_HAUNTER,
    SWITCH,
    V0_48_POKEMON,
    VENOMOTH,
    VENONAT,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "effective-pokemon-properties-v0.48.md"
TURN = 7
F, W, P, G = FIGHTING, WATER, PSYCHIC, GRASS
VS1 = "UNRESOLVED_SHIFT_COLOR_DURATION"
PG1 = "UNRESOLVED_CHANGE_ABSENT_WEAKNESS_RESISTANCE"
MH1 = "UNRESOLVED_MAX_HP_DROP"
H1 = "UNRESOLVED_EVOLUTION_HP"
COLORS = E.COLORS
COLORLESS = COLORS.index(EnergyType.COLORLESS)

# 登録の実装の型と値
ATTACKS = {
    (PORYGON, 0): (E.ChangeOpponentWeakness, {}),
    (PORYGON, 1): (E.ChangeOwnResistance, {}),
    (ROCKET_PORYGON, 0): (E.ChangeOpponentWeakness, {}),
    (ROCKET_PORYGON, 1): (E.ConfuseOnHeads, {}),
    (VENOMOTH, 0): (E.DamageThenPoisonAndConfuseOnHeads, {}),
    (SABRINAS_GASTLY, 0): (E.DamageOnly, {}),
    (SABRINAS_HAUNTER, 0): (E.CoinsPerNamedPokemonDamage, {"names": ("ナツメのゴース", "ナツメのゴースト", "ナツメのゲンガー"), "per": 30}),
    (SABRINAS_GENGAR, 0): (E.PlaceCountersOnDamagedOpponentPokemon, {"counters": 1}),
    (SABRINAS_GENGAR, 1): (E.DamageThenCoinsReturnOpponentToDeck, {"coins": 2}),
    (KOGAS_DITTO, 0): (E.SetMaxHpOnHeads, {"amount": 80}),
    (KOGAS_DITTO, 1): (E.DamageIfSelfMaxHpSet, {"effect_attack_name": "きょだいか", "amount": 30}),
}
POWERS = {VENOMOTH: E.ShiftColor(), SABRINAS_GASTLY: E.MaxHpPerAttachedEnergyCards(EnergyType.PSYCHIC, 10)}
# v0.48 で加えたワザの型（tests/helpers.py の ATTACK_TYPES_SINCE_V0_17 の最後の 8）
NEW_TYPES = (E.ChangeOpponentWeakness, E.ChangeOwnResistance, E.DamageThenPoisonAndConfuseOnHeads, E.CoinsPerNamedPokemonDamage,
             E.PlaceCountersOnDamagedOpponentPokemon, E.DamageThenCoinsReturnOpponentToDeck, E.SetMaxHpOnHeads, E.DamageIfSelfMaxHpSet)
# pcg-search.com の対象の版（サイトの一覧の番号）
EDITIONS = {PORYGON: "067/096", ROCKET_PORYGON: "050/065", VENOMOTH: "011/048", SABRINAS_GASTLY: "049/098", SABRINAS_HAUNTER: "050/098",
            SABRINAS_GENGAR: "051/098", KOGAS_DITTO: "067/098"}
# 進化しているポケモンの下のカード（build_test_state の "evolved_from"）
BELOW = {VENOMOTH: VENONAT, SABRINAS_HAUNTER: SABRINAS_GASTLY, SABRINAS_GENGAR: [SABRINAS_GASTLY, SABRINAS_HAUNTER], MUK: GRIMER, CLEFABLE: CLEFAIRY,
         HAUNTER: GASTLY, FOSSIL_GOLDUCK: FOSSIL_PSYDUCK, RATICATE: RATTATA, SABRINAS_KADABRA: SABRINAS_ABRA,
         GIOVANNIS_NIDOKING: [GIOVANNIS_NIDORAN_M, GIOVANNIS_NIDORINO]}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def bench_spec(b):
    return mon(b) if isinstance(b, str) and b in BELOW else b


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), hand=(), opponent_hand=(), turn=TURN, current=0):
    me = {"active": active, "bench": [bench_spec(b) for b in bench], "hand": list(hand)}
    them = {"active": opponent or mon(HITMONCHAN, (F, F, F)), "bench": [bench_spec(b) for b in opponent_bench], "hand": list(opponent_hand)}
    return build_test_state([me, them], turn_number=turn, current_player=current)


def full(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS))


def snapshot(state):
    return full(state), [dict(e) for e in state.log], repr(state.rng.getstate())


def audited(test, state):
    """不変条件・書き出し・観測の監査（盤面を直接作ったテスト。ログの監査は正式な対戦のテストで確かめる）。"""
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])
    return state


def events(state, since, kind=None):
    return [dict(e) for e in state.log[since:] if kind is None or e["kind"] == kind]


def answer(state, choices, *, mode="derived"):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)), preflight=mode)


def attack(state, index, *sides, player=None, mode="derived"):
    player = state.current_player if player is None else player
    return apply_kernel(with_coin_results(state, *sides) if sides else state, UseAttack(player, index), preflight=mode)


def assert_stops(test, state, command, code, *, exception=UnsupportedError):
    """どの先読みの方法でも ``code`` で拒否し、状態・乱数・ログが変わらない。"""
    before = snapshot(state)
    for mode in PREFLIGHT_MODES:
        with test.subTest(mode=mode), test.assertRaises(exception) as raised:
            apply_kernel(state, command, preflight=mode)
        test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def assert_rejected(test, state, command, code, exception=EngineError):
    before = snapshot(state)
    with test.assertRaises(exception) as raised:
        apply_kernel(state, command)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def end_turn(state):
    return apply_kernel(state, EndTurn(state.current_player))


def card_of(state, player, card, zone="hand", nth=0):
    return [u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card][nth]


def color(name: EnergyType) -> int:
    return COLORS.index(name)


def damage_amounts(state, since):
    return [e["amount"] for e in events(state, since, "damage")]


def _keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from _keys(value)


# ---------------------------------------------------------------- 登録・写し・記録


class CardDataTest(unittest.TestCase):
    """7 枚の写し・登録・記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_seven_requested_cards(self):
        """写しの組 pool_v0_48 は依頼の 7 枚（並び）。どれも対応で、どのワザも、どの特殊能力も登録した。同じ名前・似た名前の別のカードと取りちがえない。"""
        self.assertEqual(read_extract()["pool_v0_48"], list(V0_48_POKEMON))
        names = {PORYGON: "ポリゴン", ROCKET_PORYGON: "ポリゴン", VENOMOTH: "モルフォン", SABRINAS_GASTLY: "ナツメのゴース", SABRINAS_HAUNTER: "ナツメのゴースト",
                 SABRINAS_GENGAR: "ナツメのゲンガー", KOGAS_DITTO: "キョウのメタモン"}
        evolves = {VENOMOTH: "コンパン", SABRINAS_HAUNTER: "ナツメのゴース", SABRINAS_GENGAR: "ナツメのゴースト"}
        for card in V0_48_POKEMON:
            with self.subTest(card=card):
                definition = self.pool.get(card)
                self.assertEqual(definition.name_ja, names[card])
                self.assertTrue(self.pool.is_playable(card))
                self.assertEqual(definition.evolves_from, evolves.get(card))
                self.assertTrue(all(a.supported for a in definition.attacks))
        self.assertEqual(self.pool.get(SABRINAS_GENGAR).stage, "stage2")
        # 同じ名前の 2 枚のポリゴンは別のカード（HP・ワザが違う）。ゴース・ゴーストは化石の秘密のカードと別のカード
        self.assertEqual((self.pool.get(PORYGON).hp, self.pool.get(ROCKET_PORYGON).hp), (30, 40))
        self.assertNotEqual(self.pool.get(PORYGON).attacks, self.pool.get(ROCKET_PORYGON).attacks)
        for ours, other in ((SABRINAS_GASTLY, GASTLY), (SABRINAS_HAUNTER, HAUNTER)):
            self.assertNotEqual(self.pool.get(ours).name_ja, self.pool.get(other).name_ja)
        # 特殊能力の登録を除くと対応にならない（特殊能力を持つカードを、ワザだけの登録で対応と数えない）
        for card in POWERS:
            effects = E.DEFAULT_EFFECTS.without_powers(f"test-no-{card}", [E.PowerKey(card, 0)])
            with self.subTest(card=card):
                self.assertFalse(pool_from_extract(read_extract(), effects).is_playable(card))

    def test_every_attack_and_power_is_registered_with_the_expected_implementation(self):
        for card in V0_48_POKEMON:
            definition = self.pool.get(card)
            for index, attack_def in enumerate(definition.attacks):
                with self.subTest(card=card, index=index):
                    entry = E.DEFAULT_EFFECTS.attack_entry(card, index)
                    kind, values = ATTACKS[(card, index)]
                    self.assertIs(type(entry.effect), kind)
                    self.assertEqual(entry.effect, kind(**values))
                    self.assertEqual((entry.name_ja, entry.text_ja), (attack_def.name_ja, attack_def.text_ja))
                    self.assertEqual(entry.effect.check(attack_def), [])
                    if attack_def.text_ja:
                        self.assertEqual((entry.play_text_ja, entry.source), (attack_def.text_ja, cs.PRINTED_TEXT_SOURCE))
            for index, power in enumerate(definition.powers):
                with self.subTest(card=card, power=index):
                    entry = E.DEFAULT_EFFECTS.power_entry(card, index)
                    self.assertEqual(entry.effect, POWERS[card])
                    self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                                     (power.name_ja, power.text_ja, power.text_ja, cs.PRINTED_TEXT_SOURCE))
                    self.assertEqual(entry.effect.check(power), [])
            self.assertEqual(len(definition.powers), 1 if card in POWERS else 0)
        # ［へんしょく］は宣言して使う（自分の番に 1 回）。［ガスのからだ］は常にはたらく（特殊状態では消えない）
        self.assertTrue(POWERS[VENOMOTH].declared and POWERS[VENOMOTH].once_per_turn)
        self.assertIsInstance(POWERS[SABRINAS_GASTLY], E.ContinuousPower)
        self.assertFalse(POWERS[SABRINAS_GASTLY].declared or POWERS[SABRINAS_GASTLY].blocked_by_status)

    def test_text_checks_reject_other_wording(self):
        """型の ``check`` は登録した文面と同じものだけを受け付ける（ワザ・特殊能力とも）。はたくは同じカードの「きょだいか」も照らす。"""
        for (card, index), (kind, _) in ATTACKS.items():
            if kind not in NEW_TYPES:
                continue
            attack_def = self.pool.get(card).attacks[index]
            effect = E.DEFAULT_EFFECTS.attack_entry(card, index).effect
            with self.subTest(card=card, index=index):
                self.assertTrue(effect.check(dataclasses.replace(attack_def, text_ja=attack_def.text_ja + "あ")))
        for card, effect in POWERS.items():
            power = self.pool.get(card).powers[0]
            with self.subTest(card=card):
                self.assertTrue(effect.check(dataclasses.replace(power, text_ja=power.text_ja + "あ")))
        ditto = self.pool.get(KOGAS_DITTO)
        pound = E.DEFAULT_EFFECTS.attack_entry(KOGAS_DITTO, 1).effect
        self.assertEqual(pound.card_problems(ditto.attacks[1], ditto.attacks), [])
        renamed = (dataclasses.replace(ditto.attacks[0], name_ja="おおきくなる"), ditto.attacks[1])
        self.assertTrue(pound.card_problems(ditto.attacks[1], renamed))

    def test_new_types_are_kernel_programs_outside_the_v013_contract(self):
        start = ATTACK_TYPES_SINCE_V0_17.index(NEW_TYPES[0])  # あとの版の型がうしろに加わっても、v0.48 の型が続けて並んでいることを確かめる
        self.assertEqual(ATTACK_TYPES_SINCE_V0_17[start:start + len(NEW_TYPES)], NEW_TYPES)
        for kind in NEW_TYPES:
            with self.subTest(kind=kind.__name__):
                self.assertNotIn(kind, v013_checks.VERIFIED)
                self.assertIn(kind, programs.BUILDERS)
                effect = next(E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect for k in E.DEFAULT_EFFECTS.attack_keys()
                              if type(E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect) is kind)
                self.assertFalse(contract.is_contract(contract.program_for(effect)))

    def test_adoption_records_and_external_checks(self):
        """採用の記録（kyuura データの採用。処理に使う文面は kyuura の印刷の文面）と pcg-search.com の同じ版との照合。ガイドブックの項目は書かない。
        第1弾のポリゴンのテクスチャー2 の文面の違い（サイトの「抵抗力をを」）は処理に影響しない（kyuura への報告事項ではなくサイトの誤記）。"""
        records = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        for card in V0_48_POKEMON:
            with self.subTest(card=card):
                record = records[card]
                self.assertEqual((record["basis"], record["status"]), ("kyuura_data", "adopted"))
                self.assertEqual(record["kyuura_records"], [])
                checks = record["external_checks"]
                self.assertEqual(len(checks), 1)
                self.assertTrue(checks[0]["url"].startswith("https://pcg-search.com/"))
                self.assertEqual(checks[0]["edition"]["list_number"], EDITIONS[card])
                if card == PORYGON:
                    self.assertEqual(checks[0]["result"], "differences")
                    self.assertEqual([(x["field"], x["affects_behavior"]) for x in checks[0]["differences"]], [("pokemon.attacks[1].text.ja", False)])
                else:
                    self.assertEqual((checks[0]["result"], checks[0]["differences"]), ("match", []))
                self.assertFalse({"page", "pdf_page", "latest_description_ja", "card_image_text_ja"} & set(_keys(record)))
        self.assertEqual(cs.main([]), 0)


# ---------------------------------------------------------------- ポリゴン（テクスチャー1・テクスチャー2・サイケこうせん）


class ConversionTest(unittest.TestCase):
    """弱点・抵抗力の色を変える効果（相手・自分に与える持続する効果。期限はなく、ベンチにもどる・場をはなれる・進化で消える）。"""

    def converted(self, porygon=PORYGON, target=None, chosen=EnergyType.WATER):
        state = board(mon(porygon, (W, W, W)), target or mon(HITMONCHAN, (F, F, F)))
        pending = attack(state, 0)
        self.assertEqual(pending.decision.kind, SELECT_COLOR)
        self.assertEqual(pending.decision.player, 0)
        return pending, answer(pending, (color(chosen),))

    def test_conversion_1_changes_the_opponent_weakness_color(self):
        """テクスチャー1: 相手の対戦ポケモンの弱点を、選んだ「無色」以外の色にする（倍数は変えない）。選べるものに無色はない。2 枚のポリゴンで同じ。"""
        for porygon in (PORYGON, ROCKET_PORYGON):
            with self.subTest(porygon=porygon):
                pending, state = self.converted(porygon)
                self.assertNotIn(COLORLESS, pending.decision.options)
                self.assertEqual(len(pending.decision.options), len(COLORS) - 1)
                hitmonchan = state.players[1].active
                self.assertEqual(weakness_of(state, hitmonchan), EnergyType.WATER)
                self.assertEqual(state.card_def(hitmonchan.card).weakness, EnergyType.PSYCHIC)  # カードの定義は変わらない
                self.assertEqual([type(e) for e in hitmonchan.persistent_effects], [WeaknessChange])
                audited(self, state)

    def test_changed_weakness_survives_the_turn_end_and_is_used_by_damage(self):
        """変えた弱点は番の終わりで消えない（期限がない）。ダメージの計算（3 段階）で使う: 次の自分の番に、ベンチの化石の秘密のゴルダックに入れ替えて
        水のワザ（はかいこうせん 20）を使うと、弱点を水に変えた相手（エビワラー。印刷の弱点は 超）には 40。変えていなければ 20。"""
        def play(convert):
            state = board(mon(PORYGON, (W, W)), mon(HITMONCHAN, (F, F, F)), bench=(mon(FOSSIL_GOLDUCK, (W, W, W)),))
            if convert:
                state = answer(attack(state, 0), (color(EnergyType.WATER),))
            else:
                state = end_turn(state)
            state = end_turn(state)  # 相手の番を終えて、自分の番
            self.assertEqual(weakness_of(state, state.players[1].active), EnergyType.WATER if convert else EnergyType.PSYCHIC)
            porygon = state.players[0].active
            state = apply_kernel(state, Retreat(0, (porygon.energy[0],), state.players[0].bench[0].card))
            since = len(state.log)
            return damage_amounts(attack(state, 1), since)[0]

        self.assertEqual((play(True), play(False)), (40, 20))

    def test_using_it_again_replaces_the_previous_color(self):
        """もう一度使うと、前の効果を理由 replaced で消してから新しい色を与える（同じポケモンに同じ種類の効果は 1 つ）。"""
        _, state = self.converted(chosen=EnergyType.WATER)
        state = end_turn(state)  # 相手の番を終えて、自分の番
        pending = attack(state, 0)
        since = len(pending.log)
        state = answer(pending, (color(EnergyType.GRASS),))
        removed = events(state, since, "persistent_effect_removed")
        self.assertEqual([(e["persistent_effect"], e["reason"]) for e in removed], [(WeaknessChange.kind, "replaced")])
        self.assertEqual(weakness_of(state, state.players[1].active), EnergyType.GRASS)
        self.assertEqual(len(state.players[1].active.persistent_effects), 1)
        audited(self, state)

    def test_effect_ends_when_the_pokemon_returns_to_the_bench(self):
        """相手が「にげる」でベンチにもどすと消える（「ベンチに戻った時」・「バトル場をはなれた時」）。消えたら印刷の弱点にもどる。"""
        _, state = self.converted()  # ワザのあと、相手の番
        hitmonchan = state.players[1].active
        new = apply_kernel(state, Retreat(1, tuple(hitmonchan.energy[:2]), state.players[1].bench[0].card))
        moved = new.find_pokemon(hitmonchan.pokemon_id)[1]
        self.assertEqual(moved.persistent_effects, ())
        self.assertEqual(weakness_of(new, moved), EnergyType.PSYCHIC)
        self.assertIn(("weakness_change", "retreat"), [(e["persistent_effect"], e["reason"]) for e in events(new, len(state.log), "persistent_effect_removed")])
        audited(self, new)

    def test_no_weakness_is_unresolved(self):
        """弱点のないポケモン（ナツメのゴース）の弱点を変えるかは決まらない（PG1）。宣言の前に止め、状態・乱数・ログを変えない。弱点のあるポケモンは止めない。"""
        state = board(mon(PORYGON, (W,)), mon(SABRINAS_GASTLY, (P,)))
        assert_stops(self, state, UseAttack(0, 0), PG1)
        self.assertEqual(attack(board(mon(PORYGON, (W,)), mon(RATTATA)), 0).decision.kind, SELECT_COLOR)

    def test_conversion_2_changes_only_the_own_resistance_color(self):
        """テクスチャー2: 自分の抵抗力の色だけを変える（数 −30 はカードの定義のまま）。選んだ色のワザのダメージが 30 へる。ベンチにもどると消える。"""
        state = board(mon(PORYGON, (W, W)), mon(HITMONCHAN, (F, F, F)))
        pending = attack(state, 1)
        self.assertNotIn(COLORLESS, pending.decision.options)
        state = answer(pending, (color(EnergyType.FIGHTING),))
        porygon = state.players[0].active
        self.assertEqual(resistance_of(state, porygon), (EnergyType.FIGHTING, 30))
        self.assertEqual([type(e) for e in porygon.persistent_effects], [ResistanceChange])
        audited(self, state)
        # 相手（エビワラー。闘）のジャブ 20 は 抵抗力 闘 −30 で 0。弱点 闘 ×2 は先に計算する（3 段階 → 4 段階）
        since = len(state.log)
        state = attack(state, 0)
        self.assertEqual(damage_amounts(state, since), [10])  # 20 × 2（弱点 闘）− 30（抵抗力 闘）= 10

    def test_psybeam_confuses_on_heads(self):
        """ロケット団のポリゴンのサイケこうせん: ダメージ 20 → コインが「おもて」ならこんらん（既存の ConfuseOnHeads）。"""
        heads = attack(board(mon(ROCKET_PORYGON, (W, W, W)), mon(RATTATA)), 1, H)
        self.assertTrue(heads.players[1].active.conditions.confused)
        tails = attack(board(mon(ROCKET_PORYGON, (W, W, W)), mon(RATTATA)), 1, T)
        self.assertFalse(tails.players[1].active.conditions.confused)

    def test_copied_conversion(self):
        """ピクシーの「ゆびをふる」でテクスチャー1・2 を自分のワザとして使う（色を選ぶ決定はピクシーの持ち主）。抵抗力のないカスミのコダックが
        テクスチャー2 を使えるワザに含む場合は PG1 で宣言の前に止まる（既存の先読みの扱い。選べるワザのどれかが問いに当たると止める）。"""
        state = board(mon(CLEFABLE, (P, P, P)), mon(PORYGON, ()))
        pending = attack(state, 0)
        self.assertEqual(pending.decision.kind, "select_attack")
        for index, kind in ((0, WeaknessChange), (1, ResistanceChange)):
            with self.subTest(index=index):
                chosen = answer(pending, (index,))
                self.assertEqual((chosen.decision.kind, chosen.decision.player), (SELECT_COLOR, 0))
                done = answer(chosen, (color(EnergyType.GRASS),))
                holder = done.players[1].active if kind is WeaknessChange else done.players[0].active
                self.assertEqual([type(e) for e in holder.persistent_effects], [kind])
                audited(self, done)
        assert_stops(self, board(mon(MISTYS_PSYDUCK, (P, P)), mon(PORYGON, ())), UseAttack(0, 0), PG1)


# ---------------------------------------------------------------- モルフォン（［へんしょく］・りんぷん）


class ShiftColorTest(unittest.TestCase):
    """［へんしょく］: 自分の番に 1 回、このカードの色を場にいるポケモンのどれかの色にする。記録は場のポケモンの type_shift（形式 13）。"""

    def shifted(self, chosen=EnergyType.PSYCHIC, *, opponent=None, bench=(SABRINAS_GASTLY,)):
        state = board(mon(VENOMOTH, (G, G)), opponent or mon(HITMONCHAN, (F, F, F)), bench=bench)
        venomoth = state.players[0].active.pokemon_id
        pending = apply_kernel(state, UsePokemonPower(0, venomoth, 0))
        return state, pending, answer(pending, (color(chosen),))

    def test_options_are_the_colors_in_play_and_the_answer_belongs_to_the_owner(self):
        """選べる色は場にいるポケモンの色（モルフォン 草・ナツメのゴース 超・エビワラー 闘・コラッタ 無色）。決めるのは持ち主。"""
        _, pending, state = self.shifted()
        self.assertEqual((pending.decision.kind, pending.decision.player, pending.decision.resume), (SELECT_COLOR, 0, "power"))
        self.assertEqual(set(pending.decision.options), {color(c) for c in (EnergyType.GRASS, EnergyType.PSYCHIC, EnergyType.FIGHTING,
                                                                            EnergyType.COLORLESS)})
        self.assertEqual(type_readings(state, state.players[0].active), (EnergyType.PSYCHIC,))
        self.assertEqual(state.card_def(state.players[0].active.card).pokemon_type, EnergyType.GRASS)
        shift = [e for e in state.log if e["kind"] == "type_shift"]
        self.assertEqual((shift[-1]["color"], shift[-1]["player"]), ("psychic", 0))
        audited(self, state)

    def test_invalid_answers_and_second_use_are_rejected(self):
        """場にいない色・ほかのプレイヤーの答えは拒否し、状態は変わらない。自分の番に 1 回だけ（2 回目は POWER_ALREADY_USED）。"""
        _, pending, state = self.shifted()
        d = pending.decision
        assert_rejected(self, pending, ResolveDecision(0, d.id, (color(EnergyType.WATER),)), "INVALID_CHOICE")
        assert_rejected(self, pending, ResolveDecision(1, d.id, (color(EnergyType.PSYCHIC),)), "NOT_YOUR_DECISION")
        assert_rejected(self, state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0), "POWER_ALREADY_USED")

    def test_status_and_gas_switch_the_power_off(self):
        """ねむり・マヒ・こんらんでは使えない。かがくへんかガス（ベトベトン）がはたらいていると消える。"""
        asleep = board(mon(VENOMOTH, (G, G), sleep=True), bench=(SABRINAS_GASTLY,))
        assert_rejected(self, asleep, UsePokemonPower(0, asleep.players[0].active.pokemon_id, 0), "POKEMON_ASLEEP")
        gassed = board(mon(VENOMOTH, (G, G)), bench=(SABRINAS_GASTLY, MUK))
        assert_rejected(self, gassed, UsePokemonPower(0, gassed.players[0].active.pokemon_id, 0), "POWER_SUPPRESSED")

    def test_shifted_color_is_used_in_the_same_turn(self):
        """使った番のうちは変えた色で決まる: 超にしたモルフォンのりんぷん 10 は、弱点 超のエビワラーに 20。"""
        _, _, state = self.shifted()
        since = len(state.log)
        self.assertEqual(damage_amounts(attack(state, 0, T), since), [20])

    def test_after_the_turn_the_color_is_unresolved_only_when_it_matters(self):
        """使った番のあとに変えた色が続くかは決まらない（VS1）。2 つの読み方（超・草）でダメージが変わる相手（エビワラー。弱点 超なので 20 と 10）には、宣言の
        前に止める。読み方でダメージが変わらない相手（ナツメのゴース。弱点なし・抵抗力 闘なので、どちらでも 10）には止めない。もう一度［へんしょく］を使えば、
        その番は決まる。"""
        _, _, state = self.shifted()
        state = end_turn(end_turn(state))
        venomoth = state.players[0].active
        self.assertEqual(type_readings(state, venomoth), (EnergyType.PSYCHIC, EnergyType.GRASS))
        assert_stops(self, state, UseAttack(0, 0), VS1)
        # 同じ記録で、相手がナツメのゴース（弱点なし・抵抗力 闘）なら読み方でダメージは変わらないので止めない
        _, _, other = self.shifted(opponent=mon(SABRINAS_GASTLY, (P,)))
        other = end_turn(end_turn(other))
        since = len(other.log)
        self.assertEqual(damage_amounts(attack(other, 0, T), since), [10])
        # もう一度使えば、その番は決まる
        again = answer(apply_kernel(state, UsePokemonPower(0, venomoth.pokemon_id, 0)), (color(EnergyType.PSYCHIC),))
        self.assertEqual(type_readings(again, again.players[0].active), (EnergyType.PSYCHIC,))
        shift = [e for e in again.log if e["kind"] == "type_shift"][-1]
        self.assertEqual((shift["previous_color"], shift["color"]), ("psychic", "psychic"))

    def test_returning_to_the_bench_makes_the_color_undetermined(self):
        """使った番のうちでも、ベンチにもどった（にげる）あとは変えた色が続くか決まらない（VS1。記録の returned_to_bench）。観測は色を None・読み方を 2 つ。"""
        state = board(mon(VENOMOTH, (G, G)), bench=(RATTATA, SABRINAS_GASTLY))
        venomoth = state.players[0].active.pokemon_id
        state = answer(apply_kernel(state, UsePokemonPower(0, venomoth, 0)), (color(EnergyType.PSYCHIC),))
        state = apply_kernel(state, Retreat(0, (), state.players[0].bench[0].card))
        moved = state.find_pokemon(venomoth)[1]
        self.assertTrue(moved.type_shift.returned_to_bench)
        self.assertEqual(type_readings(state, moved), (EnergyType.PSYCHIC, EnergyType.GRASS))
        shown = next(p for p in observe(state, 0)["players"][0]["bench"] if p["pokemon_id"] == venomoth)
        self.assertEqual((shown["pokemon_type"], shown["pokemon_type_readings"], shown["type_shift"]["determined"]), (None, ["psychic", "grass"], False))
        audited(self, state)

    def test_record_needs_format_13(self):
        """記録は形式 13 で書き出す。形式 1〜12 は記録があると ValueError（黙って落とさない）。"""
        _, _, state = self.shifted()
        self.assertEqual(full(state)["players"][0]["active"]["type_shift"]["color"], "psychic")
        for version in range(1, 13):
            with self.subTest(version=version), self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        self.assertIn("type_shift", PUBLIC_EVENTS)

    def test_scale_dust_decides_poison_and_confusion_with_one_coin(self):
        """りんぷん: 1 枚のコインで、「おもて」ならどくとこんらん、「うら」なら何もしない。"""
        heads = attack(board(mon(VENOMOTH, (G, G)), mon(RATTATA)), 0, H)
        conditions = heads.players[1].active.conditions
        self.assertTrue(conditions.poison is not None and conditions.confused)
        self.assertEqual(len([e for e in heads.log if e["kind"] == "coin_flip" and e["source"] == "attack"]), 1)
        tails = attack(board(mon(VENOMOTH, (G, G)), mon(RATTATA)), 0, T)
        self.assertFalse(tails.players[1].active.conditions.poison is not None or tails.players[1].active.conditions.confused)


# ---------------------------------------------------------------- ナツメのゴース（［ガスのからだ］）と最大HPの低下（MH1）


class GaseousFormTest(unittest.TestCase):
    """［ガスのからだ］: ついている「超」の基本エネルギーカードの枚数 × 10 だけ最大HPが大きくなる。ねむり・マヒ・こんらんでもはたらき、かがくへんかガスで消える。"""

    def test_max_hp_counts_attached_psychic_energy_cards(self):
        """最大HP = 40 + 超のカードの枚数 × 10（ほかのタイプのカードは数えない）。カードの定義の HP は 40 のまま。観測の hp も同じ値。"""
        for energy, expected in (((), 40), ((P,), 50), ((P, P, W), 60), ((P, P, P), 70), ((W, W), 40)):
            state = board(mon(SABRINAS_GASTLY, energy))
            gastly = state.players[0].active
            with self.subTest(energy=energy):
                self.assertEqual(max_hp(state, gastly), expected)
                self.assertEqual(state.card_def(gastly.card).hp, 40)
                self.assertEqual(observe(state, 1)["players"][0]["active"]["hp"], expected)
                audited(self, state)

    def test_works_while_asleep_and_stops_under_gas(self):
        state = board(mon(SABRINAS_GASTLY, (P, P), sleep=True))
        self.assertEqual(max_hp(state, state.players[0].active), 60)
        gassed = board(mon(SABRINAS_GASTLY, (P, P)), bench=(MUK,))
        self.assertEqual(max_hp(gassed, gassed.players[0].active), 40)

    def test_knock_out_uses_the_effective_max_hp(self):
        """超 2 枚（最大HP 60）のナツメのゴースは、エビワラーのスペシャルパンチ（40 − 抵抗力 闘 30 = 10）で、ダメージ 40 ならきぜつせず（カードの HP 40 は
        超えている）、ダメージ 60 ならきぜつする（ワザのあとのきぜつの判定）。"""
        for start, knocked in ((30, False), (50, True)):
            state = board(mon(HITMONCHAN, (F, F, F)), mon(SABRINAS_GASTLY, (P, P), damage=start))
            new = attack(state, 1)
            with self.subTest(start=start):
                self.assertEqual(bool(events(new, len(state.log), "knock_out")), knocked)
                if not knocked:
                    self.assertEqual(new.players[1].active.damage, 40)
                    audited(self, new)

    def test_discarding_energy_in_an_attack_knocks_out_after_the_attack(self):
        """ワザの効果で超のカードがはがされ、最大HPがのっているダメージ以下に下がったら、ワザのあとのきぜつの判定できぜつする（GR-2000-P323-KNOCKOUT。
        化石の秘密のゴルダックのはかいこうせん。ダメージ 20 のあとエネルギーを 1 枚トラッシュ）。"""
        state = board(mon(FOSSIL_GOLDUCK, (W, W, W)), mon(SABRINAS_GASTLY, (P, P), damage=30))
        pending = attack(state, 1)
        if pending.decision is not None:
            pending = answer(pending, (pending.decision.options[0],))
        knocked = [e for e in pending.log[len(state.log):] if e["kind"] == "knock_out"]
        self.assertEqual(len(knocked), 1)  # 30 + 20 = 50 ≥ 40 + 10（超 1 枚）

    def test_gas_arriving_by_evolution_is_unresolved_when_hp_drops_to_damage(self):
        """ベトベターをベトベトンに進化させ（かがくへんかガスがはたらき［ガスのからだ］が消える）、ナツメのゴースの最大HPがのっているダメージ以下に下がるなら
        MH1 で止める（状態・乱数・ログは変わらない）。ダメージが下がったあとの最大HPより少なければ止めない。"""
        for damage, stops in ((40, True), (30, False)):
            state = board(mon(SABRINAS_GASTLY, (P, P), damage=damage), bench=(GRIMER,), hand=(MUK,))
            command = EvolvePokemon(0, card_of(state, 0, MUK), state.players[0].bench[0].pokemon_id)
            with self.subTest(damage=damage):
                if stops:
                    assert_rejected(self, state, command, MH1)
                else:
                    new = apply_kernel(state, command)
                    self.assertEqual(max_hp(new, new.players[0].active), 40)
                    audited(self, new)

    def test_pokemon_check_recovery_that_restores_gas_halts_before_the_coin(self):
        """ねむりのベトベトン（ガスが消えている）がポケモンチェックで目を覚ますと［ガスのからだ］が消えて最大HPがダメージ以下に下がる場合は、コインの前に
        HALTED（MH1）。"""
        state = board(mon(MUK, sleep=True), mon(SABRINAS_GASTLY, (P, P), damage=50))
        new = end_turn(state)
        self.assertEqual(new.phase, Phase.HALTED)
        self.assertEqual([e["code"] for e in new.log if e["kind"] == "halted"], [MH1])
        self.assertFalse([e for e in new.log[len(state.log):] if e["kind"] == "coin_flip"])

    def test_evolving_gastly_uses_the_evolved_max_hp(self):
        """ナツメのゴースト（HP 50。［ガスのからだ］はない）に進化すると最大HPは 50。のっているダメージ以上なら進化の H1（v0.4a）で止める。"""
        for damage, code in ((40, None), (50, H1)):
            state = board(mon(SABRINAS_GASTLY, (P, P), damage=damage), hand=(SABRINAS_HAUNTER,))
            command = EvolvePokemon(0, card_of(state, 0, SABRINAS_HAUNTER), state.players[0].active.pokemon_id)
            with self.subTest(damage=damage):
                if code:
                    assert_rejected(self, state, command, code)
                else:
                    new = apply_kernel(state, command)
                    self.assertEqual(max_hp(new, new.players[0].active), 50)


# ---------------------------------------------------------------- ナツメのゴースト（ナイトスピリッツ）


class NightSpiritsTest(unittest.TestCase):
    def test_coins_count_named_pokemon_once_each(self):
        """コインの数は自分の場の「ナツメのゴース」「ナツメのゴースト」「ナツメのゲンガー」の数（進化して重なったカードは 1 匹。化石の秘密のゴース・ゴースト
        は名前が違うので数えない）。「おもて」の数 × 30。"""
        state = board(mon(SABRINAS_HAUNTER, (P, P)), mon(CHANSEY), bench=(SABRINAS_GASTLY, GASTLY, HAUNTER, SABRINAS_GENGAR))
        new = attack(state, 0, H, T, H)
        coins = [e for e in new.log[len(state.log):] if e["kind"] == "coin_flip" and e["source"] == "attack"]
        self.assertEqual(len(coins), 3)
        damage = events(new, len(state.log), "damage")[0]
        self.assertEqual(damage["steps"][0][1], 60)
        audited(self, new)

    def test_preflight_modes_agree(self):
        state = board(mon(SABRINAS_HAUNTER, (P, P)), mon(RATTATA), bench=(SABRINAS_GASTLY, SABRINAS_GASTLY, SABRINAS_GASTLY, SABRINAS_GENGAR))
        results = set()
        for mode in PREFLIGHT_MODES:
            new = attack(state, 0, H, H, T, T, H, mode=mode)
            results.add(json.dumps(full(new), sort_keys=True, ensure_ascii=False))
        self.assertEqual(len(results), 1)


# ---------------------------------------------------------------- ナツメのゲンガー（ダメージぞうふく・やみのこえ）


class PainAmplifierTest(unittest.TestCase):
    def test_places_counters_on_damaged_opponent_pokemon_only(self):
        """相手の場の、ダメージカウンターがのっているポケモン全員に 1 個ずつ（ダメージではない: 弱点を計算しない・ログ damage はない）。のっていないポケモンは
        対象にしない。HP 以上になったポケモンはワザのあとにきぜつする。"""
        state = board(mon(SABRINAS_GENGAR, (P,)), mon(HITMONCHAN, (F, F, F), damage=20), opponent_bench=({"card": RATTATA, "damage": 20}, RATTATA))
        new = attack(state, 0)
        placed = events(new, len(state.log), "place_damage_counters")
        self.assertEqual([(e["pokemon_id"], e["amount"]) for e in placed], [(state.players[1].active.pokemon_id, 10),
                                                                            (state.players[1].bench[0].pokemon_id, 10)])
        self.assertFalse(events(new, len(state.log), "damage"))
        self.assertEqual(len(events(new, len(state.log), "knock_out")), 1)  # コラッタ（HP 30）

    def test_nothing_to_do_without_damaged_pokemon(self):
        state = board(mon(SABRINAS_GENGAR, (P,)), mon(HITMONCHAN, (F, F, F)))
        new = attack(state, 0)
        self.assertFalse(events(new, len(state.log), "place_damage_counters"))


class CallOfTheNightTest(unittest.TestCase):
    def board(self, opponent=None, **extra):
        return board(mon(SABRINAS_GENGAR, (P, P, P)), opponent or mon(CHANSEY, (W, W)), **extra)

    def test_both_heads_return_the_opponent_and_attached_cards_to_the_deck(self):
        """40 のあと、相手がきぜつしなければコイン 2 枚。すべて「おもて」なら、相手とついているカードを持ち主の山札にもどして切る。相手はバトル場に出す。"""
        state = self.board()
        chansey = state.players[1].active
        new = attack(state, 1, H, H)
        kinds = [e["kind"] for e in new.log[len(state.log):]]
        self.assertEqual(kinds[:6], ["attack", "damage", "coin_flip", "coin_flip", "return_in_play_to_deck", "shuffle"])
        self.assertIn(chansey.card, new.players[1].deck)
        self.assertTrue(all(uid in new.players[1].deck for uid in chansey.energy))
        self.assertEqual(new.decision.kind, "promote_active")

    def test_one_tails_does_nothing_and_knock_out_skips_the_coins(self):
        tails = attack(self.board(), 1, H, T)
        self.assertEqual(tails.players[1].active.card, self.board().players[1].active.card)
        state = self.board(mon(HITMONCHAN, (F, F, F)))  # 40 × 2（弱点 超）= 80 ≥ 70
        knocked = attack(state, 1)
        self.assertFalse([e for e in knocked.log[len(state.log):] if e["kind"] == "coin_flip"])

    def test_no_bench_is_not_required(self):
        """相手に控えがいなくても使える（別のワザの「控えが必要」という条件を持ち込まない）。もどしたあと相手のバトル場が空いて控えがいなければ、相手の負け。"""
        state = self.board(opponent_bench=())
        new = attack(state, 1, H, H)
        self.assertEqual(new.phase, Phase.GAME_OVER)
        self.assertEqual(new.result.winner, 0)


# ---------------------------------------------------------------- キョウのメタモン（きょだいか・はたく）


class GiantGrowthTest(unittest.TestCase):
    def grown(self, damage=0, opponent_hand=()):
        state = board(mon(KOGAS_DITTO, (W, W), damage=damage), bench=(RATTATA,), hand=(SWITCH,), opponent_hand=opponent_hand)
        return attack(state, 0, H)

    def test_heads_sets_max_hp_to_80_and_pound_becomes_30(self):
        """「おもて」なら最大HP 80（カードの定義は 40 のまま）。はたくは効果がはたらいている間だけ基本となるダメージ 30（そうでなければ 10）。"""
        state = self.grown()
        ditto = state.players[0].active
        self.assertEqual((max_hp(state, ditto), state.card_def(ditto.card).hp), (80, 40))
        self.assertEqual([type(e) for e in ditto.persistent_effects], [MaxHpSet])
        audited(self, state)
        state = end_turn(state)  # 相手の番を終えて、自分の番
        since = len(state.log)
        new = attack(state, 1)
        self.assertEqual(events(new, since, "damage")[0]["steps"][0][1], 30)
        plain = board(mon(KOGAS_DITTO, (W,)))
        self.assertEqual(events(attack(plain, 1), len(plain.log), "damage")[0]["steps"][0][1], 10)
        tails = attack(board(mon(KOGAS_DITTO, (W,))), 0, T)
        self.assertEqual(tails.players[0].active.persistent_effects, ())

    def test_retreat_ends_the_effect_and_dropping_to_the_damage_is_unresolved(self):
        """バトル場をはなれると消える。最大HP 80 → 40 で、のっているダメージが 40 以上になるなら MH1（にげるはエネルギーのトラッシュの前、ポケモンいれかえは
        手札から出す前に止め、状態・乱数・ログを変えない）。少なければ消えて最大HP 40・はたく 10 にもどる。"""
        state = attack(self.grown(damage=30), 0)  # 相手の番: エビワラーのジャブ 20 × 2（弱点 闘）= 40 → ダメージ 70（最大HP 80 なのできぜつしない）
        ditto = state.players[0].active
        self.assertEqual((ditto.damage, max_hp(state, ditto), state.current_player), (70, 80, 0))
        assert_rejected(self, state, Retreat(0, (ditto.energy[0],), state.players[0].bench[0].card), MH1)
        assert_rejected(self, state, PlayTrainer(0, card_of(state, 0, SWITCH)), MH1)
        low = end_turn(self.grown())
        moved = apply_kernel(low, Retreat(0, (low.players[0].active.energy[0],), low.players[0].bench[0].card))
        benched = moved.find_pokemon(low.players[0].active.pokemon_id)[1]
        self.assertEqual((benched.persistent_effects, max_hp(moved, benched)), ((), 40))
        audited(self, moved)

    def test_opponent_gust_is_stopped_before_it_leaves_the_hand(self):
        """相手の突風で、ダメージ 70・最大HP 80 のキョウのメタモンをベンチにもどすと最大HP 40 に下がるので、突風を手札から出す前に MH1 で止める。"""
        state = attack(self.grown(damage=30, opponent_hand=(GUST,)), 0)  # 相手のジャブ（ダメージ 70）
        state = end_turn(state)  # 自分の番を終えて、相手の番
        assert_rejected(self, state, PlayTrainer(1, card_of(state, 1, GUST)), MH1)

    def test_using_it_again_replaces_the_effect(self):
        state = end_turn(self.grown())
        since = len(state.log)
        again = attack(state, 0, H)
        self.assertEqual([e["reason"] for e in events(again, since, "persistent_effect_removed")], ["replaced"])
        self.assertEqual(len(again.players[0].active.persistent_effects), 1)


# ---------------------------------------------------------------- 今有効な最大HPを使うほかのワザ・先読み・複製


class EffectiveValueUsersTest(unittest.TestCase):
    """v0.48 の前からあるワザも、場のポケモンの最大HPは ``effects.max_hp``（今有効な値）で読む（印刷の HP を直接読まない）。"""

    def test_half_remaining_hp_uses_the_effective_max_hp(self):
        """ラッタの「いかりのまえば」（相手の残りの HP の半分。v0.45）: きょだいかの効果のキョウのメタモン（最大HP 80・ダメージ 20）なら 30、効果がなければ（40）10。"""
        state = board(mon(KOGAS_DITTO, (W, W), damage=20), mon(RATICATE, (W, W, W)))
        grown = attack(state, 0, H)  # きょだいか（「おもて」）。相手の番になる
        since = len(grown.log)
        self.assertEqual(events(attack(grown, 1), since, "damage")[0]["steps"][0][1], 30)
        plain = end_turn(board(mon(KOGAS_DITTO, (W,), damage=20), mon(RATICATE, (W, W, W))))
        self.assertEqual(events(attack(plain, 1), len(plain.log), "damage")[0]["steps"][0][1], 10)

    def test_life_down_leaves_ten_of_the_effective_max_hp(self):
        """ナツメのユンゲラーの「ライフダウン」（残りHPが 10 になるようにのせる。v0.42）: ［ガスのからだ］で最大HP 70 のナツメのゴース（ダメージ 10）には 50 のせる。"""
        state = board(mon(SABRINAS_KADABRA, (P,)), mon(SABRINAS_GASTLY, (P, P, P), damage=10))
        new = attack(state, 0, H)
        gastly = new.players[1].active
        self.assertEqual((gastly.damage, max_hp(new, gastly)), (60, 70))
        self.assertEqual([e["amount"] for e in events(new, len(state.log), "place_damage_counters")], [50])
        audited(self, new)

    def test_glare_compares_the_effective_max_hp(self):
        """サカキのニドキングの「すごむ」（「最大HPが50以下」のポケモンだけ。v0.40）: きょだいかの効果のキョウのメタモン（80）はワザを使えなくならず、
        効果がなければ（40）使えなくなる。"""
        grown = attack(board(mon(KOGAS_DITTO, (W, W)), mon(GIOVANNIS_NIDOKING, (G,))), 0, H)
        glared = attack(grown, 0)
        self.assertEqual([type(e) for e in glared.players[0].active.persistent_effects], [MaxHpSet])
        plain = end_turn(board(mon(KOGAS_DITTO, (W, W)), mon(GIOVANNIS_NIDOKING, (G,))))
        glared = attack(plain, 0)
        self.assertEqual([e.kind for e in glared.players[0].active.persistent_effects], ["cannot_attack_while_source_active"])

    def test_preflight_modes_agree_for_the_new_attacks(self):
        """テクスチャー1・やみのこえ・きょだいかは、どの先読みの方法でも同じ結果（v0.48 の型は v013_checks.VERIFIED に入れていないので、legacy もすべての結果を試す）。"""
        cases = (
            (board(mon(PORYGON, (W, W)), mon(HITMONCHAN, (F, F, F))), 0, ()),
            (board(mon(SABRINAS_GENGAR, (P, P, P)), mon(CHANSEY, (W, W))), 1, (H, H)),
            (board(mon(SABRINAS_GENGAR, (P, P, P)), mon(CHANSEY, (W, W))), 1, (H, T)),
            (board(mon(KOGAS_DITTO, (W,))), 0, (H,)),
        )
        for state, index, sides in cases:
            results = set()
            for mode in PREFLIGHT_MODES:
                new = attack(state, index, *sides, mode=mode)
                if new.decision is not None and new.decision.kind == SELECT_COLOR:
                    new = answer(new, (new.decision.options[0],), mode=mode)
                results.add(json.dumps(full(new), sort_keys=True, ensure_ascii=False))
            with self.subTest(card=state.card_def(state.players[0].active.card).id, sides=sides):
                self.assertEqual(len(results), 1)

    def test_clone_and_apply_keep_the_records(self):
        """複製（clone）は今有効な値の記録（持続する効果・へんしょくの記録）を同じに持ち、apply_command は渡された状態を変えない。"""
        grown = GiantGrowthTest().grown()
        self.assertEqual(full(grown.clone()), full(grown))
        before = full(grown)
        attack(end_turn(grown), 1)
        self.assertEqual(full(grown), before)
        self.assertEqual(max_hp(grown.clone(), grown.clone().players[0].active), 80)


# ---------------------------------------------------------------- 書き出しと観測


class SerializationAndObservationTest(unittest.TestCase):
    def test_persistent_effects_carry_color_and_amount(self):
        _, converted = ConversionTest().converted()
        effect = full(converted)["players"][1]["active"]["persistent_effects"][0]
        self.assertEqual((effect["effect"], effect["color"]), ("weakness_change", "water"))
        grown = GiantGrowthTest().grown()
        effect = full(grown)["players"][0]["active"]["persistent_effects"][0]
        self.assertEqual((effect["effect"], effect["amount"]), ("max_hp_set", 80))
        # 形式 13 の書き出しの hp はカードの定義の HP（今有効な最大HPは観測が書く）
        self.assertEqual(full(grown)["players"][0]["active"]["hp"], 40)
        self.assertEqual(observe(grown, 0)["players"][0]["active"]["hp"], 80)

    def test_observation_matches_the_processing_values(self):
        """観測の今有効な値は、エンジンの問い合わせ（max_hp・weakness_of・resistance_of・type_readings）と同じ。"""
        _, converted = ConversionTest().converted()
        for owner, pokemon in ((0, converted.players[0].active), (1, converted.players[1].active)):
            shown = observe(converted, None)["players"][owner]["active"]
            self.assertEqual(shown["hp"], max_hp(converted, pokemon))
            self.assertEqual(shown["weakness"], None if weakness_of(converted, pokemon) is None else weakness_of(converted, pokemon).value)
            self.assertEqual(shown["resistance"], None if resistance_of(converted, pokemon)[0] is None else resistance_of(converted, pokemon)[0].value)
            self.assertEqual(shown["pokemon_type_readings"], [c.value for c in type_readings(converted, pokemon)])


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.48 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.48 の 4 組を 3 seed ずつ（席を入れかえて 24 局）。どれも監査の失敗（やり直し・不変条件・ログ・書き出し・観測）・想定外の拒否・内部エラーがなく、
        7 枚のワザ・特殊能力が使われ、ナツメのゴースの系統が 2 進化まで進む（勝敗は判断に使わない）。"""
        from tools import existing_effect_games as games

        results = games.run(range(3), pairings=games.PAIRINGS_V0_48)
        totals, observed, policy = {}, {}, {}
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                for key, count in game["observed"].items():
                    observed[key] = observed.get(key, 0) + count
                for key, count in game["policy"].items():
                    policy[key] = policy.get(key, 0) + count
                for card, uses in game.get("card_uses", {}).items():
                    for key, count in uses.items():
                        totals[(card, key)] = totals.get((card, key), 0) + count
        for card, key in ((PORYGON, "persistent_effect_added#0"), (PORYGON, "persistent_effect_added#1"),
                          (ROCKET_PORYGON, "persistent_effect_added#0"), (ROCKET_PORYGON, "damage#1"),
                          (VENOMOTH, "evolved_to"), (VENOMOTH, "special_condition_poison#0"), (VENOMOTH, "special_condition_confusion#0"),
                          (SABRINAS_GASTLY, "damage#0"), (SABRINAS_HAUNTER, "evolved_to"), (SABRINAS_HAUNTER, "damage#0"),
                          (SABRINAS_GENGAR, "evolved_to"), (SABRINAS_GENGAR, "place_damage_counters#0"), (SABRINAS_GENGAR, "damage#1"),
                          (SABRINAS_GENGAR, "return_in_play_to_deck#1"),
                          (KOGAS_DITTO, "persistent_effect_added#0"), (KOGAS_DITTO, "base#1=30"), (KOGAS_DITTO, "base#1=10")):
            with self.subTest(card=card, key=key):
                self.assertGreater(totals.get((card, key), 0), 0)
        # ［へんしょく］を使った（選んだ色ごとに数える）。ナツメのゴーストの「ナイトスピリッツ」は「おもて」の数でダメージが変わる
        self.assertGreater(sum(n for (card, key), n in totals.items() if card == VENOMOTH and key.startswith("type_shift_")), 0)
        self.assertGreater(len({key for (card, key) in totals if card == SABRINAS_HAUNTER and key.startswith("base#0=")}), 1)
        # ［ガスのからだ］・「きょだいか」で、印刷の HP 以上のダメージがのったまま場にいた盤面（手順が数える）
        self.assertGreater(policy.get(f"v048_max_hp_{SABRINAS_GASTLY}_over_printed", 0), 0)
        self.assertGreater(policy.get(f"v048_max_hp_{KOGAS_DITTO}_over_printed", 0), 0)
        # 最大HPが下がる操作（MH1）と、弱点・抵抗力のないポケモンへのテクスチャー（PG1）は、場から確かめてから別の操作を続けた
        self.assertGreater(sum(n for key, n in observed.items() if key.endswith(MH1)), 0)
        self.assertGreater(observed.get(f"stopped_attack_{PG1}", 0), 0)


class DocumentTest(unittest.TestCase):
    def test_document_names_the_stop_codes(self):
        text = DOC.read_text(encoding="utf-8")
        for code in (VS1, PG1, MH1):
            self.assertIn(code, text)


if __name__ == "__main__":
    unittest.main()

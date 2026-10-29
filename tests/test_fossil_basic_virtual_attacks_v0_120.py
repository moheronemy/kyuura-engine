"""v0.120（docs/fossil-basic-virtual-attacks-v0.120.md）: 化石の復活と仮想ワザの供給の 11 枚（ポケモン 10・トレーナー 1。ワザ 15・特殊能力 5）。トゲチック（neo1-071）・
カブト（neo2-014）・オムナイト（neo2-032）・たまごの化石（neo2-055）・ワタッコ（neo3-007）・キングドラ（neo3-020）・プテラ（neo3-042）・スリーパー（ES3-025）・ミュウ（PR1-021）・
トゲピー（PR1-065）・ウソッキー（PF3-001）。

2 章（A0）: ナツメのESPのついたナツメのフーディンが、［サイコリンク］でカスミのコダックの「ちょうのうりょく」を使い、「おもて」3 枚で相手のコインのあるワザ（ラッキーの「まるまる」）を
自分のワザとして使う盤面。v0.119 では、宣言の前の先読みが、コピー先のコインを今の写しでは起こらないはずの ES0（コードのない問い）として内部エラー（``RuntimeError``）にしていた。

根拠は kyuura データの採用（kyuura ``e519b99`` の data/cards.json の日本語の印刷の文面。11 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録。英語の欄・現代の
ルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。盤面は ``build_test_state`` と通常の操作で作った 1 か所の規定を確かめるためのもので、
``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.120``）。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import unittest
from typing import ClassVar

from kyuura_engine import effects as E
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    BENCH_FROM_DECK_OR_HAND,
    DISCARD_OPPONENT_ENERGY,
    ESP_REDO,
    REVIVE_SOURCE,
    SEARCH_DECK,
    SELECT_ATTACK,
    SELECT_EVOLUTION_CARD,
    SELECT_POKEMON,
)
from kyuura_engine.errors import UnsupportedError
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.questions import QUESTIONS
from tests import helpers as H
from tests.test_neo_trainer_components_v0_80 import audited, new_events
from tests.test_unown_family_powers_v0_96 import snap
from tests.test_variable_coins_search_attachments_v0_113 import (
    answer,
    attack,
    board,
    esp_board,
    mon,
    provider_card,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "fossil-basic-virtual-attacks-v0.120.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, PS = H.WATER, H.PSYCHIC
ALAKAZAM = "PMCG6-053"  # ナツメのフーディン（［サイコリンク］）
MISTYS_PSYDUCK = "PMCG5-021"  # カスミのコダック（ちょうのうりょく: コイン 3 枚。「おもて」3 枚で相手のワザを自分のワザとして使う）
CHANSEY = "PMCG1-068"  # ラッキー（まるまる: コイン 1 枚・すてみタックル）
HITMONCHAN = "PMCG1-058"  # エビワラー（コインのないワザ 2 つ）
EC1 = E.ESP_COPIED_COINS_CODE


def a0_board(opponent=CHANSEY, *, esp=True):
    """超・水のついたナツメのフーディンのベンチに、超の色マーカーをのせたカスミのコダック。``esp`` ならナツメのESPを通常の操作でフーディンにつけた盤面。"""
    if esp:
        return esp_board(MISTYS_PSYDUCK, energy=(PS, W), opponent=mon(opponent))
    from kyuura_engine.cards import EnergyType
    from kyuura_engine.state import MARKER_COLOR

    return board(mon(ALAKAZAM, (PS, W)), bench=(mon(MISTYS_PSYDUCK, markers=[(MARKER_COLOR, EnergyType.PSYCHIC)]),), opponent=mon(opponent))


def psychic_power(state, *coins):
    return attack(state, 0, *coins, card=provider_card(state, MISTYS_PSYDUCK))


def coin_flips(before, after):
    return [e["result"] for e in new_events(before, after, "coin_flip") if e.get("source") == "attack"]


class EspCopiedAttackCoinsTest(unittest.TestCase):
    """A0（docs 2 章）: コピー元（ちょうのうりょく）のコインとコピー先（まるまる）のコイン。"""

    def test_declaration_reaches_the_first_redo_decision(self):
        """v0.119 では宣言の前の先読みが RuntimeError にした盤面。今は宣言を受け付け、ちょうのうりょくの 3 枚のあとにESPのやり直しを聞く（v0.66 の時点。止める選択はない）。"""
        state = a0_board()
        asked = psychic_power(state, HD, HD, HD)
        d = asked.decision
        self.assertEqual((d.kind, d.options, d.min_choices, d.max_choices), (ESP_REDO, (1,), 0, 1))
        self.assertIsNone(d.context_value("unresolved_code"))
        self.assertIsNone(d.context_value("esp_asked"))  # ESPのやり直しの決定には書かない（答えのあとに処理している並びのワザを記録し直す）
        self.assertEqual(coin_flips(state, asked), ["heads"] * 3)

    def test_copied_coin_redo_stops_and_declining_continues(self):
        """やり直す・やり直さないのどちらでも、ワザを選ぶ決定は聞いたことを続きの情報 ``esp_asked`` で運ぶ。コピー先のまるまるのコインのあとにもう一度聞くが、やり直すは選ぶと止める（EC1）。
        やり直さないはいつも答えで、まるまるのコインを 1 回だけ使う。"""
        asked = psychic_power(a0_board(), HD, HD, HD)
        for first, coins in (((), ()), ((1,), (HD, HD, HD))):
            with self.subTest(first=first):
                select = answer(asked, first, *coins)
                d = select.decision
                self.assertEqual(d.kind, SELECT_ATTACK)
                self.assertEqual(d.context_value("esp_asked"), ((MISTYS_PSYDUCK, 0),))
                second = answer(select, (0,), HD)  # まるまる
                d = second.decision
                self.assertEqual((d.kind, d.options, d.min_choices, d.max_choices), (ESP_REDO, (1,), 0, 1))
                self.assertEqual((d.context_value("unresolved_code"), d.context_value("unresolved_choices"), d.context_value("copied")),
                                 (EC1, (1,), (CHANSEY, 0)))
                self.assertIn("EC1", d.context_value("unresolved_reason"))
                with self.assertRaises(UnsupportedError) as raised:
                    answer(second, (1,), HD)
                self.assertEqual(raised.exception.code, EC1)
                done = answer(second, ())
                self.assertIsNone(done.decision)
                self.assertEqual(coin_flips(select, done), ["heads"])  # まるまるのコインは 1 回だけ
                self.assertEqual([e["kind"] for e in new_events(second, done, "esp_redo_declined")], ["esp_redo_declined"])
                self.assertTrue(any(e["kind"] == "persistent_effect_added" for e in new_events(second, done)))  # 「おもて」のまるまる
                for other in (second.clone(), copy.deepcopy(second), pickle.loads(pickle.dumps(second))):
                    self.assertEqual(snap(answer(other, ())), snap(done))
                for other in (select.clone(), copy.deepcopy(select), pickle.loads(pickle.dumps(select))):
                    self.assertEqual(snap(answer(answer(other, (0,), HD), ())), snap(done))

    def test_neighbours(self):
        """隣の例: ESPがなければワザを選ぶ決定まで進み、コインのまるまるでもESPの決定はない。相手のワザにコインがない（エビワラー）なら、ESPの決定 → ワザの選択で終わる。
        「おもて」が 3 枚でなければ、コピーしない（2 枚は 20 ダメージ）。"""
        plain = psychic_power(a0_board(esp=False), HD, HD, HD)
        self.assertEqual((plain.decision.kind, plain.decision.options), (SELECT_ATTACK, (0, 1)))
        self.assertIsNone(plain.decision.context_value("esp_asked"))
        rolled = answer(plain, (0,), HD)
        self.assertIsNone(rolled.decision)
        hitmonchan = answer(psychic_power(a0_board(HITMONCHAN), HD, HD, HD), ())
        self.assertEqual(hitmonchan.decision.kind, SELECT_ATTACK)
        self.assertIsNone(answer(hitmonchan, (0,)).decision)
        asked = psychic_power(a0_board(), HD, HD, TL)
        two = answer(asked, ())
        self.assertIsNone(two.decision)
        self.assertEqual([dict(e["steps"])["1 基本となる計算"] for e in new_events(asked, two, "damage")], [20])  # ラッキーの抵抗力で 0 になる
        self.assertEqual([e["kind"] for e in new_events(asked, two, "copy_attack")], [])

    def test_same_attack_second_toss_stays_codeless(self):
        """同じワザの説明文のコインを 2 回に分けて投げる並び（ES0）は、今もコードのない問い（今の写しでは起こらない）。EC1 とは別の問い。"""
        self.assertIsNone(QUESTIONS["esp_separate_coin_tosses"].code)
        self.assertEqual(EC1, "UNRESOLVED_ESP_COPIED_ATTACK_COINS")



# ---------------------------------------------------------------- 3 章〜9 章: 11 枚の盤面（build_test_state の 1 か所の規定）

TOGEPI, TOGETIC, MEW_PR, KINGDRA, AERODACTYL = "PR1-065", "neo1-071", "PR1-021", "neo3-020", "neo3-042"
HYPNO, SUDOWOODO, KABUTO, OMANYTE, EGG, JUMPLUFF = "ES3-025", "PF3-001", "neo2-014", "neo2-032", H.FOSSIL_EGG, "neo3-007"
V0120_POKEMON = (TOGETIC, KABUTO, OMANYTE, JUMPLUFF, KINGDRA, AERODACTYL, HYPNO, MEW_PR, TOGEPI, SUDOWOODO)
V0120 = (*V0120_POKEMON, EGG)
HORSEA, SEADRA, DROWZEE, HOPPIP, SKIPLOOM = "ES3-015", "ES3-016", "PMCG1-045", "neo1-005", "neo1-012"
KABUTOPS, OMASTAR, KABUTO_F, KABUTOPS_F, OMANYTE_F, AERODACTYL_F = "neo2-018", "neo2-035", "PMCG3-035", "PMCG3-040", "PMCG3-015", "PMCG3-041"
DOLL, DITTO, SPRAY, FOSSIL = H.CLEFAIRY_DOLL, H.DITTO, H.DEVOLUTION_SPRAY, H.MYSTERIOUS_FOSSIL
SHIELD_MEW, DARK_MAGCARGO, SLUGMA = "PR1-005", "neo4-023", "neo3-008"
F, G, L, DCE = H.FIGHTING, H.GRASS, H.LIGHTNING, H.DOUBLE_COLORLESS_ENERGY
TURN = 7
COMMIT = "e519b99e2adcc6c2cd0998569ae5ee1101de6e89"
PE1, PE2, VP1 = E.PRE_EVOLUTION_STAGE_CODE, E.PRE_EVOLUTION_CONDITION_CODE, E.PERMITTED_ATTACK_CODE
FE1, FE2, TF3 = E.REVIVED_DEVOLVE_CODE, E.REVIVE_HAND_BASIC_CODE, E.TRANSFORM_REVIVED_CODE
STOP_CODES = ((EC1, "EC1"), (PE1, "PE1"), (PE2, "PE2"), (VP1, "VP1"), (FE1, "FE1"), (FE2, "FE2"), (TF3, "TF3"))


def spec(card, energy=(), **extra):
    """場のポケモン。``below`` に進化元のカード（下から順）。``revived`` なら進化元を重ねずに出したたねとしてあつかう進化カード（重なりがあれば、いちばん下が出したカード）。"""
    result = {"card": card, "energy": list(energy), **{k: v for k, v in extra.items() if k not in ("below", "revived")}}
    if extra.get("below"):
        result["evolved_from"] = list(extra["below"])
    if extra.get("revived"):
        result["basic_entry"] = True
    return result


def table(active, *, bench=(), opponent=None, opponent_bench=(), hand=(), deck=None, opponent_deck=None, turn=TURN, current=0):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": list(deck if deck is not None else [H.WATER] * 10), "discard": [], "prizes": 6}
    them = {"active": opponent or spec(H.CHANSEY), "bench": list(opponent_bench), "hand": [], "deck": list(opponent_deck if opponent_deck is not None else [H.WATER] * 10),
            "discard": [], "prizes": 6}
    return H.build_test_state([me, them], turn_number=turn, current_player=current)


def use(state, index=0, *coins, card=None):
    return attack(state, index, *coins, **({"card": card} if card is not None else {}))


def power_use(state, pid, *coins):
    from kyuura_engine import UsePokemonPower

    return H.apply_kernel(H.with_coin_results(state, *coins) if coins else state, UsePokemonPower(state.current_player, pid, 0))


def trainer(state, card_id, *coins):
    from kyuura_engine import PlayTrainer

    uid = next(u for u in state.players[state.current_player].hand if state.cards[u].card_id == card_id)
    return H.apply_kernel(H.with_coin_results(state, *coins) if coins else state, PlayTrainer(state.current_player, uid))


def options_of(state, pokemon):
    return [(o.card_id, o.attack_index, o.route, o.provider, o.payer, o.grantors, o.problem and o.problem[0]) for o in E.available_attacks(state, pokemon)]


def kinds(before, after):
    return [e["kind"] for e in new_events(before, after)]


def rejected(test, state, command_or_fn, code, error=None):
    from kyuura_engine.errors import IllegalActionError

    with test.assertRaises(error or (IllegalActionError, UnsupportedError)) as caught:
        command_or_fn(state)
    test.assertEqual(caught.exception.code, code)
    return caught.exception


def kingdra(**extra):
    return spec(KINGDRA, extra.pop("energy", (W, W)), below=(HORSEA, SEADRA), **extra)


class RegistrationTest(unittest.TestCase):
    QUOTED: ClassVar[dict] = {
        TOGETIC: ("colorless", 60, "stage1", "トゲピー", ("おおきくゆびをふる", "そらをとぶ"), ()),
        KABUTO: ("water", 50, "stage1", "なにかの化石", ("ちからをあわせる",), ("なかまのふっかつ",)),
        OMANYTE: ("fighting", 50, "stage1", "なにかの化石", ("しめつける",), ("かせきのふっかつ",)),
        JUMPLUFF: ("grass", 70, "stage2", "ポポッコ", ("しんかのほうし", "ソーラービーム"), ()),
        KINGDRA: ("water", 90, "stage2", "シードラ", ("りゅうのいでんし", "たつまき"), ()),
        AERODACTYL: ("fighting", 60, "stage1", "なにかの化石", ("そらをとぶ",), ("げんしのきおく",)),
        HYPNO: ("psychic", 60, "stage1", "スリープ", ("マインドショック",), ("にんぎょうつかい",)),
        MEW_PR: ("psychic", 50, "basic", None, ("はたく", "サイコデュープ"), ()),
        TOGEPI: ("colorless", 30, "basic", None, ("なきつく", "ゆびをふる"), ()),
        SUDOWOODO: ("fighting", 60, "basic", None, ("たたきつける",), ("ものまね",)),
    }
    EXPECTED: ClassVar[dict] = {
        (TOGETIC, 0): E.CopyAttackFromSource(E.COPY_FROM_OPPONENT_FIELD, True), (TOGETIC, 1): E.FailOnTailsDamageThenSelfBarrier(),
        (KABUTO, 0): E.CoinBonusPerOwnBenchNamed(10, ("オムナイト", "オムスター", "カブト", "カブトプス", "プテラ")), (OMANYTE, 0): E.ParalyzeOnHeads(),
        (JUMPLUFF, 0): E.EvolveChosenNamedFromDeck(("ハネッコ", "ポポッコ")), (JUMPLUFF, 1): E.DAMAGE_ONLY,
        (KINGDRA, 0): E.CopyAttackFromSource(E.COPY_FROM_PRE_EVOLUTION, False), (KINGDRA, 1): E.CoinsDiscardOpponentEnergyElseFail(2),
        (AERODACTYL, 0): E.FailOnTailsDamageThenSelfBarrier(), (HYPNO, 0): E.DamageIgnoringWeaknessResistance(), (MEW_PR, 0): E.DAMAGE_ONLY,
        (MEW_PR, 1): E.CopyAttackFromSource(E.COPY_FROM_OPPONENT_FIELD, False, E.COPY_COST_COMBINED, "cannot_use"),
        (TOGEPI, 0): E.ReduceDamageToSelfNextOpponentTurn(20), (TOGEPI, 1): E.CopyAttackFromSource(E.COPY_FROM_DEFENDER, True), (SUDOWOODO, 0): E.CoinFlipDamage(2, 20),
    }
    POWERS: ClassVar[dict] = {KABUTO: E.CoinReviveFromDeck(E.REVIVE_NAMED, "カブト"), OMANYTE: E.CoinReviveFromDeck(E.REVIVE_FOSSIL), AERODACTYL: E.PreEvolutionAttacksForEvolvedActives(),
              HYPNO: E.DollUsesHolderAttacks(), SUDOWOODO: E.UseDefenderAttacks()}

    def test_entries_and_printed_texts(self):
        """10 枚のポケモン・15 のワザ・5 つの特殊能力と、たまごの化石。タイプ・HP・段階・進化元は固定データのまま（カブトの「水」・オムナイトの「闘」も写しのまま）。登録の型・引数と、
        処理に使う文面（印刷の文面。kyuura data/cards.json）。説明のないソーラービーム・はたくは文面・出典を持たない。"""
        from kyuura_engine import DEFAULT_EFFECTS
        from kyuura_engine.cards import load_card_pool, read_extract

        pool = load_card_pool()
        self.assertEqual(set(read_extract()["pool_v0_120"]), set(V0120))
        self.assertEqual(sum(len(q[4]) for q in self.QUOTED.values()), 15)
        self.assertEqual(sum(len(q[5]) for q in self.QUOTED.values()), 5)
        for card, (color, hp, stage, below, attacks, powers) in self.QUOTED.items():
            definition = pool.definitions[card]
            with self.subTest(card=card):
                self.assertIn(card, pool.playable_ids)
                self.assertEqual((definition.pokemon_type.value, definition.hp, definition.stage, definition.evolves_from), (color, hp, stage, below))
                self.assertEqual(tuple(a.name_ja for a in definition.attacks), attacks)
                self.assertEqual(tuple(p.name_ja for p in definition.powers), powers)
            for index, printed in enumerate(definition.attacks):
                entry = DEFAULT_EFFECTS.attack_entry(card, index)
                with self.subTest(card=card, index=index):
                    self.assertEqual(entry.effect, self.EXPECTED[(card, index)])
                    if printed.text_ja is None:
                        self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (None, None, None))
                    else:
                        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (printed.name_ja, printed.text_ja, printed.text_ja,
                                                                                                         "kyuura data/cards.json"))
                    self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, printed, definition.attacks))
            for index, printed in enumerate(definition.powers):
                entry = DEFAULT_EFFECTS.power_entry(card, index)
                with self.subTest(card=card, power=index):
                    self.assertEqual(entry.effect, self.POWERS[card])
                    self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (printed.name_ja, printed.text_ja, printed.text_ja,
                                                                                                     "kyuura data/cards.json"))
                    self.assertEqual(entry.effect.check(printed), [])
        egg = pool.definitions[EGG]
        self.assertIn(EGG, pool.playable_ids)
        self.assertEqual((egg.name_ja, egg.trainer_text_ja), ("たまごの化石", E.FOSSIL_EGG_TEXT))
        self.assertEqual(DEFAULT_EFFECTS.trainer_entry(EGG).effect, E.FossilEggRevive(E.FOSSIL_EGG_TEXT))

    def test_excluded_cards_stay_out(self):
        """依頼の対象外のメタモン（ES2-032）は登録しない（採用・保留の記録もない）。"""
        from kyuura_engine.cards import load_card_pool

        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        self.assertNotIn("ES2-032", load_card_pool().playable_ids)
        self.assertNotIn("ES2-032", sources)

    def test_unregistered_without_the_v0_120_entries(self):
        """v0.120 の登録を除くと、対戦に使えなくなるのはちょうどこの 11 枚。"""
        from kyuura_engine import DEFAULT_EFFECTS
        from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract

        registry = DEFAULT_EFFECTS.without_attacks("test-no-v0-120", E.V0_120_ATTACKS).without_powers("test-no-v0-120", E.V0_120_POWERS) \
            .without_trainers("test-no-v0-120", tuple(E.V0_120_TRAINERS))
        before = load_card_pool().playable_ids
        after = pool_from_extract(read_extract(), registry).playable_ids
        self.assertEqual(before - after, set(V0120))

    def test_records_and_research_links(self):
        """採用の記録 11 件（kyuura_data・adopted・e519b99・2026-10-30・kyuura_records なし・外部照合なし）。処理に使う文面は印刷の文面 19（ワザ 13・特殊能力 5・トレーナー 1）。研究の対応表の
        adopted_printed_text には、ポケモンのワザ・特殊能力の 18 を加えた（トレーナーの文面は対応表の範囲外）。新しい停止コード 7 は not_in_kyuura で、この版の文書の略号に結ぶ。"""
        data = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        texts = []
        for card in V0120:
            record = data[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"], record["kyuura_records"], record["external_checks"],
                                  record["issues"]), ("kyuura_data", "adopted", COMMIT, "2026-10-30", [], [], []))
                self.assertEqual(set(record["play_text"].values()), {"kyuura_printed_text"})
                texts += [f"{card}/{key}" for key in record["play_text"]]
        self.assertEqual(len(texts), 19)
        pokemon_texts = [t for t in texts if not t.startswith(EGG)]
        self.assertEqual(len(pokemon_texts), 18)
        self.assertLessEqual(set(pokemon_texts), set(links["latest_descriptions"]["adopted_printed_text"]))
        for code, ruling in STOP_CODES:
            with self.subTest(code=code):
                self.assertEqual(links["stop_codes"][code], {"engine_rulings": [{"version": "v0.120", "document": "docs/fossil-basic-virtual-attacks-v0.120.md",
                                                                                   "ruling_id": ruling}], "kyuura_issue": None, "kyuura_disposition": "not_in_kyuura"})

    def test_text_variants_are_exact(self):
        """新しい型は全文 1 通りずつ（範囲・コイン・必要なエネルギー・名前・枚数を広く読み替えない）。近い文面・違う数・違う名前は拒否する。"""
        import dataclasses

        from kyuura_engine.cards import load_card_pool

        pool = load_card_pool()
        togepi = pool.definitions[TOGEPI].attacks[1]
        self.assertEqual(E.CopyAttackFromSource(E.COPY_FROM_DEFENDER, True).check(togepi), [])
        self.assertNotEqual(E.CopyAttackFromSource(E.COPY_FROM_OPPONENT_FIELD, True).check(togepi), [])
        with self.assertRaises(ValueError):
            E.CopyAttackFromSource(E.COPY_FROM_DEFENDER, False)  # 書き方のない組は作れない
        self.assertNotEqual(E.CopyAttackFromSource(E.COPY_FROM_DEFENDER, True).check(dataclasses.replace(togepi, text_ja=togepi.text_ja.replace("相手の", "相手の場の"))), [])
        mew = pool.definitions[MEW_PR].attacks[1]
        self.assertNotEqual(E.CopyAttackFromSource(E.COPY_FROM_OPPONENT_FIELD, True).check(mew), [])
        def refused(make, printed):
            """書き方のない引数は作れず（ValueError）、作れる引数は違う文面を受け付けない。"""
            try:
                effect = make()
            except ValueError:
                return True
            return effect.check(printed) != []

        work = pool.definitions[KABUTO].attacks[0]
        five = ("オムナイト", "オムスター", "カブト", "カブトプス", "プテラ")
        for make, printed in ((lambda: E.CoinBonusPerOwnBenchNamed(10, ("オムナイト", "カブト")), work), (lambda: E.CoinBonusPerOwnBenchNamed(20, five), work),
                              (lambda: E.CoinsDiscardOpponentEnergyElseFail(3), pool.definitions[KINGDRA].attacks[1]),
                              (lambda: E.EvolveChosenNamedFromDeck(("ハネッコ",)), pool.definitions[JUMPLUFF].attacks[0]),
                              (lambda: E.CoinReviveFromDeck(E.REVIVE_NAMED, "オムナイト"), pool.definitions[KABUTO].powers[0]),
                              (lambda: E.CoinReviveFromDeck(E.REVIVE_FOSSIL), pool.definitions[KABUTO].powers[0]),
                              (lambda: E.CoinReviveFromDeck(E.REVIVE_NAMED, "カブト"), pool.definitions[OMANYTE].powers[0])):
            with self.subTest(printed=printed.name_ja):
                self.assertTrue(refused(make, printed))
        self.assertEqual(E.CoinBonusPerOwnBenchNamed(10, five).check(dataclasses.replace(work, text_ja=work.text_ja.replace("「プテラ」", ""))) != [], True)

    def test_programs_and_new_types(self):
        """要素の並び。新しいワザの型 4 つは解決の基盤の要素の並びで処理する（tests/helpers.py の ``ATTACK_TYPES_SINCE_V0_17``）。"""
        from kyuura_engine.resolution import v013_checks

        compile_attack = P.compile_attack
        self.assertEqual(compile_attack(E.CoinsDiscardOpponentEnergyElseFail(2)), (P.FailOnAllTails("coin", 2), P.Damage(P.OPP, P.Printed()),
                                                                                   P.DiscardOpponentEnergyByHeads(heads_of="coin")))
        self.assertEqual(compile_attack(E.EvolveChosenNamedFromDeck(("ハネッコ", "ポポッコ"))), (P.EvolveChosenFromDeck(("ハネッコ", "ポポッコ")),))
        togepi = compile_attack(E.CopyAttackFromSource(E.COPY_FROM_DEFENDER, True))
        self.assertEqual([type(element).__name__ for element in togepi], ["Coin", "CopyChosenAttack"])
        self.assertEqual([type(element).__name__ for element in compile_attack(E.CopyAttackFromSource(E.COPY_FROM_PRE_EVOLUTION, False))], ["CopyChosenAttack"])
        new = (E.CopyAttackFromSource, E.CoinBonusPerOwnBenchNamed, E.EvolveChosenNamedFromDeck, E.CoinsDiscardOpponentEnergyElseFail)
        start = H.ATTACK_TYPES_SINCE_V0_17.index(new[0])
        self.assertEqual(set(H.ATTACK_TYPES_SINCE_V0_17[start:start + len(new)]), set(new))
        for cls in new:
            with self.subTest(cls=cls.__name__):
                self.assertIn(cls, P.BUILDERS)
                self.assertNotIn(cls, v013_checks.VERIFIED)


class CopyChosenAttackTest(unittest.TestCase):
    """5 章: ワザを選んで自分のワザとして使うワザ。宣言したワザ・処理したワザ・ワザの出どころ・使うポケモン・払うポケモンを分ける。"""

    def test_metronome_heads_chooses_a_defender_attack_without_its_energy(self):
        """ゆびをふる: コインの「おもて」で相手の対戦ポケモンのワザを選ぶ（必要なエネルギーはいらない。スペシャルパンチの闘闘無はついていない）。「うら」なら選ばない。"""
        state = table(spec(TOGEPI, (W, W)), opponent=spec(H.HITMONCHAN))
        asked = use(state, 1, HD)
        d = asked.decision
        self.assertEqual((d.kind, d.options, d.context_value("copy_attacks"), d.context_value("copy_source")),
                         (SELECT_ATTACK, (0, 1), ((H.HITMONCHAN, 0), (H.HITMONCHAN, 1)), E.COPY_FROM_DEFENDER))
        done = answer(asked, (1,))
        self.assertIsNone(done.decision)
        copy_event = new_events(asked, done, "copy_attack")[0]
        self.assertEqual((copy_event["effect"], copy_event["copied"], copy_event["copy_source"]), (f"{TOGEPI}#1", f"{H.HITMONCHAN}#1", E.COPY_FROM_DEFENDER))
        self.assertEqual([dict(e["steps"])["1 基本となる計算"] for e in new_events(asked, done, "damage")], [40])  # スペシャルパンチ（闘闘無）は水 2 枚のまま
        tails = use(state, 1, TL)
        self.assertIsNone(tails.decision)
        self.assertEqual(new_events(state, tails, "copy_attack"), [])
        for other in (asked.clone(), copy.deepcopy(asked), pickle.loads(pickle.dumps(asked))):
            self.assertEqual(snap(answer(other, (1,))), snap(done))

    def test_super_metronome_lists_every_pokemon_on_the_opponents_field_once(self):
        """おおきくゆびをふる: 相手の場（バトル場 → ベンチ）のポケモンのワザを、ワザ（カードと位置）ごとに 1 つ。同じカードの 2 匹は 1 つにまとめる。"""
        state = table(spec(TOGETIC, (W,), below=(TOGEPI,)), opponent_bench=(H.HITMONCHAN, H.HITMONCHAN))
        asked = use(state, 0, HD)
        self.assertEqual(asked.decision.context_value("copy_attacks"), ((CHANSEY, 0), (CHANSEY, 1), (H.HITMONCHAN, 0), (H.HITMONCHAN, 1)))
        self.assertEqual(asked.decision.context_value("copy_source"), E.COPY_FROM_OPPONENT_FIELD)
        done = answer(asked, (2,))
        self.assertEqual([dict(e["steps"])["1 基本となる計算"] for e in new_events(asked, done, "damage")], [20])

    def test_psycho_dupe_needs_both_costs_as_one_payment(self):
        """サイコデュープ: 「サイコデュープ」の超 1 個に加えて、選んだワザに必要なエネルギーがミュウについていなければ使えない。払えないワザは選べず（選択に出ない）、どれも払えなければ
        宣言を受け付けない（INSUFFICIENT_ENERGY）。合わせて 1 つの支払い（超 1 枚を 2 つに数えない）。"""
        state = table(spec(MEW_PR, (PS, F)), opponent=spec(H.HITMONCHAN))
        asked = use(state, 1)
        self.assertEqual((asked.decision.options, asked.decision.context_value("copy_attacks")), ((0,), ((H.HITMONCHAN, 0), (H.HITMONCHAN, 1))))
        self.assertEqual(new_events(state, asked, "coin_flip"), [])
        rejected(self, table(spec(MEW_PR, (PS,)), opponent=spec(H.HITMONCHAN)), lambda s: use(s, 1), "INSUFFICIENT_ENERGY")
        three = table(spec(MEW_PR, (PS, F, F, F)), opponent=spec(H.HITMONCHAN))
        self.assertEqual(use(three, 1).decision.options, (0, 1))
        # 超 2 枚: 「サイコデュープ」の超 1 個とマインドショックの超 2 個は別々なら払えるが、合わせた超 3 個は払えない
        two = table(spec(MEW_PR, (PS, PS)), opponent=spec(HYPNO, below=(DROWZEE,)))
        rejected(self, two, lambda s: use(s, 1), "INSUFFICIENT_ENERGY")
        self.assertEqual(use(table(spec(MEW_PR, (PS, PS, PS)), opponent=spec(HYPNO, below=(DROWZEE,))), 1).decision.options, (0,))

    def test_genetic_memory_uses_the_card_just_below_and_stops_on_the_bottom_card(self):
        """りゅうのいでんし: 実際に重なっている進化前のカードのワザ。すぐ下のシードラのワザは選べ、いちばん下のタッツーのワザは選ぶと止める（PE1）。必要なエネルギーはいらない。"""
        state = table(kingdra(), opponent=spec(H.HITMONCHAN))
        asked = use(state, 0)
        d = asked.decision
        self.assertEqual((d.options, d.context_value("copy_attacks"), d.context_value("unresolved_choices")), ((0, 1, 2), ((SEADRA, 0), (HORSEA, 0), (HORSEA, 1)), (1, 2)))
        self.assertEqual({item[1] for item in d.context_value("unresolved_detail")}, {PE1})
        done = answer(asked, (0,))
        self.assertEqual(new_events(asked, done, "copy_attack")[0]["copy_source"], E.COPY_FROM_PRE_EVOLUTION)
        with self.assertRaises(UnsupportedError) as raised:
            answer(asked, (1,))
        self.assertEqual(raised.exception.code, PE1)
        self.assertEqual(E.copy_source_entries(state, 0, state.players[0].active, E.COPY_FROM_PRE_EVOLUTION)[0], (E.AttackKey(SEADRA, 0), None))

    def test_permitted_attacks_are_vp1_for_copiers(self):
        """許可で使えるワザ（［ものまね］で相手のウソッキーが使えるこちらのワザ・［にんぎょうつかい］でピッピ人形が使うスリーパーのワザ）は、相手の「持っているワザ」に入るかが決まらない
        （VP1）。ゆびをふるの選択に出るが、選ぶと止める。選べるワザがそれだけなら、コインの「おもて」の先で止まるので宣言を受け付けない。"""
        state = table(spec(TOGEPI, (W, W)), opponent=spec(SUDOWOODO))
        d = use(state, 1, HD).decision
        self.assertEqual((d.context_value("copy_attacks"), d.context_value("unresolved_choices")), (((SUDOWOODO, 0), (TOGEPI, 0), (TOGEPI, 1)), (1, 2)))
        self.assertEqual(d.context_value("unresolved_code"), VP1)
        doll = table(spec(TOGEPI, (W, W)), opponent=DOLL, opponent_bench=(spec(HYPNO, (PS, PS), below=(DROWZEE,)),))
        rejected(self, doll, lambda s: use(s, 1, HD), VP1, error=UnsupportedError)


class PermissionRouteTest(unittest.TestCase):
    """4 章: 「使ってよい」「使うことができる」と書く許可で使うワザ。持ち方（route）・供給するポケモン（provider）・払うポケモン（payer）・許可を与えるポケモン（grantors）。"""

    def test_prehistoric_memory_for_both_evolved_actives(self):
        """［げんしのきおく］: 場にプテラがいれば、おたがいのバトル場の進化ポケモンは、すぐ下のカードのワザを自分のワザとして使える（そのポケモンが払う）。2 進化のいちばん下は PE1。
        場ではたねとしてあつかう復活したカブトは進化ポケモンではない。その上に進化したカブトプスは、下のカブトのワザを使える。"""
        aero = spec(AERODACTYL, revived=True)
        state = table(kingdra(), bench=(aero,))
        self.assertEqual(options_of(state, state.players[0].active)[2:], [(SEADRA, 0, "prehistoric", None, None, (2,), None),
                                                                          (HORSEA, 0, "prehistoric", None, None, (2,), PE1), (HORSEA, 1, "prehistoric", None, None, (2,), PE1)])
        opponent = table(spec(H.HITMONCHAN), bench=(aero,), opponent=kingdra())
        self.assertIn((SEADRA, 0, "prehistoric", None, None, (2,), None), options_of(opponent, opponent.players[1].active))
        revived = table(spec(KABUTO, (F,), revived=True), bench=(aero,))
        self.assertEqual(E.field_stage(revived, revived.players[0].active), E.FIELD_BASIC)
        self.assertEqual(options_of(revived, revived.players[0].active), [(KABUTO, 0, "form", None, None, (), None)])
        kabutops = table(spec(KABUTOPS_F, (F, F), below=(KABUTO,), revived=True), bench=(aero,))
        self.assertEqual(E.field_stage(kabutops, kabutops.players[0].active), E.FIELD_EVOLVED)
        self.assertIn((KABUTO, 0, "prehistoric", None, None, (2,), None), options_of(kabutops, kabutops.players[0].active))
        asleep = table(kingdra(), bench=(aero,), opponent=spec(H.HITMONCHAN))
        asleep.players[0].bench[0], asleep.players[0].active = asleep.players[0].active, asleep.players[0].bench[0]
        self.assertEqual([o for o in options_of(asleep, asleep.players[0].active) if o[2] == "prehistoric"], [])  # プテラ自身は進化ポケモンではない

    def test_prehistoric_attack_log(self):
        state = table(spec(KABUTOPS_F, (F, F), below=(KABUTO,), revived=True), bench=(spec(AERODACTYL, revived=True),), opponent=spec(H.HITMONCHAN))
        done = use(state, 0, HD, card=state.players[0].active.evolution_stack[0])
        event = new_events(state, done, "attack")[0]
        self.assertEqual((event["route"], event["card_id"], event["grantors"], "payer" in event), ("prehistoric", KABUTO, (2,), False))

    def test_puppet_master_hypno_pays_and_the_doll_uses_the_attack(self):
        """［にんぎょうつかい］: バトル場のピッピ人形が、ベンチのスリーパーのワザを使う。必要なエネルギーはスリーパーのもの（払うポケモン）。2 匹のスリーパーはそれぞれ別の選択で、
        エネルギーの足りないスリーパーのワザは受け付けない（支払うポケモンを書く）。ワザを使うのはピッピ人形。"""
        state = table(DOLL, bench=(spec(HYPNO, (PS, PS), below=(DROWZEE,)), spec(HYPNO, (PS,), below=(DROWZEE,))), opponent=spec(H.HITMONCHAN))
        self.assertEqual(options_of(state, state.players[0].active), [(HYPNO, 0, "puppet", 2, 2, (2,), None), (HYPNO, 0, "puppet", 3, 3, (3,), None)])
        first, second = state.players[0].bench
        done = use(state, 0, card=first.card)
        event = new_events(state, done, "attack")[0]
        self.assertEqual((event["pokemon"], event["route"], event["provider"], event["payer"], event["grantors"]), (state.players[0].active.card, "puppet", 2, 2, (2,)))
        self.assertEqual([dict(e["steps"])["1 基本となる計算"] for e in new_events(state, done, "damage")], [30])
        error = rejected(self, state, lambda s: use(s, 0, card=second.card), "INSUFFICIENT_ENERGY")
        self.assertIn("支払うポケモン 3", str(error))
        # ［ニュートラルシールド］に渡す発生元はワザを使うピッピ人形（場ではたね）。スリーパー自身（1 進化）のワザは受けない
        shield = table(DOLL, bench=(spec(HYPNO, (PS, PS), below=(DROWZEE,)),), opponent=spec(SHIELD_MEW))
        hit = use(shield, 0, card=shield.players[0].bench[0].card)
        self.assertEqual([e["kind"] for e in new_events(shield, hit, "damage", "damage_prevented")], ["damage"])
        hypno = table(spec(HYPNO, (PS, PS), below=(DROWZEE,)), opponent=spec(SHIELD_MEW))
        self.assertEqual([e["kind"] for e in new_events(hypno, use(hypno, 0), "damage", "damage_prevented")], ["damage_prevented"])

    def test_mimic_uses_the_defender_attacks_with_its_own_energy(self):
        """［ものまね］: バトル場のウソッキーが相手の対戦ポケモンの持っているワザを使う（ウソッキーが払う）。ベンチ・ねむりでは使えない。"""
        state = table(spec(SUDOWOODO, (F,)), opponent=spec(H.HITMONCHAN))
        self.assertEqual(options_of(state, state.players[0].active), [(SUDOWOODO, 0, "form", None, None, (), None), (H.HITMONCHAN, 0, "mimic", 2, None, (1,), None),
                                                                      (H.HITMONCHAN, 1, "mimic", 2, None, (1,), None)])
        done = use(state, 0, card=state.players[1].active.card)
        event = new_events(state, done, "attack")[0]
        self.assertEqual((event["route"], event["provider"], event["grantors"], "payer" in event), ("mimic", 2, (1,), False))
        asleep = table(spec(SUDOWOODO, (F,), sleep=True), opponent=spec(H.HITMONCHAN))
        self.assertEqual([o[2] for o in options_of(asleep, asleep.players[0].active)], ["form"])
        rejected(self, state, lambda s: use(s, 1, card=s.players[1].active.card), "INSUFFICIENT_ENERGY")


class FossilRevivalTest(unittest.TestCase):
    """6 章・8 章: 進化元を重ねずに出し、場ではたねポケモンとしてあつかう進化カード（［なかまのふっかつ］・［かせきのふっかつ］・たまごの化石）。"""

    def test_revive_friends_benches_an_exact_named_kabuto_and_shuffles(self):
        """［なかまのふっかつ］: 「おもて」なら山札の「カブト」（名前が完全に同じ）を 1 枚ベンチに出し、山札を切る。出したカードは印刷の 1 進化のまま、場ではたね。番ごとに 1 回。"""
        state = table(spec(KABUTO, (F,), revived=True), deck=[KABUTO, KABUTO_F, KABUTOPS, W])
        asked = power_use(state, 1, HD)
        d = asked.decision
        names = sorted(state.cards[uid].card_id for uid in d.options)
        self.assertEqual((d.kind, d.min_choices, d.max_choices, names), ("bench_from_deck", 1, 1, sorted([KABUTO, KABUTO_F])))
        done = answer(asked, (d.options[0],))
        self.assertEqual(kinds(asked, done), ["bench_as_basic", "shuffle"])
        placed = done.players[0].bench[-1]
        self.assertEqual((placed.basic_entry.card, placed.basic_entry.zone, placed.basic_entry.source, placed.basic_entry.turn), (placed.card, "deck", f"{KABUTO}@power0", TURN))
        self.assertEqual((done.card_def(placed.card).stage, E.field_stage(done, placed)), ("stage1", E.FIELD_BASIC))
        rejected(self, done, lambda s: power_use(s, 1, HD), "POWER_ALREADY_USED")
        tails = power_use(state, 1, TL)
        self.assertEqual(kinds(state, tails), ["pokemon_power", "coin_flip"])
        none = power_use(table(spec(KABUTO, (F,), revived=True), deck=[W, W]), 1, HD)
        self.assertEqual((none.decision.options, none.decision.min_choices, none.decision.max_choices), ((), 0, 0))
        self.assertEqual(kinds(none, answer(none, ())), ["revive_none", "shuffle"])
        empty = power_use(table(spec(KABUTO, (F,), revived=True), deck=[]), 1, HD)
        self.assertEqual([e.get("reason") for e in new_events(state, empty, "revive_none")], ["deck_empty"])
        self.assertEqual(new_events(state, empty, "shuffle"), [])

    def test_revive_fossil_takes_cards_that_evolve_from_mysterious_fossil(self):
        state = table(spec(OMANYTE, (W,), revived=True), deck=[KABUTO, AERODACTYL_F, KABUTOPS, OMASTAR, W])
        asked = power_use(state, 1, HD)
        self.assertEqual(sorted(state.cards[uid].card_id for uid in asked.decision.options), sorted([KABUTO, AERODACTYL_F]))

    def test_revival_needs_room_and_no_special_condition(self):
        full = table(spec(KABUTO, (F,), revived=True), bench=[H.RATTATA] * 5, deck=[KABUTO])
        rejected(self, full, lambda s: power_use(s, 1, HD), "BENCH_FULL")
        asleep = table(spec(KABUTO, (F,), revived=True, sleep=True), deck=[KABUTO])
        rejected(self, asleep, lambda s: power_use(s, 1, HD), "POKEMON_ASLEEP")

    def test_fossil_egg_hand_or_deck(self):
        """たまごの化石: 「おもて」なら山札か手札から選ぶ（手札に出せるカードがなければ山札だけ）。手札から出せば山札を見ず切らない。山札なら見て、出したあと切る。「うら」なら何もしない。
        ベンチに空きがなければ使えない。"""
        state = table(spec(H.HITMONCHAN), hand=(EGG, OMANYTE), deck=[AERODACTYL, W])
        asked = trainer(state, EGG, HD)
        self.assertEqual((asked.decision.kind, asked.decision.options), (REVIVE_SOURCE, (0, 1)))
        from_hand = answer(asked, (0,))
        self.assertEqual(from_hand.decision.kind, SELECT_EVOLUTION_CARD)
        placed = answer(from_hand, from_hand.decision.options)
        self.assertEqual(kinds(from_hand, placed), ["bench_as_basic", "discard_trainer"])
        self.assertEqual(placed.players[0].bench[-1].basic_entry.zone, "hand")
        from_deck = answer(asked, (1,))
        self.assertEqual(from_deck.decision.kind, BENCH_FROM_DECK_OR_HAND)
        self.assertEqual([e["kind"] for e in new_events(asked, from_deck)], ["look_at_deck"])
        done = answer(from_deck, (from_deck.decision.options[0],))
        self.assertEqual(kinds(from_deck, done), ["bench_as_basic", "shuffle", "discard_trainer"])
        tails = trainer(state, EGG, TL)
        self.assertEqual(kinds(state, tails), ["play_trainer", "coin_flip", "discard_trainer"])
        deck_only = trainer(table(spec(H.HITMONCHAN), hand=(EGG,), deck=[KABUTO, W]), EGG, HD)
        self.assertEqual(deck_only.decision.options, (1,))
        full = table(spec(H.HITMONCHAN), bench=[H.RATTATA] * 5, hand=(EGG, OMANYTE))
        rejected(self, full, lambda s: trainer(s, EGG, HD), "BENCH_FULL")

    def test_fossil_egg_from_hand_under_hot_plate_is_fe2(self):
        """手札から出す進化カード（場でたねとしてあつかう）が［ヒートプレート］の「手札から「たねポケモン」を出すたび」に当たるかは決まらない（FE2）。手札から選ぶ（0）は、手札のどの
        カードも止めるので選ぶと止める選択。山札を見れば、山札のカードは止めず、手札のカードは選ぶと止める。"""
        state = table(spec(H.HITMONCHAN), hand=(EGG, OMANYTE), deck=[KABUTO, W], opponent=spec(DARK_MAGCARGO, below=(SLUGMA,)))
        asked = trainer(state, EGG, HD)
        d = asked.decision
        self.assertEqual((d.options, d.context_value("unresolved_choices"), d.context_value("unresolved_code")), ((0, 1), (0,), FE2))
        with self.assertRaises(UnsupportedError) as raised:
            answer(asked, (0,))
        self.assertEqual(raised.exception.code, FE2)
        deck = answer(asked, (1,)).decision
        hand_card = next(u for u in deck.options if state.cards[u].card_id == OMANYTE)
        self.assertEqual((deck.context_value("unresolved_choices"), deck.context_value("unresolved_code")), ((hand_card,), FE2))

    def test_revived_pokemon_evolves_by_its_printed_name_next_turn(self):
        """出した番には進化できない（場に出た番）。次の番からは、印刷のカードの名前から進化するカード（カブト → カブトプス）を重ねる。ベンチの移動・場の効果で記録は消えない。"""
        from kyuura_engine import EvolvePokemon

        state = table(spec(H.HITMONCHAN), bench=(spec(KABUTO, revived=True, played_turn=TURN),), hand=(KABUTOPS,))
        top = next(u for u in state.players[0].hand if state.cards[u].card_id == KABUTOPS)
        target = state.players[0].bench[0]
        rejected(self, state, lambda s: H.apply_kernel(s, EvolvePokemon(0, top, target.pokemon_id)), "PLAYED_THIS_TURN")
        later = table(spec(H.HITMONCHAN), bench=(spec(KABUTO, revived=True, played_turn=TURN - 2),), hand=(KABUTOPS,))
        top = next(u for u in later.players[0].hand if later.cards[u].card_id == KABUTOPS)
        evolved = H.apply_kernel(later, EvolvePokemon(0, top, later.players[0].bench[0].pokemon_id))
        pokemon = evolved.players[0].bench[0]
        self.assertEqual((pokemon.basic_entry.card, pokemon.evolution_stack, E.field_stage(evolved, pokemon)), (later.players[0].bench[0].card, (pokemon.basic_entry.card,),
                                                                                                                 E.FIELD_EVOLVED))

    def test_devolving_back_to_the_revived_card_is_fe1(self):
        """その上に進化したポケモンが退化し、たねとしてあつかった進化カードがまたいちばん上になる場面は決まらない（FE1）。退化スプレーは選べるが選ぶと止める。"""
        state = table(spec(KABUTOPS, (F,), below=(KABUTO,), revived=True), hand=(SPRAY,))
        count = answer(trainer(state, SPRAY), (state.players[0].active.pokemon_id,))
        d = count.decision
        self.assertEqual((d.options, d.context_value("unresolved_choices"), d.context_value("unresolved_code")), ((0, 1), (1,), FE1))
        with self.assertRaises(UnsupportedError) as raised:
            answer(count, (1,))
        self.assertEqual(raised.exception.code, FE1)
        self.assertIsNone(answer(count, (0,)).decision)

    def test_transforming_into_a_revived_basic_is_tf3(self):
        """［へんしん］のメタモンの相手の対戦ポケモンが、たねとしてあつかう進化カードになる操作は受け付けない（TF3）。"""
        from kyuura_engine import Retreat

        state = table(spec(H.HITMONCHAN, (F, F)), bench=(spec(KABUTO, revived=True),), opponent=spec(DITTO))
        rejected(self, state, lambda s: H.apply_kernel(s, Retreat(0, tuple(s.players[0].active.energy), s.players[0].bench[0].card)), TF3, error=UnsupportedError)

    def test_neutral_shield_sees_the_revived_card_as_basic(self):
        """場の分類はふつうの処理と共通: ［ニュートラルシールド］（相手の進化ポケモンからのワザを受けない）は、復活したカブトのワザを受け、その上に進化したカブトプスのワザは受けない。"""
        basic = table(spec(KABUTO, (F, W), revived=True), opponent=spec(SHIELD_MEW))
        hit = use(basic, 0, TL)
        self.assertEqual([e["kind"] for e in new_events(basic, hit, "damage", "damage_prevented")], ["damage"])
        evolved = table(spec(KABUTOPS, (F,), below=(KABUTO,), revived=True), opponent=spec(SHIELD_MEW))
        shielded = use(evolved, 0)
        self.assertEqual([e["kind"] for e in new_events(evolved, shielded, "damage", "damage_prevented")], ["damage_prevented"])

    def test_knocked_out_revived_pokemon_is_a_real_pokemon(self):
        """復活したポケモンはふつうのポケモン: きぜつすればトラッシュし、相手はサイドを 1 枚取る。"""
        state = table(spec(H.HITMONCHAN, (F, F, F)), opponent=spec(KABUTO, revived=True, damage=30), opponent_bench=(H.RATTATA,))
        kabuto = state.players[1].active.card
        done = use(state, 1)
        self.assertEqual([e["pokemon"] for e in new_events(state, done, "knock_out")], [kabuto])
        self.assertEqual((dict(done.pending_prizes), done.players[1].discard), ({0: 1}, [kabuto]))


class AttackMechanicsTest(unittest.TestCase):
    """7 章: ちからをあわせる・しんかのほうし・たつまき。"""

    def test_work_together_counts_exact_names_on_the_bench_only(self):
        bench = (spec(OMANYTE, revived=True), spec(KABUTO_F, revived=True), spec(AERODACTYL, revived=True), H.RATTATA)
        state = table(spec(KABUTO, (F, W), revived=True), bench=bench, opponent=spec(H.HITMONCHAN))
        self.assertEqual([dict(e["steps"])["1 基本となる計算"] for e in new_events(state, use(state, 0, HD), "damage")], [40])
        self.assertEqual([dict(e["steps"])["1 基本となる計算"] for e in new_events(state, use(state, 0, TL), "damage")], [10])

    def test_evolutionary_spore_chooses_then_searches_each_and_shuffles_once(self):
        """しんかのほうし: 自分の場の「ハネッコ」「ポポッコ」を好きなだけ選び、それぞれ山札から進化させ、最後に 1 回だけ山札を切る。0 匹は HC5（「好きなだけ」の 0）。"""
        state = table(spec(JUMPLUFF, (G,), below=(HOPPIP, SKIPLOOM)), bench=(HOPPIP, spec(SKIPLOOM, below=(HOPPIP,))), deck=[SKIPLOOM, JUMPLUFF, W])
        asked = use(state, 0)
        d = asked.decision
        self.assertEqual((d.kind, d.options, d.min_choices, d.max_choices), (SELECT_POKEMON, (2, 3), 0, 2))
        first = answer(asked, (2, 3))
        self.assertEqual(first.decision.kind, SEARCH_DECK)
        second = answer(first, first.decision.options[:1])
        done = answer(second, second.decision.options[:1])
        self.assertEqual(kinds(asked, done).count("shuffle"), 1)
        self.assertEqual([e["kind"] for e in new_events(asked, done) if e["kind"] in ("evolve", "shuffle")], ["evolve", "evolve", "shuffle"])
        with self.assertRaises(UnsupportedError) as raised:
            answer(asked, ())
        self.assertEqual(raised.exception.code, "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO")

    def test_twister_heads_count_and_failure(self):
        """たつまき: 「おもて」の数ぶんのエネルギーカードを相手からトラッシュ（ワザを使ったプレイヤーが選ぶ）。すべて「うら」なら失敗。ついている枚数が「おもて」の数より少なければ FC1。"""
        state = table(kingdra(energy=(W, W, W, W)), opponent=spec(H.HITMONCHAN, (F, F, F)))
        asked = use(state, 1, HD, HD)
        self.assertEqual((asked.decision.kind, asked.decision.min_choices, asked.decision.max_choices), (DISCARD_OPPONENT_ENERGY, 2, 2))
        done = answer(asked, asked.decision.options[:2])
        self.assertEqual(len(new_events(asked, done, "discard_attached_energy")), 2)
        one = use(state, 1, HD, TL)
        self.assertEqual(one.decision.min_choices, 1)
        failed = use(state, 1, TL, TL)
        self.assertEqual([e["kind"] for e in new_events(state, failed, "attack_failed", "damage")], ["attack_failed"])
        short = table(kingdra(energy=(W, W, W, W)), opponent=spec(H.HITMONCHAN, (F,)))
        with self.assertRaises(UnsupportedError) as raised:
            use(short, 1, HD, HD)
        self.assertEqual(raised.exception.code, "UNRESOLVED_STATED_CARDS_SHORT")


class SaveAndObservationTest(unittest.TestCase):
    """9 章: 保存の形式 28（場のポケモンの ``basic_entry``）・観測・続きの情報。"""

    def test_format_28_carries_basic_entry_and_older_formats_refuse(self):
        from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict

        state = table(spec(KABUTO, (F,), revived=True))
        self.assertEqual(max(FORMAT_VERSIONS), 28)
        data = state_to_dict(state, format_version=28)
        entry = data["players"][0]["active"]["basic_entry"]
        self.assertEqual((entry["card"], entry["zone"], entry["source"]), (state.players[0].active.card, "deck", "test"))
        with self.assertRaises(ValueError):
            state_to_dict(state, format_version=27)
        plain = table(spec(KABUTO, (F,), below=(FOSSIL,)))
        self.assertNotIn("basic_entry", state_to_dict(plain, format_version=28)["players"][0]["active"])
        state_to_dict(plain, format_version=27)

    def test_observation_shows_the_public_entry_and_hides_egg_choices(self):
        from kyuura_engine.observation import observe

        state = table(spec(H.HITMONCHAN), bench=(spec(KABUTO, revived=True),), hand=(EGG, OMANYTE), deck=[AERODACTYL, W])
        for viewer in (0, 1, None):
            shown = observe(state, viewer)["players"][0]["bench"][0]
            self.assertEqual(shown["basic_entry"]["zone"], "deck")
        asked = trainer(state, EGG, HD)
        mine, theirs = observe(asked, 0)["decision"], observe(asked, 1)["decision"]
        self.assertIn("options", mine)
        self.assertEqual(theirs, {"kind": REVIVE_SOURCE, "player": 0})
        audited(self, asked)
        deck = answer(asked, (1,))
        self.assertEqual(observe(deck, 1)["decision"], {"kind": BENCH_FROM_DECK_OR_HAND, "player": 0})
        audited(self, deck)

    def test_waiting_decisions_continue_the_same_after_copying(self):
        state = table(spec(H.HITMONCHAN), hand=(EGG, OMANYTE), deck=[AERODACTYL, KABUTO, W])
        asked = answer(trainer(state, EGG, HD), (1,))
        choice = (asked.decision.options[0],)
        expected = answer(asked, choice)
        for other in (asked.clone(), copy.deepcopy(asked), pickle.loads(pickle.dumps(asked))):
            self.assertEqual(snap(answer(other, choice)), snap(expected))



class AuditTest(unittest.TestCase):
    """12 章: ログの監査（tests/log_audit.py の ``v120_problems``・``v120_close`` と、本体の bench_as_basic・revive_none・look_at_deck の組み立て直し）は、エンジンの登録・計算を
    読まずに、処理したワザ・特殊能力・トレーナーの印刷の文面と、ログから組み立てた場・コインで確かめる。正式な開始からの対戦（tools/existing_effect_games.py の局。開発用の seed 60〜67。
    正式な対戦の seed 0〜3 とは別）を使い、ログを 1 か所書き換える・エンジンの処理を一時的に誤らせると、監査が見つける。"""

    GAMES = ((("F120", "S120"), 63), (("T120", "S120"), 62), (("F120", "J120"), 61), (("F120", "T120"), 63))
    _played: ClassVar[dict] = {}

    @classmethod
    def game(cls, labels, seed):
        from tools import existing_effect_games as games

        if (labels, seed) not in cls._played:
            cls._played[(labels, seed)] = games.play(labels, seed, keep_state=True)
        return cls._played[(labels, seed)]

    def rewritten(self, labels, seed, find, change=None, *, drop=False, double=False):
        """局のログの、``find`` に当たる最初のログを書き換えた（``change``）・除いた・2 つにした状態の監査の問題。"""
        from tests.log_audit import log_problems

        state = self.game(labels, seed)["state"].clone()
        log = list(state.log)
        index = next(i for i, e in enumerate(log) if find(log, i, e))
        event = dict(log[index])
        if change is not None:
            change(event)
        log[index:index + 1] = [] if drop else [event, event] if double else [event]
        state.log = tuple(log)
        return log_problems(state)

    def test_the_games_pass_the_audit_and_use_the_new_mechanics(self):
        from collections import Counter

        from tests.log_audit import log_problems

        used = Counter()
        for labels, seed in self.GAMES:
            result = self.game(labels, seed)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual(result["outcome"], "game_over")
                self.assertEqual((result["audit"], log_problems(result["state"])), ({}, []))
            used.update({k for k, v in result["v120"].items() if v})
        self.assertTrue({"copy_defender", "copy_opponent_field", "copy_pre_evolution", "psycho_dupe_copied", "metronome_tails", "route_prehistoric", "route_puppet",
                         "route_mimic", "puppet_paid", "revived_power_deck", "revived_trainer_hand", "revived_trainer_deck", "revive_none_no_card", "egg_looked",
                         "evolved_on_revived", "revived_attacked", "spore_evolved", "twister_failed", "twister_discarded", "work_together_heads"} <= set(used))

    def test_audit_finds_a_copied_attack_outside_the_printed_scope(self):
        found = self.rewritten(("T120", "S120"), 62, lambda log, i, e: e["kind"] == "copy_attack" and e.get("copy_source") == "pre_evolution",
                               lambda e: e.update(copied=f"{KINGDRA}#1"))
        self.assertTrue([p for p in found if "文面の範囲" in p])

    def test_audit_finds_a_puppet_attack_paid_by_the_doll(self):
        found = self.rewritten(("F120", "S120"), 63, lambda log, i, e: e["kind"] == "attack" and e.get("route") == "puppet", lambda e: e.pop("payer"))
        self.assertTrue([p for p in found if "スリーパーが払うものではない" in p])

    def test_audit_finds_a_prehistoric_attack_from_the_wrong_card(self):
        found = self.rewritten(("F120", "S120"), 63, lambda log, i, e: e["kind"] == "attack" and e.get("route") == "prehistoric", lambda e: e.update(card=e["pokemon"]))
        self.assertTrue([p for p in found if "すぐ下のカード" in p])

    def test_audit_finds_a_fossil_egg_that_looked_without_shuffling(self):
        found = self.rewritten(("F120", "S120"), 63, lambda log, i, e: e["kind"] == "shuffle" and set(e) == {"kind", "turn", "player"} and any(
            x["kind"] == "look_at_deck" for x in log[max(0, i - 3):i]), drop=True)
        self.assertTrue([p for p in found if "山札を見た場合だけ 1 回切る" in p])

    def test_audit_finds_a_second_shuffle_of_evolutionary_spore(self):
        found = self.rewritten(("F120", "J120"), 61, lambda log, i, e: e["kind"] == "shuffle" and e.get("effect") == f"{JUMPLUFF}#0", double=True)
        self.assertTrue([p for p in found if "しんかのほうしの山札を切ったログ" in p])

    def test_audit_finds_a_wrong_work_together_amount(self):
        def find(log, i, e):
            if e["kind"] != "damage" or i < 2:
                return False
            return log[i - 2]["kind"] == "attack" and log[i - 2].get("attack") == "ちからをあわせる" and log[i - 1].get("result") == "heads"

        found = self.rewritten(("F120", "S120"), 63, find, lambda e: e.update(steps=((("1 基本となる計算", dict(e["steps"])["1 基本となる計算"] + 10),) + tuple(e["steps"])[1:])))
        self.assertTrue([p for p in found if "ちからをあわせるの基本となるダメージ" in p])

    def test_audit_finds_a_twister_that_did_not_fail_on_two_tails(self):
        found = self.rewritten(("T120", "S120"), 62, lambda log, i, e: e["kind"] == "attack_failed" and log[i - 1].get("effect") == f"{KINGDRA}#1", drop=True)
        self.assertTrue([p for p in found if "すべて「うら」なのに" in p])

    def test_audit_finds_bottom_card_attacks_offered_without_pe1(self):
        """エンジンが 2 進化のいちばん下のカードのワザを止めずに選ばせると、りゅうのいでんしで選んだワザが文面の範囲（すぐ下のカード）にないことを監査が見つける。"""
        from unittest import mock

        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        original = E.pre_evolution_attack_keys

        def unchecked(state, pokemon):
            return [(key, None) for key, _ in original(state, pokemon)]

        found = []
        with mock.patch.object(E, "pre_evolution_attack_keys", unchecked):
            for labels, seed in ((("T120", "S120"), 62), (("S120", "T120"), 62), (("T120", "S120"), 63)):
                try:
                    result = games.play(labels, seed, keep_state=True)
                except Exception:  # noqa: BLE001  誤らせた処理が別の確かめで止まっても数えない
                    result = {}
                if result.get("state") is not None:
                    found += [p for p in log_problems(result["state"]) if "文面の範囲" in p]
        self.assertTrue(found)


# ---------------------------------------------------------------- 文書


class DocumentTest(unittest.TestCase):
    def test_document_records(self):
        import re

        text = DOC.read_text(encoding="utf-8")
        for word in ("EC1", "PE1", "PE2", "VP1", "FE1", "FE2", "TF3", *(code for code, _ in STOP_CODES), "0.120.0", "## 13. 検証", "lockstep", "単体のテストだけ",
                     "外部照合・カード画像・ガイドブックの読み直しをしていません", "ES2-032", "basic_entry", "setup_stopped", "1,356", "UQ-PLAY-AS-POKEMON"):
            self.assertIn(word, text)
        for card in V0120:
            self.assertIn(card, text)
        status = (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(int(re.search(r"^# 実装状況（v0\.1〜v0\.(\d+)）", status, re.MULTILINE).group(1)), 120)
        self.assertIn("## v0.120: 化石の復活と仮想ワザの供給", status)
        self.assertRegex((ROOT / "README.md").read_text(encoding="utf-8"), r"\n- v0\.120（(今のエンジンの版。)?`kyuura_engine` の版は 0\.120\.0）: 化石の復活と仮想ワザの供給")
        self.assertIn("### v0.120: 化石の復活と仮想ワザの供給", (ROOT / "docs" / "rules-2000-02-14.md").read_text(encoding="utf-8"))
        self.assertIn("## v0.120: 化石の復活と仮想ワザの供給", (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

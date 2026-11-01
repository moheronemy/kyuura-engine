"""v0.129: カツラのクイズ その1（GD5-016）と、値で答える決定（docs/blaines-quiz-heights-v0.129.md）。

- 登録・利用者が指定した参照値の記録（印刷の文面の採用・簡略ルールと別）・カード id の分岐がない
- 説明の順（置く → 名前を伝える → 身長を答える → 表にする → 引く → 手札にもどす）と、正解・不正解の引く側・枚数・山札が足りないとき
- 身長がいちばん低い・高い種族、所有者名つきカード、ポリゴン2（公式の表記はポリゴン２）、単位の換算、答えの範囲（正解の値の集合に絞らない）と不正な答え（変えずに拒否）
- 図鑑番号・身長のないカード（選べるが選ぶと止める。推測しない）、手札にポケモンがない（QZ1）
- 見える範囲（答えの前後の両プレイヤー・観戦者の観測とログ）、方策が公開の情報だけを読むこと
- 決定をまたぐ保存と復元、錯乱ジム・おもての山札、既存のクイズが変わらないこと、ログの監査、正式な開始からの対戦
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import pickle
import unittest
from types import MappingProxyType
from unittest import mock

from kyuura_engine import (
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    check_invariants,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine import effects as E
from kyuura_engine import heights as HT
from kyuura_engine.cards import load_card_pool, read_extract
from kyuura_engine.decisions import (
    QUIZ_ANSWER,
    QUIZ_CARD,
    QUIZ_HEIGHT_ANSWER,
    VALUE_ANSWER_MAX,
    VALUE_RANGE,
)
from kyuura_engine.resolution.programs import all_answers, answer_count, iter_answers
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.helpers import (
    BLAINES_QUIZ_3,
    CHAOS_GYM,
    FIGHTING,
    HITMONCHAN,
    MYSTERIOUS_FOSSIL,
    POTION,
    RATTATA,
    T,
    apply_kernel,
    build_test_state,
)
from tests.log_audit import observation_problems, v129_problems
from tests.release_catalog import cards_after
from tests.test_instant_trainers_v0_55 import (
    answer,
    assert_answer_stops,
    assert_use_stops,
    audited,
    card_of,
    kinds,
    mon,
    snapshot,
    use,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "blaines-quiz-heights-v0.129.md"
F = FIGHTING
QUIZ = "GD5-016"
DIGLETT, DIGLETT_B = "PMCG1-052", "PMCG4-038"  # ディグダ（No.050。20cm。いちばん低い種族）。2 枚は同じ名前の別の収録
STEELIX = "neo1-057"  # ハガネール（No.208。920cm。いちばん高い種族）
ONIX = "PMCG1-054"  # イワーク（No.095。880cm）
ERIKAS_BULBASAUR = "PMCG5-007"  # エリカのフシギダネ（所有者名つき。No.001。70cm）
PORYGON2 = "neo3-051"  # ポリゴン2（No.233。公式の表記は「ポリゴン２」。60cm）
PORYGON_NO_DEX = "ES1-033"  # ポリゴン（拡張シート第1弾。kyuura の記録に図鑑番号がない）
QZ1 = "UNRESOLVED_BLAINES_QUIZ_WITHOUT_POKEMON"
WITHOUT_DEX = "UNSUPPORTED_QUIZ_HEIGHT_WITHOUT_DEX"
NOT_AVAILABLE = "UNSUPPORTED_QUIZ_HEIGHT_NOT_AVAILABLE"
FU3 = "UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE"


def quiz_board(hand=(HITMONCHAN,), *, deck=(POTION, POTION, POTION, POTION), opponent_deck=(RATTATA, RATTATA, RATTATA, RATTATA), opponent_hand=()):
    me = {"active": mon(HITMONCHAN, (F,)), "bench": [RATTATA], "hand": [QUIZ, *hand], "deck": list(deck)}
    them = {"active": mon(HITMONCHAN, (F, F)), "bench": [RATTATA], "hand": list(opponent_hand), "deck": list(opponent_deck)}
    return build_test_state([me, them], turn_number=7, current_player=0)


def placed(state, card_id):
    """クイズを使い、手札の ``card_id`` を置いた（身長の答えを待つ）状態。"""
    state = use(state, QUIZ)
    return answer(state, (card_of(state, card_id),))


def reveal_of(state):
    return next(e for e in state.log if e["kind"] == "quiz_height_reveal")


def without_uids(value):
    if isinstance(value, dict):
        return {k: without_uids(v) for k, v in value.items() if k not in ("card", "cards", "trainer_card", "pokemon", "seed")}
    if isinstance(value, (list, tuple)):
        return [without_uids(v) for v in value]
    return value


# ---------------------------------------------------------------- 登録・記録


class RegistrationTest(unittest.TestCase):
    def test_entry(self):
        entry = E.DEFAULT_EFFECTS.trainer_entry(QUIZ)
        self.assertIsInstance(entry.effect, E.BlainesHeightQuiz)
        self.assertEqual((entry.name_ja, entry.source, entry.effect.draw, entry.effect.reference), ("カツラのクイズ その1", "kyuura data/cards.json", 2,
                                                                                                     E.USER_QUIZ_HEIGHT_OFFICIAL_ZUKAN))
        printed = load_card_pool().get(QUIZ).trainer_text_ja
        self.assertEqual(entry.text_ja, printed)
        self.assertEqual(entry.play_text_ja, printed)  # 処理に使う文面は印刷の文面のまま（簡略化・訂正していない）
        self.assertEqual(entry.effect.check(load_card_pool().get(QUIZ)), [])
        self.assertIn(QUIZ, load_card_pool().playable_ids)

    def test_pool(self):
        extract = read_extract()
        self.assertEqual(extract["pool_v0_129"], [QUIZ])
        self.assertEqual(cards_after(extract, "0.127"), {QUIZ})
        self.assertEqual(extract["source"]["commit"], "71d1728938fb4c8fefde9b82779cdef74beb612d")  # 写しの元は上げていない
        self.assertIn("pokemon.dex", extract["fields_used_by_engine"])

    def test_user_specified_reference_is_a_separate_record(self):
        record = E.USER_SPECIFIED_REFERENCES[f"{QUIZ}/trainer"]
        self.assertEqual(set(E.USER_SPECIFIED_REFERENCES), {f"{QUIZ}/trainer"})
        self.assertEqual((record.rule, record.specified_by, record.specified_on), (E.USER_QUIZ_HEIGHT_OFFICIAL_ZUKAN, "user", "2026-11-01"))
        self.assertEqual(record.printed_text, load_card_pool().get(QUIZ).trainer_text_ja)
        self.assertIn("全国図鑑No.001〜251の通常の姿の公式図鑑値", record.instruction)
        for word in ("印刷の身長", "印刷の訂正", "公式の裁定", "最新の説明", "エラッタ"):
            self.assertIn(word, record.not_recorded_as)
        self.assertFalse(set(E.USER_SPECIFIED_REFERENCES) & set(E.USER_SIMPLIFICATIONS))  # 誕生日・発話の省略（v0.127）とは別の指定
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        section = links["latest_descriptions"]
        self.assertEqual(section["user_specified_references"], {f"{QUIZ}/trainer": E.USER_SPECIFIED_REFERENCE_SOURCE})
        self.assertNotIn(f"{QUIZ}/trainer", section["adopted_printed_text"])
        self.assertNotIn(f"{QUIZ}/trainer", section["user_simplified_text"])
        self.assertEqual(len(section["adopted_printed_text"]), 1390)  # 印刷の文面の採用の数に入れていない
        self.assertIn({"version": "v0.129", "document": "docs/blaines-quiz-heights-v0.129.md", "ruling_id": "QZ1"},
                      links["stop_codes"][QZ1]["engine_rulings"])
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"][QUIZ]
        self.assertEqual((sources["play_text"], sources["user_specified_reference"]),
                         ({"trainer": "kyuura_printed_text"}, {"trainer": E.USER_SPECIFIED_REFERENCE_SOURCE}))

    def test_check_scripts_find_missing_records(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import check_card_sources as C

        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        record = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"][QUIZ]
        card = next(c for c in read_extract()["cards"] if c["id"] == QUIZ)
        registry = E.DEFAULT_EFFECTS
        self.assertEqual(C.user_specified_reference_problems(QUIZ, QUIZ, record, card, registry, links), [])
        missing = {k: v for k, v in record.items() if k != "user_specified_reference"}
        self.assertTrue(C.user_specified_reference_problems(QUIZ, QUIZ, missing, card, registry, links))
        unlisted = copy.deepcopy(links)
        del unlisted["latest_descriptions"]["user_specified_references"]
        self.assertTrue(C.user_specified_reference_problems(QUIZ, QUIZ, record, card, registry, unlisted))
        simplified = dict(record, play_text={"trainer": C.USER_SIMPLIFICATION_SOURCE})
        self.assertTrue(C.user_specified_reference_problems(QUIZ, QUIZ, simplified, card, registry, links))
        other = next(c for c in read_extract()["cards"] if c["id"] == "GD5-017")
        self.assertTrue(C.user_specified_reference_problems("GD5-017", "GD5-017", dict(record), other, registry, links))  # 記録のないカードには書けない

    def test_no_card_id_branch_in_engine_or_resolution(self):
        sources = [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py")),
                   ROOT / "kyuura_engine" / "decisions.py", ROOT / "kyuura_engine" / "observation.py", ROOT / "kyuura_engine" / "heights.py"]
        for path in sources:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(f'"{QUIZ}"', text, path.name)  # カード id の文字列で分けない（説明の文の中の言及はよい）
            self.assertNotIn(f"'{QUIZ}'", text, path.name)


# ---------------------------------------------------------------- 説明の順・引く側


class QuizFlowTest(unittest.TestCase):
    def test_correct_answer_opponent_draws_two_and_card_returns(self):
        state = placed(quiz_board(), HITMONCHAN)  # エビワラー（No.107。1.4m）
        self.assertEqual((state.decision.kind, state.decision.player), (QUIZ_HEIGHT_ANSWER, 1))
        right = answer(state, (140,))
        self.assertEqual(kinds(right), ["play_trainer", "quiz_card_set", "quiz_name_hint", "quiz_height_answer", "quiz_height_reveal", "draw", "set_aside_returned",
                                        "discard_trainer"])
        self.assertEqual((len(right.players[1].hand), len(right.players[0].hand), len(right.players[1].deck), len(right.players[0].deck)), (2, 1, 2, 4))
        self.assertEqual(right.cards[right.players[0].hand[0]].card_id, HITMONCHAN)  # 置いたカードは手札にもどる
        self.assertEqual(next(e for e in right.log if e["kind"] == "draw")["player"], 1)
        self.assertEqual(dict(reveal_of(right)), {"kind": "quiz_height_reveal", "turn": 7, "player": 0, "card": right.players[0].hand[0], "card_id": HITMONCHAN,
                                                  "name": "エビワラー", "dex": 107, "height_cm": 140, "correct": True, "trainer_card": right.players[0].discard[-1]})
        self.assertEqual(right.set_aside, ())
        audited(self, right)
        self.assertEqual(v129_problems(right), [])

    def test_wrong_answer_user_draws_two(self):
        state = placed(quiz_board(), HITMONCHAN)
        wrong = answer(state, (139,))
        self.assertEqual((len(wrong.players[1].hand), len(wrong.players[0].hand)), (0, 3))
        self.assertEqual(next(e for e in wrong.log if e["kind"] == "draw")["player"], 0)
        self.assertFalse(reveal_of(wrong)["correct"])
        self.assertIn(card_of(wrong, HITMONCHAN), wrong.players[0].hand)
        audited(self, wrong)

    def test_species_extremes_owner_names_and_porygon2(self):
        cases = [(DIGLETT, "ディグダ", 50, 20), (STEELIX, "ハガネール", 208, 920), (ONIX, "イワーク", 95, 880), (ERIKAS_BULBASAUR, "エリカのフシギダネ", 1, 70),
                 (PORYGON2, "ポリゴン2", 233, 60)]
        for card_id, name, dex, cm in cases:
            with self.subTest(card=card_id):
                state = placed(quiz_board(hand=(card_id,)), card_id)
                self.assertEqual(state.decision.context_value("name"), name)  # 伝えるのはカードの名前（所有者名・数字の書き方はカードのまま）
                hint = next(e for e in state.log if e["kind"] == "quiz_name_hint")
                self.assertEqual(hint["name"], name)
                right = answer(state, (cm,))
                self.assertEqual((reveal_of(right)["dex"], reveal_of(right)["height_cm"], reveal_of(right)["correct"]), (dex, cm, True))
                self.assertFalse(reveal_of(answer(state, (cm + 1,)))["correct"])
                self.assertFalse(reveal_of(answer(state, (cm - 1,)))["correct"])
                audited(self, right)
        self.assertEqual(HT.load_species_heights().by_dex[233].name_ja, "ポリゴン２")  # 参照値の名前は公式の表記のまま（答えの判定は cm だけ）

    def test_units_are_converted_by_the_input_layer(self):
        state = placed(quiz_board(hand=(DIGLETT,)), DIGLETT)
        for text in ("0.2m", "20cm", "0.20 m"):
            self.assertTrue(reveal_of(answer(state, (HT.height_answer_cm(text),)))["correct"], text)
        steel = placed(quiz_board(hand=(STEELIX,)), STEELIX)
        self.assertTrue(reveal_of(answer(steel, (HT.height_answer_cm("9.2m"),)))["correct"])
        self.assertEqual(HT.height_answer_cm("0.4m"), HT.height_answer_cm("40cm"))
        with self.assertRaises(ValueError):
            HT.height_answer_cm("20")  # 単位のない値は m か cm か決めない（エンジンの決定には整数 cm だけを渡す）

    def test_answers_are_not_limited_to_the_reference_values(self):
        state = placed(quiz_board(), HITMONCHAN)
        d = state.decision
        self.assertEqual((d.options, d.min_choices, d.max_choices, d.context_value(VALUE_RANGE)), ((), 1, 1, (1, VALUE_ANSWER_MAX)))
        references = {h.height_cm for h in HT.load_species_heights().by_dex.values()}
        self.assertTrue({1, 19, 921, 12345} - references)
        for value in (1, 19, 21, 141, 921, 1000, 12345, VALUE_ANSWER_MAX):  # 参照値にない値・とても大きい値も答えられる（正解でない）
            with self.subTest(value=value):
                self.assertFalse(reveal_of(answer(state, (value,)))["correct"])
        self.assertEqual(answer_count(d), VALUE_ANSWER_MAX)
        self.assertEqual([c for _, c in zip(range(3), iter_answers(d))], [(1,), (2,), (3,)])
        with self.assertRaises(ValueError):
            all_answers(d)  # 並べられない答えを並べない

    def test_invalid_answers_change_nothing(self):
        state = placed(quiz_board(), HITMONCHAN)
        d = state.decision
        for choices, code in (((0,), "INVALID_CHOICE"), ((-140,), "INVALID_CHOICE"), ((VALUE_ANSWER_MAX + 1,), "INVALID_CHOICE"), ((True,), "BAD_COMMAND"),
                              (("140",), "BAD_COMMAND"), ((140.0,), "BAD_COMMAND"), ((140, 140), "INVALID_CHOICE_COUNT"), ((), "INVALID_CHOICE_COUNT")):
            with self.subTest(choices=choices):
                before = snapshot(state)
                with self.assertRaises(IllegalActionError) as caught:
                    apply_kernel(state, ResolveDecision(1, d.id, choices))
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(snapshot(state), before)  # 状態・ログ・乱数は変わらない
                self.assertNotIn(HITMONCHAN, caught.exception.message)  # 置いたカードを書かない
        with self.assertRaises(IllegalActionError):
            apply_kernel(state, ResolveDecision(0, d.id, (140,)))  # 答えるのは相手プレイヤー

    def test_short_deck_draws_what_is_left(self):
        for deck, expected in (((POTION,), 1), ((), 0)):
            with self.subTest(deck=len(deck)):
                wrong = answer(placed(quiz_board(deck=deck), HITMONCHAN), (1,))
                self.assertEqual(len(wrong.players[0].hand), 1 + expected)
                self.assertEqual(sum(len(e["cards"]) for e in wrong.log if e["kind"] == "draw"), expected)
                right = answer(placed(quiz_board(opponent_deck=deck[:1] and (RATTATA,)), HITMONCHAN), (140,))
                self.assertEqual(len(right.players[1].hand), expected)
                audited(self, wrong)
                audited(self, right)
                self.assertEqual(v129_problems(wrong) + v129_problems(right), [])


# ---------------------------------------------------------------- 図鑑番号・身長のないカード、手札にポケモンがない


class MissingReferenceTest(unittest.TestCase):
    def test_card_without_dex_is_offered_but_stops_when_chosen(self):
        state = use(quiz_board(hand=(PORYGON_NO_DEX, DIGLETT)), QUIZ)
        d = state.decision
        self.assertEqual({state.cards[u].card_id for u in d.options}, {PORYGON_NO_DEX, DIGLETT})  # 選べるものから黙って除かない
        self.assertEqual(observe(state, 1)["decision"], {"kind": QUIZ_CARD, "player": 0})  # 選べるものの数・止めるカードを相手に見せない
        assert_answer_stops(self, state, (card_of(state, PORYGON_NO_DEX),), WITHOUT_DEX)  # 状態・ログ・乱数を変えずに止める
        after = answer(state, (card_of(state, DIGLETT),))
        self.assertEqual(after.decision.kind, QUIZ_HEIGHT_ANSWER)
        audited(self, state)

    def test_only_cards_without_reference_stop_before_use(self):
        assert_use_stops(self, quiz_board(hand=(PORYGON_NO_DEX,)), QUIZ, WITHOUT_DEX)  # 図鑑番号の欠け（QZ1 ではない）
        assert_use_stops(self, quiz_board(hand=(PORYGON_NO_DEX, POTION)), QUIZ, WITHOUT_DEX)

    def test_no_pokemon_is_qz1(self):
        for hand in ((), (POTION,), (MYSTERIOUS_FOSSIL,)):  # なにかの化石は手札ではトレーナーカード
            with self.subTest(hand=hand):
                assert_use_stops(self, quiz_board(hand=hand), QUIZ, QZ1)

    def test_missing_species_value_and_multiple_dex_are_not_guessed(self):
        base = HT.load_species_heights()
        without_50 = dataclasses.replace(base, by_dex=MappingProxyType({k: v for k, v in base.by_dex.items() if k != 50}))
        with mock.patch.object(HT, "load_species_heights", return_value=without_50):
            assert_use_stops(self, quiz_board(hand=(DIGLETT,)), QUIZ, NOT_AVAILABLE)  # 値がなければ 0cm にせず止める
            state = use(quiz_board(hand=(DIGLETT, HITMONCHAN)), QUIZ)
            assert_answer_stops(self, state, (card_of(state, DIGLETT),), NOT_AVAILABLE)
        state = quiz_board(hand=(PORYGON2, HITMONCHAN))
        state.definitions = MappingProxyType({**state.definitions, PORYGON2: dataclasses.replace(state.definitions[PORYGON2], dex=(137, 233))})
        state = use(state, QUIZ)
        assert_answer_stops(self, state, (card_of(state, PORYGON2),), NOT_AVAILABLE)  # 2 つの番号から選ばない


# ---------------------------------------------------------------- 見える範囲・方策


class VisibilityTest(unittest.TestCase):
    def test_same_name_cards_are_indistinguishable_before_the_answer(self):
        a = placed(quiz_board(hand=(DIGLETT,)), DIGLETT)
        b = placed(quiz_board(hand=(DIGLETT_B,)), DIGLETT_B)
        for viewer in (1, None):
            self.assertEqual(without_uids(observe(a, viewer)), without_uids(observe(b, viewer)))
            self.assertEqual(without_uids(visible_log(a, viewer)), without_uids(visible_log(b, viewer)))

    def test_only_the_name_is_public_before_the_answer(self):
        state = placed(quiz_board(hand=(DIGLETT,)), DIGLETT)
        expected = {"kind": QUIZ_HEIGHT_ANSWER, "player": 1, "min_choices": 1, "max_choices": 1, "value_range": {"min": 1, "max": VALUE_ANSWER_MAX, "unit": "cm"},
                    "name": "ディグダ"}
        self.assertEqual(observe(state, 1)["decision"], {**expected, "meaning": "value"})
        self.assertEqual(observe(state, None)["decision"], expected)
        self.assertEqual(observe(state, 0)["decision"], expected)
        for viewer in (1, None):
            text = json.dumps([observe(state, viewer), visible_log(state, viewer)], ensure_ascii=False)
            for secret in (DIGLETT, '"dex"', '"height_cm"', '"answer_cm"', '"value": '):  # 置き場所の種類の名前 quiz_card は公開
                self.assertNotIn(secret, text, (viewer, secret))
            hidden = [e for e in visible_log(state, viewer) if e["kind"] == "quiz_card_set"]
            self.assertEqual(hidden[0]["hidden"], {"card": None})
        self.assertIn(DIGLETT, json.dumps(observe(state, 0)["players"][0]["set_aside"]))  # 置いたプレイヤーは置いたカードを見ている
        self.assertEqual(next(e for e in visible_log(state, 0) if e["kind"] == "quiz_card_set")["card"], card_of(use(quiz_board(hand=(DIGLETT,)), QUIZ), DIGLETT))
        self.assertEqual(observation_problems(state), [])

    def test_after_the_reveal_everyone_sees_the_card_and_the_reference(self):
        state = answer(placed(quiz_board(hand=(DIGLETT,)), DIGLETT), (21,))
        for viewer in (0, 1, None):
            shown = next(e for e in visible_log(state, viewer) if e["kind"] == "quiz_height_reveal")
            self.assertEqual((shown["card_id"], shown["dex"], shown["height_cm"], shown["correct"]), (DIGLETT, 50, 20, False))
            returned = next(e for e in visible_log(state, viewer) if e["kind"] == "set_aside_returned")
            self.assertIn("cards", returned)
            answered = next(e for e in visible_log(state, viewer) if e["kind"] == "quiz_height_answer")
            self.assertEqual(answered["answer_cm"], 21)

    def test_policies_read_only_public_information(self):
        from tools import existing_effect_games as games

        a = placed(quiz_board(hand=(DIGLETT,)), DIGLETT)
        b = placed(quiz_board(hand=(DIGLETT_B,)), DIGLETT_B)
        for policy in games.V129_ANSWER_POLICIES:
            self.assertEqual(games.v129_public_answer(a, a.decision, policy), games.v129_public_answer(b, b.decision, policy))
        self.assertEqual(games.v129_public_answer(a, a.decision, "knowledge"), 20)
        self.assertEqual(games.v129_public_answer(a, a.decision, "wrong"), 21)
        # 置いたカード（続きの情報）を別のカードに書きかえても、観測が同じなら答えは同じ（置いたカードを読まない）
        swapped = a.clone()
        swapped.decision = dataclasses.replace(a.decision, context=tuple((k, a.players[0].active.card if k == "quiz_card" else v) for k, v in a.decision.context))
        self.assertEqual(games.v129_public_answer(swapped, swapped.decision, "knowledge"), 20)
        porygon2 = placed(quiz_board(hand=(PORYGON2,)), PORYGON2)
        self.assertEqual(games.v129_public_answer(porygon2, porygon2.decision, "knowledge"), 60)  # 名前「ポリゴン2」→ 公開のカードの一覧の図鑑番号 233


# ---------------------------------------------------------------- 保存・復元


class SaveRestoreTest(unittest.TestCase):
    def test_pending_decisions_survive_copies(self):
        first = use(quiz_board(hand=(PORYGON_NO_DEX, DIGLETT)), QUIZ)
        second = answer(first, (card_of(first, DIGLETT),))
        latest = max(FORMAT_VERSIONS)
        for state, finish in ((first, lambda s: answer(answer(s, (card_of(s, DIGLETT),)), (20,))), (second, lambda s: answer(s, (20,)))):
            for restored in (pickle.loads(pickle.dumps(state)), copy.deepcopy(state), state.clone()):
                self.assertEqual(state_to_dict(restored, format_version=latest), state_to_dict(state, format_version=latest))
                self.assertEqual(check_invariants(restored), [])
                self.assertEqual(state_to_dict(finish(restored), format_version=latest), state_to_dict(finish(state), format_version=latest))
                self.assertEqual(snapshot(finish(restored))[1], snapshot(finish(state))[1])
        written = state_to_dict(second, format_version=latest)
        self.assertEqual((written["decision"]["kind"], written["decision"]["options"], written["decision"]["context"]["value_range"]),
                         (QUIZ_HEIGHT_ANSWER, [], [1, VALUE_ANSWER_MAX]))
        self.assertEqual(written["set_aside"][0]["cards"], [card_of(first, DIGLETT)])

    def test_older_formats_refuse_rather_than_drop(self):
        state = placed(quiz_board(hand=(DIGLETT,)), DIGLETT)
        for version in FORMAT_VERSIONS:
            with self.subTest(version=version):
                if version < 21:
                    with self.assertRaises(ValueError):  # 置いておく場所（形式 21）を書けない形式は、黙って落とさない
                        state_to_dict(state, format_version=version)
                else:
                    written = state_to_dict(state, format_version=version)
                    self.assertEqual(written["decision"]["context"]["name"], "ディグダ")
                    self.assertTrue(written["set_aside"])


# ---------------------------------------------------------------- 錯乱ジム・おもての山札


class TrainerPathTest(unittest.TestCase):
    def test_borrowed_through_chaos_gym(self):
        """錯乱ジムで相手が借りて使う: 「あなた」は借りたプレイヤー（手札から置き、正解でないなら引く）。使ったプレイヤーの番を書かないので CH1 ではない。"""
        state = quiz_board(hand=(CHAOS_GYM, HITMONCHAN), opponent_hand=(DIGLETT,))
        state = use(state, CHAOS_GYM)
        state = use(state, QUIZ, coins=(T,))
        state = answer(state, (1,))  # 相手が借りて使う
        d = state.decision
        self.assertEqual((d.kind, d.player, [state.cards[u].card_id for u in d.options]), (QUIZ_CARD, 1, [DIGLETT]))
        state = answer(state, d.options)
        self.assertEqual((state.decision.kind, state.decision.player), (QUIZ_HEIGHT_ANSWER, 0))
        wrong = answer(state, (30,))
        self.assertEqual(next(e for e in wrong.log if e["kind"] == "draw")["player"], 1)  # 正解でないなら借りたプレイヤーが引く
        self.assertIn(card_of(wrong, DIGLETT, player=1), wrong.players[1].hand)
        audited(self, wrong)
        self.assertEqual(v129_problems(wrong), [])
        right = answer(state, (20,))
        self.assertEqual(next(e for e in right.log if e["kind"] == "draw")["player"], 0)
        audited(self, right)

    def test_face_up_deck_stops_before_the_answer(self):
        """おもてのカードのある山札: 正解・正解でないのどちらかの引き方が既存の止め方（FU3）に当たるなら、使う前に止める（答えの拒否から正誤を漏らさない）。いちばん上だけがおもてなら使える。"""
        from tests.test_flash_faceup_deck_v0_126 import board, card_in_hand, play_flash

        both = play_flash(board(hand=("ES2-035", QUIZ, HITMONCHAN)))
        cases = {"both": both.face_up_deck,
                 "user": tuple(u for u in both.face_up_deck if u not in both.players[1].deck),
                 "opponent": tuple(u for u in both.face_up_deck if u not in both.players[0].deck)}
        for label, marks in cases.items():
            with self.subTest(case=label):
                state = both.clone()
                state.face_up_deck = marks
                before = snapshot(state)
                with self.assertRaises(UnsupportedError) as caught:
                    apply_kernel(state, PlayTrainer(0, card_in_hand(state, QUIZ)))
                self.assertEqual(caught.exception.code, FU3)
                self.assertEqual(snapshot(state), before)
        top_only = both.clone()
        top_only.face_up_deck = tuple(u for u in both.face_up_deck if u in (both.players[0].deck[0], both.players[1].deck[0]))
        state = apply_kernel(top_only, PlayTrainer(0, card_in_hand(top_only, QUIZ)))
        state = answer(state, state.decision.options)
        for value in (140, 1):
            done = answer(state, (value,))
            self.assertEqual(len([e for e in done.log if e["kind"] == "draw"]), 1)
            self.assertEqual(check_invariants(done), [])
        # 既存のその3 は変えていない（使う前の確かめを加えていない。答えの段階の FU3 は v0.126 からの既存の動き。docs 6 章）
        three = play_flash(board(hand=("ES2-035", BLAINES_QUIZ_3, HITMONCHAN)))
        self.assertEqual(apply_kernel(three, PlayTrainer(0, card_in_hand(three, BLAINES_QUIZ_3))).decision.kind, QUIZ_CARD)


# ---------------------------------------------------------------- 既存のクイズ・監査・対戦


class ExistingQuizTest(unittest.TestCase):
    def test_quiz3_still_uses_names(self):
        me = {"active": mon(HITMONCHAN, (F,)), "bench": [RATTATA], "hand": [BLAINES_QUIZ_3, HITMONCHAN], "deck": [POTION] * 4}
        them = {"active": mon(HITMONCHAN, (F, F)), "bench": [RATTATA], "hand": [], "deck": [RATTATA] * 4}
        state = use(build_test_state([me, them], turn_number=7, current_player=0), BLAINES_QUIZ_3)
        state = answer(state, (card_of(state, HITMONCHAN),))
        state = answer(state, (0,))
        d = state.decision
        self.assertEqual(d.kind, QUIZ_ANSWER)
        self.assertIsNone(d.context_value(VALUE_RANGE))
        self.assertEqual(d.options, tuple(range(len(E.quiz_answer_names(state)))))
        self.assertEqual(len(E.quiz_answer_names(state)), 512)  # 名前の候補は変わらない（その1 はトレーナー）
        self.assertIn("option_count", observe(state, 0)["decision"])
        assert_answer_stops(self, state, (len(d.options),), "INVALID_CHOICE", IllegalActionError)
        right = answer(state, (d.context_value("names").index("エビワラー"),))
        self.assertTrue(next(e for e in right.log if e["kind"] == "quiz_reveal")["correct"])


class AuditTest(unittest.TestCase):
    def test_tampered_logs_are_found(self):
        state = answer(placed(quiz_board(), HITMONCHAN), (140,))
        self.assertEqual(v129_problems(state), [])

        def tampered(change):
            copy_ = state.clone()
            log = [dict(e) for e in copy_.log]
            change(log)
            copy_.log = [MappingProxyType(e) for e in log]
            return v129_problems(copy_)

        def at(log, kind):
            return next(e for e in log if e["kind"] == kind)

        self.assertTrue(tampered(lambda log: at(log, "draw").update(player=0)))  # 正解なのに使ったプレイヤーが引いた
        self.assertTrue(tampered(lambda log: at(log, "quiz_name_hint").update(card_id=HITMONCHAN)))  # 名前のほかに伝えた
        self.assertTrue(tampered(lambda log: at(log, "quiz_name_hint").update(name="コラッタ")))
        self.assertTrue(tampered(lambda log: at(log, "quiz_height_reveal").update(height_cm=141)))
        self.assertTrue(tampered(lambda log: at(log, "quiz_height_reveal").update(correct=False)))
        self.assertTrue(tampered(lambda log: at(log, "quiz_height_answer").update(answer_cm=0)))
        self.assertTrue(tampered(lambda log: log.remove(at(log, "quiz_name_hint"))))


class GamesTest(unittest.TestCase):
    def test_development_seed_runs_without_audit_failures(self):
        """開発用の seed 90 の v0.129 の組（席を入れかえて 6 局。鏡の組は 1 局にまとまる）。監査の失敗・想定外の拒否・内部エラー・手数の上限がなく、正解と正解でない答えの両方が起こる。"""
        from tools import existing_effect_games as games

        results = games.run(range(90, 91), pairings=games.PAIRINGS_V0_129)
        totals = {}
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                for key, count in game.get("v129", {}).items():
                    totals[key] = totals.get(key, 0) + count
        for key in ("played", "correct", "wrong", "drawn_by_answerer", "drawn_by_user", "returned"):
            self.assertGreater(totals.get(key, 0), 0, key)
        self.assertEqual(totals["played"], totals["correct"] + totals["wrong"])


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = DOC.read_text(encoding="utf-8")
        for phrase in ("QZ1", WITHOUT_DEX, NOT_AVAILABLE, E.USER_QUIZ_HEIGHT_OFFICIAL_ZUKAN, "9242b9b", "71d1728",
                       f"「{E.USER_SPECIFIED_REFERENCES[f'{QUIZ}/trainer'].instruction}」"):
            self.assertIn(phrase, text)
        for heading in ("## 1. 開始点と範囲", "## 2. 身長のデータの移行（kyuura 9242b9b）", "## 3. 利用者が指定した参照値（USER-QUIZ-HEIGHT-OFFICIAL-ZUKAN）",
                        "## 4. カードの処理", "## 5. 答えの表現（値で答える決定）", "## 6. 図鑑番号・身長がないカード、手札にポケモンがない、ほかの経路",
                        "## 7. 見える範囲・保存・不変条件・監査", "## 8. 対戦の方策・正式な対戦の組", "## 9. 数", "## 10. 検証", "## 11. 制限・kyuura への報告事項"):
            self.assertIn(heading + "\n", text)
        self.assertRegex((ROOT / "README.md").read_text(encoding="utf-8"), r"\n- v0\.129（(今のエンジンの版。)?`kyuura_engine` の版は 0\.129\.0）: カツラのクイズ その1")
        self.assertIn("## v0.129: カツラのクイズ その1と、公式図鑑の種族の身長の参照値\n", (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8"))
        self.assertIn("### v0.129: カツラのクイズ その1と公式図鑑の身長", (ROOT / "docs" / "rules-2000-02-14.md").read_text(encoding="utf-8"))
        self.assertIn("## v0.129: 公式図鑑の種族の身長の写しと、カツラのクイズ その1\n", (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

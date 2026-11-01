"""v0.131: ナッシー[Exeggutor]（PR1-075・PR1-077）と、利用者が指定した日英併記の名前の扱い（docs/exeggutor-bilingual-names-v0.131.md）。

- 登録: ふみつけは既存の ``CoinBonusDamage(10)``（全文・数値で照らす。通常のナッシーのワザには置きかえない）。2 枚は同じ登録の値で、採用の記録・名前の扱いの記録は id ごと
- 利用者が指定した名前の扱いの記録（対象・欄・判定に使う値・範囲。印刷の確認は PR1-077 だけ）と、採用の記録・研究の対応表・文書の引用。転記の訂正・ほかの利用者の指定と別
- 原文（写しの名前・ワザ名・説明）が残り、判定に使う名前と表示の欄が分かれる。ほかのカードの括弧書き・名前は変わらない。写しが変われば当てはめない
- デッキの同じ名前（通常のナッシーと合わせて 4 枚まで）・進化元（タマタマから進化でき、ほかの名前からはできない）・名前を指定する効果・同じ名前を比べる効果（スロットゲーム）
- カツラのクイズ その3（伝えるワザ名・答えの名前の候補・正解）・その1（図鑑番号がないので選ぶと止める）
- ふみつけの正常系と境界（「おもて」「うら」・エネルギーが足りない）、ゆびをふる・へんしんの名前とワザの供給元
- 保存と復元のあとも同じ判定
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import pickle
import unittest

from kyuura_engine import IllegalActionError, ResolveDecision, UseAttack, observe
from kyuura_engine import effects as E
from kyuura_engine.cards import classify_record, load_card_pool, read_extract
from kyuura_engine.commands import EvolvePokemon, PlayTrainer
from kyuura_engine.decisions import QUIZ_ANSWER, QUIZ_ATTACK, QUIZ_CARD, SELECT_ATTACK
from kyuura_engine.deck import deck_problems
from kyuura_engine.effects import current_form, form_def
from tests.helpers import (
    BLAINES_QUIZ_3,
    CLEFAIRY,
    DITTO,
    ERIKAS_EXEGGCUTE,
    EXEGGCUTE,
    EXEGGUTOR,
    FIGHTING,
    GRASS,
    HITMONCHAN,
    RATTATA,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems
from tests.release_catalog import cards_after

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "exeggutor-bilingual-names-v0.131.md"
TARGETS = ("PR1-075", "PR1-077")
PROMO, PROMO_B = TARGETS
EXEGGUTOR_SI = "SI-013"  # ナッシー（サザンアイランド）
ERIKAS_EXEGGUTOR = "PMCG5-013"  # エリカのナッシー（名前の前に別の言葉。別の名前）
EXEGGCUTE_NEO = "neo4-049"  # タマタマ（neo 第4弾）
DARK_EXEGGUTOR = "neo4-056"  # わるいナッシー（タマタマから進化。別の名前）
PONYTA_STOMP = ("PMCG2-019", 0)  # ギャロップのふみつけ（同じ処理の型・値）
UNOWN_N = "PF2-001"  # アンノーン[N]（名前に角かっこのあるほかのカード）
SLOT_GAME = "neo1-090"
BLAINES_QUIZ_1 = "GD5-016"
PRINTED_NAME, PRINTED_ATTACK = "ナッシー［Exeggutor］", "ふみつけ[Stomp]"
SOURCE = "kyuura-engine user specification docs/exeggutor-bilingual-names-v0.131.md#3"


def mon(card, energy=(), **extra):
    return {"card": card, "energy": list(energy), **extra}


def board(active, opponent=None, *, bench=(), opponent_bench=(RATTATA,), hand=(), opponent_hand=(), deck=None, opponent_deck=None, turn=5):
    me = {"active": active, "bench": list(bench), "hand": list(hand)}
    them = {"active": opponent or mon(HITMONCHAN, (FIGHTING,)), "bench": list(opponent_bench), "hand": list(opponent_hand)}
    if deck is not None:
        me["deck"] = list(deck)
    if opponent_deck is not None:
        them["deck"] = list(opponent_deck)
    return build_test_state([me, them], turn_number=turn)


def play(state, command, answers=()):
    state = apply_kernel(state, command)
    for answer in answers:
        d = state.decision
        assert d is not None, "決定がない"
        state = apply_kernel(state, ResolveDecision(d.player, d.id, answer(d) if callable(answer) else tuple(answer)))
    return state


def events(state, since, kind):
    return [dict(e) for e in state.log[since:] if e["kind"] == kind]


def card_of(state, card_id, zone="hand", player=0):
    return next(uid for uid in getattr(state.players[player], zone) if state.cards[uid].card_id == card_id)


def audited(test, state):
    from kyuura_engine import check_invariants

    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def deck(cards):
    """``cards`` に基本エネルギー（草）を足して 60 枚にしたデッキ。"""
    return [*cards, *[GRASS] * (60 - len(cards))]


def same_name_problems(cards):
    return [p for p in deck_problems(deck(cards)) if p.startswith("TOO_MANY_COPIES")]


class RegistrationTest(unittest.TestCase):
    def setUp(self):
        self.pool = load_card_pool()

    def test_pool_and_counts(self):
        extract = read_extract()
        self.assertEqual(extract["pool_v0_131"], list(TARGETS))
        self.assertEqual(cards_after(extract, "0.130"), set(TARGETS))
        self.assertEqual(extract["source"]["commit"], "71d1728938fb4c8fefde9b82779cdef74beb612d")  # 写しの元は上げていない
        self.assertLessEqual(set(TARGETS), self.pool.playable_ids)
        self.assertEqual(len(self.pool.playable_ids), 1372)

    def test_attack_reuses_coin_bonus_damage_with_the_printed_full_text(self):
        """ふみつけ（無無・20+）: 「おもて」なら 10 を追加する ``CoinBonusDamage(10)``。照合と処理に使う文面は印刷の全文（英語の文を含む。転記の元のまま）。2 枚は同じ登録の値。
        処理の型・値はギャロップのふみつけと同じ（通常のナッシーのワザ（テレポート・たまなげMAX）ではない）。"""
        cards = {card: next(c for c in read_extract()["cards"] if c["id"] == card) for card in TARGETS}
        entries = [E.DEFAULT_EFFECTS.attack_entry(card, 0) for card in TARGETS]
        self.assertIs(entries[0], entries[1])
        entry = entries[0]
        printed = cards[PROMO]["pokemon"]["attacks"][0]
        self.assertEqual(cards[PROMO]["pokemon"], cards[PROMO_B]["pokemon"])
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), ("ふみつけ", printed["text"]["ja"], printed["text"]["ja"], "kyuura data/cards.json"))
        self.assertEqual(entry.text_ja, E.STOMP_BILINGUAL_TEXT)
        self.assertEqual(entry.effect, E.CoinBonusDamage(10))
        self.assertEqual(entry.effect, E.DEFAULT_EFFECTS.attack_entry(*PONYTA_STOMP).effect)
        self.assertEqual((printed["cost"], printed["damage"]), (["colorless", "colorless"], {"base": 20, "modifier": "+", "display": "20+"}))
        self.assertEqual([a.name_ja for a in self.pool.get(EXEGGUTOR).attacks], ["テレポート", "たまなげMAX"])
        self.assertEqual(len(E.DEFAULT_EFFECTS.attack_keys()), 1755)

    def test_type_check_reads_the_whole_text_and_numbers(self):
        """``CoinBonusDamage`` の日英併記の書き方の照らしは全文と数（基本となるダメージ・追加・英語の文の数も）。登録の値・ダメージの目安が違えば受け付けない。"""
        attack = self.pool.get(PROMO).attacks[0]
        self.assertEqual(E.CoinBonusDamage(10).check(attack), [])
        self.assertNotEqual(E.CoinBonusDamage(20).check(attack), [])
        self.assertNotEqual(E.CoinBonusDamage(10).check(dataclasses.replace(attack, damage=30)), [])
        self.assertNotEqual(E.CoinBonusDamage(10).check(dataclasses.replace(attack, text_ja=attack.text_ja.replace("plus 10", "plus 20"))), [])
        self.assertNotEqual(E.CoinBonusDamage(10).check(dataclasses.replace(attack, text_ja=attack.text_ja.split(" (")[0])), [])  # 英語の文を落とした別の文面
        self.assertNotEqual(E.CoinBonusDamage(10).check(dataclasses.replace(attack, text_ja=attack.text_ja.replace("「うら」", "「おもて」"))), [])
        # 既存の書き方の照らしは変わらない
        self.assertEqual(E.CoinBonusDamage(10).check(self.pool.get(PONYTA_STOMP[0]).attacks[0]), [])

    def test_user_specified_name_records(self):
        """対象ごとの記録: 対象 2 枚だけ・欄（名前・進化元・ワザ名）と写しの値（原文）と判定に使う値・表示用の英語の併記・範囲・置きかえないもの・論点。印刷の確認は PR1-077 だけ
        （PR1-075 は未確認と書く）。ほかの利用者の指定の記録と重ならない。"""
        self.assertEqual(set(E.USER_SPECIFIED_NAMES), {"PR1-075/name", "PR1-077/name"})
        self.assertFalse({key.split("/")[0] for key in E.USER_SPECIFIED_NAMES}
                         & {key.split("/")[0] for key in (*E.USER_SIMPLIFICATIONS, *E.USER_SPECIFIED_REFERENCES, *E.USER_SPECIFIED_RULES)})
        for card in TARGETS:
            spec = E.USER_SPECIFIED_NAMES[f"{card}/name"]
            self.assertEqual((spec.rule, spec.specified_by, spec.specified_on, spec.kyuura_issue), (E.USER_BILINGUAL_NAME_JAPANESE, "user", "2026-11-01", "UQ-BILINGUAL-NAME-GLOSS"))
            self.assertEqual([(f.field, f.copy_value, f.rule_value, f.gloss) for f in spec.fields],
                             [("name.ja", PRINTED_NAME, "ナッシー", "Exeggutor"), ("pokemon.evolves_from.ja", "タマタマ", "タマタマ", "Exeggcute"),
                              ("pokemon.attacks[0].name.ja", PRINTED_ATTACK, "ふみつけ", "Stomp")])
            self.assertIn("公式の裁定", spec.not_recorded_as)
            self.assertIn("転記の訂正", spec.not_recorded_as)
            self.assertIn("HP", spec.not_changed)
            self.assertIn(f"「{spec.instruction}」", DOC.read_text(encoding="utf-8"))
        self.assertEqual(E.USER_SPECIFIED_NAMES["PR1-077/name"].print_check, "IMG-PR1-077")
        self.assertIn("未確認", E.USER_SPECIFIED_NAMES["PR1-075/name"].print_check)
        self.assertNotIn("IMG-", E.USER_SPECIFIED_NAMES["PR1-075/name"].print_check + "".join(f.printed for f in E.USER_SPECIFIED_NAMES["PR1-075/name"].fields))

    def test_adoption_and_research_records(self):
        """採用の記録は id ごと（文面の根拠は印刷の文面・名前は user_specified_name。転記の訂正 user_name_correction ではない・name_ja は写しの値）。研究の対応表は、ワザを
        adopted_printed_text、名前を user_specified_names に別に挙げ、UQ-BILINGUAL-NAME-GLOSS の 6 件の事例を user_specified_name で処理する（解決済みにしない）。"""
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        for card in TARGETS:
            record = sources[card]
            self.assertEqual((record["name_ja"], record["play_text"], record["user_specified_name"], record["kyuura_records"]),
                             (PRINTED_NAME, {"attack/0": "kyuura_printed_text"}, {"name": SOURCE}, ["UQ-BILINGUAL-NAME-GLOSS"]))
            self.assertNotIn("user_name_correction", record)
            self.assertIn(f"{card}/attack/0", links["latest_descriptions"]["adopted_printed_text"])
        self.assertIn("IMG-PR1-077", sources[PROMO_B]["notes"])
        self.assertIn("印刷は未確認", sources[PROMO]["notes"])
        self.assertEqual(links["latest_descriptions"]["user_specified_names"], {"PR1-075/name": SOURCE, "PR1-077/name": SOURCE})
        cases = [c for c in links["kyuura_cases_without_engine_ruling"]["cases"] if c["kyuura_issue"] == "UQ-BILINGUAL-NAME-GLOSS"]
        self.assertEqual({c["card_id"]: c["engine"] for c in cases},
                         {"PR1-075": {"user_specified_name": ["PR1-075/name"]}, "PR1-077": {"user_specified_name": ["PR1-077/name"]},
                          **{card: {"user_specified_name": ["PR1-075/name", "PR1-077/name"]} for card in ("PMCG2-012", "SI-013", "neo1-090", "PMCG6-082")}})
        self.assertEqual(links["counts"]["kyuura_issues"], 90)
        self.assertFalse(set(links["latest_descriptions"]["user_specified_names"]) & set(links["latest_descriptions"]["user_specified_rules"]))

    def test_no_card_id_branches_in_engine_or_resolution(self):
        sources = [ROOT / "kyuura_engine" / "engine.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]
        for path in sources:
            text = path.read_text(encoding="utf-8")
            for card in TARGETS:
                self.assertNotIn(card, text, path.name)


class OriginalTextTest(unittest.TestCase):
    def setUp(self):
        self.pool = load_card_pool()

    def test_rule_names_and_original_text_are_separate(self):
        """判定に使う名前・ワザ名は日本語の部分、原文（写しの値）は ``printed_name_ja`` に残る。写し（kyuura の値）とワザの説明（英語の文を含む）は書き換えない。名前以外の性能は
        それぞれのカードの写しの値（通常のナッシーに置きかえない）。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        for card in TARGETS:
            definition = self.pool.get(card)
            self.assertEqual((definition.name_ja, definition.printed_name_ja, definition.evolves_from), ("ナッシー", PRINTED_NAME, "タマタマ"))
            self.assertEqual((definition.attacks[0].name_ja, definition.attacks[0].printed_name_ja), ("ふみつけ", PRINTED_ATTACK))
            self.assertEqual(definition.attacks[0].text_ja, cards[card]["pokemon"]["attacks"][0]["text"]["ja"])
            self.assertIn("Flip a coin", definition.attacks[0].text_ja)
            self.assertEqual((cards[card]["name"]["ja"], cards[card]["pokemon"]["attacks"][0]["name"]["ja"]), (PRINTED_NAME, PRINTED_ATTACK))
            self.assertEqual((definition.hp, definition.retreat_cost, definition.stage), (80, 2, "stage1"))
            self.assertEqual(definition.dex, ())  # 写しにない（data_gaps）。補わない
        # 通常のナッシー（にげる 3・ワザ 2 つ）とは別の性能
        self.assertEqual((self.pool.get(EXEGGUTOR).retreat_cost, len(self.pool.get(EXEGGUTOR).attacks)), (3, 2))

    def test_other_cards_keep_their_names(self):
        """ほかのカード（名前に角かっこのあるアンノーン[N] などをふくむ）は、名前・ワザ名が写しの値のままで、原文の欄を持たない（一律の正規化ではない）。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        changed = []
        for card_id, record in cards.items():
            definition = self.pool.get(card_id)
            names = [(definition.name_ja, record["name"]["ja"])]
            names += [(a.name_ja, w["name"]["ja"]) for a, w in zip(definition.attacks, (record.get("pokemon") or {}).get("attacks") or ())]
            if any(mine != theirs for mine, theirs in names) or definition.printed_name_ja is not None or any(a.printed_name_ja for a in definition.attacks):
                changed.append(card_id)
        self.assertEqual(changed, list(TARGETS))
        self.assertEqual(self.pool.get(UNOWN_N).name_ja, "アンノーン[N]")

    def test_record_is_not_applied_when_the_copy_differs(self):
        """写しの値が記録の写しの値と違えば（写しが変わった）、名前を置きかえず、カードを未対応にする（黙って別の値で判定しない）。"""
        record = copy.deepcopy(next(c for c in read_extract()["cards"] if c["id"] == PROMO))
        record["name"]["ja"] = "ナッシー[Exeggutor]"
        definition = classify_record(record)
        self.assertFalse(definition.supported)
        self.assertEqual((definition.name_ja, definition.printed_name_ja), ("ナッシー[Exeggutor]", None))
        self.assertTrue(any("利用者が指定した名前の扱い" in reason for reason in definition.unsupported_reasons))
        # 記録のない別の id のカードには当てはめない
        record = copy.deepcopy(next(c for c in read_extract()["cards"] if c["id"] == PROMO))
        record["id"] = "PR1-999"
        self.assertEqual(classify_record(record).name_ja, PRINTED_NAME)

    def test_observation_shows_japanese_name_and_original_separately(self):
        """観測の場のポケモン・ワザは、提示する日本語名（``name_ja``）と原文（``printed_name_ja``）を別の欄に書く。ほかのポケモンには原文の欄を書かない（v0.130 までの形）。"""
        state = board(mon(PROMO, (GRASS, GRASS), evolved_from=EXEGGCUTE), mon(EXEGGUTOR, (GRASS,), evolved_from=EXEGGCUTE))
        view = observe(state, 0)
        mine = view["players"][0]["active"]
        self.assertEqual((mine["name_ja"], mine["printed_name_ja"]), ("ナッシー", PRINTED_NAME))
        self.assertEqual([(a["name_ja"], a["printed_name_ja"]) for a in mine["attacks"]], [("ふみつけ", PRINTED_ATTACK)])
        self.assertEqual((mine["form"]["name_ja"], mine["form"]["printed_name_ja"]), ("ナッシー", PRINTED_NAME))
        theirs = observe(state, 1)["players"][0]["active"]
        self.assertEqual(theirs["printed_name_ja"], PRINTED_NAME)  # 場のカードはおもて（公開の情報）
        other = view["players"][1]["active"]
        self.assertEqual(other["name_ja"], "ナッシー")
        self.assertNotIn("printed_name_ja", other)
        self.assertTrue(all("printed_name_ja" not in a for a in other["attacks"]))
        audited(self, state)


class DeckTest(unittest.TestCase):
    def test_four_with_normal_exeggutor_are_accepted_and_five_rejected(self):
        """デッキの同じ名前（p.308）: 通常のナッシー（PMCG2-012・SI-013）と対象 2 枚を合わせて「ナッシー」4 枚まで。5 枚目は拒否する。"""
        self.assertEqual(same_name_problems([EXEGGUTOR, EXEGGUTOR_SI, PROMO, PROMO_B]), [])
        self.assertEqual(same_name_problems([PROMO, PROMO, PROMO_B, PROMO_B]), [])
        for five in ([EXEGGUTOR, EXEGGUTOR_SI, PROMO, PROMO_B, PROMO], [EXEGGUTOR, PROMO, PROMO, PROMO_B, PROMO_B], [PROMO] * 3 + [PROMO_B] * 2,
                     [EXEGGUTOR] * 4 + [PROMO_B]):
            self.assertEqual(same_name_problems(five), ["TOO_MANY_COPIES: 「ナッシー」が 5 枚（同じ名前は 4 枚まで）"], five)
        # 名前の前に別の言葉のつくナッシーは別の名前（数えない）
        self.assertEqual(same_name_problems([EXEGGUTOR, EXEGGUTOR_SI, PROMO, PROMO_B, ERIKAS_EXEGGUTOR, DARK_EXEGGUTOR]), [])

    def test_whole_deck_with_the_promos_is_valid(self):
        cards = [EXEGGCUTE] * 4 + [PROMO, PROMO_B, EXEGGUTOR, EXEGGUTOR_SI]
        self.assertEqual(deck_problems(deck(cards)), [])


class EvolutionTest(unittest.TestCase):
    def evolve(self, below, card=PROMO):
        state = board(mon(HITMONCHAN, (FIGHTING,)), bench=(mon(below, played_turn=1),), hand=(card,))
        target = state.players[0].bench[0].pokemon_id
        return state, EvolvePokemon(0, card_of(state, card), target)

    def test_evolves_from_exeggcute(self):
        """進化元「タマタマ」（2 枚のタマタマ PMCG2-006・neo4-049）から進化できる。進化したあとの名前は「ナッシー」、ワザはこのカードのふみつけ。"""
        for below in (EXEGGCUTE, EXEGGCUTE_NEO):
            for card in TARGETS:
                state, command = self.evolve(below, card)
                after = apply_kernel(state, command)
                evolved = after.players[0].bench[0]
                self.assertEqual(after.cards[evolved.card].card_id, card)
                self.assertEqual(form_def(after, evolved).name_ja, "ナッシー")
                self.assertEqual([a.name_ja for a in form_def(after, evolved).attacks], ["ふみつけ"])
                audited(self, after)

    def test_unrelated_names_are_rejected(self):
        """名前の違うポケモン（エリカのタマタマ・コラッタ）からは進化できない（状態を変えない）。"""
        for below in (ERIKAS_EXEGGCUTE, RATTATA):
            state, command = self.evolve(below)
            with self.assertRaises(IllegalActionError) as raised:
                apply_kernel(state, command)
            self.assertEqual(raised.exception.code, "EVOLUTION_NAME_MISMATCH")

    def test_named_deck_evolution_query_reads_the_rule_name(self):
        """名前を指定して山札から進化カードを選ぶ共通の処理（``self_deck_evolution_cards`` の ``name``・``evolves_from``）は、判定に使う名前「ナッシー」・進化元「タマタマ」で選ぶ。"""
        state = board(mon(EXEGGCUTE, played_turn=1), deck=[PROMO, PROMO_B, EXEGGUTOR, ERIKAS_EXEGGUTOR, RATTATA])
        exeggcute = state.players[0].active
        named = E.self_deck_evolution_cards(state, 0, exeggcute, name="ナッシー")
        self.assertEqual(sorted(state.cards[uid].card_id for uid in named), sorted([PROMO, PROMO_B, EXEGGUTOR]))
        from_exeggcute = E.self_deck_evolution_cards(state, 0, exeggcute, evolves_from="タマタマ")
        self.assertEqual(sorted(state.cards[uid].card_id for uid in from_exeggcute), sorted([PROMO, PROMO_B, EXEGGUTOR]))


class SameNameEffectTest(unittest.TestCase):
    def test_slot_game_takes_exeggutor_and_the_promo_as_the_same_name(self):
        """スロットゲーム（neo1-090）: 山札の上 3 枚の「同じ名前のカード」に、通常のナッシーと対象のカードが当たり、2 枚とも手札に加える。名前の違うカードは山札にもどす。"""
        for pair in ((EXEGGUTOR, PROMO), (PROMO, PROMO_B), (EXEGGUTOR_SI, PROMO_B)):
            state = board(mon(HITMONCHAN, (FIGHTING,)), hand=(SLOT_GAME,), deck=[*pair, RATTATA])
            since = len(state.log)
            after = apply_kernel(state, PlayTrainer(0, card_of(state, SLOT_GAME)))
            self.assertEqual(sorted(after.cards[uid].card_id for uid in after.players[0].hand), sorted(pair), pair)
            self.assertEqual([after.cards[uid].card_id for uid in after.players[0].deck], [RATTATA])
            (revealed,) = events(after, since, "reveal_deck_top")
            self.assertEqual(sorted(after.cards[uid].card_id for uid in revealed["cards"]), sorted([*pair, RATTATA]))  # 見せた 3 枚（公開）
            self.assertEqual(sorted(after.cards[e["card"]].card_id for e in events(after, since, "reveal_from_deck")), sorted(pair))
            audited(self, after)
        # 名前の前に別の言葉のつくナッシーとは同じ名前ではない
        state = board(mon(HITMONCHAN, (FIGHTING,)), hand=(SLOT_GAME,), deck=[ERIKAS_EXEGGUTOR, PROMO, RATTATA])
        after = apply_kernel(state, PlayTrainer(0, card_of(state, SLOT_GAME)))
        self.assertEqual(list(after.players[0].hand), [])


class QuizTest(unittest.TestCase):
    def quiz(self, answer_name, *, card=PROMO):
        state = board(mon(HITMONCHAN, (FIGHTING,)), hand=(BLAINES_QUIZ_3, card), deck=[GRASS] * 10, opponent_deck=[GRASS] * 10)
        state = apply_kernel(state, PlayTrainer(0, card_of(state, BLAINES_QUIZ_3)))
        self.assertEqual(state.decision.kind, QUIZ_CARD)
        state = apply_kernel(state, ResolveDecision(0, state.decision.id, (card_of(state, card),)))
        self.assertEqual((state.decision.kind, state.decision.options), (QUIZ_ATTACK, tuple(range(len(load_card_pool().get(card).attacks)))))
        option = observe(state, 0)["decision"]["options"][0]
        state = apply_kernel(state, ResolveDecision(0, state.decision.id, (0,)))
        names = state.decision.context_value("names")
        waiting = state
        state = apply_kernel(state, ResolveDecision(1, state.decision.id, (names.index(answer_name),)))
        return waiting, state, option, names

    def test_quiz_3_hint_candidates_and_answer(self):
        """カツラのクイズ その3（PMCG6-082）: 伝えるワザ名は「ふみつけ」（日本語の部分）。答えの名前の候補に「ナッシー」があり、英語の併記の別の候補（「ナッシー［Exeggutor］」）は
        ない。「ナッシー」と答えれば正解（相手が 3 枚引く）、「エリカのナッシー」なら正解でない（使ったプレイヤーが 3 枚引く）。2 枚とも同じ。"""
        for card in TARGETS:
            waiting, state, option, names = self.quiz("ナッシー", card=card)
            self.assertEqual(waiting.decision.kind, QUIZ_ANSWER)
            self.assertEqual(waiting.decision.context_value("hint"), "ふみつけ")
            self.assertEqual(option["attack_name"], "ふみつけ")
            self.assertEqual(events(waiting, 0, "quiz_hint")[-1]["attack_name"], "ふみつけ")
            self.assertIn("ナッシー", names)
            self.assertFalse([name for name in names if "Exeggutor" in name or "［" in name])
            reveal = events(state, 0, "quiz_reveal")[-1]
            self.assertEqual((reveal["name"], reveal["correct"], reveal["card_id"]), ("ナッシー", True, card))
            self.assertEqual((len(state.players[1].hand), len(state.players[0].hand)), (3, 1))
            audited(self, state)
        _, wrong, _, _ = self.quiz("エリカのナッシー")
        self.assertFalse(events(wrong, 0, "quiz_reveal")[-1]["correct"])
        self.assertEqual((len(wrong.players[1].hand), len(wrong.players[0].hand)), (0, 4))

    def test_quiz_3_normal_exeggutor_answer_is_unchanged(self):
        """通常のナッシーを置いたときも「ナッシー」が正解（候補の名前は 1 つ）。"""
        _, state, _, names = self.quiz("ナッシー", card=EXEGGUTOR)
        self.assertTrue(events(state, 0, "quiz_reveal")[-1]["correct"])
        self.assertEqual(names.count("ナッシー"), 1)

    def test_quiz_1_stops_because_the_dex_number_is_missing(self):
        """カツラのクイズ その1（GD5-016）: 対象 2 枚は写しに全国図鑑番号がない（data_gaps）ので、選べるが選ぶと止める（既存の未対応。名前から補わない）。"""
        state = board(mon(HITMONCHAN, (FIGHTING,)), hand=(BLAINES_QUIZ_1, PROMO, EXEGGUTOR), deck=[GRASS] * 10, opponent_deck=[GRASS] * 10)
        state = apply_kernel(state, PlayTrainer(0, card_of(state, BLAINES_QUIZ_1)))
        blocked = E.quiz_height_blocked(state, E.quiz_height_candidates(state, E.TrainerUse(0, state.trainer_in_use.card, BLAINES_QUIZ_1)))
        self.assertEqual({state.cards[uid].card_id: code for uid, (code, _) in blocked.items()}, {PROMO: E.QUIZ_HEIGHT_WITHOUT_DEX_CODE})


class StompTest(unittest.TestCase):
    def test_heads_and_tails(self):
        """ふみつけ: 「おもて」なら 20+10、「うら」なら 20（弱点・抵抗力のない相手）。ワザのログの名前は「ふみつけ」。2 枚とも同じ。"""
        for card in TARGETS:
            for side, damage in ((H, 30), (T, 20)):
                state = with_coin_results(board(mon(card, (GRASS, WATER), evolved_from=EXEGGCUTE), mon(RATTATA)), side)
                since = len(state.log)
                after = apply_kernel(state, UseAttack(0, 0))
                self.assertEqual(events(after, since, "attack")[0]["attack"], "ふみつけ")
                self.assertEqual([e["amount"] for e in events(after, since, "damage")], [damage])
                audited(self, after)

    def test_weakness_and_energy_boundary(self):
        """必要なエネルギーは無色 2 個（1 枚では使えない）。弱点（草が弱点のニョロモ）は基本となるダメージのあと（30 × 2）。"""
        with self.assertRaises(IllegalActionError) as raised:
            apply_kernel(board(mon(PROMO, (GRASS,), evolved_from=EXEGGCUTE)), UseAttack(0, 0))
        self.assertEqual(raised.exception.code, "INSUFFICIENT_ENERGY")
        poliwag = "ES1-016"  # ニョロモ（HP 50・弱点 草）
        self.assertEqual(load_card_pool().get(poliwag).weakness.value, "grass")
        state = with_coin_results(board(mon(PROMO_B, (WATER, WATER), evolved_from=EXEGGCUTE), mon(poliwag)), H)
        since = len(state.log)
        after = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual([e["amount"] for e in events(after, since, "damage")], [60])


class CopyTransformTest(unittest.TestCase):
    def test_metronome_copies_stomp_from_the_promo(self):
        """ピッピの「ゆびをふる」で相手のナッシー[Exeggutor] のふみつけをまねる: 選ぶワザは「ふみつけ」（決定の観測は日本語名と原文を別の欄に書く）、まねたワザの供給元は対象のカードの
        ワザ（``PR1-075#0``）で、処理はその登録（「おもて」なら 30）。"""
        state = with_coin_results(board(mon(CLEFAIRY, (WATER, WATER, WATER)), mon(PROMO, (GRASS, GRASS), evolved_from=EXEGGCUTE)), H)
        since = len(state.log)
        waiting = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual(waiting.decision.kind, SELECT_ATTACK)
        self.assertEqual(observe(waiting, 0)["decision"]["options"][0]["attack"],
                         {"card_id": PROMO, "attack_index": 0, "name_ja": "ふみつけ", "printed_name_ja": PRINTED_ATTACK})
        after = play(waiting, ResolveDecision(0, waiting.decision.id, (0,)))
        (copied,) = events(after, since, "copy_attack")
        self.assertEqual((copied["copied"], copied["copied_attack"]), (f"{PROMO}#0", "ふみつけ"))
        self.assertEqual([e["effect"] for e in events(after, since, "coin_flip")], [f"{PROMO}#0"])
        self.assertEqual([e["amount"] for e in events(after, since, "damage")], [30])
        audited(self, after)

    def test_ditto_transforms_into_the_promo(self):
        """メタモンの［へんしん］: 相手のナッシー[Exeggutor] と同じカードとしてあつかい、名前は「ナッシー」（原文の欄は対象のカード）、ワザはそのカードのふみつけ（にげる 2・HP 80）。"""
        state = board(mon(DITTO, (WATER, WATER)), mon(PROMO_B, (GRASS,), evolved_from=EXEGGCUTE))
        ditto = state.players[0].active
        self.assertEqual((current_form(state, ditto).kind, form_def(state, ditto).name_ja, form_def(state, ditto).printed_name_ja), ("transform", "ナッシー", PRINTED_NAME))
        self.assertEqual([a.name_ja for a in form_def(state, ditto).attacks], ["ふみつけ"])
        view = observe(state, 0)["players"][0]["active"]
        self.assertEqual((view["form"]["card_id"], view["form"]["name_ja"], view["form"]["printed_name_ja"]), (PROMO_B, "ナッシー", PRINTED_NAME))
        after = apply_kernel(with_coin_results(state, T), UseAttack(0, 0))
        attack = [e for e in after.log if e["kind"] == "attack"][-1]
        self.assertEqual((attack["attack"], attack["card_id"], attack["route"]), ("ふみつけ", PROMO_B, "form"))
        self.assertEqual([e["amount"] for e in after.log if e["kind"] == "damage"][-1:], [20])
        audited(self, after)


class PersistenceTest(unittest.TestCase):
    def test_restored_state_judges_the_same(self):
        """保存と復元（pickle・deepcopy・clone）のあとも、進化（タマタマから）・名前・ワザ名・観測の欄が同じ。"""
        state = board(mon(HITMONCHAN, (FIGHTING,)), bench=(mon(EXEGGCUTE, played_turn=1), mon(ERIKAS_EXEGGCUTE, played_turn=1)), hand=(PROMO, PROMO_B))
        for restored in (pickle.loads(pickle.dumps(state)), copy.deepcopy(state), state.clone()):
            target, other = (p.pokemon_id for p in restored.players[0].bench)
            after = apply_kernel(restored, EvolvePokemon(0, card_of(restored, PROMO), target))
            self.assertEqual(form_def(after, after.players[0].bench[0]).name_ja, "ナッシー")
            with self.assertRaises(IllegalActionError):
                apply_kernel(restored, EvolvePokemon(0, card_of(restored, PROMO_B), other))
            self.assertEqual(observe(after, 0)["players"][0]["bench"][0]["printed_name_ja"], PRINTED_NAME)
            audited(self, after)
            self.assertEqual(pickle.loads(pickle.dumps(after)).card_def(after.players[0].bench[0].card).name_ja, "ナッシー")


if __name__ == "__main__":
    unittest.main()

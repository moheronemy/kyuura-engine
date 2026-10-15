"""v0.25: ポケモン育て屋さん（PMCG1-094）。最新の説明「このカードは、あなたが自分の場にいるポケモンを進化させるときにだけ、使える。そのポケモンの
上に「2進化カード」を直接のせ、1進化をとばして「2進化ポケモン」に進化させる。」（『ポケモンカードオフィシャルブック2000』p.259。
docs/pokemon-breeder-v0.25.md）。

規定と根拠（docs/pokemon-breeder-v0.25.md 3 章の BR1〜BR22）:

- 使うための条件（BR2・BR9）: 進化させるときにだけ使える。おたがいの最初の番は使えない（p.310 の進化の制限。p.259 の解説「対戦開始2回めの
  自分の番で」）。進化させられる組（自分の場の、その番の最初から場に出ていたたねポケモンと、手札の系統の合う 2 進化カード）がなければ使えない。
- 対象（BR3〜BR8）: 自分の場（バトル場・ベンチ）のたねポケモン。重ねるのは手札の 2 進化カード（1 進化カードは不可）。系統は、2 進化カードの
  「○○○○から進化」の 1 進化カード（写しのカードのデータ）の進化元の名前が、たねポケモンの名前（完全一致）。1 進化カードは要らない
  （p.259 の解説「1進化ポケモンカードをかなり減らして」）。
- 進化（BR11〜BR15）: 通常の進化と同じ手順（p.310。特殊状態・持続する効果・にげるの失敗の記録が消え、ダメージ・エネルギー・ついている
  トレーナーは受け継ぐ）。重なりはたねポケモン + 2 進化の 2 枚（p.319）。いちばん上の 2 進化カードの内容がそのポケモンを表す。
- 通常の進化（EvolvePokemon）では、たねポケモンに 2 進化カードを直接重ねられない（v0.4c の S2 のまま）。

kyuura の記録: kyuura（研究の基準 3f34908）に、このカードの照合の記録（CC-）・最新の説明（LD-）・p.259 のページの記録はない（報告事項。
research_links.json の engine_verified_without_kyuura_record）。p.88 の第4弾のゼニガメの解説（CC-PMCG4-018-P43。エンジンの記録の取り込み）に、
「ポケモン育て屋さん」で「わるいカメックス」に進化する例がある。

盤面を直接作るテスト（``build_test_state``。規定 1 か所ずつ）と、正式な対戦開始（``new_game``・60 枚・サイド 6 枚）から使う統合テスト
（v0.24 の ``trader`` の一時的なデッキで、デッキ B（フシギバナ・パラセクト）だけマサキ 2 枚をポケモン育て屋さん 2 枚に置き換えた ``breeder``。
tools/preset_deck_games.py）を分けている。
"""

from __future__ import annotations

import copy
import pickle
import re
import sys
import unittest
from collections import Counter
from pathlib import Path

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, PlayBasicToBench, PlayTrainer, PromoteActive, ResolveDecision, TakePrize, UseAttack,
    UsePokemonPower, apply_command, check_invariants, preset_deck, state_to_dict,
)
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract, read_verification
from kyuura_engine.decisions import SELECT_EVOLUTION_CARD, SELECT_POKEMON
from kyuura_engine.effects import DEFAULT_EFFECTS, EvolveBasicToStage2
from kyuura_engine.errors import UnsupportedError
from kyuura_engine.evolution import skipped_stage1_basic
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    BEEDRILL, BILL, BLASTOISE, BULBASAUR, CHARIZARD, FIRE, GIOVANNIS_MACHAMP, GIOVANNIS_MACHOP, GRASS, GRIMER, IVYSAUR,
    MACHAMP, MACHOKE, MACHOP, MUK, PLUSPOWER, POKEMON_BREEDER, PONYTA, ROCKET_SQUIRTLE, SQUIRTLE, STARYU, VENUSAUR, WATER, WEEDLE, build_test_state,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_computer_search_v0_22 import Base, by_id, snapshot

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import preset_deck_games as driver  # noqa: E402

LATEST = (
    "このカードは、あなたが自分の場にいるポケモンを進化させるときにだけ、使える。そのポケモンの上に「2進化カード」を直接のせ、1進化を"
    "とばして「2進化ポケモン」に進化させる。"
)
PRINTED = "ポケモンを進化させるときに使う。2進化カードをいきなりつけることができる。"
TURN = 5


def board(active=BULBASAUR, bench=(), hand=(VENUSAUR,), *, turn_number=TURN, pool=None, their_active=STARYU, their_hand=(WATER,),
          their_deck=(WATER, WATER, WATER)):
    """自分（プレイヤー 0）の番の MAIN。手札の先頭がポケモン育て屋さん。"""
    return build_test_state([
        {"active": active, "bench": list(bench), "hand": [POKEMON_BREEDER, *hand], "deck": [WATER, FIRE, GRASS]},
        {"active": their_active, "hand": list(their_hand), "deck": list(their_deck)},
    ], turn_number=turn_number, pool=pool)


def without_card(extract, card_id):
    """写しから 1 枚を除いた写し（テスト専用。カードの組からも除く）。"""
    pools = {k: [c for c in v if c != card_id] for k, v in extract.items() if k.startswith("pool_") or k == "reference_only"}
    return {**extract, **pools, "cards": [c for c in extract["cards"] if c["id"] != card_id]}


def pokemon_of(state, player, card_id):
    return [pk for pk in state.players[player].in_play() if state.cards[pk.card].card_id == card_id]


class RegistrationTest(unittest.TestCase):
    def test_entry_follows_the_verified_latest_description(self):
        """登録は p.259 の最新の説明（処理の根拠）と、kyuura の写しの印刷の文面（照合用）。照合の記録と同じ（BR1）。"""
        entry = DEFAULT_EFFECTS.trainer_entry(POKEMON_BREEDER)
        self.assertIsInstance(entry.effect, EvolveBasicToStage2)
        self.assertTrue(entry.effect.skips_stage1_evolution)
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), ("ポケモン育て屋さん", PRINTED, LATEST, "P43 p.259"))
        record = read_verification()["cards"][POKEMON_BREEDER]
        self.assertEqual((record["page"], record["card_image_text_ja"], record["latest_description_ja"]), (259, PRINTED, LATEST))
        self.assertEqual(read_extract()["pool_v0_25"], [POKEMON_BREEDER])
        self.assertTrue(load_card_pool().is_playable(POKEMON_BREEDER))

    def test_no_card_specific_branch_in_the_engine(self):
        """engine.py・resolution/ にこのカードの id・実装の名前での分岐はない（不変条件はトレーナーの実装の印 skips_stage1_evolution で見る）。"""
        sources = [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]
        for path in sources:
            text = path.read_text(encoding="utf-8")
            for word in (POKEMON_BREEDER, "EvolveBasicToStage2", "evolve_basic_to_stage2", "育て屋"):
                self.assertIsNone(re.search(re.escape(word), text), (path.name, word))


class LineageTest(unittest.TestCase):
    """系統（BR6・BR7）: 2 進化カードの「○○○○から進化」の 1 進化カード（写しのカードのデータ）の進化元の名前で決める。名前の一部・形容詞で
    推測しない。写しに 1 進化カードがなければ確かめられない。"""

    def test_stage1_lineage_from_the_card_data(self):
        pool = load_card_pool()
        expected = {
            VENUSAUR: ("フシギソウ", ("フシギダネ",)),
            MACHAMP: ("ゴーリキー", ("ワンリキー",)),
            GIOVANNIS_MACHAMP: ("サカキのゴーリキー", ("サカキのワンリキー",)),
            BEEDRILL: ("コクーン", ("ビードル",)),
            BLASTOISE: ("カメール", ("ゼニガメ",)),
            CHARIZARD: ("リザード", ()),  # リザードは写しにない（参照カード。確かめられない）
        }
        for card_id, (stage1, basics) in expected.items():
            with self.subTest(card=card_id):
                definition = pool.get(card_id)
                self.assertEqual((definition.evolves_from, definition.stage1_evolves_from), (stage1, basics))
                self.assertEqual(skipped_stage1_basic(definition), basics[0] if basics else None)
        # 2 進化カード以外は持たない
        self.assertEqual(pool.get(MACHOKE).stage1_evolves_from, ())
        self.assertIsNone(skipped_stage1_basic(pool.get(MACHOKE)))
        self.assertIsNone(skipped_stage1_basic(pool.get(BULBASAUR)))

    def test_missing_or_conflicting_stage1_data_is_not_guessed(self):
        """写しに 1 進化カードがない・同じ名前の 1 進化カードで進化元が食い違うと、系統は決まらない（None）。"""
        extract = read_extract()
        self.assertIsNone(skipped_stage1_basic(pool_from_extract(without_card(extract, IVYSAUR)).get(VENUSAUR)))
        twin = copy.deepcopy(next(c for c in extract["cards"] if c["id"] == IVYSAUR))
        twin["id"] = "TEST-IVYSAUR-2"
        twin["pokemon"]["evolves_from"]["ja"] = "ヒトカゲ"
        conflicting = dict(extract, cards=[*extract["cards"], twin])
        definition = pool_from_extract(conflicting).get(VENUSAUR)
        self.assertEqual(definition.stage1_evolves_from, ("ヒトカゲ", "フシギダネ"))
        self.assertIsNone(skipped_stage1_basic(definition))


class UsableTest(Base):
    """使うための条件（BR2・BR9・BR10）。拒否してもカードは手札に残り、状態・乱数・ログは変わらない。"""

    def assert_cannot_use(self, state, code, error=None):
        card = state.players[0].hand[0]
        if error is None:
            self.assert_rejected(state, PlayTrainer(0, card), code)
        else:
            self.assert_rejected(state, PlayTrainer(0, card), code, error)
        self.assertIn(card, state.players[0].hand)
        self.assertIsNone(state.trainer_in_use)

    def test_usable_on_the_active_and_on_the_bench(self):
        """自分の場（バトル場・ベンチ）のたねポケモン（BR3）。"""
        for active, bench in ((BULBASAUR, ()), (STARYU, (BULBASAUR,))):
            with self.subTest(active=active):
                pending = self.play(board(active=active, bench=bench))
                self.assertEqual(pending.decision.options, tuple(pk.pokemon_id for pk in pokemon_of(pending, 0, BULBASAUR)))

    def test_first_turn_of_each_player(self):
        """おたがいの最初の番（1 番・2 番）は使えない（p.310 の進化の制限。BR9）。3 番からは使える。"""
        for turn in (1, 2):
            with self.subTest(turn=turn):
                state = board(turn_number=turn, bench=())
                if turn == 2:
                    state = build_test_state([
                        {"active": STARYU, "hand": [WATER], "deck": [WATER]},
                        {"active": BULBASAUR, "hand": [POKEMON_BREEDER, VENUSAUR], "deck": [WATER]},
                    ], turn_number=2, current_player=1)
                    card = state.players[1].hand[0]
                    self.assert_rejected(state, PlayTrainer(1, card), "FIRST_TURN_EVOLUTION")
                    continue
                self.assert_cannot_use(state, "FIRST_TURN_EVOLUTION")
        self.play(board(turn_number=3))

    def test_no_pair_cannot_use_it(self):
        """進化させられる組がなければ使えない（BR2）: 手札に 2 進化カードがない・1 進化カードだけ・たねポケモンがその番に場に出した・場のポケモンが
        1 進化ポケモン（1 進化を飛ばす相手ではない。BR4）。"""
        cases = {
            "2 進化カードがない": board(hand=(GRASS,)),
            "1 進化カードだけ": board(hand=(IVYSAUR,)),
            "1 進化ポケモンに 2 進化": build_test_state([
                {"active": {"card": IVYSAUR, "evolved_from": BULBASAUR, "evolved_turn": 3}, "hand": [POKEMON_BREEDER, VENUSAUR],
                 "deck": [WATER]},
                {"active": STARYU, "deck": [WATER]},
            ], turn_number=TURN),
            "その番に場に出したたねポケモン": build_test_state([
                {"active": STARYU, "bench": [{"card": BULBASAUR, "played_turn": TURN}], "hand": [POKEMON_BREEDER, VENUSAUR], "deck": [WATER]},
                {"active": STARYU, "deck": [WATER]},
            ], turn_number=TURN),
        }
        for name, state in cases.items():
            with self.subTest(case=name):
                self.assert_cannot_use(state, "NO_EVOLUTION_TARGET")

    def test_played_this_turn_by_command(self):
        """コマンドでベンチに出したたねポケモンは、その番には進化させられない（p.310。BR9）。前の番からいるたねポケモンは選べる。"""
        state = board(active=STARYU, bench=(BULBASAUR,), hand=(VENUSAUR, BULBASAUR))
        benched = apply_command(state, PlayBasicToBench(0, by_id(state, 0, "hand", BULBASAUR)[0]))
        pending = self.play(benched)
        old = [pk for pk in pokemon_of(benched, 0, BULBASAUR) if pk.played_turn < TURN]
        self.assertEqual(pending.decision.options, (old[0].pokemon_id,))

    def test_other_lineages_are_not_pairs(self):
        """系統が違えば組にならない（BR6）: フシギダネとカイリキー、通常のワンリキーとサカキのカイリキー、サカキのワンリキーと通常のカイリキー。
        名前の一部（「カイリキー」「ワンリキー」）・形容詞（「サカキの」）で合わせない。"""
        cases = ((BULBASAUR, MACHAMP), (MACHOP, GIOVANNIS_MACHAMP), (GIOVANNIS_MACHOP, MACHAMP))
        for basic, stage2 in cases:
            with self.subTest(basic=basic, stage2=stage2):
                self.assert_cannot_use(board(active=basic, hand=(stage2,)), "NO_EVOLUTION_TARGET")
        # 名前が同じ別のカード（第4弾のゼニガメ PMCG4-018）は、名前が同じなので同じ系統（p.88 の解説の例）
        for basic, stage2 in ((MACHOP, MACHAMP), (GIOVANNIS_MACHOP, GIOVANNIS_MACHAMP), (BULBASAUR, VENUSAUR), (WEEDLE, BEEDRILL),
                              (SQUIRTLE, BLASTOISE), (ROCKET_SQUIRTLE, BLASTOISE)):
            with self.subTest(basic=basic, stage2=stage2):
                pending = self.play(board(active=basic, hand=(stage2,)))
                self.assertEqual(pending.decision.kind, SELECT_POKEMON)

    def test_unknown_lineage_is_unsupported(self):
        """系統を写しで確かめられない（1 進化カードが写しにない）組だけなら、推測で使えることにも使えないことにもせず、UnsupportedError（BR7）。"""
        pool = pool_from_extract(without_card(read_extract(), IVYSAUR))
        self.assert_cannot_use(board(pool=pool), "UNSUPPORTED_EVOLUTION_LINEAGE", UnsupportedError)

    def test_hp_at_or_below_the_damage_is_unresolved(self):
        """進化したあとの HP がのっているダメージ以下になる組（v0.4a の H1。UNRESOLVED_EVOLUTION_HP）: それだけなら使う前に止める。ほかに
        進化させられる組があれば選べるが、その組を選ぶと止まり、決定は待ったまま（BR17）。今の写しのカードでは起こらないので、2 進化カードの
        HP を変えた写しで確かめる（テスト専用。盤面を直接作った）。"""
        extract = copy.deepcopy(read_extract())
        next(c for c in extract["cards"] if c["id"] == VENUSAUR)["pokemon"]["hp"] = 30
        pool = pool_from_extract(extract)
        only = board(active={"card": BULBASAUR, "damage": 30}, pool=pool)
        self.assert_cannot_use(only, "UNRESOLVED_EVOLUTION_HP", UnsupportedError)
        mixed = board(active={"card": BULBASAUR, "damage": 30}, bench=(BULBASAUR,), pool=pool)
        pending = self.play(mixed)
        damaged, fresh = (pk.pokemon_id for pk in pokemon_of(pending, 0, BULBASAUR))
        self.assertEqual(pending.decision.options, (damaged, fresh))
        self.assertEqual(pending.decision.context_value("unresolved_choices"), (damaged,))
        self.assert_rejected(pending, ResolveDecision(0, pending.decision.id, (damaged,)), "UNRESOLVED_EVOLUTION_HP", UnsupportedError)
        self.assertEqual(pending.decision.kind, SELECT_POKEMON)
        self.answer(self.answer(pending, (fresh,)), (pending.players[0].hand[0],))


class DecisionTest(Base):
    """段階 1（進化させるたねポケモン）・段階 2（重ねる手札の 2 進化カード）（BR16・BR18・BR19）。"""

    def setUp(self):
        self.state = board(active=BULBASAUR, bench=(MACHOP, STARYU, BULBASAUR), hand=(IVYSAUR, VENUSAUR, MACHAMP, GIOVANNIS_MACHAMP, VENUSAUR))
        self.card = self.state.players[0].hand[0]
        self.pending = self.play(self.state)

    def test_target_decision_shape(self):
        d = self.pending.decision
        expected = tuple(pk.pokemon_id for pk in self.pending.players[0].in_play()
                         if self.pending.cards[pk.card].card_id in (BULBASAUR, MACHOP))
        self.assertEqual((d.player, d.kind, d.resume, d.min_choices, d.max_choices), (0, SELECT_POKEMON, "trainer", 1, 1))
        self.assertEqual(d.options, expected)  # バトル場のフシギダネ・ベンチのワンリキー・ベンチのフシギダネ（場の並び）。ヒトデマンは選べない
        self.assertEqual(d.context_value("use"), (0, self.card, POKEMON_BREEDER))
        self.assertEqual(self.pending.trainer_in_use.card, self.card)

    def test_invalid_targets_keep_the_decision(self):
        """選べない場のポケモン（ヒトデマン・相手のポケモン）・カードの uid・0 匹・2 匹・相手の答えを拒否し、決定は待ったまま。"""
        d = self.pending.decision
        staryu = pokemon_of(self.pending, 0, STARYU)[0].pokemon_id
        theirs = self.pending.players[1].active.pokemon_id
        wrong = [((staryu,), "INVALID_CHOICE"), ((theirs,), "INVALID_CHOICE"), ((by_id(self.pending, 0, "hand", VENUSAUR)[0],), "INVALID_CHOICE"),
                 ((), "INVALID_CHOICE_COUNT"), (d.options[:2], "INVALID_CHOICE_COUNT")]
        for choices, code in wrong:
            with self.subTest(choices=choices):
                self.assert_rejected(self.pending, ResolveDecision(0, d.id, choices), code)
                self.assertEqual(self.pending.decision, d)
                self.assert_conserved(self.pending)
        self.assert_rejected(self.pending, ResolveDecision(1, d.id, d.options[:1]), "NOT_YOUR_DECISION")

    def test_card_decision_shape_and_invalid_cards(self):
        """フシギダネには手札のフシギバナ 2 枚（手札の並び）。1 進化カード・系統の違う 2 進化カード（カイリキー・サカキのカイリキー）・
        山札・使用中のこのカード・相手の手札・0 枚・2 枚・相手の答えを拒否し、決定は待ったまま。"""
        bulbasaur = pokemon_of(self.pending, 0, BULBASAUR)[0].pokemon_id
        choosing = self.answer(self.pending, (bulbasaur,))
        d = choosing.decision
        self.assertEqual((d.player, d.kind, d.resume, d.min_choices, d.max_choices), (0, SELECT_EVOLUTION_CARD, "trainer", 1, 1))
        self.assertEqual(d.context_value("target"), bulbasaur)
        self.assertEqual(d.options, tuple(by_id(choosing, 0, "hand", VENUSAUR)))
        wrong = [((by_id(choosing, 0, "hand", IVYSAUR)[0],), "INVALID_CHOICE"), ((by_id(choosing, 0, "hand", MACHAMP)[0],), "INVALID_CHOICE"),
                 ((by_id(choosing, 0, "hand", GIOVANNIS_MACHAMP)[0],), "INVALID_CHOICE"), ((choosing.players[0].deck[0],), "INVALID_CHOICE"),
                 ((self.card,), "INVALID_CHOICE"), ((choosing.players[1].hand[0],), "INVALID_CHOICE"), ((), "INVALID_CHOICE_COUNT"),
                 (d.options, "INVALID_CHOICE_COUNT")]
        for choices, code in wrong:
            with self.subTest(choices=choices):
                self.assert_rejected(choosing, ResolveDecision(0, d.id, choices), code)
                self.assertEqual(choosing.decision, d)
                self.assert_conserved(choosing)
        self.assert_rejected(choosing, ResolveDecision(1, d.id, d.options[:1]), "NOT_YOUR_DECISION")
        machop = pokemon_of(self.pending, 0, MACHOP)[0].pokemon_id
        self.assertEqual(self.answer(self.pending, (machop,)).decision.options, tuple(by_id(self.pending, 0, "hand", MACHAMP)))

    def test_pending_decisions_survive_copy_and_pickle(self):
        bulbasaur = pokemon_of(self.pending, 0, BULBASAUR)[0].pokemon_id
        choosing = self.answer(self.pending, (bulbasaur,))
        command = ResolveDecision(0, choosing.decision.id, (choosing.decision.options[1],))
        expected = snapshot(apply_command(choosing, command))
        for clone in (copy.deepcopy(choosing), pickle.loads(pickle.dumps(choosing))):
            self.assertEqual(snapshot(apply_command(clone, command)), expected)


class EvolutionResultTest(Base):
    """進化のあと（BR11〜BR15・BR18）。"""

    def evolve(self, state, target_card_id=BULBASAUR, stage2=VENUSAUR):
        pending = self.play(state)
        target = pokemon_of(pending, 0, target_card_id)[0]
        choosing = self.answer(pending, (target.pokemon_id,))
        card = by_id(choosing, 0, "hand", stage2)[0]
        return self.answer(choosing, (card,)), target.pokemon_id, card

    def test_stack_is_basic_and_stage2_and_everything_else_is_inherited(self):
        """重なりはたねポケモン + 2 進化の 2 枚。場のポケモンの番号・ダメージ・エネルギー・ついているトレーナー（効果と有効期限）・場に出た番は
        受け継ぎ、進化した番は今の番。1 進化カード（手札のフシギソウ）は使わない。このカードはトラッシュに置かれ、番は続く。"""
        state = board(active={"card": BULBASAUR, "damage": 20, "energy": [GRASS, GRASS], "trainers": [(PLUSPOWER, TURN)]},
                      hand=(IVYSAUR, VENUSAUR))
        before = state.players[0].active
        done, pid, card = self.evolve(state)
        after = done.players[0].active
        self.assertEqual(after.card, card)
        self.assertEqual(after.evolution_stack, (before.card,))
        self.assertEqual((after.pokemon_id, after.damage, after.energy, after.trainers, after.played_turn, after.evolved_turn),
                         (before.pokemon_id, 20, before.energy, before.trainers, before.played_turn, TURN))
        self.assertEqual(by_id(done, 0, "hand", IVYSAUR), by_id(state, 0, "hand", IVYSAUR))  # 1 進化カードは手札のまま
        self.assertEqual(Counter(done.cards[u].card_id for u in done.cards), Counter(state.cards[u].card_id for u in state.cards))
        self.assertIn(state.players[0].hand[0], done.players[0].discard)
        self.assertIsNone(done.trainer_in_use)
        self.assertEqual((done.phase.value, done.current_player, done.turn_number), ("main", 0, TURN))
        events = [dict(e) for e in done.log[len(state.log):]]
        self.assertEqual([e["kind"] for e in events], ["play_trainer", "evolve", "discard_trainer"])
        self.assertEqual(events[1], {"kind": "evolve", "turn": TURN, "player": 0, "pokemon_id": pid, "from_card": before.card,
                                     "from_card_id": BULBASAUR, "to_card": card, "to_card_id": VENUSAUR, "trainer_card": state.players[0].hand[0]})
        self.assertEqual(rng_fingerprint(done.rng), rng_fingerprint(state.rng))  # 乱数は使わない

    def test_bench_target(self):
        state = board(active=STARYU, bench=(STARYU, BULBASAUR))
        done, pid, card = self.evolve(state)
        evolved = done.players[0].bench[1]
        self.assertEqual((evolved.pokemon_id, evolved.card, done.cards[evolved.evolution_stack[0]].card_id), (pid, card, BULBASAUR))

    def test_special_conditions_and_retreat_failure_are_cleared(self):
        """特殊状態のたねポケモンも進化でき、特殊状態（どくとこんらん）・こんらんで「にげる」に失敗した記録は消える（p.322・v0.4a の R1。BR11）。"""
        state = board(active={"card": BULBASAUR, "poison": 10, "confusion": True, "retreat_failed_turn": TURN}, bench=(STARYU,))
        done, pid, _ = self.evolve(state)
        self.assertEqual(done.players[0].active.conditions.names(), ())
        self.assertIsNone(done.players[0].active.retreat_failed_turn)
        kinds = [(e["kind"], e.get("reason")) for e in done.log[len(state.log):]]
        self.assertEqual(kinds, [("play_trainer", None), ("evolve", None), ("special_conditions_removed", "evolve"),
                                 ("retreat_failure_cleared", "evolve"), ("discard_trainer", None)])

    def test_persistent_effects_are_removed(self):
        """ワザによる持続する効果は進化で消える（p.323。BR11）。自分の番に自分の持続する効果が残る盤面は自然な対戦では起こらないので、盤面を
        直接作った（ゼニガメの「からにこもる」の効果を今の番に置いた）。"""
        state = board(active={"card": SQUIRTLE, "prevent_damage": TURN}, hand=(BLASTOISE,))
        done, pid, _ = self.evolve(state, SQUIRTLE, BLASTOISE)
        self.assertEqual(done.players[0].active.persistent_effects, ())
        removed = [e for e in done.log[len(state.log):] if e["kind"] == "persistent_effect_removed"]
        self.assertEqual([(e["pokemon_id"], e["reason"]) for e in removed], [(pid, "evolve")])

    def test_rejections_and_answers_leave_the_given_state_unchanged(self):
        """渡した状態を変えない（Base.play・answer が確かめる）。同じ盤面・同じ操作なら同じ結果。"""
        results = [snapshot(self.evolve(board(bench=(BULBASAUR,)))[0]) for _ in range(2)]
        self.assertEqual(results[0], results[1])


class AfterEvolutionTest(Base):
    """進化したあと（BR12・BR14・BR15・BR18・BR19）。"""

    def evolved(self, state, target_card_id=BULBASAUR, stage2=VENUSAUR):
        pending = self.play(state)
        target = pokemon_of(pending, 0, target_card_id)[0]
        choosing = self.answer(pending, (target.pokemon_id,))
        return self.answer(choosing, (by_id(choosing, 0, "hand", stage2)[0],))

    def test_energy_trans_and_solar_beam(self):
        """いちばん上のフシギバナの特殊能力（エナジートランス）とワザ（ソーラービーム）を使える（p.310。BR14）。"""
        state = board(active={"card": BULBASAUR, "energy": [GRASS, GRASS]}, bench=({"card": BULBASAUR, "energy": [GRASS]},), hand=(VENUSAUR, GRASS))
        done = self.evolved(state)
        venusaur = done.players[0].active
        energy = done.players[0].bench[0].energy[0]
        moved = apply_command(done, UsePokemonPower(0, venusaur.pokemon_id, 0, energy=energy, source=done.players[0].bench[0].pokemon_id,
                                                    target=venusaur.pokemon_id))
        self.assertEqual(moved.log[-1]["kind"], "move_energy")
        attached = apply_command(moved, AttachEnergy(0, by_id(moved, 0, "hand", GRASS)[0], venusaur.card))
        self.assertEqual(len(attached.players[0].active.energy), 4)
        attacked = apply_command(attached, UseAttack(0, 0))
        attack = next(e for e in attacked.log[len(attached.log):] if e["kind"] == "attack")
        damage = next(e for e in attacked.log[len(attached.log):] if e["kind"] == "damage")
        self.assertEqual((attack["pokemon"], attack["attack"]), (venusaur.card, "ソーラービーム"))
        self.assertEqual((damage["player"], damage["pokemon"], damage["amount"]), (1, attached.players[1].active.card, 60))

    def test_new_power_follows_chemical_gas(self):
        """進化したあとの特殊能力は、いちばん上のカードで決まり、はたらいているかは問い合わせのたびに求める（v0.8）。相手の場に「かがくへんかガス」の
        ベトベトンがいれば、育て屋さんで進化させたフシギバナのエナジートランスは使えない（POWER_SUPPRESSED）。育て屋さん（トレーナー）は止まらない
        （v0.8 の G8）。"""
        state = board(active={"card": BULBASAUR, "energy": [GRASS]}, bench=({"card": BULBASAUR, "energy": [GRASS]},),
                      their_active={"card": MUK, "evolved_from": GRIMER})
        done = self.evolved(state)
        venusaur, source = done.players[0].active, done.players[0].bench[0]
        self.assert_rejected(done, UsePokemonPower(0, venusaur.pokemon_id, 0, energy=source.energy[0], source=source.pokemon_id,
                                                   target=venusaur.pokemon_id), "POWER_SUPPRESSED")

    def test_normal_evolution_still_cannot_skip_and_no_second_evolution(self):
        """通常の進化（EvolvePokemon）では、たねポケモンに 2 進化カードを直接重ねられない（v0.4c の S2。BR20）。育て屋さんで進化したポケモンは、
        その番にもう一度は進化させられない（BR19）。"""
        state = board(bench=(BULBASAUR,), hand=(VENUSAUR, VENUSAUR))
        bench_bulbasaur = state.players[0].bench[0]
        self.assert_rejected(state, EvolvePokemon(0, by_id(state, 0, "hand", VENUSAUR)[0], bench_bulbasaur.pokemon_id), "EVOLUTION_NAME_MISMATCH")
        done = self.evolved(state)
        self.assert_rejected(done, EvolvePokemon(0, by_id(done, 0, "hand", VENUSAUR)[0], done.players[0].active.pokemon_id),
                             "EVOLUTION_NAME_MISMATCH")

    def test_second_breeder_in_the_same_turn(self):
        """同じ番に 2 枚目を使える（別のたねポケモン）。進化したポケモンはもう対象にならない。"""
        state = board(bench=(BULBASAUR,), hand=(VENUSAUR, VENUSAUR, POKEMON_BREEDER))
        done = self.evolved(state)
        again = apply_command(done, PlayTrainer(0, by_id(done, 0, "hand", POKEMON_BREEDER)[0]))
        self.assertEqual(again.decision.options, (done.players[0].bench[0].pokemon_id,))

    def test_knock_out_trashes_both_cards(self):
        """1 進化を飛ばした 2 進化ポケモン（ビードル → スピアー）がきぜつしたら、重なった 2 枚とついているエネルギーをトラッシュする。サイドは 1 枚
        （p.313。BR15）。"""
        state = board(active={"card": WEEDLE, "damage": 30, "energy": [GRASS]}, bench=(STARYU,), hand=(BEEDRILL,),
                      their_active={"card": PONYTA, "energy": [FIRE, FIRE]}, their_deck=(WATER, WATER, WATER))
        done = self.evolved(state, WEEDLE, BEEDRILL)
        beedrill = done.players[0].active
        cards = {beedrill.card, *beedrill.evolution_stack, *beedrill.energy}
        turn6 = apply_command(done, EndTurn(0))
        hit = apply_command(turn6, UseAttack(1, 1))  # ほのおのしっぽ 30 × 2（弱点 炎）= 60。ダメージ 30 + 60 = 90 ≥ HP 80
        self.assertTrue(cards <= set(hit.players[0].discard))
        self.assertTrue(any(e["kind"] == "knock_out" and e["pokemon"] == beedrill.card for e in hit.log))
        self.assertEqual(hit.decision.kind, "take_prize")
        prize = apply_command(hit, TakePrize(1, 0))
        self.assertEqual(len(prize.players[1].prizes), len(hit.players[1].prizes) - 1)
        promoted = apply_command(prize, PromoteActive(0, prize.players[0].bench[0].card))
        self.assertEqual(check_invariants(promoted), [])


class InvariantTest(Base):
    """たねポケモン + 2 進化の重なりの不変条件（BR13・BR20）。通常の進化で作れない重なりは、育て屋さんの進化のログ（evolve の trainer_card）が
    なければ認めない。"""

    def breeder_state(self):
        state = board(hand=(VENUSAUR, MACHOP, BILL))
        pending = self.play(state)
        choosing = self.answer(pending, (pending.players[0].active.pokemon_id,))
        return self.answer(choosing, (choosing.decision.options[0],))

    def test_hand_built_skip_stack_without_the_log_is_rejected(self):
        state = build_test_state([
            {"active": {"card": VENUSAUR, "evolved_from": BULBASAUR, "evolved_turn": 3}, "deck": [WATER]},
            {"active": STARYU, "deck": [WATER]},
        ], turn_number=TURN)
        self.assertTrue(any("重なりが正しくない" in p and "trainer_card" in p for p in check_invariants(state)), check_invariants(state))

    def test_edited_logs_and_stacks_are_detected(self):
        done = self.breeder_state()
        self.assertEqual(check_invariants(done), [])
        index = next(i for i, e in enumerate(done.log) if e["kind"] == "evolve")

        def with_event(**changes):
            broken = copy.deepcopy(done)
            event = {k: v for k, v in dict(broken.log[index]).items() if v is not None}
            event.update(changes)
            event = {k: v for k, v in event.items() if v is not None}
            broken.log = (*broken.log[:index], type(broken.log[index])(event), *broken.log[index + 1:])
            return check_invariants(broken)

        # trainer_card のない 1 進化を飛ばした進化・1 進化を飛ばさないトレーナー（マサキ）・相手のカード
        self.assertTrue(any("trainer_card" in p for p in with_event(trainer_card=None)))
        self.assertTrue(any("1 進化を飛ばして進化させるトレーナーではない" in p
                            for p in with_event(trainer_card=by_id(done, 0, "hand", BILL)[0])))
        self.assertTrue(any("持ち主 0 のカードではない" in p for p in with_event(trainer_card=done.players[1].hand[0])))
        swapped = copy.deepcopy(done)
        machop = by_id(swapped, 0, "hand", MACHOP)[0]
        bulbasaur = swapped.players[0].active.evolution_stack[0]
        swapped.players[0].active.evolution_stack = (machop,)
        swapped.players[0].hand[swapped.players[0].hand.index(machop)] = bulbasaur
        self.assertTrue(any("重なりが正しくない" in p for p in check_invariants(swapped)), check_invariants(swapped))

    def test_serialization_and_log_audit(self):
        """書き出しは形式 9 のまま（重なりは今までの項目）。書き出しの監査が通る。"""
        done = self.breeder_state()
        self.assertEqual(serialization_problems(done), [])
        data = state_to_dict(done, format_version=9)
        active = data["players"][0]["active"]
        self.assertEqual([entry["card"] for entry in active["evolution_stack"]], list(done.players[0].active.evolution_stack))
        with self.assertRaises(ValueError):
            state_to_dict(done, format_version=6)  # 進化したポケモンは形式 7 から（v0.4a のまま）


class BreederGamesTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）から: v0.24 の trader の一時的なデッキで、デッキ B だけマサキ 2 枚をポケモン育て屋さん
    2 枚に置き換えた breeder（tools/preset_deck_games.py）。v0.25 の 40 局の実行で使った局（seed 3・13・14）を、席を合わせて走らせる。"""

    GAMES = (((driver.DECK_A, driver.DECK_B), 3), ((driver.DECK_B, driver.DECK_A), 13), ((driver.DECK_B, driver.DECK_A), 14))

    @classmethod
    def setUpClass(cls):
        cls.results = [driver.play(decks, seed, keep_state=True, variant="breeder") for decks, seed in cls.GAMES]

    def test_decks(self):
        a, b = driver.deck_cards(driver.DECK_A, "breeder"), driver.deck_cards(driver.DECK_B, "breeder")
        self.assertEqual((len(a), len(b)), (60, 60))
        self.assertEqual(a, driver.deck_cards(driver.DECK_A, "trader"))  # デッキ A は trader のまま（2 進化ポケモンがいない）
        trader_b = Counter(driver.deck_cards(driver.DECK_B, "trader"))
        self.assertEqual(Counter(b) - trader_b, Counter({POKEMON_BREEDER: 2}))
        self.assertEqual(trader_b - Counter(b), Counter({BILL: 2}))
        self.assertEqual(Counter(preset_deck(driver.DECK_B).cards())[POKEMON_BREEDER], 0)  # 公開の固定のデッキは変わらない

    def test_breeder_is_used_and_followed_up(self):
        uses = [use for r in self.results for use in r["breeder_uses"]]
        self.assertGreaterEqual(len(uses), 3)
        self.assertTrue(all((use["from_card"], use["to_card"]) == (BULBASAUR, VENUSAUR) for use in uses))
        self.assertTrue(any(use["powers_same_turn"] for use in uses))  # 進化したその番にエナジートランス
        self.assertTrue(any(use["attacked_same_turn"] or use["attacked_next_own_turn"] for use in uses))  # 進化したあとのワザ

    def test_every_game_is_classified_and_audited(self):
        for r in self.results:
            with self.subTest(seed=r["seed"], decks=r["decks"]):
                self.assertIn(r["outcome"], ("game_over", "halted"))
                state = r["state"]
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])
                self.assertEqual(r["trainer_sequence_problems"], [])
                self.assertEqual(r["unresolved_rejections"], {})
                checks = r["policy"]
                self.assertFalse(any(k.startswith("check_") and "mismatch" in k for k in checks), checks)
                self.assertEqual(checks.get("check_in_use_left_in_main", 0), 0)
                for pokemon in (pk for p in state.players for pk in p.in_play()):
                    if len(pokemon.evolution_stack) == 1 and state.card_def(pokemon.card).is_stage2_pokemon:
                        self.assertTrue(state.card_def(pokemon.evolution_stack[0]).is_basic_pokemon)


if __name__ == "__main__":
    unittest.main()

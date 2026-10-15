"""v0.19: オーキドはかせ（PMCG1-077）。最新の説明「あなたの手札をすべてトラッシュする。その後、山札からカードを7枚引いて、手札にする。」
（『ポケモンカードオフィシャルブック2000』p.255。docs/professor-oak-v0.19.md）。

規定と根拠（docs/professor-oak-v0.19.md 2 章の O1〜O12）:

- 使っているこのカードは p.310 の手順 1 で手札から出す（使用中。``trainer_in_use``）ので、トラッシュする手札に含まない。使い終わったら
  トラッシュする（p.310。トラッシュにカードの順番はない。p.312）。
- トラッシュ → 7 枚引くの順（最新の説明の「その後」）。引くのは自分の山札の一番上から（p.312）。
- 使うための条件はない。手札がこのカードだけでも使える（p.255 の解説「手札が「オーキドはかせ」1枚になったときが最高の場合」）。
- 山札が 7 枚未満なら引けるだけ引き、0 枚でも負けではない。負けになるのは番の最初に引けないとき（p.309・p.312。マサキと同じ規定）。
- 使っても番は続き、同じ番に何枚でも使える（p.310）。

kyuura の記録: kyuura（研究の基準 3f34908）にこのカードの照合の記録（CC-）・最新の説明・p.255 のページの記録はない（報告事項。
research_links.json の engine_verified_without_kyuura_record）。

盤面を直接作るテスト（``build_test_state``。規定 1 か所ずつ）と、正式な対戦開始（``new_game``・60 枚・サイド 6 枚）から使う統合テスト
（``NaturalGamesTest``・``MixedDeckGamesTest``）を分けている。
"""

from __future__ import annotations

import pickle
import re
import unittest
from collections import Counter
from pathlib import Path

from kyuura_engine import (
    AttachEnergy, EndTurn, Phase, PlayTrainer, ResolveDecision, apply_command, check_invariants, expand_decklist, new_game, state_to_dict,
)
from kyuura_engine.cards import load_card_pool, read_verification
from kyuura_engine.effects import DEFAULT_EFFECTS, DiscardHandAndDraw
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    BILL, DIGLETT, DRATINI, FIGHTING, FIRE, GROWLITHE, HITMONCHAN, MACHOP, PONYTA, POTION, PROFESSOR_OAK, RATTATA, SEEL, STARYU, SWITCH,
    VOLTORB, WATER, build_test_state, trainer_policy_command,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_confusion_games import TERMINAL

ROOT = Path(__file__).resolve().parent.parent
LATEST = "あなたの手札をすべてトラッシュする。その後、山札からカードを7枚引いて、手札にする。"
PRINTED = "自分の手札を全部すてて、新たに7枚のカードを自分の山札から引いて手札にする。"


def full(state):
    return state_to_dict(state, format_version=9)


def board(hand=(), deck=(), *, discard=(), their_hand=()):
    """自分（プレイヤー 0）の番の MAIN。手札の先頭がオーキドはかせ。"""
    return build_test_state([
        {"active": GROWLITHE, "hand": [PROFESSOR_OAK, *hand], "deck": list(deck), "discard": list(discard)},
        {"active": STARYU, "hand": list(their_hand), "deck": [WATER] * 5},
    ])


def kinds(state, since):
    return [e["kind"] for e in state.log[since:]]


def zone_cards(player):
    return sorted(player.deck + player.hand + player.discard)


class RegistrationTest(unittest.TestCase):
    def test_entry_follows_the_verified_latest_description(self):
        """登録は（カード id で）1 件。照合した写しの文面（印刷）と、実装がしたがう最新の説明（p.255）を分けて持つ。"""
        entry = DEFAULT_EFFECTS.trainer_entry(PROFESSOR_OAK)
        self.assertEqual(entry.effect, DiscardHandAndDraw(count=7))
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), ("オーキドはかせ", PRINTED, LATEST, "P43 p.255"))
        definition = load_card_pool().get(PROFESSOR_OAK)
        self.assertTrue(definition.supported)
        self.assertEqual(definition.trainer_text_ja, PRINTED)
        record = read_verification()["cards"][PROFESSOR_OAK]
        self.assertEqual((record["page"], record["pdf_page"], record["checked_on"]), (255, 257, "2026-10-15"))
        self.assertEqual((record["card_image_text_ja"], record["latest_description_ja"]), (PRINTED, LATEST))
        self.assertEqual(record["status"], "不一致あり")  # 最新の説明が印刷の文面（kyuura の写し）と違う（誤りではなく版の違い）

    def test_no_card_specific_branch_in_the_engine(self):
        """engine.py・resolution/ にこのカードの id での分岐を加えていない（既存のトレーナーの登録・使用中のカード・ドローの処理で扱う）。"""
        for path in [ROOT / "kyuura_engine" / "engine.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]:
            with self.subTest(path=path.name):
                self.assertNotIn(PROFESSOR_OAK, path.read_text(encoding="utf-8"))
                self.assertIsNone(re.search(r"DiscardHandAndDraw|discard_hand", path.read_text(encoding="utf-8")))


class ProfessorOakTest(unittest.TestCase):
    """盤面を直接作り、規定を 1 つずつ確かめる。"""

    def play(self, state):
        """使う前後の状態を比べるための補助。渡した状態は変えない（apply_command の性質）。"""
        before = full(state)
        new = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        self.assertEqual(full(state), before)
        self.assertEqual(check_invariants(new), [])
        return new

    def test_discards_the_rest_of_the_hand_then_draws_seven(self):
        """O1・O3・O4: 残りの手札をすべてトラッシュし、その後、自分の山札の一番上から 7 枚引く。相手の手札・山札は変えない。乱数を使わない。"""
        state = board([PONYTA, FIRE, BILL], [RATTATA, FIRE, FIRE, PONYTA, FIRE, DRATINI, FIRE, VOLTORB, FIRE, FIRE])
        p = state.players[0]
        oak, rest, top = p.hand[0], p.hand[1:], p.deck[:7]
        theirs = (list(state.players[1].hand), list(state.players[1].deck))
        since = len(state.log)
        new = self.play(state)
        q = new.players[0]
        self.assertEqual(q.hand, top)
        self.assertEqual(q.deck, p.deck[7:])
        self.assertEqual(q.discard, rest + [oak])
        self.assertEqual(kinds(new, since), ["play_trainer", "discard_hand", "draw", "discard_trainer"])  # トラッシュ → 引く（「その後」）
        self.assertEqual(new.log[since + 1]["cards"], tuple(rest))
        self.assertEqual(new.log[since + 2]["cards"], tuple(top))
        self.assertEqual((list(new.players[1].hand), list(new.players[1].deck)), theirs)
        self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(state.rng))
        self.assertEqual((new.phase, new.current_player, new.turn_number, new.result), (Phase.MAIN, 0, state.turn_number, None))
        self.assertIsNone(new.trainer_in_use)

    def test_the_card_itself_is_not_part_of_the_discarded_hand(self):
        """O2: 使っているカードは手札から出ている（p.310 の手順 1）ので、トラッシュする手札（``discard_hand``）に含まず、効果のあとに
        ``discard_trainer`` でトラッシュする。手札にあるもう 1 枚のオーキドはかせは手札の一部なのでトラッシュする（同じ番にはもう使えない）。"""
        state = board([PROFESSOR_OAK, FIRE], [FIRE] * 10)
        oak, second, energy = state.players[0].hand
        since = len(state.log)
        new = self.play(state)
        self.assertEqual(new.log[since + 1]["cards"], (second, energy))
        self.assertEqual((new.log[-1]["kind"], new.log[-1]["card"]), ("discard_trainer", oak))
        self.assertEqual(new.players[0].discard, [second, energy, oak])
        with self.assertRaises(Exception) as ctx:
            apply_command(new, PlayTrainer(0, second))
        self.assertEqual(ctx.exception.code, "CARD_NOT_IN_HAND")

    def test_hand_of_only_this_card(self):
        """O5: 手札がこのカードだけ（残りの手札 0 枚）でも使える。トラッシュする手札は 0 枚で、7 枚引く（p.255 の解説）。"""
        state = board([], [FIRE] * 3 + [PONYTA] * 7)
        top = state.players[0].deck[:7]
        since = len(state.log)
        new = self.play(state)
        self.assertEqual(new.log[since + 1]["cards"], ())
        self.assertEqual(new.players[0].hand, top)
        self.assertEqual(len(new.players[0].discard), 1)

    def test_deck_smaller_than_seven_draws_what_it_can(self):
        """O6: 山札が 7 枚未満なら引けるだけ引く。山札がなくなっても負けではない（p.312）。"""
        for size in (1, 3, 6):
            with self.subTest(size=size):
                state = board([PONYTA, FIRE], [FIRE] * size)
                deck = list(state.players[0].deck)
                new = self.play(state)
                self.assertEqual(new.players[0].hand, deck)
                self.assertEqual(new.players[0].deck, [])
                self.assertEqual((new.phase, new.result), (Phase.MAIN, None))

    def test_deck_of_exactly_seven(self):
        state = board([PONYTA], [FIRE] * 7)
        new = self.play(state)
        self.assertEqual((len(new.players[0].hand), new.players[0].deck), (7, []))
        self.assertEqual((new.phase, new.result), (Phase.MAIN, None))

    def test_empty_deck_discards_the_hand_and_draws_nothing(self):
        """O7: 山札が 0 枚でも使える（使うための条件はない）。手札をトラッシュし、0 枚引く。負けではない（p.312）。"""
        state = board([PONYTA, FIRE, BILL], [])
        oak, *rest = state.players[0].hand
        since = len(state.log)
        new = self.play(state)
        self.assertEqual(new.players[0].hand, [])
        self.assertEqual(new.players[0].discard, rest + [oak])
        self.assertEqual(new.log[since + 2]["cards"], ())
        self.assertEqual((new.phase, new.result), (Phase.MAIN, None))

    def test_empty_deck_and_no_other_cards(self):
        """O5・O7 の組み合わせ: 手札がこのカードだけで、山札も 0 枚。トラッシュも引くのも 0 枚で、このカードだけトラッシュする。"""
        state = board([], [])
        oak = state.players[0].hand[0]
        new = self.play(state)
        self.assertEqual((new.players[0].hand, new.players[0].deck, new.players[0].discard), ([], [], [oak]))
        self.assertEqual((new.phase, new.result), (Phase.MAIN, None))

    def test_deck_out_happens_only_at_the_start_of_the_turn(self):
        """O8: 効果で山札がなくなっても負けではない。次の自分の番の最初に引けなければ負け（p.309・p.312。マサキと同じ）。"""
        state = board([PONYTA], [FIRE] * 7)
        state = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        state = apply_command(state, EndTurn(0))
        self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 1))
        state = apply_command(state, EndTurn(1))
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertEqual(state.result.winner, 1)
        self.assertEqual(state.result.conditions, ((1, "OPPONENT_DECK_EMPTY"),))

    def test_turn_continues_and_can_be_used_again_in_the_same_turn(self):
        """O9・O10: 使っても番は続き（手札からつける回数は変えない）、引いたオーキドはかせを同じ番にもう一度使える（p.310「何枚でも」）。"""
        state = board([PONYTA], [PROFESSOR_OAK, FIRE, FIRE, FIRE, FIRE, FIRE, FIRE, RATTATA, PONYTA, FIRE, FIRE, FIRE, FIRE, FIRE, FIRE])
        first = state.players[0].hand[0]
        state = self.play(state)
        self.assertEqual((state.phase, state.current_player, state.energy_attachments_this_turn), (Phase.MAIN, 0, 0))
        second = state.players[0].hand[0]
        self.assertEqual(state.cards[second].card_id, PROFESSOR_OAK)
        state = self.play(state)
        self.assertEqual(state.players[0].discard[-1], second)
        self.assertIn(first, state.players[0].discard)
        self.assertEqual(len(state.players[0].hand), 7)
        energy = next(u for u in state.players[0].hand if state.cards[u].card_id == FIRE)
        state = apply_command(state, AttachEnergy(0, energy, state.players[0].active.card))
        self.assertEqual((state.phase, state.energy_attachments_this_turn), (Phase.MAIN, 1))

    def test_cards_are_conserved(self):
        """カードの保存則: 自分の山札・手札・トラッシュのカードの集合は変わらない（場・相手は変わらない）。"""
        state = board([PONYTA, FIRE, BILL, POTION], [FIRE] * 4 + [RATTATA] * 6)
        new = self.play(state)
        self.assertEqual(zone_cards(new.players[0]), zone_cards(state.players[0]))
        self.assertEqual(zone_cards(new.players[1]), zone_cards(state.players[1]))
        self.assertEqual(sorted(new.cards), sorted(state.cards))

    def test_rejections_change_nothing(self):
        """相手の番・別のトレーナーの決定を待つ間は使えない（p.310。既存の共通の規定）。拒否しても状態は変わらない。"""
        state = board([], [FIRE] * 10, their_hand=[PROFESSOR_OAK])
        cases = [(state, PlayTrainer(1, state.players[1].hand[0]), "NOT_YOUR_TURN")]
        damaged = build_test_state([
            {"active": {"card": GROWLITHE, "damage": 20}, "hand": [POTION, PROFESSOR_OAK], "deck": [FIRE] * 10},
            {"active": STARYU},
        ])
        pending = apply_command(damaged, PlayTrainer(0, damaged.players[0].hand[0]))
        self.assertEqual(pending.phase, Phase.DECISION)
        cases.append((pending, PlayTrainer(0, pending.players[0].hand[0]), "WRONG_PHASE"))
        for before_state, command, code in cases:
            with self.subTest(code=code):
                before = full(before_state)
                with self.assertRaises(Exception) as ctx:
                    apply_command(before_state, command)
                self.assertEqual(ctx.exception.code, code)
                self.assertEqual(full(before_state), before)
        done = apply_command(pending, ResolveDecision(0, pending.decision.id, pending.decision.options[:1]))
        self.assertEqual(done.phase, Phase.MAIN)
        self.assertEqual(self.play_second(done).players[0].hand, done.players[0].deck[:7])

    def play_second(self, state):
        oak = next(u for u in state.players[0].hand if state.cards[u].card_id == PROFESSOR_OAK)
        return apply_command(state, PlayTrainer(0, oak))

    def test_log_fields(self):
        """``discard_hand`` はトラッシュ（公開の情報）に置いたカードだけを持つ。引いたカード（隠れた情報）は ``draw`` の ``cards`` だけ
        （docs/architecture-v0.2b.md 9 章の方針）。"""
        state = board([PONYTA], [FIRE] * 10)
        since = len(state.log)
        new = self.play(state)
        discard_event, draw_event = new.log[since + 1], new.log[since + 2]
        self.assertEqual(set(discard_event), {"kind", "turn", "player", "cards"})
        self.assertEqual(set(draw_event), {"kind", "turn", "player", "cards"})

    def test_saved_state_round_trips(self):
        """使ったあとの状態を保存（pickle・形式 9）しても同じで、続けられる。"""
        state = self.play(board([PONYTA], [FIRE] * 10))
        restored = pickle.loads(pickle.dumps(state))
        self.assertEqual(full(restored), full(state))
        self.assertEqual(full(apply_command(restored, EndTurn(0))), full(apply_command(state, EndTurn(0))))


# ---------------------------------------------------------------- 正式な対戦開始から使う統合テスト

OAK_DECK_A = expand_decklist({
    GROWLITHE: 4, PONYTA: 4, RATTATA: 4, DRATINI: 4, VOLTORB: 4, PROFESSOR_OAK: 4, BILL: 2, POTION: 2, SWITCH: 2, FIRE: 30,
})
OAK_DECK_B = expand_decklist({
    STARYU: 4, SEEL: 4, DIGLETT: 4, MACHOP: 4, HITMONCHAN: 4, PROFESSOR_OAK: 4, BILL: 2, POTION: 2, SWITCH: 2, WATER: 15, FIGHTING: 15,
})
# seed 0〜39 と 71。71 は、seed 0〜399 を順に進めて、山札が 0 枚のときにオーキドはかせを使う場面が最初に起こった seed（盤面を作らずに
# 正式な開始から起こる。0〜399 で 1 局だけ。山札が 0 枚なら番の最初に負けるので、同じ番に引ききってから使うときだけ起こる）
SEEDS = tuple(range(40)) + (71,)


def oak_command(state):
    """番のプレイヤーの手札にオーキドはかせがあれば使う（決まった手順。対戦相手の AI ではない。境界の場面を起こすため、手札の枚数・山札の
    枚数を見ずに使う）。使わないなら None。"""
    if state.phase is not Phase.MAIN:
        return None
    p = state.players[state.current_player]
    oak = next((u for u in p.hand if state.cards[u].card_id == PROFESSOR_OAK), None)
    return None if oak is None else PlayTrainer(state.current_player, oak)


def play_oak_game(decks, seed, *, max_steps=6000):
    """終わるまで進める。オーキドはかせを使うたびに、乱数を使わないこと・カードの保存則を確かめ、使った場面を数える。"""
    state = new_game(*decks, seed)
    commands, observed = [], Counter()
    for _ in range(max_steps):
        if state.phase in TERMINAL:
            return state, commands, observed
        command = oak_command(state) or trainer_policy_command(state, janken_winner=seed % 2)
        new = apply_command(state, command)
        problems = check_invariants(new)
        if problems:
            raise AssertionError(problems)
        if isinstance(command, PlayTrainer) and state.cards[command.card].card_id == PROFESSOR_OAK:
            p, q = state.players[command.player], new.players[command.player]
            if rng_fingerprint(new.rng) != rng_fingerprint(state.rng):
                raise AssertionError("オーキドはかせが乱数を使った")
            if zone_cards(p) != zone_cards(q):
                raise AssertionError("オーキドはかせでカードが増えた・減った")
            observed["oak"] += 1
            observed["oak_rest_0" if len(p.hand) == 1 else "oak_rest_some"] += 1
            observed["oak_deck_short" if len(p.deck) < 7 else "oak_deck_full"] += 1
            observed["oak_deck_empty"] += len(p.deck) == 0
            observed["oak_drew_oak"] += any(new.cards[u].card_id == PROFESSOR_OAK for u in q.hand)
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def oak_decks(seed):
    return (OAK_DECK_A, OAK_DECK_B) if seed % 2 == 0 else (OAK_DECK_B, OAK_DECK_A)


class NaturalGamesTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）から勝敗まで、両方のプレイヤーがオーキドはかせを使う。"""

    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_oak_game(oak_decks(seed), seed) for seed in SEEDS}

    def total(self):
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(observed)
            counted[f"phase_{state.phase.value}"] += 1
            for condition in state.result.conditions if state.result else ():
                counted[f"end_{condition[1]}"] += 1
        return counted

    def test_oak_is_used_including_boundaries(self):
        """自然な対戦で使われ、残りの手札 0 枚・山札 7 枚未満・山札 0 枚の場面も起こる（1 回も起こらない試験を成功と数えない）。"""
        counted = self.total()
        for key in ("oak", "oak_rest_0", "oak_rest_some", "oak_deck_full", "oak_deck_short", "oak_deck_empty", "oak_drew_oak"):
            self.assertGreater(counted[key], 0, (key, dict(counted)))
        self.assertEqual(counted["phase_game_over"] + counted["phase_sudden_death"], len(SEEDS), dict(counted))

    def test_deck_out_ends_games_only_at_the_start_of_a_turn(self):
        """山札切れの負けは、番の最初に引けなかったときだけ（ログの最後が引けなかった番の始まり）。"""
        counted = self.total()
        self.assertGreater(counted["end_OPPONENT_DECK_EMPTY"], 0, dict(counted))
        for seed, (state, _, _) in self.games.items():
            if state.result and any(c[1] == "OPPONENT_DECK_EMPTY" for c in state.result.conditions):
                with self.subTest(seed=seed):
                    loser = 1 - state.result.winner
                    self.assertEqual(state.players[loser].deck, [])
                    starts = [e for e in state.log if e["kind"] == "turn_start"]
                    self.assertEqual(starts[-1]["player"], loser)
                    self.assertFalse(any(e["kind"] == "draw" for e in state.log[state.log.index(starts[-1]):]))

    def test_invariants_logs_and_serialization(self):
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_replay_and_save_restore(self):
        """同じ seed・同じ操作の列で同じ結果。オーキドはかせを使った直後に保存（pickle）して再開しても同じ。"""
        restored = 0
        for seed, (state, commands, _) in self.games.items():
            replayed = new_game(*oak_decks(seed), seed)
            for command in commands:
                replayed = apply_command(replayed, command)
                if isinstance(command, PlayTrainer) and replayed.cards[command.card].card_id == PROFESSOR_OAK:
                    replayed = pickle.loads(pickle.dumps(replayed))
                    restored += 1
            with self.subTest(seed=seed):
                self.assertEqual(full(replayed), full(state))
        self.assertGreater(restored, 0)


class MixedDeckGamesTest(unittest.TestCase):
    """v0.18c の対戦（ナツメのヤドンのデッキと、R団のファイヤー・R団のカビゴン・わるいカメールのデッキ）で、マサキ 4 枚をオーキドはかせ
    4 枚に置きかえ、v0.17 の共通の手順（tests/v017_games.py）にオーキドはかせを使う手順を重ねる。ワザ・特殊能力・決定・止める処理のある
    対戦の中でも、使ったあとに番が続き、不変条件・ログの監査が保たれる。"""

    SEEDS = tuple(range(16))

    @classmethod
    def setUpClass(cls):
        from tests import test_sabrinas_slowpoke_v0_18c as v018c
        from tests.test_dark_wartortle_games_v0_13 import policy_command as base_policy
        from tests.test_machamp_games_v0_10 import working as counter_working
        from tests.test_rocket_snorlax_v0_17b import restless_working
        from tests.v017_games import play_game

        deck = Counter(v018c.SLOWPOKE_DECK)
        deck[PROFESSOR_OAK] = deck.pop(BILL)
        oak_slowpoke = expand_decklist(dict(deck))

        def policy(state, *, janken_winner, cure, tried):
            return oak_command(state) or base_policy(state, janken_winner=janken_winner, cure=cure, tried=tried)

        def decks(seed):
            pair = v018c.decks(seed)
            return tuple(oak_slowpoke if d is v018c.SLOWPOKE_DECK else d for d in pair)

        cls.games = {}
        for seed in cls.SEEDS:
            cls.games[seed] = play_game(
                decks(seed), seed, cure=seed % 3 != 0, not_declarable=(v018c.ROCKETS_SNORLAX,), policy=policy,
                extra_stop={v018c.NO_DAMAGE: lambda s, c: v018c.no_damage_case(s, c) is not None},
                double_ko_check=lambda s, t: counter_working(s, t) or restless_working(s, t),
            )

    def test_oak_is_used_and_games_end(self):
        used = 0
        for seed, (state, commands, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])
            used += sum(1 for e in state.log if e["kind"] == "play_trainer" and state.cards[e["card"]].card_id == PROFESSOR_OAK)
        self.assertGreater(used, 0)


if __name__ == "__main__":
    unittest.main()

"""v0.134: サドン・デスの延長戦の開始（``StartSuddenDeath``。docs/sudden-death-v0.134.md）。

- 原典（p.324。既存の確認記録 docs/simultaneous-ko-v0.2f.md 2 章の引用を再利用）: すべてのカードを最初のデッキの状態にもどし、サイド 1 枚で初めから対戦をやり直す
- 利用者の指定（USER-SUDDEN-DEATH-OWNERSHIP-RESET）: とりかえっこプリーズで交換したカードは、最初のデッキに入れたプレイヤー（出所）にもどす。UQ-SWAP-PLEASE-OWNERSHIP は解決済みにしない
- 正式な開始（new_game）からの合法な操作列で到達したサドン・デス（``NATURAL``）と、盤面を直接作った状態（``constructed_*``。名前に構築と書く）を分けて確かめる
"""

from __future__ import annotations

import copy
import dataclasses
import pathlib
import pickle
import re
import types
import unittest
from collections import Counter

from kyuura_engine import (
    RULE_REFERENCES,
    RULES_2000_02_14,
    EndTurn,
    EvolvePokemon,
    IllegalActionError,
    Phase,
    PlayTrainer,
    ReportJankenResult,
    ResolveDecision,
    StartSuddenDeath,
    StateIntegrityError,
    UnsupportedError,
    UsePokemonPower,
    apply_command,
    check_invariants,
    command_from_dict,
    command_to_dict,
    judge,
    new_game,
    observe,
    state_to_dict,
    sudden_death,
    visible_log,
    visible_segment_logs,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType
from kyuura_engine.effects import COLORS
from kyuura_engine.procedures import finish, halt
from kyuura_engine.resolution.programs import PrintedPlusOpponentPrizesTaken
from kyuura_engine.rng import copy_rng, rng_fingerprint
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import (
    CardInstance,
    GameState,
    Halt,
    PendingDecision,
    SegmentRecord,
    freeze_mapping,
)
from tests.helpers import (
    FIGHTING,
    FIRE,
    HITMONCHAN,
    PIKACHU_DECK,
    PIKACHU_DECK_B,
    RATTATA,
    build_test_state,
    trainer_policy_command,
)
from tests.log_audit import (
    initial_owners,
    log_problems,
    observation_problems,
    segment_problems,
    serialization_problems,
    v130_problems,
)
from tests.sudden_death_games import (
    MAGNEMITE_DECK,
    SWAP_PIKACHU_DECK,
    SWAP_PIKACHU_DECK_B,
    invariant_check,
    play_segment,
    play_segments,
    status_aware_policy,
)
from tests.test_pikachu_games import play_game as pikachu_game

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "sudden-death-v0.134.md"
LATEST = max(FORMAT_VERSIONS)
REPEAT_SEED = 17  # コイル（じばく）のデッキ同士で、最初の対戦と延長戦 1 がサドン・デスになる（v0.134 のエンジンで seed 0〜79 を調べ、17・38・73）
SWAP_SEED = 20  # 交換 7 回（再交換 2 枚）のあと自然にサドン・デスになり、延長戦はプレイヤー 0 の勝ち（v0.134 のエンジンで seed 0〜59 を調べた）
PIKA, RAICHU, VOLTORB, ELECTRODE, VULPIX, NINETALES = "PMCG1-035", "PMCG1-038", "PMCG1-037", "PMCG1-040", "PMCG5-017", "PMCG5-019"
PLUSPOWER, CHAOS_GYM, TICKLE_MACHINE, FOSSIL, SECRET_PLAN = "PMCG1-081", "PMCG5-087", "PMCG6-084", "PMCG3-046", "PMCG5-093"


def snapshot(state):
    """渡した状態が変わっていないかを見る値（書き出し・乱数の内部状態・ログ）。"""
    return state_to_dict(state, format_version=LATEST), state.rng.getstate(), tuple(dict(e) for e in state.log), tuple(state.segments)


def start(state):
    return apply_command(state, StartSuddenDeath())


def canonical_decks(state):
    """デッキリストの並びの uid の付け方から求めた、プレイヤーごとの最初のデッキのカード（uid の集まり。エンジンの出所の値を読まない）。"""
    owners = initial_owners(state)
    return [{uid for uid, owner in owners.items() if owner == player} for player in (0, 1)]


def holdings(state, player):
    """プレイヤーのゾーン（山札・手札・サイド・トラッシュ・場）にあるカードの uid（重なりのないことは不変条件が確かめる）。"""
    p = state.players[player]
    cards = [*p.deck, *p.hand, *p.prizes, *p.discard]
    for pokemon in p.in_play():
        cards.extend((*pokemon.cards(), *pokemon.energy, *(t.card for t in pokemon.trainers)))
    return cards


def with_decklists(state):
    """構築: 盤面を直接作った状態（``build_test_state``。プレイヤー 0 のカード、続けてプレイヤー 1 のカードの順に uid を付ける）に、その並びのデッキリストを付ける。"""
    cards = state.cards
    ids = [[cards[uid].card_id for uid in sorted(cards) if cards[uid].owner == player] for player in (0, 1)]
    assert sorted(cards) == list(range(len(cards))) and all(cards[uid].owner == 0 for uid in range(len(ids[0])))
    state.decklists = (tuple(ids[0]), tuple(ids[1]))
    return state


def constructed_sudden_death(state, conditions=(True, True), cannot=(False, False)):
    """構築: 対戦の途中の状態を、勝ち負けの判定（p.311 の表）でサドン・デスにした状態（``procedures.finish``。使用中のトレーナーは持ち主のトラッシュ、決定は消える）。"""
    new = state.clone()
    result = judge.decide(list(conditions), list(cannot))
    assert result.outcome == "sudden_death"
    finish(new, result)
    assert check_invariants(new) == [], check_invariants(new)
    return new


def default_of(name):
    f = GameState.__dataclass_fields__[name]
    return f.default_factory() if f.default_factory is not dataclasses.MISSING else f.default


def setUpModule():
    global NATURAL, NATURAL_COMMANDS, SWAP_END, SWAP_FINAL, SWAP_COMMANDS
    NATURAL, NATURAL_COMMANDS = pikachu_game(9)  # v0.2f の GoldenSuddenDeathGameTest と同じ（193 操作・79 番目の番で両方が最後のサイドを取る）
    SWAP_FINAL, SWAP_COMMANDS, ends = play_segments((SWAP_PIKACHU_DECK, SWAP_PIKACHU_DECK_B), SWAP_SEED, check=invariant_check)
    SWAP_END = ends[0]


class RecordTest(unittest.TestCase):
    def test_every_game_state_field_has_a_policy(self):
        """GameState の項目ごとに、延長戦を始めるときの扱い（保持・続ける・作り直す・既定の値）を決めている。項目を加えたら分類を加える。"""
        self.assertEqual(set(sudden_death.SEGMENT_FIELD_POLICY), {f.name for f in dataclasses.fields(GameState)})
        self.assertEqual(set(sudden_death.SEGMENT_FIELD_POLICY.values()), {"keep", "continue", "rebuild", "reset"})
        self.assertEqual({k for k, v in sudden_death.SEGMENT_FIELD_POLICY.items() if v == "keep"},
                         {"rules", "card_data", "seed", "definitions", "decklists", "effects"})
        self.assertEqual({k for k, v in sudden_death.SEGMENT_FIELD_POLICY.items() if v == "continue"}, {"rng"})

    def test_rules_and_records(self):
        self.assertEqual((RULES_2000_02_14.prize_count, RULES_2000_02_14.sudden_death_prize_count), (6, 1))
        self.assertEqual(RULE_REFERENCES["sudden_death"].pages, "p.324")
        rule = sudden_death.USER_SUDDEN_DEATH_OWNERSHIP_RESET
        self.assertEqual((rule.id, rule.specified_on, rule.unresolved), ("USER-SUDDEN-DEATH-OWNERSHIP-RESET", "2026-11-02", ("UQ-SWAP-PLEASE-OWNERSHIP",)))
        text = DOC.read_text(encoding="utf-8")
        self.assertIn(f"「{rule.statement}」", text)
        for quote in ("「それぞれ自分の山札、トラッシュ、サイドカード、場にあるカード、手札のすべてをまとめて、最初のデッキの状態に戻します。」",
                      "「延長戦として、もう一度初めから対戦をやり直します。ただし、サイドカードは、1枚だけしかセットしません。」"):
            self.assertIn(quote, text)
            self.assertIn(quote, (ROOT / "docs" / "simultaneous-ko-v0.2f.md").read_text(encoding="utf-8"))  # 既存の確認記録の引用の再利用
        # 利用者の指定は、カードの登録の記録（USER_SPECIFIED_RULES）とは別の種類。とりかえっこプリーズの記録の規則は変えない
        self.assertEqual(E.USER_SPECIFIED_RULES["PR1-027/trainer"].rule, E.USER_SWAP_OWNERSHIP)
        self.assertNotIn(rule.id, {r.rule for r in E.USER_SPECIFIED_RULES.values()})
        self.assertRegex((ROOT / "README.md").read_text(encoding="utf-8"), r"\n- v0\.134（(今のエンジンの版。)?`kyuura_engine` の版は 0\.134\.0）: サドン・デスの延長戦の開始")
        self.assertIn("sudden-death-v0.134.md", (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8"))

    def test_command_round_trip_and_no_card_branch(self):
        self.assertEqual(command_to_dict(StartSuddenDeath()), {"type": "start_sudden_death"})
        self.assertEqual(command_from_dict({"type": "start_sudden_death"}), StartSuddenDeath())
        with self.assertRaises(IllegalActionError):
            command_from_dict({"type": "start_sudden_death", "player": 0})  # 送ったプレイヤーの項目はない
        for path in (ROOT / "kyuura_engine" / "sudden_death.py", ROOT / "kyuura_engine" / "engine.py"):
            source = path.read_text(encoding="utf-8")
            body = source[source.index("def _start_sudden_death"):source.index("def _shuffle_deck")] if path.name == "engine.py" else source
            self.assertIsNone(re.search(r"[\"'][A-Za-z]+\d*X?-\d{3}[\"']", body), path.name)  # カードの id で分岐しない（CLAUDE.md）


class NaturalStartTest(unittest.TestCase):
    """new_game からの合法な操作列（ピカチュウ seed 9）でなったサドン・デスから始める。"""

    def test_input_is_not_changed_and_new_setup_is_returned(self):
        before = snapshot(NATURAL)
        new = start(NATURAL)
        self.assertEqual(snapshot(NATURAL), before)
        self.assertIsNot(new, NATURAL)
        self.assertEqual((NATURAL.phase, NATURAL.result.outcome), (Phase.SUDDEN_DEATH, "sudden_death"))
        self.assertIn(new.phase, (Phase.SETUP_PLACEMENT, Phase.HALTED))
        self.assertEqual((new.segment_index, new.initial_prize_count, new.turn_number, new.first_player, new.current_player), (1, 1, 0, None, None))
        self.assertEqual(check_invariants(new), [])

    def test_all_cards_return_to_the_first_decks(self):
        new = start(NATURAL)
        self.assertEqual(set(new.cards), set(NATURAL.cards))
        self.assertEqual({uid: c.card_id for uid, c in new.cards.items()}, {uid: c.card_id for uid, c in NATURAL.cards.items()})  # uid は付け直さない
        for player, deck in enumerate(canonical_decks(NATURAL)):
            held = holdings(new, player)
            self.assertEqual(Counter(held), Counter(deck))  # 重なり・欠けがない
            self.assertEqual(len(new.players[player].hand) + len(new.players[player].deck), 60)
            self.assertEqual((new.players[player].prizes, new.players[player].discard, new.players[player].active, new.players[player].bench), ([], [], None, []))
        self.assertTrue(all(c.owner == initial_owners(NATURAL)[uid] and c.origin is None for uid, c in new.cards.items()))

    def test_every_field_is_reset_kept_or_rebuilt(self):
        new = start(NATURAL)
        for name, policy in sudden_death.SEGMENT_FIELD_POLICY.items():
            if policy == "keep":
                self.assertIs(getattr(new, name), getattr(NATURAL, name), name)
            elif policy == "reset" and name not in ("mulligan_rounds", "phase", "halt"):  # 準備（切り直し）が書く項目
                self.assertEqual(getattr(new, name), default_of(name), name)
        self.assertEqual(new.next_pokemon_id, 1)  # 場のポケモンの番号・決定の番号は区間の中の番号（前の区間のログは区間の記録にある）
        for p in new.players:
            self.assertEqual((p.placed_starting_pokemon, p.mulligans >= 0), (False, True))

    def test_previous_segment_is_archived(self):
        new = start(NATURAL)
        record = new.segments[0]
        self.assertIsInstance(record, SegmentRecord)
        self.assertEqual((record.index, record.prize_count, record.first_player, record.turn_number), (0, 6, NATURAL.first_player, 79))
        self.assertEqual(record.result, NATURAL.result)
        self.assertEqual(record.log, NATURAL.log)
        self.assertEqual((record.ownership_changes, record.face_down_cards), ((), ()))
        self.assertEqual(new.log[0], {"kind": "sudden_death_started", "turn": 0, "segment": 1, "prize_count": 1})
        self.assertFalse(any(e["kind"] in ("game_created", "game_end") for e in new.log))  # 前の区間のログを今の区間に混ぜない

    def test_random_state_continues_from_the_input(self):
        """乱数は入力の状態から続ける（最初の seed にもどさない）。新しく使うのは 2 人の山札を切る分と、切り直しの分だけ。"""
        new = start(NATURAL)
        rng = copy_rng(NATURAL.rng)
        decks = [sorted(deck) for deck in canonical_decks(NATURAL)]
        for deck in decks:
            rng.shuffle(deck)
        if not new.mulligan_rounds:
            self.assertEqual([new.players[p].hand for p in (0, 1)], [decks[p][:7] for p in (0, 1)])
            self.assertEqual(new.rng.getstate(), rng.getstate())
        reseeded = new_game(PIKACHU_DECK, PIKACHU_DECK_B, NATURAL.seed)
        self.assertNotEqual([p.hand for p in new.players], [p.hand for p in reseeded.players])
        self.assertNotEqual(rng_fingerprint(new.rng), rng_fingerprint(reseeded.rng))

    def test_same_input_same_result(self):
        a, b = start(NATURAL), start(copy.deepcopy(NATURAL))
        self.assertEqual(state_to_dict(a, format_version=LATEST), state_to_dict(b, format_version=LATEST))
        self.assertEqual((rng_fingerprint(a.rng), a.log), (rng_fingerprint(b.rng), b.log))

    def test_observations_and_logs(self):
        new = start(NATURAL)
        for viewer in (0, 1, None):
            self.assertEqual(visible_segment_logs(new, viewer), [{"index": 0, "log": visible_log(NATURAL, viewer)}])
            view = observe(new, viewer)
            self.assertEqual(view["segment"], {"index": 1, "prize_count": 1, "previous": [
                {"index": 0, "outcome": "sudden_death", "conditions": [[0, "ALL_PRIZES_TAKEN"], [1, "ALL_PRIZES_TAKEN"]], "turns": 79}]})
            self.assertEqual(view["result"], None)
            for owner in (0, 1):
                hand = view["players"][owner]["hand"]
                self.assertEqual(hand["cards"] is not None, viewer == owner)
                self.assertEqual(view["players"][owner]["deck"], {"count": len(new.players[owner].deck)})
            shown = visible_log(new, viewer)
            self.assertEqual(shown[0], {"kind": "sudden_death_started", "turn": 0, "segment": 1, "prize_count": 1})
            for event, internal in zip(shown, new.log):
                if internal["kind"] == "draw" and viewer != internal["player"]:
                    self.assertNotIn("cards", event)  # 新しい手札は持ち主だけ
        self.assertNotIn("segment", observe(NATURAL, 0))  # 最初の区間の観測の項目は v0.133 と同じ
        self.assertEqual(observation_problems(new), [])

    def test_audits(self):
        new = start(NATURAL)
        self.assertEqual((log_problems(new), serialization_problems(new), segment_problems(new)), ([], [], []))


class RejectionTest(unittest.TestCase):
    """サドン・デスでない段階・不整合な状態からは始めない（状態・乱数・ログを変えない）。"""

    def assert_rejected(self, state, error, code):
        before = snapshot(state)
        with self.assertRaises(error) as ctx:
            start(state)
        if code is not None:
            self.assertEqual(ctx.exception.code, code)
        self.assertEqual(snapshot(state), before)

    def test_other_phases(self):
        fresh = new_game(PIKACHU_DECK, PIKACHU_DECK_B, 9)
        self.assert_rejected(fresh, IllegalActionError, sudden_death.NOT_SUDDEN_DEATH_CODE)  # 準備
        state = fresh
        seen = set()
        for command in NATURAL_COMMANDS:
            state = apply_command(state, command)
            if state.phase not in seen and state.phase is not Phase.SUDDEN_DEATH:
                seen.add(state.phase)
                self.assert_rejected(state, IllegalActionError, sudden_death.NOT_SUDDEN_DEATH_CODE)
        self.assertTrue({Phase.SETUP_FIRST_PLAYER, Phase.MAIN, Phase.TAKE_PRIZE, Phase.PROMOTE_ACTIVE} <= seen | {Phase.SETUP_PLACEMENT}, seen)
        over, _ = pikachu_game(0)
        self.assertEqual(over.phase, Phase.GAME_OVER)
        self.assert_rejected(over, IllegalActionError, sudden_death.NOT_SUDDEN_DEATH_CODE)
        main = next(s for s in self._states() if s.phase is Phase.MAIN)
        halted = main.clone()
        halt(halted, Halt(code="UNRESOLVED_TEST", message="テスト", references=()))
        self.assert_rejected(halted, IllegalActionError, sudden_death.NOT_SUDDEN_DEATH_CODE)
        from tests.test_deferred_shortage_user_promos_v0_127 import dry_board, dry_up
        interrupted = dry_up(dry_board(2), 3)
        self.assertIsNotNone(interrupted.halt.interruption)
        self.assert_rejected(interrupted, IllegalActionError, sudden_death.NOT_SUDDEN_DEATH_CODE)
        decision = next(s for s in self._states() if s.decision is not None)
        self.assert_rejected(decision, IllegalActionError, sudden_death.NOT_SUDDEN_DEATH_CODE)

    def _states(self):
        state = new_game(PIKACHU_DECK, PIKACHU_DECK_B, 9)
        for command in NATURAL_COMMANDS[:120]:
            state = apply_command(state, command)
            yield state

    def test_other_commands_in_sudden_death(self):
        before = snapshot(NATURAL)
        for command in (EndTurn(0), ReportJankenResult(0)):
            with self.assertRaises(IllegalActionError) as ctx:
                apply_command(NATURAL, command)
            self.assertEqual(ctx.exception.code, sudden_death.SUDDEN_DEATH_NOT_STARTED_CODE)
        self.assertEqual(snapshot(NATURAL), before)

    def test_inconsistent_sudden_death_states(self):
        win = NATURAL.clone()
        win.result = judge.decide([True, False], [False, False])
        self.assert_rejected(win, StateIntegrityError, "STATE_INTEGRITY")
        no_end = NATURAL.clone()
        no_end.log = tuple(e for e in NATURAL.log if e["kind"] != "game_end")
        self.assert_rejected(no_end, StateIntegrityError, "STATE_INTEGRITY")
        other = NATURAL.clone()
        other.result = dataclasses.replace(NATURAL.result, conditions=((0, judge.ALL_PRIZES_TAKEN),) * 2)
        self.assert_rejected(other, StateIntegrityError, "STATE_INTEGRITY")
        pending = NATURAL.clone()
        pending.decision = PendingDecision(id=1, kind="take_prize", player=0, options=(0,), min_choices=1, max_choices=1, resume="take_prize")
        self.assert_rejected(pending, StateIntegrityError, "STATE_INTEGRITY")
        broken = NATURAL.clone()
        broken.players[0].hand.append(broken.players[1].deck[0])
        self.assert_rejected(broken, StateIntegrityError, "STATE_INTEGRITY")

    def test_initial_decks_that_cannot_be_restored(self):
        """デッキリストのない状態・uid の付け方と合わない状態は、推測でデッキを作らずに未対応で止める。"""
        built = build_test_state([{"active": None}, {"active": None}], current_player=0)
        from kyuura_engine.resolution import flow
        from kyuura_engine.resolution.kernel import Resolution
        flow._after_knockouts(Resolution(built), (), None, ())
        self.assertEqual(built.phase, Phase.SUDDEN_DEATH)
        self.assert_rejected(built, UnsupportedError, sudden_death.INITIAL_DECK_UNKNOWN_CODE)
        swapped = NATURAL.clone()
        swapped.decklists = (swapped.decklists[1], swapped.decklists[0])
        self.assert_rejected(swapped, StateIntegrityError if check_invariants(swapped) else UnsupportedError, None)
        reordered = NATURAL.clone()
        first = list(reordered.decklists[0])
        j = next(i for i in range(1, 60) if first[i] != first[0])
        first[0], first[j] = first[j], first[0]
        reordered.decklists = (tuple(first), reordered.decklists[1])  # 組は同じで並びだけ違う（不変条件は通る）
        self.assertEqual(check_invariants(reordered), [])
        self.assert_rejected(reordered, UnsupportedError, sudden_death.INITIAL_DECK_UNKNOWN_CODE)


class ExtensionGameTest(unittest.TestCase):
    """延長戦を準備・対戦・終局まで進める（サイド 1 枚）。"""

    def test_play_to_the_end_with_one_prize(self):
        state = start(NATURAL)
        state, commands = play_segment(state, janken_winner=1, policy=lambda s, janken_winner, played: trainer_policy_command(s, janken_winner=janken_winner),
                                       check=invariant_check)
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertEqual([e["count"] for e in state.log if e["kind"] == "set_prizes"], [1, 1])
        winner = state.result.winner
        self.assertEqual(E.prizes_taken(state, winner), 1)
        self.assertIn((winner, judge.ALL_PRIZES_TAKEN), state.result.conditions)
        self.assertEqual((log_problems(state), observation_problems(state), serialization_problems(state)), ([], [], []))
        # 同じ入力・同じ操作の列なら同じ結果（new_game から延長戦の開始を含めてやり直す）
        replayed = new_game(PIKACHU_DECK, PIKACHU_DECK_B, 9)
        for command in (*NATURAL_COMMANDS, StartSuddenDeath(), *commands):
            replayed = apply_command(replayed, command)
        self.assertEqual(state_to_dict(replayed, format_version=LATEST), state_to_dict(state, format_version=LATEST))
        self.assertEqual(replayed.log, state.log)

    def test_prizes_taken_counts_from_the_extension(self):
        """「相手が取ったサイドの数」（ゴースト ES3-023 の「おんねん」）は、延長戦の初期枚数 1 と今の枚数から求める（6 枚から求めない・前の区間の数を使わない）。"""
        self.assertEqual([E.prizes_taken(NATURAL, p) for p in (0, 1)], [6, 6])
        state = start(NATURAL)
        grudge = PrintedPlusOpponentPrizesTaken(10)
        while state.phase is not Phase.MAIN:
            state = apply_command(state, trainer_policy_command(state, janken_winner=0))
        self.assertEqual([len(p.prizes) for p in state.players], [1, 1])
        self.assertEqual([E.prizes_taken(state, p) for p in (0, 1)], [0, 0])
        run = types.SimpleNamespace(attack=types.SimpleNamespace(damage=20), state=state, player=0)
        self.assertEqual(grudge.value(run, None), 20)  # 6 枚から求めると 20 + 5 × 10 = 70 になる
        run.state = NATURAL
        self.assertEqual(grudge.value(run, None), 80)  # 最初の区間（6 枚とも取った）は v0.133 と同じ
        over = state.clone()
        over.players[1].prizes = []
        self.assertEqual(E.prizes_taken(over, 1), 1)


class SwapOwnershipTest(unittest.TestCase):
    """とりかえっこプリーズで交換・再交換したカード（new_game からの合法な操作列。SWAP_SEED）は、出所の最初のデッキにもどる（利用者の指定）。"""

    def test_swapped_and_reswapped_cards_return_to_their_origin(self):
        end = SWAP_END
        self.assertEqual(end.phase, Phase.SUDDEN_DEATH)
        changed = Counter(c.card for c in end.ownership_changes)
        moved = [uid for uid in changed if end.cards[uid].owner != end.cards[uid].origin]
        reswapped = [uid for uid, n in changed.items() if n > 1]
        self.assertTrue(moved and reswapped)
        self.assertTrue(all(end.cards[uid].owner == end.cards[uid].origin for uid in reswapped))  # 再交換でもどったカード（出所の値は残る）
        new = start(end)
        initial = initial_owners(end)
        for uid in changed:
            self.assertEqual((new.cards[uid].owner, new.cards[uid].origin), (initial[uid], None))
            self.assertIn(uid, holdings(new, initial[uid]))  # 交換の直前の所有者でなく、最初のデッキに入れたプレイヤーの山札・手札
        self.assertEqual(new.ownership_changes, ())
        self.assertEqual(new.segments[0].ownership_changes, end.ownership_changes)  # 前の区間の記録には残す
        for player, deck in enumerate(canonical_decks(end)):
            self.assertEqual(Counter(holdings(new, player)), Counter(deck))
        self.assertEqual((v130_problems(new), segment_problems(new), log_problems(new)), ([], [], []))
        # 交換したカードの所有者を今の所有者で集めると、組がデッキリストと違う（この方法では作らない）
        by_owner = Counter(end.cards[uid].card_id for uid in end.cards if end.cards[uid].owner == 0)
        self.assertNotEqual(by_owner, Counter(end.decklists[0]))

    def test_swap_game_plays_through_the_extension(self):
        self.assertEqual(SWAP_FINAL.segment_index, 1)
        self.assertIn(SWAP_FINAL.phase, (Phase.GAME_OVER, Phase.SUDDEN_DEATH))
        self.assertEqual((log_problems(SWAP_FINAL), observation_problems(SWAP_FINAL), serialization_problems(SWAP_FINAL)), ([], [], []))
        self.assertEqual(Counter(e["kind"] for e in SWAP_FINAL.segments[0].log)["cards_exchanged"], 7)

    def test_constructed_reswap_returns_to_the_first_origin(self):
        """構築: 交換したカードをさらに交換し（出所 1 のカードが 0 → 1 → 0 と動く）、受け取ったプレイヤーのトラッシュ・場にあるままサドン・デスにした盤面。"""
        from tests.helpers import FIGHTING, POTION, RATTATA
        from tests.test_trade_please_v0_130 import swap, swap_board
        state = with_decklists(swap_board(hand=(RATTATA, POTION, "PR1-027"), opponent_hand=(RATTATA, POTION, FIGHTING, "PR1-027")))
        their_potion = next(uid for uid in state.players[1].hand if state.cards[uid].card_id == POTION)
        state = swap(state, their_potion, RATTATA, True)  # 相手のきずぐすり（出所 1）を受け取る
        self.assertEqual(state.cards[their_potion].owner, 0)
        state = apply_command(state, EndTurn(0))
        while state.phase is not Phase.MAIN:
            state = apply_command(state, trainer_policy_command(state))
        state = swap(state, their_potion, FIGHTING, True, player=1)  # 相手が使い、受け取ったきずぐすりを取りもどす（1 にもどる）
        self.assertEqual((state.cards[their_potion].owner, state.cards[their_potion].origin), (1, 1))
        sudden = constructed_sudden_death(state)
        new = start(sudden)
        self.assertEqual((new.cards[their_potion].owner, new.cards[their_potion].origin), (1, None))
        moved = [uid for uid, c in sudden.cards.items() if c.owner != c.deck_owner]
        self.assertTrue(moved)
        for uid in moved:
            self.assertEqual(new.cards[uid].owner, sudden.cards[uid].deck_owner)
        self.assertEqual(check_invariants(new), [])


class ZoneRestorationTest(unittest.TestCase):
    """構築: 盤面を直接作った状態から、合法なコマンドで、場の進化の重なり・ついているエネルギー・どうぐ（プラスパワー）・「ばける」でのせたカード・エネルギーとしてついているカード
    （［エネエネ］）・うらのカード（マチスの秘策）・置いておくカード（くすぐりマシーン）・スタジアム（錯乱ジム）・トラッシュ・サイド・手札・山札をそろえ、サドン・デスにして始める。"""

    def board(self):
        state = build_test_state([
            {"active": {"card": PIKA, "energy": [FIRE, FIRE]}, "bench": [VULPIX, VOLTORB],
             "hand": [RAICHU, NINETALES, ELECTRODE, RAICHU, PLUSPOWER, SECRET_PLAN, RATTATA, TICKLE_MACHINE, CHAOS_GYM], "discard": [FIRE, PIKA], "prizes": 2,
             "deck": [FIRE] * 5},
            {"active": {"card": HITMONCHAN, "damage": 20, "energy": [FIGHTING]}, "bench": [RATTATA], "hand": [FIRE, FIRE], "discard": [VOLTORB], "prizes": 3,
             "deck": [FIRE] * 6},
        ], current_player=0, turn_number=5)

        def uid(card_id):
            return next(u for u in state.players[0].hand if state.cards[u].card_id == card_id)

        def pid(card_id):
            return next(p.pokemon_id for p in state.players[0].in_play() if state.cards[p.card].card_id == card_id)

        def run(command, *answers):
            nonlocal state
            state = apply_command(state, command)
            for choices in answers:
                d = state.decision
                state = apply_command(state, ResolveDecision(d.player, d.id, tuple(choices(state) if callable(choices) else choices)))

        run(EvolvePokemon(0, uid(RAICHU), pid(PIKA)))
        run(EvolvePokemon(0, uid(NINETALES), pid(VULPIX)))
        run(EvolvePokemon(0, uid(ELECTRODE), pid(VOLTORB)))
        run(PlayTrainer(0, uid(PLUSPOWER)))
        run(PlayTrainer(0, uid(SECRET_PLAN)), lambda s: (next(u for u in s.players[0].hand if s.cards[u].card_id == RATTATA),))
        run(PlayTrainer(0, uid(TICKLE_MACHINE)))
        run(UsePokemonPower(0, pid(NINETALES), 0), lambda s: (next(u for u in s.players[0].hand if s.cards[u].card_id == RAICHU),))
        run(UsePokemonPower(0, pid(ELECTRODE), 0), (pid(RAICHU),), (COLORS.index(EnergyType.LIGHTNING),), (0,))
        run(PlayTrainer(0, uid(CHAOS_GYM)))
        with_decklists(state)
        self.assertEqual(check_invariants(state), [])
        self.assertTrue(state.stadium and state.energy_roles and state.set_aside and state.face_down_cards)
        self.assertTrue(any(p.disguise is not None for p in state.players[0].in_play()))
        self.assertTrue(any(p.evolution_stack for p in state.players[0].in_play()) and any(p.trainers for p in state.players[0].in_play()))
        return state

    def test_every_zone_returns_to_the_first_deck(self):
        state = self.board()
        sudden = constructed_sudden_death(state)
        new = start(sudden)
        self.assertEqual(check_invariants(new), [])
        for player, deck in enumerate(canonical_decks(sudden)):
            self.assertEqual(Counter(holdings(new, player)), Counter(deck))
        for name in ("stadium", "energy_roles", "set_aside", "face_down_cards", "trainer_effects", "face_up_prizes"):
            self.assertEqual(getattr(new, name), default_of(name), name)
        record = new.segments[0]
        self.assertEqual(record.face_down_cards, sudden.face_down_cards)
        # 前の区間でうらのままだったカード（プレイヤー 0 のマチスの秘策）の uid は、区間のログを見せるときも相手・観戦者に見せない（持ち主には見せる）
        hidden = sudden.face_down_cards[0]
        self.assertTrue(any(hidden in [v for k, v in e.items() if k in ("card", "pokemon")] for e in visible_segment_logs(new, 0)[0]["log"]))
        for viewer in (1, None):
            for event in visible_segment_logs(new, viewer)[0]["log"]:
                self.assertNotIn(sudden.face_down_cards[0], [v for k, v in event.items() if k in ("card", "pokemon")])

    def test_halted_setup_is_kept(self):
        """構築: 延長戦の準備で、両方の切り直しのあと片方だけが切り直す（切り直しの補償。UNRESOLVED_MULLIGAN_COMPENSATION）・化石の手札（PF1）になれば、通常の準備と同じに止める。"""
        found = set()
        for seed in range(200):
            for deck in ([PIKA] + [FIRE] * 30, [FOSSIL] * 4 + [PIKA] + [FIRE] * 26):
                state = build_test_state([{"active": PIKA, "deck": deck, "prizes": 0}, {"active": PIKA, "deck": [PIKA] + [FIRE] * 30, "prizes": 0}],
                                         current_player=0, seed=seed)
                new = start(constructed_sudden_death(with_decklists(state)))
                self.assertEqual(check_invariants(new), [])
                if new.phase is Phase.HALTED:
                    found.add(new.halt.code)
                    self.assertEqual(new.segment_index, 1)
                    with self.assertRaises(IllegalActionError):
                        start(new)
            if {"UNRESOLVED_MULLIGAN_COMPENSATION", E.PLAY_AS_POKEMON_SETUP_CODE} <= found:
                break
        self.assertEqual(found, {"UNRESOLVED_MULLIGAN_COMPENSATION", E.PLAY_AS_POKEMON_SETUP_CODE})


class RepeatedSuddenDeathTest(unittest.TestCase):
    """延長戦がまたサドン・デスになったら、同じ操作で次の延長戦を始める（回数の上限・勝者の決め方は加えない）。"""

    def test_natural_second_sudden_death(self):
        """new_game からの合法な操作列（コイルのデッキ同士・seed 17）: 最初の対戦・延長戦 1 がどちらもサドン・デスになり、延長戦 2 で勝敗が決まる。"""
        boundaries = []

        def boundary(before, after):
            boundaries.append((snapshot(before), before, after))
            self.assertEqual((log_problems(before), observation_problems(before), serialization_problems(before)), ([], [], []))
            self.assertEqual((log_problems(after), observation_problems(after), serialization_problems(after), segment_problems(after)), ([], [], [], []))

        final, commands, ends = play_segments((MAGNEMITE_DECK, MAGNEMITE_DECK), REPEAT_SEED, policy=status_aware_policy, check=invariant_check, boundary=boundary)
        self.assertEqual([e.phase for e in ends], [Phase.SUDDEN_DEATH, Phase.SUDDEN_DEATH, Phase.GAME_OVER])
        self.assertEqual([r.prize_count for r in final.segments], [6, 1])
        self.assertEqual(final.segment_index, 2)
        for before_snapshot, before, _ in boundaries:
            self.assertEqual(snapshot(before), before_snapshot)  # 始める操作は入力を変えない
        self.assertEqual([e["count"] for e in final.segments[1].log if e["kind"] == "set_prizes"], [1, 1])
        self.assertEqual((log_problems(final), observation_problems(final), serialization_problems(final)), ([], [], []))
        for player, deck in enumerate(canonical_decks(final)):
            self.assertEqual(Counter(holdings(final, player)), Counter(deck))
        replayed = new_game(MAGNEMITE_DECK, MAGNEMITE_DECK, REPEAT_SEED)
        for command in commands:
            replayed = apply_command(replayed, command)
        self.assertEqual(state_to_dict(replayed, format_version=LATEST), state_to_dict(final, format_version=LATEST))

    def test_constructed_second_sudden_death(self):
        """構築: 延長戦（区間 1）の途中の状態を勝ち負けの判定でサドン・デスにして、区間 2 を始める。"""
        first = start(NATURAL)
        while first.phase is not Phase.MAIN:
            first = apply_command(first, trainer_policy_command(first, janken_winner=1))
        second_end = constructed_sudden_death(first)
        second = start(second_end)
        self.assertEqual((second.segment_index, second.initial_prize_count), (2, 1))
        self.assertEqual([r.index for r in second.segments], [0, 1])
        self.assertEqual([r.prize_count for r in second.segments], [6, 1])
        self.assertEqual(second.segments[1].log, second_end.log)
        self.assertEqual(second.log[0], {"kind": "sudden_death_started", "turn": 0, "segment": 2, "prize_count": 1})
        self.assertEqual((log_problems(second), segment_problems(second), observation_problems(second), serialization_problems(second)), ([], [], [], []))
        third = start(constructed_sudden_death(next(s for s in _until_main(second))))
        self.assertEqual(third.segment_index, 3)


def _until_main(state):
    while state.phase is not Phase.MAIN:
        state = apply_command(state, trainer_policy_command(state, janken_winner=0))
    yield state


class SerializationTest(unittest.TestCase):
    """保存（pickle・deepcopy・clone）と書き出し（形式 34。古い形式は延長戦の区間を表せない）。"""

    def stages(self):
        first = start(NATURAL)
        middle = first
        while middle.phase is not Phase.MAIN:
            middle = apply_command(middle, trainer_policy_command(middle, janken_winner=1))
        return {"before": NATURAL, "setup": first, "middle": middle, "again": constructed_sudden_death(middle)}

    def test_round_trips(self):
        for name, stage in self.stages().items():
            for restored in (pickle.loads(pickle.dumps(stage)), copy.deepcopy(stage), stage.clone()):
                self.assertEqual(state_to_dict(restored, format_version=LATEST), state_to_dict(stage, format_version=LATEST), name)
                self.assertEqual(restored.segments, stage.segments, name)
                self.assertEqual(check_invariants(restored), [], name)
                if restored.phase is Phase.SUDDEN_DEATH:
                    self.assertEqual(state_to_dict(start(restored), format_version=LATEST), state_to_dict(start(stage), format_version=LATEST), name)
                elif restored.phase is not Phase.HALTED:
                    command = trainer_policy_command(stage, janken_winner=1)
                    self.assertEqual(state_to_dict(apply_command(restored, command), format_version=LATEST),
                                     state_to_dict(apply_command(stage, command), format_version=LATEST), name)

    def test_formats(self):
        stages = self.stages()
        self.assertEqual(state_to_dict(stages["before"], format_version=33), {k: v for k, v in state_to_dict(stages["before"], format_version=34).items()
                                                                              if k not in ("segment", "initial_prize_count", "segments")} | {"format_version": 33})
        for name in ("setup", "middle", "again"):
            for version in FORMAT_VERSIONS[:-1]:
                with self.assertRaises(ValueError):
                    state_to_dict(stages[name], format_version=version)
            data = state_to_dict(stages[name], format_version=34)
            self.assertEqual(data["segment"], stages[name].segment_index)
            self.assertEqual(data["initial_prize_count"], 1)
            self.assertEqual([s["index"] for s in data["segments"]], list(range(stages[name].segment_index)))
            self.assertEqual(data["segments"][0]["result"], {"outcome": "sudden_death", "winner": None, "conditions": [[0, "ALL_PRIZES_TAKEN"], [1, "ALL_PRIZES_TAKEN"]]})
            self.assertEqual(serialization_problems(stages[name]), [])

    def test_old_saves(self):
        """v0.133 までの状態の写し（区間の項目・出所の項目のない pickle）は、情報が足りるので受け付ける。デッキリストのない写しは未対応で止める。"""
        old = pickle.loads(pickle.dumps(NATURAL))
        old.__dict__.pop("segments")
        old.__dict__.pop("ownership_changes")
        cards = {uid: CardInstance(uid, c.card_id, c.owner) for uid, c in old.cards.items()}
        for card in cards.values():
            card.__dict__.pop("origin", None)
        old.cards = freeze_mapping(cards)
        old.rules = RULES_2000_02_14.__class__(**{f.name: getattr(RULES_2000_02_14, f.name) for f in dataclasses.fields(RULES_2000_02_14)})
        old.rules.__dict__.pop("sudden_death_prize_count")
        self.assertEqual((old.segments, old.ownership_changes, old.rules.sudden_death_prize_count), ((), (), 1))
        self.assertEqual(state_to_dict(start(old), format_version=LATEST), state_to_dict(start(NATURAL), format_version=LATEST))
        no_decklists = NATURAL.clone()
        no_decklists.decklists = ((), ())
        with self.assertRaises(UnsupportedError) as ctx:
            start(no_decklists)
        self.assertEqual(ctx.exception.code, sudden_death.INITIAL_DECK_UNKNOWN_CODE)


class AuditDetectsTamperingTest(unittest.TestCase):
    """ログの監査が、区間の境界をわざと誤らせた状態を見つける（エンジンの区間の番号・枚数・出所を信じない）。"""

    def test_tampered_states(self):
        new = start(SWAP_END)
        self.assertEqual(segment_problems(new), [])
        wrong_prizes = new.clone()
        wrong_prizes.log = (dict(new.log[0]) | {"prize_count": 6},) + new.log[1:]
        self.assertTrue(segment_problems(wrong_prizes))
        wrong_index = new.clone()
        wrong_index.log = (dict(new.log[0]) | {"segment": 2},) + new.log[1:]
        self.assertTrue(segment_problems(wrong_index))
        leaked = new.clone()
        leaked.log = (dict(new.log[0]) | {"hand": tuple(new.players[0].hand)},) + new.log[1:]
        self.assertTrue(segment_problems(leaked))
        record = new.segments[0]
        dropped = new.clone()
        dropped.segments = (dataclasses.replace(record, ownership_changes=record.ownership_changes[:-2]),)
        self.assertTrue(segment_problems(dropped))
        kept_owner = new.clone()  # 交換したカードを受け取ったプレイヤーのまま、新しい区間を始めた（出所にもどしていない）
        uid = next(c.card for c in record.ownership_changes if SWAP_END.cards[c.card].owner != SWAP_END.cards[c.card].origin)
        kept_owner.cards = freeze_mapping({**new.cards, uid: CardInstance(uid, new.cards[uid].card_id, 1 - new.cards[uid].owner)})
        self.assertTrue(v130_problems(kept_owner))


if __name__ == "__main__":
    unittest.main()

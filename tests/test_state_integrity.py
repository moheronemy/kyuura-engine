"""状態の整合性（v0.1 レビューで見つけた問題の再現テストと、共通の不変条件）。

- check_invariants が見逃していた壊れ方（未知の uid、場にあるエネルギー、サイドの枚数など）
- GameState の copy.deepcopy / pickle
- 共有しているカードデータを書き換えられないこと
- apply_command が壊れた状態を返さないこと
- どの段階でも、その段階で受け付けるコマンド以外は通らないこと
- 相手のカードを自分のカードとして指定できないこと
- でたらめなコマンドを送っても状態が壊れないこと
"""

import copy
import pickle
import random
import unittest
from dataclasses import fields

from kyuura_engine import (
    AttachEnergy, DrawMulliganCards, EndTurn, EvolvePokemon, IllegalActionError, Phase, PlaceStartingPokemon,
    PlayBasicToBench, PlayTrainer, PromoteActive, ReportJankenResult, ResolveDecision, Retreat, TakePrize,
    UnsupportedError, UseAttack, UsePokemonPower, apply_command, check_invariants, load_card_pool, new_game,
    state_to_dict,
)
from kyuura_engine.cards import pool_from_extract, read_extract
from kyuura_engine.commands import COMMAND_TYPES
from kyuura_engine.errors import StateIntegrityError
from kyuura_engine.state import PokemonInPlay

from tests.helpers import (
    FEW_BASICS, FIGHTING, FIRE, FIRE_DECK, GROWLITHE, HITMONCHAN, MACHOP, ONE_BASIC, PONYTA, RATTATA, SEEL, STARYU,
    WATER, WATER_FIGHTING_DECK, build_test_state, find_seed, place_all, play_until_end, replay, scripted_command,
    two_step_effects,
)


def started_state():
    state = build_test_state([{"active": GROWLITHE, "bench": [PONYTA], "hand": [FIRE, FIRE]}, {"active": STARYU}])
    assert check_invariants(state) == []
    return state


class InvariantDetectionTest(unittest.TestCase):
    """check_invariants は、カードの保存則と場の形の破れを報告する。"""

    def assert_detects(self, state, fragment):
        problems = check_invariants(state)
        self.assertTrue(any(fragment in p for p in problems), problems)

    def test_unknown_uid(self):
        state = started_state()
        state.players[0].hand.append(9999)
        self.assert_detects(state, "未知のカード")

    def test_duplicate_and_missing(self):
        state = started_state()
        state.players[0].hand.append(state.players[0].deck[0])
        self.assert_detects(state, "2 か所")
        state = started_state()
        state.players[0].deck.pop()
        self.assert_detects(state, "どこにもない")

    def test_card_of_the_other_player(self):
        state = started_state()
        state.players[0].hand.append(state.players[1].deck.pop())
        self.assert_detects(state, "持ち主でない")

    def test_energy_or_unknown_card_as_pokemon_in_play(self):
        state = started_state()
        energy = state.players[0].hand.pop()
        state.players[0].bench.append(PokemonInPlay(energy))
        self.assert_detects(state, "ポケモンでないカード")

    def test_prize_count_over_the_rule(self):
        state = started_state()
        state.players[0].prizes.append(state.players[0].deck.pop())
        self.assert_detects(state, "サイド")

    def test_main_phase_needs_both_active(self):
        state = started_state()
        state.players[1].active = None
        self.assert_detects(state, "バトル場")

    def test_pending_decisions_must_match_phase(self):
        state = started_state()
        state.phase = Phase.TAKE_PRIZE
        self.assert_detects(state, "サイドを取る")
        state = started_state()
        state.phase = Phase.PROMOTE_ACTIVE
        self.assert_detects(state, "バトル場に出す")

    def test_energy_attachments_over_the_limit(self):
        state = started_state()
        state.energy_attachments_this_turn = 2
        self.assert_detects(state, "エネルギーをつけた回数")

    def test_cards_must_match_decklists_after_new_game(self):
        state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 0)
        self.assertEqual(check_invariants(state), [])
        state.decklists = (state.decklists[1], state.decklists[0])
        self.assert_detects(state, "デッキ")


class ApplyCommandIntegrityTest(unittest.TestCase):
    def test_broken_state_is_not_returned(self):
        """壊れた状態にコマンドを送ると、壊れた状態を返さずに StateIntegrityError を投げる。"""
        state = started_state()
        state.players[0].hand.append(state.players[0].deck[0])  # 呼び出し側が状態を壊した
        before = state_to_dict(state)
        with self.assertRaises(StateIntegrityError):
            apply_command(state, EndTurn(0))
        self.assertEqual(state_to_dict(state), before)


class CopyAndPickleTest(unittest.TestCase):
    """GameState を copy.deepcopy・pickle できる（AI の探索や並列処理で使われる）。"""

    def test_deepcopy_is_independent_and_equal(self):
        state = started_state()
        copied = copy.deepcopy(state)
        self.assertEqual(state_to_dict(copied), state_to_dict(state))
        self.assertEqual(copied.rng.getstate(), state.rng.getstate())
        copied.players[0].hand.clear()
        self.assertEqual(len(state.players[0].hand), 2)
        with self.assertRaises(TypeError):
            copied.cards[0] = None

    def test_pickle_round_trip_continues_identically(self):
        start = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 7)
        end, commands = play_until_end(start)
        restored = pickle.loads(pickle.dumps(start))
        self.assertEqual(state_to_dict(restored), state_to_dict(start))
        self.assertEqual(state_to_dict(replay(restored, commands)), state_to_dict(end))
        with self.assertRaises(TypeError):
            restored.log[0]["kind"] = "changed"


class SharedCardDataTest(unittest.TestCase):
    """load_card_pool はプロセス内で共有されるので、書き換えられないようにする。"""

    def test_pool_mappings_are_read_only(self):
        pool = load_card_pool()
        with self.assertRaises(TypeError):
            pool.definitions["PMCG1-016"] = None
        with self.assertRaises(TypeError):
            pool.source["commit"] = "x"


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------- 段階とコマンドの組み合わせ

ALLOWED = {
    Phase.SETUP_PLACEMENT: {PlaceStartingPokemon},
    Phase.SETUP_MULLIGAN_DRAW: {DrawMulliganCards},
    Phase.SETUP_FIRST_PLAYER: {ReportJankenResult},
    # PlayTrainer は v0.2b、EvolvePokemon は v0.4a、UsePokemonPower は v0.5（自分の番の中だけ。p.311・p.323）
    Phase.MAIN: {PlayBasicToBench, AttachEnergy, Retreat, UseAttack, EndTurn, PlayTrainer, EvolvePokemon, UsePokemonPower},
    Phase.TAKE_PRIZE: {TakePrize, ResolveDecision},
    Phase.PROMOTE_ACTIVE: {PromoteActive, ResolveDecision},
    Phase.DECISION: {ResolveDecision},  # v0.2a（ワザの効果の途中の決定。製品のカードでは起こらない）
}


def states_in_every_phase():
    """正式な開始（new_game）から、各段階の状態を 1 つずつ作る。"""
    found = {}
    no_mulligan = find_seed(FIRE_DECK, WATER_FIGHTING_DECK, lambda s: s.mulligan_rounds == ())
    state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, no_mulligan)
    found[Phase.SETUP_PLACEMENT] = state
    found[Phase.SETUP_FIRST_PLAYER] = place_all(place_all(state, 0), 1)
    mulligan = find_seed(ONE_BASIC, FIRE_DECK, lambda s: s.mulligan_rounds and all(r == (0,) for r in s.mulligan_rounds))
    found[Phase.SETUP_MULLIGAN_DRAW] = place_all(place_all(new_game(ONE_BASIC, FIRE_DECK, mulligan), 0), 1)
    found[Phase.HALTED] = new_game(FEW_BASICS, FEW_BASICS, find_seed(FEW_BASICS, FEW_BASICS, lambda s: s.phase is Phase.HALTED))
    for seed in range(100):  # サイドを取る段階と、バトル場に出す段階を通る試合を探す
        state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, seed)
        seen = {}
        while state.phase not in (Phase.GAME_OVER, Phase.HALTED):
            seen.setdefault(state.phase, state)
            state = apply_command(state, scripted_command(state))
        if Phase.PROMOTE_ACTIVE in seen and Phase.TAKE_PRIZE in seen:
            found[Phase.MAIN] = seen[Phase.MAIN]
            found[Phase.TAKE_PRIZE] = seen[Phase.TAKE_PRIZE]
            found[Phase.PROMOTE_ACTIVE] = seen[Phase.PROMOTE_ACTIVE]
            found[Phase.GAME_OVER] = state
            break
    else:
        raise AssertionError("各段階を通る試合が見つからない")
    # v0.2a: ワザの効果の途中の決定（Phase.DECISION）。テスト専用の登録表で、正式な開始から作る
    pool = pool_from_extract(read_extract(), two_step_effects())
    for seed in range(100):
        state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, seed, pool=pool)
        while state.phase not in (Phase.DECISION, Phase.GAME_OVER, Phase.HALTED):
            state = apply_command(state, scripted_command(state, janken_winner=1))
        if state.phase is Phase.DECISION:
            found[Phase.DECISION] = state
            return found
    raise AssertionError("決定を待つ段階を通る試合が見つからない")


def sample_commands(state):
    """どの種類のコマンドも、なるべくその状態のカードを使って 1 つずつ作る。"""
    p = state.current_player if state.current_player is not None else 0
    pl = state.players[p]
    card = pl.hand[0] if pl.hand else 0
    pokemon = pl.active.card if pl.active else (pl.bench[0].card if pl.bench else 0)
    pokemon_id = pl.active.pokemon_id if pl.active else (pl.bench[0].pokemon_id if pl.bench else 0)  # v0.4a: 進化の対象、v0.5: パワーを使うポケモン
    return [
        PlaceStartingPokemon(p, card), DrawMulliganCards(p, 0), ReportJankenResult(0), PlayBasicToBench(p, card),
        AttachEnergy(p, card, pokemon), Retreat(p, (), pokemon), UseAttack(p, 0), EndTurn(p), TakePrize(p, 0),
        PromoteActive(p, pokemon), ResolveDecision(p, 1, (0,)),
        EvolvePokemon(p, card, pokemon_id), PlayTrainer(p, card), UsePokemonPower(p, pokemon_id),
    ]


class PhaseCommandMatrixTest(unittest.TestCase):
    """どの段階でも、その段階で受け付けるコマンド以外は通らない（状態も変わらない）。"""

    def test_every_command_in_every_phase(self):
        found = states_in_every_phase()
        self.assertEqual(set(found), set(ALLOWED) | {Phase.GAME_OVER, Phase.HALTED})
        for phase, state in found.items():
            # v0.4d: 形式 1 はワザの途中の決定（Phase.DECISION）を表せない（ValueError）ので、すべての段階を形式 8 で比べる
            before = state_to_dict(state, format_version=8)
            for command in sample_commands(state):
                if type(command) in ALLOWED.get(phase, set()):
                    continue
                with self.subTest(phase=phase.value, command=type(command).__name__):
                    with self.assertRaises((IllegalActionError, UnsupportedError)) as ctx:
                        apply_command(state, command)
                    # v0.4e までは UsePokemonPower はどの段階でも UNSUPPORTED_ACTION だった。v0.5 で対応にしたので、ほかの
                    # コマンドと同じく段階で拒否する（PlayTrainer は v0.2b、EvolvePokemon は v0.4a で同じ変更をした）
                    if phase is Phase.GAME_OVER:
                        expected = "GAME_OVER"
                    elif phase is Phase.HALTED:
                        expected = "UNRESOLVED_MULLIGAN_COMPENSATION"
                    else:
                        expected = "WRONG_PHASE"
                    self.assertEqual(ctx.exception.code, expected)
            self.assertEqual(state_to_dict(state, format_version=8), before)


class OpponentCardsTest(unittest.TestCase):
    """相手のカード・ポケモンを、自分のカードとして指定できない。"""

    def setUp(self):
        self.state = build_test_state([
            {"active": {"card": GROWLITHE, "energy": [FIRE]}, "bench": [PONYTA], "hand": [FIRE, RATTATA]},
            {"active": {"card": STARYU, "energy": [WATER]}, "bench": [SEEL], "hand": [WATER, MACHOP]},
        ])
        self.mine, self.theirs = self.state.players

    def assert_code(self, command, code):
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(self.state, command)
        self.assertEqual(ctx.exception.code, code, command)

    def test_main_phase_commands(self):
        their_water, their_machop = self.theirs.hand
        my_fire = self.mine.hand[0]
        self.assert_code(PlayBasicToBench(0, their_machop), "CARD_NOT_IN_HAND")
        self.assert_code(AttachEnergy(0, their_water, self.mine.active.card), "CARD_NOT_IN_HAND")
        self.assert_code(AttachEnergy(0, my_fire, self.theirs.active.card), "TARGET_NOT_YOURS")
        self.assert_code(AttachEnergy(0, my_fire, self.theirs.bench[0].card), "TARGET_NOT_YOURS")
        self.assert_code(Retreat(0, tuple(self.mine.active.energy), self.theirs.bench[0].card), "NOT_ON_BENCH")
        self.assert_code(Retreat(0, tuple(self.theirs.active.energy), self.mine.bench[0].card), "ENERGY_NOT_ATTACHED")

    def test_promote_with_opponents_bench(self):
        state = build_test_state([
            {"active": {"card": HITMONCHAN, "energy": [FIGHTING, FIGHTING, FIGHTING]}, "bench": [MACHOP]},
            {"active": PONYTA, "bench": [SEEL]},
        ])
        state = apply_command(apply_command(state, UseAttack(0, 1)), TakePrize(0, 0))
        self.assertEqual(state.phase, Phase.PROMOTE_ACTIVE)
        for uid in (state.players[0].bench[0].card, state.players[0].active.card):
            with self.assertRaises(IllegalActionError) as ctx:
                apply_command(state, PromoteActive(1, uid))
            self.assertEqual(ctx.exception.code, "NOT_ON_BENCH")

    def test_setup_with_opponents_hand(self):
        seed = find_seed(FIRE_DECK, WATER_FIGHTING_DECK, lambda s: s.mulligan_rounds == ())
        state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, seed)
        their_basic = next(u for u in state.players[1].hand if state.card_def(u).is_basic_pokemon)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, PlaceStartingPokemon(0, their_basic))
        self.assertEqual(ctx.exception.code, "CARD_NOT_IN_HAND")


class RandomCommandPropertyTest(unittest.TestCase):
    """でたらめなコマンドを送っても、(1) エンジンの例外以外で落ちない、(2) 失敗したら状態は変わらない、
    (3) 成功したら不変条件（カードの保存則など）を満たす。"""

    def random_command(self, rng, state):
        cls = rng.choice(list(COMMAND_TYPES.values()))
        uids = list(state.cards) + [-1, 10_000]
        values = {}
        for f in fields(cls):
            if f.type == "int":
                values[f.name] = rng.choice(uids if f.name not in ("player", "winner", "count", "index", "attack_index") else [-1, 0, 1, 2, 3])
            else:
                values[f.name] = tuple(rng.choice(uids) for _ in range(rng.randint(0, 3)))
        return cls(**values)

    def test_random_commands_keep_state_valid(self):
        for seed in range(12):
            rng = random.Random(seed)
            state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, seed)
            for _ in range(600):
                if state.phase in (Phase.GAME_OVER, Phase.HALTED):
                    break
                command = scripted_command(state) if rng.random() < 0.35 else self.random_command(rng, state)
                before = state_to_dict(state)
                try:
                    new = apply_command(state, command)
                except (IllegalActionError, UnsupportedError):
                    self.assertEqual(state_to_dict(state), before)
                    continue
                self.assertEqual(state_to_dict(state), before)
                self.assertEqual(check_invariants(new), [])
                state = new

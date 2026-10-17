"""ワザによる相手の強制交代（v0.4d）: バタフリー（PMCG2-007）の「ふきとばし」と、ワザの途中で相手が答える決定。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES）。分類（CONFIRMED・SUPPORTED・
UNRESOLVED）は docs/forced-switch-v0.4d.md、カードの照合は docs/butterfree-v0.4d.md。

- p.19（バタフリー）: ふきとばし（無無）20。最新の説明「相手を控えポケモンと入れ替える。入れ替わるポケモンは、相手が選ぶ。
  （相手に控えがいないとき、入れ替えはおこらない）」
- p.213（ポッポの「ふきとばし」のワザ解説）:「このワザの効果は、相手の対戦ポケモンが対象であり、相手の対戦ポケモンを
  ベンチにもどすというものです。入れ替えることが効果ではありません。…相手プレイヤーは、ベンチの控えポケモンから1匹を
  選んでバトル場に出すことになるのです。」
- p.159（ゴーストの「とうめい」の解説）:「「ふきとばし」は、相手の対戦ポケモンへの効果です。」
- p.89（わるいカメールの「こうらがえし」の解説）:「「ふきとばし」のダメージを受けたタイミングでは、まだバトル場にいる」
  （ダメージ → 入れ替え）、「その後、相手はそのダメージできぜつしなければ「スターブーメラン」の効果で手札にもどる」
- p.309 の手順 6: ダメージ → それ以外の効果。「処理の対象がなくなってしまっている場合、その内容は無視して」。
  「ワザを使っている最中に、他のことをしてはいけません」
- p.311・p.322: ベンチに戻ったら特殊状態・持続する効果は消える。ついているカード・ダメージカウンターはいっしょに移る
- p.321: 「ダメージを受けない」状態ならダメージの要素は無効、ダメージ以外の効果の要素は有効
- p.323: HP 以上のダメージできぜつ。サイドは相手側のプレイヤーが取る
- p.325: 「にげる」がおこなえない状態のポケモンでも、入れ替えると指示されたら入れ替える

盤面を直接作るテスト（``build_test_state``）は 1 か所の規定を確かめるためのもので、自然な対戦の結果ではない。正式な対戦
開始からの試験は tests/test_butterfree_games_v0_4d.py。
"""

import copy
import pickle
import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, Phase, PlayBasicToBench, PlayTrainer, PromoteActive,
    ResolveDecision, Retreat, TakePrize, UnsupportedError, UseAttack, apply_command, check_invariants, state_to_dict,
)
from kyuura_engine.decisions import FORCED_SWITCH
from kyuura_engine.effects import DEFAULT_EFFECTS, NO_BENCH, TARGET_KNOCKED_OUT, DamageAndForceSwitch
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import Phase as StatePhase

from tests.helpers import (
    BUTTERFREE, CATERPIE, DEFENDER, GRASS, GROWLITHE, H, KAKUNA, METAPOD, PLUSPOWER, PONYTA, RATTATA, SWITCH, T, VULPIX,
    WEEDLE, build_test_state, with_coin_results,
)

WHIRLWIND = 0
WHIRLWIND_LATEST = "相手を控えポケモンと入れ替える。入れ替わるポケモンは、相手が選ぶ。（相手に控えがいないとき、入れ替えはおこらない）"


def full(state):
    return state_to_dict(state, format_version=8)


def run(state, command):
    new = apply_command(state, command)
    return new, [dict(e) for e in new.log[len(state.log):]]


def kinds(events):
    return [e["kind"] for e in events]


def butterfree(**extra):
    """キャタピー → トランセル → バタフリーと 2 進化したバタフリー（盤面を直接作る。1 進化した番は状態に持たない）。"""
    return {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], **extra}


def board(mine=None, *, bench=(), hand=(), opponent=None, opponent_bench=(RATTATA, PONYTA), opponent_hand=(), turn=7, prizes=6,
          opponent_prizes=6, **kwargs):
    """プレイヤー 0 の番 ``turn`` の盤面（先攻はプレイヤー 0）。既定は 5 番に 2 進化した、無色 2 個を払えるバタフリー。"""
    return build_test_state([
        {"active": mine or butterfree(energy=[GRASS, GRASS]), "bench": list(bench), "hand": list(hand), "prizes": prizes},
        {"active": opponent or GROWLITHE, "bench": list(opponent_bench), "hand": list(opponent_hand), "prizes": opponent_prizes},
    ], current_player=0, turn_number=turn, **kwargs)


def assert_rejected(test, state, command, code, error=IllegalActionError):
    """拒否され、渡した状態（決定・場・ダメージ・ログ）も乱数も変わらない。"""
    before, fingerprint, log = full(state), rng_fingerprint(state.rng), state.log
    with test.assertRaises(error) as ctx:
        apply_command(state, command)
    test.assertEqual(ctx.exception.code, code, command)
    test.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
    test.assertIs(state.log, log)


def bench_ids(state, player):
    return tuple(p.pokemon_id for p in state.players[player].bench)


# ---------------------------------------------------------------- ワザの流れ（16.1・16.6）


class WhirlwindFlowTest(unittest.TestCase):
    def test_registration_and_card(self):
        """p.19: ふきとばし（無無）20。カード id とワザの位置で登録し、最新の説明・出典を書く。"""
        entry = DEFAULT_EFFECTS.attack_entry(BUTTERFREE, WHIRLWIND)
        self.assertIsInstance(entry.effect, DamageAndForceSwitch)
        self.assertEqual((entry.name_ja, entry.play_text_ja, entry.source), ("ふきとばし", WHIRLWIND_LATEST, "P43 p.19"))
        attack = board().card_def(board().players[0].active.card).attacks[WHIRLWIND]
        self.assertEqual((attack.damage, [c.value for c in attack.cost]), (20, ["colorless", "colorless"]))

    def test_damage_then_the_opponent_decides(self):
        """20 ダメージを与えたあと、ワザの途中の決定（FORCED_SWITCH）を出す。決定するのは相手（プレイヤー 1）で、番の
        プレイヤーはワザを使ったプレイヤー 0 のまま。選べるものは相手のベンチのポケモンの番号。番はまだ終わらない（p.309・
        p.89・p.213）。"""
        state = board()
        target = state.players[1].active
        new, events = run(state, UseAttack(0, WHIRLWIND))
        self.assertEqual(kinds(events), ["attack", "damage"])
        self.assertEqual((events[1]["amount"], events[1]["total_damage"]), (20, 20))
        d = new.decision
        self.assertEqual(new.phase, Phase.DECISION)  # 新しい段階は加えていない
        self.assertEqual((new.current_player, new.turn_number), (0, 7))
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices, d.resume),
                         (FORCED_SWITCH, 1, bench_ids(state, 1), 1, 1, "attack"))
        attacker = new.players[0].active
        self.assertEqual(d.context_value("use"), (0, attacker.pokemon_id, BUTTERFREE, WHIRLWIND))
        self.assertEqual(d.context_value("target"), target.pokemon_id)
        self.assertEqual(check_invariants(new), [])

    def test_resume_switches_and_ends_the_turn_once(self):
        """相手が選ぶと、ワザの続き（入れ替え）だけを処理して、ワザのあとの処理・番の終わり・ポケモンチェックを 1 回ずつ行う。
        ワザの再宣言・ダメージ・コインはない（乱数を使わない）。"""
        state = board()
        old = state.players[1].active
        new, _ = run(state, UseAttack(0, WHIRLWIND))
        fingerprint = rng_fingerprint(new.rng)
        chosen = new.decision.options[1]
        done, events = run(new, ResolveDecision(1, new.decision.id, (chosen,)))
        self.assertEqual(kinds(events), ["forced_switch", "turn_end", "pokemon_check", "turn_start", "draw"])
        log = [dict(e) for e in done.log]
        for kind in ("attack", "damage", "forced_switch", "turn_end", "pokemon_check"):
            self.assertEqual(sum(e["kind"] == kind and e["turn"] == 7 for e in log), 1, kind)
        self.assertEqual(rng_fingerprint(done.rng), fingerprint)
        p = done.players[1]
        self.assertEqual(p.active.pokemon_id, chosen)
        self.assertEqual(bench_ids(done, 1), (state.players[1].bench[0].pokemon_id, old.pokemon_id))  # 選んだ位置にもどる
        self.assertEqual(p.bench[1].damage, 20)  # ダメージは二重にならない
        self.assertEqual((done.phase, done.current_player, done.turn_number, done.decision), (Phase.MAIN, 1, 8, None))

    def test_one_bench_pokemon_still_asks_the_opponent(self):
        """控えが 1 匹でも、相手が選ぶ決定を出す（実装上の仮定。きぜつのあとの交代（PROMOTE_ACTIVE）と同じ形で、結果は同じ）。"""
        state = board(opponent_bench=(RATTATA,))
        new, _ = run(state, UseAttack(0, WHIRLWIND))
        self.assertEqual((new.decision.player, new.decision.options), (1, bench_ids(state, 1)))
        done, _ = run(new, ResolveDecision(1, new.decision.id, new.decision.options))
        self.assertEqual(done.players[1].active.pokemon_id, bench_ids(state, 1)[0])

    def test_any_bench_pokemon_can_be_chosen(self):
        """控えが 2 匹以上: どの控えを選んでも、そのポケモンがバトル場に出る（相手が選ぶ。p.19・p.213）。"""
        state = board(opponent_bench=(RATTATA, PONYTA, VULPIX, WEEDLE, CATERPIE))
        new, _ = run(state, UseAttack(0, WHIRLWIND))
        self.assertEqual(len(new.decision.options), 5)
        for index, chosen in enumerate(new.decision.options):
            with self.subTest(chosen=chosen):
                done, events = run(new, ResolveDecision(1, new.decision.id, (chosen,)))
                self.assertEqual(done.players[1].active.pokemon_id, chosen)
                self.assertEqual(done.players[1].bench[index].pokemon_id, state.players[1].active.pokemon_id)
                self.assertEqual(sorted(bench_ids(done, 1) + (chosen,)), sorted(bench_ids(state, 1) + (state.players[1].active.pokemon_id,)))

    def test_no_bench_no_switch_and_no_decision(self):
        """相手に控えがいなければ入れ替えはおこらない（最新の説明）。20 ダメージは与え、決定を出さずに番を終える。"""
        state = board(opponent_bench=())
        new, events = run(state, UseAttack(0, WHIRLWIND))
        self.assertEqual(kinds(events)[:3], ["attack", "damage", "forced_switch_skipped"])
        self.assertEqual(events[2]["reason"], NO_BENCH)
        self.assertEqual((new.phase, new.current_player, new.decision), (Phase.MAIN, 1, None))
        self.assertEqual(new.players[1].active.damage, 20)

    def test_not_enough_energy(self):
        """必要なエネルギー（無色 2 個）が足りなければワザを使えない（p.309 の手順 2）。状態も乱数も変わらない。"""
        assert_rejected(self, board(butterfree(energy=[GRASS])), UseAttack(0, WHIRLWIND), "INSUFFICIENT_ENERGY")

    def test_asleep_or_paralyzed_butterfree_cannot_attack(self):
        assert_rejected(self, board(butterfree(energy=[GRASS, GRASS], sleep=True)), UseAttack(0, WHIRLWIND), "POKEMON_ASLEEP")
        assert_rejected(self, board(butterfree(energy=[GRASS, GRASS], paralysis=6)), UseAttack(0, WHIRLWIND), "POKEMON_PARALYZED")


# ---------------------------------------------------------------- 誤った答え・決定を待つ間の操作（5.6・5.7・16.6・16.7）


class InvalidAnswerTest(unittest.TestCase):
    def setUp(self):
        self.start = board(bench=(PONYTA,))
        self.state = apply_command(self.start, UseAttack(0, WHIRLWIND))
        self.d = self.state.decision

    def test_wrong_answers_change_nothing(self):
        """どの誤った答えも、決定を残したまま拒否する。ダメージは二重にならず、ポケモンは動かず、番は終わらず、乱数は進まない。"""
        d = self.d
        own_bench = self.state.players[0].bench[0].pokemon_id
        their_active = self.state.players[1].active.pokemon_id
        options = d.options
        cases = [
            (ResolveDecision(0, d.id, (options[0],)), "NOT_YOUR_DECISION"),  # ワザを使ったプレイヤーが答える
            (ResolveDecision(1, d.id, (999,)), "INVALID_CHOICE"),  # ない番号
            (ResolveDecision(1, d.id, (their_active,)), "INVALID_CHOICE"),  # 相手のバトル場のポケモン（もどすポケモン）
            (ResolveDecision(1, d.id, (own_bench,)), "INVALID_CHOICE"),  # ワザを使ったプレイヤーのベンチのポケモン
            (ResolveDecision(1, d.id, (self.state.players[0].active.pokemon_id,)), "INVALID_CHOICE"),  # バタフリー自身
            (ResolveDecision(1, d.id - 1 if d.id > 1 else d.id + 1, (options[0],)), "WRONG_DECISION"),  # 古い（違う）決定の番号
            (ResolveDecision(1, d.id + 1, (options[0],)), "WRONG_DECISION"),
            (ResolveDecision(1, d.id, options), "INVALID_CHOICE_COUNT"),  # 複数を選ぶ
            (ResolveDecision(1, d.id, (options[0], options[0])), "INVALID_CHOICE_COUNT"),  # 同じものを 2 回（1 匹だけ選ぶので数で拒否）
            (ResolveDecision(1, d.id, ()), "INVALID_CHOICE_COUNT"),  # 選ばない
            (ResolveDecision(2, d.id, (options[0],)), "INVALID_PLAYER"),
        ]
        for command, code in cases:
            with self.subTest(command=command):
                assert_rejected(self, self.state, command, code)

    def test_no_decision_to_answer(self):
        """決定のない状態（ワザの前・入れ替えのあと）では答えられない（WRONG_PHASE）。"""
        assert_rejected(self, self.start, ResolveDecision(1, self.d.id, (self.d.options[0],)), "WRONG_PHASE")
        done = apply_command(self.state, ResolveDecision(1, self.d.id, (self.d.options[0],)))
        assert_rejected(self, done, ResolveDecision(1, self.d.id, (self.d.options[0],)), "WRONG_PHASE")
        assert_rejected(self, done, ResolveDecision(0, self.d.id, (self.d.options[0],)), "WRONG_PHASE")

    def test_other_commands_wait_for_the_decision(self):
        """相手の選択を待つ間は、ワザを使ったプレイヤーも相手も、ほかの操作をできない（p.309「ワザを使っている最中に、他のことを
        してはいけません」。WRONG_PHASE）。"""
        state = board(bench=(PONYTA,), hand=(GRASS, PLUSPOWER, RATTATA, BUTTERFREE),
                      opponent_hand=(GRASS, DEFENDER, VULPIX, KAKUNA), opponent_bench=(WEEDLE, PONYTA))
        state = apply_command(state, UseAttack(0, WHIRLWIND))
        for player in (0, 1):
            p = state.players[player]
            hand = {state.cards[u].card_id: u for u in p.hand}
            trainer = hand.get(PLUSPOWER, hand.get(DEFENDER))
            basic = hand.get(RATTATA, hand.get(VULPIX))
            evolution = hand.get(BUTTERFREE, hand.get(KAKUNA))
            commands = [
                AttachEnergy(player, hand[GRASS], p.active.card), PlayTrainer(player, trainer), EvolvePokemon(player, evolution, p.bench[0].pokemon_id),
                Retreat(player, (), p.bench[0].card), UseAttack(player, 0), UseAttack(player, 1), EndTurn(player),
                PlayBasicToBench(player, basic), TakePrize(player, 0), PromoteActive(player, p.bench[0].card),
            ]
            for command in commands:
                with self.subTest(command=command):
                    assert_rejected(self, state, command, "WRONG_PHASE")

    def test_resolving_twice_is_impossible(self):
        """正しい答えで再開は 1 回だけ。同じ答えをもう一度送っても、入れ替え・番の終わりは二重にならない。"""
        done = apply_command(self.state, ResolveDecision(1, self.d.id, (self.d.options[0],)))
        with self.assertRaises(IllegalActionError):
            apply_command(done, ResolveDecision(1, self.d.id, (self.d.options[0],)))
        self.assertEqual(sum(e["kind"] == "forced_switch" for e in done.log), 1)
        self.assertEqual(sum(e["kind"] == "turn_end" for e in done.log), 1)

    def test_switch_trainer_without_bench_is_still_unresolved(self):
        """「ふきとばし」の規定（控えがいなければ入れ替えない）で、トレーナーの「ポケモンいれかえ」の未解決の裁定
        （控えがいないときに使えるか。UNRESOLVED_SWITCH_WITHOUT_BENCH）を解消していない。"""
        state = board(hand=(SWITCH,))
        assert_rejected(self, state, PlayTrainer(0, state.players[0].hand[0]), "UNRESOLVED_SWITCH_WITHOUT_BENCH", UnsupportedError)


# ---------------------------------------------------------------- きぜつ・勝敗（3.2・16.1）


class KnockOutTest(unittest.TestCase):
    def test_lethal_damage_skips_the_switch(self):
        """20 ダメージで相手の対戦ポケモンがきぜつするなら、ベンチにもどす内容は対象がいないので無視する（p.309・p.213・p.89。
        SUPPORTED）。決定は出さず、ワザのあとのきぜつ・サイド・交代（相手がバトル場に出すポケモンを選ぶ。p.323）に進む。"""
        state = board(opponent={"card": RATTATA, "damage": 10})
        target = state.players[1].active
        new, events = run(state, UseAttack(0, WHIRLWIND))
        self.assertEqual(kinds(events), ["attack", "damage", "forced_switch_skipped", "knock_out"])
        self.assertEqual((events[2]["reason"], events[2]["pokemon_id"]), (TARGET_KNOCKED_OUT, target.pokemon_id))
        self.assertEqual((new.phase, new.decision.kind, new.decision.player), (Phase.TAKE_PRIZE, "take_prize", 0))
        new = apply_command(new, ResolveDecision(0, new.decision.id, (0,)))
        self.assertEqual((new.phase, new.decision.kind, new.decision.player), (Phase.PROMOTE_ACTIVE, "promote_active", 1))
        self.assertEqual(new.decision.options, bench_ids(state, 1))
        done, events = run(new, ResolveDecision(1, new.decision.id, (new.decision.options[1],)))
        self.assertEqual(kinds(events)[:2], ["promote_active", "turn_end"])
        self.assertEqual(done.players[1].active.pokemon_id, bench_ids(state, 1)[1])
        self.assertIn(target.card, done.players[1].discard)
        self.assertEqual((len(done.players[0].prizes), sum(e["kind"] == "forced_switch" for e in done.log)), (5, 0))

    def test_damage_below_hp_switches(self):
        """HP にちょうど届かないなら（残り 10）、きぜつしないので入れ替える。"""
        state = board(opponent={"card": RATTATA, "damage": 0})
        new, _ = run(state, UseAttack(0, WHIRLWIND))
        self.assertEqual(new.decision.kind, FORCED_SWITCH)
        self.assertEqual(new.players[1].active.damage, 20)

    def test_lethal_damage_without_bench_wins(self):
        """控えのいない相手をきぜつさせたら、代わりを出せない相手の負け（p.311）。対象がいないので、入れ替えなかった理由はきぜつ。"""
        state = board(opponent={"card": RATTATA, "damage": 10}, opponent_bench=())
        new, events = run(state, UseAttack(0, WHIRLWIND))
        self.assertEqual(events[2]["reason"], TARGET_KNOCKED_OUT)
        done = apply_command(new, ResolveDecision(0, new.decision.id, (0,)))
        self.assertEqual((done.phase, done.result.winner, done.decision), (Phase.GAME_OVER, 0, None))

    def test_last_prize_ends_the_game_without_a_choice(self):
        """最後のサイドを取ったら、その時点で勝敗が決まる（p.311・p.323）。相手は交代も入れ替えもしない。"""
        state = board(opponent={"card": RATTATA, "damage": 10}, prizes=1)
        new = apply_command(state, UseAttack(0, WHIRLWIND))
        done = apply_command(new, ResolveDecision(0, new.decision.id, (0,)))
        self.assertEqual((done.phase, done.result.winner, done.decision), (Phase.GAME_OVER, 0, None))
        self.assertFalse(any(e["kind"] in ("forced_switch", "promote_active") for e in done.log))

    def test_game_continues_after_the_choice(self):
        """入れ替えたあとは、相手の番が始まる（勝敗は決まらない）。"""
        state = board(prizes=1)
        new = apply_command(state, UseAttack(0, WHIRLWIND))
        done = apply_command(new, ResolveDecision(1, new.decision.id, (new.decision.options[0],)))
        self.assertEqual((done.phase, done.current_player, done.result), (Phase.MAIN, 1, None))


# ---------------------------------------------------------------- 強制交代で受け継ぐもの・消えるもの（6 章・16.2）


def defended_opponent(**opponent):
    """6 番にプレイヤー 1 が対戦ポケモンにディフェンダーをつけ（有効期限は次の相手の番 = 7 番の終わり）、7 番を返す
    （トレーナーは正式なコマンドでつけた。盤面の残りは直接作った）。"""
    state = build_test_state([
        {"active": butterfree(energy=[GRASS, GRASS]), "bench": [PONYTA]},
        {"active": opponent or {"card": GROWLITHE}, "bench": [RATTATA, PONYTA], "hand": [DEFENDER]},
    ], current_player=1, turn_number=6)
    state = apply_command(state, PlayTrainer(1, state.players[1].hand[0]))
    state = apply_command(state, ResolveDecision(1, state.decision.id, (state.players[1].active.pokemon_id,)))
    return apply_command(state, EndTurn(1))


class InheritanceTest(unittest.TestCase):
    def test_identity_damage_energy_trainers_and_stack_move_together(self):
        """ベンチにもどったポケモンの場のポケモンの番号・ダメージ・エネルギー・ついているトレーナー（有効期限も）・進化の重なり・
        場に出た番・進化した番は変わらない（p.311）。にげるエネルギーは払わない（「にげる」ではない。p.325）。ディフェンダーは
        ベンチにもどったポケモンについたまま、有効期限（7 番の終わり）にトラッシュされる（ログの pokemon_id がそのポケモン）。"""
        state = defended_opponent(card=KAKUNA, evolved_from=WEEDLE, energy=[GRASS, GRASS], damage=30)
        old = state.players[1].active
        self.assertEqual([t.discard_at_end_of_turn for t in old.trainers], [7])
        before = (old.pokemon_id, old.card, list(old.energy), old.evolution_stack, old.played_turn, old.evolved_turn)
        new = apply_command(state, UseAttack(0, WHIRLWIND))
        self.assertEqual(new.players[1].active.damage, 30)  # ディフェンダーで 20 − 20 = 0（ダメージを与えなかった）
        done, events = run(new, ResolveDecision(1, new.decision.id, (new.decision.options[0],)))
        moved = next(p for p in done.players[1].bench if p.pokemon_id == old.pokemon_id)
        self.assertEqual((moved.pokemon_id, moved.card, moved.energy, moved.evolution_stack, moved.played_turn, moved.evolved_turn),
                         before)
        self.assertEqual(moved.damage, 30)
        self.assertEqual(kinds(events)[:3], ["forced_switch", "discard_attached_trainer", "turn_end"])
        discard = events[1]
        self.assertEqual((discard["pokemon_id"], discard["card"], discard["turn"]), (old.pokemon_id, old.trainers[0].card, 7))
        self.assertIn(old.trainers[0].card, done.players[1].discard)
        self.assertEqual(sorted(done.players[1].discard), [old.trainers[0].card])  # エネルギーはトラッシュしていない

    def test_every_special_condition_is_cleared(self):
        """ベンチにもどったら、どく・ねむり・マヒ・こんらんは消える（p.311・p.322）。ねむり・マヒ状態でも入れ替える（p.325）。
        理由は forced_switch（トレーナーの switch と分ける）。どくの重複もいっしょに消える。"""
        for conditions in ({"poison": 10}, {"sleep": True}, {"paralysis": 6}, {"confusion": True}, {"poison": 10, "sleep": True},
                           {"poison": 10, "paralysis": 6}, {"poison": 10, "confusion": True}):
            with self.subTest(conditions=conditions):
                state = board(opponent={"card": GROWLITHE, **conditions})
                old = state.players[1].active
                names = old.conditions.names()
                new = apply_command(state, UseAttack(0, WHIRLWIND))
                done, events = run(new, ResolveDecision(1, new.decision.id, (new.decision.options[0],)))
                removed = [e for e in events if e["kind"] == "special_conditions_removed"]
                self.assertEqual([(e["pokemon_id"], e["conditions"], e["reason"]) for e in removed],
                                 [(old.pokemon_id, names, "forced_switch")])
                moved = next(p for p in done.players[1].bench if p.pokemon_id == old.pokemon_id)
                self.assertEqual(moved.conditions.names(), ())
                self.assertFalse(any(e["kind"] == "coin_flip" for e in events))  # こんらんでも「にげる」のコインは投げない

    def test_persistent_effect_is_removed(self):
        """「かたまる」で「ダメージを受けない」状態の相手: ダメージの要素は無効（p.321）だが、入れ替えは有効（ダメージ以外の効果）。
        ベンチにもどったので持続する効果は消える（p.311・p.322・p.89。理由 forced_switch）。"""
        state = board(opponent={"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": 6})
        old = state.players[1].active
        new, events = run(state, UseAttack(0, WHIRLWIND))
        self.assertEqual(kinds(events), ["attack", "damage_prevented"])
        self.assertEqual((new.decision.kind, new.players[1].active.damage), (FORCED_SWITCH, 0))
        done, events = run(new, ResolveDecision(1, new.decision.id, (new.decision.options[0],)))
        removed = [e for e in events if e["kind"] == "persistent_effect_removed"]
        self.assertEqual([(e["pokemon_id"], e["persistent_effect"], e["reason"]) for e in removed],
                         [(old.pokemon_id, "prevent_damage", "forced_switch")])
        moved = next(p for p in done.players[1].bench if p.pokemon_id == old.pokemon_id)
        self.assertEqual(moved.persistent_effects, ())

    def test_zero_damage_still_switches(self):
        """最終ダメージが 0 でも（ディフェンダー: 20 − 20）入れ替える。入れ替えはダメージを与えたことを条件にしていない。"""
        state = defended_opponent()
        new, events = run(state, UseAttack(0, WHIRLWIND))
        self.assertEqual((events[1]["kind"], events[1]["amount"]), ("damage", 0))
        self.assertEqual(new.decision.kind, FORCED_SWITCH)

    def test_retreat_failure_record_is_not_touched(self):
        """こんらんで「にげる」に失敗した記録は、番のプレイヤーのポケモンにしかない（v0.3c）。こんらん状態のバタフリーが「にげる」に
        失敗したあと「ふきとばし」を使っても、バタフリーの記録は変えず（番の終わりに消える）、入れ替えた相手のポケモンに記録は
        付かない。強制交代は「にげる」ではないので、新しい記録も付けない。"""
        state = board(butterfree(energy=[GRASS, GRASS, GRASS], confusion=True), bench=(PONYTA,))
        state = apply_command(with_coin_results(state, T), Retreat(0, (), state.players[0].bench[0].card))
        self.assertEqual(state.players[0].active.retreat_failed_turn, 7)
        new = apply_command(with_coin_results(state, H), UseAttack(0, WHIRLWIND))
        self.assertEqual(new.players[0].active.retreat_failed_turn, 7)
        done = apply_command(new, ResolveDecision(1, new.decision.id, (new.decision.options[0],)))
        self.assertTrue(all(p.retreat_failed_turn is None for pl in done.players for p in pl.in_play()))
        self.assertFalse(any(e["kind"] == "retreat_failed" and e["player"] == 1 for e in done.log))

    def test_log_records_who_did_what(self):
        """ログ forced_switch: 入れ替えられたプレイヤー・ワザを使ったプレイヤー・バタフリーの番号・ワザ・前後のバトル場の
        ポケモン（カードと番号）。トレーナーの switch のログの形は変えない。"""
        state = board()
        old = state.players[1].active
        new = apply_command(state, UseAttack(0, WHIRLWIND))
        chosen = new.decision.options[1]
        done, events = run(new, ResolveDecision(1, new.decision.id, (chosen,)))
        event = events[0]
        self.assertEqual(event, {
            "kind": "forced_switch", "turn": 7, "player": 1, "attacker": 0, "attacker_pokemon_id": state.players[0].active.pokemon_id,
            "effect": f"{BUTTERFREE}#0", "old_active": old.card, "new_active": done.players[1].active.card,
            "old_active_pokemon_id": old.pokemon_id, "new_active_pokemon_id": chosen,
        })
        trainer = build_test_state([{"active": GROWLITHE, "bench": [PONYTA], "hand": [SWITCH]}, {"active": RATTATA}])
        trainer = apply_command(trainer, PlayTrainer(0, trainer.players[0].hand[0]))
        trainer = apply_command(trainer, ResolveDecision(0, trainer.decision.id, trainer.decision.options))
        switch = next(dict(e) for e in trainer.log if e["kind"] == "switch")
        self.assertEqual(set(switch), {"kind", "turn", "player", "old_active", "new_active", "old_active_pokemon_id", "new_active_pokemon_id"})


# ---------------------------------------------------------------- こんらん（16.4）


class ConfusedButterfreeTest(unittest.TestCase):
    def test_heads_then_whirlwind(self):
        """こんらん状態のバタフリー: コインが「おもて」なら、ふきとばしをいつもどおり処理する（p.309 の手順 5・6）。"""
        state = board(butterfree(energy=[GRASS, GRASS], confusion=True))
        new, events = run(with_coin_results(state, H), UseAttack(0, WHIRLWIND))
        self.assertEqual(kinds(events), ["attack", "coin_flip", "confusion_check", "damage"])
        self.assertEqual(new.decision.kind, FORCED_SWITCH)

    def test_tails_no_damage_no_switch(self):
        """「うら」ならワザがこんらんし、自分に 20（弱点・抵抗力だけ）。相手へのダメージも入れ替えも決定もない。"""
        state = board(butterfree(energy=[GRASS, GRASS], confusion=True))
        new, events = run(with_coin_results(state, T), UseAttack(0, WHIRLWIND))
        self.assertEqual(kinds(events)[:4], ["attack", "coin_flip", "confusion_check", "confusion_damage"])
        self.assertFalse(any(e["kind"] in ("damage", "forced_switch", "forced_switch_skipped") for e in events))
        self.assertEqual((new.players[0].active.damage, new.players[1].active.damage, new.current_player), (20, 0, 1))

    def test_rng_is_reproducible(self):
        """同じ seed・同じコマンドなら同じ結果。ふきとばし自体はコインを使わない（こんらんのコインだけ）。"""
        results = set()
        for _ in range(3):
            state = board(butterfree(energy=[GRASS, GRASS], confusion=True), seed=11)
            new = apply_command(state, UseAttack(0, WHIRLWIND))
            if new.decision is not None:
                new = apply_command(new, ResolveDecision(1, new.decision.id, (new.decision.options[0],)))
            results.add((str(full(new)), rng_fingerprint(new.rng)))
        self.assertEqual(len(results), 1)


# ---------------------------------------------------------------- 決定を待つ状態の不変条件・複製・書き出し（13 章・16.6）


class PendingDecisionStateTest(unittest.TestCase):
    def setUp(self):
        self.state = apply_command(board(), UseAttack(0, WHIRLWIND))

    def test_copies_resume_the_same_way(self):
        """決定を待つ間の clone・deepcopy・pickle の写しで同じ答えをすると、同じ結果になる。元の状態は変わらない。"""
        d = self.state.decision
        command = ResolveDecision(1, d.id, (d.options[1],))
        expected = full(apply_command(self.state, command))
        before = full(self.state)
        for copied in (self.state.clone(), copy.deepcopy(self.state), pickle.loads(pickle.dumps(self.state))):
            self.assertEqual(full(copied), before)
            self.assertEqual(full(apply_command(copied, command)), expected)
        self.assertEqual(full(self.state), before)

    def test_serialization_keeps_format_8(self):
        """決定を待つ状態は、形式 2〜8 の decision（id・kind・player・options・resume・context）と current_player・turn_number で
        表せる（新しい形式は要らない）。形式 1 はワザの途中の決定を表せないので ValueError（黙って落とさない）。v0.6 で加えた形式 9
        （あまごいで手札からつけた枚数）でも、決定の項目は同じ。"""
        d = self.state.decision
        self.assertEqual(FORMAT_VERSIONS, (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14))  # v0.4d では 8 まで。9 は v0.6、10 は v0.31、11 は v0.44、12 は v0.47、13 は v0.48、14 は v0.49
        self.assertEqual(state_to_dict(self.state, format_version=9)["decision"], full(self.state)["decision"])
        data = full(self.state)
        self.assertEqual(data["decision"], {
            "id": d.id, "kind": FORCED_SWITCH, "player": 1, "options": list(d.options), "min_choices": 1, "max_choices": 1,
            "resume": "attack", "context": {"use": [0, self.state.players[0].active.pokemon_id, BUTTERFREE, 0],
                                            "target": self.state.players[1].active.pokemon_id},
        })
        self.assertEqual((data["phase"], data["current_player"], data["turn_number"]), ("decision", 0, 7))
        self.assertEqual(state_to_dict(self.state, format_version=7)["decision"], data["decision"])
        for version in range(1, 7):  # 進化したバタフリーがいるので、形式 1〜6 はもともと書き出せない（v0.4a）
            with self.assertRaises(ValueError):
                state_to_dict(self.state, format_version=version)
        # 進化していないポケモンのワザの途中の決定（テスト専用の効果）なら、形式 2 以上で同じ項目を書き出せ、形式 1 は ValueError
        from tests.helpers import FIGHTING, MACHOP, two_step_effects
        plain = build_test_state([{"active": {"card": MACHOP, "energy": [FIGHTING]}}, {"active": GROWLITHE, "bench": [RATTATA]}],
                                 effects=two_step_effects())
        plain = apply_command(plain, UseAttack(0, 0))
        self.assertEqual(plain.phase, Phase.DECISION)
        for version in range(2, 10):
            self.assertEqual(state_to_dict(plain, format_version=version)["decision"]["resume"], "attack")
        with self.assertRaises(ValueError):
            state_to_dict(plain)

    def test_invariants_reject_broken_decisions(self):
        """決定の形が「ふきとばし」と合わない状態は、不変条件で見つかる（決定するプレイヤー・種類・選べるもの・対象・続きの情報・
        番のプレイヤー・ワザのログ）。"""
        import dataclasses
        d = self.state.decision
        own_bench = board(bench=(PONYTA,))
        breakers = {
            "decision.player がワザを使ったプレイヤー": lambda s: setattr(s, "decision", dataclasses.replace(d, player=0)),
            "種類": lambda s: setattr(s, "decision", dataclasses.replace(d, kind="select_pokemon")),
            "選べるものが足りない": lambda s: setattr(s, "decision", dataclasses.replace(d, options=d.options[:1])),
            "選べるものにバトル場": lambda s: setattr(s, "decision", dataclasses.replace(d, options=(*d.options, s.players[1].active.pokemon_id))),
            "対象が違う": lambda s: setattr(s, "decision", dataclasses.replace(d, context=(d.context[0], ("target", d.options[0])))),
            "2 匹選ぶ": lambda s: setattr(s, "decision", dataclasses.replace(d, max_choices=2)),
            "続きの情報のプレイヤー": lambda s: setattr(s, "decision", dataclasses.replace(
                d, context=(("use", (1, *d.context_value("use")[1:])), d.context[1]))),
            "ワザのログがない": lambda s: setattr(s, "log", tuple(e for e in s.log if e["kind"] != "attack")),
        }
        self.assertEqual(check_invariants(self.state), [])
        for name, breaker in breakers.items():
            with self.subTest(name=name):
                broken = self.state.clone()
                breaker(broken)
                self.assertNotEqual(check_invariants(broken), [])
        self.assertEqual(check_invariants(own_bench), [])

    def test_state_phase_is_the_existing_decision_phase(self):
        self.assertIs(self.state.phase, StatePhase.DECISION)
        self.assertEqual(self.state.pending_prizes, {})
        self.assertEqual(self.state.pending_promotions, [])


if __name__ == "__main__":
    unittest.main()

"""v0.21: 突風（PMCG1-072）。最新の説明「相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。」（『ポケモンカードオフィシャルブック
2000』p.255。docs/gust-v0.21.md）。

規定と根拠（docs/gust-v0.21.md 3 章の GW1〜GW18）:

- 選ぶのは突風を使ったプレイヤー（GW2。最新の説明に「相手は」がない。p.255 の解説「相手のベンチからポケモンを選んでバトル場に呼んで
  きます」）。決定の ``player`` は使ったプレイヤーで、バタフリーの「ふきとばし」（相手が選ぶ。v0.4d の F3）とは違う。
- 選べるのは相手のベンチのポケモンだけ（GW3）。自分の場は関係しない（GW6）。相手に控えがいないときに使えるかは原典で決められない（GW5。
  ``UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH``）。
- 入れ替えはポケモンいれかえ（v0.2b）と同じ処理（``effects._switch_active_with_bench``）を相手の場で行う。にげるエネルギーを払わない・
  ついているカードとダメージカウンターはいっしょに移る・特殊状態と持続する効果は消える・ねむり・マヒでも入れ替える（GW7〜GW12。p.311・
  p.322・p.325。既存の記録の再利用）。ポケモンいれかえの入れ替えの規定は tests/test_trainers.py の ``SwitchTest`` が確かめているので、
  ここでは同じ行を複写せず、相手の場で起こることと、選ぶプレイヤーの違いを確かめる。
- トレーナーの効果なので「とうめい」ははたらかない（GW13。p.159。v0.9 の T29）。使っても番は続く（GW15。p.310）。

kyuura の記録: kyuura（研究の基準 3f34908）に、このカードの照合の記録（CC-）・最新の説明・p.255 のページの記録・GW5 の論点はない（報告事項。
research_links.json の engine_verified_without_kyuura_record・stop_codes の not_in_kyuura）。

盤面を直接作るテスト（``build_test_state``。規定 1 か所ずつ）と、正式な対戦開始（``new_game``・60 枚・サイド 6 枚）から使う統合テスト
（``NaturalGamesTest``。v0.20 の固定のデッキのディフェンダー 3 枚を突風 3 枚に置き換えた一時的なデッキ。tools/preset_deck_games.py）を
分けている。
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
    EndTurn, IllegalActionError, Phase, PlayTrainer, ResolveDecision, Retreat, UnsupportedError, UseAttack, apply_command, check_invariants,
    preset_deck, state_to_dict,
)
from kyuura_engine.cards import load_card_pool, read_verification
from kyuura_engine.decisions import SELECT_POKEMON
from kyuura_engine.effects import DEFAULT_EFFECTS, SwitchOpponentWithBench
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    DARK_WARTORTLE, DEFENDER, FIRE, GASTLY, GROWLITHE, GUST, HAUNTER, MACHOP, PONYTA, PSYCHIC, RATTATA, ROCKET_SQUIRTLE, ROCKETS_MOLTRES, SEEL,
    STARYU, SWITCH, VOLTORB, WATER, build_test_state,
)
from tests.log_audit import log_problems, serialization_problems

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import preset_deck_games as driver  # noqa: E402

LATEST = "相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。"
PRINTED = "相手の場の対戦ポケモンと控えポケモンを入れ替える。どの控えポケモンを出させるかは、自分が自由に選ぶことができる。相手に控えがいない場合は使えない。"
TURN = 5  # 自分（プレイヤー 0）の番。相手の番は 4（相手のポケモンが受けた効果は 4 番に与えたもの）


def full(state):
    return state_to_dict(state, format_version=9)


def snapshot(state):
    """拒否で変わらないことを確かめる値（書き出しの全体・乱数・ログ）。"""
    return full(state), rng_fingerprint(state.rng), tuple(state.log)


def board(their_active=STARYU, their_bench=(SEEL,), *, my_bench=(), hand=()):
    """自分（プレイヤー 0）の番の MAIN。手札の先頭が突風。"""
    return build_test_state([
        {"active": {"card": GROWLITHE, "energy": [FIRE]}, "bench": list(my_bench), "hand": [GUST, *hand]},
        {"active": their_active, "bench": list(their_bench)},
    ], turn_number=TURN)


def all_uids(state):
    """どのゾーンにもあるカードの uid（使用中のトレーナーを含む）。"""
    found = []
    for p in state.players:
        found += p.deck + p.hand + p.discard + p.prizes
        for pokemon in p.in_play():
            found += list(pokemon.cards()) + pokemon.energy + [t.card for t in pokemon.trainers]
    if state.trainer_in_use is not None:
        found.append(state.trainer_in_use.card)
    return found


class RegistrationTest(unittest.TestCase):
    def test_entry_follows_the_verified_latest_description(self):
        """登録は（カード id で）1 件。照合した写しの文面（第1弾の印刷の転記）と、実装がしたがう最新の説明（p.255）を分けて持つ。"""
        entry = DEFAULT_EFFECTS.trainer_entry(GUST)
        self.assertEqual(entry.effect, SwitchOpponentWithBench())
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), ("突風", PRINTED, LATEST, "P43 p.255"))
        definition = load_card_pool().get(GUST)
        self.assertTrue(definition.supported)
        self.assertEqual(definition.trainer_text_ja, PRINTED)
        record = read_verification()["cards"][GUST]
        self.assertEqual((record["page"], record["pdf_page"], record["checked_on"]), (255, 257, "2026-10-15"))
        # 図版（第1弾の版ではない可能性が高い）の文面は最新の説明と同じで、kyuura の写しと違う
        self.assertEqual((record["card_image_text_ja"], record["latest_description_ja"]), (LATEST, LATEST))
        self.assertEqual(record["status"], "不一致あり")
        self.assertEqual([m["kyuura"] for m in record["mismatches"]], [PRINTED])

    def test_no_card_specific_branch_and_no_forced_switch(self):
        """engine.py・resolution/ にこのカードの id・実装での分岐を加えていない。実装は「ふきとばし」の処理（FORCED_SWITCH・ログ forced_switch・
        ``attack_reaches``）を使わず、ポケモンいれかえと同じ入れ替えの関数を呼ぶ。

        v0.34: ナッシーの「テレポート」（ワザ。要素 ``programs.SelfSwitch``）が、ポケモンいれかえと同じ入れ替えの関数（``_switch_active_with_bench``）で
        ワザを使ったプレイヤー自身の場を入れ替える（docs/barrier-resume-coin-bonus-v0.34.md 6.4）。resolution/ でその関数を呼ぶのは、この 1 か所
        （``run.player`` の場）だけで、突風の実装・相手の場の入れ替えはない。"""
        expected_calls = {"programs.py": ["E._switch_active_with_bench(run.state, run.player, choices[0], effect=str(run.key))"]}
        for path in [ROOT / "kyuura_engine" / "engine.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(GUST, text)
                self.assertIsNone(re.search(r"SwitchOpponentWithBench|switch_opponent_with_bench", text))
                calls = [line.strip() for line in text.splitlines() if "_switch_active_with_bench(" in line]
                self.assertEqual(calls, expected_calls.get(path.name, []))
        import inspect

        from kyuura_engine.effects import SwitchWithBench
        code = "".join(inspect.getsource(getattr(SwitchOpponentWithBench, name))
                       for name in ("check_playable", "resolve", "resume", "decision_problems"))
        for used in ("FORCED_SWITCH", "forced_switch", "attack_reaches", "player=1 - use.player"):
            self.assertNotIn(used, code)
        for effect in (SwitchOpponentWithBench, SwitchWithBench):
            self.assertIn("_switch_active_with_bench(", inspect.getsource(effect.resume))


class UsableTest(unittest.TestCase):
    """使えるか（GW5・GW6）と、使う宣言の拒否（状態を変えない）。"""

    def assert_rejected(self, state, command, code, error=IllegalActionError):
        before = snapshot(state)
        with self.assertRaises(error) as ctx:
            apply_command(state, command)
        self.assertIs(type(ctx.exception), error)
        self.assertEqual(ctx.exception.code, code, command)
        self.assertEqual(snapshot(state), before)  # 拒否しても状態・乱数・ログは変わらない
        return ctx.exception

    def test_opponent_without_bench_is_unresolved(self):
        """GW5: 相手に控えポケモンがいないときに使えるかは、最新の説明・解説（p.255）・トレーナーの規定（p.310）から決められない。第1弾の
        印刷の文面の「相手に控えがいない場合は使えない」は最新の説明にないので使わない。カードを手札から出す前に止め、カードは手札に残る。
        自分のベンチがあってもなくても同じ。"""
        for my_bench in ((), (PONYTA,)):
            with self.subTest(my_bench=my_bench):
                state = board(their_bench=(), my_bench=my_bench)
                card = state.players[0].hand[0]
                error = self.assert_rejected(state, PlayTrainer(0, card), "UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH", UnsupportedError)
                self.assertIn("突風", str(error))
                self.assertIn(card, state.players[0].hand)
                self.assertIsNone(state.trainer_in_use)

    def test_one_opponent_bench_pokemon_is_enough_and_own_bench_does_not_matter(self):
        """止める場合の隣: 相手の控えが 1 匹なら使える。自分のベンチが 0 匹でも使える（GW6。最新の説明は相手の場だけを指す）。"""
        state = board(their_bench=(SEEL,), my_bench=())
        pending = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        self.assertEqual(pending.phase, Phase.DECISION)
        self.assertEqual(pending.decision.options, (state.players[1].bench[0].pokemon_id,))

    def test_rejected_declarations_do_not_change_state(self):
        """番でないプレイヤー・手札にないカード・決定を待つ間の宣言は拒否し、状態は変わらない（カードは手札のまま）。"""
        state = board(hand=(GUST,))
        first, second = state.players[0].hand[:2]
        self.assert_rejected(state, PlayTrainer(1, first), "NOT_YOUR_TURN")
        self.assert_rejected(state, PlayTrainer(0, state.players[1].active.card), "CARD_NOT_IN_HAND")
        pending = apply_command(state, PlayTrainer(0, first))
        self.assert_rejected(pending, PlayTrainer(0, second), "WRONG_PHASE")
        self.assertIn(second, pending.players[0].hand)


class ChoiceTest(unittest.TestCase):
    """GW2・GW3: 決定するのは使ったプレイヤーで、選べるのは相手のベンチのポケモンだけ。"""

    def setUp(self):
        self.state = board(their_bench=(SEEL, {"card": RATTATA, "damage": 10}, MACHOP), my_bench=(PONYTA,))
        self.card = self.state.players[0].hand[0]
        self.pending = apply_command(self.state, PlayTrainer(0, self.card))

    def test_decision_belongs_to_the_user(self):
        """決定のプレイヤーは突風を使ったプレイヤー（番のプレイヤー）で、相手ではない。番・番の番号は変えない。カードは使用中。"""
        d = self.pending.decision
        self.assertEqual((d.player, d.kind, d.resume, d.min_choices, d.max_choices), (0, SELECT_POKEMON, "trainer", 1, 1))
        self.assertEqual(d.context_value("use"), (0, self.card, GUST))
        self.assertEqual(d.options, tuple(b.pokemon_id for b in self.state.players[1].bench))
        self.assertEqual((self.pending.current_player, self.pending.turn_number), (0, TURN))
        self.assertEqual((self.pending.trainer_in_use.player, self.pending.trainer_in_use.card), (0, self.card))
        self.assertNotIn(self.card, self.pending.players[0].hand + self.pending.players[0].discard)
        self.assertEqual(check_invariants(self.pending), [])

    def test_opponent_cannot_answer(self):
        """相手の答えは拒否（NOT_YOUR_DECISION）。決定は待ったまま、カードは使用中のまま。"""
        before = snapshot(self.pending)
        d = self.pending.decision
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(self.pending, ResolveDecision(1, d.id, (d.options[0],)))
        self.assertEqual(ctx.exception.code, "NOT_YOUR_DECISION")
        self.assertEqual(snapshot(self.pending), before)

    def test_invalid_choices_keep_the_decision_waiting(self):
        """自分の場のポケモン・相手の対戦ポケモン・場にいない番号・0 個・2 個・同じものを 2 回は拒否。拒否のあとも決定は同じ番号で待ち、
        突風は使用中（手札にもトラッシュにもない。なくならない）。そのあと正しい答えで続けられる。"""
        d = self.pending.decision
        p0, p1 = self.state.players
        wrong = [((p0.active.pokemon_id,), "INVALID_CHOICE"), ((p0.bench[0].pokemon_id,), "INVALID_CHOICE"),
                 ((p1.active.pokemon_id,), "INVALID_CHOICE"), ((99,), "INVALID_CHOICE"), ((), "INVALID_CHOICE_COUNT"),
                 ((d.options[0], d.options[1]), "INVALID_CHOICE_COUNT"), ((d.options[0], d.options[0]), "INVALID_CHOICE_COUNT")]
        for choices, code in wrong:
            with self.subTest(choices=choices):
                before = snapshot(self.pending)
                with self.assertRaises(IllegalActionError) as ctx:
                    apply_command(self.pending, ResolveDecision(0, d.id, choices))
                self.assertEqual(ctx.exception.code, code)
                self.assertEqual(snapshot(self.pending), before)
                self.assertEqual(self.pending.decision, d)
                self.assertEqual(self.pending.trainer_in_use.card, self.card)
                self.assertEqual(Counter(all_uids(self.pending)), Counter(list(self.pending.cards)))
        done = apply_command(self.pending, ResolveDecision(0, d.id, (d.options[2],)))
        self.assertEqual(done.players[1].active.pokemon_id, d.options[2])

    def test_choosing_a_specific_one_among_many(self):
        """3 匹のどれを選んでも、選んだポケモンがバトル場に出て、もとの対戦ポケモンは選んだポケモンのいたベンチの位置に入る。ほかの控えは
        動かない。自分の場は変わらない。"""
        p1 = self.state.players[1]
        for index in range(3):
            with self.subTest(index=index):
                chosen = p1.bench[index]
                done = apply_command(self.pending, ResolveDecision(0, self.pending.decision.id, (chosen.pokemon_id,)))
                q1 = done.players[1]
                self.assertEqual(q1.active.pokemon_id, chosen.pokemon_id)
                expected = [b.pokemon_id for b in p1.bench]
                expected[index] = p1.active.pokemon_id
                self.assertEqual([b.pokemon_id for b in q1.bench], expected)
                mine, before = full(done)["players"][0], full(self.state)["players"][0]
                self.assertEqual((mine["active"], mine["bench"], mine["discard"]), (before["active"], before["bench"], [self.card]))
                self.assertEqual(check_invariants(done), [])


class SwitchedPokemonTest(unittest.TestCase):
    """GW7〜GW12: 相手の場で入れ替えたときに変わるもの・変わらないもの（ポケモンいれかえと同じ処理。既存の規定の再利用）。"""

    def use(self, state, index=0):
        pending = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        chosen = state.players[1].bench[index].pokemon_id
        return apply_command(pending, ResolveDecision(0, pending.decision.id, (chosen,)))

    def test_conditions_persistent_effects_and_attached_cards(self):
        """ベンチにもどった相手のポケモンの特殊状態（どく・ねむり／マヒ／こんらん）と、ワザによる持続する効果（かたまる・ほのおのかべ・
        こうらがえし）は消える（p.322。ログの reason は switch）。ついているエネルギー・ディフェンダー（トラッシュする番も）・ダメージ
        カウンター・進化の重なり・場のポケモンの番号は変わらない（p.311）。ねむり・マヒでも入れ替える（p.325）。"""
        # 持続する効果は、そのワザを持つカードが自分に与えたもの（ほのおのかべは R団のファイヤー、こうらがえしはわるいカメール）
        cases = {
            "sleep_poison_prevent": {"card": HAUNTER, "evolved_from": GASTLY, "energy": [PSYCHIC, PSYCHIC],
                                     "poison": 10, "sleep": True, "prevent_damage": TURN - 1},
            "paralysis_retaliation": {"card": ROCKETS_MOLTRES, "energy": [FIRE], "paralysis": TURN - 1, "retaliation": TURN - 1},
            "confusion_shell": {"card": DARK_WARTORTLE, "evolved_from": ROCKET_SQUIRTLE, "energy": [WATER],
                                "confusion": True, "retaliation_received": TURN - 1},
        }
        for name, spec in cases.items():
            with self.subTest(case=name):
                old_spec = {**spec, "damage": 20, "trainers": [(DEFENDER, TURN)]}
                state = board(their_active=old_spec, their_bench=(SEEL,))
                old = state.players[1].active
                since = len(state.log)
                done = self.use(state)
                moved = next(b for b in done.players[1].bench if b.pokemon_id == old.pokemon_id)
                self.assertFalse(moved.conditions.poison or moved.conditions.exclusive)
                self.assertEqual(moved.persistent_effects, ())
                self.assertEqual((moved.card, moved.evolution_stack, moved.energy, moved.damage, moved.trainers),
                                 (old.card, old.evolution_stack, old.energy, old.damage, old.trainers))
                kinds = [e["kind"] for e in done.log[since:]]
                self.assertEqual(kinds, ["play_trainer", "switch", "special_conditions_removed", "persistent_effect_removed", "discard_trainer"])
                for e in done.log[since + 2:since + 4]:
                    self.assertEqual((e["player"], e["pokemon_id"], e["reason"]), (1, old.pokemon_id, "switch"))
                self.assertEqual(done.players[1].active.conditions, state.players[1].bench[0].conditions)  # 出たポケモンは何も受けていない
                # 盤面を作ったテストなので、ログの監査（対戦の最初からのログが要る）は NaturalGamesTest で確かめる
                self.assertEqual((check_invariants(done), serialization_problems(done)), ([], []))

    def test_attached_defender_still_expires_at_its_turn(self):
        """ついているディフェンダーはポケモンといっしょにベンチに移り、有効期限（次の相手の番 = この番の終わり）にトラッシュする。"""
        state = board(their_active={"card": STARYU, "trainers": [(DEFENDER, TURN)]}, their_bench=(SEEL,))
        defender = state.players[1].active.trainers[0].card
        done = self.use(state)
        self.assertEqual([t.card for t in done.players[1].bench[0].trainers], [defender])
        ended = apply_command(done, EndTurn(0))
        self.assertIn(defender, ended.players[1].discard)
        self.assertEqual(ended.players[1].bench[0].trainers, [])

    def test_no_retreat_cost_and_retreat_is_unaffected(self):
        """にげるではない（p.325）。相手のポケモンのエネルギーは払わず、トラッシュしたのは突風だけ。自分は、そのあとも「にげる」ができる
        （p.311。回数の制限はない）。相手のポケモンに「にげる」の失敗の記録はない（記録は番のプレイヤーのポケモンにだけ付く。v0.3c）。"""
        state = board(their_active={"card": STARYU, "energy": [WATER]}, their_bench=(SEEL,), my_bench=(RATTATA,))
        old = state.players[1].active
        done = self.use(state)
        moved = done.players[1].bench[0]
        self.assertEqual((moved.pokemon_id, moved.energy, moved.retreat_failed_turn), (old.pokemon_id, old.energy, None))
        self.assertEqual(done.players[1].discard, [])
        self.assertEqual(done.players[0].discard, [state.players[0].hand[0]])
        retreated = apply_command(done, Retreat(0, tuple(done.players[0].active.energy), done.players[0].bench[0].card))
        self.assertEqual(retreated.players[0].active.card, state.players[0].bench[0].card)

    def test_transparency_is_not_evaluated(self):
        """「とうめい」はワザによるダメージや効果だけにはたらき、トレーナーの効果は受ける（p.159。T29）。相手のベンチの「とうめい」のゴーストを
        呼んでも、バトル場の「とうめい」のゴーストをベンチにもどしても、コインを投げない（乱数を使わない）。"""
        haunter = {"card": HAUNTER, "evolved_from": GASTLY}
        for their_active, their_bench in ((STARYU, (haunter,)), (haunter, (SEEL,))):
            with self.subTest(active=their_active):
                state = board(their_active=their_active, their_bench=their_bench)
                done = self.use(state)
                self.assertEqual(rng_fingerprint(done.rng), rng_fingerprint(state.rng))
                self.assertFalse([e for e in done.log if e["kind"] in ("coin_flip", "evade_check", "attack_evaded")])
                self.assertEqual(done.players[1].active.pokemon_id, state.players[1].bench[0].pokemon_id)


class TurnAndConservationTest(unittest.TestCase):
    def test_same_turn_continues_and_the_attack_hits_the_new_active(self):
        """GW15: 使っても番は終わらない（p.310）。そのあとのワザは、入れ替えで出た相手の対戦ポケモンにダメージを与える（ガーディの「ほのお」
        20。ビリリダマは HP 40 なので残る）。"""
        state = build_test_state([
            {"active": {"card": GROWLITHE, "energy": [FIRE, FIRE]}, "hand": [GUST]},
            {"active": STARYU, "bench": [VOLTORB]},
        ], turn_number=TURN)
        pending = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        target = pending.decision.options[0]
        done = apply_command(pending, ResolveDecision(0, pending.decision.id, (target,)))
        self.assertEqual((done.phase, done.current_player, done.turn_number, done.result), (Phase.MAIN, 0, TURN, None))
        self.assertIsNone(done.trainer_in_use)
        attacked = apply_command(done, UseAttack(0, 0))
        hits = [e for e in attacked.log if e["kind"] == "damage" and e["turn"] == TURN]
        self.assertEqual([(e["pokemon"], e["amount"]) for e in hits], [(done.players[1].active.card, 20)])
        self.assertEqual((attacked.players[1].active.pokemon_id, attacked.players[1].active.damage), (target, 20))

    def test_card_conservation_and_the_caller_state(self):
        """カードの保存則（決定を待つ間の使用中のカードを含む）。``apply_command`` は渡された状態を変えない（宣言・答えのどちらも）。"""
        state = board(their_bench=(SEEL, MACHOP))
        expected = Counter(list(state.cards))
        self.assertEqual(Counter(all_uids(state)), expected)
        before = snapshot(state)
        pending = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        self.assertEqual(snapshot(state), before)
        self.assertEqual(Counter(all_uids(pending)), expected)
        pending_before = snapshot(pending)
        done = apply_command(pending, ResolveDecision(0, pending.decision.id, (pending.decision.options[1],)))
        self.assertEqual(snapshot(pending), pending_before)
        self.assertEqual(Counter(all_uids(done)), expected)

    def test_pending_decision_survives_copy_and_pickle(self):
        """決定を待つ状態は、複製・deepcopy・pickle のあとでも同じ答えで同じ結果になる（使用中のカードは形式 3 以上で書き出せる）。"""
        state = board(their_bench=(SEEL, MACHOP))
        pending = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        command = ResolveDecision(0, pending.decision.id, (pending.decision.options[1],))
        expected = full(apply_command(pending, command))
        for copied in (pending.clone(), copy.deepcopy(pending), pickle.loads(pickle.dumps(pending))):
            self.assertEqual(full(copied), full(pending))
            self.assertEqual(full(apply_command(copied, command)), expected)
        with self.assertRaises(ValueError):
            state_to_dict(pending, format_version=2)  # 使用中のトレーナーは形式 1・2 で書き出せない（黙って落とさない）

    def test_switch_trainer_on_own_side_is_unchanged(self):
        """入れ替えの関数を共通にしたあとも、ポケモンいれかえは自分の場を入れ替え、ログ switch の形（player は使ったプレイヤー）は v0.20 と同じ。"""
        state = build_test_state([
            {"active": {"card": GROWLITHE, "poison": 10}, "bench": [PONYTA], "hand": [SWITCH]},
            {"active": STARYU, "bench": [SEEL]},
        ], turn_number=TURN)
        pending = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        self.assertEqual(pending.decision.options, (state.players[0].bench[0].pokemon_id,))
        done = apply_command(pending, ResolveDecision(0, pending.decision.id, pending.decision.options))
        switch = next(dict(e) for e in done.log if e["kind"] == "switch")
        self.assertEqual(set(switch), {"kind", "turn", "player", "old_active", "new_active", "old_active_pokemon_id", "new_active_pokemon_id"})
        self.assertEqual(switch["player"], 0)
        self.assertEqual(full(done)["players"][1], full(state)["players"][1])


class NaturalGamesTest(unittest.TestCase):
    """正式な対戦開始（``new_game``・60 枚・サイド 6 枚）から、v0.20 の固定のデッキのディフェンダー 3 枚を突風 3 枚に置き換えた一時的なデッキ
    で、席を入れかえて 6 局ずつ（tools/preset_deck_games.py の ``--variant gust``）。突風を山札から引き、使い、相手の控えポケモンを選んで
    入れ替え、その番にワザを使った場面が自然に起こることを確かめる（盤面は作らない）。"""

    GAMES = 6

    @classmethod
    def setUpClass(cls):
        cls.results = driver.run(cls.GAMES, keep_state=True, variant="gust")

    def test_presets_are_unchanged(self):
        """公開の固定のデッキは変えていない（突風を含まない）。一時的なデッキは 60 枚・ディフェンダー 1 枚・突風 3 枚。"""
        for deck_id in (driver.DECK_A, driver.DECK_B):
            with self.subTest(deck=deck_id):
                self.assertNotIn(GUST, preset_deck(deck_id).counts())
                self.assertEqual(preset_deck(deck_id).counts()[DEFENDER], 4)
                cards = Counter(driver.deck_cards(deck_id, "gust"))
                self.assertEqual((sum(cards.values()), cards[GUST], cards[DEFENDER]), (60, 3, 1))

    def test_gust_is_drawn_used_and_followed_by_an_attack(self):
        uses = [u | {"seed": r["seed"]} for r in self.results for u in r["gust_uses"]]
        self.assertTrue(uses)
        self.assertTrue(all(u["switched"] for u in uses))  # どれも相手の場を入れ替えた（ログ switch の player は相手）
        followed = [u for u in uses if u.get("hit_new_active")]
        self.assertTrue(followed)  # 入れ替えたあと、その番のワザで、出た相手の対戦ポケモンにダメージを与えた
        policy = Counter()
        for r in self.results:
            policy.update(r["policy"])
        self.assertGreater(policy["gust_chose_not_first"], 0)  # 複数の候補から、最初ではないものを選んだ
        self.assertGreater(policy["gust_kept_no_opponent_bench"], 0)  # 相手に控えがいない番は使わない（GW5）
        # 使った突風は、山札から引いた（ログ draw。最初の手札を含む）かサイドから取った（take_prize）カード。山札から引いたものがある
        origins = Counter()
        for r in self.results:
            state = r["state"]
            for i, e in enumerate(state.log):
                if e["kind"] == "play_trainer" and state.cards[e["card"]].card_id == GUST:
                    came = next(x["kind"] for x in reversed(state.log[:i])
                                if (x["kind"] == "draw" and e["card"] in x["cards"]) or (x["kind"] == "take_prize" and x["card"] == e["card"]))
                    origins[came] += 1
        self.assertEqual(sum(origins.values()), len(uses))
        self.assertGreater(origins["draw"], 0)

    def test_every_game_is_classified_and_audited(self):
        outcomes = Counter(r["outcome"] for r in self.results)
        self.assertEqual(sum(outcomes.values()), 2 * self.GAMES)
        self.assertEqual(outcomes["internal_error"] + outcomes["unexpected_rejection"], 0, [r.get("error") for r in self.results])
        for r in self.results:
            state = r["state"]
            with self.subTest(seed=r["seed"], decks=r["decks"]):
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])
                self.assertFalse(r["unresolved_rejections"])  # 手順は相手に控えがいないときに使わないので、GW5 で拒否されない


if __name__ == "__main__":
    unittest.main()

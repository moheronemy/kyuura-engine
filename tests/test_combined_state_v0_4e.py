"""進化・特殊状態・持続する効果・ついているトレーナー・強制交代・きぜつの組み合わせの監査（v0.4e。docs/interaction-matrix-v0.4e.md）。

1 か所の規定ずつ確かめてきた v0.4a〜v0.4d の処理を、組み合わせの表（段階 × 場所 × 特殊状態 × 持続する効果 × ついている
カード × 退場の経路）で確かめる。盤面は ``build_test_state`` で直接作る（表の 1 マスごとに 1 つの規定を確かめるテスト）。
自然な対戦で起こる組み合わせは tests/test_combined_games_v0_4e.py で数える。自然な対戦では起こらない（盤面を直接作った）
マスは、表の分類（docs/interaction-matrix-v0.4e.md 2 章の「作成可能」）に書き、自然な対戦の結果としては数えない。

根拠の誌面（『ポケモンカードオフィシャルブック2000』）:

- 進化（p.309・p.310。手順 3「特殊状態や持続する効果から回復」、ダメージカウンター・エネルギー・ついているトレーナーは受け継ぐ）、
  2 進化（p.316・p.319）。kyuura NEO-2000-OFFICIAL-RULES
- 特殊状態（p.322。どくはほかと重複、ねむり・マヒ・こんらんはたがいに重複しない。ベンチに戻る・進化で消える）
- 持続する効果（p.322・p.323。ベンチに戻る・進化・きぜつ・期限（p.236・p.18 のワザ解説）で消える）
- にげる（pp.310〜311。ねむり・マヒは宣言できない、こんらんはコイン）、ポケモンいれかえ（p.254・p.325）、
  ふきとばし（p.19・p.213・p.89。入れ替えは「にげる」ではない。p.325）
- きぜつ（p.313・p.323。重なったカード・ついていたカードをすべてトラッシュ、サイドは 1 枚）
"""

import unittest

from kyuura_engine import (
    EndTurn, EvolvePokemon, IllegalActionError, PlayTrainer, ResolveDecision, Retreat, TakePrize, UseAttack, apply_command,
    check_invariants, state_to_dict,
)
from kyuura_engine.decisions import FORCED_SWITCH
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import Phase

from tests.helpers import (
    BEEDRILL, BUTTERFREE, CATERPIE, DEFENDER, DEWGONG, GRASS, H, KAKUNA, METAPOD, PARAS, PARASECT, PLUSPOWER, PONYTA, RATTATA,
    SEEL, SWITCH, T, WATER, WEEDLE, build_test_state, uids, with_coin_results,
)

TURN = 5  # 先攻（プレイヤー 0）の 3 回目の番。進化できる（p.310）

# 進化の系統: (名前, 進化前のカード, 進化後のカード, 進化前のカードの下のカード, エネルギー, 次の段階のカード)
LINES = (
    ("パラス→パラセクト", PARAS, PARASECT, (), GRASS, None),
    ("パウワウ→ジュゴン", SEEL, DEWGONG, (), WATER, None),
    ("キャタピー→トランセル", CATERPIE, METAPOD, (), GRASS, BUTTERFREE),
    ("ビードル→コクーン", WEEDLE, KAKUNA, (), GRASS, BEEDRILL),
    ("トランセル→バタフリー", METAPOD, BUTTERFREE, (CATERPIE,), GRASS, None),
    ("コクーン→スピアー", KAKUNA, BEEDRILL, (WEEDLE,), GRASS, None),
)



def condition_states(turn):
    """特殊状態の 8 通り（p.322）。マヒは前の番（``turn - 1``。相手の番）に受けた（自分のポケモンなら、回復するのは今の番の
    終わり。p.323 の 4。相手のポケモンなら、次の相手の番の終わり）。"""
    return (
        ("なし", {}),
        ("どく", {"poison": 10}),
        ("ねむり", {"sleep": True}),
        ("マヒ", {"paralysis": turn - 1}),
        ("こんらん", {"confusion": True}),
        ("どく+ねむり", {"poison": 10, "sleep": True}),
        ("どく+マヒ", {"poison": 10, "paralysis": turn - 1}),
        ("どく+こんらん", {"poison": 10, "confusion": True}),
    )


CONDITION_STATES = condition_states(TURN)
# 2 進化ポケモンが今の番より前に進化していられる番（先攻の 4 回目の番。1 進化は 3 番か 5 番、2 進化は 5 番。後攻は 4 番・6 番）
LATER_TURN = 7

# 自分の番に自分のポケモンについているトレーナー: プラスパワーは今の番に使った（今の番の終わりにトラッシュ）、ディフェンダーも
# 今の番に使った（次の相手の番の終わりにトラッシュ）
ATTACHMENTS = (
    ("なし", ()),
    ("プラスパワー", ((PLUSPOWER, TURN),)),
    ("ディフェンダー", ((DEFENDER, TURN + 1),)),
    ("両方", ((PLUSPOWER, TURN), (DEFENDER, TURN + 1))),
    ("ディフェンダー 2 枚", ((DEFENDER, TURN + 1), (DEFENDER, TURN + 1))),
)


def spec(card, below=(), energy=GRASS, **extra):
    data = {"card": card, "damage": 20, "energy": list(energy) if isinstance(energy, (list, tuple)) else [energy], **extra}
    if below:
        data["evolved_from"] = below[0] if len(below) == 1 else list(below)
    return data


def full(state):
    return state_to_dict(state, format_version=8)


def new_events(before, after):
    return [dict(e) for e in after.log[len(before.log):]]


def snapshot(pokemon):
    """進化・入れ替えで変わらないはずの項目（p.310・p.311）。"""
    return {
        "pokemon_id": pokemon.pokemon_id,
        "damage": pokemon.damage,
        "energy": list(pokemon.energy),
        "trainers": list(pokemon.trainers),
        "played_turn": pokemon.played_turn,
    }


class EvolutionCombinationTest(unittest.TestCase):
    """進化（たね → 1 進化、1 進化 → 2 進化）× 場所（バトル場・ベンチ）× 特殊状態 8 通り × ついているトレーナー × にげるの失敗の
    記録 × 持続する効果。進化したら特殊状態・持続する効果・失敗の記録が別々に消え、ダメージ・エネルギー・ついているトレーナー
    （有効期限も）・場のポケモンの番号・場に出た番は変わらない（p.310。v0.4a の E8'）。乱数は使わない。"""

    def evolve_and_check(self, line, place, conditions=(), attachments=(), *, retreat_failed=False, prevent=False):
        name, below, above, stack, energy, _ = line
        extra = dict(conditions)
        if attachments:
            extra["trainers"] = list(attachments)
        if retreat_failed:
            extra["retreat_failed_turn"] = TURN
        if prevent:
            extra["prevent_damage"] = TURN  # 盤面を直接作った（自然な対戦では、かたまるを使った番は終わる）
        evolving = spec(below, stack, energy, **extra)
        other = {"card": RATTATA}
        player0 = {"active": evolving, "bench": [other]} if place == "active" else {"active": other, "bench": [evolving]}
        player0["hand"] = [above]
        state = build_test_state([player0, {"active": RATTATA, "bench": [PONYTA]}], turn_number=TURN)
        self.assertEqual(check_invariants(state), [])
        target = state.players[0].active if place == "active" else state.players[0].bench[0]
        before_card, before_stack, kept = target.card, target.evolution_stack, snapshot(target)
        had_conditions = bool(target.conditions.names())
        fingerprint = rng_fingerprint(state.rng)

        after = apply_command(state, EvolvePokemon(0, uids(state, 0, "hand", above)[0], target.pokemon_id))
        evolved = after.find_pokemon(target.pokemon_id)[1]
        self.assertEqual(after.cards[evolved.card].card_id, above)
        self.assertEqual(evolved.evolution_stack, (*before_stack, before_card))
        self.assertEqual(evolved.evolved_turn, TURN)
        self.assertEqual(snapshot(evolved), kept)
        self.assertEqual((evolved.conditions.names(), evolved.persistent_effects, evolved.retreat_failed_turn), ((), (), None))
        self.assertIs(evolved, after.players[0].active if place == "active" else after.players[0].bench[0])
        events = new_events(state, after)
        expected = ["evolve"]
        if had_conditions:
            expected.append("special_conditions_removed")
        if prevent:
            expected.append("persistent_effect_removed")
        if retreat_failed:
            expected.append("retreat_failure_cleared")
        self.assertEqual([e["kind"] for e in events], expected)
        self.assertTrue(all(e.get("reason", "evolve") == "evolve" for e in events))
        self.assertEqual(rng_fingerprint(after.rng), fingerprint)
        self.assertEqual(check_invariants(after), [])
        # 書き出し: 進化したポケモンは形式 7 以上（v0.4a）。持続する効果は消えたので形式 7 でも書ける
        with self.assertRaises(ValueError):
            state_to_dict(after, format_version=6)
        state_to_dict(after, format_version=7)
        self.assertEqual(full(apply_command(after.clone(), EndTurn(0)))["turn_number"], TURN + 1)
        return state, after

    def test_active_conditions_and_attachments(self):
        for line in LINES:
            for cond_name, conditions in CONDITION_STATES:
                for attach_name, attachments in ATTACHMENTS:
                    with self.subTest(line=line[0], conditions=cond_name, attachments=attach_name):
                        self.evolve_and_check(line, "active", conditions.items(), attachments)

    def test_bench_with_defender(self):
        """ベンチのポケモンは特殊状態にならない（p.322）。ディフェンダーはベンチのポケモンにもつく（p.257）。"""
        for line in LINES:
            for attach_name, attachments in (("なし", ()), ("ディフェンダー", ((DEFENDER, TURN + 1),))):
                with self.subTest(line=line[0], attachments=attach_name):
                    self.evolve_and_check(line, "bench", (), attachments)

    def test_retreat_failure_record(self):
        """こんらんで「にげる」に失敗した記録（p.311）は、進化で消える（v0.4a。SUPPORTED）。バトル場のこんらん（自然な対戦で起こる）と、
        「ポケモンいれかえ」でベンチに戻ってこんらんが消えたポケモン（自然な対戦で起こる。記録は番の終わりまで残る）の両方。"""
        for line in LINES:
            with self.subTest(line=line[0], place="active"):
                self.evolve_and_check(line, "active", {"confusion": True}.items(), retreat_failed=True)
            with self.subTest(line=line[0], place="bench"):
                self.evolve_and_check(line, "bench", (), retreat_failed=True)

    def test_persistent_effect_is_removed_on_evolution(self):
        """進化で持続する効果が消える（p.310・p.323）。効果を与えた番に進化する盤面は自然な対戦では起こらない（作成可能）。"""
        for line in LINES:
            for cond_name, conditions in CONDITION_STATES:
                with self.subTest(line=line[0], conditions=cond_name):
                    self.evolve_and_check(line, "active", conditions.items(), prevent=True)

    def test_same_turn_second_evolution_is_rejected(self):
        """今の番に進化したポケモンは、同じ番にもう一度進化できない（p.310。``EVOLVED_THIS_TURN``）。状態・乱数は変わらない。"""
        for line in LINES:
            if line[5] is None:
                continue
            for cond_name, conditions in CONDITION_STATES:
                with self.subTest(line=line[0], conditions=cond_name):
                    stage2 = build_test_state(
                        [{"active": spec(line[1], line[3], line[4], **dict(conditions)), "bench": [{"card": RATTATA}],
                          "hand": [line[2], line[5]]}, {"active": RATTATA}], turn_number=TURN)
                    target = stage2.players[0].active.pokemon_id
                    stage2 = apply_command(stage2, EvolvePokemon(0, uids(stage2, 0, "hand", line[2])[0], target))
                    before, fingerprint = full(stage2), rng_fingerprint(stage2.rng)
                    with self.assertRaises(IllegalActionError) as ctx:
                        apply_command(stage2, EvolvePokemon(0, uids(stage2, 0, "hand", line[5])[0], target))
                    self.assertEqual(ctx.exception.code, "EVOLVED_THIS_TURN")
                    self.assertEqual((full(stage2), rng_fingerprint(stage2.rng)), (before, fingerprint))

    def test_pluspower_keeps_working_after_evolution(self):
        """進化しても、ついているプラスパワーの効果は続く（p.310。v0.4a の E8'。SUPPORTED）。キャタピー → トランセルの「しびれごな」20 + 10。"""
        state = build_test_state([
            {"active": {"card": CATERPIE, "energy": [GRASS, GRASS], "trainers": [(PLUSPOWER, TURN)]}, "hand": [METAPOD]},
            {"active": {"card": PONYTA}},  # HP 40。弱点は水（草ではない）
        ], turn_number=TURN)
        state = apply_command(state, EvolvePokemon(0, uids(state, 0, "hand", METAPOD)[0], state.players[0].active.pokemon_id))
        attacked = apply_command(with_coin_results(state, T), UseAttack(0, 1))
        damage = next(e for e in attacked.log if e["kind"] == "damage")
        self.assertEqual((damage["amount"], damage["modifiers"]), (30, ((5, state.players[0].active.trainers[0].card, 10),)))
        # 番の終わりに、進化したポケモンからプラスパワーをトラッシュする（p.257）
        self.assertEqual(attacked.players[0].active.trainers, [])
        self.assertIn(state.players[0].active.trainers[0].card, attacked.players[0].discard)


class ExitPathCombinationTest(unittest.TestCase):
    """バトル場からはなれる経路（にげる・ポケモンいれかえ・ふきとばし・きぜつ）× 特殊状態 × 持続する効果 × ついているトレーナー ×
    段階。ベンチに戻ったら特殊状態と持続する効果が別々に消え（p.311・p.322）、ついているカード・ダメージ・重なり・番号は
    いっしょに移る（p.311）。きぜつしたら、重なったカード・ついていたカードをすべてトラッシュし、サイドは 1 枚（p.323）。"""

    STAGES = (("たね", CATERPIE, ()), ("1 進化", METAPOD, (CATERPIE,)), ("2 進化", BUTTERFREE, (CATERPIE, METAPOD)))

    def own_board(self, card, below, conditions, attachments, prevent, hand=()):
        extra = dict(conditions)
        extra["energy"] = [GRASS, GRASS]
        if attachments:
            extra["trainers"] = [(card_id, turn - TURN + LATER_TURN) for card_id, turn in attachments]
        if prevent:
            extra["prevent_damage"] = LATER_TURN  # 盤面を直接作った（自分の番に自分が受けている持続する効果）
        return build_test_state([
            {"active": spec(card, below, **extra), "bench": [{"card": RATTATA}, {"card": PONYTA}], "hand": list(hand)},
            {"active": RATTATA},
        ], turn_number=LATER_TURN)

    def assert_moved_to_bench(self, before, after, reason, had_conditions, prevent):
        old = before.players[0].active
        moved = after.find_pokemon(old.pokemon_id)[1]
        self.assertIn(moved, after.players[0].bench)
        self.assertEqual({**snapshot(moved), "energy": None}, {**snapshot(old), "energy": None})
        self.assertEqual((moved.card, moved.evolution_stack, moved.evolved_turn), (old.card, old.evolution_stack, old.evolved_turn))
        self.assertEqual((moved.conditions.names(), moved.persistent_effects, moved.retreat_failed_turn), ((), (), None))
        events = new_events(before, after)
        removed = [e for e in events if e["kind"] in ("special_conditions_removed", "persistent_effect_removed") and e["pokemon_id"] == old.pokemon_id]
        self.assertEqual([e["kind"] for e in removed],
                         (["special_conditions_removed"] if had_conditions else []) + (["persistent_effect_removed"] if prevent else []))
        self.assertTrue(all(e["reason"] == reason for e in removed))
        self.assertEqual(check_invariants(after), [])

    def test_retreat(self):
        """にげる: ねむり・マヒはエネルギーをトラッシュする前に拒否（p.311）。こんらんはコイン（「うら」なら失敗して記録が付く）。"""
        for stage, card, below in self.STAGES:
            for cond_name, conditions in condition_states(LATER_TURN):
                for attach_name, attachments in ATTACHMENTS[:3]:
                    for prevent in (False, True):
                        with self.subTest(stage=stage, conditions=cond_name, attachments=attach_name, prevent=prevent):
                            state = self.own_board(card, below, conditions.items(), attachments, prevent)
                            active = state.players[0].active
                            cost = state.card_def(active.card).retreat_cost
                            command = Retreat(0, tuple(active.energy[:cost]), state.players[0].bench[0].card)
                            if active.conditions.asleep or active.conditions.paralyzed:
                                before, fingerprint = full(state), rng_fingerprint(state.rng)
                                with self.assertRaises(IllegalActionError) as ctx:
                                    apply_command(state, command)
                                self.assertIn(ctx.exception.code, ("POKEMON_ASLEEP", "POKEMON_PARALYZED"))
                                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
                                continue
                            if active.conditions.confused:
                                failed = apply_command(with_coin_results(state, T), command)
                                stayed = failed.players[0].active
                                self.assertEqual(stayed.pokemon_id, active.pokemon_id)
                                self.assertEqual(stayed.retreat_failed_turn, LATER_TURN)
                                self.assertEqual((stayed.conditions, stayed.persistent_effects, stayed.trainers),
                                                 (active.conditions, active.persistent_effects, active.trainers))
                                self.assertEqual(len(stayed.energy), len(active.energy) - cost)
                                self.assertEqual(check_invariants(failed), [])
                                state = with_coin_results(state, H)
                            after = apply_command(state, command)
                            self.assert_moved_to_bench(state, after, "retreat", bool(active.conditions.names()), prevent)

    def test_switch_trainer(self):
        """ポケモンいれかえ: ねむり・マヒでも入れ替える（p.325）。乱数は使わない。"""
        for stage, card, below in self.STAGES:
            for cond_name, conditions in condition_states(LATER_TURN):
                for attach_name, attachments in ATTACHMENTS[:3]:
                    for prevent in (False, True):
                        with self.subTest(stage=stage, conditions=cond_name, attachments=attach_name, prevent=prevent):
                            state = self.own_board(card, below, conditions.items(), attachments, prevent, hand=[SWITCH])
                            fingerprint = rng_fingerprint(state.rng)
                            waiting = apply_command(state, PlayTrainer(0, uids(state, 0, "hand", SWITCH)[0]))
                            d = waiting.decision
                            after = apply_command(waiting, ResolveDecision(0, d.id, (d.options[1],)))
                            self.assert_moved_to_bench(state, after, "switch", bool(state.players[0].active.conditions.names()), prevent)
                            self.assertEqual(after.players[0].active.pokemon_id, d.options[1])
                            self.assertEqual(rng_fingerprint(after.rng), fingerprint)


# 相手の番のあとの自分の番（7 番）に、相手の対戦ポケモンが受けていられるもの。特殊状態は自分の前の番（5 番）のワザ・ポケモン
# チェックのあと。マヒは 6 番（相手の番）に受けたことにした（自然な対戦では、5 番に受けたマヒは 6 番の終わりに回復する。作成可能）。
# 持続する効果は相手が 6 番に「かたまる」で受けた（自然）。ディフェンダーは相手が 6 番に使った（7 番の終わりにトラッシュ。自然）
OPPONENT_ATTACHMENTS = (("なし", ()), ("ディフェンダー", ((DEFENDER, LATER_TURN),)))


class ForcedSwitchCombinationTest(unittest.TestCase):
    """バタフリーの「ふきとばし」（p.19・p.213）× 相手の対戦ポケモンの段階 × 特殊状態 8 通り × 持続する効果 × ディフェンダー ×
    控えの数。入れ替えは「にげる」ではない（p.325）。ベンチにもどったポケモンの特殊状態と持続する効果は別々に消え（理由
    ``forced_switch``）、ついているカード（有効期限も）・ダメージ・エネルギー・重なり・番号は変わらない。ディフェンダーは番の
    終わりに、ベンチでもトラッシュする。持続する効果は二度消えない（期限のログはない）。ふきとばしは乱数を使わない。"""

    STAGES = (("たね", SEEL, ()), ("1 進化", METAPOD, (CATERPIE,)), ("2 進化", BUTTERFREE, (CATERPIE, METAPOD)))

    def board(self, card, below, conditions, attachments, prevent, bench, damage=20):
        extra = dict(conditions)
        if attachments:
            extra["trainers"] = list(attachments)
        if prevent:
            extra["prevent_damage"] = LATER_TURN - 1
        target = {**spec(card, below, **extra), "damage": damage}
        return build_test_state([
            {"active": {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}, "bench": [RATTATA]},
            {"active": target, "bench": [{"card": PONYTA}, {"card": RATTATA}][:bench]},
        ], turn_number=LATER_TURN)

    def test_matrix(self):
        for stage, card, below in self.STAGES:
            for cond_name, conditions in condition_states(LATER_TURN):
                for attach_name, attachments in OPPONENT_ATTACHMENTS:
                    for prevent in (False, True):
                        for bench in (0, 1, 2):
                            with self.subTest(stage=stage, conditions=cond_name, attachments=attach_name, prevent=prevent, bench=bench):
                                self.check_case(card, below, conditions.items(), attachments, prevent, bench)

    def check_case(self, card, below, conditions, attachments, prevent, bench):
        state = self.board(card, below, conditions, attachments, prevent, bench)
        self.assertEqual(check_invariants(state), [])
        old = state.players[1].active
        fingerprint = rng_fingerprint(state.rng)
        attacked = apply_command(state, UseAttack(0, 0))
        events = new_events(state, attacked)
        if prevent:
            self.assertIn("damage_prevented", [e["kind"] for e in events])
            self.assertNotIn("damage", [e["kind"] for e in events])
        else:
            damage = next(e for e in events if e["kind"] == "damage")
            self.assertEqual(damage["amount"], 0 if attachments else 20)  # ディフェンダーで 20 - 20 = 0（p.321 の 7 段階）
        if bench == 0:
            # 控えがいないので入れ替えない（最新の説明）。特殊状態・持続する効果は残り、番の終わりに期限で消える
            skipped = next(e for e in events if e["kind"] == "forced_switch_skipped")
            self.assertEqual(skipped["reason"], "no_bench")
            self.assertIsNot(attacked.phase, Phase.DECISION)
            self.assertEqual(check_invariants(attacked), [])
            expired = [e for e in events if e["kind"] == "persistent_effect_removed"]
            self.assertEqual([e["reason"] for e in expired], ["expired"] if prevent else [])
            return
        d = attacked.decision
        self.assertEqual((attacked.phase, d.kind, d.player, attacked.current_player), (Phase.DECISION, FORCED_SWITCH, 1, 0))
        self.assertEqual(d.options, tuple(p.pokemon_id for p in state.players[1].bench))
        self.assertEqual(check_invariants(attacked), [])
        choice = d.options[-1]
        after = apply_command(attacked, ResolveDecision(1, d.id, (choice,)))
        moved = after.find_pokemon(old.pokemon_id)[1]
        self.assertIn(moved, after.players[1].bench)
        self.assertEqual(after.players[1].active.pokemon_id, choice)
        self.assertEqual((moved.card, moved.evolution_stack, moved.energy, moved.played_turn, moved.evolved_turn),
                         (old.card, old.evolution_stack, old.energy, old.played_turn, old.evolved_turn))
        self.assertEqual(moved.damage, old.damage + (0 if prevent or attachments else 20))
        self.assertEqual((moved.conditions.names(), moved.persistent_effects), ((), ()))
        resolved = new_events(attacked, after)
        kinds = [e["kind"] for e in resolved]
        self.assertEqual(kinds.count("forced_switch"), 1)
        removed = [e for e in resolved if e["kind"] in ("special_conditions_removed", "persistent_effect_removed")]
        self.assertEqual([e["kind"] for e in removed],
                         (["special_conditions_removed"] if old.conditions.names() else []) + (["persistent_effect_removed"] if prevent else []))
        self.assertTrue(all(e["reason"] == "forced_switch" for e in removed))
        # 番の終わり: ベンチにもどったポケモンのディフェンダーもトラッシュ（有効期限は 5 番の終わり）。持続する効果は二度消えない。
        # ポケモンチェック: ベンチのポケモンはどくのダメージを受けず、新しい対戦ポケモンには特殊状態がない（コインも投げない）
        self.assertEqual(kinds.count("persistent_effect_removed"), 1 if prevent else 0)
        self.assertEqual([e["kind"] for e in resolved if e["kind"] == "discard_attached_trainer"], ["discard_attached_trainer"] * len(attachments))
        self.assertEqual(moved.trainers, [])
        self.assertNotIn("poison_damage", kinds)
        self.assertNotIn("coin_flip", kinds)
        self.assertEqual((after.phase, after.current_player, after.turn_number), (Phase.MAIN, 1, LATER_TURN + 1))
        self.assertEqual(rng_fingerprint(after.rng), fingerprint)
        self.assertEqual(check_invariants(after), [])

    def test_knock_out_skips_the_switch(self):
        """ふきとばしの 20 で相手の対戦ポケモンがきぜつしたら入れ替えない（p.309・p.213。SUPPORTED）。重なったカード・ついていた
        カード・エネルギーはすべてトラッシュ（p.323）、サイドは 1 枚、相手は控えから出す（p.313）。特殊状態は場を離れたので消える
        （ログ special_conditions_removed はない）。"""
        for stage, card, below in self.STAGES:
            probe = build_test_state([{"active": spec(card, below)}, {"active": RATTATA}], turn_number=LATER_TURN)
            hp = probe.card_def(probe.players[0].active.card).hp
            for cond_name, conditions in condition_states(LATER_TURN):
                with self.subTest(stage=stage, conditions=cond_name):
                    state = self.board(card, below, conditions.items(), (), False, 2, damage=hp - 20)
                    old = state.players[1].active
                    cards = (*old.evolution_stack, old.card, *old.energy)
                    attacked = apply_command(state, UseAttack(0, 0))
                    kinds = [e["kind"] for e in new_events(state, attacked)]
                    self.assertEqual(kinds.count("forced_switch_skipped"), 1)
                    self.assertNotIn("special_conditions_removed", kinds)
                    ko = next(e for e in attacked.log if e["kind"] == "knock_out")
                    self.assertEqual(ko.get("evolution_stack", ()), old.evolution_stack)
                    self.assertTrue(all(uid in attacked.players[1].discard for uid in cards))
                    self.assertEqual((attacked.decision.kind, attacked.decision.player), ("take_prize", 0))
                    after = apply_command(attacked, TakePrize(0, 0))
                    self.assertEqual((after.decision.kind, after.decision.player), ("promote_active", 1))
                    self.assertEqual(len(after.players[0].prizes), 5)
                    self.assertEqual(check_invariants(after), [])


class PoisonKnockOutWithPersistentEffectTest(unittest.TestCase):
    """「かたまる」の効果を受けた番の終わりのポケモンチェックで、どくできぜつする（自然な対戦で起こる）。効果は期限ではなく
    きぜつで消え（理由 knock_out。p.322）、二度は消えない。サイドは相手が取る（p.323）。"""

    def test_harden_then_poison_knock_out(self):
        for card, below in ((KAKUNA, (WEEDLE,)), (METAPOD, (CATERPIE,))):
            with self.subTest(card=card):
                hp = 80 if card == KAKUNA else 70
                state = build_test_state([
                    {"active": {**spec(card, below, poison=10), "damage": hp - 10, "energy": [GRASS, GRASS]}, "bench": [RATTATA]},
                    {"active": RATTATA},
                ], turn_number=TURN)
                after = apply_command(with_coin_results(state, H), UseAttack(0, 0))
                kinds = [e["kind"] for e in new_events(state, after)]
                self.assertEqual(kinds[:4], ["attack", "coin_flip", "persistent_effect_added", "turn_end"])
                removed = [e for e in after.log if e["kind"] == "persistent_effect_removed"]
                self.assertEqual([e["reason"] for e in removed], ["knock_out"])
                ko = next(e for e in after.log if e["kind"] == "knock_out")
                self.assertEqual((ko["timing"], ko["evolution_stack"]), ("pokemon_check", state.players[0].active.evolution_stack))
                self.assertEqual((after.decision.kind, after.decision.player, after.decision.context_value("then")),
                                 ("take_prize", 1, "next_turn"))
                self.assertEqual(check_invariants(after), [])


if __name__ == "__main__":
    unittest.main()

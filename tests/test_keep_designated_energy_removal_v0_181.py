"""v0.181（E12 の修正）: 回答で指定したうらのカード（マチスの秘策）をおもてにしたら［KEEP］がはたらき出す場面の、エネルギー・リムーブ・超エネルギーリムーブ。

調査: docs/verification-ai-e12-energy-removal-keep-investigation.md。修正: docs/keep-designated-energy-removal-v0.181.md。

- v0.180 まで: 相手のうらについたエネルギーを選ぶと、指定でおもてにしたカードが［KEEP］（``VoidOpponentEnergyDiscardOnGroup``）を持つたねなら、確かめ直さずにトラッシュし
  ``require_discard_not_voided`` の ``RuntimeError``（内部の例外）になった。本当のカードがほかでも、受け付けるかの確かめ（``engine._identity_independent``）が［KEEP］のたねを試すので
  同じ例外になった。
- v0.181: おもてにしたあと、トラッシュする前（超エネルギーリムーブは段階 3 の決定を出す前）に既存の ``energy_discard_void`` で確かめ、当たれば既存の KP1
  （``UNRESOLVED_KEEP_PROTECTED_TARGET``。docs/counter-keep-energy-protection-v0.101.md 4.3・8 章）と同じ通常の拒否。効果なしで受理する新しい裁定は入れない。

盤面は ``tests/test_secret_plan_v0_67.py`` の部品で作る構築盤面（new_game からの到達ではない）。入口は ``apply_command`` と ``ClientHub``（既存の置きかえの確かめを通る）。
"""

from __future__ import annotations

import json
import unittest

from kyuura_engine import AttachEnergy, PlayTrainer, ResolveDecision
from kyuura_engine import zones as _zones
from kyuura_engine.cards import load_card_pool
from kyuura_engine.client_api import ClientHub
from kyuura_engine.effects import KEEP_TARGET_CODE, KEEP_TARGET_REASON
from kyuura_engine.engine import apply_command, check_invariants
from kyuura_engine.errors import HiddenPropertyRead, UnsupportedError
from kyuura_engine.observation import observe, visible_log
from kyuura_engine.zones import SECRET_PLAN_LOST_TARGET_CODE
from kyuura_engine.effects import STATED_CARDS_SHORT_CODE
from tests.helpers import (DEFENDER, DIGLETT, ENERGY_REMOVAL, FIGHTING, FIRE, HITMONCHAN, KADABRA, LT_SURGES_SECRET_PLAN, SUPER_ENERGY_REMOVAL,
                           SWITCH)
from tests.test_secret_plan_v0_67 import board, face_down, full, opponent_turn, place, uid_of

UNOWN_K = "neo3-030"  # アンノーンK（［KEEP］。たね）
SECRETS = (DIGLETT, FIRE, UNOWN_K)  # うらの本当のカード: たね・たねでない・［KEEP］を持つたね
REQ = {"contract": "kyuura-client-api", "format": 1}


def public(state):
    """答えたプレイヤーの相手・観戦者の観測とログ。"""
    return {str(v): (observe(state, v), visible_log(state, v)) for v in (1, None)}


def opponent_face_down(card_id, trainer=ENERGY_REMOVAL, energies=1, active_energies=1):
    """プレイヤー 1 が ``card_id`` をうらでベンチに出し、自分の番ごとに闘エネルギーを 1 枚ずつ ``energies`` 枚つけて、プレイヤー 0 の番にした状態。相手のバトル場（おもて）には
    闘エネルギー ``active_energies`` 枚。(状態, うら, エネルギーの uid)。"""
    state = board(hand=(trainer,), opponent={"card": HITMONCHAN, "energy": [FIGHTING] * active_energies},
                  opponent_hand=(LT_SURGES_SECRET_PLAN, card_id, *(FIGHTING,) * energies))
    state = place(opponent_turn(state), card_id, player=1)
    fd = face_down(state, 1)[0]
    attached = []
    for n in range(energies):
        energy = uid_of(state, FIGHTING, 1)
        state = apply_command(state, AttachEnergy(1, energy, fd.card))
        attached.append(energy)
        state = opponent_turn(state)
        if n + 1 < energies:
            state = opponent_turn(state)
    assert state.current_player == 0 and state.is_face_down(state.players[1].find_by_pokemon_id(fd.pokemon_id))
    return state, fd, attached


def face_up_bench(card_id, trainer=ENERGY_REMOVAL, energies=1):
    """プレイヤー 1 のベンチに ``card_id`` がおもてで、闘エネルギー ``energies`` 枚つき。(状態, ベンチのポケモン)。"""
    state = board(hand=(trainer,), opponent_bench=({"card": card_id, "energy": [FIGHTING] * energies},))
    return state, state.players[1].bench[0]


def play(state, trainer):
    state = apply_command(state, PlayTrainer(0, uid_of(state, trainer)))
    assert state.decision is not None
    return state


def no_secret(case, error_text, card_id):
    definition = load_card_pool().get(card_id)
    case.assertNotIn(card_id, error_text)
    case.assertNotIn(definition.name_ja, error_text)


class Safe:
    def rejected(self, state, command, code):
        """拒否の前後で、状態（ログ・決定・番・場）・乱数・相手と観戦者への公開・決定・一時状態が変わらない。"""
        before, seen, decision = full(state), public(state), state.decision
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, command)
        self.assertEqual(ctx.exception.code, code)
        self.assertEqual(full(state), before)
        self.assertEqual(public(state), seen)
        self.assertIs(state.decision, decision)
        self.assertEqual(check_invariants(state), [])
        self.assertIsNone(_zones.IDENTITY_CONSULTED)
        self.assertIsNone(_zones.IDENTITY_ORACLE)
        return ctx.exception


class EnergyRemovalDesignatedKeepTest(Safe, unittest.TestCase):
    def test_opponent_face_down_energy_is_kp1_for_every_identity(self):
        """相手のうらについたエネルギーを選ぶと、本当のカードがたね・たねでない・［KEEP］のたねのどれでも、内部の例外ではなく同じコード・同じ文の KP1（通常の拒否）。
        LOST_TARGET ではない（置きかえの確かめが試す順で、最初に拒否するのは［KEEP］のたね）。"""
        results = []
        for card_id in SECRETS:
            with self.subTest(card=card_id):
                state, fd, (energy,) = opponent_face_down(card_id)
                state = play(state, ENERGY_REMOVAL)
                self.assertIn(energy, state.decision.options)
                self.assertNotIn(energy, state.decision.context_value("unresolved_choices", ()))  # うらのあいだは KP1 の選択に入らない（決定の形は変えない）
                error = self.rejected(state, ResolveDecision(0, state.decision.id, (energy,)), KEEP_TARGET_CODE)
                self.assertNotEqual(error.code, SECRET_PLAN_LOST_TARGET_CODE)
                no_secret(self, json.dumps([error.code, error.message], ensure_ascii=False), card_id)
                results.append((type(error), error.code, error.message))
        self.assertEqual(len(set(results)), 1)

    def test_keep_identity_without_identity_trial_is_the_same_rejection(self):
        """本当のカードが［KEEP］のたねなら、本物の 1 回目の処理でも（v0.180 は置きかえを通らずに内部の例外）KP1 で止まり、続けて別のエネルギーを選べば受理する。"""
        state, fd, (energy,) = opponent_face_down(UNOWN_K)
        state = play(state, ENERGY_REMOVAL)
        self.rejected(state, ResolveDecision(0, state.decision.id, (energy,)), KEEP_TARGET_CODE)
        other = state.players[1].active.energy[0]
        after = apply_command(state, ResolveDecision(0, state.decision.id, (other,)))
        self.assertIsNone(after.decision)
        self.assertNotIn(other, after.players[1].active.energy)
        self.assertIn(other, after.players[1].discard)
        self.assertTrue(after.is_face_down(after.players[1].find_by_pokemon_id(fd.pokemon_id)))  # 選ばなかったうらはうらのまま
        self.assertEqual(check_invariants(after), [])

    def test_face_up_controls_are_unchanged(self):
        """おもての［KEEP］は今までどおり決定の時点の KP1（選ぶと止める選択）。［KEEP］のないおもては受理してトラッシュ。"""
        state, keep = face_up_bench(UNOWN_K)
        state = play(state, ENERGY_REMOVAL)
        self.assertEqual(tuple(state.decision.context_value("unresolved_choices", ())), tuple(keep.energy))
        error = self.rejected(state, ResolveDecision(0, state.decision.id, (keep.energy[0],)), KEEP_TARGET_CODE)
        self.assertEqual(error.message, KEEP_TARGET_REASON)
        state, plain = face_up_bench(DIGLETT)
        state = play(state, ENERGY_REMOVAL)
        energy = plain.energy[0]
        after = apply_command(state, ResolveDecision(0, state.decision.id, (energy,)))
        self.assertIn("trainer_discard_energy", [e["kind"] for e in after.log[len(state.log):]])
        self.assertIn(energy, after.players[1].discard)

    def test_fd1_when_keep_is_face_up_and_energy_on_face_down_is_unchanged(self):
        """おもての［KEEP］があり、別の相手のうらにエネルギーがあるときは、今までどおり使う時点で FD1（決定を出さない）。"""
        state = board(hand=(ENERGY_REMOVAL,), opponent_bench=({"card": UNOWN_K, "energy": [FIGHTING]},),
                      opponent_hand=(LT_SURGES_SECRET_PLAN, DIGLETT, FIGHTING))
        state = place(opponent_turn(state), DIGLETT, player=1)
        fd = face_down(state, 1)[0]
        state = opponent_turn(apply_command(state, AttachEnergy(1, uid_of(state, FIGHTING, 1), fd.card)))
        before = full(state)
        with self.assertRaises(HiddenPropertyRead):
            apply_command(state, PlayTrainer(0, uid_of(state, ENERGY_REMOVAL)))
        self.assertEqual(full(state), before)


class SuperEnergyRemovalDesignatedKeepTest(Safe, unittest.TestCase):
    def stage2(self, card_id):
        # 相手のバトル場（おもて）にもエネルギー 2 枚（使う前の答えの続きの確かめ ``engine._trainer_dead_end`` が、本当のカードによらず続きを見つける）
        state, fd, energies = opponent_face_down(card_id, SUPER_ENERGY_REMOVAL, energies=2, active_energies=2)
        state = play(state, SUPER_ENERGY_REMOVAL)
        self.assertEqual(state.decision.context_value("stage"), 1)  # 自分のエネルギー（使うための条件）
        own = state.players[0].active.energy[0]
        state = apply_command(state, ResolveDecision(0, state.decision.id, (own,)))
        self.assertEqual((state.decision.context_value("stage"), state.decision.kind), (2, "select_pokemon"))
        self.assertIn(own, state.players[0].discard)
        return state, fd, energies

    def test_stage2_opponent_face_down_is_kp1_for_every_identity(self):
        """段階 2 で相手のうら（エネルギー 2 枚）を選ぶと、どの本当のカードでも同じ KP1（段階 3 の決定を出さない・内部の例外にならない）。"""
        results = []
        for card_id in SECRETS:
            with self.subTest(card=card_id):
                state, fd, _ = self.stage2(card_id)
                self.assertNotIn(fd.pokemon_id, state.decision.context_value("unresolved_choices", ()))
                error = self.rejected(state, ResolveDecision(0, state.decision.id, (fd.pokemon_id,)), KEEP_TARGET_CODE)
                no_secret(self, json.dumps([error.code, error.message], ensure_ascii=False), card_id)
                results.append((type(error), error.code, error.message))
        self.assertEqual(len(set(results)), 1)

    def test_face_down_as_the_only_target_is_rejected_at_play_for_every_identity(self):
        """エネルギー 2 枚のポケモンが相手のうらだけなら、使う時点の答えの続きの確かめ（v0.49 の ``_trainer_dead_end``）で、どの本当のカードでも同じ拒否（FC1。最初に見つかる
        止め方はエネルギーの足りないバトル場）。v0.180 は［KEEP］のたねの試しで内部の例外だった。"""
        results = []
        for card_id in SECRETS:
            with self.subTest(card=card_id):
                state, fd, _ = opponent_face_down(card_id, SUPER_ENERGY_REMOVAL, energies=2)
                error = self.rejected(state, PlayTrainer(0, uid_of(state, SUPER_ENERGY_REMOVAL)), STATED_CARDS_SHORT_CODE)
                no_secret(self, json.dumps([error.code, error.message], ensure_ascii=False), card_id)
                results.append((type(error), error.code, error.message))
        self.assertEqual(len(set(results)), 1)

    def test_stage2_and_stage3_normal_paths(self):
        """段階 2 でおもてのポケモン（エネルギー 2 枚）を選び、段階 3 で 2 枚を選べば受理してトラッシュ（通常のトラッシュ）。おもての［KEEP］は段階 2 の KP1（今までどおり）。"""
        state, plain = face_up_bench(DIGLETT, SUPER_ENERGY_REMOVAL, energies=2)
        state = play(state, SUPER_ENERGY_REMOVAL)
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].active.energy[0],)))
        state = apply_command(state, ResolveDecision(0, state.decision.id, (plain.pokemon_id,)))
        self.assertEqual((state.decision.context_value("stage"), tuple(state.decision.options)), (3, tuple(plain.energy)))
        after = apply_command(state, ResolveDecision(0, state.decision.id, tuple(plain.energy)))
        self.assertIsNone(after.decision)
        self.assertEqual(after.players[1].bench[0].energy, [])
        self.assertEqual(check_invariants(after), [])
        # おもての［KEEP］の対照。相手のバトル場にもエネルギーを 2 枚つける（どの相手のポケモンも止める選択なら使う前に止まる。v0.101 の FC1・KP1）
        state = board(hand=(SUPER_ENERGY_REMOVAL,), opponent={"card": DIGLETT, "energy": [FIGHTING, FIGHTING]},
                      opponent_bench=({"card": UNOWN_K, "energy": [FIGHTING, FIGHTING]},))
        keep = state.players[1].bench[0]
        state = play(state, SUPER_ENERGY_REMOVAL)
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].active.energy[0],)))
        self.assertIn(keep.pokemon_id, state.decision.context_value("unresolved_choices", ()))
        self.rejected(state, ResolveDecision(0, state.decision.id, (keep.pokemon_id,)), KEEP_TARGET_CODE)


class LostTargetRelationTest(Safe, unittest.TestCase):
    def test_own_face_down_lost_target_and_switch_are_unchanged(self):
        """本人のうら（本人が持ち主。置きかえの確かめに入らない）: ディフェンダーでたねでないうらは LOST_TARGET、入れ替え（対象を失ったら終える）はトラッシュして受理。"""
        state = place(board(hand=(KADABRA, DEFENDER)), KADABRA)
        fd = face_down(state)[0]
        state = play(state, DEFENDER)
        self.rejected(state, ResolveDecision(0, state.decision.id, (fd.pokemon_id,)), SECRET_PLAN_LOST_TARGET_CODE)
        state = place(board(hand=(FIRE, SWITCH)), FIRE)
        fd = face_down(state)[0]
        state = play(state, SWITCH)
        after = apply_command(state, ResolveDecision(0, state.decision.id, (fd.pokemon_id,)))
        self.assertIn("secret_plan_target_lost", [e["kind"] for e in after.log[len(state.log):]])


def _plain(value):
    """取っ手（game・revision・operation_id）を除いた応答（双子の比べ）。"""
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items() if k not in ("game", "revision", "operation_id")}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


class ClientApiTwinTest(unittest.TestCase):
    def exchange(self, card_id):
        state, fd, (energy,) = opponent_face_down(card_id)
        state = play(state, ENERGY_REMOVAL)
        index = state.decision.options.index(energy)
        hub = ClientHub.from_state(state)
        me, spectator = hub.player(0), hub.spectator()
        views = (me.handle({**REQ, "type": "view"}), spectator.handle({**REQ, "type": "view"}))
        r = me.handle({**REQ, "type": "candidates"})["response"]
        c = next(x for x in r["candidates"] if x["kind"] == "answer_decision")
        h = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        option = f"o{index + 1}"
        inputs = me.handle({**REQ, "type": "inputs", **h})
        check = me.handle({**REQ, "type": "check", **h, "choices": [option]})
        submit = me.handle({**REQ, "type": "submit", **h, "choices": [option]})
        updates = [hub.take_updates(a) for a in (0, 1, "spectator")]
        # 拒否のあとも同じ決定で続けられる（別のエネルギーを選ぶ）
        r2 = me.handle({**REQ, "type": "candidates"})["response"]
        c2 = next(x for x in r2["candidates"] if x["kind"] == "answer_decision")
        other = f"o{state.decision.options.index(state.players[1].active.energy[0]) + 1}"
        again = me.handle({**REQ, "type": "submit", "game": r2["game"], "revision": r2["revision"], "candidate": c2["id"], "choices": [other]})
        after = [len(hub.take_updates(a)) for a in (0, 1, "spectator")]
        return {"views": views, "candidates": r, "inputs": inputs, "check": check, "submit": submit, "updates": updates, "again": again, "after": after}

    def test_twins_get_the_same_responses_and_can_continue(self):
        """秘密だけが違う双子（たね・たねでない・［KEEP］のたね）で、本人と観戦者の観測が同じことを確かめてから、候補・inputs・check・submit・診断を比べる。候補と check は
        成功し、submit は rejected（failed・INTERNAL_ERROR ではない）。拒否で相手・観戦者・本人への更新はなく、同じ決定に別の答えを出せば受理する。"""
        seen = {card_id: self.exchange(card_id) for card_id in SECRETS}
        first = seen[SECRETS[0]]
        for card_id, got in seen.items():
            with self.subTest(card=card_id):
                self.assertEqual(_plain(got["views"]), _plain(first["views"]))
                for key in ("candidates", "inputs", "check", "submit", "updates", "after"):
                    self.assertEqual(_plain(got[key]), _plain(first[key]), key)
                no_secret(self, json.dumps(got["submit"], ensure_ascii=False), card_id)
        submit = first["submit"]
        self.assertTrue(first["check"]["response"]["valid"])
        self.assertEqual(submit["outcome"], "rejected")
        self.assertNotEqual(submit["outcome"], "failed")
        self.assertEqual(submit["result"]["diagnostic_id"] if submit["result"] else None, KEEP_TARGET_CODE)
        self.assertNotIn("INTERNAL_ERROR", json.dumps(submit))
        self.assertEqual(first["updates"], [[], [], []])
        self.assertEqual(first["again"]["outcome"], "accepted")
        self.assertEqual(first["after"], [1, 1, 1])


if __name__ == "__main__":
    unittest.main()

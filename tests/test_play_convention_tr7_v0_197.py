"""v0.197（docs/play-convention-tr7-v0.197.md）: 「とうめい」で受けないと決まったあとの特殊状態のワザのコインのプレイ用の続行規約 PC-T19B-NULLIFIED-STATUS-COIN@1
（開発用の集合 CS-KYUURA-PLAY-TR7@1）。

利用者の採用（2026-11-22。設計 docs/t19b-evaded-effect-coin-design.md の案 B）: 相手の対戦ポケモンが、ワザのダメージの要素で「とうめい」の「おもて」になって、そのワザのダメージと効果を
受けないと決まったとき、特殊状態にするかだけを決めるワザのコインを、ワザを使った側が 1 回投げ、結果を使わずにワザの続きへ進む。効果の登録の型 ConfuseOnHeads・PoisonOnHeads・
ParalyzeOnHeads の元のワザの、特殊状態の要素（Status）の経路だけ。明示的に選んだ TR7 の集合だけで有効。プレイ用の取り決めで、史実の裁定の確定ではない（T19b の停止コードは
厳密側・既存の集合・対象の外の経路で active のまま）。

確かめの種類を分ける（設計 7 章の S1〜S9）:

- 構築盤面（tests.helpers.build_test_state。規約集合だけを置きかえた写し ``with_set``。コインは with_coin_bits の台本）: 登録・厳密側の拒否と巻き戻し（「うら」の台本でも先読みが
  「おもて」の枝で止める）・TR7 の「おもて」の両方のワザのコイン・「うら」で HP 以上（ワザのコインなし）・HP 未満（今と同じ）・無効化の起きない対照・ほかの 2 つの型・対象の外の経路・
  合法手 API・ログの監査
- 本物の runner（スナップショットから復元した構築盤面）と逐次バッチの判定の入口（``batch.judge_trace``）: TR7 の受理は expected。厳密側の拒否の判定は今のまま（記録するだけ）
- new_game: TR7 を明示して対戦を作れること・既定の集合が変わらないこと（通常の対戦での到達は確かめていない）
"""

from __future__ import annotations

import copy
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import conventions as C
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import UseAttack
from kyuura_engine.engine import apply_command, check_invariants, new_game
from kyuura_engine.errors import UnsupportedError
from kyuura_engine.observation import visible_log
from kyuura_engine.rng import copy_rng, rng_fingerprint
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from tests import helpers as H
from tests.log_audit import s2a_problems

LATEST = max(FORMAT_VERSIONS)
TR7 = ("CS-KYUURA-PLAY-TR7", 1)
TR6 = ("CS-KYUURA-PLAY-TR6", 1)
TR4 = ("CS-KYUURA-PLAY-TR4", 1)
COIN_ID = "PC-T19B-NULLIFIED-STATUS-COIN"
T19B = "UNRESOLVED_EVADED_EFFECT_COIN"
STRICT_SETS = (C.DEFAULT_SET, TR4, TR6)  # 厳密側（今の挙動の集合）と、この規約を持たない既存の開発用の集合
HEADS, TAILS = CoinSide.HEADS, CoinSide.TAILS
SCRIPTS = ((HEADS, HEADS), (HEADS, TAILS), (TAILS, HEADS), (TAILS, TAILS))
TURN = 7
# 既存の集合の照合値（v0.142〜v0.196 の固定の値。この版で変えない）
EXISTING_SET_DIGESTS = {
    ("CS-KYUURA-CURRENT", 1): "sha256:9a9b95c689d86fa01a5b710984560efda3c08f4dbf1d7c6218094ac8666f3cee",
    ("CS-KYUURA-LEGACY-UNRECORDED", 1): "sha256:abf39e6d87755507a9169537608596246f4ed9a9bf0c2e8794ffa44a97742407",
    ("CS-KYUURA-PLAY-S2A", 1): "sha256:b317a3f050206577bff35ac05c87fdb4224ee28c6c0222e4e7f8460b5e9410c4",
    ("CS-KYUURA-PLAY-PO", 1): "sha256:06d512194feee1857319f0c765ab2162d5259e4519895ed057d176d15fc43528",
    ("CS-KYUURA-PLAY-TR3", 1): "sha256:a7b800cff2a8614d7b181cc3a8a39f68ec4e17be9ceab0a04e75a48c4358ffb4",
    ("CS-KYUURA-PLAY-TR4", 1): "sha256:15af975a643c8d5844bf76e0a85ab20020ca331b01c463aeb344047806435552",
    ("CS-KYUURA-PLAY-TR6", 1): "sha256:aa53bc52cfc1d2193a3e1692efc585cf7daef23251c5d08dd09d7e554cf6ead2",
}
ALAKAZAM = {"card": H.ALAKAZAM, "evolved_from": [H.ABRA, "PMCG1-046"], "energy": [H.PSYCHIC] * 3}


def haunter(**extra):
    return {"card": H.HAUNTER, "evolved_from": H.GASTLY, "energy": [H.PSYCHIC], **extra}


def with_set(state, key):
    """盤面を直接作った状態（今の挙動の集合）を、同じ盤面・同じ乱数の別の集合の状態にする（constructed。規約集合だけを置きかえる）。"""
    new = state.clone()
    new.conventions = C.registered_identity(key)
    return new


def board(attacker=ALAKAZAM, defender=None, key=C.DEFAULT_SET, sides=(), bench0=(H.PONYTA,)):
    state = H.build_test_state([{"active": attacker, "bench": list(bench0)}, {"active": defender or haunter(), "bench": [H.RATTATA]}], turn_number=TURN)
    state = with_set(state, key)
    return H.with_coin_bits(state, *sides) if sides else state


def snap(state):
    """拒否で変わらないことを確かめる値: 書き出しの全体・乱数・ログ・決定の通し番号。"""
    return repr(state_to_dict(state, format_version=LATEST)), rng_fingerprint(state.rng), tuple(map(repr, state.log)), state.next_decision_id


def draws(before, after, limit=12):
    probe = copy_rng(before.rng)
    for count in range(limit + 1):
        if rng_fingerprint(probe) == rng_fingerprint(after.rng):
            return count
        probe.getrandbits(1)
    raise AssertionError("乱数の進み方が分からない")


def attack(state, index=0):
    new = apply_command(state, UseAttack(0, index))
    assert check_invariants(new) == []
    return new, [dict(e) for e in new.log[len(state.log):]]


def coins(events):
    return [(e["player"], e["source"], e["result"]) for e in events if e["kind"] == "coin_flip"]


def applied(events):
    return [e for e in events if e["kind"] == "convention_applied"]


class RegistrationTest(unittest.TestCase):
    def test_tr7_set_members_and_digests(self):
        spec = C.SETS[TR7]
        self.assertEqual((spec.usage, spec.completeness), (C.USAGE_DEVELOPMENT, C.COMPLETENESS_HALTS))  # 完成したプレイ用の集合ではない
        tr6 = C.SETS[TR6]
        self.assertEqual(len(tr6.members), 25)
        self.assertEqual(spec.members, tr6.members + ((COIN_ID, 1),))  # TR6@1 の 25 規約と、新しい 1 規約
        self.assertEqual(C.validate(spec), [])
        identity = C.identity_of(spec)
        self.assertEqual(identity.digest, C.PINNED_SET_DIGESTS[TR7])
        for member, version, digest in identity.members:
            self.assertEqual(digest, C.PINNED_CONVENTION_DIGESTS[(member, version)], member)
            self.assertEqual(digest, C.convention_digest(C.CONVENTIONS[(member, version)]), member)
        convention = C.CONVENTIONS[(COIN_ID, 1)]
        self.assertEqual((convention.layer, convention.approval, convention.scenes), (C.LAYER_CONTINUATION, C.APPROVAL_USER_AGREED, (T19B,)))
        self.assertIn("2026-11-22", convention.content["adoption"])
        self.assertIn("PC-NULLIFIED-ELEMENT-COIN", convention.content["family"])
        self.assertIn((COIN_ID, 1), C.DEFAULT_REGISTRY.implemented_continuations)
        self.assertIn(T19B, {s["id"] for s in C.scene_index()["scenes"]})
        self.assertEqual([key for key, c in C.CONVENTIONS.items() if T19B in c.scenes], [(COIN_ID, 1)])  # この場面の規約は 1 つだけ
        self.assertNotIn(("CS-KYUURA-PLAY-TR5", 1), C.SETS)  # TR5 は ER10 の設計の案で使った名前（登録しない）

    def test_existing_sets_and_default_are_unchanged(self):
        for key, digest in EXISTING_SET_DIGESTS.items():
            with self.subTest(key=key):
                self.assertEqual(C.PINNED_SET_DIGESTS[key], digest)
                self.assertEqual(C.identity_of(C.SETS[key], for_new_game=False).digest, digest)
                self.assertNotIn((COIN_ID, 1), C.SETS[key].members)
        self.assertEqual(C.DEFAULT_SET, ("CS-KYUURA-CURRENT", 1))

    def test_lookup_only_in_tr7(self):
        for key in STRICT_SETS + ((C.S2A_SET_ID, 1), (C.PO_SET_ID, 1), ("CS-KYUURA-PLAY-TR3", 1)):
            with self.subTest(key=key):
                self.assertIsNone(C.continuation_for(board(key=key), T19B))
        lookup = C.continuation_for(board(key=TR7), T19B)
        self.assertEqual((lookup.convention, lookup.scene), ((COIN_ID, 1), T19B))

    def test_new_game_only_when_selected(self):
        deck = H.expand_decklist({H.DRATINI: 4, H.LIGHTNING: 56})
        self.assertEqual(new_game(deck, deck, 1).conventions.key, C.DEFAULT_SET)
        self.assertEqual(new_game(deck, deck, 1, conventions="CS-KYUURA-PLAY-TR7@1").conventions, C.registered_identity(TR7))


class StrictTest(unittest.TestCase):
    """S1: 厳密側と既存の集合は今のまま T19b で拒否（宣言の前。状態・乱数・ログは変わらない）。「とうめい」の台本が「うら」でも、先読みが「おもて」の枝で問いに当たる。"""

    def test_strict_sets_reject_on_every_coin_script(self):
        for key in STRICT_SETS:
            for damage in (30, 0):
                for sides in SCRIPTS:
                    with self.subTest(key=key, damage=damage, sides=sides):
                        state = board(defender=haunter(damage=damage), key=key, sides=sides)
                        before = snap(state)
                        views = [visible_log(state, v) for v in (0, 1, None)]
                        with self.assertRaises(UnsupportedError) as ctx:
                            apply_command(state, UseAttack(0, 0))
                        self.assertEqual(ctx.exception.code, T19B)
                        self.assertEqual(snap(state), before)
                        self.assertEqual([visible_log(state, v) for v in (0, 1, None)], views)


class AcceptedTest(unittest.TestCase):
    """S2〜S4: TR7 の受理。「おもて」: 2 回のコイン（ゴースト側の「とうめい」→ ワザを使った側のワザのコイン）・規約の記録 1・ダメージと特殊状態なし・番が終わる。
    「うら」で HP 以上: 「とうめい」の 1 回だけ（ワザのコイン・規約の記録なし）・きぜつ。「うら」で HP 未満: 今の処理（規約の記録なし）。"""

    def test_heads_flips_the_attack_coin_once_and_ends_the_turn(self):
        for damage in (30, 0):
            for second in (HEADS, TAILS):
                with self.subTest(damage=damage, second=second):
                    state = board(defender=haunter(damage=damage), key=TR7, sides=(HEADS, second))
                    new, events = attack(state)
                    self.assertEqual(coins(events), [(1, "power", "heads"), (0, "attack", second.value)])
                    self.assertEqual(draws(state, new), 2)  # 先読みの乱数は残らない（実際のコインの 2 回だけ）
                    (record,) = applied(events)
                    self.assertEqual({k: record[k] for k in ("convention", "version", "scene", "code", "player", "target_owner", "element")},
                                     {"convention": COIN_ID, "version": 1, "scene": T19B, "code": T19B, "player": 0, "target_owner": 1, "element": "confusion"})
                    kinds = [e["kind"] for e in events]
                    i = kinds.index("convention_applied")
                    self.assertEqual(kinds[i - 3:i], ["coin_flip", "evade_check", "attack_evaded"])  # 「とうめい」のコイン・おもて・ダメージを受けない
                    self.assertEqual(kinds[i + 1], "coin_flip")
                    after = kinds[i + 2:]
                    self.assertEqual(after[:1] == ["attack_evaded"], second is HEADS)
                    self.assertNotIn("special_condition", kinds)
                    self.assertNotIn("damage", kinds)
                    target = new.players[1].active
                    self.assertEqual((target.damage, target.conditions.exclusive, target.conditions.poison), (damage, None, None))
                    self.assertEqual((new.decision, new.current_player, new.turn_number), (None, 1, TURN + 1))
                    self.assertIn("turn_end", kinds)
                    self.assertEqual(s2a_problems(new), [])

    def test_tails_knockout_has_no_attack_coin_and_no_record(self):
        for second in (HEADS, TAILS):
            state = board(defender=haunter(damage=30), key=TR7, sides=(TAILS, second))
            new, events = attack(state)
            self.assertEqual(coins(events), [(1, "power", "tails")])
            self.assertEqual(draws(state, new), 1)
            self.assertEqual(applied(events), [])
            self.assertIn("knock_out", [e["kind"] for e in events])
            self.assertEqual(new.decision.kind, "take_prize")

    def test_tails_below_hp_is_the_unchanged_coin(self):
        for second, confused in ((HEADS, True), (TAILS, False)):
            state = board(key=TR7, sides=(TAILS, second))
            new, events = attack(state)
            self.assertEqual(coins(events), [(1, "power", "tails"), (0, "attack", second.value)])
            self.assertEqual(applied(events), [])
            self.assertEqual(new.players[1].active.damage, 30)
            self.assertEqual(new.players[1].active.conditions.exclusive is not None, confused)

    def test_viewers_receive_the_same_public_records(self):
        state = board(key=TR7, sides=(HEADS, HEADS))
        n = [len(visible_log(state, v)) for v in (0, 1, None)]
        new, _ = attack(state)
        added = [[(e["kind"], e.get("player"), e.get("result"), e.get("convention")) for e in visible_log(new, v)[n[i]:]] for i, v in enumerate((0, 1, None))]
        self.assertEqual(added[0], added[1])
        self.assertEqual(added[0], added[2])
        self.assertIn(("convention_applied", 0, None, COIN_ID), added[0])
        self.assertIn(("coin_flip", 0, "heads", None), added[0])


class ControlTest(unittest.TestCase):
    """S5: 無効化が起きない・一部だけ無効の対照は、TR7 と厳密側で受理・コイン・ログ・状態が同じ（規約の記録なし）。"""

    CONTROLS = {
        "asleep": lambda key, sides: board(defender=haunter(sleep=True), key=key, sides=sides),
        "chemical_gas": lambda key, sides: board(key=key, sides=sides, bench0=({"card": H.MUK, "evolved_from": H.GRIMER},)),
        "final_zero": lambda key, sides: board({"card": H.VULPIX, "energy": [H.FIRE, H.FIRE]}, haunter(trainers=[(H.DEFENDER, TURN)]), key=key, sides=sides),
        "not_haunter": lambda key, sides: board(defender={"card": H.GROWLITHE, "energy": [H.FIRE]}, key=key, sides=sides),
        "prevent_damage": lambda key, sides: board(defender={"card": H.GROWLITHE, "energy": [H.FIRE], "prevent_damage": TURN - 1}, key=key, sides=sides),
    }

    def test_controls_are_the_same_in_tr7_and_strict(self):
        for name, make in self.CONTROLS.items():
            for sides in SCRIPTS:
                with self.subTest(name=name, sides=sides):
                    strict, s_events = attack(make(C.DEFAULT_SET, sides))
                    tr7, t_events = attack(make(TR7, sides))
                    self.assertEqual(applied(t_events), [])
                    self.assertEqual(t_events, s_events)
                    self.assertEqual(rng_fingerprint(strict.rng), rng_fingerprint(tr7.rng))


class OtherTypesTest(unittest.TestCase):
    """S6: PoisonOnHeads（ビードルの［どくばり］）・ParalyzeOnHeads（ゴースの［したでなめる］）も、同じ無効化の条件・同じ続き（要素の並びの最後）で受理する。"""

    def test_poison_and_paralysis_heads(self):
        for attacker, element in (({"card": H.WEEDLE, "energy": [H.GRASS]}, "poison"), ({"card": H.GASTLY, "energy": [H.PSYCHIC]}, "paralysis")):
            for second in (HEADS, TAILS):
                with self.subTest(element=element, second=second):
                    for key in STRICT_SETS:
                        with self.assertRaises(UnsupportedError) as ctx:
                            apply_command(board(attacker, key=key, sides=(HEADS, second)), UseAttack(0, 0))
                        self.assertEqual(ctx.exception.code, T19B)
                    state = board(attacker, key=TR7, sides=(HEADS, second))
                    new, events = attack(state)
                    self.assertEqual(coins(events), [(1, "power", "heads"), (0, "attack", second.value)])
                    self.assertEqual([e["element"] for e in applied(events)], [element])
                    target = new.players[1].active
                    self.assertEqual((target.damage, target.conditions.exclusive, target.conditions.poison), (0, None, None))
                    self.assertEqual((new.current_player, new.turn_number), (1, TURN + 1))
                    self.assertEqual(s2a_problems(new), [])


class OutOfScopeTest(unittest.TestCase):
    """S7: 対象の外の経路は TR7 でも T19b のまま（状態は変わらない）。"""

    def test_other_t19b_sites_keep_stopping(self):
        for name, attacker, index in (("poison_or_confuse", {"card": H.KOFFING, "energy": [H.GRASS, H.GRASS]}, 0),
                                      ("discard_energy_on_heads", {"card": "ES3-026", "energy": [H.PSYCHIC] * 3}, 1)):
            for sides in SCRIPTS:
                with self.subTest(name=name, sides=sides):
                    state = board(attacker, key=TR7, sides=sides)
                    before = snap(state)
                    with self.assertRaises(UnsupportedError) as ctx:
                        apply_command(state, UseAttack(0, index))
                    self.assertEqual(ctx.exception.code, T19B)
                    self.assertEqual(snap(state), before)

    def test_path_check_reads_only_the_element_and_the_registered_type(self):
        from kyuura_engine import effects as E
        from kyuura_engine.resolution import programs as P

        self.assertEqual(P.Status.NULLIFIED_COIN_EFFECTS, (E.ConfuseOnHeads, E.PoisonOnHeads, E.ParalyzeOnHeads))
        import inspect

        source = inspect.getsource(P.Status._nullified_coin_path)
        self.assertNotIn("PMCG", source)  # カード ID の定数で分けない


class ApiTest(unittest.TestCase):
    """S9: 合法手 API の候補・入力・check は両方の集合で同じ。submit だけが違う（TR7 は受理・全員に見える記録、厳密側は拒否・観測の変化なし・本人に拒否の応答）。"""

    def flow(self, key, sides):
        host = L.ActionHost(A.HostedGame(board(key=key, sides=sides)))
        session = host.session(0)
        r = session.candidates()
        (cand,) = [c for c in r["candidates"] if c["kind"] == "use_attack"]
        inputs = session.inputs(r["game"], r["revision"], cand["id"])
        option = inputs["stages"][0]["options"][0]["id"]
        checked = session.check(r["game"], r["revision"], cand["id"], [option])
        return host, session, r, cand, inputs, checked, option

    def strip(self, value):
        value = copy.deepcopy(value)
        if isinstance(value, dict):
            for k in ("game", "revision"):
                value.pop(k, None)
        return value

    def test_candidates_inputs_check_same_submit_differs(self):
        for sides in ((HEADS, HEADS), (TAILS, TAILS)):
            with self.subTest(sides=sides):
                s = self.flow(C.DEFAULT_SET, sides)
                t = self.flow(TR7, sides)
                for i in (2, 4, 5):
                    self.assertEqual(self.strip(s[i]), self.strip(t[i]))
                self.assertTrue(t[5]["valid"])
                viewers = (0, 1, None)
                s_before = [visible_log(s[0].game.state, v) for v in viewers]
                s_state = snap(s[0].game.state)
                sent = s[1].submit(s[2]["game"], s[2]["revision"], s[3]["id"], [s[6]])
                self.assertEqual((sent.outcome, sent.view.diagnostic_id, sent.view.status), (D.REJECTED, T19B, "in_progress"))
                self.assertEqual([visible_log(s[0].game.state, v) for v in viewers], s_before)
                self.assertEqual(snap(s[0].game.state), s_state)
                t_before = [len(visible_log(t[0].game.state, v)) for v in viewers]
                sent = t[1].submit(t[2]["game"], t[2]["revision"], t[3]["id"], [t[6]])
                self.assertEqual(sent.outcome, D.ACCEPTED)
                added = [[e["kind"] for e in visible_log(t[0].game.state, v)[n:]] for v, n in zip(viewers, t_before)]
                self.assertEqual(added[0], added[1])
                self.assertEqual(added[0], added[2])
                self.assertEqual(added[0].count("convention_applied"), 1 if sides[0] is HEADS else 0)


class AuditTest(unittest.TestCase):
    """ログの監査（s2a_problems）は規約の記録を、監査が独立に持つ表とログの並びで照らす（エンジンの登録を信じない）。"""

    def test_audit_accepts_the_record_and_detects_tampering(self):
        done, _ = attack(board(key=TR7, sides=(HEADS, HEADS)))
        self.assertEqual(s2a_problems(done), [])
        i = next(i for i, e in enumerate(done.log) if e["kind"] == "convention_applied")
        for label, change in (("extra_field", lambda e: e.update(hand=1)), ("wrong_player", lambda e: e.update(player=1)),
                              ("wrong_element", lambda e: e.update(element="sleep")), ("wrong_pokemon", lambda e: e.update(pokemon_id=99))):
            with self.subTest(label):
                bad = done.clone()
                record = dict(bad.log[i])
                change(record)
                bad.log = bad.log[:i] + (record,) + bad.log[i + 1:] if isinstance(bad.log, tuple) else bad.log[:i] + [record] + bad.log[i + 1:]
                self.assertNotEqual(s2a_problems(bad), [])
        moved = done.clone()
        log = list(moved.log)
        log.insert(i + 1, log.pop(i))  # ワザのコインのあとに置く
        moved.log = type(moved.log)(log) if isinstance(moved.log, tuple) else log
        self.assertNotEqual(s2a_problems(moved), [])


class JudgeTest(unittest.TestCase):
    """本物の runner（構築盤面のスナップショットから）と逐次バッチの判定の入口。TR7 の受理は expected。厳密側の拒否の判定は今のまま（judge の根拠表に T19b がないので
    evidence_missing_stop。この版で judge は変えない）。"""

    def run_attack(self, key, sides, negative=None):
        from tools.verification_ai import fixtures_u_r3a as F
        from tools.verification_ai import runner as V
        from tools.verification_ai.policies import UniformPolicy
        from tests.test_verification_ai_lost_target_p1 import RecordedFixtureRunner

        class AttackThenEnd(UniformPolicy):
            name, version = "scripted-test", 0

            def __init__(self):
                super().__init__("scripted-test")
                self.attacked = False

            def choose(self, purpose, items, context):
                if purpose == "candidate":
                    kinds = [c.get("kind") for c in items]
                    if not self.attacked and "use_attack" in kinds:
                        self.attacked = True
                        return kinds.index("use_attack"), "scripted"
                    for kind in ("answer_decision", "end_turn"):
                        if kind in kinds:
                            return kinds.index(kind), "scripted"
                return 0, "scripted"

        text, error = F.snapshot_text(board(defender=haunter(damage=30), key=key, sides=sides), f"tr7-{key[0]}")
        self.assertIsNotNone(text, error)
        config = V.Config(profile="boundary", limits=V.Limits(operations=2, seconds=60), run_id=f"test-tr7-{key[0]}")
        return RecordedFixtureRunner(config, text, policy_factory=lambda seed, dist: AttackThenEnd(), negative=negative).run()

    def test_accepted_attack_is_expected(self):
        from tools.verification_ai import batch as B
        from tools.verification_ai import judge as J
        from tests.test_verification_ai_batch_judge import NoNegative

        for sides in ((HEADS, HEADS), (HEADS, TAILS), (TAILS, HEADS)):
            for key in (TR7, C.DEFAULT_SET):
                with self.subTest(sides=sides, key=key):
                    result = self.run_attack(key, sides)
                    entry = next(e for e in result["trace"] if e.get("type") == "attempt" and e.get("submit") is not None and e["candidate"]["kind"] == "use_attack")
                    judged = B.judge_trace(result)
                    row = next(r for r in judged["rows"] if r["attempt"] == entry["n"])
                    if key == TR7:
                        self.assertEqual(entry["submit"]["outcome"], D.ACCEPTED)
                        self.assertEqual((row["verdict"], row["engine_code"], judged["undetermined"], judged["known_stop"]), (J.EXPECTED, None, [], []))
                        single = self.run_attack(key, sides, negative=NoNegative())
                        (s_entry,) = [e for e in single["trace"] if e.get("type") == "attempt" and e.get("submit") is not None and e["n"] == entry["n"]]
                        self.assertEqual(s_entry["judge"]["verdict"], J.EXPECTED)  # 単局の runner の判定（変異の実行の中）も同じ
                    else:
                        # 厳密側は今のまま（judge を変えない）: 拒否は根拠表にないので evidence_missing_stop で undetermined
                        self.assertEqual((entry["submit"]["outcome"], row["engine_code"], row["verdict"]), (D.REJECTED, T19B, J.UNDETERMINED))
                        self.assertNotIn(T19B, J.KNOWN_STOP_EVIDENCE)
                        self.assertEqual([u["category"] for u in judged["undetermined"]], ["evidence_missing_stop"])


if __name__ == "__main__":
    unittest.main()

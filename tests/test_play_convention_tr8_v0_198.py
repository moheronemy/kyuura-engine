"""v0.198（docs/play-convention-tr8-v0.198.md）: ラッキースタジアムの別の個体の同じ番の使用のプレイ用の続行規約 PC-LUCKY-STADIUM-REPLACEMENT@1
（開発用の集合 CS-KYUURA-PLAY-TR8@1）。

利用者の指示（2026-11-23。設計 docs/rs1-lucky-stadium-replacement-design.md 12 章）: 「自分の番ごとに1回」と書かれたラッキースタジアムをこの番に使ったあと、同じ名前の
別の個体に入れかわったとき、その個体を 1 回使える。回数はプレイヤー・自分の番・カードの個体で数える。場のカードと、この番の同じ名前の記録のすべてのカードが、効果の登録の型
CoinDrawStadium で once_stated のときだけ。明示的に選んだ TR8 の集合だけで有効。プレイ用の取り決めで、史実の裁定の確定ではない（RS1 の停止コードは厳密側・既存の集合・
事例 #other で active のまま）。

確かめの種類を分ける（設計 12.7 の V1〜V13）:

- 構築盤面（tests.helpers.build_test_state。規約集合は操作の前に置く。コインは with_coin_results）: 登録・厳密側の拒否と巻き戻し・TR8 の受理（A→B・B を使ったあとの C・
  異版・PRN-027 の対照・名前の違うスタジアムをはさむ・山札 0）・同じ個体の 2 回目・SX2・先行する停止・範囲の外の型・翌番と相手の番・保存と復元・記録とログの対応・
  候補 API と直接のコマンドの一致・記録のカードを手札・山札へ移した双子・ログの監査
- 本物の runner（スナップショットから復元した構築盤面）と逐次バッチの判定の入口（``batch.judge_trace``）: TR8 の受理は expected
"""

from __future__ import annotations

import json
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import conventions as C
from kyuura_engine import diagnostics as D
from kyuura_engine import effects as E
from kyuura_engine import legal_actions as L
from kyuura_engine import snapshot as S
from kyuura_engine.cards import load_card_pool
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import EndTurn, PlayTrainer, ResolveDecision, UsePokemonPower, UseStadium
from kyuura_engine.engine import apply_command, check_invariants, new_game
from kyuura_engine.errors import EngineError, IllegalActionError, UnsupportedError
from kyuura_engine.observation import visible_log
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from tests import helpers as H
from tests.log_audit import observation_problems, s2a_problems, serialization_problems

LATEST = max(FORMAT_VERSIONS)
TR8 = ("CS-KYUURA-PLAY-TR8", 1)
TR7 = ("CS-KYUURA-PLAY-TR7", 1)
CONV_ID = "PC-LUCKY-STADIUM-REPLACEMENT"
RS1 = "UNRESOLVED_STADIUM_REUSE_AFTER_REPLACEMENT"
SCENE = RS1 + "#lucky-once-stated-replacement"
OTHER = RS1 + "#other"
SX2 = "UNRESOLVED_STADIUM_REUSE_AFTER_RETURN"
STB1 = "UNRESOLVED_STADIUM_ACTIVATION_UNDER_TRAINER_BAN"
LK1 = "UNRESOLVED_LUCKY_STADIUM_UNSTATED_REPEAT"
FG1 = "UNRESOLVED_FUCHSIA_GYM_AFTER_REPLACEMENT"
STRICT_SETS = (C.DEFAULT_SET, TR7)
HD, TL = CoinSide.HEADS, CoinSide.TAILS
P15, P16, P17, P22, NIP2X, NEO, P027 = "PRN-015", "PRN-016", "PRN-017", "PRN-022", "NIP2X-009", "neo4-106", "PRN-027"
TARGET_VERSIONS = (NIP2X, "PRN-015", "PRN-016", "PRN-017", "PRN-018", "PRN-019", "PRN-020", "PRN-021", "PRN-022", NEO)
PORYGON2, PORYGON = "neo4-097", "neo4-086"
HEALING_FIELD, RADIO_TOWER = "neo3-054", "neo4-112"
# 既存の集合の照合値（v0.142〜v0.197 の固定の値。この版で変えない）
EXISTING_SET_DIGESTS = {
    ("CS-KYUURA-CURRENT", 1): "sha256:9a9b95c689d86fa01a5b710984560efda3c08f4dbf1d7c6218094ac8666f3cee",
    ("CS-KYUURA-LEGACY-UNRECORDED", 1): "sha256:abf39e6d87755507a9169537608596246f4ed9a9bf0c2e8794ffa44a97742407",
    ("CS-KYUURA-PLAY-S2A", 1): "sha256:b317a3f050206577bff35ac05c87fdb4224ee28c6c0222e4e7f8460b5e9410c4",
    ("CS-KYUURA-PLAY-PO", 1): "sha256:06d512194feee1857319f0c765ab2162d5259e4519895ed057d176d15fc43528",
    ("CS-KYUURA-PLAY-TR3", 1): "sha256:a7b800cff2a8614d7b181cc3a8a39f68ec4e17be9ceab0a04e75a48c4358ffb4",
    ("CS-KYUURA-PLAY-TR4", 1): "sha256:15af975a643c8d5844bf76e0a85ab20020ca331b01c463aeb344047806435552",
    ("CS-KYUURA-PLAY-TR6", 1): "sha256:aa53bc52cfc1d2193a3e1692efc585cf7daef23251c5d08dd09d7e554cf6ead2",
    ("CS-KYUURA-PLAY-TR7", 1): "sha256:4ee438eac0d76a1ec4fed207764fb0741c21b50f138ae3c699d73d7d6d828c45",
}


def snap(state):
    return (json.dumps(state_to_dict(state, format_version=LATEST), sort_keys=True, ensure_ascii=False),
            json.dumps([dict(e) for e in state.log], sort_keys=True, ensure_ascii=False), repr(state.rng.getstate()))


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])
    test.assertEqual(s2a_problems(state), [])


def build(key=TR8, **me):
    mine = {"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": [H.RATTATA], "deck": [H.FIRE] * 10, "prizes": 2, "discard": [], "hand": []}
    mine.update(me)
    them = {"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": [H.RATTATA], "hand": [H.WATER], "deck": [H.FIRE] * 10, "prizes": 2}
    state = H.build_test_state([mine, them], turn_number=7)
    if key != C.DEFAULT_SET:
        state.conventions = C.registered_identity(key)
    return state


def hand_uid(state, card_id, player=0):
    return next(u for u in state.players[player].hand if state.cards[u].card_id == card_id)


def resolve(state, prefer=()):
    while state.decision is not None:
        d = state.decision
        pick = [o for o in d.options if o in prefer][:d.max_choices]
        if len(pick) < d.min_choices:
            pick += [o for o in d.options if o not in pick and o not in prefer][:d.min_choices - len(pick)]
        state = apply_command(state, ResolveDecision(d.player, d.id, tuple(pick)))
    return state


def play(state, card_id, coins=(), prefer=()):
    if coins:
        state = H.with_coin_results(state, *coins)
    return resolve(apply_command(state, PlayTrainer(0, hand_uid(state, card_id))), prefer)


def use(state, coin=TL, player=0):
    return resolve(apply_command(H.with_coin_results(state, coin), UseStadium(player)))


def end_turn(state):
    return resolve(apply_command(state, EndTurn(state.current_player)))


def replaced(key=TR8, first=P15, second=P16, extra=(), **me):
    """``first`` を出して使い（「おもて」）、``second`` に入れかえた盤面。"""
    state = play(build(key, hand=[first, second, *extra], **me), first)
    return play(use(state, HD), second)


def rejects(test, state, code, error=UnsupportedError, player=0):
    before = snap(state)
    with test.assertRaises(error) as caught:
        apply_command(state, UseStadium(player))
    test.assertEqual(caught.exception.code, code)
    test.assertEqual(snap(state), before)  # 状態・ログ・乱数は変わらない


def stadium_candidate(state, actor=0):
    host = L.ActionHost(A.HostedGame(state.clone()))
    session = host.session(actor)
    r = session.candidates()
    return host, session, r, next((c for c in r["candidates"] if c["kind"] == L.KIND_USE_STADIUM), None)


def time_shift_back(state, card):
    state = apply_command(H.with_coin_results(state, HD), UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
    d = state.decision
    return resolve(apply_command(state, ResolveDecision(d.player, d.id, (card,))))


def new_events(before, after):
    return [dict(e) for e in after.log[len(before.log):]]


class RegistrationTest(unittest.TestCase):
    def test_tr8_set_members_and_digests(self):
        spec = C.SETS[TR8]
        self.assertEqual((spec.usage, spec.completeness), (C.USAGE_DEVELOPMENT, C.COMPLETENESS_HALTS))
        tr7 = C.SETS[TR7]
        self.assertEqual(len(tr7.members), 26)
        self.assertEqual(spec.members, tr7.members + ((CONV_ID, 1),))  # TR7@1 の 26 規約と、新しい 1 規約
        self.assertEqual(C.validate(spec), [])
        identity = C.identity_of(spec)
        self.assertEqual(identity.digest, C.PINNED_SET_DIGESTS[TR8])
        for member, version, digest in identity.members:
            self.assertEqual(digest, C.PINNED_CONVENTION_DIGESTS[(member, version)], member)
            self.assertEqual(digest, C.convention_digest(C.CONVENTIONS[(member, version)]), member)
        convention = C.CONVENTIONS[(CONV_ID, 1)]
        self.assertEqual((convention.layer, convention.approval, convention.scenes), (C.LAYER_CONTINUATION, C.APPROVAL_USER_AGREED, (SCENE,)))
        self.assertIn("2026-11-23", convention.content["adoption"])
        self.assertIn((CONV_ID, 1), C.DEFAULT_REGISTRY.implemented_continuations)
        self.assertEqual(sorted(C.scenes_for_code(RS1)), [SCENE, OTHER])  # RS1 は 2 つの事例
        self.assertEqual([key for key, c in C.CONVENTIONS.items() if SCENE in c.scenes or OTHER in c.scenes], [(CONV_ID, 1)])
        self.assertTrue({"card", "used_cards"} <= C.APPLIED_FIELDS)

    def test_existing_sets_and_default_are_unchanged(self):
        for key, digest in EXISTING_SET_DIGESTS.items():
            with self.subTest(key=key):
                self.assertEqual(C.PINNED_SET_DIGESTS[key], digest)
                self.assertEqual(C.identity_of(C.SETS[key], for_new_game=False).digest, digest)
                self.assertNotIn((CONV_ID, 1), C.SETS[key].members)
        self.assertEqual(C.DEFAULT_SET, ("CS-KYUURA-CURRENT", 1))

    def test_target_versions_are_the_registered_type(self):
        """対象の版は、登録の全体で、効果の型が CoinDrawStadium で once_stated のもの（カード ID で決めない）。設計の 10 版と一致する。"""
        found = sorted(cid for cid, d in load_card_pool().definitions.items() if d.category == "trainer"
                       and isinstance(getattr(E.DEFAULT_EFFECTS.trainer_entry(cid), "effect", None), E.CoinDrawStadium)
                       and E.DEFAULT_EFFECTS.trainer_entry(cid).effect.once_stated)
        self.assertEqual(found, sorted(TARGET_VERSIONS))
        self.assertFalse(E.DEFAULT_EFFECTS.trainer_entry(P027).effect.once_stated)

    def test_lookup_only_in_tr8(self):
        for key in STRICT_SETS + ((C.S2A_SET_ID, 1), (C.PO_SET_ID, 1), ("CS-KYUURA-PLAY-TR3", 1), ("CS-KYUURA-PLAY-TR6", 1)):
            with self.subTest(key=key):
                self.assertIsNone(C.continuation_for(build(key), RS1, "lucky-once-stated-replacement"))
        lookup = C.continuation_for(build(TR8), RS1, "lucky-once-stated-replacement")
        self.assertEqual((lookup.convention, lookup.scene), ((CONV_ID, 1), SCENE))
        self.assertIsNone(C.continuation_for(build(TR8), RS1, "other"))

    def test_new_game_only_when_selected(self):
        deck = H.expand_decklist({H.DRATINI: 4, H.LIGHTNING: 56})
        self.assertEqual(new_game(deck, deck, 1).conventions.key, C.DEFAULT_SET)
        self.assertEqual(new_game(deck, deck, 1, conventions="CS-KYUURA-PLAY-TR8@1").conventions, C.registered_identity(TR8))


class StrictTest(unittest.TestCase):
    """厳密側と既存の集合は今のまま RS1 で拒否（コインの前。状態・乱数・ログは変わらない）。候補 API は unresolved_ruling・CANDIDATE_NOT_EXECUTABLE。"""

    def test_strict_sets_reject_and_candidate_is_not_executable(self):
        for key in STRICT_SETS:
            with self.subTest(key=key):
                state = replaced(key)
                rejects(self, state, RS1)
                host, session, r, cand = stadium_candidate(state)
                self.assertEqual((cand["processability"], cand["reasons"]), (L.RULING_UNRESOLVED, [L.REASON_STOPS]))
                before = snap(host.game.state)
                self.assertEqual(session.check(r["game"], r["revision"], cand["id"], [])["refusal"]["code"], L.CANDIDATE_NOT_EXECUTABLE)
                self.assertEqual(session.submit(r["game"], r["revision"], cand["id"], []).refusal.code, L.CANDIDATE_NOT_EXECUTABLE)
                self.assertEqual(snap(host.game.state), before)
                game = A.HostedGame(state.clone())
                result = game.submit(UseStadium(0), submitter=0)
                self.assertEqual((result.outcome, result.diagnosis.diagnostic_id), (D.REJECTED, RS1))


class AcceptedTest(unittest.TestCase):
    """TR8 の受理: ログは stadium_used → convention_applied → coin_flip →（「おもて」なら）draw。記録は (使ったプレイヤー, 新しい個体) が 1 件増える。"""

    def check_accept(self, state, coin, used_ids):
        after = use(state, coin)
        events = new_events(state, after)
        kinds = [e["kind"] for e in events]
        deck = len(state.players[0].deck)
        self.assertEqual(kinds, ["stadium_used", "convention_applied", "coin_flip"] + (["draw"] if coin is HD else []))
        applied = events[1]
        self.assertEqual({k: applied[k] for k in ("convention", "version", "scene", "code", "player", "card", "used_cards")},
                         {"convention": CONV_ID, "version": 1, "scene": SCENE, "code": RS1, "player": 0, "card": state.stadium.card, "used_cards": tuple(used_ids)})
        self.assertEqual(sum(1 for e in after.log if e["kind"] == "convention_applied"), sum(1 for e in state.log if e["kind"] == "convention_applied") + 1)
        self.assertEqual((events[2]["source"], events[2]["player"], events[2]["effect"]), ("stadium", 0, state.cards[state.stadium.card].card_id))
        self.assertEqual(len(after.players[0].hand) - len(state.players[0].hand), 1 if coin is HD and deck > 0 else 0)
        self.assertIsNone(after.result)  # 山札 0 の「おもて」でも負けにしない
        self.assertEqual(after.stadium_uses_this_turn, state.stadium_uses_this_turn + ((0, state.stadium.card),))
        audited(self, after)
        return after

    def test_a_to_b_both_coins(self):
        for coin in (HD, TL):
            with self.subTest(coin=coin):
                self.check_accept(replaced(), coin, [P15])

    def test_b_used_then_c(self):
        state = replaced(extra=[P17])
        after_b = self.check_accept(state, HD, [P15])
        c = play(after_b, P17)
        for coin in (HD, TL):
            with self.subTest(coin=coin):
                done = self.check_accept(c, coin, [P15, P16])
                self.assertEqual(sum(1 for e in done.log if e["kind"] == "convention_applied"), 2)

    def test_second_use_of_b_is_already_used(self):
        after_b = use(replaced(), HD)
        rejects(self, after_b, "STADIUM_ALREADY_USED", IllegalActionError)
        self.assertIsNone(stadium_candidate(after_b)[3])  # ゲーム上できない（候補を作らない）

    def test_versions_within_the_ten(self):
        for first, second in ((P15, NIP2X), (P15, NEO), (NEO, P15), (P16, P22)):
            with self.subTest(first=first, second=second):
                self.check_accept(replaced(first=first, second=second), TL, [first])

    def test_prn027_placed_but_not_used(self):
        state = play(play(use(play(build(hand=[P15, P027, P16]), P15), HD), P027), P16)
        self.check_accept(state, TL, [P15])

    def test_other_name_in_between(self):
        state = play(build(hand=[P15, H.FUCHSIA_CITY_GYM, P16], bench=[H.KOGAS_EKANS]), P15)
        state = play(use(play(use(state, HD), H.FUCHSIA_CITY_GYM), TL), P16)
        self.check_accept(state, HD, [P15])

    def test_deck_zero(self):
        state = replaced(deck=[])
        for coin in (HD, TL):
            with self.subTest(coin=coin):
                after = self.check_accept(state, coin, [P15])
                self.assertEqual(len(after.players[0].deck), 0)


class BoundaryTest(unittest.TestCase):
    """TR8 でも変えない場面（先に判定される停止と、範囲の外）。"""

    def test_sx2_with_and_without_b_used(self):
        for b_used in (False, True):
            with self.subTest(b_used=b_used):
                me = {"active": {"card": PORYGON2, "energy": [H.WATER], "evolved_from": [PORYGON]}, "deck": [H.WATER] * 10}
                state = play(build(hand=[P15, P16], **me), P15)
                a = state.stadium.card
                state = play(use(state, TL), P16)
                if b_used:
                    state = use(state, TL)
                back = time_shift_back(state, a)
                self.assertEqual(back.stadium.card, a)
                rejects(self, back, SX2)

    def test_prn027_controls(self):
        rejects(self, play(use(play(build(hand=[P15, P027]), P15), HD), P027), LK1)
        rejects(self, play(use(play(build(hand=[P027, P15]), P027), HD), P15), RS1)  # #other

    def test_preceding_stops(self):
        state = play(replaced(extra=[H.ROCKETS_EXPERIMENT]), H.ROCKETS_EXPERIMENT, coins=(TL,))
        rejects(self, state, STB1)
        state = play(use(replaced(extra=[H.ROCKETS_EXPERIMENT]), HD), H.ROCKETS_EXPERIMENT, coins=(TL,))
        rejects(self, state, "STADIUM_ALREADY_USED", IllegalActionError)

    def test_other_types_keep_rs1_and_fg1(self):
        cases = [
            (H.ENERGY_STADIUM, {"discard": [H.FIRE, H.FIRE]}, RS1),
            (H.KOGAS_NINJA_GYM, {"deck": [H.GRASS] * 3 + [H.KOGAS_KOFFING] * 7, "discard": [H.FIRE], "bench": [H.KOGAS_EKANS]}, RS1),
            (HEALING_FIELD, {"active": {"card": H.CHARMANDER, "energy": [H.FIRE], "damage": 30}}, RS1),
            (RADIO_TOWER, {}, RS1),
            (H.FUCHSIA_CITY_GYM, {"bench": [H.KOGAS_EKANS]}, FG1),
        ]
        for card, me, code in cases:
            with self.subTest(card=card):
                state = play(use(play(build(hand=[card, card], **me), card), TL), card)
                self.assertEqual(E.stadium_reuse_case(state, 0, state.stadium), "other")
                rejects(self, state, code)

    def test_next_turn_and_opponent(self):
        state = use(play(use(replaced(extra=[P17]), HD), P17), HD)
        state = end_turn(state)
        self.assertEqual(state.stadium_uses_this_turn, ())
        opponent = use(state, TL, player=1)
        self.assertFalse(any(e["kind"] == "convention_applied" for e in new_events(state, opponent)))
        own = end_turn(opponent)
        later = use(own, TL)
        self.assertFalse(any(e["kind"] == "convention_applied" for e in new_events(own, later)))


class ApiTest(unittest.TestCase):
    """候補 API と直接のコマンドは同じ確かめを通る。同じ盤面・同じ乱数から、候補 API の送信と直接のコマンドが同じ状態になる。候補・入力・check は状態を変えない。"""

    def test_candidate_is_executable_without_inputs_and_matches_direct(self):
        for coin in (HD, TL):
            with self.subTest(coin=coin):
                state = H.with_coin_results(replaced(), coin)
                host, session, r, cand = stadium_candidate(state)
                before = snap(host.game.state)
                self.assertEqual((cand["processability"], cand["reasons"], cand["choices_format"]), (L.MAY_STOP_LATER, [L.REASON_CONTINUATION], "[]"))
                self.assertEqual(session.inputs(r["game"], r["revision"], cand["id"]).get("stages") or [], [])
                self.assertTrue(session.check(r["game"], r["revision"], cand["id"], [])["valid"])
                self.assertEqual(snap(host.game.state), before)  # 候補・入力・check までで状態・乱数・ログは変わらない
                self.assertEqual(session.submit(r["game"], r["revision"], cand["id"], []).outcome, D.ACCEPTED)
                game = A.HostedGame(H.with_coin_results(replaced(), coin))
                self.assertEqual(game.submit(UseStadium(0), submitter=0).outcome, D.ACCEPTED)
                self.assertEqual(snap(host.game.state), snap(game.state))


class SnapshotTest(unittest.TestCase):
    def test_restore_keeps_record_set_and_result(self):
        state = replaced(extra=[P17])
        for label, s in (("after_replace", state), ("after_b_and_c", play(use(state, HD), P17))):
            with self.subTest(label):
                report = S.restore_snapshot(S.dumps_snapshot(S.save_snapshot(s)))
                self.assertEqual(report.status, "restored")
                restored = report.state
                self.assertEqual(snap(restored), snap(s))
                self.assertEqual(restored.conventions, C.registered_identity(TR8))
                a = use(H.with_coin_results(s.clone(), TL), TL)
                b = use(H.with_coin_results(restored, TL), TL)
                self.assertEqual(snap(a), snap(b))


class HiddenZoneTest(unittest.TestCase):
    """先に使ったカード A を手札（ダウジングマシーン）・山札（リサイクル）へ移したあと。非公開の所在・並びだけを変えた双子で、判定と公開の規約の記録・相手と観戦者の閲覧が
    同じで、新しいログに A の uid が出ない（used_cards は版だけ）。"""

    def twin(self, zone, variant):
        extra = [H.WATER, H.GRASS] if variant == 0 else [H.GRASS, H.WATER]
        deck = [H.FIRE, H.WATER, H.GRASS, H.FIRE, H.FIRE, H.FIRE] if variant == 0 else [H.FIRE, H.FIRE, H.FIRE, H.GRASS, H.WATER, H.FIRE]
        trainer = H.ITEM_FINDER if zone == "hand" else H.RECYCLE
        state = play(build(hand=[P15, P16, trainer, H.FIRE, H.FIRE, *extra], deck=deck), P15)
        a = state.stadium.card
        state = play(use(state, HD), P16)
        if zone == "hand":
            discard = tuple(u for u in state.players[0].hand if state.cards[u].card_id == H.FIRE)[:2]
            state = play(state, trainer, prefer=discard + (a,))
            self.assertIn(a, state.players[0].hand)
        else:
            state = play(state, trainer, coins=(HD,), prefer=(a,))
            self.assertIn(a, state.players[0].deck)
        return state, a

    def test_twins(self):
        for zone in ("hand", "deck"):
            with self.subTest(zone=zone):
                results = []
                for variant in (0, 1):
                    state, a = self.twin(zone, variant)
                    after = use(state, TL)
                    events = new_events(state, after)
                    self.assertFalse(any(a == v or (isinstance(v, (list, tuple)) and a in v) for e in events for k, v in e.items() if k != "turn"))
                    audited(self, after)
                    results.append((E.stadium_reuse_case(state, 0, state.stadium), [e for e in events if e["kind"] == "convention_applied"],
                                    visible_log(after, 1)[len(state.log):], visible_log(after, None)[len(state.log):]))
                self.assertNotEqual(snap(self.twin(zone, 0)[0])[0], snap(self.twin(zone, 1)[0])[0])  # 双子は非公開の所在・並びが違う
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0][0], "lucky-once-stated-replacement")


class AuditTest(unittest.TestCase):
    """ログの監査（s2a_problems）は規約の記録を、監査が独立に持つ表とログの並びで照らす。"""

    def test_audit_accepts_the_record_and_detects_tampering(self):
        done = use(replaced(), HD)
        self.assertEqual(s2a_problems(done), [])
        i = next(i for i, e in enumerate(done.log) if e["kind"] == "convention_applied")
        for label, change in (("extra_field", lambda e: e.update(hand=1)), ("wrong_player", lambda e: e.update(player=1)),
                              ("wrong_card", lambda e: e.update(card=0)), ("uid_in_used", lambda e: e.update(used_cards=(3,))),
                              ("wrong_used", lambda e: e.update(used_cards=(P17,)))):
            with self.subTest(label):
                bad = done.clone()
                record = dict(bad.log[i])
                change(record)
                bad.log = bad.log[:i] + (record,) + bad.log[i + 1:] if isinstance(bad.log, tuple) else bad.log[:i] + [record] + bad.log[i + 1:]
                self.assertNotEqual(s2a_problems(bad), [])
        moved = done.clone()
        log = list(moved.log)
        log.insert(i + 1, log.pop(i))  # コインのあとに置く
        moved.log = type(moved.log)(log) if isinstance(moved.log, tuple) else log
        self.assertNotEqual(s2a_problems(moved), [])


class JudgeTest(unittest.TestCase):
    """本物の runner（構築盤面のスナップショットから）と逐次バッチの判定の入口。TR8 の受理は expected。厳密側の拒否の判定は今のまま（judge は変えない）。"""

    def run_use(self, key, coin, negative=None):
        from tools.verification_ai import fixtures_u_r3a as F
        from tools.verification_ai import runner as V
        from tools.verification_ai.policies import UniformPolicy
        from tests.test_verification_ai_lost_target_p1 import RecordedFixtureRunner

        class UseThenEnd(UniformPolicy):
            name, version = "scripted-test", 0

            def __init__(self):
                super().__init__("scripted-test")
                self.used = False

            def choose(self, purpose, items, context):
                if purpose == "candidate":
                    kinds = [c.get("kind") for c in items]
                    if not self.used and "use_stadium" in kinds:
                        self.used = True
                        return kinds.index("use_stadium"), "scripted"
                    for kind in ("answer_decision", "end_turn"):
                        if kind in kinds:
                            return kinds.index(kind), "scripted"
                return 0, "scripted"

        text, error = F.snapshot_text(H.with_coin_results(replaced(key), coin), f"tr8-{key[0]}")
        self.assertIsNotNone(text, error)
        config = V.Config(profile="boundary", limits=V.Limits(operations=2, seconds=60), run_id=f"test-tr8-{key[0]}")
        return RecordedFixtureRunner(config, text, policy_factory=lambda seed, dist: UseThenEnd(), negative=negative).run()

    def test_accepted_use_is_expected(self):
        from tools.verification_ai import batch as B
        from tools.verification_ai import judge as J
        from tests.test_verification_ai_batch_judge import NoNegative

        for coin in (HD, TL):
            with self.subTest(coin=coin):
                result = self.run_use(TR8, coin)
                entry = next(e for e in result["trace"] if e.get("type") == "attempt" and e.get("submit") is not None and e["candidate"]["kind"] == "use_stadium")
                judged = B.judge_trace(result)
                row = next(r for r in judged["rows"] if r["attempt"] == entry["n"])
                self.assertEqual(entry["submit"]["outcome"], D.ACCEPTED)
                self.assertEqual((row["verdict"], row["engine_code"], judged["undetermined"], judged["known_stop"]), (J.EXPECTED, None, [], []))
                single = self.run_use(TR8, coin, negative=NoNegative())
                (s_entry,) = [e for e in single["trace"] if e.get("type") == "attempt" and e.get("submit") is not None and e["n"] == entry["n"]]
                self.assertEqual(s_entry["judge"]["verdict"], J.EXPECTED)


if __name__ == "__main__":
    unittest.main()

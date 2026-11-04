"""v0.142: 規約集合の識別・版の管理と、対戦への組み込み（docs/ruleset-foundation-v0.142.md）。

確かめること（件数を写さない。壊した構成・状態を見つけること、今の挙動が変わらないことを確かめる）:

- 省略・明示（ConventionSet・"ID@版"・識別）で、同じ操作の結果（書き出し・乱数・ログ・観測）が同じ
- 照合値: 同じ内容から同じ値（辞書の順序・改行・Unicode の正規化・PYTHONHASHSEED によらない）、意味の内容を変えると変わり、説明上の参照を変えても変わらない
- 構成の検査: 同じ ID・版の内容違い・未知・重複・競合・依存の不足・未実装・承認のない続行規約・旧状態用の集合での開始・完全性の主張・利用者の指定を外した集合を拒否する
- 呼び出し元・登録表を後から変えても進行中の対戦の意味が変わらない（登録の内容が状態の識別と合わなければ、推測で続けずに拒否する）
- サドン・デス・決定待ち・途中停止・複製・保存で同じ識別を持つ。対戦中に集合を変えるコマンドはない
- 記録のない旧状態は条件つきで旧状態用の集合に対応付け、判断できない状態は拒否する
- 未決の場面の続行規約の照会は、どの場面でも「なし」で、今までどおり止める
- 拒否で状態・乱数・ログが変わらない
"""

from __future__ import annotations

import copy
import dataclasses
import os
import pickle
import subprocess
import sys
import unittest
from types import MappingProxyType
from unittest import mock

from kyuura_engine import (
    EndTurn,
    IllegalActionError,
    Phase,
    StartSuddenDeath,
    UnsupportedError,
    apply_command,
    commands,
    new_game,
    observe,
    state_to_dict,
)
from kyuura_engine import conventions as C
from kyuura_engine import effects as E
from kyuura_engine.deck import expand_decklist
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import GameState
from tests.helpers import (
    DRATINI,
    LIGHTNING,
    PIKACHU_DECK,
    PIKACHU_DECK_B,
    build_test_state,
)
from tests.test_deferred_shortage_user_promos_v0_127 import declare, dry_board, dry_up
from tests.test_pikachu_games import play_game as pikachu_game

LATEST = max(FORMAT_VERSIONS)
CURRENT = f"{C.CURRENT_SET_ID}@1"
# 停止コードの名前は書かない（停止の方針の台帳がテストの中の停止コードの文字列を数えるので、同梱の場面の一覧から引く）
SCENE_A, SCENE_B = sorted(s["id"] for s in C.scene_index()["scenes"] if s["codes"] and "#" not in s["id"])[:2]
MULLIGAN = next(s["codes"][0] for s in C.scene_index()["scenes"] if s["id"].endswith("#sudden-death-segment") and "MULLIGAN" in s["id"])
FEW_BASICS = expand_decklist({DRATINI: 1, LIGHTNING: 59})  # たねポケモン 1 枚（切り直しがよく起こり、切り直しの補償の停止に当たる）


def snapshot(state):
    return state_to_dict(state, format_version=LATEST), state.rng.getstate(), tuple(dict(e) for e in state.log)


def replay(commands_, seed, conventions=None):
    state = new_game(PIKACHU_DECK, PIKACHU_DECK_B, seed, **({} if conventions is None else {"conventions": conventions}))
    for command in commands_:
        state = apply_command(state, command)
    return state


def without_record(state):
    """v0.141 までの状態の写し（規約集合の項目がない pickle）と同じ読み方をした状態。"""
    data = state.__getstate__()
    del data["conventions"]
    old = object.__new__(GameState)
    old.__setstate__(data)
    return old


def make_registry(*conventions, sets=(), pin=True, implemented=frozenset()):
    """試験の登録表（今の登録に、試験の規約・集合を加える）。``pin`` が真なら、試験の規約・集合の照合値をその場で固定する。"""
    convs = dict(C.CONVENTIONS)
    convs.update({(c.id, c.version): c for c in conventions})
    pinned = dict(C.PINNED_CONVENTION_DIGESTS)
    if pin:
        pinned.update({(c.id, c.version): C.convention_digest(c) for c in conventions})
    all_sets = dict(C.SETS)
    all_sets.update({(s.id, s.version): s for s in sets})
    registry = C.Registry(MappingProxyType(convs), MappingProxyType(all_sets), MappingProxyType(pinned), C.PINNED_SET_DIGESTS,
                          implemented_continuations=frozenset(implemented))
    if pin:
        pinned_sets = dict(C.PINNED_SET_DIGESTS)
        for s in sets:
            digests = {key: C.convention_digest(convs[key]) for key in s.members if key in convs}
            if len(digests) == len(s.members):
                pinned_sets[(s.id, s.version)] = C._digest(C._SET_DOMAIN, C.set_payload(s, digests))
        registry = dataclasses.replace(registry, pinned_sets=MappingProxyType(pinned_sets))
    return registry


def continuation(cid="PLAY-TEST", version=1, *, approval=C.APPROVAL_NOT_APPROVED, scenes=None, requires=(), conflicts=(), effect="x"):
    return C.Convention(cid, version, C.LAYER_CONTINUATION, approval, "試験の続行規約", content={"effect": effect}, requires=requires, conflicts=conflicts,
                        scenes=(SCENE_A,) if scenes is None else scenes)


def with_members(*extra, usage=C.USAGE_DEVELOPMENT, set_id="CS-TEST", completeness=C.COMPLETENESS_HALTS):
    return C.ConventionSet(set_id, 1, usage, C.SETS[C.DEFAULT_SET].members + tuple((c.id, c.version) for c in extra), completeness=completeness)


def setUpModule():
    global GAME, GAME_COMMANDS
    GAME, GAME_COMMANDS = pikachu_game(9)  # サドン・デスで終わる対戦（tests/test_sudden_death_v0_134.py と同じ）


class IdentityTest(unittest.TestCase):
    def test_registered_sets_validate_and_match_pins(self):
        for key, spec in C.SETS.items():
            with self.subTest(set=key):
                self.assertEqual(C.validate(spec, for_new_game=spec.usage != C.USAGE_LEGACY), [])
                self.assertEqual(C.registered_identity(key).digest, C.PINNED_SET_DIGESTS[key])
        for key, convention in C.CONVENTIONS.items():
            self.assertEqual(C.convention_digest(convention), C.PINNED_CONVENTION_DIGESTS[key], key)

    def test_digest_ignores_order_newlines_normalization_and_references(self):
        a = C.Convention("X", 1, C.LAYER_CONTINUATION, C.APPROVAL_NOT_APPROVED, "文\n2 行", content={"a": 1, "b": ["ポ", "カ"]}, references=("docs/a.md:10",))
        b = C.Convention("X", 1, C.LAYER_CONTINUATION, C.APPROVAL_NOT_APPROVED, "文\r\n2 行", content={"b": ("ポ", "カ"), "a": 1}, references=("docs/b.md:99",))
        self.assertEqual(C.convention_digest(a), C.convention_digest(b))  # ポ（NFC）と ホ+゜（NFD）、CRLF と LF、辞書の順序、参照の違い

    def test_digest_changes_with_meaning(self):
        base = continuation()
        for changed in (continuation(effect="y"), continuation(version=2), continuation(scenes=(SCENE_A, SCENE_B)),
                        continuation(requires=(("A", 1),)), continuation(approval=C.APPROVAL_USER_AGREED),
                        dataclasses.replace(base, statement="別の文"), dataclasses.replace(base, layer=C.LAYER_CURRENT_BEHAVIOR)):
            self.assertNotEqual(C.convention_digest(changed), C.convention_digest(base), changed)

    def test_user_registration_change_changes_digest(self):
        record = E.USER_SPECIFIED_RULES["PR1-027/trainer"]
        convention = C.CONVENTIONS[("USER-SWAP-OWNERSHIP-RECEIVER", 1)]
        before = C.convention_digest(convention)
        semantic = dataclasses.replace(record, scope=record.scope + "（変えた）")
        reference = dataclasses.replace(record, source="docs/other.md#9")
        with mock.patch.object(E, "USER_SPECIFIED_RULES", MappingProxyType({**E.USER_SPECIFIED_RULES, "PR1-027/trainer": semantic})):
            self.assertNotEqual(C.convention_digest(convention), before)
        with mock.patch.object(E, "USER_SPECIFIED_RULES", MappingProxyType({**E.USER_SPECIFIED_RULES, "PR1-027/trainer": reference})):
            self.assertEqual(C.convention_digest(convention), before)  # 根拠の文書の場所は意味の内容ではない

    def test_digest_independent_of_hash_seed(self):
        code = "from kyuura_engine import conventions as C; print(C.registered_identity(C.DEFAULT_SET).digest)"
        outputs = set()
        for seed in ("0", "1", "12345"):
            env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONUTF8="1")
            outputs.add(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True).stdout.strip())
        self.assertEqual(outputs, {C.PINNED_SET_DIGESTS[C.DEFAULT_SET]})

    def test_baseline_members_are_user_agreed_and_current_behavior_is_not_approved(self):
        identity = C.default_identity()
        layers = {m: C.CONVENTIONS[(m, v)] for m, v, _ in identity.members}
        self.assertEqual({m for m, c in layers.items() if c.layer == C.LAYER_BASELINE_USER}, set(C.user_registrations()))
        self.assertTrue(all(c.approval == C.APPROVAL_USER_AGREED for c in layers.values() if c.layer == C.LAYER_BASELINE_USER))
        self.assertTrue(all(c.approval == C.APPROVAL_NOT_APPROVED for c in layers.values() if c.layer == C.LAYER_CURRENT_BEHAVIOR))
        self.assertFalse(any(c.layer == C.LAYER_CONTINUATION for c in layers.values()))  # この版は続行規約を 1 つも採用していない
        self.assertEqual(identity.completeness, C.COMPLETENESS_HALTS)


class ValidationTest(unittest.TestCase):
    def problems(self, spec, registry=C.DEFAULT_REGISTRY, **kw):
        return C.validate(spec, registry, **kw)

    def assert_rejects(self, spec, fragment, registry=C.DEFAULT_REGISTRY, **kw):
        found = self.problems(spec, registry, **kw)
        self.assertTrue(any(fragment in p for p in found), found)
        with self.assertRaises(C.ConventionSetError):
            C.identity_of(spec, registry, **kw)

    def test_same_id_and_version_with_other_content(self):
        changed = continuation(effect="y")
        registry = make_registry(continuation(), implemented={("PLAY-TEST", 1)})
        registry = dataclasses.replace(registry, conventions=MappingProxyType({**registry.conventions, ("PLAY-TEST", 1): changed}))
        self.assert_rejects(with_members(changed), "固定した照合値と違う", registry)
        spec = C.SETS[C.DEFAULT_SET]
        self.assert_rejects(dataclasses.replace(spec, members=spec.members[:-1]), "登録した同じ ID・版の集合と違う")
        self.assert_rejects(dataclasses.replace(spec, usage=C.USAGE_DEVELOPMENT), "登録した同じ ID・版の集合と違う")

    def test_unknown_set_member_and_version(self):
        self.assert_rejects(dataclasses.replace(C.SETS[C.DEFAULT_SET], id="CS-UNKNOWN"), "未知の集合 ID")
        self.assert_rejects(dataclasses.replace(C.SETS[C.DEFAULT_SET], version=2), "知っている版は [1]")
        spec = C.SETS[C.DEFAULT_SET]
        self.assert_rejects(dataclasses.replace(spec, members=spec.members + (("PLAY-UNKNOWN", 1),)), "未知の規約 ID")
        self.assert_rejects(dataclasses.replace(spec, members=spec.members[:-1] + ((spec.members[-1][0], 2),)), "知っている版は [1]")

    def test_duplicate_conflict_and_missing_dependency(self):
        spec = C.SETS[C.DEFAULT_SET]
        self.assert_rejects(dataclasses.replace(spec, members=spec.members + (spec.members[0],)), "重複")
        a = continuation("PLAY-A", conflicts=(("PLAY-B", 1),), scenes=(SCENE_A,))
        b = continuation("PLAY-B", scenes=(SCENE_B,))
        registry = make_registry(a, b, implemented={("PLAY-A", 1), ("PLAY-B", 1)})
        self.assert_rejects(with_members(a, b), "競合", registry)
        need = continuation("PLAY-NEED", requires=(("PLAY-B", 1),))
        registry = make_registry(need, b, implemented={("PLAY-NEED", 1), ("PLAY-B", 1)})
        self.assert_rejects(with_members(need), "依存の不足", registry)
        self.assertEqual(self.problems(with_members(need, b), make_registry(need, b, sets=(with_members(need, b),), implemented={("PLAY-NEED", 1), ("PLAY-B", 1)})), [])

    def test_two_conventions_on_one_scene(self):
        a, b = continuation("PLAY-A"), continuation("PLAY-B")
        registry = make_registry(a, b, implemented={("PLAY-A", 1), ("PLAY-B", 1)})
        self.assert_rejects(with_members(a, b), "2 つ以上の規約", registry)

    def test_unimplemented_unapproved_and_usage(self):
        play = continuation()
        self.assert_rejects(with_members(play), "未実装", make_registry(play, sets=(with_members(play),)))  # 登録はあるが、この版のエンジンに処理がない
        registry = make_registry(play, sets=(with_members(play, usage=C.USAGE_STANDARD),), implemented={("PLAY-TEST", 1)})
        self.assert_rejects(with_members(play, usage=C.USAGE_STANDARD), "通常の集合に入れない", registry)
        dev = with_members(play)
        self.assertEqual(self.problems(dev, make_registry(play, sets=(dev,), implemented={("PLAY-TEST", 1)})), [])  # 開発用の集合なら、承認のない続行規約を入れられる
        self.assertEqual(C.identity_of(dev, make_registry(play, sets=(dev,), implemented={("PLAY-TEST", 1)})).usage, C.USAGE_DEVELOPMENT)
        self.assert_rejects(C.SETS[(C.LEGACY_SET_ID, 1)], "新しい対戦には使わない")
        self.assertEqual(self.problems(C.SETS[(C.LEGACY_SET_ID, 1)], for_new_game=False), [])

    def test_completeness_claim_is_not_implemented(self):
        claim = with_members(completeness=C.COMPLETENESS_PLAY)
        self.assert_rejects(claim, "完全性の判定は、この版では実装していない", make_registry(sets=(claim,)))

    def test_cannot_drop_user_specs_or_approve_current_behavior(self):
        spec = C.SETS[C.DEFAULT_SET]
        dropped = C.ConventionSet("CS-TEST", 1, C.USAGE_DEVELOPMENT, spec.members[1:])
        self.assert_rejects(dropped, "外した集合は、この版のエンジンが実装できない", make_registry(sets=(dropped,)))
        approved = dataclasses.replace(C.CONVENTIONS[(C.CURRENT_BEHAVIOR_ID, 1)], approval=C.APPROVAL_USER_AGREED)
        registry = make_registry(approved, sets=(spec,))
        self.assert_rejects(spec, "承認済みにしない", registry)

    def test_new_game_rejects_before_creating_state(self):
        for bad in ("CS-UNKNOWN@1", f"{C.CURRENT_SET_ID}@2", "no-version", f"{C.LEGACY_SET_ID}@1", object(),
                    dataclasses.replace(C.default_identity(), digest="sha256:" + "0" * 64)):
            with self.subTest(bad=bad), self.assertRaises(C.ConventionSetError) as caught:
                new_game(PIKACHU_DECK, PIKACHU_DECK_B, 1, conventions=bad)
            self.assertEqual(caught.exception.code, C.INVALID_CONVENTION_SET_CODE)


class GameTest(unittest.TestCase):
    def test_default_and_explicit_are_the_same_game(self):
        expected = snapshot(GAME)
        for spec in (CURRENT, C.SETS[C.DEFAULT_SET], C.default_identity()):
            with self.subTest(spec=spec):
                state = replay(GAME_COMMANDS, 9, spec)
                self.assertEqual(snapshot(state), expected)
                self.assertEqual(state.conventions, C.default_identity())
                self.assertEqual(observe(state, 0), observe(GAME, 0))

    def test_identity_holds_only_values(self):
        state = new_game(PIKACHU_DECK, PIKACHU_DECK_B, 3, conventions=C.SETS[C.DEFAULT_SET])
        identity = state.conventions
        self.assertIsInstance(identity, C.ConventionSetIdentity)
        flat = [identity.set_id, identity.version, identity.digest, identity.usage, identity.completeness, *[x for m in identity.members for x in m]]
        self.assertTrue(all(isinstance(x, (str, int)) for x in flat))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            identity.version = 2

    def test_registry_change_after_start_is_not_followed(self):
        state = new_game(PIKACHU_DECK, PIKACHU_DECK_B, 3)
        record = E.USER_SPECIFIED_RULES["PR1-027/trainer"]
        changed = MappingProxyType({**E.USER_SPECIFIED_RULES, "PR1-027/trainer": dataclasses.replace(record, scope="変えた")})
        before = snapshot(state)
        with mock.patch.object(E, "USER_SPECIFIED_RULES", changed):
            for call in (lambda: apply_command(state, EndTurn(0)), lambda: observe(state, None)):
                with self.assertRaises(UnsupportedError) as caught:
                    call()
                self.assertEqual(caught.exception.code, C.UNSUPPORTED_CONVENTION_SET_CODE)
            with self.assertRaises(C.ConventionSetError):
                new_game(PIKACHU_DECK, PIKACHU_DECK_B, 3)  # 固定した照合値と違う登録では、新しい対戦も始めない
        self.assertEqual(snapshot(state), before)
        observe(state, None)  # 登録をもどせば同じ状態で続けられる

    def test_no_command_changes_the_set(self):
        names = {name for name in dir(commands) if isinstance(getattr(commands, name), type)}
        self.assertFalse(any("convention" in n.lower() or "ruleset" in n.lower() for n in names), names)

    def test_sudden_death_keeps_the_set(self):
        self.assertIs(GAME.phase, Phase.SUDDEN_DEATH)
        new = apply_command(GAME, StartSuddenDeath())
        self.assertIs(new.conventions, GAME.conventions)
        legacy = apply_command(without_record(GAME), StartSuddenDeath())
        self.assertIs(legacy.conventions, C.UNRECORDED)  # 記録のない旧状態は、記録のないまま（推測で今の集合にしない）
        self.assertEqual(observe(legacy, None)["convention_set"]["id"], C.LEGACY_SET_ID)

    def test_kept_through_decision_interruption_copies(self):
        asked = declare(dry_board(1))
        halted = dry_up(dry_board(1), 2)
        self.assertIsNotNone(asked.decision)
        self.assertIsNotNone(halted.halt.interruption)
        for state in (asked, halted, GAME):
            for copied in (state.clone(), state.peek(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
                self.assertEqual(copied.conventions, C.default_identity())
            self.assertEqual(state_to_dict(state, format_version=LATEST)["convention_set"], C.default_identity().record())

    def test_unresolved_stops_have_no_continuation(self):
        identity = C.default_identity()
        index = C.scene_index()
        for scene in index["scenes"]:
            for code in scene["codes"]:
                case = scene["id"].split("#", 1)[1] if "#" in scene["id"] else None
                lookup = C.continuation_lookup(identity, code, case)
                self.assertEqual((lookup.status, lookup.convention, lookup.scene), ("no_continuation", None, scene["id"]), scene["id"])
        for code, scenes in index["codes"].items():
            lookup = C.continuation_lookup(identity, code)
            self.assertIsNone(lookup.convention)
            self.assertEqual(lookup.status, "no_continuation" if len(scenes) == 1 else "case_not_identified", code)  # コードだけで事例を決めない
        self.assertEqual(C.continuation_lookup(identity, "USER-SWAP-OWNERSHIP-RECEIVER").status, "unknown_scene")  # 基礎の規約は場面の照会の対象ではない

    def test_whole_game_halts_still_halt(self):
        found = {}
        for seed in range(400):
            state = new_game(FEW_BASICS, FEW_BASICS, seed)
            if state.phase is Phase.HALTED:
                found.setdefault(state.halt.code, seed)
        self.assertIn(MULLIGAN, found)
        state = new_game(FEW_BASICS, FEW_BASICS, found[MULLIGAN], conventions=CURRENT)
        self.assertIs(state.phase, Phase.HALTED)
        self.assertEqual(state.log[-1]["kind"], "halted")
        self.assertEqual(state_to_dict(state, format_version=34), state_to_dict(new_game(FEW_BASICS, FEW_BASICS, found[MULLIGAN]), format_version=34))
        halted = dry_up(dry_board(1), 2)  # 途中停止（DU1）も今までどおり
        self.assertIs(halted.phase, Phase.HALTED)

    def test_rejections_change_nothing(self):
        state = new_game(PIKACHU_DECK, PIKACHU_DECK_B, 5, conventions=CURRENT)
        before = snapshot(state)
        with self.assertRaises((IllegalActionError, UnsupportedError)):
            apply_command(state, EndTurn(1))
        self.assertEqual(snapshot(state), before)
        broken = state.clone()
        broken.conventions = dataclasses.replace(state.conventions, digest="sha256:" + "f" * 64)
        broken_before = (broken.rng.getstate(), tuple(broken.log))
        with self.assertRaises(UnsupportedError) as caught:
            apply_command(broken, EndTurn(0))
        self.assertEqual(caught.exception.code, C.UNSUPPORTED_CONVENTION_SET_CODE)
        self.assertEqual((broken.rng.getstate(), tuple(broken.log)), broken_before)


class LegacyTest(unittest.TestCase):
    def test_recorded_game_without_record_maps_to_legacy(self):
        state = new_game(PIKACHU_DECK, PIKACHU_DECK_B, 4)
        old = without_record(state)
        self.assertIs(old.conventions, C.UNRECORDED)
        self.assertEqual(C.require_state_conventions(old).set_id, C.LEGACY_SET_ID)
        self.assertEqual(observe(old, 0)["convention_set"]["id"], C.LEGACY_SET_ID)
        self.assertEqual(state_to_dict(old, format_version=LATEST)["convention_set"]["id"], C.LEGACY_SET_ID)
        self.assertEqual(state_to_dict(old, format_version=34), state_to_dict(state, format_version=34))  # 形式 34 までは項目がない（前の版と同じ）
        copied = pickle.loads(pickle.dumps(old))
        self.assertIs(type(copied.conventions), C.UnrecordedConventions)
        legacy_members = [(m, v) for m, v, _ in C.registered_identity((C.LEGACY_SET_ID, 1)).members]
        self.assertEqual(legacy_members, [(m, v) for m, v, _ in C.default_identity().members])  # 処理はこの版のエンジンのまま（過去の版の挙動の再現は主張しない）

    def test_undeterminable_states_are_rejected(self):
        board = without_record(build_test_state([{"active": {"card": "PMCG1-058"}, "deck": ["PMCG1-058"] * 5, "prizes": 1},
                                                 {"active": {"card": "PMCG1-058"}, "deck": ["PMCG1-058"] * 5, "prizes": 1}]))
        state = new_game(PIKACHU_DECK, PIKACHU_DECK_B, 4)
        edited = without_record(state)
        edited.log = (type(edited.log[0])({**edited.log[0], "convention_set": "x"}),) + edited.log[1:]
        mismatched = without_record(state)
        mismatched.seed = state.seed + 1
        garbage = state.clone()
        garbage.conventions = None
        unknown = state.clone()
        unknown.conventions = dataclasses.replace(state.conventions, set_id="CS-FROM-LATER-VERSION")
        for name, bad in (("盤面を直接作った", board), ("作成のログに知らない項目", edited), ("作成のログと合わない", mismatched), ("記録の形が違う", garbage), ("知らない集合", unknown)):
            with self.subTest(name):
                for call in (lambda bad=bad: observe(bad, None), lambda bad=bad: apply_command(bad, EndTurn(0))):
                    with self.assertRaises(UnsupportedError) as caught:
                        call()
                    self.assertEqual(caught.exception.code, C.UNSUPPORTED_CONVENTION_SET_CODE)
                    self.assertNotIn("CS-FROM-LATER-VERSION", caught.exception.message)  # 状態の中の値を理由の文に書かない
                with self.assertRaises(ValueError):
                    state_to_dict(bad, format_version=LATEST)


class ExportTest(unittest.TestCase):
    def test_format_35_and_old_formats(self):
        state = new_game(PIKACHU_DECK, PIKACHU_DECK_B, 2)
        data = state_to_dict(state, format_version=LATEST)
        self.assertEqual(LATEST, 35)
        import kyuura_engine
        self.assertEqual((data["convention_set"], data["engine_version"]), (C.default_identity().record(), kyuura_engine.__version__))
        old = state_to_dict(state, format_version=34)
        self.assertEqual(old, {k: v for k, v in data.items() if k not in ("convention_set", "engine_version", "format_version")} | {"format_version": 34})
        dev = state.clone()
        dev.conventions = dataclasses.replace(state.conventions, set_id="CS-TEST", usage=C.USAGE_DEVELOPMENT)
        for version in (1, 9, 34):
            with self.assertRaises(ValueError):
                state_to_dict(dev, format_version=version)  # 落とすと意味が変わる集合を、古い形式に黙って書かない



class RecordsTest(unittest.TestCase):
    """同梱の記録（場面と停止コードの対応・今の挙動の記録）の検査が、対応の漏れ・不正な参照・食い違いを見つける（件数は写さない）。"""

    @classmethod
    def setUpClass(cls):
        import json
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(root / "scripts"))
        import build_convention_records as B

        cls.B = B
        cls.ledger, cls.assumptions = B.load_json(B.LEDGER), B.load_json(B.ASSUMPTIONS)
        cls.plan = B.load_json(B.PLAN)
        cls.written = json.loads(B.OUTPUT.read_text(encoding="utf-8"))

    def problems(self, written):
        return self.B.check(written, self.ledger, self.assumptions, self.plan)

    def broken(self):
        return copy.deepcopy(self.written)

    def assert_detects(self, written, fragment):
        found = self.problems(written)
        self.assertTrue(any(fragment in p for p in found), found)

    def test_written_records_have_no_problems(self):
        self.assertEqual(self.problems(self.written), [])
        self.assertEqual(self.written["scene_index"], C.scene_index())

    def test_detects_missing_code_mapping(self):
        b = self.broken()
        code = next(c for c, v in b["scene_index"]["codes"].items() if len(v) == 1)
        del b["scene_index"]["codes"][code]
        self.assert_detects(b, "対応の漏れ")

    def test_detects_unknown_scene_and_code(self):
        b = self.broken()
        b["scene_index"]["scenes"].append({"id": "SCENE-NOT-IN-LEDGER", "entry_kind": "research_stop_code", "codes": ["CODE-NOT-IN-LEDGER"]})
        self.assert_detects(b, "台帳の項目にない")
        self.assert_detects(b, "台帳の停止コードにない")

    def test_detects_case_mismatch_and_duplicates(self):
        b = self.broken()
        code = next(c for c, v in b["scene_index"]["codes"].items() if len(v) > 1)
        b["scene_index"]["codes"][code] = b["scene_index"]["codes"][code][:1]
        self.assert_detects(b, "事例")
        b = self.broken()
        b["scene_index"]["scenes"].append(dict(b["scene_index"]["scenes"][0]))
        self.assert_detects(b, "重複")

    def test_detects_current_behavior_drift(self):
        b = self.broken()
        b["current_behavior"]["items"] = b["current_behavior"]["items"][1:]
        self.assert_detects(b, "作り直した記録と違う")


if __name__ == "__main__":
    unittest.main()

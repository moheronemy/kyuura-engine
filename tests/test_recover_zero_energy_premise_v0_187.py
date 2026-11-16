"""判定の規則 10（docs/verification-ai-recover-zero-energy-design.md 8 章）の、エンジンの側の静的な前提と構築盤面での確認（エンジンの処理は変えない）。

- ``UNRESOLVED_RECOVER_ZERO_ENERGY`` を実際に投げる箇所は ``resolution/programs.py`` の ``RecoverEnergy.resume`` の 1 か所（構文木の文字列の定数で数える。説明文の中の名前は
  別の、より長い文字列なので数えない）
- 決定の種類 ``recover_energy`` を出す（``suspend``）のは 3 要素で、最小 0 を出すのは ``RecoverEnergy`` だけ
- 0 枚の答えは決定の確認（``checks.decision_choices``）を通り、そのあと状態を変える前に対象のコードで拒否され、同じ本人の決定待ちのまま（状態・乱数・ログ・決定が同じ）
- 1 枚の答えは受理される（0 枚の拒否と区別）。数・重なりの不正は別のコード（``IllegalActionError``）
- ワザをコピーする経路のうち、ピッピ・ピクシーの「ゆびをふる」（``CopyOpponentAttackEffect``。登録はこの 2 枚だけ）は、同じ要素・同じ決定の形・同じ再開先・同じ拒否になる
"""

from __future__ import annotations

import ast
import inspect
import pathlib
import unittest

from kyuura_engine import IllegalActionError, ResolveDecision, UnsupportedError, UseAttack, apply_command, load_card_pool, state_to_dict
from kyuura_engine import effects as E
from kyuura_engine.checks import decision_choices
from kyuura_engine.decisions import RECOVER_ENERGY
from kyuura_engine.resolution import programs as P
from kyuura_engine.rng import rng_fingerprint

from tests.helpers import CLEFABLE, CLEFAIRY, FIRE, GASTLY, GROWLITHE, PSYCHIC, RATTATA, WATER, build_test_state

CODE = "UNRESOLVED_RECOVER_ZERO_ENERGY"
PACKAGE = pathlib.Path(P.__file__).resolve().parents[1]


def _parsed():
    for path in sorted(PACKAGE.rglob("*.py")):
        yield path.relative_to(PACKAGE).as_posix(), ast.parse(path.read_text(encoding="utf-8"))


def _enclosing(tree):
    """各ノード → (囲むクラスの名前, 囲む関数の名前)。"""
    out = {}

    def walk(node, cls, fn):
        for child in ast.iter_child_nodes(node):
            c = child.name if isinstance(child, ast.ClassDef) else cls
            f = child.name if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
            out[child] = (cls, fn)
            walk(child, c, f)
    walk(tree, None, None)
    return out


def gastly_board(discard=(FIRE, WATER)):
    return build_test_state([{"active": {"card": GASTLY, "energy": [PSYCHIC, PSYCHIC]}, "bench": [RATTATA], "discard": list(discard)}, {"active": GROWLITHE}],
                            turn_number=7)


def metronome_board(copier):
    me = {"card": copier, "energy": [PSYCHIC, PSYCHIC, PSYCHIC]}
    if copier == CLEFABLE:
        me["evolved_from"] = CLEFAIRY
    return build_test_state([{"active": me, "discard": [FIRE, WATER]}, {"active": {"card": GASTLY, "energy": [PSYCHIC, PSYCHIC]}}], turn_number=7)


def written(state):
    return state_to_dict(state, format_version=9)


class StaticPremiseTest(unittest.TestCase):
    def test_the_code_is_raised_at_exactly_one_site(self):
        sites = []
        for name, tree in _parsed():
            where = _enclosing(tree)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and node.value == CODE:
                    sites.append((name, *where[node]))
        self.assertEqual(sites, [("resolution/programs.py", "RecoverEnergy", "resume")])
        # その定数は raise UnsupportedError(...) の最初の引数
        source = inspect.getsource(P.RecoverEnergy.resume)
        tree = ast.parse(source.lstrip() if source.startswith(" ") else source)
        raises = [n for n in ast.walk(tree) if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)
                  and getattr(n.exc.func, "id", None) == "UnsupportedError" and isinstance(n.exc.args[0], ast.Constant) and n.exc.args[0].value == CODE]
        self.assertEqual(len(raises), 1)
        # 説明文の中の名前（effects.py の RecoverEnergyAndSelfDamage）は、投げる箇所ではない
        self.assertIn(CODE, E.RecoverEnergyAndSelfDamage.__doc__)

    def test_only_recover_energy_suspends_with_min_zero(self):
        found = []
        for name, tree in _parsed():
            where = _enclosing(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                kinds = [k.value for k in node.keywords if k.arg == "kind"]
                if not kinds or not any((isinstance(v, ast.Name) and v.id == "RECOVER_ENERGY") or (isinstance(v, ast.Attribute) and v.attr == "RECOVER_ENERGY")
                                        or (isinstance(v, ast.Constant) and v.value == RECOVER_ENERGY) for v in kinds):
                    continue
                func = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
                minimum = next((ast.unparse(k.value) for k in node.keywords if k.arg == "min_choices"), None)
                found.append((name, where[node][0], func, minimum))
        generating = sorted(x for x in found if x[2] != "_decision_form")
        self.assertEqual(generating, [("resolution/programs.py", "RecoverEnergy", "suspend", "0"),
                                      ("resolution/programs.py", "RecoverEnergyByHeads", "suspend", "heads"),
                                      ("resolution/programs.py", "RecoverSpecialEnergy", "suspend", None)])
        # _decision_form は決定の形の確かめ（作らない）。effects.py だけ
        self.assertTrue(all(x[0] == "effects.py" for x in found if x[2] == "_decision_form"))
        self.assertEqual(inspect.signature(P.AttackRun.suspend).parameters["min_choices"].default, 1)  # RecoverSpecialEnergy は 1〜1
        self.assertIn("if not heads or not candidates:", inspect.getsource(P.RecoverEnergyByHeads.run))  # おもて 0 なら決定を出さない
        # 要素を作るのは RecoverEnergyAndSelfDamage だけ。その登録はゴースのエナジーへんかんだけ
        self.assertEqual([(k.card_id, k.attack_index) for k in E.DEFAULT_EFFECTS.attack_keys()
                          if isinstance(E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect, E.RecoverEnergyAndSelfDamage)], [(GASTLY, 1)])

    def test_copy_attack_effect_is_registered_only_for_the_two_metronomes(self):
        self.assertEqual(sorted((k.card_id, k.attack_index) for k in E.DEFAULT_EFFECTS.attack_keys()
                                if isinstance(E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect, E.CopyOpponentAttackEffect)),
                         [(CLEFAIRY, 1), (CLEFABLE, 0)])


class BoardTest(unittest.TestCase):
    def assert_zero_rejected_then_one_accepted(self, waiting):
        decision = waiting.decision
        self.assertEqual((decision.kind, decision.min_choices, decision.max_choices, len(decision.options)), (RECOVER_ENERGY, 0, 2, 2))
        cmd = ResolveDecision(0, decision.id, ())
        self.assertEqual(decision_choices(waiting, cmd), ())  # 構造の検査は通る
        before, fingerprint, log = written(waiting), rng_fingerprint(waiting.rng), waiting.log
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(waiting, cmd)
        self.assertEqual(ctx.exception.code, CODE)
        self.assertEqual((written(waiting), rng_fingerprint(waiting.rng)), (before, fingerprint))
        self.assertIs(waiting.log, log)
        self.assertIs(waiting.decision, decision)
        self.assertEqual((waiting.decision.player, waiting.decision.id), (0, decision.id))
        for choices, code in (((decision.options[0],) * 2, "DUPLICATE_CHOICE"), (decision.options + (decision.options[0],), "INVALID_CHOICE_COUNT")):
            with self.assertRaises(IllegalActionError) as bad:
                apply_command(waiting, ResolveDecision(0, decision.id, choices))
            self.assertEqual(bad.exception.code, code)
        done = apply_command(waiting, ResolveDecision(0, decision.id, decision.options[:1]))
        self.assertIn("recover_energy", [e["kind"] for e in done.log[len(log):]])
        return decision

    def test_own_printed_attack(self):
        waiting = apply_command(gastly_board(), UseAttack(0, 1))
        decision = self.assert_zero_rejected_then_one_accepted(waiting)
        self.assertEqual(decision.resume, "attack")

    def test_metronome_paths_use_the_same_element_decision_and_resume(self):
        own = apply_command(gastly_board(), UseAttack(0, 1)).decision
        for copier in (CLEFAIRY, CLEFABLE):
            with self.subTest(copier=copier):
                definition = load_card_pool().get(copier)
                index = next(i for i, a in enumerate(definition.attacks) if a.name_ja == "ゆびをふる")
                selecting = apply_command(metronome_board(copier), UseAttack(0, index))
                self.assertEqual(selecting.decision.kind, "select_attack")
                waiting = apply_command(selecting, ResolveDecision(0, selecting.decision.id, (1,)))  # 相手のゴースのエナジーへんかん
                decision = self.assert_zero_rejected_then_one_accepted(waiting)
                self.assertEqual((decision.resume, decision.min_choices, decision.kind), (own.resume, own.min_choices, own.kind))
                self.assertEqual(decision.context_value("copied"), (GASTLY, 1))

    def test_no_decision_without_energy_in_discard(self):
        done = apply_command(gastly_board(discard=()), UseAttack(0, 1))
        self.assertIsNone(done.decision)


if __name__ == "__main__":
    unittest.main()

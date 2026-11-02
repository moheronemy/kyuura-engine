"""停止の方針の分類台帳（docs/stop-policy-classification.json）のための、現行コードの静的な抽出。

エンジンの動作は変えない（読むだけ）。``scripts/build_stop_policy_classification.py`` が使う。抽出するもの:

- 接頭辞 ``UNSUPPORTED_``・``UNRESOLVED_`` のコード: 文字列リテラル・コメント・識別子（定数名の一部）を区別して、出現位置を集める（tokenize）。
  モジュールの最上位の ``NAME = "CODE"`` の定数を、コードの別名として解決する
- 接頭辞のないコードで ``UnsupportedError`` を作る箇所（リテラルの第 1 引数）
- 内部ガード: ``raise`` の対象が ``RuntimeError``・``NotImplementedError``・``AssertionError``・``StateIntegrityError``・``UnsupportedByKernel`` の呼び出しの箇所
  （v0.133 の棚卸しの internal_guard と同じ型の集合。対応は (ファイル, 例外の型, 文) で取る）
- ``Phase.HALTED`` への代入・``Halt(`` の作成・``halt(``・``interrupt(`` の呼び出しの箇所

静的な抽出は、実行時に到達することの証明ではない。見つからないことも、到達しないことの証明ではない。
"""

from __future__ import annotations

import ast
import io
import pathlib
import re
import tokenize

CODE_RE = re.compile(r"\b((?:UNSUPPORTED|UNRESOLVED)_[A-Z0-9_]*[A-Z0-9])\b")
GUARD_TYPES = ("RuntimeError", "NotImplementedError", "AssertionError", "StateIntegrityError", "UnsupportedByKernel")
ENGINE_DIR = "kyuura_engine"
TEST_DIRS = ("tests",)
TOOL_DIRS = ("tools", "scripts")


def python_files(root: pathlib.Path, base: str) -> list[pathlib.Path]:
    return sorted(p for p in (root / base).rglob("*.py") if "__pycache__" not in p.parts)


def rel(root: pathlib.Path, path: pathlib.Path) -> str:
    return path.relative_to(root).as_posix()


_PARSED: dict[pathlib.Path, tuple[str, ast.AST, dict[int, str]]] = {}


def parsed(path: pathlib.Path) -> tuple[str, ast.AST, dict[int, str]]:
    """(本文, 構文木, 行 → 関数・クラスの名前)。大きいファイル（effects.py）の解析を一度にする。"""
    if path not in _PARSED:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        _PARSED[path] = (text, tree, _scope_names(tree))
    return _PARSED[path]


def token_occurrences(root: pathlib.Path, path: pathlib.Path) -> list[tuple[str, int, str]]:
    """(コード, 行, 種類) の並び。種類は literal（文字列リテラルの中）・comment・name（識別子の一部。定数名など）。"""
    found = []
    text = path.read_text(encoding="utf-8")
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.STRING or getattr(tokenize, "FSTRING_MIDDLE", -1) == tok.type:
            kind = "literal"
        elif tok.type == tokenize.COMMENT:
            kind = "comment"
        elif tok.type == tokenize.NAME:
            kind = "name"
        else:
            continue
        for code in CODE_RE.findall(tok.string):
            found.append((code, tok.start[0], kind))
    return found


def module_code_constants(root: pathlib.Path) -> dict[str, str]:
    """``NAME = "CODE"``（モジュールの最上位・クラスの本体）の定数名 → コード。同じ名前に違うコードがあれば両方を ``名前@ファイル`` で持つ。"""
    constants: dict[str, str] = {}
    for path in python_files(root, ENGINE_DIR):
        _, tree, _ = parsed(path)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
                    and CODE_RE.fullmatch(node.value.value)):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        key = target.id if target.id not in constants or constants[target.id] == node.value.value else f"{target.id}@{rel(root, path)}"
                        constants[key] = node.value.value
    return constants


def prefixed_codes(root: pathlib.Path) -> dict[str, dict]:
    """コード → {"engine": {"literal": [...], "comment": [...], "name": [...]}, "tests": {...}, "tools": {...}}（位置は "path:line"）。"""
    codes: dict[str, dict] = {}

    def add(area: str, path: pathlib.Path) -> None:
        for code, line, kind in token_occurrences(root, path):
            entry = codes.setdefault(code, {"engine": {}, "tests": {}, "tools": {}})
            entry[area].setdefault(kind, []).append(f"{rel(root, path)}:{line}")

    for path in python_files(root, ENGINE_DIR):
        add("engine", path)
    for base in TEST_DIRS:
        for path in python_files(root, base):
            add("tests", path)
    for base in TOOL_DIRS:
        for path in python_files(root, base):
            add("tools", path)
    return codes


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
    return None


def _scope_names(tree: ast.AST) -> dict[int, str]:
    """行 → それを含むいちばん内側の関数・クラスの名前（``Class.method`` の形）。"""
    scopes: dict[int, str] = {}

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}.{child.name}" if prefix else child.name
                for line in range(child.lineno, (child.end_lineno or child.lineno) + 1):
                    scopes[line] = name
                visit(child, name)
            else:
                visit(child, prefix)

    visit(tree, "")
    return scopes


def guard_sites(root: pathlib.Path) -> list[dict]:
    sites = []
    for path in python_files(root, ENGINE_DIR):
        _, tree, scopes = parsed(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise) and node.exc is not None:
                name = _call_name(node.exc)
                if name in GUARD_TYPES:
                    sites.append({"path": rel(root, path), "line": node.lineno, "type": name, "scope": scopes.get(node.lineno, ""),
                                  "source": ast.unparse(node.exc)})
    return sites


def nonprefix_unsupported(root: pathlib.Path) -> list[dict]:
    """``UnsupportedError("CODE", ...)`` のうち、第 1 引数が接頭辞のないリテラルのもの。"""
    found = []
    for path in python_files(root, ENGINE_DIR):
        _, tree, _ = parsed(path)
        for node in ast.walk(tree):
            if (_call_name(node) == "UnsupportedError" and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
                    and not CODE_RE.fullmatch(node.args[0].value)):
                found.append({"code": node.args[0].value, "site": f"{rel(root, path)}:{node.lineno}"})
    return found


def halt_sites(root: pathlib.Path) -> list[dict]:
    sites = []
    for path in python_files(root, ENGINE_DIR):
        _, tree, scopes = parsed(path)
        for node in ast.walk(tree):
            kind = None
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Attribute) and t.attr == "phase" for t in node.targets):
                if isinstance(node.value, ast.Attribute) and node.value.attr == "HALTED":
                    kind = "phase_halted_assignment"
            elif _call_name(node) == "Halt":
                kind = "halt_record"
            elif _call_name(node) in ("halt", "_halt", "interrupt"):
                kind = f"{_call_name(node)}_call"
            if kind:
                sites.append({"path": rel(root, path), "line": node.lineno, "kind": kind, "scope": scopes.get(node.lineno, "")})
    return sorted(sites, key=lambda s: (s["path"], s["line"], s["kind"]))

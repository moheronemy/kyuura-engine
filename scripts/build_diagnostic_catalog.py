"""診断のコード表 kyuura_engine/data/diagnostic_catalog.json を作る・確かめる（v0.152。docs/diagnostics-adapter-v0.152.md 3 章）。

    python scripts/build_diagnostic_catalog.py --write   # 停止の方針の台帳・場面の索引・エンジンのソースから、コード表を書き直す
    python scripts/build_diagnostic_catalog.py --check   # 書いたコード表が作り直したものと同じか、エンジンが投げうるコードに表の漏れがないか

コード表は、エンジンが返す元のコード → 診断の分類・事例・安全な定型文の対応。停止の方針の台帳（研究上の停止・実行時の停止のコード）と、台帳の外のコード（不正な操作の
``IllegalActionError``・状態の不整合・デッキの検査・規約集合の構成）は別の集合で、台帳には加えない。

- 台帳のコード: 台帳の分類から決める（C → 未裁定、B → 技術的制限、A → 未対応。互換性の 3 つは仕様案の ``compatibility_codes``）。分類 E のコードは ``LEDGER_E_CODES`` に書いたものだけを
  入れ、ほかの E があれば --check が問題にする（推測で分類しない）
- 不正な操作のコード: エンジンのソースの ``IllegalActionError(...)`` の最初の引数から集める（文字列・文字列の定数）。f 文字列・変数・タプルの展開の呼び出し箇所は ``DYNAMIC_SITES`` に、
  作りうるコードを書く（関数が返すタプルは、その関数の中のタプルの先頭の文字列から集める）。表にない動的な呼び出し箇所があれば --check が問題にする
- 事例: 同梱の場面の索引（kyuura_engine/data/convention_records.json）のコード → 場面。場面が 1 つなら、その場面を事例にできる。2 つ以上なら、実行時にも事例を選ばない（not_identified）
- 安全な定型文: 埋め込みのない決まった文だけ（カード名・uid・枚数を入れない）。``CODE_TEXTS`` に個別の文、なければ分類ごとの文
"""

from __future__ import annotations

import argparse
import ast
import functools
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENGINE = ROOT / "kyuura_engine"
OUTPUT = ENGINE / "data" / "diagnostic_catalog.json"
LEDGER = ROOT / "docs" / "stop-policy-classification.json"
RECORDS = ENGINE / "data" / "convention_records.json"
SPEC = ROOT / "docs" / "diagnostics-replay-api-design.json"

SCHEMA_VERSION = 1
CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*[A-Z0-9]$")

# 台帳の分類 E の実行時の停止コードのうち、コード表に入れるもの（理由つき）。ほかの E は --check が問題にする
LEDGER_E_CODES = {
    "UNRESOLVED_RULING": ("unresolved_ruling", "決定の答えの共通の既定のコード（研究上の停止。事例を持たない）"),
}
# 台帳の分類 E のうち、例外のコードとして投げないので入れないもの（理由つき）
LEDGER_E_EXCLUDED = {
    "UNSUPPORTED_CARD": "デッキの検査の問題の文の中だけ（例外のコードは INVALID_DECK）",
}

# 台帳の外のコード（例外の型ごとに決まった 1 つ）
FIXED_CODES = {
    "STATE_INTEGRITY": ("state_integrity", ("state_integrity",), "StateIntegrityError（errors.py）"),
    "INVALID_DECK": ("invalid_input", ("deck_validation",), "DeckValidationError（errors.py）"),
    "INVALID_CONVENTION_SET": ("invalid_input", ("convention_set",), "ConventionSetError（conventions.py）"),
}

# IllegalActionError の動的な呼び出し箇所: (ファイル, 囲む関数, 引数の式) → 作りうるコード、または ("from_function", ファイル, 関数)
DYNAMIC_SITES = {
    ("kyuura_engine/effects.py", "_own_pokemon", "f'{role}_NOT_IN_PLAY'"): ("SOURCE_NOT_IN_PLAY", "TARGET_NOT_IN_PLAY"),
    ("kyuura_engine/effects.py", "_own_pokemon", "f'{role}_NOT_YOURS'"): ("SOURCE_NOT_YOURS", "TARGET_NOT_YOURS"),
    ("kyuura_engine/effects.py", "_opponent_pokemon", "f'{role}_NOT_IN_PLAY'"): ("SOURCE_NOT_IN_PLAY", "TARGET_NOT_IN_PLAY"),
    ("kyuura_engine/effects.py", "_opponent_pokemon", "f'{role}_NOT_OPPONENTS'"): ("SOURCE_NOT_OPPONENTS", "TARGET_NOT_OPPONENTS"),
    ("kyuura_engine/effects.py", "check_usable", "f'{role}_NOT_NAMED'"): ("SOURCE_NOT_NAMED", "TARGET_NOT_NAMED"),
    ("kyuura_engine/effects.py", "_require_user_not_asleep_paralyzed_confused", "code"): ("POKEMON_ASLEEP", "POKEMON_PARALYZED", "POKEMON_CONFUSED"),
    ("kyuura_engine/effects.py", "attack_power_check", "code"): ("POKEMON_ASLEEP", "POKEMON_PARALYZED", "POKEMON_CONFUSED"),
    ("kyuura_engine/effects.py", "check_playable", "*prevented"): ("from_function", "kyuura_engine/evolution.py", "evolution_prevented"),
    # evolution_block のタプルのうち DEVOLVED_THIS_TURN_CODE は、この呼び出しの直前で UnsupportedError として投げる（engine._evolve_pokemon）ので、不正な操作のコードから除く
    ("kyuura_engine/engine.py", "_evolve_pokemon", "*block"): ("from_function", "kyuura_engine/evolution.py", "evolution_block", ("DEVOLVED_THIS_TURN_CODE",)),
}

CATEGORY_TEXTS = {
    "invalid_input": "この操作は、今の対戦の状態ではルール上できません。",
    "unresolved_ruling": "この場面の扱いは、基準のルールと記録からは決まらないため、エンジンはこの操作を受け付けません。",
    "unsupported": "この操作・効果は、このエンジンがまだ処理できません。",
    "technical_limit": "エンジンの処理の上限を超えるため、この操作を受け付けません。",
    "compatibility": "この対戦の状態または規約集合を、この版のエンジンは扱えません。",
    "state_integrity": "対戦の状態に問題が見つかったため、対戦を続けられません。",
}
# 停止した状態（拒否ではない）の決まった文。停止のコードは研究上の停止・未対応・技術的制限・互換性のコードだけ
HALT_TEXTS = {
    "unresolved_ruling": "この場面の扱いは、基準のルールと記録からは決まらないため、エンジンは対戦を止めました。",
    "unsupported": "このエンジンがまだ処理できない場面になったため、対戦を止めました。",
    "technical_limit": "エンジンの処理の上限を超える場面になったため、対戦を止めました。",
    "compatibility": "この版のエンジンが扱えない状態になったため、対戦を止めました。",
}
SUBKIND_TEXTS = {
    "invalid_input/answer": "この答えは、待っている決定に対して受け付けられません。",
    "invalid_input/setup": "対戦を始める条件（デッキ・規約集合・seed）が正しくありません。",
}
# 個別の決まった文（埋め込みなし）。ここにないコードは分類ごとの文
CODE_TEXTS = {
    "NOT_YOUR_TURN": "今はあなたの番ではありません。",
    "WRONG_PHASE": "今の対戦の段階では、この操作はできません。",
    "DECISION_PENDING": "先に、待っている決定に答えてください。",
    "WRONG_DECISION": "この答えは、今待っている決定のものではありません。",
    "NOT_YOUR_DECISION": "この決定は、あなたが答えるものではありません。",
    "INVALID_CHOICE": "選んだものが、選べるものの中にありません。",
    "INVALID_CHOICE_COUNT": "選んだ数が、選ぶ数の範囲にありません。",
    "DUPLICATE_CHOICE": "同じものを重ねて選んでいます。",
    "GAME_OVER": "この対戦は終わっています。",
    "UNKNOWN_COMMAND": "知らない種類の操作です。",
    "BAD_COMMAND": "操作の項目が足りないか、余分な項目があります。",
    "BAD_PLAYER": "プレイヤーの指定が正しくありません。",
    "INVALID_PLAYER": "プレイヤーの指定が正しくありません。",
    "CARD_NOT_IN_HAND": "そのカードは手札にありません。",
    "BENCH_FULL": "ベンチがいっぱいです。",
    "ENERGY_ALREADY_ATTACHED": "この番は、もう手札からエネルギーカードをつけています。",
    "INSUFFICIENT_ENERGY": "ワザに必要なエネルギーが足りません。",
    "INVALID_ATTACK": "そのワザは使えません。",
    "ATTACK_LOCKED": "そのワザは、効果によって使えません。",
    "POKEMON_ASLEEP": "そのポケモンはねむり状態です。",
    "POKEMON_PARALYZED": "そのポケモンはマヒ状態です。",
    "FIRST_TURN_EVOLUTION": "おたがいの最初の番には、ポケモンを進化させられません。",
    "PLAYED_THIS_TURN": "この番に場に出したポケモンは、この番には進化させられません。",
    "RETREAT_PREVENTED": "そのポケモンは、効果によってにげられません。",
    "WRONG_RETREAT_COST": "にげるためにトラッシュするエネルギーが正しくありません。",
    "TRAINER_PREVENTED": "効果によって、今はトレーナーカードを使えません。",
    "POWER_ALREADY_USED": "その特殊能力は、もう使っています。",
    "POWER_SUPPRESSED": "その特殊能力は、ほかの効果で使えません。",
    "SUDDEN_DEATH_NOT_STARTED": "サドン・デスの延長戦を始める操作だけを受け付けます。",
    "NOT_SUDDEN_DEATH": "今はサドン・デスの延長戦を始める段階ではありません。",
    "INVALID_PRIZE_INDEX": "サイドの位置の指定が正しくありません。",
    "INVALID_DECK": "デッキが対戦の条件を満たしていません。",
    "INVALID_CONVENTION_SET": "指定した規約集合が正しくありません。",
}


def rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


@functools.cache
def _parse(path: pathlib.Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=1)
def _string_constants() -> dict[str, set[str]]:
    """エンジンの中の ``大文字の名前 = "コード"`` の代入（モジュール・クラスの直下だけ。関数の中の変数は定数として扱わない）。名前 → 値の集合。"""
    found: dict[str, set[str]] = {}
    for path in sorted(ENGINE.rglob("*.py")):
        tree = _parse(path)
        bodies = [tree.body] + [n.body for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        for body in bodies:
            for node in body:
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            found.setdefault(target.id, set()).add(node.value.value)
    return found


def _function_tuple_codes(path: str, name: str) -> set[str]:
    tree = _parse(ROOT / path)
    constants = _string_constants()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            codes = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Tuple) and sub.elts:
                    head = sub.elts[0]
                    if isinstance(head, ast.Constant) and isinstance(head.value, str) and CODE_RE.match(head.value):
                        codes.add(head.value)
                    elif isinstance(head, ast.Name) and head.id in constants:
                        codes |= {v for v in constants[head.id] if CODE_RE.match(v)}
            return codes
    raise SystemExit(f"{path} に関数 {name} がない")


def illegal_codes() -> tuple[dict[str, list[str]], list[str]]:
    """IllegalActionError のコード → 出どころ（ファイル:行）と、表にない動的な呼び出し箇所。"""
    constants = _string_constants()
    codes: dict[str, list[str]] = {}
    unknown: list[str] = []
    used_dynamic = set()
    for path in sorted(ENGINE.rglob("*.py")):
        tree = _parse(path)
        parents: dict[ast.AST, ast.AST] = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
            if name != "IllegalActionError" or not node.args:
                continue
            where = f"{rel(path)}:{node.lineno}"
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                codes.setdefault(arg.value, []).append(where)
                continue
            key_name = arg.id if isinstance(arg, ast.Name) else arg.attr if isinstance(arg, ast.Attribute) else None
            if key_name is not None and key_name.isupper() and key_name in constants and len(constants[key_name]) == 1:
                codes.setdefault(next(iter(constants[key_name])), []).append(where)
                continue
            scope = node
            while scope in parents and not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scope = parents[scope]
            function = scope.name if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)) else ""
            key = (rel(path), function, ast.unparse(arg) if not isinstance(arg, ast.Starred) else "*" + ast.unparse(arg.value))
            entry = DYNAMIC_SITES.get(key)
            if entry is None:
                unknown.append(f"{where}（{function}・{key[2]}）")
                continue
            used_dynamic.add(key)
            if entry[0] == "from_function":
                produced = _function_tuple_codes(entry[1], entry[2])
                for excluded in (entry[3] if len(entry) > 3 else ()):
                    values = constants.get(excluded, set())
                    if not values or not values <= produced:
                        unknown.append(f"{where}: 除くコードの定数 {excluded} が {entry[2]} のタプルにない（表を直す）")
                    produced -= values
            else:
                produced = set(entry)
            for code in produced:
                codes.setdefault(code, []).append(where)
    for key in DYNAMIC_SITES:
        if key not in used_dynamic:
            unknown.append(f"動的な呼び出し箇所の表の {key} が、ソースにない（表を直す）")
    return codes, unknown


def build() -> tuple[dict, list[str]]:
    problems: list[str] = []
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    records = json.loads(RECORDS.read_text(encoding="utf-8"))
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    compatibility = set(spec["compatibility_codes"])
    scenes = {code: sorted(ids) for code, ids in records["scene_index"]["codes"].items()}
    entries: dict[str, dict] = {}

    def add(code, category, raised_as, origin, basis):
        if code in entries:
            old = entries[code]
            if old["category"] != category:
                problems.append(f"コード {code} の分類が 2 つ（{old['category']}・{category}）")
            old["raised_as"] = sorted(set(old["raised_as"]) | set(raised_as))
            old["origins"] = sorted(set(old["origins"]) | {origin})
            return
        found = scenes.get(code, [])
        entries[code] = {"category": category, "raised_as": sorted(raised_as), "origins": [origin], "basis": basis, "scenes": found,
                         "case": found[0] if len(found) == 1 else None, "case_status": ("identified" if len(found) == 1 else "not_identified") if found else "not_applicable",
                         "text": CODE_TEXTS.get(code, CATEGORY_TEXTS[category]), "text_source": "code" if code in CODE_TEXTS else "category"}

    for e in ledger["entries"]:
        if e["entry_kind"] not in ("research_stop_code", "runtime_stop_code") or e["status"] != "active":
            continue
        mechanisms = {m["mechanism"] for m in e.get("current_stop") or []}
        if mechanisms and mechanisms <= {"not_raised", "deck_validation"}:
            continue
        code, cls = e["id"], e.get("classification")
        if code in compatibility:
            category = "compatibility"
        elif cls == "C":
            category = "unresolved_ruling"
        elif cls == "B":
            category = "technical_limit"
        elif cls == "A":
            category = "unsupported"
        elif code in LEDGER_E_CODES:
            category = LEDGER_E_CODES[code][0]
        elif code in LEDGER_E_EXCLUDED:
            continue
        else:
            problems.append(f"台帳のコード {code} の分類 {cls} を、診断の分類に対応させていない（LEDGER_E_CODES に理由つきで書く）")
            continue
        add(code, category, ("unsupported",), "stop_ledger", f"台帳 {e['entry_kind']}・分類 {cls}")
    for code in compatibility:
        if code not in entries:
            problems.append(f"互換性のコード {code} が台帳の有効な停止コードにない")

    illegal, unknown = illegal_codes()
    problems += [f"IllegalActionError の動的な呼び出し箇所が表にない: {u}" for u in unknown]
    for code, sites in sorted(illegal.items()):
        if not CODE_RE.match(code):
            problems.append(f"IllegalActionError のコード {code!r} の形が正しくない（{sites[0]}）")
            continue
        add(code, "invalid_input", ("illegal",), "engine_illegal", "IllegalActionError の呼び出し（" + str(len(sites)) + " か所）")
    for code, (category, raised_as, basis) in FIXED_CODES.items():
        add(code, category, raised_as, "engine_fixed", basis)
    for code in CODE_TEXTS:
        if code not in entries:
            problems.append(f"個別の文のコード {code} がコード表にない")

    catalog = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": "scripts/build_diagnostic_catalog.py",
        "note": ("エンジンが返す元のコード → 診断の分類・事例・安全な定型文。停止の方針の台帳の停止コードと、台帳の外のコード（不正な操作・状態の不整合・デッキの検査・規約集合の構成）を"
                 "合わせた表で、台帳には加えない。表にないコードは診断の対応漏れ（unmapped）で、接頭辞から推測で分類しない"),
        "category_texts": CATEGORY_TEXTS,
        "subkind_texts": SUBKIND_TEXTS,
        "halt_texts": HALT_TEXTS,
        "codes": dict(sorted(entries.items())),
    }
    return catalog, problems


def dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    catalog, problems = build()
    if args.write:
        if problems:
            print("\n".join(problems))
            return 1
        OUTPUT.write_text(dump(catalog), encoding="utf-8", newline="\n")
        print(f"書いた: {len(catalog['codes'])} コード")
        return 0
    if not OUTPUT.exists():
        problems.append("コード表がない（--write で作る）")
    elif OUTPUT.read_text(encoding="utf-8") != dump(catalog):
        problems.append("書いたコード表が、作り直したものと違う（--write で作り直す）")
    print("\n".join(problems) if problems else "problems=0")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

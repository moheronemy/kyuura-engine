"""状態スナップショット（U6。docs/state-snapshot-v0.157.md・仕様 docs/state-snapshot-design.md）。

信頼されたホスト・検証者が、対戦の状態の全体（山札・サイドの並び・乱数の状態・seed・決定の続き）を JSON に保存し、同じ実装・依存データ・規約集合で復元する。
閲覧用記録（U5）・観測とは別の、完全な情報を持つホスト用の形式（``kyuura_snapshot_format``）。見る人に渡さない。

責任の分け方:

- ``save_snapshot``（書き出し）: 安定した状態だけを保存する。保存の境界・登録・型の表現のどれかを満たさなければ ``SnapshotSaveError``（部分的な結果を返さない）。状態・乱数・ログを変えない
- ``dumps_snapshot``・``loads_snapshot``（JSON）: 書き出しの文字列と、安全な読み取り（``replay_record.read_json_object``。大きさ・深さ・重なった鍵・NaN を拒む）
- ``restore_snapshot``（復元）: 7 つの段（読み取り → 形式と型 → 対応 → 登録データの解決 → 組み立て → 整合 → 返す）。不正な入力で例外を投げず、``RestoreReport`` を返す
- ``RestoreReport``（結果の検査）: ``status`` は restored・read_error・malformed・unsupported・inconsistent・internal_error の 1 つ。``state`` は restored のときだけ
- ``RestoredGame``（ホストへの接続）: 復元に成功した状態だけから、既存の操作アダプタ（``adapter.HostedGame``）で続ける入口。完全な再現用記録は持たない

カード定義・効果の登録表・ルールの組・規約集合は、識別から登録済みのもの（既定のカードプール・``replay_record.KNOWN_RULES``・``conventions.registered_identity``）を解決する。
入力の型の名前からクラスを読み込まない（``state.py`` の dataclass の許した一覧だけ）。pickle・``GameState.__setstate__`` を使わない。知らない値・欠けた項目を既定の値で補わない。

例外の扱い（``adapter`` と同じ）: 復元の中の想定外の例外は ``internal_error``（ほかの結果に変えない。traceback は検証者用）。``MemoryError`` と、``Exception`` の子でない終了
（``KeyboardInterrupt``・``SystemExit`` など）は捕まえない。保存の中の想定外の例外は、そのまま呼び出し元へ伝わる（保存できない状態とは別）。
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import random
import traceback as _traceback
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from . import diagnostics as D
from . import state as _state_module
from .adapter import CommandResult, HostedGame
from .cards import EnergyType, load_card_pool
from .conventions import (
    ConventionSetError,
    ConventionSetIdentity,
    registered_identity,
    state_conventions,
)
from .engine import check_invariants, supported_decision_error
from .observation import observe
from .replay_record import (
    CHECK_METHODS,
    CONNECTION_CHECK_METHOD,
    IDENTITY_METHOD,
    KNOWN_RULES,
    MAX_DEPTH,
    MAX_RECORD_BYTES,
    STATE_EXPORT_FORMAT,
    Problem,
    RecordFormatError,
    checks,
    current_identity,
    git_commit,
    read_json_object,
    runtime_identity,
)
from .rng import RNG_FORMAT
from .state import CardInstance, GameState, Phase, freeze_mapping
from .view_record import ViewRecord, ViewRecorder

SNAPSHOT_FORMAT = 1
SUPPORTED_SNAPSHOT_FORMATS = (1,)
FORMAT_KEY = "kyuura_snapshot_format"
CARD_POOL_DEFAULT = "default"

# 復元の結果（docs/state-snapshot-design.md 7 章）
RESTORED = "restored"
READ_ERROR = "read_error"
MALFORMED = "malformed"
NOT_SUPPORTED = "unsupported"
INCONSISTENT = "inconsistent"
INTERNAL_ERROR = "internal_error"
RESULTS = (RESTORED, READ_ERROR, MALFORMED, NOT_SUPPORTED, INCONSISTENT, INTERNAL_ERROR)
RESULT_TEXTS = MappingProxyType({
    RESTORED: "スナップショットから状態を復元した",
    READ_ERROR: "スナップショットを JSON として読めない",
    MALFORMED: "スナップショットの形式・型・項目が正しくない",
    NOT_SUPPORTED: "このスナップショットは、この実装・環境・依存データ・規約集合では扱えない",
    INCONSISTENT: "スナップショットの状態が整合しない",
    INTERNAL_ERROR: "復元の処理の中で内部エラーが起きた",
})

# 保存できない理由の種類
SAVE_BOUNDARY = "boundary"  # 保存の境界の外（pending_moves・一時的な属性・不変条件・構造）
SAVE_NOT_SUPPORTED = "unsupported"  # 登録・規約集合・再開先・カードプールがこの版の対応の外
SAVE_UNREPRESENTABLE = "unrepresentable"  # 型の対応表で表せない値・上限を超える
SAVE_CODES = MappingProxyType({
    "not_game_state": SAVE_BOUNDARY,
    "pending_moves": SAVE_BOUNDARY,
    "transient_attribute": SAVE_BOUNDARY,
    "missing_attribute": SAVE_BOUNDARY,
    "invariants": SAVE_BOUNDARY,
    "structure": SAVE_BOUNDARY,
    "conventions": SAVE_NOT_SUPPORTED,
    "decision_resume": SAVE_NOT_SUPPORTED,
    "rules": SAVE_NOT_SUPPORTED,
    "card_pool": SAVE_NOT_SUPPORTED,
    "effects": SAVE_NOT_SUPPORTED,
    "unrepresentable_value": SAVE_UNREPRESENTABLE,
    "too_deep": SAVE_UNREPRESENTABLE,
    "too_large": SAVE_UNREPRESENTABLE,
})

HEADER_REQUIRED = (FORMAT_KEY, "engine", "runtime", "dependencies", "convention_set", "formats", "check", "state")
HEADER_OPTIONAL = ("origin", "label", "git_commit")
ORIGIN_KEYS = frozenset({"game_id", "seq"})  # DS-RECORD-LINK: 完全な再現用記録との対応は任意の補助情報（復元には使わない）
MAX_LABEL = 200


class SnapshotSaveError(Exception):
    """状態を保存できない（``code``・``kind``・``path``）。文に状態の値・カード・seed を入れない。部分的な結果は作らない。"""

    def __init__(self, code: str, path: str = "$"):
        super().__init__(f"状態を保存できない: {code}（{path}）")
        self.code = code
        self.kind = SAVE_CODES[code]
        self.path = path


class SnapshotNotRestoredError(Exception):
    """復元に成功していない結果から、ホストの対戦を作ろうとした（使い方の誤り）。"""


# ---------------------------------------------------------------- 型の対応表（S1）
#
# state.py の dataclass の項目の注釈（文字列）を、決まった形の型の式に読みかえる。読みかえられる形は下の _parse が知っているものだけで、知らない形は対応表の漏れとして
# codec_problems が見つける（保存も拒む）。入力の型の名前は _RECORDS（state.py の dataclass の許した一覧）だけから引く。

def _records() -> dict[str, type]:
    return {name: value for name, value in vars(_state_module).items()
            if isinstance(value, type) and dataclasses.is_dataclass(value) and value.__module__ == _state_module.__name__ and value.__name__ == name
            and name != "GameState"}


_RECORDS: dict[str, type] = _records()
_RECORD_NAMES = {cls: name for name, cls in _RECORDS.items()}
_ENUMS: dict[str, type] = {"Phase": Phase, "EnergyType": EnergyType}
_ENUM_NAMES = {cls: name for name, cls in _ENUMS.items()}

# 注釈と実際の正当な値が合わない項目の、型の対応表の訂正（注釈より広げない。理由を書く。tests/test_state_snapshot_v0_157.py の監査の記録）
HINT_OVERRIDES = MappingProxyType({
    # v0.49（ばける）から、のせたカードの特殊能力の記録は (場のポケモンの番号, 特殊能力の位置, そのカードの uid) の 3 つ（effects.power_use_record）。注釈は 2 つのまま
    ("GameState", "power_uses_this_turn"): "tuple[tuple[int, int] | tuple[int, int, int], ...]",
})

# GameState の項目のうち、値でなく識別で保存するもの（resolve）と、保存しないもの（absent）。ほかは値（value）
RESOLVED_FIELDS = ("rules", "definitions", "effects", "conventions")
ABSENT_FIELDS = ("pending_moves",)
# GameState の項目のうち、注釈の形のほかに決めた方法で保存する値
SPECIAL_VALUE_FIELDS = ("rng", "cards")


def _split(text: str, sep: str) -> list[str]:
    parts, depth, current = [], 0, ""
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if depth == 0 and text.startswith(sep, i):
            parts.append(current.strip())
            current = ""
            i += len(sep)
            continue
        current += ch
        i += 1
    parts.append(current.strip())
    return parts


class _CodecGap(Exception):
    """対応表で読みかえられない注釈（対応表の漏れ）。"""


def _parse(text: str):
    """注釈の文字列を型の式にする。式: ("int",) ("str",) ("bool",) ("none",) ("any",) ("enum", cls) ("record", (cls, ...)) ("list", t) ("tuple", t) ("fixed", (t, ...))
    ("event",) ("union", (t, ...))。"""
    text = text.strip()
    union = _split(text, "|")
    if len(union) > 1:
        members = tuple(_parse(part) for part in union)
        records = tuple(cls for m in members if m[0] == "record" for cls in m[1])
        others = tuple(m for m in members if m[0] != "record")
        if records and all(m == ("none",) for m in others):
            return ("union", (("record", records),) + others)
        return ("union", members)
    simple = {"int": ("int",), "str": ("str",), "bool": ("bool",), "None": ("none",), "Any": ("any",)}
    if text in simple:
        return simple[text]
    if text in _ENUMS:
        return ("enum", _ENUMS[text])
    if text in _RECORDS:
        return ("record", (_RECORDS[text],))
    if text.endswith("]") and "[" in text:
        head, inner = text[:-1].split("[", 1)
        args = _split(inner, ",")
        if head == "list" and len(args) == 1:
            return ("list", _parse(args[0]))
        if head == "tuple" and len(args) == 2 and args[1] == "...":
            return ("tuple", _parse(args[0]))
        if head == "tuple" and "..." not in args:
            return ("fixed", tuple(_parse(a) for a in args))
        if head == "Mapping" and args == ["str", "Any"]:
            return ("event",)
    raise _CodecGap(text)


def _annotation(owner: str, f: dataclasses.Field) -> str:
    return HINT_OVERRIDES.get((owner, f.name), f.type if isinstance(f.type, str) else f.type.__name__)


def _field_types(cls: type) -> dict[str, Any]:
    return {f.name: _parse(_annotation(cls.__name__, f)) for f in dataclasses.fields(cls)}


def _build_codec() -> tuple[dict[str, dict[str, Any]], list[str]]:
    """state.py の今の dataclass から型の対応表を作る（読み込みのときに 1 回。テストは型を加えた代わりの値で呼び、漏れを見つけることを確かめる）。"""
    table: dict[str, dict[str, Any]] = {}
    gaps: list[str] = []
    for name, cls in sorted(_records().items()):
        try:
            table[name] = _field_types(cls)
        except _CodecGap:
            gaps.append(f"{name} の項目の注釈を、型の対応表で読みかえられない")
    state_fields = {}
    for f in dataclasses.fields(GameState):
        if f.name in RESOLVED_FIELDS or f.name in ABSENT_FIELDS or f.name in SPECIAL_VALUE_FIELDS:
            continue
        try:
            state_fields[f.name] = _parse(_annotation("GameState", f))
        except _CodecGap:
            gaps.append(f"GameState.{f.name} の注釈を、型の対応表で読みかえられない")
    table["GameState"] = state_fields
    return table, gaps


_CODEC, _CODEC_GAPS = _build_codec()


def codec_fields() -> dict[str, dict[str, str]]:
    """型の対応表が扱う型・項目と、その扱い（value・resolve・absent）。仕様の分類表と名前で照らすのに使う（scripts/build_state_snapshot_design.py）。"""
    out = {name: dict.fromkeys(fields, "value") for name, fields in _CODEC.items() if name != "GameState"}
    out["GameState"] = {f.name: ("resolve" if f.name in RESOLVED_FIELDS else "absent" if f.name in ABSENT_FIELDS else "value") for f in dataclasses.fields(GameState)}
    return out


def codec_problems() -> list[str]:
    """型の対応表の漏れ（読みかえられない注釈・扱いの決まっていない GameState の項目）。空でなければ保存を拒む。"""
    problems = list(_CODEC_GAPS)
    names = {f.name for f in dataclasses.fields(GameState)}
    handled = set(_CODEC["GameState"]) | set(RESOLVED_FIELDS) | set(ABSENT_FIELDS) | set(SPECIAL_VALUE_FIELDS)
    problems += [f"GameState.{n} の扱いが型の対応表にない" for n in sorted(names - handled)]
    problems += [f"型の対応表の GameState.{n} がコードにない" for n in sorted(handled - names)]
    owners = {**_records(), "GameState": GameState}
    for owner, name in HINT_OVERRIDES:
        if owner not in owners or name not in {f.name for f in dataclasses.fields(owners[owner])}:
            problems.append(f"型の対応表の訂正 {owner}.{name} がコードにない")
    return problems


# ---------------------------------------------------------------- 書き出し（S1）


class _Unrepresentable(Exception):
    def __init__(self, path: str):
        super().__init__(path)
        self.path = path


def _is_int(value) -> bool:
    return type(value) is int


def _encode(value, t, path: str):
    kind = t[0]
    if kind == "int":
        if not _is_int(value):
            raise _Unrepresentable(path)
        return value
    if kind == "str":
        if type(value) is not str:
            raise _Unrepresentable(path)
        return value
    if kind == "bool":
        if type(value) is not bool:
            raise _Unrepresentable(path)
        return value
    if kind == "none":
        if value is not None:
            raise _Unrepresentable(path)
        return None
    if kind == "enum":
        if type(value) is not t[1]:
            raise _Unrepresentable(path)
        return value.value
    if kind == "record":
        if type(value) not in t[1]:
            raise _Unrepresentable(path)
        return _encode_record(value, path)
    if kind == "list":
        if type(value) is not list:
            raise _Unrepresentable(path)
        return [_encode(v, t[1], f"{path}[{i}]") for i, v in enumerate(value)]
    if kind == "tuple":
        if type(value) is not tuple:
            raise _Unrepresentable(path)
        return [_encode(v, t[1], f"{path}[{i}]") for i, v in enumerate(value)]
    if kind == "fixed":
        if type(value) is not tuple or len(value) != len(t[1]):
            raise _Unrepresentable(path)
        return [_encode(v, s, f"{path}[{i}]") for i, (v, s) in enumerate(zip(value, t[1], strict=True))]
    if kind == "event":
        if type(value) is not MappingProxyType or not all(type(k) is str for k in value):
            raise _Unrepresentable(path)
        return {k: _encode_any(v, f"{path}.{k}") for k, v in value.items()}
    if kind == "union":
        for member in t[1]:
            if _matches(value, member):
                return _encode(value, member, path)
        raise _Unrepresentable(path)
    if kind == "any":
        return _encode_any(value, path)
    raise _Unrepresentable(path)


def _matches(value, t) -> bool:
    kind = t[0]
    if kind == "none":
        return value is None
    if kind == "record":
        return type(value) in t[1]
    if kind == "int":
        return _is_int(value)
    if kind == "str":
        return type(value) is str
    if kind == "bool":
        return type(value) is bool
    if kind == "enum":
        return type(value) is t[1]
    if kind == "tuple":
        return type(value) is tuple
    if kind == "fixed":
        return type(value) is tuple and len(value) == len(t[1])
    if kind == "list":
        return type(value) is list
    return False


def _encode_record(value, path: str) -> dict[str, Any]:
    name = _RECORD_NAMES[type(value)]
    fields = _CODEC[name]
    return {"type": name, "fields": {n: _encode(getattr(value, n), t, f"{path}.{n}") for n, t in fields.items()}}


def _encode_any(value, path: str):
    """注釈が Any の位置（ログのイベントの値・決定の context の値・持続する効果・履歴）。JSON の配列はタプル、型の印つきのオブジェクトは値の記録か列挙。"""
    t = type(value)
    if value is None or t in (bool, int, str):
        return value
    if t is tuple:
        return [_encode_any(v, f"{path}[{i}]") for i, v in enumerate(value)]
    if t in _RECORD_NAMES:
        return _encode_record(value, path)
    if t in _ENUM_NAMES:
        return {"enum": _ENUM_NAMES[t], "value": value.value}
    raise _Unrepresentable(path)


def _encode_state(state: GameState) -> dict[str, Any]:
    """GameState の項目を、分類表の順（dataclass の項目の順）に JSON の値にする。境界・登録の確かめはしない（``save_snapshot`` が先に確かめる）。"""
    out: dict[str, Any] = {}
    for f in dataclasses.fields(GameState):
        name = f.name
        value = getattr(state, name)
        path = f"$.state.{name}"
        if name in ABSENT_FIELDS:
            continue
        if name == "rules":
            out[name] = value.id
        elif name == "definitions":
            out[name] = list(value)
        elif name == "effects":
            out[name] = value.id
        elif name == "conventions":
            out[name] = value.record()
        elif name == "rng":
            version, internal, gauss_next = value.getstate()
            if gauss_next is not None:  # エンジンは gauss を使わない。浮動小数は表さない
                raise _Unrepresentable(path)
            out[name] = {"format": RNG_FORMAT, "version": version, "internal": list(internal), "gauss_next": None}
        elif name == "cards":
            if type(value) is not MappingProxyType:
                raise _Unrepresentable(path)
            out[name] = [_encode(card, ("record", (CardInstance,)), f"{path}[{i}]") for i, card in enumerate(value.values())]
        else:
            out[name] = _encode(value, _CODEC["GameState"][name], path)
    return out


def _depth(value) -> int:
    """JSON の値の入れ子の深さ（replay_record.read_json_object と同じ数え方。最上位の辞書が 1）。"""
    deepest = 0
    stack = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        deepest = max(deepest, depth)
        if isinstance(item, dict):
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            stack.extend((v, depth + 1) for v in item)
    return deepest


def _boundary_problem(state: GameState) -> SnapshotSaveError | None:
    """保存の境界の確かめ（docs/state-snapshot-design.md 5 章）。状態・乱数・ログを変えない。最初に見つけた 1 つを返す。"""
    if type(state) is not GameState:
        return SnapshotSaveError("not_game_state")
    names = {f.name for f in dataclasses.fields(GameState)}
    if set(vars(state)) - names:
        return SnapshotSaveError("transient_attribute")
    if names - set(vars(state)):
        return SnapshotSaveError("missing_attribute")
    if state.pending_moves != () or type(state.pending_moves) is not tuple:
        return SnapshotSaveError("pending_moves", "$.state.pending_moves")
    identity, _ = state_conventions(state)
    if not isinstance(state.conventions, ConventionSetIdentity) or identity is None:
        return SnapshotSaveError("conventions", "$.state.conventions")  # 記録のない旧状態（UNRECORDED）・登録と違う識別
    if supported_decision_error(state) is not None:
        return SnapshotSaveError("decision_resume", "$.state.decision.resume")
    if KNOWN_RULES.get(getattr(state.rules, "id", None)) != state.rules:
        return SnapshotSaveError("rules", "$.state.rules")
    pool = load_card_pool()
    if state.effects is not pool.effects:
        return SnapshotSaveError("effects", "$.state.effects")
    source = pool.source
    if (type(state.card_data) is not _state_module.DataSource
            or (state.card_data.repository, state.card_data.commit, state.card_data.path) != (source["repository"], source["commit"], source["path"])):
        return SnapshotSaveError("card_pool", "$.state.card_data")
    for card_id, definition in state.definitions.items():
        if card_id not in pool.definitions or pool.get(card_id) != definition:
            return SnapshotSaveError("card_pool", "$.state.definitions")
    if check_invariants(state):
        return SnapshotSaveError("invariants")
    if structure_problems(state):
        return SnapshotSaveError("structure")
    return None


def structure_problems(state: GameState) -> list[str]:
    """スナップショットの整合の確かめのうち、check_invariants が見ないもの（保存の前と復元のあとに同じものを使う）。値を文に入れない（場所の名前だけ）。"""
    problems: list[str] = []
    if type(state.cards) is not MappingProxyType or any(type(card) is not CardInstance or card.uid != uid for uid, card in state.cards.items()):
        problems.append("cards の鍵と CardInstance.uid")
    used = {card.card_id for card in state.cards.values()}
    if set(state.definitions) != used:
        problems.append("definitions と cards の card_id の集まり")
    if type(state.players) is not list or len(state.players) != 2:
        problems.append("players")
    d = state.decision
    if d is not None and not (_is_int(d.id) and _is_int(state.next_decision_id) and 0 < d.id < state.next_decision_id):
        problems.append("decision.id と next_decision_id")
    ids = [p.pokemon_id for player in state.players if hasattr(player, "in_play") for p in player.in_play()]
    if len(set(ids)) != len(ids) or any(not (_is_int(i) and 0 < i < state.next_pokemon_id) for i in ids):
        problems.append("場のポケモンの番号と next_pokemon_id")
    if any(getattr(segment, "index", None) != i for i, segment in enumerate(state.segments)):
        problems.append("segments の番号")
    return problems


@dataclass(frozen=True)
class StateSnapshot:
    """保存した状態（ホスト・検証者用。見る人に渡さない）。repr に秘密の値を出さない。``data`` は写しを返す。"""

    _data: dict[str, Any] = dataclasses.field(repr=False)

    @property
    def data(self) -> dict[str, Any]:
        return json.loads(json.dumps(self._data, ensure_ascii=False))

    def __repr__(self) -> str:
        check = self._data.get("check") or {}
        return f"StateSnapshot(format={self._data.get(FORMAT_KEY)!r}, status={check.get('status')!r})"

    __str__ = __repr__


def _text(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"


def state_items(state: GameState) -> dict[str, Any]:
    """保存の境界・登録・型の対応を確かめて、状態の保存する全項目を JSON の値にする（スナップショットの ``state`` と同じ値。v0.158 で ``save_snapshot`` から分けた）。
    保存できなければ ``SnapshotSaveError``。状態を変えない。"""
    if codec_problems():
        raise SnapshotSaveError("unrepresentable_value")
    error = _boundary_problem(state)
    if error is not None:
        raise error
    try:
        return _encode_state(state)
    except _Unrepresentable as gap:
        raise SnapshotSaveError("unrepresentable_value", gap.path) from None


def connection_check(state: GameState) -> str:
    """接続用確認値（v0.158。U6-S5。方式 ``replay_record.CONNECTION_CHECK_METHOD``）。

    対象は、スナップショットが保存する意味のある全項目（``state_items``。登録データ・依存の識別 rules・definitions・effects・conventions・card_data を含む）と、
    カードプールの識別（default）。項目の順は保存の順（dataclass の項目の順・ログのイベントの鍵の順）のまま、鍵を並べかえずに sha256 を取る（型は型の対応表が決めた形で、
    タプルとリスト・値の記録の型の印・列挙を区別する）。
    除くもの: スナップショットの ``check``（状態から求める値で、自分を含む確認値にしない）・実装と環境の識別（照合値でなく対応の確かめで扱う）・``origin``・``label``・``git_commit``
    （補助の情報）・``pending_moves``（保存の境界で空）。

    内容を見分けるための値で、署名・出所の認証・過去に実際に作られたことの証明ではない。保存できない状態では ``SnapshotSaveError``。"""
    payload = {"method": CONNECTION_CHECK_METHOD, "card_pool": CARD_POOL_DEFAULT, "state": state_items(state)}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def save_snapshot(state: GameState, *, origin: dict[str, Any] | None = None, label: str | None = None, include_git: bool = False) -> StateSnapshot:
    """安定した状態を保存する（書き出し。S1）。保存できなければ ``SnapshotSaveError``。渡した状態・乱数・ログは変えない。

    ``origin`` は完全な再現用記録との対応の補助情報（``game_id``・``seq``。DS-RECORD-LINK。復元には使わない）、``label`` はホストの説明。どちらも確かめない説明用で、
    ここに秘密の値を書かないのはホストの責任。"""
    encoded = state_items(state)
    if origin is not None and not _origin_ok(origin):
        raise ValueError("origin は game_id（文字列）・seq（0 以上の整数）だけを持つ辞書")
    if label is not None and not (type(label) is str and len(label) <= MAX_LABEL):
        raise ValueError(f"label は {MAX_LABEL} 文字までの文字列")
    pool = load_card_pool()
    data: dict[str, Any] = {
        FORMAT_KEY: SNAPSHOT_FORMAT,
        "engine": current_identity(),
        "runtime": runtime_identity(),
        "dependencies": {"rules": state.rules.id, "card_pool": CARD_POOL_DEFAULT,
                         "card_data": {"repository": pool.source["repository"], "commit": pool.source["commit"], "path": pool.source["path"]},
                         "effects": pool.effects.id},
        "convention_set": state.conventions.record(),
        "formats": _formats(),
        "check": checks(state),
        "state": encoded,
    }
    if origin is not None:
        data["origin"] = dict(origin)
    if label is not None:
        data["label"] = label
    if include_git:
        data["git_commit"] = git_commit()
    if _depth(data) > MAX_DEPTH:
        raise SnapshotSaveError("too_deep")
    text = _text(data)
    if len(text.encode("utf-8")) > MAX_RECORD_BYTES:
        raise SnapshotSaveError("too_large")
    return StateSnapshot(json.loads(text))


def _formats() -> dict[str, Any]:
    return {"state_export": STATE_EXPORT_FORMAT, "check_methods": dict(CHECK_METHODS), "diagnostic_schema": D.DIAGNOSTIC_SCHEMA, "rng": RNG_FORMAT}


def _origin_ok(origin) -> bool:
    if type(origin) is not dict or not set(origin) <= ORIGIN_KEYS:
        return False
    if "game_id" in origin and type(origin["game_id"]) is not str:
        return False
    return "seq" not in origin or (_is_int(origin["seq"]) and origin["seq"] >= 0)


def dumps_snapshot(snapshot: StateSnapshot) -> str:
    """スナップショットの JSON の文字列（鍵の順は保存した順。ログのイベントの鍵の順を保つため並べかえない）。"""
    return _text(snapshot._data)


def loads_snapshot(text: str | bytes) -> StateSnapshot:
    """安全な読み取り（段 1）。読めなければ ``replay_record.RecordFormatError``（入力の値を文に入れない）。中身の確かめと復元は ``restore_snapshot``。"""
    return StateSnapshot(read_json_object(text))


# ---------------------------------------------------------------- 復元（S2・S3）


@dataclass(frozen=True)
class RestoreReport:
    """復元の結果（ホスト・検証者用）。``state`` は restored のときだけ（ほかの結果では部分的な状態も返さない）。``problems`` は (種類, コード, JSON の経路) で、入力の値を持たない。
    ``traceback``・``exception_type`` は internal_error のときの検証者用の記録。"""

    status: str
    problems: tuple[Problem, ...]
    state: GameState | None = dataclasses.field(default=None, repr=False)
    game_status: str | None = None
    exception_type: str | None = dataclasses.field(default=None, repr=False)
    traceback: str | None = dataclasses.field(default=None, repr=False)

    @property
    def restored(self) -> bool:
        return self.status == RESTORED

    @property
    def message(self) -> str:
        return RESULT_TEXTS[self.status]


class _Stop(Exception):
    def __init__(self, status: str, problems: list[Problem]):
        super().__init__(status)
        self.status = status
        self.problems = problems


def _stop(status: str, code: str, path: str = "$"):
    raise _Stop(status, [Problem(status, code, path)])


def restore_snapshot(snapshot: StateSnapshot | str | bytes) -> RestoreReport:
    """スナップショットから状態を復元する（段 1〜7）。不正・非対応・不整合の入力では例外を投げず、結果の種類と問題の場所を返す。
    ``StateSnapshot`` か JSON の文字列（str・bytes）でなければ ``TypeError``（使い方の誤り）。"""
    if not isinstance(snapshot, (StateSnapshot, str, bytes)):
        raise TypeError("restore_snapshot には StateSnapshot か JSON の文字列を渡す")
    try:
        return _restore(snapshot)
    except Exception as error:  # 復元の境界: 想定外の例外は内部エラーの結果にする（ほかの結果に変えない。元の例外は検証者用の記録に残す）
        if isinstance(error, MemoryError):  # 資源の不足は内部エラーの結果にしない（adapter と同じ）
            raise
        return RestoreReport(status=INTERNAL_ERROR, problems=(Problem(INTERNAL_ERROR, "internal_error", "$"),), exception_type=type(error).__name__,
                             traceback="".join(_traceback.format_exception(error)))


def _restore(snapshot) -> RestoreReport:
    # 段 1: 安全な JSON の読み取り
    if isinstance(snapshot, StateSnapshot):
        data = snapshot.data
    else:
        try:
            data = read_json_object(snapshot)
        except RecordFormatError as error:
            return RestoreReport(status=READ_ERROR, problems=(Problem(READ_ERROR, error.code, error.path),))
    try:
        _check_header(data)  # 段 2
        _check_support(data)  # 段 3
        resolved = _resolve(data)  # 段 4
        state = _assemble(data["state"], resolved)  # 段 5
        _check_restored(state, data)  # 段 6
    except _Stop as stop:
        return RestoreReport(status=stop.status, problems=tuple(stop.problems))
    return RestoreReport(status=RESTORED, problems=(), state=state, game_status=D.status_of(state))  # 段 7


# 段 2: 形式・型・必須の項目（見出し。状態の項目の型は段 5 で読む）


def _require(cond: bool, code: str, path: str) -> None:
    if not cond:
        _stop(MALFORMED, code, path)


def _is_hex64(value) -> bool:
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _keys(value, required, optional, path: str) -> None:
    _require(type(value) is dict, "not_object", path)
    missing = [k for k in required if k not in value]
    unknown = [k for k in value if k not in required and k not in optional]
    if missing:
        _stop(MALFORMED, "missing_field", f"{path}.{missing[0]}")
    if unknown:
        _stop(MALFORMED, "unknown_field", path)


def _check_header(data: dict[str, Any]) -> None:
    version = data.get(FORMAT_KEY)
    _require(_is_int(version), "format_version", f"$.{FORMAT_KEY}")
    if version not in SUPPORTED_SNAPSHOT_FORMATS:
        _stop(NOT_SUPPORTED, "format_version", f"$.{FORMAT_KEY}")
    _keys(data, HEADER_REQUIRED, HEADER_OPTIONAL, "$")
    engine = data["engine"]
    _keys(engine, ("version", "method", "behavior_digest", "behavior_files", "instrumentation_digest", "instrumentation_files"), (), "$.engine")
    _require(type(engine["version"]) is str and type(engine["method"]) is str and _is_hex64(engine["behavior_digest"]) and _is_hex64(engine["instrumentation_digest"])
             and _is_int(engine["behavior_files"]) and _is_int(engine["instrumentation_files"]), "engine", "$.engine")
    runtime = data["runtime"]
    _keys(runtime, ("python_implementation", "python_version", "rng"), (), "$.runtime")
    _require(type(runtime["python_implementation"]) is str and type(runtime["python_version"]) is list and len(runtime["python_version"]) == 3
             and all(_is_int(v) for v in runtime["python_version"]), "runtime", "$.runtime")
    _keys(runtime["rng"], ("format", "state_version"), (), "$.runtime.rng")
    _require(type(runtime["rng"]["format"]) is str and _is_int(runtime["rng"]["state_version"]), "runtime", "$.runtime.rng")
    deps = data["dependencies"]
    _keys(deps, ("rules", "card_pool", "card_data", "effects"), (), "$.dependencies")
    _keys(deps["card_data"], ("repository", "commit", "path"), (), "$.dependencies.card_data")
    _require(all(type(deps[k]) is str for k in ("rules", "card_pool", "effects")) and all(type(v) is str for v in deps["card_data"].values()),
             "dependencies", "$.dependencies")
    _check_convention_record(data["convention_set"], "$.convention_set")
    formats = data["formats"]
    _keys(formats, ("state_export", "check_methods", "diagnostic_schema", "rng"), (), "$.formats")
    _require(_is_int(formats["state_export"]) and _is_int(formats["diagnostic_schema"]) and type(formats["rng"]) is str and type(formats["check_methods"]) is dict
             and all(type(v) is str for v in formats["check_methods"].values()), "formats", "$.formats")
    _check_check(data["check"])
    _require(type(data["state"]) is dict, "not_object", "$.state")
    if "origin" in data:
        _require(_origin_ok(data["origin"]), "origin", "$.origin")
    if "label" in data:
        _require(type(data["label"]) is str and len(data["label"]) <= MAX_LABEL, "label", "$.label")
    if "git_commit" in data:
        _require(data["git_commit"] is None or type(data["git_commit"]) is str, "git_commit", "$.git_commit")


def _check_convention_record(value, path: str) -> None:
    _keys(value, ("id", "version", "digest", "usage", "completeness", "members"), (), path)
    _require(type(value["id"]) is str and _is_int(value["version"]) and type(value["digest"]) is str and type(value["usage"]) is str
             and type(value["completeness"]) is str and type(value["members"]) is list, "convention_set", path)
    for i, member in enumerate(value["members"]):
        _keys(member, ("id", "version", "digest"), (), f"{path}.members[{i}]")
        _require(type(member["id"]) is str and _is_int(member["version"]) and type(member["digest"]) is str, "convention_set", f"{path}.members[{i}]")


def _check_check(check) -> None:
    path = "$.check"
    _keys(check, ("state", "rng", "log_length", "segment", "status", "decision", "halt"), (), path)
    _require(_is_hex64(check["state"]) and _is_hex64(check["rng"]) and _is_int(check["log_length"]) and _is_int(check["segment"])
             and check["status"] in D.STATE_STATUSES and (check["halt"] is None or type(check["halt"]) is str), "check", path)
    d = check["decision"]
    if d is not None:
        _keys(d, ("id", "kind", "player"), (), f"{path}.decision")
        _require(_is_int(d["id"]) and type(d["kind"]) is str and d["player"] in (0, 1) and _is_int(d["player"]), "check", f"{path}.decision")


# 段 3: 実装・依存・環境・規約の対応


def _check_support(data: dict[str, Any]) -> None:
    problems: list[Problem] = []

    def bad(code: str, path: str) -> None:
        problems.append(Problem(NOT_SUPPORTED, code, path))

    identity = current_identity()
    runtime = runtime_identity()
    engine = data["engine"]
    if engine["method"] != IDENTITY_METHOD or engine["behavior_digest"] != identity["behavior_digest"]:
        bad("implementation_differs", "$.engine.behavior_digest")
    if engine["instrumentation_digest"] != identity["instrumentation_digest"]:  # DS-INSTRUMENTATION: 初版は記録・診断の部品の識別も一致を求める
        bad("instrumentation_differs", "$.engine.instrumentation_digest")
    if engine["version"] != identity["version"]:
        bad("engine_version_differs", "$.engine.version")
    rt = data["runtime"]
    if rt["python_implementation"] != runtime["python_implementation"] or rt["python_version"][:2] != runtime["python_version"][:2]:
        bad("runtime_differs", "$.runtime")
    if rt["rng"] != runtime["rng"]:
        bad("rng_scheme_differs", "$.runtime.rng")
    if data["formats"] != _formats():
        bad("formats_differ", "$.formats")
    deps = data["dependencies"]
    pool = load_card_pool()
    if deps["rules"] not in KNOWN_RULES:
        bad("rules_unknown", "$.dependencies.rules")
    if deps["card_pool"] != CARD_POOL_DEFAULT:
        bad("card_pool_not_default", "$.dependencies.card_pool")
    if deps["card_data"] != {"repository": pool.source["repository"], "commit": pool.source["commit"], "path": pool.source["path"]}:
        bad("card_data_differs", "$.dependencies.card_data")
    if deps["effects"] != pool.effects.id:
        bad("effects_differs", "$.dependencies.effects")
    if _registered_convention(data["convention_set"]) is None:
        bad("convention_set_unsupported", "$.convention_set")
    if problems:
        raise _Stop(NOT_SUPPORTED, problems)


def _registered_convention(record: dict[str, Any]) -> ConventionSetIdentity | None:
    try:
        registered = registered_identity((record["id"], record["version"]))
    except ConventionSetError:  # 登録にない集合（推測で別の集合に対応付けない）
        return None
    return registered if registered.record() == record else None


# 段 4: 登録済みのデータの解決


@dataclass(frozen=True)
class _Resolved:
    rules: Any
    effects: Any
    conventions: ConventionSetIdentity
    pool: Any


def _resolve(data: dict[str, Any]) -> _Resolved:
    state = data["state"]
    names = [f.name for f in dataclasses.fields(GameState) if f.name not in ABSENT_FIELDS]
    missing = [n for n in names if n not in state]
    if missing:
        _stop(MALFORMED, "missing_field", f"$.state.{missing[0]}")
    if any(k not in names for k in state):
        _stop(MALFORMED, "unknown_field", "$.state")
    pool = load_card_pool()
    if state["rules"] != data["dependencies"]["rules"] or state["effects"] != data["dependencies"]["effects"] or state["conventions"] != data["convention_set"]:
        _stop(INCONSISTENT, "dependencies_state_mismatch", "$.state")
    definitions = state["definitions"]
    _require(type(definitions) is list and all(type(c) is str for c in definitions), "definitions", "$.state.definitions")
    _require(len(set(definitions)) == len(definitions), "duplicate_definition", "$.state.definitions")
    for i, card_id in enumerate(definitions):
        if card_id not in pool.definitions:
            _stop(NOT_SUPPORTED, "card_unknown", f"$.state.definitions[{i}]")
    return _Resolved(rules=KNOWN_RULES[state["rules"]], effects=pool.effects, conventions=_registered_convention(data["convention_set"]), pool=pool)


# 段 5: 状態の組み立て


def _decode(value, t, path: str):
    kind = t[0]
    if kind == "int":
        _require(_is_int(value), "type", path)
        return value
    if kind == "str":
        _require(type(value) is str, "type", path)
        return value
    if kind == "bool":
        _require(type(value) is bool, "type", path)
        return value
    if kind == "none":
        _require(value is None, "type", path)
        return None
    if kind == "enum":
        _require(type(value) is str and value in t[1]._value2member_map_, "enum_value", path)
        return t[1](value)
    if kind == "record":
        return _decode_record(value, t[1], path)
    if kind == "list":
        _require(type(value) is list, "type", path)
        return [_decode(v, t[1], f"{path}[{i}]") for i, v in enumerate(value)]
    if kind == "tuple":
        _require(type(value) is list, "type", path)
        return tuple(_decode(v, t[1], f"{path}[{i}]") for i, v in enumerate(value))
    if kind == "fixed":
        _require(type(value) is list and len(value) == len(t[1]), "type", path)
        return tuple(_decode(v, s, f"{path}[{i}]") for i, (v, s) in enumerate(zip(value, t[1], strict=True)))
    if kind == "event":
        _require(type(value) is dict, "type", path)
        return MappingProxyType({k: _decode_any(v, f"{path}.{k}") for k, v in value.items()})
    if kind == "union":
        for member in t[1]:
            if _json_matches(value, member):
                return _decode(value, member, path)
        _stop(MALFORMED, "type", path)
    if kind == "any":
        return _decode_any(value, path)
    _stop(MALFORMED, "type", path)
    return None


def _json_matches(value, t) -> bool:
    kind = t[0]
    if kind == "none":
        return value is None
    if kind == "record":
        return type(value) is dict
    if kind == "int":
        return _is_int(value)
    if kind == "str":
        return type(value) is str
    if kind == "bool":
        return type(value) is bool
    if kind == "enum":
        return type(value) is str
    if kind == "fixed":
        return type(value) is list and len(value) == len(t[1])
    return type(value) is list if kind in ("tuple", "list") else False


def _decode_record(value, allowed: tuple[type, ...], path: str):
    _keys(value, ("type", "fields"), (), path)
    name = value["type"]
    cls = _RECORDS.get(name) if type(name) is str else None
    if cls is None:
        _stop(MALFORMED, "record_type_unknown", f"{path}.type")
    if allowed and cls not in allowed:
        _stop(MALFORMED, "record_type_not_allowed", f"{path}.type")
    spec = _CODEC[name]
    _keys(value["fields"], tuple(spec), (), f"{path}.fields")
    kwargs = {n: _decode(value["fields"][n], t, f"{path}.{n}") for n, t in spec.items()}
    try:
        return cls(**kwargs)
    except (TypeError, ValueError):  # dataclass の __post_init__ の値の確かめ（この 1 回の呼び出しだけ）
        _stop(MALFORMED, "record_value", path)
    return None


def _decode_any(value, path: str):
    t = type(value)
    if value is None or t in (bool, int, str):
        return value
    if t is list:
        return tuple(_decode_any(v, f"{path}[{i}]") for i, v in enumerate(value))
    if t is dict:
        if set(value) == {"enum", "value"}:
            cls = _ENUMS.get(value["enum"]) if type(value["enum"]) is str else None
            _require(cls is not None and type(value["value"]) is str and value["value"] in cls._value2member_map_, "enum_value", path)
            return cls(value["value"])
        return _decode_record(value, (), path)
    _stop(MALFORMED, "type", path)  # 浮動小数など
    return None


def _decode_rng(value, path: str) -> random.Random:
    _keys(value, ("format", "version", "internal", "gauss_next"), (), path)
    internal = value["internal"]
    _require(value["format"] == RNG_FORMAT and _is_int(value["version"]) and value["gauss_next"] is None, "rng", path)
    _require(type(internal) is list and len(internal) == 625 and all(_is_int(v) and 0 <= v < 2 ** 32 for v in internal) and internal[-1] <= 624, "rng", path)
    rng = random.Random()
    try:
        rng.setstate((value["version"], tuple(internal), None))
    except (TypeError, ValueError):  # 乱数の状態の値の確かめ（この 1 回の呼び出しだけ）
        _stop(MALFORMED, "rng", path)
    return rng


def _assemble(state: dict[str, Any], resolved: _Resolved) -> GameState:
    """GameState を項目の値から新しく作る（pickle・__setstate__ を使わない。既定の値で補わない。pending_moves は境界で空）。"""
    kwargs: dict[str, Any] = {}
    for f in dataclasses.fields(GameState):
        name = f.name
        path = f"$.state.{name}"
        if name == "rules":
            kwargs[name] = resolved.rules
        elif name == "definitions":
            kwargs[name] = freeze_mapping({card_id: resolved.pool.get(card_id) for card_id in state[name]})
        elif name == "effects":
            kwargs[name] = resolved.effects
        elif name == "conventions":
            kwargs[name] = resolved.conventions
        elif name == "pending_moves":
            kwargs[name] = ()
        elif name == "rng":
            kwargs[name] = _decode_rng(state[name], path)
        elif name == "cards":
            _require(type(state[name]) is list, "type", path)
            cards: dict[int, CardInstance] = {}
            for i, entry in enumerate(state[name]):
                card = _decode_record(entry, (CardInstance,), f"{path}[{i}]")
                if card.uid in cards:  # 重なりを後の値で上書きしない
                    _stop(MALFORMED, "duplicate_uid", f"{path}[{i}]")
                cards[card.uid] = card
            kwargs[name] = freeze_mapping(cards)
        else:
            kwargs[name] = _decode(state[name], _CODEC["GameState"][name], path)
    return GameState(**kwargs)


# 段 6: 不変条件と領域をまたぐ整合


def _check_restored(state: GameState, data: dict[str, Any]) -> None:
    if supported_decision_error(state) is not None:
        _stop(NOT_SUPPORTED, "decision_resume", "$.state.decision.resume")
    problems: list[Problem] = []
    if structure_problems(state):
        problems.append(Problem(INCONSISTENT, "structure", "$.state"))
    if check_invariants(state):
        problems.append(Problem(INCONSISTENT, "invariants", "$.state"))
    identity, _ = state_conventions(state)
    if identity is None:
        problems.append(Problem(INCONSISTENT, "conventions", "$.state.conventions"))
    if problems:
        raise _Stop(INCONSISTENT, problems)
    expected = data["check"]
    actual = checks(state)
    for key in ("state", "rng", "log_length", "segment", "status", "decision", "halt"):
        if expected[key] != actual[key]:
            problems.append(Problem(INCONSISTENT, "check_differs", f"$.check.{key}"))
    if _encode_state(state) != data["state"]:
        problems.append(Problem(INCONSISTENT, "round_trip_differs", "$.state"))
    if problems:
        raise _Stop(INCONSISTENT, problems)


# ---------------------------------------------------------------- ホストへの接続（S6）


class RestoredGame:
    """信頼されたホストが、復元した状態から既存の操作アダプタ（``adapter.HostedGame``）で続ける最小の入口（S6）。

    - 復元に成功した結果（restored）だけから作る。停止・終局の状態も作れるが、状態の知らせ（``status``）はその状態のまま（活動中とみなさない）。操作の受理・拒否はエンジンが決める
    - 規約集合を差し替える API はない（状態の規約集合のまま）
    - 完全な再現用記録は持たない（``full_record`` はいつも None。保存の前からの記録を持つようには扱わない。完全な記録の位置との接続と残りの照合は、v0.158 の snapshot_replay.replay_from_snapshot が検証者として別に行う。この入口から記録を継ぎ足さない）
    - 閲覧用記録は、復元した時点から ``ViewRecorder.attach`` で始める（``origin`` は attached。復元の前の各イベントの時点の知識は復元しない）
    - 見る人には ``view``（観測）・``view_record``・``CommandResult.view_for`` の結果だけを渡す。``state``・スナップショットはホストの中だけ
    """

    def __init__(self, report: RestoreReport, *, viewers=()):
        if not isinstance(report, RestoreReport) or report.status != RESTORED or report.state is None:
            raise SnapshotNotRestoredError("復元に成功した結果（restored）からだけ、ホストの対戦を作れる")
        viewers = tuple(viewers)
        for viewer in viewers:
            D.check_viewer(viewer)
        if len(set(viewers)) != len(viewers):
            raise ValueError("閲覧者が重なっている")
        self._game = HostedGame(report.state)
        self._recorders = {viewer: ViewRecorder.attach(viewer, report.state) for viewer in viewers}

    @property
    def state(self) -> GameState:
        """ホストの中だけで使う今の状態。"""
        return self._game.state

    @property
    def status(self) -> str:
        return D.status_of(self._game.state)

    @property
    def continuable(self) -> bool:
        return D.continuable(self._game.state)

    @property
    def full_record(self) -> None:
        """完全な再現用記録は持たない（U3 の収集器は新しい対戦の開始からだけ作る）。"""
        return None

    @property
    def failure(self) -> CommandResult | None:
        return self._game.failure

    def submit(self, command, *, submitter: int | None = None, operation_id: str | None = None) -> CommandResult:
        result = self._game.submit(command, submitter=submitter, operation_id=operation_id)
        for recorder in self._recorders.values():
            recorder.add(result)
        return result

    def view(self, viewer):
        D.check_viewer(viewer)
        return observe(self._game.state, viewer)

    def view_record(self, viewer) -> ViewRecord:
        D.check_viewer(viewer)
        return self._recorders[viewer].record()

    def close(self) -> dict[Any, ViewRecord]:
        """閲覧用記録を閉じる（対戦の終局とは別）。完全な再現用記録は持たないので返さない。"""
        return {viewer: recorder.close() for viewer, recorder in self._recorders.items()}

    def save(self, *, origin: dict[str, Any] | None = None, label: str | None = None) -> StateSnapshot:
        """今の状態をもう一度保存する（ホスト用）。"""
        return save_snapshot(self._game.state, origin=origin, label=label)

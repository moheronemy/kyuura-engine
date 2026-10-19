"""v0.16a: 旧経路（v0.13 の処理。v0.15 の経路 ``Route.LEGACY``）の結果を固定した参照データ（docs/legacy-removal-audit-v0.16a.md 8 章）。

v0.15 までの比較のテスト（tests/test_event_kernel_v0_14.py・test_event_kernel_games_v0_14.py・test_kernel_integration_v0_15.py・
test_preflight_v0_15c.py）は、同じ盤面・同じコマンドを旧経路と解決の基盤（KERNEL）に渡して比べていました。v0.16 で旧経路を外すと、
同じ木の中では比べられなくなります。そこで、旧経路がある木（v0.16a。``kyuura_engine/`` の中身は v0.15 の ``aa551ab`` と同じ）で、
比べていた呼び出しごとの旧経路の結果を記録しておき、旧経路を外したあとは KERNEL の結果をこの記録と比べます。

- 記録するのは、テストの呼び出しごと（テストの id と、そのテストの中の呼び出しの順番）の、渡した盤面の指紋（書き出しの形式 9 の全体・
  乱数の指紋・コマンド）と、旧経路の結果（受け付けたら返した状態の形式 9 の全体の指紋、拒否なら例外の種類・コード・理由の文）です。
  対戦の 1 歩ごとの比べ（``Chain``）は、対戦ごとに歩の数と結果の連なりの指紋だけを記録します。
- 盤面の指紋が記録と違えば、テストの盤面が記録したときと違う（比べる意味がない）ので失敗にします（黙って通さない）。
- 決定への答えの ``WRONG_PHASE`` の理由の文だけは、段階の名前の並びを名前の順に並べ直してから記録し、比べます（``error_outcome``）。
  v0.13 から、この並びは ``frozenset`` の並び（文字列のハッシュで決まり、プロセスごとに変わる）で、v0.16d で決まった並びにします。
  並べ直すのはこの文の段階の名前の並びだけで、ほかの理由の文・コード・例外の種類はそのまま比べます。
- 作り方: 旧経路がある木で ``KYUURA_RECORD_LEGACY_REFERENCE=1 python3 -m unittest <モジュール>``（``RECORDED_MODULES``）。今の版から
  作り直さないでください（作り直すと、旧経路との比較ではなくなる。旧経路がない木では作れない）。
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path

from kyuura_engine import EngineError, command_to_dict, state_to_dict
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import with_card_data_commit_before_v0_69

PATH = Path(__file__).resolve().parent / "fixtures" / "legacy_reference_v0_15.json"
RECORD_ENV = "KYUURA_RECORD_LEGACY_REFERENCE"
RECORDED_MODULES = (
    "tests.test_event_kernel_v0_14",
    "tests.test_event_kernel_games_v0_14",
    "tests.test_kernel_integration_v0_15",
    "tests.test_preflight_v0_15c",
)
HOW = (
    "旧経路（engine.Route.LEGACY）がある木（v0.16a。kyuura_engine/ は aa551ab と同じ。git の tree a616b53aef730996e79efc97d8b17f3bdc8910e7）で "
    f"{RECORD_ENV}=1 python3 -m unittest {' '.join(RECORDED_MODULES)}。今の版から作り直さない"
)


def digest(state) -> str:
    """状態の指紋（書き出しの形式 9 の全体。ログ・乱数の指紋・決定・止めた理由を含む）。v0.69: 写しの元（card_data.commit・ログ game_created の card_data_commit）の
    2 か所だけを、確かめた移行（tests/helpers.py の ``with_card_data_commit_before_v0_69``）でもどしてから指紋をとる（参照データは v0.68 までの写しの元で記録した。作り直さない）。"""
    data = json.dumps(with_card_data_commit_before_v0_69(state_to_dict(state, format_version=9)), sort_keys=True, ensure_ascii=False, default=repr)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:32]


def input_digest(state, command) -> str:
    data = json.dumps([digest(state), rng_fingerprint(state.rng), command_to_dict(command)], sort_keys=True, ensure_ascii=False, default=repr)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:32]


_WRONG_PHASE = re.compile(r"今は (\S+)。この操作は (.+) のときだけ")


def error_outcome(error: EngineError) -> tuple:
    """拒否の結果 ("error", 例外の種類, コード, 理由の文)。``WRONG_PHASE`` の理由の文の段階の名前の並びだけ、名前の順に並べ直す。"""
    message = error.message
    if error.code == "WRONG_PHASE":
        found = _WRONG_PHASE.fullmatch(message)
        if found is not None:
            message = f"今は {found.group(1)}。この操作は {', '.join(sorted(found.group(2).split(', ')))} のときだけ"
    return ("error", type(error).__name__, error.code, message)


def outcome_of(apply, state, command, **kwargs) -> tuple:
    """処理の結果: 受け付けたら ("ok", 返した状態の指紋)、拒否なら ``error_outcome``。"""
    try:
        new = apply(state, command, **kwargs)
    except EngineError as error:
        return error_outcome(error)
    return ("ok", digest(new))


def recording() -> bool:
    return bool(os.environ.get(RECORD_ENV))


def _legacy_apply(state, command):
    """旧経路（記録するときだけ。旧経路がない木では作れない）。"""
    try:
        from kyuura_engine.engine import Route, apply_command_via
    except ImportError as error:
        raise RuntimeError("旧経路（engine.Route.LEGACY）がない木では参照データを作れない（v0.16a の木で作る）") from error
    return apply_command_via(state, command, route=Route.LEGACY)


class _Store:
    def __init__(self):
        self._data = None
        self._counters: Counter = Counter()
        self._dirty = False

    @property
    def data(self) -> dict:
        if self._data is None:
            if PATH.exists():
                self._data = json.loads(PATH.read_text(encoding="utf-8"))
            elif recording():
                self._data = {"how": HOW, "calls": {}, "chains": {}}
            else:
                raise AssertionError(f"参照データ {PATH} がない（{HOW}）")
            if recording() and not self._dirty:
                self._dirty = True
                atexit.register(self._write)
        return self._data

    def _write(self) -> None:
        data = self.data
        data["how"] = HOW
        data["calls"] = dict(sorted(data["calls"].items()))
        data["chains"] = dict(sorted(data["chains"].items()))
        PATH.write_text(json.dumps(data, ensure_ascii=False, indent=0, sort_keys=False) + "\n", encoding="utf-8")

    def key(self, test_id: str) -> str:
        n = self._counters[test_id]
        self._counters[test_id] += 1
        return f"{test_id}#{n}"


STORE = _Store()


def expected(testcase, state, command) -> tuple:
    """テストの呼び出し 1 つの、旧経路の結果（``outcome_of`` の形）。記録するときは旧経路で処理して記録する。"""
    key = STORE.key(testcase.id())
    calls = STORE.data["calls"]
    given = input_digest(state, command)
    if recording():
        result = outcome_of(_legacy_apply, state, command)
        calls[key] = {"input": given, "outcome": list(result)}
        return result
    entry = calls.get(key)
    if entry is None:
        raise AssertionError(f"参照データに {key} がない（テストの呼び出しが記録したときと違う。{HOW}）")
    if entry["input"] != given:
        raise AssertionError(f"参照データの {key} の盤面が、記録したときと違う（比べる意味がない）")
    return tuple(entry["outcome"])


class Chain:
    """対戦の 1 歩ごとの結果の連なり（歩の数と、結果の連なりの指紋）。対戦の終わりに記録と比べる（記録するときは記録する）。"""

    def __init__(self, label: str):
        self.label = label
        self.steps = 0
        self._hash = hashlib.sha256()

    def add(self, state, command, result: tuple) -> None:
        self._hash.update(json.dumps([input_digest(state, command), list(result)], ensure_ascii=False).encode("utf-8"))
        self.steps += 1

    def finish(self) -> None:
        chains = STORE.data["chains"]
        value = {"steps": self.steps, "digest": self._hash.hexdigest()[:32]}
        if recording():
            chains[self.label] = value
            return
        entry = chains.get(self.label)
        if entry is None:
            raise AssertionError(f"参照データに対戦 {self.label} がない（{HOW}）")
        if entry != value:
            raise AssertionError(f"対戦 {self.label} の結果の連なりが旧経路の記録と違う（記録 {entry}、今 {value}）")


def legacy_apply_for_recording(state, command):
    """記録するときの旧経路（``Chain`` を使う比べる関数が、記録するときに基準として使う）。"""
    return _legacy_apply(state, command)

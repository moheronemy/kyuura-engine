"""範囲の外にした未裁定の候補の inputs の記録（検証者用。docs/prestop-record-design.md）。

runner（``runner.Runner``）の候補の取得ごとに、範囲の外の理由が ``processability:unresolved_ruling`` の候補について、同じ取得の取っ手で本人の入口へ
``inputs`` を 1 回要求し、返った選択肢（カードの参照・処理可能性・理由）だけを ``prestop/inputs.jsonl`` に残す。

- 方策・行動生成・trace・actor_logs・metrics・coverage・counters・anomalies には何も渡さない・書かない。check・submit・candidates は呼ばない
- 同じ鍵（主体・position・候補の種類・id を除いた候補の内容の sha256）の 2 回目以降は要求しない（repeats）
- 選択肢の値は、本人の入口が返した値だけ。``card_id`` がない（本人のうら）ものは ``face_down`` だけで、観測・内部の状態から補わない。停止コードは書かない
- 上限: 要求の数・応答 1 回の量・``prestop/inputs.jsonl`` の実際の UTF-8 のバイト数（改行をふくむ）。上限のあとの鍵は要求せず、理由ごとに数える
- 失敗: withheld・refused・形式の不正は記録して続ける。通常の例外は記録の失敗（``failure``）として、その局の記録をやめる（対戦は続ける）。
  ``MemoryError``・``KeyboardInterrupt``・``SystemExit`` は通す
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable

FORMAT = "kyuura-vai-prestop-inputs/1"
VERSION = 1
DIR = "prestop"
ROWS = f"{DIR}/inputs.jsonl"
SUMMARY = f"{DIR}/summary.json"
FILES = (ROWS, SUMMARY)
TARGET_REASON = "processability:unresolved_ruling"  # runner._scope の範囲の外の理由（metrics.fetch が数えるものと同じ）
SOURCE_RECORD_FETCH = "record_fetch"
DEFAULT_LIMITS = {"max_fetches_per_game": 256, "max_response_bytes": 16384, "max_rows_bytes": 1 << 20}
STATUSES = ("ok", "withheld", "refused", "contract_unknown", "error", "oversize")
CAP_FETCHES = "max_fetches_per_game"
CAP_ROWS_BYTES = "max_rows_bytes"
SETTING_KEYS = ("enabled", "format", "version", "limits", "note")
NOTE = "範囲の外の未裁定の候補の inputs の検証者用の記録（prestop/。docs/prestop-record-design.md）。有効なら局の必須ファイルに入る"
COUNTERS = ("offered", "keys", "repeats", "no_stages", "attempted", *STATUSES, "skipped_fetch_cap", "skipped_bytes_cap", "skipped_after_failure",
            "unsaved_bytes_cap", "unsaved_failure", "rows", "rows_bytes", "fetches")
OPTION_FIELDS = ("id", "card", "card_id", "face_down", "pokemon", "zone", "bench_index", "processability", "eligible", "reasons")
STAGE_FIELDS = ("stage", "input", "role", "meaning", "count", "order")
TEXT_LIMIT = 200


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def content_sha256(candidate: dict[str, Any]) -> str:
    """候補の内容の要約（runner.candidate_key と同じ正規化: 応答ごとの番号 id を除いた中身）。"""
    return _sha({k: v for k, v in candidate.items() if k != "id"})


# ---------------------------------------------------------------- 計画の設定


def plan_setting(enabled: bool, limits: dict[str, int] | None = None) -> dict[str, Any]:
    """計画に書く設定（無効も明示する）。上限は既定以下の正の整数だけ。"""
    if type(enabled) is not bool:
        raise ValueError("prestop_inputs の enabled は真偽値")
    if not enabled:
        if limits is not None:
            raise ValueError("無効の prestop_inputs に上限を書かない")
        return {"enabled": False, "format": None, "version": None, "limits": None, "note": NOTE}
    merged = dict(DEFAULT_LIMITS) if limits is None else dict(limits)
    problems = limits_problems(merged)
    if problems:
        raise ValueError("; ".join(problems))
    return {"enabled": True, "format": FORMAT, "version": VERSION, "limits": merged, "note": NOTE}


def limits_problems(limits) -> list[str]:
    if not isinstance(limits, dict) or set(limits) != set(DEFAULT_LIMITS):
        return [f"prestop_inputs の limits の項目は {sorted(DEFAULT_LIMITS)} ちょうど"]
    out = []
    for name, top in DEFAULT_LIMITS.items():
        value = limits[name]
        if type(value) is not int or not 1 <= value <= top:
            out.append(f"prestop_inputs の limits.{name} は 1〜{top} の整数")
    return out


def setting_problems(setting) -> list[str]:
    """計画の設定の照合（型・未知の項目・矛盾）。"""
    if not isinstance(setting, dict):
        return ["計画の prestop_inputs（範囲の外の未裁定の候補の inputs の記録の設定）がない・形が違う"]
    if set(setting) != set(SETTING_KEYS):
        return [f"prestop_inputs の項目は {list(SETTING_KEYS)} ちょうど（未知・欠け {sorted(set(setting) ^ set(SETTING_KEYS))}）"]
    if type(setting["enabled"]) is not bool:
        return ["prestop_inputs の enabled は真偽値"]
    if not setting["enabled"]:
        if setting["format"] is not None or setting["version"] is not None or setting["limits"] is not None:
            return ["無効の prestop_inputs に format・version・limits がある（矛盾）"]
        return []
    if setting["format"] != FORMAT or setting["version"] != VERSION:
        return [f"prestop_inputs の format・version は {FORMAT}・{VERSION}"]
    return limits_problems(setting["limits"])


def enabled(plan: dict[str, Any]) -> bool:
    return bool((plan.get("prestop_inputs") or {}).get("enabled"))


# ---------------------------------------------------------------- 記録器


class PrestopRecorder:
    """1 局ぶんの記録（局ごとに作り、局のファイルを書いたら捨てる）。"""

    def __init__(self, limits: dict[str, int] | None = None, *, clock: Callable[[], float] = time.monotonic):
        self.limits = dict(DEFAULT_LIMITS) if limits is None else dict(limits)
        problems = limits_problems(self.limits)
        if problems:
            raise ValueError("; ".join(problems))
        self.clock = clock
        self.failure: dict[str, Any] | None = None
        self.counts_complete = True
        self.counts = {name: 0 for name in COUNTERS}
        self.offered_by_kind: dict[str, int] = {}
        self.capped: set[str] = set()
        self.seconds = 0.0
        self._keys: set[tuple] = set()
        self._lines: list[bytes] = []
        self._rows_full = False
        self._seq = 0

    # -- runner から

    def on_fetch(self, actor, position: int, episode, cands: dict[str, Any], reasons: dict[str, str], fetch_inputs: Callable[[str], dict[str, Any]]) -> None:
        """候補の取得 1 回。``reasons`` は runner._scope の範囲の外の理由（候補の番号 → 理由）。``fetch_inputs(候補の番号)`` は同じ取得の取っ手で本人の入口へ
        inputs を要求する関数（runner が作る。check・submit・candidates は呼ばない）。"""
        c = self.counts
        c["fetches"] += 1
        fetch = c["fetches"]
        for candidate in cands.get("candidates") or []:
            if reasons.get(candidate.get("id")) != TARGET_REASON:
                continue
            kind = candidate.get("kind")
            c["offered"] += 1
            self.offered_by_kind[str(kind)] = self.offered_by_kind.get(str(kind), 0) + 1
            digest = content_sha256(candidate)
            key = (actor, position, kind, digest)
            if key in self._keys:
                c["repeats"] += 1
                continue
            self._keys.add(key)
            c["keys"] += 1
            if not candidate.get("input_stages"):
                c["no_stages"] += 1
                continue
            if self.failure is not None:
                c["skipped_after_failure"] += 1
                continue
            if c["attempted"] >= self.limits[CAP_FETCHES]:
                c["skipped_fetch_cap"] += 1
                self.capped.add(CAP_FETCHES)
                continue
            base = self._base_row(actor, position, episode, fetch, candidate, digest)
            if self._rows_full or c["rows_bytes"] + len(self._line({**base, "status": "refused", "response_bytes": 0, "seconds": 0.0})) > self.limits[CAP_ROWS_BYTES]:
                c["skipped_bytes_cap"] += 1  # 要求の前に、本文のない行すら入らないと分かる
                self._rows_full = True
                self.capped.add(CAP_ROWS_BYTES)
                continue
            self._attempt(base, candidate, fetch_inputs)

    def fail(self, where: str, error: BaseException, *, counts_complete: bool = True) -> None:
        if self.failure is None:
            self.failure = {"where": where, "type": type(error).__name__, "message": str(error)[:300], "after_fetches": self.counts["fetches"]}
        if not counts_complete:
            self.counts_complete = False

    # -- 内部

    def _base_row(self, actor, position, episode, fetch, candidate, digest) -> dict[str, Any]:
        cand = {k: candidate[k] for k in ("id", "kind", "processability", "reasons", "input_disclosure", "input_stages", "stadium") if k in candidate}
        cand["content_sha256"] = digest
        cand["guarantees_sha256"] = _sha(candidate.get("guarantees"))
        self._seq += 1
        return {"format": FORMAT, "seq": self._seq, "actor": actor, "position": position, "episode": episode, "fetch": fetch,
                "candidate": cand, "source": SOURCE_RECORD_FETCH}

    @staticmethod
    def _line(row: dict[str, Any]) -> bytes:
        return (canonical(row) + "\n").encode("utf-8")

    def _attempt(self, base: dict[str, Any], candidate: dict[str, Any], fetch_inputs) -> None:
        c = self.counts
        started = self.clock()
        c["attempted"] += 1
        try:
            answer = fetch_inputs(candidate["id"])
        except MemoryError:
            raise
        except Exception as error:  # noqa: BLE001  入口の例外（エンジンの不具合など）: 記録の失敗。対戦の進行には伝えない
            self.seconds += self.clock() - started
            c["error"] += 1
            self.fail("inputs_request", error)
            self._save({**base, "status": "error", "detail": {"type": type(error).__name__, "message": str(error)[:TEXT_LIMIT]},
                        "response_bytes": None, "seconds": round(self.clock() - started, 6)}, after_failure=True)
            return
        elapsed = self.clock() - started
        self.seconds += elapsed
        try:
            row = self._classify(base, answer)
        except MemoryError:
            raise
        except Exception as error:  # noqa: BLE001  記録の側の誤り
            c["error"] += 1
            self.fail("classify", error)
            self._save({**base, "status": "error", "detail": {"type": type(error).__name__, "message": str(error)[:TEXT_LIMIT]},
                        "response_bytes": None, "seconds": round(elapsed, 6)}, after_failure=True)
            return
        row["seconds"] = round(elapsed, 6)
        c[row["status"]] += 1
        self._save(row)

    def _classify(self, base: dict[str, Any], answer) -> dict[str, Any]:
        size = len(canonical(answer).encode("utf-8")) if isinstance(answer, (dict, list)) else None
        row = {**base, "response_bytes": size}
        if not isinstance(answer, dict):
            return {**row, "status": "contract_unknown", "detail": {"reason": "answer_not_object"}}
        if size is not None and size > self.limits["max_response_bytes"]:
            return {**row, "status": "oversize", "detail": {"reason": "response_too_large", "limit": self.limits["max_response_bytes"]}}
        if answer.get("ok") is not True:
            response = answer.get("response") if isinstance(answer.get("response"), dict) else {}
            refusal = response.get("refusal") if isinstance(response.get("refusal"), dict) else None
            error = answer.get("error") if isinstance(answer.get("error"), dict) else None
            code = (refusal or error or {}).get("code")
            if code is None:
                return {**row, "status": "contract_unknown", "detail": {"reason": "not_ok_without_code"}}
            return {**row, "status": "refused", "refusal": {"code": str(code)[:TEXT_LIMIT], "from": "refusal" if refusal else "error"},
                    "refetch_required": answer.get("refetch_required")}
        response = answer.get("response")
        if not isinstance(response, dict):
            return {**row, "status": "contract_unknown", "detail": {"reason": "response_not_object"}}
        if "withheld" in response:
            withheld = response["withheld"] if isinstance(response["withheld"], dict) else {}
            return {**row, "status": "withheld", "withheld": {"code": str(withheld.get("code"))[:TEXT_LIMIT]}}
        stages = response.get("stages")
        if not isinstance(stages, list) or not stages:
            return {**row, "status": "contract_unknown", "detail": {"reason": "stages_not_list" if not isinstance(stages, list) else "stages_empty"}}
        out = []
        for stage in stages:
            if not isinstance(stage, dict) or type(stage.get("stage")) is not int:
                return {**row, "status": "contract_unknown", "detail": {"reason": "stage_not_object"}}
            options = stage.get("options")
            if options is not None and (not isinstance(options, list) or not all(isinstance(o, dict) for o in options)):
                return {**row, "status": "contract_unknown", "detail": {"reason": "options_not_list_of_objects", "stage": stage["stage"]}}
            item = {k: stage[k] for k in STAGE_FIELDS if k in stage}
            # 選択肢は返った値だけを写す（card_id がないものは face_down などそのまま。補わない）
            item["options"] = None if options is None else [{k: o[k] for k in OPTION_FIELDS if k in o} for o in options]
            out.append(item)
        return {**row, "status": "ok", "stages": out}

    def _save(self, row: dict[str, Any], *, after_failure: bool = False) -> None:
        c = self.counts
        line = self._line(row)
        if self._rows_full or c["rows_bytes"] + len(line) > self.limits[CAP_ROWS_BYTES]:
            # 上限を超える行は書かない（別のファイルへ逃がさない）。それ以降の要求をやめる
            self._rows_full = True
            self.capped.add(CAP_ROWS_BYTES)
            c["unsaved_failure" if after_failure else "unsaved_bytes_cap"] += 1
            return
        self._lines.append(line)
        c["rows"] += 1
        c["rows_bytes"] += len(line)

    # -- 出力

    def status(self) -> str:
        if self.failure is not None:
            return "failed"
        return "capped" if self.capped else "complete"

    def summary(self) -> dict[str, Any]:
        """局の要約（固定の件数・状態・時間・失敗だけ。候補別の一覧を入れない）。"""
        return {"format": FORMAT, "enabled": True, "status": self.status(), "limits": dict(self.limits), **dict(self.counts),
                "offered_by_kind": dict(sorted(self.offered_by_kind.items())), "capped": sorted(self.capped), "seconds": round(self.seconds, 6),
                "failure": self.failure, "counts_complete": self.counts_complete}

    def rows_bytes(self) -> bytes:
        return b"".join(self._lines)

    def files(self) -> list[tuple[str, bytes]]:
        """保存するファイル（局の終わりに 1 回）。失敗していても、作れた分と失敗を書く。"""
        return [(ROWS, self.rows_bytes()), (SUMMARY, (json.dumps(self.summary(), ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8"))]


# ---------------------------------------------------------------- 照合（テスト・完了の照合・集計で同じ関数を使う）


def reconcile(summary: dict[str, Any], *, rows: bytes | None = None, excluded_by_kind: dict[str, int] | None = None) -> list[str]:
    """要約の照合式（docs/prestop-record-design.md 11 章）。``rows`` は prestop/inputs.jsonl の中身、``excluded_by_kind`` は同じ局の result.json の
    metrics.kinds.<種類>.excluded["processability:unresolved_ruling"]。問題の文の並び（空なら一致）。"""
    p = []
    if not isinstance(summary, dict) or summary.get("format") != FORMAT:
        return ["prestop の要約がない・形式が違う"]
    missing = [k for k in (*COUNTERS, "offered_by_kind", "limits", "status", "capped", "seconds", "counts_complete") if k not in summary]
    if missing:
        return [f"prestop の要約に項目がない {missing}"]
    s = summary
    if s["offered"] != s["keys"] + s["repeats"]:
        p.append("offered != keys + repeats")
    if s["offered"] != sum(s["offered_by_kind"].values()):
        p.append("offered != Σ offered_by_kind")
    if s["keys"] != s["no_stages"] + s["attempted"] + s["skipped_fetch_cap"] + s["skipped_bytes_cap"] + s["skipped_after_failure"]:
        p.append("keys != no_stages + attempted + skipped_fetch_cap + skipped_bytes_cap + skipped_after_failure")
    if s["attempted"] != sum(s[k] for k in STATUSES):
        p.append("attempted != ok + withheld + refused + contract_unknown + error + oversize")
    if s["rows"] != s["attempted"] - s["unsaved_bytes_cap"] - s["unsaved_failure"]:
        p.append("rows != attempted - unsaved_bytes_cap - unsaved_failure")
    if s["attempted"] > s["limits"].get(CAP_FETCHES, 0):
        p.append("attempted > max_fetches_per_game")
    if s["rows_bytes"] > s["limits"].get(CAP_ROWS_BYTES, 0):
        p.append("rows_bytes > max_rows_bytes")
    expected_status = "failed" if s.get("failure") is not None else ("capped" if s["capped"] else "complete")
    if s["status"] != expected_status:
        p.append(f"status {s['status']} != {expected_status}")
    if rows is not None:
        if len(rows) != s["rows_bytes"]:
            p.append(f"inputs.jsonl の長さ {len(rows)} != rows_bytes {s['rows_bytes']}")
        lines = rows.split(b"\n")
        if rows and lines[-1] != b"":
            p.append("inputs.jsonl が改行で終わらない")
        n = len(lines) - 1 if rows else 0
        if n != s["rows"]:
            p.append(f"inputs.jsonl の行の数 {n} != rows {s['rows']}")
    if excluded_by_kind is not None and s["counts_complete"]:
        kinds = set(excluded_by_kind) | set(s["offered_by_kind"])
        diff = sorted(k for k in kinds if excluded_by_kind.get(k, 0) != s["offered_by_kind"].get(k, 0))
        if diff:
            p.append(f"offered_by_kind が result.json の範囲の外（{TARGET_REASON}）と違う {diff}")
    return p


def excluded_by_kind(metrics: dict[str, Any]) -> dict[str, int]:
    """result.json の metrics から、種類ごとの範囲の外（TARGET_REASON）の延べ。"""
    out = {}
    for kind, row in (metrics.get("kinds") or {}).items():
        n = ((row or {}).get("excluded") or {}).get(TARGET_REASON, 0)
        if n:
            out[kind] = n
    return out

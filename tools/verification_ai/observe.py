"""主体別の観測・更新・公開ログの記録（検証者用。docs/verification-ai-observation.md）。

runner（``runner.Runner``）の送信ごとに、プレイヤー 0・プレイヤー 1・観戦者のそれぞれについて、送信の前後の観測・その送信で新たに発生した更新・その送信で新たに
公開されたログを、ローカルの通し番号・operation_id・受理番号と対応付けて残す。

- 主体別の内容は、エンジンの閲覧用記録（``view_record.ViewRecorder``。形式 ``kyuura_view_format`` 1）で作る。観測は ``observation.observe``、ログは
  ``visible_log``・``visible_segment_logs`` で、その時点の見える範囲の写しを凍結する（あとから遡って再投影しない）。拒否の診断は送った本人の記録だけに入る
- 対応表（``observe/rows.jsonl``。形式 ``FORMAT``）は検証者だけが読む。閲覧用記録は operation_id などを入れない形式なので、対応はこの表で行う
- 更新は、runner が通常の経路（``ClientHub.take_updates``）で取り出した結果の写しを受け取るだけ（記録側は取り出さない。通常側の更新を奪わない）。
  取り出されなかった更新は ``not_drained``（空とは書かない）
- 方策・行動生成へは何も渡さない。ホストの完全な情報（完全な記録 ``full_record.json``）はこの形式に入れない
- 記録の処理の例外は、記録の失敗（``recorder_failed``）として残す。対戦の進行は変えない
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from kyuura_engine import diagnostics as D
from kyuura_engine.observation import observe
from kyuura_engine.view_record import (
    KIND_OWN_REJECTION,
    KIND_START,
    KIND_UNAVAILABLE,
    KIND_UPDATE,
    ViewRecorder,
    dumps_view_record,
    validate_view_record,
)

FORMAT = "kyuura-vai-observation/1"
VIEWERS = (0, 1, None)  # None は観戦者
AUDIENCES = (0, 1, "spectator", "host")  # ClientHub の更新の宛先（host はホストのアプリケーション。観測は観戦者と同じ範囲）
DIR = "observe"
ROWS = f"{DIR}/rows.jsonl"
SUMMARY = f"{DIR}/summary.json"
FILES = (ROWS, f"{DIR}/view-0.json", f"{DIR}/view-1.json", f"{DIR}/view-spectator.json", SUMMARY)

# 行の状態の区分
COMPLETE = "complete"  # すべての行が期待どおりで、欠けがない
INCOMPLETE = "incomplete"  # 欠け（取り出されなかった更新・記録できなかった項目）がある。欠けは空として扱わない
INCONSISTENT = "inconsistent"  # 期待との矛盾（拒否のあとの更新・観測の不一致など）
RECORDER_FAILED = "recorder_failed"  # 記録の処理そのものの例外（以後の行は記録していない）


def viewer_key(viewer) -> str:
    return "spectator" if viewer is None else str(viewer)


def audience_viewer(audience):
    return audience if audience in (0, 1) else None


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _position(state) -> list[int]:
    """ログの位置（区間・今の区間のログの長さ）。閲覧用のログ（visible_log）は state.log と同じ長さ（見えない項目は伏せるだけで除かない）。"""
    return [state.segment_index, len(state.log)]


class ObservationRecorder:
    """1 局ぶんの記録（局ごとに作り、局の終わりにファイルのバイト列を返す。全局をためない）。runner からだけ呼ばれる。"""

    def __init__(self):
        self.rows: list[dict[str, Any]] = []
        self.failure: dict[str, Any] | None = None
        self._views: dict[Any, ViewRecorder] = {}
        self._entries = {v: 0 for v in VIEWERS}  # 各閲覧者の閲覧用記録に入った項目の数（期待の値。閉じたあとに記録と照らす）
        self._results: list[tuple[Any, Any]] = []  # まだ行に対応付けていないエンジンの結果
        self._open: dict[str, Any] | None = None
        self._last_after: dict[str, str] | None = None
        self._seq = 0
        self._records: dict[str, Any] = {}
        self._verification: dict[str, Any] = {}

    # ---------------------------------------------------------------- runner からの呼び出し

    def fail(self, where: str, error: BaseException) -> None:
        if self.failure is None:
            self.failure = {"where": where, "type": type(error).__name__, "message": str(error)[:300], "after_seq": self._seq}

    def on_start(self, state) -> None:
        for v in VIEWERS:
            self._views[v] = ViewRecorder.attach(v, state)
            self._entries[v] = 1
        sha = {viewer_key(v): digest(observe(state, v)) for v in VIEWERS}
        self.rows.append({"seq": 0, "kind": "start", "status": D.status_of(state),
                          "viewers": {viewer_key(v): {"observation_sha256": sha[viewer_key(v)], "log": _position(state), "view_entry": 1, "view_kind": KIND_START}
                                      for v in VIEWERS},
                          "updates": {"next_number": 1, "note": "ClientHub は作った直後で、受理の前に更新はない（runner は開始のあとに取り出さない）"}})
        self._last_after = sha

    def on_result(self, actor, result) -> None:
        """ホストの側の verifier の呼び出し（エンジンの結果）。閲覧用記録へ渡し、次の行に対応付ける。"""
        added = {}
        for v in VIEWERS:
            if result.outcome == D.REJECTED:
                kind = KIND_OWN_REJECTION if (v is not None and v == result.actor) else None
            elif result.outcome == D.FAILED:
                kind = KIND_UNAVAILABLE
            else:
                kind = KIND_UPDATE
            self._views[v].add(result)
            if kind is not None:
                self._entries[v] += 1
                added[viewer_key(v)] = (self._entries[v], kind)
        self._results.append((actor, result, added))

    def on_submitted(self, entry, operation_id, sent, before_state, after_state, accepted_index) -> None:
        self._flush()
        results, self._results = self._results, []
        added = results[-1][2] if results else {}
        outcome = sent.get("outcome")
        row = {"seq": self._next(), "kind": "submit", "attempt": entry["n"], "position": entry["position"], "actor": entry["actor"],
               "operation_id": operation_id, "outcome": outcome, "ok": sent.get("ok"), "refusal": (sent.get("refusal") or {}).get("code"),
               "accepted_index": accepted_index if outcome == D.ACCEPTED else None,
               "engine_results": [{"outcome": r.outcome, "actor": r.actor, "status": r.status} for _a, r, _added in results],
               "viewers": {}, "updates": {a: {"status": "pending"} for a in map(str, AUDIENCES)}}
        for v in VIEWERS:
            key = viewer_key(v)
            n, kind = added.get(key, (None, None))
            row["viewers"][key] = {"before": {"observation_sha256": digest(observe(before_state, v)), "log": _position(before_state)},
                                   "after": {"observation_sha256": digest(observe(after_state, v)), "log": _position(after_state)},
                                   "view_entry": n, "view_kind": kind}
        self._open = row

    def on_check_invalid(self, entry, state) -> None:
        """check が invalid の試み（送信なし）。runner はこのあと更新を取り出す（出ないことの確かめ）。"""
        self._flush()
        row = {"seq": self._next(), "kind": "check_invalid", "attempt": entry["n"], "position": entry["position"], "actor": entry["actor"],
               "operation_id": None, "outcome": None, "accepted_index": None, "engine_results": [],
               "viewers": {viewer_key(v): {"before": {"observation_sha256": digest(observe(state, v)), "log": _position(state)}, "after": None,
                                           "view_entry": None, "view_kind": None} for v in VIEWERS},
               "updates": {a: {"status": "pending"} for a in map(str, AUDIENCES)}}
        for item in row["viewers"].values():
            item["after"] = dict(item["before"])
        self._open = row

    def on_drained(self, audience, got) -> None:
        """runner が通常の経路で取り出した更新の写し（記録側は取り出さない）。"""
        row = self._open
        if row is None:
            self.rows.append({"seq": self._next(), "kind": "orphan_drain", "audience": str(audience), "count": len(got)})
            return
        viewer = audience_viewer(audience)
        expected = row["viewers"][viewer_key(viewer)]["after"]["observation_sha256"]
        items = []
        for u in got:
            item = {k: u.get(k) for k in ("contract", "format", "type", "number", "status")}
            obs = u.get("observation")
            item["observation_sha256"] = None if obs is None else digest(obs)
            item["observation_same_as_after_view"] = item["observation_sha256"] == expected
            if not item["observation_same_as_after_view"]:
                item["observation"] = obs  # 観測と違うときだけ中身を残す（照合のため）
            items.append(item)
        row["updates"][str(audience)] = {"status": "drained", "updates": items}

    def on_finish(self, termination, state) -> None:
        self._flush()
        row = {"seq": self._next(), "kind": "end", "termination": termination, "unpaired_engine_results": len(self._results)}
        if state is not None:
            row["viewers"] = {viewer_key(v): {"observation_sha256": digest(observe(state, v)), "log": _position(state)} for v in VIEWERS}
        self.rows.append(row)
        self._close_views()

    # ---------------------------------------------------------------- 内部

    def _next(self) -> int:
        self._seq += 1
        return self._seq

    def _flush(self) -> None:
        row, self._open = self._open, None
        if row is None:
            return
        for audience, item in row["updates"].items():
            if item["status"] == "pending":
                row["updates"][audience] = {"status": "not_drained", "note": "runner がこの行のあとに更新を取り出していない（取得できなかった。空ではない）"}
        row["problems"] = self._row_problems(row)
        after = {k: (v["after"] or {}).get("observation_sha256") for k, v in row["viewers"].items()}
        self._last_after = after
        self.rows.append(row)

    def _row_problems(self, row) -> list[dict[str, Any]]:
        out = []

        def add(kind, code, **detail):
            out.append({"kind": kind, "code": code, **detail})

        last = self._last_after or {}
        for key, item in row["viewers"].items():
            if last.get(key) is not None and item["before"]["observation_sha256"] != last[key]:
                add(INCONSISTENT, "before_differs_from_previous_after", viewer=key)
        accepted = row["outcome"] == D.ACCEPTED
        if row["kind"] == "submit" and len(row["engine_results"]) > 1:
            add(INCONSISTENT, "several_engine_results")
        if row["kind"] == "submit" and row["outcome"] in (D.ACCEPTED, D.REJECTED, D.FAILED) and not row["engine_results"]:
            add(INCOMPLETE, "engine_result_not_received")
        if not accepted:
            for key, item in row["viewers"].items():
                if item["before"]["observation_sha256"] != item["after"]["observation_sha256"] or item["before"]["log"] != item["after"]["log"]:
                    add(INCONSISTENT, "view_changed_without_acceptance", viewer=key)
        for audience, item in row["updates"].items():
            if item["status"] != "drained":
                add(INCOMPLETE, "updates_not_drained", audience=audience)
                continue
            numbers = [u["number"] for u in item["updates"]]
            if accepted and numbers != [row["accepted_index"]]:
                add(INCONSISTENT, "update_numbers", audience=audience, numbers=numbers, expected=row["accepted_index"])
            if not accepted and numbers:
                add(INCONSISTENT, "update_without_acceptance", audience=audience, numbers=numbers)
            if any(not u["observation_same_as_after_view"] for u in item["updates"]):
                add(INCONSISTENT, "update_observation_differs_from_view", audience=audience)
        return out

    def _close_views(self) -> None:
        for v in VIEWERS:
            record = self._views[v].close()
            self._records[viewer_key(v)] = record
        self._verification = self._verify_against_records()

    def _verify_against_records(self) -> dict[str, Any]:
        """閉じた閲覧用記録と行を照らす（項目の番号・種類・観測の sha256・ログの位置の連続）。"""
        problems = []
        per = {}
        for v in VIEWERS:
            key = viewer_key(v)
            data = self._records[key].data
            report = validate_view_record(data)
            entries = data["entries"]
            per[key] = {"entries": len(entries), "expected_entries": self._entries[v], "validate": report.status,
                        "validate_problems": [f"{p.kind}:{p.code}:{p.path}" for p in report.problems], "end": (data.get("end") or {}).get("state")}
            if len(entries) != self._entries[v]:
                problems.append({"kind": INCONSISTENT, "code": "view_entry_count", "viewer": key, "entries": len(entries), "expected": self._entries[v]})
            for row in self.rows:
                item = (row.get("viewers") or {}).get(key) or {}
                n = item.get("view_entry")
                if n is None:
                    continue
                if not 1 <= n <= len(entries):
                    problems.append({"kind": INCONSISTENT, "code": "view_entry_missing", "viewer": key, "seq": row["seq"], "n": n})
                    continue
                e = entries[n - 1]
                if e["kind"] != item.get("view_kind"):
                    problems.append({"kind": INCONSISTENT, "code": "view_entry_kind", "viewer": key, "seq": row["seq"], "kind_found": e["kind"]})
                    continue
                if e["kind"] in (KIND_START, KIND_UPDATE):
                    sha = (item.get("after") or {}).get("observation_sha256", item.get("observation_sha256"))
                    if digest(e["observation"]) != sha:
                        problems.append({"kind": INCONSISTENT, "code": "view_entry_observation", "viewer": key, "seq": row["seq"]})
                    events = e["events"]
                    item["new_log_events"] = len(events)
                    if e["kind"] == KIND_UPDATE:
                        before, after = item["before"]["log"], item["after"]["log"]
                        if events:
                            first, last = events[0], events[-1]
                            end = [last["segment"], last["log_index"] + 1]
                            if after[1] == 0 and after[0] != before[0]:  # 区間が変わり、新しい区間のログがまだない（前の区間の残りだけ）
                                end = after if last["segment"] == before[0] else end
                            if [first["segment"], first["log_index"]] != before or end != after:
                                problems.append({"kind": INCONSISTENT, "code": "view_entry_log_range", "viewer": key, "seq": row["seq"]})
                        elif before != after:
                            problems.append({"kind": INCONSISTENT, "code": "view_entry_log_range", "viewer": key, "seq": row["seq"]})
            if report.status != "structure_valid":
                problems.append({"kind": INCONSISTENT, "code": "view_record_structure", "viewer": key, "status": report.status})
        return {"viewers": per, "problems": problems}

    # ---------------------------------------------------------------- 出力

    def summary(self) -> dict[str, Any]:
        rows = [r for r in self.rows if r["kind"] in ("submit", "check_invalid")]
        problems = [dict(p, seq=r["seq"]) for r in rows for p in r.get("problems", [])] + list(self._verification.get("problems", []))
        orphan = [r for r in self.rows if r["kind"] == "orphan_drain"]
        if orphan:
            problems.append({"kind": INCONSISTENT, "code": "orphan_drain", "count": len(orphan)})
        if self.failure is not None:
            status = RECORDER_FAILED
        elif any(p["kind"] == INCONSISTENT for p in problems):
            status = INCONSISTENT
        elif any(p["kind"] == INCOMPLETE for p in problems) or not self._closed_ok():
            status = INCOMPLETE
        else:
            status = COMPLETE
        by_kind: dict[str, int] = {}
        for r in rows:
            k = f"{r['kind']}:{r.get('outcome')}"
            by_kind[k] = by_kind.get(k, 0) + 1
        codes: dict[str, int] = {}
        for p in problems:
            codes[f"{p['kind']}:{p['code']}"] = codes.get(f"{p['kind']}:{p['code']}", 0) + 1
        return {"format": FORMAT, "status": status, "failure": self.failure, "rows": len(rows), "by_kind": dict(sorted(by_kind.items())),
                "problem_codes": dict(sorted(codes.items())), "problems": problems[:200], "problems_total": len(problems),
                "view_records": self._verification.get("viewers"), "files": list(FILES),
                "relation": {"rows": "検証者用の対応表（ローカルの通し番号・operation_id・受理番号・主体別の観測の sha256・ログの位置・更新の写し）",
                             "view": "主体別の閲覧用記録（kyuura_view_format 1。観測・新しいログ・本人の拒否の診断）。operation_id を入れない形式",
                             "trace": "trace.jsonl の試み（attempt の n）と行の attempt が対応する", "actors": "actors/<主体>.jsonl は従来どおり、その主体が行動するときの要求と応答",
                             "host": "ホストの完全な情報は full_record.json（この形式に入れない。host の宛先の更新は観戦者と同じ範囲の観測）"}}

    def _closed_ok(self) -> bool:
        return bool(self._records) and any(r["kind"] == "end" for r in self.rows)

    def files(self) -> list[tuple[str, bytes]]:
        """保存するファイル（局の終わりに 1 回）。記録に失敗していても、作れた分と失敗を書く（欠けを空にしない）。"""
        out = [(ROWS, "".join(canonical(r) + "\n" for r in self.rows).encode("utf-8"))]
        for v in VIEWERS:
            key = viewer_key(v)
            record = self._records.get(key)
            if record is not None:
                out.append((f"{DIR}/view-{key}.json", dumps_view_record(record).encode("utf-8")))
            else:
                out.append((f"{DIR}/view-{key}.json", (canonical({"format": FORMAT, "missing": "閲覧用記録を閉じられなかった（記録の失敗）", "viewer": key}) + "\n").encode("utf-8")))
        out.append((SUMMARY, (json.dumps(self.summary(), ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8")))
        return out

"""検証ランナー（D）。``client_api`` の入口だけで 1 対戦を進め、上限・終わり方の分類・照合・記録を行う（docs/verification-ai-v0.md 4 章〜6 章）。

- 操作は ``PlayerEndpoint``・``HostEndpoint`` の ``handle`` だけで送る。``HostedGame.submit``・``apply_command`` を直接呼ばない
- 方策に渡すのは、その主体の入口の応答（JSON の値）だけ。ランナーが記録のために持つ完全な情報（状態・``CommandResult``・完全な記録）は渡さない
- 1 回の試みを 4 段階で分ける: 候補にある → 入力を作れる → check を通る → submit が受理される（受理のあとの完走は、次の試みの状態の区分と終わり方で見る）
- 単一のプロセス・上限つき。時間は単調時計で、要求と要求のあいだ（安全な処理の境界）で確かめる。1 回のエンジンの呼び出しの途中では止めない
"""

from __future__ import annotations

import json
import time
import traceback
from dataclasses import asdict, dataclass, field
from typing import Any

from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine import preset_deck
from kyuura_engine.client_api import ClientHub

from . import actions as B
from .policies import UniformPolicy, host_seed, player_seed
from kyuura_engine.replay_record import checks

from .records import RecordingGame, canonical

CONTRACT = {"contract": "kyuura-client-api", "format": 1}
HOST = "host"

# 対戦の終わり方（1 つの対戦に 1 つ。仕様 6.1 節）
GAME_OVER = "game_over"
HALTED_KNOWN = "halted_known"  # 停止の公開の診断の分類が既知の未裁定・未対応・技術的な制限
HALTED_UNCLASSIFIED = "halted_unclassified"  # 停止したが、分類が上の 3 つでない（既知の停止として扱わない）
INPUT_UNAVAILABLE = "input_unavailable"  # 操作するはずの主体に、範囲の中で送れる入力がない（R-2〜R-5・入力を返さない・作れない）
API_CONTRACT_UNKNOWN = "api_contract_unknown"  # 知らない段の項目・値・段の形の問題
NO_PROGRESS = "no_progress"  # 同じ状態での拒否・選び直しの上限
LIMIT_OPERATIONS = "limit_operations"
LIMIT_ACCEPTED = "limit_accepted"
LIMIT_TURNS = "limit_turns"
LIMIT_TIME = "limit_time"
FAILED = "failed"  # submit の結果が failed（状態の不整合でない）・処理できない結果のあとの入口
STATE_INTEGRITY = "state_integrity"  # submit の結果が failed で、診断の分類が state_integrity
EXCEPTION = "exception"  # ランナー・入口からの例外（入口は例外を投げない約束）
INCONSISTENCY = "inconsistency"  # ランナーの照合の不一致で、続けられないもの（待っている主体と候補の状況の食い違い・だれも操作できない）
START_REJECTED = "start_rejected"
LIMIT_TERMINATIONS = (LIMIT_OPERATIONS, LIMIT_ACCEPTED, LIMIT_TURNS, LIMIT_TIME)
KNOWN_HALT_CATEGORIES = frozenset({D.RULING_UNRESOLVED, D.UNSUPPORTED, D.TECHNICAL_LIMIT})

KNOWN_SITUATIONS = frozenset({L.ACTOR_TO_ACT, L.WAITING_FOR_PLAYER, L.WAITING_FOR_HOST, L.GAME_OVER, L.HALTED})
KNOWN_PROCESSABILITY = frozenset(L.PROCESSABILITY)
KNOWN_DISCLOSURE = frozenset({L.DISCLOSURE_CONFIRMED, L.DISCLOSURE_UNCONFIRMED, L.DISCLOSURE_NONE})


@dataclass(frozen=True)
class Limits:
    """上限（docs/verification-ai-v0.md 4.3 節）。

    - ``operations``: 送った ``submit`` の要求の数（受理・拒否・failed・ホストの段の refused のすべて。check だけで止めた試みは数えない）
    - ``accepted``: 受理された ``submit`` の数
    - ``turns``: 始まった番の数（公開の状態の区間と番の番号の組が変わり、番の番号が 1 以上になった回数。延長戦の区間の番も数える）
    - ``seconds``: 実行の開始からの単調時計の秒（要求と要求のあいだで確かめる。1 回のエンジンの呼び出しの途中では止めない）
    - ``rejections_per_position``: 同じ状態（受理のあいだ）での check の invalid・拒否・refused の合計
    - ``draws_per_position``: 同じ状態での候補の選び直しの回数（入力を作れなかった・試した入力をまた選んだを含む）"""

    operations: int = 2000
    accepted: int = 1000
    turns: int = 200
    seconds: float = 120.0
    rejections_per_position: int = 16
    draws_per_position: int = 64


@dataclass(frozen=True)
class Config:
    deck0: str = "hitmonchan-dewgong"
    deck1: str = "venusaur-parasect"
    conventions: str | None = None  # None は既定の規約集合
    game_seed: int = 1
    policy_seed: int = 1
    host_seed: int = 1
    profile: str = "deep"
    limits: Limits = field(default_factory=Limits)
    run_id: str = "v0"


class SubmitWithoutCheck(Exception):
    """valid な check のない入力を送ろうとした（ランナーの誤り）。"""


def request(endpoint, kind: str, **fields) -> dict[str, Any]:
    """入口へ JSON の要求を送り、JSON の応答を受け取る（文字列を通して、内部のオブジェクトを持ち出さない）。"""
    text = json.dumps({**CONTRACT, "type": kind, **fields}, ensure_ascii=False)
    answer = endpoint.handle(json.loads(text))
    return json.loads(json.dumps(answer, ensure_ascii=False))


def submit_checked(endpoint, handle: dict[str, str], choices: list, checked: dict[str, Any], *, operation_id: str) -> dict[str, Any]:
    """check の応答が valid で、同じ取っ手・同じ入力のときだけ submit を送る（check の前の送信を防ぐ）。"""
    if not checked or not (checked.get("response") or {}).get("valid") or checked.get("_handle") != handle or checked.get("_choices") != choices:
        raise SubmitWithoutCheck("valid な check のない入力は送らない")
    return request(endpoint, "submit", **handle, choices=choices, operation_id=operation_id)


def candidate_key(candidate: dict[str, Any]) -> str:
    """同じ状態の中で候補を見分ける値（応答ごとの番号 ``id`` を除いた中身）。"""
    return canonical({k: v for k, v in candidate.items() if k != "id"})


class _Stop(Exception):
    def __init__(self, termination: str, detail: dict[str, Any] | None = None):
        super().__init__(termination)
        self.termination = termination
        self.detail = detail or {}


class Runner:
    def __init__(self, config: Config, *, clock=time.monotonic, policy_factory=UniformPolicy, wrap_endpoint=None):
        self.config = config
        self.limits = config.limits
        self.clock = clock
        self.policies = {0: policy_factory(player_seed(config.policy_seed, 0)), 1: policy_factory(player_seed(config.policy_seed, 1)),
                         HOST: policy_factory(host_seed(config.host_seed))}
        self.wrap_endpoint = wrap_endpoint or (lambda actor, endpoint: endpoint)
        self.trace: list[dict[str, Any]] = []  # 検証者用の操作の記録（全主体）
        self.actor_logs: dict[Any, list[dict[str, Any]]] = {0: [], 1: [], HOST: []}  # 主体ごとの、その主体が受け取った応答と選択（本人向け）
        self.anomalies: list[dict[str, Any]] = []
        self.counters = {"operations": 0, "accepted": 0, "turns": 0, "attempts": 0, "check_invalid": 0, "rejected": 0, "refused": 0, "failed": 0,
                         "unbuildable": 0, "withheld": 0, "retry_same_input": 0, "deep_fallback_unverified": 0}
        self.coverage: dict[str, dict[str, int]] = {}
        self.game: RecordingGame | None = None
        self.hub: ClientHub | None = None
        self.last_result = None  # 検証者用の CommandResult（方策に渡さない）
        self.position = 0
        self._turn_key = None
        self._started = None

    # ---------------------------------------------------------------- 入口

    def run(self) -> dict[str, Any]:
        self._started = self.clock()
        termination, detail = None, {}
        try:
            self._start()
            while True:
                self._loop_once()
        except _Stop as stop:
            termination, detail = stop.termination, stop.detail
        except Exception as error:  # 入口は例外を投げない約束。ランナーの誤りも含めて、ほかの分類に変えずに記録する
            termination, detail = EXCEPTION, {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        record = None if self.game is None else self.game.close()
        return {"termination": {"class": termination, "detail": detail, "at": self._where()}, "counters": dict(self.counters),
                "anomalies": list(self.anomalies), "coverage": {k: dict(sorted(v.items())) for k, v in sorted(self.coverage.items())},
                "trace": self.trace, "actor_logs": self.actor_logs, "record": record,
                "policies": {str(k): {"name": p.name, "version": p.version, "distribution": p.distribution, "seed": p.seed, "draws": p.draws}
                             for k, p in self.policies.items()},
                "limits": asdict(self.limits), "elapsed_seconds": round(self.clock() - self._started, 3)}

    # ---------------------------------------------------------------- 進行

    def _start(self) -> None:
        c = self.config
        options = {} if c.conventions is None else {"conventions": c.conventions}
        self.game, result = RecordingGame.start(preset_deck(c.deck0).cards(), preset_deck(c.deck1).cards(), c.game_seed, game_id=c.run_id, **options)
        if self.game is None:
            raise _Stop(START_REJECTED, {"outcome": result.outcome, "diagnostic_id": None if result.diagnosis is None else result.diagnosis.diagnostic_id})
        self.hub = ClientHub(self.game, verifier=self._on_verifier)
        self.endpoints = {0: self.wrap_endpoint(0, self.hub.player(0)), 1: self.wrap_endpoint(1, self.hub.player(1)), HOST: self.wrap_endpoint(HOST, self.hub.host())}

    def _on_verifier(self, actor, result) -> None:
        self.last_result = result

    def _elapsed(self) -> float:
        return self.clock() - self._started

    def _check_time(self) -> None:
        if self._elapsed() >= self.limits.seconds:
            raise _Stop(LIMIT_TIME, {"seconds": self.limits.seconds})

    def _check_limits(self) -> None:
        self._check_time()
        if self.counters["operations"] >= self.limits.operations:
            raise _Stop(LIMIT_OPERATIONS, {"operations": self.counters["operations"]})
        if self.counters["accepted"] >= self.limits.accepted:
            raise _Stop(LIMIT_ACCEPTED, {"accepted": self.counters["accepted"]})

    def _cover(self, axis: str, key) -> None:
        bucket = self.coverage.setdefault(axis, {})
        bucket[str(key)] = bucket.get(str(key), 0) + 1

    def _where(self) -> dict[str, Any]:
        return {"attempt": self.counters["attempts"], "accepted": self.counters["accepted"], "operations": self.counters["operations"],
                "turns": self.counters["turns"], "position": self.position}

    def _loop_once(self) -> None:
        self._check_limits()
        view = request(self.endpoints[HOST], "view")
        if not view.get("ok"):
            raise _Stop(FAILED, {"host_view_error": view.get("error")})
        status = view["status"]
        self._cover("status", status["status"])
        self._cover("phase", status["phase"])
        if status["status"] == D.GAME_OVER:
            raise _Stop(GAME_OVER, {"result": view["observation"].get("result"), "segment": status["segment"]})
        if status["status"] == D.HALTED:
            halt = status.get("halt") or {}
            known = halt.get("category") in KNOWN_HALT_CATEGORIES
            raise _Stop(HALTED_KNOWN if known else HALTED_UNCLASSIFIED, {"halt": halt})
        key = (status["segment"], view["observation"]["turn"])
        if key != self._turn_key:
            self._turn_key = key
            if key[1] >= 1:
                if self.counters["turns"] >= self.limits.turns:
                    raise _Stop(LIMIT_TURNS, {"turns": self.counters["turns"]})
                self.counters["turns"] += 1
        waiting = status["waiting"]
        if not waiting:
            raise _Stop(INCONSISTENCY, {"reason": "nobody_waiting", "status": status})
        if len(waiting) != 1:
            raise _Stop(INCONSISTENCY, {"reason": "several_waiting", "waiting": waiting})
        by = waiting[0]["by"]
        self._cover("waiting", waiting[0]["kind"])
        actor = self._resolve_actor(by, waiting[0])
        self._act(actor)

    def _resolve_actor(self, by, waiting) -> Any:
        """待っている主体。``players``（準備で両方）は 0 → 1 の決まった順で、候補の状況が actor_to_act の方（V0 の暫定の順。D-8 は未採用）。"""
        if by in (0, 1, HOST):
            return by
        if by == "players":
            for actor in (0, 1):
                r = request(self.endpoints[actor], "candidates")
                if r.get("ok") and r["response"]["situation"] == L.ACTOR_TO_ACT:
                    return actor
            raise _Stop(INCONSISTENCY, {"reason": "players_waiting_but_no_actor", "waiting": waiting})
        raise _Stop(API_CONTRACT_UNKNOWN, {"reason": "unknown_waiting_by", "waiting": waiting})

    # ---------------------------------------------------------------- 1 つの状態での試み

    def _act(self, actor) -> None:
        endpoint = self.endpoints[actor]
        policy = self.policies[actor]
        own_view = request(endpoint, "view")
        self.actor_logs[actor].append({"type": "position", "position": self.position, "view": own_view})
        rejections = draws = 0
        tried: set[str] = set()
        unbuildable: dict[str, str] = {}
        while True:
            self._check_limits()
            response = request(endpoint, "candidates")
            if not response.get("ok"):
                raise _Stop(FAILED, {"candidates_error": response.get("error")})
            cands = response["response"]
            self._validate_candidates(actor, cands)
            if cands["situation"] != L.ACTOR_TO_ACT:
                raise _Stop(INCONSISTENCY, {"reason": "waiting_actor_not_to_act", "actor": actor, "situation": cands["situation"],
                                            "empty_reason": cands["empty_reason"]})
            in_scope, scope = self._scope(cands, unbuildable)
            if not in_scope:
                raise _Stop(INPUT_UNAVAILABLE, {"actor": actor, "empty_reason": cands["empty_reason"], "scope": scope,
                                                "residual_present": cands["coverage"]["residual"]["present"], "unbuildable": unbuildable,
                                                "withheld": cands["coverage"]["withheld_input_candidates"]})
            draws += 1
            if draws > self.limits.draws_per_position:
                raise _Stop(NO_PROGRESS, {"actor": actor, "reason": "draws_per_position", "draws": draws - 1, "rejections": rejections})
            handle_base = {"game": cands["game"], "revision": cands["revision"]}
            context = {"view": own_view, "candidates": cands}
            index, reason = policy.choose("candidate", in_scope, context)
            candidate = in_scope[index]
            allowed = B.FALLBACK_PROCESSABILITY if scope["fallback_unverified"] else B.DEEP_PROCESSABILITY
            entry = self._attempt(actor, candidate, reason, scope)
            log = {"type": "attempt", "n": entry["n"], "position": self.position, "candidates": response,
                   "choice": {"candidate": candidate["id"], "reason": reason}}
            self.actor_logs[actor].append(log)
            handle = {**handle_base, "candidate": candidate["id"]}
            stages: list = []
            if candidate["input_stages"]:
                answer = request(endpoint, "inputs", **handle)
                log["inputs"] = answer
                inputs = answer.get("response") or {}
                if not answer.get("ok"):
                    entry["build"] = {"inputs_refused": inputs.get("refusal")}
                    self._anomaly("inputs_refused_on_fresh_handle", entry, {"refusal": inputs.get("refusal")})
                    continue
                if "withheld" in inputs:
                    entry["build"] = {"withheld": inputs["withheld"]["code"]}
                    self.counters["withheld"] += 1
                    unbuildable[candidate_key(candidate)] = "withheld"
                    continue
                stages = inputs["stages"]
                # 依存する段の形の確かめ（legal_actions.stage_dependency_problems）は、2 段目以降のすべてが depends_on_stage か path_stages を持つ段の並び
                # （エネルギー・進化・ワザ・特殊能力・カツラの 2 枚目）だけが対象。前の段に依存しない 2 段目（初期配置の options_from_stage・にげるのトラッシュ）は
                # この関数の対象の外で、当てると「直前の段でない」と報告する（設計書の当初の記述の誤り。docs/verification-ai-v0.md 3.2 節）
                dependent = len(stages) > 1 and all("depends_on_stage" in s or "path_stages" in s for s in stages[1:])
                problems = L.stage_dependency_problems(stages) if dependent else []
                if problems:
                    entry["build"] = {"stage_problems": problems}
                    raise _Stop(API_CONTRACT_UNKNOWN, {"reason": "stage_dependency_problems", "problems": problems, "attempt": entry["n"]})
                entry["stages"] = stages
                try:
                    choices, picks, meaning = B.build_choices(stages, policy, {"view": own_view, "candidate": candidate}, allowed)
                except B.ContractUnknown as error:
                    entry["build"] = {"contract_unknown": error.detail}
                    raise _Stop(API_CONTRACT_UNKNOWN, {"reason": "stage_contract", "detail": error.detail, "attempt": entry["n"]}) from None
                except B.Unbuildable as error:
                    entry["build"] = {"unbuildable": error.reason, "stage": error.stage}
                    self.counters["unbuildable"] += 1
                    unbuildable[candidate_key(candidate)] = error.reason
                    continue
                self._cover_stages(stages, meaning)
            else:
                choices, picks, meaning = [], [], []
            entry.update({"build": "ok", "choices": choices, "picks": picks, "meaning": meaning})
            log["choice"].update({"choices": choices, "picks": picks})
            signature = canonical([candidate_key(candidate), meaning])
            if signature in tried:
                entry["build"] = "ok_already_tried"
                self.counters["retry_same_input"] += 1
                continue
            checked = request(endpoint, "check", **handle, choices=choices)
            checked["_handle"], checked["_choices"] = handle, choices
            entry["check"] = {k: v for k, v in checked.items() if not k.startswith("_")}
            log["check"] = entry["check"]
            if not checked["response"]["valid"]:
                self.counters["check_invalid"] += 1
                tried.add(signature)
                rejections += 1
                self._after_refusal_like(entry, actor)
                if rejections >= self.limits.rejections_per_position:
                    raise _Stop(NO_PROGRESS, {"actor": actor, "reason": "rejections_per_position", "rejections": rejections})
                continue
            if self.counters["operations"] >= self.limits.operations:
                raise _Stop(LIMIT_OPERATIONS, {"operations": self.counters["operations"]})
            before_state = self.game.state
            operation_id = f"{self.config.run_id}-{self.counters['operations'] + 1:06d}"
            self.last_result = None
            sent = submit_checked(endpoint, handle, choices, checked, operation_id=operation_id)
            self.counters["operations"] += 1
            entry["operation_id"] = operation_id
            entry["submit"] = self._submit_entry(sent)
            log["submit"] = sent
            outcome = sent.get("outcome")
            self._cover("outcome", outcome)
            if outcome == D.ACCEPTED:
                self.counters["accepted"] += 1
                self._cover("accepted_kind", candidate["kind"])
                self._after_accept(entry, sent)
                self.position += 1
                return
            if outcome == D.FAILED or not sent.get("ok", True):
                self.counters["failed"] += 1
                category = entry["submit"].get("verifier", {}).get("category")
                raise _Stop(STATE_INTEGRITY if category == D.STATE_INTEGRITY else FAILED, {"attempt": entry["n"], "submit": entry["submit"]})
            if outcome == D.REJECTED:
                self.counters["rejected"] += 1
                if candidate.get("processability") == L.SUPPORTED:
                    self._anomaly("supported_rejected", entry, {"diagnostic": entry["submit"].get("verifier")})
            elif outcome == L.REFUSED:
                self.counters["refused"] += 1
                code = (sent.get("refusal") or {}).get("code")
                self._cover("refusal", code)
                if code in (L.CANDIDATE_INPUT_INVALID, L.CANDIDATE_NOT_EXECUTABLE, L.INPUT_BOUNDARY_UNCONFIRMED):
                    self._anomaly("check_valid_but_submit_refused", entry, {"code": code})
            else:
                raise _Stop(API_CONTRACT_UNKNOWN, {"reason": "unknown_outcome", "outcome": outcome, "attempt": entry["n"]})
            if self.game.state is not before_state or checks(self.game.state) != self.game.last_check():
                self._anomaly("state_changed_on_rejection", entry, {})
            tried.add(signature)
            rejections += 1
            self._after_refusal_like(entry, actor)
            if rejections >= self.limits.rejections_per_position:
                raise _Stop(NO_PROGRESS, {"actor": actor, "reason": "rejections_per_position", "rejections": rejections})

    def _attempt(self, actor, candidate, reason, scope) -> dict[str, Any]:
        self.counters["attempts"] += 1
        self._cover("chosen_kind", candidate["kind"])
        self._cover("chosen_processability", candidate.get("processability"))
        entry = {"type": "attempt", "n": self.counters["attempts"], "position": self.position, "actor": actor, "candidate": candidate,
                 "candidate_reason": reason, "scope": scope, "build": None, "elapsed": round(self._elapsed(), 3)}
        self.trace.append(entry)
        return entry

    def _submit_entry(self, sent: dict[str, Any]) -> dict[str, Any]:
        out = {"ok": sent.get("ok"), "outcome": sent.get("outcome"), "refusal": sent.get("refusal"), "refetch_required": sent.get("refetch_required"),
               "result": sent.get("result"), "error": sent.get("error")}
        r = self.last_result
        if r is not None and r.diagnosis is not None:  # 検証者用の診断（ホストの側の verifier の呼び出しから。方策に渡さない）
            out["verifier"] = {"diagnostic_id": r.diagnosis.diagnostic_id, "category": r.diagnosis.category, "engine_code": r.verifier.engine_code}
        return out

    def _scope(self, cands: dict[str, Any], unbuildable: dict[str, str]):
        """プロファイル deep の範囲（仕様 4.5 節）: 処理可能性が supported・may_stop_later、入力を返す、表示だけでない候補。範囲の中に候補がなければ、
        unverified も許す（deep_fallback_unverified として記録）。範囲から除いた候補は理由ごとに数える。入力を作れなかった候補は、同じ状態では選び直さない。"""
        display = set(cands["coverage"]["display_only_kinds"])
        excluded: dict[str, int] = {}
        for c in cands["candidates"]:
            self._cover("offered_kind", c["kind"])

        def pick(allowed):
            chosen = []
            for c in cands["candidates"]:
                why = None
                if c["kind"] in display:
                    why = "display_only"
                elif c["input_disclosure"] == L.DISCLOSURE_UNCONFIRMED:
                    why = "input_withheld"
                elif c.get("processability") not in allowed:
                    why = f"processability:{c.get('processability')}"
                elif candidate_key(c) in unbuildable:
                    why = f"unbuildable:{unbuildable[candidate_key(c)]}"
                if why is None:
                    chosen.append(c)
                else:
                    excluded[why] = excluded.get(why, 0) + 1
            return chosen

        chosen = pick(B.DEEP_PROCESSABILITY)
        fallback = False
        if not chosen:
            excluded.clear()
            chosen = pick(B.FALLBACK_PROCESSABILITY)
            fallback = bool(chosen)
            if fallback:
                self.counters["deep_fallback_unverified"] += 1
        for why, n in excluded.items():
            self._cover("scope_excluded", why)
        for item in cands["coverage"]["residual"]["present"]:
            self._cover("residual_present", item["id"])
        return chosen, {"in_scope": len(chosen), "excluded": excluded, "fallback_unverified": fallback}

    def _validate_candidates(self, actor, cands: dict[str, Any]) -> None:
        """知らない値を推測で扱わない（仕様 4.4 節）。"""
        if cands["situation"] not in KNOWN_SITUATIONS:
            raise _Stop(API_CONTRACT_UNKNOWN, {"reason": "unknown_situation", "value": cands["situation"]})
        self._cover("situation", cands["situation"])
        known_ids = {c["id"] for c in cands["coverage"]["residual"]["classes"]}
        for item in cands["coverage"]["residual"]["present"]:
            if item["id"] not in known_ids:
                raise _Stop(API_CONTRACT_UNKNOWN, {"reason": "unknown_residual", "value": item})
        for c in cands["candidates"]:
            if c.get("processability") not in KNOWN_PROCESSABILITY:
                raise _Stop(API_CONTRACT_UNKNOWN, {"reason": "unknown_processability", "value": c.get("processability"), "kind": c["kind"]})
            if c["input_disclosure"] not in KNOWN_DISCLOSURE:
                raise _Stop(API_CONTRACT_UNKNOWN, {"reason": "unknown_disclosure", "value": c["input_disclosure"], "kind": c["kind"]})

    def _cover_stages(self, stages, meaning) -> None:
        for stage in stages:
            self._cover("input", stage["input"])
            for feature in ("depends_on_stage", "upstream_stages", "options_by_path", "options_from_stage", "total_units", "distinct_across_stages"):
                if feature in stage:
                    self._cover("stage_feature", feature)
            if "decision_kind" in stage:
                self._cover("decision_kind", stage["decision_kind"])
            if stage.get("count", {}).get("min") == 0:
                chosen = sum(1 for m in meaning if m["stage"] == stage["stage"])
                self._cover("optional_stage", "declined" if chosen == 0 else "used")
            if stage.get("count", {}).get("max", 0) > 1:
                self._cover("stage_feature", "count_max_over_1")
        self._cover("stage_count", len(stages))

    def _anomaly(self, kind: str, entry: dict[str, Any], detail: dict[str, Any]) -> None:
        item = {"kind": kind, "attempt": entry["n"], "position": entry["position"], "actor": entry["actor"], "detail": detail}
        entry.setdefault("anomalies", []).append(kind)
        self.anomalies.append(item)

    def _after_refusal_like(self, entry, actor) -> None:
        """拒否・断り・check の invalid のあと: ほかの閲覧者に公開の更新が出ない。"""
        for audience in (0, 1, "spectator", "host"):
            got = self.hub.take_updates(audience)
            if got:
                self._anomaly("update_after_rejection", entry, {"audience": audience, "count": len(got)})

    def _after_accept(self, entry, sent) -> None:
        if not sent.get("refetch_required"):
            self._anomaly("accepted_without_refetch", entry, {})
        for audience in (0, 1, "spectator", "host"):
            got = self.hub.take_updates(audience)
            numbers = [u.get("number") for u in got]
            if numbers != [self.counters["accepted"]]:
                self._anomaly("update_numbers", entry, {"audience": audience, "numbers": numbers, "expected": self.counters["accepted"]})
                continue
            if audience in (0, 1, "spectator"):
                endpoint = self.endpoints[audience] if audience in (0, 1) else self.hub.spectator()
                now = request(endpoint, "view")
                if now.get("observation") != got[0].get("observation"):
                    self._anomaly("update_observation_differs_from_view", entry, {"audience": audience})


def run_game(config: Config, **kwargs) -> dict[str, Any]:
    return Runner(config, **kwargs).run()

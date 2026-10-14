"""v0.15: 別の木（固定した前の版など）のエンジンと、同じ対戦の 1 歩ごとの結果を、別々のプロセスで記録して比べる（C 段階の道具）。

ふだんのテスト（``python3 -m unittest``）では走らせません。docs/event-integration-verification-v0.15d.md 2 章。

``record``: ``--root`` の木の ``kyuura_engine`` だけを読み込み（``python3 -I`` で、この道具がある木の ``kyuura_engine`` を読まない）、
その木の対戦のテストの方針（``tests/test_*_games*.py`` の ``play_game``）か、ストレス実行の組（``tools/stress_engine.py`` の
``choose_command``）で対戦を進め、1 歩ごとに「コマンド・受け付けたか（拒否なら例外の種類とコード）・書き出しの形式 9 の全体の
指紋」を記録する（gzip の JSON Lines。拒否の理由の文の指紋も記録する）。形式 9 にはログ・乱数の指紋・決定・止めた理由が入っている。``--save-every`` を付けると、
その歩ごとに状態を pickle で保存・復元してから続ける（両方の木で同じことをする）。

``record`` が使う API は v0.13 の公開の API（``new_game``・``apply_command``・``state_to_dict``・``command_to_dict``・``EngineError``）
だけで、``--route``・``--preflight`` を付けたときだけ内部の入口（v0.15 の木は ``engine.apply_command_via``、v0.16b からの木は経路のない
``engine.apply_command_with``）を使う（付けなければ、その木の ``apply_command``）。

``compare``: 2 つの記録を対戦ごと・歩ごとに比べ、最初の食い違いを報告する。v0.16 から、決定への答えの ``WRONG_PHASE`` の拒否は理由の文
そのもの（``m``）も記録し、2 つの文が「今の段階が同じで、並べた段階の名前の集まりが同じ（並びだけが違う）」ときだけ、食い違いではなく
許した差（``WRONG_PHASE`` の並び。v0.16d で並びを決まったものにした。docs/legacy-test-migration-v0.16d.md）として数える。ほかの
理由の文の違い・``m`` のない記録の違いは、すべて食い違い。

``tree``（v0.16）: 固定した前の版のコミットを、このリポジトリから ``git archive`` で展開した木を作る（比べる木の作り方を決まったものに
する。docs/legacy-removal-audit-v0.16a.md 8 章）。

``record`` は、文字列のハッシュの乱数化を止めた（``PYTHONHASHSEED=0``）プロセスで動く（乱数化されていれば、``PYTHONHASHSEED=0``・
``-P -s`` で自分を起動し直す。``-P`` は ``-I`` と同じく、この道具がある木の ``kyuura_engine`` を読まないため）。v0.13 の拒否の理由の文には、
``frozenset`` の並び（文字列のハッシュで決まる）で書くものがある（決定への答えの ``WRONG_PHASE``。``decisions.DECISION_PHASES``）ので、
プロセスごとに並びが変わると、同じ拒否でも理由の文の指紋が違ってしまう（docs/kernel-integration-v0.15b.md 7 章）。

例::

    python3 tools/engine_lockstep.py record --root /path/to/v013 --corpus natural --seeds 100 --out a.jsonl.gz
    python3 tools/engine_lockstep.py record --root . --route kernel --corpus natural --seeds 100 --out c.jsonl.gz
    python3 tools/engine_lockstep.py compare a.jsonl.gz c.jsonl.gz
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib
import json
import os
import pickle
import random
import re
import subprocess
import sys
import tarfile
import time
from collections import Counter
from pathlib import Path

NATURAL_MODULES = (
    "test_alakazam_games_v0_7", "test_blastoise_games_v0_6", "test_bulbasaur_games_v0_5", "test_butterfree_games_v0_4d",
    "test_coin_games", "test_combined_games_v0_4e", "test_confusion_games", "test_dark_wartortle_games_v0_13",
    "test_defender_games", "test_evolution_games_v0_4a", "test_giovanni_games_v0_11", "test_harden_games_v0_4b",
    "test_haunter_games_v0_9", "test_machamp_games_v0_10", "test_moltres_games_v0_12", "test_muk_games_v0_8",
    "test_pikachu_games", "test_pluspower_games", "test_sleep_paralysis_games", "test_stage2_games_v0_4c",
    "test_status_games_v0_3d", "test_trainer_games", "test_weedle_games",
)
KERNEL_RESUMES = frozenset({"attack", "knock_out", "post_knockout", "take_prize", "promote_active"})


class Recorder:
    def __init__(self, engine, apply, out, *, save_every: int = 0, timing: bool = False):
        self.engine = engine
        self.apply = apply
        self.out = out
        self.save_every = save_every
        self.timing = timing
        self.game = None
        self.step = 0
        self.counts: Counter = Counter()
        self.times: Counter = Counter()

    def start(self, game: str) -> None:
        self.game = game
        self.step = 0
        self.counts["games"] += 1

    def digest(self, state) -> str:
        data = json.dumps(self.engine.state_to_dict(state, format_version=9), sort_keys=True, ensure_ascii=False, default=repr)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()[:32]

    def initial(self, state) -> None:
        """対戦の始めの状態（``new_game`` の結果。対戦準備の途中で止まった対戦も比べられるように）。"""
        self.out.write(json.dumps({"g": self.game, "i": "init", "h": self.digest(state)}, ensure_ascii=False) + "\n")

    def kind(self, state, command) -> str:
        name = type(command).__name__
        if name in ("UseAttack", "EndTurn"):
            return name
        if name in ("ResolveDecision", "TakePrize", "PromoteActive") and state.decision is not None and state.decision.resume in KERNEL_RESUMES:
            return f"{name}:{state.decision.resume}"
        return "other"

    def __call__(self, state, command):
        kind = self.kind(state, command)
        cmd = json.dumps(self.engine.command_to_dict(command), sort_keys=True, default=repr)
        t0 = time.perf_counter()
        try:
            new, error = self.apply(state, command), None
        except self.engine.EngineError as caught:
            new, error = None, caught
        elapsed = time.perf_counter() - t0
        # 拒否は例外の種類・コード・理由の文（の指紋。v0.15b から）
        outcome = "ok" if error is None else [type(error).__name__, error.code, hashlib.sha1(error.message.encode()).hexdigest()[:12]]
        if self.timing and kind != "other":
            label = f"{kind}:{'ok' if error is None else 'rejected'}"
            self.times[label] += elapsed
            self.counts[f"time_n:{label}"] += 1
        record = {"g": self.game, "i": self.step, "c": hashlib.sha1(cmd.encode()).hexdigest()[:16], "o": outcome}
        if error is None:
            record["h"] = self.digest(new)
        elif error.code == "WRONG_PHASE":
            record["m"] = error.message  # v0.16: 並びの違いだけを許すかを、文そのもので確かめる（compare）
        self.out.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.step += 1
        self.counts["steps"] += 1
        if kind != "other":
            self.counts["owned"] += 1
        if error is not None:
            self.counts[f"rejected:{error.code}"] += 1
            raise error
        if self.save_every and self.step % self.save_every == 0:
            new = pickle.loads(pickle.dumps(new))
            self.counts["restored"] += 1
        return new


def _apply_function(engine_module, route: str | None, preflight: str | None):
    """その木の公開の ``apply_command``。``--route``・``--preflight`` を付けたときだけ内部の入口: v0.15 の木は ``engine.apply_command_via``
    （経路と先読み）、v0.16b からの木は ``engine.apply_command_with``（先読みだけ。経路はない）。"""
    if route is None and preflight is None:
        return engine_module.apply_command
    from kyuura_engine import engine as E
    options = {"preflight": preflight} if preflight else {}
    if hasattr(E, "Route"):  # v0.15 の木
        chosen = E.Route(route) if route is not None else E.DEFAULT_ROUTE

        def apply(state, command):
            return E.apply_command_via(state, command, route=chosen, **options)

        return apply
    if route is not None:
        raise SystemExit("この木には経路がない（v0.16b で v0.13 の経路を外した）。--route を付けずに比べる")

    def apply_with(state, command):
        return E.apply_command_with(state, command, **options)

    return apply_with


def record(args) -> int:
    root = Path(args.root).resolve()
    for path in (root / "tools", root):
        sys.path.insert(0, str(path))
    import kyuura_engine as engine

    loaded = Path(engine.__file__).resolve()
    if root not in loaded.parents:
        raise SystemExit(f"{loaded} は --root {root} の kyuura_engine ではない（python3 -I で実行する）")
    apply = _apply_function(engine, args.route, args.preflight)
    opener = gzip.open if args.out.endswith(".gz") else open
    started = time.perf_counter()
    errors = 0
    with opener(args.out, "wt", encoding="utf-8") as out:
        rec = Recorder(engine, apply, out, save_every=args.save_every, timing=args.timing)
        if args.corpus in ("natural", "all"):
            modules = args.modules.split(",") if args.modules else NATURAL_MODULES
            for name in modules:
                module = importlib.import_module(f"tests.{name}")
                original = module.apply_command
                original_new_game = getattr(module, "new_game", None)
                module.apply_command = rec
                if original_new_game is not None:
                    def recorded_new_game(*a, _new_game=original_new_game, **k):
                        state = _new_game(*a, **k)
                        rec.initial(state)
                        return state
                    module.new_game = recorded_new_game
                try:
                    for seed in range(args.start, args.start + args.seeds):
                        rec.start(f"natural:{name}:{seed}")
                        try:
                            module.play_game(seed)
                        except Exception as error:  # 対戦のテスト自身の確認（不変条件・監査）の失敗も記録する
                            errors += 1
                            out.write(json.dumps({"g": rec.game, "error": f"{type(error).__name__}: {str(error)[:300]}"}, ensure_ascii=False) + "\n")
                finally:
                    module.apply_command = original
                    if original_new_game is not None:
                        module.new_game = original_new_game
        if args.corpus in ("stress", "all"):
            import compat_driver as driver
            import stress_engine as stress
            names = set(args.scenarios.split(",")) if args.scenarios else None
            for spec in stress.ALL_SCENARIOS:
                if names is not None and spec.name not in names:
                    continue
                for seed in range(args.start, args.start + args.stress_seeds):
                    rec.start(f"stress:{spec.name}:{seed}")
                    rng = random.Random(f"kyuura-stress:{spec.name}:{seed}")
                    state = engine.new_game(driver._deck(spec.deck0), driver._deck(spec.deck1), seed)
                    rec.initial(state)
                    for _ in range(args.steps):
                        if state.phase in engine.TERMINAL_PHASES:
                            break
                        command = stress.choose_command(state, rng, args.illegal_rate)
                        try:
                            state = rec(state, command)
                        except engine.EngineError:
                            continue
        summary = {"summary": dict(rec.counts), "errors": errors, "elapsed": round(time.perf_counter() - started, 1),
                   "root": str(root), "route": args.route, "preflight": args.preflight, "version": getattr(engine, "__version__", "?"),
                   "hash_randomization": sys.flags.hash_randomization}
        if args.timing:
            summary["times_ms"] = {k: round(v / rec.counts[f"time_n:{k}"] * 1000, 4) for k, v in rec.times.items()}
            summary["times_total_s"] = {k: round(v, 4) for k, v in rec.times.items()}
        out.write(json.dumps(summary, ensure_ascii=False) + "\n")
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if errors else 0


def _read(path: str):
    opener = gzip.open if path.endswith(".gz") else open
    games: dict[str, list] = {}
    order: list[str] = []
    summary = None
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            if "summary" in item:
                summary = item
                continue
            game = item["g"]
            if game not in games:
                games[game] = []
                order.append(game)
            games[game].append(item)
    return order, games, summary


_WRONG_PHASE = re.compile(r"今は (\S+)。この操作は (.+) のときだけ")


def wrong_phase_order_only(ra: dict, rb: dict) -> bool:
    """2 つの歩の記録の違いが、決定への答えの ``WRONG_PHASE`` の理由の文の、段階の名前の並びだけか（v0.16）。

    同じ歩・同じコマンド・どちらも ``WRONG_PHASE`` の ``IllegalActionError``・理由の文（``m``）がどちらも記録され、今の段階が同じで、
    並べた段階の名前の集まり（重なりも含めて）が同じときだけ真。理由の文の指紋（``o`` の 3 つめ）以外の項目が違えば偽。"""
    if set(ra) != set(rb) or {k: v for k, v in ra.items() if k not in ("o", "m")} != {k: v for k, v in rb.items() if k not in ("o", "m")}:
        return False
    oa, ob = ra.get("o"), rb.get("o")
    if not (isinstance(oa, list) and isinstance(ob, list) and oa[:2] == ob[:2] == ["IllegalActionError", "WRONG_PHASE"]):
        return False
    ma, mb = _WRONG_PHASE.fullmatch(ra.get("m", "")), _WRONG_PHASE.fullmatch(rb.get("m", ""))
    if ma is None or mb is None or ma.group(1) != mb.group(1):
        return False
    if sorted(ma.group(2).split(", ")) != sorted(mb.group(2).split(", ")):
        return False
    # 理由の文の指紋は、記録した文そのものの指紋（文と指紋が食い違う記録は許さない）
    return all(o[2] == hashlib.sha1(r["m"].encode()).hexdigest()[:12] for o, r in ((oa, ra), (ob, rb)))


def compare(args) -> int:
    order_a, a, sa = _read(args.a)
    order_b, b, sb = _read(args.b)
    divergences = 0
    steps = 0
    allowed: Counter = Counter()
    examples: list[str] = []
    if order_a != order_b:
        print(f"対戦の並びが違う（{len(order_a)} と {len(order_b)}）")
        divergences += 1
    for game in order_a:
        ra, rb = a.get(game, []), b.get(game, [])
        n = min(len(ra), len(rb))
        first = None
        for i in range(n):
            if ra[i] == rb[i]:
                continue
            if wrong_phase_order_only(ra[i], rb[i]):
                allowed["WRONG_PHASE の段階の名前の並び"] += 1
                if len(examples) < 3:
                    examples.append(f"{game} 歩 {ra[i]['i']}: {ra[i]['m']!r} / {rb[i]['m']!r}")
                continue
            first = i
            break
        steps += sum(1 for item in ra[:n] if item.get("i") != "init") if first is None else 0
        if first is None and len(ra) != len(rb):
            first = n
        if first is not None:
            divergences += 1
            print(f"DIVERGENCE {game} 歩 {first}: {ra[first] if first < len(ra) else None} / {rb[first] if first < len(rb) else None}")
    print(f"対戦 {len(order_a)}・一致した歩 {steps}・食い違い {divergences}・許した差 {sum(allowed.values())} {dict(allowed)}")
    for example in examples:
        print(f"  許した差の例: {example}")
    for label, s in (("a", sa), ("b", sb)):
        if s is not None:
            print(label, json.dumps({k: s[k] for k in ("root", "route", "preflight", "version", "elapsed", "errors")}, ensure_ascii=False))
    return 1 if divergences else 0


def tree(args) -> int:
    """固定した前の版のコミットを ``git archive`` で ``--out`` に展開する（v0.16）。``--out`` は空か、まだないこと。展開した木の
    ``kyuura_engine.__version__`` と、展開したコミットを表示する（別のプロセスで読む。この道具がある木の ``kyuura_engine`` を読まない）。"""
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} は空ではない（固定した木を上書きしない）")
    out.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parent.parent
    commit = subprocess.run(["git", "rev-parse", "--verify", f"{args.commit}^{{commit}}"], cwd=repo, check=True, capture_output=True,
                            text=True).stdout.strip()
    archive = out / ".archive.tar"
    with open(archive, "wb") as f:
        subprocess.run(["git", "archive", "--format=tar", commit], cwd=repo, check=True, stdout=f)
    with tarfile.open(archive) as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(out, filter="data")
        else:  # 古い 3.11（自分のリポジトリの git archive なので、展開するのは木のファイルだけ）
            tar.extractall(out)
    archive.unlink()
    probe = f"import sys; sys.path.insert(0, {str(out)!r}); import kyuura_engine; print(kyuura_engine.__version__)"
    version = subprocess.run([sys.executable, "-I", "-c", probe], cwd=out, check=True, capture_output=True, text=True).stdout.strip()
    (out / "FIXED_COMMIT").write_text(f"{commit}\n{version}\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "commit": commit, "version": version}, ensure_ascii=False))
    return 0


def _rerun_without_hash_randomization(argv) -> None:
    """文字列のハッシュの乱数化を止めて起動し直す（PYTHONPATH などの環境の値は渡さない）。"""
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
    env["PYTHONHASHSEED"] = "0"
    os.execve(sys.executable, [sys.executable, "-P", "-s", os.path.abspath(__file__), *argv], env)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="action", required=True)
    r = sub.add_parser("record")
    r.add_argument("--root", required=True)
    r.add_argument("--route", choices=("legacy", "kernel"), default=None)
    r.add_argument("--preflight", default=None)
    r.add_argument("--corpus", choices=("natural", "stress", "all"), default="all")
    r.add_argument("--modules", default="")
    r.add_argument("--scenarios", default="")
    r.add_argument("--seeds", type=int, default=20)
    r.add_argument("--stress-seeds", type=int, default=10)
    r.add_argument("--start", type=int, default=0)
    r.add_argument("--steps", type=int, default=600)
    r.add_argument("--illegal-rate", type=float, default=0.05)
    r.add_argument("--save-every", type=int, default=0)
    r.add_argument("--timing", action="store_true")
    r.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    t = sub.add_parser("tree")
    t.add_argument("--commit", required=True)
    t.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.action == "record" and sys.flags.hash_randomization:
        _rerun_without_hash_randomization(sys.argv[1:] if argv is None else argv)
    return {"record": record, "compare": compare, "tree": tree}[args.action](args)


if __name__ == "__main__":
    raise SystemExit(main())

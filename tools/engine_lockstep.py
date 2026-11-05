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

記録の形式（v0.146。docs/play-set-verification-v0.146.md 2 章。エンジンの状態の書き出しの形式（``state_to_dict`` の 1〜35）とは別の番号）:

- **記録の形式 2**（v0.146 から）: 最初の行が見出し ``{"header": {...}}``（``record_format`` 2・指紋の書き出しの形式 ``digest_format``・規約集合 ``conventions``）。
  ``conventions`` は、記録した木が規約集合を持つ（v0.142 から）なら、対戦に使った集合の識別（ID・版・照合値・構成の規約の ID・版・照合値。``ConventionSetIdentity.record``）、
  持たない木なら None（``conventions_support`` が ``tree_without_conventions``）。集合を持つ木では、対戦の始め・受け付けた歩ごと・保存と復元のあとに、状態の集合がその木の
  登録の内容と合い（``conventions.state_conventions``）、見出しの集合と同じことを確かめ、違えば記録の誤り（``errors``）にする。歩の記録には、状態の集合の識別の指紋 ``k`` を加える
  （``k`` は指紋 ``h`` とは別に比べる）。
- 指紋の書き出しの形式: 今の挙動の集合（と集合を持たない木）は、今までどおり形式 9（前の版の木と比べるため。形式 9 は規約集合の項目を持たず、今の挙動・旧状態用のほかの集合を
  書き出せない）。それ以外の集合（S2a・PO など）は、その木の最新の形式（35）で、規約集合の項目 ``convention_set`` を指紋 ``h`` に含める。形式 35 の書き出しのエンジンの版
  ``engine_version`` だけは ``h`` から除く（版は見出しにある。前の版の木と同じ集合で比べるため）。形式 35 の記録には、``convention_set`` も除いた指紋 ``x`` も加える
  （集合間の比較だけが使う）。``--digest-format`` で形式を指定できる（その形式で集合を書き出せなければ始める前に止める）
- **記録の形式 1**（v0.145 までの道具の記録。見出しがない）: 規約集合の記録がない。その道具は集合を選べず、いつも木の既定で始めた（v0.142 からの木では今の挙動の集合
  CS-KYUURA-CURRENT@1、それより前の木には集合がない）。読みは今までどおり。

``compare`` の契約（v0.146）:

- 形式 2 どうしで集合（見出しの ``conventions``）と指紋の形式が同じなら、今までの比較（``h``・``k``・``x`` をすべて比べる）。集合が違えば、歩を比べる前に拒否する（終了コード 2。
  ID・版・照合値・構成のどれが違うかを書く）。指紋の形式が違っても拒否する
- 意図して異なる集合を比べるときは ``--cross-set`` を付ける（集合が同じなら拒否。両方が形式 35 の指紋の記録だけ）。歩の比べは ``h``・``k`` を除き、``x``（規約集合の項目を除いた
  指紋）・コマンド・受理と拒否で行い、最初の差を報告する。互換性の判定ではないので、終わっても終了コードは 3（0 は同じ集合の一致だけ）
- 形式 1 どうしは今までの比較（どちらにも集合の記録がない）。形式 1 と形式 2 は、形式 2 の側が集合を持たない木（None）で、形式 1 の記録の木の版が 0.142 より前のときだけ比べる。
  形式 1 の記録の木が 0.142 以後なら、``--legacy-as CS-KYUURA-CURRENT@1`` を付け、形式 2 の側がその集合（照合値が v0.142 から固定の値）のときだけ比べる。ほかは拒否（推測で対応付けない）
- 記録の改変（``k`` と見出しが合わない・見出しがない形式 2 の行・知らない形式）は拒否

例::

    python3 tools/engine_lockstep.py record --root /path/to/v013 --corpus natural --seeds 100 --out a.jsonl.gz
    python3 tools/engine_lockstep.py record --root . --route kernel --corpus natural --seeds 100 --out c.jsonl.gz
    python3 tools/engine_lockstep.py record --root . --conventions CS-KYUURA-PLAY-PO@1 --out po.jsonl.gz
    python3 tools/engine_lockstep.py compare a.jsonl.gz c.jsonl.gz
    python3 tools/engine_lockstep.py compare strict.jsonl.gz po.jsonl.gz --cross-set
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

# v0.146: 記録の形式（エンジンの状態の書き出しの形式とは別の番号）。1 は見出しのない v0.145 までの記録
RECORD_FORMAT = 2
KNOWN_RECORD_FORMATS = (1, 2)
LEGACY_DIGEST_FORMAT = 9  # 今の挙動の集合・集合を持たない木の指紋（前の版の木と比べる）
DIGEST_EXCLUDED = ("engine_version",)  # 形式 35 の指紋から除く項目（版は見出しにある）
# 形式 1 の記録（v0.142〜v0.145 の木）が使った既定の集合。照合値は v0.142 から固定（kyuura_engine.conventions.PINNED_SET_DIGESTS。tests/test_lockstep_conventions_v0_146.py が照らす）
LEGACY_DEFAULT_SET = ("CS-KYUURA-CURRENT", 1, "sha256:9a9b95c689d86fa01a5b710984560efda3c08f4dbf1d7c6218094ac8666f3cee")
CONVENTIONS_FROM_VERSION = (0, 142, 0)


class ConventionRecordError(Exception):
    """記録の途中で、状態の規約集合が見出しの集合・木の登録と合わない（記録の誤り。エンジンの拒否ではない）。"""


def conventions_digest(record: dict | None) -> str | None:
    """見出しの集合の識別の指紋（歩の記録の ``k``）。集合を持たない木では None。"""
    if record is None:
        return None
    text = json.dumps(record, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class Recorder:
    def __init__(self, engine, apply, out, *, save_every: int = 0, timing: bool = False, card_data_commit: tuple[str, str] | None = None,
                 conventions_module=None, conventions: dict | None = None, digest_format: int = LEGACY_DIGEST_FORMAT):
        self.engine = engine
        self.digest_format = digest_format
        self.card_data_commit = card_data_commit
        self.apply = apply
        self.out = out
        self.save_every = save_every
        self.timing = timing
        self.game = None
        self.step = 0
        self.counts: Counter = Counter()
        self.times: Counter = Counter()
        # v0.146: 集合を持つ木では、状態の集合を確かめる（conventions_module はその木の kyuura_engine.conventions、conventions は見出しの集合の記録）
        self.conventions_module = conventions_module
        self.conventions = conventions
        self.k = conventions_digest(conventions)

    def check_conventions(self, state) -> None:
        """状態の集合が、その木の登録の内容と合い（``state_conventions``）、見出しの集合と同じか。違えば ``ConventionRecordError``。"""
        if self.conventions_module is None:
            return
        identity, problem = self.conventions_module.state_conventions(state)
        if identity is None:
            raise ConventionRecordError(f"状態の規約集合を、記録した木の登録で確かめられない: {problem}")
        if identity.record() != self.conventions:
            raise ConventionRecordError(f"状態の規約集合 {identity.set_id}@{identity.version} が、記録の見出しの集合と違う")
        self.counts["conventions_checked"] += 1

    def start(self, game: str) -> None:
        self.game = game
        self.step = 0
        self.counts["games"] += 1

    def digest(self, state, *, raw: bool = False, without_conventions: bool = False) -> str:
        data = self.engine.state_to_dict(state, format_version=self.digest_format)
        if self.digest_format > LEGACY_DIGEST_FORMAT:
            for key in DIGEST_EXCLUDED:  # v0.146: エンジンの版（見出しにある）
                data.pop(key, None)
            if without_conventions:
                data.pop("convention_set", None)  # v0.146: 集合間の比較だけが使う指紋 x
        if self.card_data_commit is not None and not raw:
            data = map_card_data_commit(data, *self.card_data_commit)
        text = json.dumps(data, sort_keys=True, ensure_ascii=False, default=repr)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]

    def _digests(self, state) -> dict:
        found = {"h": self.digest(state)}
        if self.digest_format > LEGACY_DIGEST_FORMAT:
            found["x"] = self.digest(state, without_conventions=True)
        if self.card_data_commit is not None:
            found["r"] = self.digest(state, raw=True)  # v0.69: もどす前の指紋（生の構造の違いを数える）
        if self.k is not None:
            self.check_conventions(state)
            found["k"] = self.k  # v0.146: 状態の集合の識別の指紋（確かめたあとの値。見出しの集合と同じ）
        return found

    def initial(self, state) -> None:
        """対戦の始めの状態（``new_game`` の結果。対戦準備の途中で止まった対戦も比べられるように）。"""
        self.out.write(json.dumps({"g": self.game, "i": "init", **self._digests(state)}, ensure_ascii=False) + "\n")

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
            record.update(self._digests(new))
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
            self.check_conventions(new)  # v0.146: 復元した状態の集合も確かめる（次の歩の前）
        return new


def map_card_data_commit(data: dict, new: str, old: str) -> dict:
    """v0.69: 書き出しの写しの元（``card_data.commit``・ログ ``game_created`` の ``card_data_commit``）の 2 か所だけを、確かめた移行の値（``new`` → ``old``）で
    もどした新しい値。ほかの値は変えない。もどす前の値が ``new`` でなければ ``SystemExit``（知らない値を黙って置きかえない）。"""
    result = json.loads(json.dumps(data, default=repr))
    if result.get("card_data", {}).get("commit") != new:
        raise SystemExit(f"card_data.commit が {new} ではない: {result.get('card_data')}")
    result["card_data"]["commit"] = old
    created = [event for event in result.get("log", []) if event.get("kind") == "game_created"]
    if len(created) != 1 or created[0].get("card_data_commit") != new:
        raise SystemExit(f"game_created の card_data_commit が {new} ではない")
    created[0]["card_data_commit"] = old
    return result


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


def tree_conventions(engine, chosen: str | None):
    """v0.146: 記録する木の規約集合。(その木の ``kyuura_engine.conventions``（集合を持たない木では None）, 見出しの集合の記録（None なら集合を持たない木）)。
    ``chosen``（``ID@版``）は、その木の登録で確かめる（知らない・登録の内容と合わない集合は、対戦を始める前に ``SystemExit``）。省略はその木の既定の集合。"""
    try:
        module = importlib.import_module("kyuura_engine.conventions")
    except ModuleNotFoundError:
        if chosen is not None:
            raise SystemExit(f"--root の木（{getattr(engine, '__version__', '?')}）は規約集合を持たないので、--conventions {chosen} を使えない")
        return None, None
    try:
        identity = module.resolve_for_new_game(chosen)
    except module.ConventionSetError as error:
        raise SystemExit(f"--conventions {chosen} をこの木の登録で確かめられない: {error}") from None
    return module, identity.record()


def choose_digest_format(engine, conventions_module, conventions: dict | None, requested: int | None) -> int:
    """v0.146: 指紋の書き出しの形式。指定がなければ、形式 9 で書き出せる集合（その木の ``IMPLICIT_IN_OLD_FORMATS``）・集合を持たない木は 9、ほかはその木の最新の形式。
    指定した形式がその木にない・その形式で集合を書き出せないなら、始める前に ``SystemExit``。"""
    from kyuura_engine import serialize

    versions = tuple(serialize.FORMAT_VERSIONS)
    implicit = conventions is None or (conventions["id"], conventions["version"]) in getattr(conventions_module, "IMPLICIT_IN_OLD_FORMATS", ())
    chosen = requested if requested is not None else (LEGACY_DIGEST_FORMAT if implicit else max(versions))
    if chosen not in versions:
        raise SystemExit(f"--digest-format {chosen} はこの木の書き出しの形式（{versions[0]}〜{versions[-1]}）にない")
    if chosen < max(versions) and not implicit:
        raise SystemExit(f"指紋の形式 {chosen} は、規約集合 {conventions['id']}@{conventions['version']} を書き出せない（形式 {max(versions)} を使う）")
    if chosen != LEGACY_DIGEST_FORMAT and chosen != max(versions):
        raise SystemExit(f"指紋の形式は {LEGACY_DIGEST_FORMAT}（前の版と比べる）か、この木の最新の {max(versions)} だけ")
    return chosen


def _replace_new_game(engine, replacement) -> list:
    """読み込み済みのモジュールが ``new_game`` の名前で持つ木の ``new_game`` を ``replacement`` に置きかえ、もどすための (モジュール, もとの値) の並びを返す。"""
    original = engine.new_game
    replaced = []
    for module in list(sys.modules.values()):
        if module is not None and getattr(module, "new_game", None) is original:
            replaced.append((module, original))
            module.new_game = replacement
    return replaced


def record(args) -> int:
    root = Path(args.root).resolve()
    for path in (root / "tools", root):
        sys.path.insert(0, str(path))
    import kyuura_engine as engine

    loaded = Path(engine.__file__).resolve()
    if root not in loaded.parents:
        raise SystemExit(f"{loaded} は --root {root} の kyuura_engine ではない（python3 -I で実行する）")
    apply = _apply_function(engine, args.route, args.preflight)
    chosen = getattr(args, "conventions", None) or None
    conventions_module, conventions = tree_conventions(engine, chosen)
    new_game_options = {} if chosen is None else {"conventions": chosen}
    digest_format = choose_digest_format(engine, conventions_module, conventions, getattr(args, "digest_format", None))
    opener = gzip.open if args.out.endswith(".gz") else open
    started = time.perf_counter()
    errors = 0
    with opener(args.out, "wt", encoding="utf-8") as out:
        mapping = tuple(args.card_data_commit.split("=")) if args.card_data_commit else None
        if mapping is not None and (len(mapping) != 2 or not all(re.fullmatch(r"[0-9a-f]{40}", c) for c in mapping)):
            raise SystemExit("--card-data-commit は <この木の写しの元>=<比べる木の写しの元>（40 桁の SHA）")
        header = {"record_format": RECORD_FORMAT, "digest_format": digest_format,
                  "digest_excludes": list(DIGEST_EXCLUDED) if digest_format > LEGACY_DIGEST_FORMAT else [], "conventions": conventions,
                  "conventions_support": "recorded" if conventions_module is not None else "tree_without_conventions",
                  "conventions_chosen": chosen, "version": getattr(engine, "__version__", "?")}
        out.write(json.dumps({"header": header}, ensure_ascii=False) + "\n")
        rec = Recorder(engine, apply, out, save_every=args.save_every, timing=args.timing, card_data_commit=mapping,
                       conventions_module=conventions_module, conventions=conventions, digest_format=digest_format)
        if args.corpus in ("natural", "all"):
            modules = args.modules.split(",") if args.modules else NATURAL_MODULES
            for name in modules:
                module = importlib.import_module(f"tests.{name}")
                original = module.apply_command
                original_new_game = getattr(module, "new_game", None)
                module.apply_command = rec
                replaced = []
                if new_game_options:
                    # v0.146: 対戦のテストが別のモジュール（tests.helpers など）を通して new_game を呼んでも、選んだ集合で始める（漏れは状態の集合の確かめが見つける）
                    def chosen_new_game(*a, _new_game=engine.new_game, **k):
                        return _new_game(*a, **{**new_game_options, **k})
                    replaced = _replace_new_game(engine, chosen_new_game)
                if original_new_game is not None:
                    current_new_game = module.new_game  # 選んだ集合で始める関数に置きかえたあとの値

                    def recorded_new_game(*a, _new_game=current_new_game, **k):
                        state = _new_game(*a, **k)
                        rec.initial(state)
                        return state
                    module.new_game = recorded_new_game
                try:
                    for seed in range(args.start, args.start + args.seeds):
                        rec.start(f"natural:{name}:{seed}")
                        try:
                            module.play_game(seed)
                        except Exception as error:  # 対戦のテスト自身の確認（不変条件・監査）の失敗・規約集合の記録の誤りも記録する
                            errors += 1
                            out.write(json.dumps({"g": rec.game, "error": f"{type(error).__name__}: {str(error)[:300]}"}, ensure_ascii=False) + "\n")
                finally:
                    module.apply_command = original
                    if original_new_game is not None:
                        module.new_game = original_new_game
                    for other, value in replaced:
                        if other is not module:
                            other.new_game = value
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
                    try:
                        state = engine.new_game(driver._deck(spec.deck0), driver._deck(spec.deck1), seed, **new_game_options)
                        rec.initial(state)
                        for _ in range(args.steps):
                            if state.phase in engine.TERMINAL_PHASES:
                                break
                            command = stress.choose_command(state, rng, args.illegal_rate)
                            try:
                                state = rec(state, command)
                            except engine.EngineError:
                                continue
                    except ConventionRecordError as error:  # v0.146: 規約集合の記録の誤り（この対戦の記録をやめる。エンジンの拒否ではない）
                        errors += 1
                        out.write(json.dumps({"g": rec.game, "error": f"{type(error).__name__}: {str(error)[:300]}"}, ensure_ascii=False) + "\n")
        summary = {"summary": dict(rec.counts), "errors": errors, "elapsed": round(time.perf_counter() - started, 1),
                   "root": str(root), "route": args.route, "preflight": args.preflight, "version": getattr(engine, "__version__", "?"),
                   "hash_randomization": sys.flags.hash_randomization, "card_data_commit": args.card_data_commit or None,
                   "record_format": RECORD_FORMAT, "conventions": None if conventions is None else f"{conventions['id']}@{conventions['version']}"}
        if args.timing:
            summary["times_ms"] = {k: round(v / rec.counts[f"time_n:{k}"] * 1000, 4) for k, v in rec.times.items()}
            summary["times_total_s"] = {k: round(v, 4) for k, v in rec.times.items()}
        out.write(json.dumps(summary, ensure_ascii=False) + "\n")
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if errors else 0


def _read(path: str):
    """記録を読む。(対戦の並び, 対戦ごとの歩, 終わりの集計, 見出し（形式 1 は None）)。v0.146: 見出しは最初の行だけ（途中の見出しは記録の誤り）。"""
    opener = gzip.open if path.endswith(".gz") else open
    games: dict[str, list] = {}
    order: list[str] = []
    summary = None
    header = None
    with opener(path, "rt", encoding="utf-8") as f:
        for number, line in enumerate(f):
            item = json.loads(line)
            if "header" in item:
                if number != 0:
                    raise RecordFormatError(f"{path}: 見出しが最初の行にない（{number + 1} 行目）")
                header = item["header"]
                continue
            if "summary" in item:
                summary = item
                continue
            game = item["g"]
            if game not in games:
                games[game] = []
                order.append(game)
            games[game].append(item)
    return order, games, summary, header


class RecordFormatError(Exception):
    """記録の形式・改変の誤り（比べる前に拒否する）。"""


def _version_tuple(text) -> tuple[int, ...] | None:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", str(text or ""))
    return tuple(int(x) for x in match.groups()) if match else None


def record_conventions(path: str, games: dict, summary: dict | None, header: dict | None) -> dict:
    """v0.146: 記録の集合の扱い。``{"format": 1|2, "conventions": 見出しの集合（形式 1 は None）, "version": 木の版}``。形式・改変の誤りは ``RecordFormatError``。

    - 形式 2: 見出しの ``record_format`` が 2、``digest_format`` が 9、``conventions`` が集合の記録か None（集合を持たない木）。歩の記録の ``k`` は、見出しの集合の指紋と同じ
      （集合を持たない木では ``k`` がない）。終わりの集計の ``conventions`` も見出しと同じ
    - 形式 1: 見出しがなく、どの歩にも ``k`` がない"""
    if header is None:
        if any("k" in item for items in games.values() for item in items):
            raise RecordFormatError(f"{path}: 見出しのない記録に、集合の指紋 k の歩がある（形式 1 の記録ではない。見出しが失われた可能性）")
        return {"format": 1, "conventions": None, "version": (summary or {}).get("version"), "digest_format": LEGACY_DIGEST_FORMAT}
    fmt = header.get("record_format")
    if fmt not in KNOWN_RECORD_FORMATS or fmt == 1:
        raise RecordFormatError(f"{path}: 知らない記録の形式 {fmt!r}")
    digest_format = header.get("digest_format")
    if not isinstance(digest_format, int) or digest_format < LEGACY_DIGEST_FORMAT:
        raise RecordFormatError(f"{path}: 指紋の書き出しの形式 {digest_format!r} を知らない")
    with_x = digest_format > LEGACY_DIGEST_FORMAT
    if header.get("digest_excludes", []) != (list(DIGEST_EXCLUDED) if with_x else []):
        raise RecordFormatError(f"{path}: 指紋から除いた項目 {header.get('digest_excludes')!r} が、この道具の決まり（{list(DIGEST_EXCLUDED) if with_x else []}）と違う")
    conventions = header.get("conventions")
    if conventions is not None and not (isinstance(conventions, dict) and {"id", "version", "digest", "members"} <= set(conventions)):
        raise RecordFormatError(f"{path}: 見出しの集合の記録の形が違う")
    expected = conventions_digest(conventions)
    for game, items in games.items():
        for item in items:
            if "error" in item:
                continue
            if "h" not in item:
                # 拒否された歩（状態がない）は指紋 h も集合の指紋 k も持たない（v0.146 の確かめで分かった。k は h のある歩だけに書く）
                if "k" in item or "x" in item:
                    raise RecordFormatError(f"{path}: {game} 歩 {item.get('i')} に、状態の指紋 h がないのに k か x がある")
                continue
            if item.get("k") != expected:
                raise RecordFormatError(f"{path}: {game} 歩 {item.get('i')} の集合の指紋 k が見出しの集合と合わない（記録の改変か、集合の違う対戦）")
            if ("h" in item) != ("x" in item) and with_x:
                raise RecordFormatError(f"{path}: {game} 歩 {item.get('i')} に、形式 {digest_format} の指紋 x がない")
            if "x" in item and not with_x:
                raise RecordFormatError(f"{path}: {game} 歩 {item.get('i')} に、形式 9 の記録にない指紋 x がある")
    named = None if conventions is None else f"{conventions['id']}@{conventions['version']}"
    if summary is not None and summary.get("conventions") != named:
        raise RecordFormatError(f"{path}: 終わりの集計の集合 {summary.get('conventions')!r} が見出しの集合 {named!r} と違う")
    return {"format": 2, "conventions": conventions, "version": header.get("version"), "digest_format": digest_format}


def conventions_difference(a: dict | None, b: dict | None) -> str | None:
    """2 つの見出しの集合の違い（同じなら None）。"""
    if a == b:
        return None
    if a is None or b is None:
        return "一方は集合を持たない木の記録、もう一方は集合の記録がある"
    for field, label in (("id", "集合の ID"), ("version", "集合の版"), ("digest", "集合の照合値"), ("members", "構成の規約（ID・版・照合値）")):
        if a.get(field) != b.get(field):
            shown = (a.get(field), b.get(field)) if field != "members" else ("…", "…")
            return f"{label}が違う（{shown[0]} / {shown[1]}）"
    return "集合の記録のほかの項目が違う"


def pairing_problem(ca: dict, cb: dict, *, cross_set: bool, legacy_as: str | None) -> str | None:
    """v0.146: 2 つの記録を比べてよいか。比べてよければ None、拒否する理由の文。"""
    problem = _pairing_conventions_problem(ca, cb, cross_set=cross_set, legacy_as=legacy_as)
    if problem is None and ca["digest_format"] != cb["digest_format"]:
        problem = f"指紋の書き出しの形式が違う（{ca['digest_format']} / {cb['digest_format']}。同じ形式で記録し直す。--digest-format）"
    return problem


def _pairing_conventions_problem(ca: dict, cb: dict, *, cross_set: bool, legacy_as: str | None) -> str | None:
    """集合の扱い（指紋の形式の前に確かめる。違う集合は、集合の違いを理由に拒否する）。"""
    legacy_key = f"{LEGACY_DEFAULT_SET[0]}@{LEGACY_DEFAULT_SET[1]}"
    if ca["format"] == 2 and cb["format"] == 2:
        difference = conventions_difference(ca["conventions"], cb["conventions"])
        if legacy_as:
            return "--legacy-as は形式 1 の記録を比べるときだけ"
        if cross_set:
            if difference is None:
                return "--cross-set は異なる集合の比較だけ（2 つの記録の集合は同じ。通常の比較をする）"
            if ca["conventions"] is None or cb["conventions"] is None:
                return f"集合を持たない木の記録とは、集合間の比較もしない（{difference}）"
            if LEGACY_DIGEST_FORMAT in (ca["digest_format"], cb["digest_format"]):
                return "集合間の比較は、規約集合の項目を除いた指紋 x のある記録（形式 35 の指紋）どうしだけ（--digest-format 35 で記録する）"
            return None
        return None if difference is None else f"規約集合が違う記録は、通常の比較をしない: {difference}（意図した集合間の比較は --cross-set）"
    if cross_set:
        return "--cross-set は形式 2 の記録どうしだけ（形式 1 の記録には集合の記録がない）"
    if ca["format"] == 1 and cb["format"] == 1:
        return None if not legacy_as else "--legacy-as は形式 1 と形式 2 を比べるときだけ"
    old, new = (ca, cb) if ca["format"] == 1 else (cb, ca)
    old_version = _version_tuple(old["version"])
    if old_version is None:
        return f"形式 1 の記録の木の版 {old['version']!r} が読めない（どの集合の記録か決められない）"
    if old_version < CONVENTIONS_FROM_VERSION:
        if new["conventions"] is not None:
            return f"形式 1 の記録は集合を持たない木（{old['version']}）のもの。集合の記録がある形式 2 の記録とは比べない"
        return None if not legacy_as else "--legacy-as は、形式 1 の記録の木が 0.142.0 以後のときだけ"
    if not legacy_as:
        return (f"形式 1 の記録（木 {old['version']}）には集合の記録がない。木の既定の集合で記録したことを前提に比べるなら "
                f"--legacy-as {legacy_key} を付ける（推測で対応付けない）")
    if legacy_as != legacy_key:
        return f"--legacy-as は {legacy_key} だけ（形式 1 の道具は集合を選べず、木の既定で記録した）"
    conventions = new["conventions"]
    if conventions is None or (conventions["id"], conventions["version"], conventions["digest"]) != LEGACY_DEFAULT_SET:
        return f"形式 2 の記録の集合が {legacy_key}（照合値 {LEGACY_DEFAULT_SET[2]}）ではない"
    return None


def _without(games: dict, fields: tuple[str, ...]) -> dict:
    return {g: [{k: v for k, v in item.items() if k not in fields} for item in items] for g, items in games.items()}


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
    """2 つの記録を比べる。終了コード: 0 同じ集合で食い違いなし・1 食い違いあり・2 比べる前に拒否（集合の不一致・形式・改変）・3 意図した集合間の比較を終えた（互換性の判定ではない）。"""
    cross_set = getattr(args, "cross_set", False)
    legacy_as = getattr(args, "legacy_as", None) or None
    try:
        order_a, a, sa, ha = _read(args.a)
        order_b, b, sb, hb = _read(args.b)
        ca, cb = record_conventions(args.a, a, sa, ha), record_conventions(args.b, b, sb, hb)
    except RecordFormatError as error:
        print(f"REFUSED 記録の形式: {error}")
        return 2
    for label, c in (("a", ca), ("b", cb)):
        named = "記録なし" if c["format"] == 1 else "集合を持たない木" if c["conventions"] is None else (
            f"{c['conventions']['id']}@{c['conventions']['version']} {c['conventions']['digest']}")
        print(f"{label} 記録の形式 {c['format']}・木 {c['version']}・規約集合 {named}")
    problem = pairing_problem(ca, cb, cross_set=cross_set, legacy_as=legacy_as)
    if problem is not None:
        print(f"REFUSED {problem}")
        return 2
    if cross_set:
        print("集合間の比較（互換性の判定ではない。歩の比べは、規約集合の項目を除いた指紋 x・コマンド・受理と拒否で行い、h・k を除く）")
        a, b = _without(a, ("h", "k")), _without(b, ("h", "k"))
    elif ca["format"] != cb["format"]:
        print(f"形式 1 と形式 2 の比較（{'--legacy-as ' + legacy_as if legacy_as else '集合を持たない木どうし'}）。形式 2 の記録の集合の指紋 k を除いて比べる")
        a, b = _without(a, ("k",)), _without(b, ("k",))
    divergences = 0
    steps = 0
    allowed: Counter = Counter()
    examples: list[str] = []
    if order_a != order_b:
        print(f"対戦の並びが違う（{len(order_a)} と {len(order_b)}）")
        divergences += 1
    raw: Counter = Counter()
    for game in order_a:
        ra, rb = a.get(game, []), b.get(game, [])
        # v0.69: 写しの元をもどした記録（record の --card-data-commit）は、もどした指紋（h）で比べ、もどす前の指紋（r）と相手の指紋の違いを数える
        for xs, ys in ((ra, rb), (rb, ra)):
            for x, y in zip(xs, ys):
                if "r" in x:
                    raw["steps_with_raw"] += 1
                    raw["raw_differs"] += x["r"] != y.get("h")
        ra = [{k: v for k, v in item.items() if k != "r"} for item in ra]
        rb = [{k: v for k, v in item.items() if k != "r"} for item in rb]
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
    if raw:
        print(f"写しの元をもどして比べた歩 {raw['steps_with_raw']}（もどす前の指紋が相手と違った歩 {raw['raw_differs']}）")
    for label, s in (("a", sa), ("b", sb)):
        if s is not None:
            print(label, json.dumps({k: s.get(k) for k in ("root", "route", "preflight", "version", "elapsed", "errors", "card_data_commit", "conventions")},
                                    ensure_ascii=False))
    if cross_set:
        print(f"集合間の比較を終えた（差のある対戦 {divergences}。互換性の判定ではない）")
        return 3
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
    r.add_argument("--card-data-commit", default="", help="v0.69: <この木の写しの元>=<比べる木の写しの元>。書き出しの写しの元の 2 か所だけをもどして指紋をとる")
    r.add_argument("--conventions", default=None, help="v0.146: 対戦を始める規約集合（ID@版）。省略は木の既定。集合を持たない木では使えない")
    r.add_argument("--digest-format", type=int, default=None,
                   help="v0.146: 指紋の書き出しの形式（9 か木の最新）。省略は、今の挙動の集合なら 9、ほかの集合なら木の最新")
    r.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    c.add_argument("--cross-set", action="store_true", help="v0.146: 意図して異なる規約集合の記録を比べる（互換性の判定ではない。終了コード 3）")
    c.add_argument("--legacy-as", default=None, help="v0.146: 形式 1（集合の記録がない）の記録を、木の既定の集合 CS-KYUURA-CURRENT@1 の記録として比べる")
    t = sub.add_parser("tree")
    t.add_argument("--commit", required=True)
    t.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.action == "record" and sys.flags.hash_randomization:
        _rerun_without_hash_randomization(sys.argv[1:] if argv is None else argv)
    return {"record": record, "compare": compare, "tree": tree}[args.action](args)


if __name__ == "__main__":
    raise SystemExit(main())

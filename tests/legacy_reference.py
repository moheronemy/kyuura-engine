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
from dataclasses import dataclass
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

@dataclass(frozen=True)
class RuleChangedChain:
    """v0.140 の規約の変更で、記録と全体では比べられなくなった対戦の登録（docs/prize-order-v0140-cleanup-v0.141.md 2 章）。v0.141 から、次をすべて確かめる（記録と違うことだけを
    成功の条件にしない。``check_rule_changed_chain``）。

    - ``prize_first``: その対戦で、先にサイドを取るプレイヤーの決定（prize_first）を待つ状態に送ったコマンドの列（歩の番号・コマンド）。ほかの歩にその決定が出る・答えが違えば失敗
    - 従来の順で答えたやり直し（``previous_order_replay``）: prize_first に番のプレイヤー（v0.139 までの、すべてうらのときの順番と同じ）で答え、方策の乱数を使わずに進め、規約の
      変更が加えた項目（決定の番号・サイドの決定の ``first``）だけを記録の形にもどした連なりが、記録と同じでなければ失敗（規約の変更で説明できない差がある）
    - ``first_difference``: 記録と違いはじめる歩（その決定を出した歩）。そこより前の歩は、やり直しと同じでなければ失敗。その歩は、やり直しと違わなければ失敗
    ``first_difference`` より後の歩は、方策がその決定に乱数で答えた（取る順番も変わりうる）別の対戦で、記録と比べない（derived・legacy の lockstep・不変条件だけ）。"""

    reason: str
    convention: str
    game: tuple  # ("stress", 組の名前, seed, 歩の数, 拒否されるコマンドの割合)。tools/event_kernel_compare.py の stress_game と同じ
    prize_first: tuple  # ((歩の番号, コマンドの dict), ...)
    first_difference: int


# v0.140（docs/prize-order-user-rule-v0.140.md 7 章）・v0.141: 利用者の指定（USER-PRIZE-ORDER-ALWAYS-CHOSEN）で、両方がサイドを取るときにいつも先に取るプレイヤーの決定（prize_first）を
# 出すようになり、旧経路（v0.13）の記録と全体では比べられなくなった対戦。記録（fixtures/legacy_reference_v0_15.json）は変えない・作り直さない
RULE_CHANGED_CHAINS: dict[str, RuleChangedChain] = {
    "tests.test_event_kernel_games_v0_14.LockstepGamesTest.test_stress_scenarios_in_both_modes_with_mixed_states:stress:wartortle_mixed:0": RuleChangedChain(
        reason="両方がサイドを取る場面（歩 259 のワザの結果）に prize_first の決定が加わり、stress の選び方が乱数でその決定に答える（番のプレイヤー 1 が相手 0 を選んだ。従来と違う"
               "取る順番）ので、歩 260 から先は別の対戦になる",
        convention="CONV:USER-PRIZE-ORDER-ALWAYS-CHOSEN",
        game=("stress", "wartortle_mixed", 0, 400, 0.05),
        prize_first=((260, {"type": "resolve_decision", "player": 1, "decision": 12, "choices": [0]}),),
        first_difference=259,
    ),
}


def _previous_order_form(data: dict, answered: int, first: int | None) -> dict:
    """規約の変更が加えた項目だけを、v0.139 までの形にもどす（``RuleChangedChain`` のやり直しの比べ。ほかの項目は除かない・変えない）。

    - 次に付ける決定の番号・待っている決定の番号: それまでに答えた prize_first の数（``answered``）だけ小さくする
    - 待っているサイドの決定の ``context`` の ``("first", 番のプレイヤー)``: 除く（やり直しは番のプレイヤーで答えるので、ほかの値なら失敗）"""
    data = dict(data, next_decision_id=data["next_decision_id"] - answered)
    decision = data.get("decision")
    if decision is not None:
        decision = dict(decision, id=decision["id"] - answered)
        if decision["kind"] == "take_prize" and "first" in decision["context"]:
            context = dict(decision["context"])  # 書き出しの形では名前 → 値（serialize.py）
            if context.pop("first") != first:
                raise AssertionError(f"やり直しのサイドの決定の先に取るプレイヤー {decision['context']['first']} が、番のプレイヤー {first} と違う")
            decision["context"] = context
        data["decision"] = decision
    return data


def _previous_order_digest(state, answered: int) -> str:
    data = _previous_order_form(with_card_data_commit_before_v0_69(state_to_dict(state, format_version=9)), answered, state.current_player)
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, default=repr).encode("utf-8")).hexdigest()[:32]


def _previous_order_input(state, command, answered: int) -> str:
    given = command_to_dict(command)
    if answered and isinstance(given.get("decision"), int):
        given = dict(given, decision=given["decision"] - answered)
    data = json.dumps([_previous_order_digest(state, answered), rng_fingerprint(state.rng), given], sort_keys=True, ensure_ascii=False, default=repr)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:32]


class PreviousOrderReplay:
    """``RuleChangedChain`` の対戦を、prize_first に番のプレイヤー（従来の順番）で答えて進める（``tools/event_kernel_compare.stress_game`` に比べる関数のかわりに渡す）。
    その決定はその場で答え、方策の乱数を使わず、歩に数えない。歩の連なりは、規約の変更が加えた項目だけを記録の形にもどして作る（``_previous_order_form``）。"""

    def __init__(self, apply):
        self.apply = apply
        self.counts: Counter = Counter()
        self.rows: list[tuple] = []
        self.answered = 0
        self._hash = hashlib.sha256()

    def begin(self, game: str) -> None:
        pass

    def end(self) -> None:
        pass

    def value(self) -> dict:
        return {"steps": len(self.rows), "digest": self._hash.hexdigest()[:32]}

    def _add(self, row: tuple) -> None:
        self.rows.append(row)
        self._hash.update(json.dumps([row[0], list(row[1])], ensure_ascii=False).encode("utf-8"))

    def __call__(self, state, command):
        if state.decision is not None and state.decision.kind == "prize_first":
            raise AssertionError("やり直しで、方策が prize_first に答えようとした（その場で答えるはず）")
        given = _previous_order_input(state, command, self.answered)
        try:
            new = self.apply(state, command)
        except EngineError as error:
            self._add((given, error_outcome(error)))
            raise
        if new.decision is not None and new.decision.kind == "prize_first":
            from kyuura_engine import ResolveDecision
            new = self.apply(new, ResolveDecision(new.decision.player, new.decision.id, (new.current_player,)))
            self.answered += 1
        self._add((given, ("ok", _previous_order_digest(new, self.answered))))
        return new


def previous_order_replay(rule: RuleChangedChain, apply=None) -> PreviousOrderReplay:
    """``rule`` の対戦の、従来の順のやり直し（``tools`` を ``sys.path`` に置いたテストから呼ぶ）。``apply`` はテストが処理を差しかえるときだけ渡す。"""
    import event_kernel_compare as compare
    import stress_engine as stress

    kind, name, seed, steps, illegal_rate = rule.game
    if kind != "stress":
        raise AssertionError(f"やり直しの対戦の種類 {kind} は扱えない")
    from kyuura_engine import apply_command
    replay = PreviousOrderReplay(apply or apply_command)
    compare.stress_game(replay, next(s for s in stress.ALL_SCENARIOS if s.name == name), seed, steps=steps, illegal_rate=illegal_rate)
    return replay


def check_rule_changed_chain(chain: Chain, rule: RuleChangedChain, entry: dict, value: dict, replay: PreviousOrderReplay) -> None:
    """``RuleChangedChain`` の確かめ（``Chain.finish`` から。テストが値を変えて、無関係な差を許さないことを確かめるためにも呼ぶ）。"""
    label = chain.label
    if list(chain.prize_first) != [(step, dict(command)) for step, command in rule.prize_first]:
        raise AssertionError(f"対戦 {label} の prize_first の歩・答え {chain.prize_first} が、登録 {rule.prize_first} と違う")
    if entry == value:
        raise AssertionError(f"対戦 {label} は記録と同じ（RULE_CHANGED_CHAINS から外す）")
    previous = replay.value()
    if previous != entry:
        raise AssertionError(f"対戦 {label} の従来の順のやり直しが旧経路の記録と違う（記録 {entry}、やり直し {previous}）。規約の変更で説明できない差")
    n = rule.first_difference
    if chain.rows[:n] != replay.rows[:n]:
        bad = next(i for i, (a, b) in enumerate(zip(chain.rows, replay.rows)) if a != b)
        raise AssertionError(f"対戦 {label} が、登録した違いはじめる歩 {n} より前の歩 {bad} で、従来の順のやり直しと違う")
    if len(chain.rows) <= n or len(replay.rows) <= n or chain.rows[n] == replay.rows[n]:
        raise AssertionError(f"対戦 {label} が、登録した違いはじめる歩 {n} で、従来の順のやり直しと違わない（登録を確かめる）")


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
        self.prize_first: list[tuple] = []  # v0.140・v0.141: prize_first を待つ状態に送ったコマンド（歩の番号・コマンドの dict）。RULE_CHANGED_CHAINS の確かめ
        self.rows: list[tuple] = []  # v0.141: 歩ごとの（盤面の指紋, 結果）。RULE_CHANGED_CHAINS の対戦で、違いはじめる歩より前を比べる

    @property
    def saw_prize_first(self) -> bool:
        return bool(self.prize_first)

    def add(self, state, command, result: tuple) -> None:
        if state.decision is not None and state.decision.kind == "prize_first":
            self.prize_first.append((self.steps, command_to_dict(command)))
        given = input_digest(state, command)
        self.rows.append((given, tuple(result)))
        self._hash.update(json.dumps([given, list(result)], ensure_ascii=False).encode("utf-8"))
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
        if self.label in RULE_CHANGED_CHAINS:
            rule = RULE_CHANGED_CHAINS[self.label]
            check_rule_changed_chain(self, rule, entry, value, previous_order_replay(rule))
            return
        if self.saw_prize_first:
            raise AssertionError(f"対戦 {self.label} が先にサイドを取るプレイヤーの決定を通るのに、RULE_CHANGED_CHAINS にない（比べる意味を確かめて加える）")
        if entry != value:
            raise AssertionError(f"対戦 {self.label} の結果の連なりが旧経路の記録と違う（記録 {entry}、今 {value}）")


def legacy_apply_for_recording(state, command):
    """記録するときの旧経路（``Chain`` を使う比べる関数が、記録するときに基準として使う）。"""
    return _legacy_apply(state, command)

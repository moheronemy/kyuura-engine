"""途中停止（v0.127。docs/deferred-shortage-user-promos-v0.127.md 5 章・6 章）。

コマンドの結果は 3 つに分ける:

- 従来の拒否: ``IllegalActionError``・``UnsupportedError``。入力の状態・乱数・ログは変わらず、別の合法な操作を選べる
- 通常の受理: 正常な次の状態
- 途中停止: 共通の数量処理の **明示的なチェック地点**（``check_quantity``）で、説明の数（コインの「おもて」の数）が処理できる数より多いと分かったとき。実際のコインと、そこまでに
  一意に決まった処理を残した **終端の状態**（``Phase.HALTED`` と ``Halt.interruption``）を返す。再試行・別のワザ・裁定を選んでの再開はできない

途中停止にしてよいのは、チェック地点までの処理がどの読み方でも同じで、足りない要素をまだ処理しておらず、数を知るのに秘密の情報を使っていない地点だけ。チェック地点は
``DeferredShortage`` を投げ、コマンドの入口（``engine._apply_once``）だけがこれを捕まえて終端の状態にする。一般の ``UnsupportedError``・``OpenQuestion``・内部エラーは捕まえない
（``DeferredShortage`` はそのどれの子でもない）。宣言の前の先読み（``resolution.preflight.explore``）は、チェック地点の終端を問いでも完了でもない終端の枝として数える（その枝が
あることだけで宣言を拒否しない）。

止めたときは、不足する要素を処理しない（あるだけ処理する・失敗として番を終える・効果なしで続ける、のどれにも決めない）。使用中のトレーナー・固定した変身の姿はそのまま在途として
残し、番・ポケモンチェック・サイドを進めない。公式の裁定を決めたのではない（kyuura の UQ-STATED-COUNT-SHORT は未解決のまま）。
"""

from __future__ import annotations

from collections.abc import Callable

from .state import GameState, Halt, Interruption, Phase

# 中断の種類（``Interruption.kind``）。今は説明の枚数に足りない場合（kyuura の UQ-STATED-COUNT-SHORT）だけ
STATED_COUNT_SHORT = "stated_count_short"
STATED_COUNT_SHORT_ISSUE = "UQ-STATED-COUNT-SHORT"

# 止まった要素（``Interruption.element``）と、その要素の処理できる数を今の状態から数え直す関数（不変条件・監査が使う。止めたあとは場が変わらないので、止めたときの数と同じ）。
# 数え方は要素の実装と同じ関数（``effects.attached_typed_energy_cards``・場のエネルギーカード）
DISCARD_WATER_ENERGY_CARDS = "discard_water_energy_cards"  # ドライアップ（選んだポケモンの「水」エネルギーカードをトラッシュ）
RETURN_ENERGY_CARDS_TO_HAND = "return_energy_cards_to_hand"  # 怪電波マシーン（相手の対戦ポケモンのエネルギーカードを相手の手札にもどす）


def _water_energy_cards(state: GameState, pokemon) -> int:
    from .cards import EnergyType
    from .effects import attached_typed_energy_cards

    return len(attached_typed_energy_cards(state, pokemon, EnergyType.WATER))


def _energy_cards(state: GameState, pokemon) -> int:
    return len([uid for uid in pokemon.energy if state.card_def(uid).category == "energy"])


ELEMENT_COUNTS: dict[str, Callable[[GameState, object], int]] = {
    DISCARD_WATER_ENERGY_CARDS: _water_energy_cards,
    RETURN_ENERGY_CARDS_TO_HAND: _energy_cards,
}


class DeferredShortage(Exception):  # 終端の状態にする印（エラーではない。``UnsupportedError`` の子にしない）
    """チェック地点で、説明の数が処理できる数より多いと分かった（``check_quantity`` だけが投げる）。``engine._apply_once`` が捕まえて終端の状態にする。ほかの場所では捕まえない
    （先読みの ``explore``・答えの続きを試す確かめは、終端の枝・受け付けられる答えとして数えるだけ）。"""

    def __init__(self, *, code: str, message: str, references: tuple[str, ...], source: str, player: int, target_owner: int, target: int,
                 element: str, required: int, available: int, pending: tuple[str, ...], kind: str = STATED_COUNT_SHORT,
                 kyuura_issue: str = STATED_COUNT_SHORT_ISSUE):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.references = references
        self.kind = kind
        self.kyuura_issue = kyuura_issue
        self.source = source
        self.player = player
        self.target_owner = target_owner
        self.target = target
        self.element = element
        self.required = required
        self.available = available
        self.pending = pending


def check_quantity(*, required: int, available: int, **fields) -> None:
    """共通の数量処理の明示的なチェック地点（v0.127）。説明の数 ``required`` が処理できる数 ``available`` より多ければ ``DeferredShortage`` を投げる（その要素を処理する前）。
    ``required`` ≤ ``available`` なら何もしない（呼ぶ側が、ちょうど ``required`` 枚の選び方をすべて残して処理する）。``fields`` は ``DeferredShortage`` の残りの項目。"""
    if type(required) is not int or type(available) is not int or required < 0 or available < 0:
        raise RuntimeError(f"数量のチェック地点の数 {required!r}・{available!r} が 0 以上の整数ではない（エンジンの不具合）")
    if fields.get("element") not in ELEMENT_COUNTS:
        raise RuntimeError(f"数量のチェック地点の要素 {fields.get('element')!r} が、途中停止を許す要素ではない（エンジンの不具合）")
    if required > available:
        raise DeferredShortage(required=required, available=available, **fields)


def in_transit_cards(state: GameState) -> tuple[int, ...]:
    """在途のカード: 外側のトレーナーの使用（``trainer_stack``。外側から順）と、使用中のトレーナー（``trainer_in_use``）。"""
    return tuple(use.card for use in state.trainer_stack) + (() if state.trainer_in_use is None else (state.trainer_in_use.card,))


def interrupt(state: GameState, shortage: DeferredShortage) -> None:
    """``state``（コマンドの処理の途中の複製）を、途中停止の終端の状態にする。決定・まだ処理していない場の移動の反応が残っていればエンジンの不具合（チェック地点ではない）。
    在途のカード・固定した変身の姿は動かさない。ログの最後に ``halted``（公開の項目: 中断の種類・発生元・止まった要素・必要な数・処理できる数・対象）。"""
    if state.decision is not None or state.pending_moves or state.phase is Phase.HALTED:
        raise RuntimeError(f"途中停止 {shortage.code} の時点に、決定・まだ処理していない反応・停止が残っている（チェック地点ではない。エンジンの不具合）")
    record = Interruption(kind=shortage.kind, code=shortage.code, kyuura_issue=shortage.kyuura_issue, source=shortage.source, player=shortage.player,
                          target_owner=shortage.target_owner, target=shortage.target, element=shortage.element, required=shortage.required,
                          available=shortage.available, pending=tuple(shortage.pending), in_transit=in_transit_cards(state), log_index=len(state.log))
    state.phase = Phase.HALTED
    state.halt = Halt(code=shortage.code, message=shortage.message, references=tuple(shortage.references), interruption=record)
    state.add_event("halted", code=shortage.code, interrupted=record.kind, source=record.source, player=record.player, element=record.element,
                    required=record.required, available=record.available, target_owner=record.target_owner, target=record.target)


def public_record(record: Interruption) -> dict:
    """観測・書き出しの形（全員に見える項目だけ。診断用の文 ``Halt.message`` は書かない）。"""
    return {"kind": record.kind, "code": record.code, "kyuura_issue": record.kyuura_issue, "source": record.source, "player": record.player,
            "target_owner": record.target_owner, "target": record.target, "element": record.element, "required": record.required,
            "available": record.available, "pending": list(record.pending), "in_transit": list(record.in_transit), "log_index": record.log_index}


def interruption_problems(state: GameState) -> list[str]:
    """途中停止の終端の状態だけの不変条件（``engine.check_invariants`` が ``Halt.interruption`` のあるときに呼ぶ。通常の停止の条件は緩めない）。

    - 停止コードが記録と同じ。種類・要素が知っているもの。必要な数 > 処理できる数 ≥ 0
    - 在途のカードが、使用中のトレーナー・外側の使用のカードとちょうど同じ（ほかに残ったカードはない。カードの保存則は全体の確かめが数える）
    - 対象の場のポケモンが記録の持ち主の場にいて、処理できる数が今の状態で数え直した数と同じ（足りない要素を処理していない）
    - ログ: 記録の位置がちょうど最後の ``halted``（このあとに処理がない）。その直前が「うら」が出るまで投げたコインの最後の「うら」で、その一まとまりの「おもて」の数が必要な数
      （コインを打ち切っていない・丸めていない）
    """
    halt = state.halt
    record = halt.interruption
    problems: list[str] = []
    if not isinstance(record, Interruption):
        return [f"途中停止の記録 {record!r} が Interruption ではない"]
    if halt.code != record.code:
        problems.append(f"止めた理由のコード {halt.code} が、途中停止の記録のコード {record.code} と違う")
    if record.kind != STATED_COUNT_SHORT or record.kyuura_issue != STATED_COUNT_SHORT_ISSUE:
        problems.append(f"途中停止の種類 {record.kind!r}・論点 {record.kyuura_issue!r} が知っているものではない")
    if record.element not in ELEMENT_COUNTS:
        problems.append(f"途中停止の要素 {record.element!r} が、途中停止を許す要素ではない")
    numbers = (record.required, record.available, record.player, record.target_owner, record.target, record.log_index)
    if any(type(value) is not int for value in numbers):
        return problems + [f"途中停止の記録の数 {numbers!r} が整数ではない"]
    if not record.required > record.available >= 0:
        problems.append(f"途中停止の必要な数 {record.required} が、処理できる数 {record.available} より多くない")
    if record.player not in (0, 1) or record.target_owner not in (0, 1):
        problems.append(f"途中停止のプレイヤー {record.player}・対象の持ち主 {record.target_owner} が正しくない")
    if not isinstance(record.pending, tuple) or not record.pending or any(not isinstance(step, str) or not step for step in record.pending):
        problems.append(f"途中停止の未完了の処理 {record.pending!r} が空でない文字列の並びではない")
    if record.in_transit != in_transit_cards(state):
        problems.append(f"途中停止の在途のカード {record.in_transit} が、使用中のトレーナー・外側の使用のカード {in_transit_cards(state)} と違う")
    found = state.find_pokemon(record.target)
    if found is None or found[0] != record.target_owner:
        problems.append(f"途中停止の対象 {record.target} が、プレイヤー {record.target_owner} の場にいない")
    elif record.element in ELEMENT_COUNTS and ELEMENT_COUNTS[record.element](state, found[1]) != record.available:
        problems.append(f"途中停止の対象 {record.target} の処理できる数が {ELEMENT_COUNTS[record.element](state, found[1])} で、記録の {record.available} と違う（不足する要素を処理した）")
    log = state.log
    if not 0 <= record.log_index < len(log) or record.log_index != len(log) - 1:
        problems.append(f"途中停止のログの位置 {record.log_index} が、最後のログ（{len(log) - 1}）ではない")
        return problems
    last = log[record.log_index]
    if last.get("kind") != "halted" or last.get("code") != record.code or last.get("interrupted") != record.kind:
        problems.append(f"途中停止のログの位置に、同じコードの途中停止の halted がない（{dict(last)!r}）")
    problems.extend(_coin_problems(log, record))
    return problems


def _until_sides(sides) -> bool:
    return bool(sides) and sides[-1] == "tails" and all(side == "heads" for side in sides[:-1])


def _coin_problems(log, record: Interruption) -> list[str]:
    """最後の ``halted`` の前に処理のログがなく、直前が「うら」が出るまで投げた一まとまりの最後の「うら」で、その「おもて」の数が必要な数か。ナツメのESPのやり直しの決定の
    あとなら、直前はやり直した（``esp_redo`` の ``redone``。その前にやり直したコインの一まとまり）か、やり直さなかった（``esp_redo_declined`` の ``original``）記録で、最後の
    並びの「おもて」の数が必要な数（最初の並びで判断していない）。"""
    if record.log_index < 1:
        return ["途中停止の前に、コインのログがない"]
    end = record.log_index
    last = log[end - 1]
    if last.get("kind") == "esp_redo_declined":
        sides = tuple(last.get("original") or ())
        if not _until_sides(sides):
            return [f"途中停止の直前のやり直さなかったコインの並び {sides!r} が、「おもて」の並びと最後の「うら」1 枚の形ではない"]
        if len(sides) - 1 != record.required:
            return [f"途中停止の必要な数 {record.required} が、やり直さなかったコインの「おもて」の数 {len(sides) - 1} と違う"]
        return []
    if last.get("kind") == "esp_redo":
        sides = tuple(last.get("redone") or ())
        if not _until_sides(sides):
            return [f"途中停止の直前のやり直したコインの並び {sides!r} が、「おもて」の並びと最後の「うら」1 枚の形ではない"]
        end -= 1
    tails = log[end - 1] if end >= 1 else {}
    if tails.get("kind") != "coin_flip" or tails.get("until") != "tails" or tails.get("result") != "tails" or tails.get("number") != tails.get("count"):
        return [f"途中停止の直前のログが、「うら」が出るまで投げたコインの最後の「うら」ではない（{dict(tails)!r}）"]
    count = tails["count"]
    batch = log[end - count:end]
    if (len(batch) != count or any(e.get("kind") != "coin_flip" or e.get("until") != "tails" or e.get("count") != count or e.get("number") != i
                                    or e.get("result") != ("tails" if i == count else "heads") for i, e in enumerate(batch, start=1))):
        return ["途中停止の直前の「うら」が出るまで投げたコインの一まとまりが、「おもて」の並びと最後の「うら」1 枚の形ではない"]
    if count - 1 != record.required:
        return [f"途中停止の必要な数 {record.required} が、最後に投げたコインの「おもて」の数 {count - 1} と違う"]
    return []

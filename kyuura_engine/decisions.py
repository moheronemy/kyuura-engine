"""保留中の決定（v0.2a、レビューの M4）。

処理の途中でプレイヤーの選択が要るとき、エンジンは決定（``state.PendingDecision``）を出して止まり、
選択を受け取ったら、決定に書いた再開先（``resume``）から処理を続けます。

- 決定は一度に 1 つだけです（``GameState.decision``）。決定を待っている間は、その決定に答える
  コマンドしか受け付けません。
- 1 つの処理が何回も選択を求めるときは、再開した処理が次の決定を出します（複数段階の決定）。
  続きに必要な情報は、決定の ``context`` に入れます（読み取り専用・JSON にできる値）。
- 再開先は関数ではなく名前（文字列）で持ちます。状態を pickle・JSON にしても再開先が失われない
  ようにするためです。

再開先の名前:

- ``"take_prize"``・``"promote_active"``: エンジンの中のきぜつのあとの処理（``engine`` が持つ）
- ``"attack"``: ワザの効果の続き。``context`` の ``"use"`` から、効果の登録表の実装を引き、
  その ``resume`` を呼ぶ（``effects.AttackEffect.resume``）。決定するのは、ふつうはワザを使ったプレイヤー。v0.4d から、
  ワザを使われた側のプレイヤーが決定する種類（``FORCED_SWITCH``）がある。どちらの場合も番のプレイヤー
  （``GameState.current_player``）はワザを使ったプレイヤーのまま。ワザの実装は、自分が出す決定の形を
  ``AttackEffect.decision_problems`` で宣言し、不変条件（``engine._decision_problems``）が確かめる
- ``"trainer"``: トレーナーの効果の続き（v0.2b）。``context`` の ``"use"`` から実装を引き、
  ``effects.TrainerEffect.resume`` を呼ぶ。決定がなくなったら、エンジンがカードをトラッシュする

選べるもののうち、原典で処理を決められないもの（v0.2b）: カードの文面では選べるが、選んだときの扱いを
原典で決められないものは、``context`` の ``"unresolved_choices"`` に入れる。それを選ぶと、状態を変えずに
``UnsupportedError``（``"unresolved_code"``・``"unresolved_reason"``）になる。推測で処理しないため。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from .errors import IllegalActionError, UnsupportedError
from .state import PendingDecision, Phase

if TYPE_CHECKING:
    from .effects import AttackUse, TrainerUse
    from .state import GameState

# 決定の種類（kind）。v0.1 からある 2 つは、段階（phase）も v0.1 と同じものを使う
TAKE_PRIZE = "take_prize"  # きぜつさせたプレイヤーが、サイドの位置を 1 つ選ぶ（p.312, p.323）
PROMOTE_ACTIVE = "promote_active"  # バトル場のポケモンがいなくなったプレイヤーが、ベンチのポケモンを 1 匹選ぶ（p.313, p.323）
SELECT_POKEMON = "select_pokemon"  # 効果の対象の場のポケモンを選ぶ（v0.2b。選べるものは場のポケモンの番号）
# ワザの効果で相手の対戦ポケモンをベンチにもどすとき、入れ替わる控えポケモンを、入れ替えられるプレイヤー（ワザを使った
# プレイヤーの相手）が選ぶ（v0.4d。バタフリーの「ふきとばし」。p.19 の最新の説明「入れ替わるポケモンは、相手が選ぶ。」・
# p.213 のワザ解説。選べるものは相手のベンチのポケモンの番号。段階は Phase.DECISION）
FORCED_SWITCH = "forced_switch"

_PHASE_FOR_KIND = {TAKE_PRIZE: Phase.TAKE_PRIZE, PROMOTE_ACTIVE: Phase.PROMOTE_ACTIVE}

# 決定を待っている段階
DECISION_PHASES = frozenset({Phase.TAKE_PRIZE, Phase.PROMOTE_ACTIVE, Phase.DECISION})


def phase_for(kind: str) -> Phase:
    """決定の種類に対応する段階。v0.1 からある種類はそれぞれの段階、それ以外は Phase.DECISION。"""
    return _PHASE_FOR_KIND.get(kind, Phase.DECISION)


def push_decision(
    state: GameState,
    *,
    kind: str,
    player: int,
    options: Iterable[int],
    resume: str,
    context: Iterable[tuple[str, Any]] = (),
    min_choices: int = 1,
    max_choices: int = 1,
) -> PendingDecision:
    """決定を出し、その決定を待つ段階にする。"""
    if state.decision is not None:
        raise RuntimeError("決定を待っている間に、別の決定を出そうとした（エンジンの不具合）")
    decision = PendingDecision(
        id=state.next_decision_id,
        kind=kind,
        player=player,
        options=tuple(options),
        min_choices=min_choices,
        max_choices=max_choices,
        resume=resume,
        context=tuple(context),
    )
    state.decision = decision
    state.next_decision_id += 1
    state.phase = phase_for(kind)
    return decision


def push_attack_decision(
    state: GameState,
    use: AttackUse,
    *,
    kind: str,
    player: int,
    options: Iterable[int],
    context: Iterable[tuple[str, Any]] = (),
    min_choices: int = 1,
    max_choices: int = 1,
) -> PendingDecision:
    """ワザの効果の途中で決定を出す。選ばれたら、そのワザの実装の ``resume`` が呼ばれる。"""
    use_context = ("use", (use.player, use.pokemon_id, use.key.card_id, use.key.attack_index))
    return push_decision(
        state,
        kind=kind,
        player=player,
        options=options,
        resume="attack",
        context=(use_context, *tuple(context)),
        min_choices=min_choices,
        max_choices=max_choices,
    )


def push_trainer_decision(
    state: GameState,
    use: TrainerUse,
    *,
    kind: str,
    player: int,
    options: Iterable[int],
    context: Iterable[tuple[str, Any]] = (),
    min_choices: int = 1,
    max_choices: int = 1,
    unresolved_choices: Iterable[int] = (),
    unresolved_code: str = "UNRESOLVED_RULING",
    unresolved_reason: str = "",
) -> PendingDecision:
    """トレーナーの効果の途中で決定を出す（v0.2b）。選ばれたら、そのトレーナーの実装の ``resume`` が呼ばれる。

    ``unresolved_choices``: ``options`` のうち、選んだときの扱いを原典で決められないもの（選ぶと
    ``UnsupportedError(unresolved_code, unresolved_reason)``）。
    """
    entries = [("use", (use.player, use.card, use.card_id))]
    unresolved = tuple(unresolved_choices)
    if unresolved:
        entries += [("unresolved_choices", unresolved), ("unresolved_code", unresolved_code), ("unresolved_reason", unresolved_reason)]
    return push_decision(
        state,
        kind=kind,
        player=player,
        options=options,
        resume="trainer",
        context=(*entries, *tuple(context)),
        min_choices=min_choices,
        max_choices=max_choices,
    )


def check_choices(decision: PendingDecision, choices: tuple[int, ...]) -> None:
    """選択が決定に合っているかを確かめる（状態は変えない）。

    合わなければ ``IllegalActionError``。選べるものの中でも、原典で扱いを決められないもの
    （``context`` の ``"unresolved_choices"``）を選んだら ``UnsupportedError``。
    """
    if not decision.min_choices <= len(choices) <= decision.max_choices:
        raise IllegalActionError(
            "INVALID_CHOICE_COUNT", f"選ぶ数は {decision.min_choices}〜{decision.max_choices}（{len(choices)} 個選んでいる）"
        )
    if len(set(choices)) != len(choices):
        raise IllegalActionError("DUPLICATE_CHOICE", "同じものを 2 回選んでいる")
    for choice in choices:
        if choice not in decision.options:
            raise IllegalActionError("INVALID_CHOICE", f"{choice!r} はこの決定で選べるものではない（{decision.options}）")
    unresolved = decision.context_value("unresolved_choices", ())
    for choice in choices:
        if choice in unresolved:
            raise UnsupportedError(
                decision.context_value("unresolved_code", "UNRESOLVED_RULING"),
                decision.context_value("unresolved_reason", "") or f"{choice!r} を選んだときの扱いは原典で決められない",
            )

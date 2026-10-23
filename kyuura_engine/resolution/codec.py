"""続きの情報（``Continuation``）と、v0.13 の決定（``PendingDecision``）の相互の変換（docs/event-model-v0.14.md 5 章）。

続きの情報は frozen の値で、決定の ``resume`` と ``context`` にそのまま書けます。決定の形（種類・決定するプレイヤー・選べるもの・選ぶ数・
再開先・``context`` の項目と順番）は v0.13 のエンジンが出す決定と同じにします。そのため、

- 書き出しの形式は 9 のまま（形式 10 を加えない）。
- v0.13 のエンジンが出した決定をプロトタイプが再開でき、プロトタイプが出した決定を v0.13 のエンジンが再開できる（混ぜて進められる）。

決定をまたいで残せるのは、ここにある値だけです（解決の中の値（とうめいの結果・こんじょうの写し）は残らない。v0.13 と同じ制約）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..decisions import KO_PREVENTION, POST_KNOCKOUT_POWER, PROMOTE_ACTIVE, TAKE_PRIZE, phase_for, push_decision
from ..state import PendingDecision

if TYPE_CHECKING:
    from ..state import GameState

ATTACK = "attack"
KNOCK_OUT = "knock_out"
POST_KNOCKOUT = "post_knockout"
RESUMES = frozenset({ATTACK, KNOCK_OUT, POST_KNOCKOUT, TAKE_PRIZE, PROMOTE_ACTIVE})


@dataclass(frozen=True)
class AttackContinuation:
    """ワザの要素の途中（決定を出した要素の次から続ける）。要素の位置は、決定の種類から決まる（並びの中で決定を出す要素は 1 つ）。"""

    use: tuple[int, int, str, int]  # (プレイヤー, ワザを使ったポケモンの番号, カード id, ワザの位置)
    kind: str
    extra: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True)
class KoCheckContinuation:
    """きぜつの判定の窓の任意の効果（こんじょう）の決定のあと。答えのあと、きぜつの処理へ。"""

    attack: tuple[int, int, str, int]
    power: tuple[str, int] | None  # v0.81: 学習装置（ついているどうぐ）の決定では None（``context`` の "tool"）


@dataclass(frozen=True)
class AftermathContinuation:
    """きぜつのあと（サイド → 勝ち負け → ふしちょう → 交代 → 番の終わり／ポケモンチェックの続き）。"""

    stage: str  # TAKE_PRIZE・POST_KNOCKOUT・PROMOTE_ACTIVE
    remaining: tuple[int, ...] = ()
    then: str | None = None
    post_knockout: tuple = ()
    power: tuple[str, int] | None = None  # 勝ち負けのあとの任意の効果（ふしちょう）の特殊能力


def _then(then: str | None) -> tuple:
    return () if then is None else (("then", then),)


def attack_decision(state: GameState, cont: AttackContinuation, *, player: int, options, min_choices: int = 1, max_choices: int = 1,
                    push: bool = True) -> PendingDecision:
    """ワザの途中の決定（v0.13 の ``decisions.push_attack_decision`` と同じ形）。``push`` が False なら状態に出さずに作るだけ（先読み）。"""
    context = (("use", cont.use), *cont.extra)
    return _make(state, push, kind=cont.kind, player=player, options=options, resume=ATTACK, context=context,
                 min_choices=min_choices, max_choices=max_choices)


def ko_check_decision(state: GameState, cont: KoCheckContinuation, *, player: int, pokemon_id: int, kind: str = KO_PREVENTION,
                      extra: tuple = ()) -> PendingDecision:
    """きぜつの判定の任意の効果の決定（v0.13 の ``engine._finish_attack`` と同じ形）。v0.61: ``kind`` が ``KNOCK_OUT_POWER``（［ファイナルビーム］）なら、``extra`` に
    「きぜつ」させたポケモン（``source``）と、使うを選ぶと止める場合（``unresolved_*``）を書く（こんじょうの決定の形は変えない）。"""
    return push_decision(state, kind=kind, player=player, options=(pokemon_id,), resume=KNOCK_OUT,
                         context=(("attack", cont.attack), ("power", cont.power), *extra), min_choices=0, max_choices=1)


def exp_all_decision(state: GameState, cont: KoCheckContinuation, *, player: int, options, tool: int, holder: int, source: int,
                     extra: tuple = ()) -> PendingDecision:
    """v0.81: きぜつの判定の窓の学習装置の決定（``EXP_ALL_ENERGY``。0〜1 枚。``extra`` は使うを選ぶと止める場合（``unresolved_*``））。"""
    from ..decisions import EXP_ALL_ENERGY

    return push_decision(state, kind=EXP_ALL_ENERGY, player=player, options=options, resume=KNOCK_OUT,
                         context=(("attack", cont.attack), ("tool", tool), ("holder", holder), ("source", source), *extra), min_choices=0, max_choices=1)


def prize_decision(state: GameState, player: int, cont: AftermathContinuation) -> PendingDecision:
    """サイドを取る決定（v0.13 の ``engine._next_prize_or_judge`` と同じ形）。"""
    post = () if not cont.post_knockout else (("post_knockout", tuple(cont.post_knockout)),)
    return push_decision(state, kind=TAKE_PRIZE, player=player, options=range(len(state.players[player].prizes)), resume=TAKE_PRIZE,
                         context=(("remaining", cont.remaining), *_then(cont.then), *post))


def post_knockout_decision(state: GameState, owner: int, card: int, cont: AftermathContinuation) -> PendingDecision:
    """勝ち負けのあとの任意の効果（ふしちょう）の決定（v0.13 の ``engine._offer_post_knockout`` と同じ形）。"""
    return push_decision(state, kind=POST_KNOCKOUT_POWER, player=owner, options=(card,), resume=POST_KNOCKOUT,
                         context=(("power", cont.power), *_then(cont.then)), min_choices=0, max_choices=1)


def promote_decision(state: GameState, player: int, cont: AftermathContinuation) -> PendingDecision:
    """バトル場に出す決定（v0.13 の ``engine._next_promotion_or_end`` と同じ形）。"""
    return push_decision(state, kind=PROMOTE_ACTIVE, player=player, options=[p.pokemon_id for p in state.players[player].bench],
                         resume=PROMOTE_ACTIVE, context=(("remaining", cont.remaining), *_then(cont.then)))


def decode(decision: PendingDecision):
    """決定から続きの情報を作る（v0.13 のエンジンが出した決定も読める）。"""
    resume = decision.resume
    if resume == ATTACK:
        use = decision.context_value("use")
        extra = tuple((name, value) for name, value in decision.context if name != "use")
        return AttackContinuation(tuple(use), decision.kind, extra)
    if resume == KNOCK_OUT:
        power = decision.context_value("power")
        return KoCheckContinuation(tuple(decision.context_value("attack")), None if power is None else tuple(power))
    if resume == TAKE_PRIZE:
        return AftermathContinuation(TAKE_PRIZE, tuple(decision.context_value("remaining", ())), decision.context_value("then"),
                                     tuple(decision.context_value("post_knockout", ())))
    if resume == POST_KNOCKOUT:
        return AftermathContinuation(POST_KNOCKOUT, (), decision.context_value("then"), (), tuple(decision.context_value("power")))
    if resume == PROMOTE_ACTIVE:
        return AftermathContinuation(PROMOTE_ACTIVE, tuple(decision.context_value("remaining", ())), decision.context_value("then"))
    raise ValueError(f"再開先 {resume!r} の決定はプロトタイプの続きではない（{sorted(RESUMES)}）")


def _make(state: GameState, push: bool, **kwargs) -> PendingDecision:
    if push:
        return push_decision(state, **kwargs)
    # 先読み: 状態に出さずに、同じ形の決定の値を作る（番号は使わない）
    return PendingDecision(id=0, kind=kwargs["kind"], player=kwargs["player"], options=tuple(kwargs["options"]),
                           min_choices=kwargs["min_choices"], max_choices=kwargs["max_choices"], resume=kwargs["resume"],
                           context=tuple(kwargs["context"]))


__all__ = [
    "AftermathContinuation",
    "AttackContinuation",
    "KoCheckContinuation",
    "RESUMES",
    "attack_decision",
    "decode",
    "exp_all_decision",
    "ko_check_decision",
    "phase_for",
    "post_knockout_decision",
    "prize_decision",
    "promote_decision",
]

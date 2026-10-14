"""v0.13 の約束で書いたワザの実装を、解決の基盤の枠の中で処理するアダプタ（v0.16b。docs/kernel-consolidation-v0.16b.md 3 章）。

ワザの実装の約束（``AttackEffect``。[api-review.md](../../docs/api-review.md) 3 章で「公開（実装を加える人向け）」）は、v0.13 では
``resolve(state, use)`` が補助関数（``effects.deal_attack_damage``・``damage_opponent_active``・``attack_reaches``・``finish_damage_elements``・
``decisions.push_attack_decision``・``effects._require_not_evaded``）を呼んで処理し、決定を出したら ``resume`` で続ける、というものでした。
v0.16b で旧経路を外したあとも、この約束で書いた実装（テスト・外の登録表の実装）を、次の形で解決の基盤が処理します。

- **どの実装に使うか**（``program_for``。無条件には使わない）: 実装の型が対応表（``programs.BUILDERS``。型が完全に一致するもの）に
  あれば、要素の並び。なければ、v0.13 の約束で処理できる実装（型が ``AttackEffect.resolve`` を上書きしているか、対応表の型の部分型）
  だけ、この要素 1 つ（``Contract``）の並び。どちらでもなければ、状態を変える前に ``UnsupportedError("UNSUPPORTED_ATTACK")`` で拒否
  する（黙って効果のないワザとして処理しない）。
- **処理**: 宣言・こんらんのコインは解決の基盤のまま。ワザの枠の中で ``Contract`` が ``effect.resolve`` を呼ぶ。渡す ``AttackUse`` は
  この枠への入口（``ContractRuntime``）を持ち、補助関数はそれに委ねる（ダメージは ``kernel.deal_damage``、受けるかは ``kernel.reaches``、
  ダメージの要素のあとの窓は ``kernel.fire_pending``、決定は ``AttackRun.suspend``）。ダメージ・ダメージを受けたときの効果・送る効果・
  きぜつの判定は、ほかのワザと同じ解決の基盤の窓を通る。
- **決定と再開**: 決定の形は v0.13 と同じ（``context`` は ``("use", …)`` と実装の ``context``）。答えのあと ``effect.resume`` を呼び、
  ``resume`` がもう一度決定を出したら、そこで止まる（2 段階以上の決定）。
- **宣言の前の確認**: 実装の宣言（``problem`` と v0.13 の止める関数。``v013_checks.check``）だけ。先読み ``derived`` は使わない（``resolve``
  の中身は解決の基盤から見えず、副作用のある ``resolve`` を何度も呼ばないため。v0.13・v0.15 でこれらの実装に行っていた確認と同じ）。
- **標準の実装の部分型**: 標準の 24 種類は ``resolve``・``resume`` を持たない（v0.16b で外した）。``AttackEffect`` の既定の ``resolve``・
  ``resume`` は、最も近い対応表の型の要素の並びを、今の枠の中で処理する（``run_builtin``・``resume_builtin``）。部分型の
  ``super().resolve`` は、親の処理（解決の基盤の要素の並び）になる。

製品の登録表のワザは、この要素を使いません（24 種類はすべて対応表にある。tests/test_kernel_integration_v0_15.py が確かめる）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from .. import effects as E
from ..errors import UnsupportedError
from .kernel import Resolution, deal_damage, fire_pending, reaches
from .programs import BUILDERS, AttackRun, Element, Phase, decision_index, run_elements
from .events import FrameKind

if TYPE_CHECKING:
    from ..state import GameState, PendingDecision, PokemonInPlay

    from .catalog import Catalog


def builtin_builder(cls: type):
    """型 ``cls`` か、その先祖のうち、最も近い対応表の型の要素の並びを作る関数（なければ None）。"""
    for ancestor in cls.__mro__:
        builder = BUILDERS.get(ancestor)
        if builder is not None:
            return builder
    return None


def follows_contract(cls: type) -> bool:
    """v0.13 の約束で処理できる実装の型か（``resolve`` を上書きしているか、対応表の型の部分型）。"""
    return cls.resolve is not E.AttackEffect.resolve or builtin_builder(cls) is not None


def program_for(effect: E.AttackEffect, attack_name: str = "") -> tuple[Element, ...]:
    """登録されたワザの実装の要素の並び: 対応表の型なら要素の並び、v0.13 の約束で処理できる実装ならアダプタの要素 1 つ。どちらでも
    なければ ``UnsupportedError("UNSUPPORTED_ATTACK")``（状態を変える前に呼ぶ）。"""
    builder = BUILDERS.get(type(effect))
    if builder is not None:
        return builder(effect)
    if follows_contract(type(effect)):
        return (Contract(effect),)
    raise UnsupportedError(
        "UNSUPPORTED_ATTACK",
        f"ワザ「{attack_name}」の実装 {type(effect).__name__}（{effect.implementation_id}）は、解決の基盤の要素の並び（programs.BUILDERS）も、"
        "v0.13 の約束の resolve も持たないので処理できない",
    )


def is_contract(program: tuple[Element, ...]) -> bool:
    return len(program) == 1 and isinstance(program[0], Contract)


@dataclass(frozen=True)
class Contract(Element):
    """v0.13 の約束で書いたワザの実装（``effect.resolve``・``resume``）を、今の枠の中で処理する要素。"""

    effect: Any
    phase: ClassVar[Phase] = Phase.CONTRACT

    def decides(self, kind: str) -> bool:
        return True  # 実装が出す決定の種類は実装が決める（並びの中にこの要素だけ）

    def run(self, run: AttackRun) -> bool:
        self.effect.resolve(run.state, ContractRuntime.use(run))
        return run.suspended is not None

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        self.effect.resume(run.state, ContractRuntime.use(run), decision, choices)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        raise RuntimeError("v0.13 の約束で書いた実装は、状態の複製の上で試さない（宣言の前の確認は実装の宣言。エンジンの不具合）")


class ContractRuntime:
    """v0.13 の約束の補助関数の、解決の基盤への入口（``AttackUse.runtime``）。1 つの ``AttackRun``（ワザの枠）に結びつく。"""

    def __init__(self, run: AttackRun):
        self.run = run

    @classmethod
    def use(cls, run: AttackRun) -> E.AttackUse:
        frame = run.fs.frame
        return E.AttackUse(frame.player, frame.source_pid, frame.attack_key, runtime=cls(run))

    def _check(self, state: GameState, what: str) -> None:
        if state is not self.run.state:
            raise RuntimeError(f"{what} に、処理中の状態とは別の状態が渡された（ワザの実装の誤り）")

    # ---- 補助関数（effects・decisions の入口が呼ぶ）

    def deal_damage(self, state: GameState, target: str, base: int, log_extra) -> E.DamageResult:
        self._check(state, "deal_attack_damage")
        return deal_damage(self.run.res, self.run.fs, target, base, log_extra=dict(log_extra) if log_extra else None)

    def reaches(self, state: GameState, owner: int, pokemon: PokemonInPlay, element: str, amount: int | None) -> bool:
        self._check(state, "attack_reaches")
        return reaches(self.run.res, self.run.fs, owner, pokemon, element, amount=amount)

    def finish_damage_elements(self, state: GameState) -> None:
        self._check(state, "finish_damage_elements")
        fire_pending(self.run.res, self.run.fs)

    def push_decision(self, state: GameState, *, kind: str, player: int, options, context, min_choices: int, max_choices: int) -> PendingDecision:
        self._check(state, "push_attack_decision")
        if self.run.suspended is not None:
            raise RuntimeError(f"ワザ {self.run.key} が、決定を待っている間にもう一度決定を出した（ワザの実装の誤り）")
        self.run.suspend(kind=kind, player=player, options=options, extra=tuple(context), min_choices=min_choices, max_choices=max_choices)
        return self.run.suspended

    @property
    def reception(self) -> dict[int, bool]:
        """このワザで「とうめい」のコインで決まった、受けるか（場のポケモンの番号 → 真偽。枠の記録そのもの）。"""
        return self.run.fs.reception

    @property
    def ko_prevention_able(self) -> dict[int, bool]:
        """ダメージを受けるときの「こんじょう」を使えるかの写し（場のポケモンの番号 → 真偽。解決の記録そのもの）。"""
        return self.run.res.ko_prevention_able

    @property
    def pending(self) -> tuple:
        """まだ処理していない送る効果（「ダメージを受けたとき」の効果。``kernel.Deferred``）。試験で確かめるための読み取り。"""
        return tuple(self.run.fs.pending)

    # ---- 標準の実装の部分型（AttackEffect の既定の resolve・resume）

    def run_builtin(self, state: GameState, effect: E.AttackEffect) -> None:
        self._check(state, "resolve")
        builder = builtin_builder(type(effect))
        if builder is None:
            raise NotImplementedError(f"{effect.implementation_id} は resolve を持たない（解決の基盤の要素の並びもない）")
        inner = AttackRun(self.run.res, self.run.fs, builder(effect), self.run.attack)
        if run_elements(inner, 0):
            self.run.suspended = inner.suspended
            self.run.carried = inner.carried

    def resume_builtin(self, state: GameState, effect: E.AttackEffect, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        self._check(state, "resume")
        builder = builtin_builder(type(effect))
        if builder is None:
            raise NotImplementedError(f"{effect.implementation_id} は決定を出さない")
        program = builder(effect)
        inner = AttackRun(self.run.res, self.run.fs, program, self.run.attack)
        inner.carried = dict(self.run.carried)
        index = decision_index(program, decision.kind)
        program[index].resume(inner, decision, choices)
        if inner.suspended is None and not run_elements(inner, index + 1):
            return
        self.run.suspended = inner.suspended
        self.run.carried = inner.carried


def open_attack(state: GameState, player: int, *, attack_index: int = 0, catalog: Catalog | None = None) -> E.AttackUse:
    """試験用の入口: ``player`` のバトル場のポケモンのワザ ``attack_index`` の枠を開き、v0.13 の約束の補助関数を使える ``AttackUse`` を
    返す（宣言・確認・きぜつの判定はしない。補助関数を直接確かめる単体テストのため）。``state`` をそのまま変える。"""
    from .catalog import DEFAULT_CATALOG

    attacker = state.players[player].active
    key = E.AttackKey(state.cards[attacker.card].card_id, attack_index)
    attack = state.card_def(attacker.card).attacks[attack_index]
    res = Resolution(state, catalog=DEFAULT_CATALOG if catalog is None else catalog)
    fs = res.open_frame(FrameKind.ATTACK, parent=None, player=player, source_pid=attacker.pokemon_id, attack_key=key)
    return ContractRuntime.use(AttackRun(res, fs, (), attack))


__all__ = ["Contract", "ContractRuntime", "builtin_builder", "follows_contract", "is_contract", "open_attack", "program_for"]

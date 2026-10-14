"""v0.13 の宣言の前の確認（限定的な互換の判定。v0.16c。docs/preflight-consolidation-v0.16c.md）。

解決の基盤の先読み（``preflight``。``derived``・``derived_full``）は、ワザの要素の並びを状態の複製の上で、コインと決定のすべての結果で試して、
原典で決められない場合（``questions.QUESTIONS``）を見つけます。ここにあるのは、それとは別の、v0.13 の ``engine._use_attack`` が使っていた
止める関数（``effects`` の 5 つ）を同じ順番で呼ぶ判定です。v0.13 のワザの解決の経路は v0.16b で外しましたが、この判定は次の 3 か所だけで
使うので、この部品に分けて残します（使う所はこの 3 つに限る。tests/test_preflight_consolidation_v0_16c.py が確かめる）。

1. v0.13 の約束で書いたワザの実装（``contract``。アダプタ）の宣言の前の確認（解決の記録の方法 ``contract``）。``resolve`` の中身は
   先読みから見えないので、実装の宣言（``problem``・``damage_profile``・``opponent_effect_elements``）で確かめる（v0.13・v0.15 と同じ）。
2. 先読みで試す結果の数が上限（``preflight.MAX_BRANCHES``）を超えたとき、型が ``VERIFIED`` のワザだけ（方法 ``legacy_after_limit``）。
   ほかの型は拒否（``UNSUPPORTED_PREFLIGHT_LIMIT``）。製品の 24 種類は、正しい盤面（60 枚のデッキ）では上限に届かない（いちばん多い
   エナジーへんかん（こんらん）でも 1 + 57² = 3,250 通り。docs 3 章）ので、今は盤面を直接作った試験だけが通る。
3. 比べるための先読みの方法 ``legacy``（方法 ``legacy``）。

外す条件（docs 6 章）: 1 は、v0.13 の約束で書いた実装がなくなり、拡張の約束（``AttackEffect.resolve``）を外すと決めたとき。2 は、1 と
いっしょに外すか、製品のすべての型の試す結果の数が正しい盤面で上限以下であることを試験で保証して一律の拒否（案 C）に置きかえるとき。
3 は、比べる道具が要らなくなったとき。新しいワザの実装の型を ``VERIFIED`` に自動では加えない（v0.13 の止める関数で足りるかを確かめてから
加える）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import effects as E
from ..effects import counterattack_double_knockout_problem, ko_prevention_attack_effect_problem, retaliation_double_knockout_problem
from ..errors import UnsupportedError
from ..procedures import confusion_damage_problem

from .events import PreflightResult, Trace

if TYPE_CHECKING:
    from ..effects import AttackUse
    from ..state import GameState

MODES = ("legacy", "legacy_after_limit", "contract")

# v0.13 の止める関数で宣言の前の確認ができると確かめたワザの実装（v0.13 の 24 種類。v0.14・v0.15 の比較で ``derived`` と同じ答え）。
# 試す結果の数が上限を超えたときだけ使う。ワザの実装を加えても自動では加えない（v0.13 の止める関数で足りるかを確かめてから加える）
VERIFIED: frozenset[type] = frozenset({
    E.DamageOnly, E.CoinFlipDamage, E.CoinHeadsDamagePerOwnCounter, E.SelfDamageInsteadOnTails, E.SelfDamageOnTails, E.PoisonOnHeads,
    E.PoisonOpponent, E.SleepOpponent, E.ParalyzeOnHeads, E.CoinBonusDamageAndParalyze, E.PutToSleep, E.PoisonWithoutDamage,
    E.ConfuseOnHeads, E.PreventDamageOnHeads, E.DamageAndRetaliation, E.ReturnReceivedDamage, E.DamageAndForceSwitch, E.DamageAndDrain,
    E.DamageAndRemoveCounters, E.ExtraEnergyDamage, E.DiscardEnergyAndRemoveAllCounters, E.RecoverEnergyAndSelfDamage,
    E.DamageReducedByOwnCounters, E.DamageAndSelfDamage,
})


def check(state: GameState, use: AttackUse, effect, attacker, trace: Trace, *, mode: str = "legacy") -> None:
    """v0.13 の ``engine._use_attack`` の確認（止める関数 5 つ）を、同じ順番でそのまま呼ぶ。当たったら、その ``UnsupportedError`` を投げる
    （状態を変えない。乱数を使わない）。解決の記録には方法 ``mode`` と当たったコードを残す。"""
    if mode not in MODES:
        raise ValueError(f"v0.13 の確認の方法 {mode!r} は {MODES} のどれか")
    problem: UnsupportedError | None = effect.problem(state, use)
    if problem is None and attacker.conditions.confused:
        problem = confusion_damage_problem(state, attacker)
    if problem is None:
        problem = counterattack_double_knockout_problem(state, use, effect)
    if problem is None:
        problem = ko_prevention_attack_effect_problem(state, use, effect)
    if problem is None:
        problem = retaliation_double_knockout_problem(state, use, effect)
    trace.record(PreflightResult(mode, 0, () if problem is None else (problem.code,)))
    if problem is not None:
        raise problem


__all__ = ["MODES", "VERIFIED", "check"]

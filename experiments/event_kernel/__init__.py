"""汎用のイベント・効果の解決の仕組みのプロトタイプ（v0.14。docs/event-model-v0.14.md）。

本番のエンジン（``kyuura_engine``）の一部ではありません。v0.13 の状態の型・書き出しの形式（9）・ログ・決定の形をそのまま使い、
効果の解決の流れ（ワザ・きぜつ・番の終わり・決定の再開）を、窓（処理の段階）・枠（処理の単位）・効果の定義の対応表で処理します。

使い方は ``kyuura_engine.apply_command`` と同じです::

    from experiments import event_kernel
    state = event_kernel.apply_command(state, command)               # 先読みは "derived"（既定）
    state, trace = event_kernel.apply_command_traced(state, command)  # 解決の記録（内部のイベント）も返す
"""

from .catalog import DEFAULT_CATALOG, Catalog, EffectDefinition, EffectInstance, Mode, Origin, Timing
from .events import DamageClass, FrameKind, Trace, Window
from .flow import PREFLIGHT_MODES, apply_command, apply_command_traced, owned
from .programs import BUILDERS, UnsupportedByKernel, compile_attack
from .questions import QUESTIONS

__all__ = [
    "BUILDERS",
    "Catalog",
    "DEFAULT_CATALOG",
    "DamageClass",
    "EffectDefinition",
    "EffectInstance",
    "FrameKind",
    "Mode",
    "Origin",
    "PREFLIGHT_MODES",
    "QUESTIONS",
    "Timing",
    "Trace",
    "UnsupportedByKernel",
    "Window",
    "apply_command",
    "apply_command_traced",
    "compile_attack",
    "owned",
]

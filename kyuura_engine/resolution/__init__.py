"""効果の解決の基盤（v0.15b。v0.14 のプロトタイプ ``experiments/event_kernel`` を本番の内部の部品にしたもの）。

docs/kernel-integration-v0.15b.md・docs/kernel-consolidation-v0.16b.md・docs/event-model-v0.14.md。v0.16b から、ワザ・番の終わり・きぜつの
あとの決定を処理するのは、この基盤だけです（v0.13 の経路は外した）。

ワザ・番の終わり・きぜつのあとの決定の解決を、処理の段階（窓）・処理の枠・効果の定義の対応表・ワザの要素の並び・原典で決められない
場合の先読みで行います。状態の型（``GameState``）・書き出しの形式 9・公開のログ・決定の形は v0.13 と同じです。

公開の API ではありません。使うのは ``engine.py`` と、試験・比較の道具です。コマンドは ``engine.apply_command`` か、解決の設定（先読みの
方法・効果の定義の対応表）を指定する内部の入口 ``engine.apply_command_with``・``engine.apply_command_traced`` で渡してください。この部品は
``engine.py`` を読み込みません。
"""

from .catalog import DEFAULT_CATALOG, Catalog, EffectDefinition, EffectInstance, Mode, Origin, Timing
from .events import DamageClass, FrameKind, Trace, Window
from .contract import Contract, ContractRuntime, open_attack, program_for
from .flow import COMMANDS, CONTINUE_TURN, PREFLIGHT_MODES, RESUMES, Context, after_power, handle, processes, resume_decision
from .programs import BUILDERS, UnsupportedByKernel, compile_attack
from .questions import QUESTIONS

__all__ = [
    "BUILDERS",
    "COMMANDS",
    "CONTINUE_TURN",
    "Catalog",
    "Context",
    "Contract",
    "ContractRuntime",
    "DEFAULT_CATALOG",
    "DamageClass",
    "EffectDefinition",
    "EffectInstance",
    "FrameKind",
    "Mode",
    "Origin",
    "PREFLIGHT_MODES",
    "QUESTIONS",
    "RESUMES",
    "Timing",
    "Trace",
    "UnsupportedByKernel",
    "Window",
    "after_power",
    "compile_attack",
    "handle",
    "open_attack",
    "processes",
    "program_for",
    "resume_decision",
]

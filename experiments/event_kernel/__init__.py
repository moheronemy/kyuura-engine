"""v0.14 のプロトタイプの名前で、本番の解決の基盤（``kyuura_engine.resolution``。v0.15b）を使うための薄い互換の層。

v0.14 のプロトタイプは v0.15b で本番の内部の部品になりました（docs/kernel-integration-v0.15b.md）。コードの複製はなく、この層は
v0.14 のテスト（tests/test_event_kernel_v0_14.py・tests/test_event_kernel_games_v0_14.py）と道具（tools/event_kernel_compare.py）が
使う名前を、本番の部品につなぐだけです。

- ``experiments.event_kernel.catalog`` などの下の名前は、``kyuura_engine.resolution`` の同じモジュールそのもの（``sys.modules`` に同じ
  オブジェクトを登録する）。試験で対応表を差しかえると、本番の部品が変わる（v0.14 のテストの差しかえ・もどしはそのまま動く）。
- ``apply_command``・``apply_command_traced`` は、解決の設定を指定する ``engine.apply_command_with``・``engine.apply_command_traced``
  （v0.16b で経路はなくなった。解決の基盤だけが処理する）。
- ``owned`` は ``resolution.processes``（解決の基盤が処理するコマンドか。v0.16b で ``resolution.handles`` を外した。数を数えるためだけに
  使う）。

新しいコードは ``kyuura_engine.resolution`` と ``kyuura_engine.engine`` の内部の入口を直接使ってください。v0.16 で、この層を外すかを決めます。
"""

import sys

from kyuura_engine import resolution as _resolution
from kyuura_engine.engine import apply_command_traced, apply_command_with
from kyuura_engine.resolution import catalog, codec, events, flow, kernel, preflight, programs, questions
from kyuura_engine.resolution import (
    BUILDERS,
    DEFAULT_CATALOG,
    PREFLIGHT_MODES,
    QUESTIONS,
    Catalog,
    DamageClass,
    EffectDefinition,
    EffectInstance,
    FrameKind,
    Mode,
    Origin,
    Timing,
    Trace,
    UnsupportedByKernel,
    Window,
    compile_attack,
)

for _name, _module in (("catalog", catalog), ("codec", codec), ("events", events), ("flow", flow), ("kernel", kernel),
                       ("preflight", preflight), ("programs", programs), ("questions", questions)):
    sys.modules[f"{__name__}.{_name}"] = _module


def apply_command(state, command, *, preflight: str = "derived", catalog: Catalog = DEFAULT_CATALOG):
    """解決の設定を指定して処理する（v0.14 の ``experiments.event_kernel.apply_command`` と同じ使い方。``engine.apply_command_with``）。"""
    return apply_command_with(state, command, preflight=preflight, catalog=catalog)


def owned(state, command) -> bool:
    """解決の基盤が処理するコマンドか（``resolution.processes``。数を数えるため）。"""
    return _resolution.processes(state, command)


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

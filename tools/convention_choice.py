"""道具の対戦で使う規約集合を選ぶ（v0.143。docs/play-policy-s2a-v0.143.md 7 章）。道具だけの選び方で、エンジンの既定（省略したときの今の挙動の集合 CS-KYUURA-CURRENT@1）は変えない。

``use_conventions("CS-KYUURA-PLAY-S2A@1")`` は、読み込み済みのモジュールが ``new_game`` の名前で持つエンジンの ``new_game`` を、``conventions`` を渡す関数に置きかえる（道具の対戦と、
監査のやり直しの両方が同じ集合で始まる）。呼び出し元が ``conventions`` を渡したときはそのまま。``None`` なら何もしない（今の挙動の集合）。
"""

from __future__ import annotations

import sys

from kyuura_engine import conventions as C
from kyuura_engine import engine as E

_ORIGINAL = E.new_game


def use_conventions(text: str | None) -> str | None:
    """``text``（``ID@版``）の集合を、以後の道具の ``new_game`` に渡す。確かめた集合の ``ID@版`` を返す（``None`` なら何もせず ``None``）。"""
    if text is None:
        return None
    key = C.parse_key(text)
    C.resolve_for_new_game(text)  # 知らない・確かめに通らない集合は、対戦を始める前に ConventionSetError

    def new_game(*args, conventions=None, **kwargs):
        return _ORIGINAL(*args, conventions=text if conventions is None else conventions, **kwargs)

    new_game.__doc__ = _ORIGINAL.__doc__
    for module in list(sys.modules.values()):
        if module is not None and getattr(module, "new_game", None) is _ORIGINAL:
            module.new_game = new_game
    return f"{key[0]}@{key[1]}"

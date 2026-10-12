"""乱数の状態（v0.2a）。

エンジンの乱数は、対戦ごとの ``GameState.rng``（``random.Random(seed)``）1 本だけです。
モジュールの ``random``（グローバルな乱数）は使いません。

ここでは 2 つを区別します。

- **指紋**（``rng_fingerprint``）: 乱数の状態の SHA-256。状態を比べるためのもので、ここから乱数の
  状態はもどせない。``state_to_dict`` に入る。
- **保存・復元**（``rng_state_to_json``・``rng_from_json``）: 乱数の状態そのもの（メルセンヌ・ツイスタの
  内部状態 625 個の整数）。将来のセーブ・ロードで、状態を JSON にして保存し、同じ乱数の続きを
  再現するために使う。``GameState.clone()``・``copy.deepcopy``・``pickle`` は、これと同じ状態を
  そのまま複製する。

v0.2a のエンジンは、対戦準備（山札を切る）のあとは乱数を使いません。コインは未実装です。
"""

from __future__ import annotations

import hashlib
import random
from typing import Any

RNG_FORMAT = "python-random-mt19937-v3"


def rng_fingerprint(rng: random.Random) -> str:
    """乱数の状態の指紋（比べる用）。"""
    return hashlib.sha256(repr(rng.getstate()).encode("ascii")).hexdigest()


def rng_state_to_json(rng: random.Random) -> dict[str, Any]:
    """乱数の状態を、JSON にできる形にする（保存用）。"""
    version, internal, gauss_next = rng.getstate()
    return {"format": RNG_FORMAT, "version": version, "internal": list(internal), "gauss_next": gauss_next}


def rng_from_json(data: dict[str, Any]) -> random.Random:
    """``rng_state_to_json`` の形から乱数をもどす。"""
    if data.get("format") != RNG_FORMAT:
        raise ValueError(f"知らない乱数の状態の形式 {data.get('format')!r}")
    rng = random.Random()
    rng.setstate((data["version"], tuple(data["internal"]), data["gauss_next"]))
    return rng


def copy_rng(rng: random.Random) -> random.Random:
    """同じ状態の、別の乱数（片方を進めても、もう片方は変わらない）。"""
    new = random.Random()
    new.setstate(rng.getstate())
    return new

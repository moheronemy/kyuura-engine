"""エンジンが投げる例外。

どの例外も、``apply_command`` に渡したゲーム状態を変えません（新しい状態を作る前に失敗するため）。
"""

from __future__ import annotations


class EngineError(Exception):
    """エンジンの例外の基底。``code`` はプログラムで判定するための短い名前。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class IllegalActionError(EngineError):
    """ルール上、今その操作はできない（番・タイミング・エネルギー・ベンチの上限など）。"""


class UnsupportedError(EngineError):
    """ルールとしてはあり得るが、このエンジンが対応していない（未実装の効果・未解決の裁定など）。

    未対応のものを「効果がないもの」として処理しないために、黙って無視せずにこの例外を投げる。
    """


class DeckValidationError(EngineError):
    """デッキがルール（60 枚・同じ名前 4 枚まで・たねポケモン必須）か、対応カードの条件を満たさない。"""

    def __init__(self, problems: list[str]):
        super().__init__("INVALID_DECK", "; ".join(problems))
        self.problems = list(problems)

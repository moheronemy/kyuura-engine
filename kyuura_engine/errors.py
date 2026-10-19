"""エンジンが投げる例外。

どの例外も、``apply_command`` に渡したゲーム状態を変えません（複製した状態で処理するため。コインを投げた
あとで止まっても、渡した状態の乱数は進まない）。
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


class StateIntegrityError(EngineError):
    """処理の結果の状態が不変条件（カードの保存則・場の形など）を満たさない。

    ルール上の不正ではなく、エンジンの不具合か、呼び出し側が状態を直接書き換えたことを示す。
    """

    def __init__(self, problems: list[str]):
        super().__init__("STATE_INTEGRITY", "; ".join(problems))
        self.problems = list(problems)


SECRET_PLAN_HIDDEN_CODE = "UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY"


class HiddenPropertyRead(UnsupportedError):
    """うらにしてベンチに出したカード（v0.67。マチスの秘策）の、うらのあいだは決まらない項目（名前・HP・タイプ・弱点・抵抗力・にげる・ワザ・カードの id）を読んだ
    （FD1。docs/secret-plan-preflight-v0.67.md 5 章）。

    うらのカードは「たねポケモン」としてあつかわれるだけで、ほかの項目は決まらない。効果の対象として指定されてダメージや効果を受けるときは、その前におもてにするので
    （``zones.reveal_face_down``）、ここに来るのは、おもてにしないまま項目を読む処理（名前・タイプで数える・選ぶ効果、［へんしん］など）。本当のカードの値で処理すると、
    うらのカードを知らない相手の結果が本当のカードで変わってしまい、値がないとして処理すると読み方を 1 つに決めてしまう（p.277 の解説は「全体に働く効果」で、おもてに
    しなくてよいことだけを書く）ので、どちらにもせず止める。本当のカードによらず同じ理由で止まる（理由の文に本当のカードを書かない）。"""

    def __init__(self, field: str):
        super().__init__(SECRET_PLAN_HIDDEN_CODE,
                         f"うらにしてベンチに出したカード（マチスの秘策）の「{field}」を、おもてにしないまま読む処理（うらのあいだは決まらない。FD1）")
        self.field = field

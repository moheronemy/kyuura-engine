"""原典で決められない場合（既知の問い）の表（docs/event-model-v0.14.md 7 章）。

仕組みの共通の検出（同時のきぜつの原因の分かれ方・無効な要素のためのコインなど）が当たったら、この表で v0.13 の ``UNRESOLVED_…``
のコードと裁定の番号を引きます。表にない検出・コードのない問い（今の対応カードでは起こらない）は、推測で解決せず、エンジンの
不具合として止めます。

``priority`` は、2 つ以上の問いに当たったときに選ぶ順番で、v0.13 の ``engine._use_attack`` の確認の順番（ワザの実装の
``problem`` → こんらんのダメージの変更効果 → C18 → G37 → W24 → ワザの途中の確認）に合わせています。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import UnsupportedError


@dataclass(frozen=True)
class Question:
    key: str
    code: str | None  # None: 今の対応カードでは起こらない（当たったらエンジンの不具合）
    rulings: tuple[str, ...]
    priority: int
    message: str


QUESTIONS: dict[str, Question] = {
    q.key: q
    for q in (
        Question(
            "prevented_coin_damage", "UNRESOLVED_PREVENTED_COIN_DAMAGE", ("v0.4b",), 10,
            "「ダメージを受けない」状態の相手へのダメージの要素の量だけを決めるコインを投げるかは、原典（p.309・p.319・p.320・p.321）から"
            "決められない（投げるかどうかで乱数の続きが変わる）",
        ),
        Question(
            "evaded_effect_coin", "UNRESOLVED_EVADED_EFFECT_COIN", ("T19b",), 10,
            "「とうめい」で受けないと決まったポケモンへの効果を決めるワザのコインを投げるかは、原典（p.159・p.160・p.309・p.321）から"
            "決められない（投げるかどうかで乱数の続きが変わる）",
        ),
        Question(
            "confusion_damage_modifiers", "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", ("v0.3c",), 20,
            "こんらんしたワザの 20 ダメージに、プラスパワー・ディフェンダーの効果を計算するかは、原典（p.257・p.309・p.321・p.322）から"
            "決められない",
        ),
        Question(
            "counterattack_double_knockout", "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT", ("C18",), 30,
            "ワザによるきぜつと、それがはたらかせた特殊能力のダメージによるきぜつが「同時に「きぜつ」した」ことになるか（p.324）は、"
            "原典（p.89・p.192・p.311・p.323〜p.325）から決められない",
        ),
        Question(
            "ko_prevention_attack_effect", "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT", ("G37",), 40,
            "「こんじょう」で「きぜつ」しなかったポケモンが、そのワザの効果を受けるかは、原典（p.89・p.193・p.309・p.311・p.320〜p.324）から"
            "決められない",
        ),
        Question(
            "retaliation_double_knockout", "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT", ("W24", "S37"), 50,
            "このワザによるきぜつと、前の番のワザの効果のダメージによるきぜつが「同時に「きぜつ」した」ことになるか（p.324）は、原典"
            "（p.82・p.89・p.311・p.321・p.323〜p.325）から決められない",
        ),
        Question(
            "reparalysis_recovery_turn", "UNRESOLVED_REPARALYSIS_RECOVERY_TURN", ("v0.3b",), 60,
            "マヒの再付与で回復する番が変わる場合の扱いは、原典から決められない",
        ),
        # 今の対応カードでは起こらない（コードがない。当たったらエンジンの不具合として止める）
        Question("multiple_deferred_effects", None, ("C34", "C35"), 90, "1 つのワザで 2 つ以上の「ダメージを受けたとき」の効果がはたらいた"),
        Question("multiple_ko_prevention", None, ("G40", "G16"), 90, "きぜつするときに使える特殊能力の候補が 2 つ以上"),
        Question("multiple_post_knockout", None, ("P32",), 90, "きぜつしたときに使える特殊能力の候補が 2 つ以上"),
        Question("post_knockout_gas_source_knocked", None, ("P19",), 90, "かがくへんかガスの発生源が、消している特殊能力のポケモンといっしょにきぜつする"),
        Question("multiple_evasion", None, ("T27",), 90, "1 つのワザで 2 匹以上の「とうめい」を評価した"),
    )
}


class OpenQuestion(Exception):
    """仕組みの共通の検出が、既知の問い（``QUESTIONS``）に当たった。先読み（``preflight``）が集め、実際の処理では止める。"""

    def __init__(self, key: str, detail: str = "", error: UnsupportedError | None = None):
        if key not in QUESTIONS:
            raise KeyError(f"知らない問い {key!r}（questions.QUESTIONS に加える）")
        super().__init__(f"{key}: {detail}")
        self.key = key
        self.detail = detail
        self.error = error  # v0.13 の部品が作った理由（マヒの再付与）。あればそのまま使う


def to_error(key: str, detail: str = "", error: UnsupportedError | None = None) -> UnsupportedError:
    """問いを ``UnsupportedError`` にする。コードのない問いは ``RuntimeError``（今の対応カードでは起こらないので、エンジンの不具合）。"""
    question = QUESTIONS[key]
    if question.code is None:
        raise RuntimeError(f"今の対応カードでは起こらないはずの問い {key}（{'・'.join(question.rulings)}）: {question.message}。{detail}")
    if error is not None and error.code == question.code:
        return error
    return UnsupportedError(question.code, f"{question.message}（{'・'.join(question.rulings)}。{detail}）")


def pick(keys) -> str:
    """当たった問いのうち、優先度のいちばん高い（数の小さい）もの。同じ優先度なら名前の順（決まった答えにする）。"""
    return min(keys, key=lambda k: (QUESTIONS[k].priority, k))

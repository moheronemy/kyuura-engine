"""利用者が選んで対戦に使える固定のデッキ（v0.20）。

対応済みのカードだけを組み合わせた、最初の試作の構成です。実在した大会のデッキや、勝率の釣り合いを確かめた構成ではありません。
各デッキの考え方・使い方・既知の制限は docs/preset-decks-v0.20.md。

- デッキは安定した識別子（``deck_id``）で選びます。カード id と枚数は、このモジュールの ``PRESET_DECKS`` の 1 か所だけで持ちます。
- ``PresetDeck.cards()``・``counts()`` は呼ぶたびに新しいリスト・辞書を返すので、読み出した側が変えても次の読み出しに影響しません。
- テストの盤面・統合テストのためのデッキ（tests/ のもの）とは別です。tests/ のデッキはここに登録しません。

使い方::

    from kyuura_engine import new_game, preset_deck
    state = new_game(preset_deck("hitmonchan-dewgong").cards(), preset_deck("venusaur-parasect").cards(), seed=1)
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .deck import expand_decklist


@dataclass(frozen=True)
class PresetDeck:
    """固定のデッキ 1 つ。``entries`` は（カード id, 枚数）の並び（表示の順。ポケモン → トレーナー → エネルギー）。"""

    deck_id: str
    name_ja: str
    entries: tuple[tuple[str, int], ...]

    def counts(self) -> dict[str, int]:
        """{カード id: 枚数}（新しい辞書）。"""
        return dict(self.entries)

    def cards(self) -> list[str]:
        """``new_game`` に渡せる 60 枚のカード id の並び（新しいリスト。``expand_decklist`` と同じ形）。"""
        return expand_decklist(self.counts())


PRESET_DECKS: Mapping[str, PresetDeck] = MappingProxyType({
    deck.deck_id: deck
    for deck in (
        # デッキ A: エビワラー・ジュゴン（v0.20）。エビワラーで先に攻め、パウワウ → ジュゴンを育てる。コラッタはにげるエネルギー 0 の交代役
        PresetDeck(
            "hitmonchan-dewgong",
            "エビワラー・ジュゴン",
            (
                ("PMCG1-058", 4),  # エビワラー
                ("PMCG1-029", 4),  # パウワウ
                ("PMCG1-030", 3),  # ジュゴン
                ("PMCG1-060", 3),  # コラッタ
                ("PMCG1-077", 4),  # オーキドはかせ
                ("PMCG1-074", 4),  # マサキ
                ("PMCG1-071", 4),  # きずぐすり
                ("PMCG1-073", 4),  # ポケモンいれかえ
                ("PMCG1-081", 4),  # プラスパワー
                ("PMCG1-079", 4),  # ディフェンダー
                ("PMCG1-102", 12),  # 闘エネルギー
                ("PMCG1-099", 10),  # 水エネルギー
            ),
        ),
        # デッキ B: フシギバナ・パラセクト（v0.20）。パラセクトのねむりで時間を稼ぎ、フシギバナを育て、エナジートランスで草エネルギーを配る
        PresetDeck(
            "venusaur-parasect",
            "フシギバナ・パラセクト",
            (
                ("PMCG1-001", 4),  # フシギダネ
                ("PMCG1-008", 4),  # フシギソウ
                ("PMCG1-011", 3),  # フシギバナ
                ("PMCG2-003", 4),  # パラス
                ("PMCG2-010", 3),  # パラセクト
                ("PMCG1-077", 3),  # オーキドはかせ
                ("PMCG1-074", 4),  # マサキ
                ("PMCG1-071", 4),  # きずぐすり
                ("PMCG1-073", 4),  # ポケモンいれかえ
                ("PMCG1-081", 3),  # プラスパワー
                ("PMCG1-079", 4),  # ディフェンダー
                ("PMCG1-097", 20),  # 草エネルギー
            ),
        ),
    )
})


def preset_deck_ids() -> tuple[str, ...]:
    """選べるデッキの識別子（登録の順）。"""
    return tuple(PRESET_DECKS)


def preset_deck(deck_id: str) -> PresetDeck:
    """識別子でデッキを選ぶ。知らない識別子は ``KeyError``（選べる識別子を示す）。"""
    try:
        return PRESET_DECKS[deck_id]
    except KeyError:
        raise KeyError(f"デッキ {deck_id!r} はない。選べるのは {list(PRESET_DECKS)}") from None

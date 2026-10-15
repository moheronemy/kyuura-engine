"""利用者が選んで対戦に使える固定のデッキ（v0.20）。

対応済みのカードだけを組み合わせた試作の構成です。実在した大会のデッキ・最適化したデッキや、人間どうしで勝率の釣り合いを確かめた構成では
ありません。第1版（v0.20）の考え方・使い方・既知の制限は docs/preset-decks-v0.20.md、第2版（v0.26。``-v2`` の識別子）は
docs/preset-decks-v0.26.md。第2版を加えても、第1版の識別子と中身は変えていません（別の識別子で並べて持つ）。

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
        # 第2版（v0.26。docs/preset-decks-v0.26.md）。第1版のディフェンダーを外し、v0.21〜v0.25 で対応にした探す・回収するトレーナーを入れた。
        # デッキ A2: エビワラー・ジュゴン。ポケモン（14 枚）とエネルギー（闘 12・水 10）は第1版と同じ。ディフェンダー 4 枚を外し、オーキドはかせ・
        # ポケモンいれかえを 1 枚ずつ・きずぐすりを 2 枚減らして、突風 3・パソコン通信 3・エネルギー回収 2 を入れた。2 進化ポケモンがいないので
        # ポケモン育て屋さんは入れない。初期案（ポケモン交換おじさん 2・闘 11・水 9）から、比べた対戦でエネルギーが足りずにワザを使えない番が
        # 第1版より増えたので、ポケモン交換おじさん 2 枚を闘・水 1 枚ずつにもどした（1 回だけの調整。docs/preset-decks-v0.26.md 4 章）
        PresetDeck(
            "hitmonchan-dewgong-v2",
            "エビワラー・ジュゴン（第2版）",
            (
                ("PMCG1-058", 4),  # エビワラー
                ("PMCG1-029", 4),  # パウワウ
                ("PMCG1-030", 3),  # ジュゴン
                ("PMCG1-060", 3),  # コラッタ
                ("PMCG1-077", 3),  # オーキドはかせ
                ("PMCG1-074", 4),  # マサキ
                ("PMCG1-073", 3),  # ポケモンいれかえ
                ("PMCG1-071", 2),  # きずぐすり
                ("PMCG1-081", 4),  # プラスパワー
                ("PMCG1-072", 3),  # 突風
                ("PMCG1-090", 3),  # パソコン通信
                ("PMCG1-076", 2),  # エネルギー回収
                ("PMCG1-102", 12),  # 闘エネルギー
                ("PMCG1-099", 10),  # 水エネルギー
            ),
        ),
        # デッキ B2: フシギバナ・パラセクト。たねポケモンを 8 枚から 10 枚に（モンジャラ 2 枚）、フシギソウ 4 → 2・パラセクト 3 → 2 にして
        # 余りがちな進化カードを減らし、ポケモン育て屋さん 2 枚でフシギソウを経ない進化も選べるようにした（フシギソウは残し、通常の進化も使う）
        PresetDeck(
            "venusaur-parasect-v2",
            "フシギバナ・パラセクト（第2版）",
            (
                ("PMCG1-001", 4),  # フシギダネ
                ("PMCG1-008", 2),  # フシギソウ
                ("PMCG1-011", 3),  # フシギバナ
                ("PMCG2-003", 4),  # パラス
                ("PMCG2-010", 2),  # パラセクト
                ("PMCG1-007", 2),  # モンジャラ
                ("PMCG1-077", 3),  # オーキドはかせ
                ("PMCG1-074", 3),  # マサキ
                ("PMCG1-073", 3),  # ポケモンいれかえ
                ("PMCG1-071", 2),  # きずぐすり
                ("PMCG1-081", 2),  # プラスパワー
                ("PMCG1-072", 2),  # 突風
                ("PMCG1-090", 3),  # パソコン通信
                ("PMCG1-076", 2),  # エネルギー回収
                ("PMCG1-093", 2),  # ポケモン交換おじさん
                ("PMCG1-094", 2),  # ポケモン育て屋さん
                ("PMCG1-097", 19),  # 草エネルギー
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

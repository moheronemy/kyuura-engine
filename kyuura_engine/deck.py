"""デッキの検査（『オフィシャルブック2000』p.308「対戦の前に」）。"""

from __future__ import annotations

from collections import Counter
from types import MappingProxyType
from typing import Mapping, Sequence

from .cards import CardPool, load_card_pool
from .errors import DeckValidationError
from .rules import RULES_2000_02_14, RuleSet


def expand_decklist(counts: Mapping[str, int]) -> list[str]:
    """{カード id: 枚数} を、カード id を枚数ぶん並べたリストにする。"""
    cards: list[str] = []
    for card_id, count in counts.items():
        cards.extend([card_id] * count)
    return cards


# v0.71（docs/reprint-text-variants-v0.71.md 7 章）: 同じカードの名前の書き方の違い（写しの名前のまま持つ。名前 → デッキの同じ名前の数え方で使う名前）。名前の空白を一律に
# 除かない（ここに挙げた組だけ）。写しにどちらの名前もあることは tests/test_reprint_text_variants_v0_71.py が確かめる
SAME_NAME_SPELLINGS: Mapping[str, str] = MappingProxyType({
    "ポケモン図鑑HANDY505": "ポケモン図鑑 HANDY505",  # ポケモンジム第1弾タケシ・第3弾カツラ（GD1-022・GD5-023）と第1弾（PMCG1-082）
})


def same_name(name: str) -> str:
    """デッキの「同じ名前は 4 枚まで」（p.308）で数える名前（``SAME_NAME_SPELLINGS`` の書き方の違いをまとめる。ほかの名前はそのまま）。"""
    return SAME_NAME_SPELLINGS.get(name, name)


def deck_problems(cards: Sequence[str], pool: CardPool | None = None, rules: RuleSet = RULES_2000_02_14) -> list[str]:
    """デッキの問題点を返す。問題がなければ空のリスト。"""
    pool = pool or load_card_pool()
    problems: list[str] = []
    if len(cards) != rules.deck_size:
        problems.append(f"DECK_SIZE: デッキはぴったり {rules.deck_size} 枚（{len(cards)} 枚）")

    unknown = sorted({c for c in cards if c not in pool.definitions})
    if unknown:
        problems.append(f"UNKNOWN_CARD: このエンジンのカードデータにないカード {unknown}")
    known = [c for c in cards if c in pool.definitions]

    unsupported = sorted({c for c in known if not pool.is_playable(c)})
    for card_id in unsupported:
        definition = pool.get(card_id)
        reasons = "; ".join(definition.unsupported_reasons) or "v0.1 の対戦用のカードの組に入っていない"
        problems.append(f"UNSUPPORTED_CARD: {card_id} {definition.name_ja}（{reasons}）")

    # 同じ名前は 4 枚まで。基本エネルギーカードだけは制限なし。名前が同じなら別のカードでも同じ名前（p.308）
    names = Counter(same_name(pool.get(c).name_ja) for c in known if not pool.get(c).is_basic_energy)
    for name, count in sorted(names.items()):
        if count > rules.max_copies_per_name:
            problems.append(f"TOO_MANY_COPIES: 「{name}」が {count} 枚（同じ名前は {rules.max_copies_per_name} 枚まで）")

    # たねポケモン（ベイビィポケモン）を必ず入れる（p.308）
    if not any(pool.get(c).is_basic_pokemon for c in known):
        problems.append("NO_BASIC_POKEMON: たねポケモンが入っていない")
    return problems


def validate_deck(cards: Sequence[str], pool: CardPool | None = None, rules: RuleSet = RULES_2000_02_14) -> None:
    problems = deck_problems(cards, pool, rules)
    if problems:
        raise DeckValidationError(problems)

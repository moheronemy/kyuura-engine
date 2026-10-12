"""カードの定義（印刷された情報）と、kyuura のデータの読み込み。

カードの定義は対戦中に変わらない値だけを持ちます（HP・ワザ・弱点など）。
ダメージやついているエネルギーなど、対戦中の状態は ``state.py`` が持ちます。

読み込むときに、各カード・各ワザが v0.1 で処理できるかを分類します。処理できないものは
``supported=False`` と理由を持たせ、デッキに入れられないようにします。効果のあるワザを
「ダメージだけのワザ」として扱うことはしません。
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from importlib import resources
from typing import Iterable


class EnergyType(str, Enum):
    GRASS = "grass"
    FIRE = "fire"
    WATER = "water"
    LIGHTNING = "lightning"
    PSYCHIC = "psychic"
    FIGHTING = "fighting"
    COLORLESS = "colorless"
    DARKNESS = "darkness"
    METAL = "metal"

    @property
    def ja(self) -> str:
        return _TYPE_JA[self]


_TYPE_JA = {
    EnergyType.GRASS: "草",
    EnergyType.FIRE: "炎",
    EnergyType.WATER: "水",
    EnergyType.LIGHTNING: "雷",
    EnergyType.PSYCHIC: "超",
    EnergyType.FIGHTING: "闘",
    EnergyType.COLORLESS: "無色",
    EnergyType.DARKNESS: "悪",
    EnergyType.METAL: "鋼",
}


@dataclass(frozen=True)
class Attack:
    index: int
    name_ja: str
    name_en: str | None
    cost: tuple[EnergyType, ...]
    damage: int | None
    damage_display: str | None
    text_ja: str | None
    text_en: str | None
    supported: bool
    unsupported_reason: str | None


@dataclass(frozen=True)
class CardDefinition:
    id: str
    name_ja: str
    name_en: str | None
    category: str  # "pokemon" | "trainer" | "energy"
    supported: bool
    unsupported_reasons: tuple[str, ...]
    # ポケモン
    stage: str | None = None
    hp: int | None = None
    pokemon_type: EnergyType | None = None
    weakness: EnergyType | None = None
    resistance: EnergyType | None = None
    resistance_value: int = 0
    retreat_cost: int | None = None
    attacks: tuple[Attack, ...] = ()
    # エネルギー
    energy_kind: str | None = None
    provides: EnergyType | None = None

    @property
    def is_basic_pokemon(self) -> bool:
        # ベイビィポケモンも対戦準備ではたねポケモンと同様に扱う（p.308）が、ベイビィは v0.1 では未対応
        return self.category == "pokemon" and self.stage == "basic"

    @property
    def is_basic_energy(self) -> bool:
        return self.category == "energy" and self.energy_kind == "basic"


def can_pay_cost(cost: Iterable[EnergyType], provided: Iterable[EnergyType]) -> bool:
    """ワザに必要なエネルギーが足りているか（p.320）。

    色の指定がある分は同じ色で、「無色」の分はどの色でも払える。多くついていてもよい。
    v0.1 のエネルギーは基本エネルギーだけ（1 枚がちょうど 1 個のエネルギー）なので、
    色ごとの数と合計の数を比べれば足りる。
    """
    need = Counter(cost)
    have = Counter(provided)
    for energy_type, count in need.items():
        if energy_type is EnergyType.COLORLESS:
            continue
        if have[energy_type] < count:
            return False
    return sum(have.values()) >= sum(need.values())


def _classify_attack(index: int, raw: dict) -> Attack:
    name = raw["name"]
    text = raw.get("text") or {}
    damage = raw.get("damage")
    reasons: list[str] = []
    if text.get("ja") is not None or text.get("en") is not None:
        reasons.append("ワザの効果（説明文）は未実装")
    if damage is None or damage.get("base") is None:
        reasons.append("ダメージの数字がないワザは未実装")
    elif damage.get("modifier") is not None:
        reasons.append(f"ダメージの「{damage['modifier']}」（説明文で変わるダメージ）は未実装")
    elif damage["base"] <= 0 or damage["base"] % 10 != 0:
        reasons.append("ダメージが 10 の倍数の正の数ではない")
    if name.get("ja") is None:
        reasons.append("日本語のワザ名がない")
    return Attack(
        index=index,
        name_ja=name.get("ja") or "",
        name_en=name.get("en"),
        cost=tuple(EnergyType(c) for c in raw["cost"]),
        damage=None if damage is None else damage.get("base"),
        damage_display=None if damage is None else damage.get("display"),
        text_ja=text.get("ja"),
        text_en=text.get("en"),
        supported=not reasons,
        unsupported_reason="; ".join(reasons) or None,
    )


def classify_record(record: dict) -> CardDefinition:
    """kyuura の data/cards.json の 1 件から、カードの定義を作る。"""
    name = record["name"]
    category = record["category"]
    common = dict(id=record["id"], name_ja=name.get("ja") or "", name_en=name.get("en"), category=category)

    if category == "trainer":
        return CardDefinition(**common, supported=False, unsupported_reasons=("トレーナーカードの効果は未実装",))

    if category == "energy":
        energy = record["energy"]
        reasons = []
        if energy["kind"] != "basic":
            reasons.append("特殊エネルギーは未実装")
        if len(energy["provides"]) != 1:
            reasons.append("1 種類のエネルギーを 1 個出す基本エネルギーではない")
        provides = EnergyType(energy["provides"][0]) if len(energy["provides"]) == 1 else None
        return CardDefinition(
            **common,
            supported=not reasons,
            unsupported_reasons=tuple(reasons),
            energy_kind=energy["kind"],
            provides=provides,
        )

    if category != "pokemon":
        return CardDefinition(**common, supported=False, unsupported_reasons=(f"未知のカードの種類 {category}",))

    pokemon = record["pokemon"]
    reasons = []
    if pokemon["stage"] != "basic":
        reasons.append(f"{pokemon['stage']}（進化・ベイビィ）は未実装")
    if pokemon["powers"]:
        reasons.append("ポケモンパワー（特殊能力）は未実装")
    if pokemon.get("rules_text") is not None:
        reasons.append("ルール文のあるポケモンは未実装")
    if len(pokemon["types"]) != 1:
        reasons.append("タイプが 1 つではない")
    if pokemon["hp"] % 10 != 0:
        reasons.append("HP が 10 の倍数ではない")
    weakness = None
    if len(pokemon["weaknesses"]) > 1:
        reasons.append("弱点が 2 つ以上ある")
    elif pokemon["weaknesses"]:
        w = pokemon["weaknesses"][0]
        if w["operator"] != "×" or w["value"] != 2:
            reasons.append("弱点が「×2」ではない")
        weakness = EnergyType(w["type"])
    resistance = None
    resistance_value = 0
    if len(pokemon["resistances"]) > 1:
        reasons.append("抵抗力が 2 つ以上ある")
    elif pokemon["resistances"]:
        r = pokemon["resistances"][0]
        if r["operator"] != "-":
            reasons.append("抵抗力が「-」ではない")
        resistance = EnergyType(r["type"])
        resistance_value = r["value"]
    attacks = tuple(_classify_attack(i, a) for i, a in enumerate(pokemon["attacks"]))
    if not attacks:
        reasons.append("ワザがない")
    for attack in attacks:
        if not attack.supported:
            reasons.append(f"ワザ「{attack.name_ja}」: {attack.unsupported_reason}")
    return CardDefinition(
        **common,
        supported=not reasons,
        unsupported_reasons=tuple(reasons),
        stage=pokemon["stage"],
        hp=pokemon["hp"],
        pokemon_type=EnergyType(pokemon["types"][0]) if pokemon["types"] else None,
        weakness=weakness,
        resistance=resistance,
        resistance_value=resistance_value,
        retreat_cost=pokemon["retreat_cost"],
        attacks=attacks,
    )


@dataclass(frozen=True)
class CardPool:
    """読み込んだカードの定義と、出典の情報。"""

    definitions: dict[str, CardDefinition]
    playable_ids: frozenset[str]
    source: dict

    def get(self, card_id: str) -> CardDefinition:
        return self.definitions[card_id]

    def is_playable(self, card_id: str) -> bool:
        """v0.1 の対戦（デッキ）に使えるか。v0.1 のカードの組に入っていて、すべての要素に対応していること。"""
        return card_id in self.playable_ids


def pool_from_extract(extract: dict) -> CardPool:
    definitions = {record["id"]: classify_record(record) for record in extract["cards"]}
    playable = frozenset(
        card_id for card_id in extract["pool_v0_1"] if definitions[card_id].supported
    )
    return CardPool(definitions=definitions, playable_ids=playable, source=dict(extract["source"]))


def read_extract() -> dict:
    data = resources.files("kyuura_engine").joinpath("data", "kyuura_cards.json")
    return json.loads(data.read_text(encoding="utf-8"))


def read_verification() -> dict:
    data = resources.files("kyuura_engine").joinpath("data", "card_verification.json")
    return json.loads(data.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_card_pool() -> CardPool:
    """同梱の kyuura の写し（kyuura_engine/data/kyuura_cards.json）を読む。"""
    return pool_from_extract(read_extract())

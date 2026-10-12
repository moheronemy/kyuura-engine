"""カードの定義（印刷された情報）と、kyuura のデータの読み込み。

カードの定義は対戦中に変わらない値だけを持ちます（HP・ワザ・弱点など）。
ダメージやついているエネルギーなど、対戦中の状態は ``state.py`` が持ちます。

読み込むときに、各カード・各ワザが対戦で使えるかを分類します（``supported`` と理由）。分類は、
データの値ではなく、エンジンが実装しているかで決めます。

- エンジンの中心部分で扱える形か（たねポケモン・タイプ 1 つ・弱点 ×2 など。進化・ポケモンパワーは未実装）
- ワザ・トレーナーの効果の実装が、効果の登録表（``effects.EffectRegistry``）に登録されているか

説明文が空であることは、実装がある証拠にしません。使えないカードはデッキに入れられません。
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, replace
from enum import Enum
from functools import lru_cache
from importlib import resources
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Iterable, Mapping

if TYPE_CHECKING:
    from .effects import EffectRegistry


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
    supported: bool  # 効果の登録表に実装があり、データと合うか（登録表は CardPool.effects）
    unsupported_reason: str | None
    damage_modifier: str | None = None  # データの damage.modifier（「+」「×」など）


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
    # トレーナー（kyuura の trainer.text・trainer.kinds。効果の処理には使わず、登録した実装との照合に使う）
    trainer_text_ja: str | None = None
    trainer_text_en: str | None = None
    trainer_kinds: tuple[str, ...] = ()

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


def _parse_attack(index: int, raw: dict) -> Attack:
    """ワザのデータだけを読む。使えるかどうかは ``classify_record`` が効果の登録表で決める。"""
    name = raw["name"]
    text = raw.get("text") or {}
    damage = raw.get("damage")
    return Attack(
        index=index,
        name_ja=name.get("ja") or "",
        name_en=name.get("en"),
        cost=tuple(EnergyType(c) for c in raw["cost"]),
        damage=None if damage is None else damage.get("base"),
        damage_display=None if damage is None else damage.get("display"),
        text_ja=text.get("ja"),
        text_en=text.get("en"),
        supported=False,
        unsupported_reason="効果の登録表で確かめていない",
        damage_modifier=None if damage is None else damage.get("modifier"),
    )


def classify_record(record: dict, effects: EffectRegistry | None = None) -> CardDefinition:
    """kyuura の data/cards.json の 1 件から、カードの定義を作る。

    値はデータのまま持つ。使えるかどうか（``supported``）は、エンジンの中心部分で扱える形かと、
    効果の登録表 ``effects``（省略時は ``effects.DEFAULT_EFFECTS``）に実装があるかで決める。
    """
    if effects is None:
        from .effects import DEFAULT_EFFECTS as effects
    name = record["name"]
    category = record["category"]
    common = dict(id=record["id"], name_ja=name.get("ja") or "", name_en=name.get("en"), category=category)

    if category == "trainer":
        # トレーナーは、効果の登録表にカード id で実装が登録され、登録したときに照合した名前・文面と
        # データが合うときだけ使える（v0.2b）。説明文の有無や名前では決めない
        trainer = record["trainer"]
        text = trainer.get("text") or {}
        definition = CardDefinition(
            **common,
            supported=False,
            unsupported_reasons=(),
            trainer_text_ja=text.get("ja"),
            trainer_text_en=text.get("en"),
            trainer_kinds=tuple(trainer.get("kinds") or ()),
        )
        problem = effects.trainer_problem(definition)
        return replace(definition, supported=problem is None, unsupported_reasons=() if problem is None else (problem,))

    if category == "energy":
        # 基本エネルギーは効果を持たず、公式ルールの規定（p.310・p.318・p.320）だけで扱う（エンジンの中心部分）。
        # 特殊エネルギーは効果の実装が要るが、登録表に特殊エネルギーの欄がまだないので未対応
        energy = record["energy"]
        reasons = []
        if energy["kind"] != "basic":
            reasons.append("特殊エネルギーの効果の実装が登録されていない")
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
    attacks = tuple(_annotate_attack(record["id"], _parse_attack(i, a), effects) for i, a in enumerate(pokemon["attacks"]))
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


def _annotate_attack(card_id: str, attack: Attack, effects: EffectRegistry) -> Attack:
    problem = effects.attack_problem(card_id, attack)
    return replace(attack, supported=problem is None, unsupported_reason=problem)


@dataclass(frozen=True)
class CardPool:
    """読み込んだカードの定義と、出典の情報。``effects`` は分類に使った効果の登録表（対戦でも同じものを使う）。"""

    definitions: Mapping[str, CardDefinition]
    playable_ids: frozenset[str]
    source: Mapping[str, Any]
    effects: EffectRegistry

    def get(self, card_id: str) -> CardDefinition:
        return self.definitions[card_id]

    def is_playable(self, card_id: str) -> bool:
        """対戦（デッキ）に使えるか。対戦用のカードの組（写しの pool_v0_1〜pool_v0_3b）に入っていて、
        すべての要素に対応していること。"""
        return card_id in self.playable_ids


# 写しの中の、対戦用のカードの組（参照カード reference_only はデッキに入れない）
POOL_KEYS = ("pool_v0_1", "pool_v0_2b", "pool_v0_2c", "pool_v0_2d", "pool_v0_2e", "pool_v0_2f", "pool_v0_3a", "pool_v0_3b")


def pool_from_extract(extract: dict, effects: EffectRegistry | None = None) -> CardPool:
    if effects is None:
        from .effects import DEFAULT_EFFECTS as effects
    definitions = {record["id"]: classify_record(record, effects) for record in extract["cards"]}
    playable = frozenset(
        card_id for key in POOL_KEYS for card_id in extract.get(key, ()) if definitions[card_id].supported
    )
    # load_card_pool の結果はプロセス内で共有されるので、書き換えられないようにする
    return CardPool(
        definitions=MappingProxyType(definitions),
        playable_ids=playable,
        source=MappingProxyType(dict(extract["source"])),
        effects=effects,
    )


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

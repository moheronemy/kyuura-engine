"""カードの定義（印刷された情報）と、kyuura のデータの読み込み。

カードの定義は対戦中に変わらない値だけを持ちます（HP・ワザ・弱点など）。
ダメージやついているエネルギーなど、対戦中の状態は ``state.py`` が持ちます。

読み込むときに、各カード・各ワザが対戦で使えるかを分類します（``supported`` と理由）。分類は、
データの値ではなく、エンジンが実装しているかで決めます。

- エンジンの中心部分で扱える形か（たねポケモンと 1 進化ポケモン（v0.4a）・2 進化ポケモン（v0.4c）・タイプ 1 つ・弱点 ×2
  など。ベイビィは未実装）
- ワザ・トレーナー・ポケモンパワー（特殊能力。v0.5）の効果の実装が、効果の登録表（``effects.EffectRegistry``）に登録されて
  いるか。ポケモンパワーを持つカードは、すべてのパワーが登録されているときだけ使える（パワーを持つカードを一括で対応にしない）

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
class Power:
    """ポケモンパワー（特殊能力。p.311・p.323。v0.5）の印刷された情報（kyuura の ``pokemon.powers`` の 1 件）。

    ``kind`` は kyuura の値（旧裏の範囲では ``"pokemon_power"``）。``text_ja`` は印刷の文面（照合用。処理の根拠ではない）。
    使えるか（``supported``）は、効果の登録表に実装があり、データと合うかで決める（``Attack`` と同じ）。
    """

    index: int
    name_ja: str
    name_en: str | None
    kind: str
    text_ja: str | None
    text_en: str | None
    supported: bool
    unsupported_reason: str | None


# 進化の重なりの、下から順の段階（v0.4c。p.316・p.319 の「たねポケモンカード」+「進化カード」+「進化カード」）。
# いちばん下はたねポケモン、その上は 1 進化、その上は 2 進化。ベイビィ（p.319 の C・D）は未対応
EVOLUTION_STAGES = ("basic", "stage1", "stage2")


@dataclass(frozen=True)
class CardDefinition:
    id: str
    name_ja: str
    name_en: str | None
    category: str  # "pokemon" | "trainer" | "energy"
    supported: bool
    unsupported_reasons: tuple[str, ...]
    # ポケモン
    stage: str | None = None  # "basic"（たね）・"stage1"（1 進化。v0.4a）・"stage2"（2 進化。v0.4c）。"baby" は未対応
    evolves_from: str | None = None  # 進化カードの「○○○○から進化」の名前（kyuura の pokemon.evolves_from.ja。v0.4a）
    # 2 進化カードだけ（v0.25）: 「○○○○から進化」の名前（``evolves_from``）の 1 進化カードが、同じ写しのカードのデータで
    # 「△△から進化」とする名前（重複を除き、並べたもの）。1 進化を飛ばして 2 進化させる効果（ポケモン育て屋さん）で、正しい系統の
    # たねポケモンかを確かめるのに使う（docs/pokemon-breeder-v0.25.md）。写しにその名前の 1 進化カードがなければ ()（確かめられない）。
    # 同じ写し（``pool_from_extract``）の中で求め、名前の一部・形容詞（「サカキの」など）で推測しない
    stage1_evolves_from: tuple[str, ...] = ()
    hp: int | None = None
    pokemon_type: EnergyType | None = None
    weakness: EnergyType | None = None
    resistance: EnergyType | None = None
    resistance_value: int = 0
    retreat_cost: int | None = None
    attacks: tuple[Attack, ...] = ()
    powers: tuple[Power, ...] = ()  # ポケモンパワー（v0.5）。カードに印刷された順
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
    def is_stage1_pokemon(self) -> bool:
        """1 進化ポケモンのカード（v0.4a）。手札から「○○○○から進化」の名前のたねポケモンに重ねる（p.309・p.310）。"""
        return self.category == "pokemon" and self.stage == "stage1"

    @property
    def is_stage2_pokemon(self) -> bool:
        """2 進化ポケモンのカード（v0.4c）。手札から「○○○○から進化」の名前の 1 進化ポケモンに重ねる（p.309・p.316・p.319）。"""
        return self.category == "pokemon" and self.stage == "stage2"

    @property
    def is_evolution_pokemon(self) -> bool:
        """エンジンが進化の手順で扱う段階の進化カード（1 進化・2 進化。v0.4c）。ベイビィは含まない。"""
        return self.is_stage1_pokemon or self.is_stage2_pokemon

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
    evolves_from = (pokemon.get("evolves_from") or {}).get("ja")
    if pokemon["stage"] in ("stage1", "stage2"):
        # 1 進化（v0.4a）・2 進化（v0.4c）。「○○○○から進化」の名前がなければ、何に重ねるか決まらない（p.309・p.324）。
        # 2 進化の段階だからといって一括で対応にはしない（ワザの登録・ポケモンパワーなど、ほかの条件はカードごと）
        if not evolves_from:
            reasons.append(f"{'1' if pokemon['stage'] == 'stage1' else '2'} 進化なのに進化元の名前がない")
    elif pokemon["stage"] != "basic":
        reasons.append(f"{pokemon['stage']}（ベイビィなど）は未実装")
    # ポケモンパワー（v0.5）: 1 つずつ、効果の登録表に実装があり、データと合うか（説明文の有無・名前では決めない）
    powers = tuple(_annotate_power(record["id"], _parse_power(i, w), effects) for i, w in enumerate(pokemon["powers"]))
    for power in powers:
        if not power.supported:
            reasons.append(f"ポケモンパワー「{power.name_ja}」: {power.unsupported_reason}")
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
    parsed = tuple(_parse_attack(i, a) for i, a in enumerate(pokemon["attacks"]))
    attacks = tuple(_annotate_attack(record["id"], attack, effects, parsed) for attack in parsed)
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
        evolves_from=evolves_from,
        hp=pokemon["hp"],
        pokemon_type=EnergyType(pokemon["types"][0]) if pokemon["types"] else None,
        weakness=weakness,
        resistance=resistance,
        resistance_value=resistance_value,
        retreat_cost=pokemon["retreat_cost"],
        attacks=attacks,
        powers=powers,
    )


def _annotate_attack(card_id: str, attack: Attack, effects: EffectRegistry, attacks: tuple[Attack, ...]) -> Attack:
    # attacks（v0.27）: そのカードのワザのすべて。ほかのワザを指す登録（「つるぎのまい」が変える「きりさく」）が合うかも確かめる
    problem = effects.attack_problem(card_id, attack, attacks)
    return replace(attack, supported=problem is None, unsupported_reason=problem)


def _parse_power(index: int, raw: dict) -> Power:
    """ポケモンパワーのデータだけを読む（v0.5）。使えるかどうかは効果の登録表で決める。"""
    name = raw["name"]
    text = raw.get("text") or {}
    return Power(
        index=index,
        name_ja=name.get("ja") or "",
        name_en=name.get("en"),
        kind=raw.get("kind") or "",
        text_ja=text.get("ja"),
        text_en=text.get("en"),
        supported=False,
        unsupported_reason="効果の登録表で確かめていない",
    )


def _annotate_power(card_id: str, power: Power, effects: EffectRegistry) -> Power:
    problem = effects.power_problem(card_id, power)
    return replace(power, supported=problem is None, unsupported_reason=problem)


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
        """対戦（デッキ）に使えるか。対戦用のカードの組（写しの pool_v0_1〜pool_v0_17b）に入っていて、
        すべての要素に対応していること。"""
        return card_id in self.playable_ids


# 写しの中の、対戦用のカードの組（参照カード reference_only はデッキに入れない）
POOL_KEYS = (
    "pool_v0_1", "pool_v0_2b", "pool_v0_2c", "pool_v0_2d", "pool_v0_2e", "pool_v0_2f", "pool_v0_3a", "pool_v0_3b", "pool_v0_3c",
    "pool_v0_4a", "pool_v0_4b", "pool_v0_4c", "pool_v0_4d",  # pool_v0_4d は v0.4d（バタフリー）
    "pool_v0_5",  # v0.5（フシギダネ・フシギソウ・フシギバナ）
    "pool_v0_6",  # v0.6（ゼニガメ・カメール・カメックス）
    "pool_v0_7",  # v0.7（ケーシィ・ユンゲラー・フーディン）
    "pool_v0_8",  # v0.8（ロケット団のベトベター・ベトベトン）
    "pool_v0_9",  # v0.9（化石の秘密のゴース・ゴースト）
    "pool_v0_10",  # v0.10（ゴーリキー・カイリキー。ワンリキーは v0.1 から）
    "pool_v0_11",  # v0.11（サカキのワンリキー・サカキのゴーリキー・サカキのカイリキー）
    "pool_v0_12",  # v0.12（R団のファイヤー）
    "pool_v0_13",  # v0.13（第4弾のゼニガメ・わるいカメール）
    "pool_v0_17a",  # v0.17a（モンジャラ・サカキのニャース。既存のワザの要素だけで実装）
    "pool_v0_17b",  # v0.17b（R団のカビゴン。わるいねぞう・たおれこむ）
    "pool_v0_18c",  # v0.18c（ナツメのヤドン。ぐうたらこうげき。既存の要素だけ）
    "pool_v0_19",  # v0.19（オーキドはかせ。トレーナー。既存のトレーナーの登録・ドローの処理）
    "pool_v0_21",  # v0.21（突風。トレーナー。既存のトレーナーの登録・トレーナーの決定・ポケモンいれかえと同じ入れ替えの処理）
    "pool_v0_22",  # v0.22（パソコン通信。トレーナー。既存のトレーナーの登録・2 段階のトレーナーの決定・ゾーンの共通の関数）
    "pool_v0_23",  # v0.23（エネルギー回収。トレーナー。2 段階のトレーナーの決定・手札のトラッシュとトラッシュから手札に加える共通の関数）
    "pool_v0_24",  # v0.24（ポケモン交換おじさん。トレーナー。2 段階のトレーナーの決定・手札から山札にもどす・山札から選び出して見せる共通の関数）
    "pool_v0_25",  # v0.25（ポケモン育て屋さん。トレーナー。2 段階のトレーナーの決定・進化の手順の共通の関数・たね + 2 進化の重なり）
    "pool_v0_27",  # v0.27（ストライク。次の自分の番のワザのダメージを p.321 の 2 段階で変える持続する効果「つるぎのまい」・きりさく）
    "pool_v0_28",  # v0.28（既存の効果の型の登録だけで対応にしたポケモン 10 枚。ラプラス・スターミー・トサキント・アズマオウ・カイロスほか）
    "pool_v0_29",  # v0.29（既存の効果の型の登録だけで対応にしたポケモン 14 枚。kyuura データの採用。ニョロモ・ロケット団・リーダーズスタジアムのたねポケモン）
    "pool_v0_30",  # v0.30（自分の「炎」エネルギーカードを 1 枚トラッシュしてダメージを与えるワザの共通の型。ヒトカゲ・リザード・ウインディ・ブーバー・第4弾のポニータ）
)


def pool_from_extract(extract: dict, effects: EffectRegistry | None = None) -> CardPool:
    if effects is None:
        from .effects import DEFAULT_EFFECTS as effects
    definitions = {record["id"]: classify_record(record, effects) for record in extract["cards"]}
    definitions = _with_stage1_lineage(definitions)
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


def _with_stage1_lineage(definitions: dict[str, CardDefinition]) -> dict[str, CardDefinition]:
    """2 進化カードの定義に、進化元の 1 進化カードの進化元の名前（``stage1_evolves_from``）を加える（v0.25）。

    同じ写しの 1 進化カード（段階が stage1 のポケモンのカード。対戦に使えるかは問わない）のうち、名前（日本語の名前の完全一致）が
    2 進化カードの「○○○○から進化」と同じものの「○○○○から進化」を集める。名前の一部・形容詞で推測しない。"""
    stage1 = {}
    for definition in definitions.values():
        if definition.is_stage1_pokemon and definition.evolves_from:
            stage1.setdefault(definition.name_ja, set()).add(definition.evolves_from)
    return {
        card_id: replace(definition, stage1_evolves_from=tuple(sorted(stage1.get(definition.evolves_from, ()))))
        if definition.is_stage2_pokemon else definition
        for card_id, definition in definitions.items()
    }


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

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
    provides: EnergyType | None = None  # 基本エネルギーカードのタイプ。特殊エネルギーは None（出すエネルギーは効果の登録表の実装が決める。v0.58）
    # v0.58（docs/stadium-reuse-special-energy-v0.58.md）: 特殊エネルギーの kyuura の energy.text（効果の処理には使わず、登録した実装との照合に使う）
    energy_text_ja: str | None = None
    energy_text_en: str | None = None
    # トレーナー（kyuura の trainer.text・trainer.kinds。効果の処理には使わず、登録した実装との照合に使う）
    trainer_text_ja: str | None = None
    trainer_text_en: str | None = None
    trainer_kinds: tuple[str, ...] = ()
    # v0.47（docs/fossil-hidden-info-v0.47.md 2 章）: ポケモンとして場に出せるトレーナーカード（なにかの化石・ピッピ人形）の、場にいるあいだの定義（場での役割）
    # だけに付ける印（"fossil"・"doll"）。印刷の定義（写しから読んだ ``category`` が "trainer" の定義）はいつも None で、変えない。場での役割の定義は効果の登録表
    # （``effects.PlayAsPokemon.in_play_definition``）が印刷の定義から別のインスタンスとして作り、``GameState.card_def`` が、そのカードが場にいるあいだだけ返す
    play_role: str | None = None
    # v0.82（docs/energy-discard-return-v0.82.md 5 章）: ポケモンのルール文「「（このカードの名前）」はデッキに1枚までしか入れることができません。」の枚数（ひかるリザードン
    # neo4-025）。同じ名前のカードの枚数の上限（デッキの検査 ``deck.deck_problems``）。ほかのルール文のあるポケモンは今までどおり未対応
    deck_limit: int | None = None

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
        """基本エネルギーカード（印刷の種類）。特殊エネルギーカード（レインボーエネルギーを含む）は、手札・山札・トラッシュでは基本エネルギーカードではない
        （v0.58。kyuura の ERR-ENERGY-RETRIEVAL）。場でどの色のエネルギーとして使えるかは ``effects.energy_units`` が決める。"""
        return self.category == "energy" and self.energy_kind == "basic"

    @property
    def is_special_energy(self) -> bool:
        """特殊エネルギーカード（v0.58）。"""
        return self.category == "energy" and self.energy_kind == "special"


# v0.67（docs/secret-plan-preflight-v0.67.md 3 章）: うらにしてベンチに出したカード（マチスの秘策）の、うらのあいだのカードの定義で、読めない項目
FACE_DOWN_HIDDEN_FIELDS = frozenset({"id", "name_ja", "name_en", "hp", "pokemon_type", "weakness", "resistance", "resistance_value", "retreat_cost", "attacks"})


class FaceDownDefinition(CardDefinition):
    """うらにしてベンチに出したカード（v0.67。マチスの秘策）の、うらのあいだのカードの定義（``GameState.card_def``）。

    「うらになっている限り、「たねポケモン」としてあつかわれる」ので、種類は "pokemon"・段階は "basic"。特殊能力はない（うらのカード自身の特殊能力ははたらかない）。
    ほかの項目（``FACE_DOWN_HIDDEN_FIELDS``。名前・HP・タイプ・弱点・抵抗力・にげる・ワザ・カードの id）は本文が決めないので、読むと ``HiddenPropertyRead``（FD1）。
    決まった値（化石・人形の HP 10 など）を置かない。印刷の定義・写しは変えない（``printed_def`` は本当のカードの定義のまま）。"""

    def __getattribute__(self, name: str):
        if name in FACE_DOWN_HIDDEN_FIELDS:
            from .errors import HiddenPropertyRead

            raise HiddenPropertyRead(name)
        return super().__getattribute__(name)

    def __repr__(self) -> str:
        return "FaceDownDefinition()"

    def __eq__(self, other) -> bool:
        return isinstance(other, FaceDownDefinition)

    def __hash__(self) -> int:
        return hash("FaceDownDefinition")


FACE_DOWN_DEFINITION = FaceDownDefinition(id="", name_ja="", name_en=None, category="pokemon", supported=True, unsupported_reasons=(), stage="basic")


def can_pay_cost(cost: Iterable[EnergyType], provided: Iterable[EnergyType]) -> bool:
    """ワザに必要なエネルギーが足りているか（p.320）。

    色の指定がある分は同じ色で、「無色」の分はどの色でも払える。多くついていてもよい。
    ``provided`` は 1 個ずつのエネルギーのタイプ（基本エネルギーカードは 1 枚がちょうど 1 個）。色ごとの数と合計の数を比べれば足りる。
    特殊エネルギー（1 枚で 2 個・どの色にもなる 1 個。v0.58）を含む支払いは ``can_pay_with_units``。
    """
    need = Counter(cost)
    have = Counter(provided)
    for energy_type, count in need.items():
        if energy_type is EnergyType.COLORLESS:
            continue
        if have[energy_type] < count:
            return False
    return sum(have.values()) >= sum(need.values())


def can_pay_with_units(cost: Iterable[EnergyType], units: Iterable[frozenset[EnergyType]]) -> bool:
    """ワザに必要なエネルギーを、ついているエネルギー（1 個ずつの、そのエネルギーとして使えるタイプの集まり）で払えるか（v0.58。p.320）。

    無色 2 個エネルギーは「無色」の 1 個が 2 つ、レインボーエネルギーはどの色にもなる 1 個（合計 1 個。2 つの記号に数えない）。色の指定のある記号には、その色に
    なれる 1 個を 1 つずつ割り当て（割り当ての探索。レインボーエネルギーの色は払い方に合わせて選べる）、「無色」の記号は残りのどの 1 個でも払う。「無色」の 1 個は
    色の指定のある記号を払えない（「無色」エネルギーは、ほかの色のエネルギーのかわりにならない）。1 個が 1 つのタイプだけなら ``can_pay_cost`` と同じ答え。"""
    units = [frozenset(unit) for unit in units]
    cost = list(cost)
    colored = [symbol for symbol in cost if symbol is not EnergyType.COLORLESS]
    if len(units) < len(cost):
        return False
    owner: dict[int, int] = {}  # 1 個の位置 → 割り当てた記号の位置

    def assign(symbol: int, seen: set[int]) -> bool:
        for unit, kinds in enumerate(units):
            if colored[symbol] in kinds and unit not in seen:
                seen.add(unit)
                if unit not in owner or assign(owner[unit], seen):
                    owner[unit] = symbol
                    return True
        return False

    return all(assign(symbol, set()) for symbol in range(len(colored)))


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
        # 特殊エネルギー（v0.58）は、効果の登録表にカード id で実装が登録され、登録したときに照合した名前・文面とデータが合うときだけ使える（トレーナーと同じ）。
        # 出すエネルギーは登録した実装が決める（kyuura の energy.provides が空でも「エネルギーを出さない」と読まない。無色2個エネルギー）
        energy = record["energy"]
        text = energy.get("text") or {}
        reasons = []
        provides = None
        if energy["kind"] == "basic":
            if len(energy["provides"]) != 1:
                reasons.append("1 種類のエネルギーを 1 個出す基本エネルギーではない")
            else:
                provides = EnergyType(energy["provides"][0])
        definition = CardDefinition(
            **common,
            supported=False,
            unsupported_reasons=(),
            energy_kind=energy["kind"],
            provides=provides,
            energy_text_ja=text.get("ja"),
            energy_text_en=text.get("en"),
        )
        if energy["kind"] != "basic":
            problem = effects.energy_problem(definition)
            if problem is not None:
                reasons.append(problem)
        return replace(definition, supported=not reasons, unsupported_reasons=tuple(reasons))

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
    deck_limit = None
    if pokemon.get("rules_text") is not None:
        deck_limit = _deck_limit_rule(record["name"].get("ja") or "", pokemon["rules_text"].get("ja"))
        if deck_limit is None:
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
    if not attacks and not any(power.supported and getattr(effects.power_effect(record["id"], power), "supplies_attacks", False) for power in powers):
        # v0.49: ワザのないポケモンは、今の姿のワザを持たせる特殊能力（メタモンの［へんしん］。``PowerEffect.supplies_attacks``）が登録されているときだけ対応にする
        # （写しでワザのないポケモンはメタモンだけ）
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
        deck_limit=deck_limit,
    )


def _deck_limit_rule(name: str, text: str | None) -> int | None:
    """ポケモンのルール文が、このカード自身の名前の「デッキに1枚まで」だけなら 1（v0.82。ひかるリザードン neo4-025 の「「ひかるリザードン」はデッキに1枚までしか入れることが
    できません。」）。ほかの書き方・ほかの名前・ほかの規定のルール文は None（未対応のまま。ルール文のあるポケモンを一括で対応にしない。ひかるポケモン全体を合わせた上限・
    のちのルールの「ひかるポケモン」の規定を持ち込まない）。"""
    return 1 if name and text == f"「{name}」はデッキに1枚までしか入れることができません。" else None


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
    "pool_v0_31",  # v0.31（v0.30 で保留した 22 枚と、進化元の 7 枚。docs/held-cards-v0.31.md）
    "pool_v0_32",  # v0.32（山札からベンチに出す・ダメージカウンターでダメージが決まる・与えたぶん回復するワザの 13 枚。docs/bench-search-counter-drain-v0.32.md）
    "pool_v0_33",  # v0.33（相手のエネルギーをトラッシュする・コインで失敗する／ダメージを与えられない・控えにもダメージを与えるワザの 15 枚。docs/cd4-opponent-energy-coins-v0.33.md）
    "pool_v0_34",  # v0.34（バリアーに対するコインの見直し・ダメージのあとの決定をまたぐ処理と合わせた 15 枚。ガルーラは保留。docs/barrier-resume-coin-bonus-v0.34.md）
    "pool_v0_35",  # v0.35（可変枚数のコインの先読み・同じダメージ計算の段階の順番の決定と合わせた 5 枚。docs/coin-groups-damage-order-v0.35.md）
    "pool_v0_36",  # v0.36（すなかけ・えんまくなどの手順 4 のコイン・「にげる」ことができない効果・自分を山札にもどす効果と合わせた 11 枚。docs/sand-attack-retreat-lock-v0.36.md）
    "pool_v0_37",  # v0.37（既存の効果の再利用を中心に加えた 15 枚。docs/fifteen-reused-effects-v0.37.md）
    "pool_v0_38",  # v0.38（控えへのダメージ・入れ替え・同じコインの複数の効果・軽減・山札にもどる効果の 15 枚。docs/bench-switch-combined-v0.38.md）
    "pool_v0_39",  # v0.39（じばく・控えへのダメージ・場のポケモンの数でダメージが決まるワザの 15 枚。docs/selfdestruct-spread-count-v0.39.md）
    "pool_v0_40",  # v0.40（場の数・条件付きの効果・入れ替え・カードの移動の 15 枚。docs/count-condition-switch-return-v0.40.md）
    "pool_v0_41",  # v0.41（回復・カウンターの移動・特殊状態の変化を中心とする 15 枚。docs/heal-counter-status-v0.41.md）
    "pool_v0_42",  # v0.42（回復・カウンター操作と、特殊能力を持つ進化系統を中心とする 15 枚。docs/power-decisions-v0.42.md）
    "pool_v0_43",  # v0.43（宣言して使う特殊能力と、場に出たときに使う特殊能力を持つ 9 枚。docs/declared-entry-powers-v0.43.md）
    "pool_v0_44",  # v0.44（場のポケモンを選ぶ・山札をさがす・山札から進化する・場に出てから 1 回だけ使えるワザ・カードの移動のポケモン 14 枚とトレーナー 1 枚。docs/search-evolution-once-attacks-v0.44.md）
    "pool_v0_45",  # v0.45（条件・コイン・特殊状態・エネルギーの処理・ダメージの計算・返す効果・山札のワザのポケモン 15 枚。docs/conditional-damage-energy-v0.45.md）
    "pool_v0_46",  # v0.46（常にはたらく特殊能力を持つ 8 枚と、関連する 3 枚。docs/continuous-powers-v0.46.md）
    "pool_v0_47",  # v0.47（なにかの化石・ピッピ人形と化石のポケモン、見えない情報を扱う 4 枚、トレーナーの使用を禁止する 2 枚。docs/fossil-hidden-info-v0.47.md）
    "pool_v0_48",  # v0.48（ポリゴン 2 枚・モルフォン・ナツメのゴース／ゴースト／ゲンガー・キョウのメタモン。場のポケモンの今有効な最大HP・タイプ・弱点・抵抗力）
    "pool_v0_49",  # v0.49（ナツメのフーディン・メタモン・タケシのキュウコン・思い出させる。ワザの出どころと今の姿）
    "pool_v0_50",  # v0.50（ミュウ・退化スプレー。退化の共通の処理）
    "pool_v0_51",  # v0.51（ナツメのスリーパー・元気のかけら・ポケモンの笛。トラッシュのたねポケモンを持ち主のベンチに出す共通の処理）
    "pool_v0_52",  # v0.52（フジろうじん・ポケモン回収・エリカのハクリュー。場のポケモンを場から手札・山札にもどす共通の処理）
    "pool_v0_53",  # v0.53（エネルギー転送・モンスターボール・ボスのやりかた・タケシの育て方・カスミのなみだ・エリカのお付き・メンテナンス・ダウジングマシーン・リサイクル・夜の廃品回収）
    "pool_v0_54",  # v0.54（にせオーキドはかせ・にせオーキドの逆襲・ギャンブラー・ナツメの眼・カツラの奥の手・エリカ・スパイ作戦・カツラのギャンブル・ミニスカート・ポケモン図鑑 HANDY505）
    "pool_v0_55",  # v0.55（カスミのいかり・ロケット団のおねーさん・礼儀作法・トラッシュ交換・エネルギー・リムーブ・超エネルギーリムーブ・いいきずぐすり・なんでもなおし・ポケモンセンター・ねむれ!ねむれ!・エネルギーサーキュレート・エリカの親切・タケシ・サカキの切り札・ナツメ・ワープポイント）
    "pool_v0_56",  # v0.56（エリカの香水・マチス・ロケット団のワナ・ロケット団員・マチスの交渉・カスミのわがまま・カスミ・キョウ・見えない壁・ロケット団の実験）
    "pool_v0_57",  # v0.57（スタジアム 14 枚。docs/stadiums-v0.57.md）
    "pool_v0_58",  # v0.58（タケシのゴローン・タケシのゴローニャ・ナツメのサイキックコントロール・特殊エネルギー 4 枚。docs/stadium-reuse-special-energy-v0.58.md）
    "pool_v0_59",  # v0.59（マルマイン（第1弾）・カツラ・タケシの保護・カスミのメノクラゲ・わるいアーボック・まきちらせ!ベトベトガス。docs/energy-control-power-suppression-v0.59.md）
    "pool_v0_60",  # v0.60（サンダー（化石の秘密）・R団のストライク・カスミのギャラドス・タケシのサンドパン。docs/coins-defense-rebellion-v0.60.md）
    "pool_v0_61",  # v0.61（わるいギャラドス・わるいダグトリオ・タケシのオコリザル・バトル場は穴だらけ!。docs/reactive-powers-trainer-damage-v0.61.md）
    "pool_v0_62",  # v0.62（ピジョン・オニスズメ・オニドリル・ピジョット・タケシのダグトリオ・ベロリンガ（確定した修正を当てはめた写し）。docs/history-attacks-v0.62.md）
    "pool_v0_63",  # v0.63（ロケット団参上!・くすぐりマシーン・たたきつけろ!挑戦状・カツラのクイズ その3。docs/hidden-card-trainers-v0.63.md）
    "pool_v0_64",  # v0.64（化石の秘密のイシツブテ・ゴローン・ゴローニャ。docs/geodude-line-unbounded-coins-v0.64.md）
    "pool_v0_65",  # v0.65（キョウ秘伝,変わり身の術・カスミのドククラゲ・タケシのサイドン。docs/reactive-decisions-v0.65.md）
    "pool_v0_66",  # v0.66（お上品攻撃・ナツメのESP・カスミの勝負。docs/optional-trainers-v0.66.md）
    "pool_v0_67",  # v0.67（マチスの秘策。docs/secret-plan-preflight-v0.67.md）
    "pool_v0_68",  # v0.68（キョウのベトベトン・イマクニ？のドードー。ガルーラは pool_v0_34。docs/final-pmcg-cards-v0.68.md）
    "pool_v0_69",  # v0.69（拡張パック以外の商品の、登録したカードと処理に使う欄が同じ 96 枚。effects.EQUIVALENT_CARDS。docs/equivalent-non-pack-cards-v0.69.md）
    "pool_v0_70",  # v0.70（拡張パック以外の商品のポケモン 82 枚。どのワザも既存の効果の型と、ダメージのない小さな型 2 つ。PR1-069 は名前を訂正した写し。docs/non-pack-effect-reuse-v0.70.md）
    "pool_v0_71",  # v0.71（拡張パック以外の商品の再録で、元のカードと効果の文面だけが違う 78 枚。effects.REPRINT_CARDS。docs/reprint-text-variants-v0.71.md）
    "pool_v0_72",  # v0.72（拡張パック以外の商品のポケモン 43 枚。docs/status-coins-effect-reuse-v0.72.md）
    "pool_v0_73",  # v0.73（拡張パック以外の商品の、検索・回収・ドローのトレーナー 18 枚。docs/search-recovery-trainers-v0.73.md）
    "pool_v0_74",  # v0.74（拡張パック以外の商品のスタジアム 13 枚。docs/remaining-stadiums-v0.74.md）
    "pool_v0_75",  # v0.75（拡張パック以外の商品の、山札・トラッシュのカードを選ぶ・エネルギーをつけるポケモン 15 枚。docs/search-energy-pokemon-v0.75.md）
    "pool_v0_76",  # v0.76（拡張パック以外の商品の、持続する効果・ワザの使用の制限を中心とするポケモン 24 枚。docs/persistent-attack-modifiers-v0.76.md）
    "pool_v0_77",  # v0.77（neo 期の拡張パック（neo1〜neo4）の、既存の効果の型で表せるカード 52 枚。docs/neo-existing-effects-v0.77.md）
    "pool_v0_78",  # v0.78（悪・鋼エネルギー 5 枚と、「悪」「鋼」エネルギーを使うポケモン 8 枚。docs/darkness-metal-energy-v0.78.md）
    "pool_v0_79",  # v0.79（既存の効果の型と、それを組み合わせた 11 の組で表せるポケモン 52 枚。docs/shared-checks-pokemon-reuse-v0.79.md）
    "pool_v0_80",  # v0.80（トレーナー 30 枚。スタジアム 4 枚を含む。docs/neo-trainer-components-v0.80.md）
    "pool_v0_81",  # v0.81（ポケモンのどうぐ 11 枚・ピントレンズ・常にはたらくスタジアム 3 枚。docs/pokemon-tools-stadiums-v0.81.md）
    "pool_v0_82",  # v0.82（リサイクルエネルギー・エコロジムと、エネルギーカードをトラッシュするワザを持つポケモン 18 枚。docs/energy-discard-return-v0.82.md）
    "pool_v0_83",  # v0.83（ひかるポケモン 10 枚・やさしいポケモン 7 枚・ギャロップ ES1-014。docs/shining-gentle-pokemon-v0.83.md）
    "pool_v0_84",  # v0.84（やさしいポケモン 12 枚・ポケモン育て屋夫婦。docs/light-powers-evolution-v0.84.md）
    "pool_v0_85",  # v0.85（進化したときの特殊能力・エネルギーを動かすポケモン 13 枚とミラクルエネルギー。docs/entry-powers-energy-lifecycle-v0.85.md）
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

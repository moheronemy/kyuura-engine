"""効果の定義と、場のポケモンからはたらきうる効果を集める共通の処理（docs/event-model-v0.14.md 2 章・6 章）。

v0.13 では、自動的にはたらく・常にはたらく・決められたときに使う特殊能力を、境界の関数がそれぞれ実装の型で探していました
（``evasion_power``・``counterattack_power``・``ko_prevention_power``・``post_knockout_power``・``continuous._suppressor``。
docs/event-architecture-audit-v0.14.md 4.1）。ここでは、v0.13 の効果の登録表の実装の型・持続する効果の型から、効果の定義
（``EffectDefinition``）への対応表を 1 か所に持ち、窓ごとに「その窓ではたらきうる効果」を同じ関数で集めます。

- 特殊状態（ねむり・マヒ・こんらん）・かがくへんかガス（``continuous.suppressors_of``。v0.8 の部品をそのまま使う）・持続する効果の
  はたらく番は、定義の項目で宣言し、共通の関数（``working``・``blocked_by_status``・``suppressors``）で判定します。
- 効果の数値（はんげきの 10・こんじょうの残り HP 10 など）は、v0.13 の実装の値を読みます（ここに複製しない）。
- 宣言して使う特殊能力（エナジートランス・あまごい・ダメージスワップ）は、v0.13 の ``_use_pokemon_power`` がそのまま扱うので、
  この表にはありません（プロトタイプはそのコマンドを v0.13 のエンジンに渡す）。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from kyuura_engine import effects as E
from kyuura_engine.continuous import suppressors_of
from kyuura_engine.decisions import KO_PREVENTION, POST_KNOCKOUT_POWER
from kyuura_engine.state import PreventDamage, Retaliation

from .events import DamageClass, Window

if TYPE_CHECKING:
    from kyuura_engine.cards import Power
    from kyuura_engine.state import GameState, PokemonInPlay


class Origin(str, Enum):
    PRINTED_POWER = "printed_power"  # いちばん上のカードの特殊能力（p.310）
    PERSISTENT_EFFECT = "persistent_effect"  # ワザによる持続する効果（PokemonInPlay.persistent_effects）


class Mode(str, Enum):
    AUTOMATIC = "automatic"  # 決められたときに自動的にはたらく（宣言しない。p.323）
    OPTIONAL = "optional"  # 決められたときに使える（使うかはプレイヤーが決める。p.311）
    CONTINUOUS = "continuous"  # 常にはたらく（宣言しない。p.311・p.323）


class Timing(str, Enum):
    VOID = "void"  # ダメージの要素を無効にする（計算しない。p.321）
    REPLACE = "replace"  # 受ける前に、受けるかを決める（とうめい）
    DEFER = "defer"  # 受けたときに候補になり、ダメージの要素のあとの窓で処理する（p.89）
    OFFER = "offer"  # 決められた窓で、プレイヤーに決定で使うかを聞く
    QUERY = "query"  # 求められたときに今の状態から答える（かがくへんかガス）


BLOCKING_CONDITIONS = frozenset({"sleep", "paralysis", "confusion"})


@dataclass(frozen=True)
class EffectDefinition:
    """効果の定義（必要な項目だけ）。

    - ``windows``: 候補になる窓
    - ``disabled_by``: この特殊状態のときははたらかない・使えない（``status_time`` の時点の特殊状態で判定する）
    - ``status_time``: 特殊状態を判定する時点（``now``: 窓の時点、``on_damage``: ダメージを受けるとき（「すでに」）、
      ``on_knock_out``: きぜつするとき）
    - ``suppressible``: かがくへんかガスで消える（印刷された特殊能力。かがくへんかガス自身は名前で除かれる）
    - ``trigger_classes``・``by_opponent``: 受けたときの効果が候補になるダメージの分類と、相手のワザのダメージだけか
    - ``target``: 効果の対象（``damage_source``: ダメージを与えたポケモン、``self``、``receiving_element``: 受ける要素、
      ``discarded_card``: トラッシュのこのカード、``other_powers``: ほかの特殊能力）
    - ``action``: 処理（``kernel.ACTIONS`` の名前。効果の中身）
    - ``decision_kind``: 任意の効果の決定の種類（v0.13 と同じ）
    """

    name: str
    origin: Origin
    mode: Mode
    timing: Timing
    windows: frozenset[Window]
    disabled_by: frozenset[str]
    status_time: str
    suppressible: bool
    target: str
    action: str | None
    trigger_classes: frozenset[DamageClass] = frozenset()
    by_opponent: bool = False
    decision_kind: str | None = None


TRANSPARENCY = EffectDefinition(
    "transparency", Origin.PRINTED_POWER, Mode.AUTOMATIC, Timing.REPLACE, frozenset({Window.BEFORE_DAMAGE, Window.BEFORE_EFFECT}),
    BLOCKING_CONDITIONS, "now", True, "receiving_element", "evade_on_heads", frozenset({DamageClass.ATTACK}),
)
STRIKES_BACK = EffectDefinition(
    "strikes_back", Origin.PRINTED_POWER, Mode.AUTOMATIC, Timing.DEFER, frozenset({Window.DAMAGE_RECEIVING, Window.AFTER_DAMAGE_ELEMENTS}),
    BLOCKING_CONDITIONS, "on_damage", True, "damage_source", "power_damage_to_damage_source", frozenset({DamageClass.ATTACK}), True,
)
GUTS = EffectDefinition(
    "guts", Origin.PRINTED_POWER, Mode.OPTIONAL, Timing.OFFER, frozenset({Window.DAMAGE_RECEIVING, Window.KO_CHECK}),
    BLOCKING_CONDITIONS, "on_damage", True, "self", "coin_then_remaining_hp", frozenset({DamageClass.ATTACK}), True, KO_PREVENTION,
)
REBIRTH = EffectDefinition(
    "rebirth", Origin.PRINTED_POWER, Mode.OPTIONAL, Timing.OFFER, frozenset({Window.KO_PROCESS, Window.AFTER_JUDGE}),
    BLOCKING_CONDITIONS, "on_knock_out", True, "discarded_card", "return_card_to_hand", decision_kind=POST_KNOCKOUT_POWER,
)
CHEMICAL_GAS = EffectDefinition(
    "chemical_gas", Origin.PRINTED_POWER, Mode.CONTINUOUS, Timing.QUERY, frozenset(), BLOCKING_CONDITIONS, "now", False, "other_powers", None,
)
HARDEN = EffectDefinition(
    "harden", Origin.PERSISTENT_EFFECT, Mode.AUTOMATIC, Timing.VOID, frozenset({Window.BEFORE_DAMAGE}), frozenset(), "now", False,
    "receiving_element", "void_damage", frozenset({DamageClass.ATTACK}),
)
RETALIATION = EffectDefinition(
    "retaliation", Origin.PERSISTENT_EFFECT, Mode.AUTOMATIC, Timing.DEFER, frozenset({Window.DAMAGE_RECEIVING, Window.AFTER_DAMAGE_ELEMENTS}),
    frozenset(), "now", False, "damage_source", "attack_damage_to_damage_source", frozenset({DamageClass.ATTACK}), True,
)

# v0.13 の実装の型 → 効果の定義（型での振り分けはここだけ。部分型は親の型の定義を使う）
POWER_DEFINITIONS: tuple[tuple[type, EffectDefinition], ...] = (
    (E.AttackImmunityOnHeads, TRANSPARENCY),
    (E.CounterattackDamage, STRIKES_BACK),
    (E.PreventKnockOutOnHeads, GUTS),
    (E.ReturnToHandOnKnockOut, REBIRTH),
    (E.SuppressOtherPowers, CHEMICAL_GAS),
)
PERSISTENT_DEFINITIONS: tuple[tuple[type, EffectDefinition], ...] = (
    (PreventDamage, HARDEN),
    (Retaliation, RETALIATION),
)


@dataclass(frozen=True)
class EffectInstance:
    """場のポケモンが今持っている効果 1 つ（定義と持ち主・発生源）。状態から求め、状態に保存しない。"""

    definition: EffectDefinition
    owner: int
    pokemon_id: int
    card: int
    power_key: Any = None  # 印刷された特殊能力なら PowerKey
    power: Power | None = None  # 印刷された特殊能力のデータ（かがくへんかガスの判定に使う）
    implementation: Any = None  # v0.13 の実装（PowerEffect）か、持続する効果の値

    @property
    def name(self) -> str:
        return self.definition.name


def definition_for(implementation: Any, table: tuple[tuple[type, EffectDefinition], ...]) -> EffectDefinition | None:
    for cls in type(implementation).__mro__:
        for kind, definition in table:
            if cls is kind:
                return definition
    return None


def instances(state: GameState, owner: int, pokemon: PokemonInPlay, table=None) -> tuple[EffectInstance, ...]:
    """場のポケモン ``pokemon`` の効果（いちばん上のカードの特殊能力。p.310。と、受けている持続する効果）。"""
    powers = POWER_DEFINITIONS if table is None else table.powers
    persistent = PERSISTENT_DEFINITIONS if table is None else table.persistent
    definition = state.card_def(pokemon.card)
    found = []
    for index, power in enumerate(definition.powers):
        implementation = state.effects.power_effect(definition.id, power)
        if implementation is None:
            continue
        effect_definition = definition_for(implementation, powers)
        if effect_definition is not None:
            found.append(EffectInstance(effect_definition, owner, pokemon.pokemon_id, pokemon.card, E.PowerKey(definition.id, index), power, implementation))
    for effect in pokemon.persistent_effects:
        effect_definition = definition_for(effect, persistent)
        if effect_definition is not None:
            found.append(EffectInstance(effect_definition, owner, pokemon.pokemon_id, pokemon.card, implementation=effect))
    return tuple(found)


def in_window(state: GameState, window: Window, owner: int, pokemon: PokemonInPlay, table=None) -> tuple[EffectInstance, ...]:
    """``window`` で候補になりうる効果（特殊状態・ガス・はたらく番はまだ見ない）。"""
    return tuple(i for i in instances(state, owner, pokemon, table) if window in i.definition.windows)


def blocked_by_status(instance: EffectInstance, pokemon: PokemonInPlay) -> bool:
    """今の特殊状態で、はたらかない・使えないか（どくは関係しない。どの定義の ``disabled_by`` にもない）。"""
    return bool(set(pokemon.conditions.names()) & instance.definition.disabled_by)


def suppressors(state: GameState, instance: EffectInstance) -> tuple[int, ...]:
    """この効果を今消している、はたらいているかがくへんかガスのポケモン（v0.8 の部品。印刷された特殊能力だけ）。"""
    if instance.definition.origin is not Origin.PRINTED_POWER or not instance.definition.suppressible:
        return ()
    return suppressors_of(state, instance.power)


def active_now(state: GameState, instance: EffectInstance) -> bool:
    """持続する効果なら、はたらく番が今の番か（p.82・p.89・p.18「次の相手の番」）。印刷された特殊能力はいつも True。"""
    if instance.definition.origin is Origin.PERSISTENT_EFFECT:
        return instance.implementation.active_turn == state.turn_number
    return True


def working(state: GameState, instance: EffectInstance, pokemon: PokemonInPlay) -> bool:
    """今の時点ではたらいているか（特殊状態・ガス・はたらく番）。"""
    return not blocked_by_status(instance, pokemon) and active_now(state, instance) and not suppressors(state, instance)


@dataclass(frozen=True)
class Catalog:
    """対応表（試験用に定義を差しかえるため。既定は ``DEFAULT_CATALOG``）。"""

    powers: tuple[tuple[type, EffectDefinition], ...] = POWER_DEFINITIONS
    persistent: tuple[tuple[type, EffectDefinition], ...] = PERSISTENT_DEFINITIONS

    def with_power(self, kind: type, definition: EffectDefinition) -> Catalog:
        return Catalog(((kind, definition), *self.powers), self.persistent)


DEFAULT_CATALOG = Catalog()

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

from .. import effects as E
from ..continuous import goop_gas_effects, suppressors_of
from ..persistent import powers_use_prevented
from ..decisions import KO_PREVENTION, POST_KNOCKOUT_POWER
from ..state import AttackBarrier, PreventDamage, Retaliation

from .events import DamageClass, Window

if TYPE_CHECKING:
    from ..cards import Power
    from ..state import GameState, PokemonInPlay


class Origin(str, Enum):
    PRINTED_POWER = "printed_power"  # いちばん上のカードの特殊能力（p.310）
    PERSISTENT_EFFECT = "persistent_effect"  # ワザによる持続する効果（PokemonInPlay.persistent_effects）
    TRAINER_EFFECT = "trainer_effect"  # v0.56: トレーナーを使ったプレイヤーに与えた期限のある効果（GameState.trainer_effects。見えない壁）


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
    - ``requires``（v0.17b）: この特殊状態のときだけはたらく（R団のカビゴンの［わるいねぞう］はねむり。``status_time`` の時点で判定する）。
      ``disabled_by`` と同じ ``blocked_by_status`` で判定する（ねむり・マヒ・こんらんで消える力と同じ判定に、カードごとの分岐を加えない）
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
    requires: frozenset[str] = frozenset()
    # v0.42: 受けるポケモンがバトル場にいるときだけ候補になる（エリカのラフレシアの［ぼうぎょかふん］「このカードがバトル場でワザによるダメージを受けた時」）。
    # 既定（はんげき・わるいねぞう・返す効果）は場所を見ない（p.311・p.323）
    active_only: bool = False


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
# v0.17b: R団のカビゴンの［わるいねぞう］。はんげきと同じ窓・同じ処理（特殊能力のダメージをダメージを与えたポケモンに）で、特殊状態の条件だけが違う
# （ねむりのときだけはたらく。マヒ・こんらんはねむりと重ならないので、ねむりならマヒ・こんらんではない。どくは関係しない。p.245・p.322）
RESTLESS_SLEEP = EffectDefinition(
    "restless_sleep", Origin.PRINTED_POWER, Mode.AUTOMATIC, Timing.DEFER, frozenset({Window.DAMAGE_RECEIVING, Window.AFTER_DAMAGE_ELEMENTS}),
    frozenset(), "on_damage", True, "damage_source", "power_damage_to_damage_source", frozenset({DamageClass.ATTACK}), True,
    requires=frozenset({"sleep"}),
)
# v0.31: ミュウツーの「バリアー」（「次の相手の番の「ワザ」をうけない」）。「かたまる」と同じく要素を無効にする効果で、ダメージの要素だけでなく
# 効果の要素の前の窓（BEFORE_EFFECT）でも無効にする（ワザのダメージも効果も受けない）
BARRIER = EffectDefinition(
    "barrier", Origin.PERSISTENT_EFFECT, Mode.AUTOMATIC, Timing.VOID, frozenset({Window.BEFORE_DAMAGE, Window.BEFORE_EFFECT}), frozenset(), "now",
    False, "receiving_element", "void_attack", frozenset({DamageClass.ATTACK}),
)
# v0.42: エリカのラフレシアの［ぼうぎょかふん］。はんげきと同じ窓（受けたときに候補になり、ダメージの要素のあとの窓で処理する。CR-COUNTERATTACK-TIMING と同じ
# 時点）で、処理は「コインを投げ、「おもて」ならダメージを与えたポケモンをこんらん状態にする」（``kernel.power_confusion_to_damage_source``）。特殊状態の条件は
# ない（「ねむり・マヒ・こんらん」状態でも、必ずはたらく）。受けるときにバトル場にいること（``active_only``）。説明は「ワザによるダメージ」で「相手の」と書かない
# （``by_opponent`` は偽。今の対応カードでは、エリカのラフレシアが自分のワザのダメージを受けることはない）
DEFENSIVE_POLLEN = EffectDefinition(
    "defensive_pollen", Origin.PRINTED_POWER, Mode.AUTOMATIC, Timing.DEFER, frozenset({Window.DAMAGE_RECEIVING, Window.AFTER_DAMAGE_ELEMENTS}),
    frozenset(), "on_damage", True, "damage_source", "power_confusion_to_damage_source", frozenset({DamageClass.ATTACK}), False,
    active_only=True,
)
RETALIATION = EffectDefinition(
    "retaliation", Origin.PERSISTENT_EFFECT, Mode.AUTOMATIC, Timing.DEFER, frozenset({Window.DAMAGE_RECEIVING, Window.AFTER_DAMAGE_ELEMENTS}),
    frozenset(), "now", False, "damage_source", "attack_damage_to_damage_source", frozenset({DamageClass.ATTACK}), True,
)
# v0.56: 見えない壁（「次の相手の番が終わるまで、あなたの控えポケモンは、ワザによるダメージを受けない。(ダメージ以外の効果はそのまま)」）。使ったプレイヤーの、ダメージを
# 受ける時点の控えポケモンへのワザのダメージの要素を無効にする（「かたまる」と同じく計算しない。p.321）。効果の要素は無効にしない（BEFORE_EFFECT の窓に入れない）。
# 特殊能力ではないので、特殊状態・かがくへんかガスでは消えない（``disabled_by`` は空、``suppressible`` は偽）。はたらく期間は状態の記録（``state.TrainerTurnEffect``）で決める
INVISIBLE_WALL = EffectDefinition(
    "invisible_wall", Origin.TRAINER_EFFECT, Mode.AUTOMATIC, Timing.VOID, frozenset({Window.BEFORE_DAMAGE}), frozenset(), "now", False,
    "receiving_element", "void_damage", frozenset({DamageClass.ATTACK}),
)

# v0.13 の実装の型 → 効果の定義（型での振り分けはここだけ。部分型は親の型の定義を使う）
POWER_DEFINITIONS: tuple[tuple[type, EffectDefinition], ...] = (
    (E.AttackImmunityOnHeads, TRANSPARENCY),
    (E.CounterattackDamage, STRIKES_BACK),
    (E.CounterattackDamageWhileAsleep, RESTLESS_SLEEP),  # v0.17b（CounterattackDamage の部分型。型の並びの順は関係しない。definition_for）
    (E.PreventKnockOutOnHeads, GUTS),
    (E.ReturnToHandOnKnockOut, REBIRTH),
    (E.SuppressOtherPowers, CHEMICAL_GAS),
    (E.ConfuseDamageSourceOnHeads, DEFENSIVE_POLLEN),  # v0.42
)
PERSISTENT_DEFINITIONS: tuple[tuple[type, EffectDefinition], ...] = (
    (PreventDamage, HARDEN),
    (Retaliation, RETALIATION),
    (AttackBarrier, BARRIER),  # v0.31
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
    """場のポケモン ``pokemon`` の効果（今持つ特殊能力（いちばん上のカードの。p.310。v0.49 から ``effects.powers_of``。「ばける」でのせたカードの特殊能力を含む）と、
    受けている持続する効果）。"""
    powers = POWER_DEFINITIONS if table is None else table.powers
    persistent = PERSISTENT_DEFINITIONS if table is None else table.persistent
    found = []
    for slot in E.powers_of(state, pokemon):
        implementation = slot.effect
        if implementation is None:
            continue
        effect_definition = definition_for(implementation, powers)
        if effect_definition is not None:
            found.append(EffectInstance(effect_definition, owner, pokemon.pokemon_id, pokemon.card, slot.key, slot.power, implementation))
    for effect in pokemon.persistent_effects:
        effect_definition = definition_for(effect, persistent)
        if effect_definition is not None:
            found.append(EffectInstance(effect_definition, owner, pokemon.pokemon_id, pokemon.card, implementation=effect))
    # v0.56: プレイヤーに与えた期限のある効果のうち、このポケモンに今はたらくもの（見えない壁。持ち主が使ったもので、今そのポケモンが持ち主の控え）。場のポケモンに写さず、
    # 問い合わせの時点の場で決める（``effects.bench_damage_preventions``）
    for record in E.bench_damage_preventions(state, owner, pokemon):
        found.append(EffectInstance(INVISIBLE_WALL, owner, pokemon.pokemon_id, pokemon.card, implementation=record))
    return tuple(found)


def in_window(state: GameState, window: Window, owner: int, pokemon: PokemonInPlay, table=None) -> tuple[EffectInstance, ...]:
    """``window`` で候補になりうる効果（特殊状態・ガス・はたらく番はまだ見ない）。"""
    return tuple(i for i in instances(state, owner, pokemon, table) if window in i.definition.windows)


def blocked_by_status(instance: EffectInstance, pokemon: PokemonInPlay) -> bool:
    """今の特殊状態で、はたらかない・使えないか: ``disabled_by`` の特殊状態がある、または ``requires`` の特殊状態がない（v0.17b）。
    どくは、どの定義の ``disabled_by``・``requires`` にもない（関係しない）。"""
    names = set(pokemon.conditions.names())
    return bool(names & instance.definition.disabled_by) or not instance.definition.requires <= names


def suppressors(state: GameState, instance: EffectInstance) -> tuple[int, ...]:
    """この効果を今消している、はたらいているかがくへんかガスのポケモン（v0.8 の部品。印刷された特殊能力だけ）。"""
    if instance.definition.origin is not Origin.PRINTED_POWER or not instance.definition.suppressible:
        return ()
    return suppressors_of(state, instance.power)


def stopped(state: GameState, instance: EffectInstance) -> bool:
    """この効果（印刷された特殊能力）が今「使えず、その力も消え」ているか（v0.59）: かがくへんかガス（``suppressors``）か、まきちらせ!ベトベトガスの効果
    （``continuous.goop_gas_effects``）。印刷された特殊能力でない効果・消えない効果は False。"""
    if instance.definition.origin is not Origin.PRINTED_POWER or not instance.definition.suppressible:
        return False
    return bool(goop_gas_effects(state)) or bool(suppressors_of(state, instance.power))


def offer_stopped(state: GameState, instance: EffectInstance, pokemon: PokemonInPlay) -> bool:
    """宣言して使う任意の効果（こんじょう・ふしちょう。``Timing.OFFER``）を ``pokemon`` が今使えないか（v0.59）: ``stopped`` か、「ショックアイ」で特殊能力を使うことが
    できない（``persistent.powers_use_prevented``。宣言して使う特殊能力の使用だけを止める。CR-CHEMICAL-GAS-USE-VS-POWER）。"""
    return stopped(state, instance) or (instance.definition.origin is Origin.PRINTED_POWER and powers_use_prevented(state, pokemon) is not None)


def active_now(state: GameState, instance: EffectInstance) -> bool:
    """持続する効果なら、はたらく番が今の番か（p.82・p.89・p.18「次の相手の番」）。印刷された特殊能力はいつも True。"""
    if instance.definition.origin is Origin.PERSISTENT_EFFECT:
        return instance.implementation.active_turn == state.turn_number
    return True


def working(state: GameState, instance: EffectInstance, pokemon: PokemonInPlay) -> bool:
    """今の時点ではたらいているか（特殊状態・ガス・はたらく番）。"""
    return not blocked_by_status(instance, pokemon) and active_now(state, instance) and not stopped(state, instance)


@dataclass(frozen=True)
class Catalog:
    """対応表（試験用に定義を差しかえるため。既定は ``DEFAULT_CATALOG``）。"""

    powers: tuple[tuple[type, EffectDefinition], ...] = POWER_DEFINITIONS
    persistent: tuple[tuple[type, EffectDefinition], ...] = PERSISTENT_DEFINITIONS

    def with_power(self, kind: type, definition: EffectDefinition) -> Catalog:
        return Catalog(((kind, definition), *self.powers), self.persistent)


DEFAULT_CATALOG = Catalog()

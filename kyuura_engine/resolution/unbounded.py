"""「うら」が出るまでコインを投げ続ける効果の、先読みの有限の組（v0.64。docs/geodude-line-unbounded-coins-v0.64.md 3 章）。

実際の対戦では、コインを 1 枚ずつ「うら」が出るまで投げる（枚数・ダメージに上限はない。``coins.flip_until_tails``）。宣言の前の先読み
（``resolution.preflight``）は、コインのすべての結果を 1 つずつは試せない（「おもて」の数は上限がない）ので、「おもて」の数 h を有限の組
（``HeadClasses``）に分け、組ごとに 1 つの代表（その組でいちばん小さい h）だけを試す。代表の値は先読みの複製の上だけで使い、実際のダメージ・ログ・
ワザの履歴には使わない（実際の処理は実際のコインの数で計算する）。

組の分け方（``key``）: このワザの要素は ``Damage(OPP, HeadsUntilTails(per))`` だけで、h が後の処理に入るのは、基本となるダメージ b = per × h を
``kernel.deal_damage`` に渡すところだけ。そのあとの処理（「とうめい」・「かげぶんしん」・ダメージを受けたときの効果・こんじょう・［ずらかる］・
［ファイナルビーム］・きぜつ・サイド・同時のきぜつの問い）が b から受け取るのは、p.321 の計算の結果（最終ダメージ d と、順番の決定・色の読み方の
問いの形）と、受けたダメージで量が決まる返す効果（こうらがえし・クロスカウンター）の計算の結果だけ。``key(h)`` は、実際の処理と同じ関数
（``kernel.attack_modifiers_of``・``with_stadium_coin``・``compute_damage``・``calming_retaliation_differs``・``deferred_receivers``）で、
次を求める:

- 受けるポケモンの計算の木（順番の決定が要るなら段階と、選べる順番ごとの子。色の読み方で変わるなら ``readings``）。葉は
  (min(d, 受けるポケモンの残りの HP), 2 段階で終えたか, 返す効果ごとの計算の結果)。d が残りの HP 以上なら、どれもきぜつし、［ずらかる］の
  「ちょうど 10」も起こらないので、残りの HP にまとめる（まとめた値は組を分けるためだけに使う）
- 返す効果（ダメージを受けたときの送る効果のうち ``state.Retaliation``）ごとに、返すダメージの計算（「ワザをうけない」などで無効・CP1 で止まる・
  順番の決定（返す効果の枠では出せないので止まる）・色の読み方・(min(r, ワザを使ったポケモンの残りの HP), 2 段階で終えたか)）

同じ key の h は、先読みの範囲のどの結果（当たる問い・場の状態）も同じになる（受けたダメージの量そのものは、ログとワザの履歴にだけ残り、先読みの
範囲では読まれない）。

有限であることの根拠（3.2 節）: 計算の各段階の操作（``damage.DAMAGE_OPERATIONS``）は、どれも「入力が十分大きければ、一定か、入力について
減らない」。段階の数・変更効果の数は場で決まり有限なので、しきい値・加える数・抵抗力の和 T（ダメージの単位）、半分にする効果の数 m（P = 2^m）、
かける数の積 K から、b ≥ B（計算の道が 1 つなら P·T、2 つ以上（順番の決定・色の読み方・CP1 の 2 つの読み方）なら 3·K·P²·T）では、
どの道も一定か「P 枚ごとに同じ数だけ増える」形になり、増える道は飽和の値（残りの HP など。T に含める）以上、道どうしの等しい・等しくないは
P を周期とする。返す効果があれば、受けたダメージの飽和の値を、返す効果の計算の B を倍数で割った値まで上げ、周期を両方の P の積にする。
したがって h ≥ h_s = ⌈B / per⌉ では key(h) = key(h + P) で、h = 0 〜 h_s + P − 1 の key で、すべての h の key が尽くせる。

対応する計算（``SUPPORTED_OPERATIONS``）・前提（変更効果の数・しきい値・抵抗力・残りの HP がダメージカウンターの単位の倍数）を満たさない場は、
推測せずに止める（エンジンの未対応。問い ``unbounded_coin_preflight``・``UNSUPPORTED_UNBOUNDED_COIN_PREFLIGHT``。今の写しでは起こらない）。

v0.92（docs/power-suppression-lasting-locks-v0.92.md 9 章）: 基本となるダメージに固定の値を加えるワザ（ハッサムの「メタルニッパー」の ``30 + 10 × おもての数``。``HeadsUntilTails.fixed``）。
b(h) = fixed + per × h（``HeadsUntilTails.damage_for``）を、実際のダメージ・``key(h)``・境界のどれにも使う。根拠の前提（3.2 節）は b の値についての主張（b ≥ B で各道が一定か「P 枚
ごとに同じ数だけ増える」）で、固定の値はそのままでは崩さない: b(h + P) − b(h) = per × P は h によらず（周期はそのまま P）、b(h) ≥ B ⟺ h ≥ ⌈(B − fixed) / per⌉（0 より小さければ 0）。
加える前提は、固定の値が 0 以上でダメージカウンターの単位の倍数であること（半分にする効果の丸めの周期が b の単位の倍数で揃う。満たさなければ未対応として止める）。キーを
``per × h`` のまま作ると、組の代表の実際のダメージ（``fixed + per × h``）とずれる（同じ組の h で結果が変わりうる）ので、そうしない。
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..damage import (
    ADD,
    HALVE_DOWN,
    HALVE_UP,
    MULTIPLY,
    REDUCE_CHOICE,
    SET,
    SET_IF_AT_LEAST,
    ZERO_IF_AT_LEAST,
    ZERO_IF_BELOW,
    DamageOrderRequired,
    DamageReductionRequired,
    step_orders,
)
from ..effects import (
    OPPONENT_ACTIVE,
    AttackKey,
    TypeReadingsDiffer,
    attack_damage_modifiers,
    definition_views,
    max_hp,
    status_at_attack_powers,
)
from ..persistent import effect_attack_card
from ..state import RETALIATION_FIXED, Retaliation
from . import kernel as K
from .events import FRAME_DAMAGE_CLASS, FrameKind, Incoming

if TYPE_CHECKING:
    from .programs import AttackRun, Damage

SUPPORTED_OPERATIONS = frozenset({ADD, SET, MULTIPLY, ZERO_IF_BELOW, ZERO_IF_AT_LEAST, SET_IF_AT_LEAST, HALVE_UP, HALVE_DOWN})


class UnsupportedBoard(Exception):
    """有限の組の根拠の前提を満たさない場（エンジンの未対応）。"""


@dataclass(frozen=True)
class HeadClasses:
    """「おもて」の数の組（v0.64）。``representatives`` は組ごとのいちばん小さい「おもて」の数（小さい順）、``keys`` はその key。``bound`` は h_s、
    ``period`` は P。``key_of`` は任意の「おもて」の数の key（実際のコインの数がどの組かを決めるときに使う）。"""

    representatives: tuple[int, ...]
    keys: tuple
    bound: int
    period: int
    key_of: Callable[[int], Any] = field(compare=False, repr=False)

    def index_of_heads(self, heads: int) -> int:
        """実際に出た「おもて」の数がどの組か（代表の位置）。根拠の定理が成り立っていれば、どの数も代表のどれかと同じ key になる。"""
        key = self.key_of(heads)
        try:
            return self.keys.index(key)
        except ValueError:
            raise RuntimeError(f"「おもて」の数 {heads} の組が、先読みの有限の組（h_s {self.bound}・周期 {self.period}）にない（エンジンの不具合）") from None


@dataclass(frozen=True)
class _Frame:
    """返す効果の枠の、変更効果を集めるのに要る値だけ（``kernel.attack_modifiers_of``・``with_stadium_coin`` に渡す）。"""

    kind: FrameKind
    attack_key: AttackKey


def head_classes(run: AttackRun, element: Damage, per: int) -> HeadClasses:
    """ワザの要素 ``element``（``Damage(OPP, HeadsUntilTails(per, fixed))``）の「おもて」の数の組を、今の場から求める。状態を変えず、乱数を使わない。
    前提を満たさない場は ``res.question("unbounded_coin_preflight")``（エンジンの未対応）。v0.92: 基本となるダメージは要素の ``base.damage_for``（固定の値を含む）。"""
    try:
        key, bound, period = _key_and_bound(run, element, per)
    except UnsupportedBoard as reason:
        raise run.res.question("unbounded_coin_preflight", str(reason)) from None
    representatives: dict[Any, int] = {}
    for heads in range(bound + period):
        representatives.setdefault(key(heads), heads)
    return HeadClasses(tuple(representatives.values()), tuple(representatives), bound, period, key)


def _key_and_bound(run: AttackRun, element: Damage, per: int) -> tuple[Callable[[int], Any], int, int]:
    from .programs import OPP, HeadsUntilTails

    if not isinstance(element.base, HeadsUntilTails) or element.base.per != per:
        raise RuntimeError(f"「うら」が出るまで投げるコインの組の「おもて」1 枚あたりのダメージ {per} が、要素の基本となるダメージ {element.base!r} と合わない（エンジンの不具合）")
    fixed = element.base.fixed
    if (element.target != OPP or element.gate is not None or element.local_gate is not None or element.requires is not None or element.names is not None
            or not element.weakness_resistance or not element.resistance or not element.defender_effects):
        raise RuntimeError("「うら」が出るまで投げるコインのダメージの要素は、相手の対戦ポケモンへの、項目が既定のものだけ（エンジンの不具合）")
    res = run.res
    state = res.state
    unit = state.rules.damage_per_counter
    if per % unit or per <= 0:
        raise UnsupportedBoard(f"「おもて」1 枚あたりのダメージ {per} がダメージカウンターの単位の倍数ではない")
    if type(fixed) is not int or fixed < 0 or fixed % unit:
        raise UnsupportedBoard(f"基本となるダメージの固定の値 {fixed!r} が 0 以上のダメージカウンターの単位の倍数ではない")  # v0.92
    frame = run.fs.frame
    attacker = run.attacker()
    owner = 1 - run.player
    receiver = run.opponent_active()
    modifiers = K.with_stadium_coin(res, frame, OPPONENT_ACTIVE, K.attack_modifiers_of(res, frame, attacker, receiver, OPPONENT_ACTIVE))
    remaining = max_hp(state, receiver) - receiver.damage
    _require_unit(remaining, unit, "受けるポケモンの残りの HP")

    returns: list[Callable[[int], Any]] = []
    saturation = remaining
    periods = 1
    for instance in K.deferred_receivers(res, frame, owner, receiver):
        effect = instance.implementation
        if not isinstance(effect, Retaliation):
            continue  # はんげき・わるいねぞう・ぼうぎょかふん: 量は受けたダメージによらない（受けたかどうか（d > 0）だけで決まる）
        returned, needed, period = _retaliation(res, run, instance, effect, attacker, unit)
        returns.append(returned)
        saturation = max(saturation, needed)
        periods *= period

    receiver_views = definition_views(state, receiver)
    readings = len(definition_views(state, attacker)) * len(receiver_views)
    resistance = max((view.resistance_value or 0) for view in receiver_views)
    weakness = _weakness_multiplier(state, receiver_views)
    reducing = any(m.operation == REDUCE_CHOICE for m in modifiers)
    if reducing:
        # v0.66（docs/optional-trainers-v0.66.md 2.5 節）: お上品攻撃（5 段階で好きなだけ小さくしてよい）。減らしたあとの 5 段階のダメージ x の選び方は 0〜v（v は 5 段階の
        # 減らす前のダメージ）のすべてで、そのあとの計算（6〜8 段階・残りの HP・返す効果）は x だけで決まる。6〜8 段階の計算は、x が tail_bound 以上で一定か周期 tail_period
        # （ダメージカウンターの数）で同じになる（3.2 節の根拠を 6〜8 段階だけに当てはめる）ので、x を 0〜min(v, cap) に限っても、選べる結果の集まりは同じ。cap を飽和の値に
        # 加えて、1〜5 段階の道（v）が増えるなら v ≥ cap になる h の下限を求める（v が一定の道は key が一定）
        tail = [m for m in modifiers if m.step > 5]
        before = [m for m in modifiers if m.step <= 5 and m.operation != REDUCE_CHOICE]
        tail_period, tail_bound = _pipeline_bound([tail], 0, saturation, readings, 1, unit)
        cap = tail_bound + (tail_period + 1) * unit
        period, bound = _pipeline_bound([before], resistance, cap, readings, weakness, unit)
    else:
        period, bound = _pipeline_bound([modifiers], resistance, saturation, readings, weakness, unit)
        period *= periods

    def key(heads: int):
        base = element.base.damage_for(heads)  # v0.92: 実際のダメージと同じ式（固定の値を含む）

        def tree(orders: dict[int, tuple[int, ...]], reduction: int | None = None):
            try:
                calc = K.compute_damage(state, attacker, receiver, base, modifiers, orders=orders or None, reduction=reduction)
            except TypeReadingsDiffer:
                return ("readings",)
            except DamageOrderRequired as need:
                return ("order", need.step, tuple(tree({**orders, need.step: order}, reduction) for order in step_orders(len(need.modifiers))))
            except DamageReductionRequired as need:
                if need.below_zero:
                    return ("below_zero",)  # CA1（``deal_damage`` が止める）
                value = need.value
                # 減らしたあとのダメージ x（v から小さい順）を 0〜min(v, cap) に限る（それより大きい x の結果は、この範囲のどれかと同じ）
                kept = range(0, min(value, cap) + 1, unit) if value > 0 else (value,)
                return ("reduce", frozenset(tree(orders, value - x) for x in kept))
            final = calc.final
            # 受けるときの窓（送る効果）は最終ダメージが 0 より大きいときだけ（``deal_damage`` の ``receiving``）
            returned = tuple(g(final) for g in returns) if final > 0 else ()
            return ("final", min(final, remaining), calc.stopped_after_step_2, returned)

        return tree({})

    return key, max(0, -(-(bound - fixed) // per)), period  # v0.92: b(h) ≥ B になる最小の h（固定の値のぶん小さくなる）


def _retaliation(res, run: AttackRun, instance, effect: Retaliation, attacker, unit: int) -> tuple[Callable[[int], Any], int, int]:
    """返す効果 1 つの、返すダメージの計算の結果の関数と、受けたダメージの飽和に要る値（倍数で割った B）、周期（``kernel.attack_damage_to_damage_source``
    と同じ順番: 与える相手がすでに HP 以上 → 無効 → CP1 → 計算）。"""
    state = res.state
    holder = state.find_pokemon(instance.pokemon_id)[1]
    attacker_remaining = max_hp(state, attacker) - attacker.damage
    if attacker_remaining <= 0:
        return (lambda received: ("skipped",)), 0, 1
    key = AttackKey(effect_attack_card(state, effect), effect.attack_index)
    frame = _Frame(FrameKind.RETALIATION, key)
    # v0.103: 返す効果の枠（まだ開いていない）の発生元は返す側（効果を持つポケモンとその持ち主。ワザの分類）。実際の処理（``kernel.attack_damage_to_damage_source``）と同じ値で判定する
    incoming = Incoming(instance.owner, instance.pokemon_id, FRAME_DAMAGE_CLASS[FrameKind.RETALIATION], key)
    void = K.first_void(res, incoming, run.player, attacker) is not None
    modifiers = K.with_stadium_coin(res, frame, OPPONENT_ACTIVE, K.attack_modifiers_of(res, frame, holder, attacker, OPPONENT_ACTIVE))

    def returned(received: int):
        if void:
            return ("void",)
        base = effect.base_damage(received)
        if K.calming_retaliation_differs(state, key, holder, attacker, base, OPPONENT_ACTIVE, True, True):
            return ("cp1",)
        try:
            calc = K.compute_damage(state, holder, attacker, base, modifiers)
        except TypeReadingsDiffer:
            return ("readings",)
        except DamageOrderRequired:
            return ("order",)
        return ("final", min(calc.final, attacker_remaining), calc.stopped_after_step_2)

    if effect.basis == RETALIATION_FIXED or void:
        return returned, 0, 1  # 量が受けたダメージによらない
    _require_unit(attacker_remaining, unit, "ワザを使ったポケモンの残りの HP")
    lists = [modifiers]
    if status_at_attack_powers(state):
        # CP1 の比べで使う 2 つの読み方の変更効果（``calming_retaliation_differs``）
        every = frozenset(p.pokemon_id for player in state.players for p in player.in_play())
        lists += [list(attack_damage_modifiers(state, holder, attacker, attack=key, attack_status=snapshot)) for snapshot in (frozenset(), every)]
    attacker_views = definition_views(state, attacker)
    readings = len(definition_views(state, holder)) * len(attacker_views)
    resistance = max((view.resistance_value or 0) for view in attacker_views)
    period, bound = _pipeline_bound(lists, resistance, attacker_remaining, readings, _weakness_multiplier(state, attacker_views), unit)
    return returned, -(-bound // effect.multiplier), period


def _weakness_multiplier(state, views) -> int:
    """受けるポケモンの弱点の計算でかける数（v0.90。今有効な値の定義の ``weakness_multiplier``（のろいマーカーの「×4」）、なければ共通のルールの数）。実際の計算
    （``K.compute_damage``）と同じ定義から読み、key もこの数で計算した結果で分ける（上限だけを広げて済ませない）。"""
    return max(state.rules.weakness_multiplier if view.weakness_multiplier is None else view.weakness_multiplier for view in views)


def _require_unit(value: int, unit: int, what: str) -> None:
    if value % unit:
        raise UnsupportedBoard(f"{what} {value} がダメージカウンターの単位の倍数ではない")


def _pipeline_bound(lists: list[list], resistance: int, saturation: int, readings: int, weakness: int, unit: int) -> tuple[int, int]:
    """1 つのダメージの計算（変更効果の並び ``lists`` のどれか）の (周期 P（「おもて」の枚数）, B（ダメージの単位）)（docs 3.2 節）。"""
    halvings = 0
    multiplier = weakness
    total = resistance + saturation + unit
    multi = readings > 1 or len(lists) > 1
    for modifiers in lists:
        halvings = max(halvings, sum(1 for m in modifiers if m.operation in (HALVE_UP, HALVE_DOWN)))
        multiplier = max(multiplier, weakness * math.prod(m.amount for m in modifiers if m.operation == MULTIPLY))
        for m in modifiers:
            if m.operation not in SUPPORTED_OPERATIONS:
                raise UnsupportedBoard(f"変更効果 {m.label} の計算 {m.operation!r} は、有限の組の根拠が扱っていない")
            if m.operation not in (MULTIPLY, HALVE_UP, HALVE_DOWN) and m.amount % unit:
                raise UnsupportedBoard(f"変更効果 {m.label} の数 {m.amount} がダメージカウンターの単位の倍数ではない")
            if m.threshold is not None and m.threshold % unit:
                raise UnsupportedBoard(f"変更効果 {m.label} のしきい値 {m.threshold} がダメージカウンターの単位の倍数ではない")
            if m.operation in (HALVE_UP, HALVE_DOWN):
                total += 2 * unit
            elif m.operation != MULTIPLY:
                total += abs(m.amount) + (m.threshold or 0)
        for step in sorted({m.step for m in modifiers}):
            at_step = [m for m in modifiers if m.step == step]
            if len(at_step) > 1 and not all(m.operation == ADD for m in at_step):
                multi = True
    _require_unit(resistance, unit, "抵抗力の数")
    period = 2 ** halvings
    bound = 3 * multiplier * period * period * total if multi else period * total
    return period, bound

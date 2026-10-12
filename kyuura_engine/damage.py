"""ワザによるダメージの計算（『オフィシャルブック2000』p.321「ワザによるダメージ計算の順番」）。

公式ルールの 8 段階のうち、v0.1 の対応カードで値が変わりうるのは 1・3・4 段階だけです。
2・5・6・7・8 段階にかかわる効果（ストライクの「つるぎのまい」、プラスパワー、スタジアム、
ディフェンダー、イワークの「かたくなる」など）を持つカードは、デッキに入れられないように
しているので、ここでは段階の位置だけを示して何もしません。それらの効果を加えるときは、
この関数に段階ごとの処理を加えます（同じ段階に複数の効果があるときの順番は、ワザを使う・
受けるプレイヤーが決める。p.321）。
"""

from __future__ import annotations

from dataclasses import dataclass

from .cards import CardDefinition
from .rules import RuleSet


@dataclass(frozen=True)
class DamageCalculation:
    base: int
    weakness_applied: bool
    resistance_applied: bool
    stopped_after_step_2: bool
    final: int  # 相手に与えるダメージ。0 なら「ダメージを与えなかった」
    steps: tuple[tuple[str, int], ...]


def calculate_attack_damage(base: int, attacker: CardDefinition, defender: CardDefinition, rules: RuleSet) -> DamageCalculation:
    """バトル場のポケモンがワザで相手のバトル場のポケモンに与えるダメージ。"""
    steps: list[tuple[str, int]] = []

    # 1. 基本となるダメージ（ワザの説明にしたがって計算する。v0.1 のワザは説明がなく、ダメージの目安の数字そのもの）
    amount = base
    steps.append(("1 基本となる計算", amount))

    # 2. ワザを使うポケモンの持っている「ダメージを変更する効果」（v0.1 の対応カードにはない）
    # ここまでで 0 以下なら計算を終え、「ダメージを与えなかった」ことになる
    if amount <= 0:
        return DamageCalculation(base, False, False, True, 0, tuple(steps))

    # 3. ワザを使うポケモンのタイプが、ワザを受けるポケモンの「弱点」のタイプなら 2 倍（p.315, p.321）
    weakness_applied = defender.weakness is not None and attacker.pokemon_type == defender.weakness
    if weakness_applied:
        amount *= rules.weakness_multiplier
        steps.append(("3 弱点", amount))

    # 4. ワザを使うポケモンのタイプが「抵抗力」のタイプなら、抵抗力の数字をマイナス（p.315, p.321）
    # 計算の途中で 0 やマイナスになってもよい（p.319）
    resistance_applied = defender.resistance is not None and attacker.pokemon_type == defender.resistance
    if resistance_applied:
        amount -= defender.resistance_value
        steps.append(("4 抵抗力", amount))

    # 5〜8. ワザを使う・受けるポケモンについているカード、場の効果、受けるポケモンの効果（v0.1 の対応カードにはない）

    # 最終的に 0 以下なら「ダメージを与えなかった」（p.319, p.321）
    final = amount if amount > 0 else 0
    return DamageCalculation(base, weakness_applied, resistance_applied, False, final, tuple(steps))

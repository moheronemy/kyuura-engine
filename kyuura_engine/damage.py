"""ワザによるダメージの計算（『オフィシャルブック2000』p.321「ワザによるダメージ計算の順番」）。

公式ルールの 8 段階:

1. 基本となるダメージ（ワザの説明にしたがう）
2. ワザを使うポケモンの持っている「ダメージを変更する効果」（「つるぎのまい」など、持続する状態の効果）
   ここまでで 0 やマイナスなら計算を終え、「ダメージを与えなかった」
3. 弱点（2 倍）
4. 抵抗力（抵抗力の数字をマイナス）
5. ワザを使うポケモンについている「トレーナーカード」や「エネルギーカード」による効果（プラスパワーなど）
6. それ以外の「ダメージを変更する効果」（スタジアムなど）
7. ワザを受けるポケモンについている「トレーナーカード」や「エネルギーカード」による効果（ディフェンダーなど）
8. ワザを受けるポケモンの持っている「ダメージを変更する効果」（「かたくなる」など）

計算の途中で 0 やマイナスになってもよく（p.321「ダメージを計算している途中で、その数が0やマイナスの
数字になってもかまいません」）、最後に 0 以下なら「ダメージを与えなかった」。

v0.2c で、2・5〜8 段階のダメージの変更を ``DamageModifier`` で渡せるようにした。今の対応カードで
値を持つのは 5 段階のプラスパワーだけ。変更効果はカードの実装（``effects``）が作り、ここには
段階と数値だけが来る（プラスパワーをここに直接書かない）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .cards import CardDefinition
from .rules import RuleSet

# 同じ段階に複数の変更効果があるときに、計算の順番を決めるプレイヤー（p.321）。
# v0.2c の変更効果は加算だけで、加算どうしは順番で結果が変わらないので、選ぶ決定はまだない。
# 加算でない変更効果（「0 にする」「30 以上なら受けない」など）を加えるときは、同じ段階に 2 つ以上
# あれば、このプレイヤーが順番を選ぶ決定（保留中の決定）を出す。
DAMAGE_STEP_CHOOSER = {2: "attacker", 5: "attacker", 6: "attacker", 7: "defender", 8: "defender"}


@dataclass(frozen=True)
class DamageModifier:
    """ダメージ計算の段階（2・5・6・7・8）に加える数（v0.2c）。

    - ``step``: 段階（p.321）
    - ``amount``: 加える数（マイナスなら減らす）。加算だけを表す
    - ``label``: 段階の記録に出す名前（カード名など）
    - ``source``: 発生源のカードの uid（なければ None）
    """

    step: int
    amount: int
    label: str
    source: int | None = None

    def __post_init__(self) -> None:
        if self.step not in DAMAGE_STEP_CHOOSER:
            raise ValueError(f"ダメージを変更する効果の段階は 2・5・6・7・8（{self.step!r}）")


@dataclass(frozen=True)
class DamageCalculation:
    base: int
    weakness_applied: bool
    resistance_applied: bool
    stopped_after_step_2: bool
    final: int  # 相手に与えるダメージ。0 なら「ダメージを与えなかった」
    steps: tuple[tuple[str, int], ...]
    modifiers: tuple[DamageModifier, ...] = ()  # 計算に使った変更効果（v0.2c）


def calculate_attack_damage(
    base: int,
    attacker: CardDefinition,
    defender: CardDefinition,
    rules: RuleSet,
    modifiers: Sequence[DamageModifier] = (),
) -> DamageCalculation:
    """バトル場のポケモンがワザで相手のバトル場のポケモンに与えるダメージ。

    ``modifiers`` は 2・5〜8 段階の変更効果（v0.2c）。渡さなければ v0.1 と同じ計算・同じ記録になる。
    """
    steps: list[tuple[str, int]] = []
    used = tuple(modifiers)

    def apply(step: int, amount: int) -> int:
        for modifier in used:
            if modifier.step == step:
                amount += modifier.amount
                steps.append((f"{step} {modifier.label}", amount))
        return amount

    # 1. 基本となるダメージ（ワザの説明にしたがって計算する。説明のないワザは、ダメージの目安の数字そのもの）
    amount = base
    steps.append(("1 基本となる計算", amount))

    # 2. ワザを使うポケモンの持っている「ダメージを変更する効果」
    # ここまでで 0 以下なら計算を終え、「ダメージを与えなかった」ことになる
    amount = apply(2, amount)
    if amount <= 0:
        return DamageCalculation(base, False, False, True, 0, tuple(steps), used)

    # 3. ワザを使うポケモンのタイプが、ワザを受けるポケモンの「弱点」のタイプなら 2 倍（p.315, p.321）
    weakness_applied = defender.weakness is not None and attacker.pokemon_type == defender.weakness
    if weakness_applied:
        amount *= rules.weakness_multiplier
        steps.append(("3 弱点", amount))

    # 4. ワザを使うポケモンのタイプが「抵抗力」のタイプなら、抵抗力の数字をマイナス（p.315, p.321）
    # 計算の途中で 0 やマイナスになってもよい（p.319, p.321）
    resistance_applied = defender.resistance is not None and attacker.pokemon_type == defender.resistance
    if resistance_applied:
        amount -= defender.resistance_value
        steps.append(("4 抵抗力", amount))

    # 5. ワザを使うポケモンについているカードの効果（プラスパワーなど）
    # 6. それ以外の効果、7. ワザを受けるポケモンについているカードの効果、8. ワザを受けるポケモンの効果
    for step in (5, 6, 7, 8):
        amount = apply(step, amount)

    # 最終的に 0 以下なら「ダメージを与えなかった」（p.319, p.321）
    final = amount if amount > 0 else 0
    return DamageCalculation(base, weakness_applied, resistance_applied, False, final, tuple(steps), used)

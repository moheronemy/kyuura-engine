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

v0.2c で、2・5〜8 段階のダメージの変更を ``DamageModifier`` で渡せるようにした（5 段階のプラスパワー、v0.2e で 7 段階の
ディフェンダー）。変更効果はカードの実装（``effects``）が作り、ここには段階と数値だけが来る（プラスパワーをここに直接書かない）。
v0.27 で、2 段階の「その数にする」効果（``SET``。ストライクの「つるぎのまい」の「「きりさく」のダメージは「60」になる」。p.321 の 2 段階の
例そのもの）を加えた。加算でない効果なので、同じ段階にほかの変更効果があれば計算の順番で結果が変わる（p.321 は順番をワザを使う
プレイヤーが決めるとする）。今の対応カードでは 2 段階の変更効果は「つるぎのまい」だけで、同じ番に 2 つはたらくこともないので起こらない。
起こったら、順番を決めずに ``RuntimeError`` で止める（順番を選ぶ決定は未実装）。

1 段階の「基本となるダメージ」は、ワザの実装が説明にしたがって計算して ``base`` に渡す（v0.2d の
「みだれづき」は「おもて」の数 × 10。0 もある）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .cards import CardDefinition
from .rules import RuleSet

# 同じ段階に複数の変更効果があるときに、計算の順番を決めるプレイヤー（p.321）。
# v0.2c の変更効果は加算だけで、加算どうしは順番で結果が変わらないので、選ぶ決定はまだない。
# 加算でない変更効果（「0 にする」「30 以上なら受けない」など）を加えるときは、同じ段階に 2 つ以上
# あれば、このプレイヤーが順番を選ぶ決定（保留中の決定）を出す。v0.27 の「その数にする」効果（SET）は、
# 同じ段階にほかの変更効果があると、その決定がないので RuntimeError で止める（今の対応カードでは起こらない）。
DAMAGE_STEP_CHOOSER = {2: "attacker", 5: "attacker", 6: "attacker", 7: "defender", 8: "defender"}

ADD = "add"  # 数を加える（プラスパワー・ディフェンダー。v0.2c）
SET = "set"  # その数にする（v0.27。「つるぎのまい」の「「60」になる」）
DAMAGE_OPERATIONS = (ADD, SET)


@dataclass(frozen=True)
class DamageModifier:
    """ダメージ計算の段階（2・5・6・7・8）のダメージの変更（v0.2c）。

    - ``step``: 段階（p.321）
    - ``amount``: ``operation`` が ``ADD`` なら加える数（マイナスなら減らす）、``SET`` ならその段階でダメージをこの数にする（v0.27）
    - ``label``: 段階の記録に出す名前（カード名・ワザ名など）
    - ``source``: 発生源のカードの uid（なければ None）
    - ``operation``（v0.27）: ``ADD``（既定。v0.26 までの変更効果はすべてこれ）か ``SET``
    """

    step: int
    amount: int
    label: str
    source: int | None = None
    operation: str = ADD

    def __post_init__(self) -> None:
        if self.step not in DAMAGE_STEP_CHOOSER:
            raise ValueError(f"ダメージを変更する効果の段階は 2・5・6・7・8（{self.step!r}）")
        if self.operation not in DAMAGE_OPERATIONS:
            raise ValueError(f"ダメージを変更する効果の計算は {DAMAGE_OPERATIONS} のどれか（{self.operation!r}）")


@dataclass(frozen=True)
class DamageCalculation:
    base: int
    weakness_applied: bool
    resistance_applied: bool
    stopped_after_step_2: bool
    final: int  # 相手に与えるダメージ。0 なら「ダメージを与えなかった」
    steps: tuple[tuple[str, int], ...]
    modifiers: tuple[DamageModifier, ...] = ()  # 計算に使った変更効果（v0.2c）。2 段階で終えたら 2 段階のものだけ（v0.2d）


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
    for step in DAMAGE_STEP_CHOOSER:
        at_step = [m for m in used if m.step == step]
        if len(at_step) > 1 and any(m.operation != ADD for m in at_step):
            # 加算でない効果は、同じ段階のほかの効果との順番で結果が変わる。p.321 は順番を DAMAGE_STEP_CHOOSER のプレイヤーが決めるとするが、
            # その決定はまだない（今の対応カードでは起こらない。v0.27）。順番を決めて計算しない
            raise RuntimeError(
                f"{step} 段階に加算でない変更効果を含む {len(at_step)} つの効果が重なった（{[m.label for m in at_step]}）。計算の順番を"
                f"{DAMAGE_STEP_CHOOSER[step]}（ワザを使うプレイヤー・受けるプレイヤー）が決める決定は未実装（p.321。docs/scyther-v0.27.md）"
            )

    def apply(step: int, amount: int) -> int:
        for modifier in used:
            if modifier.step == step:
                amount = modifier.amount if modifier.operation == SET else amount + modifier.amount
                steps.append((f"{step} {modifier.label}", amount))
        return amount

    # 1. 基本となるダメージ（ワザの説明にしたがって計算する。説明のないワザは、ダメージの目安の数字そのもの）
    amount = base
    steps.append(("1 基本となる計算", amount))

    # 2. ワザを使うポケモンの持っている「ダメージを変更する効果」
    # ここまでで 0 以下なら計算を終え、「ダメージを与えなかった」ことになる
    amount = apply(2, amount)
    if amount <= 0:
        # 3 段階から先は計算しないので、5〜8 段階の変更効果（プラスパワーなど）は使っていない（v0.2d。
        # 「おもて」の数×のワザで「おもて」が 0 枚のときなど。p.257 の解説「ワザのダメージが与えられなかったら、
        # 「プラスパワー」の効果はなくなります」）
        applied = tuple(m for m in used if m.step == 2)
        return DamageCalculation(base, False, False, True, 0, tuple(steps), applied)

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


def calculate_confusion_damage(pokemon: CardDefinition, rules: RuleSet, base: int) -> DamageCalculation:
    """こんらん状態のポケモンのワザがこんらんしたとき（コインが「うら」）、ワザを使ったポケモン自身が受けるダメージ（v0.3c）。

    - 基本は 20（p.309 の手順 5「もとのワザの内容に関わらず、ワザを使ったポケモン自身が20ダメージを受けます」）。
    - 「このダメージは「弱点・抵抗力」の影響を受けます」（p.322。CONFIRMED）。ダメージを与えるのも受けるのも同じポケモン
      なので、そのポケモンのタイプが自分の弱点のタイプなら 2 倍、抵抗力のタイプなら抵抗力の数字をマイナスする（p.321 の
      3・4 段階の定義をそのまま当てはめる。SUPPORTED）。0 以下なら 0（「ダメージを受けなかった」。p.321）。
    - これは ``calculate_attack_damage``（「ワザによるダメージ」の 8 段階。p.321「8」「9」）とは別の計算にしている。こんらんの
      ダメージが「ワザによるダメージ」かは原典に書かれていないので、プラスパワー（5 段階）・ディフェンダー（7 段階）などを
      計算するかは決められない（UNRESOLVED）。ワザを使うポケモンにそれらがついているときは、エンジンがコインを投げる前に
      止める（``engine._confusion_damage_problem``）ので、ここには変更効果が来ない。
    """
    steps: list[tuple[str, int]] = [("こんらん", base)]
    amount = base
    weakness_applied = pokemon.weakness is not None and pokemon.pokemon_type == pokemon.weakness
    if weakness_applied:
        amount *= rules.weakness_multiplier
        steps.append(("弱点", amount))
    resistance_applied = pokemon.resistance is not None and pokemon.pokemon_type == pokemon.resistance
    if resistance_applied:
        amount -= pokemon.resistance_value
        steps.append(("抵抗力", amount))
    final = amount if amount > 0 else 0
    return DamageCalculation(base, weakness_applied, resistance_applied, False, final, tuple(steps))

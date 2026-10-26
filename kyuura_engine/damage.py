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

v0.35 で、2 段階の「数をかける」効果（``MULTIPLY``。マチスのコラッタ・ラッタの「きあいだめ」の「…のダメージは2倍になる」）を加え、同じ段階の
順番を選ぶ決定に対応した（docs/coin-groups-damage-order-v0.35.md 3 章）。同じ段階に加算でない効果を含む 2 つ以上の効果があり、順番によって
計算の結果（最終ダメージと、2 段階で計算を終えるか）が変わるときは、``orders`` にその段階の順番がなければ ``DamageOrderRequired`` を投げる
（呼ぶ側が、``DAMAGE_STEP_CHOOSER`` のプレイヤーに決定で選ばせて、選んだ順番を ``orders`` に渡してもう一度計算する）。順番によって結果が
変わらないとき（効果が 1 つ・加算だけ・どの順番でも同じ結果）は決定を出さず、集めた順番で計算する（順番で結果が変わる場面を、コードの
決めた順番で計算しない）。

1 段階の「基本となるダメージ」は、ワザの実装が説明にしたがって計算して ``base`` に渡す（v0.2d の
「みだれづき」は「おもて」の数 × 10。0 もある）。
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Mapping, Sequence

from .cards import CardDefinition, EnergyType
from .rules import RuleSet

# 同じ段階に複数の変更効果があるときに、計算の順番を決めるプレイヤー（p.321）。
# v0.2c の変更効果は加算だけで、加算どうしは順番で結果が変わらないので、選ぶ決定はまだない。
# 加算でない変更効果（「0 にする」「30 以上なら受けない」など）を加えるときは、同じ段階に 2 つ以上
# あれば、このプレイヤーが順番を選ぶ決定（保留中の決定）を出す。v0.27 の「その数にする」効果（SET）は、
# 同じ段階にほかの変更効果があると、その決定がないので RuntimeError で止めていた。v0.35 から、順番によって結果が変わるときは
# ``DamageOrderRequired`` を投げ、呼ぶ側がこのプレイヤーに決定で選ばせる（2・5・6 段階はワザを使うプレイヤー、7・8 段階はワザを受ける
# プレイヤー。p.321。docs/scyther-v0.27.md の SC15・docs/architecture-v0.2c.md）。
DAMAGE_STEP_CHOOSER = {2: "attacker", 5: "attacker", 6: "attacker", 7: "defender", 8: "defender"}

ADD = "add"  # 数を加える（プラスパワー・ディフェンダー。v0.2c）
SET = "set"  # その数にする（v0.27。「つるぎのまい」の「「60」になる」）
MULTIPLY = "multiply"  # その数をかける（v0.35。「きあいだめ」の「…のダメージは2倍になる」）
# v0.45: その段階のダメージがこの数より小さければ 0 にし、この数以上ならそのまま（イワークの「かたくなる」の「受けるダメージが0になる。ただしダメージが40以上の
# 場合は、そのままダメージをうける。」。p.321 の 8 段階の例）
ZERO_IF_BELOW = "zero_if_below"
# v0.46: 常にはたらく特殊能力・ワザの持続する効果の計算（docs/continuous-powers-v0.46.md 3 章）。どれも、その段階のダメージだけを見て決まる計算で、計算の順番が
# 結果を変えるときは、ほかの加算でない効果と同じく ``DamageOrderRequired``（順番の決定）になる
# - ``ZERO_IF_AT_LEAST``: その段階のダメージが ``amount`` 以上なら 0 にし、``amount`` より小さければそのまま（バリヤードの［なぞのかべ］の「このカードが受ける30以上の
#   ダメージは0になる。(30より小さいダメージはそのまま受ける。)」。p.321 の 8 段階の例。``ZERO_IF_BELOW`` と比べる向きが逆）
# - ``SET_IF_AT_LEAST``: その段階のダメージが ``threshold`` 以上なら ``amount`` にし、小さければそのまま（エリカのミニリュウの［ふしぎなバリアー］の「20以上のダメージは、
#   「10」になる」）
# - ``HALVE_UP``・``HALVE_DOWN``: その段階のダメージを半分にし、ダメージカウンター 1 個（``unit``。p.319 の 10）の単位で切り上げる・切りすてる（エリカのフシギソウの
#   ［くつろぐかおり］の「半分(切り上げ)」・エリカのタマタマの「リフレクター」の「半分(切りすて)」。単位は v0.4d のメガドレイン・v0.45 の「いかりのまえば」の
#   「半分（切り上げ）」と同じ）。0 以下のダメージは変えない（2 段階なら計算を終え、6・8 段階のあとにダメージを増やす段階はないので、最終ダメージはどちらでも 0）
ZERO_IF_AT_LEAST = "zero_if_at_least"
SET_IF_AT_LEAST = "set_if_at_least"
HALVE_UP = "halve_up"
HALVE_DOWN = "halve_down"
DAMAGE_OPERATIONS = (ADD, SET, MULTIPLY, ZERO_IF_BELOW, ZERO_IF_AT_LEAST, SET_IF_AT_LEAST, HALVE_UP, HALVE_DOWN)
# v0.66（docs/optional-trainers-v0.66.md 2 章）: 5 段階の「のぞむなら、そのダメージを好きなだけ小さくしてよい」（お上品攻撃。ワザを使うポケモンについているトレーナーカードの
# 効果）。減らす量はワザを使うプレイヤーが決定で選ぶ（``DamageReductionRequired``・``reduction``）。``amount`` は使わない（0）。``DAMAGE_OPERATIONS`` には入れない
# （ほかの計算と同じ並べかえの対象にしない。同じ 5 段階のほかの効果のあとに当てはめる）
REDUCE_CHOICE = "reduce_choice"


@dataclass(frozen=True)
class DamageModifier:
    """ダメージ計算の段階（2・5・6・7・8）のダメージの変更（v0.2c）。

    - ``step``: 段階（p.321）
    - ``amount``: ``operation`` が ``ADD`` なら加える数（マイナスなら減らす）、``SET`` ならその段階でダメージをこの数にする（v0.27）、``MULTIPLY`` なら
      その段階でダメージにこの数をかける（v0.35。2 以上の整数）
    - ``label``: 段階の記録に出す名前（カード名・ワザ名など）
    - ``source``: 発生源のカードの uid（なければ None）
    - ``operation``（v0.27）: ``ADD``（既定。v0.26 までの変更効果はすべてこれ）か ``SET``（v0.27）か ``MULTIPLY``（v0.35）か ``ZERO_IF_BELOW``（v0.45。
      ``amount`` はしきい値。その段階のダメージが ``amount`` より小さければ 0、``amount`` 以上ならそのまま）。v0.46: ``ZERO_IF_AT_LEAST``（``amount`` はしきい値）・
      ``SET_IF_AT_LEAST``（``threshold`` 以上なら ``amount`` にする）・``HALVE_UP``・``HALVE_DOWN``（``amount`` は 2。割る数）
    - ``threshold``（v0.46）: ``SET_IF_AT_LEAST`` のしきい値（ほかの計算では None）
    - ``attacker_type``（v0.97）: ダメージを与えるポケモンの今有効なタイプがこのタイプのときだけ当てはめる（アンノーンD の［DARK df］の「「悪」ポケモンからダメージを受けるとき」）。
      色の読み方（VS1 など）ごとの計算（``calculate_attack_damage`` の ``attacker``）で決める。None ならタイプによらない（v0.96 までの変更効果はすべてこれ）
    """

    step: int
    amount: int
    label: str
    source: int | None = None
    operation: str = ADD
    threshold: int | None = None
    attacker_type: EnergyType | None = None

    def __post_init__(self) -> None:
        if self.step not in DAMAGE_STEP_CHOOSER:
            raise ValueError(f"ダメージを変更する効果の段階は 2・5・6・7・8（{self.step!r}）")
        if self.operation not in DAMAGE_OPERATIONS and self.operation != REDUCE_CHOICE:
            raise ValueError(f"ダメージを変更する効果の計算は {DAMAGE_OPERATIONS} のどれか（{self.operation!r}）")
        if self.operation == MULTIPLY and (type(self.amount) is not int or self.amount < 2):
            raise ValueError(f"ダメージにかける数は 2 以上の整数（{self.amount!r}）")
        if self.operation in (ZERO_IF_BELOW, ZERO_IF_AT_LEAST) and (type(self.amount) is not int or self.amount < 1):
            raise ValueError(f"ダメージを 0 にするしきい値は 1 以上の整数（{self.amount!r}）")
        if self.operation == SET_IF_AT_LEAST:
            if type(self.threshold) is not int or self.threshold < 1 or type(self.amount) is not int or self.amount < 0:
                raise ValueError(f"しきい値以上のダメージをその数にする効果のしきい値・数が正しくない（{self.threshold!r}・{self.amount!r}）")
        elif self.threshold is not None:
            raise ValueError(f"しきい値（threshold）は、しきい値以上のダメージをその数にする効果だけに書く（{self.operation!r}）")
        if self.operation in (HALVE_UP, HALVE_DOWN) and self.amount != 2:
            raise ValueError(f"半分にする効果の割る数は 2（{self.amount!r}）")
        if self.operation == REDUCE_CHOICE and (self.step != 5 or self.amount != 0):
            raise ValueError(f"好きなだけ小さくする効果は 5 段階・数 0（{self.step!r}・{self.amount!r}）")

    def apply(self, amount: int, unit: int = 10) -> int:
        """この効果を、その段階のダメージ ``amount`` に当てはめた数（v0.35）。v0.46: ``unit`` はダメージカウンター 1 個のダメージ（半分にするときの端数の単位。
        p.319。``RuleSet.damage_per_counter``）。"""
        if self.operation == SET:
            return self.amount
        if self.operation == MULTIPLY:
            return amount * self.amount
        if self.operation == ZERO_IF_BELOW:
            return 0 if amount < self.amount else amount
        if self.operation == ZERO_IF_AT_LEAST:
            return 0 if amount >= self.amount else amount
        if self.operation == SET_IF_AT_LEAST:
            return self.amount if amount >= self.threshold else amount
        if self.operation == REDUCE_CHOICE:
            raise RuntimeError("好きなだけ小さくする効果は、選んだ量で計算する（``_calculate`` の ``reduction``。エンジンの不具合）")
        if self.operation in (HALVE_UP, HALVE_DOWN):
            if amount <= 0:
                return amount
            counters = amount // unit
            if counters * unit != amount:
                raise ValueError(f"ダメージ {amount} がダメージカウンターの単位 {unit} の倍数ではない（半分にできない）")
            return ((counters + 1) // 2 if self.operation == HALVE_UP else counters // 2) * unit
        return amount + self.amount


class DamageOrderRequired(RuntimeError):
    """同じ段階の変更効果の計算の順番によって結果が変わり、その順番が渡されていない（v0.35）。

    - ``step``: 段階（p.321）
    - ``modifiers``: その段階の変更効果（集めた順番。順番の決定の選べるものは、この並びの番号の並べかえ）
    - ``chooser``: 順番を選ぶプレイヤー（``DAMAGE_STEP_CHOOSER``。``"attacker"``・``"defender"``）

    呼ぶ側（解決の基盤のダメージの要素）が決定を出し、選んだ順番を ``orders`` に渡してもう一度計算する。決定を出せない呼ぶ側は、エンジンの
    未対応として止める（``UNSUPPORTED_DAMAGE_STEP_ORDER``）。``RuntimeError`` の部分型なのは、決定を出せない古い計算（v0.13 の止める関数の
    ``preview_attack_damage``）でこの場合に来たら、黙って順番を決めずに止めるため。"""

    def __init__(self, step: int, modifiers: tuple[DamageModifier, ...]):
        self.step = step
        self.modifiers = modifiers
        self.chooser = DAMAGE_STEP_CHOOSER[step]
        super().__init__(
            f"{step} 段階に加算でない変更効果を含む {len(modifiers)} つの効果（{[m.label for m in modifiers]}）があり、計算の順番によって結果が変わる。"
            f"順番は {self.chooser}（ワザを使うプレイヤー・受けるプレイヤー）が決める（p.321）"
        )


class DamageReductionRequired(RuntimeError):
    """5 段階の「好きなだけ小さくしてよい」効果（``REDUCE_CHOICE``。お上品攻撃）があり、減らす量が渡されていない（v0.66）。

    - ``value``: 5 段階のほかの効果を当てはめたあとのダメージ（減らす前）
    - ``choices``: 選べる減らす量（0 = 減らさない、ダメージカウンターの単位ずつ ``value`` まで。``value`` が 0 以下なら (0,)）
    - ``below_zero``: 0 より小さくすることで、0 にしたときと違う計算の結果（最終ダメージと 2 段階で終えるか）になるか（6〜8 段階に、ダメージを増やす
      効果があるとき。「好きなだけ」が 0 より小さくすることを含むかは決まらない（CA1。``kernel.deal_damage`` が止める））
    - ``modifiers``: その効果（集めた順番）。``chooser`` はワザを使うプレイヤー（``"attacker"``。p.321 の 5 段階の効果の持ち主）

    呼ぶ側（解決の基盤のダメージの要素）が決定で量を選ばせて、``reduction`` に渡してもう一度計算する。``RuntimeError`` の部分型なのは、``DamageOrderRequired``
    と同じく、決定を出せない古い計算でこの場合に来たら、黙って減らす量を決めずに止めるため。"""

    def __init__(self, value: int, choices: tuple[int, ...], below_zero: bool, modifiers: tuple[DamageModifier, ...]):
        self.value = value
        self.choices = choices
        self.below_zero = below_zero
        self.modifiers = modifiers
        self.chooser = "attacker"
        super().__init__(f"5 段階の「好きなだけ小さくしてよい」効果（{[m.label for m in modifiers]}）の減らす量が渡されていない（{value} ダメージ）")

    def outcome(self) -> tuple:
        """色の読み方ごとの比べ（``effects.same_for_type_readings``）に使う値。"""
        return ("reduce", self.value, self.choices, self.below_zero, tuple(m.label for m in self.modifiers))


def step_orders(count: int) -> tuple[tuple[int, ...], ...]:
    """同じ段階の ``count`` 個の変更効果の計算の順番のすべて（集めた順番の番号の並べかえ。辞書順。順番の決定の選べるものの番号はこの並びの位置）。"""
    return tuple(itertools.permutations(range(count)))


@dataclass(frozen=True)
class DamageCalculation:
    base: int
    weakness_applied: bool
    resistance_applied: bool
    stopped_after_step_2: bool
    final: int  # 相手に与えるダメージ。0 なら「ダメージを与えなかった」
    steps: tuple[tuple[str, int], ...]
    modifiers: tuple[DamageModifier, ...] = ()  # 計算に使った変更効果（v0.2c）。2 段階で終えたら 2 段階のものだけ（v0.2d）
    reduction: int = 0  # v0.66: 5 段階で「好きなだけ小さく」した量（お上品攻撃。減らさなければ 0）
    reduced_by: tuple[int | None, ...] = ()  # v0.66: その効果の発生源のカード（減らす量を決めたときだけ。量が 0 でも書く）
    # v0.90: 3 段階で、共通のルールの数（×2）ではない数をかけたとき、その数（のろいマーカーの「×4」）。弱点を計算しなかった・共通のルールの数なら None
    weakness_multiplier: int | None = None
    # v0.102: 特殊能力（［グリーンシールド］・［ニュートラルダメージ］）で影響を受けなかった弱点・抵抗力の、はたらいた力（(持つポケモンの番号, ``PowerKey`` の文字列) の並び）。
    # その力がなければ 3・4 段階を計算していたときだけ書く（タイプが合わない・2 段階で終えた・ワザの説明やスタジアムですでに計算しないときは空。``effects.calculate_with_stadium``）
    weakness_ignored_by: tuple[tuple[int, str], ...] = ()
    resistance_ignored_by: tuple[tuple[int, str], ...] = ()


def calculate_attack_damage(
    base: int,
    attacker: CardDefinition,
    defender: CardDefinition,
    rules: RuleSet,
    modifiers: Sequence[DamageModifier] = (),
    *,
    weakness_resistance: bool = True,
    orders: Mapping[int, tuple[int, ...]] | None = None,
    resistance: bool = True,
    weakness: bool = True,
    reduction: int | None = None,
) -> DamageCalculation:
    """バトル場のポケモンがワザで相手のバトル場のポケモンに与えるダメージ。

    ``modifiers`` は 2・5〜8 段階の変更効果（v0.2c）。渡さなければ v0.1 と同じ計算・同じ記録になる。
    ``weakness_resistance``（v0.31）: False なら 3・4 段階（弱点・抵抗力）を計算しない（説明に「「弱点・抵抗力」に関係なく」とあるダメージ。
    カツラのリザードの「やきはらう」など）。ほかの段階は同じ。
    ``orders``（v0.35）: 段階ごとの、その段階の変更効果の計算の順番（集めた順番の番号の並べかえ。順番の決定で選んだもの）。同じ段階に加算でない
    効果を含む 2 つ以上の効果があり、順番によって結果（最終ダメージと 2 段階で終えるか）が変わる段階の順番がなければ ``DamageOrderRequired``。
    結果が変わらない段階は、渡されていなければ集めた順番で計算する。
    ``resistance``（v0.45）: False なら 4 段階（抵抗力）だけを計算しない（説明に「このワザのダメージは、「抵抗力」の影響を受けない」とあるダメージ。
    タケシのイシツブテの「スパイラルショット」）。弱点（3 段階）とほかの段階は計算する。
    ``weakness``（v0.57）: False なら 3 段階（弱点）だけを計算しない（グレンタウンジムの「「カツラのポケモン」は、「水」ポケモンからダメージを受ける時、「弱点」の影響を
    受けない」。``effects.calculate_with_stadium``）。抵抗力とほかの段階は計算する。v0.102: 特殊能力（［グリーンシールド］・［ニュートラルダメージ］）で影響を受けない弱点・
    抵抗力も、``weakness``・``resistance`` で渡す（受けるポケモンの弱点・抵抗力の性質は変えず、この計算で当てはめるかだけを変える。``effects.weakness_resistance_ignored``）。
    ``reduction``（v0.66）: 5 段階の「好きなだけ小さくしてよい」効果（``REDUCE_CHOICE``。お上品攻撃）で減らす量。その効果があり、2 段階で計算を終えないのに
    渡されていなければ ``DamageReductionRequired``（呼ぶ側が決定で選ばせる）。2 段階の順番の決定は減らす量より先、6〜8 段階の順番の決定は減らす量のあと（減らした
    あとのダメージで比べる）。``REDUCE_CHOICE`` は 5 段階のほかの効果（加算だけ）のあとに当てはめる（docs/optional-trainers-v0.66.md 2.3 節）。
    v0.97: ``attacker_type`` のある変更効果は、``attacker``（ダメージを与えるポケモンの今有効な値の定義。色の読み方ごと）のタイプが同じときだけ当てはめる（ほかは集めない）。
    """
    used = tuple(m for m in modifiers if m.attacker_type is None or m.attacker_type is attacker.pokemon_type)
    reducers = tuple(m for m in used if m.operation == REDUCE_CHOICE)
    used = tuple(m for m in used if m.operation != REDUCE_CHOICE)
    if reducers and any(m.step == 5 and m.operation != ADD for m in used):
        raise RuntimeError("5 段階に、好きなだけ小さくする効果と加算でない効果がある（今の写しでは起こらない。当てはめる順番を決めていない）")
    if reduction is not None and not reducers:
        raise ValueError(f"減らす量 {reduction!r} を渡したが、好きなだけ小さくする効果がない")
    chosen = dict(orders or {})
    for step, order in chosen.items():
        at_step = [m for m in used if m.step == step]
        if step not in DAMAGE_STEP_CHOOSER or len(at_step) < 2 or sorted(order) != list(range(len(at_step))):
            raise ValueError(f"{step} 段階の計算の順番 {order!r} が、その段階の {len(at_step)} つの変更効果の並べかえではない")
    for step in DAMAGE_STEP_CHOOSER:
        at_step = tuple(m for m in used if m.step == step)
        if step > 5 and reducers and reduction is None:
            # v0.66: 6〜8 段階の順番は減らしたあとのダメージで比べるので、先に減らす量を決める（2 段階で終えるなら、減らす量は要らない）
            _calculate(base, attacker, defender, rules, used, weakness_resistance, chosen, resistance, weakness, reducers=reducers)
            break
        if step in chosen or len(at_step) < 2 or all(m.operation == ADD for m in at_step):
            continue
        # 加算でない効果は、同じ段階のほかの効果との順番で結果が変わりうる。p.321 は順番を DAMAGE_STEP_CHOOSER のプレイヤーが決めるとする。
        # どの順番でも結果（最終ダメージと 2 段階で終えるか）が同じなら決めさせない（あとの段階は、渡された順番か集めた順番で比べる）
        # v0.66: 減らす量がまだ決まっていない 2 段階の順番は、5 段階の減らす前のダメージ（と 2 段階で終えるか）で比べる
        partial = bool(reducers) and reduction is None
        outcomes = {_outcome(_calculate(base, attacker, defender, rules, used, weakness_resistance, {**chosen, step: order}, resistance, weakness,
                                        reducers=reducers, reduction=reduction, partial=partial))
                    for order in step_orders(len(at_step))}
        if len(outcomes) > 1:
            raise DamageOrderRequired(step, at_step)
    return _calculate(base, attacker, defender, rules, used, weakness_resistance, chosen, resistance, weakness, reducers=reducers, reduction=reduction)


def _outcome(calc: DamageCalculation) -> tuple[int, bool]:
    return calc.final, calc.stopped_after_step_2


def _calculate(base: int, attacker: CardDefinition, defender: CardDefinition, rules: RuleSet, used: tuple[DamageModifier, ...],
               weakness_resistance: bool, orders: Mapping[int, tuple[int, ...]], resistance: bool = True, weakness: bool = True, *,
               reducers: tuple[DamageModifier, ...] = (), reduction: int | None = None, partial: bool = False) -> DamageCalculation:
    """p.321 の 8 段階の計算（順番の確かめは ``calculate_attack_damage``）。段階の中の変更効果は、``orders`` にあればその順番、なければ集めた順番。

    結果の ``modifiers`` は v0.34 と同じ集めた順番（2 段階で終えたら 2 段階のものだけ）で、順番を選んだ段階のものだけ、その段階の位置の中で選んだ
    順番に並べかえる（順番の決定のない計算のログ ``damage`` の ``modifiers`` は v0.34 と同じ並び）。"""
    steps: list[tuple[str, int]] = []

    def at(step: int) -> list[DamageModifier]:
        found = [m for m in used if m.step == step]
        order = orders.get(step)
        return found if order is None else [found[i] for i in order]

    def apply(step: int, amount: int) -> int:
        for modifier in at(step):
            amount = modifier.apply(amount, rules.damage_per_counter)
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
        return DamageCalculation(base, False, False, True, 0, tuple(steps), _in_order(tuple(m for m in used if m.step == 2), orders))

    # 3. ワザを使うポケモンのタイプが、ワザを受けるポケモンの「弱点」のタイプなら 2 倍（p.315, p.321）
    # v0.90: 受けるポケモンの今有効な値の定義が弱点の計算でかける数を持てば、その数（のろいマーカーの「×2」ではなく「×4」。``CardDefinition.weakness_multiplier``）
    weakness_applied = weakness_resistance and weakness and defender.weakness is not None and attacker.pokemon_type == defender.weakness
    special = defender.weakness_multiplier if weakness_applied and defender.weakness_multiplier not in (None, rules.weakness_multiplier) else None
    if weakness_applied:
        amount *= rules.weakness_multiplier if special is None else special
        steps.append(("3 弱点", amount))

    # 4. ワザを使うポケモンのタイプが「抵抗力」のタイプなら、抵抗力の数字をマイナス（p.315, p.321）
    # 計算の途中で 0 やマイナスになってもよい（p.319, p.321）
    # v0.45: ``resistance`` が False（「抵抗力」の影響を受けない）なら計算しない
    resistance_applied = weakness_resistance and resistance and defender.resistance is not None and attacker.pokemon_type == defender.resistance
    if resistance_applied:
        amount -= defender.resistance_value
        steps.append(("4 抵抗力", amount))

    # 5. ワザを使うポケモンについているカードの効果（プラスパワーなど）
    amount = apply(5, amount)
    applied_reduction = 0
    if reducers:
        # v0.66: 5 段階の「好きなだけ小さくしてよい」（お上品攻撃）。5 段階のほかの効果のあと
        if partial:
            return DamageCalculation(base, weakness_applied, resistance_applied, False, amount, tuple(steps), (), weakness_multiplier=special)
        if reduction is None:
            unit = rules.damage_per_counter

            def tail(value: int) -> tuple[int, bool]:
                return _outcome(_finish(value, [], base, weakness_applied, resistance_applied, used, orders, rules, special=special))

            choices = tuple(range(0, amount + 1, unit)) if amount > 0 else (0,)
            reachable = {tail(amount - r) for r in choices}
            floor = min(amount, 0)
            depth = unit + sum(abs(m.amount) + (m.threshold or 0) for m in used if m.step > 5 and m.operation not in (MULTIPLY, HALVE_UP, HALVE_DOWN))
            below = any(tail(floor - k) not in reachable for k in range(unit, depth + 2 * unit, unit))
            raise DamageReductionRequired(amount, choices, below, reducers)
        if reduction < 0 or reduction % rules.damage_per_counter or reduction > max(amount, 0):
            raise ValueError(f"減らす量 {reduction!r} が、0 からダメージ {amount} までのダメージカウンターの単位の数ではない")
        applied_reduction = reduction
        amount -= reduction
        steps.append((f"5 {reducers[0].label}", amount))
    return _finish(amount, steps, base, weakness_applied, resistance_applied, used, orders, rules, applied_reduction, reducers, special=special)


def _finish(amount: int, steps: list, base: int, weakness_applied: bool, resistance_applied: bool, used: tuple[DamageModifier, ...],
            orders: Mapping[int, tuple[int, ...]], rules: RuleSet, reduction: int = 0, reducers: tuple[DamageModifier, ...] = (), *,
            special: int | None = None) -> DamageCalculation:
    """6〜8 段階と最終ダメージ（v0.66。``_calculate`` から分けた。5 段階の減らす量の比べにも使う）。"""
    def at(step: int) -> list[DamageModifier]:
        found = [m for m in used if m.step == step]
        order = orders.get(step)
        return found if order is None else [found[i] for i in order]

    # 6. それ以外の効果、7. ワザを受けるポケモンについているカードの効果、8. ワザを受けるポケモンの効果
    for step in (6, 7, 8):
        for modifier in at(step):
            amount = modifier.apply(amount, rules.damage_per_counter)
            steps.append((f"{step} {modifier.label}", amount))

    # 最終的に 0 以下なら「ダメージを与えなかった」（p.319, p.321）
    final = amount if amount > 0 else 0
    return DamageCalculation(base, weakness_applied, resistance_applied, False, final, tuple(steps), _in_order(used, orders), reduction,
                             tuple(m.source for m in reducers), special)


def _in_order(modifiers: tuple[DamageModifier, ...], orders: Mapping[int, tuple[int, ...]]) -> tuple[DamageModifier, ...]:
    """``modifiers``（集めた順番）のうち、``orders`` にある段階のものを、その段階の位置の中で選んだ順番に並べかえる（ほかはそのまま）。"""
    result = list(modifiers)
    for step, order in orders.items():
        positions = [i for i, m in enumerate(result) if m.step == step]
        picked = [result[i] for i in positions]
        for position, index in zip(positions, order):
            result[position] = picked[index]
    return tuple(result)


def calculate_confusion_damage(pokemon: CardDefinition, rules: RuleSet, base: int, *, weakness: bool = True, resistance: bool = True) -> DamageCalculation:
    """こんらん状態のポケモンのワザがこんらんしたとき（コインが「うら」）、ワザを使ったポケモン自身が受けるダメージ（v0.3c）。

    - 基本は 20（p.309 の手順 5「もとのワザの内容に関わらず、ワザを使ったポケモン自身が20ダメージを受けます」）。
    - 「このダメージは「弱点・抵抗力」の影響を受けます」（p.322。CONFIRMED）。ダメージを与えるのも受けるのも同じポケモン
      なので、そのポケモンのタイプが自分の弱点のタイプなら 2 倍、抵抗力のタイプなら抵抗力の数字をマイナスする（p.321 の
      3・4 段階の定義をそのまま当てはめる。SUPPORTED）。0 以下なら 0（「ダメージを受けなかった」。p.321）。
    - v0.90: かける数は共通のルールの数（のろいマーカーの「×4」は「ワザのダメージを受ける時」の効果で、こんらんの 20 が「ワザによるダメージ」かは決まらないので、
      当てはまりうるときはコインの前に止める。``procedures.confusion_damage_problem``）。
    - これは ``calculate_attack_damage``（「ワザによるダメージ」の 8 段階。p.321「8」「9」）とは別の計算にしている。こんらんの
      ダメージが「ワザによるダメージ」かは原典に書かれていないので、プラスパワー（5 段階）・ディフェンダー（7 段階）などを
      計算するかは決められない（UNRESOLVED）。ワザを使うポケモンにそれらがついているときは、エンジンがコインを投げる前に
      止める（``engine._confusion_damage_problem``）ので、ここには変更効果が来ない。
    - v0.102: ``weakness``・``resistance`` が False なら、弱点・抵抗力の影響を受けない（［グリーンシールド］・［ニュートラルダメージ］の「ダメージを受ける時」。説明はワザのダメージに
      限らない。``effects.confusion_damage_calculation``）。性質は変えない。
    """
    steps: list[tuple[str, int]] = [("こんらん", base)]
    amount = base
    weakness_applied = weakness and pokemon.weakness is not None and pokemon.pokemon_type == pokemon.weakness
    if weakness_applied:
        amount *= rules.weakness_multiplier
        steps.append(("弱点", amount))
    resistance_applied = resistance and pokemon.resistance is not None and pokemon.pokemon_type == pokemon.resistance
    if resistance_applied:
        amount -= pokemon.resistance_value
        steps.append(("抵抗力", amount))
    final = amount if amount > 0 else 0
    return DamageCalculation(base, weakness_applied, resistance_applied, False, final, tuple(steps))

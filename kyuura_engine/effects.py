"""カードの効果の実装の登録表（v0.2a、レビューの M5）。

カードのデータ（kyuura の写し。印刷された文面と数値）と、エンジンが実装している処理を分けます。
あるワザを対戦で使えるのは、この登録表にそのワザの実装が登録されているときだけです。
説明文が空であることは、実装がある証拠として扱いません（説明文のないワザも、効果のないワザとして
明示的に登録します）。

識別子は ``AttackKey``（カード id とワザの位置）です。ワザ名は識別子にしません。同じ名前のワザでも、
カードが違えば別の登録です。登録するときに確かめたワザ名（``AttackEntry.name_ja``）は、データの
並びが変わったときに気づくための照合にだけ使います。

v0.2a で登録している実装は ``DamageOnly``（説明のないワザ）だけです。トレーナー・ポケモンパワー・
効果のあるワザは、実装を登録するまで未対応のままです。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable, Mapping

from .damage import calculate_attack_damage

if TYPE_CHECKING:
    from .cards import Attack
    from .state import GameState, PendingDecision


@dataclass(frozen=True, order=True)
class AttackKey:
    """ワザの安定した識別子: カード id とワザの位置（カードに印刷された順、0 から）。"""

    card_id: str
    attack_index: int

    def __str__(self) -> str:
        return f"{self.card_id}#{self.attack_index}"


@dataclass(frozen=True)
class AttackUse:
    """ワザを 1 回使ったときの情報。効果の処理（``resolve``・``resume``）に渡す。"""

    player: int
    pokemon_id: int
    key: AttackKey


class AttackEffect:
    """ワザの効果の実装の基底。

    - ``check``: カードのデータ（説明文・ダメージ）がこの実装で処理できる形かを確かめ、問題を返す。
      登録の誤り（効果のあるワザを、効果のない実装に登録するなど）を見つけるため。
    - ``resolve``: ワザの処理（p.309 の手順 6「ワザの説明にしたがって処理」）。途中でプレイヤーの
      決定が要るときは、``decisions.push_decision`` で決定を出して戻る。
    - ``resume``: 出した決定が選ばれたあとの続き。さらに決定を出してもよい（複数段階の選択）。

    決定がなくなったら、エンジンがワザの後の処理（きぜつ・サイド・番の終わり）を続ける。
    """

    implementation_id = "abstract"

    def check(self, attack: Attack) -> list[str]:
        return []

    def resolve(self, state: GameState, use: AttackUse) -> None:
        raise NotImplementedError

    def resume(self, state: GameState, use: AttackUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        raise NotImplementedError(f"{self.implementation_id} は決定を出さない")


@dataclass(frozen=True)
class DamageOnly(AttackEffect):
    """説明のないワザ: ダメージの目安の数字ぶんのダメージを、相手のバトル場のポケモンに与える（p.309, p.320）。

    ダメージは p.321 の順番で計算する（``damage.calculate_attack_damage``）。
    """

    implementation_id = "damage_only"

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.text_ja is not None or attack.text_en is not None:
            problems.append("説明文のあるワザを、効果のないワザとして登録している")
        if attack.damage_modifier is not None:
            problems.append(f"ダメージの「{attack.damage_modifier}」があるワザを、効果のないワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
        return problems

    def resolve(self, state: GameState, use: AttackUse) -> None:
        owner, attacker = state.find_pokemon(use.pokemon_id)
        attacker_def = state.card_def(attacker.card)
        attack = attacker_def.attacks[use.key.attack_index]
        opponent = 1 - use.player
        defender = state.players[opponent].active
        defender_def = state.card_def(defender.card)
        calc = calculate_attack_damage(attack.damage, attacker_def, defender_def, state.rules)
        defender.damage += calc.final
        state.add_event(
            "damage",
            player=opponent,
            pokemon=defender.card,
            amount=calc.final,
            steps=calc.steps,
            weakness=calc.weakness_applied,
            resistance=calc.resistance_applied,
            total_damage=defender.damage,
        )


DAMAGE_ONLY = DamageOnly()


@dataclass(frozen=True)
class AttackEntry:
    """登録の 1 件: 実装と、登録したときに確かめたワザ名。"""

    effect: AttackEffect
    name_ja: str


class EffectRegistry:
    """カードの効果の実装の登録表。対戦ごとに 1 つ使う（``GameState.effects``）。

    v0.2a では、ワザの実装だけを登録できます。トレーナー・ポケモンパワー・特殊エネルギーの実装は、
    それを加えるときに同じ形（カード id などの安定した識別子 → 実装）で登録表を加えます。
    それまでは、これらのカードは未対応です。
    """

    def __init__(self, registry_id: str, attacks: Mapping[AttackKey, AttackEntry] | Iterable[tuple[AttackKey, AttackEntry]]):
        self.id = registry_id
        self._attacks: dict[AttackKey, AttackEntry] = dict(attacks)

    def __repr__(self) -> str:
        return f"EffectRegistry({self.id!r}, {len(self._attacks)} attacks)"

    def attack_keys(self) -> tuple[AttackKey, ...]:
        return tuple(sorted(self._attacks))

    def attack_entry(self, card_id: str, attack_index: int) -> AttackEntry | None:
        return self._attacks.get(AttackKey(card_id, attack_index))

    def attack_problem(self, card_id: str, attack: Attack) -> str | None:
        """このワザを使えない理由。使えるなら None。"""
        entry = self.attack_entry(card_id, attack.index)
        if entry is None:
            features = []
            if attack.text_ja is not None or attack.text_en is not None:
                features.append("説明文あり")
            if attack.damage_display is not None:
                features.append(f"ダメージ「{attack.damage_display}」")
            detail = f"（{'・'.join(features)}）" if features else ""
            return f"ワザの効果の実装が登録されていない{detail}"
        if entry.name_ja != attack.name_ja:
            return f"登録したワザ名「{entry.name_ja}」と、データのワザ名「{attack.name_ja}」が違う"
        problems = entry.effect.check(attack)
        return "; ".join(problems) or None

    def attack_effect(self, card_id: str, attack: Attack) -> AttackEffect | None:
        """使えるワザなら実装を返す。登録がない・データと合わないなら None。"""
        if self.attack_problem(card_id, attack) is not None:
            return None
        return self.attack_entry(card_id, attack.index).effect

    def with_attacks(self, registry_id: str, attacks: Mapping[AttackKey, AttackEntry]) -> EffectRegistry:
        """登録を加えた新しい登録表（元の登録表は変えない）。テストや、実装を段階的に加えるときに使う。"""
        return EffectRegistry(registry_id, {**self._attacks, **attacks})

    def without_attacks(self, registry_id: str, keys: Iterable[AttackKey]) -> EffectRegistry:
        """登録を除いた新しい登録表（元の登録表は変えない）。"""
        removed = set(keys)
        return EffectRegistry(registry_id, {k: v for k, v in self._attacks.items() if k not in removed})

    def describe(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "attacks": {str(k): {"implementation": e.effect.implementation_id, "name_ja": e.name_ja} for k, e in sorted(self._attacks.items())},
        }


def _damage_only(entries: Iterable[tuple[str, int, str]]) -> dict[AttackKey, AttackEntry]:
    return {AttackKey(card_id, index): AttackEntry(DAMAGE_ONLY, name) for card_id, index, name in entries}


# v0.2a の登録。v0.1 で使えたワザ（説明文のない固定ダメージのワザ）を、効果のないワザとして登録する。
# どれも『ポケモンカードオフィシャルブック2000』のカードのページで、「ワザ」欄に説明文がないことを
# 画像で確かめた（kyuura_engine/data/card_verification.json）。ワザ名は kyuura の写しの値（照合用）。
DEFAULT_EFFECTS = EffectRegistry(
    "kyuura-engine-0.2a",
    _damage_only([
        ("PMCG1-016", 0, "けりとばす"),  # ポニータ。p.75 は「けとばす」（kyuura との食い違い。data-provenance.md）
        ("PMCG1-016", 1, "ほのおのしっぽ"),
        ("PMCG1-018", 0, "ほのお"),  # ガーディ p.72
        ("PMCG1-025", 0, "ひらてうち"),  # ヒトデマン p.110
        ("PMCG1-029", 0, "ずつき"),  # パウワウ p.101
        ("PMCG1-037", 0, "たいあたり"),  # ビリリダマ p.136
        ("PMCG1-052", 0, "あなをほる"),  # ディグダ p.182
        ("PMCG1-052", 1, "どろかけ"),
        ("PMCG1-053", 0, "けたぐり"),  # ワンリキー p.189
        ("PMCG1-058", 0, "ジャブ"),  # エビワラー p.203
        ("PMCG1-058", 1, "スペシャルパンチ"),
        ("PMCG1-060", 0, "かみつく"),  # コラッタ p.217
        ("PMCG1-065", 0, "はたく"),  # ミニリュウ p.246
        # ヒトカゲ（参照カード。デッキには入らない）の「ひっかく」。p.63 で説明文がないことを確かめた。
        # もう 1 つのワザ「ひのこ」は効果があり、登録していない（カードは未対応のまま）
        ("PMCG1-014", 0, "ひっかく"),
    ]),
)

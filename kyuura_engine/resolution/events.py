"""内部のイベント・処理の枠・解決の記録（docs/event-model-v0.14.md 1 章・4 章）。

ここにある値は、1 つのコマンドの解決の中だけで使い、状態（``GameState``）に保存しません。公開のログ（``GameState.log``）とは
別のもので、ログを作り直すこともしません。検証のために ``apply_command_traced`` が解決の記録（``Trace``）を返します。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DamageClass(str, Enum):
    """ダメージの分類（p.321「8」）。どの効果の候補になるかを決める。"""

    ATTACK = "attack"  # ワザによるダメージ（宣言したワザの要素・前の番のワザの効果で返すダメージ）
    POWER = "power"  # 特殊能力によるダメージ（はんげき。p.321「8」・p.138・p.245）
    CONFUSION = "confusion"  # こんらんの 20（ワザによるダメージかは決められない。v0.3c）


class FrameKind(str, Enum):
    """処理の枠の種類（4 章）。"""

    ATTACK = "attack"  # 宣言したワザ
    RETALIATION = "retaliation"  # 前の番のワザの効果で返すダメージ（ほのおのかべ・こうらがえし）
    POWER_DAMAGE = "power_damage"  # 特殊能力のダメージ（はんげき）
    CONFUSION = "confusion"  # こんらんしたワザの 20


# どの枠がどの枠を起こせるか（4 章の表）。表にない枠を起こそうとしたら、規定から起こらないはずのことなので止める（回数の上限ではない）
SPAWNS: dict[FrameKind, frozenset[FrameKind]] = {
    FrameKind.ATTACK: frozenset({FrameKind.POWER_DAMAGE, FrameKind.RETALIATION}),
    FrameKind.RETALIATION: frozenset({FrameKind.POWER_DAMAGE}),
    FrameKind.POWER_DAMAGE: frozenset(),
    FrameKind.CONFUSION: frozenset(),
}

# 表にない連鎖が規定から起こらない理由（起こったら止めるときの理由の文。v0.15b。v0.13 の経路の同じ場合の文と同じ前提を書く）
SPAWN_REFUSALS: dict[tuple[FrameKind, FrameKind], str] = {
    (FrameKind.RETALIATION, FrameKind.RETALIATION): (
        "返すダメージを受けるのは番のプレイヤーのポケモンで、その持続する効果がはたらくのは持ち主の相手の番なので、返すダメージで"
        "ダメージを返す効果がはたらくことはない（番の進み方の前提に反する。v0.13 の S45）"
    ),
}

FRAME_DAMAGE_CLASS = {
    FrameKind.ATTACK: DamageClass.ATTACK,
    FrameKind.RETALIATION: DamageClass.ATTACK,
    FrameKind.POWER_DAMAGE: DamageClass.POWER,
    FrameKind.CONFUSION: DamageClass.CONFUSION,
}


class Window(str, Enum):
    """処理の段階（窓。3 章）。順番は原典の処理の順番で、ここで並べた順に開く。"""

    DECLARE = "declare"  # 宣言の前（合法性・先読み）
    BEFORE_DAMAGE = "before_damage"  # ダメージの適用の前（無効・置きかえ）
    DAMAGE_RECEIVING = "damage_receiving"  # ダメージを受けるとき（状態の写し）・受けたとき（送る効果）
    AFTER_DAMAGE_ELEMENTS = "after_damage_elements"  # ダメージの要素のあと・効果の要素の前（p.89）
    BEFORE_EFFECT = "before_effect"  # 効果の要素の適用の前（置きかえ）
    KO_CHECK = "ko_check"  # きぜつの判定（任意の効果の決定）
    KO_PROCESS = "ko_process"  # きぜつの処理（トラッシュの前の写し）
    AFTER_JUDGE = "after_judge"  # 勝ち負けの判定のあと・バトル場に出す前（任意の効果の決定。正規化した順番）
    TURN_END = "turn_end"  # 番の終わり（期限）


@dataclass(frozen=True)
class Frame:
    """処理の枠。ダメージを与えるのは ``source_pid``（持ち主 ``player``）。ワザの分類のダメージなら ``attack_key`` はそのワザ。"""

    id: int
    kind: FrameKind
    parent: int | None
    player: int
    source_pid: int
    attack_key: Any  # kyuura_engine.effects.AttackKey（枠がワザでなければ、それを起こしたワザ）

    @property
    def damage_class(self) -> DamageClass:
        return FRAME_DAMAGE_CLASS[self.kind]


@dataclass
class FrameState:
    """枠ごとの、解決の中だけの値。"""

    frame: Frame
    pending: list = field(default_factory=list)  # 送る効果（ダメージの要素のあとの窓で処理する。``Deferred``）
    reception: dict[int, bool] = field(default_factory=dict)  # 「とうめい」の結果（1 つのワザで 1 匹 1 回。T4）
    results: dict[str, Any] = field(default_factory=dict)  # 要素の結果（名前 → ``DamageResult``）
    coins: dict[str, Any] = field(default_factory=dict)  # ワザ全体のコイン（名前 → ``CoinFlips``）
    # v0.15b: 止める理由の文（questions）に書く値。結果を変えない（記録の Trace とは別。理由の文だけに使う）
    origin: Any = None  # 枠を起こした効果（``catalog.EffectInstance``。ワザの枠は None）
    applied: dict[int, int] = field(default_factory=dict)  # この枠でのせたダメージ（受けたポケモンの番号 → 最終ダメージ）
    evaded: dict[int, int] = field(default_factory=dict)  # 「とうめい」で受けなかったダメージの要素（ポケモンの番号 → 最終ダメージ）


# ---------------------------------------------------------------- 内部のイベント（記録用）


@dataclass(frozen=True)
class WindowOpened:
    window: Window
    frame: int | None


@dataclass(frozen=True)
class DamageProposal:
    frame: int
    target_pid: int
    target_owner: int
    target_kind: str
    base: int


@dataclass(frozen=True)
class DamageVoided:
    frame: int
    target_pid: int
    reason: str


@dataclass(frozen=True)
class DamageEvaded:
    frame: int
    target_pid: int
    amount: int


@dataclass(frozen=True)
class DamageApplied:
    frame: int
    damage_class: DamageClass
    source_pid: int
    target_pid: int
    target_owner: int
    final: int
    before: int
    after: int
    by_opponent: bool


@dataclass(frozen=True)
class ElementStarted:
    frame: int
    index: int
    element: str
    phase: str


@dataclass(frozen=True)
class ElementSkipped:
    frame: int
    element: str
    reason: str


@dataclass(frozen=True)
class CandidateFound:
    window: Window
    definition: str
    holder_pid: int | None
    frame: int | None


@dataclass(frozen=True)
class Activated:
    window: Window
    definition: str
    holder_pid: int | None
    frame: int | None


@dataclass(frozen=True)
class FrameOpened:
    frame: Frame


@dataclass(frozen=True)
class KnockedOutRecorded:
    pid: int
    frame: int


@dataclass(frozen=True)
class QuestionHit:
    question: str
    detail: str


@dataclass(frozen=True)
class Suspended:
    resume: str
    kind: str
    player: int


@dataclass(frozen=True)
class Delegated:
    command: str


@dataclass(frozen=True)
class PreflightResult:
    mode: str
    branches: int
    questions: tuple[str, ...]


class Trace:
    """1 つのコマンドの解決の記録（内部のイベントの並び）。状態に保存しない。"""

    def __init__(self) -> None:
        self.events: list[Any] = []

    def record(self, event: Any) -> None:
        self.events.append(event)

    def of(self, kind: type) -> list[Any]:
        return [event for event in self.events if isinstance(event, kind)]

    def __len__(self) -> int:
        return len(self.events)

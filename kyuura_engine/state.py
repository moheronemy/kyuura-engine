"""対戦中の状態。

カードの印刷された情報（HP・ワザなど）は ``CardDefinition`` が持ち、ここでは持ちません。
ここにあるのは、どのカードがどこにあるか、ポケモンのダメージ、番の進行などの、対戦中に
変わる値だけです。

1 枚 1 枚のカードには、対戦ごとに通し番号（uid）を付けます。デッキの中の同じカードも別の
uid になります。ゾーン（山札・手札など）は uid のリストで、山札は先頭が一番上です。
エネルギーは「どのエネルギーカードがどのポケモンについているか」を uid で持ちます。

``GameState.clone()`` は、変わる部分（リスト・乱数の状態）をすべて複製します。
変わらない部分（カードの定義・uid とカードの対応・ログの各要素）は読み取り専用の形で共有します。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Mapping

from .cards import CardDefinition, EnergyType
from .rng import copy_rng

if TYPE_CHECKING:
    from .effects import EffectRegistry
from .rules import RuleSet


class Phase(str, Enum):
    SETUP_PLACEMENT = "setup_placement"  # バトル場・ベンチにポケモンを出す（両方のプレイヤー）
    SETUP_MULLIGAN_DRAW = "setup_mulligan_draw"  # 相手の切り直しのぶん、最大 2 枚ずつ引く
    SETUP_FIRST_PLAYER = "setup_first_player"  # ジャンケンの結果を受け取る
    MAIN = "main"  # 番のプレイヤーの操作
    TAKE_PRIZE = "take_prize"  # 決定待ち: きぜつさせたプレイヤーがサイドを選んで取る
    PROMOTE_ACTIVE = "promote_active"  # 決定待ち: バトル場のポケモンがいなくなったプレイヤーがベンチから出す
    DECISION = "decision"  # 決定待ち: 上の 2 つ以外の決定（トレーナー・ワザの効果の途中の選択など）
    GAME_OVER = "game_over"
    SUDDEN_DEATH = "sudden_death"  # サドン・デスに移った（延長戦の開始は v0.1 では未実装）
    HALTED = "halted"  # 未解決の裁定に当たったので止めた（終端。再開する API はない）


# この段階になったら、どのコマンドも受け付けない。GAME_OVER・SUDDEN_DEATH は result、HALTED は halt を持つ
# （HALTED の result は None なので、「result が None なら続いている」とは判断できない）
TERMINAL_PHASES = frozenset({Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED})


@dataclass(frozen=True)
class CardInstance:
    uid: int
    card_id: str
    owner: int


@dataclass(frozen=True)
class AttachedTrainer:
    """ポケモンについているトレーナーカード（v0.2c。プラスパワーなど「つけて使う」トレーナー）。

    ポケモンにつけて使うトレーナーカードは、それをつけているポケモンのいる場所にあることになる
    （p.313）。そのため、ついているポケモン（``PokemonInPlay.trainers``）が持つ。にげる・入れ替えでは
    ポケモンといっしょに移り（p.311）、きぜつしたらポケモンといっしょにトラッシュする（p.323）。

    - ``card``: トレーナーカードの uid（効果の発生源。効果の内容はカード id で効果の登録表から引く）
    - ``player``: 使ったプレイヤー（カードの持ち主）
    - ``discard_at_end_of_turn``: この番（``GameState.turn_number``）の終わりにトラッシュする（有効期限）
    """

    card: int
    player: int
    discard_at_end_of_turn: int


@dataclass(frozen=True)
class Poison:
    """どく状態（v0.3a。p.322「1. どく状態」、p.323 のポケモンチェックの 2）。

    - ``damage``: ポケモンチェックの「どく」で受けるダメージ。通常のどくは 10（p.322・p.323）。
      p.322 は、どくのダメージを変える効果（「このワザによって、どく状態になったポケモンがポケモンチェックで
      受ける「どく」のダメージは「20」。」など）を「どく状態にかかるもの」としてあつかうと書くので、
      ダメージの量をどく状態の性質として持つ。そのような効果のカードは未実装（量は今は 10 だけ）。

    どく状態にしたポケモン（発生源）は持たない。発生源が場をはなれても、変化しても、受けた特殊状態は
    消えたり変化したりしない（p.322）ので、処理に使わないため。どく状態は重ならない（p.322）ので、
    1 匹のポケモンに 1 つだけ。
    """

    damage: int = 10


@dataclass(frozen=True)
class SpecialConditions:
    """場のポケモンの特殊状態（v0.3a）。物理的なカードではないので、カードの uid ではなく、場のポケモン
    （``PokemonInPlay``。番号は ``pokemon_id``）が持つ。

    p.322 の規定にしたがって分けて持つ:

    - ``poison``: どく状態（``Poison``）か None。どく状態は、ほかの特殊状態と重複する（p.322「特殊状態の重複」）。
    - ねむり・マヒ・こんらんは「重複することはありません」（p.322）。v0.3b 以降で、3 つのうち 1 つを持つ
      項目を加える（今は扱わない）。

    特殊状態になるのはバトル場のポケモンだけ（p.322）。バトル場をはなれたら（ベンチに戻ったら）すべて
    消える（p.311・p.322）。進化しても消える（p.322。進化は未実装）。
    """

    poison: Poison | None = None

    def names(self) -> tuple[str, ...]:
        """今かかっている特殊状態の名前（ログ・書き出し用。p.322 の順）。"""
        return ("poison",) if self.poison is not None else ()


# 特殊状態のないポケモン（共有してよい。frozen）
NO_SPECIAL_CONDITIONS = SpecialConditions()


@dataclass
class PokemonInPlay:
    """場にいるポケモン。v0.1 は進化がないので、ポケモンのカード 1 枚とついているエネルギーカード。

    識別子は 2 つあります。

    - ``card``: いちばん上のポケモンのカードの uid（物理的なカード。対戦中に変わらない番号だが、
      進化するといちばん上のカードが変わる）
    - ``pokemon_id``: 場のポケモンそのものの番号。場に出たときに ``GameState.next_pokemon_id`` から
      付ける。場にいるあいだ（にげる・入れ替え、将来の進化・退化でも）変わらない。場を離れたら無効になり、
      同じカードがもう一度場に出ても前の番号は使わない。0 は「付けていない」（不変条件で拒否する）
    """

    card: int
    energy: list[int] = field(default_factory=list)
    damage: int = 0
    pokemon_id: int = 0
    trainers: list[AttachedTrainer] = field(default_factory=list)  # ついているトレーナーカード（v0.2c）
    conditions: SpecialConditions = NO_SPECIAL_CONDITIONS  # 特殊状態（v0.3a。frozen なので複製でも共有してよい）

    def clone(self) -> PokemonInPlay:
        return PokemonInPlay(self.card, list(self.energy), self.damage, self.pokemon_id, list(self.trainers), self.conditions)


@dataclass
class PlayerState:
    deck: list[int]
    hand: list[int] = field(default_factory=list)
    prizes: list[int] = field(default_factory=list)
    discard: list[int] = field(default_factory=list)
    active: PokemonInPlay | None = None
    bench: list[PokemonInPlay] = field(default_factory=list)
    placed_starting_pokemon: bool = False
    mulligans: int = 0
    mulligan_draws_remaining: int = 0

    def clone(self) -> PlayerState:
        return PlayerState(
            deck=list(self.deck),
            hand=list(self.hand),
            prizes=list(self.prizes),
            discard=list(self.discard),
            active=None if self.active is None else self.active.clone(),
            bench=[p.clone() for p in self.bench],
            placed_starting_pokemon=self.placed_starting_pokemon,
            mulligans=self.mulligans,
            mulligan_draws_remaining=self.mulligan_draws_remaining,
        )

    def in_play(self) -> list[PokemonInPlay]:
        return ([self.active] if self.active is not None else []) + list(self.bench)

    def find_in_play(self, uid: int) -> PokemonInPlay | None:
        for pokemon in self.in_play():
            if pokemon.card == uid:
                return pokemon
        return None

    def bench_index(self, uid: int) -> int | None:
        for i, pokemon in enumerate(self.bench):
            if pokemon.card == uid:
                return i
        return None

    def find_by_pokemon_id(self, pokemon_id: int) -> PokemonInPlay | None:
        for pokemon in self.in_play():
            if pokemon.pokemon_id == pokemon_id:
                return pokemon
        return None


@dataclass(frozen=True)
class PendingDecision:
    """保留中の決定（v0.2a）。処理の途中でプレイヤーの選択を待つ。仕組みは ``decisions`` を参照。

    - ``id``: 決定の通し番号（``GameState.next_decision_id`` から）。古い決定への答えを見分ける
    - ``kind``: 決定の種類（``decisions.TAKE_PRIZE`` など）
    - ``player``: 決定するプレイヤー
    - ``options``: 選べるもの（意味は種類による。サイドなら位置、ポケモンなら場のポケモンの番号）
    - ``min_choices``・``max_choices``: 選ぶ数
    - ``resume``: 選んだあとに処理を続ける場所の名前
    - ``context``: 続きに必要な情報（(名前, 値) の組。値は整数・文字列とそのタプル）
    """

    id: int
    kind: str
    player: int
    options: tuple[int, ...]
    min_choices: int
    max_choices: int
    resume: str
    context: tuple[tuple[str, Any], ...] = ()

    def context_value(self, key: str, default: Any = None) -> Any:
        for name, value in self.context:
            if name == key:
                return value
        return default


@dataclass(frozen=True)
class TrainerInUse:
    """使っている最中のトレーナーカード（v0.2b）。

    トレーナーカードは手札から出して相手に見せ、説明にしたがい、使い終わったらトラッシュする（p.310）。
    説明の途中でプレイヤーの決定を待つあいだ、そのカードは手札にもトラッシュにもない。この間だけ、
    ここにある（カードの保存則の対象。``check_invariants``）。1 枚のトレーナーを使っている最中に別の
    トレーナーは使えない（p.310）ので、一度に 1 枚だけ。
    """

    player: int
    card: int


@dataclass(frozen=True)
class GameResult:
    """対戦の結果。``conditions`` は満たした勝利条件の (そのプレイヤー, 条件) の組。

    条件: ALL_PRIZES_TAKEN（サイドを取り終えた）、OPPONENT_CANNOT_FIELD_ACTIVE（相手がバトル場に
    ポケモンを出せない）、OPPONENT_DECK_EMPTY（相手が番の最初に山札から引けなかった）。
    """

    outcome: str  # "win" | "sudden_death"
    winner: int | None
    conditions: tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class Halt:
    """未解決の裁定に当たって対戦を止めたときの理由。"""

    code: str
    message: str
    references: tuple[str, ...]


@dataclass(frozen=True)
class DataSource:
    repository: str
    commit: str
    path: str


@dataclass
class GameState:
    rules: RuleSet
    card_data: DataSource
    seed: int
    rng: random.Random
    cards: Mapping[int, CardInstance]
    definitions: Mapping[str, CardDefinition]
    decklists: tuple[tuple[str, ...], tuple[str, ...]]
    players: list[PlayerState]
    phase: Phase
    effects: EffectRegistry  # この対戦で使う効果の登録表（変わらない。複製では共有する）
    turn_number: int = 0
    current_player: int | None = None
    first_player: int | None = None
    energy_attachments_this_turn: int = 0
    mulligan_rounds: tuple[tuple[int, ...], ...] = ()
    result: GameResult | None = None
    halt: Halt | None = None
    log: tuple[Mapping[str, Any], ...] = ()
    next_pokemon_id: int = 1
    decision: PendingDecision | None = None  # 保留中の決定（一度に 1 つ）
    next_decision_id: int = 1
    trainer_in_use: TrainerInUse | None = None  # 使っている最中のトレーナーカード（決定を待っている間だけ）

    def clone(self) -> GameState:
        new = object.__new__(type(self))
        new.__dict__.update(self.__dict__)
        new.rng = copy_rng(self.rng)
        new.players = [p.clone() for p in self.players]
        return new

    # --- v0.1 との互換のための読み取り専用の値（保留中の決定から作る） ---

    @property
    def pending_prizes(self) -> dict[int, int]:
        """サイドを取る決定を待っているプレイヤーと、取る枚数（v0.1 の pending_prizes と同じ形）。"""
        d = self.decision
        if d is None or d.kind != "take_prize":
            return {}
        counts: dict[int, int] = {}
        for player in (d.player, *d.context_value("remaining", ())):
            counts[player] = counts.get(player, 0) + 1
        return counts

    @property
    def pending_promotions(self) -> list[int]:
        """バトル場にポケモンを出す決定を待っているプレイヤーの順番（v0.1 の pending_promotions と同じ形）。"""
        d = self.decision
        if d is None or d.kind != "promote_active":
            return []
        return [d.player, *d.context_value("remaining", ())]

    # copy.deepcopy・pickle のため。読み取り専用の Mapping（MappingProxyType）はそのままでは
    # pickle できないので、普通の dict にして渡し、もどすときに読み取り専用にもどす。
    def __getstate__(self) -> dict[str, Any]:
        data = dict(self.__dict__)
        data["cards"] = dict(self.cards)
        data["definitions"] = dict(self.definitions)
        data["log"] = tuple(dict(event) for event in self.log)
        return data

    def __setstate__(self, data: dict[str, Any]) -> None:
        data = dict(data)
        data["cards"] = freeze_mapping(data["cards"])
        data["definitions"] = freeze_mapping(data["definitions"])
        data["log"] = tuple(MappingProxyType(dict(event)) for event in data["log"])
        self.__dict__.update(data)

    # --- 読み取り用 ---

    def card_def(self, uid: int) -> CardDefinition:
        return self.definitions[self.cards[uid].card_id]

    def find_pokemon(self, pokemon_id: int) -> tuple[int, PokemonInPlay] | None:
        """場のポケモンの番号から、(持ち主, ポケモン) を返す。場にいなければ None。"""
        for player, p in enumerate(self.players):
            pokemon = p.find_by_pokemon_id(pokemon_id)
            if pokemon is not None:
                return player, pokemon
        return None

    def energy_types(self, pokemon: PokemonInPlay) -> list[EnergyType]:
        return [self.card_def(e).provides for e in pokemon.energy]

    def add_event(self, kind: str, **data: Any) -> None:
        self.log = self.log + (MappingProxyType({"kind": kind, "turn": self.turn_number, **data}),)


def freeze_mapping(mapping: Mapping) -> Mapping:
    return MappingProxyType(dict(mapping))

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
from typing import Any, Mapping

from .cards import CardDefinition, EnergyType
from .rules import RuleSet


class Phase(str, Enum):
    SETUP_PLACEMENT = "setup_placement"  # バトル場・ベンチにポケモンを出す（両方のプレイヤー）
    SETUP_MULLIGAN_DRAW = "setup_mulligan_draw"  # 相手の切り直しのぶん、最大 2 枚ずつ引く
    SETUP_FIRST_PLAYER = "setup_first_player"  # ジャンケンの結果を受け取る
    MAIN = "main"  # 番のプレイヤーの操作
    TAKE_PRIZE = "take_prize"  # きぜつさせたプレイヤーがサイドを選んで取る
    PROMOTE_ACTIVE = "promote_active"  # バトル場のポケモンがいなくなったプレイヤーがベンチから出す
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


@dataclass
class PokemonInPlay:
    """場にいるポケモン。v0.1 は進化がないので、ポケモンのカード 1 枚とついているエネルギーカード。"""

    card: int
    energy: list[int] = field(default_factory=list)
    damage: int = 0

    def clone(self) -> PokemonInPlay:
        return PokemonInPlay(self.card, list(self.energy), self.damage)


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
    turn_number: int = 0
    current_player: int | None = None
    first_player: int | None = None
    energy_attachments_this_turn: int = 0
    pending_prizes: dict[int, int] = field(default_factory=dict)
    pending_promotions: list[int] = field(default_factory=list)
    mulligan_rounds: tuple[tuple[int, ...], ...] = ()
    result: GameResult | None = None
    halt: Halt | None = None
    log: tuple[Mapping[str, Any], ...] = ()

    def clone(self) -> GameState:
        new = object.__new__(type(self))
        new.__dict__.update(self.__dict__)
        new.rng = random.Random()
        new.rng.setstate(self.rng.getstate())
        new.players = [p.clone() for p in self.players]
        new.pending_prizes = dict(self.pending_prizes)
        new.pending_promotions = list(self.pending_promotions)
        return new

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

    def energy_types(self, pokemon: PokemonInPlay) -> list[EnergyType]:
        return [self.card_def(e).provides for e in pokemon.energy]

    def add_event(self, kind: str, **data: Any) -> None:
        self.log = self.log + (MappingProxyType({"kind": kind, "turn": self.turn_number, **data}),)


def freeze_mapping(mapping: Mapping) -> Mapping:
    return MappingProxyType(dict(mapping))

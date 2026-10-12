"""プレイヤーの操作（コマンド）。

コマンドは「何をしたいか」だけを持つ値で、検査と処理は ``engine.apply_command`` が行います。
カードやポケモンは uid（``GameState.cards`` の番号）で指定します。場のポケモンは、
そのポケモンのカードの uid で指定します。

``command_to_dict`` / ``command_from_dict`` は、ほかの言語や画面から JSON で操作を渡すための
変換です。
"""

from __future__ import annotations

from dataclasses import MISSING, asdict, dataclass, fields

from .errors import IllegalActionError


@dataclass(frozen=True)
class PlaceStartingPokemon:
    """対戦準備: 手札のたねポケモンをバトル場に 1 匹、ベンチに 5 匹まで（裏にして）出す（p.308）。"""

    player: int
    active: int
    bench: tuple[int, ...] = ()


@dataclass(frozen=True)
class DrawMulliganCards:
    """対戦準備: 相手の切り直し 1 回ぶんについて、山札から 0〜2 枚引く（p.308）。"""

    player: int
    count: int


@dataclass(frozen=True)
class ReportJankenResult:
    """対戦準備: ジャンケンに勝ったプレイヤーを伝える。勝った人が先攻（p.308）。

    ジャンケンはプレイヤーどうしの外の出来事なので、エンジンは乱数で決めず、結果を受け取る。
    """

    winner: int


@dataclass(frozen=True)
class PlayBasicToBench:
    """手札のたねポケモンをベンチに出す（p.309）。"""

    player: int
    card: int


@dataclass(frozen=True)
class AttachEnergy:
    """手札のエネルギーカードを自分の場のポケモンにつける（p.310）。"""

    player: int
    energy: int
    target: int


@dataclass(frozen=True)
class Retreat:
    """バトル場のポケモンをにがす。トラッシュするエネルギーと、入れ替える控えを選ぶ（pp.310-311）。"""

    player: int
    discard: tuple[int, ...]
    new_active: int


@dataclass(frozen=True)
class UseAttack:
    """バトル場のポケモンのワザを使う（p.309）。``attack_index`` はカードのワザの順番（0 から）。"""

    player: int
    attack_index: int


@dataclass(frozen=True)
class EndTurn:
    """ワザを使わずに番を終える（p.309）。"""

    player: int


@dataclass(frozen=True)
class TakePrize:
    """きぜつさせたとき、サイドから表を見ないで 1 枚選んで取る（p.312, p.323）。``index`` はサイドの位置。"""

    player: int
    index: int


@dataclass(frozen=True)
class PromoteActive:
    """バトル場のポケモンがいなくなったとき、ベンチのポケモンをバトル場に出す（p.313, p.323）。"""

    player: int
    pokemon: int


# --- ルールにはあるが v0.1 では対応していない操作。受け取ると UnsupportedError を投げる ---


@dataclass(frozen=True)
class EvolvePokemon:
    player: int
    card: int
    target: int


@dataclass(frozen=True)
class PlayTrainer:
    player: int
    card: int


@dataclass(frozen=True)
class UsePokemonPower:
    player: int
    pokemon: int


COMMAND_TYPES: dict[str, type] = {
    "place_starting_pokemon": PlaceStartingPokemon,
    "draw_mulligan_cards": DrawMulliganCards,
    "report_janken_result": ReportJankenResult,
    "play_basic_to_bench": PlayBasicToBench,
    "attach_energy": AttachEnergy,
    "retreat": Retreat,
    "use_attack": UseAttack,
    "end_turn": EndTurn,
    "take_prize": TakePrize,
    "promote_active": PromoteActive,
    "evolve_pokemon": EvolvePokemon,
    "play_trainer": PlayTrainer,
    "use_pokemon_power": UsePokemonPower,
}

UNSUPPORTED_COMMANDS = (EvolvePokemon, PlayTrainer, UsePokemonPower)

_TYPE_NAMES = {cls: name for name, cls in COMMAND_TYPES.items()}

Command = (
    PlaceStartingPokemon
    | DrawMulliganCards
    | ReportJankenResult
    | PlayBasicToBench
    | AttachEnergy
    | Retreat
    | UseAttack
    | EndTurn
    | TakePrize
    | PromoteActive
    | EvolvePokemon
    | PlayTrainer
    | UsePokemonPower
)


def check_command_fields(command) -> None:
    """コマンドの各項目が整数（uid・プレイヤー・番号）か、整数のタプルかを確かめる。

    JSON から来た値で、bool（True は 1 と等しい）や文字列が uid として通らないようにする。
    """
    for f in fields(command):
        value = getattr(command, f.name)
        if f.type == "int":
            ok = type(value) is int
        else:  # "tuple[int, ...]"
            ok = isinstance(value, tuple) and all(type(v) is int for v in value)
        if not ok:
            raise IllegalActionError("BAD_COMMAND", f"{type(command).__name__}.{f.name} の値 {value!r} が {f.type} ではない")


def command_to_dict(command) -> dict:
    data = asdict(command)
    for key, value in data.items():
        if isinstance(value, tuple):
            data[key] = list(value)
    return {"type": _TYPE_NAMES[type(command)], **data}


def command_from_dict(data: dict):
    data = dict(data)
    name = data.pop("type", None)
    cls = COMMAND_TYPES.get(name)
    if cls is None:
        raise IllegalActionError("UNKNOWN_COMMAND", f"知らないコマンドの種類 {name!r}")
    names = {f.name for f in fields(cls)}
    required = {f.name for f in fields(cls) if f.default is MISSING and f.default_factory is MISSING}
    missing = sorted(required - set(data))
    extra = sorted(set(data) - names)
    if missing or extra:
        raise IllegalActionError("BAD_COMMAND", f"{name}: 足りない項目 {missing}、余分な項目 {extra}")
    return cls(**{key: tuple(value) if isinstance(value, list) else value for key, value in data.items()})

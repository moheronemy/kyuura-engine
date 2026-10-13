"""プレイヤーの操作（コマンド）。

コマンドは「何をしたいか」だけを持つ値で、検査と処理は ``engine.apply_command`` が行います。
カードやポケモンは uid（``GameState.cards`` の番号）で指定します。場のポケモンは、
そのポケモンのカード（いちばん上のカード）の uid で指定します。v0.4a の ``EvolvePokemon`` と v0.5 の
``UsePokemonPower`` は、場のポケモンを場のポケモンの番号（``pokemon_id``）で指定します。

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


@dataclass(frozen=True)
class ResolveDecision:
    """保留中の決定（``GameState.decision``）に答える（v0.2a）。

    ``decision`` は答える決定の番号（``PendingDecision.id``）、``choices`` は選んだもの
    （``PendingDecision.options`` の中から、``min_choices``〜``max_choices`` 個。重ねない）。
    どの種類の決定にも使える。サイドを取る決定には ``TakePrize``、バトル場に出す決定には
    ``PromoteActive`` も使える（v0.1 からある形。ポケモンはカードの uid で指す）。
    """

    player: int
    decision: int
    choices: tuple[int, ...]


@dataclass(frozen=True)
class PlayTrainer:
    """手札のトレーナーカードを使う（p.310。v0.2b）。``card`` はトレーナーカードの uid。

    使えるのは、効果の登録表に実装が登録されたトレーナーだけ（``EffectRegistry.trainer_effect``）。
    効果の途中で対象を選ぶカードは、決定（``GameState.decision``）を出す。``ResolveDecision`` で答えると
    続きを処理し、使い終わったカードをトラッシュして、番の続きにもどる。
    """

    player: int
    card: int


@dataclass(frozen=True)
class EvolvePokemon:
    """手札の進化カードを、自分の場のポケモンに重ねて進化させる（p.309・p.310。v0.4a）。

    - ``card``: 手札の進化カードの uid（v0.4a は 1 進化ポケモンのカード。v0.4c から 2 進化ポケモンのカードも。同じコマンド）
    - ``target``: 進化させる自分の場のポケモンの番号（``PokemonInPlay.pokemon_id``）。カードの uid ではない
      （v0.1 からのコマンドは場のポケモンをカードの uid で指すが、このコマンドは v0.4a で初めて受け付けるので、
      場のポケモンの番号で指す。進化するといちばん上のカードの uid が変わるため）
    """

    player: int
    card: int
    target: int


@dataclass(frozen=True)
class UsePokemonPower:
    """自分の場のポケモンの特殊能力（ポケモンパワー）の使用を宣言し、その説明にしたがって処理する（p.311「ポケモンの
    特殊能力を使う」・p.323「14 ポケモンの特殊能力」。v0.5）。

    - ``pokemon``: 特殊能力を使う自分の場のポケモンの番号（``PokemonInPlay.pokemon_id``）。カードの uid ではない（v0.1 から
      あるコマンドだが、v0.4e までは受け付けなかった（``UNSUPPORTED_ACTION``）ので、v0.4a の ``EvolvePokemon`` と同じく場の
      ポケモンの番号で指す）。バトル場でもベンチでもよい（p.311「特に指示されていないかぎり、ベンチにいるポケモンも特殊能力を
      使うことができます」）
    - ``power``: 特殊能力の位置（カードに印刷された順、0 から）。v0.5 の対応カード（フシギバナ）は特殊能力が 1 つなので 0
    - ``energy``・``source``・``target``: 特殊能力の説明が選ばせるもの。v0.5 の「エナジートランス」は、移す「草」エネルギー
      カードの uid（``energy``）、それがついている自分の場のポケモンの番号（``source``）、つけかえる先の自分の場の別のポケモンの
      番号（``target``）。1 回の使用で 1 枚をつけかえる（実装上の仮定。docs/energy-transfer-v0.5.md）。使わない特殊能力では
      None のまま

    v0.4e までの 2 つの項目（``player``・``pokemon``）だけの形（``command_from_dict`` の辞書）も読める（ほかの項目は既定の値）。
    説明が選ばせるものが足りなければ、状態を変えずに拒否する。
    """

    player: int
    pokemon: int
    power: int = 0
    energy: int | None = None
    source: int | None = None
    target: int | None = None


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
    "resolve_decision": ResolveDecision,
    "evolve_pokemon": EvolvePokemon,
    "play_trainer": PlayTrainer,
    "use_pokemon_power": UsePokemonPower,
}

# ルールにはあるが、まだ対応していない操作（受け取ると UnsupportedError）。EvolvePokemon は v0.4a、UsePokemonPower は v0.5 で対応した
UNSUPPORTED_COMMANDS: tuple[type, ...] = ()

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
    | ResolveDecision
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
        elif f.type == "int | None":  # v0.5（UsePokemonPower の選ばせるもの。使わない特殊能力では None）
            ok = value is None or type(value) is int
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
    cls = COMMAND_TYPES.get(name) if isinstance(name, str) else None
    if cls is None:
        raise IllegalActionError("UNKNOWN_COMMAND", f"知らないコマンドの種類 {name!r}")
    names = {f.name for f in fields(cls)}
    required = {f.name for f in fields(cls) if f.default is MISSING and f.default_factory is MISSING}
    missing = sorted(required - set(data))
    extra = sorted(set(data) - names)
    if missing or extra:
        raise IllegalActionError("BAD_COMMAND", f"{name}: 足りない項目 {missing}、余分な項目 {extra}")
    return cls(**{key: tuple(value) if isinstance(value, list) else value for key, value in data.items()})

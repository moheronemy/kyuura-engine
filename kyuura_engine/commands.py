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
    """手札のエネルギーカードを自分の場のポケモンにつける（p.310）。

    v0.59（docs/energy-control-power-suppression-v0.59.md 4 章）: ``energy2`` は、トレーナー「カツラ」の効果（この番だけ、手札から「カツラのポケモン」につける「炎」
    エネルギーカードの枚数を 1 枚でなく 2 枚にする）で、同じ 1 回の操作でいっしょにつける 2 枚目の「炎」エネルギーカード。None（既定。v0.58 までの形）なら 1 枚。"""

    player: int
    energy: int
    target: int
    energy2: int | None = None


@dataclass(frozen=True)
class Retreat:
    """バトル場のポケモンをにがす。トラッシュするエネルギーと、入れ替える控えを選ぶ（pp.310-311）。"""

    player: int
    discard: tuple[int, ...]
    new_active: int


@dataclass(frozen=True)
class UseAttack:
    """バトル場のポケモンのワザを使う（p.309）。``attack_index`` はカードのワザの順番（0 から）。

    v0.49（docs/virtual-attacks-transformation-v0.49.md 2 章）: ``card`` は、そのワザを印刷したカードの uid（ワザの出どころ）。None（既定。v0.48 までの形）なら、
    バトル場のポケモンの今の姿のカード（ふつうはいちばん上のカード。メタモンの［へんしん］なら相手の対戦ポケモンのカード、タケシのキュウコンの「ばける」なら
    のせた進化カード）。ナツメのフーディンの［サイコリンク］で持つワザは、そのワザを持つ自分の場の「超」ポケモンの今の姿のカード、「思い出させる」で使う進化前の
    ワザは、重なっている進化前のカードを指す（``effects.available_attacks`` の ``card``）。ワザの名前・一覧の位置では指さない（同じ名前のワザ・一覧の変化で
    取りちがえないため）。
    """

    player: int
    attack_index: int
    card: int | None = None
    # v0.57（docs/stadiums-v0.57.md 6 章）: クチバシティジムの「お互いのプレイヤーは、のぞむなら、自分の番で「マチスのポケモン」がワザを使う時、コインを投げてもよい」を
    # 選ぶか（ワザの宣言といっしょに選ぶ）。False（既定。v0.56 までの形。辞書には書かない）なら投げない。場にクチバシティジムがない・ワザを使うのが「マチスのポケモン」
    # でないのに True なら、状態を変えずに ``STADIUM_COIN_NOT_AVAILABLE``
    stadium_coin: bool = False
    # v0.88（docs/type-energy-colors-v0.88.md 5.1 節）: ワザといっしょに使える特殊能力（ランターン neo1-040 の［すいりょくはつでん］の「この力は、このカードが「まぶしいひかり」を
    # 使うとき、使える」）を使うか（ワザの宣言といっしょに選ぶ）。False（既定。v0.87 までの形。辞書には書かない）なら使わない。ワザを使うポケモンがそのワザといっしょに使える
    # 特殊能力を持たない・使えない状態なら、状態を変えずに拒否する
    attack_power: bool = False
    # v0.118（docs/unbounded-coins-heal-allocation-v0.118.md 5 章）: ワザといっしょに使う、自分の場のポケモンの特殊能力（アンノーンX neo4-065 の［XXXXX］の「この力は、自分の場の「アンノーン」が
    # 「めざめるパワー」を使うとき、使うことができる」）を持つポケモンの場の番号（ワザを使うポケモン自身でもよい）。None（既定。v0.117 までの形。辞書には書かない）なら使わない。
    # ``attack_power``（ワザを使うポケモン自身の［すいりょくはつでん］）とは別の項目。使えない・使えない状態なら、状態を変えずに拒否する
    with_power: int | None = None
    # v0.122（docs/unown-fossil-retreat-reactions-v0.122.md 3 章）: ワザといっしょに使う、自分の場のポケモンの特殊能力を 2 つ以上いっしょに指すときの、持つポケモンの場の番号の並び
    # （アンノーンA の［ANGER］とアンノーンX の［XXXXX］を同じ「めざめるパワー」で使う）。空（既定。v0.121 までの形。辞書には書かない）なら ``with_power`` のとおり。``with_power`` との併記・
    # 同じ番号の重なりは、状態を変えずに拒否する（``effects.declared_power_holders``）。並びの順に宣言し、確かめる
    with_powers: tuple[int, ...] = ()


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
    v0.129: 値で答える決定（``decisions.VALUE_RANGE``。カツラのクイズ その1の身長）は、``choices`` に範囲の整数 1 つ（身長は整数 cm）。単位の換算は
    呼ぶ側の責任（人向けの入力は ``heights.height_answer_cm``）。
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
      番号（``target``）。1 回の使用で 1 枚をつけかえる（実装上の仮定。docs/energy-transfer-v0.5.md）。v0.6 の「あまごい」は、
      つける自分の手札の「水」エネルギーカードの uid（``energy``）と、つける先の自分の場の「水」ポケモンの番号（``target``）で、
      ``source`` は使わない（None。指定したら ``POWER_CHOICE_NOT_USED``）。1 回の使用で 1 枚をつける（実装上の仮定。
      docs/rain-dance-v0.6.md の R3）。使わない特殊能力では None のまま。項目の意味はパワーごとに決まり、パワーの実装
      （``PowerEffect.check_usable``）が確かめる

    v0.4e までの 2 つの項目（``player``・``pokemon``）だけの形（``command_from_dict`` の辞書）も読める（ほかの項目は既定の値）。
    説明が選ばせるものが足りなければ、状態を変えずに拒否する。
    """

    player: int
    pokemon: int
    power: int = 0
    energy: int | None = None
    source: int | None = None
    target: int | None = None
    # v0.49: その特殊能力を印刷したカードの uid。None（既定。v0.48 までの形）なら今の姿のカード（ふつうはいちばん上のカード。「ばける」ならのせた進化カード、
    # メタモンの［へんしん］なら相手の対戦ポケモンのカード（写した特殊能力を使えるかは決まらない。TF1））。「ばける」でのせたカードの下のタケシのキュウコンの
    # 「ばける」は、そのカードの uid で指す
    card: int | None = None


@dataclass(frozen=True)
class RemoveDisguise:
    """タケシのキュウコンの「ばける」の「自分の番に、このカードの上にのっている「進化カード」をトラッシュして、このカードを「タケシのキュウコン」にもどしてもよい。」
    （v0.49。docs/virtual-attacks-transformation-v0.49.md 4 章）。

    - ``pokemon``: のせた進化カードをトラッシュする自分の場のポケモンの番号。バトル場でもベンチでもよい
    - 自分の番（``Phase.MAIN``）だけ。説明が許す操作で、特殊能力の使用の宣言（回数の制限のある「ばける」の使用）ではない。トレーナーカードを使うことでもない
    """

    player: int
    pokemon: int


@dataclass(frozen=True)
class DiscardFromPlay:
    """自分の場のポケモンとして出したなにかの化石・ピッピ人形（進化カードがのっていないもの）を、自分の番の好きなときにトラッシュにすてる（v0.47。カードの文面
    「自分の番の好きなときに（自分のトラッシュに）すてることができる」。docs/fossil-hidden-info-v0.47.md 2 章）。

    - ``pokemon``: すてる自分の場のポケモンの番号（``PokemonInPlay.pokemon_id``）。バトル場でもベンチでもよい
    - ついているカードもいっしょにトラッシュする。きぜつではない（相手はサイドを取らない）。トレーナーカードを使うことでも、特殊能力でもない（宣言しない。
      トレーナーの使用の禁止・かがくへんかガスは関係しない）
    - バトル場が空いたら、勝ち負けの判定（場にポケモンがいない）・バトル場に出す決定のあと、自分の番にもどる
    """

    player: int
    pokemon: int


@dataclass(frozen=True)
class UseStadium:
    """場のスタジアムカードの、自分の番に使ってよい効果を使う（v0.57。docs/stadiums-v0.57.md 4 章）。スタジアムはお互いのプレイヤーの場に出ているカードとして扱うので、
    カードの持ち主でないプレイヤーも、自分の番に使ってよい（印刷の文面「お互いのプレイヤーは、…自分の番…」）。トレーナーカードを手札から使うこと・特殊能力の使用では
    ない（コマンドを分ける）。

    - ``energy``: 説明が選ばせるエネルギーカードの uid（タマムシシティジム: 自分の「エリカのポケモン」についている、トラッシュするエネルギーカード。ヤマブキシティ
      ジム: 自分の「ナツメのポケモン」についている、手札に加える基本エネルギーカード）。カードを指せばポケモンも決まる。選ばせない効果（セキチクシティジム。コインのあと
      決定でポケモンを選ぶ）は None（指定したら ``STADIUM_CHOICE_NOT_USED``）
    - 自分の番（``Phase.MAIN``）だけ。場のスタジアムに、自分の番に使ってよい効果がなければ ``STADIUM_NOT_USABLE``
    """

    player: int
    energy: int | None = None


@dataclass(frozen=True)
class RevealFaceDown:
    """うらにしてベンチに出したカード（マチスの秘策）を、自分の番におもてにする（v0.67。「のぞむなら、あなたの番の中で、あなたはいつでもそのカードをおもてにしてよい」。
    docs/secret-plan-preflight-v0.67.md 4 章）。

    - ``pokemon``: おもてにする自分の場のポケモンの番号（バトル場でもベンチでもよい）
    - 自分の番（``Phase.MAIN``）だけ。決定を待っているあいだ・ほかの処理の途中では使えない（「いつでも」は、ほかの処理に割りこむことではない。実装上の読み方）。
      トレーナーカードの使用・特殊能力の使用ではない（使用の禁止・かがくへんかガスは関係しない）
    - おもてにしたカードが「たねポケモン」でなければ、ついているすべてのカードといっしょにトラッシュする（きぜつではない）。バトル場が空いたら、勝ち負けの判定・
      バトル場に出す決定のあと、自分の番にもどる
    """

    player: int
    pokemon: int


@dataclass(frozen=True)
class CheckFaceUpDeckCard:
    """おもてを上にした山札（フラッシュ）の、上から ``position`` 番目（0 がいちばん上）のおもてのカードを確かめたい、という要求（v0.126。docs/flash-faceup-deck-v0.126.md 4 章）。

    原典が新しい自由行動を定めたのではない。いちばん上より下のおもてのカードを新しく知ろうとする操作を、通常のコマンドとして識別して止めるための、実装上の最小限の入口:

    - いちばん上（``position`` 0）のおもてのカードは、いつも観測（``face_up_top``）に出ている（CR-FLASH-TOP-CARD-SEEN）。要求は要らない（``ALREADY_VISIBLE``）
    - 山札の持ち主は、自分で並べたおもてのカードを知っている（観測の ``known_face_up``）。要求は要らない（``ALREADY_KNOWN``）
    - その位置のカードがおもてでない・ないなら ``NOT_FACE_UP``（p.312。特に指示されないかぎり山札の内容を見ない）
    - それ以外（相手の山札の 2 枚目より下のおもてのカード）は、確かめてよいかが決まらないので ``UNRESOLVED_FACE_UP_DECK_CHECK``（FU2。UQ-FLASH-FACE-UP-DECK）で止める。どの場合も
      状態・乱数・ログを変えず、カードの中身を返さない（止める理由の文にもカードを書かない）
    """

    player: int
    owner: int
    position: int


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
    "discard_from_play": DiscardFromPlay,
    "remove_disguise": RemoveDisguise,  # v0.49
    "use_stadium": UseStadium,  # v0.57
    "reveal_face_down": RevealFaceDown,  # v0.67
    "check_face_up_deck_card": CheckFaceUpDeckCard,  # v0.126
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
    | DiscardFromPlay
    | RemoveDisguise
    | UseStadium
    | RevealFaceDown
    | CheckFaceUpDeckCard
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
        elif f.type == "bool":  # v0.57（UseAttack.stadium_coin）
            ok = type(value) is bool
        else:  # "tuple[int, ...]"
            ok = isinstance(value, tuple) and all(type(v) is int for v in value)
        if not ok:
            raise IllegalActionError("BAD_COMMAND", f"{type(command).__name__}.{f.name} の値 {value!r} が {f.type} ではない")


# v0.49: v0.48 までの形を変えないため、既定の値（None）のときは辞書に書かない項目（``UseAttack.card``・``UsePokemonPower.card``）
_OMITTED_WHEN_NONE: dict[type, tuple[str, ...]] = {UseAttack: ("card", "with_power"), UsePokemonPower: ("card",), AttachEnergy: ("energy2",)}  # v0.59: AttachEnergy.energy2。v0.118: with_power
# v0.57: 同じく、既定の値（False）のときは辞書に書かない項目（``UseAttack.stadium_coin``。v0.56 までの形を変えない）
_OMITTED_WHEN_FALSE: dict[type, tuple[str, ...]] = {UseAttack: ("stadium_coin", "attack_power")}  # v0.88: attack_power
# v0.122: 同じく、既定の値（空のタプル）のときは辞書に書かない項目（``UseAttack.with_powers``。v0.121 までの形を変えない）
_OMITTED_WHEN_EMPTY: dict[type, tuple[str, ...]] = {UseAttack: ("with_powers",)}


def command_to_dict(command) -> dict:
    data = asdict(command)
    for name in _OMITTED_WHEN_NONE.get(type(command), ()):
        if data[name] is None:
            del data[name]
    for name in _OMITTED_WHEN_FALSE.get(type(command), ()):
        if data[name] is False:
            del data[name]
    for name in _OMITTED_WHEN_EMPTY.get(type(command), ()):
        if data[name] == ():
            del data[name]
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

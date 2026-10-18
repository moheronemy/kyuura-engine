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
from typing import TYPE_CHECKING, Any, ClassVar, Mapping

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
class Asleep:
    """ねむり状態（v0.3b。p.322「2. ねむり状態」）。ワザを使えず、にげるを宣言できない。ポケモンチェックの
    たびに持ち主がコインを投げ、「おもて」なら回復する（p.322・p.323 の 3）。持つ情報はない。"""

    name: ClassVar[str] = "sleep"


@dataclass(frozen=True)
class Paralyzed:
    """マヒ状態（v0.3b。p.322「3. マヒ状態」）。ワザを使えず、にげるを宣言できない。

    - ``turn``: マヒ状態になった番（``GameState.turn_number``）。マヒは「マヒ状態になった番の「次の自分（そのポケモンの
      持ち主）の番」の終わりのポケモンチェックで自動的に回復」する（p.323 の 4・p.322）ので、回復する番を決めるのに
      要る（``conditions.paralysis_recovery_turn``）。番の数だけで決めず、持ち主の番を数える。
    """

    turn: int
    name: ClassVar[str] = "paralysis"


@dataclass(frozen=True)
class Confused:
    """こんらん状態（v0.3c。p.322「4. こんらん状態」）。持つ情報はない。

    - ワザを使うとき、持ち主がコインを投げ、「うら」ならワザがこんらんする（もとのワザの内容に関わらず、ワザを使った
      ポケモン自身に 20 ダメージ。「弱点・抵抗力」の影響を受ける。p.309 の手順 5・p.322）。
    - 「にげる」をおこなうとき、エネルギーをトラッシュしてからコインを投げ、「うら」なら「にげる」は失敗（p.311 の手順 3）。
    - 自然に回復しない（p.322）。ポケモンチェックですることはない（p.323）。
    """

    name: ClassVar[str] = "confusion"


@dataclass(frozen=True)
class SpecialConditions:
    """場のポケモンの特殊状態（v0.3a）。物理的なカードではないので、カードの uid ではなく、場のポケモン
    （``PokemonInPlay``。番号は ``pokemon_id``）が持つ。

    p.322 の規定にしたがって分けて持つ:

    - ``poison``: どく状態（``Poison``）か None。どく状態は、ほかの特殊状態と重複する（p.322「特殊状態の重複」）。
    - ``exclusive``: ねむり（``Asleep``）・マヒ（``Paralyzed``）・こんらん（``Confused``。v0.3c）のどれか 1 つか None
      （v0.3b）。ねむり・マヒ・こんらんは「重複することはありません」（p.322）ので 1 つの項目に持つ。

    特殊状態になるのはバトル場のポケモンだけ（p.322）。バトル場をはなれたら（ベンチに戻ったら）すべて
    消える（p.311・p.322）。進化しても消える（p.310 の進化の手順 3・p.322。v0.4a）。
    """

    poison: Poison | None = None
    exclusive: Asleep | Paralyzed | Confused | None = None

    def names(self) -> tuple[str, ...]:
        """今かかっている特殊状態の名前（ログ・書き出し用。p.322 の順: どく・ねむり・マヒ・こんらん）。"""
        names = ("poison",) if self.poison is not None else ()
        return names + ((self.exclusive.name,) if self.exclusive is not None else ())

    @property
    def asleep(self) -> bool:
        return isinstance(self.exclusive, Asleep)

    @property
    def paralyzed(self) -> bool:
        return isinstance(self.exclusive, Paralyzed)

    @property
    def confused(self) -> bool:
        return isinstance(self.exclusive, Confused)


def _check_attack_card(card_id: Any) -> None:
    """v0.49: 持続する効果の「ワザを印刷したカードの id」（``attack_card``・``target_attack_card``）は空でない文字列か None。"""
    if card_id is not None and (type(card_id) is not str or not card_id):
        raise ValueError(f"ワザを印刷したカードの id は空でない文字列か None（{card_id!r}）")


@dataclass(frozen=True)
class PreventDamage:
    """ワザによる「持続する効果」（v0.4b。p.322「11 特殊状態以外の「持続する効果」」）のうち、「次の相手の番、このカードは
    ダメージを受けない。（ダメージ以外の効果は受ける）」（トランセル・コクーンの「かたまる」の最新の説明。p.18・p.21）。

    特殊状態（``SpecialConditions``）でも、ついているトレーナーカード（``AttachedTrainer``）でもない。物理的なカードではない
    ので、カードの uid を持たず、効果を受けている場のポケモン（``PokemonInPlay.persistent_effects``）が持つ。

    - ``source_card``: 効果を与えたワザを使ったポケモンのカード（いちばん上のカードの uid）。「かたまる」は自分自身に与える
      （p.236 のワザ解説「効果の対象：ワザを使ったポケモン自身」）ので、効果を受けているポケモンのカードと同じ
    - ``source_player``: 効果を与えたプレイヤー
    - ``created_turn``: ワザを使った番（``GameState.turn_number``）
    - ``active_turn``: 効果がはたらく番（「次の相手の番」= ``created_turn + 1``。番は先攻から交互に進む）。この番の間、
      このポケモンは「ダメージを受けない」状態（p.321: このポケモンにダメージを与えるワザの要素は無効、ダメージ以外の
      効果のワザの要素は有効）。この番の終わりに消える（p.236・p.18 のワザ解説「効果の持続：次の相手の番の最後」）。
      ポケモンチェックはどちらの番でもないので、どくのダメージは防がない（p.323）

    ベンチに戻ったら（p.311・p.322）・場をはなれたら（p.322）・進化したら（p.310・p.323）消える。一度消えたら復活しない
    （p.322）。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    kind: ClassVar[str] = "prevent_damage"
    turns_until_active: ClassVar[int] = 1  # はたらく番は効果を与えた番の何番あとか（v0.27。次の相手の番）
    on_opponent: ClassVar[bool] = False  # 相手に与える効果か（v0.31。v0.30 までの効果はどれも自分自身）


# Retaliation の与えるダメージの決め方（v0.13）。名前は書き出し・ログに出る種類（kind）と対応する
RETALIATION_FIXED = "fixed"  # 決まった量（v0.12 の「ほのおのかべ」の 10）
RETALIATION_RECEIVED = "received_damage"  # 受けたダメージと同じ（v0.13 の「こうらがえし」）
RETALIATION_KINDS = {RETALIATION_FIXED: "retaliation", RETALIATION_RECEIVED: "retaliation_received_damage"}
# v0.45: 受けたダメージで決まり、倍数（``multiplier``）か、はたらくときのコイン（``on_heads``）のある効果の種類（R団のエビワラーの「クロスカウンター」。
# 「こうらがえし」と同じ決め方 ``RETALIATION_RECEIVED`` に、量の倍数とコインの条件を明示した値。v0.44 までの読み手は知らない種類として拒否する）
RETALIATION_RECEIVED_SCALED_KIND = "retaliation_received_damage_scaled"


@dataclass(frozen=True)
class Retaliation:
    """ワザによる「持続する効果」（v0.12。p.322「11 特殊状態以外の「持続する効果」」）のうち、「次の相手の番、このカードが相手のワザに
    よるダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）相手に10ダメージを与える。」（R団のファイヤーの「ほのおのかべ」
    の最新の説明。p.82。docs/rocket-moltres-v0.12.md・docs/temporary-attack-effects-v0.12.md）。v0.13 で、与えるダメージを受けたダメージで
    決める「こうらがえし」（わるいカメール。p.89）も同じ型で表す（``basis``）。

    p.89 のワザ解説（わるいカメールの「こうらがえし」）の「相手の番ではたらく効果」と同じ形: 効果の対象はワザを使ったポケモン自身、
    効果の持続は次の相手の番の最後、ベンチにもどると消える。``PreventDamage`` と同じく、特殊状態でもついているトレーナーカードでも
    ない（物理的なカードではない）ので、効果を受けている場のポケモン（``PokemonInPlay.persistent_effects``）が持つ。

    - ``source_card``・``source_player``・``created_turn``・``active_turn``: ``PreventDamage`` と同じ（自分自身に与えるので、
      ``source_card`` は効果を受けているポケモンのカード。``active_turn`` は ``created_turn + 1``。この番の終わりに消える）
    - ``attack_index``: 効果を与えたワザの位置（``source_card`` のカードの。ダメージを与えるときのワザ ``AttackKey`` になる。
      与えるダメージは「ワザによるダメージ」（p.321「8」・p.89）で、ワザを使ったポケモンはこのポケモン）
    - ``amount``: 与えるダメージの基本となるダメージ（10。p.321 の 1 段階。弱点・抵抗力などは p.321 の順番で計算する。p.82 の解説）。
      ``basis`` が ``RETALIATION_RECEIVED`` なら None（受けたダメージで決まるので、効果を与えたときには決まっていない）
    - ``basis``（v0.13）: 与えるダメージの基本となるダメージの決め方。``RETALIATION_FIXED``（既定。「ほのおのかべ」。``amount``）か
      ``RETALIATION_RECEIVED``（わるいカメールの「こうらがえし」の最新の説明（p.89）「次の相手の番、このカードが相手のワザによって
      ダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）そのポケモンにも同じダメージを与える。（ダメージ以外の効果は
      与えない）」。受けたダメージ（p.321 で計算した最終ダメージ。HP で上限をつけない）。docs/shell-attack-v0.13.md・
      docs/variable-retaliation-v0.13.md）。受けたダメージはワザ 1 回の中の値（解決の基盤の ``kernel.Deferred.received``）で、状態に
      持たない
    - ``multiplier``・``on_heads``（v0.45）: ``RETALIATION_RECEIVED`` の効果で、与えるダメージの基本となるダメージを受けたダメージの何倍にするか（既定 1）と、
      はたらくときにコインを投げて「おもて」のときだけ与えるか（既定 False）。R団のエビワラーの「クロスカウンター」の最新の説明（LD-PMCG5-054-ATK0）
      「次の相手の番、このカードが相手のワザによるダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）コインを投げる。「おもて」なら、
      このカードが受けたダメージの2倍のダメージを、相手に与える。」は 2・True（docs/conditional-damage-energy-v0.45.md）。コインは効果を与えるときではなく、
      はたらくとき（``kernel.attack_damage_to_damage_source``）に投げる。どちらも既定の値なら v0.13 の「こうらがえし」と同じ種類・書き出し

    はたらくのは ``active_turn`` の間に、このポケモンが相手のワザによるダメージ（最終ダメージが 0 より大きい）を受けたとき
    （``effects.deal_attack_damage`` が記録し、``effects.finish_damage_elements`` が与える）。ベンチに戻ったら（p.311・p.322）・場を
    はなれたら（p.322）・進化したら（p.310・p.323）消え、一度消えたら復活しない（p.322）。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    attack_index: int
    amount: int | None
    basis: str = RETALIATION_FIXED
    multiplier: int = 1  # v0.45: 受けたダメージの何倍を与えるか（クロスカウンターは 2）
    on_heads: bool = False  # v0.45: はたらくときにコインを投げ、「おもて」のときだけ与える（クロスカウンター）
    # v0.49（docs/virtual-attacks-transformation-v0.49.md 3 章）: 効果を与えたワザを印刷したカードの id（``attack_index`` はこのカードのワザの位置）。None なら
    # ``source_card`` のカード（v0.48 までと同じ）。ワザの出どころがいちばん上のカードでないとき（へんしん・ばける・サイコリンク・思い出させる）だけ書く
    attack_card: str | None = None
    turns_until_active: ClassVar[int] = 1  # はたらく番は効果を与えた番の何番あとか（v0.27。次の相手の番）
    on_opponent: ClassVar[bool] = False  # 相手に与える効果か（v0.31。v0.30 までの効果はどれも自分自身）

    def __post_init__(self) -> None:
        _check_attack_card(self.attack_card)
        if type(self.multiplier) is not int or self.multiplier < 1 or type(self.on_heads) is not bool:
            raise ValueError(f"倍数は 1 以上の整数、コインの条件は真偽値（{self.multiplier!r}・{self.on_heads!r}）")
        if self.basis == RETALIATION_FIXED:
            if type(self.amount) is not int:
                raise ValueError(f"決まった量の効果には amount が要る（{self.amount!r}）")
            if self.multiplier != 1 or self.on_heads:
                raise ValueError("決まった量の効果に倍数・コインの条件は書かない（v0.45 の倍数・コインは受けたダメージで決まる効果だけ）")
        elif self.basis == RETALIATION_RECEIVED:
            if self.amount is not None:
                raise ValueError(f"受けたダメージで決まる効果に amount は書かない（{self.amount!r}）")
        else:
            raise ValueError(f"知らない決め方 {self.basis!r}")

    @property
    def scaled(self) -> bool:
        """受けたダメージの倍数かコインの条件がある（v0.45。既定の値でない）か。"""
        return self.multiplier != 1 or self.on_heads

    @property
    def kind(self) -> str:
        """持続する効果の種類（ログ ``persistent_effect_added`` などの ``persistent_effect``・書き出しの ``effect``）。決まった量は
        v0.12 と同じ ``"retaliation"``、受けたダメージで決まるものは ``"retaliation_received_damage"``（v0.13。v0.12 の読み手は知らない
        種類として拒否する）。v0.45: 倍数・コインの条件のあるもの（クロスカウンター）は ``"retaliation_received_damage_scaled"``（v0.44 の読み手は
        知らない種類として拒否する）。"""
        if self.scaled:
            return RETALIATION_RECEIVED_SCALED_KIND
        return RETALIATION_KINDS[self.basis]

    def terms(self) -> tuple:
        """登録された実装の ``retaliation_terms()`` と比べる値（不変条件）。v0.44 までの効果は (決め方, 量)、倍数・コインの条件のあるもの（v0.45）は
        (決め方, 量, 倍数, コインの条件)。"""
        if self.scaled:
            return self.basis, self.amount, self.multiplier, self.on_heads
        return self.basis, self.amount

    def base_damage(self, received: int) -> int:
        """与えるダメージの基本となるダメージ（p.321 の 1 段階）。``received`` はこのポケモンが受けたダメージ（相手のワザによる最終ダメージ。
        0 より大きい）。決まった量なら ``amount``、受けたダメージで決まるなら ``received`` そのもの（p.89 の解説「100ダメージを受けたら
        そのまま100ダメージが返る」「2倍のまま相手にダメージが返ります」）。v0.45: 倍数があれば ``received`` × ``multiplier``（クロスカウンターの
        「受けたダメージの2倍のダメージ」。2 倍は与えるダメージの基本となるダメージで、弱点・抵抗力などはそのあとの段階で計算する）。コインの条件
        （``on_heads``）は、はたらくときに呼ぶ側が確かめる（「おもて」のときの量を返す）。"""
        if self.basis == RETALIATION_FIXED:
            return self.amount
        return received * self.multiplier


# v0.35: 次の自分の番のワザのダメージの変え方（``NextTurnAttackDamage.operation``。``damage.SET``・``damage.MULTIPLY`` と同じ値）と、それぞれの種類
NEXT_TURN_SET = "set"
NEXT_TURN_MULTIPLY = "multiply"
NEXT_TURN_DAMAGE_KINDS = {NEXT_TURN_SET: "next_turn_attack_damage", NEXT_TURN_MULTIPLY: "next_turn_attack_damage_multiplier"}


@dataclass(frozen=True)
class NextTurnAttackDamage:
    """ワザによる「持続する効果」（v0.27。p.322「11 特殊状態以外の「持続する効果」」）のうち、「次の自分の番、このカードが使う「きりさく」の
    ダメージは「60」になる。」（ストライクの「つるぎのまい」の最新の説明。p.56・p.321。docs/scyther-v0.27.md）。

    p.57 のワザ解説「次の自分の番でつかうワザのダメージを変更する効果」: 効果の対象はワザを使ったポケモン自身、効果は「自分の番、相手の番、
    自分の番と持続」し、効果の持続は次の自分の番の最後、ベンチにもどると消える（「突風」などで入れ替えられたときも）。``PreventDamage``・
    ``Retaliation`` と同じく、特殊状態でもついているトレーナーカードでもない（物理的なカードではない）ので、効果を受けている場のポケモン
    （``PokemonInPlay.persistent_effects``）が持つ。

    - ``source_card``・``source_player``・``created_turn``: ``PreventDamage`` と同じ（自分自身に与えるので、``source_card`` は効果を受けて
      いるポケモンのカード）
    - ``active_turn``: 効果がはたらく番（「次の自分の番」= ``created_turn + 2``。番は先攻から交互に進む）。この番の終わりに消える（p.57
      「効果の持続：次の自分の番の最後」）。あいだの相手の番には何もしない
    - ``attack_index``: 効果を与えたワザ（「つるぎのまい」）の位置（``source_card`` のカードの）
    - ``target_attack_index``: ダメージが変わるワザ（「きりさく」）の位置（同じカードの）。ワザの名前ではなく位置で持つ（ほかのポケモンの
      同じ名前のワザ・このカードのほかのワザは変えない）
    - ``amount``: そのワザのダメージを、p.321 の 2 段階（「ワザを使うポケモンの持っている「ダメージを変更する効果」」）でこの数にする
      （「「60」になる」。足す数・掛ける数ではない。印刷の文面の「2倍」にはしたがわない）。v0.35 の ``operation`` が ``NEXT_TURN_MULTIPLY`` なら、
      その段階でダメージにかける数（「2倍」の 2）
    - ``operation``（v0.35）: ``NEXT_TURN_SET``（既定。「その数にする」。v0.27 の「つるぎのまい」）か ``NEXT_TURN_MULTIPLY``（「数をかける」。マチスの
      コラッタ・ラッタの「きあいだめ」の「…のダメージは2倍になる」）。``damage.DamageModifier`` の ``SET``・``MULTIPLY`` と同じ値。v0.13 の
      ``Retaliation`` の ``basis`` と同じく、決め方を明示した 1 つの型にする（別の型・ワザごとの処理にしない）。種類 ``kind`` は決め方から求める
      （``NEXT_TURN_DAMAGE_KINDS``。「その数にする」は v0.27 と同じ ``"next_turn_attack_damage"``、「数をかける」は ``"next_turn_attack_damage_multiplier"``。
      v0.34 までのエンジンは知らない種類として読まない）。クラスから ``NextTurnAttackDamage.kind`` を読まない
    - ``includes_self_damage``（v0.35）: そのワザの自分へのダメージにも当てはめるか（マチスのラッタの「きあいだめ」の「(自分へのダメージも2倍)」）。
      既定は False（相手へのダメージだけ。「つるぎのまい」の「きりさく」・「きあいだめ」の「でんこうせっか」には自分へのダメージがない）

    はたらくのは ``active_turn`` の間に、このポケモンが ``target_attack_index`` のワザでダメージを計算するとき（``effects.attack_damage_modifiers``）。
    ベンチに戻ったら（p.311・p.322・p.57）・場をはなれたら（p.322）・進化したら（p.310・p.323）消え、一度消えたら復活しない（p.322）。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    attack_index: int
    target_attack_index: int
    amount: int
    operation: str = "set"
    includes_self_damage: bool = False
    # v0.49: 効果を与えたワザ・ダメージが変わるワザを印刷したカードの id（どちらも同じカードのワザ）。None なら ``source_card`` のカード（v0.48 までと同じ）
    attack_card: str | None = None
    turns_until_active: ClassVar[int] = 2  # 次の自分の番
    on_opponent: ClassVar[bool] = False

    def __post_init__(self) -> None:
        _check_attack_card(self.attack_card)
        if self.operation not in NEXT_TURN_DAMAGE_KINDS:
            raise ValueError(f"次の自分の番のワザのダメージの変え方は {tuple(NEXT_TURN_DAMAGE_KINDS)} のどれか（{self.operation!r}）")
        if self.operation == NEXT_TURN_MULTIPLY and (type(self.amount) is not int or self.amount < 2):
            raise ValueError(f"ダメージにかける数は 2 以上の整数（{self.amount!r}）")
        if self.operation == NEXT_TURN_SET and self.includes_self_damage:
            # 自分へのダメージにも当てはめる「その数にする」効果のカードはない（v0.27 の種類 "next_turn_attack_damage" の書き出しは、この印を持たない）
            raise ValueError("「その数にする」効果（つるぎのまい）に、自分へのダメージにも当てはめる印はない")

    @property
    def kind(self) -> str:
        return NEXT_TURN_DAMAGE_KINDS[self.operation]


@dataclass(frozen=True)
class DestinyBond:
    """ワザによる「持続する効果」（v0.31）のうち、第1弾のゴース（PMCG1-044）の「みちづれ」の「次の相手の番で自分が「きぜつ」したときには、
    相手の対戦ポケモンも「きぜつ」する。」（kyuura の印刷の文面。docs/held-cards-v0.31.md）。

    ``PreventDamage`` と同じく自分自身に与え（``source_card`` は効果を受けているポケモンのカード）、はたらく番は次の相手の番（``created_turn + 1``）。
    その番の終わりに消える（ポケモンチェックはどちらの番でもない。p.323）。ベンチにもどる・進化する・きぜつで消える（p.311・p.322・p.323）。
    はたらく番に、このポケモンがワザのあとのきぜつの判定で HP 以上なら、相手の対戦ポケモンも「きぜつ」する（解決の基盤の ``flow._finish_attack``）。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    kind: ClassVar[str] = "destiny_bond"
    turns_until_active: ClassVar[int] = 1
    on_opponent: ClassVar[bool] = False


@dataclass(frozen=True)
class AttackBarrier:
    """ワザによる「持続する効果」（v0.31）のうち、ミュウツー（PMCG1-050）の「バリアー」の「次の相手の番の「ワザ」をうけない。」（kyuura の印刷の文面）。

    自分自身に与え、はたらく番は次の相手の番。その番に、このポケモンへのワザのダメージの要素と効果の要素は無効（「ワザをうけない」。ダメージだけ
    でなく効果も受けない。「かたまる」（``PreventDamage``）はダメージ以外の効果は受ける）。消える契機は ``PreventDamage`` と同じ。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    kind: ClassVar[str] = "attack_barrier"
    turns_until_active: ClassVar[int] = 1
    on_opponent: ClassVar[bool] = False


@dataclass(frozen=True)
class DamageReduction:
    """ワザによる「持続する効果」（v0.31）のうち、ピクシー（PMCG2-044）の「ちいさくなる」の「次の相手の番でこのカードが受けるダメージが20へる。」
    （kyuura の印刷の文面）。

    自分自身に与え、はたらく番は次の相手の番。その番に、このポケモンがワザのダメージを受けるとき、p.321 の 8 段階（「ワザを受けるポケモンの
    持っている「ダメージを変更する効果」」）で ``amount`` を減らす（``effects.attack_damage_modifiers``）。消える契機は ``PreventDamage`` と同じ。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    amount: int
    kind: ClassVar[str] = "damage_reduction"
    turns_until_active: ClassVar[int] = 1
    on_opponent: ClassVar[bool] = False


@dataclass(frozen=True)
class ZeroDamageBelow:
    """ワザによる「持続する効果」（v0.45）のうち、イワーク（PMCG1-054）の「かたくなる」の「次の相手の番に受けるダメージが0になる。ただしダメージが40以上の
    場合は、そのままダメージをうける。」（kyuura の印刷の文面）。

    自分自身に与え、はたらく番は次の相手の番。その番に、このポケモンがワザのダメージを受けるとき、p.321 の 8 段階（「ワザを受けるポケモンの持っている
    「ダメージを変更する効果」」。GR-2000-P321-DAMAGE-ORDER の 8 段階の例が「かたくなる」）で、その段階のダメージが ``threshold`` より小さければ 0 にし、
    ``threshold`` 以上ならそのまま（``damage.ZERO_IF_BELOW``。``effects.attack_damage_modifiers``）。計算の結果が 0 なら「ダメージを受けなかった」（p.321）
    ことになるだけで、「ダメージを受けない」状態（``PreventDamage``。ダメージの要素が計算の前に無効）ではない。ダメージ以外の効果は受ける。消える契機は
    ``PreventDamage`` と同じ（期限・ベンチ・進化・きぜつ）。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    threshold: int
    kind: ClassVar[str] = "zero_damage_below"
    turns_until_active: ClassVar[int] = 1
    on_opponent: ClassVar[bool] = False


@dataclass(frozen=True)
class HalvedDamage:
    """ワザによる「持続する効果」（v0.46）のうち、エリカのタマタマ（PMCG5-012）の「リフレクター」の「次の相手の番、このカードが受けるダメージは半分(切りすて)
    になる。(ダメージ以外の効果はそのまま)」（kyuura の印刷の文面）。

    自分自身に与え、はたらく番は次の相手の番。その番に、このポケモンがワザのダメージを受けるとき、p.321 の 8 段階（「ワザを受けるポケモンの持っている「ダメージを
    変更する効果」」）で、その段階のダメージを半分にし、ダメージカウンターの単位で切りすてる（``damage.HALVE_DOWN``。``effects.attack_damage_modifiers``）。
    エリカのフシギソウの［くつろぐかおり］（常にはたらく特殊能力の「半分(切り上げ)」。``damage.HALVE_UP``）とは、はたらく条件・期限・丸めの向きが違い、半分にする
    計算（``DamageModifier.apply``）だけを共通にする。ダメージ以外の効果は受ける。消える契機は ``PreventDamage`` と同じ（期限・ベンチ・進化・きぜつ）。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    kind: ClassVar[str] = "halved_damage"
    turns_until_active: ClassVar[int] = 1
    on_opponent: ClassVar[bool] = False


@dataclass(frozen=True)
class CannotAttack:
    """ワザによる「持続する効果」（v0.31）のうち、イーブイ（PMCG2-037）の「しっぽをふる」の「「しっぽをふる」を受けた相手の対戦ポケモンは、
    次の相手の番にワザをつかえない。」（kyuura の印刷の文面）。

    相手に与える効果（``on_opponent``。v0.30 までの持続する効果はどれも自分自身に与えた）。効果を受けるのは相手の対戦ポケモンで、``source_card``・
    ``source_player`` は効果を与えたワザを使ったポケモンのカードとそのプレイヤー（受けているポケモンとは別）。はたらく番は次の相手の番（受けている
    ポケモンの持ち主の番。``created_turn + 1``）で、その番の間、受けているポケモンはワザを使えない（``checks.attack_request``）。消える契機は
    ほかの持続する効果と同じ（期限・ベンチにもどる・進化・きぜつ。p.311・p.322・p.323）。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    kind: ClassVar[str] = "cannot_attack"
    turns_until_active: ClassVar[int] = 1
    on_opponent: ClassVar[bool] = True


@dataclass(frozen=True)
class ReducedDamageToSource:
    """ワザによる「持続する効果」（v0.34）のうち、カラカラ（PMCG2-029）の「なきつく」の「「なきつく」を受けた相手は、このカードにワザを使う時、与える
    ダメージが20へる。この状態は次の自分の番の始めに消える。」（kyuura の印刷の文面）。

    相手に与える効果（``on_opponent``。``CannotAttack`` と同じ）。効果を受けるのは相手の対戦ポケモンで、``source_card``・``source_player`` は効果を
    与えたワザを使ったポケモン（「このカード」）のカードとそのプレイヤー。はたらく番は次の相手の番（``created_turn + 1``）で、その番に、受けている
    ポケモンが ``source_card`` のポケモンにワザでダメージを与えるとき、p.321 の 2 段階（「ワザを使うポケモンの持っている「ダメージを変更する効果」」）で
    ``amount`` を減らす（``effects.attack_damage_modifiers``）。

    消える契機: 期限は「次の自分の番の始め」（効果を与えたプレイヤーの次の番の最初。``expires_at_turn_start``。はたらく番の終わりではなく、そのあとの
    ポケモンチェックのあと。``persistent.remove_turn_start_expired_persistent_effects``）。ほかの契機（受けているポケモンがベンチにもどる・進化・きぜつ）は
    ほかの持続する効果と同じ（p.311・p.322・p.323）。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    amount: int
    kind: ClassVar[str] = "reduced_damage_to_source"
    turns_until_active: ClassVar[int] = 1
    on_opponent: ClassVar[bool] = True
    expires_at_turn_start: ClassVar[bool] = True


@dataclass(frozen=True)
class CannotUseOwnAttack:
    """ワザによる「持続する効果」（v0.35）のうち、カスミのニョロモ（PMCG5-022）の「あわあわ」の「コインを投げて「うら」なら、次の自分の番、このカードは
    「あわあわ」を使えない。」（kyuura の印刷の文面）。

    自分自身に与え（``source_card`` は効果を受けているポケモンのカード）、はたらく番は次の自分の番（``created_turn + 2``。``NextTurnAttackDamage`` と同じ）。
    その番の間、このポケモンは ``target_attack_index`` のワザ（いちばん上のカードの。ワザの名前では探さない）を使えない（``checks.attack_request``）。
    ほかのワザは使える。その番の終わりに消える。ベンチにもどる・進化・きぜつで消える（p.311・p.322・p.323。ほかの持続する効果と同じ）。

    - ``attack_index``: 効果を与えたワザ（「あわあわ」）の位置
    - ``target_attack_index``: 使えなくなるワザの位置（「あわあわ」は自分自身なので ``attack_index`` と同じ）
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    attack_index: int
    target_attack_index: int
    # v0.49: 効果を与えたワザ・使えなくなるワザを印刷したカードの id（同じカードのワザ）。None なら ``source_card`` のカード（v0.48 までと同じ）。使えなくなるワザは
    # (このカード id, ``target_attack_index``) の ``AttackKey`` で探す（ワザの一覧の位置・名前では探さない。``persistent.attack_locked``）
    attack_card: str | None = None
    kind: ClassVar[str] = "cannot_use_own_attack"
    turns_until_active: ClassVar[int] = 2  # 次の自分の番
    on_opponent: ClassVar[bool] = False

    def __post_init__(self) -> None:
        _check_attack_card(self.attack_card)


@dataclass(frozen=True)
class CannotUseAttack:
    """ワザによる「持続する効果」（v0.35）のうち、カスミのニョロモ（PMCG5-022）の「ドわすれ」の「相手のワザを1つ選ぶ。次の相手の番、そのポケモンは、
    そのワザを使えない。」（kyuura の印刷の文面）。

    相手に与える効果（``on_opponent``。v0.31 の ``CannotAttack`` と同じ）。効果を受けるのは相手の対戦ポケモンで、``source_card``・``source_player`` は
    効果を与えたワザを使ったポケモンのカードとそのプレイヤー。はたらく番は次の相手の番（受けているポケモンの持ち主の番。``created_turn + 1``）で、その番の
    間、受けているポケモンは ``target_attack_index`` のワザ（効果を受けたときのいちばん上のカードの。ワザを使ったプレイヤーが選んだもの）を使えない。
    ほかのワザ・にげる・特殊能力は制限しない。消える契機はほかの持続する効果と同じ（期限・ベンチにもどる・進化・きぜつ）。進化すると、いちばん上の
    カードが変わる前に消える（p.310・p.323）ので、位置で持ってよい。

    - ``attack_index``: 効果を与えたワザ（「ドわすれ」）の、``source_card`` のカードの位置
    - ``target_attack_index``: 使えなくなる、受けているポケモンのワザの位置
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    attack_index: int
    target_attack_index: int
    # v0.49: 効果を与えたワザ（「ドわすれ」）を印刷したカードの id（None なら ``source_card`` のカード）と、使えなくなるワザを印刷したカードの id（None なら受けている
    # ポケモンのいちばん上のカード。v0.48 までと同じ）。受けているポケモンのワザの一覧（サイコリンクなど）から選んだワザを (カード id, 位置) で持つ
    attack_card: str | None = None
    target_attack_card: str | None = None
    kind: ClassVar[str] = "cannot_use_attack"
    turns_until_active: ClassVar[int] = 1
    on_opponent: ClassVar[bool] = True

    def __post_init__(self) -> None:
        _check_attack_card(self.attack_card)
        _check_attack_card(self.target_attack_card)


@dataclass(frozen=True)
class AttackCoinCheck:
    """ワザによる「持続する効果」（v0.36）のうち、p.309 のワザを使う手順 4 の「ワザを失敗させたりワザの内容を変えてしまう効果」: 効果を受けたポケモンが、
    はたらく番にワザを使うとき、持ち主（効果を受けたポケモン側のプレイヤー）がコインを 1 枚投げ、「うら」ならワザは失敗する（サンドの「すなかけ」・
    ブーバー・タッツーの「えんまく」・わるいサンダースの「サンダーフラッシュ」・カスミのパウワウの「しんきろう」など。docs/sand-attack-retreat-lock-v0.36.md）。

    相手に与える効果（``on_opponent``。v0.31 の ``CannotAttack`` と同じ）。効果を受けるのは相手の対戦ポケモンで、``source_card``・``source_player`` は効果を
    与えたワザを使ったポケモンのカードとそのプレイヤー（相手のワザとして使ったときは、使ったポケモン。どのワザで与えたかはログ ``persistent_effect_added``
    の ``effect``）。はたらく番は次の相手の番（``created_turn + 1``。受けているポケモンの持ち主の番）。ワザの宣言を拒否しない（宣言できる。手順 3 のあと、
    こんらんの手順 5 の前にコインを投げる。``resolution.flow._attack_body``）。

    - ``single_use``: サンド（PMCG1-051）の「すなかけ」の「「すなかけ」の効果は1回できえる」。手順 4 のコインを投げたら（「おもて」でも「うら」でも）消える
      （ログ ``persistent_effect_removed`` の理由 ``used``）。ほかの文面（「次の相手の番に…」）の効果は、はたらく番の終わりに消える。どちらも、はたらく番は
      次の番だけ（PMCG1-051 の「次の番に」も次の相手の番）で、ワザは 1 番に 1 回なので、どちらの消え方でも同じ番に 2 回目のコインはない
    消える契機はほかの持続する効果と同じ（期限・ベンチにもどる・進化・きぜつ。p.311・p.322・p.323）。効果を与えたポケモンが場をはなれても消えない（p.322）。

    - ``lasting``（v0.45）: カスミのタッツー（PMCG5-024）の「スミをかける」の「このワザを受けた相手は、それ以後ワザを使うたびにコインを投げ、「うら」なら
      ワザは失敗する。バトル場をはなれたポケモンからは、このワザの効果は消える。」（kyuura の印刷の文面）。はたらく番（次の相手の番）から、期限で消えずに
      はたらき続ける（``active_on``。番の終わりの期限の処理 ``persistent.remove_expired_persistent_effects`` が消さない）。消えるのはバトル場をはなれたとき
      （ベンチにもどる・きぜつ・山札や手札にもどる）と進化したとき（p.310・p.323 の一般の規定）。「次の相手の番」の効果（えんまくなど）の期限は変えない
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    single_use: bool = False
    lasting: bool = False  # v0.45: 「それ以後」（カスミのタッツーの「スミをかける」）。はたらく番から期限なしにはたらく
    kind: ClassVar[str] = "attack_coin_check"
    turns_until_active: ClassVar[int] = 1
    on_opponent: ClassVar[bool] = True

    def active_on(self, turn: int) -> bool:
        """番 ``turn`` にはたらいているか（v0.45）。ふつうは、はたらく番だけ。``lasting`` なら、はたらく番とそれ以後のすべての番（期限で消えない）。"""
        return self.active_turn <= turn if self.lasting else self.active_turn == turn


@dataclass(frozen=True)
class CannotRetreat:
    """ワザによる「持続する効果」（v0.36）のうち、カスミのパウワウ（PMCG5-023）の「アイスバーン」・マチスのオニドリル（PMCG5-064）の「わしづかみ」の
    「このワザを受けた相手は、次の相手の番に「にげる」ことができない。」（kyuura の印刷の文面）。

    相手に与える効果（``on_opponent``。``CannotAttack`` と同じ）。はたらく番は次の相手の番（``created_turn + 1``）で、その番の間、受けているポケモンは
    「にげる」を宣言できない（``engine._retreat`` がエネルギーのトラッシュ・こんらんのコインの前に ``RETREAT_PREVENTED`` で拒否する）。「にげる」ではない
    入れ替え（ポケモンいれかえ・突風・ふきとばし・テレポート）は制限しない（p.325「「にげる」がおこなえない状態のポケモンでも、「そのポケモンを入れ替える」
    と指示されたときは、入れ替えをおこないます」）。ワザ・特殊能力も制限しない。消える契機はほかの持続する効果と同じ（期限・ベンチにもどる・進化・きぜつ）。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    kind: ClassVar[str] = "cannot_retreat"
    turns_until_active: ClassVar[int] = 1
    on_opponent: ClassVar[bool] = True


@dataclass(frozen=True)
class CannotAttackWhileSourceActive:
    """ワザによる「持続する効果」（v0.40）のうち、サカキのニドキング（PMCG6-021）の「すごむ」の「このワザを受けた相手が「最大HPが50以下」のポケモンなら、
    そのポケモンは、次の相手の番、このカードがバトル場にいる限り、ワザを使えない。」（kyuura の印刷の文面。docs/count-condition-switch-return-v0.40.md 4 章）。

    相手に与える効果（``on_opponent``。``CannotAttack`` と同じ）。``source_card``・``source_player`` は効果を与えたワザを使ったポケモン（「このカード」）の
    いちばん上のカードとそのプレイヤー。はたらく番は次の相手の番（``created_turn + 1``）で、その番の間、受けているポケモンは、効果を与えたポケモン（``source_card``
    のカードがいちばん上のポケモン）が持ち主のバトル場にいるときだけ、ワザを使えない（``persistent.cannot_attack_while_source_active``。確かめるのはワザの宣言の
    とき。``checks.attack_request``）。「最大HPが50以下」は効果を与えるときに確かめ、状態には持たない（受けているポケモンが進化すると、ほかの持続する効果と同じく
    消える。p.310）。消える契機はほかの持続する効果と同じ（期限・ベンチにもどる・進化・きぜつ）。効果を与えたポケモンがバトル場をはなれても、この効果は消さない
    （はなれている間はワザを使える。同じ番にバトル場にもどる場合は決められない（SG1）ので、突風がもどす選択を止める。``effects.SwitchOpponentWithBench``）。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    kind: ClassVar[str] = "cannot_attack_while_source_active"
    turns_until_active: ClassVar[int] = 1
    on_opponent: ClassVar[bool] = True


@dataclass(frozen=True)
class WeaknessChange:
    """ワザによる「持続する効果」（v0.48。docs/effective-pokemon-properties-v0.48.md 3 章）のうち、ポリゴン（PMCG1-064・PMCG4-050）の「テクスチャー1」の
    「相手の対戦ポケモンの弱点を好きな「色」にかえる。ただし「無色」にはできない。相手がベンチに戻った時にその効果はきえる。」（第1弾）・「相手の対戦ポケモンの
    「弱点」を、無色以外の好きな「色」に変える。この効果は、そのポケモンがバトル場をはなれた時に消える。」（ロケット団）（kyuura の印刷の文面）。

    相手に与える効果（``on_opponent``。``CannotAttack`` と同じく、``source_card``・``source_player`` は効果を与えたワザを使ったポケモンのカードとそのプレイヤー）。
    与えたときからはたらき（``turns_until_active`` は 0）、期限では消えない（``lasting``。説明は番の期限を書かない）。消えるのは、受けたポケモンがベンチにもどる・
    場をはなれる（説明の「ベンチに戻った時」「バトル場をはなれた時」）と進化する（p.310・p.323 の一般の規定。GR-2000-P322-PERSISTENT-EFFECTS）とき。弱点の倍数は
    変えない（色だけ）。受けているポケモンの弱点は ``effects.weakness_of``（今有効な弱点）で求める。同じポケモンが 2 つ受けることはない（新しく与えるときに前の
    効果を理由 ``replaced`` で消す）。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    color: EnergyType
    kind: ClassVar[str] = "weakness_change"
    turns_until_active: ClassVar[int] = 0
    on_opponent: ClassVar[bool] = True
    lasting: ClassVar[bool] = True


@dataclass(frozen=True)
class ResistanceChange:
    """ワザによる「持続する効果」（v0.48）のうち、ポリゴン（PMCG1-064）の「テクスチャー2」の「自分の抵抗力を好きな「色」にかえる。ただし「無色」にはできない。
    自分がベンチに戻ったときにその効果はきえる。」（kyuura の印刷の文面）。

    自分自身に与え、与えたときからはたらき、期限では消えない（``WeaknessChange`` と同じ消え方）。変えるのは抵抗力の色だけで、抵抗力の数（−30 など。
    ``CardDefinition.resistance_value``）は変えない。受けているポケモンの抵抗力は ``effects.resistance_of`` で求める。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    color: EnergyType
    kind: ClassVar[str] = "resistance_change"
    turns_until_active: ClassVar[int] = 0
    on_opponent: ClassVar[bool] = False
    lasting: ClassVar[bool] = True


@dataclass(frozen=True)
class MaxHpSet:
    """ワザによる「持続する効果」（v0.48）のうち、キョウのメタモン（PMCG6-072）の「きょだいか」の「コインを投げて「おもて」なら、このカードの最大HPは「80」になる。
    (バトル場をはなれた時、この効果は消える)」（kyuura の印刷の文面）。

    自分自身に与え、与えたときからはたらき、期限では消えない（``WeaknessChange`` と同じ消え方。説明の「バトル場をはなれた時」）。はたらいている間、このポケモンの
    最大HPは ``amount``（``effects.max_hp``）。同じワザの「はたく」の「このカードに「きょだいか」の効果がはたらいているとき」も、この効果があるか（``effects.max_hp_set``）
    で決める（最大HPと同じものを見る）。
    """

    source_card: int
    source_player: int
    created_turn: int
    active_turn: int
    amount: int
    kind: ClassVar[str] = "max_hp_set"
    turns_until_active: ClassVar[int] = 0
    on_opponent: ClassVar[bool] = False
    lasting: ClassVar[bool] = True


@dataclass(frozen=True)
class TypeShift:
    """特殊能力でポケモンの色（タイプ）を変えた記録（v0.48。モルフォン（PMCG2-015）の［へんしょく］の「このカード持ち主は、自分の番に1回、このカードの色を場にいる
    ポケモンのどれかの色に変えることができる。「ねむり・マヒ・こんらん」状態の時、この力は消える。」。kyuura の印刷の文面）。

    ワザによる持続する効果（``persistent_effects``）ではない（特殊能力の効果で、P322 の持続する効果の規定はワザの効果のもの）。場のポケモンの ``type_shift`` に持つ。
    説明は効果の期限を書かないので、変えた色が「使った番のあと」「ベンチにもどったあと」「この力が消えている（ねむり・マヒ・こんらん・かがくへんかガス）あいだ」も
    続くかは決められない（VS1。``effects.type_readings`` が、決まらない場合に 2 つの読み方（変えた色・印刷の色）を返し、結果が変わる処理だけを止める）。

    - ``color``: 変えた色
    - ``turn``: 使った番（``GameState.turn_number``）
    - ``source_card``: 使ったときのいちばん上のカード（進化したら消す。``evolution.place_evolution_card``）
    - ``returned_to_bench``: 使ったあと、このポケモンがバトル場からベンチにもどった（にげる・入れ替え）か。もどったら真にする（``mark_returned_to_bench``）
    場をはなれたら、場のポケモンといっしょになくなる。
    """

    color: EnergyType
    turn: int
    source_card: int
    returned_to_bench: bool = False


def mark_returned_to_bench(pokemon: PokemonInPlay) -> None:
    """バトル場からベンチにもどったポケモンの、特殊能力で色を変えた記録（``TypeShift``）に、ベンチにもどったことを残す（v0.48）。記録がなければ何もしない。
    にげる・ポケモンいれかえ／突風・ワザによる入れ替えの 3 か所で、特殊状態・持続する効果を消すのと同じところで呼ぶ（ログは残さない。記録の項目が変わるだけ）。"""
    if pokemon.type_shift is not None and not pokemon.type_shift.returned_to_bench:
        pokemon.type_shift = TypeShift(pokemon.type_shift.color, pokemon.type_shift.turn, pokemon.type_shift.source_card, True)


# ワザによる持続する効果の型（v0.4b。v0.12 で Retaliation、v0.27 で NextTurnAttackDamage、v0.31 で DestinyBond・AttackBarrier・DamageReduction・
# CannotAttack、v0.34 で ReducedDamageToSource、v0.35 で CannotUseOwnAttack・CannotUseAttack、v0.36 で AttackCoinCheck・CannotRetreat、v0.40 で
# CannotAttackWhileSourceActive、v0.45 で ZeroDamageBelow、v0.46 で HalvedDamage、v0.48 で WeaknessChange・ResistanceChange・MaxHpSet を加えた）。加えるときは、消える契機（ベンチ・進化・きぜつ・期限）と不変条件を見直す
PERSISTENT_EFFECT_TYPES = (PreventDamage, Retaliation, NextTurnAttackDamage, DestinyBond, AttackBarrier, DamageReduction, CannotAttack,
                           ReducedDamageToSource, CannotUseOwnAttack, CannotUseAttack, AttackCoinCheck, CannotRetreat, CannotAttackWhileSourceActive,
                           ZeroDamageBelow, HalvedDamage, WeaknessChange, ResistanceChange, MaxHpSet)


@dataclass(frozen=True)
class TrainerUseLock:
    """プレイヤーに与える、期限のあるトレーナーカードの使用の禁止（v0.47。docs/fossil-hidden-info-v0.47.md 5 章。コダック（化石の秘密）の「ずつう」・マチスの
    サンダースの「こうしゅうは」の「次の相手の番の終わりまで、相手プレイヤーはトレーナーカードを使うことができない」）。

    - 場のポケモンではなくプレイヤーに与える効果（``GameState.trainer_locks``）。ワザによる持続する効果（``PokemonInPlay.persistent_effects``。場のポケモンが受け、
      ベンチにもどる・進化・きぜつで消える）とは別に持つ。対戦ポケモンの入れ替え・効果を与えたポケモンが場をはなれることでは消えない
    - ``player``: 使えなくなるプレイヤー。``source_player``: 効果を与えたワザを使ったプレイヤー（``player`` の相手）。``source_card``: そのワザを使ったポケモンの
      いちばん上のカード。``effect``: そのワザ（``AttackKey`` の文字列）。``created_turn``: 与えた番。``expires_turn``: 消える番（その番の終わりに消す。「次の相手の
      番」は与えた番 + 1。番は交互に進む。v0.2e と同じ前提）
    - 常にはたらく特殊能力による禁止（v0.46 の［アレルギーかふん］。場から問い合わせる）とは別の記録で、両方が重なっても、それぞれの期間で判定する
    """

    player: int
    source_player: int
    source_card: int
    effect: str
    created_turn: int
    expires_turn: int
    # v0.56（docs/trainer-decisions-turn-effects-v0.56.md 6 章）: 禁止の出どころ。``"attack"``（既定。v0.47 のずつう・こうしゅうは。相手プレイヤーに与え、消える番は
    # 与えた番 + 1）か ``"trainer"``（ロケット団の実験の「うら」の「次のあなたの番が終わるまで、あなたはトレーナーカードを使えない」。使ったプレイヤー自身に与え
    # （``player`` = ``source_player``）、``source_card`` は使ったトレーナーのカード、``effect`` はそのカード id、消える番は与えた番 + 2）。既定の値の禁止は v0.55 と
    # 同じ値・書き出し・ログ
    origin: str = "attack"


# v0.56: プレイヤーに与える、期限のあるトレーナーの効果（``TrainerTurnEffect``）の種類
ATTACK_DAMAGE_BONUS = "attack_damage_bonus"  # カスミ: 「カスミのポケモン」が使うワザが対戦ポケモンにダメージを与える時、この番だけ +20（p.321 の 6 段階）
POISON_ON_ATTACK_DAMAGE = "poison_on_attack_damage"  # キョウ: 「キョウのポケモン」がワザで相手の対戦ポケモンにダメージを与えたら、どく状態にする（この番）
BENCH_ATTACK_DAMAGE_PREVENTION = "bench_attack_damage_prevention"  # 見えない壁: 次の相手の番が終わるまで、控えポケモンはワザによるダメージを受けない
TRAINER_TURN_EFFECT_KINDS = (ATTACK_DAMAGE_BONUS, POISON_ON_ATTACK_DAMAGE, BENCH_ATTACK_DAMAGE_PREVENTION)


@dataclass(frozen=True)
class TrainerTurnEffect:
    """v0.56（docs/trainer-decisions-turn-effects-v0.56.md 5 章）: トレーナーを使ったプレイヤーに与える、期限のある効果（カスミ・キョウ・見えない壁）。

    - 場のポケモンに持たせない（効果を受けるポケモンは、はたらく時点の場で決める: カスミ・キョウはワザを使うポケモンの今の姿の名前、見えない壁はダメージを受ける時点の
      持ち主の控えポケモン。使ったときの場のポケモンに写さないので、入れ替え・進化・あとから出したポケモンも同じに扱う）。トラッシュしたトレーナーのカード・今の
      バトル場のポケモンの番号から求め直さない
    - ``kind``: ``TRAINER_TURN_EFFECT_KINDS`` のどれか。数・名前（「カスミの」・+20）は効果の登録表の実装（``TrainerEffect.turn_effect_terms``）が持つ（状態に写さない）
    - ``player``: 使ったプレイヤー。``source_card``: 使ったトレーナーのカード（ログ・ダメージの記録の発生源）。``card_id``: そのカード id（登録の実装を引く）
    - ``created_turn``: 使った番（使ったプレイヤーの番）。``expires_turn``: 消える番（その番の終わりに消す。「この番」は使った番、「次の相手の番が終わるまで」は + 1）
    - かがくへんかガス・特殊状態では消えない（特殊能力ではない）。番の終わり（ワザ・番を終える・ロケット団員の「うら」のどれで終わっても同じ ``procedures.expire_at_turn_end``）
      に消す。勝敗が決まった番は番の終わりが来ないので残る（v0.2c のついているトレーナーと同じ）
    """

    kind: str
    player: int
    source_card: int
    card_id: str
    created_turn: int
    expires_turn: int


@dataclass(frozen=True)
class RecallEffect:
    """トレーナー「思い出させる」（PMCG5-071）の「あなたの対戦ポケモンが進化カードなら、この番だけ、進化前に持っていたワザを自分のワザとして使ってよい。」の、
    今の番の記録（v0.49。docs/virtual-attacks-transformation-v0.49.md 6 章）。

    - ``player``: 使ったプレイヤー（番のプレイヤー）。``turn``: 使った番（その番の終わりに消す）
    - ``pokemon_id``・``card``: 使ったときの対戦ポケモンの番号といちばん上のカード（進化前のワザを決める重なりは、このときのもの）
    - ``trainer``: 使った「思い出させる」のカードの uid（ログ ``recall`` との対応）
    使ったあとに対戦ポケモンが入れかわった・進化した・姿が変わったときに、進化前のワザを使えるかは決まらない（RC3。``effects.available_attacks`` が選べるワザに
    止める理由を付ける）。場のポケモンではなくプレイヤーの番の記録なので、最上位の ``GameState.recalls`` に持つ。
    """

    player: int
    turn: int
    pokemon_id: int
    card: int
    trainer: int


# 特殊状態のないポケモン（共有してよい。frozen）
NO_SPECIAL_CONDITIONS = SpecialConditions()
# ねむり状態（持つ情報がないので 1 つを共有してよい。frozen）
ASLEEP = Asleep()
# こんらん状態（同じ。v0.3c）
CONFUSED = Confused()


@dataclass
class PokemonInPlay:
    """場にいるポケモン（1 匹）。ポケモンのカード（進化していれば重なった 2 枚。v0.4a）と、ついているカード。

    識別子は 2 つあります。

    - ``card``: いちばん上のポケモンのカードの uid（物理的なカード）。このカードの内容（名前・HP・タイプ・弱点・抵抗力・
      にげる・ワザ）が、そのポケモンを表す（p.310 の進化の手順 2）。進化するといちばん上のカードが変わる
    - ``pokemon_id``: 場のポケモンそのものの番号（エンジンの内部の識別子）。場に出たときに ``GameState.next_pokemon_id``
      から付ける。場にいるあいだ（にげる・入れ替え・進化（v0.4a））変わらない。場を離れたら無効になり、同じカードが
      もう一度場に出ても前の番号は使わない。0 は「付けていない」（不変条件で拒否する）

    ``pokemon_id`` が同じでも、ルールの上で同じポケモンとは限らない: 進化したポケモンは「進化前のポケモンとは、別の
    ポケモンとしてあつかわれます」（p.310）。その帰結（進化前のワザを使えない、その番の最初には場にいなかったことに
    なる、特殊状態が消える、にげるの失敗の記録が消える、持続する効果が消える（v0.4b））は、``card``・``evolved_turn``・
    ``conditions``・``retreat_failed_turn``・``persistent_effects`` で表す（docs/evolution-state-v0.4a.md）。

    進化（v0.4a）:

    - ``evolution_stack``: いちばん上のカードの下に重なっているポケモンのカードの uid（下から順。いちばん下がたね
      ポケモン）。進化していなければ空。下のカードはトラッシュしない（p.310）が、場のポケモンとして数えず、内容も
      使わない。v0.4a は 1 進化だけなので 0 枚か 1 枚、v0.4c で 2 進化を加えたので 0〜2 枚（2 進化ならたねポケモン・
      1 進化ポケモンの順。重なったカードは全部で 3 枚まで。p.319）。変えるときは新しいタプルに置きかえる（複製で
      共有してよい）
    - ``played_turn``: このポケモンが場に出た番（``GameState.turn_number``。対戦準備で出したら 0）。にげる・入れ替え・
      ベンチからバトル場に出すことでは変わらない（場をはなれていない。p.313）
    - ``evolved_turn``: いまの姿に進化した番。進化していなければ None。「その番の最初から場に出ていた」（p.310）かは、
      いまの姿になった番（``evolved_turn``、なければ ``played_turn``）が今の番より前かで決まる。2 進化（v0.4c）では
      2 進化した番で、1 進化した番は状態に持たない（進化の条件に要らない。不変条件はログ ``evolve`` と照らす。
      docs/stage2-state-v0.4c.md）。v0.50: 退化して重なりが残れば、最後に進化した番のまま（重なりがなくなれば None）。
      いまの姿になった番は ``current_form_turn``（退化した番 ``devolved_turn`` を含む）

    ワザによる持続する効果（v0.4b）:

    - ``persistent_effects``: このポケモンが受けている、ワザによる持続する効果（``PreventDamage`` など。frozen の値の
      タプル）。特殊状態（``conditions``）・ついているトレーナー（``trainers``）とは別に持つ。持続する効果は重複する
      ことがある（p.323）ので複数を持てる形にしているが、v0.4b の対応カードで受けるのは「かたまる」だけ。変えるときは
      新しいタプルに置きかえる（複製で共有してよい）。docs/persistent-effects-v0.4b.md
    """

    card: int
    energy: list[int] = field(default_factory=list)
    damage: int = 0
    pokemon_id: int = 0
    trainers: list[AttachedTrainer] = field(default_factory=list)  # ついているトレーナーカード（v0.2c）
    conditions: SpecialConditions = NO_SPECIAL_CONDITIONS  # 特殊状態（v0.3a。frozen なので複製でも共有してよい）
    # こんらん状態で「にげる」に失敗した番（v0.3c）。「一度「にげる」に失敗したこんらん状態のポケモンは、今の自分の番では、
    # もう「にげる」を宣言することができません」（p.311）。特殊状態ではないので ``conditions`` に入れない（ベンチに戻っても
    # 消さない）。番の終わりに消す（「次の自分の番になれば、再び「にげる」を宣言することができます」）
    retreat_failed_turn: int | None = None
    evolution_stack: tuple[int, ...] = ()  # v0.4a
    played_turn: int = 0  # v0.4a
    evolved_turn: int | None = None  # v0.4a
    persistent_effects: tuple[Any, ...] = ()  # v0.4b（型は PERSISTENT_EFFECT_TYPES。Retaliation は v0.12、NextTurnAttackDamage は v0.27、ほかは v0.31）
    # v0.44（docs/search-evolution-once-attacks-v0.44.md 3 章）: 「このワザは、このカードが場に出てから、1回しか使えない」ワザ（キョウのスピアーの「ひっさつばり」・
    # カモネギの「ネギでたたく」・サカキのコイキングの「りゅうのきおく」）を、この場のポケモンが使った記録。(ワザを持つカードの uid, ワザの位置) の重ならない並び。
    # ワザの宣言（p.309 の手順 3）のときに加える（こんらんの「うら」・手順 4 の失敗・コインの「うら」でも使ったことになる。p.323「12」・v0.3d の A12）。場のポケモンに
    # 持つので、にげる・入れ替え・番の終わりでは消えず、場をはなれたら（きぜつ・手札や山札にもどる）なくなる（もう一度場に出たら新しい場のポケモン）。ログから数えない
    attacks_used_once: tuple[tuple[int, int], ...] = ()
    # v0.44: トレーナー「サカキ」で選ばれ、今の番、場に出た番・進化した番でも進化させてよい（p.310 の制限のうち「その番に場に出した」「その番に進化した」だけを
    # 変える）番。なければ None。番の終わりに消す（``procedures.expire_at_turn_end``）。進化しても場のポケモンは同じなので受け継ぐ（「進化したそのポケモンを、同じ番で、
    # さらに進化させてもよい」）。場をはなれたらなくなる
    evolution_permission_turn: int | None = None
    # v0.48（docs/effective-pokemon-properties-v0.48.md 4 章）: 特殊能力で色（タイプ）を変えた記録（モルフォンの［へんしょく］。``TypeShift``）。なければ None
    type_shift: TypeShift | None = None
    # v0.49（docs/virtual-attacks-transformation-v0.49.md 4 章）: タケシのキュウコンの「ばける」で、このカードの上にのせた手札の進化カードの uid。なければ None。
    # 進化の重なり（``evolution_stack``）とは別の重なりで、``card``（いちばん上のポケモンのカード。このポケモンそのもの）は変えない。のせたカードのポケモンとして
    # あつかう（今の姿。``effects.current_form``）が、進化・退化ではない（場のポケモンの番号・場に出た番・進化した番・持続する効果・特殊状態は変えない）。
    # トラッシュしてもどす（``RemoveDisguise``）・ねむり・マヒ・こんらんになる（のせたカードはトラッシュされる）と None にもどす
    disguise: int | None = None
    # v0.50（docs/mew-devolution-spray-v0.50.md 3 章）: このポケモンが最後に退化した番（ミュウの「たいかビーム」・退化スプレー。``evolution.devolve``）。退化したことが
    # なければ None。退化したポケモンは「退化前とは別のポケモン」（p.324「19」）で、いまの姿になった番（``current_form_turn``）はこの番になる。退化した番に、そのポケモンを
    # 進化させられるか（p.310 の「その番の最初から場に出ていた」「その番に進化した」の当てはめ）は決まらないので、エンジンが止める（DV2。``evolution.evolution_block``）。
    # 進化しても消さない（いまの姿になった番は、進化した番と退化した番の新しいほう）。場をはなれたらなくなる
    devolved_turn: int | None = None

    @property
    def current_form_turn(self) -> int:
        """いまの姿（いちばん上のカード）になった番（場に出た番・進化した番・退化した番（v0.50）のいちばん新しい番。v0.4a）。退化していなければ v0.49 までと同じ
        （進化した番、進化していなければ場に出た番）。"""
        turn = self.played_turn if self.evolved_turn is None else self.evolved_turn
        return turn if self.devolved_turn is None else max(turn, self.devolved_turn)

    def cards(self) -> tuple[int, ...]:
        """このポケモンを作っているポケモンのカード（下から順。``card`` の上に、v0.49 の「ばける」でのせた進化カード（``disguise``）があれば最後）。ついている
        カード（エネルギー・トレーナー）は含まない。きぜつ・山札や手札にもどすときは、これをいっしょに動かす。"""
        if self.disguise is None:
            return (*self.evolution_stack, self.card)
        return (*self.evolution_stack, self.card, self.disguise)

    def clone(self) -> PokemonInPlay:
        return PokemonInPlay(
            self.card,
            list(self.energy),
            self.damage,
            self.pokemon_id,
            list(self.trainers),
            self.conditions,
            self.retreat_failed_turn,
            self.evolution_stack,
            self.played_turn,
            self.evolved_turn,
            self.persistent_effects,
            self.attacks_used_once,
            self.evolution_permission_turn,
            self.type_shift,
            self.disguise,
            self.devolved_turn,
        )


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
    # v0.57（docs/stadiums-v0.57.md 7 章）: 錯乱ジムで、コインが「うら」になり、相手プレイヤーがかわりに使っている（借りて使う）ときの、使っているプレイヤー。
    # ``player`` はいつもカードの持ち主（使い終わったら持ち主のトラッシュにすてる）。None なら持ち主が使っている（v0.56 までと同じ値）
    user: int | None = None
    # v0.58（docs/stadium-reuse-special-energy-v0.58.md 4 章）: 別のトレーナー（ナツメのサイキックコントロール）の効果で、相手のトラッシュから使っているときの、その外側の
    # トレーナーのカードの uid（外側の使用は ``GameState.trainer_stack`` の最後にある）。None なら手札から使っている（v0.57 までと同じ値）。カードの物理的な所在（使用中の
    # 場所。トラッシュから出して、使い終わったら持ち主のトラッシュにもどす）と、効果を使っている記録（``user``・``via``）を分けて持つ
    via: int | None = None

    @property
    def using_player(self) -> int:
        """このトレーナーの効果を使っているプレイヤー（v0.57。借りて使っていれば相手プレイヤー、ほかは持ち主）。"""
        return self.player if self.user is None else self.user


@dataclass(frozen=True)
class StadiumInPlay:
    """場に出ているスタジアムカード（v0.57。docs/stadiums-v0.57.md 2 章）。

    スタジアムカードはトレーナーカードの種類のひとつで、自分の場と相手の場の境界線上に出し、両方の場に出ているカードとして扱う（kyuura の rule_differences の
    「stadium」の 2000.02.14 版の行・GR-2000-P312-FIELD「ポケモンや、ポケモンにつけて使うトレーナーカード、スタジアムカードを出す場所」）。

    - 実際のカード 1 枚（``card`` の uid）を 1 か所に持つ（両方の場に写さない。カードの保存則では持ち主のゾーンとして 1 回だけ数える）
    - ``owner``: カードの持ち主（場に出したプレイヤー。トラッシュするときは持ち主のトラッシュ）。効果を使うプレイヤー（お互いのプレイヤー）とは別
    - ``placed_turn``: 場に出した番
    - 場に出せるスタジアムは 1 枚（新しいスタジアムが場に出たら古いものをトラッシュする。どのスタジアムの印刷の文面にもある）
    """

    owner: int
    card: int
    placed_turn: int


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
    # この番に、ポケモンパワー（特殊能力）の効果で手札から場のポケモンにつけたエネルギーカードの枚数（v0.6。カメックスの
    # 「あまごい」）。手札からつける通常の操作（p.310。``energy_attachments_this_turn``）とは別に数える。番の最初に 0 にする。
    # 通常の操作でまだつけていない番に、この数が 1 以上なら、通常の操作は原典で決められない（``UNRESOLVED_ATTACH_AFTER_POWER_ATTACH``。
    # docs/rain-dance-v0.6.md の R13）。書き出しは形式 9 だけが表せる（0 でなければ形式 1〜8 は ``ValueError``）
    energy_attached_by_powers_this_turn: int = 0
    # v0.31: この番に使った「自分の番ごとに1回使える」特殊能力（(場のポケモンの番号, 特殊能力の位置) の並び。カツラのロコンの「しぜんになおる」）。
    # 番の最初に空にする。回数の制限のある特殊能力の回数を状態に持つ（ログから数えない）。書き出しは形式 10 だけが表せる
    power_uses_this_turn: tuple[tuple[int, int], ...] = ()
    # v0.31: この番に「炎」エネルギーになったエネルギーカード（(場のポケモンの番号, エネルギーカードの uid) の並び。リザードンの「エナジーバーン」の
    # 「このカードについているすべてのエネルギーは「炎」エネルギーになり、自分の番の終わりにもとにもどる」）。そのポケモンについている間だけ「炎」
    # エネルギーとして扱う（``energy_types``）。番の終わりに空にする。書き出しは形式 10 だけが表せる
    energy_burn: tuple[tuple[int, int], ...] = ()
    # v0.47（docs/fossil-hidden-info-v0.47.md 5 章）: プレイヤーに与えた、期限のあるトレーナーカードの使用の禁止（``TrainerUseLock`` の並び。与えた順）。消える番の
    # 終わりに消す（``procedures.expire_at_turn_end``。ログ ``trainer_lock_removed``）。書き出しは形式 12 だけが表せる（空でなければ形式 1〜11 は ``ValueError``）
    trainer_locks: tuple[TrainerUseLock, ...] = ()
    # v0.49（docs/virtual-attacks-transformation-v0.49.md 6 章）: この番に使った「思い出させる」の記録（``RecallEffect`` の並び。使った順）。番の終わりに消す
    # （``procedures.expire_at_turn_end``）。書き出しは形式 14 だけが表せる（空でなければ形式 1〜13 は ``ValueError``）
    recalls: tuple[RecallEffect, ...] = ()
    # v0.56（docs/trainer-decisions-turn-effects-v0.56.md 5 章）: トレーナーを使ったプレイヤーに与えた、期限のある効果（``TrainerTurnEffect`` の並び。与えた順）。消える番の
    # 終わりに消す（``procedures.expire_at_turn_end``。ログ ``trainer_effect_removed``）。書き出しは形式 16 だけが表せる（空でなければ形式 1〜15 は ``ValueError``）
    trainer_effects: tuple[TrainerTurnEffect, ...] = ()
    # v0.57（docs/stadiums-v0.57.md 2 章）: 場に出ているスタジアムカード（なければ None）。書き出しは形式 17 だけが表せる（あれば形式 1〜16 は ``ValueError``）
    stadium: StadiumInPlay | None = None
    # v0.57: この番に使った「自分の番ごとに1回」のスタジアムの効果（(使ったプレイヤー, スタジアムカードの uid) の並び。セキチクシティジム）。番の最初に空にする。
    # コインが「うら」でも使ったことになる（使うことを選んだときに記録する）。書き出しは形式 17 だけが表せる
    stadium_uses_this_turn: tuple[tuple[int, int], ...] = ()
    # v0.58（docs/stadium-reuse-special-energy-v0.58.md 4 章）: 内側のトレーナー（``trainer_in_use``。外側のトレーナーの効果で使っているカード）を使い終わるのを待っている、
    # 外側のトレーナーの使用（``TrainerInUse`` の並び。外側から順。ナツメのサイキックコントロール）。内側を使い終えたら、外側のカードも順にトラッシュする。カードの
    # 保存則の対象（使用中のトレーナーと同じ場所）。書き出しは形式 18 だけが表せる（空でなければ形式 1〜17 は ``ValueError``）
    trainer_stack: tuple[TrainerInUse, ...] = ()

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
        """カード ``uid`` の、今の場所での定義。

        v0.47（docs/fossil-hidden-info-v0.47.md 2 章）: ポケモンとして場に出せるトレーナーカード（なにかの化石・ピッピ人形。効果の登録表の
        ``play_profile``）は、場のポケモンのカード（いちばん上のカードか、進化して下に重なったカード）であるあいだだけ、場での役割の定義（``category`` は
        "pokemon"・``play_role`` あり）を返す。手札・山札・サイド・トラッシュ・使用中のトレーナーでは、印刷の定義（トレーナーカード）のまま（「場に出ている
        とき以外は、トレーナーカードとしてあつかう」）。ほかのカードは、どこにあっても印刷の定義（v0.46 までと同じ）。印刷の定義・写しは変えない。"""
        definition = self.definitions[self.cards[uid].card_id]
        if definition.category == "trainer":
            profile = self.effects.play_profile(definition)
            if profile is not None and self._as_pokemon_in_play(uid):
                return profile
        return definition

    def printed_def(self, uid: int) -> CardDefinition:
        """カード ``uid`` の印刷の定義（写しから読んだ定義。場所によらない。v0.47）。"""
        return self.definitions[self.cards[uid].card_id]

    def in_play_def(self, uid: int) -> CardDefinition:
        """カード ``uid`` が場のポケモンのカードとしてあつかわれるときの定義（v0.47。場所によらない）。ポケモンとして場に出せるトレーナーカードなら場での役割の
        定義、ほかは印刷の定義。ログから場を組み立て直す確かめ（監査・不変条件）が、そのカードが今は場にいないときにも、場にいたときの定義を引くために使う。"""
        definition = self.definitions[self.cards[uid].card_id]
        if definition.category == "trainer":
            profile = self.effects.play_profile(definition)
            if profile is not None:
                return profile
        return definition

    def _as_pokemon_in_play(self, uid: int) -> bool:
        """カード ``uid`` が、場のポケモンを作っているカード（いちばん上か、下に重なったカード）か（v0.47）。ついているカードは含まない。"""
        for player in self.players:
            for pokemon in player.in_play():
                if pokemon.card == uid or uid in pokemon.evolution_stack:
                    return True
        return False

    def find_pokemon(self, pokemon_id: int) -> tuple[int, PokemonInPlay] | None:
        """場のポケモンの番号から、(持ち主, ポケモン) を返す。場にいなければ None。"""
        for player, p in enumerate(self.players):
            pokemon = p.find_by_pokemon_id(pokemon_id)
            if pokemon is not None:
                return player, pokemon
        return None

    def energy_types(self, pokemon: PokemonInPlay) -> list[EnergyType]:
        """``pokemon`` についているエネルギーが出すエネルギーのタイプ（ついている順）。v0.31: この番に「エナジーバーン」で「炎」エネルギーに
        なったカード（``energy_burn``。そのポケモンについている間）は「炎」。"""
        return [self.energy_type_of(pokemon, uid) for uid in pokemon.energy]

    def energy_type_of(self, pokemon: PokemonInPlay, uid: int) -> EnergyType:
        """``pokemon`` についているエネルギーカード ``uid`` が出すエネルギーのタイプ（v0.31。``energy_types`` の 1 枚ぶん）。"""
        if (pokemon.pokemon_id, uid) in self.energy_burn:
            return EnergyType.FIRE
        return self.card_def(uid).provides

    def add_event(self, kind: str, **data: Any) -> None:
        if "turn" in data:
            # ログの "turn" はいつも今の番（v0.3b で、イベントの項目が上書きしないように確かめる）
            raise ValueError(f"イベント {kind} の項目に turn は使えない（ログの番の番号と重なる）")
        self.log = self.log + (MappingProxyType({"kind": kind, "turn": self.turn_number, **data}),)


def freeze_mapping(mapping: Mapping) -> Mapping:
    return MappingProxyType(dict(mapping))


def turn_owner(state: GameState, turn_number: int) -> int:
    """``turn_number`` 番目の番のプレイヤー。1 番目は先攻（ジャンケンの勝者）で、交互に進む（p.308・p.309）。

    番は先攻から 1 つずつ交互に進む（不変条件で確かめている）ので、番の番号だけで決まる。
    ``engine.turn_owner`` と同じもの（v0.3b でマヒの回復する番を決めるのに使うため、ここに移した）。
    """
    return state.first_player if turn_number % 2 == 1 else 1 - state.first_player

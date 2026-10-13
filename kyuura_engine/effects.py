"""カードの効果の実装の登録表（v0.2a、レビューの M5。v0.2b でトレーナーを加えた）。

カードのデータ（kyuura の写し。印刷された文面と数値）と、エンジンが実装している処理を分けます。
あるワザ・トレーナーを対戦で使えるのは、この登録表にその実装が登録されているときだけです。
説明文が空であることは、実装がある証拠として扱いません（説明文のないワザも、効果のないワザとして
明示的に登録します）。

識別子は、ワザなら ``AttackKey``（カード id とワザの位置）、トレーナーならカード id、ポケモンパワー（v0.5）なら
``PowerKey``（カード id とパワーの位置）です。
名前は識別子にしません。同じ名前でも、カードが違えば別の登録です。登録するときに確かめた名前・文面
（``AttackEntry.name_ja``、``TrainerEntry.name_ja``・``text_ja``）は、データが変わったときに
気づくための照合にだけ使います。

登録している実装:

- ワザ: ``DamageOnly``（説明のないワザ）、``CoinFlipDamage``（v0.2d。コインを投げ、「おもて」の数×の
  ダメージ。ドードーの「みだれづき」。p.231 の最新の説明。docs/coin-attacks-v0.2d.md）、
  ``SelfDamageOnTails``（v0.2f。相手にダメージのあと、コインが「うら」なら自分にもダメージ。ピカチュウの
  「でんげき」。p.125 の最新の説明。docs/pikachu-v0.2f.md・docs/self-damage-v0.2f.md）、
  ``PoisonOnHeads``（v0.3a。相手にダメージのあと、コインが「おもて」なら相手をどく状態に。ビードルの
  「どくばり」。p.19 の最新の説明。docs/weedle-v0.3a.md・docs/special-conditions-v0.3a.md）、
  ``ParalyzeOnHeads``（v0.3b。相手にダメージのあと、コインが「おもて」なら相手をマヒ状態に。キャタピーの
  「いとをはく」。p.17 の最新の説明）、``PutToSleep``（v0.3b。ダメージを与えず、相手をねむり状態に。パラスの
  「キノコのほうし」。p.38 の最新の説明）。docs/cards-v0.3b.md・docs/sleep-paralysis-v0.3b.md、
  ``ConfuseOnHeads``（v0.3c。相手にダメージのあと、コインが「おもて」なら相手をこんらん状態に。ロコンの
  「あやしいひかり」。p.67 の最新の説明）。docs/confusion-v0.3c.md、
  ``PreventDamageOnHeads``（v0.4b。コインが「おもて」なら、次の相手の番、自分は「ダメージを受けない」状態（持続する
  効果）。トランセル・コクーンの「かたまる」。p.18・p.21 の最新の説明。docs/harden-v0.4b.md）、
  ``DamageAndForceSwitch``（v0.4d。相手にダメージのあと、相手の対戦ポケモンをベンチにもどし、相手が選んだ控えと入れ替える。
  決定するのは相手。バタフリーの「ふきとばし」。p.19 の最新の説明・p.213 のワザ解説。docs/forced-switch-v0.4d.md）、
  ``DamageAndDrain``（v0.4d。相手にダメージを与えたら、その半分（切り上げ）のダメージカウンターを自分からとりのぞく。
  バタフリーの「メガドレイン」。p.19 の最新の説明・p.319。docs/damage-drain-v0.4d.md）。v0.4d から ``deal_attack_damage`` が
  ダメージの要素の結果（``DamageResult``）を返す。
  ``DamageAndRemoveCounters``（v0.5。相手にダメージを与えたら、自分のダメージカウンターを決まった数とりのぞく。フシギダネの
  「やどりぎのタネ」。p.13 の最新の説明）、``PoisonOpponent``（v0.5。相手にダメージのあと、コインを投げずに相手をどく状態に。
  フシギソウの「どくのこな」。p.14 の最新の説明）。docs/bulbasaur-line-v0.5.md。``ExtraEnergyDamage``（v0.6。カメックスの
  「ハイドロポンプ」。p.90）。``DiscardEnergyAndRemoveAllCounters``（v0.7。自分についている「超」エネルギーカードをワザを使った
  プレイヤーが選んで 1 枚トラッシュし、自分のダメージカウンターをすべてとりのぞく。ユンゲラーの「じこさいせい」。p.151 の最新の
  説明。docs/alakazam-line-v0.7.md）
- トレーナー（v0.2b）: マサキ ``DrawCards``、きずぐすり ``RemoveDamageCounters``、
  ポケモンいれかえ ``SwitchWithBench``。処理は『ポケモンカードオフィシャルブック2000』p.254 の
  「最新の説明」にしたがう（``TrainerEntry.play_text_ja``。docs/trainers-v0.2b.md）
- つけて使うトレーナー（v0.2c）: プラスパワー ``AttachedAttackBonus``（p.257 の最新の説明。
  docs/pluspower-v0.2c.md）。カードはポケモンについて場に残り（``PokemonInPlay.trainers``）、
  ダメージ計算の 5 段階で効果を出し、番の終わりにエンジンがトラッシュする
- つけて使うトレーナー（v0.2e）: ディフェンダー ``AttachedDamageReduction``（p.257 の最新の説明。
  docs/defender-v0.2e.md）。自分の場のポケモンを選んでつけ、ついているポケモンがワザで受けるダメージを
  7 段階で減らし、次の相手の番の終わりにエンジンがトラッシュする
- ポケモンパワー（特殊能力。v0.5）: フシギバナの「エナジートランス」 ``EnergyTransfer``（p.16・p.323 の最新の説明。
  docs/pokemon-powers-v0.5.md・docs/energy-transfer-v0.5.md）。ワザとは別の登録（``PowerKey`` → ``PowerEntry``）と
  実装の基底（``PowerEffect``）。エンジンの ``_use_pokemon_power`` が、共通の確認のあとで ``check_usable``・``resolve`` を呼ぶ。
  v0.6 でカメックスの「あまごい」 ``AttachEnergyFromHand``（p.90。docs/rain-dance-v0.6.md）、v0.7 でフーディンの「ダメージスワップ」
  ``MoveDamageCounter``（p.153・p.320。docs/damage-swap-v0.7.md）を加えた

ほかのポケモンパワー・特殊エネルギー・ほかの効果のあるワザ・ほかのトレーナーは、実装を登録するまで未対応です。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable, Mapping

from .cards import EnergyType
from .coins import CoinSide, flip_coins
from .conditions import FORCED_SWITCH as FORCED_SWITCH_REASON
from .conditions import SWITCH, clear_special_conditions, confuse, paralysis_problem, paralyze, poison, put_to_sleep
from .damage import DamageModifier, calculate_attack_damage
from .decisions import DISCARD_ENERGY, FORCED_SWITCH, SELECT_POKEMON, push_attack_decision, push_trainer_decision
from .errors import IllegalActionError, UnsupportedError
from .persistent import add_persistent_effect, damage_prevention, remove_persistent_effects
from .state import PreventDamage
from .zones import attach_energy_from_hand, attach_trainer, draw_cards

if TYPE_CHECKING:
    from .cards import Attack, CardDefinition, Power
    from .state import AttachedTrainer, GameState, PendingDecision, PokemonInPlay


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
    - ``problem``（v0.3c）: このワザの処理が、原典で決められない場合なら、その理由（``UnsupportedError``）。
      エンジンがワザの宣言の前（こんらんのコインの前）に聞く。ワザを使う前の状態だけで決める（コインの結果で
      変わる条件も、ここで先に確かめる。「おもて」なら決められない、を投げてから見つけない）。v0.3d の対応カードの
      実装は、どれも既定（None）でよい（docs/effect-preflight-v0.3d.md。v0.3c の ``SelfDamageOnTails`` の確認は、
      v0.3d で原典の根拠が見つかり不要になった）。

    - ``decision_problems``（v0.4d）: このワザが出した決定（``resume`` が ``"attack"``）を待っている状態の、効果ごとの
      不変条件の問題。既定は「決定するのはワザを使ったプレイヤー」だけを確かめる。ワザを使われた側のプレイヤーが決定する
      効果（「ふきとばし」の ``FORCED_SWITCH``）は、上書きして決定の形（種類・決定するプレイヤー・選べるもの・続きの情報）を
      宣言する。エンジンの ``check_invariants`` が、どのワザの決定にも共通の確認（続きの情報・番のプレイヤー・ワザを使った
      ポケモン・今の番のワザのログ）のあとで呼ぶ。

    決定がなくなったら、エンジンがワザの後の処理（きぜつ・サイド・番の終わり）を続ける。
    """

    implementation_id = "abstract"

    def check(self, attack: Attack) -> list[str]:
        return []

    def problem(self, state: GameState, use: AttackUse) -> UnsupportedError | None:
        return None

    def resolve(self, state: GameState, use: AttackUse) -> None:
        raise NotImplementedError

    def resume(self, state: GameState, use: AttackUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        raise NotImplementedError(f"{self.implementation_id} は決定を出さない")

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        if decision.player != use.player:
            return [
                f"ワザ {use.key} の決定 {decision.kind} をするのがプレイヤー {decision.player} で、ワザを使ったプレイヤー {use.player} では"
                "ない（相手が決定する効果は decision_problems で宣言する）"
            ]
        return []


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
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
        damage_opponent_active(state, use, attack.damage)


@dataclass(frozen=True)
class CoinFlipDamage(AttackEffect):
    """コインを ``coins`` 枚投げ、「おもて」の数 × ``damage_per_heads`` のダメージを、相手の対戦ポケモンに与える
    （v0.2d。ドードーの「みだれづき」。p.231 の最新の説明「コインを2枚投げ、「おもて」の数×10のダメージ。」）。

    - ダメージの目安に「×」があるワザは、ワザの説明にしたがって計算した数のダメージを与える。0 倍になり、
      ダメージがなくなることもある（p.320）。ダメージを受けるのは、説明で特に指定されていないので、相手の
      対戦ポケモン（p.320）。
    - コインはワザの説明にしたがう処理（p.309 の手順 6）の中で投げる。必要なエネルギーの確認（手順 2）など、
      ワザを使えるかの確認は、エンジンが投げる前に済ませている。
    - 「おもて」の数 × ``damage_per_heads`` が p.321 の 1 段階（基本となるダメージ）。「おもて」が 0 枚なら 0 で、
      2 段階までで 0 以下なので計算を終え、「ダメージを与えなかった」（弱点・抵抗力・プラスパワーは計算しない）。
      これはワザの「失敗」（p.323）ではない（説明に「失敗」とは書かれていない）。どちらでも、ワザは使ったことになる。
    """

    coins: int
    damage_per_heads: int
    implementation_id = "coin_flip_damage"

    def problem(self, state: GameState, use: AttackUse) -> UnsupportedError | None:
        """相手の対戦ポケモンが「ダメージを受けない」状態（v0.4b。「かたまる」など）なら、原典で決められない。

        p.321 は「それを受けたポケモンが「ダメージを受けない」状態だったら、そのポケモンにダメージを与える「ワザの要素」は
        無効」と書く。このワザの要素は「コインを2枚投げ、「おもて」の数×10のダメージ」の 1 つだけで、コインはダメージの
        量を決めるためだけに投げる。無効になった要素のコインを投げるか（投げても結果は使わない）は書かれていない。
        投げるかどうかで乱数の続き（この先のコインの結果）が変わるので、こんらんのコインも含め、コインを投げる前に止める
        （docs/persistent-damage-v0.4b.md 5 章）。
        """
        target = state.players[1 - use.player].active
        prevention = None if target is None else damage_prevention(state, target)
        if prevention is None:
            return None
        return UnsupportedError(
            "UNRESOLVED_PREVENTED_COIN_DAMAGE",
            f"相手の対戦ポケモン {target.pokemon_id} は、この番「ダメージを受けない」状態（{prevention.kind}）。ダメージの量を"
            "コインで決めるワザの要素は無効になる（p.321）が、そのコインを投げるかは『オフィシャルブック2000』（p.309・p.319・"
            "p.320・p.321）から決められないので扱わない（投げるかどうかで乱数の続きが変わる）",
        )

    def __post_init__(self) -> None:
        if not isinstance(self.coins, int) or isinstance(self.coins, bool) or self.coins < 1:
            raise ValueError(f"コインの枚数は 1 以上の整数（{self.coins!r}）")
        if type(self.damage_per_heads) is not int or self.damage_per_heads <= 0 or self.damage_per_heads % 10:
            raise ValueError(f"「おもて」1 枚あたりのダメージは 10 の倍数の正の数（{self.damage_per_heads!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier != "×":
            problems.append("ダメージの目安に「×」のないワザを、「おもて」の数×のワザとして登録している")
        if attack.damage != self.damage_per_heads:
            problems.append(f"ダメージの目安の数字 {attack.damage!r} と、登録した「おもて」1 枚あたりのダメージ {self.damage_per_heads} が違う")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、コインを投げるワザとして登録している")
        return problems

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _, attacker = state.find_pokemon(use.pokemon_id)
        flips = flip_coins(
            state, use.player, self.coins, source="attack", effect=str(use.key), card=attacker.card, pokemon_id=attacker.pokemon_id
        )
        damage_opponent_active(state, use, flips.heads * self.damage_per_heads)


# ワザのダメージを受けるポケモン（p.320「ワザの要素」のダメージの分類）。今は (1) と (3) だけを扱う。
# (2) 相手の控えポケモン・(4) 自分の控えポケモンへのダメージは未実装（受けるポケモンを選ぶ手順と、計算の
# 手順（プラスパワーは控えへのダメージを変えない p.257 など）を原典で確かめてから加える）
OPPONENT_ACTIVE = "opponent_active"  # (1) 相手の対戦ポケモンへのダメージ
SELF = "self"  # (3) このワザを使うポケモンへのダメージ（v0.2f）
DAMAGE_TARGETS = (OPPONENT_ACTIVE, SELF)


def damage_receiver(state: GameState, use: AttackUse, target: str) -> PokemonInPlay:
    """ワザのダメージを受けるポケモン。``target`` は ``OPPONENT_ACTIVE`` か ``SELF``。"""
    if target == OPPONENT_ACTIVE:
        return state.players[1 - use.player].active
    if target == SELF:
        return state.find_pokemon(use.pokemon_id)[1]
    raise ValueError(f"ワザのダメージを受けるポケモンの種類 {target!r} は未実装（{DAMAGE_TARGETS}）")


@dataclass(frozen=True)
class DamageResult:
    """ワザのダメージの要素 1 つを処理した結果（v0.4d）。``deal_attack_damage`` が返す。

    ワザの後の要素（「ふきとばし」の入れ替え、「メガドレイン」の回復）が、直前のダメージの要素の結果を知るためのもの。
    ログを読み直して推定しない（ログは記録で、ルールの判断に使わない）。状態には残さない（ワザの処理の中だけで使う）。

    - ``target``: 受けるポケモンの種類（``OPPONENT_ACTIVE``・``SELF``）
    - ``player``・``pokemon_id``: 受けたポケモンの持ち主と、場のポケモンの番号。ダメージを与えたのは、いつもワザを使う
      ポケモン（``AttackUse.pokemon_id``。発生源なので、ここには重ねて持たない）
    - ``prevented``: 受けるポケモンが「ダメージを受けない」状態（v0.4b。持続する効果）で、この要素が無効になった。
      ダメージを計算していない（p.321）
    - ``amount``: p.321 の順番で計算した最終ダメージ（0 以下なら 0）。HP で上限を付けない（p.319「HPが30しかないから
      といって、「与えたダメージ」が30になるのではありません」）。``prevented`` なら None（計算していないので、量はない。
      計算した結果の 0 と区別する）
    - ``knocked_out``: この要素を処理したあと、受けたポケモンのダメージが HP 以上（p.323 できぜつする）。きぜつの処理
      （トラッシュ・サイド・交代）は、ワザの要素をすべて処理したあとでエンジンが行う（``engine._finish_attack``）
    """

    target: str
    player: int
    pokemon_id: int
    prevented: bool
    amount: int | None
    knocked_out: bool

    @property
    def dealt(self) -> int:
        """与えたダメージ。最終ダメージ（``amount``）。防いだとき・最終ダメージが 0 のときは 0（p.319「「0ダメージを受けた
        （与えた）」…のではなく、「ダメージを受けなかった（与えなかった）」ことになります」）。"""
        return 0 if self.amount is None else self.amount


def deal_attack_damage(state: GameState, use: AttackUse, target: str, base: int) -> DamageResult:
    """ワザのダメージを 1 つ与える: 受けるポケモンを決め、基本となるダメージ ``base`` から p.321 の順番で計算する。

    - ダメージを与えるのは、いつもワザを使うポケモン（発生源。弱点・抵抗力はそのタイプで見る。p.321 の 3・4 段階）。
    - 受けるポケモンは ``target``（``OPPONENT_ACTIVE`` か ``SELF``）。自分へのダメージも「ワザによるダメージ」
      （p.321「8 ワザによるダメージと効果」）なので、同じ順番で計算する。弱点・抵抗力（3・4 段階）は、ワザを使う
      ポケモンのタイプと、受けるポケモン（自分へのダメージなら自分）の弱点・抵抗力で見る（v0.3d。p.90 のわるい
      カメックスの解説「このワザによって、自分自身が受けるダメージは、「プラスパワー」、弱点・抵抗力などの影響を
      受けることです」。SUPPORTED。v0.2f〜v0.3c では、自分のタイプが自分の弱点・抵抗力のタイプなら止めていた）。
    - 変更効果は ``attack_damage_modifiers``: ワザを使うポケモンについているカードは 5 段階（プラスパワー）、
      受けるポケモンについているカードは 7 段階（ディフェンダー）。自分へのダメージでは同じポケモンが両方の
      立場になるが、カードはそれぞれ自分の立場でだけ効果を出す（プラスパワーは使う側、ディフェンダーは受ける側）
      ので、同じカードを二重に計算しない。p.257 の解説どおり、自分へのダメージはプラスパワーで +10、
      ディフェンダーで −20 される。

    ログの ``damage`` は v0.1 と同じ形（相手の対戦ポケモンへのダメージ）。変更効果を計算したときだけ ``modifiers``
    （v0.2c）、2 段階までで 0 以下になって計算を終えたときだけ ``stopped_after_step_2``（v0.2d）を加える。
    自分へのダメージ（v0.2f）には、``target``（``"self"``）・``pokemon_id``（受けたポケモン）・``effect``（ワザ）を加える。

    受けるポケモンが「ダメージを受けない」状態（v0.4b。持続する効果 ``PreventDamage``。「かたまる」）なら、このダメージの
    要素は無効（p.321「それを受けたポケモンが「ダメージを受けない」状態だったら、そのポケモンにダメージを与える「ワザの
    要素」は無効になります」）。ダメージを計算せず（p.321 の 8 段階のどれかで 0 にするのではない。変更効果・弱点・抵抗力も
    計算しない）、ダメージも変えず、ログ ``damage_prevented``（``player``・``pokemon``・``pokemon_id``・``target``・``effect``
    （ワザ）・``persistent_effect``・``source_card``）だけを残す。計算しないので、防いだダメージの量はない（ログに書かない）。
    ほかのポケモンへのダメージの要素・ダメージ以外の効果の要素は有効（p.321。ワザの実装が続けて処理する）。

    v0.4d から、処理の結果（``DamageResult``）を返す。ログ・ダメージの値・計算・乱数（使わない）は v0.4c と同じで、戻り値を
    使わない呼び出し側（v0.4c までのワザの実装）の動きは変わらない。
    """
    _, attacker = state.find_pokemon(use.pokemon_id)
    attacker_def = state.card_def(attacker.card)
    receiver = damage_receiver(state, use, target)
    receiver_player = use.player if target == SELF else 1 - use.player
    prevention = damage_prevention(state, receiver)
    if prevention is not None:
        state.add_event(
            "damage_prevented",
            player=receiver_player,
            pokemon=receiver.card,
            pokemon_id=receiver.pokemon_id,
            target=target,
            effect=str(use.key),
            persistent_effect=prevention.kind,
            source_card=prevention.source_card,
        )
        return DamageResult(target, receiver_player, receiver.pokemon_id, True, None, receiver.damage >= state.card_def(receiver.card).hp)
    receiver_def = state.card_def(receiver.card)
    modifiers = attack_damage_modifiers(state, attacker, receiver)
    calc = calculate_attack_damage(base, attacker_def, receiver_def, state.rules, modifiers)
    receiver.damage += calc.final
    extra = {}
    if calc.modifiers:
        # v0.2c: どのカードの効果を、どの段階で計算したか（変更効果がないときは v0.1 と同じ形）
        extra["modifiers"] = tuple((m.step, m.source, m.amount) for m in calc.modifiers)
    if calc.stopped_after_step_2:
        # v0.2d: 基本となるダメージ（と 2 段階）で 0 以下。弱点・抵抗力・5〜8 段階は計算していない（p.321）
        extra["stopped_after_step_2"] = True
    if target != OPPONENT_ACTIVE:
        # v0.2f: 相手の対戦ポケモン以外へのダメージ。受けたポケモン（場のポケモンの番号）とワザを書く
        extra.update(target=target, pokemon_id=receiver.pokemon_id, effect=str(use.key))
    state.add_event(
        "damage",
        player=receiver_player,
        pokemon=receiver.card,
        amount=calc.final,
        steps=calc.steps,
        weakness=calc.weakness_applied,
        resistance=calc.resistance_applied,
        total_damage=receiver.damage,
        **extra,
    )
    return DamageResult(target, receiver_player, receiver.pokemon_id, False, calc.final, receiver.damage >= receiver_def.hp)


def damage_opponent_active(state: GameState, use: AttackUse, base: int) -> DamageResult:
    """ワザで、相手の対戦ポケモンに、基本となるダメージ ``base`` から p.321 の順番で計算したダメージを与える（v0.4d から結果を返す）。"""
    return deal_attack_damage(state, use, OPPONENT_ACTIVE, base)


@dataclass(frozen=True)
class SelfDamageOnTails(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。そのあとコインを 1 枚投げ、「うら」なら自分にも
    ``self_damage`` ダメージ（v0.2f。ピカチュウの「でんげき」。p.125 の最新の説明
    「コインを投げて「うら」なら、自分にも10ダメージ。」。docs/pikachu-v0.2f.md・docs/self-damage-v0.2f.md）。

    - ダメージの目安に「×」「+」「−」がないので、説明の最初の「相手の対戦ポケモンに 30 ダメージ。」が省略されて
      いる（p.320）。ワザの要素は書いてある順番に処理する（p.320）: 相手へのダメージ → コイン → 自分へのダメージ。
    - 自分へのダメージは、p.320 のダメージの分類の (3)「このワザを使うポケモンへのダメージ」。ワザによるダメージ
      （p.321）なので、相手へのダメージと同じ p.321 の順番で計算する（``deal_attack_damage``）。
    - 相手のポケモンがこのワザできぜつしても、自分へのダメージの要素は無視しない（p.309「それ以降の内容を無視
      してはいけません」）。きぜつ・サイド・交代・勝敗は、ワザの処理のあとでエンジンがまとめて行う
      （1 つのワザできぜつしたポケモンは「同時」。p.324）。
    - 自分へのダメージも弱点・抵抗力の影響を受ける（v0.3d。p.90 の解説。``deal_attack_damage``）。v0.2f〜v0.3c では、
      自分のタイプが自分の弱点・抵抗力のタイプなら原典で決められないとして止めていた（ピカチュウでは起こらない）。
    """

    self_damage: int
    implementation_id = "self_damage_on_tails"

    def __post_init__(self) -> None:
        if type(self.self_damage) is not int or self.self_damage <= 0 or self.self_damage % 10:
            raise ValueError(f"自分へのダメージは 10 の倍数の正の数（{self.self_damage!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier is not None:
            problems.append(f"ダメージの目安に「{attack.damage_modifier}」があるワザを、目安の数字ぶんのダメージのワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、自分へのダメージのあるワザとして登録している")
        return problems

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
        damage_opponent_active(state, use, attack.damage)
        flips = flip_coins(
            state, use.player, 1, source="attack", effect=str(use.key), card=attacker.card, pokemon_id=attacker.pokemon_id
        )
        if flips.results[0] is CoinSide.TAILS:
            deal_attack_damage(state, use, SELF, self.self_damage)


@dataclass(frozen=True)
class PoisonOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。そのあとコインを 1 枚投げ、「おもて」なら相手の
    対戦ポケモンをどく状態にする（v0.3a。ビードルの「どくばり」。p.19 の最新の説明
    「コインを投げて「おもて」なら、相手を「どく」状態にする。」。docs/weedle-v0.3a.md）。

    - ダメージの目安に「×」「+」「−」がないので、説明の最初の「相手の対戦ポケモンに 10 ダメージ。」が省略されて
      いる（p.320）。ワザの要素は書いてある順番に処理する（p.309・p.320）: 相手へのダメージ → コイン → どく。
    - 説明の太字の「相手」は相手の対戦ポケモン（p.321）。特殊状態になるのもバトル場のポケモンだけ（p.322）。
    - どく状態にするのは「効果」で、ダメージではない。相手へのダメージが 0（ディフェンダーなど）でも、「おもて」なら
      どく状態にする。
    - 相手の対戦ポケモンが、このワザのダメージで HP 以上のダメージを受けたら、きぜつしている（p.323）。処理の
      対象がいなくなった内容は無視する（p.309）ので、コインを投げず、どく状態にもしない（どちらにしても、
      きぜつしたポケモンは場をはなれ、特殊状態は残らない。p.322）。きぜつの処理はワザのあとでエンジンが行う。
    - もうどく状態のポケモンなら、二重のどく状態にはならない（p.322。``conditions.poison``）。
    """

    implementation_id = "poison_on_heads"

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier is not None:
            problems.append(f"ダメージの目安に「{attack.damage_modifier}」があるワザを、目安の数字ぶんのダメージのワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、どく状態にするワザとして登録している")
        return problems

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
        damage_opponent_active(state, use, attack.damage)
        opponent = 1 - use.player
        target = state.players[opponent].active
        if target.damage >= state.card_def(target.card).hp:
            return  # 相手の対戦ポケモンはきぜつした。どく状態にする内容は対象がいないので無視する（p.309・p.323）
        flips = flip_coins(
            state, use.player, 1, source="attack", effect=str(use.key), card=attacker.card, pokemon_id=attacker.pokemon_id
        )
        if flips.results[0] is CoinSide.HEADS:
            poison(state, opponent, target, effect=str(use.key))


@dataclass(frozen=True)
class PoisonOpponent(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。そのあと、コインを投げずに相手の対戦ポケモンをどく状態にする
    （v0.5。フシギソウの「どくのこな」。p.14 の最新の説明「相手を「どく」状態にする。」・解説「確実に対戦ポケモンをどく状態に
    する「どくのこな」」。docs/bulbasaur-line-v0.5.md）。

    - ダメージの目安に「×」「+」「−」がないので、説明の最初の「相手の対戦ポケモンに 20 ダメージ。」が省略されている（p.320）。
      ダメージの処理をしてから、どく状態にする（p.309 の手順 6）。
    - コインを投げない（説明にコインがない）ので、乱数を使わない。コインを投げる ``PoisonOnHeads``（v0.3a）とは別の実装。
    - どく状態にするのは「効果」で、ダメージではない。最終ダメージが 0（ディフェンダーなど）でも、「ダメージを受けない」状態
      （v0.4b。「（ダメージ以外の効果は受ける）」）でも、どく状態にする（p.321）。
    - 相手の対戦ポケモンが、このワザのダメージできぜつしたら、処理の対象がいないので、どく状態にしない（p.309・p.323。
      ``PoisonOnHeads`` と同じ）。
    - もうどく状態のポケモンなら、二重のどく状態にはならない（p.322。``conditions.poison`` がログに ``already``）。
    """

    implementation_id = "poison_opponent"

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier is not None:
            problems.append(f"ダメージの目安に「{attack.damage_modifier}」があるワザを、目安の数字ぶんのダメージのワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、どく状態にするワザとして登録している")
        return problems

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
        result = damage_opponent_active(state, use, attack.damage)
        if result.knocked_out:
            return  # 相手の対戦ポケモンはきぜつした。どく状態にする内容は対象がいないので無視する（p.309・p.323）
        opponent = 1 - use.player
        poison(state, opponent, state.players[opponent].active, effect=str(use.key))


@dataclass(frozen=True)
class ParalyzeOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。そのあとコインを 1 枚投げ、「おもて」なら相手の
    対戦ポケモンをマヒ状態にする（v0.3b。キャタピーの「いとをはく」。p.17 の最新の説明
    「コインを投げて「おもて」なら、相手を「マヒ」状態にする。」。docs/cards-v0.3b.md）。

    - ダメージの目安に「×」「+」「−」がないので、説明の最初の「相手の対戦ポケモンに 10 ダメージ。」が省略されて
      いる（p.320。シードラの「あわ」の例: 「相手（太字）に10ダメージ。コインを投げて『おもて』なら、相手を『マヒ』状態に
      する。」）。ワザの要素は書いてある順番に処理する（p.309・p.320）: 相手へのダメージ → コイン → マヒ。
    - マヒ状態にするのは「効果」で、ダメージではない。相手へのダメージが 0（ディフェンダーなど）でも、「おもて」なら
      マヒ状態にする。
    - 相手の対戦ポケモンが、このワザのダメージできぜつしたら、処理の対象がいないのでコインを投げない（p.309・p.323。
      ``PoisonOnHeads`` と同じ）。
    - マヒ状態のポケモンが再びマヒ状態になる効果を受けて、回復する番が原典で決められない場合は、コインを投げる前に
      止める（``conditions.paralysis_problem``）。このワザ（相手の対戦ポケモンだけをマヒにする）では、不変条件を満たす
      どの状態でも起こらない（v0.3d で証明した: 相手のマヒは、相手の番の終わりまでに回復するので、自分の番に残っている
      のは今の番か前の番（相手の番）にマヒ状態になった場合だけで、どちらも回復する番は今の番 + 1 になり、同じ）。
      そのため ``problem`` は持たない（こんらんの「おもて」のあとでこの確認が働くこともない）。
      docs/effect-preflight-v0.3d.md・tests/test_effect_preflight_v0_3d.py。
    - ねむり状態の相手なら、ねむりは消えてマヒ状態になる。どく状態はそのまま（p.322。``conditions.paralyze``）。
    """

    implementation_id = "paralyze_on_heads"

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier is not None:
            problems.append(f"ダメージの目安に「{attack.damage_modifier}」があるワザを、目安の数字ぶんのダメージのワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、マヒ状態にするワザとして登録している")
        return problems

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
        damage_opponent_active(state, use, attack.damage)
        opponent = 1 - use.player
        target = state.players[opponent].active
        if target.damage >= state.card_def(target.card).hp:
            return  # 相手の対戦ポケモンはきぜつした。マヒ状態にする内容は対象がいないので無視する（p.309・p.323）
        # 原典で決められない場合は、コインの前に止める（apply_command は複製した状態で処理するので、ダメージも残らない）
        problem = paralysis_problem(state, opponent, target)
        if problem is not None:
            raise problem
        flips = flip_coins(
            state, use.player, 1, source="attack", effect=str(use.key), card=attacker.card, pokemon_id=attacker.pokemon_id
        )
        if flips.results[0] is CoinSide.HEADS:
            paralyze(state, opponent, target, effect=str(use.key))


@dataclass(frozen=True)
class PutToSleep(AttackEffect):
    """ダメージを与えず、相手の対戦ポケモンをねむり状態にする（v0.3b。パラスの「キノコのほうし」。p.38 の最新の説明
    「相手を「ねむり」状態にする。」。docs/cards-v0.3b.md）。

    - ダメージの目安の数字がないワザ（データの ``damage`` が None）だけを登録できる。「ダメージ 0」のワザ
      （``DamageOnly`` に 0 を渡すこと）とは違い、ダメージの要素がない: ダメージの計算（p.321）をせず、``damage`` の
      ログもない。p.320 のとおり、説明の最初に省略されている「相手に○○ダメージ。」は、目安の数字があるときのもの。
      p.38 の解説も「相手の対戦ポケモンを確実にねむり状態にできるのですが、ダメージを与えることはできません」。
    - コインは投げない（説明にない）。ワザの「失敗」（p.323）もない。
    - もうねむり状態なら二重にならない。マヒ状態なら、マヒは消えてねむり状態になる。どく状態はそのまま（p.322。
      ``conditions.put_to_sleep``）。
    """

    implementation_id = "put_to_sleep"

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage is not None or attack.damage_display is not None or attack.damage_modifier is not None:
            problems.append("ダメージの目安のあるワザを、ダメージを与えずにねむり状態にするワザとして登録している")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、ねむり状態にするワザとして登録している")
        return problems

    def resolve(self, state: GameState, use: AttackUse) -> None:
        opponent = 1 - use.player
        put_to_sleep(state, opponent, state.players[opponent].active, effect=str(use.key))


@dataclass(frozen=True)
class ConfuseOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。そのあとコインを 1 枚投げ、「おもて」なら相手の
    対戦ポケモンをこんらん状態にする（v0.3c。ロコンの「あやしいひかり」。p.67 の最新の説明
    「コインを投げて「おもて」なら、相手を「こんらん」状態にする。」。docs/confusion-v0.3c.md）。

    - ダメージの目安に「×」「+」「−」がないので、説明の最初の「相手の対戦ポケモンに 10 ダメージ。」が省略されて
      いる（p.320）。ワザの要素は書いてある順番に処理する（p.309・p.320）: 相手へのダメージ → コイン → こんらん。
    - こんらん状態にするのは「効果」で、ダメージではない。相手へのダメージが 0（ディフェンダーなど）でも、「おもて」
      ならこんらん状態にする。
    - 相手の対戦ポケモンが、このワザのダメージできぜつしたら、処理の対象がいないのでコインを投げない（p.309・p.323。
      ``PoisonOnHeads``・``ParalyzeOnHeads`` と同じ）。
    - もうこんらん状態なら二重にならない。ねむり・マヒ状態なら、それが消えてこんらん状態になる。どく状態はそのまま
      （p.322。``conditions.confuse``）。
    - このコインは、ワザの説明のコイン（``source: "attack"``）。ワザを使うポケモン自身がこんらん状態のときの
      判定のコイン（``source: "confusion"``。エンジンが投げる）とは別。
    """

    implementation_id = "confuse_on_heads"

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier is not None:
            problems.append(f"ダメージの目安に「{attack.damage_modifier}」があるワザを、目安の数字ぶんのダメージのワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、こんらん状態にするワザとして登録している")
        return problems

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
        damage_opponent_active(state, use, attack.damage)
        opponent = 1 - use.player
        target = state.players[opponent].active
        if target.damage >= state.card_def(target.card).hp:
            return  # 相手の対戦ポケモンはきぜつした。こんらん状態にする内容は対象がいないので無視する（p.309・p.323）
        flips = flip_coins(
            state, use.player, 1, source="attack", effect=str(use.key), card=attacker.card, pokemon_id=attacker.pokemon_id
        )
        if flips.results[0] is CoinSide.HEADS:
            confuse(state, opponent, target, effect=str(use.key))


@dataclass(frozen=True)
class PreventDamageOnHeads(AttackEffect):
    """コインを 1 枚投げ、「おもて」なら、次の相手の番、このワザを使ったポケモンは「ダメージを受けない」状態になる
    （v0.4b。トランセル・コクーンの「かたまる」。p.18・p.21 の最新の説明「コインを投げて「おもて」なら、次の相手の番、
    このカードはダメージを受けない。（ダメージ以外の効果は受ける）」。docs/harden-v0.4b.md）。

    - ダメージの目安の数字がないワザ（データの ``damage`` が None）だけを登録できる。ダメージの要素はなく、p.320 の効果の
      分類の (3)「このワザを使うポケモンへの効果（次の番にワザを受けない…など）」だけ。コインは 1 枚（説明の「コインを
      投げて」）。「うら」なら何もしない（説明にない。ワザは使ったことになり、番は終わる。ワザの「失敗」（p.323）ではない）。
    - 「おもて」なら、持続する効果 ``PreventDamage`` を自分（ワザを使ったポケモン）に与える（p.322「「ラッキー」の「まる
      まる」などのようなワザは、自分自身に「持続する効果」を与えます」。p.236 のワザ解説は「まるまる」と同じタイプのワザに
      「かたまる」を挙げる）。効果がはたらくのは次の相手の番（今の番 + 1。番は交互に進む）で、その番の終わりに消える
      （``persistent.remove_expired_persistent_effects``）。ダメージの扱いは ``deal_attack_damage``（p.321）。
    - 「おもて」でなくても、今ある持続する効果は消さない（説明にない。p.323「別の「持続する効果」を受けたからといって、
      それまで受けていた「持続する効果」が消えることはありません」）。
    - こんらん状態のポケモンが使ったら、エンジンが先にこんらんのコインを投げ、「おもて」のときだけここに来る（p.309 の
      手順 5・6）。「うら」ならこのコインは投げない。
    """

    implementation_id = "prevent_damage_on_heads"

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage is not None or attack.damage_display is not None or attack.damage_modifier is not None:
            problems.append("ダメージの目安のあるワザを、ダメージを与えずに「ダメージを受けない」状態になるワザとして登録している")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、「ダメージを受けない」状態になるワザとして登録している")
        return problems

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _, attacker = state.find_pokemon(use.pokemon_id)
        flips = flip_coins(
            state, use.player, 1, source="attack", effect=str(use.key), card=attacker.card, pokemon_id=attacker.pokemon_id
        )
        if flips.results[0] is CoinSide.HEADS:
            effect = PreventDamage(
                source_card=attacker.card,
                source_player=use.player,
                created_turn=state.turn_number,
                active_turn=state.turn_number + 1,  # 次の相手の番（番は先攻から 1 つずつ交互に進む。不変条件で確かめている）
            )
            add_persistent_effect(state, use.player, attacker, effect, attack=str(use.key))


# 「ふきとばし」で入れ替えなかった理由（ログ forced_switch_skipped の reason。v0.4d）
TARGET_KNOCKED_OUT = "knocked_out"  # 相手の対戦ポケモンがこのワザのダメージできぜつする（効果の対象がいない。p.309・p.213）
NO_BENCH = "no_bench"  # 相手に控えポケモンがいない（最新の説明「相手に控えがいないとき、入れ替えはおこらない」）


def _check_damage_then_effect(attack: Attack, what: str) -> list[str]:
    """ダメージの目安の数字ぶんのダメージのあとに効果のあるワザの、データの形の確認（v0.4d）。"""
    problems = []
    if attack.damage_modifier is not None:
        problems.append(f"ダメージの目安に「{attack.damage_modifier}」があるワザを、目安の数字ぶんのダメージのワザとして登録している")
    if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
        problems.append("ダメージが 10 の倍数の正の数ではない")
    if attack.text_ja is None:
        problems.append(f"説明文のないワザを、{what}ワザとして登録している")
    return problems


@dataclass(frozen=True)
class DamageAndForceSwitch(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。そのあと、相手の対戦ポケモンをベンチにもどし、相手が選んだ
    控えポケモンと入れ替える（v0.4d。バタフリーの「ふきとばし」。p.19 の最新の説明「相手を控えポケモンと入れ替える。入れ替わる
    ポケモンは、相手が選ぶ。（相手に控えがいないとき、入れ替えはおこらない）」。docs/forced-switch-v0.4d.md）。

    - ダメージの目安に「×」「+」「−」がないので、説明の最初の「相手の対戦ポケモンに 20 ダメージ。」が省略されている（p.320）。
      ダメージと効果の両方があるので、ダメージの処理をしてから入れ替える（p.309 の手順 6「まず、ダメージの処理をおこない、次に
      「それ以外の効果」を処理してください」。p.89 の解説「「ふきとばし」のダメージを受けたタイミングでは、まだバトル場にいる」）。
    - 効果の対象は相手の対戦ポケモンで、効果はそれをベンチにもどすこと（p.213 のワザ解説「このワザの効果は、相手の対戦ポケモン
      が対象であり、相手の対戦ポケモンをベンチにもどすというものです。入れ替えることが効果ではありません」。p.159 も
      「「ふきとばし」は、相手の対戦ポケモンへの効果です」）。もどしたあと、相手が控えポケモンから 1 匹を選んでバトル場に
      出す（p.213「相手プレイヤーは、ベンチの控えポケモンから1匹を選んでバトル場に出す」。p.19 の解説「入れ替える相手のポケモン
      は自分で選べないからです」）。選ぶのは相手なので、決定
      （``FORCED_SWITCH``）の ``player`` は相手。番のプレイヤーはワザを使ったプレイヤーのまま。選べるものは相手のベンチの
      ポケモンの番号（もどしたポケモンは選べない）。控えが 1 匹でも決定を出す（実装上の仮定。結果は同じで、きぜつのあとの
      交代（``PROMOTE_ACTIVE``）と同じ形）。
    - 相手に控えポケモンがいなければ、入れ替えはおこらない（最新の説明）。決定を出さず、ダメージだけでワザを終える。
      トレーナーの「ポケモンいれかえ」の ``UNRESOLVED_SWITCH_WITHOUT_BENCH``（使えるかが決められない）とは別の規定。
    - 相手の対戦ポケモンが、このワザのダメージで HP 以上のダメージを受けたら、きぜつする（p.323）。効果の対象（相手の対戦
      ポケモン）がいなくなったので、入れ替える内容は無視する（p.309「処理の対象がなくなってしまっている場合、その内容は無視
      して」。p.89「そのダメージできぜつしなければ「スターブーメラン」の効果で手札にもどる」。SUPPORTED。``PoisonOnHeads`` と
      同じ扱い）。決定は出さず、ワザのあとのきぜつ・サイド・交代（相手がバトル場に出すポケモンを選ぶ）はエンジンが行う。
      入れ替えてからきぜつさせる読み方でも、相手が控えから選んだポケモンがバトル場に出て、きぜつしたポケモンをトラッシュし、
      サイドを 1 枚取る結果は同じ（docs/forced-switch-v0.4d.md 4 章）。
    - 「ダメージを受けない」状態（v0.4b）の相手なら、ダメージの要素は無効だが、入れ替えは「ダメージ以外の効果」なので有効
      （p.321。「かたまる」の最新の説明「（ダメージ以外の効果は受ける）」）。最終ダメージが 0 でも入れ替える（入れ替えはダメージを
      与えたことを条件にしていない）。
    - 入れ替えは「にげる」ではない（p.325）。にげるエネルギーを払わず、こんらんのコインを投げず、「にげる」の失敗の記録も
      付けない。ねむり・マヒ状態のポケモンも入れ替える（p.325「「にげる」がおこなえない状態のポケモンでも、「そのポケモンを
      入れ替える」と指示されたときは、入れ替えをおこないます」）。
    - ベンチにもどったポケモンの特殊状態（p.311・p.322）とワザによる持続する効果（p.311・p.322・p.89）は消える（理由
      ``FORCED_SWITCH``）。ダメージ・エネルギー・ついているトレーナー（有効期限も）・進化の重なり・場のポケモンの番号・場に出た番・
      進化した番は変わらない（p.311「ついているカード・ダメージカウンターは、いっしょに移動する」）。こんらんで「にげる」に失敗
      した記録（``retreat_failed_turn``）は、ワザを使った番には相手のポケモンにない（記録は番のプレイヤーのポケモンにだけ付き、
      番の終わりに消える。不変条件で確かめている）ので、ここでは扱わない。
    - ログ: 入れ替えたら ``forced_switch``（``player``（入れ替えられたプレイヤー）・``attacker``（ワザを使ったプレイヤー）・
      ``attacker_pokemon_id``・``effect``（ワザの ``AttackKey``）・``old_active``・``new_active``・``old_active_pokemon_id``・
      ``new_active_pokemon_id``）。入れ替えなかったら ``forced_switch_skipped``（``player``・``attacker``・``attacker_pokemon_id``・
      ``effect``・``pokemon``・``pokemon_id``・``reason``（``TARGET_KNOCKED_OUT``・``NO_BENCH``））。トレーナーの ``switch`` の
      ログの形は変えない。
    """

    implementation_id = "damage_and_force_switch"

    def check(self, attack: Attack) -> list[str]:
        return _check_damage_then_effect(attack, "相手を控えポケモンと入れ替える")

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
        result = damage_opponent_active(state, use, attack.damage)
        opponent = 1 - use.player
        p = state.players[opponent]
        target = p.active
        if result.knocked_out:
            # 相手の対戦ポケモンはきぜつした。ベンチにもどす内容は対象がいないので無視する（p.309・p.323・p.213・p.89）
            self._skip(state, use, target, TARGET_KNOCKED_OUT)
            return
        if not p.bench:
            self._skip(state, use, target, NO_BENCH)  # 「相手に控えがいないとき、入れ替えはおこらない」（最新の説明）
            return
        push_attack_decision(
            state,
            use,
            kind=FORCED_SWITCH,
            player=opponent,
            options=[pokemon.pokemon_id for pokemon in p.bench],
            context=(("target", target.pokemon_id),),
        )

    def resume(self, state: GameState, use: AttackUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        opponent = 1 - use.player
        p = state.players[opponent]
        old = p.active
        if old is None or old.pokemon_id != decision.context_value("target"):
            raise RuntimeError(f"「ふきとばし」の対象 {decision.context_value('target')} が相手のバトル場にいない（エンジンの不具合）")
        index = next(i for i, pokemon in enumerate(p.bench) if pokemon.pokemon_id == choices[0])
        # 場のポケモンごと入れ替えるので、ダメージ・エネルギー・ついているカード・重なり・番号はいっしょに移る（p.311）
        p.active, p.bench[index] = p.bench[index], old
        state.add_event(
            "forced_switch",
            player=opponent,
            attacker=use.player,
            attacker_pokemon_id=use.pokemon_id,
            effect=str(use.key),
            old_active=old.card,
            new_active=p.active.card,
            old_active_pokemon_id=old.pokemon_id,
            new_active_pokemon_id=p.active.pokemon_id,
        )
        # ベンチにもどったポケモンの特殊状態と、ワザによる持続する効果は消える（p.311・p.322。別々の処理）
        clear_special_conditions(state, opponent, old, FORCED_SWITCH_REASON)
        remove_persistent_effects(state, opponent, old, FORCED_SWITCH_REASON)

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        """「ふきとばし」の決定を待っている状態の確認: 種類は ``FORCED_SWITCH``、決定するのは相手（ワザを使ったプレイヤーではない）、
        1 匹だけ選ぶ、対象（``context`` の ``"target"``）が相手のバトル場のポケモン、選べるものが相手のベンチのポケモンの番号と同じ。"""
        opponent = 1 - use.player
        p = state.players[opponent]
        problems = []
        if decision.kind != FORCED_SWITCH:
            problems.append(f"「ふきとばし」の決定の種類が {decision.kind!r}（{FORCED_SWITCH} のはず）")
        if decision.player != opponent:
            problems.append(f"「ふきとばし」で入れ替わるポケモンを選ぶのが、相手 {opponent} ではなくプレイヤー {decision.player}")
        if (decision.min_choices, decision.max_choices) != (1, 1):
            problems.append(f"「ふきとばし」で選ぶ数が {decision.min_choices}〜{decision.max_choices}（1 匹のはず）")
        if p.active is None or p.active.pokemon_id != decision.context_value("target"):
            problems.append(f"「ふきとばし」の対象 {decision.context_value('target')!r} が、相手のバトル場のポケモンではない")
        if not p.bench or decision.options != tuple(pokemon.pokemon_id for pokemon in p.bench):
            problems.append(f"「ふきとばし」の決定の選べるもの {decision.options} が、相手のベンチのポケモンと合わない")
        return problems

    @staticmethod
    def _skip(state: GameState, use: AttackUse, target: PokemonInPlay, reason: str) -> None:
        state.add_event(
            "forced_switch_skipped",
            player=1 - use.player,
            attacker=use.player,
            attacker_pokemon_id=use.pokemon_id,
            effect=str(use.key),
            pokemon=target.card,
            pokemon_id=target.pokemon_id,
            reason=reason,
        )


@dataclass(frozen=True)
class DamageAndDrain(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。相手にダメージを与えたら、与えたダメージの半分（ダメージカウンターの
    単位で切り上げ）のダメージカウンターを、ワザを使ったポケモン自身からとりのぞく（v0.4d。バタフリーの「メガドレイン」。p.19 の
    最新の説明「相手にダメージを与えたら、その半分（切り上げ）のダメージカウンターを、自分からとりのぞく。」。
    docs/damage-drain-v0.4d.md）。

    - ダメージの要素は ``damage_opponent_active``（p.321 の順番。弱点・抵抗力・プラスパワー・ディフェンダーを計算する）。
    - 「与えたダメージ」は最終ダメージ（``DamageResult.dealt``）。相手の残りの HP で上限を付けない（p.319「HPが30のポケモンに
      対して50ダメージを与えるワザを使ったとき、「与えたダメージ」はあくまでも50です」）。相手がきぜつしても回復する（回復の
      対象は自分で、いなくなっていない。p.309。SUPPORTED）。
    - 最終ダメージが 0 以下なら「ダメージを与えなかった」（p.319）ので、「相手にダメージを与えたら」を満たさず、回復しない
      （CONFIRMED）。相手が「ダメージを受けない」状態（v0.4b）でダメージの要素が無効なら、ダメージを与えていないので回復しない
      （p.321・p.319。SUPPORTED。ダメージ以外の効果は有効という規定（p.321）は、この回復の条件を満たすことにはならない）。
      どちらもログ ``drain_heal`` を残さない（ダメージの要素のログ ``damage``（``amount`` 0）・``damage_prevented`` が理由を示す）。
    - 回復するダメージカウンターの数は、与えたダメージの半分を、ダメージカウンター 1 個 = 10 ダメージ（p.319）の単位で切り上げ
      たもの（与えたダメージのカウンターの数 n の半分の切り上げ ``(n + 1) // 2`` と同じ。40 → 2 個、30 → 2 個、10 → 1 個）。
    - とりのぞけるのは、ワザを使ったポケモン（場のポケモンの番号 ``AttackUse.pokemon_id``。進化していれば重なりのいちばん上の
      カードが表すポケモン。p.19 の解説「この「バタフリー」自身からとりのぞける」）にのっているダメージカウンターだけ。のっている数より多くはとりのぞかない（p.320「ポケモンからすべての
      ダメージカウンターを取りのぞいてしまったら、もうそれ以上の回復はできません」）。のっていなければ 0 個（ログは残す）。
    - 回復はワザの要素の 1 つで、きぜつの判定はワザのあと（``engine._finish_attack``）。乱数は使わない。
    - ログ ``drain_heal``（``player``・``pokemon``・``pokemon_id``・``effect``（ワザ）・``dealt``（回復の計算のもとにした与えた
      ダメージ）・``drain_counters``（半分の切り上げ）・``counters``（実際にとりのぞいた数）・``amount``（とりのぞいたダメージ）・
      ``damage_before``・``total_damage``（とりのぞいたあと））。トレーナーの「きずぐすり」のログ ``remove_damage_counters`` の
      形は変えない。
    - こんらん状態のバタフリーがワザを使い、こんらんのコインが「うら」なら、エンジンがこのワザの処理を呼ばない（ダメージも回復も
      ない。p.309 の手順 5）。
    """

    implementation_id = "damage_and_drain"

    def check(self, attack: Attack) -> list[str]:
        return _check_damage_then_effect(attack, "与えたダメージの半分を回復する")

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
        result = damage_opponent_active(state, use, attack.damage)
        if result.dealt <= 0:
            return  # ダメージを与えなかった（防いだ・最終ダメージ 0）。回復の条件「相手にダメージを与えたら」を満たさない
        per_counter = state.rules.damage_per_counter
        if result.dealt % per_counter:
            raise RuntimeError(f"与えたダメージ {result.dealt} がダメージカウンターの単位 {per_counter} の倍数ではない（エンジンの不具合）")
        drain_counters = (result.dealt // per_counter + 1) // 2  # 与えたダメージの半分（カウンターの単位で切り上げ）
        _remove_attacker_counters(state, use, attacker, result.dealt, drain_counters)


def _remove_attacker_counters(state: GameState, use: AttackUse, attacker: PokemonInPlay, dealt: int, counters: int) -> None:
    """ワザを使ったポケモン自身から、ダメージカウンターを ``counters`` 個まで（のっている数まで）とりのぞき、ログ ``drain_heal`` を
    残す（v0.4d のメガドレイン。v0.5 のやどりぎのタネも同じ形。``drain_counters`` は説明が決めた数、``counters`` は実際にとりのぞいた
    数）。のっている数より多くはとりのぞかない（p.320）。"""
    per_counter = state.rules.damage_per_counter
    before = attacker.damage
    removed = min(counters, before // per_counter)
    attacker.damage = before - removed * per_counter
    state.add_event(
        "drain_heal",
        player=use.player,
        pokemon=attacker.card,
        pokemon_id=attacker.pokemon_id,
        effect=str(use.key),
        dealt=dealt,
        drain_counters=counters,
        counters=removed,
        amount=removed * per_counter,
        damage_before=before,
        total_damage=attacker.damage,
    )


@dataclass(frozen=True)
class DamageAndRemoveCounters(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。相手にダメージを与えたら、ワザを使ったポケモン自身にのっている
    ダメージカウンターを ``counters`` 個とりのぞく（v0.5。フシギダネの「やどりぎのタネ」。p.13 の最新の説明「相手にダメージを
    与えたら、自分にのっているダメージカウンターを1個とりのぞく。」。docs/bulbasaur-line-v0.5.md）。

    - 「与えたダメージ」は v0.4d の ``DamageResult.dealt``（最終ダメージ）。最終ダメージが 0 以下・「ダメージを受けない」状態で
      ダメージを与えなかったら、とりのぞかない（p.319・p.321。p.13 の解説「このワザはダメージを与えないと、自分のダメージ
      カウンターを取れないので、相手のポケモンが「ディフェンダー」などを使ってダメージを与えられなかった場合は、ダメージ
      カウンターを取りのぞくことができません」。CONFIRMED（解説））。
    - とりのぞく数は与えたダメージの量によらず ``counters``（1 個）。のっている数より多くはとりのぞかない（p.320）。のっていな
      ければ 0 個（ログは残す）。印刷の文面は「…とりのぞくことができる」だが、最新の説明は「とりのぞく」なので、選ばずにとり
      のぞく（最新の説明にしたがう）。
    - 相手がきぜつしても、とりのぞく（対象は自分で、いなくなっていない。p.309。メガドレインと同じ。SUPPORTED）。
    - ログはメガドレインと同じ ``drain_heal``（``drain_counters`` は ``counters``）。乱数は使わない。
    """

    counters: int
    implementation_id = "damage_and_remove_counters"

    def __post_init__(self) -> None:
        if type(self.counters) is not int or self.counters < 1:
            raise ValueError(f"とりのぞくダメージカウンターの数は 1 以上の整数（{self.counters!r}）")

    def check(self, attack: Attack) -> list[str]:
        return _check_damage_then_effect(attack, "ダメージを与えたら自分のダメージカウンターをとりのぞく")

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
        result = damage_opponent_active(state, use, attack.damage)
        if result.dealt <= 0:
            return  # ダメージを与えなかった（防いだ・最終ダメージ 0）。とりのぞく条件「相手にダメージを与えたら」を満たさない
        _remove_attacker_counters(state, use, attacker, result.dealt, self.counters)


@dataclass(frozen=True)
class ExtraEnergyDamage(AttackEffect):
    """ワザに必要なエネルギーよりも多く ``energy_type`` のエネルギーがついているとき、多いエネルギー 1 個につき ``per_energy``
    ダメージを、``max_extra`` 個ぶんまで追加する（v0.6。カメックスの「ハイドロポンプ」。p.90 の最新の説明「ワザに必要なエネルギー
    よりも多く「水」エネルギーがついているとき、多い「水」エネルギー1個につき、10ダメージを追加する。ダメージ追加は2個ぶんまで。」。
    docs/rain-dance-v0.6.md 4 章）。

    - ダメージの目安「40+」の「+」は、説明にしたがって目安の数字より大きくなることがある（p.320）。説明にしたがった計算が
      p.321 の 1 段階（基本となるダメージ）で、そのあと弱点・抵抗力・プラスパワーなどを計算する（v0.2d の「×」と同じ）。
    - 多いエネルギーの数は、ついている ``energy_type`` のエネルギーの数から、ワザに必要なエネルギーの数を引いたもの（0 より
      少なければ 0）。必要なエネルギーがすべて ``energy_type`` のワザだけを登録できる（``check``。無色が混ざると、どのエネルギーで
      払ったかで「多い」数が変わりうるので、この実装では扱わない）。p.88 の解説（サザンアイランドのカメールのページ）「「カメックス」に
      進化して「ハイドロポンプ」を使えば、同じ水エネルギー4個で50ダメージ」「水エネルギー5個までなら…「ハイドロポンプ」で活用できる」
      と合う。
    - ついているエネルギーは基本エネルギーだけ（1 枚 1 個）。乱数は使わない。
    """

    energy_type: EnergyType
    per_energy: int
    max_extra: int
    implementation_id = "extra_energy_damage"

    def __post_init__(self) -> None:
        if type(self.per_energy) is not int or self.per_energy <= 0 or self.per_energy % 10:
            raise ValueError(f"エネルギー 1 個あたりの追加のダメージは 10 の倍数の正の数（{self.per_energy!r}）")
        if type(self.max_extra) is not int or self.max_extra < 1:
            raise ValueError(f"追加するエネルギーの上限は 1 以上の整数（{self.max_extra!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier != "+":
            problems.append("ダメージの目安に「+」のないワザを、エネルギーの数でダメージを追加するワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、エネルギーの数でダメージを追加するワザとして登録している")
        if not attack.cost or any(cost is not self.energy_type for cost in attack.cost):
            problems.append(f"必要なエネルギーが「{self.energy_type.ja}」だけではないワザを登録している（多いエネルギーの数え方が決まらない）")
        return problems

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
        attached = sum(1 for uid in attacker.energy if state.card_def(uid).provides is self.energy_type)
        extra = min(max(0, attached - len(attack.cost)), self.max_extra)
        damage_opponent_active(state, use, attack.damage + extra * self.per_energy)


@dataclass(frozen=True)
class DiscardEnergyAndRemoveAllCounters(AttackEffect):
    """ワザを使うポケモン自身についている ``energy_type`` のエネルギーカードを 1 枚トラッシュして、自分にのっているダメージ
    カウンターをすべてとりのぞく（v0.7。ユンゲラーの「じこさいせい」。p.151 の最新の説明「自分についている「超」エネルギーカードを
    1枚トラッシュして、自分にのっているダメージカウンターを、すべてとりのぞく。トラッシュできないとき、このワザの効果はなくなる。」。
    docs/alakazam-line-v0.7.md）。

    - ダメージの目安の数字がないワザ（データの ``damage`` が None）だけを登録できる（ダメージの要素がない。``PutToSleep`` と同じ）。
      要素はどちらも「このワザを使うポケモンへの効果」（p.320 の効果の (3)）で、書いてある順番に処理する（p.309）: トラッシュ →
      とりのぞく。
    - トラッシュするカードは、ワザを使うプレイヤーが、ついている ``energy_type`` の基本エネルギーカードから 1 枚選ぶ（決定
      ``DISCARD_ENERGY``。選べるものはカードの uid で、ついている順。SUPPORTED: 説明は選ぶ人を書かないが、ワザの説明の処理はワザを
      使うプレイヤーが行い、p.311 の「にげる」も「ついているエネルギーの中から選んで」トラッシュする）。同じ種類のカードでも別の
      カードなので、1 枚しかなくても決定を出す（実装上の仮定。結果は同じ。v0.4d の ``FORCED_SWITCH`` と同じ形）。
    - 「トラッシュできないとき、このワザの効果はなくなる」: ワザに必要なエネルギー（``check`` で ``energy_type`` を 1 個以上含むことを
      確かめる）が、ついている ``energy_type`` の基本エネルギーカードでしか払えないあいだは起こらない（特殊エネルギーは未実装）。
      起こったらエンジンの不具合として ``RuntimeError``（確かめていない処理を黙って行わない。特殊エネルギーを加えるときに、
      この場合の処理とテストを加える）。
    - とりのぞくのは、のっているダメージカウンターすべて（0 個なら 0 個。p.320「すべて取りのぞいてしまったら、もうそれ以上の回復は
      できません」）。のっていなくてもワザは使える（説明に使うための条件がない。p.309。SUPPORTED）。とりのぞくのは回復で、ダメージ
      の計算（p.321）はしない。
    - こんらん状態のユンゲラーがワザを使い、こんらんのコインが「うら」なら、エンジンがこのワザの処理を呼ばない（決定も出ない。
      p.309 の手順 5）。乱数は使わない。
    - ログ: トラッシュしたら ``discard_energy``（``player``・``pokemon``・``pokemon_id``・``effect``（ワザ）・``energy``）、とりのぞいたら
      ``remove_all_damage_counters``（``player``・``pokemon``・``pokemon_id``・``effect``・``counters``・``amount``・``damage_before``・
      ``total_damage``（0））。「きずぐすり」の ``remove_damage_counters``・メガドレインの ``drain_heal`` とは別。
    """

    energy_type: EnergyType
    implementation_id = "discard_energy_and_remove_all_counters"

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage is not None or attack.damage_display is not None or attack.damage_modifier is not None:
            problems.append("ダメージの目安のあるワザを、ダメージを与えずに自分のダメージカウンターをとりのぞくワザとして登録している")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、エネルギーをトラッシュしてダメージカウンターをとりのぞくワザとして登録している")
        if self.energy_type not in attack.cost:
            problems.append(f"必要なエネルギーに「{self.energy_type.ja}」がないワザを登録している（トラッシュできない場合が起こりうる）")
        return problems

    def _candidates(self, state: GameState, attacker: PokemonInPlay) -> list[int]:
        return [
            uid for uid in attacker.energy if state.card_def(uid).is_basic_energy and state.card_def(uid).provides is self.energy_type
        ]

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _, attacker = state.find_pokemon(use.pokemon_id)
        candidates = self._candidates(state, attacker)
        if not candidates:
            raise RuntimeError(
                f"ワザ {use.key} を使ったポケモン {use.pokemon_id} に「{self.energy_type.ja}」エネルギーカードがない"
                "（必要なエネルギーを払えたのに。エンジンの不具合）"
            )
        push_attack_decision(state, use, kind=DISCARD_ENERGY, player=use.player, options=candidates)

    def resume(self, state: GameState, use: AttackUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        owner, attacker = state.find_pokemon(use.pokemon_id)
        energy = choices[0]
        if energy not in self._candidates(state, attacker):
            raise RuntimeError(f"トラッシュに選んだカード {energy} が、ワザを使ったポケモンについていない（エンジンの不具合）")
        # 1. 自分についている「超」エネルギーカードを 1 枚トラッシュする（同じ uid のカードを、持ち主のトラッシュへ）
        attacker.energy.remove(energy)
        state.players[owner].discard.append(energy)
        state.add_event(
            "discard_energy", player=use.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(use.key), energy=energy
        )
        # 2. 自分にのっているダメージカウンターを、すべてとりのぞく
        per_counter = state.rules.damage_per_counter
        before = attacker.damage
        attacker.damage = 0
        state.add_event(
            "remove_all_damage_counters",
            player=use.player,
            pokemon=attacker.card,
            pokemon_id=attacker.pokemon_id,
            effect=str(use.key),
            counters=before // per_counter,
            amount=before,
            damage_before=before,
            total_damage=attacker.damage,
        )

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        """「じこさいせい」の決定を待っている状態の確認: 種類は ``DISCARD_ENERGY``、決定するのはワザを使ったプレイヤー、1 枚だけ選ぶ、
        選べるものが、ワザを使ったポケモンについている ``energy_type`` の基本エネルギーカード（ついている順）と同じ。"""
        _, attacker = state.find_pokemon(use.pokemon_id)
        problems = []
        if decision.kind != DISCARD_ENERGY:
            problems.append(f"「じこさいせい」の決定の種類が {decision.kind!r}（{DISCARD_ENERGY} のはず）")
        if decision.player != use.player:
            problems.append(f"「じこさいせい」でトラッシュするカードを選ぶのが、ワザを使ったプレイヤー {use.player} ではなくプレイヤー {decision.player}")
        if (decision.min_choices, decision.max_choices) != (1, 1):
            problems.append(f"「じこさいせい」で選ぶ数が {decision.min_choices}〜{decision.max_choices}（1 枚のはず）")
        candidates = tuple(self._candidates(state, attacker))
        if not candidates or decision.options != candidates:
            problems.append(f"「じこさいせい」の決定の選べるもの {decision.options} が、ついている「{self.energy_type.ja}」エネルギーカード {candidates} と合わない")
        return problems


def attack_damage_modifiers(state: GameState, attacker: PokemonInPlay, defender: PokemonInPlay) -> tuple[DamageModifier, ...]:
    """ワザでダメージを与えるときの、ついているカードによる変更効果（v0.2c）。

    ワザを使うポケモン（``attacker``）についているカードは ``role="attacker"``（プラスパワーの 5 段階）、ダメージを
    受けるポケモン（``defender``）についているカードは ``role="defender"``（ディフェンダーの 7 段階）で聞く（p.321）。
    自分へのダメージ（v0.2f）では、``attacker`` と ``defender`` が同じポケモンになる。それぞれのカードは自分の
    立場でだけ効果を返すので、同じカードの効果を二重に数えない。
    効果の内容は、ついているカードのカード id で効果の登録表から引く（エンジンはカードの種類を知らない）。
    """
    modifiers: list[DamageModifier] = []
    for holder, role in ((attacker, "attacker"), (defender, "defender")):
        for attached in holder.trainers:
            entry = state.effects.trainer_entry(state.cards[attached.card].card_id)
            modifiers.extend(entry.effect.damage_modifiers(state, attached, role))
    return tuple(modifiers)


DAMAGE_ONLY = DamageOnly()


@dataclass(frozen=True)
class AttackEntry:
    """登録の 1 件: 実装と、登録したときに確かめたワザ名。

    説明文のあるワザ（v0.2d から）は、次も書く（説明文のないワザは None のまま）。

    - ``text_ja``: 登録したときに照合した kyuura の写しの説明文（データが変わったら使えなくなる。
      印刷の文面で、処理の根拠ではない）
    - ``play_text_ja``: 実装がしたがう文面（『オフィシャルブック2000』の「最新の説明」）
    - ``source``: ``play_text_ja`` の出典（誌面のページ）
    """

    effect: AttackEffect
    name_ja: str
    text_ja: str | None = None
    play_text_ja: str | None = None
    source: str | None = None


# ---------------------------------------------------------------- トレーナー（v0.2b）


@dataclass(frozen=True)
class TrainerUse:
    """トレーナーカードを 1 回使ったときの情報。効果の処理（``check_playable``・``resolve``・``resume``）に渡す。"""

    player: int
    card: int  # 使っているトレーナーカードの uid
    card_id: str


class TrainerEffect:
    """トレーナーカードの効果の実装の基底（v0.2b）。

    エンジン（``engine._play_trainer``）が、公式ルールの「トレーナーカードを使う」（p.310）の順番で呼ぶ。

    - ``check``: カードのデータがこの実装で扱える形かを確かめ、問題を返す（登録の誤りを見つけるため）。
    - ``check_playable``: 使えるかを確かめる。状態は変えない。カードに書かれた「使うための条件」を
      満たせないなら ``IllegalActionError``、原典で決められない場合は ``UnsupportedError``。
      拒否したら、カードは手札に残る。
    - ``resolve``: カードの説明にしたがう。途中でプレイヤーの決定が要るときは
      ``decisions.push_trainer_decision`` で決定を出して戻る。
    - ``resume``: 出した決定が選ばれたあとの続き。さらに決定を出してもよい（複数段階の選択）。

    手札から出す・相手に見せる・使い終わったらトラッシュする・番の続きにもどる、はエンジンが行う。

    つけて使うトレーナー（v0.2c）は ``stays_in_play = True`` にし、``resolve``（対象を選ぶなら ``resume``）で
    カードを場のポケモンにつける（``zones.attach_trainer``）。使い終わってもトラッシュせず、ついている間
    ``damage_modifiers`` でダメージ計算に効果を出す。トラッシュは、つけたときに決めた番の終わりに、エンジンが
    行う。その番は ``attachment_discard_turn``（使った番 + ``discard_turn_offset``）。番は 1 番ずつ交互に
    進む（p.309）ので、0 は使った番（自分の番）、1 は次の相手の番（v0.2e）。

    - ``decision_problems``（v0.4e）: このトレーナーが出した決定（``resume`` が ``"trainer"``）を待っている状態の、効果ごとの
      不変条件の問題。既定は「決定するのはトレーナーを使ったプレイヤー」だけを確かめる。決定を出す実装は、上書きして決定の形
      （種類・選ぶ数・選べるもの・原典で決められない選択）を宣言する（ワザの ``AttackEffect.decision_problems``（v0.4d）と同じ
      考え方）。決定を待つ間は場が変わらないので、選べるものは決定を出したときと同じ。エンジンの ``check_invariants`` が、
      どのトレーナーの決定にも共通の確認（使用中のトレーナー・続きの情報・番のプレイヤー）のあとで呼ぶ。
    """

    implementation_id = "abstract"
    stays_in_play = False  # True: 使い終わったら場に残る（つけて使うトレーナー）。False: 使いすて（p.310）
    discard_turn_offset = 0  # つけて使うトレーナーをトラッシュする番: 使った番から数えていくつ後の番の終わりか

    def check(self, definition: CardDefinition) -> list[str]:
        if definition.trainer_kinds:
            return [f"種類 {list(definition.trainer_kinds)} のトレーナーは、この実装では扱えない"]
        return []

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        return None

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        raise NotImplementedError

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        raise NotImplementedError(f"{self.implementation_id} は決定を出さない")

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        if decision.player != use.player:
            return [f"トレーナー {use.card_id} の決定 {decision.kind} を決定するのがプレイヤー {decision.player} で、使ったプレイヤー {use.player} ではない"]
        return []

    def damage_modifiers(self, state: GameState, attached: AttachedTrainer, role: str) -> list[DamageModifier]:
        """ついているポケモンがワザを使う（``role="attacker"``）・受ける（``"defender"``）ときの変更効果。"""
        return []

    def attachment_discard_turn(self, state: GameState) -> int:
        """今つけるなら、トラッシュする番（``GameState.turn_number``）。"""
        return state.turn_number + self.discard_turn_offset


@dataclass(frozen=True)
class DrawCards(TrainerEffect):
    """山札からカードを ``count`` 枚引いて、手札に加える（マサキ。p.254 の最新の説明）。

    - 引くのは自分の山札の一番上から（p.312「カードを引く」）。
    - 山札が足りなくても負けにはならず、引けるだけ引く。山札が 0 枚なら 0 枚（p.312）。
      山札がなくなった段階でも負けではない。負けになるのは、番の最初に引けないとき（p.309, p.312）。
    - 引いたカードを相手に見せる必要はない（p.312）。乱数は使わない。
    """

    count: int
    implementation_id = "draw_cards"

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        deck = state.players[use.player].deck
        draw_cards(state, use.player, min(self.count, len(deck)))


def _select_own_pokemon_problems(
    decision: PendingDecision, use: TrainerUse, expected: Iterable[int], what: str, unresolved: Iterable[int] = ()
) -> list[str]:
    """トレーナーを使ったプレイヤーが自分の場のポケモンを 1 匹選ぶ決定（``SELECT_POKEMON``）の形の問題（v0.4e）。

    ``expected`` は選べるもの（場のポケモンの番号。決定を出したときと同じ並び）、``unresolved`` は、そのうち原典で扱いを
    決められない選択（``context`` の ``"unresolved_choices"``）。"""
    problems = []
    if decision.player != use.player:
        problems.append(f"{what}の決定を決定するのがプレイヤー {decision.player} で、使ったプレイヤー {use.player} ではない")
    if decision.kind != SELECT_POKEMON:
        problems.append(f"{what}の決定の種類が {decision.kind!r}（{SELECT_POKEMON} のはず）")
    if (decision.min_choices, decision.max_choices) != (1, 1):
        problems.append(f"{what}の決定で選ぶ数が {decision.min_choices}〜{decision.max_choices}（1 匹のはず）")
    expected = tuple(expected)
    if decision.options != expected:
        problems.append(f"{what}の決定の選べるもの {decision.options} が、選べる自分の場のポケモン {expected} と合わない")
    unresolved = tuple(unresolved)
    if tuple(decision.context_value("unresolved_choices", ())) != unresolved:
        problems.append(
            f"{what}の決定の扱いを決められない選択 {decision.context_value('unresolved_choices', ())} が、{unresolved} と合わない"
        )
    return problems


@dataclass(frozen=True)
class RemoveDamageCounters(TrainerEffect):
    """自分の場のポケモンを 1 匹選び、のっているダメージカウンターを ``counters`` 個とりのぞく
    （きずぐすり。p.254 の最新の説明「あなたの場にいるポケモンを1匹選び、そのポケモンにのっている
    ダメージカウンターを、2個とりのぞく。」）。

    - 選ぶのは自分の場（バトル場とベンチ。p.312）のポケモン 1 匹。場のポケモンの番号で選ぶ。
    - とりのぞく数は選べない。のっている数が ``counters`` 個以上なら ``counters`` 個（p.254 の解説
      「2個のっていたら2個とってください」）、少なければ全部（すべてとりのぞいたら、それ以上は回復しない。p.320）。
    - ダメージカウンター 1 個は 10 ダメージ（p.319。``RuleSet.damage_per_counter``）。

    原典で決められないので扱わない（``UnsupportedError``）:

    - 自分の場にダメージカウンターののったポケモンが 1 匹もいないときに使えるか
    - ダメージカウンターののっていないポケモンを選べるか（選べるものには入れるが、選ぶと拒否する）
    """

    counters: int
    implementation_id = "remove_damage_counters"

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if not any(pokemon.damage > 0 for pokemon in state.players[use.player].in_play()):
            raise UnsupportedError(
                "UNRESOLVED_POTION_WITHOUT_DAMAGE",
                "自分の場にダメージカウンターののったポケモンがいない。このときに「きずぐすり」を使えるかは、"
                "『オフィシャルブック2000』（p.254・p.310）から決められないので扱わない",
            )

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        own = state.players[use.player].in_play()
        push_trainer_decision(
            state,
            use,
            kind=SELECT_POKEMON,
            player=use.player,
            options=[pokemon.pokemon_id for pokemon in own],
            unresolved_choices=[pokemon.pokemon_id for pokemon in own if pokemon.damage == 0],
            unresolved_code="UNRESOLVED_POTION_UNDAMAGED_TARGET",
            unresolved_reason=(
                "ダメージカウンターののっていないポケモンを「きずぐすり」の対象に選べるかは、"
                "『オフィシャルブック2000』（p.254・p.320）から決められないので扱わない"
            ),
        )

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        _, pokemon = state.find_pokemon(choices[0])
        per_counter = state.rules.damage_per_counter
        removed = min(self.counters, pokemon.damage // per_counter)
        pokemon.damage -= removed * per_counter
        state.add_event(
            "remove_damage_counters",
            player=use.player,
            pokemon=pokemon.card,
            pokemon_id=pokemon.pokemon_id,
            counters=removed,
            total_damage=pokemon.damage,
        )

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        """選べるのは自分の場のポケモン（バトル場 → ベンチ）。ダメージカウンターののっていないものは原典で扱いを決められない
        選択（v0.2b）。"""
        own = state.players[use.player].in_play()
        return _select_own_pokemon_problems(
            decision, use, (pokemon.pokemon_id for pokemon in own), "「きずぐすり」",
            unresolved=(pokemon.pokemon_id for pokemon in own if pokemon.damage == 0),
        )


@dataclass(frozen=True)
class SwitchWithBench(TrainerEffect):
    """自分の控えポケモンを 1 匹選び、自分の対戦ポケモンと入れ替える（ポケモンいれかえ。p.254 の最新の説明）。

    - 「にげる」ではない（「にげる」も「ポケモンの入れ替え」の一つだが、逆ではない。p.325）。にげる
      エネルギーは払わない。「にげる」は 1 番に何度でもできる（p.311）ので、回数の管理とは関係しない。
    - 移動するポケモンについているカード・ダメージカウンターは、いっしょに移動する（p.311）。
      場のポケモン（``PokemonInPlay``）ごと入れ替えるので、カードの uid・場のポケモンの番号も変わらない。
    - ベンチに戻ったもとの対戦ポケモンの特殊状態は、すべて消える（p.322「特殊状態になっているポケモンが
      ベンチに戻ったら…消えてなくなります」。v0.3a。「にげる」と同じ ``conditions.clear_special_conditions``）。
    - ねむり・マヒ状態（「にげる」を宣言できない。p.311）のポケモンでも入れ替える（p.325「「にげる」がおこなえない
      状態のポケモンでも、「そのポケモンを入れ替える」と指示されたときは、入れ替えをおこないます」。v0.3b）。
    - ベンチに戻ったもとの対戦ポケモンが受けていたワザによる持続する効果も消える（p.322。v0.4b。特殊状態とは別の処理）。

    原典で決められないので扱わない（``UnsupportedError``）: 控えポケモンがいないときに使えるか。
    """

    implementation_id = "switch_with_bench"

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if not state.players[use.player].bench:
            raise UnsupportedError(
                "UNRESOLVED_SWITCH_WITHOUT_BENCH",
                "控えポケモンがいない。このときに「ポケモンいれかえ」を使えるかは、"
                "『オフィシャルブック2000』（p.254・p.310）から決められないので扱わない",
            )

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        bench = state.players[use.player].bench
        push_trainer_decision(
            state, use, kind=SELECT_POKEMON, player=use.player, options=[pokemon.pokemon_id for pokemon in bench]
        )

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        p = state.players[use.player]
        index = next(i for i, pokemon in enumerate(p.bench) if pokemon.pokemon_id == choices[0])
        old = p.active
        p.active, p.bench[index] = p.bench[index], old
        state.add_event(
            "switch",
            player=use.player,
            old_active=old.card,
            new_active=p.active.card,
            old_active_pokemon_id=old.pokemon_id,
            new_active_pokemon_id=p.active.pokemon_id,
        )
        # ベンチに戻ったポケモンの特殊状態はすべて消える（p.322。「にげる」と同じ処理。v0.3a）
        clear_special_conditions(state, use.player, old, SWITCH)
        # ワザによる持続する効果も消える（p.322「通常、「持続する効果」を受けたポケモンがベンチにもどったら…消えてなくなります」。v0.4b）
        remove_persistent_effects(state, use.player, old, SWITCH)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        """選べるのは自分のベンチのポケモン（控えポケモン）。"""
        bench = state.players[use.player].bench
        return _select_own_pokemon_problems(decision, use, (pokemon.pokemon_id for pokemon in bench), "「ポケモンいれかえ」")


@dataclass(frozen=True)
class AttachedAttackBonus(TrainerEffect):
    """自分の対戦ポケモンにつけて使い、自分の番の終わりにトラッシュする。つけているポケモンのワザが
    対戦ポケモンにダメージを与えるとき、そのダメージは ``+amount``（プラスパワー。p.257 の最新の説明）。

    - つけるのは自分の対戦ポケモン（バトル場のポケモン）。選ぶものはないので決定は出さない。
    - 効果はダメージ計算の 5 段階（弱点・抵抗力のあと。p.321）。計算の途中の 0・マイナスはそのまま続ける。
      2 段階までで 0 以下なら計算を終える（ダメージを与えないワザには効果がない）。
    - 有効期限は、使った番の終わり。カードはついているポケモンといっしょに移り（にげる・入れ替え。p.311）、
      きぜつしたらいっしょにトラッシュする（p.323）。
    - 控えポケモンへのダメージは変えない（最新の説明）。自分自身へのダメージ（p.257 の解説では +10 される）
      を与えるワザはまだないので、``attack_damage_modifiers`` は相手の対戦ポケモンへのダメージにだけ使う。
    """

    amount: int
    implementation_id = "attached_attack_bonus"
    stays_in_play = True

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        active = state.players[use.player].active
        attach_trainer(state, use.player, use.card, active, discard_at_end_of_turn=self.attachment_discard_turn(state))

    def damage_modifiers(self, state: GameState, attached: AttachedTrainer, role: str) -> list[DamageModifier]:
        if role != "attacker":
            return []
        name = state.card_def(attached.card).name_ja
        return [DamageModifier(step=5, amount=self.amount, label=name, source=attached.card)]


@dataclass(frozen=True)
class AttachedDamageReduction(TrainerEffect):
    """自分の場のポケモンを 1 匹選んでつけ、次の相手の番の終わりにトラッシュする。つけているポケモンが
    ワザによるダメージを受けるとき、そのダメージは ``-amount``（ディフェンダー。p.257 の最新の説明
    「このカードは、あなたの場にいるポケモンにつけて使い、次の相手の番の終わりにトラッシュする。このカードを
    つけているポケモンがワザによるダメージを受けるとき、そのダメージは「-20」される。」。docs/defender-v0.2e.md）。

    - つけるのは自分の場（バトル場とベンチ。p.312・p.313）のポケモン。1 匹でも選ぶ決定を出す（場のポケモンの番号）。
    - 効果はダメージ計算の 7 段階（ワザを受けるポケモンについているカードの効果。p.321 がディフェンダーを例に
      挙げる）。弱点・抵抗力・5 段階（プラスパワー）のあと。途中の 0・マイナスはそのまま続ける。2 段階までで
      0 以下なら計算を終える（7 段階に進まない）。
    - 有効期限は次の相手の番の終わり（``discard_turn_offset = 1``）。効果はカードがついている間だけあり、
      カードをトラッシュする時点で終わる（最新の説明では、効果の終わりとトラッシュの時点が同じ）。
    - ワザで受けるダメージだけを減らす（ワザを使うときのダメージは変えない。どくのダメージは変えない。p.322）。
      自分のワザで自分が受けるダメージにも効く（p.257 の解説）が、そのワザはまだない。今は、相手のワザで
      対戦ポケモンが受けるダメージ（``attack_damage_modifiers`` の ``role="defender"``）にだけ使う。
    """

    amount: int
    implementation_id = "attached_damage_reduction"
    stays_in_play = True
    discard_turn_offset = 1

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        own = state.players[use.player].in_play()
        push_trainer_decision(state, use, kind=SELECT_POKEMON, player=use.player, options=[pokemon.pokemon_id for pokemon in own])

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        owner, pokemon = state.find_pokemon(choices[0])
        if owner != use.player:
            raise RuntimeError(f"相手の場のポケモン {choices[0]} にディフェンダーをつけようとした（エンジンの不具合）")
        attach_trainer(state, use.player, use.card, pokemon, discard_at_end_of_turn=self.attachment_discard_turn(state))

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        """選べるのは自分の場のポケモン（バトル場 → ベンチ）。"""
        own = state.players[use.player].in_play()
        return _select_own_pokemon_problems(decision, use, (pokemon.pokemon_id for pokemon in own), "「ディフェンダー」")

    def damage_modifiers(self, state: GameState, attached: AttachedTrainer, role: str) -> list[DamageModifier]:
        if role != "defender":
            return []
        name = state.card_def(attached.card).name_ja
        return [DamageModifier(step=7, amount=-self.amount, label=name, source=attached.card)]


@dataclass(frozen=True)
class TrainerEntry:
    """トレーナーの登録の 1 件。

    - ``effect``: 実装
    - ``name_ja``・``text_ja``: 登録したときに照合した kyuura の写しの名前・文面（データが変わったら
      使えなくなる。印刷の文面で、処理の根拠ではない）
    - ``play_text_ja``: 実装がしたがう文面（『オフィシャルブック2000』の「最新の説明」）
    - ``source``: ``play_text_ja`` の出典（誌面のページ）
    """

    effect: TrainerEffect
    name_ja: str
    text_ja: str
    play_text_ja: str
    source: str


# ---------------------------------------------------------------- ポケモンパワー（特殊能力。v0.5）


@dataclass(frozen=True, order=True)
class PowerKey:
    """ポケモンパワーの安定した識別子: カード id とパワーの位置（カードに印刷された順、0 から）。ワザの ``AttackKey`` とは別。"""

    card_id: str
    power_index: int

    def __str__(self) -> str:
        return f"{self.card_id}@power{self.power_index}"


@dataclass(frozen=True)
class PowerUse:
    """ポケモンパワーを 1 回使ったときの情報（``UsePokemonPower`` の値）。効果の処理（``check_usable``・``resolve``）に渡す。

    ``energy``・``source``・``target`` は、パワーの説明が選ばせるもの（使わないパワーでは None）。
    """

    player: int
    pokemon_id: int  # パワーを使うポケモン（場のポケモンの番号）
    key: PowerKey
    energy: int | None = None
    source: int | None = None
    target: int | None = None


class PowerEffect:
    """使用を宣言して使うポケモンパワー（特殊能力）の実装の基底（v0.5）。

    エンジン（``engine._use_pokemon_power``）が、公式ルールの「ポケモンの特殊能力を使う」（p.311）の順番で呼ぶ。ワザ（``AttackEffect``）
    とは別のもの: パワーの使用は番を終わらせず（p.309 で番が終わるのはワザのあと）、こんらんのコイン（ワザ・にげるの規定。p.309・
    p.311）もない。使えない特殊状態はパワーの説明ごとに書かれている（p.323 の最新の説明の例）ので、実装が ``check_usable`` で確かめる
    （ワザ・にげるの制限（``engine._require_not_asleep_or_paralyzed``）は流用しない）。

    - ``check``: カードのデータ（印刷の文面）が、この実装で処理できる形かを確かめ、問題を返す（登録の誤りを見つけるため）。
    - ``check_usable``: 使えるかと、説明が選ばせるもの（``PowerUse``）が正しいかを確かめる。状態は変えない。使えない・選んだものが
      正しくないなら ``IllegalActionError``、原典で決められない場合は ``UnsupportedError``（コードは ``UNRESOLVED_…``）。
    - ``resolve``: パワーの説明にしたがって処理する（p.311 の手順 3）。

    v0.5 のパワーは決定を出さない（説明が選ばせるものはコマンドで指定する）。決定を出すパワーを加えるときは、``resume`` と、決定の形を
    宣言する ``decision_problems``（ワザ（v0.4d）・トレーナー（v0.4e）と同じ考え方）と、エンジンの再開先を加える。使用回数の制限
    （「1 番に 1 回」など）があるパワーを加えるときは、回数を状態に持つ（ログから数えない）。自動的にはたらくパワー・常にはたらいている
    パワー（p.311・p.323）は、宣言しないので、この実装の形では扱わない（未対応）。
    """

    implementation_id = "abstract"

    def check(self, power: Power) -> list[str]:
        return []

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        return None

    def resolve(self, state: GameState, use: PowerUse) -> None:
        raise NotImplementedError


def _require_user_not_asleep_paralyzed_confused(state: GameState, use: PowerUse) -> None:
    """パワーの説明「このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない」の確認（v0.5 のエナジートランス・v0.6 の
    あまごいは、どちらも最新の説明にこの文がある。p.16・p.90・p.323）。パワーを使うポケモン（「このカード」）だけを見る。どくは
    挙げられていないので制限しない。特殊状態の制限はパワーの説明ごとなので、この文のないパワーには使わない（ワザ・にげるの制限
    ``engine._require_not_asleep_or_paralyzed`` とは別）。"""
    _, user = state.find_pokemon(use.pokemon_id)
    conditions = user.conditions
    for blocked, code, name in ((conditions.asleep, "POKEMON_ASLEEP", "ねむり"), (conditions.paralyzed, "POKEMON_PARALYZED", "マヒ"),
                                (conditions.confused, "POKEMON_CONFUSED", "こんらん")):
        if blocked:
            raise IllegalActionError(code, f"ポケモン {use.pokemon_id} は{name}状態なので、このポケモンパワーは使えない（最新の説明）")


def _own_pokemon(state: GameState, use: PowerUse, pokemon_id: int, role: str) -> PokemonInPlay:
    """パワーの説明が選ばせる「自分の場のポケモン」（``role`` は ``SOURCE``・``TARGET``。コードの接頭辞）。"""
    found = state.find_pokemon(pokemon_id)
    if found is None:
        raise IllegalActionError(f"{role}_NOT_IN_PLAY", f"場のポケモンの番号 {pokemon_id!r} は場にいない")
    owner, pokemon = found
    if owner != use.player:
        raise IllegalActionError(f"{role}_NOT_YOURS", f"場のポケモン {pokemon_id} は相手の場のポケモン（自分の場のポケモンだけ）")
    return pokemon


@dataclass(frozen=True)
class EnergyTransfer(PowerEffect):
    """自分の場のポケモンについている ``energy_type`` のエネルギーカードを 1 枚、自分の場の別のポケモンにつけかえる（v0.5。フシギバナの
    「エナジートランス」。p.16・p.323 の最新の説明「この力は、自分の番の中で何度でも使える。自分の場にいるポケモンについている
    「草」エネルギーを、自分の場にいる別のポケモンにつけかえる。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない。」。
    docs/venusaur-v0.5.md・docs/energy-transfer-v0.5.md）。

    - 使えるのは自分の番の中（エンジンが番のプレイヤーの ``Phase.MAIN`` だけで受け付ける）。何度でも使える（回数を数えない）。
    - 使えないのは、このパワーを持つポケモン（「このカード」）がねむり・マヒ・こんらんのとき（``POKEMON_ASLEEP``・
      ``POKEMON_PARALYZED``・``POKEMON_CONFUSED``）。どくだけなら使える（説明に挙げられていない。p.323「特に記述されていない
      かぎり、特殊能力はいつでも、何度でも使用を宣言することができます」）。ベンチのポケモンは特殊状態にならない（p.322）。
    - 移すのは基本エネルギーカード（物理的なカード。同じ uid）で、``energy_type``（草）を出すものだけ。移動元・移動先は自分の場の
      ポケモン（バトル場・ベンチ、パワーを持つポケモン自身を含む）で、移動先は移動元と別のポケモン（「別のポケモン」）。移動元・
      移動先の特殊状態は関係しない。
    - 1 回の使用で 1 枚（実装上の仮定。説明は枚数を書かないが、何度でも使えるので、何枚移しても 1 枚ずつ移した結果と同じ）。
    - つけかえは手札からエネルギーをつけること（p.310。1 番に 1 枚）ではないので、その回数（``energy_attachments_this_turn``）は変えない
      （SUPPORTED。p.16 の解説「すでに場に出ているので、その移動で10ダメージを受けることはありません」）。
    - 乱数は使わない。ログ ``move_energy``（``player``・``pokemon``・``pokemon_id``（パワーを使ったポケモン）・``power``（``PowerKey``
      の文字列）・``energy``・``from_pokemon_id``・``to_pokemon_id``）。手札からつけたログ ``attach_energy`` とは別。
    """

    energy_type: EnergyType
    implementation_id = "energy_transfer"

    def check(self, power: Power) -> list[str]:
        problems = []
        if power.kind != "pokemon_power":
            problems.append(f"種類 {power.kind!r} のパワーを、使用を宣言するポケモンパワーとして登録している")
        if power.text_ja is None:
            problems.append("説明文のないポケモンパワーを、エネルギーをつけかえるパワーとして登録している")
        return problems

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        if use.energy is None or use.source is None or use.target is None:
            raise IllegalActionError("POWER_CHOICE_MISSING", "つけかえるエネルギー（energy）・移動元（source）・移動先（target）を指定する")
        source = _own_pokemon(state, use, use.source, "SOURCE")
        _own_pokemon(state, use, use.target, "TARGET")
        if use.source == use.target:
            raise IllegalActionError("SAME_POKEMON", "エネルギーは、ついているポケモンとは別のポケモンにつけかえる（「別のポケモン」）")
        if use.energy not in source.energy:
            raise IllegalActionError("ENERGY_NOT_ATTACHED", f"エネルギー {use.energy!r} は移動元のポケモン {use.source} についていない")
        definition = state.card_def(use.energy)
        if not definition.is_basic_energy or definition.provides is not self.energy_type:
            raise IllegalActionError(
                "WRONG_ENERGY_TYPE", f"エネルギー {use.energy} は「{self.energy_type.ja}」エネルギーではない（「{self.energy_type.ja}」だけをつけかえる）"
            )

    def resolve(self, state: GameState, use: PowerUse) -> None:
        _, user = state.find_pokemon(use.pokemon_id)
        _, source = state.find_pokemon(use.source)
        _, target = state.find_pokemon(use.target)
        # 同じ uid のカードを移す（複製しない・トラッシュしない・持ち主は変わらない）
        source.energy.remove(use.energy)
        target.energy.append(use.energy)
        state.add_event(
            "move_energy",
            player=use.player,
            pokemon=user.card,
            pokemon_id=user.pokemon_id,
            power=str(use.key),
            energy=use.energy,
            from_pokemon_id=source.pokemon_id,
            to_pokemon_id=target.pokemon_id,
        )


@dataclass(frozen=True)
class AttachEnergyFromHand(PowerEffect):
    """自分の手札から ``energy_type`` のエネルギーカードを 1 枚出して、自分の場の ``pokemon_type`` のポケモンにつける（v0.6。
    カメックスの「あまごい」。p.90 の最新の説明「この力は、自分の番の中で何度でも使える。自分の手札から「水」エネルギーカードを
    出して、自分の場の「水」ポケモンにつける。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない。」。
    docs/rain-dance-v0.6.md）。

    - 使えるのは自分の番の中（エンジンが番のプレイヤーの ``Phase.MAIN`` だけで受け付ける）。何度でも使える（回数を数えない）。
    - 使えないのは、このパワーを持つポケモン（「このカード」）がねむり・マヒ・こんらんのとき（どくは使える。v0.5 と同じ）。
    - 選ばせるもの: 手札のエネルギーカードの uid（``energy``）と、つける自分の場のポケモンの番号（``target``）。移動元はない
      （手札）ので ``source`` は None（指定したら ``POWER_CHOICE_NOT_USED``）。
    - つけるのは自分の手札の基本エネルギーカードで、``energy_type``（水）を出すもの。p.298 の解説（レインボーエネルギーは手札では
      色を持たないので「あまごい」で水エネルギーとしてつけられない）。特殊エネルギーは未実装。
    - つける先は自分の場（バトル場・ベンチ。カメックス自身を含む）の ``pokemon_type``（水）のポケモン。タイプはいちばん上のカード
      で決める（p.310）。相手の場のポケモンにはつけない（説明「自分の場の」・p.310）。つける先の特殊状態は関係しない。
    - 1 回の使用で 1 枚（実装上の仮定。印刷の文面「1度に何枚でも」・最新の説明「何度でも使える」のどちらでも、何枚つけても
      1 枚ずつつけた結果と同じ。v0.5 のエナジートランスと同じ扱い）。
    - 手札からつける通常の操作（p.310。1 番に 1 枚）の回数 ``energy_attachments_this_turn`` は変えず、確かめない（通常の操作で
      つけたあとでも使える。p.307・p.90。R12 SUPPORTED）。この効果でつけた枚数を ``energy_attached_by_powers_this_turn`` に数える
      （そのあとの通常の操作は原典で決められないので、エンジンが止める。R13 UNRESOLVED）。
    - 乱数は使わない。ログ ``power_attach_energy``（``player``・``pokemon``・``pokemon_id``（パワーを使ったポケモン）・``power``
      （``PowerKey`` の文字列）・``energy``・``to_pokemon_id``）。手札からつけた通常のログ ``attach_energy``・場のエネルギーを
      つけかえたログ ``move_energy``（エナジートランス）とは別。
    """

    energy_type: EnergyType
    pokemon_type: EnergyType
    implementation_id = "attach_energy_from_hand"

    def check(self, power: Power) -> list[str]:
        problems = []
        if power.kind != "pokemon_power":
            problems.append(f"種類 {power.kind!r} のパワーを、使用を宣言するポケモンパワーとして登録している")
        if power.text_ja is None:
            problems.append("説明文のないポケモンパワーを、手札からエネルギーをつけるパワーとして登録している")
        return problems

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        if use.energy is None or use.target is None:
            raise IllegalActionError("POWER_CHOICE_MISSING", "つけるエネルギー（energy。手札のカード）とつける先（target）を指定する")
        if use.source is not None:
            raise IllegalActionError("POWER_CHOICE_NOT_USED", "このポケモンパワーは手札からつけるので、移動元（source）は指定しない")
        if use.energy not in state.players[use.player].hand:
            raise IllegalActionError("CARD_NOT_IN_HAND", f"カード {use.energy!r} はプレイヤー {use.player} の手札にない")
        definition = state.card_def(use.energy)
        if not definition.is_basic_energy:
            raise IllegalActionError("NOT_BASIC_ENERGY", f"カード {use.energy} は基本エネルギーカードではない")
        if definition.provides is not self.energy_type:
            raise IllegalActionError(
                "WRONG_ENERGY_TYPE", f"エネルギー {use.energy} は「{self.energy_type.ja}」エネルギーではない（「{self.energy_type.ja}」だけをつける）"
            )
        target = _own_pokemon(state, use, use.target, "TARGET")
        if state.card_def(target.card).pokemon_type is not self.pokemon_type:
            raise IllegalActionError(
                "WRONG_POKEMON_TYPE", f"場のポケモン {use.target} は「{self.pokemon_type.ja}」ポケモンではない（「{self.pokemon_type.ja}」ポケモンにだけつける）"
            )

    def resolve(self, state: GameState, use: PowerUse) -> None:
        _, user = state.find_pokemon(use.pokemon_id)
        _, target = state.find_pokemon(use.target)
        attach_energy_from_hand(state, use.player, use.energy, target)  # 同じ uid のカードを手札から場へ
        state.energy_attached_by_powers_this_turn += 1
        state.add_event(
            "power_attach_energy",
            player=use.player,
            pokemon=user.card,
            pokemon_id=user.pokemon_id,
            power=str(use.key),
            energy=use.energy,
            to_pokemon_id=target.pokemon_id,
        )


def would_be_knocked_out(state: GameState, pokemon: PokemonInPlay, damage: int) -> bool:
    """場のポケモン ``pokemon`` のダメージが ``damage`` になったら「きぜつ」するか（v0.7）。

    きぜつの判定と同じ式（ダメージが HP と同じか、それより大きい。p.319「ポケモンのダメージが、ポケモンのHPと同じか、それより
    大きくなったら、そこでそのポケモンは「きぜつ」します」・p.320「ダメージカウンターの移動によって、ダメージの数がポケモンのHPと
    同じか、それより大きくなったら、そのポケモンは「きぜつ」します」・p.323）。HP はいちばん上のカードの値（p.310）。状態は変えない。
    """
    return damage >= state.card_def(pokemon.card).hp


@dataclass(frozen=True)
class MoveDamageCounter(PowerEffect):
    """自分の場のポケモンにのっているダメージカウンターを 1 個、自分の場の別のポケモンにのせかえる（v0.7。フーディンの
    「ダメージスワップ」。p.153 の最新の説明「この力は、自分の番の中で何度でも使える。この力によってポケモンが「きぜつ」しない
    かぎり、自分の場にいるポケモンにのっているダメージカウンターを、自分の場にいる別のポケモンにのせかえる。このカードが
    「ねむり・マヒ・こんらん」状態のとき、この力は使えない。」。docs/damage-swap-v0.7.md）。

    - 使えるのは自分の番の中（エンジンが番のプレイヤーの ``Phase.MAIN`` だけで受け付ける）。何度でも使える（回数を数えない）。
    - 使えないのは、このパワーを持つポケモン（「このカード」）がねむり・マヒ・こんらんのとき（どくは使える。v0.5・v0.6 と同じ）。
    - 選ばせるもの: 移動元（``source``）と移動先（``target``）の場のポケモンの番号。エネルギーは選ばない（``energy`` を指定したら
      ``POWER_CHOICE_NOT_USED``）。
    - 移動元は、自分の場（バトル場・ベンチ。フーディン自身を含む）の、ダメージカウンターがのっているポケモン（なければ
      ``NO_DAMAGE_COUNTERS``）。移動先は、自分の場の、移動元と別のポケモン（「別のポケモン」。同じなら ``SAME_POKEMON``）。相手の
      場のポケモンはどちらにもならない（「自分の場にいる」）。移動元・移動先の特殊状態は関係しない（どくマーカーはダメージ
      カウンターとは別のもの。p.322）。
    - 1 回の使用で 1 個（実装上の仮定。最新の説明は 1 回に移す数を書かず、印刷の文面は「自由に移動できる」。何度でも使えるので、
      どの移し方も 1 個ずつの移動に分けられ、移動先のダメージは増えていくだけなので、途中できぜつする状態を通らない。
      docs/damage-swap-v0.7.md の S3・S18）。
    - のせかえで移動先のダメージが HP と同じか大きくなる（``would_be_knocked_out``）なら使えない（``WOULD_KNOCK_OUT``。「この力に
      よってポケモンが「きぜつ」しないかぎり」。印刷の文面「ポケモンが「きぜつ」しない範囲で」。p.320）。状態を変える前に確かめる
      ので、この力でポケモンがきぜつすることはなく、きぜつの処理（トラッシュ・サイド・交代）を呼ばない。
    - のせかえで増えたダメージは「ダメージを受けた」ことにならない（p.320）。弱点・抵抗力・プラスパワー・ディフェンダー・
      「ダメージを受けない」状態の計算をせず、ダメージのログ ``damage`` も出さない（ダメージ 1 個 = 10。p.319）。
    - 乱数は使わない。ログ ``move_damage_counter``（``player``・``pokemon``・``pokemon_id``（パワーを使ったポケモン）・``power``
      （``PowerKey`` の文字列）・``count``（1）・``from_pokemon_id``・``to_pokemon_id``・``from_total_damage``・``to_total_damage``（のせかえた
      あとのダメージ））。
    """

    implementation_id = "move_damage_counter"

    def check(self, power: Power) -> list[str]:
        problems = []
        if power.kind != "pokemon_power":
            problems.append(f"種類 {power.kind!r} のパワーを、使用を宣言するポケモンパワーとして登録している")
        if power.text_ja is None:
            problems.append("説明文のないポケモンパワーを、ダメージカウンターをのせかえるパワーとして登録している")
        return problems

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        if use.source is None or use.target is None:
            raise IllegalActionError("POWER_CHOICE_MISSING", "ダメージカウンターの移動元（source）と移動先（target）を指定する")
        if use.energy is not None:
            raise IllegalActionError("POWER_CHOICE_NOT_USED", "このポケモンパワーはダメージカウンターをのせかえるので、エネルギー（energy）は指定しない")
        source = _own_pokemon(state, use, use.source, "SOURCE")
        target = _own_pokemon(state, use, use.target, "TARGET")
        if use.source == use.target:
            raise IllegalActionError("SAME_POKEMON", "ダメージカウンターは、のっているポケモンとは別のポケモンにのせかえる（「別のポケモン」）")
        per_counter = state.rules.damage_per_counter
        if source.damage < per_counter:
            raise IllegalActionError("NO_DAMAGE_COUNTERS", f"移動元のポケモン {use.source} にダメージカウンターがのっていない")
        if would_be_knocked_out(state, target, target.damage + per_counter):
            raise IllegalActionError(
                "WOULD_KNOCK_OUT",
                f"移動先のポケモン {use.target} にダメージカウンターをのせると「きぜつ」する（この力によってポケモンが「きぜつ」しないかぎり）",
            )

    def resolve(self, state: GameState, use: PowerUse) -> None:
        _, user = state.find_pokemon(use.pokemon_id)
        _, source = state.find_pokemon(use.source)
        _, target = state.find_pokemon(use.target)
        per_counter = state.rules.damage_per_counter
        source.damage -= per_counter
        target.damage += per_counter
        state.add_event(
            "move_damage_counter",
            player=use.player,
            pokemon=user.card,
            pokemon_id=user.pokemon_id,
            power=str(use.key),
            count=1,
            from_pokemon_id=source.pokemon_id,
            to_pokemon_id=target.pokemon_id,
            from_total_damage=source.damage,
            to_total_damage=target.damage,
        )


@dataclass(frozen=True)
class PowerEntry:
    """ポケモンパワーの登録の 1 件（v0.5）。

    - ``effect``: 実装
    - ``name_ja``・``text_ja``: 登録したときに照合した kyuura の写しのパワーの名前・印刷の文面（データが変わったら使えなくなる。
      処理の根拠ではない）
    - ``play_text_ja``: 実装がしたがう文面（『オフィシャルブック2000』の「最新の説明」）
    - ``source``: ``play_text_ja`` の出典（誌面のページ）
    """

    effect: PowerEffect
    name_ja: str
    text_ja: str
    play_text_ja: str
    source: str


# ---------------------------------------------------------------- 登録表


class EffectRegistry:
    """カードの効果の実装の登録表。対戦ごとに 1 つ使う（``GameState.effects``）。

    ワザ（``AttackKey`` → ``AttackEntry``）と、トレーナー（カード id → ``TrainerEntry``、v0.2b）と、ポケモンパワー
    （``PowerKey`` → ``PowerEntry``、v0.5）を登録できます。特殊エネルギーの実装は、それを加えるときに同じ形（安定した
    識別子 → 実装）で欄を加えます。それまでは、これらのカードは未対応です。登録表は変えられません
    （``with_*``・``without_*`` は新しい登録表を返す）。
    """

    def __init__(
        self,
        registry_id: str,
        attacks: Mapping[AttackKey, AttackEntry] | Iterable[tuple[AttackKey, AttackEntry]],
        trainers: Mapping[str, TrainerEntry] | Iterable[tuple[str, TrainerEntry]] = (),
        powers: Mapping[PowerKey, PowerEntry] | Iterable[tuple[PowerKey, PowerEntry]] = (),
    ):
        self.id = registry_id
        self._attacks: dict[AttackKey, AttackEntry] = dict(attacks)
        self._trainers: dict[str, TrainerEntry] = dict(trainers)
        self._powers: dict[PowerKey, PowerEntry] = dict(powers)

    def __repr__(self) -> str:
        return f"EffectRegistry({self.id!r}, {len(self._attacks)} attacks, {len(self._trainers)} trainers, {len(self._powers)} powers)"

    # --- ワザ ---

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
        if entry.text_ja != attack.text_ja:
            return "登録したときに照合した説明文と、データの説明文が違う（データが変わった。照合し直す必要がある）"
        problems = entry.effect.check(attack)
        return "; ".join(problems) or None

    def attack_effect(self, card_id: str, attack: Attack) -> AttackEffect | None:
        """使えるワザなら実装を返す。登録がない・データと合わないなら None。"""
        if self.attack_problem(card_id, attack) is not None:
            return None
        return self.attack_entry(card_id, attack.index).effect

    def with_attacks(self, registry_id: str, attacks: Mapping[AttackKey, AttackEntry]) -> EffectRegistry:
        """登録を加えた新しい登録表（元の登録表は変えない）。テストや、実装を段階的に加えるときに使う。"""
        return EffectRegistry(registry_id, {**self._attacks, **attacks}, self._trainers, self._powers)

    def without_attacks(self, registry_id: str, keys: Iterable[AttackKey]) -> EffectRegistry:
        """登録を除いた新しい登録表（元の登録表は変えない）。"""
        removed = set(keys)
        return EffectRegistry(registry_id, {k: v for k, v in self._attacks.items() if k not in removed}, self._trainers, self._powers)

    # --- トレーナー（v0.2b） ---

    def trainer_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._trainers))

    def trainer_entry(self, card_id: str) -> TrainerEntry | None:
        return self._trainers.get(card_id)

    def trainer_problem(self, definition: CardDefinition) -> str | None:
        """このトレーナーカードを使えない理由。使えるなら None。名前や説明文の有無では決めない。"""
        if definition.category != "trainer":
            return "トレーナーカードではない"
        entry = self.trainer_entry(definition.id)
        if entry is None:
            return "トレーナーカードの効果の実装が登録されていない"
        if entry.name_ja != definition.name_ja:
            return f"登録した名前「{entry.name_ja}」と、データの名前「{definition.name_ja}」が違う"
        if entry.text_ja != definition.trainer_text_ja:
            return "登録したときに照合した文面と、データの文面が違う（データが変わった。照合し直す必要がある）"
        problems = entry.effect.check(definition)
        return "; ".join(problems) or None

    def trainer_effect(self, definition: CardDefinition) -> TrainerEffect | None:
        """使えるトレーナーなら実装を返す。登録がない・データと合わないなら None。"""
        if self.trainer_problem(definition) is not None:
            return None
        return self.trainer_entry(definition.id).effect

    def with_trainers(self, registry_id: str, trainers: Mapping[str, TrainerEntry]) -> EffectRegistry:
        """トレーナーの登録を加えた新しい登録表（元の登録表は変えない）。"""
        return EffectRegistry(registry_id, self._attacks, {**self._trainers, **trainers}, self._powers)

    def without_trainers(self, registry_id: str, card_ids: Iterable[str]) -> EffectRegistry:
        """トレーナーの登録を除いた新しい登録表（元の登録表は変えない）。"""
        removed = set(card_ids)
        return EffectRegistry(registry_id, self._attacks, {k: v for k, v in self._trainers.items() if k not in removed}, self._powers)

    # --- ポケモンパワー（v0.5） ---

    def power_keys(self) -> tuple[PowerKey, ...]:
        return tuple(sorted(self._powers))

    def power_entry(self, card_id: str, power_index: int) -> PowerEntry | None:
        return self._powers.get(PowerKey(card_id, power_index))

    def power_problem(self, card_id: str, power: Power) -> str | None:
        """このポケモンパワーを使えない理由。使えるなら None。名前や説明文の有無では決めない（ワザと同じ）。"""
        entry = self.power_entry(card_id, power.index)
        if entry is None:
            return "ポケモンパワーの効果の実装が登録されていない"
        if entry.name_ja != power.name_ja:
            return f"登録したパワーの名前「{entry.name_ja}」と、データの名前「{power.name_ja}」が違う"
        if entry.text_ja != power.text_ja:
            return "登録したときに照合した文面と、データの文面が違う（データが変わった。照合し直す必要がある）"
        problems = entry.effect.check(power)
        return "; ".join(problems) or None

    def power_effect(self, card_id: str, power: Power) -> PowerEffect | None:
        """使えるポケモンパワーなら実装を返す。登録がない・データと合わないなら None。"""
        if self.power_problem(card_id, power) is not None:
            return None
        return self.power_entry(card_id, power.index).effect

    def with_powers(self, registry_id: str, powers: Mapping[PowerKey, PowerEntry]) -> EffectRegistry:
        """ポケモンパワーの登録を加えた新しい登録表（元の登録表は変えない）。"""
        return EffectRegistry(registry_id, self._attacks, self._trainers, {**self._powers, **powers})

    def without_powers(self, registry_id: str, keys: Iterable[PowerKey]) -> EffectRegistry:
        """ポケモンパワーの登録を除いた新しい登録表（元の登録表は変えない）。"""
        removed = set(keys)
        return EffectRegistry(registry_id, self._attacks, self._trainers, {k: v for k, v in self._powers.items() if k not in removed})

    def describe(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "attacks": {
                str(k): {"implementation": e.effect.implementation_id, "name_ja": e.name_ja}
                | ({} if e.source is None else {"source": e.source})
                for k, e in sorted(self._attacks.items())
            },
            "trainers": {
                k: {"implementation": e.effect.implementation_id, "name_ja": e.name_ja, "source": e.source}
                for k, e in sorted(self._trainers.items())
            },
            "powers": {
                str(k): {"implementation": e.effect.implementation_id, "name_ja": e.name_ja, "source": e.source}
                for k, e in sorted(self._powers.items())
            },
        }


def _damage_only(entries: Iterable[tuple[str, int, str]]) -> dict[AttackKey, AttackEntry]:
    return {AttackKey(card_id, index): AttackEntry(DAMAGE_ONLY, name) for card_id, index, name in entries}


# 登録。ワザは v0.1 で使えたワザ（説明文のない固定ダメージのワザ）を、効果のないワザとして登録する。
# 説明文のあるワザ（v0.2d のみだれづき、v0.2f のでんげき、v0.3a のどくばり、v0.3b のいとをはく・キノコのほうし、
# v0.3c のあやしいひかり、v0.4a のパラセクトのキノコのほうし・ジュゴンのれいとうビーム、v0.4b のトランセル・コクーンの
# かたまる・しびれごな・どくのこな、v0.4c のスピアーのダブルニードル・どくばり、v0.4d のバタフリーのふきとばし・メガドレイン、
# v0.5 のやどりぎのタネ・フシギソウのどくのこな、v0.6 のゼニガメのあわ・からにこもる、カメールのからにこもる、カメックスの
# ハイドロポンプ）は、カードのページと照合した最新の説明・出典とともに登録する。
# どれも『ポケモンカードオフィシャルブック2000』のカードのページで、「ワザ」欄に説明文がないことを
# 画像で確かめた（kyuura_engine/data/card_verification.json）。ワザ名は kyuura の写しの値（照合用）。
# トレーナー（v0.2b）は p.254、プラスパワー（v0.2c）・ディフェンダー（v0.2e）は p.257、ドードーの「みだれづき」
# （v0.2d）は p.231 の画像で「最新の説明」を確かめた（同じファイル。docs/trainers-v0.2b.md・
# docs/pluspower-v0.2c.md・docs/coin-attacks-v0.2d.md・docs/defender-v0.2e.md）。
DEFAULT_EFFECTS = EffectRegistry(
    "kyuura-engine-0.7",
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
        ("PMCG1-035", 0, "かじる"),  # ピカチュウ（v0.2f）p.125。「ワザ」欄は「●かじる」で説明文なし
        ("PMCG2-003", 0, "ひっかく"),  # パラス（v0.3b）p.38。「ワザ」欄は「●ひっかく」で説明文なし
        ("PMCG2-010", 1, "きりさく"),  # パラセクト（v0.4a。1 進化）p.39。「ワザ」欄は「●きりさく」で説明文なし
        ("PMCG1-030", 0, "オーロラビーム"),  # ジュゴン（v0.4a。1 進化）p.102。「ワザ」欄は「●オーロラビーム」で説明文なし
        # フシギソウ（v0.5。1 進化）p.14。「ワザ」欄は「●つるのむち」で説明文なし。kyuura の名前は「つるのムチ」（図版・ワザ欄は
        # ひらがなの「むち」。kyuura との食い違い。data-provenance.md）。登録の照合は kyuura の写しの値
        ("PMCG1-008", 0, "つるのムチ"),
        ("PMCG1-011", 0, "ソーラービーム"),  # フシギバナ（v0.5。2 進化）p.16。「ワザ」欄は「●ソーラービーム」で説明文なし
        ("PMCG1-027", 1, "かみつく"),  # カメール（v0.6。1 進化）p.88。「ワザ」欄は「●かみつく」で説明文なし
        ("PMCG1-046", 1, "ちょうねんりき"),  # ユンゲラー（v0.7。1 進化）p.151。「ワザ」欄は「●ちょうねんりき」で説明文なし
    ])
    | {
        # ドードー（v0.2d）p.231。ダメージの目安「10×」、説明はコイン 2 枚の「おもて」の数×10
        AttackKey("PMCG1-061", 0): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=10),
            "みだれづき",
            text_ja="コインを2枚投げて「おもて」の数×10のダメージをあたえる。",
            play_text_ja="コインを2枚投げ、「おもて」の数×10のダメージ。",
            source="P43 p.231",
        ),
        # ビードル（v0.3a）p.19。相手に 10（目安の数字）、コインが「おもて」なら相手をどく状態に
        AttackKey("PMCG1-004", 0): AttackEntry(
            PoisonOnHeads(),
            "どくばり",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            source="P43 p.19",
        ),
        # キャタピー（v0.3b）p.17。相手に 10（目安の数字）、コインが「おもて」なら相手をマヒ状態に
        AttackKey("PMCG1-002", 0): AttackEntry(
            ParalyzeOnHeads(),
            "いとをはく",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source="P43 p.17",
        ),
        # ロコン（v0.3c）p.67。相手に 10（目安の数字）、コインが「おもて」なら相手をこんらん状態に
        AttackKey("PMCG1-015", 0): AttackEntry(
            ConfuseOnHeads(),
            "あやしいひかり",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            source="P43 p.67",
        ),
        # パラス（v0.3b）p.38。ダメージの目安の数字がない。ダメージを与えず、相手をねむり状態に
        AttackKey("PMCG2-003", 1): AttackEntry(
            PutToSleep(),
            "キノコのほうし",
            text_ja="相手を「ねむり」状態にする。",
            play_text_ja="相手を「ねむり」状態にする。",
            source="P43 p.38",
        ),
        # パラセクト（v0.4a。パラスから進化）p.39。パラスの「キノコのほうし」と同じ説明（p.39 の解説「ジャングルの「パラス」と
        # まったく同じ「キノコのほうし」です。ワザを使うためのエネルギーの種類も必要な個数もまったく変わっていません」）
        AttackKey("PMCG2-010", 0): AttackEntry(
            PutToSleep(),
            "キノコのほうし",
            text_ja="相手を「ねむり」状態にする。",
            play_text_ja="相手を「ねむり」状態にする。",
            source="P43 p.39",
        ),
        # ジュゴン（v0.4a。パウワウから進化）p.102。相手に 30（目安の数字）、コインが「おもて」なら相手をマヒ状態に
        # （キャタピーの「いとをはく」と同じ説明。p.102 の解説「「れいとうビーム」で相手がマヒ状態になれば」）
        AttackKey("PMCG1-030", 1): AttackEntry(
            ParalyzeOnHeads(),
            "れいとうビーム",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source="P43 p.102",
        ),
        # トランセル（v0.4b。キャタピーから進化）p.18。かたまる: ダメージの目安の数字がない。コインが「おもて」なら、次の
        # 相手の番、自分は「ダメージを受けない」状態。カードに印刷された説明（kyuura の写し）と最新の説明は違う（最新の説明に
        # 「（ダメージ以外の効果は受ける）」がある。実装は最新の説明にしたがう。docs/harden-v0.4b.md）
        AttackKey("PMCG1-003", 0): AttackEntry(
            PreventDamageOnHeads(),
            "かたまる",
            text_ja="コインを投げて「おもて」なら、次の相手の番にうけるダメージが0になる。",
            play_text_ja="コインを投げて「おもて」なら、次の相手の番、このカードはダメージを受けない。（ダメージ以外の効果は受ける）",
            source="P43 p.18",
        ),
        # トランセル p.18。しびれごな: 相手に 20（目安の数字）、コインが「おもて」なら相手をマヒ状態に（キャタピーの
        # 「いとをはく」（p.17）と同じ最新の説明。p.18 の解説「20ダメージを与え、コイントスで表を出せば相手の対戦ポケモンを
        # マヒ状態にすることができます」）
        AttackKey("PMCG1-003", 1): AttackEntry(
            ParalyzeOnHeads(),
            "しびれごな",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source="P43 p.18",
        ),
        # コクーン（v0.4b。ビードルから進化）p.21。かたまる: トランセルの「かたまる」と同じ印刷の説明・最新の説明（カードごとに照合した）
        AttackKey("PMCG1-009", 0): AttackEntry(
            PreventDamageOnHeads(),
            "かたまる",
            text_ja="コインを投げて「おもて」なら、次の相手の番にうけるダメージが0になる。",
            play_text_ja="コインを投げて「おもて」なら、次の相手の番、このカードはダメージを受けない。（ダメージ以外の効果は受ける）",
            source="P43 p.21",
        ),
        # コクーン p.21。どくのこな: 相手に 20（目安の数字）、コインが「おもて」なら相手をどく状態に（ビードルの「どくばり」
        # （p.19）と同じ最新の説明。p.21 の解説「20ダメージを与えつつ…コイントス表で相手がどく状態になったら」）
        AttackKey("PMCG1-009", 1): AttackEntry(
            PoisonOnHeads(),
            "どくのこな",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            source="P43 p.21",
        ),
        # スピアー（v0.4c。コクーンから進化する 2 進化ポケモン）p.21。ダブルニードル: ダメージの目安「30×」、最新の説明は
        # コイン 2 枚の「おもて」の数×30（ドードーの「みだれづき」と同じ実装で、数だけ違う。p.21 の解説「最大で60ダメージ」）
        AttackKey("PMCG1-012", 0): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=30),
            "ダブルニードル",
            text_ja="コインを2枚投げて「おもて」の出た数×30のダメージ。",
            play_text_ja="コインを2枚投げ、「おもて」の数×30のダメージ。",
            source="P43 p.21",
        ),
        # スピアー p.21。どくばり: 相手に 40（目安の数字）、コインが「おもて」なら相手をどく状態に。ビードルの「どくばり」
        # （p.19。必要なエネルギー・ダメージが違う）とは別のワザとして、スピアーのカード id で登録する（最新の説明の文面は同じ。
        # p.21 の解説「ダメージ40に加えてコイントスで表を出せば相手の対戦ポケモンをどく状態にする」）
        AttackKey("PMCG1-012", 1): AttackEntry(
            PoisonOnHeads(),
            "どくばり",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            source="P43 p.21",
        ),
        # バタフリー（v0.4d。トランセルから進化する 2 進化ポケモン）p.19。ふきとばし: 相手に 20（目安の数字）、相手の対戦ポケモンを
        # ベンチにもどし、相手が選んだ控えポケモンと入れ替える（控えがいなければ入れ替えない）。印刷の説明（kyuura の写し）と最新の
        # 説明は書き方が違う（「控えポケモンは相手プレイヤーがえらぶ」／「入れ替わるポケモンは、相手が選ぶ」）。処理は最新の説明と
        # p.213 のワザ解説にしたがう（docs/butterfree-v0.4d.md・docs/forced-switch-v0.4d.md）
        AttackKey("PMCG2-007", 0): AttackEntry(
            DamageAndForceSwitch(),
            "ふきとばし",
            text_ja="相手を控えポケモンと入れ替える。控えポケモンは相手プレイヤーがえらぶ。相手プレイヤーに控えポケモンがいないときには入れ替えはおこらない。",
            play_text_ja="相手を控えポケモンと入れ替える。入れ替わるポケモンは、相手が選ぶ。（相手に控えがいないとき、入れ替えはおこらない）",
            source="P43 p.19",
        ),
        # バタフリー p.19。メガドレイン: 相手に 40（目安の数字）、ダメージを与えたら、その半分（切り上げ）のダメージカウンターを自分から
        # とりのぞく。印刷の説明は「相手に与えたダメージの半分（切り上げ）の…」、最新の説明は「相手にダメージを与えたら、その半分…」
        # （与えなかったときに回復しないことがはっきり書かれている。docs/damage-drain-v0.4d.md）
        AttackKey("PMCG2-007", 1): AttackEntry(
            DamageAndDrain(),
            "メガドレイン",
            text_ja="相手に与えたダメージの半分(切り上げ)のダメージカウンターを自分からとりのぞく。",
            play_text_ja="相手にダメージを与えたら、その半分（切り上げ）のダメージカウンターを、自分からとりのぞく。",
            source="P43 p.19",
        ),
        # フシギダネ（v0.5）p.13。やどりぎのタネ: 相手に 20（目安の数字）、ダメージを与えたら自分のダメージカウンターを 1 個とりのぞく。
        # 印刷の文面は「…とりのぞくことができる」、最新の説明は「…1個とりのぞく」（docs/bulbasaur-line-v0.5.md）
        AttackKey("PMCG1-001", 0): AttackEntry(
            DamageAndRemoveCounters(counters=1),
            "やどりぎのタネ",
            text_ja="相手にダメージをあたえることができたら、その時点で自分のダメージカウンターを1つとりのぞくことができる。",
            play_text_ja="相手にダメージを与えたら、自分にのっているダメージカウンターを1個とりのぞく。",
            source="P43 p.13",
        ),
        # フシギソウ（v0.5。フシギダネから進化）p.14。どくのこな: 相手に 20（目安の数字）、コインを投げずに相手をどく状態に
        # （p.14 の解説「確実に対戦ポケモンをどく状態にする「どくのこな」」。コクーンの「どくのこな」（v0.4b。コインあり）とは別のワザ）
        AttackKey("PMCG1-008", 1): AttackEntry(
            PoisonOpponent(),
            "どくのこな",
            text_ja="相手を「どく」状態にする。",
            play_text_ja="相手を「どく」状態にする。",
            source="P43 p.14",
        ),
        # ゼニガメ（v0.6）p.87。あわ: 相手に 10（目安の数字）、コインが「おもて」なら相手をマヒ状態に（キャタピーの「いとをはく」と同じ形。
        # p.87 の解説「10ダメージを与えて、コイントスが表なら相手の対戦ポケモンをマヒ状態にします」）
        AttackKey("PMCG1-023", 0): AttackEntry(
            ParalyzeOnHeads(),
            "あわ",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source="P43 p.87",
        ),
        # ゼニガメ（v0.6）p.87・カメール（v0.6。ゼニガメから進化）p.88。からにこもる: ダメージの目安なし。コインが「おもて」なら、次の相手の番、
        # このカードはダメージを受けない（トランセル・コクーンの「かたまる」（v0.4b）と同じ最新の説明。印刷の文面「…受けるダメージが0になる。」
        # にはしたがわない。docs/rain-dance-v0.6.md 5 章）
        AttackKey("PMCG1-023", 1): AttackEntry(
            PreventDamageOnHeads(),
            "からにこもる",
            text_ja="コインを投げて「おもて」なら、次の相手の番に受けるダメージが0になる。",
            play_text_ja="コインを投げて「おもて」なら、次の相手の番、このカードはダメージを受けない。（ダメージ以外の効果は受ける）",
            source="P43 p.87",
        ),
        AttackKey("PMCG1-027", 0): AttackEntry(
            PreventDamageOnHeads(),
            "からにこもる",
            text_ja="コインを投げて「おもて」なら、次の相手の番に受けるダメージが0になる。",
            play_text_ja="コインを投げて「おもて」なら、次の相手の番、このカードはダメージを受けない。（ダメージ以外の効果は受ける）",
            source="P43 p.88",
        ),
        # カメックス（v0.6。カメールから進化）p.90。ハイドロポンプ: ダメージの目安「40+」。必要なエネルギー（水 3）よりも多い「水」エネルギー
        # 1 個につき 10 を、2 個ぶんまで追加（p.88 の解説「水エネルギー5個までなら…「ハイドロポンプ」で活用できる」）
        AttackKey("PMCG1-032", 0): AttackEntry(
            ExtraEnergyDamage(energy_type=EnergyType.WATER, per_energy=10, max_extra=2),
            "ハイドロポンプ",
            text_ja="「水」エネルギーを1つ追加すると、10ダメージ追加できる。(追加は2つまで)",
            play_text_ja="ワザに必要なエネルギーよりも多く「水」エネルギーがついているとき、多い「水」エネルギー1個につき、10ダメージを追加する。ダメージ追加は2個ぶんまで。",
            source="P43 p.90",
        ),
        # ケーシィ（v0.7）p.149。ねんりき: 相手に 10（目安の数字）、コインが「おもて」なら相手をマヒ状態に（キャタピーの「いとをはく」・
        # ゼニガメの「あわ」と同じ最新の説明。kyuura の写しは「コインを投げて、「おもて」なら、…」で読点が 1 つ多い（照合用）
        AttackKey("PMCG1-043", 0): AttackEntry(
            ParalyzeOnHeads(),
            "ねんりき",
            text_ja="コインを投げて、「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source="P43 p.149",
        ),
        # ユンゲラー（v0.7。ケーシィから進化）p.151。じこさいせい: ダメージの目安なし。自分についている「超」エネルギーカードを 1 枚（ワザを
        # 使うプレイヤーが選ぶ）トラッシュして、自分のダメージカウンターをすべてとりのぞく。印刷の文面（kyuura の写し）は「…1枚はがして
        # すてることによってダメージカウンターを全てとりのぞく。」（docs/alakazam-line-v0.7.md）
        AttackKey("PMCG1-046", 0): AttackEntry(
            DiscardEnergyAndRemoveAllCounters(energy_type=EnergyType.PSYCHIC),
            "じこさいせい",
            text_ja="自分の「超」エネルギーカードを1枚はがしてすてることによってダメージカウンターを全てとりのぞく。",
            play_text_ja="自分についている「超」エネルギーカードを1枚トラッシュして、自分にのっているダメージカウンターを、すべてとりのぞく。トラッシュできないとき、このワザの効果はなくなる。",
            source="P43 p.151",
        ),
        # フーディン（v0.7。ユンゲラーから進化）p.153。あやしいひかり: 相手に 30（目安の数字）、コインが「おもて」なら相手をこんらん状態に
        # （ロコンの「あやしいひかり」（p.67）と同じ最新の説明。名前が同じでも別の登録）
        AttackKey("PMCG1-049", 0): AttackEntry(
            ConfuseOnHeads(),
            "あやしいひかり",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            source="P43 p.153",
        ),
        # ピカチュウ（v0.2f）p.125。相手に 30（目安の数字）、コインが「うら」なら自分にも 10
        AttackKey("PMCG1-035", 1): AttackEntry(
            SelfDamageOnTails(self_damage=10),
            "でんげき",
            text_ja="コインを投げて「うら」なら、自分にも10ダメージ。",
            play_text_ja="コインを投げて「うら」なら、自分にも10ダメージ。",
            source="P43 p.125",
        ),
    },
    {
        "PMCG1-071": TrainerEntry(
            RemoveDamageCounters(counters=2),
            "きずぐすり",
            "自分の場のポケモンにのっているダメージカウンターを2個まで、とりのぞくことができる。",
            "あなたの場にいるポケモンを1匹選び、そのポケモンにのっているダメージカウンターを、2個とりのぞく。",
            "P43 p.254",
        ),
        "PMCG1-073": TrainerEntry(
            SwitchWithBench(),
            "ポケモンいれかえ",
            "自分の場の対戦ポケモンと控えポケモンを入れ替える。「にげる」ためのエネルギーを支払う必要はない。",
            "あなたの控えポケモンを1匹選び、あなたの対戦ポケモンと入れ替える。",
            "P43 p.254",
        ),
        "PMCG1-074": TrainerEntry(
            DrawCards(count=2),
            "マサキ",
            "山札からカードを2枚引いて、手札に加える。",
            "山札からカードを2枚引いて、手札に加える。",
            "P43 p.254",
        ),
        "PMCG1-079": TrainerEntry(
            AttachedDamageReduction(amount=20),
            "ディフェンダー",
            "次の相手の番の終わりまで、「ワザ」によって受けるダメージを、「-20」できる。自分の場のポケモンにつけて使い、次の自分の番の最初にはがしてすてる。",
            "このカードは、あなたの場にいるポケモンにつけて使い、次の相手の番の終わりにトラッシュする。このカードをつけているポケモンがワザによるダメージを受けるとき、そのダメージは「-20」される。",
            "P43 p.257",
        ),
        "PMCG1-081": TrainerEntry(
            AttachedAttackBonus(amount=10),
            "プラスパワー",
            "自分の対戦ポケモンの「ワザ」によって与えるダメージを「+10」できる。自分の対戦ポケモンにつけて使い、自分の番の終わりに、はがしてすてる。",
            "このカードはあなたの対戦ポケモンにつけて使い、あなたの番の終わりにトラッシュする。このカードをつけているポケモンのワザが、対戦ポケモンにダメージを与えるとき、そのダメージは「+10」される。(控えポケモンへのダメージは、そのまま)",
            "P43 p.257",
        ),
    },
    {
        # フシギバナ（v0.5）p.16（カードのページ）・p.323（公式ルール「14 ポケモンの特殊能力」に同じ最新の説明）。エナジートランス: 自分の
        # 番の中で何度でも、自分の場のポケモンについている「草」エネルギーを、自分の場の別のポケモンにつけかえる。印刷の文面（kyuura の写し）
        # は「…好きなだけ移動させることができる。…状態の時には使えない。」（docs/venusaur-v0.5.md）
        PowerKey("PMCG1-011", 0): PowerEntry(
            EnergyTransfer(energy_type=EnergyType.GRASS),
            "エナジートランス",
            "フシギバナは自分の場にある「草」エネルギーを好きなだけ移動させることができる。「ねむり・マヒ・こんらん」状態の時には使えない。",
            "この力は、自分の番の中で何度でも使える。自分の場にいるポケモンについている「草」エネルギーを、自分の場にいる別のポケモンにつけかえる。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない。",
            "P43 p.16・p.323",
        ),
        # カメックス（v0.6）p.90。あまごい: 自分の番の中で何度でも、自分の手札から「水」エネルギーカードを出して、自分の場の「水」ポケモンに
        # つける。印刷の文面（kyuura の写し）は「…手札の「水」エネルギーを1度に何枚でもつけることができる。…状態の時は使えない。」。
        # 手札からつける通常の操作（p.310。1 番に 1 枚）との関係は docs/rain-dance-v0.6.md の R11〜R13
        PowerKey("PMCG1-032", 0): PowerEntry(
            AttachEnergyFromHand(energy_type=EnergyType.WATER, pokemon_type=EnergyType.WATER),
            "あまごい",
            "カメックスは自分の「水」ポケモンに対して、手札の「水」エネルギーを1度に何枚でもつけることができる。「ねむり・マヒ・こんらん」状態の時は使えない。",
            "この力は、自分の番の中で何度でも使える。自分の手札から「水」エネルギーカードを出して、自分の場の「水」ポケモンにつける。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない。",
            "P43 p.90",
        ),
        # フーディン（v0.7）p.153。ダメージスワップ: 自分の番の中で何度でも、この力によってポケモンが「きぜつ」しないかぎり、自分の場にいる
        # ポケモンにのっているダメージカウンターを、自分の場にいる別のポケモンにのせかえる。印刷の文面（kyuura の写し）は「…ポケモンが
        # 「きぜつ」しない範囲で自由に移動できる。…状態の時は使えない。」（docs/damage-swap-v0.7.md）
        PowerKey("PMCG1-049", 0): PowerEntry(
            MoveDamageCounter(),
            "ダメージスワップ",
            "自分の場に出ているポケモンのダメージカウンターを、ポケモンが「きぜつ」しない範囲で自由に移動できる。「ねむり・マヒ・こんらん」状態の時は使えない。",
            "この力は、自分の番の中で何度でも使える。この力によってポケモンが「きぜつ」しないかぎり、自分の場にいるポケモンにのっているダメージカウンターを、自分の場にいる別のポケモンにのせかえる。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない。",
            "P43 p.153",
        ),
    },
)

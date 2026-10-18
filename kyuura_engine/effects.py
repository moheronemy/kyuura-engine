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
  説明。docs/alakazam-line-v0.7.md）。``PoisonWithoutDamage``・``CoinBonusDamageAndParalyze``（v0.8。ロケット団のベトベターの
  「どくガス」「ねばりつく」。docs/grimer-line-v0.8.md）。``SleepOpponent``（v0.9。相手にダメージのあと、コインを投げずに相手を
  ねむり状態に。化石の秘密のゴーストの「あくむ」。p.160）・``RecoverEnergyAndSelfDamage``（v0.9。自分のトラッシュのエネルギー
  カードを最大 2 枚手札に加え、その後、自分にダメージ。化石の秘密のゴースの「エナジーへんかん」。p.158。docs/haunter-line-v0.9.md）。
  ``CoinHeadsDamagePerOwnCounter``（v0.11。コインが「おもて」なら自分のダメージカウンターの数 × n。サカキのワンリキーの「いかりの
  スーパーパンチ」。p.189）・``SelfDamageInsteadOnTails``（v0.11。コインが「うら」なら相手にはダメージを与えず自分にダメージ。
  サカキのゴーリキーの「いちかばちか」。p.191。docs/giovanni-machamp-line-v0.11.md）。``DamageAndRetaliation``（v0.12。相手にダメージの
  あと、自分に「次の相手の番、このカードが相手のワザによるダメージを受けたとき、相手に10ダメージを与える」持続する効果（``state.Retaliation``）。
  R団のファイヤーの「ほのおのかべ」。p.82。そのダメージは、解決の基盤がダメージを受けたときに記録し、ダメージの要素のあとの窓で R団の
  ファイヤーのワザによるダメージとして与える（v0.16b から ``resolution.kernel.attack_damage_to_damage_source``。v0.15 までは v0.13 の
  ``_apply_retaliation``）。docs/rocket-moltres-v0.12.md・docs/temporary-attack-effects-v0.12.md）
- トレーナー（v0.2b）: マサキ ``DrawCards``、きずぐすり ``RemoveDamageCounters``、
  ポケモンいれかえ ``SwitchWithBench``。処理は『ポケモンカードオフィシャルブック2000』p.254 の
  「最新の説明」にしたがう（``TrainerEntry.play_text_ja``。docs/trainers-v0.2b.md）
- トレーナー（v0.19）: オーキドはかせ ``DiscardHandAndDraw``（p.255 の最新の説明。手札をすべてトラッシュし、その後 7 枚引く。
  docs/professor-oak-v0.19.md）
- トレーナー（v0.21）: 突風 ``SwitchOpponentWithBench``（p.255 の最新の説明。使ったプレイヤーが相手の控えポケモンを 1 匹選び、相手の
  対戦ポケモンと入れ替える。入れ替えはポケモンいれかえと共通の ``_switch_active_with_bench``。docs/gust-v0.21.md）
- トレーナー（v0.22）: パソコン通信 ``DiscardFromHandThenSearchDeck``（p.260 の最新の説明。使うための条件として手札から 2 枚選んでトラッシュ
  し、山札から 1 枚選び出して手札に加え、山札を切る。2 段階のトレーナーの決定。docs/computer-search-v0.22.md）
- トレーナー（v0.23）: エネルギー回収 ``DiscardFromHandThenRetrieveEnergy``（p.257 の最新の説明。使うための条件として手札から 1 枚選んで
  トラッシュし、トラッシュの基本エネルギーカード（そのトラッシュしたカードを除く）を最大 2 枚選び出して手札に加える。2 段階のトレーナーの
  決定。docs/energy-retrieval-v0.23.md）
- トレーナー（v0.24）: ポケモン交換おじさん ``TradePokemonWithDeck``（p.259 の最新の説明。手札のたねポケモン・進化カードを 1 枚、相手に
  見せて山札にもどし、山札のたねポケモン・進化カードを 1 枚、相手に見せて手札に加え、山札を切る。2 段階のトレーナーの決定。
  docs/pokemon-trader-v0.24.md）
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
  ``MoveDamageCounter``（p.153・p.320。docs/damage-swap-v0.7.md）、v0.8 でベトベトンの「かがくへんかガス」 ``SuppressOtherPowers``
  （常にはたらく。宣言しない。p.48・p.323。docs/chemical-gas-v0.8.md）、v0.9 でゴーストの「とうめい」 ``AttackImmunityOnHeads``
  （ワザによってダメージや効果を受けるときに自動的にはたらく。宣言しない。p.159・p.160・p.323。ワザの要素の処理の境界で
  ``attack_reaches`` が評価する。docs/transparency-v0.9.md・docs/automatic-powers-v0.9.md）、v0.10 でカイリキーの「はんげき」
  ``CounterattackDamage``（相手のワザによってダメージを受けたときに自動的にはたらく。宣言しない。``finish_damage_elements`` が
  与える。docs/counterattack-v0.10.md）、v0.11 でサカキのカイリキーの「こんじょう」 ``PreventKnockOutOnHeads``（相手のワザによる
  ダメージで「きぜつ」するとき、使える。宣言する特殊能力で、ワザのあとのきぜつの判定でエンジンが持ち主に決定で使うかを聞く。
  p.193・p.311。docs/guts-v0.11.md・docs/ko-prevention-v0.11.md）、v0.12 で R団のファイヤーの「ふしちょう」 ``ReturnToHandOnKnockOut``
  （このカードが「きぜつ」したとき、使える。宣言する特殊能力で、きぜつの処理（トラッシュ・サイド・勝ち負けの判定）のあと、対戦が続くなら
  エンジンが持ち主に決定で使うかを聞く。使えばこのカードをトラッシュから手札に加える。p.82・p.311。docs/phoenix-v0.12.md・
  docs/post-knockout-powers-v0.12.md）を加えた

ほかのポケモンパワー・特殊エネルギー・ほかの効果のあるワザ・ほかのトレーナーは、実装を登録するまで未対応です。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Iterable, Mapping

from .cards import EnergyType, can_pay_cost
from .coins import CoinSide, flip_coins
from .conditions import CONFUSION, CURED, PARALYSIS, POISON, SLEEP, SWITCH, clear_special_conditions, confuse, put_to_sleep
from .damage import HALVE_DOWN, HALVE_UP, MULTIPLY, SET, SET_IF_AT_LEAST, ZERO_IF_AT_LEAST, ZERO_IF_BELOW, DamageModifier, calculate_attack_damage
from .decisions import (
    ATTACH_FROM_DECK, ATTACH_FROM_DISCARD, ATTACH_FROM_HAND, ATTACH_TO_BENCH, BENCH_FROM_DECK, DISCARD_ENERGY, DISCARD_FROM_HAND, DISCARD_OPPONENT_ENERGY, ENTRY_POWER, FORCED_SWITCH,
    DISCARD_TO_DECK_TOP, HAND_TO_DECK, MOVE_ENERGY, MOVE_OPPONENT_ENERGY, RECOVER_ENERGY, RECOVER_POKEMON, RECOVER_TRAINER, REMOVE_COUNTERS, RETRIEVE_ENERGY, RETURN_ENERGY,
    RETURN_TO_DECK, SEARCH_DECK, SELECT_ATTACK,
    SELECT_EVOLUTION_CARD, SELECT_OPPONENT_ATTACK, SELECT_POKEMON, SELECT_SPECIAL_CONDITION, push_power_decision,
    ARRANGE_DECK_TOP, PEEK_CARD, SELECT_DECK_OWNER, SELECT_HAND_CARD, SELECT_LOOK_COUNT, SELECT_PRIZE_CARD,
    SELECT_COLOR, SELECT_DEVOLVE_COUNT, BENCH_FROM_DISCARD, DISCARD_TO_DECK, SELECT_DRAW_COUNT, push_trainer_decision,
    TAKE_LOOKED_CARDS, OPPONENT_HAND_TO_DECK, SELECT_COUNTER_COUNT,
)
from .errors import IllegalActionError, UnsupportedError
from .evolution import (
    DEVOLVE_TO_DISCARD,
    DEVOLVED_THIS_TURN_CODE,
    DEVOLVED_THIS_TURN_REASON,
    PERMISSION_FROM_DECK_CODE,
    devolve,
    devolved_this_turn,
    evolution_block,
    evolution_prevented,
    place_evolution_card,
    skipped_stage1_basic,
    turn_restriction,
)
from .persistent import (
    attack_barrier,
    damage_prevention,
    damage_reduction,
    effect_attack_card,
    halved_damage,
    max_hp_set,
    next_turn_attack_damage,
    reduced_damage_to_source,
    RETURN_IN_PLAY_TO_DECK,
    RETURN_IN_PLAY_TO_HAND,
    remove_persistent_effects,
    resistance_change,
    retaliation,
    weakness_change,
    zero_damage_below,
)
from .state import NEXT_TURN_MULTIPLY, RETALIATION_FIXED, RETALIATION_RECEIVED, Retaliation, mark_returned_to_bench
from .zones import (
    attach_energy_from_hand, attach_trainer, bench_from_deck, bench_from_discard, discard_attached_cards, discard_from_hand, discard_hand, draw_cards, return_discard_to_hand,
    return_basic_to_hand, return_hand_to_deck, return_in_play_to_deck, return_in_play_to_hand, reveal_deck_to_hand, search_deck_to_hand, shuffle_deck,
    look_at_card, put_trainer_into_play, swap_prize_with_deck_top, put_discard_on_deck_top, return_discard_to_deck, return_hand_cards_to_deck,
    look_at_hand, return_revealed_hand_cards_to_deck, reveal_hand,
    discard_attached_energy_cards, return_attached_energy_to_hand, move_attached_energy, opponent_hand_card_to_deck, take_looked_deck_cards,
    discard_pile_to_deck, deck_top_to_discard,
)

if TYPE_CHECKING:
    from .cards import Attack, CardDefinition, Power
    from .state import AttachedTrainer, GameState, PendingDecision, PokemonInPlay, RecallEffect


@dataclass(frozen=True, order=True)
class AttackKey:
    """ワザの安定した識別子: カード id とワザの位置（カードに印刷された順、0 から）。"""

    card_id: str
    attack_index: int

    def __str__(self) -> str:
        return f"{self.card_id}#{self.attack_index}"


@dataclass(frozen=True)
class AttackUse:
    """ワザを 1 回使ったときの情報: ワザを使ったプレイヤー・ワザを使ったポケモン（場のポケモンの番号）・ワザ（``AttackKey``）。

    宣言の前の確認（``AttackEffect.problem``・``damage_profile``・``decision_problems`` と v0.13 の止める関数）に渡す。

    ``runtime``（v0.16b）: 解決の基盤がワザを処理している間だけ持つ、そのワザの枠への入口（``resolution.contract.ContractRuntime``）。
    v0.13 の約束で書いたワザの実装（``resolve``・``resume``）が呼ぶ補助関数（``deal_attack_damage``・``damage_opponent_active``・
    ``attack_reaches``・``finish_damage_elements``・``decisions.push_attack_decision``・``_require_not_evaded``）は、これに委ねる（ダメージ・
    ダメージを受けたときの効果・決定は、ほかのワザと同じ解決の基盤の窓を通る）。``runtime`` のない ``AttackUse`` で補助関数を呼ぶと
    ``RuntimeError``（解決の基盤を通らずにダメージをのせることを許さない）。比較・ハッシュ・表示に含めない（状態に持たない）。

    v0.15 まで持っていたワザ 1 回の中の記録の項目は、解決の基盤の枠が持つ（v0.16b。docs/kernel-consolidation-v0.16b.md 3.4 節）:

    - ``reception``（v0.9。「とうめい」のコインで決まった、受けるか）・``ko_prevention_able``（v0.11。ダメージを受けるときの「こんじょう」を
      使えるかの写し）: ``runtime`` の値そのもの（場のポケモンの番号 → 真偽）を返す読み取りの項目にした。
    - ``counterattacks``（v0.10）・``retaliations``（v0.12）: まだ与えていない送る効果の一覧。解決の基盤の枠の ``pending``（``kernel.Deferred``）
      が持つので外した（ワザの実装が読み書きするものではない）。
    """

    player: int
    pokemon_id: int
    key: AttackKey
    runtime: Any = field(default=None, compare=False, repr=False)

    @property
    def reception(self) -> dict[int, bool]:
        return _runtime(self, "AttackUse.reception").reception

    @property
    def ko_prevention_able(self) -> dict[int, bool]:
        return _runtime(self, "AttackUse.ko_prevention_able").ko_prevention_able


def _runtime(use: AttackUse, what: str):
    """``use`` の、解決の基盤のワザの枠への入口（v0.16b）。なければ ``RuntimeError``。"""
    runtime = getattr(use, "runtime", None)
    if runtime is None:
        raise RuntimeError(
            f"{what} は、解決の基盤がワザを処理している間だけ使える（AttackUse に解決の基盤の入口がない。旧経路は v0.16b で外した。"
            "試験では resolution.open_attack で枠を開く）"
        )
    return runtime


class AttackEffect:
    """ワザの効果の実装の基底。

    - ``check``: カードのデータ（説明文・ダメージ）がこの実装で処理できる形かを確かめ、問題を返す。
      登録の誤り（効果のあるワザを、効果のない実装に登録するなど）を見つけるため。
    - ``resolve``: ワザの処理（p.309 の手順 6「ワザの説明にしたがって処理」）の、v0.13 の約束。途中でプレイヤーの決定が要るときは、
      ``decisions.push_attack_decision`` で決定を出して戻る。v0.16b から、製品の登録表のワザ（24 種類）は解決の基盤の要素の並び
      （``resolution.programs.BUILDERS``）で処理し、``resolve`` を持たない。``resolve`` を上書きした実装（テスト・外の登録表の実装）は、
      解決の基盤が枠の中で呼ぶ（``resolution.contract``。補助関数は解決の基盤の部品に委ねる）。既定の ``resolve`` は、最も近い
      対応表の型の要素の並びを今の枠の中で処理する（部分型の ``super().resolve`` のため）。
    - ``resume``: 出した決定が選ばれたあとの続き。さらに決定を出してもよい（複数段階の選択）。既定は ``resolve`` と同じく、最も近い
      対応表の型の要素の並びの続き。
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

    - ``damage_profile``（v0.10）: このワザのダメージの要素が、コインなどのどの結果でも与えうる基本となるダメージ（p.321 の
      1 段階）の候補（``DamageProfile``）。状態を変えず、乱数を使わない。エンジンがワザの宣言の前に、ダメージを受けたときに
      自動的にはたらく特殊能力（カイリキーの「はんげき」）で原典で決められない場合になりうるかを確かめるのに使う
      （``counterattack_double_knockout_problem``）。既定は、ダメージの目安の数字（なければダメージの要素なし）と、自分への
      ダメージなし。ダメージの目安に「×」「+」「−」があるワザは上書きする（上書きしないと ``NotImplementedError``。確かめないまま
      通さない）。自分にダメージを与えるワザも上書きする（既定は自分へのダメージなしなので、上書きしないと C18 を見落とす）。

    - ``card_problems``（v0.27）: このワザの登録が、同じカードのほかのワザ（位置・名前・ダメージ）と合うか。ほかのワザを指す実装だけが上書きする。

    - ``opponent_effect_elements``（v0.11）: このワザが相手の対戦ポケモンに与える、ダメージ以外の効果の要素の種類（``ATTACK_ELEMENTS``
      のうち ``DAMAGE_ELEMENT`` 以外。特殊状態・入れ替え）。既定は空。相手に効果を与えるワザの実装は宣言する（tests/test_guts_v0_11.py が、
      実装の中で相手に効果を与える ``attack_reaches`` の要素と同じかを確かめる）。エンジンがワザの宣言の前に、相手のワザによるダメージで
      きぜつするときに使える特殊能力（「こんじょう」）との順番が原典で決められない場合（docs/guts-v0.11.md の G37）を確かめるのに使う
      （``ko_prevention_attack_effect_problem``）。

    決定がなくなったら、エンジンがワザの後の処理（きぜつ・サイド・番の終わり）を続ける。
    """

    implementation_id = "abstract"
    opponent_effect_elements: ClassVar[tuple[str, ...]] = ()
    # v0.38: ワザを使ったポケモンがワザの効果で場をはなれたあとに、ワザの途中の決定を出すことがある（キョウのポッポの「でんれい」）。不変条件
    # （``engine._attack_decision_problems``）が、場にいないポケモンのワザの続きを、今の番のログ ``return_in_play_to_deck`` と照らして許す
    leaves_play_before_decisions: ClassVar[bool] = False
    # v0.44: 「このワザは、このカードが場に出てから、1回しか使えない」ワザ（``OnceAfterEntryNoDamageOnTails``）。宣言の確認（``checks.attack_request``）が、
    # 場のポケモンの記録（``PokemonInPlay.attacks_used_once``）にあれば ``ATTACK_ALREADY_USED`` で拒否し、宣言のときに記録する（``resolution.flow``）
    once_after_entering_play: ClassVar[bool] = False

    def check(self, attack: Attack) -> list[str]:
        return []

    def card_problems(self, attack: Attack, attacks: tuple[Attack, ...]) -> list[str]:
        """このワザの登録が、同じカードのほかのワザと合うか（v0.27）。``attacks`` はそのカードのワザのすべて（データの順）。既定は問題なし。
        ほかのワザを指す実装（「つるぎのまい」が変える「きりさく」の位置）は上書きする。分類（``cards.py``）と使うときの確認
        （``checks.py``）が ``EffectRegistry.attack_problem`` を通して呼ぶ。"""
        return []

    def problem(self, state: GameState, use: AttackUse) -> UnsupportedError | None:
        return None

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = attack_of(state, use.key)  # v0.49: ワザを印刷したカード（use.key）
        if attack.damage_modifier is not None:
            raise NotImplementedError(
                f"{self.implementation_id}: ダメージの目安に「{attack.damage_modifier}」があるワザは damage_profile を上書きする"
            )
        if attack.damage is None:
            return DamageProfile()
        return DamageProfile(opponent=(attack.damage,))

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _runtime(use, f"{self.implementation_id} の resolve").run_builtin(state, self)

    def resume(self, state: GameState, use: AttackUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        _runtime(use, f"{self.implementation_id} の resume").resume_builtin(state, self, decision, choices)

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        if decision.player != use.player:
            return [
                f"ワザ {use.key} の決定 {decision.kind} をするのがプレイヤー {decision.player} で、ワザを使ったプレイヤー {use.player} では"
                "ない（相手が決定する効果は decision_problems で宣言する）"
            ]
        return []

    def usage_problem(self, state: GameState, attacker: PokemonInPlay) -> IllegalActionError | None:
        """説明に「…ないときは、このワザは使えない」と書かれたワザを使うための条件（v0.31。化石の秘密のヤドンの「ぼーっとする」）。満たさなければ
        その理由（``checks.attack_request`` が、必要なエネルギーの確認のあとで投げる）。既定は条件なし。"""
        return None


@dataclass(frozen=True)
class DamageProfile:
    """ワザのダメージの要素が与えうる基本となるダメージ（p.321 の 1 段階）の候補（v0.10。``AttackEffect.damage_profile``）。

    - ``opponent``: 相手の対戦ポケモン（p.320 のダメージの (1)）への基本となるダメージの候補。ダメージの要素がなければ空。
    - ``self_damage``: ワザを使うポケモン自身（(3)）への基本となるダメージの候補。0 は「自分へのダメージがない」場合（コインの
      結果で与えないときなど）。
    コインで決まるものは、すべての結果の候補を並べる（どの結果になるかは見ない）。弱点・抵抗力・プラスパワーなどは含めない
    （``preview_attack_damage`` が計算する）。
    - ``outcomes``（v0.11）: 相手へのダメージと自分へのダメージが、同じコインの結果でいっしょに起こる組（相手への基本となるダメージ
      （相手へのダメージの要素がない結果は None）, 自分への基本となるダメージ）。空なら ``opponent`` と ``self_damage`` のすべての組
      （v0.10 のワザは、どれもすべての組が起こりうる）。相手へのダメージと自分へのダメージが同じ結果では起こらないワザ（サカキの
      ゴーリキーの「いちかばちか」。「うら」なら相手にはダメージを与えず、自分に 100）は、起こりうる組だけを並べる（``pairs``）。
    """

    opponent: tuple[int, ...] = ()
    self_damage: tuple[int, ...] = (0,)
    outcomes: tuple[tuple[int | None, int], ...] = ()

    def pairs(self) -> tuple[tuple[int | None, int], ...]:
        """同じコインの結果でいっしょに起こりうる（相手への基本となるダメージ（なければ None）, 自分への基本となるダメージ）の組。"""
        if self.outcomes:
            return self.outcomes
        return tuple((opponent, own) for opponent in (self.opponent or (None,)) for own in self.self_damage)


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
        return prevented_coin_damage_problem(state, use)

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

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        # 「おもて」の数（0〜coins 枚）ごとの基本となるダメージ（v0.10）
        return DamageProfile(opponent=tuple(heads * self.damage_per_heads for heads in range(self.coins + 1)))


def prevented_coin_damage_problem(state: GameState, use: AttackUse) -> UnsupportedError | None:
    """ダメージの量だけをコインで決めるワザの要素（``CoinFlipDamage``・v0.11 の ``CoinHeadsDamagePerOwnCounter``）を、「ダメージを
    受けない」状態（v0.4b）の相手の対戦ポケモンに使う場合（``UNRESOLVED_PREVENTED_COIN_DAMAGE``。v0.4b の ``CoinFlipDamage.problem`` を
    v0.11 で関数に分けた。メッセージ・止める条件は同じ）。"""
    target = state.players[1 - use.player].active
    prevention = None if target is None else damage_prevention(state, target)
    if prevention is None:
        return None
    return prevented_coin_damage_error(target.pokemon_id, prevention.kind)


def prevented_coin_damage_error(target_pid: int, prevention_kind: str) -> UnsupportedError:
    """``UNRESOLVED_PREVENTED_COIN_DAMAGE`` の理由（v0.15b で分けた。v0.13 の経路と解決の基盤が同じ文を使う）。"""
    return UnsupportedError(
        "UNRESOLVED_PREVENTED_COIN_DAMAGE",
        f"相手の対戦ポケモン {target_pid} は、この番「ダメージを受けない」状態（{prevention_kind}）。ダメージの量を"
        "コインで決めるワザの要素は無効になる（p.321）が、そのコインを投げるかは『オフィシャルブック2000』（p.309・p.319・"
        "p.320・p.321）から決められないので扱わない（投げるかどうかで乱数の続きが変わる）",
    )


@dataclass(frozen=True)
class CoinHeadsDamagePerOwnCounter(AttackEffect):
    """コインを 1 枚投げ、「おもて」なら、自分（ワザを使うポケモン）にのっているダメージカウンターの数 × ``damage_per_counter`` の
    ダメージを、相手の対戦ポケモンに与える（v0.11。サカキのワンリキーの「いかりのスーパーパンチ」。p.189 の最新の説明「コインを投げて
    「おもて」なら、自分にのっているダメージカウンターの数×20のダメージ。」、ダメージの目安「20×」。docs/giovanni-machamp-line-v0.11.md）。

    - ダメージの目安に「×」があるので、説明にしたがって計算した数のダメージを与える（p.320）。「おもて」なら、コインを投げたときに
      自分にのっているダメージカウンターの数 × 20 が基本となるダメージ（p.321 の 1 段階）。「うら」なら 0（「みだれづき」の「おもて」
      0 枚と同じ。2 段階までで 0 以下なので計算を終え、ダメージを与えなかった。p.321）。カウンターがなければ「おもて」でも 0（p.189 の
      解説「ダメージカウンターが「サカキのワンリキー」にのっていなければ、「いかりのスーパーパンチ」は相手にダメージを与えることが
      できません」）。
    - 数えるのは、このワザを使うポケモンのダメージカウンター（ダメージ ÷ 10。``Rules.damage_per_counter``）。このワザの要素の中で自分の
      ダメージは変わらない（自分へのダメージの要素はない）。
    - コインはダメージの量を決めるためだけに投げる（ほかの要素はない）ので、「ダメージを受けない」状態の相手には、``CoinFlipDamage`` と
      同じく、コインを投げる前に ``UNRESOLVED_PREVENTED_COIN_DAMAGE`` で止める（``prevented_coin_damage_problem``）。
    """

    damage_per_counter: int
    implementation_id = "coin_heads_damage_per_own_counter"

    def __post_init__(self) -> None:
        if type(self.damage_per_counter) is not int or self.damage_per_counter <= 0 or self.damage_per_counter % 10:
            raise ValueError(f"ダメージカウンター 1 個あたりのダメージは 10 の倍数の正の数（{self.damage_per_counter!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier != "×":
            problems.append("ダメージの目安に「×」のないワザを、ダメージカウンターの数×のワザとして登録している")
        if attack.damage != self.damage_per_counter:
            problems.append(f"ダメージの目安の数字 {attack.damage!r} と、登録したカウンター 1 個あたりのダメージ {self.damage_per_counter} が違う")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、コインを投げるワザとして登録している")
        return problems

    def problem(self, state: GameState, use: AttackUse) -> UnsupportedError | None:
        return prevented_coin_damage_problem(state, use)

    def _counters(self, state: GameState, use: AttackUse) -> int:
        _, attacker = state.find_pokemon(use.pokemon_id)
        return attacker.damage // state.rules.damage_per_counter

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        # 「うら」なら 0、「おもて」なら今のダメージカウンターの数 × damage_per_counter（自分のダメージはワザの中で変わらない）
        return DamageProfile(opponent=(0, self._counters(state, use) * self.damage_per_counter))


@dataclass(frozen=True)
class SelfDamageInsteadOnTails(AttackEffect):
    """コインを 1 枚投げ、「おもて」なら相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ、「うら」なら相手にはダメージを与えず、
    自分（ワザを使うポケモン）に ``self_damage`` ダメージ（v0.11。サカキのゴーリキーの「いちかばちか」。p.191 の最新の説明「コインを
    投げて「うら」なら、相手にはダメージを与えず、自分に100ダメージ。」、ダメージの目安「60」。docs/giovanni-machamp-line-v0.11.md）。

    - ダメージの目安に「×」がないので、説明の最初の「相手に60ダメージ。」が省略されている（p.320）。「うら」のときは、その相手への
      ダメージの要素がなく（「相手にはダメージを与えず」）、代わりに自分へのダメージの要素がある。どちらの要素を処理するかがコインで
      決まるので、コインはダメージの前に投げる。
    - 自分へのダメージは p.320 のダメージの分類の (3)。ワザによるダメージ（p.321）なので、相手へのダメージと同じ順番で計算する
      （``deal_attack_damage`` の ``SELF``。v0.3d の自分へのダメージの弱点・抵抗力。プラスパワー・ディフェンダーも計算する。p.191 の
      解説「きぜつしないためには「ディフェンダー」を2枚つけてようやくです」）。
    - 「うら」では相手はダメージを受けない（ダメージの要素がない）ので、相手の「とうめい」（v0.9）・「はんげき」（v0.10）は評価しない。
    - コインは相手へのダメージの量だけでなく自分へのダメージの要素も決める（その要素は「ダメージを受けない」状態の相手でも有効）ので、
      ``CoinFlipDamage`` の ``UNRESOLVED_PREVENTED_COIN_DAMAGE`` には当たらない（``CoinBonusDamageAndParalyze`` と同じ考え方）。
    """

    self_damage: int
    implementation_id = "self_damage_instead_on_tails"

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
            problems.append("説明文のないワザを、「うら」なら自分にダメージのワザとして登録している")
        return problems

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        # 「おもて」なら相手に目安の数字・自分へは 0、「うら」なら相手へのダメージの要素はなく（None）自分へ self_damage。2 つの結果は
        # 同時に起こらないので、起こりうる組（outcomes）を並べる（v0.10 の C18 の判定で、起こらない組で止めないため）
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = attack_of(state, use.key)  # v0.49: ワザを印刷したカード（use.key）
        return DamageProfile(
            opponent=(attack.damage,), self_damage=(0, self.self_damage), outcomes=((attack.damage, 0), (None, self.self_damage))
        )


# ワザのダメージを受けるポケモン（p.320「ワザの要素」のダメージの分類）。(1)・(3) と、v0.31 から (2) 相手の控えポケモン。
# (2) の受けるポケモンは、ワザの説明が選ばせる・決める場の番号で指す（解決の基盤の ``kernel.deal_damage`` の ``pokemon_id``）。控えポケモンへの
# ダメージの計算: プラスパワー（5 段階）は変えない（p.257 の最新の説明「(控えポケモンへのダメージは、そのまま)」。CONFIRMED）、ディフェンダー
# （7 段階）は変える（docs/defender-v0.2e.md の 16。SUPPORTED）。v0.31 の対応カードの控えポケモンへのダメージは、どれも説明に「「弱点・抵抗力」に
# 関係なく」とある（3・4 段階を計算しない）。v0.33 から (4) 自分の控えポケモン（タケシのディグダの「ミニじしん」。計算は (2) と同じ: プラスパワーは
# 変えない（p.257「(控えポケモンへのダメージは、そのまま)」）、ついているディフェンダーは変える（docs/defender-v0.2e.md の 13（自分のワザのダメージ）・16（ベンチ））。
# 説明は「弱点・抵抗力」に関係なく）
OPPONENT_ACTIVE = "opponent_active"  # (1) 相手の対戦ポケモンへのダメージ
SELF = "self"  # (3) このワザを使うポケモンへのダメージ（v0.2f）
OPPONENT_BENCH = "opponent_bench"  # (2) 相手の控えポケモンへのダメージ（v0.31）
SELF_BENCH = "self_bench"  # (4) 自分の控えポケモンへのダメージ（v0.33）
DAMAGE_TARGETS = (OPPONENT_ACTIVE, SELF, OPPONENT_BENCH, SELF_BENCH)
BENCH_TARGETS = (OPPONENT_BENCH, SELF_BENCH)  # v0.33: 控えポケモンへのダメージ（プラスパワーを変えない。``attack_damage_modifiers`` の ``bench``）


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
      （トラッシュ・サイド・交代）は、ワザの要素をすべて処理したあとで解決の基盤が行う（``resolution.flow._finish_attack``）
    - ``evaded``（v0.9）: 受けるポケモンの「とうめい」（``AttackImmunityOnHeads``）のコインが「おもて」で、このダメージを受け
      なかった（そのワザのダメージと効果を受けない。docs/transparency-v0.9.md の T5）。最終ダメージは計算したが、のせていない
      （``amount`` は None。量はログ ``attack_evaded`` に書く）。``prevented``（「ダメージを受けない」状態で要素が無効）とは別
    """

    target: str
    player: int
    pokemon_id: int
    prevented: bool
    amount: int | None
    knocked_out: bool
    evaded: bool = False

    @property
    def dealt(self) -> int:
        """与えたダメージ。最終ダメージ（``amount``）。防いだとき・「とうめい」で受けなかったとき・最終ダメージが 0 のときは 0
        （p.319「「0ダメージを受けた（与えた）」…のではなく、「ダメージを受けなかった（与えなかった）」ことになります」）。"""
        return 0 if self.amount is None else self.amount


def deal_attack_damage(
    state: GameState, use: AttackUse, target: str, base: int, *, log_extra: Mapping[str, Any] | None = None
) -> DamageResult:
    """ワザのダメージを 1 つ与える（v0.13 の約束の補助関数。v0.16b から、解決の基盤の ``kernel.deal_damage`` に委ねる入口）。

    受けるポケモンは ``target``（``OPPONENT_ACTIVE`` か ``SELF``。p.320 のダメージの (1)・(3)）、基本となるダメージは ``base``（p.321 の
    1 段階）。計算（p.321 の順番。弱点・抵抗力は、ワザを使うポケモンのタイプと受けるポケモンの弱点・抵抗力。プラスパワー・ディフェンダー）・
    「ダメージを受けない」状態（v0.4b。要素を無効にして ``damage_prevented``）・「とうめい」（v0.9）・ダメージを受けたときの効果（v0.10 の
    「はんげき」・v0.11 の「こんじょう」の写し・v0.12〜v0.13 の返す効果。与えるのは ``finish_damage_elements``）・ログ ``damage`` の形は、
    v0.13 の ``deal_attack_damage`` と同じ（解決の基盤の ``kernel.deal_damage``。v0.14〜v0.15 の比較で同じ結果・ログ・乱数）。結果は
    ``DamageResult``（v0.4d）。``use.runtime``（解決の基盤のワザの枠）がなければ ``RuntimeError``。``log_extra``（v0.12）はログ ``damage`` に
    加える項目。
    """
    return _runtime(use, "deal_attack_damage").deal_damage(state, target, base, log_extra)


def damage_opponent_active(state: GameState, use: AttackUse, base: int) -> DamageResult:
    """ワザで、相手の対戦ポケモンに、基本となるダメージ ``base`` から p.321 の順番で計算したダメージを与える（v0.4d から結果を返す）。"""
    return deal_attack_damage(state, use, OPPONENT_ACTIVE, base)


def preview_attack_damage(state: GameState, use: AttackUse, target: str, base: int) -> int | None:
    """``deal_attack_damage`` が計算する最終ダメージ（状態を変えない。ログも乱数もない）。受けるポケモンが「ダメージを受けない」
    状態なら None（要素が無効で計算しない）。ワザを使う前に、原典で決められない場合を確かめるため（v0.9。``AttackEffect.problem``）。
    変更効果は解決の基盤の ``kernel.deal_damage`` と同じ ``attack_damage_modifiers``（ワザ ``use.key`` を渡す。v0.27 の「つるぎのまい」の
    2 段階もここで数える）で集める。"""
    _, attacker = state.find_pokemon(use.pokemon_id)
    receiver = damage_receiver(state, use, target)
    if damage_prevention(state, receiver) is not None or attack_barrier(state, receiver) is not None:  # v0.31: 「バリアー」も要素を無効にする
        return None
    modifiers = attack_damage_modifiers(state, attacker, receiver, attack=use.key)
    # v0.48: 今有効な値の定義（``definition_views``）。色の読み方（VS1）で最終ダメージが変わるなら止める（``kernel.deal_damage`` と同じ判定）
    try:
        return same_for_type_readings(state, (attacker, receiver), lambda views: calculate_attack_damage(
            base, views[0], views[1], state.rules, modifiers).final)
    except TypeReadingsDiffer as differ:
        raise shift_duration_error(differ.pokemons[0], f"ワザ {use.key} のダメージの計算") from None


# ワザを受けるときに自動的にはたらく特殊能力（v0.9。ゴーストの「とうめい」）で、受けなかった要素の種類（ログ attack_evaded の
# element）。特殊状態の要素は conditions の名前（poison・sleep・paralysis・confusion）をそのまま使う
DAMAGE_ELEMENT = "damage"
FORCED_SWITCH_ELEMENT = "forced_switch"
# v0.31: 相手のポケモンについているエネルギーカードをトラッシュする効果（メラメラ・スーパーデストロイ）・ワザを使えなくする持続する効果
# （しっぽをふる）・ワザでエネルギーカードをつける効果（エナジーボム。CR-TRANSPARENCY-ENERGY-BOMB）
ENERGY_DISCARD_ELEMENT = "energy_discard"
ATTACK_LOCK_ELEMENT = "attack_lock"
ENERGY_ATTACH_ELEMENT = "energy_attach"
REDUCED_DAMAGE_ELEMENT = "reduced_damage"  # v0.34: 相手に与える「なきつく」（``ReducedDamageToSource``）
# v0.36: 相手に与える「すなかけ」・「えんまく」など（``AttackCoinCheck``）・「アイスバーン」・「わしづかみ」（``CannotRetreat``）と、ワザを使ったポケモン
# 自身を山札にもどす「くもがくれガス」（自分への効果）
ATTACK_CHECK_ELEMENT = "attack_check"
RETREAT_LOCK_ELEMENT = "retreat_lock"
RETURN_IN_PLAY_TO_DECK_ELEMENT = "return_in_play_to_deck"
# v0.41: ワザでダメージカウンターをとりのぞく効果（自分・自分の控え・相手のポケモン。GR-2000-P320-RECOVERY）と、ワザで相手の対戦ポケモンにダメージカウンターを
# のせる・取り替える効果（ダメージではない。GR-2000-P320-COUNTER-MOVE）
HEAL_ELEMENT = "heal"
COUNTERS_ELEMENT = "damage_counters"
# v0.42: ワザで自分の場のポケモンを進化させる効果（エリカのピッピの「つきのちから」）・自分の場のポケモンを手札にもどす効果（エリカのピクシーの「ようせいのきせき」）。
# どちらも自分への効果（自分のワザでも「とうめい」を評価する。v0.9 の T8・v0.17b）
EVOLVE_ELEMENT = "evolve"
RETURN_IN_PLAY_TO_HAND_ELEMENT = "return_in_play_to_hand"
# v0.45: 相手のポケモンについているエネルギーカードをはがす（ほかのポケモンにつけかえる）効果（わるいレアコイルの「じりょくせん」。トラッシュする ENERGY_DISCARD_ELEMENT
# とは行き先が違う）
ENERGY_MOVE_ELEMENT = "energy_move"
# v0.48: 相手の対戦ポケモンの弱点の色を変える効果（ポリゴンの「テクスチャー1」）・自分の抵抗力の色を変える効果（「テクスチャー2」。自分への効果）・自分の最大HPを決まった数に
# する効果（キョウのメタモンの「きょだいか」。自分への効果）
WEAKNESS_CHANGE_ELEMENT = "weakness_change"
RESISTANCE_CHANGE_ELEMENT = "resistance_change"
MAX_HP_ELEMENT = "max_hp"
# v0.50: 場のポケモンの進化カードをはがす効果（ミュウの「たいかビーム」。自分・相手のどちらのポケモンにも与える。相手のポケモンなら相手への効果）
DEVOLVE_ELEMENT = "devolve"
ATTACK_ELEMENTS = (DAMAGE_ELEMENT, FORCED_SWITCH_ELEMENT, POISON, SLEEP, PARALYSIS, CONFUSION, ENERGY_DISCARD_ELEMENT, ATTACK_LOCK_ELEMENT,
                   ENERGY_ATTACH_ELEMENT, REDUCED_DAMAGE_ELEMENT, ATTACK_CHECK_ELEMENT, RETREAT_LOCK_ELEMENT, RETURN_IN_PLAY_TO_DECK_ELEMENT,
                   HEAL_ELEMENT, COUNTERS_ELEMENT, EVOLVE_ELEMENT, RETURN_IN_PLAY_TO_HAND_ELEMENT, ENERGY_MOVE_ELEMENT, WEAKNESS_CHANGE_ELEMENT,
                   RESISTANCE_CHANGE_ELEMENT, MAX_HP_ELEMENT, DEVOLVE_ELEMENT)


def evasion_power(state: GameState, pokemon: PokemonInPlay) -> tuple[PowerKey, AttackImmunityOnHeads] | None:
    """場のポケモン ``pokemon`` の（いちばん上のカードの。p.310）特殊能力のうち、ワザを受けるときに自動的にはたらき
    （``AttackImmunityOnHeads``。ゴーストの「とうめい」）、今はたらいているもの（v0.9）。なければ None。

    はたらいていないのは、このカードがねむり・マヒ・こんらんのとき（T9〜T11。どくは関係しない。T12）と、かがくへんかガスに
    消されているとき（T14。v0.8 の ``continuous.suppressors_of`` をそのまま聞く。抑止の判定を複製しない）。場所（バトル場・
    ベンチ）は見ない（T7）。状態を変えず、乱数を使わない。
    """
    from .continuous import suppressors_of  # continuous.py は effects.py を読み込むので、使うときに読み込む

    for slot in powers_of(state, pokemon):  # v0.49: 今持つ特殊能力（「ばける」でのせたカードの特殊能力を含む）
        if isinstance(slot.effect, AttackImmunityOnHeads) and slot.effect.is_working(pokemon) and not suppressors_of(state, slot.power):
            return slot.key, slot.effect
    return None


def working_evasion_power(state: GameState, pokemon_id: int) -> PowerKey | None:
    """公開の問い合わせ（v0.9）: 場のポケモンの番号 ``pokemon_id`` のポケモンの、今はたらいている「とうめい」（ワザを受けるときに
    自動的にはたらく特殊能力。``evasion_power``）の ``PowerKey``。なければ None。場にいない番号は ``ValueError``（v0.8 の
    ``power_suppressors`` と同じ）。状態を変えず、乱数を使わない（コインを投げるのはワザを受けるとき。``attack_reaches``）。"""
    in_play = state.find_pokemon(pokemon_id)
    if in_play is None:
        raise ValueError(f"場のポケモンの番号 {pokemon_id!r} は場にいない")
    found = evasion_power(state, in_play[1])
    return None if found is None else found[0]


def attack_reaches(
    state: GameState, use: AttackUse, owner: int, pokemon: PokemonInPlay, element: str, *, amount: int | None = None
) -> bool:
    """ワザ ``use`` の要素 ``element`` のダメージや効果を、場のポケモン ``pokemon``（持ち主 ``owner``）が受けるか（v0.9。v0.13 の約束の
    補助関数。v0.16b から、解決の基盤の ``kernel.reaches`` に委ねる入口）。

    受けるポケモンに、はたらいている「とうめい」があれば、そのワザでまだ決めていなければゴースト側のプレイヤーがコインを 1 枚投げ
    （ログ ``evade_check``）、「おもて」ならそのワザのダメージと効果を受けない（要素ごとにログ ``attack_evaded``、False）。1 つのワザに
    つき 1 匹 1 回（T4）。はたらいていなければ、コインもログもなく True。効果の要素（ダメージ以外）は、まだ処理していない「ダメージを
    受けたとき」の効果があると ``RuntimeError``（``finish_damage_elements`` のあとに呼ぶ。p.89）。v0.13 と同じ結果・ログ・乱数。
    """
    return _runtime(use, "attack_reaches").reaches(state, owner, pokemon, element, amount)


def evaded_effect_coin_problem(state: GameState, use: AttackUse) -> UnsupportedError | None:
    """「相手にダメージ → ワザを使う側のコイン → 相手を特殊状態にする」ワザ（``PoisonOnHeads``・``ParalyzeOnHeads``・
    ``ConfuseOnHeads``）の、原典で決められない場合（v0.9。docs/transparency-v0.9.md の T19b）。

    相手の対戦ポケモンに、はたらいている「とうめい」があり、ダメージの要素の最終ダメージが 0 より大きい（受ける要素で「とうめい」の
    コインを投げる）と、「おもて」なら、そのあとのコインは「受けない」ポケモンへの効果だけを決める。p.321 は「効果を受けない」状態の
    ポケモンへの効果の要素を「無効」とだけ書き、その要素の中のコインを投げるかを書かない（v0.4b の ``UNRESOLVED_PREVENTED_COIN_DAMAGE``
    と同じ問い）。投げるかどうかで乱数の続きが変わるので、コインの結果で受け付けるかが変わらないように、ワザの宣言の前（こんらんの
    コインの前）に止める。最終ダメージが 0（抵抗力・ディフェンダー）なら、ダメージの要素ではコインを投げない（T21）ので、ワザの
    コインのあと、効果を受けるときに「とうめい」のコインを投げればよく、止めない。
    """
    target = state.players[1 - use.player].active
    if target is None or evasion_power(state, target) is None:
        return None
    _, attacker = state.find_pokemon(use.pokemon_id)
    attack = attack_of(state, use.key)  # v0.49: ワザを印刷したカード（use.key）
    final = preview_attack_damage(state, use, OPPONENT_ACTIVE, attack.damage)
    if final is None or final <= 0:
        return None
    return evaded_effect_coin_error(target.pokemon_id, final)


def effect_after_no_damage_error(attack: str, result: DamageResult, condition: str | None, *, what: str | None = None) -> UnsupportedError:
    """``UNRESOLVED_EFFECT_AFTER_NO_DAMAGE`` の理由（v0.17b。docs/rocket-snorlax-v0.17b.md の Z23）。説明が「ダメージを与えた後、…」の効果で、
    そのダメージの要素がダメージを与えなかった（``result``: 防いだ・「とうめい」で受けなかった・最終ダメージが 0）。v0.36: 特殊状態でない効果は
    ``what``（説明のその部分。キョウのドガースの「くもがくれガス」の「自分と、自分についているすべてのカードを山札にもどす」）で書く（同じ問い）。"""
    why = "「ダメージを受けない」状態で無効" if result.prevented else "「とうめい」で受けなかった" if result.evaded else "最終ダメージが 0"
    effect_text = what if what is not None else f"「{ {POISON: 'どく', SLEEP: 'ねむり', PARALYSIS: 'マヒ', CONFUSION: 'こんらん'}[condition]}」状態にする"
    return UnsupportedError(
        "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE",
        f"ワザ {attack} のダメージの要素が、ポケモン {result.pokemon_id} にダメージを与えなかった（{why}）。説明の「ダメージを与えた後、"
        f"…{effect_text}」が要素の順番か、ダメージを与えたことの条件かは『オフィシャルブック2000』（p.245・p.155・p.309・p.319〜p.321）"
        "から決められないので扱わない（p.321 はダメージ以外の効果の要素を有効とするが、p.155 の同じ文面の解説は「相手にダメージを与えたら」と書く）",
    )


def evaded_effect_coin_error(target_pid: int, final: int) -> UnsupportedError:
    """``UNRESOLVED_EVADED_EFFECT_COIN`` の理由（v0.15b で分けた。``final`` はダメージの要素の最終ダメージ）。"""
    return UnsupportedError(
        "UNRESOLVED_EVADED_EFFECT_COIN",
        f"相手の対戦ポケモン {target_pid} の「とうめい」がはたらいている。ダメージ（{final}）を受けるときのコインが「おもて」なら"
        "そのワザのダメージと効果を受けないが、そのあとの、効果を与えるかを決めるワザのコインを投げるかは『オフィシャルブック2000』"
        "（p.159・p.160・p.309・p.321）から決められないので扱わない（投げるかどうかで乱数の続きが変わる）",
    )


def _require_not_evaded(use: AttackUse, pokemon: PokemonInPlay) -> None:
    """ワザのコインの前の確認: このワザで、受けないと決まったポケモンへの効果を決めるコインは ``evaded_effect_coin_problem`` が
    ワザの前に止めているので、ここに来たらエンジンの不具合（確かめていない処理を黙って行わない）。v0.16b から、受けるかの記録は解決の
    基盤のワザの枠が持つ（``AttackUse.reception``）。"""
    if use.reception.get(pokemon.pokemon_id) is False:
        raise RuntimeError(
            f"ワザ {use.key} で「とうめい」により受けないと決まったポケモン {pokemon.pokemon_id} への効果を決めるコイン（problem で止めるはず。エンジンの不具合）"
        )


# ---------------------------------------------------------------- ダメージを受けたときに自動的にはたらく特殊能力（v0.10）

# 「はんげき」を与えなかった理由（ログ counterattack_skipped の reason）
COUNTERATTACK_TARGET_KNOCKED_OUT = "knocked_out"  # ダメージを与えたポケモンが、そのワザの自分へのダメージですでに HP 以上（対象がいない）



def counterattack_power(state: GameState, pokemon: PokemonInPlay) -> tuple[PowerKey, CounterattackDamage] | None:
    """場のポケモン ``pokemon`` の（いちばん上のカードの。p.310）特殊能力のうち、ダメージを受けたときに自動的にはたらき
    （``CounterattackDamage``。カイリキーの「はんげき」）、今はたらいているもの（v0.10）。なければ None。

    はたらいていないのは、このカードがねむり・マヒ・こんらんのとき（C19〜C21。どくは関係しない。C22）と、かがくへんかガスに
    消されているとき（C24。v0.8 の ``continuous.suppressors_of`` をそのまま聞く。抑止の判定を複製しない）。場所（バトル場・
    ベンチ）は見ない（C9）。v0.9 の ``evasion_power``（「とうめい」）とは別の型で探す（はたらく時点も効果も違う）。状態を変えず、
    乱数を使わない。
    """
    from .continuous import suppressors_of  # continuous.py は effects.py を読み込むので、使うときに読み込む

    for slot in powers_of(state, pokemon):  # v0.49: 今持つ特殊能力
        if isinstance(slot.effect, CounterattackDamage) and slot.effect.is_working(pokemon) and not suppressors_of(state, slot.power):
            return slot.key, slot.effect
    return None


def working_counterattack_power(state: GameState, pokemon_id: int) -> PowerKey | None:
    """公開の問い合わせ（v0.10）: 場のポケモンの番号 ``pokemon_id`` のポケモンの、今はたらいている「はんげき」（ダメージを受けた
    ときに自動的にはたらく特殊能力。``counterattack_power``）の ``PowerKey``。なければ None。場にいない番号は ``ValueError``
    （v0.9 の ``working_evasion_power`` と同じ）。状態を変えず、乱数を使わない。"""
    in_play = state.find_pokemon(pokemon_id)
    if in_play is None:
        raise ValueError(f"場のポケモンの番号 {pokemon_id!r} は場にいない")
    found = counterattack_power(state, in_play[1])
    return None if found is None else found[0]



def finish_damage_elements(state: GameState, use: AttackUse) -> None:
    """ワザのダメージの処理がすべて終わったところ（ダメージ以外の効果の前。p.89 の解説）で、そのワザのダメージではたらいた「ダメージを
    受けたとき」の効果（v0.10 の「はんげき」・v0.12 の「ほのおのかべ」・v0.13 の「こうらがえし」）を処理する（v0.13 の約束の補助関数。
    v0.16b から、解決の基盤の「ダメージの要素のあと」の窓 ``kernel.fire_pending`` に委ねる入口）。処理するものがなければ何もしない
    （2 回呼んでも二重に与えない）。2 つ以上なら順番が原典で決まらない（C34・C35。今の対応カードでは起こらない）ので、エンジンの不具合
    として止める。解決の基盤は、ワザの実装（``resolve``・``resume``）のあとにも、この窓を開く。
    """
    _runtime(use, "finish_damage_elements").finish_damage_elements(state)



def counterattack_double_knockout_problem(state: GameState, use: AttackUse, effect: AttackEffect) -> UnsupportedError | None:
    """ワザ ``use``（実装 ``effect``）で、原典で決められない場合になりうるなら、その理由（v0.10。docs/counterattack-v0.10.md の C18）。

    相手の対戦ポケモンに、はたらいている「はんげき」があり、このワザのダメージでそのポケモンがきぜつし、かつ「はんげき」のダメージで
    ワザを使ったポケモンがきぜつする（「はんげき」がなければきぜつしない）と、2 匹のきぜつが「同時に「きぜつ」した」こと（p.324
    「1つのワザや特殊能力などによって引き起こされることがらによって複数のポケモンが「きぜつ」した場合」）になるかが決められない
    （1 匹はワザ、もう 1 匹は特殊能力のダメージできぜつする）。同時かどうかで、サイドを取る・バトル場に出す決定の順番と、勝ち負け
    （両方が最後のサイドを取る・出せるポケモンがいない場合。p.311・p.323・p.325）が変わるので、推測で決めない。

    エンジンがワザの宣言の前（こんらんのコインの前）に聞く。ワザのダメージの候補（``AttackEffect.damage_profile``。コインのどの結果も）
    のどれかで、相手の対戦ポケモンがきぜつし、自分へのダメージの候補のどれかで、ワザを使ったポケモンが自分へのダメージではきぜつせず
    「はんげき」できぜつするなら止める（コインの結果で受け付けるかが変わらない。``preview_attack_damage`` で計算し、状態を変えない）。
    ワザを使ったポケモンが自分へのダメージですでにきぜつするなら、「はんげき」は与えない（C15）ので、2 匹のきぜつは 1 つのワザに
    よる同時のきぜつ（p.324。CONFIRMED）で、止めない。
    """
    defender = state.players[1 - use.player].active
    if defender is None:
        return None
    found = counterattack_power(state, defender)
    if found is None:
        return None
    power_key, power_effect = found
    _, attacker = state.find_pokemon(use.pokemon_id)
    profile = effect.damage_profile(state, use)
    defender_hp = max_hp(state, defender)  # v0.48: 今有効な最大HP
    attacker_hp = max_hp(state, attacker)

    def defender_knocked_out(base: int | None) -> bool:
        final = None if base is None else preview_attack_damage(state, use, OPPONENT_ACTIVE, base)
        return final is not None and final > 0 and defender.damage + final >= defender_hp

    def only_counterattack_knocks_out_attacker(base: int) -> bool:
        own = 0 if base <= 0 else (preview_attack_damage(state, use, SELF, base) or 0)
        return attacker.damage + own < attacker_hp <= attacker.damage + own + power_effect.amount

    # v0.11: 同じコインの結果でいっしょに起こりうる組（DamageProfile.pairs）で確かめる。v0.10 のワザはどれもすべての組が起こりうる
    # （pairs は opponent と self_damage のすべての組）ので、「相手がきぜつする候補があり、かつワザを使ったポケモンが「はんげき」だけで
    # きぜつする候補がある」という v0.10 の判定と同じ答えになる
    if not any(defender_knocked_out(opponent) and only_counterattack_knocks_out_attacker(own) for opponent, own in profile.pairs()):
        return None
    return counterattack_double_knockout_error(defender.pokemon_id, power_effect.amount, attacker.pokemon_id,
                                               *power_name_and_page(state, power_key))


def power_name_and_page(state: GameState, key: PowerKey) -> tuple[str, str]:
    """特殊能力 ``key`` の名前と、実装がしたがう最新の説明のページ（登録の出典 ``P43 p.○○`` の ``p.○○``）。理由の文に書く（v0.17b）。"""
    entry = state.effects.power_entry(key.card_id, key.power_index)
    source = entry.source
    return entry.name_ja, source.split(" ", 1)[1] if source.startswith("P43 ") else source


def counterattack_double_knockout_error(defender_pid: int, amount: int, attacker_pid: int, power_name: str = "はんげき",
                                        page: str = "p.192") -> UnsupportedError:
    """``UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT`` の理由（v0.15b で分けた。``amount`` は特殊能力のダメージ）。v0.17b から、ダメージを与えた
    特殊能力の名前と最新の説明のページを書く（既定ははんげき（p.192）で、v0.16 までと同じ文。R団のカビゴンの［わるいねぞう］は p.245。C18 と同じ
    問いで、新しいコードにしない。docs/rocket-snorlax-v0.17b.md の Z13）。"""
    return UnsupportedError(
        "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT",
        f"このワザのダメージで相手の対戦ポケモン {defender_pid} がきぜつしうるうえ、その「{power_name}」の {amount} ダメージで"
        f"ワザを使ったポケモン {attacker_pid} がきぜつしうる。ワザによるきぜつと特殊能力によるきぜつが「同時に「きぜつ」した」"
        f"ことになるか（p.324）が『オフィシャルブック2000』（p.89・{page}・p.311・p.323〜p.325）から決められないので扱わない"
        "（サイド・バトル場に出す順番と勝ち負けが変わる）",
    )


# ---------------------------------------------------------------- 相手の番ではたらくワザの効果（v0.12。「ほのおのかべ」）

# 「ほのおのかべ」のダメージを与えなかった理由（ログ retaliation_skipped の reason）。「はんげき」（C15）と同じ
RETALIATION_TARGET_KNOCKED_OUT = COUNTERATTACK_TARGET_KNOCKED_OUT
# v0.45: コインの条件のある返す効果（「クロスカウンター」）で、はたらくときのコインが「うら」（与えない。ログ ``retaliation_skipped`` の理由）
RETALIATION_COIN_TAILS = "coin_tails"



def retaliation_use(state: GameState, player: int, holder: PokemonInPlay, effect: Retaliation) -> AttackUse:
    """「ほのおのかべ」「こうらがえし」のダメージを計算するための ``AttackUse``（v0.12）: ワザを使ったのは効果を持つポケモン（``holder``。
    持ち主 ``player``）、ワザは効果を与えたワザ（``Retaliation.attack_index``）。そのダメージは効果を持つポケモンのワザによるダメージ
    （p.321「8」・p.89・p.82）なので、発生源（弱点・抵抗力・プラスパワー）はこのポケモン、受けるのは相手の対戦ポケモン。v0.16b から、
    宣言の前の確認（``retaliation_double_knockout_problem``。``preview_attack_damage``）だけが使う（返すダメージを与えるのは解決の基盤の
    ``kernel.attack_damage_to_damage_source``）。"""
    key = AttackKey(effect_attack_card(state, effect), effect.attack_index)  # v0.49: 効果を与えたワザを印刷したカード（``attack_card``）
    return AttackUse(player, holder.pokemon_id, key)



def retaliation_double_knockout_problem(state: GameState, use: AttackUse, effect: AttackEffect) -> UnsupportedError | None:
    """ワザ ``use``（実装 ``effect``）で、原典で決められない場合になりうるなら、その理由（v0.12。docs/rocket-moltres-v0.12.md の W24）。

    相手の対戦ポケモン（R団のファイヤー）に今の番にはたらく「ほのおのかべ」があり、このワザのダメージ（と、「ほのおのかべ」のダメージで
    はたらくワザを使ったポケモンの「はんげき」）で R団のファイヤーがきぜつし、かつ「ほのおのかべ」のダメージでワザを使ったポケモンが
    きぜつする（同じワザの自分へのダメージではきぜつしない）と、2 匹のきぜつが「同時に「きぜつ」した」こと（p.324「1つのワザや特殊能力
    などによって引き起こされることがら」）になるかが決められない（1 匹はこのワザ、もう 1 匹は前の番の R団のファイヤーのワザの効果の
    ダメージできぜつする。v0.10 の C18 と同じ問い）。同時かどうかで、サイドを取る・バトル場に出す決定の順番と、勝ち負け（p.311・p.323・
    p.325）が変わるので、推測で決めない。

    エンジンがワザの宣言の前（こんらんのコインの前）に聞く。ワザのダメージの候補（``AttackEffect.damage_profile`` の
    ``DamageProfile.pairs``。同じコインの結果でいっしょに起こりうる組）のどれかでそうなりうるなら止める（コインの結果で受け付けるかが
    変わらない）。「ほのおのかべ」のダメージは ``preview_attack_damage``（``retaliation_use``）で計算し、「とうめい」のコインは「受ける」
    ほうを仮定する（受けない結果もありうるが、受ける結果がありうるので止める）。ワザを使ったポケモンが自分へのダメージですでにきぜつ
    するなら、「ほのおのかべ」は与えない（W23・v0.10 の C15）ので、2 匹のきぜつは 1 つのワザによる同時のきぜつ（p.324）で、止めない。
    「こんじょう」（v0.11）で解決したことにはしない（v0.11 の G39 と同じ）。

    v0.13: わるいカメールの「こうらがえし」（受けたダメージと同じダメージを返す）でも同じ問いになる（docs/shell-attack-v0.13.md の S37。
    わるいカメールがこのワザのダメージできぜつし、ワザを使ったポケモンが返すダメージできぜつする）ので、同じコードで止める（新しい未解決の
    裁定にしない）。返すダメージは、ダメージの組ごとに、わるいカメールが受ける最終ダメージを基本となるダメージにして計算する
    （``Retaliation.base_damage``）。
    """
    holder = state.players[1 - use.player].active
    if holder is None:
        return None
    found = retaliation(state, holder)
    if found is None:
        return None
    _, attacker = state.find_pokemon(use.pokemon_id)
    fire_use = retaliation_use(state, 1 - use.player, holder, found)
    counter = counterattack_power(state, attacker)  # 返すダメージで、ワザを使ったポケモンの「はんげき」がはたらく
    counter_amount = 0 if counter is None else counter[1].amount
    holder_hp = max_hp(state, holder)  # v0.48: 今有効な最大HP
    attacker_hp = max_hp(state, attacker)
    for opponent, own in effect.damage_profile(state, use).pairs():
        final = None if opponent is None else preview_attack_damage(state, use, OPPONENT_ACTIVE, opponent)
        if final is None or final <= 0:
            continue  # 効果を持つポケモンがこのワザのダメージを受けない。効果ははたらかない（W13・S15・S16）
        # 返すダメージ（v0.13: 「こうらがえし」は受けたダメージ final を基本となるダメージにする。S9・S10。「ほのおのかべ」は 10）。
        # 発生源は効果を持つポケモン、受けるのはワザを使ったポケモン（弱点・抵抗力・ディフェンダーを計算する。S21〜S23）
        retaliation_final = preview_attack_damage(state, fire_use, OPPONENT_ACTIVE, found.base_damage(final))
        if retaliation_final is None or retaliation_final <= 0:
            continue  # ワザを使ったポケモンが返すダメージを受けない（抵抗力・ディフェンダーで 0）
        own_final = 0 if own <= 0 else (preview_attack_damage(state, use, SELF, own) or 0)
        attacker_damage = attacker.damage + own_final
        if attacker_damage >= attacker_hp:
            continue  # 自分へのダメージですでにきぜつする。返すダメージは与えない（W23）
        if attacker_damage + retaliation_final < attacker_hp:
            continue  # ワザを使ったポケモンは返すダメージではきぜつしない
        if holder.damage + final + counter_amount >= holder_hp:
            # v0.45: コインの条件のある効果（「クロスカウンター」）は「おもて」の場合を数える（「おもて」がありうるので止める。「とうめい」と同じ）
            return retaliation_double_knockout_error(holder.pokemon_id, found, retaliation_final, attacker.pokemon_id, state)
    return None


def retaliation_double_knockout_error(holder_pid: int, effect: Retaliation, retaliation_final: int, attacker_pid: int,
                                     state: GameState | None = None) -> UnsupportedError:
    """``UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`` の理由（v0.15b で分けた。``retaliation_final`` は返すダメージの最終ダメージ。v0.45: ``state`` は効果の名前を
    カードのデータから求めるため。``_retaliation_name``）。"""
    return UnsupportedError(
        "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT",
        f"このワザのダメージで相手の対戦ポケモン {holder_pid} がきぜつしうるうえ、その「{effect.kind}」（{_retaliation_name(effect, state)}）の"
        f" {retaliation_final} ダメージでワザを使ったポケモン {attacker_pid} がきぜつしうる。このワザによるきぜつと、前の番のワザの"
        "効果のダメージによるきぜつが「同時に「きぜつ」した」ことになるか（p.324）が『オフィシャルブック2000』（p.82・p.89・p.311・"
        "p.321・p.323〜p.325）から決められないので扱わない（サイド・バトル場に出す順番と勝ち負けが変わる）",
    )


def _retaliation_name(effect: Retaliation, state: GameState | None = None) -> str:
    """理由の文に書く効果の名前（v0.13）。v0.45: 倍数・コインの条件のある効果（「クロスカウンター」）は、効果を与えたワザの名前（``state`` のカードのデータ。
    v0.44 までの効果の文は変えない）。"""
    if effect.scaled and state is not None:
        return attack_of(state, AttackKey(effect_attack_card(state, effect), effect.attack_index)).name_ja  # v0.49: 効果を与えたワザを印刷したカード
    return "ほのおのかべ" if effect.basis == RETALIATION_FIXED else "こうらがえし"


def ko_prevention_power(state: GameState, pokemon: PokemonInPlay) -> tuple[PowerKey, PreventKnockOutOnHeads] | None:
    """場のポケモン ``pokemon`` の（いちばん上のカードの。p.310）特殊能力のうち、相手のワザによるダメージできぜつするときに使える
    もの（``PreventKnockOutOnHeads``。サカキのカイリキーの「こんじょう」。v0.11）。特殊状態・かがくへんかガスは見ない（持っているか
    だけ）。なければ None。状態を変えず、乱数を使わない。"""
    for slot in powers_of(state, pokemon):  # v0.49: 今持つ特殊能力
        if isinstance(slot.effect, PreventKnockOutOnHeads):
            return slot.key, slot.effect
    return None


def ko_prevention_suppressors(state: GameState, pokemon: PokemonInPlay, key: PowerKey) -> tuple[int, ...]:
    """「こんじょう」（``key``）を消している、はたらいている「かがくへんかガス」のポケモンの番号（v0.8 の ``continuous.suppressors_of``
    をそのまま聞く。抑止の判定を複製しない。G31）。"""
    from .continuous import suppressors_of  # continuous.py は effects.py を読み込むので、使うときに読み込む

    return suppressors_of(state, state.definitions[key.card_id].powers[key.power_index])  # v0.49: 特殊能力を印刷したカード（key）の定義


def available_ko_prevention_power(state: GameState, pokemon_id: int) -> PowerKey | None:
    """公開の問い合わせ（v0.11）: 場のポケモンの番号 ``pokemon_id`` のポケモンが、今の状態で相手のワザによるダメージを受けてきぜつする
    なら使える「こんじょう」（``PreventKnockOutOnHeads``）の ``PowerKey``。持っていない・今ねむり・マヒ・こんらん（G25〜G27）・
    かがくへんかガスに消されている（G31）なら None。場にいない番号は ``ValueError``（v0.10 の ``working_counterattack_power`` と同じ）。
    状態を変えず、乱数を使わない（使うかを決めるのは持ち主。決定 ``KO_PREVENTION``）。"""
    in_play = state.find_pokemon(pokemon_id)
    if in_play is None:
        raise ValueError(f"場のポケモンの番号 {pokemon_id!r} は場にいない")
    pokemon = in_play[1]
    found = ko_prevention_power(state, pokemon)
    if found is None or not found[1].is_able(pokemon) or ko_prevention_suppressors(state, pokemon, found[0]):
        return None
    return found[0]


def ko_prevention_attack_effect_problem(state: GameState, use: AttackUse, effect: AttackEffect) -> UnsupportedError | None:
    """ワザ ``use``（実装 ``effect``）で、原典で決められない場合になりうるなら、その理由（v0.11。docs/guts-v0.11.md の G30・G37）。

    相手の対戦ポケモンが「こんじょう」（相手のワザによるダメージで「きぜつ」するとき、使える。コインが「おもて」なら「きぜつ」せず、
    残り HP が 10）を使える状態で、このワザのダメージで HP 以上になり、そのあと同じワザで相手の対戦ポケモンに効果（特殊状態・入れ替え。
    ``AttackEffect.opponent_effect_elements``）を与える場合:

    - ワザのダメージで HP 以上になった相手の対戦ポケモンには、あとの効果を与えない（v0.4d。p.89「そのダメージできぜつしなければ」・
      p.309「処理の対象がなくなってしまっている場合、その内容は無視して」・p.213。SUPPORTED）。
    - 「こんじょう」は、ワザの要素をすべて処理したあとのきぜつの判定で使う（p.309「ワザを使っている最中に、…特殊能力の使用を宣言しては
      いけません」・p.324。G2・G32。SUPPORTED）。
    - 「おもて」で「きぜつ」しなかったポケモンに、そのワザのあとの効果（マヒなど）を与えるか（与えないまま残るのか、使う時点がダメージの
      直後で効果を受けるのか）は、p.193 の最新の説明・解説、p.309・p.311・p.320〜p.324 のどれにも書かれていない。

    どちらで処理するかで、特殊状態・入れ替え・決定・乱数の続きが変わるので推測で決めない。エンジンがワザの宣言の前（こんらんのコインの
    前）に聞く。ワザのダメージの候補（``AttackEffect.damage_profile``。コインのどの結果も）のどれかで相手の対戦ポケモンが HP 以上に
    なるなら止める（コインの結果で受け付けるかが変わらない。``preview_attack_damage`` で計算し、状態を変えない）。相手の対戦ポケモンが
    今「こんじょう」を使えない（持っていない・ねむり・マヒ・こんらん・かがくへんかガス）なら止めない（そのときは v0.4d どおりきぜつ
    して効果は与えない）。ダメージを与えるワザでダメージより前に相手の特殊状態を変える要素は、今の対応カードにない（あれば、ここで
    ダメージを受けるときの特殊状態を求め直す必要がある）。
    """
    if not effect.opponent_effect_elements:
        return None
    defender = state.players[1 - use.player].active
    if defender is None or available_ko_prevention_power(state, defender.pokemon_id) is None:
        return None
    hp = max_hp(state, defender)  # v0.48: 今有効な最大HP
    finals = [preview_attack_damage(state, use, OPPONENT_ACTIVE, base) for base in effect.damage_profile(state, use).opponent]
    if not any(final is not None and final > 0 and defender.damage + final >= hp for final in finals):
        return None
    return ko_prevention_attack_effect_error(defender.pokemon_id, effect.opponent_effect_elements)


def ko_prevention_attack_effect_error(defender_pid: int, elements: tuple[str, ...]) -> UnsupportedError:
    """``UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT`` の理由（v0.15b で分けた。``elements`` は相手の対戦ポケモンに与える効果の要素の種類）。"""
    return UnsupportedError(
        "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT",
        f"このワザのダメージで、「こんじょう」を使える相手の対戦ポケモン {defender_pid} が HP 以上のダメージを受けうるうえ、そのあと"
        f"同じワザで相手の対戦ポケモンに効果（{'・'.join(elements)}）を与える。「こんじょう」で「きぜつ」しなかった"
        "ポケモンが、そのワザの効果を受けるかは『オフィシャルブック2000』（p.89・p.193・p.309・p.311・p.320〜p.324）から決められないので"
        "扱わない（特殊状態・入れ替え・乱数の続きが変わる）",
    )


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

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        # 「おもて」なら自分へのダメージはない（0）、「うら」なら self_damage（v0.10）
        return DamageProfile(opponent=super().damage_profile(state, use).opponent, self_damage=(0, self.self_damage))


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
    opponent_effect_elements = (POISON,)  # v0.11: 相手の対戦ポケモンに与える効果の要素（ko_prevention_attack_effect_problem）

    def problem(self, state: GameState, use: AttackUse) -> UnsupportedError | None:
        """v0.9: 相手の対戦ポケモンの「とうめい」で、ダメージの要素で受けないと決まりうるなら、そのあとのコインを投げるかが原典で
        決められない（``evaded_effect_coin_problem``。docs/transparency-v0.9.md の T19b）。"""
        return evaded_effect_coin_problem(state, use)

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier is not None:
            problems.append(f"ダメージの目安に「{attack.damage_modifier}」があるワザを、目安の数字ぶんのダメージのワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、どく状態にするワザとして登録している")
        return problems


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
    opponent_effect_elements = (POISON,)  # v0.11: 相手の対戦ポケモンに与える効果の要素（ko_prevention_attack_effect_problem）

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier is not None:
            problems.append(f"ダメージの目安に「{attack.damage_modifier}」があるワザを、目安の数字ぶんのダメージのワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、どく状態にするワザとして登録している")
        return problems


@dataclass(frozen=True)
class SleepOpponent(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。そのあと、コインを投げずに相手の対戦ポケモンをねむり状態にする
    （v0.9。化石の秘密のゴーストの「あくむ」。p.160 の最新の説明「相手を「ねむり」状態にする。」・解説「ダメージは10と少なめですが、
    必ず相手をねむり状態にすることができます」。docs/haunter-line-v0.9.md）。

    - ダメージの目安に「×」「+」「−」がないので、説明の最初の「相手の対戦ポケモンに 10 ダメージ。」が省略されている（p.320）。
      ダメージの処理をしてから、ねむり状態にする（p.309 の手順 6）。``PoisonOpponent``（どく）と同じ形で、特殊状態だけが違う。
    - コインを投げない（説明にコインがない）。ダメージのないねむりのワザ（``PutToSleep``。キノコのほうし）とは別の実装。
    - ねむり状態にするのは「効果」。最終ダメージが 0 でも、「ダメージを受けない」状態でも、ねむり状態にする（p.321）。相手の
      対戦ポケモンが、このワザのダメージできぜつしたら、処理の対象がいないので、ねむり状態にしない（p.309・p.323）。
    - 相手の対戦ポケモンの「とうめい」（v0.9）: ダメージを受けるときに投げたコインの結果を、ねむりにも使う（T4）。最終ダメージが 0
      なら、ねむりを受けるときにコインを投げる。
    """

    implementation_id = "sleep_opponent"
    opponent_effect_elements = (SLEEP,)  # v0.11: 相手の対戦ポケモンに与える効果の要素（ko_prevention_attack_effect_problem）

    def check(self, attack: Attack) -> list[str]:
        return _check_damage_then_effect(attack, "ねむり状態にする")


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
      そのため、この確認のための ``problem`` は持たない（こんらんの「おもて」のあとでこの確認が働くこともない）。
      docs/effect-preflight-v0.3d.md・tests/test_effect_preflight_v0_3d.py。v0.9 の ``problem`` は「とうめい」の確認（T19b）だけ。
    - ねむり状態の相手なら、ねむりは消えてマヒ状態になる。どく状態はそのまま（p.322。``conditions.paralyze``）。
    """

    implementation_id = "paralyze_on_heads"
    opponent_effect_elements = (PARALYSIS,)  # v0.11: 相手の対戦ポケモンに与える効果の要素（ko_prevention_attack_effect_problem）

    def problem(self, state: GameState, use: AttackUse) -> UnsupportedError | None:
        """v0.9: 相手の対戦ポケモンの「とうめい」で、ダメージの要素で受けないと決まりうるなら、そのあとのコインを投げるかが原典で
        決められない（``evaded_effect_coin_problem``。docs/transparency-v0.9.md の T19b）。"""
        return evaded_effect_coin_problem(state, use)

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier is not None:
            problems.append(f"ダメージの目安に「{attack.damage_modifier}」があるワザを、目安の数字ぶんのダメージのワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、マヒ状態にするワザとして登録している")
        return problems


@dataclass(frozen=True)
class CoinBonusDamageAndParalyze(AttackEffect):
    """コインを 1 枚投げ、「おもて」なら、ダメージの目安の数字に ``bonus`` を加えたダメージを相手の対戦ポケモンに与えて、相手の対戦
    ポケモンをマヒ状態にする。「うら」なら目安の数字ぶんのダメージだけ（v0.8。ロケット団のベトベターの「ねばりつく」。p.45 の最新の説明
    「コインを投げて「おもて」なら、20ダメージを追加して、相手を「マヒ」状態にする。」、ダメージの目安「10+」。docs/grimer-line-v0.8.md）。

    - ダメージの目安に「×」がないので、説明の最初の「相手（太字）に10ダメージ。」が省略されている。「+」は、説明にしたがって書かれた
      数字よりダメージが大きくなることがある印（p.320）。「おもて」の 20 の追加は、説明にしたがって計算する基本となるダメージ
      （p.321 の 1 段階）。弱点・抵抗力・プラスパワー・ディフェンダーはそのあと（v0.6 のハイドロポンプと同じ）。
    - ダメージの量がコインで決まるので、コインはダメージの計算の前に投げる（「おもて」なら 30、「うら」なら 10）。
    - マヒ状態にするのは「効果」で、ダメージではない。最終ダメージが 0 でも、相手が「ダメージを受けない」状態（v0.4b。ダメージの
      要素は無効、「ダメージ以外の効果は受ける」）でも、「おもて」ならマヒ状態にする。このワザのコインはマヒにするかも決めるので、
      「ダメージを受けない」相手にもコインを投げる（``CoinFlipDamage`` の ``UNRESOLVED_PREVENTED_COIN_DAMAGE`` は、コインがダメージの
      量だけを決めるワザの問題で、このワザには当てはまらない）。
    - 相手の対戦ポケモンが、このワザのダメージできぜつしたら、処理の対象がいないのでマヒ状態にしない（p.309・p.323。
      ``ParalyzeOnHeads`` と同じ。コインは投げたあと）。
    - マヒの再付与で回復する番が原典で決められない場合（``conditions.paralysis_problem``）は、受け付けるかがコインの結果で変わら
      ないように、コインの前に確かめる。相手の対戦ポケモンだけをマヒにするワザでは、不変条件を満たすどの状態でも起こらない
      （v0.3d の証明。``ParalyzeOnHeads``）。
    """

    bonus: int
    implementation_id = "coin_bonus_damage_and_paralyze"
    opponent_effect_elements = (PARALYSIS,)  # v0.11: 相手の対戦ポケモンに与える効果の要素（ko_prevention_attack_effect_problem）

    def __post_init__(self) -> None:
        if type(self.bonus) is not int or self.bonus <= 0 or self.bonus % 10:
            raise ValueError(f"「おもて」のときに追加するダメージは 10 の倍数の正の数（{self.bonus!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier != "+":
            problems.append("ダメージの目安に「+」のないワザを、コインでダメージを追加するワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、コインでダメージを追加してマヒ状態にするワザとして登録している")
        return problems

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        # 「うら」なら目安の数字、「おもて」なら bonus を加えた数（v0.10）
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = attack_of(state, use.key)  # v0.49: ワザを印刷したカード（use.key）
        return DamageProfile(opponent=(attack.damage, attack.damage + self.bonus))


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
    opponent_effect_elements = (SLEEP,)  # v0.11: 相手の対戦ポケモンに与える効果の要素（ko_prevention_attack_effect_problem）

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage is not None or attack.damage_display is not None or attack.damage_modifier is not None:
            problems.append("ダメージの目安のあるワザを、ダメージを与えずにねむり状態にするワザとして登録している")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、ねむり状態にするワザとして登録している")
        return problems


@dataclass(frozen=True)
class PoisonWithoutDamage(AttackEffect):
    """ダメージを与えず、コインを投げずに相手の対戦ポケモンをどく状態にする（v0.8。ロケット団のベトベターの「どくガス」。p.45 の
    最新の説明「相手を「どく」状態にする。」・解説「「どくガス」は、コイントスなしで相手の対戦ポケモンを必ずどく状態にします。」。
    docs/grimer-line-v0.8.md）。

    - ダメージの目安の数字がないワザ（データの ``damage`` が None）だけを登録できる（``PutToSleep`` と同じ）。ダメージの要素がない
      ので、ダメージの計算（p.321）をせず、``damage`` のログもない。ダメージの目安のあるワザの ``PoisonOpponent``（v0.5。フシギソウの
      「どくのこな」）とは別の実装。
    - コインは投げない（説明にない）ので、乱数を使わない。
    - もうどく状態のポケモンなら、二重のどく状態にはならない（p.322。``conditions.poison`` がログに ``already``）。
    """

    implementation_id = "poison_without_damage"
    opponent_effect_elements = (POISON,)  # v0.11: 相手の対戦ポケモンに与える効果の要素（ko_prevention_attack_effect_problem）

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage is not None or attack.damage_display is not None or attack.damage_modifier is not None:
            problems.append("ダメージの目安のあるワザを、ダメージを与えずにどく状態にするワザとして登録している")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、どく状態にするワザとして登録している")
        return problems


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
    opponent_effect_elements = (CONFUSION,)  # v0.11: 相手の対戦ポケモンに与える効果の要素（ko_prevention_attack_effect_problem）

    def problem(self, state: GameState, use: AttackUse) -> UnsupportedError | None:
        """v0.9: 相手の対戦ポケモンの「とうめい」で、ダメージの要素で受けないと決まりうるなら、そのあとのコインを投げるかが原典で
        決められない（``evaded_effect_coin_problem``。docs/transparency-v0.9.md の T19b）。"""
        return evaded_effect_coin_problem(state, use)

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier is not None:
            problems.append(f"ダメージの目安に「{attack.damage_modifier}」があるワザを、目安の数字ぶんのダメージのワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、こんらん状態にするワザとして登録している")
        return problems


@dataclass(frozen=True)
class ConfuseOnHeadsWithoutDamage(AttackEffect):
    """ダメージを与えず、コインを 1 枚投げて「おもて」なら相手の対戦ポケモンをこんらん状態にする（v0.17a。サカキのニャースの「ねこノミ」。
    p.229 の最新の説明「コインを投げて「おもて」なら、相手を「こんらん」状態にする。」。docs/card-implementation-v0.17a.md）。

    - ダメージの目安の数字がないワザ（データの ``damage`` が None）だけを登録できる（``PutToSleep``・``PoisonWithoutDamage`` と同じ）。
      ダメージの要素がないので、ダメージの計算（p.321）をせず、``damage`` のログもない。ダメージの目安のあるワザの ``ConfuseOnHeads``
      （v0.3c。ロコンの「あやしいひかり」）とは別の実装。
    - 解決の基盤の要素の並びは、既存の要素だけ（``programs.Status(CONFUSION, local_coin=HEADS)``。v0.3c からの ``ConfuseOnHeads`` の
      こんらんの要素と同じ）。コイン → 「おもて」なら、効果を与える直前に「とうめい」の評価（T19・T22）→ こんらん。ダメージの要素がない
      ので、「とうめい」で受けないと決まったあとのコイン（T19b）は起こらない。
    - もうこんらん状態なら二重にならない。ねむり・マヒ状態なら、それが消えてこんらん状態になる。どく状態はそのまま（p.322。
      ``conditions.confuse``）。
    - v0.13 の約束（``resolve``・``resume``）は持たない。宣言の前の確認は解決の基盤の先読み（``derived``）だけで、v0.13 の止める関数の型
      （``v013_checks.VERIFIED``）には入れていない（ワザの実装を加えても自動では加えない。v0.16c）。
    """

    implementation_id = "confuse_on_heads_without_damage"
    opponent_effect_elements = (CONFUSION,)  # v0.11: 相手の対戦ポケモンに与える効果の要素（ko_prevention_attack_effect_problem）

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage is not None or attack.damage_display is not None or attack.damage_modifier is not None:
            problems.append("ダメージの目安のあるワザを、ダメージを与えずにこんらん状態にするワザとして登録している")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、こんらん状態にするワザとして登録している")
        return problems


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


# 持続する効果を与えなかった理由（ログ persistent_effect_skipped の reason。v0.12）
EFFECT_TARGET_KNOCKED_OUT = "knocked_out"  # 効果の対象（ワザを使ったポケモン自身）が、相手の「はんげき」のダメージですでに HP 以上


@dataclass(frozen=True)
class DamageAndRetaliation(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。そのあと、ワザを使ったポケモン自身に、「次の相手の番、このカードが相手の
    ワザによるダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）相手に ``retaliation`` ダメージを与える」持続する効果
    （``state.Retaliation``）を与える（v0.12。R団のファイヤーの「ほのおのかべ」。p.82 の最新の説明。docs/rocket-moltres-v0.12.md・
    docs/temporary-attack-effects-v0.12.md）。

    - ダメージの要素は ``damage_opponent_active``（p.321 の順番）。そのあと ``finish_damage_elements``（相手の「はんげき」。p.89）。
    - 効果は p.320 の効果の分類の (3)「このワザを使うポケモンへの効果」。p.89 のワザ解説（「こうらがえし」。同じ「相手の番ではたらく効果」）
      の「効果の対象：ワザを使ったポケモン自身」「効果の持続：次の相手の番の最後」。効果がはたらくのは次の相手の番（今の番 + 1。番は交互に
      進む。不変条件で確かめている）で、その番の終わりに消える（``persistent.remove_expired_persistent_effects``。W4・W5）。
    - 相手へのダメージを与えたかに関わらず与える（説明に「ダメージを与えたら」がない。相手が「ダメージを受けない」状態・「とうめい」で
      受けなかった・最終ダメージ 0 でも与える）。
    - ワザを使ったポケモンが、相手の「はんげき」のダメージ（このワザのダメージの処理のあと、この効果の前）で HP 以上になっていたら、
      きぜつするので与えない（p.89 のワザ解説「その後、相手はそのダメージできぜつしなければ「スターブーメラン」の効果で手札にもどる」・
      p.309。v0.10 の C16 と同じ。与えても、きぜつで場をはなれて消える（p.322）ので、ほかの結果は変わらない）。ログ
      ``persistent_effect_skipped``（``reason`` ``knocked_out``）。
    - 乱数は使わない。こんらん状態でワザがこんらんしたら、エンジンがこのワザの処理を呼ばない（ダメージも効果もない。p.309 の手順 5）。
    """

    retaliation: int
    implementation_id = "damage_and_retaliation"

    def __post_init__(self) -> None:
        if type(self.retaliation) is not int or self.retaliation <= 0 or self.retaliation % 10:
            raise ValueError(f"与えるダメージは 10 の倍数の正の数（{self.retaliation!r}）")

    def check(self, attack: Attack) -> list[str]:
        return _check_damage_then_effect(attack, "次の相手の番にダメージを受けたら相手にダメージを与える")

    def retaliation_terms(self) -> tuple[str, int | None]:
        """このワザが与える ``Retaliation`` の決め方と量（v0.13。不変条件・ログの監査が、状態の効果と登録表を照らす）。"""
        return RETALIATION_FIXED, self.retaliation


@dataclass(frozen=True)
class ReturnReceivedDamage(AttackEffect):
    """ダメージの要素のないワザ。ワザを使ったポケモン自身に、「次の相手の番、このカードが相手のワザによってダメージを受けたとき、
    （それによってこのカードが「きぜつ」しても、）そのポケモンにも同じダメージを与える。（ダメージ以外の効果は与えない）」持続する効果
    （``state.Retaliation``。``basis`` は ``RETALIATION_RECEIVED``）を与える（v0.13。わるいカメールの「こうらがえし」。p.89 の最新の説明。
    docs/shell-attack-v0.13.md・docs/variable-retaliation-v0.13.md）。

    - ダメージの目安の数字がないワザ（データの ``damage`` が None）だけを登録できる（S2。カードの図版・最新の説明にダメージがない）。
      コインもない（S1）。p.320 の効果の分類の (3)「このワザを使うポケモンへの効果」だけ。p.89 のワザ解説「効果の対象：ワザを使った
      ポケモン自身」「効果の持続：次の相手の番の最後」。効果がはたらくのは次の相手の番（今の番 + 1。番は交互に進む。不変条件で確かめて
      いる）で、その番の終わりに消える（``persistent.remove_expired_persistent_effects``。S3・S4・S33）。
    - 与えるダメージは効果を与えたときには決まらない（受けたダメージで決まる）ので、効果に量を持たない（``amount`` None）。受けた
      ダメージはワザ 1 回の中の値（v0.16b から解決の基盤の ``kernel.Deferred.received``）で、状態に持たない（docs/variable-retaliation-v0.13.md 3 章）。
    - ダメージの要素がないので、相手の「はんげき」・「ほのおのかべ」ははたらかない（効果の前に、ワザを使ったポケモンがきぜつすることは
      ない）。乱数は使わない。こんらん状態でワザがこんらんしたら、エンジンがこのワザの処理を呼ばない（効果もない。p.309 の手順 5）。
    """

    implementation_id = "return_received_damage"

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage is not None or attack.damage_display is not None or attack.damage_modifier is not None:
            problems.append("ダメージの目安のあるワザを、ダメージを与えずに受けたダメージを返す効果のワザとして登録している")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、受けたダメージを返す効果のワザとして登録している")
        return problems

    def retaliation_terms(self) -> tuple[str, int | None]:
        """このワザが与える ``Retaliation`` の決め方と量（量は受けたダメージで決まるので None）。"""
        return RETALIATION_RECEIVED, None


@dataclass(frozen=True)
class SetNextTurnAttackDamage(AttackEffect):
    """ダメージの要素のないワザ。ワザを使ったポケモン自身に、「次の自分の番、このカードが使う ``target_attack_name`` のダメージは
    ``damage`` になる」持続する効果（``state.NextTurnAttackDamage``）を与える（v0.27。ストライクの「つるぎのまい」。p.56・p.321 の最新の説明
    「次の自分の番、このカードが使う「きりさく」のダメージは「60」になる。」。p.57 のワザ解説。docs/scyther-v0.27.md）。

    - ダメージの目安の数字がないワザ（データの ``damage`` が None）だけを登録できる。コインもない。p.320 の効果の分類の (3)「このワザを
      使うポケモンへの効果」だけ（p.57「効果の対象：ワザを使ったポケモン自身」）。
    - 変わるワザは、同じカードの ``target_attack_index`` 番目のワザ（登録のデータ。名前 ``target_attack_name`` は登録の照合だけに使い、
      ワザを名前で探さない）。そのワザは説明のない、ダメージの目安の数字だけのワザでなければならない（``card_problems``）。
    - 効果がはたらくのは次の自分の番（今の番 + 2。番は交互に進む。不変条件で確かめている）で、その番の終わりに消える
      （``persistent.remove_expired_persistent_effects``。p.57「効果の持続：次の自分の番の最後」）。あいだの相手の番には何もしない。
      ベンチにもどる（にげる・ポケモンいれかえ・突風・ふきとばし）・進化・きぜつで消える（p.57・p.322・p.323）。
    - ダメージは p.321 の 2 段階で ``damage`` にする（「「60」になる」。p.321 の 2 段階の例「「ストライク」のワザ「つるぎのまい」などの
      効果」、図の「ストライクのワザ「つるぎのまい」のように、ワザを使うポケモンの持続する状態の効果を計算します」）。弱点・抵抗力・
      プラスパワー・ディフェンダーなどはそのあとの段階で計算する（``attack_damage_modifiers``・``damage.calculate_attack_damage``）。
      印刷の文面（kyuura の写し）の「2倍」・英語版の文面では処理を決めない。
    - 乱数は使わない。こんらん状態でワザがこんらんしたら、エンジンがこのワザの処理を呼ばない（効果もない。p.309 の手順 5）。ねむり・マヒ・
      エネルギーが足りないときは宣言できない（効果もない）。
    """

    target_attack_index: int
    target_attack_name: str
    damage: int
    implementation_id = "set_next_turn_attack_damage"

    def __post_init__(self) -> None:
        if type(self.target_attack_index) is not int or self.target_attack_index < 0:
            raise ValueError(f"ダメージが変わるワザの位置は 0 以上の整数（{self.target_attack_index!r}）")
        if type(self.damage) is not int or self.damage <= 0 or self.damage % 10:
            raise ValueError(f"変えたあとのダメージは 10 の倍数の正の数（{self.damage!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage is not None or attack.damage_display is not None or attack.damage_modifier is not None:
            problems.append("ダメージの目安のあるワザを、次の自分の番のワザのダメージを変える効果のワザとして登録している")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、次の自分の番のワザのダメージを変える効果のワザとして登録している")
        return problems

    def card_problems(self, attack: Attack, attacks: tuple[Attack, ...]) -> list[str]:
        index = self.target_attack_index
        if index == attack.index or not 0 <= index < len(attacks):
            return [f"ダメージが変わるワザの位置 {index} が、このカードのほかのワザではない"]
        target = attacks[index]
        problems = []
        if target.name_ja != self.target_attack_name:
            problems.append(f"ダメージが変わるワザの名前「{self.target_attack_name}」が、{index} 番目のワザ「{target.name_ja}」と違う")
        if target.text_ja is not None or target.text_en is not None or target.damage_modifier is not None or type(target.damage) is not int:
            problems.append(f"ダメージが変わるワザ「{target.name_ja}」が、説明のない、ダメージの目安の数字だけのワザではない")
        return problems

    def next_turn_terms(self) -> tuple[int, int]:
        """このワザが与える ``NextTurnAttackDamage`` のダメージが変わるワザの位置と、変えたあとのダメージ（不変条件・ログの監査が、状態の
        効果と登録表を照らす。v0.13 の ``retaliation_terms`` と同じ形）。"""
        return self.target_attack_index, self.damage


# 「ふきとばし」で入れ替えなかった理由（ログ forced_switch_skipped の reason。v0.4d）
TARGET_KNOCKED_OUT = "knocked_out"  # 相手の対戦ポケモンがこのワザのダメージできぜつする（効果の対象がいない。p.309・p.213）
NO_BENCH = "no_bench"  # 相手に控えポケモンがいない（最新の説明「相手に控えがいないとき、入れ替えはおこらない」）



def _check_damage_then_effect(attack: Attack, what: str) -> list[str]:
    """ダメージの目安の数字ぶんのダメージのあとに効果のあるワザの、データの形の確認（v0.4d。登録の照合 ``check`` が使う）。"""
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
    opponent_effect_elements = (FORCED_SWITCH_ELEMENT,)  # v0.11: 相手の対戦ポケモンに与える効果の要素（ko_prevention_attack_effect_problem）

    def check(self, attack: Attack) -> list[str]:
        return _check_damage_then_effect(attack, "相手を控えポケモンと入れ替える")

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        """「ふきとばし」の決定を待っている状態の確認: 種類は ``FORCED_SWITCH``、決定するのは相手（ワザを使ったプレイヤーではない）、
        1 匹だけ選ぶ、対象（``context`` の ``"target"``）が相手のバトル場のポケモン、選べるものが相手のベンチのポケモンの番号と同じ。"""
        return forced_switch_decision_problems(state, use, decision)


def forced_switch_decision_problems(state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
    """相手が選ぶ入れ替え（``FORCED_SWITCH``）の決定の確かめ（v0.4d の「ふきとばし」。v0.38 からアーボックの「いかくこうげき」・サイドンの「げきとつ」と
    共通）: 種類は ``FORCED_SWITCH``、決定するのは相手、1 匹だけ選ぶ、対象（``context`` の ``"target"``）が相手のバトル場のポケモン、選べるものが
    相手のベンチのポケモンの番号と同じ。"""
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
    - 回復はワザの要素の 1 つ（解決の基盤の ``programs.Drain``）で、きぜつの判定はワザのあと（``resolution.flow._finish_attack``）。乱数は使わない。
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

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        return DamageProfile(opponent=(self._base(state, use),))  # コインはない（v0.10）

    def _base(self, state: GameState, use: AttackUse) -> int:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = attack_of(state, use.key)  # v0.49: ワザを印刷したカード（use.key）
        attached = sum(1 for uid in attacker.energy if state.card_def(uid).provides is self.energy_type)
        extra = min(max(0, attached - len(attack.cost)), self.max_extra)
        return attack.damage + extra * self.per_energy


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

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        """「じこさいせい」の決定を待っている状態の確認（``discard_attached_energy_decision_problems``）。"""
        return discard_attached_energy_decision_problems(state, use, decision, self.energy_type, "じこさいせい")


def attached_basic_energy(state: GameState, attacker: PokemonInPlay, energy_type: EnergyType) -> list[int]:
    """ワザを使うポケモンについている ``energy_type`` の基本エネルギーカード（ついている順。カードの uid）。ワザの効果でトラッシュする
    カードの選べるもの（v0.7 の「じこさいせい」・v0.30 の ``DiscardEnergyThenDamage``。解決の基盤の ``programs.DiscardOwnEnergy`` も
    この関数で求める）。"""
    return [uid for uid in attacker.energy if state.card_def(uid).is_basic_energy and state.card_def(uid).provides is energy_type]


def discard_attached_energy_decision_problems(state: GameState, use: AttackUse, decision: PendingDecision, energy_type: EnergyType,
                                              label: str) -> list[str]:
    """ワザの効果で、ワザを使うポケモンについているエネルギーカードを 1 枚選んでトラッシュする決定を待っている状態の確認（v0.7 の
    「じこさいせい」から共通にした。v0.30）: 種類は ``DISCARD_ENERGY``、決定するのはワザを使ったプレイヤー、1 枚だけ選ぶ、選べるものが、
    ワザを使ったポケモンについている ``energy_type`` の基本エネルギーカード（ついている順）と同じ。``label`` は理由の文に書くワザの名前。"""
    _, attacker = state.find_pokemon(use.pokemon_id)
    problems = []
    if decision.kind != DISCARD_ENERGY:
        problems.append(f"「{label}」の決定の種類が {decision.kind!r}（{DISCARD_ENERGY} のはず）")
    if decision.player != use.player:
        problems.append(f"「{label}」でトラッシュするカードを選ぶのが、ワザを使ったプレイヤー {use.player} ではなくプレイヤー {decision.player}")
    if (decision.min_choices, decision.max_choices) != (1, 1):
        problems.append(f"「{label}」で選ぶ数が {decision.min_choices}〜{decision.max_choices}（1 枚のはず）")
    candidates = tuple(attached_basic_energy(state, attacker, energy_type))
    if not candidates or decision.options != candidates:
        problems.append(f"「{label}」の決定の選べるもの {decision.options} が、ついている「{energy_type.ja}」エネルギーカード {candidates} と合わない")
    return problems


@dataclass(frozen=True)
class DiscardEnergyThenDamage(AttackEffect):
    """ワザを使うポケモン自身についている ``energy_type`` のエネルギーカードを 1 枚トラッシュし、そのあと相手の対戦ポケモンにダメージの
    目安の数字ぶんのダメージ（v0.30。docs/discard-energy-attacks-v0.30.md）。第1弾のヒトカゲの「ひのこ」・リザード／ウインディ／ブーバーの
    「かえんほうしゃ」（印刷の文面「自分の「炎」エネルギーカードを1枚はがしてすてる。」）と、第4弾のポニータの「ひのこ」（印刷の文面
    「このカードについている「炎」エネルギーカードを1枚トラッシュする。(トラッシュできない時、このワザのダメージは0になる)」）。

    - 処理は kyuura の RUL-ENERGY-DISCARD-ATTACKS（確実）にしたがう: 炎エネルギーカードをトラッシュするワザは、ネオからの説明で、
      トラッシュがワザを使うための条件ではなく「ワザの効果」になった（kyuura の記録が引く『オフィシャルブック2000』のワザ解説と『トレーナーズ』の
      誌面。エンジンはこれらを読んでいない）。
      最新の説明は「自分についている「炎」エネルギーカードを1枚トラッシュする。トラッシュできないとき、このワザのダメージはなくなる。」。
      流れはワザの宣言 → 持続する効果の確認 → こんらんの確認 → ワザの内容の処理（ここでトラッシュ）。こんらんのコインが「うら」なら
      ワザの内容を処理しないので、トラッシュもしない（p.309 の手順 5。エンジンがこのワザの処理を呼ばない）。
    - ワザを宣言できる条件は、ほかのワザと同じ（必要なエネルギー。p.309）。トラッシュは宣言の条件ではないので、宣言のときにトラッシュしない。
    - 当てはめるのは「炎」エネルギーカードをトラッシュするワザだけ（``check`` が拒否する）。炎以外のエネルギーをトラッシュするワザに同じ説明が
      当てはまるかは、kyuura の記録の未解決の問い（open_questions）。似た文面の別のタイプのワザ（ミュウツーの「バリアー」など）に流用しない。
    - 要素の順番: トラッシュ（ワザを使うポケモンへの効果。p.320 の効果の (3)）→ 相手へのダメージ（(1)）。「トラッシュできないとき、この
      ワザのダメージはなくなる」がダメージを決めるので、トラッシュが先。
    - トラッシュするのは 1 枚だけ（「特に指示されていないかぎり、…エネルギーをトラッシュしてはいけません」。p.309。kyuura の
      GR-2000-P309-ATTACK-PROCEDURE）。ついている ``energy_type`` の基本エネルギーカードから、ワザを使うプレイヤーが選ぶ（決定
      ``DISCARD_ENERGY``。v0.7 の「じこさいせい」と同じ決定・同じ選べるもの（ついている順）。1 枚しかなくても決定を出す。実装上の仮定。K2）。
    - 「トラッシュできないとき」: ワザに必要なエネルギー（``check`` で ``energy_type`` を 1 個以上含むことを確かめる）が、ついている
      ``energy_type`` の基本エネルギーカードでしか払えないあいだは、このワザを自分のワザとして使うときには起こらない。v0.30 では起こらないので
      エンジンの不具合として ``RuntimeError`` にしていた。v0.31 の相手のワザを自分のワザとして使う効果（ゆびをふる・ちょうのうりょく。必要な
      エネルギーはいらない）で起こるようになったので、処理に使う文面のとおりに扱う（``when_lacking``: 最新の説明の「ダメージはなくなる」（既定。
      ダメージの要素を処理しない）か、第4弾のポニータの印刷の文面の「ダメージは0になる」（``"zero"``。基本となるダメージを 0 にして計算する））。
    - ダメージは p.321 の順番で計算する（弱点・抵抗力・プラスパワー・ディフェンダー・「ダメージを受けない」状態・「とうめい」は今までどおり）。
      トラッシュはダメージより先なので、相手がダメージを受けなくても（ダメージの要素が無効・「とうめい」で受けない・最終ダメージが 0）、
      トラッシュはすんでいる（ダメージを与えた後の効果ではない。Z23 にはかかわらない）。
    """

    energy_type: EnergyType
    when_lacking: str = "none"  # v0.31: トラッシュできないときの扱い（"none": ダメージはなくなる。"zero": ダメージは 0 になる）
    implementation_id = "discard_energy_then_damage"

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier is not None:
            problems.append(f"ダメージの目安に「{attack.damage_modifier}」があるワザを、目安の数字ぶんのダメージのワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない（エネルギーをトラッシュしてダメージを与えるワザではない）")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、エネルギーをトラッシュしてダメージを与えるワザとして登録している")
        if self.energy_type is not EnergyType.FIRE:
            # kyuura の RUL-ENERGY-DISCARD-ATTACKS の未解決の問い「炎エネルギー以外のエネルギーをトラッシュするワザにも同じ説明が当てはまるか」
            problems.append(f"「{self.energy_type.ja}」エネルギーをトラッシュするワザに、炎エネルギーのワザの説明（RUL-ENERGY-DISCARD-ATTACKS）を当てはめている")
        if self.energy_type not in attack.cost:
            problems.append(f"必要なエネルギーに「{self.energy_type.ja}」がないワザを登録している（トラッシュできない場合が起こりうる）")
        if self.when_lacking not in ("none", "zero"):
            problems.append(f"トラッシュできないときの扱い {self.when_lacking!r} は none か zero")
        return problems

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        """トラッシュするカードの決定を待っている状態の確認（「じこさいせい」と同じ形。``discard_attached_energy_decision_problems``）。"""
        label = state.definitions[use.key.card_id].attacks[use.key.attack_index].name_ja  # v0.31: 相手のワザとして使うときもワザの名前
        return discard_attached_energy_decision_problems(state, use, decision, self.energy_type, label)


@dataclass(frozen=True)
class RecoverEnergyAndSelfDamage(AttackEffect):
    """自分のトラッシュのエネルギーカードを ``max_cards`` 枚まで選んで手札に加え、そのあと自分に ``self_damage`` ダメージ（v0.9。
    化石の秘密のゴースの「エナジーへんかん」。p.158 の最新の説明「自分のトラッシュから、「エネルギーカード」を最大2枚選び出し、
    手札に加える。その後、自分に10ダメージ。」・解説「エネルギーカードの種類を問わず、2枚を選んでトラッシュから手札に持ってこられる
    めずらしいワザです」。docs/haunter-line-v0.9.md の H2〜H8）。

    - 選ぶのはワザを使ったプレイヤー（「自分のトラッシュから…選び出し」）。選べるものは、ワザを使ったプレイヤーのトラッシュにある
      エネルギーカードの uid（トラッシュの順。種類を問わない。今の対応カードのエネルギーカードは基本エネルギーだけ）。ワザの途中の
      決定（v0.4d の仕組み。決定の種類 ``RECOVER_ENERGY``）で、0〜``max_cards`` 枚（トラッシュにある枚数まで）を選ぶ。
    - 0 枚を選ぶこと（トラッシュにエネルギーカードがあるのに選ばない）は、「最大2枚選び出し」が 0 枚を含むかが書かれていないので、
      原典で決められない（H4）。決定は 0 枚も受け付ける形にして、0 枚を選んだら状態を変える前に ``UnsupportedError``
      （``UNRESOLVED_RECOVER_ZERO_ENERGY``）。決定は待ったままなので、1 枚以上を選び直せる。
    - トラッシュにエネルギーカードがなければ、選ぶものがないので決定を出さずに、自分へのダメージだけ（H5）。
    - 手札に加えてから自分にダメージ（「その後」。H6）。自分へのダメージは p.320 のダメージの (3)。v0.2f・v0.3d のとおり p.321 の順番で
      計算する（``deal_attack_damage`` の ``SELF``。ゴースの抵抗力は闘なので、超のワザでは 10）。
    - ダメージの目安の数字がないので、相手へのダメージの要素はない（``check``）。
    """

    max_cards: int
    self_damage: int
    implementation_id = "recover_energy_and_self_damage"

    def __post_init__(self) -> None:
        if not isinstance(self.max_cards, int) or isinstance(self.max_cards, bool) or self.max_cards < 1:
            raise ValueError(f"手札に加える枚数の上限は 1 以上の整数（{self.max_cards!r}）")
        if type(self.self_damage) is not int or self.self_damage <= 0 or self.self_damage % 10:
            raise ValueError(f"自分へのダメージは 10 の倍数の正の数（{self.self_damage!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage is not None or attack.damage_display is not None or attack.damage_modifier is not None:
            problems.append("ダメージの目安のあるワザを、トラッシュのエネルギーを手札に加えるワザとして登録している")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、トラッシュのエネルギーを手札に加えるワザとして登録している")
        return problems

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        return DamageProfile(self_damage=(self.self_damage,))  # 相手へのダメージの要素はない（v0.10）

    @staticmethod
    def _candidates(state: GameState, player: int) -> list[int]:
        """ワザを使ったプレイヤーのトラッシュにあるエネルギーカード（トラッシュの順）。"""
        return [uid for uid in state.players[player].discard if state.card_def(uid).category == "energy"]

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        """「エナジーへんかん」の決定を待っている状態の確認: 種類は ``RECOVER_ENERGY``、決定するのはワザを使ったプレイヤー、0〜
        ``max_cards`` 枚（トラッシュにある枚数まで）、選べるものが、ワザを使ったプレイヤーのトラッシュのエネルギーカード（トラッシュの順）。"""
        problems = []
        candidates = tuple(self._candidates(state, use.player))
        if decision.kind != RECOVER_ENERGY:
            problems.append(f"「エナジーへんかん」の決定の種類が {decision.kind!r}（{RECOVER_ENERGY} のはず）")
        if decision.player != use.player:
            problems.append(f"「エナジーへんかん」で選ぶのが、ワザを使ったプレイヤー {use.player} ではなくプレイヤー {decision.player}")
        if (decision.min_choices, decision.max_choices) != (0, min(self.max_cards, len(candidates))):
            problems.append(f"「エナジーへんかん」で選ぶ数が {decision.min_choices}〜{decision.max_choices}")
        if not candidates or decision.options != candidates:
            problems.append(f"「エナジーへんかん」の決定の選べるもの {decision.options} が、トラッシュのエネルギーカード {candidates} と合わない")
        return problems

@dataclass(frozen=True)
class DamageReducedByOwnCounters(AttackEffect):
    """ダメージの目安の数字から、ワザを使うポケモン自身にのっているダメージカウンター 1 個につき ``reduction_per_counter`` を引いた
    ダメージを、相手の対戦ポケモンに与える（v0.10。ゴーリキーの「からてチョップ」。p.190 の最新の説明「このワザのダメージは、自分に
    のっているダメージカウンターの数×10だけ、小さくなる。」。p.186 のタケシのマンキーの「からてチョップ」も同じ最新の説明。
    docs/machamp-line-v0.10.md）。

    - ダメージの目安「50−」の「−」は、説明にしたがって書かれた数字よりダメージが小さくなることがある印（p.320）。説明にしたがった
      計算が p.321 の 1 段階（基本となるダメージ）で、そのあと弱点・抵抗力・プラスパワーなどを計算する（v0.6 のハイドロポンプの「+」と
      同じ）。数えるのは、ワザを使うときに自分（ワザを使うポケモン。進化していれば重なり全体のポケモン）にのっているダメージカウンター
      （ダメージ ÷ 10。p.319「ダメージカウンター1個につき、10ダメージ」）。
    - 1 段階（と 2 段階）で 0 以下なら、そこで計算を終え、「ダメージを与えなかった」（p.319・p.321。弱点・抵抗力・プラスパワーは
      計算しない。``damage.calculate_attack_damage``）。ワザの失敗ではない（説明に「失敗」とは書かれていない）。
    - 乱数は使わない。
    """

    reduction_per_counter: int
    implementation_id = "damage_reduced_by_own_counters"

    def __post_init__(self) -> None:
        if type(self.reduction_per_counter) is not int or self.reduction_per_counter <= 0 or self.reduction_per_counter % 10:
            raise ValueError(f"ダメージカウンター 1 個あたりに減らすダメージは 10 の倍数の正の数（{self.reduction_per_counter!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier != "-":
            problems.append("ダメージの目安に「−」のないワザを、自分のダメージカウンターの数だけダメージが小さくなるワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、自分のダメージカウンターの数だけダメージが小さくなるワザとして登録している")
        return problems

    def _base(self, state: GameState, use: AttackUse) -> int:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = attack_of(state, use.key)  # v0.49: ワザを印刷したカード（use.key）
        counters = attacker.damage // state.rules.damage_per_counter
        return attack.damage - counters * self.reduction_per_counter

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        return DamageProfile(opponent=(self._base(state, use),))  # コインはない


@dataclass(frozen=True)
class DamageAndSelfSleep(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージを与えた後、ワザを使ったポケモン自身をねむり状態にする（v0.17b。R団のカビゴンの
    「たおれこむ」。p.245 の最新の説明「ダメージを与えた後、自分を「ねむり」状態にする。」。docs/rocket-snorlax-v0.17b.md の Z21〜Z29）。

    - 解決の基盤の要素の並びは、既存の要素 ``Damage`` と、ワザを使ったポケモン自身を対象にした ``Status(SLEEP, target=SELF,
      after_damage="damage")``（v0.17b で ``Status`` に対象と「ダメージを与えた後」を加えた。カードごとの要素ではない）。
    - 順番: 相手へのダメージ → ダメージを受けたときの効果の窓（はんげき・ほのおのかべ・こうらがえし）→ 自分をねむり（p.320・p.89。Z21）。
      そのあいだに自分が HP 以上になったら、効果の対象がいないのでねむりにしない（p.309。Z22）。
    - 相手へのダメージの要素がダメージを与えなかったとき（ディフェンダーで 0・「ダメージを受けない」状態・「とうめい」で受けない）に自分をねむりに
      するかは原典で決まらない（「ダメージを与えた後」が順番か条件か。Z23。UNRESOLVED）ので、宣言の前に止める
      （``UNRESOLVED_EFFECT_AFTER_NO_DAMAGE``）。
    - 相手の対戦ポケモンに与える効果ではない（``opponent_effect_elements`` は空。G37 の対象外）。
    - v0.13 の約束（``resolve``・``resume``）は持たない。v0.13 の止める関数の型（``v013_checks.VERIFIED``）にも入れない。
    """

    implementation_id = "damage_and_self_sleep"

    def check(self, attack: Attack) -> list[str]:
        return _check_damage_then_effect(attack, "自分をねむり状態にする")


@dataclass(frozen=True)
class DamageAndSelfDamage(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。そのあと、自分にも ``self_damage`` ダメージ（v0.10。ゴーリキーの
    「じごくぐるま」。p.190 の最新の説明「自分にも20ダメージ。」。docs/machamp-line-v0.10.md）。

    - ダメージの目安に「×」「+」「−」がないので、説明の最初の「相手の対戦ポケモンに 60 ダメージ。」が省略されている（p.320）。
      ワザの要素は書いてある順番に処理する（p.309・p.320）: 相手へのダメージ（(1)）→ 自分へのダメージ（(3)）。どちらもダメージの
      要素で、コインはない（v0.2f のでんげき（``SelfDamageOnTails``）からコインを除いた形）。
    - 自分へのダメージもワザによるダメージ（p.321）なので、p.321 の順番で計算する（``deal_attack_damage`` の ``SELF``。弱点・抵抗力は
      自分のタイプと自分の弱点・抵抗力。v0.3d。プラスパワーで +10、ディフェンダーで −20。p.257・p.90）。
    - 相手の対戦ポケモンがこのワザできぜつしても、自分へのダメージの要素は無視しない（p.309「それ以降の内容を無視してはいけません」）。
      きぜつは、ワザの要素をすべて処理してからエンジンがまとめて行う（1 つのワザできぜつしたポケモンは「同時」。p.324）。
    - 相手の「はんげき」（v0.10）は、自分へのダメージのあと（ダメージの処理がすべて終わったところ。p.89）に与えられる（エンジンが
      ``finish_damage_elements`` を呼ぶ）。自分へのダメージですでにきぜつしていれば与えられない（C15）。
    - 乱数は使わない。
    """

    self_damage: int
    implementation_id = "damage_and_self_damage"

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

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        return DamageProfile(opponent=super().damage_profile(state, use).opponent, self_damage=(self.self_damage,))


# ---------------------------------------------------------------- v0.31: 保留していた 22 枚のワザ（docs/held-cards-v0.31.md）
# 処理は解決の基盤の要素の並び（resolution/programs.py の BUILDERS）。ここには、登録の確かめ（``check``）・決定の形（``decision_problems``）・
# ワザを使うための条件（``usage_problem``）だけを書く。処理に使う文面は、kyuura の最新の説明・エラッタがあればそれ、なければ kyuura の印刷の文面
# （登録の ``play_text_ja``）。


def _check_form(attack: Attack, what: str, *, damage: str, modifier: str | None = None, cost_types: Iterable[EnergyType] = ()) -> list[str]:
    """登録の確かめの共通の部分（v0.31）。``damage`` は ``"none"``（ダメージの目安がない）・``"fixed"``（数字だけ）・``"modified"``（``modifier`` の
    記号つき）。``cost_types`` は必要なエネルギーにあるはずのタイプ。"""
    problems = []
    if attack.text_ja is None:
        problems.append(f"説明文のないワザを、{what}として登録している")
    if damage == "none":
        if attack.damage is not None or attack.damage_modifier is not None:
            problems.append(f"ダメージの目安のあるワザを、{what}（ダメージの目安なし）として登録している")
    elif damage == "fixed":
        if attack.damage_modifier is not None:
            problems.append(f"ダメージの目安に「{attack.damage_modifier}」があるワザを、{what}として登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
    elif damage == "modified":
        if attack.damage_modifier != modifier:
            problems.append(f"ダメージの目安の記号が「{attack.damage_modifier}」（「{modifier}」のはず）")
        if type(attack.damage) is not int or attack.damage < 0 or attack.damage % 10:
            problems.append("ダメージの目安の数字が 10 の倍数ではない")
    for energy_type in cost_types:
        if energy_type not in attack.cost:
            problems.append(f"必要なエネルギーに「{energy_type.ja}」がないワザを登録している")
    return problems


def _decision_form(decision: PendingDecision, label: str, *, kind: str, player: int, choices: tuple[int, int], options: Iterable[int]) -> list[str]:
    """ワザの途中の決定の形の確かめの共通の部分（v0.31）。"""
    problems = []
    if decision.kind != kind:
        problems.append(f"「{label}」の決定の種類が {decision.kind!r}（{kind} のはず）")
    if decision.player != player:
        problems.append(f"「{label}」の決定をするのがプレイヤー {decision.player}（{player} のはず）")
    if (decision.min_choices, decision.max_choices) != choices:
        problems.append(f"「{label}」で選ぶ数が {decision.min_choices}〜{decision.max_choices}（{choices[0]}〜{choices[1]} のはず）")
    expected = tuple(options)
    if decision.options != expected:
        problems.append(f"「{label}」の決定の選べるもの {decision.options} が {expected} と合わない")
    return problems


def _label(state: GameState, use: AttackUse) -> str:
    return state.definitions[use.key.card_id].attacks[use.key.attack_index].name_ja


def _attached_energy_cards(state: GameState, pokemon: PokemonInPlay, energy_type: EnergyType | None) -> list[int]:
    if energy_type is None:
        return [uid for uid in pokemon.energy if state.card_def(uid).category == "energy"]
    return attached_basic_energy(state, pokemon, energy_type)


@dataclass(frozen=True)
class SwitchOpponentActive(AttackEffect):
    """相手の控えポケモンを（ワザを使ったプレイヤーが）選んで、相手の対戦ポケモンと入れ替える（v0.31。キュウコンの「かどわかす」。印刷の文面
    「相手の控えポケモンを選んで、相手の対戦ポケモンと入れ替える。」）。バタフリーの「ふきとばし」（相手が選ぶ）と同じ要素 ``ForceSwitch`` で、選ぶ
    プレイヤーだけが違う。相手に控えがいなければ、処理の対象がないので入れ替えない（p.309。H5 と同じ。ログ ``forced_switch_skipped``）。相手への効果
    なので「とうめい」・「ワザをうけない」状態を評価する。"""

    implementation_id = "switch_opponent_active"
    opponent_effect_elements = (FORCED_SWITCH_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        # v0.41: 説明の文面も確かめる（v0.40 までは形だけ）。キュウコンの「かどわかす」（v0.31）と、ウツボットの「さそうかおり」（v0.41。「選んで」を「選び」と
        # 書くだけの違い）の書き方だけを受け付ける（``SWITCH_OPPONENT_ACTIVE_TEXTS``）
        return _check_form(attack, "相手の控えポケモンと入れ替えるワザ", damage="none") + _check_exact_text(
            attack, "相手の控えポケモンを選んで相手の対戦ポケモンと入れ替えるワザ", SWITCH_OPPONENT_ACTIVE_TEXTS)

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        p = state.players[1 - use.player]
        problems = _decision_form(decision, _label(state, use), kind=FORCED_SWITCH, player=use.player, choices=(1, 1),
                                  options=(pokemon.pokemon_id for pokemon in p.bench))
        if p.active is None or p.active.pokemon_id != decision.context_value("target"):
            problems.append(f"入れ替えの対象 {decision.context_value('target')!r} が相手のバトル場のポケモンではない")
        return problems


# v0.41: ``SwitchOpponentActive`` が受け付ける説明（kyuura の印刷の文面）。キュウコン（v0.31）とウツボット（v0.41）。docs/heal-counter-status-v0.41.md 2 章
SWITCH_OPPONENT_ACTIVE_TEXTS = (
    "相手の控えポケモンを選んで、相手の対戦ポケモンと入れ替える。",
    "相手の控えポケモンを選び、相手の対戦ポケモンと入れ替える。",
)


@dataclass(frozen=True)
class DiscardEnergyBeforeDamage(AttackEffect):
    """ワザを使うポケモンについている ``energy_type``（None ならどのタイプでも）のエネルギーカードを ``count`` 枚（None ならすべて）トラッシュしてから、
    相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ（v0.31。リザードンの「ほのおのうず」（2 枚）・サンダーの「10まんボルト」（すべて）・
    カツラのウインディの「ほのおのあらし」（「炎」3 枚））。

    - ``timing``: トラッシュの時点。「ほのおのあらし」は炎エネルギーカードをトラッシュして大きなダメージを与えるワザ（kyuura の RUL-ENERGY-DISCARD-ATTACKS
      の範囲「炎エネルギーカードをトラッシュするタイプのワザは、すべて同じ処理」）なのでワザの効果（``"effect"``）。ほかは、印刷の文面がワザを使うための
      条件の形（「はがしてすてる」）で、記録の未解決の問い（炎以外）にあたるので決められない（``"unresolved"``。こんらん状態で使うときだけ結果が変わるので、
      そのときは宣言のあとに止める。HC1）。こんらんでなければ、どちらの読み方でもトラッシュ → ダメージの結果は同じ。
    - トラッシュできない場合は、必要なエネルギー（``check``）から起こらない（相手のワザとして使うときだけ。``when_lacking``: 印刷の文面が
      「はがしてすてる」なら ``"condition"``（条件か効果か決められない）、「…トラッシュしなければ、このワザは使えない」なら ``"cannot_use"``、
      v0.34 の「…はがしてすてなければ、このワザは失敗する」（ブースターの「かえんほうしゃ」）なら ``"fail"``（ワザの失敗。p.323））。
    - v0.34: ブースターの「かえんほうしゃ」は、炎エネルギーカードをトラッシュして大きなダメージを与えるワザで、ワザの名前も RUL-ENERGY-DISCARD-ATTACKS が
      挙げる「かえんほうしゃ」なので、記録の範囲としてトラッシュの時点はワザの効果（``"effect"``。カツラのウインディの「ほのおのあらし」と同じ）。
      印刷の文面が記録の最新の説明の元のカード（第1弾のウインディ）と違うので、処理に使う文面は印刷の文面（トラッシュできなければ失敗）。
    """

    energy_type: EnergyType | None
    count: int | None
    timing: str
    when_lacking: str
    implementation_id = "discard_energy_before_damage"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "エネルギーをトラッシュしてダメージを与えるワザ", damage="fixed",
                               cost_types=() if self.energy_type is None else (self.energy_type,))
        if self.count is not None:
            usable = len(attack.cost) if self.energy_type is None else sum(1 for t in attack.cost if t is self.energy_type)
            if self.count > usable:
                problems.append(f"トラッシュする {self.count} 枚が、必要なエネルギーで必ずついている枚数 {usable} より多い")
        if self.timing == "effect" and self.energy_type is not EnergyType.FIRE:
            problems.append("炎エネルギーカードのワザでないのに、トラッシュの時点を RUL-ENERGY-DISCARD-ATTACKS の範囲（効果）にしている")
        if self.timing not in ("effect", "unresolved") or self.when_lacking not in ("condition", "cannot_use", "fail"):
            problems.append(f"トラッシュの時点 {self.timing!r}・トラッシュできないときの扱い {self.when_lacking!r} が正しくない")
        return problems

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        _, attacker = state.find_pokemon(use.pokemon_id)
        count = self.count if self.count is not None else 0
        return _decision_form(decision, _label(state, use), kind=DISCARD_ENERGY, player=use.player, choices=(count, count),
                              options=_attached_energy_cards(state, attacker, self.energy_type))


@dataclass(frozen=True)
class SleepOnHeadsWithoutDamage(AttackEffect):
    """コインを投げて「おもて」なら、相手を「ねむり」状態にする（ダメージの目安なし。v0.31。第1弾のゴースの「さいみんガス」・ピッピの「うたう」）。
    v0.17a の ``ConfuseOnHeadsWithoutDamage`` と同じ形で、特殊状態だけが違う。"""

    implementation_id = "sleep_on_heads_without_damage"
    opponent_effect_elements = (SLEEP,)

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "コインでねむりにするワザ", damage="none")


@dataclass(frozen=True)
class DiscardEnergyThenSelfEffect(AttackEffect):
    """ワザを使うポケモンについている ``energy_type`` のエネルギーカードを 1 枚トラッシュし、自分に次の相手の番の持続する効果（``effect_kind``）を与える
    （v0.31。第1弾のゴースの「みちづれ」（``destiny_bond``）・ミュウツーの「バリアー」（``attack_barrier``））。トラッシュの時点は決められない（印刷の
    文面がワザを使うための条件の形で、超エネルギー。HC1。こんらん状態で使うときは止める）。ダメージの目安はない。"""

    energy_type: EnergyType
    effect_kind: str
    implementation_id = "discard_energy_then_self_effect"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "エネルギーをトラッシュして持続する効果を与えるワザ", damage="none", cost_types=(self.energy_type,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        _, attacker = state.find_pokemon(use.pokemon_id)
        return _decision_form(decision, _label(state, use), kind=DISCARD_ENERGY, player=use.player, choices=(1, 1),
                              options=attached_basic_energy(state, attacker, self.energy_type))


@dataclass(frozen=True)
class DamagePlusDefenderEnergy(AttackEffect):
    """ダメージの目安の数字 +「相手についているエネルギーカード」× ``per`` の追加ダメージ（v0.31。ミュウツーの「サイコキネシス」）。"""

    per: int
    implementation_id = "damage_plus_defender_energy"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "相手のエネルギーで追加ダメージのワザ", damage="modified", modifier="+")


@dataclass(frozen=True)
class DamagePlusOwnCounters(AttackEffect):
    """ダメージの目安の数字 + 自分にのっているダメージカウンターの数 × ``per``（v0.31。わるいブースターの「いかり」）。"""

    per: int
    implementation_id = "damage_plus_own_counters"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "自分のダメージカウンターで追加ダメージのワザ", damage="modified", modifier="+")


@dataclass(frozen=True)
class CopyOpponentAttackEffect(AttackEffect):
    """相手の対戦ポケモンのワザの中から 1 つを選び、それを自分のワザとして使う（v0.31。ピクシーの「ゆびをふる」（``clause="cannot_use"``）・
    ピッピの「ゆびをふる」（``clause="follow_text"``。kyuura の card_differences の PMCG1-067 の記録の最新の説明と解説））。どちらも、使うワザに必要な
    エネルギーはいらない。要素は ``resolution.programs.CopyOpponentAttack``（``clause`` の意味はそちら）。

    決定（``SELECT_ATTACK``）のあと、選んだワザの決定は、そのワザの実装の ``decision_problems`` で確かめる（``context`` の ``"copied"``）。"""

    clause: str
    implementation_id = "copy_opponent_attack"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "相手のワザを自分のワザとして使うワザ", damage="none")
        if self.clause not in ("cannot_use", "follow_text"):
            problems.append(f"説明の条件 {self.clause!r} は cannot_use か follow_text")
        return problems

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        return copy_decision_problems(state, use, decision)


def copy_decision_problems(state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
    """相手のワザを自分のワザとして使うワザの決定の確かめ（v0.31。ワザを選ぶ決定と、選んだワザの決定）。"""
    copied = decision.context_value("copied")
    if copied is not None:
        card_id, index = copied
        entry = state.effects.attack_entry(card_id, index)
        if entry is None or decision.kind == SELECT_ATTACK:
            return [f"自分のワザとして使った相手のワザ {copied!r} の決定 {decision.kind} が正しくない"]
        return entry.effect.decision_problems(state, AttackUse(use.player, use.pokemon_id, AttackKey(card_id, index)), decision)
    source = state.players[1 - use.player].active
    problems = []
    if decision.kind != SELECT_ATTACK or decision.player != use.player or (decision.min_choices, decision.max_choices) != (1, 1):
        problems.append(f"相手のワザを選ぶ決定の形 {decision.kind}・{decision.player}・{decision.min_choices}〜{decision.max_choices} が正しくない")
    # v0.49: 選べるものは、相手の対戦ポケモンが今持つワザ（``held_attack_keys``）。並びがいちばん上のカードのワザと同じなら v0.48 と同じ形（``copy_from``・ワザの位置）、
    # 違えば ``copy_attacks``（(カードの id, 位置) の並び）と並びの位置。決定を待つ間は場が変わらないので、出したときと同じ並び
    entries, legacy = held_attack_keys(state, source) if source is not None else ([], True)
    keys = [(key.card_id, key.attack_index) for key, _ in entries]
    copied_keys = decision.context_value("copy_attacks")
    if source is None or (legacy and (copied_keys is not None or decision.context_value("copy_from") != state.cards[source.card].card_id)):
        problems.append(f"相手のワザを選ぶ決定のカード {decision.context_value('copy_from')!r} が、相手のバトル場のポケモンではない")
    elif not legacy and (copied_keys is None or [tuple(key) for key in copied_keys] != keys or decision.context_value("copy_from") is not None):
        problems.append(f"相手のワザを選ぶ決定のワザの並び {copied_keys!r} が、相手のバトル場のポケモンが今持つワザ {keys} ではない")
    if not decision.options or any(not 0 <= index < len(entries) for index in decision.options):
        problems.append(f"相手のワザを選ぶ決定の選べるもの {decision.options} が、相手のバトル場のポケモンのワザではない")
    held = [i for i, (_, problem) in enumerate(entries) if problem is not None]
    if not set(held) <= set(decision.context_value("unresolved_choices", ())):
        problems.append(f"持つかが読み方で変わるワザ {held} が、選ぶと止めるものにない")
    unsupported = decision.context_value("unsupported_choices", ())
    if not set(unsupported) <= set(decision.options):
        problems.append(f"対応していないワザ {unsupported} が、選べるもの {decision.options} にない")
    return problems


@dataclass(frozen=True)
class ReduceDamageNextTurn(AttackEffect):
    """次の相手の番でこのカードが受けるダメージが ``amount`` へる（v0.31。ピクシーの「ちいさくなる」。持続する効果 ``DamageReduction``。p.321 の 8 段階）。

    v0.37: 説明の文面も確かめる（v0.36 までは形だけ）。受け付けるのは、ピクシーの書き方と、化石の秘密のベトベターの「ちいさくなる」の書き方
    （「…ダメージは{n}へる。(ダメージ以外の効果はそのまま)」。括弧の中は「ダメージ以外の効果は受ける」ことで、8 段階のダメージだけを変える効果と同じ）
    だけ（``reduce_damage_next_turn_texts``）。へる数が登録と違う書き方・ほかの書き方は受け付けない。"""

    amount: int
    implementation_id = "reduce_damage_next_turn"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "受けるダメージを減らすワザ", damage="none")
        return problems + _check_exact_text(attack, "次の相手の番に受けるダメージがへる効果", reduce_damage_next_turn_texts(self.amount))


def reduce_damage_next_turn_texts(amount: int) -> tuple[str, ...]:
    """``ReduceDamageNextTurn`` が受け付ける説明の書き方（v0.37）。"""
    return (f"次の相手の番でこのカードが受けるダメージが{amount}へる。",  # ピクシー（PMCG2-044）
            f"次の相手の番でこのカードが受けるダメージは{amount}へる。(ダメージ以外の効果はそのまま)")  # 化石の秘密のベトベター（PMCG3-003）


@dataclass(frozen=True)
class DiscardFireThenMillOpponent(AttackEffect):
    """自分の「炎」エネルギーカードを好きなだけはがしてすてる。その後、はがしたのと同じ枚数のカードを相手の山札の上から取り、相手のトラッシュにすてる
    （v0.31。化石の秘密のファイヤーの「やまやき」）。トラッシュの時点は決められない（印刷の文面がワザを使うための条件の形で、大きなダメージを与えるワザ
    ではないので RUL-ENERGY-DISCARD-ATTACKS の範囲か分からない。HC1）。0 枚は HC5、相手の山札が足りない枚数は HC6。"""

    implementation_id = "discard_fire_then_mill_opponent"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "炎エネルギーをトラッシュして相手の山札をトラッシュするワザ", damage="none", cost_types=(EnergyType.FIRE,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        _, attacker = state.find_pokemon(use.pokemon_id)
        candidates = attached_basic_energy(state, attacker, EnergyType.FIRE)
        return _decision_form(decision, _label(state, use), kind=DISCARD_ENERGY, player=use.player, choices=(0, len(candidates)),
                              options=candidates)


@dataclass(frozen=True)
class FailOnTailsDamage(AttackEffect):
    """コインを投げて「うら」なら、このワザは失敗する（v0.31。化石の秘密のファイヤーの「ゴッドバード」。p.323「12 ワザの失敗」）。「おもて」なら
    ダメージの目安の数字ぶんのダメージ。

    v0.33: ``coins`` 枚を投げ、1 つでも「うら」なら失敗する（タケシのサイホーンの「ドリルタックル」「コインを2枚投げ、1つでも「うら」なら、このワザは
    失敗する。」は 2）。すべて「おもて」のときだけダメージ（「おもて」の数 × のダメージ（``CoinFlipDamage``）ではない）。既定の 1 は v0.31 と同じ。"""

    coins: int = 1
    implementation_id = "fail_on_tails_damage"

    def __post_init__(self) -> None:
        if type(self.coins) is not int or self.coins < 1:
            raise ValueError(f"コインの枚数は 1 以上の整数（{self.coins!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "コインでワザが失敗するワザ", damage="fixed")
        text = attack.text_ja or ""
        expected = "コインを投げて「うら」なら、このワザは失敗する。" if self.coins == 1 else f"コインを{self.coins}枚投げ、1つでも「うら」なら、このワザは失敗する。"
        if text != expected:
            problems.append(f"説明 {text!r} が、コイン {self.coins} 枚で失敗するワザの説明 {expected!r} と違う")
        return problems


@dataclass(frozen=True)
class HealSelfOnHeadsIfDamaged(AttackEffect):
    """コインを投げて「おもて」なら、このカードからダメージカウンターを ``counters`` 個とりのぞく。このカードにダメージカウンターがのってない時には、
    このワザは使えない（v0.31。化石の秘密のヤドンの「ぼーっとする」）。"""

    counters: int
    implementation_id = "heal_self_on_heads_if_damaged"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "コインで自分のダメージカウンターをとりのぞくワザ", damage="none")

    def usage_problem(self, state: GameState, attacker: PokemonInPlay) -> IllegalActionError | None:
        if attacker.damage == 0:
            return IllegalActionError("NO_DAMAGE_COUNTERS", "このカードにダメージカウンターがのっていないので、このワザは使えない（ワザの説明）")
        return None


@dataclass(frozen=True)
class DiscardEnergyThenRecoverTrainer(AttackEffect):
    """このカードについている ``energy_type`` のエネルギーカードを 1 枚はがしてすてなければ、このワザは使えない。自分のトラッシュの中からトレーナー
    カードを 1 枚選び、手札に加える（v0.31。化石の秘密のヤドンの「ゴミあさり」）。トラッシュは、必要なエネルギー（``check``）から必ずできる。時点は
    決められない（超エネルギー。HC1）。トラッシュにトレーナーカードがなければ、処理の対象がないので手札に加えない（p.309）。"""

    energy_type: EnergyType
    implementation_id = "discard_energy_then_recover_trainer"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "エネルギーをトラッシュしてトレーナーを回収するワザ", damage="none", cost_types=(self.energy_type,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        _, attacker = state.find_pokemon(use.pokemon_id)
        label = _label(state, use)
        if decision.kind == DISCARD_ENERGY:
            return _decision_form(decision, label, kind=DISCARD_ENERGY, player=use.player, choices=(1, 1),
                                  options=attached_basic_energy(state, attacker, self.energy_type))
        trainers = [uid for uid in state.players[use.player].discard if state.card_def(uid).category == "trainer"]
        return _decision_form(decision, label, kind=RECOVER_TRAINER, player=use.player, choices=(1, 1), options=trainers)


@dataclass(frozen=True)
class DamageThenOptionalBenchDamage(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。のぞむなら、このカードについている ``energy_type`` エネルギーカードを 1 枚トラッシュし、
    その後、相手の控えポケモンを 1 匹選んで（「弱点・抵抗力」に関係なく）``bench_damage`` ダメージを与えてもよい（v0.31。わるいギャロップの「ひばしら」）。"""

    energy_type: EnergyType
    bench_damage: int
    implementation_id = "damage_then_optional_bench_damage"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "控えポケモンにもダメージを与えられるワザ", damage="fixed", cost_types=(self.energy_type,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        _, attacker = state.find_pokemon(use.pokemon_id)
        label = _label(state, use)
        if decision.kind == DISCARD_ENERGY:
            return _decision_form(decision, label, kind=DISCARD_ENERGY, player=use.player, choices=(0, 1),
                                  options=attached_basic_energy(state, attacker, self.energy_type))
        bench = state.players[1 - use.player].bench
        return _decision_form(decision, label, kind=SELECT_POKEMON, player=use.player, choices=(1, 1), options=(p.pokemon_id for p in bench))


@dataclass(frozen=True)
class FailOnTailsDiscardThenDamage(AttackEffect):
    """コインを投げて「うら」なら、このワザは失敗する。「おもて」の時は、このカードについている ``energy_type`` エネルギーカードを 1 枚トラッシュする
    （トラッシュできない時、このワザのダメージは 0 になる）（v0.31。わるいリザードの「ファイヤーボール」）。印刷の文面がワザの効果の形なので、トラッシュは
    こんらんのコインのあと（時点の問いはない）。"""

    energy_type: EnergyType
    implementation_id = "fail_on_tails_discard_then_damage"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "コインで失敗し、おもてならエネルギーをトラッシュするワザ", damage="fixed", cost_types=(self.energy_type,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        _, attacker = state.find_pokemon(use.pokemon_id)
        return _decision_form(decision, _label(state, use), kind=DISCARD_ENERGY, player=use.player, choices=(1, 1),
                              options=attached_basic_energy(state, attacker, self.energy_type))


@dataclass(frozen=True)
class CoinBonusDiscardThenDamage(AttackEffect):
    """コインを投げて「おもて」なら、``bonus`` ダメージを追加して、このカードについている ``energy_type`` エネルギーカードを 1 枚トラッシュする（トラッシュ
    できない時、このワザのダメージは 0 になる）（v0.31。わるいブースターの「ひあそび」）。"""

    energy_type: EnergyType
    bonus: int
    implementation_id = "coin_bonus_discard_then_damage"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "コインで追加ダメージとトラッシュのワザ", damage="modified", modifier="+", cost_types=(self.energy_type,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        _, attacker = state.find_pokemon(use.pokemon_id)
        return _decision_form(decision, _label(state, use), kind=DISCARD_ENERGY, player=use.player, choices=(1, 1),
                              options=attached_basic_energy(state, attacker, self.energy_type))


@dataclass(frozen=True)
class CoinsPerEnergyDamageThenDiscard(AttackEffect):
    """このカードについている ``energy_type`` エネルギーカードの数だけコインを投げ、「おもて」の数 × ``per`` のダメージ。その後、「おもて」の数ぶんの
    ``energy_type`` エネルギーカードを、このカードからトラッシュする（v0.31。わるいリザードンの「れんぞくファイヤーボール」）。「おもて」の数は、ついている
    枚数より多くならないので、トラッシュできない場合は起こらない。"""

    energy_type: EnergyType
    per: int
    implementation_id = "coins_per_energy_damage_then_discard"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "ついているエネルギーの数のコインのワザ", damage="modified", modifier="×", cost_types=(self.energy_type,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        _, attacker = state.find_pokemon(use.pokemon_id)
        candidates = attached_basic_energy(state, attacker, self.energy_type)
        count = decision.min_choices
        return _decision_form(decision, _label(state, use), kind=DISCARD_ENERGY, player=use.player, choices=(count, count),
                              options=candidates) + ([] if 1 <= count <= len(candidates) else [f"トラッシュする数 {count} が正しくない"])


@dataclass(frozen=True)
class DiscardEnergyThenDraw(AttackEffect):
    """このカードについているエネルギーカードを 1 枚選び、トラッシュする。その後、山札からカードを ``draw`` 枚引く（v0.31。わるいゴルダックの「だい3のめ」）。
    印刷の文面がワザの効果の形なので、時点の問いはない。"""

    draw: int
    implementation_id = "discard_energy_then_draw"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "エネルギーをトラッシュして山札から引くワザ", damage="none")

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        _, attacker = state.find_pokemon(use.pokemon_id)
        return _decision_form(decision, _label(state, use), kind=DISCARD_ENERGY, player=use.player, choices=(1, 1),
                              options=_attached_energy_cards(state, attacker, None))


@dataclass(frozen=True)
class DamageThenMoveEnergyToBench(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。このカードについているエネルギーカードをすべてはがし、自分の控えポケモンに好きなように
    つける（自分に控えがいない時、エネルギーカードはトラッシュする）（v0.31。わるいマルマインの「エナジーボム」。CR-TRANSPARENCY-ENERGY-BOMB）。"""

    implementation_id = "damage_then_move_energy_to_bench"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "エネルギーを控えにつけかえるワザ", damage="fixed")

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        _, attacker = state.find_pokemon(use.pokemon_id)
        problems = _decision_form(decision, _label(state, use), kind=ATTACH_TO_BENCH, player=use.player, choices=(1, 1),
                                  options=(p.pokemon_id for p in state.players[use.player].bench))
        energy = decision.context_value("energy")
        remaining = tuple(decision.context_value("remaining", ()))
        if energy not in attacker.energy or any(uid not in attacker.energy for uid in remaining):
            problems.append(f"つけかえるエネルギー {energy!r}・残り {remaining} が、ワザを使ったポケモンについていない")
        return problems


@dataclass(frozen=True)
class DamageThenDiscardAllOnTails(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「うら」なら、自分についている ``energy_type``（None ならすべての）エネルギー
    カードを、すべてトラッシュする（v0.31。カスミのゴルダックの「エクストラビーム」・カツラのキュウコンの「しゃくねつ」）。"""

    energy_type: EnergyType | None
    implementation_id = "damage_then_discard_all_on_tails"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "コインでエネルギーをすべてトラッシュするワザ", damage="fixed")


@dataclass(frozen=True)
class CoinDiscardOpponentEnergyEach(AttackEffect):
    """コインを投げて「おもて」なら、相手と相手の控えポケモン全員から、それぞれエネルギーカードを 1 枚ずつ選び、トラッシュする（v0.31。カスミのゴルダック
    の「スーパーデストロイ」）。選ぶのはワザを使ったプレイヤー。"""

    implementation_id = "coin_discard_opponent_energy_each"
    opponent_effect_elements = (ENERGY_DISCARD_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "相手のエネルギーをトラッシュするワザ", damage="none")

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        return opponent_energy_decision_problems(state, use, decision)


def opponent_energy_decision_problems(state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
    """相手のポケモンのエネルギーカードをトラッシュする決定の確かめ（v0.31）。"""
    found = state.find_pokemon(decision.context_value("target"))
    if found is None or found[0] != 1 - use.player:
        return [f"エネルギーをトラッシュする相手のポケモン {decision.context_value('target')!r} が、相手の場にいない"]
    target = found[1]
    return _decision_form(decision, _label(state, use), kind=DISCARD_OPPONENT_ENERGY, player=use.player, choices=(1, 1),
                          options=_attached_energy_cards(state, target, None))


@dataclass(frozen=True)
class AttachDiscardEnergyToSelf(AttackEffect):
    """自分のトラッシュに ``energy_type`` エネルギーカードがあれば、最大 ``max_cards`` 枚を取り出して、自分につける（v0.31。マチスのエレブーの「たいでん」）。"""

    energy_type: EnergyType
    max_cards: int
    implementation_id = "attach_discard_energy_to_self"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "トラッシュのエネルギーを自分につけるワザ", damage="none")

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        candidates = [uid for uid in state.players[use.player].discard
                      if state.card_def(uid).is_basic_energy and state.card_def(uid).provides is self.energy_type]
        return _decision_form(decision, _label(state, use), kind=ATTACH_FROM_DISCARD, player=use.player,
                              choices=(0, min(self.max_cards, len(candidates))), options=candidates)


@dataclass(frozen=True)
class DiscardAllThenCoinDamage(AttackEffect):
    """自分についている ``energy_type`` エネルギーカードを、すべてトラッシュする。その後、トラッシュした枚数だけコインを投げ、「おもて」の数 × ``per`` の
    ダメージ（v0.31。マチスのエレブーの「ほうでん」）。印刷の文面がワザの効果の形なので、時点の問いはない。"""

    energy_type: EnergyType
    per: int
    implementation_id = "discard_all_then_coin_damage"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "エネルギーをすべてトラッシュしてコインの数のダメージのワザ", damage="modified", modifier="×",
                           cost_types=(self.energy_type,))


@dataclass(frozen=True)
class DamageThenDiscardEachEnergy(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。自分と相手についているエネルギーカードを 1 枚ずつ選び、それぞれトラッシュする（v0.31。
    カツラのヒトカゲの「メラメラ」。選ぶのはワザを使ったプレイヤー。自分 → 相手の順）。"""

    implementation_id = "damage_then_discard_each_energy"
    opponent_effect_elements = (ENERGY_DISCARD_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "自分と相手のエネルギーをトラッシュするワザ", damage="fixed")

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        if decision.kind == DISCARD_OPPONENT_ENERGY:
            return opponent_energy_decision_problems(state, use, decision)
        _, attacker = state.find_pokemon(use.pokemon_id)
        return _decision_form(decision, _label(state, use), kind=DISCARD_ENERGY, player=use.player, choices=(1, 1),
                              options=_attached_energy_cards(state, attacker, None))


@dataclass(frozen=True)
class CoinsDiscardThenSpreadDamage(AttackEffect):
    """コインを ``coins`` 枚投げ、「おもて」の数ぶんの ``energy_type`` エネルギーカードを、自分からトラッシュする。トラッシュできない時、このワザは失敗する。
    相手と相手の控えポケモン全員に、「おもて」の数 × ``per`` のダメージを、「弱点・抵抗力」に関係なく、それぞれ与える（v0.31。カツラのリザードの
    「やきはらう」）。"""

    energy_type: EnergyType
    coins: int
    per: int
    implementation_id = "coins_discard_then_spread_damage"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "コインの数のトラッシュと全員へのダメージのワザ", damage="none", cost_types=(self.energy_type,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        _, attacker = state.find_pokemon(use.pokemon_id)
        count = decision.min_choices
        return _decision_form(decision, _label(state, use), kind=DISCARD_ENERGY, player=use.player, choices=(count, count),
                              options=attached_basic_energy(state, attacker, self.energy_type)) + (
            [] if 1 <= count <= self.coins else [f"トラッシュする数 {count} が正しくない"])


@dataclass(frozen=True)
class CoinBonusDamage(AttackEffect):
    """コインを投げて「おもて」なら、``bonus`` ダメージを追加する（v0.31。カツラのブーバーの「ひをふく」・イーブイとマチスのピカチュウの「でんこうせっか」）。"""

    bonus: int
    implementation_id = "coin_bonus_damage"

    def check(self, attack: Attack) -> list[str]:
        # v0.34: 説明の追加ダメージの数と登録の ``bonus`` を照らす（「…20ダメージを追加する。」「…20ダメージ追加する。」の 2 つの書き方。v0.31 の登録も同じ）
        problems = _check_form(attack, "コインで追加ダメージのワザ", damage="modified", modifier="+")
        if re.fullmatch(f"コインを投げて「おもて」なら、{self.bonus}ダメージを?追加する。", attack.text_ja or "") is None:
            problems.append(f"説明 {attack.text_ja!r} が、コインの「おもて」で {self.bonus} ダメージを追加するワザの説明ではない")
        return problems


@dataclass(frozen=True)
class MillSelfThenDamage(AttackEffect):
    """自分の山札の上から、カードを ``count`` 枚トラッシュする。トラッシュした中にあった ``energy_type`` エネルギーカードの数 × ``per`` のダメージ（v0.31。
    カツラのブーバーの「マグマふんしゅつ」）。山札が足りないときは決められない（HC6）。"""

    count: int
    energy_type: EnergyType
    per: int
    implementation_id = "mill_self_then_damage"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "山札をトラッシュしてダメージのワザ", damage="modified", modifier="×")


@dataclass(frozen=True)
class CoinBonusDamageThenDiscardAll(AttackEffect):
    """コインを投げて「おもて」なら、``bonus`` ダメージを追加して、自分についている ``energy_type`` エネルギーカードを、すべてトラッシュする（v0.31。
    マチスのライチュウの「バリバリ」）。"""

    energy_type: EnergyType
    bonus: int
    implementation_id = "coin_bonus_damage_then_discard_all"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "コインで追加ダメージとトラッシュのワザ", damage="modified", modifier="+", cost_types=(self.energy_type,))


@dataclass(frozen=True)
class DamageThenParalyzeOrSelfDamage(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、相手を「マヒ」状態にする。「うら」なら自分にも
    ``self_damage`` ダメージ（v0.31。マチスのライチュウの「でんきタックル」）。"""

    self_damage: int
    implementation_id = "damage_then_paralyze_or_self_damage"
    opponent_effect_elements = (PARALYSIS,)

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "コインでマヒか自分へのダメージのワザ", damage="fixed")


@dataclass(frozen=True)
class DrawCardsAttack(AttackEffect):
    """山札からカードを ``count`` 枚引く（v0.31。第4弾のコダックの「めまい」）。"""

    count: int
    implementation_id = "draw_cards_attack"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "山札から引くワザ", damage="none")


@dataclass(frozen=True)
class ExtraEnergyDamageMixed(AttackEffect):
    """``ExtraEnergyDamage``（v0.6）と同じ文面で、必要なエネルギーに無色がまざるワザ（v0.31。第4弾のコダックの「みずでっぽう」。多いエネルギーの数を
    決められない場合は HC4）。

    v0.37: 説明の文面も確かめる（v0.36 までは形だけ）。受け付けるのは、登録済みの 2 つの書き方（第4弾のコダック・第2弾のシャワーズ）と、第1弾の
    ニョロボンの書き方（第1弾のカメックスの「ハイドロポンプ」・ニョロモの「みずでっぽう」と同じ印刷の文面。kyuura の LD-PMCG1-032-ATK0 が
    「必要な分より多いエネルギー1つにつき」の意味とする書き方）だけ（``extra_energy_damage_texts``）。"""

    energy_type: EnergyType
    per_energy: int
    max_extra: int
    implementation_id = "extra_energy_damage_mixed"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "多いエネルギーで追加ダメージのワザ", damage="modified", modifier="+", cost_types=(self.energy_type,))
        if EnergyType.COLORLESS not in attack.cost:
            problems.append("必要なエネルギーに無色がないワザ（ExtraEnergyDamage で登録する）")
        texts = extra_energy_damage_texts(self.energy_type, self.per_energy, self.max_extra)
        return problems + _check_exact_text(attack, "必要な分より多いエネルギーでダメージを追加する効果", texts)


def extra_energy_damage_texts(energy_type: EnergyType, per_energy: int, max_extra: int) -> tuple[str, ...]:
    """``ExtraEnergyDamageMixed`` が受け付ける説明の書き方（v0.37）。"""
    t, n, m = energy_type.ja, per_energy, max_extra
    return (f"ワザに必要なエネルギーよりも多く「{t}」エネルギーがついている時、多い「{t}」エネルギー1つにつき、{n}ダメージを追加する。(ダメージ追加は{m}つぶんまで)",  # 第4弾のコダック
            f"このワザに必要な分よりも多く「{t}」エネルギーがついている時、多いエネルギー1つにつき{n}ダメージを追加する。(ダメージ追加は{m}つぶんまで)",  # 第2弾のシャワーズ
            f"「{t}」エネルギーを1つ追加すると、{n}ダメージ追加できる。(追加は{m}つまで)",  # 第1弾のニョロボン（カメックス・ニョロモと同じ印刷の文面）
            # v0.41: 第3弾のシードラ（第2弾のシャワーズと同じ書き方で、「このワザに必要な分」を「ワザに必要なぶん」、「エネルギー」を「エネルギーカード」、括弧を
            # 全角で書く。今の写しに特殊エネルギーはなく、基本エネルギーカード 1 枚がエネルギー 1 つなので、数え方は同じ）
            f"ワザに必要なぶんよりも多く「{t}」エネルギーカードがついている時、多いエネルギー1つにつき{n}ダメージを追加する。（ダメージ追加は{m}つぶんまで）",
            # v0.47: 第3弾のオムスター（第3弾のシードラと同じ書き方で、括弧が半角。意味は同じ）
            f"ワザに必要なぶんよりも多く「{t}」エネルギーカードがついている時、多いエネルギー1つにつき{n}ダメージを追加する。(ダメージ追加は{m}つぶんまで)")


@dataclass(frozen=True)
class ThreeCoinPsychicPower(AttackEffect):
    """コインを 3 枚投げる。「おもて」が 1 枚なら、山札の上からカードを 1 枚引いて、手札に加える。2 枚なら、相手に 20 ダメージ。3 枚なら相手のワザを
    1 つ選び、それを、自分が持っているワザとして使う（そのワザに必要なエネルギーがついていなくても、かまわない）（v0.31。カスミのコダックの
    「ちょうのうりょく」）。0 枚なら何もしない。"""

    implementation_id = "three_coin_psychic_power"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "コインの数で効果が変わるワザ", damage="none")

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        return copy_decision_problems(state, use, decision)


@dataclass(frozen=True)
class CannotAttackOnHeads(AttackEffect):
    """コインを投げて「おもて」なら、このワザを受けた相手の対戦ポケモンは、次の相手の番にワザを使えない（v0.31。イーブイの「しっぽをふる」。相手に与える
    持続する効果 ``CannotAttack``）。"""

    implementation_id = "cannot_attack_on_heads"
    opponent_effect_elements = (ATTACK_LOCK_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "コインで相手がワザを使えなくなるワザ", damage="none")
        return problems + _check_exact_text(attack, "コインの「おもて」で次の相手の番に相手がワザを使えなくなる効果", cannot_attack_on_heads_texts(attack.name_ja))


def cannot_attack_on_heads_texts(name: str) -> tuple[str, ...]:
    """``CannotAttackOnHeads`` が受け付ける説明の書き方（v0.37。v0.36 までは形だけを確かめていた）。イーブイの「しっぽをふる」・サイホーンの
    「にらみつける」の書き方（「」の中はそのワザ自身の名前）と、ナツメのスリープの「あんじをかける」の書き方（「このワザを受けた相手」= このワザを受けた
    相手の対戦ポケモン）。ほかの書き方（期限・対象・コインの違うもの）は受け付けない。"""
    return (f"コインを投げて「おもて」なら「{name}」を受けた相手の対戦ポケモンは、次の相手の番にワザをつかえない。",
            "コインを投げて「おもて」なら、次の相手の番、このワザを受けた相手は、ワザを使えない。")


@dataclass(frozen=True)
class DamageAndBenchTypeDamage(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。相手のベンチにいる ``pokemon_type`` ポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ
    ``bench_damage`` ダメージ（v0.31。カツラのガーディの「もえひろがる」）。"""

    pokemon_type: EnergyType
    bench_damage: int
    implementation_id = "damage_and_bench_type_damage"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "控えのポケモンにもダメージを与えるワザ", damage="fixed")


# ---------------------------------------------------------------- v0.32: 山札からベンチに出す・ダメージカウンターでダメージが決まる・与えたぶん回復する
# （docs/bench-search-counter-drain-v0.32.md）。処理は解決の基盤の要素の並び（resolution/programs.py の BUILDERS）。処理に使う文面は kyuura の印刷の文面。


def bench_from_deck_candidates(state: GameState, player: int, names: tuple[str, ...], pokemon_type: EnergyType | None = None) -> list[int]:
    """``player`` の山札のカードのうち、名前（``name_ja``）が ``names`` のどれかと同じたねポケモン（v0.32。uid の小さい順。山札の並びを写さない）。
    同じ名前の別のカード（第2弾のナゾノクサと第4弾のナゾノクサなど）は、どれも選べる（説明は名前で指す）。v0.34: ``pokemon_type`` なら、名前でなく
    そのタイプのたねポケモン（ガラガラの「たすけをよぶ」。進化カードは選べない）。"""
    def matches(definition) -> bool:
        return definition.pokemon_type is pokemon_type if pokemon_type is not None else definition.name_ja in names

    return sorted(uid for uid in state.players[player].deck
                  if state.card_def(uid).is_basic_pokemon and matches(state.card_def(uid)))


@dataclass(frozen=True)
class PutBasicFromDeckOntoBench(AttackEffect):
    """自分の山札から、名前が ``names`` のどれかのたねポケモンを 1 匹さがしてベンチに出す。その後、その山札をよく切る。自分のベンチに空きがなければ、
    このワザは使えない（v0.32。ニドラン♀・マダツボミ・クラブの「なかまをよぶ」、ナゾノクサの「ふえる」）。

    - ベンチに空きがないことは、ワザを使うための条件（``usage_problem``。必要なエネルギーの確認のあと・こんらんのコインの前。``BENCH_FULL``）
    - 選ぶのはワザを使ったプレイヤー（決定 ``BENCH_FROM_DECK``。1 匹。省略できない）。選べるものは ``bench_from_deck_candidates``
    - 山札に選べるものがない（山札が 0 枚を含む）: 処理の対象がないので出さない（p.309。H5・ゴミあさりと同じ読み方）。そのあと山札を切る
    - 出したカードは手札を通らない（``zones.bench_from_deck``）。場に出た番は今の番（p.310 の進化の制限は手札から出したときと同じ）
    """

    names: tuple[str, ...]
    implementation_id = "put_basic_from_deck_onto_bench"

    def __post_init__(self) -> None:
        if type(self.names) is not tuple or not self.names or not all(type(name) is str and name for name in self.names):
            raise ValueError(f"さがすポケモンの名前は 1 つ以上の文字列のタプル（{self.names!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "山札からベンチに出すワザ", damage="none")
        text = attack.text_ja or ""
        first = text.split("。")[0]
        quoted = tuple(re.findall(r"「([^」]+)」", first))
        if quoted != self.names or "を1匹さがしてベンチに" not in first or not first.startswith("自分の山札から"):
            problems.append(f"説明の「自分の山札から「…」を1匹さがしてベンチに出す」の名前 {quoted} が、登録の名前 {self.names} と合わない")
        if "その山札をよくきる" not in text:
            problems.append("説明に「その山札をよくきる」がない")
        if "自分のベンチに空きがなければ" not in text or "使えない" not in text:
            problems.append("説明に「自分のベンチに空きがなければ…使えない」がない")
        return problems

    def usage_problem(self, state: GameState, attacker: PokemonInPlay) -> IllegalActionError | None:
        owner, _ = state.find_pokemon(attacker.pokemon_id)
        if len(state.players[owner].bench) >= state.rules.max_bench:
            return IllegalActionError("BENCH_FULL", f"自分のベンチに空きがない（{state.rules.max_bench} 匹）ので、このワザは使えない（ワザの説明）")
        return None

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        return _decision_form(decision, _label(state, use), kind=BENCH_FROM_DECK, player=use.player, choices=(1, 1),
                              options=bench_from_deck_candidates(state, use.player, self.names))


@dataclass(frozen=True)
class DamageTimesOwnCounters(AttackEffect):
    """自分にのっているダメージカウンターの数 × ``per`` のダメージ（v0.32。コイキング・キングラーの「じたばた」。ダメージの目安「10×」）。これが
    p.321 の 1 段階（基本となるダメージ）。0 個なら 0 で、2 段階までで 0 以下なのでダメージを与えない（p.321。サカキのワンリキーの「いかりのスーパー
    パンチ」の「おもて」と同じ数え方で、コインがない）。数えるのはダメージの要素を処理する時点のカウンター（進化前からのっているものを含む）。"""

    per: int
    implementation_id = "damage_times_own_counters"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "自分のダメージカウンターの数でダメージが決まるワザ", damage="modified", modifier="×")
        if attack.damage != self.per:
            problems.append(f"ダメージの目安の数字 {attack.damage} が、登録のカウンター 1 個あたりのダメージ {self.per} と違う")
        return problems


def attached_energy_cards(state: GameState, pokemon: PokemonInPlay) -> int:
    """場のポケモン ``pokemon`` についているエネルギーカードの枚数（v0.50。ミュウツーの「サイコキネシス」（v0.31）とミュウの「サイコウェーブ」で共通の数え方）。
    数えるのはカードの枚数で、供給するエネルギーの個数・色（``state.energy_types``。エナジーバーン・［へんしん］の「どの色としても」）ではない。"""
    return sum(1 for uid in pokemon.energy if state.card_def(uid).category == "energy")


@dataclass(frozen=True)
class DamageTimesDefenderEnergyCards(AttackEffect):
    """相手の対戦ポケモンについているエネルギーカードの枚数 × ``per`` のダメージ（v0.50。ミュウの「サイコウェーブ」。ダメージの目安「10×」。kyuura の印刷の文面
    「相手についているエネルギーカード×10のダメージ。」）。

    これが p.321 の 1 段階（基本となるダメージ）。ミュウツーの「サイコキネシス」（``DamagePlusDefenderEnergy``。目安の数字に枚数 × 10 を加える。「10+」）とは違い、
    枚数 × 10 そのものが基本となるダメージ（「×」）。数えるのはダメージの要素を処理する時点のカードの枚数（``attached_energy_cards``。供給するエネルギーの個数・色では
    ない）。0 枚なら 0 で、2 段階までで 0 以下なのでダメージを与えない（弱点・抵抗力・プラスパワーを計算しない。v0.32 の「じたばた」と同じ。p.321）。"""

    per: int
    implementation_id = "damage_times_defender_energy_cards"

    def check(self, attack: Attack) -> list[str]:
        what = "相手のエネルギーカードの枚数でダメージが決まるワザ"
        problems = _check_form(attack, what, damage="modified", modifier="×")
        if attack.damage != self.per:
            problems.append(f"ダメージの目安の数字 {attack.damage} が、登録のエネルギーカード 1 枚あたりのダメージ {self.per} と違う")
        return problems + _check_exact_text(attack, what, (f"相手についているエネルギーカード×{self.per}のダメージ。",))


@dataclass(frozen=True)
class DamagePlusDefenderCounters(AttackEffect):
    """ダメージの目安の数字 +「相手のポケモンにのっているダメージカウンター」× ``per`` の追加ダメージ（v0.32。ルージュラの「ヨガのポーズ」。ダメージの
    目安「20+」）。数えるのはダメージを受ける相手の対戦ポケモンのカウンター。「相手のポケモン」が相手の場のポケモンすべてを指すかは決められないので、
    相手の控えポケモンにダメージカウンターがのっていて読み方で答えが変わるときだけ止める（CD4。``UNRESOLVED_OPPONENT_POKEMON_COUNTERS``）。"""

    per: int
    # v0.46: 説明が「相手のポケモンにのっている」（ルージュラ。CD4 の読み方の問いがある）なら True、「相手にのっている」（バリヤードの「ヨガのポーズ」。「相手」は相手の
    # 対戦ポケモン。p.320。CD4 に当たらない）なら False
    scope_ambiguous: bool = True
    implementation_id = "damage_plus_defender_counters"

    def check(self, attack: Attack) -> list[str]:
        whom = "相手のポケモン" if self.scope_ambiguous else "相手"
        return _check_form(attack, "相手のダメージカウンターで追加ダメージのワザ", damage="modified", modifier="+") + _check_exact_text(
            attack, "相手のダメージカウンターで追加ダメージのワザ", (f"{whom}にのっているダメージカウンター×{self.per}のダメージを追加する。",))


@dataclass(frozen=True)
class DamageAndFullDrain(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。相手にダメージを与えたら、与えたぶんのダメージカウンターを自分からとりのぞく（v0.32。
    コンパン・ズバット（化石の秘密）・ゴルバットの「きゅうけつ」）。メガドレイン（``DamageAndDrain``。半分の切り上げ）と同じ要素 ``programs.Drain`` で、
    とりのぞく数だけが違う（与えたダメージ ÷ 10 個。のっている数まで）。「与えたダメージ」は最終ダメージ（p.319・p.321。v0.4d）。ダメージを与えなかったら
    とりのぞかない（「ダメージを与えたら」。Z23 の「ダメージを与えた後、…」とは別）。ログはメガドレインと同じ ``drain_heal``。"""

    implementation_id = "damage_and_full_drain"

    def check(self, attack: Attack) -> list[str]:
        return _check_damage_then_effect(attack, "与えたぶんのダメージカウンターをとりのぞく")


# ---------------------------------------------------------------- v0.33: 相手のエネルギーカードをトラッシュする・コインで失敗する／ダメージを与えられない・
# 控えポケモンにもダメージを与えるワザ（docs/cd4-opponent-energy-coins-v0.33.md）。処理は解決の基盤の要素の並び（resolution/programs.py の BUILDERS）。
# 処理に使う文面は kyuura の印刷の文面（15 枚とも kyuura に最新の説明・エラッタ・裁定の記録がない）。


@dataclass(frozen=True)
class DamageThenDiscardOpponentEnergy(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。そのあと（``on_heads`` ならコインを投げて「おもて」なら）、相手の対戦ポケモンについている
    エネルギーカードを 1 枚選び、トラッシュする（v0.33。ハクリュー・ゴルダックの「はかいこうせん」、わるいシャワーズの「うずしお」、マチスのコイルの
    「はかいでんぱ」・ナツメのコンパンの「はかいビーム」（``on_heads``））。

    - 選ぶのはワザを使ったプレイヤー（v0.31 のメラメラ・スーパーデストロイと同じ要素 ``programs.DiscardOpponentEnergy`` と決定 ``discard_opponent_energy``）。
      選べるのはエネルギーカード（基本・特殊を分けない）。トラッシュするのは相手のトラッシュ
    - ダメージ → トラッシュ（p.309 の手順 6）。トラッシュはダメージ以外の効果なので、「ダメージを受けない」状態の相手でもトラッシュする（p.321）。ダメージで
      相手が HP 以上になったら、処理の対象がいないのでトラッシュしない（コインも投げない。p.309・kyuura の CR-EFFECTS-AFTER-KO）
    - 相手の対戦ポケモンにエネルギーカードがついていなければ、処理の対象がないのでトラッシュしない（ゴルダックの説明「…ついていない時には、この効果は
      ない。」。ほかの 4 つのワザも p.309）。``on_heads`` でも、そのときコインは投げない（v0.31 のスーパーデストロイと同じ）
    """

    on_heads: bool = False
    implementation_id = "damage_then_discard_opponent_energy"
    opponent_effect_elements = (ENERGY_DISCARD_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        problems = _check_damage_then_effect(attack, "相手のエネルギーカードをトラッシュする")
        text = attack.text_ja or ""
        if ("コインを投げて「おもて」なら" in text) != self.on_heads:
            problems.append(f"説明のコインの有無と、登録の on_heads={self.on_heads} が合わない")
        if "エネルギーカードを1枚" not in text or "相手" not in text:
            problems.append("説明に「相手の…エネルギーカードを1枚」がない")
        return problems

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        return opponent_energy_decision_problems(state, use, decision)


@dataclass(frozen=True)
class NoDamageOnTails(AttackEffect):
    """コインを投げて「うら」なら、相手にダメージを与えることができない（v0.33。ニドラン♂の「つのでつつく」）。「おもて」ならダメージの目安の数字ぶんの
    ダメージ。

    - 「うら」はワザの「失敗」（p.323「12 ワザの失敗」）ではない。説明に「失敗」と書かれていない（v0.2d の ``CoinFlipDamage``・kyuura の
      CR-TRANSPARENCY-NOT-FAILURE と同じ読み方）。ワザは使ったことになり、ダメージの要素がないだけ（ログ ``attack_failed`` を残さない）
    - コインはダメージの要素だけを決めるので、相手の対戦ポケモンが「ダメージを受けない」状態なら、コインを投げるかが決められない（v0.4b の
      ``UNRESOLVED_PREVENTED_COIN_DAMAGE``。kyuura の UQ-COIN-IN-NULLIFIED-ELEMENT）。コインの前に止める
    """

    implementation_id = "no_damage_on_tails"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "コインの「うら」でダメージを与えられないワザ", damage="fixed")
        if attack.text_ja != "コインを投げて「うら」なら、相手にダメージをあたえることができない。":
            problems.append(f"説明 {attack.text_ja!r} が「コインを投げて「うら」なら、相手にダメージをあたえることができない。」ではない")
        return problems


@dataclass(frozen=True)
class DamageAndParalyzeOnHeadsElseFail(AttackEffect):
    """コインを投げて「おもて」なら、ダメージの目安の数字ぶんのダメージとともに相手をマヒ状態にする。「うら」なら、このワザは失敗する（v0.33。パルシェンの
    「からではさむ」）。

    - コインは 1 枚で、ダメージ・マヒ・失敗をまとめて決める（ワザ全体のコイン。マヒのために投げ直さない）。「うら」はワザの失敗（p.323。ログ
      ``attack_failed``）で、ダメージもマヒもない
    - マヒの再付与で回復する番が変わる場合は、コインの前に止める（v0.3b の ``UNRESOLVED_REPARALYSIS_RECOVERY_TURN``。ねばりつくと同じ）
    - 「ダメージを受けない」状態（かたまる）の相手には、ダメージだけが無効で、マヒは有効なので、コインを投げる（kyuura の CR-STICKY-VS-PREVENTED と同じ形）。
      「ワザをうけない」状態（バリアー）の相手には、コインが決めるダメージとマヒがどちらも無効なので、コインを投げるかが決められない（HC3
      ``UNRESOLVED_PREVENTED_EFFECT_COIN``）
    - ダメージで相手が HP 以上になったら、マヒにしない（p.309・CR-EFFECTS-AFTER-KO）
    """

    implementation_id = "damage_and_paralyze_on_heads_else_fail"
    opponent_effect_elements = (PARALYSIS,)

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "コインでダメージとマヒ・失敗が決まるワザ", damage="fixed")
        if attack.text_ja != "コインを投げて「おもて」なら、ダメージとともに相手を「マヒ」状態にする。「うら」なら、このワザは失敗する。":
            problems.append(f"説明 {attack.text_ja!r} が、コイン 1 枚でダメージとマヒ・失敗が決まるワザの説明ではない")
        return problems


@dataclass(frozen=True)
class DamageAndOwnBenchDamage(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。自分の控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ ``bench_damage`` ダメージ
    （v0.33。タケシのディグダの「ミニじしん」）。

    - p.320 のダメージの (4)（このワザを使うポケモンの控えへのダメージ）。受けるのは自分のベンチの全員（並びの順。選ばない）。ワザを使うポケモン自身は
      含まない。コインはない
    - 計算: 弱点・抵抗力は計算しない（説明）。プラスパワーは変えない（p.257 の最新の説明「(控えポケモンへのダメージは、そのまま)」）。受けるポケモンに
      ついているディフェンダーは変える（docs/defender-v0.2e.md の 13・16）
    - 自分のワザのダメージなので、受けたポケモンの「はんげき」・こんじょうなどの「相手のワザによって」の効果ははたらかない。「とうめい」は評価する
      （v0.9 の T8。自分のワザでもはたらく）。きぜつしたら、相手がサイドを取る（p.323）
    - v0.37: ``weakness_resistance_stated`` が False なら、説明に「「弱点・抵抗力」に関係なく」がないワザ（第1弾のダグトリオの「じしん」。説明
      「自分の控えポケモン全員にも10ダメージ。」）。控えポケモンへのダメージに弱点・抵抗力を計算するかは、2000.02.14 版の記録では決まらない（JS1。
      kyuura の rule_history.json の ``bench_weakness`` は第2版の時期の会報と第4版の冊子の記録だけ）。読み方で控えのポケモンの受けるダメージが変わる
      とき（控えに、ワザを使うポケモンのタイプに弱点・抵抗力を持つポケモンがいる）だけ、問い ``bench_damage_weakness_resistance``
      （``UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE``）で止める。変わらなければ同じ処理（``programs.BenchDamage`` の ``weakness_resistance`` が None）
    """

    bench_damage: int
    weakness_resistance_stated: bool = True
    implementation_id = "damage_and_own_bench_damage"

    def __post_init__(self) -> None:
        if type(self.bench_damage) is not int or self.bench_damage <= 0 or self.bench_damage % 10:
            raise ValueError(f"控えポケモンへのダメージは 10 の倍数の正の数（{self.bench_damage!r}）")
        if type(self.weakness_resistance_stated) is not bool:
            raise ValueError(f"説明に「弱点・抵抗力」に関係なくがあるかは真偽値（{self.weakness_resistance_stated!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "自分の控えにもダメージを与えるワザ", damage="fixed")
        if self.weakness_resistance_stated:
            expected = f"自分の控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ{self.bench_damage}ダメージ。"
        else:
            expected = f"自分の控えポケモン全員にも{self.bench_damage}ダメージ。"
        if attack.text_ja != expected:
            problems.append(f"説明 {attack.text_ja!r} が {expected!r} ではない")
        return problems


@dataclass(frozen=True)
class DamageThenCoinBenchDamage(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、相手の控えポケモンを 1 匹選び、そのポケモンにも、「弱点・
    抵抗力」に関係なく、``bench_damage`` ダメージ（v0.33。カツラのサイホーンの「かけぬける」）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。1 匹。控えが 1 匹でも出す。わるいギャロップの「ひばしら」と同じ形）
    - 順番: 相手の対戦ポケモンへのダメージ → コイン → 選ぶ → 控えへのダメージ（説明の順。どちらもダメージの要素）。相手の対戦ポケモンがきぜつしても、
      控えへのダメージは処理する（対象が違う。p.309）
    - 相手に控えポケモンがいなければ、処理の対象がないので、コインを投げない（p.309。v0.31 のスーパーデストロイ・はかいでんぱと同じ読み方）
    - 計算はタケシのディグダの「ミニじしん」と同じ（弱点・抵抗力なし・プラスパワーは変えない・ディフェンダーは変える）
    - 相手の対戦ポケモンへのダメージで「ダメージを受けたとき」の効果（はんげき・ほのおのかべ・こうらがえしなど）がはたらいたあとに控えを選ぶ場面は、
      v0.33 ではエンジンの未対応（``UNSUPPORTED_DECISION_AFTER_DAMAGE_TRIGGER``）だった。v0.34 から、その効果を決定をまたいで運び（続きの情報の
      ``frame`` の ``pending``）、控えへのダメージのあと（ダメージの要素がすべて終わったあと。p.89）に処理する
    """

    bench_damage: int
    implementation_id = "damage_then_coin_bench_damage"

    def __post_init__(self) -> None:
        if type(self.bench_damage) is not int or self.bench_damage <= 0 or self.bench_damage % 10:
            raise ValueError(f"控えポケモンへのダメージは 10 の倍数の正の数（{self.bench_damage!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "コインで相手の控えにもダメージを与えるワザ", damage="fixed")
        expected = f"コインを投げて「おもて」なら、相手の控えポケモンを1匹選び、そのポケモンにも、「弱点・抵抗力」に関係なく、{self.bench_damage}ダメージ。"
        if attack.text_ja != expected:
            problems.append(f"説明 {attack.text_ja!r} が {expected!r} ではない")
        return problems

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        bench = state.players[1 - use.player].bench
        return _decision_form(decision, _label(state, use), kind=SELECT_POKEMON, player=use.player, choices=(1, 1), options=(p.pokemon_id for p in bench))


# ---------------------------------------------------------------- v0.34: コインによる追加ダメージと付随効果・特殊状態の分岐・特殊などく・可変枚数のコイン・
# 持続する軽減・山札からタイプでベンチへ（docs/barrier-resume-coin-bonus-v0.34.md）


@dataclass(frozen=True)
class CoinBonusOrSelfDamage(AttackEffect):
    """コインを投げて「おもて」なら相手に ``bonus`` ダメージを追加し、「うら」なら自分にも ``self_damage`` ダメージ（v0.34。エレブーの「かみなりパンチ」・
    ニドキングの「あばれる」）。

    - コインは 1 枚で、追加ダメージと自分へのダメージをまとめて決める（ワザ全体のコイン。要素ごとに投げ直さない）。ダメージの量がコインで決まるので、
      コインはダメージの計算の前（kyuura の CR-STICKY-DAMAGE と同じ形）
    - 「おもて」: 相手に目安 + ``bonus``（p.321 の 1 段階）。「うら」: 相手に目安、そのあと自分に ``self_damage``（自分へのダメージの弱点・抵抗力は、
      ワザを使うポケモンのタイプと自分の弱点・抵抗力で計算する。v0.3d）
    - コインが決める要素に自分へのダメージ（無効にならない）があるので、「ダメージを受けない」「ワザをうけない」状態の相手にもコインを投げる
      （``programs.void_coin_question``）
    """

    bonus: int
    self_damage: int
    implementation_id = "coin_bonus_or_self_damage"

    def __post_init__(self) -> None:
        for value in (self.bonus, self.self_damage):
            if type(value) is not int or value <= 0 or value % 10:
                raise ValueError(f"追加・自分へのダメージは 10 の倍数の正の数（{value!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "コインで追加ダメージか自分へのダメージのワザ", damage="modified", modifier="+")
        accepted = (
            f"コインを投げて「おもて」なら、相手に{self.bonus}ダメージを追加する。「うら」なら自分にも{self.self_damage}ダメージ。",
            f"コインを投げて「おもて」なら相手に追加{self.bonus}ダメージ、「うら」なら自分に{self.self_damage}ダメージ。",
        )
        if attack.text_ja not in accepted:
            problems.append(f"説明 {attack.text_ja!r} が、コイン 1 枚で追加ダメージか自分へのダメージが決まるワザの説明ではない")
        return problems


@dataclass(frozen=True)
class DamageThenSelfBarrierOnHeads(AttackEffect):
    """相手にダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、このカードは次の相手の番にワザをうけない（v0.34。ギャロップの「こうそくいどう」）。

    - 効果は v0.31 のミュウツーの「バリアー」（「次の相手の番の「ワザ」をうけない。」）と同じ持続する効果 ``AttackBarrier``（自分自身に与え、次の相手の番に、
      このポケモンへのワザのダメージの要素と効果の要素は無効）。期限・消える条件もバリアーと同じ（次の相手の番の終わり・ベンチにもどる・進化・きぜつ）
    - コインはダメージのあと（説明の順）。自分への効果なので、相手がダメージを受けない状態でも投げる
    - ワザを使ったポケモンが相手の「はんげき」などで HP 以上になったら、処理の対象がいないので、コインを投げず効果も与えない（p.309）
    - v0.37: 第1弾のライチュウの「こうそくいどう」の説明「コインを投げて「おもて」なら、次の相手の番の「ワザ」をうけない。」も受け付ける（主語の
      「このカードは」がない。v0.31 のミュウツーの「バリアー」の「次の相手の番の「ワザ」をうけない。」と同じ書き方で、自分自身に与える効果。p.322 の
      「まるまる」のようなワザ）。ほかの書き方は受け付けない（``SELF_BARRIER_ON_HEADS_TEXTS``）
    """

    implementation_id = "damage_then_self_barrier_on_heads"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "コインで次の相手の番にワザをうけなくなるワザ", damage="fixed")
        if attack.text_ja not in SELF_BARRIER_ON_HEADS_TEXTS:
            problems.append(f"説明 {attack.text_ja!r} が、コインの「おもて」で次の相手の番にワザをうけないワザの説明ではない")
        return problems


# v0.34・v0.37: ``DamageThenSelfBarrierOnHeads`` が受け付ける説明（kyuura の印刷の文面）。ギャロップ（v0.34）と、主語の「このカードは」を書かない
# 第1弾のライチュウ（v0.37。ミュウツーの「バリアー」と同じ書き方）。docs/fifteen-reused-effects-v0.37.md 3 章
SELF_BARRIER_ON_HEADS_TEXTS = (
    "コインを投げて「おもて」なら、このカードは次の相手の番にワザをうけない。",
    "コインを投げて「おもて」なら、次の相手の番の「ワザ」をうけない。",
    # v0.41: 第3弾のシードラの「こうそくいどう」。「ワザによるダメージや効果を受けない」は、v0.37 のカスミのコイキングの「しんだふり」（``SelfBarrierOnHeads``）・
    # v0.38 のキョウのピジョンの「こうそくひこう」で ``AttackBarrier`` として登録した書き方と同じ（docs/heal-counter-status-v0.41.md 2 章）
    "コインを投げて「おもて」なら、このカードは次の相手の番に、ワザによるダメージや効果を受けない。",
)


@dataclass(frozen=True)
class DamagePlusOwnCountersThenSelfConfuseOnTails(AttackEffect):
    """ダメージの目安の数字 + 自分にのっているダメージカウンターの数 × ``per`` のダメージ（p.321 の 1 段階。v0.31 のわるいブースターの「いかり」と同じ数え方）。
    その後、コインを投げて「うら」なら、自分はこんらん状態になる（v0.34。ケンタロスの「いかりくるう」）。

    - 「その後」は説明の順（p.320 のワザの要素の順番）。たおれこむの「ダメージを与えた後」（Z23。ダメージを与えたことが条件か決められない）とは書き方が
      違い、ダメージを与えたことを条件にしない（相手がダメージを受けない状態でもコインを投げる）
    - こんらんになるのはワザを使ったポケモン自身（p.320 の効果の (3)）。そのポケモンが相手の「はんげき」などで HP 以上になったら、処理の対象がいないので、
      コインを投げずこんらんにもしない（p.309）
    """

    per: int
    implementation_id = "damage_plus_own_counters_then_self_confuse_on_tails"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "自分のダメージカウンターで追加ダメージ・コインで自分がこんらんのワザ", damage="modified", modifier="+")
        expected = f"自分にのっているダメージカウンター×{self.per}のダメージを追加する。その後、コインを投げて「うら」なら、【自分】は「こんらん」状態になる。"
        if attack.text_ja != expected:
            problems.append(f"説明 {attack.text_ja!r} が {expected!r} ではない")
        return problems


@dataclass(frozen=True)
class DamageThenCoinOwnBenchDamage(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「うら」なら、自分の控えポケモンを 1 匹選び、そのポケモンにも、「弱点・抵抗力」に
    関係なく、``bench_damage`` ダメージ（v0.34。サカキのカイロスの「うしろなげ」）。

    - v0.33 の「かけぬける」（``DamageThenCoinBenchDamage``）と同じ要素 ``ChosenBenchDamage`` の、自分の控え（``own``）・「うら」の形。選ぶのはワザを使った
      プレイヤー（決定 ``SELECT_POKEMON``。1 匹。控えが 1 匹でも出す）。自分に控えがいなければ、処理の対象がないのでコインを投げない（p.309）
    - 計算はタケシのディグダの「ミニじしん」と同じ（p.320 のダメージの (4)。弱点・抵抗力なし・プラスパワーは変えない・ディフェンダーは変える）。自分のワザの
      ダメージなので、受けた控えの「相手のワザによって」の効果ははたらかない
    - 相手の対戦ポケモンへのダメージで「ダメージを受けたとき」の効果がはたらいていれば、決定をまたいで運び、控えへのダメージのあとに処理する（v0.34）
    """

    bench_damage: int
    implementation_id = "damage_then_coin_own_bench_damage"

    def __post_init__(self) -> None:
        if type(self.bench_damage) is not int or self.bench_damage <= 0 or self.bench_damage % 10:
            raise ValueError(f"控えポケモンへのダメージは 10 の倍数の正の数（{self.bench_damage!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "コインで自分の控えにもダメージを与えるワザ", damage="fixed")
        expected = f"コインを投げて「うら」なら、自分の控えポケモンを1匹選び、そのポケモンにも、「弱点・抵抗力」に関係なく、{self.bench_damage}ダメージ。"
        if attack.text_ja != expected:
            problems.append(f"説明 {attack.text_ja!r} が {expected!r} ではない")
        return problems

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        bench = state.players[use.player].bench
        return _decision_form(decision, _label(state, use), kind=SELECT_POKEMON, player=use.player, choices=(1, 1), options=(p.pokemon_id for p in bench))


@dataclass(frozen=True)
class DamageThenPoisonOrConfuse(AttackEffect):
    """相手にダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら相手をどく状態、「うら」ならこんらん状態にする（v0.34。ドガースの「くさいガス」）。

    - コインは 1 枚で、どくかこんらんかを決める（要素 ``Status`` の ``otherwise``。投げ直さない）。コインはダメージのあと（説明の順）
    - どちらの結果も相手の対戦ポケモンへの効果なので、「ワザをうけない」状態（バリアー）の相手には、コインを投げるかが決められない（HC3）。前のダメージの要素の
      「とうめい」で受けないと決まったら T19b。ダメージで HP 以上になったら、コインを投げずどちらにもしない（p.309）
    - どくはほかの特殊状態と重複し、こんらんはねむり・マヒに置きかわる（p.322。既存の ``conditions.poison``・``confuse``）
    """

    implementation_id = "damage_then_poison_or_confuse"
    opponent_effect_elements = (POISON, CONFUSION)

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "コインでどくかこんらんになるワザ", damage="fixed")
        if attack.text_ja != "コインを投げて「おもて」なら、相手を「どく」状態、「うら」なら「こんらん」状態にする。":
            problems.append(f"説明 {attack.text_ja!r} が、コインでどくかこんらんにするワザの説明ではない")
        return problems


@dataclass(frozen=True)
class DamageAndSpecialPoison(AttackEffect):
    """相手にダメージの目安の数字ぶんのダメージ。相手を、ポケモンチェックごとに ``poison_damage`` の「どく」ダメージを受ける特殊などく状態にする（v0.34。
    ニドキングの「どくどく」「相手に「どく」カウンターを2個のせ、ポケモンチェックごとに20の「どく」ダメージ。」）。

    - 特殊などくは「どく状態にかかるもの」としてあつかう（p.322。docs/special-conditions-v0.3a.md の 13。CONFIRMED）ので、どく状態のダメージの量
      （``Poison.damage``）を 20 にする。通常のどくを 2 回付ける形にしない。どくはほかの特殊状態と重複する（p.322）
    - どく状態でないポケモン: 20 のどく状態。同じ 20 のどく状態のポケモン: 変わらない（どく状態は積み重ならない。p.322）
    - 通常のどく状態（10）のポケモン: p.322 は向きの逆（特殊などくのポケモンが通常のどくを受けたら通常のどくになる。v0.3a の 14）だけを書き、この向きは
      決められない（v0.3a の 15。UNRESOLVED）。宣言の前に ``UNRESOLVED_SPECIAL_POISON_OVERWRITE`` で止める
    - ダメージで HP 以上になったら、どく状態にしない（p.309）
    """

    poison_damage: int
    implementation_id = "damage_and_special_poison"
    opponent_effect_elements = (POISON,)

    def __post_init__(self) -> None:
        if type(self.poison_damage) is not int or self.poison_damage <= 10 or self.poison_damage % 10:
            raise ValueError(f"特殊などくのダメージは 10 の倍数で 10 より大きい（{self.poison_damage!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "相手を特殊などく状態にするワザ", damage="fixed")
        expected = f"相手に「どく」カウンターを{self.poison_damage // 10}個のせ、ポケモンチェックごとに{self.poison_damage}の「どく」ダメージ。"
        if attack.text_ja != expected:
            problems.append(f"説明 {attack.text_ja!r} が {expected!r} ではない")
        return problems


@dataclass(frozen=True)
class SwitchSelfWithBench(AttackEffect):
    """自分の控えポケモンを選び、このカード（ワザを使ったポケモン）と入れ替える（v0.34。ナッシーの「テレポート」）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。1 匹。控えが 1 匹でも出す）。入れ替えはポケモンいれかえと同じ処理
      （``_switch_active_with_bench``。にげるではない（p.325）。ベンチにもどったこのポケモンの特殊状態・持続する効果は消える。p.322）
    - 自分に控えがいなければ、処理の対象がないので入れ替えない（p.309。ワザは使ったことになり、番は終わる）
    - ダメージの要素はない（ダメージの目安がない）
    """

    implementation_id = "switch_self_with_bench"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "自分の控えと入れ替えるワザ", damage="none")
        if attack.text_ja != "自分の控えポケモンを選び、このカードと入れ替える。":
            problems.append(f"説明 {attack.text_ja!r} が、自分の控えと入れ替えるワザの説明ではない")
        return problems

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        bench = state.players[use.player].bench
        return _decision_form(decision, _label(state, use), kind=SELECT_POKEMON, player=use.player, choices=(1, 1), options=(p.pokemon_id for p in bench))


@dataclass(frozen=True)
class CoinsPerAttachedEnergyDamage(AttackEffect):
    """自分についているエネルギーの数だけコインを投げて、「おもて」の数 × ``per`` のダメージ（v0.34。ナッシーの「たまなげMAX」）。

    - 「エネルギーの数」は、ワザを使うポケモンについているエネルギーの数（``state.energy_types`` の数）。今の写しのエネルギーカードはどれも基本エネルギーで、
      1 枚が 1 つなので、ついているエネルギーカードの枚数と同じ（2 つぶんのエネルギーになる特殊エネルギーを加えるときは数え方を確かめる）
    - コインはダメージの要素の中（ダメージの量だけを決める）。受けるポケモンがダメージを受けない状態なら、投げるかが決まらない（v0.4b の問い）
    - 先読みは、v0.31 のれんぞくファイヤーボールと同じく、コインの並びのすべて（2 のエネルギーの数乗）を試す。上限（4,096 通り）を超えたら
      ``UNSUPPORTED_PREFLIGHT_LIMIT``
    """

    per: int
    implementation_id = "coins_per_attached_energy_damage"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "ついているエネルギーの数のコインでダメージのワザ", damage="modified", modifier="×")
        expected = f"自分についているエネルギーの数だけコインを投げて「おもて」の数×{self.per}のダメージ。"
        if attack.text_ja != expected or attack.damage != self.per:
            problems.append(f"説明 {attack.text_ja!r}・ダメージ {attack.damage} が {expected!r}・{self.per} ではない")
        return problems


@dataclass(frozen=True)
class ReduceDamageToSelf(AttackEffect):
    """相手の対戦ポケモンを、このカードにワザを使う時に与えるダメージが ``amount`` へる状態にする（次の自分の番の始めに消える）（v0.34。カラカラの「なきつく」）。

    - 相手に与える持続する効果 ``ReducedDamageToSource``（v0.31 の「しっぽをふる」と同じく、相手の対戦ポケモンが受ける）。はたらく番は次の相手の番で、
      受けたポケモンが「このカード」にワザでダメージを与えるとき、p.321 の 2 段階（ワザを使うポケモンの持っている「ダメージを変更する効果」）で減らす
    - 期限は説明のとおり「次の自分の番の始め」（はたらく番の終わりではない。型の ``expires_at_turn_start``）。受けたポケモンがベンチにもどる・進化する・
      きぜつすると消える（ほかの持続する効果と同じ）
    - 相手に与える効果なので、「ワザをうけない」状態・「とうめい」を評価する。ダメージの要素はない
    - 受けたポケモンのワザが、このカードが控えにいるときに控えポケモンへのダメージを与える場合は決められない（NK5。``UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET``）
    """

    amount: int
    implementation_id = "reduce_damage_to_self"
    opponent_effect_elements = (REDUCED_DAMAGE_ELEMENT,)

    def __post_init__(self) -> None:
        if type(self.amount) is not int or self.amount <= 0 or self.amount % 10:
            raise ValueError(f"減らすダメージは 10 の倍数の正の数（{self.amount!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "相手のワザのダメージをへらす状態にするワザ", damage="none")
        expected = f"「{attack.name_ja}」を受けた相手は、このカードにワザを使う時、与えるダメージが{self.amount}へる。この状態は次の自分の番の始めに消える。"
        if attack.text_ja != expected:
            problems.append(f"説明 {attack.text_ja!r} が {expected!r} ではない")
        return problems


@dataclass(frozen=True)
class PutTypeBasicFromDeckOntoBench(AttackEffect):
    """自分の山札から ``pokemon_type`` のたねポケモンを 1 匹選んでベンチに出す。その後、その山札をよく切る。進化カードは選べない。自分のベンチに空きがなければ
    使えない（v0.34。ガラガラの「たすけをよぶ」「自分の山札から「闘」ポケモンを1匹選んでベンチにだす。…」）。

    - v0.32 の「なかまをよぶ」（``PutBasicFromDeckOntoBench``。名前で選ぶ）と同じ要素 ``BenchFromDeck`` の、タイプで選ぶ形（``pokemon_type``）。選べるのは
      山札の、そのタイプのたねポケモン（説明の「進化カードは選べない」。``bench_from_deck_candidates``）
    - ベンチに空きがないことは、ワザを使うための条件（``usage_problem``。``BENCH_FULL``）。山札に選べるものがなければ出さずに切る（p.309。v0.32 と同じ）
    """

    pokemon_type: EnergyType
    implementation_id = "put_type_basic_from_deck_onto_bench"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "山札からタイプでベンチに出すワザ", damage="none")
        expected = (f"自分の山札から「{self.pokemon_type.ja}」ポケモンを1匹選んでベンチにだす。その後、その山札をよくきる。進化カードは選べない。"
                    "自分のベンチに空きがなければ使えない。")
        if attack.text_ja != expected:
            problems.append(f"説明 {attack.text_ja!r} が {expected!r} ではない")
        return problems

    def usage_problem(self, state: GameState, attacker: PokemonInPlay) -> IllegalActionError | None:
        owner, _ = state.find_pokemon(attacker.pokemon_id)
        if len(state.players[owner].bench) >= state.rules.max_bench:
            return IllegalActionError("BENCH_FULL", f"自分のベンチに空きがない（{state.rules.max_bench} 匹）ので、このワザは使えない（ワザの説明）")
        return None

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        return _decision_form(decision, _label(state, use), kind=BENCH_FROM_DECK, player=use.player, choices=(1, 1),
                              options=bench_from_deck_candidates(state, use.player, (), self.pokemon_type))


# ---------------------------------------------------------------- v0.35: 可変枚数のコインの先読み・ダメージの計算の順番の決定と合わせて加えた 5 枚
# （docs/coin-groups-damage-order-v0.35.md）。処理は解決の基盤の要素の並び（resolution/programs.py の BUILDERS）。処理に使う文面は kyuura の印刷の文面。


@dataclass(frozen=True)
class MultiplyNextTurnAttackDamage(AttackEffect):
    """ダメージの要素のないワザ。ワザを使ったポケモン自身に、「次の自分の番、このカードが使う ``target_attack_name`` のダメージは ``factor`` 倍になる」
    持続する効果を与える（v0.35。マチスのコラッタ・ラッタの「きあいだめ」）。

    - 持続する効果は v0.27 の ``state.NextTurnAttackDamage`` の「数をかける」決め方（``operation`` が ``NEXT_TURN_MULTIPLY``。種類
      ``next_turn_attack_damage_multiplier``）。「つるぎのまい」の「その数にする」（``SetNextTurnAttackDamage``）とは計算が違う（流用しない）
    - かけるのは p.321 の 2 段階（「ワザを使うポケモンの持っている「ダメージを変更する効果」」。p.321 の例「つるぎのまい」と同じく、ワザを使うポケモンの
      持続する状態の効果。``damage.MULTIPLY``）。1 段階（基本となるダメージ。でんこうせっかはコインの結果の 10 か 30）に ``factor`` をかけ、弱点・抵抗力・
      プラスパワーなどはそのあとの段階
    - ``includes_self_damage``: 説明の「(自分へのダメージも2倍)」（マチスのラッタ）。そのワザの自分へのダメージの 2 段階にも同じ数をかける。ない説明
      （マチスのコラッタ。でんこうせっかに自分へのダメージはない）は相手へのダメージだけ
    - はたらくのは次の自分の番（今の番 + 2）で、その番の終わりに消える。ベンチにもどる・進化・きぜつで消える（p.322・p.323。v0.27 と同じ消える契機）。
      はたらく番にもう一度使うと、その番の終わりまで、はたらく番の違う 2 つがある（v0.27 の SC7 と同じ。かけるのははたらく番の 1 つだけ）
    - 同じ 2 段階にほかの効果（「なきつく」）が重なり、計算の順番で結果が変わるときは、ワザを使うプレイヤーが順番を選ぶ（p.321。``damage.DamageOrderRequired``・
      決定 ``damage_step_order``）
    """

    target_attack_index: int
    target_attack_name: str
    factor: int = 2
    includes_self_damage: bool = False
    implementation_id = "multiply_next_turn_attack_damage"

    def __post_init__(self) -> None:
        if type(self.target_attack_index) is not int or self.target_attack_index < 0:
            raise ValueError(f"ダメージが変わるワザの位置は 0 以上の整数（{self.target_attack_index!r}）")
        if type(self.factor) is not int or self.factor < 2:
            raise ValueError(f"ダメージにかける数は 2 以上の整数（{self.factor!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "次の自分の番のワザのダメージをかける効果のワザ", damage="none")
        clause = f"(自分へのダメージも{self.factor}倍)" if self.includes_self_damage else ""
        pattern = f"次の自分の番、この「[^」]+」が使う「{re.escape(self.target_attack_name)}」のダメージは{self.factor}倍になる。{re.escape(clause)}"
        if re.fullmatch(pattern, attack.text_ja or "") is None:
            problems.append(f"説明 {attack.text_ja!r} が、「{self.target_attack_name}」のダメージを {self.factor} 倍にする効果"
                            f"（自分へのダメージ {'も' if self.includes_self_damage else 'なし'}）の説明ではない")
        return problems

    def card_problems(self, attack: Attack, attacks: tuple[Attack, ...]) -> list[str]:
        index = self.target_attack_index
        if index == attack.index or not 0 <= index < len(attacks):
            return [f"ダメージが変わるワザの位置 {index} が、このカードのほかのワザではない"]
        target = attacks[index]
        problems = []
        if target.name_ja != self.target_attack_name:
            problems.append(f"ダメージが変わるワザの名前「{self.target_attack_name}」が、{index} 番目のワザ「{target.name_ja}」と違う")
        if type(target.damage) is not int:
            problems.append(f"ダメージが変わるワザ「{target.name_ja}」にダメージの目安がない")
        if ("自分にも" in (target.text_ja or "")) != self.includes_self_damage:
            problems.append(f"ダメージが変わるワザ「{target.name_ja}」の自分へのダメージの有無と、登録の includes_self_damage が合わない")
        return problems

    def next_turn_terms(self) -> tuple[int, int, str, bool]:
        """このワザが与える ``NextTurnAttackDamage`` の (変わるワザの位置, かける数, 変え方, 自分へのダメージにも)（不変条件・ログの監査が照らす）。"""
        return self.target_attack_index, self.factor, NEXT_TURN_MULTIPLY, self.includes_self_damage


@dataclass(frozen=True)
class DamageThenLockSelfOnTails(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。そのあとコインを投げて「うら」なら、次の自分の番、このカードはこのワザを使えない（v0.35。
    カスミのニョロモの「あわあわ」）。

    - 持続する効果 ``state.CannotUseOwnAttack``（自分自身。はたらく番は次の自分の番）。その番の間、このワザ（位置）だけを使えない（``checks.attack_request``
      の ``ATTACK_LOCKED``。ほかのワザ・にげるは使える）。その番の終わりに消える。ベンチにもどる・進化・きぜつで消える（p.322・p.323）
    - コインはワザを使ったポケモン自身への効果だけを決めるので、相手が「ダメージを受けない」「ワザをうけない」状態でも投げる（v0.34 の
      ``void_coin_question`` の読み方）。ワザを使ったポケモンが同じワザの中で HP 以上になっていれば（相手の「はんげき」など）、効果を与えず、コインも投げない
      （v0.34 の「こうそくいどう」と同じ）
    """

    implementation_id = "damage_then_lock_self_on_tails"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_damage_then_effect(attack, "コインで自分がそのワザを使えなくなる")
        expected = f"コインを投げて「うら」なら、次の自分の番、このカードは「{attack.name_ja}」を使えない。"
        if attack.text_ja != expected:
            problems.append(f"説明 {attack.text_ja!r} が {expected!r} ではない")
        return problems

    def attack_lock_terms(self) -> tuple[type, int | None]:
        """このワザが与える持続する効果の型と、使えなくなるワザの位置（自分のこのワザなので None = 効果を与えたワザと同じ。不変条件が照らす）。"""
        from .state import CannotUseOwnAttack

        return CannotUseOwnAttack, None


# v0.35・v0.37: ``LockOpponentAttack`` が受け付ける説明（kyuura の印刷の文面）。カスミのニョロモ（v0.35）と第1弾のニョロゾ（v0.37）。
# docs/fifteen-reused-effects-v0.37.md 3 章
LOCK_OPPONENT_ATTACK_TEXTS = (
    "相手のワザを1つ選ぶ。次の相手の番、そのポケモンは、そのワザを使えない。",
    "相手の対戦ポケモンの「ワザ」を1つ選ぶ。次の相手の番でその「ワザ」はつかえない。",
)


@dataclass(frozen=True)
class LockOpponentAttack(AttackEffect):
    """ダメージの要素のないワザ。相手の対戦ポケモンのワザを 1 つ選び、次の相手の番、そのポケモンはそのワザを使えない（v0.35。カスミのニョロモの
    「ドわすれ」）。

    - 選ぶのはワザを使ったプレイヤー（説明の「相手のワザを1つ選ぶ」）。決定 ``select_opponent_attack``（選べるものは、相手の対戦ポケモンのいちばん上の
      カードのワザの位置。1 つしかなくても決定を出す。v0.7 の K2 と同じ実装上の仮定）
    - 持続する効果 ``state.CannotUseAttack``（相手に与える。はたらく番は次の相手の番）。その番の間、受けたポケモンはそのワザ（位置）だけを使えない。
      ほかのワザ・にげる・特殊能力は制限しない。消える契機はほかの持続する効果と同じ（期限・ベンチにもどる（にげる・ポケモンいれかえ・突風）・進化・きぜつ）
    - 相手に与える効果なので、選ぶ前に「ワザをうけない」状態・「とうめい」を評価する（v0.31 の「しっぽをふる」・相手のエネルギーをトラッシュする効果と
      同じ順番。受けないなら選ばない）
    - v0.37: 第1弾のニョロゾの「ドわすれ」の説明「相手の対戦ポケモンの「ワザ」を1つ選ぶ。次の相手の番でその「ワザ」はつかえない。」も受け付ける
      （選ぶのは相手の対戦ポケモンのワザ。使えなくなるのは、そのポケモンのそのワザ。ワザによる持続する効果は受けたポケモンに与えられ、ベンチに
      もどる・進化で消える（p.322。kyuura の GR-2000-P322-PERSISTENT-EFFECTS）ので、「そのポケモンは」を書かなくても処理は同じ）。ほかの書き方は
      受け付けない（``LOCK_OPPONENT_ATTACK_TEXTS``）
    """

    implementation_id = "lock_opponent_attack"
    opponent_effect_elements = (ATTACK_LOCK_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "相手のワザを使えなくするワザ", damage="none")
        if attack.text_ja not in LOCK_OPPONENT_ATTACK_TEXTS:
            problems.append(f"説明 {attack.text_ja!r} が、相手のワザを 1 つ選んで次の相手の番に使えなくする説明ではない")
        return problems

    def attack_lock_terms(self) -> tuple[type, int | None]:
        from .state import CannotUseAttack

        return CannotUseAttack, None

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        problems = super().decision_problems(state, use, decision)
        if decision.kind != SELECT_OPPONENT_ATTACK:
            return problems + [f"ドわすれの決定の種類 {decision.kind!r} が {SELECT_OPPONENT_ATTACK} ではない"]
        target = state.players[1 - use.player].active
        if target is None or decision.context_value("target") != target.pokemon_id:
            return problems + ["ドわすれの決定の対象が、相手の対戦ポケモンではない"]
        # v0.49: 選べるものは、相手の対戦ポケモンが今持つワザ（``held_attack_keys``）の並びの位置。並びがいちばん上のカードのワザと同じなら v0.48 と同じ形
        # （ワザの位置）、違えば ``lock_attacks`` に (カードの id, 位置) の並び
        entries, legacy = held_attack_keys(state, target)
        keys = [(key.card_id, key.attack_index) for key, _ in entries]
        locked = decision.context_value("lock_attacks")
        if decision.options != tuple(range(len(entries))) or not entries or (decision.min_choices, decision.max_choices) != (1, 1):
            problems.append(f"ドわすれの決定の選べるもの {decision.options!r} が、相手の対戦ポケモンのワザの位置ではない")
        if (locked is not None) == legacy or (locked is not None and [tuple(key) for key in locked] != keys):
            problems.append(f"ドわすれの決定のワザの並び {locked!r} が、相手の対戦ポケモンが今持つワザ {keys} ではない")
        held = [i for i, (_, problem) in enumerate(entries) if problem is not None]
        if not set(held) <= set(decision.context_value("unresolved_choices", ())):
            problems.append(f"持つかが読み方で変わるワザ {held} が、選ぶと止めるものにない")
        return problems


@dataclass(frozen=True)
class CoinsPerAttachedTypeBonusDamage(AttackEffect):
    """ダメージの目安の数字 +「このカードについている ``energy_type`` エネルギーの数ぶんコインを投げ、「おもて」の数 × ``per`` のダメージを追加する」（v0.35。
    カスミのニョロゾの「ウォーターパンチ」）。

    - 数えるのは、ワザを使うポケモンについている ``energy_type`` のエネルギーの数（``state.energy_types`` のうち ``energy_type`` のもの。エネルギーカードの
      枚数ではなく、カードが出すエネルギー。今の写しのエネルギーカードはどれも 1 つのエネルギーを出す基本エネルギーで、同じ数になる。2 つ以上のエネルギーを
      出すカードを加えるときは数え方を確かめる）。0 ならコインを投げず、ダメージの目安の数字だけ
    - コインはダメージの要素の中（ダメージの量だけを決める）。受けるポケモンがダメージを受けない状態なら、投げるかが決まらない（v0.4b の問い）
    - 先読みは「おもて」の数でまとめる（エネルギーの数 + 1 通り。docs 2 章）
    """

    energy_type: EnergyType
    per: int
    implementation_id = "coins_per_attached_type_bonus_damage"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "ついているエネルギーの数のコインで追加ダメージのワザ", damage="modified", modifier="+")
        expected = f"このカードについている「{self.energy_type.ja}」エネルギーの数ぶんコインを投げ、「おもて」の数×{self.per}のダメージを追加する。"
        if attack.text_ja != expected:
            problems.append(f"説明 {attack.text_ja!r} が {expected!r} ではない")
        return problems


@dataclass(frozen=True)
class CoinsHeadsDamageTailsSelfDamage(AttackEffect):
    """コインを ``coins`` 枚投げ、「おもて」の数 × ``per`` のダメージ。その後、「うら」の数 × ``self_per`` のダメージを自分に与える（v0.35。カツラの
    ケンタロスの「ぜんりょくとっしん」）。

    - 1 回投げた ``coins`` 枚のコイン（ワザ全体のコイン）の「おもて」の数で相手へのダメージ、同じコインの「うら」の数で自分へのダメージが決まる（別々に
      投げない。相手へのダメージと自分へのダメージは同じ結果の組）。先読みも「おもて」の数でまとめ、組を ``coins`` + 1 通り試す
    - 相手へのダメージ → 自分へのダメージ（説明の「その後」）。どちらもワザによるダメージ（p.321。自分へのダメージは自分のタイプと自分の弱点・抵抗力。
      v0.3d）。「おもて」が 0 枚なら相手へのダメージは 0（与えなかった）、「うら」が 0 枚なら自分へのダメージは 0
    - コインは相手へのダメージと自分へのダメージの両方を決めるので、相手が「ダメージを受けない」状態でも投げる（v0.34 の ``void_coin_question``）
    """

    coins: int
    per: int
    self_per: int
    implementation_id = "coins_heads_damage_tails_self_damage"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "コインのおもてで相手に・うらで自分にダメージのワザ", damage="modified", modifier="×")
        expected = f"コインを{self.coins}枚投げ、「おもて」の数×{self.per}のダメージ。その後、「うら」の数×{self.self_per}のダメージを自分に与える。"
        if attack.text_ja != expected or attack.damage != self.per:
            problems.append(f"説明 {attack.text_ja!r}・ダメージ {attack.damage} が {expected!r}・{self.per} ではない")
        return problems


# v0.36: 「次の相手の番にワザを使うときにコインを投げ、「うら」ならワザは失敗する」効果の説明（kyuura の印刷の文面。文面ごとに、効果が「1回できえる」か）。
# 似た名前のワザを同じ設定にしないよう、説明の文面で登録を確かめる（docs/sand-attack-retreat-lock-v0.36.md 2 章の表）
ATTACK_COIN_CHECK_TEXTS: dict[str, bool] = {
    # サンド（PMCG1-051）の「すなかけ」: 「次の番に」・「効果は1回できえる」
    "「すなかけ」を受けた相手は、次の番に「ワザ」を使うときに、コインをなげ、「おもて」なら成功、「うら」なら「ワザ」は失敗する。"
    "「すなかけ」の効果は1回できえる。": True,
    # 化石の秘密のブーバー（PMCG3-008）・タッツー（PMCG3-014）の「えんまく」
    "「えんまく」を受けた相手は、次の相手の番にワザを使うときにコインを投げ、「うら」ならワザは失敗する。": False,
    # カスミのタッツー（PMCG5-025）の「えんまく」
    "このワザを受けたポケモンは、次の相手の番にワザを使う時にコインを投げ、「うら」ならワザは失敗する。": False,
    # わるいサンダース（PMCG4-029）の「サンダーフラッシュ」
    "このワザを受けたポケモンは、次の相手の番にワザを使うときにコインを投げ、「うら」ならワザは失敗する。": False,
    # キョウのポッポ（PMCG6-062）の「すなかけ」・カスミのパウワウ（PMCG5-023）の「しんきろう」・キョウのドガース（PMCG6-015）の「えんまく」
    "このワザを受けた相手は、次の相手の番でワザを使う時にコインを投げ、「うら」なら、ワザは失敗する。": False,
}
RETREAT_LOCK_TEXT = "このワザを受けた相手は、次の相手の番に「にげる」ことができない。"
RETURN_SELF_TO_DECK_TEXT = "コインを投げて「おもて」なら、ダメージを与えた後、自分と、自分についているすべてのカードを山札にもどす。その後、その山札をよく切る。"


@dataclass(frozen=True)
class DamageThenAttackCoinCheck(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。このワザを受けたポケモンは、次の相手の番にワザを使うときにコインを投げ、「うら」ならワザは
    失敗する（v0.36。サンド・キョウのポッポの「すなかけ」、ブーバー・タッツー・カスミのタッツー・キョウのドガースの「えんまく」、わるいサンダースの
    「サンダーフラッシュ」、カスミのパウワウの「しんきろう」。docs/sand-attack-retreat-lock-v0.36.md 2 章）。

    - 相手に与える持続する効果 ``state.AttackCoinCheck``（はたらく番は次の相手の番）。コインを投げるのは、効果を受けたポケモンがワザを使うとき（p.309 の
      ワザを使う手順 4。宣言のあと・こんらんのコインの前。``resolution.flow._attack_check_failed``）で、このワザの中ではコインを投げない
    - ``single_use``: 説明が「効果は1回できえる」（サンドの「すなかけ」）。説明の文面（``ATTACK_COIN_CHECK_TEXTS``）と合わない登録は拒否する
    - 相手に与える効果なので「ワザをうけない」状態・「とうめい」を評価する。相手がこのワザで HP 以上になったら効果を与えない（p.309）
    """

    single_use: bool = False
    implementation_id = "damage_then_attack_coin_check"
    opponent_effect_elements = (ATTACK_CHECK_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "次の相手の番にワザを使うときにコインを投げさせるワザ", damage="fixed")
        if ATTACK_COIN_CHECK_TEXTS.get(attack.text_ja) is not self.single_use:
            problems.append(f"説明 {attack.text_ja!r} が、効果が1回{'で消える' if self.single_use else 'で消えない'}「うら」ならワザが失敗する効果の説明ではない")
        return problems

    def attack_check_terms(self) -> tuple[type, bool]:
        from .state import AttackCoinCheck

        return AttackCoinCheck, self.single_use


@dataclass(frozen=True)
class DamageThenRetreatLock(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。このワザを受けた相手は、次の相手の番に「にげる」ことができない（v0.36。カスミのパウワウの
    「アイスバーン」・マチスのオニドリルの「わしづかみ」）。

    - 相手に与える持続する効果 ``state.CannotRetreat``（はたらく番は次の相手の番）。その番の間、「にげる」の宣言を拒否する（``engine._retreat``。
      エネルギーのトラッシュ・こんらんのコインの前）。「にげる」でない入れ替え（ポケモンいれかえ・突風・ふきとばし・テレポート）は制限しない（p.325）
    - 相手に与える効果なので「ワザをうけない」状態・「とうめい」を評価する。相手がこのワザで HP 以上になったら効果を与えない（p.309）
    """

    implementation_id = "damage_then_retreat_lock"
    opponent_effect_elements = (RETREAT_LOCK_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "次の相手の番に「にげる」ことができなくするワザ", damage="fixed")
        if attack.text_ja != RETREAT_LOCK_TEXT:
            problems.append(f"説明 {attack.text_ja!r} が {RETREAT_LOCK_TEXT!r} ではない")
        return problems

    def retreat_lock_terms(self) -> type:
        from .state import CannotRetreat

        return CannotRetreat


@dataclass(frozen=True)
class DamageThenReturnSelfToDeckOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、ダメージを与えた後、自分と、自分についているすべてのカードを
    山札にもどす。その後、その山札をよく切る（v0.36。キョウのドガースの「くもがくれガス」。docs/sand-attack-retreat-lock-v0.36.md 4 章）。

    - ダメージ → コイン → 山札にもどす → 山札を切る。もどすのはワザを使ったポケモンのカード（進化していれば重なったカードもすべて）・ついているエネルギー
      カード・トレーナーカード（``zones.return_in_play_to_deck``）。きぜつではない（サイドは取られない。ログ ``knock_out`` ではない）
    - 場をはなれたので、ダメージカウンター・特殊状態・持続する効果はなくなる（p.322。持続する効果は理由 ``return_in_play_to_deck``）。バトル場が空くので、ワザの
      あとの勝ち負けの判定（p.311。控えがいなければ負け）とバトル場に出す決定（p.313）は、きぜつのあとと同じ処理
    - 「ダメージを与えた後」: ダメージを与えなかったときは Z23（``UNRESOLVED_EFFECT_AFTER_NO_DAMAGE``）。同じワザで HP 以上になったポケモンがいれば RD9
      （``UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT``）。どちらもコインの結果によらず宣言の前に止まる
    - ワザを使ったポケモンが相手の「はんげき」などですでに HP 以上なら、もどさない（自分への効果。CR-SHELL-ATTACK-KO-ATTACKER-OWN-EFFECTS）
    """

    implementation_id = "damage_then_return_self_to_deck_on_heads"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "自分を山札にもどすワザ", damage="fixed")
        if attack.text_ja != RETURN_SELF_TO_DECK_TEXT:
            problems.append(f"説明 {attack.text_ja!r} が {RETURN_SELF_TO_DECK_TEXT!r} ではない")
        return problems


# ---------------------------------------------------------------- v0.37（docs/fifteen-reused-effects-v0.37.md）
# 既存の要素の組み合わせ。ダメージのある型をダメージの目安のないワザに広げず、ワザの意味ごとに型を分ける。説明の文面は、登録したワザの印刷の文面
# （kyuura の写し）と完全に同じものだけを受け付ける（意味の違うワザを同じ型で登録しない）


def _check_exact_text(attack: Attack, what: str, accepted: Iterable[str]) -> list[str]:
    """説明が ``accepted`` のどれかと完全に同じか（v0.37）。"""
    accepted = tuple(accepted)
    if attack.text_ja in accepted:
        return []
    return [f"説明 {attack.text_ja!r} が、{what}の説明（{' / '.join(repr(t) for t in accepted)}）ではない"]


@dataclass(frozen=True)
class PoisonOnHeadsWithoutDamage(AttackEffect):
    """ダメージを与えず、コインを 1 枚投げて「おもて」なら相手の対戦ポケモンをどく状態にする（v0.37。化石の秘密のアーボの「どくえき」）。

    - ダメージの目安の数字がないワザだけを登録できる（v0.17a の ``ConfuseOnHeadsWithoutDamage`` と同じ形）。ダメージの要素がないので、ダメージの計算・
      ``damage`` のログはない。ダメージの目安のあるワザの ``PoisonOnHeads``（どくばり）とは別の型（同じ説明の文面でも、ダメージの有無で分ける）
    - 要素の並びは既存の要素だけ（``programs.Status(POISON, local_coin=HEADS)``。どくばりのどくの要素と同じ）。コインの前に「ワザをうけない」状態
      （HC3）を確かめ、コイン →「おもて」なら「とうめい」の評価 → どく
    """

    implementation_id = "poison_on_heads_without_damage"
    opponent_effect_elements = (POISON,)

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "ダメージを与えずにコインでどく状態にするワザ", damage="none") + _check_exact_text(
            attack, "コインでどく状態にするワザ", ("コインを投げて「おもて」なら、相手を「どく」状態にする。",))


@dataclass(frozen=True)
class ParalyzeOnHeadsWithoutDamage(AttackEffect):
    """ダメージを与えず、コインを 1 枚投げて「おもて」なら相手の対戦ポケモンをマヒ状態にする（v0.37。タケシのイワークの「うなりごえ」）。

    - ダメージの目安の数字がないワザだけを登録できる。ダメージの目安のあるワザの ``ParalyzeOnHeads``（しびれごな・まきつく）とは別の型
    - 要素の並びは既存の要素だけ（``programs.Status(PARALYSIS, local_coin=HEADS, reparalysis_check=True)``。マヒの再付与で回復する番が変わる場合は
      v0.3b の ``UNRESOLVED_REPARALYSIS_RECOVERY_TURN``）
    """

    implementation_id = "paralyze_on_heads_without_damage"
    opponent_effect_elements = (PARALYSIS,)

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "ダメージを与えずにコインでマヒ状態にするワザ", damage="none") + _check_exact_text(
            attack, "コインでマヒ状態にするワザ", ("コインを投げて「おもて」なら、相手を「マヒ」状態にする。",))


@dataclass(frozen=True)
class DamageThenDrawOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。その後、コインを投げて「おもて」なら、自分の山札の上からカードを ``count`` 枚引いて、
    手札に加える（v0.37。ニャースの「ねこにこばん」）。

    - 要素の並びは既存の要素だけ: ``Damage`` → ワザ全体のコイン ``Coin`` → ``Draw``（コインの「おもて」のとき）。ダメージの処理が先（p.309）
    - ドローはワザを使ったプレイヤーへの効果で、相手の対戦ポケモンへの効果ではない。相手が「ダメージを受けない」「ワザをうけない」状態や「とうめい」で
      ダメージを受けなくても、コインを投げて引く（v0.34 の ``void_coin_question`` の読み方）。相手がこのワザのダメージできぜつしても引く（処理の対象は
      自分の山札。p.309 の「処理の対象がいなくなっていたら」に当たらない）
    - 山札が足りなければ引けるだけ引く（効果で引くときの規定。p.312。0 枚でも負けではない）
    """

    count: int
    implementation_id = "damage_then_draw_on_heads"

    def __post_init__(self) -> None:
        if type(self.count) is not int or self.count < 1:
            raise ValueError(f"引く枚数は 1 以上の整数（{self.count!r}）")

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "ダメージのあとコインで山札から引くワザ", damage="fixed") + _check_exact_text(
            attack, "コインの「おもて」で山札から引くワザ", (f"コインを投げて「おもて」なら、自分の山札の上からカードを{self.count}枚ひいて、手札に加える。",))


@dataclass(frozen=True)
class DrawOnHeads(AttackEffect):
    """ダメージを与えず、コインを投げて「おもて」なら、山札からカードを ``count`` 枚引く（v0.37。キョウのモンジャラの「つるでさがす」）。

    - 要素の並びは既存の要素だけ: ``Coin`` → ``Draw``（コインの「おもて」のとき）。v0.31 の ``DrawCardsAttack``（コインなしで引く。第4弾のコダックの
      「めまい」）とは別の型
    - 自分への効果なので、相手の状態によらずコインを投げる。山札が足りなければ引けるだけ引く（p.312）
    """

    count: int
    implementation_id = "draw_on_heads"

    def __post_init__(self) -> None:
        if type(self.count) is not int or self.count < 1:
            raise ValueError(f"引く枚数は 1 以上の整数（{self.count!r}）")

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "コインで山札から引くワザ", damage="none") + _check_exact_text(
            attack, "コインの「おもて」で山札から引くワザ", (f"コインを投げて「おもて」なら、山札からカードを{self.count}枚引く。",))


@dataclass(frozen=True)
class SelfBarrierOnHeads(AttackEffect):
    """ダメージを与えず、コインを投げて「おもて」なら、次の相手の番、このカードはワザによるダメージや効果を受けない（v0.37。カスミのコイキングの
    「しんだふり」）。

    - 効果は v0.31 のミュウツーの「バリアー」・v0.34 のギャロップの「こうそくいどう」と同じ持続する効果 ``AttackBarrier``（自分自身に与え、次の相手の
      番に、このポケモンへのワザのダメージの要素と効果の要素を無効にする。p.321 の「ダメージを受けない」状態とは別。期限・消える条件も同じ）。説明の
      「ワザによるダメージや効果を受けない」は、ダメージだけを防ぐ「かたまる」（``PreventDamage``）・へらす「ちいさくなる」（``DamageReduction``）とは違う
    - 要素の並びは既存の要素だけ（``programs.SelfPersistent(AttackBarrier, local_coin=HEADS)``）。自分への効果なので、相手の状態によらずコインを投げる
    """

    implementation_id = "self_barrier_on_heads"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "コインで次の相手の番にワザを受けなくなるワザ", damage="none") + _check_exact_text(
            attack, "コインの「おもて」で次の相手の番にワザによるダメージや効果を受けないワザ",
            ("コインを投げて「おもて」なら、次の相手の番、このカードはワザによるダメージや効果を受けない。",))


@dataclass(frozen=True)
class DamageThenReduceDamageToSelf(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。その後、相手の対戦ポケモンを、このカードにワザを使う時に与えるダメージが ``amount``
    へる状態にする（次の自分の番の始めに消える）（v0.37。ペルシアンの「かみつく」）。

    - 効果は v0.34 のカラカラの「なきつく」（``ReduceDamageToSelf``）と同じ相手に与える持続する効果 ``ReducedDamageToSource``（要素
      ``OpponentReducedDamage``）。対象（「このカード」に与えるワザのダメージだけ。p.321 の 2 段階）・期限（次の自分の番の始め）・消える条件（受けた
      ポケモンがベンチにもどる・進化・きぜつ）・NK5（控えにいる「このカード」へのダメージ）も同じ
    - ダメージ → 効果。相手がこのワザのダメージで HP 以上になったら、処理の対象がいないので効果を与えない（p.309）。相手に与える効果なので「ワザを
      うけない」状態・「とうめい」を評価する（ダメージを防ぐ「かたまる」の相手には効果を与える。p.321）
    - 説明は「なきつく」と同じ形で、kyuura の写しの書き方（「【相手】」・「あたえる」）の違いだけを受け付ける（pcg-search.com の同じ版のページは
      「相手」。どちらも同じ意味）
    """

    amount: int
    implementation_id = "damage_then_reduce_damage_to_self"
    opponent_effect_elements = (REDUCED_DAMAGE_ELEMENT,)

    def __post_init__(self) -> None:
        if type(self.amount) is not int or self.amount <= 0 or self.amount % 10:
            raise ValueError(f"減らすダメージは 10 の倍数の正の数（{self.amount!r}）")

    def check(self, attack: Attack) -> list[str]:
        accepted = [f"「{attack.name_ja}」を受けた{subject}は、このカードにワザを使う時、{verb}ダメージが{self.amount}へる。この状態は次の自分の番の始めに消える。"
                    for subject in ("相手", "【相手】") for verb in ("与える", "あたえる")]
        return _check_form(attack, "ダメージのあと相手のワザのダメージをへらす状態にするワザ", damage="fixed") + _check_exact_text(
            attack, "このカードへのワザのダメージをへらす状態にするワザ", accepted)


# ---------------------------------------------------------------- v0.38（docs/bench-switch-combined-v0.38.md）
# 控えへのダメージ・入れ替え・同じコインの複数の効果・軽減・山札にもどる効果。どれも既存の要素（``resolution.programs``）の組み合わせで、要素の
# 共通の項目（``ChosenBenchDamage.required``・``ForceSwitch.local_coin``・``SelfSwitch.local_coin``・``SelfPersistent.gate``・``ReturnSelfToDeck`` の
# ``discard_attached``・``shuffle``）と、場をはなれたあとの要素（``PromoteFromBench``・``RevealPokemonFromDeck``）を加えた。説明の文面は、登録したワザの
# 印刷の文面（kyuura の写し）と完全に同じものだけを受け付ける


def _positive_tens(value: int, what: str) -> None:
    if type(value) is not int or value <= 0 or value % 10:
        raise ValueError(f"{what}は 10 の倍数の正の数（{value!r}）")


CHOOSE_OPPONENT_BENCH_DAMAGE_TEXTS = {
    # サワムラー（PMCG3-039）の「のびるキック」。控えがいなければ使えない（ワザを使うための条件）
    True: lambda n: (f"相手の控えポケモンを1匹選び、そのポケモンに「弱点・抵抗力」に関係なく{n}ダメージ。相手に控えポケモンがいないとき、このワザは使えない。",),
    # エリカのモンジャラ（PMCG5-006）の「のびるつる」。使えない、の記述がない。v0.43: エリカのマダツボミ（PMCG5-010）の「のびるつる」の書き方（「相手の控え
    # ポケモンを1匹選び、そのポケモンに、「弱点・抵抗力」に関係なく、10ダメージ。」。選ぶのはワザを使ったプレイヤー・相手の控えポケモン 1 匹・弱点・抵抗力に
    # 関係なく・控えがいないときに使えないとは書かない、で同じ意味）も受け付ける
    False: lambda n: (f"相手の控えポケモンから1匹を選び、(「弱点・抵抗力」に関係なく){n}ダメージ。",
                      f"相手の控えポケモンを1匹選び、そのポケモンに、「弱点・抵抗力」に関係なく、{n}ダメージ。"),
}


@dataclass(frozen=True)
class ChooseOpponentBenchDamage(AttackEffect):
    """相手の対戦ポケモンにはダメージを与えず、相手の控えポケモンを 1 匹選んで、そのポケモンに「弱点・抵抗力」に関係なく ``damage`` ダメージ（v0.38。サワムラーの
    「のびるキック」・エリカのモンジャラの「のびるつる」）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。1 匹。控えが 1 匹でも出す。v0.33 のかけぬけると同じ要素 ``ChosenBenchDamage``。コインはない）
    - 計算はかけぬける・ミニじしんと同じ（p.320 のダメージの (2)。弱点・抵抗力なし（説明に明記）・プラスパワーは変えない（p.257）・ディフェンダーは変える）
    - ``requires_bench``（のびるキック）: 説明の「相手に控えポケモンがいないとき、このワザは使えない」はワザを使うための条件（``usage_problem``。必要な
      エネルギーの確認のあと・こんらんのコインの前。``NO_OPPONENT_BENCH``）。のびるつるには同じ記述がないので、控えがいなくても使え、処理の対象がないので
      何もしない（p.309。v0.31 のかどわかす・v0.33 のかけぬけると同じ読み方。ワザは使ったことになり、番は終わる）
    """

    damage: int
    requires_bench: bool
    implementation_id = "choose_opponent_bench_damage"

    def __post_init__(self) -> None:
        _positive_tens(self.damage, "控えポケモンへのダメージ")

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "相手の控えポケモンを選んでダメージを与えるワザ", damage="none") + _check_exact_text(
            attack, "相手の控えポケモンを選んでダメージを与えるワザ", CHOOSE_OPPONENT_BENCH_DAMAGE_TEXTS[self.requires_bench](self.damage))

    def usage_problem(self, state: GameState, attacker: PokemonInPlay) -> IllegalActionError | None:
        owner, _ = state.find_pokemon(attacker.pokemon_id)
        if self.requires_bench and not state.players[1 - owner].bench:
            return IllegalActionError("NO_OPPONENT_BENCH", "相手に控えポケモンがいないので、このワザは使えない（ワザの説明）")
        return None

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        bench = state.players[1 - use.player].bench
        return _decision_form(decision, _label(state, use), kind=SELECT_POKEMON, player=use.player, choices=(1, 1), options=(p.pokemon_id for p in bench))


def choose_opponent_pokemon_damage_texts(damage: int) -> tuple[str, ...]:
    """v0.43: 相手の場のポケモンを選んでダメージを与えるワザの説明（わるいゴルバット（PMCG4-009）の「ふらふらとぶ」）。"""
    # v0.44: ロケット団のディグダ（PMCG4-038）の「じめんにもぐる」の書き方（「相手の場のポケモンを1匹選び、…」。助詞「を」の位置だけの違いで、選ぶのはワザを使った
    # プレイヤー・相手の場のポケモン（バトル場・ベンチ）1 匹・弱点・抵抗力に関係なく、で同じ意味）も受け付ける
    return (f"相手の場のポケモン1匹を選び、(「弱点・抵抗力」に関係なく){damage}ダメージ。",
            f"相手の場のポケモンを1匹選び、(「弱点・抵抗力」に関係なく){damage}ダメージ。")


@dataclass(frozen=True)
class ChooseOpponentPokemonDamage(AttackEffect):
    """相手の場のポケモン（バトル場・ベンチのどれでも）を 1 匹選び、(「弱点・抵抗力」に関係なく) ``damage`` ダメージ（v0.43。わるいゴルバットの「ふらふらとぶ」。
    kyuura の印刷の文面）。ダメージの目安の数字はない。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。選べるものは相手の場のポケモン（バトル場 → ベンチ）。1 匹でも出す）。v0.38 の
      ``ChooseOpponentBenchDamage`` と同じ要素の、選べるものに相手の対戦ポケモンを含めた形（``programs.ChosenOpponentPokemonDamage``）
    - 相手の対戦ポケモンを選んだら p.320 のダメージの (1)（プラスパワー・ディフェンダーを計算する）、控えポケモンを選んだら (2)（プラスパワーは変えない。p.257）。
      どちらも弱点・抵抗力は説明のとおり計算しない
    - 相手に控えポケモンがいなくても対戦ポケモンを選べる（使えない、の記述はない）
    """

    damage: int
    implementation_id = "choose_opponent_pokemon_damage"

    def __post_init__(self) -> None:
        _positive_tens(self.damage, "ダメージ")

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "相手の場のポケモンを選んでダメージを与えるワザ", damage="none") + _check_exact_text(
            attack, "相手の場のポケモンを選んでダメージを与えるワザ", choose_opponent_pokemon_damage_texts(self.damage))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        options = (p.pokemon_id for p in state.players[1 - use.player].in_play())
        return _decision_form(decision, _label(state, use), kind=SELECT_POKEMON, player=use.player, choices=(1, 1), options=options)


@dataclass(frozen=True)
class DamageThenChosenBenchDamage(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。相手に控えポケモンがいれば、1 匹を選び、「弱点・抵抗力」に関係なく ``bench_damage`` ダメージ
    （v0.38。タケシのロコンの「ほのおのわ」）。v0.33 のかけぬける（``DamageThenCoinBenchDamage``）からコインを除いた形（要素 ``ChosenBenchDamage`` の
    ``local_coin`` が None）。相手の対戦ポケモンがきぜつしても控えへのダメージは処理する（対象が違う。p.309）。控えがいなければ何もしない（説明の
    「いれば」）。相手の対戦ポケモンへのダメージで「ダメージを受けたとき」の効果がはたらいたら、決定をまたいで運び、控えへのダメージのあとに処理する（v0.34）。

    v0.39: ``weakness_resistance_stated`` が False なら、説明が控えへのダメージの弱点・抵抗力について書いていない書き方（ピカチュウ（PMCG2-024）の「スパーク」
    「相手の控えポケモンから1匹選び、そのポケモンにも10ダメージ。相手の控えポケモンが1匹もいないときにはこの効果はない。」）。v0.37 の JS1 と同じ問いで、選ぶと
    受けるダメージが読み方で変わる控えは選べるが選ぶと止める（``ChosenBenchDamage`` の ``weakness_resistance`` が None）。書き方と値の組だけを受け付ける。"""

    bench_damage: int
    weakness_resistance_stated: bool = True
    implementation_id = "damage_then_chosen_bench_damage"

    def __post_init__(self) -> None:
        _positive_tens(self.bench_damage, "控えポケモンへのダメージ")

    def check(self, attack: Attack) -> list[str]:
        if self.weakness_resistance_stated:
            # v0.42: ゲンガーの「ナイトヘッド」の書き方（「相手の控えポケモンから1匹選び、「弱点・抵抗力」に関係なく10ダメージ。相手に控えポケモンがいない時には、
            # この効果はない。」。選ぶのはワザを使ったプレイヤー・控えがいなければ何もしない・弱点・抵抗力に関係なく、で同じ意味）も受け付ける
            expected = (f"相手に控えポケモンがいれば、1匹を選び、「弱点・抵抗力」に関係なく、{self.bench_damage}ダメージ。",
                        f"相手の控えポケモンから1匹選び、「弱点・抵抗力」に関係なく{self.bench_damage}ダメージ。相手に控えポケモンがいない時には、この効果はない。")
        else:
            expected = (f"相手の控えポケモンから1匹選び、そのポケモンにも{self.bench_damage}ダメージ。相手の控えポケモンが1匹もいないときにはこの効果はない。",)
        return _check_form(attack, "相手の控えにもダメージを与えるワザ", damage="fixed") + _check_exact_text(attack, "相手の控えにもダメージを与えるワザ",
                                                                                                      expected)

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        bench = state.players[1 - use.player].bench
        return _decision_form(decision, _label(state, use), kind=SELECT_POKEMON, player=use.player, choices=(1, 1), options=(p.pokemon_id for p in bench))


@dataclass(frozen=True)
class SpreadDamage(AttackEffect):
    """相手の対戦ポケモンと相手の控えポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ ``damage`` ダメージ（v0.38。タケシのゴルバットの「かいてんひこう」。
    ダメージの目安の数字はない）。v0.31 のやきはらう（``CoinsDiscardThenSpreadDamage``）と同じ要素の組（``Damage(OPP, weakness_resistance=False)`` →
    ``BenchDamage``）で、量が決まっている形。相手の対戦ポケモンへのダメージはプラスパワー・ディフェンダーを計算し、控えへのダメージはプラスパワーを
    変えない（p.257）。"""

    damage: int
    implementation_id = "spread_damage"

    def __post_init__(self) -> None:
        _positive_tens(self.damage, "ダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = f"相手と相手の控えポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ{self.damage}ダメージ。"
        return _check_form(attack, "相手と相手の控え全員にダメージを与えるワザ", damage="none") + _check_exact_text(
            attack, "相手と相手の控え全員にダメージを与えるワザ", (expected,))


@dataclass(frozen=True)
class DamageThenCoinBenchDamageEitherSide(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを 1 枚投げ、「おもて」なら相手の控えポケモン全員に、「うら」なら自分の控えポケモン全員に、
    「弱点・抵抗力」に関係なく、それぞれ ``bench_damage`` ダメージ（v0.38。フリーザーの「ふぶき」）。

    - コインはワザ全体のコイン（``Coin``。1 枚。要素ごとに投げ直さない）。相手の対戦ポケモンへのダメージはコインによらない
    - 控えへのダメージは、相手の控えなら p.320 のダメージの (2)、自分の控えなら (4)（v0.33 のミニじしんと同じ計算）。自分の控えへのダメージは自分のワザの
      ダメージなので、受けた控えの「相手のワザによって」の効果ははたらかない
    - 自分にも相手にも控えポケモンがいなければ、このコインが決める要素のどれにも処理の対象がないので投げない（p.309。``Element.has_target``）。片方だけに
      いれば投げる（もう一方の面では何もしない）
    - 相手の対戦ポケモンが「ワザをうけない」状態でも、控えへのダメージは無効にならないので投げる（v0.34 の ``void_coin_question``）
    """

    bench_damage: int
    implementation_id = "damage_then_coin_bench_damage_either_side"

    def __post_init__(self) -> None:
        _positive_tens(self.bench_damage, "控えポケモンへのダメージ")

    def check(self, attack: Attack) -> list[str]:
        # v0.52: エリカのハクリューの「ふぶき」の書き方（「コインを投げ、」・かっこのない「「弱点・抵抗力」に関係なく、」）も受け付ける。どちらも 1 枚のコインの「おもて」で
        # 相手の控え全員・「うら」で自分の控え全員に、弱点・抵抗力を計算しないダメージを与える同じ意味（読点とかっこの違いだけ。docs/field-return-v0.52.md 5 章）
        accepted = (
            f"コインを投げて「おもて」なら相手の控えポケモン全員に、「うら」なら自分の控えポケモン全員に、(「弱点・抵抗力」に関係なく)それぞれ{self.bench_damage}ダメージ。",
            f"コインを投げ、「おもて」なら相手の控えポケモン全員に、「うら」なら自分の控えポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ{self.bench_damage}ダメージ。",
        )
        return _check_form(attack, "コインで相手か自分の控え全員にダメージを与えるワザ", damage="fixed") + _check_exact_text(
            attack, "コインで相手か自分の控え全員にダメージを与えるワザ", accepted)


@dataclass(frozen=True)
class CoinBonusDamageAndBenchDamage(AttackEffect):
    """コインを投げて「おもて」なら、相手に ``bonus`` ダメージを追加し、相手の控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ ``bench_damage``
    ダメージ（v0.38。カツラのギャロップの「ふみあらす」）。同じ 1 枚のコイン（``Coin``）が、追加のダメージ（p.321 の 1 段階）と控えへのダメージの両方を決める
    （投げ直さない）。相手の対戦ポケモンが「ダメージを受けない」「ワザをうけない」状態でも、控えへのダメージがあるので投げる（v0.34 の ``void_coin_question``）。
    相手に控えがいなければ、コインが決めるのは無効な追加のダメージだけなので、v0.4b の問い（``UNRESOLVED_PREVENTED_COIN_DAMAGE``）で宣言の前に止める（対象の
    ない要素は数えない。``Coin``）。"""

    bonus: int
    bench_damage: int
    implementation_id = "coin_bonus_damage_and_bench_damage"

    def __post_init__(self) -> None:
        _positive_tens(self.bonus, "追加のダメージ")
        _positive_tens(self.bench_damage, "控えポケモンへのダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = (f"コインを投げて「おもて」なら、相手に{self.bonus}ダメージを追加し、相手の控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ"
                    f"{self.bench_damage}ダメージ。")
        return _check_form(attack, "コインで追加のダメージと控えへのダメージを与えるワザ", damage="modified", modifier="+") + _check_exact_text(
            attack, "コインで追加のダメージと控えへのダメージを与えるワザ", (expected,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        attack = state.definitions[use.key.card_id].attacks[use.key.attack_index]
        return DamageProfile(opponent=(attack.damage, attack.damage + self.bonus))


@dataclass(frozen=True)
class DamageThenForceSwitchOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、相手の対戦ポケモンを控えポケモンと入れ替える。入れ替わる
    ポケモンは相手が選ぶ。相手に控えがいないときは入れ替えない（v0.38。アーボックの「いかくこうげき」）。

    - 入れ替えは v0.4d の「ふきとばし」と同じ要素 ``ForceSwitch``（相手が選ぶ。決定 ``FORCED_SWITCH``。ベンチにもどったポケモンの特殊状態・持続する効果は
      消える。ログ ``forced_switch``）に、この要素のコイン（``local_coin``）を加えた形
    - コインはダメージのあと（説明の順）。相手の対戦ポケモンがダメージで HP 以上になった・相手に控えがいないなら、入れ替えの対象がないので投げない（p.309。
      ログ ``forced_switch_skipped``）。コインは入れ替えだけを決めるので、「とうめい」で受けないと決まった相手には T19b、「ワザをうけない」相手には HC3 で
      止める（v0.31 の ``OpponentCannotAttack`` と同じ順番）
    """

    implementation_id = "damage_then_force_switch_on_heads"
    opponent_effect_elements = (FORCED_SWITCH_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        expected = ("コインを投げて「おもて」なら、相手の対戦ポケモンを控えポケモンと入れ替える。入れ替わるポケモンは相手プレイヤーが選ぶ。相手に控えポケモンが"
                    "いない時、この入れ替えは起こらない。")
        return _check_form(attack, "コインで相手を控えと入れ替えるワザ", damage="fixed") + _check_exact_text(attack, "コインで相手を控えと入れ替えるワザ",
                                                                                                  (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        return forced_switch_decision_problems(state, use, decision)


@dataclass(frozen=True)
class DamageThenForceSwitchThenSelfDamage(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。相手の対戦ポケモンを控えポケモンと入れ替える（控えポケモンは相手が選ぶ。控えがいないときは
    入れ替えない）。その後、自分にも ``self_damage`` ダメージ（v0.38。サイドンの「げきとつ」）。

    - 順番は説明のとおり: 相手へのダメージ → 入れ替え（相手の決定）→ 自分へのダメージ（「その後」。CR-ENERGY-CONVERSION-ORDER と同じく書かれた順。p.320）。
      入れ替えるのは相手の場なので、自分へのダメージを受けるのはワザを使ったポケモンのまま（入れ替えのあとも同じ）
    - 入れ替えは v0.4d の「ふきとばし」と同じ要素 ``ForceSwitch``。相手の対戦ポケモンがダメージで HP 以上になったら入れ替えない（p.309）が、自分へのダメージは
      与える。きぜつの判定はワザの要素をすべて処理したあと（p.309・p.324）
    - 相手へのダメージで「ダメージを受けたとき」の効果（はんげき・わるいねぞう・ほのおのかべ・こうらがえし）がはたらいたときは、その効果を処理する時点が
      決められない（ダメージの処理（自分へのダメージを含む）をすべてのせたあと、かつダメージ以外の効果の前、という記録の時点が、入れ替えをはさむこの並び
      にはない。GK1。``UNRESOLVED_DAMAGE_TRIGGER_TIMING``）ので、宣言の前に止める（先読みが見つける）
    """

    self_damage: int
    implementation_id = "damage_then_force_switch_then_self_damage"
    opponent_effect_elements = (FORCED_SWITCH_ELEMENT,)

    def __post_init__(self) -> None:
        _positive_tens(self.self_damage, "自分へのダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = (f"相手の対戦ポケモンを控えポケモンと入れ替える。控えポケモンは相手プレイヤーがえらぶ。相手プレイヤーに控えポケモンがいないときには入れ替えは"
                    f"おこらない。その後、自分にも{self.self_damage}ダメージ。")
        return _check_form(attack, "相手を控えと入れ替えたあと自分にもダメージを与えるワザ", damage="fixed") + _check_exact_text(
            attack, "相手を控えと入れ替えたあと自分にもダメージを与えるワザ", (expected,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        attack = state.definitions[use.key.card_id].attacks[use.key.attack_index]
        return DamageProfile(opponent=(attack.damage,), self_damage=(self.self_damage,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        return forced_switch_decision_problems(state, use, decision)


@dataclass(frozen=True)
class DamageThenSelfSwitchOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、自分の控えポケモンを 1 匹選び、このカードと入れ替える（v0.38。
    カツラのポニータの「けりにげ」）。

    - 入れ替えは v0.34 のテレポートと同じ要素 ``SelfSwitch``（ワザを使ったプレイヤーが選ぶ。決定 ``SELECT_POKEMON``。ポケモンいれかえと同じ処理。ベンチに
      もどったこのカードの特殊状態・持続する効果は消える）に、この要素のコイン（``local_coin``）を加えた形
    - コインはダメージのあと（説明の順）。自分への効果なので、相手が「ダメージを受けない」「ワザをうけない」状態でも投げる。自分に控えがいない・このカードが
      相手の「はんげき」などで HP 以上になったなら、処理の対象がないので投げない（p.309。CR-COUNTERATTACK-KO-ATTACKER）
    - 入れ替えでバトル場に出たポケモンは、このワザの残りの要素を受けない（入れ替えはワザの最後の要素）
    """

    implementation_id = "damage_then_self_switch_on_heads"

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「おもて」なら、自分の控えポケモンを1匹選び、このカードと入れ替える。"
        return _check_form(attack, "コインで自分の控えと入れ替えるワザ", damage="fixed") + _check_exact_text(attack, "コインで自分の控えと入れ替えるワザ",
                                                                                                  (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        bench = state.players[use.player].bench
        return _decision_form(decision, _label(state, use), kind=SELECT_POKEMON, player=use.player, choices=(1, 1), options=(p.pokemon_id for p in bench))


@dataclass(frozen=True)
class CoinBonusDamageAndSelfBarrier(AttackEffect):
    """コインを投げて「おもて」なら、``bonus`` ダメージを追加する。その場合、このカードは、次の相手の番、相手のワザによるダメージや効果を受けない（v0.38。キョウの
    ピジョンの「こうそくひこう」）。

    - 同じ 1 枚のコイン（``Coin``）が、追加のダメージ（p.321 の 1 段階）と自分への効果の両方を決める（「その場合」。投げ直さない）
    - 自分への効果は v0.31 のミュウツーの「バリアー」と同じ持続する効果 ``AttackBarrier``（次の相手の番に、このポケモンへのワザのダメージの要素と効果の要素は
      無効。期限・消える条件もバリアーと同じ）。v0.37 のカスミのコイキングの「しんだふり」と同じ書き方（「ワザによるダメージや効果を受けない」）
    - 相手の対戦ポケモンが「ダメージを受けない」「ワザをうけない」状態で、追加のダメージが無効になっても、自分への効果が残るので投げる（v0.34 の
      ``void_coin_question``）。このカードが相手の「はんげき」などで HP 以上になったら、自分への効果は与えない（p.309。ログ ``persistent_effect_skipped``）
    """

    bonus: int
    implementation_id = "coin_bonus_damage_and_self_barrier"

    def __post_init__(self) -> None:
        _positive_tens(self.bonus, "追加のダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = (f"コインを投げて「おもて」なら、{self.bonus}ダメージを追加する。その場合、このカードは、次の相手の番、相手のワザによるダメージや効果を"
                    "受けない。")
        return _check_form(attack, "コインで追加のダメージと次の相手の番にワザを受けない効果のワザ", damage="modified", modifier="+") + _check_exact_text(
            attack, "コインで追加のダメージと次の相手の番にワザを受けない効果のワザ", (expected,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        attack = state.definitions[use.key.card_id].attacks[use.key.attack_index]
        return DamageProfile(opponent=(attack.damage, attack.damage + self.bonus))


@dataclass(frozen=True)
class DamageThenPoisonOrParalyze(AttackEffect):
    """相手にダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら相手をどく状態に、「うら」ならマヒ状態にする（v0.38。キョウのビードルの
    「きけんなはり」）。v0.34 のくさいガス（``DamageThenPoisonOrConfuse``）と同じ要素 ``Status`` の ``otherwise``（1 枚のコイン。投げ直さない）で、「うら」が
    マヒ。マヒの再付与で回復する番が決まらない場合はコインの前に確かめる（v0.3b。この形のワザでは起こらない）。どちらの結果も相手への効果なので、「ワザを
    うけない」相手には HC3、「とうめい」で受けないと決まった相手には T19b。ダメージで HP 以上になったら投げない（p.309）。"""

    implementation_id = "damage_then_poison_or_paralyze"
    opponent_effect_elements = (POISON, PARALYSIS)

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「おもて」なら、相手を「どく」状態に、「うら」なら「マヒ」状態にする。"
        return _check_form(attack, "コインでどくかマヒになるワザ", damage="fixed") + _check_exact_text(attack, "コインでどくかマヒになるワザ", (expected,))


@dataclass(frozen=True)
class DamageAndSelfDamageThenPoisonOnHeads(AttackEffect):
    """相手にダメージの目安の数字ぶんのダメージ。自分にも ``self_damage`` ダメージ。コインを投げて「おもて」なら、相手をどく状態にする（v0.38。サカキのニドリーナの
    「どくばりタックル」）。

    - 順番は説明のとおり: 相手へのダメージ → 自分へのダメージ → 「ダメージを受けたとき」の効果（ダメージの処理をすべてのせたあと。CR-COUNTERATTACK-TIMING）→
      コイン → どく
    - コインはどくだけを決める（相手への効果）。相手が「ワザをうけない」状態なら HC3、「とうめい」で受けないと決まったら T19b（自分へのダメージはコインに
      よらないので、相手への効果が無効でもコインは投げるかが決められない）。相手がダメージで HP 以上になったら投げない（p.309）。このカードが自分へのダメージや
      相手の「はんげき」で HP 以上になっても、相手へのどくは処理する（CR-COUNTERATTACK-KO-ATTACKER）
    """

    self_damage: int
    implementation_id = "damage_and_self_damage_then_poison_on_heads"
    opponent_effect_elements = (POISON,)

    def __post_init__(self) -> None:
        _positive_tens(self.self_damage, "自分へのダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = f"自分にも{self.self_damage}ダメージ。コインを投げて「おもて」なら、相手を「どく」状態にする。"
        return _check_form(attack, "自分にもダメージを与えたあとコインでどくにするワザ", damage="fixed") + _check_exact_text(
            attack, "自分にもダメージを与えたあとコインでどくにするワザ", (expected,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        attack = state.definitions[use.key.card_id].attacks[use.key.attack_index]
        return DamageProfile(opponent=(attack.damage,), self_damage=(self.self_damage,))


@dataclass(frozen=True)
class DamageThenReduceDamageNextTurn(AttackEffect):
    """相手にダメージの目安の数字ぶんのダメージ。次の相手の番、このカードがワザによって受けるダメージは ``amount`` へる（v0.38。ナツメのポリゴンの
    「バリアアタック」の「「-10」される」）。効果は v0.31 のピクシーの「ちいさくなる」と同じ持続する効果 ``DamageReduction``（p.321 の 8 段階。ワザのダメージ
    だけ。こんらんの 20・どくのダメージは変えない。期限は次の相手の番の終わり。ベンチにもどる・進化・きぜつで消える）。このカードが相手の「はんげき」などで
    HP 以上になったら与えない（p.309。ログ ``persistent_effect_skipped``）。"""

    amount: int
    implementation_id = "damage_then_reduce_damage_next_turn"

    def __post_init__(self) -> None:
        _positive_tens(self.amount, "へらすダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = f"次の相手の番、このカードがワザによって受けるダメージは「-{self.amount}」される。"
        return _check_form(attack, "ダメージのあと次の相手の番に受けるダメージがへるワザ", damage="fixed") + _check_exact_text(
            attack, "ダメージのあと次の相手の番に受けるダメージがへるワザ", (expected,))


DISCARD_ATTACHED_RETURN_TEXT = "このカードにのっているダメージカウンターをすべてとりのぞき、ついているカードをすべてトラッシュする。その後、このカードを山札にもどし、その山札をよく切る。"


@dataclass(frozen=True)
class DiscardAttachedAndReturnSelfToDeck(AttackEffect):
    """このカードにのっているダメージカウンターをすべてとりのぞき、ついているカードをすべてトラッシュする。その後、このカードを山札にもどし、その山札をよく切る
    （v0.38。ケーシィ（PMCG4-031）の「いなくなる」）。

    - 順番は説明のとおり: ダメージカウンターをとりのぞく（ログ ``remove_all_damage_counters``）→ ついているカード（エネルギー・トレーナー）をトラッシュ
      （``zones.discard_attached_cards``）→ このカードを山札にもどす（``zones.return_in_play_to_deck``。進化していれば重なったカードも。v0.36 の RD2）→ 山札を
      切る（1 回）。キョウのドガースの「くもがくれガス」・キョウのポッポの「でんれい」（ついているカードも山札にもどす）とは、ついているカードの行き先が違う
    - きぜつではない（サイドは取られない）。バトル場が空くので、ワザのあとの勝ち負けの判定（控えがいなければ負け。p.311）とバトル場に出す決定は、v0.36 の
      くもがくれガスと同じきぜつのあとの処理。持続する効果は理由 ``return_in_play_to_deck`` で消える
    """

    implementation_id = "discard_attached_and_return_self_to_deck"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "ついているカードをトラッシュして自分を山札にもどすワザ", damage="none") + _check_exact_text(
            attack, "ついているカードをトラッシュして自分を山札にもどすワザ", (DISCARD_ATTACHED_RETURN_TEXT,))


def deck_pokemon_candidates(state: GameState, player: int, excluded: tuple[str, ...]) -> list[int]:
    """``player`` の山札のポケモンのカード（たねポケモン・進化カード）のうち、名前（``name_ja``）が ``excluded`` のどれでもないもの（v0.38。キョウのポッポの
    「でんれい」の「「キョウのポッポ」以外の「ポケモン」」。uid の小さい順。山札の並びを写さない）。名前の完全一致で除く（同じ名前の別のカードはどれも除く）。"""
    return sorted(uid for uid in state.players[player].deck
                  if state.card_def(uid).category == "pokemon" and state.card_def(uid).name_ja not in excluded)


@dataclass(frozen=True)
class ReturnSelfToDeckThenSearchPokemon(AttackEffect):
    """自分と、自分についているすべてのカードを山札にもどす。(ベンチから、かわりの対戦ポケモンを出す)。その後、自分の山札から名前が ``excluded`` 以外の「ポケモン」を
    1 枚選び出し、相手に見せてから手札に加え、その山札をよく切る（v0.38。キョウのポッポ（PMCG6-067）の「でんれい」）。

    - 順番は説明のとおり: 山札にもどす（v0.36 のくもがくれガスと同じ ``zones.return_in_play_to_deck``。ここでは切らない）→ 控えから対戦ポケモンを出す（ワザを
      使ったプレイヤーが選ぶ。``PromoteFromBench``。控えがいなければ出せず、ワザのあとの勝ち負けの判定で負け）→ 山札をさがす（決定 ``SEARCH_DECK``。見せて手札に
      加える。ログ ``reveal_from_deck``）→ 山札を切る（1 回だけ）。説明にない途中のシャッフルはしない
    - ワザを使ったポケモンは場をはなれているので、そのあとの決定（出すポケモン・さがすカード）は、場にいないポケモンのワザの続き（不変条件は今の番のログの
      ``return_in_play_to_deck`` で確かめる。``engine._attack_decision_problems``）
    - 選べるものがない（山札が 0 枚を含む）なら加えずに切る（p.309。v0.32 のなかまをよぶと同じ読み方）。きぜつではない（サイドは取られない）
    """

    excluded: tuple[str, ...]
    implementation_id = "return_self_to_deck_then_search_pokemon"
    leaves_play_before_decisions: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if type(self.excluded) is not tuple or not self.excluded or not all(type(name) is str and name for name in self.excluded):
            raise ValueError(f"除く名前は 1 つ以上の文字列のタプル（{self.excluded!r}）")

    def check(self, attack: Attack) -> list[str]:
        names = "・".join(f"「{name}」" for name in self.excluded)
        expected = (f"自分と、自分についているすべてのカードを山札にもどす。(ベンチから、かわりの対戦ポケモンを出す)。その後、自分の山札から{names}以外の「ポケモン」を"
                    "1枚選び出し、相手に見せてから手札に加え、その山札をよく切る。")
        return _check_form(attack, "自分を山札にもどして山札からポケモンを手札に加えるワザ", damage="none") + _check_exact_text(
            attack, "自分を山札にもどして山札からポケモンを手札に加えるワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        if decision.kind == SELECT_POKEMON:
            p = state.players[use.player]
            problems = _decision_form(decision, _label(state, use), kind=SELECT_POKEMON, player=use.player, choices=(1, 1),
                                      options=(pokemon.pokemon_id for pokemon in p.bench))
            if p.active is not None:
                problems.append("かわりの対戦ポケモンを出す決定なのに、バトル場が空いていない")
            return problems
        return _decision_form(decision, _label(state, use), kind=SEARCH_DECK, player=use.player, choices=(1, 1),
                              options=deck_pokemon_candidates(state, use.player, self.excluded))


# ---------------------------------------------------------------- v0.39（docs/selfdestruct-spread-count-v0.39.md）
# じばく・控えへのダメージ・場のポケモンの数でダメージが決まるワザ。どれも既存の要素（``resolution.programs``）の組み合わせで、要素の項目（``BenchDamage`` の
# ``same_type_as_opponent_active``・``exclude_type``・``ChosenBenchDamage`` の ``weakness_resistance`` の None）と、要素 ``ChosenBenchDamages``・値
# ``PrintedPlusPokemonCount`` を加えた。説明の文面は、登録したワザの印刷の文面と完全に同じものだけを受け付ける


SELF_DESTRUCT_TEXTS = {
    # 第1弾のコイル・レアコイル。自分と相手に同じダメージ。控えへのダメージに弱点・抵抗力を書かない（JS1）
    False: lambda damage, self_damage, bench: (f"自分と相手に{damage}ダメージをあたえ、お互いの控えポケモン全員にも{bench}ダメージ。",)
    if self_damage == damage else (),
    # 化石の秘密のマタドガス・レアコイル。控えへのダメージは「弱点・抵抗力」に関係なく
    True: lambda damage, self_damage, bench: (f"自分にも{self_damage}ダメージ。お互いの控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ{bench}ダメージ。",),
}


@dataclass(frozen=True)
class SelfDestruct(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ、自分（ワザを使ったポケモン）に ``self_damage``、お互いの控えポケモン全員にそれぞれ ``bench_damage``
    （v0.39。「じばく」。第1弾のコイル・レアコイルと化石の秘密のマタドガス・レアコイル）。

    - 要素の並び: 相手へのダメージ → 自分へのダメージ → 相手の控え全員 → 自分の控え全員。どれもダメージの要素で、その間に効果の要素はない（GK1 の並びではない）。
      「ダメージを受けたとき」の効果は、すべてのダメージをのせたあとに処理する（CR-COUNTERATTACK-TIMING）。並びの順で結果は変わらない（きぜつはワザのあとに
      まとめて判定し、受けるポケモンはどれも別。「とうめい」が 2 匹以上なら T27、送る効果が 2 つ以上なら C34・C35 で止まる）
    - 自分へのダメージはワザによるダメージで、弱点・抵抗力はワザを使うポケモンのタイプと自分の弱点・抵抗力（v0.3d）。残りの HP に関係なく自分をきぜつさせる
      処理ではない（HP 未満なら残る）
    - ``weakness_resistance_stated``: 化石の秘密の 2 枚は、控えへのダメージに「弱点・抵抗力」に関係なくと書く（計算しない）。第1弾の 2 枚は書かないので、
      v0.37 の JS1 と同じ問い（``BenchDamage`` の ``weakness_resistance`` が None。お互いの控えのどれかで読み方によって受けるダメージが変わるときだけ、宣言の前に
      止める）。控えへのダメージはプラスパワーを変えず、ディフェンダーは変える（p.257・v0.33）
    - きぜつ・サイド・勝ち負け・バトル場に出すのは、ワザのあとに今までどおり（同時のきぜつ。p.324。番でないプレイヤーが先に出す）
    """

    self_damage: int
    bench_damage: int
    weakness_resistance_stated: bool
    implementation_id = "self_destruct"

    def __post_init__(self) -> None:
        _positive_tens(self.self_damage, "自分へのダメージ")
        _positive_tens(self.bench_damage, "控えポケモンへのダメージ")

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "じばく", damage="fixed")
        if problems:
            return problems
        accepted = SELF_DESTRUCT_TEXTS[self.weakness_resistance_stated](attack.damage, self.self_damage, self.bench_damage)
        if not accepted:
            return [f"自分と相手に同じダメージを与える書き方なのに、自分へのダメージ {self.self_damage} が目安の数字 {attack.damage} と違う"]
        return _check_exact_text(attack, "じばく", accepted)

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        attack = state.definitions[use.key.card_id].attacks[use.key.attack_index]
        return DamageProfile(opponent=(attack.damage,), self_damage=(self.self_damage,))


@dataclass(frozen=True)
class DamageIgnoringWeaknessResistance(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。そのダメージは相手の弱点・抵抗力の影響を受けない（v0.39。化石の秘密のレアコイルの「ソニックブーム」
    「この「ソニックブーム」のダメージは、相手の「弱点・抵抗力」の影響を受けない。」）。

    - 要素は ``Damage(OPP, weakness_resistance=False)``（v0.31 のやきはらう・v0.38 のかいてんひこうの相手の対戦ポケモンへのダメージと同じ）。計算しないのは p.321 の
      3・4 段階（弱点・抵抗力）だけで、ワザを使うポケモンへの効果（2 段階）・プラスパワー（5 段階）・ディフェンダー（7 段階）・受けるポケモンへの効果（8 段階）・
      「ダメージを受けない」「ワザをうけない」状態・「とうめい」・「ダメージを受けたとき」の効果は今までどおり
    - 説明の「」の中はワザ自身の名前（登録のワザの名前と照らす）
    """

    implementation_id = "damage_ignoring_weakness_resistance"

    def check(self, attack: Attack) -> list[str]:
        # v0.42: わるいユンゲラー・わるいフーディンの「マインドショック」の書き方（「このワザのダメージは」。「この「ソニックブーム」の」と同じく、このワザ自身の
        # ダメージを指す）も受け付ける
        expected = (f"この「{attack.name_ja}」のダメージは、相手の「弱点・抵抗力」の影響を受けない。",
                    "このワザのダメージは、相手の「弱点・抵抗力」の影響を受けない。")
        return _check_form(attack, "弱点・抵抗力の影響を受けないワザ", damage="fixed") + _check_exact_text(attack, "弱点・抵抗力の影響を受けないワザ", expected)


@dataclass(frozen=True)
class DamageThenChosenBenchTargets(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。相手の控えポケモンから最大 ``max_targets`` 匹を選び、「弱点・抵抗力」に関係なく、それぞれ
    ``bench_damage`` ダメージ（v0.39。ライチュウ（PMCG3-024）の「ギガスパーク」）。選ぶのはワザを使ったプレイヤー。1 匹以上なら最大より少なくてもよい。
    0 匹は GS1（``UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE``。答えのときに止め、決定は待ったまま）。控えがいなければ何もしない（p.309）。要素 ``ChosenBenchDamages``。"""

    max_targets: int
    bench_damage: int
    implementation_id = "damage_then_chosen_bench_targets"

    def __post_init__(self) -> None:
        if type(self.max_targets) is not int or self.max_targets < 2:
            raise ValueError(f"選ぶ数の最大は 2 以上（{self.max_targets!r}）")
        _positive_tens(self.bench_damage, "控えポケモンへのダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = f"相手の控えポケモンから最大{self.max_targets}匹を選び、「弱点・抵抗力」に関係なく、それぞれ{self.bench_damage}ダメージ。"
        return _check_form(attack, "相手の控えを何匹か選んでダメージを与えるワザ", damage="fixed") + _check_exact_text(
            attack, "相手の控えを何匹か選んでダメージを与えるワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        bench = state.players[1 - use.player].bench
        return _decision_form(decision, _label(state, use), kind=SELECT_POKEMON, player=use.player, choices=(0, min(self.max_targets, len(bench))),
                              options=(p.pokemon_id for p in bench))


@dataclass(frozen=True)
class DamageThenSameTypeBenchDamage(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。相手の対戦ポケモンと同じタイプの、お互いの控えポケモン全員にそれぞれ ``bench_damage``（v0.39。
    マルマインの「ビリビリ」「相手の対戦ポケモンと同じ色の控えポケモン全員にそれぞれ10ダメージ。(自分の控えポケモンも含まれる)」）。

    - タイプは控えへのダメージを処理する時点の、相手の対戦ポケモンのいちばん上のカードのタイプ（「色」= タイプ）。受ける控えのタイプも、いちばん上のカード
    - 説明が控えへのダメージの弱点・抵抗力について書いていないので、v0.37 の JS1 と同じ問い（お互いの控えのどれかで読み方によって受けるダメージが変わるとき
      だけ、宣言の前に止める）
    """

    bench_damage: int
    implementation_id = "damage_then_same_type_bench_damage"

    def __post_init__(self) -> None:
        _positive_tens(self.bench_damage, "控えポケモンへのダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = f"相手の対戦ポケモンと同じ色の控えポケモン全員にそれぞれ{self.bench_damage}ダメージ。(自分の控えポケモンも含まれる)"
        return _check_form(attack, "相手の対戦ポケモンと同じタイプの控えにダメージを与えるワザ", damage="fixed") + _check_exact_text(
            attack, "相手の対戦ポケモンと同じタイプの控えにダメージを与えるワザ", (expected,))


@dataclass(frozen=True)
class DamageThenCoinBenchDamageBothSides(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、お互いの控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ
    ``bench_damage``（v0.39。キョウのドガース（PMCG6-008）の「おならガス」）。v0.38 のふぶき（「おもて」なら相手、「うら」なら自分の控え）と同じワザ全体のコイン
    （1 枚。要素ごとに投げ直さない）。お互いに控えがいなければ、このコインが決める要素に対象がないので投げない（v0.38 の ``has_target``）。相手の対戦ポケモンが
    「ワザをうけない」状態でも、控えへのダメージは無効にならないので投げる（v0.34 の ``void_coin_question``）。"""

    bench_damage: int
    implementation_id = "damage_then_coin_bench_damage_both_sides"

    def __post_init__(self) -> None:
        _positive_tens(self.bench_damage, "控えポケモンへのダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = f"コインを投げて「おもて」なら、お互いの控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ{self.bench_damage}ダメージ。"
        return _check_form(attack, "コインでお互いの控え全員にダメージを与えるワザ", damage="fixed") + _check_exact_text(
            attack, "コインでお互いの控え全員にダメージを与えるワザ", (expected,))


@dataclass(frozen=True)
class DamageThenOtherTypeBenchDamageBothSides(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。お互いのベンチにいる、``excluded_type`` のポケモン以外のポケモン全員にも、「弱点・抵抗力」に関係なく、
    それぞれ ``bench_damage``（v0.39。カスミのニョロボンの「ウォーターリング」）。受ける控えのタイプは、いちばん上のカードのタイプ。"""

    excluded_type: EnergyType
    bench_damage: int
    implementation_id = "damage_then_other_type_bench_damage_both_sides"

    def __post_init__(self) -> None:
        _positive_tens(self.bench_damage, "控えポケモンへのダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = f"お互いのベンチにいる、「{self.excluded_type.ja}」ポケモン以外のポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ{self.bench_damage}ダメージ。"
        return _check_form(attack, "お互いの控えのあるタイプ以外にダメージを与えるワザ", damage="fixed") + _check_exact_text(
            attack, "お互いの控えのあるタイプ以外にダメージを与えるワザ", (expected,))


POKEMON_COUNT_TEXTS = {
    # (数える範囲, 名前) → 説明の書き方（per はダメージ）
    ("own_bench", None): lambda per: (f"自分の控えポケモンの数×{per}ダメージを追加する。",),
    ("own_in_play", ("ニドキング",)): lambda per: (f"自分の場に出ている「ニドキング」の数×{per}のダメージを追加する。",),
    ("own_bench", ("コイル", "レアコイル", "わるいレアコイル")): lambda per: (
        f"自分のベンチにいる「コイル」「レアコイル」「わるいレアコイル」1匹につき、{per}ダメージを追加する。",),
}


@dataclass(frozen=True)
class DamagePlusPokemonCount(AttackEffect):
    """ダメージの目安の数字 + 自分の場のポケモンの数 × ``per`` の基本となるダメージ（p.321 の 1 段階。v0.39。プクリンの「ともだちのわ」・ニドクインの「ラブラブ
    アタック」・コイル（PMCG4-026）の「ちょくれつじりょく」）。値 ``programs.PrintedPlusPokemonCount``。

    - ``scope``: ``"own_bench"``（自分のベンチ）・``"own_in_play"``（自分の場（バトル場とベンチ））。``names``: 数えるポケモンの名前（いちばん上のカードの名前の完全
      一致。None ならすべて）。進化して重なったカードは 1 匹と数える。名前の一部・収録の弾では見ない（「マチスのコイル」は「コイル」ではない）
    - 弱点・抵抗力・プラスパワー・ディフェンダーなどは、そのあとの段階で計算する。実際の処理と先読み（どの方法も）は同じ値を使う
    - 説明の名前の一覧に対応していないカードの名前（「わるいレアコイル」）があっても、名前のまま数える（そのカードは場に出ないので、今は数に入らない）
    """

    per: int
    scope: str
    names: tuple[str, ...] | None = None
    implementation_id = "damage_plus_pokemon_count"

    def __post_init__(self) -> None:
        _positive_tens(self.per, "1 匹あたりのダメージ")
        if (self.scope, self.names) not in POKEMON_COUNT_TEXTS:
            raise ValueError(f"数える範囲と名前の組 {(self.scope, self.names)!r} の書き方がない")

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "場のポケモンの数でダメージを追加するワザ", damage="modified", modifier="+") + _check_exact_text(
            attack, "場のポケモンの数でダメージを追加するワザ", POKEMON_COUNT_TEXTS[(self.scope, self.names)](self.per))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        from .resolution.programs import counted_pokemon

        attack = state.definitions[use.key.card_id].attacks[use.key.attack_index]
        return DamageProfile(opponent=(attack.damage + len(counted_pokemon(state, use.player, self.scope, self.names)) * self.per,))


@dataclass(frozen=True)
class CoinBonusDamageAndSelfDamage(AttackEffect):
    """コインを投げて「おもて」なら、``bonus`` ダメージを追加して、自分にも ``self_damage``（v0.39。キョウのマタドガスの「とつぜんばくはつ」）。同じ 1 枚のコイン
    （``Coin``）が追加のダメージ（p.321 の 1 段階）と自分へのダメージを決める（投げ直さない）。「うら」なら目安の数字ぶんだけで、自分へのダメージはない。
    相手が「ダメージを受けない」「ワザをうけない」状態で追加のダメージが無効でも、自分へのダメージが残るので投げる（v0.34 の ``void_coin_question``）。"""

    bonus: int
    self_damage: int
    implementation_id = "coin_bonus_damage_and_self_damage"

    def __post_init__(self) -> None:
        _positive_tens(self.bonus, "追加のダメージ")
        _positive_tens(self.self_damage, "自分へのダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = f"コインを投げて「おもて」なら、{self.bonus}ダメージを追加して、自分にも{self.self_damage}ダメージ。"
        return _check_form(attack, "コインで追加のダメージと自分へのダメージのワザ", damage="modified", modifier="+") + _check_exact_text(
            attack, "コインで追加のダメージと自分へのダメージのワザ", (expected,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        attack = state.definitions[use.key.card_id].attacks[use.key.attack_index]
        return DamageProfile(opponent=(attack.damage, attack.damage + self.bonus), self_damage=(0, self.self_damage),
                             outcomes=((attack.damage, 0), (attack.damage + self.bonus, self.self_damage)))


@dataclass(frozen=True)
class DamageThenSpecialPoisonOnHeads(AttackEffect):
    """相手にダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、相手を、ポケモンチェックで ``poison_damage`` の「どく」ダメージを受けるどく状態に
    する（v0.39。キョウのマタドガスの「どくどくガス」）。v0.34 のニドキングの「どくどく」と同じ特殊などく（``Status`` の ``poison_damage``。通常のどくを 2 回
    付けない）に、この要素のコインを加えた形。受けるダメージの違うどく状態のポケモンへの特殊などくは TP3（``UNRESOLVED_SPECIAL_POISON_OVERWRITE``。コインの前に聞く
    ので、どちらの結果でも宣言の前に止まる）。コインはどくだけを決めるので、「ワザをうけない」相手には HC3、「とうめい」で受けないと決まった相手には T19b。ダメージで
    HP 以上なら投げない（p.309）。"""

    poison_damage: int
    implementation_id = "damage_then_special_poison_on_heads"
    opponent_effect_elements = (POISON,)

    def __post_init__(self) -> None:
        if type(self.poison_damage) is not int or self.poison_damage <= 10 or self.poison_damage % 10:
            raise ValueError(f"特殊などくのダメージは 10 の倍数で 10 より大きい（{self.poison_damage!r}）")

    def check(self, attack: Attack) -> list[str]:
        expected = (f"コインを投げて「おもて」なら、相手を「どく」状態にする。このワザによって「どく」状態になったポケモンがポケモンチェックで受ける「どく」の"
                    f"ダメージは、{self.poison_damage}ダメージ。")
        return _check_form(attack, "コインで特殊などくにするワザ", damage="fixed") + _check_exact_text(attack, "コインで特殊などくにするワザ", (expected,))


@dataclass(frozen=True)
class CoinPoisonAndBenchDamage(AttackEffect):
    """コインを投げて「おもて」なら、相手をどく状態にして、相手の控えポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ ``bench_damage``（v0.39。エリカのパラスの
    「きけんなほうし」。ダメージの目安の数字はない）。

    - 同じ 1 枚のコイン（``Coin``）がどくと控えへのダメージの両方を決める（投げ直さない）
    - 処理の順番は、ダメージの処理（控えへのダメージ）→ それ以外の効果（どく）（p.309 の手順 6「まず、ダメージの処理をおこない、次に「それ以外の効果」を処理して
      ください」。v0.4d の記録）。受けるポケモンはどれも別で、順番で結果は変わらない
    - 一方だけが無効・対象なし: 相手に控えがいなければ控えへのダメージは対象がない（コインはどくのために投げる）。相手の対戦ポケモンが「ワザをうけない」状態なら
      どくは無効だが、控えへのダメージがあれば投げる。どちらも残らない（控えがなく、相手が「ワザをうけない」状態）なら、投げるかが決められない（HC3）
    """

    bench_damage: int
    implementation_id = "coin_poison_and_bench_damage"
    opponent_effect_elements = (POISON,)

    def __post_init__(self) -> None:
        _positive_tens(self.bench_damage, "控えポケモンへのダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = f"コインを投げて「おもて」なら、相手を「どく」状態にして、相手の控えポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ{self.bench_damage}ダメージ。"
        return _check_form(attack, "コインでどくと控えへのダメージのワザ", damage="none") + _check_exact_text(attack, "コインでどくと控えへのダメージのワザ",
                                                                                                    (expected,))



# ---------------------------------------------------------------- v0.40（docs/count-condition-switch-return-v0.40.md）
# 場の数・条件付きの効果・入れ替え・カードの移動。要素（``resolution.programs``）の組み合わせと、v0.40 の要素（``BenchFromDeckAny``・``PokemonCountTimes``・
# ``TailsOfOpponentBenchCoins``・``OwnCountersAtLeast``・``PrintedPlusBonusIfDefenderDamaged``・``OpponentAttackLockWhileSourceActive``・``AmountIfOwnBenchNamed``・
# ``ReturnOpponentToDeck``・``PrintedPlusBonusOnAllHeads``・``ShuffleDeck``）。説明の文面は、登録したワザの印刷の文面（kyuura の写し）と完全に同じものだけを受け付ける


def _counts_and_space(state: GameState, player: int, names: tuple[str, ...]) -> tuple[list[int], int]:
    candidates = bench_from_deck_candidates(state, player, names)
    return candidates, state.rules.max_bench - len(state.players[player].bench)


@dataclass(frozen=True)
class GroupAttackFromDeck(AttackEffect):
    """自分の場にいる「``names``」の数 × ``per`` のダメージ。のぞむなら、ダメージを与える前に、自分の山札から「``names``」を好きなだけ選び出し、ベンチに出してよい。
    その場合は、その山札をよく切る（v0.40。キョウのズバットの「むれでおそう」）。

    要素は ``BenchFromDeckAny``（決定 ``BENCH_FROM_DECK``。0〜min(ベンチの空き, 山札の選べるたねポケモンの数) 枚。出したら 1 回だけ切る）→ ``Damage``（``PokemonCountTimes``。
    出したあとの自分の場の数）。ダメージの目安「10×」の数字が 1 匹あたりのダメージ。"""

    names: tuple[str, ...]
    per: int
    implementation_id = "group_attack_from_deck"

    def __post_init__(self) -> None:
        _positive_tens(self.per, "1 匹あたりのダメージ")
        if len(self.names) != 1:
            raise ValueError(f"数えて山札から出すポケモンの名前は 1 つ（{self.names!r}）")

    def check(self, attack: Attack) -> list[str]:
        name = self.names[0]
        expected = (f"自分の場にいる「{name}」の数×{self.per}ダメージ。のぞむなら、ダメージを与える前に、自分の山札から「{name}」を好きなだけ選び出し、ベンチに"
                    f"出してよい。その場合は、その山札をよく切る。")
        problems = _check_form(attack, "山札から出して場の数でダメージのワザ", damage="modified", modifier="×")
        if attack.damage != self.per:
            problems.append(f"ダメージの目安の数字 {attack.damage!r} と、1 匹あたりのダメージ {self.per} が違う")
        return problems + _check_exact_text(attack, "山札から出して場の数でダメージのワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        candidates, space = _counts_and_space(state, use.player, self.names)
        return _decision_form(decision, _label(state, use), kind=BENCH_FROM_DECK, player=use.player, choices=(0, min(space, len(candidates))),
                              options=candidates)

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        from .resolution.programs import SCOPE_OWN_IN_PLAY, counted_pokemon

        candidates, space = _counts_and_space(state, use.player, self.names)
        now = len(counted_pokemon(state, use.player, SCOPE_OWN_IN_PLAY, self.names))
        return DamageProfile(opponent=tuple((now + added) * self.per for added in range(min(max(space, 0), len(candidates)) + 1)))


EXPLOSION_TEXT = ("お互いの場にいるすべての{names}の数×{per}のダメージ。その後、お互いの場にいる全ての{names}に、それぞれ{each}ダメージ。")


@dataclass(frozen=True)
class NamedPokemonExplosion(AttackEffect):
    """お互いの場にいるすべての「``names``」の数 × ``per`` のダメージ。その後、お互いの場にいる全ての「``names``」に、それぞれ ``each`` ダメージ（v0.40。わるいマタドガスの
    「みんなでばくはつ」）。v0.39 のじばく（``SelfDestruct``）とは別の型（受けるのは名前の合うポケモンだけで、ワザを使ったポケモンも名前が合えば受ける）。

    - 相手の対戦ポケモンへの数 × ``per``（p.320 のダメージの (1)。弱点・抵抗力を計算する。数はダメージの要素を処理する時点のお互いの場。``PokemonCountTimes``）
    - その後の ``each``: 名前の合う相手の対戦ポケモン（(1)。もう一度ダメージの要素を受ける）→ 名前の合う自分（(3)。自分へのダメージの計算。v0.2f・v0.3d）→ 名前の合う
      相手の控え（(2)）→ 名前の合う自分の控え（(4)）。控えへのダメージは説明が弱点・抵抗力について書いていないので、計算するかで最終ダメージが変わる控えが
      あれば v0.37 の JS1（``bench_damage_weakness_resistance``）で宣言の前に止める（英語版の「Don't apply Weakness and Resistance」では決めない）
    - きぜつの処理はワザのあと（すべてのダメージをのせてから。p.309）。同時にきぜつしたポケモンのサイド・バトル場に出す順番は今までどおり
    """

    names: tuple[str, ...]
    per: int
    each: int
    implementation_id = "named_pokemon_explosion"

    def __post_init__(self) -> None:
        _positive_tens(self.per, "1 匹あたりのダメージ")
        _positive_tens(self.each, "それぞれへのダメージ")
        if not self.names:
            raise ValueError("数えるポケモンの名前がない")

    def check(self, attack: Attack) -> list[str]:
        names = "".join(f"「{name}」" for name in self.names)
        expected = EXPLOSION_TEXT.format(names=names, per=self.per, each=self.each)
        problems = _check_form(attack, "お互いの場の数でダメージと、それぞれへのダメージのワザ", damage="modified", modifier="×")
        if attack.damage != self.per:
            problems.append(f"ダメージの目安の数字 {attack.damage!r} と、1 匹あたりのダメージ {self.per} が違う")
        return problems + _check_exact_text(attack, "お互いの場の数でダメージと、それぞれへのダメージのワザ", (expected,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        from .resolution.programs import SCOPE_BOTH_IN_PLAY, counted_pokemon

        _, attacker = state.find_pokemon(use.pokemon_id)
        own = self.each if form_def(state, attacker).name_ja in self.names else 0  # v0.49: 今の姿の名前
        return DamageProfile(opponent=(len(counted_pokemon(state, use.player, SCOPE_BOTH_IN_PLAY, self.names)) * self.per,), self_damage=(own,))


@dataclass(frozen=True)
class OpponentFlipsTailsDamage(AttackEffect):
    """相手プレイヤーに、相手の控えポケモンの数だけコインを投げさせ、「うら」が出た数 × ``per`` のダメージ。このワザのダメージは相手の「弱点・抵抗力」の影響を受けない
    （v0.40。わるいスリーパーの「ベンチをあやつる」）。要素は ``Damage``（``TailsOfOpponentBenchCoins``。投げるのは相手、使うのは「うら」の数、``weakness_resistance``
    は False（p.321 の 3・4 段階だけを計算しない。v0.39 のソニックブームと同じ。プラスパワー・ディフェンダー・「ダメージを受けない」状態・「とうめい」はそのまま））。"""

    per: int
    implementation_id = "opponent_flips_tails_damage"

    def __post_init__(self) -> None:
        _positive_tens(self.per, "「うら」1 枚あたりのダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = (f"相手プレイヤーに、相手の控えポケモンの数だけコインを投げさせ、「うら」が出た数×{self.per}のダメージ(このワザのダメージは相手の「弱点・抵抗力」の"
                    "影響を受けない)")
        problems = _check_form(attack, "相手が投げるコインの「うら」の数でダメージのワザ", damage="modified", modifier="×")
        if attack.damage != self.per:
            problems.append(f"ダメージの目安の数字 {attack.damage!r} と、「うら」1 枚あたりのダメージ {self.per} が違う")
        return problems + _check_exact_text(attack, "相手が投げるコインの「うら」の数でダメージのワザ", (expected,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        bench = len(state.players[1 - use.player].bench)
        return DamageProfile(opponent=tuple(tails * self.per for tails in range(bench + 1)))


@dataclass(frozen=True)
class DamageRequiringOwnCounters(AttackEffect):
    """「このワザは、自分にダメージカウンターが ``minimum`` つ以上のっているときだけ、使える。」（v0.40。サカキのニドラン♂の「いかりのいちげき」）。ダメージの目安の
    数字ぶんのダメージ。条件はワザを使うための条件（``usage_problem``。必要なエネルギーの確認のあと・こんらんのコインの前。``NOT_ENOUGH_DAMAGE_COUNTERS``。
    拒否では状態・乱数・ログを変えない）。数えるのはワザを使うポケモン自身のダメージカウンター（ダメージ ÷ 10）。"""

    minimum: int
    implementation_id = "damage_requiring_own_counters"

    def __post_init__(self) -> None:
        if type(self.minimum) is not int or self.minimum < 1:
            raise ValueError(f"必要なダメージカウンターの数は 1 以上の整数（{self.minimum!r}）")

    def check(self, attack: Attack) -> list[str]:
        expected = f"このワザは、自分にダメージカウンターが{self.minimum}つ以上のっているときだけ、使える。"
        return _check_form(attack, "ダメージカウンターが条件のワザ", damage="fixed") + _check_exact_text(attack, "ダメージカウンターが条件のワザ", (expected,))

    def usage_problem(self, state: GameState, attacker: PokemonInPlay) -> IllegalActionError | None:
        counters = attacker.damage // state.rules.damage_per_counter
        if counters < self.minimum:
            return IllegalActionError("NOT_ENOUGH_DAMAGE_COUNTERS",
                                      f"自分にダメージカウンターが {self.minimum} つ以上のっていない（{counters} 個）ので、このワザは使えない（ワザの説明）")
        return None


@dataclass(frozen=True)
class DamagePlusIfDefenderDamaged(AttackEffect):
    """このワザを使う時、すでに相手（相手の対戦ポケモン）にダメージカウンターがのっているなら、``bonus`` ダメージを追加する（v0.40。サカキのニドリーノの「つのでえぐる」。
    値 ``PrintedPlusBonusIfDefenderDamaged``。のっているかだけを見る（数に比例しない））。"""

    bonus: int
    implementation_id = "damage_plus_if_defender_damaged"

    def __post_init__(self) -> None:
        _positive_tens(self.bonus, "追加のダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = f"このワザを使う時、すでに相手にダメージカウンターがのっているなら、{self.bonus}ダメージを追加する。"
        return _check_form(attack, "相手のダメージカウンターで追加ダメージのワザ", damage="modified", modifier="+") + _check_exact_text(
            attack, "相手のダメージカウンターで追加ダメージのワザ", (expected,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        attack = state.definitions[use.key.card_id].attacks[use.key.attack_index]
        damaged = state.players[1 - use.player].active.damage > 0
        return DamageProfile(opponent=(attack.damage + (self.bonus if damaged else 0),))


@dataclass(frozen=True)
class AttackLockWhileSourceActive(AttackEffect):
    """このワザを受けた相手が「最大HPが ``max_hp`` 以下」のポケモンなら、そのポケモンは、次の相手の番、このカードがバトル場にいる限り、ワザを使えない（v0.40。サカキの
    ニドキングの「すごむ」。ダメージの目安の数字はない）。要素 ``OpponentAttackLockWhileSourceActive``（持続する効果 ``state.CannotAttackWhileSourceActive``）。

    - 「最大HP」は受けるポケモンのいちばん上のカードの HP。確かめるのは効果を与えるとき。英語版の文面（「can't attack Giovanni's Nidoking」「Benching or evolving
      either Pokémon ends this effect」）は日本語版と意味が違い、使わない
    - 効果を与えたポケモンがバトル場にいないとき（ベンチにもどった・きぜつした）は、ワザを使える。同じ番にバトル場にもどるときの扱いは決められない（SG1。突風が
      もどす選択を止める。``SwitchOpponentWithBench``）
    """

    max_hp: int
    implementation_id = "attack_lock_while_source_active"
    opponent_effect_elements = (ATTACK_LOCK_ELEMENT,)

    def __post_init__(self) -> None:
        _positive_tens(self.max_hp, "最大HP")

    def check(self, attack: Attack) -> list[str]:
        expected = f"このワザを受けた相手が「最大HPが{self.max_hp}以下」のポケモンなら、そのポケモンは、次の相手の番、このカードがバトル場にいる限り、ワザを使えない。"
        return _check_form(attack, "条件つきでワザを使えなくするワザ", damage="none") + _check_exact_text(attack, "条件つきでワザを使えなくするワザ", (expected,))

    def conditional_lock_terms(self) -> tuple[type, int]:
        """不変条件（``engine._given_by_attack_problems``）が照らす、与える持続する効果の型と最大 HP の上限。"""
        from .state import CannotAttackWhileSourceActive

        return CannotAttackWhileSourceActive, self.max_hp


@dataclass(frozen=True)
class FailOnTailsAmountIfBenchNamed(AttackEffect):
    """コインを投げて「うら」なら、このワザは失敗する。自分のベンチに「``names``」がいるなら、このワザのダメージは「``amount``」になる（v0.40。サカキのニドクインの
    「ラブラリアット」）。要素は ``FailOnTails``（1 枚。p.323 の失敗）→ ``Damage``（``AmountIfOwnBenchNamed``。p.321 の 1 段階。匹数で足さない）。"""

    names: tuple[str, ...]
    amount: int
    implementation_id = "fail_on_tails_amount_if_bench_named"

    def __post_init__(self) -> None:
        _positive_tens(self.amount, "ダメージ")
        if len(self.names) != 1:
            raise ValueError(f"ベンチにいるかを見るポケモンの名前は 1 つ（{self.names!r}）")

    def check(self, attack: Attack) -> list[str]:
        expected = f"コインを投げて「うら」なら、このワザは失敗する。自分のベンチに「{self.names[0]}」がいるなら、このワザのダメージは「{self.amount}」になる。"
        return _check_form(attack, "コインで失敗しベンチでダメージが変わるワザ", damage="modified", modifier="+") + _check_exact_text(
            attack, "コインで失敗しベンチでダメージが変わるワザ", (expected,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        from .resolution.programs import SCOPE_OWN_BENCH, counted_pokemon

        attack = state.definitions[use.key.card_id].attacks[use.key.attack_index]
        named = counted_pokemon(state, use.player, SCOPE_OWN_BENCH, self.names)
        return DamageProfile(opponent=(self.amount if named else attack.damage,))


SWITCH_OPPONENT_THEN_DAMAGE_TEXTS = (
    # わるいゴーリキー（PMCG4-042）の「ひきずりだす」（全角のかっこ）
    "ダメージを与える前に、相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。（ダメージは新しい対戦ポケモンに与える。相手に控えがいない時、このワザは使えない）",
    # エリカのウツドン（PMCG5-011）の「さそってとかす」（半角のかっこ。意味は同じ）
    "ダメージを与える前に、相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。(ダメージは新しい対戦ポケモンに与える。相手に控えがいない時、このワザは使えない)",
)


@dataclass(frozen=True)
class SwitchOpponentThenDamage(AttackEffect):
    """ダメージを与える前に、相手の控えポケモンを 1 匹選び、相手の対戦ポケモンと入れ替える。ダメージは新しい対戦ポケモンに与える。相手に控えがいない時、このワザは
    使えない（v0.40。わるいゴーリキーの「ひきずりだす」・エリカのウツドンの「さそってとかす」）。ダメージを与えてから入れ替える型（``DamageAndForceSwitch``・
    ``SwitchOpponentActive``）とは別の型。

    - 相手に控えがいないことは、ワザを使うための条件（``usage_problem``。``NO_OPPONENT_BENCH``）
    - 選ぶのはワザを使ったプレイヤー（決定 ``FORCED_SWITCH``。v0.31 のかどわかすと同じ要素 ``ForceSwitch(chooser="attacker")``）。入れ替えは相手の対戦ポケモンへの
      効果（v0.31 のかどわかすと同じ読み方）なので、入れ替える前のポケモンの「ワザをうけない」状態・「とうめい」を評価する（受けなければ入れ替えず、ダメージはその
      ままのバトル場のポケモンに）。ベンチにもどったポケモンの特殊状態・持続する効果は消える（理由 ``forced_switch``）。ダメージ・エネルギー・ついているカードは
      いっしょに移る
    - ダメージは入れ替えたあとの相手の対戦ポケモンに、そのポケモンの弱点・抵抗力・防ぐ効果・「とうめい」・「ダメージを受けたとき」の効果で計算する（``Damage(OPP)``。
      決定をまたいで枠の値を運ぶ（``carry``）ので、入れ替える前のポケモンと新しいポケモンの両方の「とうめい」は T27 で止まる）
    """

    implementation_id = "switch_opponent_then_damage"
    opponent_effect_elements = (FORCED_SWITCH_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "入れ替えてからダメージを与えるワザ", damage="fixed") + _check_exact_text(
            attack, "入れ替えてからダメージを与えるワザ", SWITCH_OPPONENT_THEN_DAMAGE_TEXTS)

    def usage_problem(self, state: GameState, attacker: PokemonInPlay) -> IllegalActionError | None:
        owner, _ = state.find_pokemon(attacker.pokemon_id)
        if not state.players[1 - owner].bench:
            return IllegalActionError("NO_OPPONENT_BENCH", "相手に控えポケモンがいないので、このワザは使えない（ワザの説明）")
        return None

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        p = state.players[1 - use.player]
        problems = _decision_form(decision, _label(state, use), kind=FORCED_SWITCH, player=use.player, choices=(1, 1),
                                  options=(pokemon.pokemon_id for pokemon in p.bench))
        if p.active is None or p.active.pokemon_id != decision.context_value("target"):
            problems.append(f"入れ替えの対象 {decision.context_value('target')!r} が相手のバトル場のポケモンではない")
        return problems


@dataclass(frozen=True)
class ReturnOpponentActiveToDeck(AttackEffect):
    """相手の対戦ポケモンとそれについているすべてのカードを山札にもどさせ、その山札をよく切る。(相手に控えがいない時、このワザは使えない)（v0.40。わるいカイリキーの
    「つまみだす」。ダメージの目安の数字はない）。要素 ``ReturnOpponentToDeck``。相手に控えがいないことはワザを使うための条件（``usage_problem``。``NO_OPPONENT_BENCH``）。
    きぜつではない（サイドは取らない）。空いた相手のバトル場には、ワザのあとに相手が控えから出す。"""

    implementation_id = "return_opponent_active_to_deck"
    opponent_effect_elements = (RETURN_IN_PLAY_TO_DECK_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        expected = "相手の対戦ポケモンとそれについているすべてのカードを山札にもどさせ、その山札をよく切る。(相手に控えがいない時、このワザは使えない)"
        return _check_form(attack, "相手を山札にもどすワザ", damage="none") + _check_exact_text(attack, "相手を山札にもどすワザ", (expected,))

    def usage_problem(self, state: GameState, attacker: PokemonInPlay) -> IllegalActionError | None:
        owner, _ = state.find_pokemon(attacker.pokemon_id)
        if not state.players[1 - owner].bench:
            return IllegalActionError("NO_OPPONENT_BENCH", "相手に控えポケモンがいないので、このワザは使えない（ワザの説明）")
        return None


TAKE_AWAY_TEXT = "自分と相手、そしてそれらについているすべてのカードをそれぞれの山札にもどし、それぞれの山札をよく切る。"


@dataclass(frozen=True)
class ReturnBothActivesToDeck(AttackEffect):
    """自分と相手、そしてそれらについているすべてのカードをそれぞれの山札にもどし、それぞれの山札をよく切る（v0.52。エリカのハクリューの「つれさる」。ダメージの目安の
    数字はない。kyuura の印刷の文面。要素 ``programs.ReturnBothActivesToDeck``。docs/field-return-v0.52.md 4 章）。

    - 「自分」はワザを使ったポケモン（バトル場）、「相手」は相手の対戦ポケモン。どちらも、重なったカード・「ばける」でのせたカード・エネルギー・トレーナーを持ち主の山札に
      もどす（``zones.return_in_play_to_deck``）。きぜつではない（サイドは取らない）
    - 両方に「ワザをうけない」状態・「とうめい」を評価する（自分 → 相手の順。受けない側はもどさない・その山札を切らない）。片方だけもどることがある
    - 相手に控えがいなくても使える（説明に条件がない。わるいカイリキーの「つまみだす」の条件を持ち込まない）
    - 空いたバトル場は、ワザのあとの勝ち負けの判定・バトル場に出す決定（番でないプレイヤーが先）でうめる。両方とも場にポケモンがいなくなれば、勝ち負けの判定（p.311）
    """

    implementation_id = "return_both_actives_to_deck"
    opponent_effect_elements = (RETURN_IN_PLAY_TO_DECK_ELEMENT,)
    returns_both_actives: ClassVar[bool] = True  # ログの監査が、自分と相手の両方の return_in_play_to_deck を許すのに使う

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "自分と相手を山札にもどすワザ", damage="none") + _check_exact_text(attack, "自分と相手を山札にもどすワザ", (TAKE_AWAY_TEXT,))


@dataclass(frozen=True)
class CoinsAllHeadsBonusDamage(AttackEffect):
    """コインを ``coins`` 枚投げ、すべて「おもて」なら、``bonus`` ダメージを追加する（v0.40。カスミのシードラの「きぜつばり」。値 ``PrintedPlusBonusOnAllHeads``。
    「おもて」の数に比例しない）。コインはダメージの量だけを決めるので、「ダメージを受けない」相手には v0.4b の問い（``Damage.run``）。"""

    coins: int
    bonus: int
    implementation_id = "coins_all_heads_bonus_damage"

    def __post_init__(self) -> None:
        if type(self.coins) is not int or self.coins < 2:
            raise ValueError(f"コインの枚数は 2 以上の整数（{self.coins!r}）")
        _positive_tens(self.bonus, "追加のダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = f"コインを{self.coins}枚投げ、すべて「おもて」なら、{self.bonus}ダメージを追加する。"
        return _check_form(attack, "コインがすべて「おもて」で追加ダメージのワザ", damage="modified", modifier="+") + _check_exact_text(
            attack, "コインがすべて「おもて」で追加ダメージのワザ", (expected,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        attack = state.definitions[use.key.card_id].attacks[use.key.attack_index]
        return DamageProfile(opponent=(attack.damage, attack.damage + self.bonus))


SHUFFLE_DECK_TEXTS = {True: "自分の山札をよく切る。", False: "相手の山札をよく切る。"}


@dataclass(frozen=True)
class ShuffleDeckAttack(AttackEffect):
    """自分の（``own``）・相手の山札をよく切る（v0.40。タケシのマンキーの「ひまつぶし」・マンキーの「いたずら」。ダメージの目安の数字はない）。要素 ``ShuffleDeck``
    （``zones.shuffle_deck``。ログ ``shuffle`` の ``player`` は切る山札の持ち主）。"""

    own: bool
    implementation_id = "shuffle_deck_attack"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "山札を切るワザ", damage="none") + _check_exact_text(attack, "山札を切るワザ", (SHUFFLE_DECK_TEXTS[self.own],))


@dataclass(frozen=True)
class DamageThenSelfConfuseOnTails(AttackEffect):
    """相手にダメージの目安の数字ぶんのダメージ。コインを投げて「うら」なら、自分はこんらん状態になる（v0.40。オコリザルの「あばれまわる」）。v0.34 の
    ``DamagePlusOwnCountersThenSelfConfuseOnTails``（ケンタロスの「いかりくるう」）と同じ要素 ``Status(CONFUSION, local_coin=TAILS, target=SELF)``（相手に与えるこんらんではない）。コインは自分への
    効果だけを決めるので、相手が「ダメージを受けない」「ワザをうけない」状態でも投げる。ワザを使ったポケモンが相手の「はんげき」などで HP 以上なら投げない（p.309）。"""

    implementation_id = "damage_then_self_confuse_on_tails"

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「うら」なら、自分は「こんらん」状態になる。"
        return _check_form(attack, "コインで自分がこんらんになるワザ", damage="fixed") + _check_exact_text(attack, "コインで自分がこんらんになるワザ", (expected,))


# ---------------------------------------------------------------- v0.41（docs/heal-counter-status-v0.41.md）
# 回復（ダメージカウンターをとりのぞく）・ダメージカウンターを相手にのせる／取り替える・特殊状態の分岐と選択・山札からエネルギーをつける効果。要素は
# ``resolution.programs`` の ``HealCounters``・``ShiftCountersToOpponent``・``SwapCounters``・``ChosenStatus``・``AttachFromDeck`` と既存の要素。説明の文面は、
# 登録したワザの印刷の文面（kyuura の写し）と完全に同じものだけを受け付ける（v0.37 の約束）

# 回復の対象（``programs.HealCounters`` の ``scope``）
HEAL_SELF = "self"  # ワザを使ったポケモン（「自分」）
HEAL_OWN_ALL = "own_all"  # ワザを使ったポケモンと自分の控えポケモン全員（「自分と自分の控えポケモン全員」）
HEAL_BOTH_ALL = "both_all"  # お互いの場のポケモン全員（「お互いの場にいるポケモン全員」）
# エリカのクサイハナの「ミラクルかふん」の選べる特殊状態（説明の「ねむり・マヒ・こんらん・どく」の並び。決定 ``select_special_condition`` の番号）
CHOSEN_CONDITIONS = (SLEEP, PARALYSIS, CONFUSION, POISON)
_CONDITION_JA = {POISON: "どく", SLEEP: "ねむり", PARALYSIS: "マヒ", CONFUSION: "こんらん"}


def _positive_count(value: int, what: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{what}は正の整数（{value!r}）")


@dataclass(frozen=True)
class DamageThenHealSelf(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。その後、自分にのっているダメージカウンターを ``counters`` 個とりのぞく（``on_heads`` なら
    コインを投げて「おもて」のとき）（v0.41。エリカのナゾノクサ（PMCG5-002）の「ちょっとすいとる」・「たまにすいとる」）。要素は ``Damage(OPP)`` →
    ``HealCounters(counters, scope=HEAL_SELF)``（``on_heads`` なら要素のコイン）。

    - 説明は「ダメージを与えたら」と書かない（やどりぎのタネ（v0.5。``DamageAndRemoveCounters``）の「…ダメージを与えたら」とは別の書き方）。相手がダメージを
      受けなかった（防いだ・「とうめい」・最終ダメージ 0）ときもとりのぞく。条件を足さない
    - とりのぞくのはのっている数まで（GR-2000-P320-RECOVERY「すべてのダメージカウンターをとりのぞいたら、それ以上の回復はできない」）
    - コインは自分への効果だけを決めるので、相手の状態によらず投げる。ワザを使ったポケモンが相手の「はんげき」などで HP 以上なら、処理の対象がいないので
      投げない・とりのぞかない（p.309。v0.31 の ``HealSelfOnHeads`` と同じ）
    """

    counters: int
    on_heads: bool = False
    implementation_id = "damage_then_heal_self"

    def __post_init__(self) -> None:
        _positive_count(self.counters, "とりのぞくダメージカウンターの数")

    def check(self, attack: Attack) -> list[str]:
        prefix = "コインを投げて「おもて」なら、" if self.on_heads else ""
        expected = f"{prefix}自分にのっているダメージカウンターを、{self.counters}つとりのぞく。"
        return _check_form(attack, "ダメージのあと自分のダメージカウンターをとりのぞくワザ", damage="fixed") + _check_exact_text(
            attack, "ダメージのあと自分のダメージカウンターをとりのぞくワザ", (expected,))


@dataclass(frozen=True)
class CoinHealSelf(AttackEffect):
    """ダメージの目安の数字はない。コインを投げて「おもて」なら、自分にのっているダメージカウンターを ``counters`` 個とりのぞく。``then_sleep`` なら、同じ「おもて」で
    自分を「ねむり」状態にもする（v0.41。エリカのクサイハナの「ヒーリングかふん」・ナツメのヤドランの「いねむり」）。要素は ``Coin`` → ``HealCounters(gate=おもて)``
    （→ ``Status(SLEEP, target=SELF, gate=おもて)``）。

    - 1 枚のコイン（ワザ全体のコイン）で、とりのぞく効果と自分のねむりの両方が決まる（投げ直さない）
    - とりのぞく数がのっている数より多くても、0 個でも、ねむりにする（GR-2000-P309-ATTACK-PROCEDURE「途中で処理の対象がいなくなっていたら、その内容は
      無視して次の内容を処理する」。「とりのぞき、」の続きの効果は、とりのぞけたかを条件にしない）
    - 使うための条件はない（化石の秘密のヤドンの「ぼーっとする」の「…のってない時には、このワザは使えない」は書かれていない）。カウンターが 0 個でもワザは使え、
      コインを投げる（自分への効果なので、相手の状態によらない）
    """

    counters: int
    then_sleep: bool = False
    implementation_id = "coin_heal_self"

    def __post_init__(self) -> None:
        _positive_count(self.counters, "とりのぞくダメージカウンターの数")

    def check(self, attack: Attack) -> list[str]:
        if self.then_sleep:
            expected = f"コインを投げて「おもて」なら、自分にのっているダメージカウンターを{self.counters}つとりのぞき、自分を「ねむり」状態にする。"
        else:
            expected = f"コインを投げて「おもて」なら、自分にのっているダメージカウンターを、{self.counters}つとりのぞく。"
        return _check_form(attack, "コインで自分のダメージカウンターをとりのぞくワザ", damage="none") + _check_exact_text(
            attack, "コインで自分のダメージカウンターをとりのぞくワザ", (expected,))


@dataclass(frozen=True)
class CoinsHealOwnPokemon(AttackEffect):
    """コインを ``coins`` 枚投げ、「おもて」の数ぶんのダメージカウンターを、自分と自分の控えポケモン全員から、それぞれ、とりのぞく（v0.41。ナツメのモルフォンの
    「かいふくりんぷん」。ダメージの目安の数字はない）。要素は ``Coin(coins)`` → ``HealCounters(heads_of, scope=HEAL_OWN_ALL)``。

    - 同じコインの「おもて」の数を、どのポケモンにも使う（ポケモンごとに投げ直さない）。とりのぞくのはそれぞれのっている数まで
    - 控えポケモンの「とうめい」（化石の秘密のゴースト）は、とりのぞく効果を受けるときに評価する（自分のワザでもはたらく。v0.9 の T8）。とりのぞくカウンターがない
      ポケモンは効果を受けない（とりのぞく処理ができない。p.309）ので評価しない。2 匹以上なら T27（``UNRESOLVED_TRANSPARENCY_COIN_ORDER``）
    """

    coins: int
    implementation_id = "coins_heal_own_pokemon"

    def __post_init__(self) -> None:
        _positive_count(self.coins, "コインの枚数")

    def check(self, attack: Attack) -> list[str]:
        expected = f"コインを{self.coins}枚投げ、「おもて」の数ぶんのダメージカウンターを、自分と自分の控えポケモン全員から、それぞれ、とりのぞく。"
        return _check_form(attack, "コインの数で自分の場のダメージカウンターをとりのぞくワザ", damage="none") + _check_exact_text(
            attack, "コインの数で自分の場のダメージカウンターをとりのぞくワザ", (expected,))


@dataclass(frozen=True)
class HealAllPokemonBothSides(AttackEffect):
    """お互いの場にいるポケモン全員から、それぞれダメージカウンターを ``counters`` 個ずつ、とりのぞく（v0.41。エリカのプリンの「みんなでかいふく」。ダメージの
    目安の数字はない）。要素は ``HealCounters(counters, scope=HEAL_BOTH_ALL)``。

    - 相手のポケモンからもとりのぞく（相手のポケモンへの効果）。相手の対戦ポケモンが「ワザをうけない」状態（バリアー）なら、そのポケモンへの効果は無効
      （ほかのポケモンへの効果は有効）。「ダメージを受けない」状態（かたまる）は、ダメージ以外の効果を受けるので、とりのぞく（GR-2000-P321-PREVENTED-ELEMENTS）
    - 「とうめい」はとりのぞくカウンターのあるポケモンだけで評価する（``CoinsHealOwnPokemon`` と同じ）
    """

    counters: int
    implementation_id = "heal_all_pokemon_both_sides"
    opponent_effect_elements = (HEAL_ELEMENT,)

    def __post_init__(self) -> None:
        _positive_count(self.counters, "とりのぞくダメージカウンターの数")

    def check(self, attack: Attack) -> list[str]:
        expected = f"お互いの場にいるポケモン全員から、それぞれダメージカウンターを{self.counters}つずつ、とりのぞく。"
        return _check_form(attack, "お互いの場のダメージカウンターをとりのぞくワザ", damage="none") + _check_exact_text(
            attack, "お互いの場のダメージカウンターをとりのぞくワザ", (expected,))


@dataclass(frozen=True)
class MoveOwnCountersToOpponent(AttackEffect):
    """自分と自分の控えポケモン全員から、ダメージカウンターを 1 つずつとりのぞき、とりのぞいたダメージカウンターをすべて、相手にのせる（v0.41。ナツメのゴルダックの
    「ダメージシフト」。ダメージの目安の数字はない）。要素 ``ShiftCountersToOpponent``。

    - ダメージカウンターの移動で、相手は「ダメージを受けた」ことにならない（GR-2000-P320-COUNTER-MOVE。v0.7 の S19）。ワザのダメージの計算（p.321。弱点・抵抗力・
      プラスパワー・ディフェンダー）をせず、「ダメージを受けない」状態（かたまる）でものせる。「ダメージを受けたとき」の効果（はんげき・ほのおのかべ・こうらがえし・
      わるいねぞう）ははたらかず、のせたカウンターで HP 以上になっても「こんじょう」は使えない（相手のワザのダメージではない。v0.11 の G3〜G7）
    - とりのぞけるのは、カウンターが 1 つ以上のっているポケモンからだけ（0 個のポケモンからはとりのぞかない）。のせる数はとりのぞいた数（0 個ならのせない）
    - 相手がのせる効果を受けない（「ワザをうけない」状態・「とうめい」）とき、自分の側をとりのぞくかは決められない（CX1。``UNRESOLVED_COUNTER_TRANSFER_PROTECTED``）
    - のせたカウンターで HP 以上になった相手は、ワザのあとにきぜつする（p.323。サイドを取る）
    """

    implementation_id = "move_own_counters_to_opponent"
    opponent_effect_elements = (COUNTERS_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        expected = "自分と自分の控えポケモン全員から、ダメージカウンターを1つずつとりのぞき、とりのぞいたダメージカウンターをすべて、相手にのせる。"
        return _check_form(attack, "ダメージカウンターを相手にのせかえるワザ", damage="none") + _check_exact_text(
            attack, "ダメージカウンターを相手にのせかえるワザ", (expected,))


@dataclass(frozen=True)
class SwapCountersOnHeads(AttackEffect):
    """コインを投げて「おもて」なら、自分にのっているダメージカウンターすべてと、相手にのっているダメージカウンターすべてを、取り替える（v0.41。R団のミュウツーの
    「チェンジダメージ」。ダメージの目安の数字はない）。要素は ``Coin`` → ``SwapCounters(gate=おもて)``。

    - 取り替える前の双方の数で処理する（自分は相手の前の数に、相手は自分の前の数になる。片方を変えてから、変えたあとの数をもう片方に渡さない）
    - ダメージカウンターの移動で、どちらも「ダメージを受けた」ことにならない（GR-2000-P320-COUNTER-MOVE）。弱点・抵抗力・プラスパワー・ディフェンダーを計算せず、
      「ダメージを受けない」状態でも取り替える。「ダメージを受けたとき」の効果ははたらかず、「こんじょう」も使えない
    - 取り替えたあと、片方・両方が HP 以上なら、ワザのあとにきぜつする（両方なら同時のきぜつ。p.324）
    - 相手が取り替える効果を受けない（「ワザをうけない」状態・「とうめい」）とき、自分の側を変えるかは決められない（CX1。カウンターの数が同じなら場は変わらないので
      止めない）
    """

    implementation_id = "swap_counters_on_heads"
    opponent_effect_elements = (COUNTERS_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「おもて」なら、自分にのっているダメージカウンターすべてと、相手にのっているダメージカウンターすべてを、取り替える。"
        return _check_form(attack, "ダメージカウンターを取り替えるワザ", damage="none") + _check_exact_text(attack, "ダメージカウンターを取り替えるワザ", (expected,))


@dataclass(frozen=True)
class DamageThenConfuseBoth(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。相手を「こんらん」状態にする。その後、自分も「こんらん」状態になる（v0.41。クサイハナの「くさいにおい」）。
    要素は ``Damage(OPP)`` → ``Status(CONFUSION)`` → ``Status(CONFUSION, target=SELF)``。

    - 相手へのこんらんと自分へのこんらんは別の要素。相手がこんらんを受けない（「ワザをうけない」状態・「とうめい」・このワザのダメージで HP 以上）ときも、自分は
      こんらんになる（GR-2000-P321-PREVENTED-ELEMENTS「ほかの要素は有効」・GR-2000-P309-ATTACK-PROCEDURE）。「その後」は順番で、相手がこんらんになったかを
      条件にしない（「ダメージを与えた後」（Z23）とも別の書き方）
    - ワザを使ったポケモンが相手の「はんげき」などで HP 以上なら、自分へのこんらんは処理しない（p.309）
    """

    implementation_id = "damage_then_confuse_both"
    opponent_effect_elements = (CONFUSION,)

    def check(self, attack: Attack) -> list[str]:
        expected = "相手を「こんらん」状態にする。その後、自分も「こんらん」状態になる。"
        return _check_form(attack, "相手と自分をこんらんにするワザ", damage="fixed") + _check_exact_text(attack, "相手と自分をこんらんにするワザ", (expected,))


@dataclass(frozen=True)
class DamageThenStatusByCoin(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら相手を ``heads`` に、「うら」なら ``tails`` にする（v0.41。エリカの
    ナゾノクサ（PMCG5-003）の「へんなこな」の「こんらん」・「ねむり」）。v0.34 のくさいガス（``DamageThenPoisonOrConfuse``）と同じ要素
    ``Status(heads, local_coin=おもて, otherwise=tails)``（1 枚のコインで、どちらの状態にするかが決まる。投げ直さない）。"""

    heads: str
    tails: str
    implementation_id = "damage_then_status_by_coin"

    def __post_init__(self) -> None:
        if self.heads not in _CONDITION_JA or self.tails not in _CONDITION_JA or self.heads == self.tails:
            raise ValueError(f"特殊状態の組 ({self.heads!r}, {self.tails!r}) が正しくない")

    @property
    def opponent_effect_elements(self) -> tuple[str, ...]:  # type: ignore[override]
        return (self.heads, self.tails)

    def check(self, attack: Attack) -> list[str]:
        expected = f"コインを投げて「おもて」なら、相手を「{_CONDITION_JA[self.heads]}」状態に、「うら」なら「{_CONDITION_JA[self.tails]}」状態にする。"
        return _check_form(attack, "コインで相手の特殊状態が決まるワザ", damage="fixed") + _check_exact_text(attack, "コインで相手の特殊状態が決まるワザ", (expected,))


@dataclass(frozen=True)
class DamageThenChosenStatusOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、「ねむり・マヒ・こんらん・どく」の中から 1 つを選び、相手をその状態に
    する（v0.41。エリカのクサイハナの「ミラクルかふん」）。要素は ``Damage(OPP)`` → ``ChosenStatus(local_coin=おもて)``。

    - 選ぶのはワザを使ったプレイヤー（決定 ``select_special_condition``。選べるものは説明の並びの番号 0〜3。``CHOSEN_CONDITIONS``）。「おもて」のときだけ選ぶ
    - 選んだ状態は、ほかの特殊状態の効果と同じ規定（p.322。ねむり・マヒ・こんらんは置きかわり、どくは重なる。同じ状態は二重にならない）。マヒの再付与で回復する番が
      変わる場合（v0.3b の ``UNRESOLVED_REPARALYSIS_RECOVERY_TURN``）は、マヒを選べるが選ぶと止める（``unresolved_choices``）
    - コインの前の確かめは、ほかの「おもて」で相手を特殊状態にする効果と同じ（このワザのダメージで HP 以上なら投げない。「とうめい」で受けないと決まっていれば T19b、
      「ワザをうけない」状態なら HC3）
    """

    implementation_id = "damage_then_chosen_status_on_heads"
    opponent_effect_elements = CHOSEN_CONDITIONS

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「おもて」なら、「ねむり・マヒ・こんらん・どく」の中から1つを選び、相手をその状態にする。"
        return _check_form(attack, "コインで相手を選んだ特殊状態にするワザ", damage="fixed") + _check_exact_text(
            attack, "コインで相手を選んだ特殊状態にするワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        problems = _decision_form(decision, _label(state, use), kind=SELECT_SPECIAL_CONDITION, player=use.player, choices=(1, 1),
                                  options=range(len(CHOSEN_CONDITIONS)))
        target = state.players[1 - use.player].active
        if target is None or decision.context_value("target") != target.pokemon_id:
            problems.append(f"特殊状態を選ぶ決定の対象 {decision.context_value('target')!r} が相手の対戦ポケモンではない")
        return problems


@dataclass(frozen=True)
class CoinDamageAndConfuseElseSelfConfuse(AttackEffect):
    """コインを投げて「おもて」なら、相手の対戦ポケモンにダメージの目安の数字ぶんのダメージを与え、相手を「こんらん」状態にする。「うら」なら、相手にはダメージを
    与えず、自分を「こんらん」状態にする（v0.41。ナツメのコダックの「こまったねんりき」）。要素は ``Coin`` → ``Damage(OPP, gate=おもて)`` →
    ``Status(CONFUSION, gate=おもて)`` → ``Status(CONFUSION, target=SELF, gate=うら)``。

    - コインが先（「うら」なら相手へのダメージの要素がない。v0.11 の「いちかばちか」と同じ形）。1 枚のコインで、相手へのダメージ・相手のこんらん・自分のこんらんが
      決まる（投げ直さない）
    - 「うら」は「失敗」ではない（説明に「失敗」と書かれていない。ログ ``attack_failed`` はない）
    - コインが決める要素に自分への効果（「うら」の自分のこんらん）があるので、相手が「ダメージを受けない」「ワザをうけない」状態でも投げる（v0.34 の
      ``void_coin_question``）
    """

    implementation_id = "coin_damage_and_confuse_else_self_confuse"
    opponent_effect_elements = (CONFUSION,)

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「おもて」なら、相手を「こんらん」状態に、「うら」なら、相手にはダメージを与えず、自分を「こんらん」状態にする。"
        return _check_form(attack, "コインでダメージと相手か自分のこんらんが決まるワザ", damage="fixed") + _check_exact_text(
            attack, "コインでダメージと相手か自分のこんらんが決まるワザ", (expected,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        attack = state.definitions[use.key.card_id].attacks[use.key.attack_index]
        return DamageProfile(opponent=(attack.damage,), outcomes=((attack.damage, 0), (None, 0)))


@dataclass(frozen=True)
class DamageThenConfuseOnAnyHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを ``coins`` 枚投げ、1 枚でも「おもて」なら、相手を「こんらん」状態にする（v0.41。ナツメの
    モルフォンの「げんかくおんぱ」）。要素は ``Damage(OPP)`` → ``Coin(coins)`` → ``Status(CONFUSION, gate=(おもての数が 1 以上))``。

    - コインはダメージのあと（説明の順）。ダメージの要素で「ダメージを受けたとき」の効果（はんげきなど）がはたらいていれば、そのあと・このコインの前に処理する
      （CR-COUNTERATTACK-TIMING「ダメージ以外の効果（効果を決めるコインを含む）の前」）
    - このワザのダメージで HP 以上になった相手には、処理の対象がいないので投げない（p.309）。「とうめい」で受けないと決まった相手は T19b、「ワザをうけない」相手は HC3
    """

    coins: int
    implementation_id = "damage_then_confuse_on_any_heads"
    opponent_effect_elements = (CONFUSION,)

    def __post_init__(self) -> None:
        if type(self.coins) is not int or self.coins < 2:
            raise ValueError(f"コインの枚数は 2 以上の整数（{self.coins!r}）")

    def check(self, attack: Attack) -> list[str]:
        expected = f"コインを{self.coins}枚投げ、1枚でも「おもて」なら、相手を「こんらん」状態にする。"
        return _check_form(attack, "コインで相手をこんらんにするワザ", damage="fixed") + _check_exact_text(attack, "コインで相手をこんらんにするワザ", (expected,))


@dataclass(frozen=True)
class DamageThenSleepOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、相手を「ねむり」状態にする（v0.41。R団のミュウツーの「さいみんはどう」）。
    ``PoisonOnHeads``（v0.3a）・``ConfuseOnHeads``（v0.3c）と同じ形で、特殊状態だけが違う（要素 ``Status(SLEEP, local_coin=おもて)``）。ダメージのない
    ``SleepOnHeadsWithoutDamage``・コインのない ``SleepOpponent`` とは別の型。"""

    implementation_id = "damage_then_sleep_on_heads"
    opponent_effect_elements = (SLEEP,)

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「おもて」なら、相手を「ねむり」状態にする。"
        return _check_form(attack, "コインで相手をねむりにするワザ", damage="fixed") + _check_exact_text(attack, "コインで相手をねむりにするワザ", (expected,))


@dataclass(frozen=True)
class DamageThenRetreatLockOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、このワザを受けた相手の対戦ポケモンは、次の相手の番に「にげる」ことが
    できない（v0.41。ウツボットの「ようかいえき」）。v0.36 の ``DamageThenRetreatLock``（アイスバーン。コインなし）と同じ持続する効果 ``CannotRetreat``・要素
    ``OpponentRetreatLock`` に、要素のコイン（``local_coin``）を加えたもの。

    - コインはダメージのあと。このワザのダメージで HP 以上になった相手には投げない（p.309）。「とうめい」で受けないと決まった相手は T19b、「ワザをうけない」相手は HC3
      （コインはこの効果だけを決める）
    - 「にげる」でない入れ替え（ポケモンいれかえ・突風・ふきとばし）は制限しない（p.325。v0.36 と同じ）
    """

    implementation_id = "damage_then_retreat_lock_on_heads"
    opponent_effect_elements = (RETREAT_LOCK_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        # v0.42: ナツメのルージュラの「だきつく」の書き方（「このワザを受けた相手は」。v0.36 の手順 4 の効果の「このワザを受けたポケモンは」と同じ、ワザを受けた
        # 相手の対戦ポケモンを指す書き方）も受け付ける
        expected = (f"コインを投げて「おもて」なら、「{attack.name_ja}」を受けた相手の対戦ポケモンは、次の相手の番に「にげる」ことができない。",
                    "コインを投げて「おもて」なら、このワザを受けた相手は、次の相手の番に「にげる」ことができない。")
        return _check_form(attack, "コインで次の相手の番に「にげる」ことができなくするワザ", damage="fixed") + _check_exact_text(
            attack, "コインで次の相手の番に「にげる」ことができなくするワザ", expected)

    def retreat_lock_terms(self) -> type:
        from .state import CannotRetreat

        return CannotRetreat


@dataclass(frozen=True)
class SwitchOpponentActiveOnHeads(AttackEffect):
    """コインを投げて「おもて」なら、相手の控えポケモンを 1 匹選び、相手の対戦ポケモンと入れ替える。相手に控えがいない時、このワザは使えない（v0.41。わるいペルシアンの
    「ゆうわく」。ダメージの目安の数字はない）。要素 ``ForceSwitch(chooser="attacker", local_coin=おもて, required=True)``。

    - 選ぶのはワザを使ったプレイヤー（決定 ``FORCED_SWITCH``。v0.31 のかどわかすと同じ）。相手に控えがいないことは、ワザを使うための条件（``usage_problem``。
      ``NO_OPPONENT_BENCH``。こんらんのコインの前）
    - コインは入れ替えだけを決める。「ワザをうけない」相手には投げるかが決められない（HC3）。「とうめい」はコインの「おもて」のあと、入れ替えの効果を受けるときに評価する
    """

    implementation_id = "switch_opponent_active_on_heads"
    opponent_effect_elements = (FORCED_SWITCH_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「おもて」なら、相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。(相手に控えがいない時、このワザは使えない)。"
        return _check_form(attack, "コインで相手の控えと入れ替えるワザ", damage="none") + _check_exact_text(attack, "コインで相手の控えと入れ替えるワザ", (expected,))

    def usage_problem(self, state: GameState, attacker: PokemonInPlay) -> IllegalActionError | None:
        owner, _ = state.find_pokemon(attacker.pokemon_id)
        if not state.players[1 - owner].bench:
            return IllegalActionError("NO_OPPONENT_BENCH", "相手に控えポケモンがいないので、このワザは使えない（ワザの説明）")
        return None

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        p = state.players[1 - use.player]
        problems = _decision_form(decision, _label(state, use), kind=FORCED_SWITCH, player=use.player, choices=(1, 1),
                                  options=(pokemon.pokemon_id for pokemon in p.bench))
        if p.active is None or p.active.pokemon_id != decision.context_value("target"):
            problems.append(f"入れ替えの対象 {decision.context_value('target')!r} が相手のバトル場のポケモンではない")
        return problems


@dataclass(frozen=True)
class DamageThenReturnSelfToDeckOnTails(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「うら」なら、ダメージを与えた後、自分と、自分についているすべてのカードを山札にもどす。
    その後、その山札をよく切る（v0.41。カツラのファイヤーの「ひのとり」）。v0.36 のくもがくれガス（``DamageThenReturnSelfToDeckOnHeads``。「おもて」でもどす）と同じ
    要素 ``ReturnSelfToDeck`` で、もどすコインの面だけが違う（``local_coin=うら``）。

    - 「ダメージを与えた後」: ダメージを与えなかったときは Z23、同じワザで HP 以上になったポケモンがいれば RD9（どちらもコインの結果によらず宣言の前に止まる）
    - もどすのはきぜつではない（サイドは取られない）。空いたバトル場は、ワザのあとのバトル場に出す決定でうめる（控えがいなければ負け）
    """

    implementation_id = "damage_then_return_self_to_deck_on_tails"

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「うら」なら、ダメージを与えた後、自分と、自分についているすべてのカードを山札にもどす。その後、その山札をよく切る。"
        return _check_form(attack, "コインの「うら」で自分を山札にもどすワザ", damage="fixed") + _check_exact_text(
            attack, "コインの「うら」で自分を山札にもどすワザ", (expected,))


@dataclass(frozen=True)
class AttachEnergyFromDeckToSelf(AttackEffect):
    """自分の山札から ``energy_type`` エネルギーカードを 1 枚選び出し、このカードにつけてよい。その後、その山札をよく切る（v0.41。ロケット団のヤドンの「ひなたぼっこ」。
    ダメージの目安の数字はない）。要素 ``AttachFromDeck``。

    - 選ぶのはワザを使ったプレイヤー（決定 ``attach_from_deck``。選べるものは山札の ``energy_type`` の基本エネルギーカード。uid の小さい順。0〜1 枚。「つけてよい」
      なので選ばなくてよい）。選べるものがなければ決定を出さない
    - 山札から直接つける（``zones.attach_from_deck``。手札を通さない）。手札からつける通常の操作（p.310。1 番に 1 枚。``energy_attachments_this_turn``）・特殊能力で
      つけた枚数（v0.6 の R13。``energy_attached_by_powers_this_turn``）には数えない。つけたあとは「エネルギーカードをつけたとき」の特殊能力
      （``after_energy_attached``）を聞く
    - 山札を切るのは、つけた・つけなかった・選べるものがなかった、のどれでも（説明の「その後、その山札をよく切る。」に条件がない。v0.32 の ``BenchFromDeck`` と同じ）。
      先読みでは切らない
    """

    energy_type: EnergyType
    implementation_id = "attach_energy_from_deck_to_self"

    def check(self, attack: Attack) -> list[str]:
        expected = f"自分の山札から「{self.energy_type.ja}」エネルギーカードを1枚選び出し、このカードにつけてよい。その後、その山札をよく切る。"
        return _check_form(attack, "山札のエネルギーを自分につけるワザ", damage="none") + _check_exact_text(attack, "山札のエネルギーを自分につけるワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        candidates = deck_energy_candidates(state, use.player, self.energy_type)
        return _decision_form(decision, _label(state, use), kind=ATTACH_FROM_DECK, player=use.player, choices=(0, 1), options=candidates)


def deck_evolution_candidates(state: GameState, player: int) -> dict[int, list[int]]:
    """プレイヤーの山札の進化カード（uid の小さい順。山札の並びを決定に写さない）と、そのカードを今重ねられる自分の場のポケモンの番号（バトル場 → ベンチ）
    （v0.42。エリカのピッピの「つきのちから」）。重ねられるかは通常の進化と同じ ``evolution.evolution_block``（おたがいの最初の番・名前・その番の最初から
    場にいたか・段階。p.310。ワザによる進化でも免除しない）。重ねられるポケモンのないカードは含めない。進化したあとの HP がダメージ以下になる組
    （``UNRESOLVED_EVOLUTION_HP``）は含めたまま（呼ぶ側が選ぶと止める選択にする）。対応していない進化カード（デッキには入らない）は含めない。"""
    found: dict[int, list[int]] = {}
    for uid in sorted(state.players[player].deck):
        definition = state.card_def(uid)
        if definition.category != "pokemon" or not definition.is_evolution_pokemon or not definition.supported:
            continue
        targets = [pokemon.pokemon_id for pokemon in state.players[player].in_play() if evolution_block(state, pokemon, definition, from_deck=True) is None]
        if targets:
            found[uid] = targets
    return found


def deck_evolution_permission_pairs(state: GameState, player: int, pokemon_ids: Iterable[int] | None = None,
                                    cards: Iterable[int] | None = None) -> tuple[tuple[int, int], ...]:
    """v0.44: 山札の進化カード（``cards``。None なら山札のすべての対応している進化カード）と自分の場のポケモン（``pokemon_ids``。None なら場のすべて）の組のうち、
    トレーナー「サカキ」の許可だけで p.310 の制限が外れる組（(カードの uid, 場のポケモンの番号)）。山札から重ねる効果でこの組を重ねられるかは決められない（GV1。
    ``evolution.PERMISSION_FROM_DECK_CODE``）ので、呼ぶ側が止める。許可のないポケモンでは空。"""
    p = state.players[player]
    wanted = None if pokemon_ids is None else set(pokemon_ids)
    targets = [pokemon for pokemon in p.in_play() if wanted is None or pokemon.pokemon_id in wanted]
    if not any(pokemon.evolution_permission_turn is not None for pokemon in targets):
        return ()
    uids = sorted(p.deck) if cards is None else list(cards)
    pairs = []
    for uid in uids:
        definition = state.card_def(uid)
        if definition.category != "pokemon" or not definition.is_evolution_pokemon or not definition.supported:
            continue
        for pokemon in targets:
            block = evolution_block(state, pokemon, definition, from_deck=True)
            if block is not None and block[0] == PERMISSION_FROM_DECK_CODE:
                pairs.append((uid, pokemon.pokemon_id))
    return tuple(pairs)


def deck_evolution_devolved_pairs(state: GameState, player: int, pokemon_ids: Iterable[int] | None = None,
                                  cards: Iterable[int] | None = None) -> tuple[tuple[int, int], ...]:
    """v0.50: 山札の進化カード（``cards``。None なら山札のすべての対応している進化カード）と自分の場のポケモン（``pokemon_ids``。None なら場のすべて）の組のうち、
    ほかの確かめがすべて通り、ポケモンが今の番に退化したことだけで重ねられるかが決まらない組（DV2。``evolution.DEVOLVED_THIS_TURN_CODE``）。山札から重ねる効果
    （つきのちから・たきのぼりしんか・［うか］）は、GV1 と同じく、選べるものが変わるので決定を出す前に止める（呼ぶ側）。今の番に退化したポケモンがいなければ空。"""
    p = state.players[player]
    wanted = None if pokemon_ids is None else set(pokemon_ids)
    targets = [pokemon for pokemon in p.in_play() if (wanted is None or pokemon.pokemon_id in wanted) and devolved_this_turn(state, pokemon)]
    if not targets:
        return ()
    uids = sorted(p.deck) if cards is None else list(cards)
    pairs = []
    for uid in uids:
        definition = state.card_def(uid)
        if definition.category != "pokemon" or not definition.is_evolution_pokemon or not definition.supported:
            continue
        for pokemon in targets:
            block = evolution_block(state, pokemon, definition, from_deck=True)
            if block is not None and block[0] == DEVOLVED_THIS_TURN_CODE:
                pairs.append((uid, pokemon.pokemon_id))
    return tuple(pairs)


def evolution_hp_problem_targets(state: GameState, card: int, targets: Iterable[int]) -> tuple[int, ...]:
    """v0.42: 進化カード ``card`` を重ねると、HP がのっているダメージ以下になるポケモン（v0.4a の H1 と同じ問い。``UNRESOLVED_EVOLUTION_HP``）。"""
    # v0.48: 重ねたあとの最大HP（``evolution_hp``。重ねるカードの HP と、そのカードの常にはたらく特殊能力）
    return tuple(pid for pid in targets if state.find_pokemon(pid)[1].damage >= evolution_hp(state, state.find_pokemon(pid)[1], card))


EVOLUTION_HP_REASON = (
    "進化すると HP がのっているダメージ以下になる。そのときにきぜつするか（いつきぜつの判定をするか）は『オフィシャルブック2000』（p.310・p.323）から決められないので"
    "扱わない（v0.4a の H1）"
)


def deck_energy_candidates(state: GameState, player: int, energy_type: EnergyType) -> list[int]:
    """プレイヤーの山札の ``energy_type`` の基本エネルギーカード（uid の小さい順。山札の並びを決定に写さない）（v0.41）。"""
    return sorted(uid for uid in state.players[player].deck
                  if state.card_def(uid).is_basic_energy and state.card_def(uid).provides is energy_type)


@dataclass(frozen=True)
class DamageThenLockSelf(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。次の自分の番、このカードはこのワザを使えない（v0.41。ナツメのヤドランの「きあいずつき」）。v0.35 の
    あわあわ（``DamageThenLockSelfOnTails``。コインの「うら」のとき）と同じ持続する効果 ``CannotUseOwnAttack``・要素 ``SelfAttackLock`` で、コインがない
    （``local_coin=None``。いつも与える）。ワザを使ったポケモンが相手の「はんげき」などで HP 以上なら与えない（p.309）。"""

    implementation_id = "damage_then_lock_self"

    def check(self, attack: Attack) -> list[str]:
        expected = f"次の自分の番、このカードは「{attack.name_ja}」を使えない。"
        return _check_form(attack, "次の自分の番にそのワザを使えなくなるワザ", damage="fixed") + _check_exact_text(
            attack, "次の自分の番にそのワザを使えなくなるワザ", (expected,))

    def attack_lock_terms(self) -> tuple[type, int | None]:
        from .state import CannotUseOwnAttack

        return CannotUseOwnAttack, None


@dataclass(frozen=True)
class DamageMinusIfDefenderDamaged(AttackEffect):
    """相手（相手の対戦ポケモン）にダメージカウンターがのっている時、このワザのダメージは「-``reduction``」される（v0.41。エリカのプリンの「やさしいパンチ」）。
    値 ``PrintedMinusIfDefenderDamaged``（p.321 の 1 段階。ダメージの目安の「−」の説明。GR-2000-P320-DAMAGE-FIGURE）。のっているかだけを見る（数に比例しない。
    v0.40 の「つのでえぐる」の追加と同じ見方）。"""

    reduction: int
    implementation_id = "damage_minus_if_defender_damaged"

    def __post_init__(self) -> None:
        _positive_tens(self.reduction, "へらすダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = f"相手にダメージカウンターがのっている時、このワザのダメージは「-{self.reduction}」される。"
        problems = _check_form(attack, "相手のダメージカウンターでダメージがへるワザ", damage="modified", modifier="-") + _check_exact_text(
            attack, "相手のダメージカウンターでダメージがへるワザ", (expected,))
        if type(attack.damage) is int and attack.damage < self.reduction:
            problems.append(f"ダメージの目安 {attack.damage} がへらすダメージ {self.reduction} より小さい")
        return problems

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        attack = state.definitions[use.key.card_id].attacks[use.key.attack_index]
        damaged = state.players[1 - use.player].active.damage > 0
        return DamageProfile(opponent=(attack.damage - (self.reduction if damaged else 0),))


def attack_damage_modifiers(
    state: GameState, attacker: PokemonInPlay, defender: PokemonInPlay, *, attack: AttackKey | None = None, bench: bool = False,
    attack_status: frozenset[int] | None = None,
) -> tuple[DamageModifier, ...]:
    """ワザでダメージを与えるときの変更効果（v0.2c）。

    ワザを使うポケモン（``attacker``）についているカードは ``role="attacker"``（プラスパワーの 5 段階）、ダメージを
    受けるポケモン（``defender``）についているカードは ``role="defender"``（ディフェンダーの 7 段階）で聞く（p.321）。
    自分へのダメージ（v0.2f）では、``attacker`` と ``defender`` が同じポケモンになる。それぞれのカードは自分の
    立場でだけ効果を返すので、同じカードの効果を二重に数えない。
    効果の内容は、ついているカードのカード id で効果の登録表から引く（エンジンはカードの種類を知らない）。

    v0.27: ``attack``（ダメージを計算しているワザ）を渡すと、ワザを使うポケモンの持っている持続する効果のうち、そのワザのダメージを変える
    もの（``NextTurnAttackDamage``。ストライクの「つるぎのまい」。今の番にはたらき、効果を与えたカードの ``target_attack_index`` のワザ）を、
    p.321 の 2 段階の「その数にする」効果（``SET``）として加える。ワザの名前では探さない（``persistent.next_turn_attack_damage``）。解決の
    基盤の ``kernel.deal_damage`` と宣言の前の ``preview_attack_damage`` が同じこの関数を使う。``attack`` を渡さない呼び出し（こんらんの
    20 ダメージの確認。``procedures.confusion_damage_problem``）は v0.26 と同じ（こんらんの 20 は「きりさく」のダメージではない。p.309 の
    手順 5「もとのワザの内容に関わらず」）。

    v0.46: ``attack`` を渡すと、受けるポケモンの持っている「リフレクター」の効果（``HalvedDamage``。8 段階の半分（切りすて））と、場の常にはたらく特殊能力の
    変更効果（``continuous_attack_damage_modifiers``。なぞのかべ・ふしぎなバリアー・くつろぐかおり・きょうぼう）も加える。``attack_status`` は、ワザが使われた時
    （宣言）に「ねむり・マヒ・こんらん」状態だった場のポケモンの番号（その時点の特殊状態で決める特殊能力（くつろぐかおり）のため。解決の基盤の
    ``Resolution.attack_status``）。None なら今の特殊状態で決める（宣言の前の計算）。
    """
    modifiers: list[DamageModifier] = []
    if attack is not None:
        # v0.49: 変わるワザは ``AttackKey``（印刷したカードの id と位置）で探す（［へんしん］・「ばける」・［サイコリンク］で持つワザも、同じワザなら当てはまる）
        boost = next_turn_attack_damage(state, attacker, attack)
        if boost is not None and (defender is not attacker or boost.includes_self_damage):
            # v0.35: 「数をかける」効果（「きあいだめ」の「2倍」。``MULTIPLY``）も同じ 2 段階。自分へのダメージに当てはめるのは、説明がそう書くとき
            # だけ（マチスのラッタの「(自分へのダメージも2倍)」。``includes_self_damage``）
            name = attack_of(state, AttackKey(effect_attack_card(state, boost), boost.attack_index)).name_ja
            operation = MULTIPLY if boost.operation == NEXT_TURN_MULTIPLY else SET
            modifiers.append(DamageModifier(step=2, amount=boost.amount, label=name, source=boost.source_card, operation=operation))
    for holder, role in ((attacker, "attacker"), (defender, "defender")):
        for attached in holder.trainers:
            entry = state.effects.trainer_entry(state.cards[attached.card].card_id)
            if bench:
                # v0.31: 控えポケモンへのダメージ（``bench``）。ついているトレーナーの実装に、受けるのが控えポケモンだと渡す（プラスパワーは
                # 変えない。p.257 の最新の説明「(控えポケモンへのダメージは、そのまま)」）
                modifiers.extend(entry.effect.damage_modifiers(state, attached, role, bench=True))
            else:
                modifiers.extend(entry.effect.damage_modifiers(state, attached, role))
    if attack is not None and not bench:
        # v0.34: ワザを使うポケモンの持っている「ダメージを変更する効果」（p.321 の 2 段階）のうち、カラカラの「なきつく」を受けた状態
        # （``ReducedDamageToSource``）。受けるのが効果を与えたポケモン（「このカード」）のときだけ。控えポケモンへのダメージで受けるのが
        # そのポケモンのときは決められない（``kernel.deal_damage`` が計算の前に止める）。こんらんの 20（``attack`` を渡さない呼び出し）には使わない
        cry = reduced_damage_to_source(state, attacker)
        if cry is not None and defender.card == cry.source_card:
            modifiers.append(DamageModifier(step=2, amount=-cry.amount, label=_persistent_effect_name(state, cry), source=cry.source_card))
    if attack is not None:
        # v0.31: ワザを受けるポケモンの持っている「ダメージを変更する効果」（p.321 の 8 段階。ピクシーの「ちいさくなる」。``DamageReduction``）。
        # 今の番にはたらくもの（次の相手の番）だけ。こんらんの 20（``attack`` を渡さない呼び出し）には使わない
        reduction = damage_reduction(state, defender)
        if reduction is not None:
            name = _persistent_effect_name(state, reduction)
            modifiers.append(DamageModifier(step=8, amount=-reduction.amount, label=name, source=reduction.source_card))
        # v0.45: 同じ 8 段階の、決まった数より小さければ 0 にする効果（イワークの「かたくなる」。``ZeroDamageBelow``・``damage.ZERO_IF_BELOW``）。加算でないので、
        # 同じ段階にほかの効果があり順番で結果が変わるときは、受けるポケモンの持ち主が順番を選ぶ（p.321。v0.35 の決定）
        threshold = zero_damage_below(state, defender)
        if threshold is not None:
            modifiers.append(DamageModifier(step=8, amount=threshold.threshold, label=_persistent_effect_name(state, threshold),
                                            source=threshold.source_card, operation=ZERO_IF_BELOW))
        # v0.46: 同じ 8 段階の、受けるダメージを半分（切りすて）にする効果（エリカのタマタマの「リフレクター」。``HalvedDamage``・``damage.HALVE_DOWN``）
        halved = halved_damage(state, defender)
        if halved is not None:
            modifiers.append(DamageModifier(step=8, amount=2, label=_persistent_effect_name(state, halved), source=halved.source_card, operation=HALVE_DOWN))
        # v0.46: 常にはたらく特殊能力（2・6・8 段階）。こんらんの 20（``attack`` を渡さない呼び出し）には使わない（``confusion_power_modifiers`` で別に聞く）
        modifiers.extend(continuous_attack_damage_modifiers(state, attacker, defender, attack_status=attack_status))
    return tuple(modifiers)


def _persistent_effect_name(state: GameState, effect) -> str:
    """持続する効果のログ・ダメージの記録に出す名前（効果を与えたカードの名前と種類。v0.31）。"""
    return f"{state.card_def(effect.source_card).name_ja}（{effect.kind}）"


DAMAGE_ONLY = DamageOnly()


@dataclass(frozen=True)
class AttackEntry:
    """登録の 1 件: 実装と、登録したときに確かめたワザ名。

    説明文のあるワザ（v0.2d から）は、次も書く（説明文のないワザは None のまま）。

    - ``text_ja``: 登録したときに照合した kyuura の写しの説明文（データが変わったら使えなくなる。
      印刷の文面で、処理の根拠ではない）
    - ``play_text_ja``: 実装がしたがう文面（2026-10-14 までの登録は『オフィシャルブック2000』の「最新の説明」。2026-10-15 からの方針
      （docs/card-data-policy.md）で kyuura データの採用によって登録したものは、kyuura の最新の説明（LD-）・エラッタか、それがなければ
      kyuura の印刷の文面）
    - ``source``: ``play_text_ja`` の出典（誌面のページ。採用の記録で登録したものは、kyuura の記録の id か ``kyuura data/cards.json``）
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
    # v0.47: True なら、効果でこのカード自身をポケモンとして場に出す（なにかの化石・ピッピ人形。``PlayAsPokemon``）。使い終わってもトラッシュしない（``resolve`` が
    # ``zones.put_trainer_into_play`` で使用中から場に移した）。つけて使うトレーナー（``stays_in_play``。ポケモンについて場に残る）とは別の印
    enters_play = False
    # True: 効果で、たねポケモンの上に 2 進化カードを直接重ねる（1 進化を飛ばす。v0.25 のポケモン育て屋さん）。進化の重なりの不変条件が、
    # たねポケモン + 2 進化の重なりの進化のログ（evolve の trainer_card）のカードを、この印で確かめる（カード id では分けない）
    skips_stage1_evolution = False
    discard_turn_offset = 0  # つけて使うトレーナーをトラッシュする番: 使った番から数えていくつ後の番の終わりか
    # v0.50: True なら、効果で自分のポケモンの最大HPを下げ（退化）、のっているダメージ以下になったポケモンが「きぜつ」しうる（退化スプレー）。エンジンが、使い終わって
    # カードをトラッシュしたあとに、きぜつの処理（``resolution.after_trainer``）をする。False のトレーナーのあとに HP 以上のポケモンが残れば、v0.48 の MH1 で受け付けない
    may_knock_out = False
    # v0.52: True なら、効果で自分のバトル場のポケモンが場をはなれ（きぜつではない）、バトル場が空きうる（ポケモン回収）。エンジンが、使い終わってカードをトラッシュした
    # あとに、勝ち負けの判定・バトル場に出す決定（``resolution.after_trainer``）をする。False のトレーナーのあとにバトル場が空いていれば、不変条件で止める
    empties_active = False

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

    def damage_modifiers(self, state: GameState, attached: AttachedTrainer, role: str, *, bench: bool = False) -> list[DamageModifier]:
        """ついているポケモンがワザを使う（``role="attacker"``）・受ける（``"defender"``）ときの変更効果。``bench``（v0.31）は、ダメージを
        受けるのが控えポケモン（相手の控え ``OPPONENT_BENCH``。v0.33 から自分の控え ``SELF_BENCH`` も）のとき True（渡されるのはそのときだけ）。"""
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


@dataclass(frozen=True)
class DiscardHandAndDraw(TrainerEffect):
    """手札をすべてトラッシュし、その後、山札からカードを ``count`` 枚引いて手札にする（オーキドはかせ。p.255 の最新の説明「あなたの
    手札をすべてトラッシュする。その後、山札からカードを7枚引いて、手札にする。」。v0.19。docs/professor-oak-v0.19.md）。

    - 使っているこのカードは、p.310 の手順 1 で手札から出している（``state.trainer_in_use``）ので、トラッシュする手札に含まない。
      使い終わったらエンジンがトラッシュする（``engine._finish_trainer``。トラッシュにカードの順番はない。p.312）。
    - トラッシュ → 引くの順（最新の説明の「その後」）。引くのは自分の山札の一番上から（p.312）。
    - 使うための条件はない（最新の説明）。手札（このカードを除く）が 0 枚でも使え、トラッシュは 0 枚（p.255 の解説「手札が
      「オーキドはかせ」1枚になったときが最高の場合」）。
    - 山札が足りなくても負けにはならず、引けるだけ引く。山札が 0 枚なら 0 枚（p.312。マサキと同じ規定）。負けになるのは、番の
      最初に引けないとき（p.309, p.312）。
    - 引いたカードを相手に見せる必要はない（p.312）。トラッシュしたカードは公開。乱数は使わない。決定を出さない。
    """

    count: int
    implementation_id = "discard_hand_and_draw"

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        discard_hand(state, use.player)
        deck = state.players[use.player].deck
        draw_cards(state, use.player, min(self.count, len(deck)))


@dataclass(frozen=True)
class DiscardFromHandThenSearchDeck(TrainerEffect):
    """使うための条件として手札から ``discard`` 枚を選んでトラッシュし、その後、自分の山札からカードを ``search`` 枚選び出して手札に加え、
    その山札を切る（パソコン通信。p.260 の最新の説明「手札からカードを2枚選んでトラッシュしなければ、このカードは使えない。あなたの山札から
    カードを1枚選び出し、手札に加える。その後、その山札をよく切る。」。p.310 の「使うための条件」の例。v0.22。docs/computer-search-v0.22.md）。

    - 使うための条件（CS2〜CS5）: 使っているこのカードは p.310 の手順 1 で手札から出している（``state.trainer_in_use``）ので、トラッシュ
      する手札に含まれない。``check_playable`` は手札から出す前に呼ばれるので、このカードを除く手札が ``discard`` 枚未満なら
      ``IllegalActionError("INSUFFICIENT_CARDS_IN_HAND")``（p.310「2枚トラッシュできないときには、「パソコン通信」を使うことは
      できません。」）。拒否したらカードは手札に残る。
    - 山札が 0 枚のとき（CS6）は原典で決められない（使うための条件は手札のトラッシュだけで、山札から選び出せないときの扱いは書かれて
      いない。p.312 の「引けるだけ引く」は「カードを引く」ときの規定）ので、条件の確認のあと ``UnsupportedError`` で止める。
    - 段階 1（CS7〜CS10）: 使ったプレイヤーが手札（このカードを除く）からちょうど ``discard`` 枚を選ぶ（決定 ``DISCARD_FROM_HAND``）。
      選んだカードを手札の並びの順にトラッシュする（``zones.discard_from_hand``。ログ ``discard_from_hand``。公開）。
    - 段階 2（CS11〜CS15）: 使ったプレイヤーが自分の山札からちょうど ``search`` 枚を選ぶ（決定 ``SEARCH_DECK``。どの種類のカードでも
      よく、省略できない。山札が 1 枚でも決定を出す）。選んだカードを手札に加え（``zones.search_deck_to_hand``。ログ ``search_deck`` の
      ``card`` は選んだプレイヤーだけが見る情報）、その山札を切る（``zones.shuffle_deck``。乱数 ``state.rng``。ログ ``shuffle``）。
      「カードを引く」ではないので、山札が 0 枚になっても負けではない（負けは番の最初に引けないときだけ。p.309・p.312）。
    - 不正な答え（枚数・重複・選べないもの）は決定の確認（``decisions.check_choices``）が拒否し、決定は待ったまま、状態・乱数は変わら
      ない。段階 2 で拒否しても、段階 1 のトラッシュは取り消さない（すでにすんだ処理）。
    """

    discard: int
    search: int
    implementation_id = "discard_from_hand_then_search_deck"

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        p = state.players[use.player]
        others = [uid for uid in p.hand if uid != use.card]
        if len(others) < self.discard:
            raise IllegalActionError(
                "INSUFFICIENT_CARDS_IN_HAND",
                f"このカードを除く手札が {len(others)} 枚で、使うための条件（手札からカードを{self.discard}枚選んでトラッシュする）を"
                "満たせない（p.260・p.310）",
            )
        if not p.deck:
            raise UnsupportedError(
                "UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK",
                "山札が 0 枚。このときに「パソコン通信」を使えるか（手札をトラッシュするだけで使えるか）は、『オフィシャルブック2000』（p.260・"
                "p.310・p.312）から決められないので扱わない（p.312 の「引けるだけ引く」は「カードを引く」ときの規定）",
            )

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        push_trainer_decision(
            state, use, kind=DISCARD_FROM_HAND, player=use.player, options=state.players[use.player].hand,
            min_choices=self.discard, max_choices=self.discard,
        )

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if decision.kind == DISCARD_FROM_HAND:
            discard_from_hand(state, use.player, choices)
            push_trainer_decision(
                state, use, kind=SEARCH_DECK, player=use.player, options=sorted(state.players[use.player].deck),
                min_choices=self.search, max_choices=self.search,
            )
            return
        for card in choices:
            search_deck_to_hand(state, use.player, card)
        shuffle_deck(state, use.player)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        """決定するのは使ったプレイヤー。段階 1 は手札（このカードを除く）から ``discard`` 枚、段階 2 は山札（uid の小さい順）から
        ``search`` 枚。段階 2 を待つのは段階 1 のトラッシュのあと（今の番のログの最後の ``play_trainer`` のあとに ``discard_from_hand``）。"""
        p = state.players[use.player]
        problems = []
        if decision.player != use.player:
            problems.append(f"「パソコン通信」の決定を決定するのがプレイヤー {decision.player} で、使ったプレイヤー {use.player} ではない")
        if decision.kind == DISCARD_FROM_HAND:
            expected, count = tuple(p.hand), self.discard
        elif decision.kind == SEARCH_DECK:
            expected, count = tuple(sorted(p.deck)), self.search
            since = max((i for i, e in enumerate(state.log) if e["kind"] == "play_trainer" and e["card"] == use.card), default=None)
            if since is None or not any(e["kind"] == "discard_from_hand" for e in state.log[since:]):
                problems.append("「パソコン通信」の山札を選ぶ決定が、手札のトラッシュ（ログ discard_from_hand）のあとではない")
        else:
            return problems + [f"「パソコン通信」の決定の種類が {decision.kind!r}（{DISCARD_FROM_HAND}・{SEARCH_DECK} のはず）"]
        if (decision.min_choices, decision.max_choices) != (count, count):
            problems.append(f"「パソコン通信」の決定 {decision.kind} で選ぶ数が {decision.min_choices}〜{decision.max_choices}（{count} 枚のはず）")
        if decision.options != expected:
            problems.append(f"「パソコン通信」の決定 {decision.kind} の選べるもの {decision.options} が {expected} と合わない")
        if use.card in decision.options:
            problems.append("「パソコン通信」の決定で、使っているこのカードを選べる")
        return problems


def _retrievable_energy(state: GameState, player: int, excluded: tuple[int, ...]) -> tuple[int, ...]:
    """v0.23: エネルギー回収で選べるもの。自分のトラッシュの基本エネルギーカード（トラッシュの並び）から、このカードを使うためにトラッシュした
    カード ``excluded`` を除いたもの（p.257「ただし、このカードを使うためにトラッシュしたカードを選ぶことはできない。」）。"""
    return tuple(uid for uid in state.players[player].discard if state.card_def(uid).is_basic_energy and uid not in excluded)


@dataclass(frozen=True)
class DiscardFromHandThenRetrieveEnergy(TrainerEffect):
    """使うための条件として手札から ``discard`` 枚を選んでトラッシュし、その後、自分のトラッシュの基本エネルギーカードを最大 ``retrieve`` 枚選び
    出して手札に加える（エネルギー回収。p.257 の最新の説明「手札からカードを1枚選んでトラッシュしなければ、このカードは使えない。あなたの
    トラッシュから「基本エネルギーカード」を最大2枚選び出し、手札に加える。ただし、このカードを使うためにトラッシュしたカードを選ぶことは
    できない。」。v0.23。docs/energy-retrieval-v0.23.md の ER1〜ER17）。

    - 使うための条件（ER2・ER3）: 使っているこのカードは p.310 の手順 1 で手札から出している（``state.trainer_in_use``）ので、トラッシュ
      する手札に含まれない。``check_playable`` は手札から出す前に呼ばれるので、このカードを除く手札が ``discard`` 枚未満なら
      ``IllegalActionError("INSUFFICIENT_CARDS_IN_HAND")``（拒否したらカードは手札に残る）。トラッシュするカードの種類に制限はない。
    - 使う前のトラッシュに基本エネルギーカードがないとき（ER10）は、使えるかを原典で決められないので、条件の確認のあと ``UnsupportedError``
      で止める。トラッシュするカードは選べない（ER7）ので、トラッシュによって選べるものは増えない（選べるものは、使う前のトラッシュの基本
      エネルギーカードと同じ。ER11）。
    - 段階 1（ER4・ER5）: 使ったプレイヤーが手札（このカードを除く）からちょうど ``discard`` 枚を選び、トラッシュする（``zones.discard_from_hand``。
      ログ ``discard_from_hand``。公開。パソコン通信と同じ処理）。
    - 段階 2（ER6〜ER9・ER12）: 使ったプレイヤーが、トラッシュの基本エネルギーカード（段階 1 でトラッシュしたカードを除く。トラッシュの
      並び）から 1〜min(``retrieve``, 選べるものの数) 枚を選ぶ（決定 ``RETRIEVE_ENERGY``。``context`` の ``"discarded"`` に段階 1 で
      トラッシュしたカード）。選べるものがあるのに 0 枚を選ぶと、原典で決められない（ER9）ので ``UnsupportedError`` で止める（決定は待った
      まま。``min_choices`` は 0 にして、0 枚の答えを枚数の誤りにしない）。選んだカードはトラッシュの並びの順に手札に加える
      （``zones.return_discard_to_hand``。ログ ``retrieve_energy`` の ``cards`` は公開。トラッシュは公開の情報。ER13）。
    - 不正な答え（枚数・重複・選べないもの）は決定の確認が拒否し、決定は待ったまま。段階 2 で拒否しても、段階 1 のトラッシュは取り消さない。
    """

    discard: int
    retrieve: int
    implementation_id = "discard_from_hand_then_retrieve_energy"

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        p = state.players[use.player]
        others = [uid for uid in p.hand if uid != use.card]
        if len(others) < self.discard:
            raise IllegalActionError(
                "INSUFFICIENT_CARDS_IN_HAND",
                f"このカードを除く手札が {len(others)} 枚で、使うための条件（手札からカードを{self.discard}枚選んでトラッシュする）を"
                "満たせない（p.257・p.310）",
            )
        if not _retrievable_energy(state, use.player, ()):
            raise UnsupportedError(
                "UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET",
                "トラッシュに基本エネルギーカードがない（このカードを使うためにトラッシュするカードは選べない）。このときに「エネルギー回収」を"
                "使えるか（手札をトラッシュするだけで使えるか）は、『オフィシャルブック2000』（p.257・p.310）から決められないので扱わない",
            )

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        push_trainer_decision(
            state, use, kind=DISCARD_FROM_HAND, player=use.player, options=state.players[use.player].hand,
            min_choices=self.discard, max_choices=self.discard,
        )

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if decision.kind == DISCARD_FROM_HAND:
            discarded = discard_from_hand(state, use.player, choices)
            options = _retrievable_energy(state, use.player, discarded)
            if not options:  # check_playable で確かめた（トラッシュしたカードは選べないので、使う前と同じ）
                raise RuntimeError("「エネルギー回収」で選べる基本エネルギーカードがない（確認の漏れ。エンジンの不具合）")
            push_trainer_decision(
                state, use, kind=RETRIEVE_ENERGY, player=use.player, options=options, context=(("discarded", discarded),),
                min_choices=0, max_choices=min(self.retrieve, len(options)),
            )
            return
        if not choices:
            raise UnsupportedError(
                "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE",
                "トラッシュに選べる基本エネルギーカードがあるのに 0 枚を選んだ。「最大2枚」が 0 枚を含むか（手札に加えずに終われるか）は、"
                "『オフィシャルブック2000』（p.257）から決められないので扱わない（1 枚以上を選び直せる）",
            )
        cards = tuple(uid for uid in state.players[use.player].discard if uid in choices)
        return_discard_to_hand(state, use.player, cards)
        state.add_event("retrieve_energy", player=use.player, cards=cards)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        """決定するのは使ったプレイヤー。段階 1 は手札（このカードを除く）から ``discard`` 枚、段階 2 はトラッシュの基本エネルギーカード
        から段階 1 でトラッシュしたカードを除いたもの（0〜min(``retrieve``, 数) 枚。0 枚は答えのときに止める）。段階 2 の ``"discarded"`` は、
        今の番のログの最後のこのカードの ``play_trainer`` のあとの ``discard_from_hand`` と同じ。"""
        problems = []
        if decision.player != use.player:
            problems.append(f"「エネルギー回収」の決定を決定するのがプレイヤー {decision.player} で、使ったプレイヤー {use.player} ではない")
        if decision.kind == DISCARD_FROM_HAND:
            expected, bounds = tuple(state.players[use.player].hand), (self.discard, self.discard)
        elif decision.kind == RETRIEVE_ENERGY:
            discarded = tuple(decision.context_value("discarded", ()))
            since = max((i for i, e in enumerate(state.log) if e["kind"] == "play_trainer" and e["card"] == use.card), default=None)
            logged = None if since is None else next((tuple(e["cards"]) for e in state.log[since:] if e["kind"] == "discard_from_hand"), None)
            if logged is None or logged != discarded:
                problems.append(f"「エネルギー回収」の回収の決定の discarded {discarded} が、ログの手札のトラッシュ {logged} と合わない")
            expected = _retrievable_energy(state, use.player, discarded)
            bounds = (0, min(self.retrieve, len(expected)))
            if not expected:
                problems.append("「エネルギー回収」の回収の決定に、選べる基本エネルギーカードがない")
        else:
            return problems + [f"「エネルギー回収」の決定の種類が {decision.kind!r}（{DISCARD_FROM_HAND}・{RETRIEVE_ENERGY} のはず）"]
        if (decision.min_choices, decision.max_choices) != bounds:
            problems.append(f"「エネルギー回収」の決定 {decision.kind} で選ぶ数が {decision.min_choices}〜{decision.max_choices}（{bounds} のはず）")
        if decision.options != expected:
            problems.append(f"「エネルギー回収」の決定 {decision.kind} の選べるもの {decision.options} が {expected} と合わない")
        if use.card in decision.options:
            problems.append("「エネルギー回収」の決定で、使っているこのカードを選べる")
        return problems


def _is_pokemon_card(state: GameState, uid: int) -> bool:
    """v0.24: 「たねポケモン」または「進化カード」（1 進化・2 進化）か。既存のカードの定義（``is_basic_pokemon``・``is_evolution_pokemon``）で決める。"""
    definition = state.card_def(uid)
    return definition.is_basic_pokemon or definition.is_evolution_pokemon


@dataclass(frozen=True)
class TradePokemonWithDeck(TrainerEffect):
    """使うための条件として手札の「たねポケモン」または「進化カード」を 1 枚選び、相手に見せてから山札にもどし、その後、山札の「たねポケモン」
    または「進化カード」を 1 枚選び出し、相手に見せてから手札に加え、その山札を切る（ポケモン交換おじさん。p.259 の最新の説明「手札から
    「たねポケモン」または「進化カード」を1枚選び、相手プレイヤーに見せてから、あなたの山札にもどす。それができないとき、このカードは使えない。
    あなたの山札から「たねポケモン」または「進化カード」を1枚選び出し、相手プレイヤーに見せてから、手札に加える。その後、その山札をよく
    切る。」。v0.24。docs/pokemon-trader-v0.24.md の PT1〜PT19）。

    - 使うための条件（PT2・PT3）: 使っているこのカードは p.310 の手順 1 で手札から出している。``check_playable`` は手札から出す前に呼ばれる
      ので、このカードを除く手札にたねポケモン・進化カードがなければ ``IllegalActionError("NO_POKEMON_CARD_IN_HAND")``（拒否したら
      カードは手札に残る）。山札の中身（見えない情報）は条件にしない。もどしたカードは山札に入るので、山札にたねポケモン・進化カードが
      なくても・山札が 0 枚でも、選び出すものはある（p.259 の解説「山札の中にポケモンのカードがなかったら、交換のために入れたポケモン
      カードを持ってくることになります」。PT10・PT11）。
    - 段階 1（PT4〜PT8）: 使ったプレイヤーが手札のたねポケモン・進化カードから 1 枚を選び（決定 ``RETURN_TO_DECK``）、相手に見せてから
      山札の一番下にもどす（``zones.return_hand_to_deck``。ログ ``return_to_deck`` は公開）。手札をトラッシュする効果ではない。
    - 段階 2（PT9〜PT13）: 使ったプレイヤーが山札のたねポケモン・進化カード（段階 1 でもどしたカードを含む。uid の小さい順。``context`` の
      ``"returned"``）から 1 枚を選び出し（決定 ``SEARCH_DECK``。省略できない）、相手に見せてから手札に加え（``zones.reveal_deck_to_hand``。
      ログ ``reveal_from_deck`` は公開。選べたほかの山札のカードはログに書かない）、その山札を切る（``zones.shuffle_deck``）。
    - 不正な答えは決定の確認が拒否し、決定は待ったまま。段階 2 で拒否しても、段階 1（山札にもどしたこと）は取り消さない。
    """

    implementation_id = "trade_pokemon_with_deck"

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if not any(uid != use.card and _is_pokemon_card(state, uid) for uid in state.players[use.player].hand):
            raise IllegalActionError(
                "NO_POKEMON_CARD_IN_HAND",
                "このカードを除く手札に「たねポケモン」・「進化カード」がなく、使うための条件（1 枚選び、相手プレイヤーに見せてから、山札に"
                "もどす）を満たせない（p.259・p.310）",
            )

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        options = [uid for uid in state.players[use.player].hand if _is_pokemon_card(state, uid)]
        push_trainer_decision(state, use, kind=RETURN_TO_DECK, player=use.player, options=options, min_choices=1, max_choices=1)

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if decision.kind == RETURN_TO_DECK:
            (returned,) = choices
            return_hand_to_deck(state, use.player, returned)
            options = sorted(uid for uid in state.players[use.player].deck if _is_pokemon_card(state, uid))
            push_trainer_decision(
                state, use, kind=SEARCH_DECK, player=use.player, options=options, context=(("returned", returned),),
                min_choices=1, max_choices=1,
            )
            return
        (card,) = choices
        reveal_deck_to_hand(state, use.player, card)
        shuffle_deck(state, use.player)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        """決定するのは使ったプレイヤー。段階 1 は手札のたねポケモン・進化カード（手札の並び）から 1 枚、段階 2 は山札のたねポケモン・
        進化カード（uid の小さい順。もどしたカードを含む）から 1 枚。段階 2 の ``"returned"`` は、今のログの最後のこのカードの
        ``play_trainer`` のあとの ``return_to_deck`` のカードと同じで、山札にあり、選べるものに入る。"""
        p = state.players[use.player]
        problems = []
        if decision.player != use.player:
            problems.append(f"「ポケモン交換おじさん」の決定を決定するのがプレイヤー {decision.player} で、使ったプレイヤー {use.player} ではない")
        if decision.kind == RETURN_TO_DECK:
            expected = tuple(uid for uid in p.hand if _is_pokemon_card(state, uid))
        elif decision.kind == SEARCH_DECK:
            expected = tuple(sorted(uid for uid in p.deck if _is_pokemon_card(state, uid)))
            returned = decision.context_value("returned", None)
            since = max((i for i, e in enumerate(state.log) if e["kind"] == "play_trainer" and e["card"] == use.card), default=None)
            logged = None if since is None else next((e["card"] for e in state.log[since:] if e["kind"] == "return_to_deck"), None)
            if returned is None or logged != returned:
                problems.append(f"「ポケモン交換おじさん」の山札を選ぶ決定の returned {returned} が、ログの山札にもどしたカード {logged} と合わない")
            elif returned not in expected:
                problems.append(f"「ポケモン交換おじさん」で山札にもどしたカード {returned} が、山札の選べるものにない")
        else:
            return problems + [f"「ポケモン交換おじさん」の決定の種類が {decision.kind!r}（{RETURN_TO_DECK}・{SEARCH_DECK} のはず）"]
        if (decision.min_choices, decision.max_choices) != (1, 1):
            problems.append(f"「ポケモン交換おじさん」の決定 {decision.kind} で選ぶ数が {decision.min_choices}〜{decision.max_choices}（1 枚のはず）")
        if decision.options != expected:
            problems.append(f"「ポケモン交換おじさん」の決定 {decision.kind} の選べるもの {decision.options} が {expected} と合わない")
        if use.card in decision.options:
            problems.append("「ポケモン交換おじさん」の決定で、使っているこのカードを選べる")
        return problems


# 1 進化を飛ばして 2 進化させる組（自分の場のたねポケモンと手札の 2 進化カード）の扱い（v0.25。ポケモン育て屋さん）
SKIP_EVOLUTION_OK = "ok"  # 進化させられる
SKIP_EVOLUTION_HP = "hp"  # 進化したあとの HP がのっているダメージ以下（UNRESOLVED_EVOLUTION_HP。v0.4a の H1）
SKIP_EVOLUTION_UNSUPPORTED_CARD = "unsupported_card"  # 2 進化カードが未対応（UNSUPPORTED_EVOLUTION）
SKIP_EVOLUTION_UNKNOWN_LINEAGE = "unknown_lineage"  # 写しのカードのデータで系統を確かめられない（UNSUPPORTED_EVOLUTION_LINEAGE）
SKIP_EVOLUTION_PLAY_ROLE = "play_role"  # v0.47: 場のなにかの化石（場での役割のポケモン）に重ねる組（PF3。UNRESOLVED_BREEDER_ON_PLAY_AS_POKEMON）
SKIP_EVOLUTION_DEVOLVED = "devolved"  # v0.50: 今の番に退化したたねポケモンに重ねる組（DV2。UNRESOLVED_EVOLVE_AFTER_DEVOLUTION）
_EVOLUTION_HP_REASON = (
    "進化すると HP がのっているダメージ以下になる。そのときにきぜつするか（いつきぜつの判定をするか）は『オフィシャルブック2000』"
    "（p.310・p.323）から決められないので扱わない"
)


def skip_evolution_pairs(state: GameState, player: int) -> dict[int, list[tuple[int, str]]]:
    """1 進化を飛ばして 2 進化させられる組（v0.25。p.259 のポケモン育て屋さん。docs/pokemon-breeder-v0.25.md の BR3〜BR10）。

    自分の場（バトル場・ベンチ）のたねポケモン（重なりのないたねポケモンのカード）で、その番の最初から場に出ていたもの（p.310。今の番に
    場に出したポケモンは進化させられない）ごとに、手札の 2 進化カードのうち系統の合うもの（2 進化カードの「○○○○から進化」の 1 進化カード
    （写しのカードのデータ）の進化元の名前が、そのたねポケモンの名前と同じ。``evolution.skipped_stage1_basic``）と、その組の扱い
    （``SKIP_EVOLUTION_…``）。系統を写しで確かめられない 2 進化カードは、どのたねポケモンとも「確かめられない」組にする（推測で合う・
    合わないを決めない）。場のポケモンの番号は場の並び（バトル場 → ベンチ）、カードは手札の並び。おたがいの最初の番は呼ぶ側が確かめる。
    """
    p = state.players[player]
    cards = [uid for uid in p.hand if state.card_def(uid).is_stage2_pokemon]
    pairs: dict[int, list[tuple[int, str]]] = {}
    for pokemon in p.in_play():
        current = state.card_def(pokemon.card)
        # v0.44: その番の最初から場に出ていたかは通常の進化と共通の ``evolution.turn_restriction``（トレーナー「サカキ」の許可のあるポケモンは、今の番に場に出した
        # ポケモンでも進化させてよい。手札から重ねる進化なので許可が当てはまる。docs/search-evolution-once-attacks-v0.44.md 4 章）
        devolved = devolved_this_turn(state, pokemon)
        if pokemon.evolution_stack or not current.is_basic_pokemon or (not devolved and turn_restriction(state, pokemon) is not None):
            continue  # v0.50: 今の番に退化したたねポケモンは p.310 の制限を当てはめず、DV2 の組にする（下）
        if evolution_forbidden(state, pokemon) is not None:
            continue  # v0.49: 説明が進化を禁じるポケモン（メタモンの「このカードに進化カードをつけることはできない」）には重ねない
        for uid in cards:
            definition = state.card_def(uid)
            basic = skipped_stage1_basic(definition)
            if basic is None:
                status = SKIP_EVOLUTION_UNKNOWN_LINEAGE
            elif basic != current.name_ja:
                continue
            elif current.play_role is not None:
                status = SKIP_EVOLUTION_PLAY_ROLE  # v0.47: 系統は合うが、印刷のたねポケモンではない（PF3）
            elif not definition.supported:
                status = SKIP_EVOLUTION_UNSUPPORTED_CARD
            elif devolved:
                status = SKIP_EVOLUTION_DEVOLVED  # v0.50: 今の番に退化したポケモン（DV2）
            elif pokemon.damage >= evolution_hp(state, pokemon, uid):  # v0.48: 重ねたあとの最大HP
                status = SKIP_EVOLUTION_HP
            else:
                status = SKIP_EVOLUTION_OK
            pairs.setdefault(pokemon.pokemon_id, []).append((uid, status))
    return pairs


def _selectable_skip_evolutions(state: GameState, player: int) -> dict[int, list[tuple[int, str]]]:
    """決定で選べる組（進化させられる組と、原典で決められない HP の組・v0.47 の場のなにかの化石の組（PF3））。エンジンが確かめられない組（未対応のカード・
    系統を確かめられないカード）は選べるものに入れない。"""
    selectable = {}
    for pokemon_id, entries in skip_evolution_pairs(state, player).items():
        kept = [(uid, status) for uid, status in entries if status in (SKIP_EVOLUTION_OK, SKIP_EVOLUTION_HP, SKIP_EVOLUTION_PLAY_ROLE, SKIP_EVOLUTION_DEVOLVED)]
        if kept:
            selectable[pokemon_id] = kept
    return selectable


def _skip_unresolved_targets(selectable: dict[int, list[tuple[int, str]]]) -> tuple[list[int], list[int], list[int]]:
    """v0.47: 段階 1 で選ぶと止める場のポケモン: (どの組も HP の組のポケモン, 場のなにかの化石（PF3）, v0.50: 今の番に退化したポケモン（DV2）)。"""
    hp_only = [pid for pid, entries in selectable.items() if all(status == SKIP_EVOLUTION_HP for _, status in entries)]
    role = [pid for pid, entries in selectable.items() if all(status == SKIP_EVOLUTION_PLAY_ROLE for _, status in entries)]
    devolved = [pid for pid, entries in selectable.items() if all(status == SKIP_EVOLUTION_DEVOLVED for _, status in entries)]
    return hp_only, role, devolved


def _skip_stage1_unresolved(selectable: dict[int, list[tuple[int, str]]]) -> tuple[list[int], str, str]:
    """段階 1 の決定の選ぶと止める選択とそのコード・理由。場のなにかの化石（PF3）があればそれ、v0.50: 次に今の番に退化したポケモン（DV2）、なければ HP の組
    （v0.25 と同じ）。2 種類が同じ決定にあることはない（``check_playable`` が使う前に止める。1 つの決定に止めるコードは 1 つ）。"""
    hp_only, role, devolved = _skip_unresolved_targets(selectable)
    if role:
        return role, BREEDER_PLAY_AS_POKEMON_CODE, BREEDER_PLAY_AS_POKEMON_REASON
    if devolved:
        return devolved, DEVOLVED_THIS_TURN_CODE, DEVOLVED_THIS_TURN_REASON
    return hp_only, "UNRESOLVED_EVOLUTION_HP", _EVOLUTION_HP_REASON


@dataclass(frozen=True)
class EvolveBasicToStage2(TrainerEffect):
    """自分の場のたねポケモンの上に、手札の 2 進化カードを直接重ね、1 進化を飛ばして 2 進化ポケモンに進化させる（ポケモン育て屋さん。
    p.259 の最新の説明「このカードは、あなたが自分の場にいるポケモンを進化させるときにだけ、使える。そのポケモンの上に「2進化カード」を
    直接のせ、1進化をとばして「2進化ポケモン」に進化させる。」。v0.25。docs/pokemon-breeder-v0.25.md の BR1〜BR22）。

    - 使うための条件（BR2）: 進化させるときにだけ使える。おたがいの最初の番は ``FIRST_TURN_EVOLUTION``（p.310。BR9）。進化させられる組
      （``skip_evolution_pairs``）がなければ使えない: 原典で決められない組（HP）だけなら ``UNRESOLVED_EVOLUTION_HP``、エンジンが
      確かめられない組（未対応のカード・写しで系統を確かめられないカード）だけなら ``UNSUPPORTED_EVOLUTION``・
      ``UNSUPPORTED_EVOLUTION_LINEAGE``（``UnsupportedError``）、ほかは ``IllegalActionError("NO_EVOLUTION_TARGET")``。どれも手札から
      出す前（拒否したらカードは手札に残る）。
    - 段階 1（BR16）: 使ったプレイヤーが、進化させる自分の場のたねポケモンを選ぶ（決定 ``SELECT_POKEMON``。p.310 の進化の手順 1 の順で、
      ポケモンを先に示す）。段階 2: そのポケモンの上に重ねる手札の 2 進化カードを選ぶ（決定 ``SELECT_EVOLUTION_CARD``。``context`` の
      ``"target"``）。HP の組は選べるが、選ぶと ``UNRESOLVED_EVOLUTION_HP``（``unresolved_choices``）。
    - 進化（BR11〜BR15）: 通常の進化と同じ手順（``evolution.place_evolution_card``。特殊状態・持続する効果・にげるの失敗の記録を消し、
      ダメージ・エネルギー・ついているトレーナー・場のポケモンの番号・場に出た番は受け継ぐ）。重なりはたねポケモン + 2 進化の 2 枚で、1 進化の
      カードは使わない（作らない・動かさない）。ログ ``evolve`` に ``trainer_card``（このカードの uid）を書く。
    - 通常の操作（``EvolvePokemon``）の確認（名前・段階）は変えていない。たねポケモンに 2 進化カードを直接重ねられるのは、このカードの効果だけ。
    """

    implementation_id = "evolve_basic_to_stage2"
    skips_stage1_evolution = True

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        prevented = evolution_prevented(state)
        if prevented is not None:
            # v0.47: ［げんしのちから］がはたらいていると、どのポケモンも進化できない（使えない。手札から出す前）
            raise IllegalActionError(*prevented)
        if state.turn_number <= 2:
            raise IllegalActionError("FIRST_TURN_EVOLUTION", "おたがいのプレイヤーの最初の番には、ポケモンを進化させられない（p.310・p.259）")
        statuses = {status for entries in skip_evolution_pairs(state, use.player).values() for _, status in entries}
        hp_only, role, devolved = _skip_unresolved_targets(_selectable_skip_evolutions(state, use.player))
        if hp_only and role or role and devolved:
            # v0.47: 選ぶと止める選択が 2 種類（HP・場のなにかの化石）になる。1 つの決定に止めるコードは 1 つなので、使う前に PF3 で止める
            raise UnsupportedError(BREEDER_PLAY_AS_POKEMON_CODE, BREEDER_PLAY_AS_POKEMON_REASON)
        if hp_only and devolved:
            raise UnsupportedError(DEVOLVED_THIS_TURN_CODE, DEVOLVED_THIS_TURN_REASON)  # v0.50: 同じく 2 種類（HP・今の番に退化したポケモン）
        if SKIP_EVOLUTION_OK in statuses:
            return
        if SKIP_EVOLUTION_PLAY_ROLE in statuses:
            raise UnsupportedError(BREEDER_PLAY_AS_POKEMON_CODE, BREEDER_PLAY_AS_POKEMON_REASON)
        if SKIP_EVOLUTION_DEVOLVED in statuses:
            raise UnsupportedError(DEVOLVED_THIS_TURN_CODE, DEVOLVED_THIS_TURN_REASON)  # v0.50: 今の番に退化したたねポケモンの組だけ（DV2）
        if SKIP_EVOLUTION_HP in statuses:
            raise UnsupportedError("UNRESOLVED_EVOLUTION_HP", _EVOLUTION_HP_REASON)
        if SKIP_EVOLUTION_UNSUPPORTED_CARD in statuses:
            raise UnsupportedError("UNSUPPORTED_EVOLUTION", "1 進化を飛ばして重ねられる手札の 2 進化カードが未対応")
        if SKIP_EVOLUTION_UNKNOWN_LINEAGE in statuses:
            raise UnsupportedError(
                "UNSUPPORTED_EVOLUTION_LINEAGE",
                "手札の 2 進化カードの進化元の 1 進化カードが写しにない（または進化元が食い違う）ので、どのたねポケモンに重ねられるかを確かめられない",
            )
        raise IllegalActionError(
            "NO_EVOLUTION_TARGET",
            "自分の場に、その番の最初から場に出ていたたねポケモンと、手札にその系統の 2 進化カードの組がなく、進化させられない"
            "（このカードは進化させるときにだけ使える。p.259）",
        )

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        selectable = _selectable_skip_evolutions(state, use.player)
        options = list(selectable)
        unresolved, code, reason = _skip_stage1_unresolved(selectable)
        push_trainer_decision(
            state, use, kind=SELECT_POKEMON, player=use.player, options=options, min_choices=1, max_choices=1,
            unresolved_choices=unresolved, unresolved_code=code, unresolved_reason=reason,
        )

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if decision.kind == SELECT_POKEMON:
            (target,) = choices
            entries = _selectable_skip_evolutions(state, use.player)[target]
            push_trainer_decision(
                state, use, kind=SELECT_EVOLUTION_CARD, player=use.player, options=[uid for uid, _ in entries],
                context=(("target", target),), min_choices=1, max_choices=1,
                unresolved_choices=[uid for uid, status in entries if status == SKIP_EVOLUTION_HP],
                unresolved_code="UNRESOLVED_EVOLUTION_HP", unresolved_reason=_EVOLUTION_HP_REASON,
            )
            return
        (card,) = choices
        target = decision.context_value("target")
        if (card, SKIP_EVOLUTION_OK) not in _selectable_skip_evolutions(state, use.player).get(target, []):
            raise RuntimeError(f"場のポケモン {target} にカード {card} を 1 進化を飛ばして重ねられない（決定の確認の漏れ。エンジンの不具合）")
        pokemon = state.find_pokemon(target)[1]
        place_evolution_card(state, use.player, pokemon, card, trainer=use.card)
        # v0.43: 場に出たときに使える特殊能力（わるいカイリューの［てしたをよぶ］）があれば、使うかを聞き、そのあとこのトレーナーの処理（トラッシュ）にもどる
        # （手札から出したカード。docs/declared-entry-powers-v0.43.md 3 章）
        offer_entry_power(state, use.player, pokemon, from_hand=True, return_to=("trainer", use.player, use.card, use.card_id))

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        """決定するのは使ったプレイヤー。段階 1 は進化させられる自分の場のたねポケモン（場の並び）から 1 匹、段階 2 はそのポケモンに
        1 進化を飛ばして重ねられる手札の 2 進化カード（手札の並び）から 1 枚。原典で決められない組（HP）は ``unresolved_choices``。"""
        selectable = _selectable_skip_evolutions(state, use.player)
        what = "「ポケモン育て屋さん」"
        if decision.kind == SELECT_POKEMON:
            unresolved, code, _ = _skip_stage1_unresolved(selectable)
            problems = _select_own_pokemon_problems(decision, use, selectable, what, unresolved)
            if unresolved and decision.context_value("unresolved_code", None) != code:
                problems.append(f"{what}の決定の止めるコード {decision.context_value('unresolved_code', None)!r} が {code} ではない")
            return problems
        if decision.kind != SELECT_EVOLUTION_CARD:
            return [f"{what}の決定の種類が {decision.kind!r}（{SELECT_POKEMON}・{SELECT_EVOLUTION_CARD} のはず）"]
        problems = []
        if decision.player != use.player:
            problems.append(f"{what}の決定を決定するのがプレイヤー {decision.player} で、使ったプレイヤー {use.player} ではない")
        target = decision.context_value("target", None)
        if target not in selectable:
            return problems + [f"{what}の 2 進化カードを選ぶ決定の target {target!r} が、進化させられる自分の場のたねポケモンではない"]
        entries = selectable[target]
        if (decision.min_choices, decision.max_choices) != (1, 1):
            problems.append(f"{what}の決定で選ぶ数が {decision.min_choices}〜{decision.max_choices}（1 枚のはず）")
        if decision.options != tuple(uid for uid, _ in entries):
            problems.append(f"{what}の決定の選べるもの {decision.options} が、重ねられる手札の 2 進化カード {[uid for uid, _ in entries]} と合わない")
        unresolved = tuple(uid for uid, status in entries if status == SKIP_EVOLUTION_HP)
        if tuple(decision.context_value("unresolved_choices", ())) != unresolved:
            problems.append(f"{what}の決定の扱いを決められない選択 {decision.context_value('unresolved_choices', ())} が、{unresolved} と合わない")
        return problems


def _select_own_pokemon_problems(
    decision: PendingDecision, use: TrainerUse, expected: Iterable[int], what: str, unresolved: Iterable[int] = (), whose: str = "自分"
) -> list[str]:
    """トレーナーを使ったプレイヤーが場のポケモンを 1 匹選ぶ決定（``SELECT_POKEMON``）の形の問題（v0.4e）。

    ``expected`` は選べるもの（場のポケモンの番号。決定を出したときと同じ並び）、``unresolved`` は、そのうち原典で扱いを
    決められない選択（``context`` の ``"unresolved_choices"``）。選ぶのはいつもトレーナーを使ったプレイヤーで、v0.21 の突風は
    相手の場のポケモンを選ぶ（``whose`` は理由の文に書く、選べるポケモンの持ち主。既定は自分）。"""
    problems = []
    if decision.player != use.player:
        problems.append(f"{what}の決定を決定するのがプレイヤー {decision.player} で、使ったプレイヤー {use.player} ではない")
    if decision.kind != SELECT_POKEMON:
        problems.append(f"{what}の決定の種類が {decision.kind!r}（{SELECT_POKEMON} のはず）")
    if (decision.min_choices, decision.max_choices) != (1, 1):
        problems.append(f"{what}の決定で選ぶ数が {decision.min_choices}〜{decision.max_choices}（1 匹のはず）")
    expected = tuple(expected)
    if decision.options != expected:
        problems.append(f"{what}の決定の選べるもの {decision.options} が、選べる{whose}の場のポケモン {expected} と合わない")
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
        switch_max_hp_drop_check(state, use.player)  # v0.48: MH1（手札から出す前。決定への答えで止めない）

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        bench = state.players[use.player].bench
        push_trainer_decision(
            state, use, kind=SELECT_POKEMON, player=use.player, options=[pokemon.pokemon_id for pokemon in bench]
        )

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        _switch_active_with_bench(state, use.player, choices[0])

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        """選べるのは自分のベンチのポケモン（控えポケモン）。"""
        bench = state.players[use.player].bench
        return _select_own_pokemon_problems(decision, use, (pokemon.pokemon_id for pokemon in bench), "「ポケモンいれかえ」")


def switch_max_hp_drop_check(state: GameState, owner: int) -> None:
    """トレーナーの効果で ``owner`` の対戦ポケモンを控えと入れ替える前の確かめ（v0.48。MH1）。複製の上で、最初の控えと入れ替えた（ベンチにもどった対戦ポケモンの特殊状態・
    ワザによる持続する効果が消え、［へんしょく］の記録に「ベンチにもどった」をつけた）状態を作り、最大HPがのっているダメージ以下に下がるポケモンがいれば止める
    （``max_hp_drops``・``max_hp_drop_error``）。最大HPが下がりうるのはベンチにもどる対戦ポケモン（「きょだいか」の効果が消える）と、消えた特殊状態でまたはたらく
    かがくへんかガスの影響を受けるポケモンで、どの控えを選んでも同じなので、決定を出す前（手札から出す前）に止める（答えで止めると、ほかの答えがなく進めない）。
    渡した状態・乱数・ログは変えない。"""
    p = state.players[owner]
    if p.active is None or not p.bench:
        return
    # v0.49: メタモンの［へんしん］では、入れ替えでバトル場に出る控え（相手の対戦ポケモン）によって最大HPが変わるので、どの控えを選んでも下がるときだけ止める
    # （最初の控えの理由の文。v0.48 までに起こる組は、どの控えでも同じ）。一部の控えで下がるなら、その答えを受け付けない（``engine._apply``）
    first = None
    for pokemon in p.bench:
        trial = state.clone()
        _switch_active_with_bench(trial, owner, pokemon.pokemon_id)
        drops = max_hp_drops(state, trial)
        if not drops:
            return
        first = drops if first is None else first
    raise max_hp_drop_error(first)


def switch_choice_stops(state: GameState, owner: int) -> list[tuple[int, str, str]]:
    """``owner`` の対戦ポケモンと入れ替える控えごとに、入れ替えたあと受け付けられない状態（決められない姿・MH1。``state_stop_after``）になるなら
    (控えの番号, コード, 理由の文)（v0.49。コインのあとに入れ替える特殊能力（かおりのわな）が、どの控えでも止まるときにコインの前に止めるため）。状態を変えない。"""
    blocked = []
    for pokemon in state.players[owner].bench:
        trial = state.clone()
        _switch_active_with_bench(trial, owner, pokemon.pokemon_id)
        stop = state_stop_after(state, trial)
        if stop is not None:
            blocked.append((pokemon.pokemon_id, *stop))
    return blocked


def _switch_active_with_bench(state: GameState, owner: int, pokemon_id: int, *, effect: str | None = None) -> None:
    """トレーナーの効果で、プレイヤー ``owner`` の対戦ポケモンと、``owner`` のベンチの ``pokemon_id`` のポケモンを入れ替える。
    ポケモンいれかえ（v0.2b。``owner`` は使ったプレイヤー）と突風（v0.21。``owner`` は相手）で共通の処理で、v0.20 までの
    ``SwitchWithBench.resume`` の本体をそのまま関数にした（動作・ログ・順番は同じ）。選ぶ・確かめるのは呼ぶ側。

    - 「にげる」ではない（p.325）。にげるエネルギーは払わず、「にげる」の失敗の記録（v0.3c）にも関わらない。
    - 場のポケモン（``PokemonInPlay``）ごと入れ替えるので、ついているカード（エネルギー・トレーナー）・ダメージカウンター・重なり・
      場のポケモンの番号はいっしょに移る（p.311）。もとの対戦ポケモンは、選んだポケモンがいたベンチの位置に入る。
    - ベンチに戻ったもとの対戦ポケモンの特殊状態・ワザによる持続する効果は消える（p.322。理由は ``SWITCH``）。ねむり・マヒでも
      入れ替える（p.325）。
    - ログ ``switch`` の ``player`` は入れ替わる場の持ち主（ポケモンいれかえでは使ったプレイヤーと同じ。突風では相手。使った
      プレイヤーは、その前の ``play_trainer`` の ``player``）。
    - ``effect``（v0.34）: ワザの効果で自分のポケモンを入れ替えたとき（ナッシーの「テレポート」）のワザの識別子（``AttackKey`` の文字列）。
      渡したときだけログ ``switch`` に ``effect`` を書く（トレーナーの入れ替えのログの形は v0.33 と同じ）。入れ替えの処理・消える理由
      （``SWITCH``）はトレーナーと同じ（p.311・p.322 の「ベンチにもどったら」は入れ替えの原因を問わない）。
    """
    p = state.players[owner]
    index = next(i for i, pokemon in enumerate(p.bench) if pokemon.pokemon_id == pokemon_id)
    old = p.active
    p.active, p.bench[index] = p.bench[index], old
    extra = {} if effect is None else {"effect": effect}
    state.add_event(
        "switch",
        player=owner,
        old_active=old.card,
        new_active=p.active.card,
        old_active_pokemon_id=old.pokemon_id,
        new_active_pokemon_id=p.active.pokemon_id,
        **extra,
    )
    # ベンチに戻ったポケモンの特殊状態はすべて消える（p.322。「にげる」と同じ処理。v0.3a）
    clear_special_conditions(state, owner, old, SWITCH)
    # ワザによる持続する効果も消える（p.322「通常、「持続する効果」を受けたポケモンがベンチにもどったら…消えてなくなります」。v0.4b）
    remove_persistent_effects(state, owner, old, SWITCH)
    mark_returned_to_bench(old)  # v0.48: 特殊能力で色を変えた記録に、ベンチにもどったことを残す（VS1）


@dataclass(frozen=True)
class SwitchOpponentWithBench(TrainerEffect):
    """相手の控えポケモンを 1 匹選び、相手の対戦ポケモンと入れ替える（突風。p.255 の最新の説明「相手の控えポケモンを1匹選び、相手の
    対戦ポケモンと入れ替える。」。v0.21。docs/gust-v0.21.md）。

    - 選ぶのは突風を使ったプレイヤー（GW2。最新の説明に「相手は」がない。p.255 の解説「相手のベンチからポケモンを選んでバトル場に
      呼んできます」）。決定（``SELECT_POKEMON``）の ``player`` は使ったプレイヤーで、相手ではない。バタフリーの「ふきとばし」（相手が
      選ぶ。p.19。v0.4d の F3）とは選ぶプレイヤーが違うので、その処理（``FORCED_SWITCH``・ログ ``forced_switch``）は使わない。
    - 選べるのは相手のベンチのポケモン（場のポケモンの番号）だけ。自分の場のポケモン・相手の対戦ポケモンは選べない（GW3）。1 匹でも
      決定を出す（ポケモンいれかえと同じ）。自分の場（ベンチの有無）は関係しない（GW6）。
    - 入れ替えは、ポケモンいれかえと同じ ``_switch_active_with_bench`` を相手の場で行う（GW7〜GW12: にげるエネルギーを払わない・
      ついているカードとダメージカウンターはいっしょに移る・特殊状態と持続する効果は消える・ねむり・マヒでも入れ替える）。
    - トレーナーの効果なので「とうめい」ははたらかない（p.159。v0.9 の T29。``attack_reaches`` を呼ばない）。
    - 乱数は使わない。使っても番は終わらない（p.310）。

    原典で決められないので扱わない（``UnsupportedError``）: 相手に控えポケモンがいないときに使えるか（GW5）。

    v0.40: 使ったプレイヤーの対戦ポケモンが、この番、相手のポケモンの「すごむ」（``state.CannotAttackWhileSourceActive``。「このカードがバトル場にいる限り、
    ワザを使えない」）を受けていて、その効果を与えたポケモン（「このカード」）が相手のベンチにいる（この番にバトル場をはなれた）とき、そのポケモンを選んで
    バトル場にもどしたあとの扱い（「いる限り」が、はなれた時点で終わるのか、もどればまたはたらくのか）は、kyuura の記録・印刷の文面から決められない（SG1）。
    そのポケモンは選べるが、選ぶと ``UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED`` で止める（``unresolved_choices``）。選べる控えがそのポケモンだけなら、使う前に止める。
    """

    implementation_id = "switch_opponent_with_bench"

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if not state.players[1 - use.player].bench:
            raise UnsupportedError(
                "UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH",
                "相手に控えポケモンがいない。このときに「突風」を使えるかは、『オフィシャルブック2000』（p.255・p.310）から決められない"
                "ので扱わない（第1弾の印刷の文面の「相手に控えがいない場合は使えない」は、p.255 の最新の説明にない）",
            )
        returning = _returning_lock_sources(state, use.player)
        if returning and len(returning) == len(state.players[1 - use.player].bench):
            raise UnsupportedError("UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED", _ATTACK_LOCK_SOURCE_RETURNED_REASON)
        switch_max_hp_drop_check(state, 1 - use.player)  # v0.48: MH1（手札から出す前。決定への答えで止めない）

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        bench = state.players[1 - use.player].bench
        push_trainer_decision(
            state, use, kind=SELECT_POKEMON, player=use.player, options=[pokemon.pokemon_id for pokemon in bench],
            unresolved_choices=_returning_lock_sources(state, use.player), unresolved_code="UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED",
            unresolved_reason=_ATTACK_LOCK_SOURCE_RETURNED_REASON,
        )

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        _switch_active_with_bench(state, 1 - use.player, choices[0])

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        """決定するのは使ったプレイヤーで、選べるのは相手のベンチのポケモン（控えポケモン）。v0.40: 選ぶと止める選択は SG1 のポケモン。"""
        bench = state.players[1 - use.player].bench
        return _select_own_pokemon_problems(
            decision, use, (pokemon.pokemon_id for pokemon in bench), "「突風」", unresolved=_returning_lock_sources(state, use.player), whose="相手"
        )


_ATTACK_LOCK_SOURCE_RETURNED_REASON = (
    "このポケモンは、使ったプレイヤーの対戦ポケモンに「すごむ」（「次の相手の番、このカードがバトル場にいる限り、ワザを使えない」）の効果を与えたポケモンで、"
    "この番にバトル場をはなれている。バトル場にもどしたあと、その効果がまたはたらくか（「いる限り」が、はなれた時点で終わるか）は、kyuura の記録・印刷の文面から"
    "決められないので扱わない（SG1）"
)


def _returning_lock_sources(state: GameState, user: int) -> tuple[int, ...]:
    """v0.40（SG1）: プレイヤー ``user`` の対戦ポケモンが今の番に受けている「すごむ」（``CannotAttackWhileSourceActive``）の、効果を与えたポケモンのうち、相手の
    ベンチにいるもの（場のポケモンの番号。ベンチの並び）。効果を与えたのは前の番の相手のワザで、そのときバトル場にいたので、ベンチにいればこの番にはなれた。"""
    from .state import CannotAttackWhileSourceActive

    active = state.players[user].active
    if active is None:
        return ()
    sources = {effect.source_card for effect in active.persistent_effects
               if isinstance(effect, CannotAttackWhileSourceActive) and effect.active_turn == state.turn_number and effect.source_player == 1 - user}
    return tuple(pokemon.pokemon_id for pokemon in state.players[1 - user].bench if pokemon.card in sources)


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

    def damage_modifiers(self, state: GameState, attached: AttachedTrainer, role: str, *, bench: bool = False) -> list[DamageModifier]:
        if role != "attacker" or bench:
            # v0.31: 控えポケモンへのダメージは変えない（p.257 の最新の説明「(控えポケモンへのダメージは、そのまま)」。CONFIRMED）
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

    def damage_modifiers(self, state: GameState, attached: AttachedTrainer, role: str, *, bench: bool = False) -> list[DamageModifier]:
        # v0.31: 控えポケモンが受けるワザのダメージにも効く（「このカードをつけているポケモンがワザによるダメージを受けるとき」。バトル場に
        # かぎらない。docs/defender-v0.2e.md の 16。SUPPORTED）
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
    - ``play_text_ja``: 実装がしたがう文面（『オフィシャルブック2000』の「最新の説明」。2026-10-15 からの方針の採用の記録で登録した
      ものは ``AttackEntry`` と同じ）
    - ``source``: ``play_text_ja`` の出典（誌面のページ。採用の記録で登録したものは ``AttackEntry`` と同じ）
    """

    effect: TrainerEffect
    name_ja: str
    text_ja: str
    play_text_ja: str
    source: str


# ---------------------------------------------------------------- v0.42 のワザ（docs/power-decisions-v0.42.md）。要素は ``resolution.programs`` の
# ``ChosenOpponentHealThenDraw``・``ReturnOwnEnergyToHand``・``CountersToRemainingHp``・``EvolveFromDeck``・``ReturnOwnPokemonToHand`` と既存の要素。説明の文面は、
# 登録したワザの印刷の文面（kyuura の写し）と完全に同じものだけを受け付ける（v0.37 の約束）


@dataclass(frozen=True)
class HealChosenOpponentThenDraw(AttackEffect):
    """相手の場にいるポケモンを 1 匹選び、そのポケモンにのっているダメージカウンターを、好きなだけとりのぞく。とりのぞいた数ぶんのカードを自分の山札から引いて、
    手札に加える（v0.42。ナツメのルージュラの「よいおこない」。ダメージの目安の数字はない）。要素 ``ChosenOpponentHealThenDraw``（決定 ``select_pokemon`` →
    ``remove_counters``。0 個は HC5 と同じ問いで、選ぶと止める）。"""

    implementation_id = "heal_chosen_opponent_then_draw"
    opponent_effect_elements = (HEAL_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        expected = ("相手の場にいるポケモンを1匹選び、そのポケモンにのっているダメージカウンターを、好きなだけとりのぞく。とりのぞいた数ぶんのカードを自分の山札から"
                    "引いて、手札に加える。")
        return _check_form(attack, "相手のポケモンを回復して引くワザ", damage="none") + _check_exact_text(attack, "相手のポケモンを回復して引くワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        label = _label(state, use)
        if decision.kind == SELECT_POKEMON:
            options = (p.pokemon_id for p in state.players[1 - use.player].in_play())
            return _decision_form(decision, label, kind=SELECT_POKEMON, player=use.player, choices=(1, 1), options=options)
        found = state.find_pokemon(decision.context_value("target"))
        if found is None or found[0] != 1 - use.player:
            return [f"「{label}」のとりのぞく数の決定の対象 {decision.context_value('target')!r} が、相手の場のポケモンではない"]
        counters = found[1].damage // state.rules.damage_per_counter
        problems = _decision_form(decision, label, kind=REMOVE_COUNTERS, player=use.player, choices=(1, 1), options=range(counters + 1))
        if tuple(decision.context_value("unresolved_choices", ())) != (0,):
            problems.append(f"「{label}」のとりのぞく数の決定で、0 個が選ぶと止める選択（HC5）になっていない")
        return problems


@dataclass(frozen=True)
class CoinFlipDamageThenSelfConfuse(AttackEffect):
    """コインを ``coins`` 枚投げて「おもて」の数 × ``damage_per_heads`` のダメージ。その後、自分はこんらん状態になる（v0.42。ラフレシアの「はなびらのまい」）。
    v0.2d の ``CoinFlipDamage``（みだれづき）と同じダメージの要素（``HeadsTimes``）に、コインのない自分への特殊状態（``Status(CONFUSION, target=SELF)``。v0.41 の
    ``DamageThenConfuseBoth`` の自分への要素と同じ）を加えた形。「おもて」が 0 枚（ダメージ 0）でも、自分はこんらん状態になる（「その後」は順番。「ダメージを
    与えた後」の条件ではない）。ワザを使ったポケモンが相手の「はんげき」などで HP 以上なら、こんらんにしない（p.309）。コインはダメージの量だけを決めるので、
    「ダメージを受けない」相手には v0.4b の ``UNRESOLVED_PREVENTED_COIN_DAMAGE``。"""

    coins: int
    damage_per_heads: int
    implementation_id = "coin_flip_damage_then_self_confuse"

    def __post_init__(self) -> None:
        _positive_count(self.coins, "コインの枚数")
        _positive_tens(self.damage_per_heads, "「おもて」1 枚あたりのダメージ")

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "コインの数でダメージを与えて自分がこんらんになるワザ", damage="modified", modifier="×")
        if attack.damage != self.damage_per_heads:
            problems.append(f"ダメージの目安の数字 {attack.damage!r} と、登録した「おもて」1 枚あたりのダメージ {self.damage_per_heads} が違う")
        expected = f"コインを{self.coins}枚投げて「おもて」の数×{self.damage_per_heads}のダメージ。その後、自分は「こんらん」状態になる。"
        return problems + _check_exact_text(attack, "コインの数でダメージを与えて自分がこんらんになるワザ", (expected,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        return DamageProfile(opponent=tuple(heads * self.damage_per_heads for heads in range(self.coins + 1)))


@dataclass(frozen=True)
class ReturnEnergyThenDamage(AttackEffect):
    """自分についている ``energy_type`` のエネルギーカードを 1 枚選び、はがして手札にもどす。相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ（v0.42。
    ナツメのケーシィの「エネループ」）。要素 ``ReturnOwnEnergyToHand``（手札にもどす。決定 ``return_energy``。時点は v0.31 の「はがしてすてる」と同じく決められない
    （HC1 と同じ問い。こんらん状態で使うときだけ止める））→ ``Damage``。"""

    energy_type: EnergyType
    implementation_id = "return_energy_then_damage"

    def check(self, attack: Attack) -> list[str]:
        expected = f"自分についている「{self.energy_type.ja}」エネルギーカードを1枚選び、はがして手札にもどす。"
        return _check_form(attack, "エネルギーを手札にもどしてダメージを与えるワザ", damage="fixed", cost_types=(self.energy_type,)) + _check_exact_text(
            attack, "エネルギーを手札にもどしてダメージを与えるワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        _, attacker = state.find_pokemon(use.pokemon_id)
        return _decision_form(decision, _label(state, use), kind=RETURN_ENERGY, player=use.player, choices=(1, 1),
                              options=attached_basic_energy(state, attacker, self.energy_type))


@dataclass(frozen=True)
class PlaceCountersToRemainingHpOnHeads(AttackEffect):
    """コインを投げて「おもて」なら、残り HP が ``remaining`` になるように、相手にダメージカウンターをのせる（v0.42。ナツメのユンゲラーの「ライフダウン」。ダメージの
    目安の数字はない）。要素 ``CountersToRemainingHp``（ダメージカウンターをのせる効果。ダメージではない。GR-2000-P320-COUNTER-MOVE）。"""

    remaining: int = 10
    implementation_id = "place_counters_to_remaining_hp_on_heads"
    opponent_effect_elements = (COUNTERS_ELEMENT,)

    def __post_init__(self) -> None:
        _positive_tens(self.remaining, "残り HP")

    def check(self, attack: Attack) -> list[str]:
        expected = f"コインを投げて「おもて」なら、残りHPが「{self.remaining}」になるように、相手にダメージカウンターをのせる。"
        return _check_form(attack, "残り HP を決めてダメージカウンターをのせるワザ", damage="none") + _check_exact_text(
            attack, "残り HP を決めてダメージカウンターをのせるワザ", (expected,))


@dataclass(frozen=True)
class DamageThenOptionalSelfSwitch(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。のぞむなら、ダメージを与えた後、自分の控えポケモンを 1 匹選び、このカードと入れ替えてもよい（v0.42。
    わるいフーディンの「テレポートブラスト」）。v0.34 のテレポート・v0.38 のけりにげと同じ要素 ``SelfSwitch`` で、選ばなくてもよい（``optional``。決定
    ``select_pokemon`` の 0〜1 匹）。「ダメージを与えた後」の効果なので、ダメージを与えなかったら Z23（kyuura の UQ- の記録がこのワザを挙げている。v0.17b の
    ``after_damage``）。"""

    implementation_id = "damage_then_optional_self_switch"

    def check(self, attack: Attack) -> list[str]:
        expected = "のぞむなら、ダメージを与えた後、自分の控えポケモンを1匹選び、このカードと入れ替えてもよい。"
        return _check_form(attack, "ダメージのあと自分の控えと入れ替えてよいワザ", damage="fixed") + _check_exact_text(
            attack, "ダメージのあと自分の控えと入れ替えてよいワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        bench = state.players[use.player].bench
        return _decision_form(decision, _label(state, use), kind=SELECT_POKEMON, player=use.player, choices=(0, 1), options=(p.pokemon_id for p in bench))


@dataclass(frozen=True)
class EvolveFromDeckOnHeads(AttackEffect):
    """コインを投げて「おもて」なら、自分の山札から、自分または自分の控えポケモンを進化させる「進化カード」を 1 枚選び出し、そのポケモンの上にのせる。その後、その
    山札をよく切る（v0.42。エリカのピッピの「つきのちから」。ダメージの目安の数字はない）。要素 ``EvolveFromDeck``（通常の進化と同じ条件・手順。p.310 の制限を
    免除しない）。"""

    implementation_id = "evolve_from_deck_on_heads"

    def check(self, attack: Attack) -> list[str]:
        expected = ("コインを投げて「おもて」なら、自分の山札から、自分または自分の控えポケモンを進化させる「進化カード」を1枚選び出し、そのポケモンの上にのせる。"
                    "その後、その山札をよく切る。")
        return _check_form(attack, "山札の進化カードで進化させるワザ", damage="none") + _check_exact_text(attack, "山札の進化カードで進化させるワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        label = _label(state, use)
        candidates = deck_evolution_candidates(state, use.player)
        if decision.kind == SEARCH_DECK:
            problems = _decision_form(decision, label, kind=SEARCH_DECK, player=use.player, choices=(1, 1), options=tuple(candidates))
            # v0.43: 場に出たときに使える特殊能力を持つ進化カードは、選べるが選ぶと止める（PW4。HP で止めるカードを除く）
            blocked = set(decision.context_value("unresolved_choices", ()))
            entry = tuple(card for card in candidates if card not in blocked and applicable_entry_power(state, card, from_hand=False) is not None)
            if tuple(decision.context_value("entry_power_choices", ())) != entry:
                problems.append(f"「{label}」の進化カードの決定の、選ぶと止めるカード（場に出たときの特殊能力）{decision.context_value('entry_power_choices', ())} が "
                                f"{entry} ではない")
            return problems
        card = decision.context_value("card")
        if card not in candidates or len(candidates[card]) < 2:
            return [f"「{label}」の重ねるポケモンの決定のカード {card!r} が、2 匹以上に重ねられる山札の進化カードではない"]
        return _decision_form(decision, label, kind=SELECT_POKEMON, player=use.player, choices=(1, 1), options=candidates[card])


@dataclass(frozen=True)
class ReturnOwnPokemonToHandOnHeads(AttackEffect):
    """コインを投げて「おもて」なら、自分の場にいるポケモンを好きなだけ選び、そのポケモンと、それらについているすべてのカードを手札にもどす（v0.42。エリカの
    ピクシーの「ようせいのきせき」。ダメージの目安の数字はない）。要素 ``ReturnOwnPokemonToHand``（手札にもどす。きぜつではない。0 匹は HC5 と同じ問い）。"""

    implementation_id = "return_own_pokemon_to_hand_on_heads"

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「おもて」なら、自分の場にいるポケモンを好きなだけ選び、そのポケモンと、それらについているすべてのカードを手札にもどす。"
        return _check_form(attack, "自分の場のポケモンを手札にもどすワザ", damage="none") + _check_exact_text(attack, "自分の場のポケモンを手札にもどすワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        options = tuple(p.pokemon_id for p in state.players[use.player].in_play())
        return _decision_form(decision, _label(state, use), kind=SELECT_POKEMON, player=use.player, choices=(0, len(options)), options=options)


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
    # v0.43: 場に出したトレーナーの効果の途中で使う、場に出たときの特殊能力（ポケモン育て屋さんで場に出たわるいカイリューの［てしたをよぶ］）の、もどる先
    # （("trainer", プレイヤー, カード, カード id)。特殊能力の処理が終わったら、そのトレーナーの処理（トラッシュ）にもどる）。ほかは None
    return_to: tuple | None = None
    # v0.49: 特殊能力を印刷したカードの uid。None ならポケモンのいちばん上のカード（v0.48 までと同じ）。「ばける」でのせたカードの特殊能力なら、のせたカード
    card: int | None = None


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
    パワー（p.311・p.323）は、宣言しないので、``UsePokemonPower`` の形では扱わない（下の ``declared``）。

    v0.8: ``declared`` は、使用を宣言して使う特殊能力なら True（v0.5〜v0.7 の実装はどれも True）。常にはたらいている特殊能力
    （``SuppressOtherPowers``。ベトベトンの「かがくへんかガス」）は False で、エンジンは ``UsePokemonPower`` を ``POWER_NOT_DECLARABLE``
    で拒否する（``check_usable``・``resolve`` を呼ばない）。常にはたらいている効果は状態から求める（``continuous.py``）。

    v0.9: ワザを受けるときに自動的にはたらく特殊能力（``AttackImmunityOnHeads``。ゴーストの「とうめい」）も ``declared`` は False。
    ``declared`` は「宣言するか」だけを表し、常にはたらく・自動的にはたらくの区別はしない（エンジンは実装の型で探す。かがくへんかガスは
    ``continuous.py``、「とうめい」は ``evasion_power``・``attack_reaches``。docs/automatic-powers-v0.9.md）。
    """

    implementation_id = "abstract"
    declared: ClassVar[bool] = True
    once_per_turn: ClassVar[bool] = False  # v0.31: 「自分の番ごとに1回使える」（使った回数は ``GameState.power_uses_this_turn``）
    # v0.49: ワザのないカードに、ほかのカードのワザを持たせる特殊能力（メタモンの［へんしん］）。ワザのないポケモンを対応にするのは、これが登録されているときだけ
    supplies_attacks: ClassVar[bool] = False
    # v0.42: 説明が、処理の結果としてポケモンを「きぜつ」させうるか（ゲンガーの［のろい］だけ。説明に「きぜつ」しない範囲の条件がない）。偽の特殊能力の
    # 処理のあとに HP 以上のポケモンがいれば、きぜつの処理をせず不変条件で止める（``resolution.after_power``）
    may_knock_out: ClassVar[bool] = False

    def check(self, power: Power) -> list[str]:
        return []

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        return None

    def resolve(self, state: GameState, use: PowerUse) -> None:
        raise NotImplementedError

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        """処理の途中で出した決定（v0.42。``decisions.push_power_decision``。再開先 ``"power"``）の続き。宣言・回数の記録・コインは繰り返さない。
        もう一度決定を出してもよい。決定を出す特殊能力は上書きする。"""
        raise NotImplementedError(f"特殊能力の実装 {type(self).__name__} は決定を出さない")

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        """自分が出す決定の形（v0.42。トレーナーの ``TrainerEffect.decision_problems`` と同じ考え方）。既定は「決定するのは特殊能力を使ったプレイヤー」
        だけを確かめる。決定を出す特殊能力は、種類・選ぶ数・選べるものを上書きして確かめる。"""
        if decision.player != use.player:
            return [f"特殊能力 {use.key} の決定をするのが、使ったプレイヤー {use.player} ではない（{decision.player}）"]
        return []


def power_use_record(state: GameState, use: PowerUse) -> tuple[int, ...]:
    """「自分の番ごとに1回」の特殊能力を使った記録（``GameState.power_uses_this_turn`` の 1 つ）（v0.49）。いちばん上のカードの特殊能力は (場のポケモンの番号,
    特殊能力の位置)（v0.48 までと同じ）、ほかのカード（「ばける」でのせたカード）の特殊能力は (場のポケモンの番号, 特殊能力の位置, そのカードの uid)。同じ位置の
    特殊能力でも、印刷したカードが違えば別の特殊能力として数える。"""
    found = state.find_pokemon(use.pokemon_id)
    if use.card is None or found is None or use.card == found[1].card:
        return (use.pokemon_id, use.key.power_index)
    return (use.pokemon_id, use.key.power_index, use.card)


POWER_REUSE_AFTER_DEVOLUTION_CODE = "UNRESOLVED_POWER_REUSE_AFTER_DEVOLUTION"
POWER_REUSE_AFTER_DEVOLUTION_REASON = (
    "今の番に退化してまたいちばん上になったカードの「自分の番ごとに1回」の特殊能力を、そのカードで退化の前（進化させる前）にこの番に使っていたとき、もう一度使えるかは、"
    "退化したポケモンが「退化前とは別のポケモン」（p.324）であることと、同じカードで使った記録の関係が記録で決まらないので扱わない（DV3）"
)


def require_power_not_used(state: GameState, use: PowerUse) -> None:
    """「自分の番ごとに1回」（v0.31。v0.42 で共通の関数にした）: この番に、この場のポケモンの、この特殊能力をもう使っていたら ``POWER_ALREADY_USED``。
    使った記録は ``GameState.power_uses_this_turn``（宣言のときにエンジンが記録する。ログから数えない）。同じ名前のカードが 2 匹いれば、それぞれ 1 回。
    v0.49: 特殊能力は印刷したカードで区別する（``power_use_record``）。

    v0.50: 進化・退化でいちばん上のカードが変わると、前のいちばん上のカードで使った記録は、そのカードの記録（(番号, 位置, カード)）になる（``evolution.retag_power_uses``）。
    退化してまたいちばん上になったカードの記録は、ここでは数えない（DV3。``power_reuse_after_devolution``。エンジンがパワーごとの確かめのあとに止める）。"""
    if power_use_record(state, use) in state.power_uses_this_turn:
        raise IllegalActionError("POWER_ALREADY_USED", f"ポケモン {use.pokemon_id} の特殊能力は、この番にもう使った（自分の番ごとに1回）")


def power_reuse_after_devolution(state: GameState, use: PowerUse) -> bool:
    """v0.50: いちばん上のカードの「自分の番ごとに1回」の特殊能力を使うとき、そのカードで使った記録（(番号, 位置, そのカード)。``evolution.retag_power_uses``）がこの番に
    あるか。いちばん上のカードの記録がそのカードの記録になるのは、進化・退化でいちばん上でなくなったときだけなので、あれば、そのカードが進化させる前に使い、今の番に退化して
    またいちばん上になった（DV3。決まらない）。"""
    found = state.find_pokemon(use.pokemon_id)
    if found is None or power_use_record(state, use) != (use.pokemon_id, use.key.power_index):
        return False
    return (use.pokemon_id, use.key.power_index, found[1].card) in state.power_uses_this_turn


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
        if (source.pokemon_id, use.energy) in state.energy_burn:
            # v0.31: リザードンの「エナジーバーン」で、この番は「炎」エネルギーになっているカード。「「草」エネルギーを…つけかえる」のエネルギーが、カードの
            # 種類（草エネルギーカード）か、今のエネルギーのタイプ（炎）かは決められない（HC10）
            raise UnsupportedError(
                "UNRESOLVED_ENERGY_BURN_TRANSFER",
                f"エネルギー {use.energy} は、この番は「エナジーバーン」で「炎」エネルギーになっている。この特殊能力で「草」エネルギーとしてつけかえられるかは"
                "決められないので扱わない（HC10）",
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
        # v0.48: 「水」ポケモンかは今有効な色（``type_readings``。モルフォンの［へんしょく］で変えた色を含む）。読み方（VS1）で答えが変わるなら、エネルギーを動かす前に止める
        readings = {color is self.pokemon_type for color in type_readings(state, target)}
        if len(readings) > 1:
            raise shift_duration_error(target, f"つける先 {use.target} が「{self.pokemon_type.ja}」ポケモンか")
        if readings == {False}:
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
        after_energy_attached(state, use.player, target, use.energy)  # v0.31: つけたときにはたらく特殊能力（「水」エネルギーなので今ははたらかない）


def would_be_knocked_out(state: GameState, pokemon: PokemonInPlay, damage: int) -> bool:
    """場のポケモン ``pokemon`` のダメージが ``damage`` になったら「きぜつ」するか（v0.7）。

    きぜつの判定と同じ式（ダメージが HP と同じか、それより大きい。p.319「ポケモンのダメージが、ポケモンのHPと同じか、それより
    大きくなったら、そこでそのポケモンは「きぜつ」します」・p.320「ダメージカウンターの移動によって、ダメージの数がポケモンのHPと
    同じか、それより大きくなったら、そのポケモンは「きぜつ」します」・p.323）。HP はいちばん上のカードの値（p.310）。状態は変えない。
    """
    return damage >= max_hp(state, pokemon)  # v0.48: 今有効な最大HP


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
        _, source = state.find_pokemon(use.source)
        _, target = state.find_pokemon(use.target)
        _move_one_counter(state, use, source, target)  # v0.42 で共通にした（動き・ログは v0.41 と同じ）


@dataclass(frozen=True)
class SuppressOtherPowers(PowerEffect):
    """常にはたらいていて、ほかの特殊能力を使えなくし、その力も消す特殊能力（v0.8。ベトベトンの「かがくへんかガス」。p.48 の最新の説明
    「このカードが場にいるかぎり、「かがくへんかガス」以外のすべての「特殊能力」は使えず、その力も消える。このカードが「ねむり・マヒ・
    こんらん」状態のとき、この力は消える。」・p.323 の例。docs/chemical-gas-v0.8.md・docs/continuous-effects-v0.8.md）。

    - 宣言しない（``declared`` が False）: 「常にはたらいているため、使用を宣言しない特殊能力もあります」（p.311・p.323）。
      ``UsePokemonPower`` で使おうとしたら、エンジンが ``POWER_NOT_DECLARABLE`` で拒否する（``check_usable``・``resolve`` は呼ばない）。
    - はたらいているか（``is_working``）は、今の状態だけで決める: このカード（いちばん上のカード。p.310）が場（バトル場・ベンチ。p.308）に
      いて、ねむり・マヒ・こんらんでないこと。どくは挙げられていないので関係しない（SUPPORTED）。ベンチのポケモンは特殊状態にならない
      （p.322）ので、ベンチのこのカードはいつもはたらいている。状態を覚えておかないので、回復・進化・きぜつ・ベンチに戻ること・保存と
      復元のあとも、その時点の状態から同じ答えになる（``continuous.py``）。
    - 消すのは、名前が ``exempt_name``（「かがくへんかガス」）でない、すべての特殊能力（両方のプレイヤーの場のポケモン。p.48 の解説
      「自分のほうも特殊能力を使えなくなる」）。ワザ・トレーナー・手札からつける通常の操作は特殊能力ではないので消さない。
    - 「かがくへんかガス」どうしは消し合わない（名前で除かれる）。そのため、はたらいているかの判定がほかの特殊能力の判定に依存せず、
      循環しない（``check`` が、この実装を「かがくへんかガス」という名前のパワーだけに登録できることを確かめる）。
    """

    exempt_name: str
    implementation_id = "suppress_other_powers"
    declared = False

    def check(self, power: Power) -> list[str]:
        problems = []
        if power.kind != "pokemon_power":
            problems.append(f"種類 {power.kind!r} のパワーを、ポケモンパワー（特殊能力）として登録している")
        if power.text_ja is None:
            problems.append("説明文のないポケモンパワーを、ほかの特殊能力を消すパワーとして登録している")
        if power.name_ja != self.exempt_name:
            # 自分自身を消さないこと（「「かがくへんかガス」以外の」）を名前の除外で表しているので、除外する名前のパワーにだけ登録できる
            problems.append(f"除外する名前「{self.exempt_name}」と違う名前のパワー「{power.name_ja}」に登録している（自分自身を消してしまう）")
        return problems

    def is_working(self, pokemon: PokemonInPlay) -> bool:
        """場のポケモン ``pokemon``（このパワーを持つカードがいちばん上）のこの力がはたらいているか。ねむり・マヒ・こんらんなら消えている。"""
        conditions = pokemon.conditions
        return not (conditions.asleep or conditions.paralyzed or conditions.confused)

    def suppresses(self, power: Power) -> bool:
        """特殊能力 ``power`` を消すか（「かがくへんかガス」以外のすべて）。"""
        return power.name_ja != self.exempt_name


@dataclass(frozen=True)
class AttackImmunityOnHeads(PowerEffect):
    """ワザによってダメージや効果を受けるときに自動的にはたらき、コインが「おもて」なら、そのダメージと効果を受けない特殊能力（v0.9。
    化石の秘密のゴーストの「とうめい」。p.160 の最新の説明「このカードがワザによってダメージや効果を受けるとき、コインを投げて
    「おもて」なら、このカードはそのダメージと効果を受けない。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は消える。」・
    p.159 の特殊能力解説・p.323 の例。docs/transparency-v0.9.md・docs/automatic-powers-v0.9.md）。

    - 宣言しない（``declared`` が False）: 「決められたときに自動的にはたらくため、使用を宣言しない特殊能力もあります」（p.323）。
      ``UsePokemonPower`` で使おうとしたら、エンジンが ``POWER_NOT_DECLARABLE`` で拒否する（``check_usable``・``resolve`` は呼ばない）。
    - はたらく時点は、ワザの要素がこのカードにダメージ（最終ダメージが 0 より大きい）や効果を与える直前（``attack_reaches``。
      ``deal_attack_damage`` と、効果を与えるワザの実装が呼ぶ）。1 つのワザにつき 1 回コインを投げ、その結果をそのワザの残りに使う。
    - はたらいているか（``is_working``）は、このカード（いちばん上のカード）がねむり・マヒ・こんらんでないこと。どくは関係しない。
      かがくへんかガス（v0.8）に消されているかは ``evasion_power`` が ``continuous.suppressors_of`` で確かめる。場所は見ない（ベンチでも）。
    - 宣言して使う特殊能力（エナジートランス・あまごい・ダメージスワップ）・常にはたらく特殊能力（かがくへんかガス）とは別の実装の型。
      エンジンは型（``isinstance``）で探す（``declared`` だけでは、常にはたらく・自動的にはたらくを区別しない）。
    """

    implementation_id = "attack_immunity_on_heads"
    declared = False

    def check(self, power: Power) -> list[str]:
        problems = []
        if power.kind != "pokemon_power":
            problems.append(f"種類 {power.kind!r} のパワーを、ポケモンパワー（特殊能力）として登録している")
        if power.text_ja is None:
            problems.append("説明文のないポケモンパワーを、ワザを受けないパワーとして登録している")
        return problems

    def is_working(self, pokemon: PokemonInPlay) -> bool:
        """場のポケモン ``pokemon``（このパワーを持つカードがいちばん上）のこの力がはたらいているか（かがくへんかガスは別に見る）。"""
        conditions = pokemon.conditions
        return not (conditions.asleep or conditions.paralyzed or conditions.confused)


@dataclass(frozen=True)
class CounterattackDamage(PowerEffect):
    """相手のワザによってダメージを受けたときに自動的にはたらき、ダメージを与えたポケモンに、弱点・抵抗力に関係なく ``amount`` ダメージを
    与える特殊能力（v0.10。カイリキーの「はんげき」。p.192 の最新の説明「このカードが相手のワザによってダメージを受けたとき、（それに
    よってこのカードが「きぜつ」しても、）ダメージを与えたポケモンに、「弱点・抵抗力」に関係なく、10ダメージ。ダメージを受けるとき、
    すでにこのカードが「ねむり・マヒ・こんらん」状態だったなら、この力は、はたらかない。」。docs/counterattack-v0.10.md・
    docs/post-damage-powers-v0.10.md）。

    - 宣言しない（``declared`` が False）: 「決められたときに自動的にはたらくため、使用を宣言しない特殊能力もあります」（p.311・p.323）。
      最新の説明に「使える」がなく、p.192 の解説は「相手の番に効果が発生する特殊能力です」、印刷の文面は「かならず10ダメージを相手に
      あたえる」。``UsePokemonPower`` で使おうとしたら、エンジンが ``POWER_NOT_DECLARABLE`` で拒否する（``check_usable``・``resolve`` は
      呼ばない）。
    - はたらく時点は、このカードが相手のワザのダメージ（最終ダメージが 0 より大きい）を受けたとき（解決の基盤の ``kernel.deal_damage`` が
      枠の送る効果の列に加える）。与えるのは、そのワザのダメージの処理がすべて終わったところ（ダメージの要素のあとの窓
      ``kernel.fire_pending``。ダメージ以外の効果の前。p.89 の解説）。
    - はたらいているか（``is_working``）は、ダメージを受けるときに、このカード（いちばん上のカード）がねむり・マヒ・こんらんでないこと
      （「すでに…状態だったなら」）。どくは関係しない。かがくへんかガス（v0.8）に消されているかは ``counterattack_power`` が
      ``continuous.suppressors_of`` で確かめる。場所は見ない（ベンチでも。p.311・p.323）。
    - v0.9 の「とうめい」（``AttackImmunityOnHeads``。ワザによってダメージや効果を受ける「とき」、受ける前にはたらく）とは別の実装の型。
      エンジンは型（``isinstance``）で探す。
    """

    amount: int
    implementation_id = "counterattack_damage"
    declared = False
    # v0.17b: 最新の説明が「「弱点・抵抗力」に関係なく」と書いているか（はんげきは書いている。書いていない力の 20 に弱点・抵抗力を計算するかは
    # 原典で決まらない。解決の基盤の ``kernel.power_damage_to_damage_source`` が、それで結果が変わる場合を止める。docs/rocket-snorlax-v0.17b.md の Z9）
    ignores_weakness_resistance: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if type(self.amount) is not int or self.amount <= 0 or self.amount % 10:
            raise ValueError(f"与えるダメージは 10 の倍数の正の数（{self.amount!r}）")

    def check(self, power: Power) -> list[str]:
        problems = []
        if power.kind != "pokemon_power":
            problems.append(f"種類 {power.kind!r} のパワーを、ポケモンパワー（特殊能力）として登録している")
        if power.text_ja is None:
            problems.append("説明文のないポケモンパワーを、ダメージを受けたときにダメージを与えるパワーとして登録している")
        return problems

    def is_working(self, pokemon: PokemonInPlay) -> bool:
        """場のポケモン ``pokemon``（このパワーを持つカードがいちばん上）のこの力がはたらいているか（かがくへんかガスは別に見る）。"""
        exclusive = pokemon.conditions.exclusive
        return self.works_with(None if exclusive is None else exclusive.name)

    def works_with(self, exclusive: str | None) -> bool:
        """ダメージを受けるときのねむり・マヒ・こんらん（``SpecialConditions.exclusive`` の名前。なければ None）で、この力がはたらくか
        （どくは関係しない）。v0.17b で ``is_working`` から分けた（ログの監査がログから組み立てた特殊状態で同じ判定を使う）。はんげきは、
        ねむり・マヒ・こんらんのどれでもないときだけ。解決の基盤は、同じ条件を効果の定義（``catalog.STRIKES_BACK`` の ``disabled_by``）で持つ。"""
        return exclusive is None


@dataclass(frozen=True)
class CounterattackDamageWhileAsleep(CounterattackDamage):
    """「ねむり」状態で相手のワザによるダメージを受けたときに自動的にはたらき、ダメージを与えたポケモンに ``amount`` ダメージを与える特殊能力
    （v0.17b。R団のカビゴンの［わるいねぞう］。p.245 の最新の説明「このカードが「ねむり」状態で、相手のワザによるダメージを受けたとき、（それ
    によってこのカードが「きぜつ」しても、）ダメージを与えたポケモンに、20ダメージ。」。docs/rocket-snorlax-v0.17b.md）。

    - はんげき（``CounterattackDamage``）と同じ窓・同じ処理（解決の基盤の ``kernel.power_damage_to_damage_source``。特殊能力のダメージ。
      p.245 の解説「このダメージは特殊能力によるダメージなので「ディフェンダー」ではふせげません」。Z6・Z7）で、特殊状態の条件だけが違う:
      ダメージを受けるときにねむりのときだけはたらく（Z2）。マヒ・こんらんはねむりと重ならない（p.322）。どくは関係しない（Z3）。
      解決の基盤は、効果の定義（``catalog.RESTLESS_SLEEP`` の ``requires``）で同じ条件を持つ。
    - 宣言しない（Z4。``declared`` は False のまま）。かがくへんかガスで消える（Z14）。
    - 最新の説明に「弱点・抵抗力」に関係なく、がないので、20 に弱点・抵抗力を計算するかは原典で決まらない（Z9。UNRESOLVED）。R団のカビゴンは
      無色で、kyuura の記録（780 枚）に無色の弱点・抵抗力を持つカードはないので、結果は変わらない。結果が変わる場合は解決の基盤が止める。
    - v0.13 の部品（``counterattack_power``・``working_counterattack_power``・v0.13 の止める関数の C18）は ``isinstance`` で探すので、この力も
      「ダメージを受けたときにダメージを与えたポケモンにダメージを与える特殊能力」として同じに扱われる（``works_with`` で条件だけが違う）。
    """

    implementation_id = "counterattack_damage_while_asleep"
    ignores_weakness_resistance: ClassVar[bool] = False

    def works_with(self, exclusive: str | None) -> bool:
        return exclusive == SLEEP


@dataclass(frozen=True)
class PreventKnockOutOnHeads(PowerEffect):
    """相手のワザによるダメージで、このカードが「きぜつ」するとき、使える特殊能力。コインを投げて「おもて」なら「きぜつ」せず、残り HP が
    ``remaining_hp`` になる（v0.11。サカキのカイリキーの「こんじょう」。p.193 の最新の説明「この力は、相手のワザによるダメージで、この
    カードが「きぜつ」するとき、使える。コインを投げて「おもて」なら、このカードは「きぜつ」せず、このカードの残りHPが「10」になる。
    ダメージを受けるとき、すでにこのカードが「ねむり・マヒ・こんらん」状態だったなら、この力は使えない。」。docs/guts-v0.11.md・
    docs/ko-prevention-v0.11.md）。

    - 使用を宣言して使う特殊能力（``declared`` は True）。最新の説明は「使える」（自動的にはたらく特殊能力は「はたらく」。p.192 の
      ［はんげき］・p.188 の［ずらかる］「かならずはたらく」）で、宣言するかはプレイヤーが決める（p.311「かならずしも特殊能力の使用を
      宣言する必要はありません」。G1・G10）。決められたとき（「相手のワザによるダメージで、このカードが「きぜつ」するとき」。p.311
      「決められたときにしか使用を宣言できないものもあります」）にだけ使える。そのときは、ワザの要素をすべて処理したあとのきぜつの判定
      で、エンジンが持ち主に決定（``decisions.KO_PREVENTION``。選ばない = 使わない）を出す（``resolution.flow._finish_attack``）。それ以外の
      ときに ``UsePokemonPower`` で使おうとしたら ``check_usable`` が ``POWER_NOT_USABLE_NOW`` で拒否する。
    - 使えないのは、ダメージを受けるときに、このカード（いちばん上のカード）がねむり・マヒ・こんらんだったとき（``is_able``。どくは
      挙げられていない。G25〜G29）と、かがくへんかガス（v0.8）に消されているとき（G31。``ko_prevention_suppressors``）。場所は見ない
      （G8。ベンチのポケモンがワザのダメージを受けるワザは今の対応カードにない）。
    - 使ったら（``prevent``）、持ち主がコインを 1 枚投げ（``coin_flip`` の ``source: "power"``、``effect`` は ``PowerKey``。G15・G17）、
      「おもて」ならダメージを HP − ``remaining_hp`` にする（残り HP が 10。ダメージを 0 にするのではない。受けたダメージはそのまま
      受けたことになっている。G18・G20〜G23）。「うら」なら何もしない（そのあとのきぜつの判定で、ふつうにきぜつする。G19・G34）。
    """

    remaining_hp: int
    implementation_id = "prevent_knock_out_on_heads"

    def __post_init__(self) -> None:
        if type(self.remaining_hp) is not int or self.remaining_hp <= 0 or self.remaining_hp % 10:
            raise ValueError(f"残りの HP は 10 の倍数の正の数（{self.remaining_hp!r}）")

    def check(self, power: Power) -> list[str]:
        problems = []
        if power.kind != "pokemon_power":
            problems.append(f"種類 {power.kind!r} のパワーを、ポケモンパワー（特殊能力）として登録している")
        if power.text_ja is None:
            problems.append("説明文のないポケモンパワーを、きぜつをまぬがれるパワーとして登録している")
        return problems

    def is_able(self, pokemon: PokemonInPlay) -> bool:
        """場のポケモン ``pokemon``（このパワーを持つカードがいちばん上）が、今ダメージを受けるとして、特殊状態の条件（「すでに…
        「ねむり・マヒ・こんらん」状態だったなら、この力は使えない」）に当たらないか。かがくへんかガスは別に見る。"""
        conditions = pokemon.conditions
        return not (conditions.asleep or conditions.paralyzed or conditions.confused)

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        raise IllegalActionError(
            "POWER_NOT_USABLE_NOW",
            f"特殊能力 {use.key} は、相手のワザによるダメージで、このカードが「きぜつ」するときにだけ使える（p.193・p.311。そのときは"
            "エンジンが決定 ko_prevention を出す）",
        )

    def resolve(self, state: GameState, use: PowerUse) -> None:
        raise RuntimeError(f"特殊能力 {use.key} は UsePokemonPower では使わない（check_usable が拒否する。エンジンの不具合）")

    def prevent(self, state: GameState, owner: int, pokemon: PokemonInPlay, key: PowerKey) -> bool:
        """使用を宣言したあとの処理（p.311 の手順 3）: 持ち主 ``owner`` がコインを 1 枚投げ、「おもて」なら ``pokemon`` のダメージを
        HP − ``remaining_hp`` にする。ログ ``ko_prevented``（「おもて」）か ``ko_prevention_failed``（「うら」）。「きぜつ」しなかったら
        True。宣言のログ（``ko_prevention_declared``）と、そのあとのきぜつの処理はエンジン（``engine._resume_knock_out``）。"""
        hp = max_hp(state, pokemon)  # v0.48: 今有効な最大HP（「こんじょう」で残す HP も、その値から数える）
        if pokemon.damage < hp:
            raise RuntimeError(f"HP 以上のダメージを受けていないポケモン {pokemon.pokemon_id} に「{key}」を使おうとした（エンジンの不具合）")
        flips = flip_coins(state, owner, 1, source="power", effect=str(key), card=pokemon.card, pokemon_id=pokemon.pokemon_id)
        base = {"player": owner, "pokemon": pokemon.card, "pokemon_id": pokemon.pokemon_id, "power": str(key)}
        if flips.results[0] is not CoinSide.HEADS:
            state.add_event("ko_prevention_failed", **base, result=flips.results[0].value, total_damage=pokemon.damage)
            return False
        before = pokemon.damage
        pokemon.damage = hp - self.remaining_hp
        state.add_event(
            "ko_prevented", **base, result=flips.results[0].value, damage_before=before, total_damage=pokemon.damage,
            remaining_hp=self.remaining_hp,
        )
        return True


@dataclass(frozen=True)
class ReturnToHandOnKnockOut(PowerEffect):
    """このカードが「きぜつ」したとき、使える特殊能力。このカードをトラッシュからとり出し、相手プレイヤーに見せてから、手札に加える
    （v0.12。R団のファイヤーの「ふしちょう」。p.82 の最新の説明「この力は、このカードが「きぜつ」したとき、使える。このカードをトラッシュ
    からとり出し、相手プレイヤーに見せてから、手札に加える。このカードが「ねむり・マヒ・こんらん」状態のまま「きぜつ」するとき、この力は
    使えない。」。docs/phoenix-v0.12.md・docs/post-knockout-powers-v0.12.md）。

    - 使用を宣言して使う特殊能力（``declared`` は True）。最新の説明・印刷の文面とも「使える」で、宣言するかはプレイヤーが決める（p.311
      「かならずしも特殊能力の使用を宣言する必要はありません」。P1・P2）。決められたとき（このカードが「きぜつ」したとき。p.311「決められた
      ときにしか使用を宣言できないものもあります」）にだけ使える。そのときは、きぜつの処理（トラッシュ・サイド・勝ち負けの判定）のあと、
      対戦が続くなら、エンジンが持ち主に決定（``decisions.POST_KNOCKOUT_POWER``。選ばない = 使わない）を出す（``engine._after_knockouts``）。
      場にいるときに ``UsePokemonPower`` で使おうとしたら ``check_usable`` が ``POWER_NOT_USABLE_NOW`` で拒否する。
    - きぜつの原因は問わない（説明は「「きぜつ」したとき」だけ。v0.11 の「こんじょう」（相手のワザによるダメージで「きぜつ」する「とき」）
      とは条件も時点も違う。P5〜P10）。
    - 使えないのは、このカード（いちばん上のカード）が「きぜつ」するときにねむり・マヒ・こんらんだったとき（``is_able``。どくは挙げられて
      いない。P13〜P17）と、かがくへんかガス（v0.8）に消されているとき（P18。「すべての「特殊能力」は使えず」。きぜつの処理の前の場で
      ``continuous.suppressors_of`` を聞く）。どちらも、きぜつの処理（トラッシュ）の前に求めて決定の候補にする（場をはなれたあとの状態で
      決めない。B2）。
    - 使ったら（``recover``）、このカード（きぜつしたポケモンのいちばん上のカード。同じ uid）だけをトラッシュから手札に加える（P22〜P24）。
      ついていたエネルギー・トレーナーはトラッシュに残る。乱数は使わない。
    """

    implementation_id = "return_to_hand_on_knock_out"

    def check(self, power: Power) -> list[str]:
        problems = []
        if power.kind != "pokemon_power":
            problems.append(f"種類 {power.kind!r} のパワーを、ポケモンパワー（特殊能力）として登録している")
        if power.text_ja is None:
            problems.append("説明文のないポケモンパワーを、きぜつしたときにトラッシュから手札に加えるパワーとして登録している")
        return problems

    def is_able(self, pokemon: PokemonInPlay) -> bool:
        """場のポケモン ``pokemon``（このパワーを持つカードがいちばん上）が今「きぜつ」するとして、特殊状態の条件（「このカードが「ねむり・
        マヒ・こんらん」状態のまま「きぜつ」するとき、この力は使えない」）に当たらないか。かがくへんかガスは別に見る。"""
        conditions = pokemon.conditions
        return not (conditions.asleep or conditions.paralyzed or conditions.confused)

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        raise IllegalActionError(
            "POWER_NOT_USABLE_NOW",
            f"特殊能力 {use.key} は、このカードが「きぜつ」したときにだけ使える（p.82・p.311。そのときはエンジンが決定 post_knockout_power を出す）",
        )

    def resolve(self, state: GameState, use: PowerUse) -> None:
        raise RuntimeError(f"特殊能力 {use.key} は UsePokemonPower では使わない（check_usable が拒否する。エンジンの不具合）")

    def recover(self, state: GameState, owner: int, card: int, key: PowerKey) -> None:
        """使用を宣言したあとの処理（p.311 の手順 3）: このカード ``card``（持ち主 ``owner`` のトラッシュにある）をトラッシュからとり出し、
        相手プレイヤーに見せてから、手札に加える。ログ ``return_to_hand``（``player``・``card``・``card_id``・``power``・``revealed``）。
        宣言のログ（``post_knockout_power_declared``）はエンジン（``engine._resume_post_knockout``）。"""
        return_discard_to_hand(state, owner, (card,))
        state.add_event(
            "return_to_hand", player=owner, card=card, card_id=state.cards[card].card_id, power=str(key), revealed=True
        )


def post_knockout_power(state: GameState, pokemon: PokemonInPlay) -> tuple[PowerKey, ReturnToHandOnKnockOut] | None:
    """場のポケモン ``pokemon`` の（いちばん上のカードの。p.310）特殊能力のうち、このカードが「きぜつ」したときに使えるもの
    （``ReturnToHandOnKnockOut``。R団のファイヤーの「ふしちょう」。v0.12）。特殊状態・かがくへんかガスは見ない（持っているかだけ）。
    なければ None。状態を変えず、乱数を使わない。"""
    for slot in powers_of(state, pokemon):  # v0.49: 今持つ特殊能力
        if isinstance(slot.effect, ReturnToHandOnKnockOut):
            return slot.key, slot.effect
    return None


# ---------------------------------------------------------------- v0.31 の特殊能力（docs/held-cards-v0.31.md）


def _require_no_choices(use: PowerUse) -> None:
    if use.energy is not None or use.source is not None or use.target is not None:
        raise IllegalActionError("POWER_CHOICE_NOT_USED", "このポケモンパワーは、エネルギー・移動元・移動先を選ばない")


@dataclass(frozen=True)
class ConvertAttachedEnergy(PowerEffect):
    """このカードについているすべてのエネルギーは ``energy_type`` エネルギーになり、自分の番の終わりにもとにもどる（v0.31。リザードンの「エナジーバーン」。
    処理に使う文面は kyuura の公式エラッタ TXT-CHARIZARD の最新の説明「この力は、自分の番の中で何度でも使える。このカードについているすべてのエネルギーは
    「炎」エネルギーになり、自分の番の終わりにもとにもどる。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない。」。印刷の文面（「こんらん」
    状態のときだけ使えない）は照合だけに使う）。

    - 何度でも使える（回数を数えない）。ねむり・マヒ・こんらんのとき使えない（どくは使える）。選ぶものはない。
    - 使った時点でついているエネルギーカードを、このポケモンについている間だけ ``energy_type`` として扱う（``GameState.energy_burn``。あとからつけた
      カードは、もう一度使うまでもとのまま）。番の終わりにもどす（``procedures.expire_at_turn_end``）。ワザに必要なエネルギーの確認（``state.energy_types``）
      が使う。
    - 「炎」になったエネルギーカードを、ほかの特殊能力（エナジートランスの「草」エネルギー）でつけかえられるかは決められない（HC10。エナジートランスが止める）。
    """

    energy_type: EnergyType
    implementation_id = "convert_attached_energy"

    def check(self, power: Power) -> list[str]:
        problems = []
        if power.kind != "pokemon_power":
            problems.append(f"種類 {power.kind!r} のパワーを、使用を宣言するポケモンパワーとして登録している")
        if power.text_ja is None:
            problems.append("説明文のないポケモンパワーを、エネルギーのタイプを変えるパワーとして登録している")
        return problems

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)

    def resolve(self, state: GameState, use: PowerUse) -> None:
        _, user = state.find_pokemon(use.pokemon_id)
        added = tuple((user.pokemon_id, uid) for uid in user.energy if (user.pokemon_id, uid) not in state.energy_burn)
        state.energy_burn = state.energy_burn + added
        state.add_event("energy_burn", player=use.player, pokemon=user.card, pokemon_id=user.pokemon_id, power=str(use.key),
                        energies=tuple(user.energy), energy_type=self.energy_type.value)


@dataclass(frozen=True)
class RemoveOwnCounterOncePerTurn(PowerEffect):
    """この力は、自分の番ごとに 1 回使える。このカードにのっているダメージカウンターを、``counters`` 個とりのぞく。このカードが「ねむり・マヒ・こんらん」
    状態の時、この力は使えない（v0.31。カツラのロコンの「しぜんになおる」。kyuura の印刷の文面）。

    - 使った回数を状態に持つ（``GameState.power_uses_this_turn``。場のポケモンの番号と特殊能力の位置。番の最初に空。ログから数えない）。同じ番に 2 回目は
      ``POWER_ALREADY_USED``。
    - ダメージカウンターがのっていないときに使えるか（使ったことになるか）は決められない（HC8。v0.2b の「きずぐすり」の ``UNRESOLVED_POTION_WITHOUT_DAMAGE``
      と同じ形）。ほかの確認のあとで ``UNRESOLVED_POWER_HEAL_WITHOUT_DAMAGE``。
    """

    counters: int
    implementation_id = "remove_own_counter_once_per_turn"
    once_per_turn: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        problems = []
        if power.kind != "pokemon_power":
            problems.append(f"種類 {power.kind!r} のパワーを、使用を宣言するポケモンパワーとして登録している")
        if power.text_ja is None:
            problems.append("説明文のないポケモンパワーを、ダメージカウンターをとりのぞくパワーとして登録している")
        return problems

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)
        require_power_not_used(state, use)
        _, user = state.find_pokemon(use.pokemon_id)
        if user.damage == 0:
            raise UnsupportedError(
                "UNRESOLVED_POWER_HEAL_WITHOUT_DAMAGE",
                f"ポケモン {use.pokemon_id} にダメージカウンターがのっていないときに、この特殊能力を使えるか（自分の番ごとに1回を使ったことになるか）は"
                "決められないので扱わない（HC8）",
            )

    def resolve(self, state: GameState, use: PowerUse) -> None:
        _, user = state.find_pokemon(use.pokemon_id)
        per = state.rules.damage_per_counter
        before = user.damage
        removed = min(self.counters, before // per)
        user.damage = before - removed * per
        # 使った記録（power_uses_this_turn）は、v0.42 から宣言のときにエンジンが付ける（engine._use_pokemon_power。状態の結果は v0.41 と同じ）
        state.add_event("power_heal", player=use.player, pokemon=user.card, pokemon_id=user.pokemon_id, power=str(use.key),
                        counters=removed, amount=removed * per, damage_before=before, total_damage=user.damage)


@dataclass(frozen=True)
class HealOnEnergyAttach(PowerEffect):
    """このカードに ``energy_type`` エネルギーカードを 1 枚つけるたびに、このカードにのっているダメージカウンターを、``counters`` 個とりのぞく。このカードが
    「ねむり・マヒ・こんらん」状態の時、この力は使えない（v0.31。カツラのキュウコンの「ほのおでかいふく」。kyuura の印刷の文面。英語版の「from your hand」は
    使わない）。

    決められたとき（エネルギーカードをつけたとき）に自動的にはたらき、使用を宣言しない（``declared = False``。p.323）。つける処理（手札からつける通常の操作・
    特殊能力・ワザ）のあとに ``after_energy_attached`` が評価する。かがくへんかガスで消える（``continuous.suppressors_of``）。ダメージカウンターがなければ何も
    しない。
    """

    energy_type: EnergyType
    counters: int
    implementation_id = "heal_on_energy_attach"
    declared: ClassVar[bool] = False

    def check(self, power: Power) -> list[str]:
        problems = []
        if power.kind != "pokemon_power":
            problems.append(f"種類 {power.kind!r} のパワーを、ポケモンパワーとして登録している")
        if power.text_ja is None:
            problems.append("説明文のないポケモンパワーを、エネルギーをつけたら回復するパワーとして登録している")
        return problems


def after_energy_attached(state: GameState, owner: int, pokemon: PokemonInPlay, energy: int) -> None:
    """場のポケモン ``pokemon`` にエネルギーカード ``energy`` をつけたあと（v0.31）: つけたときに自動的にはたらく特殊能力（``HealOnEnergyAttach``。
    カツラのキュウコンの「ほのおでかいふく」）を評価する。つける処理（``engine._attach_energy``・あまごい・ワザの効果）のログのあとに呼ぶ。

    はたらくのは、いちばん上のカードの特殊能力で、つけたカードがその特殊能力のタイプの基本エネルギーカード、ねむり・マヒ・こんらんでない、かがくへんかガスに
    消されていない、ダメージカウンターがのっている、のすべてのとき。ログ ``power_heal``（``trigger`` はつけたカード）。"""
    card = state.card_def(energy)
    for slot in powers_of(state, pokemon):  # v0.49: 今持つ特殊能力
        power, effect = slot.power, slot.effect
        if not isinstance(effect, HealOnEnergyAttach):
            continue
        if not card.is_basic_energy or card.provides is not effect.energy_type:
            continue
        if pokemon.conditions.asleep or pokemon.conditions.paralyzed or pokemon.conditions.confused:
            continue
        from .continuous import suppressors_of

        if suppressors_of(state, power):
            continue
        per = state.rules.damage_per_counter
        before = pokemon.damage
        removed = min(effect.counters, before // per)
        if not removed:
            continue
        pokemon.damage = before - removed * per
        state.add_event("power_heal", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, power=str(slot.key),
                        counters=removed, amount=removed * per, damage_before=before, total_damage=pokemon.damage, trigger=energy)


# ---------------------------------------------------------------- v0.42 の特殊能力（docs/power-decisions-v0.42.md）


def _check_power_text(power: Power, what: str, accepted: Iterable[str]) -> list[str]:
    """v0.42: 宣言する・自動的にはたらく特殊能力の種類と説明（kyuura の写しの印刷の文面）が、``accepted`` のどれかと同じか。"""
    problems = []
    if power.kind != "pokemon_power":
        problems.append(f"種類 {power.kind!r} のパワーを、ポケモンパワー（特殊能力）として登録している")
    accepted = tuple(accepted)
    if power.text_ja not in accepted:
        problems.append(f"説明 {power.text_ja!r} が、{what}の説明（{' / '.join(repr(t) for t in accepted)}）ではない")
    return problems


def _power_coin(state: GameState, use: PowerUse) -> CoinSide:
    """特殊能力のコイン 1 枚（v0.42）。投げるのは特殊能力を使ったプレイヤー（``flip_coins`` の ``source="power"``、``effect`` は ``PowerKey`` の文字列。
    v0.11 の「こんじょう」のコインと同じ形）。"""
    _, user = state.find_pokemon(use.pokemon_id)
    flips = flip_coins(state, use.player, 1, source="power", effect=str(use.key), card=user.card, pokemon_id=user.pokemon_id)
    return flips.results[0]


def _power_decision_form(decision: PendingDecision, use: PowerUse, *, kind: str, choices: tuple[int, int], options, unresolved=()) -> list[str]:
    """v0.42: 特殊能力の決定の形（決定するのは使ったプレイヤー・種類・選ぶ数・選べるもの・選ぶと止める選択）。"""
    problems = []
    if decision.player != use.player:
        problems.append(f"特殊能力 {use.key} の決定をするのが、使ったプレイヤー {use.player} ではない（{decision.player}）")
    if decision.kind != kind:
        problems.append(f"特殊能力 {use.key} の決定の種類 {decision.kind} が {kind} ではない")
    if (decision.min_choices, decision.max_choices) != choices:
        problems.append(f"特殊能力 {use.key} の決定の選ぶ数 {decision.min_choices}〜{decision.max_choices} が {choices[0]}〜{choices[1]} ではない")
    options = tuple(options)
    if decision.options != options:
        problems.append(f"特殊能力 {use.key} の決定の選べるもの {decision.options} が {options} ではない")
    if tuple(decision.context_value("unresolved_choices", ())) != tuple(unresolved):
        problems.append(f"特殊能力 {use.key} の決定の選ぶと止める選択 {decision.context_value('unresolved_choices', ())} が {tuple(unresolved)} ではない")
    return problems


def _damaged_own_pokemon(state: GameState, player: int) -> list[int]:
    per = state.rules.damage_per_counter
    return [pokemon.pokemon_id for pokemon in state.players[player].in_play() if pokemon.damage >= per]


HEALING_TEXTS = (
    "このカードの持ち主は、自分の番に1回だけコインを投げて「おもて」なら、自分の場のポケモン1匹からダメージカウンターを1つとりのぞくことができる。"
    "「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
)


@dataclass(frozen=True)
class HealOwnPokemonOnHeads(PowerEffect):
    """自分の番に 1 回だけコインを投げて「おもて」なら、自分の場のポケモン 1 匹からダメージカウンターを ``counters`` 個とりのぞく（v0.42。ラフレシアの
    ［ヒーリング］。kyuura の印刷の文面「このカードの持ち主は、自分の番に1回だけコインを投げて「おもて」なら、自分の場のポケモン1匹からダメージカウンターを1つ
    とりのぞくことができる。「ねむり・マヒ・こんらん」状態の時、この力は使えない。」）。

    - 宣言して使う（「とりのぞくことができる」）。自分の番に 1 回だけ（``once_per_turn``。場のポケモンごと。v0.31 のしぜんになおると同じ記録）。コインの「うら」
      でも使ったことになる（宣言のときに記録する）
    - ねむり・マヒ・こんらんのこのカードは使えない（どくは使える）
    - 文面の順番どおり、コインを投げてから（「おもて」なら）とりのぞくポケモンを選ぶ（決定 ``SELECT_POKEMON``。選ぶのは使ったプレイヤー。選べるものは自分の場の、
      ダメージカウンターがのっているポケモン（バトル場 → ベンチ。このカードを含む）。1 匹でも決定を出す）。「うら」なら何もしない
    - 自分の場のどのポケモンにもダメージカウンターがのっていないときに使えるか（使ったことになるか）は決められない（しぜんになおるの HC8 と同じ問い。
      ``UNRESOLVED_POWER_HEAL_WITHOUT_DAMAGE``。ほかの確認のあと、宣言の前）
    - とりのぞくのは、のっている数まで（GR-2000-P320-RECOVERY）。特殊能力の効果なので「ワザをうけない」状態・「とうめい」は関係しない。ログ ``power_heal``
      （``pokemon_id`` はとりのぞいたポケモン、``user_pokemon_id`` は使ったポケモン）
    """

    counters: int = 1
    implementation_id = "heal_own_pokemon_on_heads"
    once_per_turn: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "コインで自分の場のポケモンを回復する特殊能力", HEALING_TEXTS)

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)
        require_power_not_used(state, use)
        if not _damaged_own_pokemon(state, use.player):
            raise UnsupportedError(
                "UNRESOLVED_POWER_HEAL_WITHOUT_DAMAGE",
                "自分の場のどのポケモンにもダメージカウンターがのっていないときに、この特殊能力を使えるか（自分の番に1回を使ったことになるか）は"
                "決められないので扱わない（しぜんになおるの HC8 と同じ問い）",
            )

    def resolve(self, state: GameState, use: PowerUse) -> None:
        if _power_coin(state, use) is not CoinSide.HEADS:
            return
        push_power_decision(state, use, kind=SELECT_POKEMON, player=use.player, options=_damaged_own_pokemon(state, use.player))

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        owner, target = state.find_pokemon(choices[0])
        per = state.rules.damage_per_counter
        if owner != use.player or target.damage < per:
            raise RuntimeError(f"ヒーリングでとりのぞくポケモン {choices} が、自分の場のダメージカウンターがのっているポケモンではない（エンジンの不具合）")
        before = target.damage
        removed = min(self.counters, before // per)
        target.damage = before - removed * per
        state.add_event("power_heal", player=use.player, pokemon=target.card, pokemon_id=target.pokemon_id, power=str(use.key),
                        counters=removed, amount=removed * per, damage_before=before, total_damage=target.damage, user_pokemon_id=use.pokemon_id)

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        return _power_decision_form(decision, use, kind=SELECT_POKEMON, choices=(1, 1), options=_damaged_own_pokemon(state, use.player))


def _move_one_counter(state: GameState, use: PowerUse, source: PokemonInPlay, target: PokemonInPlay, *, owner: int | None = None) -> None:
    """ダメージカウンターを 1 個、``source`` から ``target`` へのせかえる（v0.7 のダメージスワップの処理。v0.42 で共通にした）。ダメージの計算をせず、
    ログ ``move_damage_counter``（v0.7 と同じ形。v0.42: 相手の場のポケモンのあいだ（のろい）なら ``owner``（のせかえたポケモンの持ち主））。"""
    _, user = state.find_pokemon(use.pokemon_id)
    per_counter = state.rules.damage_per_counter
    source.damage -= per_counter
    target.damage += per_counter
    extra = {} if owner is None else {"owner": owner}
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
        **extra,
    )


STRANGE_BEHAVIOR_TEXTS = (
    "このカードが「きぜつ」しない範囲なら、自分の場のポケモンにのっているダメージカウンターを好きなだけ取り、このカードの上にのせてよい。"
    "「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
)


@dataclass(frozen=True)
class MoveDamageCounterToSelf(PowerEffect):
    """このカードが「きぜつ」しない範囲なら、自分の場のポケモンにのっているダメージカウンターを好きなだけ取り、このカードの上にのせてよい（v0.42。ヤドランの
    ［へんなこうどう］。kyuura の印刷の文面）。

    - 宣言して使う。回数の制限はない（数えない）。ねむり・マヒ・こんらんのこのカードは使えない（どくは使える）
    - v0.7 のダメージスワップ（``MoveDamageCounter``）と同じ処理（``_move_one_counter``。ダメージの計算をしない・「ダメージを受けた」ことにならない。
      GR-2000-P320-COUNTER-MOVE）で、移動先がいつもこのカード: ``source``（移動元。自分の場の、このカードと別の、ダメージカウンターがのっているポケモン）
      だけを選ぶ。``target``・``energy`` は指定しない（``POWER_CHOICE_NOT_USED``）
    - 1 回の使用で 1 個（ダメージスワップの S3 と同じ実装上の仮定。好きなだけ取れるので、何個取っても 1 個ずつの使用に分けられる。移動先はいつもこのカードで、
      ダメージは増えていくだけなので、途中できぜつする状態を通らない）
    - このカードが「きぜつ」するなら使えない（``WOULD_KNOCK_OUT``。状態を変える前。「きぜつ」しない範囲）
    """

    implementation_id = "move_damage_counter_to_self"

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "自分の場のダメージカウンターをこのカードにのせる特殊能力", STRANGE_BEHAVIOR_TEXTS)

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        if use.source is None:
            raise IllegalActionError("POWER_CHOICE_MISSING", "ダメージカウンターの移動元（source）を指定する（移動先はこのカード）")
        if use.energy is not None or use.target is not None:
            raise IllegalActionError("POWER_CHOICE_NOT_USED", "このポケモンパワーの移動先はこのカードなので、エネルギー（energy）・移動先（target）は指定しない")
        source = _own_pokemon(state, use, use.source, "SOURCE")
        if use.source == use.pokemon_id:
            raise IllegalActionError("SAME_POKEMON", "ダメージカウンターは、このカード以外のポケモンから取る")
        per_counter = state.rules.damage_per_counter
        if source.damage < per_counter:
            raise IllegalActionError("NO_DAMAGE_COUNTERS", f"移動元のポケモン {use.source} にダメージカウンターがのっていない")
        _, user = state.find_pokemon(use.pokemon_id)
        if would_be_knocked_out(state, user, user.damage + per_counter):
            raise IllegalActionError("WOULD_KNOCK_OUT", f"このカード（ポケモン {use.pokemon_id}）にダメージカウンターをのせると「きぜつ」する（「きぜつ」しない範囲なら）")

    def resolve(self, state: GameState, use: PowerUse) -> None:
        _, user = state.find_pokemon(use.pokemon_id)
        _, source = state.find_pokemon(use.source)
        _move_one_counter(state, use, source, user)


CURSE_TEXTS = (
    "自分の番ごとに1回だけ使える。相手の場のポケモンにのっているダメージカウンターを1つ選び、相手の場の別のポケモンの上にのせてよい。"
    "「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
)


@dataclass(frozen=True)
class MoveOpponentDamageCounter(PowerEffect):
    """自分の番ごとに 1 回だけ使える。相手の場のポケモンにのっているダメージカウンターを 1 つ選び、相手の場の別のポケモンの上にのせてよい（v0.42。ゲンガーの
    ［のろい］。kyuura の印刷の文面）。

    - 宣言して使う。自分の番ごとに 1 回（``once_per_turn``）。ねむり・マヒ・こんらんのこのカードは使えない（どくは使える）
    - 選ぶもの: ``source``（移動元。相手の場の、ダメージカウンターがのっているポケモン）と ``target``（移動先。相手の場の別のポケモン）。``energy`` は指定しない
    - 説明に「きぜつ」の制限はない（ダメージスワップの「この力によってポケモンが「きぜつ」しないかぎり」・へんなこうどうの「「きぜつ」しない範囲なら」がない）。
      文面にない制限を加えない。のせたダメージカウンターで HP 以上になったポケモンは、特殊能力の処理のあとに「きぜつ」する（``resolution.after_power``。
      サイド・勝ち負け・ふしちょう・交代。p.320「ダメージカウンターの移動によって、ダメージの数がポケモンのHPと同じか、それより大きくなったら、そのポケモンは
      「きぜつ」します」）
    - ダメージカウンターの移動はワザによるダメージではない（GR-2000-P320-COUNTER-MOVE）。ダメージの計算をせず、「ダメージを受けない」「ワザをうけない」状態・
      「とうめい」（どれもワザについての効果）は関係しない。「ダメージを受けたとき」の効果（はんげき・ぼうぎょかふん）ははたらかず、こんじょう（相手のワザによる
      ダメージで「きぜつ」するとき）は使えない
    """

    implementation_id = "move_opponent_damage_counter"
    may_knock_out: ClassVar[bool] = True
    once_per_turn: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "相手の場のダメージカウンターをのせかえる特殊能力", CURSE_TEXTS)

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        if use.source is None or use.target is None:
            raise IllegalActionError("POWER_CHOICE_MISSING", "ダメージカウンターの移動元（source）と移動先（target）を指定する（どちらも相手の場のポケモン）")
        if use.energy is not None:
            raise IllegalActionError("POWER_CHOICE_NOT_USED", "このポケモンパワーはダメージカウンターをのせかえるので、エネルギー（energy）は指定しない")
        require_power_not_used(state, use)
        source = _opponent_pokemon(state, use, use.source, "SOURCE")
        _opponent_pokemon(state, use, use.target, "TARGET")
        if use.source == use.target:
            raise IllegalActionError("SAME_POKEMON", "ダメージカウンターは、のっているポケモンとは別のポケモンにのせる（「別のポケモン」）")
        if source.damage < state.rules.damage_per_counter:
            raise IllegalActionError("NO_DAMAGE_COUNTERS", f"移動元のポケモン {use.source} にダメージカウンターがのっていない")

    def resolve(self, state: GameState, use: PowerUse) -> None:
        _, source = state.find_pokemon(use.source)
        _, target = state.find_pokemon(use.target)
        _move_one_counter(state, use, source, target, owner=1 - use.player)


def _opponent_pokemon(state: GameState, use: PowerUse, pokemon_id: int, role: str) -> PokemonInPlay:
    """パワーの説明が選ばせる「相手の場のポケモン」（v0.42。``role`` は ``SOURCE``・``TARGET``。コードの接頭辞）。"""
    found = state.find_pokemon(pokemon_id)
    if found is None:
        raise IllegalActionError(f"{role}_NOT_IN_PLAY", f"場のポケモンの番号 {pokemon_id!r} は場にいない")
    owner, pokemon = found
    if owner == use.player:
        raise IllegalActionError(f"{role}_NOT_OPPONENTS", f"場のポケモン {pokemon_id} は自分の場のポケモン（相手の場のポケモンだけ）")
    return pokemon


DEFENSIVE_POLLEN_TEXTS = (
    "このカードがバトル場でワザによるダメージを受けた時、（このカードが「きぜつ」するかしないかにかかわらず）コインを投げ、「おもて」なら、ダメージを与えたポケモンを"
    "「こんらん」状態にする。この力は、このカードが「ねむり・マヒ・こんらん」状態でも、必ずはたらく。",
)


@dataclass(frozen=True)
class ConfuseDamageSourceOnHeads(PowerEffect):
    """このカードがバトル場でワザによるダメージを受けたとき、（このカードが「きぜつ」するかしないかにかかわらず）コインを投げ、「おもて」なら、ダメージを与えた
    ポケモンを「こんらん」状態にする。ねむり・マヒ・こんらん状態でも、必ずはたらく（v0.42。エリカのラフレシアの［ぼうぎょかふん］。kyuura の印刷の文面）。

    - 宣言しない（``declared`` が False。「はたらく」。決められたときに自動的にはたらく。p.311・p.323）。``UsePokemonPower`` は ``POWER_NOT_DECLARABLE``
    - はたらく時点・処理は、はんげき（v0.10）と同じ窓（解決の基盤の「ダメージを受けるとき」に候補になり、そのワザのダメージの処理がすべて終わったあと・ダメージ
      以外の効果の前に処理する。CR-COUNTERATTACK-TIMING と同じ時点。効果の定義 ``catalog.DEFENSIVE_POLLEN``）。受けるときにバトル場にいること（ベンチで受けた
      ダメージでははたらかない）・ワザによるダメージ（最終ダメージが 0 より大きい）であること。こんらんの 20・どく・特殊能力のダメージ・ダメージカウンターの移動
      でははたらかない
    - 特殊状態の条件はない（「必ずはたらく」。定義の ``disabled_by`` は空）。かがくへんかガスで消える（受けるときに確かめる）
    - コインを投げるのはこのカードの持ち主。「おもて」なら、ダメージを与えたポケモン（ワザを使ったポケモン。返す効果のダメージなら、その効果を持つポケモン）を
      こんらん状態にする（特殊能力の効果なので「ワザをうけない」状態・「とうめい」は関係しない）。ダメージを与えたポケモンが、そのときすでに HP 以上なら、処理の
      対象がないので投げない（はんげきの C15・v0.38 の ``has_target`` と同じ読み方。ログ ``power_confusion_skipped``）
    """

    implementation_id = "confuse_damage_source_on_heads"
    declared: ClassVar[bool] = False

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "ワザのダメージを受けたときにダメージを与えたポケモンをこんらんにする特殊能力", DEFENSIVE_POLLEN_TEXTS)


STEP_IN_TEXTS = (
    "この能力はベンチにいる時に使う。自分の番ごとに1回だけ使える。バトル場にいる自分の対戦ポケモンとこのカードとを交換することができる。"
    "「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
)


@dataclass(frozen=True)
class SwitchSelfFromBench(PowerEffect):
    """この力は、自分の番ごとに 1 回、このカードがベンチにいるときに使える。バトル場にいる自分の対戦ポケモンと、このカードを入れ替える（v0.42。カイリューの
    ［かけつける］。処理に使う文面は kyuura の data/curation/card_differences.json の PMCG3-043 の記録（確度: 確実）が引く『オフィシャルブック2000』p.249 の
    最新の説明。印刷の文面の「「ねむり・マヒ・こんらん」状態の時、この力は使えない」は最新の説明にない（ベンチのポケモンは特殊状態にならないので、実際の違いは
    ない。p.322））。

    - 宣言して使う。自分の番ごとに 1 回（``once_per_turn``）。このカードがベンチにいるときだけ（``POKEMON_NOT_ON_BENCH``）。選ぶものはない
    - 入れ替えはポケモンいれかえと同じ処理（``_switch_active_with_bench``。ログ ``switch`` に特殊能力 ``effect``）。「にげる」ではない（にげるエネルギーを
      払わない・こんらんのコインがない・「にげる」ことができない効果（v0.36）に制限されない。p.325）。ベンチにもどったポケモンの特殊状態・持続する効果は消える
      （p.322。理由 ``switch``）
    """

    implementation_id = "switch_self_from_bench"
    once_per_turn: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "ベンチからバトル場のポケモンと入れ替わる特殊能力", STEP_IN_TEXTS)

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_no_choices(use)
        if not any(pokemon.pokemon_id == use.pokemon_id for pokemon in state.players[use.player].bench):
            raise IllegalActionError("POKEMON_NOT_ON_BENCH", f"ポケモン {use.pokemon_id} はベンチにいない（この力は、このカードがベンチにいるときに使える）")
        require_power_not_used(state, use)

    def resolve(self, state: GameState, use: PowerUse) -> None:
        _switch_active_with_bench(state, use.player, use.pokemon_id, effect=str(use.key))


SWEET_TRAP_TEXTS = (
    "この力は、自分の番ごとに1回使える。コインを投げて「おもて」なら、相手の控えポケモンから1匹を選び、相手の対戦ポケモンと入れ替える。"
    "このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
)


@dataclass(frozen=True)
class SwitchOpponentOnHeads(PowerEffect):
    """この力は、自分の番ごとに 1 回使える。コインを投げて「おもて」なら、相手の控えポケモンから 1 匹を選び、相手の対戦ポケモンと入れ替える（v0.42。エリカの
    ウツボットの［かおりのわな］。kyuura の印刷の文面）。

    - 宣言して使う。自分の番ごとに 1 回（``once_per_turn``。コインの「うら」でも使ったことになる）。ねむり・マヒ・こんらんのこのカードは使えない
    - 文面の順番どおり、コインを投げてから（「おもて」なら）入れ替える相手の控えポケモンを選ぶ（決定 ``SELECT_POKEMON``。選ぶのは使ったプレイヤー。突風（v0.21）と
      同じ。1 匹でも決定を出す）。入れ替えは突風と同じ処理（``_switch_active_with_bench`` を相手の場で。ログ ``switch`` に特殊能力 ``effect``）。特殊能力の効果
      なので「とうめい」・「ワザをうけない」状態は関係しない
    - 相手に控えポケモンがいないときに使えるか（コインを投げ、使ったことになるか）は決められない（PW1。``UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH``。
      突風の GW5 とは別の問い（トレーナーではない・コインがある））。宣言の前に止める
    - 使ったプレイヤーの対戦ポケモンが受けている「すごむ」の効果を与えたポケモンが相手のベンチにいるとき、そのポケモンを選ぶと止める（v0.40 の SG1。突風と同じ。
      ``unresolved_choices``）。選べる控えがそのポケモンだけなら、宣言の前に止める
    """

    implementation_id = "switch_opponent_on_heads"
    once_per_turn: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "コインで相手の控えと入れ替える特殊能力", SWEET_TRAP_TEXTS)

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)
        require_power_not_used(state, use)
        bench = state.players[1 - use.player].bench
        if not bench:
            raise UnsupportedError(
                "UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH",
                "相手に控えポケモンがいない。このときに、この特殊能力を使えるか（コインを投げ、自分の番ごとに1回を使ったことになるか）は、kyuura の記録・印刷の文面から"
                "決められないので扱わない（PW1）",
            )
        returning = _returning_lock_sources(state, use.player)
        if returning and len(returning) == len(bench):
            raise UnsupportedError("UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED", _ATTACK_LOCK_SOURCE_RETURNED_REASON)
        switch_max_hp_drop_check(state, 1 - use.player)  # v0.48: MH1（「おもて」のあとの入れ替えで下がるなら、コインの前に止める）
        blocked = switch_choice_stops(state, 1 - use.player)
        if blocked and len({pid for pid, _, _ in blocked} | set(returning)) == len(bench):
            # v0.49: どの控えと入れ替えても、決められない姿（メタモンの［へんしん］の TF1・TF2）になる。コインの前に止める（「おもて」のあとに答えのない決定を残さない）
            raise UnsupportedError(blocked[0][1], blocked[0][2])

    def resolve(self, state: GameState, use: PowerUse) -> None:
        if _power_coin(state, use) is not CoinSide.HEADS:
            return
        bench = state.players[1 - use.player].bench
        push_power_decision(state, use, kind=SELECT_POKEMON, player=use.player, options=[pokemon.pokemon_id for pokemon in bench],
                            unresolved_choices=_returning_lock_sources(state, use.player), unresolved_code="UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED",
                            unresolved_reason=_ATTACK_LOCK_SOURCE_RETURNED_REASON)

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if choices[0] not in [pokemon.pokemon_id for pokemon in state.players[1 - use.player].bench]:
            raise RuntimeError(f"かおりのわなで選んだポケモン {choices} が、相手の控えにいない（エンジンの不具合）")
        _switch_active_with_bench(state, 1 - use.player, choices[0], effect=str(use.key))

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        bench = state.players[1 - use.player].bench
        return _power_decision_form(decision, use, kind=SELECT_POKEMON, choices=(1, 1), options=[p.pokemon_id for p in bench],
                                    unresolved=_returning_lock_sources(state, use.player))


MATTER_EXCHANGE_TEXTS = (
    "自分の番ごとに1回使える。手札からカードを1枚選んでトラッシュする。その後、山札からカードを1枚引く。「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
)


@dataclass(frozen=True)
class DiscardThenDraw(PowerEffect):
    """自分の番ごとに 1 回使える。手札からカードを 1 枚選んでトラッシュする。その後、山札からカードを 1 枚引く（v0.42。わるいユンゲラーの［ぶっしつこうかん］。
    kyuura の印刷の文面）。

    - 宣言して使う。自分の番ごとに 1 回（``once_per_turn``）。ねむり・マヒ・こんらんのこのカードは使えない
    - トラッシュする手札のカードは、宣言のあと決定で選ぶ（``DISCARD_FROM_HAND``。v0.22 のパソコン通信と同じ種類。選べるものは手札のカード（手札の並び）。
      1 枚でも決定を出す）。``zones.discard_from_hand``（ログ ``discard_from_hand``）→ ``zones.draw_cards``（ログ ``draw``）。文面の順番（トラッシュ → 引く）
    - 山札が 0 枚なら引けない（効果で引くときは引けるだけ引く。0 枚でも負けではない。p.312。v0.2b のマサキ・v0.19 のオーキドはかせと同じ）
    - 手札が 0 枚のときに使えるか（トラッシュしないで引くか・使えないか）は決められない（PW2。``UNRESOLVED_POWER_DISCARD_WITHOUT_HAND``。説明はパソコン通信の
      「トラッシュしなければ、このカードは使えない」の形ではない）。宣言の前に止める
    """

    implementation_id = "discard_then_draw"
    once_per_turn: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "手札をトラッシュして山札から引く特殊能力", MATTER_EXCHANGE_TEXTS)

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)
        require_power_not_used(state, use)
        if not state.players[use.player].hand:
            raise UnsupportedError(
                "UNRESOLVED_POWER_DISCARD_WITHOUT_HAND",
                "手札がない。このときに、この特殊能力を使えるか（トラッシュしないで山札から引くか）は、kyuura の記録・印刷の文面から決められないので扱わない（PW2）",
            )

    def resolve(self, state: GameState, use: PowerUse) -> None:
        push_power_decision(state, use, kind=DISCARD_FROM_HAND, player=use.player, options=tuple(state.players[use.player].hand))

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        discard_from_hand(state, use.player, tuple(choices), power=str(use.key))
        deck = state.players[use.player].deck
        draw_cards(state, use.player, min(1, len(deck)))

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        return _power_decision_form(decision, use, kind=DISCARD_FROM_HAND, choices=(1, 1), options=state.players[use.player].hand)


COWARDICE_TEXTS = (
    "自分の番であれば、いつでもこのカードを手札にもどしてよい。その時、このカードにのっていたダメージカウンターなどを全てとりのぞき、ついていたカードも全てはがして"
    "すてる。このカードを場に出した番には、この力は使えない。また、「ねむり・マヒ・こんらん」状態の時にも、この力は使えない。",
)


@dataclass(frozen=True)
class ReturnSelfToHand(PowerEffect):
    """自分の番であれば、いつでもこのカードを手札にもどしてよい。その時、このカードにのっていたダメージカウンターなどを全てとりのぞき、ついていたカードも全て
    はがしてすてる。このカードを場に出した番には使えない。ねむり・マヒ・こんらんのときも使えない（v0.42。メノクラゲの［おくびょう］。kyuura の印刷の文面）。

    - 宣言して使う。回数は数えない（使えば場をはなれる）。場に出した番（``played_turn`` が今の番）は ``PLAYED_THIS_TURN``。バトル場・ベンチのどちらでも使える
    - 処理: ダメージカウンターをすべてとりのぞく（ログ ``remove_all_damage_counters``。v0.38 のいなくなると同じ）→ ついているカード（エネルギー・トレーナー）を
      トラッシュ（``zones.discard_attached_cards``）→ このカードを手札にもどす（``zones.return_in_play_to_hand``。山札にもどすのではない。切らない）→ 持続する効果を
      消す（理由 ``return_in_play_to_hand``）。特殊状態はなくなる（場をはなれた。p.322）
    - きぜつではない（サイドは取られない・ふしちょうは使えない）。バトル場のこのカードをもどしたら、特殊能力の処理のあとに、勝ち負けの判定（場にポケモンがいない
      プレイヤーは負ける。p.311）とバトル場に出す決定（このプレイヤー）。番は続く（``resolution.after_power``）
    """

    implementation_id = "return_self_to_hand"

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "このカードを手札にもどす特殊能力", COWARDICE_TEXTS)

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)
        _, user = state.find_pokemon(use.pokemon_id)
        if user.played_turn == state.turn_number:
            raise IllegalActionError("PLAYED_THIS_TURN", f"ポケモン {use.pokemon_id} はこの番に場に出したので、この力は使えない")

    def resolve(self, state: GameState, use: PowerUse) -> None:
        _, user = state.find_pokemon(use.pokemon_id)
        per = state.rules.damage_per_counter
        before = user.damage
        user.damage = 0
        state.add_event("remove_all_damage_counters", player=use.player, pokemon=user.card, pokemon_id=user.pokemon_id, power=str(use.key),
                        counters=before // per, amount=before, damage_before=before, total_damage=0)
        discard_attached_cards(state, use.player, user, power=str(use.key))
        return_in_play_to_hand(state, use.player, user, power=str(use.key))
        remove_persistent_effects(state, use.player, user, RETURN_IN_PLAY_TO_HAND)


# ---------------------------------------------------------------- v0.43 の特殊能力（docs/declared-entry-powers-v0.43.md）


POWER_ZERO_CARDS_CODE = "UNRESOLVED_POWER_ZERO_CARDS"
POWER_ZERO_CARDS_REASON = (
    "特殊能力の説明の「最大N枚」「1枚選び出し」で、選ぶカードが 0 枚になる（0 枚を選ぶ・選べるカードがない・ベンチに空きがない）とき、その特殊能力を使えるか"
    "（使ったことになるか・そのあと山札を切るか）は、kyuura の記録・印刷の文面から決められないので扱わない（PW3）"
)
ENERGY_BURN_MOVE_REASON = (
    "この番は「エナジーバーン」で「炎」エネルギーになっているエネルギーカード。説明の「「{type}」エネルギーカード」に当たるか（カードの種類か、今のエネルギーの"
    "タイプか）は決められないので扱わない（エナジートランスの HC10 と同じ問い）"
)


def _power_zero_cards(detail: str) -> UnsupportedError:
    return UnsupportedError(POWER_ZERO_CARDS_CODE, f"{detail}。{POWER_ZERO_CARDS_REASON}")


COIN_CONDITION_TEXTS = {
    # わるいクサイハナ（PMCG4-006）の［くさいかふん］
    CONFUSION: ("自分の番ごとに1回使える。コインを投げて「おもて」なら、相手の対戦ポケモンを「こんらん」状態にする。「うら」なら、自分の対戦ポケモンを「こんらん」"
                "状態にする。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",),
    # スリープ（PMCG4-033）の［えんかくさいみん］
    SLEEP: ("自分の番ごとに1回使える。コインを投げて「おもて」なら、相手の対戦ポケモンを「ねむり」状態にする。「うら」なら、自分の対戦ポケモンを「ねむり」状態にする。"
            "このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",),
}


@dataclass(frozen=True)
class CoinConditionOnEitherActive(PowerEffect):
    """自分の番ごとに 1 回使える。コインを投げて「おもて」なら相手の対戦ポケモンを、「うら」なら自分の対戦ポケモンを ``condition`` の特殊状態にする（v0.43。
    わるいクサイハナの［くさいかふん］（こんらん）・スリープの［えんかくさいみん］（ねむり）。kyuura の印刷の文面）。

    - 宣言して使う。自分の番ごとに 1 回（``once_per_turn``。宣言のときに記録するので、コインの「うら」でも使ったことになる）。ねむり・マヒ・こんらんのこの
      カードは使えない（どくは使える）。選ぶものはない
    - コインは使ったプレイヤーが 1 枚（``_power_coin``）。特殊状態にするのは、その時点のバトル場のポケモン（どちらのプレイヤーにも必ずいる）。このカードが
      バトル場にいて「うら」なら、このカード自身がその状態になる
    - 特殊状態にする処理は、ワザと同じ ``conditions.confuse``・``put_to_sleep``（重複の規定。p.322。ログ ``special_condition`` の ``effect`` は特殊能力）。
      ワザではないので、ワザを使うときのこんらんのコイン（p.309）はなく、ワザを防ぐ効果（「ワザをうけない」状態・「とうめい」。どれもワザについての効果）は
      関係しない
    """

    condition: str
    implementation_id = "coin_condition_on_either_active"
    once_per_turn: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if self.condition not in COIN_CONDITION_TEXTS:
            raise ValueError(f"コインでどちらかの対戦ポケモンを特殊状態にする特殊能力の状態 {self.condition!r} は {sorted(COIN_CONDITION_TEXTS)} のどれか")

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "コインでどちらかの対戦ポケモンを特殊状態にする特殊能力", COIN_CONDITION_TEXTS[self.condition])

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)
        require_power_not_used(state, use)
        # v0.49: 特殊状態にすると「ばける」でのせたカードがトラッシュされ、最大HPがのっているダメージ以下に下がる（MH1）・決められない姿になる場合は、受け付けるかが
        # コインの結果で変わらないよう、コインの前に止める（v0.48 のかおりのわなと同じ考え方）。どちらの結果も、状態の複製の上で特殊状態にして比べる
        for owner in (1 - use.player, use.player):
            trial = state.clone()
            target = trial.players[owner].active
            if self.condition == CONFUSION:
                confuse(trial, owner, target, effect=str(use.key))
            else:
                put_to_sleep(trial, owner, target, effect=str(use.key))
            stop = state_stop_after(state, trial)
            if stop is not None:
                raise UnsupportedError(stop[0], f"コインの結果でプレイヤー {owner} の対戦ポケモンを特殊状態にすると: {stop[1]}")

    def resolve(self, state: GameState, use: PowerUse) -> None:
        heads = _power_coin(state, use) is CoinSide.HEADS
        owner = 1 - use.player if heads else use.player
        target = state.players[owner].active
        if self.condition == CONFUSION:
            confuse(state, owner, target, effect=str(use.key))
        else:
            put_to_sleep(state, owner, target, effect=str(use.key))


def _energy_card_of_type(state: GameState, holder: PokemonInPlay, uid: int, energy_type: EnergyType) -> bool | None:
    """場のポケモン ``holder`` についているエネルギーカード ``uid`` が、説明の「「``energy_type``」エネルギーカード」か（v0.43）。この番に「エナジーバーン」で
    「炎」エネルギーになっていて（``GameState.energy_burn``）、カードの種類（基本エネルギーカードのタイプ）と今のエネルギーのタイプで答えが違うなら None
    （決められない。HC10）。"""
    definition = state.card_def(uid)
    printed = definition.is_basic_energy and definition.provides is energy_type
    if (holder.pokemon_id, uid) not in state.energy_burn:
        return printed
    current = state.energy_type_of(holder, uid) is energy_type
    return printed if printed == current else None


def _movable_energy(state: GameState, holders: Iterable[PokemonInPlay], energy_type: EnergyType) -> tuple[list[int], list[int]]:
    """``holders``（場の並び）についている「``energy_type``」エネルギーカード（ついている順）と、そのうち当たるかが決められないカード（HC10）。"""
    options: list[int] = []
    ambiguous: list[int] = []
    for holder in holders:
        for uid in holder.energy:
            matched = _energy_card_of_type(state, holder, uid, energy_type)
            if matched is None:
                options.append(uid)
                ambiguous.append(uid)
            elif matched:
                options.append(uid)
    return options, ambiguous


def _energy_burn_error(energy_type: EnergyType, detail: str) -> UnsupportedError:
    return UnsupportedError("UNRESOLVED_ENERGY_BURN_TRANSFER", f"{detail}: " + ENERGY_BURN_MOVE_REASON.format(type=energy_type.ja))


def _move_energy_to_user(state: GameState, use: PowerUse, cards: Iterable[int]) -> None:
    """自分の場のポケモンについているエネルギーカード ``cards`` を、同じ uid のまま、特殊能力を使ったポケモン（このカード）の ``energy`` の最後に、``cards`` の順に
    つけかえる（v0.43。複製・トラッシュ・持ち主の変更をしない。手札からつける通常の操作の回数 ``energy_attachments_this_turn`` は変えない。ログは 1 枚ずつ v0.5 の
    ``move_energy``）。"""
    _, user = state.find_pokemon(use.pokemon_id)
    for uid in cards:
        holder = next((p for p in state.players[use.player].in_play() if uid in p.energy), None)
        if holder is None or holder is user:
            raise RuntimeError(f"エネルギーカード {uid} が、このカード以外の自分の場のポケモンについていない（確認の漏れ。エンジンの不具合）")
        holder.energy.remove(uid)
        user.energy.append(uid)
        state.add_event("move_energy", player=use.player, pokemon=user.card, pokemon_id=user.pokemon_id, power=str(use.key), energy=uid,
                        from_pokemon_id=holder.pokemon_id, to_pokemon_id=user.pokemon_id)


GATHER_FIRE_TEXTS = (
    "自分の番ごとに1回使える。自分の場のポケモンについている「炎」エネルギーカードを1枚はがし、このカードにつけてよい。"
    "このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
)


@dataclass(frozen=True)
class TakeEnergyToSelf(PowerEffect):
    """自分の番ごとに 1 回使える。自分の場のポケモンについている「``energy_type``」エネルギーカードを 1 枚はがし、このカードにつけてよい（v0.43。ロケット団の
    ヒトカゲの［ほのおをもらう］。kyuura の印刷の文面）。

    - 宣言して使う。自分の番ごとに 1 回（``once_per_turn``）。ねむり・マヒ・こんらんのこのカードは使えない（どくは使える）
    - 選ぶもの（コマンドで指定する。v0.5 のエナジートランスと同じ形）: ``energy``（つけかえるエネルギーカード）と ``source``（そのカードがついている自分の場の
      ポケモン）。つける先はいつもこのカードなので ``target`` は指定しない（``POWER_CHOICE_NOT_USED``）
    - このカードについているカードを「はがし、このカードにつける」ことは、つけかえにならないので選べない（``SAME_POKEMON``。実装上の判断。英語版の文面は使わない）
    - 「「炎」エネルギーカード」は基本「炎」エネルギーカード（``WRONG_ENERGY_TYPE``）。「エナジーバーン」で「炎」になっているほかのタイプのカードは決められない（HC10）
    - つけかえは手札からつけること（p.310）ではないので、その回数は変えない。ログ ``move_energy``
    """

    energy_type: EnergyType
    implementation_id = "take_energy_to_self"
    once_per_turn: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        problems = _check_power_text(power, "自分の場のエネルギーカードを 1 枚このカードにつけかえる特殊能力", GATHER_FIRE_TEXTS)
        if self.energy_type is not EnergyType.FIRE:
            problems.append(f"説明は「炎」エネルギーカードをつけかえる（登録は {self.energy_type.ja}）")
        return problems

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        if use.energy is None or use.source is None:
            raise IllegalActionError("POWER_CHOICE_MISSING", "つけかえるエネルギーカード（energy）と、そのカードがついているポケモン（source）を指定する（つける先はこのカード）")
        if use.target is not None:
            raise IllegalActionError("POWER_CHOICE_NOT_USED", "このポケモンパワーのつける先はこのカードなので、移動先（target）は指定しない")
        require_power_not_used(state, use)
        source = _own_pokemon(state, use, use.source, "SOURCE")
        if use.source == use.pokemon_id:
            raise IllegalActionError("SAME_POKEMON", "このカードについているエネルギーカードは、このカードにつけかえられない（つけかえにならない）")
        if use.energy not in source.energy:
            raise IllegalActionError("ENERGY_NOT_ATTACHED", f"エネルギー {use.energy!r} はポケモン {use.source} についていない")
        matched = _energy_card_of_type(state, source, use.energy, self.energy_type)
        if matched is None:
            raise _energy_burn_error(self.energy_type, f"エネルギー {use.energy}")
        if not matched:
            raise IllegalActionError("WRONG_ENERGY_TYPE", f"エネルギー {use.energy} は「{self.energy_type.ja}」エネルギーカードではない")

    def resolve(self, state: GameState, use: PowerUse) -> None:
        _move_energy_to_user(state, use, (use.energy,))


SOAK_UP_TEXTS = (
    "この力は、自分の番ごとに1回使える。自分の場のポケモンについている「草」エネルギーカードを最大2枚選び、はがしてこのカードにつける。"
    "このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
)


@dataclass(frozen=True)
class TakeEnergiesToSelf(PowerEffect):
    """この力は、自分の番ごとに 1 回使える。自分の場のポケモンについている「``energy_type``」エネルギーカードを最大 ``max_cards`` 枚選び、はがしてこのカードに
    つける（v0.43。エリカのマダツボミの［ようぶんきゅうしゅう］。kyuura の印刷の文面）。

    - 宣言して使う。自分の番ごとに 1 回（``once_per_turn``）。ねむり・マヒ・こんらんのこのカードは使えない。1 回の使用で最大 2 枚（1 枚ずつ何度も使う形にしない）
    - 宣言のあと決定で選ぶ（``MOVE_ENERGY``。選ぶのは使ったプレイヤー。選べるものは、このカード以外の自分の場のポケモンについている基本「草」エネルギーカード
      （場の並び・ついている順）。同じカードは 2 回選べない）。選んだカードを場の並びの順につけかえる（ログ ``move_energy`` を 1 枚ずつ）
    - 0 枚にする（選べるカードがない・0 枚を選ぶ）ときは決められない（PW3。選べるカードがなければ宣言の前に、0 枚の答えは決定を待ったまま止める）
    - 「エナジーバーン」で「炎」になっている草エネルギーカードは決められない（HC10。選べるが選ぶと止める。選べるカードがどれもそうなら宣言の前に止める）
    """

    energy_type: EnergyType
    max_cards: int
    implementation_id = "take_energies_to_self"
    once_per_turn: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        problems = _check_power_text(power, "自分の場のエネルギーカードを最大N枚このカードにつけかえる特殊能力", SOAK_UP_TEXTS)
        if (self.energy_type, self.max_cards) != (EnergyType.GRASS, 2):
            problems.append(f"説明は「草」エネルギーカードを最大2枚（登録は {self.energy_type.ja}・{self.max_cards} 枚）")
        return problems

    def _options(self, state: GameState, use: PowerUse) -> tuple[list[int], list[int]]:
        holders = [p for p in state.players[use.player].in_play() if p.pokemon_id != use.pokemon_id]
        return _movable_energy(state, holders, self.energy_type)

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)
        require_power_not_used(state, use)
        options, ambiguous = self._options(state, use)
        if not options:
            raise _power_zero_cards(f"このカード以外の自分の場のポケモンに「{self.energy_type.ja}」エネルギーカードがついていない")
        if len(ambiguous) == len(options):
            raise _energy_burn_error(self.energy_type, f"選べるエネルギーカード {tuple(options)} がどれも")

    def resolve(self, state: GameState, use: PowerUse) -> None:
        options, ambiguous = self._options(state, use)
        push_power_decision(state, use, kind=MOVE_ENERGY, player=use.player, options=options, min_choices=0, max_choices=min(self.max_cards, len(options)),
                            unresolved_choices=ambiguous, unresolved_code="UNRESOLVED_ENERGY_BURN_TRANSFER",
                            unresolved_reason=ENERGY_BURN_MOVE_REASON.format(type=self.energy_type.ja))

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if not choices:
            raise _power_zero_cards("つけかえるエネルギーカードを 0 枚選んだ")
        _move_energy_to_user(state, use, tuple(uid for uid in decision.options if uid in choices))

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        options, ambiguous = self._options(state, use)
        return _power_decision_form(decision, use, kind=MOVE_ENERGY, choices=(0, min(self.max_cards, len(options))), options=options, unresolved=ambiguous)


ENERGY_CHARGE_TEXTS = (
    "この力は、このカードがバトル場にいる時だけ、使える。自分の控えポケモンについている「雷」エネルギーカードを好きなだけはがし、このカードにつける。"
    "このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
)


@dataclass(frozen=True)
class ChargeBenchEnergyToSelf(PowerEffect):
    """この力は、このカードがバトル場にいるときだけ使える。自分の控えポケモンについている「``energy_type``」エネルギーカードを好きなだけはがし、このカードに
    つける（v0.43。マチスのレアコイルの［エナジーチャージ］。kyuura の印刷の文面）。

    - 宣言して使う。回数の制限は書かれていないので数えない（日本語の文面にない「自分の番ごとに1回」を加えない）。このカードがバトル場にいるときだけ
      （``POKEMON_NOT_ACTIVE``）。ねむり・マヒ・こんらんのこのカードは使えない
    - 宣言のあと決定で選ぶ（``MOVE_ENERGY``。選べるものは自分の控えポケモンについている基本「雷」エネルギーカード（ベンチの並び・ついている順）。1 枚以上、
      何枚でも。同じカードは 2 回選べない）。0 枚・選べるカードがないときは、使っても何も変わらず回数もないので、使えない（``NO_ENERGY_TO_MOVE``。0 枚は選べない。
      実装上の判断）
    - 「エナジーバーン」で「炎」になっている雷エネルギーカードは決められない（HC10）
    """

    energy_type: EnergyType
    implementation_id = "charge_bench_energy_to_self"

    def check(self, power: Power) -> list[str]:
        problems = _check_power_text(power, "控えのエネルギーカードを好きなだけこのカードにつけかえる特殊能力", ENERGY_CHARGE_TEXTS)
        if self.energy_type is not EnergyType.LIGHTNING:
            problems.append(f"説明は「雷」エネルギーカード（登録は {self.energy_type.ja}）")
        return problems

    def _options(self, state: GameState, use: PowerUse) -> tuple[list[int], list[int]]:
        return _movable_energy(state, state.players[use.player].bench, self.energy_type)

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)
        active = state.players[use.player].active
        if active is None or active.pokemon_id != use.pokemon_id:
            raise IllegalActionError("POKEMON_NOT_ACTIVE", f"ポケモン {use.pokemon_id} はバトル場にいない（この力は、このカードがバトル場にいるときだけ使える）")
        options, ambiguous = self._options(state, use)
        if not options:
            raise IllegalActionError("NO_ENERGY_TO_MOVE", f"自分の控えポケモンに「{self.energy_type.ja}」エネルギーカードがついていない")
        if len(ambiguous) == len(options):
            raise _energy_burn_error(self.energy_type, f"選べるエネルギーカード {tuple(options)} がどれも")

    def resolve(self, state: GameState, use: PowerUse) -> None:
        options, ambiguous = self._options(state, use)
        push_power_decision(state, use, kind=MOVE_ENERGY, player=use.player, options=options, min_choices=1, max_choices=len(options),
                            unresolved_choices=ambiguous, unresolved_code="UNRESOLVED_ENERGY_BURN_TRANSFER",
                            unresolved_reason=ENERGY_BURN_MOVE_REASON.format(type=self.energy_type.ja))

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        _move_energy_to_user(state, use, tuple(uid for uid in decision.options if uid in choices))

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        options, ambiguous = self._options(state, use)
        return _power_decision_form(decision, use, kind=MOVE_ENERGY, choices=(1, len(options)), options=options, unresolved=ambiguous)


EVOLUTIONARY_LIGHT_TEXTS = (
    "自分の番ごとに1回使える。自分の山札から進化カードを1枚選び出し、相手プレイヤーに見せてから、手札に加える。その後、その山札をよく切る。"
    "「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
)


def deck_evolution_cards(state: GameState, player: int) -> list[int]:
    """プレイヤーの山札の進化カード（1 進化・2 進化のカード。uid の小さい順。山札の並びを決定に写さない）（v0.43）。今重ねられるか（進化の制限）では
    しぼらない（手札に加えるだけで、進化させるのではない）。"""
    return sorted(uid for uid in state.players[player].deck if state.card_def(uid).is_evolution_pokemon)


@dataclass(frozen=True)
class SearchEvolutionCardToHand(PowerEffect):
    """自分の番ごとに 1 回使える。自分の山札から進化カードを 1 枚選び出し、相手プレイヤーに見せてから、手札に加える。その後、その山札をよく切る（v0.43。
    わるいハクリューの［しんかのひかり］。kyuura の印刷の文面）。

    - 宣言して使う。自分の番ごとに 1 回（``once_per_turn``）。ねむり・マヒ・こんらんのこのカードは使えない
    - 宣言のあと決定で選ぶ（v0.22 の ``SEARCH_DECK``。選べるものは山札の進化カード（``deck_evolution_cards``）。1 枚）。進化させるのではないので、今進化できる
      カードにしぼらない。見せてから手札に加える（v0.24 の ``zones.reveal_deck_to_hand``。ログ ``reveal_from_deck`` の ``card`` は公開。選べたほかのカードは
      ログに書かない）→ 山札を切る（``zones.shuffle_deck``。ログ ``shuffle``。どちらも ``power``）
    - 山札に進化カードがない（山札が 0 枚を含む）ときは決められない（PW3。宣言の前に止める）
    """

    implementation_id = "search_evolution_card_to_hand"
    once_per_turn: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "山札から進化カードを手札に加える特殊能力", EVOLUTIONARY_LIGHT_TEXTS)

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)
        require_power_not_used(state, use)
        if not deck_evolution_cards(state, use.player):
            raise _power_zero_cards("山札に進化カードがない（山札が 0 枚を含む）")

    def resolve(self, state: GameState, use: PowerUse) -> None:
        push_power_decision(state, use, kind=SEARCH_DECK, player=use.player, options=deck_evolution_cards(state, use.player))

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if choices[0] not in deck_evolution_cards(state, use.player):
            raise RuntimeError(f"しんかのひかりで選んだカード {choices} が、山札の進化カードではない（エンジンの不具合）")
        reveal_deck_to_hand(state, use.player, choices[0], power=str(use.key))
        shuffle_deck(state, use.player, power=str(use.key))

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        return _power_decision_form(decision, use, kind=SEARCH_DECK, choices=(1, 1), options=deck_evolution_cards(state, use.player))


# ---- 場に出たときに 1 度だけ使える特殊能力（v0.43）


class EntryPower(PowerEffect):
    """場に出たときに 1 度だけ使える特殊能力の基底（v0.43。docs/declared-entry-powers-v0.43.md 3 章）。

    「この力は、このカードを手札から出した時、1度だけ使える」（わるいゴルバットの［こっそりかみつく］）・「この力は、このカードを手札から場に出した時、1度だけ
    使える」（わるいヤドランの［つりあげる］）・「この力は、このカードが場に出た時に1度だけ使える」（わるいカイリューの［てしたをよぶ］）。

    - 「使える」ので、使うかは持ち主が決める（宣言する特殊能力。``declared`` は真）。使う機会は場に出たときの 1 度だけで、エンジンが場に出す処理のあとに決定
      ``ENTRY_POWER`` で聞く（``offer_entry_power``）。``UsePokemonPower`` では使えない（``check_usable`` が ``POWER_NOT_USABLE_NOW``。機会が過ぎたあとに
      ``MAIN`` から使えない）。自分の番ごとの回数（``once_per_turn``）は使わない
    - ``from_hand_only``: 説明が「手札から出した時」「手札から場に出した時」なら真（手札から出す経路だけ。山札から重ねる進化では機会がない）。「場に出た時」なら偽
    - ``accept_problem``: 使うことを選ぶと止める場合（原典で決められない）。機会の決定の ``unresolved_choices`` にする
    - 使うことを選んだら、エンジンが宣言のログ ``pokemon_power``（``entry``）を残してから ``resolve`` を呼ぶ。そのあとの決定・再開・使用後の処理（きぜつ・
      バトル場に出す）は v0.42 の宣言する特殊能力と同じ（再開先 ``"power"``・``resolution.after_power``）
    """

    from_hand_only: ClassVar[bool] = True

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        raise IllegalActionError("POWER_NOT_USABLE_NOW", "この特殊能力は、このカードが場に出たときに 1 度だけ使える（そのときにエンジンが使うかを聞く）")

    def accept_problem(self, state: GameState, use: PowerUse) -> UnsupportedError | None:
        return None


def entry_power(state: GameState, card: int) -> tuple[int, EntryPower] | None:
    """カード ``card``（場のポケモンならいちばん上のカード）の、場に出たときに使える特殊能力（位置と実装。登録された ``EntryPower`` だけ）（v0.43）。"""
    definition = state.card_def(card)
    for index, power in enumerate(definition.powers):
        effect = state.effects.power_effect(definition.id, power)
        if isinstance(effect, EntryPower):
            return index, effect
    return None


def applicable_entry_power(state: GameState, card: int, *, from_hand: bool) -> tuple[int, EntryPower] | None:
    """カード ``card`` が場に出たときに、その経路（``from_hand``: 手札から出した）で使う機会がある特殊能力（v0.43）。経路が合わない（「手札から」の特殊能力を
    山札から重ねた）・今はたらいている「かがくへんかガス」に消されているなら None（``continuous.suppressors_of``。消された特殊能力には機会がない。p.323）。"""
    from .continuous import suppressors_of  # continuous.py は effects.py を読み込むので、使うときに読み込む

    found = entry_power(state, card)
    if found is None:
        return None
    index, effect = found
    if effect.from_hand_only and not from_hand:
        return None
    if suppressors_of(state, state.card_def(card).powers[index]):
        return None
    return found


def offer_entry_power(state: GameState, owner: int, pokemon: PokemonInPlay, *, from_hand: bool, return_to: tuple | None = None) -> bool:
    """場に出たポケモン ``pokemon``（持ち主 ``owner``）の、場に出たときに使える特殊能力を使うかを聞く決定を出す（v0.43）。出したら真。

    - いちばん上のカードに登録された ``EntryPower`` があり、経路が合い（``from_hand_only`` の特殊能力は手札から出したときだけ）、今はたらいている
      「かがくへんかガス」に消されていない（``continuous.suppressors_of``。消されていれば機会はない）ときだけ出す
    - 決定 ``ENTRY_POWER``: 決定するのは持ち主、選べるものはそのポケモンの番号 1 つ、0〜1 個（選ばない = 使わない）、再開先 ``"power"``。``context`` の
      ``"entry"`` は経路（``"hand"``）、``"return_to"`` は場に出した元の処理（トレーナーの効果の途中なら、終わったらそのトレーナーの処理にもどる）
    - 使うことを選ぶと止める場合（``accept_problem``）は、そのポケモンを ``unresolved_choices`` にする（使わないことは選べる）
    """
    found = applicable_entry_power(state, pokemon.card, from_hand=from_hand)
    if found is None:
        return False
    index, effect = found
    definition = state.card_def(pokemon.card)
    use = PowerUse(owner, pokemon.pokemon_id, PowerKey(definition.id, index), return_to=return_to)
    problem = effect.accept_problem(state, use)
    unresolved = {} if problem is None else {"unresolved_choices": (pokemon.pokemon_id,), "unresolved_code": problem.code,
                                              "unresolved_reason": problem.message}
    push_power_decision(state, use, kind=ENTRY_POWER, player=owner, options=(pokemon.pokemon_id,), context=(("entry", "hand" if from_hand else "play"),),
                        min_choices=0, max_choices=1, **unresolved)
    return True


SNEAK_ATTACK_TEXTS = (
    "この力は、このカードを手札から出した時、1度だけ使える。相手の場のポケモン1匹を選び、(「弱点・抵抗力」に関係なく)10ダメージ。",
)


@dataclass(frozen=True)
class DamageOpponentPokemonOnEntry(EntryPower):
    """この力は、このカードを手札から出したとき、1 度だけ使える。相手の場のポケモン 1 匹を選び、(「弱点・抵抗力」に関係なく) ``amount`` ダメージ（v0.43。
    わるいゴルバットの［こっそりかみつく］。kyuura の印刷の文面。pcg-search.com の転記は「手札から場に出した時」）。

    - 使う機会は手札から出したとき（手札から進化させたとき）だけ（``from_hand_only``）
    - 選ぶのは使ったプレイヤー（決定 ``SELECT_POKEMON``。選べるものは相手の場のポケモン（バトル場 → ベンチ）。1 匹）
    - 特殊能力によるダメージ（CR-COUNTERATTACK-IS-POWER-DAMAGE・CR-RESTLESS-SLEEP-NOT-ATTACK-CALCULATION と同じ読み方）: ワザによるダメージの計算（p.321。
      プラスパワー・ディフェンダー・「ダメージを受けない」状態）をせず、弱点・抵抗力は説明のとおり計算しない。「ワザをうけない」状態・「とうめい」（ワザについての
      効果）は関係しない。「相手のワザによって」ダメージを受けたときの効果（はんげき・ほのおのかべ・こうらがえし・わるいねぞう・ぼうぎょかふん）ははたらかず、
      こんじょう（相手のワザによるダメージ）は使えない。ダメージカウンターの移動（のろい）ではない（「ダメージを受けた」ことになる）
    - HP 以上になったポケモンは、特殊能力の処理のあとに「きぜつ」する（``may_knock_out``。``resolution.after_power`` のきぜつ・サイド・勝ち負け・ふしちょう・
      バトル場に出す。番は続く）。ログ ``power_damage``
    """

    amount: int
    implementation_id = "damage_opponent_pokemon_on_entry"
    may_knock_out: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        problems = _check_power_text(power, "手札から出したときに相手の場のポケモンにダメージを与える特殊能力", SNEAK_ATTACK_TEXTS)
        if self.amount != 10:
            problems.append(f"説明のダメージは 10（登録は {self.amount}）")
        return problems

    def resolve(self, state: GameState, use: PowerUse) -> None:
        push_power_decision(state, use, kind=SELECT_POKEMON, player=use.player, options=[p.pokemon_id for p in state.players[1 - use.player].in_play()])

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        found = state.find_pokemon(choices[0])
        if found is None or found[0] != 1 - use.player:
            raise RuntimeError(f"こっそりかみつくで選んだポケモン {choices} が、相手の場にいない（エンジンの不具合）")
        _, target = found
        _, user = state.find_pokemon(use.pokemon_id)
        # v0.46: 受けるポケモンの、受けるダメージ全体を書く常にはたらく特殊能力（なぞのかべ・ふしぎなバリアー）。今の対応カードでは結果が変わらない（20 は 30 より
        # 小さく、わるいゴルバットはたねポケモンではない）が、当てはめたら記録する
        amount, applied = received_power_damage(state, 1 - use.player, target, user, self.amount)
        target.damage += amount
        extra = {} if not applied else {"amount_before": self.amount, "received_modifiers": received_modifiers_log(applied)}
        state.add_event("power_damage", player=use.player, pokemon=user.card, pokemon_id=user.pokemon_id, power=str(use.key),
                        target_player=1 - use.player, target=target.card, target_pokemon_id=target.pokemon_id, amount=amount,
                        total_damage=target.damage, knocked_out=target.damage >= max_hp(state, target), **extra)

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        return _power_decision_form(decision, use, kind=SELECT_POKEMON, choices=(1, 1), options=[p.pokemon_id for p in state.players[1 - use.player].in_play()])


REEL_IN_TEXTS = (
    "この力は、このカードを手札から場に出した時、1度だけ使える。自分のトラッシュにあるポケモン(または進化)カードを最大3枚選び、相手プレイヤーに見せてから、"
    "手札に加える。",
)


def discard_pokemon_cards(state: GameState, player: int) -> list[int]:
    """プレイヤーのトラッシュのポケモンのカード（たねポケモン・進化カード。トラッシュの並び）（v0.43）。同じ名前の別のカードも別々に選べる。"""
    return [uid for uid in state.players[player].discard if state.card_def(uid).category == "pokemon"]


@dataclass(frozen=True)
class RecoverPokemonFromDiscardOnEntry(EntryPower):
    """この力は、このカードを手札から場に出したとき、1 度だけ使える。自分のトラッシュにあるポケモン（または進化）カードを最大 ``max_cards`` 枚選び、相手プレイヤーに
    見せてから、手札に加える（v0.43。わるいヤドランの［つりあげる］。kyuura の印刷の文面）。

    - 使う機会は手札から場に出したとき（手札から進化させたとき）だけ（``from_hand_only``）
    - 選ぶのは使ったプレイヤー（決定 ``RECOVER_POKEMON``。選べるものはトラッシュのポケモンのカード。1〜最大 3 枚。同じカードは 2 回選べない）。0 枚にすることは
      使わないことと結果が同じなので、機会の決定で使わないことを選ぶ（実装上の判断）。トラッシュにポケモンのカードがなければ、使っても何もしない（ログ
      ``recover_pokemon_none``。使わないときと状態は同じ）
    - 手札に加えるのは v0.12 の ``zones.return_discard_to_hand``（トラッシュの並びの順）。ログ ``recover_pokemon``（``cards`` は見せたので公開）
    """

    max_cards: int
    implementation_id = "recover_pokemon_from_discard_on_entry"

    def check(self, power: Power) -> list[str]:
        problems = _check_power_text(power, "手札から場に出したときにトラッシュのポケモンのカードを手札に加える特殊能力", REEL_IN_TEXTS)
        if self.max_cards != 3:
            problems.append(f"説明は最大3枚（登録は {self.max_cards}）")
        return problems

    def resolve(self, state: GameState, use: PowerUse) -> None:
        cards = discard_pokemon_cards(state, use.player)
        if not cards:
            _, user = state.find_pokemon(use.pokemon_id)
            state.add_event("recover_pokemon_none", player=use.player, pokemon=user.card, pokemon_id=user.pokemon_id, power=str(use.key))
            return
        push_power_decision(state, use, kind=RECOVER_POKEMON, player=use.player, options=cards, min_choices=1, max_choices=min(self.max_cards, len(cards)))

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        cards = tuple(uid for uid in discard_pokemon_cards(state, use.player) if uid in choices)
        if len(cards) != len(choices):
            raise RuntimeError(f"つりあげるで選んだカード {choices} が、トラッシュのポケモンのカードではない（エンジンの不具合）")
        return_discard_to_hand(state, use.player, cards)
        _, user = state.find_pokemon(use.pokemon_id)
        state.add_event("recover_pokemon", player=use.player, pokemon=user.card, pokemon_id=user.pokemon_id, power=str(use.key), cards=cards)

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        cards = discard_pokemon_cards(state, use.player)
        return _power_decision_form(decision, use, kind=RECOVER_POKEMON, choices=(1, min(self.max_cards, len(cards))), options=cards)


SUMMON_MINIONS_TEXTS = (
    "この力は、このカードが場に出た時に1度だけ使える。自分の山札からポケモンカード(進化カード以外)を最大2枚選び出し、自分のベンチに出す。その後、その山札をよく切る。",
)


def deck_basic_pokemon(state: GameState, player: int) -> list[int]:
    """プレイヤーの山札のたねポケモンのカード（uid の小さい順。山札の並びを決定に写さない）（v0.43）。"""
    return sorted(uid for uid in state.players[player].deck if state.card_def(uid).is_basic_pokemon)


@dataclass(frozen=True)
class BenchBasicsFromDeckOnEntry(EntryPower):
    """この力は、このカードが場に出たときに 1 度だけ使える。自分の山札からポケモンカード（進化カード以外）を最大 ``max_cards`` 枚選び出し、自分のベンチに出す。
    その後、その山札をよく切る（v0.43。わるいカイリューの［てしたをよぶ］。kyuura の印刷の文面）。

    - 使う機会は場に出たとき（手札から進化させた・ポケモン育て屋さんで進化させた）。「手札から」の条件はない（``from_hand_only`` は偽）。山札から重ねる進化
      （エリカのピッピの「つきのちから」）はワザの最中なので PW4（``programs.EvolveFromDeck``）
    - 選ぶのは使ったプレイヤー（決定 ``BENCH_FROM_DECK``。v0.32 と同じ種類。選べるものは山札のたねポケモンのカード。0〜min(2, ベンチの空き, 枚数)）。手札を通さずに
      ベンチに出す（v0.32 の ``zones.bench_from_deck``。場に出た番は今の番。ログ ``bench_from_deck`` に ``power``）→ 山札を切る（ログ ``shuffle`` に ``power``）
    - ベンチに出すカードが 0 枚になる（ベンチに空きがない・山札にたねポケモンがない・0 枚を選ぶ）ときは決められない（PW3。使うことを選ぶと止める・0 枚の答えは
      決定を待ったまま止める）
    """

    max_cards: int
    implementation_id = "bench_basics_from_deck_on_entry"
    from_hand_only: ClassVar[bool] = False

    def check(self, power: Power) -> list[str]:
        problems = _check_power_text(power, "場に出たときに山札のたねポケモンをベンチに出す特殊能力", SUMMON_MINIONS_TEXTS)
        if self.max_cards != 2:
            problems.append(f"説明は最大2枚（登録は {self.max_cards}）")
        return problems

    def _limit(self, state: GameState, use: PowerUse) -> int:
        space = state.rules.max_bench - len(state.players[use.player].bench)
        return min(self.max_cards, space, len(deck_basic_pokemon(state, use.player)))

    def accept_problem(self, state: GameState, use: PowerUse) -> UnsupportedError | None:
        if len(state.players[use.player].bench) >= state.rules.max_bench:
            return _power_zero_cards("ベンチに空きがない")
        if not deck_basic_pokemon(state, use.player):
            return _power_zero_cards("山札にたねポケモンがない（山札が 0 枚を含む）")
        return None

    def resolve(self, state: GameState, use: PowerUse) -> None:
        problem = self.accept_problem(state, use)
        if problem is not None:
            raise RuntimeError(f"てしたをよぶを、止めるはずの場合に使った（{problem.code}。機会の決定の確認の漏れ。エンジンの不具合）")
        push_power_decision(state, use, kind=BENCH_FROM_DECK, player=use.player, options=deck_basic_pokemon(state, use.player), min_choices=0,
                            max_choices=self._limit(state, use))

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if not choices:
            raise _power_zero_cards("ベンチに出すカードを 0 枚選んだ")
        cards = tuple(uid for uid in deck_basic_pokemon(state, use.player) if uid in choices)
        if len(cards) != len(choices) or len(cards) > self._limit(state, use):
            raise RuntimeError(f"てしたをよぶで選んだカード {choices} が、山札の選べるたねポケモンではない・多すぎる（エンジンの不具合）")
        _, user = state.find_pokemon(use.pokemon_id)
        for card in cards:
            pokemon = bench_from_deck(state, use.player, card)
            state.add_event("bench_from_deck", player=use.player, pokemon=user.card, pokemon_id=user.pokemon_id, power=str(use.key), card=card,
                            to_pokemon_id=pokemon.pokemon_id)
        shuffle_deck(state, use.player, power=str(use.key))

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        return _power_decision_form(decision, use, kind=BENCH_FROM_DECK, choices=(0, self._limit(state, use)), options=deck_basic_pokemon(state, use.player))


@dataclass(frozen=True)
class PowerEntry:
    """ポケモンパワーの登録の 1 件（v0.5）。

    - ``effect``: 実装
    - ``name_ja``・``text_ja``: 登録したときに照合した kyuura の写しのパワーの名前・印刷の文面（データが変わったら使えなくなる。
      処理の根拠ではない）
    - ``play_text_ja``: 実装がしたがう文面（『オフィシャルブック2000』の「最新の説明」。2026-10-15 からの方針の採用の記録で登録した
      ものは ``AttackEntry`` と同じ）
    - ``source``: ``play_text_ja`` の出典（誌面のページ。採用の記録で登録したものは ``AttackEntry`` と同じ）
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
        self._profiles: dict[CardDefinition, CardDefinition | None] = {}  # v0.47: 場での役割の定義（``play_profile``）の写し

    def __repr__(self) -> str:
        return f"EffectRegistry({self.id!r}, {len(self._attacks)} attacks, {len(self._trainers)} trainers, {len(self._powers)} powers)"

    # --- ワザ ---

    def attack_keys(self) -> tuple[AttackKey, ...]:
        return tuple(sorted(self._attacks))

    def attack_entry(self, card_id: str, attack_index: int) -> AttackEntry | None:
        return self._attacks.get(AttackKey(card_id, attack_index))

    def attack_problem(self, card_id: str, attack: Attack, attacks: tuple[Attack, ...] | None = None) -> str | None:
        """このワザを使えない理由。使えるなら None。``attacks``（v0.27）はそのカードのワザのすべて（渡したら、実装の ``card_problems`` で、
        ほかのワザを指す登録が合うかも確かめる）。"""
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
        if attacks is not None:
            problems = [*problems, *entry.effect.card_problems(attack, attacks)]
        return "; ".join(problems) or None

    def attack_effect(self, card_id: str, attack: Attack, attacks: tuple[Attack, ...] | None = None) -> AttackEffect | None:
        """使えるワザなら実装を返す。登録がない・データと合わないなら None。``attacks``（v0.27）は ``attack_problem`` と同じ。"""
        if self.attack_problem(card_id, attack, attacks) is not None:
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

    def play_profile(self, definition: CardDefinition) -> CardDefinition | None:
        """v0.47: ポケモンとして場に出せるトレーナーカード（登録した実装が ``PlayAsPokemon`` で、データと合う）なら、場にいるあいだの定義（場での役割）。ほかは None。
        印刷の定義 ``definition`` は変えない（別のインスタンスを作る）。同じ定義には同じインスタンスを返す。"""
        if definition in self._profiles:
            return self._profiles[definition]
        effect = self.trainer_effect(definition) if definition.category == "trainer" else None
        profile = effect.in_play_definition(definition) if isinstance(effect, PlayAsPokemon) else None
        self._profiles[definition] = profile
        return profile

    def evolution_preventers(self, state: GameState) -> tuple[tuple[int, int, str], ...]:
        """v0.47: 今はたらいている、ポケモンを進化できなくする特殊能力（``effects.evolution_preventers``）。``evolution.py`` は ``effects.py`` を読み込まないので、
        登録表を通して聞く。"""
        return evolution_preventers(state)

    def evolution_forbidden(self, state: GameState, target: PokemonInPlay) -> tuple[str, str] | None:
        """v0.49: カードの説明が、場のポケモン ``target`` の進化を禁じているか（``effects.evolution_forbidden``。［へんしん］・「ばける」）。``evolution.py`` から聞く入口。"""
        return evolution_forbidden(state, target)

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


# 2026-10-15 からのカードデータの方針（docs/card-data-policy.md）で、kyuura の印刷の文面を処理に使う文面にした登録の出典（v0.29 から。
# scripts/check_card_sources.py の PRINTED_TEXT_SOURCE と同じ）
# ---------------------------------------------------------------- v0.44（docs/search-evolution-once-attacks-v0.44.md）。場のポケモンを選ぶ・山札をさがす・自分を
# 手札にもどす・山札から進化する・場に出てから 1 回だけ使える・手札と山札とトラッシュのカードを動かすワザと、宣言して使う・場に出たときに使う特殊能力、トレーナー
# 「サカキ」。要素は ``resolution.programs`` の v0.44 の要素と既存の要素。説明の文面は、登録したワザの印刷の文面（kyuura の写し）と完全に同じものだけを受け付ける
# （v0.37 の約束）


STATED_CARDS_SHORT_CODE = "UNRESOLVED_STATED_CARDS_SHORT"
STATED_CARDS_SHORT_REASON = (
    "説明が決まった枚数（「カードを2枚選び」「もどしたのと同じ枚数」）のカードを選ばせるとき、選べるカードがその枚数より少ない場合に、選べるだけ選ぶのか、その内容を"
    "処理しないのか（山札を切るか）は、kyuura の記録・印刷の文面から決められないので扱わない（FC1。p.309 の「処理の対象がなくなってしまっている場合」は対象がない"
    "ときの規定で、足りないときを書かない）"
)


def deck_trainer_cards(state: GameState, player: int) -> list[int]:
    """プレイヤーの山札のトレーナーカード（uid の小さい順。山札の並びを決定に写さない）（v0.44。エリカのフシギダネの「おつかい」）。"""
    return sorted(uid for uid in state.players[player].deck if state.card_def(uid).category == "trainer")


def deck_basic_energy_cards(state: GameState, player: int) -> list[int]:
    """プレイヤーの山札の基本エネルギーカード（どのタイプでも。uid の小さい順）（v0.44。ナツメのバリヤードの「てじな」）。"""
    return sorted(uid for uid in state.players[player].deck if state.card_def(uid).is_basic_energy)


def deck_named_trainer_cards(state: GameState, player: int, name: str) -> list[int]:
    """プレイヤーの山札の、名前が ``name`` と同じトレーナーカード（名前の完全一致。uid の小さい順）（v0.44。サカキのペルシアンの［ボスをよぶ］の「サカキ」。
    「サカキの切り札」などの名前の違うカードは選べない）。"""
    return sorted(uid for uid in state.players[player].deck
                  if state.card_def(uid).category == "trainer" and state.card_def(uid).name_ja == name)


def owner_pokemon(state: GameState, player: int, owner: str) -> list[int]:
    """プレイヤーの場の「(``owner``)のポケモン」（いちばん上のカードの名前が「(``owner``)の」で始まるポケモン。場の並び）の番号（v0.44。トレーナー「サカキ」の
    「サカキのポケモン」。名前の一部（「サカキ」を含む）・カードの弾で判定しない）。"""
    prefix = f"{owner}の"
    return [pokemon.pokemon_id for pokemon in state.players[player].in_play() if form_def(state, pokemon).name_ja.startswith(prefix)]  # v0.49: 今の姿の名前


def self_deck_evolution_cards(state: GameState, player: int, pokemon: PokemonInPlay, *, evolves_from: str | None = None,
                              name: str | None = None) -> list[int]:
    """v0.44: 自分の山札の進化カードのうち、場のポケモン ``pokemon`` に今重ねられるもの（uid の小さい順）。``evolves_from`` なら「○○○○から進化」の名前がそれと
    同じカード（コイキングの「たきのぼりしんか」の「「コイキング」から進化するカード」）、``name`` ならカードの名前がそれと同じカード（キョウのコクーンの［うか］の
    「キョウのスピアー」）だけ。重ねられるかは通常の進化と同じ（``evolution.evolution_block`` の ``from_deck``。おたがいの最初の番・名前・その番の最初から場にいたか・
    段階。p.310。効果による進化だからという理由で制限を免除しない）。トレーナー「サカキ」の許可だけで重ねられる組（GV1）は含めない（``deck_evolution_permission_pairs``
    で呼ぶ側が止める）。対応していないカードは含めない。進化したあとの HP がダメージ以下になるカードは含めたまま（呼ぶ側が選ぶと止める選択にする）。"""
    found = []
    for uid in sorted(state.players[player].deck):
        definition = state.card_def(uid)
        if definition.category != "pokemon" or not definition.is_evolution_pokemon or not definition.supported:
            continue
        if evolves_from is not None and definition.evolves_from != evolves_from:
            continue
        if name is not None and definition.name_ja != name:
            continue
        if evolution_block(state, pokemon, definition, from_deck=True) is None:
            found.append(uid)
    return found


COIN_CHOOSE_OPPONENT_POKEMON_DAMAGE_TEXT = "コインを投げて「おもて」なら、相手の場にいるポケモンから1匹を選び、(「弱点・抵抗力」に関係なく){damage}ダメージ。"
# v0.45: カツラのリザードン（PMCG6-032）の「かえんひこう」の書き方（「相手の場のポケモンを1匹選び、「弱点・抵抗力」に関係なく、」。選ぶのは相手の場のポケモン 1 匹で、
# 弱点・抵抗力を計算しないことは同じ。ダメージの目安の数字はない）
COIN_CHOOSE_OPPONENT_POKEMON_DAMAGE_TEXTS = (COIN_CHOOSE_OPPONENT_POKEMON_DAMAGE_TEXT,
                                             "コインを投げて「おもて」なら、相手の場のポケモンを1匹選び、「弱点・抵抗力」に関係なく、{damage}ダメージ。")


@dataclass(frozen=True)
class CoinChooseOpponentPokemonDamage(AttackEffect):
    """コインを投げて「おもて」なら、相手の場にいるポケモン（バトル場・ベンチのどれでも）から 1 匹を選び、(「弱点・抵抗力」に関係なく) ``damage`` ダメージ（v0.44。
    ロケット団のニャースの「こばんなげ」。kyuura の印刷の文面）。ダメージの目安の数字はない。

    - v0.43 の ``ChooseOpponentPokemonDamage``（わるいゴルバットの「ふらふらとぶ」）と同じ要素 ``programs.ChosenOpponentPokemonDamage`` の、要素のコイン（``local_coin``
      が「おもて」）のある形。コイン → 「おもて」なら決定（``SELECT_POKEMON``。選ぶのはワザを使ったプレイヤー。選べるものは相手の場のポケモン（バトル場 → ベンチ））→
      ダメージ。「うら」なら何もしない（失敗ではない。ワザは使ったことになる）
    - コインはダメージの要素だけを決める。相手に控えがいれば、どの控えも受けるので、コインの前に止めない。相手に控えがなく、相手の対戦ポケモンがダメージの要素を
      無効にする状態（「ダメージを受けない」・「ワザをうけない」）なら、v0.4b の問い（``UNRESOLVED_PREVENTED_COIN_DAMAGE``。v0.33 のつのでつつくと同じ）
    """

    damage: int
    implementation_id = "coin_choose_opponent_pokemon_damage"

    def __post_init__(self) -> None:
        _positive_tens(self.damage, "ダメージ")

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "コインで相手の場のポケモンを選んでダメージを与えるワザ", damage="none") + _check_exact_text(
            attack, "コインで相手の場のポケモンを選んでダメージを与えるワザ", tuple(text.format(damage=self.damage) for text in COIN_CHOOSE_OPPONENT_POKEMON_DAMAGE_TEXTS))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        options = (p.pokemon_id for p in state.players[1 - use.player].in_play())
        return _decision_form(decision, _label(state, use), kind=SELECT_POKEMON, player=use.player, choices=(1, 1), options=options)


@dataclass(frozen=True)
class SearchTrainerOnHeads(AttackEffect):
    """コインを投げて「おもて」なら、自分の山札から「トレーナーカード」1 枚を選び出し、相手に見せてから、手札に加えてよい。その後、その山札をよく切る（v0.44。
    エリカのフシギダネの「おつかい」。kyuura の印刷の文面）。

    - 手札に加えるだけで、そのトレーナーを使うのではない（使うのは、ふつうの規定で手札から。ワザのあとは番が終わる）
    - 選ぶのはワザを使ったプレイヤー（決定 ``SEARCH_DECK``。選べるものは山札のトレーナーカード。uid の小さい順。0〜1 枚（「加えてよい」））。見せて手札に加えるのは
      v0.24 の ``zones.reveal_deck_to_hand``（ログ ``reveal_from_deck`` は公開。ワザの ``effect``。わるいハクリューの［しんかのひかり］と共通）。選べたほかのカードは
      ログに書かない
    - 「おもて」なら、加えても加えなくても・山札にトレーナーカードがなくても、そのあと山札を切る（1 回。説明の「その後、その山札をよく切る」。v0.41 のひなたぼっこと
      同じ読み方）。「うら」なら山札を見ない・切らない
    """

    implementation_id = "search_trainer_on_heads"

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「おもて」なら、自分の山札から「トレーナーカード」1枚を選び出し、相手に見せてから、手札に加えてよい。その後、その山札をよく切る。"
        return _check_form(attack, "山札のトレーナーカードを手札に加えるワザ", damage="none") + _check_exact_text(
            attack, "山札のトレーナーカードを手札に加えるワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        return _decision_form(decision, _label(state, use), kind=SEARCH_DECK, player=use.player, choices=(0, 1),
                              options=deck_trainer_cards(state, use.player))


@dataclass(frozen=True)
class DamageThenReturnSelfToHandOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、自分と自分についているすべてのカードを手札にもどす（v0.44。カスミの
    ヒトデマンの「スターブーメラン」。処理に使う文面は kyuura の最新の説明 LD-PMCG5-027-ATK0。印刷の文面「…このカードと、このカードについている全てのカードを、
    持ち主の手札にもどす。」は照合だけに使う）。

    - 手札にもどすのは v0.42 の ``zones.return_in_play_to_hand``（重なったカード・エネルギー・トレーナーをすべて。ログ ``return_in_play_to_hand``）。持続する効果を
      消す（理由 ``return_in_play_to_hand``）。きぜつではない（サイドは取られない）。空いたバトル場は、ワザのあとの勝ち負けの判定とバトル場に出す決定でうめる
      （控えがいなければ負け。p.311。v0.36 のくもがくれガス・v0.42 のようせいのきせきと同じ）
    - 「こうらがえし」などで返されたダメージは、スターブーメランのダメージを受けた時点で返り、ヒトデマンがそのダメージで HP 以上なら手札にもどらない（kyuura の
      CR-SHELL-ATTACK-STAR-BOOMERANG。CONFIRMED）。そのときコインは投げない（処理の対象がない。p.309）
    - 「ダメージを与えた後」の書き方ではないので、ダメージを与えなかったとき（Z23）の問いはない。同じワザで HP 以上になったポケモン（相手の対戦ポケモン）がいれば、
      バトル場に出す時点ときぜつの処理の順番が決まらない（v0.36 の RD9 と同じ問い。``return_in_play_to_deck_with_knockout``。行き先が手札でも同じ問い）
    """

    implementation_id = "damage_then_return_self_to_hand_on_heads"

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「おもて」なら、このカードと、このカードについている全てのカードを、持ち主の手札にもどす。"
        return _check_form(attack, "コインで自分を手札にもどすワザ", damage="fixed") + _check_exact_text(attack, "コインで自分を手札にもどすワザ", (expected,))


@dataclass(frozen=True)
class EvolveSelfFromDeck(AttackEffect):
    """「(``evolves_from``)」から進化するカードを自分の山札から 1 枚選び出し、このカードにつけてよい。その後、その山札をよく切る（v0.44。ロケット団のコイキングの
    「たきのぼりしんか」。kyuura の印刷の文面）。コインはない。

    - 「このカードにつけて」は、このカード（ワザを使ったポケモン）の上に重ねて進化させること（「「コイキング」から進化するカード」。p.309・p.324 の名前で重ねる規定。
      GR-2000-P309-EVOLUTION-BY-NAME）。重ねられるかは通常の進化と同じ（``self_deck_evolution_cards``。おたがいの最初の番・その番に場に出した・進化したポケモンは
      不可。効果による進化だからという理由で免除しない。v0.42 のつきのちからと同じ）
    - 選ぶのはワザを使ったプレイヤー（決定 ``SEARCH_DECK``。0〜1 枚（「つけてよい」））。進化は通常の進化と同じ手順（``evolution.place_evolution_card``。山札から。
      ログ ``evolve`` の ``effect``・``source_zone``）。選べるものがない・選ばないときも、山札を切る（1 回）。ワザのあと、番は終わる（特殊能力の［うか］と違う）
    - 進化したあとの HP がダメージ以下になるカードは、選べるが選ぶと止める（v0.4a の H1）。場に出たときの特殊能力を持つカード（「場に出た時」）は PW4
    """

    evolves_from: str
    implementation_id = "evolve_self_from_deck"

    def check(self, attack: Attack) -> list[str]:
        expected = f"「{self.evolves_from}」から進化するカードを自分の山札から1枚選び出し、このカードにつけてよい。その後、その山札をよく切る。"
        return _check_form(attack, "山札から自分を進化させるワザ", damage="none") + _check_exact_text(attack, "山札から自分を進化させるワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        _, attacker = state.find_pokemon(use.pokemon_id)
        options = self_deck_evolution_cards(state, use.player, attacker, evolves_from=self.evolves_from)
        return _decision_form(decision, _label(state, use), kind=SEARCH_DECK, player=use.player, choices=(0, 1), options=options)


ONCE_AFTER_ENTRY_NO_DAMAGE_ON_TAILS_TEXTS = (
    # キョウのスピアー（PMCG6-018）の「ひっさつばり」・サカキのコイキング（PMCG6-037）の「りゅうのきおく」
    "このワザは、このカードが場に出てから、1回しか使えない。コインを投げて「うら」なら、ダメージは与えられない。(その場合も、ワザは使ったことになる)",
    # カモネギ（PMCG1-063）の「ネギでたたく」（「場に出してから1度しか使えない」。場に出てからの使用が 1 回、で同じ意味。「うら」でも使ったことは、p.323「12」の
    # 「ワザが失敗した場合でも、そのポケモンは、そのワザを使ったことになります」と同じ）
    "コインを投げて「うら」なら、ダメージをあたえられない。場に出してから1度しか使えない。",
)


@dataclass(frozen=True)
class OnceAfterEntryNoDamageOnTails(AttackEffect):
    """このワザは、このカードが場に出てから 1 回しか使えない。コインを投げて「うら」なら、ダメージは与えられない（その場合も、ワザは使ったことになる）（v0.44。
    キョウのスピアーの「ひっさつばり」・カモネギの「ネギでたたく」・サカキのコイキングの「りゅうのきおく」。kyuura の印刷の文面）。

    - 要素は v0.33 のつのでつつく（``NoDamageOnTails``）と同じ（``Damage`` の ``local_gate``）。「うら」はワザの失敗ではない（ダメージを与えないだけ）
    - 使った記録は場のポケモン（``PokemonInPlay.attacks_used_once``。ワザを持つカードの uid とワザの位置）に持つ（``once_after_entering_play``）。宣言（p.309 の手順 3）
      のときに記録するので、こんらんの「うら」・手順 4 の失敗・コインの「うら」でも使ったことになる（p.323「12」・v0.3d の A12。CONFIRMED）。宣言できない（ねむり・
      マヒ・エネルギー不足・原典で決められない場合で拒否した）ときは記録しない。記録があれば、宣言の確認が ``ATTACK_ALREADY_USED`` で拒否する（エネルギーの確認の前）
    - 場をはなれたら（きぜつ・手札や山札にもどる）記録はなくなる（もう一度場に出たら、場に出てからの 1 回目）。にげる・入れ替え・番の終わりでは消えない（ログから
      数えない）。「自分の番ごとに1回」の特殊能力の記録（``power_uses_this_turn``）とは別
    - 相手のワザとして使う（ゆびをふる・ちょうのうりょく）ときは、記録がワザを持つカードのワザの位置なので、まねたポケモンの記録を表せない（エンジンの未対応。
      ``UNSUPPORTED_COPIED_ATTACK``）
    """

    implementation_id = "once_after_entry_no_damage_on_tails"
    once_after_entering_play: ClassVar[bool] = True

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "場に出てから1回しか使えない、コインの「うら」でダメージを与えられないワザ", damage="fixed") + _check_exact_text(
            attack, "場に出てから1回しか使えない、コインの「うら」でダメージを与えられないワザ", ONCE_AFTER_ENTRY_NO_DAMAGE_ON_TAILS_TEXTS)


@dataclass(frozen=True)
class CoinsAllHeadsSpreadDamageExceptSelf(AttackEffect):
    """コインを ``coins`` 枚投げ、すべて「おもて」なら、場にいる、自分以外のポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ ``damage`` ダメージ（v0.44。
    サカキのギャラドスの「あらしをよぶ」。kyuura の印刷の文面）。ダメージの目安の数字はない。

    - 1 つのワザ全体のコイン（``Coin``。2 枚。「おもて」の数でまとめて先読みする）ですべての要素を決める（要素ごとに投げ直さない）。受けるのは相手の対戦ポケモン
      （p.320 の (1)。プラスパワー・ディフェンダーを計算する）→ 相手の控え全員（(2)）→ 自分の控え全員（(4)）。自分（ワザを使ったポケモン）は受けない
    - 弱点・抵抗力はどれも計算しない（説明の「「弱点・抵抗力」に関係なく」）
    - コインの前の確かめ（v0.34 の ``void_coin_question``・v0.38 の ``has_target``）は既存の要素のまま: 控えのいる側があればコインを投げる
    """

    coins: int
    damage: int
    implementation_id = "coins_all_heads_spread_damage_except_self"

    def __post_init__(self) -> None:
        _positive_tens(self.damage, "ダメージ")
        if type(self.coins) is not int or self.coins < 1:
            raise ValueError(f"コインの枚数は 1 以上（{self.coins!r}）")

    def check(self, attack: Attack) -> list[str]:
        expected = f"コインを{self.coins}枚投げ、すべて「おもて」なら、場にいる、自分以外のポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ{self.damage}ダメージ。"
        return _check_form(attack, "コインで場の自分以外の全員にダメージを与えるワザ", damage="none") + _check_exact_text(
            attack, "コインで場の自分以外の全員にダメージを与えるワザ", (expected,))


@dataclass(frozen=True)
class DamageThenSwitchOpponentIfNotKnockedOut(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。相手が「きぜつ」しなければ、相手の控えポケモンを 1 匹選び、相手と入れ替える（v0.44。サカキの
    ギャラドスの「りゅうのたつまき」。kyuura の印刷の文面）。

    - 選ぶのはワザを使ったプレイヤー（説明に「相手プレイヤーが」がない。v0.31 のかどわかす・v0.21 の突風の GW2 と同じ読み方。要素 ``ForceSwitch`` の
      ``chooser="attacker"``。決定 ``FORCED_SWITCH``）
    - 相手の対戦ポケモンがこのワザのダメージで HP 以上なら入れ替えない（説明の「きぜつしなければ」。v0.4d のふきとばしと同じ ``ForceSwitch`` の処理。ログ
      ``forced_switch_skipped``）。相手に控えがいなければ入れ替えない（p.309。かどわかすと同じ）。相手への効果なので「とうめい」・「ワザをうけない」状態を評価する
    - 「ダメージを受けたとき」の効果（はんげきなど）は、ダメージの要素のあと・入れ替えの前に処理する（p.89。既存の窓）
    """

    implementation_id = "damage_then_switch_opponent_if_not_knocked_out"
    opponent_effect_elements = (FORCED_SWITCH_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        expected = "相手が「きぜつ」しなければ、相手の控えポケモンを1匹選び、相手と入れ替える。"
        return _check_form(attack, "きぜつしなければ相手を控えと入れ替えるワザ", damage="fixed") + _check_exact_text(
            attack, "きぜつしなければ相手を控えと入れ替えるワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        p = state.players[1 - use.player]
        problems = _decision_form(decision, _label(state, use), kind=FORCED_SWITCH, player=use.player, choices=(1, 1),
                                  options=(pokemon.pokemon_id for pokemon in p.bench))
        if p.active is None or p.active.pokemon_id != decision.context_value("target"):
            problems.append(f"入れ替えの対象 {decision.context_value('target')!r} が相手のバトル場のポケモンではない")
        return problems


@dataclass(frozen=True)
class DamageThenPoisonAndParalyzeOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、相手を「どく」と「マヒ」の両方の状態にする（v0.44。キョウのスピアーの
    「しんけいどく」。kyuura の印刷の文面）。

    - 1 枚のワザ全体のコイン（``Coin``）で両方を決める（要素ごとに投げ直さない。「どく」だけ・「マヒ」だけにはならない）。v0.38 の ``DamageThenPoisonOrParalyze``
      （同じコインの「おもて」でどく・「うら」でマヒ）とは別の型（同じ「どく」「マヒ」の語でも意味が違う）
    - どくは重ねてかかり、マヒはねむり・こんらんと置きかわる（p.322。v0.3a の ``SpecialConditions``）。マヒの再付与で回復する番が変わる場合は v0.3b の問い
    - 相手の対戦ポケモンがこのワザのダメージで HP 以上なら、コインを投げない（処理の対象がない。p.309・CR-EFFECTS-AFTER-KO）。「とうめい」で受けないと決まった・
      「ワザをうけない」相手には、効果だけを決めるコインなので T19b・HC3（v0.34 の ``void_coin_question``）
    """

    implementation_id = "damage_then_poison_and_paralyze_on_heads"
    opponent_effect_elements = (POISON, PARALYSIS)

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「おもて」なら、相手を「どく」と「マヒ」の両方の状態にする。"
        return _check_form(attack, "コインでどくとマヒの両方にするワザ", damage="fixed") + _check_exact_text(attack, "コインでどくとマヒの両方にするワザ", (expected,))


@dataclass(frozen=True)
class SpecialPoisonOnHeadsWithoutDamage(AttackEffect):
    """ダメージを与えず、コインを投げて「おもて」なら、相手を「どく」状態にする。このワザによって「どく」状態になったポケモンがポケモンチェックで受ける「どく」の
    ダメージは ``poison_damage``（v0.44。キョウのコクーンの「どくどくえき」。kyuura の印刷の文面）。

    - v0.39 の ``DamageThenSpecialPoisonOnHeads``（どくどくガス。ダメージの目安のあるワザ）と同じ説明の、ダメージの目安のないワザ（v0.37 の約束: ダメージの有無で型を
      分ける）。要素は ``Status(POISON, local_coin=HEADS, poison_damage=...)``（v0.34 の特殊などく。通常のどくを 2 回にしない）。TP3・HC3・T19b はそのまま当てはまる
    """

    poison_damage: int
    implementation_id = "special_poison_on_heads_without_damage"
    opponent_effect_elements = (POISON,)

    def __post_init__(self) -> None:
        _positive_tens(self.poison_damage, "どくのダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = (f"コインを投げて「おもて」なら、相手を「どく」状態にする。このワザによって「どく」状態になったポケモンがポケモンチェックで受ける「どく」の"
                    f"ダメージは、{self.poison_damage}ダメージ。")
        return _check_form(attack, "ダメージを与えずにコインで特殊などくにするワザ", damage="none") + _check_exact_text(
            attack, "ダメージを与えずにコインで特殊などくにするワザ", (expected,))


@dataclass(frozen=True)
class ReturnHandThenRevealBasicEnergy(AttackEffect):
    """自分の手札から最大 ``max_cards`` 枚のカードを選び、山札にもどす。もどしたのと同じ枚数の基本エネルギーカードを山札から選び出し、相手プレイヤーに見せてから、
    手札に加える。その後、その山札をよく切る（v0.44。ナツメのバリヤードの「てじな」。kyuura の印刷の文面）。

    - 段階 1（決定 ``HAND_TO_DECK``。選ぶのはワザを使ったプレイヤー。選べるものは手札のカード（手札の並び）。0〜min(``max_cards``, 手札の枚数)）→ もどす（相手に見せない。
      ``zones.return_hand_cards_to_deck``。ログ ``hand_to_deck`` の ``cards`` は非公開）→ 段階 2（決定 ``SEARCH_DECK``。選べるものは山札の基本エネルギーカード。
      もどしたカードも山札にあるので選べる（v0.24 の PT10 と同じ読み方）。もどした枚数ちょうど）→ 見せて手札に加える（``zones.reveal_deck_to_hand``。公開）→ 山札を
      切る（1 回）。段階 2 の不正な答えで、段階 1 のもどしたカードを取り消さない（決定は待ったまま）
    - 手札がなければ、もどすものも選び出すものもなく、そのあと山札を切る（p.309 の「処理の対象がなくなってしまっている場合」。説明の「その後、その山札をよく切る」は
      別の文）。手札があるとき 0 枚を選べるか（「最大3枚」が 0 枚を含むか）は決められない（v0.39 の GS1 と同じ問い。答えのときに止め、決定は待ったまま）
    - もどした枚数の基本エネルギーカードが山札（もどしたカードを含む）にないとき: 1 枚もなければ選び出す内容の対象がないので、そのあと山札を切る（p.309）。1 枚
      以上あるが足りなければ、選べるだけ選ぶのかは決められない（FC1。その枚数を選ぶ答えで止める。決定は待ったまま）
    """

    max_cards: int
    implementation_id = "return_hand_then_reveal_basic_energy"

    def check(self, attack: Attack) -> list[str]:
        expected = (f"自分の手札から最大{self.max_cards}枚のカードを選び、山札にもどす。もどしたのと同じ枚数の基本エネルギーカードを山札から選び出し、相手プレイヤーに"
                    "見せてから、手札に加える。その後、その山札をよく切る。")
        return _check_form(attack, "手札を山札にもどして基本エネルギーカードを手札に加えるワザ", damage="none") + _check_exact_text(
            attack, "手札を山札にもどして基本エネルギーカードを手札に加えるワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        label = _label(state, use)
        hand = state.players[use.player].hand
        if decision.kind == HAND_TO_DECK:
            return _decision_form(decision, label, kind=HAND_TO_DECK, player=use.player, choices=(0, min(self.max_cards, len(hand))), options=hand)
        count = decision.context_value("count")
        if type(count) is not int or not 1 <= count <= self.max_cards:
            return [f"「{label}」の段階 2 の枚数 {count!r} が 1〜{self.max_cards} ではない"]
        return _decision_form(decision, label, kind=SEARCH_DECK, player=use.player, choices=(count, count),
                              options=deck_basic_energy_cards(state, use.player))


@dataclass(frozen=True)
class CoinPutOpponentDiscardOnDeckTop(AttackEffect):
    """コインを投げて「おもて」なら、相手のトラッシュからカードを 1 枚選び出し、相手の山札の上にのせる（v0.44。カツラのマンキーの「わるいいたずら」。kyuura の印刷の
    文面）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``DISCARD_TO_DECK_TOP``。選べるものは相手のトラッシュのカード（どの種類でも。トラッシュの並び）。1 枚）。のせる先は相手の
      山札の一番上（``zones.put_discard_on_deck_top``。ログ ``put_discard_on_deck_top`` は公開）。説明にないので山札を切らない
    - 相手のトラッシュにカードがなければ、処理の対象がないのでコインを投げない（p.309。v0.31 のスーパーデストロイ・v0.38 の ``has_target`` と同じ読み方）
    - 相手のトラッシュ・山札への効果で、相手のポケモンへの効果ではないので、「ワザをうけない」状態・「とうめい」は関係しない（コインの前に止めない）
    """

    implementation_id = "coin_put_opponent_discard_on_deck_top"

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「おもて」なら、相手のトラッシュからカードを1枚選び出し、相手の山札の上にのせる。"
        return _check_form(attack, "相手のトラッシュのカードを相手の山札の上にのせるワザ", damage="none") + _check_exact_text(
            attack, "相手のトラッシュのカードを相手の山札の上にのせるワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        return _decision_form(decision, _label(state, use), kind=DISCARD_TO_DECK_TOP, player=use.player, choices=(1, 1),
                              options=state.players[1 - use.player].discard)


@dataclass(frozen=True)
class CoinDrawOrReturnHandToDeck(AttackEffect):
    """コインを投げて「おもて」なら、山札からカードを ``draw`` 枚引く。「うら」なら、自分の手札からカードを ``count`` 枚選び、山札にもどして、よく切る（v0.44。
    _____のラッキーの「ラッキーたまご」。kyuura の印刷の文面。名前は kyuura の名前のまま）。

    - 1 枚のワザ全体のコイン（``Coin``）で決める。自分への効果なので、相手の状態によらず投げる
    - 「おもて」: 山札の上から引く（山札が足りなければ引けるだけ。p.312。v0.31 の ``Draw``）。山札は切らない
    - 「うら」: 選ぶのはワザを使ったプレイヤー（決定 ``HAND_TO_DECK``。手札のカード（手札の並び）からちょうど ``count`` 枚）→ もどす（相手に見せない。
      ``zones.return_hand_cards_to_deck``）→ 山札を切る（1 回）。手札が ``count`` 枚より少ない（0 枚を含む）ときに、あるだけもどすのか、もどさないのか（そのとき切るか）は
      決められない（FC1。手札にあるカードが説明の枚数に足りない。0 枚でも「もどして、よく切る」が 1 つの内容か決まらない）ので、コインの前に止める（先読みが「うら」で見つける）
    """

    draw: int
    count: int
    implementation_id = "coin_draw_or_return_hand_to_deck"

    def check(self, attack: Attack) -> list[str]:
        expected = (f"コインを投げて「おもて」なら、山札からカードを{self.draw}枚引く。「うら」なら、自分の手札からカードを{self.count}枚選び、山札にもどして、"
                    "よく切る。")
        return _check_form(attack, "コインで引くか手札を山札にもどすワザ", damage="none") + _check_exact_text(attack, "コインで引くか手札を山札にもどすワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        return _decision_form(decision, _label(state, use), kind=HAND_TO_DECK, player=use.player, choices=(self.count, self.count),
                              options=state.players[use.player].hand)


# ---------------------------------------------------------------- v0.45（docs/conditional-damage-energy-v0.45.md）。条件・コイン・特殊状態・エネルギーの処理・
# ダメージの計算・返す効果・山札のワザ。要素は ``resolution.programs`` の v0.45 の要素と既存の要素。説明の文面は、登録したワザの印刷の文面（kyuura の写し）と完全に同じもの
# だけを受け付ける（v0.37 の約束）


_CONDITION_JA = {SLEEP: "ねむり", POISON: "どく", PARALYSIS: "マヒ", CONFUSION: "こんらん"}


@dataclass(frozen=True)
class DamageFailUnlessOpponentStatus(AttackEffect):
    """相手が ``condition`` の状態でないとき、このワザは失敗する（v0.45。第1弾のゴーストの「ゆめくい」。処理に使う文面は kyuura の最新の説明 LD-PMCG1-047-ATK1
    「相手が「ねむり」状態でないとき、このワザは失敗する。」。印刷の文面は「相手が「ねむり」状態のときだけ、ダメージをあたえる。」（照合だけに使う））。

    - 最新の説明のとおり、ワザの失敗（p.323「12 ワザの失敗」: ワザは使ったことになり、番は終わる。ログ ``attack_failed`` の ``reason`` は ``condition``）。ワザを
      使えない（宣言の拒否）・ダメージが 0 になる、とは扱わない（印刷の文面の「ダメージをあたえる」条件にしたがわない）
    - 確かめるのはワザの内容を処理するとき（p.309 の手順 6。こんらんのコインのあと。要素 ``programs.FailUnlessOpponentStatus``）の相手の対戦ポケモンの状態。相手への
      効果ではないので、「ワザをうけない」状態・「とうめい」は評価しない（受けないのはダメージの要素で、``Damage`` が評価する）
    """

    condition: str
    implementation_id = "damage_fail_unless_opponent_status"

    def check(self, attack: Attack) -> list[str]:
        expected = f"相手が「{_CONDITION_JA[self.condition]}」状態のときだけ、ダメージをあたえる。"
        return _check_form(attack, "相手の状態でワザが失敗するワザ", damage="fixed") + _check_exact_text(attack, "相手の状態でワザが失敗するワザ", (expected,))


LASTING_ATTACK_COIN_CHECK_TEXT = ("コインを投げて「おもて」なら、このワザを受けた相手は、それ以後ワザを使うたびにコインを投げ、「うら」ならワザは失敗する。"
                                  "バトル場をはなれたポケモンからは、このワザの効果は消える。")


@dataclass(frozen=True)
class DamageThenLastingAttackCoinCheckOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、このワザを受けた相手は、それ以後ワザを使うたびにコインを投げ、「うら」なら
    ワザは失敗する。バトル場をはなれたポケモンからは、このワザの効果は消える（v0.45。カスミのタッツー（PMCG5-024）の「スミをかける」。kyuura の印刷の文面）。

    - 効果を与えるコイン（このワザの中。要素 ``OpponentAttackCheck`` の ``local_coin``）と、効果を受けたポケモンがワザを使うときのコイン（p.309 の手順 4。v0.36 の
      ``flow._attack_check_failed``）は別のコイン。効果を与えるコインは効果だけを決めるので、「とうめい」で受けないと決まった・「ワザをうけない」相手には T19b・HC3。
      相手がこのワザで HP 以上なら投げない（p.309）
    - 持続する効果は v0.36 の ``AttackCoinCheck`` に「それ以後」（``lasting``）を明示した値: はたらく番（次の相手の番）から期限なしにはたらき、バトル場をはなれる
      （ベンチにもどる・きぜつ・山札や手札にもどる）・進化すると消える（p.322・p.323）。「次の相手の番」の効果（えんまくなど）の期限は変えない
    - 受けたポケモンがもう 1 つの手順 4 の効果を受けた状態でワザを使うときは AC13（``UNRESOLVED_MULTIPLE_ATTACK_CHECKS``。コインの前に止める）
    """

    implementation_id = "damage_then_lasting_attack_coin_check_on_heads"
    opponent_effect_elements = (ATTACK_CHECK_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "それ以後ワザを使うたびにコインを投げさせるワザ", damage="fixed") + _check_exact_text(
            attack, "それ以後ワザを使うたびにコインを投げさせるワザ", (LASTING_ATTACK_COIN_CHECK_TEXT,))

    def attack_check_terms(self) -> tuple[type, bool, bool]:
        from .state import AttackCoinCheck

        return AttackCoinCheck, False, True


@dataclass(frozen=True)
class DamageMultipliedAgainstType(AttackEffect):
    """このワザを受ける相手が ``pokemon_type`` のポケモンなら、このワザのダメージは ``factor`` 倍になる（v0.45。カスミのジュゴン（PMCG5-031）の「こおりのつぶて」。
    kyuura の印刷の文面）。

    - ワザの説明の計算なので、p.321 の 1 段階（基本となるダメージ。「ワザの説明にしたがう」）でダメージの目安の数字を ``factor`` 倍にする（v0.40 の「ラブラリアット」の
      「「100」になる」と同じ段階）。弱点・抵抗力・プラスパワー・ディフェンダーなどはそのあとの段階で計算する（最終ダメージを 2 倍にしない）
    - 「「闘」ポケモン」は、ダメージの要素を処理する時点の相手の対戦ポケモンのいちばん上のカードのタイプ（p.311 の「色（タイプ）」）
    """

    pokemon_type: EnergyType
    factor: int
    implementation_id = "damage_multiplied_against_type"

    def check(self, attack: Attack) -> list[str]:
        expected = f"このワザを受ける相手が「{self.pokemon_type.ja}」ポケモンなら、このワザのダメージは{self.factor}倍になる。"
        return _check_form(attack, "相手のタイプでダメージが変わるワザ", damage="fixed") + _check_exact_text(attack, "相手のタイプでダメージが変わるワザ", (expected,))


@dataclass(frozen=True)
class DamageThenPoisonAndConfuseOnAllHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを ``coins`` 枚投げ、すべて「おもて」なら、相手を「どく」と「こんらん」の両方の状態にする（v0.45。
    キョウのアーボ（PMCG6-002）の「とつぜんどく」。kyuura の印刷の文面）。

    - ``coins`` 枚のワザ全体のコイン（``Coin``）1 組で両方を決める（要素ごとに投げ直さない。「おもて」の数がちょうど ``coins`` のときだけ両方）。v0.44 の「しんけいどく」
      （1 枚・どくとマヒ）と同じ形
    - 相手がこのワザのダメージで HP 以上なら投げない（p.309）。「とうめい」で受けないと決まった・「ワザをうけない」相手には T19b・HC3（v0.34 の ``void_coin_question``）
    """

    coins: int
    implementation_id = "damage_then_poison_and_confuse_on_all_heads"
    opponent_effect_elements = (POISON, CONFUSION)

    def check(self, attack: Attack) -> list[str]:
        expected = f"コインを{self.coins}枚投げ、すべて「おもて」なら、相手を「どく」と「こんらん」の両方の状態にする。"
        return _check_form(attack, "コインがすべて「おもて」ならどくとこんらんにするワザ", damage="fixed") + _check_exact_text(
            attack, "コインがすべて「おもて」ならどくとこんらんにするワザ", (expected,))


@dataclass(frozen=True)
class SelfStatusWithoutDamage(AttackEffect):
    """ダメージを与えず、自分（ワザを使ったポケモン）を ``condition`` の状態にする（v0.45。キョウのアーボック（PMCG6-019）の「どくをためる」の「自分を「どく」状態に
    する。」。kyuura の印刷の文面）。

    - 要素は ``Status(condition, target=SELF)``（v0.17b の「たおれこむ」の自分のねむりと同じ。自分への効果も「とうめい」を評価する）。どくは通常のどく（10）
    - コインはない。ワザを使ったポケモンがすでにどく状態なら、二重にならない（p.322。``conditions.poison``）。特殊などくのポケモンは通常のどくになる（v0.3a の 14）
    """

    condition: str
    implementation_id = "self_status_without_damage"

    def check(self, attack: Attack) -> list[str]:
        expected = f"自分を「{_CONDITION_JA[self.condition]}」状態にする。"
        return _check_form(attack, "自分を特殊状態にするワザ", damage="none") + _check_exact_text(attack, "自分を特殊状態にするワザ", (expected,))


@dataclass(frozen=True)
class DamageIfSelfStatusThenOpponentStatus(AttackEffect):
    """自分が ``condition`` の状態なら、このワザのダメージは「``amount``」になる。その場合、相手を ``condition`` の状態にする（v0.45。キョウのアーボック（PMCG6-019）の
    「ポイズンパワー」。kyuura の印刷の文面）。

    - 条件（自分がどく状態か）は、ワザの内容を処理するときに 1 回だけ確かめ（要素 ``SelfStatusCheck``。p.309 の手順 6。こんらんのコインのあと）、ダメージと相手への効果で
      同じ結果を使う（ダメージの要素のあとに相手の「はんげき」などで自分の状態が変わっても、確かめ直さない）
    - 「どく」状態は通常のどくと特殊などく（v0.34。``Poison.damage``）のどちらでも（どちらもどく状態。p.322）。相手に与えるのは通常のどく（10）
    - 「「40」になる」はワザの説明の計算（p.321 の 1 段階。v0.40 の「ラブラリアット」と同じ）。条件が満たされなければダメージの目安の数字（20）。弱点・抵抗力などは
      そのあとの段階で計算する
    - 「その場合、相手を「どく」状態にする」は相手への効果（「ワザをうけない」状態・「とうめい」を評価する。相手がこのワザで HP 以上なら与えない。p.309）
    """

    condition: str
    amount: int
    implementation_id = "damage_if_self_status_then_opponent_status"

    def __post_init__(self) -> None:
        _positive_tens(self.amount, "条件を満たすときのダメージ")

    @property
    def opponent_effect_elements(self) -> tuple[str, ...]:  # type: ignore[override]
        return (self.condition,)

    def check(self, attack: Attack) -> list[str]:
        c = _CONDITION_JA[self.condition]
        expected = f"自分が「{c}」状態なら、このワザのダメージは「{self.amount}」になる。その場合、相手を「{c}」状態にする。"
        return _check_form(attack, "自分の状態でダメージと効果が変わるワザ", damage="fixed") + _check_exact_text(attack, "自分の状態でダメージと効果が変わるワザ", (expected,))


@dataclass(frozen=True)
class CoinSwitchOpponentThenStatus(AttackEffect):
    """ダメージを与えず、コインを投げて「おもて」なら、相手の控えポケモンを 1 匹選び、相手と入れ替える。その後、新しい相手の対戦ポケモンを ``condition`` の状態にする
    （v0.45。キョウのベトベター（PMCG6-007）の「ベトベトハンド」。kyuura の印刷の文面）。

    - 1 枚のコイン（入れ替えの要素 ``ForceSwitch`` の ``local_coin``）で、入れ替えと新しい対戦ポケモンへの効果の両方を決める（決定のあとで投げ直さない）。選ぶのはワザを
      使ったプレイヤー（決定 ``FORCED_SWITCH``。v0.31 の「かどわかす」と同じ）
    - 入れ替えたときだけ、新しい対戦ポケモン（入れ替えで出た控えポケモン）を ``condition`` の状態にする（要素 ``Status`` の ``after_switch``）。入れ替える前の対戦
      ポケモンを特殊状態にしない。相手に控えがいないなら入れ替えの対象がないので、コインを投げず、特殊状態にもしない（p.309。v0.38 の ``has_target``）
    - 入れ替えは入れ替える前の対戦ポケモンへの効果、特殊状態は新しい対戦ポケモンへの効果で、それぞれ「ワザをうけない」状態・「とうめい」を評価する（2 匹の「とうめい」は
      T27）
    """

    condition: str
    implementation_id = "coin_switch_opponent_then_status"

    @property
    def opponent_effect_elements(self) -> tuple[str, ...]:  # type: ignore[override]
        return (FORCED_SWITCH_ELEMENT, self.condition)

    def check(self, attack: Attack) -> list[str]:
        expected = (f"コインを投げて「おもて」なら、相手の控えポケモンを1匹選び、相手と入れ替える。その後、新しい相手の対戦ポケモンを「{_CONDITION_JA[self.condition]}」"
                    "状態にする。")
        return _check_form(attack, "コインで入れ替えて新しい対戦ポケモンを特殊状態にするワザ", damage="none") + _check_exact_text(
            attack, "コインで入れ替えて新しい対戦ポケモンを特殊状態にするワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        return _decision_form(decision, _label(state, use), kind=FORCED_SWITCH, player=use.player, choices=(1, 1),
                              options=(p.pokemon_id for p in state.players[1 - use.player].bench))


@dataclass(frozen=True)
class DamageAndSelfDamageThenPreventDamageOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。このカードにも ``self_damage`` ダメージ。コインを投げて「おもて」なら、このカードは次の相手の番に
    ダメージを受けない（ダメージ以外の効果は受ける）（v0.45。わるいカメックス（PMCG4-024）の「ロケットタックル」。kyuura の印刷の文面）。

    - 順番は説明のとおり: 相手へのダメージ → 自分へのダメージ →（「ダメージを受けたとき」の効果）→ コイン → 持続する効果 ``PreventDamage``（v0.4b の「かたまる」と同じ
      「ダメージを受けない」状態。ダメージ以外の効果は受ける）
    - このカードが自分へのダメージや相手の「はんげき」などで HP 以上なら、効果の対象がないのでコインを投げない（p.309。要素 ``SelfPersistent``）
    """

    self_damage: int
    implementation_id = "damage_and_self_damage_then_prevent_damage_on_heads"

    def __post_init__(self) -> None:
        _positive_tens(self.self_damage, "自分へのダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = (f"このカードにも{self.self_damage}ダメージ。コインを投げて「おもて」なら、このカードは次の相手の番にダメージを受けない。"
                    "(ダメージ以外の効果は受ける)")
        return _check_form(attack, "自分へのダメージとコインでダメージを受けない状態になるワザ", damage="fixed") + _check_exact_text(
            attack, "自分へのダメージとコインでダメージを受けない状態になるワザ", (expected,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        return DamageProfile(opponent=super().damage_profile(state, use).opponent, self_damage=(self.self_damage,))


MOVE_OPPONENT_ENERGY_TEXT = ("相手の対戦ポケモンのエネルギーカード(特殊エネルギーカード以外)を1枚選んではがす。その後、相手の控えポケモンを1匹選び、はがしたエネルギーを"
                             "そのポケモンにつける。(相手に控えがいない時、この効果はない)")


def opponent_active_basic_energy(state: GameState, player: int) -> list[int]:
    """プレイヤー ``player`` の相手の対戦ポケモンについている基本エネルギーカード（ついている順）（v0.45。「じりょくせん」の「エネルギーカード(特殊エネルギーカード
    以外)」）。"""
    target = state.players[1 - player].active
    return [] if target is None else [uid for uid in target.energy if state.card_def(uid).is_basic_energy]


@dataclass(frozen=True)
class DamageThenMoveOpponentEnergyToBench(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。相手の対戦ポケモンのエネルギーカード（特殊エネルギーカード以外）を 1 枚選んではがす。その後、相手の控え
    ポケモンを 1 匹選び、はがしたエネルギーをそのポケモンにつける。相手に控えがいない時、この効果はない（v0.45。わるいレアコイル（PMCG4-030）の「じりょくせん」。kyuura の
    印刷の文面）。

    - 選ぶのはワザを使ったプレイヤー: はがすカード（決定 ``MOVE_OPPONENT_ENERGY``。相手の対戦ポケモンの基本エネルギーカード。1 枚でも決定を出す）→ つける控えポケモン
      （決定 ``SELECT_POKEMON``。相手のベンチ）。要素 ``programs.MoveOpponentEnergyToBench``
    - カードの持ち主は相手のまま（同じ uid のカードを相手の対戦ポケモンから相手の控えポケモンへ動かす。トラッシュ・手札を通らない）。ログ ``move_opponent_energy``
    - 効果がない・処理の対象がない場合は何もしない（はがさない）: 相手に控えがいない（説明）・基本エネルギーカードがついていない・相手の対戦ポケモンがこのワザのダメージで
      HP 以上（p.309）
    - はがすのは相手の対戦ポケモンへの効果、つけるのは選んだ控えポケモンへの効果で、それぞれ「ワザをうけない」状態・「とうめい」を評価する。つける控えポケモンの「とうめい」が
      「おもて」なら、はがしたカードはトラッシュ（持ち主のトラッシュ）する（kyuura の CR-TRANSPARENCY-ENERGY-BOMB（わるいマルマインの「エナジーボム」。確実）と同じ
      読み方。v0.31 の ``MoveOwnEnergyToBench`` と同じ処理）
    """

    implementation_id = "damage_then_move_opponent_energy_to_bench"
    opponent_effect_elements = (ENERGY_MOVE_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "相手のエネルギーを相手の控えにつけかえるワザ", damage="fixed") + _check_exact_text(
            attack, "相手のエネルギーを相手の控えにつけかえるワザ", (MOVE_OPPONENT_ENERGY_TEXT,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        label = _label(state, use)
        if decision.kind == MOVE_OPPONENT_ENERGY:
            return _decision_form(decision, label, kind=MOVE_OPPONENT_ENERGY, player=use.player, choices=(1, 1),
                                  options=opponent_active_basic_energy(state, use.player))
        return _decision_form(decision, label, kind=SELECT_POKEMON, player=use.player, choices=(1, 1),
                              options=(p.pokemon_id for p in state.players[1 - use.player].bench))


@dataclass(frozen=True)
class DiscardExcessEnergyForDamage(AttackEffect):
    """このワザに必要なエネルギーよりも多く ``energy_type`` のエネルギーがついている時、多い ``energy_type`` のエネルギーをすべてトラッシュして、トラッシュした
    エネルギーの数 × ``per_energy`` のダメージを追加する（v0.45。カツラのリザードン（PMCG6-032）の「ファイヤーブレス」。kyuura の印刷の文面）。

    - 多いエネルギーの数は、ついている ``energy_type`` の基本エネルギーカードの枚数（1 枚 1 個）から、ワザに必要なエネルギーの数を引いたもの（0 より少なければ 0）。必要な
      エネルギーがすべて ``energy_type`` のワザだけを登録できる（v0.6 の ``ExtraEnergyDamage`` と同じ。無色が混ざると数え方が変わる。HC4）
    - トラッシュはワザの効果（kyuura の RUL-ENERGY-DISCARD-ATTACKS「炎エネルギーカードをトラッシュするタイプのワザ（「かえんほうしゃ」など）は、すべて同じ処理になります」の
      範囲。宣言のあと・こんらんのコインのあと。こんらんの「うら」ならトラッシュしない）。数えてからトラッシュし、トラッシュした枚数でダメージを決める（要素の順番:
      ``DiscardOwnEnergy`` の ``excess_over_cost`` → ``Damage`` の ``PlusPerDiscarded``）
    - どのカードをトラッシュするかはワザを使ったプレイヤーが選ぶ（決定 ``DISCARD_ENERGY``。多い枚数ちょうど。1 枚でも決定を出す。v0.7 の K2 と同じ）。多いエネルギーが
      なければトラッシュせず、決定も出さない（ダメージはダメージの目安の数字）
    - 追加のダメージはワザの説明の計算（p.321 の 1 段階）。弱点・抵抗力などはそのあとの段階
    """

    energy_type: EnergyType
    per_energy: int
    implementation_id = "discard_excess_energy_for_damage"

    def __post_init__(self) -> None:
        _positive_tens(self.per_energy, "エネルギー 1 個あたりの追加のダメージ")

    def check(self, attack: Attack) -> list[str]:
        t = self.energy_type.ja
        expected = (f"このワザに必要なエネルギーよりも多く「{t}」エネルギーがついている時、多い「{t}」エネルギーをすべてトラッシュして、トラッシュしたエネルギーの数×"
                    f"{self.per_energy}のダメージを追加する。")
        problems = _check_form(attack, "多いエネルギーをトラッシュしてダメージを追加するワザ", damage="modified", modifier="+") + _check_exact_text(
            attack, "多いエネルギーをトラッシュしてダメージを追加するワザ", (expected,))
        if not attack.cost or any(cost is not self.energy_type for cost in attack.cost):
            problems.append(f"必要なエネルギーが「{t}」だけではないワザを登録している（多いエネルギーの数え方が決まらない）")
        return problems

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = attack_of(state, use.key)  # v0.49: ワザを印刷したカード（use.key）
        excess = max(0, len(attached_basic_energy(state, attacker, self.energy_type)) - len(attack.cost))
        return DamageProfile(opponent=(attack.damage + excess * self.per_energy,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = attack_of(state, use.key)  # v0.49: ワザを印刷したカード（use.key）
        candidates = attached_basic_energy(state, attacker, self.energy_type)
        excess = len(candidates) - len(attack.cost)
        return _decision_form(decision, _label(state, use), kind=DISCARD_ENERGY, player=use.player, choices=(excess, excess), options=candidates)


@dataclass(frozen=True)
class DamageThenAttachEnergyFromDiscardToSelf(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。自分のトラッシュに ``energy_type`` のエネルギーカードがあれば、1 枚取り出して、自分につける（v0.45。
    R団のサンダー（PMCG6-042）の「プラズマ」。kyuura の印刷の文面）。

    - 要素は ``Damage`` → v0.31 の ``AttachFromDiscard``（「たいでん」）の、ちょうど 1 枚（``exact``）の形。選ぶのはワザを使ったプレイヤー（決定 ``ATTACH_FROM_DISCARD``。
      1 枚でも決定を出す）。トラッシュになければ何もしない（「あれば」）
    - つけるのは手札からつける通常の操作ではない（``energy_attachments_this_turn``・特殊能力でつけた枚数に数えない）。つけたら、つけたときの特殊能力をはたらかせる
      （``effects.after_energy_attached``）
    - このカードが相手の「はんげき」などで HP 以上なら、処理の対象がないのでつけない（p.309）
    """

    energy_type: EnergyType
    implementation_id = "damage_then_attach_energy_from_discard_to_self"

    def check(self, attack: Attack) -> list[str]:
        expected = f"自分のトラッシュに「{self.energy_type.ja}」エネルギーカードがあれば、1枚取り出して、自分につける。"
        return _check_form(attack, "トラッシュのエネルギーカードを自分につけるワザ", damage="fixed") + _check_exact_text(
            attack, "トラッシュのエネルギーカードを自分につけるワザ", (expected,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        options = [uid for uid in state.players[use.player].discard
                   if state.card_def(uid).is_basic_energy and state.card_def(uid).provides is self.energy_type]
        return _decision_form(decision, _label(state, use), kind=ATTACH_FROM_DISCARD, player=use.player, choices=(1, 1), options=options)


@dataclass(frozen=True)
class DamageAndSelfDamagePerAttachedEnergyCard(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。自分にも、自分についている ``energy_type`` のエネルギーカードの数 × ``per_card`` のダメージ（v0.45。
    R団のサンダー（PMCG6-042）の「エレクトロバーン」。kyuura の印刷の文面）。

    - 数えるのはエネルギーカードの枚数（``energy_type`` の基本エネルギーカード。エネルギーの数（``state.energy_types``）ではない。v0.31 のエナジーバーンで「炎」として数える
      状態はリザードン自身のもので、このカードには関係しない）。数えるのは自分へのダメージの要素を処理する時点
    - 自分へのダメージはワザによる自分へのダメージ（p.321 の計算。弱点・抵抗力は自分のタイプと自分の弱点・抵抗力。v0.3d）。0 枚なら 0 で、ダメージを与えない
    """

    energy_type: EnergyType
    per_card: int
    implementation_id = "damage_and_self_damage_per_attached_energy_card"

    def __post_init__(self) -> None:
        _positive_tens(self.per_card, "エネルギーカード 1 枚あたりの自分へのダメージ")

    def check(self, attack: Attack) -> list[str]:
        expected = f"自分にも、自分についている「{self.energy_type.ja}」エネルギーカードの数×{self.per_card}のダメージ。"
        return _check_form(attack, "ついているエネルギーカードの数の自分へのダメージのあるワザ", damage="fixed") + _check_exact_text(
            attack, "ついているエネルギーカードの数の自分へのダメージのあるワザ", (expected,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        _, attacker = state.find_pokemon(use.pokemon_id)
        own = len(attached_basic_energy(state, attacker, self.energy_type)) * self.per_card
        return DamageProfile(opponent=super().damage_profile(state, use).opponent, self_damage=(own,))


@dataclass(frozen=True)
class ZeroDamageBelowNextTurn(AttackEffect):
    """次の相手の番に受けるダメージが 0 になる。ただしダメージが ``threshold`` 以上の場合は、そのままダメージをうける（v0.45。イワーク（PMCG1-054）の「かたくなる」。
    kyuura の印刷の文面）。

    - 自分自身に与える持続する効果 ``state.ZeroDamageBelow``（はたらく番は次の相手の番）。はたらく番に受けるワザのダメージの p.321 の 8 段階（「ワザを受けるポケモンの
      持っている「ダメージを変更する効果」」。GR-2000-P321-DAMAGE-ORDER の 8 段階の例が「かたくなる」）で、その段階のダメージが ``threshold`` より小さければ 0、
      ``threshold`` 以上ならそのまま（``damage.ZERO_IF_BELOW``）。計算の結果が 0 なら「ダメージを受けなかった」（p.321）だけで、ダメージ以外の効果は受ける
    - v0.4b の「ダメージを受けない」状態（``PreventDamage``。ダメージの要素が計算の前に無効。ダメージの量によらない）とは別の効果（量で決まり、8 段階で計算する）
    """

    threshold: int
    implementation_id = "zero_damage_below_next_turn"

    def __post_init__(self) -> None:
        _positive_tens(self.threshold, "ダメージを 0 にするしきい値")

    def check(self, attack: Attack) -> list[str]:
        expected = f"次の相手の番に受けるダメージが0になる。ただしダメージが{self.threshold}以上の場合は、そのままダメージをうける。"
        return _check_form(attack, "次の相手の番に小さいダメージを受けないワザ", damage="none") + _check_exact_text(attack, "次の相手の番に小さいダメージを受けないワザ", (expected,))

    def threshold_terms(self) -> tuple[type, int]:
        from .state import ZeroDamageBelow

        return ZeroDamageBelow, self.threshold


HALF_REMAINING_HP_TEXT = "相手の残りのHPの半分(切り上げ)のダメージをあたえる。"


@dataclass(frozen=True)
class HalfRemainingHpDamage(AttackEffect):
    """相手の残りの HP の半分（切り上げ）のダメージをあたえる（v0.45。ラッタ（PMCG1-062）の「いかりのまえば」。kyuura の印刷の文面。ダメージの目安は「?」）。

    - 残りの HP は、ダメージの要素を処理する時点の相手の対戦ポケモンの HP（いちばん上のカード）− のっているダメージ。半分の切り上げはダメージカウンターの単位（10）で
      数える（残りの HP のカウンターの数の半分を切り上げて × 10。v0.4d のメガドレインの「半分（切り上げ）」と同じ単位）
    - これはワザの説明の計算（p.321 の 1 段階。基本となるダメージ）で、弱点・抵抗力・プラスパワー・ディフェンダーなどはそのあとの段階で計算する（ダメージカウンターを直接
      のせない。ダメージの要素）
    """

    implementation_id = "half_remaining_hp_damage"

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage is not None or attack.damage_modifier != "?":
            problems.append("ダメージの目安が「?」でないワザを、相手の残りの HP の半分のダメージのワザとして登録している")
        return problems + _check_exact_text(attack, "相手の残りの HP の半分のダメージのワザ", (HALF_REMAINING_HP_TEXT,))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        return DamageProfile(opponent=(half_remaining_hp(state, state.players[1 - use.player].active),))


def half_remaining_hp(state: GameState, pokemon: PokemonInPlay) -> int:
    """場のポケモンの残りの HP の半分（ダメージカウンターの単位で切り上げ）（v0.45。「いかりのまえば」）。"""
    per = state.rules.damage_per_counter
    remaining = max_hp(state, pokemon) - pokemon.damage  # v0.48: 今有効な最大HPから残りの HP を求める
    if remaining <= 0 or remaining % per:
        raise RuntimeError(f"ポケモン {pokemon.pokemon_id} の残りの HP {remaining} が、ダメージカウンターの単位の正の倍数ではない（エンジンの不具合）")
    return (remaining // per + 1) // 2 * per


CROSS_COUNTER_TEXT = ("次の相手の番、このカードが相手のワザによるダメージを受けた時、(このカードが「きぜつ」するしないにかかわらず、)コインを投げる。「おもて」なら、"
                      "相手に、このカードが受けた{multiplier}倍のダメージを与える。")


@dataclass(frozen=True)
class ReturnReceivedDamageOnHeads(AttackEffect):
    """次の相手の番、このカードが相手のワザによるダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）コインを投げる。「おもて」なら、このカードが受けた
    ダメージの ``multiplier`` 倍のダメージを、相手に与える（v0.45。R団のエビワラー（PMCG5-054）の「クロスカウンター」。処理に使う文面は kyuura の最新の説明
    LD-PMCG5-054-ATK0。印刷の文面は照合だけに使う）。

    - v0.13 の「こうらがえし」（``ReturnReceivedDamage``。p.89 の「同じタイプのワザ」が「クロスカウンター」）と同じ持続する効果 ``Retaliation``（受けたダメージで決まる
      ``RETALIATION_RECEIVED``）に、倍数（``multiplier``）と、はたらくときのコイン（``on_heads``）を明示した値（種類 ``retaliation_received_damage_scaled``）
    - コインは効果を与えるとき（このワザの中）ではなく、効果がはたらくとき（相手のワザのダメージの処理のあと・ダメージ以外の効果の前。CR-SHELL-ATTACK-TIMING と同じ時点。
      ``kernel.attack_damage_to_damage_source``）に、効果を持つポケモンの持ち主が投げる。このカードがそのダメージできぜつしても投げる（説明・p.203 の解説）。ダメージを
      与えたポケモンがすでに HP 以上なら、処理の対象がないので投げない（C15・W23・v0.38 の ``has_target``）
    - 与えるダメージは「クロスカウンター」のワザによるダメージ（p.321「8」）で、基本となるダメージは受けた最終ダメージ（CR-SHELL-ATTACK-ATTACKER-PLUSPOWER。HP で上限を
      つけない）の ``multiplier`` 倍（p.321 の 1 段階）。弱点・抵抗力・ディフェンダー・「とうめい」・受けたポケモンの「はんげき」はそのあとで計算・評価する（v0.13 の
      S20〜S25 と同じ）
    - そろってのきぜつ（W24・S37）は既存の ``UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT``（コインの「おもて」がありうるので、「おもて」の場合を数える）
    - 相手のワザとして使うのはエンジンの未対応（v0.31 の ``SelfRetaliation.copy_problem``。``UNSUPPORTED_COPIED_ATTACK``）
    """

    multiplier: int
    implementation_id = "return_received_damage_on_heads"

    def __post_init__(self) -> None:
        if type(self.multiplier) is not int or self.multiplier < 2:
            raise ValueError(f"受けたダメージにかける数は 2 以上の整数（{self.multiplier!r}）")

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "受けたダメージの倍をコインで返すワザ", damage="none") + _check_exact_text(
            attack, "受けたダメージの倍をコインで返すワザ", (CROSS_COUNTER_TEXT.format(multiplier=self.multiplier),))

    def retaliation_terms(self) -> tuple[str, None, int, bool]:
        return RETALIATION_RECEIVED, None, self.multiplier, True


def deck_owner_basic_pokemon(state: GameState, player: int, owner: str) -> list[int]:
    """プレイヤーの山札の「(``owner``)のポケモン」のたねポケモン（名前が「(``owner``)の」で始まる、進化カードでないポケモンのカード。uid の小さい順。山札の並びを写さない）
    （v0.45。タケシのイシツブテの「たすけをよぶ」の「「タケシのポケモン」(進化カード以外)」。v0.44 の ``owner_pokemon`` と同じ名前の判定）。"""
    prefix = f"{owner}の"
    return sorted(uid for uid in state.players[player].deck
                  if state.card_def(uid).is_basic_pokemon and state.card_def(uid).name_ja.startswith(prefix))


@dataclass(frozen=True)
class PutOwnerBasicFromDeckOntoBenchOnHeads(AttackEffect):
    """コインを投げて「おもて」なら、「(``owner``)のポケモン」(進化カード以外) を自分の山札から 1 枚選び出し、自分のベンチに出してよい。その後、その山札をよく切る。
    自分のベンチに空きが無い時、このワザは使えない（v0.45。タケシのイシツブテ（PMCG5-047）の「たすけをよぶ」。kyuura の印刷の文面）。

    - ベンチに空きがないことは、ワザを使うための条件（``usage_problem``。``BENCH_FULL``。v0.32 の ``PutBasicFromDeckOntoBench`` と同じ）
    - 「おもて」: 選ぶのはワザを使ったプレイヤー（決定 ``BENCH_FROM_DECK``。選べるものは山札の「(``owner``)の」で始まる名前のたねポケモン（uid の小さい順）。0〜1 枚
      （「出してよい」））。出したら手札を通らない（``zones.bench_from_deck``）。0 枚ならログ ``bench_from_deck_declined``。選べるものがなければログ
      ``bench_from_deck_none``。どの場合も、そのあと山札を切る（1 回。v0.44 の「おつかい」と同じ読み方）。「うら」なら何もしない（山札を切らない）
    - 自分の山札への効果なので、相手の状態によらずコインを投げる
    """

    owner: str
    implementation_id = "put_owner_basic_from_deck_onto_bench_on_heads"

    def check(self, attack: Attack) -> list[str]:
        expected = (f"コインを投げて「おもて」なら、「{self.owner}のポケモン」(進化カード以外)を自分の山札から1枚選び出し、自分のベンチに出してよい。その後、その山札を"
                    "よく切る。(自分のベンチに空きが無い時、このワザは使えない)")
        return _check_form(attack, "コインで山札からベンチに出すワザ", damage="none") + _check_exact_text(attack, "コインで山札からベンチに出すワザ", (expected,))

    def usage_problem(self, state: GameState, attacker: PokemonInPlay) -> IllegalActionError | None:
        owner, _ = state.find_pokemon(attacker.pokemon_id)
        if len(state.players[owner].bench) >= state.rules.max_bench:
            return IllegalActionError("BENCH_FULL", f"自分のベンチに空きがない（{state.rules.max_bench} 匹）ので、このワザは使えない（ワザの説明）")
        return None

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        return _decision_form(decision, _label(state, use), kind=BENCH_FROM_DECK, player=use.player, choices=(0, 1),
                              options=deck_owner_basic_pokemon(state, use.player, self.owner))


@dataclass(frozen=True)
class DamageIgnoringResistance(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。そのダメージは「抵抗力」の影響を受けない（v0.45。タケシのイシツブテ（PMCG5-047）の「スパイラルショット」。
    kyuura の印刷の文面）。

    - 要素は ``Damage(OPP, resistance=False)``。計算しないのは p.321 の 4 段階（抵抗力）だけで、弱点（3 段階）・プラスパワー・ディフェンダー・「ダメージを受けない」
      「ワザをうけない」状態・「とうめい」・「ダメージを受けたとき」の効果は今までどおり（v0.39 の「ソニックブーム」（弱点・抵抗力の両方）とは別の値）
    """

    implementation_id = "damage_ignoring_resistance"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "抵抗力の影響を受けないワザ", damage="fixed") + _check_exact_text(
            attack, "抵抗力の影響を受けないワザ", ("このワザのダメージは、「抵抗力」の影響を受けない。",))


OPPONENT_DECK_TOP_TEXT = ("コインを投げて「おもて」なら、相手の山札の一番上のカードを見る。そのカードが「トレーナーカード」なら、そのカードをトラッシュする。それ以外なら、"
                          "そのカードを相手の手札に加えさせる。")


@dataclass(frozen=True)
class CoinOpponentDeckTopDiscardTrainerElseHand(AttackEffect):
    """コインを投げて「おもて」なら、相手の山札の一番上のカードを見る。そのカードが「トレーナーカード」なら、そのカードをトラッシュする。それ以外なら、そのカードを相手の
    手札に加えさせる（v0.45。サカキのニャース（PMCG6-068）の「てつだうふり」。kyuura の印刷の文面。サカキのニャース（PMCG6-063）とは別のカード）。

    - 相手の山札の一番上（``deck[0]``）の 1 枚を、トレーナーカードなら相手のトラッシュ、それ以外（ポケモン・エネルギー）なら相手の手札に動かす（``zones.take_deck_top``）。
      「カードを引く」（p.312）ではない（ドローのログ・ドローに関わる処理を通さない）。説明にないので山札は切らない
    - 見たカードは、ワザを使ったプレイヤーが見て、トラッシュ（公開）か相手の手札（相手も知る）に動くので、ログ ``take_deck_top`` の ``card`` は公開
    - 相手の山札がなければ、処理の対象がないのでコインを投げない（p.309。v0.44 の「わるいいたずら」と同じ読み方）。相手のポケモンへの効果ではないので、「ワザをうけない」
      状態・「とうめい」は関係しない
    """

    implementation_id = "coin_opponent_deck_top_discard_trainer_else_hand"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "相手の山札の一番上のカードを動かすワザ", damage="none") + _check_exact_text(
            attack, "相手の山札の一番上のカードを動かすワザ", (OPPONENT_DECK_TOP_TEXT,))


# ---- v0.44 の特殊能力


COCOON_EVOLUTION_TEXTS = (
    # キョウのコクーン（PMCG6-011）の［うか］
    "この力は、自分の番ごとに1回使える。コインを投げて「おもて」なら、自分の山札から「{name}」を1枚選び出し、このカードの上にのせて進化させる。その後、その山札を"
    "よく切る。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
)


@dataclass(frozen=True)
class CoinEvolveSelfFromDeck(PowerEffect):
    """自分の番ごとに 1 回使える。コインを投げて「おもて」なら、自分の山札から「(``name``)」を 1 枚選び出し、このカードの上にのせて進化させる。その後、その山札をよく
    切る（v0.44。キョウのコクーンの［うか］。kyuura の印刷の文面）。

    - 宣言して使う。自分の番ごとに 1 回（``once_per_turn``。宣言のときに記録。コインの「うら」でも使ったことになる）。ねむり・マヒ・こんらんのこのカードは使えない
    - コインは使ったプレイヤー（v0.42 の特殊能力のコイン）。「うら」なら何もしない（山札を見ない・切らない）
    - 「おもて」: 選べるのは山札の、名前が「(``name``)」と同じカード（名前の完全一致）のうち、このカードに今重ねられるもの（通常の進化と同じ制限。``self_deck_evolution_cards``。
      おたがいの最初の番・その番に場に出した・進化したポケモンは不可。特殊能力による進化だからという理由で免除しない）。決定 ``SEARCH_DECK``（1 枚。「のせて進化させる」
      なので省略できない。1 枚でも決定を出す）→ 進化（``evolution.place_evolution_card`` の ``power``。ログ ``evolve`` の ``power``・``source_zone``）→ 山札を切る（ログ
      ``shuffle`` の ``power``）。選べるものがなければ進化させず（ログ ``evolve_from_deck_none`` の ``power``）、山札を切る（説明の「その後」）
    - 特殊能力なので、使っても番は終わらない（ワザの「たきのぼりしんか」と違う）。進化しても場のポケモンは同じで、決定を出したときのいちばん上のカード（このカード）の
      特殊能力の続きとして再開する（再開先 ``"power"``・続きの情報の ``"use"`` のカード id はこのカード）。進化したあとは、このカードの特殊能力はない（p.310）
    - 進化したあとの HP がダメージ以下になる組は選べるが選ぶと止める（v0.4a の H1）。トレーナー「サカキ」の許可だけで重ねられる組は GV1（このカードは「サカキの」
      ポケモンではないので［うか］からは起こらない。v0.45 から停止コード ``UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK``。v0.44 はコードのない問い）
    """

    name: str
    implementation_id = "coin_evolve_self_from_deck"
    once_per_turn: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "山札のカードで自分を進化させる特殊能力", tuple(t.format(name=self.name) for t in COCOON_EVOLUTION_TEXTS))

    def _candidates(self, state: GameState, use: PowerUse) -> list[int]:
        _, user = state.find_pokemon(use.pokemon_id)
        return self_deck_evolution_cards(state, use.player, user, name=self.name)

    def _hp_blocked(self, state: GameState, use: PowerUse, candidates: list[int]) -> tuple[int, ...]:
        _, user = state.find_pokemon(use.pokemon_id)
        return tuple(uid for uid in candidates if user.damage >= evolution_hp(state, user, uid))  # v0.48: 重ねたあとの最大HP

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)
        require_power_not_used(state, use)
        cards = [uid for uid in state.players[use.player].deck if state.card_def(uid).name_ja == self.name]
        if deck_evolution_permission_pairs(state, use.player, (use.pokemon_id,), cards):
            # GV1（v0.45 から停止コード。このカードは「サカキの」ポケモンではなく許可を受けないので、今の対応カードでは［うか］からは起こらないが、つきのちからと
            # 同じ問いなので同じコードで止める）
            raise UnsupportedError(PERMISSION_FROM_DECK_STOP_CODE, _PERMISSION_FROM_DECK_DETAIL)
        if deck_evolution_devolved_pairs(state, use.player, (use.pokemon_id,), cards):
            raise UnsupportedError(DEVOLVED_THIS_TURN_CODE, DEVOLVED_THIS_TURN_REASON)  # v0.50: 今の番に退化したこのカード（DV2。コインの前）
        candidates = self._candidates(state, use)
        if candidates and len(self._hp_blocked(state, use, candidates)) == len(candidates):
            raise UnsupportedError("UNRESOLVED_EVOLUTION_HP", EVOLUTION_HP_REASON)  # 「おもて」なら必ず止める（コインの前に止める）

    def resolve(self, state: GameState, use: PowerUse) -> None:
        if _power_coin(state, use) is not CoinSide.HEADS:
            return
        candidates = self._candidates(state, use)
        _, user = state.find_pokemon(use.pokemon_id)
        if not candidates:
            state.add_event("evolve_from_deck_none", player=use.player, pokemon_id=user.pokemon_id, power=str(use.key))
            shuffle_deck(state, use.player, power=str(use.key))
            return
        blocked = self._hp_blocked(state, use, candidates)
        extra = {} if not blocked else {"unresolved_choices": blocked, "unresolved_code": "UNRESOLVED_EVOLUTION_HP", "unresolved_reason": EVOLUTION_HP_REASON}
        push_power_decision(state, use, kind=SEARCH_DECK, player=use.player, options=candidates, **extra)

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        card = choices[0]
        if card not in self._candidates(state, use) or card in self._hp_blocked(state, use, [card]):
            raise RuntimeError(f"［うか］で選んだカード {choices} が、このカードに重ねられる山札のカードではない（エンジンの不具合）")
        if applicable_entry_power(state, card, from_hand=False) is not None:
            raise RuntimeError(f"［うか］で重ねるカード {card} に場に出たときの特殊能力がある（今の対応カードでは起こらない。エンジンの不具合）")
        _, user = state.find_pokemon(use.pokemon_id)
        place_evolution_card(state, use.player, user, card, power=str(use.key))
        shuffle_deck(state, use.player, power=str(use.key))

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        candidates = self._candidates(state, use)
        return _power_decision_form(decision, use, kind=SEARCH_DECK, choices=(1, 1), options=candidates, unresolved=self._hp_blocked(state, use, candidates))


# v0.45: GV1 の停止コード（v0.44 はコードのない問い。つきのちからで起こるので停止コードにした。``resolution.questions`` の ``evolution_permission_from_deck`` と同じ）
PERMISSION_FROM_DECK_STOP_CODE = "UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK"
_PERMISSION_FROM_DECK_DETAIL = (
    "トレーナー「サカキ」で今の番に進化させてよいポケモンを、山札から重ねる効果で進化させられるかは、説明の「(ポケモンを進化させる時には、あなたの手札から「進化カード」を"
    "出して、そのポケモンの上にのせる)」が許可を手札から重ねる進化に限るのかが決められないので扱わない（GV1）"
)


CALL_FOR_BOSS_TEXTS = (
    # サカキのペルシアン（PMCG6-071）の［ボスをよぶ］
    "この力は、このカードを手札から場に出した時、1度だけ使える。自分の山札から「{name}」を1枚選び出し、手札に加える。その後、その山札をよく切る。",
)


@dataclass(frozen=True)
class SearchNamedTrainerOnEntry(EntryPower):
    """この力は、このカードを手札から場に出したとき、1 度だけ使える。自分の山札から「(``name``)」を 1 枚選び出し、手札に加える。その後、その山札をよく切る（v0.44。
    サカキのペルシアンの［ボスをよぶ］。kyuura の印刷の文面）。

    - 使う機会は手札から場に出したとき（手札から進化させたとき）だけ（``from_hand_only``。v0.43 の ``EntryPower``・``offer_entry_power``。使うかは持ち主が決める）
    - 選ぶのは使ったプレイヤー（決定 ``SEARCH_DECK``。選べるものは山札の、名前が「(``name``)」と同じトレーナーカード（名前の完全一致。「サカキの切り札」は選べない）。
      1 枚。省略できない）。手札に加えるのは v0.22 のパソコン通信と同じ ``zones.search_deck_to_hand``（説明に見せる指示がないので、ログ ``search_deck`` の ``card`` は
      非公開。英語版の文面で見せる処理を加えない）→ 山札を切る（ログ ``shuffle`` の ``power``）
    - 山札に「(``name``)」がない（山札が 0 枚を含む）ときに使えるかは決められない（v0.43 の PW3 と同じ問い。使うことを選ぶと止める。使わないことは選べる）
    """

    name: str
    implementation_id = "search_named_trainer_on_entry"

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "手札から場に出したときに山札の決まった名前のトレーナーを手札に加える特殊能力",
                                 tuple(t.format(name=self.name) for t in CALL_FOR_BOSS_TEXTS))

    def accept_problem(self, state: GameState, use: PowerUse) -> UnsupportedError | None:
        if not deck_named_trainer_cards(state, use.player, self.name):
            return _power_zero_cards(f"山札に「{self.name}」がない（山札が 0 枚を含む）")
        return None

    def resolve(self, state: GameState, use: PowerUse) -> None:
        problem = self.accept_problem(state, use)
        if problem is not None:
            raise RuntimeError(f"［ボスをよぶ］を、止めるはずの場合に使った（{problem.code}。機会の決定の確認の漏れ。エンジンの不具合）")
        push_power_decision(state, use, kind=SEARCH_DECK, player=use.player, options=deck_named_trainer_cards(state, use.player, self.name))

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if choices[0] not in deck_named_trainer_cards(state, use.player, self.name):
            raise RuntimeError(f"［ボスをよぶ］で選んだカード {choices} が、山札の「{self.name}」ではない（エンジンの不具合）")
        search_deck_to_hand(state, use.player, choices[0], power=str(use.key))
        shuffle_deck(state, use.player, power=str(use.key))

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        return _power_decision_form(decision, use, kind=SEARCH_DECK, choices=(1, 1), options=deck_named_trainer_cards(state, use.player, self.name))


# ---- v0.44 のトレーナー


TRAINER_WITHOUT_TARGET_CODE = "UNRESOLVED_TRAINER_WITHOUT_TARGET"


@dataclass(frozen=True)
class EvolutionPermissionForOwnerPokemon(TrainerEffect):
    """あなたの場にいる「(``owner``)のポケモン」を 1 匹選ぶ。あなたがのぞむなら、そのポケモンが場に出たのが今の番でも、そのポケモンを進化させてよい。また、進化した
    そのポケモンを、同じ番で、さらに進化させてもよい（v0.44。トレーナー「サカキ」。kyuura の印刷の文面。docs/search-evolution-once-attacks-v0.44.md 4 章）。

    - 選ぶのは使ったプレイヤー（決定 ``SELECT_POKEMON``。選べるものは自分の場の「(``owner``)のポケモン」（いちばん上のカードの名前が「(``owner``)の」で始まる。
      ``owner_pokemon``。場の並び）。1 匹でも決定を出す）
    - 選んだポケモンに、今の番だけの記録（``PokemonInPlay.evolution_permission_turn``。ログ ``evolution_permission``）を置く。進化そのものは、このカードのあと、
      ふつうの手順（手札から進化カードを重ねる。``EvolvePokemon``。ポケモン育て屋さんも手札から重ねる進化）で行う（「あなたがのぞむなら…進化させてよい」「(ポケモンを
      進化させる時には、あなたの手札から「進化カード」を出して、そのポケモンの上にのせる)」）。記録があれば、p.310 の制限のうち「その番に場に出した」「その番に進化した」
      だけを外す（``evolution.turn_restriction``）。おたがいの最初の番・名前・段階の制限は変えない（日本語の文面に最初の番の記述はない。英語版の例外を持ち込まない）
    - 記録は場のポケモンに持つので、進化しても受け継ぎ（さらに進化できる）、ほかのポケモンには当てはまらない。番の終わりに消える。場をはなれたらなくなる
    - 山札から重ねる効果（ワザ・特殊能力）で進化させるときに記録が当てはまるかは決められない（GV1）
    - 自分の場に「(``owner``)のポケモン」がいないときに使えるかは決められない（TR1。``UNRESOLVED_TRAINER_WITHOUT_TARGET``。使う前に止める）
    """

    owner: str
    implementation_id = "evolution_permission_for_owner_pokemon"

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if not owner_pokemon(state, use.player, self.owner):
            raise UnsupportedError(
                TRAINER_WITHOUT_TARGET_CODE,
                f"自分の場に「{self.owner}のポケモン」がいない。説明が選ばせる対象（「あなたの場にいる「{self.owner}のポケモン」を1匹選ぶ」）がないときにこのトレーナーを"
                "使えるかは、kyuura の記録・印刷の文面から決められないので扱わない（TR1）",
            )

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        push_trainer_decision(state, use, kind=SELECT_POKEMON, player=use.player, options=owner_pokemon(state, use.player, self.owner))

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        (pokemon_id,) = choices
        if pokemon_id not in owner_pokemon(state, use.player, self.owner):
            raise RuntimeError(f"「{self.owner}」で選んだポケモン {choices} が、自分の場の「{self.owner}のポケモン」ではない（エンジンの不具合）")
        _, pokemon = state.find_pokemon(pokemon_id)
        pokemon.evolution_permission_turn = state.turn_number
        form = current_form(state, pokemon)
        # v0.49: 今の姿がいちばん上のカードでない（［へんしん］で写したカードの名前で「サカキのポケモン」）ときだけ、選んだときの姿のカードをログに書く（不変条件が照らす）
        extra = {} if form.kind == FORM_PRINTED else {"form_card": form.card}
        state.add_event("evolution_permission", player=use.player, pokemon=pokemon.card, pokemon_id=pokemon_id, trainer=use.card, **extra)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        return _select_own_pokemon_problems(decision, use, owner_pokemon(state, use.player, self.owner), f"「{self.owner}」")


_KYUURA_PRINTED_TEXT = "kyuura data/cards.json"
# v0.31: kyuura の日英の違いの記録（data/curation/card_differences.json。カード id がキー）が引く最新の説明を、処理に使う文面にした登録の出典
# （``#`` のあとがカード id。研究の対応表の difference_text・scripts/check_card_sources.py の DIFFERENCE_TEXT_SOURCE と同じ形）。
# kyuura に LD- の記録がなく、この記録だけが最新の説明を引いているもの（ピッピの「ゆびをふる」）
_CARD_DIFFERENCES = "kyuura data/curation/card_differences.json"
# v0.30: kyuura のエラッタの記録 RUL-ENERGY-DISCARD-ATTACKS（炎エネルギーカードをトラッシュするワザの、ネオからの説明。kyuura が『オフィシャルブック2000』
# のワザ解説と『トレーナーズ』Vol.5・Vol.9 の誌面で確かめた記録。確実。エンジンは誌面を読んでいない）。「炎エネルギーカードをトラッシュするタイプのワザ（「かえんほうしゃ」など）は、
# すべて同じ処理」で、最新の説明は次の文面（kyuura の記録の引用）。処理に使う文面の出典はこの id（研究の対応表の errata_text・errata_scope）
_RUL_ENERGY_DISCARD = "RUL-ENERGY-DISCARD-ATTACKS"
_FIRE_DISCARD_LATEST = "自分についている「炎」エネルギーカードを1枚トラッシュする。トラッシュできないとき、このワザのダメージはなくなる。"
_FIRE_DISCARD_PRINTED = "自分の「炎」エネルギーカードを1枚はがしてすてる。"


# ---------------------------------------------------------------- v0.46（docs/continuous-powers-v0.46.md）。常にはたらく特殊能力 8 つ（ダメージの変更・
# 「にげる」のエネルギー・トレーナーの禁止・特殊状態の防止）と、関連する 3 枚のワザ。処理に使う文面は kyuura の印刷の文面（11 枚とも kyuura に最新の説明・エラッタ・
# 裁定の記録がない）。はたらいているかは、場のポケモン・特殊状態・登録表・かがくへんかガスから、問い合わせのたびに求める（v0.8 の continuous.py と同じ考え方。
# 状態に「はたらいている」の印を持たない・ログを読まない）

CONTINUOUS_IN_PLAY = "in_play"  # 場（バトル場・ベンチ）にいればはたらく（なぞのかべ・ふしぎなバリアー・きょうぼう・アレルギーかふん・めんえき）
CONTINUOUS_ACTIVE = "active"  # バトル場にいる限りはたらく（くつろぐかおり・ねんちゃくえき）
CONTINUOUS_BENCH = "bench"  # ベンチでしか使えない（にげるサポート）


def _asleep_paralyzed_or_confused(pokemon: PokemonInPlay) -> bool:
    conditions = pokemon.conditions
    return bool(conditions.asleep or conditions.paralyzed or conditions.confused)


class ContinuousPower(PowerEffect):
    """常にはたらいていて、使用を宣言しない特殊能力の実装の基底（v0.46。docs/continuous-powers-v0.46.md 2 章）。

    - 宣言しない（``declared`` が False。p.311・p.323「常にはたらいているため、使用を宣言しない特殊能力もあります」）。``UsePokemonPower`` はエンジンが
      ``POWER_NOT_DECLARABLE`` で拒否する（``check_usable``・``resolve`` を呼ばない）
    - はたらいているか（``continuous_powers``）は、問い合わせのたびに、いちばん上のカード（p.310。進化前のカードの特殊能力は使えない）・場所（``location``）・
      特殊状態（``status_allows``）・かがくへんかガス（``continuous.suppressors_of``。抑止の判定を複製しない）から求める。進化・入れ替え・きぜつ・場をはなれる・
      特殊状態の変化・保存と復元のあとも、その時点の場から同じ答えになる
    - 特殊状態の条件は説明ごと（一律に「ねむり・マヒ・こんらんで消える」にしない）: ``blocked_by_status``（ねむり・マヒ・こんらんで消える・使えない）・
      ``requires_confusion``（「こんらん」状態の時だけはたらく。わるいオコリザルの［きょうぼう］）・``status_at_attack``（「ワザが使われた時、すでに…」。ワザの宣言の
      時点の特殊状態で決める。エリカのフシギソウの［くつろぐかおり］。解決の基盤の ``Resolution.attack_status``）。どくは、どの説明にも挙げられていないので関係しない
    - 効果ごとの問い合わせ（``attack_damage_modifiers``・``received_damage_modifier``）は、既定では何もしない。エンジン・解決の基盤は型で探し、カード id で分けない
    """

    declared: ClassVar[bool] = False
    location: ClassVar[str] = CONTINUOUS_IN_PLAY
    blocked_by_status: ClassVar[bool] = True
    requires_confusion: ClassVar[bool] = False
    status_at_attack: ClassVar[bool] = False
    what: ClassVar[str] = "常にはたらく特殊能力"

    def texts(self) -> tuple[str, ...]:
        """受け付ける説明（kyuura の写しの印刷の文面と完全に同じ）。"""
        raise NotImplementedError

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, self.what, self.texts())

    def located(self, state: GameState, owner: int, pokemon: PokemonInPlay) -> bool:
        """場所の条件（「このカードがバトル場にいる限り」「この力はベンチでしか使えない」）。"""
        if self.location == CONTINUOUS_IN_PLAY:
            return True
        active = state.players[owner].active is pokemon
        return active if self.location == CONTINUOUS_ACTIVE else not active

    def status_allows(self, pokemon: PokemonInPlay, attack_status: frozenset[int] | None = None) -> bool:
        """特殊状態の条件。``attack_status``（ワザが使われた時にねむり・マヒ・こんらんだったポケモンの番号）は ``status_at_attack`` の特殊能力だけが使う。"""
        if self.requires_confusion:
            return bool(pokemon.conditions.confused)
        if not self.blocked_by_status:
            return True
        if self.status_at_attack and attack_status is not None:
            return pokemon.pokemon_id not in attack_status
        return not _asleep_paralyzed_or_confused(pokemon)

    def attack_damage_modifiers(self, state: GameState, holder: PokemonInPlay, label: str, attacker: PokemonInPlay,
                                defender: PokemonInPlay) -> tuple[DamageModifier, ...]:
        """``attacker`` が ``defender`` にワザのダメージを与えるときの、この特殊能力（``holder`` が持つ）の変更効果（p.321 の段階）。"""
        return ()

    def received_damage_modifier(self, state: GameState, holder: PokemonInPlay, label: str, source: PokemonInPlay) -> DamageModifier | None:
        """``holder`` が ``source`` から、ワザでない（特殊能力の）ダメージを受けるときの変更（受けるダメージ全体を書く説明だけ）。"""
        return None

    def poison_damage_modifier(self, state: GameState, holder: PokemonInPlay, label: str) -> DamageModifier | None:
        """v0.47: ``holder`` がポケモンチェックのどくのダメージを受けるとき、当てはめるかが問われる変更（受けるダメージ全体を書き、与えるポケモンを書かない説明だけ。
        なぞのかべ・カブトアーマー）。当てはめると量が変わるなら止める（KA1。``poison_received_power_problem``）。"""
        return None


def continuous_powers(state: GameState, kind: type | tuple[type, ...] = ContinuousPower, *, attack_status: frozenset[int] | None = None,
                      ignore_status: bool = False) -> list[tuple[int, PokemonInPlay, PowerKey, ContinuousPower]]:
    """今はたらいている常にはたらく特殊能力（``kind`` の型）の (持ち主, 持つポケモン, ``PowerKey``, 実装)（v0.46）。並びはプレイヤー 0 → 1、それぞれバトル場 →
    ベンチ、カードの特殊能力の順。``ignore_status`` なら特殊状態の条件を見ない（くつろぐかおりの CP1 の読み方の比べ）。状態を変えず、乱数を使わない。"""
    from .continuous import suppressors_of  # continuous.py は effects.py を読み込むので、使うときに読み込む

    found = []
    for owner, player in enumerate(state.players):
        for pokemon in player.in_play():
            for slot in powers_of(state, pokemon):  # v0.49: 今持つ特殊能力（「ばける」でのせたカードの特殊能力を含む）
                effect = slot.effect
                if not isinstance(effect, kind) or not effect.located(state, owner, pokemon):
                    continue
                if not ignore_status and not effect.status_allows(pokemon, attack_status):
                    continue
                if suppressors_of(state, slot.power):
                    continue
                found.append((owner, pokemon, slot.key, effect))
    return found


def _power_label(state: GameState, holder: PokemonInPlay, key: PowerKey) -> str:
    """ダメージの記録・ログに出す名前（カードの名前と特殊能力の名前）。"""
    definition = state.definitions[key.card_id]  # v0.49: 特殊能力を印刷したカード
    return f"{definition.name_ja}［{definition.powers[key.power_index].name_ja}］"


def continuous_attack_damage_modifiers(state: GameState, attacker: PokemonInPlay, defender: PokemonInPlay, *,
                                       attack_status: frozenset[int] | None = None, ignore_status: bool = False) -> list[DamageModifier]:
    """``attacker`` が ``defender`` にワザのダメージを与えるときの、場の常にはたらく特殊能力の変更効果（v0.46。``attack_damage_modifiers`` から呼ぶ）。"""
    modifiers: list[DamageModifier] = []
    for _, holder, key, effect in continuous_powers(state, attack_status=attack_status, ignore_status=ignore_status):
        modifiers.extend(effect.attack_damage_modifiers(state, holder, _power_label(state, holder, key), attacker, defender))
    return modifiers


def status_at_attack_blocked(state: GameState) -> frozenset[int]:
    """ワザの宣言の時点で、ワザが使われた時の特殊状態で決める常にはたらく特殊能力（``status_at_attack``。くつろぐかおり）を持ち、ねむり・マヒ・こんらん状態の
    場のポケモンの番号（v0.46。解決の基盤が宣言のときに写す ``Resolution.attack_status``。決定をまたぐときは続きの情報で運ぶ）。かがくへんかガス・場所は、
    ダメージを計算するときに見る（説明の「このカードがバトル場にいる限り」は今の場所）。"""
    blocked = []
    for player in state.players:
        for pokemon in player.in_play():
            if not _asleep_paralyzed_or_confused(pokemon):
                continue
            if any(isinstance(slot.effect, ContinuousPower) and slot.effect.status_at_attack for slot in powers_of(state, pokemon)):  # v0.49: 今持つ特殊能力
                blocked.append(pokemon.pokemon_id)
    return frozenset(blocked)


def status_at_attack_powers(state: GameState) -> list[tuple[int, PokemonInPlay, PowerKey, ContinuousPower]]:
    """場所・かがくへんかガスの条件を満たす、ワザが使われた時の特殊状態で決める常にはたらく特殊能力（特殊状態は見ない。CP1 の確かめ）。"""
    return [found for found in continuous_powers(state, ignore_status=True) if found[3].status_at_attack]


MYSTERIOUS_WALL_TEXT = "このカードが受ける{n}以上のダメージは0になる。({n}より小さいダメージはそのまま受ける。)「ねむり・マヒ・こんらん」状態の時、この力は使えない。"


@dataclass(frozen=True)
class ZeroLargeDamageReceived(ContinuousPower):
    """このカードが受ける ``threshold`` 以上のダメージは 0 になる（``threshold`` より小さいダメージはそのまま受ける）。ねむり・マヒ・こんらん状態の時、この力は使えない
    （v0.46。バリヤード（PMCG2-027）の［なぞのかべ］。kyuura の印刷の文面）。

    - p.321 の 8 段階（「ワザを受けるポケモンの持っている「ダメージを変更する効果」」。GR-2000-P321-DAMAGE-ORDER の 8 段階の例が「なぞのかべ」）で、その段階のダメージが
      ``threshold`` 以上なら 0（``damage.ZERO_IF_AT_LEAST``。イワークの「かたくなる」の ``ZERO_IF_BELOW`` とは比べる向きが逆で、発生源も持続する効果ではなく特殊能力）。
      計算の結果が 0 なら「ダメージを受けなかった」（p.321）だけで、ダメージ以外の効果は受ける（ワザの要素を無効にする処理にしない）
    - 場（バトル場・ベンチ）のどこでもはたらく（控えへのダメージも 8 段階）。ねむり・マヒ・こんらん（ダメージを受ける時の状態）で使えない。どくは関係しない
    - ワザでない特殊能力のダメージ（はんげき・わるいねぞう・こっそりかみつく）も「受けるダメージ」なので当てはめる（``received_damage_modifier``。今の対応カードの
      特殊能力のダメージは 20 以下で、結果は変わらない）。ポケモンチェックのどくのダメージ（10・特殊などくは 20）もしきい値より小さく結果が変わらないので、どくの処理は
      通さない（どくの量がしきい値以上のカードを加えるときは見直す）。ダメージカウンターをのせる・移す効果はダメージではない（GR-2000-P320-COUNTER-MOVE）
    """

    threshold: int
    implementation_id = "zero_large_damage_received"
    what = "受ける大きいダメージを 0 にする特殊能力"

    def __post_init__(self) -> None:
        _positive_tens(self.threshold, "ダメージを 0 にするしきい値")

    def texts(self) -> tuple[str, ...]:
        return (MYSTERIOUS_WALL_TEXT.format(n=self.threshold),)

    def _modifier(self, holder: PokemonInPlay, label: str) -> DamageModifier:
        return DamageModifier(step=8, amount=self.threshold, label=label, source=holder.card, operation=ZERO_IF_AT_LEAST)

    def attack_damage_modifiers(self, state, holder, label, attacker, defender):
        return (self._modifier(holder, label),) if holder is defender else ()

    def received_damage_modifier(self, state, holder, label, source):
        return self._modifier(holder, label)

    def poison_damage_modifier(self, state, holder, label):
        return self._modifier(holder, label)  # v0.47: どくの 10・20 はしきい値より小さく、量は変わらない（止めない）


STRANGE_BARRIER_TEXT = ("このカードが「たねポケモン」から受ける{n}以上のダメージは、「{m}」になる。(ダメージ以外の効果は、そのまま)。ダメージを受ける時、すでにこのカードが"
                        "「ねむり・マヒ・こんらん」状態だったなら、この力は使えない。")


@dataclass(frozen=True)
class CapDamageFromBasic(ContinuousPower):
    """このカードが「たねポケモン」から受ける ``threshold`` 以上のダメージは ``amount`` になる（ダメージ以外の効果はそのまま）。ダメージを受ける時、すでにねむり・マヒ・
    こんらん状態だったなら、この力は使えない（v0.46。エリカのミニリュウ（PMCG5-063）の［ふしぎなバリアー］。kyuura の印刷の文面）。

    - p.321 の 8 段階（受けるポケモンの持っている効果）で、その段階のダメージが ``threshold`` 以上なら ``amount``（``damage.SET_IF_AT_LEAST``）。ダメージ以外の効果は
      受ける（ワザの要素を無効にしない）
    - 「たねポケモンから」: ダメージを与えるポケモン（ワザを使ったポケモン・返す効果を持つポケモン・特殊能力でダメージを与えるポケモン）の、ダメージを受ける時の
      いちばん上のカードが、たねポケモン（``is_basic_pokemon``）。進化した 1 進化・2 進化のポケモンは「たねポケモン」ではない。ポケモンチェックのどくは、ポケモンから
      受けるダメージではない（GR-2000-P319-HP-AND-DAMAGE「ポケモン以外のもの（…ポケモンチェックの「どく」）から受けたダメージ」）ので当てはめない
    - 特殊状態は「ダメージを受ける時、すでに」の時点（ダメージを計算する時の特殊状態）。場（バトル場・ベンチ）のどこでもはたらく
    - ワザでないダメージ（R団のカビゴンの［わるいねぞう］の 20 など。説明が「受けるダメージ」をワザに限らない）にも当てはめる（``received_damage_modifier``）
    """

    threshold: int
    amount: int
    implementation_id = "cap_damage_from_basic"
    what = "たねポケモンから受ける大きいダメージを決まった数にする特殊能力"

    def __post_init__(self) -> None:
        _positive_tens(self.threshold, "しきい値")
        _positive_tens(self.amount, "決まった数")
        if self.amount >= self.threshold:
            raise ValueError(f"決まった数 {self.amount} はしきい値 {self.threshold} より小さい")

    def texts(self) -> tuple[str, ...]:
        return (STRANGE_BARRIER_TEXT.format(n=self.threshold, m=self.amount),)

    def _modifier(self, state: GameState, holder: PokemonInPlay, label: str, source: PokemonInPlay) -> DamageModifier | None:
        if not form_def(state, source).is_basic_pokemon:  # v0.49: 今の姿のカードがたねポケモンか（［へんしん］・「ばける」）
            return None
        return DamageModifier(step=8, amount=self.amount, label=label, source=holder.card, operation=SET_IF_AT_LEAST, threshold=self.threshold)

    def attack_damage_modifiers(self, state, holder, label, attacker, defender):
        if holder is not defender:
            return ()
        found = self._modifier(state, holder, label, attacker)
        return () if found is None else (found,)

    def received_damage_modifier(self, state, holder, label, source):
        return self._modifier(state, holder, label, source)


CALMING_AROMA_TEXT = ("このカードがバトル場にいる限り、お互いの対戦ポケモンの、すべてのワザのダメージは、半分(切り上げ)になる。(自分や、控えへのダメージも半分になる)。"
                      "ワザが使われた時、すでにこのカードが「ねむり・マヒ・こんらん」状態なら、この力ははたらかない。")


@dataclass(frozen=True)
class HalveActiveAttackDamage(ContinuousPower):
    """このカードがバトル場にいる限り、お互いの対戦ポケモンの、すべてのワザのダメージは半分（切り上げ）になる（自分や、控えへのダメージも半分）。ワザが使われた時、
    すでにねむり・マヒ・こんらん状態なら、この力ははたらかない（v0.46。エリカのフシギソウ（PMCG6-010）の［くつろぐかおり］。kyuura の印刷の文面）。

    - 対象: 対戦ポケモン（バトル場のポケモン）が使ったワザのダメージ（相手・自分・控えへのダメージ）。返す効果のダメージ（ほのおのかべ・こうらがえし）もワザによる
      ダメージ（GR-2000-P321-ATTACK-DAMAGE）だが、「ワザが使われた時」がどのワザか（返す効果を与えた前の番のワザか、きっかけのワザか）が決まらないので、結果が
      変わるときは止める（CP1。解決の基盤の ``kernel.deal_damage``）。特殊能力のダメージ（はんげき・わるいねぞう）はワザのダメージではないので当てはめない。こんらんの
      20 は「ワザによるダメージ」かが決まらない（v0.3c）ので、この特殊能力がはたらいていればコインの前に止める（``confusion_power_modifiers``）
    - 段階（GR-2000-P321-DAMAGE-ORDER の持ち主の区別）: このカードがワザを使うポケモンなら 2 段階（ワザを使うポケモンの持っている効果）、ダメージを受けるポケモンなら
      8 段階、どちらでもない（相手の控えへのダメージで、このカードがバトル場にいる側）なら 6 段階（それ以外の効果）。どの段階でも 1 つのダメージの要素に 1 回
      （同じダメージに二重に当てはめない）。このカードが同じワザでワザを使うポケモンとダメージを受けるポケモンの両方になる（自分へのダメージ）場合の段階は決まらない
      が、このカードのワザに自分へのダメージはなく、相手のワザを使う効果もないので起こらない（起こったらエンジンの不具合として止める）
    - 半分の丸め: ダメージカウンターの単位（10）で切り上げ（``damage.HALVE_UP``。v0.4d のメガドレインの「半分（切り上げ）」と同じ単位）
    - 特殊状態: 「ワザが使われた時、すでに」の時点（ワザの宣言。``status_at_attack``）。ワザの途中でこのカードの特殊状態が変わっても、そのワザでは変わらない。場所
      （バトル場）・かがくへんかガスは、ダメージを計算する時の場で見る
    """

    implementation_id = "halve_active_attack_damage"
    location = CONTINUOUS_ACTIVE
    status_at_attack = True
    what = "お互いの対戦ポケモンのワザのダメージを半分にする特殊能力"

    def texts(self) -> tuple[str, ...]:
        return (CALMING_AROMA_TEXT,)

    def attack_damage_modifiers(self, state, holder, label, attacker, defender):
        located = state.find_pokemon(attacker.pokemon_id)
        if located is None or state.players[located[0]].active is not attacker:
            return ()  # 対戦ポケモンのワザのダメージではない
        if holder is attacker and holder is defender:
            raise RuntimeError(f"{label} を持つポケモン {holder.pokemon_id} が、自分のワザで自分にダメージを与えた（段階が決まらない。今の対応カードでは起こらない。"
                               "エンジンの不具合）")
        step = 2 if holder is attacker else 8 if holder is defender else 6
        return (DamageModifier(step=step, amount=2, label=label, source=holder.card, operation=HALVE_UP),)


FRENZY_TEXT = "このカードが「こんらん」状態の時、このカードがポケモンに与えるダメージは「+{n}」される。"


@dataclass(frozen=True)
class BonusDamageWhileConfused(ContinuousPower):
    """このカードがこんらん状態の時、このカードがポケモンに与えるダメージは ``amount`` 増える（v0.46。わるいオコリザル（PMCG4-041）の［きょうぼう］。kyuura の印刷の
    文面）。

    - はたらくのは、このカードがこんらん状態の時（``requires_confusion``。こんらんで消える特殊能力ではない。ねむり・マヒとこんらんは重ならない。どくは関係しない）。
      こんらん状態はダメージを計算する時の状態（あばれくるうの「ダメージを与えた後、自分は「こんらん」状態になる」は、そのダメージのあと）
    - p.321 の 2 段階（ワザを使うポケモンの持っている効果）で ``amount`` を加える。相手・控え・自分へのワザのダメージに当てはめる（「ポケモンに与えるダメージ」）
    - こんらんの 20（このカードのワザがこんらんして自分が受ける）が「このカードがポケモンに与えるダメージ」かは決まらない（v0.3c の「こんらんのダメージがワザによる
      ダメージか」と同じ問い）ので、こんらんのコインの前に止める（``confusion_power_modifiers``・``UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS``）。この特殊能力がはたらくのは
      こんらん状態の時だけなので、宣言の前の先読みがこんらんの「うら」で止まり、このカードのワザは受け付けない（docs 4.4）
    """

    amount: int
    implementation_id = "bonus_damage_while_confused"
    requires_confusion = True
    blocked_by_status = False
    what = "こんらん状態の時に与えるダメージを増やす特殊能力"

    def __post_init__(self) -> None:
        _positive_tens(self.amount, "増やすダメージ")

    def texts(self) -> tuple[str, ...]:
        return (FRENZY_TEXT.format(n=self.amount),)

    def attack_damage_modifiers(self, state, holder, label, attacker, defender):
        return (DamageModifier(step=2, amount=self.amount, label=label, source=holder.card),) if holder is attacker else ()


RETREAT_AID_TEXT = "この力はベンチでしか使えない。自分の対戦ポケモンが「にげる」時、はがしてすてるエネルギーを{n}つ分少なくできる。"


@dataclass(frozen=True)
class ReduceOwnActiveRetreatCost(ContinuousPower):
    """この力はベンチでしか使えない。自分の対戦ポケモンが「にげる」時、はがしてすてるエネルギーを ``amount`` 個分少なくできる（v0.46。ドードリオ（PMCG2-040）の
    ［にげるサポート］。kyuura の印刷の文面）。

    - 「にげる」の最中に特殊能力の使用を宣言してはいけない（p.311）ので、宣言しない（常にはたらく）。「少なくできる」なので、少なくするかは「にげる」のプレイヤーが
      トラッシュするエネルギーの数で決める（``retreat_cost``。少なくしない数でもよい）
    - ベンチにいるとき（バトル場のこのカードには当てはめない）。説明に特殊状態の条件はない（ベンチのポケモンは特殊状態にならない。p.322）。かがくへんかガスで消える
    - 「にげる」（p.311）のエネルギーだけ。ポケモンいれかえ・突風・ワザの入れ替えはエネルギーをトラッシュしないので関係しない
    """

    amount: int
    implementation_id = "reduce_own_active_retreat_cost"
    location = CONTINUOUS_BENCH
    blocked_by_status = False
    what = "自分の対戦ポケモンの「にげる」エネルギーを少なくできる特殊能力"

    def texts(self) -> tuple[str, ...]:
        return (RETREAT_AID_TEXT.format(n=self.amount),)


STICKY_GOO_TEXT = ("このカードがバトル場にいるかぎり、相手の対戦ポケモンは、「にげる」時トラッシュするエネルギーが{n}ぶん多く必要になる。このカードが「ねむり・マヒ・こんらん」"
                   "状態の時、この力は消える。")


@dataclass(frozen=True)
class IncreaseOpponentActiveRetreatCost(ContinuousPower):
    """このカードがバトル場にいるかぎり、相手の対戦ポケモンは、「にげる」時トラッシュするエネルギーが ``amount`` 個分多く必要になる。ねむり・マヒ・こんらん状態の時、
    この力は消える（v0.46。わるいベトベトン（PMCG4-007）の［ねんちゃくえき］。kyuura の印刷の文面）。

    - 「にげる」のエネルギーの数（``retreat_cost``）に、決まって ``amount`` を加える（「必要になる」なので選べない）。バトル場にいるときだけ。かがくへんかガスで消える
    - 「にげる」（p.311）のエネルギーだけ。ポケモンいれかえ・突風・ワザの入れ替えはエネルギーをトラッシュしないので関係しない
    """

    amount: int
    implementation_id = "increase_opponent_active_retreat_cost"
    location = CONTINUOUS_ACTIVE
    what = "相手の対戦ポケモンの「にげる」エネルギーを多くする特殊能力"

    def texts(self) -> tuple[str, ...]:
        return (STICKY_GOO_TEXT.format(n=self.amount),)


@dataclass(frozen=True)
class RetreatCost:
    """「にげる」でトラッシュするエネルギーの数（v0.46。``retreat_cost``）。

    - ``printed``: バトル場のポケモンのいちばん上のカードの「にげる」の数（p.310）
    - ``increases``: 決まって増やす特殊能力（(持つポケモンの番号, ``PowerKey`` の文字列, 数)。ねんちゃくえき）
    - ``reductions``: 少なくできる特殊能力（同じ形。にげるサポート。少なくするかは選べる）

    増やす数と少なくする数をまとめ、最後に 0 で下限をつける（``maximum`` = 印刷の数 + 増やす数、``minimum`` = max(0, ``maximum`` − 少なくできる数)）。少なくする数が
    印刷の数より多く、増やす数もあるときは、先に少なくして 0 で止めてから増やす読み方（``floor_first_minimum``）と最後に下限をつける読み方で、トラッシュしてよい数が
    変わる。どちらの読み方も記録から決まらない（CP2）ので、その違う数をトラッシュする「にげる」は止める（``engine._retreat``）。"""

    printed: int
    increases: tuple[tuple[int, str, int], ...] = ()
    reductions: tuple[tuple[int, str, int], ...] = ()

    @property
    def maximum(self) -> int:
        return self.printed + sum(amount for _, _, amount in self.increases)

    @property
    def minimum(self) -> int:
        return max(0, self.maximum - sum(amount for _, _, amount in self.reductions))

    @property
    def floor_first_minimum(self) -> int:
        """少なくする数を先に当てはめて 0 で止めてから、増やす数を加える読み方の下限（CP2 の比べ）。"""
        return max(0, self.printed - sum(amount for _, _, amount in self.reductions)) + sum(amount for _, _, amount in self.increases)

    def allows(self, count: int) -> bool:
        return self.minimum <= count <= self.maximum

    def floor_ambiguous(self, count: int) -> bool:
        """``count`` 枚が、最後に下限をつける読み方では正しく、先に 0 で止める読み方では足りない（CP2）。"""
        return self.minimum <= count < self.floor_first_minimum

    @property
    def modified(self) -> bool:
        return bool(self.increases or self.reductions)


def retreat_cost(state: GameState, player: int) -> RetreatCost:
    """プレイヤー ``player`` のバトル場のポケモンが「にげる」ときにトラッシュするエネルギーの数（v0.46。公開の問い合わせ。``RetreatCost``）。増やすのは相手の
    はたらいている［ねんちゃくえき］、少なくできるのは自分のはたらいている［にげるサポート］。状態を変えず、乱数を使わない。バトル場にポケモンがいなければ ``ValueError``。
    v0.47: バトル場がなにかの化石・ピッピ人形（場での役割のあるカード）なら、にげるエネルギーの数が決まらない（PF2）ので ``UnsupportedError``
    （``UNRESOLVED_PLAY_AS_POKEMON_RETREAT``。``engine._retreat`` と同じ問い）。"""
    active = state.players[player].active
    if active is None:
        raise ValueError(f"プレイヤー {player} のバトル場にポケモンがいない")
    definition = form_def(state, active)  # v0.49: 今の姿のカードのにげるエネルギー（［へんしん］・「ばける」）
    if definition.play_role is not None:
        raise UnsupportedError(PLAY_AS_POKEMON_RETREAT_CODE, f"バトル場のポケモン {active.pokemon_id}: {PLAY_AS_POKEMON_RETREAT_REASON}")
    increases, reductions = [], []
    for owner, holder, key, effect in continuous_powers(state, (IncreaseOpponentActiveRetreatCost, ReduceOwnActiveRetreatCost)):
        if isinstance(effect, IncreaseOpponentActiveRetreatCost) and owner != player:
            increases.append((holder.pokemon_id, str(key), effect.amount))
        elif isinstance(effect, ReduceOwnActiveRetreatCost) and owner == player:
            reductions.append((holder.pokemon_id, str(key), effect.amount))
    return RetreatCost(definition.retreat_cost, tuple(increases), tuple(reductions))


ALLERGIC_POLLEN_TEXT = "このカードが場にいる限り、誰もトレーナーカードを使うことができない。「ねむり・マヒ・こんらん」状態の時、この力は消える。"


@dataclass(frozen=True)
class PreventTrainerUse(ContinuousPower):
    """このカードが場にいる限り、誰もトレーナーカードを使うことができない。ねむり・マヒ・こんらん状態の時、この力は消える（v0.46。わるいラフレシア（PMCG4-010）の
    ［アレルギーかふん］。kyuura の印刷の文面）。

    - お互いのプレイヤーが、手札のトレーナーカードを使えない（``engine._play_trainer`` が、カードを手札から出す前に ``TRAINER_PREVENTED`` で拒否する。状態・乱数・
      ログは変わらない）。場（バトル場・ベンチ）のどこでもはたらく。ねむり・マヒ・こんらんで消える。かがくへんかガスで消える
    - すでに使ってポケモンについているトレーナー（プラスパワー・ディフェンダー）は、使い終わっているので、その効果は続く（使う操作ではない）。使っている最中のトレーナー
      （ポケモン育て屋さんでこのカードを場に出した）も、使い終える
    """

    implementation_id = "prevent_trainer_use"
    what = "トレーナーカードを使えなくする特殊能力"

    def texts(self) -> tuple[str, ...]:
        return (ALLERGIC_POLLEN_TEXT,)


def trainer_lock_sources(state: GameState) -> tuple[tuple[int, int, str], ...]:
    """今はたらいている、トレーナーカードを使えなくする特殊能力（v0.46。［アレルギーかふん］）の (持ち主, 持つポケモンの番号, ``PowerKey`` の文字列)。空なら
    トレーナーカードを使える（ほかの条件による）。公開の問い合わせ。状態を変えず、乱数を使わない。"""
    return tuple((owner, holder.pokemon_id, str(key)) for owner, holder, key, _ in continuous_powers(state, PreventTrainerUse))


IMMUNITY_TEXT = "このカードは、「どく・ねむり・マヒ・こんらん」状態にならない。(なんらかの原因で「ねむり・マヒ・こんらん」状態になっているとき、この力は使えない)"


@dataclass(frozen=True)
class SpecialConditionImmunity(ContinuousPower):
    """このカードは、どく・ねむり・マヒ・こんらん状態にならない。なんらかの原因でねむり・マヒ・こんらん状態になっているとき、この力は使えない（v0.46。カビゴン
    （PMCG2-047）の［めんえき］。kyuura の印刷の文面）。

    - 特殊状態にする効果（ワザ・特殊能力のどれでも）を受けても、その特殊状態にならない（``conditions`` の付ける処理の共通の入口で防ぐ。ログ
      ``special_condition_prevented``）。すでにある特殊状態を回復する効果ではない（どくは残る）
    - すでにねむり・マヒ・こんらん状態（かがくへんかガスで消えていた間になった）なら使えない。どく状態だけなら使える（ねむり・マヒ・こんらんにならない・どくの
      上書き（特殊などく）もしない）
    - 防がれる特殊状態について、原典で決められない場合の確かめ（マヒの再付与・特殊などくの上書き・「ダメージを与えた後」の効果）は、防がれて結果が変わらないので
      聞かない（``resolution.programs.Status``）。効果を決めるコインは、効果の要素が無効なのではなく、効果を受けて特殊状態にならないので、今までどおり投げる
    """

    implementation_id = "special_condition_immunity"
    what = "特殊状態にならない特殊能力"

    def texts(self) -> tuple[str, ...]:
        return (IMMUNITY_TEXT,)


def status_immunity(state: GameState, owner: int, pokemon: PokemonInPlay) -> PowerKey | None:
    """場のポケモン ``pokemon``（持ち主 ``owner``）の、今はたらいている特殊状態にならない特殊能力（v0.46。［めんえき］）の ``PowerKey``。なければ None。"""
    from .continuous import suppressors_of  # continuous.py は effects.py を読み込むので、使うときに読み込む

    for slot in powers_of(state, pokemon):  # v0.49: 今持つ特殊能力
        effect = slot.effect
        if isinstance(effect, SpecialConditionImmunity) and effect.located(state, owner, pokemon) and effect.status_allows(pokemon) \
                and not suppressors_of(state, slot.power):
            return slot.key
    return None


def received_power_damage(state: GameState, owner: int, receiver: PokemonInPlay, source: PokemonInPlay, amount: int) -> tuple[int, tuple[DamageModifier, ...]]:
    """特殊能力のダメージ（はんげき・わるいねぞう・こっそりかみつく。ワザによるダメージではない）を ``receiver`` が受けるときの、受けるダメージ全体を書く常にはたらく
    特殊能力（なぞのかべ・ふしぎなバリアー）を当てはめた数と、当てはめた変更（v0.46）。p.321 の計算の順番（ワザによるダメージの計算）は当てはめず、受けるポケモンの
    特殊能力だけを、持つ特殊能力の順に当てはめる（2 つ以上が当てはまる場合は今の対応カードでは起こらない。起こったらエンジンの不具合として止める）。"""
    applied = []
    for holder_owner, holder, key, effect in continuous_powers(state):
        if holder is not receiver:
            continue
        modifier = effect.received_damage_modifier(state, holder, _power_label(state, holder, key), source)
        if modifier is not None:
            applied.append(modifier)
    if len(applied) > 1:
        raise RuntimeError(f"特殊能力のダメージを受けるポケモン {receiver.pokemon_id} に、受けるダメージを変える特殊能力が 2 つ以上ある（順番が決まらない。エンジンの不具合）")
    for modifier in applied:
        amount = modifier.apply(amount, state.rules.damage_per_counter)
    return amount, tuple(applied)


def received_modifiers_log(applied: tuple[DamageModifier, ...]) -> tuple[tuple, ...]:
    """ワザでないダメージに当てはめた、受けるダメージを変える特殊能力の記録（ログの ``received_modifiers``。(発生源のカード, 計算, しきい値, 数)）。"""
    return tuple((m.source, m.operation, m.threshold, m.amount) for m in applied)


def confusion_power_modifiers(state: GameState, pokemon: PokemonInPlay, attack_status: frozenset[int] | None) -> list[str]:
    """こんらんしたワザの 20（ワザを使ったポケモン ``pokemon`` が自分に受ける）を、ワザのダメージ（このポケモンが与えるダメージ）として扱うなら当てはまる、常に
    はたらく特殊能力の名前（v0.46。くつろぐかおり・きょうぼう・なぞのかべ・ふしぎなバリアー）。こんらんの 20 がワザによるダメージか・このポケモンが与えるダメージかは
    決まらない（v0.3c）ので、当てはまるものがあれば、コインの前に止める（``procedures.confusion_damage_problem``）。"""
    return [modifier.label for modifier in continuous_attack_damage_modifiers(state, pokemon, pokemon, attack_status=attack_status, ignore_status=False)]


# --- v0.46 のワザ（エリカのフシギソウ・わるいオコリザル・わるいラフレシア・エリカのフシギバナ・エリカのタマタマ・エリカのナッシー）


@dataclass(frozen=True)
class DamageThenSelfConfuse(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージを与えた後、自分（ワザを使ったポケモン）をこんらん状態にする（v0.46。わるいオコリザルの「あばれくるう」。
    kyuura の印刷の文面「ダメージを与えた後、自分は「こんらん」状態になる。」）。

    - 要素の並びは v0.17b の「たおれこむ」と同じ形（``Damage`` → ``Status(CONFUSION, target=SELF, after_damage="damage")``）。ダメージ → ダメージを受けたときの効果の窓
      → 自分をこんらん。自分が HP 以上なら、処理の対象がないのでこんらんにしない（p.309）
    - ダメージを与えなかったとき（ディフェンダーで 0・「ダメージを受けない」・「とうめい」・なぞのかべで 0）は「ダメージを与えた後」の効果を処理するかが決まらない
      （Z23。既存の問いを使う）
    - ［きょうぼう］の +30 は、このダメージを計算する時にこんらん状態のときだけ（あばれくるうで自分をこんらんにするのは、ダメージのあと）
    """

    implementation_id = "damage_then_self_confuse"

    def check(self, attack: Attack) -> list[str]:
        return _check_damage_then_effect(attack, "自分をこんらん状態にする") + _check_exact_text(
            attack, "ダメージのあと自分をこんらん状態にするワザ", ("ダメージを与えた後、自分は「こんらん」状態になる。",))


@dataclass(frozen=True)
class CoinsTimesDamageSelfConfuse(AttackEffect):
    """コインを ``coins`` 枚投げて「おもて」の数 × ``per`` のダメージ。``at_least`` 枚以上「おもて」なら、自分（ワザを使ったポケモン）をこんらん状態にする（v0.46。
    わるいラフレシアの「はなびらのうず」。kyuura の印刷の文面。文末の「。」がない書き方も、ある書き方も受け付ける）。

    - 同じ ``coins`` 枚のコイン（ワザ全体のコイン ``Coin``）の「おもて」の数で、ダメージと自分のこんらんの両方を決める（要素ごとに投げ直さない）。``Damage`` は
      「おもて」の数 × ``per``（``HeadsOfCoin``）、``Status(CONFUSION, target=SELF, gate=("coin", AtLeast(at_least)))``
    - 自分のこんらんは自分への効果なので、相手が「ダメージを受けない」状態でもコインを投げる（v0.34 の ``void_coin_question``）。自分が HP 以上なら処理の対象がない
    """

    coins: int
    per: int
    at_least: int
    implementation_id = "coins_times_damage_self_confuse"

    def __post_init__(self) -> None:
        if type(self.coins) is not int or self.coins < 2 or type(self.at_least) is not int or not 1 <= self.at_least <= self.coins:
            raise ValueError(f"コインの枚数 {self.coins!r}・こんらんになる「おもて」の数 {self.at_least!r} が正しくない")
        _positive_tens(self.per, "「おもて」1 枚あたりのダメージ")

    def check(self, attack: Attack) -> list[str]:
        text = f"コインを{self.coins}枚投げて「おもて」の数×{self.per}のダメージ。{self.at_least}枚以上「おもて」なら、自分は「こんらん」状態になる"
        problems = _check_form(attack, "コインの数でダメージを与えて自分をこんらんにするワザ", damage="modified", modifier="×")
        if attack.damage != self.per:
            problems.append(f"ダメージの目安の数字 {attack.damage!r} と、登録した「おもて」1 枚あたりのダメージ {self.per} が違う")
        return problems + _check_exact_text(attack, "コインの数でダメージを与えて自分をこんらんにするワザ", (text, text + "。"))


GROWTH_TEXT = "コインを投げて「おもて」なら、自分の手札にある「{type}」エネルギーカードを最大{n}枚、このカードにつける。"


def hand_basic_energy(state: GameState, player: int, energy_type: EnergyType) -> list[int]:
    """プレイヤー ``player`` の手札の ``energy_type`` の基本エネルギーカード（手札の並び。v0.46）。"""
    return [uid for uid in state.players[player].hand if state.card_def(uid).is_basic_energy and state.card_def(uid).provides is energy_type]


@dataclass(frozen=True)
class AttachEnergyFromHandOnHeads(AttackEffect):
    """コインを投げて「おもて」なら、自分の手札にある ``energy_type`` エネルギーカードを最大 ``max_cards`` 枚、このカード（ワザを使ったポケモン）につける（v0.46。
    エリカのフシギバナの「せいちょう」。kyuura の印刷の文面）。

    - コイン（``Coin``）→「おもて」なら決定 ``ATTACH_FROM_HAND``（ワザを使ったプレイヤー。手札の ``energy_type`` の基本エネルギーカード。0〜min(``max_cards``, 枚数)）→
      つける（``zones.attach_energy_from_hand``。手札からつける通常の操作・あまごいと同じカードの動かし方）。つけたら ``after_energy_attached``
    - 手札からつける通常の操作（p.310。1 番に 1 枚。``energy_attachments_this_turn``）・特殊能力でつけた枚数（``energy_attached_by_powers_this_turn``）には数えない
      （ワザの効果。別の処理）
    - 手札にそのエネルギーカードがなければ、処理の対象がないのでコインを投げない（v0.38 の ``has_target``）。あるときに 0 枚を選べるかは決まらない（「最大2枚」が
      0 枚を含むか。v0.31 の HC7 と同じ問い。答えのときに止める）
    - 特殊エネルギーは選べない（説明は「「草」エネルギーカード」。今の写しに特殊エネルギーのカードはない）
    """

    energy_type: EnergyType
    max_cards: int
    implementation_id = "attach_energy_from_hand_on_heads"

    def __post_init__(self) -> None:
        if type(self.max_cards) is not int or self.max_cards < 1:
            raise ValueError(f"つける枚数の最大は 1 以上（{self.max_cards!r}）")

    def check(self, attack: Attack) -> list[str]:
        text = GROWTH_TEXT.format(type=self.energy_type.ja, n=self.max_cards)
        return _check_form(attack, "手札のエネルギーカードを自分につけるワザ", damage="none") + _check_exact_text(attack, "手札のエネルギーカードを自分につけるワザ", (text,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        candidates = hand_basic_energy(state, use.player, self.energy_type)
        return _decision_form(decision, _label(state, use), kind=ATTACH_FROM_HAND, player=use.player, choices=(0, min(self.max_cards, len(candidates))),
                              options=candidates)


SPREAD_SOLAR_BEAM_TEXT = "相手の控えポケモンを{n}匹選び、それらのポケモンにも、「弱点・抵抗力」に関係なく、それぞれ{d}ダメージ。"


@dataclass(frozen=True)
class DamageThenExactBenchTargets(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。相手の控えポケモンを ``targets`` 匹選び、「弱点・抵抗力」に関係なく、それぞれ ``bench_damage``
    ダメージ（v0.46。エリカのフシギバナの「かくさんソーラービーム」。kyuura の印刷の文面）。

    - 要素は v0.39 の ``ChosenBenchDamages`` の ``exact``（ちょうど ``targets`` 匹。「最大」の v0.39 の「ギガスパーク」と混ぜない。0 匹・少ない数は選べない）
    - 相手に控えがいなければ、処理の対象がないので選ばない（p.309）。控えが 1 匹以上で ``targets`` 匹より少ないときに、いるだけ選ぶのか、その内容を処理しないのかは
      決まらない（v0.44 の FC1 と同じ問い「説明が決まった数を選ばせるとき、選べるものが足りない」。宣言の前に止まる）
    """

    targets: int
    bench_damage: int
    implementation_id = "damage_then_exact_bench_targets"

    def __post_init__(self) -> None:
        if type(self.targets) is not int or self.targets < 2:
            raise ValueError(f"選ぶ数は 2 以上（{self.targets!r}）")
        _positive_tens(self.bench_damage, "控えポケモンへのダメージ")

    def check(self, attack: Attack) -> list[str]:
        text = SPREAD_SOLAR_BEAM_TEXT.format(n=self.targets, d=self.bench_damage)
        return _check_form(attack, "相手の控えを決まった数選んでダメージを与えるワザ", damage="fixed") + _check_exact_text(
            attack, "相手の控えを決まった数選んでダメージを与えるワザ", (text,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        bench = state.players[1 - use.player].bench
        return _decision_form(decision, _label(state, use), kind=SELECT_POKEMON, player=use.player, choices=(self.targets, self.targets),
                              options=(p.pokemon_id for p in bench))


@dataclass(frozen=True)
class HalveDamageNextTurn(AttackEffect):
    """次の相手の番、このカードが受けるダメージは半分（切りすて）になる（ダメージ以外の効果はそのまま）（v0.46。エリカのタマタマの「リフレクター」。kyuura の印刷の
    文面）。

    - 自分自身に与える持続する効果 ``state.HalvedDamage``（はたらく番は次の相手の番。消える契機は v0.4b と同じ）。はたらく番に受けるワザのダメージの p.321 の 8 段階で、
      半分にしてダメージカウンターの単位で切りすてる（``damage.HALVE_DOWN``）。［くつろぐかおり］（常にはたらく特殊能力。切り上げ）とは、はたらく条件・期限・丸めの
      向きが違い、半分にする計算だけを共通にする
    - ダメージ以外の効果は受ける（「ダメージを受けない」状態・「ワザをうけない」状態とは別）
    """

    implementation_id = "halve_damage_next_turn"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "次の相手の番に受けるダメージを半分にするワザ", damage="none") + _check_exact_text(
            attack, "次の相手の番に受けるダメージを半分にするワザ", ("次の相手の番、このカードが受けるダメージは半分(切りすて)になる。(ダメージ以外の効果はそのまま)",))

    def halved_terms(self) -> tuple[type]:
        from .state import HalvedDamage

        return (HalvedDamage,)


PSYCHIC_EXCHANGE_TEXT = "自分の手札をすべて山札にもどし、山札をよく切る。その後、カードを{n}枚引いて、手札にする。"


@dataclass(frozen=True)
class ShuffleHandIntoDeckThenDraw(AttackEffect):
    """自分の手札をすべて山札にもどし、山札をよく切る。その後、カードを ``count`` 枚引いて、手札にする（v0.46。エリカのナッシーの「サイコエクスチェンジ」。kyuura の
    印刷の文面）。

    - もどす（相手に見せない。v0.44 の ``zones.return_hand_cards_to_deck``。手札の並びの順。決定はない（すべて））→ 切る（1 回。``programs.shuffle_in_attack``）→ 引く
      （``zones.draw_cards``。山札が足りなければ引けるだけ。効果で引くときの規定。p.312）。もどす前に引かない・もどしたカードを見せない
    - 手札がなくても、山札を切って引く（説明の文はそれぞれ別の内容。p.309）
    - 要素の並びの最後の要素（先読みでは山札を切らない。引いたカードを使う要素があとにない）
    """

    count: int
    implementation_id = "shuffle_hand_into_deck_then_draw"

    def __post_init__(self) -> None:
        if type(self.count) is not int or self.count < 1:
            raise ValueError(f"引く枚数は 1 以上（{self.count!r}）")

    def check(self, attack: Attack) -> list[str]:
        text = PSYCHIC_EXCHANGE_TEXT.format(n=self.count)
        return _check_form(attack, "手札を山札にもどして引くワザ", damage="none") + _check_exact_text(attack, "手札を山札にもどして引くワザ", (text,))


# ---------------------------------------------------------------- v0.47（docs/fossil-hidden-info-v0.47.md）。なにかの化石・ピッピ人形（ポケモンとして場に出せる
# トレーナーカード）、常にはたらく特殊能力 3 つ（おみとおし・カブトアーマー・げんしのちから）、見えないカードを見る・入れかえる特殊能力 2 つ（スパイ・わるふざけ）、
# 期限のあるトレーナーの使用の禁止（ずつう・こうしゅうは）と、関連するワザ。処理に使う文面はどれも kyuura の印刷の文面（13 枚とも kyuura に最新の説明・エラッタ・裁定の
# 記録がない）。場での HP などは pcg-search.com の同じ版のページの値（kyuura の写しのトレーナーのデータにない。採用の記録に書いた）

FOSSIL_TEXT = ("このカードはポケモンとして場に出すことができ、場に出ている限りポケモンとしてあつかわれる。このカードには、「なにかの化石から進化」と書かれている進化"
               "カードを重ねることができる。進化カードがのっていないときに限り、「きぜつ」しても「きぜつ」とカウントされず、自分の番の好きなときに自分のトラッシュに"
               "すてることができる。")
DOLL_TEXT = ("ポケモンとして場に出すことができる。「きぜつ」しても「きぜつ」ポケモンとしてカウントされない。自分の番の好きなときにすてることができる。場に出ているとき"
             "以外は、トレーナーカードとしてあつかう。")
PLAY_AS_POKEMON_TEXTS = {"fossil": FOSSIL_TEXT, "doll": DOLL_TEXT}

# 場での役割のポケモンの「にげる」が決まらない（v0.47。docs 3 章の PF2）。印刷の文面に「にげる」の記述がなく、kyuura の写しのトレーナーのデータに「にげる」の欄がない。
# pcg-search.com のページの「にげる -」は、にげるエネルギーが 0 のポケモン（マンキーなど）と同じ表示で、0 か「にげることができない」かを区別しない。英語版の
# 「can't retreat」は持ち込まない
PLAY_AS_POKEMON_RETREAT_CODE = "UNRESOLVED_PLAY_AS_POKEMON_RETREAT"
PLAY_AS_POKEMON_RETREAT_REASON = (
    "場のなにかの化石・ピッピ人形が「にげる」ことができるか（にげるエネルギーの数）は、印刷の文面・kyuura のデータ（トレーナーのデータに「にげる」の欄がない）・"
    "pcg-search.com のページ（「にげる -」は、にげるエネルギーが 0 のポケモンと同じ表示）から決められないので扱わない（PF2。英語版の「can't retreat」は持ち込まない）"
)
# 対戦準備（PF1）: 手札のなにかの化石・ピッピ人形（手札ではトレーナーカード）を、最初のポケモンとして場に出せるか・手札にたねポケモンがなくこれらがあるときに切り直すか
PLAY_AS_POKEMON_SETUP_CODE = "UNRESOLVED_PLAY_AS_POKEMON_SETUP"
PLAY_AS_POKEMON_SETUP_REASON = (
    "手札のなにかの化石・ピッピ人形（場に出ているとき以外はトレーナーカード）を、対戦準備で最初のポケモンとして場に出せるか、手札にたねポケモンがなくこれらがある"
    "ときに切り直すかは、公式ルール 2000.02.14版（p.308「たねポケモン」）とカードの文面から決められないので扱わない（PF1。1997 年の会報 Vol.2 の第2版の時期の"
    "記述（kyuura rule_history.json の P35）は別の版の記録なので使わない）"
)
# ポケモン育て屋さん（PF3）: 場のなにかの化石（印刷のたねポケモンではない）に、1 進化を飛ばして 2 進化カード（オムスター・カブトプス）を重ねられるか
BREEDER_PLAY_AS_POKEMON_CODE = "UNRESOLVED_BREEDER_ON_PLAY_AS_POKEMON"
BREEDER_PLAY_AS_POKEMON_REASON = (
    "ポケモン育て屋さんで、場のなにかの化石（ポケモンとしてあつかわれるが、印刷のたねポケモンのカードではない）に、1 進化を飛ばして 2 進化カードを重ねられるかは、"
    "最新の説明（p.259）・解説（たねポケモンの例）・なにかの化石の文面（「なにかの化石から進化」と書かれている進化カードを重ねる）から決められないので扱わない（PF3）"
)


@dataclass(frozen=True)
class PlayAsPokemon(TrainerEffect):
    """ポケモンとして場に出すことができるトレーナーカード（v0.47。なにかの化石（PMCG3-046。``role`` は ``"fossil"``）・ピッピ人形（PMCG1-091。``"doll"``）。kyuura の
    印刷の文面。docs/fossil-hidden-info-v0.47.md 2 章）。

    - 印刷の分類はトレーナーカードのまま（写し・``CardDefinition`` を変えない）。手札・山札・サイド・トラッシュではトレーナーカード（デッキの検査・切り直し・山札や
      トラッシュから選ぶ効果の対象・トレーナーの使用の禁止も、その分類で決まる）。場にいるあいだだけ、場での役割の定義（``in_play_definition``。``GameState.card_def``
      が返す）でポケモンとしてあつかう
    - 使う（``PlayTrainer``）と、手札から出し（ログ ``play_trainer``）、自分のベンチにポケモンとして出す（``zones.put_trainer_into_play``。ログ
      ``play_trainer_as_pokemon``）。トラッシュしない（``enters_play``）。ベンチに空きがなければ使えない（``BENCH_FULL``。手札から出す前）。バトル場には直接出さない
      （手札のポケモンはベンチに出す。p.309）。トレーナーカードを使うことなので、トレーナーの使用の禁止（［アレルギーかふん］・ずつう）を受ける
    - 場での役割: HP ``hp``（pcg-search.com の同じ版のページの「HP:10」）・タイプなし・弱点なし・抵抗力なし（同じページの「弱点 -」「抵抗力 -」）・ワザなし・特殊能力
      なし。「にげる」は決まらない（PF2。``PLAY_AS_POKEMON_RETREAT_CODE``）。段階は、進化の重なりのいちばん下のカードとして「たね」と同じ位置（なにかの化石には
      「なにかの化石から進化」の 1 進化カードを重ねる。``evolution.evolution_block`` の名前と段階の確かめ）。特殊状態・エネルギー・トレーナーをつけることは、印刷の
      文面に制限がないので場のポケモンの規定のまま（英語版の制限は持ち込まない）
    - 「きぜつ」してもカウントされない（``counts_knockout`` が偽）: きぜつの処理（トラッシュ）はするが、相手はサイドを取らない（ログ ``knock_out`` の ``counted`` が
      False）。進化カードがのったら（いちばん上が進化カード）ふつうのポケモンで、きぜつはカウントされる（場での役割はいちばん上のカードで決まる）
    - 自分の番の好きなときにすてられる（``DiscardFromPlay``。進化カードがのっていないときだけ）
    """

    hp: int
    role: str
    implementation_id = "play_as_pokemon"
    enters_play = True
    counts_knockout: ClassVar[bool] = False
    discardable_from_play: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if self.role not in PLAY_AS_POKEMON_TEXTS:
            raise ValueError(f"場での役割 {self.role!r} は {sorted(PLAY_AS_POKEMON_TEXTS)} のどれでもない")
        _positive_tens(self.hp, "場での HP")

    def check(self, definition: CardDefinition) -> list[str]:
        problems = super().check(definition)
        if definition.trainer_text_ja != PLAY_AS_POKEMON_TEXTS[self.role]:
            problems.append(f"文面 {definition.trainer_text_ja!r} が、ポケモンとして場に出せるトレーナーカード（{self.role}）の文面ではない")
        return problems

    def in_play_definition(self, printed: CardDefinition) -> CardDefinition:
        """場にいるあいだの定義（印刷の定義とは別のインスタンス。印刷の定義は変えない）。"""
        from .cards import CardDefinition

        return CardDefinition(id=printed.id, name_ja=printed.name_ja, name_en=printed.name_en, category="pokemon", supported=True, unsupported_reasons=(),
                              stage="basic", hp=self.hp, pokemon_type=None, weakness=None, resistance=None, retreat_cost=None, attacks=(), powers=(),
                              play_role=self.role)

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if len(state.players[use.player].bench) >= state.rules.max_bench:
            raise IllegalActionError("BENCH_FULL", f"ベンチに空きがないので、「{state.card_def(use.card).name_ja}」をポケモンとして場に出せない（ベンチは {state.rules.max_bench} 匹まで）")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        put_trainer_into_play(state, use.player, use.card)


def play_as_pokemon_effect(state: GameState, pokemon: PokemonInPlay) -> PlayAsPokemon | None:
    """場のポケモン ``pokemon`` のいちばん上のカードが、ポケモンとして場に出したトレーナーカードなら、その実装（v0.47）。ほかは None。"""
    definition = state.card_def(pokemon.card)
    if definition.play_role is None:
        return None
    effect = state.effects.trainer_effect(state.printed_def(pokemon.card))
    if not isinstance(effect, PlayAsPokemon):
        raise RuntimeError(f"場での役割 {definition.play_role} のカード {pokemon.card} の登録が PlayAsPokemon ではない（エンジンの不具合）")
    return effect


def counts_as_knockout(state: GameState, pokemon: PokemonInPlay) -> bool:
    """場のポケモン ``pokemon`` の「きぜつ」が、きぜつしたポケモンとしてカウントされる（相手がサイドを取る）か（v0.47）。いちばん上のカードがなにかの化石・ピッピ人形
    （進化カードがのっていない）ならカウントされない。きぜつの処理（トラッシュ）の前に、場にいるうちに聞く。"""
    effect = play_as_pokemon_effect(state, pokemon)
    return effect is None or effect.counts_knockout


def play_as_pokemon_in_hand(state: GameState, player: int) -> list[int]:
    """プレイヤー ``player`` の手札の、ポケモンとして場に出せるトレーナーカード（登録した実装が ``PlayAsPokemon``）の uid（v0.47。対戦準備の PF1 の確かめ）。"""
    return [uid for uid in state.players[player].hand if isinstance(state.effects.trainer_effect(state.printed_def(uid)), PlayAsPokemon)]


# --- 常にはたらく特殊能力（v0.46 の ``ContinuousPower`` の部分型）

CLAIRVOYANCE_TEXT = ("オムナイトが場にいる限り、相手プレイヤーは自分の手札が全員に見えるようにしてプレイしなければならない。「ねむり・マヒ・こんらん」状態の時、"
                     "この力は消える。")


@dataclass(frozen=True)
class RevealOpponentHand(ContinuousPower):
    """このカードが場にいる限り、相手プレイヤーは自分の手札が全員に見えるようにしてプレイしなければならない。ねむり・マヒ・こんらん状態の時、この力は消える（v0.47。
    オムナイト（PMCG3-015）の［おみとおし］。kyuura の印刷の文面）。

    - 相手の手札を続けて公開する（1 枚を 1 度見る効果ではない）。公開しているかは、問い合わせのたびに今の場から求める（``hand_revealed_by``。v0.46 の
      ``continuous_powers``。特殊状態・かがくへんかガス・進化（いちばん上のカード）・場をはなれることを、その時点の場で反映する）。手札が増えた・減った・入れかわった
      あとも、その時点の手札全体が見える
    - プレイヤーに渡す観測（``observation.observe``）で、相手の手札を全員（両方のプレイヤーと観戦者）に見せる。はたらかなくなったら、その時点からは見せない（前の観測で
      見えていた情報は、その観測の値として残る。状態に「見た」記録を持たない）
    - ゲームの処理（ワザ・トレーナー・選び方）は変えない（見えるかどうかだけ）
    """

    implementation_id = "reveal_opponent_hand"
    what = "相手の手札を見えるようにする特殊能力"

    def texts(self) -> tuple[str, ...]:
        return (CLAIRVOYANCE_TEXT,)


def hand_revealed_by(state: GameState, player: int) -> tuple[tuple[int, int, str], ...]:
    """プレイヤー ``player`` の手札を全員に見えるようにしている、今はたらいている特殊能力（相手の［おみとおし］）の (持ち主, 持つポケモンの番号, ``PowerKey`` の文字列)
    （v0.47。公開の問い合わせ）。空なら、手札は持ち主にだけ見える。状態を変えず、乱数を使わない。"""
    return tuple((owner, holder.pokemon_id, str(key)) for owner, holder, key, _ in continuous_powers(state, RevealOpponentHand) if owner != player)


KABUTO_ARMOR_TEXT = "このカードが受けるダメージは半分(切りすて)になる。(ダメージ以外の効果はそのまま)。「ねむり・マヒ・こんらん」状態の時、この力は使えない。"


@dataclass(frozen=True)
class HalveDamageReceived(ContinuousPower):
    """このカードが受けるダメージは半分（切りすて）になる（ダメージ以外の効果はそのまま）。ねむり・マヒ・こんらん状態の時、この力は使えない（v0.47。カブト
    （PMCG3-035）の［カブトアーマー］。kyuura の印刷の文面）。

    - p.321 の 8 段階（ワザを受けるポケモンの持っている効果。GR-2000-P321-DAMAGE-ORDER）で、その段階のダメージを半分（切りすて。``damage.HALVE_DOWN``。v0.46 の
      リフレクターと同じ計算の部品・ダメージカウンターの単位の丸め）。どのポケモンのワザのダメージでも（自分のワザ・控えへのダメージも。説明は与えるポケモンを
      書かない）。ダメージ以外の効果は受ける（ワザの要素を無効にする処理にしない）。同じ 8 段階にほかの効果があり、順番で結果が変われば v0.35 の決定で選ばせる
    - 場（バトル場・ベンチ）のどこでもはたらく。ねむり・マヒ・こんらん（ダメージを受ける時の状態）で使えない。かがくへんかガスで消える。どくは関係しない
    - ワザでない特殊能力のダメージ（はんげき・わるいねぞう・こっそりかみつく）も「受けるダメージ」なので当てはめる（v0.46 の ``received_power_damage``）
    - こんらんの 20（自分のワザがこんらんして受ける）には当てはまらない: こんらん状態のカブトはこの力を使えないので、v0.3c の問い（こんらんの 20 に当てはめるか。
      ``UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS``）は起こらない（こんらんの 20 をそのまま受ける）
    - ポケモンチェックのどくのダメージ（ワザによるダメージではない。p.321・p.322）に当てはめるかは決まらない（KA1。「受けるダメージ」が説明の「(ダメージ以外の効果は
      そのまま)」とともにワザのダメージを指すのか、どくのダメージも含むのか）。当てはめると結果が変わるので、ダメージを与える前に対戦を止める
      （``procedures.pokemon_check_poison``。``POISON_RECEIVED_POWER``）
    - ダメージカウンターをのせる・移す効果はダメージではない（GR-2000-P320-COUNTER-MOVE）ので変えない
    """

    implementation_id = "halve_damage_received"
    what = "受けるダメージを半分にする特殊能力"

    def texts(self) -> tuple[str, ...]:
        return (KABUTO_ARMOR_TEXT,)

    def _modifier(self, holder: PokemonInPlay, label: str) -> DamageModifier:
        return DamageModifier(step=8, amount=2, label=label, source=holder.card, operation=HALVE_DOWN)

    def attack_damage_modifiers(self, state, holder, label, attacker, defender):
        return (self._modifier(holder, label),) if holder is defender else ()

    def received_damage_modifier(self, state, holder, label, source):
        return self._modifier(holder, label)

    def poison_damage_modifier(self, state: GameState, holder: PokemonInPlay, label: str) -> DamageModifier | None:
        return self._modifier(holder, label)


PREHISTORIC_POWER_TEXT = "プテラが場にいる限り、全てのポケモンは進化することができない。(すでに進化しているポケモンに影響はない)。「ねむり・マヒ・こんらん」状態の時、この力は消える。"


@dataclass(frozen=True)
class PreventEvolution(ContinuousPower):
    """このカードが場にいる限り、全てのポケモンは進化することができない（すでに進化しているポケモンに影響はない）。ねむり・マヒ・こんらん状態の時、この力は消える
    （v0.47。プテラ（PMCG3-041）の［げんしのちから］。kyuura の印刷の文面）。

    - お互いの場のすべてのポケモンの、どの方法の進化も止める（``evolution_preventers``。進化の入口の共通の確かめ ``evolution.evolution_block`` の最初に聞く）: 手札の
      進化カードを重ねる通常の操作（``EvolvePokemon``）・ポケモン育て屋さん（使えない）・ワザの効果で山札から重ねる（つきのちから・たきのぼりしんか）・特殊能力の
      効果で山札から重ねる（［うか］）。進化カードを山札から手札に加える効果（しんかのひかり）は進化ではないので止めない
    - すでに進化しているポケモンを退化させない（重なりを変えない）
    - 場（バトル場・ベンチ）のどこでもはたらく。ねむり・マヒ・こんらん・かがくへんかガスで消え、消えたらその時点から進化できる（今の場から求める）
    """

    implementation_id = "prevent_evolution"
    what = "ポケモンを進化できなくする特殊能力"

    def texts(self) -> tuple[str, ...]:
        return (PREHISTORIC_POWER_TEXT,)


def evolution_preventers(state: GameState) -> tuple[tuple[int, int, str], ...]:
    """今はたらいている、ポケモンを進化できなくする特殊能力（［げんしのちから］）の (持ち主, 持つポケモンの番号, ``PowerKey`` の文字列)（v0.47。公開の問い合わせ）。空なら
    （ほかの条件しだいで）進化できる。状態を変えず、乱数を使わない。"""
    return tuple((owner, holder.pokemon_id, str(key)) for owner, holder, key, _ in continuous_powers(state, PreventEvolution))


# どくのダメージに受けるダメージを変える特殊能力を当てはめるか（KA1。``procedures.pokemon_check_poison`` が止める。停止コードは ``procedures.POISON_RECEIVED_POWER``）


def poison_received_power_problem(state: GameState, owner: int, pokemon: PokemonInPlay, amount: int) -> str | None:
    """ポケモンチェックのどくのダメージ ``amount`` を ``pokemon`` が受けるとき、受けるダメージを変える常にはたらく特殊能力（カブトアーマー・なぞのかべ）を当てはめると
    量が変わるなら、止める理由（KA1。v0.47）。変わらない（なぞのかべのしきい値より小さい）・当てはまる特殊能力がないなら None。ふしぎなバリアー（「たねポケモンから」）は、
    どくがポケモンから受けるダメージではない（GR-2000-P319-HP-AND-DAMAGE）ので当てはめない（v0.46）。"""
    for holder_owner, holder, key, effect in continuous_powers(state):
        if holder is not pokemon:
            continue
        modifier = effect.poison_damage_modifier(state, holder, _power_label(state, holder, key))
        if modifier is not None and modifier.apply(amount, state.rules.damage_per_counter) != amount:
            return (f"ポケモン {pokemon.pokemon_id} の {modifier.label} を、ポケモンチェックのどくのダメージ {amount}（ワザによるダメージではない。p.321・p.322）に"
                    "当てはめるか（説明の「受けるダメージ」がどくのダメージを含むか）は決められないので扱わない（KA1）")
    return None


# --- 見えないカードを見る・入れかえる特殊能力（v0.47。docs 4 章）

PEEK_TEXT = ("どちらかの山札の1番上、またはどちらかのサイドカード1枚、または相手の手札1枚を、自分の番に1回だけ見ることができる。見たカードは元の場所に戻す。"
             "「ねむり・マヒ・こんらん」状態の時、この力は使えない。")


def peek_targets(state: GameState, player: int) -> tuple[tuple, ...]:
    """［スパイ］で見られるカードの位置（v0.47。並び: 自分の山札の一番上 → 相手の山札の一番上 → 自分のサイド（位置の順）→ 相手のサイド → 相手の手札（位置の順））。
    (``"deck"``, 持ち主)・(``"prize"``, 持ち主, 位置)・(``"hand"``, 持ち主, 位置)。位置だけで、カードの uid・内容を含まない（見る前に内容を漏らさない）。"""
    opponent = 1 - player
    targets: list[tuple] = []
    for owner in (player, opponent):
        if state.players[owner].deck:
            targets.append(("deck", owner))
    for owner in (player, opponent):
        targets.extend(("prize", owner, i) for i in range(len(state.players[owner].prizes)))
    targets.extend(("hand", opponent, i) for i in range(len(state.players[opponent].hand)))
    return tuple(targets)


@dataclass(frozen=True)
class PeekCard(PowerEffect):
    """どちらかの山札の 1 番上、またはどちらかのサイド 1 枚、または相手の手札 1 枚を、自分の番に 1 回だけ見ることができる。見たカードは元の場所に戻す。ねむり・マヒ・
    こんらん状態の時、この力は使えない（v0.47。マンキー（PMCG2-028）の［スパイ］。kyuura の印刷の文面）。

    - 宣言して使う。自分の番に 1 回（``once_per_turn``。宣言のときに記録する。v0.42）。ねむり・マヒ・こんらんのこのカードは使えない
    - 宣言のあと決定 ``PEEK_CARD``（使ったプレイヤー。選べるものは ``peek_targets`` の位置の番号。``context`` の ``"targets"``。1 つ）で、見るカードを位置で選ぶ。
      サイド・相手の手札は裏向き・見えないカードなので、位置で選び、選ぶ前に内容を見せない。相手の手札の 1 枚は、使ったプレイヤーが位置で選ぶ（日本語の文面は
      無作為に選ぶとは書かない。英語版の「random」は持ち込まない）
    - 見る（``zones.look_at_card``。ログ ``look_at_card`` の ``card`` は見たプレイヤーにだけ見える）。カードは動かさない（サイド・山札・手札の並びは変わらない）。
      相手には見せない（「見る」で「見せる」ではない）
    - 見られるカードがない（両方の山札・サイド・相手の手札が 0 枚）ときは決められない（v0.43 の PW3 と同じ問い。宣言の前に止める）
    """

    implementation_id = "peek_card"
    once_per_turn: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "見えないカードを 1 枚見る特殊能力", (PEEK_TEXT,))

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)
        require_power_not_used(state, use)
        if not peek_targets(state, use.player):
            raise _power_zero_cards("見られるカード（山札の一番上・サイド・相手の手札）がない")

    def resolve(self, state: GameState, use: PowerUse) -> None:
        targets = peek_targets(state, use.player)
        push_power_decision(state, use, kind=PEEK_CARD, player=use.player, options=range(len(targets)), context=(("targets", targets),))

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        target = decision.context_value("targets")[choices[0]]
        if target != peek_targets(state, use.player)[choices[0]]:
            raise RuntimeError(f"［スパイ］で選んだ位置 {target} が、今の見られるカードの位置と違う（決定を待つ間は場が変わらない。エンジンの不具合）")
        zone, owner = target[0], target[1]
        look_at_card(state, use.player, owner, zone, 0 if zone == "deck" else target[2], power=str(use.key))

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        targets = peek_targets(state, use.player)
        problems = _power_decision_form(decision, use, kind=PEEK_CARD, choices=(1, 1), options=range(len(targets)))
        if tuple(decision.context_value("targets", ())) != targets:
            problems.append(f"特殊能力 {use.key} の決定の見られるカードの位置 {decision.context_value('targets', ())} が {targets} ではない")
        return problems


TRICKERY_TEXT = ("自分の番ごとに1回使える。自分のサイドカードから1枚を選び、自分の山札の一番上のカードと入れ替える。「ねむり・マヒ・こんらん」状態の時、この力は使えない。")


@dataclass(frozen=True)
class SwapPrizeWithDeckTop(PowerEffect):
    """自分の番ごとに 1 回使える。自分のサイドから 1 枚を選び、自分の山札の一番上のカードと入れ替える。ねむり・マヒ・こんらん状態の時、この力は使えない（v0.47。
    コラッタ（PMCG4-045。ロケット団）の［わるふざけ］。kyuura の印刷の文面）。

    - 宣言して使う。自分の番ごとに 1 回（``once_per_turn``）。ねむり・マヒ・こんらんのこのカードは使えない
    - 宣言のあと決定 ``SELECT_PRIZE_CARD``（使ったプレイヤー。選べるものは自分のサイドの位置。1 つ）。サイドは裏向きなので、位置で選び、選ぶ前に内容を見せない
    - 入れかえる（``zones.swap_prize_with_deck_top``）。どちらのカードも見ない・見せない（説明に「見る」がない）。サイドの枚数・位置、山札の枚数・ほかのカードの並び
      は変わらない。山札は切らない（説明にない）
    - サイドが 0 枚、または山札が 0 枚（一番上のカードがない）のときは、使えるか（使ったことになるか）が決められない（v0.43 の PW3 と同じ問い。宣言の前に止める）
    """

    implementation_id = "swap_prize_with_deck_top"
    once_per_turn: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "サイドと山札の一番上を入れかえる特殊能力", (TRICKERY_TEXT,))

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)
        require_power_not_used(state, use)
        p = state.players[use.player]
        if not p.prizes or not p.deck:
            raise _power_zero_cards(f"サイド {len(p.prizes)} 枚・山札 {len(p.deck)} 枚で、入れかえるカードがない")

    def resolve(self, state: GameState, use: PowerUse) -> None:
        push_power_decision(state, use, kind=SELECT_PRIZE_CARD, player=use.player, options=range(len(state.players[use.player].prizes)))

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        swap_prize_with_deck_top(state, use.player, choices[0], power=str(use.key))

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        return _power_decision_form(decision, use, kind=SELECT_PRIZE_CARD, choices=(1, 1), options=range(len(state.players[use.player].prizes)))


# --- ワザ（v0.47）

PROPHECY_TEXT = "自分または相手の山札の上から{n}枚まで見て、好きな順番に入れ替えて、もとの山札の上にもどす。"


@dataclass(frozen=True)
class ArrangeDeckTopEffect(AttackEffect):
    """自分または相手の山札の上から ``max_cards`` 枚まで見て、好きな順番に入れ替えて、もとの山札の上にもどす（v0.47。スリーパー（PMCG3-032）の「みらいよち」。kyuura の
    印刷の文面）。ダメージの目安の数字はない。要素 ``ArrangeDeckTop``。

    - 選ぶのはワザを使ったプレイヤー。決定 ``SELECT_DECK_OWNER``（見る山札の持ち主。選べるものは自分・相手のプレイヤー）→ ``SELECT_LOOK_COUNT``（見る枚数。0〜min(``max_cards``,
      その山札の枚数)）→ 見る（ログ ``look_at_deck_top`` の ``cards`` は見たプレイヤーにだけ見える）→ ``ARRANGE_DECK_TOP``（2 枚以上なら、見たカードの新しい並び（上から
      順）。1 枚なら決定はない）→ もどす（ログ ``arrange_deck_top``。並びは見たプレイヤーにだけ見える）。見た部分より下の山札の並びは変えない。山札は切らない
    - 選んだ山札が 0 枚なら、見るカードがない（p.309。ログ ``look_at_deck_top_none``）。山札があるとき 0 枚を選べるか（「3枚まで」が 0 を含むか）は決められない
      （v0.39 の GS1 と同じ問い「ワザの説明の「最大N」が 0 を含むか」。v0.44 のてじなと同じく、答えのときに止める。先読みは 0 を試さない）
    - 相手の山札を見ても、相手に見せない（「見て」で「見せる」ではない）。山札は裏向きなので、見る前に内容を見せない（選べるものはプレイヤーと枚数だけ）
    """

    max_cards: int
    implementation_id = "arrange_deck_top"

    def __post_init__(self) -> None:
        if type(self.max_cards) is not int or self.max_cards < 1:
            raise ValueError(f"見る枚数の最大は 1 以上（{self.max_cards!r}）")

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "山札の上を見て並べかえるワザ", damage="none") + _check_exact_text(
            attack, "山札の上を見て並べかえるワザ", (PROPHECY_TEXT.format(n=self.max_cards),))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        label = _label(state, use)
        if decision.kind == SELECT_DECK_OWNER:
            return _decision_form(decision, label, kind=SELECT_DECK_OWNER, player=use.player, choices=(1, 1), options=(use.player, 1 - use.player))
        owner = decision.context_value("owner")
        if owner not in (0, 1):
            return [f"{label} の決定 {decision.kind} の山札の持ち主 {owner!r} が正しくない"]
        deck = state.players[owner].deck
        if decision.kind == SELECT_LOOK_COUNT:
            return _decision_form(decision, label, kind=SELECT_LOOK_COUNT, player=use.player, choices=(1, 1), options=range(min(self.max_cards, len(deck)) + 1))
        count = len(decision.options)
        return _decision_form(decision, label, kind=ARRANGE_DECK_TOP, player=use.player, choices=(count, count), options=deck[:count]) + (
            [] if count >= 2 else [f"{label} の並べかえの決定の見たカードが {count} 枚（2 枚以上のときだけ出す）"])


SURPRISE_TEXT = "相手の手札から、おもてを見ないで1枚選び、そのカードを見る。その後、そのカードを相手の山札にもどさせ、その山札をよく切る。"


@dataclass(frozen=True)
class LookOpponentHandCardToDeck(AttackEffect):
    """相手の手札から、おもてを見ないで 1 枚選び、そのカードを見る。その後、そのカードを相手の山札にもどさせ、その山札をよく切る（v0.47。マチスのイーブイ（PMCG5-062）の
    「おどろかす」。kyuura の印刷の文面）。ダメージの目安の数字はない。要素 ``LookHandCardToDeck``。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_HAND_CARD``。選べるものは相手の手札の位置。1 つ）。おもてを見ないで選ぶので、選ぶ前にカードの内容を見せない（位置で
      選ぶ。相手の手札全体を見せない）。日本語の文面は無作為に選ぶとは書かない（英語版の「random」は持ち込まない）
    - 選んだカードを見る（ログ ``look_at_card``。見たプレイヤーと持ち主にだけ見える）→ 相手（持ち主）がそのカードを山札にもどす（``zones.return_hand_cards_to_deck``。
      ログ ``hand_to_deck``）→ その山札を切る（1 回）。この順番を変えない
    - 相手の対戦ポケモンではなく相手の手札・山札への効果なので、「ワザをうけない」状態・「とうめい」は評価しない
    - 相手の手札が 0 枚なら決められない（v0.44 の FC1 と同じ問い「説明が決まった枚数のカードを選ばせるとき、選べるカードが足りない」。0 枚を選んで山札を切るのか、
      その内容を処理しないのか。宣言の前に止める）
    """

    implementation_id = "look_opponent_hand_card_to_deck"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "相手の手札を見て山札にもどさせるワザ", damage="none") + _check_exact_text(attack, "相手の手札を見て山札にもどさせるワザ", (SURPRISE_TEXT,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        opponent = 1 - use.player
        problems = _decision_form(decision, _label(state, use), kind=SELECT_HAND_CARD, player=use.player, choices=(1, 1),
                                  options=range(len(state.players[opponent].hand)))
        if decision.context_value("owner") != opponent:
            problems.append(f"{_label(state, use)} の決定の手札の持ち主 {decision.context_value('owner')!r} が相手 {opponent} ではない")
        return problems


HEADACHE_TEXT = "次の相手の番の終わりまで、相手プレイヤーはトレーナーカードを使うことができない。"
HIGH_VOLTAGE_TEXT = "コインを投げて「おもて」なら、次の相手の番が終わるまで、相手プレイヤーは「トレーナーカード」を使うことができない。"


@dataclass(frozen=True)
class LockOpponentTrainersNextTurn(AttackEffect):
    """次の相手の番の終わりまで、相手プレイヤーはトレーナーカードを使うことができない（v0.47。コダック（PMCG3-010。化石の秘密）の「ずつう」。kyuura の印刷の文面）。
    ダメージの目安の数字はない。要素 ``LockOpponentTrainers``（プレイヤーに与える期限のある禁止 ``state.TrainerUseLock``。場のポケモンに与える効果ではないので、
    「ワザをうけない」状態・「とうめい」は評価しない）。"""

    implementation_id = "lock_opponent_trainers_next_turn"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "相手のトレーナーの使用を禁止するワザ", damage="none") + _check_exact_text(attack, "相手のトレーナーの使用を禁止するワザ", (HEADACHE_TEXT,))

    def lock_terms(self) -> tuple[bool]:
        """不変条件（``engine._trainer_lock_problems``）が照らす値: (コインの「おもて」で与えるか,)。"""
        return (False,)


@dataclass(frozen=True)
class DamageThenLockOpponentTrainersOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、次の相手の番が終わるまで、相手プレイヤーはトレーナーカードを使うことができない
    （v0.47。マチスのサンダース（PMCG5-042）の「こうしゅうは」。kyuura の印刷の文面）。

    - 要素 ``Damage`` → ``LockOpponentTrainers(local_coin=HEADS)``。コインはダメージのあと（説明の順）。禁止は相手プレイヤーへの効果なので、相手の対戦ポケモンが
      「ダメージを受けない」「ワザをうけない」状態・「とうめい」でもコインを投げ、「おもて」なら与える（コインが決める要素は相手の対戦ポケモンへの要素ではない。v0.34 の
      ``void_coin_question`` に当たらない）。相手の対戦ポケモンがこのダメージできぜつしても与える（対象はプレイヤー）
    """

    implementation_id = "damage_then_lock_opponent_trainers_on_heads"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "ダメージとコインで相手のトレーナーの使用を禁止するワザ", damage="fixed") + _check_exact_text(
            attack, "ダメージとコインで相手のトレーナーの使用を禁止するワザ", (HIGH_VOLTAGE_TEXT,))

    def lock_terms(self) -> tuple[bool]:
        return (True,)


THUNDER_FLARE_TEXT = "自分にのっているダメージカウンターの数×{per}のダメージを追加する。その後、コインを投げて「うら」なら、自分にも{n}ダメージ。"


@dataclass(frozen=True)
class DamagePlusOwnCountersThenSelfDamageOnTails(AttackEffect):
    """ダメージの目安の数字 + 自分にのっているダメージカウンターの数 × ``per`` のダメージ。その後、コインを投げて「うら」なら、自分にも ``self_damage`` ダメージ（v0.47。
    マチスのサンダース（PMCG5-042）の「いかりのサンダー」。kyuura の印刷の文面）。

    - 要素は v0.46 の「いかり」（``PlusOwnCounters``）と v0.2f の「でんげき」（``Damage(SELF, Fixed, local_gate=TAILS)``）の組み合わせ。数えるのはダメージを計算する時の
      自分のカウンター（p.321 の 1 段階。最終ダメージに直接足さない）。コインは相手へのダメージのあと（説明の「その後」）
    """

    per: int
    self_damage: int
    implementation_id = "damage_plus_own_counters_then_self_damage_on_tails"

    def __post_init__(self) -> None:
        _positive_tens(self.per, "カウンター 1 個あたりのダメージ")
        _positive_tens(self.self_damage, "自分へのダメージ")

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "自分のカウンターで追加ダメージを与え、コインで自分にもダメージのワザ", damage="modified", modifier="+") + _check_exact_text(
            attack, "自分のカウンターで追加ダメージを与え、コインで自分にもダメージのワザ", (THUNDER_FLARE_TEXT.format(per=self.per, n=self.self_damage),))

    def damage_profile(self, state: GameState, use: AttackUse) -> DamageProfile:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = attack_of(state, use.key)  # v0.49: ワザを印刷したカード（use.key）
        base = attack.damage + attacker.damage // state.rules.damage_per_counter * self.per
        return DamageProfile(opponent=(base,), self_damage=(0, self.self_damage))


def trainer_use_blockers(state: GameState, player: int) -> tuple[tuple, ...]:
    """プレイヤー ``player`` が今トレーナーカードを使えない理由（v0.47。公開の問い合わせ）: はたらいている常にはたらく特殊能力（［アレルギーかふん］。v0.46 の
    ``trainer_lock_sources``。(``"power"``, 持ち主, 持つポケモンの番号, ``PowerKey`` の文字列)）と、``player`` に与えた期限のある禁止（ずつう・こうしゅうは。
    (``"lock"``, 与えたプレイヤー, ワザ, 消える番)）。空なら（ほかの条件しだいで）使える。2 つは別の記録で、それぞれの期間で判定する。状態を変えず、乱数を使わない。"""
    found: list[tuple] = [("power", owner, pid, key) for owner, pid, key in trainer_lock_sources(state)]
    found.extend(("lock", lock.source_player, lock.effect, lock.expires_turn) for lock in state.trainer_locks if lock.player == player)
    return tuple(found)


# ---------------------------------------------------------------- v0.48（docs/effective-pokemon-properties-v0.48.md）。場のポケモンの「今有効な最大HP・タイプ（色）・
# 弱点・抵抗力」を一か所で求める処理と、それを変える 7 枚の効果（ポリゴン 2 枚・モルフォン・ナツメのゴース／ゴースト／ゲンガー・キョウのメタモン）。処理に使う文面はどれも
# kyuura の印刷の文面（7 枚とも kyuura に最新の説明・エラッタ・裁定の記録がない）
#
# 印刷の定義（``GameState.printed_def``）・場での役割の定義（v0.47。``GameState.card_def`` が場にいるあいだ返す）は書きかえない。今有効な値は、そのつど、カードの定義
# （``card_def``。場での役割を含む）に、今の効果（ワザによる持続する効果・はたらいている常にはたらく特殊能力・特殊能力で色を変えた記録）を当てはめて求める。値を
# 状態・ログに書き写さない（進化・入れ替え・きぜつ・特殊状態・かがくへんかガス・保存と復元のあとも、その時点の場から同じ答えになる）。

COLORS: tuple[EnergyType, ...] = tuple(EnergyType)  # 色を選ぶ決定（``SELECT_COLOR``）の選べるもの i は COLORS[i]
# 「好きな「色」…ただし「無色」にはできない」「無色以外の好きな「色」」（テクスチャー1・2）。色は 2000.02.14 版の公式ルールのタイプ（p.321 が悪エネルギー・鋼エネルギーを
# 例に挙げる。kyuura rule_history.json の NEO-2000-OFFICIAL-RULES）のうち無色以外の 8 つ（実装上の判断。docs 3 章）
NON_COLORLESS_CHOICES: tuple[int, ...] = tuple(i for i, color in enumerate(COLORS) if color is not EnergyType.COLORLESS)

# VS1（docs 4 章）: モルフォンの［へんしょく］で変えた色が、いつまで続くか
SHIFT_DURATION_CODE = "UNRESOLVED_SHIFT_COLOR_DURATION"
SHIFT_DURATION_REASON = (
    "モルフォンの［へんしょく］で変えた色が、使った番のあと（次の番以後）・バトル場からベンチにもどったあと・この力が消えている（ねむり・マヒ・こんらん状態・"
    "かがくへんかガス）あいだも続くかは、印刷の文面（効果の期限を書かない）・kyuura の記録（持続する効果の規定 GR-2000-P322-PERSISTENT-EFFECTS はワザの効果のもの。"
    "v0.8 の G27 は物理的なカード・カウンターの結果だけ）から決められず、変えた色と印刷の色で結果が変わる（VS1）"
)
# PG1（docs 3 章）: 弱点・抵抗力のないポケモンの弱点・抵抗力を「好きな色にかえる」
ABSENT_WEAKNESS_RESISTANCE_CODE = "UNRESOLVED_CHANGE_ABSENT_WEAKNESS_RESISTANCE"
ABSENT_WEAKNESS_RESISTANCE_REASON = (
    "弱点（抵抗力）を持たないポケモンの弱点（抵抗力）を「好きな「色」にかえる」効果（ポリゴンの「テクスチャー1」「テクスチャー2」）で、弱点（抵抗力）を新しく持たせる"
    "のか、何もしないのか（抵抗力なら引く数も）は、印刷の文面・kyuura の記録から決められない（PG1。英語版の「If the Defending Pokémon has a Weakness」は持ち込まない）"
)
# MH1（docs 5 章）: ダメージ以外の原因で最大HPが下がり、のっているダメージ以下になる
MAX_HP_DROP_CODE = "UNRESOLVED_MAX_HP_DROP"
MAX_HP_DROP_REASON = (
    "場のポケモンの最大HPが、ダメージ以外の原因（ついている「超」エネルギーカードが減る・［ガスのからだ］がかがくへんかガスで消える・「きょだいか」の効果が消える）で"
    "のっているダメージ以下に下がるとき、きぜつするか・いつきぜつの判定をするかは、ワザのあとのきぜつの判定（p.309・GR-2000-P323-KNOCKOUT）のほかに記録がなく決められない"
    "（MH1。v0.4a の H1 は進化のときの問いで、ここには広げない）"
)
# ワザの途中の決定を待つあいだに、ワザの効果で最大HPが下がってのっているダメージ以下になる（ワザのあとのきぜつの判定で処理するが、待つあいだの状態をエンジンが表せない。
# 今の対応カードでは起こらない。エンジンの未対応。研究の対応表の停止コードに入れない）
MAX_HP_DROP_DURING_ATTACK_CODE = "UNSUPPORTED_MAX_HP_DROP_DURING_ATTACK"


GASEOUS_FORM_TEXT = ("このカードの最大HPは、このカードについている「{type}」エネルギーカードの数×{per}ぶん、大きいものになる。このカードが「ねむり・マヒ・こんらん」状態の"
                     "時でも、この力は必ずはたらく。")


@dataclass(frozen=True)
class MaxHpPerAttachedEnergyCards(ContinuousPower):
    """このカードの最大HPは、このカードについている ``energy_type`` エネルギーカードの数 × ``per`` ぶん、大きいものになる。ねむり・マヒ・こんらん状態の時でも、この力は
    必ずはたらく（v0.48。ナツメのゴース（PMCG6-049）の［ガスのからだ］。kyuura の印刷の文面）。

    - 常にはたらく特殊能力（v0.46 の ``ContinuousPower``。宣言しない）。場（バトル場・ベンチ）のどこでもはたらく。説明のとおり特殊状態では消えない（``blocked_by_status`` が
      偽）。かがくへんかガスでは消える（G4。抑止は ``continuous.suppressors_of`` で別に判定する）
    - 数えるのは、ついている基本エネルギーカードのうち、カードが ``energy_type`` のもの（カードの枚数。エナジーバーンなどで供給するエネルギーのタイプが変わっても、
      カードの種類で数える。供給するエネルギーの個数（``state.energy_types``）とは別）
    - 最大HP（``max_hp``）はそのつど求める。エネルギーカードをつける・はがす・つけかえる・かがくへんかガスがはたらく／消える・進化する（いちばん上のカードが変わる）と
      変わる。下がってのっているダメージ以下になる場合は MH1（ワザのあとのきぜつの判定で処理する場合を除く。``max_hp_drops``）
    """

    energy_type: EnergyType
    per: int
    implementation_id = "max_hp_per_attached_energy_cards"
    blocked_by_status: ClassVar[bool] = False
    what: ClassVar[str] = "ついているエネルギーカードの数で最大HPが大きくなる特殊能力"

    def __post_init__(self) -> None:
        _positive_tens(self.per, "エネルギーカード 1 枚あたりの最大HP")

    def texts(self) -> tuple[str, ...]:
        return (GASEOUS_FORM_TEXT.format(type=self.energy_type.ja, per=self.per),)

    def hp_bonus(self, state: GameState, pokemon: PokemonInPlay) -> int:
        cards = [uid for uid in pokemon.energy if state.card_def(uid).is_basic_energy and state.card_def(uid).provides is self.energy_type]
        return len(cards) * self.per


def _own_working_continuous(state: GameState, pokemon: PokemonInPlay, kind: type, *, card: int | None = None) -> list[tuple[PowerKey, ContinuousPower]]:
    """``pokemon`` のいちばん上のカード（``card`` を渡したら、そのカードがいちばん上だとしたとき。進化の確かめ）の常にはたらく特殊能力（``kind`` の型）のうち、今はたらいて
    いるもの（v0.48）。場所・特殊状態の条件（``ContinuousPower.located``・``status_allows``）とかがくへんかガス（``continuous.suppressors_of``）は ``continuous_powers`` と同じ
    判定。``card`` を渡したとき、進化したポケモンは特殊状態が消える（p.310）ので、特殊状態の条件は見ない。"""
    slots = powers_of(state, pokemon) if card is None else card_power_slots(state, card)  # v0.49: 今持つ特殊能力（重ねるカードなら、そのカードの特殊能力）
    if not slots:
        return []
    from .continuous import suppressors_of  # continuous.py は effects.py を読み込むので、使うときに読み込む

    found = []
    for slot in slots:
        power, effect = slot.power, slot.effect
        if not isinstance(effect, kind):
            continue
        if effect.location != CONTINUOUS_IN_PLAY:
            located = state.find_pokemon(pokemon.pokemon_id)
            if located is None or not effect.located(state, located[0], located[1]):
                continue
        if card is None and not effect.status_allows(pokemon):
            continue
        if suppressors_of(state, power):
            continue
        found.append((slot.key, effect))
    return found


def max_hp(state: GameState, pokemon: PokemonInPlay, *, card: int | None = None) -> int:
    """場のポケモン ``pokemon`` の今有効な最大HP（v0.48。公開の問い合わせ。HP を使う処理はどれもこれを使う）。

    - もとの値はカードの定義の HP（``GameState.card_def``。場での役割（v0.47）を含む。いちばん上のカード）
    - 「きょだいか」の効果（``persistent.max_hp_set``。ワザによる持続する効果）がはたらいていれば、その数（「「80」になる」）
    - はたらいている［ガスのからだ］（``MaxHpPerAttachedEnergyCards``）の分だけ大きくなる
    - 2 つが同時にはたらくポケモンは今の写しにない（その数にするのと足すのの順番は決まらない）ので ``RuntimeError``
    ``card`` を渡したら、そのカードがいちばん上だとしたときの最大HP（進化の確かめ。H1・``evolution_hp``。進化すると持続する効果は消えるので、常にはたらく特殊能力だけを
    当てはめる）。状態を変えず、乱数を使わない。"""
    definition = form_def(state, pokemon) if card is None else state.card_def(card)  # v0.49: 今の姿のカード（［へんしん］・「ばける」）
    if definition.hp is None:
        raise RuntimeError(f"場のポケモン {pokemon.pokemon_id} のカード {definition.id} に HP がない（エンジンの不具合）")
    fixed = max_hp_set(pokemon) if card is None else None
    bonus = sum(effect.hp_bonus(state, pokemon) for _, effect in _own_working_continuous(state, pokemon, MaxHpPerAttachedEnergyCards, card=card))
    if fixed is not None and bonus:
        raise RuntimeError(f"場のポケモン {pokemon.pokemon_id} の最大HPを、その数にする効果と大きくする特殊能力が同時に変える（今の写しでは起こらない）")
    return fixed.amount if fixed is not None else definition.hp + bonus


def knocked_by_hp(state: GameState, pokemon: PokemonInPlay) -> bool:
    """のっているダメージが今有効な最大HP以上か（v0.48。HP 以上のダメージを受けた。``max_hp``）。"""
    return pokemon.damage >= max_hp(state, pokemon)


def weakness_of(state: GameState, pokemon: PokemonInPlay) -> EnergyType | None:
    """場のポケモンの今有効な弱点の色（v0.48）。「テクスチャー1」の効果（``persistent.weakness_change``）があればその色、なければカードの定義の弱点。倍数は変えない。"""
    change = weakness_change(pokemon)
    return change.color if change is not None else form_def(state, pokemon).weakness  # v0.49: 今の姿のカード


def resistance_of(state: GameState, pokemon: PokemonInPlay) -> tuple[EnergyType | None, int]:
    """場のポケモンの今有効な抵抗力（色, 数）（v0.48）。「テクスチャー2」の効果（``persistent.resistance_change``）があれば色だけ変わる（数はカードの定義の値のまま）。"""
    definition = form_def(state, pokemon)  # v0.49: 今の姿のカード
    change = resistance_change(pokemon)
    return (change.color if change is not None else definition.resistance), definition.resistance_value


def type_shift_power(state: GameState, pokemon: PokemonInPlay) -> tuple[PowerKey, ShiftColor] | None:
    """``pokemon`` が今持つ［へんしょく］（``ShiftColor``。v0.49 から ``powers_of``。「ばける」でのせたカードの特殊能力を含む）。なければ None。"""
    for slot in powers_of(state, pokemon):
        if isinstance(slot.effect, ShiftColor):
            return slot.key, slot.effect
    return None


def type_shift_power_works(state: GameState, pokemon: PokemonInPlay) -> bool:
    """［へんしょく］が今消えていないか（v0.48）。説明の「「ねむり・マヒ・こんらん」状態の時、この力は消える」と、かがくへんかガス（G4。``continuous.suppressors_of``）。"""
    found = type_shift_power(state, pokemon)
    if found is None or _asleep_paralyzed_or_confused(pokemon):
        return False
    from .continuous import suppressors_of

    return not suppressors_of(state, state.definitions[found[0].card_id].powers[found[0].power_index])  # v0.49: 特殊能力を印刷したカード


def type_shift_determined(state: GameState, pokemon: PokemonInPlay) -> bool:
    """特殊能力で変えた色（``PokemonInPlay.type_shift``）が今も有効と決まっているか（v0.48）。決まっているのは、使った番のうちで、使ってからベンチにもどっておらず、
    いちばん上のカードが使ったときと同じで、［へんしょく］が今消えていない（ねむり・マヒ・こんらん・かがくへんかガスでない）ときだけ。ほかは VS1（``type_readings``）。"""
    shift = pokemon.type_shift
    return (shift is not None and shift.turn == state.turn_number and not shift.returned_to_bench and shift.source_card == pokemon.card
            and type_shift_power_works(state, pokemon))


def type_readings(state: GameState, pokemon: PokemonInPlay) -> tuple[EnergyType | None, ...]:
    """場のポケモンの今有効な色（タイプ）の読み方（v0.48。公開の問い合わせ）。ふつうは 1 つ（カードの定義のタイプ。場での役割のポケモンは None）。

    - ［へんしょく］で変えた色（``type_shift``）が決まって有効（``type_shift_determined``）なら、その色だけ
    - 変えた記録はあるが有効か決まらない（VS1。使った番のあと・ベンチにもどったあと・この力が消えている）なら、(変えた色, カードの定義のタイプ) の 2 つ。この値を使う処理は、
      2 つの読み方で結果が変わるときだけ止める（変わらなければ止めない）。どちらか 1 つを選んで続けない
    """
    printed = form_def(state, pokemon).pokemon_type  # v0.49: 今の姿のカードのタイプ
    shift = pokemon.type_shift
    if shift is None:
        return (printed,)
    if type_shift_determined(state, pokemon) or shift.color is printed:
        return (shift.color,)
    return (shift.color, printed)


def definition_views(state: GameState, pokemon: PokemonInPlay) -> tuple[CardDefinition, ...]:
    """ダメージの計算などに渡す、今有効な値を入れたカードの定義（v0.48）。色の読み方（``type_readings``）ごとに 1 つ。最大HP・弱点・抵抗力・色がカードの定義と同じなら、
    カードの定義そのもの（共有する定義を書きかえず、違うときは ``dataclasses.replace`` の新しい値。状態に持たない）。"""
    from dataclasses import replace

    base = form_def(state, pokemon)  # v0.49: 今の姿のカード（［へんしん］・「ばける」）
    hp = max_hp(state, pokemon)
    weakness = weakness_of(state, pokemon)
    resistance, _ = resistance_of(state, pokemon)
    views = []
    for color in type_readings(state, pokemon):
        if (hp, color, weakness, resistance) == (base.hp, base.pokemon_type, base.weakness, base.resistance):
            views.append(base)
        else:
            views.append(replace(base, hp=hp, pokemon_type=color, weakness=weakness, resistance=resistance))
    return tuple(views)


def shift_duration_error(pokemon: PokemonInPlay, detail: str) -> UnsupportedError:
    """VS1 の止める理由（v0.48）。解決の基盤の問い（``shift_color_duration``）と、ワザの外の確かめ（特殊能力の使用など）で同じ文。"""
    shift = pokemon.type_shift
    what = f"ポケモン {pokemon.pokemon_id} の［へんしょく］の色 {shift.color.ja}（{shift.turn} 番）" if shift is not None else f"ポケモン {pokemon.pokemon_id}"
    return UnsupportedError(SHIFT_DURATION_CODE, f"{what}。{detail}: {SHIFT_DURATION_REASON}")


def same_for_type_readings(state: GameState, pokemons: Iterable[PokemonInPlay], compute) -> Any:
    """``pokemons`` の色の読み方（``type_readings``）のすべての組で ``compute(views)``（``views`` は ``pokemons`` の順の ``definition_views`` の 1 つずつ）を求め、どれも同じなら
    その値を返す（v0.48）。読み方で結果が変わるなら ``TypeReadingsDiffer``（呼ぶ側が VS1 の止める処理にする）。どのポケモンも読み方が 1 つなら 1 回だけ求める（v0.47 までと
    同じ計算）。計算の順番の決定が要る（``damage.DamageOrderRequired``）のも結果の 1 つとして比べ、どの読み方でも同じならそのまま投げる。"""
    from itertools import product

    from .damage import DamageOrderRequired

    pokemons = tuple(pokemons)
    choices = [definition_views(state, p) for p in pokemons]
    if all(len(c) == 1 for c in choices):
        return compute(tuple(c[0] for c in choices))
    outcomes = []
    for combo in product(*choices):
        try:
            outcomes.append(("value", compute(combo)))
        except DamageOrderRequired as need:
            outcomes.append(("order", need.step, tuple(m.label for m in need.modifiers)))
    if any(outcome != outcomes[0] for outcome in outcomes[1:]):
        raise TypeReadingsDiffer([p for p, c in zip(pokemons, choices) if len(c) > 1])
    if outcomes[0][0] == "order":
        return compute(tuple(c[0] for c in choices))  # どの読み方でも同じ段階の順番の決定が要る（呼ぶ側が決定を出す）
    return outcomes[0][1]


class TypeReadingsDiffer(Exception):
    """色の読み方（VS1）で結果が変わった（v0.48。``same_for_type_readings``）。``pokemons`` は読み方が 2 つある場のポケモン。"""

    def __init__(self, pokemons: list[PokemonInPlay]):
        super().__init__(f"色の読み方で結果が変わる: {[p.pokemon_id for p in pokemons]}")
        self.pokemons = pokemons


def single_type(state: GameState, pokemon: PokemonInPlay, detail: str) -> EnergyType | None:
    """色の読み方が 1 つならその色。2 つなら VS1 で止める（v0.48。読み方ごとに結果を比べられない処理が使う。今の対応カードでは、読み方ごとに比べる処理だけが使う）。"""
    readings = type_readings(state, pokemon)
    if len(readings) > 1:
        raise shift_duration_error(pokemon, detail)
    return readings[0]


def evolution_hp(state: GameState, pokemon: PokemonInPlay, card: int) -> int:
    """``pokemon`` に ``card`` を重ねて進化させたあとの最大HP（v0.48。v0.4a の H1 の確かめ。進化すると持続する効果・特殊状態は消えるので、重ねるカードの HP と、そのカードの
    はたらく常にはたらく特殊能力だけ）。"""
    return max_hp(state, pokemon, card=card)


def max_hp_drops(before: GameState, after: GameState) -> list[tuple[int, PokemonInPlay, int, int]]:
    """``before`` から ``after`` までのあいだに、今有効な最大HPが下がって、のっているダメージ以下になった場のポケモン（持ち主, ポケモン, 前の最大HP, 今の最大HP）（v0.48。MH1）。

    同じ場のポケモンの番号で比べる（``before`` にいなかったポケモン・場をはなれたポケモンは数えない）。ダメージを受けて HP 以上になったポケモン（最大HPは下がっていない）は
    数えない（ワザのあとのきぜつの判定・こんじょうなどの既存の処理）。状態を変えず、乱数を使わない。"""
    previous = {pokemon.pokemon_id: max_hp(before, pokemon) for player in before.players for pokemon in player.in_play()}
    found = []
    for owner, player in enumerate(after.players):
        for pokemon in player.in_play():
            old = previous.get(pokemon.pokemon_id)
            if old is None:
                continue
            hp = max_hp(after, pokemon)
            if hp < old and pokemon.damage >= hp:
                found.append((owner, pokemon, old, hp))
    return found


def max_hp_drop_error(drops: list[tuple[int, PokemonInPlay, int, int]], *, during_attack: bool = False) -> UnsupportedError:
    """MH1 の止める理由（v0.48）。``during_attack`` なら、ワザの途中の決定を待つあいだの場合（エンジンの未対応のコード）。"""
    detail = "・".join(f"プレイヤー {owner} のポケモン {pokemon.pokemon_id}（最大HP {old} → {hp}、ダメージ {pokemon.damage}）" for owner, pokemon, old, hp in drops)
    if during_attack:
        return UnsupportedError(MAX_HP_DROP_DURING_ATTACK_CODE,
                                f"{detail}: ワザの途中の決定を待つあいだに、ワザの効果で最大HPがのっているダメージ以下に下がった。ワザのあとのきぜつの判定で処理するが、"
                                "待つあいだの状態をエンジンが表せない（エンジンの未対応。今の対応カードでは起こらない）")
    return UnsupportedError(MAX_HP_DROP_CODE, f"{detail}: {MAX_HP_DROP_REASON}")


SHIFT_TEXT = "このカード持ち主は、自分の番に1回、このカードの色を場にいるポケモンのどれかの色に変えることができる。「ねむり・マヒ・こんらん」状態の時、この力は消える。"


def shift_color_options(state: GameState) -> tuple[frozenset[int], frozenset[int]]:
    """［へんしょく］で選べる色（``COLORS`` の位置）: (決まって場にいる色, 読み方によって場にいる色)（v0.48）。場にいるポケモン（お互いの場のバトル場・ベンチ）の今有効な色
    （``type_readings``）。色のないポケモン（なにかの化石・ピッピ人形の場での役割）は数えない。無色も選べる（日本語の文面は無色を除かない。英語版の「other than
    Colorless」は持ち込まない）。読み方が 2 つあるポケモンの色は、ほかに決まってその色のポケモンがいなければ、選ぶと止める（VS1）。"""
    sure: set[int] = set()
    maybe: set[int] = set()
    for player in state.players:
        for pokemon in player.in_play():
            readings = [color for color in type_readings(state, pokemon) if color is not None]
            target = sure if len(type_readings(state, pokemon)) == 1 else maybe
            target.update(COLORS.index(color) for color in readings)
    return frozenset(sure), frozenset(maybe - sure)


@dataclass(frozen=True)
class ShiftColor(PowerEffect):
    """このカードの持ち主は、自分の番に 1 回、このカードの色を場にいるポケモンのどれかの色に変えることができる。ねむり・マヒ・こんらん状態の時、この力は消える（v0.48。
    モルフォン（PMCG2-015）の［へんしょく］。kyuura の印刷の文面。印刷の「このカード持ち主は」は誤植で、kyuura の記録は「このカードの持ち主は」に直した版があるとする。
    意味は同じ）。

    - 宣言して使う。自分の番に 1 回（``once_per_turn``。宣言のときに記録する。v0.42）。ねむり・マヒ・こんらんのこのカードは使えない。かがくへんかガスで消える（エンジンの
      共通の確認 ``POWER_SUPPRESSED``）
    - 宣言のあと、使ったプレイヤーが色を選ぶ（決定 ``SELECT_COLOR``。選べるものは ``shift_color_options``）。選んだ色を場のポケモンの記録（``TypeShift``）に残す（ログ
      ``type_shift``）。前の記録は置きかえる
    - 変えた色がいつまで続くか（使った番のあと・ベンチにもどったあと・この力が消えているあいだ）は決まらない（VS1）。決まっている間（使った番・ベンチにもどっていない・
      力が消えていない）は変えた色、それ以外は 2 つの読み方（``type_readings``）で、結果が変わる処理だけを止める。力を使えなくすること（特殊状態・ガス）と、すでに
      変えた色を消すことを、同じ処理にしない（消えたことにも、続くことにもしない）
    - 場をはなれたら、記録は場のポケモンといっしょになくなる。モルフォンから進化するカードは写しにない（進化したら記録を消す。``evolution.place_evolution_card``）
    """

    implementation_id = "shift_color"
    once_per_turn: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "このカードの色を場にいるポケモンの色に変える特殊能力", (SHIFT_TEXT,))

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)
        require_power_not_used(state, use)
        sure, _ = shift_color_options(state)
        if not sure:
            _, user = state.find_pokemon(use.pokemon_id)
            raise shift_duration_error(user, "決まって場にいる色がない（どの色も、読み方によっては場にいない）")

    def resolve(self, state: GameState, use: PowerUse) -> None:
        sure, maybe = shift_color_options(state)
        _, user = state.find_pokemon(use.pokemon_id)
        push_power_decision(state, use, kind=SELECT_COLOR, player=use.player, options=sorted(sure | maybe), unresolved_choices=sorted(maybe),
                            unresolved_code=SHIFT_DURATION_CODE, unresolved_reason=shift_duration_error(user, "選んだ色は、読み方によっては場にいない").message)

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        from .state import TypeShift

        owner, user = state.find_pokemon(use.pokemon_id)
        color = COLORS[choices[0]]
        previous = user.type_shift
        user.type_shift = TypeShift(color, state.turn_number, user.card)
        extra = {} if previous is None else {"previous_color": previous.color.value, "previous_turn": previous.turn}
        state.add_event("type_shift", player=owner, pokemon=user.card, pokemon_id=user.pokemon_id, power=str(use.key), color=color.value, **extra)

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        sure, maybe = shift_color_options(state)
        return _power_decision_form(decision, use, kind=SELECT_COLOR, choices=(1, 1), options=sorted(sure | maybe), unresolved=sorted(maybe))


CONVERSION_WEAKNESS_TEXTS = (
    # 第1弾のポリゴン（PMCG1-064）
    "相手の対戦ポケモンの弱点を好きな「色」にかえる。ただし「無色」にはできない。相手がベンチに戻った時にその効果はきえる。",
    # ロケット団のポリゴン（PMCG4-050）。書き方だけが違う（「ベンチに戻った時」と「バトル場をはなれた時」はどちらも、受けたポケモンがバトル場をはなれると消える。場をはなれる・
    # 進化するときは一般の規定（GR-2000-P322-PERSISTENT-EFFECTS）でも消える）
    "相手の対戦ポケモンの「弱点」を、無色以外の好きな「色」に変える。この効果は、そのポケモンがバトル場をはなれた時に消える。",
)
CONVERSION_RESISTANCE_TEXTS = ("自分の抵抗力を好きな「色」にかえる。ただし「無色」にはできない。自分がベンチに戻ったときにその効果はきえる。",)


@dataclass(frozen=True)
class ChangeOpponentWeakness(AttackEffect):
    """相手の対戦ポケモンの弱点を、無色以外の好きな色に変える。受けたポケモンがバトル場をはなれた（ベンチにもどった）時にその効果は消える（v0.48。ポリゴン（PMCG1-064・
    PMCG4-050）の「テクスチャー1」。kyuura の印刷の文面。2 つの書き方を受け付ける）。

    - 相手に与える持続する効果 ``state.WeaknessChange``（与えたときからはたらき、期限はない。ベンチにもどる・場をはなれる・進化で消える）。弱点の倍数は変えない
    - 相手に与える効果なので「ワザをうけない」状態・「とうめい」を評価する。色を選ぶのはワザを使ったプレイヤー（決定 ``SELECT_COLOR``。無色以外の 8 色）
    - 受けるポケモンに弱点がないときは決まらない（PG1）。同じポケモンがもう一度受けたら、前の効果を消して新しい色にする（``persistent.replace_persistent_effect``）
    """

    implementation_id = "change_opponent_weakness"
    opponent_effect_elements = (WEAKNESS_CHANGE_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "相手の弱点の色を変えるワザ", damage="none") + _check_exact_text(attack, "相手の弱点の色を変えるワザ", CONVERSION_WEAKNESS_TEXTS)

    def color_terms(self) -> tuple[type]:
        from .state import WeaknessChange

        return (WeaknessChange,)


@dataclass(frozen=True)
class ChangeOwnResistance(AttackEffect):
    """自分の抵抗力を、無色以外の好きな色に変える。自分がベンチにもどった時にその効果は消える（v0.48。ポリゴン（PMCG1-064）の「テクスチャー2」。kyuura の印刷の文面）。

    - 自分自身に与える持続する効果 ``state.ResistanceChange``（与えたときからはたらき、期限はない）。変えるのは色だけで、抵抗力の数（-30）は変えない
    - 自分への効果も「とうめい」を評価する（v0.9 の T8。ポリゴンは持たない）。色を選ぶのはワザを使ったプレイヤー。自分に抵抗力がないとき（相手のワザとして使う）は PG1
    """

    implementation_id = "change_own_resistance"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "自分の抵抗力の色を変えるワザ", damage="none") + _check_exact_text(attack, "自分の抵抗力の色を変えるワザ", CONVERSION_RESISTANCE_TEXTS)

    def color_terms(self) -> tuple[type]:
        from .state import ResistanceChange

        return (ResistanceChange,)


GIANT_GROWTH_TEXT = "コインを投げて「おもて」なら、このカードの最大HPは「{amount}」になる。(バトル場をはなれた時、この効果は消える)"


@dataclass(frozen=True)
class SetMaxHpOnHeads(AttackEffect):
    """コインを投げて「おもて」なら、このカードの最大HPは ``amount`` になる。バトル場をはなれた時、この効果は消える（v0.48。キョウのメタモン（PMCG6-072）の「きょだいか」。
    kyuura の印刷の文面）。

    - 自分自身に与える持続する効果 ``state.MaxHpSet``（与えたときからはたらき、期限はない。ベンチにもどる・場をはなれる・進化で消える）。「うら」なら何もしない（前に受けた
      効果はそのまま）。もう一度「おもて」なら前の効果を消して新しい効果にする（同じ数）
    - ダメージはない。自分への効果なので、コインは相手の状態に関係なく投げる。最大HPが下がる（効果が消える）ときにのっているダメージ以下になる場合は MH1（ワザのあとの
      きぜつの判定で処理する場合を除く）
    """

    amount: int
    implementation_id = "set_max_hp_on_heads"

    def __post_init__(self) -> None:
        _positive_tens(self.amount, "最大HP")

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "コインで最大HPを決まった数にするワザ", damage="none") + _check_exact_text(
            attack, "コインで最大HPを決まった数にするワザ", (GIANT_GROWTH_TEXT.format(amount=self.amount),))

    def max_hp_terms(self) -> tuple[type, int]:
        from .state import MaxHpSet

        return MaxHpSet, self.amount


POUND_TEXT = "このカードに「{name}」の効果がはたらいているとき、このワザのダメージは「{amount}」になる。"


@dataclass(frozen=True)
class DamageIfSelfMaxHpSet(AttackEffect):
    """このカードに「``effect_attack_name``」の効果がはたらいているとき、このワザのダメージは ``amount`` になる（v0.48。キョウのメタモン（PMCG6-072）の「はたく」。kyuura の
    印刷の文面。英語版は条件を「Giant Growth」の文に書くが、効果は同じ（kyuura の card_differences の PMCG6-072。確度: 確実））。

    - 「「30」になる」はワザの説明の計算（p.321 の 1 段階。v0.40 の「ラブラリアット」と同じ）。条件が満たされなければダメージの目安の数字（10）。弱点・抵抗力などは
      そのあとの段階
    - 「きょだいか」の効果がはたらいているかは、最大HP（``max_hp``）と同じ問い合わせ ``persistent.max_hp_set`` で見る（同じ効果の有無を参照する）
    - 同じカードの「``effect_attack_name``」のワザが最大HPを決まった数にするワザであることを ``card_problems`` で確かめる
    """

    effect_attack_name: str
    amount: int
    implementation_id = "damage_if_self_max_hp_set"

    def __post_init__(self) -> None:
        _positive_tens(self.amount, "ダメージ")

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "最大HPの効果でダメージが変わるワザ", damage="fixed") + _check_exact_text(
            attack, "最大HPの効果でダメージが変わるワザ", (POUND_TEXT.format(name=self.effect_attack_name, amount=self.amount),))

    def card_problems(self, attack: Attack, attacks: tuple[Attack, ...]) -> list[str]:
        named = [a for a in attacks if a.index != attack.index and a.name_ja == self.effect_attack_name]
        if len(named) != 1:
            return [f"「{self.effect_attack_name}」のワザが、このカードのほかのワザに 1 つない"]
        text = named[0].text_ja or ""
        if not (text.startswith("コインを投げて「おもて」なら、このカードの最大HPは「") and text.endswith("(バトル場をはなれた時、この効果は消える)")):
            return [f"「{self.effect_attack_name}」が、最大HPを決まった数にするワザではない（{text!r}）"]
        return []


@dataclass(frozen=True)
class DamageThenPoisonAndConfuseOnHeads(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。コインを投げて「おもて」なら、相手を「どく」と「こんらん」状態にする（v0.48。モルフォン（PMCG2-015）の
    「りんぷん」。kyuura の印刷の文面）。

    - 1 枚のワザ全体のコイン（``Coin``）で両方を決める（要素ごとに投げ直さない。v0.44 の「しんけいどく」（どくとマヒ）と同じ形。説明の書き方（「両方の」の有無）が違う
      ので別の型）
    - 相手がこのワザのダメージで HP 以上なら投げない（p.309）。「とうめい」で受けないと決まった・「ワザをうけない」相手には T19b・HC3（v0.34 の ``void_coin_question``）
    """

    implementation_id = "damage_then_poison_and_confuse_on_heads"
    opponent_effect_elements = (POISON, CONFUSION)

    def check(self, attack: Attack) -> list[str]:
        expected = "コインを投げて「おもて」なら、相手を「どく」と「こんらん」状態にする。"
        return _check_form(attack, "コインでどくとこんらんにするワザ", damage="fixed") + _check_exact_text(attack, "コインでどくとこんらんにするワザ", (expected,))


NIGHT_SPIRITS_TEXT = "自分の場にいる{names}の数だけコインを投げ、「おもて」の数×{per}のダメージ。"


@dataclass(frozen=True)
class CoinsPerNamedPokemonDamage(AttackEffect):
    """自分の場にいる名前が ``names`` のどれかのポケモンの数だけコインを投げ、「おもて」の数 × ``per`` のダメージ（v0.48。ナツメのゴースト（PMCG6-050）の「ナイトスピリッツ」。
    kyuura の印刷の文面）。

    - 数えるのはダメージの要素を処理する時点の自分の場（バトル場・ベンチ）のポケモン（v0.39 の ``programs.counted_pokemon``。進化して重なったカードは 1 匹。名前は
      いちばん上のカードの名前の完全一致。カード id の一覧ではなく、説明の名前で数える）。ワザを使ったポケモンも数える
    - コインはダメージの要素の中（ダメージの量だけを決める）。結果は「おもて」の数だけを使う（先読みは「おもて」の数でまとめる。v0.35）。実際の対戦のコインは 1 枚ずつ
    - 相手が「ダメージを受けない」状態なら、ダメージの量だけを決めるコインなので投げるかが決められない（v0.4b の問い）
    """

    names: tuple[str, ...]
    per: int
    implementation_id = "coins_per_named_pokemon_damage"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "場の名前の合うポケモンの数のコインでダメージのワザ", damage="modified", modifier="×")
        expected = NIGHT_SPIRITS_TEXT.format(names="".join(f"「{name}」" for name in self.names), per=self.per)
        if attack.text_ja != expected or attack.damage != self.per:
            problems.append(f"説明 {attack.text_ja!r}・ダメージ {attack.damage} が {expected!r}・{self.per} ではない")
        return problems


PAIN_AMPLIFIER_TEXT = "相手の場の、ダメージカウンターがのっているポケモン全員に、ダメージカウンターを{n}つずつのせる。"


@dataclass(frozen=True)
class PlaceCountersOnDamagedOpponentPokemon(AttackEffect):
    """相手の場の、ダメージカウンターがのっているポケモン全員に、ダメージカウンターを ``counters`` 個ずつのせる（v0.48。ナツメのゲンガー（PMCG6-054）の「ダメージぞうふく」。
    kyuura の印刷の文面）。

    - ダメージカウンターをのせる効果で、ワザによるダメージではない（v0.41 の「ダメージシフト」と同じ。GR-2000-P320-COUNTER-MOVE）。弱点・抵抗力・プラスパワー・ディフェンダー・
      「ダメージを受けない」状態を計算せず、「ダメージを受けたとき」の効果ははたらかない。ログは v0.41 の ``place_damage_counters``
    - 対象は、この要素を処理する時点で相手の場（バトル場 → ベンチの順）にいて、ダメージカウンターがのっているポケモン全員。のっていないポケモン・自分の場のポケモンには
      のせない。対象がいなければ何もしない（p.309）
    - 相手のポケモンへの効果なので、ポケモンごとに「ワザをうけない」状態・「とうめい」を評価する（2 匹以上が「とうめい」なら T27）
    - のせて HP 以上になったポケモンは、ワザのあとのきぜつの判定でまとめてきぜつする（同時のきぜつ。こんじょうは使えない。v0.41 の ``_counters_changed``）
    """

    counters: int
    implementation_id = "place_counters_on_damaged_opponent_pokemon"
    opponent_effect_elements = (COUNTERS_ELEMENT,)  # 相手の場のポケモンにダメージカウンターをのせる（ダメージではない。v0.41 のダメージシフトと同じ要素の種類）

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "ダメージカウンターがのっている相手のポケモン全員にのせるワザ", damage="none") + _check_exact_text(
            attack, "ダメージカウンターがのっている相手のポケモン全員にのせるワザ", (PAIN_AMPLIFIER_TEXT.format(n=self.counters),))


CALL_OF_THE_NIGHT_TEXT = ("相手が「きぜつ」しなかったなら、コインを{n}枚投げる。すべて「おもて」なら、相手と、相手についているすべてのカードを持ち主の山札にもどし、"
                          "その山札をよく切る。")


@dataclass(frozen=True)
class DamageThenCoinsReturnOpponentToDeck(AttackEffect):
    """相手の対戦ポケモンにダメージの目安の数字ぶんのダメージ。相手が「きぜつ」しなかったなら、コインを ``coins`` 枚投げる。すべて「おもて」なら、相手と、相手について
    いるすべてのカードを持ち主の山札にもどし、その山札をよく切る（v0.48。ナツメのゲンガー（PMCG6-054）の「やみのこえ」。kyuura の印刷の文面）。

    - 山札にもどす処理は v0.40 の「つまみだす」と同じ要素 ``programs.ReturnOpponentToDeck``（きぜつではない。サイドは取らない。空いたバトル場はワザのあとに相手が控えから
      出す。控えがいなければ相手の負け）。「つまみだす」の「相手に控えがいない時、このワザは使えない」は、このワザの説明にないので持ち込まない（``required`` が偽）
    - 「相手が「きぜつ」しなかったなら」: このワザのダメージで相手が HP 以上になっていればコインを投げない（処理の対象がない。``has_target``。こんじょうを使えるなら G37）。
      「ダメージを受けない」状態でダメージを受けなかった相手はきぜつしていないので投げる（山札にもどす効果はダメージではないので受ける）。「ワザをうけない」相手・「とうめい」で
      受けないと決まった相手には、効果だけを決めるコインなので HC3・T19b
    - 同じワザで HP 以上になったポケモンがいて山札にもどす場合は RD9（v0.36 と同じ問い）
    """

    coins: int
    implementation_id = "damage_then_coins_return_opponent_to_deck"
    opponent_effect_elements = (RETURN_IN_PLAY_TO_DECK_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "コインがすべて「おもて」なら相手を山札にもどすワザ", damage="fixed") + _check_exact_text(
            attack, "コインがすべて「おもて」なら相手を山札にもどすワザ", (CALL_OF_THE_NIGHT_TEXT.format(n=self.coins),))


# ---------------------------------------------------------------- v0.49: 今の姿・特殊能力の一覧・ワザの一覧（docs/virtual-attacks-transformation-v0.49.md）
#
# 場のポケモンを表す情報を 3 つに分ける（2 章）:
#
# - 実際のカード: ``PokemonInPlay.card``（いちばん上のポケモンのカード。このポケモンそのもの）・``evolution_stack``・``disguise``（「ばける」でのせたカード）。持ち主・uid は
#   カードの表（``GameState.cards``）のまま。どの効果も、印刷の定義・共有する ``CardDefinition``・カードの id を書きかえない
# - 今の姿: ``current_form``（今の姿を決めるカード。ふつうはいちばん上のカード、［へんしん］なら相手の対戦ポケモンのカード、「ばける」ならのせたカード）。名前・段階・HP・
#   タイプ・弱点・抵抗力・にげる・ワザは今の姿のカードの定義（``form_def``）から読む（v0.48 の今有効な値の問い合わせも、今の姿の定義をもとにする）
# - 持っている特殊能力: ``powers_of``（印刷したカードと位置で識別する ``PowerSlot``）。今使えるワザ: ``available_attacks``（印刷したカード・位置・出どころで識別する
#   ``AttackOption``）。宣言・使用条件・回数・使用の禁止・決定の再開・先読み・ログ・観測は、ワザを ``AttackKey``（印刷したカードの id と位置）と印刷したカードの uid で
#   識別する（名前・一覧の位置では識別しない）

FORM_PRINTED = "printed"  # いちばん上のカード（v0.48 までと同じ）
FORM_TRANSFORM = "transform"  # メタモンの［へんしん］: 相手の対戦ポケモンと同じカードとしてあつかう
FORM_DISGUISE = "disguise"  # タケシのキュウコンの「ばける」: のせた進化カードのポケモンとしてあつかう


@dataclass(frozen=True)
class Form:
    """場のポケモンの今の姿（v0.49）。``card`` は今の姿を決めるカードの uid（その定義が名前・段階・HP・タイプ・弱点・抵抗力・にげる・ワザを決める）、``kind`` は決め方、
    ``defender`` は［へんしん］で同じカードとしてあつかう相手の対戦ポケモンの番号。状態に持たず、問い合わせのたびに求める（``current_form``）。"""

    card: int
    kind: str
    defender: int | None = None


@dataclass(frozen=True)
class PowerSlot:
    """場のポケモンが今持つ特殊能力の 1 つ（v0.49）。``card`` はその特殊能力を印刷したカードの uid、``key`` は登録の ``PowerKey``（カードの id と位置）、``effect`` は
    登録された実装（なければ None）。"""

    card: int
    key: PowerKey
    power: Power
    effect: PowerEffect | None


def card_power_slots(state: GameState, card: int) -> list[PowerSlot]:
    """カード ``card`` に印刷された特殊能力（v0.49。カードの今の場所での定義 ``GameState.card_def``）。"""
    definition = state.card_def(card)
    return [PowerSlot(card, PowerKey(definition.id, index), power, state.effects.power_effect(definition.id, power))
            for index, power in enumerate(definition.powers)]


def powers_of(state: GameState, pokemon: PokemonInPlay) -> list[PowerSlot]:
    """場のポケモン ``pokemon`` が今持つ特殊能力（v0.49。特殊能力を探す処理はどれもこれを使う）。

    - ふつうはいちばん上のカード（``card``）の特殊能力（p.310。進化前のカードの特殊能力は持たない）
    - 「ばける」でのせたカードがあれば、そのカードの特殊能力（先）と、いちばん上のカード（タケシのキュウコン）の「ばける」（もどす・ねむり・マヒ・こんらんでもどる説明の
      ため）。2000.02.14 版の基準（『オフィシャルブック2000』）では、のせたカードの特殊能力ははたらき・使える（kyuura の ERR-BROCK-NINETALES・card_differences の
      PMCG5-019。のせたカードの特殊能力を使えなくした「ルール変更のお知らせ」は 2000年5月で、この基準のあと。持ち込まない）。ただし「手札から場に出した時」の特殊能力は
      「ばける」でのせたときには使えない（同じ記録の p.69 の解説。使う機会を出さない）
    - メタモンの［へんしん］で相手の対戦ポケモンと同じカードとしてあつかうとき、写したカードの特殊能力を持つかは決まらない（TF1）。ここにはメタモン自身の特殊能力
      （［へんしん］）だけを入れる（写した特殊能力を持つ・持たないのどちらにも決めない。宣言する特殊能力は使うときに止め、ほかの特殊能力は ``form_problems`` が止める）
    状態を変えず、乱数を使わない。"""
    if pokemon.disguise is None:
        return card_power_slots(state, pokemon.card)
    return card_power_slots(state, pokemon.disguise) + card_power_slots(state, pokemon.card)


TRANSFORM_TEXT = (
    "バトル場にいる限り、このカードは相手の対戦ポケモンと同じカードとしてあつかう。エネルギーカードは、このカードについている限り、どの色のエネルギーとしても使うことが"
    "できる。「ねむり・マヒ・こんらん」状態の時やベンチにいる時には、この「へんしん」の力は消える。このカードに進化カードをつけることはできない。"
)


@dataclass(frozen=True)
class TransformIntoDefender(ContinuousPower):
    """バトル場にいる限り、このカードは相手の対戦ポケモンと同じカードとしてあつかう。エネルギーカードは、このカードについている限り、どの色のエネルギーとしても使える。
    ねむり・マヒ・こんらん状態の時やベンチにいる時には、この力は消える。このカードに進化カードをつけることはできない（v0.49。メタモン（PMCG3-042）の［へんしん］。kyuura の
    印刷の文面。docs/virtual-attacks-transformation-v0.49.md 5 章）。

    - 常にはたらく（宣言しない）。はたらくのは、バトル場にいて、ねむり・マヒ・こんらんでなく、かがくへんかガスに消されていないとき（``transform_works``）
    - はたらいているあいだ、今の姿は相手の対戦ポケモンのいちばん上のカード（``current_form``）: 名前・段階・HP・タイプ・弱点・抵抗力・にげる・ワザはそのカードの定義から
      読む。相手のポケモンが受けている効果（ダメージ・特殊状態・持続する効果・「きょだいか」・テクスチャー・［へんしょく］の記録・ついているカード）はカードではないので
      写さない。メタモンが受けている効果（「きょだいか」・テクスチャーなど）は、メタモンに当てはめたまま
    - 写したカードのワザは、メタモンのワザとして、必要なエネルギー・ワザの説明の条件をそのまま満たして使う（必要なエネルギーをなくす「ゆびをふる」の説明とは違う）。
      エネルギーカードはどの色としても払える（1 枚が出すエネルギーは 1 つのまま。同じ 1 枚を 2 つの記号に数えない。``attack_cost_payable``）。ワザの説明がタイプの
      エネルギーの数を数えるとき、どの色としても数えるかは決まらない（TE1）。トラッシュする「○エネルギーカード」は、カードの印刷の種類で決める
    - 写した特殊能力を持つかは決まらない（TF1）。相手の対戦ポケモンが「ばける」でほかのポケモンとしてあつかわれている・ポケモンとして出したトレーナーカードのときに、
      どのカードと同じにあつかうかは決まらない（TF2）。どちらも ``form_problems`` が、その状態にするコマンドを受け付けない（その状態にならない）
    - 進化カードをつけることはできない（通常の進化・ポケモン育て屋さん・山札から重ねる効果のどれも。``evolution_forbidden``）
    """

    implementation_id = "transform_into_defender"
    supplies_attacks: ClassVar[bool] = True  # ワザのないカード（メタモン）に、今の姿のカードのワザを持たせる（``cards`` の分類）
    location: ClassVar[str] = CONTINUOUS_ACTIVE
    what: ClassVar[str] = "相手の対戦ポケモンと同じカードとしてあつかう特殊能力"

    def texts(self) -> tuple[str, ...]:
        return (TRANSFORM_TEXT,)


def transform_slot(state: GameState, pokemon: PokemonInPlay) -> PowerSlot | None:
    """``pokemon`` のいちばん上のカードの［へんしん］（``TransformIntoDefender``）。なければ None（v0.49）。"""
    for slot in card_power_slots(state, pokemon.card):
        if isinstance(slot.effect, TransformIntoDefender):
            return slot
    return None


def transform_works(state: GameState, pokemon: PokemonInPlay) -> bool:
    """``pokemon`` の［へんしん］が今はたらいているか（v0.49。バトル場にいる・ねむり・マヒ・こんらんでない・かがくへんかガスに消されていない）。"""
    if pokemon.disguise is not None:
        return False
    slot = transform_slot(state, pokemon)
    if slot is None:
        return False
    located = state.find_pokemon(pokemon.pokemon_id)
    if located is None or located[1] is not pokemon:
        return False
    if not slot.effect.located(state, located[0], pokemon) or not slot.effect.status_allows(pokemon):
        return False
    from .continuous import suppressors_of  # continuous.py は effects.py を読み込むので、使うときに読み込む

    return not suppressors_of(state, slot.power)


def transform_defender(state: GameState, pokemon: PokemonInPlay) -> PokemonInPlay | None:
    """［へんしん］がはたらいているなら、同じカードとしてあつかう相手の対戦ポケモン（v0.49）。はたらいていない・相手のバトル場が空いているなら None。"""
    if not transform_works(state, pokemon):
        return None
    owner = state.find_pokemon(pokemon.pokemon_id)[0]
    return state.players[1 - owner].active


def current_form(state: GameState, pokemon: PokemonInPlay) -> Form:
    """場のポケモンの今の姿（v0.49。公開の問い合わせ）。「ばける」でのせたカードがあればそのカード、［へんしん］がはたらいていれば相手の対戦ポケモンのいちばん上のカード
    （相手のポケモンの姿がそのカードと違う（TF2）・写したカードの特殊能力（TF1）の状態には、``form_problems`` がしない）、どちらでもなければいちばん上のカード。
    状態に持たず、問い合わせのたびに今の場から求める（入れ替え・進化・場をはなれる・特殊状態・かがくへんかガスのあとも、その時点の答え）。"""
    if pokemon.disguise is not None:
        return Form(pokemon.disguise, FORM_DISGUISE)
    defender = transform_defender(state, pokemon)
    if defender is not None:
        return Form(defender.card, FORM_TRANSFORM, defender.pokemon_id)
    return Form(pokemon.card, FORM_PRINTED)


def form_def(state: GameState, pokemon: PokemonInPlay) -> CardDefinition:
    """場のポケモンの今の姿のカードの定義（v0.49）。名前・段階・HP（もとの値）・タイプ・弱点・抵抗力・にげる・ワザはここから読む（今有効な値は ``max_hp`` などが、
    この定義をもとに求める）。"""
    return state.card_def(current_form(state, pokemon).card)


def attack_of(state: GameState, key: AttackKey) -> Attack:
    """ワザ ``key``（印刷したカードの id と位置）の定義（v0.49）。"""
    return state.definitions[key.card_id].attacks[key.attack_index]


def any_color_energy(state: GameState, pokemon: PokemonInPlay) -> bool:
    """``pokemon`` についているエネルギーカードを、ワザに必要なエネルギーの支払いで、どの色のエネルギーとしても使えるか（v0.49。［へんしん］がはたらいているとき）。"""
    return transform_works(state, pokemon)


def attack_cost_payable(state: GameState, pokemon: PokemonInPlay, attack: Attack) -> bool:
    """``pokemon`` が今ついているエネルギーで、ワザ ``attack`` に必要なエネルギーを払えるか（p.320。v0.49 で関数にした）。

    ふつうは色の指定のある記号を同じ色で、無色をどの色でも払う（``cards.can_pay_cost``）。［へんしん］がはたらいているメタモンは、ついているエネルギーカードをどの色の
    エネルギーとしても使える（1 枚が出すエネルギーは 1 つのまま。同じ 1 枚を 2 つの記号に数えない）ので、エネルギーの数が記号の数以上なら払える。"""
    provided = state.energy_types(pokemon)
    if any_color_energy(state, pokemon):
        return len(provided) >= len(attack.cost)
    return can_pay_cost(attack.cost, provided)


def energy_type_readings(state: GameState, pokemon: PokemonInPlay, energy_type: EnergyType) -> tuple[list[EnergyType], ...]:
    """ワザの説明が ``pokemon`` についている ``energy_type`` のエネルギーを数えるときの、エネルギーのタイプの並びの読み方（v0.49）。ふつうは 1 つ（``energy_types``）。
    ［へんしん］がはたらいていれば、(今のタイプの並び, すべてを ``energy_type`` として数える並び) の 2 つ（TE1。解決の基盤の ``programs.transform_energy_question`` が、
    2 つの読み方で数える・選べるカードが変わるときに止める）。"""
    types = state.energy_types(pokemon)
    if not any_color_energy(state, pokemon) or all(kind is energy_type for kind in types):
        return (types,)
    return (types, [energy_type] * len(types))


# ---------------------------------------------------------------- サイコリンク

PSYLINK_TEXT = (
    "自分の場の「{type}」ポケモンが持っているすべてのワザを、このカードも持っているものとする。(それらのワザを、このカードのワザとして使うことができる)。"
    "このカードが「ねむり・マヒ・こんらん」状態の時、この力は消える。"
)


@dataclass(frozen=True)
class AttacksOfOwnTypePokemon(ContinuousPower):
    """自分の場の「``pokemon_type``」ポケモンが持っているすべてのワザを、このカードも持っているものとする。ねむり・マヒ・こんらん状態の時、この力は消える（v0.49。
    ナツメのフーディン（PMCG6-053）の［サイコリンク］。kyuura の印刷の文面。docs/virtual-attacks-transformation-v0.49.md 3 章）。

    - 常にはたらく（宣言しない）。場所はどこでもよい（「このカードも持っている」。ワザを使えるのはバトル場のときだけ）。ねむり・マヒ・こんらん・かがくへんかガスで消える
    - ワザを持つポケモン（供給するポケモン）は、自分の場（バトル場・ベンチ）のこのカード以外のポケモンで、今有効なタイプ（v0.48 の ``type_readings``）が「超」のもの。
      ［へんしょく］で変えた色が有効か決まらない（VS1）ポケモンは、読み方でワザを持つかが変わるので、そのワザを選ぶと止める（VS1）
    - 持つワザは、供給するポケモンの今の姿のカードのワザ（``form_def``。ほかの［サイコリンク］・「思い出させる」で持つワザは数えない。どのフーディンも同じ自分の場を
      見るので、数えても同じワザの集まりになる。数えないので、2 匹以上の［サイコリンク］が重なっても再帰・ワザの増え続けは起こらない）
    - 持ったワザは、このカードのワザとして使う（ワザを使うポケモンはこのカード。必要なエネルギー・説明の条件・エネルギーのトラッシュ・自分へのダメージ・「このカード」は
      このカードについて処理する。弱点・抵抗力はこのカードのタイプで計算する）。供給するポケモンは処理しない
    - 同じワザ（同じカードの同じ位置）を 2 匹以上が持つときは、出どころ（供給するポケモンの今の姿のカードの uid）ごとに選べる。使えないワザの効果（「メガバーン」の「次の
      自分の番、このカードは「メガバーン」を使えない」）は ``AttackKey`` で探すので、どの出どころの同じワザにも当てはまる
    """

    pokemon_type: EnergyType
    implementation_id = "attacks_of_own_type_pokemon"
    what: ClassVar[str] = "自分の場のポケモンのワザを持つ特殊能力"

    def texts(self) -> tuple[str, ...]:
        return (PSYLINK_TEXT.format(type=self.pokemon_type.ja),)


def link_types(state: GameState, owner: int, pokemon: PokemonInPlay) -> tuple[EnergyType, ...]:
    """``pokemon``（持ち主 ``owner``）が今はたらいている［サイコリンク］で、ワザを持つ自分の場のポケモンのタイプ（v0.49）。はたらいていなければ空。"""
    from .continuous import suppressors_of  # continuous.py は effects.py を読み込むので、使うときに読み込む

    found = []
    for slot in powers_of(state, pokemon):
        effect = slot.effect
        if (isinstance(effect, AttacksOfOwnTypePokemon) and effect.located(state, owner, pokemon) and effect.status_allows(pokemon)
                and not suppressors_of(state, slot.power) and effect.pokemon_type not in found):
            found.append(effect.pokemon_type)
    return tuple(found)


# ---------------------------------------------------------------- ワザの一覧

ROUTE_FORM = "form"  # 今の姿のカードのワザ
ROUTE_RECALL = "recall"  # 「思い出させる」で使う進化前のワザ
ROUTE_LINK = "psylink"  # ［サイコリンク］で持つ、自分の場の「超」ポケモンのワザ


@dataclass(frozen=True)
class AttackOption:
    """場のポケモンが今持つワザの 1 つ（v0.49。``available_attacks``）。

    - ``card``: そのワザを印刷したカードの uid（ワザの出どころ。``UseAttack.card``）。``card_id``・``attack_index``: 登録の ``AttackKey``（ワザの同一性）
    - ``route``: 持ち方（``ROUTE_FORM``・``ROUTE_RECALL``・``ROUTE_LINK``）。``provider``: ［サイコリンク］でワザを供給する場のポケモンの番号
    - ``problem``: そのワザを選ぶと止める理由 (コード, 理由の文)（読み方で持つかが変わる VS1・「思い出させる」の RC2〜RC4・1 回しか使えないワザの VA1）。None なら止めない
    """

    card: int
    card_id: str
    attack_index: int
    route: str = ROUTE_FORM
    provider: int | None = None
    problem: tuple[str, str] | None = None

    @property
    def key(self) -> AttackKey:
        return AttackKey(self.card_id, self.attack_index)


VIRTUAL_ONCE_ATTACK_CODE = "UNRESOLVED_VIRTUAL_ONCE_ATTACK"
VIRTUAL_ONCE_ATTACK_REASON = (
    "「このワザは、このカードが場に出てから、1回しか使えない」ワザを、ほかのカードのワザとして使う（［へんしん］・「ばける」で写したカード・［サイコリンク］・「思い出させる」）"
    "とき、「このカード」と「場に出てから」がどのカード・どの時点を指すか（使った記録をどのカードに付けるか）は、kyuura の記録・印刷の文面から決められないので扱わない（VA1）"
)
RECALL_WITHOUT_ATTACK_CODE = "UNRESOLVED_RECALL_WITHOUT_PRE_EVOLUTION_ATTACK"
RECALL_WITHOUT_ATTACK_REASON = (
    "「思い出させる」の「あなたの対戦ポケモンが進化カードなら、…進化前に持っていたワザを…使ってよい」で、対戦ポケモンが進化していない（重なった進化前のカードがない）か、"
    "進化前のカードにワザがないとき、このトレーナーを使えるか（効果のないトレーナーを使えるか）は、kyuura の記録・印刷の文面から決められないので扱わない（RC1）"
)
RECALL_EARLIER_STAGE_CODE = "UNRESOLVED_RECALL_EARLIER_STAGE"
RECALL_EARLIER_STAGE_REASON = (
    "2 進化ポケモン（1 進化ポケモンから進化したもの）で、「進化前に持っていたワザ」に、すぐ下の 1 進化ポケモンのカードのワザのほか、いちばん下のたねポケモンのカードのワザも"
    "入るかは、kyuura の記録・印刷の文面から決められないので扱わない（RC2。すぐ下のカードのワザは、最後に進化する前に持っていたワザなので使える）"
)
RECALL_TARGET_CHANGED_CODE = "UNRESOLVED_RECALL_TARGET_CHANGED"
RECALL_TARGET_CHANGED_REASON = (
    "「思い出させる」を使ったあと、対戦ポケモンが入れかわった・進化した（使ったときの対戦ポケモンといちばん上のカードが違う）。説明の「この番だけ、…使ってよい」が、"
    "使ったときの対戦ポケモンにだけ当てはまるのか、ワザを使うときの対戦ポケモンに当てはまるのかは決められないので扱わない（RC3）"
)
RECALL_FORM_CODE = "UNRESOLVED_RECALL_FORM"
RECALL_FORM_REASON = (
    "対戦ポケモンが「ばける」でのせたカードのポケモンとしてあつかわれている。「進化前に持っていたワザ」が、重なっている進化前のカード（タケシのロコン）のワザか、のせた"
    "カードのポケモンの進化前か（場にはない）は決められないので扱わない（RC4）"
)


def available_attacks(state: GameState, pokemon: PokemonInPlay) -> tuple[AttackOption, ...]:
    """場のポケモン ``pokemon`` が今持つワザ（v0.49。公開の問い合わせ。並びは今の姿のカードのワザ → 「思い出させる」で使える進化前のワザ（すぐ下のカードから）→
    ［サイコリンク］で持つワザ（供給するポケモンをバトル場 → ベンチの順に））。

    持っていても使えるとは限らない（必要なエネルギー・使えない効果・説明の条件は ``checks.attack_request`` が確かめる）。選ぶと止めるワザは ``problem`` に理由がある。
    ワザは印刷したカードの uid と ``AttackKey`` で識別する。状態を変えず、乱数を使わない。場にいないポケモンなら空。"""
    located = state.find_pokemon(pokemon.pokemon_id)
    if located is None or located[1] is not pokemon:
        return ()
    owner = located[0]
    form = current_form(state, pokemon)
    definition = state.card_def(form.card)
    options = [_attack_option(state, form, form.card, definition.id, attack.index, ROUTE_FORM, None, None) for attack in definition.attacks]
    if state.players[owner].active is pokemon:
        options += _recall_options(state, owner, pokemon, form)
    options += _link_options(state, owner, pokemon, form)
    return tuple(options)


def _attack_option(state: GameState, form: Form, card: int, card_id: str, index: int, route: str, provider: int | None,
                   problem: tuple[str, str] | None) -> AttackOption:
    if problem is None and (route != ROUTE_FORM or form.kind != FORM_PRINTED):
        effect = state.effects.attack_effect(card_id, state.definitions[card_id].attacks[index], state.definitions[card_id].attacks)
        if effect is not None and effect.once_after_entering_play:
            problem = (VIRTUAL_ONCE_ATTACK_CODE, VIRTUAL_ONCE_ATTACK_REASON)
    return AttackOption(card, card_id, index, route, provider, problem)


def recall_records(state: GameState, player: int) -> tuple[RecallEffect, ...]:
    """プレイヤー ``player`` がこの番に使った「思い出させる」の記録（v0.49）。"""
    return tuple(record for record in state.recalls if record.player == player and record.turn == state.turn_number)


def recall_stack_attacks(state: GameState, pokemon: PokemonInPlay) -> list[tuple[int, int]]:
    """``pokemon`` に重なっている進化前のカードのワザ（すぐ下のカードから、(カードの uid, ワザの位置)）（v0.49）。ポケモン育て屋さんで 1 進化を飛ばした 2 進化ポケモンは、
    実際に重なっているカード（たねポケモン）だけ（飛ばした 1 進化のカードは場にないので数えない）。"""
    return [(uid, attack.index) for uid in reversed(pokemon.evolution_stack) for attack in state.card_def(uid).attacks]


def _recall_options(state: GameState, owner: int, pokemon: PokemonInPlay, form: Form) -> list[AttackOption]:
    records = recall_records(state, owner)
    if not records or not pokemon.evolution_stack:
        return []
    bound = any(record.pokemon_id == pokemon.pokemon_id and record.card == pokemon.card for record in records)
    if form.kind != FORM_PRINTED:
        shared = (RECALL_FORM_CODE, RECALL_FORM_REASON)
    elif not bound:
        shared = (RECALL_TARGET_CHANGED_CODE, RECALL_TARGET_CHANGED_REASON)
    else:
        shared = None
    immediate = pokemon.evolution_stack[-1]
    options = []
    for uid, index in recall_stack_attacks(state, pokemon):
        problem = shared if shared is not None else (None if uid == immediate else (RECALL_EARLIER_STAGE_CODE, RECALL_EARLIER_STAGE_REASON))
        options.append(_attack_option(state, form, uid, state.cards[uid].card_id, index, ROUTE_RECALL, None, problem))
    return options


def _link_options(state: GameState, owner: int, pokemon: PokemonInPlay, form: Form) -> list[AttackOption]:
    types = link_types(state, owner, pokemon)
    if not types:
        return []
    options = []
    for supplier in state.players[owner].in_play():
        if supplier is pokemon:
            continue
        matches = [color in types for color in type_readings(state, supplier)]
        if not any(matches):
            continue
        problem = None if all(matches) else (SHIFT_DURATION_CODE, shift_duration_error(supplier, "このポケモンが［サイコリンク］でワザを供給するか").message)
        supplier_form = current_form(state, supplier)
        definition = state.card_def(supplier_form.card)
        for attack in definition.attacks:
            options.append(_attack_option(state, form, supplier_form.card, definition.id, attack.index, ROUTE_LINK, supplier.pokemon_id, problem))
    return options


def find_attack_option(state: GameState, pokemon: PokemonInPlay, card: int | None, attack_index: int) -> AttackOption | None:
    """``UseAttack`` の (印刷したカード, 位置) に当たる、``pokemon`` が今持つワザ（v0.49）。``card`` が None なら今の姿のカードのワザ（v0.48 までの ``UseAttack``）。
    なければ None。"""
    for option in available_attacks(state, pokemon):
        if option.attack_index != attack_index:
            continue
        if (card is None and option.route == ROUTE_FORM) or (card is not None and option.card == card):
            return option
    return None


def held_attack_keys(state: GameState, pokemon: PokemonInPlay) -> tuple[list[tuple[AttackKey, tuple[str, str] | None]], bool]:
    """``pokemon`` が今持つワザを、ワザ（``AttackKey``）ごとに 1 つにまとめた並び（v0.49。相手のワザを選ぶ効果（「ゆびをふる」・「ちょうのうりょく」・「ドわすれ」）の
    選べるもの。並びは ``available_attacks`` の順）。

    - 同じワザ（同じカードの同じ位置）を 2 匹以上が供給するときは 1 つ（選ぶのはワザで、出どころではない）
    - 2 つめの値は、持つかが読み方で変わるワザ（［へんしょく］の VS1。供給するすべての出どころで変わるときだけ）の (コード, 理由の文)。ほかの止める理由（VA1・
      RC2〜RC4）は、そのポケモンがワザを使うときの理由なので、ここでは持つワザとして数える
    - 返す真偽値は、並びがいちばん上のカードのワザの並び（v0.48 までの選べるもの）と同じか（同じなら決定の形を v0.48 と同じにする）
    """
    order: list[AttackKey] = []
    problems: dict[AttackKey, tuple[str, str] | None] = {}
    for option in available_attacks(state, pokemon):
        problem = option.problem if option.problem is not None and option.problem[0] == SHIFT_DURATION_CODE else None
        if option.key not in problems:
            order.append(option.key)
            problems[option.key] = problem
        elif problem is None:
            problems[option.key] = None
    top = state.cards[pokemon.card].card_id
    legacy = order == [AttackKey(top, attack.index) for attack in state.card_def(pokemon.card).attacks]
    return [(key, problems[key]) for key in order], legacy


# ---------------------------------------------------------------- ばける

SHAPESHIFT_TEXT = (
    "この力は、自分の番ごとに1回だけ使える。手札から「進化カード」を1枚選び、このカードの上にのせる。それ以後、このカードを、のせた「進化カード」のポケモンとしてあつかう。"
    "(ただし「進化・退化」はできない)。自分の番に、このカードの上にのっている「進化カード」をトラッシュして、このカードを「{name}」にもどしてもよい。このカードが"
    "「ねむり・マヒ・こんらん」状態の時、この「ばける」の力は使えず、このカードは「{name}」にもどる。(のせてあった「進化カード」はトラッシュされる)"
)
SHAPESHIFT_SUPPRESSED_CODE = "UNRESOLVED_SHAPESHIFT_SUPPRESSED"
SHAPESHIFT_SUPPRESSED_REASON = (
    "「ばける」でのせたカードのポケモンとしてあつかわれているポケモンの「ばける」の力が、かがくへんかガスで消える（のせたカードのかがくへんかガスを含む）。のせたカードを"
    "トラッシュしてもどるのか、のせたまま元の姿にもどるのか、ガスがなくなったら続くのかは、kyuura の記録・印刷の文面から決められないので扱わない（DG1）"
)
SHAPESHIFT_ENTRY_POWER_CODE = "UNRESOLVED_SHAPESHIFT_ENTRY_POWER"
SHAPESHIFT_ENTRY_POWER_REASON = (
    "「場に出た時」に使える特殊能力を持つ進化カードを「ばける」でのせる。p.69 の解説（kyuura の ERR-BROCK-NINETALES）は「手札から場に出したときに使える能力は、[ばける]で"
    "場に出したときには使えません」とだけ書き、「場に出た時」の特殊能力を使う機会があるかは決められないので扱わない（DG2）"
)
SHAPESHIFT_AGAIN_CODE = "UNRESOLVED_SHAPESHIFT_AGAIN"
SHAPESHIFT_AGAIN_REASON = (
    "もう「ばける」でのせたカードのポケモンとしてあつかわれているポケモンが、もう一度「ばける」を使う。のせたカードの上にさらにのせるのか、入れかえるのか、使えないのかは"
    "kyuura の記録・印刷の文面から決められないので扱わない（DG3）"
)


def shapeshift_choices(state: GameState, player: int, pokemon: PokemonInPlay, key: PowerKey) -> tuple[list[int], list[tuple[int, str, str]]]:
    """「ばける」で手札からのせられる進化カード（手札の順）と、選ぶと止めるもの（(カード, コード, 理由)）（v0.49）。止める理由は、のせると: 「場に出た時」の特殊能力を
    持つ（DG2）・かがくへんかガスで「ばける」が消える（DG1）・［へんしん］が決まらなくなる（TF1・TF2）・最大HPがのっているダメージ以下に下がる（MH1）。状態を変えない
    （複製の上でのせて比べる）。"""
    from .zones import place_disguise

    options = [uid for uid in state.players[player].hand if state.card_def(uid).is_evolution_pokemon]
    blocked = []
    for uid in options:
        entry = [slot for slot in card_power_slots(state, uid) if isinstance(slot.effect, EntryPower) and not slot.effect.from_hand_only]
        if entry:
            blocked.append((uid, SHAPESHIFT_ENTRY_POWER_CODE, f"カード {uid}（{state.card_def(uid).name_ja}［{entry[0].power.name_ja}］）: {SHAPESHIFT_ENTRY_POWER_REASON}"))
            continue
        trial = state.clone()
        owner, target = trial.find_pokemon(pokemon.pokemon_id)
        place_disguise(trial, owner, target, uid, power=str(key))
        stop = state_stop_after(state, trial)
        if stop is not None:
            blocked.append((uid, stop[0], f"カード {uid}（{state.card_def(uid).name_ja}）をのせると: {stop[1]}"))
    return options, blocked


@dataclass(frozen=True)
class Shapeshift(PowerEffect):
    """この力は、自分の番ごとに 1 回だけ使える。手札から進化カードを 1 枚選び、このカードの上にのせる。それ以後、このカードを、のせた進化カードのポケモンとしてあつかう
    （ただし進化・退化はできない）。自分の番に、のせている進化カードをトラッシュして、このカードを元にもどしてもよい。ねむり・マヒ・こんらん状態の時、この力は使えず、
    このカードは元にもどる（のせてあった進化カードはトラッシュされる）（v0.49。タケシのキュウコン（PMCG5-019）の「ばける」。kyuura の印刷の文面。2000.02.14 版の基準では、
    のせたカードの特殊能力ははたらく（2000年5月の ERR-BROCK-NINETALES は持ち込まない）。docs/virtual-attacks-transformation-v0.49.md 4 章）。

    - 宣言して使う。自分の番に 1 回（``once_per_turn``。宣言のときに記録する。v0.42）。ねむり・マヒ・こんらんのこのカードは使えない。かがくへんかガスで使えない（エンジンの
      共通の確認）
    - 宣言のあと、使ったプレイヤーが手札の進化カードを 1 枚選ぶ（決定 ``SELECT_EVOLUTION_CARD``。名前・段階の一致は要らない）。選んだカードを ``PokemonInPlay.disguise`` に
      のせる（``zones.place_disguise``。ログ ``disguise``）。進化の重なりではないので、場のポケモンの番号・場に出た番・進化した番・ダメージ・エネルギー・ついている
      トレーナー・持続する効果・特殊状態は変えない。「手札から場に出した時」の特殊能力の使う機会はない（p.69 の解説）
    - 手札に進化カードがない: PW3。もうのせている: DG3。のせると止める場合（``shapeshift_choices``）は選べるが選ぶと止める（どれもそうなら宣言の前に止める）
    - 元にもどす操作は ``RemoveDisguise``（特殊能力の使用の宣言ではない）。ねむり・マヒ・こんらんになったら、付ける処理がのせたカードをトラッシュする
      （``conditions._end_disguise``。ログ ``disguise_removed``）
    """

    original_name: str
    implementation_id = "shapeshift"
    once_per_turn: ClassVar[bool] = True

    def check(self, power: Power) -> list[str]:
        return _check_power_text(power, "手札の進化カードをのせて、そのポケモンとしてあつかう特殊能力", (SHAPESHIFT_TEXT.format(name=self.original_name),))

    def check_usable(self, state: GameState, use: PowerUse) -> None:
        _require_user_not_asleep_paralyzed_confused(state, use)
        _require_no_choices(use)
        require_power_not_used(state, use)
        owner, user = state.find_pokemon(use.pokemon_id)
        if user.disguise is not None:
            raise UnsupportedError(SHAPESHIFT_AGAIN_CODE, f"ポケモン {user.pokemon_id}（のせたカード {user.disguise}）: {SHAPESHIFT_AGAIN_REASON}")
        options, blocked = shapeshift_choices(state, owner, user, use.key)
        if not options:
            raise _power_zero_cards("「ばける」で選ぶ手札の「進化カード」がない")
        if len(blocked) == len(options):
            raise UnsupportedError(blocked[0][1], blocked[0][2])

    def resolve(self, state: GameState, use: PowerUse) -> None:
        owner, user = state.find_pokemon(use.pokemon_id)
        options, blocked = shapeshift_choices(state, owner, user, use.key)
        push_power_decision(state, use, kind=SELECT_EVOLUTION_CARD, player=use.player, options=options,
                            unresolved_choices=[uid for uid, _, _ in blocked], unresolved_detail=blocked,
                            unresolved_code=blocked[0][1] if blocked else "UNRESOLVED_RULING", unresolved_reason=blocked[0][2] if blocked else "")

    def resume(self, state: GameState, use: PowerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        from .zones import place_disguise

        owner, user = state.find_pokemon(use.pokemon_id)
        place_disguise(state, owner, user, choices[0], power=str(use.key))

    def decision_problems(self, state: GameState, use: PowerUse, decision: PendingDecision) -> list[str]:
        owner, user = state.find_pokemon(use.pokemon_id)
        options, blocked = shapeshift_choices(state, owner, user, use.key)
        problems = _power_decision_form(decision, use, kind=SELECT_EVOLUTION_CARD, choices=(1, 1), options=options,
                                        unresolved=[uid for uid, _, _ in blocked])
        if tuple(decision.context_value("unresolved_detail", ())) != tuple(blocked):
            problems.append(f"特殊能力 {use.key} の決定の選択ごとの止める理由 {decision.context_value('unresolved_detail', ())} が {tuple(blocked)} ではない")
        return problems


def shapeshift_slot(state: GameState, pokemon: PokemonInPlay) -> PowerSlot | None:
    """``pokemon`` のいちばん上のカード（のせたカードではない）の「ばける」（``Shapeshift``）。なければ None（v0.49）。"""
    for slot in card_power_slots(state, pokemon.card):
        if isinstance(slot.effect, Shapeshift):
            return slot
    return None


def evolution_forbidden(state: GameState, target: PokemonInPlay) -> tuple[str, str] | None:
    """カードの説明が、場のポケモン ``target`` の進化を禁じているなら (コード, 理由の文)（v0.49。``evolution.evolution_block`` が、げんしのちからの次に聞く。どの進化の
    入口でも同じ）: メタモンの［へんしん］の「このカードに進化カードをつけることはできない」と、「ばける」でのせたカードのポケモンとしてあつかわれているポケモンの
    「(ただし「進化・退化」はできない)」。どちらも印刷の文面に書かれた禁止。［へんしん］の禁止は、はたらいているか（バトル場・特殊状態・かがくへんかガス）を見ない
    （写しに「メタモンから進化」のカードはなく、名前の確かめでも重ねられないので、見ても結果は変わらない。［へんしん］で同じカードとしてあつかう間に、そのカードから
    進化するカードを重ねることを、ここで止める）。"""
    if target.disguise is not None:
        return "EVOLUTION_PREVENTED", f"場のポケモン {target.pokemon_id} は「ばける」でのせたカードのポケモンとしてあつかわれているので、進化できない（「ただし「進化・退化」はできない」）"
    if transform_slot(state, target) is not None:
        return "EVOLUTION_PREVENTED", f"場のポケモン {target.pokemon_id} のカードには進化カードをつけることはできない（［へんしん］の説明）"
    return None


# ---------------------------------------------------------------- 思い出させる

RECALL_TEXT = "あなたの対戦ポケモンが進化カードなら、この番だけ、進化前に持っていたワザを自分のワザとして使ってよい。"


@dataclass(frozen=True)
class RecallPreEvolutionAttacks(TrainerEffect):
    """あなたの対戦ポケモンが進化カードなら、この番だけ、進化前に持っていたワザを自分のワザとして使ってよい（v0.49。トレーナー「思い出させる」（PMCG5-071）。kyuura の
    印刷の文面。docs/virtual-attacks-transformation-v0.49.md 6 章）。

    - 使うと、この番の記録（``GameState.recalls`` の ``RecallEffect``。使ったときの対戦ポケモンの番号といちばん上のカード）を置く（ログ ``recall``）。番の終わりに消える
    - 進化前に持っていたワザ: 実際に重なっている進化前のカード（``evolution_stack``）のワザ（p.310「進化前に持っていたワザや特殊能力」と同じ言い方。kyuura の
      GR-2000-P310-EVOLUTION）。すぐ下のカードのワザは、最後に進化する前に持っていたワザなので使える。2 進化ポケモンのいちばん下のたねポケモンのワザは決まらない（RC2）。ポケモン育て屋さんで 1 進化を飛ばした 2 進化ポケモンは、
      重なっているたねポケモンがすぐ下のカード（飛ばした 1 進化カードは場にない）
    - 自分のワザとして使うので、必要なエネルギー・説明の条件はそのまま当てはめる（「ゆびをふる」の「必要なエネルギーがついていなくても、かまわない」とは違う）
    - 対戦ポケモンが進化していない・進化前のカードにワザがないときに使えるかは決まらない（RC1。使う前に止める）。対戦ポケモンが「ばける」でほかのポケモンとしてあつかわれて
      いるときは RC4（使う前に止める）。使ったあとに対戦ポケモンが入れかわった・進化した・姿が変わったときは、進化前のワザを選ぶと止める（RC3・RC4。``available_attacks``）
    """

    implementation_id = "recall_pre_evolution_attacks"

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        active = state.players[use.player].active
        if active is None:
            raise RuntimeError("番の途中に自分のバトル場にポケモンがいない（エンジンの不具合）")
        if current_form(state, active).kind == FORM_DISGUISE:
            raise UnsupportedError(RECALL_FORM_CODE, f"対戦ポケモン {active.pokemon_id}（のせたカード {active.disguise}）: {RECALL_FORM_REASON}")
        if not recall_stack_attacks(state, active):
            raise UnsupportedError(RECALL_WITHOUT_ATTACK_CODE, f"対戦ポケモン {active.pokemon_id}（{state.card_def(active.card).name_ja}）: {RECALL_WITHOUT_ATTACK_REASON}")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        from .state import RecallEffect

        active = state.players[use.player].active
        state.recalls = state.recalls + (RecallEffect(use.player, state.turn_number, active.pokemon_id, active.card, use.card),)
        state.add_event("recall", player=use.player, pokemon=active.card, pokemon_id=active.pokemon_id, card=use.card)


# ---------------------------------------------------------------- 退化させる効果（v0.50。docs/mew-devolution-spray-v0.50.md）

DEVOLUTION_BEAM_TEXT = "自分または相手の場にいるポケモンの中から「進化カード」のついているもの1匹を選び、その「進化カード」を上から1枚はがして持ち主の手札に戻す。"
DEVOLUTION_SPRAY_TEXT = "自分の進化ポケモンを1匹選び、進化カードを何枚でもはがしてすてることができる。"

# DV4: 自分の場に進化ポケモンがいないときに退化スプレーを使えるか。説明は「自分の進化ポケモンを1匹選び」で、選ぶものがないときの記述がない（トレーナー「サカキ」の TR1・
# 突風の GW5 と同じ形の問いだが、別のカードの問いなので答えを流用しない）
DEVOLUTION_SPRAY_WITHOUT_TARGET_CODE = "UNRESOLVED_DEVOLUTION_SPRAY_WITHOUT_TARGET"
DEVOLUTION_SPRAY_WITHOUT_TARGET_REASON = (
    "自分の場に進化ポケモン（実際に進化カードが重なっているポケモン）がいないときに退化スプレーを使えるかは、説明の「自分の進化ポケモンを1匹選び」に選ぶものがない"
    "ときの記述がなく、記録で決まらないので扱わない（DV4）"
)
# DV5: 「ばける」でのせたカードのあるタケシのキュウコン（「(ただし「進化・退化」はできない)」）を、退化させる効果で選べるか・選んだらどうなるか（のせたカードを
# 「進化カード」としてはがすのか、退化できないので何も起こらないのか）
DEVOLUTION_TARGET_DISGUISED_CODE = "UNRESOLVED_DEVOLUTION_TARGET_DISGUISED"
DEVOLUTION_TARGET_DISGUISED_REASON = (
    "「ばける」でのせたカードのあるポケモン（説明に「(ただし「進化・退化」はできない)」）を、退化させる効果で選べるか、選んだらのせたカードをはがすのか何も起こらないのかは、"
    "記録で決まらないので扱わない（DV5）"
)
# DV1: 退化スプレーで 2 枚以上はがすとき、途中の重なり（はがし終える前）で HP がのっているダメージ以下になり、最後の重なりではきぜつしない（またはカウントのされ方が
# 違う）場合。きぜつの判定をはがすたびにするか、はがし終えてからするかが記録で決まらない
DEVOLUTION_INTERMEDIATE_KNOCKOUT_CODE = "UNRESOLVED_DEVOLUTION_INTERMEDIATE_KNOCKOUT"
DEVOLUTION_INTERMEDIATE_KNOCKOUT_REASON = (
    "2 枚以上の進化カードをはがすとき、途中の重なりで HP がのっているダメージ以下になり、はがし終えた重なりではきぜつしない（またはカウントのされ方が違う）。きぜつの判定を"
    "はがすたびにするか、はがし終えてからするかが記録で決まらないので扱わない（DV1）"
)


def devolution_forbidden(state: GameState, pokemon: PokemonInPlay) -> bool:
    """v0.50: 場のポケモン ``pokemon`` を、説明が退化を禁じているか（タケシのキュウコンの「ばける」でのせたカードのあるポケモン（``disguise``）。「(ただし「進化・退化」は
    できない)」）。メタモンの［へんしん］（「このカードに進化カードをつけることはできない」）は進化カードが重ならないので、退化させる効果の対象にならない。"""
    return pokemon.disguise is not None


def devolution_candidates(state: GameState, players: Iterable[int]) -> tuple[int, ...]:
    """v0.50: プレイヤー ``players`` の順に、それぞれの場（バトル場 → ベンチ）の、実際に進化カードが重なっているポケモン（``evolution_stack`` がある）の番号。今の姿
    （［へんしん］）ではなく実際の重なりで決める（進化カードの重ならないメタモンは入らない）。説明が退化を禁じるポケモン（``devolution_forbidden``）も入れる（呼ぶ側が
    選ぶと止める選択にする。DV5）。"""
    return tuple(pokemon.pokemon_id for player in players for pokemon in state.players[player].in_play() if pokemon.evolution_stack)


@dataclass(frozen=True)
class DevolveChosenPokemon(AttackEffect):
    """自分または相手の場にいるポケモンの中から「進化カード」のついているもの 1 匹を選び、その「進化カード」を上から 1 枚はがして持ち主の手札に戻す（v0.50。ミュウの
    「たいかビーム」。ダメージの目安の数字はない。kyuura の印刷の文面）。要素 ``programs.DevolveChosenPokemon``（決定 ``select_pokemon``）。

    - 選ぶのはワザを使ったプレイヤー。選べるものは自分の場 → 相手の場の、実際に進化カードが重なっているポケモン（``devolution_candidates``）。1 匹もいなければ何もしない
      （p.309。ログ ``devolve_none``）。「ばける」のポケモンは選べるが選ぶと止める（DV5）。どれもそうなら宣言の前に止める
    - はがした進化カードは持ち主の手札（相手のポケモンなら相手の手札。使ったプレイヤーの手札に入れない）。退化の処理は ``evolution.devolve``（特殊状態・持続する効果を
      消す。p.324「19」）。ワザによるダメージではなく、ワザの効果。退化させる前に、そのポケモンの「ワザをうけない」状態・「とうめい」を評価する（``reaches`` の
      ``devolve``。自分のポケモンも「とうめい」を評価する。v0.42 の「ようせいのきせき」と同じ）
    - 退化して最大HPがのっているダメージ以下になったポケモンは、ワザのあとのきぜつの判定できぜつする（GR-2000-P323-KNOCKOUT・GR-2000-P324-DEVOLUTION。v0.48 のワザの
      効果で最大HPが下がったときと同じ）"""

    implementation_id = "devolve_chosen_pokemon"
    opponent_effect_elements = (DEVOLVE_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        what = "進化カードを 1 枚はがして手札にもどすワザ"
        return _check_form(attack, what, damage="none") + _check_exact_text(attack, what, (DEVOLUTION_BEAM_TEXT,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        label = _label(state, use)
        options = devolution_candidates(state, (use.player, 1 - use.player))
        problems = _decision_form(decision, label, kind=SELECT_POKEMON, player=use.player, choices=(1, 1), options=options)
        forbidden = tuple(pid for pid in options if devolution_forbidden(state, state.find_pokemon(pid)[1]))
        if tuple(decision.context_value("unresolved_choices", ())) != forbidden:
            problems.append(f"「{label}」の決定の、選ぶと止める選択 {decision.context_value('unresolved_choices', ())} が {forbidden}（DV5）ではない")
        return problems


def devolve_count_problems(state: GameState, player: int, pokemon_id: int, card: int) -> dict[int, tuple[str, str]]:
    """v0.50: 退化スプレーで場のポケモン ``pokemon_id`` からはがす枚数ごとの、選ぶと止める理由（DV1）。状態の複製の上で 1 枚ずつはがして（``evolution.devolve``）、途中の
    重なりで HP がのっているダメージ以下になるかを、今有効な最大HP（``max_hp``。［ガスのからだ］・かがくへんかガスを含む）で求める。最後の重なりでも同じカウントのされ方で
    きぜつするなら、どちらで判定しても結果は同じなので止めない。状態は変えない。"""
    trial = state.clone()
    pokemon = trial.find_pokemon(pokemon_id)[1]
    results = []  # はがした枚数 k（1 から）ごとの (きぜつするか, カウントされるか)
    for _ in range(len(pokemon.evolution_stack)):
        devolve(trial, player, pokemon, 1, destination=DEVOLVE_TO_DISCARD, by_player=player, trainer=card)
        results.append((pokemon.damage >= max_hp(trial, pokemon), counts_as_knockout(trial, pokemon)))
    problems = {}
    for count in range(2, len(results) + 1):
        first = next((k for k in range(count - 1) if results[k][0]), None)
        if first is None:
            continue
        final_ko, final_counted = results[count - 1]
        if not final_ko or final_counted != results[first][1]:
            problems[count] = (DEVOLUTION_INTERMEDIATE_KNOCKOUT_CODE,
                               f"場のポケモン {pokemon_id} から {count} 枚: {DEVOLUTION_INTERMEDIATE_KNOCKOUT_REASON}")
    return problems


@dataclass(frozen=True)
class DevolveOwnPokemon(TrainerEffect):
    """自分の進化ポケモンを 1 匹選び、進化カードを何枚でもはがしてすてることができる（v0.50。退化スプレー（PMCG1-086）。kyuura の印刷の文面。docs/mew-devolution-spray-v0.50.md
    4 章）。

    - 段階 1: 使ったプレイヤーが、自分の場の、実際に進化カードが重なっているポケモン（``devolution_candidates``）を 1 匹選ぶ（決定 ``select_pokemon``）。1 匹もいなければ
      使えるかが決まらない（DV4。使う前）。「ばける」のポケモンは選べるが選ぶと止める（DV5。どれもそうなら使う前）
    - 段階 2: はがす枚数（決定 ``select_devolve_count``。0〜重なっている進化カードの数。上から順にはがす）。0 枚は「ことができる」の、はがさないこと（何もしない。ログ
      ``devolve_declined``。退化していないので特殊状態も消さない）。途中の重なりできぜつするかで結果が変わる枚数は選ぶと止める（DV1。``devolve_count_problems``）
    - はがした進化カードは持ち主（使ったプレイヤー）のトラッシュ（手札にもどさない）。退化の処理は ``evolution.devolve``
    - 使い終わって（カードをトラッシュして）から、退化で最大HPがのっているダメージ以下になったポケモンは「きぜつ」する（``may_knock_out``。``resolution.after_trainer``。
      サイド → 勝ち負け → バトル場に出す → 同じ番の続き）。根拠: p.323「16」（HP 以上のダメージを受けると「きぜつ」）・p.319（ダメージカウンター 1 個は 10 ダメージを
      受けていることを表す）・p.324「19」（退化前の進化カードに書かれている内容のすべては無効）・p.324「16」の続き（「ワザや特殊能力などによって引き起こされることがら」）。
      SUPPORTED（第4版の冊子の「退化してダメージが HP 以上ならきぜつ」は別の版の記録なので根拠にしない）
    """

    implementation_id = "devolve_own_pokemon"
    may_knock_out = True

    def _candidates(self, state: GameState, player: int) -> tuple[int, ...]:
        return devolution_candidates(state, (player,))

    def _forbidden(self, state: GameState, candidates: Iterable[int]) -> tuple[int, ...]:
        return tuple(pid for pid in candidates if devolution_forbidden(state, state.find_pokemon(pid)[1]))

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        candidates = self._candidates(state, use.player)
        if not candidates:
            raise UnsupportedError(DEVOLUTION_SPRAY_WITHOUT_TARGET_CODE, DEVOLUTION_SPRAY_WITHOUT_TARGET_REASON)
        if len(self._forbidden(state, candidates)) == len(candidates):
            raise UnsupportedError(DEVOLUTION_TARGET_DISGUISED_CODE, DEVOLUTION_TARGET_DISGUISED_REASON)

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        candidates = self._candidates(state, use.player)
        push_trainer_decision(state, use, kind=SELECT_POKEMON, player=use.player, options=candidates, unresolved_choices=self._forbidden(state, candidates),
                              unresolved_code=DEVOLUTION_TARGET_DISGUISED_CODE, unresolved_reason=DEVOLUTION_TARGET_DISGUISED_REASON)

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if decision.kind == SELECT_POKEMON:
            (target,) = choices
            pokemon = state.players[use.player].find_by_pokemon_id(target)
            if pokemon is None or not pokemon.evolution_stack or devolution_forbidden(state, pokemon):
                raise RuntimeError(f"退化スプレーで選んだポケモン {target} から進化カードをはがせない（決定の確認の漏れ。エンジンの不具合）")
            stops = devolve_count_problems(state, use.player, target, use.card)
            push_trainer_decision(state, use, kind=SELECT_DEVOLVE_COUNT, player=use.player, options=range(len(pokemon.evolution_stack) + 1),
                                  context=(("target", target),), unresolved_choices=tuple(stops),
                                  unresolved_code=DEVOLUTION_INTERMEDIATE_KNOCKOUT_CODE, unresolved_reason=DEVOLUTION_INTERMEDIATE_KNOCKOUT_REASON,
                                  unresolved_detail=tuple((count, code, reason) for count, (code, reason) in stops.items()))
            return
        (count,) = choices
        target = decision.context_value("target")
        pokemon = state.players[use.player].find_by_pokemon_id(target)
        if pokemon is None or not 0 <= count <= len(pokemon.evolution_stack):
            raise RuntimeError(f"退化スプレーではがす枚数 {count}・ポケモン {target} が正しくない（決定の確認の漏れ。エンジンの不具合）")
        if count == 0:
            state.add_event("devolve_declined", player=use.player, pokemon=pokemon.card, pokemon_id=target, trainer_card=use.card)
            return
        devolve(state, use.player, pokemon, count, destination=DEVOLVE_TO_DISCARD, by_player=use.player, trainer=use.card)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = "「退化スプレー」"
        candidates = self._candidates(state, use.player)
        if decision.kind == SELECT_POKEMON:
            return _select_own_pokemon_problems(decision, use, candidates, what, self._forbidden(state, candidates))
        if decision.kind != SELECT_DEVOLVE_COUNT:
            return [f"{what}の決定の種類が {decision.kind!r}（{SELECT_POKEMON}・{SELECT_DEVOLVE_COUNT} のはず）"]
        problems = []
        if decision.player != use.player:
            problems.append(f"{what}の決定を決定するのがプレイヤー {decision.player} で、使ったプレイヤー {use.player} ではない")
        target = decision.context_value("target", None)
        pokemon = state.players[use.player].find_by_pokemon_id(target) if isinstance(target, int) else None
        if pokemon is None or target not in candidates or devolution_forbidden(state, pokemon):
            return problems + [f"{what}のはがす枚数の決定の target {target!r} が、選べる自分の進化ポケモンではない"]
        if (decision.min_choices, decision.max_choices) != (1, 1) or decision.options != tuple(range(len(pokemon.evolution_stack) + 1)):
            problems.append(f"{what}のはがす枚数の決定の選べるもの {decision.options}・選ぶ数が、0〜{len(pokemon.evolution_stack)} から 1 つではない")
        stops = tuple(devolve_count_problems(state, use.player, target, use.card))
        if tuple(decision.context_value("unresolved_choices", ())) != stops:
            problems.append(f"{what}のはがす枚数の決定の、選ぶと止める選択 {decision.context_value('unresolved_choices', ())} が {stops}（DV1）ではない")
        return problems


# ---------------------------------------------------------------- トラッシュのたねポケモンを持ち主のベンチに出す効果（v0.51。docs/discard-to-bench-v0.51.md）

INVIGORATE_TEXT = "自分または相手のトラッシュから「たねポケモン」を1枚選び出し、持ち主のベンチに出す。そして、そのポケモンに、HPの半分(切り捨て)のダメージカウンターをのせる。"
PENDULUM_CURSE_TEXT = "相手にのっているダメージカウンターの数だけコインを投げ、「おもて」の数×{per}のダメージ。"
REVIVE_TEXT = "トラッシュからポケモンカードを1枚選んで、HPの半分(きりすて)のダメージカウンターをのせた状態でベンチに出すことができる。進化カードを選ぶことはできない。"
POKEMON_FLUTE_TEXT = "相手のトラッシュからポケモンカードを1枚選び、相手のベンチに出させることができる。ただし進化カードを選ぶことはできない。"

# RV1: 自分のトラッシュにたねポケモンのカードがない・自分のベンチに空きがないときに元気のかけらを使えるか。印刷の文面は「…ベンチに出すことができる。」で、出せないときの
# 記述がない。kyuura の再録の文面の書き換えの記録（ポケモンジム第1弾の版は「…このカードは使えない」を加えた。区分「書き方だけ」）は、v0.21 の突風（GW5）と同じく、処理に
# 使う文面を補う根拠にしない（記録の文面ではなく、処理の文面の区分の判断）
REVIVE_WITHOUT_TARGET_CODE = "UNRESOLVED_REVIVE_WITHOUT_TARGET"
REVIVE_WITHOUT_TARGET_REASON = (
    "自分のトラッシュにたねポケモンのカードがない・自分のベンチに空きがないときに元気のかけらを使えるかは、印刷の文面（「…ベンチに出すことができる。」）に出せないときの"
    "記述がなく、記録で決まらないので扱わない（RV1。kyuura の再録の文面の書き換えの記録の「書き方だけ」で、のちの版の「…このカードは使えない」を補わない）"
)
# FT1: 相手のトラッシュにたねポケモンのカードがない・相手のベンチに空きがないときにポケモンの笛を使えるか（RV1 と同じ形の問いだが、別のカードの問いなので答えを流用しない。
# ポケモンの笛には文面の書き換えの記録もない）
POKEMON_FLUTE_WITHOUT_TARGET_CODE = "UNRESOLVED_POKEMON_FLUTE_WITHOUT_TARGET"
POKEMON_FLUTE_WITHOUT_TARGET_REASON = (
    "相手のトラッシュにたねポケモンのカードがない・相手のベンチに空きがないときにポケモンの笛を使えるかは、印刷の文面（「…相手のベンチに出させることができる。」）に出せない"
    "ときの記述がなく、記録で決まらないので扱わない（FT1）"
)


def discard_basic_pokemon(state: GameState, player: int) -> tuple[int, ...]:
    """v0.51: プレイヤー ``player`` のトラッシュの、たねポケモンのカード（トラッシュの並び）。トラッシュにある間のカードの定義（印刷の定義。``state.card_def``）で決めるので、
    進化カード・エネルギーカード・トレーナーカード（なにかの化石・ピッピ人形も、トラッシュではトレーナーカード。v0.47）は入らない。「ポケモンカード」で「進化カードを
    選ぶことはできない」（元気のかけら・ポケモンの笛）と「たねポケモン」（よみがえらせる）は、どちらもこの集まり（ベイビィポケモンは写しにない。cards.py が拒否する）。"""
    return tuple(uid for uid in state.players[player].discard if state.card_def(uid).is_basic_pokemon)


def bench_has_space(state: GameState, player: int) -> bool:
    """v0.51: プレイヤー ``player`` のベンチに空きがあるか（共通のルールの値 ``rules.max_bench``。p.312）。"""
    return len(state.players[player].bench) < state.rules.max_bench


def bench_from_discard_candidates(state: GameState, players: Iterable[int]) -> tuple[int, ...]:
    """v0.51: プレイヤー ``players`` の順に、それぞれのトラッシュのたねポケモンのカードのうち、持ち主のベンチに空きがあるもの（持ち主のベンチに出せるもの）。ベンチの空きは
    カードの持ち主の側で確かめる（よみがえらせるで、自分のベンチがいっぱいでも、相手のベンチに空きがあれば相手のトラッシュのカードは選べる）。"""
    return tuple(uid for player in players if bench_has_space(state, player) for uid in discard_basic_pokemon(state, player))


def half_hp_counters(state: GameState, hp: int | None) -> int:
    """v0.51: 「HPの半分(切り捨て)のダメージカウンター」の数。ダメージカウンター 1 個は 10 ダメージ（p.319。GR-2000-P319-HP-AND-DAMAGE）なので、HP をダメージカウンターの
    数で表して半分にし、切りすてる（HP 70 なら 3 個、50 なら 2 個）。半分の丸めをダメージカウンターの単位でするのは、v0.46 のリフレクター（「半分(切りすて)」）・v0.45 の
    「いかりのまえば」（「半分（切り上げ）」）と同じ。HP がダメージカウンターの単位の正の倍数でなければエンジンの不具合。"""
    per = state.rules.damage_per_counter
    if not isinstance(hp, int) or hp <= 0 or hp % per:
        raise RuntimeError(f"HP {hp!r} が、ダメージカウンターの単位の正の倍数ではない（エンジンの不具合）")
    return hp // per // 2


def discard_entry_power_guard(state: GameState, card: int) -> None:
    """v0.51: トラッシュから場に出すカード ``card`` に、場に出たときに使える特殊能力（``EntryPower``）があるかを、出す前に確かめる。「手札から出した時」「手札から場に出した時」
    の特殊能力（``from_hand_only``）は、トラッシュから出すと経路が合わないので使う機会はない（手札から出したことにしない）。「場に出た時」の特殊能力（わるいカイリューの
    ［てしたをよぶ］）は、トラッシュから出すときに機会を出すかを決めていない（ワザの最中なら v0.43 の PW4 の場面）。今の対応カードでは、場に出たときの特殊能力を持つカードは
    どれも進化カード（トラッシュから出せるたねポケモンにはない。tests/test_discard_to_bench_v0_51.py が登録を確かめる）なので起こらない。来たら ``RuntimeError``（状態を
    変える前）。"""
    found = entry_power(state, card)
    if found is not None and not found[1].from_hand_only:
        raise RuntimeError(f"トラッシュから場に出すカード {card} に、場に出たときに使える特殊能力がある（トラッシュからの経路の使う機会は未対応。エンジンの不具合）")


def log_bench_from_discard(state: GameState, pokemon: PokemonInPlay, *, by_player: int, source: dict[str, Any], counters: int | None = None) -> None:
    """v0.51: トラッシュから持ち主のベンチに出したログ ``bench_from_discard``（公開。トラッシュと場は公開の情報）。

    ``player`` はカードの持ち主（カードを置いていたトラッシュと、出したベンチの持ち主）、``by_player`` は効果を使って選んだプレイヤー、``card``・``to_pokemon_id``（新しい
    場のポケモンの番号）。場に出た番はこのログの番（``played_turn`` と同じ）。``source`` は効果の出どころ（ワザなら ``pokemon``・``pokemon_id``・``effect``、トレーナーなら
    ``trainer_card``・``trainer``）。``counters`` は、ベンチに出す前にのせた（「のせた状態でベンチに出す」）ダメージカウンターの数で、そのときだけ ``counters``・``damage`` を
    書く（よみがえらせるは、出したあとの ``place_damage_counters``）。"""
    owner = state.cards[pokemon.card].owner
    extra = {} if counters is None else {"counters": counters, "damage": pokemon.damage}
    state.add_event("bench_from_discard", player=owner, by_player=by_player, card=pokemon.card, from_zone="discard", to_zone="bench",
                    to_pokemon_id=pokemon.pokemon_id, **source, **extra)


@dataclass(frozen=True)
class BenchBasicFromEitherDiscard(AttackEffect):
    """自分または相手のトラッシュから「たねポケモン」を 1 枚選び出し、持ち主のベンチに出す。そして、そのポケモンに、HP の半分（切り捨て）のダメージカウンターをのせる
    （v0.51。ナツメのスリーパーの「よみがえらせる」。ダメージの目安の数字はない。kyuura の印刷の文面）。要素 ``programs.BenchFromEitherDiscard``（決定 ``bench_from_discard``）。

    - 選ぶのはワザを使ったプレイヤー。選べるものは自分のトラッシュ → 相手のトラッシュの、たねポケモンのカードのうち、持ち主のベンチに空きがあるもの
      （``bench_from_discard_candidates``）。1 枚（「選び出し、…出す」。省略できない）。1 枚もなければ何もしない（p.309。GR-2000-P309-ATTACK-PROCEDURE。ログ
      ``bench_from_discard_none``）。相手のカードは相手のベンチに出す（自分のベンチに出さない）
    - 出す処理は ``zones.bench_from_discard``（同じ uid。新しい場のポケモンの番号。場に出た番は今の番。前に場にいたときのものは引き継がない）。トラッシュのカードを出すことは
      場のポケモンへの効果ではない（「ワザをうけない」状態・「とうめい」はトラッシュのカードには関係しない）
    - そのあと、出したポケモンの今有効な最大HP（``max_hp``）の半分（ダメージカウンターの単位で切り捨て。``half_hp_counters``）のダメージカウンターをのせる。ワザによる
      ダメージではない（GR-2000-P320-COUNTER-MOVE と同じ読み方。弱点・抵抗力・プラスパワー・ディフェンダー・「ダメージを受けたとき」の効果は関係しない）。場のポケモンへの
      ワザの効果なので、のせる前に「ワザをうけない」状態・「とうめい」を評価する（``reaches`` の ``damage_counters``。自分のポケモンも「とうめい」を評価する）。ログ
      ``place_damage_counters``（v0.41 と同じ形）。半分なので HP 以上にはならない（きぜつしない）
    """

    implementation_id = "bench_basic_from_either_discard"
    opponent_effect_elements = (COUNTERS_ELEMENT,)

    def check(self, attack: Attack) -> list[str]:
        what = "トラッシュのたねポケモンを持ち主のベンチに出すワザ"
        return _check_form(attack, what, damage="none") + _check_exact_text(attack, what, (INVIGORATE_TEXT,))

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        options = bench_from_discard_candidates(state, (use.player, 1 - use.player))
        return _decision_form(decision, _label(state, use), kind=BENCH_FROM_DISCARD, player=use.player, choices=(1, 1), options=options)


@dataclass(frozen=True)
class CoinsPerDefenderCountersDamage(AttackEffect):
    """相手（相手の対戦ポケモン）にのっているダメージカウンターの数だけコインを投げ、「おもて」の数 × ``per`` のダメージ（v0.51。ナツメのスリーパーの「ふりこののろい」。
    ダメージの目安「20×」。kyuura の印刷の文面）。要素 ``Damage(OPP, programs.HeadsPerDefenderCounters(per))``。

    - 「相手」は相手の対戦ポケモン（p.320。v0.46 のバリヤードの「ヨガのポーズ」の「相手にのっている」と同じ。CD4 の「相手のポケモン」には当たらない）
    - コインの枚数は、ダメージの要素を処理する時点の相手の対戦ポケモンのダメージカウンターの数（ダメージ ÷ 10）。0 個ならコインを投げず、基本となるダメージは 0（ダメージを
      与えない。p.321。v0.32 の「じたばた」と同じ）。「おもて」の数 × ``per`` が p.321 の 1 段階（基本となるダメージ）で、弱点・抵抗力・プラスパワー・ディフェンダーなどは
      そのあとの段階（最終ダメージに直接足さない）
    - コイン 1 枚で「おもて」ならカウンターの数 × 20 の「いかりのスーパーパンチ」（``CoinHeadsDamagePerOwnCounter``）・自分のカウンターの「じたばた」とは別の型
    - コインはこのダメージの量だけを決めるので、ダメージを受けない状態の相手には投げるかが決められない（v0.4b の ``UNRESOLVED_PREVENTED_COIN_DAMAGE``。投げる枚数が 1 枚以上の
      ときだけ）。先読みは「おもて」の数でまとめる（``by_heads``。v0.35）。実際の対戦では 1 枚ずつ投げる（乱数・ログは v0.35 の ``CoinFlipDamage`` と同じ）
    """

    per: int
    implementation_id = "coins_per_defender_counters_damage"

    def check(self, attack: Attack) -> list[str]:
        what = "相手のダメージカウンターの数だけコインを投げるワザ"
        problems = _check_form(attack, what, damage="modified", modifier="×")
        if attack.damage != self.per:
            problems.append(f"ダメージの目安の数字 {attack.damage} が、登録の「おもて」1 回あたりのダメージ {self.per} と違う")
        return problems + _check_exact_text(attack, what, (PENDULUM_CURSE_TEXT.format(per=self.per),))


class _BenchBasicFromDiscardTrainer(TrainerEffect):
    """v0.51: トラッシュのたねポケモンのカードを、使ったプレイヤーが選んで、持ち主のベンチに出す（「ことができる」）トレーナーの共通の部分（元気のかけら・ポケモンの笛）。

    - 選ぶのは使ったプレイヤー（決定 ``bench_from_discard``。0〜1 枚。0 枚は「ことができる」の、出さないこと（ログ ``bench_from_discard_declined``。v0.50 の退化スプレーの
      0 枚と同じ読み方））。選べるものは ``from_player`` のトラッシュのたねポケモンのカード（トラッシュの並び）
    - 使う前に、選べるカードがない・その持ち主のベンチに空きがない（出せない）なら、使えるかが決まらないので止める（``without_target``。手札から出す前。状態・乱数・ログを
      変えない）。決定を待つ間は場が変わらないので、答えのときにも同じ選べるもの
    - 出したポケモンは、きぜつしない（元気のかけらのカウンターは HP の半分）ので、使い終えたあとのきぜつの処理（``may_knock_out``）はしない
    """

    text: ClassVar[str]
    without_target: ClassVar[tuple[str, str]]

    def from_player(self, use: TrainerUse) -> int:
        raise NotImplementedError

    def counters(self, state: GameState, card: int) -> int | None:
        return None

    def check(self, definition: CardDefinition) -> list[str]:
        problems = super().check(definition)
        if definition.trainer_text_ja != self.text:
            problems.append(f"文面 {definition.trainer_text_ja!r} が、{self.implementation_id} の文面ではない")
        return problems

    def candidates(self, state: GameState, use: TrainerUse) -> tuple[int, ...]:
        return bench_from_discard_candidates(state, (self.from_player(use),))

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        owner = self.from_player(use)
        if not self.candidates(state, use):
            code, reason = self.without_target
            scene = "ベンチに空きがない" if discard_basic_pokemon(state, owner) else "トラッシュにたねポケモンのカードがない"
            raise UnsupportedError(code, f"{reason}。プレイヤー {owner} の{scene}")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        push_trainer_decision(state, use, kind=BENCH_FROM_DISCARD, player=use.player, options=self.candidates(state, use), min_choices=0, max_choices=1)

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        source = {"trainer_card": use.card, "trainer": use.card_id}
        if not choices:
            state.add_event("bench_from_discard_declined", player=self.from_player(use), by_player=use.player, **source)
            return
        (card,) = choices
        if card not in self.candidates(state, use):
            raise RuntimeError(f"{self.implementation_id} で選んだカード {card} が、選べるトラッシュのたねポケモンのカードではない（決定の確認の漏れ。エンジンの不具合）")
        discard_entry_power_guard(state, card)
        counters = self.counters(state, card)
        pokemon = bench_from_discard(state, card, counters=counters or 0)
        log_bench_from_discard(state, pokemon, by_player=use.player, source=source, counters=counters)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = f"トレーナー {use.card_id}"
        problems = []
        if decision.kind != BENCH_FROM_DISCARD:
            problems.append(f"{what}の決定の種類が {decision.kind!r}（{BENCH_FROM_DISCARD} のはず）")
        if decision.player != use.player:
            problems.append(f"{what}の決定をするのがプレイヤー {decision.player}（使ったプレイヤー {use.player} のはず）")
        if (decision.min_choices, decision.max_choices) != (0, 1):
            problems.append(f"{what}で選ぶ数が {decision.min_choices}〜{decision.max_choices}（0〜1 のはず）")
        expected = self.candidates(state, use)
        if decision.options != expected:
            problems.append(f"{what}の決定の選べるもの {decision.options} が、トラッシュの出せるたねポケモンのカード {expected} と合わない")
        return problems


@dataclass(frozen=True)
class BenchBasicFromOwnDiscardWithCounters(_BenchBasicFromDiscardTrainer):
    """トラッシュからポケモンカードを 1 枚選んで、HP の半分（きりすて）のダメージカウンターをのせた状態でベンチに出すことができる。進化カードを選ぶことはできない（v0.51。
    元気のかけら（PMCG1-078）。kyuura の印刷の文面）。

    - 「トラッシュ」「ベンチ」は使ったプレイヤーのもの（相手のトラッシュを指すポケモンの笛の「相手の」がない。実装上の読み方。docs/discard-to-bench-v0.51.md 4 章）。選べる
      ものは自分のトラッシュのたねポケモンのカード（「ポケモンカード」で進化カードは選べない）
    - のせるダメージカウンターの数は、そのカードの HP（トラッシュにある間のカードの定義の値）の半分（ダメージカウンターの単位で切り捨て。``half_hp_counters``）。カウンターを
      のせた状態で場に出す（``zones.bench_from_discard`` の ``counters``。よみがえらせるの「ベンチに出す。そして、…のせる」とは順番が違う。今の対応カードのたねポケモンでは、
      ベンチに出した直後の今有効な最大HPは印刷の HP と同じで、のせる数は変わらない。tests が登録のすべてのたねポケモンで確かめる）
    - 使えるか決まらない場面は RV1（自分のトラッシュにたねポケモンのカードがない・自分のベンチに空きがない）
    """

    implementation_id = "bench_basic_from_own_discard_with_counters"
    text: ClassVar[str] = REVIVE_TEXT
    without_target: ClassVar[tuple[str, str]] = (REVIVE_WITHOUT_TARGET_CODE, REVIVE_WITHOUT_TARGET_REASON)

    def from_player(self, use: TrainerUse) -> int:
        return use.player

    def counters(self, state: GameState, card: int) -> int | None:
        return half_hp_counters(state, state.card_def(card).hp)


@dataclass(frozen=True)
class BenchBasicFromOpponentDiscard(_BenchBasicFromDiscardTrainer):
    """相手のトラッシュからポケモンカードを 1 枚選び、相手のベンチに出させることができる。ただし進化カードを選ぶことはできない（v0.51。ポケモンの笛（PMCG1-084）。kyuura の
    印刷の文面）。

    - 選ぶのは使ったプレイヤー（「選び」の主語。出される側の相手に選ばせない）。選べるものは相手のトラッシュのたねポケモンのカード。出すのは相手のベンチ（カードの持ち主）
    - ダメージカウンターはのせない（ほかの 2 枚の処理を当てはめない）
    - 使えるか決まらない場面は FT1（相手のトラッシュにたねポケモンのカードがない・相手のベンチに空きがない）
    """

    implementation_id = "bench_basic_from_opponent_discard"
    text: ClassVar[str] = POKEMON_FLUTE_TEXT
    without_target: ClassVar[tuple[str, str]] = (POKEMON_FLUTE_WITHOUT_TARGET_CODE, POKEMON_FLUTE_WITHOUT_TARGET_REASON)

    def from_player(self, use: TrainerUse) -> int:
        return 1 - use.player


# ---------------------------------------------------------------- 場のポケモンを場から山札・手札にもどすトレーナー（v0.52。docs/field-return-v0.52.md）

MR_FUJI_TEXT = "自分の控えポケモンを1匹選び、そのカードとそれについているカード全てを自分の山札にもどす。その後、その山札をよくきる。"
SCOOP_UP_TEXT = ("自分の場のポケモン1匹を手札に戻す。そのポケモンのダメージカウンター、エネルギーカード、進化カードは全てはがしてすてる。バトル場のポケモンを手札に戻す"
                 "ときは、ベンチからポケモンをバトル場にだす。")

# FJ1: 自分に控えポケモンがいないときにフジろうじんを使えるか。印刷の文面は「自分の控えポケモンを1匹選び、…」で、選べないときの記述がない（「使えない」と書かれて
# いない）。ほかのカードの問い（突風の GW5・サカキの TR1・元気のかけらの RV1）の答えを流用しない
MR_FUJI_WITHOUT_BENCH_CODE = "UNRESOLVED_MR_FUJI_WITHOUT_BENCH"
MR_FUJI_WITHOUT_BENCH_REASON = (
    "自分に控えポケモンがいないときにフジろうじんを使えるかは、印刷の文面（「自分の控えポケモンを1匹選び、…」）に選べないときの記述がなく、記録で決まらないので扱わない"
    "（FJ1。ほかのカードの「対象がない」ときの問いの答えを流用しない）"
)
# SU1: ポケモン回収で手札にもどすポケモンにトレーナーカード（プラスパワー・ディフェンダー）がついているときの、そのトレーナーカードの行き先。日本語の文面は
# 「ダメージカウンター、エネルギーカード、進化カードは全てはがしてすてる」で、トレーナーカードを挙げていない。英語版の「(Discard all cards attached to that card.)」は
# 日本語版の処理の根拠にしない。場をはなれたポケモンについていたカードの行き先の一般の規定は、kyuura の記録（GR-2000-P322-PERSISTENT-EFFECTS・P323-KNOCKOUT・P312-FIELD）
# にない（きぜつのトラッシュは「きぜつ」の規定）
SCOOP_UP_ATTACHED_TRAINER_CODE = "UNRESOLVED_SCOOP_UP_ATTACHED_TRAINER"
SCOOP_UP_ATTACHED_TRAINER_REASON = (
    "ポケモン回収で手札にもどすポケモンについているトレーナーカード（プラスパワー・ディフェンダー）の行き先（トラッシュ・手札・そのほか）は、日本語の文面（「ダメージ"
    "カウンター、エネルギーカード、進化カードは全てはがしてすてる」）に書かれておらず、記録で決まらないので扱わない（SU1。英語版の「all cards attached」は持ち込まない）"
)
# SU2: 自分の場のポケモンがバトル場の 1 匹だけ（控えがいない）のときに、そのポケモンをポケモン回収で手札にもどせるか。文面の「バトル場のポケモンを手札に戻すときは、
# ベンチからポケモンをバトル場にだす」をしたがえない。使えない・使って場にポケモンがいなくなる（p.311 で負け）のどちらも記録で決まらない
SCOOP_UP_LAST_POKEMON_CODE = "UNRESOLVED_SCOOP_UP_LAST_POKEMON"
SCOOP_UP_LAST_POKEMON_REASON = (
    "控えポケモンがいないときにバトル場のポケモンをポケモン回収で手札にもどせるか（文面の「ベンチからポケモンをバトル場にだす」をしたがえない）は、記録で決まらないので"
    "扱わない（SU2。ほかのカードの使うための条件を持ち込まない）"
)


@dataclass(frozen=True)
class ReturnBenchedPokemonToDeck(TrainerEffect):
    """自分の控えポケモンを 1 匹選び、そのカードとそれについているカード全てを自分の山札にもどす。その後、その山札をよくきる（v0.52。フジろうじん（PMCG3-048）。kyuura の
    印刷の文面。docs/field-return-v0.52.md 3 章）。

    - 選ぶのは使ったプレイヤー（決定 ``select_pokemon``。選べるものは自分のベンチのポケモン。バトル場のポケモン・相手のポケモンは選べない）
    - もどすのは、重なったカード（進化カード・「ばける」でのせた進化カード）・エネルギーカード・トレーナーカードのすべて（``zones.return_in_play_to_deck``。v0.36 のワザと
      同じ関数を、トレーナーの出どころ ``trainer`` で呼ぶ）→ 持続する効果を消す（理由 ``return_in_play_to_deck``）→ 自分の山札を切る（``zones.shuffle_deck``）。きぜつでは
      ない（サイドは取られない）。ダメージカウンター・特殊状態はなくなる
    - 自分に控えポケモンがいなければ使えるか決まらない（FJ1。使う前）
    """

    implementation_id = "return_benched_pokemon_to_deck"

    def _candidates(self, state: GameState, player: int) -> tuple[int, ...]:
        return tuple(pokemon.pokemon_id for pokemon in state.players[player].bench)

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if not self._candidates(state, use.player):
            raise UnsupportedError(MR_FUJI_WITHOUT_BENCH_CODE, MR_FUJI_WITHOUT_BENCH_REASON)

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        push_trainer_decision(state, use, kind=SELECT_POKEMON, player=use.player, options=self._candidates(state, use.player))

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        (target,) = choices
        p = state.players[use.player]
        pokemon = next((b for b in p.bench if b.pokemon_id == target), None)
        if pokemon is None:
            raise RuntimeError(f"フジろうじんで選んだポケモン {target} が自分の控えにいない（決定の確認の漏れ。エンジンの不具合）")
        return_in_play_to_deck(state, use.player, pokemon, trainer=use.card)
        remove_persistent_effects(state, use.player, pokemon, RETURN_IN_PLAY_TO_DECK)
        shuffle_deck(state, use.player)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        return _select_own_pokemon_problems(decision, use, self._candidates(state, use.player), "「フジろうじん」")


@dataclass(frozen=True)
class ReturnOwnPokemonBasicToHand(TrainerEffect):
    """自分の場のポケモン 1 匹を手札に戻す。そのポケモンのダメージカウンター、エネルギーカード、進化カードは全てはがしてすてる。バトル場のポケモンを手札に戻すときは、
    ベンチからポケモンをバトル場にだす（v0.52。ポケモン回収（PMCG1-092）。kyuura の印刷の文面。docs/field-return-v0.52.md 3 章）。

    - 選ぶのは使ったプレイヤー（決定 ``select_pokemon``。選べるものは自分の場のポケモン（バトル場 → ベンチの順））
    - 手札にもどすのは重なりのいちばん下のカードだけ。進化カード（「ばける」でのせたカードも進化カード）・エネルギーカードはトラッシュ、ダメージカウンターはカードでは
      ないのでなくなる（``zones.return_basic_to_hand``）→ 持続する効果を消す（理由 ``return_in_play_to_hand``）。v0.42 の ``return_in_play_to_hand``（すべて手札へ）は
      使わない。きぜつではない（サイドは取られない）
    - バトル場のポケモンを手札にもどしたら、使い終えて（カードをトラッシュして）から、使ったプレイヤーが控えからバトル場に出す（``empties_active``。
      ``resolution.after_trainer`` の勝ち負けの判定 → バトル場に出す決定 → 同じ番の続き。きぜつのあとと同じ ``promote_active``）
    - 選ぶと止める: トレーナーカードがついているポケモン（SU1）、控えがいないときのバトル場のポケモン（SU2）。どのポケモンもそうなら使う前に止める
    """

    implementation_id = "return_own_pokemon_basic_to_hand"
    empties_active = True

    def _candidates(self, state: GameState, player: int) -> tuple[int, ...]:
        return tuple(pokemon.pokemon_id for pokemon in state.players[player].in_play())

    def stops(self, state: GameState, player: int) -> tuple[tuple[int, str, str], ...]:
        """選ぶと止める選択ごとの (場のポケモンの番号, コード, 理由)（選べるものの並び）。トレーナーカードのついたポケモンは SU1、控えのいないバトル場のポケモンは SU2
        （両方に当たれば SU1）。"""
        p = state.players[player]
        found = []
        for pokemon in p.in_play():
            if pokemon.trainers:
                found.append((pokemon.pokemon_id, SCOOP_UP_ATTACHED_TRAINER_CODE, SCOOP_UP_ATTACHED_TRAINER_REASON))
            elif pokemon is p.active and not p.bench:
                found.append((pokemon.pokemon_id, SCOOP_UP_LAST_POKEMON_CODE, SCOOP_UP_LAST_POKEMON_REASON))
        return tuple(found)

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        candidates = self._candidates(state, use.player)
        stops = self.stops(state, use.player)
        if not candidates:
            raise RuntimeError(f"プレイヤー {use.player} の場にポケモンがいない（エンジンの不具合）")
        if len(stops) == len(candidates):
            raise UnsupportedError(stops[0][1], stops[0][2])

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        stops = self.stops(state, use.player)
        push_trainer_decision(state, use, kind=SELECT_POKEMON, player=use.player, options=self._candidates(state, use.player),
                              unresolved_choices=tuple(pid for pid, _, _ in stops),
                              unresolved_code=stops[0][1] if stops else "UNRESOLVED_RULING", unresolved_reason=stops[0][2] if stops else "",
                              unresolved_detail=stops)

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        (target,) = choices
        p = state.players[use.player]
        pokemon = p.find_by_pokemon_id(target)
        if pokemon is None or pokemon.trainers or (pokemon is p.active and not p.bench):
            raise RuntimeError(f"ポケモン回収で選んだポケモン {target} を手札にもどせない（決定の確認の漏れ。エンジンの不具合）")
        return_basic_to_hand(state, use.player, pokemon, trainer=use.card)
        remove_persistent_effects(state, use.player, pokemon, RETURN_IN_PLAY_TO_HAND)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        stops = self.stops(state, use.player)
        problems = _select_own_pokemon_problems(decision, use, self._candidates(state, use.player), "「ポケモン回収」", tuple(pid for pid, _, _ in stops))
        if tuple(decision.context_value("unresolved_detail", ())) != stops:
            problems.append(f"「ポケモン回収」の決定の選択ごとの止める理由 {decision.context_value('unresolved_detail', ())} が {stops} ではない")
        return problems


# ---------------------------------------------------------------- 山札・トラッシュからカードを選ぶトレーナー（v0.53。docs/search-retrieval-trainers-v0.53.md）

ENERGY_SEARCH_TEXT = ("自分の山札の中からエネルギーカードを1枚選び出し、手札に加える。ただし、特殊なエネルギーカード(無色2個エネルギーカードなど)を選ぶことはできない。"
                      "その後、自分の山札をよくきる。")
POKE_BALL_TEXT = ("コインを投げて「おもて」なら、自分の山札から好きなポケモンカード(進化カードも可)1枚を選び手札に加えることができる。選んだカードは相手に見せる。"
                  "その後、自分の山札をよくきる。")
BOSS_WAY_TEXT = "自分の山札から、わるいポケモンへの「進化カード」を1枚選び出し、相手プレイヤーに見せてから、手札に加える。その後、その山札をよく切る。"
BROCK_TRAINING_TEXT = ("あなたの山札から「タケシのポケモン」(たねポケモンカードまたは進化カード)を1枚選び出し、相手プレイヤーに見せてから、手札に加える。"
                       "その後、その山札をよく切る。")
MISTYS_TEARS_TEXT = ("手札からカードを1枚選んでトラッシュしなければ、このカードは使えない。あなたの山札から「水」エネルギーカードを最大2枚選び出し、相手プレイヤーに"
                     "見せてから、手札に加えてよい。その後、その山札をよく切る。")
ERIKAS_MAIDS_TEXT = ("手札からカードを2枚選んで、山札にもどす。それができない時、このカードは使えない。あなたの山札から「エリカのポケモン」を最大2枚選び出し、"
                     "相手プレイヤーに見せてから、手札に加えてよい。その後、その山札をよく切る。")
MAINTENANCE_TEXT = "手札から2枚のカードを選び山札に戻す。その後で山札をよくきってから1枚ひいて手札にする。"
ITEM_FINDER_TEXT = "手札からカードを2枚すてることによって、トラッシュの中にあるトレーナーカードを1枚とって手札に加えることができる。"
RECYCLE_TEXT = "コインを投げて「おもて」なら、自分のトラッシュから好きなカードを1枚選び、自分の山札の1番上に置く。"
NIGHTLY_GARBAGE_RUN_TEXT = ("あなたのトラッシュから、ポケモン(または進化)カードかエネルギーカード(特殊エネルギーカード以外)を最大3枚選び、相手プレイヤーに見せてから、"
                            "山札にもどす。その後、その山札をよく切る。")

# ST1: 説明が山札・トラッシュから決まったカードを 1 枚選ばせ、「てよい」「ことができる」がない（選ばずに終われると書かれていない）トレーナーで、選べるカードがないとき
# （エネルギー転送・ボスのやりかた・タケシの育て方は山札、リサイクルはトラッシュ）。使えない・使って何もしない（山札は切る）のどちらも、文面・kyuura の記録で決まらない。
# パソコン通信の CS6（山札 0 枚）・エネルギー回収の ER10・サカキの TR1・元気のかけらの RV1 など、ほかのカードの問いの答えを流用しない
SEARCH_TRAINER_WITHOUT_TARGET_CODE = "UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET"
SEARCH_TRAINER_WITHOUT_TARGET_REASON = (
    "説明が山札・トラッシュから決まったカードを1枚選ばせる（「てよい」「ことができる」と書かれていない）トレーナーで、選べるカードがないときに使えるか（使えない・使って"
    "何もしないのどちらか）は、印刷の文面・kyuura の記録で決まらないので扱わない（ST1。ほかのカードの「対象がない」ときの問いの答えを流用しない）"
)
# NG1: 夜の廃品回収の「最大3枚選び」に 0 枚が含まれるか。「てよい」「ことができる」がない（エネルギー回収の ER9・ギガスパークの GS1 と同じ言い回しの、別のカードの問い）。
# 0 枚を選んだとき（決定は待ったまま）と、トラッシュに選べるカードがないとき（使う前）の両方で止める（選べるカードがなければ、選ぶのは 0 枚しかない）
NIGHTLY_GARBAGE_RUN_ZERO_CODE = "UNRESOLVED_NIGHTLY_GARBAGE_RUN_ZERO_CHOICE"
NIGHTLY_GARBAGE_RUN_ZERO_REASON = (
    "夜の廃品回収の「最大3枚選び」が 0 枚を含むか（トラッシュから何ももどさずに山札を切って終われるか）は、印刷の文面（「てよい」「ことができる」がない）・kyuura の記録で"
    "決まらないので扱わない（NG1。エネルギー回収の ER9・ギガスパークの GS1 の答えを流用しない）"
)


@dataclass(frozen=True)
class CardFilter:
    """v0.53: トレーナーが山札・トラッシュから選べるカードの種類（説明の言葉と 1 対 1 の、決まった種類だけ。汎用の条件の書き方にしない）。

    選ぶ場所（山札・トラッシュ）では、カードの定義は印刷の定義（``GameState.card_def``。なにかの化石・ピッピ人形はトレーナーカード。v0.47）で決める。
    - ``kind``: ``"any"``（どのカードでも。リサイクルの「好きなカード」）・``"trainer"``（トレーナーカード）・``"basic_energy"``（基本エネルギーカード。``energy_type`` が
      あればそのタイプの基本エネルギーカード（カスミのなみだの「水」エネルギーカード。ほかの色として使えるエネルギーを含めない））・``"pokemon"``（たねポケモンのカード・
      進化カード。``evolution_only`` なら進化カードだけ）・``"pokemon_or_basic_energy"``（夜の廃品回収の「ポケモン(または進化)カードかエネルギーカード(特殊エネルギー
      カード以外)」）・``"basic_pokemon"``（v0.55。たねポケモンのカード。礼儀作法の「「たねポケモン」」）
    - ``name_prefix``: 名前の始まり（ボスのやりかたの「わるい」、タケシの育て方の「タケシの」、エリカのお付きの「エリカの」）。進化カードの名前で決め、進化前のポケモンの
      名前・カード id の一覧で決めない
    """

    kind: str
    energy_type: EnergyType | None = None
    name_prefix: str | None = None
    evolution_only: bool = False

    def matches(self, definition: CardDefinition) -> bool:
        pokemon = definition.is_basic_pokemon or definition.is_evolution_pokemon
        if self.kind == "any":
            ok = True
        elif self.kind == "trainer":
            ok = definition.category == "trainer"
        elif self.kind == "basic_energy":
            ok = definition.is_basic_energy and (self.energy_type is None or definition.provides is self.energy_type)
        elif self.kind == "pokemon":
            ok = definition.is_evolution_pokemon if self.evolution_only else pokemon
        elif self.kind == "basic_pokemon":
            ok = definition.is_basic_pokemon  # v0.55: 礼儀作法の「たねポケモン」（手札・山札にある間の印刷の定義。なにかの化石・ピッピ人形はトレーナーカード）
        elif self.kind == "pokemon_or_basic_energy":
            ok = pokemon or definition.is_basic_energy
        else:
            raise ValueError(f"カードの種類 {self.kind!r} は CardFilter の種類ではない")
        return ok and (self.name_prefix is None or definition.name_ja.startswith(self.name_prefix))


def deck_cards_matching(state: GameState, player: int, target: CardFilter) -> tuple[int, ...]:
    """v0.53: プレイヤーの山札の ``target`` のカード（uid の小さい順。山札の並びを決定に写さない）。"""
    return tuple(sorted(uid for uid in state.players[player].deck if target.matches(state.card_def(uid))))


def discard_cards_matching(state: GameState, player: int, target: CardFilter) -> tuple[int, ...]:
    """v0.53: プレイヤーのトラッシュの ``target`` のカード（トラッシュの並び。公開の情報）。使っている最中のトレーナーはトラッシュにない（``trainer_in_use``）。"""
    return tuple(uid for uid in state.players[player].discard if target.matches(state.card_def(uid)))


def _hand_cost_problem(state: GameState, use: TrainerUse, count: int, what: str) -> None:
    """v0.53: 使うための条件として、このカードを除く手札から ``count`` 枚を選んでトラッシュする・山札にもどすトレーナーで、手札が足りなければ拒否する（手札から出す前。
    パソコン通信・エネルギー回収と同じ ``INSUFFICIENT_CARDS_IN_HAND``）。"""
    others = [uid for uid in state.players[use.player].hand if uid != use.card]
    if len(others) < count:
        raise IllegalActionError(
            "INSUFFICIENT_CARDS_IN_HAND",
            f"このカードを除く手札が {len(others)} 枚で、使うための条件（手札からカードを{count}枚選んで{what}）を満たせない",
        )


def _trainer_coin(state: GameState, use: TrainerUse) -> bool:
    """v0.53: トレーナーの説明のコイン（モンスターボール・リサイクル）を 1 枚投げ、「おもて」なら True。投げるのは使ったプレイヤー（``coin_flip`` の ``source`` は
    ``"trainer"``・``effect`` はカード id・``card`` は使っているトレーナーのカード）。使えるかの確認はすべて投げる前に済ませる。"""
    flips = flip_coins(state, use.player, 1, source="trainer", effect=use.card_id, card=use.card)
    return flips.results[0] is CoinSide.HEADS


def _trainer_take_none(state: GameState, use: TrainerUse, zone: str, *, no_target: bool) -> None:
    """v0.53: 選ばずに終わった（「てよい」「ことができる」の 0 枚・選べるカードがない）ことのログ ``trainer_take_none``。山札をさがしたときの理由（選べるカードが
    なかった・選ばなかった）は、山札の中身の情報なので使ったプレイヤーだけが見る（``reason``。observation の PRIVATE_FIELDS）。"""
    state.add_event("trainer_take_none", player=use.player, trainer_card=use.card, zone=zone, reason="no_target" if no_target else "declined")


def _last_trainer_events(state: GameState, use: TrainerUse) -> list[dict]:
    """v0.53: 今のログの最後のこのカードの ``play_trainer`` からあとのイベント（決定の不変条件が、すんだ段階を確かめる）。"""
    since = max((i for i, e in enumerate(state.log) if e["kind"] == "play_trainer" and e["card"] == use.card), default=None)
    return [] if since is None else list(state.log[since:])


@dataclass(frozen=True)
class SearchDeckTrainer(TrainerEffect):
    """v0.53: 自分の山札から ``target`` のカードを最大 ``count`` 枚選び出して手札に加え、その山札を切るトレーナーの共通の処理（エネルギー転送・モンスターボール・
    ボスのやりかた・タケシの育て方・カスミのなみだ・エリカのお付き。どれも kyuura の印刷の文面。docs/search-retrieval-trainers-v0.53.md 3 章）。

    - 使うための条件（``discard_cost``・``return_cost``）: このカードを除く手札から決まった枚数をトラッシュする（カスミのなみだ）・山札にもどす（エリカのお付き。見せる指示が
      ないので ``zones.return_hand_cards_to_deck``。ログ ``hand_to_deck`` の ``cards`` は使ったプレイヤーだけが見る）。足りなければ手札から出す前に
      ``INSUFFICIENT_CARDS_IN_HAND``。どの種類のカードでもよい。もどしたカードは山札に入るので、そのあと選べるカードに含める（山札に選べるカードがなかったことを、
      使えない理由にしない）
    - コイン（``coin``。モンスターボール）: 使うための条件のあと・山札を見る前に投げる。「うら」なら何もしない（山札を見ず、切らない。「その後」は「おもて」のときの山札を
      さがす処理のあと。v0.44 のおつかい・v0.45 のたすけをよぶと同じ読み方。投げ直さない）
    - 選ぶ（決定 ``SEARCH_DECK``。選べるものは山札の ``target`` のカード（uid の小さい順））: ``optional``（「てよい」「ことができる」）なら 0〜min(``count``, 数) 枚
      （選べるカードがなければ決定を出さない）、そうでなければちょうど ``count`` 枚（今の登録では 1 枚。選べるカードがなければ ST1 で使う前に止める）
    - 手札に加える: ``reveal``（「相手プレイヤーに見せてから」「選んだカードは相手に見せる」）なら ``zones.reveal_deck_to_hand``（ログ ``reveal_from_deck`` は公開）、
      見せる指示がなければ ``zones.search_deck_to_hand``（ログ ``search_deck`` の ``card`` は使ったプレイヤーだけが見る。エネルギー転送）。選んだカードを uid の小さい順に
      加え、そのあと山札を 1 回切る（``zones.shuffle_deck``）。選ばなかった・選べなかったらログ ``trainer_take_none`` のあと切る
    - 不正な答えは決定の確認が拒否し、決定は待ったまま（すんだ使うための条件は取り消さない）
    """

    text: str
    target: CardFilter
    count: int
    optional: bool
    reveal: bool
    coin: bool = False
    discard_cost: int = 0
    return_cost: int = 0
    # v0.55（礼儀作法）: 使うための条件「あなたの手札に「たねポケモン」が1枚もない時だけ、使える」（``no_basic_in_hand``）と、山札をさがす前に「相手プレイヤーにあなたの手札を
    # 見せる」（``reveal_hand``。``zones.reveal_hand``。ログ ``reveal_hand`` は公開）
    no_basic_in_hand: bool = False
    reveal_hand: bool = False
    implementation_id = "search_deck_trainer"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = super().check(definition)
        text = definition.trainer_text_ja
        if text != self.text:
            problems.append(f"文面 {text!r} が、登録の文面ではない")
            return problems
        expected = {
            "見せる": ("見せ" in text, self.reveal),
            "選ばなくてよい": ("てよい" in text or "ことができる" in text, self.optional),
            "コイン": (text.startswith("コインを投げて「おもて」なら"), self.coin),
            "切る": ("切る" in text or "きる" in text, True),
            "枚数": ((f"最大{self.count}枚" in text) if self.count > 1 else ("1枚" in text and "最大" not in text), True),
            "トラッシュの条件": (f"手札からカードを{self.discard_cost}枚選んでトラッシュしなければ、このカードは使えない" in text, self.discard_cost > 0),
            "山札にもどす条件": (f"手札からカードを{self.return_cost}枚選んで、山札にもどす。それができない時、このカードは使えない" in text, self.return_cost > 0),
            "手札にたねポケモンがない条件": ("あなたの手札に「たねポケモン」が1枚もない時だけ、使える" in text, self.no_basic_in_hand),
            "手札を見せる": ("相手プレイヤーにあなたの手札を見せる" in text, self.reveal_hand),
        }
        problems += [f"文面と登録の「{name}」が合わない" for name, (found, registered) in expected.items() if found != registered]
        if self.discard_cost and self.return_cost:
            problems.append("使うための条件（トラッシュ・山札にもどす）は一方だけ")
        if not self.optional and (self.count != 1 or self.return_cost):
            problems.append("選ばなくてよいと書かれていない登録は、1 枚を選び、手札を山札にもどす条件のないものだけ（ST1 の確かめ方）")
        return problems

    def candidates(self, state: GameState, use: TrainerUse) -> tuple[int, ...]:
        return deck_cards_matching(state, use.player, self.target)

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if self.no_basic_in_hand and any(state.card_def(uid).is_basic_pokemon for uid in state.players[use.player].hand):
            # v0.55: 手札にある間の印刷の定義のたねポケモン（なにかの化石・ピッピ人形はトレーナーカードなので数えない）。手札から出す前に拒否する
            raise IllegalActionError("BASIC_POKEMON_IN_HAND", "手札に「たねポケモン」があるので、このカードは使えない（「あなたの手札に「たねポケモン」が1枚もない時だけ、使える」）")
        if self.discard_cost:
            _hand_cost_problem(state, use, self.discard_cost, "トラッシュする")
        if self.return_cost:
            _hand_cost_problem(state, use, self.return_cost, "山札にもどす")
        if not self.optional and not self.candidates(state, use):
            raise UnsupportedError(SEARCH_TRAINER_WITHOUT_TARGET_CODE, f"{SEARCH_TRAINER_WITHOUT_TARGET_REASON}。山札に選べるカードがない")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        hand = state.players[use.player].hand
        if self.discard_cost:
            push_trainer_decision(state, use, kind=DISCARD_FROM_HAND, player=use.player, options=hand,
                                  min_choices=self.discard_cost, max_choices=self.discard_cost)
        elif self.return_cost:
            push_trainer_decision(state, use, kind=HAND_TO_DECK, player=use.player, options=hand,
                                  min_choices=self.return_cost, max_choices=self.return_cost)
        else:
            if self.reveal_hand:
                reveal_hand(state, use.player, trainer=use.card)
            self._search(state, use)

    def _search(self, state: GameState, use: TrainerUse) -> None:
        if self.coin and not _trainer_coin(state, use):
            return
        options = self.candidates(state, use)
        if not options:
            if not self.optional:
                raise RuntimeError(f"{use.card_id} で山札に選べるカードがない（使う前の確認の漏れ。エンジンの不具合）")
            _trainer_take_none(state, use, "deck", no_target=True)
            shuffle_deck(state, use.player)
            return
        low = 0 if self.optional else self.count
        push_trainer_decision(state, use, kind=SEARCH_DECK, player=use.player, options=options, min_choices=low,
                              max_choices=min(self.count, len(options)))

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if decision.kind == DISCARD_FROM_HAND:
            discard_from_hand(state, use.player, choices)
            self._search(state, use)
            return
        if decision.kind == HAND_TO_DECK:
            return_hand_cards_to_deck(state, use.player, choices, trainer=use.card)
            self._search(state, use)
            return
        if not choices:
            _trainer_take_none(state, use, "deck", no_target=False)
        for card in sorted(choices):
            if card not in self.candidates(state, use):
                raise RuntimeError(f"{use.card_id} で選んだカード {card} が、山札の選べるカードではない（決定の確認の漏れ。エンジンの不具合）")
            if self.reveal:
                reveal_deck_to_hand(state, use.player, card)
            else:
                search_deck_to_hand(state, use.player, card)
        shuffle_deck(state, use.player)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = f"トレーナー {use.card_id}"
        p = state.players[use.player]
        problems = [] if decision.player == use.player else [f"{what}の決定をするのがプレイヤー {decision.player}（使ったプレイヤー {use.player} のはず）"]
        events = _last_trainer_events(state, use)
        if decision.kind == DISCARD_FROM_HAND and self.discard_cost:
            expected, bounds = tuple(p.hand), (self.discard_cost, self.discard_cost)
        elif decision.kind == HAND_TO_DECK and self.return_cost:
            expected, bounds = tuple(p.hand), (self.return_cost, self.return_cost)
        elif decision.kind == SEARCH_DECK:
            expected = self.candidates(state, use)
            bounds = (0 if self.optional else self.count, min(self.count, len(expected)))
            if self.discard_cost and not any(e["kind"] == "discard_from_hand" for e in events):
                problems.append(f"{what}の山札を選ぶ決定が、使うための条件（手札のトラッシュ）のあとではない")
            if self.return_cost and not any(e["kind"] == "hand_to_deck" and e.get("trainer_card") == use.card for e in events):
                problems.append(f"{what}の山札を選ぶ決定が、使うための条件（手札を山札にもどす）のあとではない")
            if self.coin and not any(e["kind"] == "coin_flip" and e["source"] == "trainer" and e["card"] == use.card and e["result"] == "heads" for e in events):
                problems.append(f"{what}の山札を選ぶ決定が、「おもて」のコインのあとではない")
            if not expected:
                problems.append(f"{what}の山札を選ぶ決定に、選べるカードがない")
        else:
            return problems + [f"{what}の決定の種類が {decision.kind!r}"]
        if (decision.min_choices, decision.max_choices) != bounds:
            problems.append(f"{what}の決定 {decision.kind} で選ぶ数が {decision.min_choices}〜{decision.max_choices}（{bounds} のはず）")
        if decision.options != expected:
            problems.append(f"{what}の決定 {decision.kind} の選べるもの {decision.options} が {expected} と合わない")
        return problems


@dataclass(frozen=True)
class ReturnHandToDeckThenDraw(TrainerEffect):
    """v0.53: 手札から ``count`` 枚のカードを選び山札にもどし、山札を切ってから 1 枚引いて手札にする（メンテナンス。kyuura の印刷の文面「手札から2枚のカードを選び山札に
    戻す。その後で山札をよくきってから1枚ひいて手札にする。」。docs/search-retrieval-trainers-v0.53.md 3 章）。

    - もどすのは使ったプレイヤーが選ぶ、このカードを除く手札のちょうど ``count`` 枚（決定 ``HAND_TO_DECK``。どの種類でもよい）。見せる指示がないので
      ``zones.return_hand_cards_to_deck``（ログ ``hand_to_deck`` の ``cards`` は使ったプレイヤーだけが見る）
    - 順番は説明のとおり: もどす → 切る（``zones.shuffle_deck``）→ 1 枚引く（``zones.draw_cards``。「カードを引く」。p.312。切る前に引かない）。もどしたあとの山札は
      ``count`` 枚以上あるので、引けないことはない
    - このカードを除く手札が ``count`` 枚より少ないときは、FC1（説明が決まった枚数のカードを選ばせるとき、選べるカードが足りない場合。v0.44 のラッキーたまごと同じ言い回し
      「手札からカードを2枚選び、山札にもどして」の、同じ問い。``UNRESOLVED_STATED_CARDS_SHORT``）で、手札から出す前に止める。印刷の文面に「それができない時、このカードは
      使えない」はないので、使うための条件（``INSUFFICIENT_CARDS_IN_HAND``）にしない
    """

    text: str
    count: int = 2
    draw: int = 1
    implementation_id = "return_hand_to_deck_then_draw"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = super().check(definition)
        if definition.trainer_text_ja != self.text:
            problems.append(f"文面 {definition.trainer_text_ja!r} が、登録の文面ではない")
        elif f"手札から{self.count}枚のカードを選び山札に戻す" not in self.text or f"よくきってから{self.draw}枚ひいて" not in self.text:
            problems.append("文面と登録の枚数（もどす・引く）が合わない")
        return problems

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        others = [uid for uid in state.players[use.player].hand if uid != use.card]
        if len(others) < self.count:
            raise UnsupportedError(STATED_CARDS_SHORT_CODE, f"{STATED_CARDS_SHORT_REASON}。メンテナンスで、このカードを除く手札が {len(others)} 枚")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        push_trainer_decision(state, use, kind=HAND_TO_DECK, player=use.player, options=state.players[use.player].hand,
                              min_choices=self.count, max_choices=self.count)

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        return_hand_cards_to_deck(state, use.player, choices, trainer=use.card)
        shuffle_deck(state, use.player)
        draw_cards(state, use.player, min(self.draw, len(state.players[use.player].deck)))

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = f"トレーナー {use.card_id}"
        problems = [] if decision.player == use.player else [f"{what}の決定をするのがプレイヤー {decision.player}（使ったプレイヤー {use.player} のはず）"]
        if decision.kind != HAND_TO_DECK:
            return problems + [f"{what}の決定の種類が {decision.kind!r}（{HAND_TO_DECK} のはず）"]
        if (decision.min_choices, decision.max_choices) != (self.count, self.count):
            problems.append(f"{what}で選ぶ数が {decision.min_choices}〜{decision.max_choices}（{self.count} 枚のはず）")
        if decision.options != tuple(state.players[use.player].hand):
            problems.append(f"{what}の決定の選べるもの {decision.options} が手札と合わない")
        return problems


# トラッシュから選んだカードの行き先（v0.53）
TO_HAND = "hand"  # 手札に加える（ダウジングマシーン）
TO_DECK_TOP = "deck_top"  # 山札の一番上に置く。切らない（リサイクル）
TO_DECK = "deck"  # 見せてから山札にもどし、切る（夜の廃品回収）
_DISCARD_DESTINATIONS = (TO_HAND, TO_DECK_TOP, TO_DECK)


@dataclass(frozen=True)
class TakeFromDiscardTrainer(TrainerEffect):
    """v0.53: 自分のトラッシュから ``target`` のカードを最大 ``count`` 枚選び、手札・山札の一番上・山札（切る）に動かすトレーナーの共通の処理（ダウジングマシーン・
    リサイクル・夜の廃品回収。どれも kyuura の印刷の文面。docs/search-retrieval-trainers-v0.53.md 3 章）。

    - 使うための条件（``discard_cost``。ダウジングマシーンの「手札からカードを2枚すてることによって」）: このカードを除く手札から ``discard_cost`` 枚を選んでトラッシュする
      （決定 ``DISCARD_FROM_HAND``・``zones.discard_from_hand``。公開）。足りなければ手札から出す前に ``INSUFFICIENT_CARDS_IN_HAND``（「…ことによって」は、すてることで
      手札に加えられるという条件の言い回し。トラッシュせずに使うことはない。実装上の読み方）
    - 選べるもの（自分のトラッシュの ``target`` のカード。トラッシュの並び）は、使うための条件でトラッシュしたあとに求める。トラッシュしたカードも、説明に除く記述がない
      （エネルギー回収の「ただし、このカードを使うためにトラッシュしたカードを選ぶことはできない。」がない）ので選べる。使っている最中のこのカードはまだトラッシュにない
      （使い終わってからトラッシュする）ので選べない（トラッシュにある別の同じ名前のカードは選べる）。相手のトラッシュ・場のトレーナーは選べない
    - コイン（``coin``。リサイクル）: 確認のあと・選ぶ前に投げる。「うら」なら何もしない
    - 選ぶ（使ったプレイヤー）: ``optional``（「ことができる」）なら 0〜min(``count``, 数) 枚、そうでなければ 1〜min(``count``, 数) 枚。0 枚の扱いが決まらない
      カード（夜の廃品回収の「最大3枚選び」。NG1）は 0〜 で決定を出し、0 枚の答えで止める（決定は待ったまま）。選べるカードがないとき: ``optional`` なら選ばずに終わる
      （ログ ``trainer_take_none``）、そうでなければ使う前に止める（リサイクルは ST1、夜の廃品回収は NG1）
    - 行き先: ``TO_HAND``（``zones.return_discard_to_hand`` とログ ``retrieve_trainer``。公開）・``TO_DECK_TOP``（``zones.put_discard_on_deck_top``。切らない。のせたカードは
      公開、山札のほかのカードは見えないまま）・``TO_DECK``（``zones.return_discard_to_deck``。見せる。そのあと山札を切る）。手札に加える処理・カードを引く処理にしない
    """

    text: str
    target: CardFilter
    count: int
    destination: str
    optional: bool = False
    zero_undetermined: bool = False
    coin: bool = False
    discard_cost: int = 0
    implementation_id = "take_from_discard_trainer"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = [] if self.secret_machine_ok(definition) else super().check(definition)
        text = definition.trainer_text_ja
        if text != self.text:
            problems.append(f"文面 {text!r} が、登録の文面ではない")
            return problems
        expected = {
            "選ばなくてよい": ("ことができる" in text or "てよい" in text, self.optional),
            "最大": ("最大" in text, self.count > 1),
            "コイン": (text.startswith("コインを投げて「おもて」なら"), self.coin),
            "すてる条件": (f"手札からカードを{self.discard_cost}枚すてることによって" in text, self.discard_cost > 0),
            "山札の一番上": ("山札の1番上に置く" in text, self.destination == TO_DECK_TOP),
            "手札に加える": ("手札に加える" in text, self.destination == TO_HAND),
            "山札にもどして切る": ("山札にもどす。その後、その山札をよく切る" in text, self.destination == TO_DECK),
        }
        problems += [f"文面と登録の「{name}」が合わない" for name, (found, registered) in expected.items() if found != registered]
        if self.destination not in _DISCARD_DESTINATIONS:
            problems.append(f"行き先 {self.destination!r} が {_DISCARD_DESTINATIONS} のどれでもない")
        if self.zero_undetermined and (self.optional or self.count < 2):
            problems.append("0 枚の扱いが決まらない（NG1）のは、「最大」の枚数で選ばなくてよいと書かれていない登録だけ")
        return problems

    @staticmethod
    def secret_machine_ok(definition: CardDefinition) -> bool:
        """夜の廃品回収の種類 ``rockets_secret_machine``（kyuura の区分「ロケット団秘密メカ」）。v0.55 から、ねむれ!ねむれ!と共通の関数 ``secret_machine_ok`` に委ねる。"""
        return secret_machine_ok(definition)

    def candidates(self, state: GameState, use: TrainerUse) -> tuple[int, ...]:
        return discard_cards_matching(state, use.player, self.target)

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if self.discard_cost:
            _hand_cost_problem(state, use, self.discard_cost, "すてる")
            return  # 選べるものは、すてたあとに求める（すてたカードも選べる）。選ばなくてよい（「ことができる」）ので、選べるカードがなくても止めない
        if not self.optional and not self.candidates(state, use):
            if self.zero_undetermined:
                raise UnsupportedError(NIGHTLY_GARBAGE_RUN_ZERO_CODE, f"{NIGHTLY_GARBAGE_RUN_ZERO_REASON}。トラッシュに選べるカードがない")
            raise UnsupportedError(SEARCH_TRAINER_WITHOUT_TARGET_CODE, f"{SEARCH_TRAINER_WITHOUT_TARGET_REASON}。トラッシュにカードがない")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        if self.discard_cost:
            push_trainer_decision(state, use, kind=DISCARD_FROM_HAND, player=use.player, options=state.players[use.player].hand,
                                  min_choices=self.discard_cost, max_choices=self.discard_cost)
            return
        self._choose(state, use)

    def decision_kind(self) -> str:
        return {TO_HAND: RECOVER_TRAINER, TO_DECK_TOP: DISCARD_TO_DECK_TOP, TO_DECK: DISCARD_TO_DECK}[self.destination]

    def bounds(self, options: tuple[int, ...]) -> tuple[int, int]:
        low = 0 if (self.optional or self.zero_undetermined) else 1
        return low, min(self.count, len(options))

    def _choose(self, state: GameState, use: TrainerUse) -> None:
        if self.coin and not _trainer_coin(state, use):
            return
        options = self.candidates(state, use)
        if not options:
            if not self.optional:
                raise RuntimeError(f"{use.card_id} でトラッシュに選べるカードがない（使う前の確認の漏れ。エンジンの不具合）")
            _trainer_take_none(state, use, "discard", no_target=True)
            return
        low, high = self.bounds(options)
        push_trainer_decision(state, use, kind=self.decision_kind(), player=use.player, options=options, min_choices=low, max_choices=high)

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if decision.kind == DISCARD_FROM_HAND:
            discard_from_hand(state, use.player, choices)
            self._choose(state, use)
            return
        if not choices:
            if self.zero_undetermined:
                raise UnsupportedError(NIGHTLY_GARBAGE_RUN_ZERO_CODE, f"{NIGHTLY_GARBAGE_RUN_ZERO_REASON}（1 枚以上を選び直せる）")
            _trainer_take_none(state, use, "discard", no_target=False)
            return
        options = self.candidates(state, use)
        if any(card not in options for card in choices):
            raise RuntimeError(f"{use.card_id} で選んだカード {choices} が、トラッシュの選べるカードではない（決定の確認の漏れ。エンジンの不具合）")
        cards = tuple(uid for uid in state.players[use.player].discard if uid in choices)
        if self.destination == TO_HAND:
            return_discard_to_hand(state, use.player, cards)
            for card in cards:
                state.add_event("retrieve_trainer", player=use.player, card=card, trainer_card=use.card)
        elif self.destination == TO_DECK_TOP:
            (card,) = cards
            put_discard_on_deck_top(state, use.player, card, trainer=use.card, chooser=use.player)
        else:
            return_discard_to_deck(state, use.player, cards, trainer=use.card)
            shuffle_deck(state, use.player)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = f"トレーナー {use.card_id}"
        problems = [] if decision.player == use.player else [f"{what}の決定をするのがプレイヤー {decision.player}（使ったプレイヤー {use.player} のはず）"]
        events = _last_trainer_events(state, use)
        if decision.kind == DISCARD_FROM_HAND and self.discard_cost:
            expected, bounds = tuple(state.players[use.player].hand), (self.discard_cost, self.discard_cost)
        elif decision.kind == self.decision_kind():
            expected = self.candidates(state, use)
            bounds = self.bounds(expected)
            if self.discard_cost and not any(e["kind"] == "discard_from_hand" for e in events):
                problems.append(f"{what}のトラッシュを選ぶ決定が、使うための条件（手札をすてる）のあとではない")
            if self.coin and not any(e["kind"] == "coin_flip" and e["source"] == "trainer" and e["card"] == use.card and e["result"] == "heads" for e in events):
                problems.append(f"{what}のトラッシュを選ぶ決定が、「おもて」のコインのあとではない")
            if not expected:
                problems.append(f"{what}のトラッシュを選ぶ決定に、選べるカードがない")
        else:
            return problems + [f"{what}の決定の種類が {decision.kind!r}"]
        if (decision.min_choices, decision.max_choices) != bounds:
            problems.append(f"{what}の決定 {decision.kind} で選ぶ数が {decision.min_choices}〜{decision.max_choices}（{bounds} のはず）")
        if decision.options != expected:
            problems.append(f"{what}の決定 {decision.kind} の選べるもの {decision.options} が {expected} と合わない")
        if use.card in decision.options:
            problems.append(f"{what}の決定で、使っているこのカードを選べる")
        return problems


# ---------------------------------------------------------------- 手札の入れ替え・ドロー・情報の確認のトレーナー（v0.54）
# どれも kyuura の印刷の文面（kyuura data/cards.json。kyuura に最新の説明・エラッタ・裁定の記録はない）。docs/hand-deck-trainers-v0.54.md

IMPOSTER_OAK_TEXT = "相手の手札をすべて相手の山札にもどさせ、よくきってから、新たに7枚を引いて手札にさせる。"
IMPOSTER_OAKS_REVENGE_TEXT = ("手札からカードを1枚選んでトラッシュしなければ、このカードは使えない。\n\n\n\n"
                              "相手の手札をすべて山札にもどさせ、山札をよく切ってから、新たに4枚を引かせて手札にさせる。")
GAMBLER_TEXT = ("自分の手札を自分の山札に全てもどし、その山札をよくきる。その後、コインを投げて「おもて」なら8枚、「うら」なら1枚のカードを自分の山札からひいて"
                "手札にする。")
SABRINAS_GAZE_TEXT = ("お互いのプレイヤーは、それぞれ、自分の手札の数を数え、それらすべてを自分の山札にもどす。その後、お互いに山札をよく切り、それぞれ、自分がもどした"
                      "枚数のカードを引いて、手札にする。")
BLAINES_LAST_RESORT_TEXT = "このカードは、あなたの手札に「カツラの奥の手」以外のカードがある時には、使えない。山札からカードを5枚引いて、手札に加える。"
ERIKA_TEXT = "あなたと相手プレイヤーは、それぞれ、のぞむなら最大3枚まで、山札からカードを引いてよい。(あなたがカードを引き終わってから、相手プレイヤーが引く)"
SECRET_MISSION_TEXT = ("相手プレイヤーの手札を見る。その後、のぞむなら、あなたの手札からカードを好きなだけトラッシュして、トラッシュしたのと同じ数のカードを、山札から"
                       "引いてよい。")
BLAINES_GAMBLE_TEXT = ("あなたの手札から、好きなだけカードを選んでトラッシュする。その後、コインを投げて「おもて」なら、トラッシュした数×2枚のカードを、山札から引いて"
                       "手札に加える。")
LASS_TEXT = "お互いのプレイヤーは手札を見せ合い、手札にあるトレーナーカードを全て山札に戻す。そのあとで山札をよくきって、プレイを再開する。"
POKEDEX_TEXT = "自分の山札を上から5枚まで見て、好きな順番に入れ替えて山札に戻すことができる。"

# 手札を山札にもどすプレイヤー（v0.54）。両方なら、使ったプレイヤー → 相手プレイヤーの順に処理する（実装上の順番。docs 3 章）
HANDS_OPPONENT = "opponent"
HANDS_SELF = "self"
HANDS_BOTH = "both"
# HC5（v0.31）: 「好きなだけ」（「のぞむなら」のない）で 0 枚を選べるか。カツラのギャンブルの「好きなだけカードを選んでトラッシュする」は同じ言い回し
DISCARD_ANY_NUMBER_ZERO_CODE = "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO"
DISCARD_ANY_NUMBER_ZERO_REASON = (
    "「好きなだけカードを選んでトラッシュする」（「のぞむなら」のない「好きなだけ」）で 0 枚を選べるかは決められないので扱わない（v0.31 の HC5 と同じ言い回しの問い。"
    "カツラのギャンブル）。1 枚以上を選ぶ"
)


def _players_in_order(use: TrainerUse, who: str) -> tuple[int, ...]:
    return {HANDS_SELF: (use.player,), HANDS_OPPONENT: (1 - use.player,), HANDS_BOTH: (use.player, 1 - use.player)}[who]


def _draw_up_to(state: GameState, player: int, count: int) -> tuple[int, ...]:
    """効果で ``count`` 枚引く（山札が足りなければ引けるだけ。0 枚でも負けではない。p.312。マサキ・オーキドはかせと同じ規定）。"""
    return draw_cards(state, player, min(count, len(state.players[player].deck)))


@dataclass(frozen=True)
class ReturnHandsToDeckTrainer(TrainerEffect):
    """v0.54: プレイヤーの手札（すべて・トレーナーカードだけ）を山札にもどし、山札を切り、決まった枚数を引くトレーナーの共通の処理（にせオーキドはかせ・にせオーキドの逆襲・
    ギャンブラー・ナツメの眼・ミニスカート。docs/hand-deck-trainers-v0.54.md 3 章）。

    - ``who``: もどすプレイヤー（``HANDS_OPPONENT``・``HANDS_SELF``・``HANDS_BOTH``）。相手の手札をもどさせる・相手に引かせるのは相手の手札・山札への効果で、相手の決定は
      ない（選ぶものがない）。両方なら、見せる・もどす・切る・引くのそれぞれを、使ったプレイヤー → 相手プレイヤーの順に行う（実装上の順番。手札・山札は別々なので結果の
      分布は変わらない）
    - ``returns``: ``"all"``（手札をすべて）・``"trainers"``（手札のトレーナーカード。手札にある間の印刷の定義で決める ``CardFilter("trainer")``。なにかの化石・ピッピ人形・
      ほかの種類のトレーナーも含む。ポケモン・エネルギーは動かさない）。使っているこのカードは手札にない（``trainer_in_use``）ので含まない
    - ``reveal``: もどす前に手札を見せ合う（``zones.reveal_hand``。ログ ``reveal_hand`` は公開）。見せたカードからもどすので ``revealed_hand_to_deck``（公開）。見せない
      ときは ``zones.return_hand_cards_to_deck``（ログ ``hand_to_deck`` の ``cards`` は持ち主だけ）。もどすカードがなければもどすログはない
    - 切る: もどすプレイヤーの山札を必ず切る（もどすカードが 0 枚でも。説明の「よくきって」の主語はもどすプレイヤー）
    - 引く枚数: ``draw``（決まった数）・``draw_returned``（そのプレイヤーがもどした枚数。ナツメの眼。プレイヤーごとに別に数える）・``coin_draws``（切ったあとに使った
      プレイヤーがコインを 1 枚投げ、(「おもて」, 「うら」) の枚数。ギャンブラー）。山札が足りなければ引けるだけ（p.312）。``returns`` が ``"trainers"`` なら引かない
    - ``discard_cost``: 使うための条件として、このカードを除く手札から決まった枚数をトラッシュする（にせオーキドの逆襲。``INSUFFICIENT_CARDS_IN_HAND``。決定
      ``DISCARD_FROM_HAND``）。トラッシュのあとで不正な答えがあっても、すんだトラッシュは取り消さない
    """

    text: str
    who: str
    returns: str = "all"
    reveal: bool = False
    draw: int | None = None
    draw_returned: bool = False
    coin_draws: tuple[int, int] | None = None
    discard_cost: int = 0
    implementation_id = "return_hands_to_deck_trainer"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = super().check(definition)
        text = definition.trainer_text_ja
        if text != self.text:
            problems.append(f"文面 {text!r} が、登録の文面ではない")
            return problems
        draws = [self.draw is not None, self.draw_returned, self.coin_draws is not None]
        coin = self.coin_draws or (0, 0)
        expected = {
            "相手の手札": ("相手の手札をすべて" in text, self.who == HANDS_OPPONENT),
            "自分の手札": ("自分の手札を自分の山札に全てもどし" in text, self.who == HANDS_SELF),
            "お互いのプレイヤー": (text.startswith("お互いのプレイヤーは"), self.who == HANDS_BOTH),
            "トレーナーカードだけ": ("トレーナーカードを全て山札に戻す" in text, self.returns == "trainers"),
            "見せ合う": ("見せ合い" in text, self.reveal),
            "決まった枚数を引く": (self.draw is not None and f"{self.draw}枚を引" in text, self.draw is not None),
            "もどした枚数を引く": ("自分がもどした枚数のカードを引いて" in text, self.draw_returned),
            "コイン": (f"コインを投げて「おもて」なら{coin[0]}枚、「うら」なら{coin[1]}枚" in text, self.coin_draws is not None),
            "トラッシュの条件": ("選んでトラッシュしなければ、このカードは使えない" in text, self.discard_cost > 0),
        }
        problems += [f"文面と登録の「{name}」が合わない" for name, (found, registered) in expected.items() if found != registered]
        if self.discard_cost and f"手札からカードを{self.discard_cost}枚選んでトラッシュしなければ" not in text:
            problems.append(f"文面と登録の使うための条件の枚数（{self.discard_cost}）が合わない")
        if sum(draws) != (0 if self.returns == "trainers" else 1):
            problems.append("引く枚数の決め方（決まった数・もどした枚数・コイン）は、手札をすべてもどすときちょうど 1 つ（トレーナーカードだけもどすときは引かない）")
        if self.returns not in ("all", "trainers") or self.who not in (HANDS_OPPONENT, HANDS_SELF, HANDS_BOTH):
            problems.append(f"もどすカード {self.returns!r}・プレイヤー {self.who!r} が登録できる値ではない")
        return problems

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if self.discard_cost:
            _hand_cost_problem(state, use, self.discard_cost, "トラッシュする")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        if self.discard_cost:
            push_trainer_decision(state, use, kind=DISCARD_FROM_HAND, player=use.player, options=state.players[use.player].hand,
                                  min_choices=self.discard_cost, max_choices=self.discard_cost)
            return
        self._apply(state, use)

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        discard_from_hand(state, use.player, choices)
        self._apply(state, use)

    def _apply(self, state: GameState, use: TrainerUse) -> None:
        players = _players_in_order(use, self.who)
        if self.reveal:
            for player in players:
                reveal_hand(state, player, trainer=use.card)
        returned: dict[int, int] = {}
        for player in players:
            hand = state.players[player].hand
            cards = tuple(uid for uid in hand if self.returns == "all" or CardFilter("trainer").matches(state.card_def(uid)))
            returned[player] = len(cards)
            if not cards:
                continue
            if self.reveal:
                return_revealed_hand_cards_to_deck(state, player, cards, trainer=use.card)
            else:
                return_hand_cards_to_deck(state, player, cards, trainer=use.card)
        for player in players:
            shuffle_deck(state, player)
        if self.returns == "trainers":
            return
        if self.coin_draws is not None:
            count = self.coin_draws[0] if _trainer_coin(state, use) else self.coin_draws[1]
        for player in players:
            if self.draw is not None:
                count = self.draw
            elif self.draw_returned:
                count = returned[player]
            _draw_up_to(state, player, count)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = f"トレーナー {use.card_id}"
        problems = [] if decision.player == use.player else [f"{what}の決定をするのがプレイヤー {decision.player}（使ったプレイヤー {use.player} のはず）"]
        if decision.kind != DISCARD_FROM_HAND or not self.discard_cost:
            return problems + [f"{what}の決定の種類が {decision.kind!r}"]
        if (decision.min_choices, decision.max_choices) != (self.discard_cost, self.discard_cost):
            problems.append(f"{what}で選ぶ数が {decision.min_choices}〜{decision.max_choices}（{self.discard_cost} 枚のはず）")
        if decision.options != tuple(state.players[use.player].hand):
            problems.append(f"{what}の決定の選べるもの {decision.options} が手札と合わない")
        return problems


@dataclass(frozen=True)
class DrawIfOnlyNamedInHand(TrainerEffect):
    """v0.54: 手札に ``name`` 以外のカードがある時には使えず、山札からカードを ``count`` 枚引いて手札に加える（カツラの奥の手）。

    - 使うための条件: 使っているこのカードを除く手札に、名前（手札にある間の印刷の定義の名前の完全一致）が ``name`` でないカードがあれば、手札から出す前に
      ``IllegalActionError("OTHER_CARDS_IN_HAND")``。同じ名前のカード（ほかの「カツラの奥の手」）はあってよく、手札がこのカードだけでも使える
    - 手札を見せる指示は日本語版の文面にない（英語版の「Show your hand to your opponent」を持ち込まない）。条件はエンジンが確かめるだけで、ログに手札を書かない
    - 引くのは山札から ``count`` 枚（足りなければ引けるだけ。p.312）
    """

    text: str
    name: str
    count: int
    implementation_id = "draw_if_only_named_in_hand"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = super().check(definition)
        if definition.trainer_text_ja != self.text:
            problems.append(f"文面 {definition.trainer_text_ja!r} が、登録の文面ではない")
        elif f"手札に「{self.name}」以外のカードがある時には、使えない" not in self.text or f"カードを{self.count}枚引いて" not in self.text:
            problems.append("文面と登録の名前・枚数が合わない")
        if definition.name_ja != self.name:
            problems.append(f"カードの名前 {definition.name_ja!r} が、条件の名前 {self.name!r} ではない")
        return problems

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        others = [uid for uid in state.players[use.player].hand if uid != use.card and state.card_def(uid).name_ja != self.name]
        if others:
            raise IllegalActionError(
                "OTHER_CARDS_IN_HAND",
                f"手札に「{self.name}」以外のカードが {len(others)} 枚あるので、このカードは使えない（使うための条件）",
            )

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        _draw_up_to(state, use.player, self.count)


@dataclass(frozen=True)
class EachPlayerMayDraw(TrainerEffect):
    """v0.54: 使ったプレイヤーと相手プレイヤーが、それぞれ、のぞむなら最大 ``max_count`` 枚まで山札から引く（エリカ。使ったプレイヤーが引き終わってから相手が引く）。

    - 引く枚数を決めるのは引くプレイヤー自身（決定 ``SELECT_DRAW_COUNT``。選べるものは 0〜min(``max_count``, 自分の山札の枚数)。``context`` の ``"stage"`` は 0（使った
      プレイヤー）・1（相手プレイヤー））。相手プレイヤーの決定は、このカードの ``decision_problems`` だけが許す（ほかのトレーナーの、使ったプレイヤーが決める約束は変えない）
    - 0 枚は「のぞむなら」の、引かないこと（ログ ``trainer_draw_declined`` の ``reason`` ``declined``）。山札が 0 枚なら決定を出さない（``reason`` ``empty_deck``）。両方が
      引かなくてもよい
    - 使ったプレイヤーが引いてから、相手プレイヤーの決定を出す（説明の「(あなたがカードを引き終わってから、相手プレイヤーが引く)」）。相手は使ったプレイヤーが引いた枚数を
      知ってから決める（ログ ``draw`` の枚数は公開、カードは引いたプレイヤーだけ）
    """

    text: str
    max_count: int
    implementation_id = "each_player_may_draw"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = super().check(definition)
        if definition.trainer_text_ja != self.text:
            problems.append(f"文面 {definition.trainer_text_ja!r} が、登録の文面ではない")
        elif f"のぞむなら最大{self.max_count}枚まで" not in self.text or "あなたがカードを引き終わってから、相手プレイヤーが引く" not in self.text:
            problems.append("文面と登録の枚数・順番が合わない")
        return problems

    def _drawer(self, use: TrainerUse, stage: int) -> int:
        return use.player if stage == 0 else 1 - use.player

    def _options(self, state: GameState, player: int) -> tuple[int, ...]:
        return tuple(range(min(self.max_count, len(state.players[player].deck)) + 1))

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        self._offer(state, use, 0)

    def _offer(self, state: GameState, use: TrainerUse, stage: int) -> None:
        for current in range(stage, 2):
            player = self._drawer(use, current)
            if state.players[player].deck:
                push_trainer_decision(state, use, kind=SELECT_DRAW_COUNT, player=player, options=self._options(state, player), context=(("stage", current),))
                return
            state.add_event("trainer_draw_declined", player=player, trainer_card=use.card, reason="empty_deck")

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        stage = decision.context_value("stage")
        player = self._drawer(use, stage)
        if choices[0]:
            draw_cards(state, player, choices[0])
        else:
            state.add_event("trainer_draw_declined", player=player, trainer_card=use.card, reason="declined")
        if stage == 0:
            self._offer(state, use, 1)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = f"トレーナー {use.card_id}"
        if decision.kind != SELECT_DRAW_COUNT:
            return [f"{what}の決定の種類が {decision.kind!r}（{SELECT_DRAW_COUNT} のはず）"]
        stage = decision.context_value("stage")
        if stage not in (0, 1):
            return [f"{what}の決定の段階 {stage!r} が 0・1 ではない"]
        problems = []
        player = self._drawer(use, stage)
        if decision.player != player:
            problems.append(f"{what}の段階 {stage} で引く枚数を決めるのがプレイヤー {decision.player}（{player} のはず）")
        if (decision.min_choices, decision.max_choices) != (1, 1):
            problems.append(f"{what}で選ぶ数が {decision.min_choices}〜{decision.max_choices}")
        if not state.players[player].deck or decision.options != self._options(state, player):
            problems.append(f"{what}の決定の選べるもの {decision.options} が、プレイヤー {player} の山札の枚数と合わない")
        if stage == 1 and not any(e["kind"] in ("draw", "trainer_draw_declined") and e["player"] == use.player for e in _last_trainer_events(state, use)):
            problems.append(f"{what}の相手プレイヤーの決定が、使ったプレイヤーが引き終わる前に出ている")
        return problems


@dataclass(frozen=True)
class DiscardFromHandThenDrawTrainer(TrainerEffect):
    """v0.54: 手札から好きなだけトラッシュし、トラッシュした数（× ``multiplier``）のカードを引くトレーナーの共通の処理（スパイ作戦・カツラのギャンブル）。

    - ``look_opponent_hand``（スパイ作戦）: 最初に相手プレイヤーの手札を見る（``zones.look_at_hand``。ログ ``look_at_hand`` の ``cards`` は見たプレイヤーと持ち主だけ。
      相手の手札が 0 枚でも見る処理をして、そのあとの処理を続ける（見るカードがないだけ。実装上の読み方））。見たのはこの時点の手札で、あとで観測の手札を公開しない
    - トラッシュするのは使ったプレイヤーが選ぶ、このカードを除く手札の 0〜すべて（決定 ``DISCARD_FROM_HAND``）。``optional``（「のぞむなら」。スパイ作戦）なら 0 枚は
      トラッシュも引くこともしない（ログ ``trainer_discard_declined``）。``optional`` でない（カツラのギャンブルの「好きなだけ」）なら 0 枚は HC5（答えのときに止める。
      手札がこのカードだけなら、選べるのは 0 枚しかないので使う前に止める）
    - ``coin``: トラッシュのあとに使ったプレイヤーがコインを 1 枚投げ、「おもて」ならトラッシュした数 × ``multiplier`` 枚引く。「うら」なら引かない（トラッシュしたカードは
      もどさない）。スパイ作戦はトラッシュした数と同じ数を引く（トラッシュと引くのは 1 つの「のぞむなら」。トラッシュして引かない選択はない。実装上の読み方）
    - 引く枚数は山札が足りなければ引けるだけ（p.312）
    """

    text: str
    multiplier: int = 1
    coin: bool = False
    optional: bool = False
    look_opponent_hand: bool = False
    implementation_id = "discard_from_hand_then_draw_trainer"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = super().check(definition)
        text = definition.trainer_text_ja
        if text != self.text:
            problems.append(f"文面 {text!r} が、登録の文面ではない")
            return problems
        expected = {
            "相手の手札を見る": (text.startswith("相手プレイヤーの手札を見る。"), self.look_opponent_hand),
            "のぞむなら": ("のぞむなら" in text, self.optional),
            "コイン": ("コインを投げて「おもて」なら" in text, self.coin),
            "引く枚数": ("トラッシュした数×2枚" in text if self.multiplier == 2 else "トラッシュしたのと同じ数のカード" in text, True),
            "好きなだけ": ("好きなだけ" in text, True),
        }
        problems += [f"文面と登録の「{name}」が合わない" for name, (found, registered) in expected.items() if found != registered]
        return problems

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if not self.optional and not [uid for uid in state.players[use.player].hand if uid != use.card]:
            raise UnsupportedError(DISCARD_ANY_NUMBER_ZERO_CODE, f"{DISCARD_ANY_NUMBER_ZERO_REASON}。このカードを除く手札が 0 枚で、選べるのは 0 枚だけ")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        if self.look_opponent_hand:
            look_at_hand(state, use.player, 1 - use.player, trainer=use.card)
        hand = state.players[use.player].hand
        if not hand:
            state.add_event("trainer_discard_declined", player=use.player, trainer_card=use.card, reason="empty_hand")
            return
        push_trainer_decision(state, use, kind=DISCARD_FROM_HAND, player=use.player, options=hand, min_choices=0, max_choices=len(hand))

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if not choices:
            if not self.optional:
                raise UnsupportedError(DISCARD_ANY_NUMBER_ZERO_CODE, DISCARD_ANY_NUMBER_ZERO_REASON)
            state.add_event("trainer_discard_declined", player=use.player, trainer_card=use.card, reason="declined")
            return
        discarded = discard_from_hand(state, use.player, choices)
        if self.coin and not _trainer_coin(state, use):
            return
        _draw_up_to(state, use.player, len(discarded) * self.multiplier)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = f"トレーナー {use.card_id}"
        problems = [] if decision.player == use.player else [f"{what}の決定をするのがプレイヤー {decision.player}（使ったプレイヤー {use.player} のはず）"]
        if decision.kind != DISCARD_FROM_HAND:
            return problems + [f"{what}の決定の種類が {decision.kind!r}（{DISCARD_FROM_HAND} のはず）"]
        hand = tuple(state.players[use.player].hand)
        if (decision.min_choices, decision.max_choices) != (0, len(hand)) or not hand:
            problems.append(f"{what}で選ぶ数が {decision.min_choices}〜{decision.max_choices}（0〜{len(hand)} 枚のはず）")
        if decision.options != hand:
            problems.append(f"{what}の決定の選べるもの {decision.options} が手札と合わない")
        if self.look_opponent_hand and not any(e["kind"] == "look_at_hand" and e.get("trainer_card") == use.card for e in _last_trainer_events(state, use)):
            problems.append(f"{what}の決定が、相手の手札を見るまえに出ている")
        return problems


@dataclass(frozen=True)
class ArrangeOwnDeckTopTrainer(TrainerEffect):
    """v0.54: 自分の山札を上から ``max_cards`` 枚まで見て、好きな順番に入れ替えて山札にもどすことができる（ポケモン図鑑 HANDY505）。

    - 見る山札は自分の山札だけ（みらいよちの持ち主を選ぶ決定はない）。見る枚数は使ったプレイヤーが選ぶ（決定 ``SELECT_LOOK_COUNT``。0〜min(``max_cards``, 山札の枚数)）。
      0 枚は「ことができる」の、見ないこと（ログ ``look_at_deck_top_declined``。v0.39 の GS1（「最大N」が 0 を含むか）とは別の言い回しで、GS1 を当てはめない）
    - 見る（ログ ``look_at_deck_top`` の ``cards`` は見たプレイヤーだけ）→ 2 枚以上なら新しい並び（決定 ``ARRANGE_DECK_TOP``。選べるものは見たカード（上から順）。答えの
      並びが新しい上からの順）→ もどす（ログ ``arrange_deck_top``）。1 枚なら並べかえる決定はない。見た部分より下の並びは変えない。手札に加えず、切らない
    - 山札が 0 枚なら見るカードがない（ログ ``look_at_deck_top_none``。決定なし）。見る枚数を選ぶ前は山札の内容を見せない
    - 出どころはトレーナー（ログの ``trainer_card``）。みらいよちのワザの ``effect`` とは別（ワザの要素 ``programs.ArrangeDeckTop`` は変えない）
    """

    text: str
    max_cards: int
    implementation_id = "arrange_own_deck_top_trainer"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = super().check(definition)
        if definition.trainer_text_ja != self.text:
            problems.append(f"文面 {definition.trainer_text_ja!r} が、登録の文面ではない")
        elif f"自分の山札を上から{self.max_cards}枚まで見て" not in self.text or "ことができる" not in self.text:
            problems.append("文面と登録の枚数・「ことができる」が合わない")
        return problems

    def _count_options(self, state: GameState, use: TrainerUse) -> tuple[int, ...]:
        return tuple(range(min(self.max_cards, len(state.players[use.player].deck)) + 1))

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        if not state.players[use.player].deck:
            state.add_event("look_at_deck_top_none", player=use.player, owner=use.player, trainer_card=use.card)
            return
        push_trainer_decision(state, use, kind=SELECT_LOOK_COUNT, player=use.player, options=self._count_options(state, use))

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        deck = state.players[use.player].deck
        if decision.kind == SELECT_LOOK_COUNT:
            count = choices[0]
            if count == 0:
                state.add_event("look_at_deck_top_declined", player=use.player, owner=use.player, trainer_card=use.card)
                return
            cards = tuple(deck[:count])
            state.add_event("look_at_deck_top", player=use.player, owner=use.player, count=count, cards=cards, trainer_card=use.card)
            if count == 1:
                state.add_event("arrange_deck_top", player=use.player, owner=use.player, count=1, cards=cards, trainer_card=use.card)
                return
            push_trainer_decision(state, use, kind=ARRANGE_DECK_TOP, player=use.player, options=cards, min_choices=count, max_choices=count)
            return
        count = len(decision.options)
        if tuple(deck[:count]) != tuple(decision.options) or sorted(choices) != sorted(decision.options):
            raise RuntimeError(f"ポケモン図鑑の並べかえ {choices} が、見たカード {decision.options} の並べかえではない（エンジンの不具合）")
        deck[:count] = list(choices)
        state.add_event("arrange_deck_top", player=use.player, owner=use.player, count=count, cards=tuple(choices), trainer_card=use.card)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = f"トレーナー {use.card_id}"
        problems = [] if decision.player == use.player else [f"{what}の決定をするのがプレイヤー {decision.player}（使ったプレイヤー {use.player} のはず）"]
        deck = state.players[use.player].deck
        if decision.kind == SELECT_LOOK_COUNT:
            if (decision.min_choices, decision.max_choices) != (1, 1) or not deck or decision.options != self._count_options(state, use):
                problems.append(f"{what}の見る枚数の決定 {decision.options}（{decision.min_choices}〜{decision.max_choices}）が山札と合わない")
            return problems
        if decision.kind != ARRANGE_DECK_TOP:
            return problems + [f"{what}の決定の種類が {decision.kind!r}"]
        count = len(decision.options)
        if not 2 <= count <= self.max_cards or (decision.min_choices, decision.max_choices) != (count, count) or tuple(deck[:count]) != decision.options:
            problems.append(f"{what}の並べかえの決定 {decision.options} が、山札の上の {count} 枚と合わない")
        looked = [e for e in _last_trainer_events(state, use) if e["kind"] == "look_at_deck_top" and e.get("trainer_card") == use.card]
        if len(looked) != 1 or tuple(looked[0]["cards"]) != decision.options:
            problems.append(f"{what}の並べかえの決定の前に、同じカードを見たログがない")
        return problems


# ---------------------------------------------------------------- v0.55: すぐに使い終わるトレーナー 16 枚（docs/instant-trainers-v0.55.md。どれも kyuura の印刷の文面）
# 山札の上を見る・相手の手札を見る・トラッシュを入れ替える・場のエネルギーカードをはがす（トラッシュ・手札・つけなおし）・ダメージカウンターをとりのぞく・特殊状態を
# 回復する・特殊状態にする・お互いの対戦ポケモンを入れ替える。意味（側・範囲・数・行き先・順番）ごとに共通の型にし、カード id では分けない

MISTYS_WRATH_TEXT = "あなたの山札の上から7枚のカードを見て、その中から2枚を選んで手札に加え、残りをトラッシュする。"
ROCKETS_SNEAK_ATTACK_TEXT = "相手の手札を見る。その中にトレーナーカードがあれば、1枚を選び、それを相手の山札にもどさせる。その後、その山札をよく切る。"
GOOD_MANNERS_TEXT = ("このカードは、あなたの手札に「たねポケモン」が1枚もない時だけ、使える。相手プレイヤーにあなたの手札を見せる。その後、あなたの山札から「たねポケモン」を"
                     "1枚選び出し、相手プレイヤーに見せてから、手札に加えてよい。その後、その山札をよく切る。")
TRASH_EXCHANGE_TEXT = "あなたのトラッシュにあるカードの枚数を数えてから、それらをすべて山札にもどし、よく切る。その後、数えた枚数のカードを山札の上から取って、トラッシュする。"
ENERGY_REMOVAL_TEXT = "相手の場のポケモンについているエネルギーカードを1枚はがしてすてる。"
SUPER_ENERGY_REMOVAL_TEXT = "自分の場のポケモンについているエネルギーカードを1枚はがしてすてることによって、相手の場のポケモン1匹から2枚のエネルギーカードをはがしてすてる。"
SUPER_POTION_TEXT = "自分のポケモン1匹のエネルギーカードを1枚はがしてすてることによって、そのポケモンのダメージカウンターを4個までとりのぞくことができる。"
FULL_HEAL_TEXT = "特殊状態にあるポケモンの全ての特殊状態を回復する。"
POKEMON_CENTER_TEXT = "ダメージカウンターがのっている自分のポケモン全員から、ダメージカウンターとエネルギーカード全てをはがしてすてる。"
SLEEP_TRAINER_TEXT = "コインを投げて「おもて」なら、相手の対戦ポケモンを「ねむり」状態にする。"
ENERGY_FLOW_TEXT = "あなたの場のポケモンについている「基本エネルギーカード」を好きなだけはがし、手札に戻してよい。"
ERIKAS_KINDNESS_TEXT = "お互いの場にいるポケモン全員から、それぞれ、ダメージカウンターを2つずつとりのぞく。"
BROCK_TRAINER_TEXT = "自分の場のすべてのポケモンから、それぞれ1つずつダメージカウンターをとりのぞく。"
GIOVANNIS_LAST_RESORT_TEXT = ("あなたの場にいる「サカキのポケモン」を1匹選び、そのポケモンにのっているダメージカウンターを、すべてとりのぞく。その後、あなたの手札をすべて"
                              "トラッシュする。")
SABRINA_TRAINER_TEXT = ("あなたの場にいる「ナツメのポケモン」を1匹選び、それについているエネルギーカードをすべてはがす。そして、はがしたエネルギーカードすべてを、あなたの場に"
                        "いる別の「ナツメのポケモン」1匹につけなおす。")
# kyuura の文面は閉じかっこ「)」がない（pcg-search.com の同じ版のページにはある。処理は変わらない。kyuura への報告事項）
WARP_POINT_TEXT = ("お互いの対戦ポケモンを、それぞれ、控えポケモンと入れ替える。入れ替わるポケモンは、それぞれ、持ち主が選ぶ。(入れ替えは、相手プレイヤーが先におこなう。控えが"
                   "いないプレイヤーは、入れ替えをしない。")

# MW1: カスミのいかりで、山札が 7 枚より少ないとき（「上から7枚のカードを見て」の 7 枚がない）。見られるだけ見て 2 枚を選ぶ（2 枚より少なければ選べるだけ）のか、使えない・
# 何もしないのかは、印刷の文面・kyuura の記録で決まらない（引くときの「引けるだけ」（p.312）は「カードを引く」の規定で、見る・手札に加える処理に当てはめない）
MISTYS_WRATH_SHORT_DECK_CODE = "UNRESOLVED_MISTYS_WRATH_SHORT_DECK"
MISTYS_WRATH_SHORT_DECK_REASON = (
    "カスミのいかりの「山札の上から7枚のカードを見て、その中から2枚を選んで手札に加え」で、山札が 7 枚より少ないときに、見られるだけ見て選ぶのか、このカードを使えないのかは、"
    "印刷の文面・kyuura の記録で決まらないので扱わない（MW1。「カードを引く」ときの「引けるだけ」（p.312）を、見る・手札に加える処理に当てはめない）"
)
# EM1: エネルギー・リムーブで、相手の場のポケモンにエネルギーカードが 1 枚もないとき（はがすカードがない）
ENERGY_REMOVAL_WITHOUT_TARGET_CODE = "UNRESOLVED_ENERGY_REMOVAL_WITHOUT_TARGET"
ENERGY_REMOVAL_WITHOUT_TARGET_REASON = (
    "相手の場のポケモンにエネルギーカードが 1 枚もない。このときにエネルギー・リムーブを使えるか（使えない・使って何もしないのどちらか）は、印刷の文面・kyuura の記録で"
    "決まらないので扱わない（EM1。ほかのカードの「対象がない」ときの問いの答えを流用しない）"
)
# SP1: いいきずぐすりで、ダメージカウンターののっていないポケモンを選ぶとき（エネルギーカードはついている）
SUPER_POTION_UNDAMAGED_CODE = "UNRESOLVED_SUPER_POTION_UNDAMAGED_TARGET"
SUPER_POTION_UNDAMAGED_REASON = (
    "ダメージカウンターののっていないポケモンを、いいきずぐすり（「そのポケモンのダメージカウンターを4個までとりのぞくことができる」）の対象に選んで、エネルギーカードを"
    "はがしてすてられるかは、印刷の文面・kyuura の記録で決まらないので扱わない（SP1。きずぐすりの UNRESOLVED_POTION_UNDAMAGED_TARGET とは別のカードの問い）"
)
# FH1: なんでもなおしの「特殊状態にあるポケモン」がどのポケモンか（使ったプレイヤーの対戦ポケモンだけ・どちらかを選ぶ・特殊状態のポケモンすべて）
FULL_HEAL_SCOPE_CODE = "UNRESOLVED_FULL_HEAL_SCOPE"
FULL_HEAL_SCOPE_REASON = (
    "なんでもなおしの「特殊状態にあるポケモンの全ての特殊状態を回復する」の対象（自分の対戦ポケモンだけか・相手の対戦ポケモンも含むか・選ぶのか）と、特殊状態のポケモンが"
    "いないときに使えるかは、印刷の文面・kyuura の記録で決まらないので扱わない（FH1。英語版の「Your Active Pokémon」を持ち込まない）。どの読み方でも結果が同じ（特殊状態の"
    "ポケモンが自分の対戦ポケモンだけ）なら回復する"
)
# GL1・GL2: サカキの切り札で、自分の場に「サカキのポケモン」がいない・選んだサカキのポケモンにダメージカウンターがのっていない
LAST_RESORT_WITHOUT_TARGET_CODE = "UNRESOLVED_LAST_RESORT_WITHOUT_TARGET"
LAST_RESORT_WITHOUT_TARGET_REASON = (
    "自分の場に「サカキのポケモン」がいない。このときにサカキの切り札を使えるか（使えない・手札をトラッシュするだけ）は、印刷の文面・kyuura の記録で決まらないので扱わない"
    "（GL1。トレーナー「サカキ」の TR1 とは別のカードの問い）"
)
LAST_RESORT_UNDAMAGED_CODE = "UNRESOLVED_LAST_RESORT_UNDAMAGED_TARGET"
LAST_RESORT_UNDAMAGED_REASON = (
    "ダメージカウンターののっていない「サカキのポケモン」を、サカキの切り札（「そのポケモンにのっているダメージカウンターを、すべてとりのぞく。その後、あなたの手札をすべて"
    "トラッシュする」）の対象に選べるかは、印刷の文面・kyuura の記録で決まらないので扱わない（GL2）"
)
# SB1・SB2: ナツメで、自分の場に「ナツメのポケモン」が 2 匹いない（「別の」ナツメのポケモンがいない）・はがすポケモンにエネルギーカードがついていない
SABRINA_WITHOUT_TWO_CODE = "UNRESOLVED_SABRINA_WITHOUT_TWO_POKEMON"
SABRINA_WITHOUT_TWO_REASON = (
    "自分の場に「ナツメのポケモン」が 2 匹以上いない（つけなおす「別の「ナツメのポケモン」」がいない）。このときにナツメを使えるかは、印刷の文面・kyuura の記録で決まらない"
    "ので扱わない（SB1）"
)
SABRINA_SOURCE_WITHOUT_ENERGY_CODE = "UNRESOLVED_SABRINA_SOURCE_WITHOUT_ENERGY"
SABRINA_SOURCE_WITHOUT_ENERGY_REASON = (
    "エネルギーカードがついていない「ナツメのポケモン」を、ナツメの「それについているエネルギーカードをすべてはがす」ポケモンに選べるかは、印刷の文面・kyuura の記録で"
    "決まらないので扱わない（SB2）"
)


def secret_machine_ok(definition: CardDefinition) -> bool:
    """kyuura の種類 ``rockets_secret_machine``（「ロケット団秘密メカ」。夜の廃品回収（v0.53）・ねむれ!ねむれ!（v0.55））だけを持つトレーナーか。2000.02.14 版の規定の記録
    （kyuura の rule_clauses）にこの種類を区別する規定はなく、今の対応カードにこの種類を参照するカードもないので、この種類のほかの種類がないときだけ受け付ける（ほかの種類の
    トレーナーを一律に受け付けない。この種類を参照するカードを加えるときに見直す）。"""
    return definition.trainer_kinds == ("rockets_secret_machine",)


def _require_text(definition: CardDefinition, text: str, effect: TrainerEffect, *, secret_machine: bool = False) -> list[str]:
    """v0.55: トレーナーの登録の共通の確かめ（種類と、文面が登録の文面と同じか）。"""
    problems = [] if secret_machine and secret_machine_ok(definition) else TrainerEffect.check(effect, definition)
    if definition.trainer_text_ja != text:
        problems.append(f"文面 {definition.trainer_text_ja!r} が、登録の文面ではない")
    return problems


def _decided_by(decision: PendingDecision, player: int, what: str) -> list[str]:
    return [] if decision.player == player else [f"{what}の決定をするのがプレイヤー {decision.player}（{player} のはず）"]


def _attached_cards(pokemons: Iterable[PokemonInPlay]) -> tuple[int, ...]:
    """場のポケモン（場の並び）についているエネルギーカード（ポケモンの順・ついている順）。"""
    return tuple(uid for pokemon in pokemons for uid in pokemon.energy)


@dataclass(frozen=True)
class LookTopTakeRestDiscardTrainer(TrainerEffect):
    """v0.55: 自分の山札の上から ``look`` 枚を見て、その中から ``take`` 枚を選んで手札に加え、残りをトラッシュする（カスミのいかり）。

    - 見る（ログ ``look_at_deck_top`` の ``cards`` は使ったプレイヤーだけ）→ 選ぶ（決定 ``TAKE_LOOKED_CARDS``。選べるものは見たカード（山札の上からの順）。ちょうど ``take``
      枚。「選んで手札に加え」に選ばなくてよい言い回しはない）→ 手札に加える（ログ ``looked_to_hand`` の ``cards`` は使ったプレイヤーだけ。「カードを引く」ではない）・残りを
      トラッシュ（ログ ``looked_to_discard`` は公開）。見た部分より下の山札の並びは変えず、切らない
    - 山札が ``look`` 枚より少ないとき（2 枚未満・0 枚を含む）は MW1 で、手札から出す前に止める
    """

    text: str
    look: int = 7
    take: int = 2
    implementation_id = "look_top_take_rest_discard"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = _require_text(definition, self.text, self)
        if not problems and (f"山札の上から{self.look}枚のカードを見て" not in self.text or f"その中から{self.take}枚を選んで手札に加え、残りをトラッシュする" not in self.text):
            problems.append("文面と登録の枚数（見る・手札に加える）が合わない")
        return problems

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        deck = state.players[use.player].deck
        if len(deck) < self.look:
            raise UnsupportedError(MISTYS_WRATH_SHORT_DECK_CODE, f"{MISTYS_WRATH_SHORT_DECK_REASON}。山札が {len(deck)} 枚")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        cards = tuple(state.players[use.player].deck[:self.look])
        state.add_event("look_at_deck_top", player=use.player, owner=use.player, count=self.look, cards=cards, trainer_card=use.card)
        push_trainer_decision(state, use, kind=TAKE_LOOKED_CARDS, player=use.player, options=cards, min_choices=self.take, max_choices=self.take)

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        take_looked_deck_cards(state, use.player, len(decision.options), choices, trainer=use.card)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = f"トレーナー {use.card_id}"
        problems = _decided_by(decision, use.player, what)
        if decision.kind != TAKE_LOOKED_CARDS:
            return problems + [f"{what}の決定の種類が {decision.kind!r}（{TAKE_LOOKED_CARDS} のはず）"]
        if decision.options != tuple(state.players[use.player].deck[:self.look]) or (decision.min_choices, decision.max_choices) != (self.take, self.take):
            problems.append(f"{what}の決定 {decision.options}（{decision.min_choices}〜{decision.max_choices}）が、山札の上の {self.look} 枚から {self.take} 枚ではない")
        looked = [e for e in _last_trainer_events(state, use) if e["kind"] == "look_at_deck_top" and e.get("trainer_card") == use.card]
        if len(looked) != 1 or tuple(looked[0]["cards"]) != decision.options:
            problems.append(f"{what}の決定の前に、同じカードを見たログがない")
        return problems


@dataclass(frozen=True)
class OpponentHandTrainerToDeck(TrainerEffect):
    """v0.55: 相手の手札を見て、その中にトレーナーカードがあれば 1 枚を選び、相手の山札にもどさせ、その山札を切る（ロケット団のおねーさん）。

    - 見る（``zones.look_at_hand``。ログ ``look_at_hand`` の ``cards`` は見たプレイヤーと持ち主だけ。1 回見るだけで、あとで観測の手札を公開しない（［おみとおし］の
      ような続けて見せる効果ではない））。相手の手札が 0 枚でも見る処理をして終わる（トレーナーカードがない場合の一つ。説明の「あれば」）
    - トレーナーカードは、手札にある間の印刷の分類（``CardFilter("trainer")``。なにかの化石・ピッピ人形・ロケット団秘密メカなどの種類のあるトレーナーも含む）
    - 選ぶのは使ったプレイヤー（決定 ``OPPONENT_HAND_TO_DECK``。選べるものは相手の手札のトレーナーカード（手札の並び）。1 枚でも決定を出す）。もどすのは相手の山札
      （``zones.opponent_hand_card_to_deck``。相手の決定はない）。そのあと相手の山札を切る
    - トレーナーカードがなければ、もどさず、切らない（「その後」は、あればの処理のあと。v0.53 の MB1 と同じ読み方。実装上の読み方）
    """

    text: str
    implementation_id = "opponent_hand_trainer_to_deck"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = _require_text(definition, self.text, self)
        if not problems and ("相手の手札を見る" not in self.text or "トレーナーカードがあれば、1枚を選び" not in self.text or "相手の山札にもどさせる" not in self.text):
            problems.append("文面と登録の処理（相手の手札を見る・トレーナーカード 1 枚・相手の山札）が合わない")
        return problems

    @staticmethod
    def _trainers(state: GameState, owner: int) -> tuple[int, ...]:
        return tuple(uid for uid in state.players[owner].hand if CardFilter("trainer").matches(state.card_def(uid)))

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        opponent = 1 - use.player
        look_at_hand(state, use.player, opponent, trainer=use.card)
        options = self._trainers(state, opponent)
        if options:
            push_trainer_decision(state, use, kind=OPPONENT_HAND_TO_DECK, player=use.player, options=options)

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        opponent = 1 - use.player
        if choices[0] not in self._trainers(state, opponent):
            raise RuntimeError(f"ロケット団のおねーさんで選んだカード {choices} が、相手の手札のトレーナーカードではない（エンジンの不具合）")
        opponent_hand_card_to_deck(state, opponent, choices[0], looker=use.player, trainer=use.card)
        shuffle_deck(state, opponent)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = f"トレーナー {use.card_id}"
        problems = _decided_by(decision, use.player, what)
        if decision.kind != OPPONENT_HAND_TO_DECK:
            return problems + [f"{what}の決定の種類が {decision.kind!r}（{OPPONENT_HAND_TO_DECK} のはず）"]
        expected = self._trainers(state, 1 - use.player)
        if not expected or decision.options != expected or (decision.min_choices, decision.max_choices) != (1, 1):
            problems.append(f"{what}の決定 {decision.options} が、相手の手札のトレーナーカード {expected} から 1 枚ではない")
        if not any(e["kind"] == "look_at_hand" and e.get("trainer_card") == use.card for e in _last_trainer_events(state, use)):
            problems.append(f"{what}の決定が、相手の手札を見るまえに出ている")
        return problems


@dataclass(frozen=True)
class DiscardPileExchange(TrainerEffect):
    """v0.55: 自分のトラッシュの枚数を数え、それらをすべて山札にもどして切り、数えた枚数を山札の上からトラッシュする（トラッシュ交換）。

    - 数えるのは、このカードを使う時点のトラッシュ（使っているこのカードは ``trainer_in_use`` にあり、まだトラッシュにない（使い終わってからトラッシュする）ので数えない）
    - もどす（``zones.discard_pile_to_deck``。公開）→ 切る（0 枚でも切る。「もどし、よく切る」は続けて書かれている）→ 上から数えた枚数をトラッシュ（``zones.deck_top_to_discard``。
      公開。「カードを引く」ではない）。もどしたカードもトラッシュされうる。もどしたあとの山札は数えた枚数以上あるので、足りないことはない（トラッシュ 0 枚なら 0 枚）
    - 選ぶものがないので決定を出さない。使うための条件はない
    """

    text: str
    implementation_id = "discard_pile_exchange"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = _require_text(definition, self.text, self)
        if not problems and ("トラッシュにあるカードの枚数を数えてから、それらをすべて山札にもどし、よく切る" not in self.text
                             or "数えた枚数のカードを山札の上から取って、トラッシュする" not in self.text):
            problems.append("文面と登録の順番（数える → もどす → 切る → 上からトラッシュ）が合わない")
        return problems

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        count = len(discard_pile_to_deck(state, use.player, trainer=use.card))
        shuffle_deck(state, use.player)
        deck_top_to_discard(state, use.player, count, trainer=use.card)


@dataclass(frozen=True)
class DiscardAttachedEnergyTrainer(TrainerEffect):
    """v0.55: 相手の場のポケモンについているエネルギーカードを ``opponent_cards`` 枚はがしてすてるトレーナーの共通の処理（エネルギー・リムーブ・超エネルギーリムーブ）。

    - ``own_cost``（超エネルギーリムーブの「自分の場のポケモンについているエネルギーカードを1枚はがしてすてることによって」）: 使うための条件。自分の場のポケモンに
      エネルギーカードがなければ手札から出す前に ``NO_ENERGY_TO_DISCARD``。段階 1 で、使ったプレイヤーが自分の場のポケモンについているエネルギーカードを選んで（決定
      ``DISCARD_ENERGY``。選べるものはポケモンの場の並び・ついている順）トラッシュする。後の段階の不正な答えで取り消さない
    - ``opponent_cards`` が 1（エネルギー・リムーブ）: 相手の場のポケモンについているエネルギーカードから 1 枚を選ぶ（決定 ``DISCARD_OPPONENT_ENERGY``。ポケモンは選んだカードの
      ついているポケモン）。相手の場にエネルギーカードがなければ EM1（使う前）
    - ``opponent_cards`` が 2（超エネルギーリムーブの「相手の場のポケモン1匹から2枚」）: 段階 2 で相手の場のポケモンを 1 匹選び（``SELECT_POKEMON``）、段階 3 でそのポケモンに
      ついているエネルギーカードから 2 枚を選ぶ（``DISCARD_OPPONENT_ENERGY``。ちょうど 2 枚。2 匹から 1 枚ずつはできない）。エネルギーカードが 2 枚より少ないポケモンは、選べるが
      選ぶと FC1（説明が決まった枚数を選ばせるとき足りない。kyuura の MIX-SUPER-ENERGY-REMOVAL の「before」の要約「2 枚まで」は、のちの版の記録の要約で最新の説明ではないので
      使わない）。どの相手のポケモンも 2 枚より少なければ、使う前に FC1
    - 選ぶのはいつも使ったプレイヤー。はがしたカードは持ち主（相手）のトラッシュ（``zones.discard_attached_energy_cards``。ログ ``trainer_discard_energy``）。カードを数える
      （何個ぶんのエネルギーかではない）。トレーナーの効果なので「ワザをうけない」状態・「とうめい」などワザを防ぐ効果を当てはめない
    """

    text: str
    opponent_cards: int
    own_cost: int = 0
    implementation_id = "discard_attached_energy_trainer"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = _require_text(definition, self.text, self)
        if problems:
            return problems
        expected = {
            "自分のエネルギーカードをはがしてすてる条件": ("自分の場のポケモンについているエネルギーカードを1枚はがしてすてることによって" in self.text, self.own_cost == 1),
            "相手のポケモン 1 匹から 2 枚": ("相手の場のポケモン1匹から2枚のエネルギーカードをはがしてすてる" in self.text, self.opponent_cards == 2),
            "相手のエネルギーカード 1 枚": ("相手の場のポケモンについているエネルギーカードを1枚はがしてすてる" in self.text, self.opponent_cards == 1),
        }
        problems += [f"文面と登録の「{name}」が合わない" for name, (found, registered) in expected.items() if found != registered]
        return problems

    def _short(self, state: GameState, use: TrainerUse) -> tuple[int, ...]:
        """相手の場のポケモンのうち、エネルギーカードが ``opponent_cards`` 枚より少ないもの（選ぶと FC1）。"""
        return tuple(p.pokemon_id for p in state.players[1 - use.player].in_play() if len(p.energy) < self.opponent_cards)

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if self.own_cost and not _attached_cards(state.players[use.player].in_play()):
            raise IllegalActionError("NO_ENERGY_TO_DISCARD", "自分の場のポケモンにエネルギーカードがついていないので、使うための条件（はがしてすてる）を満たせない")
        opponent = state.players[1 - use.player].in_play()
        if self.opponent_cards == 1:
            if not _attached_cards(opponent):
                raise UnsupportedError(ENERGY_REMOVAL_WITHOUT_TARGET_CODE, ENERGY_REMOVAL_WITHOUT_TARGET_REASON)
        elif len(self._short(state, use)) == len(opponent):
            raise UnsupportedError(STATED_CARDS_SHORT_CODE, f"{STATED_CARDS_SHORT_REASON}。相手の場のどのポケモンにも、エネルギーカードが {self.opponent_cards} 枚ついていない")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        if self.own_cost:
            push_trainer_decision(state, use, kind=DISCARD_ENERGY, player=use.player, options=_attached_cards(state.players[use.player].in_play()),
                                  min_choices=self.own_cost, max_choices=self.own_cost, context=(("stage", 1),))
            return
        self._opponent_stage(state, use)

    def _opponent_stage(self, state: GameState, use: TrainerUse) -> None:
        opponent = state.players[1 - use.player].in_play()
        if self.opponent_cards == 1:
            push_trainer_decision(state, use, kind=DISCARD_OPPONENT_ENERGY, player=use.player, options=_attached_cards(opponent), context=(("stage", 3),))
            return
        push_trainer_decision(state, use, kind=SELECT_POKEMON, player=use.player, options=[p.pokemon_id for p in opponent], context=(("stage", 2),),
                              unresolved_choices=self._short(state, use), unresolved_code=STATED_CARDS_SHORT_CODE,
                              unresolved_reason=f"{STATED_CARDS_SHORT_REASON}。選んだポケモンにエネルギーカードが {self.opponent_cards} 枚ついていない")

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        stage = decision.context_value("stage")
        if stage == 1:
            owner = use.player
            for pokemon in state.players[owner].in_play():
                mine = tuple(uid for uid in choices if uid in pokemon.energy)
                if mine:
                    discard_attached_energy_cards(state, owner, pokemon, mine, trainer=use.card, user=use.player)
            self._opponent_stage(state, use)
            return
        opponent = 1 - use.player
        if stage == 2:
            _, target = state.find_pokemon(choices[0])
            push_trainer_decision(state, use, kind=DISCARD_OPPONENT_ENERGY, player=use.player, options=tuple(target.energy),
                                  min_choices=self.opponent_cards, max_choices=self.opponent_cards, context=(("stage", 3), ("target", target.pokemon_id)))
            return
        holders = [p for p in state.players[opponent].in_play() if any(uid in p.energy for uid in choices)]
        if len(holders) != 1:
            raise RuntimeError(f"はがすエネルギーカード {choices} が、相手の場のポケモン 1 匹についていない（エンジンの不具合）")
        discard_attached_energy_cards(state, opponent, holders[0], choices, trainer=use.card, user=use.player)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = f"トレーナー {use.card_id}"
        problems = _decided_by(decision, use.player, what)
        stage = decision.context_value("stage")
        opponent = state.players[1 - use.player].in_play()
        events = _last_trainer_events(state, use)
        paid = any(e["kind"] == "trainer_discard_energy" and e["player"] == use.player and e["trainer_card"] == use.card for e in events)
        if stage == 1 and self.own_cost:
            expected, bounds, kind = _attached_cards(state.players[use.player].in_play()), (self.own_cost, self.own_cost), DISCARD_ENERGY
        elif stage == 2 and self.opponent_cards > 1:
            expected, bounds, kind = tuple(p.pokemon_id for p in opponent), (1, 1), SELECT_POKEMON
            if tuple(decision.context_value("unresolved_choices", ())) != self._short(state, use):
                problems.append(f"{what}の選ぶと止める選択 {decision.context_value('unresolved_choices', ())} が、エネルギーカードが足りないポケモン {self._short(state, use)} ではない")
        elif stage == 3 and self.opponent_cards == 1:
            expected, bounds, kind = _attached_cards(opponent), (1, 1), DISCARD_OPPONENT_ENERGY
        elif stage == 3:
            found = state.find_pokemon(decision.context_value("target"))
            if found is None or found[0] != 1 - use.player or len(found[1].energy) < self.opponent_cards:
                return problems + [f"{what}のエネルギーカードを選ぶポケモン {decision.context_value('target')} が、カードの足りる相手のポケモンではない"]
            expected, bounds, kind = tuple(found[1].energy), (self.opponent_cards, self.opponent_cards), DISCARD_OPPONENT_ENERGY
        else:
            return problems + [f"{what}の決定の段階 {stage!r} が登録と合わない"]
        if decision.kind != kind or decision.options != expected or (decision.min_choices, decision.max_choices) != bounds:
            problems.append(f"{what}の段階 {stage} の決定 {decision.kind} {decision.options}（{decision.min_choices}〜{decision.max_choices}）が {kind} {expected} {bounds} と合わない")
        if self.own_cost and stage != 1 and not paid:
            problems.append(f"{what}の相手のポケモンの決定が、使うための条件（自分のエネルギーカードをはがしてすてる）のまえに出ている")
        return problems


@dataclass(frozen=True)
class DiscardEnergyThenHealTrainer(TrainerEffect):
    """v0.55: 自分のポケモン 1 匹のエネルギーカードを 1 枚はがしてすてることによって、そのポケモンのダメージカウンターを ``max_counters`` 個までとりのぞくことができる
    （いいきずぐすり）。

    - 段階 1: 使ったプレイヤーが自分の場のポケモンを選ぶ（``SELECT_POKEMON``。選べるものはエネルギーカードがついているポケモン。はがすカードのないポケモンは条件を満たせない
      ので選べない）。自分の場にエネルギーカードがついているポケモンがいなければ、手札から出す前に ``NO_ENERGY_TO_DISCARD``。ダメージカウンターののっていないポケモンは選べるが
      選ぶと SP1。選べるポケモンがどれもそうなら使う前に SP1
    - 段階 2: そのポケモンについているエネルギーカードを 1 枚選び（``DISCARD_ENERGY``。1 枚でも決定を出す）、はがしてすてる（``trainer_discard_energy``。使うための条件なので、
      このときにトラッシュする。後の段階で取り消さない）
    - 段階 3: とりのぞく数を選ぶ（``SELECT_COUNTER_COUNT``。0〜min(``max_counters``, のっている数)。「4個まで…ことができる」。きずぐすりの決まった 2 個とは別。ダメージカウンター
      が 4 個より少なければ、のっている数まで）。ログ ``remove_damage_counters``（``trainer_card``）。0 個ならとりのぞかない（ログは 0 個で残す）
    - エネルギーカードをはがして最大HPが下がる（［ガスのからだ］）とき、とりのぞく前の状態で最大HPがのっているダメージ以下になれば、段階 2 の答えを MH1 で受け付けない
      （エンジンの ``max_hp_drops``。はがすのは実際の処理の順番の一歩で、実装の都合の途中の状態ではない）
    """

    text: str
    max_counters: int = 4
    implementation_id = "discard_energy_then_heal_trainer"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = _require_text(definition, self.text, self)
        if not problems and (f"ダメージカウンターを{self.max_counters}個までとりのぞくことができる" not in self.text
                             or "エネルギーカードを1枚はがしてすてることによって" not in self.text):
            problems.append("文面と登録の数（はがす 1 枚・とりのぞく数まで）が合わない")
        return problems

    @staticmethod
    def _targets(state: GameState, use: TrainerUse) -> list[PokemonInPlay]:
        return [p for p in state.players[use.player].in_play() if p.energy]

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        targets = self._targets(state, use)
        if not targets:
            raise IllegalActionError("NO_ENERGY_TO_DISCARD", "自分の場のポケモンにエネルギーカードがついていないので、使うための条件（はがしてすてる）を満たせない")
        if all(p.damage == 0 for p in targets):
            raise UnsupportedError(SUPER_POTION_UNDAMAGED_CODE, f"{SUPER_POTION_UNDAMAGED_REASON}。エネルギーカードがついているポケモンに、ダメージカウンターがのっていない")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        targets = self._targets(state, use)
        push_trainer_decision(state, use, kind=SELECT_POKEMON, player=use.player, options=[p.pokemon_id for p in targets],
                              unresolved_choices=[p.pokemon_id for p in targets if p.damage == 0], unresolved_code=SUPER_POTION_UNDAMAGED_CODE,
                              unresolved_reason=SUPER_POTION_UNDAMAGED_REASON)

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if decision.kind == SELECT_POKEMON:
            _, target = state.find_pokemon(choices[0])
            push_trainer_decision(state, use, kind=DISCARD_ENERGY, player=use.player, options=tuple(target.energy), context=(("target", target.pokemon_id),))
            return
        _, target = state.find_pokemon(decision.context_value("target"))
        if decision.kind == DISCARD_ENERGY:
            discard_attached_energy_cards(state, use.player, target, choices, trainer=use.card, user=use.player)
            per = state.rules.damage_per_counter
            push_trainer_decision(state, use, kind=SELECT_COUNTER_COUNT, player=use.player, options=tuple(range(min(self.max_counters, target.damage // per) + 1)),
                                  context=(("target", target.pokemon_id),))
            return
        target.damage -= choices[0] * state.rules.damage_per_counter
        state.add_event("remove_damage_counters", player=use.player, pokemon=target.card, pokemon_id=target.pokemon_id, counters=choices[0],
                        total_damage=target.damage, trainer_card=use.card)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = f"トレーナー {use.card_id}"
        if decision.kind == SELECT_POKEMON:
            targets = self._targets(state, use)
            return _select_own_pokemon_problems(decision, use, (p.pokemon_id for p in targets), "「いいきずぐすり」",
                                                unresolved=(p.pokemon_id for p in targets if p.damage == 0))
        problems = _decided_by(decision, use.player, what)
        found = state.find_pokemon(decision.context_value("target"))
        if found is None or found[0] != use.player:
            return problems + [f"{what}の対象 {decision.context_value('target')} が自分の場のポケモンではない"]
        target = found[1]
        per = state.rules.damage_per_counter
        if decision.kind == DISCARD_ENERGY:
            if decision.options != tuple(target.energy) or not target.energy or (decision.min_choices, decision.max_choices) != (1, 1) or target.damage == 0:
                problems.append(f"{what}のはがすカードの決定 {decision.options} が、対象 {target.pokemon_id} のエネルギーカード 1 枚ではない")
        elif decision.kind == SELECT_COUNTER_COUNT:
            if decision.options != tuple(range(min(self.max_counters, target.damage // per) + 1)) or (decision.min_choices, decision.max_choices) != (1, 1):
                problems.append(f"{what}のとりのぞく数の決定 {decision.options} が、0〜min({self.max_counters}, のっている数) ではない")
            if not any(e["kind"] == "trainer_discard_energy" and e["trainer_card"] == use.card and e["pokemon_id"] == target.pokemon_id
                       for e in _last_trainer_events(state, use)):
                problems.append(f"{what}のとりのぞく数の決定が、エネルギーカードをはがしてすてるまえに出ている")
        else:
            problems.append(f"{what}の決定の種類が {decision.kind!r}")
        return problems


@dataclass(frozen=True)
class CureSpecialConditionsTrainer(TrainerEffect):
    """v0.55: 特殊状態にあるポケモンの全ての特殊状態を回復する（なんでもなおし）。

    - 特殊状態（どく・ねむり・マヒ・こんらん。p.322。kyuura の GR-2000-P322-SPECIAL-CONDITIONS）になるのはバトル場のポケモンだけ。説明の「特殊状態にあるポケモン」が、自分の
      対戦ポケモンだけか・相手の対戦ポケモンも含むか・選ぶのかは決まらない（FH1）。どの読み方でも結果が同じ場合（特殊状態のポケモンが、使ったプレイヤーの対戦ポケモンだけ）
      だけ回復し、ほかの場合（相手の対戦ポケモンが特殊状態・どちらも特殊状態でない）は手札から出す前に FH1 で止める
    - 回復するのは特殊状態だけ（``conditions.clear_special_conditions``。理由 ``CURED``。ログ ``special_conditions_removed`` の ``trainer_card``）。ダメージ・ワザによる持続する
      効果・にげるの失敗の記録は変えない。やけど（ネオ以降）はない
    """

    text: str
    implementation_id = "cure_special_conditions_trainer"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = _require_text(definition, self.text, self)
        if not problems and "特殊状態にあるポケモンの全ての特殊状態を回復する" not in self.text:
            problems.append("文面と登録の処理（特殊状態の回復）が合わない")
        return problems

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        own, opponent = state.players[use.player].active, state.players[1 - use.player].active
        own_hit = own is not None and bool(own.conditions.names())
        opponent_hit = opponent is not None and bool(opponent.conditions.names())
        if opponent_hit or not own_hit:
            where = "相手の対戦ポケモンが特殊状態" if opponent_hit else "特殊状態のポケモンがいない"
            raise UnsupportedError(FULL_HEAL_SCOPE_CODE, f"{FULL_HEAL_SCOPE_REASON}。{where}")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        clear_special_conditions(state, use.player, state.players[use.player].active, CURED, trainer_card=use.card)


@dataclass(frozen=True)
class CoinStatusOnOpponentActiveTrainer(TrainerEffect):
    """v0.55: コインを投げて「おもて」なら、相手の対戦ポケモンを ``condition`` 状態にする（ねむれ!ねむれ!）。

    - コインを投げるのは使ったプレイヤー（``coin_flip`` の ``source`` は ``"trainer"``）。「うら」なら何もしない
    - 特殊状態にするのは既存の処理（``conditions.put_to_sleep``）で、［めんえき］（v0.46）・「ばける」のもどり（v0.49）・ほかの特殊状態との重複（p.322）はそのまま。トレーナーの
      効果なので「ワザをうけない」状態・「とうめい」は評価しない（ワザを防ぐ効果）
    - 「おもて」で特殊状態にしたあとの状態が受け付けられない（決められない姿・MH1。``state_stop_after``）なら、コインの結果で受け付けるかが変わらないように、コインの前に止める
    - kyuura の種類 ``rockets_secret_machine`` だけを持つトレーナーを受け付ける（``secret_machine_ok``。ほかの種類を一律に受け付けない）
    """

    text: str
    condition: str = SLEEP
    implementation_id = "coin_status_on_opponent_active_trainer"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = _require_text(definition, self.text, self, secret_machine=True)
        if not problems and (self.condition != SLEEP or self.text != "コインを投げて「おもて」なら、相手の対戦ポケモンを「ねむり」状態にする。"):
            problems.append("文面と登録の特殊状態（ねむり）が合わない")
        return problems

    def _apply(self, state: GameState, use: TrainerUse) -> None:
        opponent = 1 - use.player
        put_to_sleep(state, opponent, state.players[opponent].active, effect=use.card_id)

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        trial = state.clone()
        self._apply(trial, use)
        stop = state_stop_after(state, trial)
        if stop is not None:
            raise UnsupportedError(stop[0], f"コインが「おもて」で相手の対戦ポケモンを特殊状態にすると: {stop[1]}")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        if _trainer_coin(state, use):
            self._apply(state, use)


@dataclass(frozen=True)
class ReturnBasicEnergyToHandTrainer(TrainerEffect):
    """v0.55: 自分の場のポケモンについている基本エネルギーカードを好きなだけはがし、手札にもどしてよい（エネルギーサーキュレート）。

    - 選ぶのは使ったプレイヤー（決定 ``RETURN_ENERGY``。選べるものは自分の場のポケモン（場の並び）についている基本エネルギーカード（カードの種類。エナジーバーンで「炎」になって
      いても基本エネルギーカード。供給するエネルギーのタイプではない）。0〜すべて。何匹のポケモンからでもよい）。0 枚は「戻してよい」の、もどさないこと
    - もどす先は手札（``zones.return_attached_energy_to_hand``。ログ ``trainer_return_energy``。ポケモンごと）。トラッシュ・手札からつける通常の操作ではない
    - 選べるカードがなければ決定を出さずに終わる
    - エネルギーカードをもどして最大HPが下がる（［ガスのからだ］）答えは、のっているダメージ以下になれば MH1 で受け付けない（エンジンの ``max_hp_drops``。ほかの答えはある）
    """

    text: str
    implementation_id = "return_basic_energy_to_hand_trainer"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = _require_text(definition, self.text, self)
        if not problems and ("「基本エネルギーカード」を好きなだけはがし、手札に戻してよい" not in self.text):
            problems.append("文面と登録の処理（基本エネルギーカード・好きなだけ・手札）が合わない")
        return problems

    @staticmethod
    def _options(state: GameState, use: TrainerUse) -> tuple[int, ...]:
        return tuple(uid for uid in _attached_cards(state.players[use.player].in_play()) if state.card_def(uid).is_basic_energy)

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        options = self._options(state, use)
        if options:
            push_trainer_decision(state, use, kind=RETURN_ENERGY, player=use.player, options=options, min_choices=0, max_choices=len(options))

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        for pokemon in state.players[use.player].in_play():
            mine = tuple(uid for uid in choices if uid in pokemon.energy)
            if mine:
                return_attached_energy_to_hand(state, use.player, pokemon, mine, trainer=use.card)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = f"トレーナー {use.card_id}"
        problems = _decided_by(decision, use.player, what)
        options = self._options(state, use)
        if decision.kind != RETURN_ENERGY or not options or decision.options != options or (decision.min_choices, decision.max_choices) != (0, len(options)):
            problems.append(f"{what}の決定 {decision.kind} {decision.options} が、自分の場の基本エネルギーカード {options} の 0〜すべてではない")
        return problems


HEAL_SELF = "self"
HEAL_BOTH = "both"


@dataclass(frozen=True)
class HealEachDamagedPokemonTrainer(TrainerEffect):
    """v0.55: ダメージカウンターがのっている場のポケモン全員から、それぞれ、ダメージカウンターをとりのぞくトレーナーの共通の処理（エリカの親切・タケシ・ポケモンセンター）。

    - ``who``: ``HEAL_SELF``（自分の場。タケシ・ポケモンセンター）・``HEAL_BOTH``（お互いの場。エリカの親切。使ったプレイヤー → 相手の順。選ぶものはない）
    - ``counters``: ポケモンごとにとりのぞく数（のっている数まで。1 個だけのっていれば 1 個）。None はすべて（ポケモンセンター）
    - ``discard_energy``（ポケモンセンター）: とりのぞいたポケモンについているエネルギーカードをすべてはがしてすてる（とりのぞいたあと。``trainer_discard_energy``）。ダメージ
      カウンターののっていないポケモンのエネルギーカードはすてない。重なった進化カード・ついているトレーナーはそのまま
    - ダメージカウンターののっていないポケモンは何もしない。全員のっていなければ何も起こらずに使い終わる（「全員から」の対象が 0 匹。選ばせるものがないので、「選ぶ」効果の
      対象がない問いとは別。実装上の読み方）。トレーナーの効果なので「ワザをうけない」状態・「とうめい」は評価しない
    """

    text: str
    who: str
    counters: int | None
    discard_energy: bool = False
    implementation_id = "heal_each_damaged_pokemon_trainer"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = _require_text(definition, self.text, self)
        if problems:
            return problems
        expected = {
            "お互いの場": ("お互いの場" in self.text, self.who == HEAL_BOTH),
            "2 つずつ": ("ダメージカウンターを2つずつとりのぞく" in self.text, self.counters == 2),
            "1 つずつ": ("1つずつダメージカウンターをとりのぞく" in self.text, self.counters == 1),
            "エネルギーカード全てをはがしてすてる": ("ダメージカウンターとエネルギーカード全てをはがしてすてる" in self.text, self.discard_energy and self.counters is None),
        }
        problems += [f"文面と登録の「{name}」が合わない" for name, (found, registered) in expected.items() if found != registered]
        if self.who not in (HEAL_SELF, HEAL_BOTH):
            problems.append(f"とりのぞくプレイヤー {self.who!r} が {HEAL_SELF}・{HEAL_BOTH} ではない")
        return problems

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        per = state.rules.damage_per_counter
        players = (use.player,) if self.who == HEAL_SELF else (use.player, 1 - use.player)
        for owner in players:
            for pokemon in state.players[owner].in_play():
                if pokemon.damage == 0:
                    continue
                removed = pokemon.damage // per if self.counters is None else min(self.counters, pokemon.damage // per)
                pokemon.damage -= removed * per
                state.add_event("remove_damage_counters", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, counters=removed,
                                total_damage=pokemon.damage, trainer_card=use.card)
                if self.discard_energy and pokemon.energy:
                    discard_attached_energy_cards(state, owner, pokemon, tuple(pokemon.energy), trainer=use.card, user=use.player)


@dataclass(frozen=True)
class HealOwnerPokemonThenDiscardHand(TrainerEffect):
    """v0.55: 自分の場の「(``owner``)のポケモン」を 1 匹選び、のっているダメージカウンターをすべてとりのぞく。その後、自分の手札をすべてトラッシュする（サカキの切り札）。

    - 選ぶのは使ったプレイヤー（``SELECT_POKEMON``。選べるものは ``owner_pokemon``（今の姿の名前が「サカキの」で始まる。v0.44 のトレーナー「サカキ」と同じ判定））。いなければ
      GL1、ダメージカウンターののっていないものは選べるが選ぶと GL2（どれもそうなら使う前に GL2）
    - とりのぞく（ログ ``remove_damage_counters``）→ 手札をすべてトラッシュ（``zones.discard_hand``。使っているこのカードは手札から出ているので含まない。手札が 0 枚なら
      トラッシュは 0 枚）。手札のトラッシュは「使うための条件」ではなく、とりのぞいたあとの効果（「その後」）
    """

    text: str
    owner: str = "サカキ"
    implementation_id = "heal_owner_pokemon_then_discard_hand"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = _require_text(definition, self.text, self)
        if not problems and (f"「{self.owner}のポケモン」を1匹選び、そのポケモンにのっているダメージカウンターを、すべてとりのぞく" not in self.text
                             or "その後、あなたの手札をすべてトラッシュする" not in self.text):
            problems.append("文面と登録の処理（ポケモンの名前・すべてとりのぞく・その後の手札のトラッシュ）が合わない")
        return problems

    def _targets(self, state: GameState, use: TrainerUse) -> list[int]:
        return owner_pokemon(state, use.player, self.owner)

    def _undamaged(self, state: GameState, use: TrainerUse) -> list[int]:
        return [pid for pid in self._targets(state, use) if state.find_pokemon(pid)[1].damage == 0]

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        targets = self._targets(state, use)
        if not targets:
            raise UnsupportedError(LAST_RESORT_WITHOUT_TARGET_CODE, LAST_RESORT_WITHOUT_TARGET_REASON)
        if len(self._undamaged(state, use)) == len(targets):
            raise UnsupportedError(LAST_RESORT_UNDAMAGED_CODE, f"{LAST_RESORT_UNDAMAGED_REASON}。どの「{self.owner}のポケモン」にもダメージカウンターがのっていない")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        push_trainer_decision(state, use, kind=SELECT_POKEMON, player=use.player, options=self._targets(state, use),
                              unresolved_choices=self._undamaged(state, use), unresolved_code=LAST_RESORT_UNDAMAGED_CODE, unresolved_reason=LAST_RESORT_UNDAMAGED_REASON)

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if choices[0] not in self._targets(state, use):
            raise RuntimeError(f"「{self.owner}の切り札」で選んだポケモン {choices} が、自分の場の「{self.owner}のポケモン」ではない（エンジンの不具合）")
        _, target = state.find_pokemon(choices[0])
        removed = target.damage // state.rules.damage_per_counter
        target.damage = 0
        state.add_event("remove_damage_counters", player=use.player, pokemon=target.card, pokemon_id=target.pokemon_id, counters=removed, total_damage=0,
                        trainer_card=use.card)
        discard_hand(state, use.player)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        return _select_own_pokemon_problems(decision, use, self._targets(state, use), f"「{self.owner}の切り札」", unresolved=self._undamaged(state, use))


@dataclass(frozen=True)
class MoveAllEnergyBetweenOwnerPokemon(TrainerEffect):
    """v0.55: 自分の場の「(``owner``)のポケモン」を 1 匹選び、ついているエネルギーカードをすべてはがし、自分の場の別の「(``owner``)のポケモン」1 匹につけなおす（ナツメ）。

    - 段階 1: はがすポケモン（``SELECT_POKEMON``。選べるものは ``owner_pokemon``（今の姿の名前。v0.44 と同じ判定））。エネルギーカードがついていないものは選べるが選ぶと SB2
      （どれもそうなら使う前に SB2）。「(``owner``)のポケモン」が 2 匹いなければ SB1（使う前）
    - 段階 2: つけなおすポケモン（``SELECT_POKEMON``。選べるものは段階 1 のポケモン以外の「(``owner``)のポケモン」。同じポケモンは選べない）
    - つけなおすのは、はがしたカードすべて（カードの種類・タイプを限らない。エナジートランスの「草」・ベンチだけなどの制限を持ち込まない）を 1 回で（``zones.move_attached_energy``。
      1 枚ずつの途中の状態を作らない）。手札からつける通常の操作の回数・特殊能力でつけた枚数は変えない。つけたあと、カードごとに、つけたときにはたらく特殊能力を評価する
      （``after_energy_attached``。ワザの効果のつけかえ（じりょくせん）と同じ。「つけなおす」）
    - エナジーバーン（v0.31）の「炎」は「そのポケモンについている間」（``GameState.energy_type_of``）なので、つけなおしたカードは印刷のタイプにもどる（今の対応カードでは、
      はがす「ナツメのポケモン」がエナジーバーンを使えないので起こらない）
    - はがして・つけなおして最大HPが下がる（［ガスのからだ］）答えは、のっているダメージ以下になれば MH1 で受け付けない（エンジンの ``max_hp_drops``。つけなおしたあとの状態で比べる）
    """

    text: str
    owner: str = "ナツメ"
    implementation_id = "move_all_energy_between_owner_pokemon"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = _require_text(definition, self.text, self)
        if not problems and (f"「{self.owner}のポケモン」を1匹選び、それについているエネルギーカードをすべてはがす" not in self.text
                             or f"別の「{self.owner}のポケモン」1匹につけなおす" not in self.text):
            problems.append("文面と登録の処理（ポケモンの名前・すべてはがす・別のポケモンにつけなおす）が合わない")
        return problems

    def _targets(self, state: GameState, use: TrainerUse) -> list[int]:
        return owner_pokemon(state, use.player, self.owner)

    def _empty(self, state: GameState, use: TrainerUse) -> list[int]:
        return [pid for pid in self._targets(state, use) if not state.find_pokemon(pid)[1].energy]

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        targets = self._targets(state, use)
        if len(targets) < 2:
            raise UnsupportedError(SABRINA_WITHOUT_TWO_CODE, f"{SABRINA_WITHOUT_TWO_REASON}。「{self.owner}のポケモン」は {len(targets)} 匹")
        if len(self._empty(state, use)) == len(targets):
            raise UnsupportedError(SABRINA_SOURCE_WITHOUT_ENERGY_CODE, f"{SABRINA_SOURCE_WITHOUT_ENERGY_REASON}。どの「{self.owner}のポケモン」にもエネルギーカードがついていない")

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        push_trainer_decision(state, use, kind=SELECT_POKEMON, player=use.player, options=self._targets(state, use), context=(("stage", 1),),
                              unresolved_choices=self._empty(state, use), unresolved_code=SABRINA_SOURCE_WITHOUT_ENERGY_CODE,
                              unresolved_reason=SABRINA_SOURCE_WITHOUT_ENERGY_REASON)

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if decision.context_value("stage") == 1:
            push_trainer_decision(state, use, kind=SELECT_POKEMON, player=use.player,
                                  options=[pid for pid in self._targets(state, use) if pid != choices[0]], context=(("stage", 2), ("source", choices[0])))
            return
        _, source = state.find_pokemon(decision.context_value("source"))
        _, target = state.find_pokemon(choices[0])
        for uid in move_attached_energy(state, use.player, source, target, trainer=use.card):
            after_energy_attached(state, use.player, target, uid)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        stage = decision.context_value("stage")
        what = f"「{self.owner}」"
        if stage == 1:
            return _select_own_pokemon_problems(decision, use, self._targets(state, use), what, unresolved=self._empty(state, use))
        source = decision.context_value("source")
        if stage != 2 or source not in self._targets(state, use):
            return [f"{what}の決定の段階 {stage!r}・はがすポケモン {source!r} が正しくない"]
        return _select_own_pokemon_problems(decision, use, [pid for pid in self._targets(state, use) if pid != source], what)


@dataclass(frozen=True)
class SwitchBothActivesTrainer(TrainerEffect):
    """v0.55: お互いの対戦ポケモンを、それぞれ、控えポケモンと入れ替える。入れ替わるポケモンは持ち主が選ぶ。入れ替えは相手プレイヤーが先。控えがいないプレイヤーは入れ替えを
    しない（ワープポイント）。

    - 段階 0: 相手プレイヤーが自分のベンチのポケモンを選び（決定 ``SELECT_POKEMON``。決めるのは相手プレイヤー。この相手の決定は、このカードの ``decision_problems`` だけが許す
      （ほかのトレーナーの、使ったプレイヤーが決める約束は変えない））、入れ替える。段階 1: 使ったプレイヤーが自分のベンチから選んで入れ替える
    - 入れ替えは、ポケモンいれかえ・突風と共通の ``_switch_active_with_bench``（特殊状態・持続する効果は理由 ``switch`` で消える。ログ ``switch`` の ``player`` は入れ替わる場の
      持ち主）。控えがいなければ入れ替えない（ログ ``trainer_switch_skipped``）。どちらにも控えがいなくても使える（説明が書いている。ポケモンいれかえの
      ``UNRESOLVED_SWITCH_WITHOUT_BENCH``・突風の GW5 を当てはめない）
    - SG1（v0.40）: 使ったプレイヤーの対戦ポケモンが「すごむ」を受けていて、その効果を与えたポケモンが相手のベンチにいるとき、相手がそれを選んでバトル場にもどすと SG1。ただし、
      使ったプレイヤーに控えがいれば、そのあと使ったプレイヤーの対戦ポケモンがベンチにもどって効果が消える（p.322）ので、問いにならない。使ったプレイヤーに控えがいない
      ときだけ、そのポケモンは選ぶと止める（選べるがどれもそうなら使う前に止める）
    - 入れ替えで決められない姿・最大HPの低下（TF1・TF2・MH1）になる答えは、エンジンが受け付けない（``engine._apply``・``_trainer_dead_end``）
    """

    text: str
    implementation_id = "switch_both_actives_trainer"

    def check(self, definition: CardDefinition) -> list[str]:
        problems = _require_text(definition, self.text, self)
        if not problems and ("入れ替わるポケモンは、それぞれ、持ち主が選ぶ" not in self.text or "相手プレイヤーが先におこなう" not in self.text
                             or "控えがいないプレイヤーは、入れ替えをしない" not in self.text):
            problems.append("文面と登録の処理（持ち主が選ぶ・相手が先・控えがいなければしない）が合わない")
        return problems

    @staticmethod
    def _switcher(use: TrainerUse, stage: int) -> int:
        return 1 - use.player if stage == 0 else use.player

    @staticmethod
    def _blocked(state: GameState, use: TrainerUse) -> tuple[int, ...]:
        """SG1: 相手のベンチの、選ぶと止めるポケモン（使ったプレイヤーに控えがいないときだけ）。"""
        return () if state.players[use.player].bench else _returning_lock_sources(state, use.player)

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        blocked = self._blocked(state, use)
        if blocked and len(blocked) == len(state.players[1 - use.player].bench):
            raise UnsupportedError("UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED", _ATTACK_LOCK_SOURCE_RETURNED_REASON)

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        self._offer(state, use, 0)

    def _offer(self, state: GameState, use: TrainerUse, stage: int) -> None:
        for current in range(stage, 2):
            player = self._switcher(use, current)
            bench = state.players[player].bench
            if bench:
                blocked = self._blocked(state, use) if current == 0 else ()
                push_trainer_decision(state, use, kind=SELECT_POKEMON, player=player, options=[p.pokemon_id for p in bench], context=(("stage", current),),
                                      unresolved_choices=blocked, unresolved_code="UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED",
                                      unresolved_reason=_ATTACK_LOCK_SOURCE_RETURNED_REASON)
                return
            state.add_event("trainer_switch_skipped", player=player, trainer_card=use.card)

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        stage = decision.context_value("stage")
        _switch_active_with_bench(state, self._switcher(use, stage), choices[0])
        if stage == 0:
            self._offer(state, use, 1)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        what = f"トレーナー {use.card_id}"
        stage = decision.context_value("stage")
        if stage not in (0, 1):
            return [f"{what}の決定の段階 {stage!r} が 0・1 ではない"]
        player = self._switcher(use, stage)
        problems = _decided_by(decision, player, what)
        bench = tuple(p.pokemon_id for p in state.players[player].bench)
        if decision.kind != SELECT_POKEMON or not bench or decision.options != bench or (decision.min_choices, decision.max_choices) != (1, 1):
            problems.append(f"{what}の段階 {stage} の決定 {decision.kind} {decision.options} が、プレイヤー {player} の控えポケモン {bench} から 1 匹ではない")
        blocked = self._blocked(state, use) if stage == 0 else ()
        if tuple(decision.context_value("unresolved_choices", ())) != tuple(blocked):
            problems.append(f"{what}の選ぶと止める選択 {decision.context_value('unresolved_choices', ())} が {blocked} ではない")
        events = _last_trainer_events(state, use)
        if stage == 1 and not any(e["kind"] in ("switch", "trainer_switch_skipped") and e["player"] == 1 - use.player for e in events):
            problems.append(f"{what}の使ったプレイヤーの決定が、相手プレイヤーの入れ替えのまえに出ている")
        return problems


# ---------------------------------------------------------------- 決められない姿の状態（TF1・TF2・DG1）

TRANSFORM_POWER_CODE = "UNRESOLVED_TRANSFORM_COPIED_POWER"
TRANSFORM_POWER_REASON = (
    "［へんしん］の「相手の対戦ポケモンと同じカードとしてあつかう」で、相手の対戦ポケモンのカードの特殊能力をこのカードも持つか（写した特殊能力を使える・はたらくか）は、"
    "kyuura の記録・印刷の文面から決められないので扱わない（TF1。英語版の「always has this Pokémon Power」は日本語版の処理の根拠にしない）"
)
TRANSFORM_TARGET_CODE = "UNRESOLVED_TRANSFORM_MODIFIED_DEFENDER"
TRANSFORM_TARGET_REASON = (
    "［へんしん］で同じカードとしてあつかう相手の対戦ポケモンが、「ばける」でのせたカードのポケモンとしてあつかわれている・ポケモンとして場に出したトレーナーカードである。"
    "同じにあつかうのが、いちばん上のカード・のせたカード・場での役割のどれかは、kyuura の記録・印刷の文面から決められないので扱わない（TF2）"
)


def _copied_power_needs_stop(effect: PowerEffect | None) -> bool:
    """写したカードの特殊能力のうち、使う宣言の前に止められないもの（常にはたらく・自動的にはたらく・きぜつするとき・きぜつしたときに使える）。場に出たときの特殊能力は、
    写すことで場に出るのではないので当たらない。宣言して使う特殊能力は、使うときに止める（``engine._use_pokemon_power``）。"""
    if effect is None:
        return True
    if isinstance(effect, EntryPower):
        return False
    return not effect.declared or isinstance(effect, (PreventKnockOutOnHeads, ReturnToHandOnKnockOut))


def form_problems(state: GameState) -> list[tuple[str, str]]:
    """今の状態の、決められない姿（v0.49。``engine._apply`` が、コマンドのあとに新しくできたら受け付けない。ポケモンチェック・対戦準備・答えのない決定は止める）。

    - TF1: ［へんしん］がはたらいているメタモンの相手の対戦ポケモンのカードに、常にはたらく・自動的にはたらく・きぜつするとき・きぜつしたときの特殊能力がある（写した
      特殊能力を持つかで、処理が続けて変わる）。宣言して使う特殊能力だけなら、この状態になってよい（使うときに止める）
    - TF2: ［へんしん］がはたらいているメタモンの相手の対戦ポケモンが、「ばける」でのせたカードのポケモンとしてあつかわれている・ポケモンとして出したトレーナーカード
    - DG1: 「ばける」でのせたカードのあるポケモンの「ばける」が、かがくへんかガスで消えている
    並びはプレイヤー 0 → 1、バトル場 → ベンチ。状態を変えず、乱数を使わない。"""
    from .continuous import suppressors_of  # continuous.py は effects.py を読み込むので、使うときに読み込む

    problems: list[tuple[str, str]] = []
    for owner, player in enumerate(state.players):
        for pokemon in player.in_play():
            if pokemon.disguise is not None:
                slot = shapeshift_slot(state, pokemon)
                if slot is not None and suppressors_of(state, slot.power):
                    problems.append((SHAPESHIFT_SUPPRESSED_CODE, f"プレイヤー {owner} のポケモン {pokemon.pokemon_id}（のせたカード {pokemon.disguise}）: {SHAPESHIFT_SUPPRESSED_REASON}"))
            defender = transform_defender(state, pokemon)
            if defender is None:
                continue
            where = f"プレイヤー {owner} のポケモン {pokemon.pokemon_id} の［へんしん］（相手の対戦ポケモン {defender.pokemon_id}）"
            if defender.disguise is not None or state.card_def(defender.card).play_role is not None:
                problems.append((TRANSFORM_TARGET_CODE, f"{where}: {TRANSFORM_TARGET_REASON}"))
                continue
            copied = [slot for slot in card_power_slots(state, defender.card) if _copied_power_needs_stop(slot.effect)]
            if copied:
                names = "・".join(slot.power.name_ja for slot in copied)
                problems.append((TRANSFORM_POWER_CODE, f"{where}・写す特殊能力［{names}］: {TRANSFORM_POWER_REASON}"))
    return problems


def state_stop_after(before: GameState, after: GameState) -> tuple[str, str] | None:
    """``before`` から ``after`` までの変化で、受け付けられない状態になったら、その (コード, 理由の文)（v0.49）。新しくできた決められない姿（``form_problems``）と、
    ダメージ以外の原因で最大HPがのっているダメージ以下に下がったポケモン（v0.48 の MH1。``max_hp_drops``）。どちらもなければ None。状態を変えない。"""
    known = set(form_problems(before))
    for problem in form_problems(after):
        if problem not in known:
            return problem
    drops = max_hp_drops(before, after)
    if drops:
        error = max_hp_drop_error(drops)
        return error.code, error.message
    return None


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
    "kyuura-engine-0.13",
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
        # ヒトカゲの「ひっかく」。v0.2a に p.63 で説明文がないことを確かめた（v0.29 までは参照カード）。
        # もう 1 つのワザ「ひのこ」は v0.30 で DiscardEnergyThenDamage として登録した（下。カードは対戦用になった）
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
        ("PMCG1-057", 0, "ちきゅうなげ"),  # カイリキー（v0.10。2 進化）p.192。「ワザ」欄は「●ちきゅうなげ」で説明文なし
        ("PMCG6-057", 0, "チョップ"),  # サカキのワンリキー（v0.11）p.189。「ワザ」欄は「●チョップ」で説明文なし
        ("PMCG4-018", 0, "こうらアタック"),  # 第4弾のゼニガメ（v0.13）p.88。「ワザ」欄は「●こうらアタック」で説明文なし
        ("PMCG6-063", 1, "ねこキック"),  # サカキのニャース（v0.17a）p.229。「ワザ」欄は「●ねこキック」で説明文なし
        # ストライク（v0.27）p.56。「ワザ」欄は「●きりさく」で説明文なし。「つるぎのまい」の効果がはたらく番は、p.321 の 2 段階で 60 になる
        # （ダメージを変えるのは「つるぎのまい」の持続する効果。この登録は変えない）
        ("PMCG2-017", 1, "きりさく"),
        # v0.28: 既存の効果の型の登録だけで加えたポケモン（docs/existing-effect-pokemon-v0.28.md）。どれも「ワザ」欄はワザ名だけで説明文なし
        ("PMCG2-021", 0, "つのでつく"),  # トサキント p.108
        ("PMCG2-022", 0, "つのでつく"),  # アズマオウ（トサキントから進化）p.109。解説「トサキント（ジャングル）が使っているワザとまったく同じ」
        ("PMCG2-022", 1, "たきのぼり"),
        ("PMCG2-018", 1, "ハサミギロチン"),  # カイロス p.58
        ("PMCG2-035", 1, "はたく"),  # プリン p.225（kyuura の notes のとおり 2 つめは「はたく」）
        ("PMCG1-045", 0, "はたく"),  # スリープ p.164
        # v0.29: 既存の効果の型の登録だけで加えたポケモン（kyuura データの採用。docs/existing-effect-pokemon-v0.29.md。記録は
        # card_sources.json）。どれも kyuura の写しで説明文がなく、pcg-search.com の同じ版のページでも説明文がない
        ("PMCG4-001", 0, "かみつく"),  # アーボ（ロケット団）
        ("PMCG4-002", 0, "ぶつかる"),  # ズバット（ロケット団）
        ("PMCG4-002", 1, "かみつく"),
        ("PMCG4-005", 0, "たいあたり"),  # ドガース（ロケット団）
        ("PMCG4-027", 0, "スピードボール"),  # ビリリダマ（ロケット団）
        ("PMCG4-040", 0, "パンチ"),  # ワンリキー（ロケット団）
        ("PMCG4-040", 1, "キック"),
        ("PMCG5-001", 0, "つばさでうつ"),  # タケシのズバット
        ("PMCG5-037", 1, "たいあたり"),  # マチスのコイル
        ("PMCG5-061", 0, "ベロではたく"),  # タケシのベロリンガ
        # v0.30: エネルギーをトラッシュしてダメージを与えるワザの共通の型で加えたポケモンの、説明文のないワザ（kyuura データの採用。
        # docs/discard-energy-attacks-v0.30.md。pcg-search.com の同じ版のページでも説明文がない）
        ("PMCG1-017", 0, "きりさく"),  # リザード（第1弾）。ストライク・パラセクトの「きりさく」とは別のカードのワザ
        ("PMCG1-020", 0, "ほのおパンチ"),  # ブーバー（第1弾）
        # v0.31: 保留していた 22 枚のうち、説明文のないワザ（kyuura データの採用。docs/held-cards-v0.31.md）
        ("PMCG4-014", 0, "うしろげり"),  # わるいギャロップ
        ("PMCG4-015", 0, "しっぽでたたく"),  # わるいリザード
        ("PMCG4-017", 0, "つめではじく"),  # わるいリザードン
        ("PMCG4-022", 1, "ちょうねんりき"),  # わるいゴルダック
        ("PMCG4-028", 0, "ころがりタックル"),  # わるいマルマイン
        ("PMCG6-025", 1, "きりさく"),  # カツラのヒトカゲ
        ("PMCG6-029", 0, "ほのおのつめ"),  # カツラのリザード
        # v0.32: 山札からベンチに出す・ダメージカウンターでダメージが決まる・与えたぶん回復するワザのポケモンと進化先のうち、説明文のないワザ（kyuura
        # データの採用。docs/bench-search-counter-drain-v0.32.md。pcg-search.com の同じ版のページでも説明文がない）
        ("PMCG2-005", 0, "つるのムチ"),  # マダツボミ（第2弾）
        ("PMCG3-013", 1, "はさむ"),  # クラブ（化石の秘密）
        ("PMCG2-011", 1, "はっぱカッター"),  # ウツドン（第2弾）
        ("PMCG1-031", 0, "たいあたり"),  # コイキング（第1弾）
        ("PMCG1-034", 0, "りゅうのいかり"),  # ギャラドス（第1弾）
        ("PMCG3-019", 1, "クラブハンマー"),  # キングラー（化石の秘密）
        ("PMCG3-005", 0, "つばさでうつ"),  # ゴルバット（化石の秘密）。タケシのズバットの「つばさでうつ」とは別のカードのワザ
        # v0.33: 相手のエネルギーカードをトラッシュする・コインで失敗する／ダメージを与えられない・控えにもダメージを与えるワザのポケモンと進化先のうち、
        # 説明文のないワザ（kyuura データの採用。docs/cd4-opponent-energy-coins-v0.33.md。pcg-search.com の同じ版のページでも説明文がない）
        ("PMCG4-023", 0, "かみつく"),  # わるいシャワーズ（ロケット団）
        ("PMCG1-010", 1, "つのドリル"),  # ニドリーノ（第1弾）
        ("PMCG4-046", 0, "かじる"),  # わるいラッタ（ロケット団）
        # v0.34: 説明文のないワザ（kyuura データの採用。docs/barrier-resume-coin-bonus-v0.34.md。pcg-search.com の同じ版のページでも説明文がない）
        ("PMCG5-018", 0, "ほのお"),  # タケシのロコン（リーダーズスタジアム。第1弾のロコン・カツラのロコンとは別の名前のカード）
        # v0.36: 説明文のないワザ（kyuura データの採用。docs/sand-attack-retreat-lock-v0.36.md。pcg-search.com の同じ版のページでも説明文がない）
        ("PMCG3-036", 0, "きりさく"),  # サンドパン（化石の秘密）
        ("PMCG5-025", 0, "たいあたり"),  # カスミのタッツー（リーダーズスタジアム）
        ("PMCG6-062", 0, "つつく"),  # キョウのポッポ（闇からの挑戦）
        # v0.37: 説明文のないワザ（kyuura データの採用。docs/fifteen-reused-effects-v0.37.md。pcg-search.com の同じ版のページでも説明文がない）
        ("PMCG2-030", 1, "つのでつく"),  # サイホーン（第2弾）
        ("PMCG4-049", 0, "たいあたり"),  # イーブイ（ロケット団。第2弾のイーブイ PMCG2-037 とは別のカード）
        ("PMCG6-045", 1, "ずつき"),  # ナツメのスリープ（闇からの挑戦）
        ("PMCG1-056", 0, "きりさく"),  # ダグトリオ（第1弾）
        ("PMCG5-048", 1, "いわおとし"),  # タケシのイワーク（リーダーズスタジアム）
        ("PMCG5-028", 1, "はねる"),  # カスミのコイキング（リーダーズスタジアム。第1弾のコイキング PMCG1-031 とは別の名前のカード）
        ("PMCG2-039", 0, "ひっかく"),  # ペルシアン（第2弾）
        # v0.38: 説明文のないワザ（kyuura データの採用。docs/bench-switch-combined-v0.38.md。pcg-search.com の同じ版のページでも説明文がない）
        ("PMCG3-039", 1, "とびひざげり"),  # サワムラー（化石の秘密）
        ("PMCG5-006", 0, "つるでうつ"),  # エリカのモンジャラ（リーダーズスタジアム。第1弾のモンジャラ・キョウのモンジャラとは別の名前のカード）
        ("PMCG5-008", 0, "スピードひこう"),  # タケシのゴルバット（リーダーズスタジアム。化石の秘密のゴルバットとは別の名前のカード）
        ("PMCG2-033", 0, "つのでつく"),  # サイドン（第2弾）
        ("PMCG6-030", 0, "ほのおのたてがみ"),  # カツラのギャロップ（闇からの挑戦。第2弾のギャロップとは別の名前のカード）
        ("PMCG6-001", 0, "チクチクさす"),  # キョウのビードル（闇からの挑戦。第1弾のビードルとは別の名前のカード）
        ("PMCG6-066", 0, "とがる"),  # ナツメのポリゴン（闇からの挑戦）
        ("PMCG6-067", 1, "つばさでうつ"),  # キョウのポッポ（闇からの挑戦。キョウのポッポ PMCG6-062 とは同じ名前の別のカード）
        # v0.39: 説明文のないワザ（kyuura データの採用。docs/selfdestruct-spread-count-v0.39.md。pcg-search.com の同じ版のページでも説明文がない）
        ("PMCG2-025", 0, "たいあたり"),  # マルマイン（第2弾）
        ("PMCG4-026", 0, "たいあたり"),  # コイル（ロケット団。第1弾のコイル PMCG1-036 とは同じ名前の別のカード）
        ("PMCG2-013", 1, "メガトンパンチ"),  # ニドクイン（第2弾）
        ("PMCG5-004", 0, "はさむ"),  # エリカのパラス（リーダーズスタジアム。第2弾のパラス PMCG2-003 とは別の名前のカード）
        # v0.40: 説明文のないワザ（kyuura データの採用。docs/count-condition-switch-return-v0.40.md。pcg-search.com の同じ版のページでも説明文がない）
        ("PMCG6-014", 0, "かみつく"),  # キョウのゴルバット（闇からの挑戦。キョウのズバットから進化）
        ("PMCG4-037", 0, "サイコパンチ"),  # わるいスリーパー（ロケット団）
        ("PMCG6-020", 0, "メガトンキック"),  # サカキのニドクイン（闇からの挑戦）
        ("PMCG4-044", 0, "メガトンパンチ"),  # わるいカイリキー（ロケット団）
        ("PMCG5-011", 0, "よだれ"),  # エリカのウツドン（リーダーズスタジアム）
        ("PMCG5-034", 0, "しっぽのムチ"),  # カスミのシードラ（リーダーズスタジアム）
        # v0.41: 説明文のないワザ（kyuura データの採用。docs/heal-counter-status-v0.41.md。pcg-search.com の同じ版のページでも説明文がない）
        ("PMCG4-032", 1, "ずつき"),  # ヤドン（ロケット団。化石の秘密のヤドン PMCG3-028・ナツメのヤドン PMCG6-044 とは別のカード）
        ("PMCG6-036", 0, "ひっかく"),  # ナツメのコダック（闇からの挑戦）
        ("PMCG6-055", 2, "サイコバーン"),  # R団のミュウツー（闇からの挑戦。第1弾のミュウツー PMCG1-050 とは別の名前のカード）
        # v0.42: 説明文のないワザ（kyuura データの採用。docs/power-decisions-v0.42.md。pcg-search.com の同じ版のページでも説明文がない）
        ("PMCG6-047", 1, "サイコショット"),  # ナツメのユンゲラー（闇からの挑戦。第1弾のユンゲラー・わるいユンゲラーとは別の名前のカード）
        ("PMCG5-015", 0, "はっぱカッター"),  # エリカのウツボット（リーダーズスタジアム。第2弾のウツボットとは別の名前のカード）
        ("PMCG3-011", 0, "ようかいえき"),  # メノクラゲ（化石の秘密。ウツボットの「ようかいえき」とは別のワザ（説明文なし））
        ("PMCG5-060", 1, "ムーンキック"),  # エリカのピッピ（リーダーズスタジアム）
        ("PMCG5-065", 1, "ムーンインパクト"),  # エリカのピクシー（リーダーズスタジアム）
        # v0.43: 説明文のないワザ（kyuura データの採用。docs/declared-entry-powers-v0.43.md。pcg-search.com の同じ版のページでも説明文がない）
        ("PMCG4-012", 0, "ほのおのしっぽ"),  # ヒトカゲ（ロケット団。第1弾のヒトカゲ PMCG1-014 とは同じ名前の別のカード）
        # v0.44: 説明文のないワザ（kyuura データの採用。docs/search-evolution-once-attacks-v0.44.md。pcg-search.com の同じ版のページでも説明文がない）
        ("PMCG4-038", 1, "ひっかく"),  # ディグダ（ロケット団。第1弾のディグダ PMCG1-052 とは同じ名前の別のカード）
        ("PMCG4-020", 0, "はねまわる"),  # コイキング（ロケット団。第1弾のコイキング PMCG1-031 とは同じ名前の別のカード）
        ("PMCG1-063", 1, "ナベでたたく"),  # カモネギ（第1弾）
        ("PMCG6-046", 1, "ビンタ"),  # ナツメのバリヤード（闇からの挑戦）
        # v0.45: 説明文のないワザ（kyuura データの採用。docs/conditional-damage-energy-v0.45.md。pcg-search.com の同じ版のページでも説明文がない）
        ("PMCG6-007", 1, "ヘドロなげ"),  # キョウのベトベター（闇からの挑戦）
        ("PMCG1-054", 0, "いわおとし"),  # イワーク（第1弾。タケシのイワーク PMCG5-048 とは別のカード）
        ("PMCG1-062", 0, "かみつく"),  # ラッタ（第1弾）
        ("PMCG5-054", 1, "マグナムパンチ"),  # R団のエビワラー（リーダーズスタジアム）
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
        # ロケット団のベトベター（v0.8。たね）p.45。どくガス（草。ダメージの目安なし）: コインを投げずに相手をどく状態に
        AttackKey("PMCG4-004", 0): AttackEntry(
            PoisonWithoutDamage(),
            "どくガス",
            text_ja="相手を「どく」状態にする。",
            play_text_ja="相手を「どく」状態にする。",
            source="P43 p.45",
        ),
        # ねばりつく（草草。10+）: コインが「おもて」なら 20 を追加して（30）、相手をマヒ状態に。「うら」なら 10
        AttackKey("PMCG4-004", 1): AttackEntry(
            CoinBonusDamageAndParalyze(bonus=20),
            "ねばりつく",
            text_ja="コインを投げて「おもて」なら、20ダメージを追加して、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージを追加して、相手を「マヒ」状態にする。",
            source="P43 p.45",
        ),
        # ベトベトン（v0.8。1 進化）p.48。ヘドロこうげき（草草草）: 相手に 30（目安の数字）、コインが「おもて」なら相手をどく状態に
        AttackKey("PMCG3-007", 0): AttackEntry(
            PoisonOnHeads(),
            "ヘドロこうげき",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            source="P43 p.48",
        ),
        # 化石の秘密のゴース（v0.9。たね）p.158。したでなめる（超）: 相手に 10（目安の数字）、コインが「おもて」なら相手をマヒ状態に
        AttackKey("PMCG3-029", 0): AttackEntry(
            ParalyzeOnHeads(),
            "したでなめる",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source="P43 p.158",
        ),
        # エナジーへんかん（超超。目安なし）: トラッシュのエネルギーカードを最大 2 枚手札に加え、そのあと自分に 10
        AttackKey("PMCG3-029", 1): AttackEntry(
            RecoverEnergyAndSelfDamage(max_cards=2, self_damage=10),
            "エナジーへんかん",
            text_ja="自分のトラッシュから最大2枚のエネルギーカードを選び、手札に加える。その後、自分に10ダメージ。",
            play_text_ja="自分のトラッシュから、「エネルギーカード」を最大2枚選び出し、手札に加える。その後、自分に10ダメージ。",
            source="P43 p.158",
        ),
        # 化石の秘密のゴースト（v0.9。1 進化）p.160。あくむ（超無）: 相手に 10（目安の数字）、コインを投げずに相手をねむり状態に
        AttackKey("PMCG3-030", 0): AttackEntry(
            SleepOpponent(),
            "あくむ",
            text_ja="相手を「ねむり」状態にする。",
            play_text_ja="相手を「ねむり」状態にする。",
            source="P43 p.160",
        ),
        # ゴーリキー（v0.10。ワンリキーから進化）p.190。からてチョップ（闘闘無。50−）: 目安の数字から、自分にのっているダメージカウンター
        # 1 個につき 10 を引いた数が基本となるダメージ。印刷の文面（kyuura の写し）は「自分のダメージカウンター×10だけ、相手にあたえる
        # ダメージがへる。」（docs/machamp-line-v0.10.md）
        AttackKey("PMCG1-055", 0): AttackEntry(
            DamageReducedByOwnCounters(reduction_per_counter=10),
            "からてチョップ",
            text_ja="自分のダメージカウンター×10だけ、相手にあたえるダメージがへる。",
            play_text_ja="このワザのダメージは、自分にのっているダメージカウンターの数×10だけ、小さくなる。",
            source="P43 p.190",
        ),
        # じごくぐるま（闘闘無無。60）: 相手に 60（目安の数字）、そのあと自分にも 20
        AttackKey("PMCG1-055", 1): AttackEntry(
            DamageAndSelfDamage(self_damage=20),
            "じごくぐるま",
            text_ja="自分にも20ダメージ。",
            play_text_ja="自分にも20ダメージ。",
            source="P43 p.190",
        ),
        # サカキのワンリキー（v0.11）p.189。いかりのスーパーパンチ（闘闘。20×）: コインが「おもて」なら、自分にのっているダメージカウンター
        # の数 × 20 が基本となるダメージ（「うら」なら 0）。docs/giovanni-machamp-line-v0.11.md
        AttackKey("PMCG6-057", 1): AttackEntry(
            CoinHeadsDamagePerOwnCounter(damage_per_counter=20),
            "いかりのスーパーパンチ",
            text_ja="コインを投げて「おもて」なら、自分にのっているダメージカウンターの数×20のダメージ。",
            play_text_ja="コインを投げて「おもて」なら、自分にのっているダメージカウンターの数×20のダメージ。",
            source="P43 p.189",
        ),
        # サカキのゴーリキー（v0.11。サカキのワンリキーから進化）p.191。いちかばちか（闘。60）: コインが「おもて」なら相手に 60（目安の数字）、
        # 「うら」なら相手にはダメージを与えず、自分に 100
        AttackKey("PMCG6-059", 0): AttackEntry(
            SelfDamageInsteadOnTails(self_damage=100),
            "いちかばちか",
            text_ja="コインを投げて「うら」なら、相手にはダメージを与えず、自分に100ダメージ。",
            play_text_ja="コインを投げて「うら」なら、相手にはダメージを与えず、自分に100ダメージ。",
            source="P43 p.191",
        ),
        # じごくがため（闘闘無。20+）: ロケット団のベトベターの「ねばりつく」（v0.8）と同じ説明。「おもて」なら 20 + 20 で相手をマヒ状態に
        AttackKey("PMCG6-059", 1): AttackEntry(
            CoinBonusDamageAndParalyze(bonus=20),
            "じごくがため",
            text_ja="コインを投げて「おもて」なら、20ダメージを追加して、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージを追加して、相手を「マヒ」状態にする。",
            source="P43 p.191",
        ),
        # サカキのカイリキー（v0.11。サカキのゴーリキーから進化）p.193。ハリケーンパンチ（闘闘闘無。30×）: コイン 4 枚の「おもて」の数 × 30
        AttackKey("PMCG6-061", 0): AttackEntry(
            CoinFlipDamage(coins=4, damage_per_heads=30),
            "ハリケーンパンチ",
            text_ja="コインを4枚投げ、「おもて」の数×30のダメージ。",
            play_text_ja="コインを4枚投げ、「おもて」の数×30のダメージ。",
            source="P43 p.193",
        ),
        # R団のファイヤー（v0.12。たね）p.82。ほのおのかべ（炎炎炎。40）: 相手に 40。そのあと、次の相手の番、このカードが相手のワザによる
        # ダメージを受けたとき、相手に 10 ダメージを与える（持続する効果。p.89 のワザ解説の「相手の番ではたらく効果」）。印刷の文面（kyuura の
        # 写し）は「…受けた時、(このカードが「きぜつ」するしないにかかわらず)相手にも10ダメージ。」（docs/rocket-moltres-v0.12.md）
        AttackKey("PMCG5-020", 0): AttackEntry(
            DamageAndRetaliation(retaliation=10),
            "ほのおのかべ",
            text_ja="次の相手の番、このカードが相手のワザによるダメージを受けた時、(このカードが「きぜつ」するしないにかかわらず)相手にも10ダメージ。",
            play_text_ja="次の相手の番、このカードが相手のワザによるダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）相手に10ダメージを与える。",
            source="P43 p.82",
        ),
        # わるいカメール（v0.13。ゼニガメから進化）p.89。おうふくびんた（水。10×）: コイン 2 枚の「おもて」の数 × 10（ドードーの「みだれづき」と
        # 同じ説明。印刷の文面（kyuura の写し）は「…投げて…」）
        AttackKey("PMCG4-021", 0): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=10),
            "おうふくびんた",
            text_ja="コインを2枚投げて「おもて」の数×10のダメージ。",
            play_text_ja="コインを2枚投げ、「おもて」の数×10のダメージ。",
            source="P43 p.89",
        ),
        # こうらがえし（水無。ダメージなし）: 次の相手の番、このカードが相手のワザによってダメージを受けたとき、そのポケモンにも同じダメージを
        # 与える（持続する効果。受けたダメージで量が決まる。p.89 のワザ解説の「相手の番ではたらく効果」。docs/shell-attack-v0.13.md）。印刷の
        # 文面（kyuura の写し）は「次の相手の番で、…受けた時、(このカードが「きぜつ」するしないにかかわらず、)…」
        AttackKey("PMCG4-021", 1): AttackEntry(
            ReturnReceivedDamage(),
            "こうらがえし",
            text_ja="次の相手の番で、このカードが相手のワザによってダメージを受けた時、(このカードが「きぜつ」するしないにかかわらず、)そのポケモンにも同じダメージを与える。(ダメージ以外の効果は与えない)",
            play_text_ja="次の相手の番、このカードが相手のワザによってダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）そのポケモンにも同じダメージを与える。（ダメージ以外の効果は与えない）",
            source="P43 p.89",
        ),
        # モンジャラ（v0.17a）p.55。既存の実装だけで登録（docs/card-implementation-v0.17a.md）。しめつける（草無）: 相手に 20（目安の
        # 数字）、コインが「おもて」なら相手をマヒ状態に（ParalyzeOnHeads。マヒの再付与の確認・T19b の確認も同じ）。どくのこな（草草草）:
        # 相手に 20、コインなしで相手をどく状態に（PoisonOpponent）。最新の説明は kyuura の写しと同じ
        AttackKey("PMCG1-007", 0): AttackEntry(
            ParalyzeOnHeads(),
            "しめつける",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source="P43 p.55",
        ),
        AttackKey("PMCG1-007", 1): AttackEntry(
            PoisonOpponent(),
            "どくのこな",
            text_ja="相手を「どく」状態にする。",
            play_text_ja="相手を「どく」状態にする。",
            source="P43 p.55",
        ),
        # サカキのニャース（v0.17a）p.229。ねこノミ（無。ダメージの目安なし）: コインが「おもて」なら相手をこんらん状態に
        # （ConfuseOnHeadsWithoutDamage。既存の要素 Status の新しい並び）。最新の説明は kyuura の写しと同じ
        AttackKey("PMCG6-063", 0): AttackEntry(
            ConfuseOnHeadsWithoutDamage(),
            "ねこノミ",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            source="P43 p.229",
        ),
        # R団のカビゴン（v0.17b）p.245。たおれこむ（無無無）20: ダメージを与えた後、自分をねむり状態に（DamageAndSelfSleep）。印刷の文面（kyuura の
        # 写し）は「ダメージを与えたあと、…」（docs/rocket-snorlax-v0.17b.md）
        AttackKey("PMCG6-073", 0): AttackEntry(
            DamageAndSelfSleep(),
            "たおれこむ",
            text_ja="ダメージを与えたあと、自分を「ねむり」状態にする。",
            play_text_ja="ダメージを与えた後、自分を「ねむり」状態にする。",
            source="P43 p.245",
        ),
        # ナツメのヤドン（v0.18c）p.155。ぐうたらこうげき（超無）30: たおれこむと同じ説明（最新の説明・kyuura の写しとも「ダメージを与えた後、…」）。
        # 既存の DamageAndSelfSleep で処理する（新しい要素・型・分岐はない）。ダメージを与えなかったときは Z23 で止める（docs/kernel-reuse-v0.18c.md）
        AttackKey("PMCG6-044", 0): AttackEntry(
            DamageAndSelfSleep(),
            "ぐうたらこうげき",
            text_ja="ダメージを与えた後、自分を「ねむり」状態にする。",
            play_text_ja="ダメージを与えた後、自分を「ねむり」状態にする。",
            source="P43 p.155",
        ),
        # ストライク（v0.27）p.56。つるぎのまい（草。ダメージの目安なし）: 自分に「次の自分の番、このカードが使う「きりさく」（1 番目のワザ）の
        # ダメージは「60」になる」持続する効果（SetNextTurnAttackDamage。p.321 の 2 段階）。印刷の文面（kyuura の写し）は「次の自分の番だけ、…
        # ダメージは2倍になる。」で、最新の説明と書き方・内容の表し方が違う（「2倍」で処理しない。docs/scyther-v0.27.md）
        AttackKey("PMCG2-017", 0): AttackEntry(
            SetNextTurnAttackDamage(target_attack_index=1, target_attack_name="きりさく", damage=60),
            "つるぎのまい",
            text_ja="次の自分の番だけ、このカードが使う「きりさく」のダメージは2倍になる。",
            play_text_ja="次の自分の番、このカードが使う「きりさく」のダメージは「60」になる。",
            source="P43 p.56",
        ),
        # v0.28: 既存の効果の型の登録だけで加えたポケモン（docs/existing-effect-pokemon-v0.28.md。照合の記録は card_verification.json）。
        # ラプラス（化石の秘密）p.116。みずでっぽう（水。10+）: カメックスの「ハイドロポンプ」（p.90）と同じ最新の説明。必要なエネルギーは「水」1 個
        # だけなので、多い「水」エネルギーの数え方が決まる（ExtraEnergyDamage の check）。印刷の文面（kyuura の写し）は照合用
        AttackKey("PMCG3-022", 0): AttackEntry(
            ExtraEnergyDamage(energy_type=EnergyType.WATER, per_energy=10, max_extra=2),
            "みずでっぽう",
            text_ja="ワザに必要なぶんよりも多く「水」エネルギーがついている時、多いエネルギー1つにつき10ダメージを追加する。(ダメージ追加は2つぶんまで)",
            play_text_ja="ワザに必要なエネルギーよりも多く「水」エネルギーがついているとき、多い「水」エネルギー1個につき、10ダメージを追加する。ダメージ追加は2個ぶんまで。",
            source="P43 p.116",
        ),
        # ラプラス p.116。あやしいひかり（水水）10: ロコンの「あやしいひかり」（p.67）と同じ最新の説明
        AttackKey("PMCG3-022", 1): AttackEntry(
            ConfuseOnHeads(),
            "あやしいひかり",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            source="P43 p.116",
        ),
        # スターミー（ヒトデマンから進化）p.112。じこさいせい（水水。ダメージの目安なし）: ユンゲラーの「じこさいせい」（p.151）と同じ最新の説明で、
        # エネルギーの種類だけ「水」（解説「たった1枚の水エネルギーカードをトラッシュするだけで…全部回復できる」）
        AttackKey("PMCG1-026", 0): AttackEntry(
            DiscardEnergyAndRemoveAllCounters(energy_type=EnergyType.WATER),
            "じこさいせい",
            text_ja="自分の「水」エネルギーカードを1枚はがしてすてることによってダメージカウンターを全てとりのぞく。",
            play_text_ja="自分についている「水」エネルギーカードを1枚トラッシュして、自分にのっているダメージカウンターを、すべてとりのぞく。トラッシュできないとき、このワザの効果はなくなる。",
            source="P43 p.112",
        ),
        # スターミー p.112。スターフリーズ（水無無）20: キャタピーの「いとをはく」（p.17）と同じ最新の説明
        AttackKey("PMCG1-026", 1): AttackEntry(
            ParalyzeOnHeads(),
            "スターフリーズ",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source="P43 p.112",
        ),
        # カイロス p.58。まんりきばさみ（草草）20: コインが「おもて」なら相手をマヒ状態に
        AttackKey("PMCG2-018", 0): AttackEntry(
            ParalyzeOnHeads(),
            "まんりきばさみ",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source="P43 p.58",
        ),
        # タマタマ p.49。さいみんじゅつ（超。ダメージの目安なし）: パラスの「キノコのほうし」（p.38）と同じ最新の説明
        AttackKey("PMCG2-006", 0): AttackEntry(
            PutToSleep(),
            "さいみんじゅつ",
            text_ja="相手を「ねむり」状態にする。",
            play_text_ja="相手を「ねむり」状態にする。",
            source="P43 p.49",
        ),
        # タマタマ p.49。やどりぎのタネ（草草）20: フシギダネの「やどりぎのタネ」（p.13）と同じ最新の説明。図版・「ワザ」欄・解説の名前は
        # ひらがなの「やどりぎのたね」（kyuura の写しは「やどりぎのタネ」。表記の食い違い。登録の照合は kyuura の写しの値。PMCG1-008 と同じ扱い）
        AttackKey("PMCG2-006", 1): AttackEntry(
            DamageAndRemoveCounters(counters=1),
            "やどりぎのタネ",
            text_ja="相手にダメージを与えたら、自分のダメージカウンターを1つとりのぞく。",
            play_text_ja="相手にダメージを与えたら、自分にのっているダメージカウンターを1個とりのぞく。",
            source="P43 p.49",
        ),
        # プリン p.225。こもりうた（無。ダメージの目安なし）: 相手をねむり状態に
        AttackKey("PMCG2-035", 0): AttackEntry(
            PutToSleep(),
            "こもりうた",
            text_ja="相手を「ねむり」状態にする。",
            play_text_ja="相手を「ねむり」状態にする。",
            source="P43 p.225",
        ),
        # ラッキー p.235。まるまる（無無。ダメージの目安なし）: トランセル・コクーンの「かたまる」（p.18・p.21）と同じ最新の説明（印刷の文面
        # 「…うけるダメージが0になる。」にはしたがわない）。p.322 の「「ラッキー」の「まるまる」などのようなワザは、自分自身に「持続する効果」を与えます」
        AttackKey("PMCG1-068", 0): AttackEntry(
            PreventDamageOnHeads(),
            "まるまる",
            text_ja="コインを投げて「おもて」なら、次の相手の番にうけるダメージが0になる。",
            play_text_ja="コインを投げて「おもて」なら、次の相手の番、このカードはダメージを受けない。（ダメージ以外の効果は受ける）",
            source="P43 p.235",
        ),
        # ラッキー p.235。すてみタックル（無無無無）80: 相手に 80、そのあと自分にも 80（ゴーリキーの「じごくぐるま」（p.190）と同じ形。解説「この
        # 「ラッキー」自身も80ダメージ受けてしまいます」）
        AttackKey("PMCG1-068", 1): AttackEntry(
            DamageAndSelfDamage(self_damage=80),
            "すてみタックル",
            text_ja="自分にも80ダメージ。",
            play_text_ja="自分にも80ダメージ。",
            source="P43 p.235",
        ),
        # スリープ p.164。あやしいひかり（超超）10: ロコンの「あやしいひかり」（p.67）と同じ最新の説明
        AttackKey("PMCG1-045", 1): AttackEntry(
            ConfuseOnHeads(),
            "あやしいひかり",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            source="P43 p.164",
        ),
        # シェルダー（化石の秘密）p.103。ちょうおんぱ（水。ダメージの目安なし）: サカキのニャースの「ねこノミ」（p.229）と同じ最新の説明
        AttackKey("PMCG3-012", 0): AttackEntry(
            ConfuseOnHeadsWithoutDamage(),
            "ちょうおんぱ",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            source="P43 p.103",
        ),
        # シェルダー p.103。からをとじる（水。ダメージの目安なし）: 「かたまる」と同じ最新の説明（印刷の文面「…受けるダメージは0になる。（ダメージ
        # 以外の効果はそのまま）」にはしたがわない）
        AttackKey("PMCG3-012", 1): AttackEntry(
            PreventDamageOnHeads(),
            "からをとじる",
            text_ja="コインを投げて「おもて」なら、次の相手の番にこのカードが受けるダメージは0になる。(ダメージ以外の効果はそのまま)",
            play_text_ja="コインを投げて「おもて」なら、次の相手の番、このカードはダメージを受けない。（ダメージ以外の効果は受ける）",
            source="P43 p.103",
        ),
        # v0.29: 既存の効果の型の登録だけで加えたポケモン（kyuura データの採用。docs/existing-effect-pokemon-v0.29.md・docs/card-data-policy.md）。
        # kyuura の研究の基準のコミットに、どのカードの最新の説明（LD-）・エラッタ・裁定もないので、処理に使う文面は kyuura の印刷の文面
        # （play_text_ja = text_ja。出典 _KYUURA_PRINTED_TEXT）。型とパラメーターは、既存の登録の同じ文面・同じ形のワザと同じ
        # ニョロモ（第1弾）。みずでっぽう（水。10+）: 印刷の文面はカメックスの「ハイドロポンプ」と同じ。kyuura は同じ文面を LD-PMCG1-032-ATK0 で
        # 「何に対して追加したエネルギーを数えるかを書かない」とし、ニョロモのイントロパック（ゼニガメデッキ）の版の文面「ワザに必要なエネルギー
        # よりも多く…」との違いを「書き方だけ」と分類している（docs/cards/reprints.md）。必要なエネルギーは「水」1 個だけ
        AttackKey("PMCG1-024", 0): AttackEntry(
            ExtraEnergyDamage(energy_type=EnergyType.WATER, per_energy=10, max_extra=2),
            "みずでっぽう",
            text_ja="「水」エネルギーを1つ追加すると、10ダメージ追加できる。(追加は2つまで)",
            play_text_ja="「水」エネルギーを1つ追加すると、10ダメージ追加できる。(追加は2つまで)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # アーボ（ロケット団）。どくばり（草草）20: ビードルの「どくばり」と同じ文面
        AttackKey("PMCG4-001", 1): AttackEntry(
            PoisonOnHeads(),
            "どくばり",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナゾノクサ（ロケット団）。ねむりごな（草。ダメージの目安なし）: パラスの「キノコのほうし」と同じ文面
        AttackKey("PMCG4-003", 0): AttackEntry(
            PutToSleep(),
            "ねむりごな",
            text_ja="相手を「ねむり」状態にする。",
            play_text_ja="相手を「ねむり」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナゾノクサ。どくのこな（草。ダメージの目安なし）: ロケット団のベトベターの「どくガス」と同じ文面（ダメージの目安のある「どくのこな」の
        # PoisonOpponent とは別）
        AttackKey("PMCG4-003", 1): AttackEntry(
            PoisonWithoutDamage(),
            "どくのこな",
            text_ja="相手を「どく」状態にする。",
            play_text_ja="相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ドガース（ロケット団）。どくガス（草無）20: コインを投げる（ダメージの目安のない、ロケット団のベトベターの「どくガス」とは別の文面）
        AttackKey("PMCG4-005", 1): AttackEntry(
            PoisonOnHeads(),
            "どくガス",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ミニリュウ（ロケット団）。まきつく（無無）10: キャタピーの「いとをはく」と同じ文面
        AttackKey("PMCG4-051", 0): AttackEntry(
            ParalyzeOnHeads(),
            "まきつく",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのズバット。どくのきば（草無）20
        AttackKey("PMCG5-001", 1): AttackEntry(
            PoisonOnHeads(),
            "どくのきば",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのトサキント。みだれづき（無。10×）: コイン 2 枚の「おもて」の数×10（ドードーの「みだれづき」と同じパラメーター）
        AttackKey("PMCG5-026", 0): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=10),
            "みだれづき",
            text_ja="コインを2枚投げて「おもて」の数×10のダメージ。",
            play_text_ja="コインを2枚投げて「おもて」の数×10のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのトサキント。ちょうおんぱ（水。ダメージの目安なし）: シェルダーの「ちょうおんぱ」と同じ文面
        AttackKey("PMCG5-026", 1): AttackEntry(
            ConfuseOnHeadsWithoutDamage(),
            "ちょうおんぱ",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのコイル。でんきショック（雷）10
        AttackKey("PMCG5-037", 0): AttackEntry(
            ParalyzeOnHeads(),
            "でんきショック",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのビリリダマ。スピンボール（雷。20×）: コイン 1 枚の「おもて」の数×20
        AttackKey("PMCG5-038", 0): AttackEntry(
            CoinFlipDamage(coins=1, damage_per_heads=20),
            "スピンボール",
            text_ja="コインを1枚投げ、「おもて」の数×20のダメージ。",
            play_text_ja="コインを1枚投げ、「おもて」の数×20のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのビリリダマ。ダブルスピン（雷無。20×）: コイン 2 枚の「おもて」の数×20
        AttackKey("PMCG5-038", 1): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=20),
            "ダブルスピン",
            text_ja="コインを2枚投げ、「おもて」の数×20のダメージ。",
            play_text_ja="コインを2枚投げ、「おもて」の数×20のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのイシツブテ。いしなげ（闘。10×）: コイン 3 枚の「おもて」の数×10
        AttackKey("PMCG5-046", 0): AttackEntry(
            CoinFlipDamage(coins=3, damage_per_heads=10),
            "いしなげ",
            text_ja="コインを3枚投げ、「おもて」の数×10のダメージ。",
            play_text_ja="コインを3枚投げ、「おもて」の数×10のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのベロリンガ。たたきつける（無無無。30×）: コイン 2 枚の「おもて」の数×30
        AttackKey("PMCG5-061", 1): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=30),
            "たたきつける",
            text_ja="コインを2枚投げ、「おもて」の数×30のダメージ。",
            play_text_ja="コインを2枚投げ、「おもて」の数×30のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.30: 自分の「炎」エネルギーカードを 1 枚トラッシュしてから相手にダメージ（DiscardEnergyThenDamage。docs/discard-energy-attacks-v0.30.md）。
        # 印刷の文面「自分の「炎」エネルギーカードを1枚はがしてすてる。」のワザは、kyuura の RUL-ENERGY-DISCARD-ATTACKS の最新の説明にしたがう
        # （トラッシュはワザを使うための条件ではなく、ワザの効果。印刷の文面は照合にだけ使う）。ヒトカゲは v0.2a の過去の原典照合の記録があるカード
        # （card_verification.json。「ひっかく」を照合した。ひのこの最新の説明の欄はない）で、ひのこの文面の根拠は card_sources.json に置いた
        AttackKey("PMCG1-014", 1): AttackEntry(
            DiscardEnergyThenDamage(energy_type=EnergyType.FIRE),
            "ひのこ",
            text_ja=_FIRE_DISCARD_PRINTED,
            play_text_ja=_FIRE_DISCARD_LATEST,
            source=_RUL_ENERGY_DISCARD,
        ),
        # リザード（第1弾。ヒトカゲから進化）。かえんほうしゃ（炎炎無）50
        AttackKey("PMCG1-017", 1): AttackEntry(
            DiscardEnergyThenDamage(energy_type=EnergyType.FIRE),
            "かえんほうしゃ",
            text_ja=_FIRE_DISCARD_PRINTED,
            play_text_ja=_FIRE_DISCARD_LATEST,
            source=_RUL_ENERGY_DISCARD,
        ),
        # ウインディ（第1弾。ガーディから進化）。かえんほうしゃ（炎炎無）50。RUL-ENERGY-DISCARD-ATTACKS が挙げるカード（『トレーナーズ』Vol.9 の Q&A）
        AttackKey("PMCG1-019", 0): AttackEntry(
            DiscardEnergyThenDamage(energy_type=EnergyType.FIRE),
            "かえんほうしゃ",
            text_ja=_FIRE_DISCARD_PRINTED,
            play_text_ja=_FIRE_DISCARD_LATEST,
            source=_RUL_ENERGY_DISCARD,
        ),
        # ウインディ。とっしん（炎炎無無）80・自分にも 30（既存の DamageAndSelfDamage。ゴーリキーの「じごくぐるま」と同じ形。kyuura の印刷の文面）
        AttackKey("PMCG1-019", 1): AttackEntry(
            DamageAndSelfDamage(30),
            "とっしん",
            text_ja="自分にも30ダメージ。",
            play_text_ja="自分にも30ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ブーバー（第1弾）。かえんほうしゃ（炎炎無）50
        AttackKey("PMCG1-020", 1): AttackEntry(
            DiscardEnergyThenDamage(energy_type=EnergyType.FIRE),
            "かえんほうしゃ",
            text_ja=_FIRE_DISCARD_PRINTED,
            play_text_ja=_FIRE_DISCARD_LATEST,
            source=_RUL_ENERGY_DISCARD,
        ),
        # 第4弾のポニータ。ひのこ（炎無）30。印刷の文面がすでに「ワザの効果としてトラッシュする」書き方で、RUL-ENERGY-DISCARD-ATTACKS が挙げる文面
        # （第1弾）と違うので、処理に使う文面は kyuura の印刷の文面（「トラッシュできない時、…0になる」と最新の説明の「…なくなる」の違いは、v0.30 では
        # 起こらない場合だけにかかわった。v0.31 で相手のワザとして使われると起こるので、印刷の文面のとおり 0 にする。DiscardEnergyThenDamage の説明）
        AttackKey("PMCG4-013", 0): AttackEntry(
            DiscardEnergyThenDamage(energy_type=EnergyType.FIRE, when_lacking="zero"),
            "ひのこ",
            text_ja="このカードについている「炎」エネルギーカードを1枚トラッシュする。(トラッシュできない時、このワザのダメージは0になる)",
            play_text_ja="このカードについている「炎」エネルギーカードを1枚トラッシュする。(トラッシュできない時、このワザのダメージは0になる)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.31: v0.30 で保留した 22 枚と、進化元として加えた 7 枚（docs/held-cards-v0.31.md）。kyuura データの採用（card_sources.json）。処理に使う文面は、
        # 記録のあるものは kyuura のエラッタ（RUL-ENERGY-DISCARD-ATTACKS）、ほかは kyuura の印刷の文面
        # キュウコン（第1弾。ロコンから進化）。かどわかす（無無）: ワザを使ったプレイヤーが相手の控えを選んで入れ替える
        AttackKey("PMCG1-022", 0): AttackEntry(
            SwitchOpponentActive(),
            "かどわかす",
            text_ja="相手の控えポケモンを選んで、相手の対戦ポケモンと入れ替える。",
            play_text_ja="相手の控えポケモンを選んで、相手の対戦ポケモンと入れ替える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キュウコン。だいもんじ（炎炎炎炎）80。印刷の文面がかえんほうしゃと同じなので、RUL-ENERGY-DISCARD-ATTACKS の最新の説明（範囲としての当てはめ。errata_scope）
        AttackKey("PMCG1-022", 1): AttackEntry(
            DiscardEnergyThenDamage(energy_type=EnergyType.FIRE),
            "だいもんじ",
            text_ja=_FIRE_DISCARD_PRINTED,
            play_text_ja=_FIRE_DISCARD_LATEST,
            source=_RUL_ENERGY_DISCARD,
        ),
        # リザードン（第1弾。リザードから進化）。ほのおのうず（炎炎炎炎）100: どのエネルギーカードでも 2 枚トラッシュ（時点は HC1）
        AttackKey("PMCG1-021", 0): AttackEntry(
            DiscardEnergyBeforeDamage(None, 2, "unresolved", "condition"),
            "ほのおのうず",
            text_ja="自分のエネルギーカードを2枚はがしてすてる。",
            play_text_ja="自分のエネルギーカードを2枚はがしてすてる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サンダー（第1弾）。かみなり（雷雷雷無）60・「うら」なら自分にも 30（既存の SelfDamageOnTails）
        AttackKey("PMCG1-042", 0): AttackEntry(
            SelfDamageOnTails(self_damage=30),
            "かみなり",
            text_ja="コインを投げて「うら」なら、自分にも30ダメージ。",
            play_text_ja="コインを投げて「うら」なら、自分にも30ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サンダー。10まんボルト（雷雷雷雷）100: エネルギーカードをすべてトラッシュ（時点は HC1）
        AttackKey("PMCG1-042", 1): AttackEntry(
            DiscardEnergyBeforeDamage(None, None, "unresolved", "condition"),
            "10まんボルト",
            text_ja="自分のエネルギーカードを全てはがしてすてる。",
            play_text_ja="自分のエネルギーカードを全てはがしてすてる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ゴース（第1弾）。さいみんガス（超）: コインで「おもて」ならねむり
        AttackKey("PMCG1-044", 0): AttackEntry(
            SleepOnHeadsWithoutDamage(),
            "さいみんガス",
            text_ja="コインを投げて「おもて」なら、相手を「ねむり」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「ねむり」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ゴース。みちづれ（超無）: 超 1 枚トラッシュ・次の相手の番の「みちづれ」（DestinyBond。時点は HC1）
        AttackKey("PMCG1-044", 1): AttackEntry(
            DiscardEnergyThenSelfEffect(EnergyType.PSYCHIC, "destiny_bond"),
            "みちづれ",
            text_ja="「超」エネルギーカードを1枚はがしてすてる。次の相手の番で自分が「きぜつ」したときには、相手の対戦ポケモンも「きぜつ」する。",
            play_text_ja="「超」エネルギーカードを1枚はがしてすてる。次の相手の番で自分が「きぜつ」したときには、相手の対戦ポケモンも「きぜつ」する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ミュウツー（第1弾）。サイコキネシス（超無）10+: 相手のエネルギーカード × 10
        AttackKey("PMCG1-050", 0): AttackEntry(
            DamagePlusDefenderEnergy(10),
            "サイコキネシス",
            text_ja="相手についているエネルギーカード×10の追加ダメージをあたえる。",
            play_text_ja="相手についているエネルギーカード×10の追加ダメージをあたえる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ミュウツー。バリアー（超超）: 超 1 枚トラッシュ・次の相手の番のワザを受けない（AttackBarrier。時点は HC1）
        AttackKey("PMCG1-050", 1): AttackEntry(
            DiscardEnergyThenSelfEffect(EnergyType.PSYCHIC, "attack_barrier"),
            "バリアー",
            text_ja="自分についている「超」エネルギーカードを1枚はがしてすてることによって、次の相手の番の「ワザ」をうけない。",
            play_text_ja="自分についている「超」エネルギーカードを1枚はがしてすてることによって、次の相手の番の「ワザ」をうけない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ピクシー（第2弾。ピッピから進化）。ゆびをふる（無）: 相手のワザを自分のワザとして使う
        AttackKey("PMCG2-044", 0): AttackEntry(
            CopyOpponentAttackEffect("cannot_use"),
            "ゆびをふる",
            text_ja="相手のワザの中から1つを選び、それを【自分】のワザとして使う。そのワザを使うのに必要なエネルギーがついていなくてもかまわないが、ほかに必要な条件(エネルギーカードをはがしてすてるなど)がたりないときには使えない。",
            play_text_ja="相手のワザの中から1つを選び、それを【自分】のワザとして使う。そのワザを使うのに必要なエネルギーがついていなくてもかまわないが、ほかに必要な条件(エネルギーカードをはがしてすてるなど)がたりないときには使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ピクシー。ちいさくなる（無無）: 次の相手の番に受けるダメージ -20（p.321 の 8 段階）
        AttackKey("PMCG2-044", 1): AttackEntry(
            ReduceDamageNextTurn(20),
            "ちいさくなる",
            text_ja="次の相手の番でこのカードが受けるダメージが20へる。",
            play_text_ja="次の相手の番でこのカードが受けるダメージが20へる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ファイヤー（化石の秘密）。やまやき（炎）: 炎を好きなだけトラッシュし、同じ枚数を相手の山札から（時点は HC1・0 枚は HC5・山札は HC6）
        AttackKey("PMCG3-009", 0): AttackEntry(
            DiscardFireThenMillOpponent(),
            "やまやき",
            text_ja="自分の「炎」エネルギーカードを好きなだけはがしてすてる。その後、はがしたのと同じ枚数のカードを相手の山札の上から取り、相手のトラッシュにすてる。",
            play_text_ja="自分の「炎」エネルギーカードを好きなだけはがしてすてる。その後、はがしたのと同じ枚数のカードを相手の山札の上から取り、相手のトラッシュにすてる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ファイヤー。ゴッドバード（炎炎炎炎）80: 「うら」ならワザは失敗
        AttackKey("PMCG3-009", 1): AttackEntry(
            FailOnTailsDamage(),
            "ゴッドバード",
            text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            play_text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ヤドン（化石の秘密）。ぼーっとする（無）: ダメージカウンターがなければ使えない・「おもて」なら 1 個とりのぞく
        AttackKey("PMCG3-027", 0): AttackEntry(
            HealSelfOnHeadsIfDamaged(1),
            "ぼーっとする",
            text_ja="コインを投げて「おもて」なら、このカードからダメージカウンターを1つとりのぞく。このカードにダメージカウンターがのってない時には、このワザは使えない。",
            play_text_ja="コインを投げて「おもて」なら、このカードからダメージカウンターを1つとりのぞく。このカードにダメージカウンターがのってない時には、このワザは使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ヤドン。ゴミあさり（超超）: 超 1 枚トラッシュ・トラッシュのトレーナーを 1 枚手札に（時点は HC1）
        AttackKey("PMCG3-027", 1): AttackEntry(
            DiscardEnergyThenRecoverTrainer(EnergyType.PSYCHIC),
            "ゴミあさり",
            text_ja="このカードについている「超」エネルギーカードを1枚はがしてすてなければ、このワザは使えない。自分のトラッシュの中からトレーナーカードを1枚選び、手札に加える。",
            play_text_ja="このカードについている「超」エネルギーカードを1枚はがしてすてなければ、このワザは使えない。自分のトラッシュの中からトレーナーカードを1枚選び、手札に加える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいギャロップ（ロケット団）。ひばしら（炎炎）30: のぞむなら炎 1 枚トラッシュ・相手の控え 1 匹に 10
        AttackKey("PMCG4-014", 1): AttackEntry(
            DamageThenOptionalBenchDamage(EnergyType.FIRE, 10),
            "ひばしら",
            text_ja="のぞむなら、このカードについている「炎」エネルギーカードを1枚トラッシュし、その後、相手の控えポケモンを1匹選んで(「弱点・抵抗力」に関係なく)10ダメージを与えてもよい。",
            play_text_ja="のぞむなら、このカードについている「炎」エネルギーカードを1枚トラッシュし、その後、相手の控えポケモンを1匹選んで(「弱点・抵抗力」に関係なく)10ダメージを与えてもよい。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいリザード（ロケット団）。ファイヤーボール（炎炎炎）70
        AttackKey("PMCG4-015", 1): AttackEntry(
            FailOnTailsDiscardThenDamage(EnergyType.FIRE),
            "ファイヤーボール",
            text_ja="コインを投げて「うら」なら、このワザは失敗する。「おもて」の時は、このカードについている「炎」エネルギーカードを1枚トラッシュする。(トラッシュできない時、このワザのダメージは0になる)",
            play_text_ja="コインを投げて「うら」なら、このワザは失敗する。「おもて」の時は、このカードについている「炎」エネルギーカードを1枚トラッシュする。(トラッシュできない時、このワザのダメージは0になる)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいブースター（ロケット団）。いかり（無）10+
        AttackKey("PMCG4-016", 0): AttackEntry(
            DamagePlusOwnCounters(10),
            "いかり",
            text_ja="自分にのっているダメージカウンターの数×10のダメージを追加する。",
            play_text_ja="自分にのっているダメージカウンターの数×10のダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいブースター。ひあそび（炎炎）30+
        AttackKey("PMCG4-016", 1): AttackEntry(
            CoinBonusDiscardThenDamage(EnergyType.FIRE, 20),
            "ひあそび",
            text_ja="コインを投げて「おもて」なら、20ダメージを追加して、このカードについている「炎」エネルギーカードを1枚トラッシュする。(トラッシュできない時、このワザのダメージは0になる)",
            play_text_ja="コインを投げて「おもて」なら、20ダメージを追加して、このカードについている「炎」エネルギーカードを1枚トラッシュする。(トラッシュできない時、このワザのダメージは0になる)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいリザードン（ロケット団）。れんぞくファイヤーボール（炎炎）50×
        AttackKey("PMCG4-017", 1): AttackEntry(
            CoinsPerEnergyDamageThenDiscard(EnergyType.FIRE, 50),
            "れんぞくファイヤーボール",
            text_ja="このカードについている「炎」エネルギーカードの数だけコインを投げ、「おもて」の数×50のダメージ。その後、「おもて」の数ぶんの「炎」エネルギーカードを、このカードからはがしてトラッシュする。(トラッシュできない時、このワザのダメージは0になる)",
            play_text_ja="このカードについている「炎」エネルギーカードの数だけコインを投げ、「おもて」の数×50のダメージ。その後、「おもて」の数ぶんの「炎」エネルギーカードを、このカードからはがしてトラッシュする。(トラッシュできない時、このワザのダメージは0になる)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいゴルダック（ロケット団）。だい3のめ（超）
        AttackKey("PMCG4-022", 0): AttackEntry(
            DiscardEnergyThenDraw(3),
            "だい3のめ",
            text_ja="このカードについているエネルギーカードを1枚選び、トラッシュする。その後、山札からカードを3枚引く。",
            play_text_ja="このカードについているエネルギーカードを1枚選び、トラッシュする。その後、山札からカードを3枚引く。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいマルマイン（ロケット団）。エナジーボム（雷雷）30（CR-TRANSPARENCY-ENERGY-BOMB）
        AttackKey("PMCG4-028", 1): AttackEntry(
            DamageThenMoveEnergyToBench(),
            "エナジーボム",
            text_ja="このカードについているエネルギーカードをすべてはがし、自分の控えポケモンに好きなようにつける。(自分に控えがいない時、エネルギーカードはトラッシュする)",
            play_text_ja="このカードについているエネルギーカードをすべてはがし、自分の控えポケモンに好きなようにつける。(自分に控えがいない時、エネルギーカードはトラッシュする)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのゴルダック（リーダーズスタジアム）。エクストラビーム（水無）40
        AttackKey("PMCG5-032", 0): AttackEntry(
            DamageThenDiscardAllOnTails(None),
            "エクストラビーム",
            text_ja="コインを投げて「うら」なら、自分についているエネルギーカードを、すべてトラッシュする。",
            play_text_ja="コインを投げて「うら」なら、自分についているエネルギーカードを、すべてトラッシュする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのゴルダック。スーパーデストロイ（超無）
        AttackKey("PMCG5-032", 1): AttackEntry(
            CoinDiscardOpponentEnergyEach(),
            "スーパーデストロイ",
            text_ja="コインを投げて「おもて」なら、相手と相手の控えポケモン全員から、それぞれエネルギーカードを1枚ずつ選び、トラッシュする。",
            play_text_ja="コインを投げて「おもて」なら、相手と相手の控えポケモン全員から、それぞれエネルギーカードを1枚ずつ選び、トラッシュする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのエレブー（リーダーズスタジアム）。たいでん（雷）: 0 枚は HC7
        AttackKey("PMCG5-041", 0): AttackEntry(
            AttachDiscardEnergyToSelf(EnergyType.LIGHTNING, 2),
            "たいでん",
            text_ja="自分のトラッシュに「雷」エネルギーカードがあれば、最大2枚を取り出して、自分につける。",
            play_text_ja="自分のトラッシュに「雷」エネルギーカードがあれば、最大2枚を取り出して、自分につける。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのエレブー。ほうでん（雷）30×
        AttackKey("PMCG5-041", 1): AttackEntry(
            DiscardAllThenCoinDamage(EnergyType.LIGHTNING, 30),
            "ほうでん",
            text_ja="自分についている「雷」エネルギーカードを、すべてトラッシュする。その後、トラッシュした「雷」エネルギーカードの数だけコインを投げ、「おもて」の数×30のダメージ。",
            play_text_ja="自分についている「雷」エネルギーカードを、すべてトラッシュする。その後、トラッシュした「雷」エネルギーカードの数だけコインを投げ、「おもて」の数×30のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのヒトカゲ（闇からの挑戦）。メラメラ（炎）10
        AttackKey("PMCG6-025", 0): AttackEntry(
            DamageThenDiscardEachEnergy(),
            "メラメラ",
            text_ja="自分と相手についているエネルギーカードを1枚ずつ選び、それぞれトラッシュする。",
            play_text_ja="自分と相手についているエネルギーカードを1枚ずつ選び、それぞれトラッシュする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのリザード（闇からの挑戦）。やきはらう（炎炎炎）
        AttackKey("PMCG6-029", 1): AttackEntry(
            CoinsDiscardThenSpreadDamage(EnergyType.FIRE, 3, 10),
            "やきはらう",
            text_ja="コインを3枚投げ、「おもて」の数ぶんの「炎」エネルギーカードを、自分からトラッシュする。トラッシュできない時、このワザは失敗する。相手と相手の控えポケモン全員に、「おもて」の数×10のダメージを、「弱点・抵抗力」に関係なく、それぞれ与える。",
            play_text_ja="コインを3枚投げ、「おもて」の数ぶんの「炎」エネルギーカードを、自分からトラッシュする。トラッシュできない時、このワザは失敗する。相手と相手の控えポケモン全員に、「おもて」の数×10のダメージを、「弱点・抵抗力」に関係なく、それぞれ与える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのブーバー（闇からの挑戦）。ひをふく（炎）10+
        AttackKey("PMCG6-031", 0): AttackEntry(
            CoinBonusDamage(10),
            "ひをふく",
            text_ja="コインを投げて「おもて」なら、10ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、10ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのブーバー。マグマふんしゅつ（炎炎炎）20×（山札が足りないときは HC6）
        AttackKey("PMCG6-031", 1): AttackEntry(
            MillSelfThenDamage(5, EnergyType.FIRE, 20),
            "マグマふんしゅつ",
            text_ja="自分の山札の上から、カード5枚トラッシュする。トラッシュした5枚の中にあった「炎」エネルギーカードの数×20のダメージ。",
            play_text_ja="自分の山札の上から、カード5枚トラッシュする。トラッシュした5枚の中にあった「炎」エネルギーカードの数×20のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのキュウコン（闇からの挑戦）。しゃくねつ（炎炎）50
        AttackKey("PMCG6-033", 0): AttackEntry(
            DamageThenDiscardAllOnTails(EnergyType.FIRE),
            "しゃくねつ",
            text_ja="コインを投げて「うら」なら、自分についている「炎」エネルギーカードを、すべてトラッシュする。",
            play_text_ja="コインを投げて「うら」なら、自分についている「炎」エネルギーカードを、すべてトラッシュする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのウインディ（闇からの挑戦）。ヒートタックル（炎無無）40・自分にも 10（既存の DamageAndSelfDamage）
        AttackKey("PMCG6-034", 0): AttackEntry(
            DamageAndSelfDamage(10),
            "ヒートタックル",
            text_ja="自分にも10ダメージ。",
            play_text_ja="自分にも10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのウインディ。ほのおのあらし（炎炎炎炎）120: 炎 3 枚トラッシュ（RUL-ENERGY-DISCARD-ATTACKS の範囲の時点。文面は印刷。トラッシュできなければ使えない）
        AttackKey("PMCG6-034", 1): AttackEntry(
            DiscardEnergyBeforeDamage(EnergyType.FIRE, 3, "effect", "cannot_use"),
            "ほのおのあらし",
            text_ja="自分についている「炎」エネルギーカードを3枚トラッシュしなければ、このワザは使えない。",
            play_text_ja="自分についている「炎」エネルギーカードを3枚トラッシュしなければ、このワザは使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのライチュウ（闇からの挑戦）。バリバリ（雷雷）20+
        AttackKey("PMCG6-041", 0): AttackEntry(
            CoinBonusDamageThenDiscardAll(EnergyType.LIGHTNING, 30),
            "バリバリ",
            text_ja="コインを投げて「おもて」なら、30ダメージを追加して、自分についている「雷」エネルギーカードを、すべてトラッシュする。",
            play_text_ja="コインを投げて「おもて」なら、30ダメージを追加して、自分についている「雷」エネルギーカードを、すべてトラッシュする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのライチュウ。でんきタックル（雷雷無無）40
        AttackKey("PMCG6-041", 1): AttackEntry(
            DamageThenParalyzeOrSelfDamage(20),
            "でんきタックル",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。「うら」なら自分にも20ダメージ。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。「うら」なら自分にも20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ピッピ（第1弾。ピクシーの進化元）。うたう（無）
        AttackKey("PMCG1-067", 0): AttackEntry(
            SleepOnHeadsWithoutDamage(),
            "うたう",
            text_ja="コインを投げて「おもて」なら、相手を「ねむり」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「ねむり」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ピッピ。ゆびをふる（無無無）: 処理に使う文面は kyuura の card_differences の PMCG1-067 の記録（確度: 確実）が引く p.223 の最新の説明。
        # 同じ記録の解説「基本的にワザに必要なエネルギー以外はワザの説明にしたがいます」（FOLLOW_TEXT）。印刷の文面は照合だけに使う
        AttackKey("PMCG1-067", 1): AttackEntry(
            CopyOpponentAttackEffect("follow_text"),
            "ゆびをふる",
            text_ja="相手の対戦ポケモンの「ワザ」の中から1つを選び、それを自分の「ワザ」としてつかう。",
            play_text_ja="相手のワザを1つ選び、それを、自分が持っているワザとして使う。（そのワザに必要なエネルギーがついていなくても、かまわない）",
            source=f"{_CARD_DIFFERENCES}#PMCG1-067",
        ),
        # イーブイ（第2弾。わるいブースターの進化元）。しっぽをふる（無）
        AttackKey("PMCG2-037", 0): AttackEntry(
            CannotAttackOnHeads(),
            "しっぽをふる",
            text_ja="コインを投げて「おもて」なら「しっぽをふる」を受けた相手の対戦ポケモンは、次の相手の番にワザをつかえない。",
            play_text_ja="コインを投げて「おもて」なら「しっぽをふる」を受けた相手の対戦ポケモンは、次の相手の番にワザをつかえない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # イーブイ。でんこうせっか（無無）10+
        AttackKey("PMCG2-037", 1): AttackEntry(
            CoinBonusDamage(20),
            "でんこうせっか",
            text_ja="コインを投げて「おもて」なら、20ダメージ追加する。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージ追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # コダック（ロケット団。わるいゴルダックの進化元）。めまい（超）
        AttackKey("PMCG4-019", 0): AttackEntry(
            DrawCardsAttack(1),
            "めまい",
            text_ja="山札からカードを1枚引く。",
            play_text_ja="山札からカードを1枚引く。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # コダック。みずでっぽう（水無）20+（無色のぶんの数え方は HC4）
        AttackKey("PMCG4-019", 1): AttackEntry(
            ExtraEnergyDamageMixed(EnergyType.WATER, 10, 2),
            "みずでっぽう",
            text_ja="ワザに必要なエネルギーよりも多く「水」エネルギーがついている時、多い「水」エネルギー1つにつき、10ダメージを追加する。(ダメージ追加は2つぶんまで)",
            play_text_ja="ワザに必要なエネルギーよりも多く「水」エネルギーがついている時、多い「水」エネルギー1つにつき、10ダメージを追加する。(ダメージ追加は2つぶんまで)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのコダック（リーダーズスタジアム。カスミのゴルダックの進化元）。ちょうのうりょく（超）
        AttackKey("PMCG5-021", 0): AttackEntry(
            ThreeCoinPsychicPower(),
            "ちょうのうりょく",
            text_ja="コインを3枚投げる。「おもて」が1枚なら、山札の上からカードを1枚引いて、手札に加える。「おもて」が2枚なら、相手に20ダメージ。「おもて」が3枚なら相手のワザを1つ選び、それを、自分が持っているワザとして使う。(そのワザに必要なエネルギーがついていなくても、かまわない)",
            play_text_ja="コインを3枚投げる。「おもて」が1枚なら、山札の上からカードを1枚引いて、手札に加える。「おもて」が2枚なら、相手に20ダメージ。「おもて」が3枚なら相手のワザを1つ選び、それを、自分が持っているワザとして使う。(そのワザに必要なエネルギーがついていなくても、かまわない)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのロコン（闇からの挑戦。カツラのキュウコンの進化元）。しっぽでまどわす（炎無無）20（既存の ConfuseOnHeads）
        AttackKey("PMCG6-026", 0): AttackEntry(
            ConfuseOnHeads(),
            "しっぽでまどわす",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのガーディ（闇からの挑戦。カツラのウインディの進化元）。もえひろがる（炎炎）20
        AttackKey("PMCG6-027", 0): AttackEntry(
            DamageAndBenchTypeDamage(EnergyType.GRASS, 10),
            "もえひろがる",
            text_ja="相手のベンチにいる「草」ポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            play_text_ja="相手のベンチにいる「草」ポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのピカチュウ（リーダーズスタジアム。マチスのライチュウの進化元）。でんこうせっか（無無）10+
        AttackKey("PMCG5-036", 0): AttackEntry(
            CoinBonusDamage(20),
            "でんこうせっか",
            text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.32（docs/bench-search-counter-drain-v0.32.md）。kyuura データの採用（card_sources.json）。処理に使う文面は kyuura の印刷の文面
        # ニドラン♀（第2弾）。みだれひっかき（草）10×
        AttackKey("PMCG2-001", 0): AttackEntry(
            CoinFlipDamage(coins=3, damage_per_heads=10),
            "みだれひっかき",
            text_ja="コインを3枚投げて「おもて」の数×10のダメージ。",
            play_text_ja="コインを3枚投げて「おもて」の数×10のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ニドラン♀。なかまをよぶ（草草）。v0.32 ではニドラン♂（PMCG1-005）を写していなかったので選べるのはニドラン♀だけだった。v0.33 でニドラン♂を
        # 加えたので、どちらも選べる（説明は名前で指す）
        AttackKey("PMCG2-001", 1): AttackEntry(
            PutBasicFromDeckOntoBench(("ニドラン♂", "ニドラン♀")),
            "なかまをよぶ",
            text_ja="自分の山札から「ニドラン♂」または「ニドラン♀」を1匹さがしてベンチにだす。その後、その山札をよくきる。自分のベンチに空きがなければ使えない。",
            play_text_ja="自分の山札から「ニドラン♂」または「ニドラン♀」を1匹さがしてベンチにだす。その後、その山札をよくきる。自分のベンチに空きがなければ使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナゾノクサ（第2弾。第4弾のナゾノクサ PMCG4-003 とは別のカード）。しびれごな（草）10
        AttackKey("PMCG2-002", 0): AttackEntry(
            ParalyzeOnHeads(),
            "しびれごな",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナゾノクサ（第2弾）。ふえる（草草）。名前で指すので、第4弾のナゾノクサも選べる
        AttackKey("PMCG2-002", 1): AttackEntry(
            PutBasicFromDeckOntoBench(("ナゾノクサ",)),
            "ふえる",
            text_ja="自分の山札から「ナゾノクサ」を1匹さがしてベンチにだす。その後、その山札をよくきる。自分のベンチに空きがなければ使えない。",
            play_text_ja="自分の山札から「ナゾノクサ」を1匹さがしてベンチにだす。その後、その山札をよくきる。自分のベンチに空きがなければ使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マダツボミ（第2弾）。なかまをよぶ（草）
        AttackKey("PMCG2-005", 1): AttackEntry(
            PutBasicFromDeckOntoBench(("マダツボミ",)),
            "なかまをよぶ",
            text_ja="自分の山札から「マダツボミ」を1匹さがしてベンチにだす。その後、その山札をよくきる。自分のベンチに空きがなければ使えない。",
            play_text_ja="自分の山札から「マダツボミ」を1匹さがしてベンチにだす。その後、その山札をよくきる。自分のベンチに空きがなければ使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # クラブ（化石の秘密）。なかまをよぶ（水）
        AttackKey("PMCG3-013", 0): AttackEntry(
            PutBasicFromDeckOntoBench(("クラブ",)),
            "なかまをよぶ",
            text_ja="自分の山札から「クラブ」を1匹さがしてベンチに出す。その後、その山札をよくきる。自分のベンチに空きがなければ、このワザは使えない。",
            play_text_ja="自分の山札から「クラブ」を1匹さがしてベンチに出す。その後、その山札をよくきる。自分のベンチに空きがなければ、このワザは使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ニドリーナ（第2弾。ニドラン♀から進化）。ちょうおんぱ（草）
        AttackKey("PMCG2-008", 0): AttackEntry(
            ConfuseOnHeadsWithoutDamage(),
            "ちょうおんぱ",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ニドリーナ。にどげり（草無無）30×
        AttackKey("PMCG2-008", 1): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=30),
            "にどげり",
            text_ja="コインを2枚投げて「おもて」の数×30のダメージ。",
            play_text_ja="コインを2枚投げて「おもて」の数×30のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ウツドン（第2弾。マダツボミから進化）。どくのこな（草）10
        AttackKey("PMCG2-011", 0): AttackEntry(
            PoisonOnHeads(),
            "どくのこな",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # コイキング（第1弾）。じたばた（水）10×
        AttackKey("PMCG1-031", 1): AttackEntry(
            DamageTimesOwnCounters(10),
            "じたばた",
            text_ja="自分のダメージカウンターの数×10のダメージをあたえる。",
            play_text_ja="自分のダメージカウンターの数×10のダメージをあたえる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ギャラドス（第1弾。コイキングから進化）。バブルこうせん（水水水水）40
        AttackKey("PMCG1-034", 1): AttackEntry(
            ParalyzeOnHeads(),
            "バブルこうせん",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キングラー（化石の秘密。クラブから進化）。じたばた（水）10×
        AttackKey("PMCG3-019", 0): AttackEntry(
            DamageTimesOwnCounters(10),
            "じたばた",
            text_ja="自分にのっているダメージカウンターの数×10のダメージ。",
            play_text_ja="自分にのっているダメージカウンターの数×10のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ルージュラ（第1弾）。おうふくびんた（超）10×
        AttackKey("PMCG1-048", 0): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=10),
            "おうふくびんた",
            text_ja="コインを2枚投げて「おもて」の出た数×10のダメージをあたえる。",
            play_text_ja="コインを2枚投げて「おもて」の出た数×10のダメージをあたえる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ルージュラ。ヨガのポーズ（超超無）20+（「相手のポケモン」の範囲は CD4）
        AttackKey("PMCG1-048", 1): AttackEntry(
            DamagePlusDefenderCounters(10),
            "ヨガのポーズ",
            text_ja="相手のポケモンにのっているダメージカウンター×10のダメージを追加する。",
            play_text_ja="相手のポケモンにのっているダメージカウンター×10のダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # コンパン（第2弾）。しびれごな（草）10
        AttackKey("PMCG2-004", 0): AttackEntry(
            ParalyzeOnHeads(),
            "しびれごな",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # コンパン。きゅうけつ（草無）10
        AttackKey("PMCG2-004", 1): AttackEntry(
            DamageAndFullDrain(),
            "きゅうけつ",
            text_ja="相手にダメージを与えたら、与えたぶんのダメージカウンターを自分からとりのぞく。",
            play_text_ja="相手にダメージを与えたら、与えたぶんのダメージカウンターを自分からとりのぞく。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ズバット（化石の秘密。第4弾のズバット PMCG4-002・タケシのズバットとは別のカード）。ちょうおんぱ（無無）
        AttackKey("PMCG3-002", 0): AttackEntry(
            ConfuseOnHeadsWithoutDamage(),
            "ちょうおんぱ",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ズバット（化石の秘密）。きゅうけつ（草無）10
        AttackKey("PMCG3-002", 1): AttackEntry(
            DamageAndFullDrain(),
            "きゅうけつ",
            text_ja="相手にダメージを与えたら、与えたぶんのダメージカウンターを自分からとりのぞく。",
            play_text_ja="相手にダメージを与えたら、与えたぶんのダメージカウンターを自分からとりのぞく。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ゴルバット（化石の秘密。ズバットから進化）。きゅうけつ（草草無）20
        AttackKey("PMCG3-005", 1): AttackEntry(
            DamageAndFullDrain(),
            "きゅうけつ",
            text_ja="相手にダメージを与えたら、与えたぶんのダメージカウンターを自分からとりのぞく。",
            play_text_ja="相手にダメージを与えたら、与えたぶんのダメージカウンターを自分からとりのぞく。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.33（docs/cd4-opponent-energy-coins-v0.33.md）。kyuura データの採用（card_sources.json）。処理に使う文面は kyuura の印刷の文面
        # ハクリュー（第1弾。ミニリュウから進化）。たたきつける（無無無）30×
        AttackKey("PMCG1-069", 0): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=30),
            "たたきつける",
            text_ja="コインを2枚投げて「おもて」の数×30のダメージを相手にあたえる。",
            play_text_ja="コインを2枚投げて「おもて」の数×30のダメージを相手にあたえる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ハクリュー。はかいこうせん（無無無無）20: 相手の対戦ポケモンのエネルギーカードを 1 枚トラッシュ（選ぶのはワザを使ったプレイヤー）
        AttackKey("PMCG1-069", 1): AttackEntry(
            DamageThenDiscardOpponentEnergy(),
            "はかいこうせん",
            text_ja="相手の対戦ポケモンのエネルギーカードを1枚はがしてすてる。",
            play_text_ja="相手の対戦ポケモンのエネルギーカードを1枚はがしてすてる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ゴルダック（化石の秘密。コダックから進化）。ねんりき（超）10
        AttackKey("PMCG3-016", 0): AttackEntry(
            ParalyzeOnHeads(),
            "ねんりき",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ゴルダック。はかいこうせん（水水無）20: エネルギーカードがついていなければ効果はない（説明）
        AttackKey("PMCG3-016", 1): AttackEntry(
            DamageThenDiscardOpponentEnergy(),
            "はかいこうせん",
            text_ja="相手の対戦ポケモンについているエネルギーカードを1枚選び、それをはがして相手のトラッシュにすてる。相手の対戦ポケモンにエネルギーカードがついていない時には、この効果はない。",
            play_text_ja="相手の対戦ポケモンについているエネルギーカードを1枚選び、それをはがして相手のトラッシュにすてる。相手の対戦ポケモンにエネルギーカードがついていない時には、この効果はない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいシャワーズ（ロケット団。イーブイから進化）。うずしお（水水無）20: 「選び、トラッシュさせる」（選ぶのはワザを使ったプレイヤー）
        AttackKey("PMCG4-023", 1): AttackEntry(
            DamageThenDiscardOpponentEnergy(),
            "うずしお",
            text_ja="相手の対戦ポケモンについているエネルギーカードを1枚選び、トラッシュさせる。",
            play_text_ja="相手の対戦ポケモンについているエネルギーカードを1枚選び、トラッシュさせる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのコイル（リーダーズスタジアム。v0.29 のマチスのコイル PMCG5-037 とは別のカード）。はかいでんぱ（雷）10
        AttackKey("PMCG5-039", 0): AttackEntry(
            DamageThenDiscardOpponentEnergy(on_heads=True),
            "はかいでんぱ",
            text_ja="コインを投げて「おもて」なら、相手についているエネルギーカードを1枚選び、トラッシュさせる。",
            play_text_ja="コインを投げて「おもて」なら、相手についているエネルギーカードを1枚選び、トラッシュさせる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのコイル。こんらんでんぱ（雷雷）20
        AttackKey("PMCG5-039", 1): AttackEntry(
            ConfuseOnHeads(),
            "こんらんでんぱ",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのコンパン（闇からの挑戦）。どくのしょっかく（草。ダメージの目安なし）
        AttackKey("PMCG6-006", 0): AttackEntry(
            PoisonWithoutDamage(),
            "どくのしょっかく",
            text_ja="相手を「どく」状態にする。",
            play_text_ja="相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのコンパン。はかいビーム（超無）20
        AttackKey("PMCG6-006", 1): AttackEntry(
            DamageThenDiscardOpponentEnergy(on_heads=True),
            "はかいビーム",
            text_ja="コインを投げて「おもて」なら、相手についているエネルギーカードを1枚選び、トラッシュする。",
            play_text_ja="コインを投げて「おもて」なら、相手についているエネルギーカードを1枚選び、トラッシュする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ニドラン♂（第1弾）。つのでつつく（草）30: 「うら」ならダメージを与えられない（ワザの失敗ではない）
        AttackKey("PMCG1-005", 0): AttackEntry(
            NoDamageOnTails(),
            "つのでつつく",
            text_ja="コインを投げて「うら」なら、相手にダメージをあたえることができない。",
            play_text_ja="コインを投げて「うら」なら、相手にダメージをあたえることができない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ニドリーノ（第1弾。ニドラン♂から進化）。にどげり（草無無）30×
        AttackKey("PMCG1-010", 0): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=30),
            "にどげり",
            text_ja="コインを2枚投げて「おもて」のでた数×30のダメージをあたえる。",
            play_text_ja="コインを2枚投げて「おもて」のでた数×30のダメージをあたえる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # パルシェン（化石の秘密。シェルダーから進化）。からではさむ（水水）30: 1 枚のコインでダメージ・マヒ・失敗が決まる
        AttackKey("PMCG3-018", 0): AttackEntry(
            DamageAndParalyzeOnHeadsElseFail(),
            "からではさむ",
            text_ja="コインを投げて「おもて」なら、ダメージとともに相手を「マヒ」状態にする。「うら」なら、このワザは失敗する。",
            play_text_ja="コインを投げて「おもて」なら、ダメージとともに相手を「マヒ」状態にする。「うら」なら、このワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # パルシェン。とげキャノン（水水）30×
        AttackKey("PMCG3-018", 1): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=30),
            "とげキャノン",
            text_ja="コインを2枚投げて「おもて」の数×30のダメージ。",
            play_text_ja="コインを2枚投げて「おもて」の数×30のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいラッタ（ロケット団。コラッタから進化）。ひっさつまえば（無無無）50
        AttackKey("PMCG4-046", 1): AttackEntry(
            FailOnTailsDamage(),
            "ひっさつまえば",
            text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            play_text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのディグダ（リーダーズスタジアム）。ふいをつく（闘）20
        AttackKey("PMCG5-044", 0): AttackEntry(
            FailOnTailsDamage(),
            "ふいをつく",
            text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            play_text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのディグダ。ミニじしん（闘無）40: 自分の控えポケモン全員にも 10（弱点・抵抗力なし）
        AttackKey("PMCG5-044", 1): AttackEntry(
            DamageAndOwnBenchDamage(10),
            "ミニじしん",
            text_ja="自分の控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            play_text_ja="自分の控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのサイホーン（リーダーズスタジアム）。ドリルタックル（闘無）70: 2 枚とも「おもて」のときだけダメージ
        AttackKey("PMCG5-049", 0): AttackEntry(
            FailOnTailsDamage(coins=2),
            "ドリルタックル",
            text_ja="コインを2枚投げ、1つでも「うら」なら、このワザは失敗する。",
            play_text_ja="コインを2枚投げ、1つでも「うら」なら、このワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのオニスズメ（リーダーズスタジアム）。ふきとばし（無）10: 入れ替えるポケモンは相手が選ぶ
        AttackKey("PMCG5-057", 0): AttackEntry(
            DamageAndForceSwitch(),
            "ふきとばし",
            text_ja="相手を、控えポケモンと入れ替える。入れ替えるポケモンは、相手が選ぶ。（相手に控えがいない時、入れ替えはおこらない。）",
            play_text_ja="相手を、控えポケモンと入れ替える。入れ替えるポケモンは、相手が選ぶ。（相手に控えがいない時、入れ替えはおこらない。）",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのオニスズメ。かまいたち（無無）40
        AttackKey("PMCG5-057", 1): AttackEntry(
            FailOnTailsDamage(),
            "かまいたち",
            text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            play_text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのニドラン♀（闇からの挑戦。第2弾のニドラン♀ PMCG2-001 とは別の名前）。つき（草）20
        AttackKey("PMCG6-003", 0): AttackEntry(
            FailOnTailsDamage(),
            "つき",
            text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            play_text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのニドラン♀。すてみタックル（無無）30
        AttackKey("PMCG6-003", 1): AttackEntry(
            DamageAndSelfDamage(20),
            "すてみタックル",
            text_ja="自分にも20ダメージ。",
            play_text_ja="自分にも20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのサイホーン（闇からの挑戦）。ホーンアタック（闘）30
        AttackKey("PMCG6-058", 0): AttackEntry(
            FailOnTailsDamage(),
            "ホーンアタック",
            text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            play_text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのサイホーン。かけぬける（無無無）20: 「おもて」なら相手の控えを 1 匹選んで 20（弱点・抵抗力なし）
        AttackKey("PMCG6-058", 1): AttackEntry(
            DamageThenCoinBenchDamage(20),
            "かけぬける",
            text_ja="コインを投げて「おもて」なら、相手の控えポケモンを1匹選び、そのポケモンにも、「弱点・抵抗力」に関係なく、20ダメージ。",
            play_text_ja="コインを投げて「おもて」なら、相手の控えポケモンを1匹選び、そのポケモンにも、「弱点・抵抗力」に関係なく、20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのドードー（闇からの挑戦）。けりつける（無）20
        AttackKey("PMCG6-064", 0): AttackEntry(
            FailOnTailsDamage(),
            "けりつける",
            text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            play_text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのドードー。しかえし（無無）10×: じたばた（v0.32）と同じ型
        AttackKey("PMCG6-064", 1): AttackEntry(
            DamageTimesOwnCounters(10),
            "しかえし",
            text_ja="自分にのっているダメージカウンターの数×10のダメージ。",
            play_text_ja="自分にのっているダメージカウンターの数×10のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.34（docs/barrier-resume-coin-bonus-v0.34.md）。ギャロップ（第2弾。ポニータから進化）。ふみつけ（無無）20+
        AttackKey("PMCG2-019", 0): AttackEntry(
            CoinBonusDamage(10),
            "ふみつけ",
            text_ja="コインを投げて「おもて」なら、10ダメージ追加する。",
            play_text_ja="コインを投げて「おもて」なら、10ダメージ追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ギャロップ。こうそくいどう（炎炎無）30: ダメージのあと、コインが「おもて」なら次の相手の番にワザをうけない（バリアーと同じ持続する効果）
        AttackKey("PMCG2-019", 1): AttackEntry(
            DamageThenSelfBarrierOnHeads(),
            "こうそくいどう",
            text_ja="コインを投げて「おもて」なら、このカードは次の相手の番にワザをうけない。",
            play_text_ja="コインを投げて「おもて」なら、このカードは次の相手の番にワザをうけない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ブースター（第2弾。イーブイから進化）。でんこうせっか（無無）10+
        AttackKey("PMCG2-020", 0): AttackEntry(
            CoinBonusDamage(20),
            "でんこうせっか",
            text_ja="コインを投げて「おもて」なら、20ダメージ追加する。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージ追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ブースター。かえんほうしゃ（炎炎無無）60: 炎エネルギーカードを 1 枚トラッシュ（ワザの効果。RUL-ENERGY-DISCARD-ATTACKS の範囲）→ ダメージ。トラッシュできなければ失敗
        AttackKey("PMCG2-020", 1): AttackEntry(
            DiscardEnergyBeforeDamage(EnergyType.FIRE, 1, "effect", "fail"),
            "かえんほうしゃ",
            text_ja="このカードについている「炎」エネルギーカードを1枚はがしてすてなければ、このワザは失敗する。",
            play_text_ja="このカードについている「炎」エネルギーカードを1枚はがしてすてなければ、このワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # シャワーズ（第2弾。イーブイから進化）。でんこうせっか（無無）10+
        AttackKey("PMCG2-023", 0): AttackEntry(
            CoinBonusDamage(20),
            "でんこうせっか",
            text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # シャワーズ。みずでっぽう（水水無）30+: 第4弾のコダック（v0.31）と同じ型（無色に払った水の扱いは HC4）
        AttackKey("PMCG2-023", 1): AttackEntry(
            ExtraEnergyDamageMixed(EnergyType.WATER, 10, 2),
            "みずでっぽう",
            text_ja="このワザに必要な分よりも多く「水」エネルギーがついている時、多いエネルギー1つにつき10ダメージを追加する。(ダメージ追加は2つぶんまで)",
            play_text_ja="このワザに必要な分よりも多く「水」エネルギーがついている時、多いエネルギー1つにつき10ダメージを追加する。(ダメージ追加は2つぶんまで)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サンダース（第2弾。イーブイから進化）。でんこうせっか（無無）10+
        AttackKey("PMCG2-026", 0): AttackEntry(
            CoinBonusDamage(20),
            "でんこうせっか",
            text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サンダース。ミサイルばり（雷雷無）20×
        AttackKey("PMCG2-026", 1): AttackEntry(
            CoinFlipDamage(coins=4, damage_per_heads=20),
            "ミサイルばり",
            text_ja="コインを4枚投げて「おもて」の数×20のダメージ。",
            play_text_ja="コインを4枚投げて「おもて」の数×20のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エレブー（第1弾）。でんきショック（雷）10
        AttackKey("PMCG1-041", 0): AttackEntry(
            ParalyzeOnHeads(),
            "でんきショック",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エレブー。かみなりパンチ（雷無）30+: 1 枚のコインで「おもて」なら追加 10、「うら」なら自分に 10（投げ直さない）
        AttackKey("PMCG1-041", 1): AttackEntry(
            CoinBonusOrSelfDamage(bonus=10, self_damage=10),
            "かみなりパンチ",
            text_ja="コインを投げて「おもて」なら、相手に10ダメージを追加する。「うら」なら自分にも10ダメージ。",
            play_text_ja="コインを投げて「おもて」なら、相手に10ダメージを追加する。「うら」なら自分にも10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ケンタロス（第2弾）。ふみつけ（無無）20+
        AttackKey("PMCG2-042", 0): AttackEntry(
            CoinBonusDamage(10),
            "ふみつけ",
            text_ja="コインを投げて「おもて」なら、10ダメージ追加する。",
            play_text_ja="コインを投げて「おもて」なら、10ダメージ追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ケンタロス。いかりくるう（無無無）20+: ダメージのあと、コインが「うら」なら自分がこんらん
        AttackKey("PMCG2-042", 1): AttackEntry(
            DamagePlusOwnCountersThenSelfConfuseOnTails(10),
            "いかりくるう",
            text_ja="自分にのっているダメージカウンター×10のダメージを追加する。その後、コインを投げて「うら」なら、【自分】は「こんらん」状態になる。",
            play_text_ja="自分にのっているダメージカウンター×10のダメージを追加する。その後、コインを投げて「うら」なら、【自分】は「こんらん」状態になる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのロコン（リーダーズスタジアム。「ほのお」は説明文のないワザの一覧）。でんこうせっか（無無）10+
        AttackKey("PMCG5-018", 1): AttackEntry(
            CoinBonusDamage(20),
            "でんこうせっか",
            text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのカイロス（闇からの挑戦。第2弾のカイロス PMCG2-018 とは別のカード）。きあいばさみ（草無）10+
        AttackKey("PMCG6-024", 0): AttackEntry(
            CoinBonusDamage(20),
            "きあいばさみ",
            text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのカイロス。うしろなげ（草無無）40: コインが「うら」なら自分の控えを 1 匹選んで 20（弱点・抵抗力なし）
        AttackKey("PMCG6-024", 1): AttackEntry(
            DamageThenCoinOwnBenchDamage(20),
            "うしろなげ",
            text_ja="コインを投げて「うら」なら、自分の控えポケモンを1匹選び、そのポケモンにも、「弱点・抵抗力」に関係なく、20ダメージ。",
            play_text_ja="コインを投げて「うら」なら、自分の控えポケモンを1匹選び、そのポケモンにも、「弱点・抵抗力」に関係なく、20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのガルーラ（闇からの挑戦。第2弾のガルーラ PMCG2-046 とは別のカード）。こどもパンチ（無）10
        AttackKey("PMCG6-069", 0): AttackEntry(
            FailOnTailsDamage(),
            "こどもパンチ",
            text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            play_text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのガルーラ。おやこパンチ（無無無）30+
        AttackKey("PMCG6-069", 1): AttackEntry(
            CoinBonusDamage(10),
            "おやこパンチ",
            text_ja="コインを投げて「おもて」なら、10ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、10ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ドガース（第1弾。ロケット団のドガース PMCG4-005 とは別のカード）。くさいガス（草草）10: 1 枚のコインで「おもて」ならどく、「うら」ならこんらん
        AttackKey("PMCG1-006", 0): AttackEntry(
            DamageThenPoisonOrConfuse(),
            "くさいガス",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態、「うら」なら「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態、「うら」なら「こんらん」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ニドキング（第1弾。ニドリーノから進化）。あばれる（草無無）30+
        AttackKey("PMCG1-013", 0): AttackEntry(
            CoinBonusOrSelfDamage(bonus=10, self_damage=10),
            "あばれる",
            text_ja="コインを投げて「おもて」なら相手に追加10ダメージ、「うら」なら自分に10ダメージ。",
            play_text_ja="コインを投げて「おもて」なら相手に追加10ダメージ、「うら」なら自分に10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ニドキング。どくどく（草草草）20: ポケモンチェックごとに 20 の特殊などく
        AttackKey("PMCG1-013", 1): AttackEntry(
            DamageAndSpecialPoison(poison_damage=20),
            "どくどく",
            text_ja="相手に「どく」カウンターを2個のせ、ポケモンチェックごとに20の「どく」ダメージ。",
            play_text_ja="相手に「どく」カウンターを2個のせ、ポケモンチェックごとに20の「どく」ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナッシー（第2弾。タマタマから進化）。テレポート（超）: 自分の控えと入れ替える
        AttackKey("PMCG2-012", 0): AttackEntry(
            SwitchSelfWithBench(),
            "テレポート",
            text_ja="自分の控えポケモンを選び、このカードと入れ替える。",
            play_text_ja="自分の控えポケモンを選び、このカードと入れ替える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナッシー。たまなげMAX（無）20×: ついているエネルギーの数だけコインを投げる
        AttackKey("PMCG2-012", 1): AttackEntry(
            CoinsPerAttachedEnergyDamage(20),
            "たまなげMAX",
            text_ja="自分についているエネルギーの数だけコインを投げて「おもて」の数×20のダメージ。",
            play_text_ja="自分についているエネルギーの数だけコインを投げて「おもて」の数×20のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カラカラ（第2弾）。なきつく（無）: 相手がこのカードにワザで与えるダメージが 20 へる（次の自分の番の始めまで）
        AttackKey("PMCG2-029", 0): AttackEntry(
            ReduceDamageToSelf(20),
            "なきつく",
            text_ja="「なきつく」を受けた相手は、このカードにワザを使う時、与えるダメージが20へる。この状態は次の自分の番の始めに消える。",
            play_text_ja="「なきつく」を受けた相手は、このカードにワザを使う時、与えるダメージが20へる。この状態は次の自分の番の始めに消える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カラカラ。いかり（闘闘）10+
        AttackKey("PMCG2-029", 1): AttackEntry(
            DamagePlusOwnCounters(10),
            "いかり",
            text_ja="自分にのっているダメージカウンター×10のダメージを追加する。",
            play_text_ja="自分にのっているダメージカウンター×10のダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ガラガラ（第2弾。カラカラから進化）。ほねブーメラン（闘闘）30×
        AttackKey("PMCG2-032", 0): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=30),
            "ほねブーメラン",
            text_ja="コインを2枚投げて「おもて」の数×30のダメージ。",
            play_text_ja="コインを2枚投げて「おもて」の数×30のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ガラガラ。たすけをよぶ（闘闘無）: 山札から「闘」のたねポケモンを 1 匹ベンチに出す
        AttackKey("PMCG2-032", 1): AttackEntry(
            PutTypeBasicFromDeckOntoBench(EnergyType.FIGHTING),
            "たすけをよぶ",
            text_ja="自分の山札から「闘」ポケモンを1匹選んでベンチにだす。その後、その山札をよくきる。進化カードは選べない。自分のベンチに空きがなければ使えない。",
            play_text_ja="自分の山札から「闘」ポケモンを1匹選んでベンチにだす。その後、その山札をよくきる。進化カードは選べない。自分のベンチに空きがなければ使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ---- v0.35（docs/coin-groups-damage-order-v0.35.md）。kyuura データの採用（card_sources.json）。処理に使う文面は kyuura の印刷の文面
        # マチスのコラッタ（リーダーズスタジアム）。きあいだめ（無）: 次の自分の番、でんこうせっかのダメージは 2 倍（p.321 の 2 段階）
        AttackKey("PMCG5-056", 0): AttackEntry(
            MultiplyNextTurnAttackDamage(target_attack_index=1, target_attack_name="でんこうせっか"),
            "きあいだめ",
            text_ja="次の自分の番、この「マチスのコラッタ」が使う「でんこうせっか」のダメージは2倍になる。",
            play_text_ja="次の自分の番、この「マチスのコラッタ」が使う「でんこうせっか」のダメージは2倍になる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのコラッタ。でんこうせっか（無無）10+
        AttackKey("PMCG5-056", 1): AttackEntry(
            CoinBonusDamage(20),
            "でんこうせっか",
            text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのラッタ（マチスのコラッタから進化）。きあいだめ（無）: 次の自分の番、すてみタックルのダメージは 2 倍（自分へのダメージも）
        AttackKey("PMCG5-059", 0): AttackEntry(
            MultiplyNextTurnAttackDamage(target_attack_index=1, target_attack_name="すてみタックル", includes_self_damage=True),
            "きあいだめ",
            text_ja="次の自分の番、この「マチスのラッタ」が使う「すてみタックル」のダメージは2倍になる。(自分へのダメージも2倍)",
            play_text_ja="次の自分の番、この「マチスのラッタ」が使う「すてみタックル」のダメージは2倍になる。(自分へのダメージも2倍)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのラッタ。すてみタックル（無無）40: 自分にも 20
        AttackKey("PMCG5-059", 1): AttackEntry(
            DamageAndSelfDamage(20),
            "すてみタックル",
            text_ja="自分にも20ダメージ。",
            play_text_ja="自分にも20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのニョロモ（リーダーズスタジアム）。あわあわ（水）20: コインが「うら」なら、次の自分の番このワザを使えない
        AttackKey("PMCG5-022", 0): AttackEntry(
            DamageThenLockSelfOnTails(),
            "あわあわ",
            text_ja="コインを投げて「うら」なら、次の自分の番、このカードは「あわあわ」を使えない。",
            play_text_ja="コインを投げて「うら」なら、次の自分の番、このカードは「あわあわ」を使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのニョロモ。ドわすれ（水水）: 相手のワザを 1 つ選び、次の相手の番に使えなくする
        AttackKey("PMCG5-022", 1): AttackEntry(
            LockOpponentAttack(),
            "ドわすれ",
            text_ja="相手のワザを1つ選ぶ。次の相手の番、そのポケモンは、そのワザを使えない。",
            play_text_ja="相手のワザを1つ選ぶ。次の相手の番、そのポケモンは、そのワザを使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのニョロゾ（カスミのニョロモから進化）。はかいのうず（水無）20: コインが「おもて」なら相手のエネルギーカードを 1 枚トラッシュ
        AttackKey("PMCG5-029", 0): AttackEntry(
            DamageThenDiscardOpponentEnergy(on_heads=True),
            "はかいのうず",
            text_ja="コインを投げて「おもて」なら、相手についているエネルギーカードを1枚選び、トラッシュする。",
            play_text_ja="コインを投げて「おもて」なら、相手についているエネルギーカードを1枚選び、トラッシュする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのニョロゾ。ウォーターパンチ（無無無）30+: ついている「水」エネルギーの数のコインの「おもて」の数 × 10 を追加
        AttackKey("PMCG5-029", 1): AttackEntry(
            CoinsPerAttachedTypeBonusDamage(EnergyType.WATER, 10),
            "ウォーターパンチ",
            text_ja="このカードについている「水」エネルギーの数ぶんコインを投げ、「おもて」の数×10のダメージを追加する。",
            play_text_ja="このカードについている「水」エネルギーの数ぶんコインを投げ、「おもて」の数×10のダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのケンタロス（闇からの挑戦）。3ぼんのしっぽ（無）10×
        AttackKey("PMCG6-065", 0): AttackEntry(
            CoinFlipDamage(coins=3, damage_per_heads=10),
            "3ぼんのしっぽ",
            text_ja="コインを3枚投げ、「おもて」の数×10のダメージ。",
            play_text_ja="コインを3枚投げ、「おもて」の数×10のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのケンタロス。ぜんりょくとっしん（無無無）20×: 同じ 4 枚のコインの「おもて」の数 × 20 を相手に、「うら」の数 × 20 を自分に
        AttackKey("PMCG6-065", 1): AttackEntry(
            CoinsHeadsDamageTailsSelfDamage(coins=4, per=20, self_per=20),
            "ぜんりょくとっしん",
            text_ja="コインを4枚投げ、「おもて」の数×20のダメージ。その後、「うら」の数×20のダメージを自分に与える。",
            play_text_ja="コインを4枚投げ、「おもて」の数×20のダメージ。その後、「うら」の数×20のダメージを自分に与える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.36（docs/sand-attack-retreat-lock-v0.36.md）。kyuura データの採用。処理に使う文面は kyuura の印刷の文面
        # サンド（第1弾）。すなかけ（闘）10: 次の番にワザを使うときコイン。「効果は1回できえる」（AttackCoinCheck の single_use）
        AttackKey("PMCG1-051", 0): AttackEntry(
            DamageThenAttackCoinCheck(single_use=True),
            "すなかけ",
            text_ja="「すなかけ」を受けた相手は、次の番に「ワザ」を使うときに、コインをなげ、「おもて」なら成功、「うら」なら「ワザ」は失敗する。「すなかけ」の効果は1回できえる。",
            play_text_ja="「すなかけ」を受けた相手は、次の番に「ワザ」を使うときに、コインをなげ、「おもて」なら成功、「うら」なら「ワザ」は失敗する。「すなかけ」の効果は1回できえる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サンドパン（化石の秘密。サンドから進化）。みだれひっかき（闘闘）20×: コイン 3 枚の「おもて」の数 × 20（kyuura の文面は最後の「。」がない）
        AttackKey("PMCG3-036", 1): AttackEntry(
            CoinFlipDamage(coins=3, damage_per_heads=20),
            "みだれひっかき",
            text_ja="コインを3枚投げて「おもて」の数×20のダメージ",
            play_text_ja="コインを3枚投げて「おもて」の数×20のダメージ",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ブーバー（化石の秘密。第1弾のブーバー PMCG1-020 とは別のカード）。えんまく（炎）10
        AttackKey("PMCG3-008", 0): AttackEntry(
            DamageThenAttackCoinCheck(),
            "えんまく",
            text_ja="「えんまく」を受けた相手は、次の相手の番にワザを使うときにコインを投げ、「うら」ならワザは失敗する。",
            play_text_ja="「えんまく」を受けた相手は、次の相手の番にワザを使うときにコインを投げ、「うら」ならワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ブーバー（化石の秘密）。スモッグ（炎炎）20: コインが「おもて」ならどく
        AttackKey("PMCG3-008", 1): AttackEntry(
            PoisonOnHeads(),
            "スモッグ",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タッツー（化石の秘密）。えんまく（水）10
        AttackKey("PMCG3-014", 0): AttackEntry(
            DamageThenAttackCoinCheck(),
            "えんまく",
            text_ja="「えんまく」を受けた相手は、次の相手の番にワザを使うときにコインを投げ、「うら」ならワザは失敗する。",
            play_text_ja="「えんまく」を受けた相手は、次の相手の番にワザを使うときにコインを投げ、「うら」ならワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのタッツー（リーダーズスタジアム）。えんまく（水水）20
        AttackKey("PMCG5-025", 1): AttackEntry(
            DamageThenAttackCoinCheck(),
            "えんまく",
            text_ja="このワザを受けたポケモンは、次の相手の番にワザを使う時にコインを投げ、「うら」ならワザは失敗する。",
            play_text_ja="このワザを受けたポケモンは、次の相手の番にワザを使う時にコインを投げ、「うら」ならワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのポッポ（闇からの挑戦）。すなかけ（無無無）20（サンドの「すなかけ」とは別の文面。1回では消えない）
        AttackKey("PMCG6-062", 1): AttackEntry(
            DamageThenAttackCoinCheck(),
            "すなかけ",
            text_ja="このワザを受けた相手は、次の相手の番でワザを使う時にコインを投げ、「うら」なら、ワザは失敗する。",
            play_text_ja="このワザを受けた相手は、次の相手の番でワザを使う時にコインを投げ、「うら」なら、ワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいサンダース（ロケット団。イーブイから進化）。サンダーフラッシュ（雷）20
        AttackKey("PMCG4-029", 0): AttackEntry(
            DamageThenAttackCoinCheck(),
            "サンダーフラッシュ",
            text_ja="このワザを受けたポケモンは、次の相手の番にワザを使うときにコインを投げ、「うら」ならワザは失敗する。",
            play_text_ja="このワザを受けたポケモンは、次の相手の番にワザを使うときにコインを投げ、「うら」ならワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいサンダース。サンダーアタック（雷雷無）30: 1 枚のコインで「おもて」ならマヒ、「うら」なら自分に 10（投げ直さない。マチスのライチュウの
        # 「でんきタックル」と同じ型。説明は「自分に」と「自分にも」の違いだけ）
        AttackKey("PMCG4-029", 1): AttackEntry(
            DamageThenParalyzeOrSelfDamage(10),
            "サンダーアタック",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。「うら」なら自分に10ダメージ。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。「うら」なら自分に10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのパウワウ（リーダーズスタジアム）。アイスバーン（水）10: 次の相手の番に「にげる」ことができない
        AttackKey("PMCG5-023", 0): AttackEntry(
            DamageThenRetreatLock(),
            "アイスバーン",
            text_ja="このワザを受けた相手は、次の相手の番に「にげる」ことができない。",
            play_text_ja="このワザを受けた相手は、次の相手の番に「にげる」ことができない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのパウワウ。しんきろう（水無）10
        AttackKey("PMCG5-023", 1): AttackEntry(
            DamageThenAttackCoinCheck(),
            "しんきろう",
            text_ja="このワザを受けた相手は、次の相手の番でワザを使う時にコインを投げ、「うら」なら、ワザは失敗する。",
            play_text_ja="このワザを受けた相手は、次の相手の番でワザを使う時にコインを投げ、「うら」なら、ワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのオニドリル（リーダーズスタジアム。マチスのオニスズメから進化）。マシンガンドリル（無無）10×: コイン 5 枚の「おもて」の数 × 10
        AttackKey("PMCG5-064", 0): AttackEntry(
            CoinFlipDamage(coins=5, damage_per_heads=10),
            "マシンガンドリル",
            text_ja="コインを5枚投げ、「おもて」の数×10のダメージ。",
            play_text_ja="コインを5枚投げ、「おもて」の数×10のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのオニドリル。わしづかみ（無無無）30: 次の相手の番に「にげる」ことができない
        AttackKey("PMCG5-064", 1): AttackEntry(
            DamageThenRetreatLock(),
            "わしづかみ",
            text_ja="このワザを受けた相手は、次の相手の番に「にげる」ことができない。",
            play_text_ja="このワザを受けた相手は、次の相手の番に「にげる」ことができない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのドガース（闇からの挑戦。第1弾・第4弾のドガースとは別のカード）。えんまく（草）10
        AttackKey("PMCG6-015", 0): AttackEntry(
            DamageThenAttackCoinCheck(),
            "えんまく",
            text_ja="このワザを受けた相手は、次の相手の番でワザを使う時にコインを投げ、「うら」なら、ワザは失敗する。",
            play_text_ja="このワザを受けた相手は、次の相手の番でワザを使う時にコインを投げ、「うら」なら、ワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのドガース。くもがくれガス（草無）30: コインが「おもて」なら、ダメージを与えた後、自分とついているカードを山札にもどして切る
        AttackKey("PMCG6-015", 1): AttackEntry(
            DamageThenReturnSelfToDeckOnHeads(),
            "くもがくれガス",
            text_ja="コインを投げて「おもて」なら、ダメージを与えた後、自分と、自分についているすべてのカードを山札にもどす。その後、その山札をよく切る。",
            play_text_ja="コインを投げて「おもて」なら、ダメージを与えた後、自分と、自分についているすべてのカードを山札にもどす。その後、その山札をよく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのマダツボミ（リーダーズスタジアム。第2弾のマダツボミ PMCG2-005 とは別のカード）。へなへなタックル（無）20: 自分にも 10
        AttackKey("PMCG5-005", 0): AttackEntry(
            DamageAndSelfDamage(10),
            "へなへなタックル",
            text_ja="自分にも10ダメージ。",
            play_text_ja="自分にも10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.37（docs/fifteen-reused-effects-v0.37.md）。kyuura データの採用（ベトベター PMCG3-003 は v0.8 の過去の原典照合の記録）。処理に使う文面は
        # kyuura の印刷の文面（ベトベターは照合の記録の最新の説明）
        # サイホーン（第2弾）。にらみつける（無）: コインの「おもて」で、次の相手の番にワザを使えない（v0.31 のイーブイの「しっぽをふる」と同じ型。CannotAttack）
        AttackKey("PMCG2-030", 0): AttackEntry(
            CannotAttackOnHeads(),
            "にらみつける",
            text_ja="コインを投げて「おもて」なら「にらみつける」を受けた相手の対戦ポケモンは、次の相手の番にワザをつかえない。",
            play_text_ja="コインを投げて「おもて」なら「にらみつける」を受けた相手の対戦ポケモンは、次の相手の番にワザをつかえない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # 化石の秘密のベトベター（v0.8 の参照カード。照合の記録 card_verification.json の p.47）。ベトベト（無）10: コインが「おもて」ならマヒ
        AttackKey("PMCG3-003", 0): AttackEntry(
            ParalyzeOnHeads(),
            "ベトベト",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source='P43 p.47',
        ),
        # 化石の秘密のベトベター。ちいさくなる（草）: 照合の記録の最新の説明（kyuura の LD-PMCG3-003-ATK1 と同じ）。p.321 の 8 段階（DamageReduction）
        AttackKey("PMCG3-003", 1): AttackEntry(
            ReduceDamageNextTurn(amount=20),
            "ちいさくなる",
            text_ja="次の相手の番でこのカードが受けるダメージは20へる。(ダメージ以外の効果はそのまま)",
            play_text_ja="次の相手の番、このカードがワザによって受けるダメージは「-20」される。（ダメージ以外の効果は受ける）",
            source='P43 p.47',
        ),
        # イーブイ（ロケット団）。すなかけ（無無）10: 次の相手の番にワザを使うときコイン（v0.36 の AttackCoinCheck。カスミのタッツーの「えんまく」と同じ文面。1回では消えない）
        AttackKey("PMCG4-049", 1): AttackEntry(
            DamageThenAttackCoinCheck(),
            "すなかけ",
            text_ja="このワザを受けたポケモンは、次の相手の番にワザを使う時にコインを投げ、「うら」ならワザは失敗する。",
            play_text_ja="このワザを受けたポケモンは、次の相手の番にワザを使う時にコインを投げ、「うら」ならワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのサンド（リーダーズスタジアム）。すなじごく（闘闘）20: 次の相手の番に「にげる」ことができない（v0.36 の CannotRetreat。アイスバーンと同じ文面）
        AttackKey("PMCG5-043", 0): AttackEntry(
            DamageThenRetreatLock(),
            "すなじごく",
            text_ja="このワザを受けた相手は、次の相手の番に「にげる」ことができない。",
            play_text_ja="このワザを受けた相手は、次の相手の番に「にげる」ことができない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのスリープ（闇からの挑戦）。あんじをかける（超）: コインの「おもて」で、次の相手の番にワザを使えない（CannotAttack）
        AttackKey("PMCG6-045", 0): AttackEntry(
            CannotAttackOnHeads(),
            "あんじをかける",
            text_ja="コインを投げて「おもて」なら、次の相手の番、このワザを受けた相手は、ワザを使えない。",
            play_text_ja="コインを投げて「おもて」なら、次の相手の番、このワザを受けた相手は、ワザを使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ライチュウ（第1弾。ピカチュウから進化）。こうそくいどう（雷無無）20: コインの「おもて」で次の相手の番のワザをうけない（AttackBarrier。v0.34 のギャロップと同じ型。主語のない書き方は SELF_BARRIER_ON_HEADS_TEXTS）
        AttackKey("PMCG1-038", 0): AttackEntry(
            DamageThenSelfBarrierOnHeads(),
            "こうそくいどう",
            text_ja="コインを投げて「おもて」なら、次の相手の番の「ワザ」をうけない。",
            play_text_ja="コインを投げて「おもて」なら、次の相手の番の「ワザ」をうけない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ライチュウ。かみなり（雷雷雷無）60: コインの「うら」で自分にも 30（サンダー PMCG1-042 の「かみなり」と同じ文面）
        AttackKey("PMCG1-038", 1): AttackEntry(
            SelfDamageOnTails(self_damage=30),
            "かみなり",
            text_ja="コインを投げて「うら」なら、自分にも30ダメージ。",
            play_text_ja="コインを投げて「うら」なら、自分にも30ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ダグトリオ（第1弾。ディグダから進化）。じしん（闘闘闘闘）70: 自分の控えポケモン全員にも 10（説明に「弱点・抵抗力」に関係なくがない。JS1）
        AttackKey("PMCG1-056", 1): AttackEntry(
            DamageAndOwnBenchDamage(10, weakness_resistance_stated=False),
            "じしん",
            text_ja="自分の控えポケモン全員にも10ダメージ。",
            play_text_ja="自分の控えポケモン全員にも10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ニョロゾ（第1弾。ニョロモから進化）。ドわすれ（水水）: 相手のワザを 1 つ選んで次の相手の番に使えなくする（v0.35 の CannotUseAttack。書き方は LOCK_OPPONENT_ATTACK_TEXTS）
        AttackKey("PMCG1-028", 0): AttackEntry(
            LockOpponentAttack(),
            "ドわすれ",
            text_ja="相手の対戦ポケモンの「ワザ」を1つ選ぶ。次の相手の番でその「ワザ」はつかえない。",
            play_text_ja="相手の対戦ポケモンの「ワザ」を1つ選ぶ。次の相手の番でその「ワザ」はつかえない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ニョロゾ。おうふくびんた（水水無）30×: コイン 2 枚の「おもて」の数 × 30（説明の「表の出た数」は「おもて」の数）
        AttackKey("PMCG1-028", 1): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=30),
            "おうふくびんた",
            text_ja="コインを2枚投げて、表の出た数×30のダメージをあたえる。",
            play_text_ja="コインを2枚投げて、表の出た数×30のダメージをあたえる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ニョロボン（第1弾。ニョロゾから進化）。みずでっぽう（水水無）30+: ニョロモの「みずでっぽう」と同じ文面で、必要なエネルギーに無色がある（v0.31 の HC4。読み方で数が変わるときだけ止める）
        AttackKey("PMCG1-033", 0): AttackEntry(
            ExtraEnergyDamageMixed(energy_type=EnergyType.WATER, per_energy=10, max_extra=2),
            "みずでっぽう",
            text_ja="「水」エネルギーを1つ追加すると、10ダメージ追加できる。(追加は2つまで)",
            play_text_ja="「水」エネルギーを1つ追加すると、10ダメージ追加できる。(追加は2つまで)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ニョロボン。うずしお（水水無無）40: 相手のエネルギーカードを 1 枚トラッシュ（ハクリューの「はかいこうせん」と同じ文面。選ぶのはワザを使ったプレイヤー）
        AttackKey("PMCG1-033", 1): AttackEntry(
            DamageThenDiscardOpponentEnergy(on_heads=False),
            "うずしお",
            text_ja="相手の対戦ポケモンのエネルギーカードを1枚はがしてすてる。",
            play_text_ja="相手の対戦ポケモンのエネルギーカードを1枚はがしてすてる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # アーボ（化石の秘密。ロケット団のアーボ PMCG4-001 とは別のカード）。どくえき（草）: ダメージなし、コインの「おもて」でどく
        AttackKey("PMCG3-001", 0): AttackEntry(
            PoisonOnHeadsWithoutDamage(),
            "どくえき",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # アーボ（化石の秘密）。まきつく（草無）20: コインの「おもて」でマヒ
        AttackKey("PMCG3-001", 1): AttackEntry(
            ParalyzeOnHeads(),
            "まきつく",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのイワーク（リーダーズスタジアム。kyuura の CC-PMCG5-048-P200 は最新の説明が印刷の文面と同じ）。うなりごえ（無）: ダメージなし、コインの「おもて」でマヒ
        AttackKey("PMCG5-048", 0): AttackEntry(
            ParalyzeOnHeadsWithoutDamage(),
            "うなりごえ",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ニャース（第2弾。サカキのニャース PMCG6-063 とは別の名前のカード）。ねこにこばん（無無）10: ダメージ → コインの「おもて」で 1 枚引く
        AttackKey("PMCG2-036", 0): AttackEntry(
            DamageThenDrawOnHeads(count=1),
            "ねこにこばん",
            text_ja="コインを投げて「おもて」なら、自分の山札の上からカードを1枚ひいて、手札に加える。",
            play_text_ja="コインを投げて「おもて」なら、自分の山札の上からカードを1枚ひいて、手札に加える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのモンジャラ（闇からの挑戦。第1弾のモンジャラ PMCG1-007 とは別の名前のカード）。ねむりごな（草）10: ダメージのあとコインなしでねむり（v0.9 のゴーストの「あくむ」と同じ型）
        AttackKey("PMCG6-009", 0): AttackEntry(
            SleepOpponent(),
            "ねむりごな",
            text_ja="相手を「ねむり」状態にする。",
            play_text_ja="相手を「ねむり」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのモンジャラ。つるでさがす（草無）: ダメージなし、コインの「おもて」で 2 枚引く
        AttackKey("PMCG6-009", 1): AttackEntry(
            DrawOnHeads(count=2),
            "つるでさがす",
            text_ja="コインを投げて「おもて」なら、山札からカードを2枚引く。",
            play_text_ja="コインを投げて「おもて」なら、山札からカードを2枚引く。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのコイキング（リーダーズスタジアム）。しんだふり（無）: ダメージなし、コインの「おもて」で次の相手の番にワザによるダメージや効果を受けない（AttackBarrier）
        AttackKey("PMCG5-028", 0): AttackEntry(
            SelfBarrierOnHeads(),
            "しんだふり",
            text_ja="コインを投げて「おもて」なら、次の相手の番、このカードはワザによるダメージや効果を受けない。",
            play_text_ja="コインを投げて「おもて」なら、次の相手の番、このカードはワザによるダメージや効果を受けない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ペルシアン（第2弾。ニャースから進化）。かみつく（無無無）30: ダメージ → 相手がこのカードに与えるワザのダメージが 10 へる（v0.34 のなきつくと同じ ReducedDamageToSource）
        AttackKey("PMCG2-039", 1): AttackEntry(
            DamageThenReduceDamageToSelf(10),
            "かみつく",
            text_ja="「かみつく」を受けた【相手】は、このカードにワザを使う時、あたえるダメージが10へる。この状態は次の自分の番の始めに消える。",
            play_text_ja="「かみつく」を受けた【相手】は、このカードにワザを使う時、あたえるダメージが10へる。この状態は次の自分の番の始めに消える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.38（docs/bench-switch-combined-v0.38.md）。kyuura データの採用（処理に使う文面は kyuura の印刷の文面）
        # フリーザー（化石の秘密）。フリーズドライ（水水水）30: コインの「おもて」でマヒ
        AttackKey("PMCG3-023", 0): AttackEntry(
            ParalyzeOnHeads(),
            "フリーズドライ",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # フリーザー。ふぶき（水水水水）50: 1 枚のコインで「おもて」なら相手の控え全員、「うら」なら自分の控え全員に 10（弱点・抵抗力なし）
        AttackKey("PMCG3-023", 1): AttackEntry(
            DamageThenCoinBenchDamageEitherSide(10),
            "ふぶき",
            text_ja="コインを投げて「おもて」なら相手の控えポケモン全員に、「うら」なら自分の控えポケモン全員に、(「弱点・抵抗力」に関係なく)それぞれ10ダメージ。",
            play_text_ja="コインを投げて「おもて」なら相手の控えポケモン全員に、「うら」なら自分の控えポケモン全員に、(「弱点・抵抗力」に関係なく)それぞれ10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サワムラー（化石の秘密）。のびるキック（闘闘）: 相手の控えを 1 匹選んで 20（弱点・抵抗力なし）。相手に控えがいなければ使えない
        AttackKey("PMCG3-039", 0): AttackEntry(
            ChooseOpponentBenchDamage(20, requires_bench=True),
            "のびるキック",
            text_ja="相手の控えポケモンを1匹選び、そのポケモンに「弱点・抵抗力」に関係なく20ダメージ。相手に控えポケモンがいないとき、このワザは使えない。",
            play_text_ja="相手の控えポケモンを1匹選び、そのポケモンに「弱点・抵抗力」に関係なく20ダメージ。相手に控えポケモンがいないとき、このワザは使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのモンジャラ。のびるつる（草草無）: 相手の控えを 1 匹選んで 20（弱点・抵抗力なし）。使えない、の記述はない（控えがいなければ何もしない）
        AttackKey("PMCG5-006", 1): AttackEntry(
            ChooseOpponentBenchDamage(20, requires_bench=False),
            "のびるつる",
            text_ja="相手の控えポケモンから1匹を選び、(「弱点・抵抗力」に関係なく)20ダメージ。",
            play_text_ja="相手の控えポケモンから1匹を選び、(「弱点・抵抗力」に関係なく)20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのロコン（リーダーズスタジアム。タケシのロコン PMCG5-018 とは同じ名前の別のカード）。みつめる（無）: ダメージなし、ねむり
        AttackKey("PMCG5-017", 0): AttackEntry(
            PutToSleep(),
            "みつめる",
            text_ja="相手を「ねむり」状態にする。",
            play_text_ja="相手を「ねむり」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのロコン。ほのおのわ（炎炎）20: 相手に控えがいれば 1 匹を選んで 10（弱点・抵抗力なし）
        AttackKey("PMCG5-017", 1): AttackEntry(
            DamageThenChosenBenchDamage(10),
            "ほのおのわ",
            text_ja="相手に控えポケモンがいれば、1匹を選び、「弱点・抵抗力」に関係なく、10ダメージ。",
            play_text_ja="相手に控えポケモンがいれば、1匹を選び、「弱点・抵抗力」に関係なく、10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのゴルバット（タケシのズバットから進化）。かいてんひこう（無無無）: 相手と相手の控え全員に 10（弱点・抵抗力なし）
        AttackKey("PMCG5-008", 1): AttackEntry(
            SpreadDamage(10),
            "かいてんひこう",
            text_ja="相手と相手の控えポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            play_text_ja="相手と相手の控えポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # アーボック（化石の秘密。アーボから進化）。いかくこうげき（草）10: コインの「おもて」で相手が選ぶ控えと入れ替える
        AttackKey("PMCG3-004", 0): AttackEntry(
            DamageThenForceSwitchOnHeads(),
            "いかくこうげき",
            text_ja="コインを投げて「おもて」なら、相手の対戦ポケモンを控えポケモンと入れ替える。入れ替わるポケモンは相手プレイヤーが選ぶ。相手に控えポケモンがいない時、この入れ替えは起こらない。",
            play_text_ja="コインを投げて「おもて」なら、相手の対戦ポケモンを控えポケモンと入れ替える。入れ替わるポケモンは相手プレイヤーが選ぶ。相手に控えポケモンがいない時、この入れ替えは起こらない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # アーボック。どくのきば（草草無）20: コインなしでどく
        AttackKey("PMCG3-004", 1): AttackEntry(
            PoisonOpponent(),
            "どくのきば",
            text_ja="相手を「どく」状態にする。",
            play_text_ja="相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サイドン（第2弾。サイホーンから進化）。げきとつ（闘闘闘闘）50: 相手が選ぶ控えと入れ替え → 自分にも 20
        AttackKey("PMCG2-033", 1): AttackEntry(
            DamageThenForceSwitchThenSelfDamage(20),
            "げきとつ",
            text_ja="相手の対戦ポケモンを控えポケモンと入れ替える。控えポケモンは相手プレイヤーがえらぶ。相手プレイヤーに控えポケモンがいないときには入れ替えはおこらない。その後、自分にも20ダメージ。",
            play_text_ja="相手の対戦ポケモンを控えポケモンと入れ替える。控えポケモンは相手プレイヤーがえらぶ。相手プレイヤーに控えポケモンがいないときには入れ替えはおこらない。その後、自分にも20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのポニータ（闇からの挑戦）。けりにげ（無無）20: コインの「おもて」で自分の控えを選んで入れ替える
        AttackKey("PMCG6-028", 0): AttackEntry(
            DamageThenSelfSwitchOnHeads(),
            "けりにげ",
            text_ja="コインを投げて「おもて」なら、自分の控えポケモンを1匹選び、このカードと入れ替える。",
            play_text_ja="コインを投げて「おもて」なら、自分の控えポケモンを1匹選び、このカードと入れ替える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのギャロップ（カツラのポニータから進化）。ふみあらす（炎無無）30+: 1 枚のコインの「おもて」で相手に + 10 と相手の控え全員に 10
        AttackKey("PMCG6-030", 1): AttackEntry(
            CoinBonusDamageAndBenchDamage(bonus=10, bench_damage=10),
            "ふみあらす",
            text_ja="コインを投げて「おもて」なら、相手に10ダメージを追加し、相手の控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            play_text_ja="コインを投げて「おもて」なら、相手に10ダメージを追加し、相手の控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのピジョン（闇からの挑戦。キョウのポッポから進化）。クイックターン（無無無）30×: コイン 2 枚の「おもて」の数 × 30
        AttackKey("PMCG6-070", 0): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=30),
            "クイックターン",
            text_ja="コインを2枚投げ、「おもて」の数×30のダメージ。",
            play_text_ja="コインを2枚投げ、「おもて」の数×30のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのピジョン。こうそくひこう（無無無無）10+: 1 枚のコインの「おもて」で + 30 と、次の相手の番にワザによるダメージや効果を受けない
        AttackKey("PMCG6-070", 1): AttackEntry(
            CoinBonusDamageAndSelfBarrier(30),
            "こうそくひこう",
            text_ja="コインを投げて「おもて」なら、30ダメージを追加する。その場合、このカードは、次の相手の番、相手のワザによるダメージや効果を受けない。",
            play_text_ja="コインを投げて「おもて」なら、30ダメージを追加する。その場合、このカードは、次の相手の番、相手のワザによるダメージや効果を受けない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのビードル。きけんなはり（草無）10: 1 枚のコインで「おもて」ならどく、「うら」ならマヒ
        AttackKey("PMCG6-001", 1): AttackEntry(
            DamageThenPoisonOrParalyze(),
            "きけんなはり",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態に、「うら」なら「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態に、「うら」なら「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのニドリーナ（闇からの挑戦。サカキのニドラン♀から進化）。どくばりタックル（草無）30: 自分にも 20 → コインの「おもて」でどく
        AttackKey("PMCG6-012", 0): AttackEntry(
            DamageAndSelfDamageThenPoisonOnHeads(20),
            "どくばりタックル",
            text_ja="自分にも20ダメージ。コインを投げて「おもて」なら、相手を「どく」状態にする。",
            play_text_ja="自分にも20ダメージ。コインを投げて「おもて」なら、相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのニドリーナ。のしかかり（草無無）20: コインの「おもて」でマヒ
        AttackKey("PMCG6-012", 1): AttackEntry(
            ParalyzeOnHeads(),
            "のしかかり",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのポリゴン。バリアアタック（無無）20: 次の相手の番、このカードがワザによって受けるダメージは - 10（8 段階）
        AttackKey("PMCG6-066", 1): AttackEntry(
            DamageThenReduceDamageNextTurn(10),
            "バリアアタック",
            text_ja="次の相手の番、このカードがワザによって受けるダメージは「-10」される。",
            play_text_ja="次の相手の番、このカードがワザによって受けるダメージは「-10」される。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ケーシィ（ロケット団。第1弾のケーシィ PMCG1-043 とは別のカード）。いなくなる（超）: カウンターをとりのぞき、ついているカードをトラッシュ → 自分を山札にもどして切る
        AttackKey("PMCG4-031", 0): AttackEntry(
            DiscardAttachedAndReturnSelfToDeck(),
            "いなくなる",
            text_ja="このカードにのっているダメージカウンターをすべてとりのぞき、ついているカードをすべてトラッシュする。その後、このカードを山札にもどし、その山札をよく切る。",
            play_text_ja="このカードにのっているダメージカウンターをすべてとりのぞき、ついているカードをすべてトラッシュする。その後、このカードを山札にもどし、その山札をよく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ケーシィ（ロケット団）。ねんりき（超）10: コインの「おもて」でマヒ
        AttackKey("PMCG4-031", 1): AttackEntry(
            ParalyzeOnHeads(),
            "ねんりき",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのポッポ（PMCG6-067）。でんれい（無）: 自分とついているカードを山札にもどす → 控えから対戦ポケモンを出す → 「キョウのポッポ」以外のポケモンを見せて手札に → 切る
        AttackKey("PMCG6-067", 0): AttackEntry(
            ReturnSelfToDeckThenSearchPokemon(("キョウのポッポ",)),
            "でんれい",
            text_ja="自分と、自分についているすべてのカードを山札にもどす。(ベンチから、かわりの対戦ポケモンを出す)。その後、自分の山札から「キョウのポッポ」以外の「ポケモン」を1枚選び出し、相手に見せてから手札に加え、その山札をよく切る。",
            play_text_ja="自分と、自分についているすべてのカードを山札にもどす。(ベンチから、かわりの対戦ポケモンを出す)。その後、自分の山札から「キョウのポッポ」以外の「ポケモン」を1枚選び出し、相手に見せてから手札に加え、その山札をよく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.39（docs/selfdestruct-spread-count-v0.39.md）。kyuura データの採用（処理に使う文面は kyuura の印刷の文面）
        # コイル（第1弾）。でんじは（雷）10: コインの「おもて」でマヒ（第4弾のコイル PMCG4-026 とは同じ名前の別のカード）
        AttackKey("PMCG1-036", 0): AttackEntry(
            ParalyzeOnHeads(),
            "でんじは",
            text_ja="コインを投げて「おもて」がでたら「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」がでたら「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # コイル（第1弾）。じばく（雷無）40: 自分にも 40、お互いの控え全員に 10（弱点・抵抗力を書かない。JS1）
        AttackKey("PMCG1-036", 1): AttackEntry(
            SelfDestruct(self_damage=40, bench_damage=10, weakness_resistance_stated=False),
            "じばく",
            text_ja="自分と相手に40ダメージをあたえ、お互いの控えポケモン全員にも10ダメージ。",
            play_text_ja="自分と相手に40ダメージをあたえ、お互いの控えポケモン全員にも10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # レアコイル（第1弾。コイルから進化）。でんじは（雷雷無）30
        AttackKey("PMCG1-039", 0): AttackEntry(
            ParalyzeOnHeads(),
            "でんじは",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # レアコイル（第1弾）。じばく（雷雷無無）80: 自分にも 80、お互いの控え全員に 20（JS1）
        AttackKey("PMCG1-039", 1): AttackEntry(
            SelfDestruct(self_damage=80, bench_damage=20, weakness_resistance_stated=False),
            "じばく",
            text_ja="自分と相手に80ダメージをあたえ、お互いの控えポケモン全員にも20ダメージ。",
            play_text_ja="自分と相手に80ダメージをあたえ、お互いの控えポケモン全員にも20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マタドガス（化石の秘密。ドガースから進化）。スモッグ（草草）20
        AttackKey("PMCG3-006", 0): AttackEntry(
            PoisonOnHeads(),
            "スモッグ",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マタドガス（化石の秘密）。じばく（草草無）60: 自分にも 60、お互いの控え全員に 10（弱点・抵抗力に関係なく）
        AttackKey("PMCG3-006", 1): AttackEntry(
            SelfDestruct(self_damage=60, bench_damage=10, weakness_resistance_stated=True),
            "じばく",
            text_ja="自分にも60ダメージ。お互いの控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            play_text_ja="自分にも60ダメージ。お互いの控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # レアコイル（化石の秘密。コイルから進化）。ソニックブーム（雷無）20: 相手の弱点・抵抗力の影響を受けない
        AttackKey("PMCG3-025", 0): AttackEntry(
            DamageIgnoringWeaknessResistance(),
            "ソニックブーム",
            text_ja="この「ソニックブーム」のダメージは、相手の「弱点・抵抗力」の影響を受けない。",
            play_text_ja="この「ソニックブーム」のダメージは、相手の「弱点・抵抗力」の影響を受けない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # レアコイル（化石の秘密）。じばく（雷雷雷雷）100: 自分にも 100、お互いの控え全員に 20（弱点・抵抗力に関係なく）
        AttackKey("PMCG3-025", 1): AttackEntry(
            SelfDestruct(self_damage=100, bench_damage=20, weakness_resistance_stated=True),
            "じばく",
            text_ja="自分にも100ダメージ。お互いの控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ20ダメージ。",
            play_text_ja="自分にも100ダメージ。お互いの控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ピカチュウ（第2弾。第1弾のピカチュウ PMCG1-035 とは別のカード）。スパーク（雷雷）20: 相手の控えから 1 匹を選んで 10（JS1 は選んだ控えだけ）
        AttackKey("PMCG2-024", 0): AttackEntry(
            DamageThenChosenBenchDamage(bench_damage=10, weakness_resistance_stated=False),
            "スパーク",
            text_ja="相手の控えポケモンから1匹選び、そのポケモンにも10ダメージ。相手の控えポケモンが1匹もいないときにはこの効果はない。",
            play_text_ja="相手の控えポケモンから1匹選び、そのポケモンにも10ダメージ。相手の控えポケモンが1匹もいないときにはこの効果はない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ライチュウ（化石の秘密。ピカチュウから進化。第1弾のライチュウ PMCG1-038 とは別のカード）。ギガスパーク（雷雷雷雷）30: 相手の控えから最大 3 匹（0 匹は GS1）
        AttackKey("PMCG3-024", 0): AttackEntry(
            DamageThenChosenBenchTargets(max_targets=3, bench_damage=10),
            "ギガスパーク",
            text_ja="相手の控えポケモンから最大3匹を選び、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            play_text_ja="相手の控えポケモンから最大3匹を選び、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マルマイン（第2弾。ビリリダマから進化）。ビリビリ（雷雷雷）20: 相手の対戦ポケモンと同じタイプのお互いの控え全員に 10（JS1）
        AttackKey("PMCG2-025", 1): AttackEntry(
            DamageThenSameTypeBenchDamage(bench_damage=10),
            "ビリビリ",
            text_ja="相手の対戦ポケモンと同じ色の控えポケモン全員にそれぞれ10ダメージ。(自分の控えポケモンも含まれる)",
            play_text_ja="相手の対戦ポケモンと同じ色の控えポケモン全員にそれぞれ10ダメージ。(自分の控えポケモンも含まれる)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのドガース（闇からの挑戦。キョウのドガース PMCG6-015 とは同じ名前の別のカード）。おならガス（草）10
        AttackKey("PMCG6-008", 0): AttackEntry(
            DamageThenCoinBenchDamageBothSides(bench_damage=10),
            "おならガス",
            text_ja="コインを投げて「おもて」なら、お互いの控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            play_text_ja="コインを投げて「おもて」なら、お互いの控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのニョロボン（闇からの挑戦。カスミのニョロゾから進化する 2 進化）。ウォーターリング（水水無無）30
        AttackKey("PMCG6-039", 0): AttackEntry(
            DamageThenOtherTypeBenchDamageBothSides(excluded_type=EnergyType.WATER, bench_damage=10),
            "ウォーターリング",
            text_ja="お互いのベンチにいる、「水」ポケモン以外のポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            play_text_ja="お互いのベンチにいる、「水」ポケモン以外のポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # コイル（ロケット団）。ちょくれつじりょく（雷無）10+: 自分のベンチの「コイル」「レアコイル」「わるいレアコイル」1 匹につき + 10
        AttackKey("PMCG4-026", 1): AttackEntry(
            DamagePlusPokemonCount(per=10, scope="own_bench", names=("コイル", "レアコイル", "わるいレアコイル")),
            "ちょくれつじりょく",
            text_ja="自分のベンチにいる「コイル」「レアコイル」「わるいレアコイル」1匹につき、10ダメージを追加する。",
            play_text_ja="自分のベンチにいる「コイル」「レアコイル」「わるいレアコイル」1匹につき、10ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # プクリン（第2弾。プリンから進化）。こもりうた（無）: ダメージなしでねむり
        AttackKey("PMCG2-045", 0): AttackEntry(
            PutToSleep(),
            "こもりうた",
            text_ja="相手を「ねむり」状態にする。",
            play_text_ja="相手を「ねむり」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # プクリン（第2弾）。ともだちのわ（無無無）10+: 自分の控えポケモンの数 × 10 を追加
        AttackKey("PMCG2-045", 1): AttackEntry(
            DamagePlusPokemonCount(per=10, scope="own_bench"),
            "ともだちのわ",
            text_ja="自分の控えポケモンの数×10ダメージを追加する。",
            play_text_ja="自分の控えポケモンの数×10ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ニドクイン（第2弾。ニドリーナから進化する 2 進化）。ラブラブアタック（草無）20+: 自分の場の「ニドキング」の数 × 20 を追加
        AttackKey("PMCG2-013", 0): AttackEntry(
            DamagePlusPokemonCount(per=20, scope="own_in_play", names=("ニドキング",)),
            "ラブラブアタック",
            text_ja="自分の場に出ている「ニドキング」の数×20のダメージを追加する。",
            play_text_ja="自分の場に出ている「ニドキング」の数×20のダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのマタドガス（闇からの挑戦。キョウのドガースから進化）。とつぜんばくはつ（草草）10+: 同じコインの「おもて」で + 30 と自分にも 30
        AttackKey("PMCG6-016", 0): AttackEntry(
            CoinBonusDamageAndSelfDamage(bonus=30, self_damage=30),
            "とつぜんばくはつ",
            text_ja="コインを投げて「おもて」なら、30ダメージを追加して、自分にも30ダメージ。",
            play_text_ja="コインを投げて「おもて」なら、30ダメージを追加して、自分にも30ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのマタドガス。どくどくガス（草草無）20: コインの「おもて」で 20 の特殊などく（TP3 は既存のまま）
        AttackKey("PMCG6-016", 1): AttackEntry(
            DamageThenSpecialPoisonOnHeads(poison_damage=20),
            "どくどくガス",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。このワザによって「どく」状態になったポケモンがポケモンチェックで受ける「どく」のダメージは、20ダメージ。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。このワザによって「どく」状態になったポケモンがポケモンチェックで受ける「どく」のダメージは、20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ポッポ（第1弾）。かぜおこし（無無）10: 相手が選ぶ控えと入れ替える（v0.4d のふきとばしと同じ処理。pcg-search.com・p.159 のワザの名前は「ふきとばし」で、kyuura の名前と違う。kyuura への報告事項）
        AttackKey("PMCG1-059", 0): AttackEntry(
            DamageAndForceSwitch(),
            "かぜおこし",
            text_ja="相手の対戦ポケモンを控えポケモンと入れ替える。入れ替えは相手が行う。相手の控えポケモンがいないときには、ダメージだけをあたえる。",
            play_text_ja="相手の対戦ポケモンを控えポケモンと入れ替える。入れ替えは相手が行う。相手の控えポケモンがいないときには、ダメージだけをあたえる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのパラス（リーダーズスタジアム）。きけんなほうし（草草）: 同じコインの「おもて」でどくと相手の控え全員に 10
        AttackKey("PMCG5-004", 1): AttackEntry(
            CoinPoisonAndBenchDamage(bench_damage=10),
            "きけんなほうし",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にして、相手の控えポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にして、相手の控えポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.40（docs/count-condition-switch-return-v0.40.md）。kyuura データの採用（処理に使う文面は kyuura の印刷の文面）。
        # キョウのズバット（闇からの挑戦）。むれでおそう（草無）10×: のぞむなら山札から「キョウのズバット」を好きなだけベンチに出し（出したら 1 回切る）、自分の場の数 × 10
        AttackKey("PMCG6-005", 0): AttackEntry(
            GroupAttackFromDeck(names=("キョウのズバット",), per=10),
            "むれでおそう",
            text_ja="自分の場にいる「キョウのズバット」の数×10ダメージ。のぞむなら、ダメージを与える前に、自分の山札から「キョウのズバット」を好きなだけ選び出し、ベンチに出してよい。その場合は、その山札をよく切る。",
            play_text_ja="自分の場にいる「キョウのズバット」の数×10ダメージ。のぞむなら、ダメージを与える前に、自分の山札から「キョウのズバット」を好きなだけ選び出し、ベンチに出してよい。その場合は、その山札をよく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのゴルバット（闇からの挑戦）。ひどいおんぱ（草草草）30: コインの「おもて」でこんらん（v0.3c の ConfuseOnHeads）
        AttackKey("PMCG6-014", 1): AttackEntry(
            ConfuseOnHeads(),
            "ひどいおんぱ",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいマタドガス（ロケット団。ドガースから進化）。みんなでばくはつ（草無）20×: お互いの場の名前の合うポケモンの数 × 20 → 名前の合うポケモンそれぞれに 20
        AttackKey("PMCG4-011", 0): AttackEntry(
            NamedPokemonExplosion(names=("ドガース", "マタドガス", "わるいマタドガス"), per=20, each=20),
            "みんなでばくはつ",
            text_ja="お互いの場にいるすべての「ドガース」「マタドガス」「わるいマタドガス」の数×20のダメージ。その後、お互いの場にいる全ての「ドガース」「マタドガス」「わるいマタドガス」に、それぞれ20ダメージ。",
            play_text_ja="お互いの場にいるすべての「ドガース」「マタドガス」「わるいマタドガス」の数×20のダメージ。その後、お互いの場にいる全ての「ドガース」「マタドガス」「わるいマタドガス」に、それぞれ20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいマタドガス。しびれガス（草草草）20: 1 枚のコインで「おもて」ならどく、「うら」ならマヒ（v0.38 のきけんなはりと同じ型）
        AttackKey("PMCG4-011", 1): AttackEntry(
            DamageThenPoisonOrParalyze(),
            "しびれガス",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態に、「うら」なら「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態に、「うら」なら「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいスリーパー（ロケット団。スリープから進化）。ベンチをあやつる（超超無）20×: 相手が相手の控えの数だけコインを投げ、「うら」の数 × 20（弱点・抵抗力なし）
        AttackKey("PMCG4-037", 1): AttackEntry(
            OpponentFlipsTailsDamage(per=20),
            "ベンチをあやつる",
            text_ja="相手プレイヤーに、相手の控えポケモンの数だけコインを投げさせ、「うら」が出た数×20のダメージ(このワザのダメージは相手の「弱点・抵抗力」の影響を受けない)",
            play_text_ja="相手プレイヤーに、相手の控えポケモンの数だけコインを投げさせ、「うら」が出た数×20のダメージ(このワザのダメージは相手の「弱点・抵抗力」の影響を受けない)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのニドラン♂（闇からの挑戦）。にどげり（無）10×: コイン 2 枚の「おもて」の数 × 10
        AttackKey("PMCG6-004", 0): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=10),
            "にどげり",
            text_ja="コインを2枚投げて「おもて」の数×10のダメージ。",
            play_text_ja="コインを2枚投げて「おもて」の数×10のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのニドラン♂。いかりのいちげき（草）30: 自分にダメージカウンターが 2 つ以上のっているときだけ使える（ワザを使うための条件）
        AttackKey("PMCG6-004", 1): AttackEntry(
            DamageRequiringOwnCounters(minimum=2),
            "いかりのいちげき",
            text_ja="このワザは、自分にダメージカウンターが2つ以上のっているときだけ、使える。",
            play_text_ja="このワザは、自分にダメージカウンターが2つ以上のっているときだけ、使える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのニドリーノ（闇からの挑戦。サカキのニドラン♂から進化）。つのでえぐる（草無無）20+: 相手にカウンターがのっていれば + 20
        AttackKey("PMCG6-013", 0): AttackEntry(
            DamagePlusIfDefenderDamaged(bonus=20),
            "つのでえぐる",
            text_ja="このワザを使う時、すでに相手にダメージカウンターがのっているなら、20ダメージを追加する。",
            play_text_ja="このワザを使う時、すでに相手にダメージカウンターがのっているなら、20ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのニドキング（闇からの挑戦。サカキのニドリーノから進化）。すごむ（草）: 最大 HP 50 以下の相手は、次の相手の番、このカードがバトル場にいる限りワザを使えない
        AttackKey("PMCG6-021", 0): AttackEntry(
            AttackLockWhileSourceActive(max_hp=50),
            "すごむ",
            text_ja="このワザを受けた相手が「最大HPが50以下」のポケモンなら、そのポケモンは、次の相手の番、このカードがバトル場にいる限り、ワザを使えない。",
            play_text_ja="このワザを受けた相手が「最大HPが50以下」のポケモンなら、そのポケモンは、次の相手の番、このカードがバトル場にいる限り、ワザを使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのニドキング。ローリングアタック（草草草無）40+: コインの「おもて」で + 30（v0.31 の CoinBonusDamage）
        AttackKey("PMCG6-021", 1): AttackEntry(
            CoinBonusDamage(bonus=30),
            "ローリングアタック",
            text_ja="コインを投げて「おもて」なら、30ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、30ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのニドクイン（闇からの挑戦。サカキのニドリーナから進化）。ラブラリアット（草草無無）50+: 「うら」なら失敗。ベンチに「サカキのニドキング」がいればダメージは 100
        AttackKey("PMCG6-020", 1): AttackEntry(
            FailOnTailsAmountIfBenchNamed(names=("サカキのニドキング",), amount=100),
            "ラブラリアット",
            text_ja="コインを投げて「うら」なら、このワザは失敗する。自分のベンチに「サカキのニドキング」がいるなら、このワザのダメージは「100」になる。",
            play_text_ja="コインを投げて「うら」なら、このワザは失敗する。自分のベンチに「サカキのニドキング」がいるなら、このワザのダメージは「100」になる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいゴーリキー（ロケット団。ワンリキーから進化）。ひきずりだす（闘闘無）20: 相手の控えを選んで入れ替えてから、新しい対戦ポケモンに 20
        AttackKey("PMCG4-042", 0): AttackEntry(
            SwitchOpponentThenDamage(),
            "ひきずりだす",
            text_ja="ダメージを与える前に、相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。（ダメージは新しい対戦ポケモンに与える。相手に控えがいない時、このワザは使えない）",
            play_text_ja="ダメージを与える前に、相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。（ダメージは新しい対戦ポケモンに与える。相手に控えがいない時、このワザは使えない）",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいゴーリキー。なぐりとばす（闘闘無）30: ダメージのあと、相手が選ぶ控えと入れ替える（v0.4d のふきとばしと同じ型）
        AttackKey("PMCG4-042", 1): AttackEntry(
            DamageAndForceSwitch(),
            "なぐりとばす",
            text_ja="相手の対戦ポケモンを控えポケモンと入れ替える。入れ替えるポケモンは相手が選ぶ。（相手に控えがいない時、入れ替えは起こらない）",
            play_text_ja="相手の対戦ポケモンを控えポケモンと入れ替える。入れ替えるポケモンは相手が選ぶ。（相手に控えがいない時、入れ替えは起こらない）",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいカイリキー（ロケット団。わるいゴーリキーから進化）。つまみだす（闘闘闘無）: 相手の対戦ポケモンとついているカードを持ち主の山札にもどし、切る
        AttackKey("PMCG4-044", 1): AttackEntry(
            ReturnOpponentActiveToDeck(),
            "つまみだす",
            text_ja="相手の対戦ポケモンとそれについているすべてのカードを山札にもどさせ、その山札をよく切る。(相手に控えがいない時、このワザは使えない)",
            play_text_ja="相手の対戦ポケモンとそれについているすべてのカードを山札にもどさせ、その山札をよく切る。(相手に控えがいない時、このワザは使えない)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのウツドン（リーダーズスタジアム。エリカのマダツボミから進化）。さそってとかす（草草）20: ひきずりだすと同じ型
        AttackKey("PMCG5-011", 1): AttackEntry(
            SwitchOpponentThenDamage(),
            "さそってとかす",
            text_ja="ダメージを与える前に、相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。(ダメージは新しい対戦ポケモンに与える。相手に控えがいない時、このワザは使えない)",
            play_text_ja="ダメージを与える前に、相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。(ダメージは新しい対戦ポケモンに与える。相手に控えがいない時、このワザは使えない)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのシードラ（リーダーズスタジアム。カスミのタッツーから進化）。きぜつばり（水水水）30+: コイン 2 枚がすべて「おもて」なら + 60
        AttackKey("PMCG5-034", 1): AttackEntry(
            CoinsAllHeadsBonusDamage(coins=2, bonus=60),
            "きぜつばり",
            text_ja="コインを2枚投げ、すべて「おもて」なら、60ダメージを追加する。",
            play_text_ja="コインを2枚投げ、すべて「おもて」なら、60ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのマンキー（リーダーズスタジアム）。ひまつぶし（無）: 自分の山札を切る
        AttackKey("PMCG5-045", 0): AttackEntry(
            ShuffleDeckAttack(own=True),
            "ひまつぶし",
            text_ja="自分の山札をよく切る。",
            play_text_ja="自分の山札をよく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのマンキー。からてチョップ（闘無）40-: 自分のカウンターの数 × 10 だけ小さくなる（v0.10 の DamageReducedByOwnCounters。kyuura の印刷の文面が、v0.10 のゴーリキーの最新の説明と同じ文面）
        AttackKey("PMCG5-045", 1): AttackEntry(
            DamageReducedByOwnCounters(reduction_per_counter=10),
            "からてチョップ",
            text_ja="このワザのダメージは、自分にのっているダメージカウンターの数×10だけ、小さくなる。",
            play_text_ja="このワザのダメージは、自分にのっているダメージカウンターの数×10だけ、小さくなる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マンキー（ロケット団）。いたずら（無）: 相手の山札を切る
        AttackKey("PMCG4-039", 0): AttackEntry(
            ShuffleDeckAttack(own=False),
            "いたずら",
            text_ja="相手の山札をよく切る。",
            play_text_ja="相手の山札をよく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マンキー。おこる（闘無）20+: コインの「おもて」で + 20
        AttackKey("PMCG4-039", 1): AttackEntry(
            CoinBonusDamage(bonus=20),
            "おこる",
            text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # オコリザル（第2弾。マンキーから進化）。みだれひっかき（闘闘）20×: コイン 3 枚の「おもて」の数 × 20
        AttackKey("PMCG2-031", 0): AttackEntry(
            CoinFlipDamage(coins=3, damage_per_heads=20),
            "みだれひっかき",
            text_ja="コインを3枚投げて「おもて」の数×20のダメージ。",
            play_text_ja="コインを3枚投げて「おもて」の数×20のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # オコリザル。あばれまわる（闘闘無）50: ダメージ → コインの「うら」で自分がこんらん
        AttackKey("PMCG2-031", 1): AttackEntry(
            DamageThenSelfConfuseOnTails(),
            "あばれまわる",
            text_ja="コインを投げて「うら」なら、自分は「こんらん」状態になる。",
            play_text_ja="コインを投げて「うら」なら、自分は「こんらん」状態になる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.41（docs/heal-counter-status-v0.41.md）。kyuura データの採用（処理に使う文面は kyuura の印刷の文面）。
        # クサイハナ（第2弾。ナゾノクサから進化）。どくのこな（草）: ダメージなしでどく（v0.8 の PoisonWithoutDamage。ロケット団のベトベターの「どくガス」と同じ文面）
        AttackKey("PMCG2-009", 0): AttackEntry(
            PoisonWithoutDamage(),
            "どくのこな",
            text_ja="相手を「どく」状態にする。",
            play_text_ja="相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # クサイハナ。くさいにおい（草草）20: ダメージ → 相手をこんらん → 自分もこんらん（相手の効果が無効でも自分の効果は残る）
        AttackKey("PMCG2-009", 1): AttackEntry(
            DamageThenConfuseBoth(),
            "くさいにおい",
            text_ja="相手を「こんらん」状態にする。その後、自分も「こんらん」状態になる。",
            play_text_ja="相手を「こんらん」状態にする。その後、自分も「こんらん」状態になる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ウツボット（第2弾。ウツドンから進化）。さそうかおり（草）: ワザを使ったプレイヤーが相手の控えを選んで入れ替える（v0.31 のかどわかすと同じ型。書き方の違いは SWITCH_OPPONENT_ACTIVE_TEXTS）
        AttackKey("PMCG2-016", 0): AttackEntry(
            SwitchOpponentActive(),
            "さそうかおり",
            text_ja="相手の控えポケモンを選び、相手の対戦ポケモンと入れ替える。",
            play_text_ja="相手の控えポケモンを選び、相手の対戦ポケモンと入れ替える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ウツボット。ようかいえき（草草）20: ダメージ → コインの「おもて」で次の相手の番に「にげる」ことができない（v0.36 の CannotRetreat に要素のコイン）
        AttackKey("PMCG2-016", 1): AttackEntry(
            DamageThenRetreatLockOnHeads(),
            "ようかいえき",
            text_ja="コインを投げて「おもて」なら、「ようかいえき」を受けた相手の対戦ポケモンは、次の相手の番に「にげる」ことができない。",
            play_text_ja="コインを投げて「おもて」なら、「ようかいえき」を受けた相手の対戦ポケモンは、次の相手の番に「にげる」ことができない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # シードラ（第3弾。タッツーから進化）。みずでっぽう（水無）20+: 必要なエネルギーに無色がまざる多いエネルギーの追加（v0.31 の型。決められない数は HC4。書き方の違いは extra_energy_damage_texts）
        AttackKey("PMCG3-020", 0): AttackEntry(
            ExtraEnergyDamageMixed(energy_type=EnergyType.WATER, per_energy=10, max_extra=2),
            "みずでっぽう",
            text_ja="ワザに必要なぶんよりも多く「水」エネルギーカードがついている時、多いエネルギー1つにつき10ダメージを追加する。（ダメージ追加は2つぶんまで）",
            play_text_ja="ワザに必要なぶんよりも多く「水」エネルギーカードがついている時、多いエネルギー1つにつき10ダメージを追加する。（ダメージ追加は2つぶんまで）",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # シードラ。こうそくいどう（水無無）20: コインの「おもて」で次の相手の番にワザをうけない（v0.34 のギャロップと同じ AttackBarrier。書き方の違いは SELF_BARRIER_ON_HEADS_TEXTS）
        AttackKey("PMCG3-020", 1): AttackEntry(
            DamageThenSelfBarrierOnHeads(),
            "こうそくいどう",
            text_ja="コインを投げて「おもて」なら、このカードは次の相手の番に、ワザによるダメージや効果を受けない。",
            play_text_ja="コインを投げて「おもて」なら、このカードは次の相手の番に、ワザによるダメージや効果を受けない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいペルシアン（ロケット団。ニャースから進化）。ゆうわく（無）: 相手に控えがいなければ使えない。コインの「おもて」でワザを使ったプレイヤーが選んで入れ替える
        AttackKey("PMCG4-048", 0): AttackEntry(
            SwitchOpponentActiveOnHeads(),
            "ゆうわく",
            text_ja="コインを投げて「おもて」なら、相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。(相手に控えがいない時、このワザは使えない)。",
            play_text_ja="コインを投げて「おもて」なら、相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。(相手に控えがいない時、このワザは使えない)。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいペルシアン。どくのつめ（無無）10: コインの「おもて」でどく（v0.3a の PoisonOnHeads）
        AttackKey("PMCG4-048", 1): AttackEntry(
            PoisonOnHeads(),
            "どくのつめ",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのファイヤー（闇からの挑戦）。ひのとり（炎炎炎炎炎）90: ダメージ → コインの「うら」で自分とついているカードを山札にもどして切る（くもがくれガスと逆の面。Z23・RD9）
        AttackKey("PMCG6-035", 0): AttackEntry(
            DamageThenReturnSelfToDeckOnTails(),
            "ひのとり",
            text_ja="コインを投げて「うら」なら、ダメージを与えた後、自分と、自分についているすべてのカードを山札にもどす。その後、その山札をよく切る。",
            play_text_ja="コインを投げて「うら」なら、ダメージを与えた後、自分と、自分についているすべてのカードを山札にもどす。その後、その山札をよく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ヤドン（ロケット団）。ひなたぼっこ（無）: 山札の「超」エネルギーカードを 1 枚まで選んで自分につけ、山札を切る（手札からつける通常の操作ではない）
        AttackKey("PMCG4-032", 0): AttackEntry(
            AttachEnergyFromDeckToSelf(energy_type=EnergyType.PSYCHIC),
            "ひなたぼっこ",
            text_ja="自分の山札から「超」エネルギーカードを1枚選び出し、このカードにつけてよい。その後、その山札をよく切る。",
            play_text_ja="自分の山札から「超」エネルギーカードを1枚選び出し、このカードにつけてよい。その後、その山札をよく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのナゾノクサ（リーダーズスタジアム。HP 50）。ちょっとすいとる（草）10: ダメージ → 自分のカウンターを 1 つとりのぞく（「ダメージを与えたら」の条件はない）
        AttackKey("PMCG5-002", 0): AttackEntry(
            DamageThenHealSelf(counters=1),
            "ちょっとすいとる",
            text_ja="自分にのっているダメージカウンターを、1つとりのぞく。",
            play_text_ja="自分にのっているダメージカウンターを、1つとりのぞく。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのナゾノクサ（HP 50）。たまにすいとる（草無）20: ダメージ → コインの「おもて」で自分のカウンターを 1 つとりのぞく
        AttackKey("PMCG5-002", 1): AttackEntry(
            DamageThenHealSelf(counters=1, on_heads=True),
            "たまにすいとる",
            text_ja="コインを投げて「おもて」なら、自分にのっているダメージカウンターを、1つとりのぞく。",
            play_text_ja="コインを投げて「おもて」なら、自分にのっているダメージカウンターを、1つとりのぞく。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのナゾノクサ（リーダーズスタジアム。HP 40。PMCG5-002 とは同じ名前の別のカード）。へんなこな（草）10: 1 枚のコインで「おもて」ならこんらん、「うら」ならねむり
        AttackKey("PMCG5-003", 0): AttackEntry(
            DamageThenStatusByCoin(heads=CONFUSION, tails=SLEEP),
            "へんなこな",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態に、「うら」なら「ねむり」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態に、「うら」なら「ねむり」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのクサイハナ（リーダーズスタジアム。エリカのナゾノクサから進化）。ヒーリングかふん（草）: コインの「おもて」で自分のカウンターを 4 つまでとりのぞく
        AttackKey("PMCG5-009", 0): AttackEntry(
            CoinHealSelf(counters=4),
            "ヒーリングかふん",
            text_ja="コインを投げて「おもて」なら、自分にのっているダメージカウンターを、4つとりのぞく。",
            play_text_ja="コインを投げて「おもて」なら、自分にのっているダメージカウンターを、4つとりのぞく。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのクサイハナ。ミラクルかふん（草草草）30: ダメージ → コインの「おもて」でワザを使ったプレイヤーが 4 つの特殊状態から 1 つ選ぶ
        AttackKey("PMCG5-009", 1): AttackEntry(
            DamageThenChosenStatusOnHeads(),
            "ミラクルかふん",
            text_ja="コインを投げて「おもて」なら、「ねむり・マヒ・こんらん・どく」の中から1つを選び、相手をその状態にする。",
            play_text_ja="コインを投げて「おもて」なら、「ねむり・マヒ・こんらん・どく」の中から1つを選び、相手をその状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのコダック（闇からの挑戦）。こまったねんりき（超）20: コインが先。「おもて」ならダメージと相手のこんらん、「うら」なら相手にダメージなしで自分がこんらん
        AttackKey("PMCG6-036", 1): AttackEntry(
            CoinDamageAndConfuseElseSelfConfuse(),
            "こまったねんりき",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態に、「うら」なら、相手にはダメージを与えず、自分を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態に、「うら」なら、相手にはダメージを与えず、自分を「こんらん」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのゴルダック（闇からの挑戦。ナツメのコダックから進化）。ダメージシフト（超超）: 自分の場のポケモンから 1 つずつとりのぞいて相手にのせる（ダメージではない。CX1）
        AttackKey("PMCG6-038", 0): AttackEntry(
            MoveOwnCountersToOpponent(),
            "ダメージシフト",
            text_ja="自分と自分の控えポケモン全員から、ダメージカウンターを1つずつとりのぞき、とりのぞいたダメージカウンターをすべて、相手にのせる。",
            play_text_ja="自分と自分の控えポケモン全員から、ダメージカウンターを1つずつとりのぞき、とりのぞいたダメージカウンターをすべて、相手にのせる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのゴルダック。ウォーターシュート（水無無）20+: コインの「おもて」で 20 追加（v0.31 の CoinBonusDamage）
        AttackKey("PMCG6-038", 1): AttackEntry(
            CoinBonusDamage(bonus=20),
            "ウォーターシュート",
            text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのモルフォン（闇からの挑戦。ナツメのコンパンから進化）。かいふくりんぷん（草）: コイン 3 枚の「おもて」の数ぶんを、自分の場のポケモンそれぞれからとりのぞく
        AttackKey("PMCG6-022", 0): AttackEntry(
            CoinsHealOwnPokemon(coins=3),
            "かいふくりんぷん",
            text_ja="コインを3枚投げ、「おもて」の数ぶんのダメージカウンターを、自分と自分の控えポケモン全員から、それぞれ、とりのぞく。",
            play_text_ja="コインを3枚投げ、「おもて」の数ぶんのダメージカウンターを、自分と自分の控えポケモン全員から、それぞれ、とりのぞく。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのモルフォン。げんかくおんぱ（超）10: ダメージ → コイン 2 枚の 1 枚でも「おもて」ならこんらん
        AttackKey("PMCG6-022", 1): AttackEntry(
            DamageThenConfuseOnAnyHeads(coins=2),
            "げんかくおんぱ",
            text_ja="コインを2枚投げ、1枚でも「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを2枚投げ、1枚でも「おもて」なら、相手を「こんらん」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのヤドラン（闇からの挑戦。ナツメのヤドンから進化）。いねむり（超）: 1 枚のコインの「おもて」で自分のカウンターを 3 つまでとりのぞき、自分をねむりにする
        AttackKey("PMCG6-048", 0): AttackEntry(
            CoinHealSelf(counters=3, then_sleep=True),
            "いねむり",
            text_ja="コインを投げて「おもて」なら、自分にのっているダメージカウンターを3つとりのぞき、自分を「ねむり」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、自分にのっているダメージカウンターを3つとりのぞき、自分を「ねむり」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのヤドラン。きあいずつき（超無無）40: ダメージ → 次の自分の番にこのワザを使えない（v0.35 の CannotUseOwnAttack。コインなし）
        AttackKey("PMCG6-048", 1): AttackEntry(
            DamageThenLockSelf(),
            "きあいずつき",
            text_ja="次の自分の番、このカードは「きあいずつき」を使えない。",
            play_text_ja="次の自分の番、このカードは「きあいずつき」を使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのプリン（リーダーズスタジアム）。みんなでかいふく（無）: お互いの場のポケモン全員から 1 つずつとりのぞく
        AttackKey("PMCG5-058", 0): AttackEntry(
            HealAllPokemonBothSides(counters=1),
            "みんなでかいふく",
            text_ja="お互いの場にいるポケモン全員から、それぞれダメージカウンターを1つずつ、とりのぞく。",
            play_text_ja="お互いの場にいるポケモン全員から、それぞれダメージカウンターを1つずつ、とりのぞく。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのプリン。やさしいパンチ（無無）40-: 相手にカウンターがのっていれば p.321 の 1 段階で 30 へらす（数に比例しない）
        AttackKey("PMCG5-058", 1): AttackEntry(
            DamageMinusIfDefenderDamaged(reduction=30),
            "やさしいパンチ",
            text_ja="相手にダメージカウンターがのっている時、このワザのダメージは「-30」される。",
            play_text_ja="相手にダメージカウンターがのっている時、このワザのダメージは「-30」される。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # R団のミュウツー（闇からの挑戦）。チェンジダメージ（超）: コインの「おもて」で自分と相手のダメージカウンターを取り替える（取り替える前の双方の数で。ダメージではない。CX1）
        AttackKey("PMCG6-055", 0): AttackEntry(
            SwapCountersOnHeads(),
            "チェンジダメージ",
            text_ja="コインを投げて「おもて」なら、自分にのっているダメージカウンターすべてと、相手にのっているダメージカウンターすべてを、取り替える。",
            play_text_ja="コインを投げて「おもて」なら、自分にのっているダメージカウンターすべてと、相手にのっているダメージカウンターすべてを、取り替える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # R団のミュウツー。さいみんはどう（超超）20: ダメージ → コインの「おもて」でねむり
        AttackKey("PMCG6-055", 1): AttackEntry(
            DamageThenSleepOnHeads(),
            "さいみんはどう",
            text_ja="コインを投げて「おもて」なら、相手を「ねむり」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「ねむり」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.42（docs/power-decisions-v0.42.md）。kyuura データの採用（処理に使う文面は kyuura の印刷の文面）
        # ナツメのルージュラ（闇からの挑戦）。よいおこない（超）: 相手の場のポケモンを 1 匹選び、とりのぞく数を選ぶ（0 は HC5 と同じ問い）→ とりのぞいた数を引く
        AttackKey("PMCG6-052", 0): AttackEntry(
            HealChosenOpponentThenDraw(),
            "よいおこない",
            text_ja="相手の場にいるポケモンを1匹選び、そのポケモンにのっているダメージカウンターを、好きなだけとりのぞく。とりのぞいた数ぶんのカードを自分の山札から引いて、手札に加える。",
            play_text_ja="相手の場にいるポケモンを1匹選び、そのポケモンにのっているダメージカウンターを、好きなだけとりのぞく。とりのぞいた数ぶんのカードを自分の山札から引いて、手札に加える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのルージュラ。だきつく（超無）20: ダメージ → コインの「おもて」で次の相手の番に「にげる」ことができない（v0.41 のようかいえきと同じ型。書き方の違いを受け付ける）
        AttackKey("PMCG6-052", 1): AttackEntry(
            DamageThenRetreatLockOnHeads(),
            "だきつく",
            text_ja="コインを投げて「おもて」なら、このワザを受けた相手は、次の相手の番に「にげる」ことができない。",
            play_text_ja="コインを投げて「おもて」なら、このワザを受けた相手は、次の相手の番に「にげる」ことができない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ラフレシア（第2弾。クサイハナから進化）。はなびらのまい（草草草）40×: コイン 3 枚の「おもて」の数 × 40 → 自分はこんらん
        AttackKey("PMCG2-014", 0): AttackEntry(
            CoinFlipDamageThenSelfConfuse(coins=3, damage_per_heads=40),
            "はなびらのまい",
            text_ja="コインを3枚投げて「おもて」の数×40のダメージ。その後、自分は「こんらん」状態になる。",
            play_text_ja="コインを3枚投げて「おもて」の数×40のダメージ。その後、自分は「こんらん」状態になる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ヤドラン（化石の秘密。ヤドンから進化）。ねんりき（超超）20: ダメージ → コインの「おもて」でマヒ
        AttackKey("PMCG3-028", 0): AttackEntry(
            ParalyzeOnHeads(),
            "ねんりき",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ゲンガー（化石の秘密。ゴーストから進化）。ナイトヘッド（超超超）30: ダメージ → 相手の控えを 1 匹選び「弱点・抵抗力」に関係なく 10（控えがいなければ何もしない。書き方の違いを受け付ける）
        AttackKey("PMCG3-031", 0): AttackEntry(
            DamageThenChosenBenchDamage(10),
            "ナイトヘッド",
            text_ja="相手の控えポケモンから1匹選び、「弱点・抵抗力」に関係なく10ダメージ。相手に控えポケモンがいない時には、この効果はない。",
            play_text_ja="相手の控えポケモンから1匹選び、「弱点・抵抗力」に関係なく10ダメージ。相手に控えポケモンがいない時には、この効果はない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのラフレシア（リーダーズスタジアム。エリカのクサイハナから進化）。メガドレイン（草草草）30: v0.4d と同じ（与えたダメージの半分（切り上げ）をとりのぞく）
        AttackKey("PMCG5-014", 0): AttackEntry(
            DamageAndDrain(),
            "メガドレイン",
            text_ja="相手にダメージを与えたら、与えたダメージの半分（切り上げ）のダメージカウンターを、自分からとりのぞく。",
            play_text_ja="相手にダメージを与えたら、与えたダメージの半分（切り上げ）のダメージカウンターを、自分からとりのぞく。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのケーシィ（闇からの挑戦）。エネループ（超）20: 自分の「超」エネルギーカードを 1 枚選んで手札にもどす（時点は HC1 と同じ問い）→ ダメージ
        AttackKey("PMCG6-043", 0): AttackEntry(
            ReturnEnergyThenDamage(EnergyType.PSYCHIC),
            "エネループ",
            text_ja="自分についている「超」エネルギーカードを1枚選び、はがして手札にもどす。",
            play_text_ja="自分についている「超」エネルギーカードを1枚選び、はがして手札にもどす。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのユンゲラー（闇からの挑戦。ナツメのケーシィから進化）。ライフダウン（超）: コインの「おもて」で残り HP が 10 になるようにカウンターをのせる（ダメージではない）
        AttackKey("PMCG6-047", 0): AttackEntry(
            PlaceCountersToRemainingHpOnHeads(remaining=10),
            "ライフダウン",
            text_ja="コインを投げて「おもて」なら、残りHPが「10」になるように、相手にダメージカウンターをのせる。",
            play_text_ja="コインを投げて「おもて」なら、残りHPが「10」になるように、相手にダメージカウンターをのせる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カイリュー（化石の秘密。ハクリューから進化）。たたきつける（無無無無）40×: コイン 2 枚の「おもて」の数 × 40
        AttackKey("PMCG3-043", 0): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=40),
            "たたきつける",
            text_ja="コインを2枚投げて、「おもて」のでた数×40のダメージ。",
            play_text_ja="コインを2枚投げて、「おもて」のでた数×40のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいユンゲラー（ロケット団。ケーシィから進化）。マインドショック（超超）30: 相手の弱点・抵抗力の影響を受けない（v0.39 のソニックブームと同じ型。書き方の違いを受け付ける）
        AttackKey("PMCG4-034", 0): AttackEntry(
            DamageIgnoringWeaknessResistance(),
            "マインドショック",
            text_ja="このワザのダメージは、相手の「弱点・抵抗力」の影響を受けない。",
            play_text_ja="このワザのダメージは、相手の「弱点・抵抗力」の影響を受けない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいフーディン（ロケット団。わるいユンゲラーから進化）。テレポートブラスト（超超無）30: ダメージ → のぞむなら自分の控えと入れ替える（ダメージを与えなかったら Z23）
        AttackKey("PMCG4-035", 0): AttackEntry(
            DamageThenOptionalSelfSwitch(),
            "テレポートブラスト",
            text_ja="のぞむなら、ダメージを与えた後、自分の控えポケモンを1匹選び、このカードと入れ替えてもよい。",
            play_text_ja="のぞむなら、ダメージを与えた後、自分の控えポケモンを1匹選び、このカードと入れ替えてもよい。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいフーディン。マインドショック（超超超）40: 相手の弱点・抵抗力の影響を受けない
        AttackKey("PMCG4-035", 1): AttackEntry(
            DamageIgnoringWeaknessResistance(),
            "マインドショック",
            text_ja="このワザのダメージは、相手の「弱点・抵抗力」の影響を受けない。",
            play_text_ja="このワザのダメージは、相手の「弱点・抵抗力」の影響を受けない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ドククラゲ（化石の秘密。メノクラゲから進化）。ちょうおんぱ（水）: コインの「おもて」でこんらん（ダメージなし）
        AttackKey("PMCG3-017", 0): AttackEntry(
            ConfuseOnHeadsWithoutDamage(),
            "ちょうおんぱ",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ドククラゲ。クラゲばり（水水）10: ダメージ → どく
        AttackKey("PMCG3-017", 1): AttackEntry(
            PoisonOpponent(),
            "クラゲばり",
            text_ja="相手を「どく」状態にする。",
            play_text_ja="相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのピッピ（リーダーズスタジアム）。つきのちから（無）: コインの「おもて」で山札の進化カードを自分または控えに重ねる（通常の進化の条件）→ 山札を切る
        AttackKey("PMCG5-060", 0): AttackEntry(
            EvolveFromDeckOnHeads(),
            "つきのちから",
            text_ja="コインを投げて「おもて」なら、自分の山札から、自分または自分の控えポケモンを進化させる「進化カード」を1枚選び出し、そのポケモンの上にのせる。その後、その山札をよく切る。",
            play_text_ja="コインを投げて「おもて」なら、自分の山札から、自分または自分の控えポケモンを進化させる「進化カード」を1枚選び出し、そのポケモンの上にのせる。その後、その山札をよく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのピクシー（リーダーズスタジアム。エリカのピッピから進化）。ようせいのきせき（無）: コインの「おもて」で自分の場のポケモンを好きなだけ選び、ついているカードごと手札にもどす（0 匹は HC5 と同じ問い）
        AttackKey("PMCG5-065", 0): AttackEntry(
            ReturnOwnPokemonToHandOnHeads(),
            "ようせいのきせき",
            text_ja="コインを投げて「おもて」なら、自分の場にいるポケモンを好きなだけ選び、そのポケモンと、それらについているすべてのカードを手札にもどす。",
            play_text_ja="コインを投げて「おもて」なら、自分の場にいるポケモンを好きなだけ選び、そのポケモンと、それらについているすべてのカードを手札にもどす。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ピカチュウ（v0.2f）p.125。相手に 30（目安の数字）、コインが「うら」なら自分にも 10
        AttackKey("PMCG1-035", 1): AttackEntry(
            SelfDamageOnTails(self_damage=10),
            "でんげき",
            text_ja="コインを投げて「うら」なら、自分にも10ダメージ。",
            play_text_ja="コインを投げて「うら」なら、自分にも10ダメージ。",
            source="P43 p.125",
        ),
        # ---- v0.43（docs/declared-entry-powers-v0.43.md）: 宣言して使う特殊能力・場に出たときに使う特殊能力を持つ 9 枚のワザ（kyuura データの採用。処理に使う文面は kyuura の印刷の文面）
        # わるいクサイハナ（ロケット団。ナゾノクサから進化）。どくのこな（草草）10: ダメージ → どく
        AttackKey("PMCG4-006", 0): AttackEntry(
            PoisonOpponent(),
            "どくのこな",
            text_ja="相手を「どく」状態にする。",
            play_text_ja="相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # スリープ（ロケット団。第1弾のスリープ PMCG1-045 とは同じ名前の別のカード）。あくむ（超無）10: ダメージ → ねむり（コインなし）
        AttackKey("PMCG4-033", 0): AttackEntry(
            SleepOpponent(),
            "あくむ",
            text_ja="相手を「ねむり」状態にする。",
            play_text_ja="相手を「ねむり」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのマダツボミ（リーダーズスタジアム。HP 40。エリカのマダツボミ PMCG5-005 とは同じ名前の別のカード）。のびるつる（草）: 相手の控えを 1 匹選び、弱点・抵抗力に関係なく 10（v0.38 の型。書き方の違いを受け付ける）
        AttackKey("PMCG5-010", 0): AttackEntry(
            ChooseOpponentBenchDamage(10, requires_bench=False),
            "のびるつる",
            text_ja="相手の控えポケモンを1匹選び、そのポケモンに、「弱点・抵抗力」に関係なく、10ダメージ。",
            play_text_ja="相手の控えポケモンを1匹選び、そのポケモンに、「弱点・抵抗力」に関係なく、10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのレアコイル（リーダーズスタジアム。マチスのコイルから進化）。メガショック（雷雷雷無）50: コインの「うら」で自分にも 20
        AttackKey("PMCG5-040", 0): AttackEntry(
            SelfDamageOnTails(20),
            "メガショック",
            text_ja="コインを投げて「うら」なら、自分にも20ダメージ。",
            play_text_ja="コインを投げて「うら」なら、自分にも20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいハクリュー（ロケット団。ミニリュウから進化）。しっぽでつく（無無無）20+: コインの「おもて」で 20 追加
        AttackKey("PMCG4-052", 0): AttackEntry(
            CoinBonusDamage(20),
            "しっぽでつく",
            text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいゴルバット（ロケット団。ズバットから進化）。ふらふらとぶ（草草）: 相手の場のポケモン（バトル場・ベンチ）を 1 匹選び、弱点・抵抗力に関係なく 20（v0.43 の型）
        AttackKey("PMCG4-009", 0): AttackEntry(
            ChooseOpponentPokemonDamage(20),
            "ふらふらとぶ",
            text_ja="相手の場のポケモン1匹を選び、(「弱点・抵抗力」に関係なく)20ダメージ。",
            play_text_ja="相手の場のポケモン1匹を選び、(「弱点・抵抗力」に関係なく)20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいヤドラン（ロケット団。ヤドンから進化）。きまぐれこうげき（超超）40: コインの「うら」で失敗
        AttackKey("PMCG4-036", 0): AttackEntry(
            FailOnTailsDamage(),
            "きまぐれこうげき",
            text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            play_text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいカイリュー（ロケット団。わるいハクリューから進化）。きょだいなしっぽ（無無無無）70: コインの「うら」で失敗
        AttackKey("PMCG4-053", 0): AttackEntry(
            FailOnTailsDamage(),
            "きょだいなしっぽ",
            text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            play_text_ja="コインを投げて「うら」なら、このワザは失敗する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.44（docs/search-evolution-once-attacks-v0.44.md）。kyuura データの採用。ディグダ（ロケット団）。じめんにもぐる（闘）: 相手の場のポケモン（バトル場・ベンチ）を 1 匹選び、弱点・抵抗力に関係なく 10（v0.43 の型。書き方の違いを受け付ける）
        AttackKey("PMCG4-038", 0): AttackEntry(
            ChooseOpponentPokemonDamage(10),
            "じめんにもぐる",
            text_ja="相手の場のポケモンを1匹選び、(「弱点・抵抗力」に関係なく)10ダメージ。",
            play_text_ja="相手の場のポケモンを1匹選び、(「弱点・抵抗力」に関係なく)10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ニャース（ロケット団）。こばんなげ（無無）: コインの「おもて」で相手の場のポケモンを 1 匹選び、弱点・抵抗力に関係なく 20
        AttackKey("PMCG4-047", 0): AttackEntry(
            CoinChooseOpponentPokemonDamage(20),
            "こばんなげ",
            text_ja="コインを投げて「おもて」なら、相手の場にいるポケモンから1匹を選び、(「弱点・抵抗力」に関係なく)20ダメージ。",
            play_text_ja="コインを投げて「おもて」なら、相手の場にいるポケモンから1匹を選び、(「弱点・抵抗力」に関係なく)20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのフシギダネ（リーダーズスタジアム）。ねむりのたね（草）10: ダメージ → ねむり（コインなし）
        AttackKey("PMCG5-007", 0): AttackEntry(
            SleepOpponent(),
            "ねむりのたね",
            text_ja="相手を「ねむり」状態にする。",
            play_text_ja="相手を「ねむり」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # おつかい（草草）: コインの「おもて」で山札のトレーナーカードを 0〜1 枚見せて手札に加え、山札を切る
        AttackKey("PMCG5-007", 1): AttackEntry(
            SearchTrainerOnHeads(),
            "おつかい",
            text_ja="コインを投げて「おもて」なら、自分の山札から「トレーナーカード」1枚を選び出し、相手に見せてから、手札に加えてよい。その後、その山札をよく切る。",
            play_text_ja="コインを投げて「おもて」なら、自分の山札から「トレーナーカード」1枚を選び出し、相手に見せてから、手札に加えてよい。その後、その山札をよく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのヒトデマン（リーダーズスタジアム）。スターブーメラン（水）20: 処理に使う文面は kyuura の最新の説明 LD-PMCG5-027-ATK0（印刷の文面は照合だけに使う）。返されたダメージで HP 以上なら手札にもどらない（CR-SHELL-ATTACK-STAR-BOOMERANG）
        AttackKey("PMCG5-027", 0): AttackEntry(
            DamageThenReturnSelfToHandOnHeads(),
            "スターブーメラン",
            text_ja="コインを投げて「おもて」なら、このカードと、このカードについている全てのカードを、持ち主の手札にもどす。",
            play_text_ja="コインを投げて「おもて」なら、自分と自分についているすべてのカードを手札にもどす。",
            source="LD-PMCG5-027-ATK0",
        ),
        # コイキング（ロケット団）。たきのぼりしんか（水水水）: 山札の「コイキング」から進化するカードを 0〜1 枚このカードに重ねて進化させ、山札を切る（通常の進化の制限。ワザなので番は終わる）
        AttackKey("PMCG4-020", 1): AttackEntry(
            EvolveSelfFromDeck("コイキング"),
            "たきのぼりしんか",
            text_ja="「コイキング」から進化するカードを自分の山札から1枚選び出し、このカードにつけてよい。その後、その山札をよく切る。",
            play_text_ja="「コイキング」から進化するカードを自分の山札から1枚選び出し、このカードにつけてよい。その後、その山札をよく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのコクーン（闇からの挑戦。キョウのビードルから進化）。どくどくえき（草）: ダメージなし。コインの「おもて」で特殊などく（20）
        AttackKey("PMCG6-011", 0): AttackEntry(
            SpecialPoisonOnHeadsWithoutDamage(20),
            "どくどくえき",
            text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。このワザによって「どく」状態になったポケモンがポケモンチェックで受ける「どく」のダメージは、20ダメージ。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」状態にする。このワザによって「どく」状態になったポケモンがポケモンチェックで受ける「どく」のダメージは、20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのスピアー（闇からの挑戦。キョウのコクーンから進化）。しんけいどく（草草）20: ダメージ → 同じコインの「おもて」でどくとマヒの両方
        AttackKey("PMCG6-018", 0): AttackEntry(
            DamageThenPoisonAndParalyzeOnHeads(),
            "しんけいどく",
            text_ja="コインを投げて「おもて」なら、相手を「どく」と「マヒ」の両方の状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」と「マヒ」の両方の状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ひっさつばり（無無無）70: 場に出てから 1 回しか使えない（記録は場のポケモン）。コインの「うら」ならダメージなし（使ったことになる）
        AttackKey("PMCG6-018", 1): AttackEntry(
            OnceAfterEntryNoDamageOnTails(),
            "ひっさつばり",
            text_ja="このワザは、このカードが場に出てから、1回しか使えない。コインを投げて「うら」なら、ダメージは与えられない。(その場合も、ワザは使ったことになる)",
            play_text_ja="このワザは、このカードが場に出てから、1回しか使えない。コインを投げて「うら」なら、ダメージは与えられない。(その場合も、ワザは使ったことになる)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カモネギ（第1弾）。ネギでたたく（無）30: コインの「うら」ならダメージなし。場に出してから 1 度しか使えない
        AttackKey("PMCG1-063", 0): AttackEntry(
            OnceAfterEntryNoDamageOnTails(),
            "ネギでたたく",
            text_ja="コインを投げて「うら」なら、ダメージをあたえられない。場に出してから1度しか使えない。",
            play_text_ja="コインを投げて「うら」なら、ダメージをあたえられない。場に出してから1度しか使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのコイキング（闇からの挑戦）。りゅうのきおく（水）40: ひっさつばりと同じ説明
        AttackKey("PMCG6-037", 0): AttackEntry(
            OnceAfterEntryNoDamageOnTails(),
            "りゅうのきおく",
            text_ja="このワザは、このカードが場に出てから、1回しか使えない。コインを投げて「うら」なら、ダメージは与えられない。(その場合も、ワザは使ったことになる)",
            play_text_ja="このワザは、このカードが場に出てから、1回しか使えない。コインを投げて「うら」なら、ダメージは与えられない。(その場合も、ワザは使ったことになる)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # はねまくる（水無）10×: コイン 3 枚の「おもて」の数 × 10
        AttackKey("PMCG6-037", 1): AttackEntry(
            CoinFlipDamage(coins=3, damage_per_heads=10),
            "はねまくる",
            text_ja="コインを3枚投げ、「おもて」の数×10のダメージ。",
            play_text_ja="コインを3枚投げ、「おもて」の数×10のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのギャラドス（闇からの挑戦。サカキのコイキングから進化）。あらしをよぶ（水）: 同じコイン 2 枚がすべて「おもて」なら、自分以外の場のポケモン全員に弱点・抵抗力に関係なく 20
        AttackKey("PMCG6-040", 0): AttackEntry(
            CoinsAllHeadsSpreadDamageExceptSelf(coins=2, damage=20),
            "あらしをよぶ",
            text_ja="コインを2枚投げ、すべて「おもて」なら、場にいる、自分以外のポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ20ダメージ。",
            play_text_ja="コインを2枚投げ、すべて「おもて」なら、場にいる、自分以外のポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # りゅうのたつまき（水水無無）40: ダメージ → 相手がきぜつしなければ、ワザを使ったプレイヤーが相手の控えを選んで入れ替える
        AttackKey("PMCG6-040", 1): AttackEntry(
            DamageThenSwitchOpponentIfNotKnockedOut(),
            "りゅうのたつまき",
            text_ja="相手が「きぜつ」しなければ、相手の控えポケモンを1匹選び、相手と入れ替える。",
            play_text_ja="相手が「きぜつ」しなければ、相手の控えポケモンを1匹選び、相手と入れ替える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのバリヤード（闇からの挑戦）。てじな（無）: 手札を最大 3 枚山札にもどす → 同じ枚数の基本エネルギーカードを見せて手札に加える → 山札を切る
        AttackKey("PMCG6-046", 0): AttackEntry(
            ReturnHandThenRevealBasicEnergy(3),
            "てじな",
            text_ja="自分の手札から最大3枚のカードを選び、山札にもどす。もどしたのと同じ枚数の基本エネルギーカードを山札から選び出し、相手プレイヤーに見せてから、手札に加える。その後、その山札をよく切る。",
            play_text_ja="自分の手札から最大3枚のカードを選び、山札にもどす。もどしたのと同じ枚数の基本エネルギーカードを山札から選び出し、相手プレイヤーに見せてから、手札に加える。その後、その山札をよく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのマンキー（闇からの挑戦）。わるいいたずら（無）: コインの「おもて」で相手のトラッシュのカード 1 枚を相手の山札の上に（切らない）
        AttackKey("PMCG6-056", 0): AttackEntry(
            CoinPutOpponentDiscardOnDeckTop(),
            "わるいいたずら",
            text_ja="コインを投げて「おもて」なら、相手のトラッシュからカードを1枚選び出し、相手の山札の上にのせる。",
            play_text_ja="コインを投げて「おもて」なら、相手のトラッシュからカードを1枚選び出し、相手の山札の上にのせる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # みだれひっかき（闘）10×: コイン 3 枚の「おもて」の数 × 10
        AttackKey("PMCG6-056", 1): AttackEntry(
            CoinFlipDamage(coins=3, damage_per_heads=10),
            "みだれひっかき",
            text_ja="コインを3枚投げ、「おもて」の数×10のダメージ。",
            play_text_ja="コインを3枚投げ、「おもて」の数×10のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # _____のラッキー（闇からの挑戦。名前は kyuura の名前のまま）。ラッキーたまご（無）: コインの「おもて」で 2 枚引く・「うら」で手札を 2 枚山札にもどして切る
        AttackKey("PMCG6-075", 0): AttackEntry(
            CoinDrawOrReturnHandToDeck(draw=2, count=2),
            "ラッキーたまご",
            text_ja="コインを投げて「おもて」なら、山札からカードを2枚引く。「うら」なら、自分の手札からカードを2枚選び、山札にもどして、よく切る。",
            play_text_ja="コインを投げて「おもて」なら、山札からカードを2枚引く。「うら」なら、自分の手札からカードを2枚選び、山札にもどして、よく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ラッキーパンチ（無無無）10+: コインの「おもて」で 30 追加
        AttackKey("PMCG6-075", 1): AttackEntry(
            CoinBonusDamage(30),
            "ラッキーパンチ",
            text_ja="コインを投げて「おもて」なら、30ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、30ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのペルシアン（闇からの挑戦。サカキのニャースから進化）。おそいかかる（無無無）20+: コインの「おもて」で 20 追加
        AttackKey("PMCG6-071", 0): AttackEntry(
            CoinBonusDamage(20),
            "おそいかかる",
            text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.45（docs/conditional-damage-energy-v0.45.md）。ゴースト（第1弾）は v0.9 の過去の原典照合の記録（card_verification.json。p.160。2 つのワザの最新の説明がある）
        # で登録する（化石の秘密のベトベター（v0.37）と同じ扱い）。ほかの 14 枚は kyuura データの採用（処理に使う文面は kyuura の印刷の文面。クロスカウンターは
        # kyuura の最新の説明 LD-PMCG5-054-ATK0）。さいみんじゅつ（超）: ダメージなし。相手をねむりにする（v0.3b の型）
        AttackKey("PMCG1-047", 0): AttackEntry(
            PutToSleep(),
            "さいみんじゅつ",
            text_ja="相手を「ねむり」状態にする。",
            play_text_ja="相手を「ねむり」状態にする。",
            source="P43 p.160",
        ),
        # ゆめくい（超超）50: 照合の記録の最新の説明（kyuura の LD-PMCG1-047-ATK1 と同じ）「相手が「ねむり」状態でないとき、このワザは失敗する。」。印刷の文面
        # （「…ねむり状態のときだけ、ダメージをあたえる。」）にはしたがわない（使えない・ダメージ 0 にしない。p.323 のワザの失敗）
        AttackKey("PMCG1-047", 1): AttackEntry(
            DamageFailUnlessOpponentStatus(SLEEP),
            "ゆめくい",
            text_ja="相手が「ねむり」状態のときだけ、ダメージをあたえる。",
            play_text_ja="相手が「ねむり」状態でないとき、このワザは失敗する。",
            source="P43 p.160",
        ),
        # カスミのタッツー（リーダーズスタジアム。PMCG5-024。えんまくの PMCG5-025 とは別のカード）。スミをかける（水水）20: コインの「おもて」で、それ以後ワザを使う
        # たびにコイン（期限のない AttackCoinCheck。バトル場をはなれると消える）
        AttackKey("PMCG5-024", 0): AttackEntry(
            DamageThenLastingAttackCoinCheckOnHeads(),
            "スミをかける",
            text_ja=LASTING_ATTACK_COIN_CHECK_TEXT,
            play_text_ja=LASTING_ATTACK_COIN_CHECK_TEXT,
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カスミのジュゴン（リーダーズスタジアム。カスミのパウワウから進化）。こおりのつぶて（水水）20: 相手が「闘」ポケモンなら 1 段階で 2 倍
        AttackKey("PMCG5-031", 0): AttackEntry(
            DamageMultipliedAgainstType(EnergyType.FIGHTING, 2),
            "こおりのつぶて",
            text_ja="このワザを受ける相手が「闘」ポケモンなら、このワザのダメージは2倍になる。",
            play_text_ja="このワザを受ける相手が「闘」ポケモンなら、このワザのダメージは2倍になる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # とっしん（水無無無）60: 自分にも 20（既存の型）
        AttackKey("PMCG5-031", 1): AttackEntry(
            DamageAndSelfDamage(20),
            "とっしん",
            text_ja="自分にも20ダメージ。",
            play_text_ja="自分にも20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのアーボ（闇からの挑戦）。とつぜんどく（草）10: コイン 2 枚がすべて「おもて」なら、どくとこんらん（1 組のコインで両方）
        AttackKey("PMCG6-002", 0): AttackEntry(
            DamageThenPoisonAndConfuseOnAllHeads(coins=2),
            "とつぜんどく",
            text_ja="コインを2枚投げ、すべて「おもて」なら、相手を「どく」と「こんらん」の両方の状態にする。",
            play_text_ja="コインを2枚投げ、すべて「おもて」なら、相手を「どく」と「こんらん」の両方の状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのアーボック（闇からの挑戦。キョウのアーボから進化）。どくをためる（草）: ダメージなし。自分をどく状態にする
        AttackKey("PMCG6-019", 0): AttackEntry(
            SelfStatusWithoutDamage(POISON),
            "どくをためる",
            text_ja="自分を「どく」状態にする。",
            play_text_ja="自分を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ポイズンパワー（草草）20: 自分がどく状態（通常・特殊などく）なら 1 段階で「40」になり、その場合、相手をどく状態にする（条件は 1 回だけ確かめる）
        AttackKey("PMCG6-019", 1): AttackEntry(
            DamageIfSelfStatusThenOpponentStatus(POISON, 40),
            "ポイズンパワー",
            text_ja="自分が「どく」状態なら、このワザのダメージは「40」になる。その場合、相手を「どく」状態にする。",
            play_text_ja="自分が「どく」状態なら、このワザのダメージは「40」になる。その場合、相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのベトベター（闇からの挑戦）。ベトベトハンド（草）: ダメージなし。コインの「おもて」で相手の控えを選んで入れ替え、新しい対戦ポケモンをどく状態にする
        AttackKey("PMCG6-007", 0): AttackEntry(
            CoinSwitchOpponentThenStatus(POISON),
            "ベトベトハンド",
            text_ja="コインを投げて「おもて」なら、相手の控えポケモンを1匹選び、相手と入れ替える。その後、新しい相手の対戦ポケモンを「どく」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手の控えポケモンを1匹選び、相手と入れ替える。その後、新しい相手の対戦ポケモンを「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいカメックス（ロケット団。わるいカメールから進化）。ハイドロキャノン（水水）30+: 多い「水」1 つにつき 20（2 つまで。v0.6 の型。kyuura の文面の「がいている」は
        # 転記の誤り（pcg-search.com は「がついている」。kyuura への報告事項）。型は文面の形を確かめない）
        AttackKey("PMCG4-024", 0): AttackEntry(
            ExtraEnergyDamage(EnergyType.WATER, 20, 2),
            "ハイドロキャノン",
            text_ja="ワザに必要なエネルギーよりも多く「水」エネルギーがいている時、多い「水」エネルギー1つにつき、20ダメージを追加する。(ダメージ追加は2つぶんまで)",
            play_text_ja="ワザに必要なエネルギーよりも多く「水」エネルギーがいている時、多い「水」エネルギー1つにつき、20ダメージを追加する。(ダメージ追加は2つぶんまで)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ロケットタックル（水無無）40: 自分にも 10。コインの「おもて」で次の相手の番にダメージを受けない（ダメージ以外の効果は受ける）
        AttackKey("PMCG4-024", 1): AttackEntry(
            DamageAndSelfDamageThenPreventDamageOnHeads(10),
            "ロケットタックル",
            text_ja="このカードにも10ダメージ。コインを投げて「おもて」なら、このカードは次の相手の番にダメージを受けない。(ダメージ以外の効果は受ける)",
            play_text_ja="このカードにも10ダメージ。コインを投げて「おもて」なら、このカードは次の相手の番にダメージを受けない。(ダメージ以外の効果は受ける)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいレアコイル（ロケット団。コイルから進化）。ソニックブーム（無無）20: 相手の弱点・抵抗力の影響を受けない（v0.39 の型）
        AttackKey("PMCG4-030", 0): AttackEntry(
            DamageIgnoringWeaknessResistance(),
            "ソニックブーム",
            text_ja="このワザのダメージは、相手の「弱点・抵抗力」の影響を受けない。",
            play_text_ja="このワザのダメージは、相手の「弱点・抵抗力」の影響を受けない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # じりょくせん（雷雷）30: 相手の対戦ポケモンの基本エネルギーカードを 1 枚はがし、相手の控えポケモンにつける（控えがいなければ効果なし）
        AttackKey("PMCG4-030", 1): AttackEntry(
            DamageThenMoveOpponentEnergyToBench(),
            "じりょくせん",
            text_ja=MOVE_OPPONENT_ENERGY_TEXT,
            play_text_ja=MOVE_OPPONENT_ENERGY_TEXT,
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カツラのリザードン（闇からの挑戦。カツラのリザードから進化）。ファイヤーブレス（炎）20+: 多い「炎」エネルギーをすべてトラッシュし、トラッシュした数 × 20 を追加
        AttackKey("PMCG6-032", 0): AttackEntry(
            DiscardExcessEnergyForDamage(EnergyType.FIRE, 20),
            "ファイヤーブレス",
            text_ja="このワザに必要なエネルギーよりも多く「炎」エネルギーがついている時、多い「炎」エネルギーをすべてトラッシュして、トラッシュしたエネルギーの数×20のダメージを追加する。",
            play_text_ja="このワザに必要なエネルギーよりも多く「炎」エネルギーがついている時、多い「炎」エネルギーをすべてトラッシュして、トラッシュしたエネルギーの数×20のダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # かえんひこう（炎炎）: ダメージなし。コインの「おもて」で相手の場のポケモンを 1 匹選び、弱点・抵抗力に関係なく 40（v0.44 の型。書き方の違いを受け付ける）
        AttackKey("PMCG6-032", 1): AttackEntry(
            CoinChooseOpponentPokemonDamage(40),
            "かえんひこう",
            text_ja="コインを投げて「おもて」なら、相手の場のポケモンを1匹選び、「弱点・抵抗力」に関係なく、40ダメージ。",
            play_text_ja="コインを投げて「おもて」なら、相手の場のポケモンを1匹選び、「弱点・抵抗力」に関係なく、40ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # R団のサンダー（闇からの挑戦）。プラズマ（雷）20: トラッシュに「雷」エネルギーカードがあれば 1 枚自分につける
        AttackKey("PMCG6-042", 0): AttackEntry(
            DamageThenAttachEnergyFromDiscardToSelf(EnergyType.LIGHTNING),
            "プラズマ",
            text_ja="自分のトラッシュに「雷」エネルギーカードがあれば、1枚取り出して、自分につける。",
            play_text_ja="自分のトラッシュに「雷」エネルギーカードがあれば、1枚取り出して、自分につける。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エレクトロバーン（雷雷雷無）70: 自分にも、ついている「雷」エネルギーカードの枚数 × 10
        AttackKey("PMCG6-042", 1): AttackEntry(
            DamageAndSelfDamagePerAttachedEnergyCard(EnergyType.LIGHTNING, 10),
            "エレクトロバーン",
            text_ja="自分にも、自分についている「雷」エネルギーカードの数×10のダメージ。",
            play_text_ja="自分にも、自分についている「雷」エネルギーカードの数×10のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # イワーク（第1弾。タケシのイワークとは別のカード）。かたくなる（闘闘）: 次の相手の番に受けるダメージが 40 より小さければ 0（8 段階）
        AttackKey("PMCG1-054", 1): AttackEntry(
            ZeroDamageBelowNextTurn(40),
            "かたくなる",
            text_ja="次の相手の番に受けるダメージが0になる。ただしダメージが40以上の場合は、そのままダメージをうける。",
            play_text_ja="次の相手の番に受けるダメージが0になる。ただしダメージが40以上の場合は、そのままダメージをうける。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ラッタ（第1弾。コラッタから進化）。いかりのまえば（無無無）?: 相手の残りの HP の半分（10 の単位で切り上げ）を 1 段階の基本となるダメージにする
        AttackKey("PMCG1-062", 1): AttackEntry(
            HalfRemainingHpDamage(),
            "いかりのまえば",
            text_ja=HALF_REMAINING_HP_TEXT,
            play_text_ja=HALF_REMAINING_HP_TEXT,
            source=_KYUURA_PRINTED_TEXT,
        ),
        # R団のエビワラー（リーダーズスタジアム）。クロスカウンター（闘）: kyuura の最新の説明 LD-PMCG5-054-ATK0。次の相手の番、相手のワザのダメージを受けたら
        # コイン（はたらくとき）の「おもて」で受けたダメージの 2 倍を返す（Retaliation の倍数・コインの条件）
        AttackKey("PMCG5-054", 0): AttackEntry(
            ReturnReceivedDamageOnHeads(2),
            "クロスカウンター",
            text_ja=CROSS_COUNTER_TEXT.format(multiplier=2),
            play_text_ja="次の相手の番、このカードが相手のワザによるダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）コインを投げる。「おもて」なら、"
                         "このカードが受けたダメージの2倍のダメージを、相手に与える。",
            source="LD-PMCG5-054-ATK0",
        ),
        # タケシのイシツブテ（リーダーズスタジアム。PMCG5-047。PMCG5-046 とは別のカード）。たすけをよぶ（闘）: コインの「おもて」で山札の「タケシのポケモン」（たねポケモン）を
        # 0〜1 匹ベンチに出し、山札を切る（ベンチに空きがなければ使えない）
        AttackKey("PMCG5-047", 0): AttackEntry(
            PutOwnerBasicFromDeckOntoBenchOnHeads("タケシ"),
            "たすけをよぶ",
            text_ja="コインを投げて「おもて」なら、「タケシのポケモン」(進化カード以外)を自分の山札から1枚選び出し、自分のベンチに出してよい。その後、その山札をよく切る。"
                    "(自分のベンチに空きが無い時、このワザは使えない)",
            play_text_ja="コインを投げて「おもて」なら、「タケシのポケモン」(進化カード以外)を自分の山札から1枚選び出し、自分のベンチに出してよい。その後、その山札をよく切る。"
                         "(自分のベンチに空きが無い時、このワザは使えない)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # スパイラルショット（闘無）20: 抵抗力（4 段階）だけを計算しない
        AttackKey("PMCG5-047", 1): AttackEntry(
            DamageIgnoringResistance(),
            "スパイラルショット",
            text_ja="このワザのダメージは、「抵抗力」の影響を受けない。",
            play_text_ja="このワザのダメージは、「抵抗力」の影響を受けない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サカキのニャース（闇からの挑戦。PMCG6-068。PMCG6-063 とは別のカード）。てつだうふり（無）: コインの「おもて」で相手の山札の一番上をトレーナーならトラッシュ、
        # それ以外なら相手の手札に（ドローではない。山札を切らない）
        AttackKey("PMCG6-068", 0): AttackEntry(
            CoinOpponentDeckTopDiscardTrainerElseHand(),
            "てつだうふり",
            text_ja=OPPONENT_DECK_TOP_TEXT,
            play_text_ja=OPPONENT_DECK_TOP_TEXT,
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ダブルひっかき（無無）20×: コイン 2 枚の「おもて」の数 × 20
        AttackKey("PMCG6-068", 1): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=20),
            "ダブルひっかき",
            text_ja="コインを2枚投げ、「おもて」の数×20のダメージ。",
            play_text_ja="コインを2枚投げ、「おもて」の数×20のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.46（docs/continuous-powers-v0.46.md）。11 枚のワザ。処理に使う文面は kyuura の印刷の文面（kyuura データの採用）
        # バリヤード（ポケモンジャングル）。ヨガのポーズ（超無）10+: 相手（対戦ポケモン。p.320）のダメージカウンター × 10 を加える（ルージュラの「相手のポケモン」ではないので CD4 に当たらない）
        AttackKey("PMCG2-027", 0): AttackEntry(
            DamagePlusDefenderCounters(10, scope_ambiguous=False),
            "ヨガのポーズ",
            text_ja="相手にのっているダメージカウンター×10のダメージを追加する。",
            play_text_ja="相手にのっているダメージカウンター×10のダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのミニリュウ（リーダーズスタジアム）。しっぽでつく（無無）10+: コインの「おもて」で 20 を追加（v0.31 の型）
        AttackKey("PMCG5-063", 0): AttackEntry(
            CoinBonusDamage(20),
            "しっぽでつく",
            text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、20ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのフシギソウ（闇からの挑戦。エリカのフシギダネから進化）。ダブルはっぱカッター（草草草）40×: コイン 2 枚の「おもて」の数 × 40（既存のコインのダメージ）
        AttackKey("PMCG6-010", 0): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=40),
            "ダブルはっぱカッター",
            text_ja="コインを2枚投げ、「おもて」の数×40のダメージ。",
            play_text_ja="コインを2枚投げ、「おもて」の数×40のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいオコリザル（ロケット団。マンキーから進化）。あばれくるう（闘闘）40: ダメージを与えた後、自分をこんらん（ダメージを与えなかったら Z23）
        AttackKey("PMCG4-041", 0): AttackEntry(
            DamageThenSelfConfuse(),
            "あばれくるう",
            text_ja="ダメージを与えた後、自分は「こんらん」状態になる。",
            play_text_ja="ダメージを与えた後、自分は「こんらん」状態になる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ドードリオ（ポケモンジャングル。ドードーから進化）。いかり（無無無）10+: 自分のダメージカウンター × 10 を加える（v0.34 のカラカラの「いかり」と同じ型）
        AttackKey("PMCG2-040", 0): AttackEntry(
            DamagePlusOwnCounters(10),
            "いかり",
            text_ja="自分にのっているダメージカウンター×10のダメージを追加する。",
            play_text_ja="自分にのっているダメージカウンター×10のダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいベトベトン（ロケット団。ベトベターから進化）。ヘドロパンチ（草草）20: ダメージのあと相手をどく（コインなし）
        AttackKey("PMCG4-007", 0): AttackEntry(
            PoisonOpponent(),
            "ヘドロパンチ",
            text_ja="相手を「どく」状態にする。",
            play_text_ja="相手を「どく」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # わるいラフレシア（ロケット団。わるいクサイハナから進化）。はなびらのうず（草草草）30×: 同じ 3 枚のコインの「おもて」の数 × 30・2 枚以上「おもて」なら自分をこんらん
        AttackKey("PMCG4-010", 0): AttackEntry(
            CoinsTimesDamageSelfConfuse(coins=3, per=30, at_least=2),
            "はなびらのうず",
            text_ja="コインを3枚投げて「おもて」の数×30のダメージ。2枚以上「おもて」なら、自分は「こんらん」状態になる",
            play_text_ja="コインを3枚投げて「おもて」の数×30のダメージ。2枚以上「おもて」なら、自分は「こんらん」状態になる",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カビゴン（ポケモンジャングル）。のしかかり（無無無無）30: コインの「おもて」で相手をマヒ
        AttackKey("PMCG2-047", 0): AttackEntry(
            ParalyzeOnHeads(),
            "のしかかり",
            text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのフシギバナ（闇からの挑戦。エリカのフシギソウから進化）。せいちょう（草）: コインの「おもて」で手札の「草」エネルギーカードを最大 2 枚このカードにつける（通常の操作の回数に数えない。0 枚は HC7）
        AttackKey("PMCG6-017", 0): AttackEntry(
            AttachEnergyFromHandOnHeads(EnergyType.GRASS, 2),
            "せいちょう",
            text_ja="コインを投げて「おもて」なら、自分の手札にある「草」エネルギーカードを最大2枚、このカードにつける。",
            play_text_ja="コインを投げて「おもて」なら、自分の手札にある「草」エネルギーカードを最大2枚、このカードにつける。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # かくさんソーラービーム（草草草草）20: 相手の控えポケモンをちょうど 2 匹選び、「弱点・抵抗力」に関係なくそれぞれ 20（控えが 1 匹なら FC1）
        AttackKey("PMCG6-017", 1): AttackEntry(
            DamageThenExactBenchTargets(targets=2, bench_damage=20),
            "かくさんソーラービーム",
            text_ja="相手の控えポケモンを2匹選び、それらのポケモンにも、「弱点・抵抗力」に関係なく、それぞれ20ダメージ。",
            play_text_ja="相手の控えポケモンを2匹選び、それらのポケモンにも、「弱点・抵抗力」に関係なく、それぞれ20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのタマタマ（リーダーズスタジアム）。リフレクター（超）: 次の相手の番、受けるダメージは 8 段階で半分（切りすて）（持続する効果 HalvedDamage）
        AttackKey("PMCG5-012", 0): AttackEntry(
            HalveDamageNextTurn(),
            "リフレクター",
            text_ja="次の相手の番、このカードが受けるダメージは半分(切りすて)になる。(ダメージ以外の効果はそのまま)",
            play_text_ja="次の相手の番、このカードが受けるダメージは半分(切りすて)になる。(ダメージ以外の効果はそのまま)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タマゴばくだん（草無）40: コインの「うら」なら相手へのダメージはなくなり、自分に 20（ワザの失敗ではない。v0.11 の型）
        AttackKey("PMCG5-012", 1): AttackEntry(
            SelfDamageInsteadOnTails(20),
            "タマゴばくだん",
            text_ja="コインを投げて「うら」なら、相手へのダメージはなくなり、自分に20ダメージ。",
            play_text_ja="コインを投げて「うら」なら、相手へのダメージはなくなり、自分に20ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # エリカのナッシー（リーダーズスタジアム。エリカのタマタマから進化）。サイコエクスチェンジ（超）: 手札をすべて山札にもどし、切ってから 5 枚引く
        AttackKey("PMCG5-013", 0): AttackEntry(
            ShuffleHandIntoDeckThenDraw(5),
            "サイコエクスチェンジ",
            text_ja="自分の手札をすべて山札にもどし、山札をよく切る。その後、カードを5枚引いて、手札にする。",
            play_text_ja="自分の手札をすべて山札にもどし、山札をよく切る。その後、カードを5枚引いて、手札にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ふみつけ（草無無）30+: コインの「おもて」で 10 を追加
        AttackKey("PMCG5-013", 1): AttackEntry(
            CoinBonusDamage(10),
            "ふみつけ",
            text_ja="コインを投げて「おもて」なら、10ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、10ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.47（docs/fossil-hidden-info-v0.47.md）。13 枚のうちポケモン 11 枚のワザ。処理に使う文面は kyuura の印刷の文面（kyuura データの採用。13 枚とも kyuura に最新の説明・
        # エラッタ・裁定の記録がない）
        # オムナイト（化石の秘密。なにかの化石から進化）。みずでっぽう（水）10+: 必要なエネルギーはすべて「水」なので v0.6 のハイドロポンプと同じ型（多い「水」1 つにつき 10。2 つまで）
        AttackKey("PMCG3-015", 0): AttackEntry(
            ExtraEnergyDamage(energy_type=EnergyType.WATER, per_energy=10, max_extra=2),
            "みずでっぽう",
            text_ja="ワザに必要なぶんよりも多く「水」エネルギーカードがついている時、多いエネルギー1つにつき10ダメージを追加する。(ダメージ追加は2つぶんまで)",
            play_text_ja="ワザに必要なぶんよりも多く「水」エネルギーカードがついている時、多いエネルギー1つにつき10ダメージを追加する。(ダメージ追加は2つぶんまで)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # オムスター（化石の秘密。オムナイトから進化）。みずでっぽう（水無）20+: 必要なエネルギーに無色がまざるので v0.31 の型（多いエネルギーの数が読み方で変われば HC4）
        AttackKey("PMCG3-021", 0): AttackEntry(
            ExtraEnergyDamageMixed(EnergyType.WATER, 10, 2),
            "みずでっぽう",
            text_ja="ワザに必要なぶんよりも多く「水」エネルギーカードがついている時、多いエネルギー1つにつき10ダメージを追加する。(ダメージ追加は2つぶんまで)",
            play_text_ja="ワザに必要なぶんよりも多く「水」エネルギーカードがついている時、多いエネルギー1つにつき10ダメージを追加する。(ダメージ追加は2つぶんまで)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # とげキャノン（水水）30×: コイン 2 枚の「おもて」の数 × 30
        AttackKey("PMCG3-021", 1): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=30),
            "とげキャノン",
            text_ja="コインを2枚投げて「おもて」の数×30のダメージ。",
            play_text_ja="コインを2枚投げて「おもて」の数×30のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # カブト（化石の秘密。なにかの化石から進化）。ひっかく（無）10
        AttackKey("PMCG3-035", 0): AttackEntry(DAMAGE_ONLY, "ひっかく"),
        # カブトプス（化石の秘密。カブトから進化）。するどいかま（闘闘）30
        AttackKey("PMCG3-040", 0): AttackEntry(DAMAGE_ONLY, "するどいかま"),
        # すいとる（闘闘闘闘）40: 与えたダメージ（最終ダメージ）の半分（切り上げ）のカウンターを自分からとりのぞく（v0.4d のメガドレインと同じ型。のっている数まで）
        AttackKey("PMCG3-040", 1): AttackEntry(
            DamageAndDrain(),
            "すいとる",
            text_ja="相手にあたえたダメージの半分(切り上げ)のダメージカウンターを自分からとりのぞく。",
            play_text_ja="相手にあたえたダメージの半分(切り上げ)のダメージカウンターを自分からとりのぞく。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # プテラ（化石の秘密。なにかの化石から進化）。つばさでうつ（無無無）30
        AttackKey("PMCG3-041", 0): AttackEntry(DAMAGE_ONLY, "つばさでうつ"),
        # マンキー（ポケモンジャングル）。ひっかく（無）10
        AttackKey("PMCG2-028", 0): AttackEntry(DAMAGE_ONLY, "ひっかく"),
        # コラッタ（ロケット団）。でんこうせっか（無）10+: コインの「おもて」で 10 を追加
        AttackKey("PMCG4-045", 0): AttackEntry(
            CoinBonusDamage(10),
            "でんこうせっか",
            text_ja="コインを投げて「おもて」なら、10ダメージを追加する。",
            play_text_ja="コインを投げて「おもて」なら、10ダメージを追加する。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # スリーパー（化石の秘密。スリープから進化）。みらいよち（超）: 自分または相手の山札の上から 3 枚まで見て並べかえる（0 枚は GS1）
        AttackKey("PMCG3-032", 0): AttackEntry(
            ArrangeDeckTopEffect(3),
            "みらいよち",
            text_ja="自分または相手の山札の上から3枚まで見て、好きな順番に入れ替えて、もとの山札の上にもどす。",
            play_text_ja="自分または相手の山札の上から3枚まで見て、好きな順番に入れ替えて、もとの山札の上にもどす。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナイトヘッド（超超超）30: v0.42 のゲンガーの「ナイトヘッド」と同じ文面・同じ型（相手の控えを 1 匹選び「弱点・抵抗力」に関係なく 10。控えがいなければ何もしない）
        AttackKey("PMCG3-032", 1): AttackEntry(
            DamageThenChosenBenchDamage(10),
            "ナイトヘッド",
            text_ja="相手の控えポケモンから1匹選び、「弱点・抵抗力」に関係なく10ダメージ。相手に控えポケモンがいない時には、この効果はない。",
            play_text_ja="相手の控えポケモンから1匹選び、「弱点・抵抗力」に関係なく10ダメージ。相手に控えポケモンがいない時には、この効果はない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # マチスのイーブイ（リーダーズスタジアム）。おどろかす（無）: 相手の手札を位置で 1 枚選んで見る → 相手の山札にもどさせて切る（相手の手札が 0 枚なら FC1）
        AttackKey("PMCG5-062", 0): AttackEntry(
            LookOpponentHandCardToDeck(),
            "おどろかす",
            text_ja="相手の手札から、おもてを見ないで1枚選び、そのカードを見る。その後、そのカードを相手の山札にもどさせ、その山札をよく切る。",
            play_text_ja="相手の手札から、おもてを見ないで1枚選び、そのカードを見る。その後、そのカードを相手の山札にもどさせ、その山札をよく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ひっかく（無無）20
        AttackKey("PMCG5-062", 1): AttackEntry(DAMAGE_ONLY, "ひっかく"),
        # マチスのサンダース（リーダーズスタジアム。マチスのイーブイから進化）。こうしゅうは（雷無）20: ダメージ → コインの「おもて」で相手プレイヤーのトレーナーの使用を禁止（次の相手の番の終わりまで）
        AttackKey("PMCG5-042", 0): AttackEntry(
            DamageThenLockOpponentTrainersOnHeads(),
            "こうしゅうは",
            text_ja="コインを投げて「おもて」なら、次の相手の番が終わるまで、相手プレイヤーは「トレーナーカード」を使うことができない。",
            play_text_ja="コインを投げて「おもて」なら、次の相手の番が終わるまで、相手プレイヤーは「トレーナーカード」を使うことができない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # いかりのサンダー（雷雷雷）30+: 自分のカウンター × 10 を加える → コインの「うら」で自分にも 30
        AttackKey("PMCG5-042", 1): AttackEntry(
            DamagePlusOwnCountersThenSelfDamageOnTails(per=10, self_damage=30),
            "いかりのサンダー",
            text_ja="自分にのっているダメージカウンターの数×10のダメージを追加する。その後、コインを投げて「うら」なら、自分にも30ダメージ。",
            play_text_ja="自分にのっているダメージカウンターの数×10のダメージを追加する。その後、コインを投げて「うら」なら、自分にも30ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # コダック（化石の秘密）。ずつう（超）: 次の相手の番の終わりまで、相手プレイヤーはトレーナーカードを使えない（プレイヤーに与える期限のある禁止）
        AttackKey("PMCG3-010", 0): AttackEntry(
            LockOpponentTrainersNextTurn(),
            "ずつう",
            text_ja="次の相手の番の終わりまで、相手プレイヤーはトレーナーカードを使うことができない。",
            play_text_ja="次の相手の番の終わりまで、相手プレイヤーはトレーナーカードを使うことができない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # みだれひっかき（水）10×: コイン 3 枚の「おもて」の数 × 10
        AttackKey("PMCG3-010", 1): AttackEntry(
            CoinFlipDamage(coins=3, damage_per_heads=10),
            "みだれひっかき",
            text_ja="コインを3枚投げて「おもて」の数×10のダメージ。",
            play_text_ja="コインを3枚投げて「おもて」の数×10のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.48（docs/effective-pokemon-properties-v0.48.md）。処理に使う文面は kyuura の印刷の文面（7 枚とも kyuura に最新の説明・エラッタ・裁定の記録がない）
        # ポリゴン（第1弾）。テクスチャー1（無）: 相手の対戦ポケモンの弱点を無色以外の好きな色に変える（期限なし。ベンチにもどる・場をはなれる・進化で消える）
        AttackKey("PMCG1-064", 0): AttackEntry(
            ChangeOpponentWeakness(),
            "テクスチャー1",
            text_ja="相手の対戦ポケモンの弱点を好きな「色」にかえる。ただし「無色」にはできない。相手がベンチに戻った時にその効果はきえる。",
            play_text_ja="相手の対戦ポケモンの弱点を好きな「色」にかえる。ただし「無色」にはできない。相手がベンチに戻った時にその効果はきえる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # テクスチャー2（無無）: 自分の抵抗力の色を無色以外の好きな色に変える（数は変えない）
        AttackKey("PMCG1-064", 1): AttackEntry(
            ChangeOwnResistance(),
            "テクスチャー2",
            text_ja="自分の抵抗力を好きな「色」にかえる。ただし「無色」にはできない。自分がベンチに戻ったときにその効果はきえる。",
            play_text_ja="自分の抵抗力を好きな「色」にかえる。ただし「無色」にはできない。自分がベンチに戻ったときにその効果はきえる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ポリゴン（ロケット団）。テクスチャー1（無）: 第1弾と同じ処理（書き方だけが違う）
        AttackKey("PMCG4-050", 0): AttackEntry(
            ChangeOpponentWeakness(),
            "テクスチャー1",
            text_ja="相手の対戦ポケモンの「弱点」を、無色以外の好きな「色」に変える。この効果は、そのポケモンがバトル場をはなれた時に消える。",
            play_text_ja="相手の対戦ポケモンの「弱点」を、無色以外の好きな「色」に変える。この効果は、そのポケモンがバトル場をはなれた時に消える。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # サイケこうせん（無無無）20: ダメージ → コインの「おもて」でこんらん（v0.3c の「あやしいひかり」と同じ型）
        AttackKey("PMCG4-050", 1): AttackEntry(
            ConfuseOnHeads(),
            "サイケこうせん",
            text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「こんらん」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # モルフォン（ポケモンジャングル）。りんぷん（草草）10: ダメージ → 同じコインの「おもて」でどくとこんらん
        AttackKey("PMCG2-015", 0): AttackEntry(
            DamageThenPoisonAndConfuseOnHeads(),
            "りんぷん",
            text_ja="コインを投げて「おもて」なら、相手を「どく」と「こんらん」状態にする。",
            play_text_ja="コインを投げて「おもて」なら、相手を「どく」と「こんらん」状態にする。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのゴース（闇からの挑戦）。ガスでつつむ（超超）30: 説明のないワザ
        AttackKey("PMCG6-049", 0): AttackEntry(DAMAGE_ONLY, "ガスでつつむ"),
        # ナツメのゴースト（闇からの挑戦。ナツメのゴースから進化）。ナイトスピリッツ（超超）30×: 自分の場の名前の合うポケモンの数だけコイン
        AttackKey("PMCG6-050", 0): AttackEntry(
            CoinsPerNamedPokemonDamage(names=("ナツメのゴース", "ナツメのゴースト", "ナツメのゲンガー"), per=30),
            "ナイトスピリッツ",
            text_ja="自分の場にいる「ナツメのゴース」「ナツメのゴースト」「ナツメのゲンガー」の数だけコインを投げ、「おもて」の数×30のダメージ。",
            play_text_ja="自分の場にいる「ナツメのゴース」「ナツメのゴースト」「ナツメのゲンガー」の数だけコインを投げ、「おもて」の数×30のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ナツメのゲンガー（闇からの挑戦。ナツメのゴーストから進化）。ダメージぞうふく（超）: ダメージカウンターがのっている相手のポケモン全員に 1 個ずつのせる（ダメージではない）
        AttackKey("PMCG6-054", 0): AttackEntry(
            PlaceCountersOnDamagedOpponentPokemon(1),
            "ダメージぞうふく",
            text_ja="相手の場の、ダメージカウンターがのっているポケモン全員に、ダメージカウンターを1つずつのせる。",
            play_text_ja="相手の場の、ダメージカウンターがのっているポケモン全員に、ダメージカウンターを1つずつのせる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # やみのこえ（超超超）40: ダメージ → 相手がきぜつしなかったらコイン 2 枚 → すべて「おもて」なら相手を山札にもどして切る（控えがいなくても使える）
        AttackKey("PMCG6-054", 1): AttackEntry(
            DamageThenCoinsReturnOpponentToDeck(2),
            "やみのこえ",
            text_ja="相手が「きぜつ」しなかったなら、コインを2枚投げる。すべて「おもて」なら、相手と、相手についているすべてのカードを持ち主の山札にもどし、その山札をよく切る。",
            play_text_ja="相手が「きぜつ」しなかったなら、コインを2枚投げる。すべて「おもて」なら、相手と、相手についているすべてのカードを持ち主の山札にもどし、その山札をよく切る。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # キョウのメタモン（闇からの挑戦）。きょだいか（無）: コインの「おもて」で最大HPは 80（バトル場をはなれると消える）
        AttackKey("PMCG6-072", 0): AttackEntry(
            SetMaxHpOnHeads(80),
            "きょだいか",
            text_ja="コインを投げて「おもて」なら、このカードの最大HPは「80」になる。(バトル場をはなれた時、この効果は消える)",
            play_text_ja="コインを投げて「おもて」なら、このカードの最大HPは「80」になる。(バトル場をはなれた時、この効果は消える)",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # はたく（無）10: 「きょだいか」の効果がはたらいているとき 30（p.321 の 1 段階。最大HPと同じ効果の有無を見る）
        AttackKey("PMCG6-072", 1): AttackEntry(
            DamageIfSelfMaxHpSet("きょだいか", 30),
            "はたく",
            text_ja="このカードに「きょだいか」の効果がはたらいているとき、このワザのダメージは「30」になる。",
            play_text_ja="このカードに「きょだいか」の効果がはたらいているとき、このワザのダメージは「30」になる。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.49（docs/virtual-attacks-transformation-v0.49.md）。処理に使う文面は kyuura の印刷の文面
        # ナツメのフーディン。メガバーン（超無無無）60: ダメージ → 次の自分の番、このカードは「メガバーン」を使えない（v0.41 の DamageThenLockSelf。使えないワザは
        # ``AttackKey`` で探すので、［サイコリンク］で同じワザを持つ出どころが変わっても当てはまる）
        AttackKey("PMCG6-053", 0): AttackEntry(
            DamageThenLockSelf(),
            "メガバーン",
            text_ja="次の自分の番、このカードは「メガバーン」を使えない。",
            play_text_ja="次の自分の番、このカードは「メガバーン」を使えない。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # タケシのキュウコン。おにび（炎炎）30（説明文なし）
        AttackKey("PMCG5-019", 0): AttackEntry(DAMAGE_ONLY, "おにび"),
        # v0.50（docs/mew-devolution-spray-v0.50.md）。ミュウ（化石の秘密）。処理に使う文面は kyuura の印刷の文面
        # サイコウェーブ（超）10×: 相手の対戦ポケモンについているエネルギーカードの枚数 × 10 が基本となるダメージ（「サイコキネシス」の「10+」とは違う）
        AttackKey("PMCG3-033", 0): AttackEntry(
            DamageTimesDefenderEnergyCards(10),
            "サイコウェーブ",
            text_ja="相手についているエネルギーカード×10のダメージ。",
            play_text_ja="相手についているエネルギーカード×10のダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # たいかビーム（超超）: 自分・相手の場の、進化カードの重なっているポケモンを 1 匹選び、いちばん上の進化カードを持ち主の手札にもどす（退化）
        AttackKey("PMCG3-033", 1): AttackEntry(
            DevolveChosenPokemon(),
            "たいかビーム",
            text_ja=DEVOLUTION_BEAM_TEXT,
            play_text_ja=DEVOLUTION_BEAM_TEXT,
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.51（docs/discard-to-bench-v0.51.md）。ナツメのスリーパー（闇からの挑戦）。処理に使う文面は kyuura の印刷の文面
        # よみがえらせる（超）: 自分または相手のトラッシュのたねポケモンを 1 枚選び、持ち主のベンチに出す → 出したポケモンに HP の半分（切り捨て）のダメージカウンターをのせる
        AttackKey("PMCG6-051", 0): AttackEntry(
            BenchBasicFromEitherDiscard(),
            "よみがえらせる",
            text_ja=INVIGORATE_TEXT,
            play_text_ja=INVIGORATE_TEXT,
            source=_KYUURA_PRINTED_TEXT,
        ),
        # ふりこののろい（超超）20×: 相手の対戦ポケモンのダメージカウンターの数だけコインを投げ、「おもて」の数 × 20 が基本となるダメージ
        AttackKey("PMCG6-051", 1): AttackEntry(
            CoinsPerDefenderCountersDamage(20),
            "ふりこののろい",
            text_ja=PENDULUM_CURSE_TEXT.format(per=20),
            play_text_ja=PENDULUM_CURSE_TEXT.format(per=20),
            source=_KYUURA_PRINTED_TEXT,
        ),
        # v0.52（docs/field-return-v0.52.md 4・5 章）。エリカのハクリュー（PMCG5-066。エリカのミニリュウから進化）
        # ふぶき（無無無）30: 1 枚のコインで「おもて」なら相手の控え全員、「うら」なら自分の控え全員に 10（弱点・抵抗力なし）。フリーザーの「ふぶき」と同じ型
        AttackKey("PMCG5-066", 0): AttackEntry(
            DamageThenCoinBenchDamageEitherSide(10),
            "ふぶき",
            text_ja="コインを投げ、「おもて」なら相手の控えポケモン全員に、「うら」なら自分の控えポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            play_text_ja="コインを投げ、「おもて」なら相手の控えポケモン全員に、「うら」なら自分の控えポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ10ダメージ。",
            source=_KYUURA_PRINTED_TEXT,
        ),
        # つれさる（無無無無）: 自分と相手の対戦ポケモンを、ついているすべてのカードとともにそれぞれの山札にもどし、それぞれの山札を切る（きぜつではない）
        AttackKey("PMCG5-066", 1): AttackEntry(
            ReturnBothActivesToDeck(),
            "つれさる",
            text_ja=TAKE_AWAY_TEXT,
            play_text_ja=TAKE_AWAY_TEXT,
            source=_KYUURA_PRINTED_TEXT,
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
        # 突風（v0.21）p.255。図版の文面は最新の説明と同じ（第1弾の版ではない可能性が高い）。kyuura の写し（第1弾の印刷の転記）にある
        # 「相手に控えがいない場合は使えない」は最新の説明にないので、控えがいないときは UNRESOLVED（docs/gust-v0.21.md の GW5）
        "PMCG1-072": TrainerEntry(
            SwitchOpponentWithBench(),
            "突風",
            "相手の場の対戦ポケモンと控えポケモンを入れ替える。どの控えポケモンを出させるかは、自分が自由に選ぶことができる。相手に控えがいない場合は使えない。",
            "相手の控えポケモンを1匹選び、相手の対戦ポケモンと入れ替える。",
            "P43 p.255",
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
        # オーキドはかせ（v0.19）p.255。図版の文面は kyuura の写しと同じ。最新の説明は「すべてトラッシュする。その後、…7枚引いて、手札に
        # する。」（docs/professor-oak-v0.19.md）
        # エネルギー回収（v0.23）p.257。図版の文面は第1弾の印刷（kyuura の写し）と違う版。処理は最新の説明（手札から 1 枚選んでトラッシュ →
        # トラッシュの基本エネルギーカード（トラッシュしたカードを除く）を最大 2 枚選び出し、手札に加える。docs/energy-retrieval-v0.23.md）
        "PMCG1-076": TrainerEntry(
            DiscardFromHandThenRetrieveEnergy(discard=1, retrieve=2),
            "エネルギー回収",
            "手札から1枚のカードをすてることによって、トラッシュから2枚の好きなエネルギーカードをひろって、手札に加えることができる。",
            "手札からカードを1枚選んでトラッシュしなければ、このカードは使えない。あなたのトラッシュから「基本エネルギーカード」を最大2枚選び出し、手札に加える。ただし、このカードを使うためにトラッシュしたカードを選ぶことはできない。",
            "P43 p.257",
        ),
        "PMCG1-077": TrainerEntry(
            DiscardHandAndDraw(count=7),
            "オーキドはかせ",
            "自分の手札を全部すてて、新たに7枚のカードを自分の山札から引いて手札にする。",
            "あなたの手札をすべてトラッシュする。その後、山札からカードを7枚引いて、手札にする。",
            "P43 p.255",
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
        # パソコン通信（v0.22）p.260（p.310 の「使うための条件」の例にも同じ最新の説明）。図版の文面は kyuura の写しと同じ（印刷の文面）。
        # 処理は最新の説明（手札から 2 枚選んでトラッシュ → 山札から 1 枚選び出し、手札に加える → その山札をよく切る。docs/computer-search-v0.22.md）
        "PMCG1-090": TrainerEntry(
            DiscardFromHandThenSearchDeck(discard=2, search=1),
            "パソコン通信",
            "手札から2枚カードをすてることによって、山札から好きなカードを1枚選んで手札にすることができる。そのあとで山札をよくきってもとに戻す。",
            "手札からカードを2枚選んでトラッシュしなければ、このカードは使えない。あなたの山札からカードを1枚選び出し、手札に加える。その後、その山札をよく切る。",
            "P43 p.260",
        ),
        # ポケモン交換おじさん（v0.24）p.259。図版の文面は kyuura の写しと同じ（第1弾の印刷）。処理は最新の説明（手札のたねポケモン・進化カードを
        # 見せて山札にもどす → 山札のたねポケモン・進化カードを見せて手札に加える → その山札をよく切る。docs/pokemon-trader-v0.24.md）
        "PMCG1-093": TrainerEntry(
            TradePokemonWithDeck(),
            "ポケモン交換おじさん",
            "自分の山札から好きなポケモンカードか進化カードを1枚選んで、手札のポケモンカードか進化カードと交換することができる。そのあとで、自分の山札をよくきる。交換するカードは相手に見せなければならない。",
            "手札から「たねポケモン」または「進化カード」を1枚選び、相手プレイヤーに見せてから、あなたの山札にもどす。それができないとき、このカードは使えない。あなたの山札から「たねポケモン」または「進化カード」を1枚選び出し、相手プレイヤーに見せてから、手札に加える。その後、その山札をよく切る。",
            "P43 p.259",
        ),
        "PMCG1-094": TrainerEntry(
            EvolveBasicToStage2(),
            "ポケモン育て屋さん",
            "ポケモンを進化させるときに使う。2進化カードをいきなりつけることができる。",
            "このカードは、あなたが自分の場にいるポケモンを進化させるときにだけ、使える。そのポケモンの上に「2進化カード」を直接のせ、1進化をとばして「2進化ポケモン」に進化させる。",
            "P43 p.259",
        ),
        # サカキ（v0.44。闇からの挑戦。kyuura データの採用。処理に使う文面は kyuura の印刷の文面。選んだ「サカキのポケモン」に、今の番だけ、場に出た番・進化した番でも
        # 進化させてよい記録を置く。英語版の「or if this is your first turn」は持ち込まない。docs/search-evolution-once-attacks-v0.44.md 4 章）
        "PMCG6-095": TrainerEntry(
            EvolutionPermissionForOwnerPokemon("サカキ"),
            "サカキ",
            "あなたの場にいる「サカキのポケモン」を1匹選ぶ。あなたがのぞむなら、そのポケモンが場に出たのが今の番でも、そのポケモンを進化させてよい。また、進化したそのポケモンを、同じ番で、さらに進化させてもよい。(ポケモンを進化させる時には、あなたの手札から「進化カード」を出して、そのポケモンの上にのせる)",
            "あなたの場にいる「サカキのポケモン」を1匹選ぶ。あなたがのぞむなら、そのポケモンが場に出たのが今の番でも、そのポケモンを進化させてよい。また、進化したそのポケモンを、同じ番で、さらに進化させてもよい。(ポケモンを進化させる時には、あなたの手札から「進化カード」を出して、そのポケモンの上にのせる)",
            _KYUURA_PRINTED_TEXT,
        ),
        # v0.47（docs/fossil-hidden-info-v0.47.md 2 章）。ポケモンとして場に出せるトレーナーカード。処理に使う文面は kyuura の印刷の文面。場での HP 10 は pcg-search.com の
        # 同じ版のページの値（kyuura の写しのトレーナーのデータに HP の欄がない。採用の記録に書いた）
        "PMCG3-046": TrainerEntry(PlayAsPokemon(hp=10, role="fossil"), "なにかの化石", FOSSIL_TEXT, FOSSIL_TEXT, _KYUURA_PRINTED_TEXT),
        "PMCG1-091": TrainerEntry(PlayAsPokemon(hp=10, role="doll"), "ピッピ人形", DOLL_TEXT, DOLL_TEXT, _KYUURA_PRINTED_TEXT),
        # v0.49（docs/virtual-attacks-transformation-v0.49.md 6 章）。思い出させる: この番だけ、対戦ポケモンが重なっている進化前のカードのワザを使ってよい。処理に使う文面は
        # kyuura の印刷の文面（英語版の「any attack from its Basic Pokémon card or any Evolution card attached to it」は持ち込まない）
        "PMCG5-071": TrainerEntry(RecallPreEvolutionAttacks(), "思い出させる", RECALL_TEXT, RECALL_TEXT, _KYUURA_PRINTED_TEXT),
        # v0.50（docs/mew-devolution-spray-v0.50.md 4 章）。退化スプレー: 自分の進化ポケモンを 1 匹選び、進化カードを好きな枚数（0 枚を含む）はがしてトラッシュする。処理に
        # 使う文面は kyuura の印刷の文面（英語版の「a Stage of Evolution」・退化スプレーHYPER の文面は持ち込まない）
        "PMCG1-086": TrainerEntry(DevolveOwnPokemon(), "退化スプレー", DEVOLUTION_SPRAY_TEXT, DEVOLUTION_SPRAY_TEXT, _KYUURA_PRINTED_TEXT),
        # v0.51（docs/discard-to-bench-v0.51.md 4 章）。処理に使う文面は kyuura の印刷の文面（英語版の「Basic Pokémon card」・「You can't play … if … Bench is full」、のちの版
        # （ポケモンジム第1弾）の「…このカードは使えない」は持ち込まない）
        # 元気のかけら: 自分のトラッシュのたねポケモンのカードを、HP の半分（きりすて）のダメージカウンターをのせた状態で自分のベンチに出してよい
        "PMCG1-078": TrainerEntry(BenchBasicFromOwnDiscardWithCounters(), "元気のかけら", REVIVE_TEXT, REVIVE_TEXT, _KYUURA_PRINTED_TEXT),
        # ポケモンの笛: 相手のトラッシュのたねポケモンのカードを、使ったプレイヤーが選び、相手のベンチに出させてよい
        "PMCG1-084": TrainerEntry(BenchBasicFromOpponentDiscard(), "ポケモンの笛", POKEMON_FLUTE_TEXT, POKEMON_FLUTE_TEXT, _KYUURA_PRINTED_TEXT),
        # v0.52（docs/field-return-v0.52.md 3 章）。処理に使う文面は kyuura の印刷の文面（英語版の「Shuffle it … into your deck」「return its Basic Pokémon card to your hand.
        # (Discard all cards attached to that card.)」は持ち込まない）
        # フジろうじん: 自分の控えポケモンを 1 匹選び、そのカードとついているカードすべてを自分の山札にもどして切る
        "PMCG3-048": TrainerEntry(ReturnBenchedPokemonToDeck(), "フジろうじん", MR_FUJI_TEXT, MR_FUJI_TEXT, _KYUURA_PRINTED_TEXT),
        # ポケモン回収: 自分の場のポケモン 1 匹のいちばん下のカードを手札に、進化カード・エネルギーカードをトラッシュに。バトル場なら控えからバトル場に出す
        "PMCG1-092": TrainerEntry(ReturnOwnPokemonBasicToHand(), "ポケモン回収", SCOOP_UP_TEXT, SCOOP_UP_TEXT, _KYUURA_PRINTED_TEXT),
        # v0.53（docs/search-retrieval-trainers-v0.53.md 3 章）。山札・トラッシュからカードを選ぶトレーナー。処理に使う文面は kyuura の印刷の文面（英語版の「basic Energy」
        # 「Basic Pokémon or Evolution card」「in order to」「Shuffle … into your deck」などは持ち込まない）
        # エネルギー転送: 山札の基本エネルギーカードを 1 枚、見せずに手札に加えて切る（選べなければ ST1）
        "PMCG3-044": TrainerEntry(SearchDeckTrainer(ENERGY_SEARCH_TEXT, CardFilter("basic_energy"), 1, optional=False, reveal=False),
                                  "エネルギー転送", ENERGY_SEARCH_TEXT, ENERGY_SEARCH_TEXT, _KYUURA_PRINTED_TEXT),
        # モンスターボール: コインの「おもて」なら、山札のたねポケモン・進化カードを 0〜1 枚、見せて手札に加えて切る（「うら」なら何もしない）
        "PMCG2-048": TrainerEntry(SearchDeckTrainer(POKE_BALL_TEXT, CardFilter("pokemon"), 1, optional=True, reveal=True, coin=True),
                                  "モンスターボール", POKE_BALL_TEXT, POKE_BALL_TEXT, _KYUURA_PRINTED_TEXT),
        # ボスのやりかた: 山札の、名前が「わるい」で始まる進化カードを 1 枚、見せて手札に加えて切る（選べなければ ST1）
        "PMCG4-060": TrainerEntry(SearchDeckTrainer(BOSS_WAY_TEXT, CardFilter("pokemon", name_prefix="わるい", evolution_only=True), 1, optional=False, reveal=True),
                                  "ボスのやりかた", BOSS_WAY_TEXT, BOSS_WAY_TEXT, _KYUURA_PRINTED_TEXT),
        # タケシの育て方: 山札の「タケシのポケモン」（たねポケモン・進化カード）を 1 枚、見せて手札に加えて切る（選べなければ ST1）
        "PMCG5-077": TrainerEntry(SearchDeckTrainer(BROCK_TRAINING_TEXT, CardFilter("pokemon", name_prefix="タケシの"), 1, optional=False, reveal=True),
                                  "タケシの育て方", BROCK_TRAINING_TEXT, BROCK_TRAINING_TEXT, _KYUURA_PRINTED_TEXT),
        # カスミのなみだ: 手札を 1 枚トラッシュ（使うための条件）→ 山札の「水」の基本エネルギーカードを 0〜2 枚、見せて手札に加えて切る
        "PMCG5-069": TrainerEntry(SearchDeckTrainer(MISTYS_TEARS_TEXT, CardFilter("basic_energy", energy_type=EnergyType.WATER), 2, optional=True, reveal=True,
                                                    discard_cost=1),
                                  "カスミのなみだ", MISTYS_TEARS_TEXT, MISTYS_TEARS_TEXT, _KYUURA_PRINTED_TEXT),
        # エリカのお付き: 手札を 2 枚、見せずに山札にもどす（使うための条件）→ 山札の「エリカのポケモン」を 0〜2 枚、見せて手札に加えて切る（もどしたカードも選べる）
        "PMCG5-072": TrainerEntry(SearchDeckTrainer(ERIKAS_MAIDS_TEXT, CardFilter("pokemon", name_prefix="エリカの"), 2, optional=True, reveal=True, return_cost=2),
                                  "エリカのお付き", ERIKAS_MAIDS_TEXT, ERIKAS_MAIDS_TEXT, _KYUURA_PRINTED_TEXT),
        # メンテナンス: 手札を 2 枚、見せずに山札にもどす → 切る → 1 枚引く（手札が足りなければ FC1）
        "PMCG1-085": TrainerEntry(ReturnHandToDeckThenDraw(MAINTENANCE_TEXT), "メンテナンス", MAINTENANCE_TEXT, MAINTENANCE_TEXT, _KYUURA_PRINTED_TEXT),
        # ダウジングマシーン: 手札を 2 枚すてる（使うための条件）→ 自分のトラッシュのトレーナーカード（すてたカードを含む）を 0〜1 枚、手札に加える
        "PMCG1-087": TrainerEntry(TakeFromDiscardTrainer(ITEM_FINDER_TEXT, CardFilter("trainer"), 1, TO_HAND, optional=True, discard_cost=2),
                                  "ダウジングマシーン", ITEM_FINDER_TEXT, ITEM_FINDER_TEXT, _KYUURA_PRINTED_TEXT),
        # リサイクル: コインの「おもて」なら、自分のトラッシュの好きなカードを 1 枚、山札の一番上に置く（切らない。トラッシュが空なら ST1）
        "PMCG3-047": TrainerEntry(TakeFromDiscardTrainer(RECYCLE_TEXT, CardFilter("any"), 1, TO_DECK_TOP, coin=True),
                                  "リサイクル", RECYCLE_TEXT, RECYCLE_TEXT, _KYUURA_PRINTED_TEXT),
        # 夜の廃品回収: 自分のトラッシュのたねポケモン・進化カード・基本エネルギーカードを最大 3 枚、見せて山札にもどして切る（0 枚・選べるカードがないときは NG1）
        "PMCG4-057": TrainerEntry(TakeFromDiscardTrainer(NIGHTLY_GARBAGE_RUN_TEXT, CardFilter("pokemon_or_basic_energy"), 3, TO_DECK, zero_undetermined=True),
                                  "夜の廃品回収", NIGHTLY_GARBAGE_RUN_TEXT, NIGHTLY_GARBAGE_RUN_TEXT, _KYUURA_PRINTED_TEXT),
        # v0.54（docs/hand-deck-trainers-v0.54.md。どれも kyuura の印刷の文面）
        # にせオーキドはかせ: 相手の手札をすべて相手の山札にもどさせ、切ってから 7 枚引かせる（相手の手札 0 枚でも切って引かせる。山札が足りなければ引けるだけ）
        "PMCG1-089": TrainerEntry(ReturnHandsToDeckTrainer(IMPOSTER_OAK_TEXT, HANDS_OPPONENT, draw=7),
                                  "にせオーキドはかせ", IMPOSTER_OAK_TEXT, IMPOSTER_OAK_TEXT, _KYUURA_PRINTED_TEXT),
        # にせオーキドの逆襲: 手札 1 枚のトラッシュが使うための条件。そのあと相手の手札をすべて山札にもどさせ、切ってから 4 枚引かせる
        "PMCG4-059": TrainerEntry(ReturnHandsToDeckTrainer(IMPOSTER_OAKS_REVENGE_TEXT, HANDS_OPPONENT, draw=4, discard_cost=1),
                                  "にせオーキドの逆襲", IMPOSTER_OAKS_REVENGE_TEXT, IMPOSTER_OAKS_REVENGE_TEXT, _KYUURA_PRINTED_TEXT),
        # ギャンブラー: 自分の手札をすべて山札にもどして切る → コイン → 「おもて」なら 8 枚、「うら」なら 1 枚引く
        "PMCG3-045": TrainerEntry(ReturnHandsToDeckTrainer(GAMBLER_TEXT, HANDS_SELF, coin_draws=(8, 1)),
                                  "ギャンブラー", GAMBLER_TEXT, GAMBLER_TEXT, _KYUURA_PRINTED_TEXT),
        # ナツメの眼: お互いに自分の手札をすべて山札にもどし、切り、それぞれ自分がもどした枚数を引く（枚数はプレイヤーごと）
        "PMCG6-078": TrainerEntry(ReturnHandsToDeckTrainer(SABRINAS_GAZE_TEXT, HANDS_BOTH, draw_returned=True),
                                  "ナツメの眼", SABRINAS_GAZE_TEXT, SABRINAS_GAZE_TEXT, _KYUURA_PRINTED_TEXT),
        # カツラの奥の手: 手札に「カツラの奥の手」以外のカードがあれば使えない（使うための条件）。5 枚引く
        "PMCG6-081": TrainerEntry(DrawIfOnlyNamedInHand(BLAINES_LAST_RESORT_TEXT, "カツラの奥の手", 5),
                                  "カツラの奥の手", BLAINES_LAST_RESORT_TEXT, BLAINES_LAST_RESORT_TEXT, _KYUURA_PRINTED_TEXT),
        # エリカ: 使ったプレイヤー → 相手プレイヤーの順に、それぞれ 0〜3 枚を選んで引く（決めるのは引くプレイヤー）
        "PMCG5-083": TrainerEntry(EachPlayerMayDraw(ERIKA_TEXT, 3), "エリカ", ERIKA_TEXT, ERIKA_TEXT, _KYUURA_PRINTED_TEXT),
        # スパイ作戦: 相手の手札を見る → のぞむなら手札を好きなだけトラッシュして、同じ数を引く
        "PMCG5-088": TrainerEntry(DiscardFromHandThenDrawTrainer(SECRET_MISSION_TEXT, optional=True, look_opponent_hand=True),
                                  "スパイ作戦", SECRET_MISSION_TEXT, SECRET_MISSION_TEXT, _KYUURA_PRINTED_TEXT),
        # カツラのギャンブル: 手札を好きなだけトラッシュ（0 枚は HC5）→ コイン → 「おもて」ならトラッシュした数 × 2 枚引く
        "PMCG6-076": TrainerEntry(DiscardFromHandThenDrawTrainer(BLAINES_GAMBLE_TEXT, multiplier=2, coin=True),
                                  "カツラのギャンブル", BLAINES_GAMBLE_TEXT, BLAINES_GAMBLE_TEXT, _KYUURA_PRINTED_TEXT),
        # ミニスカート: お互いに手札を見せ合い、手札のトレーナーカードをすべて山札にもどし、お互いに山札を切る
        "PMCG1-095": TrainerEntry(ReturnHandsToDeckTrainer(LASS_TEXT, HANDS_BOTH, returns="trainers", reveal=True),
                                  "ミニスカート", LASS_TEXT, LASS_TEXT, _KYUURA_PRINTED_TEXT),
        # ポケモン図鑑 HANDY505: 自分の山札の上から 0〜5 枚を見て、好きな順番にもどす（手札に加えない・切らない）
        "PMCG1-082": TrainerEntry(ArrangeOwnDeckTopTrainer(POKEDEX_TEXT, 5),
                                  "ポケモン図鑑 HANDY505", POKEDEX_TEXT, POKEDEX_TEXT, _KYUURA_PRINTED_TEXT),
        # v0.55（docs/instant-trainers-v0.55.md。どれも kyuura の印刷の文面）
        # カスミのいかり: 山札の上から 7 枚を見て、2 枚を手札に加え、残りをトラッシュ（切らない。山札が 7 枚より少なければ MW1）
        "PMCG5-075": TrainerEntry(LookTopTakeRestDiscardTrainer(MISTYS_WRATH_TEXT), "カスミのいかり", MISTYS_WRATH_TEXT, MISTYS_WRATH_TEXT, _KYUURA_PRINTED_TEXT),
        # ロケット団のおねーさん: 相手の手札を見て、トレーナーカードがあれば 1 枚を相手の山札にもどさせて切る
        "PMCG4-061": TrainerEntry(OpponentHandTrainerToDeck(ROCKETS_SNEAK_ATTACK_TEXT), "ロケット団のおねーさん", ROCKETS_SNEAK_ATTACK_TEXT, ROCKETS_SNEAK_ATTACK_TEXT,
                                  _KYUURA_PRINTED_TEXT),
        # 礼儀作法: 手札にたねポケモンがないときだけ使える。手札を見せ、山札のたねポケモンを 0〜1 枚、見せて手札に加えて切る
        "PMCG5-082": TrainerEntry(SearchDeckTrainer(GOOD_MANNERS_TEXT, CardFilter("basic_pokemon"), 1, optional=True, reveal=True, no_basic_in_hand=True, reveal_hand=True),
                                  "礼儀作法", GOOD_MANNERS_TEXT, GOOD_MANNERS_TEXT, _KYUURA_PRINTED_TEXT),
        # トラッシュ交換: トラッシュの枚数を数え、すべて山札にもどして切り、数えた枚数を山札の上からトラッシュ
        "PMCG6-077": TrainerEntry(DiscardPileExchange(TRASH_EXCHANGE_TEXT), "トラッシュ交換", TRASH_EXCHANGE_TEXT, TRASH_EXCHANGE_TEXT, _KYUURA_PRINTED_TEXT),
        # エネルギー・リムーブ: 相手の場のポケモンのエネルギーカードを 1 枚はがしてすてる（相手の場にエネルギーカードがなければ EM1）
        "PMCG1-070": TrainerEntry(DiscardAttachedEnergyTrainer(ENERGY_REMOVAL_TEXT, 1), "エネルギー・リムーブ", ENERGY_REMOVAL_TEXT, ENERGY_REMOVAL_TEXT, _KYUURA_PRINTED_TEXT),
        # 超エネルギーリムーブ: 自分のエネルギーカード 1 枚をはがしてすてる（使うための条件）→ 相手のポケモン 1 匹から 2 枚（足りなければ FC1）
        "PMCG1-088": TrainerEntry(DiscardAttachedEnergyTrainer(SUPER_ENERGY_REMOVAL_TEXT, 2, own_cost=1), "超エネルギーリムーブ", SUPER_ENERGY_REMOVAL_TEXT,
                                  SUPER_ENERGY_REMOVAL_TEXT, _KYUURA_PRINTED_TEXT),
        # いいきずぐすり: 自分のポケモン 1 匹のエネルギーカード 1 枚をはがしてすてる → そのポケモンのダメージカウンターを 0〜4 個とりのぞく
        "PMCG1-075": TrainerEntry(DiscardEnergyThenHealTrainer(SUPER_POTION_TEXT), "いいきずぐすり", SUPER_POTION_TEXT, SUPER_POTION_TEXT, _KYUURA_PRINTED_TEXT),
        # なんでもなおし: 特殊状態のポケモンが自分の対戦ポケモンだけなら、その特殊状態をすべて回復（ほかは FH1）
        "PMCG1-080": TrainerEntry(CureSpecialConditionsTrainer(FULL_HEAL_TEXT), "なんでもなおし", FULL_HEAL_TEXT, FULL_HEAL_TEXT, _KYUURA_PRINTED_TEXT),
        # ポケモンセンター: ダメージカウンターがのっている自分のポケモン全員から、ダメージカウンターとエネルギーカードをすべて
        "PMCG1-083": TrainerEntry(HealEachDamagedPokemonTrainer(POKEMON_CENTER_TEXT, HEAL_SELF, None, discard_energy=True), "ポケモンセンター", POKEMON_CENTER_TEXT,
                                  POKEMON_CENTER_TEXT, _KYUURA_PRINTED_TEXT),
        # ねむれ!ねむれ!: コインの「おもて」なら相手の対戦ポケモンをねむり（kyuura の種類 rockets_secret_machine）
        "PMCG4-054": TrainerEntry(CoinStatusOnOpponentActiveTrainer(SLEEP_TRAINER_TEXT), "ねむれ!ねむれ!", SLEEP_TRAINER_TEXT, SLEEP_TRAINER_TEXT, _KYUURA_PRINTED_TEXT),
        # エネルギーサーキュレート: 自分の場の基本エネルギーカードを 0〜すべて手札にもどす
        "PMCG5-067": TrainerEntry(ReturnBasicEnergyToHandTrainer(ENERGY_FLOW_TEXT), "エネルギーサーキュレート", ENERGY_FLOW_TEXT, ENERGY_FLOW_TEXT, _KYUURA_PRINTED_TEXT),
        # エリカの親切: お互いの場のポケモン全員から 2 つずつ（のっている数まで）
        "PMCG5-084": TrainerEntry(HealEachDamagedPokemonTrainer(ERIKAS_KINDNESS_TEXT, HEAL_BOTH, 2), "エリカの親切", ERIKAS_KINDNESS_TEXT, ERIKAS_KINDNESS_TEXT,
                                  _KYUURA_PRINTED_TEXT),
        # タケシ: 自分の場のポケモン全員から 1 つずつ
        "PMCG5-089": TrainerEntry(HealEachDamagedPokemonTrainer(BROCK_TRAINER_TEXT, HEAL_SELF, 1), "タケシ", BROCK_TRAINER_TEXT, BROCK_TRAINER_TEXT, _KYUURA_PRINTED_TEXT),
        # サカキの切り札: 自分の「サカキのポケモン」1 匹のダメージカウンターをすべてとりのぞく → 手札をすべてトラッシュ
        "PMCG6-096": TrainerEntry(HealOwnerPokemonThenDiscardHand(GIOVANNIS_LAST_RESORT_TEXT), "サカキの切り札", GIOVANNIS_LAST_RESORT_TEXT, GIOVANNIS_LAST_RESORT_TEXT,
                                  _KYUURA_PRINTED_TEXT),
        # ナツメ: 自分の「ナツメのポケモン」1 匹のエネルギーカードをすべて、別の「ナツメのポケモン」につけなおす
        "PMCG6-098": TrainerEntry(MoveAllEnergyBetweenOwnerPokemon(SABRINA_TRAINER_TEXT), "ナツメ", SABRINA_TRAINER_TEXT, SABRINA_TRAINER_TEXT, _KYUURA_PRINTED_TEXT),
        # ワープポイント: 相手 → 使ったプレイヤーの順に、持ち主が選んで対戦ポケモンと控えを入れ替える（控えがいなければしない）
        "PMCG6-080": TrainerEntry(SwitchBothActivesTrainer(WARP_POINT_TEXT), "ワープポイント", WARP_POINT_TEXT, WARP_POINT_TEXT, _KYUURA_PRINTED_TEXT),
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
        # ベトベトン（v0.8）p.48・p.323。「かがくへんかガス」: 常にはたらいていて（宣言しない）、「かがくへんかガス」以外のすべての特殊能力を
        # 使えなくし、その力も消す。このカードがねむり・マヒ・こんらんなら消えている（docs/chemical-gas-v0.8.md）
        PowerKey("PMCG3-007", 0): PowerEntry(
            SuppressOtherPowers(exempt_name="かがくへんかガス"),
            "かがくへんかガス",
            "ベトベトンが場にいる限り、場にいるすべてのポケモンの特殊能力は使えず、その力も消える。(ただし、この「かがくへんかガス」という特殊能力は除く)「ねむり・マヒ・こんらん」状態の時、この「かがくへんかガス」の力は消える。",
            "このカードが場にいるかぎり、「かがくへんかガス」以外のすべての「特殊能力」は使えず、その力も消える。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は消える。",
            "P43 p.48",
        ),
        # 化石の秘密のゴースト（v0.9）p.160・p.159（特殊能力解説）・p.323。ワザによってダメージや効果を受けるときに自動的にはたらく
        PowerKey("PMCG3-030", 0): PowerEntry(
            AttackImmunityOnHeads(),
            "とうめい",
            "このカードがワザによるダメージや効果を受ける時、コインを投げ、「おもて」ならこのカードはダメージや効果を受けない。「ねむり・マヒ・こんらん」状態の時、この力は消える。",
            "このカードがワザによってダメージや効果を受けるとき、コインを投げて「おもて」なら、このカードはそのダメージと効果を受けない。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は消える。",
            "P43 p.160",
        ),
        # カイリキー（v0.10）p.192。「はんげき」: 相手のワザによってダメージを受けたときに自動的にはたらき（宣言しない）、ダメージを与えた
        # ポケモンに、弱点・抵抗力に関係なく 10 ダメージ。ダメージを受けるとき、すでにねむり・マヒ・こんらんなら、はたらかない
        # （docs/counterattack-v0.10.md）
        PowerKey("PMCG1-057", 0): PowerEntry(
            CounterattackDamage(amount=10),
            "はんげき",
            "カイリキーがダメージをうけたときには、かならず10ダメージを相手にあたえる。このダメージは、弱点・抵抗力の影響を受けず、常に「10」である。「ねむり・マヒ・こんらん」状態のときにはつかえない。",
            "このカードが相手のワザによってダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）ダメージを与えたポケモンに、「弱点・抵抗力」に関係なく、10ダメージ。ダメージを受けるとき、すでにこのカードが「ねむり・マヒ・こんらん」状態だったなら、この力は、はたらかない。",
            "P43 p.192",
        ),
        # サカキのカイリキー（v0.11）p.193。「こんじょう」: 相手のワザによるダメージで、このカードが「きぜつ」するとき、使える（宣言する。
        # 使うかは持ち主が決める）。コインを投げて「おもて」なら「きぜつ」せず、残り HP が 10。ダメージを受けるとき、すでにねむり・マヒ・
        # こんらんなら使えない。印刷の文面（kyuura の写し）は「…する時、使える。…残りHPは「10」になる。ダメージを受ける時、…」
        # （docs/guts-v0.11.md）
        PowerKey("PMCG6-061", 0): PowerEntry(
            PreventKnockOutOnHeads(remaining_hp=10),
            "こんじょう",
            "この力は、相手のワザによるダメージで、このカードが「きぜつ」する時、使える。コインを投げて「おもて」なら、このカードは「きぜつ」せず、このカードの残りHPは「10」になる。ダメージを受ける時、すでにこのカードが「ねむり・マヒ・こんらん」状態だったなら、この力は使えない。",
            "この力は、相手のワザによるダメージで、このカードが「きぜつ」するとき、使える。コインを投げて「おもて」なら、このカードは「きぜつ」せず、このカードの残りHPが「10」になる。ダメージを受けるとき、すでにこのカードが「ねむり・マヒ・こんらん」状態だったなら、この力は使えない。",
            "P43 p.193",
        ),
        # R団のファイヤー（v0.12）p.82。「ふしちょう」: このカードが「きぜつ」したとき、使える（宣言する。使うかは持ち主が決める）。このカードを
        # トラッシュからとり出し、相手プレイヤーに見せてから、手札に加える。ねむり・マヒ・こんらんのまま「きぜつ」するときは使えない。
        # 印刷の文面（kyuura の写し）は「…した時だけ、使える。このカードをトラッシュからとり出し、手札に加える。…する時、…」
        # （docs/phoenix-v0.12.md）
        PowerKey("PMCG5-020", 0): PowerEntry(
            ReturnToHandOnKnockOut(),
            "ふしちょう",
            "この力は、このカードが「きぜつ」した時だけ、使える。このカードをトラッシュからとり出し、手札に加える。このカードが「ねむり・マヒ・こんらん」状態のまま「きぜつ」する時、この力は使えない。",
            "この力は、このカードが「きぜつ」したとき、使える。このカードをトラッシュからとり出し、相手プレイヤーに見せてから、手札に加える。このカードが「ねむり・マヒ・こんらん」状態のまま「きぜつ」するとき、この力は使えない。",
            "P43 p.82",
        ),
        # R団のカビゴン（v0.17b）p.245。「わるいねぞう」: ねむり状態で相手のワザによるダメージを受けたときに自動的にはたらき（宣言しない）、ダメージを
        # 与えたポケモンに 20（特殊能力によるダメージ）。印刷の文面（kyuura の写し）は「…受けた時、（このカードが「きぜつ」するしないにかかわらず、）
        # …ポケモンに20ダメージ。」（docs/rocket-snorlax-v0.17b.md）
        PowerKey("PMCG6-073", 0): PowerEntry(
            CounterattackDamageWhileAsleep(amount=20),
            "わるいねぞう",
            "このカードが「ねむり」状態で、相手のワザによるダメージを受けた時、（このカードが「きぜつ」するしないにかかわらず、）ダメージを与えたポケモンに20ダメージ。",
            "このカードが「ねむり」状態で、相手のワザによるダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）ダメージを与えたポケモンに、20ダメージ。",
            "P43 p.245",
        ),
        # v0.31（docs/held-cards-v0.31.md）。リザードン（第1弾）の「エナジーバーン」: 処理に使う文面は kyuura の公式エラッタ TXT-CHARIZARD の最新の説明
        # （kyuura が『オフィシャルブック2000』p.66 で確かめた記録。エンジンは誌面を読んでいない）。印刷の文面（「こんらん」のときだけ使えない）は照合だけに使う
        PowerKey("PMCG1-021", 0): PowerEntry(
            ConvertAttachedEnergy(EnergyType.FIRE),
            "エナジーバーン",
            "リザードンは、「炎」以外の自分のエネルギーを「炎」エネルギーとして扱うことができる。「こんらん」状態のときには使えない。",
            "この力は、自分の番の中で何度でも使える。このカードについているすべてのエネルギーは「炎」エネルギーになり、自分の番の終わりにもとにもどる。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない。",
            "TXT-CHARIZARD",
        ),
        # カツラのロコンの「しぜんになおる」（自分の番ごとに 1 回。回数は GameState.power_uses_this_turn。kyuura の印刷の文面）
        PowerKey("PMCG6-026", 0): PowerEntry(
            RemoveOwnCounterOncePerTurn(counters=1),
            "しぜんになおる",
            "この力は、自分の番ごとに1回使える。このカードにのっているダメージカウンターを、1つとりのぞく。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "この力は、自分の番ごとに1回使える。このカードにのっているダメージカウンターを、1つとりのぞく。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # カツラのキュウコンの「ほのおでかいふく」（「炎」エネルギーカードをつけるたびに自動的にはたらく。kyuura の印刷の文面。英語版の「from your hand」は使わない）
        PowerKey("PMCG6-033", 0): PowerEntry(
            HealOnEnergyAttach(EnergyType.FIRE, counters=1),
            "ほのおでかいふく",
            "このカードに「炎」エネルギーカードを1枚つけるたびに、このカードにのっているダメージカウンターを、1つとりのぞく。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "このカードに「炎」エネルギーカードを1枚つけるたびに、このカードにのっているダメージカウンターを、1つとりのぞく。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # v0.42（docs/power-decisions-v0.42.md）。kyuura データの採用
        # ラフレシアの［ヒーリング］（自分の番に 1 回。コイン → 「おもて」なら自分の場のポケモンを選んで 1 つとりのぞく。kyuura の印刷の文面）
        PowerKey("PMCG2-014", 0): PowerEntry(
            HealOwnPokemonOnHeads(counters=1),
            "ヒーリング",
            "このカードの持ち主は、自分の番に1回だけコインを投げて「おもて」なら、自分の場のポケモン1匹からダメージカウンターを1つとりのぞくことができる。「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "このカードの持ち主は、自分の番に1回だけコインを投げて「おもて」なら、自分の場のポケモン1匹からダメージカウンターを1つとりのぞくことができる。「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # ヤドランの［へんなこうどう］（何度でも。自分の場のほかのポケモンのカウンターを 1 つずつこのカードへ。このカードがきぜつしない範囲。kyuura の印刷の文面）
        PowerKey("PMCG3-028", 0): PowerEntry(
            MoveDamageCounterToSelf(),
            "へんなこうどう",
            "このカードが「きぜつ」しない範囲なら、自分の場のポケモンにのっているダメージカウンターを好きなだけ取り、このカードの上にのせてよい。「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "このカードが「きぜつ」しない範囲なら、自分の場のポケモンにのっているダメージカウンターを好きなだけ取り、このカードの上にのせてよい。「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # ゲンガーの［のろい］（自分の番ごとに 1 回。相手の場のカウンターを 1 つ相手の場の別のポケモンへ。きぜつの制限はない。kyuura の印刷の文面）
        PowerKey("PMCG3-031", 0): PowerEntry(
            MoveOpponentDamageCounter(),
            "のろい",
            "自分の番ごとに1回だけ使える。相手の場のポケモンにのっているダメージカウンターを1つ選び、相手の場の別のポケモンの上にのせてよい。「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "自分の番ごとに1回だけ使える。相手の場のポケモンにのっているダメージカウンターを1つ選び、相手の場の別のポケモンの上にのせてよい。「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # v0.43 の特殊能力（宣言して使う 6 つ・場に出たときに 1 度だけ使える 3 つ。kyuura の印刷の文面）
        # わるいクサイハナの［くさいかふん］（自分の番ごとに 1 回。コインの「おもて」で相手の、「うら」で自分の対戦ポケモンをこんらん）
        PowerKey("PMCG4-006", 0): PowerEntry(
            CoinConditionOnEitherActive(CONFUSION),
            "くさいかふん",
            "自分の番ごとに1回使える。コインを投げて「おもて」なら、相手の対戦ポケモンを「こんらん」状態にする。「うら」なら、自分の対戦ポケモンを「こんらん」状態にする。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "自分の番ごとに1回使える。コインを投げて「おもて」なら、相手の対戦ポケモンを「こんらん」状態にする。「うら」なら、自分の対戦ポケモンを「こんらん」状態にする。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # スリープの［えんかくさいみん］（自分の番ごとに 1 回。コインの「おもて」で相手の、「うら」で自分の対戦ポケモンをねむり）
        PowerKey("PMCG4-033", 0): PowerEntry(
            CoinConditionOnEitherActive(SLEEP),
            "えんかくさいみん",
            "自分の番ごとに1回使える。コインを投げて「おもて」なら、相手の対戦ポケモンを「ねむり」状態にする。「うら」なら、自分の対戦ポケモンを「ねむり」状態にする。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "自分の番ごとに1回使える。コインを投げて「おもて」なら、相手の対戦ポケモンを「ねむり」状態にする。「うら」なら、自分の対戦ポケモンを「ねむり」状態にする。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # ヒトカゲの［ほのおをもらう］（自分の番ごとに 1 回。自分の場のほかのポケモンの「炎」エネルギーカードを 1 枚このカードにつけかえる）
        PowerKey("PMCG4-012", 0): PowerEntry(
            TakeEnergyToSelf(EnergyType.FIRE),
            "ほのおをもらう",
            "自分の番ごとに1回使える。自分の場のポケモンについている「炎」エネルギーカードを1枚はがし、このカードにつけてよい。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "自分の番ごとに1回使える。自分の場のポケモンについている「炎」エネルギーカードを1枚はがし、このカードにつけてよい。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # エリカのマダツボミの［ようぶんきゅうしゅう］（自分の番ごとに 1 回。自分の場のほかのポケモンの「草」エネルギーカードを最大 2 枚このカードにつけかえる。0 枚は PW3）
        PowerKey("PMCG5-010", 0): PowerEntry(
            TakeEnergiesToSelf(EnergyType.GRASS, 2),
            "ようぶんきゅうしゅう",
            "この力は、自分の番ごとに1回使える。自分の場のポケモンについている「草」エネルギーカードを最大2枚選び、はがしてこのカードにつける。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "この力は、自分の番ごとに1回使える。自分の場のポケモンについている「草」エネルギーカードを最大2枚選び、はがしてこのカードにつける。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # マチスのレアコイルの［エナジーチャージ］（バトル場にいるときだけ。回数の制限はない。控えの「雷」エネルギーカードを好きなだけこのカードにつけかえる）
        PowerKey("PMCG5-040", 0): PowerEntry(
            ChargeBenchEnergyToSelf(EnergyType.LIGHTNING),
            "エナジーチャージ",
            "この力は、このカードがバトル場にいる時だけ、使える。自分の控えポケモンについている「雷」エネルギーカードを好きなだけはがし、このカードにつける。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "この力は、このカードがバトル場にいる時だけ、使える。自分の控えポケモンについている「雷」エネルギーカードを好きなだけはがし、このカードにつける。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # わるいハクリューの［しんかのひかり］（自分の番ごとに 1 回。山札の進化カードを 1 枚見せて手札に加え、山札を切る。山札に進化カードがなければ PW3）
        PowerKey("PMCG4-052", 0): PowerEntry(
            SearchEvolutionCardToHand(),
            "しんかのひかり",
            "自分の番ごとに1回使える。自分の山札から進化カードを1枚選び出し、相手プレイヤーに見せてから、手札に加える。その後、その山札をよく切る。「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "自分の番ごとに1回使える。自分の山札から進化カードを1枚選び出し、相手プレイヤーに見せてから、手札に加える。その後、その山札をよく切る。「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # わるいゴルバットの［こっそりかみつく］（手札から出したときに 1 度だけ。相手の場のポケモン 1 匹に、特殊能力によるダメージ 10。きぜつさせうる）
        PowerKey("PMCG4-009", 0): PowerEntry(
            DamageOpponentPokemonOnEntry(10),
            "こっそりかみつく",
            "この力は、このカードを手札から出した時、1度だけ使える。相手の場のポケモン1匹を選び、(「弱点・抵抗力」に関係なく)10ダメージ。",
            "この力は、このカードを手札から出した時、1度だけ使える。相手の場のポケモン1匹を選び、(「弱点・抵抗力」に関係なく)10ダメージ。",
            _KYUURA_PRINTED_TEXT,
        ),
        # わるいヤドランの［つりあげる］（手札から場に出したときに 1 度だけ。トラッシュのポケモンのカードを最大 3 枚見せて手札に加える）
        PowerKey("PMCG4-036", 0): PowerEntry(
            RecoverPokemonFromDiscardOnEntry(3),
            "つりあげる",
            "この力は、このカードを手札から場に出した時、1度だけ使える。自分のトラッシュにあるポケモン(または進化)カードを最大3枚選び、相手プレイヤーに見せてから、手札に加える。",
            "この力は、このカードを手札から場に出した時、1度だけ使える。自分のトラッシュにあるポケモン(または進化)カードを最大3枚選び、相手プレイヤーに見せてから、手札に加える。",
            _KYUURA_PRINTED_TEXT,
        ),
        # わるいカイリューの［てしたをよぶ］（場に出たときに 1 度だけ。山札のたねポケモンを最大 2 枚ベンチに出し、山札を切る。0 枚になるときは PW3）
        PowerKey("PMCG4-053", 0): PowerEntry(
            BenchBasicsFromDeckOnEntry(2),
            "てしたをよぶ",
            "この力は、このカードが場に出た時に1度だけ使える。自分の山札からポケモンカード(進化カード以外)を最大2枚選び出し、自分のベンチに出す。その後、その山札をよく切る。",
            "この力は、このカードが場に出た時に1度だけ使える。自分の山札からポケモンカード(進化カード以外)を最大2枚選び出し、自分のベンチに出す。その後、その山札をよく切る。",
            _KYUURA_PRINTED_TEXT,
        ),
        # エリカのラフレシアの［ぼうぎょかふん］（バトル場でワザのダメージを受けたときに自動的にはたらく。特殊状態でもはたらく。kyuura の印刷の文面）
        PowerKey("PMCG5-014", 0): PowerEntry(
            ConfuseDamageSourceOnHeads(),
            "ぼうぎょかふん",
            "このカードがバトル場でワザによるダメージを受けた時、（このカードが「きぜつ」するかしないかにかかわらず）コインを投げ、「おもて」なら、ダメージを与えたポケモンを「こんらん」状態にする。この力は、このカードが「ねむり・マヒ・こんらん」状態でも、必ずはたらく。",
            "このカードがバトル場でワザによるダメージを受けた時、（このカードが「きぜつ」するかしないかにかかわらず）コインを投げ、「おもて」なら、ダメージを与えたポケモンを「こんらん」状態にする。この力は、このカードが「ねむり・マヒ・こんらん」状態でも、必ずはたらく。",
            _KYUURA_PRINTED_TEXT,
        ),
        # カイリューの［かけつける］: 処理に使う文面は kyuura の card_differences の PMCG3-043 の記録（確度: 確実）が引く p.249 の最新の説明（特殊状態の条件はない）。印刷の文面は照合だけに使う
        PowerKey("PMCG3-043", 0): PowerEntry(
            SwitchSelfFromBench(),
            "かけつける",
            "この能力はベンチにいる時に使う。自分の番ごとに1回だけ使える。バトル場にいる自分の対戦ポケモンとこのカードとを交換することができる。「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "この力は、自分の番ごとに1回、このカードがベンチにいるときに使える。バトル場にいる自分の対戦ポケモンと、このカードを入れ替える。",
            f"{_CARD_DIFFERENCES}#PMCG3-043",
        ),
        # エリカのウツボットの［かおりのわな］（自分の番ごとに 1 回。コイン → 「おもて」なら相手の控えを選んで入れ替える。控えがいなければ PW1。kyuura の印刷の文面）
        PowerKey("PMCG5-015", 0): PowerEntry(
            SwitchOpponentOnHeads(),
            "かおりのわな",
            "この力は、自分の番ごとに1回使える。コインを投げて「おもて」なら、相手の控えポケモンから1匹を選び、相手の対戦ポケモンと入れ替える。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "この力は、自分の番ごとに1回使える。コインを投げて「おもて」なら、相手の控えポケモンから1匹を選び、相手の対戦ポケモンと入れ替える。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # わるいユンゲラーの［ぶっしつこうかん］（自分の番ごとに 1 回。手札を 1 枚選んでトラッシュ → 1 枚引く。手札がなければ PW2。kyuura の印刷の文面）
        PowerKey("PMCG4-034", 0): PowerEntry(
            DiscardThenDraw(),
            "ぶっしつこうかん",
            "自分の番ごとに1回使える。手札からカードを1枚選んでトラッシュする。その後、山札からカードを1枚引く。「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "自分の番ごとに1回使える。手札からカードを1枚選んでトラッシュする。その後、山札からカードを1枚引く。「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # v0.44 の特殊能力（kyuura の印刷の文面。docs/search-evolution-once-attacks-v0.44.md）
        # キョウのコクーンの［うか］（自分の番ごとに 1 回。コインの「おもて」で山札の「キョウのスピアー」をこのカードに重ねて進化させ、山札を切る。特殊能力なので番は続く）
        PowerKey("PMCG6-011", 0): PowerEntry(
            CoinEvolveSelfFromDeck("キョウのスピアー"),
            "うか",
            "この力は、自分の番ごとに1回使える。コインを投げて「おもて」なら、自分の山札から「キョウのスピアー」を1枚選び出し、このカードの上にのせて進化させる。その後、その山札をよく切る。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "この力は、自分の番ごとに1回使える。コインを投げて「おもて」なら、自分の山札から「キョウのスピアー」を1枚選び出し、このカードの上にのせて進化させる。その後、その山札をよく切る。このカードが「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # サカキのペルシアンの［ボスをよぶ］（手札から場に出したときに 1 度だけ。山札の「サカキ」を 1 枚手札に加え（見せる指示はない）、山札を切る。山札になければ PW3）
        PowerKey("PMCG6-071", 0): PowerEntry(
            SearchNamedTrainerOnEntry("サカキ"),
            "ボスをよぶ",
            "この力は、このカードを手札から場に出した時、1度だけ使える。自分の山札から「サカキ」を1枚選び出し、手札に加える。その後、その山札をよく切る。",
            "この力は、このカードを手札から場に出した時、1度だけ使える。自分の山札から「サカキ」を1枚選び出し、手札に加える。その後、その山札をよく切る。",
            _KYUURA_PRINTED_TEXT,
        ),
        # メノクラゲの［おくびょう］（自分の番にいつでも。このカードを手札にもどし、カウンターをとりのぞき、ついていたカードをトラッシュ。場に出した番は使えない。kyuura の印刷の文面）
        PowerKey("PMCG3-011", 0): PowerEntry(
            ReturnSelfToHand(),
            "おくびょう",
            "自分の番であれば、いつでもこのカードを手札にもどしてよい。その時、このカードにのっていたダメージカウンターなどを全てとりのぞき、ついていたカードも全てはがしてすてる。このカードを場に出した番には、この力は使えない。また、「ねむり・マヒ・こんらん」状態の時にも、この力は使えない。",
            "自分の番であれば、いつでもこのカードを手札にもどしてよい。その時、このカードにのっていたダメージカウンターなどを全てとりのぞき、ついていたカードも全てはがしてすてる。このカードを場に出した番には、この力は使えない。また、「ねむり・マヒ・こんらん」状態の時にも、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # v0.46 の常にはたらく特殊能力（kyuura の印刷の文面。docs/continuous-powers-v0.46.md）
        # バリヤードの［なぞのかべ］（常にはたらく。受ける 30 以上のダメージは 0。8 段階。ねむり・マヒ・こんらんで使えない）
        PowerKey("PMCG2-027", 0): PowerEntry(
            ZeroLargeDamageReceived(30),
            "なぞのかべ",
            "このカードが受ける30以上のダメージは0になる。(30より小さいダメージはそのまま受ける。)「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            "このカードが受ける30以上のダメージは0になる。(30より小さいダメージはそのまま受ける。)「ねむり・マヒ・こんらん」状態の時、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # エリカのミニリュウの［ふしぎなバリアー］（常にはたらく。たねポケモンから受ける 20 以上のダメージは 10。8 段階。受けるときのねむり・マヒ・こんらんで使えない）
        PowerKey("PMCG5-063", 0): PowerEntry(
            CapDamageFromBasic(threshold=20, amount=10),
            "ふしぎなバリアー",
            "このカードが「たねポケモン」から受ける20以上のダメージは、「10」になる。(ダメージ以外の効果は、そのまま)。ダメージを受ける時、すでにこのカードが「ねむり・マヒ・こんらん」状態だったなら、この力は使えない。",
            "このカードが「たねポケモン」から受ける20以上のダメージは、「10」になる。(ダメージ以外の効果は、そのまま)。ダメージを受ける時、すでにこのカードが「ねむり・マヒ・こんらん」状態だったなら、この力は使えない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # エリカのフシギソウの［くつろぐかおり］（常にはたらく。バトル場にいる限り、お互いの対戦ポケモンのワザのダメージは半分（切り上げ）。ワザが使われた時の特殊状態）
        PowerKey("PMCG6-010", 0): PowerEntry(
            HalveActiveAttackDamage(),
            "くつろぐかおり",
            "このカードがバトル場にいる限り、お互いの対戦ポケモンの、すべてのワザのダメージは、半分(切り上げ)になる。(自分や、控えへのダメージも半分になる)。ワザが使われた時、すでにこのカードが「ねむり・マヒ・こんらん」状態なら、この力ははたらかない。",
            "このカードがバトル場にいる限り、お互いの対戦ポケモンの、すべてのワザのダメージは、半分(切り上げ)になる。(自分や、控えへのダメージも半分になる)。ワザが使われた時、すでにこのカードが「ねむり・マヒ・こんらん」状態なら、この力ははたらかない。",
            _KYUURA_PRINTED_TEXT,
        ),
        # わるいオコリザルの［きょうぼう］（常にはたらく。こんらん状態の時、このカードが与えるダメージ + 30。2 段階）
        PowerKey("PMCG4-041", 0): PowerEntry(
            BonusDamageWhileConfused(30),
            "きょうぼう",
            "このカードが「こんらん」状態の時、このカードがポケモンに与えるダメージは「+30」される。",
            "このカードが「こんらん」状態の時、このカードがポケモンに与えるダメージは「+30」される。",
            _KYUURA_PRINTED_TEXT,
        ),
        # ドードリオの［にげるサポート］（常にはたらく。ベンチにいるとき、自分の対戦ポケモンの「にげる」エネルギーを 1 少なくできる）
        PowerKey("PMCG2-040", 0): PowerEntry(
            ReduceOwnActiveRetreatCost(1),
            "にげるサポート",
            "この力はベンチでしか使えない。自分の対戦ポケモンが「にげる」時、はがしてすてるエネルギーを1つ分少なくできる。",
            "この力はベンチでしか使えない。自分の対戦ポケモンが「にげる」時、はがしてすてるエネルギーを1つ分少なくできる。",
            _KYUURA_PRINTED_TEXT,
        ),
        # わるいベトベトンの［ねんちゃくえき］（常にはたらく。バトル場にいるかぎり、相手の対戦ポケモンの「にげる」エネルギーが 2 多く必要。ねむり・マヒ・こんらんで消える）
        PowerKey("PMCG4-007", 0): PowerEntry(
            IncreaseOpponentActiveRetreatCost(2),
            "ねんちゃくえき",
            "このカードがバトル場にいるかぎり、相手の対戦ポケモンは、「にげる」時トラッシュするエネルギーが2ぶん多く必要になる。このカードが「ねむり・マヒ・こんらん」状態の時、この力は消える。",
            "このカードがバトル場にいるかぎり、相手の対戦ポケモンは、「にげる」時トラッシュするエネルギーが2ぶん多く必要になる。このカードが「ねむり・マヒ・こんらん」状態の時、この力は消える。",
            _KYUURA_PRINTED_TEXT,
        ),
        # わるいラフレシアの［アレルギーかふん］（常にはたらく。場にいる限り、誰もトレーナーカードを使えない。ねむり・マヒ・こんらんで消える）
        PowerKey("PMCG4-010", 0): PowerEntry(
            PreventTrainerUse(),
            "アレルギーかふん",
            "このカードが場にいる限り、誰もトレーナーカードを使うことができない。「ねむり・マヒ・こんらん」状態の時、この力は消える。",
            "このカードが場にいる限り、誰もトレーナーカードを使うことができない。「ねむり・マヒ・こんらん」状態の時、この力は消える。",
            _KYUURA_PRINTED_TEXT,
        ),
        # カビゴンの［めんえき］（常にはたらく。どく・ねむり・マヒ・こんらん状態にならない。ねむり・マヒ・こんらん状態なら使えない）
        PowerKey("PMCG2-047", 0): PowerEntry(
            SpecialConditionImmunity(),
            "めんえき",
            "このカードは、「どく・ねむり・マヒ・こんらん」状態にならない。(なんらかの原因で「ねむり・マヒ・こんらん」状態になっているとき、この力は使えない)",
            "このカードは、「どく・ねむり・マヒ・こんらん」状態にならない。(なんらかの原因で「ねむり・マヒ・こんらん」状態になっているとき、この力は使えない)",
            _KYUURA_PRINTED_TEXT,
        ),
        # v0.47（docs/fossil-hidden-info-v0.47.md）。処理に使う文面は kyuura の印刷の文面
        # オムナイトの［おみとおし］（常にはたらく。場にいる限り、相手の手札を全員に見えるようにする。ねむり・マヒ・こんらんで消える。ゲームの処理は変えない）
        PowerKey("PMCG3-015", 0): PowerEntry(RevealOpponentHand(), "おみとおし", CLAIRVOYANCE_TEXT, CLAIRVOYANCE_TEXT, _KYUURA_PRINTED_TEXT),
        # カブトの［カブトアーマー］（常にはたらく。受けるダメージは 8 段階で半分（切りすて）。ねむり・マヒ・こんらんで使えない。どくのダメージは KA1）
        PowerKey("PMCG3-035", 0): PowerEntry(HalveDamageReceived(), "カブトアーマー", KABUTO_ARMOR_TEXT, KABUTO_ARMOR_TEXT, _KYUURA_PRINTED_TEXT),
        # プテラの［げんしのちから］（常にはたらく。場にいる限り、全てのポケモンは進化できない。進化の入口の共通の確かめ。ねむり・マヒ・こんらんで消える）
        PowerKey("PMCG3-041", 0): PowerEntry(PreventEvolution(), "げんしのちから", PREHISTORIC_POWER_TEXT, PREHISTORIC_POWER_TEXT, _KYUURA_PRINTED_TEXT),
        # マンキーの［スパイ］（宣言して使う。自分の番に 1 回。山札の一番上・サイド・相手の手札のどれか 1 枚を位置で選んで見る）
        PowerKey("PMCG2-028", 0): PowerEntry(PeekCard(), "スパイ", PEEK_TEXT, PEEK_TEXT, _KYUURA_PRINTED_TEXT),
        # コラッタ（ロケット団）の［わるふざけ］（宣言して使う。自分の番ごとに 1 回。サイド 1 枚（位置で選ぶ）と山札の一番上を、見ないで入れかえる）
        PowerKey("PMCG4-045", 0): PowerEntry(SwapPrizeWithDeckTop(), "わるふざけ", TRICKERY_TEXT, TRICKERY_TEXT, _KYUURA_PRINTED_TEXT),
        # v0.48（docs/effective-pokemon-properties-v0.48.md）。処理に使う文面は kyuura の印刷の文面
        # モルフォンの［へんしょく］（宣言して使う。自分の番に 1 回。このカードの色を場にいるポケモンの色に変える。ねむり・マヒ・こんらんで消える。変えた色の期限は VS1）
        PowerKey("PMCG2-015", 0): PowerEntry(ShiftColor(), "へんしょく", SHIFT_TEXT, SHIFT_TEXT, _KYUURA_PRINTED_TEXT),
        # ナツメのゴースの［ガスのからだ］（常にはたらく。最大HPがついている「超」エネルギーカードの数×10 大きくなる。特殊状態でもはたらく。かがくへんかガスでは消える）
        PowerKey("PMCG6-049", 0): PowerEntry(
            MaxHpPerAttachedEnergyCards(EnergyType.PSYCHIC, 10),
            "ガスのからだ",
            GASEOUS_FORM_TEXT.format(type="超", per=10),
            GASEOUS_FORM_TEXT.format(type="超", per=10),
            _KYUURA_PRINTED_TEXT,
        ),
        # v0.49（docs/virtual-attacks-transformation-v0.49.md）。処理に使う文面は kyuura の印刷の文面
        # ナツメのフーディンの［サイコリンク］（常にはたらく。自分の場の「超」ポケモンのワザを、このカードのワザとして持つ。ねむり・マヒ・こんらんで消える）
        PowerKey("PMCG6-053", 0): PowerEntry(
            AttacksOfOwnTypePokemon(EnergyType.PSYCHIC), "サイコリンク", PSYLINK_TEXT.format(type="超"), PSYLINK_TEXT.format(type="超"), _KYUURA_PRINTED_TEXT,
        ),
        # メタモンの［へんしん］（常にはたらく。バトル場にいる限り、相手の対戦ポケモンと同じカードとしてあつかう。エネルギーカードはどの色としても使える。写した特殊能力は
        # TF1、写すカードの姿は TF2）
        PowerKey("PMCG3-042", 0): PowerEntry(TransformIntoDefender(), "へんしん", TRANSFORM_TEXT, TRANSFORM_TEXT, _KYUURA_PRINTED_TEXT),
        # タケシのキュウコンの「ばける」（宣言して使う。自分の番ごとに 1 回。手札の進化カードをのせて、そのポケモンとしてあつかう。2000.02.14 版の基準では、のせたカードの
        # 特殊能力ははたらく（2000年5月の ERR-BROCK-NINETALES は持ち込まない））
        PowerKey("PMCG5-019", 0): PowerEntry(
            Shapeshift("タケシのキュウコン"), "ばける", SHAPESHIFT_TEXT.format(name="タケシのキュウコン"), SHAPESHIFT_TEXT.format(name="タケシのキュウコン"),
            _KYUURA_PRINTED_TEXT,
        ),
    },
)

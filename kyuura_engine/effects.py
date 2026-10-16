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

from .cards import EnergyType
from .coins import CoinSide, flip_coins
from .conditions import CONFUSION, PARALYSIS, POISON, SLEEP, SWITCH, clear_special_conditions
from .damage import SET, DamageModifier, calculate_attack_damage
from .decisions import (
    ATTACH_FROM_DISCARD, ATTACH_TO_BENCH, BENCH_FROM_DECK, DISCARD_ENERGY, DISCARD_FROM_HAND, DISCARD_OPPONENT_ENERGY, FORCED_SWITCH, RECOVER_ENERGY, RECOVER_TRAINER,
    RETRIEVE_ENERGY, RETURN_TO_DECK, SEARCH_DECK, SELECT_ATTACK, SELECT_EVOLUTION_CARD, SELECT_POKEMON, push_trainer_decision,
)
from .errors import IllegalActionError, UnsupportedError
from .evolution import place_evolution_card, skipped_stage1_basic
from .persistent import (
    attack_barrier,
    damage_prevention,
    damage_reduction,
    next_turn_attack_damage,
    reduced_damage_to_source,
    remove_persistent_effects,
    retaliation,
)
from .state import RETALIATION_FIXED, RETALIATION_RECEIVED, Retaliation
from .zones import (
    attach_energy_from_hand, attach_trainer, discard_from_hand, discard_hand, draw_cards, return_discard_to_hand, return_hand_to_deck,
    reveal_deck_to_hand, search_deck_to_hand, shuffle_deck,
)

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
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
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
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
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
    return calculate_attack_damage(base, state.card_def(attacker.card), state.card_def(receiver.card), state.rules, modifiers).final


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
ATTACK_ELEMENTS = (DAMAGE_ELEMENT, FORCED_SWITCH_ELEMENT, POISON, SLEEP, PARALYSIS, CONFUSION, ENERGY_DISCARD_ELEMENT, ATTACK_LOCK_ELEMENT,
                   ENERGY_ATTACH_ELEMENT, REDUCED_DAMAGE_ELEMENT)


def evasion_power(state: GameState, pokemon: PokemonInPlay) -> tuple[PowerKey, AttackImmunityOnHeads] | None:
    """場のポケモン ``pokemon`` の（いちばん上のカードの。p.310）特殊能力のうち、ワザを受けるときに自動的にはたらき
    （``AttackImmunityOnHeads``。ゴーストの「とうめい」）、今はたらいているもの（v0.9）。なければ None。

    はたらいていないのは、このカードがねむり・マヒ・こんらんのとき（T9〜T11。どくは関係しない。T12）と、かがくへんかガスに
    消されているとき（T14。v0.8 の ``continuous.suppressors_of`` をそのまま聞く。抑止の判定を複製しない）。場所（バトル場・
    ベンチ）は見ない（T7）。状態を変えず、乱数を使わない。
    """
    from .continuous import suppressors_of  # continuous.py は effects.py を読み込むので、使うときに読み込む

    definition = state.card_def(pokemon.card)
    for index, power in enumerate(definition.powers):
        effect = state.effects.power_effect(definition.id, power)
        if isinstance(effect, AttackImmunityOnHeads) and effect.is_working(pokemon) and not suppressors_of(state, power):
            return PowerKey(definition.id, index), effect
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
    attack = state.card_def(attacker.card).attacks[use.key.attack_index]
    final = preview_attack_damage(state, use, OPPONENT_ACTIVE, attack.damage)
    if final is None or final <= 0:
        return None
    return evaded_effect_coin_error(target.pokemon_id, final)


def effect_after_no_damage_error(attack: str, result: DamageResult, condition: str) -> UnsupportedError:
    """``UNRESOLVED_EFFECT_AFTER_NO_DAMAGE`` の理由（v0.17b。docs/rocket-snorlax-v0.17b.md の Z23）。説明が「ダメージを与えた後、…」の効果で、
    そのダメージの要素がダメージを与えなかった（``result``: 防いだ・「とうめい」で受けなかった・最終ダメージが 0）。"""
    why = "「ダメージを受けない」状態で無効" if result.prevented else "「とうめい」で受けなかった" if result.evaded else "最終ダメージが 0"
    name = {POISON: "どく", SLEEP: "ねむり", PARALYSIS: "マヒ", CONFUSION: "こんらん"}[condition]
    return UnsupportedError(
        "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE",
        f"ワザ {attack} のダメージの要素が、ポケモン {result.pokemon_id} にダメージを与えなかった（{why}）。説明の「ダメージを与えた後、"
        f"…「{name}」状態にする」が要素の順番か、ダメージを与えたことの条件かは『オフィシャルブック2000』（p.245・p.155・p.309・p.319〜p.321）"
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

    definition = state.card_def(pokemon.card)
    for index, power in enumerate(definition.powers):
        effect = state.effects.power_effect(definition.id, power)
        if isinstance(effect, CounterattackDamage) and effect.is_working(pokemon) and not suppressors_of(state, power):
            return PowerKey(definition.id, index), effect
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
    defender_hp = state.card_def(defender.card).hp
    attacker_hp = state.card_def(attacker.card).hp

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



def retaliation_use(state: GameState, player: int, holder: PokemonInPlay, effect: Retaliation) -> AttackUse:
    """「ほのおのかべ」「こうらがえし」のダメージを計算するための ``AttackUse``（v0.12）: ワザを使ったのは効果を持つポケモン（``holder``。
    持ち主 ``player``）、ワザは効果を与えたワザ（``Retaliation.attack_index``）。そのダメージは効果を持つポケモンのワザによるダメージ
    （p.321「8」・p.89・p.82）なので、発生源（弱点・抵抗力・プラスパワー）はこのポケモン、受けるのは相手の対戦ポケモン。v0.16b から、
    宣言の前の確認（``retaliation_double_knockout_problem``。``preview_attack_damage``）だけが使う（返すダメージを与えるのは解決の基盤の
    ``kernel.attack_damage_to_damage_source``）。"""
    key = AttackKey(state.cards[effect.source_card].card_id, effect.attack_index)
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
    holder_hp = state.card_def(holder.card).hp
    attacker_hp = state.card_def(attacker.card).hp
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
            return retaliation_double_knockout_error(holder.pokemon_id, found, retaliation_final, attacker.pokemon_id)
    return None


def retaliation_double_knockout_error(holder_pid: int, effect: Retaliation, retaliation_final: int, attacker_pid: int) -> UnsupportedError:
    """``UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`` の理由（v0.15b で分けた。``retaliation_final`` は返すダメージの最終ダメージ）。"""
    return UnsupportedError(
        "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT",
        f"このワザのダメージで相手の対戦ポケモン {holder_pid} がきぜつしうるうえ、その「{effect.kind}」（{_retaliation_name(effect)}）の"
        f" {retaliation_final} ダメージでワザを使ったポケモン {attacker_pid} がきぜつしうる。このワザによるきぜつと、前の番のワザの"
        "効果のダメージによるきぜつが「同時に「きぜつ」した」ことになるか（p.324）が『オフィシャルブック2000』（p.82・p.89・p.311・"
        "p.321・p.323〜p.325）から決められないので扱わない（サイド・バトル場に出す順番と勝ち負けが変わる）",
    )


def _retaliation_name(effect: Retaliation) -> str:
    """理由の文に書く効果の名前（v0.13）。"""
    return "ほのおのかべ" if effect.basis == RETALIATION_FIXED else "こうらがえし"


def ko_prevention_power(state: GameState, pokemon: PokemonInPlay) -> tuple[PowerKey, PreventKnockOutOnHeads] | None:
    """場のポケモン ``pokemon`` の（いちばん上のカードの。p.310）特殊能力のうち、相手のワザによるダメージできぜつするときに使える
    もの（``PreventKnockOutOnHeads``。サカキのカイリキーの「こんじょう」。v0.11）。特殊状態・かがくへんかガスは見ない（持っているか
    だけ）。なければ None。状態を変えず、乱数を使わない。"""
    definition = state.card_def(pokemon.card)
    for index, power in enumerate(definition.powers):
        effect = state.effects.power_effect(definition.id, power)
        if isinstance(effect, PreventKnockOutOnHeads):
            return PowerKey(definition.id, index), effect
    return None


def ko_prevention_suppressors(state: GameState, pokemon: PokemonInPlay, key: PowerKey) -> tuple[int, ...]:
    """「こんじょう」（``key``）を消している、はたらいている「かがくへんかガス」のポケモンの番号（v0.8 の ``continuous.suppressors_of``
    をそのまま聞く。抑止の判定を複製しない。G31）。"""
    from .continuous import suppressors_of  # continuous.py は effects.py を読み込むので、使うときに読み込む

    return suppressors_of(state, state.card_def(pokemon.card).powers[key.power_index])


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
    hp = state.card_def(defender.card).hp
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
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
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
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
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
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
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
        return _check_form(attack, "相手の控えポケモンと入れ替えるワザ", damage="none")

    def decision_problems(self, state: GameState, use: AttackUse, decision: PendingDecision) -> list[str]:
        p = state.players[1 - use.player]
        problems = _decision_form(decision, _label(state, use), kind=FORCED_SWITCH, player=use.player, choices=(1, 1),
                                  options=(pokemon.pokemon_id for pokemon in p.bench))
        if p.active is None or p.active.pokemon_id != decision.context_value("target"):
            problems.append(f"入れ替えの対象 {decision.context_value('target')!r} が相手のバトル場のポケモンではない")
        return problems


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
    attacks = () if source is None else state.card_def(source.card).attacks
    problems = []
    if decision.kind != SELECT_ATTACK or decision.player != use.player or (decision.min_choices, decision.max_choices) != (1, 1):
        problems.append(f"相手のワザを選ぶ決定の形 {decision.kind}・{decision.player}・{decision.min_choices}〜{decision.max_choices} が正しくない")
    if source is None or decision.context_value("copy_from") != state.cards[source.card].card_id:
        problems.append(f"相手のワザを選ぶ決定のカード {decision.context_value('copy_from')!r} が、相手のバトル場のポケモンではない")
    if not decision.options or any(not 0 <= index < len(attacks) for index in decision.options):
        problems.append(f"相手のワザを選ぶ決定の選べるもの {decision.options} が、相手のバトル場のポケモンのワザではない")
    unsupported = decision.context_value("unsupported_choices", ())
    if not set(unsupported) <= set(decision.options):
        problems.append(f"対応していないワザ {unsupported} が、選べるもの {decision.options} にない")
    return problems


@dataclass(frozen=True)
class ReduceDamageNextTurn(AttackEffect):
    """次の相手の番でこのカードが受けるダメージが ``amount`` へる（v0.31。ピクシーの「ちいさくなる」。持続する効果 ``DamageReduction``。p.321 の 8 段階）。"""

    amount: int
    implementation_id = "reduce_damage_next_turn"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "受けるダメージを減らすワザ", damage="none")


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
    決められない場合は HC4）。"""

    energy_type: EnergyType
    per_energy: int
    max_extra: int
    implementation_id = "extra_energy_damage_mixed"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "多いエネルギーで追加ダメージのワザ", damage="modified", modifier="+", cost_types=(self.energy_type,))
        if EnergyType.COLORLESS not in attack.cost:
            problems.append("必要なエネルギーに無色がないワザ（ExtraEnergyDamage で登録する）")
        return problems


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
        return _check_form(attack, "コインで相手がワザを使えなくなるワザ", damage="none")


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


@dataclass(frozen=True)
class DamagePlusDefenderCounters(AttackEffect):
    """ダメージの目安の数字 +「相手のポケモンにのっているダメージカウンター」× ``per`` の追加ダメージ（v0.32。ルージュラの「ヨガのポーズ」。ダメージの
    目安「20+」）。数えるのはダメージを受ける相手の対戦ポケモンのカウンター。「相手のポケモン」が相手の場のポケモンすべてを指すかは決められないので、
    相手の控えポケモンにダメージカウンターがのっていて読み方で答えが変わるときだけ止める（CD4。``UNRESOLVED_OPPONENT_POKEMON_COUNTERS``）。"""

    per: int
    implementation_id = "damage_plus_defender_counters"

    def check(self, attack: Attack) -> list[str]:
        return _check_form(attack, "相手のダメージカウンターで追加ダメージのワザ", damage="modified", modifier="+")


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
    """

    bench_damage: int
    implementation_id = "damage_and_own_bench_damage"

    def __post_init__(self) -> None:
        if type(self.bench_damage) is not int or self.bench_damage <= 0 or self.bench_damage % 10:
            raise ValueError(f"控えポケモンへのダメージは 10 の倍数の正の数（{self.bench_damage!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "自分の控えにもダメージを与えるワザ", damage="fixed")
        expected = f"自分の控えポケモン全員にも、「弱点・抵抗力」に関係なく、それぞれ{self.bench_damage}ダメージ。"
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
    """

    implementation_id = "damage_then_self_barrier_on_heads"

    def check(self, attack: Attack) -> list[str]:
        problems = _check_form(attack, "コインで次の相手の番にワザをうけなくなるワザ", damage="fixed")
        if attack.text_ja != "コインを投げて「おもて」なら、このカードは次の相手の番にワザをうけない。":
            problems.append(f"説明 {attack.text_ja!r} が、コインの「おもて」で次の相手の番にワザをうけないワザの説明ではない")
        return problems


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


def attack_damage_modifiers(
    state: GameState, attacker: PokemonInPlay, defender: PokemonInPlay, *, attack: AttackKey | None = None, bench: bool = False
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
    """
    modifiers: list[DamageModifier] = []
    if attack is not None and state.cards[attacker.card].card_id == attack.card_id:
        boost = next_turn_attack_damage(state, attacker, attack.attack_index)
        if boost is not None:
            name = state.card_def(boost.source_card).attacks[boost.attack_index].name_ja
            modifiers.append(DamageModifier(step=2, amount=boost.amount, label=name, source=boost.source_card, operation=SET))
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
    # True: 効果で、たねポケモンの上に 2 進化カードを直接重ねる（1 進化を飛ばす。v0.25 のポケモン育て屋さん）。進化の重なりの不変条件が、
    # たねポケモン + 2 進化の重なりの進化のログ（evolve の trainer_card）のカードを、この印で確かめる（カード id では分けない）
    skips_stage1_evolution = False
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
        if pokemon.evolution_stack or not current.is_basic_pokemon or pokemon.current_form_turn >= state.turn_number:
            continue
        for uid in cards:
            definition = state.card_def(uid)
            basic = skipped_stage1_basic(definition)
            if basic is None:
                status = SKIP_EVOLUTION_UNKNOWN_LINEAGE
            elif basic != current.name_ja:
                continue
            elif not definition.supported:
                status = SKIP_EVOLUTION_UNSUPPORTED_CARD
            elif pokemon.damage >= definition.hp:
                status = SKIP_EVOLUTION_HP
            else:
                status = SKIP_EVOLUTION_OK
            pairs.setdefault(pokemon.pokemon_id, []).append((uid, status))
    return pairs


def _selectable_skip_evolutions(state: GameState, player: int) -> dict[int, list[tuple[int, str]]]:
    """決定で選べる組（進化させられる組と、原典で決められない HP の組）。エンジンが確かめられない組（未対応のカード・系統を確かめられない
    カード）は選べるものに入れない。"""
    selectable = {}
    for pokemon_id, entries in skip_evolution_pairs(state, player).items():
        kept = [(uid, status) for uid, status in entries if status in (SKIP_EVOLUTION_OK, SKIP_EVOLUTION_HP)]
        if kept:
            selectable[pokemon_id] = kept
    return selectable


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
        if state.turn_number <= 2:
            raise IllegalActionError("FIRST_TURN_EVOLUTION", "おたがいのプレイヤーの最初の番には、ポケモンを進化させられない（p.310・p.259）")
        statuses = {status for entries in skip_evolution_pairs(state, use.player).values() for _, status in entries}
        if SKIP_EVOLUTION_OK in statuses:
            return
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
        unresolved = [pid for pid in options if all(status == SKIP_EVOLUTION_HP for _, status in selectable[pid])]
        push_trainer_decision(
            state, use, kind=SELECT_POKEMON, player=use.player, options=options, min_choices=1, max_choices=1,
            unresolved_choices=unresolved, unresolved_code="UNRESOLVED_EVOLUTION_HP", unresolved_reason=_EVOLUTION_HP_REASON,
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
        place_evolution_card(state, use.player, state.find_pokemon(target)[1], card, trainer=use.card)

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        """決定するのは使ったプレイヤー。段階 1 は進化させられる自分の場のたねポケモン（場の並び）から 1 匹、段階 2 はそのポケモンに
        1 進化を飛ばして重ねられる手札の 2 進化カード（手札の並び）から 1 枚。原典で決められない組（HP）は ``unresolved_choices``。"""
        selectable = _selectable_skip_evolutions(state, use.player)
        what = "「ポケモン育て屋さん」"
        if decision.kind == SELECT_POKEMON:
            unresolved = [pid for pid in selectable if all(status == SKIP_EVOLUTION_HP for _, status in selectable[pid])]
            return _select_own_pokemon_problems(decision, use, selectable, what, unresolved)
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
    """

    implementation_id = "switch_opponent_with_bench"

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if not state.players[1 - use.player].bench:
            raise UnsupportedError(
                "UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH",
                "相手に控えポケモンがいない。このときに「突風」を使えるかは、『オフィシャルブック2000』（p.255・p.310）から決められない"
                "ので扱わない（第1弾の印刷の文面の「相手に控えがいない場合は使えない」は、p.255 の最新の説明にない）",
            )

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        bench = state.players[1 - use.player].bench
        push_trainer_decision(
            state, use, kind=SELECT_POKEMON, player=use.player, options=[pokemon.pokemon_id for pokemon in bench]
        )

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        _switch_active_with_bench(state, 1 - use.player, choices[0])

    def decision_problems(self, state: GameState, use: TrainerUse, decision: PendingDecision) -> list[str]:
        """決定するのは使ったプレイヤーで、選べるのは相手のベンチのポケモン（控えポケモン）。"""
        bench = state.players[1 - use.player].bench
        return _select_own_pokemon_problems(
            decision, use, (pokemon.pokemon_id for pokemon in bench), "「突風」", whose="相手"
        )


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
        after_energy_attached(state, use.player, target, use.energy)  # v0.31: つけたときにはたらく特殊能力（「水」エネルギーなので今ははたらかない）


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
        hp = state.card_def(pokemon.card).hp
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
    definition = state.card_def(pokemon.card)
    for index, power in enumerate(definition.powers):
        effect = state.effects.power_effect(definition.id, power)
        if isinstance(effect, ReturnToHandOnKnockOut):
            return PowerKey(definition.id, index), effect
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
        if (use.pokemon_id, use.key.power_index) in state.power_uses_this_turn:
            raise IllegalActionError("POWER_ALREADY_USED", f"ポケモン {use.pokemon_id} の特殊能力は、この番にもう使った（自分の番ごとに1回）")
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
        state.power_uses_this_turn = state.power_uses_this_turn + ((use.pokemon_id, use.key.power_index),)
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
    definition = state.card_def(pokemon.card)
    card = state.card_def(energy)
    for index, power in enumerate(definition.powers):
        effect = state.effects.power_effect(definition.id, power)
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
        state.add_event("power_heal", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, power=str(PowerKey(definition.id, index)),
                        counters=removed, amount=removed * per, damage_before=before, total_damage=pokemon.damage, trigger=energy)


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
    },
)

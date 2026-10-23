"""ログと状態の整合・書き出しの形式の監査（v0.4e。docs/integration-audit-v0.4e.md 8 章・9 章）。テスト・ツールから使う道具。

ファイル名が ``test_`` で始まらないので、``python3 -m unittest`` はこのファイルを読み込まない（テストはしない）。

- ``log_problems(state)``: ``new_game`` から進めた対戦のログ（内部の完全な記録）だけから、場のポケモンのダメージ・ついている
  エネルギー・トラッシュ・サイドの枚数を組み立て直し、状態と同じかを確かめる。番の進行（番の始まりが 1 つずつ交互・番と番の
  あいだに番の終わりとポケモンチェックが 1 回ずつ）・ワザ 1 回あたりの要素の数（同じポケモンへのダメージの要素は 1 回）・
  サイドとカードの重複・持続する効果の付与と解除の対応・進化の番も確かめる。v0.5 から、特殊能力（エナジートランス）の
  エネルギーの移動（``move_energy``。直前に同じポケモンの宣言 ``pokemon_power`` が 1 つ）も組み立て直しに含める。v0.6 から、
  手札（引いた・取ったサイド → 場に出した・つけた・使った）と、特殊能力（あまごい）で手札からつけたエネルギー
  （``power_attach_energy``。直前に同じポケモンの宣言が 1 つ。手札にあった自分のカードを自分の場のポケモンへ）も組み立て直し、
  手札からつける通常の操作（``attach_energy``）が 1 番に 1 回までで、特殊能力でつけたあと（通常の操作をまだしていない番）に
  ないこと（R13 はエンジンが止める）も確かめる。宣言（``pokemon_power``）のすぐあとには、その処理（``move_energy``・
  ``power_attach_energy``・``move_damage_counter``）が 1 つある（v0.5〜v0.7 の特殊能力は決定を出さず、1 回の宣言で 1 回処理する。
  p.311）。v0.7 から、特殊能力（ダメージスワップ）のダメージカウンターの移動（``move_damage_counter``。移動元から 1 個へり、
  移動先に 1 個ふえる。自分の場のポケモンのあいだだけ・移動元と移動先が別・移動元にカウンターがあった・移動先がきぜつしない・
  登録された実装がダメージカウンターを移す特殊能力）と、ワザ（じこさいせい）のエネルギーのトラッシュ（``discard_energy``）・
  ダメージカウンターをすべてとりのぞく処理（``remove_all_damage_counters``）も組み立て直しに含める。v0.8 から、場のポケモンの
  ねむり・マヒ・こんらん（``special_condition``・``special_conditions_removed``・きぜつ）も組み立て直し、特殊能力の宣言
  （``pokemon_power``）のたびに、その時点の場（いちばん上のカード・特殊状態）から、はたらいている「かがくへんかガス」
  （``SuppressOtherPowers``）を求めて、消されている特殊能力・宣言しない特殊能力の宣言がないことを確かめる（最後の状態だけから過去の
  使用を決めない）。v0.9 から、ワザを受けるときに自動的にはたらく特殊能力（ゴーストの「とうめい」。``AttackImmunityOnHeads``）の
  ログ（``evade_check``・``attack_evaded``）を、その時点の場（いちばん上のカード・ねむり・マヒ・こんらん・かがくへんかガス）と比べる:
  はたらいている「とうめい」を持つポケモンがワザのダメージ（0 より大きい）・効果（特殊状態・入れ替え）を受ける前に判定がある・
  判定はワザ 1 回につき 1 匹 1 回（T4）・直前にゴースト側のプレイヤーの ``source: "power"`` のコインがあり結果が同じ（T33）・
  判定したポケモンがはたらいている「とうめい」を持つ（T9〜T14）・ワザの中だけ・「おもて」なら、そのワザのダメージ・効果を受けず
  （``attack_evaded`` が続く。T5）、「うら」なら、その要素をすぐに処理する・``attack_evaded`` のダメージは 0 より大きい（T21）。
  ワザ（エナジーへんかん）でトラッシュから手札に加えたエネルギーカード（``recover_energy``）も組み立て直しに含める（v0.23 からトレーナー
  （エネルギー回収）の ``retrieve_energy`` も。基本エネルギーカード・1〜2 枚・そのトレーナーを使うためにトラッシュしたカードでないこと）。
  v0.25 から、進化（``evolve``）の名前（通常の進化）と、``trainer_card`` のある進化（ポケモン育て屋さん。使っている最中のトレーナーの効果で、
  たねポケモンに系統の合う 2 進化カードを重ねた）を確かめる。
  v0.24 から、トレーナー（ポケモン交換おじさん）の ``return_to_deck``（手札 → 山札）・``reveal_from_deck``（山札 → 手札）も手札の組み立て直しに
  含める（どちらもたねポケモン・進化カード。山札は組み立て直さないので、山札にあったかは持ち主・手札とトラッシュにないことで確かめる）。
  v0.10 から、ダメージを受けたときに自動的にはたらく特殊能力（カイリキーの「はんげき」。``CounterattackDamage``）のログ
  （``counterattack``・``counterattack_skipped``）を、その時点の場と比べる: 相手のワザのダメージ（0 より大きい）を、そのときに
  はたらいている「はんげき」を持つポケモン（いちばん上のカード・ねむり・マヒ・こんらんでない・かがくへんかガスに消されていない）が
  受けたら、そのワザの中に 1 回ある（C2・C8・C19〜C24）・それ以外のダメージ（自分のワザ・どく・こんらん・移動・はんげき）では
  ない（C3〜C6・C14）・与える相手はワザを使ったポケモン・量は登録の数（10）・そのワザのダメージのあと（あとにダメージの要素が
  ない）で、ダメージ以外の効果（特殊状態・入れ替え・回復）・きぜつの前（p.89）・ダメージの組み立て直し・与えなかったのは相手が
  すでに HP 以上のとき（C15）・「はんげき」できぜつしたポケモンへの回復がない（C16）・「はんげき」できぜつしたワザのときに、
  ほかのポケモンのきぜつがない（C18。エンジンが止めるはず）。
  v0.11 から、相手のワザによるダメージで「きぜつ」するときに使える特殊能力（サカキのカイリキーの「こんじょう」。
  ``PreventKnockOutOnHeads``）のログ（``ko_prevention_declined``・``ko_prevention_declared``・``ko_prevented``・
  ``ko_prevention_failed``）を、その時点の場と比べる: 相手のワザのダメージ（0 より大きい）を受けたときにねむり・マヒ・こんらんで
  なく（G25〜G29）、ワザのあと HP 以上で、かがくへんかガスに消されていない（G31）なら、きぜつの前に答えが 1 つある（G2・G10）・
  答えはワザのあと・持ち主・登録がこんじょう・相手のワザのダメージを受けた（G3〜G7）・答えはワザ 1 回につき 1 回まで（G14）・
  宣言のすぐあとに持ち主の ``source: "power"`` のコイン（1 枚）とその結果があり、結果がコインと同じ（G13・G17）・使わない答えの
  あとにコインがない（G11）・「おもて」なら残り HP 10（G18・G20）で、そのワザのあときぜつしない（サイドもない。G33）・「うら」・
  使わないならきぜつする（G19・G34）・ダメージの組み立て直しに ``ko_prevented`` を含める。決定の中身はログにない（v0.2a）ので、
  答えと決定の対応はエンジンの不変条件で確かめる。
  v0.30 から、ワザのエネルギーのトラッシュ（``discard_energy``）の数を、そのワザの登録した実装で確かめる: じこさいせい
  （``DiscardEnergyAndRemoveAllCounters``）はダメージカウンターをすべてとりのぞく処理と同じ数、エネルギーをトラッシュしてダメージを与える
  ワザ（``DiscardEnergyThenDamage``。ひのこ・かえんほうしゃ）は、こんらんで「うら」でなければ 1 回で、そのワザのダメージの要素
  （``damage``・``damage_prevented``・「とうめい」の判定）より前・トラッシュしたのはワザを使ったポケモンについていた登録のタイプの基本
  エネルギーカード（ワザの途中の決定を待っている最後のワザだけは 0 回）。ほかのワザにはエネルギーのトラッシュがない。
  v0.31 から、v0.31 のワザ（docs/held-cards-v0.31.md）のトラッシュは、登録した実装の要素の並び（``resolution.programs.BUILDERS``）で確かめる:
  トラッシュの要素（``DiscardOwnEnergy``・自分に控えがいない／受けなかったときにトラッシュする ``MoveOwnEnergyToBench``）がなければ 0 回、
  決まった枚数の要素だけなら（こんらんの「うら」・ワザの失敗・トラッシュできなかった・効果の対象がいない・決定を待つ最後のワザでなければ）その数、
  トラッシュの要素がダメージの要素より前ならダメージの要素より前・あとならダメージの要素（``damage``・``damage_prevented``・``attack_evaded``）の
  あと、トラッシュしたのはワザを使ったポケモンについていた、要素のタイプ（None ならどのエネルギーカードでも）のエネルギーカード。相手のワザを
  自分のワザとして使ったワザ（``copy_attack``）は、そのあとを使ったワザの登録で確かめる。控えポケモンへのダメージ（``target`` が
  ``opponent_bench``）はポケモンごとに 1 回。新しいイベント（``discard_attached_energy``・``attack_heal``・``power_heal``・``recover_trainer``・
  ``attach_energy_from_discard``・``attack_attach_energy``・``discard_from_deck``・``energy_burn``・``destiny_bond``）を組み立て直しに含め、
  宣言する特殊能力のすぐあとの処理に ``energy_burn``・``power_heal`` を加え、「みちづれ」できぜつしたポケモン（``destiny_bond`` の相手）は HP 未満で
  きぜつしてよい。「とうめい」の判定のあとに続く処理に、相手のエネルギーのトラッシュ・ワザを使えなくする効果・控えへのエネルギーをつける処理を加える。
  v0.32 から、山札からベンチに出したカード（``bench_from_deck``。ワザを使ったプレイヤーの山札（手札・トラッシュにない）の、登録の名前のたねポケモン。
  場のポケモンの番号は次の番号）を場の組み立て直しに含め、``bench_from_deck``・``bench_from_deck_none`` のすぐあとに同じプレイヤーの ``shuffle``
  があること、ワザ 1 回に 1 回までであることを確かめる。``drain_heal`` のとりのぞく数（``drain_counters``）を登録の実装（半分の切り上げ・決まった数・
  与えたぶん）と照らし、実際にとりのぞいた数がのっている数までであることを確かめる。
  ログは記録で、状態の正本ではない（状態とログが食い違えば、どちらかの不具合として報告する）。
- ``serialization_problems(state)``: 形式 1〜10 の書き出しが、表せない状態では ``ValueError``（黙って落とさない）、表せる状態では
  形式 10 の書き出しから後の形式の項目を除いたものと同じになることを確かめる（v0.31 で形式 10 を加えた）。形式 11 はない。
"""

from __future__ import annotations

from collections import Counter

from kyuura_engine import state_to_dict
from kyuura_engine.cards import EnergyType
from kyuura_engine.decisions import DISCARD_ENERGY
from kyuura_engine.effects import ActiveRetreatIncreaseStadium, CoinReturnOwnerPokemonStadium, OwnerRetreatReductionStadium  # v0.57
from kyuura_engine.effects import HealOnAttachEnergy, RainbowEnergy  # v0.58
from kyuura_engine.effects import ConvertSelfToEnergy  # v0.59
from kyuura_engine.effects import DiscardAttackerEnergyOnDamage  # v0.68
from kyuura_engine.effects import EachPlayerRecoverFromDiscard  # v0.83
from kyuura_engine.effects import CoinWashChosenBench, DamageSleepThenHealBothBench, EachPlayerLookTopTakeBasicEnergy, HealChosenBenchByEnergy  # v0.83
from kyuura_engine.effects import HealOwnPokemonWithoutDamage, LookTopTakeOneThenShuffle  # v0.83
from kyuura_engine.effects import BenchBabyOrBasicFromOwnDiscardAttack, DamageThenBubbleJump, ReturnOwnBenchToDeckAttack  # v0.84
from kyuura_engine.effects import EachPlayerEvolutionSong, EachPlayerSearchToolOnEntry, HealActiveThenSwitchOnBenchEntry  # v0.84
from kyuura_engine.effects import (  # v0.85
    AttachFromDeckUpToNamedCount, CoinAttachFromDeckOnEntry, CoinAttachFromDiscardToTypePokemon, CoinChosenSideHealAttack, CoinHealTypePokemonOnEntry,
    CoinMillDeckOnEvolve, DiscardTypeEnergyFromHand, GatherTypeEnergyCardsToSelf,
)
from kyuura_engine.effects import SleepDamageSourceOnHeads, SwitchOpponentChosenByOpponent  # v0.84
from kyuura_engine.effects import (  # v0.86
    CoinPerOpponentPokemonDamageThenHealDealt, CureBothActivesOncePerTurn, DamageOnOpponentHandEnergyAttach, DiscardDeckTopAttachTypeEnergyThenEndTurn, EvolveFromDeckByAttachedEnergyColor,
    EvolveFromDeckOnOtherEvolution, HealEachOwnPokemonOnEntry, HealThenCoinHealOnEvolve, ReturnToDeckOnHeadsAfterDamage, SwitchOpponentOnTypeEnergyAttach,
    TriggeredPower, DamageThenLockOpponentHandTrainersOnHeads, DamageThenProtectOwnBench, ATTACK_HAND_TRAINER_LOCK,
)
from kyuura_engine.state import PowersStopped  # v0.86
from kyuura_engine.state import StatusImmunityWhileActive, ZeroDamageAtLeast  # v0.84
from kyuura_engine.effects import BenchBasicFromOwnDiscardThenCounters  # v0.71
from kyuura_engine.effects import CoinReturnOwnPokemonWithAttachedToHand, DiscardDeckTopThenReturnTypeEnergy, LookTopTakePokemonThenShuffle  # v0.73
from kyuura_engine.effects import DiscardEnergyThenBenchBasicFromDiscard, DiscardFromHandThenRetrieveEnergy, SearchNamedFromDeckOrDiscard  # v0.73
from kyuura_engine.effects import EachPlayerMayBenchBasicFromDeck, LookDeckTopStadium  # v0.80
from kyuura_engine.effects import CoinTakeEvolutionOrBasicFromDiscard, DrawThenReturnHandCardsToDeck, LookTopTakeTrainerThenShuffleLock  # v0.80
from kyuura_engine.effects import ReturnHandDrawThenHandLock, ReturnHandEnergyThenCoinSearchBasicEnergy, SetAsideGuessKindQuiz, ShuffleThenArrangeDeckTop  # v0.80
from kyuura_engine.effects import HAND_LOCK_TRAINERS, HAND_TRAINER_LOCK, CoinsSearchBasicEnergyPerHeads, DevolveOneToHandWithBan  # v0.80
from kyuura_engine.effects import EachPlayerReturnDiscardToDeckThenHandLock, RevealDeckTopTakeSameNamed  # v0.80
from kyuura_engine.effects import GuessOpponentPrizeKind, LookOpponentHandReturnOneThenMayDraw, LookOpponentPrizesMayRedeal  # v0.80
from kyuura_engine.effects import CoinHealOwnActiveStadium  # v0.80
from kyuura_engine.effects import (  # v0.81
    BalloonBerry, BasicRetreatIncreaseStadium, CounterBerry, CounterClaw, ExpAll, FocusBand, NamedMaxHpStadium, RetreatCost, is_pokemon_tool_card,
)
from kyuura_engine.effects import ATTACK_ELEMENTS as _ATTACK_ELEMENTS, PlaceFaceDownOnBench  # v0.67
from kyuura_engine.effects import BeamOnKnockOut, DamageOnOpponentRetreat, ReturnToDeckAtRemainingHp  # v0.61
from kyuura_engine.effects import FailAndReturnOnAttack  # v0.60
from kyuura_engine.effects import (  # v0.75
    AttachDiscardEnergyCardsToSelf, AttachEnergyFromDeckToBench, AttachEnergyFromDeckToSelfExactly, CoinAttachEnergyFromDeckToSelf, RevealNamedPokemonFromDeckAny,
    ChooseBenchThenAttachFromDeck, OptionalDiscardEnergyBonusDamage,
)
from kyuura_engine.effects import CoinBenchOwnerBasicFromDeckStadium, CoinRetrieveBasicEnergyStadium, DiscardToHandSuppressionStadium  # v0.74
from kyuura_engine.effects import AttackLockWhileSourceActiveOnHeads, CoinNextTurnMultiplyElseLockAttack, LockOpponentAttackOnHeads  # v0.76
from kyuura_engine.effects import EXPIRE_TO_HAND, RockPaperScissorsRefreshHand  # v0.66
from kyuura_engine.effects import BlainesQuiz, ChallengeBenchFromDecks, CoinSetAsideOpponentHandElseEndTurn, RevealAllPrizesTrainer  # v0.63
from kyuura_engine.effects import (
    AskOpponentEachTakePrizeElseDraw,
    BenchActiveThenHandBasicToActive,
    CoinReturnOpponentHandPositions,
    CoinsReturnOpponentBenchElseEndTurn,
    LookOpponentHandThenBenchBasics,
    LookPrizeAskSwapElseDraw,
    TrainerTurnEffectTrainer,
    TO_DECK,
    TO_DECK_TOP,
    TO_HAND,
    ArrangeOwnDeckTopTrainer,
    DiscardFromHandThenDrawTrainer,
    DrawIfOnlyNamedInHand,
    EachPlayerMayDraw,
    ReturnHandsToDeckTrainer,
    ReturnHandToDeckThenDraw,
    SearchDeckTrainer,
    TakeFromDiscardTrainer,
    BenchBasicFromEitherDiscard,
    BenchBasicFromOpponentDiscard,
    BenchBasicFromOwnDiscardWithCounters,
    DevolveChosenPokemon,
    DevolveOwnPokemon,
    Shapeshift,
    TransformIntoDefender,
    ATTACK_ELEMENTS,
    ATTACK_CHECK_ELEMENT,
    COLORS,
    MaxHpPerAttachedEnergyCards,
    PlaceCountersOnDamagedOpponentPokemon,
    ShiftColor,
    ATTACK_LOCK_ELEMENT,
    DAMAGE_ELEMENT,
    ENERGY_ATTACH_ELEMENT,
    ENERGY_DISCARD_ELEMENT,
    FORCED_SWITCH_ELEMENT,
    REDUCED_DAMAGE_ELEMENT,
    RETREAT_LOCK_ELEMENT,
    RETURN_IN_PLAY_TO_DECK_ELEMENT,
    COUNTERS_ELEMENT,
    EVOLVE_ELEMENT,
    HEAL_ELEMENT,
    RETURN_IN_PLAY_TO_HAND_ELEMENT,
    DEVOLVE_ELEMENT,
    AttachEnergyFromDeckToSelf,
    BenchBasicsFromDeckOnEntry,
    ChargeBenchEnergyToSelf,
    CoinConditionOnEitherActive,
    DamageOpponentPokemonOnEntry,
    EntryPower,
    RecoverPokemonFromDiscardOnEntry,
    SearchEvolutionCardToHand,
    # v0.47（docs/fossil-hidden-info-v0.47.md）
    ArrangeDeckTopEffect,
    DamageThenLockOpponentTrainersOnHeads,
    HalveDamageReceived,
    LockOpponentTrainersNextTurn,
    LookOpponentHandCardToDeck,
    PeekCard,
    PlayAsPokemon,
    PreventEvolution,
    RevealOpponentHand,
    SwapPrizeWithDeckTop,
    # v0.45（docs/conditional-damage-energy-v0.45.md）
    CoinOpponentDeckTopDiscardTrainerElseHand,
    DamageThenMoveOpponentEnergyToBench,
    PutOwnerBasicFromDeckOntoBenchOnHeads,
    ENERGY_MOVE_ELEMENT,
    WAKE_ELEMENT,
    RETALIATION_COIN_TAILS,
    # v0.44（docs/search-evolution-once-attacks-v0.44.md）
    CoinDrawOrReturnHandToDeck,
    CoinEvolveSelfFromDeck,
    CoinPutOpponentDiscardOnDeckTop,
    DamageThenReturnOpponentToHand,
    DamageThenReturnSelfToHandOnHeads,
    EvolutionPermissionForOwnerPokemon,
    EvolveSelfFromDeck,
    ReturnHandThenRevealBasicEnergy,
    SearchNamedTrainerOnEntry,
    SearchTrainerOnHeads,
    SearchTrainerRequiredOnHeads,
    SpecialPoisonOnHeadsWithoutDamage,
    TakeEnergiesToSelf,
    TakeEnergyToSelf,
    ConfuseDamageSourceOnHeads,
    DiscardThenDraw,
    EvolveFromDeckOnHeads,
    HealChosenOpponentThenDraw,
    HealOwnPokemonOnHeads,
    MoveDamageCounter,
    MoveDamageCounterToSelf,
    MoveOpponentDamageCounter,
    PlaceCountersToRemainingHpOnHeads,
    ReturnBenchedPokemonToDeck,
    ReturnOwnPokemonBasicToHand,
    ReturnOwnPokemonToHandOnHeads,
    ReturnSelfToHand,
    SwitchOpponentOnHeads,
    SwitchSelfFromBench,
    CoinsHealOwnPokemon,
    HealAllPokemonBothSides,
    MoveOwnCountersToOpponent,
    SwapCountersOnHeads,
    DamageAndSpecialPoison,
    DamageThenSpecialPoisonOnHeads,
    AttackImmunityOnHeads,
    ConvertAttachedEnergy,
    HealOnEnergyAttach,
    RemoveOwnCounterOncePerTurn,
    CounterattackDamage,
    DamageAndDrain,
    DamageAndFullDrain, DamageAndOptionalFullDrain, RevealBasicEnergyFromDeck,
    DamageAndRemoveCounters,
    DiscardEnergyAndRemoveAllCounters,
    DiscardEnergyThenDamage,
    PreventKnockOutOnHeads,
    ReturnToHandOnKnockOut,
    SuppressOtherPowers,
    # v0.46（docs/continuous-powers-v0.46.md）
    CONTINUOUS_ACTIVE,
    CONTINUOUS_BENCH,
    AttachEnergyFromHandOnHeads,
    BonusDamageWhileConfused,
    CapDamageFromBasic,
    ContinuousPower,
    HalveActiveAttackDamage,
    IncreaseOpponentActiveRetreatCost,
    PreventTrainerUse,
    ReduceOwnActiveRetreatCost,
    ShuffleHandIntoDeckThenDraw,
    SpecialConditionImmunity,
    ZeroLargeDamageReceived,
    # v0.55
    CoinStatusOnOpponentActiveTrainer, CureSpecialConditionsTrainer, DiscardAttachedEnergyTrainer, DiscardEnergyThenHealTrainer, DiscardPileExchange,
    HealEachDamagedPokemonTrainer, HealOwnerPokemonThenDiscardHand, LookTopTakeRestDiscardTrainer, MoveAllEnergyBetweenOwnerPokemon, OpponentHandTrainerToDeck,
    ReturnBasicEnergyToHandTrainer, SwitchBothActivesTrainer,
)
from kyuura_engine.damage import ADD, HALVE_DOWN, HALVE_UP, MULTIPLY, SET_IF_AT_LEAST, ZERO_IF_AT_LEAST
from kyuura_engine.evolution import skipped_stage1_basic
from kyuura_engine.resolution.programs import (
    BUILDERS, Damage, DiscardOwnEnergy, MoveOneEnergyToBench, MoveOwnEnergyToBench, OptionalDiscardBenchDamage, ReturnOwnEnergyToHand,
    DiscardEachType, OptionalDiscardAll, OptionalDiscardForBonus,
)
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import (
    RETALIATION_FIXED,
    RETALIATION_KINDS,
    RETALIATION_RECEIVED,
    RETALIATION_RECEIVED_SCALED_KIND,
    NEXT_TURN_DAMAGE_KINDS,
    CannotAttack,
    CannotAttackNextOwnTurn,
    CannotAttackWhileSourceActive,
    AttackCoinCheck,
    CannotRetreat,
    CannotUseAttack,
    CannotUseOwnAttack,
    HalvedDamage,
    DoubledDamage,
    MaxHpSet,
    NextTurnAttackDamage,
    Phase,
    ReducedDamageToSource,
    ReducedDamageToSourceNextTurn,
    ResistanceChange,
    TailsDamageGuard,
    WeaknessChange,
)

TERMINAL = (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED)
# v0.48: 期限のない（与えた番からはたらき、ベンチにもどる・場をはなれる・進化で消える）効果の種類。テクスチャー1・テクスチャー2・きょだいか
V048_LASTING_KINDS = (WeaknessChange.kind, ResistanceChange.kind, MaxHpSet.kind)
# v0.60: 「かげぶんしん」（与えた番からはたらき、期限では消えない。ダメージを受けた・ベンチにもどる・進化・場をはなれると消える）
# v0.84: 「きらめきタッチ」の効果（与えた番からはたらき、期限では消えない。バトル場をはなれると消える）
LASTING_KINDS = (*V048_LASTING_KINDS, TailsDamageGuard.kind, StatusImmunityWhileActive.kind)
# v0.76: 「このカード」に与えるダメージを 2 段階で減らす相手に与える効果（なきつく・かみつく は次の自分の番の始め、なきごえ は次の相手の番の終わりに消える）
REDUCED_DAMAGE_KINDS = (ReducedDamageToSource.kind, ReducedDamageToSourceNextTurn.kind)

# v0.10: はたらいた「はんげき」より先にあってはならない、ワザのダメージ以外の効果・きぜつ・番の終わり（p.89）
COUNTER_BARRIERS = (
    "special_condition", "forced_switch", "forced_switch_skipped", "drain_heal", "drain_heal_skipped", "drain_heal_declined", "knock_out", "turn_end", "game_end",
    "halted", "recover_energy", "discard_energy", "remove_all_damage_counters", "persistent_effect_added", "persistent_effect_skipped",
    # v0.31: ダメージ以外の効果（エネルギーのトラッシュ・つける・回復・トレーナーの回収・山札・引く）と、ワザの失敗・効果を受けない状態
    "discard_attached_energy", "attack_heal", "recover_trainer", "attach_energy_from_discard", "attack_attach_energy", "discard_from_deck",
    "draw", "effect_prevented", "effect_skipped", "destiny_bond",
    # v0.32: 山札からベンチに出す（なかまをよぶ・ふえる）
    "bench_from_deck", "bench_from_deck_none",
    # v0.34: ワザの効果で自分のポケモンを入れ替える（テレポート）
    "switch",
    # v0.41: ダメージカウンターをのせる・取り替える・山札からエネルギーをつける
    "place_damage_counters", "swap_damage_counters", "attach_energy_from_deck", "attach_energy_from_deck_none",
    # v0.46: 特殊状態にならない（めんえき）・手札からエネルギーをつける（せいちょう）
    "special_condition_prevented", "attach_energy_from_hand",
    # v0.51: トラッシュからベンチに出す（よみがえらせる）
    "bench_from_discard", "bench_from_discard_none",
    # v0.75: エナジーサポートで「とうめい」の控えにつけなかったカード
    "deck_energy_evaded",
)
# v0.10: ダメージの要素のあとのワザのコインが、ダメージ以外の効果（特殊状態）を決めるワザ（「はんげき」はそのコインより先）。でんげきの
# コインは自分へのダメージ（ダメージの要素）を決めるので含めない
EFFECT_COIN_AFTER_DAMAGE = ("poison_on_heads", "paralyze_on_heads", "confuse_on_heads",
                            # v0.41: ダメージの要素のあとのコインが、ダメージ以外の効果（回復・特殊状態・「にげる」ことができない効果・引く）だけを決めるワザ
                            "damage_then_heal_self", "damage_then_status_by_coin", "damage_then_chosen_status_on_heads",
                            "damage_then_confuse_on_any_heads", "damage_then_sleep_on_heads", "damage_then_retreat_lock_on_heads",
                            "damage_then_draw_on_heads")

# 形式ごとに加わった場のポケモンの項目（serialize.py の説明）
POKEMON_FIELDS_SINCE = {
    "pokemon_id": 2, "trainers": 4, "special_conditions": 5, "retreat_failed_turn": 6, "evolution_stack": 7, "played_turn": 7,
    "evolved_turn": 7, "persistent_effects": 8, "attacks_used_once": 11, "evolution_permission_turn": 11, "type_shift": 13, "disguise": 14,
    "devolved_turn": 15, "history": 20,
}
TOP_FIELDS_SINCE = {
    "format_version": 2, "effects": 2, "next_pokemon_id": 2, "next_decision_id": 2, "decision": 2, "trainer_in_use": 3,
    "energy_attached_by_powers_this_turn": 9, "power_uses_this_turn": 10, "energy_burn": 10, "trainer_locks": 12, "recalls": 14,
    "trainer_effects": 16, "stadium": 17, "stadium_uses_this_turn": 17, "trainer_stack": 18, "energy_roles": 19, "set_aside": 21, "face_up_prizes": 21, "face_down_cards": 22,
}
LATEST_FORMAT = 22



# v0.67: うらのカードをおもてにする理由（``zones.reveal_face_down`` の ``cause``）
SECRET_PLAN_CAUSES = frozenset({"choice", "attack", "power", "evolve", "retreat", "damage", "effect", "trainer", "energy", "heal", "devolve",
                                "damage_counters", "switch", "energy_move", "poison", "sleep", "paralysis", "confusion"}) | frozenset(_ATTACK_ELEMENTS)

def _project(data_latest: dict, version: int) -> dict:
    """最新の形式（9）の書き出しから、形式 ``version`` にない項目を除いたもの。"""
    data = {k: v for k, v in data_latest.items() if TOP_FIELDS_SINCE.get(k, 1) <= version}
    if "format_version" in data:
        data["format_version"] = version

    def pokemon(p):
        return None if p is None else {k: v for k, v in p.items() if POKEMON_FIELDS_SINCE.get(k, 1) <= version}

    data["players"] = [
        {**player, "active": pokemon(player["active"]), "bench": [pokemon(b) for b in player["bench"]]} for player in data_latest["players"]
    ]
    if version < 18 and isinstance(data.get("trainer_in_use"), dict):
        data["trainer_in_use"] = {k: v for k, v in data["trainer_in_use"].items() if k != "via"}  # v0.58: 外側のトレーナーのカードは形式 18 から
    if version < 17 and isinstance(data.get("trainer_in_use"), dict):
        data["trainer_in_use"] = {k: v for k, v in data["trainer_in_use"].items() if k != "user"}  # v0.57: 借りて使っているプレイヤーは形式 17 から
    if version < 16 and "trainer_locks" in data:
        data["trainer_locks"] = [{k: v for k, v in lock.items() if k != "origin"} for lock in data["trainer_locks"]]  # v0.56: 禁止の出どころは形式 16 から
    return data


def required_format(state) -> tuple[int, bool]:
    """状態を表すのに要る最小の形式と、形式 1 で表せない決定があるか。"""
    in_play = [pokemon for p in state.players for pokemon in p.in_play()]
    needed = 1
    if state.trainer_in_use is not None:
        needed = max(needed, 3)
    if any(pokemon.trainers for pokemon in in_play):
        needed = max(needed, 4)
    if any(pokemon.conditions.names() for pokemon in in_play):
        needed = max(needed, 5)
    if any(pokemon.retreat_failed_turn is not None for pokemon in in_play):
        needed = max(needed, 6)
    if any(pokemon.evolution_stack for pokemon in in_play):
        needed = max(needed, 7)
    if any(pokemon.persistent_effects for pokemon in in_play):
        needed = max(needed, 8)
    if state.energy_attached_by_powers_this_turn:
        needed = max(needed, 9)
    if state.power_uses_this_turn or state.energy_burn:
        needed = max(needed, 10)  # v0.31
    if any(pokemon.attacks_used_once or pokemon.evolution_permission_turn is not None for pokemon in in_play):
        needed = max(needed, 11)  # v0.44
    if state.trainer_locks:
        needed = max(needed, 12)  # v0.47
    if any(pokemon.type_shift is not None for pokemon in in_play):
        needed = max(needed, 13)  # v0.48: ［へんしょく］の記録
    if (state.recalls or any(len(use) != 2 for use in state.power_uses_this_turn) or any(pokemon.disguise is not None for pokemon in in_play)
            or any(getattr(e, "attack_card", None) is not None or getattr(e, "target_attack_card", None) is not None
                   for pokemon in in_play for e in pokemon.persistent_effects)):
        needed = max(needed, 14)  # v0.49: 「ばける」でのせたカード・「思い出させる」の記録・ワザを印刷したカードを持つ効果・のせたカードの特殊能力の使用の記録
    disguise_uses = set()
    for event in reversed(state.log):
        if event["kind"] == "turn_start":
            break
        if event["kind"] == "pokemon_power" and event.get("card") is not None:
            disguise_uses.add((event.get("pokemon_id"), event.get("power_index"), event.get("card")))
    if (any(pokemon.devolved_turn is not None for pokemon in in_play)
            or any(len(use) == 3 and use not in disguise_uses for use in state.power_uses_this_turn)):
        needed = max(needed, 15)  # v0.50: 退化した番・進化や退化でいちばん上でなくなったカードの特殊能力の使用の記録
    if state.trainer_effects or any(lock.origin != "attack" for lock in state.trainer_locks):
        needed = max(needed, 16)  # v0.56: 期限のあるトレーナーの効果・トレーナーの効果によるトレーナーの使用の禁止
    if (state.stadium is not None or state.stadium_uses_this_turn
            or (state.trainer_in_use is not None and state.trainer_in_use.user is not None)):
        needed = max(needed, 17)  # v0.57: 場のスタジアム・スタジアムの効果を使った記録・錯乱ジムで借りて使っているトレーナー
    if state.trainer_stack or (state.trainer_in_use is not None and state.trainer_in_use.via is not None):
        needed = max(needed, 18)  # v0.58: 外側のトレーナーの効果で相手のトラッシュから使っているトレーナー（サイキックコントロール）
    if state.energy_roles:
        needed = max(needed, 19)  # v0.59: エネルギーとしてついているカード（マルマインの［エネエネ］）
    if any(pokemon.history for pokemon in in_play):
        needed = max(needed, 20)  # v0.62: 場のポケモンのワザの履歴
    if state.set_aside or state.face_up_prizes:
        needed = max(needed, 21)  # v0.63: 一時的に置いておくカード・おもてのサイド
    if state.face_down_cards:
        needed = max(needed, 22)  # v0.67: うらにしてベンチに出したカード（マチスの秘策）
    d = state.decision
    not_v0_1 = d is not None and (
        d.context_value("then") is not None or d.resume in ("attack", "knock_out", "post_knockout", "power")  # v0.42: 特殊能力の途中の決定
        or d.context_value("post_knockout") is not None
    )
    return needed, not_v0_1


def serialization_problems(state) -> list[str]:
    problems = []
    needed, not_v0_1 = required_format(state)
    if max(FORMAT_VERSIONS) != LATEST_FORMAT:
        problems.append(f"形式の一覧 {FORMAT_VERSIONS} の最後が、監査の知っている形式 {LATEST_FORMAT} ではない（監査を更新する）")
    data_latest = state_to_dict(state, format_version=LATEST_FORMAT)
    for version in FORMAT_VERSIONS:
        expected = version >= needed and not (version == 1 and not_v0_1)
        try:
            data = state_to_dict(state, format_version=version)
        except ValueError:
            if expected:
                problems.append(f"形式 {version} で書き出せるはずの状態が ValueError")
            continue
        if not expected:
            problems.append(f"形式 {version} で表せない状態（要る形式 {needed}）を書き出した（黙って落とした）")
        elif data != _project(data_latest, version):
            problems.append(f"形式 {version} の書き出しが、形式 {LATEST_FORMAT} から後の項目を除いたものと違う")
    try:
        state_to_dict(state, format_version=LATEST_FORMAT + 1)
        problems.append(f"形式 {LATEST_FORMAT + 1} を書き出せた（v0.67 では形式 {LATEST_FORMAT + 1} を加えない）")
    except ValueError:
        pass
    return problems


def _without_stadium_steps(events):
    """v0.57: 1 回ぶんのトレーナーの並び（play_trainer から discard_trainer まで）から、スタジアムの処理（錯乱ジムのコイン・chaos_check・chaos_answered・
    chaos_not_borrowable・リムーブ禁止ジムの追加の条件の discard_from_hand）を除く。錯乱ジムで相手が借りて使ったら、play_trainer の写しのプレイヤーを借りた
    プレイヤーにする。使わなかったカード（借りなかった・借りられなかった）は (None, None)。スタジアムの処理がなければ (0, None) で、呼ぶ側は今までどおり確かめる。"""
    chaos = [e for e in events if e["kind"] in ("chaos_check", "chaos_answered", "chaos_not_borrowable")]
    cost = [e for e in events if e["kind"] == "discard_from_hand" and "stadium_card" in e]
    if not chaos and not cost:
        return 0, None
    if any(e["kind"] == "chaos_not_borrowable" for e in chaos) or any(e["kind"] == "chaos_answered" and not e["accepted"] for e in chaos):
        return None, None
    borrower = next((e["player"] for e in chaos if e["kind"] == "chaos_answered"), None)
    stadium_coin = {e.get("stadium_card") for e in chaos if e["kind"] == "chaos_check"}
    kept = []
    for e in events:
        if e["kind"] in ("chaos_check", "chaos_answered") or (e["kind"] == "discard_from_hand" and "stadium_card" in e) \
                or (e["kind"] == "coin_flip" and e.get("source") == "stadium" and e.get("card") in stadium_coin):
            continue
        if e["kind"] == "play_trainer" and borrower is not None:
            e = {**e, "player": borrower}
        kept.append(e)
    return None, kept


def _trainer_effect_of(state, card):
    """v0.53: 使っている最中のトレーナー（カードの uid）の実装（なければ None）。"""
    entry = state.effects.trainer_entry(state.cards[card].card_id) if card in state.cards else None
    return None if entry is None else entry.effect


def search_retrieval_problems(state, events: list[dict]) -> list[str]:
    """v0.53: 山札・トラッシュからカードを選ぶトレーナー（``SearchDeckTrainer``・``TakeFromDiscardTrainer``・``ReturnHandToDeckThenDraw``）1 回ぶんのイベント
    （``play_trainer`` から ``discard_trainer`` まで）の並びが、登録の実装（使うための条件 → コイン → 選んだカード → 切る・引く）と合うか。カードの種類・枚数・
    見せるか（``reveal_from_deck``・``search_deck``）・出どころ（``trainer_card``）を確かめる。ゾーンの組み立て直しは ``log_problems`` の本体が行う。"""
    play = events[0]
    card, player = play["card"], play["player"]
    effect = _trainer_effect_of(state, card)
    if not isinstance(effect, (SearchDeckTrainer, TakeFromDiscardTrainer, ReturnHandToDeckThenDraw)):
        return []
    body = list(events[1:-1])
    label = f"{play['turn']} 番の {state.cards[card].card_id}（カード {card}）"
    problems: list[str] = []

    def mine(e: dict) -> bool:
        return e.get("player") == player and e.get("trainer_card", card) == card

    def take(kind: str) -> dict | None:
        if body and body[0]["kind"] == kind and mine(body[0]):
            return body.pop(0)
        problems.append(f"{label} のイベントの並びに {kind} がない（{[e['kind'] for e in body[:3]]}）")
        body.clear()
        return None

    if isinstance(effect, ReturnHandToDeckThenDraw):
        returned = take("hand_to_deck")
        if returned is not None and (len(returned["cards"]) != effect.count or returned.get("trainer_card") != card):
            problems.append(f"{label} で山札にもどしたカード {returned['cards']} が {effect.count} 枚ではない")
        take("shuffle")
        drawn = take("draw")
        if drawn is not None and len(drawn["cards"]) != effect.draw:
            problems.append(f"{label} で引いたカード {drawn['cards']} が {effect.draw} 枚ではない（もどしたあとの山札は足りる）")
    else:
        if getattr(effect, "reveal_hand", False):
            shown = take("reveal_hand")  # v0.55: 礼儀作法（山札をさがす前に手札を見せる。見せた手札にたねポケモンはない）
            if shown is not None and any(state.printed_def(uid).is_basic_pokemon for uid in shown["cards"]):
                problems.append(f"{label} で見せた手札 {shown['cards']} にたねポケモンがある（使うための条件を満たしていない）")
        if effect.discard_cost:
            paid = take("discard_from_hand")
            if paid is not None and len(paid["cards"]) != effect.discard_cost:
                problems.append(f"{label} の使うための条件でトラッシュしたカード {paid['cards']} が {effect.discard_cost} 枚ではない")
        if isinstance(effect, SearchDeckTrainer) and effect.return_cost:
            paid = take("hand_to_deck")
            if paid is not None and len(paid["cards"]) != effect.return_cost:
                problems.append(f"{label} の使うための条件で山札にもどしたカード {paid['cards']} が {effect.return_cost} 枚ではない")
        if effect.coin:
            coin = take("coin_flip")
            if coin is not None and (coin["source"] != "trainer" or coin["card"] != card or coin["count"] != 1):
                problems.append(f"{label} のコインが、このトレーナーのコイン（source trainer）ではない")
            if coin is not None and coin["result"] == "tails":
                if isinstance(effect, SearchDeckTrainer) and effect.tails_self_lock:
                    # v0.56: ロケット団の実験（「うら」なら、次の自分の番が終わるまで、自分はトレーナーカードを使えない。期限は使った番 + 2）
                    lock = take("trainer_lock_added")
                    if lock is None or lock.get("origin") != "trainer" or lock["player"] != player or lock.get("trainer_card") != card \
                            or lock["expires_turn"] != play["turn"] + 2:
                        problems.append(f"{label} のコインが「うら」なのに、自分のトレーナーの使用の禁止（使った番 + 2 まで）がない・違う")
                if body:
                    problems.append(f"{label} のコインが「うら」なのに、そのあとに {[e['kind'] for e in body]} がある（何もしない）")
                return problems
        zone = "deck" if isinstance(effect, SearchDeckTrainer) else "discard"
        if body and body[0]["kind"] == "trainer_take_none":
            none = body.pop(0)
            if none["zone"] != zone or not effect.optional:
                problems.append(f"{label} で選ばずに終わった（{none['zone']}）が、選ばなくてよいトレーナーの{zone}ではない")
            chosen = []
        elif isinstance(effect, SearchDeckTrainer):
            moved = "reveal_from_deck" if effect.reveal else "search_deck"
            chosen = []
            while body and body[0]["kind"] in ("reveal_from_deck", "search_deck") and body[0]["player"] == player:
                e = body.pop(0)
                if e["kind"] != moved:
                    problems.append(f"{label} で山札から手札に加えたログが {e['kind']}（{moved} のはず。見せる指示{'がある' if effect.reveal else 'がない'}）")
                chosen.append(e["card"])
        elif effect.destination == TO_HAND:
            chosen = []
            while body and body[0]["kind"] == "retrieve_trainer" and mine(body[0]):
                chosen.append(body.pop(0)["card"])
        elif effect.destination == TO_DECK_TOP:
            put = take("put_discard_on_deck_top")
            chosen = [] if put is None else [put["card"]]
            if put is not None and put["chooser"] != player:
                problems.append(f"{label} で山札の上にのせたカードを選んだのが {put['chooser']}")
        else:
            back = take("discard_to_deck")
            chosen = [] if back is None else list(back["cards"])
        if not 0 <= len(chosen) <= effect.count or (not effect.optional and not getattr(effect, "zero_undetermined", False) and len(chosen) != effect.count) \
                or (getattr(effect, "zero_undetermined", False) and not chosen):
            problems.append(f"{label} で選んだカード {chosen} の枚数が、登録（最大 {effect.count} 枚・選ばなくてよい {effect.optional}）と合わない")
        for uid in chosen:
            if not effect.target.matches(state.printed_def(uid)) or state.cards[uid].owner != player:
                problems.append(f"{label} で選んだカード {uid} が、プレイヤー {player} の登録の種類のカードではない")
        if zone == "deck" or effect.destination == TO_DECK:
            take("shuffle")
    if body:
        problems.append(f"{label} の最後に、処理にないイベント {[e['kind'] for e in body]} がある")
    return problems


def hand_deck_problems(state, events: list[dict]) -> list[str]:
    """v0.54: 手札の入れ替え・ドロー・情報の確認のトレーナー（``ReturnHandsToDeckTrainer``・``DrawIfOnlyNamedInHand``・``EachPlayerMayDraw``・
    ``DiscardFromHandThenDrawTrainer``・``ArrangeOwnDeckTopTrainer``）1 回ぶんのイベント（``play_trainer`` から ``discard_trainer`` まで）の並びが、登録の実装
    （使うための条件 → 見せる・見る → もどす → 切る → コイン → 引く。プレイヤーの順は使ったプレイヤー → 相手）と合うか。引いた枚数（山札が足りなければ引けるだけ）・
    もどしたカードの種類・見せるか・出どころ（``trainer_card``）を確かめる。ゾーンの組み立て直しは ``log_problems`` の本体が行う。"""
    play = events[0]
    card, user = play["card"], play["player"]
    effect = _trainer_effect_of(state, card)
    if not isinstance(effect, (ReturnHandsToDeckTrainer, DrawIfOnlyNamedInHand, EachPlayerMayDraw, DiscardFromHandThenDrawTrainer, ArrangeOwnDeckTopTrainer)):
        return []
    body = list(events[1:-1])
    label = f"{play['turn']} 番の {state.cards[card].card_id}（カード {card}）"
    problems: list[str] = []
    order = {"self": (user,), "opponent": (1 - user,), "both": (user, 1 - user)}

    def take(kind: str, player: int) -> dict | None:
        if body and body[0]["kind"] == kind and body[0].get("player") == player and body[0].get("trainer_card", card) == card:
            return body.pop(0)
        problems.append(f"{label} のイベントの並びに プレイヤー {player} の {kind} がない（{[e['kind'] for e in body[:3]]}）")
        body.clear()
        return None

    def drew(player: int, count: int) -> None:
        e = take("draw", player)
        if e is not None and len(e["cards"]) > count:
            problems.append(f"{label} でプレイヤー {player} が引いたカード {e['cards']} が {count} 枚より多い")

    if isinstance(effect, ReturnHandsToDeckTrainer):
        players = order[effect.who]
        if effect.discard_cost:
            paid = take("discard_from_hand", user)
            if paid is not None and len(paid["cards"]) != effect.discard_cost:
                problems.append(f"{label} の使うための条件でトラッシュしたカード {paid['cards']} が {effect.discard_cost} 枚ではない")
        shown = {}
        if effect.reveal:
            for player in players:
                e = take("reveal_hand", player)
                shown[player] = () if e is None else tuple(e["cards"])
        returned = {player: 0 for player in players}
        moved = "revealed_hand_to_deck" if effect.reveal else "hand_to_deck"
        while body and body[0]["kind"] == moved:
            e = body.pop(0)
            if e["player"] not in returned or e.get("trainer_card") != card or returned[e["player"]]:
                problems.append(f"{label} で手札を山札にもどしたプレイヤー {e['player']} が、処理のプレイヤー {players} の順ではない")
                continue
            returned[e["player"]] = len(e["cards"])
            if effect.returns == "trainers" and (tuple(uid for uid in shown.get(e["player"], ()) if state.printed_def(uid).category == "trainer") != tuple(e["cards"])):
                problems.append(f"{label} でもどしたカード {e['cards']} が、見せた手札のトレーナーカードのすべてではない")
        for player in players:
            take("shuffle", player)
        if effect.returns == "all":
            count = None
            if effect.coin_draws is not None:
                coin = take("coin_flip", user)
                if coin is not None:
                    if coin["source"] != "trainer" or coin["card"] != card or coin["count"] != 1:
                        problems.append(f"{label} のコインが、このトレーナーのコイン（source trainer）ではない")
                    count = effect.coin_draws[0] if coin["result"] == "heads" else effect.coin_draws[1]
            for player in players:
                drew(player, effect.draw if effect.draw is not None else returned[player] if effect.draw_returned else (count or 0))
    elif isinstance(effect, DrawIfOnlyNamedInHand):
        drew(user, effect.count)
    elif isinstance(effect, EachPlayerMayDraw):
        for player in (user, 1 - user):
            if body and body[0]["kind"] == "trainer_draw_declined" and body[0]["player"] == player:
                body.pop(0)
            else:
                drew(player, effect.max_count)
    elif isinstance(effect, DiscardFromHandThenDrawTrainer):
        if effect.look_opponent_hand:
            seen = take("look_at_hand", user)
            if seen is not None and seen["owner"] != 1 - user:
                problems.append(f"{label} で見た手札の持ち主 {seen['owner']} が相手ではない")
        if body and body[0]["kind"] == "trainer_discard_declined":
            if not effect.optional and body[0]["reason"] == "declined":
                problems.append(f"{label} で 0 枚のトラッシュを受け付けた（HC5 で止めるはず）")
            body.pop(0)
        else:
            paid = take("discard_from_hand", user)
            if paid is not None:
                heads = True
                if effect.coin:
                    coin = take("coin_flip", user)
                    heads = coin is not None and coin["result"] == "heads" and coin["source"] == "trainer" and coin["card"] == card
                if heads:
                    drew(user, len(paid["cards"]) * effect.multiplier)
    else:
        if body and body[0]["kind"] in ("look_at_deck_top_none", "look_at_deck_top_declined"):
            body.pop(0)
        else:
            looked = take("look_at_deck_top", user)
            arranged = take("arrange_deck_top", user)
            if looked is not None and arranged is not None and (not 1 <= looked["count"] <= effect.max_cards or looked["owner"] != user
                                                                or sorted(arranged["cards"]) != sorted(looked["cards"])):
                problems.append(f"{label} で見た・もどしたカード {looked['cards']}・{arranged['cards']} が、自分の山札の上の {effect.max_cards} 枚までの並べかえではない")
    if body:
        problems.append(f"{label} の最後に、処理にないイベント {[e['kind'] for e in body]} がある")
    return problems


def instant_trainer_problems(state, events: list[dict]) -> list[str]:
    """v0.55: すぐに使い終わるトレーナー（docs/instant-trainers-v0.55.md）1 回ぶんのイベント（``play_trainer`` から ``discard_trainer`` まで）の並びが、登録の実装
    （見る → 手札・トラッシュ／もどす → 切る／使うための条件 → 相手の側／とりのぞく → すてる／相手 → 使ったプレイヤーの入れ替え）と合うか。動かしたカードの数・側・
    出どころ（``trainer_card``）を確かめる。ゾーンの組み立て直しは ``log_problems`` の本体が行う（礼儀作法は ``search_retrieval_problems``）。"""
    play = events[0]
    card, user = play["card"], play["player"]
    effect = _trainer_effect_of(state, card)
    kinds = (LookTopTakeRestDiscardTrainer, OpponentHandTrainerToDeck, DiscardPileExchange, DiscardAttachedEnergyTrainer, DiscardEnergyThenHealTrainer,
             CureSpecialConditionsTrainer, CoinStatusOnOpponentActiveTrainer, ReturnBasicEnergyToHandTrainer, HealEachDamagedPokemonTrainer,
             HealOwnerPokemonThenDiscardHand, MoveAllEnergyBetweenOwnerPokemon, SwitchBothActivesTrainer)
    if not isinstance(effect, kinds):
        return []
    body = list(events[1:-1])
    label = f"{play['turn']} 番の {state.cards[card].card_id}（カード {card}）"
    problems: list[str] = []
    opponent = 1 - user

    def take(kind: str, player: int | None = None) -> dict | None:
        if body and body[0]["kind"] == kind and (player is None or body[0].get("player") == player) and body[0].get("trainer_card", card) == card:
            return body.pop(0)
        problems.append(f"{label} のイベントの並びに プレイヤー {player} の {kind} がない（{[e['kind'] for e in body[:3]]}）")
        body.clear()
        return None

    def skip(*names: str) -> None:
        while body and body[0]["kind"] in names:
            body.pop(0)

    if isinstance(effect, LookTopTakeRestDiscardTrainer):
        looked, taken, rest = take("look_at_deck_top", user), take("looked_to_hand", user), take("looked_to_discard", user)
        if None not in (looked, taken, rest) and (len(taken["cards"]) != effect.take or sorted(taken["cards"] + rest["cards"]) != sorted(looked["cards"])):
            problems.append(f"{label} で手札に加えたカード {taken['cards']}・トラッシュしたカード {rest['cards']} が、見た {effect.look} 枚を {effect.take} 枚と残りに分けたものではない")
    elif isinstance(effect, OpponentHandTrainerToDeck):
        seen = take("look_at_hand", user)
        trainers = [] if seen is None else [uid for uid in seen["cards"] if state.printed_def(uid).category == "trainer"]
        if trainers:
            moved = take("opponent_hand_to_deck", opponent)
            if moved is not None and moved["card"] not in trainers:
                problems.append(f"{label} で相手の山札にもどさせたカード {moved['card']} が、見た手札のトレーナーカードではない")
            take("shuffle", opponent)
    elif isinstance(effect, DiscardPileExchange):
        back, _, top = take("discard_pile_to_deck", user), take("shuffle", user), take("deck_top_to_discard", user)
        if back is not None and top is not None and len(back["cards"]) != len(top["cards"]):
            problems.append(f"{label} で山札の上からトラッシュした枚数 {len(top['cards'])} が、数えたトラッシュの枚数 {len(back['cards'])} と違う")
    elif isinstance(effect, DiscardAttachedEnergyTrainer):
        if effect.own_cost:
            paid = take("trainer_discard_energy", user)
            if paid is not None and len(paid["cards"]) != effect.own_cost:
                problems.append(f"{label} の使うための条件ではがしてすてたカード {paid['cards']} が {effect.own_cost} 枚ではない")
        removed = take("trainer_discard_energy", opponent)
        if removed is not None and (len(removed["cards"]) != effect.opponent_cards or removed["user"] != user):
            problems.append(f"{label} で相手のポケモン {removed['pokemon_id']} からはがしてすてたカード {removed['cards']} が {effect.opponent_cards} 枚ではない（1 匹から）")
    elif isinstance(effect, DiscardEnergyThenHealTrainer):
        paid = take("trainer_discard_energy", user)
        healed = take("remove_damage_counters", user)
        if paid is not None and healed is not None and (len(paid["cards"]) != 1 or healed["pokemon_id"] != paid["pokemon_id"]
                                                        or not 0 <= healed["counters"] <= effect.max_counters):
            problems.append(f"{label} で、はがしたポケモン {paid['pokemon_id']} とダメージカウンターをとりのぞいたポケモン {healed['pokemon_id']}・数 {healed['counters']} が合わない")
    elif isinstance(effect, CureSpecialConditionsTrainer):
        cured = take("special_conditions_removed", user)
        if cured is not None and cured["reason"] != "cured":
            problems.append(f"{label} で特殊状態を消した理由が {cured['reason']}（cured のはず）")
    elif isinstance(effect, CoinStatusOnOpponentActiveTrainer):
        coin = take("coin_flip", user)
        if coin is not None and (coin["source"] != "trainer" or coin["card"] != card or coin["count"] != 1):
            problems.append(f"{label} のコインが、このトレーナーのコイン（source trainer）ではない")
        if coin is not None and coin["result"] == "heads":
            results = [e for e in body if e["kind"] in ("special_condition", "special_condition_prevented")]
            if len(results) != 1 or results[0]["player"] != opponent or results[0]["condition"] != effect.condition or results[0].get("effect") != state.cards[card].card_id:
                problems.append(f"{label} の「おもて」のあとに、相手の対戦ポケモンを {effect.condition} にする処理が 1 回ない")
            skip("special_conditions_removed", "special_condition", "special_condition_prevented", "disguise_removed")
    elif isinstance(effect, ReturnBasicEnergyToHandTrainer):
        while body and body[0]["kind"] == "trainer_return_energy":
            if body.pop(0)["player"] != user:
                problems.append(f"{label} で相手のエネルギーカードを手札にもどした")
    elif isinstance(effect, HealEachDamagedPokemonTrainer):
        order = (user,) if effect.who == "self" else (user, opponent)
        position = 0
        while body and body[0]["kind"] == "remove_damage_counters":
            e = body.pop(0)
            while position < len(order) and order[position] != e["player"]:
                position += 1
            per = state.rules.damage_per_counter
            if position == len(order) or e["counters"] <= 0 or (effect.counters is not None and e["counters"] > effect.counters) \
                    or (effect.counters is None and e["total_damage"] != 0) or (effect.counters is not None and e["counters"] < effect.counters and e["total_damage"] != 0):
                problems.append(f"{label} でポケモン {e['pokemon_id']} からとりのぞいた数 {e['counters']}（残り {e['total_damage'] // per} 個）が登録と合わない・プレイヤーの順ではない")
            if effect.discard_energy and body and body[0]["kind"] == "trainer_discard_energy" and body.pop(0)["pokemon_id"] != e["pokemon_id"]:
                problems.append(f"{label} でエネルギーカードをすてたポケモンが、とりのぞいたポケモンではない")
    elif isinstance(effect, HealOwnerPokemonThenDiscardHand):
        healed = take("remove_damage_counters", user)
        take("discard_hand", user)
        if healed is not None and (healed["total_damage"] != 0 or healed["counters"] <= 0):
            problems.append(f"{label} で、選んだポケモンのダメージカウンターをすべてとりのぞいていない")
    elif isinstance(effect, MoveAllEnergyBetweenOwnerPokemon):
        take("trainer_move_energy", user)
        skip("power_heal")
    elif isinstance(effect, SwitchBothActivesTrainer):
        for player in (opponent, user):
            if body and body[0]["kind"] == "trainer_switch_skipped" and body[0]["player"] == player:
                body.pop(0)
            else:
                take("switch", player)
                skip("special_conditions_removed", "persistent_effect_removed")
    if body:
        problems.append(f"{label} の最後に、処理にないイベント {[e['kind'] for e in body]} がある")
    return problems


def _effect_of_event(state, e: dict):
    """ワザの効果のログ ``e`` の ``effect``（処理したワザ。相手のワザを自分のワザとして使ったら、そのワザ）の登録の実装（v0.41）。"""
    entry = state.effects.attack_entry(*_attack_key(e["effect"]))
    return None if entry is None else entry.effect


def _same_attack(attack_window: dict | None, e: dict) -> bool:
    """ワザの効果のログ ``e`` の ``effect`` が、今のワザ（``attack_window``）か、そのワザが自分のワザとして使った相手のワザ（``copy_attack`` の ``copied``）か（v0.44）。"""
    return attack_window is not None and e.get("effect") is not None and e.get("effect") in (attack_window["effect"], attack_window.get("copied"))


def coin_gated_effect_problems(state, log: list[dict]) -> list[str]:
    """v0.76（docs/persistent-attack-modifiers-v0.76.md 8 章）: コインの面で与える持続する効果が決まるワザの、コインと与えた効果の対応。

    - ワンリキーの「きあいいっぱつ」（``CoinNextTurnMultiplyElseLockAttack``）: ワザ全体のコインを 1 枚だけ投げ、「おもて」なら「数をかける」効果
      （``next_turn_attack_damage_multiplier``）、「うら」なら登録の位置（``attack_lock_terms``）のワザを使えない効果（``cannot_use_own_attack``）を、ワザを使ったポケモンに
      ちょうど 1 つ与える（両方を与えない）
    - コンパンの「かなしばり」（``LockOpponentAttackOnHeads``）・「にらみつける」など（``AttackLockWhileSourceActiveOnHeads``）: コインは 1 枚まで。「うら」なら効果を与えない。
      効果を与えたら、そのすぐ前のこのワザのコインが「おもて」
    ワザの処理は、そのワザの ``attack`` のあと、次の ``attack``・``turn_start`` の前までのログ（決定をまたいでも同じ番の中）。"""
    problems = []
    gated = (CoinNextTurnMultiplyElseLockAttack, LockOpponentAttackOnHeads, AttackLockWhileSourceActiveOnHeads)
    for i, e in enumerate(log):
        if e["kind"] != "attack":
            continue
        effect = _attack_effect_of(state, e)
        if not isinstance(effect, gated):
            continue
        key = f"{_attack_card_id(state, e)}#{e['attack_index']}"
        end = next((j for j in range(i + 1, len(log)) if log[j]["kind"] in ("attack", "turn_start")), len(log))
        window = log[i + 1:end]
        coins = [x for x in window if x["kind"] == "coin_flip" and x.get("source") == "attack" and x.get("effect") == key]
        given = [x for x in window if x["kind"] == "persistent_effect_added" and x.get("effect") == key]
        where = f"{e['turn']} 番のワザ {key}"
        if len(coins) > 1 or len(given) > 1:
            problems.append(f"{where} のコイン {len(coins)} 枚・与えた効果 {len(given)} つが、1 つまでではない")
            continue
        if given and (not coins or coins[0]["result"] != "heads") and not isinstance(effect, CoinNextTurnMultiplyElseLockAttack):
            problems.append(f"{where} が、「おもて」のコインなしに効果を与えた")
        if isinstance(effect, CoinNextTurnMultiplyElseLockAttack) and coins:
            # 「数をかける」効果のログは位置・かける数を書かない（v0.35 と同じ形。状態の効果の位置・数は不変条件 ``engine._next_turn_attack_damage_problems`` が
            # 登録の ``next_turn_terms`` と照らす）。使えなくなる効果のログは使えなくなるワザの位置を書く
            heads = coins[0]["result"] == "heads"
            expected = ("next_turn_attack_damage_multiplier", None) if heads else ("cannot_use_own_attack", effect.attack_lock_terms()[1])
            found = [(x["persistent_effect"], x.get("target_attack_index")) for x in given]
            skipped = any(x["kind"] == "persistent_effect_skipped" and x.get("effect") == key for x in window)
            if found != [expected] and not (skipped and not found):
                problems.append(f"{where} のコイン {coins[0]['result']} で与えた効果 {found} が、{expected} の 1 つではない")
    return problems


def _attack_key(text: str) -> tuple[str, int]:
    """ログのワザ（``AttackKey`` の文字列 ``"カード id#位置"``）を (カード id, 位置) にする（v0.12）。"""
    card_id, _, index = text.partition("#")
    return card_id, int(index) if index.isdigit() else -1


def _attack_card_id(state, attack_event: dict) -> str:
    """ログのワザ（``attack``）を印刷したカードの id（v0.49。ワザの出どころがいちばん上のカードと違うときはログの ``card_id``。なければいちばん上のカード）。"""
    return attack_event.get("card_id") or state.in_play_def(attack_event["pokemon"]).id


def _attack_effect_of(state, attack_event: dict | None):
    """ログのワザ（``attack``）の、その対戦の登録表の実装（v0.30。v0.49 からワザを印刷したカードで引く）。"""
    if attack_event is None:
        return None
    entry = state.effects.attack_entry(_attack_card_id(state, attack_event), attack_event["attack_index"])
    return None if entry is None else entry.effect


def _v046_rank(label: str) -> int:
    """ダメージの記録の段階の名前（v0.46）: 0 = v0.45 までの効果、1 = 「リフレクター」（持続する効果 ``halved_damage``）、2 = 常にはたらく特殊能力（名前に［］）。
    計算の順番の決定がない段階では、エンジンが集めた順番（v0.45 までの効果 → リフレクター → 常にはたらく特殊能力）に並ぶ。"""
    if "［" in label:
        return 2
    if label.endswith((f"（{HalvedDamage.kind}）", f"（{DoubledDamage.kind}）", f"（{ZeroDamageAtLeast.kind}）")):  # v0.84: 「パルスガード」も
        return 1  # v0.75: 「もろばバサミ」（doubled_damage）も同じ 8 段階の持続する効果
    return 0


def _poison_problems(state, e: dict, current: int | None) -> list[str]:
    """ログ ``special_condition``（どく）の量（v0.34）。どく状態にしたワザの登録が特殊などく（``DamageAndSpecialPoison``。v0.39 からキョウのマタドガスの
    ``DamageThenSpecialPoisonOnHeads`` も）ならその量、ほかは通常のどくの 10（p.322）。すでにどく状態なら ``already``。受けるダメージの違うどく状態から特殊などくにすることはない（v0.3a の #15。
    止めるはず）。特殊などく → 通常のどくは通常のどくになる（v0.3a の #14）。"""
    found = []
    entry = state.effects.attack_entry(*_attack_key(e["effect"]))
    effect = entry.effect if entry is not None else None
    # v0.44: キョウのコクーンの「どくどくえき」（SpecialPoisonOnHeadsWithoutDamage）
    expected = effect.poison_damage if isinstance(effect, (DamageAndSpecialPoison, DamageThenSpecialPoisonOnHeads, SpecialPoisonOnHeadsWithoutDamage)) else 10
    if e.get("damage") != expected:
        found.append(f"{e['turn']} 番のどく（ワザ {e['effect']}）の量 {e.get('damage')} が、登録の実装の量 {expected} と違う")
    if current is not None and not e.get("already"):
        found.append(f"{e['turn']} 番のどく（ポケモン {e['pokemon_id']}）の already {e.get('already')} が、ログから組み立てたどく状態 {current} と合わない")
    if current is not None and current != expected and expected != 10:
        found.append(f"{e['turn']} 番に、どくの量 {current} のポケモン {e['pokemon_id']} を、量の違う特殊などく {expected} にした（v0.3a の #15。止めるはず）")
    return found


# v0.31: ワザを使ったポケモンのエネルギーカードをトラッシュしうる要素（トラッシュの要素・自分に控えがいない／受けなかったときにトラッシュする
# エナジーボム・のぞむならトラッシュするひばしら）
# v0.72: デンキとばし（MoveOneEnergyToBench）も、控えがいない・つける控えが受けなかったときにトラッシュする
DISCARDING_ELEMENTS = (DiscardOwnEnergy, MoveOwnEnergyToBench, MoveOneEnergyToBench, OptionalDiscardBenchDamage,
                       OptionalDiscardForBonus, OptionalDiscardAll, DiscardEachType)  # v0.82


# v0.42: 宣言する特殊能力の宣言（pokemon_power）のすぐあとに続く処理のログ（v0.41 までの move_energy・power_attach_energy・move_damage_counter・
# energy_burn・power_heal は、それぞれの分岐が宣言との対応を確かめる）
DECLARED_FOLLOWERS = ("move_energy", "power_attach_energy", "move_damage_counter", "energy_burn", "power_heal")


def _power_effect(state, key: str | None):
    """ログの特殊能力（``PowerKey`` の文字列 ``"カード id@power位置"``）の登録の実装（v0.42。なければ None）。"""
    card_id, _, index = str(key).partition("@power")
    entry = state.effects.power_entry(card_id, int(index)) if index.isdigit() else None
    return None if entry is None else entry.effect


def _follows_declaration(state, key: str, player: int, pid: int, e: dict) -> bool:
    """v0.42: 特殊能力 ``key``（プレイヤー ``player`` のポケモン ``pid`` が宣言した）の宣言のすぐあとのログ ``e`` が、その処理の最初のログか。コインを投げる
    特殊能力（ヒーリング・かおりのわな）は持ち主のそのコイン、かけつけるは自分の場の入れ替え（``switch`` の ``effect``）、ぶっしつこうかんは手札のトラッシュ
    （``discard_from_hand`` の ``power``。そのあいだに決定がある）、おくびょうはダメージカウンターをすべてとりのぞく処理（``remove_all_damage_counters`` の ``power``）。"""
    effect = _power_effect(state, key)
    kind = e["kind"]
    if isinstance(effect, ConvertSelfToEnergy):
        # v0.59: ［エネエネ］は、決定（つける先・色）のあと、使ったマルマインのきぜつ（timing power・to_energy）
        return kind == "knock_out" and e["player"] == player and e.get("timing") == "power" and "to_energy" in e
    if isinstance(effect, (HealOwnPokemonOnHeads, SwitchOpponentOnHeads)):
        return kind == "coin_flip" and e["source"] == "power" and e.get("effect") == key and e["player"] == player and e.get("pokemon_id") == pid
    if isinstance(effect, SwitchSelfFromBench):
        return kind == "switch" and e.get("effect") == key and e["player"] == player
    if isinstance(effect, DiscardThenDraw):
        return kind == "discard_from_hand" and e.get("power") == key and e["player"] == player
    if isinstance(effect, ReturnSelfToHand):
        return kind == "remove_all_damage_counters" and e.get("power") == key and e["player"] == player and e["pokemon_id"] == pid
    # v0.43: くさいかふん・えんかくさいみんは持ち主のコイン、しんかのひかりは山札から見せて手札に加える処理（そのあいだに決定がある）、場に出たときの特殊能力は
    # こっそりかみつくの特殊能力のダメージ・つりあげるのトラッシュから手札に加える処理（加えるものがないなら recover_pokemon_none）・てしたをよぶの山札からベンチに
    # 出す処理（つける・つけかえるもの（ほのおをもらう・ようぶんきゅうしゅう・エナジーチャージ）は move_energy の分岐が確かめる）
    if isinstance(effect, CoinConditionOnEitherActive):
        return kind == "coin_flip" and e["source"] == "power" and e.get("effect") == key and e["player"] == player and e.get("pokemon_id") == pid
    if isinstance(effect, SearchEvolutionCardToHand):
        return kind == "reveal_from_deck" and e.get("power") == key and e["player"] == player
    if isinstance(effect, DamageOpponentPokemonOnEntry):
        return kind == "power_damage" and e.get("power") == key and e["player"] == player and e["pokemon_id"] == pid
    if isinstance(effect, RecoverPokemonFromDiscardOnEntry):
        return kind in ("recover_pokemon", "recover_pokemon_none") and e.get("power") == key and e["player"] == player and e["pokemon_id"] == pid
    if isinstance(effect, BenchBasicsFromDeckOnEntry):
        return kind == "bench_from_deck" and e.get("power") == key and e["player"] == player and e["pokemon_id"] == pid
    # v0.44: ［うか］は持ち主のコイン、［ボスをよぶ］は山札のサカキを手札に加える処理（search_deck の power。そのあいだに決定がある）
    if isinstance(effect, CoinEvolveSelfFromDeck):
        return kind == "coin_flip" and e["source"] == "power" and e.get("effect") == key and e["player"] == player and e.get("pokemon_id") == pid
    if isinstance(effect, SearchNamedTrainerOnEntry):
        return kind == "search_deck" and e.get("power") == key and e["player"] == player
    # v0.47: ［スパイ］は見る処理（look_at_card の power）、［わるふざけ］はサイドと山札の一番上の入れかえ（そのあいだに決定がある）
    if isinstance(effect, PeekCard):
        return kind == "look_at_card" and e.get("power") == key and e["player"] == player
    if isinstance(effect, SwapPrizeWithDeckTop):
        return kind == "swap_prize_with_deck_top" and e.get("power") == key and e["player"] == player
    # v0.48: ［へんしょく］は色を変えた記録（type_shift。そのあいだに色を選ぶ決定がある）
    if isinstance(effect, ShiftColor):
        return kind == "type_shift" and e.get("power") == key and e["player"] == player and e["pokemon_id"] == pid
    # v0.49: 「ばける」は手札の進化カードをのせた記録（disguise。そのあいだに手札の進化カードを選ぶ決定がある）
    if isinstance(effect, Shapeshift):
        return kind == "disguise" and e.get("power") == key and e["player"] == player and e["pokemon_id"] == pid
    # v0.84: ［おいはらう］は相手の場の入れ替え（switch の power。そのあいだに相手の決定がある）、［たすけだす］はバトルポケモンのカウンターをとりのぞく処理
    # （tag_team_heal）、［おくりもの］はどちらかのプレイヤーの答えの結果（gift_declined・reveal_from_deck・gift_take_none。そのあいだに決定がある）
    if isinstance(effect, SwitchOpponentChosenByOpponent):
        return kind == "switch" and e.get("power") == key and e["player"] == 1 - player
    if isinstance(effect, HealActiveThenSwitchOnBenchEntry):
        return kind == "tag_team_heal" and e.get("power") == key and e["player"] == player
    if isinstance(effect, EachPlayerSearchToolOnEntry):
        return kind in ("gift_declined", "reveal_from_deck", "gift_take_none") and e.get("power") == key
    # v0.85: ［あばれんぼう］（かならずはたらく）・［ハーブのかおり］・［ファイヤーブースト］・［ファイヤーリチャージ］は持ち主のコイン、［どしゃぶり］は手札のトラッシュ
    # （discard_from_hand の power）。［ファイヤーレイズ］のつけ替えは move_energy の分岐が確かめる
    if isinstance(effect, (CoinMillDeckOnEvolve, CoinHealTypePokemonOnEntry, CoinAttachFromDeckOnEntry, CoinAttachFromDiscardToTypePokemon)):
        return kind == "coin_flip" and e["source"] == "power" and e.get("effect") == key and e["player"] == player and e.get("pokemon_id") == pid
    if isinstance(effect, DiscardTypeEnergyFromHand):
        return kind == "discard_from_hand" and e.get("power") == key and e["player"] == player
    # v0.86: ［エナジーしんか］・［タマゴうみ］の 2 回目は持ち主のコイン（［タマゴうみ］の 1 回目は remove_damage_counters の step 1）、［れんさしんか］は山札から重ねる・重ねるカードが
    # ない（そのあいだに決定がある）、［おたけび］は山札の上からのトラッシュ、［いなびかり］は相手の場の入れ替え（そのあいだに相手の決定がある）、［いやしのかぜ］はポケモンごとの
    # remove_damage_counters（ダメージカウンターのあるポケモンがいなければ何もない）、［ソーラーパワー］はお互いの対戦ポケモンの特殊状態の回復（cured）
    if isinstance(effect, EvolveFromDeckByAttachedEnergyColor):
        return kind == "coin_flip" and e["source"] == "power" and e.get("effect") == key and e["player"] == player and e.get("pokemon_id") == pid
    if isinstance(effect, HealThenCoinHealOnEvolve):
        return kind == "remove_damage_counters" and e.get("power") == key and e.get("step") == 1 and e["pokemon_id"] == pid
    if isinstance(effect, EvolveFromDeckOnOtherEvolution):
        return kind in ("evolve", "evolve_from_deck_none") and e.get("power") == key and e["pokemon_id"] == pid
    if isinstance(effect, DiscardDeckTopAttachTypeEnergyThenEndTurn):
        return kind == "deck_top_to_discard" and e.get("power") == key and e["player"] == player
    if isinstance(effect, SwitchOpponentOnTypeEnergyAttach):
        return kind == "switch" and e.get("power") == key and e["player"] == 1 - player
    if isinstance(effect, HealEachOwnPokemonOnEntry):
        return not (kind == "remove_damage_counters" and (e.get("power") != key or e["player"] != player))
    if isinstance(effect, CureBothActivesOncePerTurn):
        return kind == "special_conditions_removed" and e.get("reason") == "cured"
    return False


def _power_coin_follows(state, coin: dict, e: dict) -> bool:
    """特殊能力のコイン（``coin_flip`` の ``source`` が ``power``）のすぐあとのログ ``e`` が、そのコインの結果か。v0.9 の「とうめい」は判定（evade_check）、
    v0.11 の「こんじょう」は結果（ko_prevented・ko_prevention_failed）。v0.42 の「ぼうぎょかふん」は結果（power_confusion）、ヒーリング・かおりのわなは
    「おもて」なら処理（power_heal・switch。そのあいだに決定がある）、「うら」なら何もしない（そのあとに処理がない）。"""
    effect = _power_effect(state, coin.get("effect"))
    kind = e["kind"]
    if isinstance(effect, ConfuseDamageSourceOnHeads):
        return kind == "power_confusion" and e["power"] == coin["effect"] and e["result"] == coin["result"]
    if isinstance(effect, HealOwnPokemonOnHeads):
        return (kind == "power_heal" and e.get("power") == coin["effect"]) if coin["result"] == "heads" else kind != "power_heal"
    if isinstance(effect, SwitchOpponentOnHeads):
        return (kind == "switch" and e.get("effect") == coin["effect"]) if coin["result"] == "heads" else not (
            kind == "switch" and e.get("effect") == coin["effect"])
    if isinstance(effect, CoinConditionOnEitherActive):
        # v0.43: 「おもて」なら相手の、「うら」なら自分の対戦ポケモンが、その特殊状態になる（ほかのねむり・マヒ・こんらんがあれば、それを消してから。p.322）
        side = coin["player"] if coin["result"] == "tails" else 1 - coin["player"]
        if kind == "special_conditions_removed":
            return e["player"] == side and e["reason"] == "replaced"
        # v0.46: その対戦ポケモンが［めんえき］で特殊状態にならない（special_condition_prevented。置きかえる前に防ぐ）
        return kind in ("special_condition", "special_condition_prevented") and e.get("effect") == coin["effect"] and e["player"] == side \
            and e["condition"] == effect.condition
    if isinstance(effect, CoinEvolveSelfFromDeck):
        # v0.44: ［うか］。「おもて」なら山札のカードを重ねる（evolve。そのあいだに決定がある）か、重ねられるカードがない（evolve_from_deck_none）。「うら」なら何もしない
        mine = kind in ("evolve", "evolve_from_deck_none") and e.get("power") == coin["effect"] and e["pokemon_id"] == coin.get("pokemon_id")
        return mine if coin["result"] == "heads" else not (kind in ("evolve", "evolve_from_deck_none") and e.get("power") == coin["effect"])
    if isinstance(effect, FailAndReturnOnAttack):
        # v0.60: ［はんこう］。同じ特殊能力の次のコインか、すべて投げたあとの判定（rebellion_check）
        if coin["number"] < coin["count"]:
            return kind == "coin_flip" and e["source"] == "power" and e["effect"] == coin["effect"] and e["number"] == coin["number"] + 1
        return kind == "rebellion_check" and e["power"] == coin["effect"]
    if isinstance(effect, DamageOnOpponentRetreat):
        # v0.61: ［おとしあな］。にげたプレイヤーのコインのすぐあとに判定（sinkhole_check）
        return kind == "sinkhole_check" and e["power"] == coin["effect"] and e["flipper"] == coin["player"] and e["result"] == coin["result"]
    if isinstance(effect, DiscardAttackerEnergyOnDamage):
        # v0.68: ［だつりょくえき］。持ち主のコインのすぐあとに判定（energy_drain_check）。「おもて」ならそのあとに決定とトラッシュ（energy_drain_discard）
        return kind == "energy_drain_check" and e["power"] == coin["effect"] and e["player"] == coin["player"] and e["result"] == coin["result"]
    if isinstance(effect, BeamOnKnockOut):
        # v0.61: ［ファイナルビーム］。「おもて」ならダメージ（knock_out_power_damage）、「うら」なら knock_out_power_failed
        return kind == ("knock_out_power_damage" if coin["result"] == "heads" else "knock_out_power_failed") and e["power"] == coin["effect"]
    if isinstance(effect, SleepDamageSourceOnHeads):
        # v0.84: ［ふかふかなからだ］。持ち主のコインのすぐあとに結果（power_sleep）
        return kind == "power_sleep" and e["power"] == coin["effect"] and e["result"] == coin["result"]
    if isinstance(effect, CoinMillDeckOnEvolve):
        # v0.85: ［あばれんぼう］。「おもて」なら相手の、「うら」なら自分の山札の上から（power_discard_deck）
        side = 1 - coin["player"] if coin["result"] == "heads" else coin["player"]
        return kind == "power_discard_deck" and e["power"] == coin["effect"] and e["player"] == side and e["user"] == coin["player"]
    if isinstance(effect, CoinHealTypePokemonOnEntry):
        # v0.85: ［ハーブのかおり］。「おもて」ならポケモンごとの remove_damage_counters（「草」ポケモンにダメージカウンターがなければ何もない）。「うら」なら何もしない
        healed = kind == "remove_damage_counters" and e.get("power") == coin["effect"]
        return True if coin["result"] == "heads" else not healed
    if isinstance(effect, CoinAttachFromDeckOnEntry):
        # v0.85: ［ファイヤーブースト］。「おもて」なら山札からつける（power_attach_from_deck）か、つけずに切る（shuffle。そのあいだに決定がある）。「うら」なら何もしない
        mine = kind in ("power_attach_from_deck", "shuffle") and e.get("power") == coin["effect"]
        return mine if coin["result"] == "heads" else not mine
    if isinstance(effect, CoinAttachFromDiscardToTypePokemon):
        # v0.85: ［ファイヤーリチャージ］。「おもて」ならトラッシュからつける（power_attach_from_discard。そのあいだに 2 つの決定がある）。「うら」なら何もしない
        mine = kind == "power_attach_from_discard" and e.get("power") == coin["effect"]
        return mine if coin["result"] == "heads" else not mine
    if isinstance(effect, ReturnToDeckOnHeadsAfterDamage):
        # v0.86: ［はしりさる］。持ち主のコインのすぐあとに判定（bolt_check）。「おもて」ならそのあとに山札にもどす（return_in_play_to_deck）
        return kind == "bolt_check" and e["power"] == coin["effect"] and e["player"] == coin["player"] and e["result"] == coin["result"]
    if isinstance(effect, EvolveFromDeckByAttachedEnergyColor):
        # v0.86: ［エナジーしんか］。「おもて」なら山札から重ねる（evolve）か、重ねるカードがない（evolve_from_deck_none。そのあいだに決定がある）。「うら」なら何もしない
        mine = kind in ("evolve", "evolve_from_deck_none") and e.get("power") == coin["effect"] and e["pokemon_id"] == coin.get("pokemon_id")
        return mine if coin["result"] == "heads" else not (kind in ("evolve", "evolve_from_deck_none") and e.get("power") == coin["effect"])
    if isinstance(effect, HealThenCoinHealOnEvolve):
        # v0.86: ［タマゴうみ］。「おもて」なら 2 回目の remove_damage_counters（step 2）。「うら」なら何もしない
        mine = kind == "remove_damage_counters" and e.get("power") == coin["effect"] and e.get("step") == 2
        return mine if coin["result"] == "heads" else not (kind == "remove_damage_counters" and e.get("power") == coin["effect"])
    return kind in ("evade_check", "ko_prevented", "ko_prevention_failed")


def _returns_without_shuffle(state, effect: str) -> bool:
    """v0.38: ワザ ``effect``（ログの ``AttackKey`` の文字列）の要素の並びの、自分を山札にもどす要素が、もどしたあとに山札を切らない（あとの要素が
    山札をさがしてから切る。キョウのポッポの「でんれい」）か。"""
    card_id, _, index = effect.partition("#")
    entry = state.effects.attack_entry(card_id, int(index)) if index.isdigit() else None
    return any(type(element).__name__ == "ReturnSelfToDeck" and not element.shuffle for element in _program_of(None if entry is None else entry.effect))


def _benches_any_from_deck(state, effect: str) -> bool:
    """v0.40: ワザ ``effect`` の要素の並びに、山札から好きなだけベンチに出す要素（キョウのズバットの「むれでおそう」。``BenchFromDeckAny``）があるか。そのワザの
    ``bench_from_deck`` は 1 回のワザに何回もあり、出したあと 1 回だけ山札を切る。"""
    card_id, _, index = str(effect).partition("#")
    entry = state.effects.attack_entry(card_id, int(index)) if index.isdigit() else None
    return any(type(element).__name__ == "BenchFromDeckAny" for element in _program_of(None if entry is None else entry.effect))


def _damage_element_limits(effect) -> tuple[int, int]:
    """v0.40: 登録した実装の要素の並びの、相手の対戦ポケモン・自分へのダメージの要素の数（1 回のワザで同じポケモンが受けるダメージの要素の上限。わるいマタドガスの
    「みんなでばくはつ」は相手の対戦ポケモンに 2 つ）。並びのない実装は 1 つずつ。"""
    program = _program_of(effect)
    opponent = sum(1 for element in program if isinstance(element, Damage) and element.target == "opponent_active")
    own = sum(1 for element in program if isinstance(element, Damage) and element.target == "self")
    return max(opponent, 1), max(own, 1)


def _program_of(effect) -> tuple:
    """登録した実装の、解決の基盤の要素の並び（v0.31。対応表にない実装は空）。"""
    builder = None if effect is None else BUILDERS.get(type(effect))
    return () if builder is None else tuple(builder(effect))


def _is_discarding(element) -> bool:
    """ワザを使ったポケモンのエネルギーカードをトラッシュしうる要素か（v0.31）。v0.42 のエネループ（``ReturnOwnEnergyToHand``。トラッシュの要素と同じ選び方で、
    行き先が手札。ログ ``return_energy_to_hand``）はトラッシュしない。"""
    return isinstance(element, DISCARDING_ELEMENTS) and not isinstance(element, ReturnOwnEnergyToHand)


def _discard_elements(program) -> list:
    """要素の並びのうち、ワザを使ったポケモンのエネルギーカードをトラッシュしうる要素（v0.31）。"""
    return [element for element in program if _is_discarding(element)]


def _discard_position(program) -> str | None:
    """トラッシュの要素が、相手へのダメージの要素より前（``"before"``）か、あと（``"after"``）か（v0.31。どちらもなければ None）。"""
    discards = [i for i, element in enumerate(program) if _is_discarding(element)]
    damages = [i for i, element in enumerate(program) if isinstance(element, Damage) and element.target != "self"]
    if not discards or not damages:
        return None
    return "before" if discards[0] < damages[0] else "after"


def _discard_energy_window_problems(state, effect, window: Counter, *, log_ended: bool) -> list[str]:
    """ワザ 1 回のエネルギーのトラッシュ（``discard_energy``）の数が、登録した実装と合うか（v0.30。v0.31 から要素の並びで確かめる）。"""
    discarded = window["discard_energy"]
    if isinstance(effect, DiscardEnergyAndRemoveAllCounters):
        if discarded != window["remove_all_damage_counters"]:
            return ["1 回のワザで、エネルギーのトラッシュとダメージカウンターをすべてとりのぞく処理の数が違う（じこさいせい）"]
        return []
    if isinstance(effect, DiscardEnergyThenDamage):
        if window["confusion_damage"] or window["discard_energy_failed"]:
            # こんらんで「うら」なら、もとのワザの要素はない（p.309 の手順 5）。v0.82: 相手のワザとして使い、トラッシュできなかった（v0.31 から起こりうる。ログ
            # discard_energy_failed。この確かめが数えていなかった）
            expected = {0}
        elif log_ended and state.decision is not None and state.decision.kind == DISCARD_ENERGY:
            expected = {0}  # トラッシュするカードを選ぶ決定を待っている（最後のワザ）
        else:
            expected = {1}
        if discarded not in expected:
            return [f"1 回のワザ（{effect.implementation_id}）で、エネルギーのトラッシュが {discarded} 回（{sorted(expected)} のはず）"]
        return []
    elements = _discard_elements(_program_of(effect))
    if not elements:
        if discarded:
            return [f"エネルギーをトラッシュしないワザ（{type(effect).__name__}）で、エネルギーのトラッシュが {discarded} 回"]
        return []
    exact = [element for element in elements if isinstance(element, DiscardOwnEnergy) and isinstance(element.count, int) and element.gate is None
             and element.local_coin is None and element.heads_of is None and not element.any_number]
    interrupted = (window["confusion_damage"] or window["attack_failed"] or window["discard_energy_failed"] or window["effect_skipped"]
                   or (log_ended and state.decision is not None and state.decision.resume == "attack"))
    if len(exact) == len(elements) and not interrupted and discarded != sum(element.count for element in exact):
        return [f"1 回のワザ（{type(effect).__name__}）で、エネルギーのトラッシュが {discarded} 回（{sum(e.count for e in exact)} のはず）"]
    return []


def _persistent_effect_live(state, event) -> bool:
    """v0.84: ログの ``event`` の時点で、同じポケモンに同じ種類の持続する効果がある（``persistent_effect_added`` があり、そのあとに ``persistent_effect_removed`` がない）か。"""
    live = False
    for e in state.log:
        if e == event:  # 監査はログの写しを読むので、同じ内容のイベントで比べる
            return live
        if e.get("pokemon_id") == event["pokemon_id"] and e.get("persistent_effect") == event["persistent_effect"]:
            if e["kind"] == "persistent_effect_added":
                live = True
            elif e["kind"] == "persistent_effect_removed":
                live = False
    return False


def log_problems(state) -> list[str]:
    """``new_game`` から進めた対戦のログと状態の整合の問題（なければ空）。"""
    log = [dict(e) for e in state.log]
    problems: list[str] = []

    # 1. 番は増えていき、番の始まりは 1 つずつ交互（p.309）
    turns = [e["turn"] for e in log]
    if turns != sorted(turns):
        problems.append("ログの番が増えていく順になっていない")
    starts = [e for e in log if e["kind"] == "turn_start"]
    janken = next((e for e in log if e["kind"] == "janken"), None)
    for index, event in enumerate(starts):
        expected_player = None if janken is None else (janken["first_player"] + index) % 2
        if event["turn"] != index + 1 or event["player"] != expected_player:
            problems.append(f"{index + 1} 回目の番の始まりが {event['turn']} 番・プレイヤー {event['player']}")
            break

    # 2. 番ごと: 番と番のあいだに turn_end → pokemon_check が 1 回ずつ。ワザ・ワザを使わずに終える は合わせて 1 回まで
    per_turn: dict[int, list[str]] = {}
    for e in log:
        per_turn.setdefault(e["turn"], []).append(e["kind"])
    last_turn = starts[-1]["turn"] if starts else 0
    for turn, kinds in per_turn.items():
        if turn == 0:
            continue
        marks = [k for k in kinds if k in ("turn_end", "pokemon_check")]
        if turn < last_turn and marks != ["turn_end", "pokemon_check"]:
            problems.append(f"{turn} 番の番の終わり・ポケモンチェックが {marks}")
        if turn == last_turn and marks not in ([], ["turn_end", "pokemon_check"]):
            problems.append(f"最後の {turn} 番の番の終わり・ポケモンチェックが {marks}")
        ends = kinds.count("attack") + kinds.count("end_turn_without_attack") + kinds.count("trainer_turn_end")  # v0.56: ロケット団員の「うら」でも番が終わる
        if ends > 1:
            problems.append(f"{turn} 番にワザ・番を終える操作が {ends} 回")

    # 3. ワザ 1 回の要素: 同じポケモンへのダメージの要素は 1 回（相手の対戦ポケモン・自分）。こんらんしたらワザの要素はない
    window = None
    attack_event: dict | None = None
    window_effect = None  # v0.31: 今のワザの登録の実装（相手のワザを自分のワザとして使ったら、そのワザの実装）
    for e in log + [{"kind": "turn_end", "turn": None}]:
        kind = e["kind"]
        if kind == "attack":
            window = Counter()
            attack_event = e
            window_effect = _attack_effect_of(state, e)
            continue
        if window is None:
            continue
        if kind in ("turn_end", "game_end", "halted"):
            problems.extend(_discard_energy_window_problems(state, window_effect, window, log_ended=e["turn"] is None))
            opponent_limit, own_limit = _damage_element_limits(window_effect)  # v0.40: みんなでばくはつは相手の対戦ポケモンに 2 つ
            if window["damage:opponent"] + window["prevented:opponent_active"] > opponent_limit or window["damage:self"] + window["prevented:self"] > own_limit:
                problems.append(f"1 回のワザで同じポケモンへのダメージの要素が、登録の要素の数より多い {dict(window)}")
            if any(count > 1 for key, count in window.items() if key.startswith("damage:bench:") or key.startswith("prevented:bench:")):
                problems.append(f"1 回のワザで同じ控えポケモンへのダメージの要素が 2 回以上 {dict(window)}")
            if window["confusion_damage"] and (window["damage:opponent"] or window["damage:self"] or window["prevented:opponent_active"]):
                problems.append("こんらんしたワザに、もとのワザのダメージの要素がある")
            if window["attack_failed:attack_check"] and (window["confusion_check"] or window["damage:opponent"] or window["damage:self"]
                                                          or window["prevented:opponent_active"] or window["persistent_effect_added"]
                                                          or window["special_condition"] or window["evade_check"]):
                problems.append(f"手順 4 のコインで失敗したワザに、こんらんのコイン・ワザの要素がある {dict(window)}")  # v0.36
            # v0.86: ほのおのまもり（DamageThenProtectOwnBench）は、自分の控えポケモン全員に 1 つずつ（下で確かめる）
            protects_bench = isinstance(window_effect, DamageThenProtectOwnBench)
            if protects_bench and window["persistent_effect_added"] > 5:
                problems.append(f"1 回のワザでほのおのまもりの効果が {window['persistent_effect_added']} 回（控えポケモンの数より多い）")
            for once in ("forced_switch", "drain_heal", "confusion_check", "confusion_damage", *(() if protects_bench else ("persistent_effect_added",)),
                         "remove_all_damage_counters", "recover_energy", "drain_heal_skipped",
                         # v0.31
                         "copy_attack", "attack_failed", "recover_trainer", "attach_energy_from_discard", "destiny_bond",
                         # v0.36
                         "attack_check",
                         # v0.52: つれさる（ReturnBothActivesToDeck）は自分と相手で 2 回まで（下で確かめる）
                         *(() if getattr(window_effect, "returns_both_actives", False) else ("return_in_play_to_deck",)),
                         # v0.38
                         "discard_attached_cards",
                         # v0.41（v0.48 のダメージぞうふくは、相手の場のポケモンごとに 1 回。下で確かめる）
                         *(() if isinstance(window_effect, PlaceCountersOnDamagedOpponentPokemon) else ("place_damage_counters",)), "swap_damage_counters",
                         # v0.42
                         "return_energy_to_hand", "evolve", "evolve_from_deck_none", "switch_declined", "power_confusion",
                         "power_confusion_skipped",
                         # v0.46
                         "attach_energy_from_hand",
                         # v0.51
                         "bench_from_discard", "bench_from_discard_none"):
                if window[once] > 1:
                    problems.append(f"1 回のワザで {once} が {window[once]} 回")
            if any(count > 1 for key, count in window.items() if key.startswith("place_damage_counters:")):
                problems.append(f"1 回のワザで同じポケモンにダメージカウンターをのせる処理が 2 回以上 {dict(window)}")  # v0.48: ダメージぞうふく
            if any(count > 1 for key, count in window.items() if key.startswith("attack_heal:")):
                # v0.31・v0.41: ワザでダメージカウンターをとりのぞくのは、ポケモンごとに 1 回（v0.41 から、複数のポケモンからとりのぞくワザがある）
                problems.append(f"1 回のワザで同じポケモンからダメージカウンターをとりのぞく処理が 2 回以上 {dict(window)}")
            if window["return_in_play_to_deck"] > 2:
                problems.append(f"1 回のワザで山札にもどす処理が {window['return_in_play_to_deck']} 回")  # v0.52: つれさるでも自分と相手の 2 回まで
            if window["attack_energy_from_deck"] > (window_effect.max_cards if isinstance(window_effect, CoinAttachEnergyFromDeckToSelf)
                                                     else 6 if isinstance(window_effect, AttachFromDeckUpToNamedCount) else 1):
                # v0.41。v0.75: しおまねきは最大 3 枚（1 枚に 1 つの attach_energy_from_deck）
                problems.append("1 回のワザで山札からエネルギーをつける処理（attach_energy_from_deck・attach_energy_from_deck_none）が多すぎる")
            if isinstance(window_effect, ReturnHandThenRevealBasicEnergy):
                # v0.44: てじなは、もどした枚数と同じ枚数を 1 枚ずつ見せる（山札の基本エネルギーカードがなければ reveal_from_deck_none が 1 回。もどさなければどちらもない）
                # （決定を待ったまま対戦が終わったときは、見せる前のことがあるので 0 も許す）
                if window["hand_to_deck"] > 1 or (window["reveal_from_deck_none"] and window["reveal_from_deck"]) or window["reveal_from_deck_none"] > 1 \
                        or window["reveal_from_deck"] not in (0, window["hand_to_deck_cards"]) \
                        or (window["reveal_from_deck"] or window["reveal_from_deck_none"]) and not window["hand_to_deck"]:
                    problems.append(f"てじなで、山札にもどした枚数と見せて手札に加えた枚数・回数が合わない {dict(window)}")
            elif isinstance(window_effect, RevealNamedPokemonFromDeckAny):
                # v0.75: くらげのむれは好きなだけ見せる（reveal_from_deck が何回もあり、reveal_from_deck_none・reveal_from_deck_declined とはいっしょにない）
                if (window["reveal_from_deck_none"] + window["reveal_from_deck_declined"]) and window["reveal_from_deck"] \
                        or window["reveal_from_deck_none"] + window["reveal_from_deck_declined"] > 1:
                    problems.append(f"くらげのむれで、見せて手札に加えた処理の回数が合わない {dict(window)}")
            elif isinstance(window_effect, EachPlayerLookTopTakeBasicEnergy):
                # v0.83: みずかき。おたがいのプレイヤーが、それぞれ見た中の基本エネルギーカードを好きなだけ見せて手札に加える（見せない回は deck_top_take_declined）
                if window["reveal_from_deck_none"]:
                    problems.append(f"みずかきで、見せて手札に加えた処理の回数が合わない {dict(window)}")
            elif window["reveal_from_deck"] + window["reveal_from_deck_none"] > 1:
                problems.append("1 回のワザで山札から見せて手札に加える処理（reveal_from_deck・reveal_from_deck_none）が 2 回以上")  # v0.38
            if window["bench_from_deck"] + window["bench_from_deck_none"] > 1 and not (
                    attack_event is not None and _benches_any_from_deck(state, f"{_attack_card_id(state, attack_event)}#{attack_event['attack_index']}")
                    and not window["bench_from_deck_none"]):
                # v0.40: むれでおそうは好きなだけ出す（bench_from_deck が何回もあり、bench_from_deck_none はない）
                problems.append("1 回のワザで山札からベンチに出す処理（bench_from_deck・bench_from_deck_none）が 2 回以上")  # v0.32
            if window["forced_switch"] + window["forced_switch_skipped"] > 1:
                problems.append("1 回のワザで入れ替えの結果が 2 回以上")
            if window["counterattack"] + window["counterattack_skipped"] > 1:
                problems.append(f"1 回のワザで「はんげき」が {window['counterattack'] + window['counterattack_skipped']} 回（今の対応カードでは 1 回まで）")
            if window["drain_heal"] + window["drain_heal_skipped"] + window["drain_heal_declined"] > 1:  # v0.72: 取りのぞかなかった（きゅうけつの「取りのぞいてよい」）
                problems.append("1 回のワザで回復の結果が 2 回以上")
            # v0.11: 「こんじょう」を使うかの決定はワザ 1 回につき 1 回まで（今の対応カードでは、ワザのダメージを受ける相手のポケモンは 1 匹）。
            # 宣言 1 回につき結果（ko_prevented・ko_prevention_failed）が 1 回
            if window["ko_prevention_declined"] + window["ko_prevention_declared"] > 1:
                problems.append(f"1 回のワザで「こんじょう」を使うかの決定が {window['ko_prevention_declined'] + window['ko_prevention_declared']} 回（G14・G40）")
            if window["ko_prevented"] + window["ko_prevention_failed"] != window["ko_prevention_declared"]:
                problems.append("1 回のワザで「こんじょう」の宣言と結果（ko_prevented・ko_prevention_failed）の数が違う")
            # v0.12: 「ほのおのかべ」はワザ 1 回につき 1 回まで（ダメージを受ける相手のポケモンは 1 匹。W25）。そのダメージの要素も 1 回まで
            if window["retaliation"] + window["retaliation_skipped"] > 1 or window["damage:retaliation"] > window["retaliation"]:
                problems.append(f"1 回のワザで「ほのおのかべ」・「こうらがえし」が {window['retaliation'] + window['retaliation_skipped']} 回・そのダメージが {window['damage:retaliation']} 回")
            if window["post_knockout_power_declined"] + window["post_knockout_power_declared"] > 1:
                problems.append("1 回のワザのあとで「ふしちょう」を使うかの答えが 2 回以上")
            window = None
            continue
        if kind in ("pokemon_power", "move_energy", "power_attach_energy", "move_damage_counter"):
            # v0.5: ワザを使ったら番は終わる（p.309）ので、ワザのあと（番の終わりまで）に特殊能力の使用はない（v0.6 のあまごい・
            # v0.7 のダメージスワップも）
            problems.append(f"{e['turn']} 番のワザのあとに特殊能力の使用（{kind}）がある")
        if kind == "copy_attack":
            # v0.31: 相手のワザを自分のワザとして使った。このあとの要素は、そのワザの登録の実装で確かめる
            window_effect = state.effects.attack_entry(*_attack_key(e["copied"])).effect if state.effects.attack_entry(*_attack_key(e["copied"])) else None
        if kind == "discard_energy":
            # v0.30: エネルギーをトラッシュしてダメージを与えるワザは、トラッシュしてからダメージの要素を処理する（RUL-ENERGY-DISCARD-ATTACKS の
            # 最新の説明の順番）。トラッシュしたのは、ワザを使ったポケモンについていた、登録のタイプの基本エネルギーカード。v0.31 から、トラッシュの
            # 要素とダメージの要素の順番・トラッシュするタイプを、登録の要素の並びで確かめる
            effect = window_effect
            program = _program_of(effect)
            damaged = (window["damage:opponent"] + window["damage:self"] + window["prevented:opponent_active"] + window["prevented:self"]
                       + window["evade_check"])
            position = "before" if isinstance(effect, DiscardEnergyThenDamage) else _discard_position(program)
            if position == "before" and damaged:
                problems.append(f"{e['turn']} 番のワザのエネルギーのトラッシュが、そのワザのダメージの要素のあと")
            if position == "after" and not (window["damage:opponent"] + window["prevented:opponent_active"] + window["attack_evaded"]):
                problems.append(f"{e['turn']} 番のワザのエネルギーのトラッシュが、そのワザの相手へのダメージの要素より前")
            bench_discard = (isinstance(effect, OptionalDiscardEnergyBonusDamage) and effect.include_bench and e["player"] == attack_event["player"]
                             and e.get("attacker_pokemon_id") is not None)  # v0.82: ファイヤーバーンの控えのカード（ワザを使ったポケモンの番号を書く）
            if (e["player"], e["pokemon"]) != (attack_event["player"], attack_event["pokemon"]) and not bench_discard:
                problems.append(f"{e['turn']} 番のワザのエネルギーのトラッシュが、ワザを使ったポケモンのものでない")
            elements = _discard_elements(program)
            types = {getattr(element, "energy_type", None) for element in elements} if elements else {getattr(effect, "energy_type", None)}
            definition = state.printed_def(e["energy"])
            if None in types:
                if definition.category != "energy":
                    problems.append(f"{e['turn']} 番のワザでトラッシュしたカード {e['energy']} が、エネルギーカードでない")
            elif not definition.is_basic_energy or definition.provides not in types:
                problems.append(f"{e['turn']} 番のワザでトラッシュしたカード {e['energy']} が、登録のタイプ {types} の基本エネルギーカードでない")
        if kind == "damage":
            if e.get("target") in ("opponent_bench", "self_bench"):
                window[f"damage:bench:{e['pokemon_id']}"] += 1  # v0.31: 控えポケモンへのダメージ（v0.33 から自分の控えも）
            else:
                window["damage:retaliation" if e.get("retaliation") else "damage:self" if e.get("target") == "self" else "damage:opponent"] += 1
        elif kind == "damage_prevented":
            if e["target"] in ("opponent_bench", "self_bench"):
                window[f"prevented:bench:{e['pokemon_id']}"] += 1
            else:
                window[f"prevented:{e['target']}"] += 1
        else:
            window[kind] += 1
            if kind == "attack_failed" and e.get("reason") == "attack_check":
                window["attack_failed:attack_check"] += 1  # v0.36
            if kind == "attack_heal":
                window[f"attack_heal:{e['pokemon_id']}"] += 1  # v0.41
            if kind == "place_damage_counters":
                window[f"place_damage_counters:{e['pokemon_id']}"] += 1  # v0.48
            if kind == "hand_to_deck":
                window["hand_to_deck_cards"] += len(e["cards"])  # v0.44: てじな・ラッキーたまごで山札にもどした枚数
            if kind in ("attach_energy_from_deck", "attach_energy_from_deck_none"):
                window["attack_energy_from_deck"] += 1  # v0.41

    # 4. ログからの組み立て直し: 場のポケモンの番号・ダメージ・エネルギー・トラッシュ・サイド
    ids: dict[int, int] = {}  # いちばん上のカードの uid → 場のポケモンの番号
    next_id = 1
    damage: Counter = Counter()
    energy: dict[int, list[int]] = {}
    in_play: set[int] = set()
    discard: dict[int, list[int]] = {0: [], 1: []}
    prizes_taken: Counter = Counter()
    taken_cards: list[int] = []
    trainer_prizes = [0, 0]  # v0.56: トレーナーの効果（マチスの交渉）で取ったサイドの数（きぜつで取ったサイド prizes_taken とは別に数える）
    knocked: Counter = Counter()
    evolve_turns: dict[int, list[int]] = {}
    devolve_turns: dict[int, list[int]] = {}  # v0.50: 場のポケモンの番号 → 退化した番（ログの順）
    trainer_damaged: set[tuple[int, int]] = set()  # v0.61: バトル場は穴だらけ!でダメージを受けた (場のポケモンの番号, 番)（timing trainer のきぜつの確かめ）
    trainer_devolved: set[tuple[int, int]] = set()  # v0.50: トレーナー（退化スプレー）で退化した (場のポケモンの番号, 番)（timing trainer のきぜつの確かめ）
    permitted: set[tuple[int, int]] = set()  # v0.44: トレーナー「サカキ」の許可（場のポケモンの番号, 番）
    once_used: set[tuple[int, int, int]] = set()  # v0.44: 場に出てから 1 度しか使えないワザの記録（場のポケモンの番号, カードの uid, ワザの位置）
    added: dict[tuple, int] = {}
    removed: Counter = Counter()

    pokemon_owner: dict[int, int] = {}  # 場のポケモンの番号 → 持ち主（v0.5。エネルギーの移動は自分の場のポケモンのあいだだけ）
    top: dict[int, int] = {}  # 場のポケモンの番号 → いちばん上のカードの uid（v0.6。つける先のタイプを見る）
    turn_player: int | None = None  # 今の番のプレイヤー（最後の turn_start）
    hand: dict[int, list[int]] = {0: [], 1: []}  # 手札（v0.6。引いた・取ったサイド → 場に出した・つけた・使った）
    # v0.23: 使っている最中のトレーナーの使うための条件でトラッシュした手札（discard_from_hand から discard_trainer まで）
    trainer_discarded: dict[int, tuple[int, ...]] = {0: (), 1: ()}
    using_trainer: dict[int, int | None] = {0: None, 1: None}  # v0.25: 使っている最中のトレーナー（play_trainer から discard_trainer まで）
    howl_milled: dict[int, tuple[str, set[int]]] = {}  # v0.86: ［おたけび］で今トラッシュしたカード（プレイヤーごと。power_attach_from_discard で確かめる）
    outer_trainers: dict[int, list] = {}  # v0.58: 内側のカードを使っている間の外側のトレーナー（サイキックコントロール。プレイヤーごとに積む）
    attached_this_turn = 0  # この番の、手札からつける通常の操作（attach_energy）でつけた枚数（v0.6。v0.59 からカツラの 2 枚を 2 と数える）
    blaine_turns: set[int] = set()  # v0.59: カツラの効果で 2 枚をいっしょにつけた番
    converted_units: dict[int, int] = {}  # v0.59: ［エネエネ］でエネルギーとしてついたカード → 出すエネルギーの個数（ログ energy_conversion）
    pending_conversion: dict[int, tuple[int, int]] = {}  # v0.59: ［エネエネ］できぜつし、まだエネルギーとしてついていないカード → (持ち主, きぜつしたポケモンの番号)
    power_attached_this_turn = 0  # この番の、特殊能力で手札からつけた数（power_attach_energy。v0.6）
    exclusive: dict[int, str] = {}  # 場のポケモンの番号 → ねむり・マヒ・こんらんのどれか（v0.8。かがくへんかガスがはたらいているかを見る）
    poisoned: dict[int, int] = {}  # 場のポケモンの番号 → どくで受けるダメージ（v0.34。特殊などく（どくどく）は 20）
    replaced: dict[int, str] = {}  # 特殊状態が置きかわる直前の、ねむり・マヒ・こんらん（v0.9。置きかえたワザの効果を受けた時点の状態）
    attack_window: dict | None = None  # 今の番のワザ（attack から番の終わりまで。v0.9）: 使ったプレイヤー・ポケモン・ワザ・受けるかの判定
    expect: tuple | None = None  # 直前の evade_check のすぐあとに続くはずの処理（場のポケモンの番号, 要素, 受けるか。v0.9）
    previous: dict | None = None  # 1 つ前のイベント（v0.9。evade_check の直前のコイン）
    # v0.12: ログから組み立てた、今ある持続する効果（(場のポケモンの番号, 与えた番) → 種類・はたらく番・ワザ）
    alive: dict[tuple[int, int], dict] = {}
    # v0.12: 直前のきぜつで「ふしちょう」を使えた・使えなかったカード（答えを待つもの）と、その答えのあとの状態
    rebirth_pending: list[dict] = []
    rebirth_answered: dict | None = None  # 直前の答え（宣言なら、すぐあとに return_to_hand が続くはず）
    batch_answered = False  # このきぜつの処理で答えがあった（そのあとにサイド・きぜつ・対戦の終わりはないはず）
    destiny_knocked: set[int] = set()  # v0.31: 「みちづれ」できぜつする相手の対戦ポケモン（HP 未満できぜつしてよい）
    shuffle_due: dict | None = None  # v0.32: 直前の bench_from_deck・bench_from_deck_none（すぐあとに同じプレイヤーの shuffle が続くはず）
    static_attaches: set[int] = set()  # v0.85: せいでんきのつけるログ（続けてつけるあいだは山札を切らない）
    discard_entered: dict[int, int] = {}  # v0.51: トラッシュからベンチに出したポケモンの番号 → 出した番（状態の場に出た番と同じはず）
    revive_then_counters: tuple | None = None  # v0.71: ポケモンジム第1弾の元気のかけらで出したポケモン（番号・トレーナーのカード・番）。すぐあとにカウンターをのせる
    # v0.38: 直前の、山札を切らずにもどした return_in_play_to_deck（キョウのポッポの「でんれい」。かわりの対戦ポケモンを出してから山札をさがし、その
    # すぐあとに切る。もどしたあとに切らない）
    search_due: dict | None = None
    # v0.52: つれさる（自分と相手を山札にもどす）。もどした return_in_play_to_deck の並び（自分 → 相手）。そのあと（もう一方の受けるかの判定・もどす処理・持続する
    # 効果を消すログのあと）に、同じ順番で同じワザの shuffle が続くはず
    both_due: list | None = None
    both_shuffling = False
    # v0.36: p.309 の手順 4 のコイン（すなかけ・えんまくなど）。ワザの宣言（attack）のときにはたらいている効果（場のポケモンの番号, 与えた番, 1回で消えるか）が
    # あれば、宣言のすぐあとに coin_flip（source attack_check）→ attack_check が続くはず。「うら」なら、そのあと（1回で消える効果は消したログのあと）に
    # attack_failed（reason attack_check）が続き、ワザの要素はない
    check_due: tuple | None = None
    check_failed: dict | None = None
    used_due: tuple | None = None
    # v0.42: 直前の宣言の特殊能力（PowerKey の文字列）。手札をトラッシュした・相手のポケモンのカウンターをとりのぞいたあとに続くはずの引く処理
    # （プレイヤー, 枚数の上限, 番, 前のログ）。特殊能力の処理（のろい）で HP 以上になったポケモン（すぐあとに timing power のきぜつ）。
    # 「ぼうぎょかふん」の「おもて」でこんらんにする相手（すぐあとに、その特殊能力のこんらん）
    declared_key: str | None = None
    draw_due: tuple | None = None
    power_ko_due: int | None = None
    confusion_due: tuple | None = None
    # v0.43: 場に出たときの特殊能力の使う機会（(番, 場のポケモンの番号, 特殊能力の PowerKey の文字列)。進化のすぐあと（進化の手順のログのあと）に、答え（pokemon_power
    # の entry・entry_power_declined）が 1 つ続くはず）。くさいかふん・えんかくさいみんのコインのあとに置きかえたねむり・マヒ・こんらん（すぐあとにその特殊状態）。
    # 1 回の宣言で何枚もつけかえる特殊能力（ようぶんきゅうしゅう・エナジーチャージ）の今の宣言（番, プレイヤー, ポケモン, 特殊能力, つけかえた枚数）
    entry_due: dict[int, tuple] = {}  # v0.86: 答えを待つ場に出たときの特殊能力の使う機会（場のポケモンの番号 → (番, PowerKey)。同じ時点のほかの反応のあとに答えることがある）
    condition_due: tuple | None = None
    moving: tuple | None = None
    # v0.46: 各プレイヤーのバトル場のポケモンの番号（常にはたらく特殊能力の場所の条件を確かめる。場をはなれたら in_play にない）。
    # サイコエクスチェンジ（手札を山札にもどしたあと、切ってから引く）の引く処理（プレイヤー, 枚数の上限, 番）
    active_of: dict[int, int | None] = {0: None, 1: None}
    exchange_due: tuple | None = None
    # v0.47: ログから組み立てた、期限のあるトレーナーの使用の禁止（(禁止されたプレイヤー, 消える番) → 与えたログ）。みらいよちの見たカード（すぐあとに、その並べかえ
    # arrange_deck_top が続くはず）
    trainer_locks_log: dict[tuple, dict] = {}  # v0.56: (使えなくなるプレイヤー, 消える番, 出どころ)
    trainer_effects_log: dict[tuple[int, int], dict] = {}  # v0.56: (使ったプレイヤー, トレーナーのカード) → 与えたログ
    stadium_zone: tuple[int, int] | None = None  # v0.57: 場のスタジアム（カードの uid, 持ち主）。stadium_placed から stadium_discarded まで
    tools_on: dict[int, list[int]] = {}  # v0.81: ログから組み立てた、場のポケモンについているポケモンのどうぐ（番号 → カード。attach_trainer から discard_attached_trainer・きぜつまで）
    # v0.63: ログから組み立てた、おもてのサイドのカード（prizes_revealed で加え、サイドをはなれたら除く）と、一時的に置いておくカード
    # （(種類, 持ち主, トレーナーのカード) → カード・もどす番）
    face_up_log: set[int] = set()
    set_aside_log: dict[tuple, dict] = {}

    def trainer_user(card) -> int | None:
        """v0.57: 使っている最中のトレーナー ``card`` を使っているプレイヤー（錯乱ジムで相手が借りて使っていれば借りたプレイヤー。ほかは持ち主）。"""
        return next((p_index for p_index in (0, 1) if using_trainer.get(p_index) == card), owner.get(card))

    def bench_limit_now() -> int:
        """v0.57: ログから組み立てた場のスタジアム（せまいジムなら上限 4）のベンチの上限。"""
        effect = None if stadium_zone is None else _trainer_effect_of(state, stadium_zone[0])
        return effect.bench_limit if getattr(effect, "bench_limit", None) is not None else state.rules.max_bench

    arrange_due: dict | None = None
    looked_due: dict | None = None  # v0.55: カスミのいかりで見たカード（look_at_deck_top）。手札に加える・トラッシュするカードはその中から
    # v0.48: ログから組み立てた、特殊能力で色を変えた記録（場のポケモンの番号 → 色・番・使ったときのいちばん上のカード・使ってからベンチにもどったか）。
    # ログから組み立てた今の番（最後の turn_start の番）
    shifts: dict[int, dict] = {}
    current_turn = 0
    # v0.49: ログから組み立てた、「ばける」でのせたカード（場のポケモンの番号 → カードの uid）
    disguised: dict[int, int] = {}
    # v0.60: ログから組み立てた、はたらいている「まきちらせ!ベトベトガス」（使ったトレーナーのカード → 消える番）。v0.59 から特殊能力を消すが、「とうめい」・はんげきの
    # 確かめはかがくへんかガスしか見ていなかった（v0.59 の対戦では起こらなかった）
    goop_gases: dict[int, int] = {}

    def power_defs(pid: int) -> list[tuple[object, int, object]]:
        """v0.49: ログから組み立てた今の場の、ポケモン ``pid`` が今持つ特殊能力（``effects.powers_of`` と同じ求め方）: [(印刷したカードの定義, 位置, 特殊能力)]。
        「ばける」でのせたカードがあれば、そのカードの特殊能力（先）といちばん上のカードの特殊能力。［へんしん］で写したカードの特殊能力は持たない（TF1）。"""
        definitions = ([state.in_play_def(disguised[pid])] if pid in disguised else []) + [state.in_play_def(top[pid])]
        return [(definition, index, power) for definition in definitions for index, power in enumerate(definition.powers)]

    def transform_target(pid: int) -> int | None:
        """v0.49: ログから組み立てた今の場で、ポケモン ``pid`` の［へんしん］がはたらいていれば、同じカードとしてあつかう相手の対戦ポケモンの番号（バトル場にいて、
        ねむり・マヒ・こんらんでなく、かがくへんかガスに消されていない。``effects.transform_defender`` と同じ求め方）。"""
        if pid not in in_play or pid in disguised or not is_active(pid) or pid in exclusive:
            return None
        definition = state.in_play_def(top[pid])
        for power in definition.powers:
            if isinstance(state.effects.power_effect(definition.id, power), TransformIntoDefender):
                if [g for _, g in working_gases() if g.suppresses(power)]:
                    return None
                target = active_of.get(1 - pokemon_owner.get(pid))
                return target if target in in_play else None  # 相手のバトル場が空いている（きぜつのあと、出す前・対戦の終わり）なら、はたらく相手がいない
        return None

    def form_def(pid: int):
        """v0.49: ログから組み立てた、ポケモン ``pid`` の今の姿のカードの定義（「ばける」でのせたカード・［へんしん］の相手の対戦ポケモンのカード・いちばん上のカード）。"""
        if pid in disguised:
            return state.in_play_def(disguised[pid])
        target = transform_target(pid)
        if target is not None and target in top:
            return state.in_play_def(top[target])
        return state.in_play_def(top[pid])

    def entry_opportunity(uid: int, *, from_hand: bool, on_bench: bool = True) -> str | None:
        """v0.43: カード ``uid`` を重ねた進化（手札から ``from_hand``）で、場に出たときの特殊能力を使う機会があるか（その特殊能力の PowerKey の文字列。経路が
        合わない（「手札から」の特殊能力を山札から重ねた）・ログから組み立てた今の場ではたらいている「かがくへんかガス」に消されているなら None）。"""
        definition = state.in_play_def(uid)
        for index, power in enumerate(definition.powers):
            effect = state.effects.power_effect(definition.id, power)
            if isinstance(effect, EntryPower):
                if (effect.from_hand_only and not from_hand) or [pid for pid, gas in working_gases() if gas.suppresses(power)]:
                    return None
                if effect.bench_only and not on_bench:
                    return None  # v0.84: ［たすけだす］は、このポケモンがベンチにいるときだけ使える
                if effect.discard_to_hand_only and tower_in_play():
                    return None  # v0.74: ポケモンタワーで効果が消える（使う機会を出さない）
                return f"{definition.id}@power{index}"
        return None

    def tower_in_play() -> bool:
        """v0.74: ログから組み立てた今の場のスタジアムが、ポケモンタワー（トラッシュから手札に加える効果を消す）か。"""
        return stadium_zone is not None and isinstance(_trainer_effect_of(state, stadium_zone[0]), DiscardToHandSuppressionStadium)

    def working_gases() -> list[tuple[int, SuppressOtherPowers]]:
        """ログから組み立てた今の場で、はたらいている「ほかの特殊能力を消す」特殊能力（v0.8。かがくへんかガス）。"""
        found = []
        for pid in sorted(in_play):
            for definition, _, power in power_defs(pid):  # v0.49: 今持つ特殊能力（「ばける」でのせたカードを含む）
                effect = state.effects.power_effect(definition.id, power)
                if isinstance(effect, SuppressOtherPowers) and pid not in exclusive:
                    found.append((pid, effect))
        return found

    def evasion(pid: int, *, blocked: str | None = None) -> tuple[str | None, str | None]:
        """ログから組み立てた今の場の、ポケモン ``pid`` の「とうめい」（v0.9）: (持っている特殊能力の PowerKey の文字列, はたらいて
        いない理由)。持っていなければ (None, None)。``blocked`` はその時点のねむり・マヒ・こんらん（置きかわる直前の値を渡すため）。"""
        for definition, index, power in power_defs(pid):  # v0.49
            effect = state.effects.power_effect(definition.id, power)
            if isinstance(effect, AttackImmunityOnHeads):
                key = f"{definition.id}@power{index}"
                condition = blocked if blocked is not None else exclusive.get(pid)
                if condition is not None:
                    return key, f"{condition} 状態"
                gases = [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(power)]
                if gases:
                    return key, f"かがくへんかガス（ポケモン {gases}）"
                if goop_gases:
                    return key, f"まきちらせ!ベトベトガス（{sorted(goop_gases)}）"
                return key, None
        return None, None

    def counter_power(pid: int) -> tuple[str | None, int | None, str | None]:
        """ログから組み立てた今の場の、ポケモン ``pid`` の「はんげき」（v0.10）・「わるいねぞう」（v0.17b）: (持っている特殊能力の PowerKey の
        文字列, 与える量, はたらいていない理由)。持っていなければ (None, None, None)。ねむり・マヒ・こんらんは、その時点（ダメージを受けるとき）
        の値で、はたらくかは実装の ``works_with`` で決める（はんげきはどれでもないとき、わるいねぞうはねむりのときだけ）。"""
        for definition, index, power in power_defs(pid):  # v0.49
            effect = state.effects.power_effect(definition.id, power)
            if isinstance(effect, CounterattackDamage):
                key = f"{definition.id}@power{index}"
                if not effect.works_with(exclusive.get(pid)):
                    return key, effect.amount, f"{exclusive.get(pid) or '特殊状態なし'}（ねむり・マヒ・こんらん）の状態"
                gases = [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(power)]
                if gases:
                    return key, effect.amount, f"かがくへんかガス（ポケモン {gases}）"
                if goop_gases:
                    return key, effect.amount, f"まきちらせ!ベトベトガス（{sorted(goop_gases)}）"
                return key, effect.amount, None
        return None, None, None

    def guts_power(pid: int) -> tuple[str | None, PreventKnockOutOnHeads | None, object | None]:
        """ログから組み立てた今の場の、ポケモン ``pid`` の「こんじょう」（v0.11）: (持っている特殊能力の PowerKey の文字列, 実装,
        特殊能力の定義)。持っていなければ (None, None, None)。"""
        for definition, index, power in power_defs(pid):  # v0.49
            effect = state.effects.power_effect(definition.id, power)
            if isinstance(effect, PreventKnockOutOnHeads):
                return f"{definition.id}@power{index}", effect, power
        return None, None, None

    def rebirth_power(uid: int) -> tuple[str | None, object | None]:
        """カード ``uid`` の「ふしちょう」（v0.12。``ReturnToHandOnKnockOut``）: (PowerKey の文字列, 特殊能力の定義)。なければ (None, None)。"""
        definition = state.in_play_def(uid)
        for index, power in enumerate(definition.powers):
            if isinstance(state.effects.power_effect(definition.id, power), ReturnToHandOnKnockOut):
                return f"{definition.id}@power{index}", power
        return None, None

    def active_retaliation(pid: int, turn: int) -> dict | None:
        """ログから組み立てた、ポケモン ``pid`` の今の番 ``turn`` にはたらく「ほのおのかべ」（v0.12）・「こうらがえし」（v0.13）の効果。"""
        for (effect_pid, _), info in alive.items():
            if effect_pid == pid and info["kind"] in (*RETALIATION_KINDS.values(), RETALIATION_RECEIVED_SCALED_KIND) and info["active_turn"] == turn:
                return info
        return None

    def lasting_value(pid: int, kind: str, field: str):
        """v0.48: ログから組み立てた、ポケモン ``pid`` の期限のない効果（``kind``。テクスチャー1・2・きょだいか）の値（色・最大HP）。なければ None。"""
        values = [info[field] for (effect_pid, _), info in alive.items() if effect_pid == pid and info["kind"] == kind]
        if len(values) > 1:
            problems.append(f"ポケモン {pid} に同じ種類の期限のない効果（{kind}）が 2 つ以上ある（置きかえたはず）")
        return values[-1] if values else None

    def max_hp_now(pid: int) -> int:
        """v0.48: ログから組み立てた今の場の、ポケモン ``pid`` の今有効な最大HP（``effects.max_hp`` と同じ求め方を、ログから組み立てた値で）。「きょだいか」の効果
        （max_hp_set）があればその数、なければいちばん上のカードの HP に、はたらいている［ガスのからだ］（ついている「超」の基本エネルギーカードの枚数 × 10。ねむり・
        マヒ・こんらんでもはたらき、ログから組み立てたかがくへんかガスで消える）を足す。"""
        form = form_def(pid)  # v0.49: 今の姿のカードの HP
        fixed = lasting_value(pid, MaxHpSet.kind, "amount")
        bonus = 0
        for definition, _, power in power_defs(pid):
            effect = state.effects.power_effect(definition.id, power)
            if isinstance(effect, MaxHpPerAttachedEnergyCards) and not [g for _, g in working_gases() if g.suppresses(power)]:
                bonus += effect.per * sum(1 for uid in energy.get(pid, ())
                                          if state.printed_def(uid).is_basic_energy and state.printed_def(uid).provides is effect.energy_type)
        if stadium_zone is not None:
            hideout = _trainer_effect_of(state, stadium_zone[0])
            if isinstance(hideout, NamedMaxHpStadium) and form.name_ja.startswith(hideout.prefix):
                bonus += hideout.amount  # v0.81: ロケット団のアジト（今の姿の名前が「わるい」で始まるポケモン）
        if fixed is not None and bonus:
            problems.append(f"ポケモン {pid} の最大HPを、その数にする効果と大きくする特殊能力が同時に変えている（MH2。その状態にならないはず）")
        return fixed if fixed is not None else form.hp + bonus

    def hp_of(pid: int) -> int:
        """v0.48: ログから組み立てた今の場のポケモン ``pid`` の今有効な最大HP（場にいなければ 0）。"""
        return max_hp_now(pid) if pid in top and pid in in_play else 0

    def weakness_now(pid: int):
        """v0.48: ログから組み立てた、ポケモン ``pid`` の今有効な弱点の色（「テクスチャー1」の効果があればその色）。"""
        color = lasting_value(pid, WeaknessChange.kind, "color")
        return EnergyType(color) if color is not None else form_def(pid).weakness  # v0.49: 今の姿

    def resistance_now(pid: int):
        """v0.48: ログから組み立てた、ポケモン ``pid`` の今有効な抵抗力の色（「テクスチャー2」の効果があればその色。数は変えない）。"""
        color = lasting_value(pid, ResistanceChange.kind, "color")
        return EnergyType(color) if color is not None else form_def(pid).resistance  # v0.49: 今の姿

    def type_readings_now(pid: int) -> tuple:
        """v0.48: ログから組み立てた、ポケモン ``pid`` の色の読み方（``effects.type_readings`` と同じ求め方。［へんしょく］の記録が、使った番のうちで、ベンチに
        もどっておらず、いちばん上のカードが同じで、この力が消えていない（ねむり・マヒ・こんらん・かがくへんかガス）なら変えた色だけ。記録があって決まらなければ
        （VS1）変えた色と印刷の色の 2 つ）。"""
        printed = form_def(pid).pokemon_type  # v0.49: 今の姿のカードの色
        shift = shifts.get(pid)
        if shift is None:
            return (printed,)
        works = False
        for definition, _, power in power_defs(pid):
            if isinstance(state.effects.power_effect(definition.id, power), ShiftColor):
                works = pid not in exclusive and not [g for _, g in working_gases() if g.suppresses(power)]
        determined = shift["turn"] == current_turn and not shift["returned"] and shift["source_card"] == top[pid] and works
        if determined or shift["color"] is printed:
            return (shift["color"],)
        return (shift["color"], printed)

    def retaliation_damage_problems(e: dict, ret: dict) -> list[str]:
        """「ほのおのかべ」のダメージのログ（v0.12）: 基本となるダメージが効果の量で、弱点・抵抗力は R団のファイヤーのタイプと、受けた
        ポケモン（いちばん上のカード）の弱点・抵抗力で計算した（W15・W16。p.82「この10ダメージは、弱点・抵抗力の影響を受けます」）。
        v0.13 の「こうらがえし」も同じ（基本となるダメージは受けたダメージ。弱点・抵抗力はわるいカメールのタイプで計算する。S20〜S22。p.89）。"""
        found = []
        pid = e.get("pokemon_id")
        steps = e.get("steps") or ()
        if not steps or tuple(steps[0]) != ("1 基本となる計算", ret["amount"]):
            found.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」のダメージの基本となるダメージ {steps[:1]} が {ret['amount']} ではない（W14）")
        if pid in top and ret["pokemon_id"] in top:
            # v0.48: 受けたポケモンの今有効な弱点・抵抗力（テクスチャー1・2）と、効果を持つポケモンの色の読み方（読み方で結果が変わる場合はエンジンが止める）
            readings = type_readings_now(ret["pokemon_id"])
            weakness, resistance = weakness_now(pid), resistance_now(pid)
            if e["weakness"] not in {weakness is not None and weakness is color for color in readings}:
                found.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」のダメージの弱点 {e['weakness']} が、タイプと弱点に合わない（W15）")
            if e["resistance"] not in {resistance is not None and resistance is color for color in readings}:
                found.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」のダメージの抵抗力 {e['resistance']} が、タイプと抵抗力に合わない（W16）")
        return found

    def zero_damage_below_problems(e: dict) -> list[str]:
        """ワザのダメージのログ（v0.45）の p.321 の 8 段階の「決まった数より小さければ 0 にする」効果（イワークの「かたくなる」）の記録。ダメージを受けた
        ポケモンが、今の番にはたらく ``zero_damage_below`` の効果（ログから組み立てた）を持つときだけ記録があり、しきい値は効果を与えたワザの登録の値、
        受けたダメージは 0 かしきい値以上。"""
        pid = e["pokemon_id"] if "pokemon_id" in e else ids.get(e["pokemon"])
        expected = []
        for (effect_pid, _), info in alive.items():
            if effect_pid == pid and info["kind"] == "zero_damage_below" and info["active_turn"] == e["turn"]:
                card_id, index = info["effect"].split("#")
                expected.append((8, info["source_card"], state.effects.attack_entry(card_id, int(index)).effect.threshold_terms()[1]))
        recorded = [tuple(m) for m in e.get("damage_zero_below", ())]
        ended_early = e["amount"] == 0 and not any(str(step[0]).startswith("8 ") for step in (e.get("steps") or ()))
        if expected and not recorded and ended_early:
            return []  # p.321: 途中の段階で 0 以下になって計算を終えた（8 段階まで進まない）
        if recorded != expected:
            return [f"{e['turn']} 番のポケモン {pid} へのダメージの 8 段階の記録 {recorded} が、はたらいている「かたくなる」の効果 {expected} と違う"]
        if recorded and 0 < e["amount"] < recorded[0][2]:
            return [f"{e['turn']} 番のポケモン {pid} へのダメージ {e['amount']} が、0 でもしきい値 {recorded[0][2]} 以上でもない"]
        return []

    def attack_damage_set_problems(e: dict) -> list[str]:
        """ワザのダメージのログ（v0.27）の p.321 の 2 段階の記録。ワザを使ったポケモンが持つ効果（ログから組み立てた）から、そのダメージにはたらく
        2 段階の変更効果を求めて、記録と照らす:

        - 「つるぎのまい」（v0.27。「その数にする」）・「きあいだめ」（v0.35。「数をかける」）: 効果の登録の ``next_turn_terms`` の位置のワザ（名前では
          探さない）のダメージで、はたらく番が今の番。自分へのダメージ（``target`` が ``self``）は、登録が自分へのダメージにも当てはめるときだけ
        - 「なきつく」（v0.34）: 受けたポケモン（ワザを使ったポケモン）が、効果の発生源のカードの対戦ポケモンに与えるダメージ
        はたらく効果がなければ 2 段階の記録はない。あれば、1 段階のすぐあとに効果の数だけ 2 段階の記録が並び、計算した順番に当てはめた数が記録の数と同じ。
        「その数にする」は ``damage_set``、「数をかける」は ``damage_multiplied``、加える数は ``modifiers`` に入る。2 つ以上なら、順番の決定で選んだ順番
        （``step_orders``。v0.35）が記録の並びと同じで、決定がなければ集めた順番（効果の登録 → なきつく）。"""
        target = e.get("target")
        expected: list[tuple[str, str, int, int]] = []  # (名前, 計算, 数, 発生源のカード)。集めた順番
        for (effect_pid, _), info in alive.items():
            if effect_pid != attack_window["pokemon_id"] or info["kind"] not in NEXT_TURN_DAMAGE_KINDS.values() or info["active_turn"] != e["turn"]:
                continue
            card_id, index = info["effect"].split("#")
            entry = state.effects.attack_entry(card_id, int(index))
            terms = entry.effect.next_turn_terms()
            operation, includes_self = (terms[2], terms[3]) if len(terms) == 4 else ("set", False)
            if attack_window["effect"] == f"{card_id}#{terms[0]}" and (target != "self" or includes_self):
                expected.append((entry.name_ja, operation, terms[1], info["source_card"]))
        for (effect_pid, _), info in alive.items():
            # v0.34: 「なきつく」を受けたポケモン（ワザを使ったポケモン）が、なきつくを使ったポケモン（効果の発生源のカード）の対戦ポケモンにワザの
            # ダメージを与えるときは、p.321 の 2 段階で効果の量をへらす
            # v0.76: 「なきごえ」（期限が次の相手の番の終わり。種類 reduced_damage_to_source_next_turn）も同じ 2 段階
            if (effect_pid == attack_window["pokemon_id"] and info["kind"] in REDUCED_DAMAGE_KINDS and info["active_turn"] == e["turn"]
                    and target is None and e["pokemon"] == info["source_card"]):
                card_id, index = info["effect"].split("#")
                amount = state.effects.attack_entry(card_id, int(index)).effect.amount
                expected.append((f"{state.printed_def(info['source_card']).name_ja}（{info['kind']}）", "add", -amount, info["source_card"]))
        steps = [tuple(step) for step in (e.get("steps") or ())]
        # v0.46: 常にはたらく特殊能力の 2 段階の記録（くつろぐかおり・きょうぼう）は continuous_damage_problems が確かめる（ここでは並びの位置だけに数える）
        step2_all = [step for step in steps if str(step[0]).startswith("2 ")]
        step2 = [step for step in step2_all if not _v046_rank(str(step[0])[2:])]
        damage_set = tuple(tuple(m) for m in e.get("damage_set", ()))
        multiplied = tuple(tuple(m) for m in e.get("damage_multiplied", ()) if m[0] == 2)  # v0.75: 8 段階（もろばバサミ）は continuous_damage_problems
        orders = {step: tuple(labels) for step, labels in e.get("step_orders", ())}
        orders2 = [label for label in orders.get(2, ()) if not _v046_rank(label)]
        where = f"{e['turn']} 番のワザ {attack_window['effect']} のダメージの 2 段階 {step2}"
        if not expected:
            if step2 or damage_set or multiplied or orders2:
                return [f"{where}: はたらいている効果のない 2 段階の記録・{damage_set}・{multiplied}・{orders} がある"]
            return []
        by_label = {label: (operation, amount, source) for label, operation, amount, source in expected}
        applied = [str(step[0])[2:] for step in step2]
        if len(by_label) != len(expected) or sorted(applied) != sorted(by_label) or steps[1:1 + len(step2_all)] != step2_all:
            return [f"{where} が、はたらく効果 {[x[0] for x in expected]} と合わない"]
        value = steps[0][1]
        for label, recorded in ((str(step[0])[2:], step[1]) for step in step2_all):
            if _v046_rank(label):
                value = recorded  # v0.46: 常にはたらく特殊能力のあとの数（continuous_damage_problems が確かめる）
                continue
            operation, amount, _ = by_label[label]
            value = amount if operation == "set" else value * amount if operation == "multiply" else value + amount
            if recorded != value:
                return [f"{where} の「{label}」のあとの数 {recorded} が、計算した {value} と違う"]
        if damage_set != tuple((2, by_label[label][2], by_label[label][1]) for label in applied if by_label[label][0] == "set") \
                or multiplied != tuple((2, by_label[label][2], by_label[label][1]) for label in applied if by_label[label][0] == "multiply") \
                or any((2, by_label[label][2], by_label[label][1]) not in [tuple(m) for m in e.get("modifiers", ())]
                       for label in applied if by_label[label][0] == "add"):
            return [f"{where} の damage_set {damage_set}・damage_multiplied {multiplied}・modifiers が、計算した順番の効果と合わない"]
        if len(expected) > 1:
            if 2 in orders and orders2 != applied:
                return [f"{where} の並びが、順番の決定で選んだ順番 {orders[2]} と違う"]
            if 2 not in orders and applied != [x[0] for x in expected]:
                return [f"{where} が、順番の決定がないのに集めた順番 {[x[0] for x in expected]} でない"]
        elif 2 in orders and len(step2_all) < 2:
            # v0.46: 2 段階の効果が 1 つでも、常にはたらく特殊能力（くつろぐかおり）と重なれば順番の決定がある
            return [f"{where}: 2 段階の効果が 1 つなのに順番の決定の記録 {orders} がある"]
        return []

    def is_active(pid: int | None) -> bool:
        """ログから組み立てた今の場で、ポケモン ``pid`` がバトル場にいるか（v0.46）。"""
        return pid is not None and pid in in_play and active_of.get(pokemon_owner.get(pid)) == pid

    def working_continuous(pid: int | None, types, *, attack_status: frozenset | None = None) -> list[tuple[str, object, object]]:
        """ログから組み立てた今の場で、ポケモン ``pid`` のいちばん上のカードの、はたらいている常にはたらく特殊能力（``types`` の型。v0.46）:
        [(PowerKey の文字列, 実装, 特殊能力の定義)]。場所（バトル場・ベンチ）・特殊状態（説明ごと。［くつろぐかおり］はワザの宣言の時点 ``attack_status``）・
        はたらいているかがくへんかガスで決める（エンジンの ``effects.continuous_powers`` と別に、ログから求める）。"""
        if pid is None or pid not in in_play:
            return []
        found = []
        for definition, index, power in power_defs(pid):  # v0.49: 今持つ特殊能力
            effect = state.effects.power_effect(definition.id, power)
            if not isinstance(effect, types):
                continue
            if (effect.location == CONTINUOUS_ACTIVE and not is_active(pid)) or (effect.location == CONTINUOUS_BENCH and is_active(pid)):
                continue
            if effect.requires_confusion:
                blocked = exclusive.get(pid) != "confusion"
            elif not effect.blocked_by_status:
                blocked = False
            elif effect.status_at_attack and attack_status is not None:
                blocked = pid in attack_status
            else:
                blocked = pid in exclusive
            if blocked or [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(power)]:
                continue
            found.append((f"{definition.id}@power{index}", effect, power))
        return found

    def continuous_expected(attacker_pid: int | None, receiver_pid: int | None, attack_status: frozenset | None) -> list[tuple]:
        """ワザのダメージ（``attacker_pid`` → ``receiver_pid``）に当てはまる、常にはたらく特殊能力と「リフレクター」の変更効果（v0.46）:
        [(段階, 名前, 計算, しきい値, 数, 発生源のカード)]。ログから組み立てた場（場所・特殊状態・かがくへんかガス・持続する効果）で求める。"""
        expected = []
        if attacker_pid not in in_play or receiver_pid not in in_play:
            return expected
        for (effect_pid, _), info in alive.items():
            # v0.84: 「パルスガード」（8 段階の、決まった数以上なら 0。リフレクターの前に集める）。しきい値は効果を与えたワザの登録（threshold_terms）
            if effect_pid == receiver_pid and info["kind"] == ZeroDamageAtLeast.kind and info["active_turn"] == turn_now:
                entry = state.effects.attack_entry(*_attack_key(info["effect"]))
                threshold = entry.effect.threshold_terms()[1]
                expected.append((8, f"{state.printed_def(info['source_card']).name_ja}（{ZeroDamageAtLeast.kind}）", ZERO_IF_AT_LEAST, None, threshold,
                                 info["source_card"]))
        for (effect_pid, _), info in alive.items():
            if effect_pid == receiver_pid and info["kind"] == HalvedDamage.kind and info["active_turn"] == turn_now:
                expected.append((8, f"{state.printed_def(info['source_card']).name_ja}（{HalvedDamage.kind}）", HALVE_DOWN, None, 2, info["source_card"]))
        for (effect_pid, _), info in alive.items():
            # v0.75: 「もろばバサミ」（8 段階の 2 倍。リフレクターのあとに集める）
            if effect_pid == receiver_pid and info["kind"] == DoubledDamage.kind and info["active_turn"] == turn_now:
                expected.append((8, f"{state.printed_def(info['source_card']).name_ja}（{DoubledDamage.kind}）", MULTIPLY, None, 2, info["source_card"]))
        attacker_active = is_active(attacker_pid)
        for pid in sorted(in_play, key=lambda q: (pokemon_owner.get(q), not is_active(q), q)):
            for key, effect, power in working_continuous(pid, ContinuousPower, attack_status=attack_status):
                label, source = f"{state.definitions[key.partition('@')[0]].name_ja}［{power.name_ja}］", top[pid]  # v0.49: 特殊能力を印刷したカードの名前
                if isinstance(effect, ZeroLargeDamageReceived) and pid == receiver_pid:
                    expected.append((8, label, ZERO_IF_AT_LEAST, None, effect.threshold, source))
                elif isinstance(effect, CapDamageFromBasic) and pid == receiver_pid and form_def(attacker_pid).is_basic_pokemon:
                    expected.append((8, label, SET_IF_AT_LEAST, effect.threshold, effect.amount, source))
                elif isinstance(effect, HalveActiveAttackDamage) and attacker_active:
                    expected.append((2 if pid == attacker_pid else 8 if pid == receiver_pid else 6, label, HALVE_UP, None, 2, source))
                elif isinstance(effect, BonusDamageWhileConfused) and pid == attacker_pid:
                    expected.append((2, label, ADD, None, effect.amount, source))
                elif isinstance(effect, HalveDamageReceived) and pid == receiver_pid:
                    expected.append((8, label, HALVE_DOWN, None, 2, source))  # v0.47: ［カブトアーマー］
        return expected

    def continuous_damage_problems(e: dict) -> list[str]:
        """ワザのダメージのログ（v0.46）の、常にはたらく特殊能力（なぞのかべ・ふしぎなバリアー・くつろぐかおり・きょうぼう）と「リフレクター」の記録。ログから組み立てた
        場で当てはまる効果（``continuous_expected``）が、その段階の記録に 1 回ずつあり（計算が 2 段階で終わったら 3 段階からあとはない）、当てはまらない効果の記録が
        なく、記録の数が直前の数から計算した数（しきい値・その数・半分の丸め・加える数）で、``damage_zero_at_least``・``damage_set_if_at_least``・``damage_halved``・
        ``modifiers`` が記録と合う。計算の順番の決定のない段階では、v0.45 までの効果 → リフレクター → 常にはたらく特殊能力の順。決定があれば選んだ順番。"""
        if e.get("retaliation"):
            ret = attack_window.get("ret")
            attacker_pid = ret["pokemon_id"] if ret is not None else None
        else:
            attacker_pid = attack_window["pokemon_id"]
        receiver_pid = e["pokemon_id"] if "pokemon_id" in e else ids.get(e["pokemon"])
        where = f"{e['turn']} 番のポケモン {attacker_pid} → {receiver_pid} のワザのダメージ"
        steps = [tuple(step) for step in (e.get("steps") or ())]
        early = [step for step in steps if str(step[0])[:2] in ("1 ", "2 ")]
        ended_early = bool(early) and early[-1][1] <= 0 and len(early) == len(steps)
        expected = [x for x in continuous_expected(attacker_pid, receiver_pid, attack_window.get("status_at_attack"))
                    if not ended_early or x[0] <= 2]
        by_label = {f"{x[0]} {x[1]}": x for x in expected}
        recorded = [(i, step) for i, step in enumerate(steps) if _v046_rank(str(step[0]).partition(" ")[2])]
        found = []
        if len(by_label) != len(expected) or sorted(str(step[0]) for _, step in recorded) != sorted(by_label):
            return [f"{where} の記録 {[step[0] for _, step in recorded]} が、当てはまる効果 {sorted(by_label)} と合わない"]
        for i, step in recorded:
            stage, _, operation, threshold, amount, _ = by_label[str(step[0])]
            before = steps[i - 1][1]
            per = state.rules.damage_per_counter
            value = (0 if before >= amount else before) if operation == ZERO_IF_AT_LEAST else \
                (amount if before >= threshold else before) if operation == SET_IF_AT_LEAST else \
                before if before <= 0 and operation in (HALVE_UP, HALVE_DOWN) else \
                ((before // per + 1) // 2 * per) if operation == HALVE_UP else (before // per // 2 * per) if operation == HALVE_DOWN else \
                before * amount if operation == MULTIPLY else before + amount
            if step[1] != value:
                found.append(f"{where} の「{step[0]}」のあとの数 {step[1]} が、{before} から計算した {value} と違う")
        applied = [by_label[str(step[0])] for _, step in recorded]
        zero = sorted((x[0], x[5], x[4]) for x in applied if x[2] == ZERO_IF_AT_LEAST)
        capped = sorted((x[0], x[5], x[3], x[4]) for x in applied if x[2] == SET_IF_AT_LEAST)
        halved = sorted((x[0], x[5], "up" if x[2] == HALVE_UP else "down") for x in applied if x[2] in (HALVE_UP, HALVE_DOWN))
        if sorted(tuple(m) for m in e.get("damage_zero_at_least", ())) != zero \
                or sorted(tuple(m) for m in e.get("damage_set_if_at_least", ())) != capped \
                or sorted(tuple(m) for m in e.get("damage_halved", ())) != halved \
                or sorted(tuple(m) for m in e.get("damage_multiplied", ()) if m[0] != 2) != sorted((x[0], x[5], x[4]) for x in applied if x[2] == MULTIPLY) \
                or any((x[0], x[5], x[4]) not in [tuple(m) for m in e.get("modifiers", ())] for x in applied if x[2] == ADD):
            found.append(f"{where} の damage_zero_at_least・damage_set_if_at_least・damage_halved・modifiers が、記録した効果 {[x[1] for x in applied]} と合わない")
        orders = {stage: tuple(labels) for stage, labels in e.get("step_orders", ())}
        for stage in sorted({int(str(step[0]).split(" ")[0]) for step in steps if str(step[0])[0].isdigit()}):
            at = [str(step[0]).partition(" ")[2] for step in steps if str(step[0]).split(" ")[0] == str(stage)]
            if stage in orders:
                if list(orders[stage]) != at or len(at) < 2:
                    found.append(f"{where} の {stage} 段階の並び {at} が、順番の決定で選んだ順番 {orders[stage]} と違う")
            elif [_v046_rank(label) for label in at] != sorted(_v046_rank(label) for label in at):
                found.append(f"{where} の {stage} 段階の並び {at} が、順番の決定がないのに集めた順番（v0.45 までの効果 → リフレクター → 常にはたらく特殊能力）でない")
        return found

    def received_power_expected(receiver_pid: int, source_pid: int | None, amount: int) -> tuple[int, tuple]:
        """特殊能力のダメージ（はんげき・わるいねぞう・こっそりかみつく。v0.46）を ``receiver_pid`` が ``source_pid`` から受けるときの、受けるダメージ全体を書く
        常にはたらく特殊能力（なぞのかべ・ふしぎなバリアー）を当てはめた数と記録（(発生源のカード, 計算, しきい値, 数)）。ログから組み立てた場で求める。"""
        applied = []
        for _, effect, _ in working_continuous(receiver_pid, (ZeroLargeDamageReceived, CapDamageFromBasic, HalveDamageReceived)):
            if isinstance(effect, HalveDamageReceived):
                # v0.47: ［カブトアーマー］（半分。切りすて）
                applied.append((top[receiver_pid], HALVE_DOWN, None, 2))
                amount = amount if amount <= 0 else amount // state.rules.damage_per_counter // 2 * state.rules.damage_per_counter
            elif isinstance(effect, ZeroLargeDamageReceived):
                applied.append((top[receiver_pid], ZERO_IF_AT_LEAST, None, effect.threshold))
                amount = 0 if amount >= effect.threshold else amount
            elif source_pid in in_play and form_def(source_pid).is_basic_pokemon:
                applied.append((top[receiver_pid], SET_IF_AT_LEAST, effect.threshold, effect.amount))
                amount = effect.amount if amount >= effect.threshold else amount
        return amount, tuple(applied)

    def received_power_problems(e: dict, receiver_pid: int, source_pid: int | None, registered: int) -> list[str]:
        """特殊能力のダメージのログ（counterattack・power_damage）の量と、受けるダメージを変える特殊能力の記録（v0.46。``amount_before``・``received_modifiers``。
        当てはめたときだけある）。"""
        expected, applied = received_power_expected(receiver_pid, source_pid, registered)
        recorded = tuple(tuple(m) for m in e.get("received_modifiers", ()))
        if not applied and not recorded and "amount_before" not in e:
            # 当てはめる特殊能力がないときは v0.45 までと同じ確かめと文（登録の量）
            if e["amount"] == registered:
                return []
            if e["kind"] == "counterattack":
                return [f"{e['turn']} 番の「はんげき」の量 {e['amount']} が、登録の {registered} と違う"]
            return [f"{e['turn']} 番の power_damage（{e['power']} → ポケモン {receiver_pid}）が、場に出たときに相手の場のポケモンにダメージを与える特殊能力の処理と合わない"]
        if e["amount"] != expected or recorded != applied or (("amount_before" in e) != bool(applied)) \
                or (applied and e["amount_before"] != registered):
            return [f"{e['turn']} 番の {e['kind']}（→ ポケモン {receiver_pid}）の量 {e['amount']}・記録 {recorded} が、登録の {registered} に受けるポケモンの"
                    f"特殊能力 {applied} を当てはめた {expected} と合わない"]
        return []

    def source_of(e: dict) -> dict | None:
        """イベント ``e``（判定・ダメージ・はんげき）を起こしたワザ（v0.12）: 今の番のワザ（attack_window）か、その中の「ほのおのかべ」
        （attack_window["ret"]。ワザを使ったポケモンは R団のファイヤー）。どちらでもなければ None。"""
        if attack_window is None:
            return None
        keys = (e.get("effect"), e.get("attacker"), e.get("attacker_pokemon_id"))
        if keys == (attack_window["effect"], attack_window["player"], attack_window["pokemon_id"]):
            return attack_window
        if keys == (attack_window.get("copied"), attack_window["player"], attack_window["pokemon_id"]):
            # v0.50: 相手のワザを自分のワザとして使ったワザ（ゆびをふる・ちょうのうりょく）の判定の effect は、使ったワザ（copied。v0.44 の約束）。v0.49 までは、
            # まねたワザで「とうめい」のポケモンにダメージ・効果を与える対戦がなかった
            return attack_window
        ret = attack_window["ret"]
        if ret is not None and keys == (ret["effect"], ret["player"], ret["pokemon_id"]):
            return ret
        return None

    def received(e: dict, pid: int, element: str, *, blocked: str | None = None) -> None:
        """ワザの要素 ``element`` のダメージ・効果を、ポケモン ``pid`` が受けた（v0.9）。はたらいている「とうめい」があれば、その前に
        このワザでの判定があって「受ける」こと。"""
        if attack_window is None or pid not in in_play:
            return
        reception = attack_window["reception"]
        if e.get("retaliation"):
            # v0.12: 「ほのおのかべ」のダメージは R団のファイヤーのワザによるダメージ（「とうめい」の判定は、そのワザで 1 回）
            if attack_window["ret"] is None:
                return
            reception = attack_window["ret"]["reception"]
        if reception.get(pid) is False:
            problems.append(f"{e['turn']} 番のワザで「とうめい」により受けないと決まったポケモン {pid} が {element} を受けた（{e['kind']}）")
        elif pid not in reception:
            key, blocked_by = evasion(pid, blocked=blocked)
            if key is not None and blocked_by is None:
                problems.append(f"{e['turn']} 番のワザの {element} を、はたらいている「とうめい」のポケモン {pid} が判定（evade_check）なしで受けた")

    def window_damaged(window: dict) -> bool:
        """今のワザ（attack_window）に、すでにダメージの要素（damage・damage_prevented・ダメージの attack_evaded）があったか（v0.42）。"""
        return bool(window.get("any_damage"))

    face_down_pids: set[int] = set()  # v0.67: ログから組み立てた、うらのカードの場のポケモン

    def enter(uid: int) -> None:
        nonlocal next_id
        ids[uid] = next_id
        energy[next_id] = []
        in_play.add(next_id)
        pokemon_owner[next_id] = owner[uid]
        top[next_id] = uid
        next_id += 1

    def from_hand(e: dict, player: int, uid: int) -> None:
        """手札から出たカード（v0.6）。ログから組み立てた手札になければ報告する。"""
        if uid in hand[player]:
            hand[player].remove(uid)
        else:
            problems.append(f"{e['turn']} 番の {e['kind']} のカード {uid} が、ログから組み立てたプレイヤー {player} の手札にない")

    owner = {uid: card.owner for uid, card in state.cards.items()}
    turn_now = 0  # v0.46: 今処理しているイベントの番（continuous_expected が持続する効果のはたらく番を見る）
    declared = None  # 直前の特殊能力の宣言（番・プレイヤー・ポケモン）。移動のログはその直後に続く（v0.5）
    last_damage = None  # v0.65: 直前のログ damage（［ベンチガード］の確かめ）
    duel_winner = {}  # v0.66: カスミの勝負のカード → 直前のじゃんけん（duel_janken）で勝ったプレイヤー（あいこなら None）
    for e in log:
        kind = e["kind"]
        turn_now = e["turn"]
        if kind == "damage":
            last_damage = e
        if kind == "duel_janken":
            # v0.66: カスミの勝負のじゃんけん。使っている最中のそのカードで、両方の手と勝ったプレイヤー（あいこなら None）が手の組と合う
            from kyuura_engine.effects import JANKEN_HANDS, janken_winner
            result = janken_winner(*(JANKEN_HANDS.index(h) for h in e["hands"]))
            expected = None if result is None else (e["player"] if result == 0 else e["opponent"])
            if not isinstance(_trainer_effect_of(state, e["trainer_card"]), RockPaperScissorsRefreshHand) or e["winner"] != expected \
                    or e["opponent"] != 1 - e["player"]:
                problems.append(f"{e['turn']} 番のカスミの勝負のじゃんけん {e['hands']} の勝ち負け {e['winner']} が、手の組と合わない")
            duel_winner[e["trainer_card"]] = e["winner"]
        if kind == "trainer_effect_added" and e["effect_kind"] == "power_suppression":
            goop_gases[e["trainer_card"]] = e["expires_turn"]
        elif kind == "trainer_effect_removed" and e.get("effect_kind") == "power_suppression":
            goop_gases.pop(e.get("trainer_card"), None)
        prior = previous  # 1 つ前のイベント（v0.11。「こんじょう」の宣言・コイン・結果の順番）
        if prior is not None and prior["kind"] == "attack" and kind != "once_attack_recorded":
            # v0.44: 場に出てから 1 度しか使えないワザの宣言のすぐあとには、その記録（once_attack_recorded）がある
            once_entry = state.effects.attack_entry(_attack_card_id(state, prior), prior["attack_index"])
            if once_entry is not None and once_entry.effect.once_after_entering_play:
                problems.append(f"{prior['turn']} 番の 1 度だけ使えるワザの宣言（ポケモン {ids.get(prior['pokemon'])}）のすぐあとに、その記録がない（{kind}）")
        if both_due is not None:
            if kind == "shuffle" and e.get("effect") == both_due[0]["effect"] and e["player"] == both_due[0]["player"]:
                both_due.pop(0)
                both_shuffling = bool(both_due)
                if not both_due:
                    both_due = None
            elif not both_shuffling and (kind in ("coin_flip", "evade_check", "attack_evaded", "effect_prevented")
                                         or (kind == "persistent_effect_removed" and e["reason"] == "return_in_play_to_deck")
                                         or (kind == "return_in_play_to_deck" and e.get("effect") == both_due[0]["effect"])):
                pass
            else:
                problems.append(f"{both_due[0]['turn']} 番の {both_due[0]['effect']} で山札にもどしたあと、もどしたプレイヤー {[d['player'] for d in both_due]} の"
                                f"山札を切る処理（shuffle）がないまま {kind} になった")
                both_due, both_shuffling = None, False
        if search_due is not None:
            # v0.38: でんれい。もどしたあと、持続する効果を消したログ・同じワザのかわりの対戦ポケモンを出すログ（promote_active）のあと、同じワザの
            # 山札をさがすログ（reveal_from_deck・reveal_from_deck_none）が続き、そのすぐあとに山札を切る（途中で切らない）
            same = e.get("effect") == search_due["effect"] and e.get("player") == search_due["player"]
            if kind == "persistent_effect_removed" and e["reason"] == "return_in_play_to_deck" and e["pokemon_id"] == search_due["pokemon_id"]:
                pass
            elif kind == "promote_active" and same:
                pass
            elif kind in ("reveal_from_deck", "reveal_from_deck_none") and same:
                search_due, shuffle_due = None, e
            else:
                problems.append(f"{search_due['turn']} 番の {search_due['kind']} のあとに、同じワザの山札をさがす処理がないまま {kind} になった")
                search_due = None
        elif shuffle_due is not None and not (
            # v0.36: 山札にもどしたポケモン（return_in_play_to_deck）の持続する効果を消したログは、もどしたあと・山札を切る前
            shuffle_due["kind"] == "return_in_play_to_deck" and kind == "persistent_effect_removed" and e["reason"] == "return_in_play_to_deck"
            and e["pokemon_id"] == shuffle_due["pokemon_id"]
        ) and not (
            # v0.42: つきのちから。山札から重ねた進化（evolve）の手順（特殊状態・持続する効果・にげるの失敗の記録を消す）のあと、山札を切る
            shuffle_due["kind"] == "evolve" and kind in ("special_conditions_removed", "persistent_effect_removed", "retreat_failure_cleared")
            and e.get("reason") == "evolve" and e["pokemon_id"] == shuffle_due["pokemon_id"]
        ) and not (
            # v0.40: むれでおそうは、好きなだけ出したあと（同じワザの bench_from_deck が続いたあと）に 1 回だけ切る
            shuffle_due["kind"] == "bench_from_deck" and kind == "bench_from_deck" and e.get("effect") == shuffle_due.get("effect")
            and e["player"] == shuffle_due["player"] and "effect" in e and _benches_any_from_deck(state, e["effect"])
        ) and not (
            # v0.43: てしたをよぶは、最大 2 枚を続けて出したあと（同じ特殊能力の bench_from_deck が続いたあと）に 1 回だけ切る
            shuffle_due["kind"] == "bench_from_deck" and kind == "bench_from_deck" and "power" in e and e["power"] == shuffle_due.get("power")
            and e["player"] == shuffle_due["player"]
        ) and not (
            # v0.85: せいでんきは、何枚もつけたあと（同じワザの attach_energy_from_deck が続いたあと）に 1 回だけ切る
            shuffle_due.get("kind") == "attach_energy_from_deck" and kind == "attach_energy_from_deck" and id(shuffle_due) in static_attaches
            and e["player"] == shuffle_due["player"] and e["pokemon_id"] == shuffle_due["pokemon_id"]
        ) and shuffle_due is not e:
            due_event, shuffle_due = shuffle_due, None
            if kind != "shuffle" or e["player"] != due_event["player"]:
                problems.append(f"{due_event['turn']} 番の {due_event['kind']} のすぐあとに、プレイヤー {due_event['player']} の山札を切る処理（shuffle）がない")
        if check_due is not None and not (kind == "coin_flip" and e["source"] == "attack_check"):
            due_check, check_due = check_due, None
            if kind != "attack_check" or (e["pokemon_id"], e["created_turn"]) != due_check[:2] or prior is None \
                    or prior["kind"] != "coin_flip" or prior["source"] != "attack_check" or prior["result"] != e["result"] \
                    or prior["player"] != e["player"] or e["succeeded"] != (e["result"] == "heads"):
                problems.append(f"{e['turn']} 番のワザの宣言（ポケモン {due_check[0]}）のすぐあとに、手順 4 のコイン（coin_flip・attack_check）がない（{kind}）")
            elif not e["succeeded"]:
                check_failed = e
            if kind == "attack_check" and due_check[2]:
                used_due = (due_check[0], due_check[1])  # 「1回できえる」効果は、すぐあとに消える（理由 used）
        elif used_due is not None:
            due_used, used_due = used_due, None
            if kind != "persistent_effect_removed" or e["reason"] != "used" or (e["pokemon_id"], e["created_turn"]) != due_used:
                problems.append(f"{e['turn']} 番の手順 4 のコインのあとに、「1回できえる」効果（ポケモン {due_used[0]}）を消したログがない（{kind}）")
        elif kind == "attack_check":
            problems.append(f"{e['turn']} 番の手順 4 のコイン（ポケモン {e['pokemon_id']}）が、ワザの宣言のすぐあとにない・はたらいている効果がない")
        elif check_failed is not None and kind != "attack_check" and not (kind == "persistent_effect_removed" and e["reason"] == "used"):
            failed, check_failed = check_failed, None
            if kind != "attack_failed" or e.get("reason") != "attack_check" or e["pokemon_id"] != failed["pokemon_id"]:
                problems.append(f"{failed['turn']} 番の手順 4 のコインが「うら」（ポケモン {failed['pokemon_id']}）なのに、そのあとに attack_failed がない（{kind}）")
        if kind == "persistent_effect_removed" and e["reason"] == "used":
            info = alive.get((e["pokemon_id"], e["created_turn"]))
            if prior is None or prior["kind"] != "attack_check" or prior["pokemon_id"] != e["pokemon_id"] or info is None \
                    or info["kind"] != AttackCoinCheck.kind or not info.get("single_use"):
                problems.append(f"{e['turn']} 番に「1回できえる」でない効果・手順 4 のコインのあとでない効果（ポケモン {e['pokemon_id']}）を「使った」で消した")
        if kind not in DECLARED_FOLLOWERS:
            # v0.42: 宣言のすぐあとに、その特殊能力の処理の最初のログ（コイン・入れ替え・手札のトラッシュ・ダメージカウンターをとりのぞく処理）がある
            if declared is not None and not _follows_declaration(state, declared_key, declared[1], declared[2], e):
                problems.append(
                    f"{declared[0]} 番の特殊能力の宣言（ポケモン {declared[2]}）のすぐあとに、その処理（move_energy・power_attach_energy・"
                    "move_damage_counter・v0.42 の特殊能力の処理）がない"
                )
            declared = None
        if draw_due is not None:
            due_draw, draw_due = draw_due, None
            if kind != "draw" or e["player"] != due_draw[0] or len(e["cards"]) > due_draw[1]:
                problems.append(f"{due_draw[2]} 番の {due_draw[3]} のすぐあとに、プレイヤー {due_draw[0]} が {due_draw[1]} 枚まで引く処理（draw）がない（{kind}）")
        answers_entry = kind == "entry_power_declined" or (kind == "pokemon_power" and "entry" in e)
        # v0.43: 場に出たときの特殊能力の使う機会には、その機会のあと（進化・手札から場に出したあと）に 1 回だけ答える。v0.86 から、同じ時点のほかの反応（［れんさしんか］・
        # 別のポケモンの使う機会。順番は番のプレイヤーが決める）のあとに答えることがあるので、答えを待つ機会を番号ごとに持ち、ワザ・番の終わりまでにすべて答えたことを確かめる
        if answers_entry:
            due_entry = entry_due.pop(e["pokemon_id"], None)
            if due_entry is None or e["turn"] != due_entry[0]:
                problems.append(f"{e['turn']} 番の場に出たときの特殊能力の答え（ポケモン {e['pokemon_id']}）が、使う機会（その特殊能力を持つカードの進化・手札から場に出したあと）にない")
        elif kind in ("attack", "turn_end") and entry_due:
            for pid, (turn, key) in sorted(entry_due.items()):
                problems.append(f"{turn} 番の進化・場に出したポケモン {pid} の場に出たときの特殊能力 {key} を使うかの答えが、{kind} の前にない")
            entry_due.clear()
        if kind != "move_energy":
            moving = None
        if condition_due is not None:
            due_coin, condition_due = condition_due, None
            if kind != "special_condition" or e["pokemon_id"] != due_coin[1] or e.get("effect") != due_coin[0]["effect"]:
                problems.append(f"{due_coin[0]['turn']} 番の特殊能力のコインのあと、置きかえたポケモン {due_coin[1]} が、その特殊能力の特殊状態にならない（{kind}）")
        if previous is not None and previous["kind"] == "coin_flip" and previous["source"] == "power" and kind == "special_conditions_removed" \
                and isinstance(_power_effect(state, previous.get("effect")), CoinConditionOnEitherActive):
            condition_due = (previous, e["pokemon_id"])
        power_knock_out = False
        if power_ko_due is not None:
            due_pid, power_ko_due = power_ko_due, None
            if kind == "knock_out" and ids.get(e["pokemon"]) == due_pid and e.get("timing") == "power":
                power_knock_out = True
            else:
                problems.append(f"{e['turn']} 番の特殊能力の処理で HP 以上になったポケモン {due_pid} が、すぐあとにきぜつしていない（{kind}）")
        if confusion_due is not None:
            due_pid, due_key = confusion_due
            if kind == "special_conditions_removed" and e["pokemon_id"] == due_pid and e["reason"] == "replaced":
                pass
            else:
                confusion_due = None
                if not (kind == "special_condition" and e["pokemon_id"] == due_pid and e["condition"] == "confusion" and e.get("effect") == due_key):
                    problems.append(f"{e['turn']} 番の「ぼうぎょかふん」の「おもて」のあとに、ダメージを与えたポケモン {due_pid} のこんらんがない（{kind}）")
        # v0.12: 「ふしちょう」。きぜつ（knock_out）のあと、サイド（take_prize）のあとに答え（post_knockout_power_declined・
        # post_knockout_power_declared）が 1 つ。対戦が終わるなら答えはない。宣言のすぐあとに、そのカードの return_to_hand
        if rebirth_answered is not None:
            answered, rebirth_answered = rebirth_answered, None
            if answered["kind"] == "post_knockout_power_declared" and not (
                kind == "return_to_hand" and e["card"] == answered["card"] and e["player"] == answered["player"] and e["power"] == answered["power"]
            ):
                problems.append(f"{answered['turn']} 番の「ふしちょう」の宣言（カード {answered['card']}）のすぐあとに、そのカードの return_to_hand がない（{kind}）")
        if kind == "return_to_hand" and (previous is None or previous["kind"] != "post_knockout_power_declared"):
            problems.append(f"{e['turn']} 番にトラッシュから手札に加えた {e['card']} の直前に、「ふしちょう」の宣言がない（使わなかった・宣言のない回収）")
        if batch_answered and kind in ("take_prize", "knock_out", "game_end"):
            problems.append(f"{e['turn']} 番の「ふしちょう」の答えのあとに {kind} がある（答えは、サイドを取り、対戦が続くと決まったあと。正規化した順番）")
        if kind in ("post_knockout_power_declined", "post_knockout_power_declared"):
            match = next((r for r in rebirth_pending if r["card"] == e["card"]), None)
            if match is None:
                problems.append(f"{e['turn']} 番の「ふしちょう」の答え（カード {e['card']}）が、直前のきぜつの処理の中にない")
            else:
                rebirth_pending.remove(match)
                if match["blocked"] is not None:
                    problems.append(f"{e['turn']} 番に、使えない「ふしちょう」（カード {e['card']}。{match['blocked']}）を使うかを決めた（P13〜P18）")
                if (e["player"], e["power"]) != (match["player"], match["power"]):
                    problems.append(f"{e['turn']} 番の「ふしちょう」の答え（カード {e['card']}）のプレイヤー・特殊能力が、きぜつしたカードの持ち主・特殊能力と違う")
            rebirth_answered = e
            batch_answered = True
        elif rebirth_pending and kind not in ("knock_out", "persistent_effect_removed", "take_prize"):
            if kind != "game_end":
                for r in rebirth_pending:
                    if r["blocked"] is None:
                        problems.append(f"{r['turn']} 番にきぜつした「ふしちょう」を使えるカード {r['card']} に、使うかの答えがないまま {kind} になった（P1・P2）")
            rebirth_pending = []
        if batch_answered and kind in ("promote_active", "turn_end", "pokemon_check", "turn_start"):
            batch_answered = False
        # v0.9: ワザを受けるときに自動的にはたらく特殊能力（ゴーストの「とうめい」）
        if previous is not None and previous["kind"] == "coin_flip" and previous["source"] == "power" and not _power_coin_follows(state, previous, e):
            # v0.9 の「とうめい」の判定・v0.11 の「こんじょう」の結果・v0.42 の「ぼうぎょかふん」の結果・ヒーリング・かおりのわなの「おもて」の処理
            problems.append(
                f"{previous['turn']} 番の特殊能力のコイン（{previous['effect']}）のすぐあとに、その結果（「とうめい」の判定 evade_check・"
                "「こんじょう」の ko_prevented・ko_prevention_failed・v0.42 の特殊能力の結果）がない"
            )
        # v0.11: 「こんじょう」の宣言のすぐあとに持ち主のコイン 1 枚（p.311 の手順。G13・G17）。使わなかったらコインはない（G11）
        if prior is not None and prior["kind"] == "ko_prevention_declared" and not (
            kind == "coin_flip" and e["source"] == "power" and e["player"] == prior["player"] and e["pokemon_id"] == prior["pokemon_id"]
            and e["effect"] == prior["power"]
        ):
            problems.append(f"{prior['turn']} 番の「こんじょう」の宣言（ポケモン {prior['pokemon_id']}）のすぐあとに、持ち主の「こんじょう」のコインがない（{kind}）")
        if prior is not None and prior["kind"] == "ko_prevention_declined" and kind == "coin_flip":
            problems.append(f"{prior['turn']} 番に「こんじょう」を使わなかった（ポケモン {prior['pokemon_id']}）のに、コインを投げた（G11）")
        if expect is not None:
            pid, element, reaches = expect
            expect = None
            if not reaches:
                follows = kind == "attack_evaded" and e["pokemon_id"] == pid and e["element"] == element
            elif element == DAMAGE_ELEMENT:
                follows = kind == "damage" and e.get("pokemon_id", ids.get(e["pokemon"])) == pid and e["amount"] > 0
            elif element == FORCED_SWITCH_ELEMENT:
                follows = kind == "forced_switch" and e["old_active_pokemon_id"] == pid
            elif element == ENERGY_DISCARD_ELEMENT:  # v0.31: 相手のエネルギーカードのトラッシュ（スーパーデストロイ・メラメラ）
                follows = kind == "discard_attached_energy" and e["pokemon_id"] == pid
            elif element == ATTACK_LOCK_ELEMENT:  # v0.31: 次の相手の番にワザを使えなくする効果（しっぽをふる）
                follows = kind == "persistent_effect_added" and e["pokemon_id"] == pid
            elif element == ENERGY_ATTACH_ELEMENT:  # v0.31: 控えポケモンにエネルギーをつける（エナジーボム）
                follows = kind == "attack_attach_energy" and e["to_pokemon_id"] == pid
            elif element in (REDUCED_DAMAGE_ELEMENT, ATTACK_CHECK_ELEMENT, RETREAT_LOCK_ELEMENT):
                # v0.34: 与えるダメージがへる状態にする効果（なきつく）。v0.36: すなかけ・えんまくなど・アイスバーン・わしづかみ
                follows = kind == "persistent_effect_added" and e["pokemon_id"] == pid
            elif element == RETURN_IN_PLAY_TO_DECK_ELEMENT:  # v0.36: 自分を山札にもどす（くもがくれガス）
                follows = kind == "return_in_play_to_deck" and e["pokemon_id"] == pid
            elif element == HEAL_ELEMENT:  # v0.41: ワザでダメージカウンターをとりのぞく（とりのぞくカウンターがあるポケモンだけで判定する）
                follows = kind == "attack_heal" and e["pokemon_id"] == pid
            elif element == COUNTERS_ELEMENT:  # v0.41: ダメージカウンターをのせる・取り替える（受けなければ CX1 で止まる）
                follows = (kind == "place_damage_counters" and e["pokemon_id"] == pid) or (kind == "swap_damage_counters" and e["opponent_pokemon_id"] == pid)
            elif element == EVOLVE_ELEMENT:  # v0.42: 山札の進化カードを重ねる（つきのちから）
                follows = kind == "evolve" and e["pokemon_id"] == pid
            elif element == RETURN_IN_PLAY_TO_HAND_ELEMENT:  # v0.42: 自分の場のポケモンを手札にもどす（ようせいのきせき）
                follows = kind == "return_in_play_to_hand" and e["pokemon_id"] == pid
            elif element == DEVOLVE_ELEMENT:  # v0.50: 進化カードをはがして手札にもどす（たいかビーム。自分・相手のポケモン）
                follows = kind == "devolve" and e["pokemon_id"] == pid and "effect" in e
            elif kind == "special_conditions_removed" and e["pokemon_id"] == pid and e["reason"] == "replaced":
                follows, expect = True, (pid, element, reaches)  # 置きかえてから、その特殊状態になる
            else:
                # v0.46: 効果を受けたが、めんえきで特殊状態にならない（special_condition_prevented）も受けたことになる
                follows = kind in ("special_condition", "special_condition_prevented") and e["pokemon_id"] == pid and e["condition"] == element
            if not follows:
                problems.append(
                    f"{e['turn']} 番の「とうめい」の判定（ポケモン {pid}・{element}・{'受ける' if reaches else '受けない'}）のすぐあとが {kind}"
                )
        # v0.10: ダメージを受けたときに自動的にはたらく特殊能力（カイリキーの「はんげき」）。ワザのダメージを受けたときにはたらいて
        # いたら（due）、そのワザのダメージの要素のあと、ダメージ以外の効果・きぜつの前に、counterattack（か counterattack_skipped）がある
        if attack_window is not None:
            due = attack_window["due"]
            if kind in ("damage", "damage_prevented") or (kind == "attack_evaded" and e["element"] == DAMAGE_ELEMENT):
                attack_window["any_damage"] = True  # v0.42: エネループのもどす処理はダメージの要素より前
            if kind == "damage" and e["amount"] > 0 and not e.get("retaliation"):
                # v0.42: このワザのダメージ（0 より大きい）を受けたポケモン（「ぼうぎょかふん」がはたらく理由）
                attack_window.setdefault("damaged", set()).add(e.get("pokemon_id", ids.get(e["pokemon"])))
            if kind == "damage":
                pid = e.get("pokemon_id", ids.get(e["pokemon"]))
                source = attack_window
                if e.get("retaliation"):
                    # v0.12: 「ほのおのかべ」のダメージ（R団のファイヤーのワザによるダメージ。ワザを使ったポケモンへ）
                    source = attack_window["ret"]
                    if source is None or source["damage_seen"]:
                        problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」のダメージ（ポケモン {pid}）の前に、その「ほのおのかべ」・「こうらがえし」（retaliation）がない・2 回目")
                        source = attack_window
                    else:
                        source["damage_seen"] = True
                        if (pid, e["player"], e.get("effect")) != (attack_window["pokemon_id"], attack_window["player"], source["effect"]):
                            problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」のダメージを受けたのが、ダメージを与えた相手の対戦ポケモン {attack_window['pokemon_id']} ではない（{pid}。W14）")
                        problems.extend(retaliation_damage_problems(e, source))
                elif attack_window["ret_seen"]:
                    problems.append(f"{e['turn']} 番のワザで、「ほのおのかべ」・「こうらがえし」のあとにワザのダメージの要素（ポケモン {pid}）がある（ダメージの処理のあとに与えるはず。p.89・W21）")
                if attack_window["counter_seen"]:
                    problems.append(f"{e['turn']} 番のワザで、「はんげき」のあとにダメージの要素（ポケモン {pid}）がある（ダメージの処理のあとに与えるはず。p.89）")
                if e["amount"] > 0 and pid in in_play and pokemon_owner.get(pid) != source["player"]:
                    key, amount, blocked_by = counter_power(pid)
                    if key is not None and blocked_by is None:
                        due.append((pid, key, amount))
                    if guts_power(pid)[0] is not None:
                        # v0.11: 「こんじょう」を持つポケモンが、相手のワザのダメージを受けたときのねむり・マヒ・こんらん（None なら使える。G29）
                        attack_window["ko_able"][pid] = exclusive.get(pid)
                    info = None if e.get("retaliation") else active_retaliation(pid, e["turn"])
                    if info is not None:
                        # v0.12: 「ほのおのかべ」がはたらく（W11・W13）。v0.13: 受けたダメージ（このログの最終ダメージ）も覚えておく
                        # （「こうらがえし」の返すダメージの基本となるダメージ。S9・S10）
                        attack_window["ret_due"].append((pid, info, e["amount"]))
            elif attack_window["ret_due"] and (
                kind in COUNTER_BARRIERS or (kind == "special_conditions_removed" and e["reason"] == "replaced")
                or (kind == "coin_flip" and e["source"] == "attack" and attack_window["counter_after_coin"])
            ):
                problems.append(f"{e['turn']} 番のワザで、はたらいた「ほのおのかべ」・「こうらがえし」（ポケモン {[d[0] for d in attack_window['ret_due']]}）より先に {kind} がある（p.89・W21）")
                attack_window["ret_due"].clear()
            elif due and (
                kind in COUNTER_BARRIERS or (kind == "special_conditions_removed" and e["reason"] == "replaced")
                or (kind == "coin_flip" and e["source"] == "attack" and attack_window["counter_after_coin"])
            ):
                problems.append(f"{e['turn']} 番のワザで、はたらいた「はんげき」（ポケモン {[d[0] for d in due]}）より先に {kind} がある（p.89）")
                due.clear()
            if kind == "knock_out" and attack_window["counter_ko"] is not None and ids.get(e["pokemon"]) != attack_window["counter_ko"]:
                problems.append(
                    f"{e['turn']} 番のワザで、「はんげき」できぜつしたポケモン {attack_window['counter_ko']} のほかにポケモン {ids.get(e['pokemon'])} が"
                    "きぜつした（同時のきぜつか決められない。UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT で止めるはず）"
                )
            if kind == "drain_heal" and attack_window["counter_ko"] == e["pokemon_id"]:
                problems.append(f"{e['turn']} 番に、「はんげき」できぜつしたポケモン {e['pokemon_id']} のダメージカウンターをとりのぞいた（C16）")
            if kind == "drain_heal_skipped" and (e["pokemon_id"] not in in_play or damage[e["pokemon_id"]] < max_hp_now(e["pokemon_id"])):
                problems.append(f"{e['turn']} 番に、きぜつしていないポケモン {e['pokemon_id']} のとりのぞく効果を処理しなかった")
        if kind == "attack":
            for (effect_pid, _), info in alive.items():
                # v0.35: 「あわあわ」（自分）・「ドわすれ」（相手が選んだワザ）で、はたらく番に使えないワザを使っていない
                if (effect_pid == ids.get(e["pokemon"]) and info["kind"] in (CannotUseOwnAttack.kind, CannotUseAttack.kind)
                        and info["active_turn"] == e["turn"] and info["target_attack_index"] == e["attack_index"]
                        and info["target_attack_card"] == _attack_card_id(state, e)):  # v0.49: ワザは (印刷したカード, 位置) で識別する
                    problems.append(f"{e['turn']} 番に、ポケモン {effect_pid} が使えないワザ（{e['attack_index']} 番目。{info['kind']}）を使った")
            # v0.36: はたらいている手順 4 のコインの効果（すなかけ・えんまくなど）。宣言のすぐあとにコインがあるはず
            due_checks = [(effect_pid, created, bool(info.get("single_use"))) for (effect_pid, created), info in alive.items()
                          if effect_pid == ids.get(e["pokemon"]) and info["kind"] == AttackCoinCheck.kind
                          and (info["active_turn"] <= e["turn"] if info.get("lasting") else info["active_turn"] == e["turn"])]
            if len(due_checks) > 1:
                problems.append(f"{e['turn']} 番のワザを使うポケモン {ids.get(e['pokemon'])} に、手順 4 のコインの効果が 2 つ以上ある")
            check_due = due_checks[0] if due_checks else None
            attack_window = {
                "player": e["player"], "pokemon_id": ids.get(e["pokemon"]), "reception": {},
                "effect": f"{_attack_card_id(state, e)}#{e['attack_index']}",
                # v0.10: はたらいた「はんげき」（場のポケモンの番号, PowerKey, 量）・「はんげき」のログがあったか・「はんげき」で
                # きぜつしたポケモン・効果のコインより前に「はんげき」があるはずか（ダメージのあとのコインが効果を決めるワザ）
                "due": [], "counter_seen": False, "counter_ko": None,
                # v0.11: 「こんじょう」を持つポケモンが相手のワザのダメージを受けたときの特殊状態（ko_able）・決定のあったポケモン（ko_offer）・
                # その結果（declined・declared・heads・tails）・このワザのあとにきぜつしたポケモン（knocked）
                "ko_able": {}, "ko_offer": None, "ko_result": None, "knocked": set(),
                # v0.12: はたらいた「ほのおのかべ」（(場のポケモンの番号, 効果)）・処理中の「ほのおのかべ」（ワザを使ったのは R団のファイヤー）
                "ret_due": [], "ret": None, "ret_seen": False,
                "counter_after_coin": state.effects.attack_entry(_attack_card_id(state, e), e["attack_index"]) is not None
                and state.effects.attack_entry(_attack_card_id(state, e), e["attack_index"]).effect.implementation_id in EFFECT_COIN_AFTER_DAMAGE,
                # v0.46: ワザが使われた時（宣言）にねむり・マヒ・こんらん状態だった場のポケモン（［くつろぐかおり］の「ワザが使われた時、すでに」）
                "status_at_attack": frozenset(exclusive),
            }
        elif kind in ("turn_end", "game_end", "halted"):
            if attack_window is not None and attack_window["ko_offer"] is not None:
                pid, result = attack_window["ko_offer"], attack_window["ko_result"]
                if result == "declared":
                    problems.append(f"{e['turn']} 番の「こんじょう」の宣言（ポケモン {pid}）のあとに結果（ko_prevented・ko_prevention_failed）がない")
                elif result in ("tails", "declined") and pid not in attack_window["knocked"]:
                    problems.append(
                        f"{e['turn']} 番に「こんじょう」が{'「うら」' if result == 'tails' else 'ないまま（使わなかった）'}のポケモン {pid} がきぜつしていない（G11・G19・G34）"
                    )
            attack_window = None
        elif kind == "evade_check":
            pid = e["pokemon_id"]
            source = source_of(e)  # v0.12: 「ほのおのかべ」のダメージ（R団のファイヤーのワザ）の判定もある
            if source is None:
                problems.append(f"{e['turn']} 番の「とうめい」の判定（ポケモン {pid}）が、ワザ（{e['effect']}）の処理の中にない")
            elif pid in source["reception"]:
                problems.append(f"{e['turn']} 番のワザで、ポケモン {pid} の「とうめい」の判定が 2 回以上（1 つのワザにつき 1 回。T4）")
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or ids.get(e["pokemon"]) != pid:
                problems.append(f"{e['turn']} 番の「とうめい」の判定（ポケモン {pid}）が、判定したプレイヤーの場のポケモンではない（T33）")
            else:
                key, blocked_by = evasion(pid)
                if key is None:
                    problems.append(f"{e['turn']} 番の「とうめい」の判定のポケモン {pid} が、いちばん上のカードに「とうめい」を持っていない")
                elif key != e["power"]:
                    problems.append(f"{e['turn']} 番の「とうめい」の判定の特殊能力 {e['power']} が、ポケモン {pid} の {key} と違う")
                elif blocked_by is not None:
                    problems.append(f"{e['turn']} 番に、{blocked_by} で力が消えている「とうめい」（ポケモン {pid}）の判定がある")
            coin = previous or {}
            if (coin.get("kind"), coin.get("source"), coin.get("player"), coin.get("pokemon_id"), coin.get("effect"), coin.get("result")) != (
                "coin_flip", "power", e["player"], pid, e["power"], e["result"]
            ):
                problems.append(f"{e['turn']} 番の「とうめい」の判定（ポケモン {pid}）の直前に、ゴースト側のプレイヤーの同じ結果のコインがない")
            if e["evaded"] != (e["result"] == "heads") or e["element"] not in ATTACK_ELEMENTS:
                problems.append(f"{e['turn']} 番の「とうめい」の判定（ポケモン {pid}）の結果 {e['result']}・{e['evaded']}・{e['element']} が合わない")
            if source is not None:
                source["reception"].setdefault(pid, not e["evaded"])
            expect = (pid, e["element"], not e["evaded"])
        elif kind == "attack_evaded":
            pid = e["pokemon_id"]
            ret = None if attack_window is None else attack_window["ret"]
            source = ret if ret is not None and e["effect"] == ret["effect"] and pid == attack_window["pokemon_id"] else attack_window
            if source is None or source["reception"].get(pid) is not False or e["effect"] not in (source["effect"], source.get("copied")):
                problems.append(f"{e['turn']} 番のポケモン {pid} の受けなかった要素 {e['element']} の前に、そのワザの「おもて」の判定がない")
            if source is not None and source is ret:
                ret["damage_seen"] = True  # 「ほのおのかべ」のダメージの要素を受けなかった（W19）
            if e["element"] == DAMAGE_ELEMENT and not e.get("amount", 0) > 0:
                problems.append(f"{e['turn']} 番のポケモン {pid} の受けなかったダメージが {e.get('amount')}（0 より大きいはず。T21）")
        elif kind == "damage" and e["amount"] > 0 and not e.get("ignore_defender_effects"):
            # v0.60: 「スピードスター」のダメージは、相手の持っている「とうめい」の影響を受けない（判定がない）
            received(e, e.get("pokemon_id", ids.get(e["pokemon"])), DAMAGE_ELEMENT)
        elif kind == "special_condition" and attack_window is not None and e.get("effect") == attack_window["effect"]:
            received(e, e["pokemon_id"], e["condition"], blocked=replaced.get(e["pokemon_id"]))
        elif kind == "forced_switch":
            received(e, e["old_active_pokemon_id"], FORCED_SWITCH_ELEMENT)
        elif kind == "special_condition_prevented" and attack_window is not None and e.get("effect") == attack_window["effect"]:
            received(e, e["pokemon_id"], e["condition"], blocked=replaced.get(e["pokemon_id"]))  # v0.46: 効果を受けて、めんえきで特殊状態にならない
        elif kind == "discard_attached_energy":  # v0.31
            received(e, e["pokemon_id"], ENERGY_DISCARD_ELEMENT)
        elif kind == "attack_attach_energy":
            received(e, e["to_pokemon_id"], ENERGY_ATTACH_ELEMENT)
        elif kind == "special_conditions_removed" and attack_window is not None and e.get("effect") == attack_window["effect"]:
            received(e, e["pokemon_id"], WAKE_ELEMENT)  # v0.72: めざめのキッス（ワザの効果でねむりから回復させる。相手のポケモンへの効果）
        elif kind == "persistent_effect_added" and e["persistent_effect"] in (CannotAttack.kind, CannotUseAttack.kind, CannotAttackWhileSourceActive.kind):
            received(e, e["pokemon_id"], ATTACK_LOCK_ELEMENT)  # v0.35: 「ドわすれ」も相手の対戦ポケモンが受ける効果。v0.40: 「すごむ」も
        elif kind == "persistent_effect_added" and e["persistent_effect"] in REDUCED_DAMAGE_KINDS:
            received(e, e["pokemon_id"], REDUCED_DAMAGE_ELEMENT)  # v0.34（v0.76: なきごえも）
        elif kind == "persistent_effect_added" and e["persistent_effect"] == AttackCoinCheck.kind:
            received(e, e["pokemon_id"], ATTACK_CHECK_ELEMENT)  # v0.36
        elif kind == "move_opponent_energy":
            received(e, e["pokemon_id"], ENERGY_MOVE_ELEMENT)  # v0.45: はがすのは相手の対戦ポケモンへの効果、つけるのは控えへの効果
            if e["result"] == "attached":
                received(e, e["to_pokemon_id"], ENERGY_ATTACH_ELEMENT)
        elif kind == "persistent_effect_added" and e["persistent_effect"] == CannotRetreat.kind:
            received(e, e["pokemon_id"], RETREAT_LOCK_ELEMENT)  # v0.36
        elif kind == "return_in_play_to_deck":
            received(e, e["pokemon_id"], RETURN_IN_PLAY_TO_DECK_ELEMENT)  # v0.36
        elif kind == "attack_heal":
            received(e, e["pokemon_id"], HEAL_ELEMENT)  # v0.41: ワザでダメージカウンターをとりのぞく効果（自分・控え・相手のポケモン）
        elif kind == "place_damage_counters":
            received(e, e["pokemon_id"], COUNTERS_ELEMENT)  # v0.41: ダメージカウンターをのせる効果（ダメージシフト）
        elif kind == "swap_damage_counters":
            received(e, e["opponent_pokemon_id"], COUNTERS_ELEMENT)  # v0.41: ダメージカウンターを取り替える効果（チェンジダメージ）
        elif kind == "evolve" and "effect" in e:
            received(e, e["pokemon_id"], EVOLVE_ELEMENT)  # v0.42: つきのちから（自分の場のポケモンへの効果）
        elif kind == "return_in_play_to_hand" and "effect" in e:
            received(e, e["pokemon_id"], RETURN_IN_PLAY_TO_HAND_ELEMENT)  # v0.42: ようせいのきせき
        elif kind == "devolve" and "effect" in e:
            received(e, e["pokemon_id"], DEVOLVE_ELEMENT)  # v0.50: たいかビーム（自分・相手の場のポケモンへの効果）
        if kind == "copy_attack" and attack_window is not None:
            attack_window["copied"] = e["copied"]  # v0.44: 相手のワザを自分のワザとして使った（そのワザの効果のログの effect は copied）
        if kind == "damage" and attack_window is not None and not e.get("retaliation"):
            problems.extend(attack_damage_set_problems(e))  # v0.27
        if kind == "damage" and attack_window is not None:
            problems.extend(zero_damage_below_problems(e))  # v0.45
            problems.extend(continuous_damage_problems(e))  # v0.46
        if kind == "confusion_damage" and attack_window is not None:
            # v0.46: こんらんの 20 に当てはまりうる常にはたらく特殊能力（くつろぐかおり・きょうぼう・なぞのかべ・ふしぎなバリアー）がはたらいていれば、コインの前に
            # 止まる（UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS）ので、こんらんのダメージはない
            found = continuous_expected(e["pokemon_id"], e["pokemon_id"], attack_window["status_at_attack"])
            if [x for x in found if x[1].count("［")]:
                problems.append(f"{e['turn']} 番のこんらんのダメージ（ポケモン {e['pokemon_id']}）に当てはまりうる常にはたらく特殊能力 {[x[1] for x in found]} がはたらいている")
        if kind == "special_condition" and replaced.get(e["pokemon_id"]) is None and working_continuous(e["pokemon_id"], SpecialConditionImmunity):
            # v0.46: はたらいている［めんえき］のポケモンは、特殊状態にならない（付ける前の、置きかえる前のねむり・マヒ・こんらんで使えないときを除く）
            problems.append(f"{e['turn']} 番に、はたらいている特殊状態にならない特殊能力を持つポケモン {e['pokemon_id']} が {e['condition']} 状態になった")
        if kind == "special_conditions_removed" and e["reason"] == "replaced":
            replaced[e["pokemon_id"]] = exclusive.get(e["pokemon_id"])
        elif kind == "special_condition":
            replaced.pop(e["pokemon_id"], None)
        previous = e

        if kind == "turn_start":
            turn_player = e["player"]
            current_turn = e["turn"]  # v0.48
            attached_this_turn = power_attached_this_turn = 0
        if kind == "draw":
            hand[e["player"]].extend(e["cards"])
        elif kind == "mulligan":
            if sorted(e["revealed_hand"]) != sorted(hand[e["player"]]):
                problems.append(f"プレイヤー {e['player']} の切り直しで見せた手札が、ログから組み立てた手札と違う")
            hand[e["player"]] = []
        elif kind == "play_trainer":
            # v0.46: はたらいている［アレルギーかふん］（場のどこでも。ねむり・マヒ・こんらん・かがくへんかガスで消える）があれば、誰もトレーナーカードを使えない
            locked = [pid for pid in sorted(in_play) if working_continuous(pid, PreventTrainerUse)]
            if locked:
                problems.append(f"{e['turn']} 番に、はたらいているトレーナーカードを使えなくする特殊能力（ポケモン {locked}）があるのに、トレーナー {e['card']} を使った")
            # v0.47: 期限のあるトレーナーの使用の禁止（ずつう・こうしゅうは。与えた番の次の番から、消える番まで）を受けているプレイヤーは使えない
            banned = [key for key, info in trainer_locks_log.items() if key[0] == e["player"] and info["turn"] < e["turn"] <= key[1]]
            if banned:
                problems.append(f"{e['turn']} 番に、トレーナーの使用を禁止されている（{banned}）プレイヤー {e['player']} が、トレーナー {e['card']} を使った")
            if e.get("source_zone") == "discard":
                # v0.58: ナツメのサイキックコントロールで、相手（持ち主）のトラッシュのトレーナーカードを使う。外側のカード（via）を使っている最中のプレイヤーが使い、
                # カードは持ち主のトラッシュから出る（手札を通らない）
                card_owner = e.get("owner")
                if card_owner != owner.get(e["card"]) or card_owner == e["player"] or using_trainer.get(e["player"]) != e.get("via") \
                        or e["card"] not in discard[card_owner]:
                    problems.append(f"{e['turn']} 番に外側のトレーナー {e.get('via')} の効果で使ったカード {e['card']} が、使っている最中のプレイヤーの相手のトラッシュのカードではない")
                else:
                    discard[card_owner].remove(e["card"])
                outer_trainers.setdefault(e["player"], []).append(e.get("via"))
            else:
                from_hand(e, e["player"], e["card"])
            using_trainer[e["player"]] = e["card"]
        if kind == "place_starting_pokemon":
            for uid in (e["active"], *e["bench"]):
                from_hand(e, e["player"], uid)
                enter(uid)
            active_of[e["player"]] = ids[e["active"]]  # v0.46
        elif kind == "play_to_bench":
            from_hand(e, e["player"], e["card"])
            enter(e["card"])
            key = entry_opportunity(e["card"], from_hand=True)
            if key is not None:
                entry_due[ids[e["card"]]] = (e["turn"], key)  # v0.86: 手札から場に出したたねポケモンの使う機会（エンテイの［おたけび］）
        elif kind == "evolve":
            shifts.pop(e["pokemon_id"], None)  # v0.48: 進化したら［へんしょく］の記録は消える（別のポケモン。p.310）
            # v0.47: はたらいている［げんしのちから］（場のどこでも。ねむり・マヒ・こんらん・かがくへんかガスで消える）があれば、どの方法でも進化できない。重ねる前の場で求める
            preventing = [pid for pid in sorted(in_play) if working_continuous(pid, PreventEvolution)]
            if preventing:
                problems.append(f"{e['turn']} 番に、はたらいている進化できなくする特殊能力（ポケモン {preventing}）があるのに、ポケモン {e['pokemon_id']} が進化した")
            # v0.25: 通常の進化は「○○○○から進化」の名前が進化前のカードの名前（p.309・p.324）。trainer_card のある進化（ポケモン育て屋さん）は、
            # 使っている最中の 1 進化を飛ばして進化させるトレーナーの効果で、たねポケモンに系統の合う 2 進化カードを重ねた（p.259）
            below, upper, via = state.in_play_def(e["from_card"]), state.in_play_def(e["to_card"]), e.get("trainer_card")
            if via is None:
                if upper.evolves_from != below.name_ja:
                    problems.append(f"{e['turn']} 番の進化（{e['from_card']} → {e['to_card']}）で、{upper.name_ja} の進化元 {upper.evolves_from!r} が {below.name_ja} ではない")
            else:
                entry = state.effects.trainer_entry(state.cards[via].card_id) if via in state.cards else None
                if (entry is None or not entry.effect.skips_stage1_evolution or using_trainer.get(e["player"]) != via
                        or not below.is_basic_pokemon or skipped_stage1_basic(upper) != below.name_ja):
                    problems.append(
                        f"{e['turn']} 番の 1 進化を飛ばした進化（{e['from_card']} → {e['to_card']}、trainer_card {via!r}）が、使っている最中の"
                        "トレーナーの効果で、たねポケモンに系統の合う 2 進化カードを重ねたものではない"
                    )
            if e.get("source_zone") == "deck":
                # v0.42: ワザ（つきのちから）で、ワザを使ったプレイヤーの山札の進化カードを、手札を通さずに重ねた（山札は組み立て直さないので、持ち主・手札・
                # トラッシュ・場にないことで確かめる）。すぐあとに（進化の手順のログのあと）山札を切る
                uid = e["to_card"]
                if "power" in e:
                    # v0.44: ［うか］（特殊能力）。直前に持ち主の「おもて」のコイン（そのあいだに決定がある）。重ねるのは説明の名前のカード
                    effect = _power_effect(state, e["power"])
                    valid = isinstance(effect, CoinEvolveSelfFromDeck) and state.printed_def(uid).name_ja == effect.name \
                        and e["power"].partition("@power")[0] == state.cards[e["from_card"]].card_id
                    if isinstance(effect, (EvolveFromDeckByAttachedEnergyColor, EvolveFromDeckOnOtherEvolution)):
                        # v0.86: ［エナジーしんか］・［れんさしんか］。その特殊能力を持つポケモン自身を、山札の、そのポケモンの名前から進化するカードで進化させる
                        valid = e["power"].partition("@power")[0] == state.cards[e["from_card"]].card_id \
                            and state.printed_def(uid).evolves_from == state.printed_def(e["from_card"]).name_ja
                else:
                    # v0.44: たきのぼりしんか（EvolveSelfFromDeck。ワザを使ったポケモン自身を、説明の名前から進化するカードで進化させる）
                    # v0.84: しんかのうた（EachPlayerEvolutionSong）は、おたがいのプレイヤーが自分のポケモンを自分の山札のカードで進化させる
                    valid = _same_attack(attack_window, e) and (
                        (e["player"] == attack_window["player"] and isinstance(_effect_of_event(state, e), (EvolveFromDeckOnHeads, EvolveSelfFromDeck)))
                        or isinstance(_effect_of_event(state, e), EachPlayerEvolutionSong))
                if not valid or owner.get(uid) != e["player"] \
                        or uid in hand[e["player"]] or uid in discard[e["player"]] or uid in ids or pokemon_owner.get(e["pokemon_id"]) != e["player"]:
                    problems.append(f"{e['turn']} 番に山札から重ねた進化カード {uid} が、そのワザ（山札から進化させるワザ）の処理・山札のカードではない")
                shuffle_due = e
            else:
                from_hand(e, e["player"], e["to_card"])
            ids[e["to_card"]] = e["pokemon_id"]
            top[e["pokemon_id"]] = e["to_card"]
            before = evolve_turns.get(e["pokemon_id"], [])
            if e["turn"] in devolve_turns.get(e["pokemon_id"], ()):
                # v0.50: 退化した番に、そのポケモンを進化させられるかは決まらない（DV2。エンジンが止める）
                problems.append(f"{e['turn']} 番に、その番に退化した場のポケモン {e['pokemon_id']} を進化させた（DV2）")
            elif before and before[-1] == e["turn"] and (e["pokemon_id"], e["turn"]) not in permitted:
                # v0.44: 同じ番の 2 回目の進化は、その前にトレーナー「サカキ」の許可（evolution_permission）があるときだけ
                problems.append(f"{e['turn']} 番に場のポケモン {e['pokemon_id']} を同じ番に 2 回進化させた（サカキの許可がない）")
            evolve_turns.setdefault(e["pokemon_id"], []).append(e["turn"])
            key = entry_opportunity(e["to_card"], from_hand="source_zone" not in e, on_bench=not is_active(e["pokemon_id"]))
            if key is not None:
                entry_due[e["pokemon_id"]] = (e["turn"], key)  # v0.43: 場に出たときの特殊能力の使う機会
        elif kind == "devolve":
            # v0.50: 退化（ミュウの「たいかビーム」・退化スプレー。docs/mew-devolution-spray-v0.50.md）。はがしたカード（上から順）が、ログから組み立てた重なりの上から
            # 続くカードで、持ち主の手札（たいかビーム）・トラッシュ（退化スプレー）に置く。たいかビームはワザの処理の中で 1 枚、退化スプレーは使っている最中のその
            # トレーナーで、使ったプレイヤーの場のポケモン
            pid = e["pokemon_id"]
            removed_cards = list(e.get("removed") or ())
            via = e.get("trainer_card")
            if via is None:
                source_ok = attack_window is not None and _same_attack(attack_window, e) and e["by_player"] == attack_window["player"] \
                    and isinstance(_effect_of_event(state, e), DevolveChosenPokemon) and e["destination"] == "hand" and len(removed_cards) == 1
            else:
                trainer_entry = state.effects.trainer_entry(state.cards[via].card_id) if via in state.cards else None
                source_ok = using_trainer.get(e["by_player"]) == via and e["by_player"] == e["player"] == turn_player \
                    and trainer_entry is not None and (isinstance(trainer_entry.effect, DevolveOwnPokemon) and e["destination"] == "discard"
                                                       # v0.80: 退化スプレーHYPER（1 枚を持ち主の手札に）
                                                       or isinstance(trainer_entry.effect, DevolveOneToHandWithBan) and e["destination"] == "hand"
                                                       and len(removed_cards) == 1)
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or not removed_cards or removed_cards[0] != top.get(pid) \
                    or e["from_card"] != removed_cards[0] or any(ids.get(uid) != pid or owner.get(uid) != e["player"] for uid in removed_cards) \
                    or ids.get(e["to_card"]) != pid or e["to_card"] in removed_cards or disguised.get(pid) is not None or not source_ok:
                problems.append(f"{e['turn']} 番の退化（ポケモン {pid}・はがしたカード {removed_cards}）が、ログから組み立てた重なり・ワザ・トレーナーと合わない")
            for uid in removed_cards:
                ids.pop(uid, None)
                (hand if e["destination"] == "hand" else discard)[e["player"]].append(uid)
            top[pid] = e["to_card"]
            shifts.pop(pid, None)  # 退化したら［へんしょく］の記録は消える（別のポケモン。p.324）
            once_used.difference_update({used for used in once_used if used[0] == pid and used[1] in removed_cards})
            devolve_turns.setdefault(pid, []).append(e["turn"])
            if via is not None:
                trainer_devolved.add((pid, e["turn"]))
        elif kind == "devolve_declined":
            # v0.50: 退化スプレーで 0 枚を選んだ（はがさない）。使っている最中のそのトレーナー
            if using_trainer.get(e["player"]) != e.get("trainer_card") or e["pokemon_id"] not in in_play or pokemon_owner.get(e["pokemon_id"]) != e["player"]:
                problems.append(f"{e['turn']} 番の退化スプレーの 0 枚（ポケモン {e['pokemon_id']}）が、使っている最中のトレーナー・自分の場のポケモンと合わない")
        elif kind == "bench_from_discard":
            # v0.51: トラッシュのたねポケモンのカードを、同じ uid のまま持ち主のベンチに出した（よみがえらせる・元気のかけら・ポケモンの笛。
            # docs/discard-to-bench-v0.51.md）。カードは持ち主（player）のトラッシュ（ログから組み立てた）にあり、トラッシュにある間のカードの定義がたねポケモン、
            # 持ち主のベンチに空きがあった。出どころは、今のワザ（よみがえらせる。選んだのはワザを使ったプレイヤー）か、使っている最中のトレーナー（元気のかけらは使った
            # プレイヤー自身の、ポケモンの笛は相手のトラッシュ）。場のポケモンの番号は次の番号（新しい番号。前に場にいたときのものは引き継がない）
            uid = e["card"]
            via = e.get("trainer_card")
            effect = None
            if via is None:
                effect = _effect_of_event(state, e) if attack_window is not None and _same_attack(attack_window, e) else None
                source_ok = isinstance(effect, BenchBasicFromEitherDiscard) and e["by_player"] == attack_window["player"] and "counters" not in e
            else:
                trainer_entry = state.effects.trainer_entry(state.cards[via].card_id) if via in state.cards else None
                effect = None if trainer_entry is None else trainer_entry.effect
                source_ok = using_trainer.get(e["by_player"]) == via and e["by_player"] == turn_player and (
                    (isinstance(effect, BenchBasicFromOwnDiscardWithCounters) and e["player"] == e["by_player"] and "counters" in e)
                    or (isinstance(effect, BenchBasicFromOpponentDiscard) and e["player"] == 1 - e["by_player"] and "counters" not in e)
                    # v0.71: ポケモンジム第1弾の元気のかけら（自分のトラッシュから、カウンターをのせずに出す。のせるのはすぐあとの trainer_place_damage_counters）
                    or (isinstance(effect, BenchBasicFromOwnDiscardThenCounters) and e["player"] == e["by_player"] and "counters" not in e)
                    # v0.73: 元気のかたまり（自分のトラッシュから、カウンターをのせずに出す。使うための条件のエネルギーカードのトラッシュのあと）
                    or (isinstance(effect, DiscardEnergyThenBenchBasicFromDiscard) and e["player"] == e["by_player"] and "counters" not in e))
            bench_count = sum(1 for pid in in_play if pokemon_owner.get(pid) == e["player"]) - (1 if active_of.get(e["player"]) in in_play else 0)
            if not source_ok or owner.get(uid) != e["player"] or uid not in discard[e["player"]] or not state.printed_def(uid).is_basic_pokemon \
                    or bench_count >= bench_limit_now() or (e["from_zone"], e["to_zone"]) != ("discard", "bench"):
                problems.append(f"{e['turn']} 番にトラッシュからベンチに出したカード {uid}（持ち主 {e['player']}）が、持ち主のトラッシュのたねポケモン・その効果の処理と合わない")
            if uid in discard[e["player"]]:
                discard[e["player"]].remove(uid)
            enter(uid)
            pid = ids[uid]
            if pid != e["to_pokemon_id"]:
                problems.append(f"{e['turn']} 番にトラッシュからベンチに出したポケモンの番号 {e['to_pokemon_id']} が、ログから組み立てた {pid} と違う")
            discard_entered[pid] = e["turn"]
            if "counters" in e:
                # 元気のかけら: カードの HP（トラッシュにある間の定義）の半分（切り捨て。ダメージカウンターの単位）をのせた状態で出す
                per = state.rules.damage_per_counter
                hp = state.printed_def(uid).hp
                if e["counters"] != hp // per // 2 or e["damage"] != e["counters"] * per:
                    problems.append(f"{e['turn']} 番に元気のかけらで出したポケモン {pid} のダメージカウンター {e['counters']} が、HP {hp} の半分（切り捨て）ではない")
                damage[pid] = e["damage"]
            if via is None:
                attack_window["discard_entered"] = pid
            elif isinstance(effect, BenchBasicFromOwnDiscardThenCounters):
                revive_then_counters = (pid, via, e["turn"])
        elif kind == "trainer_place_damage_counters":
            # v0.71: ポケモンジム第1弾の元気のかけら（GD1-017）。同じトレーナーでトラッシュからベンチに出したポケモンに、出したあとの今有効な最大HPの半分（切り捨て）の
            # ダメージカウンター（ダメージではない）。出したすぐあと・1 回だけ
            pid = e["pokemon_id"]
            per = state.rules.damage_per_counter
            if revive_then_counters != (pid, e.get("trainer_card"), e["turn"]) or prior is None or prior["kind"] != "bench_from_discard" \
                    or e["damage_before"] != damage[pid] or e["counters"] != max_hp_now(pid) // per // 2 or e["counters"] <= 0 \
                    or e["amount"] != e["counters"] * per or pokemon_owner.get(pid) != e["player"]:
                problems.append(f"{e['turn']} 番の trainer_place_damage_counters（ポケモン {pid}）が、元気のかけらで出したすぐあとに HP の半分（切り捨て）をのせる処理と合わない")
            revive_then_counters = None
            damage[pid] += e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の trainer_place_damage_counters のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind in ("bench_from_discard_none", "bench_from_discard_declined"):
            # v0.51: よみがえらせるで出せるカードがなかった（ワザの処理の中）・元気のかけら・ポケモンの笛で 0 枚を選んだ（使っている最中のトレーナー）
            if kind == "bench_from_discard_none":
                source_ok = attack_window is not None and _same_attack(attack_window, e) and isinstance(_effect_of_event(state, e), BenchBasicFromEitherDiscard) \
                    and e["player"] == attack_window["player"] and not any(
                        uid for p_index in (0, 1) for uid in discard[p_index]
                        if state.printed_def(uid).is_basic_pokemon
                        and sum(1 for pid in in_play if pokemon_owner.get(pid) == p_index) - (1 if active_of.get(p_index) in in_play else 0) < bench_limit_now())
                # v0.84: むかえび（自分のトラッシュのベイビィ・たねポケモン。出せるカードがない）
                source_ok = source_ok or (attack_window is not None and _same_attack(attack_window, e)
                                          and isinstance(_effect_of_event(state, e), BenchBabyOrBasicFromOwnDiscardAttack)
                                          and e["player"] == attack_window["player"]
                                          and not any(state.printed_def(uid).is_basic_pokemon for uid in discard[e["player"]]))
            else:
                via = e.get("trainer_card")
                trainer_entry = state.effects.trainer_entry(state.cards[via].card_id) if via in state.cards else None
                source_ok = trainer_entry is not None and isinstance(trainer_entry.effect, (BenchBasicFromOwnDiscardWithCounters, BenchBasicFromOpponentDiscard)) \
                    and using_trainer.get(e["by_player"]) == via and e["by_player"] == turn_player
            if not source_ok:
                problems.append(f"{e['turn']} 番の {kind} が、出せるカードのない「よみがえらせる」・使っている最中の元気のかけら・ポケモンの笛の処理と合わない")
        elif kind in ("counterattack", "counterattack_skipped"):
            # v0.10: 「はんげき」のダメージ（ワザを使ったポケモンへ。ワザによるダメージではない）
            target = e["attacker_pokemon_id"]
            if source_of(e) is None:
                # v0.12: 「ほのおのかべ」のダメージ（R団のファイヤーのワザ）を受けたポケモンの「はんげき」は、R団のファイヤーに与える
                problems.append(f"{e['turn']} 番の「はんげき」（ポケモン {e['pokemon_id']}）が、ダメージを与えたワザの処理の中にない（与える相手はワザを使ったポケモン）")
            amount = None
            if attack_window is not None:
                attack_window["counter_seen"] = True
                if not attack_window["due"]:
                    problems.append(f"{e['turn']} 番の「はんげき」（ポケモン {e['pokemon_id']}）が、はたらく理由（相手のワザのダメージを、はたらいている「はんげき」で受けた）なしにある")
                else:
                    pid, key, amount = attack_window["due"].pop(0)
                    if (e["pokemon_id"], e["power"]) != (pid, key) or ids.get(e["pokemon"]) != pid or e["player"] != pokemon_owner.get(pid):
                        problems.append(f"{e['turn']} 番の「はんげき」が、ダメージを受けたポケモン {pid} の {key} ではない（{e['pokemon_id']}・{e['power']}）")
            if target not in in_play:
                problems.append(f"{e['turn']} 番の「はんげき」を与える相手 {target} が場にいない")
                continue
            hp = max_hp_now(target)
            if kind == "counterattack_skipped":
                if e["reason"] != "knocked_out" or damage[target] < hp:
                    problems.append(f"{e['turn']} 番に、きぜつしていない相手 {target}（ダメージ {damage[target]}）に「はんげき」を与えなかった（{e['reason']}）")
                continue
            if damage[target] >= hp:
                problems.append(f"{e['turn']} 番に、すでに HP 以上のダメージの相手 {target} に「はんげき」を与えた（対象がいない。C15）")
            if amount is not None:
                # v0.46: 受けるポケモン（ワザを使ったポケモン）の、受けるダメージを変える常にはたらく特殊能力（ふしぎなバリアー・なぞのかべ）を当てはめた量
                problems.extend(received_power_problems(e, target, e["pokemon_id"], amount))
            damage[target] += e["amount"]
            if damage[target] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の counterattack のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[target]} と違う")
            if e["knocked_out"] != (damage[target] >= hp):
                problems.append(f"{e['turn']} 番の「はんげき」のきぜつの印 {e['knocked_out']} が、ログから組み立てたダメージ {damage[target]} と合わない")
            if damage[target] >= hp and attack_window is not None:
                attack_window["counter_ko"] = target
        elif kind in ("retaliation", "retaliation_skipped"):
            # v0.12: 「ほのおのかべ」（相手のワザによるダメージを受けたとき、ダメージを与えた相手の対戦ポケモンに 10。R団のファイヤーのワザ）
            holder, target = e["pokemon_id"], e["attacker_pokemon_id"]
            if attack_window is None or (e["trigger"], e["attacker"], target) != (
                attack_window["effect"], attack_window["player"], attack_window["pokemon_id"]
            ):
                problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」（ポケモン {holder}）が、ダメージを与えたワザの処理の中にない（W14）")
                continue
            if not attack_window["ret_due"] or attack_window["ret_due"][0][0] != holder:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」（ポケモン {holder}）が、はたらく理由（相手のワザのダメージを、効果がはたらいているポケモンが受けた）なしにある（W4・W11・W13）")
                info, received_damage = active_retaliation(holder, e["turn"]), None
            else:
                _, info, received_damage = attack_window["ret_due"].pop(0)
            if info is None or pokemon_owner.get(holder) != e["player"] or ids.get(e["pokemon"]) != holder or info["source_card"] != e["source_card"]:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」（ポケモン {holder}）に、今の番にはたらく効果（ログの persistent_effect_added）がない（W4・W5）")
            elif e["effect"] != info["effect"]:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」のワザ {e['effect']} が、効果を与えたワザ {info['effect']} と違う")
            if target not in in_play:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」を与える相手 {target} が場にいない")
                continue
            hp = max_hp_now(target)
            entry = state.effects.attack_entry(*_attack_key(e["effect"]))
            terms = getattr(entry.effect, "retaliation_terms", None) if entry is not None else None
            # v0.45: 倍数とはたらくときのコインのある効果（クロスカウンター）は 4 つの値（v0.44 までの効果は 2 つ）
            basis, fixed, multiplier, on_heads = (tuple(terms()) + (1, False))[:4] if terms is not None else (None, None, 1, False)
            scaled = multiplier != 1 or on_heads
            coin = prior or {}
            heads_coin = (coin.get("kind"), coin.get("source"), coin.get("player"), coin.get("pokemon_id"), coin.get("effect")) == (
                "coin_flip", "attack", e["player"], holder, e["effect"])
            if kind == "retaliation_skipped":
                if e["reason"] == RETALIATION_COIN_TAILS:
                    # v0.45: クロスカウンターのコインが「うら」（与えない）。直前に効果を持つポケモンの持ち主の「うら」のコインがある
                    if not on_heads or not heads_coin or coin.get("result") != "tails" or e.get("received_damage") != received_damage \
                            or damage[target] >= hp:
                        problems.append(f"{e['turn']} 番のクロスカウンターの「うら」（ポケモン {holder}）の直前に持ち主の「うら」のコインがない・受けたダメージが合わない")
                elif e["reason"] != "knocked_out" or damage[target] < hp:
                    problems.append(f"{e['turn']} 番に、きぜつしていない相手 {target}（ダメージ {damage[target]}）に「ほのおのかべ」・「こうらがえし」を与えなかった（{e['reason']}）")
                elif coin.get("kind") == "coin_flip" and coin.get("effect") == e["effect"] and coin.get("pokemon_id") == holder:
                    problems.append(f"{e['turn']} 番に、すでに HP 以上の相手 {target} への返す効果のコインを投げた（C15）")
                continue
            if damage[target] >= hp:
                problems.append(f"{e['turn']} 番に、すでに HP 以上のダメージの相手 {target} に「ほのおのかべ」・「こうらがえし」を与えた（対象がいない。W23）")
            expected_kind = RETALIATION_RECEIVED_SCALED_KIND if scaled else RETALIATION_KINDS.get(basis)
            if info is not None and basis is not None and info["kind"] != expected_kind:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」の効果の種類 {info['kind']} が、ワザ {e['effect']} の登録と違う")
            if on_heads and (not heads_coin or coin.get("result") != "heads" or e.get("coin") != "heads"):
                problems.append(f"{e['turn']} 番のクロスカウンター（ポケモン {holder}）の直前に、持ち主の「おもて」のコインがない（LD-PMCG5-054-ATK0）")
            if scaled:
                # v0.45: 基本となるダメージは、受けたダメージ（きっかけのダメージのログの最終ダメージ）の multiplier 倍
                if (e.get("basis"), e.get("received_damage"), e.get("multiplier")) != (basis, received_damage, multiplier) \
                        or received_damage is None or e["amount"] != received_damage * multiplier:
                    problems.append(f"{e['turn']} 番のクロスカウンターの量 {e['amount']}（{e.get('received_damage')}・{e.get('multiplier')}）が、受けたダメージ"
                                    f" {received_damage} の {multiplier} 倍と違う")
            elif basis == RETALIATION_FIXED:
                if e["amount"] != fixed or "basis" in e or "received_damage" in e:
                    problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」の量 {e['amount']} が、ワザ {e['effect']} の登録と違う（W14）")
            elif basis == RETALIATION_RECEIVED:
                # v0.13: 「こうらがえし」。基本となるダメージは、きっかけのダメージのログの最終ダメージ（受けたダメージ）と同じ（S9・S10）
                if (e.get("basis"), e.get("received_damage")) != (basis, received_damage) or e["amount"] != received_damage \
                        or "multiplier" in e or "coin" in e:
                    problems.append(
                        f"{e['turn']} 番の「こうらがえし」の量 {e['amount']}（{e.get('basis')}・{e.get('received_damage')}）が、受けたダメージ"
                        f" {received_damage} と違う（S9・S10）"
                    )
            else:
                problems.append(f"{e['turn']} 番の「ほのおのかべ」・「こうらがえし」のワザ {e['effect']} に、ダメージを返す効果が登録されていない（W14）")
            attack_window["ret"] = {
                "effect": e["effect"], "player": e["player"], "pokemon_id": holder, "reception": {}, "amount": e["amount"], "damage_seen": False,
            }
            attack_window["ret_seen"] = True
        elif kind == "persistent_effect_skipped":
            # v0.12: ワザを使ったポケモンが相手の「はんげき」で HP 以上になったので、自分に与える持続する効果を与えなかった
            pid = e["pokemon_id"]
            if attack_window is None or pid != attack_window["pokemon_id"] or pid not in in_play or damage[pid] < max_hp_now(pid):
                problems.append(f"{e['turn']} 番に、きぜつしていないポケモン {pid} の持続する効果（{e['persistent_effect']}）を与えなかった")
        elif kind == "energy_returned_to_hand":
            # v0.82: 場からトラッシュに置かれたエネルギーカードを、持ち主の手札にもどす（リサイクルエネルギー・エコロジム）。すぐ前に同じカードをトラッシュに置いた
            # （ログから組み立てたトラッシュにある）・理由と原因が合う（リサイクルエネルギーは登録の実装、エコロジムは相手が使ったワザ・特殊能力・トレーナー）
            reasons = tuple(e["reasons"])
            definition = state.printed_def(e["card"])
            recycle = definition.is_special_energy and getattr(state.effects.energy_effect(definition), "returns_from_play", False)
            ecogym_ok = e["cause"] in ("attack", "power", "trainer") and e.get("by_player") not in (None, e["player"]) and e.get("stadium_card") is not None
            if e["card"] not in discard[e["player"]] or owner.get(e["card"]) != e["player"] or not reasons \
                    or not set(reasons) <= {"recycle_energy", "ecogym"} or ("recycle_energy" in reasons) != recycle or ("ecogym" in reasons and not ecogym_ok):
                problems.append(f"{e['turn']} 番に手札にもどしたエネルギーカード {e['card']} が、ログから組み立てたトラッシュにない・理由 {reasons}（{e['cause']}）が合わない")
            else:
                discard[e["player"]].remove(e["card"])
                hand[e["player"]].append(e["card"])
        elif kind == "return_to_hand":
            # v0.12: 「ふしちょう」でトラッシュから手札に加えたカード（きぜつしたポケモンのカード 1 枚だけ。P22〜P24）
            if e["card"] not in discard[e["player"]] or owner.get(e["card"]) != e["player"] or state.printed_def(e["card"]).category != "pokemon":
                problems.append(f"{e['turn']} 番に手札に加えたカード {e['card']} が、ログから組み立てたプレイヤー {e['player']} のトラッシュのポケモンのカードにない")
            else:
                discard[e["player"]].remove(e["card"])
                hand[e["player"]].append(e["card"])
        elif kind in ("ko_prevention_declined", "ko_prevention_declared", "ko_prevented", "ko_prevention_failed"):
            # v0.11: 相手のワザによるダメージで「きぜつ」するときに使える特殊能力（サカキのカイリキーの「こんじょう」）
            pid = e["pokemon_id"]
            if attack_window is None:
                problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）が、相手のワザのあとのきぜつの判定の中にない（G3・G7）")
                continue
            by_attacker = e["player"] == attack_window["player"]  # v0.12: 「ほのおのかべ」のダメージで HP 以上になったワザを使ったポケモン
            if pid not in in_play or ids.get(e["pokemon"]) != pid or pokemon_owner.get(pid) != e["player"] or (
                by_attacker and (pid != attack_window["pokemon_id"] or attack_window["ret"] is None)
            ):
                problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）が、相手のワザ（「ほのおのかべ」・「こうらがえし」を含む）のダメージを受けた場のポケモンではない（G4・G15）")
                continue
            gkey, geffect, gpower = guts_power(pid)
            hp = max_hp_now(pid)
            if gkey is None or gkey != e["power"]:
                problems.append(f"{e['turn']} 番の「こんじょう」の {kind} の特殊能力 {e['power']} が、ポケモン {pid} のいちばん上のカードの「こんじょう」ではない")
                continue
            if kind in ("ko_prevention_declined", "ko_prevention_declared"):
                if attack_window["ko_offer"] is not None:
                    problems.append(f"{e['turn']} 番のワザで、「こんじょう」を使うかの決定が 2 回以上（ポケモン {attack_window['ko_offer']}・{pid}。G14）")
                if attack_window["knocked"]:
                    problems.append(f"{e['turn']} 番のワザで、きぜつの処理（ポケモン {sorted(attack_window['knocked'])}）のあとに「こんじょう」の {kind} がある（G32）")
                attack_window["ko_offer"] = pid
                attack_window["ko_result"] = "declined" if kind == "ko_prevention_declined" else "declared"
                if pid not in attack_window["ko_able"]:
                    problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）の前に、そのワザのダメージを受けたログがない（G3〜G7）")
                elif attack_window["ko_able"][pid] is not None:
                    problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）: ダメージを受けるとき {attack_window['ko_able'][pid]} 状態だった（使えない。G25〜G27）")
                gases = [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(gpower)]
                if gases:
                    problems.append(f"{e['turn']} 番に、はたらいている「かがくへんかガス」（ポケモン {gases}）に消されている「こんじょう」（ポケモン {pid}）の {kind} がある（G31）")
                if damage[pid] < hp:
                    problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）: ログから組み立てたダメージ {damage[pid]} が HP {hp} 未満（G2）")
                if e["total_damage"] != damage[pid]:
                    problems.append(f"{e['turn']} 番の {kind} のダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
                continue
            coin = prior or {}
            if attack_window["ko_offer"] != pid or attack_window["ko_result"] != "declared":
                problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）の前に、そのワザでの宣言（ko_prevention_declared）がない")
            attack_window["ko_result"] = "heads" if kind == "ko_prevented" else "tails"
            if (coin.get("kind"), coin.get("source"), coin.get("player"), coin.get("pokemon_id"), coin.get("effect"), coin.get("result")) != (
                "coin_flip", "power", e["player"], pid, e["power"], e["result"]
            ) or e["result"] != attack_window["ko_result"]:
                problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）の直前に、持ち主の同じ結果のコインがない・結果が合わない（G15・G17〜G19）")
            if damage[pid] < hp:
                problems.append(f"{e['turn']} 番の「こんじょう」の {kind}（ポケモン {pid}）: ログから組み立てたダメージ {damage[pid]} が HP {hp} 未満")
            if kind == "ko_prevented":
                if e["damage_before"] != damage[pid]:
                    problems.append(f"{e['turn']} 番の ko_prevented の前のダメージ {e['damage_before']} が、ログから組み立てた {damage[pid]} と違う")
                damage[pid] = e["total_damage"]
                if e["total_damage"] != hp - geffect.remaining_hp or e.get("remaining_hp") != geffect.remaining_hp:
                    problems.append(f"{e['turn']} 番の「こんじょう」の「おもて」のあとのダメージ {e['total_damage']} が、残り HP {geffect.remaining_hp}（ダメージ {hp - geffect.remaining_hp}）ではない（G18・G20）")
            elif e["total_damage"] != damage[pid]:
                problems.append(f"{e['turn']} 番の ko_prevention_failed のダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う（「うら」はダメージを変えない。G19）")
        elif kind == "drain_heal_declined":
            # v0.72: きゅうけつ（「取りのぞいてよい」）で取りのぞかなかった。登録の実装が DamageAndOptionalFullDrain で、与えたぶんのカウンターの数・取りのぞけるカウンターがあったこと
            # （なければ決定を出さない）を確かめる。ダメージは変えない
            per = state.rules.damage_per_counter
            entry = state.effects.attack_entry(*_attack_key(e["effect"]))
            if entry is None or not isinstance(entry.effect, DamageAndOptionalFullDrain) or e["dealt"] <= 0 or e["drain_counters"] != e["dealt"] // per \
                    or damage[e["pokemon_id"]] // per <= 0:
                problems.append(f"{e['turn']} 番の drain_heal_declined（ワザ {e['effect']}・与えたダメージ {e['dealt']}）が、取りのぞいてよいワザの決定の答えと合わない")
        elif kind == "tool_heal":
            # v0.81: きのみ・おうごんのみ（ポケモンチェックの 1。ついているどうぐの登録の数だけとりのぞく。のっている数がその数以上）
            pid = e["pokemon_id"]
            per = state.rules.damage_per_counter
            effect = _trainer_effect_of(state, e["card"])
            if e["card"] not in tools_on.get(pid, ()) or not isinstance(effect, CounterBerry) or e["counters"] != effect.counters \
                    or damage[pid] < effect.counters * per:
                problems.append(f"{e['turn']} 番の tool_heal（ポケモン {pid}・カード {e['card']}）が、ついているきのみの処理と合わない")
            damage[pid] -= e["counters"] * per
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の tool_heal のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "focus_band":
            # v0.81: きあいのハチマキ（きぜつの判定の窓。持ち主のコインのすぐあと。「おもて」なら残りHP 10）
            pid = e["pokemon_id"]
            if e["card"] not in tools_on.get(pid, ()) or not isinstance(_trainer_effect_of(state, e["card"]), FocusBand) or damage[pid] < hp_of(pid) \
                    or prior is None or (prior["kind"], prior.get("source"), prior.get("card"), prior.get("result")) != ("coin_flip", "trainer", e["card"], e["result"]) \
                    or e["survived"] != (e["result"] == "heads"):
                problems.append(f"{e['turn']} 番の focus_band（ポケモン {pid}）が、HP 以上のポケモンについているきあいのハチマキのすぐ前のコインと合わない")
            if e["survived"]:
                damage[pid] = hp_of(pid) - 10
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の focus_band のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "counter_claw":
            # v0.81: はんげきのツメ（持ち主のコインのすぐあと）
            if e["card"] not in tools_on.get(e["pokemon_id"], ()) or not isinstance(_trainer_effect_of(state, e["card"]), CounterClaw) \
                    or prior is None or (prior["kind"], prior.get("source"), prior.get("card"), prior.get("result")) != ("coin_flip", "trainer", e["card"], e["result"]):
                problems.append(f"{e['turn']} 番の counter_claw（ポケモン {e['pokemon_id']}）が、ついているはんげきのツメのすぐ前のコインと合わない")
        elif kind == "tool_damage_counters":
            # v0.81: はんげきのツメの「おもて」（相手の対戦ポケモンにダメージカウンター。ダメージではない）
            target = e["target_pokemon_id"]
            per = state.rules.damage_per_counter
            if prior is None or prior["kind"] != "counter_claw" or prior["result"] != "heads" or prior["card"] != e["card"] or target not in in_play \
                    or active_of.get(e["target_player"]) != target:
                problems.append(f"{e['turn']} 番の tool_damage_counters（ポケモン {target}）が、すぐ前の「おもて」のはんげきのツメの相手の対戦ポケモンではない")
            damage[target] += e["counters"] * per
            if damage[target] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の tool_damage_counters のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[target]} と違う")
        elif kind == "tool_move_energy":
            # v0.81: 学習装置（きぜつする対戦ポケモンの基本エネルギーカードを、学習装置をつけたポケモンへ）
            source, holder = e["source_pokemon_id"], e["pokemon_id"]
            if e["card"] not in tools_on.get(holder, ()) or not isinstance(_trainer_effect_of(state, e["card"]), ExpAll) or e["energy"] not in energy.get(source, []) \
                    or not state.printed_def(e["energy"]).is_basic_energy or damage[source] < hp_of(source):
                problems.append(f"{e['turn']} 番の tool_move_energy（{source} → {holder}）が、学習装置のつけ替えと合わない")
            else:
                energy[source].remove(e["energy"])
                energy.setdefault(holder, []).append(e["energy"])
        elif kind == "exp_all_declined":
            if e["card"] not in tools_on.get(e["pokemon_id"], ()) or not isinstance(_trainer_effect_of(state, e["card"]), ExpAll):
                problems.append(f"{e['turn']} 番の exp_all_declined（ポケモン {e['pokemon_id']}）が、ついている学習装置の決定ではない")
        elif kind == "attach_trainer":
            if is_pokemon_tool_card(state, e["card"]):
                if tools_on.get(e["pokemon_id"]):
                    problems.append(f"{e['turn']} 番に、ポケモンのどうぐのついているポケモン {e['pokemon_id']} に、ポケモンのどうぐ {e['card']} をつけた")
                tools_on.setdefault(e["pokemon_id"], []).append(e["card"])
        elif kind in ("darkness_energy_damage", "darkness_energy_counters"):
            # v0.78: ポケモンチェックの悪エネルギー（ダメージ・ダメージカウンター）。ついている悪エネルギーのカードで、ダメージは 10 から鋼エネルギー（NIP1X-010）の数 × 10 を
            # 引いた数（0 より小さくしない）、ダメージカウンターは 1 個
            pid = e["pokemon_id"]
            per = state.rules.damage_per_counter
            card = state.card_def(e["energy"])
            effect = state.effects.energy_effect(card) if card.is_special_energy else None
            if e["energy"] not in energy.get(pid, ()) or effect is None or not effect.pokemon_check_penalty:
                problems.append(f"{e['turn']} 番の {kind}（ポケモン {pid}）のカード {e['energy']} が、そのポケモンについている悪エネルギーではない")
            if kind == "darkness_energy_damage":
                reducers = tuple(e.get("energy_reduction", ()))
                if any(uid not in energy.get(pid, ()) for uid in reducers) or e["amount"] != max(0, 10 - per * len(reducers)) \
                        or e.get("amount_before", 10) != 10:
                    problems.append(f"{e['turn']} 番の悪エネルギーのダメージ {e['amount']}（ポケモン {pid}）が、ついている鋼エネルギー {reducers} と合わない")
                damage[pid] += e["amount"]
            else:
                damage[pid] += e["counters"] * per
                if e["counters"] != 1:
                    problems.append(f"{e['turn']} 番の悪エネルギーのダメージカウンター {e['counters']}（ポケモン {pid}）が 1 個ではない")
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の {kind} のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "conductivity":
            # v0.86: ［かんでん］。相手プレイヤーが手札からエネルギーカードをつけたポケモンに、特殊能力のダメージ（弱点・抵抗力を計算しない。受けるダメージを変える特殊能力・
            # 鋼エネルギーは amount_before・received_modifiers）。発生源は相手の場の、はたらいている［かんでん］を持つポケモン
            pid, holder = e["target_pokemon_id"], e["pokemon_id"]
            effect = _power_effect(state, e["power"])
            if not isinstance(effect, DamageOnOpponentHandEnergyAttach) or pokemon_owner.get(pid) != e["target_player"] or pokemon_owner.get(holder) != e["player"] \
                    or e["player"] == e["target_player"] or e["energy"] not in energy.get(pid, ()) or e.get("amount_before", e["amount"]) != effect.amount:
                problems.append(f"{e['turn']} 番の［かんでん］（ポケモン {holder} → {pid}）が、相手の場のポケモンにつけたエネルギーカードへの反応と合わない")
            damage[pid] += e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の［かんでん］のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind in ("damage", "poison_damage", "confusion_damage", "drain_heal", "remove_damage_counters", "remove_all_damage_counters"):
            pid = e["pokemon_id"] if "pokemon_id" in e else ids[e["pokemon"]]
            if kind == "drain_heal":
                # v0.32: とりのぞく数は登録の実装で決まる（メガドレインは与えたダメージの半分の切り上げ、やどりぎのタネは決まった数、きゅうけつは与えたぶん）。
                # 実際にとりのぞくのは、のっている数まで
                per = state.rules.damage_per_counter
                entry = state.effects.attack_entry(*_attack_key(e["effect"]))
                effect = entry.effect if entry is not None else None
                # v0.86: ダークドレインは、相手の場のポケモンに実際に与えたダメージの合計ぶん（drain_heal の dealt）
                expected = (e["dealt"] // per if isinstance(effect, (DamageAndFullDrain, DamageAndOptionalFullDrain, CoinPerOpponentPokemonDamageThenHealDealt)) else (e["dealt"] // per + 1) // 2 if isinstance(effect, DamageAndDrain)
                            else effect.counters if isinstance(effect, DamageAndRemoveCounters) else None)
                if expected is None or e["drain_counters"] != expected or e["dealt"] <= 0 \
                        or e["counters"] != min(e["drain_counters"], damage[pid] // per) or e["amount"] != e["counters"] * per:
                    problems.append(f"{e['turn']} 番の drain_heal（ワザ {e['effect']}・与えたダメージ {e['dealt']}）のとりのぞく数 {e['drain_counters']}・{e['counters']} が"
                                    f"登録の実装 {type(effect).__name__} と合わない（ログのダメージ {damage[pid]}）")
            if kind in ("drain_heal", "remove_all_damage_counters"):
                damage[pid] -= e["amount"]
            elif kind == "remove_damage_counters":
                damage[pid] -= e["counters"] * state.rules.damage_per_counter
            else:
                damage[pid] += e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の {kind} のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "attach_energy":
            from_hand(e, e["player"], e["energy"])
            energy[ids[e["target"]]].append(e["energy"])
            attached_this_turn += 1
            if "energy2" in e:
                # v0.59: カツラの効果で、手札の「炎」エネルギーカード 2 枚を 1 回の通常の操作でつけた（この番の枚数の上限が 1 枚多い）
                from_hand(e, e["player"], e["energy2"])
                energy[ids[e["target"]]].append(e["energy2"])
                attached_this_turn += 1
                blaine_turns.add(e["turn"])
                if attached_this_turn != 2 or "trainer_card" not in e:
                    problems.append(f"{e['turn']} 番のカツラの 2 枚のつけかたが、この番の最初の通常の操作ではない・カツラのカードがない")
            if attached_this_turn > state.rules.energy_attachments_per_turn + (1 if e["turn"] in blaine_turns else 0):
                problems.append(f"{e['turn']} 番に手札からエネルギーをつける通常の操作が {attached_this_turn} 枚")
            if attached_this_turn == (2 if "energy2" in e else 1) and power_attached_this_turn:
                # v0.6 の R13（原典で決められない。エンジンは UNRESOLVED_ATTACH_AFTER_POWER_ATTACH で止める）
                problems.append(f"{e['turn']} 番に、特殊能力で手札からつけたあとで通常の操作でつけた（R13 は止めるはず）")
        elif kind == "pokemon_power":
            declared = (e["turn"], e["player"], e["pokemon_id"])
            power_card = e.get("card", top.get(e["pokemon_id"]))  # v0.49: のせたカードの特殊能力ならそのカード（ログの card）
            declared_key = f"{state.cards[power_card].card_id}@power{e['power_index']}" if power_card is not None else None
            if e["player"] != turn_player or pokemon_owner.get(e["pokemon_id"]) != e["player"] or e["pokemon_id"] not in in_play:
                problems.append(f"{e['turn']} 番の特殊能力の宣言（ポケモン {e['pokemon_id']}）が、番のプレイヤーの場のポケモンではない")
                continue
            # v0.8: 宣言した時点の場で、宣言しない特殊能力でないこと・はたらいているかがくへんかガスに消されていないこと
            definition = state.in_play_def(power_card)
            if power_card != top[e["pokemon_id"]] and disguised.get(e["pokemon_id"]) != power_card:
                problems.append(f"{e['turn']} 番の特殊能力の宣言のカード {power_card}（ポケモン {e['pokemon_id']}）が、いちばん上のカードでも「ばける」でのせたカードでもない")
            power = definition.powers[e["power_index"]] if 0 <= e["power_index"] < len(definition.powers) else None
            if power is None or power.name_ja != e["power"]:
                problems.append(f"{e['turn']} 番の特殊能力の宣言 {e['power']!r} が、ポケモン {e['pokemon_id']} のいちばん上のカードの特殊能力ではない")
                continue
            effect = state.effects.power_effect(definition.id, power)
            # v0.86: かならずはたらく反応の特殊能力（［いなびかり］。TriggeredPower の forced）も、ログ pokemon_power の forced（宣言ではない）
            forced = isinstance(effect, (EntryPower, TriggeredPower)) and effect.forced
            if forced != bool(e.get("forced")):
                # v0.85: かならずはたらく場に出たときの特殊能力（［あばれんぼう］）は、ログ pokemon_power の forced（使う機会の答えではない）
                problems.append(f"{e['turn']} 番の特殊能力「{power.name_ja}」の宣言の forced {e.get('forced')!r} が、かならずはたらく特殊能力かと合わない")
            if effect is not None and not effect.declared and not forced:
                problems.append(f"{e['turn']} 番に、常にはたらいていて宣言しない特殊能力「{power.name_ja}」の宣言がある")
            if ("entry" in e) != isinstance(effect, EntryPower):
                # v0.43: 場に出たときの特殊能力は、使う機会の答えとしてだけ宣言する（番の中の宣言（UsePokemonPower）では使えない）
                problems.append(f"{e['turn']} 番の特殊能力「{power.name_ja}」の宣言の entry {e.get('entry')!r} が、場に出たときの特殊能力かと合わない")
            gases = [pid for pid, gas in working_gases() if gas.suppresses(power)]
            if gases:
                problems.append(f"{e['turn']} 番に、はたらいている「かがくへんかガス」（ポケモン {gases}）に消されている特殊能力「{power.name_ja}」を使った")
            continue
        elif kind == "entry_power_declined":
            # v0.43: 場に出たときの特殊能力を使わなかった（使う機会の答え。番のプレイヤーの場のポケモン）
            definition = state.in_play_def(top[e["pokemon_id"]]) if e["pokemon_id"] in top else None
            power = definition.powers[e["power_index"]] if definition is not None and 0 <= e["power_index"] < len(definition.powers) else None
            if power is None or power.name_ja != e["power"] or not isinstance(state.effects.power_effect(definition.id, power), EntryPower) \
                    or e["player"] != turn_player or pokemon_owner.get(e["pokemon_id"]) != e["player"]:
                problems.append(f"{e['turn']} 番の entry_power_declined（ポケモン {e['pokemon_id']}）が、番のプレイヤーの場に出たときの特殊能力ではない")
        elif kind == "power_damage":
            # v0.43: こっそりかみつく。相手の場のポケモン 1 匹に、特殊能力によるダメージ（ワザによるダメージの計算をしない。登録の量）。HP 以上になったら、すぐあとに
            # timing power のきぜつ
            effect = _power_effect(state, e["power"])
            target = e["target_pokemon_id"]
            if not isinstance(effect, DamageOpponentPokemonOnEntry) or target not in in_play \
                    or pokemon_owner.get(target) != 1 - e["player"] or e["target_player"] != 1 - e["player"] or pokemon_owner.get(e["pokemon_id"]) != e["player"]:
                problems.append(f"{e['turn']} 番の power_damage（{e['power']} → ポケモン {target}）が、場に出たときに相手の場のポケモンにダメージを与える特殊能力の処理と合わない")
            else:
                problems.extend(received_power_problems(e, target, e["pokemon_id"], effect.amount))  # v0.46
                damage[target] += e["amount"]
                if damage[target] != e["total_damage"] or (damage[target] >= max_hp_now(target)) != e["knocked_out"]:
                    problems.append(f"{e['turn']} 番の power_damage のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[target]} と違う")
                if damage[target] >= max_hp_now(target):
                    power_ko_due = target
        elif kind in ("recover_pokemon", "recover_pokemon_none"):
            # v0.43: つりあげる。自分のトラッシュのポケモンのカード（同じカードは 1 回まで・最大 3 枚）を見せて手札に加える。加えるものがないのは、トラッシュに
            # ポケモンのカードがないときだけ
            effect = _power_effect(state, e["power"])
            player = e["player"]
            cards = tuple(e.get("cards", ()))
            if not isinstance(effect, RecoverPokemonFromDiscardOnEntry) or pokemon_owner.get(e["pokemon_id"]) != player:
                problems.append(f"{e['turn']} 番の {kind} の特殊能力 {e['power']} が、トラッシュのポケモンのカードを手札に加える特殊能力ではない")
            elif kind == "recover_pokemon_none":
                if any(state.printed_def(uid).category == "pokemon" for uid in discard[player]):
                    problems.append(f"{e['turn']} 番の recover_pokemon_none のとき、ログから組み立てたトラッシュにポケモンのカードがある")
            elif not 1 <= len(cards) <= effect.max_cards or len(set(cards)) != len(cards) or any(
                    uid not in discard[player] or owner.get(uid) != player or state.printed_def(uid).category != "pokemon" for uid in cards):
                problems.append(f"{e['turn']} 番に手札に加えたカード {cards} が、ログから組み立てたトラッシュのポケモンのカード（最大 {effect.max_cards} 枚）ではない")
            else:
                for uid in cards:
                    discard[player].remove(uid)
                    hand[player].append(uid)
        elif kind == "special_condition_prevented" and "persistent_effect" in e:
            # v0.84: 「きらめきタッチ」の効果（持続する効果）で特殊状態にならなかった。バトル場のポケモンで、その時点で同じポケモンに効果がある（与えたログがあり、
            # そのあとに消したログがない）
            if not is_active(e["pokemon_id"]) or e["condition"] not in ("poison", "sleep", "paralysis", "confusion") \
                    or pokemon_owner.get(e["pokemon_id"]) != e["player"] or not _persistent_effect_live(state, e):
                problems.append(f"{e['turn']} 番の special_condition_prevented（ポケモン {e['pokemon_id']}・{e['persistent_effect']}）が、効果のあるバトル場のポケモンではない")
        elif kind == "special_condition_prevented":
            # v0.46: ［めんえき］で特殊状態にならなかった（状態は変わらない）。バトル場のポケモンで、その時点ではたらいている特殊能力
            powers = [key for key, _, _ in working_continuous(e["pokemon_id"], SpecialConditionImmunity)]
            if not is_active(e["pokemon_id"]) or e["power"] not in powers or e["condition"] not in ("poison", "sleep", "paralysis", "confusion") \
                    or pokemon_owner.get(e["pokemon_id"]) != e["player"]:
                problems.append(f"{e['turn']} 番の special_condition_prevented（ポケモン {e['pokemon_id']}・{e['power']}）が、はたらいている［めんえき］を持つバトル場のポケモンではない")
        elif kind == "attach_energy_from_hand":
            # v0.46: せいちょう。コインの「おもて」のあと、ワザを使ったプレイヤーの手札の、登録のタイプの基本エネルギーカード（1〜最大枚数）をワザを使ったポケモンにつける
            # （手札からつける通常の操作・特殊能力でつけた枚数には数えない）
            effect = _effect_of_event(state, e) if attack_window is not None else None
            cards = tuple(e["cards"])
            heads = prior is not None and prior["kind"] == "coin_flip" and prior["source"] == "attack" and prior["result"] == "heads"
            if not isinstance(effect, AttachEnergyFromHandOnHeads) or e["pokemon_id"] != attack_window["pokemon_id"] or e["player"] != attack_window["player"] \
                    or not heads or not 1 <= len(cards) <= effect.max_cards or len(set(cards)) != len(cards) \
                    or any(not state.printed_def(uid).is_basic_energy or state.printed_def(uid).provides is not effect.energy_type for uid in cards):
                problems.append(f"{e['turn']} 番の attach_energy_from_hand（{cards}）が、コインの「おもて」のあとに手札の基本エネルギーカードをつけるワザの処理と合わない")
            for uid in cards:
                from_hand(e, e["player"], uid)
                energy.setdefault(e["pokemon_id"], []).append(uid)
        elif kind == "special_condition":
            # v0.8: ねむり・マヒ・こんらんは重複しない（ほかのものは、その前に special_conditions_removed（replaced）で消える）
            if e["condition"] in ("sleep", "paralysis", "confusion") and not e.get("already"):
                if e["pokemon_id"] in exclusive:
                    problems.append(f"{e['turn']} 番に、{exclusive[e['pokemon_id']]} のポケモン {e['pokemon_id']} が、それを消さずに {e['condition']} になった")
                exclusive[e["pokemon_id"]] = e["condition"]
            if e["condition"] == "poison":
                problems.extend(_poison_problems(state, e, poisoned.get(e["pokemon_id"])))
                poisoned[e["pokemon_id"]] = e.get("damage")
        elif kind == "special_conditions_removed":
            if exclusive.get(e["pokemon_id"]) in e["conditions"]:
                del exclusive[e["pokemon_id"]]
            if "poison" in e["conditions"]:
                poisoned.pop(e["pokemon_id"], None)
        elif kind == "poison_damage":
            # v0.34: ポケモンチェックのどくのダメージは、そのポケモンのどくの量（通常 10・特殊などくはその量。p.322・p.323）
            # 盤面を直接作ったテスト（build_test_state）は、どく状態にしたログがないので、ログで組み立てたどくだけを確かめる
            if e["pokemon_id"] in poisoned and poisoned[e["pokemon_id"]] != e.get("amount_before", e["amount"]):  # v0.78: 鋼エネルギー（NIP1X-010）で減らす前の量
                problems.append(f"{e['turn']} 番のポケモン {e['pokemon_id']} のどくのダメージ {e['amount']} が、ログから組み立てたどくの量 {poisoned.get(e['pokemon_id'])} と違う")
        elif kind == "energy_conversion":
            # v0.59: ［エネエネ］できぜつしたマルマインのカード（直前のきぜつの to_energy）を、使ったプレイヤーの場のほかのポケモンにエネルギーとしてつける
            kept = pending_conversion.pop(e["card"], None)
            target = e["target_pokemon_id"]
            if kept != (e["player"], e["pokemon_id"]) or target not in in_play or pokemon_owner.get(target) != e["target_player"] \
                    or e["target_player"] != e["player"] or e.get("units") != 2:
                problems.append(f"{e['turn']} 番の［エネエネ］のつけかた（カード {e['card']} → ポケモン {target}）が、ログから組み立てた直前のきぜつ・場と合わない")
            else:
                energy[target].append(e["card"])
                converted_units[e["card"]] = e["units"]
        elif kind == "move_energy":
            # v0.5: 特殊能力（エナジートランス）で、同じ uid のエネルギーを移動元から移動先へ（トラッシュには置かない）
            effect = _power_effect(state, e.get("power"))
            continuing = moving is not None and moving[:4] == (e["turn"], e["player"], e["pokemon_id"], e.get("power"))
            if declared != (e["turn"], e["player"], e["pokemon_id"]) and not continuing:
                problems.append(f"{e['turn']} 番のエネルギーの移動 {e['energy']} の直前に、同じポケモンの特殊能力の宣言（pokemon_power）がない")
            declared = None  # 1 回の宣言で 1 枚（v0.5 のエナジートランス）
            if isinstance(effect, (TakeEnergiesToSelf, ChargeBenchEnergyToSelf, GatherTypeEnergyCardsToSelf)):
                # v0.43: ようぶんきゅうしゅう（最大 2 枚）・エナジーチャージ（好きなだけ）は 1 回の宣言で何枚も（続けて move_energy）
                moving = (e["turn"], e["player"], e["pokemon_id"], e.get("power"), moving[4] + 1 if continuing else 1)
                if isinstance(effect, (TakeEnergiesToSelf, GatherTypeEnergyCardsToSelf)) and moving[4] > effect.max_cards:
                    problems.append(f"{e['turn']} 番のようぶんきゅうしゅう（ポケモン {e['pokemon_id']}）で、1 回に {moving[4]} 枚つけかえた")
            source, target = e["from_pokemon_id"], e["to_pokemon_id"]
            if isinstance(effect, (TakeEnergyToSelf, TakeEnergiesToSelf, ChargeBenchEnergyToSelf, GatherTypeEnergyCardsToSelf)) and (
                    target != e["pokemon_id"] or not state.printed_def(e["energy"]).is_basic_energy or state.printed_def(e["energy"]).provides is not effect.energy_type):
                # v0.43: つける先は特殊能力を使ったポケモン（このカード）。つけかえるのは登録のタイプの基本エネルギーカード
                problems.append(f"{e['turn']} 番のエネルギーの移動 {e['energy']}（{source} → {target}）が、特殊能力 {e.get('power')} のつけかえ（このカードに・"
                                "登録のタイプの基本エネルギーカード）ではない")
            if pokemon_owner.get(source) != e["player"] or pokemon_owner.get(target) != e["player"] or owner.get(e["energy"]) != e["player"]:
                problems.append(f"{e['turn']} 番のエネルギーの移動 {e['energy']}（{source} → {target}）が、自分の場のポケモンのあいだではない")
            if source == target or source not in in_play or target not in in_play or e["energy"] not in energy.get(source, []):
                problems.append(f"{e['turn']} 番のエネルギーの移動 {e['energy']}（{source} → {target}）が、ログから組み立てた場と合わない")
            else:
                energy[source].remove(e["energy"])
                energy[target].append(e["energy"])
        elif kind == "power_attach_energy":
            # v0.6: 特殊能力（あまごい）で、手札の同じ uid のエネルギーカードを自分の場のポケモンへ
            if declared != (e["turn"], e["player"], e["pokemon_id"]):
                problems.append(f"{e['turn']} 番の手札からのエネルギー {e['energy']} の直前に、同じポケモンの特殊能力の宣言（pokemon_power）がない")
            declared = None  # 1 回の宣言で 1 枚（v0.6 のあまごい。実装上の仮定）
            target = e["to_pokemon_id"]
            power_attached_this_turn += 1
            if pokemon_owner.get(target) != e["player"] or owner.get(e["energy"]) != e["player"] or target not in in_play:
                problems.append(f"{e['turn']} 番の手札からのエネルギー {e['energy']}（→ {target}）が、自分のカードを自分の場のポケモンにつけていない")
                continue
            from_hand(e, e["player"], e["energy"])
            energy[target].append(e["energy"])
            card_id, _, index = e["power"].partition("@power")
            entry = state.effects.power_entry(card_id, int(index)) if index.isdigit() else None
            effect = None if entry is None else entry.effect
            if effect is None or not hasattr(effect, "energy_type"):
                problems.append(f"{e['turn']} 番の手札からのエネルギー {e['energy']} の特殊能力 {e['power']} が、手札からつける特殊能力として登録されていない")
            else:
                if state.printed_def(e["energy"]).provides is not effect.energy_type:
                    problems.append(f"{e['turn']} 番の手札からのエネルギー {e['energy']} が「{effect.energy_type.ja}」エネルギーではない")
                if effect.pokemon_type not in type_readings_now(target):  # v0.49: 今の姿・今有効な色
                    problems.append(f"{e['turn']} 番の手札からのエネルギー {e['energy']} のつける先 {target} が「{effect.pokemon_type.ja}」ポケモンではない")
        elif kind == "move_damage_counter":
            # v0.7: 特殊能力（ダメージスワップ）で、自分の場のポケモンのダメージカウンターを、自分の場の別のポケモンへ（1 回に 1 個）
            if declared != (e["turn"], e["player"], e["pokemon_id"]):
                problems.append(f"{e['turn']} 番のダメージカウンターの移動の直前に、同じポケモンの特殊能力の宣言（pokemon_power）がない")
            declared = None  # 1 回の宣言で 1 個（v0.7 のダメージスワップ。実装上の仮定）
            source, target, count = e["from_pokemon_id"], e["to_pokemon_id"], e["count"]
            card_id, _, index = e["power"].partition("@power")
            entry = state.effects.power_entry(card_id, int(index)) if index.isdigit() else None
            # v0.42: へんなこうどう（MoveDamageCounterToSelf。移動先は使ったポケモン）・のろい（MoveOpponentDamageCounter。相手の場のポケモンのあいだ。
            # ログの owner は相手。説明に「きぜつ」しない範囲の条件がないので、移動先が HP 以上になってよい（すぐあとにきぜつ））
            movers = (MoveDamageCounter, MoveDamageCounterToSelf, MoveOpponentDamageCounter)
            effect = None if entry is None else entry.effect
            if not isinstance(effect, movers) or state.cards[top[e["pokemon_id"]]].card_id != card_id:
                problems.append(f"{e['turn']} 番のダメージカウンターの移動の特殊能力 {e['power']} が、使ったポケモンのダメージカウンターを移す特殊能力ではない")
            if count != 1:
                problems.append(f"{e['turn']} 番のダメージカウンターの移動が 1 回に {count} 個（1 個のはず）")
            side = e.get("owner", e["player"])
            if isinstance(effect, MoveOpponentDamageCounter) != (side != e["player"]) or (
                    isinstance(effect, MoveDamageCounterToSelf) and target != e["pokemon_id"]):
                problems.append(f"{e['turn']} 番のダメージカウンターの移動（{source} → {target}・owner {e.get('owner')}）が、特殊能力 {e['power']} の移す場所と合わない")
            if pokemon_owner.get(source) != side or pokemon_owner.get(target) != side:
                problems.append(f"{e['turn']} 番のダメージカウンターの移動（{source} → {target}）が、{'自分' if side == e['player'] else '相手'}の場のポケモンのあいだではない")
            if source == target or source not in in_play or target not in in_play:
                problems.append(f"{e['turn']} 番のダメージカウンターの移動（{source} → {target}）が、ログから組み立てた場と合わない")
                continue
            amount = count * state.rules.damage_per_counter
            if damage[source] < amount:
                problems.append(f"{e['turn']} 番のダメージカウンターの移動元 {source} に、ログから組み立てたダメージ {damage[source]} しかない")
            damage[source] -= amount
            damage[target] += amount
            if (damage[source], damage[target]) != (e["from_total_damage"], e["to_total_damage"]):
                problems.append(
                    f"{e['turn']} 番のダメージカウンターの移動のあとのダメージ {(e['from_total_damage'], e['to_total_damage'])} が、ログから"
                    f"組み立てた {(damage[source], damage[target])} と違う"
                )
            if damage[target] >= max_hp_now(target):
                if isinstance(effect, MoveOpponentDamageCounter):
                    power_ko_due = target  # v0.42: のろいのあとの「きぜつ」（すぐあとに timing power のきぜつ）
                else:
                    problems.append(f"{e['turn']} 番のダメージカウンターの移動で、移動先 {target} がきぜつするダメージ {damage[target]} になった")
        elif kind == "discard_energy":
            # v0.7: ワザ（じこさいせい）で、ワザを使ったポケモンについているエネルギーカードをトラッシュ
            pid = e["pokemon_id"]
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or e["energy"] not in energy.get(pid, []):
                problems.append(f"{e['turn']} 番のエネルギーのトラッシュ {e['energy']} が、ログから組み立てたポケモン {pid} のエネルギーにない")
            else:
                energy[pid].remove(e["energy"])
                discard[e["player"]].append(e["energy"])
        elif kind == "recover_energy":
            # v0.9: ワザ（エナジーへんかん）で、ワザを使ったプレイヤーのトラッシュのエネルギーカードを手札に加える
            if attack_window is None or e["pokemon_id"] != attack_window["pokemon_id"] or e["player"] != attack_window["player"]:
                problems.append(f"{e['turn']} 番のトラッシュから手札に加えたエネルギー {e['cards']} が、そのポケモンのワザの処理の中にない")
            for uid in e["cards"]:
                if uid not in discard[e["player"]] or state.printed_def(uid).category != "energy":
                    problems.append(f"{e['turn']} 番に手札に加えたカード {uid} が、ログから組み立てたプレイヤー {e['player']} のトラッシュのエネルギーカードにない")
                    continue
                discard[e["player"]].remove(uid)
                hand[e["player"]].append(uid)
        elif kind in ("retreat", "retreat_failed"):
            pid = e["pokemon_id"] if kind == "retreat_failed" else ids[e["old_active"]]
            # v0.46: トラッシュしたエネルギーの数は、印刷の数に、ログから組み立てた場ではたらく［ねんちゃくえき］（相手のバトル場。決まって増やす）・［にげるサポート］
            # （自分のベンチ。少なくできる）を当てはめた範囲（最後に 0 で下限）。少なくしてから 0 で止める読み方と答えが変わる数は CP2 で止まる
            printed = form_def(pid).retreat_cost  # v0.49: 今の姿のカードのにげるエネルギー
            increases = sorted((hpid, key, eff.amount) for hpid in in_play if pokemon_owner.get(hpid) != e["player"]
                               for key, eff, _ in working_continuous(hpid, IncreaseOpponentActiveRetreatCost))
            reductions = sorted((hpid, key, eff.amount) for hpid in in_play if pokemon_owner.get(hpid) == e["player"]
                                for key, eff, _ in working_continuous(hpid, ReduceOwnActiveRetreatCost))
            # v0.57: 場のスタジアム（ロケット団の特訓ジムは決まって + 1、ハナダシティジムは「カスミのポケモン」なら決まって − 1）。ログから組み立てた場のスタジアムと、
            # にげるポケモンの今の姿の名前で求める（エンジンの ``retreat_cost`` とは別に）
            stadium_terms: list[tuple[int, int]] = []
            if stadium_zone is not None:
                stadium_effect = _trainer_effect_of(state, stadium_zone[0])
                if isinstance(stadium_effect, ActiveRetreatIncreaseStadium):
                    stadium_terms.append((stadium_zone[0], stadium_effect.amount))
                elif isinstance(stadium_effect, OwnerRetreatReductionStadium) and form_def(pid).name_ja.startswith(f"{stadium_effect.owner}の"):
                    stadium_terms.append((stadium_zone[0], -stadium_effect.amount))
                elif isinstance(stadium_effect, BasicRetreatIncreaseStadium) and form_def(pid).stage == "basic":
                    stadium_terms.append((stadium_zone[0], stadium_effect.amount))  # v0.81: でこぼこジム（今の姿の段階が「たね」）
            plus = sum(x[2] for x in increases) + sum(a for _, a in stadium_terms if a > 0)
            forced = -sum(a for _, a in stadium_terms if a < 0)
            optional = sum(x[2] for x in reductions)
            maximum = max(0, printed + plus - forced)
            minimum = max(0, printed + plus - forced - optional)
            first_max = max(0, printed - forced) + plus
            first_min = max(0, printed - forced - optional) + plus
            floor_first = first_min
            # v0.58: トラッシュしたエネルギーの個数（無色2個エネルギーは 1 枚で 2 個。カードの枚数ではない）。登録の特殊エネルギーの実装で数える
            # v0.59: ［エネエネ］でエネルギーとしてついていたカードは、ログの energy_conversion の個数
            count = sum(converted_units[u] if u in converted_units else
                        len(state.effects.energy_effect(state.printed_def(u)).units()) if state.printed_def(u).is_special_energy else 1
                        for u in e["discarded"])
            last_ok, first_ok = minimum <= count <= maximum, first_min <= count <= first_max
            # v0.81: ふうせんのみ（ログから組み立てたついているどうぐ）。「すべてなくなる」を当てはめる読み方（エンジンの ``RetreatCost.readings``）のどれでも正しい数（CP2 で
            # 止める数は宣言しない）
            zeroed = tuple(c for c in tools_on.get(pid, ()) if isinstance(_trainer_effect_of(state, c), BalloonBerry))
            if zeroed:
                readings = RetreatCost(printed, tuple(increases), tuple(reductions), tuple((c, a) for c, a in stadium_terms if a > 0),
                                       tuple((c, -a) for c, a in stadium_terms if a < 0), zeroed)
                last_ok = first_ok = all(low <= count <= high for low, high in readings.readings)
                minimum, maximum = readings.minimum, readings.maximum
            if tuple(e.get("retreat_cost_zeroed", ())) != zeroed:
                problems.append(f"{e['turn']} 番の{kind}のふうせんのみの記録 {e.get('retreat_cost_zeroed')} が、ログから組み立てたついているふうせんのみ {zeroed} と違う")
            if not is_active(pid) or not last_ok or not first_ok:
                problems.append(f"{e['turn']} 番の{kind}（ポケモン {pid}）でトラッシュした {count} 個が、にげるエネルギーの範囲 {minimum}〜{maximum}"
                                f"（印刷 {printed}・増やす {increases}・少なくできる {reductions}。CP2 の下限 {floor_first}）にない")
            if tuple(tuple(x) for x in e.get("retreat_cost_stadium", ())) != tuple(stadium_terms):
                problems.append(f"{e['turn']} 番の{kind}のスタジアムのにげるエネルギーの記録 {e.get('retreat_cost_stadium')} が、ログから組み立てた {stadium_terms} と違う")
            if increases or reductions or stadium_terms or zeroed:
                if (tuple(e.get("retreat_cost", ())), e.get("retreat_cost_printed"), sorted(tuple(x) for x in e.get("retreat_cost_increases", ())),
                        sorted(tuple(x) for x in e.get("retreat_cost_reductions", ()))) != ((minimum, maximum), printed, increases, reductions):
                    problems.append(f"{e['turn']} 番の{kind}のにげるエネルギーの記録が、ログから組み立てた範囲 {minimum}〜{maximum}・{increases}・{reductions} と違う")
            elif any(field in e for field in ("retreat_cost", "retreat_cost_printed", "retreat_cost_increases", "retreat_cost_reductions")):
                problems.append(f"{e['turn']} 番の{kind}に、はたらく特殊能力がないのに、にげるエネルギーの記録がある")
            if kind == "retreat":
                active_of[e["player"]] = ids[e["new_active"]]
                if pid in shifts:
                    shifts[pid]["returned"] = True  # v0.48: ［へんしょく］を使ってからベンチにもどった
            for (effect_pid, _), info in alive.items():
                # v0.36: 「アイスバーン」・「わしづかみ」を受けたポケモンは、はたらく番に「にげる」を宣言しない（エネルギーのトラッシュ・コインの前に拒否）
                if effect_pid == pid and info["kind"] == CannotRetreat.kind and info["active_turn"] == e["turn"]:
                    problems.append(f"{e['turn']} 番に、「にげる」ことができないポケモン {pid} が「にげる」を宣言した（{kind}）")
            for uid in e["discarded"]:
                energy[pid].remove(uid)
                discard[e["player"]].append(uid)
        elif kind == "discard_hand":
            # v0.19: トレーナー（オーキドはかせ）の効果で、手札をすべてトラッシュする。使っているカードは手札から出ている（p.310）
            if sorted(e["cards"]) != sorted(hand[e["player"]]):
                problems.append(f"{e['turn']} 番にトラッシュした手札 {e['cards']} が、ログから組み立てたプレイヤー {e['player']} の手札と違う")
            discard[e["player"]].extend(e["cards"])
            hand[e["player"]] = []
        elif kind == "discard_from_hand":
            # v0.22: トレーナー（パソコン通信）の使うための条件で、手札から選んだカードをトラッシュする（手札の並びの順。使っているカードは
            # 手札から出ている。p.310）
            if len(set(e["cards"])) != len(e["cards"]):
                problems.append(f"{e['turn']} 番にトラッシュした手札 {e['cards']} に同じカードが 2 回ある")
            for uid in e["cards"]:
                from_hand(e, e["player"], uid)
                discard[e["player"]].append(uid)
            if "power" in e and isinstance(_power_effect(state, e["power"]), DiscardTypeEnergyFromHand):
                # v0.85: ［どしゃぶり］。手札の「水」の基本エネルギーカードを 1 枚トラッシュした（引かない）
                definition = state.printed_def(e["cards"][0]) if len(e["cards"]) == 1 else None
                if definition is None or not definition.is_basic_energy or definition.provides is not _power_effect(state, e["power"]).energy_type:
                    problems.append(f"{e['turn']} 番の［どしゃぶり］でトラッシュした手札 {e['cards']} が、「水」エネルギーカード 1 枚ではない")
            elif "power" in e:
                # v0.42: 特殊能力（ぶっしつこうかん）で手札を 1 枚トラッシュした。すぐあとに 1 枚まで引く（トレーナーを使うためのトラッシュではない）
                if len(e["cards"]) != 1 or not isinstance(_power_effect(state, e["power"]), DiscardThenDraw):
                    problems.append(f"{e['turn']} 番の特殊能力 {e['power']} でトラッシュした手札 {e['cards']} が、1 枚トラッシュする特殊能力の処理と合わない")
                draw_due = (e["player"], 1, e["turn"], "discard_from_hand（特殊能力）")
            else:
                trainer_discarded[e["player"]] = tuple(e["cards"])
        elif kind == "retrieve_energy":
            # v0.23: トレーナー（エネルギー回収）の効果で、自分のトラッシュの基本エネルギーカード（最大 2 枚）を手札に加える。このカードを使う
            # ためにトラッシュしたカードは選べない（p.257）
            # v0.73: 超エネルギー回収（SuperEnergyRetrieval）は最大 4 枚。最大の枚数は使っている最中のトレーナーの登録（retrieve）で決める
            retriever = _trainer_effect_of(state, using_trainer[e["player"]]) if using_trainer.get(e["player"]) is not None else None
            limit = retriever.retrieve if isinstance(retriever, DiscardFromHandThenRetrieveEnergy) else 2
            if not 1 <= len(e["cards"]) <= limit or len(set(e["cards"])) != len(e["cards"]):
                problems.append(f"{e['turn']} 番にトラッシュから手札に加えた基本エネルギーカード {e['cards']} の枚数・重複が合わない")
            for uid in e["cards"]:
                if uid not in discard[e["player"]] or owner.get(uid) != e["player"] or not state.printed_def(uid).is_basic_energy:
                    problems.append(f"{e['turn']} 番に手札に加えたカード {uid} が、ログから組み立てたプレイヤー {e['player']} のトラッシュの基本エネルギーカードにない")
                    continue
                if uid in trainer_discarded[e["player"]]:
                    problems.append(f"{e['turn']} 番に、このカードを使うためにトラッシュしたカード {uid} を手札に加えた（p.257）")
                discard[e["player"]].remove(uid)
                hand[e["player"]].append(uid)
        elif kind == "return_to_deck":
            # v0.24: トレーナー（ポケモン交換おじさん）の使うための条件で、手札のたねポケモン・進化カードを相手に見せてから山札にもどす（p.259）
            uid = e["card"]
            # v0.80: エネルギー増幅装置は、手札のエネルギーカード（基本・特殊）を見せて山札にもどす
            amplifier = isinstance(_trainer_effect_of(state, using_trainer[e["player"]]), ReturnHandEnergyThenCoinSearchBasicEnergy) \
                if using_trainer.get(e["player"]) is not None else False
            if owner.get(uid) != e["player"] or not (state.printed_def(uid).is_basic_pokemon or state.printed_def(uid).is_evolution_pokemon
                                                     or amplifier and state.printed_def(uid).category == "energy"):
                problems.append(f"{e['turn']} 番に山札にもどしたカード {uid} が、プレイヤー {e['player']} のたねポケモン・進化カードではない")
            from_hand(e, e["player"], uid)
        elif kind == "reveal_from_deck":
            # v0.24: トレーナー（ポケモン交換おじさん）の効果で、山札のたねポケモン・進化カードを相手に見せてから手札に加える（p.259。山札に
            # もどしたカードを選んでもよい）
            uid = e["card"]
            definition = state.printed_def(uid)
            # v0.44: おつかい（SearchTrainerOnHeads）はトレーナーカード、てじな（ReturnHandThenRevealBasicEnergy）は基本エネルギーカードを見せて手札に加える
            revealer = _effect_of_event(state, e) if "effect" in e else None
            trainer_effect = None if revealer is not None or "power" in e or using_trainer.get(e["player"]) is None \
                else _trainer_effect_of(state, using_trainer[e["player"]])
            if isinstance(trainer_effect, (SearchDeckTrainer, SearchNamedFromDeckOrDiscard)):
                kind_ok = trainer_effect.target.matches(definition)  # v0.53: 説明の種類のカード（モンスターボール・ボスのやりかた など）。v0.73: 化石の発掘
            elif isinstance(trainer_effect, (CoinsSearchBasicEnergyPerHeads, ReturnHandEnergyThenCoinSearchBasicEnergy)):
                kind_ok = definition.is_basic_energy  # v0.80: エネルギーアーク・エネルギー増幅装置
            elif isinstance(trainer_effect, LookTopTakeTrainerThenShuffleLock):
                kind_ok = definition.category == "trainer"  # v0.80: ポケモンギア（見た 7 枚のうちのトレーナーカード）
            elif isinstance(trainer_effect, RevealDeckTopTakeSameNamed):
                kind_ok = True  # v0.80: スロットゲーム（見せた 3 枚のうちの同じ名前のカード。並びは reveal_deck_top と照らさない）
            elif isinstance(trainer_effect, LookTopTakePokemonThenShuffle):
                kind_ok = definition.is_basic_pokemon or definition.is_evolution_pokemon  # v0.73: マスターボール（見た 7 枚のうちのポケモンのカード）
            elif isinstance(revealer, (SearchTrainerOnHeads, SearchTrainerRequiredOnHeads)):
                kind_ok = definition.category == "trainer"  # v0.79: ひらめく（SearchTrainerRequiredOnHeads。ちょうど 1 枚）も
            elif isinstance(revealer, (ReturnHandThenRevealBasicEnergy, RevealBasicEnergyFromDeck, EachPlayerLookTopTakeBasicEnergy)):
                kind_ok = definition.is_basic_energy  # v0.72: おつきみ（RevealBasicEnergyFromDeck）も基本エネルギーカード
            elif isinstance(revealer, RevealNamedPokemonFromDeckAny):
                kind_ok = definition.category == "pokemon" and definition.name_ja in revealer.names  # v0.75: くらげのむれ（名前の完全一致）
            else:
                kind_ok = definition.is_basic_pokemon or definition.is_evolution_pokemon
            if owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]] or not kind_ok:
                problems.append(f"{e['turn']} 番に山札から見せて手札に加えたカード {uid} が、プレイヤー {e['player']} の山札のたねポケモン・進化カード"
                                "（おつかいならトレーナー、てじな・おつきみなら基本エネルギーカード）ではない")
            if "power" in e:
                # v0.43: しんかのひかり。山札の進化カードを見せて手札に加え、すぐあとに山札を切る
                if not isinstance(_power_effect(state, e["power"]), SearchEvolutionCardToHand) or not state.printed_def(uid).is_evolution_pokemon:
                    problems.append(f"{e['turn']} 番に特殊能力 {e['power']} で山札から見せて手札に加えたカード {uid} が、しんかのひかりの進化カードではない")
                shuffle_due = e
            hand[e["player"]].append(uid)
        elif kind == "search_deck":
            # v0.22: トレーナー（パソコン通信）の効果で、自分の山札から選び出したカードを手札に加える（「カードを引く」ではない。p.260・p.312）
            uid = e["card"]
            if owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]]:
                problems.append(f"{e['turn']} 番に山札から手札に加えたカード {uid} が、プレイヤー {e['player']} の山札のカードではない（持ち主・手札・トラッシュ）")
            if "power" in e:
                # v0.44: ［ボスをよぶ］。山札の説明の名前のトレーナーカードを手札に加え、すぐあとに山札を切る
                effect = _power_effect(state, e["power"])
                if not isinstance(effect, SearchNamedTrainerOnEntry) or state.printed_def(uid).name_ja != effect.name or state.printed_def(uid).category != "trainer":
                    problems.append(f"{e['turn']} 番に特殊能力 {e['power']} で山札から手札に加えたカード {uid} が、説明の名前のトレーナーカードではない")
                shuffle_due = e
            hand[e["player"]].append(uid)
        elif kind == "evolution_permission":
            # v0.44: トレーナー「サカキ」。使っている最中のそのトレーナーの効果で、使ったプレイヤー（番のプレイヤー）の場の、説明の名前の持ち主のポケモンに許可を与える
            pid = e["pokemon_id"]
            entry = state.effects.trainer_entry(state.cards[e["trainer"]].card_id) if e.get("trainer") in state.cards else None
            effect = None if entry is None else entry.effect
            if not isinstance(effect, EvolutionPermissionForOwnerPokemon) or using_trainer.get(e["player"]) != e["trainer"] or e["player"] != turn_player \
                    or pid not in in_play or pokemon_owner.get(pid) != e["player"] or ids.get(e["pokemon"]) != pid \
                    or not state.in_play_def(e["pokemon"]).name_ja.startswith(f"{effect.owner}の") or e["turn"] <= 2 or (pid, e["turn"]) in permitted:
                problems.append(f"{e['turn']} 番のサカキの許可（ポケモン {pid}）が、使っている最中のサカキの効果・自分の場のサカキのポケモンのものではない")
            permitted.add((pid, e["turn"]))
        elif kind == "once_attack_recorded":
            # v0.44: 場に出てから 1 度しか使えないワザ。ワザの宣言（attack）のすぐあとに、そのポケモン・そのワザの記録。同じ場のポケモンの同じカードのワザは 1 回だけ
            pid = e["pokemon_id"]
            entry = state.effects.attack_entry(_attack_card_id(state, e), e["attack_index"]) if e["pokemon"] in state.cards else None
            if prior is None or prior["kind"] != "attack" or prior["pokemon"] != e["pokemon"] or prior["attack_index"] != e["attack_index"] \
                    or prior["player"] != e["player"] or entry is None or not entry.effect.once_after_entering_play or ids.get(e["pokemon"]) != pid:
                problems.append(f"{e['turn']} 番の 1 度だけ使えるワザの記録（ポケモン {pid}）が、そのワザの宣言のすぐあとにない")
            if (pid, e["pokemon"], e["attack_index"]) in once_used:
                problems.append(f"{e['turn']} 番に、場のポケモン {pid} が 1 度しか使えないワザ {e['attack_index']} をもう一度使った")
            once_used.add((pid, e["pokemon"], e["attack_index"]))
        elif kind == "hand_to_deck" and "trainer_card" in e:
            # v0.53: エリカのお付き（使うための条件）・メンテナンス。使っている最中のそのトレーナーで、手札のカードを見せずに山札にもどす（山札は組み立て直さない）
            # v0.54: にせオーキドはかせ・にせオーキドの逆襲（相手の手札）・ギャンブラー・ナツメの眼（両方）。もどすのは手札のすべて
            trainer_effect = _trainer_effect_of(state, e["trainer_card"])
            user = trainer_user(e["trainer_card"])
            if using_trainer.get(user) != e["trainer_card"] \
                    or not (isinstance(trainer_effect, (SearchDeckTrainer, ReturnHandToDeckThenDraw)) and e["player"] == user
                            # v0.80: ウツギはかせ（手札のすべて）・クルミ（引いたあとの手札から 2 枚）
                            or isinstance(trainer_effect, ReturnHandDrawThenHandLock) and e["player"] == user and sorted(e["cards"]) == sorted(hand[user])
                            or isinstance(trainer_effect, DrawThenReturnHandCardsToDeck) and e["player"] == user and len(e["cards"]) == trainer_effect.count
                            or isinstance(trainer_effect, RockPaperScissorsRefreshHand) and duel_winner.get(e["trainer_card"]) == e["player"]
                            and sorted(e["cards"]) == sorted(hand[e["player"]])  # v0.66: カスミの勝負（じゃんけんに勝ったプレイヤーの手札のすべて）
                            or isinstance(trainer_effect, ReturnHandsToDeckTrainer) and not trainer_effect.reveal
                            and e["player"] in {"self": (user,), "opponent": (1 - user,), "both": (0, 1)}[trainer_effect.who]
                            and sorted(e["cards"]) == sorted(hand[e["player"]])):
                problems.append(f"{e['turn']} 番に手札から山札にもどしたカード {e['cards']} が、使っている最中のトレーナーの処理のものではない")
            for uid in e["cards"]:
                from_hand(e, e["player"], uid)
        elif kind in ("look_at_deck_top", "look_at_deck_top_none", "look_at_deck_top_declined") and "stadium_card" in e:
            # v0.80: ラジオとう（場のスタジアムを、自分の番に使ったプレイヤーが自分の山札の上を見る。順番を変えない）
            if not isinstance(_trainer_effect_of(state, e["stadium_card"]), LookDeckTopStadium) or e["player"] != e["owner"] \
                    or kind == "look_at_deck_top" and not 1 <= e["count"] <= 2:
                problems.append(f"{e['turn']} 番の {kind} が、ラジオとうの処理のものではない")
        elif kind in ("reveal_hand", "revealed_hand_to_deck", "look_at_hand", "trainer_draw_declined", "trainer_discard_declined", "look_at_deck_top_declined") \
                or kind in ("look_at_deck_top", "look_at_deck_top_none") and "trainer_card" in e:
            # v0.54: 使っている最中のトレーナー（ミニスカート・スパイ作戦・エリカ・スパイ作戦／カツラのギャンブル・ポケモン図鑑）の処理
            trainer_effect = _trainer_effect_of(state, e["trainer_card"])
            user = trainer_user(e["trainer_card"])
            expected = {"reveal_hand": (ReturnHandsToDeckTrainer, SearchDeckTrainer), "revealed_hand_to_deck": ReturnHandsToDeckTrainer,
                        "look_at_hand": (DiscardFromHandThenDrawTrainer, OpponentHandTrainerToDeck, LookOpponentHandThenBenchBasics,  # v0.55・v0.56（エリカの香水）
                                         LookOpponentHandReturnOneThenMayDraw),  # v0.80: ロケット団の暗躍
                        "trainer_draw_declined": (EachPlayerMayDraw, LookOpponentHandReturnOneThenMayDraw), "trainer_discard_declined": DiscardFromHandThenDrawTrainer}.get(
                kind, (ArrangeOwnDeckTopTrainer, LookTopTakeRestDiscardTrainer, LookTopTakePokemonThenShuffle, ShuffleThenArrangeDeckTop, LookTopTakeTrainerThenShuffleLock)
                if kind == "look_at_deck_top" else ArrangeOwnDeckTopTrainer)  # v0.80: 新ポケモン図鑑HANDY808・ポケモンギア
            if using_trainer.get(user) != e["trainer_card"] or not isinstance(trainer_effect, expected):
                problems.append(f"{e['turn']} 番の {kind} が、使っている最中のトレーナーの処理のものではない")
            elif kind == "reveal_hand" and sorted(e["cards"]) != sorted(hand[e["player"]]):
                problems.append(f"{e['turn']} 番にプレイヤー {e['player']} が見せた手札 {e['cards']} が、ログから組み立てた手札と違う")
            elif kind == "look_at_hand" and (e["player"] != user or e["owner"] != 1 - user or sorted(e["cards"]) != sorted(hand[e["owner"]])):
                problems.append(f"{e['turn']} 番に見た相手の手札 {e['cards']} が、ログから組み立てた相手の手札と違う")
            elif kind == "revealed_hand_to_deck":
                if any(state.printed_def(uid).category != "trainer" for uid in e["cards"]) \
                        or sorted(e["cards"]) != sorted(uid for uid in hand[e["player"]] if state.printed_def(uid).category == "trainer"):
                    problems.append(f"{e['turn']} 番に見せた手札から山札にもどしたカード {e['cards']} が、手札のトレーナーカードのすべてではない")
                for uid in e["cards"]:
                    from_hand(e, e["player"], uid)
            elif kind in ("look_at_deck_top", "look_at_deck_top_none", "look_at_deck_top_declined") and (e["player"] != user or e["owner"] != user):
                problems.append(f"{e['turn']} 番の {kind} が、使ったプレイヤーの自分の山札ではない")
            elif kind == "look_at_deck_top" and isinstance(trainer_effect, (ShuffleThenArrangeDeckTop, LookTopTakeTrainerThenShuffleLock)):
                # v0.80: 新ポケモン図鑑HANDY808（切ったあと上のちょうど look 枚を見て並べかえる）・ポケモンギア（上のちょうど look 枚を見る）
                if e["count"] != trainer_effect.look or len(e["cards"]) != e["count"] or len(set(e["cards"])) != e["count"] \
                        or any(owner.get(uid) != e["owner"] or uid in hand[e["owner"]] or uid in discard[e["owner"]] for uid in e["cards"]):
                    problems.append(f"{e['turn']} 番の {trainer_effect.implementation_id} で見たカード {e['cards']} が、自分の山札の上の {trainer_effect.look} 枚ではない")
                if isinstance(trainer_effect, ShuffleThenArrangeDeckTop):
                    arrange_due = e
            elif kind == "look_at_deck_top" and isinstance(trainer_effect, LookTopTakePokemonThenShuffle):
                # v0.73: マスターボール。自分の山札の上のちょうど look 枚を見る（そのあとポケモンのカード 1 枚を見せて手札に加えるか、選ばずに終わり、山札を切る）
                if e["count"] != trainer_effect.look or len(e["cards"]) != e["count"] or len(set(e["cards"])) != e["count"] \
                        or any(owner.get(uid) != e["owner"] or uid in hand[e["owner"]] or uid in discard[e["owner"]] for uid in e["cards"]):
                    problems.append(f"{e['turn']} 番のマスターボールで見たカード {e['cards']} が、自分の山札の上の {trainer_effect.look} 枚ではない")
            elif kind == "look_at_deck_top" and isinstance(trainer_effect, LookTopTakeRestDiscardTrainer):
                # v0.55: カスミのいかり。自分の山札の上のちょうど look 枚を見る（そのあと手札に加えるカード・トラッシュするカードに分ける）
                if e["count"] != trainer_effect.look or len(e["cards"]) != e["count"] or len(set(e["cards"])) != e["count"] \
                        or any(owner.get(uid) != e["owner"] or uid in hand[e["owner"]] or uid in discard[e["owner"]] for uid in e["cards"]):
                    problems.append(f"{e['turn']} 番のカスミのいかりで見たカード {e['cards']} が、自分の山札の上の {trainer_effect.look} 枚ではない")
                looked_due = e
            elif kind == "look_at_deck_top":
                if not 1 <= e["count"] <= trainer_effect.max_cards or len(e["cards"]) != e["count"] or len(set(e["cards"])) != e["count"] \
                        or any(owner.get(uid) != e["owner"] or uid in hand[e["owner"]] or uid in discard[e["owner"]] for uid in e["cards"]):
                    problems.append(f"{e['turn']} 番のポケモン図鑑で見たカード {e['cards']} が、自分の山札の上の {trainer_effect.max_cards} 枚までではない")
                arrange_due = e
        elif kind == "hand_to_deck" and isinstance(_effect_of_event(state, e), LookOpponentHandCardToDeck):
            # v0.47: おどろかす。見た相手の手札の 1 枚（直前の look_at_card）を、相手が山札にもどし（見せない）、すぐあとに相手の山札を切る
            if not _same_attack(attack_window, e) or e["player"] != 1 - attack_window["player"] or prior is None or prior["kind"] != "look_at_card" \
                    or tuple(e["cards"]) != (prior["card"],) or prior["owner"] != e["player"]:
                problems.append(f"{e['turn']} 番のおどろかすで山札にもどしたカード {e['cards']} が、直前に見た相手の手札のカードではない")
            for uid in e["cards"]:
                from_hand(e, e["player"], uid)
            shuffle_due = e
        elif kind == "hand_to_deck":
            # v0.44: てじな・ラッキーたまご。ワザを使ったプレイヤーの手札のカードを、見せずに山札にもどす（cards は手札の並びの順。山札は組み立て直さない）
            if not _same_attack(attack_window, e) or e["player"] != attack_window["player"] \
                    or not isinstance(_effect_of_event(state, e), (ReturnHandThenRevealBasicEnergy, CoinDrawOrReturnHandToDeck, ShuffleHandIntoDeckThenDraw)) \
                    or not e["cards"] or len(set(e["cards"])) != len(e["cards"]):
                problems.append(f"{e['turn']} 番に手札から山札にもどしたカード {e['cards']} が、そのワザ（てじな・ラッキーたまご）の処理のものではない")
            hand_before = list(hand[e["player"]])
            for uid in e["cards"]:
                from_hand(e, e["player"], uid)
            effect = _effect_of_event(state, e)
            if isinstance(effect, ShuffleHandIntoDeckThenDraw):
                # v0.46: サイコエクスチェンジ。手札をすべてもどす → すぐあとに切る → count 枚まで引く
                if sorted(e["cards"]) != sorted(hand_before):
                    problems.append(f"{e['turn']} 番のサイコエクスチェンジで山札にもどしたカード {e['cards']} が、ログから組み立てた手札 {hand_before} と違う（すべてもどす）")
                shuffle_due, exchange_due = e, (e["player"], effect.count, e["turn"])
            if isinstance(effect, CoinDrawOrReturnHandToDeck):
                if len(e["cards"]) != effect.count:
                    problems.append(f"{e['turn']} 番のラッキーたまごで山札にもどしたカードが {len(e['cards'])} 枚（説明は {effect.count} 枚）")
                shuffle_due = e
        elif kind == "move_opponent_energy":
            # v0.45: じりょくせん。相手の対戦ポケモンの基本エネルギーカード（同じ uid）を、相手の控えポケモンにつける。つける控えが「とうめい」で受けなければ
            # 持ち主のトラッシュ（CR-TRANSPARENCY-ENERGY-BOMB と同じ読み方）
            source, target, uid = e["pokemon_id"], e["to_pokemon_id"], e["energy"]
            if not _same_attack(attack_window, e) or e["attacker"] != attack_window["player"] or e["player"] == e["attacker"] \
                    or not isinstance(_effect_of_event(state, e), DamageThenMoveOpponentEnergyToBench) or uid not in energy.get(source, ()) \
                    or not state.printed_def(uid).is_basic_energy or owner.get(uid) != e["player"] or pokemon_owner.get(target) != e["player"] \
                    or target == source or target not in in_play or e["result"] not in ("attached", "evaded"):
                problems.append(f"{e['turn']} 番のじりょくせんのエネルギー {uid}（{source} → {target}）が、そのワザの処理のものではない")
            else:
                energy[source].remove(uid)
                if e["result"] == "attached":
                    energy[target].append(uid)
                else:
                    discard[e["player"]].append(uid)
                    if attack_window["reception"].get(target) is not False:
                        problems.append(f"{e['turn']} 番のじりょくせんで、「とうめい」で受けないと決まっていない控え {target} のかわりにトラッシュした")
        elif kind == "take_deck_top":
            # v0.45: てつだうふり。相手の山札の一番上のカードを、トレーナーなら相手のトラッシュ、それ以外なら相手の手札へ（カードを引くことではない。山札は組み立て
            # 直さない）。見たのはワザを使ったプレイヤー
            uid = e["card"]
            expected = "discard" if state.printed_def(uid).category == "trainer" else "hand"
            if not _same_attack(attack_window, e) or e["looker"] != attack_window["player"] or e["player"] == e["looker"] \
                    or not isinstance(_effect_of_event(state, e), CoinOpponentDeckTopDiscardTrainerElseHand) or owner.get(uid) != e["player"] \
                    or e["destination"] != expected:
                problems.append(f"{e['turn']} 番のてつだうふりのカード {uid}（{e['destination']}）が、そのワザの処理のものではない")
            (discard if e["destination"] == "discard" else hand)[e["player"]].append(uid)
        elif kind == "put_discard_on_deck_top" and "trainer_card" in e:
            # v0.53: リサイクル。使っている最中のそのトレーナーで、自分のトラッシュのカードを自分の山札の上にのせる（切らない。山札は組み立て直さない）
            uid = e["card"]
            if using_trainer.get(e["player"]) != e["trainer_card"] or e["chooser"] != e["player"] or owner.get(uid) != e["player"] \
                    or uid not in discard[e["player"]] or not isinstance(_trainer_effect_of(state, e["trainer_card"]), TakeFromDiscardTrainer):
                problems.append(f"{e['turn']} 番に山札の上にのせたカード {uid} が、リサイクルを使ったプレイヤーのトラッシュのカードではない")
            else:
                discard[e["player"]].remove(uid)
        elif kind == "discard_to_deck":
            # v0.53: 夜の廃品回収。自分のトラッシュのカードを見せて山札にもどす（このあと切る。山札は組み立て直さない）
            # v0.80: エネルギーチャージ（自分のトラッシュのエネルギーカード）・タイムカプセル（それぞれのプレイヤーが自分のトラッシュから）
            capsule = isinstance(_trainer_effect_of(state, e["trainer_card"]), EachPlayerReturnDiscardToDeckThenHandLock) \
                and using_trainer.get(trainer_user(e["trainer_card"])) == e["trainer_card"]
            for uid in e["cards"]:
                if (using_trainer.get(e["player"]) != e["trainer_card"] and not capsule) or owner.get(uid) != e["player"] or uid not in discard[e["player"]]:
                    problems.append(f"{e['turn']} 番に山札にもどしたカード {uid} が、使ったプレイヤーのトラッシュのカードではない")
                else:
                    discard[e["player"]].remove(uid)
        elif kind in ("each_player_recover", "each_player_discard_to_deck"):
            # v0.83: おたがいのプレイヤーが選ぶワザ（ふしぎなはばたき・あかりでてらす・すくいあげる）。そのプレイヤー自身のトラッシュの、ワザの登録の種類のカードを、手札に加える・
            # 山札にもどす（山札は組み立て直さない。このあと、もどしたプレイヤーの山札を切る）
            effect = _effect_of_event(state, e)
            to_hand = kind == "each_player_recover"
            ok = isinstance(effect, EachPlayerRecoverFromDiscard) and (effect.destination == "hand") == to_hand and len(e["cards"]) <= effect.max_cards
            for uid in e["cards"]:
                if not ok or owner.get(uid) != e["player"] or uid not in discard[e["player"]] or (
                        effect.category == "pokemon" and state.printed_def(uid).category != "pokemon"):
                    problems.append(f"{e['turn']} 番に{'手札に加えた' if to_hand else '山札にもどした'}カード {uid} が、プレイヤー {e['player']} のトラッシュの選べるカードではない")
                else:
                    discard[e["player"]].remove(uid)
                    if to_hand:
                        hand[e["player"]].append(uid)
        elif kind == "milled_to_hand":
            # v0.73: 熱血!。すぐ前に同じトレーナーで山札の上からトラッシュしたカード（deck_top_to_discard）のうち、その色の基本エネルギーカードのすべてを手札に加える
            # （前からトラッシュにあったカードは加えない）
            trainer_effect = _trainer_effect_of(state, e["trainer_card"])
            user = trainer_user(e["trainer_card"])
            milled = prior["cards"] if prior is not None and prior["kind"] == "deck_top_to_discard" and prior.get("trainer_card") == e["trainer_card"] else None
            expected = None if milled is None or not isinstance(trainer_effect, DiscardDeckTopThenReturnTypeEnergy) else tuple(
                uid for uid in milled if state.printed_def(uid).is_basic_energy and state.printed_def(uid).provides is trainer_effect.energy_type)
            if using_trainer.get(user) != e["trainer_card"] or e["player"] != user or tuple(e["cards"]) != expected \
                    or any(uid not in discard[user] for uid in e["cards"]):
                problems.append(f"{e['turn']} 番に熱血!で手札に加えたカード {e['cards']} が、すぐ前にトラッシュしたカードのその色の基本エネルギーカードのすべてではない")
            else:
                for uid in e["cards"]:
                    discard[user].remove(uid)
                    hand[user].append(uid)
        elif kind == "retrieve_trainer":
            # v0.53: ダウジングマシーン。自分のトラッシュのトレーナーカードを手札に加える（使うための条件ですてたカードも選べる。使っている最中のこのカードは選べない）
            uid = e["card"]
            rod = isinstance(_trainer_effect_of(state, e["trainer_card"]), CoinTakeEvolutionOrBasicFromDiscard)  # v0.80: すごいつりざお（進化カード・たねポケモン）
            if using_trainer.get(e["player"]) != e["trainer_card"] or uid == e["trainer_card"] or owner.get(uid) != e["player"] \
                    or uid not in discard[e["player"]] or (state.printed_def(uid).category != "trainer" if not rod
                                                           else not (state.printed_def(uid).is_basic_pokemon or state.printed_def(uid).is_evolution_pokemon)):
                problems.append(f"{e['turn']} 番に手札に加えたカード {uid} が、使ったプレイヤーのトラッシュのトレーナーカードではない")
            else:
                discard[e["player"]].remove(uid)
                hand[e["player"]].append(uid)
        elif kind == "deck_top_to_discard" and "power" in e:
            # v0.86: エンテイの［おたけび］で、自分の山札の上から 5 枚をトラッシュした（山札は組み立て直さないので、持ち主・手札とトラッシュにないことで確かめる）。そのあとに
            # つける「炎」エネルギーカードは、このトラッシュしたカードの中だけ（power_attach_from_discard で確かめる）
            effect = _power_effect(state, e["power"])
            if not isinstance(effect, DiscardDeckTopAttachTypeEnergyThenEndTurn) or e["player"] != turn_player or len(e["cards"]) != effect.count:
                problems.append(f"{e['turn']} 番の特殊能力 {e['power']} による山札のトラッシュ {e['cards']} が、［おたけび］の処理と合わない")
            for uid in e["cards"]:
                if owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]]:
                    problems.append(f"{e['turn']} 番に［おたけび］で山札からトラッシュしたカード {uid} が、プレイヤー {e['player']} の山札のカードではない")
                    continue
                discard[e["player"]].append(uid)
            howl_milled[e["player"]] = (e["power"], set(e["cards"]))
        elif kind in ("trainer_discard_energy", "trainer_return_energy", "trainer_move_energy", "looked_to_hand", "looked_to_discard", "discard_pile_to_deck",
                      "deck_top_to_discard", "opponent_hand_to_deck", "trainer_switch_skipped"):
            # v0.55: すぐに使い終わるトレーナー。使っている最中のそのトレーナーの処理で、場のエネルギーカード・山札の上のカード・トラッシュ・相手の手札を動かす
            # （山札は組み立て直さない）。並び・数・側は instant_trainer_problems が確かめる
            user = trainer_user(e["trainer_card"])
            trainer_effect = _trainer_effect_of(state, e["trainer_card"])
            if using_trainer.get(user) != e["trainer_card"] or trainer_effect is None:
                problems.append(f"{e['turn']} 番の {kind} が、使っている最中のトレーナーの処理のものではない")
            elif kind in ("trainer_discard_energy", "trainer_return_energy"):
                pid = e["pokemon_id"]
                if pid not in in_play or pokemon_owner.get(pid) != e["player"] or any(uid not in energy.get(pid, []) for uid in e["cards"]) or not e["cards"] \
                        or any(owner.get(uid) != e["player"] or state.printed_def(uid).category != "energy" for uid in e["cards"]) \
                        or (kind == "trainer_return_energy" and (e["player"] != user or any(not state.printed_def(uid).is_basic_energy for uid in e["cards"]))):
                    problems.append(f"{e['turn']} 番に {kind} で動かしたカード {e['cards']} が、ログから組み立てたポケモン {pid} のエネルギーカードではない")
                else:
                    for uid in e["cards"]:
                        energy[pid].remove(uid)
                    (discard if kind == "trainer_discard_energy" else hand)[e["player"]].extend(e["cards"])
            elif kind == "trainer_move_energy":
                source, target = e["from_pokemon_id"], e["to_pokemon_id"]
                if source == target or e["player"] != user or any(pokemon_owner.get(pid) != user or pid not in in_play for pid in (source, target)) \
                        or tuple(energy.get(source, [])) != tuple(e["cards"]):
                    problems.append(f"{e['turn']} 番のナツメのつけなおし {e['cards']}（{source} → {target}）が、ログから組み立てた移動元のエネルギーカードのすべてではない")
                else:
                    energy[source] = []
                    energy[target].extend(e["cards"])
            elif kind in ("looked_to_hand", "looked_to_discard"):
                if looked_due is None or e["player"] != user or any(uid not in looked_due["cards"] for uid in e["cards"]):
                    problems.append(f"{e['turn']} 番の {kind} のカード {e['cards']} が、すぐ前にカスミのいかりで見たカードではない")
                (hand if kind == "looked_to_hand" else discard)[e["player"]].extend(e["cards"])
                if kind == "looked_to_discard":
                    looked_due = None
            elif kind == "discard_pile_to_deck":
                if e["player"] != user or sorted(e["cards"]) != sorted(discard[user]):
                    problems.append(f"{e['turn']} 番のトラッシュ交換で山札にもどしたカード {e['cards']} が、ログから組み立てたトラッシュのすべてではない")
                discard[user] = []
            elif kind == "deck_top_to_discard":
                if e["player"] != user or any(owner.get(uid) != user or uid in hand[user] or uid in discard[user] for uid in e["cards"]):
                    problems.append(f"{e['turn']} 番のトラッシュ交換で山札の上からトラッシュしたカード {e['cards']} が、自分の山札のカードではない")
                discard[user].extend(e["cards"])
            elif kind == "opponent_hand_to_deck":
                any_card = isinstance(_trainer_effect_of(state, e["trainer_card"]), LookOpponentHandReturnOneThenMayDraw)  # v0.80: ロケット団の暗躍（好きなカード）
                if e["player"] != 1 - user or e["looker"] != user or (state.printed_def(e["card"]).category != "trainer" and not any_card):
                    problems.append(f"{e['turn']} 番に相手の山札にもどさせたカード {e['card']} が、相手の手札のトレーナーカードではない")
                from_hand(e, e["player"], e["card"])
        elif kind == "prize_revealed":
            # v0.80: カードめくりゲーム。使っている最中のそのトレーナーで、相手のうらのサイドを 1 枚おもてにする（そのまま）
            user = trainer_user(e["trainer_card"])
            uid = e["card"]
            if using_trainer.get(user) != e["trainer_card"] or not isinstance(_trainer_effect_of(state, e["trainer_card"]), GuessOpponentPrizeKind) \
                    or e["player"] != 1 - user or owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]] \
                    or ids.get(uid) in in_play or uid in face_up_log:
                problems.append(f"{e['turn']} 番にカードめくりゲームでおもてにしたカード {uid} が、相手のうらのサイドのカードではない")
            face_up_log.add(uid)
        elif kind == "prizes_to_deck":
            # v0.80: にせオーキドの発明。相手のサイドをすべて山札にもどす（おもてのサイドの記録も除く。サイドを取ることではない）
            user = trainer_user(e["trainer_card"])
            if using_trainer.get(user) != e["trainer_card"] or not isinstance(_trainer_effect_of(state, e["trainer_card"]), LookOpponentPrizesMayRedeal) \
                    or e["player"] != 1 - user or e["looker"] != user or len(e["cards"]) != e["count"]:
                problems.append(f"{e['turn']} 番ににせオーキドの発明で山札にもどしたサイド {e['cards']} が、そのトレーナーの処理ではない")
            face_up_log.difference_update(e["cards"])
        elif kind == "prizes_revealed":
            # v0.63: ロケット団参上!。使っている最中のそのトレーナーで、お互いのサイドのカード（そのときサイドにある裏のカード）をおもてにする
            user = trainer_user(e["trainer_card"])
            if using_trainer.get(user) != e["trainer_card"] or not isinstance(_trainer_effect_of(state, e["trainer_card"]), RevealAllPrizesTrainer) \
                    or any(owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]] or ids.get(uid) in in_play or uid in face_up_log
                           for uid in e["cards"]) or len(e["cards"]) != len(e["positions"]):
                problems.append(f"{e['turn']} 番にロケット団参上!でおもてにしたカード {e['cards']} が、プレイヤー {e['player']} の裏のサイドのカードではない")
            face_up_log.update(e["cards"])
        elif kind == "set_aside_hand":
            # v0.63: くすぐりマシーンの「おもて」。使ったプレイヤーの相手の手札をすべて、手札とは別の場所に置く（ログから組み立てた手札のすべて）
            user = trainer_user(e["trainer_card"])
            if using_trainer.get(user) != e["trainer_card"] or not isinstance(_trainer_effect_of(state, e["trainer_card"]), CoinSetAsideOpponentHandElseEndTurn) \
                    or e["player"] != 1 - user or e["user"] != user or sorted(e["cards"]) != sorted(hand[e["player"]]) or e["count"] != len(e["cards"]) \
                    or e["return_turn"] != e["turn"] + 1:
                problems.append(f"{e['turn']} 番にくすぐりマシーンで置いたカード {e['cards']} が、相手の手札のすべてではない（もどす番 {e['return_turn']}）")
            hand[e["player"]] = []
            if e["cards"]:
                set_aside_log[("hand_set_aside", e["player"], e["trainer_card"])] = {"cards": tuple(e["cards"]), "return_turn": e["return_turn"]}
        elif kind == "face_down_bench":
            # v0.63: たたきつけろ!挑戦状。使っている最中のそのトレーナーで、選ぶプレイヤーの山札のたねポケモンをうらにしてベンチに出す（場のポケモンにはしない）
            user = trainer_user(e["trainer_card"])
            if using_trainer.get(user) != e["trainer_card"] or not isinstance(_trainer_effect_of(state, e["trainer_card"]), ChallengeBenchFromDecks) \
                    or any(owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]] or ids.get(uid) in in_play
                           or not state.printed_def(uid).is_basic_pokemon for uid in e["cards"]) or not e["cards"] or e["count"] != len(e["cards"]):
                problems.append(f"{e['turn']} 番に挑戦状でうらにして出したカード {e['cards']} が、プレイヤー {e['player']} の山札のたねポケモンではない")
            set_aside_log[("face_down_bench", e["player"], e["trainer_card"])] = {"cards": tuple(e["cards"]), "return_turn": None}
        elif kind == "face_down_revealed":
            # v0.63: うらにして出したカードを、置いた順に表にして場のポケモンにする（新しい場のポケモンの番号）
            group = set_aside_log.pop(("face_down_bench", e["player"], e["trainer_card"]), None)
            if group is None or group["cards"] != tuple(e["cards"]) or len(e["pokemon_ids"]) != len(e["cards"]):
                problems.append(f"{e['turn']} 番に表にしたカード {e['cards']} が、うらにして出したカード {group} ではない")
            for uid, pid in zip(e["cards"], e["pokemon_ids"]):
                enter(uid)
                if ids[uid] != pid:
                    problems.append(f"{e['turn']} 番に表にしたカード {uid} の場のポケモンの番号 {pid} が、ログの順番の番号 {ids[uid]} と違う")
        elif kind == "quiz_card_set":
            # v0.63: カツラのクイズ その3。使ったプレイヤーの手札のワザを持つポケモンのカードを、おもてを下にして置く（手札から出る）
            user = trainer_user(e["trainer_card"])
            quiz = _trainer_effect_of(state, e["trainer_card"])
            # v0.80: カツラのクイズ その2（手札のどのカードでも）・ポケモン性格判定（進化カード）
            accepted = (state.printed_def(e["card"]).category == "pokemon" and bool(state.printed_def(e["card"]).attacks)) if isinstance(quiz, BlainesQuiz) \
                else isinstance(quiz, SetAsideGuessKindQuiz) and (quiz.kinds != "personality" or state.printed_def(e["card"]).is_evolution_pokemon)
            if using_trainer.get(user) != e["trainer_card"] or e["player"] != user or not accepted:
                problems.append(f"{e['turn']} 番にクイズで置いたカード {e['card']} が、使ったプレイヤーの手札のワザを持つポケモンのカードではない")
            from_hand(e, e["player"], e["card"])
            set_aside_log[("quiz_card", e["player"], e["trainer_card"])] = {"cards": (e["card"],), "return_turn": None}
        elif kind == "quiz_reveal":
            # v0.63: 置いたカードをおもてにした（正解は答えの名前と置いたカードの名前が同じ）。答え（quiz_answer）はすぐ前
            group = set_aside_log.get(("quiz_card", e["player"], e["trainer_card"]))
            answered = prior if prior is not None and prior["kind"] == "quiz_answer" else None
            if group is None or group["cards"] != (e["card"],) or answered is None or answered["player"] != 1 - e["player"] \
                    or e["correct"] != (answered["answer"] == state.printed_def(e["card"]).name_ja) or e["name"] != state.printed_def(e["card"]).name_ja:
                problems.append(f"{e['turn']} 番のクイズの表にしたカード {e['card']}・正解 {e['correct']} が、置いたカード・すぐ前の答えと合わない")
        elif kind == "set_aside_returned":
            # v0.63: 置いておいたカードを持ち主の手札にもどす（くすぐりマシーンはもどす番の番の終わり、クイズは答えのあと）
            key = ("hand_set_aside" if e["reason"] == "expired" else "quiz_card", e["player"], e["trainer_card"])
            group = set_aside_log.pop(key, None)
            if group is None or group["cards"] != tuple(e["cards"]) or (e["reason"] == "expired" and group["return_turn"] != e["turn"]) \
                    or (e["reason"] == "quiz") != ("cards" in e.get("face_up", ())):
                problems.append(f"{e['turn']} 番に手札にもどしたカード {e['cards']}（{e['reason']}）が、置いておいたカード {group} ではない")
            hand[e["player"]].extend(e["cards"])
        elif kind == "trainer_bench_from_hand":
            # v0.56: エリカの香水。使っている最中のそのトレーナーで、使ったプレイヤーが選んだ相手（持ち主）の手札のたねポケモンを、持ち主のベンチに出す（新しい場のポケモン）
            user = trainer_user(e["trainer_card"])
            if using_trainer.get(user) != e["trainer_card"] or not isinstance(_trainer_effect_of(state, e["trainer_card"]), LookOpponentHandThenBenchBasics) \
                    or e["chooser"] != user or e["player"] != 1 - user or not state.printed_def(e["card"]).is_basic_pokemon or owner.get(e["card"]) != e["player"]:
                problems.append(f"{e['turn']} 番にエリカの香水でベンチに出させたカード {e['card']} が、相手の手札のたねポケモンではない")
            from_hand(e, e["player"], e["card"])
            enter(e["card"])
            if ids[e["card"]] != e["pokemon_id"]:
                problems.append(f"{e['turn']} 番にベンチに出させたカード {e['card']} の場のポケモンの番号 {e['pokemon_id']} が、ログの順番の番号 {ids[e['card']]} と違う")
            key = entry_opportunity(e["card"], from_hand=True)
            if key is not None:
                entry_due[e["pokemon_id"]] = (e["turn"], key)  # v0.86: 相手のトレーナーで手札から場に出させられたたねポケモンの使う機会
        elif kind == "trainer_hand_to_active":
            # v0.56: トレーナー「マチス」。バトル場のポケモンをベンチにもどし、手札のたねポケモンを直接バトル場に出す（新しい場のポケモン）
            user = trainer_user(e["trainer_card"])
            if using_trainer.get(user) != e["trainer_card"] or not isinstance(_trainer_effect_of(state, e["trainer_card"]), BenchActiveThenHandBasicToActive) \
                    or e["player"] != user or active_of.get(user) != e["old_active_pokemon_id"] or not state.printed_def(e["card"]).is_basic_pokemon:
                problems.append(f"{e['turn']} 番にマチスでバトル場に出したカード {e['card']} が、使ったプレイヤーの手札のたねポケモン（もとのバトル場 {e['old_active_pokemon_id']}）ではない")
            from_hand(e, e["player"], e["card"])
            enter(e["card"])
            active_of[e["player"]] = ids[e["card"]]
            if ids[e["card"]] != e["pokemon_id"]:
                problems.append(f"{e['turn']} 番にバトル場に出したカード {e['card']} の場のポケモンの番号 {e['pokemon_id']} が、ログの順番の番号 {ids[e['card']]} と違う")
            key = entry_opportunity(e["card"], from_hand=True, on_bench=False)
            if key is not None:
                entry_due[e["pokemon_id"]] = (e["turn"], key)  # v0.86: マチスで手札からバトル場に出したたねポケモンの使う機会
        elif kind == "hand_positions_to_deck":
            # v0.56: ロケット団のワナ。おもてを見ないで選んだ相手の手札の位置のカードを、相手（持ち主）の山札にもどす（このあと切る。山札は組み立て直さない）
            user = trainer_user(e["trainer_card"])
            if using_trainer.get(user) != e["trainer_card"] or not isinstance(_trainer_effect_of(state, e["trainer_card"]), CoinReturnOpponentHandPositions) \
                    or e["chooser"] != user or e["player"] != 1 - user or not 1 <= len(e["cards"]) <= 3 or len(e["positions"]) != len(e["cards"]) \
                    or any(not 0 <= i < len(hand[e["player"]]) for i in e["positions"]) or any(uid not in hand[e["player"]] for uid in e["cards"]):
                problems.append(f"{e['turn']} 番にロケット団のワナでもどしたカード {e['cards']}（位置 {e['positions']}）が、ログから組み立てた相手の手札のその位置のカードではない")
            for uid in e["cards"]:
                from_hand(e, e["player"], uid)
        elif kind == "swap_prize_with_hand":
            # v0.56: カスミのわがまま。見たサイドの位置のカードと手札のカードを入れかえる（サイドの枚数は変わらない）
            user = trainer_user(e["trainer_card"])
            if using_trainer.get(user) != e["trainer_card"] or not isinstance(_trainer_effect_of(state, e["trainer_card"]), LookPrizeAskSwapElseDraw) \
                    or e["player"] != user or owner.get(e["to_hand"]) != user or e["to_hand"] in hand[user] or e["to_hand"] in discard[user]:
                problems.append(f"{e['turn']} 番のカスミのわがままの入れかえ（{e['to_prize']} ↔ {e['to_hand']}）が、使っている最中のその処理の自分のサイドと手札ではない")
            if ("to_hand" in e.get("face_up", ())) != (e["to_hand"] in face_up_log):
                problems.append(f"{e['turn']} 番のカスミのわがままで手札に来たサイド {e['to_hand']} のおもての印が、ログから組み立てたおもてのサイドと合わない")  # v0.63
            face_up_log.discard(e["to_hand"])
            from_hand(e, e["player"], e["to_prize"])
            hand[e["player"]].append(e["to_hand"])
            if e["to_prize"] in taken_cards:
                # v0.57 で直した v0.56 の監査の漏れ: 前に取ったサイドのカードを、カスミのわがままでサイドにもどした（また取れる。同じカードの 2 回目の取得ではない）
                taken_cards.remove(e["to_prize"])
        elif kind in ("request_answered", "trainer_effect_added"):
            # v0.56: 相手の答え（マチスの交渉・カスミのわがまま）・期限のある効果を与えた（カスミ・キョウ・見えない壁）。使っている最中のそのトレーナーの処理
            user = trainer_user(e["trainer_card"])
            trainer_effect = _trainer_effect_of(state, e["trainer_card"])
            expected = (AskOpponentEachTakePrizeElseDraw, LookPrizeAskSwapElseDraw, ChallengeBenchFromDecks) if kind == "request_answered" \
                else (TrainerTurnEffectTrainer, DevolveOneToHandWithBan)  # v0.80: 退化スプレーHYPER（その番だけ、退化させたポケモンを進化させない）
            if kind == "request_answered" and isinstance(trainer_effect, LookOpponentPrizesMayRedeal):
                # v0.80: にせオーキドの発明（置きなおすかを決めるのは使ったプレイヤー）
                if using_trainer.get(user) != e["trainer_card"] or e["player"] != user:
                    problems.append(f"{e['turn']} 番の {kind} が、使っている最中のトレーナーの処理のものではない")
            elif kind == "trainer_effect_added" and isinstance(trainer_effect, DevolveOneToHandWithBan):
                here = next(i for i in range(len(log) - 1, -1, -1) if log[i] is e)
                devolved = next((x for x in reversed(log[:here]) if x["kind"] in ("devolve", "play_trainer")), None)  # 退化で消した特殊状態・効果のログはあいだにある
                if using_trainer.get(user) != e["trainer_card"] or e["player"] != user or e["effect_kind"] != "evolution_ban" or e["expires_turn"] != e["turn"] \
                        or devolved is None or devolved["kind"] != "devolve" or devolved.get("trainer_card") != e["trainer_card"] or devolved["pokemon_id"] != e.get("pokemon_id"):
                    problems.append(f"{e['turn']} 番の退化スプレーHYPER の期限のある効果が、そのトレーナーで退化させたすぐあとの、その番の終わりまでのものではない")
                trainer_effects_log[(e["player"], e["trainer_card"])] = e
            elif using_trainer.get(user) != e["trainer_card"] or not isinstance(trainer_effect, expected) \
                    or e["player"] != (1 - user if kind == "request_answered" else user):
                problems.append(f"{e['turn']} 番の {kind} が、使っている最中のトレーナーの処理のものではない")
            elif kind == "trainer_effect_added":
                terms = trainer_effect.turn_effect_terms()
                if e["effect_kind"] != terms[0] or e["expires_turn"] != e["turn"] + terms[1] or (e["player"], e["trainer_card"]) in trainer_effects_log:
                    problems.append(f"{e['turn']} 番に与えた期限のある効果 {e['effect_kind']}（{e['expires_turn']} 番まで）が、登録の実装 {terms} と合わない")
                trainer_effects_log[(e["player"], e["trainer_card"])] = e
        elif kind == "trainer_effect_removed":
            info = trainer_effects_log.pop((e["player"], e["trainer_card"]), None)
            if info is None or e["reason"] != "expired" or e["turn"] != e["expires_turn"] or e["created_turn"] != info["turn"] or e["effect_kind"] != info["effect_kind"]:
                problems.append(f"{e['turn']} 番に消した期限のある効果（プレイヤー {e['player']}・カード {e['trainer_card']}）が、与えた効果の期限と合わない")
        elif kind == "trainer_turn_end":
            # v0.56: ロケット団員の「うら」。使い終えたそのトレーナーをトラッシュしたすぐあとに、番の終わりに進む
            if prior is None or prior["kind"] != "discard_trainer" or prior["card"] != e["trainer_card"] or e["player"] != turn_player \
                    or not getattr(_trainer_effect_of(state, e["trainer_card"]), "may_end_turn", False):
                problems.append(f"{e['turn']} 番のトレーナーの効果による番の終わりが、番を終えるトレーナーを使い終えたすぐあとではない")
        elif kind == "trainer_take_none":
            # v0.80: タイムカプセルは、それぞれのプレイヤーが自分のトラッシュから選ぶ（相手プレイヤーの選ばなかったログもある）
            capsule = isinstance(_trainer_effect_of(state, e["trainer_card"]), EachPlayerReturnDiscardToDeckThenHandLock) \
                and using_trainer.get(trainer_user(e["trainer_card"])) == e["trainer_card"]
            if using_trainer.get(e["player"]) != e["trainer_card"] and not capsule:
                problems.append(f"{e['turn']} 番の選ばずに終わったログ（カード {e['trainer_card']}）が、使っている最中のトレーナーのものではない")
        elif kind == "put_discard_on_deck_top":
            # v0.44: わるいいたずら。相手（カードの持ち主）のトラッシュのカードを、その山札の上にのせる（切らない）。選んだのはワザを使ったプレイヤー
            uid = e["card"]
            if not _same_attack(attack_window, e) or e["chooser"] != attack_window["player"] \
                    or e["player"] == e["chooser"] or not isinstance(_effect_of_event(state, e), CoinPutOpponentDiscardOnDeckTop) \
                    or owner.get(uid) != e["player"] or uid not in discard[e["player"]]:
                problems.append(f"{e['turn']} 番に山札の上にのせたカード {uid} が、ワザを使ったプレイヤーの相手のトラッシュのカードではない")
            else:
                discard[e["player"]].remove(uid)
        elif kind == "stadium_placed":
            # v0.57: 使っている最中のスタジアムカード（play_trainer のすぐあと）を、トラッシュせずに両方の場の境界線上に出す。前のスタジアムはすぐあとに持ち主のトラッシュ
            card = e["card"]
            entry = state.effects.trainer_entry(state.cards[card].card_id) if card in state.cards else None
            if using_trainer.get(e["player"]) != card or entry is None or not entry.effect.is_stadium or prior is None \
                    or prior["kind"] != "play_trainer" or prior["card"] != card or owner.get(card) != e["player"] \
                    or e.get("replaces") != (None if stadium_zone is None else stadium_zone[0]):
                problems.append(f"{e['turn']} 番に場に出したスタジアム {card} が、使っている最中のスタジアムカード（前のスタジアム {stadium_zone}）ではない")
            using_trainer[e["player"]] = None
            stadium_due = stadium_zone
            stadium_zone = (card, e["player"])
            if stadium_due is not None:
                after = log[next(i for i in range(len(log) - 1, -1, -1) if log[i] is e) + 1:]
                follow = after[0] if after else None
                if follow is None or follow["kind"] != "stadium_discarded" or follow["card"] != stadium_due[0] or follow["player"] != stadium_due[1] \
                        or follow.get("reason") != "replaced" or follow.get("by_card") != card:
                    problems.append(f"{e['turn']} 番にスタジアム {card} を出したあとに、前のスタジアム {stadium_due[0]} を持ち主のトラッシュにすてたログがない")
                else:
                    discard[stadium_due[1]].append(stadium_due[0])
        elif kind == "stadium_discarded" and e.get("reason") == "attack":
            # v0.58: ワザの効果で場のスタジアムをトラッシュする（タケシのゴローンの「ばくれつ」）。そのワザ（effect）の宣言のあと、場のスタジアムを持ち主のトラッシュに
            last_attack = next((x for x in reversed(log[:next(i for i in range(len(log) - 1, -1, -1) if log[i] is e)]) if x["kind"] == "attack"), None)
            if stadium_zone is None or stadium_zone != (e["card"], e["player"]) or last_attack is None or last_attack["turn"] != e["turn"] \
                    or e.get("by_card") != last_attack.get("pokemon"):
                problems.append(f"{e['turn']} 番にワザの効果でトラッシュしたスタジアム {e['card']} が、ログから組み立てた場のスタジアム {stadium_zone} ではない")
            else:
                discard[e["player"]].append(e["card"])
                stadium_zone = None
        elif kind == "stadium_discarded":
            if prior is None or prior["kind"] != "stadium_placed" or prior.get("replaces") != e["card"] or owner.get(e["card"]) != e["player"]:
                problems.append(f"{e['turn']} 番にトラッシュしたスタジアム {e['card']} が、新しいスタジアムに入れかわった前のスタジアムではない")
        elif kind == "chaos_answered" and e["accepted"]:
            # v0.57: 錯乱ジムのコインの「うら」で、相手プレイヤーが借りて使う（使っている最中のカードを使うプレイヤーが借りたプレイヤーになる。持ち主は変わらない）
            if using_trainer.get(e["owner"]) != e["card"] or e["player"] != 1 - e["owner"]:
                problems.append(f"{e['turn']} 番に借りて使ったトレーナー {e['card']} が、相手の使っている最中のトレーナーではない")
            using_trainer[e["owner"]] = None
            using_trainer[e["player"]] = e["card"]
        elif kind in ("stadium_used", "stadium_attack_coin", "chaos_check", "chaos_answered", "chaos_not_borrowable"):
            card = e["stadium_card"] if "stadium_card" in e else e.get("card")
            if kind in ("stadium_used", "stadium_attack_coin", "chaos_check") and (stadium_zone is None or stadium_zone[0] != card):
                problems.append(f"{e['turn']} 番の {kind} のスタジアム {card} が、ログから組み立てた場のスタジアム {stadium_zone} ではない")
            if kind in ("stadium_used", "stadium_attack_coin") and e["player"] != turn_player:
                problems.append(f"{e['turn']} 番の {kind} が、番のプレイヤーの操作ではない")
        elif kind == "discard_to_hand_suppressed":
            # v0.74: ポケモンタワーで「トラッシュからカードを取り出して手札に加える」効果が消えた。場のスタジアムがポケモンタワーのとき
            if stadium_zone is None or stadium_zone[0] != e["stadium_card"] or not tower_in_play():
                problems.append(f"{e['turn']} 番の discard_to_hand_suppressed のスタジアム {e['stadium_card']} が、ログから組み立てた場のポケモンタワー（{stadium_zone}）ではない")
        elif kind == "stadium_retrieve_energy":
            # v0.74: エネルギースタジアムの「おもて」。番のプレイヤーのトラッシュの基本エネルギーカードを手札へ（直前のこのスタジアムのコインが「おもて」）
            uid = e["card"]
            effect = None if stadium_zone is None else _trainer_effect_of(state, stadium_zone[0])
            coin = next((x for x in reversed(log[:next(i for i in range(len(log) - 1, -1, -1) if log[i] is e)]) if x["kind"] == "coin_flip"), None)
            if not isinstance(effect, CoinRetrieveBasicEnergyStadium) or stadium_zone[0] != e["stadium_card"] or e["player"] != turn_player \
                    or uid not in discard[e["player"]] or not state.printed_def(uid).is_basic_energy or coin is None or coin["source"] != "stadium" \
                    or coin.get("card") != e["stadium_card"] or coin["result"] != "heads":
                problems.append(f"{e['turn']} 番にエネルギースタジアムで手札に加えたカード {uid} が、「おもて」のあとの番のプレイヤーのトラッシュの基本エネルギーカードではない")
            else:
                discard[e["player"]].remove(uid)
                hand[e["player"]].append(uid)
        elif kind == "trainer_bench_from_deck":
            # v0.80: ポケモンマーチ。使っている最中のそのトレーナーで、それぞれのプレイヤーが自分の山札のたねポケモンを手札を通さずにベンチへ（山札は組み立て直さない）
            uid = e["card"]
            if not isinstance(_trainer_effect_of(state, e["trainer_card"]), EachPlayerMayBenchBasicFromDeck) or owner.get(uid) != e["player"] \
                    or uid in hand[e["player"]] or uid in discard[e["player"]] or ids.get(uid) in in_play or not state.printed_def(uid).is_basic_pokemon:
                problems.append(f"{e['turn']} 番にポケモンマーチでベンチに出したカード {uid} が、プレイヤー {e['player']} の山札のたねポケモンではない")
            enter(uid)
            if ids[uid] != e["to_pokemon_id"]:
                problems.append(f"{e['turn']} 番にベンチに出したポケモンの番号 {e['to_pokemon_id']} が、ログから組み立てた {ids[uid]} と違う")
        elif kind == "stadium_bench_from_deck":
            # v0.74: キョウの忍者ジムの「おもて」。番のプレイヤーの山札の「キョウのたねポケモン」を手札を通さずにベンチへ。すぐあとに同じプレイヤーの山札を切る
            uid = e["card"]
            effect = None if stadium_zone is None else _trainer_effect_of(state, stadium_zone[0])
            definition = state.printed_def(uid)
            if not isinstance(effect, CoinBenchOwnerBasicFromDeckStadium) or stadium_zone[0] != e["stadium_card"] or e["player"] != turn_player \
                    or owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]] or ids.get(uid) in in_play \
                    or not definition.is_basic_pokemon or not definition.name_ja.startswith(f"{effect.owner}の"):
                # 場にいないこと（ids は場をはなれたカードも残す。セキチクシティジム・くもがくれガスで山札にもどったカードも、また山札から出せる）
                problems.append(f"{e['turn']} 番にキョウの忍者ジムでベンチに出したカード {uid} が、番のプレイヤーの山札の「キョウのたねポケモン」ではない")
            enter(uid)
            if ids[uid] != e["to_pokemon_id"]:
                problems.append(f"{e['turn']} 番にベンチに出したポケモンの番号 {e['to_pokemon_id']} が、ログから組み立てた {ids[uid]} と違う")
            after = log[next(i for i in range(len(log) - 1, -1, -1) if log[i] is e) + 1:]
            if not after or after[0]["kind"] != "shuffle" or after[0]["player"] != e["player"] or after[0].get("stadium_card") != e["stadium_card"]:
                problems.append(f"{e['turn']} 番にキョウの忍者ジムでベンチに出したあとに、山札を切ったログがない")
        elif kind in ("stadium_discard_energy", "stadium_return_energy"):
            # v0.57: タマムシシティジム（エネルギーカードをトラッシュ）・ヤマブキシティジム（基本エネルギーカードを手札に）。番のプレイヤーの場のポケモンから
            pid = e["pokemon_id"]
            if stadium_zone is None or stadium_zone[0] != e["stadium_card"] or e["player"] != turn_player or pokemon_owner.get(pid) != e["player"] \
                    or e["card"] not in energy.get(pid, []):
                problems.append(f"{e['turn']} 番の {kind}（{e['card']}）が、場のスタジアム・番のプレイヤーのポケモン {pid} のエネルギーカードではない")
            else:
                energy[pid].remove(e["card"])
                (discard if kind == "stadium_discard_energy" else hand)[e["player"]].append(e["card"])
                if kind == "stadium_return_energy" and not state.printed_def(e["card"]).is_basic_energy:
                    problems.append(f"{e['turn']} 番にヤマブキシティジムで手札に加えたカード {e['card']} が、基本エネルギーカードではない")
        elif kind == "energy_drain_discard":
            # v0.68: ［だつりょくえき］の「おもて」。直前の判定（energy_drain_check）が同じ特殊能力・「おもて」で、ダメージを与えたポケモンのエネルギーカードを、その持ち主の
            # トラッシュに置く（あいだにワザの途中の決定がある）
            pid = e["attacker_pokemon_id"]
            check = next((x for x in reversed(log[:next(i for i in range(len(log) - 1, -1, -1) if log[i] is e)]) if x["kind"] == "energy_drain_check"), None)
            if check is None or check["power"] != e["power"] or check["result"] != "heads" or check["attacker_pokemon_id"] != pid \
                    or e["card"] not in energy.get(pid, []):
                problems.append(f"{e['turn']} 番の［だつりょくえき］でトラッシュしたカード {e['card']} が、「おもて」の判定のあとの、ダメージを与えたポケモン {pid} の"
                                "エネルギーカードではない")
            else:
                energy[pid].remove(e["card"])
                discard[owner[e["card"]]].append(e["card"])
        elif kind in ("energy_heal", "energy_damage"):
            # v0.58: 特殊エネルギーを手札から出してつけたときの効果（きずぐすり配合エネルギーの回復・レインボーエネルギーの 10）。つけたログ（attach_energy・
            # power_attach_energy・attach_energy_from_hand）のすぐあとで、そのカードの登録の実装と量が合う
            pid = e["pokemon_id"]
            effect = state.effects.energy_effect(state.printed_def(e["energy"])) if e["energy"] in state.cards else None
            attached = prior is not None and prior["kind"] in ("attach_energy", "power_attach_energy", "attach_energy_from_hand") \
                and prior.get("energy", prior.get("card")) == e["energy"]
            if kind == "energy_heal":
                ok = isinstance(effect, HealOnAttachEnergy) and 0 < e["counters"] <= effect.counters and e["damage_before"] == damage[pid]
                damage[pid] -= e["counters"] * state.rules.damage_per_counter
            else:
                ok = isinstance(effect, RainbowEnergy) and e["amount"] == effect.amount
                damage[pid] += e["amount"]
            if not ok or not attached or damage[pid] != e["total_damage"] or damage[pid] < 0:
                problems.append(f"{e['turn']} 番の {kind}（ポケモン {pid}・カード {e['energy']}）が、手札からつけたすぐあとの登録の特殊エネルギーの効果・ログから組み立てた"
                                f"ダメージ {damage[pid]} と合わない")
        elif kind == "stadium_damage":
            # v0.57: ロケット団の爆発ジム（手札からベンチに出したたねポケモンへの 20。持ち主のコインの「うら」のすぐあと）
            pid = e["pokemon_id"]
            if stadium_zone is None or stadium_zone[0] != e.get("stadium_card", stadium_zone[0]) or prior is None or prior["kind"] != "coin_flip" \
                    or prior.get("result") != "tails" or prior.get("player") != e["player"]:
                problems.append(f"{e['turn']} 番の爆発ジムのダメージ（ポケモン {pid}）が、場のスタジアムの持ち主のコインの「うら」のすぐあとではない")
            damage[pid] += e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の stadium_damage のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind in ("sinkhole_damage", "knock_out_power_damage", "trainer_damage"):
            # v0.61: ［おとしあな］・［ファイナルビーム］のダメージ（特殊能力のダメージ）とバトル場は穴だらけ!のダメージ（トレーナーのダメージ）。どれもワザのダメージ
            # ではない（弱点・抵抗力を計算しない。量はログの amount）
            pid = e["pokemon_id"] if kind == "trainer_damage" else e["target_pokemon_id"]
            if kind == "trainer_damage":
                trainer_damaged.add((pid, e["turn"]))
            damage[pid] += e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の {kind} のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "bench_guard":
            # v0.65: ［ベンチガード］でタケシのサイドンがかわりに受けた 10（ワザのダメージの要素の一部。すぐ前のログ damage の bench_guard に、このサイドンと量がある）
            pid = e["pokemon_id"]
            source = last_damage
            if source is None or (pid, e["amount"]) not in tuple(source.get("bench_guard", ())) or source.get("pokemon_id") != e["from_pokemon_id"]:
                problems.append(f"{e['turn']} 番の［ベンチガード］（ポケモン {pid}）が、すぐ前の控えポケモンへのダメージのログの bench_guard と合わない")
            damage[pid] += e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の bench_guard のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "stadium_heal":
            # v0.80: いやしの野原（自分の番に使ったプレイヤーの対戦ポケモンから、「おもて」ならダメージカウンターを 2 個まで）
            pid = e["pokemon_id"]
            damage[pid] -= e["counters"] * state.rules.damage_per_counter
            effect = None if stadium_zone is None else _trainer_effect_of(state, stadium_zone[0])
            if not isinstance(effect, CoinHealOwnActiveStadium) or stadium_zone[0] != e["stadium_card"] or e["player"] != turn_player \
                    or active_of.get(e["player"]) != pid or not 0 < e["counters"] <= effect.counters or damage[pid] != e["total_damage"] or damage[pid] < 0:
                problems.append(f"{e['turn']} 番のいやしの野原のとりのぞき（ポケモン {pid}）が、場のスタジアム・ログから組み立てたダメージ {damage[pid]} と合わない")
        elif kind == "evolution_heal":
            # v0.57: トキワシティジム（進化したサカキのポケモンから、のぞむならダメージカウンターを 2 つ）
            pid = e["pokemon_id"]
            damage[pid] -= e["count"] * state.rules.damage_per_counter
            if stadium_zone is None or stadium_zone[0] != e["stadium_card"] or damage[pid] != e["total_damage"] or damage[pid] < 0:
                problems.append(f"{e['turn']} 番のトキワシティジムのとりのぞき（ポケモン {pid}）が、場のスタジアム・ログから組み立てたダメージ {damage[pid]} と合わない")
        elif kind == "discard_trainer":
            here = next(i for i in range(len(log) - 1, -1, -1) if log[i] is e)
            start = next((i for i in range(here, -1, -1) if log[i]["kind"] == "play_trainer" and log[i]["card"] == e["card"]), None)
            if start is not None:
                # v0.57: 錯乱ジム（コイン・相手への問いと答え）・リムーブ禁止ジムの追加の条件（スタジアムのトラッシュ）は、カードの効果の前のスタジアムの処理なので、
                # 1 回ぶんのトレーナーの並びの確かめからは除く。相手が借りて使ったら、使ったプレイヤーは借りたプレイヤー。使わなかった（借りなかった・借りられなかった）
                # カードは、効果の並びを確かめない（持ち主のトラッシュにすてただけ）
                start, sequence = _without_stadium_steps(log[start:here + 1])
                if sequence is not None:
                    problems.extend(search_retrieval_problems(state, sequence))
                    problems.extend(hand_deck_problems(state, sequence))
                    problems.extend(instant_trainer_problems(state, sequence))
                start = None
            if start is not None:
                problems.extend(search_retrieval_problems(state, log[start:here + 1]))  # v0.53
                problems.extend(hand_deck_problems(state, log[start:here + 1]))  # v0.54
                problems.extend(instant_trainer_problems(state, log[start:here + 1]))  # v0.55
            discard[e["player"]].append(e["card"])
            trainer_discarded[e["player"]] = ()
            using_trainer[e["player"]] = None
            for p_index in (0, 1):
                if using_trainer.get(p_index) == e["card"]:
                    using_trainer[p_index] = None  # v0.57: 錯乱ジムで借りて使ったカードも、持ち主のトラッシュにすてる
            for p_index, stack in outer_trainers.items():
                # v0.58: 内側のカードを使い終えたら、外側のカード（サイキックコントロール）を使い終える。外側のカードのすてるログは内側のすぐあと
                if stack and stack[-1] == e["card"]:
                    stack.pop()
                elif stack and using_trainer.get(p_index) is None and owner.get(e["card"]) != p_index:
                    using_trainer[p_index] = stack[-1]
        elif kind == "secret_plan_placed":
            # v0.67: マチスの秘策。使っている最中のマチスの秘策（play_trainer のあと）の効果で、手札のカードをうらにしてベンチに出す（新しい場のポケモン）
            card = e["card"]
            trainer_effect = _trainer_effect_of(state, e["trainer_card"])
            if using_trainer.get(e["player"]) != e["trainer_card"] or not isinstance(trainer_effect, PlaceFaceDownOnBench) or owner.get(card) != e["player"]:
                problems.append(f"{e['turn']} 番にうらにして出したカード {card} が、使っている最中のマチスの秘策の効果ではない")
            from_hand(e, e["player"], card)
            enter(card)
            face_down_pids.add(ids[card])
            if ids[card] != e["pokemon_id"]:
                problems.append(f"{e['turn']} 番にうらにして出したカード {card} の場のポケモンの番号 {e['pokemon_id']} が、ログの順番の番号 {ids[card]} と違う")
        elif kind == "secret_plan_revealed":
            # v0.67: うらのカードをおもてにした。おもてにするのはうらのカードだけ（同じ場のポケモン。番号・ついているカードは変えない）
            pid = e["pokemon_id"]
            if pid not in face_down_pids or pid not in in_play or top.get(pid) != e["card"] or state.cards[e["card"]].card_id != e["card_id"] \
                    or e["cause"] not in SECRET_PLAN_CAUSES:
                problems.append(f"{e['turn']} 番におもてにした場のポケモン {pid}（カード {e['card']}・理由 {e['cause']}）が、ログから組み立てたうらのカードではない")
            face_down_pids.discard(pid)
            if damage.get(pid, 0):
                problems.append(f"{e['turn']} 番におもてにしたうらのカード {pid} に、おもてにする前にダメージ {damage[pid]} がのっている")
        elif kind == "secret_plan_discarded":
            # v0.67: おもてにしたカードがたねポケモンでなかった。そのカードとついているすべてのカードをトラッシュ（きぜつではない。直前のログは同じポケモンの secret_plan_revealed）
            pid = e["pokemon_id"]
            if prior is None or prior["kind"] != "secret_plan_revealed" or prior["pokemon_id"] != pid or state.printed_def(prior["card"]).is_basic_pokemon \
                    or pokemon_owner.get(pid) != e["player"]:
                problems.append(f"{e['turn']} 番にトラッシュしたうらのカード {pid} が、すぐ前におもてにした、たねポケモンでないカードではない")
            if sorted(e["energy"]) != sorted(energy.get(pid, [])) or tuple(e["cards"]) != (top.get(pid), *e["energy"], *e["trainers"]):
                problems.append(f"{e['turn']} 番にトラッシュしたうらのカード {pid} のカード {e['cards']} が、ログの組み立てと違う")
            in_play.discard(pid)
            exclusive.pop(pid, None)
            poisoned.pop(pid, None)
            energy[pid] = []
            damage[pid] = 0
            discard[e["player"]].extend((top.get(pid), *e["energy"]))
            for uid in e["trainers"]:
                discard[owner[uid]].append(uid)
            if active_of.get(e["player"]) == pid:
                active_of[e["player"]] = None
        elif kind == "play_trainer_as_pokemon":
            # v0.47: なにかの化石・ピッピ人形。使っている最中のこのカード（play_trainer のすぐあと）を、トラッシュせずにベンチにポケモンとして出す
            card = e["card"]
            entry = state.effects.trainer_entry(state.cards[card].card_id) if card in state.cards else None
            if using_trainer.get(e["player"]) != card or entry is None or not isinstance(entry.effect, PlayAsPokemon) or prior is None \
                    or prior["kind"] != "play_trainer" or prior["card"] != card or owner.get(card) != e["player"]:
                problems.append(f"{e['turn']} 番にポケモンとして場に出したカード {card} が、使っている最中のポケモンとして場に出せるトレーナーカードではない")
            using_trainer[e["player"]] = None
            enter(card)
            if ids[card] != e["pokemon_id"]:
                problems.append(f"{e['turn']} 番にポケモンとして場に出したカード {card} の場のポケモンの番号 {e['pokemon_id']} が、ログの順番の番号 {ids[card]} と違う")
        elif kind == "discard_from_play":
            # v0.47: なにかの化石・ピッピ人形（進化カードがのっていない）を、自分の番に、ついているカードといっしょにトラッシュする（きぜつではない）
            pid = e["pokemon_id"]
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or ids.get(e["pokemon"]) != pid or e["player"] != turn_player \
                    or state.in_play_def(e["pokemon"]).play_role is None or evolve_turns.get(pid):
                problems.append(f"{e['turn']} 番にトラッシュした場のポケモン {pid} が、自分の番の、すてられる場での役割のカード（進化していない）ではない")
            if sorted(e["energy"]) != sorted(energy.get(pid, [])) or e["damage"] != damage[pid] \
                    or tuple(e["cards"]) != (e["pokemon"], *e["energy"], *e["trainers"]):
                problems.append(f"{e['turn']} 番にトラッシュした場のポケモン {pid} のカード {e['cards']}・ダメージ {e['damage']} が、ログの組み立てと違う")
            in_play.discard(pid)
            exclusive.pop(pid, None)
            poisoned.pop(pid, None)
            energy[pid] = []
            damage[pid] = 0
            discard[e["player"]].extend((e["pokemon"], *e["energy"]))
            for uid in e["trainers"]:
                discard[owner[uid]].append(uid)
            if active_of.get(e["player"]) == pid:
                active_of[e["player"]] = None
        elif kind == "trainer_lock_added" and e.get("origin") == "trainer":
            # v0.56: ロケット団の実験の「うら」。使っている最中のそのトレーナーのコインの「うら」のすぐあとに、使ったプレイヤー自身に、与えた番 + 2 の番の終わりまでの禁止
            user = trainer_user(e["trainer_card"])
            trainer_effect = _trainer_effect_of(state, e["trainer_card"])
            if using_trainer.get(user) != e["trainer_card"] or not getattr(trainer_effect, "tails_self_lock", False) or e["player"] != user \
                    or e["source_player"] != user or e["expires_turn"] != e["turn"] + 2 or prior is None or prior["kind"] != "coin_flip" \
                    or prior.get("card") != e["trainer_card"] or prior.get("result") != "tails" or (e["player"], e["expires_turn"], "trainer") in trainer_locks_log:
                problems.append(f"{e['turn']} 番のトレーナーの効果の禁止（プレイヤー {e['player']}・{e['expires_turn']} 番まで）が、ロケット団の実験の「うら」の処理ではない")
            trainer_locks_log[(e["player"], e["expires_turn"], "trainer")] = e
        elif kind == "trainer_lock_added" and e.get("origin") == HAND_TRAINER_LOCK:
            # v0.80: ウツギはかせ・タイムカプセル・ポケモンギア。使っている最中のそのトレーナーで、使ったプレイヤー自身に、次の相手の番の終わりまで手札から出して使うことの禁止
            user = trainer_user(e["trainer_card"])
            if using_trainer.get(user) != e["trainer_card"] or not isinstance(_trainer_effect_of(state, e["trainer_card"]), HAND_LOCK_TRAINERS) \
                    or e["player"] != user or e["source_player"] != user or e["expires_turn"] != e["turn"] + (1 if user == turn_player else 2) \
                    or (e["player"], e["expires_turn"], HAND_TRAINER_LOCK) in trainer_locks_log:
                problems.append(f"{e['turn']} 番の手札から出して使うことの禁止（プレイヤー {e['player']}・{e['expires_turn']} 番まで）が、そのトレーナーの処理ではない")
            trainer_locks_log[(e["player"], e["expires_turn"], HAND_TRAINER_LOCK)] = e
        elif kind == "trainer_lock_added" and e.get("origin") == ATTACK_HAND_TRAINER_LOCK:
            # v0.86: わるいモココの「こうしゅうは」。ワザを使ったプレイヤーの相手に、次の相手の番の終わりまで手札から出して使うことだけの禁止（同じ番に 2 つは与えない）
            if not _same_attack(attack_window, e) or e["source_player"] != attack_window["player"] or e["player"] != 1 - e["source_player"] \
                    or not isinstance(_effect_of_event(state, e), DamageThenLockOpponentHandTrainersOnHeads) \
                    or e["expires_turn"] != e["turn"] + 1 or (e["player"], e["expires_turn"], ATTACK_HAND_TRAINER_LOCK) in trainer_locks_log:
                problems.append(f"{e['turn']} 番の手札から出して使うことの禁止（プレイヤー {e['player']}・{e['expires_turn']} 番まで）が、こうしゅうはの処理のものではない")
            trainer_locks_log[(e["player"], e["expires_turn"], ATTACK_HAND_TRAINER_LOCK)] = e
        elif kind == "trainer_lock_added":
            # v0.47: ずつう・こうしゅうは。ワザを使ったプレイヤーの相手に、次の相手の番の終わりまでの使用の禁止を与える（同じ番に 2 つは与えない）
            if not _same_attack(attack_window, e) or e["source_player"] != attack_window["player"] or e["player"] != 1 - e["source_player"] \
                    or not isinstance(_effect_of_event(state, e), (LockOpponentTrainersNextTurn, DamageThenLockOpponentTrainersOnHeads)) \
                    or e["expires_turn"] != e["turn"] + 1 or (e["player"], e["expires_turn"], "attack") in trainer_locks_log:
                problems.append(f"{e['turn']} 番のトレーナーの使用の禁止（プレイヤー {e['player']}・{e['expires_turn']} 番まで）が、そのワザの処理のものではない")
            trainer_locks_log[(e["player"], e["expires_turn"], "attack")] = e
        elif kind == "trainer_lock_removed":
            info = trainer_locks_log.pop((e["player"], e["expires_turn"], e.get("origin", "attack")), None)
            if info is None or e["reason"] != "expired" or e["turn"] != e["expires_turn"] or e["created_turn"] != info["turn"] \
                    or e["source_player"] != info["source_player"] or e["effect"] != info["effect"]:
                problems.append(f"{e['turn']} 番に消したトレーナーの使用の禁止（プレイヤー {e['player']}・{e['expires_turn']} 番まで）が、与えた禁止の期限と合わない")
        elif kind == "look_at_card":
            # v0.47: ［スパイ］（使ったプレイヤーの番。どちらかの山札の一番上・どちらかのサイド・相手の手札）・おどろかす（相手の手札）。カードは動かない
            zone, holder, card = e["zone"], e["owner"], e["card"]
            if "trainer_card" in e:
                # v0.56: カスミのわがまま（使っている最中のそのトレーナーで、自分のサイドの位置を見る）
                valid = using_trainer.get(e["player"]) == e["trainer_card"] and isinstance(_trainer_effect_of(state, e["trainer_card"]), LookPrizeAskSwapElseDraw) \
                    and zone == "prize" and holder == e["player"]
            elif "power" in e:
                valid = isinstance(_power_effect(state, e["power"]), PeekCard) and e["player"] == turn_player and (zone != "hand" or holder != e["player"]) \
                    and (zone != "deck" or e["position"] == 0)
            else:
                valid = _same_attack(attack_window, e) and e["player"] == attack_window["player"] and holder == 1 - e["player"] and zone == "hand" \
                    and isinstance(_effect_of_event(state, e), LookOpponentHandCardToDeck)
            where = hand[holder] if zone == "hand" else None
            if not valid or owner.get(card) != holder or (where is not None and card not in where) \
                    or (where is None and (card in hand[holder] or card in discard[holder])):
                problems.append(f"{e['turn']} 番に見たカード {card}（プレイヤー {holder} の {zone}）が、その特殊能力・ワザで見られるカードではない")
        elif kind in ("look_at_deck_top", "look_at_deck_top_none"):
            # v0.47: みらいよち。ワザを使ったプレイヤーが、自分または相手の山札の上から見る（相手には見せない）
            effect = _effect_of_event(state, e)
            if isinstance(effect, (LookTopTakeOneThenShuffle, EachPlayerLookTopTakeBasicEnergy)) and kind == "look_at_deck_top":
                # v0.83: フラッシュサーチ（ワザを使ったプレイヤーが自分の山札の上を見て 1 枚を手札に加える）・みずかき（おたがいのプレイヤーが、それぞれ自分の山札の
                # 上を見る）。見るのは山札の上から ``look`` 枚（山札が足りなければ LT1 で止まるので、いつもちょうど ``look`` 枚）
                each = isinstance(effect, EachPlayerLookTopTakeBasicEnergy)
                if not _same_attack(attack_window, e) or e["owner"] != e["player"] or (not each and e["player"] != attack_window["player"]) \
                        or e["count"] != effect.look or len(e["cards"]) != e["count"] or len(set(e["cards"])) != e["count"] \
                        or any(owner.get(uid) != e["owner"] or uid in hand[e["owner"]] or uid in discard[e["owner"]] for uid in e["cards"]):
                    problems.append(f"{e['turn']} 番の {kind} が、山札の上から {getattr(effect, 'look', None)} 枚を見るワザの処理ではない")
            elif not _same_attack(attack_window, e) or e["player"] != attack_window["player"] or not isinstance(effect, ArrangeDeckTopEffect) \
                    or e["owner"] not in (0, 1):
                problems.append(f"{e['turn']} 番の {kind} が、山札の上を見て並べかえるワザの処理ではない")
            elif kind == "look_at_deck_top":
                if not 1 <= e["count"] <= effect.max_cards or len(e["cards"]) != e["count"] or len(set(e["cards"])) != e["count"] \
                        or any(owner.get(uid) != e["owner"] or uid in hand[e["owner"]] or uid in discard[e["owner"]] for uid in e["cards"]):
                    problems.append(f"{e['turn']} 番のみらいよちで見たカード {e['cards']}（{e['count']} 枚）が、プレイヤー {e['owner']} の山札の上の {effect.max_cards} 枚までではない")
                arrange_due = e
        elif kind == "arrange_deck_top":
            if arrange_due is None or prior is not arrange_due or (e["player"], e["owner"], e.get("effect"), e.get("trainer_card"), e["count"]) \
                    != (arrange_due["player"], arrange_due["owner"], arrange_due.get("effect"), arrange_due.get("trainer_card"), arrange_due["count"]) \
                    or sorted(e["cards"]) != sorted(arrange_due["cards"]):
                problems.append(f"{e['turn']} 番のみらいよちでもどした並び {e['cards']} が、すぐ前に見たカードの並べかえではない")
            arrange_due = None
        elif kind == "swap_prize_with_deck_top":
            # v0.47: ［わるふざけ］。自分のサイドの位置と山札の一番上を入れかえる（どちらも見ない）
            if not isinstance(_power_effect(state, e["power"]), SwapPrizeWithDeckTop) or e["player"] != turn_player \
                    or not 0 <= e["prize_position"] < state.rules.prize_count - prizes_taken[e["player"]]:
                problems.append(f"{e['turn']} 番のサイドと山札の一番上の入れかえ（位置 {e['prize_position']}）が、その特殊能力の処理ではない")
            if "face_up_card" in e:
                if e["face_up_card"] not in face_up_log:
                    problems.append(f"{e['turn']} 番に山札の一番上と入れかえたおもてのサイド {e['face_up_card']} が、ログから組み立てたおもてのサイドにない")  # v0.63
                face_up_log.discard(e["face_up_card"])
        elif kind == "discard_attached_trainer":
            discard[owner[e["card"]]].append(e["card"])
            if e["card"] in tools_on.get(e.get("pokemon_id"), ()):
                tools_on[e["pokemon_id"]].remove(e["card"])  # v0.81: 使い終えた・「にげる」でトラッシュしたどうぐ
        elif kind == "return_attached_trainer":
            # v0.66: お上品攻撃。有効期限の番の終わりに、つけたプレイヤー（持ち主）の手札にもどす（ついているトレーナーの行き先が手札の実装だけ）
            if getattr(_trainer_effect_of(state, e["card"]), "expiry_destination", None) != EXPIRE_TO_HAND or owner[e["card"]] != e["player"] \
                    or e.get("reason") != "end_of_turn":
                problems.append(f"{e['turn']} 番に手札にもどしたついているトレーナー {e['card']} が、行き先が手札のトレーナーの有効期限の処理ではない")
            hand[e["player"]].append(e["card"])
        elif kind == "disguise":
            # v0.49: 「ばける」。宣言（pokemon_power）と手札の進化カードを選ぶ決定のあと、使ったポケモンの上に手札の進化カードをのせる（進化ではない。番号・いちばん上の
            # カードは変わらない）
            pid = e["pokemon_id"]
            effect = _power_effect(state, e["power"])
            if not isinstance(effect, Shapeshift) or pid not in in_play or pokemon_owner.get(pid) != e["player"] or e["player"] != turn_player \
                    or ids.get(e["pokemon"]) != pid or pid in disguised or not state.printed_def(e["card"]).is_evolution_pokemon \
                    or e["power"].partition("@")[0] != state.cards[top[pid]].card_id:
                problems.append(f"{e['turn']} 番の disguise（ポケモン {pid}・カード {e['card']}）が、番のプレイヤーの「ばける」の処理ではない")
            from_hand(e, e["player"], e["card"])
            disguised[pid] = e["card"]
        elif kind == "disguise_removed":
            # v0.49: 「ばける」でのせたカードをトラッシュして元にもどした（自分の番の操作・ねむり・マヒ・こんらんになった）
            pid = e["pokemon_id"]
            if disguised.get(pid) != e["card"] or e["reason"] not in ("revert", "special_condition") \
                    or (e["reason"] == "revert" and e["player"] != turn_player):
                problems.append(f"{e['turn']} 番の disguise_removed（ポケモン {pid}・カード {e['card']}）が、ログから組み立てたのせたカード {disguised.get(pid)} と合わない")
            disguised.pop(pid, None)
            discard[e["player"]].append(e["card"])
        elif kind == "recall":
            # v0.49: 「思い出させる」。使っている最中のそのトレーナーの効果で、番のプレイヤーの対戦ポケモン（進化していて、進化前のカードにワザがある）の記録
            if using_trainer.get(e["player"]) != e["card"] or e["player"] != turn_player or active_of.get(e["player"]) != e["pokemon_id"] \
                    or ids.get(e["pokemon"]) != e["pokemon_id"]:
                problems.append(f"{e['turn']} 番の recall（ポケモン {e['pokemon_id']}）が、使っている最中の「思い出させる」・番のプレイヤーの対戦ポケモンのものではない")
        elif kind == "type_shift":
            # v0.48: ［へんしょく］。宣言のすぐあと（色を選ぶ決定のあと）に、使ったポケモンの色を変えた記録。前の記録があれば previous_color・previous_turn
            pid = e["pokemon_id"]
            keys = [] if pid not in top else [f"{definition.id}@power{index}" for definition, index, power in power_defs(pid)
                                               if isinstance(state.effects.power_effect(definition.id, power), ShiftColor)]  # v0.49: 今持つ特殊能力
            if e["power"] not in keys or pid not in in_play or pokemon_owner.get(pid) != e["player"] or e["player"] != turn_player:
                problems.append(f"{e['turn']} 番の type_shift（ポケモン {pid}）が、番のプレイヤーの場のポケモンの［へんしょく］の処理ではない")
            old = shifts.get(pid)
            if (None if old is None else (old["color"].value, old["turn"])) != ((e["previous_color"], e["previous_turn"]) if "previous_color" in e else None):
                problems.append(f"{e['turn']} 番の type_shift（ポケモン {pid}）の前の記録 {e.get('previous_color')} が、ログから組み立てた {old} と違う")
            if EnergyType(e["color"]) not in COLORS:
                problems.append(f"{e['turn']} 番の type_shift の色 {e['color']} が色ではない")
            shifts[pid] = {"color": EnergyType(e["color"]), "turn": e["turn"], "source_card": top.get(pid), "returned": False}
        elif kind == "energy_burn":
            # v0.31: 特殊能力（エナジーバーン）。ついているエネルギーのタイプだけが変わる（カードは動かない）。直前に同じポケモンの宣言
            if declared != (e["turn"], e["player"], e["pokemon_id"]):
                problems.append(f"{e['turn']} 番の energy_burn の直前に、同じポケモンの特殊能力の宣言（pokemon_power）がない")
            declared = None
            card_id, _, index = e["power"].partition("@power")
            entry = state.effects.power_entry(card_id, int(index)) if index.isdigit() else None
            if entry is None or not isinstance(entry.effect, ConvertAttachedEnergy) or e["pokemon_id"] not in top \
                    or state.cards[top[e["pokemon_id"]]].card_id != card_id:
                problems.append(f"{e['turn']} 番の energy_burn の特殊能力 {e['power']} が、使ったポケモンのエネルギーのタイプを変える特殊能力ではない")
            if sorted(e["energies"]) != sorted(energy.get(e["pokemon_id"], [])):
                problems.append(f"{e['turn']} 番の energy_burn のエネルギー {e['energies']} が、ログから組み立てた {energy.get(e['pokemon_id'])} と違う")
        elif kind == "power_heal":
            # v0.31: 特殊能力のダメージカウンターをとりのぞく処理。宣言する（しぜんになおる。直前に同じポケモンの宣言）か、炎エネルギーカードを
            # つけたとき（ほのおでかいふく。trigger はつけたカードで、このポケモンについている炎の基本エネルギーカード）
            pid = e["pokemon_id"]
            card_id, _, index = e["power"].partition("@power")
            entry = state.effects.power_entry(card_id, int(index)) if index.isdigit() else None
            if "trigger" in e:
                if entry is None or not isinstance(entry.effect, HealOnEnergyAttach) or e["trigger"] not in energy.get(pid, []) \
                        or state.printed_def(e["trigger"]).provides is not entry.effect.energy_type:
                    problems.append(f"{e['turn']} 番の power_heal（ポケモン {pid}）が、ついた {e['trigger']} でとりのぞく特殊能力の処理ではない")
                if pid in exclusive:
                    problems.append(f"{e['turn']} 番に、{exclusive[pid]} のポケモン {pid} の「ほのおでかいふく」がはたらいた")
            elif entry is not None and isinstance(entry.effect, HealOwnPokemonOnHeads):
                # v0.42: ヒーリング。直前に使ったプレイヤーの「おもて」のコイン（その特殊能力）があり、とりのぞくのは自分の場のポケモン（使ったポケモン
                # user_pokemon_id は場にいる）から、登録の数まで
                coin = prior or {}
                user = e.get("user_pokemon_id")
                if (coin.get("kind"), coin.get("source"), coin.get("effect"), coin.get("result"), coin.get("player")) != (
                        "coin_flip", "power", e["power"], "heads", e["player"]) or user not in in_play or pokemon_owner.get(user) != e["player"] \
                        or pokemon_owner.get(pid) != e["player"] or state.cards[top[user]].card_id != card_id \
                        or e["counters"] != min(entry.effect.counters, damage[pid] // state.rules.damage_per_counter):
                    problems.append(f"{e['turn']} 番の power_heal（ポケモン {pid}）が、「おもて」のあとの自分の場のポケモンのヒーリングの処理と合わない")
            else:
                if declared != (e["turn"], e["player"], pid):
                    problems.append(f"{e['turn']} 番の power_heal の直前に、同じポケモンの特殊能力の宣言（pokemon_power）がない")
                declared = None
                if entry is None or not isinstance(entry.effect, RemoveOwnCounterOncePerTurn):
                    problems.append(f"{e['turn']} 番の power_heal の特殊能力 {e['power']} が、宣言してとりのぞく特殊能力ではない")
            if e["amount"] <= 0 or e["amount"] != e["counters"] * state.rules.damage_per_counter or e["damage_before"] != damage[pid]:
                problems.append(f"{e['turn']} 番の power_heal の量 {e['amount']}・前のダメージ {e['damage_before']} が合わない（ログ {damage[pid]}）")
            damage[pid] -= e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の power_heal のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "tag_team_heal":
            # v0.84: ［たすけだす］。手札から進化させたベンチのこのカードの宣言のすぐあとに、自分の対戦ポケモンのカウンターを登録の数まで（のっている数まで。0 個もある）
            pid = e["pokemon_id"]
            effect = _power_effect(state, e["power"])
            if not isinstance(effect, HealActiveThenSwitchOnBenchEntry) or active_of.get(e["player"]) != pid or pokemon_owner.get(pid) != e["player"] \
                    or e["damage_before"] != damage[pid] or e["counters"] != min(effect.counters, damage[pid] // state.rules.damage_per_counter) \
                    or e["amount"] != e["counters"] * state.rules.damage_per_counter:
                problems.append(f"{e['turn']} 番の tag_team_heal（ポケモン {pid}）が、自分の対戦ポケモンから登録の数までとりのぞく処理と合わない（ログ {damage.get(pid)}）")
            damage[pid] -= e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の tag_team_heal のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "bench_from_deck" and "power" in e:
            # v0.43: てしたをよぶ（場に出たときの特殊能力）。自分の山札のたねポケモンを、手札を通さずにベンチに出す（最大 2 枚。続けて出し、そのあとに山札を切る）
            effect = _power_effect(state, e["power"])
            uid = e["card"]
            definition = state.printed_def(uid)
            if not isinstance(effect, BenchBasicsFromDeckOnEntry) or pokemon_owner.get(e["pokemon_id"]) != e["player"] or owner.get(uid) != e["player"] \
                    or uid in hand[e["player"]] or uid in discard[e["player"]] or uid in ids or not definition.is_basic_pokemon:
                problems.append(f"{e['turn']} 番に特殊能力 {e['power']} でベンチに出したカード {uid} が、プレイヤー {e['player']} の山札のたねポケモンではない")
            benched = (shuffle_due["count"] + 1) if shuffle_due is not None and shuffle_due.get("power") == e["power"] and "count" in shuffle_due else 1
            if isinstance(effect, BenchBasicsFromDeckOnEntry) and benched > effect.max_cards:
                problems.append(f"{e['turn']} 番のてしたをよぶで、1 回に {benched} 枚ベンチに出した")
            enter(uid)
            if ids[uid] != e["to_pokemon_id"]:
                problems.append(f"{e['turn']} 番にベンチに出したポケモンの番号 {e['to_pokemon_id']} が、ログから組み立てた {ids[uid]} と違う")
            shuffle_due = {**e, "count": benched}
        elif kind in ("bench_from_deck", "bench_from_deck_none"):
            # v0.32: ワザ（なかまをよぶ・ふえる）で、ワザを使ったプレイヤーの山札の、説明の名前のたねポケモンを、手札を通さずにベンチに出す（山札は組み立て
            # 直さないので、持ち主・手札・トラッシュ・場にないことで確かめる）。どちらのあとにも同じプレイヤーの山札を切る（shuffle）
            # v0.34: たすけをよぶは名前でなくタイプで選ぶ（登録の ``pokemon_type``）
            # v0.45: タケシのイシツブテのたすけをよぶは「(owner)のポケモン」（名前が「(owner)の」で始まるたねポケモン。登録の ``owner``）
            entry = state.effects.attack_entry(*_attack_key(e["effect"]))
            names = getattr(entry.effect, "names", None) if entry is not None else None
            pokemon_type = getattr(entry.effect, "pokemon_type", None) if entry is not None else None
            owner_name = entry.effect.owner if entry is not None and isinstance(entry.effect, PutOwnerBasicFromDeckOntoBenchOnHeads) else None
            if attack_window is None or e["player"] != attack_window["player"] or e["pokemon_id"] != attack_window["pokemon_id"] \
                    or [names, pokemon_type, owner_name].count(None) != 2:
                problems.append(f"{e['turn']} 番の {kind} が、山札からベンチに出すワザ（登録の名前・タイプ）の処理の中にない")
            if kind == "bench_from_deck":
                uid = e["card"]
                definition = state.printed_def(uid)
                if owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]] or uid in ids \
                        or not definition.is_basic_pokemon or (names is not None and definition.name_ja not in names) \
                        or (pokemon_type is not None and definition.pokemon_type is not pokemon_type) \
                        or (owner_name is not None and not definition.name_ja.startswith(f"{owner_name}の")):
                    problems.append(f"{e['turn']} 番にベンチに出したカード {uid} が、プレイヤー {e['player']} の山札の、名前 {names}・タイプ {pokemon_type} の"
                                    "たねポケモンではない")
                enter(uid)
                if ids[uid] != e["to_pokemon_id"]:
                    problems.append(f"{e['turn']} 番にベンチに出したポケモンの番号 {e['to_pokemon_id']} が、ログから組み立てた {ids[uid]} と違う")
            shuffle_due = e
        elif kind == "attack_heal":
            # v0.31: ワザ（ぼーっとする）で、ワザを使ったポケモンのダメージカウンターをとりのぞく。v0.41: 自分の場のポケモン全員（かいふくりんぷん・
            # ダメージシフト）・お互いの場のポケモン全員（みんなでかいふく）からとりのぞくワザもある（とりのぞいてよいポケモンは登録の実装で決める）。
            # とりのぞくのはのっている数まで・1 つ以上（GR-2000-P320-RECOVERY）
            pid = e["pokemon_id"]
            effect = _effect_of_event(state, e) if attack_window is not None else None
            if isinstance(effect, HealAllPokemonBothSides):
                allowed = pid in in_play
            elif isinstance(effect, HealChosenOpponentThenDraw):
                # v0.42: よいおこない。相手の場のポケモン 1 匹から、選んだ数（1 つ以上）。すぐあとに、ワザを使ったプレイヤーがとりのぞいた数まで引く
                allowed = pid in in_play and pokemon_owner.get(pid) != attack_window["player"] and e.get("attacker") == attack_window["player"]
                draw_due = (attack_window["player"], e["counters"], e["turn"], "よいおこないの attack_heal")
            elif isinstance(effect, (CoinsHealOwnPokemon, MoveOwnCountersToOpponent, HealOwnPokemonWithoutDamage)):
                allowed = pid in in_play and pokemon_owner.get(pid) == attack_window["player"]
            elif isinstance(effect, (HealChosenBenchByEnergy, CoinWashChosenBench)):
                # v0.83: いやしのみず・あらいながす。自分の控えポケモン 1 匹
                allowed = pid in in_play and pokemon_owner.get(pid) == attack_window["player"] and pid != attack_window["pokemon_id"]
            elif isinstance(effect, CoinChosenSideHealAttack):
                # v0.85: あまいかおり。コインで決めたどちらかの場のポケモン 1 匹（自分の場ならワザを使ったポケモンも）
                allowed = pid in in_play and e.get("attacker") == attack_window["player"]
            elif isinstance(effect, DamageSleepThenHealBothBench):
                # v0.83: ヒプノシャワー。おたがいの控えポケモン全員（バトル場のポケモンは除く）
                allowed = pid in in_play and pid != attack_window["pokemon_id"] and pid != active_of.get(1 - attack_window["player"])
            else:
                allowed = attack_window is not None and pid == attack_window["pokemon_id"]
            per = state.rules.damage_per_counter
            if not allowed or e["damage_before"] != damage[pid] or e["player"] != pokemon_owner.get(pid) or e["amount"] != e["counters"] * per \
                    or e["amount"] > damage[pid]:
                problems.append(f"{e['turn']} 番の attack_heal（ポケモン {pid}）が、そのワザでとりのぞけるポケモンでない・前のダメージ・数が合わない")
            if isinstance(effect, MoveOwnCountersToOpponent):
                if e["counters"] != 1:
                    problems.append(f"{e['turn']} 番のダメージシフトでとりのぞいた数 {e['counters']} が 1 つではない")
                attack_window["shifted"] = attack_window.get("shifted", 0) + e["counters"]
            damage[pid] -= e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の attack_heal のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "place_damage_counters":
            # v0.41: ワザ（ダメージシフト）で、とりのぞいたダメージカウンターをすべて相手の対戦ポケモンにのせる（ダメージではない。GR-2000-P320-COUNTER-MOVE）
            pid = e["pokemon_id"]
            effect = _effect_of_event(state, e) if attack_window is not None else None
            if isinstance(effect, PlaceCountersOnDamagedOpponentPokemon):
                # v0.48: ダメージぞうふく。相手の場の、ダメージカウンターがのっているポケモンに登録の数ずつ（ダメージではない。最大HPで上限をつけない）
                if pid not in in_play or pokemon_owner.get(pid) != e["player"] or e["player"] == attack_window["player"] or e["damage_before"] != damage[pid] \
                        or damage[pid] <= 0 or e["counters"] != effect.counters or e["amount"] != e["counters"] * state.rules.damage_per_counter:
                    problems.append(f"{e['turn']} 番の place_damage_counters（ポケモン {pid}）が、ダメージカウンターがのっている相手のポケモンに {effect.counters} 個のせる処理と合わない")
                damage[pid] += e["amount"]
                if damage[pid] != e["total_damage"]:
                    problems.append(f"{e['turn']} 番の place_damage_counters のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
                continue
            if isinstance(effect, BenchBasicFromEitherDiscard):
                # v0.51: よみがえらせる。同じワザでトラッシュからベンチに出したポケモンに、出したあとの今有効な最大HPの半分（切り捨て）（ダメージではない）
                per = state.rules.damage_per_counter
                if pid != attack_window.get("discard_entered") or e["damage_before"] != damage[pid] or e["counters"] != max_hp_now(pid) // per // 2 \
                        or e["counters"] <= 0 or e["amount"] != e["counters"] * per or pokemon_owner.get(pid) != e["player"]:
                    problems.append(f"{e['turn']} 番の place_damage_counters（ポケモン {pid}）が、よみがえらせるで出したポケモンに HP の半分（切り捨て）をのせる処理と合わない")
                damage[pid] += e["amount"]
                if damage[pid] != e["total_damage"]:
                    problems.append(f"{e['turn']} 番の place_damage_counters のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
                continue
            if isinstance(effect, PlaceCountersToRemainingHpOnHeads):
                # v0.42: ライフダウン。相手の対戦ポケモンの残り HP が登録の数になるまで（ダメージではない）
                hp = hp_of(pid)
                if pid not in in_play or pokemon_owner.get(pid) != e["player"] or e["player"] == attack_window["player"] or e["damage_before"] != damage[pid] \
                        or e["total_damage"] != hp - effect.remaining or e["amount"] != e["counters"] * state.rules.damage_per_counter or e["counters"] <= 0:
                    problems.append(f"{e['turn']} 番の place_damage_counters（ポケモン {pid}）が、残り HP を {effect.remaining} にするライフダウンの処理と合わない")
                damage[pid] += e["amount"]
                continue
            if not isinstance(effect, MoveOwnCountersToOpponent) or pid not in in_play or pokemon_owner.get(pid) != e["player"] \
                    or e["player"] == attack_window["player"] or e["damage_before"] != damage[pid] \
                    or e["counters"] != attack_window.get("shifted", 0) or e["amount"] != e["counters"] * state.rules.damage_per_counter:
                problems.append(f"{e['turn']} 番の place_damage_counters（ポケモン {pid}）が、そのワザでとりのぞいた数を相手のポケモンにのせる処理と合わない")
            damage[pid] += e["amount"]
            if damage[pid] != e["total_damage"]:
                problems.append(f"{e['turn']} 番の place_damage_counters のあとのダメージ {e['total_damage']} が、ログから組み立てた {damage[pid]} と違う")
        elif kind == "swap_damage_counters":
            # v0.41: ワザ（チェンジダメージ）で、ワザを使ったポケモンと相手の対戦ポケモンのダメージカウンターを、取り替える前の双方の数で取り替える
            own, other = e["pokemon_id"], e["opponent_pokemon_id"]
            effect = _effect_of_event(state, e) if attack_window is not None else None
            if not isinstance(effect, SwapCountersOnHeads) or own != attack_window["pokemon_id"] or pokemon_owner.get(other) != e["opponent"] \
                    or e["opponent"] == e["player"] or (e["damage_before"], e["opponent_damage_before"]) != (damage[own], damage[other]) \
                    or (e["total_damage"], e["opponent_total_damage"]) != (damage[other], damage[own]) or damage[own] == damage[other]:
                problems.append(f"{e['turn']} 番の swap_damage_counters（{own}・{other}）が、取り替える前の双方の数と合わない（ログ {damage[own]}・{damage[other]}）")
            damage[own], damage[other] = e["total_damage"], e["opponent_total_damage"]
        elif kind in ("attach_energy_from_deck", "attach_energy_from_deck_none", "deck_energy_evaded"):
            # v0.41: ワザ（ひなたぼっこ）で、ワザを使ったプレイヤーの山札の基本エネルギーカードを、ワザを使ったポケモンにつける（手札を通さない）。
            # つけた・つけなかった・選べるものがなかった、のどれでも、すぐあとに山札を切る
            # v0.75: もえあがる・しおまねき（山札を切らない）もワザを使ったポケモンにつける。エナジーサポートは自分の控えポケモンにつける（「とうめい」で受けなければ
            # deck_energy_evaded。カードは持ち主のトラッシュ）
            pid = e["pokemon_id"]
            effect = _effect_of_event(state, e) if attack_window is not None else None
            # v0.82: あたためる（ChooseBenchThenAttachFromDeck）も自分の控えポケモンにつける（控え → カードの順に選ぶ）
            to_bench = isinstance(effect, (AttachEnergyFromDeckToBench, ChooseBenchThenAttachFromDeck)) and kind != "attach_energy_from_deck_none"
            if not isinstance(effect, (AttachEnergyFromDeckToSelf, AttachEnergyFromDeckToSelfExactly, CoinAttachEnergyFromDeckToSelf, AttachEnergyFromDeckToBench,
                                       ChooseBenchThenAttachFromDeck, AttachFromDeckUpToNamedCount)) \
                    or (kind == "deck_energy_evaded") != (to_bench and kind == "deck_energy_evaded") \
                    or (pid == attack_window["pokemon_id"]) == to_bench or e["player"] != attack_window["player"] \
                    or to_bench and (pokemon_owner.get(pid) != e["player"] or pid not in in_play):
                problems.append(f"{e['turn']} 番の {kind}（ポケモン {pid}）が、山札からエネルギーをつけるワザの処理の中にない")
            elif kind == "attach_energy_from_deck":
                uid = e["card"]
                definition = state.printed_def(uid)
                if owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]] or not definition.is_basic_energy \
                        or definition.provides is not effect.energy_type:
                    problems.append(f"{e['turn']} 番に山札からつけたカード {uid} が、プレイヤー {e['player']} の山札の「{effect.energy_type.ja}」の基本エネルギーカードではない")
                energy.setdefault(pid, []).append(uid)
            elif kind == "deck_energy_evaded":
                uid = e["card"]  # v0.75: 山札のカードを、持ち主のトラッシュに置いた
                if owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]] or not state.printed_def(uid).is_basic_energy:
                    problems.append(f"{e['turn']} 番に山札からトラッシュに置いたカード {uid} が、プレイヤー {e['player']} の山札の基本エネルギーカードではない")
                discard[e["player"]].append(uid)
            if isinstance(effect, AttachFromDeckUpToNamedCount) and kind == "attach_energy_from_deck":
                static_attaches.add(id(e))  # v0.85: せいでんきは何枚もつけてから 1 回だけ切る（続くつけるログのあいだは待ち、最後のあとに shuffle を求める）
                shuffle_due = e
            elif not isinstance(effect, CoinAttachEnergyFromDeckToSelf):
                shuffle_due = e  # v0.75: しおまねきは山札を切らない（説明に「よく切る」がない）
        elif kind == "evolve_from_deck_none":
            # v0.42: つきのちから（「おもて」）で、山札に重ねられる進化カードがなかった。すぐあとに山札を切る
            if "power" in e:
                # v0.44: ［うか］（「おもて」）で、山札に重ねられるカードがなかった。直前に持ち主の「おもて」のコイン。すぐあとに山札を切る
                chain = isinstance(_power_effect(state, e["power"]), EvolveFromDeckOnOtherEvolution)
                if chain:
                    # v0.86: ［れんさしんか］（コインがない）。直前にこの特殊能力の宣言（そのあいだに決定がある）
                    if prior is None or prior["kind"] != "pokemon_power" or prior.get("pokemon_id") != e["pokemon_id"]:
                        problems.append(f"{e['turn']} 番の evolve_from_deck_none（特殊能力 {e['power']}）が、［れんさしんか］の宣言のすぐあとにない")
                elif not isinstance(_power_effect(state, e["power"]), (CoinEvolveSelfFromDeck, EvolveFromDeckByAttachedEnergyColor)) or prior is None \
                        or prior["kind"] != "coin_flip" or prior.get("effect") != e["power"] or prior["result"] != "heads":
                    problems.append(f"{e['turn']} 番の evolve_from_deck_none（特殊能力 {e['power']}）が、［うか］の「おもて」のすぐあとにない")
            elif not _same_attack(attack_window, e) or not isinstance(_effect_of_event(state, e), (EvolveFromDeckOnHeads, EvolveSelfFromDeck,
                                                                                                    EachPlayerEvolutionSong)):
                problems.append(f"{e['turn']} 番の evolve_from_deck_none が、山札から進化させるワザの処理の中にない")
            shuffle_due = e
        elif kind == "return_energy_to_hand":
            # v0.42: ワザ（エネループ）で、ワザを使ったポケモンについているエネルギーカードを手札にもどす（ダメージの要素より前）
            pid = e["pokemon_id"]
            if attack_window is None or pid != attack_window["pokemon_id"] or e["player"] != attack_window["player"] \
                    or e["energy"] not in energy.get(pid, []) or window_damaged(attack_window):
                problems.append(f"{e['turn']} 番に手札にもどしたエネルギー {e['energy']} が、ワザを使ったポケモンについていた・ダメージの要素より前のものではない")
            else:
                energy[pid].remove(e["energy"])
                hand[e["player"]].append(e["energy"])
        elif kind == "return_in_play_to_hand":
            # v0.42: 特殊能力（おくびょう。ついているカードをトラッシュしたすぐあと）・ワザ（ようせいのきせき）で、自分の場のポケモンを手札にもどす（きぜつでは
            # ない。重なったカードとついているカードもいっしょに手札へ）
            pid = e["pokemon_id"]
            if "power" in e:
                valid = prior is not None and prior["kind"] == "discard_attached_cards" and prior.get("power") == e["power"] and prior["pokemon_id"] == pid \
                    and isinstance(_power_effect(state, e["power"]), ReturnSelfToHand)
            elif "stadium_card" in e:
                # v0.57: せまいジムが場に出た時、ベンチが上限より多いプレイヤーが控えポケモン 1 匹を手札へ（場に出したすぐあとから）
                valid = stadium_zone is not None and stadium_zone[0] == e["stadium_card"] and active_of.get(e["player"]) != pid \
                    and sum(1 for q in in_play if pokemon_owner.get(q) == e["player"]) - (1 if active_of.get(e["player"]) in in_play else 0) > bench_limit_now()
            elif "trainer_card" in e:
                # v0.56: ロケット団員（2 枚とも「おもて」）。使っている最中のそのトレーナーで、相手（持ち主）の控えポケモンを持ち主の手札へ
                user = trainer_user(e["trainer_card"])
                trainer_effect = _trainer_effect_of(state, e["trainer_card"])
                valid = using_trainer.get(user) == e["trainer_card"] and isinstance(trainer_effect, CoinsReturnOpponentBenchElseEndTurn) \
                    and e["player"] == 1 - user and active_of.get(e["player"]) != pid
                # v0.73: スーパーポケモン回収（「おもて」のとき、使ったプレイヤーの自分の場のポケモン。ログの zone はもどす前の場所）
                valid = valid or (using_trainer.get(user) == e["trainer_card"] and isinstance(trainer_effect, CoinReturnOwnPokemonWithAttachedToHand)
                                  and e["player"] == user and e.get("zone") == ("active" if active_of.get(e["player"]) == pid else "bench"))
            elif _same_attack(attack_window, e) and isinstance(_effect_of_event(state, e), DamageThenReturnOpponentToHand):
                # v0.62: ハリケーン（相手の対戦ポケモンを持ち主の手札へ。ダメージの要素のあと・きぜつしていないとき）
                valid = e["player"] == 1 - attack_window["player"] and active_of.get(e["player"]) == pid and window_damaged(attack_window)
            else:
                # v0.44: スターブーメラン（DamageThenReturnSelfToHandOnHeads。ワザを使ったポケモン自身）
                valid = _same_attack(attack_window, e) and e["player"] == attack_window["player"] \
                    and isinstance(_effect_of_event(state, e), (ReturnOwnPokemonToHandOnHeads, DamageThenReturnSelfToHandOnHeads, DamageThenBubbleJump))
            if not valid or pid not in in_play or pokemon_owner.get(pid) != e["player"] or ids.get(e["pokemon"]) != pid:
                problems.append(f"{e['turn']} 番に手札にもどしたポケモン {pid} が、その特殊能力・ワザの処理のものではない")
            if sorted(e["energy"]) != sorted(energy.get(pid, [])) or e["damage"] != damage[pid]:
                problems.append(f"{e['turn']} 番に手札にもどしたポケモン {pid} のエネルギー {e['energy']}・ダメージ {e['damage']} がログの組み立てと違う")
            if sorted(e["cards"]) != sorted([*e["evolution_stack"], e["pokemon"], *(() if "disguise" not in e else (e["disguise"],)), *e["energy"], *e["trainers"]]) \
                    or any(owner.get(uid) != e["player"] for uid in e["cards"]) or e.get("disguise") != disguised.get(pid):
                problems.append(f"{e['turn']} 番に手札にもどしたカード {e['cards']} が、そのポケモンのカード・ついているカードと合わない")
            disguised.pop(pid, None)  # v0.49
            in_play.discard(pid)
            exclusive.pop(pid, None)
            poisoned.pop(pid, None)
            energy[pid] = []
            damage[pid] = 0
            hand[e["player"]].extend(e["cards"])
        elif kind in ("power_confusion", "power_confusion_skipped"):
            # v0.42: 「ぼうぎょかふん」（バトル場で相手のワザのダメージを受けたときに自動的にはたらく。特殊状態でもはたらく。かがくへんかガスは止める）。
            # 直前に持ち主の「ぼうぎょかふん」のコイン。「おもて」なら、すぐあとにダメージを与えたポケモン（ワザを使ったポケモン）をこんらんにする
            holder = e["pokemon_id"]
            effect = _power_effect(state, e["power"])
            if attack_window is None or (e["attacker"], e["attacker_pokemon_id"], e["effect"]) != (
                    attack_window["player"], attack_window["pokemon_id"], attack_window["effect"]) or holder not in in_play \
                    or pokemon_owner.get(holder) != e["player"] or e["player"] == e["attacker"] or not isinstance(effect, ConfuseDamageSourceOnHeads) \
                    or e["power"] not in [f"{d.id}@power{i}" for d, i, _ in power_defs(holder)] or holder not in attack_window.get("damaged", set()):
                problems.append(f"{e['turn']} 番の {kind}（ポケモン {holder}）が、相手のワザのダメージを受けた「ぼうぎょかふん」のポケモンの処理ではない")
            power = next((pw for definition, index, pw in power_defs(holder) if f"{definition.id}@power{index}" == e["power"]), None) if holder in top else None
            if power is not None and [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(power)]:
                problems.append(f"{e['turn']} 番に、かがくへんかガスに消されている「ぼうぎょかふん」（ポケモン {holder}）がはたらいた")
            target = e["attacker_pokemon_id"]
            if kind == "power_confusion_skipped":
                if e["reason"] != "knocked_out" or target not in in_play or damage[target] < max_hp_now(target):
                    problems.append(f"{e['turn']} 番に、きぜつしていない相手 {target} に「ぼうぎょかふん」がはたらかなかった（{e['reason']}）")
            else:
                coin = prior or {}
                if (coin.get("kind"), coin.get("source"), coin.get("player"), coin.get("effect"), coin.get("result")) != (
                        "coin_flip", "power", e["player"], e["power"], e["result"]) or e["confused"] != (e["result"] == "heads"):
                    problems.append(f"{e['turn']} 番の「ぼうぎょかふん」（ポケモン {holder}）の直前に、持ち主の同じ結果のコインがない・結果が合わない")
                if e["confused"]:
                    confusion_due = (target, e["power"])
        elif kind == "discard_attached_energy":
            # v0.31: ワザ（スーパーデストロイ・メラメラ）で、相手のポケモンについているエネルギーカードを持ち主のトラッシュへ
            pid = e["pokemon_id"]
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or e["energy"] not in energy.get(pid, []) \
                    or attack_window is None or e["attacker"] != attack_window["player"] or e["player"] == attack_window["player"]:
                problems.append(f"{e['turn']} 番の相手のエネルギーのトラッシュ {e['energy']} が、ログから組み立てた相手のポケモン {pid} のエネルギーにない")
            else:
                energy[pid].remove(e["energy"])
                discard[e["player"]].append(e["energy"])
        elif kind == "recover_trainer":
            # v0.31: ワザ（ゴミあさり）で、ワザを使ったプレイヤーのトラッシュのトレーナーカード 1 枚を手札に加える
            uid = e["card"]
            if uid not in discard[e["player"]] or state.printed_def(uid).category != "trainer":
                problems.append(f"{e['turn']} 番に手札に加えたカード {uid} が、ログから組み立てたプレイヤー {e['player']} のトラッシュのトレーナーカードにない")
            else:
                discard[e["player"]].remove(uid)
                hand[e["player"]].append(uid)
        elif kind == "attach_energy_from_discard":
            # v0.31: ワザ（たいでん）で、ワザを使ったプレイヤーのトラッシュの基本エネルギーカードを、ワザを使ったポケモンにつける
            pid = e["pokemon_id"]
            if not 1 <= len(e["cards"]) <= 2 or attack_window is None or pid != attack_window["pokemon_id"]:
                problems.append(f"{e['turn']} 番のトラッシュからつけたエネルギー {e['cards']} の枚数・ポケモンが合わない")
            # v0.75: エネルギーきゅうしゅう（AttachDiscardEnergyCardsToSelf）は「エネルギーカード」（特殊エネルギーも）
            any_energy = isinstance(_effect_of_event(state, e) if attack_window is not None else None, AttachDiscardEnergyCardsToSelf)
            for uid in e["cards"]:
                definition = state.printed_def(uid)
                if uid not in discard[e["player"]] or not (definition.category == "energy" if any_energy else definition.is_basic_energy):
                    problems.append(f"{e['turn']} 番につけたカード {uid} が、ログから組み立てたプレイヤー {e['player']} のトラッシュの基本エネルギーカードにない")
                    continue
                discard[e["player"]].remove(uid)
                energy.setdefault(pid, []).append(uid)
        elif kind == "attack_attach_energy":
            # v0.31: ワザ（エナジーボム）で、ワザを使ったポケモンのエネルギーカードを、自分の控えポケモンにつける（同じカード）
            source, target = e["pokemon_id"], e["to_pokemon_id"]
            if source == target or target not in in_play or pokemon_owner.get(target) != e["player"] or e["energy"] not in energy.get(source, []):
                problems.append(f"{e['turn']} 番の控えにつけたエネルギー {e['energy']}（{source} → {target}）が、ログから組み立てた場と合わない")
            else:
                energy[source].remove(e["energy"])
                energy[target].append(e["energy"])
        elif kind == "discard_from_deck":
            # v0.31: ワザ（やまやき・マグマふんしゅつ）で、山札の上からカードをトラッシュする（山札は組み立て直さないので、持ち主・手札とトラッシュに
            # ないことで確かめる）
            for uid in e["cards"]:
                if owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]]:
                    problems.append(f"{e['turn']} 番に山札からトラッシュしたカード {uid} が、プレイヤー {e['player']} の山札のカードではない")
                    continue
                discard[e["player"]].append(uid)
        elif kind == "power_discard_deck":
            # v0.85: ［あばれんぼう］で、相手か自分の山札の上から 5 枚をトラッシュした（山札は組み立て直さないので、持ち主・手札とトラッシュにないことで確かめる）
            for uid in e["cards"]:
                if owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]]:
                    problems.append(f"{e['turn']} 番に［あばれんぼう］で山札からトラッシュしたカード {uid} が、プレイヤー {e['player']} の山札のカードではない")
                    continue
                discard[e["player"]].append(uid)
        elif kind == "power_attach_from_deck":
            # v0.85: ［ファイヤーブースト］で、山札の「炎」の基本エネルギーカードを特殊能力を使ったポケモンにつけた（手札を通さない）
            uid, pid = e["card"], e["pokemon_id"]
            definition = state.printed_def(uid)
            if owner.get(uid) != e["player"] or uid in hand[e["player"]] or uid in discard[e["player"]] or not definition.is_basic_energy or pid not in in_play:
                problems.append(f"{e['turn']} 番に［ファイヤーブースト］でつけたカード {uid} が、プレイヤー {e['player']} の山札の基本エネルギーカードではない")
            energy.setdefault(pid, []).append(uid)
        elif kind == "power_attach_from_discard":
            # v0.85: ［ファイヤーリチャージ］で、トラッシュの「炎」の基本エネルギーカードを自分の場の「炎」ポケモンにつけた
            # v0.86: ［おたけび］なら、すぐ前に同じ特殊能力でトラッシュしたカード（今回トラッシュした 5 枚）の中のカードだけ（前からトラッシュにあったカードは使わない）
            pid = e["pokemon_id"]
            if isinstance(_power_effect(state, e.get("power")), DiscardDeckTopAttachTypeEnergyThenEndTurn):
                milled = howl_milled.get(e["player"])
                if milled is None or milled[0] != e["power"] or not set(e["cards"]) <= milled[1]:
                    problems.append(f"{e['turn']} 番に［おたけび］でつけたカード {e['cards']} が、すぐ前にこの特殊能力でトラッシュしたカードではない")
            for uid in e["cards"]:
                if uid not in discard[e["player"]] or not state.printed_def(uid).is_basic_energy or pokemon_owner.get(pid) != e["player"]:
                    problems.append(f"{e['turn']} 番に［ファイヤーリチャージ］でつけたカード {uid} が、プレイヤー {e['player']} のトラッシュの基本エネルギーカードではない")
                    continue
                discard[e["player"]].remove(uid)
                energy.setdefault(pid, []).append(uid)
        elif kind == "attack_discard_to_deck":
            # v0.85: ぎゃくりゅうで、トラッシュの「水」エネルギーカードをすべて山札にもどした（山札は組み立て直さない）
            for uid in e["cards"]:
                if uid not in discard[e["player"]]:
                    problems.append(f"{e['turn']} 番にトラッシュから山札にもどしたカード {uid} が、ログから組み立てたプレイヤー {e['player']} のトラッシュにない")
                    continue
                discard[e["player"]].remove(uid)
        elif kind == "miracle_energy_discarded":
            # v0.85: ミラクルエネルギーを、つけているポケモンから持ち主のトラッシュに置いた（つけた番の終わり・つけているポケモンが「ひかる」「やさしい」でなくなった）
            pid = e["pokemon_id"]
            if e["card"] not in energy.get(pid, []) or state.printed_def(e["card"]).name_ja != "ミラクルエネルギー":
                problems.append(f"{e['turn']} 番にトラッシュしたミラクルエネルギー {e['card']} が、ログから組み立てたポケモン {pid} についていない")
            else:
                energy[pid].remove(e["card"])
                discard[owner[e["card"]]].append(e["card"])
        elif kind == "destiny_bond":
            # v0.31: 「みちづれ」の効果のポケモンがきぜつしたので、相手の対戦ポケモンもきぜつする（ダメージではない）
            if e["pokemon_id"] in in_play and damage[e["pokemon_id"]] < max_hp_now(e["pokemon_id"]):
                problems.append(f"{e['turn']} 番の「みちづれ」（ポケモン {e['pokemon_id']}）が、きぜつしていないポケモンの効果ではたらいた")
            destiny_knocked.add(e["target_pokemon_id"])
        elif kind == "return_in_play_to_deck":
            # v0.36: ワザ（くもがくれガス）で、ワザを使ったポケモンと、ついているすべてのカードを持ち主の山札にもどす（きぜつではない。山札は組み立て
            # 直さないので、持ち主・場にあったことで確かめる）。すぐあとに（持続する効果を消したログのあと）同じプレイヤーの山札を切る
            pid = e["pokemon_id"]
            # v0.40: わるいカイリキーの「つまみだす」は、相手の対戦ポケモンを持ち主（相手）の山札にもどす（登録の実装 ReturnOpponentActiveToDeck）。
            # v0.48: ナツメのゲンガーの「やみのこえ」も同じ。相手を山札にもどすワザは、登録の実装の相手への効果の要素（opponent_effect_elements）で決める
            if "stadium_card" in e:
                # v0.57: セキチクシティジム（場のスタジアムの効果。番のプレイヤーの「キョウのポケモン」）
                card = e["stadium_card"]
                stadium_entry = state.effects.trainer_entry(state.cards[card].card_id) if card in state.cards else None
                both = False
                invalid = stadium_entry is None or not isinstance(stadium_entry.effect, CoinReturnOwnerPokemonStadium) or e["player"] != turn_player
            elif "trainer_card" in e:
                # v0.52: フジろうじん（使っている最中のトレーナー。使ったプレイヤーの控えポケモン）
                card = e["trainer_card"]
                trainer_entry = state.effects.trainer_entry(state.cards[card].card_id) if card in state.cards else None
                both = False
                invalid = using_trainer.get(e["player"]) != card or trainer_entry is None or not isinstance(trainer_entry.effect, ReturnBenchedPokemonToDeck) \
                    or active_of.get(e["player"]) == pid
            elif "power" in e:
                # v0.60: カスミのギャラドスの［はんこう］（p.309 の手順 4。ワザを使おうとした自分のポケモン）
                card_id, _, index = e["power"].partition("@power")
                power_entry = state.effects.power_entry(card_id, int(index)) if index.isdigit() else None
                both = False
                if power_entry is not None and isinstance(power_entry.effect, ReturnToDeckOnHeadsAfterDamage):
                    # v0.86: ［はしりさる］（すぐ前のログ bolt_check の、「おもて」でもどるポケモン）
                    invalid = prior is None or prior["kind"] != "bolt_check" or prior["pokemon_id"] != pid or prior["power"] != e["power"] or not prior["returned"]
                elif power_entry is not None and isinstance(power_entry.effect, ReturnToDeckAtRemainingHp):
                    # v0.61: ［ずらかる］（すぐ前のログ scram の、残りHPがちょうど「10」のポケモン）
                    invalid = prior is None or prior["kind"] != "scram" or prior["pokemon_id"] != pid or prior["power"] != e["power"]
                else:
                    invalid = power_entry is None or not isinstance(power_entry.effect, FailAndReturnOnAttack) or attack_window is None \
                        or pid != attack_window["pokemon_id"] or e["player"] != attack_window["player"]
            else:
                entry = state.effects.attack_entry(*_attack_key(e["effect"]))
                opponent_return = entry is not None and RETURN_IN_PLAY_TO_DECK_ELEMENT in getattr(entry.effect, "opponent_effect_elements", ())
                # v0.52: つれさる（ReturnBothActivesToDeck）は、ワザを使ったポケモンと相手の対戦ポケモンの両方をもどす
                both = entry is not None and getattr(entry.effect, "returns_both_actives", False)
                attacker_side = attack_window is not None and pid == attack_window["pokemon_id"] and e["player"] == attack_window["player"]
                opponent_side = attack_window is not None and e["player"] != attack_window["player"]
                invalid = attack_window is None or (both and not (attacker_side or opponent_side)) \
                    or (not both and not opponent_return and not attacker_side) or (not both and opponent_return and not opponent_side)
                if entry is not None and isinstance(entry.effect, ReturnOwnBenchToDeckAttack):
                    # v0.84: やまにかえす（ワザを使ったプレイヤーの控えポケモン）
                    invalid = attack_window is None or e["player"] != attack_window["player"] or active_of.get(e["player"]) == pid
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or ids.get(e["pokemon"]) != pid or invalid:
                problems.append(f"{e['turn']} 番に山札にもどしたポケモン {pid} が、そのワザを使ったポケモン（つまみだすなら相手のポケモン）・フジろうじんで選んだ控えポケモンではない")
            if sorted(e["energy"]) != sorted(energy.get(pid, [])) or e["damage"] != damage[pid]:
                problems.append(f"{e['turn']} 番に山札にもどしたポケモン {pid} のエネルギー {e['energy']}・ダメージ {e['damage']} がログの組み立てと違う")
            if sorted(e["cards"]) != sorted([*e["evolution_stack"], e["pokemon"], *(() if "disguise" not in e else (e["disguise"],)), *e["energy"], *e["trainers"]]) \
                    or any(owner.get(uid) != e["player"] for uid in e["cards"]) or e.get("disguise") != disguised.get(pid):
                problems.append(f"{e['turn']} 番に山札にもどしたカード {e['cards']} が、そのポケモンのカード・ついているカードと合わない")
            disguised.pop(pid, None)  # v0.49
            in_play.discard(pid)
            exclusive.pop(pid, None)
            poisoned.pop(pid, None)
            energy[pid] = []
            damage[pid] = 0
            if "effect" in e and _returns_without_shuffle(state, e["effect"]):
                search_due = e  # v0.38: でんれい（山札をさがしたあとに切る）
            elif both:
                both_due = [*(both_due or []), e]  # v0.52: つれさる（もどした側の山札を、もどした順に切る）
            else:
                shuffle_due = e
        elif kind == "return_basic_to_hand":
            # v0.52: ポケモン回収（使っている最中のトレーナー）。使ったプレイヤーの場のポケモンの、重なりのいちばん下のカードを手札に、進化カード（「ばける」で
            # のせたカードを含む）・エネルギーカードをトラッシュに。ダメージカウンターはなくなる。トレーナーがついていたら SU1 で止まるので、ついていない
            pid = e["pokemon_id"]
            card = e["trainer_card"]
            trainer_entry = state.effects.trainer_entry(state.cards[card].card_id) if card in state.cards else None
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or ids.get(e["pokemon"]) != pid or using_trainer.get(e["player"]) != card \
                    or trainer_entry is None or not isinstance(trainer_entry.effect, ReturnOwnPokemonBasicToHand) \
                    or e["zone"] != ("active" if active_of.get(e["player"]) == pid else "bench"):
                problems.append(f"{e['turn']} 番に手札にもどしたポケモン {pid} が、ポケモン回収で選んだ自分の場のポケモンではない")
            if sorted(e["energy"]) != sorted(energy.get(pid, [])) or e["damage"] != damage[pid] or e.get("disguise") != disguised.get(pid):
                problems.append(f"{e['turn']} 番に手札にもどしたポケモン {pid} のエネルギー {e['energy']}・ダメージ {e['damage']} がログの組み立てと違う")
            stack = (e["card"], *e["evolution_cards"])
            if e["pokemon"] not in stack or (e.get("disguise") is not None and stack[-1] != e["disguise"]) \
                    or tuple(e["discarded"]) != (*e["evolution_cards"], *e["energy"]) or any(owner.get(uid) != e["player"] for uid in (*stack, *e["energy"])):
                problems.append(f"{e['turn']} 番に手札にもどしたカード {e['card']}・トラッシュしたカード {e['discarded']} が、そのポケモンのカードと合わない")
            disguised.pop(pid, None)
            in_play.discard(pid)
            exclusive.pop(pid, None)
            poisoned.pop(pid, None)
            energy[pid] = []
            damage[pid] = 0
            hand[e["player"]].append(e["card"])
            discard[e["player"]].extend(e["discarded"])
            if active_of.get(e["player"]) == pid:
                active_of[e["player"]] = None
        elif kind == "discard_attached_cards":
            # v0.38: ワザ（ケーシィの「いなくなる」）で、ワザを使ったポケモンについているエネルギー・トレーナーを持ち主のトラッシュへ（ダメージカウンターを
            # とりのぞいたあと・山札にもどす前）
            pid = e["pokemon_id"]
            # v0.42: 特殊能力（おくびょう）は、ダメージカウンターをすべてとりのぞいたすぐあとに、使ったポケモンについているカードをトラッシュする
            by_power = "power" in e and prior is not None and prior["kind"] == "remove_all_damage_counters" and prior.get("power") == e["power"] \
                and prior["pokemon_id"] == pid
            if pid not in in_play or pokemon_owner.get(pid) != e["player"] or (not by_power and (attack_window is None or pid != attack_window["pokemon_id"])) \
                    or sorted(e["energy"]) != sorted(energy.get(pid, [])) or damage[pid] != 0 \
                    or any(owner.get(uid) != e["player"] for uid in (*e["energy"], *e["trainers"])):
                problems.append(f"{e['turn']} 番のついているカードのトラッシュ（ポケモン {pid}）が、ログから組み立てたワザを使ったポケモンのカードと合わない")
            else:
                energy[pid] = []
                discard[e["player"]].extend((*e["energy"], *e["trainers"]))
        elif kind == "knock_out":
            pid = ids[e["pokemon"]]
            tools_on.pop(pid, None)  # v0.81: ついていたどうぐもトラッシュした
            if pid not in in_play:
                problems.append(f"場にいないポケモン {pid} がきぜつした")
            if (e.get("timing") == "power") != (power_knock_out or "to_energy" in e):  # v0.59: ［エネエネ］のきぜつは HP によらない
                problems.append(f"{e['turn']} 番のきぜつ（ポケモン {pid}・timing {e.get('timing')}）が、特殊能力の処理のすぐあとのきぜつと合わない")
            # v0.61: バトル場は穴だらけ!（使い終えたあと）でダメージを受けたポケモン（どちらのプレイヤーのポケモンでもよい）のきぜつも
            devolved_ko = (pid, e["turn"]) in trainer_devolved and e["player"] == turn_player
            if e.get("timing") == "trainer" and (not (devolved_ko or (pid, e["turn"]) in trainer_damaged) or using_trainer.get(turn_player) is not None):
                # v0.50: トレーナー（退化スプレー）を使い終えたあと（トラッシュしたあと）の、その番に退化した自分のポケモンのきぜつ
                problems.append(f"{e['turn']} 番のきぜつ（ポケモン {pid}・timing trainer）が、使い終えたトレーナーで退化した自分のポケモンのきぜつではない")
            if attack_window is not None and pid in in_play:
                # v0.11: 「こんじょう」の「おもて」のポケモンはきぜつしない。使えたのに決定がないまま、きぜつしない（使うかは持ち主が決める）
                attack_window["knocked"].add(pid)
                if attack_window["ko_offer"] == pid and attack_window["ko_result"] == "heads":
                    problems.append(f"{e['turn']} 番に「こんじょう」が「おもて」のポケモン {pid} がきぜつした（G18・G33）")
                if attack_window["ko_offer"] != pid and attack_window["ko_able"].get(pid, "なし") is None:
                    gkey, _, gpower = guts_power(pid)
                    if gkey is not None and not [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(gpower)]:
                        problems.append(
                            f"{e['turn']} 番に「こんじょう」を使えるポケモン {pid} が、使うかの決定（ko_prevention_declined・ko_prevention_declared）"
                            "がないまま、きぜつした（G10・A4）"
                        )
            # v0.48: 「きょだいか」の効果があればその最大HP（きぜつのログは効果を消すログより前）。［ガスのからだ］の分は足さない（同じきぜつの判定で、それを消していた
            # かがくへんかガスの持ち主が先にきぜつのログに出ると、ログから組み立てた場ではガスがなくなる。エンジンはきぜつの判定の前の場で最大HPを求める）
            fixed_hp = lasting_value(pid, MaxHpSet.kind, "amount") if pid in top else None
            # v0.49: 今の姿（「ばける」・［へんしん］）の HP。きぜつのログの順番で［へんしん］の相手が先に場をはなれることがあるので、いちばん上のカードの HP との小さいほう
            hp_floor = fixed_hp if fixed_hp is not None else min(state.in_play_def(e["pokemon"]).hp, form_def(pid).hp if pid in top else 10 ** 6)
            if damage[pid] < hp_floor and pid not in destiny_knocked and "to_energy" not in e:
                problems.append(f"場のポケモン {pid} が、ログから組み立てたダメージ {damage[pid]}（HP 未満）できぜつした")
            destiny_knocked.discard(pid)
            rkey, rpower = rebirth_power(e["pokemon"])
            if rkey is not None and pid in in_play:
                # v0.12: 「ふしちょう」を使えるか（きぜつするときのねむり・マヒ・こんらん（P13〜P17）・はたらいているかがくへんかガス（P18））
                gases = [gas_pid for gas_pid, gas in working_gases() if gas.suppresses(rpower) and gas_pid != pid]
                blocked = f"{exclusive[pid]} 状態" if pid in exclusive else f"かがくへんかガス（ポケモン {gases}）" if gases else None
                if blocked is None and tower_in_play():
                    blocked = "ポケモンタワー"  # v0.74: 効果が消えるので、使う機会を出さない（答えがないのが正しい）
                rebirth_pending.append({"card": e["pokemon"], "player": e["player"], "power": rkey, "turn": e["turn"], "blocked": blocked})
            in_play.discard(pid)
            exclusive.pop(pid, None)
            # v0.47: いちばん上がなにかの化石・ピッピ人形（場での役割のあるカード。進化カードがのっていない）の「きぜつ」はカウントされない（counted False。相手は
            # サイドを取らない）。ほかのきぜつは今までどおり（counted を書かない）
            counted = state.in_play_def(e["pokemon"]).play_role is None
            if e.get("counted", True) != counted or ("counted" in e and counted):
                problems.append(f"{e['turn']} 番のきぜつ（ポケモン {pid}）の counted {e.get('counted')!r} が、いちばん上のカードの場での役割と合わない")
            if counted:
                knocked[e["player"]] += 1
            if e.get("disguise") != disguised.get(pid):
                problems.append(f"{e['turn']} 番のきぜつ（ポケモン {pid}）の「ばける」でのせたカード {e.get('disguise')} が、ログから組み立てた {disguised.get(pid)} と違う")
            disguised.pop(pid, None)
            # v0.59: ［エネエネ］のきぜつ（``to_energy``）は、いちばん上のカードをトラッシュせず、すぐあとの energy_conversion でエネルギーとしてつける
            if "to_energy" in e and e["to_energy"] != e["pokemon"]:
                problems.append(f"{e['turn']} 番のきぜつ（ポケモン {pid}）の to_energy {e['to_energy']} が、いちばん上のカードではない")
            kept = e.get("to_energy")
            if kept is not None:
                pending_conversion[kept] = (e["player"], pid)
            discard[e["player"]].extend([*e.get("evolution_stack", ()), *(() if kept is not None else (e["pokemon"],)),
                                         *(() if "disguise" not in e else (e["disguise"],)), *e["discarded_energy"]])
            if sorted(e["discarded_energy"]) != sorted(energy.get(pid, [])):
                problems.append(f"きぜつしたポケモン {pid} のトラッシュしたエネルギー {e['discarded_energy']} がログの組み立てと違う")
            for uid in e.get("discarded_trainers", ()):
                discard[owner[uid]].append(uid)
        elif kind == "take_prize":
            if ("card" in e.get("face_up", ())) != (e["card"] in face_up_log):
                problems.append(f"{e['turn']} 番に取ったサイド {e['card']} のおもての印が、ログから組み立てたおもてのサイドと合わない")  # v0.63
            face_up_log.discard(e["card"])
            prizes_taken[e["player"]] += 1
            taken_cards.append(e["card"])
            hand[e["player"]].append(e["card"])
        elif kind == "trainer_take_prize":
            # v0.56: マチスの交渉。きぜつではなく、使っている最中のそのトレーナーの効果で、お互いに自分のサイドを 1 枚ずつ取る（使ったプレイヤーから）
            user = trainer_user(e["trainer_card"])
            if using_trainer.get(user) != e["trainer_card"] or not isinstance(_trainer_effect_of(state, e["trainer_card"]), AskOpponentEachTakePrizeElseDraw) \
                    or owner.get(e["card"]) != e["player"] or e["card"] in hand[e["player"]] or e["card"] in discard[e["player"]]:
                problems.append(f"{e['turn']} 番にトレーナーで取ったサイド {e['card']} が、使っている最中のマチスの交渉で取った自分のサイドではない")
            if ("card" in e.get("face_up", ())) != (e["card"] in face_up_log):
                problems.append(f"{e['turn']} 番にトレーナーで取ったサイド {e['card']} のおもての印が、ログから組み立てたおもてのサイドと合わない")  # v0.63
            face_up_log.discard(e["card"])
            trainer_prizes[e["player"]] += 1
            taken_cards.append(e["card"])
            hand[e["player"]].append(e["card"])
        elif kind == "persistent_effect_added":
            added[(e["pokemon_id"], e["turn"])] = added.get((e["pokemon_id"], e["turn"]), 0) + 1
            # v0.12: はたらく番は次の相手の番（与えた番 + 1）。その番の終わりまで残り、そのあとは残らない。v0.27 の「つるぎのまい」は
            # 次の自分の番（与えた番 + 2）
            alive[(e["pokemon_id"], e["turn"])] = {
                "kind": e["persistent_effect"], "active_turn": e["active_turn"], "effect": e["effect"], "source_card": e["source_card"],
                "target_attack_index": e.get("target_attack_index"),  # v0.35: 「あわあわ」・「ドわすれ」の使えなくなるワザの位置
                # v0.49: 使えなくなるワザを印刷したカードの id（「あわあわ」は効果を与えたワザのカード、「ドわすれ」はログの target_attack_card か受けたポケモンのカード）
                "target_attack_card": (_attack_key(e["effect"])[0] if e["persistent_effect"] == CannotUseOwnAttack.kind
                                       else e.get("target_attack_card") or state.in_play_def(e["pokemon"]).id),
                "single_use": e.get("single_use"),  # v0.36: 「すなかけ」（PMCG1-051）の「効果は1回できえる」
                "lasting": e.get("lasting", False),  # v0.45: 「スミをかける」の「それ以後」（期限で消えない。場をはなれる・進化で消える）
                "color": e.get("color"), "amount": e.get("amount"),  # v0.48: テクスチャー1・2 の色、きょだいかの最大HP
                # v0.34: 「次の自分の番の始めに消える」効果（なきつく）は、はたらく番の次の番の始めに消える（はたらく番の終わりではない）
                # v0.45: 期限のない効果は期限で消えない。v0.48: テクスチャー1・2・きょだいかも期限がない（ベンチにもどる・場をはなれる・進化で消える）
                "until": (float("inf") if e.get("lasting") or e["persistent_effect"] in LASTING_KINDS else
                          e["active_turn"] + 1 if e["persistent_effect"] == ReducedDamageToSource.kind else e["active_turn"]),
            }
            if e.get("lasting") and (e["persistent_effect"] != AttackCoinCheck.kind or e.get("single_use")):
                problems.append(f"{e['turn']} 番の期限のない持続する効果（ポケモン {e['pokemon_id']}）が、手順 4 のコインの「1回できえる」でない効果ではない")
            # v0.35: 「きあいだめ」（next_turn_attack_damage_multiplier）・「あわあわ」（cannot_use_own_attack）も次の自分の番
            # v0.78: 「メタルスラッシュ」（cannot_attack_next_own_turn）も次の自分の番
            # v0.86: 「スタンウェーブ」（powers_stopped。与えた番から、効果を与えたプレイヤーの次の番の終わりまで）も次の自分の番
            offset = (NextTurnAttackDamage.turns_until_active
                      if e["persistent_effect"] in (*NEXT_TURN_DAMAGE_KINDS.values(), CannotUseOwnAttack.kind, CannotAttackNextOwnTurn.kind, PowersStopped.kind)
                      else 0 if e["persistent_effect"] in LASTING_KINDS else 1)
            if e["active_turn"] != e["turn"] + offset:
                problems.append(
                    f"{e['turn']} 番の持続する効果（ポケモン {e['pokemon_id']}）のはたらく番 {e['active_turn']} が、"
                    f"{'次の相手の番' if offset == 1 else '与えた番' if offset == 0 else '次の自分の番'}ではない"
                )
            if e["persistent_effect"] in V048_LASTING_KINDS:
                # v0.48: テクスチャー1（相手の対戦ポケモン）・テクスチャー2・きょだいか（ワザを使ったポケモン）。色は無色以外、最大HPは登録の数。同じ種類の前の効果は
                # すぐ前に理由 replaced で消した（受けているポケモンに同じ種類の効果は 1 つ）
                entry = state.effects.attack_entry(*_attack_key(e["effect"]))
                effect = None if entry is None else entry.effect
                expected = getattr(effect, "color_terms", lambda: None)() or getattr(effect, "max_hp_terms", lambda: None)()
                value = e.get("color") if e["persistent_effect"] != MaxHpSet.kind else e.get("amount")
                if expected is None or expected[0].kind != e["persistent_effect"] or (e["persistent_effect"] == MaxHpSet.kind and value != expected[1]) \
                        or (e["persistent_effect"] != MaxHpSet.kind and (value is None or EnergyType(value) is EnergyType.COLORLESS)):
                    problems.append(f"{e['turn']} 番の期限のない効果 {e['persistent_effect']}（ポケモン {e['pokemon_id']}・{value}）が、登録のワザ {e['effect']} の効果と合わない")
                on_opponent = e["persistent_effect"] == WeaknessChange.kind
                if (pokemon_owner.get(e["pokemon_id"]) != e["source_player"]) != on_opponent or e["source_player"] != turn_player:
                    problems.append(f"{e['turn']} 番の期限のない効果 {e['persistent_effect']} を受けたポケモン {e['pokemon_id']} の持ち主が合わない")
                if len([1 for (pid, _), info in alive.items() if pid == e["pokemon_id"] and info["kind"] == e["persistent_effect"]]) > 1:
                    problems.append(f"{e['turn']} 番に、ポケモン {e['pokemon_id']} の同じ種類の期限のない効果 {e['persistent_effect']} を消さずに重ねた")
            if e["persistent_effect"] == TailsDamageGuard.kind:
                # v0.60: かげぶんしん。登録のワザの効果・ワザを使ったポケモン自身・同じ種類は 1 つ（前の効果はすぐ前に理由 replaced で消した）
                entry = state.effects.attack_entry(*_attack_key(e["effect"]))
                if entry is None or getattr(entry.effect, "guard_terms", lambda: None)() is not TailsDamageGuard \
                        or attack_window is None or e["pokemon_id"] != attack_window["pokemon_id"] or pokemon_owner.get(e["pokemon_id"]) != e["source_player"]:
                    problems.append(f"{e['turn']} 番のかげぶんしんの効果（ポケモン {e['pokemon_id']}）が、そのワザを使ったポケモン自身への登録の効果ではない")
                if len([1 for (pid, _), info in alive.items() if pid == e["pokemon_id"] and info["kind"] == TailsDamageGuard.kind]) > 1:
                    problems.append(f"{e['turn']} 番に、ポケモン {e['pokemon_id']} のかげぶんしんの効果を消さずに重ねた")
        elif kind == "damage_guard_check":
            # v0.60: かげぶんしんのコイン。受けるポケモンにはたらいている効果・相手のワザ・コインは相手プレイヤー（ワザを使ったプレイヤー）が直前に投げた
            guard = alive.get((e["pokemon_id"], e["created_turn"]))
            if guard is None or guard["kind"] != TailsDamageGuard.kind or e["flipped_by"] != 1 - e["player"] or pokemon_owner.get(e["pokemon_id"]) != e["player"] \
                    or attack_window is None or attack_window["player"] == e["player"] or e["amount"] <= 0:
                problems.append(f"{e['turn']} 番のかげぶんしんのコイン（ポケモン {e['pokemon_id']}）が、はたらいている効果・相手のワザのダメージのものではない")
            if prior is None or prior["kind"] != "coin_flip" or prior["player"] != e["flipped_by"] or prior["result"] != e["result"] \
                    or e["received"] != (e["result"] == "heads"):
                problems.append(f"{e['turn']} 番のかげぶんしんの判定（ポケモン {e['pokemon_id']}）の直前のコイン・結果が合わない")
        elif kind == "persistent_effect_removed":
            removed[(e["pokemon_id"], e["created_turn"])] += 1
            if e["reason"] == "damaged" and (e["persistent_effect"] != TailsDamageGuard.kind or prior is None
                                             or (prior["attacker_pokemon_id"] if prior["kind"] == "counterattack" else prior.get("pokemon_id", ids.get(prior.get("pokemon")))) != e["pokemon_id"]
                                             or not prior.get("amount", 0)):
                problems.append(f"{e['turn']} 番に、ダメージを受けて消えた持続する効果（ポケモン {e['pokemon_id']}）が、ダメージのすぐあとのかげぶんしんではない")
            info = alive.pop((e["pokemon_id"], e["created_turn"]), None)
            if info is not None and e["reason"] == "expired" and e["turn"] != info["until"]:
                problems.append(f"{e['turn']} 番に、はたらく番 {info['active_turn']} の持続する効果（ポケモン {e['pokemon_id']}）が期限で消えた（早すぎる・遅すぎる）")
            if info is not None and e["reason"] == "expired" and info["until"] != info["active_turn"] \
                    and (prior is None or prior["kind"] not in ("turn_start", "persistent_effect_removed")):
                problems.append(f"{e['turn']} 番に、番の始めに消える持続する効果（ポケモン {e['pokemon_id']}）が、番の始め（turn_start のすぐあと）以外で消えた")
        if arrange_due is not None and kind != "arrange_deck_top" and prior is arrange_due:
            problems.append(f"{arrange_due['turn']} 番のみらいよちで見たカードのすぐあとに、その並べかえ（arrange_deck_top）がない（{kind}）")
            arrange_due = None
        if kind == "turn_end":
            for (locked_player, expires, _origin), info in trainer_locks_log.items():
                if expires <= e["turn"]:
                    problems.append(f"{e['turn']} 番の終わり（turn_end）に、{expires} 番までのトレーナーの使用の禁止（プレイヤー {locked_player}）が残っている")
            for (pid, created), info in alive.items():
                if info["until"] <= e["turn"]:
                    problems.append(f"{e['turn']} 番の終わり（turn_end）に、はたらく番 {info['active_turn']} の持続する効果（ポケモン {pid}・{created} 番）が残っている")
        # v0.46: バトル場のポケモン（常にはたらく特殊能力の場所の条件）。にげるは retreat の処理で、場をはなれたら in_play からなくなる
        if kind == "promote_active":
            active_of[e["player"]] = ids.get(e["pokemon"])
        elif kind in ("switch", "forced_switch"):
            active_of[e["player"]] = e["new_active_pokemon_id"]
            if e.get("old_active_pokemon_id") in shifts:
                shifts[e["old_active_pokemon_id"]]["returned"] = True  # v0.48: ［へんしょく］を使ってからベンチにもどった
        elif kind == "shuffle" and exchange_due is not None and e["player"] == exchange_due[0]:
            # v0.46: サイコエクスチェンジ。手札を山札にもどして切ったすぐあとに、count 枚まで引く
            draw_due, exchange_due = (exchange_due[0], exchange_due[1], exchange_due[2], "サイコエクスチェンジの shuffle"), None

    if declared is not None and not (state.decision is not None and state.decision.resume == "power"
                                     and (state.decision.context_value("use") or (None, None))[1] == declared[2]):
        # v0.42: 宣言のあと、その特殊能力の決定（ぶっしつこうかんのトラッシュする手札）を待っているなら、処理はまだない
        problems.append(f"{declared[0]} 番の特殊能力の宣言（ポケモン {declared[2]}）のあとに、その処理がない（ログの最後）")
    if draw_due is not None:
        problems.append(f"{draw_due[2]} 番の {draw_due[3]} のあとに、引く処理がない（ログの最後）")
    if power_ko_due is not None:
        problems.append(f"特殊能力の処理で HP 以上になったポケモン {power_ko_due} が、きぜつしていない（ログの最後）")
    if entry_due and state.decision is None:
        # v0.86: 答えを待つ使う機会が残るのは、その機会か同じ時点のほかの反応の決定を待っているときだけ
        problems.append(f"場に出たときの特殊能力の使う機会 {sorted(entry_due)} の答えも、決定もない（ログの最後）")
    if condition_due is not None:
        problems.append(f"特殊能力のコインのあと、置きかえたポケモン {condition_due[1]} の特殊状態がない（ログの最後）")
    if confusion_due is not None:
        problems.append(f"「ぼうぎょかふん」の「おもて」のあとに、ポケモン {confusion_due[0]} のこんらんがない（ログの最後）")
    if expect is not None:
        problems.append(f"「とうめい」の判定（ポケモン {expect[0]}）のあとに、その要素の処理がない（ログの最後）")
    if attack_window is not None and attack_window["due"]:
        problems.append(f"はたらいた「はんげき」（ポケモン {[d[0] for d in attack_window['due']]}）がない（ログの最後。決定の前に与えるはず）")
    if attack_window is not None and attack_window["ret_due"]:
        problems.append(f"はたらいた「ほのおのかべ」・「こうらがえし」（ポケモン {[d[0] for d in attack_window['ret_due']]}）がない（ログの最後。決定の前に与えるはず）")
    if rebirth_answered is not None and rebirth_answered["kind"] == "post_knockout_power_declared":
        problems.append(f"「ふしちょう」の宣言（カード {rebirth_answered['card']}）のあとに、手札に加えた記録がない（ログの最後）")
    d = state.decision
    for r in rebirth_pending:
        waiting = d is not None and d.resume == "post_knockout" and d.options == (r["card"],)
        waiting_prize = d is not None and d.kind == "take_prize" and (r["player"], r["card"]) in [
            (c[0], c[1]) for c in d.context_value("post_knockout", ())
        ]
        if r["blocked"] is None and not (waiting or waiting_prize or state.phase in TERMINAL):
            problems.append(f"きぜつした「ふしちょう」を使えるカード {r['card']} の答えも、それを待つ決定もない（ログの最後）")
        if r["blocked"] is not None and (waiting or waiting_prize):
            problems.append(f"使えない「ふしちょう」（カード {r['card']}。{r['blocked']}）を使うかの決定を出している")
    for (pid, created), info in alive.items():
        if pid not in in_play:
            problems.append(f"場をはなれたポケモン {pid} の持続する効果（{created} 番）を消したログがない（p.322）")
    for p_index, p in enumerate(state.players):
        for pokemon in p.in_play():
            pid = pokemon.pokemon_id
            if pid not in in_play:
                problems.append(f"場のポケモン {pid} がログでは場にいない")
                continue
            if pokemon.damage != damage[pid]:
                problems.append(f"場のポケモン {pid} のダメージ {pokemon.damage} が、ログから組み立てた {damage[pid]} と違う")
            if sorted(pokemon.energy) != sorted(energy[pid]):
                problems.append(f"場のポケモン {pid} のエネルギー {pokemon.energy} が、ログから組み立てた {energy[pid]} と違う")
            if ids.get(pokemon.card) != pid:
                problems.append(f"場のポケモン {pid} のいちばん上のカード {pokemon.card} が、ログの進化と対応しない")
            if pid in discard_entered and pokemon.played_turn != discard_entered[pid]:
                problems.append(f"トラッシュから出した場のポケモン {pid} の場に出た番 {pokemon.played_turn} が、ログの {discard_entered[pid]} 番と違う")  # v0.51
            state_exclusive = pokemon.conditions.exclusive
            if (None if state_exclusive is None else state_exclusive.name) != exclusive.get(pid):
                problems.append(f"場のポケモン {pid} のねむり・マヒ・こんらん {state_exclusive!r} が、ログから組み立てた {exclusive.get(pid)!r} と違う")
            # v0.48: ［へんしょく］の記録と、今有効な最大HP・弱点・抵抗力・色の読み方が、ログから組み立てた値と同じ（エンジンの問い合わせ effects.max_hp など）
            shift, logged = pokemon.type_shift, shifts.get(pid)
            if (None if shift is None else (shift.color, shift.turn, shift.source_card, shift.returned_to_bench)) != (
                    None if logged is None else (logged["color"], logged["turn"], logged["source_card"], logged["returned"])):
                problems.append(f"場のポケモン {pid} の［へんしょく］の記録 {shift} が、ログから組み立てた {logged} と違う")
            if state.is_face_down(pokemon) != (pid in face_down_pids):
                problems.append(f"場のポケモン {pid} がうらのカードか（{state.is_face_down(pokemon)}）が、ログから組み立てた値と違う")  # v0.67
            if state.is_face_down(pokemon):
                continue  # v0.67: うらのカードの最大HP・弱点・抵抗力・色は決まらない（FD1）
            from kyuura_engine.effects import max_hp, resistance_of, type_readings, weakness_of
            if (max_hp(state, pokemon), weakness_of(state, pokemon), resistance_of(state, pokemon)[0]) != (max_hp_now(pid), weakness_now(pid), resistance_now(pid)):
                problems.append(f"場のポケモン {pid} の今有効な最大HP・弱点・抵抗力 {(max_hp(state, pokemon), weakness_of(state, pokemon), resistance_of(state, pokemon)[0])} が、"
                                f"ログから組み立てた {(max_hp_now(pid), weakness_now(pid), resistance_now(pid))} と違う")
            if type_readings(state, pokemon) != type_readings_now(pid):
                problems.append(f"場のポケモン {pid} の色の読み方 {type_readings(state, pokemon)} が、ログから組み立てた {type_readings_now(pid)} と違う")
        if p_index == 0:
            # v0.63: おもてのサイド・一時的に置いておくカードが、ログから組み立てたものと同じ
            if face_up_log != set(state.face_up_prizes):
                problems.append(f"おもてのサイド {sorted(state.face_up_prizes)} が、ログから組み立てた {sorted(face_up_log)} と違う")
            logged = {key: value["cards"] for key, value in set_aside_log.items()}
            actual = {(g.kind, g.owner, g.trainer_card): g.cards for g in state.set_aside}
            if logged != actual:
                problems.append(f"置いておくカード {actual} が、ログから組み立てた {logged} と違う")
        if sorted(p.hand) != sorted(hand[p_index]):
            problems.append(f"プレイヤー {p_index} の手札 {sorted(p.hand)} が、ログから組み立てた {sorted(hand[p_index])} と違う")
        if sorted(p.discard) != sorted(discard[p_index]):
            problems.append(f"プレイヤー {p_index} のトラッシュ {sorted(p.discard)} が、ログから組み立てた {sorted(discard[p_index])} と違う")
        if starts and len(p.prizes) != state.rules.prize_count - prizes_taken[p_index] - trainer_prizes[p_index]:
            problems.append(f"プレイヤー {p_index} のサイド {len(p.prizes)} 枚が、取ったサイドの数 {prizes_taken[p_index]} + {trainer_prizes[p_index]} と合わない")
        if prizes_taken[p_index] > min(knocked[1 - p_index], state.rules.prize_count):
            problems.append(f"プレイヤー {p_index} が、相手のきぜつ {knocked[1 - p_index]} 回より多くサイドを取った")
        if state.phase in TERMINAL and state.phase is not Phase.HALTED \
                and prizes_taken[p_index] != min(knocked[1 - p_index], state.rules.prize_count - trainer_prizes[p_index]):
            problems.append(f"プレイヤー {p_index} の取ったサイド {prizes_taken[p_index]} 枚が、相手のきぜつ {knocked[1 - p_index]} 回と合わない")
    if {pokemon.pokemon_id for p in state.players for pokemon in p.in_play()} != in_play:
        problems.append("ログから組み立てた場のポケモンが状態と違う")
    if len(set(taken_cards)) != len(taken_cards):
        problems.append("同じサイドのカードを 2 回取った")
    # v0.47: 状態の期限のあるトレーナーの使用の禁止が、ログで与えてまだ消していない禁止と同じ
    if {(lock.player, lock.expires_turn, lock.origin) for lock in state.trainer_locks} != set(trainer_locks_log):
        problems.append(f"状態のトレーナーの使用の禁止 {state.trainer_locks} が、ログから組み立てた {sorted(trainer_locks_log)} と違う")
    # v0.56: 状態の期限のあるトレーナーの効果が、ログで与えてまだ消していない効果と同じ
    if {(e.player, e.source_card) for e in state.trainer_effects} != set(trainer_effects_log):
        problems.append(f"状態の期限のあるトレーナーの効果 {state.trainer_effects} が、ログから組み立てた {sorted(trainer_effects_log)} と違う")
    if arrange_due is not None and not (state.decision is not None and state.decision.kind == "arrange_deck_top"):
        problems.append(f"{arrange_due['turn']} 番のみらいよちで見たカードの並べかえも、その決定もない（ログの最後）")
    for p in state.players:
        for pokemon in p.in_play():
            # v0.44: 状態の 1 度だけ使えるワザの記録・サカキの許可が、ログの記録と同じ
            recorded = {(card, index) for pid, card, index in once_used if pid == pokemon.pokemon_id}
            if set(pokemon.attacks_used_once) != recorded:
                problems.append(f"場のポケモン {pokemon.pokemon_id} の 1 度だけ使えるワザの記録 {pokemon.attacks_used_once} が、ログの記録 {sorted(recorded)} と違う")
            if pokemon.evolution_permission_turn is not None and (pokemon.pokemon_id, pokemon.evolution_permission_turn) not in permitted:
                problems.append(f"場のポケモン {pokemon.pokemon_id} のサカキの許可（{pokemon.evolution_permission_turn} 番）が、ログにない")
    for pid, evolved in evolve_turns.items():
        # v0.44: サカキの許可のある番は、同じ番に 2 回進化できる（進化した時点で許可があったことは evolve の分岐が確かめる）
        if (len(evolved) > 2 and not devolve_turns.get(pid)) or evolved != sorted(evolved) or any(turn <= 2 for turn in evolved) \
                or any(a == b and (pid, a) not in permitted for a, b in zip(evolved, evolved[1:])):
            problems.append(f"場のポケモン {pid} の進化の番 {evolved} が正しくない")
    for key, count in removed.items():
        if count > added.get(key, 0):
            problems.append(f"持続する効果 {key} を、与えた回数より多く消した")
    # v0.13: 状態の効果の種類（「ほのおのかべ」の retaliation・「こうらがえし」の retaliation_received_damage など）が、ログで与えた効果の種類と同じ
    for p in state.players:
        for pokemon in p.in_play():
            for effect in pokemon.persistent_effects:
                info = alive.get((pokemon.pokemon_id, effect.created_turn))
                if info is not None and info["kind"] != effect.kind:
                    problems.append(f"持続する効果 {(pokemon.pokemon_id, effect.created_turn)} の種類 {effect.kind} が、ログで与えた {info['kind']} と違う")
    remaining = {(pokemon.pokemon_id, e.created_turn) for p in state.players for pokemon in p.in_play() for e in pokemon.persistent_effects}
    for key, count in added.items():
        if count != 1:
            problems.append(f"持続する効果 {key} を {count} 回与えた")
        alive = removed[key] == 0
        if alive and key[0] in in_play and key not in remaining:
            problems.append(f"持続する効果 {key} が、消したログがないのに状態にない")
        if not alive and key in remaining:
            problems.append(f"持続する効果 {key} が、消したあとも状態に残っている")
    problems.extend(coin_gated_effect_problems(state, log))  # v0.76
    return problems


def _card_values(node, found: set) -> set:
    """観測（辞書・並び）の中の、カードの項目（``"card"``）の値（カードの uid）をすべて集める（v0.47）。"""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "card" and isinstance(value, int):
                found.add(value)
            else:
                _card_values(value, found)
    elif isinstance(node, (list, tuple)):
        for value in node:
            _card_values(value, found)
    return found


def _face_up_from_log(state) -> set[int]:
    """v0.63: ログから組み立てた、いまおもてのサイドのカード（prizes_revealed で加え、サイドをはなれたログで除く）。"""
    face_up: set[int] = set()
    for e in state.log:
        kind = e["kind"]
        if kind == "prizes_revealed":
            face_up.update(e["cards"])
        elif kind == "prize_revealed":
            face_up.add(e["card"])  # v0.80: カードめくりゲーム
        elif kind == "prizes_to_deck":
            face_up.difference_update(e["cards"])  # v0.80: にせオーキドの発明（サイドをはなれた）
        elif kind in ("take_prize", "trainer_take_prize"):
            face_up.discard(e["card"])
        elif kind == "swap_prize_with_hand":
            face_up.discard(e["to_hand"])
        elif kind == "swap_prize_with_deck_top" and "face_up_card" in e:
            face_up.discard(e["face_up_card"])
    return face_up


def _sees_private(event: dict, viewer) -> bool:
    """v0.47: 見えない項目のあるログのイベントで、その項目が ``viewer`` に見えてよいか（observation.PRIVATE_FIELDS とは別に、イベントの意味から書き直した規則）。"""
    kind = event["kind"]
    if kind == "game_created":
        return False  # seed から山札の並び・コインがわかる
    if kind == "look_at_card":
        return viewer is not None and (viewer == event["player"] or (event["zone"] == "hand" and viewer == event["owner"]))
    if kind == "take_deck_top":
        return event.get("destination") == "discard" or (viewer is not None and viewer in (event.get("looker"), event.get("player")))
    if kind == "look_at_hand":
        return viewer is not None and viewer in (event["player"], event["owner"])  # v0.54: スパイ作戦（見たプレイヤーと、自分の手札を知っている持ち主）
    if kind == "opponent_hand_to_deck":
        return viewer is not None and viewer in (event["player"], event["looker"])  # v0.55: ロケット団のおねーさん（持ち主と、見て選んだプレイヤー）
    if kind == "set_aside_hand":
        return False  # v0.63: くすぐりマシーンで置いたカードは、だれも見られない（持ち主も）
    if kind == "prizes_to_deck":
        return viewer is not None and viewer == event["looker"]  # v0.80: にせオーキドの発明（サイドを見たプレイヤーだけ。サイドの持ち主は見ていない）
    return viewer is not None and viewer == event.get("player")


def _effective_from_state(state, pokemon) -> dict:
    """v0.48: 観測と照らす、場のポケモンの今有効な最大HP・色・弱点・抵抗力（エンジンの問い合わせ ``effects.max_hp`` などとは別に、状態の持続する効果・いちばん上の
    カードの特殊能力・特殊状態・かがくへんかガス・［へんしょく］の記録から求める。観測の形の値）。"""
    from kyuura_engine.continuous import power_suppressed

    definition = _form_from_state(state, pokemon)  # v0.49: 今の姿のカード
    effects = {type(effect): effect for effect in pokemon.persistent_effects}
    hp = definition.hp
    shift_works = False
    held = ([state.card_def(pokemon.disguise)] if pokemon.disguise is not None else []) + [state.card_def(pokemon.card)]
    for power, owner_def in ((power, d) for d in held for power in d.powers):
        effect = state.effects.power_effect(owner_def.id, power)
        if isinstance(effect, MaxHpPerAttachedEnergyCards) and not power_suppressed(state, power):
            hp += effect.per * len([uid for uid in pokemon.energy
                                    if state.card_def(uid).is_basic_energy and state.card_def(uid).provides is effect.energy_type])
        if isinstance(effect, ShiftColor):
            shift_works = pokemon.conditions.exclusive is None and not power_suppressed(state, power)
    if state.stadium is not None:
        hideout = _trainer_effect_of(state, state.stadium.card)
        if isinstance(hideout, NamedMaxHpStadium) and definition.name_ja.startswith(hideout.prefix):
            hp += hideout.amount  # v0.81a: ロケット団のアジト（今の姿の名前が「わるい」で始まるポケモン。v0.81 は ``max_hp_now`` だけに足していた）
    if MaxHpSet in effects:
        hp = effects[MaxHpSet].amount  # 大きくする効果と同時にはたらく状態（MH2）にはならない（ログの組み立て直しの ``max_hp_now`` が確かめる）
    shift = pokemon.type_shift
    if shift is None:
        readings = [definition.pokemon_type]
    elif (shift.turn == state.turn_number and not shift.returned_to_bench and shift.source_card == pokemon.card and shift_works) \
            or shift.color is definition.pokemon_type:
        readings = [shift.color]
    else:
        readings = [shift.color, definition.pokemon_type]
    weakness = effects[WeaknessChange].color if WeaknessChange in effects else definition.weakness
    resistance = effects[ResistanceChange].color if ResistanceChange in effects else definition.resistance

    def color(value):
        return None if value is None else value.value

    return {"hp": hp, "pokemon_type": color(readings[0]) if len(readings) == 1 else None, "pokemon_type_readings": [color(c) for c in readings],
            "weakness": color(weakness), "resistance": color(resistance), "resistance_value": _reduced_resistance_value(state, resistance, definition.resistance_value)}


def _reduced_resistance_value(state, resistance, value):
    """v0.57: 場の抵抗力低下ジム（登録の実装が ``ReduceResistanceStadium``）が、抵抗力のあるポケモンの数を ``amount`` へらす（0 で下限）。エンジンの ``resistance_of`` とは別に、
    場のスタジアムのカードと登録から求める。"""
    from kyuura_engine.effects import ReduceResistanceStadium

    stadium = state.stadium
    if stadium is None or resistance is None:
        return value
    effect = state.effects.trainer_effect(state.card_def(stadium.card))
    return max(0, value - effect.amount) if isinstance(effect, ReduceResistanceStadium) else value


def _form_from_state(state, pokemon):
    """v0.49: 観測と照らす、場のポケモンの今の姿のカードの定義（エンジンの ``effects.current_form`` とは別に、状態から求める）。「ばける」でのせたカードがあればそのカード、
    いちばん上のカードが［へんしん］を持ち、バトル場にいて、ねむり・マヒ・こんらんでなく、かがくへんかガスに消されていなければ相手の対戦ポケモンのいちばん上の
    カード、どちらでもなければいちばん上のカード。"""
    from kyuura_engine.continuous import power_suppressed

    if pokemon.disguise is not None:
        return state.card_def(pokemon.disguise)
    definition = state.card_def(pokemon.card)
    owner = next(o for o, p in enumerate(state.players) if any(q is pokemon for q in p.in_play()))
    for power in definition.powers:
        if isinstance(state.effects.power_effect(definition.id, power), TransformIntoDefender) and state.players[owner].active is pokemon \
                and pokemon.conditions.exclusive is None and not power_suppressed(state, power) and state.players[1 - owner].active is not None:
            return state.card_def(state.players[1 - owner].active.card)
    return definition


AUDIT_UID_FIELDS = frozenset({"pokemon", "card", "cards", "old_active", "new_active", "target", "active", "bench", "energy", "discarded", "discarded_energy"})


def _audit_masked(event, hidden):
    """v0.67: 監査の側で求めた、``hidden``（今うらのカードの uid）を除いたイベントの写し。カードの uid を書く項目（``pokemon``・``card``・``cards``・``…_card``・
    ``…_cards``）の値だけを None にする（ログの ``turn`` などの数は uid ではない）。"""
    if not hidden:
        return event
    masked = dict(event)
    for name, value in event.items():
        if not (name in AUDIT_UID_FIELDS or name.endswith(("_card", "_cards"))):
            continue
        if type(value) is int and value in hidden:
            masked[name] = None
        elif isinstance(value, (tuple, list)) and any(type(v) is int and v in hidden for v in value):
            masked[name] = type(value)(None if type(v) is int and v in hidden else v for v in value)
    return masked


def observation_problems(state) -> list[str]:
    """v0.47: プレイヤー（と観戦者）に渡す観測（``observation.observe``・``visible_log``。docs/fossil-hidden-info-v0.47.md 5 章）が、その人が見てよい情報だけを渡すか。

    - 手札: 持ち主か、相手の［おみとおし］がはたらいているとき（エンジンの ``hand_revealed_by`` とは別に、場のいちばん上のカード・ねむり・マヒ・こんらん・かがくへんかガス
      から求める）だけカードが見え、ほかは枚数だけ。山札・サイドは枚数だけ
    - 観測のどこにも、見えないカード（山札・サイド・見えない手札）の uid がない（uid の付け方からカードがわかる）。対戦準備のポケモンは表にするまで持ち主にだけ見える
    - 保留中の決定の選べるものは決めるプレイヤーだけに渡し、見えないカードの uid は、決めるプレイヤーが効果で見ている山札（``DECK_REVEALING_KINDS``）のときだけ
    - ログの写し: 見えない項目は、イベントの意味から決めた見てよい人（``_sees_private``）だけに残り、ほかには ``hidden`` に名前だけ。ほかのイベントは内部の記録と同じ
    """
    from kyuura_engine.continuous import power_suppressed
    from kyuura_engine.observation import DECK_REVEALING_KINDS, LOOKED_HAND_KINDS, OPTION_MEANINGS, PRIVATE_FIELDS, observe, visible_log

    problems: list[str] = []
    revealed = {0: False, 1: False}
    for owner, p in enumerate(state.players):
        for pokemon in p.in_play():
            held = ([state.card_def(pokemon.disguise)] if pokemon.disguise is not None else []) + [state.card_def(pokemon.card)]  # v0.49
            for definition in held:
                for power in definition.powers:
                    effect = state.effects.power_effect(definition.id, power)
                    if isinstance(effect, RevealOpponentHand) and pokemon.conditions.exclusive is None and not power_suppressed(state, power):
                        revealed[1 - owner] = True
    used = state.trainer_in_use
    public = {uid for p in state.players for uid in p.discard} | ({used.card} if used is not None else set()) | (
        {state.stadium.card} if state.stadium is not None else set()) | {
        uid for p in state.players for pokemon in p.in_play() for uid in (*pokemon.cards(), *pokemon.energy, *(t.card for t in pokemon.trainers))}
    face_up = _face_up_from_log(state)  # v0.63
    # v0.67: うらのカード（マチスの秘策）の本当のカードは持ち主だけに見える（場のカードでも公開ではない）
    face_down_owner = {pokemon.card: owner for owner, p in enumerate(state.players) for pokemon in p.in_play() if state.is_face_down(pokemon)}
    if set(face_down_owner) != set(state.face_down_cards):
        problems.append(f"うらのカードの一覧 {state.face_down_cards} が、場のうらのポケモン {sorted(face_down_owner)} と違う")
    public -= set(face_down_owner)
    for viewer in (0, 1, None):
        view = observe(state, viewer)
        visible = set(public) | {uid for uid, owner in face_down_owner.items() if owner == viewer}
        hidden_uids = {uid for uid, owner in face_down_owner.items() if owner != viewer}
        for owner, (p, pv) in enumerate(zip(state.players, view["players"])):
            shows = viewer == owner or revealed[owner]
            cards = pv["hand"]["cards"]
            if pv["hand"]["count"] != len(p.hand) or shows != (cards is not None):
                problems.append(f"観測（{viewer}）のプレイヤー {owner} の手札が、見えるか（{shows}）・枚数 {len(p.hand)} と合わない")
            if cards is not None and [c["card"] for c in cards] != list(p.hand):
                problems.append(f"観測（{viewer}）のプレイヤー {owner} の手札のカードが、状態の手札と違う")
            if shows:
                visible.update(p.hand)
            if set(pv["deck"]) != {"count"} or set(pv["prizes"]) != {"count", "face_up"} or pv["deck"]["count"] != len(p.deck) or pv["prizes"]["count"] != len(p.prizes):
                problems.append(f"観測（{viewer}）のプレイヤー {owner} の山札・サイドが、枚数（とおもてのサイド）だけではない")
            # v0.63: おもてのサイド（ロケット団参上!）は、ログから組み立てたおもてのカードだけを、位置とともに全員に見せる
            shown_face_up = [(f["position"], f["card"]) for f in pv["prizes"]["face_up"]]
            if shown_face_up != [(i, uid) for i, uid in enumerate(p.prizes) if uid in face_up]:
                problems.append(f"観測（{viewer}）のプレイヤー {owner} のおもてのサイド {shown_face_up} が、ログから組み立てたおもてのカードと違う")
            visible.update(uid for uid in p.prizes if uid in face_up)
            # v0.63: 一時的に置いておくカード。くすぐりマシーンはだれにも、挑戦状・クイズは持ち主にだけカードが見える（枚数は全員）
            groups = [g for g in state.set_aside if g.owner == owner]
            if [(g["kind"], g["count"]) for g in pv["set_aside"]] != [(g.kind, len(g.cards)) for g in groups]:
                problems.append(f"観測（{viewer}）のプレイヤー {owner} の置いておくカードの種類・枚数が、状態と違う")
            for g, gv in zip(groups, pv["set_aside"]):
                sees = viewer == owner and g.kind != "hand_set_aside"
                if (gv["cards"] is not None) != sees or (sees and [c["card"] for c in gv["cards"]] != list(g.cards)):
                    problems.append(f"観測（{viewer}）のプレイヤー {owner} の置いておくカード（{g.kind}）が、見えるか（{sees}）と合わない")
                if sees:
                    visible.update(g.cards)
            if state.turn_number == 0 and viewer != owner and p.active is not None and pv["active"] != {"face_down": True}:
                problems.append(f"観測（{viewer}）で、表にする前のプレイヤー {owner} の対戦準備のポケモンが見える")
            # v0.48: 見える場のポケモンの今有効な値（最大HP・色・弱点・抵抗力）が、状態から求めた値と同じ（観測とエンジンの処理が同じ値を使う）
            for pokemon, shown in zip(p.in_play(), [pv["active"], *pv["bench"]] if pv["active"] is not None else pv["bench"]):
                if state.turn_number == 0 and viewer != owner:
                    continue  # 対戦準備のポケモン（表にする前）は上で確かめた
                if bool(shown.get("face_down")) != state.is_face_down(pokemon):
                    problems.append(f"観測（{viewer}）の場のポケモン {pokemon.pokemon_id} のうらの印が、状態と違う")  # v0.67
                    continue
                if state.is_face_down(pokemon):
                    # v0.67: 本当のカードは持ち主だけ。HP・タイプ・ワザなどの決まらない値は書かない
                    real = shown.get("real")
                    if (real is not None) != (viewer == owner) or (real is not None and real.get("card") != pokemon.card):
                        problems.append(f"観測（{viewer}）のうらのカード {pokemon.pokemon_id} の本当のカードが、持ち主だけに見えるのではない")
                    if set(shown) - {"pokemon_id", "face_down", "damage", "energy", "trainers", "special_conditions", "persistent_effects", "real"}:
                        problems.append(f"観測（{viewer}）のうらのカード {pokemon.pokemon_id} に、うらのあいだは決まらない項目 {sorted(set(shown))} がある")
                    continue
                expected = _effective_from_state(state, pokemon)
                if {key: shown.get(key) for key in expected} != expected or shown.get("printed_hp") != state.card_def(pokemon.card).hp:
                    problems.append(f"観測（{viewer}）の場のポケモン {pokemon.pokemon_id} の今有効な値 {[shown.get(key) for key in expected]} が、"
                                    f"状態から求めた {list(expected.values())} と違う")
        board = {key: value for key, value in view.items() if key != "decision"}
        leaked = _card_values(board, set()) - visible
        if leaked:
            problems.append(f"観測（{viewer}）に、見えないカードの uid {sorted(leaked)} がある")
        d, dv = state.decision, view["decision"]
        if d is not None:
            # v0.63: 選ぶ数・選べるものの数も見せない決定。v0.73: 化石の発掘・マスターボール（選べるものの数が山札の中身を漏らす）
            # v0.75: search_deck・attach_from_deck（くらげのむれ・しおまねきの選べるものの数が山札の中身を漏らす）
            hidden_count = d.kind in ("challenge_bench", "quiz_card", "quiz_attack", "search_deck_or_discard", "take_looked_pokemon", "bench_from_deck",
                                      "search_deck", "attach_from_deck", "take_looked_trainer",  # v0.74: bench_from_deck。v0.80: ポケモンギア
                                      # v0.81: 手札（見た相手の手札）から種類でしぼったカードを選ぶ決定（docs/pokemon-tools-stadiums-v0.81.md 2 章）
                                      "return_to_deck", "select_evolution_card", "attach_from_hand", "hand_to_active", "discard_from_hand",
                                      "opponent_hand_to_deck", "opponent_hand_to_bench",
                                      "take_looked_cards")  # v0.83: 見た山札の上のカードから選ぶ決定（docs/shining-gentle-pokemon-v0.83.md 3.1）
            if viewer != d.player and ("options" in dv or (dv != {"kind": d.kind, "player": d.player} if hidden_count else dv.get("option_count") != len(d.options))):
                problems.append(f"観測（{viewer}）に、ほかのプレイヤー {d.player} の決定の選べるもの（の数）がある")
            if viewer == d.player and OPTION_MEANINGS[d.kind] == "card":
                for option in dv["options"]:
                    uid = option["value"]
                    # v0.55: 決めるプレイヤーが効果で見た相手の手札（LOOKED_HAND_KINDS）も、決めるプレイヤーには見えている
                    seen = d.kind in DECK_REVEALING_KINDS or (d.kind in LOOKED_HAND_KINDS and all(uid in state.players[1 - d.player].hand for uid in d.options))
                    if uid not in visible and not seen:
                        problems.append(f"観測（{viewer}）の決定 {d.kind} の選べるものに、見えないカード {uid} がある")
                    if ("card_id" in option) != (uid in visible or seen):
                        problems.append(f"観測（{viewer}）の決定 {d.kind} の選べるもの {uid} のカードの id の有無が、見えるかと合わない")
        for event, shown in zip(state.log, visible_log(state, viewer)):
            event = _audit_masked(event, hidden_uids)  # v0.67: 見る人の相手の今うらのカードの uid は、カードの uid を書く項目から除く
            if event["kind"] in PRIVATE_FIELDS:
                # v0.63: おもてだったカードの項目（face_up）は全員に見える
                fields = [name for name in PRIVATE_FIELDS[event["kind"]][0] if name in event and name not in event.get("face_up", ())]
                if _sees_private(event, viewer) or not fields:
                    if shown != dict(event):
                        problems.append(f"ログの写し（{viewer}）の {event['kind']} が、見てよい内部の記録と違う")
                elif any(name in shown for name in fields) or set(shown.get("hidden", {})) != set(fields):
                    problems.append(f"ログの写し（{viewer}）の {event['kind']}（{event['turn']} 番）に、見えない項目 {fields} がある・hidden がない")
            elif shown != dict(event):
                problems.append(f"ログの写し（{viewer}）の公開のイベント {event['kind']} が、内部の記録と違う")
    return problems

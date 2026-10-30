"""ワザを要素の並び（``AttackProgram``）として書き、仕組みが順番どおりに処理する（docs/event-model-v0.14.md 2 章・3 章）。

v0.13 のワザの実装（24 種類）は、それぞれの ``resolve`` の中で、ダメージ → ``finish_damage_elements`` → 効果、の順番と、
「とうめい」の評価（``attack_reaches``）・きぜつした対象の確認を手で書いていました（docs/event-architecture-audit-v0.14.md 4.2）。
ここでは、ワザを要素の並びにして、要素の分類（``Phase``）から仕組みが窓を開きます。

- ``Phase.DAMAGE``: ダメージの要素。要素の中のコイン（でんげきの「うら」なら自分にも、みだれづきの「おもて」の数）は、その要素に属する。
- ``Phase.EFFECT``: ダメージ以外の効果の要素。最初の効果の要素の前に、仕組みが「ダメージの要素のあと」の窓を開く（p.89）。要素の中の
  コイン（どくばりの「おもて」なら）は、その要素に属する。決定を出す要素も効果の要素。
- ``Phase.NEUTRAL``: ワザ全体のコイン（ねばりつく・いちかばちか。ダメージと効果の両方を決める）と、ワザの前の確認。ダメージの要素より前に
  だけ置く（送る効果が残っていれば不具合として止める）。
- ``Phase.CONTRACT``（v0.16b）: v0.13 の約束（``AttackEffect.resolve``・``resume``）で書いたワザの実装を 1 つの要素として処理するアダプタ
  （``contract.Contract``。docs/kernel-consolidation-v0.16b.md）。中でダメージと効果を混ぜるので、「ダメージの要素のあと」の窓は実装が
  ``finish_damage_elements`` で開き、最後に仕組みが開く（v0.13 の約束と同じ）。並びの中でこの要素だけを置く。

効果の中身（量の求め方・特殊状態の付け方・回復）はふつうの Python で書き、DSL にはしません。量の数値は v0.13 の実装の値を読みます。
対応表（``BUILDERS``）にないワザの実装は ``compile_attack`` では扱いません（``UnsupportedByKernel``。効果のないワザとして処理しない）。
v0.16b から、対応表にない実装をどう扱うか（v0.13 の約束のアダプタか、拒否か）は ``contract.program_for`` が決めます。
"""

from __future__ import annotations

import dataclasses
import itertools
import math
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

from .. import effects as E
from ..cards import EnergyType
from ..coins import CoinFlips, CoinSide, flip_coins, flip_until_tails
from ..conditions import CONFUSION, CURED, PARALYSIS, POISON, SLEEP, clear_special_conditions, confuse, cure_conditions, paralysis_problem, paralyze, poison, put_to_sleep, wake_up
from ..conditions import FORCED_SWITCH as FORCED_SWITCH_REASON
from ..damage import DAMAGE_STEP_CHOOSER, DamageOptionRequired, DamageOrderRequired, DamageReductionRequired, step_orders
from ..decisions import (
    ATTACH_FROM_DECK, ATTACH_FROM_DISCARD, ATTACH_FROM_HAND, ATTACH_TO_BENCH, BENCH_FROM_DECK, DAMAGE_STEP_ORDER, DISCARD_ENERGY, DISCARD_OPPONENT_ENERGY,
    DISCARD_TO_DECK_TOP, FORCED_SWITCH, HAND_TO_DECK, MOVE_OPPONENT_ENERGY, RECOVER_ENERGY, RECOVER_TRAINER, REMOVE_COUNTERS, RETURN_ENERGY, SEARCH_DECK, SELECT_ATTACK,
    SELECT_COLOR, SELECT_OPPONENT_ATTACK, SELECT_POKEMON, SELECT_SPECIAL_CONDITION, BENCH_FROM_DISCARD, EVOLUTION_HEAL,
)
from ..decisions import ARRANGE_DECK_TOP, SELECT_DECK_OWNER, SELECT_HAND_CARD, SELECT_LOOK_COUNT
from ..decisions import ENERGY_DRAIN_DISCARD
from ..decisions import MOVE_ENERGY, OPTIONAL_DRAIN
from ..decisions import OPTIONAL_DISCARD_ALL
from ..decisions import OPTIONAL_HEAL
from ..decisions import OPPONENT_HAND_TO_BENCH
from ..decisions import DISCARD_TO_DECK, RECOVER_POKEMON, SELECT_DRAW_COUNT, TAKE_LOOKED_CARDS
from ..decisions import DISCARD_STADIUM, EVOLUTION_SONG_POKEMON
from ..stadiums import bench_limit
from ..errors import SECRET_PLAN_HIDDEN_CODE, IllegalActionError, UnsupportedError
from ..evolution import DEVOLVE_TO_DECK, DEVOLVE_TO_DISCARD, DEVOLVE_TO_HAND, devolve, evolution_block, place_evolution_card
from ..persistent import (RETURN_IN_PLAY_TO_DECK, RETURN_IN_PLAY_TO_HAND, add_persistent_effect, leave_lock, max_hp_set, remove_on_entering_active,
                          remove_persistent_effects, remove_source_left_effects, replace_persistent_effect, require_can_leave)
from ..persistent import CURED as PERSISTENT_CURED
from ..state import (
    NEXT_TURN_MULTIPLY, NEXT_TURN_SET, RETALIATION_FIXED, RETALIATION_RECEIVED, AttackBarrier, AttackCoinCheck, CannotAttack, CannotAttackNextOwnTurn, CannotRetreatNextOwnTurn,
    CannotAttachEnergy, CannotAttackWhileSourceActive, CannotRetreat, CannotUseAttack, CannotUsePowers, CannotUseOwnAttack, DamageReduction, DestinyBond, DoubledDamage, HalvedDamage, NextTurnAttackDamage, PreventAttackDamage, PreventDamage,
    MaxHpSet, ReducedDamageToSource, ReducedDamageToSourceNextTurn, ReflectShield, ResistanceChange, Retaliation, TailsDamageGuard, TrainerTurnEffect, TrainerUseLock, WeaknessChange, ZeroDamageBelow, mark_returned_to_bench,
    OPPONENT_POWER_SUPPRESSION, StatusImmunityWhileActive, BenchAttackDamageGuard, ZeroDamageAtLeast, AttackEffectGuard, StatusImmunityNextTurn, PowersStopped, BenchProtection,
    ATTACK_FIELD_POWER_SUPPRESSION, ReceivedAttackDamageBonus, DealtAttackDamageReduction, TimedDamageGuard, KnockOutSurvival,
    EvolutionLock, StatusOnEnergyAttach, PursuitOnRetreat,
)
from ..state import ATTACK_POWER_SUPPRESSION, BENCH_ATTACK_DAMAGE_PREVENTION, COUNTER_BONE, COUNTER_FOOD, COUNTER_KINDS, MARKER_CHAR, MARKER_COLOR, MARKER_CURSE, MARKER_KINDS, MARKER_LIGHTNING_ROD, MARKER_STICKY, POWER_SUPPRESSION, Marker
from ..markers import CLEARED as MARKERS_CLEARED
from ..markers import REPLACED as MARKERS_REPLACED
from ..markers import USED as MARKERS_USED
from ..markers import add_marker, has_marker, marker_count, remove_markers, replace_marker
from ..decisions import SELECT_MARKER_COUNT
from ..decisions import OPPONENT_HAND_TO_DECK, SELECT_ATTACHED_SPECIAL_ENERGY, SELECT_ATTACHED_TRAINER
from ..decisions import ALLOCATE_DAMAGE
from ..decisions import HEAL_ALLOCATION, OPTIONAL_COIN
from ..history import note_processed
from ..zones import (
    attach_energy_from_hand, attach_from_deck, attach_from_discard, bench_from_deck, bench_from_discard, discard_attached_cards, discard_from_deck, draw_cards, promote_from_bench, put_discard_on_deck_top,
    return_discard_to_hand, return_hand_cards_to_deck, return_in_play_to_deck, return_in_play_to_hand, reveal_deck_to_hand, search_deck_to_hand, shuffle_deck,
    take_deck_top,
)
from ..zones import discard_stadium, look_at_card
from ..zones import hand_to_bench_by_effect
from ..zones import look_at_hand, opponent_hand_card_to_deck, return_attached_energy_to_deck, return_attached_trainer_to_deck
from ..zones import return_attached_cards_to_hand

from . import catalog as C
from . import codec
from .events import ElementStarted, FrameKind, Incoming, KnockedOutRecorded, Suspended, Window
from .kernel import IGNORE_HELD, IGNORE_RECEIVER_HELD, IGNORE_UNSTATED, BenchGuardRequest, EnergyDrainRequest, Resolution, SplitRequest, check_simultaneous, knocked_out, deal_damage, fire_pending, reaches, settle_scram, track_ko, type_question, weakness_resistance_matters
from .kernel import effect_ko_entries, knock_out_by_effect, note_source_form, restore_effect_ko
from ..decisions import BENCH_GUARD, DAMAGE_OPTION, DAMAGE_REDUCTION, ESP_REDO, KO_PREVENTION, NINJA_TRICK, REACTION_SWITCH
from ..decisions import MAGMA_POOL_ENERGY, REACTION_ORDER, SPLIT_FROM_DECK
from .. import movement as M
from .questions import QUESTIONS, OpenQuestion, pick, to_error

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ..cards import Attack
    from ..state import GameState, PendingDecision, PokemonInPlay

    from .events import FrameState


class UnsupportedByKernel(NotImplementedError):
    """プロトタイプの対応表にないワザの実装（黙って効果のないワザとして処理しない）。"""


class EspRedoOffer(Exception):
    """v0.66: ナツメのESPのやり直しの決定を出す（``AttackRun.flip`` が、ワザの説明文のコインを投げた直後・結果を使う前に投げる）。``run_elements`` が受け取って
    決定（``ESP_REDO``）を出し、答えのあとに同じ要素をもう一度処理する（``esp_preset``）。"""

    def __init__(self, count: int, by_heads: bool, flipper: int, flips, cards: tuple[int, ...], problem, chain: ContinueOnHeads | None = None,
                 until_tails: bool = False, players: tuple[int, ...] = ()):
        super().__init__(f"ナツメのESPのやり直し（{count} 枚）")
        self.count = count
        self.by_heads = by_heads
        self.flipper = flipper
        self.flips = flips
        self.cards = cards
        self.problem = problem
        # v0.115: 条件つきで続けて投げるコインのまとまり（``AttackRun.flip_chain``。びっくりサンダー）。やり直すなら、同じまとまりを最初から投げ直す（枚数は面で変わりうる）
        self.chain = chain
        # v0.118: 「うら」が出るまで投げるコインのまとまり（``AttackRun.flip_until_tails``。れんぞくいしなげ・まるもうけ）。やり直すなら、最初から「うら」が出るまで投げ直す
        self.until_tails = until_tails
        # v0.118: お互いのプレイヤーが 1 枚ずつ投げる 1 つのコイントス（``AttackRun.flip_each``。ふしぎなかおり）の、投げたプレイヤーの並び（相手のコインを含むので、やり直すは ES1）
        self.players = players


class Phase(str, Enum):
    DAMAGE = "damage"
    EFFECT = "effect"
    NEUTRAL = "neutral"
    CONTRACT = "contract"  # v0.16b: v0.13 の約束で書いた実装のアダプタ（contract.Contract）


OPP = E.OPPONENT_ACTIVE
SELF = E.SELF
HEADS = CoinSide.HEADS
TAILS = CoinSide.TAILS
# v0.115: ナツメのESPのやり直しの決定のあとに、条件つきで続けて投げるコインのまとまり（``AttackRun.flip_chain``）をもう一度処理するときの ``esp_preset`` の印（枚数のかわり）。
# やり直さなかった（決定の前の面の並びを使う）・やり直した（まとまりを最初から投げ直す）
ESP_CHAIN_KEPT = "chain_kept"
ESP_CHAIN_REDO = "chain_redo"
# v0.118（docs/unbounded-coins-heal-allocation-v0.118.md 2 章）: 同じく、「うら」が出るまで投げるコインのまとまり（``AttackRun.flip_until_tails``）をもう一度処理するときの印。
# 続きの情報の ``esp`` の 7 つめの値は ``ESP_UNTIL_TAILS``（v0.115 の ``("chain", 枚数)`` と同じ位置。v0.117 までの 6 つの値の形は変えない）
ESP_UNTIL_KEPT = "until_kept"
ESP_UNTIL_REDO = "until_redo"
ESP_UNTIL_TAILS = ("until", "tails")


def until_tails_complete(results) -> bool:
    """v0.118: ``results`` が、「うら」が出るまで投げ終えた面の並び（「おもて」が 0 枚以上続いたあとに「うら」1 枚）か。"""
    results = tuple(CoinSide(side) for side in results)
    return bool(results) and results[-1] is TAILS and all(side is HEADS for side in results[:-1])


@dataclass(frozen=True)
class ContinueOnHeads:
    """v0.115（docs/spread-damage-allocation-v0.115.md 5 章）: 条件つきで続けて投げるコインのまとまり。1 枚ずつ、最大 ``coins`` 枚まで、前の面が「おもて」の間だけ次の 1 枚を投げる
    （わるいライチュウの「びっくりサンダー」の「コインを投げて「おもて」なら、もう1枚コインを投げる」。「うら」が出たら、そのあとは投げない）。2 枚ならありうる面の並びは T・HT・HH の
    3 つで、投げる枚数は 1・2・2（いつも 2 枚投げて余った面を捨てる投げ方にしない）。"""

    coins: int = 2

    def __post_init__(self) -> None:
        if type(self.coins) is not int or self.coins < 2:
            raise ValueError(f"続けて投げるコインの最大の枚数は 2 以上（{self.coins!r}）")

    def next_count(self, results: tuple[CoinSide, ...]) -> int:
        """ここまでの面 ``results`` のあとに投げる枚数（0 ならまとまりは終わり）。"""
        if len(results) >= self.coins or (results and results[-1] is TAILS):
            return 0
        return 1

    def complete(self, results: tuple[CoinSide, ...]) -> bool:
        """``results`` が、このまとまりを最後まで投げた面の並びか（途中の並び・投げすぎた並びは偽）。"""
        return bool(results) and all(self.next_count(results[:i]) == 1 for i in range(len(results))) and self.next_count(results) == 0
APPLY_CONDITION = {POISON: poison, SLEEP: put_to_sleep, PARALYSIS: paralyze, CONFUSION: confuse}


class AttackRun:
    """ワザの要素を処理するときの、枠と状態への入口。

    v0.31:

    - ``declared``: 宣言したワザ（ログ ``attack`` のワザ・決定の続きの情報の ``use``）。ふだんは処理しているワザ（``key``）と同じ。相手のワザを
      自分のワザとして使う効果（ピクシーの「ゆびをふる」など。``CopyOpponentAttack``）では、``key`` が選んだ相手のワザになる（``redirect``）
    - ``failed``: ワザが失敗した（p.323「12 ワザの失敗」。ゴッドバードのコインの「うら」など）。残りの要素を処理しない
    - ``redirect``: 次の要素から処理する要素の並び（(ワザ, ワザのデータ, 要素の並び)。``run_elements`` が切りかえる）
    """

    def __init__(self, res: Resolution, fs: FrameState, program: tuple, attack: Attack, declared: E.AttackKey | None = None):
        self.res = res
        self.fs = fs
        self.program = program
        self.attack = attack
        self.suspended: PendingDecision | None = None
        self.carried: dict[str, Any] = {}  # 決定をまたいで要素が使う値（続きの情報の extra。再開では codec.decode から入れる）
        self.declared = fs.frame.attack_key if declared is None else declared
        self.failed = False
        self.redirect: tuple | None = None
        self.index = 0  # v0.65: 処理している要素の位置（``run_elements``。ダメージの要素の中の決定（［ベンチガード］）の続きの情報の "element"）
        # v0.66: ナツメのESPのやり直しの決定のあとに、もう一度処理する要素が使うコインの結果（(枚数, 採った結果)）。``flip`` が投げずに返す
        self.esp_preset: tuple[int, tuple] | None = None
        # v0.120（docs/fossil-basic-virtual-attacks-v0.120.md 2 章）: このワザで、ナツメのESPのやり直しを聞いた（説明文のコイントスを投げた）要素の並びのワザ（``key``）。v0.66〜v0.119 は
        # 真偽値（``esp_done``）で、どのワザの説明文のコインかを区別せず、決定をまたいで運ばなかった。続きの情報 ``esp_asked`` で運ぶ（``suspend``・``restore``）
        self.esp_asked: tuple[E.AttackKey, ...] = ()
        self.element_log = 0  # v0.66: 処理している要素を始めたときのログの長さ（もう一度処理する要素が、コインの前にログを残していないか）

    @property
    def state(self) -> GameState:
        return self.res.state

    @property
    def player(self) -> int:
        return self.fs.frame.player

    @property
    def key(self) -> E.AttackKey:
        return self.fs.frame.attack_key

    def attacker(self) -> PokemonInPlay:
        return self.state.find_pokemon(self.fs.frame.source_pid)[1]

    def incoming(self) -> Incoming:
        """v0.103: このワザの枠の発生元（``events.Incoming``。実際の使い手・ワザを使ったポケモン・ワザの分類・処理しているワザ）。無効にする効果の判定（``kernel.first_void``）に渡す。"""
        return Incoming.of(self.fs.frame)

    def opponent_active(self) -> PokemonInPlay:
        active = self.state.players[1 - self.player].active
        if active is None and self.res.secret_lost:
            from .kernel import lost_pokemon

            return lost_pokemon(self.res, 1 - self.player)  # v0.67: おもてにしてトラッシュしたバトル場のうらのカード（対象がいない。``knocked_out`` が真）
        return active

    def flip(self, count: int, *, by_heads: bool = False, player: int | None = None) -> CoinFlips:
        """コインを ``count`` 枚投げる。``by_heads``（v0.35）: 結果を「おもて」の数だけで使うコイン（先読みが「おもて」の数でまとめて試せる。
        ``coins.flip_coins``。実際の対戦の投げ方・乱数・ログは同じ）。並びの順番（1 枚目の面など）を使う要素は渡さない。

        ``player``（v0.40）: コインを投げるプレイヤー（既定はワザを使ったプレイヤー）。説明が「相手プレイヤーに…コインを投げさせ」と書くワザ（わるいスリーパーの
        「ベンチをあやつる」）は相手。乱数の使い方（1 枚 1 回 ``getrandbits(1)``）は同じで、ログ ``coin_flip`` の ``player`` だけが変わる（``card``・
        ``pokemon_id``・``effect`` はワザを使ったポケモンとワザ）。"""
        attacker = self.attacker()
        flipper = self.player if player is None else player
        if self.esp_preset is not None:
            # v0.66: ナツメのESPのやり直しの決定のあと、要素をもう一度処理している。決定の前に投げたコイン（やり直したなら、やり直したコイン）の結果を使う（投げ直さない）
            preset_count, results = self.esp_preset
            if preset_count != count or len(self.state.log) != self.element_log:
                raise RuntimeError("ナツメのESPのやり直しのあとの要素が、決定の前と違うコイン・ログの処理をした（エンジンの不具合）")
            self.esp_preset = None
            return CoinFlips(tuple(results))
        flips = flip_coins(self.state, flipper, count, source="attack", effect=str(self.key), card=attacker.card,
                           pokemon_id=attacker.pokemon_id, by_heads=by_heads)
        cards = E.esp_cards(self.state, attacker)
        if not cards or count == 0:
            return flips
        problem = self._esp_begin(attacker, cards, flipper)
        if self.res.dry_run:
            # 先読み: やり直さない・やり直す（止める選択は試さない）の両方を試す。やり直すなら、同じ枚数を投げ直す
            answers = [()] + ([] if problem is not None else [(1,)])
            if not self.res.oracle.choose(answers):
                return flips
            return self._esp_reflip(count, by_heads, flipper, cards, flips)
        raise EspRedoOffer(count, by_heads, flipper, flips, cards, problem)

    def flip_chain(self, chain: ContinueOnHeads, *, player: int | None = None) -> CoinFlips:
        """v0.115（docs/spread-damage-allocation-v0.115.md 5 章）: 条件つきで続けて投げるコインのまとまり ``chain``（前の面で次に投げる枚数が決まる）を投げ、面の並びを返す。1 枚ごとの
        ``coin_flip`` は、その時点で投げる 1 枚（``count`` は 1）。結果は「おもて」の数でまとめない（面の並びで処理が変わる）。

        ナツメのESPのやり直しは、まとまりを投げ終えたあとに 1 回だけ聞く（「ワザの説明文のコイントスをすべてやり直す」の「すべて」はこのまとまりの全部）。やり直すなら、同じまとまりを
        最初から投げ直す（最初の 1 枚だけを投げ直さない・最初の並びの長さにそろえない。面で枚数が変わりうる）。決定の前の面の並びは使わず、あとの要素には最後の並びだけを渡す。"""
        attacker = self.attacker()
        flipper = self.player if player is None else player
        if self.esp_preset is not None:
            preset, results = self.esp_preset
            if preset not in (ESP_CHAIN_KEPT, ESP_CHAIN_REDO) or len(self.state.log) != self.element_log or not chain.complete(tuple(results)):
                raise RuntimeError("ナツメのESPのやり直しのあとの要素が、決定の前と違うコイン・ログの処理をした（エンジンの不具合）")
            self.esp_preset = None
            if preset == ESP_CHAIN_KEPT:
                return CoinFlips(tuple(results))
            return self._esp_rechain(chain, flipper, E.esp_cards(self.state, attacker), CoinFlips(tuple(results)))
        flips = self._chain_flips(chain, flipper)
        cards = E.esp_cards(self.state, attacker)
        if not cards:
            return flips
        problem = self._esp_begin(attacker, cards, flipper)
        if self.res.dry_run:
            # 先読み: やり直さない・やり直す（止める選択は試さない）の両方を試す。やり直すなら、同じまとまりを最初から投げ直す
            answers = [()] + ([] if problem is not None else [(1,)])
            if not self.res.oracle.choose(answers):
                return flips
            return self._esp_rechain(chain, flipper, cards, flips)
        raise EspRedoOffer(len(flips.results), False, flipper, flips, cards, problem, chain=chain)

    def _chain_flips(self, chain: ContinueOnHeads, flipper: int) -> CoinFlips:
        attacker = self.attacker()
        results: tuple[CoinSide, ...] = ()
        while True:
            count = chain.next_count(results)
            if not count:
                return CoinFlips(results)
            results += flip_coins(self.state, flipper, count, source="attack", effect=str(self.key), card=attacker.card, pokemon_id=attacker.pokemon_id).results

    def _esp_rechain(self, chain: ContinueOnHeads, flipper: int, cards: tuple[int, ...], original) -> CoinFlips:
        """v0.115: ナツメのESPで、条件つきで続けて投げるコインのまとまりを最初から投げ直す（同じプレイヤー。最初の結果は使わない）。ログ ``esp_redo``（最初の並び・やり直した並び。
        枚数は違いうる）。"""
        attacker = self.attacker()
        redone = self._chain_flips(chain, flipper)
        self.state.add_event("esp_redo", player=self.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(self.key), cards=tuple(cards),
                             original=tuple(side.value for side in original.results), redone=tuple(side.value for side in redone.results))
        return redone

    def flip_until_tails(self, classes) -> CoinFlips:
        """v0.118（docs/unbounded-coins-heal-allocation-v0.118.md 2 章）: 「うら」が出るまでコインを投げ続け、面の並び（最後の 1 枚が「うら」）を返す（``coins.flip_until_tails``。
        ``classes`` は先読みの「おもて」の数の組を返す関数。実際の対戦の投げ方・乱数・ログは v0.64 と同じ）。

        ナツメのESPのやり直しは、「うら」が出るまでの一まとまりを投げ終えたあとに 1 回だけ聞く（「ワザの説明文に書かれているすべてのコイントス」はこのまとまりの全部。v0.115 の
        ``flip_chain`` と同じ形）。やり直すなら、最初から「うら」が出るまで投げ直す（最初の並びの長さにそろえない。枚数は最初と違いうる）。決定の前の並びは使わず、あとの処理には
        最後の並びだけを渡す。v0.117 までは、ESPのついたポケモンがこのコインを投げると内部エラーにしていた（「今の写しでは起こらない」という前提が誤りで、［サイコリンク］と超の色マーカーで
        届く。docs 2 章）。"""
        attacker = self.attacker()
        flipper = self.player
        if self.esp_preset is not None:
            preset, results = self.esp_preset
            if preset not in (ESP_UNTIL_KEPT, ESP_UNTIL_REDO) or len(self.state.log) != self.element_log or not until_tails_complete(results):
                raise RuntimeError("ナツメのESPのやり直しのあとの要素が、決定の前と違うコイン・ログの処理をした（エンジンの不具合）")
            self.esp_preset = None
            if preset == ESP_UNTIL_KEPT:
                return CoinFlips(tuple(CoinSide(side) for side in results))
            return self._esp_rerun(classes, flipper, E.esp_cards(self.state, attacker), CoinFlips(tuple(CoinSide(side) for side in results)))
        flips = self._until_flips(classes, flipper)
        cards = E.esp_cards(self.state, attacker)
        if not cards:
            return flips
        problem = self._esp_begin(attacker, cards, flipper)
        if self.res.dry_run:
            # 先読み: やり直さない・やり直す（止める選択は試さない）の両方を試す。やり直すなら、最初から「うら」が出るまで投げ直す（最初と最後の「おもて」の数は、どちらも組の代表で試す）
            answers = [()] + ([] if problem is not None else [(1,)])
            if not self.res.oracle.choose(answers):
                return flips
            return self._esp_rerun(classes, flipper, cards, flips)
        raise EspRedoOffer(len(flips.results), False, flipper, flips, cards, problem, until_tails=True)

    def flip_each(self, players: tuple[int, ...]) -> CoinFlips:
        """v0.118（docs/unbounded-coins-heal-allocation-v0.118.md 7 章）: プレイヤー ``players`` が順に 1 枚ずつ投げる、説明の 1 つのコイントス（ふしぎなかおりの「お互いのプレイヤーは、それぞれ
        コインを投げる」）。結果は投げた順の面の並び（1 人だけなら ``flip(1, player=...)`` と同じ）。

        ナツメのESPのやり直しは、まとまりを投げ終えたあとに 1 回だけ聞く。まとまりに相手プレイヤーのコインがあるので、やり直すは選べるが選ぶと止める（ES1。``esp_redo_problem``）。
        決定の続きの情報の ``esp`` の 7 つめは ``("players", 並び)``。決定のあとは最初の並びを使う。2 回に分けたコイントス（ES0）にはしない。"""
        if len(players) == 1:
            return self.flip(1, player=players[0])
        attacker = self.attacker()
        if self.esp_preset is not None:
            preset_count, results = self.esp_preset
            if preset_count != len(players) or len(self.state.log) != self.element_log:
                raise RuntimeError("ナツメのESPのやり直しのあとの要素が、決定の前と違うコイン・ログの処理をした（エンジンの不具合）")
            self.esp_preset = None
            return CoinFlips(tuple(CoinSide(side) for side in results))
        results: tuple[CoinSide, ...] = ()
        for player in players:
            results += flip_coins(self.state, player, 1, source="attack", effect=str(self.key), card=attacker.card, pokemon_id=attacker.pokemon_id).results
        flips = CoinFlips(results)
        cards = E.esp_cards(self.state, attacker)
        if not cards:
            return flips
        flipper = next(player for player in players if player != self.player)
        problem = self._esp_begin(attacker, cards, flipper)
        if problem is None:
            raise RuntimeError("相手プレイヤーのコインを含むコイントスのやり直しに、止める理由がない（エンジンの不具合）")
        if self.res.dry_run:
            self.res.oracle.choose([()])  # 先読み: やり直さない（やり直すは選ぶと止める選択なので試さない）
            return flips
        raise EspRedoOffer(len(players), False, flipper, flips, cards, problem, players=tuple(players))

    def _until_flips(self, classes, flipper: int) -> CoinFlips:
        attacker = self.attacker()
        return flip_until_tails(self.state, flipper, source="attack", effect=str(self.key), card=attacker.card, pokemon_id=attacker.pokemon_id, classes=classes)

    def _esp_rerun(self, classes, flipper: int, cards: tuple[int, ...], original) -> CoinFlips:
        """v0.118: ナツメのESPで、「うら」が出るまで投げるコインを最初から投げ直す（同じプレイヤー。最初の結果は使わない）。ログ ``esp_redo``（最初の並び・やり直した並び。枚数は違いうる）。"""
        attacker = self.attacker()
        redone = self._until_flips(classes, flipper)
        self.state.add_event("esp_redo", player=self.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(self.key), cards=tuple(cards),
                             original=tuple(side.value for side in original.results), redone=tuple(side.value for side in redone.results))
        return redone

    def _esp_carry_check(self) -> None:
        """v0.114: ナツメのESPのやり直しの決定のあとにもう一度処理する要素（とそのあと）が名前で読む前の要素の結果のうち、続きの情報で運ぶ種類（トラッシュ・ダメージ・入れ替えの結果。
        先に選んだ対象・色はどの決定でも運ぶ。``suspend``）でないものがあれば、黙って省かずに ``UNSUPPORTED_ESP_CONTINUATION``（エンジンの未対応。先読みが宣言の前に見つける）。
        今の写しの並びでは起こらない（docs/baby-rules-evolution-v0.114.md 3 章の探索）。"""
        later = _read_names(self.program[self.index:])
        missing = sorted(name for name, result in self.fs.results.items()
                         if name in later and not isinstance(result, (Discarded, E.DamageResult, ChosenTarget, ChosenColor, ChosenOption)) and type(result) is not int)
        if missing:
            raise UnsupportedError("UNSUPPORTED_ESP_CONTINUATION",
                                   f"ナツメのESPのやり直しのあとの要素が読む前の要素の結果 {missing} を、続きの情報で運べない（エンジンの未対応）")

    def _esp_begin(self, attacker: PokemonInPlay, cards: tuple[int, ...], flipper: int) -> tuple[str, str] | None:
        """v0.120（docs/fossil-basic-virtual-attacks-v0.120.md 2 章）: 説明文のコインを投げたあと、ナツメのESPのやり直しを聞く前の確かめ。聞いたことを記録し、やり直すを選ぶと止める
        理由 (コード, 理由の文) を返す（止めなければ None）。

        - 同じワザ（要素の並び）の説明文のコイントスで 2 回目に聞く: ES0（コードのない問い。今の写しのワザは、どれも説明文のコイントスを 1 回にまとめて投げる）
        - 宣言したワザの説明文のコインで聞いたあとに、そのワザが自分のワザとして使う別のワザ（ちょうのうりょくの「おもて」3 枚・ゆびをふるの「おもて」のあとに選んだワザ）の説明文の
          コインを投げた: そのコインが「そのワザの説明文に書かれているすべてのコイントス」に入るか（入るなら 2 回目のやり直しになるか）は決まらないので、やり直すは選ぶと止める
          （EC1。``E.ESP_COPIED_COINS_CODE``）。やり直さないは、どの読み方でも答えになる（「のぞむなら」）。v0.119 までは、ここを今の写しでは起こらない ES0 として内部エラーにしていた
        - それ以外は v0.66 の ES1〜ES3（``E.esp_redo_problem``）
        """
        if self.key in self.esp_asked:
            raise self.res.question("esp_separate_coin_tosses", f"ポケモン {attacker.pokemon_id}・ワザ {self.key}")
        earlier = self.esp_asked
        self._esp_carry_check()
        self.esp_mark()
        if earlier:
            return E.ESP_COPIED_COINS_CODE, f"{E.ESP_COPIED_COINS_REASON}（先に聞いたワザ {'・'.join(str(key) for key in earlier)}・このワザ {self.key}）"
        return E.esp_redo_problem(self.state, attacker, cards, flipper, self.player)

    def esp_mark(self) -> None:
        """v0.120: 処理している要素の並びのワザ（``key``）で、ナツメのESPのやり直しを聞いたことを記録する（``esp_asked``）。"""
        if self.key not in self.esp_asked:
            self.esp_asked += (self.key,)

    def _esp_reflip(self, count: int, by_heads: bool, flipper: int, cards: tuple[int, ...], original) -> CoinFlips:
        """v0.66: ナツメのESPで、説明文のコイントスをすべて投げ直す（同じ枚数・同じプレイヤー。最初の結果は使わない）。ログ ``esp_redo``（最初の結果・やり直した結果）。"""
        attacker = self.attacker()
        redone = flip_coins(self.state, flipper, count, source="attack", effect=str(self.key), card=attacker.card, pokemon_id=attacker.pokemon_id,
                            by_heads=by_heads)
        self.state.add_event("esp_redo", player=self.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(self.key), cards=tuple(cards),
                             original=tuple(side.value for side in original.results), redone=tuple(side.value for side in redone.results))
        return redone

    def coin_is(self, gate: tuple) -> bool:
        """ワザ全体のコインの面（(名前, CoinSide)）か、v0.31 の「おもて」の数（(名前, 数)）が合うか。"""
        name, side = gate
        if isinstance(side, CoinSide):
            results = self.fs.coins[name].results
            # v0.38: 投げなかったコイン（決める要素のどれにも処理の対象がない。``Coin``）の面は、どちらでもない（何も処理しない）
            return bool(results) and results[0] is side
        if isinstance(side, AtLeast):
            # v0.41: 「おもて」の数が ``side.count`` 以上（「1枚でも「おもて」なら」。投げなかったコインは 0 枚）
            return self.fs.coins[name].heads >= side.count
        if isinstance(side, Exactly):
            # v0.83: 「おもて」の数がちょうど ``side.count``（「フラッシュアイ」。投げなかったコインは 0 枚）
            return self.fs.coins[name].heads == side.count
        return self.fs.coins[name].heads == side

    def heads(self, name: str) -> int:
        """ワザ全体のコイン ``name`` の「おもて」の数（v0.31）。"""
        return self.fs.coins[name].heads

    def apply_redirect(self) -> None:
        """``redirect`` の要素の並びに切りかえる（v0.31。相手のワザを自分のワザとして使う）。枠のワザ（ログの ``effect``・ダメージを変える効果を
        探すワザ）は、選んだワザになる。宣言したワザ（``declared``）は変えない。"""
        if self.res.stadium_coin is not None:
            # v0.57: クチバシティジムのコインを投げた「マチスのポケモン」のワザで、相手のワザを自分のワザとして使うものは写しにない（マチスのポケモンにまねるワザはない）
            raise RuntimeError("クチバシティジムのコインを投げたワザで、相手のワザに切りかえた（今の写しでは起こらない。エンジンの不具合）")
        key, attack, program = self.redirect
        self.redirect = None
        note_processed(self.state, self.attacker(), key)  # v0.62: 使ったワザの記録（A）に処理したワザを書く
        self.program = program
        self.attack = attack
        self.fs.frame = dataclasses.replace(self.fs.frame, attack_key=key)

    def fail(self, reason: str) -> None:
        """ワザが失敗した（p.323「12 ワザの失敗」。ワザは使ったことになり、番は終わる）。残りの要素を処理しない（v0.31）。"""
        attacker = self.attacker()
        self.state.add_event("attack_failed", player=self.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(self.key),
                             reason=reason)
        self.failed = True

    def restore(self, carried: dict[str, Any]) -> None:
        """決定をまたいで運んだ値（``suspend`` の ``coins``・``frame``。v0.31）を、新しい枠にもどす。"""
        from ..coins import CoinFlips

        for name, sides in carried.get("coins", ()):
            self.fs.coins[name] = CoinFlips(tuple(CoinSide(side) for side in sides))
        for entry in carried.get("chosen_targets", ()):
            # v0.83: (名前, 番号)。v0.89: 持ち主も選んだ要素（``ChooseTarget``）は (名前, 番号, 持ち主)
            self.fs.results[entry[0]] = ChosenTarget(entry[1], entry[2] if len(entry) > 2 else None)
        for name, color in carried.get("chosen_colors", ()):
            self.fs.results[name] = ChosenColor(None if color is None else EnergyType(color))  # v0.88
        for name, chosen in carried.get("chosen_options", ()):
            self.fs.results[name] = ChosenOption(bool(chosen))  # v0.118
        group_power = carried.get("group_power")
        # v0.118。v0.122: 2 つ以上の力は ``group_powers``（宣言の順）。1 つなら v0.121 までと同じ ``group_power``
        self.res.group_powers = (tuple(tuple(entry) for entry in carried["group_powers"]) if "group_powers" in carried
                                 else (() if group_power is None else (tuple(group_power),)))
        for name, values in carried.get("damage_results", ()):
            self.fs.results[name] = E.DamageResult(*values)  # v0.87
        for name, cards, outcome in carried.get("discarded_results", ()):
            self.fs.results[name] = Discarded(tuple(cards), outcome)  # v0.113: ESPのやり直しのあとの要素が読むトラッシュの結果
        for name, pokemon_id in carried.get("switched_results", ()):
            self.fs.results[name] = int(pokemon_id)  # v0.114: ESPのやり直しのあとの要素が読む入れ替えの結果（入れ替えて出た控えポケモンの番号）
        self.esp_asked = tuple(E.AttackKey(*key) for key in carried.get("esp_asked", ()))  # v0.120
        frame = dict(carried.get("frame", ()))
        for pid, value in frame.get("reception", ()):
            self.fs.reception[pid] = bool(value)
        self.fs.fired = frame.get("fired", 0)
        pending = frame.get("pending", ())
        if pending:
            from .kernel import restore_deferred

            self.fs.pending.extend(restore_deferred(self.res, self.fs, pending))
        for pid, value in frame.get("guts", ()):
            self.res.ko_prevention_able.setdefault(pid, bool(value))
        for pid, player, source, attack in frame.get("ko_by", ()):
            self.res.ko_carried.setdefault(pid, (player, source, bool(attack)))  # v0.61
        # v0.65: ［にげこむ］のまだ聞いていない候補と、入れ替えたポケモン（もと → かわり）
        self.res.flee_offers = [tuple(entry) for entry in frame.get("flee", ())]
        self.res.fled = {orig: new for orig, new in frame.get("fled", ())}
        from ..state import PokemonInPlay

        # v0.67: おもてにしてトラッシュしたうらのカード（場をはなれたので、番号だけを持つ場のポケモンとして作り直す。対象がいないことを確かめるだけに使う）
        self.res.secret_lost = {pid: (owner, PokemonInPlay(card, pokemon_id=pid, played_turn=0), bool(was_active))
                                for pid, owner, card, was_active in frame.get("secret_lost", ())}
        for pid, player, source in frame.get("damage_ko", ()):
            self.res.damage_ko.setdefault(pid, (player, source))  # v0.81
        restore_effect_ko(self.res, frame.get("effect_ko", ()))  # v0.100: このワザの効果で「きぜつ」させたポケモン（決定のあとのきぜつの判定でも「きぜつ」する）
        # v0.46: ワザが使われた時の特殊状態（くつろぐかおり）。決定の前の宣言で写した値（書いていなければ空。決定をまたいでも今の特殊状態で決め直さない）
        self.res.attack_status = frozenset(carried.get("attack_status", ()))
        # v0.57: クチバシティジムのコインの結果（投げ直さない）
        coin = carried.get("stadium_coin")
        self.res.stadium_coin = None if coin is None else (coin[0], bool(coin[1]))
        self.res.attack_power = bool(carried.get("attack_power", 0))  # v0.88

    def knocked_out(self, pokemon: PokemonInPlay) -> bool:
        """v0.67: おもてにしてトラッシュしたうらのカード（``res.secret_lost``）は、処理の対象がいない（効果を与えない・効果を決めるコインを投げない。HP 以上になった
        対象と同じ扱い）。うらのカード（まだおもてにしていない）は、ダメージがのっていない（うらのあいだはダメージを受けない）ので HP 以上ではない（HP を読まない）。

        効果の対象が、このワザの処理の中で HP 以上になった（p.309「処理の対象がなくなってしまっている場合」。きぜつの処理はワザのあと）。
        v0.13 では、ワザの実装によって今のダメージで比べるものと、ダメージの要素の結果で見るものがあった（audit 4.3）。ここでは今のダメージで
        比べる（今の対応カードでは同じ答え）。"""
        if self.res.fled and (pokemon.pokemon_id in self.res.fled or pokemon.pokemon_id in self.res.fled.values()):
            # v0.65: ［にげこむ］で入れ替えたポケモンと、かわりに出たポケモンは、このワザの残りの「ダメージ以外の効果」の対象ではない（効果を移さない）。処理の対象がない
            # ときと同じく、その効果を決めるコインも投げない（p.309。HP 以上になった対象と同じ扱い）
            return True
        if pokemon.pokemon_id in self.res.secret_lost:
            return True
        if self.state.is_face_down(pokemon):
            return False
        knocked = E.knocked_by_hp(self.state, pokemon)  # v0.48: 今有効な最大HP
        if knocked:
            # v0.81（FB1）: きあいのハチマキのついたポケモンが、相手のワザのダメージで HP 以上になったあとに、同じワザの要素の対象になる（すぐあとにコインを投げる読み方では
            # 残りHP 10 で対象になりうる）
            from .kernel import focus_band_timing, knockout_survival_timing

            focus_band_timing(self.res, pokemon, f"HP 以上になったあとのワザ {self.key} の要素")
            # v0.110（KS1）: 残りHPがなくなっても「きぜつ」しない効果のポケモンが、HP 以上になったあとに同じワザの要素の対象になる（すぐあとに残りHP 10 にする読み方では対象になりうる）
            knockout_survival_timing(self.res, pokemon, f"HP 以上になったあとのワザ {self.key} の要素")
        return knocked

    def ko_prevention_conflict(self, target: PokemonInPlay, owner: int | None = None) -> None:
        """効果の対象がきぜつして効果を飛ばすとき、その対象がきぜつの判定で任意の効果（こんじょう）を使えるなら、効果を受けるかが原典で
        決まらない（相手の対戦ポケモンは G37）。v0.17b: 対象がワザを使ったポケモン自身（``owner`` が番のプレイヤー）なら、同じ形の問いで、
        今の対応カードでは起こらない（自分に効果を与えるワザを持つポケモンに、こんじょうはない。コードのない問い）。"""
        owner = 1 - self.player if owner is None else owner
        for instance in C.in_window(self.state, Window.KO_CHECK, owner, target, self.res.catalog):
            if instance.definition.timing is not C.Timing.OFFER or instance.definition.decision_kind != KO_PREVENTION:
                continue  # v0.61: ［ファイナルビーム］は「きぜつ」をまぬがれないので、効果を飛ばしてよい
            if self.res.ko_prevention_able.get(target.pokemon_id) and not C.offer_stopped(self.state, instance, target):
                if owner == self.player:
                    raise self.res.question("ko_prevention_self_effect", f"ポケモン {target.pokemon_id}")
                raise self.res.question("ko_prevention_attack_effect", f"ポケモン {target.pokemon_id}",
                                        E.ko_prevention_attack_effect_error(target.pokemon_id, opponent_effect_elements(self.program)))
            break

    def _ko_by(self) -> tuple:
        """v0.61: HP 以上になった場のポケモンのきぜつの原因 ((番号, 原因の枠のプレイヤー, ダメージを与えたポケモン, ワザの分類か), ...)。"""
        from .kernel import ko_cause

        found = []
        for pid in sorted(set(self.res.knocked_by) | set(self.res.ko_carried)):
            cause = ko_cause(self.res, pid)
            if cause is not None and self._knocked_pid(pid):
                found.append((pid, cause[0], cause[1], int(cause[2])))
        return tuple(found)

    def _knocked_pid(self, pid: int) -> bool:
        located = self.state.find_pokemon(pid)
        return located is not None and E.knocked_by_hp(self.state, located[1])

    def suspend(self, *, kind: str, player: int, options, extra: tuple = (), min_choices: int = 1, max_choices: int = 1,
                carry: bool = False) -> None:
        """決定を出して止まる。v0.31: 決定をまたいで要素が使う値を続きの情報に運ぶ: ワザ全体のコインの結果（``coins``。あるときだけ）・相手の
        ワザを自分のワザとして使っているときの選んだワザ（``copied``）・``carry`` なら枠の値（``frame``: 「とうめい」の結果（T4。1 つのワザで 1 匹
        1 回）・処理した送る効果の数（C34・C35）・こんじょうの写し）。v0.30 までの決定の形は変えない（どれも運ぶ値がない）。

        v0.34: ``carry`` なら、まだ処理していない送る効果（``fs.pending``）も運ぶ（``frame`` の ``pending``。ダメージの要素のあとに決定を出すダメージの
        要素（``ChosenBenchDamage``）。v0.33 の ``UNSUPPORTED_DECISION_AFTER_DAMAGE_TRIGGER`` を解消した）。``carry`` でない決定の前に送る効果が残って
        いれば、今までどおりエンジンの不具合。"""
        if self.fs.pending and not carry:
            raise RuntimeError("決定の前に送る効果が残っている（窓の位置の誤り。エンジンの不具合）")
        check_simultaneous(self.res)  # 決定をまたぐと、きぜつの原因の記録はなくなるので、ここで確かめる
        extra = tuple(extra)
        if self.key != self.declared:
            extra += (("copied", (self.key.card_id, self.key.attack_index)),)
        if self.fs.coins:
            extra += (("coins", tuple((name, tuple(side.value for side in flips.results)) for name, flips in self.fs.coins.items())),)
        if self.res.attack_status:
            # v0.46: ワザが使われた時（宣言）にねむり・マヒ・こんらんだった、その時点の特殊状態で決める常にはたらく特殊能力（くつろぐかおり）を持つポケモン
            # （``Resolution.attack_status``）。空なら書かない（v0.45 までの決定の形は変えない）
            extra += (("attack_status", tuple(sorted(self.res.attack_status))),)
        if self.res.stadium_coin is not None:
            # v0.57: クチバシティジムのコインの結果（(スタジアムカード, 「おもて」なら 1)）。投げていなければ書かない（v0.56 までの決定の形は変えない）
            extra += (("stadium_coin", (self.res.stadium_coin[0], int(self.res.stadium_coin[1]))),)
        if self.res.attack_power:
            extra += (("attack_power", 1),)  # v0.88: ワザといっしょに使った特殊能力（［すいりょくはつでん］）。使っていなければ書かない（v0.87 までの決定の形は変えない）
        # v0.61: HP 以上になったポケモンのきぜつの原因（［ファイナルビーム］の候補。``kernel.ko_cause``）。HP 以上のポケモンがなければ書かない
        ko_by = self._ko_by()
        # v0.65: ［にげこむ］のまだ聞いていない候補・入れ替えたポケモン。なければ書かない（v0.64 までの決定の形は変えない）
        flee = ((("flee", tuple(self.res.flee_offers)),) if self.res.flee_offers else ()) + (
            (("fled", tuple(sorted(self.res.fled.items()))),) if self.res.fled else ())
        if self.res.secret_lost:
            # v0.67: このワザでおもてにしてトラッシュしたうらのカード（(番号, 持ち主, カード, バトル場にいたか)）。なければ書かない（v0.66 までの決定の形は変えない）
            flee += (("secret_lost", tuple(sorted((pid, owner, pokemon.card, int(was_active))
                                                 for pid, (owner, pokemon, was_active) in self.res.secret_lost.items()))),)
        damage_ko = tuple(sorted((pid, player, source) for pid, (player, source) in self.res.damage_ko.items() if self._knocked_pid(pid)))
        if damage_ko:
            # v0.81: ワザの分類のダメージで HP 以上になったポケモン（きあいのハチマキ・学習装置）。なければ書かない（v0.80 までの決定の形は変えない）
            flee += (("damage_ko", damage_ko),)
        if self.res.effect_ko:
            # v0.100: このワザの効果で「きぜつ」させたポケモン（(番号, ワザを使ったプレイヤー, ワザを使ったポケモン)）。なければ書かない（v0.99 までの決定の形は変えない）
            flee += (("effect_ko", effect_ko_entries(self.res)),)
        chosen = tuple(sorted(((name, result.pokemon_id) if result.owner is None else (name, result.pokemon_id, result.owner))
                              for name, result in self.fs.results.items() if isinstance(result, ChosenTarget)))
        if chosen:
            # v0.83: 先に選んだ控えポケモン（「サンダースコール」。``ChooseOpponentBench``）。あとのダメージの要素が順番の決定などで止まっても、選び直さない。
            # v0.89: 選んだ個体の持ち主も運ぶ（``ChooseTarget``。v0.83 の要素は持ち主を書かない形のまま）
            extra += (("chosen_targets", chosen),)
        colors = tuple(sorted((name, None if result.color is None else result.color.value) for name, result in self.fs.results.items() if isinstance(result, ChosenColor)))
        if colors:
            # v0.88: 先に選んだ色（コアストリーム・レインボーウェーブ。``ChooseColor``）。あとのダメージの要素が順番の決定などで止まっても、選び直さない
            extra += (("chosen_colors", colors),)
        chosen_options = tuple(sorted((name, int(result.chosen)) for name, result in self.fs.results.items() if isinstance(result, ChosenOption)))
        if chosen_options:
            # v0.118: 「のぞむなら」の決定の答え（エアロウイングの投げる・投げない。``OptionalCoin``）。あとの決定（ナツメのESPのやり直しなど）をまたいでも選び直さない
            extra += (("chosen_options", chosen_options),)
        if len(self.res.group_powers) == 1:
            # v0.118: ワザといっしょに使った自分の場のポケモンの［XXXXX］（発生源・特殊能力・「おもて」の数）。使っていなければ書かない（v0.117 までの決定の形は変えない）
            extra += (("group_power", self.res.group_powers[0]),)
        elif self.res.group_powers:
            # v0.122: 2 つ以上の力（［ANGER］と［XXXXX］）は宣言の順の並び。1 つのときの形（``group_power``）は v0.121 までと同じ
            extra += (("group_powers", self.res.group_powers),)
        if self.esp_asked and kind != ESP_REDO:
            # v0.120（docs/fossil-basic-virtual-attacks-v0.120.md 2 章）: このワザでナツメのESPのやり直しを聞いた要素の並びのワザ。聞いていなければ書かない（v0.119 までの決定の形は
            # 変えない）。v0.119 までは運ばず、ちょうのうりょくのコインで聞いたあとのワザを選ぶ決定をまたぐと聞いたことを忘れ、先読み（ES0 の内部エラー）と実際の処理（もう一度の
            # やり直しを聞く）が食い違っていた。ESPのやり直しの決定は、答えのあとに処理している並びのワザを記録し直す（``apply_esp_redo``）ので書かない
            extra += (("esp_asked", tuple((key.card_id, key.attack_index) for key in self.esp_asked)),)
        boundary = dict(extra).get("boundary")
        if boundary is not None:
            # v0.87: 要素のあいだの決定（［ぶんれつ］・［だつりょくえき］など。``boundary`` は次に処理する要素の位置）のあとの要素が、前のダメージの要素の結果を
            # 名前で読む（「ダメージを与えた後、…」の ``after_damage`` など）なら、その結果を運ぶ。読まなければ書かない（v0.86 までの決定の形は変えない）
            used_later = {value for later in self.program[boundary:] for value in _result_names(later)}
            # v0.109: 受けるときのコインで防ぐ期限つきの効果で受けなかった結果だけ、その効果の種類（``DamageResult.guard``）を加える（ほかは v0.108 までと同じ形。``carried_values``）
            damage = tuple(sorted((name, result.carried_values()) for name, result in self.fs.results.items()
                                  if isinstance(result, E.DamageResult) and name in used_later))
            if damage:
                extra += (("damage_results", damage),)
        esp = dict(extra).get("esp")
        if esp is not None:
            # v0.113: ナツメのESPのやり直しのあとにもう一度処理する要素（とそのあと）が、前の要素の結果を名前で読むなら、その結果を運ぶ（読まなければ書かない。v0.112 までの決定の形は
            # 変えない）。トラッシュの結果（わるいバクフーンの「ファイヤーラッシュ」・マチスのエレブーの「ほうでん」の、トラッシュした枚数だけ投げるダメージの要素のコイン）は
            # ``discarded_results``（トラッシュしたカード・扱い）、ダメージの結果（キョウのドガースの「くもがくれガス」の「ダメージを与えた後」）は境目の決定と同じ ``damage_results``。
            # v0.112 までは運ばず、［サイコリンク］でこれらのワザを使ったナツメのフーディンのESPの答えで内部エラー（``KeyError``）になっていた。ほかの種類の結果（入れ替えた控えの番号など）は運ばない
            used_later = {value for later in self.program[esp[0]:] for value in _result_names(later)}
            discarded = tuple(sorted((name, tuple(result.cards), result.outcome) for name, result in self.fs.results.items()
                                     if isinstance(result, Discarded) and name in used_later))
            if discarded:
                extra += (("discarded_results", discarded),)
            damage = tuple(sorted((name, result.carried_values()) for name, result in self.fs.results.items()
                                  if isinstance(result, E.DamageResult) and name in used_later))
            if damage:
                extra += (("damage_results", damage),)
            # v0.114（docs/baby-rules-evolution-v0.114.md 3 章）: 入れ替えの結果（``ForceSwitch`` の、入れ替えて出た控えポケモンの番号）も運ぶ。v0.113 までは運ばず、わるいアリアドスの
            # 「からめとる」（入れ替え → この要素のコインで新しく出てきたポケモンをマヒ）を［サイコリンク］で使ったナツメのフーディンのESPの答えのあとに、マヒの要素が入れ替えなかったと
            # 読んで、黙ってマヒを省いていた（``Status.after_switch``）。入れ替え・コインは処理し直さない（運んだ値を読むだけ）
            switched = tuple(sorted((name, result) for name, result in self.fs.results.items() if type(result) is int and name in used_later))
            if switched:
                extra += (("switched_results", switched),)
        if carry:
            frame = (
                ("reception", tuple(sorted((pid, int(value)) for pid, value in self.fs.reception.items()))),
                ("fired", self.fs.fired),
                ("guts", tuple(sorted((pid, int(value)) for pid, value in self.res.ko_prevention_able.items()))),
            )
            if ko_by:
                frame += (("ko_by", ko_by),)
            frame += flee
            if self.fs.pending:
                # v0.34: まだ処理していない送る効果（「ダメージを受けたとき」の効果。ダメージの要素がすべて終わったあとに処理する。p.89）。持ち主・
                # 持つポケモン・効果の定義の名前・受けたダメージだけを運び、再開のときに場の効果から作り直す（``kernel.restore_deferred``）。
                # 送る効果がないときは v0.33 までと同じ形
                frame += (("pending", tuple((d.instance.owner, d.instance.pokemon_id, d.instance.definition.name, d.received)
                                            for d in self.fs.pending)),)
            extra += (("frame", frame),)
        else:
            # v0.49: ``carry`` でない決定でも、こんじょうの写しのうち、もう HP 以上になったポケモンのもの（きぜつの判定で使う）は運ぶ（``frame`` の ``guts``
            # だけ）。v0.48 までは運ばず、ダメージのあとにエネルギーをトラッシュする決定を出すワザ（わるいリザードンの「れんぞくファイヤーボール」。v0.49 で
            # 「ばける」・［へんしん］からも使える）で、HP 以上になったサカキのカイリキーのきぜつの判定が内部エラーになっていた。HP 以上のポケモンの写しが
            # ないときは v0.48 までと同じ形
            knocked = tuple(sorted((pid, int(value)) for pid, value in self.res.ko_prevention_able.items() if self._knocked_pid(pid)))
            frame = ((("guts", knocked),) if knocked else ()) + ((("ko_by", ko_by),) if ko_by else ()) + flee
            if frame:
                extra += (("frame", frame),)
        # v0.38: ワザを使ったポケモンは枠の番号で指す（ワザの効果で場をはなれたあとの決定でも同じ。キョウのポッポの「でんれい」。場にいれば
        # v0.37 までの ``attacker.pokemon_id`` と同じ値）
        cont = codec.AttackContinuation((self.player, self.fs.frame.source_pid, self.declared.card_id, self.declared.attack_index), kind, extra)
        self.carried = dict(cont.extra)
        self.suspended = codec.attack_decision(self.state, cont, player=player, options=options, min_choices=min_choices,
                                               max_choices=max_choices, push=not self.res.dry_run)
        self.res.trace.record(Suspended("attack", kind, player))


def run_elements(run: AttackRun, start: int) -> bool:
    """要素を ``start`` から順に処理する。決定で止まったら True。最初の効果の要素の前と最後に「ダメージの要素のあと」の窓を開く。

    v0.31: ワザが失敗したら（``run.failed``）残りの要素を処理しない。要素が別の要素の並びに切りかえたら（``run.redirect``。相手のワザを自分の
    ワザとして使う）、その並びの最初から処理する。"""
    res = run.res
    index = start
    while True:
        if run.redirect is not None:
            run.apply_redirect()
            index = 0
        if run.state.pending_moves and settle_moves(run, index):
            return True  # v0.87: 前の要素の入れ替えへの反応（［まきびし］・［やけのこり］）の決定
        if index >= len(run.program):
            break
        element = run.program[index]
        if run.failed and not element.after_failure:
            # v0.79: ワザが失敗したら、残りの要素は処理しない。ただし、説明が失敗しても与えると書く効果（ハガネールの「メタルクラッシュ」の「次の自分の番、このカードは
            # ワザを使えない」。``Element.after_failure``）は処理する
            index += 1
            continue
        # v0.61: ［ずらかる］を確かめる決まった時点（ダメージの要素のまとまりのあと・ダメージ以外の要素の前とあと。送る効果を処理したあと）
        boundary = element.phase is not Phase.DAMAGE or (index > 0 and run.program[index - 1].phase is not Phase.DAMAGE)
        if element.phase is Phase.EFFECT:
            if run.fs.pending and any(later.phase is Phase.DAMAGE for later in run.program[index + 1:]):
                # v0.38: 「ダメージを受けたとき」の効果がはたらいていて、このあとにダメージ以外の効果をはさんでダメージの要素がある（サイドンの「げきとつ」の
                # 入れ替え → 自分にも 20）。その効果を、ダメージの処理（自分へのダメージを含む）をすべてのせたあと・ダメージ以外の効果の前に処理する
                # （CR-COUNTERATTACK-TIMING・CR-FIRE-WALL-TIMING・CR-SHELL-ATTACK-TIMING）時点がなく、決められない（GK1）
                raise res.question("damage_trigger_timing", f"{[d.instance.name for d in run.fs.pending]}・{type(element).__name__} のあとのダメージの要素")
            if fire_or_suspend(run, index):
                return True  # v0.68: ［だつりょくえき］のトラッシュするカードの決定
        elif element.phase is Phase.NEUTRAL and run.fs.pending:
            if any(later.phase is Phase.DAMAGE for later in run.program[index + 1:]):
                raise RuntimeError("ダメージの要素を決めるワザ全体のコイン・確認は、ダメージの要素より前に置く（エンジンの不具合）")
            # v0.41: ダメージの要素のあとの、ダメージ以外の効果だけを決めるワザ全体のコイン（ナツメのモルフォンの「げんかくおんぱ」・v0.37 のニャースの
            # 「ねこにこばん」）。「ダメージを受けたとき」の効果は、そのワザのダメージの処理のあと・ダメージ以外の効果（効果を決めるコインを含む）の前に
            # 処理する（CR-COUNTERATTACK-TIMING・CR-FIRE-WALL-TIMING・CR-SHELL-ATTACK-TIMING）ので、コインの前に処理する。v0.40 までは、ここで
            # RuntimeError（内部エラー）になっていた（ねこにこばんをカイリキーの「はんげき」などに使うと止まった。docs/heal-counter-status-v0.41.md 3.5）
            if fire_or_suspend(run, index):
                return True
        if element.phase is not Phase.DAMAGE and res.flee_offers and offer_flee(run, index):
            return True  # v0.65: ［にげこむ］（ダメージの要素のあと・ダメージ以外の効果の前。送る効果のあと）
        if boundary and not run.fs.pending:
            settle_scram(res, rest=run.program[index:])
        res.trace.record(ElementStarted(run.fs.frame.id, index, type(element).__name__, element.phase.value))
        note_source_form(res, run.fs.frame)  # v0.103: 要素の中でワザを使ったポケモンが場をはなれても、続く無効の判定に要る今の姿を残す
        run.index = index
        run.element_log = len(res.state.log)
        try:
            suspended = element.run(run)
        except EspRedoOffer as offer:
            suspend_esp_redo(run, index, offer)
            return True
        if suspended:
            if not res.dry_run:
                return True
            while run.suspended is not None:  # 先読み: 決定の答えを選んで続ける（答えのあとでもう一度決定を出す要素もある）
                decision, run.suspended = run.suspended, None
                element.resume(run, decision, res.oracle.choose(element.dry_choices(run, decision)))
        index += 1
    if fire_or_suspend(run, len(run.program)):
        return True
    if res.flee_offers and offer_flee(run, len(run.program)):
        return True  # v0.65: 最後のダメージの要素のあと（きぜつの判定の前）
    settle_scram(res, rest=())
    return False


def fire_or_suspend(run: AttackRun, index: int) -> bool:
    """v0.68: 「ダメージの要素のあと」の窓（``kernel.fire_pending``）を開く。［だつりょくえき］の「おもて」で、トラッシュするエネルギーカードを持ち主に選ばせるなら
    （``EnergyDrainRequest``。実際の処理だけ。先読みは答えを選んで続ける）、決定 ``ENERGY_DRAIN_DISCARD`` を出して True。続きの情報の "boundary" は次に処理する要素の位置
    （送る効果はもう処理したので、再開では窓を開き直しても何もしない）、"drain" は (持ち主, ポケモンの番号, カード id, 特殊能力の位置, ダメージを与えたポケモンの番号)。"""
    try:
        fire_pending(run.res, run.fs)
    except EnergyDrainRequest as request:
        run.suspend(kind=ENERGY_DRAIN_DISCARD, player=request.entry[0], options=list(request.options), min_choices=1, max_choices=1, carry=True,
                    extra=(("boundary", index), ("drain", request.entry)) + _unresolved_extra(*request.unresolved))
        return True
    except SplitRequest as request:
        # v0.87: ［ぶんれつ］。持ち主に、山札の名前の合うたねポケモンをベンチに出すかを聞く（0〜1 枚。選べるカードがなくても聞く。続きの情報の "split" は
        # (持ち主, ポケモンの番号, カード id, 特殊能力の位置, 名前)）
        run.suspend(kind=SPLIT_FROM_DECK, player=request.entry[0], options=list(request.options), min_choices=0, max_choices=1 if request.options else 0,
                    carry=True, extra=(("boundary", index), ("split", request.entry)) + _unresolved_extra(*request.unresolved))
        return True
    return False


def suspend_esp_redo(run: AttackRun, index: int, offer: EspRedoOffer) -> None:
    """v0.66: ナツメのESPのやり直しの決定（``ESP_REDO``）をワザを使ったプレイヤーに出す。続きの情報の ``esp`` は (コインを投げた要素の位置, 枚数, 「おもて」の数でまとめる
    コインか, 投げたプレイヤー, 最初の結果, ESPのカード)。答えのあとに、その要素をもう一度処理する（それまでの要素・コイン・ダメージはくり返さない）。"""
    if run.esp_preset is not None:
        raise RuntimeError("ナツメのESPのやり直しの決定を待つ間に、もう一度決定を出そうとした（エンジンの不具合）")
    esp = (index, offer.count, offer.by_heads, offer.flipper, tuple(side.value for side in offer.flips.results), tuple(offer.cards))
    if offer.chain is not None:
        esp += (("chain", offer.chain.coins),)  # v0.115: 条件つきで続けて投げるコインのまとまり（最大の枚数）。v0.114 までの 6 つの値の形は変えない
    elif offer.until_tails:
        esp += (ESP_UNTIL_TAILS,)  # v0.118: 「うら」が出るまで投げるコインのまとまり（枚数は最初の並びの長さ。やり直しの枚数は決まらない）
    elif offer.players:
        esp += (("players", tuple(offer.players)),)  # v0.118: お互いのプレイヤーが 1 枚ずつ投げる 1 つのコイントス（投げた順のプレイヤー）
    unresolved = _unresolved_extra((1,), *offer.problem) if offer.problem is not None else ()
    run.suspend(kind=ESP_REDO, player=run.player, options=(1,), min_choices=0, max_choices=1, carry=True, extra=(("esp", esp),) + unresolved)


def apply_esp_redo(run: AttackRun, esp: tuple, choices: tuple[int, ...]) -> int:
    """v0.66: ESPのやり直しの決定の答え。やり直すなら同じ枚数を投げ直し（ログ ``esp_redo``）、やり直さないならログ ``esp_redo_declined``。採った結果を ``esp_preset`` に置き、
    もう一度処理する要素の位置を返す。"""
    from ..coins import CoinFlips

    index, count, by_heads, flipper, original, cards = esp[:6]
    flips = CoinFlips(tuple(CoinSide(side) for side in original))
    attacker = run.attacker()
    if len(esp) == 7 and esp[6][0] == "chain":
        # v0.115: 条件つきで続けて投げるコインのまとまり。やり直すなら、もう一度処理する要素が同じまとまりを最初から投げ直す（ログ ``esp_redo`` もそこで残す。枚数は面で変わりうる）
        if not choices:
            run.state.add_event("esp_redo_declined", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                cards=tuple(cards), original=tuple(original))
        run.esp_mark()
        run.esp_preset = (ESP_CHAIN_REDO if choices else ESP_CHAIN_KEPT, flips.results)
        return index
    if len(esp) == 7 and tuple(esp[6]) == ESP_UNTIL_TAILS:
        # v0.118: 「うら」が出るまで投げるコインのまとまり。やり直すなら、もう一度処理する要素が最初から「うら」が出るまで投げ直す（ログ ``esp_redo`` もそこで残す。先読みの「おもて」の数の組は
        # その要素だけが求められるので、ここでは投げない）
        if not choices:
            run.state.add_event("esp_redo_declined", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                cards=tuple(cards), original=tuple(original))
        run.esp_mark()
        run.esp_preset = (ESP_UNTIL_REDO if choices else ESP_UNTIL_KEPT, flips.results)
        return index
    if len(esp) == 7 and esp[6][0] == "players":
        # v0.118: お互いのプレイヤーが 1 枚ずつ投げる 1 つのコイントス。相手プレイヤーのコインを含むので、やり直すは選ぶと止める（ES1。答えの確かめで止まる）
        if choices:
            raise RuntimeError("相手プレイヤーのコインを含むコイントスのやり直しを処理しようとした（ES1 で止める選択。エンジンの不具合）")
        run.state.add_event("esp_redo_declined", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            cards=tuple(cards), original=tuple(original))
        run.esp_mark()
        run.esp_preset = (count, flips.results)
        return index
    if esp[6:]:
        raise RuntimeError(f"ナツメのESPの続きの情報 {esp!r} の形が正しくない（エンジンの不具合）")
    if choices:
        flips = run._esp_reflip(count, by_heads, flipper, tuple(cards), flips)
    else:
        run.state.add_event("esp_redo_declined", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            cards=tuple(cards), original=tuple(original))
    run.esp_mark()
    run.esp_preset = (count, flips.results)
    return index


# ---------------------------------------------------------------- v0.87 ワザの途中の場の移動への反応（docs/movement-damage-reactions-v0.87.md 3 章）


def settle_moves(run: AttackRun, index: int) -> bool:
    """前の要素の入れ替え・バトル場に出す処理の事実への反応（``GameState.pending_moves``）を、次の要素（``index``）の前に処理する。決定を出したら True（続きの情報の ``boundary`` は
    ``index``、``moves`` は残りの反応の段）。同じ時点に 2 つ以上の反応があれば、番のプレイヤーが順番を選ぶ（``REACTION_ORDER``。GR-2000-P325-SAME-TIMING）。"""
    queue = M.take(run.state)
    while queue:
        step, queue = queue[0], queue[1:]
        if _settle_move_step(run, index, step, queue):
            return True
    return False


def _settle_move_step(run: AttackRun, index: int, step: tuple, rest: tuple) -> bool:
    res, state = run.res, run.state
    _, label, pending, info = step
    live = []
    for reaction in pending:
        now = M.still_working(state, reaction)
        if now is None:
            continue
        if now != reaction[-1]:
            raise res.question("reaction_condition_changed", f"反応 {reaction!r}")
        if now:
            live.append(reaction)
    if not live:
        return False
    baseline = set(info[2]) if len(info) > 2 else set()
    fresh = [p.pokemon_id for _, p in knocked_out(state) if p.pokemon_id not in baseline]
    if fresh:
        raise res.question("reaction_after_knockout", f"HP 以上のポケモン {fresh}・残りの反応 {[r[0] for r in live]}")
    if len(live) >= 2:
        if res.dry_run:
            chosen = res.oracle.choose([(i,) for i in range(len(live))])[0]
            others = tuple(r for i, r in enumerate(live) if i != chosen)
            return _apply_move(run, index, live[chosen], ((M.SAME, label, others, info),) + rest)
        run.suspend(kind=REACTION_ORDER, player=state.current_player, options=list(range(len(live))), carry=True,
                    extra=(("boundary", index), ("move_order", (M.SAME, label, tuple(live), info)), ("moves", rest)))
        return True
    return _apply_move(run, index, live[0], rest)


def _apply_move(run: AttackRun, index: int, reaction: tuple, rest: tuple) -> bool:
    """反応 1 つを処理する。決定を出したら True。出さなければ残りの段を状態にもどして False（``settle_moves`` が続ける）。"""
    res, state = run.res, run.state
    kind = reaction[0]
    if kind in (M.SPIKES, M.HOT_PLATE):
        child = res.open_frame(FrameKind.POWER_DAMAGE, parent=run.fs.frame.id, player=1 - reaction[1], source_pid=reaction[3][0][1],
                               attack_key=run.fs.frame.attack_key)
        M.power_damage(state, reaction, track=lambda pokemon, before: track_ko(res, child, pokemon, before))
    elif kind == M.MAGMA:
        choice = M.magma_choice(state, reaction)
        if choice is None:
            M.magma_none(state, reaction)
        elif isinstance(choice, M.MagmaChoice):
            blocked, code, reason = choice.unresolved
            if res.dry_run:
                M.magma_move(state, reaction, res.oracle.choose([(uid,) for uid in choice.options if uid not in blocked])[0])
            else:
                run.suspend(kind=MAGMA_POOL_ENERGY, player=choice.player, options=list(choice.options), carry=True,
                            extra=(("boundary", index), ("move_magma", reaction), ("moves", rest)) + _unresolved_extra(blocked, code, reason))
                return True
        else:
            M.magma_move(state, reaction, choice)
    else:
        raise RuntimeError(f"ワザの途中に来ない場の移動の反応 {reaction!r}（エンジンの不具合）")
    state.pending_moves = tuple(rest) + state.pending_moves
    return False


def resume_moves(run: AttackRun, index: int, decision: PendingDecision, carried: dict, choices: tuple[int, ...]) -> bool:
    """v0.87: ワザの途中の場の移動への反応の決定（順番・［やけのこり］のカード）の答え。答えを処理し、残りの反応の段を状態にもどす。もう一度決定を出したら True。"""
    rest = tuple(carried.get("moves", ()))
    if decision.kind == REACTION_ORDER:
        _, label, live, info = carried["move_order"]
        chosen = live[choices[0]]
        others = tuple(r for i, r in enumerate(live) if i != choices[0])
        return _apply_move(run, index, chosen, (((M.SAME, label, others, info),) if others else ()) + rest)
    if decision.kind == MAGMA_POOL_ENERGY:
        if choices[0] in tuple(carried.get("unresolved_choices", ())):
            raise UnsupportedError(carried.get("unresolved_code"), carried.get("unresolved_reason"))
        M.magma_move(run.state, tuple(carried["move_magma"]), choices[0])
        run.state.pending_moves = rest + run.state.pending_moves
        return False
    raise RuntimeError(f"場の移動の反応の決定 {decision.kind} は扱わない（エンジンの不具合）")


# ---------------------------------------------------------------- v0.65 ワザの途中の任意の決定（docs/reactive-decisions-v0.65.md 2 章）


def _unresolved_extra(unresolved: tuple[int, ...], code: str | None, reason: str | None) -> tuple:
    return () if not unresolved else (("unresolved_choices", unresolved), ("unresolved_code", code), ("unresolved_reason", reason))


def _switch_changes_attacker(run: AttackRun, owner: int, option: int) -> bool:
    """入れ替え（``owner`` のバトル場のポケモンと控えの ``option``）で、ワザを使っているポケモンの今の姿（［へんしん］）が変わるか（RX1。状態を変えない）。"""
    state = run.state
    attacker = run.attacker()
    if owner == run.player or E.transform_defender(state, attacker) is None:
        return False  # ［へんしん］で相手の対戦ポケモンの姿になっていなければ、相手の入れ替えで今の姿は変わらない（状態を複製しない。先読みの中でも使う）
    incoming = state.find_pokemon(option)[1]
    return state.cards[incoming.card].card_id != E.form_def(state, attacker).id


def _boundary_answer(run: AttackRun, kind: str, owner: int, options: tuple[int, ...], unresolved: tuple[int, ...], code, reason, extra: tuple):
    """入れ替えの決定（0〜1 個）を出す。先読みなら選ぶ答え（() か (番号,)。止める選択は試さない）を返し、実際の処理なら決定を出して None を返す。"""
    if run.res.dry_run:
        return tuple(run.res.oracle.choose([()] + [(o,) for o in options if o not in unresolved]))
    run.suspend(kind=kind, player=owner, options=list(options), min_choices=0, max_choices=1, carry=True,
                extra=extra + _unresolved_extra(unresolved, code, reason))
    return None


def offer_ninja_trick(run: AttackRun) -> bool:
    """相手がワザを使う時（宣言が受け付けられ、ワザの要素の前）に、ワザを受ける側のバトル場のポケモンについている「キョウ秘伝,変わり身の術」で入れ替えるかを、その持ち主に
    聞く（決定 ``NINJA_TRICK``。再開すると要素の並びの最初から処理する）。使えなければ何もしない。決定で止まったら True。"""
    state = run.state
    owner = 1 - run.player
    tricks = E.usable_ninja_tricks(state, owner)
    if not tricks:
        return False
    options = tuple(p.pokemon_id for p in state.players[owner].bench)
    if E.trainer_use_blockers(state, owner):
        unresolved, code, reason = options, E.NINJA_TRICK_BAN_CODE, E.NINJA_TRICK_BAN_REASON
    else:
        unresolved = tuple(o for o in options if _switch_changes_attacker(run, owner, o))
        code, reason = (E.REACTIVE_SWITCH_TRANSFORM_CODE, E.REACTIVE_SWITCH_TRANSFORM_REASON) if unresolved else (None, None)
    answer = _boundary_answer(run, NINJA_TRICK, owner, options, unresolved, code, reason, (("boundary", 0), ("tricks", tricks)))
    if answer is None:
        return True
    apply_ninja_trick(run, tricks, answer)
    return False


def apply_ninja_trick(run: AttackRun, tricks: tuple[int, ...], choices: tuple[int, ...]) -> None:
    """変わり身の術の答え。入れ替えるなら、変わり身の術のついたポケモンと選んだ控えを入れ替える（「にげる」ではない。ベンチにもどったポケモンの特殊状態・持続する効果は消え、
    変わり身の術はバトル場をはなれたのでトラッシュする（``effects._switch_active_with_bench``）。宣言・それまでのコインはやり直さない）。"""
    state = run.state
    owner = 1 - run.player
    active = state.players[owner].active
    if not choices:
        state.add_event("ninja_trick_declined", player=owner, cards=tuple(tricks), pokemon_id=active.pokemon_id, effect=str(run.declared))
        return
    state.add_event("ninja_trick", player=owner, cards=tuple(tricks), pokemon_id=active.pokemon_id, new_pokemon_id=choices[0], effect=str(run.declared))
    E._switch_active_with_bench(state, owner, choices[0], trainer=tricks[0])


def offer_flee(run: AttackRun, index: int) -> bool:
    """［にげこむ］の候補を順に聞く（決定 ``REACTION_SWITCH``。0 個は使わない）。ダメージを受けたときの特殊状態は候補にしたときに確かめた（``kernel.receiving``）。聞く時点で、
    バトル場にいない・控えがいない・力が消えている（かがくへんかガス・まきちらせ!ベトベトガス）・ショックアイで使えないなら聞かない。自分のワザの中の返す効果のダメージで
    候補になったものは、使うを選ぶと止める（FL1）。決定で止まったら True（残りの候補は続きの情報で運ぶ）。"""
    res = run.res
    state = run.state
    while res.flee_offers:
        owner, pid, card_id, power_index, own_attack = res.flee_offers.pop(0)
        located = state.find_pokemon(pid)
        p = state.players[owner]
        if located is None or p.active is not located[1] or not p.bench:
            continue
        pokemon = located[1]
        if leave_lock(state, owner, pokemon) is not None:
            continue  # v0.93: 「バトル場をはなれられない」なら入れ替えられないので聞かない（使う答えの効果が起こらない）
        instance = next((i for i in C.instances(state, owner, pokemon, res.catalog)
                         if i.definition.decision_kind == REACTION_SWITCH and i.power_key == E.PowerKey(card_id, power_index)), None)
        if instance is None or C.offer_stopped(state, instance, pokemon):
            continue
        options = tuple(b.pokemon_id for b in p.bench)
        if E.knocked_by_hp(state, pokemon):
            from .kernel import knockout_survival_timing

            knockout_survival_timing(res, pokemon, "HP 以上になったあとの［にげこむ］")  # v0.110（KS1）: すぐあとに残りHP 10 にする読み方では KD1 に当たらない
            unresolved, code, reason = options, E.KNOCKED_OUT_REACTION_CODE, E.KNOCKED_OUT_REACTION_REASON  # KD1（同じワザのダメージで HP 以上）
        elif own_attack:
            unresolved, code, reason = options, E.FLEE_OWN_ATTACK_CODE, E.FLEE_OWN_ATTACK_REASON
        else:
            unresolved = tuple(o for o in options if _switch_changes_attacker(run, owner, o))
            code, reason = (E.REACTIVE_SWITCH_TRANSFORM_CODE, E.REACTIVE_SWITCH_TRANSFORM_REASON) if unresolved else (None, None)
        entry = (owner, pid, card_id, power_index)
        answer = _boundary_answer(run, REACTION_SWITCH, owner, options, unresolved, code, reason, (("boundary", index), ("flee", entry)))
        if answer is None:
            return True
        apply_flee(run, entry, answer)
    return False


def apply_flee(run: AttackRun, entry: tuple, choices: tuple[int, ...]) -> None:
    """［にげこむ］の答え。使うなら入れ替え（「にげる」ではない。``effects._switch_active_with_bench``）、そのワザの残りの「ダメージ以外の効果」を、このポケモンにもかわりに出た
    ポケモンにも与えない（``res.fled``。``kernel.reaches``）。"""
    state = run.state
    owner, pid, card_id, power_index = entry
    key = str(E.PowerKey(card_id, power_index))
    pokemon = state.find_pokemon(pid)[1]
    if not choices:
        state.add_event("flee_declined", player=owner, pokemon=pokemon.card, pokemon_id=pid, power=key, effect=str(run.declared))
        return
    state.add_event("flee", player=owner, pokemon=pokemon.card, pokemon_id=pid, power=key, new_pokemon_id=choices[0], effect=str(run.declared))
    E._switch_active_with_bench(state, owner, choices[0], power=key)
    run.res.fled[pid] = choices[0]


def ninja_trick_leave_question(run: AttackRun, pokemon: PokemonInPlay) -> None:
    """v0.65（NT2）: 変わり身の術がついているポケモンを、ワザの効果で、ついているカードといっしょに山札・手札にもどすなら止める（問い。先読みが宣言の前に見つける）。"""
    tricks = E.ninja_tricks(run.state, pokemon)
    if tricks:
        raise run.res.question("ninja_trick_leaves_play", f"ポケモン {pokemon.pokemon_id}（変わり身の術 {list(tricks)}）")


def guarded_damages(run: AttackRun, element: Element, entries, after: Any = None, record: bool = False, *, guard: tuple[int, ...] | None = None,
                    optional: bool | None = None) -> bool:
    """控えポケモンへのダメージを順に与える（``entries`` は (受けるもの, ポケモンの番号, 基本となるダメージ, 弱点・抵抗力を計算するか) の並び）。［ベンチガード］の決定が要るときは、
    残りの並び（今のダメージを含む）・要素の続き（``after``）を続きの情報で運び、決定を出して True を返す（``resume_guarded`` で続ける）。``record`` なら、要素の結果に
    最後のダメージの結果を置く。

    v0.119: 受ける控えポケモンの 8 段階の使うかを選ぶ効果（［シェルアーマー］。``damage.DamageOptionRequired``）も、同じ形で決定（``DAMAGE_OPTION``。決めるのは受けるポケモンの持ち主）を
    出す（p.321 の計算の中なので［ベンチガード］の決定より先）。``guard``・``optional`` は運んだ並びの最初のダメージの答え（決めた答えは、そのダメージのあとの［ベンチガード］の決定の
    続きにも運ぶ）。先読みでは、使う・使わないの両方を試す。"""
    entries = tuple(tuple(entry) for entry in entries)
    for i, entry in enumerate(entries):
        kind, pid, base, wr = entry[:4]
        first_guard, first_optional = (guard, optional) if i == 0 else (None, None)
        try:
            result = deal_damage(run.res, run.fs, kind, base, pokemon_id=pid, weakness_resistance=bool(wr), guard=first_guard, guard_suspend=True,
                                 optional=first_optional, optional_decision=True, **_ignored_effects(entry))
        except BenchGuardRequest as request:
            chosen = (("optional", int(first_optional)),) if first_optional is not None else ()
            run.suspend(kind=BENCH_GUARD, player=request.owner, options=list(request.options), min_choices=0, max_choices=request.max_choices, carry=True,
                        extra=(("element", run.index), ("bench_guard", (entries[i:], after, int(record)))) + chosen + request.extra())
            return True
        except DamageOptionRequired as need:
            if run.res.dry_run:
                return guarded_damages(run, element, entries[i:], after, record, optional=run.res.oracle.choose([False, True]))
            owner, receiver = run.state.find_pokemon(pid)
            run.suspend(kind=DAMAGE_OPTION, player=owner, options=(receiver.pokemon_id,), min_choices=0, max_choices=1, carry=True,
                        extra=(("element", run.index), ("bench_guard", (entries[i:], after, int(record))), *_option_extra(need)))
            return True
        if record:
            run.fs.results[element.name] = result
    return False


def resume_guarded(run: AttackRun, element: Element, decision: PendingDecision, choices: tuple[int, ...]) -> None:
    """［ベンチガード］の答えのあと: 運んだ並びの最初のダメージを答えで与え（計算をやり直す。「とうめい」の結果は続きの情報。コインは投げ直さない）、残りを続け、要素の続き
    （``Element.after_guarded``）を処理する。v0.119: 使うかを選ぶ効果の決定（``DAMAGE_OPTION``）の答えのあとも同じ（最初のダメージに答えを渡す。そのあとの［ベンチガード］の決定は
    もう一度出しうる）。"""
    entries, after, record = run.carried["bench_guard"]
    if decision.kind == DAMAGE_OPTION:
        guard, optional = None, bool(choices)
    else:
        carried = run.carried.get("optional")
        guard, optional = tuple(choices), (None if carried is None else bool(carried))
    if guarded_damages(run, element, entries, after, bool(record), guard=guard, optional=optional):
        return
    element.after_guarded(run, after)


def _option_extra(need: DamageOptionRequired) -> tuple:
    """v0.119: 使うかを選ぶ効果の決定（``DAMAGE_OPTION``）の続きの情報の、効果 (段階, 発生源のカード, 数)・8 段階の前のダメージ・使わないときの最終ダメージ。"""
    option = need.modifiers[0]
    return (("option", (need.step, option.source, option.amount)), ("value", need.value), ("finals", tuple(sorted(need.finals))))


def _ignored_effects(entry: tuple) -> dict:
    """v0.89: 控えポケモンへのダメージの並びの 5 つめ（あれば）は、受けるポケモンの持っている効果を除く書き方（``kernel.IGNORE_HELD``・``IGNORE_UNSTATED``）。だましうちの選んだ控え
    （``TargetDamage`` の ``defender_effects`` が偽）。4 つの並び（v0.88 までの続きの情報の形）なら除かない。"""
    if len(entry) < 5:
        return {}
    return {"defender_effects": False, "ignore_scope": entry[4]}


def opponent_effect_elements(program: tuple) -> tuple[str, ...]:
    """並びの中で、相手の対戦ポケモンに与えるダメージ以外の効果の要素の種類（並びの順番。v0.13 の ``AttackEffect.opponent_effect_elements``
    にあたる値を、ワザの実装の宣言ではなく並びから求める。G37 の理由の文に書く）。"""
    found: list[str] = []
    for element in program:
        for kind in element.opponent_elements:
            if kind not in found:
                found.append(kind)
    return tuple(found)


def declare(program: tuple, res: Resolution, player: int, attacker: PokemonInPlay) -> None:
    """ワザの宣言のあと・こんらんのコインの前の確認（v0.31。``Element.on_declare``。決められない場合は問い）。"""
    for element in program:
        element.on_declare(res, player, attacker)


def decision_index(program: tuple, kind: str) -> int:
    """決定の種類から、決定を出した要素の位置（並びの中で決定を出す要素は 1 つ）。"""
    found = [i for i, element in enumerate(program) if element.decides(kind)]
    if len(found) != 1:
        raise RuntimeError(f"決定 {kind} を出す要素が {len(found)} つ（エンジンの不具合）")
    return found[0]


@dataclass(frozen=True)
class AtLeast:
    """ワザ全体のコインの「おもて」の数が ``count`` 以上（v0.41。要素の ``gate`` の面の代わりに渡す。ナツメのモルフォンの「げんかくおんぱ」の「コインを2枚投げ、
    1枚でも「おもて」なら」）。「おもて」の数だけを使うので、先読みは「おもて」の数でまとめて試せる（v0.35）。"""

    count: int


# ---------------------------------------------------------------- 基本となるダメージ（p.321 の 1 段階）


@dataclass(frozen=True)
class Printed:
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage


@dataclass(frozen=True)
class Fixed:
    amount: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return self.amount


@dataclass(frozen=True)
class PrintedPlusBonus:
    coin: str
    bonus: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + (self.bonus if run.coin_is((self.coin, HEADS)) else 0)


@dataclass(frozen=True)
class HeadsTimes:
    """コインを ``coins`` 枚投げ、「おもて」の数 × ``per``（v0.13 の ``CoinFlipDamage``。みだれづき・ハリケーンパンチ・3ぼんのしっぽなど）。

    v0.35: 結果の使い道は「おもて」の数だけなので、先読みで「おもて」の数にまとめても答えは変わらない（安全に当てはめられる）が、まとめない
    （``by_heads`` は False）。枚数は登録で決まった 2〜4 枚（多くても 16 通り）で上限に届かず、v0.15c・v0.16c の上限のテスト（``ManyCoins``）が
    この値の 1 枚ずつの木を基準にしている（docs/coin-groups-damage-order-v0.35.md 2 章）。"""

    coins: int
    per: int
    by_heads: ClassVar[bool] = False

    @property
    def local_coins(self) -> int:
        return self.coins

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return flips.heads * self.per


@dataclass(frozen=True)
class HeadsUntilTails:
    """「うら」が出るまでコインを投げ続け、その間に出た「おもて」の数 × ``per``（v0.64。化石の秘密のイシツブテの「れんぞくいしなげ」。
    docs/geodude-line-unbounded-coins-v0.64.md）。

    - 実際の対戦では「うら」が出るまで 1 枚ずつ投げる（``coins.flip_until_tails``。枚数・ダメージに上限はない）。1 枚目が「うら」なら基本となるダメージは 0
      （2 段階で計算を終える「ダメージを与えなかった」。ワザの失敗ではない）
    - 先読みは「おもて」の数の有限の組（``resolution.unbounded.head_classes``）の代表だけを試す。代表の値を実際のダメージ・ログ・履歴に使わない
    - コインはダメージの量だけを決めるので、「ダメージを受けない」相手には v0.4b の問い（``local_coins`` が 1 以上なのはそのため。``Damage.run``）
    - コインを投げたあとで決定（順番の決定）をまたいでも、基本となるダメージを続きの情報で運び、投げ直さない（``Damage.resume``）

    v0.92: ``fixed``（ハッサムの「メタルニッパー」の目安の 30。既定 0）。基本となるダメージは ``fixed + per × おもての数``（``damage_for``）。実際のダメージ・先読みの組を分けるキー・
    有限の境界（``resolution.unbounded``）はどれも ``damage_for`` で求める（キーを ``per × おもての数`` のまま作らない）"""

    per: int
    fixed: int = 0
    local_coins: ClassVar[int] = 1

    def damage_for(self, heads: int) -> int:
        """「おもて」の数 ``heads`` のときの基本となるダメージ（p.321 の 1 段階）。"""
        return self.fixed + self.per * heads

    def flip_until_tails(self, run: AttackRun, element: Damage) -> CoinFlips:
        """v0.118: ナツメのESPのやり直しは ``AttackRun.flip_until_tails``（「うら」が出るまでの一まとまりのあとに聞き、やり直すなら最初から投げ直す）。v0.117 までは、ESPのついた
        ポケモンがこのワザを使うと内部エラーにしていた（［サイコリンク］と超の色マーカーで届く。docs/unbounded-coins-heal-allocation-v0.118.md 2 章）。先読みの組は、最初と
        やり直しのどちらのコインでも、この要素の今の場から求める（ESPの決定のあいだに場は変わらない）。"""
        from .unbounded import head_classes

        found: list = []

        def classes():
            if not found:
                found.append(head_classes(run, element, self.per))
            return found[0]

        return run.flip_until_tails(classes)

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return self.damage_for(flips.heads)


@dataclass(frozen=True)
class HeadsOwnCounters:
    per: int
    local_coins: ClassVar[int] = 1

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        counters = run.attacker().damage // run.state.rules.damage_per_counter
        return counters * self.per if flips.results[0] is HEADS else 0


def transform_energy_question(run: AttackRun, pokemon: PokemonInPlay, energy_type: EnergyType, *, cards: bool, wild: bool = True) -> None:
    """v0.49（TE1）: ワザの説明が ``pokemon`` についている ``energy_type`` のエネルギー（カード）を数える・トラッシュするとき、［へんしん］の「どの色のエネルギー
    としても使うことができる」が当てはまるかで、数える・選べるカードが変わるなら止める（``E.energy_type_readings`` が 2 つの読み方を返すとき）。［へんしん］が
    はたらいていない・ついているエネルギーがどれも ``energy_type`` なら何もしない。必要なエネルギーの支払い（``E.attack_cost_payable``）とは別の問い。

    v0.88（docs/type-energy-colors-v0.88.md 3 章）: ``cards`` は説明が数える・選ぶものの種類。真なら「「X」エネルギーカード」（カードとしての色）で、エナジーコンバーター・こうごうせいで
    色が変わったカードが当たるかが決まらなければ止める（CE3）。偽なら「「X」エネルギー」（エネルギーの今の色。``E.typed_unit_count``）で、色の読み方（CE1・CE2）で数が変われば止める。"""
    if len(E.energy_type_readings(run.state, pokemon, energy_type)) > 1:
        raise run.res.question("transform_energy_count", f"ポケモン {pokemon.pokemon_id}・「{energy_type.ja}」エネルギー")
    # v0.58（RB1）: レインボーエネルギーが、説明の「「X」エネルギー(カード)」に当たるかが決まらない（数える・選べるカードが変わる）なら止める
    rainbow = E.ambiguous_rainbow_cards(run.state, pokemon, energy_type)
    if rainbow:
        raise run.res.question("rainbow_energy_type", f"ポケモン {pokemon.pokemon_id} のレインボーエネルギー {rainbow}・「{energy_type.ja}」エネルギー")
    # v0.59（BZ2）: ［エネエネ］でその色のエネルギーになったカードが、説明の「「X」エネルギー(カード)」に当たるかが決まらない
    converted = E.converted_energy_cards(run.state, pokemon, energy_type)
    if converted:
        raise run.res.question("buzzap_energy_type", f"ポケモン {pokemon.pokemon_id} のカード {converted}・「{energy_type.ja}」エネルギー")
    # v0.85（MEC1）: ミラクルエネルギーが、説明の「「X」エネルギー(カード)」に当たるかが決まらない
    miracle = E.ambiguous_miracle_cards(run.state, pokemon, energy_type)
    if miracle:
        raise run.res.question("miracle_energy_type", f"ポケモン {pokemon.pokemon_id} のミラクルエネルギー {miracle}・「{energy_type.ja}」エネルギー")
    if cards:
        changed = E.color_changed_cards(run.state, pokemon, energy_type)
        if changed:
            raise run.res.question("color_changed_energy_card", f"ポケモン {pokemon.pokemon_id} のカード {changed}・「{energy_type.ja}」エネルギーカード",
                                   E.color_card_error(pokemon, energy_type, changed))
    else:
        problem = E.typed_unit_count_problem(run.state, pokemon, energy_type)
        if problem is not None:
            raise run.res.question(COLOR_QUESTION_BY_CODE[problem.code], f"ポケモン {pokemon.pokemon_id}・「{energy_type.ja}」エネルギーの数", problem)
    if wild:
        # v0.89: ``wild`` が偽（「草」でない色を数える。``typed_units_for``）なら、［おいしげる］で「草」の個数が決まらないことでは止めない（その色の数は変わらない）
        wild_growth_question(run, pokemon)


# v0.88: 色の読み方の止めるコード → 問い（``kernel.COLOR_QUESTIONS`` と同じ問い）
COLOR_QUESTION_BY_CODE = {E.COLOR_CONTINUATION_CODE: "color_effect_continuation", E.COLOR_OVERLAP_CODE: "color_replacement_order", E.COLOR_CARD_CODE: "color_changed_energy_card",
                          E.COLOR_MARKER_PRECEDENCE_CODE: "color_marker_precedence"}  # v0.90: CM1


def wild_growth_question(run: AttackRun, pokemon: PokemonInPlay | None) -> None:
    """v0.85: ワザの説明が ``pokemon`` についているエネルギーの個数・色を数えるとき、［おいしげる］で「草」2 個になるかが決まらないカード（VS1・RB1・BZ2・MEC1）があれば止める
    （個数はかならず変わる）。"""
    if pokemon is None:
        return
    found = E.wild_growth_ambiguities(run.state, pokemon)
    if not found:
        return
    uid, kind = found[0]
    name = {"vs1": "shift_color_duration", "rb1": "rainbow_energy_type", "bz2": "buzzap_energy_type", "mc1": "miracle_energy_type",
            "ce1": "color_effect_continuation", "ce2": "color_replacement_order", "ce3": "color_changed_energy_card",
            "cm1": "color_marker_precedence"}[kind]  # v0.88: CE1〜CE3。v0.90: CM1
    raise run.res.question(name, f"［おいしげる］（「草」エネルギーカードは「草」2 個ぶん）・ポケモン {pokemon.pokemon_id} のカード {uid}")


def rainbow_attach_question(run: AttackRun, uids, energy_type: EnergyType) -> None:
    """v0.58（RB2）: 山札・トラッシュ・手札から「「○」エネルギーカード」をつけるワザで、選べるかもしれないレインボーエネルギーがあれば止める。"""
    cards = E.rainbow_cards_in(run.state, uids)
    if cards:
        raise run.res.question("rainbow_attach_type", f"レインボーエネルギー {cards}・「{energy_type.ja}」エネルギーカード")


@dataclass(frozen=True)
class ExtraEnergy:
    energy_type: EnergyType
    per: int
    max_extra: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        attacker = run.attacker()
        transform_energy_question(run, attacker, self.energy_type, cards=False)  # v0.49: TE1
        # v0.88: 説明の「「水」エネルギー」はエネルギーの今の色で数える（エナジーコンバーターで変わった色も。基本エネルギーカードだけの場では v0.87 までのカードの枚数と同じ）
        attached = E.typed_unit_count(run.state, attacker, self.energy_type)
        return run.attack.damage + min(max(0, attached - len(run.attack.cost)), self.max_extra) * self.per


@dataclass(frozen=True)
class PrintedMinusOwnCounters:
    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage - run.attacker().damage // run.state.rules.damage_per_counter * self.per


# ---------------------------------------------------------------- 要素


class Element:
    phase: ClassVar[Phase]
    decision_kind: ClassVar[str | None] = None
    # v0.40: 山札の並び（上から何枚目か）を使う要素（引く・山札の上からトラッシュする）。先読み（``res.dry_run``）で山札を切らない要素は、あとにこの要素が
    # あれば止める（``shuffle_in_attack``。切った並びを先読みで使えない）
    reads_deck_order: ClassVar[bool] = False

    @property
    def opponent_element(self) -> str | None:
        """相手の対戦ポケモンに与える、ダメージ以外の効果の要素の種類（``effects.ATTACK_ELEMENTS``。なければ None）。"""
        return None

    @property
    def opponent_elements(self) -> tuple[str, ...]:
        """相手の対戦ポケモンに与えうる、ダメージ以外の効果の要素の種類のすべて（v0.34。コインでどちらかになる要素（くさいガスのどく・こんらん）は 2 つ）。"""
        kind = self.opponent_element
        return () if kind is None else (kind,)

    def run(self, run: AttackRun) -> bool:
        raise NotImplementedError

    def decides(self, kind: str) -> bool:
        """決定の種類 ``kind`` を出す要素か（再開する要素を決定の種類から探す。v0.16b から要素が答える）。v0.65: 控えポケモンへのダメージの要素は［ベンチガード］の決定も出す。"""
        return (self.decision_kind is not None and self.decision_kind == kind) or (kind in (BENCH_GUARD, DAMAGE_OPTION) and self.guards_bench)

    # v0.65: 控えポケモンへのダメージを ``guarded_damages`` で与える要素（［ベンチガード］の決定を出して続けられる）
    guards_bench: ClassVar[bool] = False

    @property
    def after_failure(self) -> bool:
        """v0.79: ワザが失敗した（``run.failed``）あとも処理する要素か（既定は偽。失敗したら残りの要素を処理しない。v0.31）。"""
        return False

    def after_guarded(self, run: AttackRun, after: Any) -> None:
        """［ベンチガード］の決定のあと、控えポケモンへのダメージをすべて与えてからの、この要素の続き（v0.65。既定はない）。"""

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        """決定の答えのあと。v0.16b から、``resume`` がもう一度決定を出してもよい（``run.suspended``。v0.13 の約束の 2 段階の決定）。"""
        raise NotImplementedError(f"{type(self).__name__} は決定を出さない")

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        """先読みで試す答え: 決定に合うすべての答え（選ぶ数・選ぶもの・順番。v0.15c）。"""
        return all_answers(decision)

    def on_declare(self, res: Resolution, player: int, attacker: PokemonInPlay) -> None:
        """ワザの宣言のあと・こんらんのコインの前の確認（v0.31）。既定は何もしない。"""
        return None

    def has_target(self, run: AttackRun) -> bool:
        """処理の対象があるか（v0.38。``Coin`` が、このコインが決める要素のどれにも対象がなければ投げない（p.309。v0.31 のスーパーデストロイ・v0.33 の
        かけぬけると同じ読み方））。既定はある。対象がなくなりうる要素（控えポケモン全員へのダメージ）だけが上書きする。"""
        return True

    def coin_dependent(self, name: str) -> bool:
        """ワザ全体のコイン ``name`` の結果で、処理する・量が変わる要素か（v0.34。``gate`` の面・基本となるダメージの ``coin``・トラッシュの枚数の
        ``heads_of``）。"""
        gate = getattr(self, "gate", None)
        if gate is not None and gate[0] == name:
            return True
        if getattr(getattr(self, "base", None), "coin", None) == name:
            return True
        return getattr(self, "heads_of", None) == name

    def coin_receiver(self) -> str | None:
        """コインが決める要素として、相手の対戦ポケモンへのダメージの要素（``"damage"``）か効果の要素（``"effect"``）か（v0.34。``void_coin_question``）。
        ほか（ワザを使ったポケモン自身・控え・山札・手札への要素）は None: 相手の対戦ポケモンの「ダメージを受けない」「ワザをうけない」状態で無効に
        ならない。コインで処理が決まる要素を相手の対戦ポケモンに与える要素を加えたら、上書きする（tests が並びの要素の型を確かめる）。"""
        return None

    def discard_protected(self, run: AttackRun) -> bool:
        """v0.119（docs 8 章）: この要素が、トラッシュにあるカードを動かすことだけで、今［アレルギーほうし］がはたらいている（トラッシュのカードが効果を受けない）か。``Coin`` は、決める
        要素の処理の対象のあるものがどれもそう（または ``leave_blocked``）で、そのうち 1 つ以上がこれなら、投げる前に AP1 にする。既定は偽（トラッシュのカードを動かす要素だけが上書きする）。"""
        return False

    def leave_blocked(self, run: AttackRun) -> bool:
        """v0.94（docs/switch-return-attacks-v0.94.md 6 章）: ワザ全体のコインが決めるこの要素が、「バトル場をはなれられない」ポケモンをバトル場からはなれさせることだけか
        （その部分は起こらない）。``Coin`` は、決める要素の処理の対象のあるものがどれもそうなら、投げる前に AL2 にし、ほかに有効な要素があれば、それだけを無効の判定
        （``void_coin_question``）にかける。既定は偽（移動の要素だけが上書きする）。"""
        return False

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        """相手のワザを自分のワザとして使うとき（v0.31。``CopyOpponentAttack``）、この要素を ``copier`` のワザとして処理できるか。できなければ
        (種類, 理由)。種類は ``ILLEGAL``（説明が使えないとする）・``UNRESOLVED``（原典で決められない）・``UNSUPPORTED``（エンジンの未対応）。
        ``clause`` は使う効果の説明の条件（``CANNOT_USE``: 「ほかに必要な条件…がたりないときには使えない」）。既定は処理できる。"""
        return None


ILLEGAL = "illegal"
UNRESOLVED = "unresolved"
UNSUPPORTED = "unsupported"
# 相手のワザを自分のワザとして使う効果の説明の条件（``CopyOpponentAttack.clause``）
CANNOT_USE = "cannot_use"  # 「ほかに必要な条件（エネルギーカードをはがしてすてるなど）がたりないときには使えない」（ピクシー）
FOLLOW_TEXT = "follow_text"  # 「ワザに必要なエネルギー以外はワザの説明にしたがう」（ピッピ。kyuura の card_differences の PMCG1-067 の記録）


def combinations_answers(decision: PendingDecision, sizes) -> list[tuple[int, ...]]:
    """決定の選べるものから、``sizes`` の数を選ぶ組み合わせ（順番を区別しない。v0.31）。選んだ順番で結果が変わらない決定（トラッシュするカードは
    ついている順に処理する）だけに使う。"""
    return [answer for count in sizes for answer in itertools.combinations(decision.options, count)]


def all_answers(decision: PendingDecision, *, minimum: int = 0) -> list[tuple[int, ...]]:
    """決定に合うすべての答え（``min_choices``（と ``minimum`` の大きいほう）〜``max_choices`` 個の、重ならない選択の並び。
    ``decisions.check_choices`` が受け付けるもの）。代表を選ばない（v0.15c。docs/preflight-optimization-v0.15c.md 3 章）。"""
    return list(iter_answers(decision, minimum=minimum))


def iter_answers(decision: PendingDecision, *, minimum: int = 0):
    """``all_answers`` と同じ答えを同じ順に 1 つずつ返す（v0.63。答えの数が多い決定（たたきつけろ!挑戦状の「好きなだけ」）で、すべてを並びにしない）。"""
    low = max(decision.min_choices, minimum)
    for count in range(low, decision.max_choices + 1):
        yield from itertools.permutations(decision.options, count)


def answer_count(decision: PendingDecision) -> int:
    """``all_answers(decision)`` の数（v0.63。並びを作らずに数える）。"""
    n = len(decision.options)
    return sum(math.perm(n, count) for count in range(decision.min_choices, decision.max_choices + 1) if count <= n)


@dataclass(frozen=True)
class Coin(Element):
    """ワザ全体のコイン（ダメージと効果の両方を決める）。v0.31: ``count`` 枚（カツラのリザードの「やきはらう」は 3 枚）、または ``per_attached``
    のエネルギーカードがワザを使うポケモンについている数だけ（わるいリザードンの「れんぞくファイヤーボール」。0 枚なら投げない）。"""

    name: str
    count: int = 1
    per_attached: EnergyType | None = None
    per_opponent_energy: bool = False  # v0.83: 相手（相手の対戦ポケモン）についている「エネルギー」の数だけ（ひかるセレビィの「ミラクルリーフ」。エネルギーの個数）
    # v0.112: ワザを実際に使ったポケモンについている「X」エネルギーの数だけ（ドククラゲ・オムスターの「しょくしゅをつかう」。エネルギーの個数で、``per_attached`` の基本エネルギー
    # カードの枚数とは別。``typed_units_for`` の数え方と問い）
    per_own_typed: EnergyType | None = None
    # v0.113: 場のポケモンの数だけ（(範囲, 名前)。``counted_pokemon`` の範囲（``SCOPE_*``）と名前（None なら名前でしぼらない））。数えるのはこのコインの要素を処理する時点の場
    # （バトル場とベンチの場のポケモン。進化して重なったカード・ついているカードを別の 1 匹にしない）。ピッピの「みんなでおどる」・ロケット団のニャースの「だいぎゃくてん？」は
    # お互いの場（``FIELD_POKEMON``。数だけを使うので、うらのカード・場でポケモンとしてあつかうトレーナーも 1 匹で、正体を読まない）、ヤミカラスの「むれでつつく」は自分のベンチの
    # 「ヤミカラス」（今の姿の名前の完全一致。名前の読めないうらのカードがあれば既存の FD1）
    per_pokemon: tuple[str, tuple[str, ...] | None] | None = None
    phase: ClassVar[Phase] = Phase.NEUTRAL

    def __post_init__(self) -> None:
        if sum((self.per_attached is not None, self.per_opponent_energy, self.per_own_typed is not None, self.per_pokemon is not None)) > 1:
            raise ValueError("コインの枚数の決め方（per_attached・per_opponent_energy・per_own_typed・per_pokemon）は 1 つだけ")
        if self.per_pokemon is not None:
            scope, names = self.per_pokemon
            if scope not in (SCOPE_OWN_BENCH, SCOPE_OWN_IN_PLAY, SCOPE_BOTH_IN_PLAY) or not (
                    names is None or (type(names) is tuple and names and all(type(name) is str and name for name in names))):
                raise ValueError(f"場のポケモンの数え方 {self.per_pokemon!r} は (範囲, 名前のタプルか None)")

    def run(self, run: AttackRun) -> bool:
        count = self.count
        if self.per_attached is not None:
            transform_energy_question(run, run.attacker(), self.per_attached, cards=True)  # v0.49: TE1
            count = len(E.attached_basic_energy(run.state, run.attacker(), self.per_attached))
        if self.per_opponent_energy:
            count = all_energy_units(run.state, run.opponent_active(), run)
        if self.per_own_typed is not None:
            count = typed_units_for(run, run.attacker(), self.per_own_typed)
        if self.per_pokemon is not None:
            count = len(counted_pokemon(run.state, run.player, *self.per_pokemon))
        decided = [element for element in run.program if element.coin_dependent(self.name)]
        if count and decided and not any(element.has_target(run) for element in decided):
            # v0.38: このコインが決める要素のどれにも処理の対象がない（フリーザーの「ふぶき」で、自分にも相手にも控えポケモンがいない）。投げない（p.309。
            # v0.31 のスーパーデストロイ・v0.33 のかけぬけると同じ読み方）。結果のないコインの面は、どの要素も満たさない（``coin_is``）
            count = 0
        if count:
            # v0.34: このコインが決める要素（``coin_dependent``）がどれも、受ける相手の対戦ポケモンにとって無効なら、投げるかが決められない。
            # v0.38: 処理の対象がない要素（控えのいない側の控えへのダメージ）は、コインの結果で場を変えないので数えない（カツラのギャロップの「ふみあらす」を、
            # 控えのいない「ワザをうけない」相手に使うと、追加のダメージだけが残り、それも無効。v0.37 までの型では has_target を上書きする要素がなく、同じ）
            targeted = [element for element in decided if element.has_target(run)]
            # v0.94（docs/switch-return-attacks-v0.94.md 6 章）: 「バトル場をはなれられない」ポケモンを動かすだけの要素（``leave_blocked``。その部分は起こらない）は、コインの結果で
            # 場を変えない。決める要素がどれもそうなら、投げるかが決まらない（AL2。v0.93 のやみのこえの ``has_target`` の確かめを、コインの側にまとめた）。ほかに有効な要素が
            # あれば投げ、その要素だけを無効の判定にかける（追加のダメージ・相手の特殊状態・自分の入れ替えを、移動が起こらないことで捨てない）
            movable = [element for element in targeted if not element.leave_blocked(run) and not element.discard_protected(run)]
            if targeted and not movable:
                protected = [type(element).__name__ for element in targeted if element.discard_protected(run)]
                if protected:
                    # v0.119（AP1。docs 8 章）: ［アレルギーほうし］でトラッシュのカードが効果を受けない要素だけ（処理の対象がないと読むか、効果を受けないだけと読むかで、投げるかが変わる）
                    raise run.res.question("discard_protected_coin", f"ワザ {run.key} のコインが決める要素 {protected}・［アレルギーほうし］ "
                                                                     f"{list(E.discard_protection(run.state))}")
                raise run.res.question("leave_locked_coin", f"ワザ {run.key} のコインが決める要素 {[type(element).__name__ for element in targeted]} は、どれも"
                                                            "はなれられないポケモンの移動だけ")
            void_coin_question(run, movable)
        by_heads = (self.count > 1 or self.per_attached is not None or self.per_opponent_energy or self.per_own_typed is not None
                    or self.per_pokemon is not None)
        if by_heads and any(isinstance(getattr(element, "gate", None), tuple) and element.gate[0] == self.name and isinstance(element.gate[1], CoinSide)
                            for element in run.program):
            # v0.35: 2 枚以上のワザ全体のコインは、あとの要素が「おもて」の数（``coin_is`` の数・``heads``・``heads_of``）だけを使う。1 枚目の面を
            # 使う要素があると、先読みで「おもて」の数にまとめられない（並びで処理が変わる）
            raise RuntimeError(f"2 枚以上のワザ全体のコイン {self.name} の 1 枚目の面を使う要素がある（エンジンの不具合）")
        run.fs.coins[self.name] = run.flip(count, by_heads=by_heads) if count else CoinFlips(())
        return False


def void_coin_question(run: AttackRun, decided: list[Element]) -> None:
    """コインの前に（v0.34）: コインの結果で処理が決まる要素 ``decided`` がどれも相手の対戦ポケモンへの要素で（``coin_receiver``）、どれもその
    ポケモンにとって無効なら、コインを投げても場は変わらないので、投げるかが決められない（kyuura の UQ-COIN-IN-NULLIFIED-ELEMENT と同じ形の問い）。

    - 相手の対戦ポケモンが前の要素の「とうめい」で受けないと決まっている: T19b（``evaded_effect_coin``）
    - 効果の要素があり、効果の要素も無効にする状態（「ワザをうけない」。バリアー）: HC3（``prevented_effect_coin``。v0.33 のパルシェンの「からではさむ」と
      同じ。ロケット団のベトベターの「ねばりつく」・サカキのゴーリキーの「じごくがため」も、追加のダメージとマヒがどちらも無効になる）
    - ダメージの要素だけで、ダメージの要素を無効にする状態（かたまる・バリアー）: v0.4b の ``prevented_coin_damage``（ゴッドバード）
    - どれかの要素が無効にならない（自分へのダメージ・自分のエネルギーのトラッシュ・ドロー・「ダメージを受けない」状態の相手へのマヒなど）: 投げる
      （kyuura の CR-STICKY-VS-PREVENTED と同じ読み方）"""
    roles = [element.coin_receiver() for element in decided]
    if not roles or None in roles:
        return
    # v0.56: 控えポケモンへのダメージの要素（``BenchDamage``）は、受ける控えポケモンがみなダメージを受けない（見えない壁）ときだけ無効と数える。有効な要素があれば投げる。
    # すべての要素が控えへのダメージで、どれも無効なら、v0.4b と同じ問い（ダメージを受けない相手へのダメージの量だけを決めるコインを投げるか）
    bench = [element for element in decided if element.coin_receiver() == "bench"]
    if bench:
        if not all(element.void_for_all(run) for element in bench):
            return
        if len(bench) == len(decided):
            raise run.res.question("prevented_coin_damage", f"ダメージを受けない控えポケモン（見えない壁）への要素 {[type(e).__name__ for e in bench]} だけを決めるコイン")
        roles = [role for role in roles if role != "bench"]
    from .kernel import first_void

    owner, target = 1 - run.player, run.opponent_active()
    if run.fs.reception.get(target.pokemon_id) is False:
        final = run.fs.evaded.get(target.pokemon_id)
        raise run.res.question("evaded_effect_coin", f"ポケモン {target.pokemon_id}",
                               None if final is None else E.evaded_effect_coin_error(target.pokemon_id, final))
    # v0.80（docs/neo-trainer-components-v0.80.md 6 章）: ダメージの要素と効果の要素は、それぞれを無効にする効果で別々に確かめる（v0.79 までは「効果の要素を無効にするなら
    # ダメージの要素も無効」として、効果の要素があれば効果の窓だけを見ていた。エフェクトガードは効果の要素だけを無効にする）。どれかの要素が有効なら投げる
    effect_void = first_void(run.res, run.incoming(), owner, target, Window.BEFORE_EFFECT) if "effect" in roles else None
    damage_void = first_void(run.res, run.incoming(), owner, target) if "damage" in roles else None
    if ("effect" in roles and effect_void is None) or ("damage" in roles and damage_void is None):
        return
    if "effect" in roles:
        covers = Window.BEFORE_DAMAGE in effect_void.definition.windows  # バリアーはダメージの要素も無効にする（v0.79 までと同じ理由の文）
        kinds = effect_void.implementation.kind if covers or damage_void is None else f"{effect_void.implementation.kind}・{damage_void.implementation.kind}"
        raise run.res.question("prevented_effect_coin", f"ポケモン {target.pokemon_id}（{kinds}。ダメージと効果を決めるコイン）")
    raise run.res.question("prevented_coin_damage", f"ポケモン {target.pokemon_id}",
                           E.prevented_coin_damage_error(target.pokemon_id, damage_void.implementation.kind))


@dataclass(frozen=True)
class FailOnTails(Element):
    """コインを ``count`` 枚投げ、1 つでも「うら」ならワザは失敗する（v0.31。ファイヤーの「ゴッドバード」・わるいリザードの「ファイヤーボール」。p.323
    「12 ワザの失敗」: 失敗してもワザを使ったことになる）。結果はワザ全体のコイン ``name`` として、あとの要素も使う。v0.33: タケシのサイホーンの
    「ドリルタックル」は 2 枚（すべて「おもて」のときだけ残りの要素を処理する）。

    v0.34: このコインは残りの要素すべてを処理するかを決めるので、コインの前に ``void_coin_question`` で残りの要素を確かめる（v0.31〜v0.33 の
    ``only_damage``・``with_effect`` は、ワザごとに並びへ書いた印だった。並びから求める形にした。結果は同じ: ゴッドバード・ドリルタックルなど
    相手へのダメージだけなら v0.4b の問い、からではさむ（ダメージとマヒ）はバリアーで HC3、ファイヤーボールは自分のエネルギーのトラッシュが
    残るので投げる）。"""

    name: str = "coin"
    count: int = 1
    # v0.121（docs/hand-bench-attack-conditions-v0.121.md 8 章）: ワザを使ったポケモンに、このワザのコインの「うら」でワザが失敗しなくなる効果（コイルの「ロックオン」。``E.failure_waiver``）が
    # はたらいていれば、コインは実際に投げ、「うら」でも失敗しない（「うら」を書きかえない。ログ ``attack_failure_waived``）
    waiver: bool = False
    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        index = next((i for i, element in enumerate(run.program) if element is self), None)
        if index is None:
            raise RuntimeError("ワザの失敗のコインの要素が、処理している要素の並びにない（エンジンの不具合）")
        # v0.80（docs/neo-trainer-components-v0.80.md 2 章）: ワザが失敗しても処理する要素（``after_failure``。メタルクラッシュの「(その場合も、…)」）は、このコインの結果で
        # 処理が決まらないので、コインが決める要素に数えない（v0.79 は数えていて、「ダメージを受けない」相手にも投げていた）
        void_coin_question(run, [element for element in run.program[index + 1:] if not element.after_failure])
        flips = run.flip(self.count, by_heads=True)  # v0.35: すべて「おもて」か（「おもて」の数が枚数か）だけを使う
        run.fs.coins[self.name] = flips
        if any(side is TAILS for side in flips.results):
            waiver = E.failure_waiver(run.state, run.attacker(), run.key) if self.waiver else None
            if waiver is None:
                run.fail("coin")
            else:
                attacker = run.attacker()
                run.state.add_event("attack_failure_waived", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                    persistent_effect=waiver.kind, target_pokemon=waiver.target_pokemon)
        return False


@dataclass(frozen=True)
class ReparalysisGuard(Element):
    """ワザ全体のコインの前に、マヒの再付与で回復する番が決まらない場合を確かめる（v0.13 の ``CoinBonusDamageAndParalyze``）。"""

    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        target = run.opponent_active()
        if E.status_immunity(run.state, 1 - run.player, target) is not None:
            return False  # v0.46: マヒにならない（［めんえき］）ので、回復する番は変わらない
        problem = paralysis_problem(run.state, 1 - run.player, target)
        if problem is not None:
            raise run.res.question("reparalysis_recovery_turn", problem.code, error=problem)
        return False


@dataclass(frozen=True)
class Damage(Element):
    """ダメージの要素。``gate`` はワザ全体のコインの面、``local_gate`` はこの要素のコイン 1 枚の面（でんげき）。``base`` が要素の中の
    コインで量を決めるなら、受けるポケモンがダメージを受けない状態のとき、そのコインを投げるかが決まらない（v0.4b。コインの前に止める）。"""

    target: str
    base: Any
    name: str = "damage"
    gate: tuple | None = None
    local_gate: CoinSide | None = None
    coin_name: str | None = None  # v0.31: ``local_gate`` のコインを、ワザ全体のコインとしてこの名前で残す（でんきタックル）
    requires: str | None = None  # v0.31: トラッシュの要素の名前。トラッシュできなかったら（``Discarded.outcome``）ダメージはなくなる・0 になる
    weakness_resistance: bool = True  # v0.31: False なら「弱点・抵抗力」に関係なく
    resistance: bool = True  # v0.45: False なら「抵抗力」の影響を受けない（弱点は計算する。タケシのイシツブテの「スパイラルショット」）
    # v0.40: 受けるポケモンの名前（いちばん上のカードの名前の完全一致）がこのどれかのときだけ与える（わるいマタドガスの「みんなでばくはつ」の「お互いの場にいる
    # 全ての「ドガース」「マタドガス」「わるいマタドガス」に、それぞれ20ダメージ」の、相手の対戦ポケモンと自分へのダメージ）。None なら名前を見ない
    names: tuple[str, ...] | None = None
    # v0.60: False なら、相手の持っている「弱点・抵抗力・特殊能力・その他の効果」の影響を受けない（タケシのサンドパンの「スピードスター」。``kernel.deal_damage`` の
    # ``defender_effects``。相手の対戦ポケモンへのダメージだけ）
    defender_effects: bool = True
    # v0.88: 受けるポケモンを、前の ``ChooseColor`` で選んだ色でしぼる（(``COLOR_BY_ENERGY`` か ``COLOR_BY_TYPE``, 選んだ色の結果の名前)。``color_filter_hit``）。None ならしぼらない
    color_filter: tuple[str, str] | None = None
    # v0.91: 受けるポケモンに種類 ``marker`` のマーカーがのっているときだけ与える（エレブーの「かみなりショック」の「「ひらいしんマーカー」をのせているすべてのポケモンに、それぞれ
    # 20ダメージ」の、相手の対戦ポケモンと自分へのダメージ）。この要素を処理する時点の場で見る。None ならマーカーを見ない
    marker: str | None = None
    # v0.114: 受けるポケモンが、この要素を処理する時点で「特殊能力」を持っている（``effects.holds_power``）ときだけ与える（ピチューの「パチパチ」。うらのカードは持たないので、おもてにしない）
    has_power: bool = False
    # v0.115: 受けるポケモンの今有効なタイプがこれでないときだけ与える（サナギラスの「すなあらし」の「おたがいの場の「闘」ポケモン以外のポケモン全員に」の、相手の対戦ポケモンと自分への
    # ダメージ。この要素を処理する時点のタイプ。読み方（VS1 ほか）で変われば止め、うらのカードはタイプを読めない（FD1）。``not_of_type``）。None ならタイプを見ない
    exclude_type: EnergyType | None = None
    # v0.115: 受けるポケモンが、この要素を処理する時点で「エネルギーカード」をつけているときだけ与える（わるいエーフィの「サイコスプラッシュ」。0 枚のポケモンは説明の対象ではない）
    energy_cards: bool = False
    phase: ClassVar[Phase] = Phase.DAMAGE

    def coin_receiver(self) -> str | None:
        return "damage" if self.target == OPP else None

    def has_target(self, run: AttackRun) -> bool:
        if (self.names is None and self.color_filter is None and self.marker is None and not self.has_power and self.exclude_type is None
                and not self.energy_cards):
            return True
        _, receiver = receiver_of_target(run, self.target)
        if receiver is None:
            return False
        if self.marker is not None and not has_marker(receiver, self.marker):
            return False  # v0.91（うらのカードにはマーカーがないので、おもてにしない）
        if self.has_power and not holds_power_now(run, receiver):
            return False  # v0.114
        if self.energy_cards and not E.attached_energy_cards(run.state, receiver):
            return False  # v0.115（ついているカードは場の公開の情報。うらのカードもおもてにせずに数える）
        if self.exclude_type is not None and not not_of_type(run, receiver, self.exclude_type):
            return False  # v0.115
        if self.color_filter is not None and not color_filter_hit(run, receiver, self.color_filter):
            return False
        return self.names is None or E.form_def(run.state, receiver).name_ja in self.names  # v0.49: 今の姿の名前（［へんしん］・「ばける」）

    def decides(self, kind: str) -> bool:
        # v0.35: 同じ段階の変更効果の計算の順番の決定（``DAMAGE_STEP_ORDER``）。並びの中にダメージの要素が 2 つ以上あっても、続きの情報の
        # ``element``（要素の位置）で区別する（``flow._resume_attack``）。v0.66: お上品攻撃の減らす量の決定（``DAMAGE_REDUCTION``）も。v0.119: 受けるポケモンの使うかを選ぶ
        # 効果（［シェルアーマー］）の決定（``DAMAGE_OPTION``）も
        return kind in (DAMAGE_STEP_ORDER, DAMAGE_REDUCTION, DAMAGE_OPTION)

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        if not self.has_target(run):
            return False  # v0.40: 名前の合わないポケモン（みんなでばくはつ）。ダメージの要素はなく、ログもない
        zero = False
        if self.requires is not None:
            discarded = run.fs.results.get(self.requires)
            if discarded is not None and discarded.outcome == LACKING_NONE:
                return False  # 「トラッシュできないとき、このワザのダメージはなくなる」（RUL-ENERGY-DISCARD-ATTACKS）
            zero = discarded is not None and discarded.outcome == LACKING_ZERO  # 「（トラッシュできない時、このワザのダメージは0になる）」
        coins = local_coins(self.base, run)
        # v0.33: 相手へのダメージの要素だけを決めるこの要素のコイン（ニドラン♂の「つのでつつく」。``coin_name`` のない ``local_gate``）も、受けるポケモンが
        # ダメージの要素を無効にする状態なら投げるかが決められない（v0.4b と同じ問い）。でんげき（自分へのダメージ）・コインが効果も決めるもの（``coin_name``）は変えない
        gate_only_damage = self.local_gate is not None and self.coin_name is None and self.target == OPP
        if coins or gate_only_damage:
            owner = 1 - run.player if self.target == OPP else run.player
            receiver = run.opponent_active() if self.target == OPP else run.attacker()
            from .kernel import first_void

            void = first_void(run.res, run.incoming(), owner, receiver)
            if void is not None:
                raise run.res.question("prevented_coin_damage", f"ポケモン {receiver.pokemon_id}",
                                       E.prevented_coin_damage_error(receiver.pokemon_id, void.implementation.kind))
        if self.local_gate is not None:
            gate_flips = run.flip(1)
            if self.coin_name is not None:
                run.fs.coins[self.coin_name] = gate_flips
            if gate_flips.results[0] is not self.local_gate:
                return False
        # v0.40: 相手プレイヤーが投げるコイン（``flipped_by_opponent``。ベンチをあやつる）
        flipper = 1 - run.player if getattr(self.base, "flipped_by_opponent", False) else None
        until_tails = getattr(self.base, "flip_until_tails", None)
        if until_tails is not None:
            flips = until_tails(run, self)  # v0.64: 「うら」が出るまで投げるコイン（れんぞくいしなげ）
        else:
            flips = run.flip(coins, by_heads=getattr(self.base, "by_heads", False), player=flipper) if coins else None
        if self.target == OPP and run.state.is_face_down(run.opponent_active()):
            # v0.67: うらのカード（マチスの秘策）は、ダメージを受ける時におもてにする。基本となるダメージ（受けるポケモンを読む値。「相手のエネルギーの数」など）を
            # 求める前におもてにする。「たねポケモン」でなくトラッシュしたら、このダメージの要素の対象はいない
            from .kernel import designate

            if designate(run.res, run.fs, 1 - run.player, run.opponent_active(), "damage") is None:
                run.fs.results[self.name] = E.DamageResult(OPP, 1 - run.player, run.opponent_active().pokemon_id, False, None, False, lost=True)
                return False
        if self.target == OPP and any(entry[4] is None for entry in run.res.group_powers) and run.fs.frame.kind is FrameKind.ATTACK:
            # v0.118: ワザといっしょに使った［XXXXX］のコイン（相手の対戦ポケモンへのダメージの要素で投げる）。v0.122: ［ANGER］のダメージカウンターもここで数える（コインより先）
            declared_power_amounts(run, self)
        value_for = getattr(self.base, "value_for", None)  # v0.115: 受けるポケモンごとの基本となるダメージ（サイコスプラッシュ）
        base = 0 if zero else (value_for(run, receiver_of_target(run, self.target)[1]) if value_for is not None else self.base.value(run, flips))
        return self._deal(run, base, {})

    def _deal(self, run: AttackRun, base: int, orders: dict[int, tuple[int, ...]], reduction: int | None = None, optional: bool | None = None) -> bool:
        """基本となるダメージ ``base`` を与える。同じ段階の変更効果の計算の順番によって結果が変わるなら、順番の決定を出して止まる（v0.35）。v0.66: お上品攻撃
        （5 段階で好きなだけ小さくしてよい）の減らす量がまだ決まっていなければ、減らす量の決定を出して止まる（``reduction`` は決めた量）。v0.119: 受けるポケモンの 8 段階の使うかを
        選ぶ効果（［シェルアーマー］）を使うかがまだ決まっていなければ、受けるポケモンの持ち主に決定を出して止まる（``optional`` は決めた答え）。"""
        try:
            run.fs.results[self.name] = deal_damage(run.res, run.fs, self.target, base, weakness_resistance=self.weakness_resistance,
                                                    orders=orders or None, order_decision=True, resistance=self.resistance,
                                                    defender_effects=self.defender_effects, reduction=reduction,
                                                    private_amount=getattr(self.base, "private", False), optional=optional, optional_decision=True)
        except DamageOrderRequired as need:
            suspend_step_order(run, self, need, base, orders, reduction, optional)
            return True
        except DamageReductionRequired as need:
            if run.res.dry_run:
                # 先読み: 選べる量のうち、計算の結果（最終ダメージと 2 段階で終えるか）が同じ量は 1 つにまとめて試す（そのあとの処理は計算の結果だけを使う）
                return self._deal(run, base, orders, run.res.oracle.choose(reduction_answers(run, self, base, orders, need)))
            suspend_damage_reduction(run, self, need, base, orders)
            return True
        except DamageOptionRequired as need:
            if run.res.dry_run:
                return self._deal(run, base, orders, reduction, run.res.oracle.choose([False, True]))  # v0.119: 先読みは使う・使わないの両方を試す
            suspend_damage_option(run, self, need, base, orders, reduction)
            return True
        return False

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        optional = None
        if decision.kind == DAMAGE_REDUCTION:
            base, orders, reduction = resume_damage_reduction(run, self, decision, choices)
        elif decision.kind == DAMAGE_OPTION:
            base, orders, reduction, optional = resume_damage_option(run, self, decision, choices)
        else:
            base, orders, reduction = resume_step_order(run, self, decision, choices)
            optional = carried_optional(run)
        self._deal(run, base, orders, reduction, optional)


@dataclass(frozen=True)
class StadiumSelfDamage(Damage):
    """クチバシティジムの「うら」の「ワザを使ったポケモン自身にも、そのワザのダメージとして、10ダメージ」（v0.57）。ワザによる自分へのダメージ（v0.2f。弱点・抵抗力・
    プラスパワー・ディフェンダー・「ダメージを受けない」状態を、ほかの自分へのダメージと同じに計算する）。ログ ``damage`` に ``stadium_card``。``with_stadium_self_damage``
    だけが並びに入れる。"""

    stadium: int = 0

    def _deal(self, run: AttackRun, base: int, orders: dict[int, tuple[int, ...]], reduction: int | None = None) -> bool:
        try:
            run.fs.results[self.name] = deal_damage(run.res, run.fs, self.target, base, weakness_resistance=self.weakness_resistance,
                                                    orders=orders or None, order_decision=True, resistance=self.resistance,
                                                    log_extra={"stadium_card": self.stadium})
        except DamageOrderRequired as need:
            suspend_step_order(run, self, need, base, orders)
            return True
        return False


def with_stadium_self_damage(program: tuple, stadium: int, amount: int) -> tuple:
    """クチバシティジムの「うら」の自分へのダメージの要素（``StadiumSelfDamage``）を入れた並び（v0.57）。入れる位置は、並びのダメージの要素の最後のあと（ダメージの
    要素がなければ最初の効果の要素の前。ダメージの処理はダメージ以外の効果より先。p.309）。宣言のときと決定のあとの再開で同じ並びを作る（要素の位置が同じ）。"""
    damage = [i for i, element in enumerate(program) if element.phase is Phase.DAMAGE]
    if damage:
        index = damage[-1] + 1
    else:
        index = next((i for i, element in enumerate(program) if element.phase is Phase.EFFECT), len(program))
    return program[:index] + (StadiumSelfDamage(SELF, Fixed(amount), name="stadium_self_damage", stadium=stadium),) + program[index:]


def program_may_fail(program: tuple) -> bool:
    """並びに、ワザを失敗させうる要素（コインで失敗する・条件で失敗する・トラッシュできなければ失敗する）があるか（v0.57。クチバシティジムの VM1）。"""
    # v0.93: 相手に控えがいないときの失敗（からめとる。``FailWithoutOpponentBench``）も数える
    # v0.100: 「スケッチ」（このカードが前の相手の番に場に出ていなければ失敗する。``UseLastOpponentAttack``）も数える
    # v0.113: ベンチに空きがないときの失敗（ヤミカラスの「なかまをよぶ」。``BenchFromDeck.when_full``）も数える
    return any(isinstance(element, (FailOnTails, FailUnlessOpponentStatus, FailWithoutOpponentBench, UseLastOpponentAttack))
               or (isinstance(element, DiscardOwnEnergy) and element.when_lacking == LACKING_FAIL)
               or (isinstance(element, BenchFromDeck) and element.when_full == BENCH_FULL_FAIL) for element in program)


def suspend_step_order(run: AttackRun, element: Element, need: DamageOrderRequired, base: int, orders: dict[int, tuple[int, ...]],
                       reduction: int | None = None, optional: bool | None = None) -> None:
    """同じ段階の変更効果の計算の順番によって結果が変わる（v0.35。``damage.DamageOrderRequired``）。``DAMAGE_STEP_CHOOSER`` のプレイヤー（2・5・6 段階は
    ワザを使うプレイヤー、7・8 段階はダメージを受けるポケモンの持ち主。p.321）に、順番の決定（``DAMAGE_STEP_ORDER``）を出して止まる。

    続きの情報に、決定を出した要素の位置（``element``）・基本となるダメージ（``base``。要素のコインを投げ直さない）・前に選んだ段階の順番（``orders``）・
    段階（``step``）・受けるポケモン（``target``・``receiver``）・その段階の変更効果（``modifiers``: (名前, 発生源, 計算, 数)。集めた順番）・選べる
    順番（``permutations``。``damage.step_orders``。決定の選べるもの i が permutations[i]）を書く。ダメージはまだ与えていない（受けるときの効果・
    「とうめい」は、順番を決めたあとの計算で評価する）。

    決定をまたいで運べるのは、ワザ全体のコインと枠の値（``AttackRun.suspend`` の ``carry``）だけなので、この要素より前の要素がダメージを与えて
    いる（``applied``・``evaded``）か、前の要素の結果をこの要素より後の要素が使う並びでは、決定を出せない（エンジンの未対応として v0.34 と同じ
    問い ``damage_step_order`` で止める。今の対応カードでは起こらない）。"""
    index = next((i for i, candidate in enumerate(run.program) if candidate is element), None)
    if index is None:
        raise RuntimeError("順番の決定を出すダメージの要素が、処理している要素の並びにない（エンジンの不具合）")
    if run.fs.applied or run.fs.evaded or _uncarried_results_used_later(run, element, index):
        raise run.res.question("damage_step_order", f"ポケモン {run.fs.frame.source_pid}・{need.step} 段階の効果 {[m.label for m in need.modifiers]}"
                                                     "（前の要素の結果を決定のあとに運べない）")
    target = element_target(run, element)
    owner, receiver = receiver_of_target(run, target)
    chooser = run.player if DAMAGE_STEP_CHOOSER[need.step] == "attacker" else owner
    permutations = step_orders(len(need.modifiers))
    described = tuple((m.label, m.source, m.operation, m.amount) for m in need.modifiers)
    # v0.45: 「抵抗力」の影響を受けないダメージ（スパイラルショット）だけ ``resistance`` を書く（v0.44 までの決定の形は変えない）
    resistance = (("resistance", False),) if getattr(element, "resistance", True) is False else ()
    # v0.66: お上品攻撃で決めた減らす量（6〜8 段階の順番の決定は減らす量のあと）。決めていなければ書かない（v0.65 までの決定の形は変えない）
    reduced = (("reduction", reduction),) if reduction is not None else ()
    # v0.119: 決めた使うかを選ぶ効果の答え（8 段階の順番の決定は使うかのあと）。決めていなければ書かない（v0.118 までの決定の形は変えない）
    reduced += (("optional", int(optional)),) if optional is not None else ()
    run.suspend(kind=DAMAGE_STEP_ORDER, player=chooser, options=tuple(range(len(permutations))),
                extra=(("element", index), ("base", base), ("orders", tuple(sorted(orders.items()))), ("step", need.step), ("target", target),
                       ("receiver", receiver.pokemon_id), ("weakness_resistance", getattr(element, "weakness_resistance", True)),
                       *resistance, *reduced, ("modifiers", described), ("permutations", permutations)),
                carry=True)


def _carry_check(run: AttackRun, element: Element, what: str) -> int:
    """決定を出すダメージの要素の位置（v0.66。``suspend_step_order`` と同じ確かめ: 前の要素がダメージを与えた並び・前の要素の結果を後の要素が使う並びでは、決定を
    またいで運べないので、エンジンの未対応として止める）。"""
    index = next((i for i, candidate in enumerate(run.program) if candidate is element), None)
    if index is None:
        raise RuntimeError(f"{what}の決定を出すダメージの要素が、処理している要素の並びにない（エンジンの不具合）")
    if run.fs.applied or run.fs.evaded or _uncarried_results_used_later(run, element, index):
        raise run.res.question("damage_reduction_decision", f"ポケモン {run.fs.frame.source_pid}・{what}（前の要素の結果を決定のあとに運べない）")
    return index


def _uncarried_results_used_later(run: AttackRun, element: Element, index: int) -> bool:
    """決定を出す要素（位置 ``index``）より前の要素の結果のうち、あとの要素が名前で読み、続きの情報で運ばないものがあるか（v0.35 の確かめ）。v0.89: 先に選んだ個体
    （``ChosenTarget``。v0.83 から ``chosen_targets`` で運ぶ）・色（``ChosenColor``。v0.88 から ``chosen_colors`` で運ぶ）は運ぶので数えない（v0.88 までは数えていて、
    選んだ相手の対戦ポケモンへのダメージ・ひかるライチュウの「サンダースコール」の相手の対戦ポケモンへのダメージが順番・お上品攻撃の決定を出せず、エンジンの未対応で止まっていた）。"""
    used_later = {value for later in run.program[index + 1:] for value in _result_names(later)}
    return any(name in used_later for name, value in run.fs.results.items()
               if name != getattr(element, "name", None) and not isinstance(value, (ChosenTarget, ChosenColor, ChosenOption)))  # v0.118: ChosenOption も運ぶ


def element_target(run: AttackRun, element: Element) -> str:
    """ダメージの要素の受けるポケモンの種類（``OPP``・``SELF``）。v0.89: 先に選んだ個体へのダメージ（``TargetDamage``）は、選んだ個体の今の場所で決める（``resolve_target``）。"""
    resolve = getattr(element, "resolve_target", None)
    return element.target if resolve is None else resolve(run)


def reduction_answers(run: AttackRun, element: Element, base: int, orders: dict[int, tuple[int, ...]], need) -> list[int]:
    """先読みで試す減らす量（v0.66）: 選べる量のうち、計算の結果（最終ダメージ・2 段階で終えるか・6〜8 段階の順番の決定の要否）が同じものは、いちばん小さい量だけ。
    減らす量のあとの処理（「とうめい」・ダメージを受けたときの効果・きぜつ・返すダメージ）は、計算の結果だけを使う（``kernel.deal_damage``）。"""
    from .kernel import attack_modifiers_of, compute_damage

    state = run.state
    target = element_target(run, element)
    _owner, receiver = receiver_of_target(run, target)
    attacker = run.attacker()
    modifiers = with_coin_modifiers(run, target, attack_modifiers_of(run.res, run.fs.frame, attacker, receiver, target))
    seen: dict = {}
    for amount in need.choices:
        try:
            calc = compute_damage(state, attacker, receiver, base, modifiers, weakness_resistance=element.weakness_resistance, orders=orders or None,
                                  resistance=element.resistance, reduction=amount)
            key = ("final", calc.final, calc.stopped_after_step_2, calc.nonpositive_alternative)
        except DamageOrderRequired as order:
            key = ("order", amount, order.step)  # 順番の決定が要る量は、まとめずに試す
        except DamageOptionRequired:
            key = ("option", amount)  # v0.119: 受けるポケモンの使うかを選ぶ効果の決定が要る量も、まとめずに試す
        seen.setdefault(key, amount)
    return list(seen.values())


def with_coin_modifiers(run: AttackRun, target: str, modifiers: list) -> list:
    from .kernel import with_stadium_coin

    return with_stadium_coin(run.res, run.fs.frame, target, modifiers)


def suspend_damage_reduction(run: AttackRun, element: Element, need, base: int, orders: dict[int, tuple[int, ...]]) -> None:
    """お上品攻撃の減らす量の決定（v0.66。``DAMAGE_REDUCTION``）を、ワザを使ったプレイヤーに出して止まる。続きの情報は順番の決定と同じ形（要素の位置・基本となる
    ダメージ（コインを投げ直さない）・前に選んだ段階の順番・受けるポケモン）と、5 段階の減らす前のダメージ（``value``）。ダメージはまだ与えていない。"""
    index = _carry_check(run, element, "お上品攻撃の減らす量")
    target = element_target(run, element)
    _owner, receiver = receiver_of_target(run, target)
    resistance = (("resistance", False),) if getattr(element, "resistance", True) is False else ()
    run.suspend(kind=DAMAGE_REDUCTION, player=run.player, options=tuple(need.choices),
                extra=(("element", index), ("base", base), ("orders", tuple(sorted(orders.items()))), ("target", target), ("receiver", receiver.pokemon_id),
                       ("weakness_resistance", getattr(element, "weakness_resistance", True)), *resistance, ("value", need.value),
                       ("reducers", tuple(m.source for m in need.modifiers))),
                carry=True)


def resume_damage_reduction(run: AttackRun, element: Element, decision: PendingDecision, choices: tuple[int, ...]) -> tuple[int, dict, int]:
    """減らす量の決定の答えのあと（v0.66）: 続きの情報の基本となるダメージ・段階の順番と、選んだ量を返す（コインを投げ直さない）。"""
    carried = run.carried
    if decision.kind != DAMAGE_REDUCTION or len(choices) != 1 or choices[0] not in decision.options:
        raise RuntimeError(f"減らす量の決定の答え {choices!r} が、選べる量ではない（エンジンの不具合）")
    _, receiver = receiver_of_target(run, element_target(run, element))
    if receiver.pokemon_id != carried["receiver"]:
        raise RuntimeError("減らす量の決定を待つ間に、ダメージを受けるポケモンが変わった（エンジンの不具合）")
    orders = {int(k): tuple(v) for k, v in carried.get("orders", ())}
    return carried["base"], orders, choices[0]


def suspend_damage_option(run: AttackRun, element: Element, need: DamageOptionRequired, base: int, orders: dict[int, tuple[int, ...]], reduction: int | None) -> None:
    """v0.119（docs/damage-reactions-poison-sleep-v0.119.md 3 章）: 受けるポケモンの 8 段階の使うかを選ぶ効果（［シェルアーマー］）の決定（``DAMAGE_OPTION``）を、受けるポケモンの持ち主に
    出して止まる。選べるものは受けるポケモンの番号 1 つ（1 個: 使う・0 個: 使わない）。続きの情報は順番の決定と同じ形（要素の位置・基本となるダメージ（コインを投げ直さない）・前に選んだ
    段階の順番・決めた減らす量・受けるポケモン）と、効果・8 段階の前のダメージ・使わないときの最終ダメージ。ダメージはまだ与えていない。前の要素がダメージを与えた並び・前の要素の
    結果をあとの要素が使う並びでは、決定をまたいで運べないので、エンジンの未対応として止める。"""
    index = next((i for i, candidate in enumerate(run.program) if candidate is element), None)
    if index is None:
        raise RuntimeError("使うかを選ぶ効果の決定を出すダメージの要素が、処理している要素の並びにない（エンジンの不具合）")
    if run.fs.applied or run.fs.evaded or _uncarried_results_used_later(run, element, index):
        raise run.res.question("damage_option_element", f"ポケモン {run.fs.frame.source_pid}（前の要素の結果を決定のあとに運べない）")
    target = element_target(run, element)
    owner, receiver = receiver_of_target(run, target)
    resistance = (("resistance", False),) if getattr(element, "resistance", True) is False else ()
    reduced = (("reduction", reduction),) if reduction is not None else ()
    run.suspend(kind=DAMAGE_OPTION, player=owner, options=(receiver.pokemon_id,), min_choices=0, max_choices=1,
                extra=(("element", index), ("base", base), ("orders", tuple(sorted(orders.items()))), ("target", target), ("receiver", receiver.pokemon_id),
                       ("weakness_resistance", getattr(element, "weakness_resistance", True)), *resistance, *reduced, *_option_extra(need)),
                carry=True)


def resume_damage_option(run: AttackRun, element: Element, decision: PendingDecision, choices: tuple[int, ...]) -> tuple[int, dict, int | None, bool]:
    """v0.119: 使うかを選ぶ効果の決定の答えのあと: 続きの情報の基本となるダメージ・段階の順番・減らす量と、使うか（1 個なら使う）を返す（コインを投げ直さない）。"""
    carried = run.carried
    if decision.kind != DAMAGE_OPTION or len(choices) > 1 or not set(choices) <= set(decision.options):
        raise RuntimeError(f"使うかを選ぶ効果の決定の答え {choices!r} が、選べるものではない（エンジンの不具合）")
    _, receiver = receiver_of_target(run, element_target(run, element))
    if receiver.pokemon_id != carried["receiver"]:
        raise RuntimeError("使うかを選ぶ効果の決定を待つ間に、ダメージを受けるポケモンが変わった（エンジンの不具合）")
    orders = {int(k): tuple(v) for k, v in carried.get("orders", ())}
    return carried["base"], orders, carried.get("reduction"), bool(choices)


def carried_optional(run: AttackRun) -> bool | None:
    """v0.119: 続きの情報で運んだ、使うかを選ぶ効果の答え（順番の決定の続き。決めていなければ None）。"""
    value = run.carried.get("optional")
    return None if value is None else bool(value)


def resume_step_order(run: AttackRun, element: Element, decision: PendingDecision, choices: tuple[int, ...]) -> tuple[int, dict[int, tuple[int, ...]]]:
    """順番の決定の答えのあと（v0.35）: 続きの情報の基本となるダメージと、選んだ順番を加えた段階の順番を返す（コインを投げ直さない。ダメージは
    呼ぶ側がもう一度計算して与える）。決定を待つ間に場は変わらないので、受けるポケモン・その段階の変更効果が続きの情報と違えばエンジンの不具合。"""
    carried = run.carried
    step = carried["step"]
    permutations = tuple(tuple(order) for order in carried["permutations"])
    if decision.kind != DAMAGE_STEP_ORDER or len(choices) != 1 or not 0 <= choices[0] < len(permutations):
        raise RuntimeError(f"順番の決定の答え {choices!r} が、選べる順番の番号ではない（エンジンの不具合）")
    owner, receiver = receiver_of_target(run, element_target(run, element))
    if receiver.pokemon_id != carried["receiver"]:
        raise RuntimeError("順番の決定を待つ間に、ダメージを受けるポケモンが変わった（エンジンの不具合）")
    orders = {int(k): tuple(v) for k, v in carried.get("orders", ())}
    orders[step] = permutations[choices[0]]
    return carried["base"], orders, carried.get("reduction")


def receiver_of_target(run: AttackRun, target: str) -> tuple[int, PokemonInPlay]:
    """ダメージの要素の ``target``（相手の対戦ポケモン・自分）の、受けるポケモンとその持ち主（v0.35。順番の決定の選ぶプレイヤー・続きの情報）。"""
    if target == OPP:
        return 1 - run.player, run.opponent_active()
    if target == SELF:
        return run.player, run.attacker()
    raise RuntimeError(f"順番の決定を出すダメージの要素の受けるポケモンの種類 {target!r} は未対応（エンジンの不具合）")


def _result_names(element: Element) -> set[str]:
    """要素（とその基本となるダメージの値）が、前の要素の結果として名前で読むもの（v0.35。``requires``・``after_damage``・``discard``・``mill``・
    ``source`` など、文字列の項目すべて。読まない文字列も含めて広めに数える）。"""
    found: set[str] = set()
    for holder in (element, getattr(element, "base", None)):
        if holder is None or not dataclasses.is_dataclass(holder):
            continue
        for field in dataclasses.fields(holder):
            value = getattr(holder, field.name)
            if isinstance(value, str):
                found.add(value)
    return found


def _read_names(elements) -> set[str]:
    """v0.114: 要素の並び（とその基本となるダメージの値）が、前の要素の結果として名前で読むもの。``_result_names`` から、要素自身が書く結果の名前の項目（``name``）を
    除いたもの（ESPの続きの情報で運べない結果を見つける確かめに使う。運ぶ値を決めるのは ``_result_names``）。"""
    found: set[str] = set()
    for element in elements:
        for holder in (element, getattr(element, "base", None)):
            if holder is None or not dataclasses.is_dataclass(holder):
                continue
            for field in dataclasses.fields(holder):
                value = getattr(holder, field.name)
                if isinstance(value, str) and not (holder is element and field.name == "name"):
                    found.add(value)
    return found


def local_coins(base: Any, run: AttackRun) -> int:
    """基本となるダメージ ``base`` が、ダメージの要素の中で投げるコインの枚数（v0.31 から、数が状態で決まるもの（``coin_count``）もある）。"""
    count = getattr(base, "coin_count", None)
    return count(run) if count is not None else base.local_coins


@dataclass(frozen=True)
class Status(Element):
    """特殊状態にする効果の要素。``local_coin`` はこの要素のコイン（どくばり）、``gate`` はワザ全体のコイン（ねばりつく）。

    - ``target``（v0.17b）: 対象。``OPP``（相手の対戦ポケモン。既定）か ``SELF``（ワザを使ったポケモン自身。p.320 の効果の (3)。R団のカビゴンの
      「たおれこむ」）。自分への効果も、効果を与える直前に「とうめい」を評価する（自分のワザでもはたらく。v0.9 の T8。R団のカビゴンは持たない）。
    - ``after_damage``（v0.17b）: 説明が「ダメージを与えた後、…」の効果で、その名前のダメージの要素の結果。そのダメージの要素がダメージを与え
      なかった（防いだ・「とうめい」で受けなかった・最終ダメージが 0）ときに効果を与えるかは原典で決まらない（「ダメージを与えた後」が順番か
      条件か。docs/rocket-snorlax-v0.17b.md の Z23）ので、推測せずに止める（先読みがすべての結果を試すので、宣言の前に止まる）。
    """

    condition: str
    gate: tuple | None = None
    local_coin: CoinSide | None = None
    reparalysis_check: bool = False
    target: str = OPP
    after_damage: str | None = None
    otherwise: str | None = None  # v0.34: この要素のコインが ``local_coin`` の面でないときの特殊状態（ドガースの「くさいガス」の「うら」のこんらん）
    poison_damage: int | None = None  # v0.34: 特殊などく（ニドキングの「どくどく」。どくのダメージの量。p.322「どく状態にかかるもの」）
    # v0.119: どくのダメージカウンターの数にかける数（ツボツボの「どくどくエキス」の 2。``state.Poison.multiplier``）。1 なら通常のどく（``poison_damage`` がなければ）
    poison_multiplier: int = 1
    # v0.45: 入れ替えの要素（``ForceSwitch``）の名前。入れ替えたとき（その結果があるとき）だけ、新しい相手の対戦ポケモンに与える（キョウのベトベターの「ベトベトハンド」）。
    # 入れ替えなかったら与えない（入れ替える前のポケモンに与えない）
    after_switch: str | None = None
    # v0.45: 自分の状態の確かめ（``SelfStatusCheck``）の名前。その結果が真のときだけ与える（キョウのアーボックの「ポイズンパワー」の「その場合、相手を「どく」状態にする」）
    if_result: str | None = None
    phase: ClassVar[Phase] = Phase.EFFECT

    @property
    def opponent_element(self) -> str | None:
        return self.condition if self.target == OPP else None

    @property
    def opponent_elements(self) -> tuple[str, ...]:
        if self.target != OPP:
            return ()
        return (self.condition,) if self.otherwise is None else (self.condition, self.otherwise)

    def coin_receiver(self) -> str | None:
        return "effect" if self.target == OPP else None

    def has_target(self, run: AttackRun) -> bool:
        """v0.41: 対象（相手の対戦ポケモン・自分）が、このワザの中で HP 以上になっていれば、処理の対象がない（p.309。ワザ全体のコインがダメージの要素のあとに
        あるワザ（「げんかくおんぱ」）で、コインを投げない）。対象がきぜつの判定で任意の効果（こんじょう）を使えるなら、効果を受けるかが決まらない（G37）ので、
        ここで問いにする（コインを投げないことで G37 を見落とさない）。"""
        if self.target == SELF:
            owner, target = run.player, run.attacker()
        else:
            owner, target = 1 - run.player, run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target, owner)
            return False
        return True

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        if self.if_result is not None and not run.fs.results[self.if_result]:
            return False  # v0.45: 条件が満たされない（「その場合」ではない）
        if self.after_switch is not None and self.after_switch not in run.fs.results:
            return False  # v0.45: 入れ替えなかった（入れ替える前の対戦ポケモンには与えない）
        if self.target == SELF:
            owner, target = run.player, run.attacker()
        else:
            owner, target = 1 - run.player, run.opponent_active()
        # v0.46: 対象が特殊状態にならない（カビゴンの［めんえき］。``effects.status_immunity``）なら、この要素の特殊状態はどれも防がれ、結果は変わらない。原典で決められ
        # ない場合の確かめのうち、防がれる特殊状態の結果だけを決めるもの（「ダメージを与えた後」（コインのないとき）・マヒの再付与・特殊などくの上書き）は聞かない
        # （不要な停止にしない）。コインは、効果の要素が無効なのではない（効果を受けて特殊状態にならない）ので、今までどおり投げる
        immune = target is not None and E.status_immunity(run.state, owner, target) is not None
        if self.after_damage is not None:
            result = run.fs.results[self.after_damage]
            if result.dealt <= 0 and not (immune and self.local_coin is None):
                raise run.res.question("effect_after_no_damage", f"ポケモン {result.pokemon_id}",
                                       E.effect_after_no_damage_error(str(run.key), result, self.condition))
        if run.knocked_out(target):
            run.ko_prevention_conflict(target, owner)
            return False
        if self.reparalysis_check and not immune:
            problem = paralysis_problem(run.state, owner, target)
            if problem is not None:
                raise run.res.question("reparalysis_recovery_turn", problem.code, error=problem)
        special = self.poison_damage is not None or self.poison_multiplier != 1
        if special and not immune:
            # v0.119: どくの性質は (受けるダメージ, ダメージカウンターの数にかける数)。かける数だけが違うどく（「どくどくエキス」の 2 倍）も、受けるダメージの違うどくと同じ問い
            current = target.conditions.poison
            wanted = (10 if self.poison_damage is None else self.poison_damage, self.poison_multiplier)
            differs = current is not None and (current.damage, current.multiplier) != wanted
            shown = ""
            if differs:
                shown = (f"どくのダメージ {current.damage} → {wanted[0]}" if (current.multiplier, wanted[1]) == (1, 1)
                         else f"どくのダメージ {current.damage}・かける数 {current.multiplier} → {wanted[0]}・{wanted[1]}")
            if target.pokemon_id in run.res.trainer_poisoned and differs:
                # v0.56（KG1）: このワザのダメージで、トレーナー「キョウ」の効果がどく状態にしたポケモンを、ワザの効果が受けるダメージの違うどく状態にする（キョウの
                # どくどくガス）。キョウの効果とワザの効果の順番が決まらない（ワザの効果が先なら p.322 の特殊などく → 通常のどく、キョウの効果が先なら v0.3a の 15）。
                # v0.3a の 15 の問い（TP3）より先に聞く
                raise run.res.question("trainer_poison_order", f"ポケモン {target.pokemon_id}（{shown}）")
            if differs:
                # v0.34: どく状態のポケモンが、どくのダメージの違う特殊などくを受ける（p.322 は特殊などく → 通常のどくの向きだけを書く。
                # v0.3a の 15。「とうめい」のコインより先に聞く。先読みがすべての結果を試すので、どちらでも宣言の前に止まる）
                raise run.res.question("special_poison_overwrite", f"ポケモン {target.pokemon_id}（{shown}）")
        if self.local_coin is not None:
            if run.fs.reception.get(target.pokemon_id) is False:
                final = run.fs.evaded.get(target.pokemon_id)
                raise run.res.question("evaded_effect_coin", f"ポケモン {target.pokemon_id}",
                                       None if final is None else E.evaded_effect_coin_error(target.pokemon_id, final))
            prevented_effect_coin(run, owner, target)  # v0.31: 「ワザをうけない」状態（バリアー）なら、効果だけを決めるコインを投げるか決まらない
            condition = self.condition
            if run.flip(1).results[0] is not self.local_coin:
                if self.otherwise is None:
                    return False
                condition = self.otherwise  # v0.34: 同じコインの「うら」の効果（投げ直さない）
        else:
            condition = self.condition
        if not reaches(run.res, run.fs, owner, target, condition):
            return False
        if condition == POISON and (self.poison_damage is not None or self.poison_multiplier != 1):
            poison(run.state, owner, target, effect=str(run.key), damage=10 if self.poison_damage is None else self.poison_damage, multiplier=self.poison_multiplier)
            return False
        APPLY_CONDITION[condition](run.state, owner, target, effect=str(run.key))
        return False


def prevented_effect_coin(run: AttackRun, owner: int, target: PokemonInPlay) -> None:
    """効果の要素のコインの前に、対象が効果の要素を無効にする状態（v0.31。バリアー）なら問い（HC3。コインはその効果だけを決めるので、投げるかが
    決められない。v0.4b の ``prevented_coin_damage`` と同じ形）。"""
    from .kernel import first_void

    void = first_void(run.res, run.incoming(), owner, target, Window.BEFORE_EFFECT)
    if void is not None:
        raise run.res.question("prevented_effect_coin", f"ポケモン {target.pokemon_id}（{void.implementation.kind}）")


def effect_coin_questions(run: AttackRun, owner: int, target: PokemonInPlay) -> None:
    """相手の対戦ポケモンへの効果だけを決めるこの要素のコインの前の問い（v0.76。v0.36 の ``OpponentAttackCheck`` の ``local_coin`` と同じ順番を関数にした）: 前の要素の
    「とうめい」で受けないと決まっていれば T19b（``evaded_effect_coin``）、効果の要素を無効にする状態（「ワザをうけない」。バリアー）なら HC3（``prevented_effect_coin``）。
    ダメージだけを防ぐ状態（「ダメージを受けない」）では効果は受けるので、止めずに投げる。"""
    if run.fs.reception.get(target.pokemon_id) is False:
        final = run.fs.evaded.get(target.pokemon_id)
        raise run.res.question("evaded_effect_coin", f"ポケモン {target.pokemon_id}",
                               None if final is None else E.evaded_effect_coin_error(target.pokemon_id, final))
    prevented_effect_coin(run, owner, target)


def _leave_prevented(run: AttackRun, owner: int, pokemon: PokemonInPlay, cause: str, coin: CoinSide | None) -> bool:
    """v0.93（docs/active-leave-locks-v0.93.md 4 章）: ワザの要素の、プレイヤー ``owner`` の ``pokemon`` をバトル場からはなれさせる部分の前（コイン・「とうめい」・決定の前）の確かめ。
    「バトル場をはなれられない」効果を受けていれば、その部分は起こらない（ログ ``leave_prevented``。ワザのほかの部分は書かれた順に続ける。p.309）。その部分だけを決めるこの要素の
    コイン（``coin``）があれば、投げるかが決まらない（AL2。問い ``leave_locked_coin``）。止めなければ真を返す（呼ぶ側はこの部分を処理しない）。"""
    lock = leave_lock(run.state, owner, pokemon)
    if lock is None:
        return False
    if coin is not None:
        raise run.res.question("leave_locked_coin", f"ポケモン {pokemon.pokemon_id}（ワザ {run.key} の、はなれさせる部分だけを決めるコイン）")
    E.note_leave_prevented(run.state, owner, pokemon, lock, cause, effect=str(run.key))
    return True


@dataclass(frozen=True)
class ForceSwitch(Element):
    """相手の対戦ポケモンをベンチにもどし、相手が選んだ控えと入れ替える（ふきとばし。v0.13 の ``DamageAndForceSwitch`` と同じ結果・ログ）。"""

    chooser: str = "opponent"  # v0.31: 選ぶのは相手（ふきとばし）か、ワザを使ったプレイヤー（"attacker"。キュウコンの「かどわかす」）
    # v0.38: この要素のコイン（アーボックの「いかくこうげき」は「おもて」で入れ替える）。入れ替えの対象がいない（HP 以上・控えがいない）なら投げない
    # （p.309）。「とうめい」で受けないと決まった相手・「ワザをうけない」相手には、効果だけを決めるコインなので投げるかが決められない（T19b・HC3）
    local_coin: CoinSide | None = None
    # v0.40: 説明に「相手に控えがいない時、このワザは使えない」がある（わるいゴーリキーの「ひきずりだす」・エリカのウツドンの「さそってとかす」。ワザを使うための
    # 条件は実装の ``usage_problem``。相手のワザとして使うときは ``copy_problem``）。ここに控えがいないまま来たら、使うための条件の確認の漏れ
    required: bool = False
    # v0.40: 決定をまたいで枠の値（「とうめい」の結果など。``AttackRun.suspend`` の ``carry``）を運ぶ。入れ替えのあとにダメージの要素があるワザ（ひきずりだす）は、
    # 入れ替えの効果で評価した「とうめい」の結果（T4。1 つのワザで 1 匹 1 回）を、新しい対戦ポケモンへのダメージの判定（T27）で使う。v0.39 までのワザは運ばない
    # （決定の形を変えない）
    carry: bool = False
    # v0.45: 入れ替えたら、結果（入れ替えて出た控えポケモンの番号）をこの名前で残す（キョウのベトベターの「ベトベトハンド」の「その後、新しい相手の対戦ポケモンを…」。
    # ``Status.after_switch``）。入れ替えなかった（控えがいない・コインが「うら」・受けない）ときは残さない
    name: str = "switch"
    # v0.72: 「ダメージを与えた後、相手の対戦ポケモンを控えポケモンと入れ替える」（タケシのサイホーン（GD1-012）の「つのでなげる」）のもとのダメージの要素。そのダメージの要素が
    # ダメージを与えなかったら Z23（v0.17b の ``Status.after_damage``・v0.42 の ``SelfSwitch.after_damage`` と同じ問い）。入れ替えの対象がない（相手が HP 以上・控えが
    # いない）ときは、どちらの読み方でも入れ替えないので聞かない
    after_damage: str | None = None
    # v0.94（docs/switch-return-attacks-v0.94.md 7 章）: 「のぞむなら、…入れ替えてよい」（ロコンの「きつねび」）。選ぶプレイヤーが 0〜1 匹を選ぶ（選ばなければ入れ替えない。
    # ログ ``forced_switch_declined``）。必須の入れ替え（1 匹）の決定の意味は変えない
    optional: bool = False
    # v0.94（6 章・8 章）: ワザ全体のコインの面（ケンタロスの「ふんだりけったり」・わるいドンファンの「すくいなげ」の「うら」）。コインの前の確かめは ``has_target``・
    # ``leave_blocked``・``coin_receiver``。この要素のコイン（``local_coin``）とは別
    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = FORCED_SWITCH
    opponent_element: ClassVar[str] = E.FORCED_SWITCH_ELEMENT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        if self.required and not run.state.players[1 - run.player].bench:
            return (ILLEGAL if clause in (CANNOT_USE, FOLLOW_TEXT) else UNRESOLVED), "相手に控えポケモンがいない（ワザを使うための条件）"
        return None

    def coin_receiver(self) -> str | None:
        return "effect"  # v0.94: 相手の対戦ポケモンへの効果（ワザ全体のコインの面 ``gate`` で決まるときの ``void_coin_question``）

    def has_target(self, run: AttackRun) -> bool:
        """v0.94: ワザ全体のコインが決める入れ替えの対象があるか（相手の対戦ポケモンがこのワザで HP 以上でなく、相手に控えがいる。p.309）。こんじょうを使えるなら G37
        （``Status.has_target`` と同じ）。"""
        target = run.opponent_active()
        if target is None:
            return False
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        return bool(run.state.players[1 - run.player].bench)

    def leave_blocked(self, run: AttackRun) -> bool:
        target = run.opponent_active()
        return target is not None and leave_lock(run.state, 1 - run.player, target) is not None

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        opponent = 1 - run.player
        p = run.state.players[opponent]
        target = p.active
        if self.required and not p.bench:
            raise RuntimeError(f"相手に控えポケモンがいないのに、ワザ {run.key} の入れ替えに来た（使うための条件の確認の漏れ。エンジンの不具合）")
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            self._skip(run, target, E.TARGET_KNOCKED_OUT)
            return False
        if not p.bench:
            self._skip(run, target, E.NO_BENCH)
            return False
        if self.after_damage is not None:
            result = run.fs.results[self.after_damage]
            if result.dealt <= 0:
                raise run.res.question("effect_after_no_damage", f"ポケモン {result.pokemon_id}",
                                       E.effect_after_no_damage_error(str(run.key), result, None, what="相手の対戦ポケモンを控えポケモンと入れ替える"))
        if _leave_prevented(run, opponent, target, E.LEAVE_FORCED_SWITCH, self.local_coin):
            return False  # v0.93: 「バトル場をはなれられない」相手は入れ替えない（決定を出さない。``Status.after_switch`` の結果も残さない）
        if self.local_coin is not None:
            if run.fs.reception.get(target.pokemon_id) is False:
                final = run.fs.evaded.get(target.pokemon_id)
                raise run.res.question("evaded_effect_coin", f"ポケモン {target.pokemon_id}",
                                       None if final is None else E.evaded_effect_coin_error(target.pokemon_id, final))
            prevented_effect_coin(run, opponent, target)
            if run.flip(1).results[0] is not self.local_coin:
                return False
        if not reaches(run.res, run.fs, opponent, target, E.FORCED_SWITCH_ELEMENT):
            return False
        chooser = run.player if self.chooser == "attacker" else opponent
        options = tuple(pokemon.pokemon_id for pokemon in p.bench)
        extra: tuple = (("target", target.pokemon_id),)
        changes = self._form_changes(run, options)
        if changes:
            # v0.94（RX1。docs/switch-return-attacks-v0.94.md 7 章）: 入れ替えるとワザを使っている［へんしん］のメタモンの今の姿が変わる控えは、選べるが選ぶと止める（v0.65 の
            # ワザの途中の入れ替えと同じ問い）。必須の入れ替えで選べるどの控えもそうなら、決定を出す前に止める（先読みが宣言の前に見つける）。任意の入れ替えは入れ替えない答えが残る
            if len(changes) == len(options) and not self.optional:
                raise run.res.question("attack_switch_transformed_attacker", f"控えのポケモン {list(changes)}（選べるどのポケモンも）")
            extra += _unresolved_extra(changes, E.REACTIVE_SWITCH_TRANSFORM_CODE, E.REACTIVE_SWITCH_TRANSFORM_REASON)
        run.suspend(kind=FORCED_SWITCH, player=chooser, options=list(options), extra=extra, carry=self.carry, min_choices=0 if self.optional else 1)
        if self.optional and not run.res.dry_run:
            _mark_branch_questions(run, tuple(option for option in options if option not in changes))
        return True

    def _form_changes(self, run: AttackRun, options: tuple[int, ...]) -> tuple[int, ...]:
        """v0.94（RX1）: 入れ替えのあとにダメージの要素があるワザ（ひきずりだす・きつねび）で、入れ替えるとワザを使っている［へんしん］のメタモンの今の姿（相手の対戦ポケモンの
        カード）が変わる控え（あとのダメージを、どの姿のタイプで計算するかが決まらない）。あとにダメージの要素がない（ふきとばし・こうそくスピン）なら、姿が変わっても残りの処理の
        結果は変わらないので聞かない（状態を変えない）。"""
        if not any(element.phase is Phase.DAMAGE for element in run.program[run.index + 1:]):
            return ()
        if E.transform_defender(run.state, run.attacker()) is None:
            return ()
        # 相手のうらのカード（マチスの秘策）は、本当のカードによらず止める選択にする（選ぶのがワザを使ったプレイヤーでも、正体で選べるものが変わらない。入れ替えでおもてにしない）
        return tuple(option for option in options
                     if run.state.is_face_down(run.state.find_pokemon(option)[1]) or _switch_changes_attacker(run, 1 - run.player, option))

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        if self.optional:
            # v0.94: 任意の入れ替えは、宣言の前の先読みでは入れ替えない答えだけを試す。入れ替える控えのそれぞれの続きは、実際の処理で決定を出すときに試し、問いに当たる控えを
            # 選ぶと止める選択にする（``_mark_branch_questions``。選ばなかった枝の問いで、入れ替えない答えまで宣言の前に止めない）
            return [()]
        blocked = set(decision.context_value("unresolved_choices", ()))  # v0.94: 選ぶと止める控え（RX1）は試さない（答えのときに止める）
        return [answer for answer in all_answers(decision) if not blocked & set(answer)]

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        opponent = 1 - run.player
        p = run.state.players[opponent]
        old = p.active
        target = run.carried.get("target")
        if old is None or old.pokemon_id != target:
            raise RuntimeError(f"入れ替えの対象 {target} が相手のバトル場にいない（エンジンの不具合）")
        if not choices:
            if not self.optional:
                raise RuntimeError(f"入れ替えるワザ {run.key} で入れ替えるポケモンを選ばなかった（エンジンの不具合）")
            # v0.94: 任意の入れ替えで入れ替えなかった（移動・反応・持続する効果の消去は起こらない。``Status.after_switch`` の結果も残さない）
            run.state.add_event("forced_switch_declined", player=opponent, attacker=run.player, attacker_pokemon_id=run.fs.frame.source_pid, effect=str(run.key),
                                pokemon=old.card, pokemon_id=old.pokemon_id)
            return
        # v0.121: 入れ替えの共通の部分を ``swap_opponent_active`` に分けた（ぶきみなとおぼえと共通。ログ・処理の順番は v0.120 と同じ）
        swap_opponent_active(run, opponent, old, choices[0], chosen_by="attacker" if self.chooser == "attacker" else None)
        run.fs.results[self.name] = p.active.pokemon_id  # v0.45: 入れ替えて出た控えポケモン

    @staticmethod
    def _skip(run: AttackRun, target: PokemonInPlay, reason: str) -> None:
        run.state.add_event(
            "forced_switch_skipped",
            player=1 - run.player,
            attacker=run.player,
            attacker_pokemon_id=run.fs.frame.source_pid,
            effect=str(run.key),
            pokemon=target.card,
            pokemon_id=target.pokemon_id,
            reason=reason,
        )


def _mark_branch_questions(run: AttackRun, options: tuple[int, ...]) -> None:
    """v0.94（docs/switch-return-attacks-v0.94.md 7 章）: 任意の決定（ロコンの「きつねび」の入れ替え）を出したあと、選べる ``options`` のそれぞれを答えたときの続き（きぜつの判定まで。
    コインと決定のすべての結果）を、状態の複製の上で先読みする（``preflight.explore``。答えのあとには先読みしないので、ここで試す）。問いに当たる選択は、選べるが選ぶと止める選択
    （``unresolved_choices``・``unresolved_detail``。選択ごとのコードと理由）にする。上限を超えたら、確かめられないのでエンジンの未対応として選ぶと止める。答えのあとの処理は乱数の
    結果によらず、試した結果のどれかで止まる選択を選ばせない（黙って解決しない）。状態の決定を書きかえるだけで、ログ・乱数は変えない。"""
    from . import flow
    from .preflight import BranchLimit, explore

    state = run.state
    found: list[tuple[int, str, str]] = []
    for option in options:
        def body(res: Resolution, option: int = option) -> None:
            decision = res.state.decision
            res.state.decision = None
            flow._resume_attack(res, decision, codec.decode(decision), (option,))

        try:
            questions, _ = explore(state, body, run.res.catalog)
        except BranchLimit:
            found.append((option, "UNSUPPORTED_PREFLIGHT_LIMIT", f"この控えと入れ替えたあとの先読みで試す結果の数が上限を超えた（確かめられないので扱わない。ワザ {run.key}）"))
            continue
        if questions:
            key = pick(questions)
            error = to_error(key, questions[key].detail, questions[key].error)
            found.append((option, error.code, error.message))
    if not found:
        return
    decision = state.decision
    old = tuple(decision.context_value("unresolved_choices", ()))
    detail = tuple(decision.context_value("unresolved_detail", ())) or tuple(
        (choice, decision.context_value("unresolved_code"), decision.context_value("unresolved_reason")) for choice in old)
    detail = tuple(sorted(detail + tuple(found)))
    context = tuple(item for item in decision.context if item[0] not in ("unresolved_choices", "unresolved_code", "unresolved_reason", "unresolved_detail"))
    context += (("unresolved_choices", tuple(item[0] for item in detail)), ("unresolved_code", detail[0][1]), ("unresolved_reason", detail[0][2]),
                ("unresolved_detail", detail))
    state.decision = dataclasses.replace(decision, context=context)


@dataclass(frozen=True)
class Drain(Element):
    """相手にダメージを与えたら、自分のダメージカウンターをとりのぞく（メガドレイン・やどりぎのタネ）。``counters`` が None なら与えた
    ダメージの半分（カウンターの単位で切り上げ）。v0.32: ``full`` なら与えたぶん（与えたダメージ ÷ 10 個。きゅうけつ）。どれも、のっている数まで。"""

    source: str
    counters: int | None = None
    full: bool = False
    # v0.72: 「取りのぞいてよい」（ゴルバット（ES1-009）・パラセクト（ES1-011）の「きゅうけつ」）。取りのぞくカウンターがあれば、取りのぞくかをワザを使ったプレイヤーが選ぶ
    # （決定 ``OPTIONAL_DRAIN``。0 個なら取りのぞかない（ログ ``drain_heal_declined``）。与えたぶんの一部だけを取りのぞく答えはない）
    optional: bool = False
    # v0.105（docs/recovery-evolution-coin-branches-v0.105.md 5 章）: とりのぞく前に「とうめい」などを評価する（``reaches`` の ``heal``。v0.104 の ``HealCounters`` と同じ。とりのぞく数が
    # 0 なら評価しない）。受けなければとりのぞかない（ログ ``drain_heal`` を残さない。判定のログは ``reaches``）。ハイパーリバース・サイコリーフ。v0.104 までの登録（メガドレイン・
    # やどりぎのタネ・きゅうけつ）は評価しないまま（False。v0.104 の docs 9 章の差は変えない）
    reach: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT

    def decides(self, kind: str) -> bool:
        return self.optional and kind == OPTIONAL_DRAIN

    def run(self, run: AttackRun) -> bool:
        state = run.state
        result = run.fs.results[self.source]
        if result.dealt <= 0:
            return False
        attacker = run.attacker()
        if run.knocked_out(attacker):
            state.add_event("drain_heal_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            dealt=result.dealt, reason=E.COUNTERATTACK_TARGET_KNOCKED_OUT)
            return False
        per = state.rules.damage_per_counter
        if self.counters is None:
            if result.dealt % per:
                raise RuntimeError(f"与えたダメージ {result.dealt} がダメージカウンターの単位の倍数ではない（エンジンの不具合）")
            counters = result.dealt // per if self.full else (result.dealt // per + 1) // 2
        else:
            counters = self.counters
        if self.optional and attacker.damage // per > 0:
            run.suspend(kind=OPTIONAL_DRAIN, player=run.player, options=(attacker.pokemon_id,), min_choices=0, max_choices=1, carry=True,
                        extra=(("dealt", result.dealt), ("counters", counters)))
            return True
        self._remove(run, attacker, result.dealt, counters)
        return False

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        attacker = run.attacker()
        dealt, counters = run.carried["dealt"], run.carried["counters"]
        if choices:
            if choices != (attacker.pokemon_id,):
                raise RuntimeError(f"取りのぞくポケモン {choices} が、ワザを使ったポケモンではない（エンジンの不具合）")
            self._remove(run, attacker, dealt, counters)
        else:
            run.state.add_event("drain_heal_declined", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                dealt=dealt, drain_counters=counters)

    def _remove(self, run: AttackRun, attacker: PokemonInPlay, dealt: int, counters: int) -> None:
        state = run.state
        per = state.rules.damage_per_counter
        before = attacker.damage
        removed = min(counters, before // per)
        if self.reach and removed > 0 and not reaches(run.res, run.fs, run.player, attacker, E.HEAL_ELEMENT):
            return
        attacker.damage = before - removed * per
        state.add_event("drain_heal", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                        dealt=dealt, drain_counters=counters, counters=removed, amount=removed * per, damage_before=before,
                        total_damage=attacker.damage)


def effect_attack_card_of(run: AttackRun, attacker: PokemonInPlay) -> str | None:
    """持続する効果を与えるワザを印刷したカードの id（v0.49。効果の ``attack_card``）。ワザの出どころがワザを使ったポケモンのいちばん上のカードと同じカードの id なら
    None（v0.48 までの効果と同じ形）。違う（［へんしん］・「ばける」・［サイコリンク］・「思い出させる」）ときだけ、そのカードの id。"""
    return None if run.key.card_id == run.state.cards[attacker.card].card_id else run.key.card_id


@dataclass(frozen=True)
class SelfRetaliation(Element):
    """自分に「次の相手の番、相手のワザのダメージを受けたら返す」持続する効果（ほのおのかべ: ``amount``、こうらがえし: None = 受けたダメージ）。"""

    amount: int | None
    multiplier: int = 1  # v0.45: 受けたダメージの何倍を返すか（クロスカウンターは 2）
    on_heads: bool = False  # v0.45: はたらくときにコインを投げ、「おもて」のときだけ返す（クロスカウンター。``kernel.attack_damage_to_damage_source``）
    phase: ClassVar[Phase] = Phase.EFFECT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        # v0.31: この持続する効果は、効果を与えたワザを、効果を持つポケモンのカードのワザの位置（``attack_index``）で持つ。相手のワザを自分のワザと
        # して使ったときの効果は、その位置で表せない（書き出しの形を変えずには持てない）ので、エンジンの未対応として選べない
        return UNSUPPORTED, "番をまたぐ効果を、効果を持つポケモンのカードのワザの位置で記録するので、相手のワザとして使った効果を表せない"

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        basis = RETALIATION_FIXED if self.amount is not None else RETALIATION_RECEIVED
        effect = Retaliation(source_card=attacker.card, source_player=run.player, created_turn=run.state.turn_number,
                             active_turn=run.state.turn_number + 1, attack_index=run.key.attack_index, amount=self.amount, basis=basis,
                             multiplier=self.multiplier, on_heads=self.on_heads, attack_card=effect_attack_card_of(run, attacker))
        if run.knocked_out(attacker):
            run.state.add_event("persistent_effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                persistent_effect=effect.kind, effect=str(run.key), reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        add_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key))
        return False


@dataclass(frozen=True)
class SelfPreventDamage(Element):
    """コインが「おもて」なら、次の相手の番、自分はダメージを受けない（かたまる・からにこもる）。"""

    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.flip(1).results[0] is HEADS:
            effect = PreventDamage(source_card=attacker.card, source_player=run.player, created_turn=run.state.turn_number,
                                   active_turn=run.state.turn_number + 1)
            add_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key))
        return False


@dataclass(frozen=True)
class SelfNextTurnAttackDamage(Element):
    """次の自分の番、自分の ``target_attack_index`` 番目のワザのダメージを、p.321 の 2 段階で ``amount`` にする持続する効果（v0.27。
    ストライクの「つるぎのまい」。効果を与えるだけで、ダメージは ``effects.attack_damage_modifiers`` が計算するときに変わる）。

    ダメージの要素のないワザなので、この要素の前にワザを使ったポケモンがダメージを受けることはない（相手の「はんげき」・返す効果は
    はたらかない）。コインも決定もない。
    """

    target_attack_index: int
    amount: int
    operation: str = NEXT_TURN_SET  # v0.35: ``NEXT_TURN_MULTIPLY`` なら「数をかける」（「きあいだめ」の 2 倍。``amount`` はかける数）
    includes_self_damage: bool = False  # v0.35: そのワザの自分へのダメージにも（マチスのラッタの「(自分へのダメージも2倍)」）
    # v0.76: ワザ全体のコインの面（ワンリキーの「きあいいっぱつ」は、同じ 1 枚のコインの「おもて」で与え、「うら」で ``SelfAttackLock`` を与える）。None ならいつも与える
    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        # v0.31: この持続する効果は、効果を与えたワザを、効果を持つポケモンのカードのワザの位置（``attack_index``）で持つ。相手のワザを自分のワザと
        # して使ったときの効果は、その位置で表せない（書き出しの形を変えずには持てない）ので、エンジンの未対応として選べない
        return UNSUPPORTED, "番をまたぐ効果を、効果を持つポケモンのカードのワザの位置で記録するので、相手のワザとして使った効果を表せない"

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        attacker = run.attacker()
        turn = run.state.turn_number
        effect = NextTurnAttackDamage(source_card=attacker.card, source_player=run.player, created_turn=turn,
                                      active_turn=turn + NextTurnAttackDamage.turns_until_active, attack_index=run.key.attack_index,
                                      target_attack_index=self.target_attack_index, amount=self.amount, operation=self.operation,
                                      includes_self_damage=self.includes_self_damage, attack_card=effect_attack_card_of(run, attacker))
        add_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key))
        return False


# v0.31: トラッシュできない（ついているエネルギーカードが足りない）ときの扱い（``DiscardOwnEnergy.when_lacking``）
LACKING_ERROR = "error"  # 今の対応カードでは起こらない（ワザに必要なエネルギーが足りているので）。起こったらエンジンの不具合
LACKING_FAIL = "fail"  # このワザは失敗する（カツラのリザードの「やきはらう」）
LACKING_ZERO = "zero"  # このワザのダメージは 0 になる（わるいリザードの「ファイヤーボール」など）
LACKING_NONE = "none"  # このワザのダメージ（効果）はなくなる（RUL-ENERGY-DISCARD-ATTACKS の最新の説明・じこさいせいの K3）
LACKING_CONDITION = "condition"  # 印刷の文面が「はがしてすてる」の形（ワザを使うための条件か効果かが決められない。HC1）
LACKING_CANNOT_USE = "cannot_use"  # 説明が「…トラッシュしなければ（はがしてすてなければ）、このワザは使えない」と書いている
# v0.79: トラッシュできない（選べるカードがない）なら、処理の対象がないので何もしない（p.309。それまでの要素（ダメージ）はそのまま。カツラのヒトカゲ（GD5-001）の
# 「ファイヤーテール」の「コインを投げて「うら」なら、自分についている「炎」エネルギーカードを1枚選び、トラッシュする。」。説明はトラッシュできないときを書かない）。
# この要素のコインは、選べるカードがなければ投げない（コインが決めるのはこのトラッシュだけ）
LACKING_SKIP = "skip"

# v0.31: トラッシュの時点（``DiscardOwnEnergy.timing``）
TIMING_EFFECT = "effect"  # ワザの効果（こんらんのコインのあと。説明がワザの効果として書かれている・RUL-ENERGY-DISCARD-ATTACKS）
TIMING_UNRESOLVED = "unresolved"  # ワザを使うための条件か効果かが決められない（こんらん状態で使うときは宣言のあとに止める。HC1）


@dataclass(frozen=True)
class Discarded:
    """トラッシュの要素の結果（v0.31）: トラッシュしたカード（ついている順）と、``outcome``（``"done"``・トラッシュできなかったときの扱い）。"""

    cards: tuple[int, ...]
    outcome: str = "done"


@dataclass(frozen=True)
class DiscardOwnEnergy(Element):
    """ワザを使ったポケモン自身についている ``energy_type`` のエネルギーカード（None ならどのエネルギーカードでも）をトラッシュする（じこさいせい（v0.7）と、
    v0.30 のエネルギーをトラッシュしてダメージを与えるワザ（ひのこ・かえんほうしゃ）で共通。v0.29 までの ``DiscardEnergyHealAll`` のトラッシュの部分。
    決定・選べるもの・ログ ``discard_energy`` は同じ）。

    v0.31 から、トラッシュする数（``count``。None ならついているものをすべて（決定なし）。``heads_of`` ならそのコインの「おもて」の数。``any_number``
    なら好きなだけ（0 枚は決められない。HC5））・ワザ全体のコインの面（``gate``）・この要素のコイン（``local_coin``。その面ならトラッシュする）・
    トラッシュできないときの扱い（``when_lacking``）・トラッシュの時点（``timing``）を持つ。選ぶのはワザを使ったプレイヤー（1 枚しかなくても決定を出す。
    K2）。選んだカードは、選んだ順ではなく、ついている順にトラッシュする（選んだ順番で結果が変わらないので、先読みは組み合わせだけを試す）。

    選べるものは ``effects.attached_basic_energy``（ついている順。``energy_type`` が None ならついているエネルギーカードすべて）。トラッシュできない
    場合は、v0.30 までのワザでは起こらない（ワザに必要なエネルギーに ``energy_type`` があるので）。v0.31 の相手のワザを自分のワザとして使う効果では
    起こりうるので、``when_lacking`` で扱う。
    """

    energy_type: EnergyType | None
    count: int | None = 1
    heads_of: str | None = None
    any_number: bool = False
    # v0.117: トラッシュする数はそのコインの「うら」の数（コインの枚数 −「おもて」の数。エンテイの「メガフレイム」）。``heads_of`` と同じく、投げなかったコインは 0
    tails_of: str | None = None
    gate: tuple | None = None
    local_coin: CoinSide | None = None
    name: str = "discard"
    when_lacking: str = LACKING_ERROR
    timing: str = TIMING_EFFECT
    copy_need: int | None = None  # 相手のワザとして使うときに必要な枚数（``heads_of`` のときのいちばん多い数。None なら ``count``）
    deck_limit: bool = False  # ``any_number``: 選べる数は相手の山札の枚数まで（ファイヤーの「やまやき」。多ければ HC6）
    # v0.45: トラッシュする数は「このワザに必要なエネルギーよりも多い ``energy_type`` のエネルギー」すべて（カツラのリザードンの「ファイヤーブレス」）。ついている
    # ``energy_type`` の基本エネルギーカードの枚数から、ワザに必要なエネルギーの ``energy_type`` の数を引いたもの（0 より少なければ 0。そのときはトラッシュせず、決定も
    # 出さない）。どのカードかはワザを使ったプレイヤーが選ぶ（その数ちょうど）
    excess_over_cost: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = DISCARD_ENERGY

    def decides(self, kind: str) -> bool:
        # v0.82: ついているものをすべてトラッシュする（``count`` が None。決定なし）要素は決定を出さない（ファイヤーの「ハイパーフレイム」は、「おもて」の 1 枚を選ぶ要素と
        # 「うら」のすべての要素が並ぶ。再開する要素を決定の種類で探すときに、決定を出す要素だけを数える）
        if self.count is None and self.heads_of is None and self.tails_of is None and not self.any_number and not self.excess_over_cost:
            return False
        return super().decides(kind)

    def _candidates(self, run: AttackRun, pokemon: PokemonInPlay | None = None) -> list[int]:
        pokemon = run.attacker() if pokemon is None else pokemon
        if self.energy_type is None:
            return [uid for uid in pokemon.energy if run.state.card_def(uid).category == "energy"]
        transform_energy_question(run, pokemon, self.energy_type, cards=True)  # v0.49: TE1（トラッシュするカードの選べるもの）
        return E.attached_basic_energy(run.state, pokemon, self.energy_type)

    def _needed(self, run: AttackRun) -> int | None:
        if self.excess_over_cost:
            required = sum(1 for cost in run.attack.cost if cost is self.energy_type)
            return max(0, len(self._candidates(run)) - required)
        if self.heads_of is not None:
            return run.heads(self.heads_of)
        if self.tails_of is not None:
            coins = run.fs.coins[self.tails_of]
            return len(coins.results) - coins.heads
        return self.count

    def on_declare(self, res: Resolution, player: int, attacker: PokemonInPlay) -> None:
        if self.timing == TIMING_UNRESOLVED and attacker.conditions.confused:
            raise res.question("discard_energy_timing", f"ポケモン {attacker.pokemon_id}")
        if self.timing == TIMING_UNRESOLVED and E.baby_rule_applies(res.state, player):
            # v0.114: 相手のバトル場のベイビィポケモンのルールのコイン（宣言のあと・説明の処理の前）。トラッシュがワザを使うための条件（宣言のとき）か効果（コインのあと）かで、
            # 「うら」でトラッシュするかが変わる（HC1 と同じ問い。CR-BABY-RULE-COIN-STEP の notes の「トラッシュしないと使えない」とベイビィのコインの前後）
            raise res.question("discard_energy_timing", f"ポケモン {attacker.pokemon_id}（相手のバトル場のベイビィポケモンのルールのコイン）")

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        need = self.copy_need if self.copy_need is not None else (1 if self.any_number else self.count)
        if need is None or len(self._candidates(run, copier)) >= need:
            return None
        what = f"{'エネルギー' if self.energy_type is None else '「' + self.energy_type.ja + '」エネルギー'}カードが {need} 枚ない"
        if self.when_lacking == LACKING_CANNOT_USE:
            # 使うワザの説明が「…しなければ、このワザは使えない」。説明にしたがう（ピッピ）・条件がたりなければ使えない（ピクシー）なら選べない
            return (ILLEGAL, what) if clause in (CANNOT_USE, FOLLOW_TEXT) else (UNRESOLVED, f"{what}（ワザを使うための条件）")
        if self.when_lacking == LACKING_CONDITION:
            # 「はがしてすてる」が条件か効果か決められない（HC1）ので、ピッピ（説明にしたがう）でも決められない
            return (ILLEGAL, what) if clause == CANNOT_USE else (UNRESOLVED, f"{what}（ワザを使うための条件か効果か決められない。HC1）")
        if self.when_lacking in (LACKING_FAIL, LACKING_ZERO, LACKING_NONE) and clause != CANNOT_USE:
            return None  # 説明がトラッシュできないときの処理を書いている
        if self.when_lacking == LACKING_SKIP:
            return None  # v0.79: トラッシュはワザを使うための条件ではなく、選べるカードがなければ処理の対象がない（p.309）
        return UNRESOLVED, f"{what}（使うワザの説明と、トラッシュできないときの処理が合わない・書かれていない）"

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        attacker = run.attacker()
        if run.knocked_out(attacker):
            # 処理の対象（ワザを使ったポケモン）がいなくなった（相手の「はんげき」などで HP 以上。p.309。C16 と同じ）
            run.state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                element="discard_energy", reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        if self.when_lacking == LACKING_SKIP and not self._candidates(run):
            run.state.add_event("discard_energy_failed", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                effect=str(run.key), needed=self.count, attached=0, outcome=LACKING_SKIP)
            return False
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        candidates = self._candidates(run)
        needed = self._needed(run)
        if needed is None:
            if not candidates and self.when_lacking in (LACKING_NONE, LACKING_ZERO, LACKING_FAIL):
                # v0.82: 「…すべてを、トラッシュする。…トラッシュできない時、ダメージは与えられない」（ファイヤーの「ハイパーフレイム」の「うら」）。1 枚もついていなければ
                # トラッシュできない（既定の ``LACKING_ERROR`` の「すべて」は今までどおり、0 枚なら何もしない）
                return self._lacking(run, candidates, 1)
            self._discard(run, tuple(candidates))
            return False
        if needed == 0 and not self.any_number:
            run.fs.results[self.name] = Discarded(())
            return False
        if len(candidates) < max(needed, 1):
            return self._lacking(run, candidates, max(needed, 1))
        if self.any_number:
            limit = len(candidates)
            if self.deck_limit:
                limit = min(limit, len(run.state.players[1 - run.player].deck))
                if limit == 0:
                    raise run.res.question("deck_short", "相手の山札が 0 枚（トラッシュした枚数のカードを取れない）")
            run.suspend(kind=self.decision_kind, player=run.player, options=candidates, min_choices=0, max_choices=len(candidates))
            return True
        # v0.42: 決定の種類は要素の ``decision_kind``（トラッシュは DISCARD_ENERGY。手札にもどす ``ReturnOwnEnergyToHand`` は RETURN_ENERGY）
        run.suspend(kind=self.decision_kind, player=run.player, options=candidates, min_choices=needed, max_choices=needed)
        return True

    def _lacking(self, run: AttackRun, candidates: list[int], needed: int) -> bool:
        if self.when_lacking == LACKING_FAIL:
            run.fail("discard")
            return False
        if self.when_lacking in (LACKING_ZERO, LACKING_NONE):
            run.fs.results[self.name] = Discarded((), self.when_lacking)
            attacker = run.attacker()
            run.state.add_event("discard_energy_failed", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                effect=str(run.key), needed=needed, attached=len(candidates), outcome=self.when_lacking)
            return False
        raise RuntimeError(
            f"ワザ {run.key} を使ったポケモンに{'エネルギー' if self.energy_type is None else '「' + self.energy_type.ja + '」エネルギー'}カードが "
            f"{needed} 枚ない（エンジンの不具合）"
        )

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        candidates = self._candidates(run)
        if any(energy not in candidates for energy in choices):
            raise RuntimeError(f"トラッシュに選んだカード {choices} が、ワザを使ったポケモンについていない（エンジンの不具合）")
        if self.any_number:
            if not choices:
                raise UnsupportedError(
                    "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO",
                    "「好きなだけはがしてすてる」で 0 枚を選べるかは決められないので扱わない（HC5）。1 枚以上を選ぶ",
                )
            if self.deck_limit and len(choices) > len(run.state.players[1 - run.player].deck):
                raise UnsupportedError(
                    "UNRESOLVED_DISCARD_DECK_SHORT",
                    f"トラッシュした枚数（{len(choices)}）のカードを相手の山札の上から取れない（山札 {len(run.state.players[1 - run.player].deck)} 枚）。"
                    "山札が足りない場合の処理は決められないので扱わない（HC6）。相手の山札の枚数までを選ぶ",
                )
        self._discard(run, tuple(uid for uid in run.attacker().energy if uid in choices))

    def _discard(self, run: AttackRun, cards: tuple[int, ...]) -> None:
        state = run.state
        owner, attacker = state.find_pokemon(run.fs.frame.source_pid)
        returns = E.energy_discard_plan(state, attacker, cards, cause=E.DISCARD_BY_ATTACK, by_player=run.player)  # v0.82: リサイクルエネルギー
        for energy in cards:
            attacker.energy.remove(energy)
            state.players[owner].discard.append(energy)
            state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy=energy)
        E.return_discarded_energy(state, returns)  # トラッシュした数（Discarded）はそのまま（トラッシュに置いたことは消さない）
        run.fs.results[self.name] = Discarded(cards)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        if self.any_number:
            limit = decision.max_choices
            if self.deck_limit:
                limit = min(limit, len(run.state.players[1 - run.player].deck))
            return combinations_answers(decision, range(1, limit + 1))  # 0 枚・相手の山札より多い枚数は答えのときに止める（HC5・HC6）
        return combinations_answers(decision, range(decision.min_choices, decision.max_choices + 1))


@dataclass(frozen=True)
class HealAllCounters(Element):
    """ワザを使ったポケモン自身にのっているダメージカウンターをすべてとりのぞく（じこさいせい。0 個なら 0 個。ダメージの計算はしない）。"""

    requires: str | None = None  # v0.31: トラッシュの要素の名前。トラッシュできなかったら（K3「このワザの効果はなくなる」）何もしない
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        if self.requires is not None:
            discarded = run.fs.results.get(self.requires)
            if discarded is not None and discarded.outcome != "done":
                return False
        attacker = run.attacker()
        per = state.rules.damage_per_counter
        before = attacker.damage
        attacker.damage = 0
        state.add_event("remove_all_damage_counters", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                        effect=str(run.key), counters=before // per, amount=before, damage_before=before, total_damage=attacker.damage)
        return False


def attached_in_attack(run: AttackRun, owner: int, pokemon: PokemonInPlay, cards, *, moved: bool = False) -> None:
    """v0.116（docs/energy-movement-attachment-devolution-v0.116.md 4 章）: ワザの効果で、場のポケモン ``pokemon``（持ち主 ``owner``）にエネルギーカード ``cards`` がついたあと（カードを
    動かしてログを残したあと）の反応を 1 枚ずつ処理する（``effects.energy_attached_by_effect``。［ほのおでかいふく］と、ついた時に発動するワザの持続効果）。``moved`` は場のほかの
    ポケモンからのつけ替え。止める理由（AT1・反応の順番の未対応）は問いにする（先読みが宣言の前に見つける）。v0.115 までの ``effects.after_energy_attached`` の呼び出しを置きかえた
    （持続効果のないポケモンでは同じ処理）。"""
    for card in cards:
        problem = E.attach_trigger_problem(run.state, pokemon, card, moved=moved, how=f"ワザ {run.key}")
        if problem is not None:
            raise run.res.question("attach_trigger_scope" if problem[0] == E.ATTACH_TRIGGER_SCOPE_CODE else "attach_trigger_order", problem[1])
        E.energy_attached_by_effect(run.state, owner, pokemon, card, moved=moved, how=f"ワザ {run.key}")


def suppressed_discard_to_hand(run: AttackRun) -> bool:
    """v0.74: 場のポケモンタワーで、ワザの「トラッシュからカードを取り出して手札に加える」要素の効果が消えるなら、ログ ``discard_to_hand_suppressed`` を残して True。
    相手のワザとして使った（まねた）ワザ・再録の登録も同じ要素なので、同じに当てはまる。実際の処理と先読み（状態の複製）で同じ問い合わせ。"""
    tower = E.discard_to_hand_suppressor(run.state)
    if tower is None:
        return False
    E.log_discard_to_hand_suppressed(run.state, run.player, tower, effect=str(run.key))
    return True


def protected_discard(run: AttackRun, element: str) -> bool:
    """v0.119（docs 8 章）: ［アレルギーほうし］がはたらいていて、ワザの要素 ``element`` の「トラッシュにあるカードを動かす」効果が起こらないなら、ログ ``discard_protected`` を残して True。
    要素が処理される時点の場で問い合わせる（宣言のときの場ではない。同じワザの前の要素で発生源がきぜつ・特殊状態になれば、その時点から変わる）。相手のワザとして使った（まねた）ワザ・
    再録の登録も同じ要素なので、同じに当てはまる。実際の処理と先読み（状態の複製）で同じ問い合わせ。ポケモンタワーの ``suppressed_discard_to_hand`` のあとに呼ぶ（両方なら、タワーのログ
    だけ）。"""
    if not E.discard_protection(run.state):
        return False
    attacker = run.state.find_pokemon(run.fs.frame.source_pid)
    source = {} if attacker is None else {"pokemon": attacker[1].card, "pokemon_id": attacker[1].pokemon_id}
    E.log_discard_protected(run.state, run.player, effect=str(run.key), element=element, **source)
    return True


def _discard_protected(self, run: AttackRun) -> bool:
    """v0.119: トラッシュのカードを動かす要素の ``Element.discard_protected``（はたらいている［アレルギーほうし］があるか）。"""
    return bool(E.discard_protection(run.state))


@dataclass(frozen=True)
class RecoverEnergy(Element):
    """自分のトラッシュのエネルギーカードを ``max_cards`` 枚まで選んで手札に加える（エナジーへんかん。0 枚は原典で決められない。H4）。"""

    max_cards: int
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = RECOVER_ENERGY

    @staticmethod
    def _candidates(run: AttackRun) -> list[int]:
        return [uid for uid in run.state.players[run.player].discard if run.state.card_def(uid).category == "energy"]

    discard_protected = _discard_protected

    def run(self, run: AttackRun) -> bool:
        if suppressed_discard_to_hand(run):
            return False  # v0.74: ポケモンタワーで、この要素（トラッシュから手札に加える）の効果が消える。次の要素（自分へのダメージ）はそのまま
        if protected_discard(run, "recover_energy"):
            return False  # v0.119: ［アレルギーほうし］。次の要素はそのまま
        candidates = self._candidates(run)
        if not candidates:
            return False  # 選べるものがない。手札に加えるものはなく、次の要素へ（H5）
        run.suspend(kind=RECOVER_ENERGY, player=run.player, options=candidates, min_choices=0,
                    max_choices=min(self.max_cards, len(candidates)))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if not choices:
            raise UnsupportedError(
                "UNRESOLVED_RECOVER_ZERO_ENERGY",
                "トラッシュにエネルギーカードがあるときに 0 枚を選べるか（「最大2枚選び出し」が 0 枚を含むか）は『オフィシャルブック2000』"
                "（p.158）から決められないので扱わない。1 枚以上を選ぶ",
            )
        for uid in choices:
            if uid not in self._candidates(run):
                raise RuntimeError(f"手札に加えるカード {uid} が、ワザを使ったプレイヤーのトラッシュのエネルギーカードではない（エンジンの不具合）")
        return_discard_to_hand(run.state, run.player, tuple(choices))
        attacker = run.attacker()
        run.state.add_event("recover_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            cards=tuple(choices))

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        # 先読み（v0.15c）: 1 枚以上のすべての答え（選ぶカードと順番）を試す。v0.14 は枚数ごとの代表（最初のカードから）だけだった。
        # 0 枚は試さない: 0 枚の答えは決定の答えのときに止める（H4。UNRESOLVED_RECOVER_ZERO_ENERGY。決定は待ったまま）もので、ワザの
        # 宣言を止める理由ではない（1 枚以上を選べば処理できる）。ここで 0 枚を試すと、宣言そのものを H4 で拒否してしまう
        return all_answers(decision, minimum=1)


# ---------------------------------------------------------------- v0.31: 保留していた 22 枚のための要素（docs/held-cards-v0.31.md）


@dataclass(frozen=True)
class HeadsBonus:
    """「コインを投げて「おもて」なら、``bonus`` ダメージを追加」（でんこうせっか・ひをふく）。コインはダメージの要素の中（ダメージの量だけを決める。
    受けるポケモンがダメージを受けない状態なら投げるかが決まらない。v0.4b と同じ問い）。"""

    bonus: int
    local_coins: ClassVar[int] = 1

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + (self.bonus if flips.results[0] is HEADS else 0)


@dataclass(frozen=True)
class OpponentTailsBonus:
    """v0.61: 「相手プレイヤーにコインを投げさせ、「うら」なら ``bonus`` ダメージを追加する」（わるいダグトリオの「つきおとす」）。コインはダメージの要素の中で、相手プレイヤーが
    1 枚投げる（``flipped_by_opponent``。v0.40 の ``TailsOfOpponentBenchCoins`` と同じ投げる人）。基本となるダメージは目安 +（「うら」なら ``bonus``）。受けるポケモンがダメージを
    受けない状態なら投げるかが決まらない（v0.4b と同じ問い。``Damage.run``）。"""

    bonus: int
    local_coins: ClassVar[int] = 1
    flipped_by_opponent: ClassVar[bool] = True

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + (self.bonus if flips.results[0] is TAILS else 0)


@dataclass(frozen=True)
class PlusDefenderEnergy:
    """ダメージの目安の数字 +「相手についているエネルギーカード」の枚数 × ``per``（ミュウツーの「サイコキネシス」）。"""

    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + E.attached_energy_cards(run.state, run.opponent_active()) * self.per  # v0.50: 数え方を「サイコウェーブ」と共通にした（同じ値）


@dataclass(frozen=True)
class DefenderEnergyCardsTimes:
    """相手の対戦ポケモンについているエネルギーカードの枚数 × ``per``（v0.50。ミュウの「サイコウェーブ」。p.321 の 1 段階の基本となるダメージそのもの。「サイコキネシス」の
    ``PlusDefenderEnergy`` は目安の数字に加える値で、こちらは目安の数字を使わない）。数えるのはカードの枚数（``effects.attached_energy_cards``）。0 枚なら 0。"""

    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return E.attached_energy_cards(run.state, run.opponent_active()) * self.per


@dataclass(frozen=True)
class PlusOwnCounters:
    """ダメージの目安の数字 + 自分にのっているダメージカウンターの数 × ``per``（わるいブースターの「いかり」）。"""

    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + run.attacker().damage // run.state.rules.damage_per_counter * self.per


@dataclass(frozen=True)
class HeadsPlusOwnCounters:
    """v0.79: ダメージの目安の数字 +（コインが「おもて」なら）自分にのっているダメージカウンターの数 × ``per``（ブルー（neo3-048）の「いかりのずつき」）。p.321 の 1 段階。
    コインはダメージの要素の中で、ダメージの量だけを決める（v0.11 の ``HeadsOwnCounters``・v0.2d の ``HeadsBonus`` と同じ。受けるポケモンがダメージを受けない状態なら
    投げるかが決まらない v0.4b の問い）。「うら」・カウンターが 0 個なら目安の数字（0 にしない）。"""

    per: int
    local_coins: ClassVar[int] = 1

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        counters = run.attacker().damage // run.state.rules.damage_per_counter
        return run.attack.damage + (counters * self.per if flips.results[0] is HEADS else 0)


@dataclass(frozen=True)
class HeadsOfCoin:
    """ワザ全体のコイン ``coin`` の「おもて」の数 × ``per``（れんぞくファイヤーボール・やきはらう。コインはトラッシュも決める）。"""

    coin: str
    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.heads(self.coin) * self.per


@dataclass(frozen=True)
class HeadsOfDiscarded:
    """トラッシュの要素 ``discard`` でトラッシュしたカードの数だけコインを投げ、「おもて」の数 × ``per``（マチスのエレブーの「ほうでん」）。コインは
    ダメージの要素の中（ダメージの量だけを決める）。"""

    discard: str
    per: int
    by_heads: ClassVar[bool] = True  # v0.35: 「おもて」の数だけを使う（先読みは「おもて」の数でまとめる。トラッシュした枚数だけ投げる）

    def coin_count(self, run: AttackRun) -> int:
        return len(run.fs.results[self.discard].cards)

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return (0 if flips is None else flips.heads) * self.per


@dataclass(frozen=True)
class PerMilledEnergy:
    """山札からトラッシュの要素 ``mill`` でトラッシュしたカードの中の ``energy_type`` の基本エネルギーカードの数 × ``per``（カツラのブーバーの
    「マグマふんしゅつ」。v0.95: わるいマグマラシの「マグマラッシュ」）。

    v0.95（docs/private-looks-deck-movement-v0.95.md 5 章）: カードの枚数で数える（エネルギーの個数ではない）。山札・サイドにレインボーエネルギーがあれば FV1（``milled_type_energy``。
    印刷の文面にない「基本」の条件を書き足さない）。ミラクルエネルギーは場の外では色がない（v0.85 の読み方）ので数えない。数は宣言の前には分からない（山札の上の並び）ので、先読みは
    山札とサイドの中身からありうる数のすべてを試す（``Resolution.hidden_choice``。受け付けるかがトラッシュする 5 枚によらない）。"""

    mill: str
    energy_type: EnergyType
    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        cards = run.fs.results[self.mill].cards
        found = milled_type_energy(run, cards, self.energy_type)
        pool = hidden_deck_pool(run, cards)
        typed = sum(1 for uid in pool if _typed_basic_energy(run.state, uid, self.energy_type))
        low, high = max(0, len(cards) - (len(pool) - typed)), min(len(cards), typed)
        return run.res.hidden_choice(range(low, high + 1), len(found)) * self.per


def hidden_deck_pool(run: AttackRun, milled: tuple[int, ...]) -> tuple[int, ...]:
    """v0.95: ワザを使ったプレイヤーが、山札の上からトラッシュする前に見えなかった自分のカード（今トラッシュした ``milled`` と、残りの山札・サイド）。中身は持ち主が知っている
    （デッキから見えているカードを除いたもの）が、どのカードが山札の上にあったかは知らない（v0.73 の熱血!の FV1 と同じ範囲）。"""
    p = run.state.players[run.player]
    return (*milled, *p.deck, *(uid for uid in p.prizes if uid is not None))


def _typed_basic_energy(state: GameState, uid: int, energy_type: EnergyType) -> bool:
    definition = state.card_def(uid)
    return definition.is_basic_energy and definition.provides is energy_type


def milled_type_energy(run: AttackRun, milled: tuple[int, ...], energy_type: EnergyType) -> tuple[int, ...]:
    """v0.95: 自分の山札の上からトラッシュしたカード ``milled`` のうち、説明の「「``energy_type``」エネルギーカード」（その色の基本エネルギーカード。トラッシュした順）。

    - 山札の上からトラッシュしたレインボーエネルギーが「「X」エネルギーカード」に当たるかは決まらない（v0.73 の熱血!の FV1 と同じ問い ``milled_rainbow_energy``）。トラッシュするまで
      山札の上のカードは分からないので、山札・サイド（``hidden_deck_pool``）にレインボーエネルギーがあれば止める（先読みが宣言の前に見つける。トラッシュした 5 枚によらない）
    - 特殊エネルギーのうち、その色を出さないもの（無色2個エネルギーなど）は当たらない。ミラクルエネルギーは場の外では色がない（v0.85 の読み方。``rainbow_cards_in`` と同じ）"""
    rainbow = E.rainbow_cards_in(run.state, hidden_deck_pool(run, milled))
    if rainbow:
        raise run.res.question("milled_rainbow_energy", f"ワザ {run.key}・山札・サイドのレインボーエネルギー {rainbow}・「{energy_type.ja}」エネルギーカード")
    return tuple(uid for uid in milled if _typed_basic_energy(run.state, uid, energy_type))


@dataclass(frozen=True)
class ExtraEnergyMixed:
    """ダメージの目安の数字 +「ワザに必要なエネルギーよりも多く ``energy_type`` エネルギーがついている時、多いエネルギー 1 つにつき ``per``（``max_extra``
    つぶんまで）」で、必要なエネルギーに無色がまざるワザ（第4弾のコダックの「みずでっぽう」）。多いエネルギーの数は、無色のぶんを ``energy_type`` で
    払うかで変わる（記号の数で数える・無色をほかのエネルギーで払う・無色を ``energy_type`` で払う）。読み方で答えが違う場合は決められない（HC4）。"""

    energy_type: EnergyType
    per: int
    max_extra: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        transform_energy_question(run, run.attacker(), self.energy_type, cards=False)  # v0.49: TE1。v0.58: RB1（レインボーエネルギー）
        units = E.attached_units(run.state, run.attacker())  # v0.58: 出すエネルギーの個数（無色2個エネルギーは 2 個）
        have = sum(1 for unit in units if unit == frozenset({self.energy_type}))
        others = len(units) - have
        symbols = sum(1 for t in run.attack.cost if t is self.energy_type)
        colorless = sum(1 for t in run.attack.cost if t is EnergyType.COLORLESS)
        by_symbols = have - symbols
        others_first = have - symbols - max(0, colorless - others)
        typed_first = have - symbols - min(colorless, max(0, have - symbols))
        extras = {min(max(0, value), self.max_extra) for value in (by_symbols, others_first, typed_first)}
        if len(extras) > 1:
            raise run.res.question("extra_energy_colorless", f"「{self.energy_type.ja}」{have}・ほか {others}・読み方ごとの数 {sorted(extras)}")
        return run.attack.damage + extras.pop() * self.per


@dataclass(frozen=True)
class BenchDamage(Element):
    """相手の控えポケモン（``pokemon_type`` なら、そのタイプのポケモンだけ）の全員に、それぞれダメージ（v0.31。カツラのガーディの「もえひろがる」・
    カツラのリザードの「やきはらう」）。受けるのは控えの並びの順。プラスパワーは変えない（p.257）。``weakness_resistance`` が False なら「弱点・抵抗力」に
    関係なく。v0.33: ``own`` なら自分の控えポケモンの全員（p.320 のダメージの (4)。タケシのディグダの「ミニじしん」。``E.SELF_BENCH``）。
    v0.37: ``weakness_resistance`` が None なら、説明が弱点・抵抗力について書いていない（第1弾のダグトリオの「じしん」）。ダメージを与える前に、どれかの
    控えのポケモンで計算するかどうかで最終ダメージが変わるなら、問い ``bench_damage_weakness_resistance``（JS1）で止める。変わらなければ「弱点・抵抗力に
    関係なく」と同じ計算（結果は同じ）。

    v0.39: 受ける控えのポケモンをタイプでしぼる項目を加えた。``same_type_as_opponent_active`` なら、相手の対戦ポケモンと同じタイプのポケモンだけ（マルマインの
    「ビリビリ」の「相手の対戦ポケモンと同じ色の控えポケモン全員」）、``exclude_type`` なら、そのタイプ以外のポケモンだけ（カスミのニョロボンの「ウォーター
    リング」の「「水」ポケモン以外のポケモン全員」）。タイプはどれも、この要素を処理する時点の場のポケモンのいちばん上のカードのタイプ（p.310）。"""

    base: Any
    pokemon_type: EnergyType | None = None
    weakness_resistance: bool | None = False
    gate: tuple | None = None
    name: str = "bench_damage"
    own: bool = False
    same_type_as_opponent_active: bool = False
    exclude_type: EnergyType | None = None
    # v0.40: 名前（いちばん上のカードの名前の完全一致）がこのどれかの控えポケモンだけ（わるいマタドガスの「みんなでばくはつ」）。None なら名前を見ない
    names: tuple[str, ...] | None = None
    requires: str | None = None  # v0.85: トラッシュの要素の名前。トラッシュできなかったら（「このワザのダメージは、すべてなくなる」。かえんぐるま）何もしない
    color_filter: tuple[str, str] | None = None  # v0.88: ``Damage.color_filter`` と同じ（コアストリーム・レインボーウェーブ）
    marker: str | None = None  # v0.91: ``Damage.marker`` と同じ（かみなりショック。マーカーのない控え・うらのカードは受けない）
    has_power: bool = False  # v0.114: ``Damage.has_power`` と同じ（パチパチ。特殊能力を持っていない控え・うらのカードは受けない）
    energy_cards: bool = False  # v0.115: ``Damage.energy_cards`` と同じ（サイコスプラッシュ。エネルギーカードをつけていない控えは受けない）
    phase: ClassVar[Phase] = Phase.DAMAGE
    guards_bench: ClassVar[bool] = True  # v0.65

    def targets(self, run: AttackRun) -> list[PokemonInPlay]:
        side = run.player if self.own else 1 - run.player
        bench = run.state.players[side].bench
        if self.marker is not None:
            bench = [p for p in bench if has_marker(p, self.marker)]
        if self.has_power:
            bench = [p for p in bench if holds_power_now(run, p)]
        if self.energy_cards:
            bench = [p for p in bench if E.attached_energy_cards(run.state, p)]
        named = [p for p in bench if self.names is None or E.form_def(run.state, p).name_ja in self.names]  # v0.49: 今の姿の名前
        if self.color_filter is not None:
            named = [p for p in named if color_filter_hit(run, p, self.color_filter)]  # v0.88
        if self.pokemon_type is None and not self.same_type_as_opponent_active and self.exclude_type is None:
            return named
        # v0.48: タイプ（色）は今有効な色（``effects.type_readings``。［へんしょく］）。読み方（VS1）が 2 つあり、選ばれる控えが変わるなら止める
        involved = ([run.opponent_active()] if self.same_type_as_opponent_active else []) + named

        def chosen(views) -> tuple[int, ...]:
            color_of = {p.pokemon_id: view.pokemon_type for p, view in zip(involved, views)}
            wanted = self.pokemon_type
            if self.same_type_as_opponent_active:
                wanted = views[0].pokemon_type
                if wanted is None:
                    # v0.47: タイプ（色）のない相手の対戦ポケモン（場のなにかの化石・ピッピ人形）と「同じ色」の控えポケモンはいない（実装上の判断。
                    # docs/fossil-hidden-info-v0.47.md 3 章。None を「タイプでしぼらない」と読まない）
                    return ()
            return tuple(p.pokemon_id for p in named
                         if (wanted is None or color_of[p.pokemon_id] is wanted)
                         and (self.exclude_type is None or color_of[p.pokemon_id] is not self.exclude_type))

        try:
            ids = E.same_for_type_readings(run.state, involved, chosen)
        except E.TypeReadingsDiffer as differ:
            raise type_question(run.res, differ, f"ワザ {run.key} の控えポケモンへのダメージの対象（色で選ぶ）") from None
        return [p for p in named if p.pokemon_id in ids]

    def coin_receiver(self) -> str | None:
        """v0.56: 控えポケモンへのダメージの要素。受けるポケモンのどれかがダメージを受ければ有効（``void_coin_question`` が、受けるポケモンがみな無効（見えない壁）かを見る）。"""
        return "bench"

    def void_for_all(self, run: AttackRun) -> bool:
        """v0.56: 受ける控えポケモンが 1 匹以上いて、どれもダメージの要素を無効にする状態（見えない壁）か。"""
        from .kernel import first_void

        side = run.player if self.own else 1 - run.player
        targets = self.targets(run)
        return bool(targets) and all(first_void(run.res, run.incoming(), side, pokemon) is not None for pokemon in targets)

    def has_target(self, run: AttackRun) -> bool:
        return bool(self.targets(run))  # v0.38: 控えポケモンがいなければ、処理の対象がない

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        if self.requires is not None:
            discarded = run.fs.results.get(self.requires)
            if discarded is not None and discarded.outcome == LACKING_NONE:
                return False  # v0.85: 「…トラッシュできないとき、このワザのダメージは、すべてなくなる」（かえんぐるま）
        if local_coins(self.base, run):
            raise RuntimeError("控えポケモンへのダメージの量を、要素の中のコインで決めるワザはない（エンジンの不具合）")
        targets = self.targets(run)
        kind = E.SELF_BENCH if self.own else E.OPPONENT_BENCH
        value_for = getattr(self.base, "value_for", None)  # v0.115: 受けるポケモンごとの基本となるダメージ（サイコスプラッシュ。控えごとに数える）
        if value_for is not None:
            if self.weakness_resistance is None:
                raise RuntimeError("受けるポケモンごとの基本となるダメージで、弱点・抵抗力を書いていない控えへのダメージはない（エンジンの不具合）")
            return guarded_damages(run, self, [(kind, target.pokemon_id, value_for(run, target), bool(self.weakness_resistance)) for target in targets])
        if self.weakness_resistance is None:
            differs = [p.pokemon_id for p in targets
                       if weakness_resistance_matters(run.res, run.fs, kind, self.base.value(run, None), p.pokemon_id)]
            if differs:
                raise run.res.question("bench_damage_weakness_resistance", f"控えのポケモン {differs}")
        base = self.base.value(run, None)
        # v0.65: ［ベンチガード］の決定が要れば止まる（``guarded_damages``）
        return guarded_damages(run, self, [(kind, target.pokemon_id, base, bool(self.weakness_resistance)) for target in targets])


@dataclass(frozen=True)
class ChosenBenchDamage(Element):
    """コインを投げて ``local_coin`` の面なら、控えポケモンを 1 匹選び、そのポケモンにダメージ（v0.33。カツラのサイホーンの「かけぬける」は相手の控え・
    「おもて」。v0.34: ``own`` なら自分の控え（サカキのカイロスの「うしろなげ」は「うら」））。選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。
    控えが 1 匹でも出す）。その控えがいなければ、処理の対象がないのでコインを投げない（p.309）。

    ダメージの要素（``Phase.DAMAGE``）なので、前のダメージの要素で「ダメージを受けたとき」の効果（はんげき・返す効果・わるいねぞう）がはたらいていると、
    その効果はこの要素のあと（ダメージの処理がすべて終わったあと。p.89）に処理する。v0.34 から、決定をまたいでその送る効果を運ぶ（``AttackRun.suspend``
    の ``carry``。v0.33 は決定の前に ``UNSUPPORTED_DECISION_AFTER_DAMAGE_TRIGGER`` で止めていた）。選んだ控えも「ダメージを受けたとき」の効果を持つと、
    1 つのワザで 2 つ（C34・C35。先読みが宣言の前に止める）。"""

    base: Any
    local_coin: CoinSide | None = HEADS
    # v0.39: None なら、説明が弱点・抵抗力について書いていない（第2弾のピカチュウの「スパーク」）。選べる控えのうち、計算するかどうかで最終ダメージが
    # 変わるポケモンは、選べるが選ぶと止める（JS1。``unresolved_choices``。選んだポケモンだけが受けるので、ほかの控えを選ぶ処理は止めない）。選べるどの
    # ポケモンでも変わるなら、宣言の前に止める（先読みが見つける）
    weakness_resistance: bool | None = False
    name: str = "bench_damage"
    own: bool = False
    # v0.38: 説明に「控えポケモンがいないとき、このワザは使えない」がある（サワムラーの「のびるキック」。ワザを使うための条件は実装の ``usage_problem``。
    # 相手のワザとして使うときは ``copy_problem``）。ない（エリカのモンジャラの「のびるつる」・タケシのロコンの「ほのおのわ」）なら、控えがいなければ処理の
    # 対象がないので何もしない（p.309。v0.31 のかどわかす・v0.33 のかけぬけると同じ読み方）
    required: bool = False
    phase: ClassVar[Phase] = Phase.DAMAGE
    guards_bench: ClassVar[bool] = True  # v0.65
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def side(self, run: AttackRun) -> int:
        return run.player if self.own else 1 - run.player

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        if self.required and not run.state.players[self.side(run)].bench:
            return (ILLEGAL if clause in (CANNOT_USE, FOLLOW_TEXT) else UNRESOLVED), "相手に控えポケモンがいない（ワザを使うための条件）"
        return None

    def run(self, run: AttackRun) -> bool:
        if local_coins(self.base, run):
            raise RuntimeError("控えポケモンへのダメージの量を、要素の中のコインで決めるワザはない（エンジンの不具合）")
        bench = run.state.players[self.side(run)].bench
        if not bench:
            if self.required:
                raise RuntimeError(f"控えポケモンがいないのに、ワザ {run.key} の控えポケモンへのダメージに来た（使うための条件の確認の漏れ。エンジンの不具合）")
            return False
        if self.local_coin is not None:
            from .kernel import first_void

            if all(first_void(run.res, run.incoming(), self.side(run), pokemon) is not None for pokemon in bench):
                # v0.56: このコインが決めるのは控えポケモンへのダメージだけで、選べるどの控えもダメージを受けない（見えない壁）。v0.4b と同じ問い（投げるかが決まらない）
                # v0.84: こおりのはしら（``catalog.ICE_PILLAR``）も同じ（理由の文に、無効にした効果の種類を書く）
                names = {"invisible_wall": "見えない壁", "ice_pillar": "こおりのはしら", "neutral_shield": "ニュートラルシールド"}  # v0.103: ［ニュートラルシールド］
                kinds = sorted({names.get(first_void(run.res, run.incoming(), self.side(run), pokemon).definition.name, "ダメージを受けない状態") for pokemon in bench})
                raise run.res.question("prevented_coin_damage", f"ダメージを受けない控えポケモン {[p.pokemon_id for p in bench]}（{'・'.join(kinds)}）を選ぶダメージだけを決めるコイン")
            if run.flip(1).results[0] is not self.local_coin:
                return False
        extra: tuple = ()
        if self.weakness_resistance is None:
            kind = E.SELF_BENCH if self.own else E.OPPONENT_BENCH
            base = self.base.value(run, None)
            differs = tuple(p.pokemon_id for p in bench if weakness_resistance_matters(run.res, run.fs, kind, base, p.pokemon_id))
            if len(differs) == len(bench):
                raise run.res.question("bench_damage_weakness_resistance", f"控えのポケモン {list(differs)}（選べるどのポケモンも）")
            if differs:
                question = QUESTIONS["bench_damage_weakness_resistance"]
                extra = (("unresolved_choices", differs), ("unresolved_code", question.code),
                         ("unresolved_reason", f"{question.message}（JS1。選んだ控えのポケモンで、計算するかどうかで受けるダメージが変わる）"))
        # 枠の値（「とうめい」の結果（T4・T27）・処理した送る効果の数（C34・C35）・こんじょうの写し・v0.34 からまだ処理していない送る効果）を運ぶ。
        # 相手の対戦ポケモンへのダメージの結果を、決定のあとのきぜつの判定・控えのポケモンの「とうめい」の判定・送る効果の処理で使う
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=[p.pokemon_id for p in bench], carry=True, extra=extra)
        return True

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        # v0.39: 選ぶと止める控え（JS1）は試さない（選んだときに決定の確認が止める。ほかの控えを選ぶ処理は止めない）
        blocked = set(decision.context_value("unresolved_choices", ()))
        return [answer for answer in all_answers(decision) if not blocked & set(answer)]

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        bench = run.state.players[self.side(run)].bench
        if choices[0] not in [p.pokemon_id for p in bench]:
            raise RuntimeError(f"選んだポケモン {choices} が、{'自分' if self.own else '相手'}の控えにいない（エンジンの不具合）")
        guarded_damages(run, self, [(E.SELF_BENCH if self.own else E.OPPONENT_BENCH, choices[0], self.base.value(run, None), bool(self.weakness_resistance))],
                        record=True)  # v0.65: ［ベンチガード］


@dataclass(frozen=True)
class SelfPersistent(Element):
    """ワザを使ったポケモン自身に、次の相手の番にはたらく持続する効果を与える（v0.31。みちづれ ``DestinyBond``・バリアー ``AttackBarrier``・
    ちいさくなる ``DamageReduction``。v0.45: ロケットタックルの「ダメージを受けない」 ``PreventDamage``・かたくなる ``ZeroDamageBelow``）。``requires`` の
    トラッシュの要素がトラッシュできなかったら与えない。"""

    kind: str
    amount: int | None = None
    requires: str | None = None
    local_coin: CoinSide | None = None  # v0.34: この要素のコイン（ギャロップの「こうそくいどう」は「おもて」でバリアー）。ワザを使ったポケモンがいなければ投げない
    gate: tuple | None = None  # v0.38: ワザ全体のコインの面（キョウのピジョンの「こうそくひこう」は、追加のダメージと同じコインの「おもて」でバリアー）
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        if self.requires is not None:
            discarded = run.fs.results.get(self.requires)
            if discarded is not None and discarded.outcome != "done":
                return False
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("persistent_effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                persistent_effect=self.kind, effect=str(run.key), reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        turn = run.state.turn_number
        common = {"source_card": attacker.card, "source_player": run.player, "created_turn": turn, "active_turn": turn + 1}
        if self.kind == DestinyBond.kind:
            effect = DestinyBond(**common)
        elif self.kind == AttackBarrier.kind:
            effect = AttackBarrier(**common)
        elif self.kind == DamageReduction.kind:
            effect = DamageReduction(**common, amount=self.amount)
        elif self.kind == PreventAttackDamage.kind:
            effect = PreventAttackDamage(**common)  # v0.79: ピカチュウ（neo1-036）の「こうそくいどう」（ワザによるダメージだけを受けない）
        elif self.kind == PreventDamage.kind:
            effect = PreventDamage(**common)  # v0.45: わるいカメックスの「ロケットタックル」（自分へのダメージのあとのコイン。HP 以上なら投げない）
        elif self.kind == ZeroDamageBelow.kind:
            effect = ZeroDamageBelow(**common, threshold=self.amount)  # v0.45: イワークの「かたくなる」（しきい値 ``amount``）
        elif self.kind == HalvedDamage.kind:
            effect = HalvedDamage(**common)  # v0.46: エリカのタマタマの「リフレクター」（半分（切りすて））
        elif self.kind == DoubledDamage.kind:
            effect = DoubledDamage(**common)  # v0.75: キングラーの「もろばバサミ」（2 倍）
        elif self.kind == BenchAttackDamageGuard.kind:
            effect = BenchAttackDamageGuard(**common)  # v0.84: やさしいジュゴンの「こおりのはしら」（持ち主の控えポケモンへのワザのダメージを無効にする）
        elif self.kind == ZeroDamageAtLeast.kind:
            effect = ZeroDamageAtLeast(**common, threshold=self.amount)  # v0.84: やさしいサンダースの「パルスガード」（しきい値 ``amount`` 以上なら 0）
        elif self.kind == AttackEffectGuard.kind:
            effect = AttackEffectGuard(**common)  # v0.84: やさしいカイリューの「ひかりのはどう」（ワザの効果の要素を無効にする）
        elif self.kind == StatusImmunityNextTurn.kind:
            effect = StatusImmunityNextTurn(**common)  # v0.85: ベイリーフの「しんぴのこな」（次の相手の番、特殊状態にならない）
        else:
            raise ValueError(f"知らない持続する効果の種類 {self.kind!r}")
        add_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key))
        return False


@dataclass(frozen=True)
class OpponentCannotAttack(Element):
    """コインが「おもて」なら、相手の対戦ポケモンは次の相手の番にワザを使えない（v0.31。イーブイの「しっぽをふる」。持続する効果 ``CannotAttack``。
    相手に与える効果なので「とうめい」・「ワザをうけない」状態を評価する）。"""

    local_coin: CoinSide | None = HEADS
    # v0.92: ワザ全体のコインの面（イトマルの「こわいかお」の 1 枚のコインで、ワザとにげるの両方の禁止を決める。``local_coin`` は None）。None ならこの要素のコインだけ（v0.91 まで）
    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.ATTACK_LOCK_ELEMENT

    def coin_receiver(self) -> str | None:
        return "effect"  # v0.92: ワザ全体のコインが決める相手の対戦ポケモンへの効果（``void_coin_question``）

    def has_target(self, run: AttackRun) -> bool:
        return not run.knocked_out(run.opponent_active())  # v0.92: このワザで HP 以上なら処理の対象がない（ワザ全体のコインを投げない。p.309）

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if self.local_coin is not None:
            if run.fs.reception.get(target.pokemon_id) is False:
                raise run.res.question("evaded_effect_coin", f"ポケモン {target.pokemon_id}")
            prevented_effect_coin(run, opponent, target)
            if run.flip(1).results[0] is not self.local_coin:
                return False
        if not reaches(run.res, run.fs, opponent, target, E.ATTACK_LOCK_ELEMENT):
            return False
        attacker = run.attacker()
        turn = run.state.turn_number
        effect = CannotAttack(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn + 1)
        add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key))
        return False


@dataclass(frozen=True)
class DiscardOpponentEnergy(Element):
    """相手の対戦ポケモン（``each_bench`` なら、さらに相手の控えポケモン全員）から、それぞれエネルギーカードを 1 枚ずつ、ワザを使ったプレイヤーが
    選んでトラッシュする（v0.31。カツラのヒトカゲの「メラメラ」・カスミのゴルダックの「スーパーデストロイ」（``local_coin`` が「おもて」なら））。

    相手のポケモンへの効果なので、ポケモンごとに「ワザをうけない」状態・「とうめい」を評価する（1 つのワザで 2 匹以上の「とうめい」は T27）。処理の
    対象がいない（エネルギーカードがついていない・このワザで HP 以上になった）ポケモンは飛ばす（p.309）。どのポケモンにもエネルギーカードがなければ、
    コインも投げない（内容の対象がない。p.309）。決定はポケモンごと（対戦ポケモン → 控えの並びの順）。

    v0.101（docs/counter-keep-energy-protection-v0.101.md 4 章）: ［KEEP］（``E.energy_discard_void``。ワザを実際に使ったプレイヤーの効果として聞く）でトラッシュする効果がなくなる
    ポケモンは、効果を受けたあと（「とうめい」などの判定のあと）に選ばせずに飛ばし、ログ ``energy_discard_voided`` を残す（手札にもどるかの問いも聞かない）。この要素のコイン
    （``local_coin``）は、決めるトラッシュがどれもなくなるなら投げるかが決まらない（KP2）。ほかのポケモンへのトラッシュが残れば投げる。選んだ個体（``chosen``）は選ぶと KP2"""

    each_bench: bool = False
    local_coin: CoinSide | None = None
    # v0.89: 先に選んだ個体（``ChooseTarget`` の ``ChosenTarget``）の名前。あれば、そのポケモンだけ（対戦ポケモンでも控えポケモンでも。レアコイルの「マイクロウェーブ」の
    # 「そのポケモンについているエネルギーカード」）。選んだ個体が相手の場をはなれていれば、処理の対象がない（今の対戦ポケモンにすり替えない）
    chosen: str | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = DISCARD_OPPONENT_ENERGY
    opponent_element: ClassVar[str] = E.ENERGY_DISCARD_ELEMENT

    @staticmethod
    def _energy(run: AttackRun, pokemon: PokemonInPlay) -> list[int]:
        if E.energy_removal_protected(run.state, 1 - run.player, pokemon, run.player) is not None:
            return []  # v0.59: タケシの保護（相手の使うワザによってははがされない）。はがせるカードがないポケモンと同じ（処理の対象がない）
        return [uid for uid in pokemon.energy if run.state.card_def(uid).category == "energy"]

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        p = run.state.players[opponent]
        if self.chosen is not None:
            if self.each_bench:
                raise RuntimeError("選んだ個体のエネルギーカードのトラッシュに、控え全員を加える並びはない（エンジンの不具合）")
            candidates = chosen_pokemon(run, self.chosen, opponent)
        else:
            candidates = [p.active] + (list(p.bench) if self.each_bench else [])
        targets = []
        for pokemon in candidates:
            if run.knocked_out(pokemon):
                run.ko_prevention_conflict(pokemon, opponent)
                continue
            if self._energy(run, pokemon):
                targets.append(pokemon)
        if self.local_coin is not None:
            if not targets:
                return False
            from .kernel import first_void

            # v0.101: ［KEEP］でトラッシュの効果がなくなるポケモン（エネルギーカードはある）は、このコインが決めるものがない。どれもそうなら、なくなった効果だけを決めるコインを
            # 投げるかは決まらない（KP2。UQ-COIN-IN-NULLIFIED-ELEMENT と同じ形）。ほかのポケモンが残れば、そのポケモンについて今までどおり（なくなったポケモンのログは ``_next``）
            live = [pokemon for pokemon in targets if self._voided(run, pokemon) is None]
            if not live:
                raise run.res.question("keep_voided_discard_coin", f"ポケモン {[pokemon.pokemon_id for pokemon in targets]}（［KEEP］でトラッシュの効果がなくなる）")
            if all(run.fs.reception.get(pokemon.pokemon_id) is False for pokemon in live):
                # v0.33: 前のダメージの要素で「とうめい」の「おもて」になり、このワザで受けないと決まったポケモンだけへの効果のコイン（はかいでんぱ・
                # はかいビーム。T19b と同じ問い。v0.31 のスーパーデストロイは前にダメージの要素がないので起こらない）
                finals = [run.fs.evaded.get(pokemon.pokemon_id) for pokemon in live]
                raise run.res.question("evaded_effect_coin", f"ポケモン {[pokemon.pokemon_id for pokemon in live]}",
                                       E.evaded_effect_coin_error(live[0].pokemon_id, finals[0]) if len(live) == 1 and finals[0] is not None else None)
            if all(first_void(run.res, run.incoming(), opponent, pokemon, Window.BEFORE_EFFECT) is not None for pokemon in live):
                raise run.res.question("prevented_effect_coin", f"ポケモン {[pokemon.pokemon_id for pokemon in live]}")
            if run.flip(1).results[0] is not self.local_coin:
                return False
        return self._next(run, [pokemon.pokemon_id for pokemon in targets])

    @staticmethod
    def _voided(run: AttackRun, pokemon: PokemonInPlay) -> E.EnergyDiscardVoid | None:
        """v0.101: 相手のポケモン ``pokemon`` のエネルギーカードをトラッシュする効果が、［KEEP］でなくなるか（ワザを実際に使ったプレイヤーの効果。``E.energy_discard_void``）。"""
        return E.energy_discard_void(run.state, pokemon, cause=E.DISCARD_BY_ATTACK, by_player=run.player)

    def choice_problem(self, run: AttackRun, owner: int, pokemon: PokemonInPlay) -> tuple[str, str] | None:
        """v0.89: 選ぶ要素（``ChooseTarget``）が、このポケモンを選ぶと決められない場合を聞く（``chosen`` の要素だけ）。コイン（``local_coin``）はこのポケモンへのトラッシュだけを
        決めるので、そのポケモンが「ワザをうけない」状態（効果の要素を無効にする効果）なら HC3、前のダメージの要素で「とうめい」の判定をしうるなら T19b（前のダメージで受けないと
        決まると、コインを投げるかが決められない。コインの結果で受け付けるかが変わらないよう、選ぶ前に止める）。エネルギーカードがない・タケシの保護のポケモンは、処理の対象がない
        のでコインを投げない（止めない）。"""
        if self.chosen is None or self.local_coin is None or run.state.is_face_down(pokemon) or not self._energy(run, pokemon):
            return None
        from .kernel import first_void

        if self._voided(run, pokemon) is not None:
            # v0.101: ［KEEP］でトラッシュの効果がなくなるポケモン。コインはこのポケモンへのトラッシュだけを決める（KP2。選ぶと止める。ほかのポケモンを選ぶ答えは止めない）
            return "keep_voided_discard_coin", f"ポケモン {pokemon.pokemon_id}（［KEEP］でなくなるエネルギーカードのトラッシュだけを決めるコイン）"
        if first_void(run.res, run.incoming(), owner, pokemon, Window.BEFORE_EFFECT) is not None:
            return "prevented_effect_coin", f"ポケモン {pokemon.pokemon_id}（「ワザをうけない」ポケモンのエネルギーカードのトラッシュだけを決めるコイン）"
        if E.evasion_power(run.state, pokemon) is not None and run.fs.reception.get(pokemon.pokemon_id) is not True:
            return "evaded_effect_coin", f"ポケモン {pokemon.pokemon_id}（ダメージの要素で「とうめい」の「おもて」なら、エネルギーカードのトラッシュだけを決めるコインを投げるかが決められない）"
        return None

    def _next(self, run: AttackRun, queue: list[int]) -> bool:
        opponent = 1 - run.player
        while queue:
            pid = queue.pop(0)
            found = run.state.find_pokemon(pid)
            if found is None or found[0] != opponent:
                continue
            target = found[1]
            if run.knocked_out(target) or not self._energy(run, target):
                continue
            if not reaches(run.res, run.fs, opponent, target, E.ENERGY_DISCARD_ELEMENT):
                continue
            void = self._voided(run, target)
            if void is not None:
                # v0.101: ［KEEP］でトラッシュする効果がなくなる（選ばせない・トラッシュしない。手札にもどるかの問い（TE2 など）も聞かない）。ほかのポケモンへの効果は続ける
                E.note_energy_discard_voided(run.state, void, cause=E.DISCARD_BY_ATTACK, by_player=run.player, effect=str(run.key))
                continue
            options = self._energy(run, target)
            # v0.83: 手札にもどるかが TE2 の答えで変わるカード（エコロジムと［へんしん］のメタモンの無色の特殊エネルギー）は、選べるが選ぶと止める。どれもそうなら止める
            problems = {uid: E.energy_discard_problem(run.state, target, uid, cause=E.DISCARD_BY_ATTACK, by_player=run.player) for uid in options}
            blocked = tuple(uid for uid in options if problems[uid] is not None)
            if blocked and len(blocked) == len(options):
                raise UnsupportedError(*problems[blocked[0]])
            code, reason = problems[blocked[0]] if blocked else (None, None)
            run.suspend(kind=DISCARD_OPPONENT_ENERGY, player=run.player, options=options,
                        extra=(("target", pid), ("queue", tuple(queue))) + _unresolved_extra(blocked, code, reason), carry=True)
            return True
        return False

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ()))  # v0.83: 選ぶと止めるカード（TE2）は試さない
        return [answer for answer in all_answers(decision) if not blocked & set(answer)]

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        opponent = 1 - run.player
        pid = run.carried["target"]
        queue = list(run.carried.get("queue", ()))
        found = run.state.find_pokemon(pid)
        if found is None or found[0] != opponent or choices[0] not in found[1].energy:
            raise RuntimeError(f"トラッシュに選んだカード {choices} が、相手のポケモン {pid} についていない（エンジンの不具合）")
        target = found[1]
        energy = choices[0]
        attacker = run.attacker()
        E.discard_energy_from_play(  # v0.82: 相手のワザでトラッシュ（リサイクルエネルギー・エコロジム）
            run.state, target, (energy,), cause=E.DISCARD_BY_ATTACK, by_player=run.player,
            log=lambda: run.state.add_event("discard_attached_energy", player=opponent, pokemon=target.card, pokemon_id=target.pokemon_id, energy=energy,
                                            effect=str(run.key), attacker=run.player, attacker_pokemon_id=attacker.pokemon_id))
        self._next(run, queue)


@dataclass(frozen=True)
class HealSelfOnHeads(Element):
    """コインを投げて「おもて」なら、このカードからダメージカウンターを ``counters`` 個とりのぞく（v0.31。化石の秘密のヤドンの「ぼーっとする」。
    「このカードにダメージカウンターがのってない時には、このワザは使えない」は、ワザを使うための条件（``checks.attack_request`` が実装の
    ``usage_problem`` で確かめる）。"""

    counters: int = 1
    requires_damage: bool = True
    phase: ClassVar[Phase] = Phase.EFFECT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        if self.requires_damage and copier.damage == 0:
            return (ILLEGAL if clause in (CANNOT_USE, FOLLOW_TEXT) else UNRESOLVED), "ダメージカウンターがのっていない（ワザを使うための条件）"
        return None

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                element="heal", reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        if run.flip(1).results[0] is not HEADS:
            return False
        per = run.state.rules.damage_per_counter
        before = attacker.damage
        removed = min(self.counters, before // per)
        attacker.damage = before - removed * per
        run.state.add_event("attack_heal", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            counters=removed, amount=removed * per, damage_before=before, total_damage=attacker.damage)
        return False


@dataclass(frozen=True)
class RecoverTrainer(Element):
    """自分のトラッシュの中からトレーナーカードを 1 枚選び、手札に加える（v0.31。化石の秘密のヤドンの「ゴミあさり」）。トラッシュにトレーナーカードが
    なければ、処理の対象がないので何もしない（p.309。H5 と同じ）。"""

    requires: str | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = RECOVER_TRAINER
    discard_protected = _discard_protected

    @staticmethod
    def _candidates(run: AttackRun) -> list[int]:
        return [uid for uid in run.state.players[run.player].discard if run.state.card_def(uid).category == "trainer"]

    def run(self, run: AttackRun) -> bool:
        if self.requires is not None:
            discarded = run.fs.results.get(self.requires)
            if discarded is not None and discarded.outcome != "done":
                return False
        if suppressed_discard_to_hand(run):
            return False  # v0.74: ポケモンタワー（エネルギーのトラッシュはすんでいて、取り消さない）
        if protected_discard(run, "recover_trainer"):
            return False  # v0.119: ［アレルギーほうし］（エネルギーのトラッシュは取り消さない）
        candidates = self._candidates(run)
        if not candidates:
            return False
        run.suspend(kind=RECOVER_TRAINER, player=run.player, options=candidates)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if choices[0] not in self._candidates(run):
            raise RuntimeError(f"手札に加えるカード {choices} が、トラッシュのトレーナーカードではない（エンジンの不具合）")
        return_discard_to_hand(run.state, run.player, tuple(choices))
        attacker = run.attacker()
        run.state.add_event("recover_trainer", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            card=choices[0])


@dataclass(frozen=True)
class Draw(Element):
    """山札からカードを ``count`` 枚引く（v0.31。わるいゴルダックの「だい3のめ」・第4弾のコダックの「めまい」・カスミのコダックの「ちょうのうりょく」）。
    山札が足りなければ引けるだけ引く（効果で引くときの規定。p.312。v0.2b のマサキと同じ）。

    v0.112: ``heads_of`` はワザ全体のコイン（``Coin``）の名前で、引く枚数はその「おもて」の数 × ``per_heads``（ドククラゲ・オムスターの「しょくしゅをつかう」。``count`` は書かない）。
    コインをすべて投げて確定したあとの要素なので、ナツメのESPのやり直しの決定の前には引かない。投げなかったコイン（0 枚）は 0 枚。"""

    count: int | None = None
    gate: tuple | None = None
    requires: str | None = None
    heads_of: str | None = None
    per_heads: int = 1
    phase: ClassVar[Phase] = Phase.EFFECT
    reads_deck_order: ClassVar[bool] = True  # v0.40: 山札の上から引く

    def __post_init__(self) -> None:
        if (self.count is None) == (self.heads_of is None):
            raise ValueError("引く枚数は count・heads_of のどちらか 1 つで決める")
        if self.count is not None and (type(self.count) is not int or self.count < 0):
            raise ValueError(f"引く枚数 {self.count!r} は 0 以上の整数")
        if type(self.per_heads) is not int or self.per_heads < 1 or (self.per_heads != 1 and self.heads_of is None):
            raise ValueError(f"「おもて」1 枚あたりの枚数 {self.per_heads!r} は、heads_of のときだけの正の整数")

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        if self.requires is not None:
            discarded = run.fs.results.get(self.requires)
            if discarded is not None and discarded.outcome != "done":
                return False
        wanted = self.count if self.heads_of is None else run.heads(self.heads_of) * self.per_heads
        draw_cards(run.state, run.player, min(wanted, len(run.state.players[run.player].deck)))
        return False


def attach_prevented(run: AttackRun, pokemon: PokemonInPlay, element: str) -> bool:
    """v0.59: ワザの効果でエネルギーカードをつける先 ``pokemon`` が、クリスタルビームの効果（次の相手の番、エネルギーカードをつけることができない）を受けているなら、つけずに
    ログ ``effect_skipped``（``reason`` は ``attach_prevented``）を残して真。手札・山札・トラッシュからつけるのは「つける」こと（場のエネルギーのつけかえとは別。CB1）。"""
    if E.energy_attach_block(run.state, pokemon) is None:
        return False
    run.state.add_event("effect_skipped", player=run.player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, effect=str(run.key),
                        element=element, reason="attach_prevented")
    return True


@dataclass(frozen=True)
class AttachFromDiscard(Element):
    """自分のトラッシュに ``energy_type`` の基本エネルギーカードがあれば、最大 ``max_cards`` 枚を取り出して、自分（ワザを使ったポケモン）につける
    （v0.31。マチスのエレブーの「たいでん」）。なければ何もしない（「あれば」）。0 枚を選べるかは決められない（HC7。答えのときに止める）。"""

    energy_type: EnergyType | None  # v0.75: None は「エネルギーカード」（種類・タイプを問わない。ミュウツーの「エネルギーきゅうしゅう」）
    max_cards: int
    # v0.45: ちょうど ``max_cards`` 枚（R団のサンダーの「プラズマ」の「あれば、1枚取り出して」。0 枚は選べない）。v0.31 の「たいでん」は「最大2枚」（0 枚は HC7）
    exact: bool = False
    # v0.113: 選べるカードを、場の外のカードとしての種類・色で決める（``effects.off_field_typed_energy_card``。その色の基本エネルギーカードと、出すエネルギーがどれもその色 1 色の特殊エネルギー
    # カード（悪エネルギーの「このカードは「悪」エネルギー1個ぶんとしてあつかう。」）。特殊エネルギーを基本エネルギーカードにはしない）。ヘルガー（neo3-044）の「ダークフレイム」の
    # 「自分のトラッシュに「悪」エネルギーカードがあれば」（「悪」の基本エネルギーカードはない）。偽（既定）なら、その色の基本エネルギーカードだけ（v0.31〜v0.112 と同じ）。レインボー
    # エネルギーはどちらも RB2、ミラクルエネルギー（場の外では色がない。v0.85）はどちらも選べない
    typed_cards: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = ATTACH_FROM_DISCARD
    discard_protected = _discard_protected

    def __post_init__(self) -> None:
        if self.typed_cards and (self.energy_type is None or self.energy_type is EnergyType.COLORLESS):
            raise ValueError("場の外の種類・色で選ぶ（typed_cards）のは、「無色」以外の色のエネルギーカード")

    def _candidates(self, run: AttackRun) -> list[int]:
        if self.energy_type is None:
            # v0.75: ミュウツー（PR1-007・PR1-008）の「エネルギーきゅうしゅう」の「エネルギーカード」（種類・タイプを問わない。特殊エネルギーも 1 枚。カードの枚数で数える）。
            # 色を選ぶ効果ではないので RB2 に当たらない
            # v0.85: つける先の制限のある特殊エネルギー（ミラクルエネルギー）は、つける先（このカード）につけられるものだけ
            return [uid for uid in run.state.players[run.player].discard if run.state.card_def(uid).category == "energy"
                    and E.energy_attach_target_allowed(run.state, uid, run.attacker())]
        rainbow_attach_question(run, run.state.players[run.player].discard, self.energy_type)  # v0.58: RB2
        if self.typed_cards:
            return [uid for uid in run.state.players[run.player].discard if E.off_field_typed_energy_card(run.state, uid, self.energy_type)
                    and E.energy_attach_target_allowed(run.state, uid, run.attacker())]
        return [uid for uid in run.state.players[run.player].discard
                if run.state.card_def(uid).is_basic_energy and run.state.card_def(uid).provides is self.energy_type]

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            # v0.45: 処理の対象（ワザを使ったポケモン）が、ダメージの要素のあとの相手の「はんげき」などで HP 以上（p.309。C16 と同じ。「プラズマ」）。v0.31 の
            # 「たいでん」はダメージの要素がないので起こらない
            run.state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                element="attach_from_discard", reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        if attach_prevented(run, attacker, "attach_from_discard"):
            return False
        if protected_discard(run, "attach_from_discard"):
            return False  # v0.119: ［アレルギーほうし］（つけるカードを決めないので、RB2 にも当たらない）
        candidates = self._candidates(run)
        if not candidates:
            return False
        count = min(self.max_cards, len(candidates))
        run.suspend(kind=ATTACH_FROM_DISCARD, player=run.player, options=candidates, min_choices=count if self.exact else 0, max_choices=count)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if not choices:
            if self.energy_type is None:
                raise UnsupportedError(
                    "UNRESOLVED_ATTACH_FROM_DISCARD_ZERO",
                    f"トラッシュにエネルギーカードがあるときに 0 枚を選べるか（「エネルギーカードを最大{self.max_cards}枚選び、このカードにつける」が 0 枚を含むか）は"
                    "決められないので扱わない（v0.31 の HC7 と同じ問い）。1 枚以上を選ぶ",
                )
            raise UnsupportedError(
                "UNRESOLVED_ATTACH_FROM_DISCARD_ZERO",
                "トラッシュに「雷」エネルギーカードがあるときに 0 枚を選べるか（「最大2枚を取り出して」が 0 枚を含むか）は決められないので扱わない（HC7）。"
                "1 枚以上を選ぶ",
            )
        candidates = self._candidates(run)
        if any(uid not in candidates for uid in choices):
            raise RuntimeError(f"つけるカード {choices} が、トラッシュの選べるエネルギーカードではない（エンジンの不具合）")
        cards = tuple(uid for uid in run.state.players[run.player].discard if uid in choices)  # トラッシュの並びの順につける（選んだ順によらない）
        attacker = run.attacker()
        attach_from_discard(run.state, run.player, cards, attacker)
        run.state.add_event("attach_energy_from_discard", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                            effect=str(run.key), cards=cards)
        for uid in cards:
            attached_in_attack(run, run.player, attacker, (uid,))

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return combinations_answers(decision, range(1, decision.max_choices + 1))  # 0 枚は答えのときに止める（HC7）


@dataclass(frozen=True)
class MoveOwnEnergyToBench(Element):
    """このカードについているエネルギーカードをすべてはがし、自分の控えポケモンに好きなようにつける。自分に控えがいない時、エネルギーカードは
    トラッシュする（v0.31。わるいマルマインの「エナジーボム」）。1 枚ずつ（ついている順）、ワザを使ったプレイヤーがつける控えポケモンを選ぶ。

    控えポケモンにエネルギーをつけるのはワザの効果なので、つけるポケモンの「とうめい」を評価し、「おもて」ならそのエネルギーカードはトラッシュする
    （kyuura の CR-TRANSPARENCY-ENERGY-BOMB。エンジンの T36。確実）。つけたら、つけた先の「炎」エネルギーカードをつけたときの特殊能力をはたらかせる
    （``effects.after_energy_attached``）。処理の対象（このカード）が、相手の「はんげき」などで HP 以上なら何もしない（p.309。C16 と同じ）。"""

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = ATTACH_TO_BENCH

    def run(self, run: AttackRun) -> bool:
        state = run.state
        attacker = run.attacker()
        if run.knocked_out(attacker):
            state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            element="move_energy", reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        energies = tuple(attacker.energy)
        if not energies:
            return False
        if not state.players[run.player].bench:
            for uid in energies:
                E.discard_energy_from_play(  # v0.82: リサイクルエネルギー
                    state, attacker, (uid,), cause=E.DISCARD_BY_ATTACK, by_player=run.player,
                    log=lambda uid=uid: state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                                        effect=str(run.key), energy=uid, reason="no_bench"))
            return False
        return self._next(run, energies)

    @staticmethod
    def _next(run: AttackRun, energies: tuple[int, ...]) -> bool:
        if not energies:
            return False
        run.suspend(kind=ATTACH_TO_BENCH, player=run.player, options=[p.pokemon_id for p in run.state.players[run.player].bench],
                    extra=(("energy", energies[0]), ("remaining", energies[1:])), carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        energy = run.carried["energy"]
        remaining = tuple(run.carried.get("remaining", ()))
        attacker = run.attacker()
        target = next((p for p in state.players[run.player].bench if p.pokemon_id == choices[0]), None)
        if energy not in attacker.energy or target is None:
            raise RuntimeError(f"つけかえるエネルギー {energy}・控えポケモン {choices} が正しくない（エンジンの不具合）")
        returns = E.energy_discard_plan(state, attacker, (energy,), cause=E.DISCARD_BY_ATTACK, by_player=run.player)  # v0.82: トラッシュに置くときだけ使う
        attacker.energy.remove(energy)
        if reaches(run.res, run.fs, run.player, target, E.ENERGY_ATTACH_ELEMENT):
            target.energy.append(energy)
            state.add_event("attack_attach_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy=energy, to_pokemon_id=target.pokemon_id)
            attached_in_attack(run, run.player, target, (energy,), moved=True)
        else:
            state.players[run.player].discard.append(energy)  # 「とうめい」の「おもて」: エネルギーカードはトラッシュ（CR-TRANSPARENCY-ENERGY-BOMB）
            state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy=energy, reason="evaded", to_pokemon_id=target.pokemon_id)
            E.return_discarded_energy(state, returns)  # 場（ワザを使ったポケモン）からトラッシュに置かれた
        self._next(run, remaining)


@dataclass(frozen=True)
class MillOwnDeck(Element):
    """自分の山札の上から、カードを ``count`` 枚トラッシュする（v0.31。カツラのブーバーの「マグマふんしゅつ」）。山札が足りなければ決められない
    （HC6。宣言の前に止める）。"""

    count: int
    name: str = "mill"
    phase: ClassVar[Phase] = Phase.EFFECT
    reads_deck_order: ClassVar[bool] = True  # v0.40: 山札の上からトラッシュする

    def run(self, run: AttackRun) -> bool:
        deck = run.state.players[run.player].deck
        if len(deck) < self.count:
            raise run.res.question("deck_short", f"山札 {len(deck)} 枚から {self.count} 枚")
        cards = discard_from_deck(run.state, run.player, self.count)
        attacker = run.attacker()
        run.state.add_event("discard_from_deck", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            cards=cards)
        run.fs.results[self.name] = Discarded(cards)
        return False


@dataclass(frozen=True)
class MillOpponentDeck(Element):
    """トラッシュの要素 ``from_discard`` でトラッシュしたのと同じ枚数のカードを相手の山札の上から取り、相手のトラッシュにすてる（v0.31。ファイヤーの
    「やまやき」）。枚数が相手の山札より多い答えは、トラッシュの要素の答えのときに止めている（HC6）。

    v0.115（docs/spread-damage-allocation-v0.115.md 6 章）: ``heads_of`` なら、ワザ全体のコインの「おもて」の数だけ（わるいバンギラスの「やまくだき」の「その後、「おもて」の数ぶんの
    カードを、相手の山札の上からトラッシュする」。ダメージと同じ確定したコインの結果。ダメージが無効でもトラッシュする）。相手の山札がその数より少なければ HC6（``deck_short``。山札の
    上から決まった枚数をトラッシュする効果で足りない場合。コインのあとに分かるので、先読みがコインのすべての結果を試して宣言の前に止める）。相手のポケモンへの効果ではない"""

    from_discard: str = "discard"
    heads_of: str | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    reads_deck_order: ClassVar[bool] = True  # v0.40: 相手の山札の上からトラッシュする

    def run(self, run: AttackRun) -> bool:
        if self.heads_of is not None:
            count = run.heads(self.heads_of)
        else:
            discarded = run.fs.results.get(self.from_discard)
            count = 0 if discarded is None else len(discarded.cards)
        if count == 0:
            return False
        opponent = 1 - run.player
        if len(run.state.players[opponent].deck) < count:
            if self.heads_of is not None:
                raise run.res.question("deck_short", f"相手の山札 {len(run.state.players[opponent].deck)} 枚から {count} 枚（「おもて」の数）")
            raise RuntimeError(f"相手の山札が {count} 枚ない（答えのときに止めるはず。エンジンの不具合）")
        cards = discard_from_deck(run.state, opponent, count)
        attacker = run.attacker()
        run.state.add_event("discard_from_deck", player=opponent, effect=str(run.key), cards=cards, attacker=run.player,
                            attacker_pokemon_id=attacker.pokemon_id)
        return False


@dataclass(frozen=True)
class OptionalDiscardBenchDamage(Element):
    """「のぞむなら、このカードについている ``energy_type`` エネルギーカードを1枚トラッシュし、その後、相手の控えポケモンを1匹選んで（「弱点・抵抗力」に
    関係なく）``damage`` ダメージを与えてもよい」（v0.31。わるいギャロップの「ひばしら」）。決定は 2 つ: トラッシュするカード（0 枚ならしない）→
    控えポケモン（相手に控えがいなければ、処理の対象がないのでダメージはない。p.309）。トラッシュとダメージを 1 つの「のぞむなら」として扱う。"""

    energy_type: EnergyType
    damage: int
    phase: ClassVar[Phase] = Phase.EFFECT
    guards_bench: ClassVar[bool] = True  # v0.65

    def decides(self, kind: str) -> bool:
        return kind in (DISCARD_ENERGY, SELECT_POKEMON, BENCH_GUARD)

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                element="discard_energy", reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        transform_energy_question(run, attacker, self.energy_type, cards=True)  # v0.49: TE1
        candidates = E.attached_basic_energy(run.state, attacker, self.energy_type)
        if not candidates:
            return False
        run.suspend(kind=DISCARD_ENERGY, player=run.player, options=candidates, min_choices=0, max_choices=1, carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        if decision.kind == DISCARD_ENERGY:
            if not choices:
                return
            _owner, attacker = state.find_pokemon(run.fs.frame.source_pid)
            if choices[0] not in E.attached_basic_energy(state, attacker, self.energy_type):
                raise RuntimeError(f"トラッシュに選んだカード {choices} が、ワザを使ったポケモンについていない（エンジンの不具合）")
            E.discard_energy_from_play(  # v0.82: リサイクルエネルギー
                state, attacker, (choices[0],), cause=E.DISCARD_BY_ATTACK, by_player=run.player,
                log=lambda: state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                            energy=choices[0]))
            bench = state.players[1 - run.player].bench
            if not bench:
                return
            run.suspend(kind=SELECT_POKEMON, player=run.player, options=[p.pokemon_id for p in bench], carry=True)
            return
        guarded_damages(run, self, [(E.OPPONENT_BENCH, choices[0], self.damage, False)])  # v0.65: ［ベンチガード］


@dataclass(frozen=True)
class CopyOpponentAttack(Element):
    """相手の対戦ポケモンのワザの中から 1 つを選び、それを自分のワザとして使う（v0.31。ピクシー・ピッピの「ゆびをふる」、カスミのコダックの
    「ちょうのうりょく」の「おもて」が 3 枚）。選んだワザの要素の並びを、このワザの枠の中で、ワザを使ったポケモンのワザとして処理する（弱点・抵抗力は
    ワザを使ったポケモンのタイプ。``run.redirect``）。

    - 必要なエネルギーはいらない（3 つの説明がどれも「必要なエネルギーがついていなくても、かまわない」。ピッピは kyuura の記録の最新の説明）
    - ``clause``: ``CANNOT_USE``（ピクシー。「ほかに必要な条件（エネルギーカードをはがしてすてるなど）がたりないときには使えない」）・``FOLLOW_TEXT``
      （ピッピ。p.223 の解説「ワザに必要なエネルギー以外はワザの説明にしたがう」。kyuura の card_differences の記録）・None（カスミのコダック。
      ほかの条件を書いていない）。使うワザの条件がたりないときに選べるか（``Element.copy_problem``）を決める
    - 選べるもの: 相手の対戦ポケモンのワザ（使えないもの（``ILLEGAL``）は除く）。処理を決められないもの・エンジンが対応していないものは選べるが、
      選ぶと止める（``unresolved_choices``・``context`` の ``"unsupported_choices"``）。処理できるワザがなければ問い（HC9）。相手の対戦ポケモンに
      ワザがなければ、処理の対象がないので何もしない（p.309）。
    """

    clause: str | None = None
    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_ATTACK

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        return UNRESOLVED, "相手のワザを自分のワザとして使うワザを、さらに自分のワザとして使う"

    def _status(self, run: AttackRun, definition, attack) -> tuple[str, str] | None:
        return copy_status(run, definition, attack, self.clause)

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        source = run.opponent_active()
        # v0.49: 相手の対戦ポケモンが今持つワザ（``E.held_attack_keys``。今の姿のカード（［へんしん］・「ばける」）・［サイコリンク］で持つワザを含む。ワザごとに 1 つ）。
        # 並びがいちばん上のカードのワザと同じなら、決定の形は v0.48 と同じ（選べるものはワザの位置・``copy_from``）。違えば、選べるものは並びの位置で、
        # ``copy_attacks`` に (カードの id, ワザの位置) の並びを書く
        entries, legacy = E.held_attack_keys(run.state, source)
        if not entries:
            return False
        attacks = [E.attack_of(run.state, key) for key, _ in entries]
        statuses = {i: self._status(run, run.state.definitions[key.card_id], attacks[i]) for i, (key, _) in enumerate(entries)}
        held = {i: problem for i, (_, problem) in enumerate(entries) if problem is not None and statuses[i] is None}  # VS1（持つかが読み方で変わる）
        label = run.state.card_def(source.card).id if legacy else E.form_def(run.state, source).id
        options = [i for i, status in statuses.items() if status is None or status[0] != ILLEGAL]
        if not any(status is None for status in statuses.values()):
            detail = "・".join(f"{attacks[i].name_ja}: {status[1]}" for i, status in statuses.items())
            if any(status[0] == UNSUPPORTED for status in statuses.values()):
                # 処理できるワザがなく、そのうちエンジンが対応していないワザがある（ルールの問いではない）
                raise run.res.question("copied_attack_unsupported", f"{label}（{detail}）")
            raise run.res.question("copied_attack", f"{label}（{detail}）")
        unresolved = tuple(i for i in options if statuses[i] is not None and statuses[i][0] == UNRESOLVED)
        unsupported = tuple(i for i in options if statuses[i] is not None and statuses[i][0] == UNSUPPORTED)
        if legacy:
            extra: tuple = (("copy_from", label),)
        else:
            extra = (("copy_attacks", tuple((key.card_id, key.attack_index) for key, _ in entries)),)
        if unresolved or held:
            reason = "・".join(f"{attacks[i].name_ja}: {statuses[i][1]}" for i in unresolved)
            extra += (("unresolved_choices", tuple(sorted(unresolved + tuple(held)))), ("unresolved_code", "UNRESOLVED_COPIED_ATTACK"),
                      ("unresolved_reason", f"相手のワザを自分のワザとして使うとき、処理が決められない（HC9。{reason}）"))
        if held:
            extra += (("unresolved_detail", tuple((i, problem[0], f"相手のワザ「{attacks[i].name_ja}」: {problem[1]}") for i, problem in sorted(held.items()))),)
        if unsupported:
            extra += (("unsupported_choices", unsupported),)
        run.suspend(kind=SELECT_ATTACK, player=run.player, options=options, extra=extra)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        index = choices[0]
        if "copy_attacks" in run.carried:
            card_id, index = run.carried["copy_attacks"][index]  # v0.49: 選べるものは並びの位置
        else:
            card_id = run.carried["copy_from"]
        definition = run.state.definitions[card_id]
        attack = definition.attacks[index]
        status = self._status(run, definition, attack)
        if status is not None:
            code = "UNSUPPORTED_COPIED_ATTACK" if status[0] == UNSUPPORTED else "UNRESOLVED_COPIED_ATTACK"
            raise UnsupportedError(code, f"相手のワザ「{attack.name_ja}」を自分のワザとして使えない（{status[1]}）")
        effect = run.state.effects.attack_effect(definition.id, attack, definition.attacks)
        attacker = run.attacker()
        key = E.AttackKey(card_id, index)
        run.state.add_event("copy_attack", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.declared),
                            copied=str(key), copied_attack=attack.name_ja)
        run.redirect = (key, attack, BUILDERS[type(effect)](effect))

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ())) | set(decision.context_value("unsupported_choices", ()))
        return [(index,) for index in decision.options if index not in blocked]


def copy_status(run: AttackRun, definition, attack, clause: str | None) -> tuple[str, str] | None:
    """ほかのワザ ``attack``（カードの定義 ``definition``）を、ワザを使ったポケモンのワザとして使えるか（v0.31 の ``CopyOpponentAttack`` から分けた。v0.62 からピジョンの
    「オウムがえし」と共通）。使える（None）・(``ILLEGAL``・``UNRESOLVED``・``UNSUPPORTED``, 理由の文)。``clause`` は説明が書く条件（``Element.copy_problem``）。"""
    effect = run.state.effects.attack_effect(definition.id, attack, definition.attacks)
    if effect is None:
        return UNSUPPORTED, "効果の実装が登録されていない"
    if effect.once_after_entering_play:
        # v0.44: 「このワザは、このカードが場に出てから、1回しか使えない」ワザ。使った記録はワザを持つカードのワザの位置（``PokemonInPlay.attacks_used_once``）
        # なので、まねたポケモンの記録を表せない（エンジンの未対応。v0.36 のドわすれと同じ扱い）
        return UNSUPPORTED, "場に出てから1回しか使えないワザの使った記録を、ワザを持つカードのワザの位置で持つので、まねたポケモンの記録を表せない"
    builder = BUILDERS.get(type(effect))
    if builder is None:
        return UNSUPPORTED, f"実装 {type(effect).__name__} に解決の基盤の要素の並びがない"
    copier = run.attacker()
    for element in builder(effect):
        problem = element.copy_problem(run, copier, clause)
        if problem is not None:
            return problem
    return None


@dataclass(frozen=True)
class CopyChosenAttack(CopyOpponentAttack):
    """v0.120（docs/fossil-basic-virtual-attacks-v0.120.md 5 章）: ワザを 1 つ選び、それを自分のワザとして使う（実装 ``effects.CopyAttackFromSource``）。v0.31 の ``CopyOpponentAttack`` と
    同じく、選んだワザの要素の並びを、このワザの枠の中で、ワザを使ったポケモンのワザとして処理する（``run.redirect``。弱点・抵抗力・「このカード」はワザを使ったポケモン）。

    - ``source``: 選べるワザの範囲（``E.copy_source_entries``。相手の対戦ポケモン・相手の場にいるポケモン・自分が進化する前に持っていたワザ）。決定の続きの情報は ``copy_source`` と
      ``copy_attacks``（(カードの id, 位置) の並び。選べるものは並びの位置）
    - ``cost``: ``E.COPY_COST_COMBINED`` なら、宣言したワザの必要なエネルギーに選んだワザの必要なエネルギーを合わせて、ワザを使うポケモンのエネルギーで照らす（別々にではない。
      ``E.combined_cost_attack``）。払えないワザは選べない（説明が「使えない」とする）。エネルギーはトラッシュしない
    - 選んだワザの条件（``copy_status``）: 説明が「使えない」とする（``ILLEGAL``）ワザは選べない。決まらない（``UNRESOLVED``）ワザは選べるが選ぶと止める（``condition_code``。相手のワザは
      HC9、自分の進化前のワザは PE2）。範囲のワザの止める理由（VS1・VP1・PE1）も選ぶと止める（選択ごとの理由 ``unresolved_detail``）。エンジンが対応していないワザは選べるが選ぶと止める
    - コインで選ぶワザ（``gate``）は、コインのあとに選ぶ（ESPのやり直しで確定する前に候補を確かめない。再開ではコインを投げ直さない）。選べるワザがなければ、処理の対象がないので何も
      しない（p.309。``has_target`` も偽で、コインは投げない）。止めないワザが 1 つもなければ、宣言の前に止める
    """

    source: str = E.COPY_FROM_DEFENDER
    cost: str = E.COPY_COST_EXEMPT
    condition_code: str = "UNRESOLVED_COPIED_ATTACK"

    def entries(self, run: AttackRun) -> list[tuple[E.AttackKey, tuple[str, str] | None]]:
        return E.copy_source_entries(run.state, run.player, run.attacker(), self.source)

    def has_target(self, run: AttackRun) -> bool:
        return bool(self.entries(run))

    def choice_status(self, run: AttackRun, key: E.AttackKey, held: tuple[str, str] | None) -> tuple[str, str, str | None] | None:
        """選んだワザ ``key`` の (種類, 理由, 止めるコード)。選べて止めないなら None。種類は ``ILLEGAL``（選べない）・``UNRESOLVED``（選ぶと止める）・``UNSUPPORTED``。"""
        definition = run.state.definitions[key.card_id]
        attack = definition.attacks[key.attack_index]
        status = copy_status(run, definition, attack, self.clause)
        if status is not None:
            return status[0], status[1], self.condition_code if status[0] == UNRESOLVED else None
        if self.cost == E.COPY_COST_COMBINED:
            combined = E.combined_cost_attack(run.attack, attack)
            problem = E.attack_cost_problem(run.state, run.attacker(), combined)
            if problem is not None:
                return UNRESOLVED, problem.message, problem.code
            if not E.attack_cost_payable(run.state, run.attacker(), combined):
                return ILLEGAL, f"「{run.attack.name_ja}」に必要なエネルギーに加えて、「{attack.name_ja}」に必要なエネルギーがついていない", None
        if held is not None:
            return UNRESOLVED, held[1], held[0]
        return None

    def choices(self, run: AttackRun, entries) -> tuple[list[int], dict[int, tuple[str, str]], set[int]]:
        """選べるもの（並びの位置。選べないワザを除く）・選ぶと止めるもの {位置: (コード, 理由)}・エンジンが対応していないもの。"""
        options: list[int] = []
        stops: dict[int, tuple[str, str]] = {}
        unsupported: set[int] = set()
        for i, (key, held) in enumerate(entries):
            status = self.choice_status(run, key, held)
            if status is not None and status[0] == ILLEGAL:
                continue
            options.append(i)
            if status is None:
                continue
            name = E.attack_of(run.state, key).name_ja
            if status[0] == UNSUPPORTED:
                unsupported.add(i)
            else:
                stops[i] = (status[2], f"「{name}」: {status[1]}")
        return options, stops, unsupported

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        entries = self.entries(run)
        if not entries:
            return False
        options, stops, unsupported = self.choices(run, entries)
        detail = "・".join(f"{reason}（{code}）" for code, reason in stops.values())
        if not [i for i in options if i not in stops and i not in unsupported]:
            if not options:
                # 選べるワザがない（どれも説明が「使えない」とする）。宣言の前の確かめ（``combined_copy_usage_problem``）が拒否するので、ここには来ない
                raise RuntimeError(f"ワザを選ぶワザ {run.declared} で、選べるワザがない（宣言の前の確かめの漏れ。エンジンの不具合）")
            if unsupported and not stops:
                raise run.res.question("copied_attack_unsupported", f"範囲 {self.source}（{len(unsupported)} のワザが未対応）")
            code = stops[min(stops)][0]
            if code == "UNRESOLVED_COPIED_ATTACK":
                raise run.res.question("copied_attack", f"範囲 {self.source}（{detail}）")
            raise UnsupportedError(code, f"選べるワザがどれも選ぶと止めるもの（範囲 {self.source}。{detail}）")
        extra: tuple = (("copy_source", self.source), ("copy_attacks", tuple((key.card_id, key.attack_index) for key, _ in entries)))
        if stops:
            first = stops[min(stops)]
            extra += (("unresolved_choices", tuple(sorted(stops))), ("unresolved_code", first[0]), ("unresolved_reason", f"選ぶワザの処理が決められない（{detail}）"),
                      ("unresolved_detail", tuple((i, code, reason) for i, (code, reason) in sorted(stops.items()))))
        if unsupported:
            extra += (("unsupported_choices", tuple(sorted(unsupported))),)
        run.suspend(kind=SELECT_ATTACK, player=run.player, options=options, extra=extra)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        card_id, index = run.carried["copy_attacks"][choices[0]]
        key = E.AttackKey(card_id, index)
        held = dict(self.entries(run)).get(key)
        status = self.choice_status(run, key, held)
        definition = run.state.definitions[card_id]
        attack = definition.attacks[index]
        if status is not None:
            code = "UNSUPPORTED_COPIED_ATTACK" if status[0] == UNSUPPORTED else (status[2] or "UNRESOLVED_COPIED_ATTACK")
            raise UnsupportedError(code, f"ワザ「{attack.name_ja}」を自分のワザとして使えない（{status[1]}）")
        effect = run.state.effects.attack_effect(definition.id, attack, definition.attacks)
        attacker = run.attacker()
        run.state.add_event("copy_attack", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.declared),
                            copied=str(key), copied_attack=attack.name_ja, copy_source=self.source)
        run.redirect = (key, attack, BUILDERS[type(effect)](effect))


def combined_copy_usage_problem(state: GameState, attacker: PokemonInPlay, effect) -> Exception | None:
    """v0.120: 必要なエネルギーを合わせるワザ（ミュウの「サイコデュープ」。``E.CopyAttackFromSource`` の ``COPY_COST_COMBINED``）を宣言できるか（ワザを使うための条件。``checks.attack_request``
    の ``usage_problem``）。選べるワザ（合わせた必要なエネルギーを払え、説明が使えないとしないもの）が 1 つもなければ使えない（「…ついていない限り、「サイコデュープ」は使えない」「ほかに
    必要な条件…が満たせない時にも使えない」）。払えるワザがなければ ``INSUFFICIENT_ENERGY``、払えても条件をみたすワザがなければ ``COPIED_ATTACK_CONDITIONS``。状態は変えない
    （確かめのための複製の上で、要素の ``choice_status`` を使う）。"""
    located = state.find_pokemon(attacker.pokemon_id)
    if located is None:
        return None
    owner = located[0]
    probe = state.peek()
    user = probe.find_pokemon(attacker.pokemon_id)[1]
    key = next((option.key for option in E.available_attacks(state, attacker)
                if state.effects.attack_effect(option.card_id, E.attack_of(state, option.key), state.definitions[option.card_id].attacks) == effect), None)
    if key is None:
        return None
    attack = E.attack_of(state, key)
    res = Resolution(probe)
    fs = res.open_frame(FrameKind.ATTACK, parent=None, player=owner, source_pid=user.pokemon_id, attack_key=key)
    element = CopyChosenAttack(effect.clause, source=effect.source, cost=effect.cost)
    run = AttackRun(res, fs, (element,), attack)
    entries = element.entries(run)
    statuses = [element.choice_status(run, entry_key, held) for entry_key, held in entries]
    if any(status is None or status[0] != ILLEGAL for status in statuses):
        return None
    payable = [entry_key for (entry_key, _), status in zip(entries, statuses, strict=True)
               if E.attack_cost_payable(state, attacker, E.combined_cost_attack(attack, E.attack_of(state, entry_key)))]
    if not payable:
        return IllegalActionError("INSUFFICIENT_ENERGY", f"ワザ「{attack.name_ja}」: 必要なエネルギーに加えて選べるワザに必要なエネルギーがついていない（選べるワザ {len(entries)}）")
    return IllegalActionError("COPIED_ATTACK_CONDITIONS", f"ワザ「{attack.name_ja}」: 必要なエネルギーを払える相手のワザ {[str(k) for k in payable]} は、どれもほかに必要な条件を満たせない")


# ---------------------------------------------------------------- v0.120（docs/fossil-basic-virtual-attacks-v0.120.md 7 章）


@dataclass(frozen=True)
class HeadsPlusPokemonCount:
    """v0.120: ダメージの目安の数字 +（コインが「おもて」なら）数えた場のポケモンの数 × ``per``（カブト（neo2-014）の「ちからをあわせる」）。p.321 の 1 段階。コインはダメージの要素の中で、
    ダメージの量だけを決める（v0.79 の ``HeadsPlusOwnCounters`` と同じ。受けるポケモンがダメージを受けない状態なら投げるかが決まらない v0.4b の問い）。「うら」・数が 0 なら目安の数字。
    数えるのはダメージの要素を処理する時点（``counted_pokemon``。今の姿の名前の完全一致。名前の読めないうらのカードは FD1）。"""

    per: int
    scope: str
    names: tuple[str, ...] | None = None
    local_coins: ClassVar[int] = 1

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        if flips.results[0] is not HEADS:
            return run.attack.damage
        return run.attack.damage + len(counted_pokemon(run.state, run.player, self.scope, self.names)) * self.per


@dataclass(frozen=True)
class FailOnAllTails(Element):
    """v0.120: コインを ``count`` 枚投げ、すべて「うら」ならワザは失敗する（キングドラの「たつまき」の「すべて「うら」なら、このワザは失敗する」。p.323「12 ワザの失敗」）。結果はワザ全体の
    コイン ``name`` として、あとの要素（トラッシュの枚数 ``heads_of``）も使う（投げ直さない）。v0.31 の ``FailOnTails``（1 つでも「うら」なら失敗）とは失敗の条件が違う。コインの前に、
    残りの要素を ``void_coin_question`` で確かめる（``FailOnTails`` と同じ）。"""

    name: str = "coin"
    count: int = 2
    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        index = next((i for i, element in enumerate(run.program) if element is self), None)
        if index is None:
            raise RuntimeError("ワザの失敗のコインの要素が、処理している要素の並びにない（エンジンの不具合）")
        void_coin_question(run, [element for element in run.program[index + 1:] if not element.after_failure])
        flips = run.flip(self.count, by_heads=True)  # 「おもて」の数（0 なら失敗）だけを使う
        run.fs.coins[self.name] = flips
        if flips.heads == 0:
            run.fail("coin")
        return False


@dataclass(frozen=True)
class DiscardOpponentEnergyByHeads(DiscardOpponentEnergy):
    """v0.120: ワザ全体のコイン ``heads_of`` の「おもて」の数ぶんの「エネルギーカード」を、相手（相手の対戦ポケモン）からトラッシュする（キングドラの「たつまき」）。選ぶのはワザを使った
    プレイヤー（決定 ``DISCARD_OPPONENT_ENERGY``。ちょうど「おもて」の数。ついている順にトラッシュ）。v0.31 の ``DiscardOpponentEnergy``（1 枚ずつ）の確かめ（タケシの保護・［KEEP］・
    「ワザをうけない」・「とうめい」・リサイクルエネルギーなど）を使う。

    - 「おもて」が 0 なら何もしない（ワザは前の要素で失敗している）。相手がこのワザで HP 以上・エネルギーカードがついていない（タケシの保護を含む）なら、処理の対象がない（p.309）
    - ついているエネルギーカードが 1 枚以上で「おもて」の数より少ないときは、選べるだけ選ぶとは決まらない（FC1。``stated_cards_short``。v0.75 の「おにびあつめ」と同じ。min で丸めない）
    """

    heads_of: str = "coin"

    def has_target(self, run: AttackRun) -> bool:
        target = run.opponent_active()
        return target is not None and not run.knocked_out(target) and bool(self._energy(run, target))

    def run(self, run: AttackRun) -> bool:
        heads = run.heads(self.heads_of)
        opponent = 1 - run.player
        target = run.opponent_active()
        if not heads or target is None or run.knocked_out(target):
            if heads and target is not None:
                run.ko_prevention_conflict(target, opponent)
            return False
        if not self._energy(run, target) or not reaches(run.res, run.fs, opponent, target, E.ENERGY_DISCARD_ELEMENT):
            return False
        void = self._voided(run, target)
        if void is not None:
            E.note_energy_discard_voided(run.state, void, cause=E.DISCARD_BY_ATTACK, by_player=run.player, effect=str(run.key))
            return False
        options = self._energy(run, target)
        if len(options) < heads:
            raise run.res.question("stated_cards_short", f"相手のエネルギーカード {len(options)} 枚（「おもて」の数 {heads}）")
        problems = {uid: E.energy_discard_problem(run.state, target, uid, cause=E.DISCARD_BY_ATTACK, by_player=run.player) for uid in options}
        blocked = tuple(uid for uid in options if problems[uid] is not None)
        if len(options) - len(blocked) < heads:
            raise UnsupportedError(*problems[blocked[0]])
        code, reason = problems[blocked[0]] if blocked else (None, None)
        run.suspend(kind=DISCARD_OPPONENT_ENERGY, player=run.player, options=options, min_choices=heads, max_choices=heads,
                    extra=(("target", target.pokemon_id),) + _unresolved_extra(blocked, code, reason), carry=True)
        return True

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ()))
        return [answer for answer in combinations_answers(decision, (decision.min_choices,)) if not blocked & set(answer)]

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        opponent = 1 - run.player
        found = run.state.find_pokemon(run.carried["target"])
        if found is None or found[0] != opponent or len(choices) != run.heads(self.heads_of) or any(uid not in found[1].energy for uid in choices):
            raise RuntimeError(f"トラッシュに選んだカード {choices} が、相手の対戦ポケモンについている「おもて」の数のカードではない（エンジンの不具合）")
        target = found[1]
        attacker = run.attacker()
        for energy in tuple(uid for uid in target.energy if uid in choices):
            E.discard_energy_from_play(
                run.state, target, (energy,), cause=E.DISCARD_BY_ATTACK, by_player=run.player,
                log=lambda energy=energy: run.state.add_event("discard_attached_energy", player=opponent, pokemon=target.card, pokemon_id=target.pokemon_id,
                                                              energy=energy, effect=str(run.key), attacker=run.player, attacker_pokemon_id=attacker.pokemon_id))


@dataclass(frozen=True)
class EvolveChosenFromDeck(Element):
    """v0.120: 自分の場の「``names``」を好きなだけ選ぶ。その後、自分の山札から、選んだポケモンから進化する「進化カード」を、それぞれ 1 枚ずつ選びだし、それぞれのポケモンの上にのせ、
    進化させる。山札を見た場合は、その山札をよく切る（ワタッコ（neo3-007）の「しんかのほうし」。実装 ``effects.EvolveChosenNamedFromDeck``）。

    - 段階 1: 自分の場（バトル場 → ベンチ）の、今の姿の名前が ``names`` のどれかのポケモンを選ぶ（決定 ``SELECT_POKEMON``。0〜その数。ワザを使ったポケモン自身も選べる）。いなければ処理の
      対象がない（p.309。ログ ``evolve_from_deck_none``）。「好きなだけ」（「のぞむなら」がない）の 0 匹は、v0.31 の HC5 と同じ問い（答えのときに止める。v0.42 のようせいのきせきと同じ扱い）。
      山札を見る前に公開の情報だけで決まる問い（DV2・GV1・［れんさしんか］の PW4。``effects.self_deck_evolution_open_question``）のあるポケモンは、選べるが選ぶと止める。名前の読めない
      うらのカードは FD1（選べるが選ぶと止める）
    - 段階 2: 選んだポケモンごとに（場の並びの順）、山札にカードがあれば山札を見て、そのポケモンに今重ねられる進化カード（``effects.self_deck_evolution_cards``。通常の進化と同じ制限）を
      1 枚選ぶ（決定 ``SEARCH_DECK``。選べるカードがあれば 1〜1 枚、なければ選べるもののない決定。v0.84 の A3）。選んだらそのまま重ねて進化させる（重ねる前に「とうめい」を評価する。
      トキワシティジムの機会があれば答えてから次へ）。重ねたカードは山札をはなれるので、同じカードを 2 匹に使わない。進化したあとの HP がダメージ以下になるカード（H1）・場に出たときの
      特殊能力を持つカード（PW4）は選べるが選ぶと止める
    - 最後に、山札を見たときだけ 1 回切る（山札が 0 枚なら見ない）。決定をまたぐ続きの情報は、まだ処理していない選んだポケモン（``spore_targets``）・山札を見たか（``spore_looked``）
    """

    names: tuple[str, ...]
    phase: ClassVar[Phase] = Phase.EFFECT

    def decides(self, kind: str) -> bool:
        return kind in (SELECT_POKEMON, SEARCH_DECK, EVOLUTION_HEAL)

    def _chosen_stops(self, run: AttackRun, pokemon: PokemonInPlay) -> tuple[str, str] | None:
        question = E.self_deck_evolution_open_question(run.state, run.player, pokemon, run.state.card_def(pokemon.card).name_ja)
        if question is None:
            return None
        found = QUESTIONS[question[0]]
        return found.code, f"{found.message}（{'・'.join(found.rulings)}。{question[1]}）"

    def _targets(self, run: AttackRun) -> tuple[list[int], dict[int, tuple[str, str]]]:
        targets: list[int] = []
        stops: dict[int, tuple[str, str]] = {}
        for pokemon in run.state.players[run.player].in_play():
            if run.state.is_face_down(pokemon):
                targets.append(pokemon.pokemon_id)
                stops[pokemon.pokemon_id] = (SECRET_PLAN_HIDDEN_CODE, f"うらのカード（場のポケモン {pokemon.pokemon_id}）の名前は読めない（FD1）")
                continue
            if E.form_def(run.state, pokemon).name_ja not in self.names:
                continue
            targets.append(pokemon.pokemon_id)
            stop = self._chosen_stops(run, pokemon)
            if stop is not None:
                stops[pokemon.pokemon_id] = stop
        return targets, stops

    def run(self, run: AttackRun) -> bool:
        targets, stops = self._targets(run)
        if not targets:
            run.state.add_event("evolve_from_deck_none", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key))
            return False
        if len(stops) == len(targets):
            code, reason = stops[targets[0]]
            raise UnsupportedError(code, f"選べるポケモンがどれも選ぶと止めるもの（{reason}）")
        blocked = tuple(pid for pid in targets if pid in stops)
        extra: tuple = ()
        if blocked:
            extra = (("unresolved_choices", blocked), ("unresolved_code", stops[blocked[0]][0]), ("unresolved_reason", stops[blocked[0]][1]),
                     ("unresolved_detail", tuple((pid, *stops[pid]) for pid in blocked)))
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=targets, min_choices=0, max_choices=len(targets), extra=extra)
        return True

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        if decision.kind == SELECT_POKEMON:
            blocked = set(decision.context_value("unresolved_choices", ()))
            return [answer for answer in combinations_answers(decision, range(1, decision.max_choices + 1)) if not blocked & set(answer)]  # 0 匹は答えのときに止める（HC5）
        blocked = set(decision.context_value("unresolved_choices", ())) | set(decision.context_value("entry_power_choices", ()))
        if decision.kind == SEARCH_DECK:
            return [answer for answer in card_id_answers(run.state, decision, (decision.max_choices,)) if not blocked & set(answer)]
        return [answer for answer in all_answers(decision) if not blocked & set(answer)]

    def _next(self, run: AttackRun, remaining: tuple[int, ...], looked: bool) -> bool:
        """選んだポケモン ``remaining`` の順に、山札を見て進化カードを選ぶ決定を出す（出したら True）。すべて終えたら、見たときだけ山札を切る。"""
        state = run.state
        while remaining:
            pid, remaining = remaining[0], remaining[1:]
            found = state.find_pokemon(pid)
            if found is None or found[0] != run.player:
                continue
            target = found[1]
            if not state.players[run.player].deck:
                state.add_event("evolve_from_deck_none", player=run.player, pokemon_id=pid, effect=str(run.key))
                continue
            looked = True
            extra: tuple = (("spore_target", pid), ("spore_targets", remaining), ("spore_looked", 1))
            candidates = E.self_deck_evolution_cards(state, run.player, target)
            if not candidates:
                run.suspend(kind=SEARCH_DECK, player=run.player, options=(), min_choices=0, max_choices=0, extra=extra)
                return True
            blocked = tuple(uid for uid in candidates if target.damage >= E.evolution_hp(state, target, uid))
            entry = tuple(uid for uid in candidates if uid not in blocked and E.applicable_entry_power(state, uid, from_hand=False) is not None)
            if len(blocked) + len(entry) == len(candidates):
                if entry:
                    raise run.res.question("entry_power_during_attack", f"山札の進化カード {list(entry)}")
                raise run.res.question("evolution_hp_every_card", f"山札の進化カード {list(blocked)}")
            if blocked:
                extra += (("unresolved_choices", blocked), ("unresolved_code", "UNRESOLVED_EVOLUTION_HP"), ("unresolved_reason", E.EVOLUTION_HP_REASON))
            if entry:
                extra += (("entry_power_choices", entry),)
            run.suspend(kind=SEARCH_DECK, player=run.player, options=candidates, min_choices=1, max_choices=1, extra=extra)
            return True
        if looked:
            shuffle_in_attack(run, self, run.player)
        return False

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        if decision.kind == SELECT_POKEMON:
            if not choices:
                raise UnsupportedError(
                    "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO",
                    "「好きなだけ選ぶ」（「のぞむなら」がない）で 0 匹を選べるかは決められないので扱わない（HC5。v0.42 のようせいのきせきと同じ）。1 匹以上を選ぶ",
                )
            order = [p.pokemon_id for p in state.players[run.player].in_play()]
            chosen = tuple(sorted(choices, key=order.index))
            state.add_event("evolve_targets", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key), targets=chosen)
            self._next(run, chosen, False)
            return
        remaining = tuple(run.carried.get("spore_targets", ()))
        if decision.kind == EVOLUTION_HEAL:
            found = state.find_pokemon(decision.context_value("heal_pokemon"))
            if found is None:
                raise RuntimeError(f"トキワシティジムの決定のポケモン {decision.context_value('heal_pokemon')} が場にいない（エンジンの不具合）")
            E.apply_evolution_heal(state, found[0], found[1], decision.context_value("heal_stadium"), bool(choices))
            self._next(run, remaining, True)
            return
        pid = run.carried["spore_target"]
        found = state.find_pokemon(pid)
        if found is None or found[0] != run.player:
            raise RuntimeError(f"しんかのほうしの選んだポケモン {pid} が場にいない（エンジンの不具合）")
        target = found[1]
        if not choices:
            if E.self_deck_evolution_cards(state, run.player, target):
                raise RuntimeError(f"必ず選ぶ山札の進化カードの決定に、0 枚の答え（{run.key}。決定の形の誤り。エンジンの不具合）")
            state.add_event("evolve_from_deck_none", player=run.player, pokemon_id=pid, effect=str(run.key))
            self._next(run, remaining, True)
            return
        card = choices[0]
        if card not in E.self_deck_evolution_cards(state, run.player, target):
            raise RuntimeError(f"しんかのほうしで選んだカード {choices} が、ポケモン {pid} に重ねられる山札の進化カードではない（エンジンの不具合）")
        if card in decision.context_value("entry_power_choices", ()):
            question = QUESTIONS["entry_power_during_attack"]
            raise UnsupportedError(question.code, f"{question.message}（PW4。山札の進化カード {card}）")
        if reaches(run.res, run.fs, run.player, target, E.EVOLVE_ELEMENT):
            before_name = E.form_def(state, target).name_ja
            place_evolution_card(state, run.player, target, card, effect=str(run.key))
            terms = E.evolution_heal_terms(state, target, before_name)
            if terms is not None:
                stadium, _, one = terms
                extra: tuple = (("heal_stadium", stadium.card), ("heal_pokemon", target.pokemon_id), ("spore_targets", remaining), ("spore_looked", 1))
                if one:
                    extra += (("unresolved_choices", (target.pokemon_id,)), ("unresolved_code", E.VIRIDIAN_GYM_ONE_COUNTER_CODE),
                              ("unresolved_reason", E.VIRIDIAN_GYM_ONE_COUNTER_REASON))
                run.suspend(kind=EVOLUTION_HEAL, player=run.player, options=(target.pokemon_id,), min_choices=0, max_choices=1, extra=extra)
                return
        self._next(run, remaining, True)


# ---------------------------------------------------------------- v0.32: 山札からベンチに出す・ダメージカウンターでダメージが決まる
# （docs/bench-search-counter-drain-v0.32.md）


@dataclass(frozen=True)
class OwnCountersTimes:
    """自分（ワザを使ったポケモン）にのっているダメージカウンターの数 × ``per``（じたばた。コインはない。0 個なら 0）。``HeadsOwnCounters``（いかりの
    スーパーパンチ。コインの「おもて」なら）と同じ数え方。数えるのはダメージの要素を処理する時点。"""

    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attacker().damage // run.state.rules.damage_per_counter * self.per


@dataclass(frozen=True)
class PlusDefenderCounters:
    """ダメージの目安の数字 + 相手の対戦ポケモンにのっているダメージカウンターの数 × ``per``（ヨガのポーズ）。説明の「相手のポケモン」が相手の場の
    ポケモンすべてを指すかは決められない（CD4）ので、相手の控えポケモンにダメージカウンターがのっていて、読み方で基本となるダメージが変わるときは
    問い ``opponent_pokemon_counters``（宣言の前に止まる。先読みがこの要素を処理するので、コインの結果によらない）。"""

    per: int
    scope_ambiguous: bool = True  # v0.46: False なら説明は「相手にのっている」（バリヤードの「ヨガのポーズ」。相手の対戦ポケモンだけ。CD4 に当たらない）
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        per_counter = run.state.rules.damage_per_counter
        opponent = run.state.players[1 - run.player]
        bench = sum(pokemon.damage for pokemon in opponent.bench) // per_counter
        if bench and self.scope_ambiguous:
            raise run.res.question(
                "opponent_pokemon_counters",
                f"相手の対戦ポケモン {run.opponent_active().damage // per_counter} 個・相手の控えポケモン {bench} 個",
            )
        return run.attack.damage + run.opponent_active().damage // per_counter * self.per


@dataclass(frozen=True)
class BenchFromDeck(Element):
    """自分の山札から、名前が ``names`` のどれかのたねポケモンを 1 匹さがして、自分のベンチに出す。その後、その山札をよく切る（なかまをよぶ・ふえる）。

    - ベンチに空きがないときは使えない（ワザを使うための条件。``effects.PutBasicFromDeckOntoBench.usage_problem`` が宣言の前に拒否する。相手のワザとして
      使うときは ``copy_problem``）。ここに来たらエンジンの不具合
    - 選ぶのはワザを使ったプレイヤー（決定 ``BENCH_FROM_DECK``。1 匹。省略できない）。選べるものは山札の、名前の合うたねポケモン（uid の小さい順）
    - 選べるものがない（山札が 0 枚を含む）: 処理の対象がないので出さない（p.309。ログ ``bench_from_deck_none``）。どちらの場合も、そのあと山札を切る
    - 出したカードは手札を通らない（``zones.bench_from_deck``。ログ ``bench_from_deck``。出したカードは公開。山札の中身はログに書かない）
    - 先読み（``res.dry_run``）では山札を切らない（乱数はコインだけ。切った並びを使う処理が先読みの範囲にないことを、この要素がワザの最後の要素である
      ことで確かめる）
    """

    names: tuple[str, ...]
    pokemon_type: EnergyType | None = None  # v0.34: 名前でなくタイプで選ぶ（ガラガラの「たすけをよぶ」の「闘」ポケモン。進化カードは選べない）
    # v0.45: 名前でなく「(``owner``)のポケモン」（名前が「(``owner``)の」で始まるたねポケモン）で選ぶ（タケシのイシツブテの「たすけをよぶ」の「「タケシのポケモン」
    # (進化カード以外)」。``effects.deck_owner_basic_pokemon``）
    owner: str | None = None
    optional: bool = False  # v0.45: 「出してよい」（0〜1 匹。0 匹ならログ ``bench_from_deck_declined``。そのあと山札を切る）
    local_coin: CoinSide | None = None  # v0.45: この要素のコイン（「コインを投げて「おもて」なら」）。その面でなければ何もしない（山札を切らない）
    # v0.113: ベンチに空きがないときの扱い。``BENCH_FULL_ILLEGAL``（既定。ワザを使うための条件。宣言の前に ``BENCH_FULL`` で拒否する。v0.32 の「なかまをよぶ」）・``BENCH_FULL_FAIL``
    # （ワザを使ってからの失敗。ヤミカラス（neo3-043）の「なかまをよぶ」の「(自分のベンチに空きがないとき、このワザは失敗する。)」。p.323「12 ワザの失敗」。ログ ``attack_failed`` の
    # ``reason`` は ``bench_full``。山札を見ず・切らない）。山札に選べるカードがない（処理の対象がない。p.309）のとは別の理由
    when_full: str = "illegal"
    # v0.114: 名前でなく「ベイビィポケモン」（山札のベイビィポケモンのカード。``effects.deck_baby_pokemon``）で選ぶ（ピチューの「いっしょにあそぼ」）
    babies: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = BENCH_FROM_DECK

    def __post_init__(self) -> None:
        if self.when_full not in (BENCH_FULL_ILLEGAL, BENCH_FULL_FAIL):
            raise ValueError(f"ベンチに空きがないときの扱い {self.when_full!r} は {(BENCH_FULL_ILLEGAL, BENCH_FULL_FAIL)} のどれか")
        if self.babies and (self.names or self.pokemon_type is not None or self.owner is not None):
            raise ValueError("ベイビィポケモンで選ぶ要素は、名前・タイプ・持ち主の名前で選ばない")

    def candidates(self, run: AttackRun) -> list[int]:
        if self.babies:
            return E.deck_baby_pokemon(run.state, run.player)
        if self.owner is not None:
            return E.deck_owner_basic_pokemon(run.state, run.player, self.owner)
        era = E.text_era(run.key.card_id) if self.pokemon_type is not None else None  # v0.114: タイプで選ぶ説明の版（ベイビィポケモンカードの扱い）
        return E.bench_from_deck_candidates(run.state, run.player, self.names, self.pokemon_type, era=era)

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        if len(run.state.players[run.player].bench) >= bench_limit(run.state, run.player):
            if self.when_full == BENCH_FULL_FAIL:
                # v0.113: 説明がベンチに空きがないときの処理（失敗）を書いている（DiscardOwnEnergy の LACKING_FAIL と同じ扱い）。ピクシーの「ほかに必要な条件…がたりないときには
                # 使えない」に当たるかは決められない
                return None if clause != CANNOT_USE else (UNRESOLVED, "自分のベンチに空きがない（使うワザの説明は失敗とする。ほかに必要な条件に当たるか決められない）")
            return (ILLEGAL if clause in (CANNOT_USE, FOLLOW_TEXT) else UNRESOLVED), "自分のベンチに空きがない（ワザを使うための条件）"
        return None

    def run(self, run: AttackRun) -> bool:
        state = run.state
        if len(state.players[run.player].bench) >= bench_limit(state, run.player):
            if self.when_full == BENCH_FULL_FAIL:
                run.fail("bench_full")  # v0.113: ワザの失敗（使ったことになる。山札を見ない・切らない）
                return False
            raise RuntimeError(f"ベンチに空きがないのに、ワザ {run.key} の山札からベンチに出す処理に来た（使うための条件の確認の漏れ。エンジンの不具合）")
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False  # v0.45: 自分の山札への効果なので、相手の状態によらず投げる。「うら」なら何もしない（山札を切らない）
        candidates = self.candidates(run)
        if not candidates:
            attacker = run.attacker()
            extra = {} if self.pokemon_type is None else {"pokemon_type": self.pokemon_type.value}  # v0.34: タイプで選ぶとき
            if self.owner is not None:
                extra["owner"] = self.owner  # v0.45: 「(owner)のポケモン」で選ぶとき
            if self.babies:
                extra["babies"] = True  # v0.114: ベイビィポケモンで選ぶとき
            state.add_event("bench_from_deck_none", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            names=self.names, **extra)
            self._shuffle(run)
            return False
        run.suspend(kind=BENCH_FROM_DECK, player=run.player, options=candidates, min_choices=0 if self.optional else 1)
        return True

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        if self.optional:
            return card_id_answers(run.state, decision, (0, 1))  # v0.45: 同じカード id の答えは 1 つにまとめる（v0.44）
        return all_answers(decision)

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        if not choices:
            # v0.45: 「出してよい」で出さない（ログ ``bench_from_deck_declined``）。そのあと山札を切る（説明の「その後、その山札をよく切る」。v0.44 の「おつかい」と同じ読み方）
            attacker = run.attacker()
            state.add_event("bench_from_deck_declined", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            names=self.names, owner=self.owner)
            self._shuffle(run)
            return
        card = choices[0]
        if card not in self.candidates(run):
            raise RuntimeError(f"ベンチに出すカード {choices} が、山札の選べるたねポケモンではない（エンジンの不具合）")
        pokemon = bench_from_deck(state, run.player, card)
        attacker = run.attacker()
        state.add_event("bench_from_deck", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                        card=card, to_pokemon_id=pokemon.pokemon_id)
        self._shuffle(run)

    def _shuffle(self, run: AttackRun) -> None:
        if run.res.dry_run:
            if run.program[-1] is not self:
                raise RuntimeError("山札を切る要素のあとに要素がある（先読みで切った並びを使えない。エンジンの不具合）")
            return
        shuffle_deck(run.state, run.player)


# v0.113: ``BenchFromDeck.when_full`` の値
BENCH_FULL_ILLEGAL = "illegal"
BENCH_FULL_FAIL = "fail"


# ---------------------------------------------------------------- v0.34（docs/barrier-resume-coin-bonus-v0.34.md）


@dataclass(frozen=True)
class SelfSwitch(Element):
    """ワザを使ったポケモンと、自分の控えポケモン（ワザを使ったプレイヤーが選ぶ。決定 ``SELECT_POKEMON``。1 匹）を入れ替える（v0.34。ナッシーの「テレポート」）。
    入れ替えはポケモンいれかえと同じ処理（``effects._switch_active_with_bench``。ログ ``switch`` に、入れ替えたワザ ``effect`` を加える）。控えがいなければ、
    処理の対象がないので何もしない（p.309）。"""

    # v0.38: この要素のコイン（カツラのポニータの「けりにげ」は「おもて」で入れ替える）。ワザを使ったポケモンが HP 以上（相手の「はんげき」など。
    # CR-COUNTERATTACK-KO-ATTACKER）・控えがいないなら、処理の対象がないので投げない（p.309）。自分への効果なので、相手が「ワザをうけない」状態でも投げる
    local_coin: CoinSide | None = None
    # v0.42: わるいフーディンの「テレポートブラスト」（「のぞむなら、ダメージを与えた後、自分の控えポケモンを1匹選び、このカードと入れ替えてもよい」）。``optional``
    # なら 0〜1 匹を選ぶ（選ばなければ入れ替えない。ログ ``switch_declined``）。``after_damage`` は「ダメージを与えた後」の効果のもとのダメージの要素（ダメージを
    # 与えなかったら Z23。v0.36 の ``ReturnSelfToDeck`` と同じ問い・同じ時点（ワザを使ったポケモンの確認の前））
    optional: bool = False
    after_damage: str | None = None
    # v0.75: タケシのズバットの「しらせる」の「自分に控えがいない時、このワザは使えない」（ワザを使うための条件。実装の ``usage_problem`` が宣言の前に拒否する。
    # 相手のワザとして使うときは ``copy_problem``）
    required: bool = False
    # v0.94（docs/switch-return-attacks-v0.94.md 6 章）: ワザ全体のコインの面（キレイハナの「フローラルスピン」の「うら」）。自分への効果なので、相手の「ワザをうけない」状態で
    # 無効にならない（``coin_receiver`` は None のまま）
    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        if self.required and not run.state.players[run.player].bench:
            return (ILLEGAL if clause in (CANNOT_USE, FOLLOW_TEXT) else UNRESOLVED), "自分に控えポケモンがいない（ワザを使うための条件）"
        return None

    def has_target(self, run: AttackRun) -> bool:
        """v0.94: ワザ全体のコインが決める自分の入れ替えの対象があるか（ワザを使ったポケモンがこのワザで HP 以上でなく、自分に控えがいる。p.309。「(自分に控えがいないとき、
        入れ替える効果はなくなる。)」）。"""
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.ko_prevention_conflict(attacker, run.player)
            return False
        return bool(run.state.players[run.player].bench)

    def leave_blocked(self, run: AttackRun) -> bool:
        return leave_lock(run.state, run.player, run.attacker()) is not None

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        if self.after_damage is not None:
            result = run.fs.results[self.after_damage]
            if result.dealt <= 0:
                raise run.res.question("effect_after_no_damage", f"ポケモン {result.pokemon_id}",
                                       E.effect_after_no_damage_error(str(run.key), result, None, what="自分の控えポケモンと入れ替える"))
        bench = run.state.players[run.player].bench
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.ko_prevention_conflict(attacker, run.player)
            return False
        if not bench:
            return False
        if _leave_prevented(run, run.player, attacker, E.LEAVE_SWITCH, self.local_coin):
            return False  # v0.93: 「バトル場をはなれられない」効果を受けたワザを使ったポケモンは入れ替えない（選ぶ決定を出さない）
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        if run.state.players[run.player].active is not attacker:
            raise RuntimeError(f"入れ替えるワザ {run.key} を使ったポケモンがバトル場にいない（エンジンの不具合）")
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=[p.pokemon_id for p in bench], carry=True, min_choices=0 if self.optional else 1)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if not choices:
            if not self.optional:
                raise RuntimeError(f"入れ替えるワザ {run.key} で入れ替えるポケモンを選ばなかった（エンジンの不具合）")
            attacker = run.attacker()
            run.state.add_event("switch_declined", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key))
            return
        bench = run.state.players[run.player].bench
        if choices[0] not in [p.pokemon_id for p in bench]:
            raise RuntimeError(f"入れ替えるポケモン {choices} が、自分の控えにいない（エンジンの不具合）")
        E._switch_active_with_bench(run.state, run.player, choices[0], effect=str(run.key))


@dataclass(frozen=True)
class HeadsTimesAttachedEnergy:
    """ワザを使うポケモンについているエネルギーの数だけコインを投げ、「おもて」の数 × ``per``（v0.34。ナッシーの「たまなげMAX」）。コインはダメージの要素の
    中（ダメージの量だけを決める）。エネルギーの数は出すエネルギーの個数（v0.58。``effects.attached_units``。無色2個エネルギーは 2 個、レインボーエネルギーは 1 個。
    カードの枚数ではない）。"""

    per: int
    by_heads: ClassVar[bool] = True  # v0.35: 「おもて」の数だけを使う（先読みは「おもて」の数でまとめる。v0.34 の 13 枚からの上限の拒否を解消した）

    def coin_count(self, run: AttackRun) -> int:
        wild_growth_question(run, run.attacker())  # v0.85: ［おいしげる］で個数が決まらない
        return len(E.attached_units(run.state, run.attacker()))

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return (0 if flips is None else flips.heads) * self.per


@dataclass(frozen=True)
class PlusHeadsPerAttachedType:
    """ダメージの目安の数字 + ワザを使うポケモンについている ``energy_type`` のエネルギーの数だけコインを投げた「おもて」の数 × ``per``（v0.35。カスミの
    ニョロゾの「ウォーターパンチ」）。エネルギーの数は ``state.energy_types`` の ``energy_type`` の数（カードが出すエネルギーの数。今の写しでは基本
    エネルギーカードの枚数と同じ）。コインはダメージの要素の中（ダメージの量だけを決める）。"""

    energy_type: EnergyType
    per: int
    by_heads: ClassVar[bool] = True  # 「おもて」の数だけを使う（先読みは「おもて」の数でまとめる）

    def coin_count(self, run: AttackRun) -> int:
        attacker = run.attacker()
        transform_energy_question(run, attacker, self.energy_type, cards=False)  # v0.49: TE1。v0.58: RB1（レインボーエネルギー）
        # v0.58: 出すエネルギーの個数で数える（無色2個エネルギーは「水」ではないので数えない。レインボーエネルギーは RB1 で止めている）
        return sum(1 for unit in E.attached_units(run.state, attacker) if unit == frozenset({self.energy_type}))

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + (0 if flips is None else flips.heads) * self.per


@dataclass(frozen=True)
class TailsOfCoin:
    """ワザ全体のコイン ``coin`` の「うら」の数 × ``per``（v0.35。カツラのケンタロスの「ぜんりょくとっしん」の自分へのダメージ。相手へのダメージは同じコインの
    ``HeadsOfCoin``）。"""

    coin: str
    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.fs.coins[self.coin].tails * self.per


@dataclass(frozen=True)
class SelfAttackLock(Element):
    """コインが ``local_coin`` なら、次の自分の番、ワザを使ったポケモンはこのワザを使えない（v0.35。カスミのニョロモの「あわあわ」。持続する効果
    ``CannotUseOwnAttack``）。ワザを使ったポケモンへの効果（v0.31 の ``SelfPersistent`` と同じく「とうめい」を評価しない）。ワザを使ったポケモンが
    このワザの中で HP 以上になっていれば、効果を与えず、コインも投げない（v0.34 の「こうそくいどう」と同じ）。"""

    # v0.41: None ならコインを投げずにいつも与える（ナツメのヤドランの「きあいずつき」の「次の自分の番、このカードは「きあいずつき」を使えない。」）
    local_coin: CoinSide | None = TAILS
    # v0.76: 使えなくなるワザの位置（同じカードのワザ）。None なら、このワザ自身（v0.75 までのあわあわ・きあいずつきと同じ）。ワンリキーの「きあいいっぱつ」は
    # 「うら」なら「どつく」（位置 1）を使えなくする（使ったワザ「きあいいっぱつ」は使える）
    target_attack_index: int | None = None
    # v0.76: ワザ全体のコインの面（「きあいいっぱつ」の同じ 1 枚のコインの「うら」）。None ならこの要素のコイン（``local_coin``）だけ
    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        # 番をまたぐ効果を、効果を持つポケモンのカードのワザの位置で記録する（v0.31 の SelfNextTurnAttackDamage と同じ）。相手のワザとして使ったときの
        # 「このカードは「あわあわ」を使えない」は、使ったポケモンのワザの位置で表せないので、エンジンの未対応
        return UNSUPPORTED, "番をまたぐ効果を、効果を持つポケモンのカードのワザの位置で記録するので、相手のワザとして使った効果を表せない"

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("persistent_effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                persistent_effect=CannotUseOwnAttack.kind, effect=str(run.key), reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        turn = run.state.turn_number
        index = run.key.attack_index if self.target_attack_index is None else self.target_attack_index
        effect = CannotUseOwnAttack(source_card=attacker.card, source_player=run.player, created_turn=turn,
                                    active_turn=turn + CannotUseOwnAttack.turns_until_active, attack_index=run.key.attack_index, target_attack_index=index,
                                    attack_card=effect_attack_card_of(run, attacker))
        add_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key), target_attack_index=index)
        return False


@dataclass(frozen=True)
class OpponentAttackLock(Element):
    """相手の対戦ポケモンのワザを 1 つ、ワザを使ったプレイヤーが選び（決定 ``SELECT_OPPONENT_ATTACK``）、次の相手の番、そのポケモンはそのワザを使えない
    （v0.35。カスミのニョロモの「ドわすれ」。持続する効果 ``CannotUseAttack``）。相手に与える効果なので、選ぶ前に「ワザをうけない」状態・「とうめい」を
    評価する（受けないなら選ばない。v0.31 の ``DiscardOpponentEnergy`` と同じ順番）。選べるものは、そのポケモンのいちばん上のカードのワザの位置。"""

    # v0.76: この要素のコイン（コンパンの「かなしばり」は「おもて」なら選ぶ）。相手がこのワザで HP 以上・選ぶワザがない（処理の対象がない。p.309）なら投げない。「とうめい」で
    # 受けないと決まった相手・「ワザをうけない」相手には、効果だけを決めるコインなので T19b・HC3（v0.36 の ``OpponentAttackCheck`` と同じ）。「うら」なら選ばず、効果も
    # 与えない（ワザの失敗ではない）。コインは選ぶ前で、決定をまたいで投げ直さない（決定のあとは ``resume`` だけ）
    local_coin: CoinSide | None = None
    # v0.117: 「相手が「たねポケモン」なら」（オドシシの「いかく」）。相手の対戦ポケモンが説明の「たねポケモン」（``effects.field_is_basic_in_text``。ワザを印刷したカードの説明の版）で
    # なければ選ばず、効果を与えない（処理の対象がない。p.309）。決まらない（neo の説明の場のベイビィポケモン）なら NB1
    basic_only: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_OPPONENT_ATTACK
    opponent_element: ClassVar[str] = E.ATTACK_LOCK_ELEMENT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        # v0.36: 効果（``CannotUseAttack``）は、効果を与えたワザを効果を与えたポケモンのカードのワザの位置（``attack_index``）で記録するので、相手のワザ
        # として使った「ドわすれ」の効果を表せない（v0.35 は選べて、効果を与えたところで不変条件の違反（内部エラー）になっていた。あわあわ・きあいだめと
        # 同じ扱いにした。docs/sand-attack-retreat-lock-v0.36.md 5 章）
        return UNSUPPORTED, "番をまたぐ効果を、効果を与えたポケモンのカードのワザの位置で記録するので、相手のワザとして使った効果を表せない"

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if self.basic_only:
            basic = E.field_is_basic_in_text(run.state, target, E.text_era(run.key.card_id))
            if basic is None:
                raise E.neo_basic_baby_error(f"ポケモン {target.pokemon_id}（ワザ {run.key} の「相手が「たねポケモン」なら」）")
            if not basic:
                return False
        if self.local_coin is not None:
            if not E.held_attack_keys(run.state, target)[0]:
                return False  # v0.76: 選ぶワザがない（処理の対象がない。p.309）。コインを投げない
            effect_coin_questions(run, opponent, target)
            if run.flip(1).results[0] is not self.local_coin:
                return False
        if not reaches(run.res, run.fs, opponent, target, E.ATTACK_LOCK_ELEMENT):
            return False
        # v0.49: 選べるものは相手の対戦ポケモンが今持つワザ（``E.held_attack_keys``。今の姿のカード・［サイコリンク］で持つワザを含む。ワザごとに 1 つ）。並びが
        # いちばん上のカードのワザと同じなら v0.48 と同じ形（選べるものはワザの位置）。違えば選べるものは並びの位置で、``lock_attacks`` に (カードの id, 位置) を
        # 書く。持つかが読み方で変わるワザ（VS1）は、選ぶと止める。ワザを持たない相手の対戦ポケモン（v0.47 のポケモンとして出したトレーナーカード）には、
        # 選ぶワザがないので何もしない（p.309。v0.31 の「ゆびをふる」と同じ読み方。v0.48 までは内部エラーだった）
        entries, legacy = E.held_attack_keys(run.state, target)
        if not entries:
            return False
        extra: tuple = (("target", target.pokemon_id),)
        if not legacy:
            extra += (("lock_attacks", tuple((key.card_id, key.attack_index) for key, _ in entries)),)
        held = [(i, problem) for i, (key, problem) in enumerate(entries) if problem is not None]
        if held:
            extra += (("unresolved_choices", tuple(i for i, _ in held)), ("unresolved_code", held[0][1][0]), ("unresolved_reason", held[0][1][1]),
                      ("unresolved_detail", tuple((i, problem[0], f"相手のワザ「{E.attack_of(run.state, entries[i][0]).name_ja}」: {problem[1]}")
                                                  for i, problem in held)))
        run.suspend(kind=SELECT_OPPONENT_ATTACK, player=run.player, options=tuple(range(len(entries))), extra=extra, carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        opponent = 1 - run.player
        target = run.opponent_active()
        if target.pokemon_id != run.carried["target"] or choices[0] not in decision.options:
            raise RuntimeError(f"ドわすれの決定の答え {choices!r} が、相手の対戦ポケモンのワザではない（エンジンの不具合）")
        if "lock_attacks" in run.carried:
            card_id, index = run.carried["lock_attacks"][choices[0]]
        else:
            card_id, index = run.state.cards[target.card].card_id, choices[0]
        attacker = run.attacker()
        turn = run.state.turn_number
        # v0.49: 使えなくなるワザを印刷したカードの id（``target_attack_card``）は、受けるポケモンのいちばん上のカードと違うときだけ書く（v0.48 までの効果と同じ形）。
        # 効果を与えたワザ（「ドわすれ」）の出どころがワザを使ったポケモンのいちばん上のカードと違うとき（［サイコリンク］など）は ``attack_card``
        target_card = card_id if card_id != run.state.cards[target.card].card_id else None
        effect = CannotUseAttack(source_card=attacker.card, source_player=run.player, created_turn=turn,
                                 active_turn=turn + CannotUseAttack.turns_until_active, attack_index=run.key.attack_index,
                                 target_attack_index=index, attack_card=effect_attack_card_of(run, attacker), target_attack_card=target_card)
        add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key), target_attack_index=index,
                              **({"target_attack_card": target_card} if target_card is not None else {}))

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ()))  # v0.49: 持つかが読み方で変わるワザ（VS1）は答えのときに止める
        return [(index,) for index in decision.options if index not in blocked]


@dataclass(frozen=True)
class OpponentReducedDamage(Element):
    """相手の対戦ポケモンを、このワザを使ったポケモン（「このカード」）にワザでダメージを与えるとき、与えるダメージが ``amount`` へる状態にする（v0.34。
    カラカラの「なきつく」。持続する効果 ``ReducedDamageToSource``。相手に与える効果なので「とうめい」・「ワザをうけない」状態を評価する）。"""

    amount: int
    # v0.76: 期限が「次の相手の番」（はたらく番の終わり）の「なきごえ」（``ReducedDamageToSourceNextTurn``）。False なら v0.34 の「なきつく」の「次の自分の番の始め」
    until_turn_end: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.REDUCED_DAMAGE_ELEMENT

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if not reaches(run.res, run.fs, opponent, target, E.REDUCED_DAMAGE_ELEMENT):
            return False
        attacker = run.attacker()
        turn = run.state.turn_number
        kind = ReducedDamageToSourceNextTurn if self.until_turn_end else ReducedDamageToSource
        effect = kind(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn + 1, amount=self.amount)
        add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key))
        return False


# ---------------------------------------------------------------- 登録表の実装 → 要素の並び（v0.13 の 24 種類と、v0.17 から加えた型）


# ---------------------------------------------------------------- v0.36（docs/sand-attack-retreat-lock-v0.36.md）


@dataclass(frozen=True)
class OpponentAttackCheck(Element):
    """相手の対戦ポケモンは、次の相手の番にワザを使うときにコインを投げ、「うら」ならワザは失敗する（v0.36。「すなかけ」・「えんまく」など。持続する効果
    ``AttackCoinCheck``。コインは、効果を受けたポケモンがワザを使うときに ``flow._attack_check_failed`` が投げる。このワザの中では投げない）。相手に与える
    効果なので「ワザをうけない」状態・「とうめい」を評価する（v0.31 の ``OpponentCannotAttack`` と同じ順番）。``single_use``: 「効果は1回できえる」。

    v0.45: ``lasting``（カスミのタッツーの「スミをかける」の「それ以後ワザを使うたびに」。期限のない効果。``AttackCoinCheck.lasting``）と、効果を与えるかを決める
    この要素のコイン（``local_coin``。「コインを投げて「おもて」なら」。効果を受けたポケモンがワザを使うときのコインとは別）。相手がこのワザで HP 以上なら投げない
    （p.309）。「とうめい」で受けないと決まった相手・「ワザをうけない」相手には、効果だけを決めるコインなので T19b・HC3（v0.31 の ``OpponentCannotAttack`` と同じ）。"""

    single_use: bool = False
    lasting: bool = False
    local_coin: CoinSide | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.ATTACK_CHECK_ELEMENT

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if self.local_coin is not None:
            if run.fs.reception.get(target.pokemon_id) is False:
                final = run.fs.evaded.get(target.pokemon_id)
                raise run.res.question("evaded_effect_coin", f"ポケモン {target.pokemon_id}",
                                       None if final is None else E.evaded_effect_coin_error(target.pokemon_id, final))
            prevented_effect_coin(run, opponent, target)
            if run.flip(1).results[0] is not self.local_coin:
                return False
        if not reaches(run.res, run.fs, opponent, target, E.ATTACK_CHECK_ELEMENT):
            return False
        attacker = run.attacker()
        turn = run.state.turn_number
        effect = AttackCoinCheck(source_card=attacker.card, source_player=run.player, created_turn=turn,
                                 active_turn=turn + AttackCoinCheck.turns_until_active, single_use=self.single_use, lasting=self.lasting)
        # v0.45: 期限のない効果だけ、ログに ``lasting``（v0.44 までのログの形は変えない）
        extra = {"lasting": True} if self.lasting else {}
        add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key), single_use=self.single_use, **extra)
        return False


@dataclass(frozen=True)
class OpponentRetreatLock(Element):
    """相手の対戦ポケモンは、次の相手の番に「にげる」ことができない（v0.36。「アイスバーン」・「わしづかみ」。持続する効果 ``CannotRetreat``）。相手に
    与える効果なので「ワザをうけない」状態・「とうめい」を評価する。"""

    # v0.41: この要素のコイン（ウツボットの「ようかいえき」は「おもて」で与える）。対象がこのワザで HP 以上なら投げない（p.309）。「とうめい」で受けないと
    # 決まった相手・「ワザをうけない」相手には、効果だけを決めるコインなので投げるかが決められない（T19b・HC3。v0.38 の ``ForceSwitch`` の ``local_coin`` と同じ）
    local_coin: CoinSide | None = None
    # v0.92: ワザ全体のコインの面（こわいかお。``OpponentCannotAttack.gate`` と同じ 1 枚のコイン）。None ならこの要素のコインだけ（v0.91 まで）
    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.RETREAT_LOCK_ELEMENT

    def coin_receiver(self) -> str | None:
        return "effect"  # v0.92: ワザ全体のコインが決める相手の対戦ポケモンへの効果（``void_coin_question``）

    def has_target(self, run: AttackRun) -> bool:
        return not run.knocked_out(run.opponent_active())  # v0.92: このワザで HP 以上なら処理の対象がない（ワザ全体のコインを投げない。p.309）

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if self.local_coin is not None:
            if run.fs.reception.get(target.pokemon_id) is False:
                final = run.fs.evaded.get(target.pokemon_id)
                raise run.res.question("evaded_effect_coin", f"ポケモン {target.pokemon_id}",
                                       None if final is None else E.evaded_effect_coin_error(target.pokemon_id, final))
            prevented_effect_coin(run, opponent, target)
            if run.flip(1).results[0] is not self.local_coin:
                return False
        if not reaches(run.res, run.fs, opponent, target, E.RETREAT_LOCK_ELEMENT):
            return False
        attacker = run.attacker()
        turn = run.state.turn_number
        effect = CannotRetreat(source_card=attacker.card, source_player=run.player, created_turn=turn,
                               active_turn=turn + CannotRetreat.turns_until_active)
        add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key))
        return False


@dataclass(frozen=True)
class OpponentAttachLock(OpponentRetreatLock):
    """コインが ``local_coin`` なら、次の相手の番、相手の対戦ポケモン（このワザを受けた相手）にはエネルギーカードをつけることができない（v0.59。カスミのメノクラゲの
    「クリスタルビーム」。持続する効果 ``CannotAttachEnergy``）。v0.41 の ``OpponentRetreatLock`` と同じ形（対象が HP 以上ならコインを投げない・「とうめい」・「ワザを
    うけない」状態の評価・効果だけを決めるコインの問い）で、与える効果だけが違う。"""

    opponent_element: ClassVar[str] = E.ATTACH_LOCK_ELEMENT

    def run(self, run: AttackRun) -> bool:
        return _opponent_lock(self, run, CannotAttachEnergy, E.ATTACH_LOCK_ELEMENT)


def _opponent_lock(element, run: AttackRun, kind: type, element_kind: str) -> bool:
    if element.gate is not None and not run.coin_is(element.gate):
        return False
    opponent = 1 - run.player
    target = run.opponent_active()
    if run.knocked_out(target):
        run.ko_prevention_conflict(target)
        return False
    if element.local_coin is not None:
        if run.fs.reception.get(target.pokemon_id) is False:
            final = run.fs.evaded.get(target.pokemon_id)
            raise run.res.question("evaded_effect_coin", f"ポケモン {target.pokemon_id}",
                                   None if final is None else E.evaded_effect_coin_error(target.pokemon_id, final))
        prevented_effect_coin(run, opponent, target)
        if run.flip(1).results[0] is not element.local_coin:
            return False
    if not reaches(run.res, run.fs, opponent, target, element_kind):
        return False
    attacker = run.attacker()
    turn = run.state.turn_number
    effect = kind(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn + kind.turns_until_active)
    add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key))
    return False


@dataclass(frozen=True)
class LockChosenPowers(Element):
    """``damage`` のダメージの要素（相手の場のポケモンを選んだダメージ。v0.89 から ``TargetDamage``）で選んだポケモンは、次の相手の番の終わりまで特殊能力を使うことが
    できない（v0.59。わるいアーボックの「ショックアイ」。持続する効果 ``CannotUsePowers``。バトル場・ベンチのどちらのポケモンも受ける）。

    - 相手のポケモンへの効果なので「ワザをうけない」状態・「とうめい」を評価する（``reaches``。選んだポケモンが控えでも同じ）
    - 選んだポケモンがこのワザで HP 以上なら与えない（p.309。こんじょうを使えるなら G37 と同じ問い）
    - ダメージの要素が「ダメージを受けない」状態などでダメージを与えなかったときも、効果は与える（説明は「ダメージを与えた後」の形ではない）
    """

    damage: str = "bench_damage"
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.POWER_LOCK_ELEMENT

    def run(self, run: AttackRun) -> bool:
        result = run.fs.results.get(self.damage)
        if result is None:
            raise RuntimeError(f"特殊能力を使えなくするポケモンを選んだダメージの要素 {self.damage} の結果がない（エンジンの不具合）")
        opponent = 1 - run.player
        found = run.state.find_pokemon(result.pokemon_id)
        if found is None or found[0] != opponent:
            return False
        target = found[1]
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if not reaches(run.res, run.fs, opponent, target, E.POWER_LOCK_ELEMENT):
            return False
        attacker = run.attacker()
        turn = run.state.turn_number
        effect = CannotUsePowers(source_card=attacker.card, source_player=run.player, created_turn=turn,
                                 active_turn=turn + CannotUsePowers.turns_until_active)
        add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key))
        return False


@dataclass(frozen=True)
class ReturnSelfToDeck(Element):
    """コインが ``local_coin`` なら、``after_damage`` のダメージの要素のあと、ワザを使ったポケモンと、ついているすべてのカードを山札にもどし、その山札を
    よく切る（v0.36。キョウのドガースの「くもがくれガス」。docs/sand-attack-retreat-lock-v0.36.md 4 章）。

    - 「ダメージを与えた後」（``after_damage``）: そのダメージの要素がダメージを与えなかったら Z23（v0.17b の ``Status.after_damage`` と同じ問い。コインの前）
    - ワザを使ったポケモンがこのワザの中で HP 以上なら、もどさない（自分への効果。コインも投げない。p.309「処理の対象がなくなってしまっている場合」）
    - 自分への効果も「とうめい」を評価する（v0.17b の ``Status`` の ``SELF`` と同じ）
    - 同じワザで HP 以上になったポケモンがいれば RD9（``return_in_play_to_deck_with_knockout``。バトル場に出す時点ときぜつの処理の順番が決まらない）。もどす前
    - もどす（``zones.return_in_play_to_deck``）→ 持続する効果を消す（理由 ``return_in_play_to_deck``）→ 山札を切る。先読み（``res.dry_run``）では切らない（v0.32 の
      ``BenchFromDeck`` と同じ。この要素がワザの最後の要素であることで確かめる）。空いたバトル場は、ワザのあとの勝ち負けの判定・バトル場に出す決定で
      うめる（``flow._next_prize_or_judge``・``_promotions_after_judge``。きぜつのあとと同じ処理）
    """

    local_coin: CoinSide | None = HEADS
    after_damage: str | None = "damage"
    # v0.38: ケーシィの「いなくなる」（「このカードにのっているダメージカウンターをすべてとりのぞき、ついているカードをすべてトラッシュする。その後、
    # このカードを山札にもどし」）。もどす前にダメージカウンターをとりのぞき（ログ ``remove_all_damage_counters``）、ついているカード（エネルギー・
    # トレーナー）をトラッシュする（``zones.discard_attached_cards``）。山札にもどすのはポケモンのカード（進化していれば重なったカードも。v0.36 の RD2）
    discard_attached: bool = False
    # v0.38: もどしたあと、この要素で山札を切るか。キョウのポッポの「でんれい」は、もどしたあとに交代・山札をさがしてから切る（説明にない途中の
    # シャッフルをしない）ので False（切るのはあとの ``RevealPokemonFromDeck``）
    shuffle: bool = True
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        if self.after_damage is not None:
            result = run.fs.results[self.after_damage]
            if result.dealt <= 0:
                raise run.res.question("effect_after_no_damage", f"ポケモン {result.pokemon_id}",
                                       E.effect_after_no_damage_error(str(run.key), result, None,
                                                                      what="自分と、自分についているすべてのカードを山札にもどす"))
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.ko_prevention_conflict(attacker, run.player)
            return False
        if _leave_prevented(run, run.player, attacker, E.LEAVE_TO_DECK, self.local_coin):
            return False  # v0.93: もどさない（いなくなるのダメージカウンター・ついているカードのトラッシュ、山札を切ることも起こらない）
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        if not reaches(run.res, run.fs, run.player, attacker, E.RETURN_IN_PLAY_TO_DECK_ELEMENT):
            return False
        from .kernel import knocked

        gone = knocked(run.res)
        if gone:
            raise run.res.question("return_in_play_to_deck_with_knockout", f"ポケモン {[p.pokemon_id for _, p in gone]}")
        if self.discard_attached:
            per = state.rules.damage_per_counter
            before = attacker.damage
            attacker.damage = 0
            state.add_event("remove_all_damage_counters", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                            effect=str(run.key), counters=before // per, amount=before, damage_before=before, total_damage=attacker.damage)
            discard_attached_cards(state, run.player, attacker, effect=str(run.key))
        ninja_trick_leave_question(run, attacker)  # v0.65（NT2）
        return_in_play_to_deck(state, run.player, attacker, effect=str(run.key))
        remove_persistent_effects(state, run.player, attacker, RETURN_IN_PLAY_TO_DECK)
        if not self.shuffle:
            return False
        if run.res.dry_run:
            if run.program[-1] is not self:
                raise RuntimeError("山札を切る要素のあとに要素がある（先読みで切った並びを使えない。エンジンの不具合）")
            return False
        shuffle_deck(state, run.player)
        return False


# ---------------------------------------------------------------- v0.38（docs/bench-switch-combined-v0.38.md）


@dataclass(frozen=True)
class PromoteFromBench(Element):
    """ワザを使ったポケモンがワザの効果で場をはなれて空いたバトル場に、ワザを使ったプレイヤーが自分の控えポケモンを 1 匹選んで出す（v0.38。キョウのポッポの
    「でんれい」の「(ベンチから、かわりの対戦ポケモンを出す)」。決定 ``SELECT_POKEMON``。控えが 1 匹でも出す（きぜつのあとのバトル場に出す決定と同じ））。

    - 説明の順（山札にもどす → 出す → 山札をさがす）に、ワザの途中で出す（p.320 の要素の順番。CR-ENERGY-CONVERSION-ORDER と同じく書かれた順）。出したポケモンは
      そのあとのワザの要素を受けない（今の対応カードでは、出したあとの要素は山札をさがすことだけ）
    - バトル場が空いていない（もどさなかった）なら出さない。控えがいなければ出せないので何もしない（ワザのあとの勝ち負けの判定で、場にポケモンがいない
      プレイヤーは負ける。p.311。v0.36 のくもがくれガスと同じ）
    - 出すのは ``zones.promote_from_bench``（きぜつのあとのバトル場に出す決定と共通。ログ ``promote_active`` にワザの ``effect`` を加える）
    """

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def run(self, run: AttackRun) -> bool:
        p = run.state.players[run.player]
        if p.active is not None or not p.bench:
            return False
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=[pokemon.pokemon_id for pokemon in p.bench])
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        p = run.state.players[run.player]
        if p.active is not None or choices[0] not in [pokemon.pokemon_id for pokemon in p.bench]:
            raise RuntimeError(f"バトル場に出すポケモン {choices} が、空いたバトル場のプレイヤー {run.player} の控えにいない（エンジンの不具合）")
        promoted = promote_from_bench(run.state, run.player, choices[0], effect=str(run.key))
        M.note_switch(run.state, run.player, None, promoted)  # v0.87: 控えからバトル場に出た事実（相手の［まきびし］）


@dataclass(frozen=True)
class RevealPokemonFromDeck(Element):
    """自分の山札から、名前が ``excluded`` のどれでもない「ポケモン」のカードを 1 枚選び出し、相手に見せてから手札に加え、その山札をよく切る（v0.38。キョウの
    ポッポの「でんれい」の「自分の山札から「キョウのポッポ」以外の「ポケモン」を1枚選び出し、相手に見せてから手札に加え、その山札をよく切る」）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SEARCH_DECK``。v0.22 のパソコン通信・v0.24 のポケモン交換おじさんと同じ決定の種類。1 枚。省略できない）。選べるものは
      山札のポケモンのカード（たねポケモン・進化カード）で名前が ``excluded`` にないもの（uid の小さい順。``effects.deck_pokemon_candidates``）。山札の中身は
      ログに書かない
    - 見せて手札に加えるのは ``zones.reveal_deck_to_hand``（v0.24 と共通。ログ ``reveal_from_deck`` は公開。ワザの ``effect`` を加える）
    - 選べるものがない（山札が 0 枚を含む）: 処理の対象がないので加えない（p.309。v0.32 のなかまをよぶと同じ読み方。ログ ``reveal_from_deck_none``）。どちらの
      場合も、そのあと山札を切る（1 回。説明の「その山札をよく切る」）
    - 先読み（``res.dry_run``）では山札を切らない（この要素がワザの最後の要素であることで確かめる。v0.32 の ``BenchFromDeck`` と同じ）
    """

    excluded: tuple[str, ...]
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SEARCH_DECK

    def candidates(self, run: AttackRun) -> list[int]:
        return E.deck_pokemon_candidates(run.state, run.player, self.excluded)

    def run(self, run: AttackRun) -> bool:
        candidates = self.candidates(run)
        if not candidates:
            run.state.add_event("reveal_from_deck_none", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key),
                                excluded=self.excluded)
            self._shuffle(run)
            return False
        run.suspend(kind=SEARCH_DECK, player=run.player, options=candidates)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        card = choices[0]
        if card not in self.candidates(run):
            raise RuntimeError(f"山札から選び出したカード {choices} が、選べるポケモンのカードではない（エンジンの不具合）")
        reveal_deck_to_hand(run.state, run.player, card, effect=str(run.key))
        self._shuffle(run)

    def _shuffle(self, run: AttackRun) -> None:
        if run.res.dry_run:
            if run.program[-1] is not self:
                raise RuntimeError("山札を切る要素のあとに要素がある（先読みで切った並びを使えない。エンジンの不具合）")
            return
        shuffle_deck(run.state, run.player)


# ---------------------------------------------------------------- v0.39（docs/selfdestruct-spread-count-v0.39.md）


@dataclass(frozen=True)
class ChosenBenchDamages(Element):
    """相手の控えポケモンから最大 ``max_targets`` 匹を選び、それぞれにダメージ（v0.39。化石の秘密のライチュウの「ギガスパーク」の「相手の控えポケモンから最大3匹を
    選び、「弱点・抵抗力」に関係なく、それぞれ10ダメージ」）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。``min_choices`` 0・``max_choices`` は min(``max_targets``, 控えの数)。同じポケモンを 2 回選べない
      （``decisions.check_choices``））。控えがいなければ、処理の対象がないので決定を出さない（p.309。v0.31 のかどわかす・v0.33 のかけぬけると同じ読み方）
    - 1 匹以上なら、選んだ数より少なくてもよい（説明の「最大」）。0 匹を選べるかは決められない（GS1。v0.9 の H4・v0.23 の ER9 と同じ言い回しの別のワザの問いで、
      それらの答えで決めない）。0 匹の答えは ``UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE`` で止め、決定は待ったまま（1 匹以上を選び直せる）。先読みは 0 匹を試さない
    - 受けるのは答えの並びの順。どの順でも結果は同じ（ダメージののる控えのポケモンはどれも別。「とうめい」が 2 匹以上なら T27、「ダメージを受けたとき」の効果が
      2 つ以上なら C34・C35 で、順番に頼る前に止まる）
    - ダメージの要素（``Phase.DAMAGE``）なので、前のダメージの要素の送る効果は決定をまたいで運び（v0.34 の ``carry``）、この要素のあとに処理する（p.89）
    """

    base: Any
    max_targets: int
    weakness_resistance: bool = False
    name: str = "bench_damage"
    # v0.46: ちょうど ``max_targets`` 匹を選ぶ（エリカのフシギバナの「かくさんソーラービーム」の「相手の控えポケモンを2匹選び」。「最大」ではない）。控えが 1 匹以上で
    # ``max_targets`` 匹より少なければ、いるだけ選ぶのか、その内容を処理しないのかが決まらない（v0.44 の FC1 と同じ問い。決定の前に止める。先読みが見つける）
    exact: bool = False
    phase: ClassVar[Phase] = Phase.DAMAGE
    guards_bench: ClassVar[bool] = True  # v0.65
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def run(self, run: AttackRun) -> bool:
        if local_coins(self.base, run):
            raise RuntimeError("控えポケモンへのダメージの量を、要素の中のコインで決めるワザはない（エンジンの不具合）")
        bench = run.state.players[1 - run.player].bench
        if not bench:
            return False
        if self.exact and len(bench) < self.max_targets:
            raise run.res.question("stated_cards_short", f"相手の控えポケモン {len(bench)} 匹（説明は {self.max_targets} 匹）")
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=[p.pokemon_id for p in bench], min_choices=self.max_targets if self.exact else 0,
                    max_choices=min(self.max_targets, len(bench)), carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if self.exact and len(choices) != self.max_targets:
            raise RuntimeError(f"選んだポケモン {choices} が {self.max_targets} 匹ではない（エンジンの不具合）")
        if not choices:
            raise UnsupportedError(
                "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE",
                f"相手の控えポケモンがいるときに 0 匹を選べるか（「最大{self.max_targets}匹を選び」が 0 匹を含むか）は、記録から決められないので扱わない"
                "（GS1）。1 匹以上を選ぶ",
            )
        bench = [p.pokemon_id for p in run.state.players[1 - run.player].bench]
        if len(choices) > self.max_targets or any(choice not in bench for choice in choices):
            raise RuntimeError(f"選んだポケモン {choices} が、相手の控えにいない・多すぎる（エンジンの不具合）")
        base = self.base.value(run, None)
        guarded_damages(run, self, [(E.OPPONENT_BENCH, choice, base, self.weakness_resistance) for choice in choices], record=True)  # v0.65

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        # 0 匹は試さない: 0 匹の答えは決定の答えのときに止める（GS1）もので、ワザの宣言を止める理由ではない（1 匹以上を選べば処理できる）。選ぶポケモン・数・
        # 順番の違う答えは、どれも試す（同じものとみなさない）。v0.46 の ``exact`` は決定の選ぶ数がちょうど ``max_targets``
        return all_answers(decision, minimum=1)


SCOPE_OWN_BENCH = "own_bench"
SCOPE_OWN_IN_PLAY = "own_in_play"
SCOPE_BOTH_IN_PLAY = "both_in_play"  # v0.40: お互いの場（わるいマタドガスの「みんなでばくはつ」）


def counted_pokemon(state: GameState, player: int, scope: str, names: tuple[str, ...] | None) -> list[PokemonInPlay]:
    """``player`` の場のポケモンのうち、``scope``（``SCOPE_OWN_BENCH``: ベンチ・``SCOPE_OWN_IN_PLAY``: バトル場とベンチ）にいて、名前（いちばん上のカードの
    ``name_ja``）が ``names`` のどれかと同じもの（None ならすべて）（v0.39）。数えるのは場のポケモン（進化して重なったカードは 1 匹。p.310）。名前は完全一致で、
    名前の一部・収録の弾では見ない。v0.40: ``SCOPE_BOTH_IN_PLAY`` なら、お互いの場（``player`` の場 → 相手の場の順。数だけを使う）。
    v0.49: 名前は今の姿の名前（``effects.form_def``。［へんしん］で相手の対戦ポケモンと同じカード・「ばける」でのせたカードのポケモンとしてあつかうなら、そのカードの
    名前。それ以外はいちばん上のカードの名前で v0.48 と同じ）。"""
    if scope not in (SCOPE_OWN_BENCH, SCOPE_OWN_IN_PLAY, SCOPE_BOTH_IN_PLAY):
        raise ValueError(f"数える範囲 {scope!r}")
    p = state.players[player]
    if scope == SCOPE_BOTH_IN_PLAY:
        pokemon = [*p.in_play(), *state.players[1 - player].in_play()]
    else:
        pokemon = list(p.bench) if scope == SCOPE_OWN_BENCH else list(p.in_play())
    return [x for x in pokemon if names is None or E.form_def(state, x).name_ja in names]


@dataclass(frozen=True)
class PrintedPlusPokemonCount:
    """ダメージの目安の数字 + 数えた場のポケモンの数 × ``per``（v0.39。p.321 の 1 段階の基本となるダメージ）。数えるのはダメージの要素を処理する時点で、実際の処理と
    先読みは同じ値を使う（この値を通る）。弱点・抵抗力・プラスパワーなどは、そのあとの段階で計算する（``deal_damage``）。

    - プクリンの「ともだちのわ」: 自分の控えポケモンの数 × 10（``SCOPE_OWN_BENCH``・名前なし）
    - ニドクインの「ラブラブアタック」: 自分の場に出ている「ニドキング」の数 × 20（``SCOPE_OWN_IN_PLAY``）
    - ロケット団のコイルの「ちょくれつじりょく」: 自分のベンチにいる「コイル」「レアコイル」「わるいレアコイル」1 匹につき 10（``SCOPE_OWN_BENCH``。対応して
      いないカードの名前も、説明の名前のまま数える）
    """

    per: int
    scope: str
    names: tuple[str, ...] | None = None
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + len(counted_pokemon(run.state, run.player, self.scope, self.names)) * self.per



# ---------------------------------------------------------------- v0.40（docs/count-condition-switch-return-v0.40.md）。場の数・条件付きの効果・入れ替え・カードの移動


def shuffle_in_attack(run: AttackRun, element: Element, player: int) -> None:
    """ワザの効果で ``player`` の山札を切る（v0.40。ログ ``shuffle`` にワザの ``effect``）。先読み（``res.dry_run``）では切らない（乱数はコインだけ）。そのとき、この
    要素よりあとに山札の並びを使う要素（``Element.reads_deck_order``）があれば、切った並びを先読みで使えないので止める（エンジンの不具合）。v0.32 の
    ``BenchFromDeck``（ワザの最後の要素であることで確かめる）と同じ考え方を、あとにダメージの要素などが続く要素（むれでおそう）に広げた。"""
    if run.res.dry_run:
        index = next((i for i, candidate in enumerate(run.program) if candidate is element), None)
        if index is None or any(later.reads_deck_order for later in run.program[index + 1:]):
            raise RuntimeError("山札を切る要素のあとに、山札の並びを使う要素がある（先読みで切った並びを使えない。エンジンの不具合）")
        return
    shuffle_deck(run.state, player, effect=str(run.key))


@dataclass(frozen=True)
class BenchFromDeckAny(Element):
    """のぞむなら、自分の山札から名前が ``names`` のどれかのたねポケモンを好きなだけ選び出し、自分のベンチに出す。出したら、その山札をよく切る（v0.40。キョウの
    ズバットの「むれでおそう」の「のぞむなら、ダメージを与える前に、自分の山札から「キョウのズバット」を好きなだけ選び出し、ベンチに出してよい。その場合は、
    その山札をよく切る。」）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``BENCH_FROM_DECK``。v0.32 の ``BenchFromDeck`` と同じ決定の種類）。選べるものは山札の、名前の合うたねポケモン
      （``effects.bench_from_deck_candidates``。uid の小さい順）。選ぶ数は 0〜min(ベンチの空き, 選べるものの数)（「のぞむなら」「好きなだけ」。0 枚は出さないこと。
      v0.39 の GS1（「最大3匹」で 0 匹を選べるか）とは書き方が違い、説明が「のぞむなら」と選ばないことを認めている）。同じカードを 2 回選べない
      （``decisions.check_choices`` の ``DUPLICATE_CHOICE``）
    - 選べるものがない・ベンチに空きがないなら、出せないので決定を出さない（山札は切らない。説明の「その場合は」は出した場合）
    - 出すのは答えの並びの順に 1 枚ずつ（``zones.bench_from_deck``。場に出た番は今の番。ログ ``bench_from_deck`` は v0.32 と同じ形で 1 枚に 1 つ）。そのあと山札を
      1 回だけ切る（``shuffle_in_attack``。1 枚ごとに切らない）。0 枚を選んだら、出さず、切らない（ログ ``bench_from_deck_declined``）
    - ダメージの要素より前に置く（「ダメージを与える前に」）。出したあとの場の数でダメージを数える（``PokemonCountTimes``）
    """

    names: tuple[str, ...]
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = BENCH_FROM_DECK

    def candidates(self, run: AttackRun) -> list[int]:
        return E.bench_from_deck_candidates(run.state, run.player, self.names)

    def space(self, run: AttackRun) -> int:
        return bench_limit(run.state, run.player) - len(run.state.players[run.player].bench)

    def run(self, run: AttackRun) -> bool:
        candidates = self.candidates(run)
        space = self.space(run)
        if not candidates or space <= 0:
            return False
        run.suspend(kind=BENCH_FROM_DECK, player=run.player, options=candidates, min_choices=0, max_choices=min(space, len(candidates)))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        attacker = run.attacker()
        if not choices:
            state.add_event("bench_from_deck_declined", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            names=self.names)
            return
        candidates = self.candidates(run)
        if len(set(choices)) != len(choices) or any(card not in candidates for card in choices) or len(choices) > self.space(run):
            raise RuntimeError(f"ベンチに出すカード {choices} が、山札の選べるたねポケモンではない・多すぎる（エンジンの不具合）")
        for card in choices:
            pokemon = bench_from_deck(state, run.player, card)
            state.add_event("bench_from_deck", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            card=card, to_pokemon_id=pokemon.pokemon_id)
        shuffle_in_attack(run, self, run.player)


@dataclass(frozen=True)
class PokemonCountTimes:
    """数えた場のポケモンの数 × ``per``（v0.40。p.321 の 1 段階の基本となるダメージ。v0.39 の ``PrintedPlusPokemonCount`` の、目安の数字を足さない形）。
    数えるのはダメージの要素を処理する時点（``counted_pokemon``。進化して重なったカードは 1 匹・名前の完全一致）。

    - キョウのズバットの「むれでおそう」: 自分の場にいる「キョウのズバット」の数 × 10（``SCOPE_OWN_IN_PLAY``。山札から出したあとの数。ワザを使ったポケモンも数える）
    - わるいマタドガスの「みんなでばくはつ」: お互いの場にいる「ドガース」「マタドガス」「わるいマタドガス」の数 × 20（``SCOPE_BOTH_IN_PLAY``。ワザを使ったポケモンも
      数える。「キョウのドガース」「キョウのマタドガス」は名前が違うので数えない）
    """

    per: int
    scope: str
    names: tuple[str, ...] | None = None
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return len(counted_pokemon(run.state, run.player, self.scope, self.names)) * self.per


@dataclass(frozen=True)
class TailsOfOpponentBenchCoins:
    """相手プレイヤーが、相手の控えポケモンの数だけコインを投げ、「うら」の数 × ``per``（v0.40。わるいスリーパーの「ベンチをあやつる」の「相手プレイヤーに、相手の
    控えポケモンの数だけコインを投げさせ、「うら」が出た数×20のダメージ」）。

    - コインはダメージの要素の中（ダメージの量だけを決める）。枚数はダメージの要素を処理する時点の相手の控えの数（0 匹なら投げず、0。p.321 の 2 段階までで 0 以下
      なので「ダメージを与えなかった」）
    - 投げるのは相手プレイヤー（``flipped_by_opponent``。ログ ``coin_flip`` の ``player`` が相手。乱数の使い方は同じ）
    - 結果は「うら」の数（= 枚数 −「おもて」の数）だけを使う（``by_heads``。先読みは「おもて」の数でまとめる。v0.35）
    - 相手が「ダメージを受けない」状態なら、ダメージの量だけを決めるコインなので投げるかが決められない（v0.4b の問い。``Damage.run``）
    """

    per: int
    by_heads: ClassVar[bool] = True
    flipped_by_opponent: ClassVar[bool] = True

    def coin_count(self, run: AttackRun) -> int:
        return len(run.state.players[1 - run.player].bench)

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return (0 if flips is None else flips.tails) * self.per


@dataclass(frozen=True)
class CoinPerOpponentBench(Element):
    """相手の控えポケモンそれぞれに対してコインを投げ、「おもて」ならそのポケモンに（「弱点・抵抗力」に関係なく）``bench_damage``。全員に対してコインを投げ終わったら、
    その間に出た「うら」の数 × ``self_per`` ダメージをワザを使ったポケモンに与える（v0.60。サンダーの「サンダーストーム」。docs/coins-defense-rebellion-v0.60.md 2 章）。

    - 対象は、この要素を処理する時点の相手の控えの並び（ベンチの順）。コインは 1 匹 1 枚、並びの順に 1 回の ``flip`` で投げ、``i`` 枚目は ``i`` 番目の控えのもの（「おもて」の
      数でまとめない。``by_heads`` は渡さない。先読みは 2 の控えの数乗通りを試す）。結果は ``fs.coins[name]`` とログ ``bench_coin_results``（控えの番号と面の対応）に残す
    - すべて投げてから、「おもて」の控えに並びの順でダメージ（``deal_damage`` の ``OPPONENT_BENCH``・弱点・抵抗力なし）。そのあと同じコインの「うら」の数で自分へのダメージ
      （ワザによる自分へのダメージ。「うら」が 0 なら与えない。投げ直さない）。控えがいなければコインも自分へのダメージもない
    - 「とうめい」がはたらいている控えポケモンのあとに控えがいれば、コインの投げ方（すべて投げてからか、1 匹ずつか。印刷の文面・記録で決まらない）で乱数の割り当てが変わるので、
      コインの前に TS1（``bench_coin_transparency_order``）で止める。2 匹以上の「とうめい」は今までどおり T27（``multiple_evasion``）
    - コインが決めるのは控えへのダメージと自分へのダメージ（自分へのダメージは有効な要素）なので、受ける控えがみな無効（見えない壁）でもコインを投げる（``void_coin_question`` の
      対象にしない）
    """

    bench_damage: int
    self_per: int
    name: str = "bench_coins"
    phase: ClassVar[Phase] = Phase.DAMAGE
    guards_bench: ClassVar[bool] = True  # v0.65

    def run(self, run: AttackRun) -> bool:
        state = run.state
        bench = list(state.players[1 - run.player].bench)
        if not bench:
            run.fs.coins[self.name] = CoinFlips(())
            return False
        if any(E.evasion_power(state, pokemon) is not None for pokemon in bench[:-1]):
            raise run.res.question("bench_coin_transparency_order", f"控えのポケモン {[p.pokemon_id for p in bench]}")
        flips = run.flip(len(bench))
        run.fs.coins[self.name] = flips
        state.add_event("bench_coin_results", player=run.player, pokemon=run.attacker().card, pokemon_id=run.attacker().pokemon_id, effect=str(run.key),
                        targets=tuple(p.pokemon_id for p in bench), results=tuple(side.value for side in flips.results))
        heads = [(E.OPPONENT_BENCH, pokemon.pokemon_id, self.bench_damage, False) for pokemon, side in zip(bench, flips.results) if side is HEADS]
        # v0.65: ［ベンチガード］の決定が要れば止まり、「うら」の数（コインは投げ直さない）を続きの情報で運んで、決定のあとで自分へのダメージを与える
        if guarded_damages(run, self, heads, after=flips.tails):
            return True
        self.after_guarded(run, flips.tails)
        return False

    def after_guarded(self, run: AttackRun, after: Any) -> None:
        if after:
            run.fs.results["self_damage"] = deal_damage(run.res, run.fs, SELF, after * self.self_per)


@dataclass(frozen=True)
class SelfDamageGuard(Element):
    """ワザを使ったポケモン自身に「かげぶんしん」の効果（``state.TailsDamageGuard``）を与える（v0.60。R団のストライクの「かげぶんしん」）。コインはない（コインはダメージを受ける時に
    相手プレイヤーが投げる。``kernel.damage_guard_passes``）。自分自身への持続する効果（``SelfMaxHp`` と同じく「とうめい」は評価しない）。前の効果は理由 ``replaced`` で消す。
    ワザを使ったポケモンがこのワザの中で HP 以上なら与えない（今の対応カードでは、ダメージのないこのワザで起こらない）。"""

    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("persistent_effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                persistent_effect=TailsDamageGuard.kind, effect=str(run.key), reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        turn = run.state.turn_number
        effect = TailsDamageGuard(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn)
        replace_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key))
        return False


@dataclass(frozen=True)
class OwnCountersAtLeast(Element):
    """ワザを使うための条件「このワザは、自分にダメージカウンターが ``minimum`` つ以上のっているときだけ、使える」（v0.40。サカキのニドラン♂の「いかりのいちげき」）。

    条件はワザの実装の ``usage_problem`` が宣言の前（必要なエネルギーの確認のあと・こんらんのコインの前）に確かめる（``NOT_ENOUGH_DAMAGE_COUNTERS``。状態・乱数・
    ログを変えない）。この要素は、相手のワザとして使うとき（ピクシー・ピッピの「ゆびをふる」など）の扱い（``copy_problem``。v0.38 の ``ChosenBenchDamage.required``
    と同じ）と、ここに条件を満たさないまま来たときの確かめ（エンジンの不具合）だけを持つ。"""

    minimum: int
    phase: ClassVar[Phase] = Phase.NEUTRAL

    def counters(self, run: AttackRun, pokemon: PokemonInPlay) -> int:
        return pokemon.damage // run.state.rules.damage_per_counter

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        if self.counters(run, copier) < self.minimum:
            return (ILLEGAL if clause in (CANNOT_USE, FOLLOW_TEXT) else UNRESOLVED), \
                f"自分にダメージカウンターが {self.minimum} つ以上のっていない（ワザを使うための条件）"
        return None

    def run(self, run: AttackRun) -> bool:
        if self.counters(run, run.attacker()) < self.minimum:
            raise RuntimeError(f"ダメージカウンターが {self.minimum} つ以上のっていないのに、ワザ {run.key} に来た（使うための条件の確認の漏れ。エンジンの不具合）")
        return False


@dataclass(frozen=True)
class PrintedPlusBonusIfDefenderDamaged:
    """ダメージの目安の数字 + （相手の対戦ポケモンにダメージカウンターがのっていれば ``bonus``）（v0.40。サカキのニドリーノの「つのでえぐる」の「このワザを使う時、
    すでに相手にダメージカウンターがのっているなら、20ダメージを追加する。」。p.321 の 1 段階）。

    - 「相手」は相手の対戦ポケモン（p.320 の「相手」）。控えポケモンのカウンターは見ない（v0.32 の CD4（「相手のポケモン」）とは書き方が違う）
    - 見るのは、のっているかどうかだけ（数に比例しない。v0.32 の ``PlusDefenderCounters``（ヨガのポーズ）とは別の値）
    - 「このワザを使う時、すでに」: ワザの宣言のあと、このワザのダメージより前（ダメージの要素はこの 1 つで、前の要素はない）の相手の対戦ポケモンのダメージで決める
    """

    bonus: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + (self.bonus if run.opponent_active().damage > 0 else 0)


@dataclass(frozen=True)
class OpponentAttackLockWhileSourceActive(Element):
    """このワザを受けた相手の対戦ポケモンが「最大HPが ``max_hp`` 以下」のポケモンなら、次の相手の番、このカードがバトル場にいる限り、そのポケモンはワザを使えない
    （v0.40。サカキのニドキングの「すごむ」。持続する効果 ``CannotAttackWhileSourceActive``）。

    - 「最大HP」は受けるポケモンのいちばん上のカードの HP（ダメージを引かない）。確かめるのは効果を与えるとき（受けるとき）。50 より大きければ、与える効果がないので、
      「とうめい」・「ワザをうけない」状態も評価しない（処理の対象がない。p.309。v0.31 の ``DiscardOpponentEnergy`` と同じ順番）
    - 相手に与える効果なので「ワザをうけない」状態・「とうめい」を評価する（v0.31 の ``OpponentCannotAttack`` と同じ）
    - 「このカードがバトル場にいる限り」は、ワザの宣言のときに効果を与えたポケモンがバトル場にいるかで確かめる（``persistent.cannot_attack_while_source_active``）
    """

    max_hp: int | None  # v0.76: None なら最大HPの条件がない（ヒノアラシ・ワニノコの「にらみつける」・ウパーの「しっぽをふる」）
    # v0.76: この要素のコイン（「コインを投げて「おもて」なら、…」）。相手がこのワザで HP 以上なら投げない（p.309）。「とうめい」で受けないと決まった相手・「ワザをうけない」相手には、
    # 効果だけを決めるコインなので T19b・HC3（v0.36 の ``OpponentAttackCheck`` と同じ）。「うら」なら効果を与えない（ワザの失敗ではない）
    local_coin: CoinSide | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.ATTACK_LOCK_ELEMENT

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if self.max_hp is not None and E.max_hp(run.state, target) > self.max_hp:  # v0.48: 今有効な最大HP（受けるとき）
            return False
        if self.local_coin is not None:
            effect_coin_questions(run, opponent, target)
            if run.flip(1).results[0] is not self.local_coin:
                return False
        if not reaches(run.res, run.fs, opponent, target, E.ATTACK_LOCK_ELEMENT):
            return False
        attacker = run.attacker()
        turn = run.state.turn_number
        effect = CannotAttackWhileSourceActive(source_card=attacker.card, source_player=run.player, created_turn=turn,
                                               active_turn=turn + CannotAttackWhileSourceActive.turns_until_active)
        add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key))
        return False


@dataclass(frozen=True)
class AmountIfOwnBenchNamed:
    """自分のベンチに名前が ``names`` のどれかのポケモンがいれば ``amount``、いなければダメージの目安の数字（v0.40。サカキのニドクインの「ラブラリアット」の「自分の
    ベンチに「サカキのニドキング」がいるなら、このワザのダメージは「100」になる。」）。

    p.321 の 1 段階（ワザの説明にしたがって計算した基本となるダメージ）。ワザを使うポケモンにかかっている効果（2 段階。v0.27 の「つるぎのまい」の「「60」になる」は
    前の番のワザの持続する効果）ではない。匹数で足さない（1 匹でも 2 匹でも ``amount``）。名前は完全一致（「ニドキング」は「サカキのニドキング」ではない）。"""

    names: tuple[str, ...]
    amount: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return self.amount if counted_pokemon(run.state, run.player, SCOPE_OWN_BENCH, self.names) else run.attack.damage


@dataclass(frozen=True)
class ReturnOpponentToDeck(Element):
    """相手の対戦ポケモンと、それについているすべてのカードを、持ち主（相手）の山札にもどさせ、その山札をよく切る（v0.40。わるいカイリキーの「つまみだす」。
    「(相手に控えがいない時、このワザは使えない)」）。

    - 相手に控えがいないことは、ワザを使うための条件（実装の ``usage_problem``。``NO_OPPONENT_BENCH``。相手のワザとして使うときは ``copy_problem``）
    - 相手に与える効果なので「ワザをうけない」状態・「とうめい」を評価する（受けないなら何もしない。山札も切らない）
    - もどす（``zones.return_in_play_to_deck``。v0.36 の自分を山札にもどす処理と同じ関数を、持ち主（相手）で呼ぶ。重なったカード・エネルギー・トレーナーを持ち主の
      山札に。ダメージカウンター・特殊状態はなくなる）→ 持続する効果を消す（理由 ``return_in_play_to_deck``）→ 持ち主の山札を切る（ログ ``shuffle`` の ``player`` は
      相手。``effect`` はワザ）。きぜつではない（サイドは取らない。ログ ``knock_out`` ではない）
    - 空いた相手のバトル場は、ワザのあとの勝ち負けの判定・バトル場に出す決定（相手が自分の控えから選ぶ。``flow._promotions_after_judge``）でうめる（v0.36 の
      くもがくれガスと同じ処理。相手には控えがいる）
    - 同じワザで HP 以上になったポケモンがいれば RD9（v0.36 と同じ問い。ダメージの要素のないワザなので、今の対応カードでは起こらない）
    - 先読み（``res.dry_run``）では切らない（``shuffle_in_attack``）
    - v0.48: ``gate`` はワザ全体のコインの面（ナツメのゲンガーの「やみのこえ」の「コインを2枚投げる。すべて「おもて」なら」）。``required`` が偽なら、相手に控えが
      いなくても使える（「やみのこえ」の説明に「つまみだす」の条件はない）。相手の対戦ポケモンがこのワザで HP 以上なら処理の対象がない（``has_target``。コインを投げない。
      「相手が「きぜつ」しなかったなら」）
    """

    required: bool = True
    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.RETURN_IN_PLAY_TO_DECK_ELEMENT

    def coin_receiver(self) -> str | None:
        return "effect"  # v0.48: 相手の対戦ポケモンへの効果（コインの前の ``void_coin_question``）

    def has_target(self, run: AttackRun) -> bool:
        """v0.48: 相手の対戦ポケモンが、このワザの中で HP 以上になっていれば処理の対象がない（コインを投げない）。こんじょうを使えるなら G37（``Status.has_target`` と同じ）。
        v0.93: 相手の対戦ポケモンが「バトル場をはなれられない」なら、このワザ全体のコインはもどす部分（起こらない）だけを決めるので AL2（コインの前）。v0.94 から、その確かめは
        ``leave_blocked`` で、コイン（``Coin``）が決める要素の全体で判断する（やみのこえは、このコインがこの要素だけを決めるので、結果は同じ）。"""
        target = run.opponent_active()
        if target is None:
            return False
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        return True

    def leave_blocked(self, run: AttackRun) -> bool:
        target = run.opponent_active()
        return target is not None and leave_lock(run.state, 1 - run.player, target) is not None

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        if self.required and not run.state.players[1 - run.player].bench:
            return (ILLEGAL if clause in (CANNOT_USE, FOLLOW_TEXT) else UNRESOLVED), "相手に控えポケモンがいない（ワザを使うための条件）"
        return None

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        state = run.state
        opponent = 1 - run.player
        p = state.players[opponent]
        target = p.active
        if self.required and not p.bench:
            raise RuntimeError(f"相手に控えポケモンがいないのに、ワザ {run.key} の山札にもどす処理に来た（使うための条件の確認の漏れ。エンジンの不具合）")
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if _leave_prevented(run, opponent, target, E.LEAVE_TO_DECK, None):
            return False  # v0.93（ワザ全体のコイン（やみのこえ）の前の確かめは ``has_target``）
        if not reaches(run.res, run.fs, opponent, target, E.RETURN_IN_PLAY_TO_DECK_ELEMENT):
            return False
        from .kernel import knocked

        gone = knocked(run.res)
        if gone:
            raise run.res.question("return_in_play_to_deck_with_knockout", f"ポケモン {[pokemon.pokemon_id for _, pokemon in gone]}")
        ninja_trick_leave_question(run, target)  # v0.65（NT2）
        return_in_play_to_deck(state, opponent, target, effect=str(run.key))
        remove_persistent_effects(state, opponent, target, RETURN_IN_PLAY_TO_DECK)
        shuffle_in_attack(run, self, opponent)
        return False


@dataclass(frozen=True)
class ReturnBothActivesToDeck(Element):
    """ワザを使ったポケモンと相手の対戦ポケモン、それぞれについているすべてのカードを、それぞれの持ち主の山札にもどし、それぞれの山札をよく切る（v0.52。エリカの
    ハクリューの「つれさる」。docs/field-return-v0.52.md 4 章）。

    - 対象: ワザを使ったポケモン（自分）と相手の対戦ポケモン。このワザの中で HP 以上になっていれば、その側は処理の対象がない（p.309。こんじょうを使えるなら G37 と同じ問い。
      このワザにダメージの要素はないので、今の対応カードでは起こらない）
    - 同じワザで HP 以上になったポケモンがいれば RD9（もどす前・受けるかのコインの前。v0.36 と同じ問い）
    - 自分 → 相手の順に、受けるか（「ワザをうけない」状態・「とうめい」。``reaches``。両方が「とうめい」なら T27）を評価し、受けるなら、もどす（``zones.return_in_play_to_deck``）
      → 持続する効果を消す（理由 ``return_in_play_to_deck``）。受けない側はもどさない。対象は、効果を処理し始めたときの 2 匹（自分をもどしても、相手の対戦ポケモンは
      変わらない）。そのあと、もどした側の山札を、自分 → 相手の順に切る（``shuffle_in_attack``。先読みでは切らない）。説明は「もどし、…切る」で、もどすことと切ることの順番だけを決めている。2 匹をもどす順・2 つの山札を切る順は
      結果（どちらの山札にどのカードが入るか）を変えないので、説明の書かれた順（自分 → 相手）にした（実装上の判断。乱数の使い方だけが決まる）。英語版の「Then, your
      opponent …」の順番は根拠にしない
    - 片方がもどったあとも、もう片方の処理を続ける（ワザを使ったポケモンが場をはなれても、この要素の処理は終わらない）。きぜつではないので、サイド・きぜつしたときの
      特殊能力はない。空いたバトル場は、ワザのあとの勝ち負けの判定・バトル場に出す決定（``flow._promotions_after_judge``。番でないプレイヤーが先）でうめる
    """

    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.RETURN_IN_PLAY_TO_DECK_ELEMENT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        opponent = 1 - run.player
        sides = []
        for owner, pokemon in ((run.player, run.attacker()), (opponent, run.opponent_active())):
            if pokemon is None:
                continue
            if run.knocked_out(pokemon):
                run.ko_prevention_conflict(pokemon, owner)
                continue
            if _leave_prevented(run, owner, pokemon, E.LEAVE_TO_DECK, None):
                continue  # v0.93: その側はもどさない（もう片方は続ける）
            sides.append((owner, pokemon))
        from .kernel import knocked

        gone = knocked(run.res)
        if gone:
            raise run.res.question("return_in_play_to_deck_with_knockout", f"ポケモン {[pokemon.pokemon_id for _, pokemon in gone]}")
        returned = []
        for owner, pokemon in sides:
            if not reaches(run.res, run.fs, owner, pokemon, E.RETURN_IN_PLAY_TO_DECK_ELEMENT):
                continue
            ninja_trick_leave_question(run, pokemon)  # v0.65（NT2）
            return_in_play_to_deck(state, owner, pokemon, effect=str(run.key))
            remove_persistent_effects(state, owner, pokemon, RETURN_IN_PLAY_TO_DECK)
            returned.append(owner)
        for owner in returned:
            shuffle_in_attack(run, self, owner)
        return False


@dataclass(frozen=True)
class PrintedPlusBonusOnAllHeads:
    """コインを ``coins`` 枚投げ、すべて「おもて」なら、ダメージの目安の数字 + ``bonus``（v0.40。カスミのシードラの「きぜつばり」の「コインを2枚投げ、すべて「おもて」
    なら、60ダメージを追加する。」）。「おもて」の数に比例しない（1 枚だけ「おもて」なら目安の数字だけ）。コインはダメージの要素の中（ダメージの量だけを決める）で、
    結果は「おもて」の数だけを使う（``by_heads``）。"""

    coins: int
    bonus: int
    by_heads: ClassVar[bool] = True

    @property
    def local_coins(self) -> int:
        return self.coins

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + (self.bonus if flips is not None and flips.heads == self.coins else 0)


@dataclass(frozen=True)
class ShuffleDeck(Element):
    """山札をよく切る（v0.40。タケシのマンキーの「ひまつぶし」の「自分の山札をよく切る。」（``own``）・マンキーの「いたずら」の「相手の山札をよく切る。」）。

    - 切るのは ``zones.shuffle_deck``（乱数 ``state.rng`` の並べかえ 1 回。ログ ``shuffle`` の ``player`` は切る山札の持ち主、``effect`` はワザ）
    - 相手の山札を切ることは、相手の対戦ポケモンへの効果ではない（「ワザをうけない」状態・「とうめい」は関係しない。v0.31 の相手の山札をトラッシュする要素と同じ）
    - 山札が 0 枚でも切る処理をする（並べかえる札がなく、乱数は使わない。ログは残す）
    - 先読み（``res.dry_run``）では切らない（``shuffle_in_attack``）
    """

    own: bool = True
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        shuffle_in_attack(run, self, run.player if self.own else 1 - run.player)
        return False


@dataclass(frozen=True)
class DiscardStadium(Element):
    """場に「スタジアムカード」があれば、それをトラッシュする（v0.58。タケシのゴローンの「ばくれつ」）。

    - トラッシュするのは v0.57 の ``zones.discard_stadium``（同じ uid のまま持ち主のトラッシュ。ログ ``stadium_discarded`` の ``reason`` は ``attack``・``by_card`` は
      ワザを使ったポケモンのカード・``effect`` はワザ）。スタジアムがなければ何もしない（p.309。ログ ``stadium_discard_none``）
    - 場のポケモンへの効果ではない（「ワザをうけない」状態・「とうめい」は関係しない）。ワザを使ったポケモンがこのワザで HP 以上になっても処理する
    - 先読み（``res.dry_run``）でも状態の複製の上で同じに処理する（乱数を使わない）
    """

    phase: ClassVar[Phase] = Phase.EFFECT
    # v0.61: 場のポケモンによらない要素（ワザを使ったポケモンが［ずらかる］で場をはなれたあとも、時点で結果が変わらない。``kernel.settle_scram``）
    independent_of_pokemon: ClassVar[bool] = True

    def run(self, run: AttackRun) -> bool:
        stadium = run.state.stadium
        if stadium is None:
            run.state.add_event("stadium_discard_none", player=run.player, effect=str(run.key))
            return False
        # v0.61: ワザを使ったポケモンが［ずらかる］で山札にもどっていても、ワザを使ったカード（ログ ``attack`` の ``pokemon``）を書く
        located = run.state.find_pokemon(run.fs.frame.source_pid)
        by_card = located[1].card if located is not None else _declared_attacker_card(run)
        discard_stadium(run.state, stadium, reason="attack", by_card=by_card, effect=str(run.key))
        return False


def _declared_attacker_card(run: AttackRun) -> int:
    """v0.61: 今のワザを宣言したポケモンのカード（今の番の最後のログ ``attack`` の ``pokemon``）。ワザを使ったポケモンが場をはなれたあとに使う。"""
    for event in reversed(run.state.log):
        if event["kind"] == "attack" and event.get("player") == run.player:
            return event["pokemon"]
    raise RuntimeError("ワザの宣言のログがない（エンジンの不具合）")


# ---------------------------------------------------------------- v0.41（docs/heal-counter-status-v0.41.md）
# 回復（ダメージカウンターをとりのぞく）・ダメージカウンターを相手にのせる／取り替える・特殊状態を選ぶ・山札からエネルギーをつける


@dataclass(frozen=True)
class PrintedMinusIfDefenderDamaged:
    """ダメージの目安の数字 −（相手の対戦ポケモンにダメージカウンターがのっていれば ``reduction``）（v0.41。エリカのプリンの「やさしいパンチ」の「相手にダメージ
    カウンターがのっている時、このワザのダメージは「-30」される。」。p.321 の 1 段階。ダメージの目安の「−」の説明。GR-2000-P320-DAMAGE-FIGURE）。

    - 「相手」は相手の対戦ポケモン（p.320 の「相手」）。見るのはのっているかどうかだけ（数に比例しない。v0.40 の ``PrintedPlusBonusIfDefenderDamaged`` と同じ見方）
    - 見る時点は、このワザのダメージの計算のとき（ダメージの要素はこの 1 つで、前の要素はない）
    """

    reduction: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage - (self.reduction if run.opponent_active().damage > 0 else 0)


def _counters_changed(run: AttackRun, pokemon: PokemonInPlay, before: int) -> None:
    """ワザの効果でダメージカウンターをのせた・取り替えたあと（v0.41）。HP 以上になったら、きぜつの原因の枠を記録する（``kernel.track_ko``。同時のきぜつの判定）。
    カウンターの移動はワザのダメージではない（GR-2000-P320-COUNTER-MOVE）ので、それで HP 以上になったポケモンは、きぜつの判定で「こんじょう」を使えない
    （相手のワザのダメージで HP 以上になったのではない。v0.11 の G3〜G7。``ko_prevention_able`` を偽にする）。"""
    track_ko(run.res, run.fs, pokemon, before)
    hp = E.max_hp(run.state, pokemon)  # v0.48: 今有効な最大HP
    if before >= hp and pokemon.damage != before:
        from .kernel import focus_band_timing, knockout_survival_timing

        focus_band_timing(run.res, pokemon, "HP 以上になったあとのダメージカウンター")  # v0.81（FB1）
        knockout_survival_timing(run.res, pokemon, "HP 以上になったあとのダメージカウンター")  # v0.110（KS1）
    if before < hp <= pokemon.damage:
        run.res.ko_prevention_able[pokemon.pokemon_id] = False


def _counter_transfer_protected(run: AttackRun, target: PokemonInPlay, detail: str) -> None:
    """相手の対戦ポケモンが、ダメージカウンターをのせる・取り替える効果を受けない（「ワザをうけない」状態。v0.31 のバリアー）なら、自分の側の処理をするかが
    決まらない（CX1）。「とうめい」は ``reaches`` で効果を受けるときに評価し、受けなければ同じ問いにする（呼ぶ側）。"""
    from .kernel import first_void

    void = first_void(run.res, run.incoming(), 1 - run.player, target, Window.BEFORE_EFFECT)
    if void is not None:
        raise run.res.question("counter_transfer_protected", f"ポケモン {target.pokemon_id}（{void.implementation.kind}。{detail}）")


@dataclass(frozen=True)
class HealCounters(Element):
    """ダメージカウンターをとりのぞく（回復。GR-2000-P320-RECOVERY「ダメージの回復は、かならず「ダメージカウンターをとりのぞく」ことによっておこなう。すべての
    ダメージカウンターをとりのぞいたら、それ以上の回復はできない」）（v0.41）。

    - ``scope``: 対象。``HEAL_SELF``（ワザを使ったポケモン）・``HEAL_OWN_ALL``（自分の場のポケモン全員: バトル場 → ベンチの順）・``HEAL_BOTH_ALL``（ワザを使った
      プレイヤーの場 → 相手の場の順に、それぞれバトル場 → ベンチ）・v0.104 の ``HEAL_BOTH_ACTIVE``（ワザを使ったポケモン → 相手の対戦ポケモン。やさしいうた）・v0.105 の
      ``HEAL_OPPONENT_ACTIVE``（相手の対戦ポケモンだけ。プレゼント）。どの順でも、とりのぞく数は変わらない（ポケモンごとに決まる）。順番はログの並びだけ
    - とりのぞく数: ``counters``（決まった数）か ``heads_of``（ワザ全体のコインの「おもて」の数。どのポケモンにも同じ数。ポケモンごとに投げ直さない。v0.104 の ``per_heads`` は
      「おもて」1 枚あたりの数（ミルクのみの「おもて」の数 × 2 個））か、v0.104 の ``every``（のっているすべて。おひるね・ねむる。大きな決まった数で表さない）のどれか 1 つ。
      それぞれのっている数まで。0 個のポケモンからはとりのぞかない（効果を受けない。p.309）
    - ``gate``（ワザ全体のコインの面）・``local_coin``（この要素のコイン。自分への効果だけを決めるので、相手の状態によらず投げる）
    - ワザを使ったポケモン（``HEAL_SELF``）がこのワザの中で HP 以上なら、処理の対象がいないので、コインを投げず、とりのぞかない（v0.31 の ``HealSelfOnHeads`` と同じ。
      ログ ``effect_skipped``）。ほかの対象も、HP 以上のポケモンは飛ばす
    - とりのぞくポケモンごとに、その効果を受ける前に「ワザをうけない」状態・「とうめい」を評価する（``reaches``。自分のワザでもはたらく。v0.9 の T8。2 匹以上なら T27）
    - 「ダメージを与えたら」の条件はない（やどりぎのタネの ``Drain`` とは別。説明に書かれた条件だけ）
    - ログは、とりのぞいたポケモンごとに ``attack_heal``（v0.31 のぼーっとすると同じ形。``player`` はそのポケモンの持ち主、相手のポケモンなら ``attacker``）
    """

    counters: int | None = None
    heads_of: str | None = None
    scope: str = E.HEAL_SELF
    gate: tuple | None = None
    local_coin: CoinSide | None = None
    per_heads: int = 1  # v0.104
    every: bool = False  # v0.104
    phase: ClassVar[Phase] = Phase.EFFECT

    def __post_init__(self) -> None:
        if [self.counters is not None, self.heads_of is not None, self.every].count(True) != 1:
            raise ValueError("とりのぞく数は counters・heads_of・every のどれか 1 つで決める")
        if type(self.per_heads) is not int or self.per_heads <= 0 or (self.per_heads != 1 and self.heads_of is None):
            raise ValueError(f"「おもて」1 枚あたりの数 {self.per_heads!r} は、heads_of のときだけの正の整数")
        if self.scope not in (E.HEAL_SELF, E.HEAL_OWN_ALL, E.HEAL_BOTH_ALL, E.HEAL_BOTH_BENCH, E.HEAL_BOTH_ACTIVE, E.HEAL_OPPONENT_ACTIVE):
            raise ValueError(f"回復の対象 {self.scope!r} は未定義")

    @property
    def opponent_element(self) -> str | None:
        return E.HEAL_ELEMENT if self.scope in (E.HEAL_BOTH_ALL, E.HEAL_BOTH_BENCH, E.HEAL_BOTH_ACTIVE, E.HEAL_OPPONENT_ACTIVE) else None

    def coin_receiver(self) -> str | None:
        # v0.105: 相手の対戦ポケモンだけからとりのぞく要素（プレゼントの「おもて」2 枚・0 枚）は、ワザ全体のコインが決める相手の対戦ポケモンへの効果の要素（``void_coin_question``）。
        # ほかの対象は v0.104 までと同じ（自分・控え・場の全員を含むので、相手の対戦ポケモンの状態で無効と数えない）
        return "effect" if self.scope == E.HEAL_OPPONENT_ACTIVE else None

    def targets(self, run: AttackRun) -> list[tuple[int, PokemonInPlay]]:
        if self.scope == E.HEAL_SELF:
            return [(run.player, run.attacker())]
        if self.scope == E.HEAL_OPPONENT_ACTIVE:
            return [(1 - run.player, run.opponent_active())]  # v0.105: 相手の対戦ポケモンだけ（プレゼント）
        if self.scope == E.HEAL_BOTH_ACTIVE:
            # v0.104: 自分（ワザを使ったポケモン）と相手（相手の対戦ポケモン）。控えは含めない（やさしいうた）
            return [(run.player, run.attacker()), (1 - run.player, run.opponent_active())]
        if self.scope == E.HEAL_BOTH_BENCH:
            # v0.83: おたがいの控えポケモン全員（やさしいシャワーズの「ヒプノシャワー」。ワザを使ったプレイヤーの控え → 相手の控え。対戦ポケモンは含めない）
            return [(side, pokemon) for side in (run.player, 1 - run.player) for pokemon in run.state.players[side].bench]
        sides = (run.player,) if self.scope == E.HEAL_OWN_ALL else (run.player, 1 - run.player)
        return [(side, pokemon) for side in sides for pokemon in run.state.players[side].in_play()]

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        state = run.state
        if self.scope == E.HEAL_SELF:
            attacker = run.attacker()
            if run.knocked_out(attacker):
                state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                element="heal", reason=E.EFFECT_TARGET_KNOCKED_OUT)
                return False
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        if self.every:
            count = None
        else:
            count = self.counters if self.heads_of is None else run.heads(self.heads_of) * self.per_heads
        per = state.rules.damage_per_counter
        for owner, pokemon in self.targets(run):
            if run.knocked_out(pokemon):
                continue
            removed = pokemon.damage // per if count is None else min(count, pokemon.damage // per)
            if removed <= 0 or not reaches(run.res, run.fs, owner, pokemon, E.HEAL_ELEMENT):
                continue
            before = pokemon.damage
            pokemon.damage = before - removed * per
            extra = {} if owner == run.player else {"attacker": run.player}
            state.add_event("attack_heal", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, effect=str(run.key),
                            counters=removed, amount=removed * per, damage_before=before, total_damage=pokemon.damage, **extra)
        return False


@dataclass(frozen=True)
class ShiftCountersToOpponent(Element):
    """自分と自分の控えポケモン全員から、ダメージカウンターを 1 つずつとりのぞき、とりのぞいたダメージカウンターをすべて、相手（相手の対戦ポケモン）にのせる
    （v0.41。ナツメのゴルダックの「ダメージシフト」）。

    - とりのぞくのは、カウンターが 1 つ以上のっているポケモンから 1 つずつ（ワザを使ったポケモン → ベンチの順。ログ ``attack_heal``。とりのぞく前に、そのポケモンの
      「とうめい」を評価する）。のせるのはとりのぞいた数（0 個ならのせない。ログ ``place_damage_counters``）
    - ダメージカウンターの移動で、相手は「ダメージを受けた」ことにならない（GR-2000-P320-COUNTER-MOVE）。ダメージの計算（弱点・抵抗力・プラスパワー・ディフェンダー）
      をせず、「ダメージを受けない」状態でものせる。「ダメージを受けたとき」の効果ははたらかない。のせたカウンターで HP 以上になった相手は、ワザのあとにきぜつする
      （「こんじょう」は使えない。``_counters_changed``）
    - 相手がのせる効果を受けない（「ワザをうけない」状態・「とうめい」）とき、自分の側をとりのぞくかは決められない（CX1）。「ワザをうけない」状態は、とりのぞく前に
      確かめる。「とうめい」は、のせる効果を受けるときに評価し、受けなければ問い（先読みがすべての結果を試すので、宣言の前に止まる）
    """

    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.COUNTERS_ELEMENT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        per = state.rules.damage_per_counter
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            raise RuntimeError(f"ワザ {run.key} の相手の対戦ポケモンが、ダメージカウンターをのせる前に HP 以上（このワザにダメージの要素はない。エンジンの不具合）")
        sources = [pokemon for pokemon in state.players[run.player].in_play() if not run.knocked_out(pokemon) and pokemon.damage >= per]
        if not sources:
            return False
        _counter_transfer_protected(run, target, "のせる")
        moved = 0
        for pokemon in sources:
            if not reaches(run.res, run.fs, run.player, pokemon, E.HEAL_ELEMENT):
                continue
            before = pokemon.damage
            pokemon.damage = before - per
            moved += 1
            state.add_event("attack_heal", player=run.player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, effect=str(run.key),
                            counters=1, amount=per, damage_before=before, total_damage=pokemon.damage)
        if not moved:
            return False
        if not reaches(run.res, run.fs, opponent, target, E.COUNTERS_ELEMENT):
            raise run.res.question("counter_transfer_protected", f"ポケモン {target.pokemon_id}（「とうめい」。のせる）")
        before = target.damage
        target.damage = before + moved * per
        state.add_event("place_damage_counters", player=opponent, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key),
                        counters=moved, amount=moved * per, damage_before=before, total_damage=target.damage, attacker=run.player,
                        attacker_pokemon_id=run.fs.frame.source_pid)
        _counters_changed(run, target, before)
        return False


@dataclass(frozen=True)
class SwapCounters(Element):
    """自分（ワザを使ったポケモン）にのっているダメージカウンターすべてと、相手（相手の対戦ポケモン）にのっているダメージカウンターすべてを、取り替える（v0.41。
    R団のミュウツーの「チェンジダメージ」。``gate`` はワザ全体のコインの面）。

    - 取り替える前の双方の数で処理する（片方を変えてから、変えたあとの数をもう片方に渡さない）。ログ ``swap_damage_counters``（前と後の両方の数）
    - ダメージカウンターの移動で、どちらも「ダメージを受けた」ことにならない（GR-2000-P320-COUNTER-MOVE）。ダメージの計算をせず、「ダメージを受けない」状態でも
      取り替える。取り替えたあと HP 以上のポケモンは、ワザのあとにきぜつする（両方なら同時のきぜつ。p.324。「こんじょう」は使えない）
    - 数が同じなら場は変わらないので、何もしない（効果を受けるポケモンがない。ログもない）
    - 相手が取り替える効果を受けない（「ワザをうけない」状態・「とうめい」）とき、自分の側を変えるかは決められない（CX1）
    """

    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.COUNTERS_ELEMENT

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        state = run.state
        opponent = 1 - run.player
        attacker, target = run.attacker(), run.opponent_active()
        if run.knocked_out(attacker) or run.knocked_out(target):
            raise RuntimeError(f"ワザ {run.key} のダメージカウンターを取り替える前に HP 以上のポケモンがいる（このワザにダメージの要素はない。エンジンの不具合）")
        own, theirs = attacker.damage, target.damage
        if own == theirs:
            return False
        _counter_transfer_protected(run, target, "取り替える")
        if not reaches(run.res, run.fs, opponent, target, E.COUNTERS_ELEMENT):
            raise run.res.question("counter_transfer_protected", f"ポケモン {target.pokemon_id}（「とうめい」。取り替える）")
        attacker.damage, target.damage = theirs, own
        state.add_event("swap_damage_counters", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                        damage_before=own, total_damage=attacker.damage, opponent=opponent, opponent_pokemon=target.card,
                        opponent_pokemon_id=target.pokemon_id, opponent_damage_before=theirs, opponent_total_damage=target.damage)
        _counters_changed(run, attacker, own)
        _counters_changed(run, target, theirs)
        return False


@dataclass(frozen=True)
class ChosenStatus(Element):
    """コインが ``local_coin`` なら、「ねむり・マヒ・こんらん・どく」の中から 1 つを選び、相手（相手の対戦ポケモン）をその状態にする（v0.41。エリカのクサイハナの
    「ミラクルかふん」）。

    - コインの前の確かめは ``Status`` の ``local_coin`` と同じ（このワザで HP 以上なら投げない（こんじょうを使えるなら G37）。「とうめい」で受けないと決まっていれば
      T19b、「ワザをうけない」状態なら HC3）
    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_SPECIAL_CONDITION``。選べるものは ``effects.CHOSEN_CONDITIONS`` の番号。1 つ）。マヒの再付与で回復する番が
      変わる場合は、マヒを選べるが選ぶと止める（``unresolved_choices``。v0.3b の ``UNRESOLVED_REPARALYSIS_RECOVERY_TURN``）
    - 選んだ状態にする前に、その効果を受けるかを評価する（``reaches``。「とうめい」の結果は、ダメージの要素で評価していればそれを使う（T4）。決定をまたいで運ぶ
      （``carry``））。状態の重なり・置きかえは、ほかの特殊状態の効果と同じ（``APPLY_CONDITION``。p.322）
    """

    local_coin: CoinSide | None = HEADS
    # v0.83: ワザ全体のコインの面（ひかるセレビィの「ミラクルリーフ」の「1枚でも「おもて」なら」。``AtLeast``）と、選べる特殊状態（None なら ``CHOSEN_CONDITIONS`` の 4 つ。
    # ミラクルリーフは「どく・ねむり・こんらん」。選べるものの番号は ``CHOSEN_CONDITIONS`` の番号のまま）
    gate: tuple | None = None
    conditions: tuple[str, ...] | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_SPECIAL_CONDITION

    def __post_init__(self) -> None:
        if self.conditions is not None and (not self.conditions or set(self.conditions) - set(E.CHOSEN_CONDITIONS)):
            raise ValueError(f"選べる特殊状態 {self.conditions!r} が CHOSEN_CONDITIONS の中にない")
        if self.gate is not None and self.local_coin is not None:
            raise ValueError("ワザ全体のコインとこの要素のコインの両方では決めない")

    def choices(self) -> tuple[int, ...]:
        return tuple(sorted(E.CHOSEN_CONDITIONS.index(c) for c in (self.conditions or E.CHOSEN_CONDITIONS)))

    @property
    def opponent_elements(self) -> tuple[str, ...]:
        return tuple(self.conditions or E.CHOSEN_CONDITIONS)

    def has_target(self, run: AttackRun) -> bool:
        return not run.knocked_out(run.opponent_active())

    def coin_receiver(self) -> str | None:
        return "effect"

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        owner, target = 1 - run.player, run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if self.local_coin is not None:
            if run.fs.reception.get(target.pokemon_id) is False:
                final = run.fs.evaded.get(target.pokemon_id)
                raise run.res.question("evaded_effect_coin", f"ポケモン {target.pokemon_id}",
                                       None if final is None else E.evaded_effect_coin_error(target.pokemon_id, final))
            prevented_effect_coin(run, owner, target)
            if run.flip(1).results[0] is not self.local_coin:
                return False
        extra: tuple = (("target", target.pokemon_id),)
        problem = paralysis_problem(run.state, owner, target) if PARALYSIS in (self.conditions or E.CHOSEN_CONDITIONS) else None
        if problem is not None:
            extra += (("unresolved_choices", (E.CHOSEN_CONDITIONS.index(PARALYSIS),)), ("unresolved_code", problem.code),
                      ("unresolved_reason", problem.message))
        run.suspend(kind=SELECT_SPECIAL_CONDITION, player=run.player, options=self.choices(), extra=extra, carry=True)
        return True

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ()))
        return [answer for answer in all_answers(decision) if not blocked & set(answer)]

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        owner, target = 1 - run.player, run.opponent_active()
        if target is None or target.pokemon_id != run.carried.get("target"):
            raise RuntimeError(f"特殊状態にする相手 {run.carried.get('target')} が相手のバトル場にいない（エンジンの不具合）")
        condition = E.CHOSEN_CONDITIONS[choices[0]]
        if not reaches(run.res, run.fs, owner, target, condition):
            return
        APPLY_CONDITION[condition](run.state, owner, target, effect=str(run.key))


@dataclass(frozen=True)
class AttachFromDeck(Element):
    """自分の山札から ``energy_type`` の基本エネルギーカードを 1 枚選び出し、このカード（ワザを使ったポケモン）につけてよい。その後、その山札をよく切る（v0.41。
    ロケット団のヤドンの「ひなたぼっこ」）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``ATTACH_FROM_DECK``。選べるものは山札の ``energy_type`` の基本エネルギーカード（uid の小さい順）。0〜1 枚）。選べるものが
      なければ決定を出さない（ログ ``attach_energy_from_deck_none`` の ``reason`` ``no_candidates``）。選ばなければ ``declined``
    - 山札から直接つける（``zones.attach_from_deck``。ログ ``attach_energy_from_deck``。つけたカードは公開。山札の中身はログに書かない）。手札からつける通常の操作・
      特殊能力でつけた枚数には数えない。つけたあと ``effects.after_energy_attached``（v0.31 の「ほのおでかいふく」などのエネルギーカードをつけたときの効果）
    - そのあと、どの場合も山札を切る（``shuffle_in_attack``。ログ ``shuffle`` に ``effect``。先読みでは切らない）

    v0.75（docs/search-energy-pokemon-v0.75.md 3 章）: 説明ごとの違いを明示した項目で表す（カードごとの分岐にしない）。

    - ``max_cards``: つける最大の枚数（キングラーの「しおまねき」は 3。つけるのは山札の uid の小さい順。選んだ順によらない）
    - ``zero``: 0 枚の答え。``ZERO_ALLOWED``（「つけてよい」。ひなたぼっこ・じゅうでん）・``ZERO_REQUIRED``（ちょうど 1 枚。0 枚は選べない。カツラのガーディの「もえあがる」の
      「…1枚を選び出し、自分につける」）・``ZERO_UNRESOLVED``（「最大3枚選び出し」。選べるものがあるときの 0 枚は v0.31 の HC7 と同じ問いで、答えのときに止める）
    - ``local_coin``: この要素のコイン（しおまねきは「おもて」なら）。山札の中身によらず投げる（自分の山札への効果。山札の中身を投げるかで漏らさない）。ワザを使ったポケモンが
      エネルギーカードをつけることができない（クリスタルビーム。公開の情報）なら、処理の対象がないので投げない
    - ``shuffle``: 山札を切るか（しおまねきの説明に「その後、その山札をよく切る」がないので切らない。GR-2000-P312-DECK-HAND-DISCARD）
    """

    energy_type: EnergyType
    max_cards: int = 1
    zero: str = "allowed"
    local_coin: CoinSide | None = None
    shuffle: bool = True
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = ATTACH_FROM_DECK

    def candidates(self, run: AttackRun) -> list[int]:
        rainbow_attach_question(run, run.state.players[run.player].deck, self.energy_type)  # v0.58: RB2
        return E.deck_energy_candidates(run.state, run.player, self.energy_type)

    def has_target(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        return not run.knocked_out(attacker) and E.energy_attach_block(run.state, attacker) is None

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            raise RuntimeError(f"ワザ {run.key} を使ったポケモンが、山札からエネルギーをつける前に HP 以上（このワザにダメージの要素はない。エンジンの不具合）")
        if E.energy_attach_block(run.state, attacker) is not None:
            # v0.59: クリスタルビームを受けている（エネルギーカードをつけることができない）。つけない（「つけてよい」の、つけないこと）。山札は今までどおり切る
            self._none(run, attacker, "attach_prevented")
            return False
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False  # v0.75: 「うら」なら何もしない（山札を見ない・切らない）
        candidates = self.candidates(run)
        if not candidates:
            self._none(run, attacker, "no_candidates")
            return False
        run.suspend(kind=ATTACH_FROM_DECK, player=run.player, options=candidates, min_choices=1 if self.zero == ZERO_REQUIRED else 0,
                    max_choices=min(self.max_cards, len(candidates)))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        attacker = run.attacker()
        if not choices:
            if self.zero == ZERO_UNRESOLVED:
                raise UnsupportedError(
                    "UNRESOLVED_ATTACH_FROM_DISCARD_ZERO",
                    f"山札に「{self.energy_type.ja}」エネルギーカードがあるときに 0 枚を選べるか（「最大{self.max_cards}枚選び出し、このカードにつける」が 0 枚を含むか）は"
                    "決められないので扱わない（v0.31 の HC7 と同じ問い）。1 枚以上を選ぶ",
                )
            if self.zero == ZERO_REQUIRED:
                raise RuntimeError(f"ワザ {run.key} で、つけるカードを選ばなかった（ちょうど 1 枚。エンジンの不具合）")
            self._none(run, attacker, "declined")
            return
        candidates = self.candidates(run)
        if len(set(choices)) != len(choices) or any(card not in candidates for card in choices):
            raise RuntimeError(f"つけるカード {choices} が、山札の「{self.energy_type.ja}」エネルギーカードではない（エンジンの不具合）")
        cards = tuple(uid for uid in candidates if uid in choices)  # 山札の uid の小さい順につける（選んだ順によらない）
        for card in cards:
            attach_from_deck(state, run.player, card, attacker)
            state.add_event("attach_energy_from_deck", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), card=card)
        for card in cards:
            attached_in_attack(run, run.player, attacker, (card,))
        if self.shuffle:
            shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        if self.max_cards == 1 and self.zero == ZERO_ALLOWED:
            return all_answers(decision)  # v0.41 のひなたぼっこと同じ（変えない）
        # v0.75: 同じカード id の基本エネルギーカードは、つけたあとも内容（カードの定義）が同じで、カードごとの状態を持たない。uid だけが違う答えは uid を入れかえた
        # 同じ形の状態になる（v0.46 の「せいちょう」（``AttachFromHand``）と同じまとめ方）。0 枚が問いになる説明（HC7）は、0 枚を試さない（答えのときに止める）
        low = 0 if self.zero == ZERO_ALLOWED else 1
        return card_id_answers(run.state, decision, range(low, decision.max_choices + 1))

    def _none(self, run: AttackRun, attacker: PokemonInPlay, reason: str) -> None:
        run.state.add_event("attach_energy_from_deck_none", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy_type=self.energy_type.value, reason=reason)
        if self.shuffle:
            shuffle_in_attack(run, self, run.player)


# v0.75: ``AttachFromDeck.zero`` の値
ZERO_ALLOWED = "allowed"
ZERO_REQUIRED = "required"
ZERO_UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class AttachFromDeckToBench(Element):
    """自分の山札から ``energy_type`` の基本エネルギーカードを 1 枚選び出し、自分の控えポケモンにつける。その後、山札をよく切る（v0.75。ナツメのスリープ（GD6-009）の
    「エナジーサポート」。kyuura の日本語の印刷の文面。英語の欄（手札に加える）とは違う。日本語の文面にしたがう）。

    - 決定は 2 つ: つけるカード（``ATTACH_FROM_DECK``。``context`` の ``"stage"`` は ``"card"``。ちょうど 1 枚（「…1枚選び出し、…つける」。「てよい」がない））→ つける控え
      （``ATTACH_TO_BENCH``。``"stage"`` は ``"bench"``・``"card"`` は選んだカード。1 匹）。どちらもワザを使ったプレイヤーが選ぶ。2 つの決定のあいだ、カードは山札にある
    - 控えポケモンがいない・山札に選べるカードがない: 処理の対象がないのでつけない（p.309。ログ ``attach_energy_from_deck_none`` の ``reason`` は ``no_bench``・
      ``no_candidates``）。どちらの場合も山札は切る（説明の「その後、山札をよく切る」に条件がない。v0.41 のひなたぼっこと同じ読み方）
    - つけるのはワザの効果なので、つける控えの「とうめい」を評価する。受けないなら、カードは持ち主のトラッシュに置く（v0.45 の「じりょくせん」・CR-TRANSPARENCY-ENERGY-BOMB と
      同じ読み方。実装上の判断。ログ ``deck_energy_evaded``）。エネルギーカードをつけることができない控え（v0.59）は選べるものに入れない
    - 山札から直接つける（``zones.attach_from_deck``。ログ ``attach_energy_from_deck`` の ``pokemon`` はつけた控え）。手札からつける通常の操作・特殊能力でつけた枚数には
      数えない。つけたら ``effects.after_energy_attached``
    """

    energy_type: EnergyType
    # v0.82: やさしいブースター（neo4-019）の「あたためる」の「自分の控えポケモンを1匹選ぶ。その後、自分の山札から「炎」エネルギーカードを1枚選び出し、選んだポケモンにつける。
    # 山札を見た場合は、その山札をよく切る。(自分に控えがいないとき、このワザは失敗する。)」。控え → カードの順に選び、控えがいなければワザの失敗（p.323 の 12）、山札を見た
    # （山札にカードがあった）ときだけ切る
    bench_first: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = ATTACH_FROM_DECK

    def decides(self, kind: str) -> bool:
        return kind in (ATTACH_FROM_DECK, ATTACH_TO_BENCH)

    def candidates(self, run: AttackRun) -> list[int]:
        rainbow_attach_question(run, run.state.players[run.player].deck, self.energy_type)  # v0.58: RB2
        return E.deck_energy_candidates(run.state, run.player, self.energy_type)

    def targets(self, run: AttackRun) -> list[PokemonInPlay]:
        return [p for p in run.state.players[run.player].bench if E.energy_attach_block(run.state, p) is None]

    def _bench_first_run(self, run: AttackRun) -> bool:
        if not run.state.players[run.player].bench:
            run.fail("no_bench")
            return False
        run.suspend(kind=ATTACH_TO_BENCH, player=run.player, options=[p.pokemon_id for p in self.targets(run)], carry=True, extra=(("stage", "bench"),))
        return True

    def _bench_first_resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        if run.carried.get("stage") == "bench":
            target = next((p for p in self.targets(run) if p.pokemon_id == choices[0]), None)
            if target is None:
                raise RuntimeError(f"つける控えポケモン {choices} が正しくない（エンジンの不具合）")
            if not state.players[run.player].deck:
                self._none(run, run.attacker(), "no_candidates", shuffle=False)  # 山札にカードがなく、見ていないので切らない
                return
            candidates = self.candidates(run)
            if not candidates:
                self._none(run, run.attacker(), "no_candidates")
                return
            run.suspend(kind=ATTACH_FROM_DECK, player=run.player, options=candidates, min_choices=1, max_choices=1, carry=True,
                        extra=(("stage", "card"), ("target", target.pokemon_id)))
            return
        card = choices[0]
        target = next((p for p in self.targets(run) if p.pokemon_id == run.carried["target"]), None)
        if len(choices) != 1 or card not in self.candidates(run) or target is None:
            raise RuntimeError(f"つけるカード {choices}・控えポケモン {run.carried.get('target')} が正しくない（エンジンの不具合）")
        self._attach(run, card, target)

    def _attach(self, run: AttackRun, card: int, target: PokemonInPlay) -> None:
        state = run.state
        if reaches(run.res, run.fs, run.player, target, E.ENERGY_ATTACH_ELEMENT):
            attach_from_deck(state, run.player, card, target)
            state.add_event("attach_energy_from_deck", player=run.player, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key), card=card)
            attached_in_attack(run, run.player, target, (card,))
        else:
            state.players[run.player].deck.remove(card)
            state.players[run.player].discard.append(card)  # 「とうめい」の「おもて」: カードは持ち主のトラッシュ（CR-TRANSPARENCY-ENERGY-BOMB と同じ読み方）
            state.add_event("deck_energy_evaded", player=run.player, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key), card=card)
        shuffle_in_attack(run, self, run.player)

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            raise RuntimeError(f"ワザ {run.key} を使ったポケモンが、山札からエネルギーをつける前に HP 以上（このワザにダメージの要素はない。エンジンの不具合）")
        if self.bench_first:
            return self._bench_first_run(run)
        if not self.targets(run):
            self._none(run, attacker, "no_bench")
            return False
        candidates = self.candidates(run)
        if not candidates:
            self._none(run, attacker, "no_candidates")
            return False
        run.suspend(kind=ATTACH_FROM_DECK, player=run.player, options=candidates, min_choices=1, max_choices=1, carry=True, extra=(("stage", "card"),))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if self.bench_first:
            self._bench_first_resume(run, decision, choices)
            return
        state = run.state
        if decision.kind == ATTACH_FROM_DECK:
            if len(choices) != 1 or choices[0] not in self.candidates(run):
                raise RuntimeError(f"つけるカード {choices} が、山札の「{self.energy_type.ja}」エネルギーカードではない（エンジンの不具合）")
            run.suspend(kind=ATTACH_TO_BENCH, player=run.player, options=[p.pokemon_id for p in self.targets(run)], carry=True,
                        extra=(("stage", "bench"), ("card", choices[0])))
            return
        card = run.carried["card"]
        target = next((p for p in self.targets(run) if p.pokemon_id == choices[0]), None)
        if card not in state.players[run.player].deck or target is None:
            raise RuntimeError(f"つけるカード {card}・控えポケモン {choices} が正しくない（エンジンの不具合）")
        if reaches(run.res, run.fs, run.player, target, E.ENERGY_ATTACH_ELEMENT):
            attach_from_deck(state, run.player, card, target)
            state.add_event("attach_energy_from_deck", player=run.player, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key), card=card)
            attached_in_attack(run, run.player, target, (card,))
        else:
            state.players[run.player].deck.remove(card)
            state.players[run.player].discard.append(card)  # 「とうめい」の「おもて」: カードは持ち主のトラッシュ（CR-TRANSPARENCY-ENERGY-BOMB と同じ読み方）
            state.add_event("deck_energy_evaded", player=run.player, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key), card=card)
        shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        if decision.kind == ATTACH_FROM_DECK:
            return card_id_answers(run.state, decision, (1,))  # 同じカード id の基本エネルギーカードは、どれをつけても同じ形の状態（v0.46 の AttachFromHand と同じ）
        return all_answers(decision)

    def _none(self, run: AttackRun, attacker: PokemonInPlay, reason: str, *, shuffle: bool = True) -> None:
        run.state.add_event("attach_energy_from_deck_none", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy_type=self.energy_type.value, reason=reason)
        if shuffle:
            shuffle_in_attack(run, self, run.player)


@dataclass(frozen=True)
class RevealNamedPokemonFromDeck(Element):
    """自分の山札から、名前が ``names`` のどれかのポケモンのカードを好きなだけさがし出し、相手プレイヤーに見せてから、手札に加えてよい。その後、その山札をよく切る
    （v0.75。カスミのメノクラゲ（GD2-003）の「くらげのむれ」。kyuura の印刷の文面。docs/search-energy-pokemon-v0.75.md 4 章）。

    - 選べるものは山札の、名前（その場所の印刷の名前）が ``names`` のどれかと完全に同じポケモンのカード（段階は問わない。同じ名前の別の id のカードも選べる。uid の小さい順。
      ``effects.deck_named_pokemon``）。名前の一部・「カスミの」などの始まりで選ばない
    - 選ぶのはワザを使ったプレイヤー（決定 ``SEARCH_DECK``。0〜選べるものの数。「好きなだけ」「加えてよい」なので 0 枚・すべても選べる。0 枚は「てよい」の、加えないこと
      （ログ ``reveal_from_deck_declined``）で、v0.39 の GS1（「最大3匹」）・v0.31 の HC7（「最大2枚」）の問いとは書き方が違う）。同じカードを 2 回選べない
      （``DUPLICATE_CHOICE``）。山札にないカードは選べない
    - 選んだカードだけを見せて手札に加える（v0.24 の ``zones.reveal_deck_to_hand``。1 枚に 1 つのログ ``reveal_from_deck``。山札の uid の小さい順。選んだ順によらない）。
      選べたほかのカードはログに書かない。選べるものがなければ加えない（ログ ``reveal_from_deck_none``）
    - そのあと、どの場合も山札を 1 回だけ切る（``shuffle_in_attack``）
    - 先読み: 選んだカードは手札に入るだけで、このあとの要素はない（最後の要素。山札の並びを使う要素もない）。同じカード id のカードは内容が同じなので、uid だけが違う答えを
      まとめる（``card_id_answers``。v0.44）。選ぶ枚数・カード id の組み合わせは、すべて試す（1 つの代表にまとめない）
    """

    names: tuple[str, ...]
    # v0.83: ちょうど 1 枚（ひかるコイキングの「りゅうのきずな」の「1枚を選び出し」。「好きなだけ」「てよい」がないので 0 枚は選べない。選べるものがなければ選ばずに切る）
    exactly_one: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SEARCH_DECK

    def candidates(self, run: AttackRun) -> list[int]:
        return E.deck_named_pokemon(run.state, run.player, self.names)

    def run(self, run: AttackRun) -> bool:
        candidates = self.candidates(run)
        if not candidates:
            run.state.add_event("reveal_from_deck_none", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key), category="named_pokemon")
            shuffle_in_attack(run, self, run.player)
            return False
        low, high = (1, 1) if self.exactly_one else (0, len(candidates))
        run.suspend(kind=SEARCH_DECK, player=run.player, options=candidates, min_choices=low, max_choices=high)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if choices:
            candidates = self.candidates(run)
            if len(set(choices)) != len(choices) or any(card not in candidates for card in choices):
                raise RuntimeError(f"選んだカード {choices} が、山札の選べるポケモンのカードではない（エンジンの不具合）")
            for card in sorted(choices):
                reveal_deck_to_hand(run.state, run.player, card, effect=str(run.key))
        else:
            run.state.add_event("reveal_from_deck_declined", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key), category="named_pokemon")
        shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, range(decision.min_choices, decision.max_choices + 1))


@dataclass(frozen=True)
class RecoverEnergyByHeads(Element):
    """ワザ全体のコイン ``heads_of`` の「おもて」の数ぶんの ``energy_type`` エネルギーカードを、自分のトラッシュから選び出し、手札に加える（v0.75。カツラのロコン（GD5-003）の
    「おにびあつめ」の「コインを3枚投げ、「おもて」の数ぶんの「炎」エネルギーカードを自分のトラッシュから選び出し、手札に加える。」。kyuura の印刷の文面）。

    - 選べるものは自分のトラッシュの ``energy_type`` の基本エネルギーカード。トラッシュのレインボーエネルギーが「「炎」エネルギーカード」に当たるかは決まらない（RB5。v0.58 の
      RB2・v0.73 の FV1 と同じ種類の、別の場面の問い）ので、あれば止める（コインの前。先読みが宣言の前に見つける）
    - 「おもて」が 0 なら何もしない（ワザの失敗ではない）。選べるものの数が「おもて」の数以上なら、ちょうど「おもて」の数を選ぶ（決定 ``RECOVER_ENERGY``。ワザを使ったプレイヤー）。
      「おもての数ぶん」を「最大」と読みかえない。選べるものが 1 枚以上で「おもて」の数より少ないときは、説明の枚数を選べないので決められない（v0.44 の FC1
      ``stated_cards_short``。kyuura の UQ-STATED-COUNT-SHORT。先読みが宣言の前に見つける）。選べるものがなければ処理の対象がない（p.309）
    - 選べるものがないなら、このコインが決める要素に処理の対象がないので、コインを投げない（v0.38 の ``has_target``）。トラッシュは公開の情報
    - 場のポケモンタワー（v0.74）で、この要素（トラッシュから手札に加える）の効果が消える。処理の対象がないので、コインを投げない（ログ ``discard_to_hand_suppressed``）
    - 手札に加えるのは ``zones.return_discard_to_hand``（ログ ``recover_energy``。v0.9 のエナジーへんかんと同じ形。トラッシュの並びの順。選んだ順によらない）
    """

    energy_type: EnergyType
    heads_of: str
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = RECOVER_ENERGY

    def candidates(self, run: AttackRun) -> list[int]:
        rainbow = E.rainbow_cards_in(run.state, run.state.players[run.player].discard)
        if rainbow:
            raise run.res.question("rainbow_recover_type", f"トラッシュのレインボーエネルギー {rainbow}・「{self.energy_type.ja}」エネルギーカード")
        return [uid for uid in run.state.players[run.player].discard
                if run.state.card_def(uid).is_basic_energy and run.state.card_def(uid).provides is self.energy_type]

    def has_target(self, run: AttackRun) -> bool:
        return E.discard_to_hand_suppressor(run.state) is None and bool(self.candidates(run))

    discard_protected = _discard_protected

    def run(self, run: AttackRun) -> bool:
        if suppressed_discard_to_hand(run):
            return False  # v0.74: ポケモンタワーで、この要素の効果が消える
        heads = run.heads(self.heads_of)
        if heads and protected_discard(run, "recover_energy"):
            return False  # v0.119: ［アレルギーほうし］（選べるカードがあればコインの前に AP1 で止まるので、ここに来るのはコインのあとに力がはたらきはじめたときだけ）
        candidates = self.candidates(run)
        if not heads or not candidates:
            return False
        if len(candidates) < heads:
            raise run.res.question("stated_cards_short", f"トラッシュの「{self.energy_type.ja}」エネルギーカード {len(candidates)} 枚（「おもて」の数 {heads}）")
        run.suspend(kind=RECOVER_ENERGY, player=run.player, options=candidates, min_choices=heads, max_choices=heads)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        candidates = self.candidates(run)
        if len(choices) != run.heads(self.heads_of) or len(set(choices)) != len(choices) or any(uid not in candidates for uid in choices):
            raise RuntimeError(f"手札に加えるカード {choices} が、トラッシュの「{self.energy_type.ja}」エネルギーカードの「おもて」の数ではない（エンジンの不具合）")
        cards = tuple(uid for uid in run.state.players[run.player].discard if uid in choices)
        return_discard_to_hand(run.state, run.player, cards)
        attacker = run.attacker()
        run.state.add_event("recover_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), cards=cards)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, (decision.min_choices,))


# ---------------------------------------------------------------- v0.42（docs/power-decisions-v0.42.md）


@dataclass(frozen=True)
class ChosenOpponentHealThenDraw(Element):
    """相手の場にいるポケモンを 1 匹選び、そのポケモンにのっているダメージカウンターを、好きなだけとりのぞく。とりのぞいた数ぶんのカードを自分の山札から引いて、
    手札に加える（v0.42。ナツメのルージュラの「よいおこない」。kyuura の印刷の文面）。

    - 選ぶのはワザを使ったプレイヤー: ポケモン（決定 ``SELECT_POKEMON``。相手の場のポケモン全員（バトル場 → ベンチ）。ダメージカウンターのないポケモンも選べる
      （説明は「相手の場にいるポケモンを1匹選び」。そのときはとりのぞく数も引く数も 0））→ とりのぞく数（決定 ``REMOVE_COUNTERS``。0〜のっている数。``context`` の
      ``"target"``）。相手のどのポケモンにもカウンターがなければ、どれを選んでも何も起こらないので決定を出さない（p.309）
    - 0 を選べるか（「好きなだけ」に 0 を含むか）は決められない（v0.31 の HC5 と同じ問い。「のぞむなら」がない。v0.40 の GR5）。0 は選べるが選ぶと止める
      （``unresolved_choices``。``UNRESOLVED_DISCARD_ANY_NUMBER_ZERO``）
    - とりのぞく前に、そのポケモンの「ワザをうけない」状態・「とうめい」を評価する（相手のポケモンへの効果。``reaches`` の ``heal``。v0.41 の ``HealCounters`` と同じ）。
      受けなければ、とりのぞかず、引かない（とりのぞいた数は 0）。回復は、のっている数まで（GR-2000-P320-RECOVERY）。ログ ``attack_heal``（``attacker`` つき）
    - 引くのは、実際にとりのぞいた数。山札が足りなければ引けるだけ（効果で引くときの規定。p.312。v0.31 の ``Draw`` と同じ）
    """

    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.HEAL_ELEMENT
    reads_deck_order: ClassVar[bool] = True

    def decides(self, kind: str) -> bool:
        return kind in (SELECT_POKEMON, REMOVE_COUNTERS)

    def run(self, run: AttackRun) -> bool:
        per = run.state.rules.damage_per_counter
        pokemon = [p for p in run.state.players[1 - run.player].in_play() if not run.knocked_out(p)]
        if not any(p.damage >= per for p in pokemon):
            return False
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=[p.pokemon_id for p in pokemon])
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        per = state.rules.damage_per_counter
        if decision.kind == SELECT_POKEMON:
            found = state.find_pokemon(choices[0])
            if found is None or found[0] != 1 - run.player:
                raise RuntimeError(f"よいおこないで選んだポケモン {choices} が、相手の場にいない（エンジンの不具合）")
            target = found[1]
            counters = target.damage // per
            if counters <= 0:
                return  # とりのぞく数も、引く数も 0
            code = "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO"
            reason = "「好きなだけとりのぞく」で 0 個を選べるかは決められないので扱わない（v0.31 の HC5 と同じ問い。1 個以上を選ぶ）"
            run.suspend(kind=REMOVE_COUNTERS, player=run.player, options=range(counters + 1),
                        extra=(("target", target.pokemon_id), ("unresolved_choices", (0,)), ("unresolved_code", code), ("unresolved_reason", reason)))
            return
        found = state.find_pokemon(decision.context_value("target"))
        if found is None or found[0] != 1 - run.player or not 1 <= choices[0] <= found[1].damage // per:
            raise RuntimeError(f"よいおこないでとりのぞく数 {choices}・ポケモン {decision.context_value('target')} が正しくない（エンジンの不具合）")
        owner, target = found
        if not reaches(run.res, run.fs, owner, target, E.HEAL_ELEMENT):
            return
        before = target.damage
        removed = choices[0]
        target.damage = before - removed * per
        state.add_event("attack_heal", player=owner, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key), counters=removed,
                        amount=removed * per, damage_before=before, total_damage=target.damage, attacker=run.player)
        draw_cards(state, run.player, min(removed, len(state.players[run.player].deck)))

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ()))
        return [answer for answer in all_answers(decision) if not blocked & set(answer)]


@dataclass(frozen=True)
class ReturnOwnEnergyToHand(DiscardOwnEnergy):
    """ワザを使ったポケモン自身についている ``energy_type`` のエネルギーカードを選び、はがして手札にもどす（v0.42。ナツメのケーシィの「エネループ」の「自分に
    ついている「超」エネルギーカードを1枚選び、はがして手札にもどす。」）。トラッシュの要素 ``DiscardOwnEnergy`` と、選び方（ついている順。1 枚でも決定を出す。
    選ぶのはワザを使ったプレイヤー）・時点（``timing``）・トラッシュできないとき（``when_lacking``）・相手のワザとして使うとき（``copy_problem``）が同じで、行き先
    だけが違う（手札。ログ ``return_energy_to_hand``。決定の種類 ``RETURN_ENERGY``）。

    - 時点: 印刷の文面の「はがして」が、ワザを使うための条件か効果か（こんらんのコインの前か後か）は、v0.31 の「はがしてすてる」と同じく決められない（HC1 と同じ問い。
      トラッシュではないが、RUL-ENERGY-DISCARD-ATTACKS の範囲（炎エネルギーカードをトラッシュするワザ）の外）。こんらん状態で使うときだけ宣言のあとに止める
      （``TIMING_UNRESOLVED``）。こんらんでなければ、どちらの読み方でも結果は同じ
    - ダメージの要素より前（v0.31 の「はがしてすてる」ワザ（10まんボルト）と同じ並び）
    """

    decision_kind: ClassVar[str] = RETURN_ENERGY

    def on_declare(self, res: Resolution, player: int, attacker: PokemonInPlay) -> None:
        if self.timing == TIMING_UNRESOLVED and attacker.conditions.confused:
            # 問いの文は v0.31 の「はがしてすてる」のもの（変えない）。手札にもどすワザでも同じ問いであることを、ここで書き足す
            raise res.question("discard_energy_timing", f"ポケモン {attacker.pokemon_id}。「はがして手札にもどす」と書かれたワザも同じ問い")
        if self.timing == TIMING_UNRESOLVED and E.baby_rule_applies(res.state, player):
            raise res.question("discard_energy_timing", f"ポケモン {attacker.pokemon_id}（相手のバトル場のベイビィポケモンのルールのコイン）。「はがして手札にもどす」と書かれたワザも同じ問い")

    def _discard(self, run: AttackRun, cards: tuple[int, ...]) -> None:
        state = run.state
        owner, attacker = state.find_pokemon(run.fs.frame.source_pid)
        for energy in cards:
            attacker.energy.remove(energy)
            state.players[owner].hand.append(energy)
            state.add_event("return_energy_to_hand", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy=energy)
        run.fs.results[self.name] = Discarded(cards)


@dataclass(frozen=True)
class CountersToRemainingHp(Element):
    """コインを投げて ``local_coin`` なら、残り HP が ``remaining`` になるように、相手（相手の対戦ポケモン）にダメージカウンターをのせる（v0.42。ナツメの
    ユンゲラーの「ライフダウン」）。

    - のせる数は（HP − ``remaining`` − のっているダメージ）÷ 10。HP はいちばん上のカードの値。すでに残り HP が ``remaining`` 以下（バトル場のポケモンはきぜつ
      していないので、ちょうど ``remaining``）なら 0 個で、効果を受けない（v0.41 の回復で 0 個のポケモンと同じ。GR-2000-P309-ATTACK-PROCEDURE）。コインは投げる
      （対象のポケモンはいる）
    - ダメージカウンターをのせることはワザによるダメージではない（GR-2000-P320-COUNTER-MOVE。v0.41 の ``ShiftCountersToOpponent`` と同じ）。ダメージの計算
      （弱点・抵抗力・プラスパワー・ディフェンダー）をせず、「ダメージを受けない」状態（かたまる）でものせる。「ダメージを受けたとき」の効果ははたらかない。
      残り HP が ``remaining`` になるので、きぜつしない
    - 相手への効果なので、のせる前に「ワザをうけない」状態・「とうめい」を評価する（``reaches`` の ``damage_counters``）。コインはこの効果だけを決めるので、
      「ワザをうけない」相手には投げるかが決められない（HC3）。前の要素で「とうめい」で受けないと決まった相手は T19b（このワザには前の要素がない）
    - ログ ``place_damage_counters``（v0.41 と同じ形。``attacker``・``attacker_pokemon_id``）
    """

    remaining: int = 10
    local_coin: CoinSide | None = HEADS
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.COUNTERS_ELEMENT

    def coin_receiver(self) -> str | None:
        return "effect"

    def run(self, run: AttackRun) -> bool:
        state = run.state
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            raise RuntimeError(f"ワザ {run.key} の相手の対戦ポケモンが、ダメージカウンターをのせる前に HP 以上（このワザにダメージの要素はない。エンジンの不具合）")
        if self.local_coin is not None:
            if run.fs.reception.get(target.pokemon_id) is False:
                final = run.fs.evaded.get(target.pokemon_id)
                raise run.res.question("evaded_effect_coin", f"ポケモン {target.pokemon_id}",
                                       None if final is None else E.evaded_effect_coin_error(target.pokemon_id, final))
            prevented_effect_coin(run, opponent, target)
            if run.flip(1).results[0] is not self.local_coin:
                return False
        per = state.rules.damage_per_counter
        hp = E.max_hp(state, target)  # v0.48: 今有効な最大HP（「残り HP が 10 になるように」）
        count = (hp - self.remaining - target.damage) // per
        if count <= 0:
            return False
        if not reaches(run.res, run.fs, opponent, target, E.COUNTERS_ELEMENT):
            return False
        before = target.damage
        target.damage = before + count * per
        state.add_event("place_damage_counters", player=opponent, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key),
                        counters=count, amount=count * per, damage_before=before, total_damage=target.damage, attacker=run.player,
                        attacker_pokemon_id=run.fs.frame.source_pid)
        _counters_changed(run, target, before)
        return False


def suspend_evolution_heal(run: AttackRun, owner: int, pokemon: PokemonInPlay, before_name: str) -> bool:
    """ワザで山札から重ねて進化させたポケモンに、場のトキワシティジムの機会があれば、ワザの途中の決定（``EVOLUTION_HEAL``。決めるのは持ち主。0〜1 個。カウンターが
    1 つだけなら VG1 で選ぶと止める）を出して True（v0.57。docs/stadiums-v0.57.md 5 章）。答え（``resume_evolution_heal``）のあと、その要素の残り（山札を切る）に進む。"""
    terms = E.evolution_heal_terms(run.state, pokemon, before_name)
    if terms is None:
        return False
    stadium, _, one = terms
    extra: tuple = (("heal_stadium", stadium.card), ("heal_pokemon", pokemon.pokemon_id))
    if one:
        extra += (("unresolved_choices", (pokemon.pokemon_id,)), ("unresolved_code", E.VIRIDIAN_GYM_ONE_COUNTER_CODE),
                  ("unresolved_reason", E.VIRIDIAN_GYM_ONE_COUNTER_REASON))
    run.suspend(kind=EVOLUTION_HEAL, player=owner, options=(pokemon.pokemon_id,), min_choices=0, max_choices=1, extra=extra)
    return True


def resume_evolution_heal(run: AttackRun, element: Element, decision: PendingDecision, choices: tuple[int, ...]) -> None:
    """トキワシティジムの答え（v0.57）: ダメージカウンターをとりのぞく（``effects.apply_evolution_heal``）か、とりのぞかないで、その要素の残り（山札を切る）。"""
    found = run.state.find_pokemon(decision.context_value("heal_pokemon"))
    if found is None:
        raise RuntimeError(f"トキワシティジムの決定のポケモン {decision.context_value('heal_pokemon')} が場にいない（エンジンの不具合）")
    E.apply_evolution_heal(run.state, found[0], found[1], decision.context_value("heal_stadium"), bool(choices))
    shuffle_in_attack(run, element, run.player)


@dataclass(frozen=True)
class EvolveFromDeck(Element):
    """コインを投げて ``local_coin`` なら、自分の山札から、自分または自分の控えポケモンを進化させる「進化カード」を 1 枚選び出し、そのポケモンの上にのせる。その後、
    その山札をよく切る（v0.42。エリカのピッピの「つきのちから」。kyuura の印刷の文面。ワザを使ったポケモン自身も進化できることは kyuura の
    data/curation/card_differences.json のエリカのピッピの記録（確度: 確実）が引く p.223 の解説と同じ）。

    - 選ぶのはワザを使ったプレイヤー: 進化カード（決定 ``SEARCH_DECK``。選べるものは山札の進化カードのうち、自分の場のポケモンに今重ねられるもの。uid の小さい順。
      ``effects.deck_evolution_candidates``）→ そのカードを重ねられるポケモンが 2 匹以上なら、重ねるポケモン（決定 ``SELECT_POKEMON``。``context`` の ``"card"``）
    - 重ねられるかは通常の進化と同じ（``evolution.evolution_block``。おたがいの最初の番・名前・その番の最初から場にいたか（この番に場に出した・進化したポケモンは
      不可）・段階。p.310）。ワザによる進化だからという理由で制限を免除しない。進化したあとの HP がダメージ以下になる組は、選べるが選ぶと止める（v0.4a の H1。
      ``UNRESOLVED_EVOLUTION_HP``）
    - 重ねる前に、そのポケモンの「とうめい」を評価する（自分への効果。``reaches`` の ``evolve``）。受けなければ重ねない
    - 進化は通常の進化と同じ手順（``evolution.place_evolution_card``。山札から。ログ ``evolve`` の ``effect``・``source_zone``）。ワザを使ったポケモン自身が進化した
      ら、ワザの残り（山札を切る）のあと、番は終わる
    - 選べる進化カードがない（山札に進化カードがない・重ねられるポケモンがいない・最初の番）なら、出さない（ログ ``evolve_from_deck_none``）。どの場合も、コインが
      ``local_coin`` なら山札を切る（1 回。説明の「その後、その山札をよく切る」）。先読みでは切らない（``shuffle_in_attack``）
    """

    local_coin: CoinSide | None = HEADS
    phase: ClassVar[Phase] = Phase.EFFECT

    def decides(self, kind: str) -> bool:
        return kind in (SEARCH_DECK, SELECT_POKEMON, EVOLUTION_HEAL)  # v0.57: トキワシティジム

    def run(self, run: AttackRun) -> bool:
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        permitted = E.deck_evolution_permission_pairs(run.state, run.player)
        if permitted:
            # v0.44: トレーナー「サカキ」の許可だけで重ねられる組がある（GV1）。重ねられるかで選べるものが変わるので、決定を出す前に止める（v0.45 から停止コード
            # ``UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK``。v0.44 はコードのない問いで、自分の場のサカキのコイキングに許可があると内部エラーになっていた）
            raise run.res.question("evolution_permission_from_deck", f"山札の進化カードと場のポケモン {list(permitted)}")
        devolved = E.deck_evolution_devolved_pairs(run.state, run.player)
        if devolved:
            # v0.50: 今の番に退化したポケモンに重ねられる組（DV2）。GV1 と同じく、選べるものが変わるので決定を出す前に止める
            raise run.res.question("evolve_after_devolution", f"山札の進化カードと場のポケモン {list(devolved)}")
        candidates = E.deck_evolution_candidates(run.state, run.player)
        if not candidates:
            run.state.add_event("evolve_from_deck_none", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key))
            shuffle_in_attack(run, self, run.player)
            return False
        blocked = tuple(card for card, targets in candidates.items()
                        if len(E.evolution_hp_problem_targets(run.state, card, targets)) == len(targets))
        # v0.43: 場に出たときに使える特殊能力を持つ進化カード（わるいカイリューの［てしたをよぶ］）を重ねると、ワザの最中に特殊能力を使う機会が来る（PW4）。
        # 選べるが選ぶと止める（``entry_power_choices``。答えのときに止める）
        # v0.86: 重ねられるポケモンがどれも、ほかのポケモンの［れんさしんか］の機会が来るポケモンのカードも同じ（PW4。``effects.deck_evolution_entry_cards``）
        entry = E.deck_evolution_entry_cards(run.state, run.player, candidates, blocked)
        if len(blocked) + len(entry) == len(candidates):
            # どの進化カードも選ぶと止める（v0.42 では、先読みが選べる答えのない決定で内部エラーになっていた。docs/declared-entry-powers-v0.43.md 4.3）
            if entry:
                raise run.res.question("entry_power_during_attack", f"山札の進化カード {list(entry)}")
            raise run.res.question("evolution_hp_every_card", f"山札の進化カード {list(blocked)}")
        extra: tuple = ()
        if blocked:
            extra = (("unresolved_choices", blocked), ("unresolved_code", "UNRESOLVED_EVOLUTION_HP"), ("unresolved_reason", E.EVOLUTION_HP_REASON))
        if entry:
            extra += (("entry_power_choices", entry),)
        run.suspend(kind=SEARCH_DECK, player=run.player, options=tuple(candidates), extra=extra)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if decision.kind == EVOLUTION_HEAL:
            resume_evolution_heal(run, self, decision, choices)
            return
        candidates = E.deck_evolution_candidates(run.state, run.player)
        if decision.kind == SEARCH_DECK:
            card = choices[0]
            if card not in candidates:
                raise RuntimeError(f"つきのちからで選んだカード {choices} が、山札の重ねられる進化カードではない（エンジンの不具合）")
            if card in decision.context_value("entry_power_choices", ()):
                question = QUESTIONS["entry_power_during_attack"]
                raise UnsupportedError(question.code, f"{question.message}（PW4。山札の進化カード {card}）")
            targets = candidates[card]
            if len(targets) == 1:
                self._evolve(run, card, targets[0])
                return
            blocked = E.evolution_hp_problem_targets(run.state, card, targets)
            extra: tuple = (("card", card),)
            if blocked:
                extra += (("unresolved_choices", blocked), ("unresolved_code", "UNRESOLVED_EVOLUTION_HP"), ("unresolved_reason", E.EVOLUTION_HP_REASON))
            chain = E.chain_evolution_targets(run.state, run.player, [pid for pid in targets if pid not in blocked])
            if chain:
                extra += (("entry_power_choices", chain),)  # v0.86: 重ねるとほかのポケモンの［れんさしんか］の機会が来るポケモン（PW4。選ぶと止める）
            run.suspend(kind=SELECT_POKEMON, player=run.player, options=targets, extra=extra)
            return
        card = decision.context_value("card")
        if card not in candidates or choices[0] not in candidates[card]:
            raise RuntimeError(f"つきのちからで重ねるポケモン {choices}（カード {card}）が、重ねられるポケモンではない（エンジンの不具合）")
        if choices[0] in decision.context_value("entry_power_choices", ()):
            question = QUESTIONS["entry_power_during_attack"]
            raise UnsupportedError(question.code, f"{question.message}（PW4。［れんさしんか］の機会が来るポケモン {choices[0]}）")
        self._evolve(run, card, choices[0])

    def _evolve(self, run: AttackRun, card: int, pokemon_id: int) -> None:
        state = run.state
        owner, target = state.find_pokemon(pokemon_id)
        if target.damage >= E.evolution_hp(state, target, card):  # v0.48: 重ねたあとの最大HP
            raise RuntimeError(f"進化すると HP がダメージ以下になる組（カード {card}・ポケモン {pokemon_id}）を選んだ（選ぶと止める選択の漏れ。エンジンの不具合）")
        if reaches(run.res, run.fs, owner, target, E.EVOLVE_ELEMENT):
            before_name = E.form_def(state, target).name_ja
            place_evolution_card(state, owner, target, card, effect=str(run.key))
            if suspend_evolution_heal(run, owner, target, before_name):  # v0.57: トキワシティジム（答えたあとに山札を切る）
                return
        shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ())) | set(decision.context_value("entry_power_choices", ()))
        return [answer for answer in all_answers(decision) if not blocked & set(answer)]


@dataclass(frozen=True)
class ReturnOwnPokemonToHand(Element):
    """コインを投げて ``local_coin`` なら、自分の場にいるポケモンを好きなだけ選び、そのポケモンと、それらについているすべてのカードを手札にもどす（v0.42。エリカの
    ピクシーの「ようせいのきせき」。kyuura の印刷の文面）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。選べるものは自分の場のポケモン全員（バトル場 → ベンチ。ワザを使ったポケモンを含む）。0〜全員）。
      0 匹を選べるか（「好きなだけ」に 0 を含むか）は決められない（v0.31 の HC5 と同じ問い。答えのときに止め、決定は待ったまま）
    - もどすのは、重なったカードを含むポケモンと、ついているエネルギー・トレーナーのすべて（``zones.return_in_play_to_hand``。手札。山札にもどす v0.36 の
      ``ReturnSelfToDeck`` とは行き先が違い、山札を切らない）。持続する効果を消す（理由 ``return_in_play_to_hand``）。もどす前に、そのポケモンの「とうめい」を
      評価する（自分への効果。``reaches`` の ``return_in_play_to_hand``。2 匹以上なら T27）。選んだ順ではなく場の順（バトル場 → ベンチ）に処理する
    - きぜつではない（サイドは取られない）。バトル場のポケモンをもどしたら、ワザのあとの勝ち負けの判定（場にポケモンがいないプレイヤーは負ける。p.311）とバトル場に
      出す決定で空いたバトル場をうめる（v0.36 のくもがくれガスと同じ）。このワザにダメージの要素はないので、同じワザで HP 以上になったポケモンはいない
    """

    local_coin: CoinSide | None = HEADS
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def run(self, run: AttackRun) -> bool:
        options = [p.pokemon_id for p in run.state.players[run.player].in_play()]
        # v0.93: 「バトル場をはなれられない」バトル場のポケモンは、選べるが選ぶと止める（AL2）。それしか選べないなら、コインはもどす部分（起こらない）だけを決める（コインの前に AL2）
        locked = E.leave_locked_choices(run.state, run.player, options)
        if locked and len(locked) == len(options):
            raise run.res.question("leave_locked_coin", f"ポケモン {locked[0]}（ワザ {run.key} の、手札にもどす部分だけを決めるコイン）")
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        extra = _unresolved_extra(locked, E.LEAVE_LOCK_NO_EFFECT_CODE, E.LEAVE_LOCK_NO_EFFECT_REASON)
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=options, min_choices=0, max_choices=len(options), extra=extra)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        if not choices:
            raise UnsupportedError(
                "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO",
                "「好きなだけ選び」で 0 匹を選べるかは決められないので扱わない（v0.31 の HC5 と同じ問い。1 匹以上を選ぶ）",
            )
        own = [p for p in state.players[run.player].in_play() if p.pokemon_id in choices]
        if len(own) != len(choices):
            raise RuntimeError(f"ようせいのきせきで選んだポケモン {choices} が、自分の場にいない（エンジンの不具合）")
        for pokemon in own:
            if not reaches(run.res, run.fs, run.player, pokemon, E.RETURN_IN_PLAY_TO_HAND_ELEMENT):
                continue
            ninja_trick_leave_question(run, pokemon)  # v0.65（NT2）
            return_in_play_to_hand(state, run.player, pokemon, effect=str(run.key))
            remove_persistent_effects(state, run.player, pokemon, RETURN_IN_PLAY_TO_HAND)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ()))  # v0.93: AL2 の選択を含む答えは試さない（答えのときに止める）
        # 0 匹は答えのときに止める（HC5）。もどす順は場の順
        return [answer for answer in combinations_answers(decision, range(1, decision.max_choices + 1)) if not blocked & set(answer)]


# ---------------------------------------------------------------- v0.44（docs/search-evolution-once-attacks-v0.44.md）。山札をさがす・自分を手札にもどす・
# 山札から自分を進化させる・手札と山札とトラッシュのカードを動かす要素


def card_id_answers(state: GameState, decision: PendingDecision, sizes) -> list[tuple[int, ...]]:
    """先読みで試す答え（v0.44）: 決定の選べるもののうち、``sizes`` の枚数の組み合わせを、同じカード（カード id が同じ）の別の写しを区別せずに作る（それぞれの
    カード id から、選べるものの並びの前から順に取る）。

    手札・山札・トラッシュのカードは、カード id が同じなら内容（カードの定義）が同じで、カードごとの状態（ダメージ・ついているカードなど）を持たない。選んだカードの
    uid が違うだけの答えは、uid を入れかえた同じ形の状態になる（このあとの要素は山札の並びを使わない。``shuffle_in_attack`` が確かめる）。v0.35 のコインの「おもて」の
    数でまとめる先読み（``Oracle.coin_group``）と同じく、結果が同じになる答えだけをまとめる（代表で別の結果の答えを置きかえない。v0.15c）。この関数を使うのは、選んだ
    カードがどの場のポケモンにもならない（手札・山札・トラッシュのあいだを動くだけの）要素だけ。"""
    groups: dict[str, list[int]] = {}
    for uid in decision.options:
        groups.setdefault(state.cards[uid].card_id, []).append(uid)
    ids = list(groups)
    answers: list[tuple[int, ...]] = []
    for size in sizes:
        for combo in itertools.combinations_with_replacement(ids, size):
            counts = {card_id: combo.count(card_id) for card_id in set(combo)}
            if any(count > len(groups[card_id]) for card_id, count in counts.items()):
                continue
            answers.append(tuple(uid for card_id in ids for uid in groups[card_id][:counts.get(card_id, 0)]))
    return answers


@dataclass(frozen=True)
class RevealTrainerFromDeck(Element):
    """コインを投げて ``local_coin`` なら、自分の山札から「トレーナーカード」1 枚を選び出し、相手に見せてから、手札に加えてよい。その後、その山札をよく切る（v0.44。
    エリカのフシギダネの「おつかい」）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SEARCH_DECK``。選べるものは山札のトレーナーカード（``effects.deck_trainer_cards``。uid の小さい順）。0〜1 枚（「加えて
      よい」））。見せて手札に加えるのは v0.24 の ``zones.reveal_deck_to_hand``（ログ ``reveal_from_deck`` にワザの ``effect``）。0 枚ならログ ``reveal_from_deck_declined``
    - 山札にトレーナーカードがなければ、処理の対象がないので加えない（ログ ``reveal_from_deck_none`` の ``category`` は ``"trainer"``。p.309）
    - コインが ``local_coin`` なら、どの場合も、そのあと山札を切る（1 回。``shuffle_in_attack``）。自分の山札への効果なので、相手の状態によらずコインを投げる
    """

    local_coin: CoinSide | None = HEADS
    # v0.72: 選べるカードの種類。"trainer"（トレーナーカード。おつかい）か "basic_energy"（基本エネルギーカード。どのタイプでも。エリカのピッピ（GD4-012）の「おつきみ」。
    # コインなし）。ログの ``category`` もこの値
    category: str = "trainer"
    # v0.79: 「手札に加える」（「てよい」がない。ヤドキング（SI-014）の「ひらめく」）。選べるカードがあれば、ちょうど 1 枚（0 枚の答えはない）。選べるカードがない（山札に
    # トレーナーカードがない・山札が 0 枚）なら、処理の対象がないので加えずに山札を切る（p.309。v0.75 の「もえあがる」（``AttachFromDeck`` の ``ZERO_REQUIRED``）と同じ読み方）
    required: bool = False
    # v0.113: 選ぶ枚数はワザ全体のコイン ``heads_of`` の「おもて」の数 H 以下（ピッピの「みんなでおどる」の「「おもて」の数以下の枚数の「基本エネルギーカード」を自分の山札から選び出し、
    # 相手プレイヤーに見せてから、手札に加える。その後、その山札をよく切る。」）。0〜H 枚（「以下」なので 0 枚も。v0.85 のせいでんきと同じ読み方）。H = 0 なら選ぶカードがないので決定を
    # 出さず、山札を 1 回切る（説明の最後の「その後、その山札をよく切る」。せいでんきの数 0 と同じ）。H が正なら、選べるカードがなくても決定を出して答えを待つ（最大の枚数は H のまま。
    # 選べるカードの数で小さくしない。山札の中身で進み方を変えない。v0.84 の A3）。``local_coin``・``required`` とはいっしょに使わない
    heads_of: str | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SEARCH_DECK

    def __post_init__(self) -> None:
        if self.heads_of is not None and (self.local_coin is not None or self.required):
            raise ValueError("「おもて」の数以下を選ぶ（heads_of）ときは、この要素のコイン（local_coin）・ちょうど 1 枚（required）を使わない")

    def candidates(self, run: AttackRun) -> list[int]:
        if self.category == "trainer":
            return E.deck_trainer_cards(run.state, run.player)
        if self.category == "basic_energy":
            return E.deck_basic_energy_cards(run.state, run.player)
        raise RuntimeError(f"山札から選ぶカードの種類 {self.category!r} が正しくない（エンジンの不具合）")

    def run(self, run: AttackRun) -> bool:
        if self.heads_of is not None:
            heads = run.heads(self.heads_of)
            if not heads:
                shuffle_in_attack(run, self, run.player)  # v0.113: 「おもて」が 0（コインを投げなかったときを含む）。選ぶカードはなく、山札は切る
                return False
            run.suspend(kind=SEARCH_DECK, player=run.player, options=self.candidates(run), min_choices=0, max_choices=heads)
            return True
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        candidates = self.candidates(run)
        if not candidates:
            run.state.add_event("reveal_from_deck_none", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key), category=self.category)
            shuffle_in_attack(run, self, run.player)
            return False
        run.suspend(kind=SEARCH_DECK, player=run.player, options=candidates, min_choices=1 if self.required else 0, max_choices=1)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if self.required and not choices:
            raise RuntimeError("「手札に加える」（ちょうど 1 枚）の決定に、0 枚の答えが来た（決定の確認の漏れ。エンジンの不具合）")
        if self.heads_of is not None:
            candidates = self.candidates(run)
            if len(set(choices)) != len(choices) or len(choices) > run.heads(self.heads_of) or any(card not in candidates for card in choices):
                raise RuntimeError(f"選んだカード {choices} が、山札の選べるカード（{self.category}）の「おもて」の数以下ではない（エンジンの不具合）")
            for card in sorted(choices):  # v0.113: 選んだカードだけを見せて手札に加える（山札の uid の小さい順。選んだ順によらない）
                reveal_deck_to_hand(run.state, run.player, card, effect=str(run.key))
            if not choices:
                run.state.add_event("reveal_from_deck_declined", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key), category=self.category)
            shuffle_in_attack(run, self, run.player)
            return
        if choices:
            if choices[0] not in self.candidates(run):
                raise RuntimeError(f"選んだカード {choices} が、山札の選べるカード（{self.category}）ではない（エンジンの不具合）")
            reveal_deck_to_hand(run.state, run.player, choices[0], effect=str(run.key))
        else:
            run.state.add_event("reveal_from_deck_declined", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key), category=self.category)
        shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        if self.heads_of is not None:
            # v0.113: 0〜min(H, 選べるものの数) 枚のすべての枚数を、同じカード id の写しを区別せずに試す（せいでんきと同じまとめ方。意味の違う枚数・カード id の組は省かない）
            return card_id_answers(run.state, decision, range(min(decision.max_choices, len(decision.options)) + 1))
        return card_id_answers(run.state, decision, (1,) if self.required else (0, 1))


@dataclass(frozen=True)
class ReturnAttackerToHand(Element):
    """コインを投げて ``local_coin`` なら、ワザを使ったポケモンと、ついているすべてのカードを手札にもどす（v0.44。カスミのヒトデマンの「スターブーメラン」。処理に
    使う文面は kyuura の最新の説明（カスミのヒトデマンの LD-）「…自分と自分についているすべてのカードを手札にもどす。」）。

    - ワザを使ったポケモンがこのワザの中で HP 以上なら、もどさない（「こうらがえし」などで返されたダメージ。kyuura の CR-SHELL-ATTACK-STAR-BOOMERANG。返すダメージは
      ダメージの要素のあと・この要素の前に処理する（p.89。既存の窓））。処理の対象がないのでコインも投げない（p.309）
    - 自分への効果も「とうめい」を評価する（v0.17b の ``Status`` の ``SELF``・v0.36 の ``ReturnSelfToDeck`` と同じ）
    - 同じワザで HP 以上になったポケモン（相手の対戦ポケモン）がいれば、バトル場に出す時点ときぜつの処理の順番が決まらない（v0.36 の RD9 と同じ問い
      ``return_in_play_to_deck_with_knockout``。行き先が手札でも、空いたバトル場ときぜつの処理の順番の問いは同じ）。もどす前
    - もどす（v0.42 の ``zones.return_in_play_to_hand``。重なったカード・エネルギー・トレーナーをすべて。ログ ``return_in_play_to_hand`` にワザの ``effect``）→ 持続する
      効果を消す（理由 ``return_in_play_to_hand``）。山札にもどす ``ReturnSelfToDeck`` と行き先が違い、山札を切らない。きぜつではない（サイドは取られない）。空いた
      バトル場は、ワザのあとの勝ち負けの判定とバトル場に出す決定でうめる（v0.36 のくもがくれガスと同じ）
    """

    local_coin: CoinSide | None = HEADS
    # v0.117: 「自分と、自分についているすべてのエネルギーカードを、持ち主の手札にもどす」（ナツメのゴースの「ぱっときえる」）。もどすのは重なったポケモンのカードとエネルギーカード。
    # エネルギーカードでないついているカード（トレーナーカード・エネルギーとしてついているポケモンのカード）があれば、その行き先が決まらないので止める（VH1。もどす前）
    energy_only: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT

    def has_target(self, run: AttackRun) -> bool:
        return not run.knocked_out(run.attacker())

    def run(self, run: AttackRun) -> bool:
        state = run.state
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.ko_prevention_conflict(attacker, run.player)
            return False
        if self.energy_only:
            others = tuple(t.card for t in attacker.trainers) + tuple(uid for uid in attacker.energy if state.card_def(uid).category != "energy")
            if others:
                raise UnsupportedError(E.VANISH_OTHER_ATTACHED_CODE, f"ポケモン {attacker.pokemon_id}・カード {list(others)}: {E.VANISH_OTHER_ATTACHED_REASON}")
        if _leave_prevented(run, run.player, attacker, E.LEAVE_TO_HAND, self.local_coin):
            return False  # v0.93
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        if not reaches(run.res, run.fs, run.player, attacker, E.RETURN_IN_PLAY_TO_HAND_ELEMENT):
            return False
        from .kernel import knocked

        gone = knocked(run.res)
        if gone:
            raise run.res.question("return_in_play_to_deck_with_knockout", f"手札にもどす。ポケモン {[p.pokemon_id for _, p in gone]}")
        ninja_trick_leave_question(run, attacker)  # v0.65（NT2）
        return_in_play_to_hand(state, run.player, attacker, effect=str(run.key))
        remove_persistent_effects(state, run.player, attacker, RETURN_IN_PLAY_TO_HAND)
        return False


@dataclass(frozen=True)
class EvolveAttackerFromDeck(Element):
    """「(``evolves_from``)」から進化するカードを自分の山札から 1 枚選び出し、このカード（ワザを使ったポケモン）につけてよい。その後、その山札をよく切る（v0.44。
    ロケット団のコイキングの「たきのぼりしんか」）。コインはない。v0.42 の ``EvolveFromDeck``（つきのちから。自分の場のどのポケモンにも重ねる）と、重ねる先が
    このカードだけで、選ばないこともできる点が違う。

    - 選べるのは山札の進化カードで、「○○○○から進化」の名前が ``evolves_from`` のもののうち、このカードに今重ねられるもの（``effects.self_deck_evolution_cards``。
      通常の進化と同じ制限。効果による進化だからという理由で免除しない）。決定 ``SEARCH_DECK``（0〜1 枚）。0 枚ならログ ``evolve_from_deck_declined``
    - 進化したあとの HP がダメージ以下になるカードは選べるが選ぶと止める（v0.4a の H1）。場に出たときに使える特殊能力を持つカード（「場に出た時」）は PW4（v0.43）
    - トレーナー「サカキ」の許可だけで重ねられるカードがあれば GV1（決定の前に止める）
    - 重ねる前に「とうめい」を評価する（自分への効果。``reaches`` の ``evolve``）。進化は通常の進化と同じ手順（``evolution.place_evolution_card``。山札から。ログ
      ``evolve`` の ``effect``・``source_zone``）。選べるものがない（ログ ``evolve_from_deck_none``）・選ばないときも、そのあと山札を切る（1 回）

    v0.105（docs/recovery-evolution-coin-branches-v0.105.md 4 章。トランセル（neo2-006）の「からやぶりしんか」・ヒマナッツ（neo4-003）の「ひざしをあびる」の「その後、自分の山札から…
    「進化カード」を1枚選び出し、この…の上にのせ、進化させる。山札を見た場合は、その山札をよく切る。」）。どれも既定ではたきのぼりしんか（v0.44）と同じ:

    - ``gate``: ワザ全体のコインの面（前の回復と同じコイン）。満たさなければ、山札を見ず、切らない（ログもない）
    - ``required``: 選べるものがあれば 1 枚を選ぶ（決定 ``SEARCH_DECK`` の 1〜1 枚。「てよい」がない）。山札にカードがあって選べるものがなくても、選べるもののない決定（0〜0 枚）を
      出して答えを待つ（v0.84 の A3。山札の中身で決定の有無を変えない。答えのあとログ ``evolve_from_deck_none``）。山札を見る前に、公開の情報だけで決まる問い（DV2・GV1・
      ［れんさしんか］の PW4）を、山札の中身によらず確かめる（``effects.self_deck_evolution_open_question``。宣言を受け付けるかから山札の中身がわからないように）。選べるカードが
      どれも選ぶと止めるもの（H1・場に出たときの特殊能力の PW4）なら、決定を出す前に止める（選べる答えのない決定にしない）。ワザを使ったポケモンがこのワザの中で HP 以上なら、
      処理の対象がない（ログ ``effect_skipped``）
    - ``shuffle_if_looked``: 山札を見た（さがすときに山札にカードがあった）ときだけ 1 回切る。山札が 0 枚なら見ないので切らない（v0.82 のあたためると同じ読み方）。選べるカードが
      なくても、山札にカードがあれば見たので切る
    """

    evolves_from: str
    gate: tuple | None = None  # v0.105
    required: bool = False  # v0.105
    shuffle_if_looked: bool = False  # v0.105
    # v0.115: 選べるのはカードの名前がこれと同じ進化カードだけ（わるいサナギラスの「ばくれつしんか」の「自分の山札から「わるいバンギラス」を1枚選び出し、このわるいサナギラスの上にのせ、
    # 進化させる」。名前の完全一致。重ねられるかは通常の進化と同じ（``effects.self_deck_evolution_cards`` の ``name``）。説明が「進化カード」と書かないので NB2 の範囲ではない）
    card_name: str | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SEARCH_DECK

    def candidates(self, run: AttackRun) -> list[int]:
        return E.self_deck_evolution_cards(run.state, run.player, run.attacker(), evolves_from=self.evolves_from, name=self.card_name)

    def _none(self, run: AttackRun, attacker: PokemonInPlay) -> None:
        run.state.add_event("evolve_from_deck_none", player=run.player, pokemon_id=attacker.pokemon_id, effect=str(run.key))
        if not self.shuffle_if_looked or run.state.players[run.player].deck:
            shuffle_in_attack(run, self, run.player)

    def _required_run(self, run: AttackRun) -> bool:
        state = run.state
        attacker = run.attacker()
        if run.knocked_out(attacker):
            state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            element="evolve", reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        if not state.players[run.player].deck:
            self._none(run, attacker)  # 山札にカードがない: さがすカードがない（見ない）
            return False
        question = E.self_deck_evolution_open_question(state, run.player, attacker, self.evolves_from)
        if question is not None:
            raise run.res.question(*question)
        candidates = self.candidates(run)
        if not candidates:
            # 山札を見たが、選べるカードがない。選べるもののない決定を出して答えを待つ（v0.84 の A3）。答えのあとに切る
            run.suspend(kind=SEARCH_DECK, player=run.player, options=(), min_choices=0, max_choices=0)
            return True
        blocked = tuple(uid for uid in candidates if attacker.damage >= E.evolution_hp(state, attacker, uid))
        entry = tuple(uid for uid in candidates if uid not in blocked and E.applicable_entry_power(state, uid, from_hand=False) is not None)
        if len(blocked) + len(entry) == len(candidates):
            if entry:
                raise run.res.question("entry_power_during_attack", f"山札の進化カード {list(entry)}")
            raise run.res.question("evolution_hp_every_card", f"山札の進化カード {list(blocked)}")
        extra: tuple = ()
        if blocked:
            extra = (("unresolved_choices", blocked), ("unresolved_code", "UNRESOLVED_EVOLUTION_HP"), ("unresolved_reason", E.EVOLUTION_HP_REASON))
        if entry:
            extra += (("entry_power_choices", entry),)
        run.suspend(kind=SEARCH_DECK, player=run.player, options=candidates, min_choices=1, max_choices=1, extra=extra)
        return True

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        if self.required:
            return self._required_run(run)
        state = run.state
        attacker = run.attacker()
        cards = [uid for uid in state.players[run.player].deck if state.card_def(uid).evolves_from == self.evolves_from
                 and (self.card_name is None or state.card_def(uid).name_ja == self.card_name)]
        permitted = E.deck_evolution_permission_pairs(state, run.player, (attacker.pokemon_id,), cards)
        if permitted:
            raise run.res.question("evolution_permission_from_deck", f"山札の進化カードと場のポケモン {list(permitted)}")
        devolved = E.deck_evolution_devolved_pairs(state, run.player, (attacker.pokemon_id,), cards)
        if devolved:
            raise run.res.question("evolve_after_devolution", f"山札の進化カードと場のポケモン {list(devolved)}")  # v0.50: DV2
        candidates = self.candidates(run)
        if not candidates:
            self._none(run, attacker)
            return False
        blocked = tuple(uid for uid in candidates if attacker.damage >= E.evolution_hp(state, attacker, uid))  # v0.48
        chain = bool(E.chain_evolution_targets(state, run.player, (attacker.pokemon_id,)))  # v0.86: ほかのポケモンの［れんさしんか］の機会が来る（PW4）
        entry = tuple(uid for uid in candidates if uid not in blocked and (chain or E.applicable_entry_power(state, uid, from_hand=False) is not None))
        extra: tuple = ()
        if blocked:
            extra = (("unresolved_choices", blocked), ("unresolved_code", "UNRESOLVED_EVOLUTION_HP"), ("unresolved_reason", E.EVOLUTION_HP_REASON))
        if entry:
            extra += (("entry_power_choices", entry),)
        run.suspend(kind=SEARCH_DECK, player=run.player, options=candidates, min_choices=0, max_choices=1, extra=extra)
        return True

    def decides(self, kind: str) -> bool:
        return kind in (SEARCH_DECK, EVOLUTION_HEAL)  # v0.57: トキワシティジム

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if decision.kind == EVOLUTION_HEAL:
            resume_evolution_heal(run, self, decision, choices)
            return
        state = run.state
        attacker = run.attacker()
        if not choices:
            if self.required:
                if self.candidates(run):
                    raise RuntimeError(f"必ず選ぶ山札の進化カードの決定に、0 枚の答え（{run.key}。決定の形の誤り。エンジンの不具合）")
                self._none(run, attacker)  # 選べるもののない決定の答え（山札は見たので切る）
                return
            state.add_event("evolve_from_deck_declined", player=run.player, pokemon_id=attacker.pokemon_id, effect=str(run.key))
            shuffle_in_attack(run, self, run.player)
            return
        card = choices[0]
        if card not in self.candidates(run):
            raise RuntimeError(f"たきのぼりしんかで選んだカード {choices} が、このカードに重ねられる山札の進化カードではない（エンジンの不具合）")
        if card in decision.context_value("entry_power_choices", ()):
            question = QUESTIONS["entry_power_during_attack"]
            raise UnsupportedError(question.code, f"{question.message}（PW4。山札の進化カード {card}）")
        if attacker.damage >= E.evolution_hp(state, attacker, card):  # v0.48: 重ねたあとの最大HP
            raise RuntimeError(f"進化すると HP がダメージ以下になるカード {card} を選んだ（選ぶと止める選択の漏れ。エンジンの不具合）")
        if reaches(run.res, run.fs, run.player, attacker, E.EVOLVE_ELEMENT):
            before_name = E.form_def(state, attacker).name_ja
            place_evolution_card(state, run.player, attacker, card, effect=str(run.key))
            if suspend_evolution_heal(run, run.player, attacker, before_name):  # v0.57: トキワシティジム（答えたあとに山札を切る）
                return
        shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ())) | set(decision.context_value("entry_power_choices", ()))
        if self.required and decision.kind == SEARCH_DECK:
            # v0.105: 同じカード id の進化カードは、どれを重ねても同じ形の状態（v0.84 のしんかのうたと同じ）
            return [answer for answer in card_id_answers(run.state, decision, (decision.max_choices,)) if not blocked & set(answer)]
        return [answer for answer in all_answers(decision) if not blocked & set(answer)]


@dataclass(frozen=True)
class OpponentDiscardToDeckTop(Element):
    """コインを投げて ``local_coin`` なら、相手のトラッシュからカードを 1 枚選び出し、相手の山札の上にのせる（v0.44。カツラのマンキーの「わるいいたずら」）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``DISCARD_TO_DECK_TOP``。選べるものは相手のトラッシュのカード（どの種類でも。トラッシュの並び）。1 枚）。のせるのは
      ``zones.put_discard_on_deck_top``（相手の山札の一番上。持ち主は相手のまま。ログ ``put_discard_on_deck_top``）。山札は切らない（説明にない）
    - 相手のトラッシュにカードがなければ、処理の対象がないのでコインを投げない（``has_target``。p.309）
    - 相手のポケモンへの効果ではないので、「ワザをうけない」状態・「とうめい」は関係しない（``coin_receiver`` は None）
    """

    local_coin: CoinSide | None = HEADS
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = DISCARD_TO_DECK_TOP

    discard_protected = _discard_protected

    def has_target(self, run: AttackRun) -> bool:
        return bool(run.state.players[1 - run.player].discard)

    def run(self, run: AttackRun) -> bool:
        if not self.has_target(run):
            return False
        if self.local_coin is not None and self.discard_protected(run):
            # v0.119（AP1）: このコインが決めるのは、効果を受けない相手のトラッシュのカードを動かすことだけ（処理の対象がないと読めば投げない）
            raise run.res.question("discard_protected_coin", f"ワザ {run.key} の相手のトラッシュのカードを山札の上にのせる要素・［アレルギーほうし］ "
                                                             f"{list(E.discard_protection(run.state))}")
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        if protected_discard(run, "discard_to_deck_top"):
            return False
        run.suspend(kind=DISCARD_TO_DECK_TOP, player=run.player, options=list(run.state.players[1 - run.player].discard))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if choices[0] not in run.state.players[1 - run.player].discard:
            raise RuntimeError(f"わるいいたずらで選んだカード {choices} が、相手のトラッシュにない（エンジンの不具合）")
        put_discard_on_deck_top(run.state, 1 - run.player, choices[0], effect=str(run.key), chooser=run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, (1,))


def _hand_to_deck(run: AttackRun, choices: tuple[int, ...]) -> tuple[int, ...]:
    hand = run.state.players[run.player].hand
    if len(set(choices)) != len(choices) or any(uid not in hand for uid in choices):
        raise RuntimeError(f"山札にもどすカード {choices} が、手札のカードではない（エンジンの不具合）")
    return return_hand_cards_to_deck(run.state, run.player, choices, effect=str(run.key))


@dataclass(frozen=True)
class ReturnHandToDeck(Element):
    """``gate`` のワザ全体のコインの面なら、自分の手札からカードを ``count`` 枚選び、山札にもどして、よく切る（v0.44。_____のラッキーの「ラッキーたまご」の「うら」）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``HAND_TO_DECK``。選べるものは手札のカード（手札の並び）。ちょうど ``count`` 枚）→ もどす（相手に見せない。
      ``zones.return_hand_cards_to_deck``）→ 山札を切る（1 回。``shuffle_in_attack``）
    - 手札が ``count`` 枚より少ない（0 枚を含む）ときは決められない（FC1。``stated_cards_short``。決定の前に止める。先読みがこのコインの面で見つける）
    """

    count: int
    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = HAND_TO_DECK

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        hand = run.state.players[run.player].hand
        if len(hand) < self.count:
            raise run.res.question("stated_cards_short", f"手札 {len(hand)} 枚（説明は {self.count} 枚）")
        run.suspend(kind=HAND_TO_DECK, player=run.player, options=list(hand), min_choices=self.count, max_choices=self.count)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if len(choices) != self.count:
            raise RuntimeError(f"山札にもどすカード {choices} が {self.count} 枚ではない（エンジンの不具合）")
        _hand_to_deck(run, choices)
        shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, (self.count,))


@dataclass(frozen=True)
class ReturnHandThenRevealEnergy(Element):
    """自分の手札から最大 ``max_cards`` 枚のカードを選び、山札にもどす。もどしたのと同じ枚数の基本エネルギーカードを山札から選び出し、相手プレイヤーに見せてから、
    手札に加える。その後、その山札をよく切る（v0.44。ナツメのバリヤードの「てじな」）。

    - 段階 1（決定 ``HAND_TO_DECK``。0〜min(``max_cards``, 手札の枚数)）→ もどす（相手に見せない。``zones.return_hand_cards_to_deck``）→ 段階 2（決定 ``SEARCH_DECK``。
      選べるものは山札の基本エネルギーカード（``effects.deck_basic_energy_cards``。もどしたカードを含む。uid の小さい順）。もどした枚数ちょうど。``context`` の
      ``"count"``）→ 見せて手札に加える（``zones.reveal_deck_to_hand``。山札の uid の小さい順に 1 枚ずつ。ログ ``reveal_from_deck``）→ 山札を切る（1 回）
    - 手札がなければ決定を出さず、もどすもの・選び出すものはなく、そのあと山札を切る（p.309。説明の「その後、その山札をよく切る」は別の文）
    - 手札があるとき 0 枚を選べるかは決められない（v0.39 の GS1 と同じ問い。答えのときに止め、決定は待ったまま。先読みは 0 枚を試さない）
    - もどしたカードを含む山札の基本エネルギーカードが、もどした枚数より少ないとき: 0 枚なら選び出す内容の対象がないので、そのあと山札を切る（p.309。ログ
      ``reveal_from_deck_none`` の ``category`` は ``"basic_energy"``）。1 枚以上あるが足りなければ FC1（その答えのときに止める。決定は待ったまま。先読みは試さない）
    - 段階 2 の不正な答え（枚数・選べないカード）は決定の確かめが拒否し、段階 1 でもどしたカードは取り消さない（決定は待ったまま）
    """

    max_cards: int
    phase: ClassVar[Phase] = Phase.EFFECT

    def decides(self, kind: str) -> bool:
        return kind in (HAND_TO_DECK, SEARCH_DECK)

    def run(self, run: AttackRun) -> bool:
        hand = run.state.players[run.player].hand
        if not hand:
            shuffle_in_attack(run, self, run.player)
            return False
        run.suspend(kind=HAND_TO_DECK, player=run.player, options=list(hand), min_choices=0, max_choices=min(self.max_cards, len(hand)))
        return True

    def _available(self, run: AttackRun, choices: tuple[int, ...]) -> int:
        """段階 1 の答え ``choices`` でもどしたあとの、山札の基本エネルギーカードの枚数（もどしたカードを含む）。"""
        state = run.state
        return len(E.deck_basic_energy_cards(state, run.player)) + sum(1 for uid in choices if state.card_def(uid).is_basic_energy)

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        if decision.kind == HAND_TO_DECK:
            if not choices:
                raise UnsupportedError(
                    "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE",
                    f"手札があるときに 0 枚を選べるか（「最大{self.max_cards}枚のカードを選び」が 0 枚を含むか）は、記録から決められないので扱わない"
                    "（v0.39 の GS1 と同じ問い。ワザの説明の「最大N」が 0 を含むか）。1 枚以上を選ぶ",
                )
            count = len(choices)
            available = self._available(run, choices)
            if 0 < available < count:
                raise UnsupportedError(E.STATED_CARDS_SHORT_CODE, f"{E.STATED_CARDS_SHORT_REASON}（FC1。もどす {count} 枚、山札の基本エネルギーカード {available} 枚）")
            _hand_to_deck(run, choices)
            if available == 0:
                state.add_event("reveal_from_deck_none", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key),
                                category="basic_energy", count=count)
                shuffle_in_attack(run, self, run.player)
                return
            run.suspend(kind=SEARCH_DECK, player=run.player, options=E.deck_basic_energy_cards(state, run.player), min_choices=count, max_choices=count,
                        extra=(("count", count),))
            return
        count = decision.context_value("count")
        candidates = E.deck_basic_energy_cards(state, run.player)
        if len(choices) != count or any(uid not in candidates for uid in choices):
            raise RuntimeError(f"てじなで選んだカード {choices} が、山札の基本エネルギーカード {count} 枚ではない（エンジンの不具合）")
        for uid in (uid for uid in candidates if uid in choices):  # 山札の uid の小さい順（選んだ順によらない）
            reveal_deck_to_hand(state, run.player, uid, effect=str(run.key))
        shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        if decision.kind == HAND_TO_DECK:
            # 0 枚（GS1）と、足りない枚数（FC1）は答えのときに止めるもので、ワザの宣言を止める理由ではない（1 枚を選べば、どちらにも当たらない）
            return [answer for answer in card_id_answers(run.state, decision, range(1, decision.max_choices + 1))
                    if not 0 < self._available(run, answer) < len(answer)]
        return card_id_answers(run.state, decision, (decision.min_choices,))


# ---------------------------------------------------------------- v0.45（docs/conditional-damage-energy-v0.45.md）


def has_condition(pokemon: PokemonInPlay, condition: str) -> bool:
    """場のポケモンが特殊状態 ``condition`` か（v0.45。どくは通常のどくと特殊などくのどちらでも。p.322）。"""
    conditions = pokemon.conditions
    if condition == POISON:
        return conditions.poison is not None
    return {SLEEP: conditions.asleep, PARALYSIS: conditions.paralyzed, CONFUSION: conditions.confused}[condition]


@dataclass(frozen=True)
class FailUnlessOpponentStatus(Element):
    """相手の対戦ポケモンが ``condition`` の状態でないとき、このワザは失敗する（v0.45。第1弾のゴーストの「ゆめくい」の最新の説明。p.323「12 ワザの
    失敗」。ログ ``attack_failed`` の ``reason`` は ``condition``）。確かめるのはワザの内容を処理するとき（こんらんのコインのあと。並びの最初）。相手への効果ではないので
    「ワザをうけない」状態・「とうめい」は評価しない。"""

    condition: str
    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        if not has_condition(run.opponent_active(), self.condition):
            run.fail("condition")
        return False


@dataclass(frozen=True)
class SelfStatusCheck(Element):
    """ワザを使ったポケモンが ``condition`` の状態かを 1 回だけ確かめ、結果を ``name`` で残す（v0.45。キョウのアーボックの「ポイズンパワー」の「自分が「どく」状態なら」。
    ダメージの値 ``IfSelfStatus`` と効果の要素 ``Status.if_result`` が同じ結果を使う。並びの最初（ワザの内容を処理するとき。こんらんのコインのあと））。"""

    name: str
    condition: str
    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        run.fs.results[self.name] = has_condition(run.attacker(), self.condition)
        return False


@dataclass(frozen=True)
class PrintedTimesIfDefenderType:
    """相手の対戦ポケモン（ダメージの要素を処理する時点のいちばん上のカード）のタイプが ``pokemon_type`` なら、ダメージの目安の数字 × ``factor``（v0.45。カスミの
    ジュゴンの「こおりのつぶて」。p.321 の 1 段階）。"""

    pokemon_type: EnergyType
    factor: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        # v0.48: 今有効な色（``effects.type_readings``。［へんしょく］）。読み方（VS1）で倍数が変わるなら止める
        defender = run.opponent_active()
        try:
            return E.same_for_type_readings(run.state, (defender,),
                                            lambda views: run.attack.damage * (self.factor if views[0].pokemon_type is self.pokemon_type else 1))
        except E.TypeReadingsDiffer as differ:
            raise type_question(run.res, differ, f"ワザ {run.key} の相手のタイプで変わるダメージ") from None


@dataclass(frozen=True)
class IfSelfStatus:
    """自分の状態の確かめ ``check`` の結果が真なら ``amount``、そうでなければダメージの目安の数字（v0.45。「ポイズンパワー」の「このワザのダメージは「40」になる」。
    p.321 の 1 段階）。"""

    check: str
    amount: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return self.amount if run.fs.results[self.check] else run.attack.damage


@dataclass(frozen=True)
class PlusPerDiscarded:
    """ダメージの目安の数字 + トラッシュの要素 ``discard`` でトラッシュしたカードの枚数 × ``per``（v0.45。カツラのリザードンの「ファイヤーブレス」。p.321 の 1 段階）。"""

    discard: str
    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        result = run.fs.results.get(self.discard)
        return run.attack.damage + (0 if result is None else len(result.cards)) * self.per


@dataclass(frozen=True)
class PerAttachedEnergyCards:
    """ワザを使ったポケモンについている ``energy_type`` の基本エネルギーカードの枚数 × ``per``（v0.45。R団のサンダーの「エレクトロバーン」の自分へのダメージ。エネルギーの
    数ではなくカードの枚数。p.321 の 1 段階）。"""

    energy_type: EnergyType
    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        transform_energy_question(run, run.attacker(), self.energy_type, cards=True)  # v0.49: TE1
        return len(E.attached_basic_energy(run.state, run.attacker(), self.energy_type)) * self.per


@dataclass(frozen=True)
class HalfRemainingHp:
    """相手の対戦ポケモンの残りの HP の半分（ダメージカウンターの単位で切り上げ）（v0.45。ラッタの「いかりのまえば」。p.321 の 1 段階）。v0.78: ``round_down`` なら
    切りすて（ハッサムの「みねうち」）。"""

    round_down: bool = False
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return E.half_remaining_hp(run.state, run.opponent_active(), round_down=self.round_down)


@dataclass(frozen=True)
class MoveOpponentEnergyToBench(Element):
    """相手の対戦ポケモンの基本エネルギーカードを 1 枚選んではがし、相手の控えポケモンを 1 匹選んで、そのポケモンにつける（v0.45。わるいレアコイルの「じりょくせん」）。

    - 選ぶのはワザを使ったプレイヤー: はがすカード（決定 ``MOVE_OPPONENT_ENERGY``。``effects.opponent_active_basic_energy``。1 枚でも決定を出す）→ つける控えポケモン
      （決定 ``SELECT_POKEMON``）。2 つの決定のあいだ、はがすカードは相手の対戦ポケモンについたまま（続きの情報の ``energy``）。カードは 2 つめの答えのあとで動かす
    - 何もしない: 相手に控えがいない（説明「相手に控えがいない時、この効果はない」）・基本エネルギーカードがない・相手の対戦ポケモンがこのワザで HP 以上（p.309）
    - はがすのは相手の対戦ポケモンへの効果（要素の種類 ``ENERGY_MOVE_ELEMENT``。「ワザをうけない」状態・「とうめい」）、つけるのは選んだ控えポケモンへの効果
      （``ENERGY_ATTACH_ELEMENT``。「とうめい」）。つける控えポケモンが受けなければ、はがしたカードは持ち主のトラッシュ（CR-TRANSPARENCY-ENERGY-BOMB と同じ読み方。
      v0.31 の ``MoveOwnEnergyToBench``）。ログ ``move_opponent_energy``（``result`` は ``attached``・``evaded``）。つけたら、つけたときの特殊能力を評価する
      （``effects.after_energy_attached``）
    - v0.101: はがしてつけかえるのはトラッシュする効果ではないので、［KEEP］のはたらくアンノーンからも動かす。つける控えが受けずにトラッシュに置く場合だけ、KEEP でなくなる効果に
      当たるかが決まらない（KP3）
    - v0.116（docs/energy-movement-attachment-devolution-v0.116.md 5 章）: ``any_card`` は、はがすカードが相手の対戦ポケモンについている「エネルギーカード」（特殊エネルギーカードを
      ふくむ。ネイティオの「エナジーサイクル」。基本エネルギーカードに限らないので RB3 の問いはない）。``gate`` はワザ全体のコインの面（エナジーサイクルの「おもて」）。どちらも既定の値で
      v0.115 までと同じ（じりょくせん）
    """

    any_card: bool = False
    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.ENERGY_MOVE_ELEMENT

    def decides(self, kind: str) -> bool:
        return kind in (MOVE_OPPONENT_ENERGY, SELECT_POKEMON)

    def coin_receiver(self) -> str | None:
        return "effect"  # v0.116: ワザ全体のコインが決める相手の対戦ポケモンへの効果（``void_coin_question``。``gate`` があるときだけ聞かれる）

    def _energies(self, run: AttackRun, target: PokemonInPlay) -> list[int]:
        """はがせるカード（ついている順）。v0.116: ``any_card`` ならついているエネルギーカードすべて。"""
        return list(target.energy) if self.any_card else E.opponent_active_basic_energy(run.state, run.player)

    def has_target(self, run: AttackRun) -> bool:
        """v0.116: ワザ全体のコインが決める処理の対象があるか（相手の対戦ポケモンがこのワザで HP 以上でなく、控えがいて、はがせるカードがある。p.309）。"""
        opponent = 1 - run.player
        p = run.state.players[opponent]
        target = p.active
        if target is None or run.knocked_out(target) or not p.bench or E.energy_removal_protected(run.state, opponent, target, run.player) is not None:
            return False
        return bool(self._energies(run, target))

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        opponent = 1 - run.player
        p = run.state.players[opponent]
        target = p.active
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if not p.bench:
            return False  # 「相手に控えがいない時、この効果はない」（はがさない）
        if E.energy_removal_protected(run.state, opponent, target, run.player) is not None:
            return False  # v0.59: タケシの保護（相手の使うワザによってははがされない）。はがせるカードがない
        rainbow = () if self.any_card else E.rainbow_cards_attached(run.state, [target])
        if rainbow:
            # v0.58（RB3）: 相手の対戦ポケモンのレインボーエネルギーが、説明の「基本エネルギーカード」として選べるかが決まらない
            raise run.res.question("rainbow_basic_energy_card", f"相手の対戦ポケモン {target.pokemon_id} のレインボーエネルギー {rainbow}")
        energies = self._energies(run, target)
        if not energies:
            return False
        if not reaches(run.res, run.fs, opponent, target, E.ENERGY_MOVE_ELEMENT):
            return False
        run.suspend(kind=MOVE_OPPONENT_ENERGY, player=run.player, options=energies, extra=(("target", target.pokemon_id),), carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        opponent = 1 - run.player
        state = run.state
        p = state.players[opponent]
        target = p.active
        if target is None or target.pokemon_id != run.carried.get("target"):
            raise RuntimeError(f"はがす相手の対戦ポケモン {run.carried.get('target')} が相手のバトル場にいない（エンジンの不具合）")
        if decision.kind == MOVE_OPPONENT_ENERGY:
            if choices[0] not in self._energies(run, target):
                raise RuntimeError(f"はがすカード {choices} が、相手の対戦ポケモンのはがせるエネルギーカードではない（エンジンの不具合）")
            run.suspend(kind=SELECT_POKEMON, player=run.player, options=[pokemon.pokemon_id for pokemon in p.bench],
                        extra=(("target", target.pokemon_id), ("energy", choices[0])), carry=True)
            return
        energy = run.carried["energy"]
        destination = next((pokemon for pokemon in p.bench if pokemon.pokemon_id == choices[0]), None)
        if energy not in target.energy or destination is None:
            raise RuntimeError(f"つけかえるカード {energy}・控えポケモン {choices} が正しくない（エンジンの不具合）")
        # v0.101: ［KEEP］がはたらくアンノーンからはがすとき（はがして別のポケモンにつけるのはトラッシュする効果ではないので、そのまま動かす）、つける控えが受けずにトラッシュに
        # 置く場合だけが、なくなる効果に当たるかが決まらない（KP3。手札にもどる計画・TE2 も聞かない）
        void = E.energy_discard_void(state, target, cause=E.DISCARD_BY_ATTACK, by_player=run.player)
        returns = () if void is not None else E.energy_discard_plan(state, target, (energy,), cause=E.DISCARD_BY_ATTACK, by_player=run.player)  # v0.82: トラッシュに置くときだけ使う
        target.energy.remove(energy)
        base = {"player": opponent, "pokemon": target.card, "pokemon_id": target.pokemon_id, "energy": energy, "to_pokemon_id": destination.pokemon_id,
                "effect": str(run.key), "attacker": run.player, "attacker_pokemon_id": run.fs.frame.source_pid}
        if reaches(run.res, run.fs, opponent, destination, E.ENERGY_ATTACH_ELEMENT):
            destination.energy.append(energy)
            state.add_event("move_opponent_energy", **base, result="attached")
            attached_in_attack(run, opponent, destination, (energy,), moved=True)
        else:
            if void is not None:
                raise run.res.question("keep_detached_energy_discard", f"ポケモン {target.pokemon_id} からはがしたエネルギーカード {energy}（つける控え {destination.pokemon_id} が受けない）")
            p.discard.append(energy)  # 「とうめい」の「おもて」: はがしたカードは持ち主のトラッシュ（CR-TRANSPARENCY-ENERGY-BOMB と同じ読み方）
            state.add_event("move_opponent_energy", **base, result="evaded")
            E.return_discarded_energy(state, returns)  # v0.82: 相手のワザで場からトラッシュに置かれた（エコロジム）

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        if decision.kind == MOVE_OPPONENT_ENERGY:
            return card_id_answers(run.state, decision, (1,))  # 同じカード id（同じタイプの基本エネルギー）の答えは 1 つにまとめる（v0.44）
        return all_answers(decision)


@dataclass(frozen=True)
class OpponentDeckTopDiscardTrainerElseHand(Element):
    """コインを投げて ``local_coin`` なら、相手の山札の一番上のカードを見て、トレーナーカードなら相手のトラッシュ、それ以外なら相手の手札に動かす（v0.45。サカキの
    ニャースの「てつだうふり」。``zones.take_deck_top``。山札を切らない）。相手の山札が 0 枚なら、処理の対象がないのでコインを投げない（p.309）。相手のポケモンへの
    効果ではない（「ワザをうけない」状態・「とうめい」は関係しない）。"""

    local_coin: CoinSide | None = HEADS
    phase: ClassVar[Phase] = Phase.EFFECT
    reads_deck_order: ClassVar[bool] = True

    def has_target(self, run: AttackRun) -> bool:
        return bool(run.state.players[1 - run.player].deck)

    def run(self, run: AttackRun) -> bool:
        if not self.has_target(run):
            return False
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        take_deck_top(run.state, 1 - run.player, effect=str(run.key), looker=run.player)
        return False


# ---------------------------------------------------------------- v0.46（docs/continuous-powers-v0.46.md）。手札のエネルギーカードを自分につける・手札を山札にもどして
# 引く


@dataclass(frozen=True)
class AttachFromHand(Element):
    """``gate`` のワザ全体のコインの面なら、自分の手札にある ``energy_type`` の基本エネルギーカードを最大 ``max_cards`` 枚、ワザを使ったポケモン（このカード）につける
    （v0.46。エリカのフシギバナの「せいちょう」）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``ATTACH_FROM_HAND``。選べるものは手札の ``energy_type`` の基本エネルギーカード（手札の並び）。0〜min(``max_cards``, 枚数)）→
      つける（``zones.attach_energy_from_hand``。手札からつける通常の操作・あまごいと同じカードの動かし方。手札の並びの順）→ つけたカードごとに ``after_energy_attached``。
      ログ ``attach_energy_from_hand``（``effect`` はワザ、``cards`` はつけたカード。場に出るので公開）
    - 手札からつける通常の操作（p.310。1 番に 1 枚）の回数・特殊能力でつけた枚数には数えない（ワザの効果。別の処理）
    - 手札にそのエネルギーカードがない・ワザを使ったポケモンがこのワザの中で HP 以上なら、処理の対象がない（``has_target``。コインも投げない。v0.38）
    - あるときに 0 枚を選べるかは決まらない（「最大2枚」。v0.31 の HC7 と同じ問いで、答えのときに止め、決定は待ったまま。先読みは 0 枚を試さない）
    """

    energy_type: EnergyType
    max_cards: int
    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = ATTACH_FROM_HAND

    def _candidates(self, run: AttackRun) -> list[int]:
        rainbow_attach_question(run, run.state.players[run.player].hand, self.energy_type)  # v0.58: RB2
        return E.hand_basic_energy(run.state, run.player, self.energy_type)

    def has_target(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        return bool(self._candidates(run)) and not run.knocked_out(attacker) and E.energy_attach_block(run.state, attacker) is None

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                element="attach_from_hand", reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        if attach_prevented(run, attacker, "attach_from_hand"):
            return False
        candidates = self._candidates(run)
        if not candidates:
            return False
        run.suspend(kind=ATTACH_FROM_HAND, player=run.player, options=candidates, min_choices=0, max_choices=min(self.max_cards, len(candidates)))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if not choices:
            raise UnsupportedError(
                "UNRESOLVED_ATTACH_FROM_DISCARD_ZERO",
                f"手札に「{self.energy_type.ja}」エネルギーカードがあるときに 0 枚を選べるか（「最大{self.max_cards}枚、このカードにつける」が 0 枚を含むか）は決められないので"
                "扱わない（v0.31 の HC7 と同じ問い）。1 枚以上を選ぶ",
            )
        candidates = self._candidates(run)
        if len(set(choices)) != len(choices) or any(uid not in candidates for uid in choices):
            raise RuntimeError(f"つけるカード {choices} が、手札の「{self.energy_type.ja}」エネルギーカードではない（エンジンの不具合）")
        attacker = run.attacker()
        cards = tuple(uid for uid in run.state.players[run.player].hand if uid in choices)  # 手札の並びの順につける（選んだ順によらない）
        for uid in cards:
            question = E.attack_hand_attach_question(run.state, run.player, attacker, uid)  # v0.86: 手札からつけた事実への反応（PW4・エンジンの未対応）
            if question is not None:
                raise run.res.question(question, f"手札からつけるカード {uid}・ポケモン {attacker.pokemon_id}")
        for uid in cards:
            attach_energy_from_hand(run.state, run.player, uid, attacker)
        run.state.add_event("attach_energy_from_hand", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            cards=cards)
        for uid in cards:
            attached_in_attack(run, run.player, attacker, (uid,))

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, range(1, decision.max_choices + 1))  # 0 枚は答えのときに止める（HC7）


@dataclass(frozen=True)
class ShuffleHandThenDraw(Element):
    """自分の手札をすべて山札にもどし、山札をよく切る。その後、カードを ``count`` 枚引いて、手札にする（v0.46。エリカのナッシーの「サイコエクスチェンジ」）。

    - もどす（相手に見せない。``zones.return_hand_cards_to_deck``。手札の並びの順。ログ ``hand_to_deck``）→ 切る（1 回。``shuffle_in_attack``）→ 引く（``zones.draw_cards``。
      山札が足りなければ引けるだけ。効果で引くときの規定。p.312）。手札がなければもどさずに、切って引く
    - 先読み（``res.dry_run``）では切らない（乱数はコインだけ）。引いたカードを使う要素はあとにない（この要素はワザの最後の要素。``shuffle_in_attack`` が確かめる）
    """

    count: int
    phase: ClassVar[Phase] = Phase.EFFECT
    reads_deck_order: ClassVar[bool] = True  # 山札の上から引く

    def run(self, run: AttackRun) -> bool:
        hand = tuple(run.state.players[run.player].hand)
        if hand:
            return_hand_cards_to_deck(run.state, run.player, hand, effect=str(run.key))
        shuffle_in_attack(run, self, run.player)
        draw_cards(run.state, run.player, min(self.count, len(run.state.players[run.player].deck)))
        return False


# ---------------------------------------------------------------- v0.47（docs/fossil-hidden-info-v0.47.md）。山札の上を見て並べかえる・相手の手札を見て山札にもどさせる・
# 相手プレイヤーのトレーナーの使用を禁止する


@dataclass(frozen=True)
class ArrangeDeckTop(Element):
    """自分または相手の山札の上から ``max_cards`` 枚まで見て、好きな順番に入れ替えて、もとの山札の上にもどす（v0.47。スリーパーの「みらいよち」）。

    - 選ぶのはワザを使ったプレイヤー: 見る山札の持ち主（決定 ``SELECT_DECK_OWNER``。選べるものは自分・相手のプレイヤーの番号）→ 見る枚数（決定 ``SELECT_LOOK_COUNT``。
      0〜min(``max_cards``, その山札の枚数)。``context`` の ``"owner"``）→ 見る（ログ ``look_at_deck_top`` の ``cards`` は見たプレイヤーにだけ見える）→ 2 枚以上なら
      新しい並び（決定 ``ARRANGE_DECK_TOP``。選べるものは見たカード（上から順）。ちょうどその枚数。答えの並びが新しい上からの順）→ もどす（ログ ``arrange_deck_top``）
    - 1 枚なら並べかえる決定はない（並びは変わらない。ログ ``arrange_deck_top`` は同じ）。見た部分より下の並びは変えない。山札は切らない（説明にない）
    - 選んだ山札が 0 枚なら見るカードがない（p.309。ログ ``look_at_deck_top_none``）。山札があるとき 0 枚を選べるかは GS1（答えのときに止める。決定は待ったまま。
      先読みは 0 枚を試さない）
    - 山札は裏向きなので、見る前（持ち主と枚数を選ぶ決定）には内容を見せない。相手には見せない（「見て」で「見せる」ではない）
    """

    max_cards: int
    # v0.95（docs/private-looks-deck-movement-v0.95.md 6 章）: ちょうど ``max_cards`` 枚を見る（ネイティオの「みらいよち」の「自分または相手の山札の上から3枚のカードを見る」。
    # 見る枚数の決定はない）。山札が ``max_cards`` 枚より少ない持ち主は、v0.83 の LT1（``attack_deck_top_short``）で、選べるが選ぶと止める（もう一方の山札は止めない）。
    # どちらの山札も少なければ宣言の前に止める。偽なら v0.47 の「3枚まで」
    exact: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT

    def decides(self, kind: str) -> bool:
        return kind in (SELECT_DECK_OWNER, SELECT_LOOK_COUNT, ARRANGE_DECK_TOP)

    def run(self, run: AttackRun) -> bool:
        owners = (run.player, 1 - run.player)
        extra: tuple = ()
        if self.exact:
            short = tuple(owner for owner in owners if len(run.state.players[owner].deck) < self.max_cards)
            detail = f"ワザ {run.key}・山札が {self.max_cards} 枚より少ないプレイヤー {[(owner, len(run.state.players[owner].deck)) for owner in short]}"
            if len(short) == len(owners):
                raise run.res.question("attack_deck_top_short", detail)
            if short:
                error = to_error("attack_deck_top_short", detail)
                extra = _unresolved_extra(short, error.code, error.message)
        run.suspend(kind=SELECT_DECK_OWNER, player=run.player, options=owners, extra=extra)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        if decision.kind == SELECT_DECK_OWNER:
            owner = choices[0]
            deck = state.players[owner].deck
            if self.exact:
                if owner in decision.context_value("unresolved_choices", ()) or len(deck) < self.max_cards:
                    raise RuntimeError(f"みらいよちで山札が {len(deck)} 枚の持ち主 {owner} を選んだ（答えのときに止めるはず。エンジンの不具合）")
                self._look(run, owner, self.max_cards)
                return
            if not deck:
                state.add_event("look_at_deck_top_none", player=run.player, owner=owner, effect=str(run.key))
                return
            run.suspend(kind=SELECT_LOOK_COUNT, player=run.player, options=tuple(range(min(self.max_cards, len(deck)) + 1)), extra=(("owner", owner),))
            return
        owner = decision.context_value("owner")
        deck = state.players[owner].deck
        if decision.kind == SELECT_LOOK_COUNT:
            count = choices[0]
            if count == 0:
                raise UnsupportedError(
                    "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE",
                    f"山札があるときに 0 枚を見るのを選べるか（「上から{self.max_cards}枚まで見て」が 0 枚を含むか）は、記録から決められないので扱わない"
                    "（v0.39 の GS1 と同じ問い。ワザの説明の「最大N」が 0 を含むか）。1 枚以上を選ぶ",
                )
            self._look(run, owner, count)
            return
        count = len(decision.options)
        if tuple(deck[:count]) != tuple(decision.options) or sorted(choices) != sorted(decision.options):
            raise RuntimeError(f"みらいよちの並べかえ {choices} が、見たカード {decision.options} の並べかえではない（エンジンの不具合）")
        deck[:count] = list(choices)
        state.add_event("arrange_deck_top", player=run.player, owner=owner, count=count, cards=tuple(choices), effect=str(run.key))

    def _look(self, run: AttackRun, owner: int, count: int) -> None:
        """山札の上から ``count`` 枚を見る（ログ ``look_at_deck_top``）。2 枚以上なら並べかえる決定を出し、1 枚ならそのままもどす。"""
        state = run.state
        cards = tuple(state.players[owner].deck[:count])
        state.add_event("look_at_deck_top", player=run.player, owner=owner, count=count, cards=cards, effect=str(run.key))
        if count == 1:
            state.add_event("arrange_deck_top", player=run.player, owner=owner, count=1, cards=cards, effect=str(run.key))
            return
        run.suspend(kind=ARRANGE_DECK_TOP, player=run.player, options=cards, min_choices=count, max_choices=count, extra=(("owner", owner),))

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        if decision.kind == SELECT_LOOK_COUNT:
            return [(count,) for count in decision.options if count]  # 0 枚は答えのときに止める（GS1）
        blocked = set(decision.context_value("unresolved_choices", ()))  # v0.95: 選ぶと止める山札の持ち主（LT1）は試さない（答えのときに止める）
        return [answer for answer in all_answers(decision) if not blocked & set(answer)]


@dataclass(frozen=True)
class LookHandCardToDeck(Element):
    """相手の手札から、おもてを見ないで 1 枚選び、そのカードを見る。その後、そのカードを相手の山札にもどさせ、その山札をよく切る（v0.47。マチスのイーブイの「おどろかす」）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_HAND_CARD``。選べるものは相手の手札の位置（0 から）。カードの uid・内容を選べるものに書かない。``context`` の
      ``"owner"``）→ 見る（``zones.look_at_card``。ログ ``look_at_card``）→ 相手がそのカードを山札にもどす（``zones.return_hand_cards_to_deck``。ログ ``hand_to_deck``）→
      相手の山札を切る（1 回。``shuffle_in_attack``）。この順番を変えない
    - 相手の手札・山札への効果なので、相手の対戦ポケモンの「ワザをうけない」状態・「とうめい」は評価しない
    - 相手の手札が 0 枚なら決められない（FC1 ``stated_cards_short``。決定の前に止める。先読みが見つける）
    """

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_HAND_CARD

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        hand = run.state.players[opponent].hand
        if not hand:
            raise run.res.question("stated_cards_short", "相手の手札 0 枚（説明は 1 枚）")
        run.suspend(kind=SELECT_HAND_CARD, player=run.player, options=tuple(range(len(hand))), extra=(("owner", opponent),))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        opponent = decision.context_value("owner")
        if opponent != 1 - run.player or len(choices) != 1:
            raise RuntimeError(f"おどろかすの決定 {decision.kind}・答え {choices} が正しくない（エンジンの不具合）")
        card = look_at_card(run.state, run.player, opponent, "hand", choices[0], effect=str(run.key))
        return_hand_cards_to_deck(run.state, opponent, (card,), effect=str(run.key))
        shuffle_in_attack(run, self, opponent)


@dataclass(frozen=True)
class LockOpponentTrainers(Element):
    """コインを投げて ``local_coin`` なら（None ならコインなしで）、次の相手の番の終わりまで、相手プレイヤーはトレーナーカードを使うことができない（v0.47。コダックの
    「ずつう」・マチスのサンダースの「こうしゅうは」）。

    - 相手プレイヤーに与える期限のある禁止（``state.TrainerUseLock``。``GameState.trainer_locks``。消える番は与えた番 + 1。番の終わりに消す）。場のポケモンに与える
      効果ではないので、「ワザをうけない」状態・「とうめい」は評価せず、相手の対戦ポケモンがこのワザのダメージで HP 以上でも与える。対戦ポケモンの入れ替え・ワザを
      使ったポケモンが場をはなれることでは消えない。ログ ``trainer_lock_added``
    - 同じプレイヤー・同じ消える番のワザによる禁止が 2 つになることはない（1 番に使えるワザは 1 つ。起これば RuntimeError）。v0.56: ロケット団の実験の「うら」の
      禁止（``origin`` が ``"trainer"``。消える番は使った番 + 2）とは別の記録で、同じ消える番に重なってよい（それぞれの記録として持ち、それぞれ消える）
    """

    local_coin: CoinSide | None = None
    # v0.86: 「手札から「トレーナーカード」を出して使うことができない」（わるいモココの「こうしゅうは」）。出どころ ``ATTACK_HAND_TRAINER_LOCK``（手札から出して使うことだけを止める。
    # ``effects.trainer_use_blockers``）。消える番・与えるプレイヤーはワザの禁止と同じ
    hand_only: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        state = run.state
        opponent = 1 - run.player
        expires = state.turn_number + 1
        origin = E.ATTACK_HAND_TRAINER_LOCK if self.hand_only else "attack"
        if any(lock.player == opponent and lock.expires_turn == expires and lock.origin == origin for lock in state.trainer_locks):
            raise RuntimeError(f"プレイヤー {opponent} に、消える番 {expires} のトレーナーの使用の禁止がすでにある（エンジンの不具合）")
        lock = TrainerUseLock(player=opponent, source_player=run.player, source_card=run.attacker().card, effect=str(run.key),
                              created_turn=state.turn_number, expires_turn=expires, origin=origin)
        state.trainer_locks = state.trainer_locks + (lock,)
        extra = {} if origin == "attack" else {"origin": origin}  # ワザの禁止のログの形は v0.85 と同じ
        state.add_event("trainer_lock_added", player=opponent, source_player=run.player, source_card=lock.source_card, effect=lock.effect,
                        expires_turn=expires, **extra)
        return False


# ---------------------------------------------------------------- v0.48（docs/effective-pokemon-properties-v0.48.md）。弱点・抵抗力の色を変える・最大HPを決まった数に
# する・場の名前の合うポケモンの数のコイン・ダメージカウンターがのっている相手のポケモン全員にのせる


@dataclass(frozen=True)
class AmountIfSelfMaxHpSet:
    """ワザを使ったポケモン（「このカード」）に「きょだいか」の効果（``persistent.max_hp_set``）がはたらいていれば ``amount``、いなければダメージの目安の数字（v0.48。
    キョウのメタモンの「はたく」の「このカードに「きょだいか」の効果がはたらいているとき、このワザのダメージは「30」になる。」）。p.321 の 1 段階（ワザの説明の計算。
    v0.40 の ``AmountIfOwnBenchNamed`` と同じ）。最大HP（``effects.max_hp``）と同じ問い合わせで効果の有無を見る。"""

    amount: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return self.amount if max_hp_set(run.attacker()) is not None else run.attack.damage


@dataclass(frozen=True)
class HeadsTimesNamedPokemon:
    """自分の場にいる名前が ``names`` のどれかのポケモンの数だけコインを投げ、「おもて」の数 × ``per``（v0.48。ナツメのゴーストの「ナイトスピリッツ」）。数えるのは
    ダメージの要素を処理する時点（v0.39 の ``counted_pokemon``。``SCOPE_OWN_IN_PLAY``。進化して重なったカードは 1 匹・名前の完全一致・ワザを使ったポケモンも数える）。
    コインはダメージの要素の中（ダメージの量だけを決める）で、結果は「おもて」の数だけを使う（``by_heads``。先読みは「おもて」の数でまとめる。v0.35）。"""

    per: int
    names: tuple[str, ...]
    by_heads: ClassVar[bool] = True

    def coin_count(self, run: AttackRun) -> int:
        return len(counted_pokemon(run.state, run.player, SCOPE_OWN_IN_PLAY, self.names))

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return (0 if flips is None else flips.heads) * self.per


def _color_choice(run: AttackRun, choices: tuple[int, ...]) -> EnergyType:
    if len(choices) != 1 or choices[0] not in E.NON_COLORLESS_CHOICES:
        raise RuntimeError(f"色の決定の答え {choices!r} が、無色以外の色の位置ではない（エンジンの不具合）")
    return E.COLORS[choices[0]]


@dataclass(frozen=True)
class OpponentWeaknessColor(Element):
    """相手の対戦ポケモンの弱点を、ワザを使ったプレイヤーが選んだ無色以外の色に変える（v0.48。ポリゴンの「テクスチャー1」。持続する効果 ``WeaknessChange``）。

    - 相手に与える効果なので、選ぶ前に「ワザをうけない」状態・「とうめい」を評価する（受けないなら選ばない。v0.35 の ``OpponentAttackLock`` と同じ順番）
    - 受けるポケモンに今有効な弱点がない（``effects.weakness_of`` が None）なら決まらない（PG1）
    - 選ぶ（決定 ``SELECT_COLOR``。選べるものは ``effects.NON_COLORLESS_CHOICES``）→ 前の効果を理由 ``replaced`` で消して与える（``replace_persistent_effect``）
    """

    # v0.88: 「変えてよい」（変えないこともできる。決定の 0 個。かっこいいポリゴンの「テクスチャーマジック」）。``absent_skips`` は「相手に弱点があれば」（弱点がなければ何もしない。
    # PG1 にしない）
    optional: bool = False
    absent_skips: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_COLOR
    opponent_element: ClassVar[str] = E.WEAKNESS_CHANGE_ELEMENT

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if self.absent_skips and E.weakness_of(run.state, target) is None:
            return False  # v0.88: 「相手に弱点があれば」（弱点のないポケモンには何もしない。効果を受けるかの評価もしない）
        if not reaches(run.res, run.fs, opponent, target, E.WEAKNESS_CHANGE_ELEMENT):
            return False
        if E.weakness_of(run.state, target) is None:
            raise run.res.question("change_absent_weakness_resistance", f"相手の対戦ポケモン {target.pokemon_id} に弱点がない")
        # v0.88: 「変えてよい」ワザは、並びに色を選ぶ要素が 2 つあることがある（テクスチャーマジック）ので、決定を出した要素の位置を運ぶ（v0.35 の "element"）
        where = (("element", run.index),) if self.optional else ()
        run.suspend(kind=SELECT_COLOR, player=run.player, options=E.NON_COLORLESS_CHOICES, extra=(("target", target.pokemon_id),) + where, carry=True,
                    min_choices=0 if self.optional else 1)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        target = run.opponent_active()
        if target is None or target.pokemon_id != run.carried.get("target"):
            raise RuntimeError(f"テクスチャー1の対象 {run.carried.get('target')} が相手のバトル場にいない（エンジンの不具合）")
        if not choices and self.optional:
            run.state.add_event("color_change_declined", player=run.player, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key),
                                change="weakness")  # v0.88
            return
        color = _color_choice(run, choices)
        turn = run.state.turn_number
        effect = WeaknessChange(source_card=run.attacker().card, source_player=run.player, created_turn=turn, active_turn=turn, color=color)
        replace_persistent_effect(run.state, 1 - run.player, target, effect, attack=str(run.key), color=color.value)


@dataclass(frozen=True)
class SelfResistanceColor(Element):
    """ワザを使ったポケモン自身の抵抗力の色を、ワザを使ったプレイヤーが選んだ無色以外の色に変える（v0.48。ポリゴンの「テクスチャー2」。持続する効果
    ``ResistanceChange``。数は変えない）。自分自身への持続する効果（v0.31 の ``SelfPersistent`` と同じく、「とうめい」は評価しない。ポリゴン・まねるワザを持つポケモンは
    「とうめい」を持たない）。今有効な抵抗力がない（相手のワザとして使ったポケモン）なら決まらない（PG1）。"""

    # v0.88: 「変えてよい」（ポリゴン ES1-033 の「テクスチャー2」・かっこいいポリゴンの「テクスチャーマジック」）。変えないこともできる（決定の 0 個）。抵抗力がないなら、色を選ぶと
    # PG1（変えないことはできるので、宣言の前には止めない。``unresolved_choices``）
    optional: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_COLOR

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.ko_prevention_conflict(attacker, run.player)
            return False
        extra: tuple = (("target", attacker.pokemon_id),) + ((("element", run.index),) if self.optional else ())  # v0.88: 位置は ``OpponentWeaknessColor`` と同じ
        if E.resistance_of(run.state, attacker)[0] is None:
            if not self.optional:
                raise run.res.question("change_absent_weakness_resistance", f"ワザを使ったポケモン {attacker.pokemon_id} に抵抗力がない")
            extra += (("unresolved_choices", E.NON_COLORLESS_CHOICES), ("unresolved_code", E.ABSENT_WEAKNESS_RESISTANCE_CODE),
                      ("unresolved_reason", f"ワザを使ったポケモン {attacker.pokemon_id} に抵抗力がない: {E.ABSENT_WEAKNESS_RESISTANCE_REASON}"))
        run.suspend(kind=SELECT_COLOR, player=run.player, options=E.NON_COLORLESS_CHOICES, extra=extra, carry=True, min_choices=0 if self.optional else 1)
        return True

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ()))
        return [answer for answer in all_answers(decision) if not blocked & set(answer)]

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        attacker = run.attacker()
        if attacker.pokemon_id != run.carried.get("target"):
            raise RuntimeError("テクスチャー2の対象がワザを使ったポケモンではない（エンジンの不具合）")
        if not choices and self.optional:
            run.state.add_event("color_change_declined", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                change="resistance")  # v0.88
            return
        color = _color_choice(run, choices)
        turn = run.state.turn_number
        effect = ResistanceChange(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn, color=color)
        replace_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key), color=color.value)


@dataclass(frozen=True)
class SelfMaxHp(Element):
    """コインを投げて ``local_coin`` なら、ワザを使ったポケモン自身の最大HPを ``amount`` にする（v0.48。キョウのメタモンの「きょだいか」。持続する効果 ``MaxHpSet``）。
    「うら」なら何もしない（前の効果はそのまま）。自分自身への持続する効果（``SelfPersistent`` と同じく「とうめい」は評価しない）。前の効果は理由 ``replaced`` で消す。"""

    amount: int
    local_coin: CoinSide | None = HEADS
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("persistent_effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                persistent_effect=MaxHpSet.kind, effect=str(run.key), reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        if E.max_hp_bonus(run.state, attacker):
            # v0.81a（MH2）: 最大HPを大きくする効果がはたらいているポケモンに決まった数にする効果を与えると、最大HPが決まらない。コインの結果で受け付けるかが変わらないよう、
            # コインの前に止める（今の写しのワザの組み合わせでは、「きょだいか」を使うポケモンに大きくする効果ははたらかない）
            fixed = MaxHpSet(source_card=attacker.card, source_player=run.player, created_turn=0, active_turn=0, amount=self.amount)
            raise E.MaxHpOrderUndetermined(attacker, fixed.amount, E.max_hp_bonus(run.state, attacker))
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        turn = run.state.turn_number
        effect = MaxHpSet(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn, amount=self.amount)
        replace_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key), amount=self.amount)
        return False


@dataclass(frozen=True)
class PlaceCountersOnDamagedOpponents(Element):
    """相手の場の、ダメージカウンターがのっているポケモン全員に、ダメージカウンターを ``counters`` 個ずつのせる（v0.48。ナツメのゲンガーの「ダメージぞうふく」）。

    - 対象はこの要素を処理する時点で相手の場（バトル場 → ベンチの順）にいて、ダメージカウンターがのっているポケモン（のせても対象は変わらない）。いなければ何もしない
    - ダメージカウンターをのせることはワザによるダメージではない（v0.41 の ``ShiftCountersToOpponent``・``CountersToRemainingHp`` と同じ。GR-2000-P320-COUNTER-MOVE）。
      ダメージの計算をせず、「ダメージを受けない」状態でものせ、「ダメージを受けたとき」の効果ははたらかない
    - ポケモンごとに、のせる前に「ワザをうけない」状態・「とうめい」を評価する（``reaches`` の ``damage_counters``。2 匹以上が「とうめい」なら T27）
    - ログはポケモンごとに v0.41 の ``place_damage_counters``。HP 以上になったら、ワザのあとのきぜつの判定でまとめてきぜつする（``_counters_changed``）
    """

    counters: int = 1
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.COUNTERS_ELEMENT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        opponent = 1 - run.player
        per = state.rules.damage_per_counter
        targets = [pokemon for pokemon in state.players[opponent].in_play() if pokemon.damage > 0]
        for target in targets:
            if not reaches(run.res, run.fs, opponent, target, E.COUNTERS_ELEMENT):
                continue
            before = target.damage
            target.damage = before + self.counters * per
            state.add_event("place_damage_counters", player=opponent, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key),
                            counters=self.counters, amount=self.counters * per, damage_before=before, total_damage=target.damage, attacker=run.player,
                            attacker_pokemon_id=run.fs.frame.source_pid)
            _counters_changed(run, target, before)
        return False


# ---------------------------------------------------------------- v0.50（docs/mew-devolution-spray-v0.50.md）。進化カードをはがす（退化させる）要素


def _hp_dropped_in_attack(run: AttackRun) -> None:
    """ワザの効果で最大HPが下がり、のっているダメージ以下になったポケモン（v0.50。退化。退化したポケモンと、［へんしん］で同じカードとしてあつかう相手のメタモンなど）の、
    きぜつの原因の枠を記録する（同時のきぜつの判定。``kernel.check_simultaneous``）。きぜつの処理はワザのあとの判定（v0.48 のワザの効果で最大HPが下がったときと同じ）。
    ダメージを受けたのではないので、「こんじょう」は使えない（``ko_prevention_able`` を偽。v0.41 のカウンターの移動と同じ）。"""
    res = run.res
    for player in (run.player, 1 - run.player):
        for pokemon in run.state.players[player].in_play():
            if E.knocked_by_hp(run.state, pokemon) and pokemon.pokemon_id not in res.knocked_by:
                res.knocked_by[pokemon.pokemon_id] = run.fs.frame.id
                res.trace.record(KnockedOutRecorded(pokemon.pokemon_id, run.fs.frame.id))
                res.ko_prevention_able[pokemon.pokemon_id] = False


@dataclass(frozen=True)
class DevolveChosenPokemon(Element):
    """自分または相手の場にいるポケモンの中から「進化カード」のついているもの 1 匹を選び、その「進化カード」を上から 1 枚はがして持ち主の手札に戻す（v0.50。ミュウの
    「たいかビーム」。kyuura の印刷の文面）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。選べるものは自分の場 → 相手の場の、実際に進化カードが重なっているポケモン。``effects.devolution_candidates``。
      今の姿（［へんしん］）ではなく実際の重なりで決める）。1 匹もいなければ何もしない（p.309。ログ ``devolve_none``）
    - 「ばける」でのせたカードのあるポケモン（「進化・退化」はできない）は選べるが選ぶと止める（DV5）。どれもそうなら、決定を出す前に止める（問い
      ``devolution_target_disguised``）
    - はがす前に、そのポケモンの「ワザをうけない」状態・「とうめい」を評価する（``reaches`` の ``devolve``。自分のポケモンでも「とうめい」は評価する。受けなければはがさない）
    - はがしたカードは持ち主の手札（``evolution.devolve`` の ``hand``。相手のポケモンのカードは相手の手札）。ワザによるダメージではなく、ワザの効果。退化して最大HPが
      のっているダメージ以下になったポケモンは、ワザのあとのきぜつの判定できぜつする（``_hp_dropped_in_attack``）
    """

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_POKEMON
    opponent_element: ClassVar[str] = E.DEVOLVE_ELEMENT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        options = E.devolution_candidates(state, (run.player, 1 - run.player))
        if not options:
            state.add_event("devolve_none", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key))
            return False
        forbidden = tuple(pid for pid in options if E.devolution_forbidden(state, state.find_pokemon(pid)[1]))
        if len(forbidden) == len(options):
            raise run.res.question("devolution_target_disguised", f"ポケモン {list(forbidden)}")
        # v0.120（FE1）: はがすとたねポケモンとしてあつかった進化カードがまたいちばん上になるポケモンは、選べるが選ぶと止める（ないときは v0.119 までの決定の形）
        revived = {pid: problem for pid in options if pid not in forbidden
                   for problem in (E.revived_devolve_problem(state, state.find_pokemon(pid)[1], 1),) if problem is not None}
        if len(forbidden) + len(revived) == len(options):
            raise UnsupportedError(*revived[next(iter(revived))])
        extra: tuple = ()
        if forbidden:
            extra = (("unresolved_choices", forbidden), ("unresolved_code", E.DEVOLUTION_TARGET_DISGUISED_CODE),
                     ("unresolved_reason", E.DEVOLUTION_TARGET_DISGUISED_REASON))
        if revived:
            stops = {**{pid: (E.DEVOLUTION_TARGET_DISGUISED_CODE, E.DEVOLUTION_TARGET_DISGUISED_REASON) for pid in forbidden}, **revived}
            first = stops[min(stops, key=options.index)]
            extra = (("unresolved_choices", tuple(pid for pid in options if pid in stops)), ("unresolved_code", first[0]), ("unresolved_reason", first[1]),
                     ("unresolved_detail", tuple((pid, *stops[pid]) for pid in options if pid in stops)))
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=options, extra=extra)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        found = state.find_pokemon(choices[0])
        if found is None or not found[1].evolution_stack or E.devolution_forbidden(state, found[1]):
            raise RuntimeError(f"たいかビームで選んだポケモン {choices} から進化カードをはがせない（決定の確認の漏れ。エンジンの不具合）")
        owner, target = found
        if not reaches(run.res, run.fs, owner, target, E.DEVOLVE_ELEMENT):
            return
        devolve(state, owner, target, 1, destination=DEVOLVE_TO_HAND, by_player=run.player, effect=str(run.key))
        _hp_dropped_in_attack(run)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ()))
        return [answer for answer in all_answers(decision) if not blocked & set(answer)]


# ---------------------------------------------------------------- v0.51（docs/discard-to-bench-v0.51.md）


@dataclass(frozen=True)
class HeadsPerDefenderCounters:
    """相手（相手の対戦ポケモン）にのっているダメージカウンターの数だけコインを投げ、「おもて」の数 × ``per``（v0.51。ナツメのスリーパーの「ふりこののろい」。p.321 の
    1 段階の基本となるダメージ）。数えるのはダメージの要素を処理する時点のカウンター（ダメージ ÷ 10）で、0 個ならコインを投げず 0。コインはダメージの要素の中（ダメージの
    量だけを決める）で、結果は「おもて」の数だけを使う（``by_heads``。先読みは「おもて」の数でまとめる。v0.35）。コイン 1 枚の「いかりのスーパーパンチ」
    （``HeadsOwnCounters``）とは別の値。"""

    per: int
    by_heads: ClassVar[bool] = True

    def coin_count(self, run: AttackRun) -> int:
        return run.opponent_active().damage // run.state.rules.damage_per_counter

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return (0 if flips is None else flips.heads) * self.per


@dataclass(frozen=True)
class BenchFromEitherDiscard(Element):
    """自分または相手のトラッシュから「たねポケモン」を 1 枚選び出し、持ち主のベンチに出す。そして、そのポケモンに、HP の半分（切り捨て）のダメージカウンターをのせる
    （v0.51。ナツメのスリーパーの「よみがえらせる」。``effects.BenchBasicFromEitherDiscard``）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``BENCH_FROM_DISCARD``。1 枚。省略できない）。選べるものは自分のトラッシュ → 相手のトラッシュの、たねポケモンのカードのうち、
      持ち主のベンチに空きがあるもの（``effects.bench_from_discard_candidates``）。1 枚もなければ処理の対象がないので何もしない（p.309。ログ ``bench_from_discard_none``）
    - 出す: ``zones.bench_from_discard``（持ち主のベンチ。同じ uid・新しい場のポケモンの番号・場に出た番は今の番）。ログ ``bench_from_discard``（``by_player`` はワザを
      使ったプレイヤー）。場に出たときの特殊能力は ``effects.discard_entry_power_guard``（今の対応カードでは起こらない）
    - そして、出したポケモンの今有効な最大HPの半分（切り捨て。``effects.half_hp_counters``）のダメージカウンターをのせる。ワザによるダメージではない。のせる前に「ワザを
      うけない」状態・「とうめい」を評価する（``reaches`` の ``damage_counters``。持ち主が相手でも自分でも）。0 個なら効果を受けない（v0.41 と同じ）。ログ
      ``place_damage_counters``（v0.41 と同じ形）
    - 先読みは、選べるすべてのカードを試す（``all_answers``。選んだカードは場のポケモンになるので、v0.44 の ``card_id_answers`` でまとめない）
    """

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = BENCH_FROM_DISCARD
    opponent_element: ClassVar[str] = E.COUNTERS_ELEMENT

    discard_protected = _discard_protected

    def candidates(self, run: AttackRun) -> tuple[int, ...]:
        return E.bench_from_discard_candidates(run.state, (run.player, 1 - run.player), E.text_era(run.key.card_id))

    def run(self, run: AttackRun) -> bool:
        if protected_discard(run, "bench_from_discard"):
            return False  # v0.119: ［アレルギーほうし］（ベンチに出さないので、カウンターものせない）
        candidates = self.candidates(run)
        if not candidates:
            attacker = run.attacker()
            run.state.add_event("bench_from_discard_none", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key))
            return False
        run.suspend(kind=BENCH_FROM_DISCARD, player=run.player, options=candidates)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        if len(choices) != 1 or choices[0] not in self.candidates(run):
            raise RuntimeError(f"よみがえらせるで選んだカード {choices} が、持ち主のベンチに出せるトラッシュのたねポケモンのカードではない（決定の確認の漏れ。エンジンの不具合）")
        card = choices[0]
        owner = state.cards[card].owner
        E.discard_entry_power_guard(state, card)
        pokemon = bench_from_discard(state, card)
        attacker = run.attacker()
        E.log_bench_from_discard(state, pokemon, by_player=run.player,
                                 source={"pokemon": attacker.card, "pokemon_id": attacker.pokemon_id, "effect": str(run.key)})
        per = state.rules.damage_per_counter
        count = E.half_hp_counters(state, E.max_hp(state, pokemon))  # 出したあとの今有効な最大HP（「そのポケモンに、HPの半分」）
        if count <= 0 or not reaches(run.res, run.fs, owner, pokemon, E.COUNTERS_ELEMENT):
            return
        before = pokemon.damage
        pokemon.damage = before + count * per
        state.add_event("place_damage_counters", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, effect=str(run.key),
                        counters=count, amount=count * per, damage_before=before, total_damage=pokemon.damage, attacker=run.player,
                        attacker_pokemon_id=run.fs.frame.source_pid)
        _counters_changed(run, pokemon, before)


# ---------------------------------------------------------------- v0.62（docs/history-attacks-v0.62.md）。前の番のワザの履歴を読む要素・相手を手札にもどす要素


@dataclass(frozen=True)
class UsedAttackCondition(Element):
    """ワザを使うための条件「このカードが、前の自分の番に「(``attack_name``)」を使っていた時だけ」（v0.62。タケシのダグトリオの「ドリルホール」）。使えるかは実装の
    ``usage_problem``（宣言の前）が確かめるので、処理では何もしない。このワザを自分のワザとして使うとき（「ゆびをふる」・ピジョンの「オウムがえし」）は ``copy_problem`` が
    使うポケモン（まねたポケモン）の使った記録で答える。「(``attack_name``)」を自分のワザとして使った記録が使っていたことになるかは決まらない（ED1）。"""

    attack_index: int
    attack_name: str
    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        return False

    def on_declare(self, res: Resolution, player: int, attacker: PokemonInPlay) -> None:
        # 自分のワザとして宣言したポケモンが、前の自分の番に「あながくれ」を宣言せず、ほかのワザでそれを自分のワザとして使っていた（ED1）。このワザを自分のワザとして持つ
        # ポケモン（タケシのダグトリオ・［へんしん］のメタモン・「ばける」のタケシのキュウコン）は「あながくれ」も自分のワザとして持つので、今の写しでは起こらない
        if E.used_attack_last_turn(res.state, attacker, self.attack_index, self.attack_name) == E.USED_AS_COPY:
            raise res.question("earthdrill_copied_use", f"ポケモン {attacker.pokemon_id}・「{self.attack_name}」")

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        status = E.used_attack_last_turn(run.state, copier, self.attack_index, self.attack_name)
        if status == E.USED:
            return None
        if status == E.USED_AS_COPY:
            return UNRESOLVED, f"前の自分の番に「{self.attack_name}」を、ほかのワザで自分のワザとして使っていた（使っていたことになるかが決まらない。ED1）"
        return (ILLEGAL if clause in (CANNOT_USE, FOLLOW_TEXT) else UNRESOLVED), f"前の自分の番に「{self.attack_name}」を使っていない（ワザを使うための条件）"


def _mirror_none(run: AttackRun, reason: str) -> None:
    attacker = run.attacker()
    run.state.add_event("mirror_move_none", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), reason=reason)


MIRROR_NO_ATTACK = "no_attack"  # 前の相手の番に相手のワザを受けていない（受けた記録がない）
MIRROR_NOT_RECEIVED = "not_received"  # 受けた記録はあるが、どの要素も受けなかった（「ワザをうけない」状態・「とうめい」）


@dataclass(frozen=True)
class RepeatReceivedAttack(Element):
    """前の相手の番で受けた「ワザ」と同じ「ワザ」をだす（v0.62。ピジョンの「オウムがえし」。実装 ``effects.RepeatReceivedAttack``）。

    - 受けた記録（``history.received_on``。前の番。このカードのもの）の処理したワザ（B）の要素の並びに切りかえ（``run.redirect``。v0.31 の ``CopyOpponentAttack`` と同じ）、
      このワザの枠の中で、ワザを使ったポケモンのワザとして処理する（弱点・抵抗力・「このカード」はワザを使ったポケモン。コイン・選ぶものは新しく決める。前の結果を使わない）
    - 記録がない・どの要素も受けなかった（理由がどれも「ワザをうけない」状態・「とうめい」）: 何もしない（ログ ``mirror_move_none``）
    - ダメージの要素だけを受けなかった（「ダメージを受けない」状態・見えない壁・「かげぶんしん」）・受けたワザが相手のワザを自分のワザとして使ったもの（宣言したワザと処理したワザが
      違う）: 受けた「ワザ」が決まらない（MM1）
    - 出すワザが、場に出てから 1 度だけ使えるワザ・要素の並びのないワザ: エンジンの未対応。説明が書く条件をみたさない（``copy_problem`` の ``clause`` は None）・必要な
      エネルギーをこのカードのエネルギーで払えない: みたす必要があるかが決まらない（MM2）
    - 切りかえたら、ログ ``copy_attack``（v0.31 の「ゆびをふる」と同じ。``received_turn`` に受けた番）
    """

    phase: ClassVar[Phase] = Phase.EFFECT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        return UNRESOLVED, "受けたワザと同じワザをだすワザを、さらに自分のワザとして使う"

    def run(self, run: AttackRun) -> bool:
        from ..history import VOID_ATTACK_BARRIER, VOID_EVADED, VOID_IMMUNE, received_on

        state = run.state
        attacker = run.attacker()
        turn = state.turn_number - 1
        record = received_on(attacker, turn)
        if record is None:
            _mirror_none(run, MIRROR_NO_ATTACK)
            return False
        if not record.reached and not any(reason == VOID_IMMUNE for _, reason in record.voided):
            if all(reason in (VOID_ATTACK_BARRIER, VOID_EVADED) for _, reason in record.voided):
                _mirror_none(run, MIRROR_NOT_RECEIVED)
                return False
            raise run.res.question("mirror_move_received_attack", f"ポケモン {attacker.pokemon_id}（受けなかった要素 {list(record.voided)}）")
        if record.declared != record.processed:
            raise run.res.question("mirror_move_received_attack",
                                   f"ポケモン {attacker.pokemon_id}（宣言したワザ {E.AttackKey(*record.declared)}・処理したワザ {E.AttackKey(*record.processed)}）")
        key = E.AttackKey(*record.processed)
        definition = state.definitions[key.card_id]
        attack = definition.attacks[key.attack_index]
        status = copy_status(run, definition, attack, None)
        if status is not None:
            if status[0] == UNSUPPORTED:
                raise run.res.question("mirror_move_unsupported_attack", f"「{attack.name_ja}」: {status[1]}")
            raise run.res.question("mirror_move_attack_conditions", f"「{attack.name_ja}」: {status[1]}")
        if not E.attack_cost_payable(state, attacker, attack):
            raise run.res.question("mirror_move_attack_conditions", f"「{attack.name_ja}」: 必要なエネルギーを、このカードについているエネルギーで払えない")
        effect = state.effects.attack_effect(definition.id, attack, definition.attacks)
        state.add_event("copy_attack", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.declared),
                        copied=str(key), copied_attack=attack.name_ja, received_turn=turn)
        run.redirect = (key, attack, BUILDERS[type(effect)](effect))
        return False


def reflected_record(run: AttackRun):
    """オニスズメの「オウムがえし」で与える、前の相手の番にこのカードが受けた記録（``history.received_on``。なければ None）。"""
    from ..history import received_on

    return received_on(run.attacker(), run.state.turn_number - 1)


@dataclass(frozen=True)
class ReflectCheck(Element):
    """オニスズメの「オウムがえし」（v0.62。実装 ``effects.ReflectReceivedDamageAndEffects``）の最初の要素: 与えるものを確かめる（与えるのは、あとの要素 ``ReflectedDamage``・
    ``ReflectedParalysis``）。

    - 前の相手の番にワザ以外でダメージ・効果を受けていた（``OtherReceived``）: それも与えるかが決まらない（OM2）
    - 受けた記録がない・どの要素も受けなかった: 何もしない（ログ ``mirror_move_none``）
    - 続く効果（ねむり・こんらん・どく・持続する効果。``effects.LASTING_RECEIVED_ELEMENTS``）を受けた: 「1回で消える」の読み方で与えたあとが変わる（OM1）
    - ほかの効果（入れ替え・エネルギー・ダメージカウンター・回復など）を受けた: 与えるのはエンジンの未対応（``UNSUPPORTED_MIRROR_MOVE_EFFECT``）
    - 与えるものが決まったら、ログ ``reflect_received``（受けた番・受けた最終ダメージ・効果の種類）"""

    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        from ..history import other_received_on

        state = run.state
        attacker = run.attacker()
        turn = state.turn_number - 1
        if other_received_on(attacker, turn):
            raise run.res.question("mirror_move_non_attack", f"ポケモン {attacker.pokemon_id}（{turn} 番）")
        record = reflected_record(run)
        if record is None or not record.reached:
            _mirror_none(run, MIRROR_NO_ATTACK if record is None else MIRROR_NOT_RECEIVED)
            return False
        lasting = sorted(kind for kind in record.reached if kind in E.LASTING_RECEIVED_ELEMENTS)
        if lasting:
            raise run.res.question("mirror_move_lasting_effect", f"ポケモン {attacker.pokemon_id}（{lasting}）")
        other = sorted(kind for kind in record.reached if kind not in E.REFLECTABLE_RECEIVED_ELEMENTS)
        if other:
            raise run.res.question("mirror_move_unsupported_effect", f"ポケモン {attacker.pokemon_id}（{other}）")
        state.add_event("reflect_received", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), received_turn=turn,
                        received_attack=str(E.AttackKey(*record.processed)), damage=record.damage,
                        effects=tuple(kind for kind in record.reached if kind != E.DAMAGE_ELEMENT))
        return False


@dataclass(frozen=True)
class ReceivedDamageAmount:
    """基本となるダメージ（p.321 の 1 段階）= 前の相手の番にこのカードが受けた最終ダメージの合計（v0.62。オニスズメの「オウムがえし」）。"""

    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        record = reflected_record(run)
        return 0 if record is None else record.damage


@dataclass(frozen=True)
class ReflectedDamage(Damage):
    """受けたダメージを相手の対戦ポケモンに与えるダメージの要素（v0.62）。受けた最終ダメージが 0 なら、ダメージの要素はない（ログもない）。"""

    def has_target(self, run: AttackRun) -> bool:
        record = reflected_record(run)
        return record is not None and record.damage > 0


@dataclass(frozen=True)
class ReflectedParalysis(Status):
    """受けたマヒを相手の対戦ポケモンに与える効果の要素（v0.62）。受けていなければ何もしない。与え方はほかのマヒを与える要素と同じ（``Status``。「とうめい」・「ワザを
    うけない」状態・［めんえき］・マヒの再付与・HP 以上の相手）。"""

    def _received(self, run: AttackRun) -> bool:
        record = reflected_record(run)
        return record is not None and PARALYSIS in record.reached

    def has_target(self, run: AttackRun) -> bool:
        return self._received(run) and super().has_target(run)

    def run(self, run: AttackRun) -> bool:
        if not self._received(run):
            return False
        return super().run(run)


@dataclass(frozen=True)
class ReturnOpponentToHand(Element):
    """相手の対戦ポケモンが「きぜつ」しなければ、そのカードにのっていたダメージカウンターをとりのぞき、そのカードとついていた全てのカードを持ち主の手札にもどす（v0.62。
    ピジョットの「ハリケーン」。実装 ``effects.DamageThenReturnOpponentToHand``）。

    - 相手の対戦ポケモンがこのワザで HP 以上なら処理しない（きぜつする。p.309）。こんじょうを使えるなら G37（``Status`` と同じ）
    - 相手への効果なので「ワザをうけない」状態・「とうめい」を評価する（受けないならもどさない）
    - 同じワザで HP 以上になったポケモン（「はんげき」などで返されたワザを使ったポケモン）がいれば、バトル場に出す時点ときぜつの処理の順番が決まらない（v0.36 の RD9。
      v0.44 のスターブーメランと同じ問い）
    - もどす（v0.42 の ``zones.return_in_play_to_hand``。持ち主の手札に。重なったカード・「ばける」でのせたカード・エネルギー・トレーナー。ダメージカウンター・特殊状態は
      なくなる）→ 持続する効果を消す（理由 ``return_in_play_to_hand``）。きぜつではない（サイドは取らない）
    """

    # v0.94（docs/switch-return-attacks-v0.94.md 8 章）: ワザ全体のコインの面（わるいドンファンの「すくいなげ」の「おもて」）。ピジョットの「ハリケーン」は None のまま
    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.RETURN_IN_PLAY_TO_HAND_ELEMENT

    def coin_receiver(self) -> str | None:
        return "effect"

    def has_target(self, run: AttackRun) -> bool:
        target = run.opponent_active()
        if target is None:
            return False
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        return True

    def leave_blocked(self, run: AttackRun) -> bool:
        target = run.opponent_active()
        return target is not None and leave_lock(run.state, 1 - run.player, target) is not None

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        state = run.state
        opponent = 1 - run.player
        target = state.players[opponent].active
        if target is None:
            return False
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if _leave_prevented(run, opponent, target, E.LEAVE_TO_HAND, None):
            return False  # v0.93: ダメージカウンターもとりのぞかない（もどす部分）
        if not reaches(run.res, run.fs, opponent, target, E.RETURN_IN_PLAY_TO_HAND_ELEMENT):
            return False
        from .kernel import knocked

        gone = knocked(run.res)
        if gone:
            raise run.res.question("return_in_play_to_deck_with_knockout", f"相手を手札にもどす。ポケモン {[p.pokemon_id for _, p in gone]}")
        ninja_trick_leave_question(run, target)  # v0.65（NT2）
        return_in_play_to_hand(state, opponent, target, effect=str(run.key))
        remove_persistent_effects(state, opponent, target, RETURN_IN_PLAY_TO_HAND)
        return False


# ---------------------------------------------------------------- v0.72（docs/status-coins-effect-reuse-v0.72.md）


@dataclass(frozen=True)
class PrintedPlusHeadsTimes:
    """ダメージの目安の数字 + コインを ``coins`` 枚投げた「おもて」の数 × ``per``（v0.72。ルギア（PRN-042）の「エアロブラスト」の「コインを2枚投げ、「おもて」の数×20のダメージを
    追加する。」。目安 20+ なので 20・40・60）。コインはダメージの要素の中（ダメージの量だけを決める）で、結果は「おもて」の数だけを使う（``by_heads``。先読みは「おもて」の数で
    まとめる。v0.35）。"""

    coins: int
    per: int
    by_heads: ClassVar[bool] = True

    @property
    def local_coins(self) -> int:
        return self.coins

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + (0 if flips is None else flips.heads) * self.per


@dataclass(frozen=True)
class WakeOpponent(Element):
    """相手の対戦ポケモンを「ねむり」状態から回復させる（v0.72。ナツメのルージュラ（GD6-012）の「めざめのキッス」）。

    - ねむりでなければ処理の対象がないので何もしない（「とうめい」も評価しない。v0.41 の回復の要素の「0 個のポケモンは効果を受けない」と同じ）
    - 相手がこのワザのダメージで HP 以上なら回復させない（p.309。こんじょうを使えるなら G37）
    - 相手のポケモンへの効果なので、回復させる前に「ワザをうけない」状態・「とうめい」を評価する（``reaches`` の ``WAKE_ELEMENT``）。回復はねむりだけ（どくは残す。``conditions.wake_up``）
    """

    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.WAKE_ELEMENT

    def run(self, run: AttackRun) -> bool:
        owner, target = 1 - run.player, run.opponent_active()
        if target is None or not target.conditions.asleep:
            return False
        if run.knocked_out(target):
            run.ko_prevention_conflict(target, owner)
            return False
        if not reaches(run.res, run.fs, owner, target, E.WAKE_ELEMENT):
            return False
        wake_up(run.state, owner, target, effect=str(run.key))
        return False


@dataclass(frozen=True)
class MoveOneEnergyToBench(Element):
    """ワザを使ったポケモンについている ``energy_type`` のエネルギーカードを 1 枚選んではがし、自分に控えポケモンがいれば 1 匹を選んでつける。控えがいなければトラッシュする
    （v0.72。マチスのエレブーの「デンキとばし」。``effects.DamageThenMoveOneEnergyToBench``）。

    - 決定は 2 つ: はがすカード（``MOVE_ENERGY``。``context`` の ``"stage"`` は ``"energy"``）→ つける控え（``ATTACH_TO_BENCH``。``"stage"`` は ``"bench"``・``"energy"`` は選んだ
      カード）。どちらも決めるのはワザを使ったプレイヤーで、決定のあいだカードはワザを使ったポケモンについたまま（2 つ目の答えで動かす）
    - つける控えの「とうめい」を評価し、受けないならそのカードはトラッシュ（v0.31 の ``MoveOwnEnergyToBench`` と同じ。CR-TRANSPARENCY-ENERGY-BOMB）。クリスタルビームの効果を
      受けている控えは CB1（選べるが選ぶと止める。どれもそうなら決定の前に止める）
    """

    energy_type: EnergyType
    phase: ClassVar[Phase] = Phase.EFFECT

    def decides(self, kind: str) -> bool:
        return kind in (MOVE_ENERGY, ATTACH_TO_BENCH)

    def run(self, run: AttackRun) -> bool:
        state = run.state
        attacker = run.attacker()
        if run.knocked_out(attacker):
            state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            element="move_energy", reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        transform_energy_question(run, attacker, self.energy_type, cards=True)
        candidates = E.attached_basic_energy(state, attacker, self.energy_type)
        if not candidates:
            return False
        run.suspend(kind=MOVE_ENERGY, player=run.player, options=candidates, carry=True, extra=(("stage", "energy"),))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        attacker = run.attacker()
        if run.carried.get("stage") == "energy":
            energy = choices[0]
            if energy not in E.attached_basic_energy(state, attacker, self.energy_type):
                raise RuntimeError(f"はがすカード {choices} が、ワザを使ったポケモンについている「{self.energy_type.ja}」エネルギーカードではない（エンジンの不具合）")
            bench = state.players[run.player].bench
            if not bench:
                E.discard_energy_from_play(  # v0.82: リサイクルエネルギー（デンキとばしの控えがいないとき）
                    state, attacker, (energy,), cause=E.DISCARD_BY_ATTACK, by_player=run.player,
                    log=lambda: state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                                energy=energy, reason="no_bench"))
                return
            extra = (("stage", "bench"), ("energy", energy))
            run.suspend(kind=ATTACH_TO_BENCH, player=run.player, options=[p.pokemon_id for p in bench], carry=True, extra=extra)
            return
        energy = run.carried["energy"]
        target = next((p for p in state.players[run.player].bench if p.pokemon_id == choices[0]), None)
        if energy not in attacker.energy or target is None:
            raise RuntimeError(f"つけかえるエネルギー {energy}・控えポケモン {choices} が正しくない（エンジンの不具合）")
        if E.energy_attach_block(state, target) is not None:
            # クリスタルビームの効果（持続する効果）はベンチにもどると消えるので、控えポケモンが受けていることはない（受けていたら CB1 の確かめが要る）
            raise RuntimeError(f"控えポケモン {target.pokemon_id} がクリスタルビームの効果を受けている（ベンチでは消えるはず。エンジンの不具合）")
        returns = E.energy_discard_plan(state, attacker, (energy,), cause=E.DISCARD_BY_ATTACK, by_player=run.player)  # v0.82: トラッシュに置くときだけ使う
        attacker.energy.remove(energy)
        if reaches(run.res, run.fs, run.player, target, E.ENERGY_ATTACH_ELEMENT):
            target.energy.append(energy)
            state.add_event("attack_attach_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy=energy, to_pokemon_id=target.pokemon_id)
            attached_in_attack(run, run.player, target, (energy,), moved=True)
        else:
            state.players[run.player].discard.append(energy)
            state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy=energy, reason="evaded", to_pokemon_id=target.pokemon_id)
            E.return_discarded_energy(state, returns)


@dataclass(frozen=True)
class DiscardOpponentTrainers(Element):
    """相手の対戦ポケモンについているトレーナーカードを、すべてトラッシュする（v0.78。デルビルの「ごうだつ」の「ダメージを与える前に、相手についている「トレーナーカード」を
    すべてトラッシュする。」）。ダメージの要素より前に置く（トラッシュしたあとの場でダメージを計算する）。

    - ついているトレーナーがなければ処理の対象がない（p.309。「とうめい」・「ワザをうけない」状態を評価しない）
    - 相手の対戦ポケモンへの効果（要素の種類 ``TRAINER_DISCARD_ELEMENT``）なので、トラッシュの前に「ワザをうけない」状態・「とうめい」を評価する（「とうめい」の結果は
      このワザの中で記録され、あとのダメージの要素も同じ結果を使う）
    - カードはつけたプレイヤー（``AttachedTrainer.player``。持ち主）のトラッシュに置く。ついている順に 1 枚ずつログ ``discard_attached_trainer``（``reason`` は ``attack``・
      ``effect`` はワザ）
    """

    # v0.79: 相手の場のポケモン全員（バトル場 → ベンチの並び）についているトレーナーカード（ニューラ（PF3-003）の「だましとる」）。偽なら相手の対戦ポケモンだけ（v0.78）
    all_pokemon: bool = False
    # v0.79: この要素のコイン（「だましとる」は「おもて」なら）。処理の対象（トレーナーカードのついている相手のポケモン）がなければ投げない（p.309）
    local_coin: CoinSide | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.TRAINER_DISCARD_ELEMENT

    def _targets(self, run: AttackRun) -> list[PokemonInPlay]:
        p = run.state.players[1 - run.player]
        candidates = ([p.active] if p.active is not None else []) + (list(p.bench) if self.all_pokemon else [])
        return [pokemon for pokemon in candidates if pokemon.trainers]

    def has_target(self, run: AttackRun) -> bool:
        return bool(self._targets(run))

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        targets = []
        for target in self._targets(run):
            if run.knocked_out(target):
                run.ko_prevention_conflict(target, opponent)
                continue
            targets.append(target)
        if not targets:
            return False
        if self.local_coin is not None:
            from .kernel import first_void

            if all(run.fs.reception.get(pokemon.pokemon_id) is False for pokemon in targets):
                raise run.res.question("evaded_effect_coin", f"ポケモン {[pokemon.pokemon_id for pokemon in targets]}")
            if all(first_void(run.res, run.incoming(), opponent, pokemon, Window.BEFORE_EFFECT) is not None for pokemon in targets):
                # このコインが決めるのは相手のポケモンへの効果だけで、どの対象も「ワザをうけない」状態（HC3。v0.31 のスーパーデストロイと同じ形）
                raise run.res.question("prevented_effect_coin", f"ポケモン {[pokemon.pokemon_id for pokemon in targets]}")
            if run.flip(1).results[0] is not self.local_coin:
                return False
        state = run.state
        for target in targets:
            # ポケモンごとに、トラッシュの前に「ワザをうけない」状態・「とうめい」を評価する（2 匹以上の「とうめい」は T27。``reaches``）
            if not reaches(run.res, run.fs, opponent, target, E.TRAINER_DISCARD_ELEMENT):
                continue
            for attached in list(target.trainers):
                target.trainers.remove(attached)
                state.players[attached.player].discard.append(attached.card)
                state.add_event("discard_attached_trainer", player=attached.player, card=attached.card, pokemon=target.card, pokemon_id=target.pokemon_id,
                                reason="attack", effect=str(run.key))
        return False


@dataclass(frozen=True)
class SelfCannotAttack(Element):
    """次の自分の番、ワザを使ったポケモンはワザ（すべて）を使えない（v0.78。エアームドの「メタルスラッシュ」。持続する効果 ``CannotAttackNextOwnTurn``）。ワザを使った
    ポケモンへの効果（v0.35 の ``SelfAttackLock`` と同じく「とうめい」を評価しない）。このワザの中で HP 以上になっていれば与えない（p.309）。

    v0.79: ``even_if_failed`` なら、ワザが失敗しても与える（ハガネール（PRN-014）の「メタルクラッシュ」の「コインを投げて「うら」なら、このワザは失敗する。(その場合も、
    ワザは使ったことになる)。次の自分の番、このカードはワザを使えない。」。失敗を決めるコインのあと、ダメージの要素のあとに置き、コインの結果（ナツメのESPでやり直したら
    やり直した結果）にかかわらず 1 回だけ与える）。"""

    even_if_failed: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT

    @property
    def after_failure(self) -> bool:
        return self.even_if_failed

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        return None  # 効果はワザの位置を記録しない（すべてのワザ）ので、相手のワザとして使っても使ったポケモンに与えられる

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("persistent_effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                persistent_effect=CannotAttackNextOwnTurn.kind, effect=str(run.key), reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        turn = run.state.turn_number
        effect = CannotAttackNextOwnTurn(source_card=attacker.card, source_player=run.player, created_turn=turn,
                                         active_turn=turn + CannotAttackNextOwnTurn.turns_until_active)
        add_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key))
        return False


@dataclass(frozen=True)
class SelfCannotRetreat(Element):
    """次の自分の番、ワザを使ったポケモンは「にげる」ことができない（v0.122。わるいオニドリルの「ドリルダイブ」。持続する効果 ``CannotRetreatNextOwnTurn``）。v0.78 の ``SelfCannotAttack`` と
    同じく、ワザを使ったポケモンへの効果（「とうめい」を評価しない）。このワザの中で HP 以上になっていれば与えない（p.309）。相手のワザとして使っても使ったポケモンに与える。"""

    phase: ClassVar[Phase] = Phase.EFFECT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        return None  # 効果はワザの位置を記録しないので、相手のワザとして使っても使ったポケモンに与えられる

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("persistent_effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                persistent_effect=CannotRetreatNextOwnTurn.kind, effect=str(run.key), reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        turn = run.state.turn_number
        effect = CannotRetreatNextOwnTurn(source_card=attacker.card, source_player=run.player, created_turn=turn,
                                          active_turn=turn + CannotRetreatNextOwnTurn.turns_until_active)
        add_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key))
        return False


# ---------------------------------------------------------------- v0.82（docs/energy-discard-return-v0.82.md）


@dataclass(frozen=True)
class AmountIfDiscarded:
    """トラッシュの要素 ``discard`` で 1 枚以上トラッシュしたら ``amount``、しなければダメージの目安の数字（v0.82。ライチュウ（neo3-025）の「らいげき」の「トラッシュした場合、
    このワザのダメージは「80」になる」。p.321 の 1 段階。v0.40 の ``AmountIfOwnBenchNamed`` と同じく、目安に足す数ではない）。"""

    discard: str
    amount: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        result = run.fs.results.get(self.discard)
        return self.amount if result is not None and result.cards else run.attack.damage


@dataclass(frozen=True)
class PrintedPlusHeadsOfCoin:
    """ダメージの目安の数字 + ワザ全体のコイン ``coin`` の「おもて」の数 × ``per``（v0.82。やさしいブースターの「ヒートフレイム」。同じコインがトラッシュする枚数も決める。
    p.321 の 1 段階）。"""

    coin: str
    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + run.heads(self.coin) * self.per


@dataclass(frozen=True)
class OptionalDiscardForBonus(Element):
    """のぞむなら、``energy_type`` の基本エネルギーカードを（``include_bench`` なら自分の控えポケモンについているものも）好きなだけ（``max_cards`` があればその枚数まで）
    トラッシュする（v0.82。ブーバーの「ファイヤーバーン」・ギャロップの「かえんじごく」。``effects.OptionalDiscardEnergyBonusDamage``）。結果は ``Discarded``（トラッシュした
    カード。ダメージの値 ``PlusPerDiscarded`` が数える）。

    - 決定 ``DISCARD_ENERGY``（0〜上限枚。0 枚は「のぞむなら」の、トラッシュしないこと）。選べるものがなければ決定を出さない
    - 選んだカードは、ついているポケモンごとにトラッシュする（ワザを使ったポケモン → 控え（ベンチの順））。控えポケモンのカードは、そのポケモンへのワザの効果なので「ワザを
      うけない」状態・「とうめい」を評価し（``reaches``）、受けないポケモンのカードはトラッシュしない（数えない）
    - 場からトラッシュに置くので、リサイクルエネルギー・エコロジムの処理を通す（``effects.discard_energy_from_play``）
    """

    energy_type: EnergyType
    include_bench: bool
    max_cards: int | None
    name: str = "discard"
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = DISCARD_ENERGY

    def holders(self, run: AttackRun) -> list[PokemonInPlay]:
        attacker = run.attacker()
        return [attacker] + (list(run.state.players[run.player].bench) if self.include_bench else [])

    def candidates(self, run: AttackRun) -> list[int]:
        found = []
        for pokemon in self.holders(run):
            transform_energy_question(run, pokemon, self.energy_type, cards=True)  # TE1・RB1・BZ2（どのポケモンのカードを数える・選ぶかが変わる）
            found += E.attached_basic_energy(run.state, pokemon, self.energy_type)
        return found

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            raise RuntimeError(f"ワザ {run.key} を使ったポケモンが、ダメージの前のトラッシュで HP 以上（エンジンの不具合）")
        candidates = self.candidates(run)
        if not candidates:
            run.fs.results[self.name] = Discarded(())
            return False
        top = len(candidates) if self.max_cards is None else min(self.max_cards, len(candidates))
        run.suspend(kind=DISCARD_ENERGY, player=run.player, options=candidates, min_choices=0, max_choices=top)
        return True

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        # 同じポケモンについている同じカード id のカードは、どれを選んでも同じ形の状態（ポケモンごと・カード id ごとの枚数の組だけを試す。組み合わせ・順番は区別しない）
        groups: dict[tuple[int, str], list[int]] = {}
        for pokemon in self.holders(run):
            for uid in pokemon.energy:
                if uid in decision.options:
                    groups.setdefault((pokemon.pokemon_id, run.state.cards[uid].card_id), []).append(uid)
        answers: list[tuple[int, ...]] = [()]
        for uids in groups.values():
            answers = [answer + tuple(uids[:count]) for answer in answers for count in range(len(uids) + 1)]
        return [answer for answer in answers if len(answer) <= decision.max_choices]

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        if any(uid not in self.candidates(run) for uid in choices):
            raise RuntimeError(f"トラッシュに選んだカード {choices} が、選べるカードではない（エンジンの不具合）")
        attacker = run.attacker()
        discarded: list[int] = []
        if not choices:
            state.add_event("discard_energy_declined", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key))
        for pokemon in self.holders(run):
            cards = tuple(uid for uid in pokemon.energy if uid in choices)
            if not cards:
                continue
            if pokemon is not attacker and not reaches(run.res, run.fs, run.player, pokemon, E.ENERGY_DISCARD_ELEMENT):
                continue
            for uid in cards:
                E.discard_energy_from_play(
                    state, pokemon, (uid,), cause=E.DISCARD_BY_ATTACK, by_player=run.player,
                    log=lambda uid=uid, pokemon=pokemon: state.add_event(
                        "discard_energy", player=run.player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, effect=str(run.key), energy=uid,
                        **({} if pokemon is attacker else {"attacker_pokemon_id": attacker.pokemon_id})))
                discarded.append(uid)
        run.fs.results[self.name] = Discarded(tuple(discarded))


@dataclass(frozen=True)
class OptionalDiscardAll(Element):
    """のぞむなら、自分についている ``energy_type`` の基本エネルギーカードを、すべてトラッシュする（v0.82。ライチュウ（neo3-025）の「らいげき」）。決定 ``OPTIONAL_DISCARD_ALL``
    （選べるものは 1。0 個（トラッシュしない）か 1 個（すべて））。ついていなければ決定を出さない。結果は ``Discarded``（``AmountIfDiscarded`` が見る）。"""

    energy_type: EnergyType
    name: str = "discard"
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = OPTIONAL_DISCARD_ALL

    def candidates(self, run: AttackRun) -> list[int]:
        transform_energy_question(run, run.attacker(), self.energy_type, cards=True)  # TE1・RB1・BZ2
        return E.attached_basic_energy(run.state, run.attacker(), self.energy_type)

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            raise RuntimeError(f"ワザ {run.key} を使ったポケモンが、ダメージの前のトラッシュで HP 以上（エンジンの不具合）")
        if not self.candidates(run):
            run.fs.results[self.name] = Discarded(())
            return False
        run.suspend(kind=OPTIONAL_DISCARD_ALL, player=run.player, options=(1,), min_choices=0, max_choices=1)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        attacker = run.attacker()
        if not choices:
            state.add_event("discard_energy_declined", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key))
            run.fs.results[self.name] = Discarded(())
            return
        cards = tuple(self.candidates(run))
        for uid in cards:
            E.discard_energy_from_play(
                state, attacker, (uid,), cause=E.DISCARD_BY_ATTACK, by_player=run.player,
                log=lambda uid=uid: state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                                    effect=str(run.key), energy=uid))
        run.fs.results[self.name] = Discarded(cards)


@dataclass(frozen=True)
class DiscardEachType(Element):
    """自分についている ``types`` の基本エネルギーカードを、それぞれ 1 枚ずつトラッシュする（v0.82。ルギアの「エレメンタルブラスト」・ひかるリザードンの「しゃくねつのほのお」。
    ``effects.DiscardEachTypeThenDamage``）。

    - 色の順に 1 つずつ決定 ``DISCARD_ENERGY``（その色のカード。ちょうど 1 枚。1 枚しかなくても出す。K2。``context`` の ``"type_index"``、選んだカードは ``"chosen"``）。
      選び終えてから、ついている順にまとめてトラッシュする。結果は ``Discarded``
    - どれかの色のカードがなければ、1 枚もトラッシュせず、結果の ``outcome`` は ``LACKING_NONE``（ダメージの要素を処理しない。ログ ``discard_energy_failed``）
    """

    types: tuple[EnergyType, ...]
    name: str = "discard"
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = DISCARD_ENERGY

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        if clause == CANNOT_USE and any(not E.attached_basic_energy(run.state, copier, t) for t in self.types):
            return ILLEGAL, f"「{'」「'.join(t.ja for t in self.types)}」のエネルギーカードが 1 枚ずつない"
        return None  # 説明がトラッシュできないときの処理（ダメージはなくなる）を書いている

    def options(self, run: AttackRun, index: int) -> list[int]:
        transform_energy_question(run, run.attacker(), self.types[index], cards=True)  # TE1・RB1・BZ2
        return E.attached_basic_energy(run.state, run.attacker(), self.types[index])

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            raise RuntimeError(f"ワザ {run.key} を使ったポケモンが、ダメージの前のトラッシュで HP 以上（エンジンの不具合）")
        missing = [t for i, t in enumerate(self.types) if not self.options(run, i)]
        if missing:
            run.fs.results[self.name] = Discarded((), LACKING_NONE)
            run.state.add_event("discard_energy_failed", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                needed=len(self.types), attached=len(self.types) - len(missing), outcome=LACKING_NONE,
                                missing_types=tuple(t.value for t in missing))
            return False
        return self._ask(run, 0, ())

    def _ask(self, run: AttackRun, index: int, chosen: tuple[int, ...]) -> bool:
        run.suspend(kind=DISCARD_ENERGY, player=run.player, options=self.options(run, index), min_choices=1, max_choices=1, carry=True,
                    extra=(("type_index", index), ("chosen", chosen)))
        return True

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, (1,))  # 同じ色の基本エネルギーカード（同じカード id）は、どれを選んでも同じ形の状態

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        index = run.carried["type_index"]
        chosen = tuple(run.carried.get("chosen", ())) + tuple(choices)
        if len(choices) != 1 or choices[0] not in self.options(run, index):
            raise RuntimeError(f"トラッシュに選んだカード {choices} が、「{self.types[index].ja}」エネルギーカードではない（エンジンの不具合）")
        if index + 1 < len(self.types):
            self._ask(run, index + 1, chosen)
            return
        state = run.state
        attacker = run.attacker()
        cards = tuple(uid for uid in attacker.energy if uid in chosen)
        for uid in cards:
            E.discard_energy_from_play(
                state, attacker, (uid,), cause=E.DISCARD_BY_ATTACK, by_player=run.player,
                log=lambda uid=uid: state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                                    effect=str(run.key), energy=uid))
        run.fs.results[self.name] = Discarded(cards)


@dataclass(frozen=True)
class ChosenBenchCoinDamage(Element):
    """相手の控えポケモンを 1 匹選ぶ。コインを ``coins`` 枚投げ、「おもて」の数 × ``per`` ダメージを、「弱点・抵抗力」に関係なく、そのポケモンに与える（v0.82。マグマラシの
    「ほのおのかぜ」）。選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。控えが 1 匹でも出す）。選んでからコインを投げる。控えがいなければ選ばず、コインも投げない。
    v0.33 の ``ChosenBenchDamage``（コインは選ぶ前）とはコインの位置が違う。前のダメージの要素の送る効果は決定をまたいで運ぶ（``carry``）。"""

    coins: int
    per: int
    name: str = "bench_damage"
    phase: ClassVar[Phase] = Phase.DAMAGE
    guards_bench: ClassVar[bool] = True
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def has_target(self, run: AttackRun) -> bool:
        return bool(run.state.players[1 - run.player].bench)

    def run(self, run: AttackRun) -> bool:
        bench = run.state.players[1 - run.player].bench
        if not bench:
            return False
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=[p.pokemon_id for p in bench], carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        bench = run.state.players[1 - run.player].bench
        target = next((p for p in bench if p.pokemon_id == choices[0]), None)
        if target is None:
            raise RuntimeError(f"選んだポケモン {choices} が、相手の控えにいない（エンジンの不具合）")
        from .kernel import first_void

        void = first_void(run.res, run.incoming(), 1 - run.player, target)
        if void is not None:
            # このコインが決めるのは、選んだ控えポケモンへのダメージだけで、そのポケモンはダメージを受けない（見えない壁）。v0.4b と同じ問い（投げるかが決まらない）
            raise run.res.question("prevented_coin_damage", f"ダメージを受けない控えポケモン {target.pokemon_id}（見えない壁）へのダメージだけを決めるコイン")
        flips = run.flip(self.coins, by_heads=True)
        guarded_damages(run, self, [(E.OPPONENT_BENCH, target.pokemon_id, flips.heads * self.per, False)], record=True)  # v0.65: ［ベンチガード］


# ---------------------------------------------------------------- v0.83（docs/shining-gentle-pokemon-v0.83.md）


@dataclass(frozen=True)
class Exactly:
    """ワザ全体のコインの「おもて」の数がちょうど ``count``（v0.83。ひかるヨルノズクの「フラッシュアイ」の「「おもて」が1枚なら…、2枚なら…」）。「おもて」の数だけを使うので、
    先読みは「おもて」の数でまとめて試せる（v0.35）。``AtLeast`` と違い、それより多いときは満たさない。"""

    count: int


@dataclass(frozen=True)
class ChosenTarget:
    """v0.83: 先に選んだ控えポケモン（``ChooseOpponentBench``）の番号。``fs.results`` に置き、決定をまたぐときは続きの情報の ``chosen_targets`` で運ぶ（v0.82 の ``DiscardEachType`` の ``chosen`` とは別の名前）（``AttackRun.suspend``）。
    選べなかった（控えがいなかった）なら ``pokemon_id`` は None。

    v0.89: ``owner`` は選んだ個体の持ち主（``ChooseTarget`` が置く。v0.83 の ``ChooseOpponentBench`` は None のまま。あとの要素は番号で個体を探し、場をはなれていれば
    何もしない。今の対戦ポケモン・同じ名前の別のポケモンにすり替えない）。"""

    pokemon_id: int | None
    owner: int | None = None


def typed_energy_units(run: AttackRun, pokemon: PokemonInPlay, energy_type: EnergyType) -> int:
    """v0.83: ``pokemon`` についている「``energy_type``」エネルギーの数（エネルギーの個数。カードの枚数ではない。``effects.attached_units`` の 1 個ずつのうち、その色だけの
    もの）。［へんしん］のメタモン（TE1）・レインボーエネルギー（RB1）・［エネエネ］（BZ2）で数え方が決まらなければ止める（``transform_energy_question``）。"""
    transform_energy_question(run, pokemon, energy_type, cards=False)
    return sum(1 for unit in E.attached_units(run.state, pokemon) if unit == frozenset({energy_type}))


def all_energy_units(state: GameState, pokemon: PokemonInPlay | None, run: AttackRun | None = None) -> int:
    """v0.83: ``pokemon`` についている「エネルギー」の数（すべての色。エネルギーの個数。無色2個エネルギーは 2 個、レインボーエネルギーは 1 個。カードの枚数ではない）。
    v0.85: ``run`` があれば、［おいしげる］で個数が決まらないカードがあれば止める（``wild_growth_question``）。"""
    if run is not None:
        wild_growth_question(run, pokemon)
    return 0 if pokemon is None else E.energy_unit_count(state, pokemon.energy, pokemon)


@dataclass(frozen=True)
class PlusOwnCountersOnHeads:
    """ダメージの目安の数字 + 自分にのっているダメージカウンターの数 × ``per``（v0.83。ひかるギャラドスの「げきりん」の「「おもて」なら、…追加する」。コインの「うら」で
    ワザは失敗する（``FailOnTails``）ので、この値を使うのは「おもて」のときだけ。``PlusOwnCounters`` と同じ値）。"""

    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + run.attacker().damage // run.state.rules.damage_per_counter * self.per


@dataclass(frozen=True)
class PlusDefenderEnergyUnits:
    """ダメージの目安の数字 + 相手（相手の対戦ポケモン）についている「エネルギー」の数 × ``per``（v0.83。ひかるミュウツーの「サイコバースト」。エネルギーの個数。v0.31 の
    ``PlusDefenderEnergy``（「エネルギーカード」の枚数）とは別の値）。"""

    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + all_energy_units(run.state, run.opponent_active(), run) * self.per


@dataclass(frozen=True)
class DefenderEnergyUnitsTimes:
    """相手（相手の対戦ポケモン）についている「エネルギー」の数 × ``per``（v0.105。バタフリー（neo2-009）の「ハイパーリバース」。p.321 の 1 段階の基本となるダメージそのもの。目安の
    数字はない）。エネルギーの個数（``all_energy_units``。無色2個エネルギーは 2）で、v0.50 の ``DefenderEnergyCardsTimes``（カードの枚数）とは別の値。0 個なら 0。"""

    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return all_energy_units(run.state, run.opponent_active(), run) * self.per


@dataclass(frozen=True)
class PlusDefenderSpecialEnergyCards:
    """ダメージの目安の数字 + 相手についている「特殊エネルギーカード」の枚数 × ``per``（v0.83。やさしいゴルダックの「コアブラスト」。カードの枚数。ついている間の定義で決める
    （［エネエネ］で場についているカードは特殊エネルギーの種類の定義。``GameState.card_def``））。"""

    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        target = run.opponent_active()
        count = 0 if target is None else sum(1 for uid in target.energy if run.state.card_def(uid).is_special_energy)
        return run.attack.damage + count * self.per


@dataclass(frozen=True)
class PlusIfDefenderMoreEnergy:
    """ダメージの目安の数字。相手についている「エネルギー」の数が自分についている「エネルギー」の数より多いとき、``bonus`` を加える（v0.83。やさしいヤドランの「みずあそび」。
    エネルギーの個数で比べる。同じ数なら加えない）。"""

    bonus: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        more = all_energy_units(run.state, run.opponent_active(), run) > all_energy_units(run.state, run.attacker(), run)
        return run.attack.damage + (self.bonus if more else 0)


@dataclass(frozen=True)
class ExcessTypedEnergy:
    """ダメージの目安の数字 + ワザに必要な「``energy_type``」エネルギーよりも多くついている「``energy_type``」エネルギー 1 個につき ``per``（v0.83。ひかるカブトプスの
    「ウォータースラッシュ」。上限なし）。

    - 必要なエネルギーのうち、その色の記号の数（無色の記号はない書き方だけを登録する。必要なエネルギーに無色がまざるときの、どのエネルギーで払ったかの扱い（v0.31 の HC4）は
      この書き方では起こらない。型の ``check`` が確かめる）より多い「``energy_type``」エネルギーの数（エネルギーの個数。``typed_energy_units``）
    - 相手のワザとして使う（ゆびをふるなど。必要なエネルギーはいらない）ときも、ワザの必要なエネルギーの記号で数える（v0.4c の ``ExtraEnergy`` と同じ読み方）"""

    energy_type: EnergyType
    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        attached = typed_energy_units(run, run.attacker(), self.energy_type)
        needed = sum(1 for symbol in run.attack.cost if symbol is self.energy_type)
        return run.attack.damage + max(0, attached - needed) * self.per


@dataclass(frozen=True)
class OwnTypedEnergyTimes:
    """自分（ワザを使ったポケモン）についている「``energy_type``」エネルギーの数 × ``per``（v0.83。ひかるライチュウの「サンダースコール」の控えへのダメージ。エネルギーの個数）。"""

    energy_type: EnergyType
    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return typed_energy_units(run, run.attacker(), self.energy_type) * self.per


@dataclass(frozen=True)
class EachPlayerStep(Element):
    """おたがいのプレイヤーが、それぞれ自分のカードについて選ぶ（v0.83。「おたがいのプレイヤーは、それぞれ、…」のワザの共通の進み方）。

    - 順番は、ワザを使ったプレイヤー → 相手プレイヤー（実装上の順番。説明は順番を書かない。v0.54 のエリカ・v0.73 のパソコン大暴走！は説明に「あなたがカードを引き終わって
      から、相手プレイヤーが引く」があり、その順番と同じにした。先に選んだプレイヤーの公開したカード・引いた枚数を、あとのプレイヤーは知ってから選ぶ。研究の論点として
      docs 3 章に書く）
    - 決めるのはそのプレイヤー自身（相手の決定は、相手のカード（山札・トラッシュ）について相手が決める。ワザを使ったプレイヤーが相手のぶんを答えない）。``context`` の
      ``"stage"`` は 0（ワザを使ったプレイヤー）・1（相手プレイヤー）
    - 選べるものがないプレイヤーには決定を出さない（``skip``）。部分型は ``options``・``bounds``・``apply``・``skip``・``finish`` を書く"""

    phase: ClassVar[Phase] = Phase.EFFECT

    def chooser(self, run: AttackRun, stage: int) -> int:
        return run.player if stage == 0 else 1 - run.player

    def options(self, run: AttackRun, player: int) -> tuple[int, ...]:
        raise NotImplementedError

    def bounds(self, run: AttackRun, player: int, options: tuple[int, ...]) -> tuple[int, int]:
        raise NotImplementedError

    def extra(self, run: AttackRun, player: int) -> tuple:
        return ()

    def apply(self, run: AttackRun, player: int, choices: tuple[int, ...]) -> None:
        raise NotImplementedError

    def skip(self, run: AttackRun, player: int) -> None:
        return None

    def finish(self, run: AttackRun) -> None:
        return None

    def start(self, run: AttackRun) -> bool:
        """``run`` の最初の処理（コイン・ポケモンタワーなど）。True なら決定の処理をしない（部分型が上書きする）。"""
        return False

    def run(self, run: AttackRun) -> bool:
        if self.start(run):
            return False
        return self._offer(run, 0)

    def _offer(self, run: AttackRun, stage: int) -> bool:
        for current in range(stage, 2):
            player = self.chooser(run, current)
            options = self.options(run, player)
            if not options:
                self.skip(run, player)
                continue
            low, high = self.bounds(run, player, options)
            run.suspend(kind=self.decision_kind, player=player, options=options, min_choices=low, max_choices=high, carry=True,
                        extra=(("stage", current),) + self.extra(run, player))
            return True
        self.finish(run)
        return False

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        stage = run.carried["stage"]
        player = self.chooser(run, stage)
        if decision.player != player or set(choices) - set(self.options(run, player)):
            raise RuntimeError(f"おたがいのプレイヤーが選ぶ決定 {decision.kind} の答え {choices} が、プレイヤー {player} の選べるものではない（エンジンの不具合）")
        self.apply(run, player, choices)
        self._offer(run, stage + 1)


@dataclass(frozen=True)
class EachPlayerDraws(EachPlayerStep):
    """おたがいのプレイヤーは、のぞむなら、それぞれの山札からカードを最大 ``max_cards`` 枚まで引いて、手札に加えてよい（v0.83。ひかるコイキングの「きんいろのうろこ」）。

    - 引く枚数を決めるのは引くプレイヤー自身（決定 ``SELECT_DRAW_COUNT``。v0.54 のエリカと同じ。選べるものは 0〜min(``max_cards``, 自分の山札の枚数)。0 は「のぞむなら」の、
      引かないこと（ログ ``attack_draw_declined`` の ``reason`` ``declined``）。山札が 0 枚なら決定を出さない（``reason`` ``empty_deck``）。英語版の「2 枚引くか、引かないか」に
      しない）
    - 引いたカードは引いたプレイヤーだけが見る（ログ ``draw``。枚数は公開）"""

    max_cards: int = 2
    decision_kind: ClassVar[str] = SELECT_DRAW_COUNT
    reads_deck_order: ClassVar[bool] = True

    def options(self, run: AttackRun, player: int) -> tuple[int, ...]:
        deck = run.state.players[player].deck
        return tuple(range(min(self.max_cards, len(deck)) + 1)) if deck else ()

    def bounds(self, run: AttackRun, player: int, options: tuple[int, ...]) -> tuple[int, int]:
        return 1, 1

    def apply(self, run: AttackRun, player: int, choices: tuple[int, ...]) -> None:
        if choices[0]:
            draw_cards(run.state, player, choices[0])
        else:
            run.state.add_event("attack_draw_declined", player=player, effect=str(run.key), attacker=run.player, reason="declined")

    def skip(self, run: AttackRun, player: int) -> None:
        run.state.add_event("attack_draw_declined", player=player, effect=str(run.key), attacker=run.player, reason="empty_deck")

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return [(count,) for count in decision.options]


DISCARD_RECOVERY_CATEGORIES = ("pokemon", "any")


@dataclass(frozen=True)
class EachPlayerRecoversFromDiscard(EachPlayerStep):
    """おたがいのプレイヤーは、それぞれ、のぞむなら、自分のトラッシュから ``category`` のカードを ``max_cards`` 枚まで選び出してよい。選び出したプレイヤーは、そのカードを
    相手プレイヤーに見せてから、``destination`` に置く（v0.83。やさしいモルフォンの「ふしぎなはばたき」（ポケモンのカード・1 枚・手札）・やさしいランターンの「あかりでてらす」
    （カード・1 枚・手札。``local_coin`` の「おもて」のとき）・やさしいヤドランの「すくいあげる」（ポケモンのカード・3 枚まで・山札。そのあと選び出したプレイヤーの山札を切る））。

    - 決定は、手札に加えるなら ``RECOVER_POKEMON``（v0.43 の［つりあげる］と同じ「見せてから手札に加える」決定。あかりでてらすはどの種類のカードも選べる）、山札にもどすなら
      ``DISCARD_TO_DECK``（v0.53 の夜の廃品回収と同じ）。選べるものは自分のトラッシュの ``category`` のカード（トラッシュの並び。トラッシュは公開の情報）。0〜min(``max_cards``,
      枚数)。0 は「のぞむなら」「てよい」の、選ばないこと（ログ ``each_player_declined``）。トラッシュに選べるカードがなければ決定を出さない（``reason`` ``no_target``）
    - 「ポケモンのカード」は、トラッシュにある間の印刷の分類（``GameState.card_def``）がポケモン（なにかの化石・ピッピ人形はトレーナーカード）
    - ポケモンタワー（v0.74）の場では、手札に加える効果は消える（``suppressed_discard_to_hand``。おたがいのぶんとも。コインの前に確かめ、コインも投げない（v0.75 の
      「おにびあつめ」と同じ読み方））。山札にもどす効果は消えない
    - 山札にもどしたら、そのプレイヤーの山札を 1 回だけ切る（説明の「その後、その山札をよく切る」。選び出したプレイヤーだけ。0 枚なら切らない（実装上の読み方））"""

    category: str = "pokemon"
    max_cards: int = 1
    destination: str = "hand"
    local_coin: CoinSide | None = None

    def __post_init__(self) -> None:
        if self.category not in DISCARD_RECOVERY_CATEGORIES or self.destination not in ("hand", "deck"):
            raise ValueError(f"トラッシュから選ぶカードの種類 {self.category!r}・行き先 {self.destination!r} は未定義")

    @property
    def decision_kind(self) -> str:  # type: ignore[override]
        return RECOVER_POKEMON if self.destination == "hand" else DISCARD_TO_DECK

    def decides(self, kind: str) -> bool:
        return kind == self.decision_kind

    discard_protected = _discard_protected

    def start(self, run: AttackRun) -> bool:
        if self.destination == "hand" and suppressed_discard_to_hand(run):
            return True
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return True
        # v0.119: ［アレルギーほうし］（おたがいのぶんとも選ばない。コインは、選べるカードがなくても投げる今までの読み方のまま（どちらの読み方でも投げるので AP1 に当たらない））
        return protected_discard(run, "each_player_recover")

    def options(self, run: AttackRun, player: int) -> tuple[int, ...]:
        state = run.state
        return tuple(uid for uid in state.players[player].discard if self.category == "any" or state.card_def(uid).category == self.category)

    def bounds(self, run: AttackRun, player: int, options: tuple[int, ...]) -> tuple[int, int]:
        return 0, min(self.max_cards, len(options))

    def apply(self, run: AttackRun, player: int, choices: tuple[int, ...]) -> None:
        state = run.state
        if not choices:
            state.add_event("each_player_declined", player=player, effect=str(run.key), attacker=run.player, reason="declined")
            return
        if len(set(choices)) != len(choices):
            raise RuntimeError(f"トラッシュから選んだカード {choices} が重なっている（エンジンの不具合）")
        cards = tuple(uid for uid in state.players[player].discard if uid in choices)  # トラッシュの並びの順
        if self.destination == "hand":
            return_discard_to_hand(state, player, cards)
            state.add_event("each_player_recover", player=player, effect=str(run.key), attacker=run.player, cards=cards)
            return
        p = state.players[player]
        for uid in cards:
            p.discard.remove(uid)
            p.deck.append(uid)
        state.add_event("each_player_discard_to_deck", player=player, effect=str(run.key), attacker=run.player, cards=cards)
        shuffle_in_attack(run, self, player)

    def skip(self, run: AttackRun, player: int) -> None:
        run.state.add_event("each_player_declined", player=player, effect=str(run.key), attacker=run.player, reason="no_target")

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, range(decision.max_choices + 1))


ATTACK_LOOK_COUNT = 3


def attack_deck_top_short(run: AttackRun, players: Iterable[int], count: int) -> None:
    """v0.83（LT1）: 「山札の上からカードを3枚見る」ワザで、見るプレイヤーの山札が ``count`` 枚より少ないなら止める（先読みが宣言の前に見つける）。"""
    short = [(player, len(run.state.players[player].deck)) for player in players if len(run.state.players[player].deck) < count]
    if short:
        raise run.res.question("attack_deck_top_short", f"ワザ {run.key}・山札が {count} 枚より少ないプレイヤー {short}")


@dataclass(frozen=True)
class EachPlayerLooksTakesBasicEnergy(EachPlayerStep):
    """おたがいのプレイヤーは、それぞれ、自分の山札の上からカードを ``look`` 枚見る。その後、それぞれ、見た中にある「基本エネルギーカード」を好きなだけ選び出し、相手プレイヤーに
    見せてから、自分の手札に加える。山札を見たプレイヤーは、その山札をよく切る（v0.83。やさしいゴルダックの「みずかき」）。

    - 見るのはそれぞれ自分の山札の上（山札全体をさがさない）。見たカードはそのプレイヤーだけが見る（ログ ``look_at_deck_top``）。決定は ``TAKE_LOOKED_CARDS``（選べるものは
      見た中の基本エネルギーカード（山札の上からの順）。0〜枚数。「好きなだけ」なので 0 枚も選べる）。選んだカードだけを見せて手札に加え（``reveal_deck_to_hand``）、
      そのプレイヤーの山札を 1 回切る。見た中に基本エネルギーカードがなくても、選べるもののない決定（0 枚だけが答え）を出して答えを待つ（v0.84 の A3。決定を出すか・
      進み方・切る時点が見えない山札の中身で変わらない）。選ばなかったログ ``deck_top_take_declined`` の理由（選べるカードがなかった・選ばなかった）は
      山札の上の中身の情報なので、見たプレイヤーだけが見る
    - どちらかの山札が ``look`` 枚より少なければ LT1（見る前に止める。あるだけ見るかが決まらない）
    - 順番は ``EachPlayerStep``（ワザを使ったプレイヤーが見て・選んで・切ってから、相手プレイヤー）"""

    look: int = ATTACK_LOOK_COUNT
    decision_kind: ClassVar[str] = TAKE_LOOKED_CARDS

    def start(self, run: AttackRun) -> bool:
        attack_deck_top_short(run, (run.player, 1 - run.player), self.look)
        return False

    def _looked(self, run: AttackRun, player: int) -> tuple[int, ...]:
        return tuple(run.state.players[player].deck[:self.look])

    def options(self, run: AttackRun, player: int) -> tuple[int, ...]:
        return tuple(uid for uid in self._looked(run, player) if run.state.card_def(uid).is_basic_energy)

    def bounds(self, run: AttackRun, player: int, options: tuple[int, ...]) -> tuple[int, int]:
        return 0, len(options)

    def _offer(self, run: AttackRun, stage: int) -> bool:
        for current in range(stage, 2):
            player = self.chooser(run, current)
            looked = self._looked(run, player)
            run.state.add_event("look_at_deck_top", player=player, owner=player, count=len(looked), cards=looked, effect=str(run.key))
            options = self.options(run, player)
            # v0.84（docs/light-powers-evolution-v0.84.md 2 章の A3）: 見た中に基本エネルギーカードがなくても（選べるものが 0）、決定を出してそのプレイヤーの答えを待つ。
            # 選べるものの有無で、決定を出すか・次のプレイヤーへ進むか・切る時点が変わると、相手に山札の上の中身が漏れる（v0.83 は、ないときに決定を出さずに進んでいた）
            run.suspend(kind=TAKE_LOOKED_CARDS, player=player, options=options, min_choices=0, max_choices=len(options), carry=True,
                        extra=(("stage", current),))
            return True
        return False

    def apply(self, run: AttackRun, player: int, choices: tuple[int, ...]) -> None:
        if len(set(choices)) != len(choices):
            raise RuntimeError(f"選んだカード {choices} が重なっている（エンジンの不具合）")
        if not choices:
            # 理由（選べるカードがなかった・選ばなかった）は山札の上の中身の情報なので、見たプレイヤーだけが見る（観測の非公開の項目）
            reason = "declined" if self.options(run, player) else "no_target"
            run.state.add_event("deck_top_take_declined", player=player, effect=str(run.key), attacker=run.player, reason=reason)
        for uid in sorted(choices, key=run.state.players[player].deck.index):
            reveal_deck_to_hand(run.state, player, uid, effect=str(run.key))
        shuffle_in_attack(run, self, player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, range(decision.max_choices + 1))


@dataclass(frozen=True)
class LookTopTakeOne(Element):
    """自分の山札の上からカードを ``look`` 枚見る。その中から好きなカードを 1 枚選び出し、自分の手札に加える。その後、その山札をよく切る（v0.83。ひかるミュウの「フラッシュサーチ」）。

    - 見たカードはワザを使ったプレイヤーだけが見る（ログ ``look_at_deck_top``）。決定 ``TAKE_LOOKED_CARDS``（選べるものは見たカード（上からの順）。ちょうど 1 枚。種類を問わない）。
      選んだカードは見せない（ログ ``search_deck``。見せる指示がない）。ほかのカードはトラッシュせず・並べかえず、そのあと山札を切る
    - 山札が ``look`` 枚より少なければ LT1（見る前に止める）"""

    look: int = ATTACK_LOOK_COUNT
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = TAKE_LOOKED_CARDS

    def run(self, run: AttackRun) -> bool:
        attack_deck_top_short(run, (run.player,), self.look)
        looked = tuple(run.state.players[run.player].deck[:self.look])
        run.state.add_event("look_at_deck_top", player=run.player, owner=run.player, count=len(looked), cards=looked, effect=str(run.key))
        run.suspend(kind=TAKE_LOOKED_CARDS, player=run.player, options=looked, min_choices=1, max_choices=1)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if len(choices) != 1 or choices[0] not in run.state.players[run.player].deck[:self.look]:
            raise RuntimeError(f"手札に加えるカード {choices} が、見た山札の上のカードではない（エンジンの不具合）")
        search_deck_to_hand(run.state, run.player, choices[0])
        shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, (1,))


@dataclass(frozen=True)
class HealChosenOwnBench(Element):
    """自分の控えポケモンを 1 匹選ぶ。その後、自分についている「``energy_type``」エネルギーの数ぶんのダメージカウンターを、選んだポケモンからとりのぞく（v0.83。ひかるセレビィの
    「いやしのみず」）。自分に控えがいないとき、このワザは失敗する（説明。宣言の前に拒否しない。p.323「12」。ログ ``attack_failed`` の ``reason`` ``no_bench``）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。控えが 1 匹でも出す）。ダメージカウンターのない控えも選べる（とりのぞく数は 0）
    - とりのぞく数は、選んだあとの時点の自分の「``energy_type``」エネルギーの数（エネルギーの個数。``typed_energy_units``）。のっている数まで。0 個ならとりのぞかない
    - 選んだポケモンへのワザの効果なので、「ワザをうけない」状態・「とうめい」を評価する（``reaches``。v0.41 の ``HealCounters`` と同じ）。ログ ``attack_heal``"""

    energy_type: EnergyType
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def run(self, run: AttackRun) -> bool:
        bench = run.state.players[run.player].bench
        if not bench:
            run.fail("no_bench")
            return False
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=[p.pokemon_id for p in bench], carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        target = next((p for p in state.players[run.player].bench if p.pokemon_id == choices[0]), None)
        if target is None:
            raise RuntimeError(f"選んだポケモン {choices} が、自分の控えにいない（エンジンの不具合）")
        count = typed_energy_units(run, run.attacker(), self.energy_type)
        per = state.rules.damage_per_counter
        removed = min(count, target.damage // per)
        if removed <= 0 or not reaches(run.res, run.fs, run.player, target, E.HEAL_ELEMENT):
            return
        before = target.damage
        target.damage = before - removed * per
        state.add_event("attack_heal", player=run.player, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key),
                        counters=removed, amount=removed * per, damage_before=before, total_damage=target.damage)


@dataclass(frozen=True)
class WashOwnBench(Element):
    """コインを投げて「おもて」なら、自分の控えポケモンを 1 匹選ぶ。その後、そのポケモンにのっているダメージカウンターを、すべてとりのぞき、そのポケモンについている
    「エネルギーカード」を、すべてトラッシュする（v0.83。やさしいシャワーズの「あらいながす」）。自分に控えがいないとき、このワザは失敗する（説明。コインの前に確かめる。
    控えがいなければコインを投げない（実装上の判断。コインの結果によらずワザは失敗する））。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``）。選んだポケモンへのワザの効果なので、「ワザをうけない」状態・「とうめい」を評価し（``reaches``。とりのぞく・
      トラッシュする前に 1 回）、受けないなら何もしない
    - とりのぞく（ログ ``attack_heal``。0 個なら書かない）→ トラッシュ（種類を問わないエネルギーカードすべて。``effects.discard_energy_from_play``。原因はワザ・使ったのは
      ワザを使ったプレイヤー。リサイクルエネルギーは持ち主の手札にもどる。自分のポケモンなのでエコロジムは当たらない。ログ ``discard_attached_energy``）"""

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def run(self, run: AttackRun) -> bool:
        bench = run.state.players[run.player].bench
        if not bench:
            run.fail("no_bench")
            return False
        if run.flip(1).results[0] is not HEADS:
            return False
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=[p.pokemon_id for p in bench], carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        target = next((p for p in state.players[run.player].bench if p.pokemon_id == choices[0]), None)
        if target is None:
            raise RuntimeError(f"選んだポケモン {choices} が、自分の控えにいない（エンジンの不具合）")
        if not reaches(run.res, run.fs, run.player, target, E.HEAL_ELEMENT):
            return
        before = target.damage
        if before:
            target.damage = 0
            per = state.rules.damage_per_counter
            state.add_event("attack_heal", player=run.player, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key),
                            counters=before // per, amount=before, damage_before=before, total_damage=0)
        attacker = run.attacker()
        for uid in tuple(target.energy):
            E.discard_energy_from_play(
                state, target, (uid,), cause=E.DISCARD_BY_ATTACK, by_player=run.player,
                log=lambda uid=uid: state.add_event("discard_attached_energy", player=run.player, pokemon=target.card, pokemon_id=target.pokemon_id, energy=uid,
                                                    effect=str(run.key), attacker=run.player, attacker_pokemon_id=attacker.pokemon_id))


@dataclass(frozen=True)
class ChooseOpponentBench(Element):
    """相手の控えポケモンを 1 匹選ぶ（v0.83。ひかるライチュウの「サンダースコール」の「相手の控えポケモンを1匹選ぶ。その後、…選んだポケモンにも…与える」。ダメージより先に選ぶ）。
    選んだ番号を ``fs.results[name]``（``ChosenTarget``）に置き、あとの ``ChosenTargetDamage`` が使う。相手に控えがいなければ選ばない（``ChosenTarget(None)``。説明の「相手に
    控えがいないとき、控えへのダメージはなくなる」。ワザは失敗しない）。選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。控えが 1 匹でも出す）。"""

    name: str = "chosen"
    weakness_resistance: bool = False
    phase: ClassVar[Phase] = Phase.NEUTRAL
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def run(self, run: AttackRun) -> bool:
        bench = run.state.players[1 - run.player].bench
        if not bench:
            run.fs.results[self.name] = ChosenTarget(None)
            return False
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=[p.pokemon_id for p in bench], carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if choices[0] not in [p.pokemon_id for p in run.state.players[1 - run.player].bench]:
            raise RuntimeError(f"選んだポケモン {choices} が、相手の控えにいない（エンジンの不具合）")
        run.fs.results[self.name] = ChosenTarget(choices[0])


@dataclass(frozen=True)
class ChosenTargetDamage(Element):
    """先に選んだ相手の控えポケモン（``ChooseOpponentBench`` の ``chosen``）に ``base`` のダメージを与える（v0.83。「サンダースコール」の「選んだポケモンにも、「弱点・抵抗力」に
    関係なく与える」）。p.320 のダメージの (2)。計算は v0.33 のかけぬけると同じ（弱点・抵抗力なし・プラスパワーは変えない・ディフェンダーは変える）。選んだポケモンがもう相手の
    控えにいなければ何もしない（今のワザの並びでは、選んでからダメージまでのあいだに場は変わらない）。量が 0 なら与えない。［ベンチガード］は ``guarded_damages``。"""

    base: Any
    chosen: str = "chosen"
    name: str = "bench_damage"
    phase: ClassVar[Phase] = Phase.DAMAGE
    guards_bench: ClassVar[bool] = True

    def run(self, run: AttackRun) -> bool:
        target = run.fs.results.get(self.chosen)
        if target is None:
            raise RuntimeError("選んだ控えポケモンの記録がない（要素の並びの誤り。エンジンの不具合）")
        if target.pokemon_id is None or target.pokemon_id not in [p.pokemon_id for p in run.state.players[1 - run.player].bench]:
            return False
        amount = self.base.value(run, None)
        if amount <= 0:
            return False
        return guarded_damages(run, self, [(E.OPPONENT_BENCH, target.pokemon_id, amount, False)], record=True)


@dataclass(frozen=True)
class AttachFromHandToChosen(Element):
    """自分の場の「``energy_type``」ポケモンを 1 匹選ぶ。その後、自分の手札にある「``energy_type``」エネルギーカードを ``max_cards`` 枚まで選び、選んだポケモンにつける（v0.83。
    やさしいキマワリの「ひざしをかえす」）。

    - 選ぶのはワザを使ったプレイヤー。ポケモン（決定 ``SELECT_POKEMON``。選べるものは自分の場の、今有効な色が ``energy_type`` のポケモン（バトル場 → ベンチの順）。色の読み方
      （VS1）で ``energy_type`` かが変わるポケモンがいれば止める）→ カード（決定 ``ATTACH_FROM_HAND``。選べるものは手札の ``energy_type`` の基本エネルギーカード（手札の並び）。
      0〜min(``max_cards``, 枚数)。``context`` の ``"target"`` が選んだポケモン）
    - 手札に「``energy_type``」エネルギーカードがあるときに 0 枚を選べるか（「2枚まで選び」が 0 枚を含むか）は決められない（v0.31 の HC7 と同じ問いで、答えのときに止め、
      決定は待ったまま。v0.46 のせいちょうの「最大2枚」と同じ扱い）。手札にないなら、処理の対象がないので決定を出さない（p.309）
    - クリスタルビームの効果（エネルギーカードをつけることができない）を受けているポケモンは選べない（v0.59。ワザの効果でつけるのも「つける」こと）。選べるポケモンがいなければ
      何もしない
    - つけるのはワザの効果（``zones.attach_energy_from_hand``。手札からつける通常の操作（p.310。1 番に 1 枚）の回数・特殊能力でつけた枚数には数えない。v0.46 のせいちょうと同じ）。
      ログ ``attach_energy_from_hand``（``effect`` はワザ、``cards`` はつけたカード）。つけたカードごとに ``after_energy_attached``
    - 自分の場のポケモンへの効果なので、選んだポケモンの「ワザをうけない」状態・「とうめい」を評価する（``reaches``。受けないならつけない）"""

    energy_type: EnergyType
    max_cards: int
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def decides(self, kind: str) -> bool:
        return kind in (SELECT_POKEMON, ATTACH_FROM_HAND)

    def _cards(self, run: AttackRun) -> list[int]:
        rainbow_attach_question(run, run.state.players[run.player].hand, self.energy_type)  # v0.58: RB2
        return E.hand_basic_energy(run.state, run.player, self.energy_type)

    def _pokemon(self, run: AttackRun) -> list[int]:
        found = []
        for pokemon in run.state.players[run.player].in_play():
            readings = E.type_readings(run.state, pokemon)
            matches = {reading is self.energy_type for reading in readings}
            if len(matches) > 1:
                raise type_question(run.res, E.TypeReadingsDiffer([pokemon]), f"「{self.energy_type.ja}」ポケモンを選ぶワザ {run.key}")
            if True in matches and E.energy_attach_block(run.state, pokemon) is None:
                found.append(pokemon.pokemon_id)
        return found

    def run(self, run: AttackRun) -> bool:
        if not self._cards(run):
            return False
        options = self._pokemon(run)
        if not options:
            return False
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=options, carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        if decision.kind == SELECT_POKEMON:
            if choices[0] not in self._pokemon(run):
                raise RuntimeError(f"選んだポケモン {choices} が、自分の場の「{self.energy_type.ja}」ポケモンではない（エンジンの不具合）")
            cards = self._cards(run)
            run.suspend(kind=ATTACH_FROM_HAND, player=run.player, options=cards, min_choices=0, max_choices=min(self.max_cards, len(cards)), carry=True,
                        extra=(("target", choices[0]),))
            return
        if not choices:
            raise UnsupportedError(
                "UNRESOLVED_ATTACH_FROM_DISCARD_ZERO",
                f"手札に「{self.energy_type.ja}」エネルギーカードがあるときに 0 枚を選べるか（「{self.max_cards}枚まで選び、選んだポケモンにつける」が 0 枚を含むか）は決められないので"
                "扱わない（v0.31 の HC7 と同じ問い）。1 枚以上を選ぶ",
            )
        cards = self._cards(run)
        if len(set(choices)) != len(choices) or any(uid not in cards for uid in choices):
            raise RuntimeError(f"つけるカード {choices} が、手札の「{self.energy_type.ja}」エネルギーカードではない（エンジンの不具合）")
        found = state.find_pokemon(run.carried["target"])
        if found is None or found[0] != run.player:
            raise RuntimeError(f"つける先のポケモン {run.carried['target']} が、自分の場にいない（エンジンの不具合）")
        target = found[1]
        if not reaches(run.res, run.fs, run.player, target, E.ENERGY_ATTACH_ELEMENT):
            return
        ordered = tuple(uid for uid in state.players[run.player].hand if uid in choices)
        for uid in ordered:
            question = E.attack_hand_attach_question(state, run.player, target, uid)  # v0.86: 手札からつけた事実への反応（PW4・エンジンの未対応）
            if question is not None:
                raise run.res.question(question, f"手札からつけるカード {uid}・ポケモン {target.pokemon_id}")
        for uid in ordered:
            attach_energy_from_hand(state, run.player, uid, target)
        state.add_event("attach_energy_from_hand", player=run.player, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key), cards=ordered)
        for uid in ordered:
            attached_in_attack(run, run.player, target, (uid,))

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        if decision.kind == ATTACH_FROM_HAND:
            return card_id_answers(run.state, decision, range(1, decision.max_choices + 1))  # 0 枚は答えのときに止める（HC7）
        return all_answers(decision)


@dataclass(frozen=True)
class FailUnlessEqualEnergyCards(Element):
    """自分（ワザを使ったポケモン）と相手（相手の対戦ポケモン）に、同じ枚数の「エネルギーカード」がついていないとき、このワザは失敗する（v0.83。やさしいモルフォンの「シンクロ
    ウェーブ」。p.323「12」。ログ ``attack_failed`` の ``reason`` ``condition``）。数えるのはカードの枚数（無色2個エネルギー 1 枚と基本エネルギー 2 枚は同じ枚数ではない）。
    ついている間に特殊エネルギーの種類として場についているカード（［エネエネ］）も 1 枚。相手への効果ではないので「ワザをうけない」状態・「とうめい」は評価しない。"""

    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        state = run.state

        def cards(pokemon: PokemonInPlay | None) -> int:
            return 0 if pokemon is None else sum(1 for uid in pokemon.energy if state.card_def(uid).category == "energy")

        if cards(run.attacker()) != cards(run.opponent_active()):
            run.fail("condition")
        return False


@dataclass(frozen=True)
class SelfReflectShield(Element):
    """ワザを使ったポケモン自身に「リフレクトシールド」の効果（``state.ReflectShield``。はたらく番は次の相手の番）を与える（v0.83。ひかるミュウツー）。自分への効果なので「とうめい」を
    評価しない（v0.35 の ``SelfAttackLock`` と同じ）。このワザで HP 以上になっていれば与えない（p.309）。同じ効果がすでにあれば置きかえる（``replace_persistent_effect``。前の効果は
    はたらく番が過ぎていれば番の終わりに消えている。同じ番に 2 回使うことはない）。"""

    amount: int = 20
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("persistent_effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                persistent_effect=ReflectShield.kind, effect=str(run.key), reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        turn = run.state.turn_number
        effect = ReflectShield(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn + ReflectShield.turns_until_active,
                               attack_index=run.key.attack_index, amount=self.amount, attack_card=effect_attack_card_of(run, attacker))
        add_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key))
        return False


# ---------------------------------------------------------------- v0.84（docs/light-powers-evolution-v0.84.md）。入れ替えと特殊状態の守り・控えの守り・場の移動・
# おたがいのプレイヤーの進化・相手の対戦ポケモンで決まる基本となるダメージ


@dataclass(frozen=True)
class SwitchSelfThenStatusGuard(Element):
    """自分の控えポケモンを 1 匹選び、自分と入れ替える。このワザで新しく出てきたポケモンは、バトル場にいるかぎり、「どく・ねむり・マヒ・こんらん」状態にならない。自分に
    控えがいないとき、このワザは失敗する（v0.84。やさしいレディアンの「きらめきタッチ」。docs 4 章）。

    - 控えがいなければワザの失敗（説明。宣言の前に拒否しない。ログ ``attack_failed`` の ``reason`` ``no_bench``）
    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。1 匹でも出す）。入れ替えはポケモンいれかえと同じ処理（``effects._switch_active_with_bench``。ログ ``switch`` の
      ``effect``）
    - 新しく出てきたポケモンへのワザの効果なので、効果の前に「ワザをうけない」状態・「とうめい」を評価する（``reaches`` の ``status_guard``。自分のワザでも評価する。v0.9 の T8）。
      受けるなら持続する効果 ``state.StatusImmunityWhileActive``（与えたときからはたらき、バトル場をはなれると消える）。すでにある特殊状態は回復しない
    - ワザを使ったポケモンが同じワザの中で HP 以上なら、処理の対象がないので何もしない（p.309。今のワザにダメージの要素はない）"""

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.ko_prevention_conflict(attacker, run.player)
            return False
        bench = run.state.players[run.player].bench
        if not bench:
            run.fail("no_bench")
            return False
        if _leave_prevented(run, run.player, attacker, E.LEAVE_SWITCH, None):
            return False  # v0.93: 入れ替えないので、「このワザで新しく出てきたポケモン」はいない（効果を与えない。ワザの失敗ではない）
        if run.state.players[run.player].active is not attacker:
            raise RuntimeError(f"入れ替えるワザ {run.key} を使ったポケモンがバトル場にいない（エンジンの不具合）")
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=[p.pokemon_id for p in bench], carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        if len(choices) != 1 or choices[0] not in [p.pokemon_id for p in state.players[run.player].bench]:
            raise RuntimeError(f"入れ替えるポケモン {choices} が、自分の控えにいない（エンジンの不具合）")
        attacker = run.attacker()
        E._switch_active_with_bench(state, run.player, choices[0], effect=str(run.key))
        new = state.players[run.player].active
        if not reaches(run.res, run.fs, run.player, new, E.STATUS_GUARD_ELEMENT):
            return
        turn = state.turn_number
        printed = state.cards[attacker.card].card_id
        effect = StatusImmunityWhileActive(source_card=new.card, source_player=run.player, created_turn=turn, active_turn=turn, attack_index=run.key.attack_index,
                                           given_by=attacker.card, attack_card=None if run.key.card_id == printed else run.key.card_id)
        add_persistent_effect(state, run.player, new, effect, attack=str(run.key))


@dataclass(frozen=True)
class ReturnOwnBenchToDeck(Element):
    """自分の控えポケモンを 1 匹選び、そのポケモンとそのポケモンについているすべてのカードを、自分の山札にもどす。その後、その山札をよく切る。自分に控えがいないとき、
    このワザは失敗する（v0.84。やさしいゴーリキーの「やまにかえす」。docs 4 章）。

    - 控えがいなければワザの失敗（ログ ``attack_failed`` の ``reason`` ``no_bench``）
    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``）。選んだポケモンへのワザの効果なので「とうめい」を評価し（``reaches``）、受けないなら何もしない（山札も切らない）
    - もどすのは v0.36 の ``zones.return_in_play_to_deck``（重なったカード・エネルギー・トレーナーを同じ uid のまま持ち主の山札に。ダメージカウンターはなくなる）→ 持続する
      効果を消す（控えにはない）→ 山札を切る（``shuffle_in_attack``。先読みでは切らない）。きぜつではない（サイド・きぜつしたときの特殊能力はない）。場から手札・山札に
      もどるので、リサイクルエネルギー・エコロジムの「トラッシュに置かれたとき」には当たらない
    - 同じワザで HP 以上になったポケモンがいれば RD9（v0.36 と同じ問い。このワザにダメージの要素はないので、今の対応カードでは起こらない）"""

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def run(self, run: AttackRun) -> bool:
        bench = run.state.players[run.player].bench
        if not bench:
            run.fail("no_bench")
            return False
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=[p.pokemon_id for p in bench], carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        target = next((p for p in state.players[run.player].bench if len(choices) == 1 and p.pokemon_id == choices[0]), None)
        if target is None:
            raise RuntimeError(f"山札にもどすポケモン {choices} が、自分の控えにいない（エンジンの不具合）")
        from .kernel import knocked

        gone = knocked(run.res)
        if gone:
            raise run.res.question("return_in_play_to_deck_with_knockout", f"ポケモン {[pokemon.pokemon_id for _, pokemon in gone]}")
        if not reaches(run.res, run.fs, run.player, target, E.RETURN_IN_PLAY_TO_DECK_ELEMENT):
            return
        ninja_trick_leave_question(run, target)
        return_in_play_to_deck(state, run.player, target, effect=str(run.key))
        remove_persistent_effects(state, run.player, target, RETURN_IN_PLAY_TO_DECK)
        shuffle_in_attack(run, self, run.player)


# v0.84 の関数。v0.116 で effects.py に移した（わるいゴーストの「よびもどす」の決定の確かめも同じ選べるものを使う。中身は変えていない）
discard_baby_or_basic = E.discard_baby_or_basic


@dataclass(frozen=True)
class BenchBabyOrBasicFromOwnDiscard(Element):
    """自分のトラッシュから「ベイビィポケモン」または「たねポケモン」を 1 枚選び出し、ベンチに出す。自分のベンチに空きがないとき、このワザは失敗する（v0.84。やさしい
    キュウコンの「むかえび」。docs 4 章）。

    - ベンチに空きがない（``stadiums.bench_limit``。せまいジム）ならワザの失敗（ログ ``attack_failed`` の ``reason`` ``bench_full``）。空きがあり、選べるカードがなければ何もしない
      （p.309。ログ ``bench_from_discard_none``）
    - 選ぶのはワザを使ったプレイヤー（決定 ``BENCH_FROM_DISCARD``。v0.51 と同じ種類。1 枚。省略できない）。自分のトラッシュだけ（v0.51 の「よみがえらせる」の相手のトラッシュを
      持ち込まない）。ダメージカウンターはのせない
    - 出すのは v0.51 の ``zones.bench_from_discard``（同じ uid・新しい場のポケモン・場に出た番は今の番。手札を通さない）。場に出たときの特殊能力は v0.51 の
      ``effects.discard_entry_power_guard``"""

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = BENCH_FROM_DISCARD

    def run(self, run: AttackRun) -> bool:
        state = run.state
        if len(state.players[run.player].bench) >= bench_limit(state, run.player):
            run.fail("bench_full")
            return False
        if protected_discard(run, "bench_from_discard"):
            return False  # v0.119: ［アレルギーほうし］（ワザの失敗の条件はトラッシュのカードへの効果ではないので、先に見る）
        candidates = discard_baby_or_basic(state, run.player)
        if not candidates:
            attacker = run.attacker()
            state.add_event("bench_from_discard_none", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key))
            return False
        run.suspend(kind=BENCH_FROM_DISCARD, player=run.player, options=candidates)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        if len(choices) != 1 or choices[0] not in discard_baby_or_basic(state, run.player):
            raise RuntimeError(f"むかえびで選んだカード {choices} が、自分のトラッシュのたねポケモンのカードではない（エンジンの不具合）")
        card = choices[0]
        E.discard_entry_power_guard(state, card)
        pokemon = bench_from_discard(state, card)
        attacker = run.attacker()
        E.log_bench_from_discard(state, pokemon, by_player=run.player,
                                 source={"pokemon": attacker.card, "pokemon_id": attacker.pokemon_id, "effect": str(run.key)})

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, (1,))


@dataclass(frozen=True)
class BubbleJump(Element):
    """コインを投げて「おもて」なら、自分の控えポケモンを 1 匹選ぶ。その後、自分についている「エネルギーカード」を 2 枚はがし、選んだポケモンにつけ替える。つけ替えた場合、
    自分と自分についているすべてのカードを、自分の手札にもどす。(自分に控えがいないとき、このワザの効果はすべてなくなる。)（v0.84。やさしいマリルリの「バブルジャンプ」。
    docs 4 章）。ダメージの要素のあとに置く。

    - 「このワザの効果はすべてなくなる」の「効果」は、ダメージ以外の効果（説明の「ダメージ以外の効果」（こおりのはしら・ひかりのはどう）と同じ使い分け。ダメージの目安の
      ダメージは残る）。控えがいなければコインを投げない（ログ ``effect_skipped`` の ``reason`` ``no_bench``）
    - ワザを使ったポケモンが同じワザの中で HP 以上なら、処理の対象がないのでコインを投げない（p.309）
    - 「エネルギーカード」はカードの枚数（無色2個エネルギーも 1 枚）。ついているエネルギーカードが 1 枚なら、2 枚をはがせない。1 枚だけつけ替えるかが決まらないので、コインの
      前に v0.44 の FC1（``UNRESOLVED_STATED_CARDS_SHORT``）で止める。0 枚なら、つけ替えられないので手札にももどさない（処理の対象がない。コインは投げる）
    - 選ぶのはワザを使ったプレイヤー: 控え（``SELECT_POKEMON``）→ 3 枚以上ついていれば、はがす 2 枚（``MOVE_ENERGY``。ちょうど 2 枚。2 枚ならすべてで決定はない）。
      はがすカードはカードを動かすだけで、トラッシュに置かない（リサイクルエネルギー・エコロジムに当たらない）。手札からつける通常の操作・つけたときの効果に数えない
    - つける控えの「とうめい」を評価し（``reaches`` の ``energy_attach``）、受けないなら 2 枚とも持ち主のトラッシュ（v0.31 の CR-TRANSPARENCY-ENERGY-BOMB と同じ読み方）で、
      つけ替えていないので手札にもどさない
    - つけ替えたら、ワザを使ったポケモンと、重なったカード・ついているカードを手札にもどす（v0.42 の ``zones.return_in_play_to_hand``。持続する効果を消す）。きぜつではない。
      空いたバトル場は、ワザのあとの勝ち負けの判定・バトル場に出す決定でうめる。同じワザで HP 以上になったポケモンがいれば RD9（v0.44 のスターブーメランと同じ。コインの
      「おもて」のあと、決定の前）"""

    phase: ClassVar[Phase] = Phase.EFFECT
    count: ClassVar[int] = 2

    def decides(self, kind: str) -> bool:
        return kind in (SELECT_POKEMON, MOVE_ENERGY)

    def run(self, run: AttackRun) -> bool:
        state = run.state
        attacker = run.attacker()
        if not state.players[run.player].bench:
            state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            element="bubble_jump", reason="no_bench")
            return False
        if run.knocked_out(attacker):
            run.ko_prevention_conflict(attacker, run.player)
            return False
        if 0 < len(attacker.energy) < self.count:
            question = QUESTIONS["stated_cards_short"]
            raise UnsupportedError(question.code, f"{question.message}（ワザ {run.key}・ついているエネルギーカード {len(attacker.energy)} 枚。2 枚をはがす）")
        if run.flip(1).results[0] is not HEADS:
            return False
        if not attacker.energy:
            state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            element="bubble_jump", reason="no_energy")
            return False
        from .kernel import knocked

        gone = knocked(run.res)
        if gone and leave_lock(state, run.player, attacker) is None:  # v0.93: もどれない（はなれられない）なら、バトル場は空かない
            raise run.res.question("return_in_play_to_deck_with_knockout", f"ポケモン {[pokemon.pokemon_id for _, pokemon in gone]}")
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=[p.pokemon_id for p in state.players[run.player].bench], carry=True,
                    extra=(("stage", "bench"),))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        attacker = run.attacker()
        if run.carried.get("stage") == "bench":
            target = choices[0]
            if target not in [p.pokemon_id for p in state.players[run.player].bench]:
                raise RuntimeError(f"バブルジャンプで選んだポケモン {choices} が、自分の控えにいない（エンジンの不具合）")
            if len(attacker.energy) > self.count:
                run.suspend(kind=MOVE_ENERGY, player=run.player, options=tuple(attacker.energy), min_choices=self.count, max_choices=self.count, carry=True,
                            extra=(("stage", "energy"), ("target", target)))
                return
            self._move(run, attacker, target, tuple(attacker.energy))
            return
        target = run.carried["target"]
        if len(set(choices)) != self.count or not set(choices) <= set(attacker.energy):
            raise RuntimeError(f"バブルジャンプではがすカード {choices} が、ワザを使ったポケモンについているエネルギーカード 2 枚ではない（エンジンの不具合）")
        self._move(run, attacker, target, tuple(uid for uid in attacker.energy if uid in choices))

    def _move(self, run: AttackRun, attacker: PokemonInPlay, target_id: int, cards: tuple[int, ...]) -> None:
        state = run.state
        target = next(p for p in state.players[run.player].bench if p.pokemon_id == target_id)
        if E.energy_attach_block(state, target) is not None:
            raise RuntimeError(f"控えポケモン {target.pokemon_id} がクリスタルビームの効果を受けている（ベンチでは消えるはず。エンジンの不具合）")
        if not reaches(run.res, run.fs, run.player, target, E.ENERGY_ATTACH_ELEMENT):
            E.discard_energy_from_play(
                state, attacker, cards, cause=E.DISCARD_BY_ATTACK, by_player=run.player,
                log=lambda: [state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                             energy=uid, reason="evaded", to_pokemon_id=target.pokemon_id) for uid in cards])
            return
        for uid in cards:
            # デンキとばし（v0.72）と同じ、はがしたカードを控えにつけるログ（1 枚ごと）。つけたあとの処理（ほのおでかいふくなど）も同じ
            attacker.energy.remove(uid)
            target.energy.append(uid)
            state.add_event("attack_attach_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy=uid, to_pokemon_id=target.pokemon_id)
            attached_in_attack(run, run.player, target, (uid,), moved=True)
        if _leave_prevented(run, run.player, attacker, E.LEAVE_TO_HAND, None):
            return  # v0.93: つけ替えた（その部分は起こる）が、自分を手札にもどす部分は起こらない
        ninja_trick_leave_question(run, attacker)
        return_in_play_to_hand(state, run.player, attacker, effect=str(run.key))
        remove_persistent_effects(state, run.player, attacker, RETURN_IN_PLAY_TO_HAND)


@dataclass(frozen=True)
class OptionalDiscardStadium(Element):
    """のぞむなら、場にある「スタジアムカード」をトラッシュしてよい（v0.84。やさしいイノムーの「つきくずす」）。ダメージの要素のあとに置く。

    - 場にスタジアムがなければ何もしない（決定なし）。あれば、ワザを使ったプレイヤーが決める（決定 ``DISCARD_STADIUM``。選べるものは場のスタジアムのカード 1 つ。0〜1 個。
      選ばない = トラッシュしない。ログ ``stadium_discard_declined``）。トラッシュは v0.58 の ``zones.discard_stadium``（ログ ``stadium_discarded`` の ``reason`` ``attack``）
    - 場のポケモンへの効果ではないので「ワザをうけない」状態・「とうめい」は関係しない。ダメージの結果（相手が受けたか・きぜつしたか）によらない（``independent_of_pokemon``）"""

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = DISCARD_STADIUM
    independent_of_pokemon: ClassVar[bool] = True

    def run(self, run: AttackRun) -> bool:
        stadium = run.state.stadium
        if stadium is None:
            return False
        run.suspend(kind=DISCARD_STADIUM, player=run.player, options=(stadium.card,), min_choices=0, max_choices=1, carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        stadium = run.state.stadium
        if stadium is None or decision.options != (stadium.card,):
            raise RuntimeError(f"つきくずすの決定のスタジアム {decision.options} が場にない（エンジンの不具合）")
        if not choices:
            run.state.add_event("stadium_discard_declined", player=run.player, card=stadium.card, effect=str(run.key))
            return
        located = run.state.find_pokemon(run.fs.frame.source_pid)
        by_card = located[1].card if located is not None else _declared_attacker_card(run)
        discard_stadium(run.state, stadium, reason="attack", by_card=by_card, effect=str(run.key))


@dataclass(frozen=True)
class OpponentMayDraw(EachPlayerDraws):
    """相手プレイヤーは、のぞむなら、山札からカードを ``max_cards`` 枚引いて、手札に加えてよい（v0.84。やさしいトゲチックの「てんしのキッス」。ダメージの要素のあとに置く）。
    v0.83 の ``EachPlayerDraws`` の相手プレイヤーの段階だけ（決定 ``SELECT_DRAW_COUNT``。決めるのは相手。0〜min(``max_cards``, 山札の枚数)）。相手の山札が 0 枚なら決定を
    出さず、引かない（負けにならない。p.312。山札の枚数は公開の情報）。"""

    max_cards: int = 1

    def run(self, run: AttackRun) -> bool:
        return self._offer(run, 1)


def baby_evolution_cards_possible(state: GameState, owner: int, pokemon: PokemonInPlay) -> bool:
    """v0.114: ``owner`` の山札・サイド（持ち主に見えないカード）に、場のベイビィポケモン ``pokemon`` の進化先（印刷の名前）のたねポケモンカードがあるか。"""
    current = state.card_def(pokemon.card)
    if state.is_face_down(pokemon) or not current.is_baby_pokemon:
        return False
    hidden = (*state.players[owner].deck, *state.players[owner].prizes)
    return any(state.card_def(uid).is_basic_pokemon and state.card_def(uid).name_ja in current.evolves_to for uid in hidden)


def evolution_song_cards(state: GameState, owner: int, pokemon: PokemonInPlay) -> tuple[int, ...]:
    """v0.84: 「しんかのうた」で、``owner`` の山札から ``pokemon`` に今重ねられる進化カード（uid の小さい順。通常の進化と同じ ``evolution.evolution_block``（山札から重ねる効果。
    おたがいの最初の番・名前・その番に場に出した・進化した・段階・進化を止める特殊能力）。対応していないカードは入れない）。"""
    found = []
    for uid in sorted(state.players[owner].deck):
        definition = state.card_def(uid)
        if definition.category == "pokemon" and definition.is_evolution_pokemon and definition.supported \
                and evolution_block(state, pokemon, definition, from_deck=True) is None:
            found.append(uid)
    return tuple(found)


@dataclass(frozen=True)
class EachPlayerEvolvesFromDeck(EachPlayerStep):
    """おたがいのプレイヤーは、それぞれ、のぞむなら、自分の場のポケモンを 1 匹選んでもよい。選んだプレイヤーは、自分の山札から、選んだポケモンから進化する「進化カード」を
    1 枚選び出し、そのポケモンの上にのせ、進化させる。山札を見たプレイヤーは、その山札をよく切る（v0.84。やさしいプクリンの「しんかのうた」。docs 6 章）。

    - 順番はワザを使ったプレイヤー → 相手プレイヤー（v0.83 の ``EachPlayerStep``。実装上の順番。説明は順番を書かない）。決めるのはそのプレイヤー自身
    - 1 つめの決定 ``EVOLUTION_SONG_POKEMON``（選べるものは自分の場のポケモンの番号（バトル場 → ベンチ）。0〜1 匹。0 は「のぞむなら」の、選ばないこと。選ばなければ山札を
      見ない・切らない）。選べるものは公開の情報（場のポケモン）だけで決め、山札の中身でしぼらない
    - 2 つめの決定 ``SEARCH_DECK``（選べるものは山札の、選んだポケモンに今重ねられる進化カード。``evolution_song_cards``。あればちょうど 1 枚。なければ選べるもののない決定を
      出して答えを待つ（v0.84 の A3 と同じく、山札の中身で進み方を変えない））。そのあと、そのプレイヤーの山札を 1 回切る（見たので）
    - 重ねられるかは通常の進化と同じ（``evolution.evolution_block``。ワザによる進化でも、おたがいの最初の番・その番に場に出した・進化した・進化を止める特殊能力の制限を
      免除しない）。進化したあとの HP がダメージ以下になる組（H1）・場に出たときに使う特殊能力の機会が来る進化カード（v0.43 の PW4）は、選べるが選ぶと止める。どの進化
      カードでもそうなら、1 つめの決定でそのポケモンを選ぶと止める。今の番に退化したポケモン（DV2）・サカキの許可だけで重ねられる組（GV1）は、選べるカードが変わるので、
      1 つめの決定でそのポケモンを選ぶと止める
    - 重ねる前に、そのポケモンの「とうめい」を評価する（``reaches`` の ``evolve``。ワザの効果。相手のポケモンでも、自分のポケモンでも）。進化は通常の進化と同じ手順
      （``evolution.place_evolution_card``。ログ ``evolve`` の ``effect``・``source_zone``）。場のトキワシティジムの機会（``EVOLUTION_HEAL``）は、そのプレイヤーの決定として
      出し、答えのあとに山札を切って次のプレイヤーへ進む
    - 「手札から場に出して」進化させたときの特殊能力（たすけだす・おくりもの）の機会はない（山札から重ねた）"""

    decision_kind: ClassVar[str] = EVOLUTION_SONG_POKEMON

    def decides(self, kind: str) -> bool:
        return kind in (EVOLUTION_SONG_POKEMON, SEARCH_DECK, EVOLUTION_HEAL)

    def _pokemon_problem(self, run: AttackRun, owner: int, pokemon: PokemonInPlay) -> tuple[str, str] | None:
        state = run.state
        permitted = E.deck_evolution_permission_pairs(state, owner, (pokemon.pokemon_id,))
        if permitted:
            question = QUESTIONS["evolution_permission_from_deck"]
            return question.code, f"{question.message}（山札の進化カードと場のポケモン {list(permitted)}）"
        devolved = E.deck_evolution_devolved_pairs(state, owner, (pokemon.pokemon_id,))
        if devolved:
            question = QUESTIONS["evolve_after_devolution"]
            return question.code, f"{question.message}（山札の進化カードと場のポケモン {list(devolved)}）"
        if E.chain_evolution_targets(state, owner, (pokemon.pokemon_id,)):
            # v0.86: 進化させると、そのプレイヤーのほかのポケモンの［れんさしんか］の機会が来る（ワザの最中の宣言。PW4）
            question = QUESTIONS["entry_power_during_attack"]
            return question.code, f"{question.message}（PW4。［れんさしんか］の機会が来るポケモン {pokemon.pokemon_id}）"
        baby = baby_evolution_cards_possible(state, owner, pokemon) and E.deck_baby_evolution_card_in_text(E.text_era(run.key.card_id)) is None
        if baby:
            # v0.114（NB2）: 選んだベイビィポケモンから進化する、山札の進化先のたねポケモンカードを、neo の説明の「進化カード」にふくむかは決まらない（UQ-NEO-TEXT-BABY-CATEGORIES）。
            # 山札の中身で受け付けるかを変えないよう、持ち主に見えないカード（山札・サイド）に進化先のたねポケモンカードがあれば、ポケモンを選ぶと止める
            return E.NEO_EVOLUTION_CARD_BABY_CODE, f"ポケモン {pokemon.pokemon_id}（山札・サイドの進化先のたねポケモンカード）: {E.NEO_EVOLUTION_CARD_BABY_REASON}"
        cards = evolution_song_cards(state, owner, pokemon)
        blocked = [card for card in cards if card in self._blocked_cards(run, owner, pokemon, cards)]
        if cards and len(blocked) == len(cards):
            return self._card_problem(run, owner, pokemon, blocked[0])
        return None

    def _blocked_cards(self, run: AttackRun, owner: int, pokemon: PokemonInPlay, cards) -> tuple[int, ...]:
        return tuple(card for card in cards if self._card_problem(run, owner, pokemon, card) is not None)

    def _card_problem(self, run: AttackRun, owner: int, pokemon: PokemonInPlay, card: int) -> tuple[str, str] | None:
        state = run.state
        if pokemon.damage >= E.evolution_hp(state, pokemon, card):
            return "UNRESOLVED_EVOLUTION_HP", E.EVOLUTION_HP_REASON
        if E.applicable_entry_power(state, card, from_hand=False) is not None:
            question = QUESTIONS["entry_power_during_attack"]
            return question.code, f"{question.message}（PW4。山札の進化カード {card}）"
        return None

    def options(self, run: AttackRun, player: int) -> tuple[int, ...]:
        return tuple(p.pokemon_id for p in run.state.players[player].in_play())

    def bounds(self, run: AttackRun, player: int, options: tuple[int, ...]) -> tuple[int, int]:
        return 0, 1

    def _offer(self, run: AttackRun, stage: int) -> bool:
        for current in range(stage, 2):
            player = self.chooser(run, current)
            options = self.options(run, player)
            problems = [(pid, self._pokemon_problem(run, player, run.state.find_pokemon(pid)[1])) for pid in options]
            unresolved = tuple(pid for pid, problem in problems if problem is not None)
            extra: tuple = (("stage", current),)
            if unresolved:
                # 選ぶと止めるポケモンと、ポケモンごとの止める理由（v0.49 の ``unresolved_detail``）
                extra += (("unresolved_choices", unresolved), ("unresolved_detail", tuple((pid, *problem) for pid, problem in problems if problem is not None)))
            run.suspend(kind=EVOLUTION_SONG_POKEMON, player=player, options=options, min_choices=0, max_choices=1, carry=True, extra=extra)
            return True
        return False

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        stage = run.carried["stage"]
        player = self.chooser(run, stage)
        if decision.player != player:
            raise RuntimeError(f"しんかのうたの決定 {decision.kind} をするのが、段階 {stage} のプレイヤー {player} ではない（エンジンの不具合）")
        if decision.kind == EVOLUTION_HEAL:
            found = state.find_pokemon(decision.context_value("heal_pokemon"))
            if found is None:
                raise RuntimeError("トキワシティジムの決定のポケモンが場にいない（エンジンの不具合）")
            E.apply_evolution_heal(state, found[0], found[1], decision.context_value("heal_stadium"), bool(choices))
            shuffle_in_attack(run, self, player)
            self._offer(run, stage + 1)
            return
        if decision.kind == EVOLUTION_SONG_POKEMON:
            if not choices:
                state.add_event("each_player_declined", player=player, effect=str(run.key), attacker=run.player, reason="declined")
                self._offer(run, stage + 1)
                return
            found = state.find_pokemon(choices[0])
            if found is None or found[0] != player:
                raise RuntimeError(f"しんかのうたで選んだポケモン {choices} が、プレイヤー {player} の場にいない（エンジンの不具合）")
            problem = self._pokemon_problem(run, player, found[1])
            if problem is not None:
                raise UnsupportedError(*problem)
            cards = evolution_song_cards(state, player, found[1])
            blocked = self._blocked_cards(run, player, found[1], cards)
            extra: tuple = (("stage", stage), ("target", choices[0]))
            if blocked:
                extra += (("unresolved_choices", blocked),
                          ("unresolved_detail", tuple((card, *self._card_problem(run, player, found[1], card)) for card in blocked)))
            run.suspend(kind=SEARCH_DECK, player=player, options=cards, min_choices=1 if cards else 0, max_choices=1 if cards else 0, carry=True,
                        extra=extra)
            return
        target = run.carried["target"]
        found = state.find_pokemon(target)
        if found is None or found[0] != player:
            raise RuntimeError(f"しんかのうたで選んだポケモン {target} が、プレイヤー {player} の場にいない（エンジンの不具合）")
        pokemon = found[1]
        cards = evolution_song_cards(state, player, pokemon)
        if not choices:
            if cards:
                raise RuntimeError(f"しんかのうたで重ねるカードを選ばなかった（選べるカード {cards}。エンジンの不具合）")
            state.add_event("evolve_from_deck_none", player=player, pokemon_id=target, effect=str(run.key))
            shuffle_in_attack(run, self, player)
            self._offer(run, stage + 1)
            return
        card = choices[0]
        problem = self._card_problem(run, player, pokemon, card) if card in cards else None
        if card not in cards:
            raise RuntimeError(f"しんかのうたで選んだカード {choices} が、重ねられる進化カードではない（エンジンの不具合）")
        if problem is not None:
            raise UnsupportedError(*problem)
        if reaches(run.res, run.fs, player, pokemon, E.EVOLVE_ELEMENT):
            before_name = E.form_def(state, pokemon).name_ja
            place_evolution_card(state, player, pokemon, card, effect=str(run.key))
            terms = E.evolution_heal_terms(state, pokemon, before_name)
            if terms is not None:
                stadium, _, one = terms
                heal = (("stage", stage), ("heal_stadium", stadium.card), ("heal_pokemon", pokemon.pokemon_id))
                if one:
                    heal += _unresolved_extra((pokemon.pokemon_id,), E.VIRIDIAN_GYM_ONE_COUNTER_CODE, E.VIRIDIAN_GYM_ONE_COUNTER_REASON)
                run.suspend(kind=EVOLUTION_HEAL, player=player, options=(pokemon.pokemon_id,), min_choices=0, max_choices=1, carry=True, extra=heal)
                return
        shuffle_in_attack(run, self, player)
        self._offer(run, stage + 1)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ()))
        if decision.kind == SEARCH_DECK:
            return [answer for answer in card_id_answers(run.state, decision, (decision.max_choices,)) if not blocked & set(answer)]
        return [answer for answer in all_answers(decision) if not blocked & set(answer)]


@dataclass(frozen=True)
class PrintedByDefenderStage:
    """相手の対戦ポケモン（今の姿）が「ベイビィポケモン」なら ``baby``、「たねポケモン」なら ``basic``、それ以外ならダメージの目安の数字（v0.84。やさしいウインディの
    「やさしいほのお」。p.321 の 1 段階。「このワザのダメージは「10」になり」）。段階は今の姿の定義（``effects.form_def``。［へんしん］のメタモンは写した姿、「ばける」は
    のせたカード）。なにかの化石・ピッピ人形（場での役割）は「たねポケモン」。"""

    baby: int
    basic: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        # v0.114: 場の分類（``effects.field_stage``）。ベイビィから進化したたねポケモンは「進化ポケモン」（GR-2000-P315-EVOLVED-BABY）なので目安の数字。［へんしん］でベイビィの姿の
        # メタモンは、ベイビィとたねのどちらかで量が変わるので BX1
        defender = run.opponent_active()
        stage = E.field_stage(run.state, defender)
        if stage == E.FIELD_BABY:
            problem = E.transform_baby_question(run.state, defender)
            if problem is not None:
                raise problem
            return self.baby
        if stage == E.FIELD_BASIC:
            return self.basic
        return run.attack.damage


@dataclass(frozen=True)
class AmountIfDefenderDamaged:
    """相手の対戦ポケモンにダメージカウンターがのっているとき ``amount``、のっていなければダメージの目安の数字（v0.84。やさしいゴーリキーの「やさしいキック」の「このワザの
    ダメージは「20」になる」。p.321 の 1 段階。見るのはのっているかどうかだけ（v0.41 の ``PrintedMinusIfDefenderDamaged`` と同じ見方））。"""

    amount: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return self.amount if run.opponent_active().damage > 0 else run.attack.damage


def defender_is_dark(run: AttackRun) -> bool:
    """v0.84: 相手の対戦ポケモンが「わるい」ポケモン（今の姿の名前が「わるい」ではじまる。日本語のカードの名前）または「悪」ポケモン（今有効なタイプ。［へんしょく］の読み方で
    答えが変わるなら VS1）。v0.78 の悪エネルギーの「「悪」または「わるい」ポケモン」と同じ判定。"""
    defender = run.opponent_active()
    if E.form_def(run.state, defender).name_ja.startswith("わるい"):
        return True
    try:
        return E.same_for_type_readings(run.state, (defender,), lambda views: views[0].pokemon_type is EnergyType.DARKNESS)
    except E.TypeReadingsDiffer as differ:
        raise type_question(run.res, differ, f"ワザ {run.key} の相手が「悪」ポケモンか") from None


@dataclass(frozen=True)
class CoinSetIfDefenderDark:
    """相手が「わるい」ポケモンまたは「悪」ポケモンなら、コインを投げる。「おもて」なら ``amount``（v0.84。やさしいカイリキーの「せいけんづき」の「このワザのダメージは「100」に
    なる」。p.321 の 1 段階）。そうでなければ（コインを投げない・「うら」）ダメージの目安の数字。コインはダメージの量だけを決めるので、「ダメージを受けない」相手には v0.4b の
    問い（``Damage.run``。``coin_count`` が 1 のとき）。"""

    amount: int

    def coin_count(self, run: AttackRun) -> int:
        return 1 if defender_is_dark(run) else 0

    @property
    def local_coins(self) -> int:
        return 1

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return self.amount if flips is not None and flips.results[0] is HEADS else run.attack.damage



# ---------------------------------------------------------------- v0.85（docs/entry-powers-energy-lifecycle-v0.85.md 6 章）


@dataclass(frozen=True)
class CoinChosenSideHeal(Element):
    """コインを投げ、「おもて」なら自分の場から、「うら」なら相手の場から、ダメージカウンターののっているポケモンを 1 匹選び、ダメージカウンターを ``counters`` 個
    （のっている数まで）とりのぞく（v0.85。ベイリーフの「あまいかおり」）。

    - コインは 1 枚（この要素の中。ワザ全体のコインではない）。選ぶのはワザを使ったプレイヤー（どちらの場でも。決定 ``SELECT_POKEMON``。1 匹でも出す）。その場に
      ダメージカウンターののっているポケモンがいなければ、何もしない（p.309）
    - とりのぞく前に「ワザをうけない」状態・「とうめい」を評価する（``reaches`` の ``heal``）。ログ ``attack_heal``（``attacker`` つき）
    """

    counters: int
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.HEAL_ELEMENT
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def run(self, run: AttackRun) -> bool:
        side = run.player if run.flip(1).results[0] is HEADS else 1 - run.player
        per = run.state.rules.damage_per_counter
        options = [p.pokemon_id for p in run.state.players[side].in_play() if p.damage >= per and not run.knocked_out(p)]
        if not options:
            return False
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=options)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        found = state.find_pokemon(choices[0]) if len(choices) == 1 else None
        if found is None or choices[0] not in decision.options:
            raise RuntimeError(f"「あまいかおり」で選んだポケモン {choices} が、選べるポケモンではない（エンジンの不具合）")
        owner, target = found
        if not reaches(run.res, run.fs, owner, target, E.HEAL_ELEMENT):
            return
        per = state.rules.damage_per_counter
        before = target.damage
        removed = min(self.counters, before // per)
        target.damage = before - removed * per
        state.add_event("attack_heal", player=owner, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key), counters=removed,
                        amount=removed * per, damage_before=before, total_damage=target.damage, attacker=run.player)


@dataclass(frozen=True)
class PlusHeadsPerOwnCounters:
    """ダメージの目安の数字 + 自分（ワザを使ったポケモン）にのっているダメージカウンターの数だけコインを投げた「おもて」の数 × ``per``（v0.85。オーダイルの「いかりのキバ」。
    p.321 の 1 段階）。0 個ならコインを投げない。結果は「おもて」の数だけを使う（``by_heads``。先読みは「おもて」の数でまとめる）。"""

    per: int
    by_heads: ClassVar[bool] = True

    def coin_count(self, run: AttackRun) -> int:
        return run.attacker().damage // run.state.rules.damage_per_counter

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + (0 if flips is None else flips.heads) * self.per


def discard_type_energy_cards(run: AttackRun, energy_type: EnergyType) -> list[int]:
    """v0.85: ワザを使ったプレイヤーのトラッシュの「``energy_type``」の基本エネルギーカード（トラッシュの並び）。トラッシュのレインボーエネルギーを数えるかは決まらない（RB2 と
    同じ問い）ので、あれば止める。"""
    discard = run.state.players[run.player].discard
    rainbow_attach_question(run, discard, energy_type)
    return [uid for uid in discard if run.state.card_def(uid).is_basic_energy and run.state.card_def(uid).provides is energy_type]


@dataclass(frozen=True)
class PlusDiscardTypeCards:
    """ダメージの目安の数字 + ワザを使ったプレイヤーのトラッシュの「``energy_type``」エネルギーカードの枚数 × ``per``（v0.85。オーダイルの「ぎゃくりゅう」。p.321 の 1 段階）。"""

    energy_type: EnergyType
    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + len(discard_type_energy_cards(run, self.energy_type)) * self.per


@dataclass(frozen=True)
class ReturnDiscardTypeToDeck(Element):
    """ワザを使ったプレイヤーのトラッシュの「``energy_type``」エネルギーカードを、すべて同じ uid のまま山札（一番下。そのあと切るので結果は変わらない。v0.24 の PT7 と同じ実装上の
    仮定）にもどし、その山札を切る（v0.85。オーダイルの「ぎゃくりゅう」）。0 枚でも切る（実装上の読み方）。ログ ``attack_discard_to_deck``（公開）・``shuffle``。トラッシュから
    山札にもどす効果なので、ポケモンタワーでは消えない。"""

    energy_type: EnergyType
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        # v0.119: ［アレルギーほうし］なら、もどさない（0 枚のときと同じに、山札は切る。ダメージの目安の枚数を数えることは効果ではないので変わらない）
        cards = () if protected_discard(run, "discard_to_deck") else tuple(discard_type_energy_cards(run, self.energy_type))
        p = state.players[run.player]
        for uid in cards:
            p.discard.remove(uid)
        p.deck.extend(cards)
        attacker = run.attacker()
        state.add_event("attack_discard_to_deck", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), cards=cards)
        shuffle_in_attack(run, self, run.player)
        return False


@dataclass(frozen=True)
class AttachFromDeckUpToNamedCount(Element):
    """おたがいの場にいる「``name``」の数以下の「``energy_type``」エネルギーカードを自分の山札から選び出し、自分につける。その後、山札をよく切る（v0.85。メリープの
    「せいでんき」。``effects.AttachFromDeckUpToNamedCount``）。

    - 数は、おたがいの場のポケモンのうち、今の姿の名前が ``name`` のもの（うらのカードは数えない）。最大の枚数はその数（選べるものの数に合わせて変えない）。0 枚も選べる
    - 選べるカードがなくても、数が 1 以上なら決定を出して答えを待つ（山札の中身で進み方を変えない）。数が 0 なら決定を出さない（場の公開の情報）
    - ワザを使ったポケモンがクリスタルビームの効果を受けていれば、つけない（山札は切る）。そのあと、どの場合も山札を 1 回切る
    """

    energy_type: EnergyType
    name: str
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = ATTACH_FROM_DECK

    def count(self, run: AttackRun) -> int:
        return sum(1 for side in run.state.players for p in side.in_play()
                   if not run.state.is_face_down(p) and E.form_def(run.state, p).name_ja == self.name)

    def candidates(self, run: AttackRun) -> list[int]:
        rainbow_attach_question(run, run.state.players[run.player].deck, self.energy_type)  # v0.58: RB2
        return E.deck_energy_candidates(run.state, run.player, self.energy_type)

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            raise RuntimeError(f"ワザ {run.key} を使ったポケモンが、山札からエネルギーをつける前に HP 以上（このワザにダメージの要素はない。エンジンの不具合）")
        count = self.count(run)
        if E.energy_attach_block(run.state, attacker) is not None or count == 0:
            reason = "attach_prevented" if count else "no_count"
            run.state.add_event("attach_energy_from_deck_none", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                energy_type=self.energy_type.value, reason=reason)
            shuffle_in_attack(run, self, run.player)
            return False
        run.suspend(kind=ATTACH_FROM_DECK, player=run.player, options=self.candidates(run), min_choices=0, max_choices=count)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        attacker = run.attacker()
        candidates = self.candidates(run)
        if len(set(choices)) != len(choices) or any(card not in candidates for card in choices) or len(choices) > self.count(run):
            raise RuntimeError(f"つけるカード {choices} が、山札の「{self.energy_type.ja}」エネルギーカードではない（エンジンの不具合）")
        cards = tuple(uid for uid in candidates if uid in choices)
        if not cards:
            state.add_event("attach_energy_from_deck_none", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy_type=self.energy_type.value, reason="declined")
        for card in cards:
            attach_from_deck(state, run.player, card, attacker)
            state.add_event("attach_energy_from_deck", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), card=card)
        for card in cards:
            attached_in_attack(run, run.player, attacker, (card,))
        shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, range(min(decision.max_choices, len(decision.options)) + 1))


BUILDERS: dict[type, Any] = {
    E.DamageOnly: lambda e: (Damage(OPP, Printed()),),
    E.SimplifiedSongDamage: lambda e: (Damage(OPP, Printed()),),  # v0.68: ハモる（簡略化した仕様。すぐに 30）
    E.CoinFlipDamage: lambda e: (Damage(OPP, HeadsTimes(e.coins, e.damage_per_heads)),),
    E.CoinsUntilTailsDamage: lambda e: (Damage(OPP, HeadsUntilTails(e.per)),),  # v0.64
    E.CoinHeadsDamagePerOwnCounter: lambda e: (Damage(OPP, HeadsOwnCounters(e.damage_per_counter)),),
    E.SelfDamageInsteadOnTails: lambda e: (
        Coin("coin"), Damage(OPP, Printed(), gate=("coin", HEADS)), Damage(SELF, Fixed(e.self_damage), name="self_damage", gate=("coin", TAILS)),
    ),
    E.SelfDamageOnTails: lambda e: (Damage(OPP, Printed()), Damage(SELF, Fixed(e.self_damage), name="self_damage", local_gate=TAILS)),
    E.PoisonOnHeads: lambda e: (Damage(OPP, Printed()), Status(POISON, local_coin=HEADS)),
    E.PoisonOpponent: lambda e: (Damage(OPP, Printed()), Status(POISON)),
    E.SleepOpponent: lambda e: (Damage(OPP, Printed()), Status(SLEEP)),
    E.ParalyzeOnHeads: lambda e: (Damage(OPP, Printed()), Status(PARALYSIS, local_coin=HEADS, reparalysis_check=True)),
    E.CoinBonusDamageAndParalyze: lambda e: (
        ReparalysisGuard(), Coin("coin"), Damage(OPP, PrintedPlusBonus("coin", e.bonus)), Status(PARALYSIS, gate=("coin", HEADS)),
    ),
    E.PutToSleep: lambda e: (Status(SLEEP),),
    E.PoisonWithoutDamage: lambda e: (Status(POISON),),
    E.ConfuseOnHeads: lambda e: (Damage(OPP, Printed()), Status(CONFUSION, local_coin=HEADS)),
    E.PreventDamageOnHeads: lambda e: (SelfPreventDamage(),),
    E.DamageAndRetaliation: lambda e: (Damage(OPP, Printed()), SelfRetaliation(e.retaliation)),
    E.ReturnReceivedDamage: lambda e: (SelfRetaliation(None),),
    E.DamageAndForceSwitch: lambda e: (Damage(OPP, Printed()), ForceSwitch()),
    E.DamageAndDrain: lambda e: (Damage(OPP, Printed()), Drain("damage")),
    E.DamageAndRemoveCounters: lambda e: (Damage(OPP, Printed()), Drain("damage", e.counters)),
    E.ExtraEnergyDamage: lambda e: (Damage(OPP, ExtraEnergy(e.energy_type, e.per_energy, e.max_extra)),),
    E.DiscardEnergyAndRemoveAllCounters: lambda e: (
        DiscardOwnEnergy(e.energy_type, when_lacking=LACKING_NONE), HealAllCounters(requires="discard"),
    ),
    E.RecoverEnergyAndSelfDamage: lambda e: (RecoverEnergy(e.max_cards), Damage(SELF, Fixed(e.self_damage), name="self_damage")),
    E.DamageReducedByOwnCounters: lambda e: (Damage(OPP, PrintedMinusOwnCounters(e.reduction_per_counter)),),
    E.DamageAndSelfDamage: lambda e: (Damage(OPP, Printed()), Damage(SELF, Fixed(e.self_damage), name="self_damage")),
    # v0.17a: 既存の要素の新しい並び（サカキのニャースの「ねこノミ」。docs/card-implementation-v0.17a.md）
    E.ConfuseOnHeadsWithoutDamage: lambda e: (Status(CONFUSION, local_coin=HEADS),),
    # v0.17b: 自分への特殊状態（R団のカビゴンの「たおれこむ」。docs/rocket-snorlax-v0.17b.md）
    E.DamageAndSelfSleep: lambda e: (Damage(OPP, Printed()), Status(SLEEP, target=SELF, after_damage="damage")),
    E.DamageThenSelfSleepThenSleepOpponentOnHeads: lambda e: (Damage(OPP, Printed()), Status(SLEEP, target=SELF, after_damage="damage"),
                                                               Status(SLEEP, local_coin=HEADS)),
    # v0.27: 次の自分の番にワザのダメージを変える持続する効果（ストライクの「つるぎのまい」。docs/scyther-v0.27.md）
    E.SetNextTurnAttackDamage: lambda e: (SelfNextTurnAttackDamage(e.target_attack_index, e.damage),),
    # v0.30: 自分のエネルギーカードを選んで 1 枚トラッシュしてから、相手にダメージ（ひのこ・かえんほうしゃ。RUL-ENERGY-DISCARD-ATTACKS。
    # docs/discard-energy-attacks-v0.30.md）。トラッシュの要素はじこさいせいと共通
    E.DiscardEnergyThenDamage: lambda e: (
        DiscardOwnEnergy(e.energy_type, when_lacking=LACKING_ZERO if e.when_lacking == "zero" else LACKING_NONE),
        Damage(OPP, Printed(), requires="discard"),
    ),
    # v0.31: 保留していた 22 枚と、進化元として加えた 7 枚のワザ（docs/held-cards-v0.31.md）。トラッシュできない場合（``when_lacking``）は、相手のワザを
    # 自分のワザとして使うときだけ起こる（ワザに必要なエネルギーから、ふつうは起こらない）
    E.SwitchOpponentActive: lambda e: (ForceSwitch(chooser="attacker"),),
    E.DiscardEnergyBeforeDamage: lambda e: (
        DiscardOwnEnergy(e.energy_type, count=e.count, when_lacking=e.when_lacking, timing=e.timing), Damage(OPP, Printed(), requires="discard"),
    ),
    # v0.71: プロモのリザードンの「ほのおのうず」（エネルギーカードを count 枚。トラッシュはワザの効果。足りなければトラッシュせず、ダメージは 0）
    E.DiscardEnergyCardsThenDamageZeroIfLacking: lambda e: (
        DiscardOwnEnergy(None, count=e.count, when_lacking=LACKING_ZERO, timing=TIMING_EFFECT), Damage(OPP, Printed(), requires="discard"),
    ),
    E.SleepOnHeadsWithoutDamage: lambda e: (Status(SLEEP, local_coin=HEADS),),
    E.DiscardEnergyThenSelfEffect: lambda e: (
        DiscardOwnEnergy(e.energy_type, when_lacking=LACKING_CONDITION, timing=TIMING_UNRESOLVED), SelfPersistent(e.effect_kind, requires="discard"),
    ),
    E.DamagePlusDefenderEnergy: lambda e: (Damage(OPP, PlusDefenderEnergy(e.per)),),
    E.DamagePlusOwnCounters: lambda e: (Damage(OPP, PlusOwnCounters(e.per)),),
    E.CopyOpponentAttackEffect: lambda e: (CopyOpponentAttack(e.clause),),
    # v0.120（docs/fossil-basic-virtual-attacks-v0.120.md 5 章）: ワザを選んで自分のワザとして使う（コインのあとに選ぶ・範囲・必要なエネルギー・条件）
    E.CopyAttackFromSource: lambda e: ((Coin("coin"),) if e.coin else ()) + (
        CopyChosenAttack(e.clause, gate=("coin", HEADS) if e.coin else None, source=e.source, cost=e.cost,
                         condition_code=E.PRE_EVOLUTION_CONDITION_CODE if e.source == E.COPY_FROM_PRE_EVOLUTION else "UNRESOLVED_COPIED_ATTACK"),),
    E.ReduceDamageNextTurn: lambda e: (SelfPersistent(DamageReduction.kind, amount=e.amount),),
    E.DiscardFireThenMillOpponent: lambda e: (
        DiscardOwnEnergy(EnergyType.FIRE, any_number=True, deck_limit=True, when_lacking=LACKING_CONDITION, timing=TIMING_UNRESOLVED),
        MillOpponentDeck(),
    ),
    E.FailOnTailsDamage: lambda e: (FailOnTails(count=e.coins), Damage(OPP, Printed())),
    E.HealSelfOnHeadsIfDamaged: lambda e: (HealSelfOnHeads(e.counters),),
    E.DiscardEnergyThenRecoverTrainer: lambda e: (
        DiscardOwnEnergy(e.energy_type, when_lacking=LACKING_CANNOT_USE, timing=TIMING_UNRESOLVED), RecoverTrainer(requires="discard"),
    ),
    E.DamageThenOptionalBenchDamage: lambda e: (Damage(OPP, Printed()), OptionalDiscardBenchDamage(e.energy_type, e.bench_damage)),
    E.FailOnTailsDiscardThenDamage: lambda e: (
        FailOnTails(), DiscardOwnEnergy(e.energy_type, when_lacking=LACKING_ZERO), Damage(OPP, Printed(), requires="discard"),
    ),
    E.CoinBonusDiscardThenDamage: lambda e: (
        Coin("coin"), DiscardOwnEnergy(e.energy_type, gate=("coin", HEADS), when_lacking=LACKING_ZERO),
        Damage(OPP, PrintedPlusBonus("coin", e.bonus), requires="discard"),
    ),
    E.CoinsPerEnergyDamageThenDiscard: lambda e: (
        Coin("coin", per_attached=e.energy_type), Damage(OPP, HeadsOfCoin("coin", e.per)),
        DiscardOwnEnergy(e.energy_type, heads_of="coin", copy_need=0),
    ),
    E.DiscardEnergyThenDraw: lambda e: (DiscardOwnEnergy(None), Draw(e.draw, requires="discard")),
    E.DamageThenMoveEnergyToBench: lambda e: (Damage(OPP, Printed()), MoveOwnEnergyToBench()),
    E.DamageThenDiscardAllOnTails: lambda e: (Damage(OPP, Printed()), DiscardOwnEnergy(e.energy_type, count=None, local_coin=TAILS)),
    E.CoinDiscardOpponentEnergyEach: lambda e: (DiscardOpponentEnergy(each_bench=True, local_coin=HEADS),),
    E.AttachDiscardEnergyToSelf: lambda e: (AttachFromDiscard(e.energy_type, e.max_cards),),
    E.DiscardAllThenCoinDamage: lambda e: (DiscardOwnEnergy(e.energy_type, count=None), Damage(OPP, HeadsOfDiscarded("discard", e.per))),
    E.DamageThenDiscardEachEnergy: lambda e: (Damage(OPP, Printed()), DiscardOwnEnergy(None), DiscardOpponentEnergy()),
    E.CoinsDiscardThenSpreadDamage: lambda e: (
        Coin("coin", count=e.coins), DiscardOwnEnergy(e.energy_type, heads_of="coin", when_lacking=LACKING_FAIL, copy_need=e.coins),
        Damage(OPP, HeadsOfCoin("coin", e.per), weakness_resistance=False), BenchDamage(HeadsOfCoin("coin", e.per)),
    ),
    E.CoinBonusDamage: lambda e: (Damage(OPP, HeadsBonus(e.bonus)),),
    E.MillSelfThenDamage: lambda e: (MillOwnDeck(e.count), Damage(OPP, PerMilledEnergy("mill", e.energy_type, e.per))),
    E.CoinBonusDamageThenDiscardAll: lambda e: (
        Coin("coin"), Damage(OPP, PrintedPlusBonus("coin", e.bonus)), DiscardOwnEnergy(e.energy_type, count=None, gate=("coin", HEADS)),
    ),
    E.DamageThenParalyzeOrSelfDamage: lambda e: (
        Damage(OPP, Printed()), Damage(SELF, Fixed(e.self_damage), name="self_damage", local_gate=TAILS, coin_name="coin"),
        Status(PARALYSIS, gate=("coin", HEADS), reparalysis_check=True),
    ),
    E.DrawCardsAttack: lambda e: (Draw(e.count),),
    E.ExtraEnergyDamageMixed: lambda e: (Damage(OPP, ExtraEnergyMixed(e.energy_type, e.per_energy, e.max_extra)),),
    # v0.120（docs/fossil-basic-virtual-attacks-v0.120.md 7 章）
    E.CoinBonusPerOwnBenchNamed: lambda e: (Damage(OPP, HeadsPlusPokemonCount(e.per, SCOPE_OWN_BENCH, e.names)),),
    E.EvolveChosenNamedFromDeck: lambda e: (EvolveChosenFromDeck(e.names),),
    E.CoinsDiscardOpponentEnergyElseFail: lambda e: (FailOnAllTails("coin", e.coins), Damage(OPP, Printed()), DiscardOpponentEnergyByHeads(heads_of="coin")),
    E.ThreeCoinPsychicPower: lambda e: (
        Coin("coin", count=3), Damage(OPP, Fixed(20), gate=("coin", 2)), Draw(1, gate=("coin", 1)), CopyOpponentAttack(gate=("coin", 3)),
    ),
    E.CannotAttackOnHeads: lambda e: (OpponentCannotAttack(HEADS),),
    E.DamageAndBenchTypeDamage: lambda e: (Damage(OPP, Printed()), BenchDamage(Fixed(e.bench_damage), pokemon_type=e.pokemon_type)),
    # v0.32（docs/bench-search-counter-drain-v0.32.md）
    E.PutBasicFromDeckOntoBench: lambda e: (BenchFromDeck(e.names),),
    E.DamageTimesOwnCounters: lambda e: (Damage(OPP, OwnCountersTimes(e.per)),),
    E.DamagePlusDefenderCounters: lambda e: (Damage(OPP, PlusDefenderCounters(e.per, e.scope_ambiguous)),),
    E.DamageAndFullDrain: lambda e: (Damage(OPP, Printed()), Drain("damage", full=True)),
    # v0.33（docs/cd4-opponent-energy-coins-v0.33.md）
    E.DamageThenDiscardOpponentEnergy: lambda e: (Damage(OPP, Printed()), DiscardOpponentEnergy(local_coin=HEADS if e.on_heads else None)),
    E.NoDamageOnTails: lambda e: (Damage(OPP, Printed(), local_gate=HEADS),),
    E.DamageAndParalyzeOnHeadsElseFail: lambda e: (
        ReparalysisGuard(), FailOnTails(), Damage(OPP, Printed()), Status(PARALYSIS),
    ),
    E.DamageAndOwnBenchDamage: lambda e: (
        Damage(OPP, Printed()), BenchDamage(Fixed(e.bench_damage), own=True, weakness_resistance=False if e.weakness_resistance_stated else None),
    ),
    E.DamageThenCoinBenchDamage: lambda e: (Damage(OPP, Printed()), ChosenBenchDamage(Fixed(e.bench_damage))),
    # v0.34（docs/barrier-resume-coin-bonus-v0.34.md）
    E.CoinBonusOrSelfDamage: lambda e: (
        Coin("coin"), Damage(OPP, PrintedPlusBonus("coin", e.bonus)), Damage(SELF, Fixed(e.self_damage), name="self_damage", gate=("coin", TAILS)),
    ),
    E.DamageThenSelfBarrierOnHeads: lambda e: (Damage(OPP, Printed()), SelfPersistent(AttackBarrier.kind, local_coin=HEADS)),
    E.DamagePlusOwnCountersThenSelfConfuseOnTails: lambda e: (
        Damage(OPP, PlusOwnCounters(e.per)), Status(CONFUSION, local_coin=TAILS, target=SELF),
    ),
    E.DamageThenCoinOwnBenchDamage: lambda e: (Damage(OPP, Printed()), ChosenBenchDamage(Fixed(e.bench_damage), local_coin=TAILS, own=True)),
    E.DamageThenPoisonOrConfuse: lambda e: (Damage(OPP, Printed()), Status(POISON, local_coin=HEADS, otherwise=CONFUSION)),
    E.DamageAndSpecialPoison: lambda e: (Damage(OPP, Printed()), Status(POISON, poison_damage=e.poison_damage)),
    E.SwitchSelfWithBench: lambda e: (SelfSwitch(),),
    E.CoinsPerAttachedEnergyDamage: lambda e: (Damage(OPP, HeadsTimesAttachedEnergy(e.per)),),
    E.ReduceDamageToSelf: lambda e: (OpponentReducedDamage(e.amount),),
    E.PutTypeBasicFromDeckOntoBench: lambda e: (BenchFromDeck((), pokemon_type=e.pokemon_type),),
    # v0.35（docs/coin-groups-damage-order-v0.35.md）
    E.MultiplyNextTurnAttackDamage: lambda e: (
        SelfNextTurnAttackDamage(e.target_attack_index, e.factor, operation=NEXT_TURN_MULTIPLY, includes_self_damage=e.includes_self_damage),
    ),
    E.DamageThenLockSelfOnTails: lambda e: (Damage(OPP, Printed()), SelfAttackLock(TAILS)),
    E.LockOpponentAttack: lambda e: (OpponentAttackLock(),),
    E.CoinsPerAttachedTypeBonusDamage: lambda e: (Damage(OPP, PlusHeadsPerAttachedType(e.energy_type, e.per)),),
    E.CoinsHeadsDamageTailsSelfDamage: lambda e: (
        Coin("coin", count=e.coins), Damage(OPP, HeadsOfCoin("coin", e.per)), Damage(SELF, TailsOfCoin("coin", e.self_per), name="self_damage"),
    ),
    # v0.36（docs/sand-attack-retreat-lock-v0.36.md）
    E.DamageThenAttackCoinCheck: lambda e: (Damage(OPP, Printed()), OpponentAttackCheck(e.single_use)),
    E.DamageThenRetreatLock: lambda e: (Damage(OPP, Printed()), OpponentRetreatLock()),
    E.DamageThenReturnSelfToDeckOnHeads: lambda e: (Damage(OPP, Printed()), ReturnSelfToDeck(HEADS, after_damage="damage")),
    # v0.37（docs/fifteen-reused-effects-v0.37.md）。どれも既存の要素の組み合わせ
    E.PoisonOnHeadsWithoutDamage: lambda e: (Status(POISON, local_coin=HEADS),),
    E.ParalyzeOnHeadsWithoutDamage: lambda e: (Status(PARALYSIS, local_coin=HEADS, reparalysis_check=True),),
    E.DamageThenDrawOnHeads: lambda e: (Damage(OPP, Printed()), Coin("coin"), Draw(e.count, gate=("coin", HEADS))),
    E.DrawOnHeads: lambda e: (Coin("coin"), Draw(e.count, gate=("coin", HEADS))),
    E.SelfBarrierOnHeads: lambda e: (SelfPersistent(AttackBarrier.kind, local_coin=HEADS),),
    E.DamageThenReduceDamageToSelf: lambda e: (Damage(OPP, Printed()), OpponentReducedDamage(e.amount)),
    # v0.38（docs/bench-switch-combined-v0.38.md）。控えへのダメージ・入れ替え・同じコインの複数の効果・軽減・山札にもどる効果
    E.ChooseOpponentBenchDamage: lambda e: (ChosenBenchDamage(Fixed(e.damage), local_coin=None, required=e.requires_bench),),
    # v0.89: 選ぶ要素と選んだ個体へのダメージの要素に分けた（``chosen_damage``。選んだ相手の対戦ポケモンへのダメージで、順番・お上品攻撃の減らす量の決定を出せる。選ぶ決定の形・
    # ログは v0.88 までの ``ChosenOpponentPokemonDamage`` と同じ）
    E.ChooseOpponentPokemonDamage: lambda e: chosen_damage(Fixed(e.damage)),
    E.DamageThenChosenBenchDamage: lambda e: (
        Damage(OPP, Printed()),
        ChosenBenchDamage(Fixed(e.bench_damage), local_coin=None, weakness_resistance=False if e.weakness_resistance_stated else None),
    ),
    E.SpreadDamage: lambda e: (Damage(OPP, Fixed(e.damage), weakness_resistance=False), BenchDamage(Fixed(e.damage))),
    E.DamageThenCoinBenchDamageEitherSide: lambda e: (
        Coin("coin"), Damage(OPP, Printed()), BenchDamage(Fixed(e.bench_damage), gate=("coin", HEADS)),
        BenchDamage(Fixed(e.bench_damage), gate=("coin", TAILS), own=True),
    ),
    E.CoinBonusDamageAndBenchDamage: lambda e: (
        Coin("coin"), Damage(OPP, PrintedPlusBonus("coin", e.bonus)), BenchDamage(Fixed(e.bench_damage), gate=("coin", HEADS)),
    ),
    E.DamageThenForceSwitchOnHeads: lambda e: (Damage(OPP, Printed()), ForceSwitch(local_coin=HEADS)),
    E.DamageThenForceSwitchThenSelfDamage: lambda e: (Damage(OPP, Printed()), ForceSwitch(), Damage(SELF, Fixed(e.self_damage), name="self_damage")),
    E.DamageThenSelfSwitchOnHeads: lambda e: (Damage(OPP, Printed()), SelfSwitch(local_coin=HEADS)),
    E.CoinBonusDamageAndSelfBarrier: lambda e: (
        Coin("coin"), Damage(OPP, PrintedPlusBonus("coin", e.bonus)), SelfPersistent(AttackBarrier.kind, gate=("coin", HEADS)),
    ),
    E.DamageThenPoisonOrParalyze: lambda e: (
        Damage(OPP, Printed()), Status(POISON, local_coin=HEADS, otherwise=PARALYSIS, reparalysis_check=True),
    ),
    E.DamageAndSelfDamageThenPoisonOnHeads: lambda e: (
        Damage(OPP, Printed()), Damage(SELF, Fixed(e.self_damage), name="self_damage"), Status(POISON, local_coin=HEADS),
    ),
    E.DamageThenReduceDamageNextTurn: lambda e: (Damage(OPP, Printed()),
                                                 SelfPersistent(DamageReduction.kind, amount=e.amount, local_coin=HEADS if e.on_heads else None)),
    E.DiscardAttachedAndReturnSelfToDeck: lambda e: (ReturnSelfToDeck(local_coin=None, after_damage=None, discard_attached=True),),
    E.ReturnSelfToDeckThenSearchPokemon: lambda e: (
        ReturnSelfToDeck(local_coin=None, after_damage=None, shuffle=False), PromoteFromBench(), RevealPokemonFromDeck(e.excluded),
    ),
    # v0.39（docs/selfdestruct-spread-count-v0.39.md）。じばく・控えへのダメージ・場のポケモンの数でダメージが決まるワザ
    E.ChooseOpponentPokemonDamageAndPowerLock: lambda e: (*chosen_damage(Fixed(e.damage), name="bench_damage"), LockChosenPowers()),  # v0.89
    E.DamagePoisonAndBenchDamage: lambda e: (Damage(OPP, Printed()), BenchDamage(Fixed(e.bench_damage)), Status(POISON)),
    E.DamageThenAttachLockOnHeads: lambda e: (Damage(OPP, Printed()), OpponentAttachLock(local_coin=HEADS)),
    # v0.60（docs/coins-defense-rebellion-v0.60.md）
    E.DamageThenCoinPerOpponentBench: lambda e: (Damage(OPP, Printed()), CoinPerOpponentBench(e.bench_damage, e.self_per)),
    E.SelfTailsDamageGuard: lambda e: (SelfDamageGuard(),),
    E.DamageIgnoringDefenderEffects: lambda e: (Damage(OPP, Printed(), defender_effects=False),),
    E.SelfDestructThenDiscardStadium: lambda e: (
        Damage(OPP, Printed()), Damage(SELF, Fixed(e.self_damage), name="self_damage"),
        BenchDamage(Fixed(e.bench_damage), weakness_resistance=False),
        BenchDamage(Fixed(e.bench_damage), weakness_resistance=False, own=True),
        DiscardStadium(),
    ),
    E.SelfDestruct: lambda e: (
        Damage(OPP, Printed()), Damage(SELF, Fixed(e.self_damage), name="self_damage"),
        BenchDamage(Fixed(e.bench_damage), weakness_resistance=False if e.weakness_resistance_stated else None),
        BenchDamage(Fixed(e.bench_damage), weakness_resistance=False if e.weakness_resistance_stated else None, own=True),
    ),
    # v0.61（docs/reactive-powers-trainer-damage-v0.61.md）
    E.OpponentCoinTailsBonusDamage: lambda e: (Damage(OPP, OpponentTailsBonus(e.bonus)),),
    E.DamageSelfDamageThenDiscardStadium: lambda e: (Damage(OPP, Printed()), Damage(SELF, Fixed(e.self_damage), name="self_damage"), DiscardStadium()),
    E.DamageIgnoringWeaknessResistance: lambda e: (Damage(OPP, Printed(), weakness_resistance=False),),
    E.DamageThenChosenBenchTargets: lambda e: (Damage(OPP, Printed()), ChosenBenchDamages(Fixed(e.bench_damage), e.max_targets)),
    E.DamageThenSameTypeBenchDamage: lambda e: (
        Damage(OPP, Printed()),
        BenchDamage(Fixed(e.bench_damage), weakness_resistance=None, same_type_as_opponent_active=True),
        BenchDamage(Fixed(e.bench_damage), weakness_resistance=None, same_type_as_opponent_active=True, own=True),
    ),
    E.DamageThenCoinBenchDamageBothSides: lambda e: (
        Coin("coin"), Damage(OPP, Printed()), BenchDamage(Fixed(e.bench_damage), gate=("coin", HEADS)),
        BenchDamage(Fixed(e.bench_damage), gate=("coin", HEADS), own=True),
    ),
    E.DamageThenOtherTypeBenchDamageBothSides: lambda e: (
        Damage(OPP, Printed()), BenchDamage(Fixed(e.bench_damage), exclude_type=e.excluded_type),
        BenchDamage(Fixed(e.bench_damage), exclude_type=e.excluded_type, own=True),
    ),
    E.DamagePlusPokemonCount: lambda e: (Damage(OPP, PrintedPlusPokemonCount(e.per, e.scope, e.names)),),
    E.CoinBonusDamageAndSelfDamage: lambda e: (
        Coin("coin"), Damage(OPP, PrintedPlusBonus("coin", e.bonus)), Damage(SELF, Fixed(e.self_damage), gate=("coin", HEADS), name="self_damage"),
    ),
    E.DamageThenSpecialPoisonOnHeads: lambda e: (Damage(OPP, Printed()), Status(POISON, local_coin=HEADS, poison_damage=e.poison_damage)),
    E.CoinPoisonAndBenchDamage: lambda e: (
        Coin("coin"), BenchDamage(Fixed(e.bench_damage), gate=("coin", HEADS)), Status(POISON, gate=("coin", HEADS)),
    ),
    # v0.40（docs/count-condition-switch-return-v0.40.md）。場の数・条件付きの効果・入れ替え・カードの移動
    E.GroupAttackFromDeck: lambda e: (BenchFromDeckAny(e.names), Damage(OPP, PokemonCountTimes(e.per, SCOPE_OWN_IN_PLAY, e.names))),
    E.NamedPokemonExplosion: lambda e: (
        Damage(OPP, PokemonCountTimes(e.per, SCOPE_BOTH_IN_PLAY, e.names)),
        Damage(OPP, Fixed(e.each), name="named_damage", names=e.names),
        Damage(SELF, Fixed(e.each), name="self_damage", names=e.names),
        BenchDamage(Fixed(e.each), weakness_resistance=None, names=e.names),
        BenchDamage(Fixed(e.each), weakness_resistance=None, names=e.names, own=True, name="own_bench_damage"),
    ),
    E.OpponentFlipsTailsDamage: lambda e: (Damage(OPP, TailsOfOpponentBenchCoins(e.per), weakness_resistance=False),),
    E.DamageRequiringOwnCounters: lambda e: (OwnCountersAtLeast(e.minimum), Damage(OPP, Printed())),
    E.DamagePlusIfDefenderDamaged: lambda e: (Damage(OPP, PrintedPlusBonusIfDefenderDamaged(e.bonus)),),
    E.AttackLockWhileSourceActive: lambda e: (OpponentAttackLockWhileSourceActive(e.max_hp),),
    E.FailOnTailsAmountIfBenchNamed: lambda e: (FailOnTails(), Damage(OPP, AmountIfOwnBenchNamed(e.names, e.amount))),
    E.SwitchOpponentThenDamage: lambda e: (ForceSwitch(chooser="attacker", required=True, carry=True), Damage(OPP, Printed())),
    E.ReturnOpponentActiveToDeck: lambda e: (ReturnOpponentToDeck(),),
    E.CoinsAllHeadsBonusDamage: lambda e: (Damage(OPP, PrintedPlusBonusOnAllHeads(e.coins, e.bonus)),),
    E.ShuffleDeckAttack: lambda e: (ShuffleDeck(own=e.own),),
    E.DamageThenSelfConfuseOnTails: lambda e: (Damage(OPP, Printed()), Status(CONFUSION, local_coin=TAILS, target=SELF)),
    # v0.41（docs/heal-counter-status-v0.41.md）。回復・ダメージカウンターの移動・特殊状態の分岐と選択・山札からエネルギーをつける効果
    E.DamageThenHealSelf: lambda e: (Damage(OPP, Printed()), HealCounters(e.counters, local_coin=HEADS if e.on_heads else None)),
    E.CoinHealSelf: lambda e: (Coin("coin"), HealCounters(e.counters, gate=("coin", HEADS)))
    + ((Status(SLEEP, target=SELF, gate=("coin", HEADS)),) if e.then_sleep else ()),
    E.CoinsHealOwnPokemon: lambda e: (Coin("coin", count=e.coins), HealCounters(heads_of="coin", scope=E.HEAL_OWN_ALL)),
    E.HealAllPokemonBothSides: lambda e: (HealCounters(e.counters, scope=E.HEAL_BOTH_ALL),),
    E.MoveOwnCountersToOpponent: lambda e: (ShiftCountersToOpponent(),),
    E.SwapCountersOnHeads: lambda e: (Coin("coin"), SwapCounters(gate=("coin", HEADS))),
    E.DamageThenConfuseBoth: lambda e: (Damage(OPP, Printed()), Status(CONFUSION), Status(CONFUSION, target=SELF)),
    E.DamageThenStatusByCoin: lambda e: (
        Damage(OPP, Printed()), Status(e.heads, local_coin=HEADS, otherwise=e.tails, reparalysis_check=PARALYSIS in (e.heads, e.tails)),
    ),
    # v0.70: ダメージのない「ぐるぐる」（ニョロゾ）。DamageThenStatusByCoin の Status と同じ
    E.StatusByCoinWithoutDamage: lambda e: (Status(e.heads, local_coin=HEADS, otherwise=e.tails, reparalysis_check=PARALYSIS in (e.heads, e.tails)),),
    E.DamageThenChosenStatusOnHeads: lambda e: (Damage(OPP, Printed()), ChosenStatus(conditions=e.conditions)),  # v0.88: デルタビームの 3 つ
    E.CoinDamageAndConfuseElseSelfConfuse: lambda e: (
        Coin("coin"), Damage(OPP, Printed(), gate=("coin", HEADS)), Status(CONFUSION, gate=("coin", HEADS)),
        Status(CONFUSION, target=SELF, gate=("coin", TAILS)),
    ),
    E.DamageThenConfuseOnAnyHeads: lambda e: (Damage(OPP, Printed()), Coin("coin", count=e.coins), Status(CONFUSION, gate=("coin", AtLeast(1)))),
    E.DamageThenSleepOnHeads: lambda e: (Damage(OPP, Printed()), Status(SLEEP, local_coin=HEADS)),
    E.DamageThenRetreatLockOnHeads: lambda e: (Damage(OPP, Printed()), OpponentRetreatLock(local_coin=HEADS)),
    E.SwitchOpponentActiveOnHeads: lambda e: (ForceSwitch(chooser="attacker", local_coin=HEADS, required=True),),
    E.DamageThenReturnSelfToDeckOnTails: lambda e: (Damage(OPP, Printed()), ReturnSelfToDeck(TAILS, after_damage="damage")),
    E.AttachEnergyFromDeckToSelf: lambda e: (AttachFromDeck(e.energy_type),),
    E.DamageThenLockSelf: lambda e: (Damage(OPP, Printed()), SelfAttackLock(None)),
    E.DamageMinusIfDefenderDamaged: lambda e: (Damage(OPP, PrintedMinusIfDefenderDamaged(e.reduction)),),
    # v0.42（docs/power-decisions-v0.42.md）。相手のポケモンの回復と引く・エネルギーを手札にもどす・残り HP を決めてカウンターをのせる・山札から進化・自分の場の
    # ポケモンを手札にもどす・ダメージのあとの任意の入れ替え・コインの数のダメージと自分のこんらん
    E.HealChosenOpponentThenDraw: lambda e: (ChosenOpponentHealThenDraw(),),
    E.CoinFlipDamageThenSelfConfuse: lambda e: (Damage(OPP, HeadsTimes(e.coins, e.damage_per_heads)), Status(CONFUSION, target=SELF)),
    E.ReturnEnergyThenDamage: lambda e: (
        ReturnOwnEnergyToHand(e.energy_type, when_lacking=LACKING_CONDITION, timing=TIMING_UNRESOLVED), Damage(OPP, Printed()),
    ),
    E.PlaceCountersToRemainingHpOnHeads: lambda e: (CountersToRemainingHp(e.remaining),),
    E.DamageThenOptionalSelfSwitch: lambda e: (Damage(OPP, Printed()), SelfSwitch(optional=True, after_damage="damage")),
    E.EvolveFromDeckOnHeads: lambda e: (EvolveFromDeck(),),
    E.ReturnOwnPokemonToHandOnHeads: lambda e: (ReturnOwnPokemonToHand(),),
    # v0.44（docs/search-evolution-once-attacks-v0.44.md）。場のポケモンを選ぶ・山札をさがす・自分を手札にもどす・山札から進化する・場に出てから 1 回だけ使える・
    # 手札と山札とトラッシュのカードを動かす。どれも既存の要素か、v0.44 の要素
    E.CoinChooseOpponentPokemonDamage: lambda e: chosen_damage(Fixed(e.damage), local_coin=HEADS),  # v0.89（のびるベロも同じ型）
    E.SearchTrainerOnHeads: lambda e: (RevealTrainerFromDeck(),),
    E.DamageThenReturnSelfToHandOnHeads: lambda e: (Damage(OPP, Printed()), ReturnAttackerToHand(HEADS)),
    E.EvolveSelfFromDeck: lambda e: (EvolveAttackerFromDeck(e.evolves_from),),
    E.OnceAfterEntryNoDamageOnTails: lambda e: (Damage(OPP, Printed(), local_gate=HEADS),),
    E.CoinsAllHeadsSpreadDamageExceptSelf: lambda e: (
        Coin("coin", count=e.coins), Damage(OPP, Fixed(e.damage), weakness_resistance=False, gate=("coin", AtLeast(e.coins))),
        BenchDamage(Fixed(e.damage), gate=("coin", AtLeast(e.coins))), BenchDamage(Fixed(e.damage), gate=("coin", AtLeast(e.coins)), own=True),
    ),
    E.DamageThenSwitchOpponentIfNotKnockedOut: lambda e: (Damage(OPP, Printed()), ForceSwitch(chooser="attacker")),
    E.DamageThenPoisonAndParalyzeOnHeads: lambda e: (
        Damage(OPP, Printed()), Coin("coin"), Status(POISON, gate=("coin", HEADS)), Status(PARALYSIS, gate=("coin", HEADS), reparalysis_check=True),
    ),
    E.SpecialPoisonOnHeadsWithoutDamage: lambda e: (Status(POISON, local_coin=HEADS, poison_damage=e.poison_damage),),
    E.ReturnHandThenRevealBasicEnergy: lambda e: (ReturnHandThenRevealEnergy(e.max_cards),),
    E.CoinPutOpponentDiscardOnDeckTop: lambda e: (OpponentDiscardToDeckTop(),),
    E.CoinDrawOrReturnHandToDeck: lambda e: (Coin("coin"), Draw(e.draw, gate=("coin", HEADS)), ReturnHandToDeck(e.count, gate=("coin", TAILS))),
    # v0.45（docs/conditional-damage-energy-v0.45.md）
    E.DamageFailUnlessOpponentStatus: lambda e: (FailUnlessOpponentStatus(e.condition), Damage(OPP, Printed())),
    E.DamageThenLastingAttackCoinCheckOnHeads: lambda e: (Damage(OPP, Printed()), OpponentAttackCheck(lasting=True, local_coin=HEADS)),
    E.DamageMultipliedAgainstType: lambda e: (Damage(OPP, PrintedTimesIfDefenderType(e.pokemon_type, e.factor)),),
    E.DamageThenPoisonAndConfuseOnAllHeads: lambda e: (
        Damage(OPP, Printed()), Coin("coin", count=e.coins), Status(POISON, gate=("coin", e.coins)), Status(CONFUSION, gate=("coin", e.coins))),
    E.SelfStatusWithoutDamage: lambda e: (Status(e.condition, target=SELF),),
    E.DamageIfSelfStatusThenOpponentStatus: lambda e: (
        SelfStatusCheck("self_status", e.condition), Damage(OPP, IfSelfStatus("self_status", e.amount)), Status(e.condition, if_result="self_status")),
    E.CoinSwitchOpponentThenStatus: lambda e: (ForceSwitch(chooser="attacker", local_coin=HEADS, carry=True), Status(e.condition, after_switch="switch")),
    E.DamageAndSelfDamageThenPreventDamageOnHeads: lambda e: (
        Damage(OPP, Printed()), Damage(SELF, Fixed(e.self_damage), name="self_damage"), SelfPersistent(PreventDamage.kind, local_coin=HEADS)),
    E.DamageThenMoveOpponentEnergyToBench: lambda e: (Damage(OPP, Printed()), MoveOpponentEnergyToBench()),
    E.DiscardExcessEnergyForDamage: lambda e: (
        DiscardOwnEnergy(e.energy_type, count=None, excess_over_cost=True), Damage(OPP, PlusPerDiscarded("discard", e.per_energy))),
    E.DamageThenAttachEnergyFromDiscardToSelf: lambda e: (Damage(OPP, Printed()), AttachFromDiscard(e.energy_type, 1, exact=True)),
    # v0.70: ダメージのない「たいでん」（マチスのピカチュウ）。DamageThenAttachEnergyFromDiscardToSelf の AttachFromDiscard と同じ（ちょうど 1 枚）
    E.AttachEnergyFromDiscardToSelf: lambda e: (AttachFromDiscard(e.energy_type, 1, exact=True),),
    E.DamageAndSelfDamagePerAttachedEnergyCard: lambda e: (
        Damage(OPP, Printed()), Damage(SELF, PerAttachedEnergyCards(e.energy_type, e.per_card), name="self_damage")),
    E.ZeroDamageBelowNextTurn: lambda e: (SelfPersistent(ZeroDamageBelow.kind, amount=e.threshold),),
    E.HalfRemainingHpDamage: lambda e: (Damage(OPP, HalfRemainingHp(e.round_down)),),
    E.ReturnReceivedDamageOnHeads: lambda e: (SelfRetaliation(None, multiplier=e.multiplier, on_heads=True),),
    E.PutOwnerBasicFromDeckOntoBenchOnHeads: lambda e: (BenchFromDeck((), owner=e.owner, optional=True, local_coin=HEADS),),
    E.DamageIgnoringResistance: lambda e: (Damage(OPP, Printed(), resistance=False),),
    E.CoinOpponentDeckTopDiscardTrainerElseHand: lambda e: (OpponentDeckTopDiscardTrainerElseHand(),),
    # v0.46（docs/continuous-powers-v0.46.md）
    E.DamageThenSelfConfuse: lambda e: (Damage(OPP, Printed()), Status(CONFUSION, target=SELF, after_damage="damage")),
    E.CoinsTimesDamageSelfConfuse: lambda e: (
        Coin("coin", count=e.coins), Damage(OPP, HeadsOfCoin("coin", e.per)), Status(CONFUSION, target=SELF, gate=("coin", AtLeast(e.at_least)))),
    E.AttachEnergyFromHandOnHeads: lambda e: (Coin("coin"), AttachFromHand(e.energy_type, e.max_cards, gate=("coin", HEADS))),
    E.DamageThenExactBenchTargets: lambda e: (
        Damage(OPP, Printed()), ChosenBenchDamages(Fixed(e.bench_damage), e.targets, weakness_resistance=False, exact=True)),
    E.HalveDamageNextTurn: lambda e: (SelfPersistent(HalvedDamage.kind),),
    E.ShuffleHandIntoDeckThenDraw: lambda e: (ShuffleHandThenDraw(e.count),),
    # v0.47（docs/fossil-hidden-info-v0.47.md）
    E.ArrangeDeckTopEffect: lambda e: (ArrangeDeckTop(e.max_cards),),
    E.LookOpponentHandCardToDeck: lambda e: (LookHandCardToDeck(),),
    E.LockOpponentTrainersNextTurn: lambda e: (LockOpponentTrainers(),),
    E.DamageThenLockOpponentTrainersOnHeads: lambda e: (Damage(OPP, Printed()), LockOpponentTrainers(local_coin=HEADS)),
    E.DamagePlusOwnCountersThenSelfDamageOnTails: lambda e: (
        Damage(OPP, PlusOwnCounters(e.per)), Damage(SELF, Fixed(e.self_damage), name="self_damage", local_gate=TAILS)),
    # v0.48（docs/effective-pokemon-properties-v0.48.md）
    E.ChangeOpponentWeakness: lambda e: (OpponentWeaknessColor(),),
    E.ChangeOwnResistance: lambda e: (SelfResistanceColor(),),
    E.SetMaxHpOnHeads: lambda e: (SelfMaxHp(e.amount),),
    E.DamageIfSelfMaxHpSet: lambda e: (Damage(OPP, AmountIfSelfMaxHpSet(e.amount)),),
    E.DamageThenPoisonAndConfuseOnHeads: lambda e: (
        Damage(OPP, Printed()), Coin("coin"), Status(POISON, gate=("coin", HEADS)), Status(CONFUSION, gate=("coin", HEADS))),
    E.CoinsPerNamedPokemonDamage: lambda e: (Damage(OPP, HeadsTimesNamedPokemon(e.per, e.names)),),
    E.PlaceCountersOnDamagedOpponentPokemon: lambda e: (PlaceCountersOnDamagedOpponents(e.counters),),
    E.DamageThenCoinsReturnOpponentToDeck: lambda e: (
        Damage(OPP, Printed()), Coin("coin", count=e.coins), ReturnOpponentToDeck(required=False, gate=("coin", AtLeast(e.coins)))),
    # v0.50（docs/mew-devolution-spray-v0.50.md）
    E.DamageTimesDefenderEnergyCards: lambda e: (Damage(OPP, DefenderEnergyCardsTimes(e.per)),),
    E.DevolveChosenPokemon: lambda e: (DevolveChosenPokemon(),),
    # v0.51（docs/discard-to-bench-v0.51.md）
    E.BenchBasicFromEitherDiscard: lambda e: (BenchFromEitherDiscard(),),
    E.CoinsPerDefenderCountersDamage: lambda e: (Damage(OPP, HeadsPerDefenderCounters(e.per)),),
    # v0.52（docs/field-return-v0.52.md）
    E.ReturnBothActivesToDeck: lambda e: (ReturnBothActivesToDeck(),),
    # v0.62（docs/history-attacks-v0.62.md）
    E.DamageIfUsedAttackLastTurn: lambda e: (UsedAttackCondition(e.target_attack_index, e.target_attack_name), Damage(OPP, Printed())),
    E.RepeatReceivedAttack: lambda e: (RepeatReceivedAttack(),),
    E.ReflectReceivedDamageAndEffects: lambda e: (ReflectCheck(), ReflectedDamage(OPP, ReceivedDamageAmount()), ReflectedParalysis(PARALYSIS, reparalysis_check=True)),
    E.DamageThenReturnOpponentToHand: lambda e: (Damage(OPP, Printed()), ReturnOpponentToHand()),
    # v0.72（docs/status-coins-effect-reuse-v0.72.md）
    E.CoinsHeadsTimesBonusDamage: lambda e: (Damage(OPP, PrintedPlusHeadsTimes(e.coins, e.per)),),
    E.DamageThenStatusSelfAndOpponent: lambda e: (Damage(OPP, Printed()), Status(e.condition, target=SELF, after_damage="damage"),
                                                  Status(e.condition, after_damage="damage")),
    E.PoisonAndSleepWithoutDamage: lambda e: (Status(POISON), Status(SLEEP)),
    E.DamageThenWakeOpponent: lambda e: (Damage(OPP, Printed()), WakeOpponent()),
    E.DamageAndOptionalFullDrain: lambda e: (Damage(OPP, Printed()), Drain("damage", full=True, optional=True)),
    E.DamageThenMoveOneEnergyToBench: lambda e: (Damage(OPP, Printed()), MoveOneEnergyToBench(e.energy_type)),
    E.RevealBasicEnergyFromDeck: lambda e: (RevealTrainerFromDeck(local_coin=None, category="basic_energy"),),
    E.DamageThenForceSwitchAfterDamage: lambda e: (Damage(OPP, Printed()), ForceSwitch(after_damage="damage")),
    # v0.75（docs/search-energy-pokemon-v0.75.md）
    E.DrawThenSwitchSelf: lambda e: (Draw(e.count), SelfSwitch(required=True)),
    E.RevealNamedPokemonFromDeckAny: lambda e: (RevealNamedPokemonFromDeck(e.names),),
    E.CoinsRecoverEnergyByHeads: lambda e: (Coin("coin", count=e.coins), RecoverEnergyByHeads(e.energy_type, heads_of="coin")),
    E.AttachEnergyFromDeckToSelfExactly: lambda e: (AttachFromDeck(e.energy_type, zero=ZERO_REQUIRED),),
    E.AttachEnergyFromDeckToBench: lambda e: (AttachFromDeckToBench(e.energy_type),),
    E.CoinAttachEnergyFromDeckToSelf: lambda e: (AttachFromDeck(e.energy_type, e.max_cards, zero=ZERO_UNRESOLVED, local_coin=HEADS, shuffle=False),),
    E.DamageThenDoubleDamageNextTurn: lambda e: (Damage(OPP, Printed()), SelfPersistent(DoubledDamage.kind)),
    # v0.76（docs/persistent-attack-modifiers-v0.76.md）
    E.ReduceDamageToSelfNextOpponentTurn: lambda e: (OpponentReducedDamage(e.amount, until_turn_end=True),),
    E.LockOpponentAttackOnHeads: lambda e: (OpponentAttackLock(local_coin=HEADS),),
    E.CoinNextTurnMultiplyElseLockAttack: lambda e: (
        Coin("coin"),
        SelfNextTurnAttackDamage(e.target_attack_index, e.factor, operation=NEXT_TURN_MULTIPLY, gate=("coin", HEADS)),
        SelfAttackLock(local_coin=None, target_attack_index=e.target_attack_index, gate=("coin", TAILS)),
    ),
    E.AttackLockWhileSourceActiveOnHeads: lambda e: (OpponentAttackLockWhileSourceActive(None, local_coin=HEADS),),
    E.AttachDiscardEnergyCardsToSelf: lambda e: (AttachFromDiscard(None, e.max_cards),),
    # v0.78（docs/darkness-metal-energy-v0.78.md）
    E.CoinsPerOwnPokemonDamage: lambda e: (Damage(OPP, HeadsTimesNamedPokemon(e.per, None)),),
    E.DiscardOpponentTrainersThenDamage: lambda e: (DiscardOpponentTrainers(), Damage(OPP, Printed())),
    E.RetreatLockWithoutDamage: lambda e: (OpponentRetreatLock(),),
    E.DamageThenSelfCannotAttack: lambda e: (Damage(OPP, Printed()), SelfCannotAttack()),
    # v0.79（docs/shared-checks-pokemon-reuse-v0.79.md 5 章）。既存の要素を組み合わせた 11 の型
    E.DamageThenParalyzeAndOpponentBenchOnHeads: lambda e: (
        ReparalysisGuard(), Coin("coin"), Damage(OPP, Printed()), BenchDamage(Fixed(e.bench_damage), gate=("coin", HEADS)),
        Status(PARALYSIS, gate=("coin", HEADS)),
    ),
    E.DamageThenPreventAttackDamageOnHeads: lambda e: (Damage(OPP, Printed()), SelfPersistent(PreventAttackDamage.kind, local_coin=HEADS)),
    E.DamageThenOpponentBenchOnHeads: lambda e: (Coin("coin"), Damage(OPP, Printed()), BenchDamage(Fixed(e.bench_damage), gate=("coin", HEADS))),
    E.CoinBonusDamageAndConfuse: lambda e: (Coin("coin"), Damage(OPP, PrintedPlusBonus("coin", e.bonus)), Status(CONFUSION, gate=("coin", HEADS))),
    E.CoinBonusPerOwnCounter: lambda e: (Damage(OPP, HeadsPlusOwnCounters(e.per)),),
    E.HealSelfWithoutDamage: lambda e: (HealCounters(e.counters),),
    E.DamageThenDiscardOneOnTails: lambda e: (Damage(OPP, Printed()), DiscardOwnEnergy(e.energy_type, local_coin=TAILS, when_lacking=LACKING_SKIP)),
    E.CoinChooseOpponentBenchDamage: lambda e: (ChosenBenchDamage(Fixed(e.damage)),),
    E.SearchTrainerRequiredOnHeads: lambda e: (RevealTrainerFromDeck(required=True),),
    E.CoinDiscardAllOpponentTrainers: lambda e: (DiscardOpponentTrainers(all_pokemon=True, local_coin=HEADS),),
    E.FailOnTailsDamageThenSelfCannotAttack: lambda e: (FailOnTails(), Damage(OPP, Printed()), SelfCannotAttack(even_if_failed=True)),
    # v0.82（docs/energy-discard-return-v0.82.md 6 章）: エネルギーカードをトラッシュするワザ
    E.CoinDiscardEnergyCardThenDamage: lambda e: (
        DiscardOwnEnergy(None, local_coin=TAILS, when_lacking=LACKING_NONE if e.when_lacking == "none" else LACKING_FAIL),
        Damage(OPP, Printed(), requires="discard"),
    ),
    E.OptionalDiscardEnergyBonusDamage: lambda e: (
        OptionalDiscardForBonus(e.energy_type, e.include_bench, e.max_cards), Damage(OPP, PlusPerDiscarded("discard", e.per)),
    ),
    E.DamageThenDiscardAllEnergyCards: lambda e: (Damage(OPP, Printed()), DiscardOwnEnergy(None, count=None)),
    E.OptionalDiscardAllSetDamage: lambda e: (OptionalDiscardAll(e.energy_type), Damage(OPP, AmountIfDiscarded("discard", e.amount))),
    E.DiscardEachTypeThenDamage: lambda e: (
        DiscardEachType(e.types), Damage(OPP, Printed(), requires="discard"),
        *((Damage(SELF, Fixed(e.self_damage), name="self_damage", local_gate=TAILS, coin_name="coin", requires="discard"),) if e.self_damage else ()),
    ),
    E.ChooseBenchThenAttachFromDeck: lambda e: (AttachFromDeckToBench(e.energy_type, bench_first=True),),
    E.CoinsDiscardThenBonusDamage: lambda e: (
        Coin("coin", count=e.coins), DiscardOwnEnergy(e.energy_type, heads_of="coin", when_lacking=LACKING_NONE, copy_need=e.coins),
        Damage(OPP, PrintedPlusHeadsOfCoin("coin", e.per), requires="discard"),
    ),
    E.CoinDiscardOneOrAllThenDamage: lambda e: (
        Coin("coin"), DiscardOwnEnergy(e.energy_type, gate=("coin", HEADS), when_lacking=LACKING_NONE),
        DiscardOwnEnergy(None, count=None, gate=("coin", TAILS), when_lacking=LACKING_NONE), Damage(OPP, Printed(), requires="discard"),
    ),
    # v0.83（docs/shining-gentle-pokemon-v0.83.md）
    E.EachPlayerMayDrawAttack: lambda e: (EachPlayerDraws(e.max_cards),),
    E.RevealOneNamedPokemonFromDeck: lambda e: (RevealNamedPokemonFromDeck(e.names, exactly_one=True),),
    E.FailOnTailsPlusOwnCounters: lambda e: (FailOnTails(), Damage(OPP, PlusOwnCountersOnHeads(e.per))),
    E.DiscardEnergyThenSpreadThenCoinDiscardEach: lambda e: (
        DiscardOwnEnergy(e.energy_type, count=e.count, when_lacking=LACKING_FAIL), Damage(OPP, Printed()), BenchDamage(Fixed(e.bench_damage)),
        DiscardOpponentEnergy(each_bench=True, local_coin=HEADS),
    ),
    E.HealChosenBenchByEnergy: lambda e: (HealChosenOwnBench(e.energy_type),),
    E.CoinsPerDefenderEnergyChosenStatus: lambda e: (
        Damage(OPP, Printed()), Coin("coin", per_opponent_energy=True),
        ChosenStatus(local_coin=None, gate=("coin", AtLeast(1)), conditions=E.MIRACLE_LEAF_CONDITIONS),
    ),
    E.ChooseBenchThenDamageAndEnergyBenchDamage: lambda e: (
        ChooseOpponentBench(), Damage(OPP, Printed()), ChosenTargetDamage(OwnTypedEnergyTimes(e.energy_type, e.per)),
    ),
    E.SelfReflectShield: lambda e: (SelfReflectShield(e.amount),),
    E.DiscardEnergyThenPlusDefenderEnergyUnits: lambda e: (
        DiscardOwnEnergy(e.energy_type, when_lacking=LACKING_NONE), Damage(OPP, PlusDefenderEnergyUnits(e.per), requires="discard"),
    ),
    E.CoinBonusAndBenchElseSelfDamage: lambda e: (
        Coin("coin"), Damage(OPP, PrintedPlusBonus("coin", e.bonus)), BenchDamage(Fixed(e.bench_damage), gate=("coin", HEADS)),
        Damage(SELF, Fixed(e.self_damage), gate=("coin", TAILS)),
    ),
    E.ExcessEnergyDamageIgnoringResistance: lambda e: (Damage(OPP, ExcessTypedEnergy(e.energy_type, e.per), resistance=False),),
    E.FailOnTailsSpreadBothThenSelfCannotAttack: lambda e: (
        FailOnTails(), Damage(OPP, Printed()), BenchDamage(Fixed(e.bench_damage)), BenchDamage(Fixed(e.bench_damage), own=True),
        SelfCannotAttack(even_if_failed=True),
    ),
    E.ThreeCoinsStatusByHeads: lambda e: (
        Damage(OPP, Printed()), ReparalysisGuard(), Coin("coin", count=3), Status(SLEEP, gate=("coin", Exactly(1))),
        Status(CONFUSION, gate=("coin", Exactly(2))), Status(PARALYSIS, gate=("coin", Exactly(3))),
    ),
    E.LookTopTakeOneThenShuffle: lambda e: (LookTopTakeOne(e.look),),
    E.DiscardEnergyThenCoinConfuseElseSleep: lambda e: (
        DiscardOwnEnergy(e.energy_type, when_lacking=LACKING_FAIL), Damage(OPP, Printed()), Status(CONFUSION, local_coin=HEADS, otherwise=SLEEP),
    ),
    E.ChooseOwnTypeThenAttachFromHand: lambda e: (AttachFromHandToChosen(e.energy_type, e.max_cards),),
    E.EachPlayerRecoverFromDiscard: lambda e: (
        EachPlayerRecoversFromDiscard(e.category, e.max_cards, e.destination, HEADS if e.coin else None),
    ),
    E.FailUnlessEqualEnergyCardsDamage: lambda e: (FailUnlessEqualEnergyCards(), Damage(OPP, Printed())),
    E.EachPlayerLookTopTakeBasicEnergy: lambda e: (EachPlayerLooksTakesBasicEnergy(e.look),),
    E.PlusDefenderSpecialEnergyCardsDamage: lambda e: (Damage(OPP, PlusDefenderSpecialEnergyCards(e.per)),),
    E.CoinWashChosenBench: lambda e: (WashOwnBench(),),
    E.DamageSleepThenHealBothBench: lambda e: (Damage(OPP, Printed()), Status(SLEEP), HealCounters(e.counters, scope=E.HEAL_BOTH_BENCH)),
    E.PlusIfDefenderMoreEnergyDamage: lambda e: (Damage(OPP, PlusIfDefenderMoreEnergy(e.bonus)),),
    E.HealOwnPokemonWithoutDamage: lambda e: (HealCounters(e.counters, scope=E.HEAL_OWN_ALL),),
    E.DamageThenChosenBenchCoinDamage: lambda e: (Damage(OPP, Printed()), ChosenBenchCoinDamage(e.coins, e.per)),
    # v0.84（docs/light-powers-evolution-v0.84.md）
    E.SwitchSelfThenStatusGuardAttack: lambda e: (SwitchSelfThenStatusGuard(),),
    E.BenchBabyOrBasicFromOwnDiscardAttack: lambda e: (BenchBabyOrBasicFromOwnDiscard(),),
    E.ReturnOwnBenchToDeckAttack: lambda e: (ReturnOwnBenchToDeck(),),
    E.DamageThenBubbleJump: lambda e: (Damage(OPP, Printed()), BubbleJump()),
    E.DamageThenOptionalDiscardStadium: lambda e: (Damage(OPP, Printed()), OptionalDiscardStadium()),
    E.DamageThenOpponentMayDraw: lambda e: (Damage(OPP, Printed()), OpponentMayDraw()),
    E.EachPlayerEvolutionSong: lambda e: (EachPlayerEvolvesFromDeck(),),
    E.DamageThenBenchAttackDamageGuard: lambda e: (Damage(OPP, Printed()), SelfPersistent(BenchAttackDamageGuard.kind)),
    E.ZeroDamageAtLeastNextTurn: lambda e: (SelfPersistent(ZeroDamageAtLeast.kind, amount=e.threshold),),
    E.DamageThenAttackEffectGuard: lambda e: (Damage(OPP, Printed()), SelfPersistent(AttackEffectGuard.kind)),
    # v0.85（docs/entry-powers-energy-lifecycle-v0.85.md 6 章）
    E.CoinChosenSideHealAttack: lambda e: (CoinChosenSideHeal(e.counters),),
    E.CoinsPerOwnCountersBonusDamage: lambda e: (Damage(OPP, PlusHeadsPerOwnCounters(e.per)),),
    E.DamageThenStatusImmunityNextTurn: lambda e: (Damage(OPP, Printed()), SelfPersistent(StatusImmunityNextTurn.kind)),
    E.DiscardFireThenDamageBothBenches: lambda e: (
        DiscardOwnEnergy(EnergyType.FIRE, count=e.count, when_lacking=LACKING_NONE, timing=TIMING_EFFECT), Damage(OPP, Printed(), requires="discard"),
        BenchDamage(Fixed(e.bench), requires="discard"), BenchDamage(Fixed(e.bench), own=True, requires="discard"),
    ),
    E.DamageThenMillOwnDeck: lambda e: (Damage(OPP, Printed()), MillOwnDeck(e.count)),
    E.PlusDiscardTypeCardsThenReturnToDeck: lambda e: (Damage(OPP, PlusDiscardTypeCards(e.energy_type, e.per)), ReturnDiscardTypeToDeck(e.energy_type)),
    E.DiscardEnergyCardsThenDamageNoneIfLacking: lambda e: (
        DiscardOwnEnergy(None, count=e.count, when_lacking=LACKING_NONE, timing=TIMING_EFFECT), Damage(OPP, Printed(), requires="discard"),
    ),
    E.AttachFromDeckUpToNamedCount: lambda e: (AttachFromDeckUpToNamedCount(e.energy_type, e.name),),
    E.DamageByDefenderStage: lambda e: (Damage(OPP, PrintedByDefenderStage(e.baby, e.basic)),),
    E.AmountIfDefenderDamagedDamage: lambda e: (Damage(OPP, AmountIfDefenderDamaged(e.amount)),),
    E.CoinSetIfDefenderDarkDamage: lambda e: (Damage(OPP, CoinSetIfDefenderDark(e.amount)),),
    E.CoinsTimesDamageThenParalyzeIfAtLeast: lambda e: (
        ReparalysisGuard(), Coin("coin", count=e.coins), Damage(OPP, HeadsOfCoin("coin", e.per)), Status(PARALYSIS, gate=("coin", AtLeast(e.at_least))),
    ),
    # v0.86（docs/entry-energy-evolution-reactions-v0.86.md 7 章）
    E.DiscardTypeCardsThenDamageNoneIfLacking: lambda e: (
        DiscardOwnEnergy(e.energy_type, count=e.count, when_lacking=LACKING_NONE, timing=TIMING_EFFECT), Damage(OPP, Printed(), requires="discard"),
    ),
    E.CoinPerOpponentPokemonDamageThenHealDealt: lambda e: (CoinPerOpponentPokemon(e.amount, name="dark_drain"), Drain("dark_drain", full=True)),
    E.DamageThenLockOpponentHandTrainersOnHeads: lambda e: (Damage(OPP, Printed()), LockOpponentTrainers(local_coin=HEADS, hand_only=True)),
    E.DamageThenStopDefenderPowers: lambda e: (Damage(OPP, Printed()), StopDefenderPowers()),
    E.DamageThenParalyzeOrSleepByTwoCoins: lambda e: (
        ReparalysisGuard(), Coin("coin", count=2), Damage(OPP, Printed()), Status(PARALYSIS, gate=("coin", Exactly(2))), Status(SLEEP, gate=("coin", Exactly(1))),
    ),
    E.DamageThenProtectOwnBench: lambda e: (Damage(OPP, Printed()), ProtectOwnBench()),
}


# ---------------------------------------------------------------- v0.86（docs/entry-energy-evolution-reactions-v0.86.md 7 章）


@dataclass(frozen=True)
class DealtTotal:
    """v0.86: 要素が与えたダメージの合計（``DamageResult.dealt`` の和）。``Drain`` が ``dealt`` を読む（ダークドレインの「与えたダメージの合計ぶん」）。"""

    dealt: int


@dataclass(frozen=True)
class CoinPerOpponentPokemon(Element):
    """相手の場のポケモン全員に対して 1 枚ずつコインを投げ、「おもて」が出たポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ ``amount`` ダメージ（v0.86。わるいクロバットの
    「ダークドレイン」）。結果は与えたダメージの合計（``DealtTotal``。``fs.results[name]``）。

    - 対象はこの要素を処理する時点の相手の場の並び（バトル場 → ベンチの順）。コインは 1 匹 1 枚、並びの順に 1 回の ``flip`` で投げ、``i`` 枚目は ``i`` 番目のポケモンのもの
      （「おもて」の数でまとめない。どのポケモンかが要る。ログ ``pokemon_coin_results``）。v0.60 の ``CoinPerOpponentBench`` と同じ形
    - すべて投げてから、「おもて」のポケモンに並びの順でダメージ（バトル場は ``OPPONENT_ACTIVE``・控えは ``OPPONENT_BENCH``。弱点・抵抗力なし）。控えへのダメージは［ベンチガード］の
      決定を出しうる（決定をまたいで、残りの並びとそれまでの合計を運ぶ。コインは投げ直さない）
    - 「とうめい」がはたらいているポケモンのあとにポケモンがいれば TS1（コインの割り当てが投げ方で変わる。v0.60 と同じ問い）。2 匹以上は T27
    """

    amount: int
    name: str = "pokemon_coins"
    phase: ClassVar[Phase] = Phase.DAMAGE
    guards_bench: ClassVar[bool] = True

    def run(self, run: AttackRun) -> bool:
        state = run.state
        side = state.players[1 - run.player]
        targets = ([side.active] if side.active is not None else []) + list(side.bench)
        if not targets:
            run.fs.results[self.name] = DealtTotal(0)
            return False
        if any(E.evasion_power(state, pokemon) is not None for pokemon in targets[:-1]):
            raise run.res.question("bench_coin_transparency_order", f"相手の場のポケモン {[p.pokemon_id for p in targets]}")
        flips = run.flip(len(targets))
        run.fs.coins[self.name] = flips
        state.add_event("pokemon_coin_results", player=run.player, pokemon=run.attacker().card, pokemon_id=run.attacker().pokemon_id, effect=str(run.key),
                        targets=tuple(p.pokemon_id for p in targets), results=tuple(face.value for face in flips.results))
        entries = tuple((E.OPPONENT_ACTIVE if pokemon is side.active else E.OPPONENT_BENCH, pokemon.pokemon_id, self.amount, False)
                        for pokemon, face in zip(targets, flips.results) if face is HEADS)
        return self._deal(run, entries, 0)

    def _deal(self, run: AttackRun, entries: tuple, total: int, guard: tuple[int, ...] | None = None) -> bool:
        for i, (kind, pid, base, wr) in enumerate(entries):
            try:
                result = deal_damage(run.res, run.fs, kind, base, pokemon_id=pid, weakness_resistance=bool(wr), guard=guard if i == 0 else None,
                                     guard_suspend=True)
            except BenchGuardRequest as request:
                run.suspend(kind=BENCH_GUARD, player=request.owner, options=list(request.options), min_choices=0, max_choices=request.max_choices, carry=True,
                            extra=(("element", run.index), ("bench_guard", (entries[i:], total, 0))) + request.extra())
                return True
            total += result.dealt
        run.fs.results[self.name] = DealtTotal(total)
        return False

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        entries, total, _ = run.carried["bench_guard"]
        self._deal(run, tuple(tuple(e) for e in entries), total, tuple(choices))


@dataclass(frozen=True)
class StopDefenderPowers(OpponentRetreatLock):
    """次の自分の番が終わるまで、このワザを受けた相手（相手の対戦ポケモン）は「特殊能力」を使うことができず、その効果も消える（v0.86。わるいモココの「スタンウェーブ」。持続する効果
    ``PowersStopped``）。v0.41 の ``OpponentRetreatLock`` と同じ形（対象がこのワザで HP 以上なら与えない・「とうめい」・「ワザをうけない」状態・クリスタルボディの評価）。"""

    opponent_element: ClassVar[str] = E.POWER_LOCK_ELEMENT

    def run(self, run: AttackRun) -> bool:
        return _opponent_lock(self, run, PowersStopped, E.POWER_LOCK_ELEMENT)


@dataclass(frozen=True)
class ProtectOwnBench(Element):
    """次の相手の番が終わるまで、自分の控えポケモン全員は、ワザによるダメージや効果を受けない（v0.86。エンテイ（PF2-008）の「ほのおのまもり」）。この要素を処理する時点の自分の
    控えポケモンそれぞれに持続する効果 ``BenchProtection`` を与える（自分のポケモンへの効果なので、受けるかを評価する（``reaches``）。控えがいなければ何もしない）。"""

    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        turn = run.state.turn_number
        for pokemon in list(run.state.players[run.player].bench):
            if not reaches(run.res, run.fs, run.player, pokemon, E.BENCH_PROTECTION_ELEMENT):
                continue
            effect = BenchProtection(source_card=attacker.card, source_player=run.player, created_turn=turn,
                                     active_turn=turn + BenchProtection.turns_until_active)
            add_persistent_effect(run.state, run.player, pokemon, effect, attack=str(run.key))
        return False


def compile_attack(effect: E.AttackEffect) -> tuple[Element, ...]:
    """v0.13 のワザの実装から要素の並びを作る（部分型は使わない。実装の型が完全に一致するものだけ）。"""
    builder = BUILDERS.get(type(effect))
    if builder is None:
        raise UnsupportedByKernel(f"ワザの実装 {type(effect).__name__}（{effect.implementation_id}）はプロトタイプの対応表にない")
    return builder(effect)


# ---------------------------------------------------------------- v0.87（docs/movement-damage-reactions-v0.87.md 8 章）


@dataclass(frozen=True)
class OpponentPowerSuppression(Element):
    """コインを投げて ``local_coin`` なら、次の相手の番が終わるまで、相手の場にいるポケモンは特殊能力を使うことができず、その力も消える（v0.87。ドガースの「ふしぎなガス」）。

    - 相手プレイヤーの場に与える期限のある効果（``state.TrainerTurnEffect`` の種類 ``OPPONENT_POWER_SUPPRESSION``。``player`` はワザを使ったプレイヤー・``source_card`` はワザを
      印刷したカード・``attack_index``。消える番は与えた番 + 1）。場のポケモンに写さないので、入れ替え・きぜつ・場をはなれることでは消えない。ログ ``trainer_effect_added``
      （``attack_index``・``effect``）
    - 相手の場に、ワザの効果を受けないポケモン（「ワザをうけない」状態・［オーロラヴェール］の控え・エフェクトガード・［クリスタルボディ］・「とうめい」）がいれば、そのポケモンも
      止まるかは決まらない（MG2）。効果だけを決めるコインなので、コインの前に止める（先読みが見つける）
    """

    local_coin: CoinSide | None = None
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        from .kernel import first_void
        state = run.state
        opponent = 1 - run.player
        for pokemon in state.players[opponent].in_play():
            if state.is_face_down(pokemon):
                continue
            if first_void(run.res, run.incoming(), opponent, pokemon, Window.BEFORE_EFFECT) is not None or E.evasion_power(state, pokemon) is not None:
                raise run.res.question("strange_gas_protected", f"ポケモン {pokemon.pokemon_id}")
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        expires = state.turn_number + 1
        card = run.attacker().card
        record = TrainerTurnEffect(kind=OPPONENT_POWER_SUPPRESSION, player=run.player, source_card=card, card_id=run.key.card_id, created_turn=state.turn_number,
                                   expires_turn=expires, attack_index=run.key.attack_index)
        if any(r.kind == OPPONENT_POWER_SUPPRESSION and r.player == run.player and r.expires_turn == expires for r in state.trainer_effects):
            raise RuntimeError(f"プレイヤー {run.player} の「ふしぎなガス」が、消える番 {expires} にすでにある（1 番に使えるワザは 1 つ。エンジンの不具合）")
        state.trainer_effects = state.trainer_effects + (record,)
        state.add_event("trainer_effect_added", player=run.player, effect_kind=OPPONENT_POWER_SUPPRESSION, trainer_card=card, card_id=run.key.card_id,
                        expires_turn=expires, attack_index=run.key.attack_index, effect=str(run.key))
        return False


BUILDERS |= {
    E.DamageThenSwitchBothActives: lambda e: (Damage(OPP, Printed()), ForceSwitch(carry=True), SelfSwitch()),
    E.DamageThenSuppressOpponentPowersOnHeads: lambda e: (Damage(OPP, Printed()), OpponentPowerSuppression(local_coin=HEADS)),
}


# ---------------------------------------------------------------- v0.88（docs/type-energy-colors-v0.88.md）

COLOR_ANY = "any"  # 無色以外の 8 色（コアストリーム）
COLOR_OWN_BASIC = "own_basic"  # 自分についている「基本エネルギーカード」の色（レインボーウェーブ）
COLOR_BY_ENERGY = "energy"  # その色の「エネルギー」がついているポケモン（``effects.energy_color_presence``）
COLOR_BY_TYPE = "type"  # 今有効なタイプがその色のポケモン（``effects.type_readings``）
# 止めるコード → 問い（色の数え方・タイプの読み方の問いを、解決の基盤の問いとして止める。先読みが集めて宣言の前に止める）
QUESTION_BY_CODE = {question.code: key for key, question in QUESTIONS.items() if question.code is not None}


@dataclass(frozen=True)
class ChosenColor:
    """v0.88: ``ChooseColor`` で選んだ色。``fs.results`` に置き、決定をまたぐときは続きの情報の ``chosen_colors`` で運ぶ（``AttackRun.suspend``）。選べる色がなかったなら None。"""

    color: EnergyType | None


def raise_color_problem(run: AttackRun, error: UnsupportedError, detail: str) -> None:
    """v0.88: 色の数え方・タイプの読み方が決まらない理由（``UnsupportedError``）を、同じコードの問いとして止める。"""
    raise run.res.question(QUESTION_BY_CODE[error.code], detail, error)


@dataclass(frozen=True)
class ChooseColor(Element):
    """ワザを使ったプレイヤーが色を 1 つ選ぶ（v0.88。決定 ``SELECT_COLOR``）。``source`` が ``COLOR_ANY`` なら無色以外の 8 色（スターミーの「コアストリーム」）、``COLOR_OWN_BASIC`` なら
    自分についている「基本エネルギーカード」の印刷の色（ミュウの「レインボーウェーブ」。``effects.basic_energy_card_colors``。色を変えたカード（CE3）・レインボーエネルギー（RB3）で
    選べる色が変わるなら止める）。選べる色が 1 つでも決定を出す。選べる色がなければ選ばない（``ChosenColor(None)``。あとのダメージの要素の対象はない）。

    v0.90: ``gate``（ワザ全体のコインの面のときだけ選ぶ。ドーブルの「ペイント」の「コインを投げて「おもて」なら、好きな「色(タイプ)」(無色以外)を1つ選び」）。選ぶだけなので、
    コインの処理の対象・無効の確かめ（``Coin`` の ``void_coin_question``）には、あとの要素だけを数える（``ChooseTarget`` と同じ）。選ばなかったら ``ChosenColor(None)``"""

    source: str = COLOR_ANY
    name: str = "color"
    gate: tuple | None = None
    # v0.91: 前の要素（``RemoveChosenMarker``）の結果の名前。取りのぞいた数が 0 なら選ばない（ポリゴンの「ハイパーテクスチャー」の「のっているなら、それをとりのぞき、好きな
    # 「色(タイプ)」(無色以外)を選んでから」）。None なら見ない
    requires: str | None = None
    phase: ClassVar[Phase] = Phase.NEUTRAL
    decision_kind: ClassVar[str] = SELECT_COLOR

    def coin_dependent(self, name: str) -> bool:
        return False  # 選ぶだけ（v0.90。コインが決める処理は、あとの要素で数える）

    def options(self, run: AttackRun) -> tuple[int, ...]:
        if self.source == COLOR_ANY:
            return E.NON_COLORLESS_CHOICES
        readings, error = E.basic_energy_card_colors(run.state, run.attacker())
        if len(set(readings)) > 1:
            raise_color_problem(run, error, f"ワザ {run.key} で選べる「基本エネルギーカード」の色")
        return tuple(sorted(E.COLORS.index(color) for color in readings[0]))

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            run.fs.results[self.name] = ChosenColor(None)  # v0.90: コインの面が違う（選ばない。ログは残さない）
            return False
        if self.requires is not None:
            removed = run.fs.results.get(self.requires)
            if removed is None:
                raise RuntimeError(f"取りのぞいた数の結果 {self.requires!r} がない（要素の並びの誤り。エンジンの不具合）")
            if not isinstance(removed, MarkersRemoved):
                raise TypeError(f"取りのぞいた数の結果 {self.requires!r} が {type(removed).__name__}（MarkersRemoved でない。エンジンの不具合）")
            if removed.count == 0:
                run.fs.results[self.name] = ChosenColor(None)  # v0.91: 取りのぞかなかった（選ばない。ログは残さない）
                return False
        options = self.options(run)
        if not options:
            run.fs.results[self.name] = ChosenColor(None)
            run.state.add_event("attack_color_none", player=run.player, pokemon_id=run.attacker().pokemon_id, effect=str(run.key))
            return False
        run.suspend(kind=SELECT_COLOR, player=run.player, options=options, carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if len(choices) != 1 or choices[0] not in decision.options:
            raise RuntimeError(f"色の決定の答え {choices!r} が、選べる色ではない（エンジンの不具合）")
        color = E.COLORS[choices[0]]
        run.fs.results[self.name] = ChosenColor(color)
        run.state.add_event("attack_color_chosen", player=run.player, pokemon_id=run.attacker().pokemon_id, effect=str(run.key), color=color.value)


def color_filter_hit(run: AttackRun, pokemon: PokemonInPlay, color_filter: tuple[str, str]) -> bool:
    """v0.88: ``pokemon`` が、前の ``ChooseColor`` で選んだ色でしぼる条件に合うか。``COLOR_BY_ENERGY``: その色の「エネルギー」がついている（エネルギーの今の色。数え方が決まらなければ
    止める）。``COLOR_BY_TYPE``: 今有効なタイプがその色（色の読み方で答えが変わるなら止める。VS1・CE1・CE2）。選んだ色がなければ合わない。"""
    mode, result = color_filter
    chosen = run.fs.results.get(result)
    if chosen is None:
        raise RuntimeError(f"色を選んだ結果 {result!r} がない（要素の並びの誤り。エンジンの不具合）")
    if chosen.color is None:
        return False
    if mode == COLOR_BY_ENERGY:
        answer, problem = E.energy_color_presence(run.state, pokemon, chosen.color)
        if problem is not None and not answer:
            raise_color_problem(run, problem, f"ワザ {run.key} の対象（「{chosen.color.ja}」のエネルギーのついているポケモン {pokemon.pokemon_id}）")
        return answer
    if mode == COLOR_BY_TYPE:
        hits = {color is chosen.color for color in E.type_readings(run.state, pokemon)}
        if len(hits) > 1:
            raise type_question(run.res, E.TypeReadingsDiffer([pokemon]), f"ワザ {run.key} の対象（「{chosen.color.ja}」のポケモン）")
        return hits.pop()
    raise ValueError(f"色でしぼる条件 {mode!r} は未定義")


@dataclass(frozen=True)
class PlusPerBasicEnergyColor:
    """ダメージの目安の数字 + 自分についている「基本エネルギーカード」の色の種類の数 × ``per``（v0.88。ホウオウの「レインボーバーン」。p.321 の 1 段階）。数えるのはカードの印刷の色
    （``effects.basic_energy_card_colors``）。色を変えたカード（CE3）・レインボーエネルギー（RB3）で数が変わるなら止める。"""

    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        readings, error = E.basic_energy_card_colors(run.state, run.attacker())
        if len({len(colors) for colors in readings}) > 1:
            raise_color_problem(run, error, f"ワザ {run.key} の「基本エネルギーカード」の色の数")
        return run.attack.damage + len(readings[0]) * self.per


BUILDERS |= {
    E.ChosenColorEnergySpreadDamage: lambda e: (
        ChooseColor(COLOR_ANY),
        Damage(OPP, Fixed(e.amount), weakness_resistance=False, color_filter=(COLOR_BY_ENERGY, "color")),
        BenchDamage(Fixed(e.amount), weakness_resistance=False, color_filter=(COLOR_BY_ENERGY, "color")),
    ),
    E.OwnBasicColorTypeSpreadDamage: lambda e: (
        ChooseColor(COLOR_OWN_BASIC),
        Damage(OPP, Fixed(e.amount), weakness_resistance=False, color_filter=(COLOR_BY_TYPE, "color")),
        BenchDamage(Fixed(e.amount), weakness_resistance=False, color_filter=(COLOR_BY_TYPE, "color")),
    ),
    E.PlusDistinctBasicEnergyColors: lambda e: (Damage(OPP, PlusPerBasicEnergyColor(e.per)),),
    E.ChangeOwnResistanceOptional: lambda e: (SelfResistanceColor(optional=True),),
    E.ChangeWeaknessAndResistanceOptional: lambda e: (OpponentWeaknessColor(optional=True, absent_skips=True), SelfResistanceColor(optional=True)),
}


# ---------------------------------------------------------------- v0.89（docs/selected-target-damage-v0.89.md）: 選んだ個体へのダメージ・効果


def chosen_pokemon(run: AttackRun, name: str, owner: int | None = None) -> list[PokemonInPlay]:
    """先に選んだ個体（``fs.results[name]`` の ``ChosenTarget``）。今も持ち主の場（``owner`` を渡せばその場）にいれば [そのポケモン]、選ばなかった・場をはなれたなら []。
    番号で探す（選んだ個体が場をはなれても、今の対戦ポケモン・同じ名前の別のポケモンにすり替えない）。"""
    picked = run.fs.results.get(name)
    if picked is None:
        raise RuntimeError(f"選んだ個体の記録 {name!r} がない（要素の並びの誤り。エンジンの不具合）")
    if not isinstance(picked, ChosenTarget):
        raise TypeError(f"選んだ個体の記録 {name!r} が {type(picked).__name__}（ChosenTarget でない。同じ名前の別の結果。エンジンの不具合）")
    if picked.pokemon_id is None or picked.pokemon_id in run.res.secret_lost:
        return []
    found = run.state.find_pokemon(picked.pokemon_id)
    if found is None or (picked.owner is not None and found[0] != picked.owner) or (owner is not None and found[0] != owner):
        return []
    return [found[1]]


def target_kind(run: AttackRun, owner: int, pokemon: PokemonInPlay) -> str:
    """場のポケモン ``pokemon``（持ち主 ``owner``）が今いる場所の、ダメージを受けるポケモンの種類（p.320 のダメージの (1)〜(4)）。"""
    if owner == run.player:
        if pokemon.pokemon_id == run.fs.frame.source_pid:
            return SELF
        if run.state.players[owner].active is pokemon:
            raise RuntimeError(f"ワザを使ったポケモンでない自分のバトル場のポケモン {pokemon.pokemon_id} への、選んだ個体のダメージ（エンジンの不具合）")
        return E.SELF_BENCH
    return OPP if run.state.players[owner].active is pokemon else E.OPPONENT_BENCH


@dataclass(frozen=True)
class ChooseTarget(Element):
    """場のポケモンを 1 匹選ぶ（v0.89。選んだ個体を ``fs.results[name]``（``ChosenTarget``。番号と持ち主）に置き、あとの要素（``TargetDamage``・``TargetHeal``・
    ``DiscardOpponentEnergy`` の ``chosen``）が使う。決定をまたぐときは続きの情報の ``chosen_targets`` で運ぶ）。

    - ``side``（どちらの場から）・``scope``（対戦ポケモンと控えポケモン ``TARGET_IN_PLAY``、控えポケモンだけ ``TARGET_BENCH``）・``chooser``（ワザを使ったプレイヤーか、相手
      プレイヤーか）を別々に表す（``effects.target_candidates``。選べるものはバトル場 → ベンチの並び。``TARGET_SIDE_BOTH`` はワザを使ったプレイヤーの場 → 相手の場）。相手が
      選ぶ決定でも、番のプレイヤーは変えない
    - 選ぶ時点は並びの位置で表す: ``gate``（ワザ全体のコインの面のときだけ選ぶ）・``local_coin``（この要素で 1 枚投げ、その面のときだけ選ぶ。のびるベロ・こばんなげ。
      コインはあとの要素のダメージだけを決めるので、選べるどのポケモンでもそのダメージが無効なら投げるかが決められない（v0.4b の問い。控えがいなければ v0.44 と同じ
      ``void_coin_question``））
    - 選べるポケモンがいなければ選ばない（``ChosenTarget(None)``。p.309。あとの要素は何もしない）。``required`` は説明が「…いないとき、このワザは使えない」と書くワザ
      （ワザを使うための条件は実装の ``usage_problem``。ここに来たらエンジンの不具合）
    - 選ぶと止めるポケモン: あとの要素（``choice_problem``）が、そのポケモンを選ぶと決められない場合（JS1・FA1・ダメージを受けないポケモンへのコイン）を返したら、選べるが選ぶと
      止める（``unresolved_choices``。どれもそうなら選ぶ前に止める。先読みは試さない）
    - ダメージの要素のまとまりの中で選ぶ（``Phase.DAMAGE``。前のダメージの要素の「ダメージを受けたとき」の効果は、選んだ個体へのダメージのあとに処理する。決定をまたいで運ぶ）。
      効果の対象を選ぶのは ``ChooseEffectTarget``"""

    side: str = E.TARGET_SIDE_OPPONENT
    scope: str = E.TARGET_IN_PLAY
    chooser: str = E.CHOOSER_ATTACKER
    name: str = "target"
    gate: tuple | None = None
    local_coin: CoinSide | None = None
    required: bool = False
    phase: ClassVar[Phase] = Phase.DAMAGE
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def __post_init__(self) -> None:
        if self.side not in E.TARGET_SIDES or self.scope not in E.TARGET_SCOPES or self.chooser not in E.TARGET_CHOOSERS:
            raise ValueError(f"選ぶ対象の指定 {(self.side, self.scope, self.chooser)!r} は未定義")
        if self.gate is not None and self.local_coin is not None:
            raise ValueError("選ぶ時点のコインは gate か local_coin のどちらか一方")

    def coin_dependent(self, name: str) -> bool:
        # 選ぶだけ（ワザ全体のコインが決める処理は、あとの要素で数える。``Coin`` の処理の対象・``void_coin_question`` はそちらで見る）
        return False

    def candidates(self, run: AttackRun) -> list[tuple[int, PokemonInPlay]]:
        return E.target_candidates(run.state, run.player, self.side, self.scope)

    def consumers(self, run: AttackRun) -> list[Element]:
        return [element for element in run.program if element is not self and getattr(element, "chosen", None) == self.name]

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        if self.required and not self.candidates(run):
            return (ILLEGAL if clause in (CANNOT_USE, FOLLOW_TEXT) else UNRESOLVED), "選べるポケモンがいない（ワザを使うための条件）"
        return None

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        candidates = self.candidates(run)
        if not candidates:
            if self.required:
                raise RuntimeError(f"選べるポケモンがいないのに、ワザ {run.key} の選ぶ要素に来た（使うための条件の確認の漏れ。エンジンの不具合）")
            run.fs.results[self.name] = ChosenTarget(None)
            return False
        if self.local_coin is not None:
            self._coin_question(run, candidates)
            if run.flip(1).results[0] is not self.local_coin:
                run.fs.results[self.name] = ChosenTarget(None)
                return False
        problems = {}
        for owner, pokemon in candidates:
            for consumer in self.consumers(run):
                check = getattr(consumer, "choice_problem", None)
                problem = None if check is None else check(run, owner, pokemon)
                if problem is not None:
                    problems[pokemon.pokemon_id] = problem
                    break
        options = [pokemon.pokemon_id for _, pokemon in candidates]
        blocked = tuple(pid for pid in options if pid in problems)
        keys = {problems[pid][0] for pid in blocked}
        if blocked and (len(blocked) == len(options) or len(keys) > 1):
            # どのポケモンを選んでも止まる（違う問いの組み合わせも、1 つの決定の止める理由に書けないので、選ぶ前に止める）
            key, detail = problems[blocked[0]]
            raise run.res.question(key, detail)
        extra: tuple = ()
        if blocked:
            question = QUESTIONS[problems[blocked[0]][0]]
            extra = _unresolved_extra(blocked, question.code, f"{question.message}（{'・'.join(question.rulings)}。選んだポケモン {list(blocked)} で結果が変わる）")
        player = run.player if self.chooser == E.CHOOSER_ATTACKER else 1 - run.player
        run.suspend(kind=SELECT_POKEMON, player=player, options=options, carry=True, extra=extra)
        return True

    def _coin_question(self, run: AttackRun, candidates: list[tuple[int, PokemonInPlay]]) -> None:
        """この要素のコインは、あとで選ぶ個体へのダメージだけを決める（のびるベロ・こばんなげ・きあいだま）。選べるどのポケモンでもそのダメージが無効なら止める。"""
        damages = [consumer for consumer in self.consumers(run) if isinstance(consumer, TargetDamage)]
        if not damages:
            return
        if self.side == E.TARGET_SIDE_OPPONENT and self.scope == E.TARGET_IN_PLAY and not run.state.players[1 - run.player].bench:
            # 選べるのが相手の対戦ポケモンだけ（v0.44 のこばんなげと同じ確かめ。「とうめい」で受けないと決まっていれば T19b、「ダメージを受けない」「ワザをうけない」状態なら v0.4b の問い）
            void_coin_question(run, [Damage(OPP, damages[0].base)])
            return
        if all(any(damage.void_target(run, owner, pokemon) for damage in damages) for owner, pokemon in candidates):
            raise run.res.question("prevented_coin_damage", f"ダメージを受けないポケモン {[p.pokemon_id for _, p in candidates]} から選ぶダメージだけを決めるコイン")

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ()))  # 選ぶと止めるポケモンは試さない
        return [answer for answer in all_answers(decision) if not blocked & set(answer)]

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        found = run.state.find_pokemon(choices[0]) if len(choices) == 1 and choices[0] in decision.options else None
        if found is None or (found[0], found[1].pokemon_id) not in {(owner, p.pokemon_id) for owner, p in self.candidates(run)}:
            raise RuntimeError(f"選んだポケモン {choices} が、選べるポケモンではない（エンジンの不具合）")
        run.fs.results[self.name] = ChosenTarget(choices[0], found[0])


@dataclass(frozen=True)
class ChooseEffectTarget(ChooseTarget):
    """効果（回復）の対象の場のポケモンを 1 匹選ぶ（v0.89。ベロリンガの「きずをなめる」）。``ChooseTarget`` と同じで、ダメージの要素のまとまりの外（``Phase.EFFECT``）。"""

    phase: ClassVar[Phase] = Phase.EFFECT


@dataclass(frozen=True)
class TargetDamage(Element):
    """先に選んだ個体（``ChooseTarget`` の ``chosen``）に、``base`` のダメージ（v0.89）。

    - 受けるポケモンの種類は、選んだ個体の今の場所で決める（相手の対戦ポケモンは p.320 の (1)、相手の控えは (2)、ワザを使ったポケモン自身は (3)、自分の控えは (4)。
      ``target_kind``）。選んだ個体が場をはなれていれば何もしない（コインも投げない）
    - 対戦ポケモン・自分へのダメージは ``Damage`` と同じ経路（同じ段階の順番の決定・お上品攻撃の減らす量の決定を出せる。``element_target`` が選んだ個体の種類を返す）。
      控えポケモンへのダメージは ``guarded_damages``（［ベンチガード］）
    - ``local_gate``: この要素のコイン 1 枚（「その後、コインを投げて「おもて」なら」。ロングショット・だくりゅう）。``base`` の要素のコイン（マジックダーツ・ねらいだま）も、
      選んでから投げる（ナツメのESPのやり直しで要素をもう一度処理しても、選んだ個体は続きの情報で運ぶので選び直さない）。コインがダメージだけを決め、選んだ個体へのダメージが
      無効なら投げるかが決められない（v0.4b の問い。「とうめい」で受けないと決まっていれば T19b）。どれも選ぶ前に ``choice_problem`` で選ぶと止めるポケモンにする
    - ``weakness_resistance``: False なら「弱点・抵抗力」に関係なく。``wr_unstated`` なら、説明が控えへのダメージの弱点・抵抗力について書いていない（ニャースの「ねこパンチ」）。
      計算するかどうかで受けるダメージが変わる控えは選ぶと止める（JS1。v0.39 のスパークと同じ）
    - ``defender_effects``（偽なら受けるポケモン自身の持っている効果を除く）と ``ignore_scope``（``kernel.IGNORE_HELD``・``IGNORE_UNSTATED``。だましうちは後者で、除く範囲の
      読み方で受けるダメージが変わるポケモンは選ぶと止める。FA1）"""

    base: Any
    chosen: str = "target"
    name: str = "target_damage"
    side: str = E.TARGET_SIDE_OPPONENT  # 選ぶ要素と同じ（コインの処理の対象・無効の確かめ）
    scope: str = E.TARGET_IN_PLAY
    gate: tuple | None = None
    local_gate: CoinSide | None = None
    weakness_resistance: bool = False
    wr_unstated: bool = False
    resistance: bool = True
    defender_effects: bool = True
    ignore_scope: str = IGNORE_HELD
    phase: ClassVar[Phase] = Phase.DAMAGE
    guards_bench: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if self.wr_unstated and self.weakness_resistance:
            raise ValueError("説明が弱点・抵抗力について書いていない控えへのダメージは、関係なくと同じ計算で、読み方で変わるときだけ止める")
        if not self.defender_effects and self.side != E.TARGET_SIDE_OPPONENT:
            raise ValueError("受けるポケモンの持っている効果を除くダメージは、相手のポケモンへのダメージだけ")
        if (self.wr_unstated or (not self.defender_effects and self.ignore_scope == IGNORE_UNSTATED)) and not isinstance(self.base, Fixed):
            # 選ぶ前に、読み方ごとの受けるダメージを比べる（``_fixed_base``）。決まった数でない基本は、組み立てる時に拒否する
            raise TypeError(f"選ぶ前に読み方で比べる選んだ個体へのダメージの基本は Fixed だけ（{type(self.base).__name__}）")

    def decides(self, kind: str) -> bool:
        return kind in (DAMAGE_STEP_ORDER, DAMAGE_REDUCTION, DAMAGE_OPTION) or super().decides(kind)

    def coin_receiver(self) -> str | None:
        # 相手の場のポケモンから選ぶダメージは、受けるポケモンがみな無効なら無効（``void_coin_question`` の控えの要素と同じ扱い。``void_for_all``）
        return "bench" if self.side == E.TARGET_SIDE_OPPONENT else None

    def _targets(self, run: AttackRun) -> list[tuple[int, PokemonInPlay]]:
        picked = run.fs.results.get(self.chosen)
        if isinstance(picked, ChosenTarget):
            found = chosen_pokemon(run, self.chosen)
            return [(run.state.find_pokemon(found[0].pokemon_id)[0], found[0])] if found else []
        return E.target_candidates(run.state, run.player, self.side, self.scope)

    def has_target(self, run: AttackRun) -> bool:
        return bool(self._targets(run))

    def void_target(self, run: AttackRun, owner: int, pokemon: PokemonInPlay) -> bool:
        from .kernel import first_void

        if run.fs.reception.get(pokemon.pokemon_id) is False:
            return True
        return first_void(run.res, run.incoming(), owner, pokemon, held_by_receiver=self.defender_effects) is not None

    def void_for_all(self, run: AttackRun) -> bool:
        targets = self._targets(run)
        return bool(targets) and all(self.void_target(run, owner, pokemon) for owner, pokemon in targets)

    def locate(self, run: AttackRun) -> tuple[str, int, PokemonInPlay] | None:
        found = chosen_pokemon(run, self.chosen)
        if not found:
            return None
        owner = run.state.find_pokemon(found[0].pokemon_id)[0]
        return target_kind(run, owner, found[0]), owner, found[0]

    def resolve_target(self, run: AttackRun) -> str:
        located = self.locate(run)
        if located is None:
            raise RuntimeError("決定を待つ間に、選んだ個体が場をはなれた（エンジンの不具合）")
        return located[0]

    def _coins(self, run: AttackRun) -> int:
        return local_coins(self.base, run)

    def _coin_problem(self, run: AttackRun, owner: int, pokemon: PokemonInPlay) -> tuple[str, str] | None:
        """コイン（この要素・基本となるダメージ）がダメージだけを決め、選んだ個体へのダメージが無効なら、その問い。"""
        if not (self._coins(run) or self.local_gate is not None) or not self.void_target(run, owner, pokemon):
            return None
        if run.fs.reception.get(pokemon.pokemon_id) is False:
            return "evaded_effect_coin", f"ポケモン {pokemon.pokemon_id}（「とうめい」で受けないと決まったポケモンへのダメージだけを決めるコイン）"
        return "prevented_coin_damage", f"ダメージを受けないポケモン {pokemon.pokemon_id} へのダメージだけを決めるコイン"

    def choice_problem(self, run: AttackRun, owner: int, pokemon: PokemonInPlay) -> tuple[str, str] | None:
        """選ぶ要素が、このポケモンを選ぶと決められない場合を聞く（なければ None）。うらのカード（マチスの秘策）は本当のカードを読まない（ダメージを受ける時におもてにしてから、
        今までどおり確かめる）。"""
        if run.state.is_face_down(pokemon):
            return None
        problem = self._coin_problem(run, owner, pokemon)
        if problem is not None:
            return problem
        check = getattr(self.base, "choice_problem", None)  # 選んだポケモンを読む基本となるダメージ（ろうでんの「水」エネルギーの数え方）
        problem = None if check is None else check(run, pokemon)
        if problem is not None:
            return problem
        kind = target_kind(run, owner, pokemon)
        if self.wr_unstated and kind in E.BENCH_TARGETS and weakness_resistance_matters(run.res, run.fs, kind, self._fixed_base(run), pokemon.pokemon_id):
            return "bench_damage_weakness_resistance", f"控えのポケモン {pokemon.pokemon_id}（選んだ控えで、計算するかどうかで受けるダメージが変わる）"
        if not self.defender_effects and self.ignore_scope == IGNORE_UNSTATED:
            from .kernel import ignored_effects_scope_difference

            difference = ignored_effects_scope_difference(run.res, run.fs, run.attacker(), owner, pokemon, kind, self._fixed_base(run))
            if difference is not None:
                return "ignored_effects_scope", f"ポケモン {run.attacker().pokemon_id} → ポケモン {pokemon.pokemon_id}・{difference}"
        if isinstance(self.base, Fixed):
            # v0.97（DF1）: 選んだポケモンへのダメージで、同じ力（［DARK df］・［NORMAL df］）のどれがはたらくかの読み方で受けるダメージが変わるなら、そのポケモンは選ぶと止める
            # （ほかのポケモンは選べる。決まった数でない基本は、ダメージを与えるときに deal_damage が止める）
            from .kernel import self_excluding_copies_question

            if self.defender_effects:
                excludes = (None,)
            else:
                excludes = (E.EXCLUDE_DEFENDER_HELD,) if self.ignore_scope == IGNORE_RECEIVER_HELD else (E.EXCLUDE_DEFENDER_HELD, E.EXCLUDE_DEFENDER_SIDE)
            wr = self.weakness_resistance and self.defender_effects
            copies = self_excluding_copies_question(run.res, run.fs, run.attacker(), pokemon, kind, self._fixed_base(run), excludes=excludes,
                                                    weakness_resistance=wr, resistance=self.resistance and self.defender_effects)
            if copies is not None:
                return "self_excluding_power_copies", copies
        return None

    def _fixed_base(self, run: AttackRun) -> int:
        return self.base.value(run, None)  # 決まった数（``__post_init__`` で確かめた）

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        located = self.locate(run)
        if located is None:
            return False  # 選ばなかった（選べるポケモンがいなかった・コインで選ばなかった）・選んだ個体が場をはなれた
        kind, owner, pokemon = located
        coins = self._coins(run)
        problem = self._coin_problem(run, owner, pokemon)
        if problem is not None:
            raise run.res.question(*problem)
        if self.local_gate is not None and run.flip(1).results[0] is not self.local_gate:
            return False
        flips = run.flip(coins, by_heads=getattr(self.base, "by_heads", False)) if coins else None
        if run.state.is_face_down(pokemon):
            # v0.67 と同じ: うらのカードは、ダメージを受ける時（基本となるダメージで受けるポケモンを読む前）におもてにする。「たねポケモン」でなくトラッシュしたら、対象はいない
            from .kernel import designate

            if designate(run.res, run.fs, owner, pokemon, "damage") is None:
                run.fs.results[self.name] = E.DamageResult(kind, owner, pokemon.pokemon_id, False, None, False, lost=True)
                return False
        base = self.base.value(run, flips)
        if self.wr_unstated and kind in E.BENCH_TARGETS and weakness_resistance_matters(run.res, run.fs, kind, base, pokemon.pokemon_id):
            raise run.res.question("bench_damage_weakness_resistance", f"控えのポケモン {pokemon.pokemon_id}")
        return self._deal(run, kind, pokemon, base, {})

    def _deal(self, run: AttackRun, kind: str, pokemon: PokemonInPlay, base: int, orders: dict[int, tuple[int, ...]], reduction: int | None = None,
              optional: bool | None = None) -> bool:
        if kind in (OPP, SELF):
            try:
                run.fs.results[self.name] = deal_damage(run.res, run.fs, kind, base, weakness_resistance=self.weakness_resistance, orders=orders or None,
                                                        order_decision=True, resistance=self.resistance, defender_effects=self.defender_effects,
                                                        reduction=reduction, ignore_scope=self.ignore_scope, optional=optional, optional_decision=True)
            except DamageOrderRequired as need:
                suspend_step_order(run, self, need, base, orders, reduction, optional)
                return True
            except DamageReductionRequired as need:
                if run.res.dry_run:
                    return self._deal(run, kind, pokemon, base, orders, run.res.oracle.choose(reduction_answers(run, self, base, orders, need)))
                suspend_damage_reduction(run, self, need, base, orders)
                return True
            except DamageOptionRequired as need:
                if run.res.dry_run:
                    return self._deal(run, kind, pokemon, base, orders, reduction, run.res.oracle.choose([False, True]))  # v0.119
                suspend_damage_option(run, self, need, base, orders, reduction)
                return True
            return False
        entry = (kind, pokemon.pokemon_id, base, self.weakness_resistance) + (() if self.defender_effects else (self.ignore_scope,))
        return guarded_damages(run, self, [entry], record=True)

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        located = self.locate(run)
        if located is None or located[0] not in (OPP, SELF):
            raise RuntimeError("順番・減らす量の決定を待つ間に、選んだ個体が対戦ポケモンでなくなった（エンジンの不具合）")
        optional = None
        if decision.kind == DAMAGE_REDUCTION:
            base, orders, reduction = resume_damage_reduction(run, self, decision, choices)
        elif decision.kind == DAMAGE_OPTION:
            base, orders, reduction, optional = resume_damage_option(run, self, decision, choices)  # v0.119
        else:
            base, orders, reduction = resume_step_order(run, self, decision, choices)
            optional = carried_optional(run)
        self._deal(run, located[0], located[2], base, orders, reduction, optional)


@dataclass(frozen=True)
class TargetHeal(Element):
    """先に選んだ個体（``ChooseEffectTarget`` の ``chosen``）から、ダメージカウンターを ``counters`` 個（のっている数まで）とりのぞく（v0.89。ベロリンガの「きずをなめる」）。

    - 0 個のポケモンは効果を受けない（GR-2000-P320-RECOVERY）。このワザで HP 以上のポケモン・場をはなれたポケモンは飛ばす（p.309）
    - とりのぞく前に「ワザをうけない」状態・「とうめい」を評価する（``reaches`` の ``heal``。自分のポケモンでも。v0.41 の ``HealCounters`` と同じ）。ログ ``attack_heal``
      （相手のポケモンなら ``attacker`` つき）
    - 説明に「ダメージカウンターののっている」の条件はないので、選ぶ要素の選べるものは場のポケモンのすべて（v0.85 のあまいかおりの条件を持ち込まない）
    - v0.104: ``every`` なら、のっているすべて（``counters`` の代わり。キレイハナの「あまいみつ」。大きな決まった数で表さない）。``side`` は選ぶ要素と同じ場（自分の場だけから選ぶ
      ワザ（``TARGET_SIDE_OWN``）は相手のポケモンに効果を与えないので、``opponent_element`` がない）"""

    counters: int | None = None
    chosen: str = "target"
    gate: tuple | None = None
    every: bool = False  # v0.104
    side: str = E.TARGET_SIDE_BOTH  # v0.104
    phase: ClassVar[Phase] = Phase.EFFECT

    def __post_init__(self) -> None:
        if (self.counters is None) != self.every:
            raise ValueError("とりのぞく数は counters か every のどちらか一方で決める")
        if self.side not in E.TARGET_SIDES:
            raise ValueError(f"選ぶ場 {self.side!r} は未定義")

    @property
    def opponent_element(self) -> str | None:
        return None if self.side == E.TARGET_SIDE_OWN else E.HEAL_ELEMENT

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        found = chosen_pokemon(run, self.chosen)
        if not found:
            return False
        state = run.state
        target = found[0]
        owner = state.find_pokemon(target.pokemon_id)[0]
        if run.knocked_out(target):
            return False
        per = state.rules.damage_per_counter
        removed = target.damage // per if self.every else min(self.counters, target.damage // per)
        if removed <= 0 or not reaches(run.res, run.fs, owner, target, E.HEAL_ELEMENT):
            return False
        before = target.damage
        target.damage = before - removed * per
        extra = {} if owner == run.player else {"attacker": run.player}
        state.add_event("attack_heal", player=owner, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key), counters=removed,
                        amount=removed * per, damage_before=before, total_damage=target.damage, **extra)
        return False


def typed_units_for(run: AttackRun, pokemon: PokemonInPlay, energy_type: EnergyType) -> int:
    """v0.89: ``pokemon`` についている「``energy_type``」エネルギーの数（エネルギーの個数。``typed_energy_units`` と同じ数え方）。［おいしげる］で個数が決まらないカードは、
    「草」を数えるときだけ止める（ほかの色の数は変わらない。v0.85 の ``wild_growth_question`` を、関係のない色の数え方に当てはめない）。"""
    transform_energy_question(run, pokemon, energy_type, cards=False, wild=energy_type is EnergyType.GRASS)
    return E.typed_unit_count(run.state, pokemon, energy_type)


def definite_typed_units(run: AttackRun, pokemon: PokemonInPlay, energy_type: EnergyType) -> int:
    """v0.89: どの読み方（TE1・RB1・BZ2・MEC1・CE1・CE2・［おいしげる］）でも「``energy_type``」エネルギーとして数える個数（いちばん少ない読み方の数）。読み方が決まらないカード
    （レインボーエネルギー・［エネエネ］・ミラクルエネルギー）は 0、色を変える効果で読み方が分かれるカードはいちばん少ない数。［へんしん］（TE1）は数える読み方のほうが多いので
    今の数。［おいしげる］で 2 個かが決まらないカードは印刷のとおり（``energy_units``）。"""
    state = run.state
    unsure = set(E.ambiguous_rainbow_cards(state, pokemon, energy_type)) | set(E.converted_energy_cards(state, pokemon, energy_type)) | set(
        E.ambiguous_miracle_cards(state, pokemon, energy_type))
    wanted = frozenset({energy_type})
    total = 0
    for uid in pokemon.energy:
        if uid in unsure:
            continue
        printed = sum(1 for unit in E.energy_units(state, pokemon, uid) if unit == wanted)
        readings = [sum(1 for unit in reading if unit == wanted) for reading in E.card_color_readings(state, pokemon, uid)]
        total += min([printed, *readings])
    return total


@dataclass(frozen=True)
class OwnTypedEnergyTimesCapped:
    """自分（ワザを使ったポケモン）についている「``energy_type``」エネルギーの数 × ``per``。与えることのできるダメージは「``energy_type``」エネルギー ``cap`` 個ぶんまで（v0.89。
    わるいオムナイトの「てっぽうみず」。p.321 の 1 段階。エネルギーの個数で数え、カードの枚数ではない）。

    - 数え方の読み方（TE1・RB1・BZ2・MEC1・CE1・CE2）で数が変わっても、どの読み方でも ``cap`` 個以上（``definite_typed_units``）なら、上限で同じ量になるので止めない。そうでなければ
      今までどおり、読み方で数が変わるなら止める（``typed_units_for``）"""

    energy_type: EnergyType
    per: int
    cap: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        attacker = run.attacker()
        if definite_typed_units(run, attacker, self.energy_type) >= self.cap:
            return self.cap * self.per
        return min(typed_units_for(run, attacker, self.energy_type), self.cap) * self.per


@dataclass(frozen=True)
class TargetTypedEnergyTimes:
    """選んだ個体（``chosen``）についている「``energy_type``」エネルギーの数 × ``per``（v0.89。ライチュウの「ろうでん」。p.321 の 1 段階。エネルギーの個数）。数え方の読み方で
    数が変わるなら止める（``typed_units_for``）。"""

    energy_type: EnergyType
    per: int
    chosen: str = "target"
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        found = chosen_pokemon(run, self.chosen)
        if not found:
            raise RuntimeError("エネルギーを数える選んだ個体がいない（エンジンの不具合）")
        return typed_units_for(run, found[0], self.energy_type) * self.per

    def choice_problem(self, run: AttackRun, pokemon: PokemonInPlay) -> tuple[str, str] | None:
        """選ぶ前に、このポケモンの「X」エネルギーの数え方が決まらないか（決まらなければ、そのポケモンを選ぶと止める。ほかのポケモンを選ぶ答えは止めない）。"""
        try:
            typed_units_for(run, pokemon, self.energy_type)
        except OpenQuestion as question:
            return question.key, question.detail
        return None


@dataclass(frozen=True)
class HeadsPerOwnTypedEnergy:
    """自分（ワザを使ったポケモン）についている「``energy_type``」エネルギーの数だけコインを投げ、「おもて」の数 × ``per``（v0.89。ナッシーの「ねらいだま」。エネルギーの個数。
    0 個なら投げず 0）。「おもて」の数だけを使うので、先読みは「おもて」の数でまとめる（v0.35）。実際の対戦は 1 枚ずつ投げる。"""

    energy_type: EnergyType
    per: int
    by_heads: ClassVar[bool] = True

    def coin_count(self, run: AttackRun) -> int:
        return typed_units_for(run, run.attacker(), self.energy_type)

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return (0 if flips is None else flips.heads) * self.per


def chosen_damage(base: Any, *, side: str = E.TARGET_SIDE_OPPONENT, scope: str = E.TARGET_IN_PLAY, chooser: str = E.CHOOSER_ATTACKER,
                  gate: tuple | None = None, local_coin: CoinSide | None = None, required: bool = False, **damage: Any) -> tuple[Element, Element]:
    """選ぶ要素と、選んだ個体へのダメージの要素の組（v0.89。同じ ``side``・``scope``・``gate`` を両方に書く）。"""
    return (ChooseTarget(side=side, scope=scope, chooser=chooser, gate=gate, local_coin=local_coin, required=required),
            TargetDamage(base, side=side, scope=scope, gate=gate, **damage))


BUILDERS |= {
    E.ChooseOpponentPokemonDamageIgnoringEffects: lambda e: chosen_damage(Fixed(e.damage), defender_effects=False, ignore_scope=IGNORE_UNSTATED),
    E.ChooseOpponentPokemonOwnEnergyDamage: lambda e: chosen_damage(OwnTypedEnergyTimesCapped(e.energy_type, e.per, e.cap)),
    E.ChooseOpponentBenchThenCoinDamage: lambda e: chosen_damage(Fixed(e.damage), scope=E.TARGET_BENCH, required=True, local_gate=HEADS),
    E.DamageThenChooseBenchCoinDamage: lambda e: (Damage(OPP, Printed()), *chosen_damage(Fixed(e.bench_damage), scope=E.TARGET_BENCH, local_gate=HEADS)),
    E.ChooseOpponentPokemonCoinsDamage: lambda e: chosen_damage(HeadsTimes(e.coins, e.per)),
    E.ChooseOpponentPokemonTargetEnergyDamage: lambda e: chosen_damage(TargetTypedEnergyTimes(e.energy_type, e.per)),
    E.ChooseOpponentPokemonDamageThenDiscardEnergyOnHeads: lambda e: (
        *chosen_damage(Fixed(e.damage)), DiscardOpponentEnergy(local_coin=HEADS, chosen="target"),
    ),
    E.CoinChooseEitherPokemonHeal: lambda e: (
        Coin("coin"), ChooseEffectTarget(side=E.TARGET_SIDE_BOTH, gate=("coin", HEADS)), TargetHeal(e.counters, gate=("coin", HEADS)),
    ),
    E.ChooseOpponentPokemonCoinsPerOwnEnergyDamage: lambda e: chosen_damage(HeadsPerOwnTypedEnergy(e.energy_type, e.per)),
    E.CoinChooseOpponentPokemonDamageApplyingWR: lambda e: chosen_damage(Fixed(e.damage), local_coin=HEADS, weakness_resistance=True),
    E.CoinActiveElseChosenBenchDamage: lambda e: (
        Coin("coin"), Damage(OPP, Fixed(e.damage), gate=("coin", HEADS)),
        *chosen_damage(Fixed(e.bench_damage), scope=E.TARGET_BENCH, gate=("coin", TAILS),
                       chooser=E.CHOOSER_OPPONENT if e.opponent_chooses else E.CHOOSER_ATTACKER, wr_unstated=e.opponent_chooses),
    ),
    E.CoinChooseBenchElseSelfDamage: lambda e: (
        Coin("coin"), Damage(OPP, Printed()), *chosen_damage(Fixed(e.bench_damage), scope=E.TARGET_BENCH, gate=("coin", HEADS)),
        Damage(SELF, Fixed(e.self_damage), name="self_damage", gate=("coin", TAILS)),
    ),
    E.DamageThenTailsChooseOwnPokemonDamage: lambda e: (
        Coin("coin"), Damage(OPP, Printed()), *chosen_damage(Fixed(e.own_damage), side=E.TARGET_SIDE_OWN, gate=("coin", TAILS)),
    ),
}


# ---------------------------------------------------------------- v0.90（docs/markers-counters-v0.90.md）: マーカー・ダメージカウンター以外のカウンター


def _marker_label(kind: str) -> str:
    return {MARKER_STICKY: "ベトベトマーカー", COUNTER_BONE: "ほねカウンター", COUNTER_FOOD: "たべものカウンター", MARKER_CURSE: "のろいマーカー",
            MARKER_COLOR: "色マーカー", MARKER_CHAR: "くろこげマーカー", MARKER_LIGHTNING_ROD: "ひらいしんマーカー"}[kind]


@dataclass(frozen=True)
class PlaceMarker(Element):
    """``target``（相手の対戦ポケモン ``OPP``・ワザを使ったポケモン自身 ``SELF``）に、種類 ``kind`` のマーカー・カウンターを 1 つのせる（v0.90。``markers.add_marker``）。

    - ``if_absent``: 「…がのっていなければ、1つのせる」（ベトベトえき・ほねさがし）。のっていれば何もしない（コイン・「とうめい」の評価もしない。ログも残さない）
    - ``limit``: 説明が「…が ``limit`` つのっている時、このワザは使えない」と書く数（たべるの 2）。ワザを使うための条件は実装の ``usage_problem``。相手のワザとして使うときは
      ``copy_problem``（まねたポケモンの数を読む）。ここに来てその数なら、確かめの漏れ（エンジンの不具合）
    - ``local_coin``: この要素のコイン（あくまののろい）。相手への効果だけを決めるので、前の要素の「とうめい」で受けないと決まっていれば T19b、「ワザをうけない」状態なら HC3 で
      コインの前に止める（``effect_coin_questions``。v0.76 と同じ順番）。``gate``: ワザ全体のコインの面（ペイント）
    - ``color``: 色を選んだ要素（``ChooseColor``）の結果の名前。色マーカーは、のっているものを取りのぞいて新たにのせる（``markers.replace_marker``）。選ばなかったら何もしない
    - 対象がこのワザで HP 以上になっていれば何もしない（p.309。こんじょうを使えるなら G37）。相手への効果・自分への効果のどちらも、のせる直前に「ワザをうけない」状態・「とうめい」を
      評価する（``reaches``。自分のワザでもはたらく。v0.9 の T8・v0.17b の ``Status`` と同じ）。うらのカード（マチスの秘策）は、そのときおもてにする
    - のせたプレイヤーはワザを使ったプレイヤー、発生源はワザを使ったポケモンのいちばん上のカード、ワザは処理したワザ（相手のワザとして使ったなら、まねたワザ）"""

    kind: str
    target: str = OPP
    if_absent: bool = False
    limit: int | None = None
    local_coin: CoinSide | None = None
    gate: tuple | None = None
    color: str | None = None
    # v0.91: 先に選んだ個体（``ChooseEffectTarget`` の結果の名前）にのせる（エレブーの「ひらいしん」・ポリゴンの「ハイパーテクスチャー」）。``target`` は読まない。選んだ個体が
    # 場をはなれていれば何もしない（同じ位置に出た別のポケモンにのせない）
    chosen: str | None = None
    phase: ClassVar[Phase] = Phase.EFFECT

    def __post_init__(self) -> None:
        if self.target not in (OPP, SELF):
            raise ValueError(f"マーカーをのせる対象 {self.target!r} は相手の対戦ポケモンか自分")
        if (self.kind == MARKER_COLOR) != (self.color is not None):
            raise ValueError("色マーカーだけが、のせる色を選んだ結果を読む")
        if self.chosen is not None and (self.limit is not None or self.local_coin is not None):
            raise ValueError("選んだ個体にのせる要素は、数の上限・この要素のコインを持たない")

    @property
    def opponent_element(self) -> str | None:
        return E.MARKER_ELEMENT if self.target == OPP or self.chosen is not None else None

    def coin_receiver(self) -> str | None:
        return "effect" if self.target == OPP and self.chosen is None else None

    def receiver(self, run: AttackRun) -> tuple[int, PokemonInPlay] | None:
        if self.chosen is not None:
            picked = chosen_pokemon(run, self.chosen)
            return None if not picked else run.state.find_pokemon(picked[0].pokemon_id)
        return (1 - run.player, run.opponent_active()) if self.target == OPP else (run.player, run.attacker())

    def has_target(self, run: AttackRun) -> bool:
        found = self.receiver(run)
        if found is None:
            return False  # v0.91: 選ばなかった・選んだ個体が場をはなれた
        owner, target = found
        if run.knocked_out(target):
            run.ko_prevention_conflict(target, owner)
            return False
        return not (self.if_absent and has_marker(target, self.kind))

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        if self.limit is not None and marker_count(copier, self.kind) >= self.limit:
            what = f"「{_marker_label(self.kind)}」が {self.limit} つのっている（このワザは使えない）"
            return (ILLEGAL, what) if clause in (CANNOT_USE, FOLLOW_TEXT) else (UNRESOLVED, f"{what}（ワザを使うための条件）")
        return None

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        found = self.receiver(run)
        if found is None:
            return False  # v0.91: 選ばなかった・選んだ個体が場をはなれた
        owner, target = found
        if run.knocked_out(target):
            run.ko_prevention_conflict(target, owner)
            return False
        if self.limit is not None and marker_count(target, self.kind) >= self.limit:
            raise RuntimeError(f"「{_marker_label(self.kind)}」が {self.limit} つのっているのに、ワザ {run.key} の要素に来た（使うための条件の確認の漏れ。エンジンの不具合）")
        if self.if_absent and has_marker(target, self.kind):
            return False  # 「のっていなければ」。のっているので何もしない（数を増やさない）
        if self.local_coin is not None:
            if self.target == OPP:
                effect_coin_questions(run, owner, target)
            if run.flip(1).results[0] is not self.local_coin:
                return False
        color = None
        if self.color is not None:
            chosen = run.fs.results.get(self.color)
            if chosen is None:
                raise RuntimeError(f"色を選んだ結果 {self.color!r} がない（要素の並びの誤り。エンジンの不具合）")
            if not isinstance(chosen, ChosenColor):
                raise TypeError(f"色を選んだ結果 {self.color!r} が {type(chosen).__name__}（ChosenColor でない。エンジンの不具合）")
            if chosen.color is None:
                return False
            color = chosen.color
        if not reaches(run.res, run.fs, owner, target, E.MARKER_ELEMENT):
            return False
        marker = Marker(self.kind, run.player, run.attacker().card, str(run.key), run.state.turn_number, color)
        if self.kind == MARKER_COLOR:
            replace_marker(run.state, owner, target, marker)
        else:
            add_marker(run.state, owner, target, marker)
        return False


@dataclass(frozen=True)
class RemoveOwnMarkers(Element):
    """ワザを使ったポケモン自身にのっている種類 ``kind`` を ``count`` 個取りのぞく（v0.90。ガラガラの「ほねこんぼう」の「それを1つとりのぞいて」。ログ ``marker_removed`` の
    ``reason`` ``used``）。

    - ``required``: 説明が「このワザは、このカードに…がのっている時だけ、使える」と書く（ワザを使うための条件は実装の ``usage_problem``。相手のワザとして使うときは
      ``copy_problem``（まねたポケモンの数を読む））。のっているかの確かめ（宣言の前）と、取りのぞく時点（ワザの効果。こんらん・すなかけでワザが失敗したら取りのぞかない）を分ける
    - ワザを使ったポケモンがこのワザで HP 以上なら何もしない（p.309。きぜつでなくなる）。ここに来て数が足りなければ、確かめの漏れ（エンジンの不具合）"""

    kind: str
    count: int = 1
    required: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        if self.required and marker_count(copier, self.kind) < self.count:
            what = f"「{_marker_label(self.kind)}」がのっていない（このワザは、のっている時だけ使える）"
            return (ILLEGAL, what) if clause in (CANNOT_USE, FOLLOW_TEXT) else (UNRESOLVED, f"{what}（ワザを使うための条件）")
        return None

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            return False
        if marker_count(attacker, self.kind) < self.count:
            raise RuntimeError(f"ワザ {run.key} で取りのぞく「{_marker_label(self.kind)}」が {self.count} 個ない（使うための条件の確認の漏れ。エンジンの不具合）")
        remove_markers(run.state, run.player, attacker, MARKERS_USED, kinds=(self.kind,), count=self.count, effect=str(run.key))
        return False


@dataclass(frozen=True)
class MarkersRemoved:
    """v0.90: ``OptionalRemoveOwnMarkers`` の結果（取りのぞいた数）。"""

    count: int


@dataclass(frozen=True)
class OptionalRemoveOwnMarkers(Element):
    """のぞむなら、ワザを使ったポケモン自身にのっている種類 ``kind`` を ``maximum`` 個まで（None ならのっている数まで）取りのぞく（v0.90。カラカラの「ボーンキラー」（1 つ）・
    くいしんぼカビゴンの「ころがる」（好きなだけ））。結果は ``MarkersRemoved``（ダメージの値 ``PlusPerRemovedMarkers`` が数える）。

    - 決定 ``SELECT_MARKER_COUNT``（選べるものは 0〜上限の数。0 は「のぞむなら」の、取りのぞかないこと。ログ ``marker_removal_declined``）。のっていなければ決定を出さない（0）
    - ダメージより先（追加するダメージが取りのぞいた数で決まる。v0.82 のファイヤーバーンと同じ）。上限は説明の数とのっている数だけで決め、相手の残りHP・相手がダメージを受けるかで
      しぼらない。自分への効果なので「ワザをうけない」状態・「とうめい」を評価しない（v0.30 の自分のエネルギーのトラッシュと同じ）
    - 取りのぞくのは答えのあと 1 回だけ（決定のあとのダメージの要素の決定（順番・お上品攻撃）は、基本となるダメージを続きの情報で運ぶので、取りのぞき直さない）"""

    kind: str
    maximum: int | None = None
    name: str = "removed_markers"
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_MARKER_COUNT

    def top(self, run: AttackRun) -> int:
        present = marker_count(run.attacker(), self.kind)
        return present if self.maximum is None else min(self.maximum, present)

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            raise RuntimeError(f"ワザ {run.key} を使ったポケモンが、ダメージの前に HP 以上（エンジンの不具合）")
        top = self.top(run)
        if top == 0:
            run.fs.results[self.name] = MarkersRemoved(0)
            return False
        run.suspend(kind=SELECT_MARKER_COUNT, player=run.player, options=tuple(range(top + 1)), extra=(("marker", self.kind),))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if decision.kind != SELECT_MARKER_COUNT or len(choices) != 1 or choices[0] not in decision.options or choices[0] > self.top(run):
            raise RuntimeError(f"取りのぞく数の答え {choices!r} が、選べる数ではない（エンジンの不具合）")
        count = choices[0]
        attacker = run.attacker()
        if count:
            remove_markers(run.state, run.player, attacker, MARKERS_USED, kinds=(self.kind,), count=count, effect=str(run.key))
        else:
            run.state.add_event("marker_removal_declined", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, marker=self.kind,
                                effect=str(run.key))
        run.fs.results[self.name] = MarkersRemoved(count)


@dataclass(frozen=True)
class PlusPerRemovedMarkers:
    """ダメージの目安の数字 + 前の要素 ``removed`` で取りのぞいた数 × ``per``（v0.90。ボーンキラー・ころがる。p.321 の 1 段階の「基本となるダメージ」に加える）。"""

    removed: str
    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        result = run.fs.results.get(self.removed)
        if result is None:
            raise RuntimeError(f"取りのぞいた数の結果 {self.removed!r} がない（要素の並びの誤り。エンジンの不具合）")
        if not isinstance(result, MarkersRemoved):
            raise TypeError(f"取りのぞいた数の結果 {self.removed!r} が {type(result).__name__}（MarkersRemoved でない。エンジンの不具合）")
        return run.attack.damage + result.count * self.per


@dataclass(frozen=True)
class ClearOwnMarkers(Element):
    """ワザを使ったポケモン自身にのっているマーカー（``MARKER_KINDS``。名前が「…マーカー」）をすべて取りのぞく（v0.90。ミュウツーの「かんぜんかいふく」の「自分にのっている
    ダメージカウンターやマーカーをすべて取りのぞき」のマーカーの部分。ダメージカウンターは前の ``HealAllCounters``）。ログ ``marker_removed`` の ``reason`` ``cleared``。

    ダメージカウンター以外のカウンター（ほねカウンター・たべものカウンター）がのっていれば、「ダメージカウンターやマーカー」に含むかが決まらない（KR1）ので止める（相手のワザとして
    使う・［へんしん］のメタモンで起こる。先読みが宣言の前に見つける）。持続する効果・特殊能力の記録・色を変えた記録（［へんしょく］・［せんすい］）は「マーカー」ではないので変えない"""

    phase: ClassVar[Phase] = Phase.EFFECT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        # 相手のワザとして使うとき、まねたポケモンにカウンターがあれば、選べるが選ぶと止める（KR1 の理由。宣言のすべてを止めない）
        counters = [m.kind for m in copier.markers if m.kind in COUNTER_KINDS]
        if counters:
            return UNRESOLVED, f"{'・'.join(_marker_label(k) for k in dict.fromkeys(counters))}を「ダメージカウンターやマーカー」に含むか決まらない（KR1）"
        return None

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            return False
        counters = [m.kind for m in attacker.markers if m.kind in COUNTER_KINDS]
        if counters:
            raise run.res.question("full_recovery_counters", f"ポケモン {attacker.pokemon_id}（{'・'.join(_marker_label(k) for k in dict.fromkeys(counters))}）")
        remove_markers(run.state, run.player, attacker, MARKERS_CLEARED, kinds=MARKER_KINDS, effect=str(run.key))
        return False


@dataclass(frozen=True)
class CureOwnConditions(Element):
    """ワザを使ったポケモン自身を、説明が書く特殊状態（``names``）だけから回復させる（v0.90。かんぜんかいふくの「「どく・こんらん」状態のすべてからも回復させる」。
    ``conditions.cure_conditions``）。ワザを使ったポケモンがこのワザで HP 以上なら何もしない（p.309）。

    v0.104: ``reach`` なら、回復させる特殊状態があるときだけ、回復させる前に「とうめい」などを評価する（``reaches`` の ``cure``。ジュゴンの「ねむる」。同じワザの前の回復（``HealCounters``）・
    あとのねむり（``Status``）と同じく、自分への効果の受ける判定を通す。1 匹 1 回で投げ直さない）。v0.90 のかんぜんかいふく（``HealAllCounters`` のあと）は今までどおり評価しない"""

    names: tuple[str, ...]
    reach: bool = False  # v0.104
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            return False
        if self.reach and (not any(name in self.names for name in attacker.conditions.names())
                           or not reaches(run.res, run.fs, run.player, attacker, E.CURE_ELEMENT)):
            return False
        cure_conditions(run.state, run.player, attacker, self.names, effect=str(run.key))
        return False


BUILDERS |= {
    E.MarkOpponentIfAbsent: lambda e: (PlaceMarker(e.kind, OPP, if_absent=True),),
    E.MarkSelfIfAbsent: lambda e: (PlaceMarker(e.kind, SELF, if_absent=True),),
    E.MarkSelfUpToLimit: lambda e: (PlaceMarker(e.kind, SELF, limit=e.limit),),
    E.CoinMarkOpponent: lambda e: (PlaceMarker(e.kind, OPP, local_coin=HEADS),),
    E.CoinPaintOpponent: lambda e: (Coin("coin"), ChooseColor(COLOR_ANY, gate=("coin", HEADS)), PlaceMarker(MARKER_COLOR, OPP, gate=("coin", HEADS), color="color")),
    E.DamageThenRemoveOwnMarkerParalyzeOnHeads: lambda e: (
        Damage(OPP, Printed()), RemoveOwnMarkers(e.kind, required=True), Status(PARALYSIS, local_coin=HEADS, reparalysis_check=True),
    ),
    E.OptionalRemoveOwnMarkersBonusDamage: lambda e: (
        OptionalRemoveOwnMarkers(e.kind, e.maximum), Damage(OPP, PlusPerRemovedMarkers("removed_markers", e.per)),
    ),
    E.DiscardAllEnergyThenFullRecovery: lambda e: (
        DiscardOwnEnergy(None, count=None), HealAllCounters(), ClearOwnMarkers(), CureOwnConditions(e.conditions),
    ),
}


# ---------------------------------------------------------------- v0.91（docs/marker-check-field-reset-v0.91.md）: 選んだ個体のマーカー・マーカーのポケモンへのダメージ・オールクリア


@dataclass(frozen=True)
class RemoveChosenMarker(Element):
    """先に選んだ個体（``chosen``）にのっている種類 ``kind`` を取りのぞく（v0.91。ポリゴンの「ハイパーテクスチャー」の「そのポケモンに「色マーカー」がのっているなら、それを
    とりのぞき」。ログ ``marker_removed`` の ``reason`` ``replaced``）。結果は ``MarkersRemoved``（取りのぞいた数。あとの ``ChooseColor(requires)`` が読む）。

    - ``question``: のっていないポケモンを選ぶと止める問い（HX1）。選ぶ要素（``ChooseTarget``）の ``choice_problem`` として返すので、選べるが選ぶと止める（どれものっていなければ
      選ぶ前に止める）
    - 相手のポケモンへの効果なので、取りのぞく前に「ワザをうけない」状態・「とうめい」を評価する（``reaches``。受けないなら、あとの色を選ぶ・のせるもしない）
    - 取りのぞいたあと（あとの色を選ぶ決定のあいだ）の状態が受け付けられない（決められない姿など。``effects.attack_state_stop_after``）なら止める（宣言の前に先読みが見つける）"""

    kind: str
    chosen: str = "target"
    name: str = "removed_marker"
    question: str | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.MARKER_ELEMENT

    def choice_problem(self, run: AttackRun, owner: int, pokemon: PokemonInPlay) -> tuple[str, str] | None:
        if self.question is not None and not has_marker(pokemon, self.kind):
            return self.question, f"ポケモン {pokemon.pokemon_id}（{_marker_label(self.kind)}がのっていない）"
        return None

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        # 相手のワザとして使うとき、選べるどのポケモンにものっていなければ、選べるが選ぶと止める（HX1 の理由。宣言のすべては止めない。v0.90 の KR1 と同じ書き方）
        candidates = E.target_candidates(run.state, run.player, E.TARGET_SIDE_OPPONENT, E.TARGET_IN_PLAY)
        if self.question is not None and candidates and not any(has_marker(pokemon, self.kind) for _, pokemon in candidates):
            return UNRESOLVED, f"選べるポケモンのどれにも{_marker_label(self.kind)}がのっていない（HX1）"
        return None

    def run(self, run: AttackRun) -> bool:
        run.fs.results[self.name] = MarkersRemoved(0)
        picked = chosen_pokemon(run, self.chosen)
        if not picked:
            return False  # 選ばなかった・選んだ個体が場をはなれた
        owner, target = run.state.find_pokemon(picked[0].pokemon_id)
        if run.knocked_out(target):
            run.ko_prevention_conflict(target, owner)
            return False
        if not has_marker(target, self.kind):
            if self.question is not None:
                raise run.res.question(self.question, f"ポケモン {target.pokemon_id}（{_marker_label(self.kind)}がのっていない）")
            return False
        if not reaches(run.res, run.fs, owner, target, E.MARKER_ELEMENT):
            return False
        before = run.state.peek()
        removed = remove_markers(run.state, owner, target, MARKERS_REPLACED, kinds=(self.kind,), effect=str(run.key))
        stop = E.attack_state_stop_after(before, run.state)
        if stop is not None:
            raise UnsupportedError(*stop)
        run.fs.results[self.name] = MarkersRemoved(removed)
        return False


def damage_units_difference(run: AttackRun, owner: int, receiver: PokemonInPlay, first: int, second: int) -> str | None:
    """v0.91（HR1）: 相手の対戦ポケモン ``receiver`` が 1 つのワザで基本となるダメージ ``first``（目安）と ``second`` の 2 つを受けるとき、2 つを別々に計算する読み方（v0.40 の
    NE3 と同じ。p.321 の段階をダメージごとに）と、合わせて 1 つのダメージとして計算する読み方で、受けるダメージか「ダメージを受けたとき」「ダメージを受ける時」の効果が変わるなら、その
    違い（理由の文の一部）。変わらなければ None。状態を変えず、乱数を使わない。どちらの読み方でもダメージの要素が無効なら変わらない。"""
    from ..persistent import tails_damage_guard
    from .kernel import (
        _receiving_candidates,
        attack_modifiers_of,
        compute_damage,
        deferred_receivers,
        first_void,
        with_stadium_coin,
    )

    res, fs, state = run.res, run.fs, run.state
    if first_void(res, run.incoming(), owner, receiver) is not None:
        return None
    attacker = run.attacker()
    modifiers = with_stadium_coin(res, fs.frame, OPP, attack_modifiers_of(res, fs.frame, attacker, receiver, OPP))
    try:
        separate = (compute_damage(state, attacker, receiver, first, modifiers).final, compute_damage(state, attacker, receiver, second, modifiers).final)
        combined = compute_damage(state, attacker, receiver, first + second, modifiers).final
    except (DamageOrderRequired, DamageReductionRequired, DamageOptionRequired):
        return "計算に決定（同じ段階の順番・お上品攻撃の減らす量・受けるポケモンの使うかを選ぶ効果）が要る"
    except E.TypeReadingsDiffer as differ:
        raise type_question(res, differ, f"ワザ {run.key} の相手の対戦ポケモンへのダメージ") from None
    if sum(max(value, 0) for value in separate) != max(combined, 0):
        return f"別々に計算すると {separate[0]}・{separate[1]}、合わせて計算すると {combined}"
    if tails_damage_guard(receiver) is not None:
        return "かげぶんしん（ダメージを受ける時のコイン）を受けている"
    if deferred_receivers(res, fs.frame, owner, receiver) or any(True for _ in _receiving_candidates(res, fs.frame, owner, receiver)):
        return "「ダメージを受けたとき」「ダメージを受ける時」の効果がある"
    return None


@dataclass(frozen=True)
class DamageUnitsCheck(Element):
    """v0.91（HR1）: 相手の対戦ポケモンに種類 ``kind`` のマーカーがのっていれば、目安のダメージ（``Printed``）と ``extra`` の 2 つを受ける（エレブーの「かみなりショック」）。
    2 つを別々に計算するか、合わせて計算するかで結果が変わるなら、ダメージを与える前に止める（``damage_units_difference``。先読みが宣言の前に見つける）。何も処理しない。"""

    kind: str
    extra: Any
    phase: ClassVar[Phase] = Phase.DAMAGE

    def run(self, run: AttackRun) -> bool:
        defender = run.opponent_active()
        if defender is None or run.state.is_face_down(defender) or not has_marker(defender, self.kind):
            return False
        difference = damage_units_difference(run, 1 - run.player, defender, run.attack.damage, self.extra.value(run, None))
        if difference is not None:
            raise run.res.question("lightning_bolt_units", f"ポケモン {defender.pokemon_id}（{_marker_label(self.kind)}）: {difference}")
        return False


def _field_pokemon(run: AttackRun) -> list[tuple[int, PokemonInPlay]]:
    """v0.91: おたがいの場のポケモン（ワザを使ったプレイヤーの場 → 相手の場。それぞれバトル場 → ベンチ）。うらのカード（マチスの秘策）は除く（全体にはたらく効果ではおもてに
    しない。v0.67 の 4 章。うらのあいだはトレーナー・特殊状態・持続する効果・マーカーがない）。"""
    state = run.state
    return [(owner, pokemon) for owner in (run.player, 1 - run.player) for pokemon in state.players[owner].in_play() if not state.is_face_down(pokemon)]


def _raise_state_stop(before: GameState, after: GameState) -> None:
    """v0.91: ``effects.attack_state_stop_after``（決められない姿・［ずらかる］の力がもどる）なら止める。最大HP が下がるのはワザのあとのきぜつの判定で扱う。"""
    stop = E.attack_state_stop_after(before, after)
    if stop is not None:
        raise UnsupportedError(*stop)


# v0.91: オールクリアの「その他の効果」に含むかが記録から決まらない、ポケモンに写していない効果（プレイヤーに与えた効果で、この番のあとも続くもの）の種類。この番で消えるもの
# （カスミ・キョウ・カツラ・退化スプレーHYPER・特殊能力で色を変える効果・エナジーバーン）は、ワザで番が終わるので、消すかどうかで結果が変わらない（docs 7.3 節）
ALL_CLEAR_UNDECIDED_FIELD_EFFECTS = (BENCH_ATTACK_DAMAGE_PREVENTION, POWER_SUPPRESSION, OPPONENT_POWER_SUPPRESSION,
                                     ATTACK_FIELD_POWER_SUPPRESSION)  # v0.92: やみのはどう（次の相手の番の終わりまで）


def all_clear_question(run: AttackRun) -> None:
    """v0.91: オールクリアで、記録から決まらず結果が変わる場面なら問いで止める（状態を変えない）。

    - ZC1: 「その他の効果」に含むかが決まらない効果がある（［へんしょく］で色を変えた記録、この番のあとも続く見えない壁・まきちらせ!ベトベトガス・ふしぎなガスの効果）
    - ZC3: 場になにかの化石のカードがある（「場に出ている限りポケモンとしてあつかわれる」が、「トレーナーカード」でもあるかは書かれていない。ピッピ人形は「場に出ているとき以外は、
      トレーナーカードとしてあつかう」ので、場ではトレーナーカードではない）"""
    state = run.state
    shifted = [pokemon.pokemon_id for _, pokemon in _field_pokemon(run) if pokemon.type_shift is not None]
    lasting = [record.kind for record in state.trainer_effects if record.kind in ALL_CLEAR_UNDECIDED_FIELD_EFFECTS and record.expires_turn > state.turn_number]
    if shifted or lasting:
        raise run.res.question("all_clear_other_effects", f"［へんしょく］で色を変えたポケモン {shifted}・続く効果 {lasting}")
    fossils = [pokemon.pokemon_id for _, pokemon in _field_pokemon(run) if any(state.in_play_def(uid).play_role == "fossil" for uid in pokemon.cards())]
    if fossils:
        raise run.res.question("all_clear_fossil", f"なにかの化石のカードのあるポケモン {fossils}")


@dataclass(frozen=True)
class AllClearPowerSuppression(Element):
    """v0.91: 「このワザを使っているあいだ、おたがいの場にいるすべてのポケモンは「特殊能力」を使うことができず、その力も消える」の期間の始まり（ポリゴンの「オールクリア」）。
    ワザの説明を処理する始め（p.309 の手順 6。宣言・ワザの失敗のコイン・こんらんのコインのあと）に、期限のある効果（``ATTACK_POWER_SUPPRESSION``。ワザの処理のあと・きぜつの
    判定の前に ``flow.end_attack_power_suppression`` が消す）を加える。ログ ``trainer_effect_added``。

    - 始める前に、ZC1・ZC3（``all_clear_question``）と、ワザの出どころが特殊能力（［へんしん］・［サイコリンク］など）でそのワザを持たなくなるか（ZC2）を確かめる
    - 特殊能力が消えたあとの状態が受け付けられない（「ばける」の DG1 などの決められない姿・［ずらかる］の力がもどる。``effects.attack_state_stop_after``）なら止める（宣言の前に
      先読みが見つける）。最大HP が変わるのは、ワザのあとのきぜつの判定（期間が終わったあと）で扱う（途中できぜつの判定はしない。p.309・p.323）"""

    phase: ClassVar[Phase] = Phase.EFFECT

    def record(self, run: AttackRun) -> TrainerTurnEffect:
        turn = run.state.turn_number
        return TrainerTurnEffect(kind=ATTACK_POWER_SUPPRESSION, player=run.player, source_card=run.attacker().card, card_id=run.key.card_id, created_turn=turn,
                                 expires_turn=turn, attack_index=run.key.attack_index)

    def run(self, run: AttackRun) -> bool:
        state = run.state
        all_clear_question(run)
        record = self.record(run)
        if any(r.kind == ATTACK_POWER_SUPPRESSION for r in state.trainer_effects):
            raise RuntimeError("ワザを使っているあいだの特殊能力の抑止が、すでにある（ワザの処理のあとに消していない。エンジンの不具合）")
        trial = state.peek()
        trial.trainer_effects = trial.trainer_effects + (record,)
        attacker = run.attacker()
        held = [option for option in E.available_attacks(state, attacker) if option.key == run.declared]
        kept = [option for option in E.available_attacks(trial, trial.find_pokemon(attacker.pokemon_id)[1]) if option.key == run.declared]
        if held and {(o.card, o.route) for o in kept} != {(o.card, o.route) for o in held}:
            raise run.res.question("all_clear_attack_source", f"ポケモン {attacker.pokemon_id}・宣言したワザ {run.declared}（{[o.route for o in held]}）")
        _raise_state_stop(state, trial)
        state.trainer_effects = state.trainer_effects + (record,)
        state.add_event("trainer_effect_added", player=run.player, effect_kind=ATTACK_POWER_SUPPRESSION, trainer_card=record.source_card, card_id=record.card_id,
                        expires_turn=record.expires_turn, attack_index=record.attack_index, effect=str(run.key))
        return False


@dataclass(frozen=True)
class DiscardFieldTrainers(Element):
    """v0.91: おたがいの場にある、すべてのトレーナーカードをトラッシュする（オールクリア）。場のポケモン（ワザを使ったプレイヤーの場 → 相手の場。バトル場 → ベンチ）についている
    トレーナーカード（ついている順）→ 場のスタジアム。

    - カードは持ち主（カードの ``owner``）のトラッシュに置く。ついているトレーナーはログ ``discard_attached_trainer``（``reason`` ``attack``・``effect``）、スタジアムは
      ``zones.discard_stadium``（``reason`` ``attack``・``by_card``・``effect``）。エネルギーカード・進化カード・「ばける」のカード・［エネエネ］のカードはトレーナーカードではない
    - 場のピッピ人形（「場に出ているとき以外は、トレーナーカードとしてあつかう」）・うらのカード（「たねポケモン」としてあつかわれる）はポケモンなので、トラッシュしない（場を
      はなれない。なにかの化石は ZC3 で止める）
    - ポケモンごとに「ワザをうけない」状態を評価する（``reaches``。「とうめい」は力が消えているので投げない）。トラッシュしたあとの状態が受け付けられないなら止める"""

    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.TRAINER_DISCARD_ELEMENT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        before = state.peek()
        for owner, pokemon in _field_pokemon(run):
            if not pokemon.trainers or not reaches(run.res, run.fs, owner, pokemon, E.TRAINER_DISCARD_ELEMENT):
                continue
            for attached in list(pokemon.trainers):
                pokemon.trainers.remove(attached)
                card_owner = state.cards[attached.card].owner
                state.players[card_owner].discard.append(attached.card)
                state.add_event("discard_attached_trainer", player=card_owner, card=attached.card, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id,
                                reason="attack", effect=str(run.key))
        if state.stadium is not None:
            discard_stadium(state, state.stadium, reason="attack", by_card=run.attacker().card, effect=str(run.key))
        _raise_state_stop(before, state)
        return False


@dataclass(frozen=True)
class CureAllPokemon(Element):
    """v0.91: おたがいの場にいるポケモン全員を「どく・ねむり・マヒ・こんらん」状態や「その他の効果」から、すべて回復させる（オールクリア）。特殊状態はすべて消し（ログ
    ``special_conditions_removed`` の ``reason`` ``cured``）、ワザによる持続する効果（``persistent_effects``）はすべて消す（ログ ``persistent_effect_removed`` の ``reason``
    ``cured``。p.324 の退化の「その他の「持続する効果」から回復する」と同じ範囲）。ダメージカウンター・マーカー（次の要素）・ついているカード・プレイヤーの記録は変えない
    （docs 7.3 節の表）。ポケモンごとに「ワザをうけない」状態を評価する。回復させたあとの状態が受け付けられないなら止める。"""

    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.CURE_ELEMENT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        before = state.peek()
        for owner, pokemon in _field_pokemon(run):
            if not (pokemon.conditions.names() or pokemon.persistent_effects) or not reaches(run.res, run.fs, owner, pokemon, E.CURE_ELEMENT):
                continue
            if pokemon.conditions.names():
                clear_special_conditions(state, owner, pokemon, CURED, effect=str(run.key))
            if pokemon.persistent_effects:
                remove_persistent_effects(state, owner, pokemon, PERSISTENT_CURED)
        _raise_state_stop(before, state)
        return False


@dataclass(frozen=True)
class ClearAllMarkers(Element):
    """v0.91: おたがいの場にいるポケモン全員から、マーカーとカウンターを、すべてとりのぞく（ダメージカウンターはそのまま。オールクリア）。ほねカウンター・たべものカウンターも
    含む（説明が「マーカーとカウンター」と書く。KR1 のかんぜんかいふくとは書き方が違う）。ログ ``marker_removed`` の ``reason`` ``cleared``。ポケモンごとに「ワザをうけない」状態を
    評価する。とりのぞいたあとの状態が受け付けられないなら止める。"""

    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.MARKER_ELEMENT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        before = state.peek()
        for owner, pokemon in _field_pokemon(run):
            if pokemon.markers and reaches(run.res, run.fs, owner, pokemon, E.MARKER_ELEMENT):
                remove_markers(state, owner, pokemon, MARKERS_CLEARED, effect=str(run.key))
        _raise_state_stop(before, state)
        return False


BUILDERS |= {
    E.DamageThenCoinMarkOpponentIfAbsent: lambda e: (Damage(OPP, Printed()), PlaceMarker(e.kind, OPP, if_absent=True, local_coin=HEADS)),
    E.ChooseOpponentPokemonMarkIfAbsent: lambda e: (ChooseEffectTarget(), PlaceMarker(e.kind, if_absent=True, chosen="target")),
    E.DamageThenMarkedPokemonDamage: lambda e: (
        DamageUnitsCheck(e.kind, Fixed(e.damage)), Damage(OPP, Printed()), Damage(OPP, Fixed(e.damage), name="marker_damage", marker=e.kind),
        Damage(SELF, Fixed(e.damage), name="self_damage", marker=e.kind), BenchDamage(Fixed(e.damage), weakness_resistance=True, marker=e.kind),
        BenchDamage(Fixed(e.damage), weakness_resistance=True, own=True, name="own_bench_damage", marker=e.kind),
    ),
    E.ChooseOpponentPokemonReplaceColorMarker: lambda e: (
        ChooseEffectTarget(), RemoveChosenMarker(MARKER_COLOR, question="hyper_texture_unmarked", name="removed_color"),
        ChooseColor(COLOR_ANY, requires="removed_color"), PlaceMarker(MARKER_COLOR, chosen="target", color="color"),
    ),
    E.AllClear: lambda e: (AllClearPowerSuppression(), DiscardFieldTrainers(), CureAllPokemon(), ClearAllMarkers()),
}


# ---------------------------------------------------------------- v0.92（docs/power-suppression-lasting-locks-v0.92.md）: 能力の消去・続く制限


@dataclass(frozen=True)
class OpponentPeriodLock(Element):
    """相手の対戦ポケモンに、期間と消える契機を明示した「にげる」ことができない効果（``lock`` が ``E.LOCK_RETREAT``。``state.PeriodRetreatLock``）か、ワザを使えない効果
    （``E.LOCK_ATTACK``。``state.PeriodAttackLock``）を与える（v0.92。クモのす・くろいまなざし・ヨーギラスの「にらみつける」）。

    - ``start``・``end``: 与えた番からの番の数（期間の始まり・終わり。``end`` が None なら期限なし）。``while_source_active``・``ends_on``: ``state.PeriodRetreatLock`` と同じ。発生源は
      ワザを使ったポケモン（相手のワザとして使ったときは使ったポケモン。場の番号 ``source_pokemon``）
    - ``local_coin``: この要素のコイン。相手がこのワザで HP 以上なら投げない（p.309。こんじょうを使えるなら G37）。「とうめい」で受けないと決まった相手は T19b、「ワザをうけない」相手は
      HC3（v0.76 の ``effect_coin_questions``）。「うら」なら与えない（ワザの失敗ではない）
    - 相手に与える効果なので「とうめい」・「ワザをうけない」状態を評価する（要素の種類は禁止の種類）。ログ ``persistent_effect_added`` に ``end_turn``・``source_pokemon`` と、あるときだけ
      ``while_source_active``・``ends_on`` を書く

    v0.93（docs/active-leave-locks-v0.93.md）: ``lock`` に ``E.LOCK_LEAVE``（「バトル場をはなれられない」。``state.PeriodLeaveLock``。``knockout_exception`` は「(「きぜつ」した場合を
    のぞく)」。ログにあるときだけ書く）と ``E.LOCK_ATTACK_CHECK``（ワザを使うときのコイン。``state.PeriodAttackCoinCheck``）を加えた。``gate`` はワザ全体のコインの面（クサイハナの
    「ねばるみつ」の 1 枚のコイン。``local_coin`` は None）。v0.92 の登録の値は変えていない"""

    lock: str
    start: int
    end: int | None
    while_source_active: bool = False
    ends_on: tuple[str, ...] = ()
    local_coin: CoinSide | None = None
    knockout_exception: bool = False  # v0.93
    gate: tuple | None = None  # v0.93
    phase: ClassVar[Phase] = Phase.EFFECT

    @property
    def opponent_element(self) -> str:
        return E._period_lock_element(self.lock)

    def coin_receiver(self) -> str | None:
        return "effect"  # v0.93: ワザ全体のコインが決める相手の対戦ポケモンへの効果（``void_coin_question``。ねばるみつ）

    def has_target(self, run: AttackRun) -> bool:
        return not run.knocked_out(run.opponent_active())  # v0.93: このワザで HP 以上なら処理の対象がない（p.309）

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if self.local_coin is not None:
            effect_coin_questions(run, opponent, target)
            if run.flip(1).results[0] is not self.local_coin:
                return False
        if not reaches(run.res, run.fs, opponent, target, self.opponent_element):
            return False
        attacker = run.attacker()
        if (self.while_source_active or self.ends_on) and run.state.players[run.player].active is not attacker:
            raise RuntimeError(f"発生源の場所で決まる効果を与えるポケモン {attacker.pokemon_id} がバトル場にいない（今の写しでは起こらない。エンジンの不具合）")
        turn = run.state.turn_number
        kind = E._period_lock_type(self.lock)
        extra = {"knockout_exception": self.knockout_exception} if self.lock == E.LOCK_LEAVE else {}
        if self.knockout_exception and self.lock != E.LOCK_LEAVE:
            raise RuntimeError(f"きぜつの例外は、バトル場をはなれられない効果だけが持つ（{self!r}。エンジンの不具合）")
        effect = kind(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn + self.start,
                      end_turn=None if self.end is None else turn + self.end, source_pokemon=attacker.pokemon_id,
                      while_source_active=self.while_source_active, ends_on=self.ends_on, **extra)
        add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key), **period_log_fields(effect))
        return False


def period_log_fields(effect) -> dict:
    """v0.92: 期間を明示した持続する効果のログ ``persistent_effect_added`` の項目（期間の終わり・発生源の場の番号。発生源の条件・消える契機はあるときだけ）。v0.93: バトル場を
    はなれられない効果のきぜつの例外も、あるときだけ。"""
    fields: dict = {"end_turn": effect.end_turn, "source_pokemon": effect.source_pokemon}
    if effect.while_source_active:
        fields["while_source_active"] = True
    if effect.ends_on:
        fields["ends_on"] = effect.ends_on
    if getattr(effect, "knockout_exception", False):
        fields["knockout_exception"] = True
    return fields


@dataclass(frozen=True)
class OpponentDamageTakenBonus(Element):
    """相手の対戦ポケモン（このワザを受けた相手）に、与えた番 + ``start``〜+ ``end`` の番、受けるワザによるダメージを ``amount`` 増やす効果（``state.ReceivedAttackDamageBonus``）を
    与える（v0.92。イワーク・ゴルバットの「いやなおと」）。相手に与える効果なので「とうめい」・「ワザをうけない」状態を評価する。相手がこのワザで HP 以上なら与えない。ログ
    ``persistent_effect_added`` に ``end_turn``・``source_pokemon``・``amount``。"""

    amount: int
    start: int
    end: int
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.DAMAGE_TAKEN_ELEMENT

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if not reaches(run.res, run.fs, opponent, target, E.DAMAGE_TAKEN_ELEMENT):
            return False
        attacker = run.attacker()
        turn = run.state.turn_number
        effect = ReceivedAttackDamageBonus(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn + self.start,
                                           end_turn=turn + self.end, source_pokemon=attacker.pokemon_id, amount=self.amount)
        add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key), amount=self.amount, **period_log_fields(effect))
        return False


# きぜつの判定・きぜつのあとに使える特殊能力の窓（こんじょうは G37 で別に聞く）
_KNOCK_OUT_WINDOWS = frozenset({Window.KO_CHECK, Window.KO_PROCESS, Window.AFTER_JUDGE})


@dataclass(frozen=True)
class FieldPowerSuppression(Element):
    """v0.92: 次の相手の番の終わりまで、お互いの場にいるすべてのポケモンは、特殊能力を使うことができず、それらの力も消える（ナツメのゲンガーの「やみのはどう」）。プレイヤーに与える
    期限のある効果（``ATTACK_FIELD_POWER_SUPPRESSION``。``player`` はワザを使ったプレイヤー、``source_card``・``pokemon_id`` は実際にワザを使ったポケモン、``card_id``・``attack_index`` は
    ワザの出どころ、消える番は与えた番 + 1）を加える。ログ ``trainer_effect_added``。

    - 決められない場面（加える前に止める。先読みが宣言の前に見つける）: 相手の場の特殊能力を持つポケモンが、相手のワザの効果を受けない（「ワザをうけない」状態・［オーロラヴェール］・
      エフェクトガード・［クリスタルボディ］・「とうめい」。このワザで受けると決まったポケモンは除く）なら DW2。このワザで HP 以上になったポケモンがこんじょうを使えるなら G37、
      きぜつの時の特殊能力（［ファイナルビーム］・ふしちょう）を持つなら DW3
    - 加えたあとの状態が受け付けられない（決められない姿・［ずらかる］の力がもどる。``effects.attack_state_stop_after``）なら止める。最大HP が下がるのはワザのあとのきぜつの判定で扱う
    - これがワザの最後の要素なので、ワザの出どころが特殊能力でも、処理を続けるかの問い（オールクリアの ZC2）はない"""

    turns: int = 1  # v0.114: 消える番は与えた番 + ``turns``（やみのはどうは 1（次の相手の番の終わり）、ブビィの「モクモク」は 2（次の自分の番の終わり））
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.POWER_LOCK_ELEMENT

    def __post_init__(self) -> None:
        if self.turns not in (1, 2):
            raise ValueError(f"おたがいの場の特殊能力を止める期間 {self.turns!r} は 1（次の相手の番）か 2（次の自分の番）")

    def record(self, run: AttackRun) -> TrainerTurnEffect:
        turn = run.state.turn_number
        attacker = run.attacker()
        return TrainerTurnEffect(kind=ATTACK_FIELD_POWER_SUPPRESSION, player=run.player, source_card=attacker.card, card_id=run.key.card_id, created_turn=turn,
                                 expires_turn=turn + self.turns, pokemon_id=attacker.pokemon_id, attack_index=run.key.attack_index)

    def _protected_question(self, run: AttackRun) -> None:
        from .kernel import first_void

        state = run.state
        opponent = 1 - run.player
        for pokemon in state.players[opponent].in_play():
            if state.is_face_down(pokemon) or not E.powers_of(state, pokemon):
                continue  # うらのカードは全体にはたらく効果ではおもてにしない。特殊能力のないポケモンは、止まるかどうかで結果が変わらない
            received = run.fs.reception.get(pokemon.pokemon_id)
            evasion = received is not True and E.evasion_power(state, pokemon) is not None
            if received is False or evasion or first_void(run.res, run.incoming(), opponent, pokemon, Window.BEFORE_EFFECT) is not None:
                raise run.res.question("dark_wave_protected", f"ポケモン {pokemon.pokemon_id}")

    def _knocked_out_question(self, run: AttackRun) -> None:
        state = run.state
        for owner in (run.player, 1 - run.player):
            for pokemon in state.players[owner].in_play():
                if state.is_face_down(pokemon) or not E.knocked_by_hp(state, pokemon):
                    continue
                if owner != run.player:
                    run.ko_prevention_conflict(pokemon, owner)  # こんじょう（G37）
                for instance in C.instances(state, owner, pokemon, run.res.catalog):
                    definition = instance.definition
                    if (definition.origin is C.Origin.PRINTED_POWER and definition.suppressible and definition.windows & _KNOCK_OUT_WINDOWS
                            and definition.decision_kind != KO_PREVENTION and not C.stopped(state, instance) and not C.blocked_by_status(instance, pokemon)):
                        raise run.res.question("dark_wave_knocked_out_power", f"ポケモン {pokemon.pokemon_id}（{definition.name}）")

    def run(self, run: AttackRun) -> bool:
        state = run.state
        self._protected_question(run)
        self._knocked_out_question(run)
        record = self.record(run)
        if any(r.kind == ATTACK_FIELD_POWER_SUPPRESSION and r.player == run.player and r.created_turn == record.created_turn for r in state.trainer_effects):
            raise RuntimeError(f"プレイヤー {run.player} の「やみのはどう」の効果が、与えた番 {record.created_turn} にすでにある（1 番に使えるワザは 1 つ。エンジンの不具合）")
        trial = state.peek()
        trial.trainer_effects = trial.trainer_effects + (record,)
        _raise_state_stop(state, trial)
        state.trainer_effects = state.trainer_effects + (record,)
        state.add_event("trainer_effect_added", player=run.player, effect_kind=ATTACK_FIELD_POWER_SUPPRESSION, trainer_card=record.source_card, card_id=record.card_id,
                        expires_turn=record.expires_turn, attack_index=record.attack_index, pokemon_id=record.pokemon_id, effect=str(run.key))
        return False


BUILDERS |= {
    E.CoinAttackAndRetreatLock: lambda e: (
        Coin("coin"), OpponentCannotAttack(local_coin=None, gate=("coin", HEADS)), OpponentRetreatLock(gate=("coin", HEADS)),
    ),
    E.PeriodLockAttack: lambda e: (
        OpponentPeriodLock(e.lock, e.start, e.end, e.while_source_active, e.ends_on, local_coin=HEADS if e.on_heads else None),
    ),
    E.ReceivedAttackDamageBonusAttack: lambda e: (OpponentDamageTakenBonus(e.amount, e.start, e.end),),
    E.DamageDrainThenPoison: lambda e: (Damage(OPP, Printed()), Drain("damage"), Status(POISON, after_damage="damage")),
    # v0.97: 「そのポケモンの持っている」（ヤミカラス）は IGNORE_RECEIVER_HELD（受けるポケモン自身の効果だけを除く。SS1 の比べはしない。docs/unown-research-idfnj-v0.97.md 9 章）
    E.ChooseOpponentPokemonDamageIgnoringHeldEffects: lambda e: chosen_damage(Fixed(e.damage), defender_effects=False, ignore_scope=IGNORE_RECEIVER_HELD),
    E.DamageThenFieldPowerSuppression: lambda e: (Damage(OPP, Printed()), FieldPowerSuppression()),
    E.CoinsUntilTailsBonusDamage: lambda e: (Damage(OPP, HeadsUntilTails(e.per, fixed=e.base)),),
}


# ---------------------------------------------------------------- v0.93（docs/active-leave-locks-v0.93.md）: バトル場をはなれられない効果・続くワザの制限


@dataclass(frozen=True)
class FailWithoutOpponentBench(Element):
    """相手に控えがいないとき、このワザは失敗する（v0.93。わるいアリアドスの「からめとる」の「(相手に控えがいないとき、このワザは失敗する。)」。p.323「12 ワザの失敗」。ログ
    ``attack_failed`` の ``reason`` は ``E.ENTANGLE_NO_BENCH``）。確かめるのはワザの内容を処理するとき（こんらんのコインのあと。並びの最初。v0.45 の ``FailUnlessOpponentStatus`` と
    同じ時点）。宣言はでき、ワザを使ったことになる（使うための条件の「使えない」ではない）。相手への効果ではないので「ワザをうけない」状態・「とうめい」は評価しない。"""

    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        if not run.state.players[1 - run.player].bench:
            run.fail(E.ENTANGLE_NO_BENCH)
        return False


BUILDERS |= {
    E.DamageThenPeriodLock: lambda e: (
        Damage(OPP, Printed()),
        OpponentPeriodLock(e.lock, e.start, e.end, e.while_source_active, e.ends_on, local_coin=HEADS if e.on_heads else None, knockout_exception=e.knockout_exception),
    ),
    E.CoinBonusDamageThenLeaveLock: lambda e: (
        Coin("coin"), Damage(OPP, PrintedPlusBonus("coin", e.bonus)), OpponentPeriodLock(E.LOCK_LEAVE, 0, 1, gate=("coin", HEADS)),
    ),
    E.DamageThenPoisonThenLeaveLockOnHeads: lambda e: (
        Damage(OPP, Printed()), Status(POISON), OpponentPeriodLock(E.LOCK_LEAVE, 0, 1, local_coin=HEADS, knockout_exception=True),
    ),
    E.SwitchOpponentThenParalyzeNewOnHeads: lambda e: (
        FailWithoutOpponentBench(), ForceSwitch(chooser="attacker", carry=True), Status(PARALYSIS, local_coin=HEADS, after_switch="switch", reparalysis_check=True),
    ),
    E.DamageThenRetreatLockAndAttackCoinCheck: lambda e: (
        Damage(OPP, Printed()), OpponentPeriodLock(E.LOCK_RETREAT, 1, 1, ends_on=(E.SOURCE_LEAVES_ACTIVE,)),
        OpponentPeriodLock(E.LOCK_ATTACK_CHECK, 1, 1, ends_on=(E.SOURCE_LEAVES_ACTIVE,)),
    ),
}


# ---------------------------------------------------------------- v0.94（docs/switch-return-attacks-v0.94.md）: 入れ替え・帰還のワザ


BUILDERS |= {
    # このゆびとまれ（ピッピ）: ワザを使ったプレイヤーが選ぶ。相手に控えがいなければ使えない（``usage_problem``）
    E.SwitchOpponentActiveRequiringBench: lambda e: (ForceSwitch(chooser="attacker", required=True),),
    # ほえる（ブルー）: この要素のコインの「おもて」で、相手が選ぶ。控えがいなければ入れ替えない（コインも投げない）
    E.ForceSwitchOnHeadsWithoutDamage: lambda e: (ForceSwitch(local_coin=HEADS),),
    # はしゃぐ（トゲピー）: ダメージのあと、自分の控えと入れ替える（控えがいれば必ず。0 匹の答えはない）
    E.DamageThenSelfSwitch: lambda e: (Damage(OPP, Printed()), SelfSwitch()),
    # フローラルスピン（キレイハナ）: ダメージのあとの 1 枚のコインで、「おもて」は相手の特殊状態、「うら」は自分の入れ替え
    E.DamageThenStatusOnHeadsElseSelfSwitch: lambda e: (
        Damage(OPP, Printed()), Coin("coin"), Status(e.condition, gate=("coin", HEADS)), SelfSwitch(gate=("coin", TAILS)),
    ),
    # ふんだりけったり（ケンタロス）: ダメージの前の 1 枚のコインで、「おもて」は基本となるダメージの追加、「うら」はダメージのあとに相手が選ぶ入れ替え
    E.CoinBonusDamageElseForceSwitch: lambda e: (Coin("coin"), Damage(OPP, PrintedPlusBonus("coin", e.bonus)), ForceSwitch(gate=("coin", TAILS))),
    # きつねび（ロコン）: ダメージの前に、ワザを使ったプレイヤーが入れ替えるかを選び（0〜1 匹）、そのあとのバトル場のポケモンにダメージ
    E.OptionalSwitchOpponentThenDamage: lambda e: (ForceSwitch(chooser="attacker", optional=True, carry=True), Damage(OPP, Printed())),
    # すくいなげ（わるいドンファン）: 相手に控えがいなければワザの失敗。1 枚のコインで、「おもて」は相手の手札にもどす、「うら」は相手が選ぶ入れ替え
    E.CoinReturnOpponentToHandElseForceSwitch: lambda e: (
        FailWithoutOpponentBench(), Coin("coin"), ReturnOpponentToHand(gate=("coin", HEADS)), ForceSwitch(gate=("coin", TAILS)),
    ),
}


# ---------------------------------------------------------------- v0.95（docs/private-looks-deck-movement-v0.95.md）: 手札・山札を見る効果と、見たカード・山札・ついている
# トレーナーを動かすワザ


@dataclass(frozen=True)
class LookedCount:
    """v0.95: 見た相手の手札の中のトレーナーカードの枚数（``CountLookedHandTrainers`` の結果。``Resolution.hidden_choice`` で求めた値）。"""

    count: int


@dataclass(frozen=True)
class LookOpponentHand(Element):
    """相手の手札を見る（v0.95。オタチの「さぐる」・ナツメのケーシィの「とうし」）。``zones.look_at_hand``（ログ ``look_at_hand`` の ``cards`` は見たプレイヤーと持ち主だけ。
    1 回見るだけで、あとで観測の手札を公開しない）。相手の手札が 0 枚でも見る処理をして終わる（見るカードがない。p.309）。相手の手札への効果なので、「ワザをうけない」状態・
    「とうめい」は評価しない。カードは動かさない。"""

    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        look_at_hand(run.state, run.player, 1 - run.player, effect=str(run.key))
        return False


@dataclass(frozen=True)
class CountLookedHandTrainers(Element):
    """相手の手札を見て、その中にある「トレーナーカード」の枚数を数える（v0.95。ゴーストの「ポルターガイスト」の「相手の手札を見て、その中にある「トレーナーカード」の枚数」）。

    - 見る（``zones.look_at_hand``。``LookOpponentHand`` と同じログ）。トレーナーカードは手札にある間の印刷の分類（``CardFilter("trainer")``）
    - 数は見る前には分からないので、先読みは 0〜手札の枚数のすべてを試す（``Resolution.hidden_choice``。宣言を受け付けるか・止める問いが、相手の手札の中身によらない）
    - 結果（``LookedCount``）はダメージの要素の基本となるダメージ（``PerLookedTrainers``）が読む。この要素とダメージの要素のあいだに決定はない（ダメージの要素の中の決定は、
      基本となるダメージを続きの情報で運ぶので、数え直さない）
    - ダメージを決める確認なので ``Phase.NEUTRAL``（ダメージの要素より前）"""

    name: str = "looked_trainers"
    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        state = run.state
        cards = look_at_hand(state, run.player, 1 - run.player, effect=str(run.key))
        actual = len(E.hand_trainer_cards(state, cards))
        run.fs.results[self.name] = LookedCount(run.res.hidden_choice(range(len(cards) + 1), actual))
        return False


@dataclass(frozen=True)
class PerLookedTrainers:
    """見た相手の手札の中のトレーナーカードの枚数（``CountLookedHandTrainers`` の結果 ``looked``）× ``per``（v0.95。「ポルターガイスト」）。p.321 の 1 段階（基本となるダメージ）。
    0 枚なら 0（ワザの失敗ではない。そのあとの計算は今までどおり）。``private``: 受けなかったダメージの量を観戦者に見せない（``kernel._amount_privacy``）。"""

    looked: str
    per: int
    local_coins: ClassVar[int] = 0
    private: ClassVar[bool] = True

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.fs.results[self.looked].count * self.per


@dataclass(frozen=True)
class LookHandTrainerToDeck(Element):
    """コインを投げて ``local_coin`` なら、相手プレイヤーの手札を見る。その中にある「トレーナーカード」を 1 枚選び、相手の山札にもどす。その後、その山札をよく切る（v0.95。
    わるいハッサムの「おどす」）。

    - 見る（``zones.look_at_hand``）→ 選ぶ（決定 ``OPPONENT_HAND_TO_DECK``。決めるのはワザを使ったプレイヤー。選べるものは見た手札のトレーナーカード（``CardFilter("trainer")``。
      手札の並び）。「てよい」がないので、あればちょうど 1 枚。1 枚でも決定を出す）→ 相手の山札にもどす（``zones.opponent_hand_card_to_deck``）→ 相手の山札を切る（1 回）
    - トレーナーカードがない（相手の手札が 0 枚を含む）なら、もどさずに相手の山札を切る（v0.75 のもえあがる・v0.79 の「選べるカードがない・山札が 0 枚なら、加えずに山札を切る」と
      同じ読み方。p.309。説明の「その後、その山札をよく切る」は別の文）。見る前に、トレーナーカードがないことでコインを省いたり、宣言を拒否したりしない
    - 相手の手札・山札への効果なので、相手の対戦ポケモンの「ワザをうけない」状態・「とうめい」は評価しない。相手の手札も山札も 0 枚なら、処理の対象がないのでコインを投げない（p.309）
    - 見たあとの処理（もどす・切る）は問いに当たらない（ワザの最後の要素で、ダメージもない）ので、先読みは見た手札の中身で分けない
    - 先読み（``res.dry_run``）では切らない（``shuffle_in_attack``）"""

    local_coin: CoinSide | None = HEADS
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = OPPONENT_HAND_TO_DECK

    def has_target(self, run: AttackRun) -> bool:
        p = run.state.players[1 - run.player]
        return bool(p.hand or p.deck)

    def run(self, run: AttackRun) -> bool:
        if not self.has_target(run):
            return False
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        state = run.state
        opponent = 1 - run.player
        cards = look_at_hand(state, run.player, opponent, effect=str(run.key))
        trainers = E.hand_trainer_cards(state, cards)
        if not trainers:
            shuffle_in_attack(run, self, opponent)
            return False
        run.suspend(kind=OPPONENT_HAND_TO_DECK, player=run.player, options=trainers, extra=(("owner", opponent),))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        opponent = decision.context_value("owner")
        if opponent != 1 - run.player or len(choices) != 1 or choices[0] not in E.hand_trainer_cards(state, state.players[opponent].hand):
            raise RuntimeError(f"おどすの決定 {decision.kind}・答え {choices} が、相手の手札のトレーナーカードではない（エンジンの不具合）")
        opponent_hand_card_to_deck(state, opponent, choices[0], looker=run.player, effect=str(run.key))
        shuffle_in_attack(run, self, opponent)


@dataclass(frozen=True)
class OpponentDeckTopDiscardIfTrainer(Element):
    """相手の山札の 1 番上のカードを見て、それが「トレーナーカード」なら、トラッシュする。「トレーナーカード」でないなら、そのカードをもとの山札の上にもどす（v0.95。わるいマグマラシの
    「もやす」）。

    - 見る（``zones.look_at_card``。ログ ``look_at_card`` の ``card`` は見たプレイヤーだけ。相手には見せない）。トレーナーカードは山札にある間の印刷の分類（``CardFilter("trainer")``）
    - トレーナーカードなら相手のトラッシュに置く（``zones.discard_from_deck``。ログ ``discard_from_deck`` は公開。v0.31 のやまやきと同じ形）。でなければ動かさない（ログ
      ``deck_top_returned``。公開でカードを書かない）。どちらでも山札を切らない（説明にない）。手札に加えない（v0.45 のてつだうふりではない）
    - 相手の山札が 0 枚なら、見るカードがない（p.309。ログ ``look_at_deck_top_none``。v0.47 のみらいよちと同じ）
    - 相手の山札への効果なので、「ワザをうけない」状態・「とうめい」は評価しない。見たあとの処理は問いに当たらない（ワザの最後の要素で、ダメージもない）"""

    phase: ClassVar[Phase] = Phase.EFFECT
    reads_deck_order: ClassVar[bool] = True

    def run(self, run: AttackRun) -> bool:
        state = run.state
        opponent = 1 - run.player
        if not state.players[opponent].deck:
            state.add_event("look_at_deck_top_none", player=run.player, owner=opponent, effect=str(run.key))
            return False
        card = look_at_card(state, run.player, opponent, "deck", 0, effect=str(run.key))
        if not E.CardFilter("trainer").matches(state.card_def(card)):
            state.add_event("deck_top_returned", player=run.player, owner=opponent, effect=str(run.key))
            return False
        cards = discard_from_deck(state, opponent, 1)
        state.add_event("discard_from_deck", player=opponent, effect=str(run.key), cards=cards, attacker=run.player, attacker_pokemon_id=run.attacker().pokemon_id)
        return False


@dataclass(frozen=True)
class ReturnMilledTypeEnergy(Element):
    """山札からトラッシュの要素 ``mill`` でトラッシュしたカードの中に「``energy_type``」エネルギーカードがあれば、それらをすべてトラッシュから取り出し、手札に加える（v0.95。サイドンの
    「やまくずし」）。

    - 加えるのは、このワザでトラッシュしたカード（``mill`` の結果）のうち、その色の基本エネルギーカードだけ（前からトラッシュにあったカードは加えない。同じ uid。
      ``zones.return_discard_to_hand``。ログ ``milled_to_hand`` は公開。トラッシュから手札に動いたので見える）。なければ空のログ
    - 場のポケモンタワーで「トラッシュから手札に加える」部分だけが消える（トラッシュはする。v0.74。ログ ``discard_to_hand_suppressed``）。そのときはレインボーエネルギーの問い（FV1）に
      当たらない（加えるカードを決めない。v0.73 の熱血!と同じ）
    - 山札・サイドにレインボーエネルギーがあれば FV1（``milled_type_energy``）。カードの枚数で数え、特殊エネルギーで色を出さないもの・場の外のミラクルエネルギーは当たらない
    - 決定はなく、トラッシュの要素のすぐあとに 1 回だけ処理する（決定をまたがない）"""

    energy_type: EnergyType
    mill: str = "mill"
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        milled = run.fs.results.get(self.mill)
        if milled is None:
            raise RuntimeError(f"ワザ {run.key} で、手札に加える前にトラッシュの要素 {self.mill} の結果がない（エンジンの不具合）")
        if suppressed_discard_to_hand(run):
            return False
        if protected_discard(run, "milled_to_hand"):
            return False  # v0.119: ［アレルギーほうし］（山札からトラッシュすることは残る。加えるカードを決めないので FV1 にも当たらない）
        state = run.state
        returned = milled_type_energy(run, milled.cards, self.energy_type)
        if any(uid not in state.players[run.player].discard for uid in returned):
            raise RuntimeError(f"ワザ {run.key} でトラッシュしたカード {returned} が、トラッシュにない（エンジンの不具合）")
        if returned:
            return_discard_to_hand(state, run.player, returned)
        state.add_event("milled_to_hand", player=run.player, cards=returned, effect=str(run.key))
        return False


@dataclass(frozen=True)
class ReturnAttachedTrainerToDeck(Element):
    """相手の場のポケモンについている「トレーナーカード」を 1 枚選び、相手の山札にもどす。その後、その山札をよく切る（v0.95。エイパムの「とりさる」）。

    - 選べるもの: 相手の場のポケモン（バトル場 → ベンチ）についているトレーナーカード（``PokemonInPlay.trainers``。ついている順）。進化カード・エネルギーカード・「ばける」のカード・
      ポケモンとして場に出ているトレーナーカード（ピッピ人形・なにかの化石）・進化のもとになったなにかの化石は、ついているトレーナーではない。このワザで HP 以上になったポケモンの
      カードは選べない（処理の対象がない。p.309。こんじょうを使えるなら G37）
    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_ATTACHED_TRAINER``。1 枚でも決定を出す）。もどすのはカードとポケモンの持ち主（相手）の山札（``zones.return_attached_trainer_to_deck``。
      ポケモンは動かない。ログ ``attached_trainer_to_deck`` は公開）→ 相手の山札を切る（1 回）
    - ついているポケモンへの効果（要素の種類 ``TRAINER_RETURN_ELEMENT``）なので、選んだあと、そのポケモンの「ワザをうけない」状態・エフェクトガード・「とうめい」を評価する（``reaches``。
      うらのカードはおもてにする）。受けないなら何もしない（もどさない・切らない。v0.40 のつまみだすと同じ）
    - 選べるカードがないなら、もどさずに相手の山札を切る（v0.75 のもえあがる・v0.79 の L と同じ読み方。p.309）
    - ポケモンは場をはなれないので、「バトル場をはなれられない」効果では止めない。もどしたあとの場は、v0.91 のオールクリアと同じ確かめ（``_raise_state_stop``）にかける
    - 先読み（``res.dry_run``）では切らない（``shuffle_in_attack``）"""

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_ATTACHED_TRAINER
    opponent_element: ClassVar[str] = E.TRAINER_RETURN_ELEMENT

    def _options(self, run: AttackRun) -> tuple[int, ...]:
        opponent = 1 - run.player
        found = []
        for pokemon in run.state.players[opponent].in_play():
            if not pokemon.trainers:
                continue
            if run.knocked_out(pokemon):
                run.ko_prevention_conflict(pokemon, opponent)
                continue
            found.extend(attached.card for attached in pokemon.trainers)
        return tuple(found)

    def run(self, run: AttackRun) -> bool:
        options = self._options(run)
        opponent = 1 - run.player
        if not options:
            shuffle_in_attack(run, self, opponent)
            return False
        run.suspend(kind=SELECT_ATTACHED_TRAINER, player=run.player, options=options, extra=(("owner", opponent),))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        opponent = decision.context_value("owner")
        holder = next((pokemon for pokemon in state.players[1 - run.player].in_play() if len(choices) == 1
                       and any(attached.card == choices[0] for attached in pokemon.trainers)), None)
        if opponent != 1 - run.player or holder is None or choices[0] not in self._options(run):
            raise RuntimeError(f"とりさるの決定 {decision.kind}・答え {choices} が、相手のポケモンについているトレーナーカードではない（エンジンの不具合）")
        before = state.peek()
        if not reaches(run.res, run.fs, opponent, holder, E.TRAINER_RETURN_ELEMENT):
            return
        return_attached_trainer_to_deck(state, opponent, holder, choices[0], effect=str(run.key), chooser=run.player)
        shuffle_in_attack(run, self, opponent)
        _raise_state_stop(before, state)


BUILDERS |= {
    # さぐる（オタチ）・とうし（ナツメのケーシィ）: 相手の手札を見るだけ
    E.LookOpponentHandAttack: lambda e: (LookOpponentHand(),),
    # ポルターガイスト（ゴースト）: 見た手札のトレーナーカードの枚数 × per が基本となるダメージ
    E.DamageTimesLookedHandTrainers: lambda e: (CountLookedHandTrainers(), Damage(OPP, PerLookedTrainers("looked_trainers", e.per))),
    # みらいよち（ネイティオ）: 自分または相手の山札の上からちょうど count 枚を見て並べかえる
    E.ArrangeDeckTopExactlyEffect: lambda e: (ArrangeDeckTop(e.count, exact=True),),
    # おどす（わるいハッサム）: この要素のコインの「おもて」で、見た手札のトレーナーカードを 1 枚相手の山札にもどして切る
    E.CoinLookOpponentHandTrainerToDeck: lambda e: (LookHandTrainerToDeck(),),
    # もやす（わるいマグマラシ）: 相手の山札の一番上を見て、トレーナーカードならトラッシュ
    E.OpponentDeckTopDiscardIfTrainer: lambda e: (OpponentDeckTopDiscardIfTrainer(),),
    # やまくずし（サイドン）: ダメージ → 自分の山札の上から count 枚をトラッシュ → その中の energy_type エネルギーカードを手札に加える
    E.DamageThenMillReturnTypeEnergy: lambda e: (Damage(OPP, Printed()), MillOwnDeck(e.count), ReturnMilledTypeEnergy(e.energy_type)),
    # とりさる（エイパム）: 相手の場のポケモンについているトレーナーカードを 1 枚選び、相手の山札にもどして切る
    E.ReturnOpponentAttachedTrainerToDeck: lambda e: (ReturnAttachedTrainerToDeck(),),
}


# ---------------------------------------------------------------- v0.99（docs/unown-perform-help-history-v0.99.md）。前の相手の番に受けたダメージで追加するワザ


@dataclass(frozen=True)
class PlusIfDamagedLastOpponentTurn:
    """ダメージの目安の数字 + （前の相手の番、このカードがワザによるダメージを受けていたなら ``bonus``）（v0.99。タッツーの「ひれがえし」。p.321 の 1 段階）。

    - 「このカード」はワザを使うポケモン（``run.attacker()``。相手のワザとして使うときは使うポケモン）。読むのは前の相手の番（今の番の 1 つ前）の、このカードの受けた記録
      （``history.received_on``）の最終ダメージの合計（バトル場・ベンチを問わない。0 は受けなかった）。今のダメージカウンター・場所・ログからは決めない"""

    bonus: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        from ..history import received_on

        record = received_on(run.attacker(), run.state.turn_number - 1)
        return run.attack.damage + (self.bonus if record is not None and record.damage > 0 else 0)


BUILDERS |= {
    # ひれがえし（タッツー）: 前の相手の番にワザによるダメージを受けていたら bonus を追加する
    E.PlusIfDamagedByAttackLastOpponentTurn: lambda e: (Damage(OPP, PlusIfDamagedLastOpponentTurn(e.bonus)),),
}


# ---------------------------------------------------------------- v0.100（docs/sketch-perish-song-history-v0.100.md）。前の相手の番のワザを使う・前の自分の番に受けたワザで「きぜつ」させる

SKETCH_NOT_IN_PLAY = "not_in_play"  # ログ attack_failed の reason（「スケッチ」の「前の相手の番、このカードが場に出ていなければ、このワザは失敗する」）
SKETCH_NO_ATTACK = "no_attack"  # ログ sketch_none の reason（前の相手の番に、相手がワザを使っていない）
# ``sketch_presence`` の答え
PRESENT = "present"  # 前の相手の番の始めから、同じポケモンとして場にいた
ABSENT = "absent"  # 前の相手の番には場にいなかった（今の番に場に出た・今の姿になったカードで、前の相手の番に場にいたカードの記録にない）
PRESENCE_UNDETERMINED = "undetermined"  # 読み方で失敗するかが変わる（SK1）
PRESENCE_UNRECORDED = "unrecorded"  # 前の相手の番に場にいたカードの記録がない（エンジンの持つ情報の不足）


def sketch_presence(state, player: int, pokemon: PokemonInPlay) -> tuple[str, str]:
    """v0.100: 「前の相手の番、このカードが場に出ていなければ、このワザは失敗する」の、プレイヤー ``player`` の ``pokemon``（このカード）が前の相手の番に場に出ていたか（答え, 理由の文）。

    - 今の姿になった番（``current_form_turn``。場に出た番・進化・退化した番。ドーブルはたねポケモンで進化・退化しないので場に出た番と同じ）が前の相手の番より前なら、前の相手の番の
      始めから同じポケモンとして場にいた（``PRESENT``。場をはなれたら別のポケモン）
    - 前の相手の番に場に出た・今の姿になった: 前の相手の番の途中から場にいた（``PRESENCE_UNDETERMINED``。英語版の「攻撃の時に場にいた」を足さない）
    - 今の番に場に出た・今の姿になった: 前の相手の番に場にいたカードの記録（``history.turn_field``）にこのカードがなく、うらのカードもなかったなら ``ABSENT``。記録にこのカードがある
      （前の相手の番に場にいて、そのあと場をはなれて出し直した。場に出た番は新しくなるので、それだけでは区別を失う）・うらのカードがあった（正体を記録しないので、このカードでないと
      言えない）なら ``PRESENCE_UNDETERMINED``。記録がなければ ``PRESENCE_UNRECORDED``
    - 前の相手の番がない（今の番が 1。対戦準備は相手の番ではない）: ``PRESENCE_UNDETERMINED``"""
    from ..history import turn_field

    previous = state.turn_number - 1
    entered = pokemon.current_form_turn
    if previous < 1:
        return PRESENCE_UNDETERMINED, "前の相手の番がない（先攻の最初の番）"
    if entered < previous:
        return PRESENT, f"{entered} 番から場にいる"
    if entered == previous:
        return PRESENCE_UNDETERMINED, f"前の相手の番（{previous} 番）の途中に場に出た・今の姿になった"
    field = turn_field(state, previous, player)
    if field is None:
        return PRESENCE_UNRECORDED, f"前の相手の番（{previous} 番）に場にいたカードの記録がない"
    if pokemon.card in field.cards:
        return PRESENCE_UNDETERMINED, f"前の相手の番（{previous} 番）に場にいたこのカードを、場をはなれたあと今の番に出し直した"
    if field.face_down:
        return PRESENCE_UNDETERMINED, f"前の相手の番（{previous} 番）に場にいたうらのカード {field.face_down} 枚（正体を記録しない）が、このカードでないと言えない"
    return ABSENT, f"今の番（{entered} 番）に場に出た・今の姿になった"


@dataclass(frozen=True)
class UseLastOpponentAttack(Element):
    """前の相手の番に相手が使ったワザを、このカードのワザとして使う（v0.100。ドーブルの「スケッチ」。実装 ``effects.UseLastOpponentAttack``）。

    - 先に「このカードが場に出ていなければ、このワザは失敗する」を確かめる（``sketch_presence``）。場に出ていなければワザの失敗（``run.fail``。ログ ``attack_failed`` の ``reason``
      ``not_in_play``。使ったことになり、番は終わる）。決まらなければ SK1（宣言の前の先読みが見つける）
    - 前の相手の番のプレイヤーの記録（``history.turn_attack``）がなければ、処理の対象がないので何もしない（ログ ``sketch_none``。失敗ではない）。記録していない番ならエンジンの情報の不足
      （``UNSUPPORTED_HISTORY_TURN_RECORD_MISSING``。「使わなかった」と読まない）
    - 宣言したワザと処理したワザが違う（まねたワザ）なら SK2。そのワザを使えるか（``copy_status``。説明が条件をみたさないときの処理を書かないので ``clause`` なし）が決まらなければ
      HC9（``copied_attack``）・エンジンの未対応なら ``copied_attack_unsupported``。必要なエネルギーは確かめない
    - そのワザの要素の並びに切りかえる（``run.redirect``。v0.31 の ``CopyOpponentAttack``・v0.62 の ``RepeatReceivedAttack`` と同じ。処理したワザを使った記録に書く ``note_processed``）。
      ログ ``copy_attack``（``used_turn`` に使われた番・``used_by`` に使った相手のポケモンの番号。過去の参照で、新しい対象にしない）
    """

    phase: ClassVar[Phase] = Phase.EFFECT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        return UNRESOLVED, "相手のワザを自分のワザとして使うワザを、さらに自分のワザとして使う"

    def run(self, run: AttackRun) -> bool:
        from ..history import turn_attack, turn_field

        state = run.state
        attacker = run.attacker()
        previous = state.turn_number - 1
        presence, why = sketch_presence(state, run.player, attacker)
        if presence == PRESENCE_UNDETERMINED:
            raise run.res.question("sketch_presence", f"ポケモン {attacker.pokemon_id}: {why}")
        if presence == PRESENCE_UNRECORDED:
            raise run.res.question("turn_history_missing", f"ポケモン {attacker.pokemon_id}: {why}")
        if presence == ABSENT:
            run.fail(SKETCH_NOT_IN_PLAY)
            return False
        record = turn_attack(state, previous)
        if record is None:
            if turn_field(state, previous, run.player) is None:
                raise run.res.question("turn_history_missing", f"{previous} 番")
            state.add_event("sketch_none", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), reason=SKETCH_NO_ATTACK,
                            used_turn=previous)
            return False
        if record.player != 1 - run.player:
            raise RuntimeError(f"前の相手の番（{previous} 番）のワザの記録のプレイヤーが {record.player}（エンジンの不具合）")
        if record.processed is not None and record.processed != record.declared:
            raise run.res.question("sketch_copied_attack", f"宣言したワザ {E.AttackKey(*record.declared)}・処理したワザ {E.AttackKey(*record.processed)}")
        key = E.AttackKey(*record.declared)
        definition = state.definitions[key.card_id]
        attack = definition.attacks[key.attack_index]
        status = copy_status(run, definition, attack, None)
        if status is not None:
            raise run.res.question("copied_attack_unsupported" if status[0] == UNSUPPORTED else "copied_attack", f"「{attack.name_ja}」: {status[1]}")
        effect = state.effects.attack_effect(definition.id, attack, definition.attacks)
        state.add_event("copy_attack", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.declared),
                        copied=str(key), copied_attack=attack.name_ja, used_turn=previous, used_by=record.pokemon_id)
        run.redirect = (key, attack, BUILDERS[type(effect)](effect))
        return False


@dataclass(frozen=True)
class KnockOutIfAsleepAndReceived(Element):
    """このワザを受ける相手が「ねむり」状態で、前の自分の番に「``attack_name``」を受けていたなら、相手は「きぜつ」する（v0.100。ムウマの「ほろびのうた」。実装
    ``effects.KnockOutIfAsleepAndReceived``）。

    - 相手の対戦ポケモンが今ねむりでなければ、何もしない（「とうめい」も評価しない。v0.72 の「めざめのキッス」と同じ順番。受けた記録も読まない）
    - 前の自分の番（今の番の 2 つ前）の受けた記録（``history.named_attack_received``）で受けていなければ何もしない。決まらなければ PSG1。ログ ``knock_out_condition``（今ねむりか・
      受けていたか）
    - 成り立てば、相手のこのワザの中で HP 以上なら処理の対象がない（こんじょうなら G37）。相手への効果として ``reaches``（``KNOCK_OUT_ELEMENT``。「ワザをうけない」状態・「とうめい」・
      効果だけを無効にする効果）を評価し、受けるなら ``kernel.knock_out_by_effect``（ダメージによらない「きぜつ」。きぜつの処理はワザのあと）
    """

    attack_name: str
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.KNOCK_OUT_ELEMENT

    def run(self, run: AttackRun) -> bool:
        from ..history import RECEIVED, RECEIVED_UNDETERMINED, named_attack_received

        state = run.state
        owner, target = 1 - run.player, run.opponent_active()
        if target is None:
            return False
        attacker = run.attacker()
        turn = state.turn_number - 2
        asleep = state.find_pokemon(target.pokemon_id) is not None and target.conditions.asleep
        received = named_attack_received(state, target, turn, self.attack_name) if asleep else None
        state.add_event("knock_out_condition", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), target_player=owner,
                        target_pokemon_id=target.pokemon_id, asleep=asleep, received_attack=self.attack_name, received_turn=turn,
                        received=None if received is None else received[0])
        if received is None or received[0] not in (RECEIVED, RECEIVED_UNDETERMINED):
            return False
        if received[0] == RECEIVED_UNDETERMINED:
            raise run.res.question("perish_song_received_attack", f"ポケモン {target.pokemon_id}: {received[1]}")
        if run.knocked_out(target):
            run.ko_prevention_conflict(target, owner)
            return False
        if not reaches(run.res, run.fs, owner, target, E.KNOCK_OUT_ELEMENT):
            return False
        knock_out_by_effect(run.res, run.fs, owner, target)
        return False


BUILDERS |= {
    # スケッチ（ドーブル）: 前の相手の番に相手が使ったワザを、このカードのワザとして使う（必要なエネルギーはいらない）
    E.UseLastOpponentAttack: lambda e: (UseLastOpponentAttack(),),
    # ほろびのうた（ムウマ）: 相手が今ねむりで、前の自分の番に attack_name を受けていたなら、相手は「きぜつ」する
    E.KnockOutIfAsleepAndReceived: lambda e: (KnockOutIfAsleepAndReceived(e.attack_name),),
}


# ---------------------------------------------------------------- v0.104（docs/healing-pokemon-v0.104.md）: 回復の量・対象・とりのぞくかの選択


@dataclass(frozen=True)
class OptionalHealSelf(Element):
    """自分についているダメージカウンターを ``counters`` 個取り除くことができる（v0.104。プリンの「かいふく」。実装 ``effects.OptionalHealSelf``）。

    - ワザを使ったポケモンにダメージカウンターがのっていれば、取り除くかをワザを使ったプレイヤーが選ぶ（決定 ``OPTIONAL_HEAL``。選べるものはワザを使ったポケモンの番号 1 つで、
      0〜1 個。``context`` の "counters"）。のっていなければ選ぶものがないので出さない。ワザを使ったポケモンがこのワザで HP 以上なら処理の対象がない（``HealCounters`` と同じ
      ログ ``effect_skipped``）
    - 取り除くを選んだら、受ける前に「とうめい」などを評価し（``reaches`` の ``heal``）、のっている数まで取り除く（ログ ``attack_heal``）。取り除かないを選んだら、ログ
      ``attack_heal_declined``（取り除けた数）。「相手にダメージを与えたら」の条件はない（v0.72 の ``Drain`` の ``optional`` とは別）
    - 答えのあとに続ける要素はない。決定をまたいで運ぶ値は、決定の形の値（取り除く数）と枠の値（``carry``）だけ
    """

    counters: int
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = OPTIONAL_HEAL

    def run(self, run: AttackRun) -> bool:
        state = run.state
        attacker = run.attacker()
        if run.knocked_out(attacker):
            state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            element="heal", reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        if attacker.damage // state.rules.damage_per_counter <= 0:
            return False  # 取り除くダメージカウンターがない（選ぶものがない。p.309）
        run.suspend(kind=OPTIONAL_HEAL, player=run.player, options=(attacker.pokemon_id,), min_choices=0, max_choices=1, carry=True,
                    extra=(("counters", self.counters),))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        attacker = run.attacker()
        if choices and choices != (attacker.pokemon_id,):
            raise RuntimeError(f"取り除くポケモン {choices} が、ワザを使ったポケモンではない（エンジンの不具合）")
        per = state.rules.damage_per_counter
        removed = min(self.counters, attacker.damage // per)
        if not choices:
            state.add_event("attack_heal_declined", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            counters=removed)
            return
        if removed <= 0 or not reaches(run.res, run.fs, run.player, attacker, E.HEAL_ELEMENT):
            return
        before = attacker.damage
        attacker.damage = before - removed * per
        state.add_event("attack_heal", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), counters=removed,
                        amount=removed * per, damage_before=before, total_damage=attacker.damage)


BUILDERS |= {
    # あまいみつ（キレイハナ）: コイン →「おもて」なら自分の場のポケモンを 1 匹選ぶ → そのポケモンのダメージカウンターをすべてとりのぞく
    E.CoinChooseOwnPokemonHealAll: lambda e: (
        Coin("coin"), ChooseEffectTarget(side=E.TARGET_SIDE_OWN, gate=("coin", HEADS)), TargetHeal(every=True, gate=("coin", HEADS), side=E.TARGET_SIDE_OWN),
    ),
    # フラワーダンス（キレイハナ）: 自分の場の、今の姿の名前が names のポケモンの数 × per
    E.OwnNamedPokemonCountDamage: lambda e: (Damage(OPP, PokemonCountTimes(e.per, SCOPE_OWN_IN_PLAY, e.names)),),
    # ミルクのみ（ミルタンク）: コイン coins 枚 →「おもて」の数 × per 個を自分からとりのぞく
    E.CoinsHealSelfTimes: lambda e: (Coin("coin", count=e.coins), HealCounters(heads_of="coin", per_heads=e.per)),
    # おひるね（ヒメグマ）・ねむる（ジュゴン）: 自分のダメージカウンターをすべてとりのぞく →（説明の特殊状態を回復させる）→ 自分をねむりにする
    E.HealAllSelfThenSelfSleep: lambda e: (
        HealCounters(every=True), *((CureOwnConditions(e.cures, reach=True),) if e.cures else ()), Status(SLEEP, target=SELF),
    ),
    # もうとっしん（イノムー）: 相手にダメージ → 自分にもダメージ → 次の自分の番、このワザを使えない
    E.DamageAndSelfDamageThenLockSelf: lambda e: (Damage(OPP, Printed()), Damage(SELF, Fixed(e.self_damage), name="self_damage"), SelfAttackLock(None)),
    # かいふく（プリン）: 自分のダメージカウンターを counters 個取り除くかを選ぶ
    E.OptionalHealSelf: lambda e: (OptionalHealSelf(e.counters),),
    # やさしいうた（ラプラス）: 自分と相手の対戦ポケモンから counters 個ずつとりのぞく → 相手をねむりにする
    E.HealBothActivesThenSleep: lambda e: (HealCounters(e.counters, scope=E.HEAL_BOTH_ACTIVE), Status(SLEEP)),
}


# ---------------------------------------------------------------- v0.105（docs/recovery-evolution-coin-branches-v0.105.md）: 回復のあとの山札からの進化・与えたぶんの回復・コインの分岐

BUILDERS |= {
    # からやぶりしんか（トランセル）・ひざしをあびる（ヒマナッツ）: コイン →「おもて」なら自分のダメージカウンターをすべてとりのぞく → 山札から自分を進化させる（必ず 1 枚。山札を見たら切る）
    E.CoinHealAllThenEvolveSelfFromDeck: lambda e: (
        Coin("coin"), HealCounters(every=True, gate=("coin", HEADS)),
        EvolveAttackerFromDeck(e.evolves_from, gate=("coin", HEADS), required=True, shuffle_if_looked=True),
    ),
    # ハイパーリバース（バタフリー）: 相手のエネルギーの個数 × per → 与えたぶんを自分からとりのぞく（受ける前に判定する）
    E.DefenderEnergyUnitsDamageAndFullDrain: lambda e: (Damage(OPP, DefenderEnergyUnitsTimes(e.per)), Drain("damage", full=True, reach=True)),
    # サイコリーフ（セレビィ）: 相手のエネルギーの個数ぶんのコイン → 目安 +「おもて」の数 × per → 与えたぶんを自分からとりのぞく（受ける前に判定する）
    E.CoinsPerDefenderEnergyBonusAndFullDrain: lambda e: (
        Coin("coin", per_opponent_energy=True), Damage(OPP, PrintedPlusHeadsOfCoin("coin", e.per)), Drain("damage", full=True, reach=True),
    ),
    # プレゼント（デリバード）: コイン 3 枚 →「おもて」の数で 1 つだけ（3: ダメージ・1: ダメージ・2: 相手から決まった数・0: 相手からすべて）。ダメージの要素を先に並べる（1 つだけを
    # 処理するので並びは結果を変えない。ダメージの要素のあいだにダメージ以外の効果の要素を置くと、処理しない回復の要素で「ダメージを受けたとき」の効果の時点の確かめ（v0.38 の GK1）に当たる）
    E.ThreeCoinDamageOrOpponentHeal: lambda e: (
        Coin("coin", count=3), Damage(OPP, Fixed(e.all_heads), gate=("coin", 3)), Damage(OPP, Fixed(e.one_heads), name="one_heads_damage", gate=("coin", 1)),
        HealCounters(e.two_heads, scope=E.HEAL_OPPONENT_ACTIVE, gate=("coin", 2)), HealCounters(every=True, scope=E.HEAL_OPPONENT_ACTIVE, gate=("coin", 0)),
    ),
}


# ---------------------------------------------------------------- v0.106（docs/counts-coins-compositions-v0.106.md）: 数とコインの組み合わせ（「おもて」の数の表・カードの枚数ぶんの上限つきの
# コイン・相手が取ったサイドの数・同じコインの追加のダメージと自分へのダメージ）


@dataclass(frozen=True)
class PrintedPlusHeadsTable:
    """ダメージの目安の数字 + コインを ``len(bonuses) - 1`` 枚投げた「おもて」の数 h の追加のダメージ ``bonuses[h]``（v0.106。ストライク（neo2-008）の「れんぞくぎり」の「コインを4枚
    投げる。「おもて」が1枚なら10ダメージ、…「おもて」が4枚なら80ダメージを追加する。」。目安 10+ なので 10・20・30・50・90）。p.321 の 1 段階（表の値を最終ダメージにしない）。
    表は登録の引数（``effects.CoinsHeadsTableBonusDamage``。カードの id を見ない）。コインはダメージの要素の中（ダメージの量だけを決める）で、結果は「おもて」の数だけを使う
    （``by_heads``。先読みは「おもて」の数でまとめる。実際には 1 枚ずつ投げる。v0.72 の ``PrintedPlusHeadsTimes`` と同じ投げ方）。"""

    bonuses: tuple[int, ...]
    by_heads: ClassVar[bool] = True

    @property
    def local_coins(self) -> int:
        return len(self.bonuses) - 1

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + self.bonuses[0 if flips is None else flips.heads]


@dataclass(frozen=True)
class HeadsTimesAttachedEnergyCards:
    """ワザを使うポケモンについている「エネルギーカード」の枚数ぶん（``max_coins`` 枚まで）コインを投げ、「おもて」の数 × ``per``（v0.106。カブトプス（neo2-018）の
    「ハイドロカッター」）。数えるのはカードの枚数（``effects.attached_energy_cards``。v0.50 のサイコウェーブと同じ数え方。無色2個エネルギーは 1 枚）で、v0.34 の
    ``HeadsTimesAttachedEnergy``（出すエネルギーの個数）とは別の値。コインの枚数は枚数と上限の小さいほう（``effects.CappedCoinsPerAttachedEnergyCardsDamage.coin_count`` と同じ値）。
    0 枚なら投げず 0。コインはダメージの要素の中（ダメージの量だけを決める）で、結果は「おもて」の数だけを使う（``by_heads``）。"""

    per: int
    max_coins: int
    by_heads: ClassVar[bool] = True

    def coin_count(self, run: AttackRun) -> int:
        return min(E.attached_energy_cards(run.state, run.attacker()), self.max_coins)

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return (0 if flips is None else flips.heads) * self.per


@dataclass(frozen=True)
class PrintedPlusOpponentPrizesTaken:
    """ダメージの目安の数字 + 相手プレイヤーがすでに取ったサイドの数 × ``per``（v0.106。ゴースト（ES3-023）の「おんねん」）。p.321 の 1 段階。相手はワザを使ったプレイヤー
    （``run.player``。相手のワザとして使ったなら使ったプレイヤー）の相手で、取った数は ``effects.prizes_taken``（準備で置く数 − 今のサイドの枚数。きぜつ・トレーナーで取ったもの。
    カードの中身は読まない）。"""

    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + E.prizes_taken(run.state, 1 - run.player) * self.per


BUILDERS |= {
    # いかりのとっしん（グランブル）: 目安 + 自分のカウンターの数 × per（相手へのダメージの時点）→ 自分にも self_damage（別のダメージの要素。相手が受けなくても省かない）
    E.DamagePlusOwnCountersThenSelfDamage: lambda e: (Damage(OPP, PlusOwnCounters(e.per)), Damage(SELF, Fixed(e.self_damage), name="self_damage")),
    # れんぞくぎり（ストライク）: コイン（表の長さ − 1 枚）→ 目安 +「おもて」の数の表の値
    E.CoinsHeadsTableBonusDamage: lambda e: (Damage(OPP, PrintedPlusHeadsTable(e.bonuses)),),
    # ハイドロカッター（カブトプス）: 自分のエネルギーカードの枚数ぶん（上限つき）のコイン →「おもて」の数 × per
    E.CappedCoinsPerAttachedEnergyCardsDamage: lambda e: (Damage(OPP, HeadsTimesAttachedEnergyCards(e.per, e.max_coins)),),
    # おんねん（ゴースト）: 目安 + 相手が取ったサイドの数 × per
    E.DamagePlusOpponentPrizesTaken: lambda e: (Damage(OPP, PrintedPlusOpponentPrizesTaken(e.per)),),
    # ローリングニードル（サンドパン）: コイン coins 枚（1 組）→ 目安 +「おもて」の数 × per → 自分にも同じ「おもて」の数 × self_per（同じコインの組。投げ直さない）
    E.CoinsBonusAndSelfDamagePerHeads: lambda e: (
        Coin("coin", count=e.coins), Damage(OPP, PrintedPlusHeadsOfCoin("coin", e.per)), Damage(SELF, HeadsOfCoin("coin", e.self_per), name="self_damage"),
    ),
}


# ---------------------------------------------------------------- v0.107（docs/coin-failure-status-flight-v0.107.md）: コインによる成否・特殊状態・防護（既存の要素の組み合わせ。新しい要素・値はない）


BUILDERS |= {
    # とげでつつく（ビードル）: 失敗のコイン 1 枚（「うら」ならワザ全体が失敗）→ 相手にダメージ → 相手をどく
    E.FailOnTailsDamageThenPoison: lambda e: (FailOnTails(), Damage(OPP, Printed()), Status(POISON)),
    # とつぜんじばく（クヌギダマ）: 失敗のコイン 1 枚 → じばく（SelfDestruct の「弱点・抵抗力」に関係ない書き方）と同じダメージのまとまり（相手 → 自分 → 相手の控え全員 → 自分の控え全員）
    E.FailOnTailsSelfDestruct: lambda e: (
        FailOnTails(), *BUILDERS[E.SelfDestruct](E.SelfDestruct(e.self_damage, e.bench_damage, weakness_resistance_stated=True)),
    ),
    # そらをとぶ（そらをとぶピカチュウ・バタフリー）: 失敗のコイン 1 枚 → 相手にダメージ → 自分に次の相手の番のワザへの防護（AttackBarrier。同じコインの「おもて」。投げ直さない）
    E.FailOnTailsDamageThenSelfBarrier: lambda e: (FailOnTails(), Damage(OPP, Printed()), SelfPersistent(AttackBarrier.kind)),
    # へんずつう（コダック）: 相手にダメージ → コイン 1 枚 →「おもて」なら相手、「うら」なら自分をこんらん（ダメージはどちらの面でも与える）
    E.DamageThenConfuseOpponentOrSelf: lambda e: (
        Damage(OPP, Printed()), Coin("coin"), Status(CONFUSION, gate=("coin", HEADS)), Status(CONFUSION, target=SELF, gate=("coin", TAILS)),
    ),
}


# ---------------------------------------------------------------- v0.108（docs/damage-modifiers-condition-bonuses-v0.108.md）: 使うワザのダメージを減らす効果・相手の特殊状態の確かめと
# 追加・相手の特殊状態の回復


@dataclass(frozen=True)
class OpponentDealtDamageReduction(Element):
    """相手の対戦ポケモン（このワザを受けた相手）に、次の相手の番（与えた番 + 1）だけ、使うワザによるダメージを ``amount`` 減らす効果（``state.DealtAttackDamageReduction``）を与える
    （v0.108。チョンチーの「マイナスイオン」・トゲピーの「あまえる」）。

    - 相手に与える効果なので「とうめい」・「ワザをうけない」状態・［ニュートラルシールド］など（``reaches``。発生元は実際にワザを使ったポケモン）を評価する。相手がこのワザで HP 以上なら
      与えない（p.309。こんじょうを使えるなら G37）
    - 発生源（``source_card``・``source_player``・``source_pokemon``）は実際にワザを使ったポケモン（相手のワザとして使ったなら使ったポケモン）。ログ ``persistent_effect_added`` に
      ``end_turn``・``source_pokemon``・``amount``
    - v0.34 の ``OpponentReducedDamage``（なきつく。「このカード」に与えるダメージだけ）とは別の要素・別の持続する効果"""

    amount: int
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.DEALT_DAMAGE_ELEMENT

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if not reaches(run.res, run.fs, opponent, target, E.DEALT_DAMAGE_ELEMENT):
            return False
        attacker = run.attacker()
        turn = run.state.turn_number
        effect = DealtAttackDamageReduction(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn + 1, end_turn=turn + 1,
                                            source_pokemon=attacker.pokemon_id, amount=self.amount)
        add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key), amount=self.amount, **period_log_fields(effect))
        return False


@dataclass(frozen=True)
class OpponentStatusCheck(Element):
    """相手の対戦ポケモンが ``conditions`` のどれかの状態かを 1 回だけ確かめ、結果を ``name`` で残す（v0.108。アーボックの「もうどく」の「このワザを受ける前から相手が「どく」状態なら」・
    わるいプクリンの「たたきおこす」の「相手が「ねむり」または「こんらん」状態なら」）。

    - 並びの最初（ワザの内容を処理するとき。こんらんのコイン・手順 4 のコインのあと、ダメージの要素の前）。ダメージの値 ``PlusIfResult`` がこの結果を読む。あとの要素（どく・回復）・
      キョウのどく・反応・決定で状態が変わっても確かめ直さない（v0.45 の ``SelfStatusCheck`` と同じ形で、確かめるのが相手の対戦ポケモン）
    - どくは通常のどくと特殊などくのどちらでも（``has_condition``。どくの量ではなく、どく状態か）
    - 相手への効果ではないので「ワザをうけない」状態・「とうめい」は評価しない（v0.45 の ``FailUnlessOpponentStatus`` と同じ）。相手の対戦ポケモンは、実際にワザを使ったプレイヤーの相手"""

    name: str
    conditions: tuple[str, ...]
    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        target = run.opponent_active()
        run.fs.results[self.name] = target is not None and any(has_condition(target, condition) for condition in self.conditions)
        return False


@dataclass(frozen=True)
class PlusIfResult:
    """ダメージの目安の数字 + （確かめ ``check`` の結果が真なら ``bonus``）（v0.108。もうどく・たたきおこす。p.321 の 1 段階）。確かめの結果は並びの最初で決まり、決定をまたぐときは
    この値で決めた基本となるダメージを続きの情報（``base``）で運ぶ（確かめ直さない）。"""

    check: str
    bonus: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + (self.bonus if run.fs.results[self.check] else 0)


@dataclass(frozen=True)
class CureOpponentConditions(Element):
    """相手の対戦ポケモンを、説明が書く特殊状態（``names``）だけから回復させる（v0.108。わるいプクリンの「たたきおこす」の「その後、相手を「ねむり」または「こんらん」状態から回復させる」。
    ``conditions.cure_conditions``。ログ ``special_conditions_removed`` の ``reason`` ``cured``）。

    - 回復させる状態がなければ処理の対象がないので何もしない（「とうめい」なども評価しない。v0.72 の ``WakeOpponent`` と同じ）。どく・マヒ・ダメージカウンター・マーカー・持続する効果は残す
    - 相手がこのワザのダメージで HP 以上なら回復させない（p.309。こんじょうを使えるなら G37）
    - 相手のポケモンへの効果なので、回復させる前に「ワザをうけない」状態・「とうめい」・効果を無効にする効果を評価する（``reaches`` の ``CURE_ELEMENT``。有益な効果でも防ぐ。回復は特殊状態に
      する効果ではないので［めんえき］・特殊状態にならない効果は見ない）。ダメージだけが無効でも、この要素は受ける判定で決める（「ダメージを与えたら」の条件はない）
    - v0.90 の ``CureOwnConditions``（自分への要素）の対象・``reach`` の既定は変えない
    - 回復させたあとの状態が受け付けられない（特殊能力がまたはたらいて決められない姿・［ずらかる］の力がもどる。``effects.attack_state_stop_after``）なら止める（宣言の前に先読みが見つける）。
      最大HP が下がるのは、ワザのあとのきぜつの判定が扱う"""

    names: tuple[str, ...]
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.CURE_ELEMENT

    def run(self, run: AttackRun) -> bool:
        owner, target = 1 - run.player, run.opponent_active()
        if target is None or not any(name in self.names for name in target.conditions.names()):
            return False
        if run.knocked_out(target):
            run.ko_prevention_conflict(target, owner)
            return False
        if not reaches(run.res, run.fs, owner, target, E.CURE_ELEMENT):
            return False
        before = run.state.peek()
        cure_conditions(run.state, owner, target, self.names, effect=str(run.key))
        stop = E.attack_state_stop_after(before, run.state)
        if stop is not None:
            raise UnsupportedError(*stop)
        return False


BUILDERS |= {
    E.DamageThenDealtDamageReduction: lambda e: (Damage(OPP, Printed()), OpponentDealtDamageReduction(e.amount)),
    E.DealtDamageReductionWithoutDamage: lambda e: (OpponentDealtDamageReduction(e.amount),),
    E.DamageThenReceivedAttackDamageBonus: lambda e: (Damage(OPP, Printed()), OpponentDamageTakenBonus(e.amount, e.start, e.end)),
    E.PlusIfDefenderPoisonedThenPoison: lambda e: (
        OpponentStatusCheck("opponent_status_before", (POISON,)), Damage(OPP, PlusIfResult("opponent_status_before", e.bonus)), Status(POISON),
    ),
    E.PlusIfDefenderStatusThenCure: lambda e: (
        OpponentStatusCheck("opponent_status_before", e.conditions), Damage(OPP, PlusIfResult("opponent_status_before", e.bonus)), CureOpponentConditions(e.conditions),
    ),
}


# ---------------------------------------------------------------- v0.109（docs/timed-damage-guards-v0.109.md）: 次の相手の番に受けるときのコインでダメージを防ぐ効果・相手のタイプで
# 決まる基本となるダメージ


@dataclass(frozen=True)
class SelfTimedDamageGuard(Element):
    """ワザを使ったポケモン自身に、次の相手の番だけ、受けるときのコインでダメージを防ぐ効果（``state.TimedDamageGuard``）を与える（v0.109。ウパーの「ぬるぬる」・エビワラーの「かわす」・
    ユンゲラーの「ブリンク」）。コインはない（コインはダメージを受けるときに投げる。``kernel.timed_guard_passes``）。

    - 自分への効果なので「とうめい」・「ワザをうけない」状態は評価しない（v0.83 の ``SelfReflectShield`` と同じ）。ワザを使ったポケモンがこのワザの中で HP 以上なら与えない（p.309。返す効果の
      ダメージなど。ログ ``persistent_effect_skipped``）。相手がダメージを受けたか・HP 以上になったかは条件にしない（ブリンクのダメージのあとでも与える）
    - 前の効果ははたらく番の終わりに消えている（同じ番に 2 回使うことはない）ので、置きかえずに加える。ログ ``persistent_effect_added`` に面・投げる人・範囲
    - 実際にワザを使ったポケモンに与える（相手のワザとして使ったなら使ったポケモン）"""

    prevent_on: str
    flipper: str
    scope: str
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("persistent_effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                persistent_effect=TimedDamageGuard.kind, effect=str(run.key), reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        turn = run.state.turn_number
        effect = TimedDamageGuard(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn + TimedDamageGuard.turns_until_active,
                                  prevent_on=self.prevent_on, flipper=self.flipper, scope=self.scope)
        add_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key), prevent_on=self.prevent_on, flipper=self.flipper, scope=self.scope)
        return False


@dataclass(frozen=True)
class AmountIfDefenderType:
    """相手の対戦ポケモン（ダメージの要素を処理する時点）の今有効なタイプが ``pokemon_type`` なら ``amount``、そうでなければダメージの目安の数字（v0.109。ユンゲラーの「サイコパニック」の
    「このワザを受ける相手が「超」ポケモンなら、このワザのダメージは60になる」。p.321 の 1 段階。弱点・抵抗力などはそのあとの段階で計算する（最終ダメージを ``amount`` にしない））。

    - タイプは今の姿と今有効な色（``effects.same_for_type_readings``。［へんしょく］など。読み方で結果が変わるなら VS1。v0.45 の ``PrintedTimesIfDefenderType`` と同じ問い合わせ）。
      印刷されたタイプで決めない。うらのカード（マチスの秘策）は ``Damage.run`` がこの値を求める前におもてにする
    - 「その数になる」の固定の量で、目安の数字の倍数ではない（v0.45 の「「…」倍になる」の ``PrintedTimesIfDefenderType`` とは別の値。目安と量の組は登録の文面で照らす）"""

    pokemon_type: EnergyType
    amount: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        defender = run.opponent_active()
        try:
            return E.same_for_type_readings(run.state, (defender,),
                                            lambda views: self.amount if views[0].pokemon_type is self.pokemon_type else run.attack.damage)
        except E.TypeReadingsDiffer as differ:
            raise type_question(run.res, differ, f"ワザ {run.key} の相手のタイプで決まるダメージ") from None


BUILDERS |= {
    E.SelfTimedDamageGuardWithoutDamage: lambda e: (SelfTimedDamageGuard(e.prevent_on.value, e.flipper, e.scope),),
    E.DamageThenSelfTimedDamageGuard: lambda e: (Damage(OPP, Printed()), SelfTimedDamageGuard(e.prevent_on.value, e.flipper, e.scope)),
    E.DamageSetAgainstType: lambda e: (Damage(OPP, AmountIfDefenderType(e.pokemon_type, e.amount)),),
}


# ---------------------------------------------------------------- v0.110（docs/endure-armor-up-v0.110.md）: 使うときのコインで、残りHPがなくなっても「きぜつ」しない期間つきの効果


@dataclass(frozen=True)
class SelfKnockOutSurvival(Element):
    """使うときにコインを 1 枚投げ、「おもて」なら、ワザを使ったポケモン自身に、残りHPがなくなっても「きぜつ」しない期間つきの効果（``state.KnockOutSurvival``）を与える（v0.110。
    ゴマゾウの「こらえる」・わるいフォレトスの「こうてつか」）。

    - コインはワザの説明のコイン（``AttackRun.flip``）。ナツメのESPでやり直したなら、やり直したあとの結果でだけ与える（決定の前に効果を与えない。コインの前にログを残さない）。こんらんの
      コイン（宣言のあと・ワザの要素の前）とは別。「うら」なら何もしない（ワザの失敗ではない。持っている効果を消さない）
    - 期間は与えた番から数える（``start``〜``end``）。前の効果が残っていても置きかえずに加える（こうてつかを次の自分の番にもう一度使うと、その番は 2 つがはたらく。どちらも同じ結果）
    - 自分への効果なので「とうめい」・「ワザをうけない」状態は評価しない。ワザを使ったポケモンがこのワザの中で HP 以上なら、処理の対象がないのでコインも投げない（p.309）
    - 実際にワザを使ったポケモンに与える（相手のワザとして使ったなら使ったポケモン）"""

    start: int
    end: int
    scope: str
    remaining_hp: int
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("persistent_effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                persistent_effect=KnockOutSurvival.kind, effect=str(run.key), reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        if run.flip(1).results[0] is not HEADS:
            return False
        turn = run.state.turn_number
        effect = KnockOutSurvival(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn + self.start, end_turn=turn + self.end,
                                  scope=self.scope, remaining_hp=self.remaining_hp)
        add_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key), end_turn=effect.end_turn, scope=self.scope,
                              remaining_hp=self.remaining_hp)
        return False


BUILDERS |= {
    E.SelfKnockOutSurvivalOnHeads: lambda e: (SelfKnockOutSurvival(e.start, e.end, e.scope, e.remaining_hp),),
}


# ---------------------------------------------------------------- v0.111（docs/field-energy-card-counts-v0.111.md）: 場のエネルギーカードの枚数でダメージ・ワザの使用条件が決まるワザ


@dataclass(frozen=True)
class OpponentFieldEnergyCardsTimes:
    """ワザを実際に使ったプレイヤーの相手の場（バトル場と控え）のポケモンについている「``energy_type``」エネルギーカードの枚数 × ``per``（v0.111。ミュウツーの「サイコクラッシュ」。
    p.321 の 1 段階の基本となるダメージそのもの。目安の数字を加えない）。数えるのはダメージの要素を処理する時点（``effects.field_energy_cards_of_type``）。0 枚なら 0。

    - 数えることはワザの効果ではないので、控えの「とうめい」・「ワザをうけない」状態は評価しない（数から除かない）。ダメージを受けるのは相手の対戦ポケモンだけ（``Damage(OPP)``）
    - カードとしての色が決まらないカード（``effects.field_energy_card_ambiguities``）があれば、そのポケモンごとに既存の問い（TE1・RB1・BZ2・MEC1・CE3。``transform_energy_question`` の
      カードの色の確かめ。［おいしげる］の「草」の個数の問いは色の枚数に関係しないので聞かない）で止める。ただし、受ける相手の対戦ポケモンにとってこのダメージの要素が無効
      （``kernel.first_void``。かたまる・バリアー・［ニュートラルシールド］など）なら、量は使われない（計算しない）ので止めずに 0 を返す
    - 相手のワザとして使ったときも、実際に使ったプレイヤー（``run.player``）の相手の場を数える"""

    energy_type: EnergyType
    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        state = run.state
        owner = 1 - run.player
        if E.field_energy_card_ambiguities(state, owner, self.energy_type):
            from .kernel import first_void

            receiver = run.opponent_active()
            if receiver is not None and first_void(run.res, run.incoming(), owner, receiver) is not None:
                return 0  # このダメージの要素は無効（量を計算しない）。色の決まらないカードで結果は変わらない
            for pokemon in state.players[owner].in_play():
                if pokemon.energy:
                    transform_energy_question(run, pokemon, self.energy_type, cards=True, wild=False)
            remaining = E.field_energy_card_ambiguities(state, owner, self.energy_type)
            if remaining:
                # 残るのはエナジーバーンの「炎」だけ（使った番の自分のポケモンにだけ起こるので、相手の場にはない）
                raise RuntimeError(f"相手の場のカード {list(remaining)} がエナジーバーンで「炎」になっている（使った番の自分のポケモンだけに起こる。エンジンの不具合）")
        return E.field_energy_cards_of_type(state, owner, self.energy_type) * self.per


@dataclass(frozen=True)
class EqualEnergyCardsRequired(Element):
    """ワザを使うための条件「自分と相手に同じ数のエネルギーカードがついている時だけ、このワザは使える」（v0.111。ナツメのケーシィの「シンクロウェーブ」）。

    条件はワザの実装の ``usage_problem`` が宣言の前（必要なエネルギーの確認のあと・こんらんのコインの前）に確かめる（``ENERGY_CARD_COUNTS_DIFFER``。状態・乱数・ログを変えない）。
    この要素は、相手のワザとして使うとき（ピクシー・ピッピの「ゆびをふる」など）の扱い（``copy_problem``。実際に使うポケモンと、その相手の対戦ポケモンで比べる。v0.40 の
    ``OwnCountersAtLeast`` と同じ扱い: 説明が「使えない」「説明にしたがう」なら選べず、ほかは HC9）だけを持つ。

    宣言のあとは比べ直さない（変わり身の術の「相手がワザを使う時」の入れ替えで相手の対戦ポケモンが変わっても、ワザは宣言のときの条件で使っている。「そのワザのダメージや効果は、
    入れ替えの後でおこる」）。v0.83 のやさしいモルフォンの ``FailUnlessEqualEnergyCards``（処理の中で比べて失敗する）とは別の要素。"""

    phase: ClassVar[Phase] = Phase.NEUTRAL

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        defender = run.opponent_active()
        own, theirs = E.attached_energy_cards(run.state, copier), 0 if defender is None else E.attached_energy_cards(run.state, defender)
        if own != theirs:
            return (ILLEGAL if clause in (CANNOT_USE, FOLLOW_TEXT) else UNRESOLVED), \
                f"自分（{own} 枚）と相手（{theirs} 枚）に同じ数のエネルギーカードがついていない（ワザを使うための条件）"
        return None

    def run(self, run: AttackRun) -> bool:
        return False


BUILDERS |= {
    E.DamageTimesOpponentFieldEnergyCards: lambda e: (Damage(OPP, OpponentFieldEnergyCardsTimes(e.energy_type, e.per)),),
    E.DamageRequiringEqualEnergyCards: lambda e: (EqualEnergyCardsRequired(), Damage(OPP, Printed())),
}


# ---------------------------------------------------------------- v0.112（docs/energy-coins-draw-v0.112.md）: 水エネルギーの個数によるコインとドロー・コインのマヒと自分のワザの制限


BUILDERS |= {
    # しょくしゅをつかう: 自分の「水」エネルギーの個数だけのワザ全体のコイン（「おもて」の数だけを使う）→ その「おもて」の数 × 2 枚を引く
    E.CoinsPerOwnTypedEnergyDraw: lambda e: (Coin("coin", per_own_typed=e.energy_type), Draw(heads_of="coin", per_heads=e.per_heads)),
    # ふしょくえき: ダメージ → 1 枚のワザ全体のコイン →「おもて」なら相手をマヒ・「うら」なら次の自分の番にこのワザを使えない（同じ結果を両方が使う）
    E.DamageParalyzeOnHeadsElseLockSelf: lambda e: (
        Damage(OPP, Printed()), Coin("coin"), Status(PARALYSIS, gate=("coin", HEADS), reparalysis_check=True),
        SelfAttackLock(local_coin=None, gate=("coin", TAILS)),
    ),
}


# ---------------------------------------------------------------- v0.113（docs/variable-coins-search-attachments-v0.113.md）: 可変枚数のコインと、山札の検索・つける・場全体のトラッシュ


# v0.113: お互いの場にいるポケモンの数（``Coin.per_pokemon``。ピッピの「みんなでおどる」とロケット団のニャースの「だいぎゃくてん？」で共有する。数だけを使い、名前でしぼらない）
FIELD_POKEMON = (SCOPE_BOTH_IN_PLAY, None)


@dataclass(frozen=True)
class AttachFromDeckByHeads(Element):
    """ワザ全体のコイン ``heads_of`` の「おもて」の数ぶんの ``energy_type`` エネルギーカードを自分の山札から選び出し、自分の場の ``energy_type`` ポケモンそれぞれに、好きなように
    つける。その後、その山札をよく切る（v0.113。デンリュウ（neo3-028）の「ゆうでん」。kyuura の日本語の印刷の文面。英語の欄の「may」（0 枚・任意）は持ち込まない）。

    - 選ぶ枚数は「おもて」の数 H ちょうど（「おもて」の数ぶん。ピッピの「みんなでおどる」の「以下」とは別）。選ぶのはワザを使ったプレイヤー: カード（決定 ``ATTACH_FROM_DECK``。
      ``context`` の ``"stage"`` は ``"card"``。山札の ``energy_type`` の基本エネルギーカード（uid の小さい順）から H 枚）→ 選んだカード 1 枚ずつ（山札の uid の小さい順）につける
      ポケモン（決定 ``SELECT_POKEMON``。``"stage"`` は ``"target"``・``"cards"`` は選んだカード・``"assigned"`` はそれまでに決めたつける先・``"card"`` は今つける先を決めるカード）。
      1 匹に 2 枚以上をつけてもよい（「好きなように」）。決める間、カードは山札にある（つけるのは、すべてのつける先を決めたあと。1 回だけ切る）
    - つけられるポケモンは自分の場（バトル場 → ベンチ）の、今有効な色（``effects.type_readings``）が ``energy_type`` のポケモン（名前・印刷のタイプで固定しない）。エネルギーカードを
      つけることができない（クリスタルビーム）・このワザの中で HP 以上になった（相手の［はんげき］など。p.309）ポケモンは選べない。色の読み方で ``energy_type`` かが決まらない（VS1・
      CE1・CE2・CM1）ポケモン、うらのカード（マチスの秘策。タイプが読めない。FD1）は、選べるが選ぶと止める（``unresolved_detail``）。止めないつけ先がなければ、その理由で止める
    - H = 0（投げなかったときを含む）・つけられるポケモンがいないなら、選ぶカードはない（ログ ``attach_energy_from_deck_none`` の ``reason`` は ``no_heads``・``no_target``。
      どちらも公開の情報）。つけられるポケモンの有無は公開の情報なので、いなければコインも投げない（v0.38 の ``has_target``。山札の中身では決めない）
    - 山札の選べるカードの数 c: c ≧ H ならちょうど H 枚。c = 0 なら選び出す内容の対象がない（p.309）が、山札の中身で進み方を変えないよう、決定を出して答え（0 枚）を待つ（v0.84 の
      A3。ログ ``attach_energy_from_deck_none`` の ``reason`` ``no_candidates``）。0 < c < H は FC1（説明の枚数より少ない。kyuura の UQ-STATED-COUNT-SHORT。止める）。山札の
      レインボーエネルギーは RB2（選べるが選ぶと止める。それを選ばないと H 枚にならないなら止める）
    - どの場合も、そのあと山札を 1 回切る（説明の最後の「その後、その山札をよく切る」。v0.85 のせいでんき・v0.75 のエナジーサポートと同じ読み方。エネルギーアーク（トレーナー）の
      「おもて」0 枚で切らない読み方は移さない）。ワザの失敗ではない
    - つけるのはワザの効果なので、つける先の「とうめい」を評価する（``reaches``。受けないなら、カードは持ち主のトラッシュ。v0.75 のエナジーサポートと同じ読み方。ログ
      ``deck_energy_evaded``）。山札から直接つける（``zones.attach_from_deck``。ログ ``attach_energy_from_deck`` は公開。手札からつける通常の操作・特殊能力でつけた枚数に数えない）。
      つけたあと ``effects.after_energy_attached``
    """

    energy_type: EnergyType
    heads_of: str
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = ATTACH_FROM_DECK

    def decides(self, kind: str) -> bool:
        return kind in (ATTACH_FROM_DECK, SELECT_POKEMON)

    def cards(self, run: AttackRun) -> tuple[tuple[int, ...], tuple[int, ...]]:
        """(山札の選べるカード, そのうちの選ぶと止めるレインボーエネルギー)。山札にあるあいだの印刷の定義で決める（uid の小さい順）。"""
        rainbow = tuple(sorted(E.rainbow_cards_in(run.state, run.state.players[run.player].deck)))
        return tuple(sorted(set(E.deck_energy_candidates(run.state, run.player, self.energy_type)) | set(rainbow))), rainbow

    def targets(self, run: AttackRun) -> tuple[tuple[int, ...], tuple[tuple[int, str, str], ...]]:
        """(つけられる自分の場のポケモン（バトル場 → ベンチ）, そのうちの選ぶと止めるもの (番号, コード, 理由))。状態・乱数・問いの記録を変えない。"""
        from ..errors import HiddenPropertyRead
        from .kernel import COLOR_QUESTIONS

        options: list[int] = []
        stops: list[tuple[int, str, str]] = []
        for pokemon in run.state.players[run.player].in_play():
            if E.energy_attach_block(run.state, pokemon) is not None or run.knocked_out(pokemon):
                continue
            if run.state.is_face_down(pokemon):
                hidden = HiddenPropertyRead("pokemon_type")
                options.append(pokemon.pokemon_id)
                stops.append((pokemon.pokemon_id, hidden.code, hidden.message))
                continue
            matches = {reading is self.energy_type for reading in E.type_readings(run.state, pokemon)}
            if True not in matches:
                continue
            options.append(pokemon.pokemon_id)
            if len(matches) > 1:
                cause = E.type_reading_cause(run.state, pokemon)
                question = QUESTIONS[COLOR_QUESTIONS[cause] if cause in ("ce1", "ce2", "cm1") else "shift_color_duration"]
                stops.append((pokemon.pokemon_id, question.code, f"ポケモン {pokemon.pokemon_id} が「{self.energy_type.ja}」ポケモンか: {question.message}"))
        return tuple(options), tuple(stops)

    def has_target(self, run: AttackRun) -> bool:
        return bool(self.targets(run)[0])

    def run(self, run: AttackRun) -> bool:
        heads = run.heads(self.heads_of)
        targets, stops = self.targets(run)
        if not heads or not targets:
            self._none(run, "no_target" if not targets else "no_heads")  # つけられるポケモンがいなければコインも投げていない（v0.38）
            return False
        if len(stops) == len(targets):
            raise UnsupportedError(stops[0][1], stops[0][2])  # 止めないつけ先がない（FD1・VS1 など。答えのない決定を出さない）
        cards, rainbow = self.cards(run)
        usable = len(cards) - len(rainbow)
        if usable < heads:
            if rainbow:
                rainbow_attach_question(run, rainbow, self.energy_type)  # RB2（レインボーエネルギーを選ばないと H 枚にならない）
            if usable:
                raise run.res.question("stated_cards_short", f"山札の「{self.energy_type.ja}」エネルギーカード {usable} 枚（「おもて」の数 {heads}）")
        low = heads if usable >= heads else 0
        extra = (("stage", "card"), ("heads", heads)) + _unresolved_extra(rainbow, E.RAINBOW_ATTACH_CODE, E.RAINBOW_ATTACH_REASON.format(type=self.energy_type.ja))
        run.suspend(kind=ATTACH_FROM_DECK, player=run.player, options=cards, min_choices=low, max_choices=heads, carry=True, extra=extra)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        heads = run.carried["heads"]
        if decision.kind == ATTACH_FROM_DECK:
            cards, rainbow = self.cards(run)
            wanted = heads if len(cards) - len(rainbow) >= heads else 0
            if len(set(choices)) != len(choices) or any(card not in cards or card in rainbow for card in choices) or len(choices) != wanted:
                raise RuntimeError(f"つけるカード {choices} が、山札の「{self.energy_type.ja}」エネルギーカードの「おもて」の数 {heads} 枚ではない（エンジンの不具合）")
            if not choices:
                self._none(run, "no_candidates")
                return
            self._ask_target(run, tuple(card for card in cards if card in choices), (), heads)
            return
        chosen = tuple(run.carried["cards"])
        assigned = tuple(run.carried["assigned"]) + tuple(choices)
        targets, stops = self.targets(run)
        if (len(choices) != 1 or choices[0] not in targets or choices[0] in {stop[0] for stop in stops}
                or any(card not in run.state.players[run.player].deck for card in chosen)):
            raise RuntimeError(f"つける先 {choices}・カード {chosen} が正しくない（エンジンの不具合）")
        if len(assigned) < len(chosen):
            self._ask_target(run, chosen, assigned, heads)
            return
        self._attach(run, chosen, assigned)

    def _ask_target(self, run: AttackRun, chosen: tuple[int, ...], assigned: tuple[int, ...], heads: int) -> None:
        targets, stops = self.targets(run)
        extra: tuple = (("stage", "target"), ("heads", heads), ("cards", chosen), ("assigned", assigned), ("card", chosen[len(assigned)]))
        if stops:
            extra += (("unresolved_choices", tuple(stop[0] for stop in stops)), ("unresolved_code", stops[0][1]), ("unresolved_reason", stops[0][2]),
                      ("unresolved_detail", stops))
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=targets, carry=True, extra=extra)

    def _attach(self, run: AttackRun, chosen: tuple[int, ...], assigned: tuple[int, ...]) -> None:
        state = run.state
        for card, pid in zip(chosen, assigned):
            target = state.find_pokemon(pid)[1]
            if reaches(run.res, run.fs, run.player, target, E.ENERGY_ATTACH_ELEMENT):
                attach_from_deck(state, run.player, card, target)
                state.add_event("attach_energy_from_deck", player=run.player, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key), card=card)
                attached_in_attack(run, run.player, target, (card,))
            else:
                state.players[run.player].deck.remove(card)
                state.players[run.player].discard.append(card)  # 「とうめい」の「おもて」: カードは持ち主のトラッシュ（エナジーサポートと同じ読み方）
                state.add_event("deck_energy_evaded", player=run.player, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key), card=card)
        shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        stopped = set(decision.context_value("unresolved_choices", ()))
        if decision.kind == ATTACH_FROM_DECK:
            # 同じカード id の基本エネルギーカードは、どれをつけても同じ形の状態（v0.46 の AttachFromHand と同じまとめ方）。選ぶと止めるレインボーエネルギーは試さない
            return [answer for answer in card_id_answers(run.state, decision, (decision.min_choices,)) if not stopped & set(answer)]
        return [answer for answer in all_answers(decision) if not stopped & set(answer)]

    def _none(self, run: AttackRun, reason: str) -> None:
        attacker = run.attacker()
        run.state.add_event("attach_energy_from_deck_none", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy_type=self.energy_type.value, reason=reason)
        shuffle_in_attack(run, self, run.player)


@dataclass(frozen=True)
class DiscardFieldEnergyAnyNumber(OptionalDiscardForBonus):
    """自分の場の ``energy_type`` エネルギーカードを、好きなだけトラッシュする（v0.113。わるいバクフーン（neo4-022）の「ファイヤーラッシュ」の前半。結果は ``Discarded``（実際にトラッシュした
    カード）。あとのダメージの要素 ``HeadsOfDiscarded`` がその枚数だけコインを投げる）。

    - 範囲は自分の場のポケモン全員（ワザを使ったポケモン → ベンチの順。v0.82 の ``OptionalDiscardForBonus`` の ``include_bench``）。数えるのはカード（その色の基本エネルギーカード。
      エネルギーの個数ではない）。ポケモンごとの色の問い（TE1・RB1・BZ2・MEC1・CE3）・控えへのワザの効果の「ワザをうけない」状態・「とうめい」の評価・リサイクルエネルギーとエコロジムの
      処理（原因はワザ、実際に使ったのは自分。``effects.discard_energy_from_play``）は ``OptionalDiscardForBonus`` と同じ
    - 選べるカードがあるとき 0 枚を選べるか（「のぞむなら」のない「好きなだけ」）は決められない（v0.31 の HC5。選べるが選ぶと止める。答えのときに止め、決定は待ったまま。先読みは試さない）。
      1 枚以上は選べる。選べるカードがないなら、トラッシュする対象がない（p.309。決定を出さない。0 枚をトラッシュした扱いで、コインを投げない）。どちらもワザの失敗ではない
    """

    include_bench: bool = True
    max_cards: int | None = None

    def __post_init__(self) -> None:
        if not self.include_bench or self.max_cards is not None:
            raise ValueError("自分の場の「好きなだけ」のトラッシュは、ベンチを含み、上限がない")

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return [answer for answer in super().dry_choices(run, decision) if answer]  # 0 枚は答えのときに止める（HC5）

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if not choices:
            raise UnsupportedError(
                "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO",
                f"「自分の場の「{self.energy_type.ja}」エネルギーカードを、好きなだけトラッシュする」で、選べるカードがあるときに 0 枚を選べるかは決められないので扱わない（HC5）。"
                "1 枚以上を選ぶ",
            )
        super().resume(run, decision, choices)


BUILDERS |= {
    # みんなでおどる: お互いの場のポケモンの数のワザ全体のコイン →「おもて」の数以下の基本エネルギーカードを山札から見せて手札に → 山札を切る
    E.CoinsPerPokemonInPlaySearchBasicEnergy: lambda e: (
        Coin("coin", per_pokemon=FIELD_POKEMON), RevealTrainerFromDeck(local_coin=None, category="basic_energy", heads_of="coin"),
    ),
    # ゆうでん: ダメージ（目安。説明の最初に省略されている）→ コイン coins 枚（1 組）→「おもて」の数ぶんの「雷」エネルギーカードを山札から自分の場の「雷」ポケモンに好きなように → 切る
    E.DamageThenCoinsAttachTypedEnergyFromDeck: lambda e: (
        Damage(OPP, Printed()), Coin("coin", count=e.coins), AttachFromDeckByHeads(e.energy_type, "coin"),
    ),
    # ギガボルト: コイン 1 枚（ダメージの計算の前）→ 目安 +「おもて」なら bonus → 「うら」なら相手をマヒ（同じ結果を両方が使う）
    E.CoinBonusOnHeadsElseParalyze: lambda e: (
        Coin("coin"), Damage(OPP, PrintedPlusBonus("coin", e.bonus)), Status(PARALYSIS, gate=("coin", TAILS), reparalysis_check=True),
    ),
    # なかまをよぶ: 山札の名前の合うたねポケモン 1 匹をベンチに → 切る。ベンチに空きがなければワザの失敗
    E.PutNamedBasicFromDeckOntoBenchOrFail: lambda e: (BenchFromDeck(e.names, when_full=BENCH_FULL_FAIL),),
    # むれでつつく: 自分のベンチの名前の合うポケモンの数のワザ全体のコイン → 目安 +「おもて」の数 × per
    E.CoinsPerOwnBenchNamedBonusDamage: lambda e: (
        Coin("coin", per_pokemon=(SCOPE_OWN_BENCH, e.names)), Damage(OPP, PrintedPlusHeadsOfCoin("coin", e.per)),
    ),
    # ダークフレイム: 自分の「炎」エネルギーカード 1 枚をトラッシュ（できなければワザの失敗）→ ダメージ（目安）→ トラッシュに「悪」エネルギーカードがあれば 1 枚を自分に
    E.DiscardEnergyThenDamageThenAttachFromDiscard: lambda e: (
        DiscardOwnEnergy(e.discard_type, count=1, when_lacking=LACKING_FAIL), Damage(OPP, Printed()),
        AttachFromDiscard(e.attach_type, 1, exact=True, typed_cards=True),
    ),
    # くろいキバ: 実際に使ったポケモンの「悪」エネルギーの個数のワザ全体のコイン → 目安 +「おもて」の数 × per
    E.CoinsPerOwnTypedEnergyBonusDamage: lambda e: (
        Coin("coin", per_own_typed=e.energy_type), Damage(OPP, PrintedPlusHeadsOfCoin("coin", e.per)),
    ),
    # ファイヤーラッシュ: 自分の場の「炎」エネルギーカードを好きなだけトラッシュ → トラッシュした枚数のコイン（ダメージの要素の中）→「おもて」の数 × per
    E.DiscardFieldEnergyThenCoinsDamage: lambda e: (
        DiscardFieldEnergyAnyNumber(e.energy_type), Damage(OPP, HeadsOfDiscarded("discard", e.per)),
    ),
    # だいぎゃくてん？: お互いの場のポケモンの数のワザ全体のコイン（1 組）→ 相手に「おもて」の数 × per → 自分に「うら」の数 × self_per（同じ組。投げ直さない）
    E.CoinsPerPokemonInPlayHeadsDamageTailsSelfDamage: lambda e: (
        Coin("coin", per_pokemon=FIELD_POKEMON), Damage(OPP, HeadsOfCoin("coin", e.per)), Damage(SELF, TailsOfCoin("coin", e.self_per), name="self_damage"),
    ),
}


# ---------------------------------------------------------------- v0.114（docs/baby-rules-evolution-v0.114.md 6 章）: ベイビィポケモン 13 枚のワザ


@dataclass(frozen=True)
class PowerHolderQuestion(Element):
    """v0.114（HV1）: 説明の「「特殊能力」を持っているポケモン」を受けるポケモンにするダメージ（ピチューの「パチパチ」）の前に、受けるかが決まらないポケモン（持っている特殊能力がすべて
    ほかの効果で消えている。``effects.holds_power`` が None）がおたがいの場にいれば止める（ダメージの要素の前。先読みが宣言の前に見つける）。状態を変えない。"""

    phase: ClassVar[Phase] = Phase.DAMAGE

    def run(self, run: AttackRun) -> bool:
        state = run.state
        undecided = [pokemon.pokemon_id for owner in (run.player, 1 - run.player) for pokemon in state.players[owner].in_play() if E.holds_power(state, pokemon) is None]
        if undecided:
            raise run.res.question("stopped_power_holder", f"ポケモン {undecided}（特殊能力がすべてほかの効果で消えている）")
        return False


def holds_power_now(run: AttackRun, pokemon: PokemonInPlay) -> bool:
    """v0.114: ``Damage``・``BenchDamage`` の ``has_power``（要素を処理する時点で、受けるポケモンが「特殊能力」を持っているか）。決まらない（HV1）なら止める（``PowerHolderQuestion`` が
    先に止めるので、ワザの途中で決まらなくなったときだけ）。"""
    held = E.holds_power(run.state, pokemon)
    if held is None:
        raise run.res.question("stopped_power_holder", f"ポケモン {pokemon.pokemon_id}（特殊能力がすべてほかの効果で消えている）")
    return held


@dataclass(frozen=True)
class TargetCounters(Element):
    """先に選んだ個体（``ChooseEffectTarget`` の ``chosen``）に、ダメージカウンターを ``counters`` 個のせる（v0.114。ムチュールの「なげキッス」）。

    - ダメージカウンターをのせることはワザによるダメージではない（v0.48 の ``PlaceCountersOnDamagedOpponents`` と同じ。GR-2000-P320-COUNTER-MOVE）。ダメージの計算をせず、「ダメージを受けない」
      状態でものせ、「ダメージを受けたとき」の効果ははたらかない
    - のせる前に、そのポケモンの「ワザをうけない」状態・エフェクトガード・「とうめい」を評価する（``reaches`` の ``damage_counters``。うらのカードはおもてにする。受けないなら何もしない）。
      選んだ個体が場をはなれていれば何もしない
    - ログは v0.41 の ``place_damage_counters``。HP 以上になったら、ワザのあとのきぜつの判定でまとめてきぜつする（``_counters_changed``）"""

    counters: int = 1
    chosen: str = "target"
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.COUNTERS_ELEMENT

    def run(self, run: AttackRun) -> bool:
        found = chosen_pokemon(run, self.chosen)
        if not found:
            return False
        state = run.state
        target = found[0]
        owner = state.find_pokemon(target.pokemon_id)[0]
        if not reaches(run.res, run.fs, owner, target, E.COUNTERS_ELEMENT):
            return False
        per = state.rules.damage_per_counter
        before = target.damage
        target.damage = before + self.counters * per
        state.add_event("place_damage_counters", player=owner, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key),
                        counters=self.counters, amount=self.counters * per, damage_before=before, total_damage=target.damage, attacker=run.player,
                        attacker_pokemon_id=run.fs.frame.source_pid)
        _counters_changed(run, target, before)
        return False


@dataclass(frozen=True)
class ReturnAttachedSpecialEnergyToDeck(Element):
    """コインを投げて ``local_coin`` の面なら、相手の場のポケモンについている「特殊エネルギーカード」を 1 枚選び、相手の山札にもどす。その後、その山札をよく切る（v0.114。ムチュールの
    「サイコキッス」）。v0.95 の ``ReturnAttachedTrainerToDeck``（とりさる）と同じ形で、選ぶカードとコインが違う。

    - 選べるもの: ``effects.opponent_attached_special_energy_cards``（相手の場のポケモン（バトル場 → ベンチ）についている特殊エネルギーカード。ついている間の定義。HP 以上のポケモン・
      タケシの保護のポケモンのカードは除く）。なければコインを投げず何もしない（内容の対象がない。p.309。v0.31 のスーパーデストロイと同じ）
    - コインはこの要素の 1 枚（ナツメのESPがやり直せる説明のコイン。``run.flip``）。選べるカードのついているポケモンがどれも「ワザをうけない」状態（効果の要素を無効にする効果）なら、
      投げるかが決まらない（``prevented_effect_coin``。コインの前）
    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_ATTACHED_SPECIAL_ENERGY``。ちょうど 1 枚。1 枚でも決定を出す）。選んだあと、そのカードのついているポケモンの「ワザをうけない」状態・
      エフェクトガード・「とうめい」を評価する（``reaches``。受けないなら何もしない。切らない）→ もどす（``zones.return_attached_energy_to_deck``）→ 相手の山札を切る（1 回）
    - もどしたあとの場は、v0.95 と同じ確かめ（``_raise_state_stop``）にかける。先読みでは切らない（``shuffle_in_attack``）"""

    local_coin: CoinSide | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_ATTACHED_SPECIAL_ENERGY
    opponent_element: ClassVar[str] = E.ENERGY_RETURN_ELEMENT

    def _options(self, run: AttackRun) -> tuple[int, ...]:
        return E.opponent_attached_special_energy_cards(run.state, run.player)

    def run(self, run: AttackRun) -> bool:
        options = self._options(run)
        if not options:
            return False
        state = run.state
        opponent = 1 - run.player
        if self.local_coin is not None:
            from .kernel import first_void

            holders = [pokemon for pokemon in state.players[opponent].in_play() if any(uid in pokemon.energy for uid in options)]
            if all(first_void(run.res, run.incoming(), opponent, pokemon, Window.BEFORE_EFFECT) is not None for pokemon in holders):
                raise run.res.question("prevented_effect_coin", f"ポケモン {[pokemon.pokemon_id for pokemon in holders]}")
            if run.flip(1).results[0] is not self.local_coin:
                return False
        run.suspend(kind=SELECT_ATTACHED_SPECIAL_ENERGY, player=run.player, options=options, extra=(("owner", opponent),))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        opponent = decision.context_value("owner")
        holder = next((pokemon for pokemon in state.players[1 - run.player].in_play() if len(choices) == 1 and choices[0] in pokemon.energy), None)
        if opponent != 1 - run.player or holder is None or choices[0] not in self._options(run):
            raise RuntimeError(f"サイコキッスの決定 {decision.kind}・答え {choices} が、相手のポケモンについている特殊エネルギーカードではない（エンジンの不具合）")
        before = state.peek()
        if not reaches(run.res, run.fs, opponent, holder, E.ENERGY_RETURN_ELEMENT):
            return
        return_attached_energy_to_deck(state, opponent, holder, choices[0], effect=str(run.key), chooser=run.player)
        shuffle_in_attack(run, self, opponent)
        _raise_state_stop(before, state)


BUILDERS |= {
    # モクモク: ダメージ（目安）→ おたがいの場の特殊能力を止める（消える番は与えた番 + 2。やみのはどうと同じ要素）
    E.DamageThenFieldPowerSuppressionUntilOwnNextTurn: lambda e: (Damage(OPP, Printed()), FieldPowerSuppression(e.field_effect_terms()[1])),
    # パチパチ: 受けるかが決まらないポケモンがいれば止める → 特殊能力を持っているポケモン（相手の対戦ポケモン → 自分 → 相手の控え → 自分の控え）にそれぞれ amount（弱点・抵抗力に関係なく）
    E.PowerHoldersSpreadDamage: lambda e: (
        PowerHolderQuestion(),
        Damage(OPP, Fixed(e.amount), weakness_resistance=False, name="power_holder_damage", has_power=True),
        Damage(SELF, Fixed(e.amount), weakness_resistance=False, name="self_damage", has_power=True),
        BenchDamage(Fixed(e.amount), weakness_resistance=False, has_power=True),
        BenchDamage(Fixed(e.amount), weakness_resistance=False, has_power=True, own=True, name="own_bench_damage"),
    ),
    # サイコキッス: この要素のコイン →「おもて」なら相手の場の特殊エネルギーカードを 1 枚選び、相手の山札にもどす → 切る
    E.CoinReturnOpponentSpecialEnergyToDeck: lambda e: (ReturnAttachedSpecialEnergyToDeck(local_coin=HEADS),),
    # いっしょにあそぼ: 山札のベイビィポケモン 1 匹をベンチに → 切る。ベンチに空きがなければワザの失敗
    E.PutBabyFromDeckOntoBenchOrFail: lambda e: (BenchFromDeck((), when_full=BENCH_FULL_FAIL, babies=True),),
    # なげキッス: 相手の場のポケモンを 1 匹選ぶ → そのポケモンにダメージカウンターを counters 個
    E.PlaceCountersOnChosenOpponentPokemon: lambda e: (ChooseEffectTarget(side=E.TARGET_SIDE_OPPONENT, scope=E.TARGET_IN_PLAY), TargetCounters(e.counters)),
}


# ---------------------------------------------------------------- v0.115（docs/spread-damage-allocation-v0.115.md 4〜6 章）: 場・ベンチへのダメージ、対象ごとのコイン、ダメージの配分


def not_of_type(run: AttackRun, pokemon: PokemonInPlay, excluded: EnergyType) -> bool:
    """v0.115: 場のポケモン ``pokemon`` の今有効なタイプ（色）が ``excluded`` でないか（サナギラスの「すなあらし」の「「闘」ポケモン以外」）。タイプはこの要素を処理する時点の今の姿の
    今有効な色（``effects.type_readings``。色マーカー・［へんしょく］・［せんすい］）。読み方（VS1・CE1・CE2・CM1）で答えが変われば止める（``type_question``。どちらか 1 つを選んで続け
    ない）。うらのカード（マチスの秘策）はタイプを読めない（FD1。おもてにしない）。場での役割のポケモン（なにかの化石など。タイプなし）は「闘」ポケモンではない。"""
    try:
        return E.same_for_type_readings(run.state, [pokemon], lambda views: views[0].pokemon_type is not excluded)
    except E.TypeReadingsDiffer as differ:
        raise type_question(run.res, differ, f"ワザ {run.key} のダメージを受けるポケモン（「{excluded.ja}」ポケモン以外）") from None


@dataclass(frozen=True)
class EnergyCardsOfReceiver:
    """受けるポケモンが（そのダメージの要素を処理する時点で）つけている「エネルギーカード」の枚数 × ``per``（v0.115。わるいエーフィの「サイコスプラッシュ」の「それぞれがつけている
    「エネルギーカード」の枚数×10」。p.321 の 1 段階）。受けるポケモンごとに数える（``value_for``。``Damage``・``BenchDamage`` が受けるポケモンを渡す。相手の対戦ポケモンの枚数を控えに
    使い回さない）。数えるのはカードの枚数（``effects.attached_energy_cards``。無色2個エネルギーも［エネエネ］でエネルギーとしてついているカードも 1 枚。エネルギーの個数ではない）。"""

    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        raise RuntimeError("受けるポケモンごとの基本となるダメージは value_for で求める（エンジンの不具合）")

    def value_for(self, run: AttackRun, receiver: PokemonInPlay) -> int:
        return E.attached_energy_cards(run.state, receiver) * self.per


@dataclass(frozen=True)
class AmountIfOpponentBench:
    """相手に控えポケモンがいるとき ``amount``、いなければダメージの目安の数字（v0.115。わるいバンギラスの「ぶんなげる」の「相手に控えポケモンがいるとき、このワザのダメージは「30」に
    なる」。p.321 の 1 段階。目安から引く数ではない）。控えがいるかは、このダメージの要素を処理する時点の相手の場で決める（あとの控えへのダメージと同じ時点の場）。"""

    amount: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return self.amount if run.state.players[1 - run.player].bench else run.attack.damage


@dataclass(frozen=True)
class ChainedCoinsBenchDamage(Element):
    """コインを投げて「おもて」なら、もう 1 枚コインを投げる。2 枚目が「おもて」なら相手の控えポケモン全員にも ``amounts[0]``、「うら」なら ``amounts[1]``（どちらも「弱点・抵抗力」に
    関係なく。v0.115。わるいライチュウの「びっくりサンダー」の、相手の対戦ポケモンへの目安のダメージのあとの部分）。

    - コインは条件つきで続けて投げるまとまり（``AttackRun.flip_chain`` の ``ContinueOnHeads(2)``）。面の並びは T（1 枚。控えへのダメージなし）・HT（2 枚。``amounts[1]``）・HH（2 枚。
      ``amounts[0]``）。1 枚目が「うら」なら 2 枚目を投げない。結果はワザ全体のコインの記録 ``fs.coins[name]`` とログ ``chained_coin_results``（面の並びと控えへの量）に残す
    - 受けるのは、この要素を処理する時点の相手の控えの並び。控えがいなければ処理の対象がないのでコインを投げない（p.309。v0.38 の ``has_target`` と同じ読み方）。控えがいて、どれも
      ダメージの要素を無効にする状態（見えない壁など）なら、投げるかが決まらない（v0.56 と同じ問い ``prevented_coin_damage``。コインの前に止める）
    - ナツメのESPのやり直しは、まとまりを投げ終えたあとに 1 回だけ聞き、やり直すならまとまりを最初から投げ直す（決定のあとはこの要素だけをもう一度処理する。前の要素の相手の対戦
      ポケモンへのダメージはやり直さない。最後の並びだけで量を決める）。控えへのダメージは［ベンチガード］の決定を出しうる（``guarded_damages``）"""

    amounts: tuple[int, int]
    chain: ContinueOnHeads = ContinueOnHeads(2)
    name: str = "bench_damage"
    phase: ClassVar[Phase] = Phase.DAMAGE
    guards_bench: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if (len(self.amounts) != 2 or any(type(a) is not int or a <= 0 or a % 10 for a in self.amounts)) or self.chain.coins != 2:
            raise ValueError(f"続けて投げる 2 枚のコインの控えへのダメージ {self.amounts!r} は、2 枚目の「おもて」・「うら」の 10 の倍数の正の数")

    def coin_receiver(self) -> str | None:
        return "bench"

    def targets(self, run: AttackRun) -> list[PokemonInPlay]:
        return list(run.state.players[1 - run.player].bench)

    def has_target(self, run: AttackRun) -> bool:
        return bool(self.targets(run))

    def void_for_all(self, run: AttackRun) -> bool:
        from .kernel import first_void

        targets = self.targets(run)
        return bool(targets) and all(first_void(run.res, run.incoming(), 1 - run.player, pokemon) is not None for pokemon in targets)

    def amount_for(self, results: tuple[CoinSide, ...]) -> int:
        """面の並び（``chain`` を最後まで投げた並び）の控えへのダメージ（T なら 0）。"""
        if len(results) < 2:
            return 0
        return self.amounts[0] if results[1] is HEADS else self.amounts[1]

    def run(self, run: AttackRun) -> bool:
        targets = self.targets(run)
        if not targets:
            run.fs.coins[self.name] = CoinFlips(())
            return False
        if self.void_for_all(run):
            raise run.res.question("prevented_coin_damage", f"ダメージを受けない控えポケモン {[p.pokemon_id for p in targets]} へのダメージだけを決める、続けて投げるコイン")
        flips = run.flip_chain(self.chain)
        run.fs.coins[self.name] = flips
        amount = self.amount_for(flips.results)
        attacker = run.attacker()
        run.state.add_event("chained_coin_results", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            results=tuple(side.value for side in flips.results), amount=amount, targets=tuple(p.pokemon_id for p in targets))
        if not amount:
            return False
        return guarded_damages(run, self, [(E.OPPONENT_BENCH, pokemon.pokemon_id, amount, False) for pokemon in targets])


@dataclass(frozen=True)
class CoinPerBenchPokemon(Element):
    """おたがいの控えポケモン全員に対して、1 枚ずつコインを投げ、「おもて」が出たポケモンに、「弱点・抵抗力」に関係なく、``amount`` ダメージ（コインを投げるのは、相手側から）（v0.115。
    バンギラスの「なぎたおす」の、相手の対戦ポケモンへの目安のダメージのあとの部分）。

    - 対象はこの要素を処理する時点の、相手の控えの並び → 自分の控えの並び（「相手側から」は対象の側の順番。コインを投げるのは、ワザを使ったプレイヤー（v0.2d の「その効果を使っている側」。
      相手プレイヤーに投げさせる説明ではない））。コインは 1 匹 1 枚、この並びの順に 1 回の ``flip`` で投げ、``i`` 枚目は ``i`` 番目の控えのもの（「おもて」の数でまとめない。どの控えかが
      要る。HT と TH は違う結果。先読みは 2 の控えの数乗通りを試す）。結果はログ ``pokemon_coin_results``（``targets``・``owners``・``results``）
    - すべて投げてから、「おもて」の控えに並びの順でダメージ（相手の控えは ``OPPONENT_BENCH``、自分の控えは ``SELF_BENCH``。弱点・抵抗力なし。ワザを使ったポケモン自身は受けない）。
      控えへのダメージは［ベンチガード］の決定を出しうる（残りの並びを運ぶ。コインは投げ直さず、対象も変えない）
    - 「とうめい」がはたらいているポケモンのあとに対象がいれば、コインの投げ方（すべて投げてからか、1 匹ずつか）で乱数の割り当てが変わるので TS1（v0.60 と同じ問い）。2 匹以上は T27。
      受けるときのコインを本文のコインとひとまとめにしない（ナツメのESPのやり直しは本文のコインだけ。``AttackRun.flip``）
    - 対象がいなければ投げない（p.309）。対象がみなダメージの要素を無効にする状態なら、投げるかが決まらない（v0.56 と同じ問い）。ナツメのESPでやり直すと、同じ並びの対象に同じ枚数を
      投げ直す（面と対象の対応を保つ）"""

    amount: int
    name: str = "bench_coins"
    phase: ClassVar[Phase] = Phase.DAMAGE
    guards_bench: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if type(self.amount) is not int or self.amount <= 0 or self.amount % 10:
            raise ValueError(f"控えポケモンへのダメージは 10 の倍数の正の数（{self.amount!r}）")

    def targets(self, run: AttackRun) -> list[tuple[int, PokemonInPlay]]:
        opponent = 1 - run.player
        return ([(opponent, p) for p in run.state.players[opponent].bench] + [(run.player, p) for p in run.state.players[run.player].bench])

    def has_target(self, run: AttackRun) -> bool:
        return bool(self.targets(run))

    def run(self, run: AttackRun) -> bool:
        from .kernel import first_void

        state = run.state
        targets = self.targets(run)
        if not targets:
            run.fs.coins[self.name] = CoinFlips(())
            return False
        if any(E.evasion_power(state, pokemon) is not None for _, pokemon in targets[:-1]):
            raise run.res.question("bench_coin_transparency_order", f"おたがいの控えのポケモン {[p.pokemon_id for _, p in targets]}")
        if all(first_void(run.res, run.incoming(), owner, pokemon) is not None for owner, pokemon in targets):
            raise run.res.question("prevented_coin_damage", f"ダメージを受けない控えポケモン {[p.pokemon_id for _, p in targets]} へのダメージだけを決めるコイン")
        flips = run.flip(len(targets))
        run.fs.coins[self.name] = flips
        attacker = run.attacker()
        state.add_event("pokemon_coin_results", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                        targets=tuple(p.pokemon_id for _, p in targets), owners=tuple(owner for owner, _ in targets),
                        results=tuple(face.value for face in flips.results))
        entries = [(E.SELF_BENCH if owner == run.player else E.OPPONENT_BENCH, pokemon.pokemon_id, self.amount, False)
                   for (owner, pokemon), face in zip(targets, flips.results) if face is HEADS]
        return guarded_damages(run, self, entries)


@dataclass(frozen=True)
class ExtraTypedUnits:
    """配る単位: ワザに必要なエネルギーよりも多くついている ``energy_type`` エネルギーの数（``max_extra`` つぶんまで。v0.115。シードラの「ウォーターボム」の「多い「水」エネルギー1つにつき」）。
    数えるのはワザを実際に使ったポケモンについている、その色のエネルギーの個数（v0.88 の ``typed_unit_count``。カードの枚数ではない）から、使ったワザの必要なエネルギーの数（記号の数）を
    引いた数（v0.4c の ``ExtraEnergy`` と同じ読み方。色の問いは TE1・RB1・BZ2・MEC1・CE1・CE2）。"""

    energy_type: EnergyType
    max_extra: int

    def count(self, run: AttackRun) -> int:
        attacker = run.attacker()
        transform_energy_question(run, attacker, self.energy_type, cards=False)
        if any(t is EnergyType.COLORLESS for t in run.attack.cost):
            raise RuntimeError("必要なエネルギーに無色がまざるワザの多いエネルギーの数え方（HC4）は、配分の単位に使わない（エンジンの不具合）")
        return min(max(0, E.typed_unit_count(run.state, attacker, self.energy_type) - len(run.attack.cost)), self.max_extra)


@dataclass(frozen=True)
class CoinHeadsUnits:
    """配る単位: この要素でコインを ``coins`` 枚投げた「おもて」の数（v0.115。ゴローンの「がんせきくだき」の「コインを2枚投げ、「おもて」の数×10のダメージを、…わりふって与える」）。
    結果は「おもて」の数だけを使う（先読みは「おもて」の数でまとめる）。配る先が決まってから投げ、投げてから配分を決める（配分を先に固定しない）。"""

    coins: int


@dataclass(frozen=True)
class DiscardedUnits:
    """配る単位: トラッシュの要素 ``discard`` で実際にトラッシュしたカードの枚数（v0.115。ゴローニャの「ロックブラスト」の「トラッシュした数ぶん、相手の場のポケモンを選ぶ」）。"""

    discard: str

    def count(self, run: AttackRun) -> int:
        discarded = run.fs.results.get(self.discard)
        return 0 if discarded is None else len(discarded.cards)


@dataclass(frozen=True)
class FixedUnits:
    """配る単位: 決まった数（v0.122。わるいフシギソウの「みだれうち」の「相手プレイヤーが、3回選ぶ」）。"""

    units: int

    def count(self, run: AttackRun) -> int:
        return self.units


CHOOSER_ATTACKER = "attacker"  # v0.122: 配分を選ぶのはワザを使ったプレイヤー（v0.115 からの既定）
CHOOSER_OPPONENT = "opponent"  # v0.122: 配分を選ぶのはワザを使ったプレイヤーの相手（みだれうち）


@dataclass(frozen=True)
class AllocateDamage(Element):
    """得た単位（``units``）× ``per`` のダメージを、相手の場（``scope``: 控えだけ ``TARGET_BENCH``・対戦ポケモンと控え ``TARGET_IN_PLAY``）のポケモンに、ワザを使ったプレイヤーが選んだ配分で、
    「弱点・抵抗力」に関係なく与える（v0.115。シードラの「ウォーターボム」・ゴローンの「がんせきくだき」・ゴローニャの「ロックブラスト」。docs 4.3 節）。

    - 配分は、選べるポケモン（バトル場 → ベンチの並び。``effects.target_candidates``）ごとの単位の数の組で、合計はちょうど得た単位の数（対象があれば得た分をすべて配る。「好きなように」を
      合計を減らすことと読まない）。1 匹に集めても、分けてもよい。同じポケモンに配った単位は合算し、そのポケモンに 1 回だけ ``per`` × 単位の数のダメージを与える（1 単位ずつ別のダメージに
      しない。ディフェンダー・受けるときのコイン・「ダメージを受けたとき」の効果の回数が変わる）。ロックブラストの「同じポケモンを2回以上選んでもよい」は、同じポケモンへの単位の数で表す
    - 決定 ``ALLOCATE_DAMAGE``（ちょうど 1 つ。選べるものは配分の表 ``table`` の位置。表と配る先の番号・単位の数・1 単位のダメージを続きの情報 ``allocation`` に置く。答えのときに、今の場の
      配る先・表と照らす）。配る先が 1 匹でも出す。単位の数が 0・配る先がなければ決定を出さない（処理の対象がない。p.309）。先読みはすべての配分を試す
    - 単位をこの要素のコインで決める（``CoinHeadsUnits``）なら、配る先がいなければ投げず、配る先がどれもダメージの要素を無効にする状態なら投げるかが決まらない（v0.56 と同じ問い）。
      ナツメのESPのやり直しはそのコインだけ（決定のあとはこの要素をもう一度処理し、配分はやり直したあとの単位で決める）
    - 与える順は配る先の並び（相手の対戦ポケモン → 控え）。相手の対戦ポケモンは p.320 の (1)、控えは (2)。控えへのダメージは［ベンチガード］の決定を出しうる（``guarded_damages``）。結果は
      ログ ``damage_allocated``（配る先・単位の数・1 単位のダメージ）と、最後のダメージの結果（``fs.results[name]``）"""

    units: Any
    per: int
    scope: str = E.TARGET_BENCH
    name: str = "allocated_damage"
    # v0.122（docs/unown-fossil-retreat-reactions-v0.122.md 5 章）: 配分を選ぶプレイヤー（``CHOOSER_OPPONENT`` はワザを使ったプレイヤーの相手。みだれうち）。ダメージを与えるのはワザを使った
    # ポケモンのまま（弱点・抵抗力に関係なく。受ける判定・無効・反応は同じ）。ログ ``damage_allocated`` には相手が選んだときだけ ``chooser`` を書く（v0.121 までの形を変えない）
    chooser: str = CHOOSER_ATTACKER
    phase: ClassVar[Phase] = Phase.DAMAGE
    guards_bench: ClassVar[bool] = True
    decision_kind: ClassVar[str] = ALLOCATE_DAMAGE

    def __post_init__(self) -> None:
        if self.scope not in (E.TARGET_BENCH, E.TARGET_IN_PLAY):
            raise ValueError(f"配る先の範囲 {self.scope!r} は相手の控え・相手の場")
        if self.chooser not in (CHOOSER_ATTACKER, CHOOSER_OPPONENT):
            raise ValueError(f"配分を選ぶプレイヤー {self.chooser!r} は {CHOOSER_ATTACKER} か {CHOOSER_OPPONENT}")
        if type(self.per) is not int or self.per <= 0 or self.per % 10:
            raise ValueError(f"1 単位のダメージは 10 の倍数の正の数（{self.per!r}）")

    def candidates(self, run: AttackRun) -> list[tuple[int, PokemonInPlay]]:
        return E.target_candidates(run.state, run.player, E.TARGET_SIDE_OPPONENT, self.scope)

    def coin_receiver(self) -> str | None:
        return "bench" if isinstance(self.units, CoinHeadsUnits) else None

    def has_target(self, run: AttackRun) -> bool:
        return bool(self.candidates(run))

    def void_for_all(self, run: AttackRun) -> bool:
        from .kernel import first_void

        targets = self.candidates(run)
        return bool(targets) and all(first_void(run.res, run.incoming(), owner, pokemon) is not None for owner, pokemon in targets)

    def run(self, run: AttackRun) -> bool:
        targets = self.candidates(run)
        if isinstance(self.units, CoinHeadsUnits):
            if not targets:
                run.fs.coins[self.name] = CoinFlips(())
                return False
            if self.void_for_all(run):
                raise run.res.question("prevented_coin_damage", f"ダメージを受けないポケモン {[p.pokemon_id for _, p in targets]} に配るダメージだけを決めるコイン")
            flips = run.flip(self.units.coins, by_heads=True)
            run.fs.coins[self.name] = flips
            units = flips.heads
        else:
            units = self.units.count(run)
        if not units or not targets:
            return False
        ids = tuple(pokemon.pokemon_id for _, pokemon in targets)
        table = E.damage_allocations(units, len(ids))
        chooser = run.player if self.chooser == CHOOSER_ATTACKER else 1 - run.player
        run.suspend(kind=ALLOCATE_DAMAGE, player=chooser, options=tuple(range(len(table))), carry=True,
                    extra=(("allocation", (ids, units, self.per)), ("table", table)))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if decision.kind != ALLOCATE_DAMAGE:
            raise RuntimeError(f"配分の要素の決定 {decision.kind} は扱わない（エンジンの不具合）")
        ids, units, per = run.carried["allocation"]
        table = tuple(tuple(row) for row in run.carried["table"])
        targets = self.candidates(run)
        if (tuple(pokemon.pokemon_id for _, pokemon in targets) != tuple(ids) or table != E.damage_allocations(units, len(ids)) or per != self.per
                or len(choices) != 1 or not 0 <= choices[0] < len(table)):
            raise RuntimeError(f"配分の決定の答え {choices}・配る先 {ids} が、今の場・表と合わない（エンジンの不具合）")
        counts = table[choices[0]]
        attacker = run.attacker()
        extra = {} if self.chooser == CHOOSER_ATTACKER else {"chooser": 1 - run.player}  # v0.122
        run.state.add_event("damage_allocated", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            targets=tuple(ids), counts=tuple(counts), per=per, units=units, **extra)
        entries = [(target_kind(run, owner, pokemon), pokemon.pokemon_id, per * count, False) for (owner, pokemon), count in zip(targets, counts) if count]
        guarded_damages(run, self, entries, record=True)


UP_TO_DISCARD_ZERO_CODE = "UNRESOLVED_DISCARD_UP_TO_ZERO"


@dataclass(frozen=True)
class DiscardOwnEnergyUpTo(OptionalDiscardForBonus):
    """自分についている ``energy_type`` エネルギーカードを最大 ``max_cards`` 枚トラッシュする（v0.115。ゴローニャの「ロックブラスト」の前半。「のぞむなら」のない「最大」）。結果は
    ``Discarded``（実際にトラッシュしたカード。あとの ``AllocateDamage`` の ``DiscardedUnits`` がその枚数を数える）。

    - 範囲はワザを実際に使ったポケモン（写して使えば写したポケモン）。数えるのはカード（その色の基本エネルギーカード。色の問い TE1・RB1・BZ2・MEC1・CE3）。場からトラッシュに置くので、
      リサイクルエネルギー・エコロジムの処理（原因はワザ、実際に使ったのは自分）を通す（v0.82 の ``OptionalDiscardForBonus`` と同じ）
    - 選べるカードがあるとき 0 枚を選べるかは決められない（kyuura の UQ-UP-TO-ZERO-CHOICE と同じ形の問い。「好きなだけ」の HC5・トラッシュからつける HC7・控えを選ぶ GS1 とは別の文面の問いで、
      それらの答えで決めない。RKB1）。選べるが選ぶと止める（答えのときに止め、決定は待ったまま。先読みは試さない）。1 枚以上は選べる。選べるカードがないなら、トラッシュする対象がない
      （p.309。決定を出さない。0 枚をトラッシュした扱いで、あとのポケモンを選ばない）。どれもワザの失敗ではない"""

    include_bench: bool = False
    max_cards: int | None = 5

    def __post_init__(self) -> None:
        if self.include_bench or type(self.max_cards) is not int or self.max_cards < 1:
            raise ValueError("「最大」のトラッシュは、ワザを使ったポケモンについているカードで、上限がある")

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return [answer for answer in super().dry_choices(run, decision) if answer]  # 0 枚は答えのときに止める（RKB1）

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if not choices:
            raise UnsupportedError(
                UP_TO_DISCARD_ZERO_CODE,
                f"「自分についている「{self.energy_type.ja}」エネルギーカードを最大{self.max_cards}枚トラッシュして」（「のぞむなら」「てよい」のない「最大」）で、選べるカードがあるときに"
                "0 枚を選べるかは、印刷の文面・kyuura の記録から決められないので扱わない（RKB1。kyuura の UQ-UP-TO-ZERO-CHOICE と同じ形の問い）。1 枚以上を選ぶ",
            )
        super().resume(run, decision, choices)


@dataclass(frozen=True)
class AlsoTargetDamage(TargetDamage):
    """先に選んだ相手のポケモン（``ChooseTarget`` の ``chosen``）にも ``base`` のダメージ（v0.115。イシツブテ（NIP1X-004）の「いしなだれ」の「相手のポケモンを1匹選び、そのポケモンにも、
    「弱点・抵抗力」に関係なく、10ダメージ」。相手の対戦ポケモンへの目安のダメージのあと）。

    - 選べるのは相手の場のポケモン（バトル場 → ベンチ）。選べるものを控えだけにしない（説明は「相手のポケモン」）
    - 相手の対戦ポケモンを選んだとき、目安のダメージを受けたポケモンに「にも」のダメージを別の 10 として与えるか、目安と合わせた 1 つのダメージとするか（選べるか自体も）は、印刷の文面・
      kyuura の記録から決められない（SLD1。弱点・抵抗力・ディフェンダー・受けるときのコイン・「ダメージを受けたとき」の効果の回数で結果が変わる）。相手の対戦ポケモンは、選べるが選ぶと
      止める（``choice_problem``。控えは選べる）。控えがいなければ選べるのは相手の対戦ポケモンだけなので、選ぶ前に止める（先読みが宣言の前に見つける）。ロックブラストの選ばれた回数の
      合算と同じとみなさない"""

    def choice_problem(self, run: AttackRun, owner: int, pokemon: PokemonInPlay) -> tuple[str, str] | None:
        if owner != run.player and run.state.players[owner].active is pokemon:
            return "chosen_active_extra_damage", f"相手の対戦ポケモン {pokemon.pokemon_id}（ワザ {run.key} の目安のダメージを受けたポケモン）"
        return super().choice_problem(run, owner, pokemon)


BUILDERS |= {
    # しょうげきは: コイン 1 枚 →「おもて」なら相手の場のポケモン全員に amount（弱点・抵抗力に関係なく。バトル場 → 控え）→ その後、相手が選ぶ控えと入れ替える（「おもて」のときだけ）
    E.CoinSpreadDamageThenOpponentSwitch: lambda e: (
        Coin("coin"), Damage(OPP, Fixed(e.amount), weakness_resistance=False, gate=("coin", HEADS)), BenchDamage(Fixed(e.amount), gate=("coin", HEADS)),
        ForceSwitch(gate=("coin", HEADS)),
    ),
    # びっくりサンダー: ダメージ（目安）→ 条件つきで続けて投げる 2 枚のコイン → 相手の控え全員にも（HH・HT の量。弱点・抵抗力に関係なく）
    E.DamageThenChainedCoinsBenchDamage: lambda e: (Damage(OPP, Printed()), ChainedCoinsBenchDamage((e.heads_heads, e.heads_tails))),
    # すなあらし: おたがいの場の、今のタイプが excluded でないポケモン全員に amount（弱点・抵抗力に関係なく。相手の対戦ポケモン → 自分 → 相手の控え → 自分の控え。みんなでばくはつと同じ並び）
    E.SpreadDamageExceptType: lambda e: (
        Damage(OPP, Fixed(e.amount), weakness_resistance=False, name="spread_damage", exclude_type=e.excluded),
        Damage(SELF, Fixed(e.amount), weakness_resistance=False, name="self_damage", exclude_type=e.excluded),
        BenchDamage(Fixed(e.amount), exclude_type=e.excluded),
        BenchDamage(Fixed(e.amount), exclude_type=e.excluded, own=True, name="own_bench_damage"),
    ),
    # なぎたおす: ダメージ（目安）→ おたがいの控え全員に 1 枚ずつ（相手側から）→「おもて」の控えに amount（弱点・抵抗力に関係なく）
    E.DamageThenCoinPerBothBenches: lambda e: (Damage(OPP, Printed()), CoinPerBenchPokemon(e.amount)),
    # サイコスプラッシュ: 相手の場のエネルギーカードをつけているポケモン全員に、それぞれのカードの枚数 × per（弱点・抵抗力に関係なく。バトル場 → 控え）
    E.EnergyCardsSpreadDamage: lambda e: (
        Damage(OPP, EnergyCardsOfReceiver(e.per), weakness_resistance=False, energy_cards=True),
        BenchDamage(EnergyCardsOfReceiver(e.per), energy_cards=True),
    ),
    # ばくれつしんか: コイン 1 枚 →「おもて」なら相手の場のポケモン全員に amount → その後、山札の名前の合う進化カードを必ず自分に重ねる（「おもて」のときだけ。見たら切る）
    E.CoinSpreadDamageThenEvolveNamedFromDeck: lambda e: (
        Coin("coin"), Damage(OPP, Fixed(e.amount), weakness_resistance=False, gate=("coin", HEADS)), BenchDamage(Fixed(e.amount), gate=("coin", HEADS)),
        EvolveAttackerFromDeck(e.evolves_from, gate=("coin", HEADS), required=True, shuffle_if_looked=True, card_name=e.card_name),
    ),
    # やまくだき: 自分についている energy_type エネルギーカードの枚数のワザ全体のコイン →「おもて」の数 × per → その後、「おもて」の数ぶん相手の山札の上からトラッシュ（同じコイン）
    E.CoinsPerOwnEnergyCardsDamageThenMillOpponent: lambda e: (
        Coin("coin", per_attached=e.energy_type), Damage(OPP, HeadsOfCoin("coin", e.per)), MillOpponentDeck(heads_of="coin"),
    ),
    # ぶんなげる: 相手に控えがいれば reduced、いなければ目安 → 控えがいれば 1 匹を選んでそのポケモンにも bench_damage（弱点・抵抗力に関係なく）
    E.ReducedDamageThenChosenBenchDamage: lambda e: (
        Damage(OPP, AmountIfOpponentBench(e.reduced)), ChosenBenchDamage(Fixed(e.bench_damage), local_coin=None, weakness_resistance=False),
    ),
    # ちていいどう: 相手の控えから最大 max_targets 匹を選び、それぞれに bench_damage（0 匹は GS1）→ 次の自分の番、使ったポケモンはワザを使えない（すべてのワザ）
    E.ChosenBenchTargetsThenSelfCannotAttack: lambda e: (ChosenBenchDamages(Fixed(e.bench_damage), e.max_targets), SelfCannotAttack()),
    # ウォーターボム: ダメージ（目安）→ 多い energy_type エネルギー（max_extra まで）の数 × per を相手の控えに配る
    E.DamageThenAllocateExtraEnergyToBench: lambda e: (
        Damage(OPP, Printed()), AllocateDamage(ExtraTypedUnits(e.energy_type, e.max_extra), e.per),
    ),
    # がんせきくだき: ダメージ（目安）→ この要素のコイン coins 枚の「おもて」の数 × per を相手の控えに配る
    E.DamageThenCoinsAllocateToBench: lambda e: (Damage(OPP, Printed()), AllocateDamage(CoinHeadsUnits(e.coins), e.per)),
    # ロックブラスト: 自分の energy_type エネルギーカードを最大 max_cards 枚トラッシュ（0 枚は RKB1）→ トラッシュした枚数ぶん、相手の場のポケモンに per ずつ配る（同じポケモンは回数を合算）
    E.DiscardEnergyUpToThenAllocateToOpponentPokemon: lambda e: (
        DiscardOwnEnergyUpTo(e.energy_type, max_cards=e.max_cards), AllocateDamage(DiscardedUnits("discard"), e.per, scope=E.TARGET_IN_PLAY),
    ),
    # いしなだれ: ダメージ（目安）→ 相手の場のポケモンを 1 匹選ぶ（相手の対戦ポケモンは SLD1 で選ぶと止める）→ そのポケモンにも amount（弱点・抵抗力に関係なく）
    E.DamageThenChosenOpponentPokemonDamage: lambda e: (
        Damage(OPP, Printed()), ChooseTarget(side=E.TARGET_SIDE_OPPONENT, scope=E.TARGET_IN_PLAY), AlsoTargetDamage(Fixed(e.amount)),
    ),
}



# ---------------------------------------------------------------- v0.116（docs/energy-movement-attachment-devolution-v0.116.md）


@dataclass(frozen=True)
class OpponentAttachStatusTrigger(Element):
    """相手の対戦ポケモン（このワザを受けた相手）に、次の相手の番にエネルギーカードがついたら ``condition``（どく・マヒ）になる持続する効果（``StatusOnEnergyAttach``）を与える（v0.116。
    クロバットの「しこみどく」・ユンゲラーの「エナジーショック」。docs 4 章）。ワザを受けたときにはどく・マヒにしない。

    - ダメージの要素のあとに、受けた相手が効果の要素（``ATTACH_STATUS_ELEMENT``）を受けるかを ``reaches`` で決める（「ワザをうけない」状態・エフェクトガード・「とうめい」・
      ［ニュートラルシールド］。ダメージだけを受けない状態（かたまる）なら効果は受ける）。このワザで HP 以上なら処理の対象がない（p.309。こんじょうは G37）
    - 効果の ``source_card`` はワザを実際に使ったポケモンのいちばん上のカード（発生源を場の位置で探さない。効果のはたらき方は発生源の場所によらない）"""

    condition: str
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.ATTACH_STATUS_ELEMENT

    def has_target(self, run: AttackRun) -> bool:
        return not run.knocked_out(run.opponent_active())

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if not reaches(run.res, run.fs, opponent, target, E.ATTACH_STATUS_ELEMENT):
            return False
        attacker = run.attacker()
        turn = run.state.turn_number
        effect = StatusOnEnergyAttach(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn + StatusOnEnergyAttach.turns_until_active,
                                      condition=self.condition, attack=str(run.key))
        add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key), condition=self.condition)
        return False


@dataclass(frozen=True)
class OpponentEvolutionLock(OpponentRetreatLock):
    """次の相手の番、相手プレイヤーはこのワザを受けた相手（相手の対戦ポケモン）を、手札・トレーナーの効果で進化させることができない（v0.116。わるいオムスターの「やみのしょくしゅ」。
    持続する効果 ``EvolutionLock``）。v0.41 の ``OpponentRetreatLock`` と同じ形（対象が HP 以上なら与えない・「とうめい」・「ワザをうけない」状態の評価）で、与える効果だけが違う。"""

    opponent_element: ClassVar[str] = E.EVOLUTION_LOCK_ELEMENT

    def run(self, run: AttackRun) -> bool:
        return _opponent_lock(self, run, EvolutionLock, E.EVOLUTION_LOCK_ELEMENT)


@dataclass(frozen=True)
class BatonPass(Element):
    """自分のベンチにいる「``energy_type``」ポケモンを 1 匹選ぶ。自分についている「エネルギーカード」をすべてはがし、選んだポケモンに付け替えてから、選んだポケモンを自分と入れ替える
    （v0.116。レディアンの「バトンタッチ」。``effects.DamageThenMoveAllEnergyToTypeBenchThenSwitch``。docs 5 章）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。``effects.baton_pass_targets``。今のタイプ。VS1 などで決まらない・うらのカードは選べるが選ぶと止める。どれもそうなら止める）。
      選べる控えがいなければ、付け替えも入れ替えもしない（p.309。ログ ``effect_skipped`` の ``no_target``）
    - 付け替え: ワザを実際に使ったポケモンについているエネルギーカードを、ついている順に 1 枚ずつ、選んだポケモンに付け替える（ログ ``attack_attach_energy``。同じ uid のまま。手札・
      トラッシュを通さない）。1 枚ごとの反応（``attached_in_attack``。［ほのおでかいふく］など）。選んだポケモンが受けない（「とうめい」）なら、はがしたカードは持ち主のトラッシュ（T36 と
      同じ読み方。原因は自分のワザ。リサイクルエネルギーの処理を通す）
    - すべて付け替えてから入れ替える（``effects._switch_active_with_bench``。効果の入れ替えで「にげる」ではない）。「バトル場をはなれられない」なら入れ替える部分は起こらない（v0.93）
    - ワザを使ったポケモンがこのワザで HP 以上（相手の「はんげき」など）なら処理の対象がない（p.309。ログ ``effect_skipped``）"""

    energy_type: EnergyType
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def run(self, run: AttackRun) -> bool:
        state = run.state
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.ko_prevention_conflict(attacker, run.player)
            state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            element="baton_pass", reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        options, stops = E.baton_pass_targets(state, run.player, self.energy_type)
        if not options:
            state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            element="baton_pass", reason="no_target")
            return False
        if len(stops) == len(options):
            raise UnsupportedError(stops[0][1], stops[0][2])  # 止めない選べる控えがない（FD1・VS1 など。答えのない決定を出さない）
        extra: tuple = ()
        if stops:
            extra = (("unresolved_choices", tuple(stop[0] for stop in stops)), ("unresolved_code", stops[0][1]), ("unresolved_reason", stops[0][2]),
                     ("unresolved_detail", stops))
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=options, carry=True, extra=extra)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        attacker = run.attacker()
        options, stops = E.baton_pass_targets(state, run.player, self.energy_type)
        if len(choices) != 1 or choices[0] not in options or choices[0] in {stop[0] for stop in stops}:
            raise RuntimeError(f"バトンタッチで選んだポケモン {choices} が、選べる自分の控え {options} ではない（エンジンの不具合）")
        target = next(pokemon for pokemon in state.players[run.player].bench if pokemon.pokemon_id == choices[0])
        cards = tuple(attacker.energy)
        if cards and reaches(run.res, run.fs, run.player, target, E.ENERGY_ATTACH_ELEMENT):
            for uid in cards:
                attacker.energy.remove(uid)
                target.energy.append(uid)
                state.add_event("attack_attach_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                energy=uid, to_pokemon_id=target.pokemon_id)
                attached_in_attack(run, run.player, target, (uid,), moved=True)
        elif cards:
            E.discard_energy_from_play(
                state, attacker, cards, cause=E.DISCARD_BY_ATTACK, by_player=run.player,
                log=lambda: [state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                             energy=uid, reason="evaded", to_pokemon_id=target.pokemon_id) for uid in cards])
        if _leave_prevented(run, run.player, attacker, E.LEAVE_SWITCH, None):
            return  # 付け替えた（その部分は起こる）が、入れ替える部分は起こらない
        if state.players[run.player].active is not attacker:
            raise RuntimeError(f"バトンタッチを使ったポケモン {attacker.pokemon_id} がバトル場にいない（エンジンの不具合）")
        E._switch_active_with_bench(state, run.player, target.pokemon_id, effect=str(run.key))


@dataclass(frozen=True)
class SelfCounters(Element):
    """ワザを使ったポケモン自身にダメージカウンターを ``counters`` 個のせる（v0.116。ニョロゾの「はらだいこ」の前半）。ワザのダメージではない（ダメージの計算・弱点・抵抗力・防御・
    「ダメージを受けたとき」の効果は関係しない。GR-2000-P320-COUNTER-MOVE と同じく「ダメージを受けた」ことにならない）。自分への効果なので相手の状態によらない。ログ
    ``place_damage_counters``。のせて HP 以上になったら、ワザのあとのきぜつの判定（``_counters_changed``。こんじょうは使えない）。"""

    counters: int
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        attacker = run.attacker()
        per = state.rules.damage_per_counter
        before = attacker.damage
        attacker.damage = before + self.counters * per
        state.add_event("place_damage_counters", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                        counters=self.counters, amount=self.counters * per, damage_before=before, total_damage=attacker.damage, attacker=run.player,
                        attacker_pokemon_id=run.fs.frame.source_pid)
        _counters_changed(run, attacker, before)
        return False


@dataclass(frozen=True)
class AttachBasicEnergyFromDeckToSelf(Element):
    """自分の山札から「基本エネルギーカード」を ``cards`` 枚選び出し、自分（ワザを使ったポケモン）につけ、その山札をよく切る（v0.116。ニョロゾの「はらだいこ」の後半）。

    - ワザを使ったポケモンがこのワザで HP 以上（前の要素のダメージカウンターなど）なら処理の対象がないので、山札を見ない・つけない・切らない（p.309。ログ ``effect_skipped``）。
      エネルギーカードをつけることができない（クリスタルビーム。公開の情報）なら、つけないで山札を切る（v0.59 の ``AttachFromDeck`` と同じ。ログ ``attach_energy_from_deck_none``）
    - 山札の基本エネルギーカード（どのタイプでも。``effects.deck_basic_energy_cards``）が c 枚: c ≧ ``cards`` ならちょうど ``cards`` 枚を選ぶ（決定 ``ATTACH_FROM_DECK``）。c = 0 なら選べる
      もののない決定（v0.84 の A3。山札の中身で決定の有無を変えない）。0 < c < ``cards`` は FC1（v0.113 の「ゆうでん」と同じ）。選べるものの数は決めるプレイヤーだけに見える
    - つけるのは山札から直接（``zones.attach_from_deck``。ログ ``attach_energy_from_deck``。手札からつける操作・あまごいの回数に数えない）。すべてつけてから 1 枚ずつ反応
      （``attached_in_attack``。ついた時に発動する相手のワザの持続効果も）。どの場合も最後に山札を 1 回切る"""

    cards: int
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = ATTACH_FROM_DECK

    def run(self, run: AttackRun) -> bool:
        state = run.state
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.ko_prevention_conflict(attacker, run.player)
            state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            element="attach_from_deck", reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        if E.energy_attach_block(state, attacker) is not None:
            self._none(run, attacker, "attach_prevented")
            return False
        options = E.deck_basic_energy_cards(state, run.player)
        if 0 < len(options) < self.cards:
            raise run.res.question("stated_cards_short", f"山札の基本エネルギーカード {len(options)} 枚（{self.cards} 枚を選び出す）")
        count = self.cards if len(options) >= self.cards else 0
        run.suspend(kind=ATTACH_FROM_DECK, player=run.player, options=options, min_choices=count, max_choices=count, carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        attacker = run.attacker()
        options = E.deck_basic_energy_cards(state, run.player)
        wanted = self.cards if len(options) >= self.cards else 0
        if len(set(choices)) != len(choices) or any(card not in options for card in choices) or len(choices) != wanted:
            raise RuntimeError(f"つけるカード {choices} が、山札の基本エネルギーカードの {wanted} 枚ではない（エンジンの不具合）")
        if not choices:
            self._none(run, attacker, "no_candidates")
            return
        cards = tuple(uid for uid in options if uid in choices)  # 山札の uid の小さい順につける（選んだ順によらない）
        for card in cards:
            attach_from_deck(state, run.player, card, attacker)
            state.add_event("attach_energy_from_deck", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), card=card)
        attached_in_attack(run, run.player, attacker, cards)
        shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        # 同じカード id の基本エネルギーカードは、どれをつけても同じ形の状態（v0.46 の AttachFromHand と同じまとめ方）
        return card_id_answers(run.state, decision, (decision.min_choices,))

    def _none(self, run: AttackRun, attacker: PokemonInPlay, reason: str) -> None:
        run.state.add_event("attach_energy_from_deck_none", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy_type=None, reason=reason)
        shuffle_in_attack(run, self, run.player)


@dataclass(frozen=True)
class MoveOpponentFieldEnergy(Element):
    """相手の場のエネルギーカード（特殊エネルギー以外）を 1 枚選んではがす。その後、相手の場のポケモンを 1 匹選び、はがしたエネルギーをそのポケモンにつける（v0.116。ミュウツーの
    「エナジーコントロール」の、失敗のコインのあと。``effects.FailOnTailsMoveOpponentFieldEnergy``。docs 5 章）。

    - 選ぶのはワザを使ったプレイヤー: はがすカード（決定 ``MOVE_OPPONENT_ENERGY``。``context`` の ``"stage"`` は ``"energy"``。``effects.opponent_field_energy_options``。場のレインボー
      エネルギーは RB3 で選べるが選ぶと止める）→ はがす前に、そのカードのついているポケモンが効果の要素（``ENERGY_MOVE_ELEMENT``）を受けるかを ``reaches`` で決める（受けなければ何もしない）
      → つけるポケモン（決定 ``SELECT_POKEMON``。``"stage"`` は ``"target"``。相手の場のポケモン。はがしたポケモン自身も選べる）。2 つの決定のあいだ、カードはついたまま
    - つけるポケモンが受けない（``ENERGY_ATTACH_ELEMENT``。「とうめい」）なら、はがしたカードは持ち主のトラッシュ（T36 と同じ読み方。KEEP でなくなる効果なら v0.101 の KP3）。手札からつける
      操作ではない（つけたときの特殊エネルギーの効果は起こらない）。ついたカードへの反応は ``attached_in_attack``（つけ替え）
    - 相手の場にエネルギーカードがなければ処理の対象がない（p.309）"""

    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.ENERGY_MOVE_ELEMENT  # 宣言（G37 の理由の文）。受けるかは、はがすポケモン・つけるポケモンごとに ``reaches`` で決める

    def decides(self, kind: str) -> bool:
        return kind in (MOVE_OPPONENT_ENERGY, SELECT_POKEMON)

    def has_target(self, run: AttackRun) -> bool:
        return bool(E.opponent_field_energy_options(run.state, run.player)[0])

    def run(self, run: AttackRun) -> bool:
        options, rainbow = E.opponent_field_energy_options(run.state, run.player)
        if not options:
            return False
        if len(rainbow) == len(options):
            raise run.res.question("rainbow_basic_energy_card", f"相手の場のレインボーエネルギー {list(rainbow)}（エナジーコントロールの「特殊エネルギー以外」）")
        extra = (("stage", "energy"),) + _unresolved_extra(rainbow, E.RAINBOW_BASIC_CODE, E.RAINBOW_BASIC_REASON)
        run.suspend(kind=MOVE_OPPONENT_ENERGY, player=run.player, options=options, carry=True, extra=extra)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        opponent = 1 - run.player
        p = state.players[opponent]
        if run.carried.get("stage") == "energy":
            options, rainbow = E.opponent_field_energy_options(state, run.player)
            if len(choices) != 1 or choices[0] not in options or choices[0] in rainbow:
                raise RuntimeError(f"はがすカード {choices} が、相手の場の選べるエネルギーカードではない（エンジンの不具合）")
            source = next(pokemon for pokemon in p.in_play() if choices[0] in pokemon.energy)
            if not reaches(run.res, run.fs, opponent, source, E.ENERGY_MOVE_ELEMENT):
                return  # はがすポケモンが効果を受けない（「ワザをうけない」状態・「とうめい」）。はがさない
            run.suspend(kind=SELECT_POKEMON, player=run.player, options=[pokemon.pokemon_id for pokemon in p.in_play()], carry=True,
                        extra=(("stage", "target"), ("energy", choices[0]), ("source", source.pokemon_id)))
            return
        energy = run.carried["energy"]
        source = next((pokemon for pokemon in p.in_play() if pokemon.pokemon_id == run.carried.get("source")), None)
        destination = next((pokemon for pokemon in p.in_play() if pokemon.pokemon_id == choices[0]), None)
        if source is None or energy not in source.energy or destination is None or len(choices) != 1:
            raise RuntimeError(f"つけ替えるカード {energy}・はがすポケモン {run.carried.get('source')}・つけるポケモン {choices} が正しくない（エンジンの不具合）")
        void = E.energy_discard_void(state, source, cause=E.DISCARD_BY_ATTACK, by_player=run.player)
        returns = () if void is not None else E.energy_discard_plan(state, source, (energy,), cause=E.DISCARD_BY_ATTACK, by_player=run.player)  # トラッシュに置くときだけ使う
        source.energy.remove(energy)
        base = {"player": opponent, "pokemon": source.card, "pokemon_id": source.pokemon_id, "energy": energy, "to_pokemon_id": destination.pokemon_id,
                "effect": str(run.key), "attacker": run.player, "attacker_pokemon_id": run.fs.frame.source_pid}
        if reaches(run.res, run.fs, opponent, destination, E.ENERGY_ATTACH_ELEMENT):
            destination.energy.append(energy)
            state.add_event("move_opponent_energy", **base, result="attached")
            attached_in_attack(run, opponent, destination, (energy,), moved=True)
        else:
            if void is not None:
                raise run.res.question("keep_detached_energy_discard", f"ポケモン {source.pokemon_id} からはがしたエネルギーカード {energy}（つけるポケモン {destination.pokemon_id} が受けない）")
            p.discard.append(energy)
            state.add_event("move_opponent_energy", **base, result="evaded")
            E.return_discarded_energy(state, returns)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        stopped = set(decision.context_value("unresolved_choices", ()))
        return [answer for answer in all_answers(decision) if not stopped & set(answer)]


def _single_effect_target_question(run: AttackRun, candidates: tuple[int, ...]) -> None:
    """v0.116: コインが決める、相手の場のポケモンを選ぶ効果の要素で、選べるのが相手の対戦ポケモン 1 匹だけなら、効果だけを決めるコインの問い（T19b・HC3。``effect_coin_questions``）。
    控えも選べるなら、選んだあとに ``reaches`` で決める（投げる）。"""
    active = run.opponent_active()
    if active is not None and candidates == (active.pokemon_id,):
        effect_coin_questions(run, 1 - run.player, active)


@dataclass(frozen=True)
class DevolveOpponentToDeck(Element):
    """相手の場の「進化ポケモン」を 1 匹選ぶ。その後、そのポケモンにのっている「進化カード」を 1 枚はがし、そのポケモンを退化させる。はがした「進化カード」は、相手の山札にもどし、その
    山札をよく切る（v0.116。わるいオムスターの「げんしのしずく」の「おもて」。``effects.CoinDevolveOpponentEvolvedToDeck``。docs 6 章）。

    - 選ぶのはワザを使ったプレイヤー（決定 ``SELECT_POKEMON``。``effects.opponent_evolved_targets``。相手の場だけ）。いなければコインを投げない（p.309。``has_target``）。選べるのが相手の
      対戦ポケモンだけで、それが効果の要素を受けないなら、コインの前に T19b・HC3。「ばける」（DV5）・ベイビィから進化したたねポケモン（NB2）は選べるが選ぶと止める（どれもそうなら止める）
    - はがす前に ``reaches``（``DEVOLVE_ELEMENT``）。はがすのは実際の重なりのいちばん上 1 枚（``evolution.devolve`` の ``DEVOLVE_TO_DECK``。持ち主の山札）→ 最大HPが下がったきぜつの原因
      （``_hp_dropped_in_attack``）→ その山札を切る（``shuffle_in_attack``。受けなかったときは切らない）"""

    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_POKEMON
    opponent_element: ClassVar[str] = E.DEVOLVE_ELEMENT  # v0.50 の ``DevolveChosenPokemon`` と同じ宣言（G37 の理由の文）

    def has_target(self, run: AttackRun) -> bool:
        options = E.opponent_evolved_targets(run.state, run.player)
        if options:
            _single_effect_target_question(run, options)
        return bool(options)

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        state = run.state
        options = E.opponent_evolved_targets(state, run.player)
        if not options:
            state.add_event("devolve_none", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key))
            return False
        stops = E.opponent_devolve_stops(state, E.text_era(run.key.card_id), options)
        if len(stops) == len(options):
            raise UnsupportedError(*stops[options[0]])  # 止めない選べるポケモンがない（答えのない決定を出さない）
        extra: tuple = ()
        if stops:
            extra = (("unresolved_choices", tuple(stops)), ("unresolved_code", stops[next(iter(stops))][0]), ("unresolved_reason", stops[next(iter(stops))][1]),
                     ("unresolved_detail", tuple((pid, *problem) for pid, problem in stops.items())))
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=options, carry=True, extra=extra)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        options = E.opponent_evolved_targets(state, run.player)
        if len(choices) != 1 or choices[0] not in options or choices[0] in E.opponent_devolve_stops(state, E.text_era(run.key.card_id), options):
            raise RuntimeError(f"げんしのしずくで選んだポケモン {choices} が、選べる相手の進化ポケモンではない（エンジンの不具合）")
        owner, target = state.find_pokemon(choices[0])
        if not reaches(run.res, run.fs, owner, target, E.DEVOLVE_ELEMENT):
            return
        devolve(state, owner, target, 1, destination=DEVOLVE_TO_DECK, by_player=run.player, effect=str(run.key))
        _hp_dropped_in_attack(run)
        shuffle_in_attack(run, self, owner)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ()))
        return [answer for answer in all_answers(decision) if not blocked & set(answer)]


@dataclass(frozen=True)
class BenchFromOpponentDiscard(Element):
    """相手のトラッシュから「ベイビィポケモン」または「たねポケモン」を 1 枚選び出す。その後、そのカードにダメージカウンターを ``counters`` 個のせ、相手のベンチに出す。(相手のベンチに
    空きがないとき、このワザは失敗する。)（v0.116。わるいゴーストの「よびもどす」。``effects.BenchBabyOrBasicFromOpponentDiscardOrFail``。docs 6 章）。

    - 相手のベンチに空きがない（``stadiums.bench_limit``）ならワザの失敗（ログ ``attack_failed`` の ``reason`` ``opponent_bench_full``。選ばない）。空きがあり、選べるカードがなければ何もしない
      （p.309。ログ ``bench_from_discard_none``）
    - 選ぶのはワザを使ったプレイヤー（決定 ``BENCH_FROM_DISCARD``。``effects.discard_baby_or_basic`` の相手のトラッシュ。1 枚。省略できない）。カードの持ち主・出すベンチは相手
    - ``zones.bench_from_discard`` の ``counters``（ベンチに出す前にのせる。元気のかけらと同じ）。ログ ``bench_from_discard`` の ``counters``・``damage``。出したあとのダメージ・ワザの
      効果ではないので「とうめい」などは評価しない。のせたカウンターで HP 以上なら、ワザのあとのきぜつの判定（``_counters_changed``）。場に出たときの特殊能力は v0.51 の
      ``effects.discard_entry_power_guard``"""

    counters: int
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = BENCH_FROM_DISCARD

    def run(self, run: AttackRun) -> bool:
        state = run.state
        opponent = 1 - run.player
        if len(state.players[opponent].bench) >= bench_limit(state, opponent):
            run.fail("opponent_bench_full")
            return False
        if protected_discard(run, "bench_from_discard"):
            return False  # v0.119: ［アレルギーほうし］（カウンターをのせることもベンチに出すことも起こらない）
        candidates = E.discard_baby_or_basic(state, opponent)
        if not candidates:
            attacker = run.attacker()
            state.add_event("bench_from_discard_none", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key))
            return False
        run.suspend(kind=BENCH_FROM_DISCARD, player=run.player, options=candidates)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        opponent = 1 - run.player
        if len(choices) != 1 or choices[0] not in E.discard_baby_or_basic(state, opponent):
            raise RuntimeError(f"よびもどすで選んだカード {choices} が、相手のトラッシュのたね・ベイビィポケモンのカードではない（エンジンの不具合）")
        card = choices[0]
        E.discard_entry_power_guard(state, card)
        pokemon = bench_from_discard(state, card, counters=self.counters)
        attacker = run.attacker()
        E.log_bench_from_discard(state, pokemon, by_player=run.player, counters=self.counters,
                                 source={"pokemon": attacker.card, "pokemon_id": attacker.pokemon_id, "effect": str(run.key)})
        if self.counters:
            _counters_changed(run, pokemon, 0)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, (1,))


@dataclass(frozen=True)
class RegressToBasic(Element):
    """自分についている「進化カード」と「エネルギーカード」をすべてトラッシュして、「たねポケモン」にもどる（v0.116。ウツドンの「さいせい」の後半。前の ``HealAllCounters`` のあと。
    ``effects.HealAllThenRegressToBasic``。docs 6 章）。

    - 「進化カード」「たねポケモン」は処理に使う文面の版（``effects.text_era``）で、実際の重なり（ベイビィをふくむ）から読む: いちばん下のカードの上のカードがどれも「進化カード」で、
      いちばん下のカードが「たねポケモン」に当たるときだけ処理する（neo の説明でベイビィが関わり決まらないなら NB1・NB2 で止める。ES3 はネオより前の説明なので決まる）
    - 重なりのカードを上からすべて持ち主のトラッシュに置く（``evolution.devolve`` の ``DEVOLVE_TO_DISCARD``。退化の共通の処理）→ ついているエネルギーカードをすべてトラッシュする（原因は
      自分のワザ。``effects.discard_energy_from_play``。ログ ``discard_energy``）。ついているトレーナーカードは残す。重なりがなければエネルギーカードだけ。「ばける」のポケモンは DV5
    - ワザを使ったポケモンがこのワザで HP 以上なら処理の対象がない（p.309）"""

    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.ko_prevention_conflict(attacker, run.player)
            state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            element="regress_to_basic", reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        if attacker.evolution_stack:
            if E.devolution_forbidden(state, attacker):
                raise run.res.question("devolution_target_disguised", f"ポケモン {attacker.pokemon_id}（さいせいの「進化カード」）")
            era = E.text_era(run.key.card_id)
            chain = (*attacker.evolution_stack, attacker.card)
            for uid in chain[1:]:
                definition = state.card_def(uid)
                if not definition.is_evolution_pokemon and definition.is_basic_pokemon and E.baby_evolution_card_in_text(era) is None:
                    raise UnsupportedError(E.NEO_EVOLUTION_CARD_BABY_CODE, f"ポケモン {attacker.pokemon_id} のたねポケモンカード {uid}（ベイビィから進化）: {E.NEO_EVOLUTION_CARD_BABY_REASON}")
            if E.card_is_basic_in_text(state.card_def(chain[0]), era) is None:
                raise E.neo_basic_baby_error(f"ポケモン {attacker.pokemon_id} のいちばん下のベイビィポケモンカード {chain[0]}（「たねポケモン」にもどる）")
            devolve(state, run.player, attacker, len(attacker.evolution_stack), destination=DEVOLVE_TO_DISCARD, by_player=run.player, effect=str(run.key))
            _hp_dropped_in_attack(run)
        cards = tuple(attacker.energy)
        if cards:
            E.discard_energy_from_play(
                state, attacker, cards, cause=E.DISCARD_BY_ATTACK, by_player=run.player,
                log=lambda: [state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                             energy=uid) for uid in cards])
        return False


@dataclass(frozen=True)
class RecoverSpecialEnergy(Element):
    """自分のトラッシュから「特殊エネルギーカード」を 1 枚選び出し、手札に加える（v0.116。ユンゲラーの「エナジーさいせい」）。

    - 選べるのはトラッシュの特殊エネルギーカード（``effects.discard_special_energy``。トラッシュにある間の定義。色・出すエネルギーで選ばない）。1 枚ちょうど（決定 ``RECOVER_ENERGY``）。
      なければ処理の対象がないので何もしない（p.309。v0.31 の ``RecoverTrainer`` と同じ H5 の読み方）
    - 場のポケモンタワーで、この要素（トラッシュから手札に加える）の効果が消える（v0.74 の ``suppressed_discard_to_hand``。トレーナーの使用の問い PT1 は持ち込まない）"""

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = RECOVER_ENERGY

    def run(self, run: AttackRun) -> bool:
        if suppressed_discard_to_hand(run):
            return False
        if protected_discard(run, "recover_energy"):
            return False  # v0.119: ［アレルギーほうし］
        candidates = E.discard_special_energy(run.state, run.player)
        if not candidates:
            return False
        run.suspend(kind=RECOVER_ENERGY, player=run.player, options=candidates)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if len(choices) != 1 or choices[0] not in E.discard_special_energy(run.state, run.player):
            raise RuntimeError(f"手札に加えるカード {choices} が、ワザを使ったプレイヤーのトラッシュの特殊エネルギーカードではない（エンジンの不具合）")
        return_discard_to_hand(run.state, run.player, tuple(choices))
        attacker = run.attacker()
        run.state.add_event("recover_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), cards=tuple(choices))

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, (1,))


@dataclass(frozen=True)
class ReturnAttachedCardsToHand(Element):
    """相手が「きぜつ」しなかったなら、コインを投げる。「おもて」なら、このワザを受けた相手についているすべてのエネルギーカードとトレーナーカードを、持ち主の手札にもどす（v0.116。ピジョンの
    「ツイスター」の、目安のダメージのあと。``effects.DamageThenCoinReturnAttachedCardsToHand``。docs 5 章）。

    - 相手の対戦ポケモンがこのワザで HP 以上（きぜつする）なら、コインを投げない（p.309。こんじょうは G37・残りHP 10 の効果は KS1。``knocked_out``）。もどすカードがない（``effects.
      returned_attached_cards``。タケシの保護のエネルギーカードは除く）ならコインを投げない（実装上の読み方。v0.31 のスーパーデストロイと同じ）
    - コインはこの要素のコイン（効果だけを決める）。前に「とうめい」で受けないと決まった・効果の要素を受けない状態なら T19b・HC3（``effect_coin_questions``）。「おもて」なら ``reaches``
      （``ATTACHED_RETURN_ELEMENT``）→ ``zones.return_attached_cards_to_hand``（カードごとの持ち主の手札。トラッシュを通さない。ログ ``attached_cards_to_hand``）"""

    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.ATTACHED_RETURN_ELEMENT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        opponent = 1 - run.player
        target = run.opponent_active()
        if target is None:
            return False
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        energy, trainers = E.returned_attached_cards(state, opponent, target, run.player)
        if not energy and not trainers:
            return False
        effect_coin_questions(run, opponent, target)
        if run.flip(1).results[0] is not HEADS:
            return False
        if not reaches(run.res, run.fs, opponent, target, E.ATTACHED_RETURN_ELEMENT):
            return False
        energy, trainers = E.returned_attached_cards(state, opponent, target, run.player)
        return_attached_cards_to_hand(state, opponent, target, energy, trainers, effect=str(run.key), by_player=run.player)
        return False


@dataclass(frozen=True)
class MoveAllSelfCountersToOpponent(Element):
    """自分（ワザを実際に使ったポケモン）にのっているすべてのダメージカウンターを、相手（相手の対戦ポケモン）にのせかえる（v0.116。フーディンの「トランスダメージ」の後半。
    ``effects.DiscardAllEnergyThenMoveAllSelfCountersToOpponent``。docs 6 章）。

    - のせかえる数は、この要素を処理する時点で自分にのっているダメージカウンターの数（控えから集めない。v0.41 の ``ShiftCountersToOpponent`` の 1 つずつとは別）。0 個なら何もしない
    - ダメージカウンターの移動はダメージではない（GR-2000-P320-COUNTER-MOVE。弱点・抵抗力・プラスパワー・ディフェンダー・ダメージの軽減を計算せず、「ダメージを受けない」状態でものせる。
      「ダメージを受けたとき」の効果ははたらかない）。のせたカウンターで HP 以上なら、ワザのあとのきぜつの判定（こんじょうは使えない。``_counters_changed``）
    - 相手がのせる効果を受けない（「ワザをうけない」状態）なら、自分の側をとりのぞく前に CX1。とりのぞく前に自分の「とうめい」を評価する（v0.41 と同じ。受けなければ何もしない）。相手の
      「とうめい」はのせるときに評価し、受けなければ CX1（先読みが宣言の前に見つける）"""

    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.COUNTERS_ELEMENT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        per = state.rules.damage_per_counter
        opponent = 1 - run.player
        target = run.opponent_active()
        attacker = run.attacker()
        if run.knocked_out(target):
            raise RuntimeError(f"ワザ {run.key} の相手の対戦ポケモンが、ダメージカウンターをのせる前に HP 以上（このワザにダメージの要素はない。エンジンの不具合）")
        counters = attacker.damage // per
        if not counters or run.knocked_out(attacker):
            return False
        _counter_transfer_protected(run, target, "のせかえる")
        if not reaches(run.res, run.fs, run.player, attacker, E.HEAL_ELEMENT):
            return False
        before_self = attacker.damage
        attacker.damage = before_self - counters * per
        state.add_event("attack_heal", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                        counters=counters, amount=counters * per, damage_before=before_self, total_damage=attacker.damage)
        if not reaches(run.res, run.fs, opponent, target, E.COUNTERS_ELEMENT):
            raise run.res.question("counter_transfer_protected", f"ポケモン {target.pokemon_id}（「とうめい」。のせかえる）")
        before = target.damage
        target.damage = before + counters * per
        state.add_event("place_damage_counters", player=opponent, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key),
                        counters=counters, amount=counters * per, damage_before=before, total_damage=target.damage, attacker=run.player,
                        attacker_pokemon_id=run.fs.frame.source_pid)
        _counters_changed(run, target, before)
        return False


BUILDERS |= {
    # クロスアタック: ワザ全体のコイン coins 枚 →「おもて」の数 × per → 同じ「おもて」の数が at_least 以上ならこんらん（ダメージと状態で別のコインを投げない）
    E.CoinsTimesDamageThenConfuseIfAtLeast: lambda e: (
        Coin("coin", count=e.coins), Damage(OPP, HeadsOfCoin("coin", e.per)), Status(CONFUSION, gate=("coin", AtLeast(e.at_least))),
    ),
    # しこみどく・エナジーショック: ダメージ（目安）→ 次の相手の番にエネルギーカードがついたら condition（今すぐ特殊状態にしない）
    E.DamageThenStatusOnEnergyAttach: lambda e: (Damage(OPP, Printed()), OpponentAttachStatusTrigger(e.condition)),
    # やみのしょくしゅ: ダメージ（目安）→ 次の相手の番、手札・トレーナーで進化させられない（ワザ・特殊能力の進化は止めない）
    E.DamageThenEvolutionLock: lambda e: (Damage(OPP, Printed()), OpponentEvolutionLock()),
    # とりかこむ: ダメージ（目安）→ コイン 1 枚 →「おもて」ならねむり、「うら」なら次の相手の番の「にげる」の禁止（どちらか一方）
    E.DamageThenSleepOnHeadsElseRetreatLock: lambda e: (
        Damage(OPP, Printed()), Coin("coin"), Status(SLEEP, gate=("coin", HEADS)), OpponentRetreatLock(gate=("coin", TAILS)),
    ),
    # バトンタッチ: ダメージ（目安）→ 自分の控えの energy_type ポケモンを選ぶ → 自分のエネルギーカードをすべて付け替えてから入れ替える
    E.DamageThenMoveAllEnergyToTypeBenchThenSwitch: lambda e: (Damage(OPP, Printed()), BatonPass(e.energy_type)),
    # はらだいこ: 自分にダメージカウンター counters 個 → 山札の基本エネルギーカード cards 枚を自分につけ、山札を切る
    E.SelfCountersThenAttachBasicEnergyFromDeck: lambda e: (SelfCounters(e.counters), AttachBasicEnergyFromDeckToSelf(e.cards)),
    # エナジーサイクル: 相手に控えがいなければ失敗 → コイン →「おもて」なら相手の対戦ポケモンのエネルギーカード（特殊もふくむ）1 枚を相手の控えにつけ替える
    E.CoinMoveOpponentEnergyCardToBenchOrFail: lambda e: (
        FailWithoutOpponentBench(), Coin("coin"), MoveOpponentEnergyToBench(any_card=True, gate=("coin", HEADS)),
    ),
    # エナジーコントロール: コイン（「うら」なら失敗）→ 相手の場の基本エネルギーカード 1 枚をはがし、相手の場のポケモン 1 匹につける
    E.FailOnTailsMoveOpponentFieldEnergy: lambda e: (FailOnTails(), MoveOpponentFieldEnergy()),
    # げんしのしずく: コイン →「おもて」なら相手の場の進化ポケモンを選び、いちばん上の進化カードを相手の山札にもどして退化させ、山札を切る
    E.CoinDevolveOpponentEvolvedToDeck: lambda e: (Coin("coin"), DevolveOpponentToDeck(gate=("coin", HEADS))),
    # よびもどす: 相手のベンチに空きがなければ失敗 → 相手のトラッシュのたね・ベイビィを選び、カウンター counters 個をのせた状態で相手のベンチに出す
    E.BenchBabyOrBasicFromOpponentDiscardOrFail: lambda e: (BenchFromOpponentDiscard(e.counters),),
    # さいせい: ダメージカウンターをすべてとりのぞく → 進化カードとエネルギーカードをすべてトラッシュしてたねポケモンにもどる
    E.HealAllThenRegressToBasic: lambda e: (HealAllCounters(), RegressToBasic()),
    # エナジーさいせい: トラッシュの特殊エネルギーカード 1 枚を手札に加える
    E.RecoverSpecialEnergyFromDiscard: lambda e: (RecoverSpecialEnergy(),),
    # ツイスター: ダメージ（目安）→ 相手がきぜつしなければコイン →「おもて」なら相手についているエネルギーカードとトレーナーカードを持ち主の手札にもどす
    E.DamageThenCoinReturnAttachedCardsToHand: lambda e: (Damage(OPP, Printed()), ReturnAttachedCardsToHand()),
    # トランスダメージ: 自分のエネルギーカードをすべてトラッシュ（使うための条件か効果かは HC1）→ 自分のダメージカウンターをすべて相手にのせかえる
    E.DiscardAllEnergyThenMoveAllSelfCountersToOpponent: lambda e: (
        DiscardOwnEnergy(None, count=None, when_lacking=LACKING_CANNOT_USE, timing=TIMING_UNRESOLVED), MoveAllSelfCountersToOpponent(),
    ),
}


# ---------------------------------------------------------------- v0.117（docs/retreat-return-active-powers-v0.117.md）


@dataclass(frozen=True)
class OpponentCountersByHeads(Element):
    """コインを ``coins`` 枚投げ、「おもて」の数ぶんのダメージカウンターを、相手の対戦ポケモンにのせる（v0.117。セレビィの「サイキックダメージ」。``effects.CoinsCountersOnOpponent``）。

    - 相手がこのワザの中で HP 以上なら処理の対象がない（コインを投げない。p.309）。コインは効果だけを決めるので、「とうめい」で受けないと決まった相手・「ワザをうけない」相手には T19b・HC3
      （``effect_coin_questions``）。コインはワザの説明のコイン（``AttackRun.flip``。ナツメのESPのやり直しを含む。「おもて」の数でまとめる）
    - 「おもて」が 1 枚以上なら、のせる前に効果の要素（``COUNTERS_ELEMENT``）を受けるかを ``reaches`` で決め（うらのカードはおもてにする）、v0.41 の ``place_damage_counters`` のログで
      のせる（``_counters_changed``。ダメージではないので、こんじょうは使えない）。0 枚なら何もしない"""

    coins: int = 3
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.COUNTERS_ELEMENT

    def has_target(self, run: AttackRun) -> bool:
        return not run.knocked_out(run.opponent_active())

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        effect_coin_questions(run, opponent, target)
        heads = run.flip(self.coins, by_heads=True).heads
        if not heads:
            return False
        if not reaches(run.res, run.fs, opponent, target, E.COUNTERS_ELEMENT):
            return False
        state = run.state
        per = state.rules.damage_per_counter
        before = target.damage
        target.damage = before + heads * per
        state.add_event("place_damage_counters", player=opponent, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key),
                        counters=heads, amount=heads * per, damage_before=before, total_damage=target.damage, attacker=run.player,
                        attacker_pokemon_id=run.fs.frame.source_pid)
        _counters_changed(run, target, before)
        return False


def _returned_attacker_card(run: AttackRun) -> int:
    """v0.117: このワザの効果で場をはなれた（山札にもどった）ワザを使ったポケモンの、はなれる前のいちばん上のカード（このワザのログ ``return_in_play_to_deck`` の ``pokemon``）。"""
    pid = run.fs.frame.source_pid
    for event in reversed(run.state.log):
        if event["kind"] == "return_in_play_to_deck" and event.get("pokemon_id") == pid and event.get("effect") == str(run.key):
            return event["pokemon"]
    raise RuntimeError(f"ワザ {run.key} を使ったポケモン {pid} が場にいないのに、このワザで山札にもどしたログがない（エンジンの不具合）")


@dataclass(frozen=True)
class CoinDiscardCardToDeckThenShuffle(Element):
    """コインを投げて「おもて」なら、自分のトラッシュからカードを 1 枚選び出し、山札にもどす。その後、その山札をよく切る（v0.117。エイパムの「もちさる」の後半。前の要素
    ``ReturnSelfToDeck`` が自分を山札にもどしたあと。``effects.ReturnSelfToDeckThenCoinDiscardCardToDeck``）。

    - ワザを使ったポケモンがもう場にいなくても、コイン・選ぶ・切ることは続ける。場にいない（山札にもどった）ときのコインのログの ``card``・``pokemon_id`` は、もどしたポケモン（このワザの
      ``return_in_play_to_deck`` のいちばん上のカード）。「バトル場をはなれられない」で場に残ったときは今までどおり ``AttackRun.flip``（ナツメのESPのやり直しを含む）
    - 宣言のとき、ワザを使うポケモンにナツメのESPがつき、山札にもどる（はなれられない効果を受けていない）なら ES4（ESPといっしょに場をはなれたあとのコイン。docs 7 章）
    - 「おもて」でトラッシュにカードがあれば、決定 ``DISCARD_TO_DECK``（ちょうど 1 枚。選べるものはトラッシュの並び。公開）。答えのカードを山札（一番下。このあと切る）に置き（ログ
      ``attack_discard_to_deck``）、山札を切る。「うら」・トラッシュにカードがないときも、山札を 1 回切る"""

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = DISCARD_TO_DECK

    def on_declare(self, res: Resolution, player: int, attacker: PokemonInPlay) -> None:
        cards = E.esp_cards(res.state, attacker)
        if cards and leave_lock(res.state, player, attacker) is None:
            raise UnsupportedError(E.ESP_LEFT_BEFORE_COIN_CODE, f"ポケモン {attacker.pokemon_id}・ナツメのESP {list(cards)}: {E.ESP_LEFT_BEFORE_COIN_REASON}")

    def _source(self, run: AttackRun) -> tuple[int, int]:
        found = run.state.find_pokemon(run.fs.frame.source_pid)
        if found is not None:
            return found[1].card, found[1].pokemon_id
        return _returned_attacker_card(run), run.fs.frame.source_pid

    def run(self, run: AttackRun) -> bool:
        state = run.state
        if state.find_pokemon(run.fs.frame.source_pid) is not None:
            side = run.flip(1).results[0]
        else:
            card, pid = self._source(run)
            side = flip_coins(state, run.player, 1, source="attack", effect=str(run.key), card=card, pokemon_id=pid).results[0]
        discard = tuple(state.players[run.player].discard)
        if side is HEADS and discard and protected_discard(run, "discard_to_deck"):
            discard = ()  # v0.119: ［アレルギーほうし］（トラッシュにカードがないときと同じに、コインは投げていて、山札は切る。どちらの読み方でも投げるので AP1 に当たらない）
        if side is not HEADS or not discard:
            shuffle_in_attack(run, self, run.player)
            return False
        run.suspend(kind=DISCARD_TO_DECK, player=run.player, options=discard, min_choices=1, max_choices=1)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        p = state.players[run.player]
        if len(choices) != 1 or choices[0] not in p.discard or choices[0] not in decision.options:
            raise RuntimeError(f"「もちさる」で選んだカード {choices} が、自分のトラッシュのカードではない（エンジンの不具合）")
        card, pid = self._source(run)
        p.discard.remove(choices[0])
        p.deck.append(choices[0])
        state.add_event("attack_discard_to_deck", player=run.player, pokemon=card, pokemon_id=pid, effect=str(run.key), cards=(choices[0],))
        shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, range(1, 2))


@dataclass(frozen=True)
class OpponentPursuitOnRetreat(Element):
    """相手の対戦ポケモン（このワザを受けた相手）に、次の相手の番に「にげる」とき ``amount`` ダメージを受ける持続する効果（``PursuitOnRetreat``）を与える（v0.117。「おいうち」。docs 3 章）。
    v0.116 の ``OpponentAttachStatusTrigger`` と同じ形（ダメージの要素のあと・``reaches`` の効果の要素・このワザで HP 以上なら与えない・発生源は実際に使ったポケモンのいちばん上のカード）。"""

    amount: int = 10
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.RETREAT_PURSUIT_ELEMENT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        return UNSUPPORTED, "番をまたぐ効果を、効果を与えたポケモンのカードのワザで記録するので、相手のワザとして使った効果を表せない"

    def has_target(self, run: AttackRun) -> bool:
        return not run.knocked_out(run.opponent_active())

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if not reaches(run.res, run.fs, opponent, target, E.RETREAT_PURSUIT_ELEMENT):
            return False
        attacker = run.attacker()
        turn = run.state.turn_number
        effect = PursuitOnRetreat(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn + PursuitOnRetreat.turns_until_active,
                                  amount=self.amount, attack=str(run.key))
        add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key), amount=self.amount)
        return False


BUILDERS |= {
    # いかく: 相手が「たねポケモン」なら（NB1）、相手のワザを 1 つ選び、次の相手の番に使えなくする
    E.LockOpponentAttackIfBasic: lambda e: (OpponentAttackLock(basic_only=True),),
    # サイキックダメージ: コイン coins 枚の「おもて」の数ぶんのダメージカウンターを相手にのせる（ダメージではない）
    E.CoinsCountersOnOpponent: lambda e: (OpponentCountersByHeads(e.coins),),
    # ぱっときえる: ダメージ（目安）→ 自分と自分についているエネルギーカードを持ち主の手札にもどす（ほかのカードがついていれば VH1）
    E.DamageThenReturnSelfAndEnergyToHand: lambda e: (Damage(OPP, Printed()), ReturnAttackerToHand(local_coin=None, energy_only=True)),
    # もちさる: 自分と自分についているカードを山札にもどす（切らない）→ コイン →「おもて」ならトラッシュのカード 1 枚を山札に → 山札を切る
    E.ReturnSelfToDeckThenCoinDiscardCardToDeck: lambda e: (ReturnSelfToDeck(local_coin=None, after_damage=None, shuffle=False), CoinDiscardCardToDeckThenShuffle()),
    # メガフレイム: コイン coins 枚 →「うら」の数ぶんの energy_type エネルギーカードをトラッシュ（足りなければダメージはなくなる）→ ダメージ（目安）
    E.CoinsDiscardTailsEnergyThenDamage: lambda e: (
        Coin("coin", count=e.coins), DiscardOwnEnergy(e.energy_type, tails_of="coin", when_lacking=LACKING_NONE, copy_need=e.coins),
        Damage(OPP, Printed(), requires="discard"),
    ),
    # おいうち: ダメージ（目安）→ 次の相手の番に「にげる」とき amount ダメージの持続する効果
    E.DamageThenPursuitOnRetreat: lambda e: (Damage(OPP, Printed()), OpponentPursuitOnRetreat(e.amount)),
}


# ---------------------------------------------------------------- v0.118（docs/unbounded-coins-heal-allocation-v0.118.md）


@dataclass(frozen=True)
class ExtraUnits:
    """ダメージの目安の数字 +「ワザに必要な「エネルギー」よりも多く「エネルギー」がついているとき、多い「エネルギー」1 個につき ``per``（``max_extra`` 個ぶんまで）」（v0.118。わるいオクタンの
    「スミでっぽう」。``effects.ExtraEnergyUnitsDamage``）。数えるのはワザを実際に使ったポケモンについている「エネルギー」の個数（色を問わない。``all_energy_units``）で、多い数はワザに必要な
    エネルギーの記号の数を引いた数（0 より小さくしない）。色の読み方の問いは数える個数を変えないので当てはめず、［おいしげる］で個数が決まらないときだけ止める。"""

    per: int
    max_extra: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        units = all_energy_units(run.state, run.attacker(), run)
        return run.attack.damage + min(max(0, units - len(run.attack.cost)), self.max_extra) * self.per


@dataclass(frozen=True)
class HeadsTimesOpponentFieldEnergy:
    """相手の場のポケモン全員についている「エネルギー」の数だけコインを投げ、「おもて」の数 × ``per``（v0.118。わるいナッシーの「わるわるMAX」。``effects.CoinsPerOpponentFieldEnergyDamage``）。
    数えるのは、このダメージの要素を処理する時点の相手の場（バトル場・ベンチ）のポケモンすべてについている「エネルギー」の個数（``all_energy_units``。［おいしげる］で個数が決まらなければ止める）。
    コインはダメージの要素の中（ダメージの量だけを決める）。0 個なら投げず 0。"""

    per: int
    by_heads: ClassVar[bool] = True  # 「おもて」の数だけを使う（先読みは「おもて」の数でまとめる。v0.35）

    def coin_count(self, run: AttackRun) -> int:
        return sum(all_energy_units(run.state, pokemon, run) for pokemon in run.state.players[1 - run.player].in_play())

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return (0 if flips is None else flips.heads) * self.per


@dataclass(frozen=True)
class OpponentRetreatCostIncrease(Element):
    """相手の対戦ポケモン（このワザを受けた相手）に、次の相手の番に「にげる」ときに必要な「エネルギー」が ``amount`` 個ぶん多くなる持続する効果（``RetreatCostIncrease``）を与える（v0.118。
    わるいオクタンの「しめつづける」の「うら」）。相手に与える効果なので「ワザをうけない」状態・「とうめい」を評価する（効果の要素 ``RETREAT_COST_ELEMENT``）。このワザで HP 以上なら
    処理の対象がない（p.309）。``gate`` はワザ全体のコインの面。"""

    amount: int = 1
    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.RETREAT_COST_ELEMENT

    def coin_receiver(self) -> str | None:
        return "effect"  # ワザ全体のコインが決める相手の対戦ポケモンへの効果（``void_coin_question``）

    def has_target(self, run: AttackRun) -> bool:
        return not run.knocked_out(run.opponent_active())

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if not reaches(run.res, run.fs, opponent, target, E.RETREAT_COST_ELEMENT):
            return False
        from ..state import RetreatCostIncrease

        attacker = run.attacker()
        turn = run.state.turn_number
        effect = RetreatCostIncrease(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn + RetreatCostIncrease.turns_until_active,
                                     amount=self.amount, attack=str(run.key))
        add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key), amount=self.amount)
        return False


def draw_classes(deck_size: int):
    """v0.118: 「うら」が出るまで投げるコインの「おもて」の数 h のうち、引く枚数 ``min(h, deck_size)`` だけを使う要素（まるもうけ）の組（``unbounded.HeadClasses``）。h = 0〜``deck_size`` は
    それぞれ別の組、``deck_size`` 以上はどれも山札をすべて引くので 1 つの組（代表は ``deck_size``）。"""
    from .unbounded import HeadClasses

    representatives = tuple(range(deck_size + 1))
    return HeadClasses(representatives, representatives, deck_size, 1, lambda heads: min(heads, deck_size))


@dataclass(frozen=True)
class DrawUntilTails(Element):
    """「うら」が出るまでコインを投げつづけ、その間に出た「おもて」の数だけ、カードを引く（v0.118。ニャースの「まるもうけ」。``effects.CoinsUntilTailsDraw``）。

    - コインはワザの説明のコイン（``AttackRun.flip_until_tails``。実際の対戦では上限なく 1 枚ずつ。ナツメのESPのやり直しは一まとまりのあとに 1 回だけ。A0）。山札が 0 枚でも投げる（v0.112 の
      しょくしゅをつかうと同じ。引く効果を処理の対象がないことにしない）
    - 引くのは ``min(「おもて」の数, 山札の枚数)``（``zones.draw_cards``。引けるだけ。効果で山札がなくなっても負けにしない）。ログ ``draw``（引いたカードは持ち主だけ）
    - 先読みは ``draw_classes``（山札の枚数 + 1 の組の代表）。「おもて」の数は引く枚数にだけ使う"""

    phase: ClassVar[Phase] = Phase.EFFECT
    reads_deck_order: ClassVar[bool] = True

    def run(self, run: AttackRun) -> bool:
        deck = run.state.players[run.player].deck
        size = len(deck)
        flips = run.flip_until_tails(lambda: draw_classes(size))
        draw_cards(run.state, run.player, min(flips.heads, len(deck)))
        return False


@dataclass(frozen=True)
class CoinEachPlayer(Element):
    """お互いのプレイヤーが、それぞれコインを 1 枚投げる（v0.118。フシギソウの「ふしぎなかおり」の「お互いのプレイヤーは、それぞれコインを投げる」）。投げるのはワザを使ったプレイヤー → 相手
    プレイヤーの順（実装上の順番。説明の 1 つのコイントスを 2 人で投げる。``AttackRun.flip_each``）。結果は ``names``（(ワザを使ったプレイヤーのコイン, 相手プレイヤーのコイン)）のワザ全体の
    コイン（1 枚ずつ）。

    - そのプレイヤーのコインが決める要素（``gate`` の名前）のどれにも処理の対象がなければ、そのプレイヤーは投げない（p.309。v0.38 の ``Coin`` と同じ読み方。投げなかったコインの面はどちらでもない）
    - 決める要素の処理の対象がどれも効果を受けない状態（「ワザをうけない」状態など）なら、投げるかが決められない（v0.34 の HC3 と同じ問い）"""

    names: tuple[str, str] = ("coin", "coin_opponent")
    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        flippers: list[tuple[int, str]] = []
        for player, name in zip((run.player, 1 - run.player), self.names):
            run.fs.coins[name] = CoinFlips(())
            decided = [element for element in run.program if element.coin_dependent(name)]
            targeted = [element for element in decided if element.has_target(run)]
            if decided and not targeted:
                continue
            if targeted and all(getattr(element, "void_for_all", lambda run: False)(run) for element in targeted):
                raise run.res.question("prevented_effect_coin", f"プレイヤー {player} のコインが決める要素 {[type(e).__name__ for e in targeted]} の対象が、どれも効果を受けない")
            flippers.append((player, name))
        if not flippers:
            return False
        flips = run.flip_each(tuple(player for player, _ in flippers))
        for (_, name), side in zip(flippers, flips.results):
            run.fs.coins[name] = CoinFlips((side,))
        return False


HEAL_SIDE_OWN, HEAL_SIDE_OPPONENT = "own", "opponent"


@dataclass(frozen=True)
class AllocateHeal(Element):
    """とりのぞくダメージカウンターの数を、とりのぞく先に配分して、とりのぞく（v0.118。ふしぎなかおり・ごくらくかふん。docs 7 章）。

    - とりのぞく先: ``chosen`` がなければ ``side`` の場（バトル場 → ベンチ）のポケモン、``chosen`` があれば先に選んだ自分の控えポケモン（``ChooseEffectTarget``。いなければなし）とワザを使った
      ポケモン（説明の順）。そのうちカウンターののっているものだけ（このワザで HP 以上のポケモンは飛ばす）。どれにもなければ決定を出さない（処理の対象がない。p.309）
    - 上限: ``total``（合計の上限。ふしぎなかおりの「最大3つ」）か ``each``（先ごとの上限。ごくらくかふんの「最大2つと、…最大2つを、それぞれ」）のちょうど一方。1 匹からはのっている数まで
    - 決定 ``HEAL_ALLOCATION``（決めるのは先の持ち主。表は ``effects.heal_allocations``。続きの情報の ``heal``・``table``・``heal_side``・``element``）。とりのぞけるのに 0 個を選ぶ組は選べるが
      選ぶと止める（HZ1。``effects.heal_zero_rows``）
    - 宣言の前の先読みは、表のはじめの組（0 でない）だけを試す。ほかの組の続き（コイン・決定・きぜつの判定まで）は、実際に決定を出すときに試し、問いに当たる組を選ぶと止める（v0.94 の
      ``_mark_branch_questions``。2 人の配分の直積を先読みの上限にのせず、1 つずつ順に扱う）
    - とりのぞく前に、先ごとに「ワザをうけない」状態・「とうめい」を評価する（``reaches`` の ``heal``。受けなければ、その先からはとりのぞかない。ほかの先は続ける）。ログ ``attack_heal``"""

    side: str = HEAL_SIDE_OWN
    total: int | None = None
    each: int | None = None
    chosen: str | None = None
    gate: tuple | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = HEAL_ALLOCATION

    def __post_init__(self) -> None:
        if (self.total is None) == (self.each is None):
            raise ValueError("とりのぞく数の上限は total・each のちょうど一方")
        if self.side not in (HEAL_SIDE_OWN, HEAL_SIDE_OPPONENT) or (self.chosen is not None and (self.side != HEAL_SIDE_OWN or self.each is None)):
            raise ValueError(f"とりのぞく先の指定 {(self.side, self.chosen, self.total, self.each)!r} が正しくない")

    @property
    def opponent_element(self) -> str | None:
        return E.HEAL_ELEMENT if self.side == HEAL_SIDE_OPPONENT else None

    def owner(self, run: AttackRun) -> int:
        return run.player if self.side == HEAL_SIDE_OWN else 1 - run.player

    def targets(self, run: AttackRun) -> list[tuple[PokemonInPlay, int]]:
        """とりのぞく先と、その上限（カウンターののっているものだけ）。"""
        if self.chosen is not None:
            pokemon = [*chosen_pokemon(run, self.chosen, run.player), run.attacker()]
        else:
            pokemon = list(run.state.players[self.owner(run)].in_play())
        per = run.state.rules.damage_per_counter
        limit = self.total if self.total is not None else self.each
        found = []
        for target in pokemon:
            cap = 0 if run.knocked_out(target) else min(limit, target.damage // per)
            if cap > 0:
                found.append((target, cap))
        return found

    def has_target(self, run: AttackRun) -> bool:
        if self.chosen is not None:
            # 選ぶ前（ワザ全体のコインの前）: 自分の控えを選べるか、自分にカウンターがある
            attacker = run.attacker()
            return bool(run.state.players[run.player].bench) or (not run.knocked_out(attacker) and attacker.damage >= run.state.rules.damage_per_counter)
        return bool(self.targets(run))

    def void_for_all(self, run: AttackRun) -> bool:
        if self.chosen is not None:
            return False
        from .kernel import first_void

        owner = self.owner(run)
        targets = self.targets(run)
        return bool(targets) and all(first_void(run.res, run.incoming(), owner, target, Window.BEFORE_EFFECT) is not None for target, _ in targets)

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        targets = self.targets(run)
        if not targets:
            return False
        caps = tuple(cap for _, cap in targets)
        table = E.heal_allocations(caps, self.total)
        zeros = E.heal_zero_rows(table, caps, self.total)
        index = next((i for i, element in enumerate(run.program) if element is self), None)
        if index is None:
            raise RuntimeError("とりのぞく数の配分の要素が、処理している要素の並びにない（エンジンの不具合）")
        heal = (tuple(target.pokemon_id for target, _ in targets), caps, self.total, self.each)
        extra = (("element", index), ("heal", heal), ("table", table), ("heal_side", self.side)) + _unresolved_extra(zeros, E.HEAL_UP_TO_ZERO_CODE, E.HEAL_UP_TO_ZERO_REASON)
        run.suspend(kind=HEAL_ALLOCATION, player=self.owner(run), options=tuple(range(len(table))), carry=True, extra=extra)
        if not run.res.dry_run:
            first = next(i for i in range(len(table)) if i not in zeros)
            others = tuple(i for i in range(len(table)) if i not in zeros and i != first)
            if others:
                _mark_branch_questions(run, others)
        return True

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ()))
        return [(next(option for option in decision.options if option not in blocked),)]  # はじめの組だけ（ほかは決定を出すときに試す）

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        pids, caps, _, _ = decision.context_value("heal")
        row = tuple(decision.context_value("table"))[choices[0]]
        owner = decision.player
        per = state.rules.damage_per_counter
        for pid, cap, amount in zip(pids, caps, row):
            if amount <= 0:
                continue
            if amount > cap:
                raise RuntimeError(f"とりのぞく数 {amount} が上限 {cap} より多い（表の誤り。エンジンの不具合）")
            target = state.players[owner].find_by_pokemon_id(pid)
            if target is None or run.knocked_out(target):
                continue
            removed = min(amount, target.damage // per)
            if removed <= 0 or not reaches(run.res, run.fs, owner, target, E.HEAL_ELEMENT):
                continue
            before = target.damage
            target.damage = before - removed * per
            extra = {} if owner == run.player else {"attacker": run.player}
            state.add_event("attack_heal", player=owner, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key), counters=removed,
                            amount=removed * per, damage_before=before, total_damage=target.damage, **extra)


@dataclass(frozen=True)
class ChosenOption:
    """v0.118: 「のぞむなら」の決定で選んだ答え（``OptionalCoin``。投げると選んだなら真）。``fs.results`` に置き、決定をまたぐときは続きの情報の ``chosen_options`` で運ぶ（``AttackRun.suspend``）。
    ナツメのESPのやり直しのあとの要素も、運んだ答えを読む（選び直さない）。"""

    chosen: bool


@dataclass(frozen=True)
class OptionalCoin(Element):
    """のぞむなら、コインを投げてよい（v0.118。ルギアの「エアロウイング」）。決定 ``OPTIONAL_COIN``（選べるものは (1,)。0 個: 投げない・1 個: 投げる）。答えは ``ChosenOption``（あとの要素が読む）。

    - 宣言の前の先読みは投げない答えだけを試す。投げる答えの続き（コイン・ナツメのESP・ダメージ・きぜつの判定まで）は、実際に決定を出すときに試し、問いに当たれば投げるを選ぶと止める
      （v0.94 の ``_mark_branch_questions``。投げたときだけ止まる盤面で、投げない答えまで宣言の前に拒否しない）
    - ログ ``optional_coin_chosen``・``optional_coin_declined``（公開）"""

    name: str = "choice"
    phase: ClassVar[Phase] = Phase.NEUTRAL
    decision_kind: ClassVar[str] = OPTIONAL_COIN

    def run(self, run: AttackRun) -> bool:
        run.suspend(kind=OPTIONAL_COIN, player=run.player, options=(1,), min_choices=0, max_choices=1, carry=True)
        if not run.res.dry_run:
            _mark_branch_questions(run, (1,))
        return True

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return [()]  # 投げない答えだけ（投げる答えは決定を出すときに試す）

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        attacker = run.attacker()
        chosen = bool(choices)
        run.fs.results[self.name] = ChosenOption(chosen)
        run.state.add_event("optional_coin_chosen" if chosen else "optional_coin_declined", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                            effect=str(run.key))


@dataclass(frozen=True)
class ChosenCoinFailOnTails(Element):
    """「のぞむなら」の決定（``choice``）で投げると選んだときだけ、コインを 1 枚投げ、「うら」ならワザは失敗する（v0.118。エアロウイング。p.323「12 ワザの失敗」）。結果はワザ全体のコイン ``name``
    （投げなかったなら面はどちらでもない）。コインの前に、残りの要素が相手の状態で無効かを ``void_coin_question`` で確かめる（v0.34 の ``FailOnTails`` と同じ）。コインはワザの説明のコイン
    （ナツメのESPのやり直しを含む ``AttackRun.flip``。やり直しのあとは、運んだ答えを読む）。"""

    choice: str = "choice"
    name: str = "coin"
    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        picked = run.fs.results.get(self.choice)
        if picked is None:
            raise RuntimeError(f"「のぞむなら」の答え {self.choice!r} がない（要素の並びの誤り。エンジンの不具合）")
        if not picked.chosen:
            run.fs.coins[self.name] = CoinFlips(())
            return False
        index = next((i for i, element in enumerate(run.program) if element is self), None)
        if index is None:
            raise RuntimeError("ワザの失敗のコインの要素が、処理している要素の並びにない（エンジンの不具合）")
        void_coin_question(run, [element for element in run.program[index + 1:] if not element.after_failure])
        flips = run.flip(1, by_heads=True)
        run.fs.coins[self.name] = flips
        if flips.results[0] is TAILS:
            run.fail("coin")
        return False


@dataclass(frozen=True)
class SetOnHeads:
    """ワザ全体のコイン ``coin`` が「おもて」なら「``amount``」、そうでなければ（投げなかった）ダメージの目安の数字（v0.118。エアロウイングの「このワザのダメージは「80」になる」。p.321 の
    1 段階の値。目安に追加しない。「うら」はワザの失敗で、この値を使わない）。"""

    coin: str
    amount: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return self.amount if run.coin_is((self.coin, HEADS)) else run.attack.damage


def declared_power_amounts(run: AttackRun, element: Damage) -> None:
    """v0.118（docs/unbounded-coins-heal-allocation-v0.118.md 5 章）: ワザといっしょに使った自分の場のポケモンの［XXXXX］（``Resolution.group_powers``）のコインを、そのワザの相手の対戦ポケモンへの
    ダメージの要素で投げる（「うら」が出るまで。投げるのは使ったプレイヤー。``source="power"``。ワザの説明のコインではないので、ナツメのESPのやり直しの対象ではない）。

    - 受けるポケモンがダメージを受けない状態なら、コインはダメージの量だけを決めるので、投げるかが決められない（v0.4b の問い）
    - 先読みは ``unbounded.bonus_classes``（追加の段階で key を求めた「おもて」の数の組）の代表だけを試す。実際の対戦のコイン・ログ・追加は実際の数
    - 投げたら「おもて」の数を ``Resolution.group_powers`` に置き（決定をまたいでも続きの情報で運び、投げ直さない）、ログ ``group_attack_power_coins``（公開。追加の量と段階）

    v0.122（docs/unown-fossil-retreat-reactions-v0.122.md 3 章）: 2 つ以上の力を宣言の順に処理する（前の力の値を上書きしない）。のっているダメージカウンターの数で決める力（［ANGER］）を
    先に数え（この要素を処理する時点の、力を持つ個体のダメージカウンター。コインはない。ログ ``group_attack_power_counters``）、そのあとコインの力を投げる（コインの力の「おもて」の数の組は、
    数えた追加を含めて求める）。ダメージを受けない状態の相手でも、カウンターを数えることは結果を変えないので止めない"""
    from ..effects import PowerKey
    from .kernel import first_void
    from .unbounded import bonus_classes

    res = run.res
    state = run.state
    attacker = run.attacker()
    entries = list(res.group_powers)
    for index, (holder_id, holder_card, card_id, power_index, value) in enumerate(entries):
        effect = E.declared_power_effect(state, entries[index])
        if value is not None or not effect.counts_holder_counters:
            continue
        found = state.find_pokemon(holder_id)
        if found is None:
            # 宣言のあと、相手の対戦ポケモンへのダメージの要素の前に、力を持つ個体が場をはなれる処理はない（「めざめるパワー」は説明のないワザ。今の写しでは起こらない）
            raise RuntimeError(f"ワザといっしょに使った力を持つポケモン {holder_id} が、ダメージの要素の前に場にいない（エンジンの不具合）")
        counters = found[1].damage // state.rules.damage_per_counter
        entries[index] = (holder_id, holder_card, card_id, power_index, counters)
        res.group_powers = tuple(entries)
        state.add_event("group_attack_power_counters", player=run.player, pokemon=holder_card, pokemon_id=holder_id, power=str(PowerKey(card_id, power_index)),
                        effect=str(run.key), counters=counters, amount=effect.bonus_amount(counters), step=2 if holder_id == attacker.pokemon_id else 6,
                        attacker_pokemon_id=attacker.pokemon_id)
    for index, (holder_id, holder_card, card_id, power_index, heads) in enumerate(entries):
        effect = E.declared_power_effect(state, entries[index])
        if heads is not None or not effect.uses_coins:
            continue
        owner, receiver = 1 - run.player, run.opponent_active()
        void = first_void(res, run.incoming(), owner, receiver)
        if void is not None:
            raise res.question("prevented_coin_damage", f"ポケモン {receiver.pokemon_id}（［XXXXX］のコイン）", E.prevented_coin_damage_error(receiver.pokemon_id, void.implementation.kind))
        definition = state.definitions[card_id]
        step = 2 if holder_id == attacker.pokemon_id else 6
        label = f"［{definition.powers[power_index].name_ja}］"
        found_classes: list = []

        def classes(per=effect.per, step=step, label=label, holder_card=holder_card, found_classes=found_classes):
            if not found_classes:
                found_classes.append(bonus_classes(run, element, per, step, label, holder_card))
            return found_classes[0]

        key = PowerKey(card_id, power_index)
        flips = flip_until_tails(state, run.player, source="power", effect=str(key), card=holder_card, pokemon_id=holder_id, classes=classes)
        entries[index] = (holder_id, holder_card, card_id, power_index, flips.heads)
        res.group_powers = tuple(entries)
        state.add_event("group_attack_power_coins", player=run.player, pokemon=holder_card, pokemon_id=holder_id, power=str(key), effect=str(run.key), heads=flips.heads,
                        amount=flips.heads * effect.per, step=step, attacker_pokemon_id=attacker.pokemon_id)


BUILDERS |= {
    # スミでっぽう: 目安 + 多い「エネルギー」（色を問わない個数）1 個につき per（max_extra 個まで）
    E.ExtraEnergyUnitsDamage: lambda e: (Damage(OPP, ExtraUnits(e.per, e.max_extra)),),
    # しめつづける: ダメージ（目安）→ コイン 1 枚 →「おもて」でマヒ・「うら」で次の相手の番の「にげる」エネルギー +amount
    E.DamageThenParalyzeOnHeadsElseRetreatCost: lambda e: (
        Damage(OPP, Printed()), Coin("coin"), Status(PARALYSIS, gate=("coin", HEADS), reparalysis_check=True), OpponentRetreatCostIncrease(e.amount, gate=("coin", TAILS)),
    ),
    # わるわるMAX: 相手の場のポケモン全員の「エネルギー」の数だけコイン →「おもて」の数 × per
    E.CoinsPerOpponentFieldEnergyDamage: lambda e: (Damage(OPP, HeadsTimesOpponentFieldEnergy(e.per)),),
    # ふしぎなかおり: お互いのコイン（使ったプレイヤー → 相手）→「おもて」のプレイヤーごとに自分の場から合計 counters まで（使ったプレイヤー → 相手の順に配分）
    E.EachPlayerCoinHealOwnField: lambda e: (
        CoinEachPlayer(), AllocateHeal(HEAL_SIDE_OWN, total=e.counters, gate=("coin", HEADS)),
        AllocateHeal(HEAL_SIDE_OPPONENT, total=e.counters, gate=("coin_opponent", HEADS)),
    ),
    # ごくらくかふん: コイン →「おもて」なら自分の控えを 1 匹選ぶ → 選んだ控えと自分から、それぞれ counters まで
    E.CoinHealChosenBenchAndSelf: lambda e: (
        Coin("coin"), ChooseEffectTarget(side=E.TARGET_SIDE_OWN, scope=E.TARGET_BENCH, name="bench", gate=("coin", HEADS)),
        AllocateHeal(HEAL_SIDE_OWN, each=e.counters, chosen="bench", gate=("coin", HEADS)),
    ),
    # まるもうけ: 「うら」が出るまでコイン →「おもて」の数だけ引く（引けるだけ）
    E.CoinsUntilTailsDraw: lambda e: (DrawUntilTails(),),
    # エアロウイング: のぞむならコイン →「うら」で失敗 →「おもて」ならダメージ amount（投げなければ目安）
    E.OptionalCoinSetDamageElseFail: lambda e: (OptionalCoin("choice"), ChosenCoinFailOnTails("choice", "coin"), Damage(OPP, SetOnHeads("coin", e.amount))),
}


# ---------------------------------------------------------------- v0.119（docs/damage-reactions-poison-sleep-v0.119.md）


@dataclass(frozen=True)
class OwnCounterCountOnOpponent(Element):
    """自分（ワザを実際に使ったポケモン）にのっているダメージカウンターと同じ数のダメージカウンターを、相手の対戦ポケモンにのせる（v0.119。ムウマの「いたみわけ」。
    ``effects.PlaceOwnCounterCountOnOpponent``）。

    - 数は、この要素を処理する時点で自分にのっている数（自分からはとりのぞかない）。0 個なら何もしない（ログを残さない。相手の「とうめい」も評価しない）
    - のせる前に効果の要素（``COUNTERS_ELEMENT``）を受けるかを ``reaches`` で決め（「ワザをうけない」状態・エフェクトガード・「とうめい」。うらのカードはおもてにする）、v0.41 の
      ``place_damage_counters`` のログでのせる（``_counters_changed``。ダメージではないので、弱点・抵抗力・鋼エネルギー・はんげき・こんじょうは関係しない）"""

    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.COUNTERS_ELEMENT

    def has_target(self, run: AttackRun) -> bool:
        return not run.knocked_out(run.opponent_active())

    def run(self, run: AttackRun) -> bool:
        state = run.state
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        per = state.rules.damage_per_counter
        counters = run.attacker().damage // per
        if not counters:
            return False
        if not reaches(run.res, run.fs, opponent, target, E.COUNTERS_ELEMENT):
            return False
        before = target.damage
        target.damage = before + counters * per
        state.add_event("place_damage_counters", player=opponent, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key),
                        counters=counters, amount=counters * per, damage_before=before, total_damage=target.damage, attacker=run.player,
                        attacker_pokemon_id=run.fs.frame.source_pid)
        _counters_changed(run, target, before)
        return False


@dataclass(frozen=True)
class FieldWeaknessImmunity(Element):
    """v0.119: 次の相手の番、自分の場の「水」ポケモンは「弱点」の影響を受けない（ヒトデマンの「なぞのこうせん」）。プレイヤーに与える期限のある効果
    （``ATTACK_FIELD_WEAKNESS_IMMUNITY``。``player`` はワザを使ったプレイヤー、``source_card``・``pokemon_id`` は実際にワザを使ったポケモン、``card_id``・``attack_index`` はワザの出どころ、
    消える番は与えた番 + 1）を加える。ログ ``trainer_effect_added``。

    - 自分の場に与える効果なので、相手の防護（「ワザをうけない」・「とうめい」）は関係しない。タイプ（「水」）は登録の実装が持ち、記録に写さない（受けるポケモンはダメージを受ける時の
      今の姿で決める。``effects.field_weakness_immunities``）"""

    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        from ..state import ATTACK_FIELD_WEAKNESS_IMMUNITY

        state = run.state
        turn = state.turn_number
        attacker = run.attacker()
        record = TrainerTurnEffect(kind=ATTACK_FIELD_WEAKNESS_IMMUNITY, player=run.player, source_card=attacker.card, card_id=run.key.card_id, created_turn=turn,
                                   expires_turn=turn + 1, pokemon_id=attacker.pokemon_id, attack_index=run.key.attack_index)
        if any(r.kind == ATTACK_FIELD_WEAKNESS_IMMUNITY and r.player == run.player and r.created_turn == turn for r in state.trainer_effects):
            raise RuntimeError(f"プレイヤー {run.player} の「なぞのこうせん」の効果が、与えた番 {turn} にすでにある（1 番に使えるワザは 1 つ。エンジンの不具合）")
        state.trainer_effects = state.trainer_effects + (record,)
        state.add_event("trainer_effect_added", player=run.player, effect_kind=ATTACK_FIELD_WEAKNESS_IMMUNITY, trainer_card=record.source_card, card_id=record.card_id,
                        expires_turn=record.expires_turn, attack_index=record.attack_index, pokemon_id=record.pokemon_id, effect=str(run.key))
        return False


@dataclass(frozen=True)
class SelfSecretePoison(Element):
    """v0.119: 自分に「次の相手の番、相手のワザのダメージを受けたら、相手をどくにし、相手の控え全員に ``amount``」の持続する効果（コクーンの「どくをだす」。``state.SecretePoison``）を
    与える（v0.12 の ``SelfRetaliation`` と同じ形。自分への効果なので「とうめい」は評価しない。HP 以上なら与えない）。"""

    amount: int = 10
    phase: ClassVar[Phase] = Phase.EFFECT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        return UNSUPPORTED, "番をまたぐ効果を、効果を持つポケモンのカードのワザの位置で記録するので、相手のワザとして使った効果を表せない（v0.12 の返す効果と同じ）"

    def run(self, run: AttackRun) -> bool:
        from ..state import SecretePoison

        attacker = run.attacker()
        effect = SecretePoison(source_card=attacker.card, source_player=run.player, created_turn=run.state.turn_number, active_turn=run.state.turn_number + 1,
                               attack_index=run.key.attack_index, amount=self.amount, attack_card=effect_attack_card_of(run, attacker))
        if run.knocked_out(attacker):
            run.state.add_event("persistent_effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                persistent_effect=effect.kind, effect=str(run.key), reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        add_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key))
        return False


@dataclass(frozen=True)
class ReplacementPoisonOnKnockOut(Element):
    """v0.119（docs/damage-reactions-poison-sleep-v0.119.md 6 章）: 「このワザによって相手が「きぜつ」したなら、そのかわりに出てくる対戦ポケモンを「どく」状態にする」（マタドガスの「ガスばくはつ」）。
    相手の対戦ポケモンがこのワザで HP 以上なら、記録（``state.ReplacementPoison``。``REPLACEMENT_PENDING``）を状態に置く（ログ ``replacement_poison_pending``）。「きぜつ」したかは、このワザの
    あとのきぜつの処理で決める（``flow.settle_replacement_poisons``）。どくを与えるのは、持ち主がかわりのポケモンをバトル場に出したとき（``flow.apply_replacement_poison``）。HP 以上でなければ
    何もしない（ポケモンチェックなどほかの原因で「きぜつ」しても対象ではない）。"""

    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        from ..state import ReplacementPoison

        state = run.state
        opponent = 1 - run.player
        target = run.opponent_active()
        if target is None or run.state.is_face_down(target) or not E.knocked_by_hp(state, target):
            return False
        attacker = run.attacker()
        if any(r.knocked_pokemon_id == target.pokemon_id for r in state.replacement_poisons):
            raise RuntimeError(f"ポケモン {target.pokemon_id} のかわりのポケモンへのどくの記録がすでにある（1 つのワザで 1 回。エンジンの不具合）")
        record = ReplacementPoison(player=opponent, knocked_pokemon_id=target.pokemon_id, card_id=run.key.card_id, attack_index=run.key.attack_index,
                                   attacker_player=run.player, attacker_pokemon_id=attacker.pokemon_id, attacker_card=attacker.card,
                                   attacker_evolved=E.is_evolution_in_play(state, attacker), created_turn=state.turn_number)
        state.replacement_poisons = state.replacement_poisons + (record,)
        state.add_event("replacement_poison_pending", player=opponent, pokemon=target.card, pokemon_id=target.pokemon_id, effect=str(run.key), attacker=run.player,
                        attacker_pokemon_id=attacker.pokemon_id)
        return False


BUILDERS |= {
    # ガスばくはつ: ダメージ（目安）→ 自分にも self_damage → このワザで相手が HP 以上なら、かわりに出てくる対戦ポケモンへのどくの記録
    E.DamageAndSelfDamageThenPoisonReplacement: lambda e: (
        Damage(OPP, Printed()), Damage(SELF, Fixed(e.self_damage), name="self_damage"), ReplacementPoisonOnKnockOut(),
    ),
    # どくをだす: 自分に次の相手の番の「相手のワザのダメージを受けたら、相手をどく・相手の控え全員に amount」の持続する効果
    E.SecretePoisonNextTurn: lambda e: (SelfSecretePoison(e.amount),),
    # いたみわけ: 自分にのっているダメージカウンターと同じ数を相手の対戦ポケモンにのせる（自分からはとりのぞかない）
    E.PlaceOwnCounterCountOnOpponent: lambda e: (OwnCounterCountOnOpponent(),),
    # なぞのこうせん: ダメージ（目安）→ 次の相手の番、自分の場の pokemon_type のポケモンは弱点の影響を受けない
    E.DamageThenOwnTypeWeaknessImmunityNextTurn: lambda e: (Damage(OPP, Printed()), FieldWeaknessImmunity()),
    # ひきずりこむ: のぞむなら入れ替え（ワザを使ったプレイヤーが選ぶ）→ ダメージ（目安。今の相手の対戦ポケモン）→ ねむり（コインなし）
    E.OptionalSwitchOpponentThenDamageAndSleep: lambda e: (ForceSwitch(chooser="attacker", optional=True, carry=True), Damage(OPP, Printed()), Status(SLEEP)),
    # どくどくエキス: コイン →「おもて」なら相手をどく（ダメージカウンターの数を multiplier 倍にする性質のどく）
    E.ToxicPoisonOnHeadsWithoutDamage: lambda e: (Status(POISON, local_coin=HEADS, poison_multiplier=e.multiplier),),
}



# ---------------------------------------------------------------- v0.121（docs/hand-bench-attack-conditions-v0.121.md）: ねむりのときだけのワザ・失敗しなくなる効果・場のポケモン全員のコイン・
# 相手の手札から場へ出すワザ


@dataclass(frozen=True)
class FailUnlessAsleep(Element):
    """ワザを使ったポケモンが「ねむり」状態ではないとき、このワザは失敗する（v0.121。ヤドランの「おおいびき」の最新の説明。``effects.FailUnlessAsleepDamage``。docs 6 章）。

    - 説明を処理する p.309 の手順 6 の最初の要素（こんらんのコインはその前の手順 5。CR-SLOWBRO-SNORE-ONLY-THIS-ATTACK）。ねむり状態なら何もしない（目を覚まさない）。でなければ失敗
      （ログ ``attack_failed`` の ``reason`` ``not_asleep``。ワザは使ったことになり番は終わる。CR-SLOWBRO-SNORE-AWAKE-FAILS）
    - 相手のワザとして使う（写す）ときは、「このカード」がだれかが決まらない（UQ-COPIED-ATTACK。HC9）"""

    phase: ClassVar[Phase] = Phase.NEUTRAL

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        return UNRESOLVED, "「このカードが「ねむり」状態ではないとき、このワザは失敗する」の「このカード」が、写したポケモンか元のカードかが決まらない（UQ-COPIED-ATTACK）"

    def run(self, run: AttackRun) -> bool:
        if not run.attacker().conditions.asleep:
            run.fail("not_asleep")
        return False


@dataclass(frozen=True)
class SelfFailureWaiver(Element):
    """自分に「次の自分の番、このカードが使う「``target_name``」で投げるコインが「うら」でも失敗しない。(このワザを受けた相手がバトル場をはなれたら、この効果は消える。)」の持続する効果
    （``state.NextTurnFailureWaiver``）を与える（v0.121。コイルの「ロックオン」。docs 8 章）。

    - 効果を持つのはワザを使ったポケモン自身。失効を決める参照先は、このワザを受けた相手（今の相手の対戦ポケモンの場の番号）。失敗しなくなるワザは同じカードの ``target_name`` のワザの位置
    - 受けた相手がワザの効果の要素を受けない状態（「ワザをうけない」状態・バリアー・［クリスタルボディ］・［ニュートラルシールド］などの ``first_void``、「とうめい」）なら、相手への効果として
      評価するかが決まらない（LO1。問い ``lock_on_protected_target``。コインを投げない）
    - 相手のワザとして使う（写す）効果は表せない（番をまたぐ効果をワザの位置で記録する。v0.12 の返す効果と同じ ``UNSUPPORTED``）"""

    target_name: str
    phase: ClassVar[Phase] = Phase.EFFECT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        return UNSUPPORTED, "番をまたぐ効果を、効果を持つポケモンのカードのワザの位置で記録するので、相手のワザとして使った効果を表せない（v0.12 の返す効果と同じ）"

    def run(self, run: AttackRun) -> bool:
        from ..state import NextTurnFailureWaiver
        from .kernel import first_void

        state = run.state
        attacker = run.attacker()
        defender = run.opponent_active()
        opponent = 1 - run.player
        if first_void(run.res, run.incoming(), opponent, defender, Window.BEFORE_EFFECT) is not None or E.evasion_power(state, defender) is not None:
            raise run.res.question("lock_on_protected_target", f"ポケモン {defender.pokemon_id}（ワザ {run.key} を受けた相手）")
        attacks = state.definitions[run.key.card_id].attacks
        target = next(attack.index for attack in attacks if attack.name_ja == self.target_name)
        effect = NextTurnFailureWaiver(source_card=attacker.card, source_player=run.player, created_turn=state.turn_number, active_turn=state.turn_number + 2,
                                       attack_index=run.key.attack_index, target_attack_index=target, target_player=opponent,
                                       target_pokemon=defender.pokemon_id, attack_card=effect_attack_card_of(run, attacker))
        add_persistent_effect(state, run.player, attacker, effect, attack=str(run.key), target_attack_index=target, target_player=opponent,
                              target_pokemon=defender.pokemon_id)
        return False


@dataclass(frozen=True)
class DiscardTypeCardForBonus(DiscardOwnEnergy):
    """自分に「``energy_type``」エネルギーカードがついていれば、それを 1 枚トラッシュする（v0.121。わるいヘルガーの「じごくのほのお」の前半。追加のダメージは次の ``Damage`` の
    ``PlusPerDiscarded``。``effects.DiscardTypeEnergyCardForBonus``。docs 8 章）。

    - 選べるものは、ついているカードのうち、カードとしての種類・タイプがその色のもの（``effects.attached_typed_energy_cards``。悪エネルギー）。1 枚でも決定を出す（v0.7 の K2 と同じ）。
      ついていなければトラッシュせず、追加の効果だけがなくなる（``LACKING_SKIP``。ワザの失敗・0 ダメージにしない）。レインボーエネルギーなどの問いは ``transform_energy_question``
    - トラッシュするカードに、ついたまま計算すれば相手の対戦ポケモンへのこのワザのダメージを変える効果（悪エネルギーの「+10」）があり、そのダメージの要素が無効でなければ、当てはめるか
      （トラッシュとダメージの計算の順番）が決まらない（DK1。問い ``discarded_energy_damage_bonus``。トラッシュする前）"""

    def _candidates(self, run: AttackRun, pokemon: PokemonInPlay | None = None) -> list[int]:
        pokemon = run.attacker() if pokemon is None else pokemon
        transform_energy_question(run, pokemon, self.energy_type, cards=True)
        return E.attached_typed_energy_cards(run.state, pokemon, self.energy_type)

    def _discard(self, run: AttackRun, cards: tuple[int, ...]) -> None:
        from .kernel import first_void

        attacker = run.attacker()
        defender = run.opponent_active()
        if defender is not None and not run.knocked_out(defender) and first_void(run.res, run.incoming(), 1 - run.player, defender) is None:
            for card in cards:
                if E.discarded_card_damage_bonus(run.state, attacker, card, defender):
                    raise run.res.question("discarded_energy_damage_bonus", f"ワザ {run.key} でトラッシュするカード {card}")
        super()._discard(run, cards)


@dataclass(frozen=True)
class CoinPerPokemonInPlay(Element):
    """おたがいの場のポケモン全員に対して、1 枚ずつコインを投げ、「おもて」が出たポケモン全員に、「弱点・抵抗力」に関係なく、それぞれ ``amount`` ダメージ（v0.121。わるいリングマの
    「だいらんとう」。``effects.CoinPerPokemonInPlayDamage``。docs 8 章）。

    - 対象はこの要素を処理する時点の、相手のバトル場 → 相手のベンチの並び → 自分のバトル場（ワザを使ったポケモン自身）→ 自分のベンチの並び（実装上の順番。記録の裁定ではない。v0.115 の
      ``CoinPerBenchPokemon`` と同じ形に、バトル場の 2 匹を加えた）。コインは 1 匹 1 枚、この並びの順に 1 回の ``flip`` で投げ、``i`` 枚目は ``i`` 番目のポケモンのもの（面と個体の対応を
      持つ。「おもて」の数でまとめない。ナツメのESPのやり直しは同じ並びに同じ枚数を投げ直す）。結果はログ ``pokemon_coin_results``
    - すべて投げてから、「おもて」のポケモンに並びの順でダメージ（相手のバトル場は ``OPPONENT_ACTIVE``、相手の控えは ``OPPONENT_BENCH``、自分は ``SELF``、自分の控えは ``SELF_BENCH``。
      弱点・抵抗力なし）。控えへのダメージは［ベンチガード］の決定を出しうる。「ダメージを受けたとき」の反応・きぜつは、既存のダメージの要素のあとの窓・ワザのあとの判定
    - 「とうめい」がはたらいているポケモンのあとに対象がいれば TS1、対象がみなダメージの要素を無効にする状態なら投げるかが決まらない（v0.115 と同じ問い）"""

    amount: int
    name: str = "pokemon_coins"
    phase: ClassVar[Phase] = Phase.DAMAGE
    guards_bench: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if type(self.amount) is not int or self.amount <= 0 or self.amount % 10:
            raise ValueError(f"ダメージは 10 の倍数の正の数（{self.amount!r}）")

    def targets(self, run: AttackRun) -> list[tuple[str, int, PokemonInPlay]]:
        state = run.state
        opponent = 1 - run.player
        found: list[tuple[str, int, PokemonInPlay]] = []
        if state.players[opponent].active is not None:
            found.append((E.OPPONENT_ACTIVE, opponent, state.players[opponent].active))
        found += [(E.OPPONENT_BENCH, opponent, p) for p in state.players[opponent].bench]
        found.append((E.SELF, run.player, run.attacker()))
        found += [(E.SELF_BENCH, run.player, p) for p in state.players[run.player].bench]
        return found

    def run(self, run: AttackRun) -> bool:
        from .kernel import first_void

        state = run.state
        targets = self.targets(run)
        if any(E.evasion_power(state, pokemon) is not None for _, _, pokemon in targets[:-1]):
            raise run.res.question("bench_coin_transparency_order", f"おたがいの場のポケモン {[p.pokemon_id for _, _, p in targets]}")
        if all(first_void(run.res, run.incoming(), owner, pokemon) is not None for _, owner, pokemon in targets):
            raise run.res.question("prevented_coin_damage", f"ダメージを受けない場のポケモン {[p.pokemon_id for _, _, p in targets]} へのダメージだけを決めるコイン")
        flips = run.flip(len(targets))
        run.fs.coins[self.name] = flips
        attacker = run.attacker()
        state.add_event("pokemon_coin_results", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                        targets=tuple(p.pokemon_id for _, _, p in targets), owners=tuple(owner for _, owner, _ in targets),
                        results=tuple(face.value for face in flips.results))
        entries = [(kind, pokemon.pokemon_id, self.amount, False) for (kind, _, pokemon), face in zip(targets, flips.results) if face is HEADS]
        return guarded_damages(run, self, entries)


def attack_hand_bench_reaction(state: GameState, owner: int) -> str | None:
    """v0.121（HB1）: プレイヤー ``owner`` の手札のたね・ベイビィポケモンをワザの効果でベンチに出すとき、手札から出したことへの場の反応・特殊能力を止める効果の範囲がかかわるなら、その名前
    （公開の情報だけで決める。手札の中身によらない）。なければ None。状態を変えない。"""
    from ..continuous import goop_gas_effects

    if E.hot_plates(state):
        return "［ヒートプレート］"
    if E.stadium_of(state, E.BenchEntryDamageStadium) is not None:
        return "ロケット団の爆発ジム"
    if goop_gas_effects(state) or E.strange_gas_effects(state, owner) or any(r.kind == E.ATTACK_FIELD_POWER_SUPPRESSION for r in state.trainer_effects):
        return "特殊能力を止める効果"
    return None


def hand_entry_power_cards(state: GameState, cards) -> tuple[int, ...]:
    """v0.121（HB1）: 手札のカード ``cards`` のうち、場に出たときに使える特殊能力（``EntryPower``）を持つもの（ワザの途中に手札から出したときの機会と時点が決まらない。選べるが選ぶと止める）。"""
    return tuple(uid for uid in cards if E.entry_power(state, uid) is not None)


def _hand_bench_reaction_question(run: AttackRun, owners) -> None:
    state = run.state
    for owner in owners:
        p = state.players[owner]
        if not p.hand or len(p.bench) >= bench_limit(state, owner):
            continue
        found = attack_hand_bench_reaction(state, owner)
        if found is not None:
            raise run.res.question("attack_hand_bench_reaction", f"{found}（プレイヤー {owner} の手札からベンチに出しうる。ワザ {run.key}）")


def place_from_hand_in_attack(run: AttackRun, owner: int, cards: tuple[int, ...], chooser: int) -> tuple[PokemonInPlay, ...]:
    """v0.121: プレイヤー ``owner`` の手札のカード ``cards``（手札の並びの順）を、ワザの効果で ``owner`` のベンチの最後に出す（``zones.hand_to_bench_by_effect`` の ``effect``。ログ
    ``attack_bench_from_hand``。選ぶ人は ``chooser``）。出したポケモン（場の番号の個体）を返す。場に出たときの特殊能力を持つカードは、呼ぶ側が選べるが選ぶと止める選択にしている。"""
    attacker = run.attacker()
    return hand_to_bench_by_effect(run.state, owner, cards, chooser=chooser, effect=str(run.key), attacker=run.player, attacker_pokemon_id=attacker.pokemon_id)


@dataclass(frozen=True)
class OpponentHandToBenchThenSwitch(Element):
    """相手プレイヤーの手札を見る。その中にある「たねポケモン」または「ベイビィポケモン」を 1 枚選び、相手のベンチに出す。その後、そのポケモンを相手と入れ替える。(相手のベンチに空きが
    ないとき、このワザは失敗する。)（v0.121。わるいヘルガーの「ぶきみなとおぼえ」。``effects.BenchOpponentHandBasicThenSwitchOrFail``。docs 7 章）。

    - 相手のベンチに空きがなければ、手札を見る前にワザの失敗（ログ ``attack_failed`` の ``reason`` ``opponent_bench_full``。中身を得ない）
    - 手札から出したことへの場の反応・特殊能力を止める効果がかかわるなら HB1（見る前。公開の情報と手札の枚数だけで決め、手札の中身で宣言の受け付けを変えない）
    - 見る（``zones.look_at_hand``。ログの ``cards`` は見たプレイヤーと持ち主だけ）→ 候補（``effects.hand_baby_or_basic``。手札の並び）がなければ何もしない（p.309。ログ
      ``attack_bench_from_hand_none``）→ 選ぶ（決定 ``OPPONENT_HAND_TO_BENCH``。ワザを使ったプレイヤー。ちょうど 1 枚。場に出たときの特殊能力を持つカードは選べるが選ぶと止める（HB1））
    - 出す（``place_from_hand_in_attack``。持ち主・出すベンチは相手）→ 出したその個体（場の番号）を相手の対戦ポケモンと入れ替える。相手の対戦ポケモンが「バトル場をはなれられない」・
      効果の要素を受けないなら入れ替えない（``ForceSwitch`` と同じ確かめ。発生元は ``run.incoming``）。出した個体がベンチにいなければ、ベンチの別のポケモンにすりかえない"""

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = OPPONENT_HAND_TO_BENCH
    opponent_element: ClassVar[str] = E.FORCED_SWITCH_ELEMENT

    def run(self, run: AttackRun) -> bool:
        state = run.state
        opponent = 1 - run.player
        if len(state.players[opponent].bench) >= bench_limit(state, opponent):
            run.fail("opponent_bench_full")
            return False
        _hand_bench_reaction_question(run, (opponent,))
        look_at_hand(state, run.player, opponent, effect=str(run.key))
        candidates = E.hand_baby_or_basic(state, opponent)
        if not candidates:
            attacker = run.attacker()
            state.add_event("attack_bench_from_hand_none", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), owner=opponent)
            return False
        stops = () if run.res.dry_run else hand_entry_power_cards(state, candidates)
        run.suspend(kind=OPPONENT_HAND_TO_BENCH, player=run.player, options=candidates,
                    extra=(("owner", opponent),) + _unresolved_extra(stops, E.ATTACK_HAND_BENCH_REACTION_CODE, E.ATTACK_HAND_BENCH_REACTION_REASON))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        opponent = 1 - run.player
        if decision.context_value("owner") != opponent or len(choices) != 1 or choices[0] not in E.hand_baby_or_basic(state, opponent):
            raise RuntimeError(f"ぶきみなとおぼえで選んだカード {choices} が、相手の手札のたね・ベイビィポケモンではない（エンジンの不具合）")
        if len(state.players[opponent].bench) >= bench_limit(state, opponent):
            raise RuntimeError("ぶきみなとおぼえの決定のあとに、相手のベンチの空きがなくなった（エンジンの不具合）")
        (placed,) = place_from_hand_in_attack(run, opponent, choices, run.player)
        p = state.players[opponent]
        old = p.active
        if not any(pokemon is placed for pokemon in p.bench):
            ForceSwitch._skip(run, old, E.NO_BENCH)
            return
        if _leave_prevented(run, opponent, old, E.LEAVE_FORCED_SWITCH, None):
            return
        if not reaches(run.res, run.fs, opponent, old, E.FORCED_SWITCH_ELEMENT):
            return
        swap_opponent_active(run, opponent, old, placed.pokemon_id, chosen_by="effect")

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return [(option,) for option in decision.options]  # 先読みでは場に出たときの特殊能力の止める選択を付けない（手札の中身で宣言の受け付けを変えない）


@dataclass(frozen=True)
class EachPlayerHandToBench(Element):
    """おたがいのプレイヤーは、それぞれ、相手のプレイヤーの手札を見る。その後、それぞれ、のぞむなら、相手の手札にある「ベイビィポケモン」と「たねポケモン」を、相手のベンチの空きぶん、
    好きなだけ選び、相手のベンチに出してよい（v0.121。わるいリングマの「ちょうはつ」。``effects.EachPlayerBenchesOpponentHandBasics``。docs 7 章）。

    - 手札から出したことへの場の反応・特殊能力を止める効果がかかわるなら HB1（見る前。どちらかのベンチに出しうるとき。公開の情報と手札の枚数だけで決める）
    - 見る: ワザを使ったプレイヤーが相手の手札を、そのあと相手がワザを使ったプレイヤーの手札を（実装上の順番。それぞれ ``zones.look_at_hand``）。片方の手札が 0 枚・ベンチに空きが
      ないときも、もう片方の見る・選ぶを省かない
    - 選ぶ: 1 段目はワザを使ったプレイヤーが相手の手札から、2 段目は相手がワザを使ったプレイヤーの手札から（決定 ``OPPONENT_HAND_TO_BENCH``。続きの情報 ``owner``・``stage``。0〜min(空き, 数) 枚。
      0 枚は「のぞむなら」の出さないこと。選べるカードがない・空きがない段は決定を出さない（ログ ``attack_bench_from_hand_none``））。場に出たときの特殊能力を持つカードは選べるが選ぶと止める
      （HB1）。選んだカードを手札の並びの順に、カードの持ち主のベンチに出す（``place_from_hand_in_attack``）
    - 選ぶ順番（番のプレイヤーから）は実装上の順番。2 つの選択は別の手札・別のベンチで、選んだカードが同じなら結果は順番によらない（出したカードは公開。手札は永久に公開しない）"""

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = OPPONENT_HAND_TO_BENCH

    def run(self, run: AttackRun) -> bool:
        state = run.state
        opponent = 1 - run.player
        _hand_bench_reaction_question(run, (opponent, run.player))
        look_at_hand(state, run.player, opponent, effect=str(run.key))
        look_at_hand(state, opponent, run.player, effect=str(run.key))
        return self._stage(run, 1)

    def _stage(self, run: AttackRun, stage: int) -> bool:
        state = run.state
        while stage <= 2:
            chooser = run.player if stage == 1 else 1 - run.player
            owner = 1 - chooser
            candidates = E.hand_baby_or_basic(state, owner)
            space = bench_limit(state, owner) - len(state.players[owner].bench)
            if candidates and space > 0:
                stops = () if run.res.dry_run else hand_entry_power_cards(state, candidates)
                run.suspend(kind=OPPONENT_HAND_TO_BENCH, player=chooser, options=candidates, min_choices=0, max_choices=min(space, len(candidates)),
                            extra=(("owner", owner), ("stage", stage)) + _unresolved_extra(stops, E.ATTACK_HAND_BENCH_REACTION_CODE, E.ATTACK_HAND_BENCH_REACTION_REASON))
                return True
            attacker = run.attacker()
            state.add_event("attack_bench_from_hand_none", player=chooser, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), owner=owner)
            stage += 1
        return False

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        stage = decision.context_value("stage")
        owner = decision.context_value("owner")
        chooser = run.player if stage == 1 else 1 - run.player
        if stage not in (1, 2) or owner != 1 - chooser or decision.player != chooser or any(c not in E.hand_baby_or_basic(state, owner) for c in choices) \
                or len(state.players[owner].bench) + len(choices) > bench_limit(state, owner):
            raise RuntimeError(f"ちょうはつの決定（段 {stage!r}・持ち主 {owner!r}）の答え {choices} が、相手の手札のたね・ベイビィポケモンを空きの数までではない（エンジンの不具合）")
        if choices:
            ordered = tuple(uid for uid in state.players[owner].hand if uid in set(choices))
            place_from_hand_in_attack(run, owner, ordered, chooser)
        else:
            attacker = run.attacker()
            state.add_event("attack_bench_from_hand_declined", player=chooser, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), owner=owner)
        self._stage(run, stage + 1)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return [()]  # 先読みでは出さない答えだけを試す（出したあとに当たる問いはなく、手札の中身で宣言の受け付けを変えない）


def swap_opponent_active(run: AttackRun, opponent: int, old: PokemonInPlay, new_pid: int, *, chosen_by: str | None) -> None:
    """v0.121: ワザの効果で、相手（``opponent``）のバトル場のポケモン ``old`` と、相手の控えの ``new_pid`` を入れ替える（``ForceSwitch.resume`` から分けた共通の部分。移動・ログ
    ``forced_switch``・特殊状態と持続する効果の消去・発生源がはなれた効果・バトル場に出たら消える効果・ベンチにもどった印・バトル場をはなれた時のトラッシュ）。確かめ（はなれられない・
    効果を受けない）は呼ぶ側。"""
    p = run.state.players[opponent]
    index = next(i for i, pokemon in enumerate(p.bench) if pokemon.pokemon_id == new_pid)
    require_can_leave(run.state, opponent, old)  # v0.93: 決定を出す前に確かめた（``run``）
    p.active, p.bench[index] = p.bench[index], old
    M.note_switch(run.state, opponent, old, p.active)  # v0.87: 入れ替えの事実（相手の［やけのこり］。次の要素の前に処理する）
    extra = {} if chosen_by is None else {"chosen_by": chosen_by}  # v0.31: かどわかす（ふきとばしのログの形は v0.30 と同じ）。v0.121: ぶきみなとおぼえは "effect"
    run.state.add_event(
        "forced_switch",
        player=opponent,
        attacker=run.player,
        attacker_pokemon_id=run.fs.frame.source_pid,
        effect=str(run.key),
        old_active=old.card,
        new_active=p.active.card,
        old_active_pokemon_id=old.pokemon_id,
        new_active_pokemon_id=p.active.pokemon_id,
        **extra,
    )
    clear_special_conditions(run.state, opponent, old, FORCED_SWITCH_REASON)
    remove_persistent_effects(run.state, opponent, old, FORCED_SWITCH_REASON)
    remove_source_left_effects(run.state, opponent, old)  # v0.92: 発生源がバトル場をはなれたら消える効果
    remove_on_entering_active(run.state, opponent, p.active)  # v0.114: バトル場に出てきたら消える効果（じっとみる）
    mark_returned_to_bench(old)  # v0.48: 特殊能力で色を変えた記録に、ベンチにもどったことを残す（VS1）
    E.discard_on_leaving_active(run.state, opponent, old)  # v0.65: バトル場をはなれた時にトラッシュするついているトレーナー（変わり身の術）


BUILDERS |= {
    # おおあくび: 自分 → 相手を、それぞれ特殊状態にする（ダメージを与えたことを条件にしない）
    E.StatusSelfAndOpponent: lambda e: (Status(e.condition, target=SELF), Status(e.condition)),
    # おおいびき: ねむり状態でなければ失敗 → ダメージ（目安）
    E.FailUnlessAsleepDamage: lambda e: (FailUnlessAsleep(), Damage(OPP, Printed())),
    # でんじほう: コイン（1 枚でも「うら」なら失敗。ロックオンの効果があれば失敗しない）→ ダメージ（目安）→ マヒ
    E.CoinsFailThenDamageParalyze: lambda e: (FailOnTails(count=e.coins, waiver=True), Damage(OPP, Printed()), Status(PARALYSIS, reparalysis_check=True)),
    # ロックオン: 自分に次の自分の番の「target_name のコインの「うら」で失敗しない」効果（受けた相手がバトル場をはなれたら消える）
    E.WaiveTailsFailureNextTurn: lambda e: (SelfFailureWaiver(e.target_name),),
    # じごくのほのお: ついている色のエネルギーカードを 1 枚トラッシュ（なければ追加の効果だけがなくなる）→ ダメージ（目安 + トラッシュした枚数 × per）
    E.DiscardTypeEnergyCardForBonus: lambda e: (
        DiscardTypeCardForBonus(e.energy_type, count=1, when_lacking=LACKING_SKIP), Damage(OPP, PlusPerDiscarded("discard", e.per)),
    ),
    # だいらんとう: おたがいの場のポケモン全員に 1 枚ずつコイン →「おもて」のポケモンに弱点・抵抗力なしで amount
    E.CoinPerPokemonInPlayDamage: lambda e: (CoinPerPokemonInPlay(e.amount),),
    # ぶきみなとおぼえ: 相手のベンチに空きがなければ失敗 → 相手の手札を見る → たね・ベイビィを 1 枚相手のベンチに出す → そのポケモンを相手と入れ替える
    E.BenchOpponentHandBasicThenSwitchOrFail: lambda e: (OpponentHandToBenchThenSwitch(),),
    # ちょうはつ: おたがいに相手の手札を見る → それぞれ、のぞむなら相手の手札のたね・ベイビィを相手のベンチの空きぶん出す
    E.EachPlayerBenchesOpponentHandBasics: lambda e: (EachPlayerHandToBench(),),
}


# v0.122（docs/unown-fossil-retreat-reactions-v0.122.md）: 10まんボルト（GD3-003）・きりもみアタック・みだれうち・いやなかふん・ドリルダイブ
BUILDERS |= {
    # 10まんボルト: 自分についているエネルギーカードをすべてトラッシュ（ワザの効果。決定なし。0 枚ならトラッシュできない）→ ダメージ（トラッシュできなければ基本となるダメージ 0）
    E.DiscardAllEnergyCardsThenDamageZeroIfLacking: lambda e: (
        DiscardOwnEnergy(None, count=None, when_lacking=LACKING_ZERO, timing=TIMING_EFFECT), Damage(OPP, Printed(), requires="discard"),
    ),
    # きりもみアタック: 相手へのダメージ → 自分へのダメージ（弱点・抵抗力だけを計算しない）
    E.DamageAndSelfDamageIgnoringWeaknessResistance: lambda e: (
        Damage(OPP, Printed()), Damage(SELF, Fixed(e.self_damage), name="self_damage", weakness_resistance=False),
    ),
    # みだれうち: 相手プレイヤーが相手の場のポケモンに units 単位を配る（同じポケモンの単位は合算した 1 回のダメージ。弱点・抵抗力に関係なく）
    E.OpponentChoosesRepeatedTargetsDamage: lambda e: (AllocateDamage(FixedUnits(e.units), e.per, scope=E.TARGET_IN_PLAY, chooser=CHOOSER_OPPONENT),),
    # いやなかふん: ダメージ → 2 枚のコイン → どく → 「おもて」1 枚ならねむり・2 枚ならこんらん・0 枚ならマヒ（同じコインの組）
    E.DamageThenPoisonAndStatusByTwoCoins: lambda e: (
        Damage(OPP, Printed()), Coin("coins", count=2), Status(POISON), Status(SLEEP, gate=("coins", Exactly(1))),
        Status(CONFUSION, gate=("coins", Exactly(2))), Status(PARALYSIS, gate=("coins", Exactly(0)), reparalysis_check=True),
    ),
    # ドリルダイブ: ダメージ → 次の自分の番、ワザ（すべて）を使えない → 「にげる」ことができない（どちらも自分に与える持続する効果）
    E.DamageThenSelfCannotAttackOrRetreat: lambda e: (Damage(OPP, Printed()), SelfCannotAttack(), SelfCannotRetreat()),
}


# v0.123（docs/arcanine-name-migration-v0.123.md 5 章）: いかりのほのお（PR1-016）。既存の要素の新しい組み合わせ
BUILDERS |= {
    # いかりのほのお: 自分の「炎」エネルギーカードを count 枚トラッシュ（ワザの効果。足りなければ使えない）→ ダメージ（目安 + 自分のダメージカウンターの数 × per）
    E.DiscardEnergyBeforeDamagePlusOwnCounters: lambda e: (
        DiscardOwnEnergy(e.energy_type, count=e.count, when_lacking=LACKING_CANNOT_USE, timing=TIMING_EFFECT), Damage(OPP, PlusOwnCounters(e.per), requires="discard"),
    ),
}

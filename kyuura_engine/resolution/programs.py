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
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

from .. import effects as E
from ..cards import EnergyType
from ..coins import CoinFlips, CoinSide, flip_coins
from ..conditions import CONFUSION, PARALYSIS, POISON, SLEEP, clear_special_conditions, confuse, paralysis_problem, paralyze, poison, put_to_sleep
from ..conditions import FORCED_SWITCH as FORCED_SWITCH_REASON
from ..decisions import (
    ATTACH_FROM_DISCARD, ATTACH_TO_BENCH, DISCARD_ENERGY, DISCARD_OPPONENT_ENERGY, FORCED_SWITCH, RECOVER_ENERGY, RECOVER_TRAINER, SELECT_ATTACK,
    SELECT_POKEMON,
)
from ..errors import UnsupportedError
from ..persistent import add_persistent_effect, remove_persistent_effects
from ..state import (
    RETALIATION_FIXED, RETALIATION_KINDS, RETALIATION_RECEIVED, AttackBarrier, CannotAttack, DamageReduction, DestinyBond, NextTurnAttackDamage,
    PreventDamage, Retaliation,
)
from ..zones import attach_from_discard, discard_from_deck, draw_cards, return_discard_to_hand

from . import catalog as C
from . import codec
from .events import ElementStarted, Suspended, Window
from .kernel import Resolution, check_simultaneous, deal_damage, fire_pending, reaches

if TYPE_CHECKING:
    from ..cards import Attack
    from ..state import GameState, PendingDecision, PokemonInPlay

    from .events import FrameState


class UnsupportedByKernel(NotImplementedError):
    """プロトタイプの対応表にないワザの実装（黙って効果のないワザとして処理しない）。"""


class Phase(str, Enum):
    DAMAGE = "damage"
    EFFECT = "effect"
    NEUTRAL = "neutral"
    CONTRACT = "contract"  # v0.16b: v0.13 の約束で書いた実装のアダプタ（contract.Contract）


OPP = E.OPPONENT_ACTIVE
SELF = E.SELF
HEADS = CoinSide.HEADS
TAILS = CoinSide.TAILS
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

    def opponent_active(self) -> PokemonInPlay:
        return self.state.players[1 - self.player].active

    def flip(self, count: int) -> CoinFlips:
        attacker = self.attacker()
        return flip_coins(self.state, self.player, count, source="attack", effect=str(self.key), card=attacker.card, pokemon_id=attacker.pokemon_id)

    def coin_is(self, gate: tuple) -> bool:
        """ワザ全体のコインの面（(名前, CoinSide)）か、v0.31 の「おもて」の数（(名前, 数)）が合うか。"""
        name, side = gate
        if isinstance(side, CoinSide):
            return self.fs.coins[name].results[0] is side
        return self.fs.coins[name].heads == side

    def heads(self, name: str) -> int:
        """ワザ全体のコイン ``name`` の「おもて」の数（v0.31）。"""
        return self.fs.coins[name].heads

    def apply_redirect(self) -> None:
        """``redirect`` の要素の並びに切りかえる（v0.31。相手のワザを自分のワザとして使う）。枠のワザ（ログの ``effect``・ダメージを変える効果を
        探すワザ）は、選んだワザになる。宣言したワザ（``declared``）は変えない。"""
        key, attack, program = self.redirect
        self.redirect = None
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
        frame = dict(carried.get("frame", ()))
        for pid, value in frame.get("reception", ()):
            self.fs.reception[pid] = bool(value)
        self.fs.fired = frame.get("fired", 0)
        for pid, value in frame.get("guts", ()):
            self.res.ko_prevention_able.setdefault(pid, bool(value))

    def knocked_out(self, pokemon: PokemonInPlay) -> bool:
        """効果の対象が、このワザの処理の中で HP 以上になった（p.309「処理の対象がなくなってしまっている場合」。きぜつの処理はワザのあと）。
        v0.13 では、ワザの実装によって今のダメージで比べるものと、ダメージの要素の結果で見るものがあった（audit 4.3）。ここでは今のダメージで
        比べる（今の対応カードでは同じ答え）。"""
        return pokemon.damage >= self.state.card_def(pokemon.card).hp

    def ko_prevention_conflict(self, target: PokemonInPlay, owner: int | None = None) -> None:
        """効果の対象がきぜつして効果を飛ばすとき、その対象がきぜつの判定で任意の効果（こんじょう）を使えるなら、効果を受けるかが原典で
        決まらない（相手の対戦ポケモンは G37）。v0.17b: 対象がワザを使ったポケモン自身（``owner`` が番のプレイヤー）なら、同じ形の問いで、
        今の対応カードでは起こらない（自分に効果を与えるワザを持つポケモンに、こんじょうはない。コードのない問い）。"""
        owner = 1 - self.player if owner is None else owner
        for instance in C.in_window(self.state, Window.KO_CHECK, owner, target, self.res.catalog):
            if instance.definition.timing is not C.Timing.OFFER:
                continue
            if self.res.ko_prevention_able.get(target.pokemon_id) and not C.suppressors(self.state, instance):
                if owner == self.player:
                    raise self.res.question("ko_prevention_self_effect", f"ポケモン {target.pokemon_id}")
                raise self.res.question("ko_prevention_attack_effect", f"ポケモン {target.pokemon_id}",
                                        E.ko_prevention_attack_effect_error(target.pokemon_id, opponent_effect_elements(self.program)))
            break

    def suspend(self, *, kind: str, player: int, options, extra: tuple = (), min_choices: int = 1, max_choices: int = 1,
                carry: bool = False) -> None:
        """決定を出して止まる。v0.31: 決定をまたいで要素が使う値を続きの情報に運ぶ: ワザ全体のコインの結果（``coins``。あるときだけ）・相手の
        ワザを自分のワザとして使っているときの選んだワザ（``copied``）・``carry`` なら枠の値（``frame``: 「とうめい」の結果（T4。1 つのワザで 1 匹
        1 回）・処理した送る効果の数（C34・C35）・こんじょうの写し）。v0.30 までの決定の形は変えない（どれも運ぶ値がない）。"""
        if self.fs.pending:
            raise RuntimeError("決定の前に送る効果が残っている（窓の位置の誤り。エンジンの不具合）")
        check_simultaneous(self.res)  # 決定をまたぐと、きぜつの原因の記録はなくなるので、ここで確かめる
        attacker = self.attacker()
        extra = tuple(extra)
        if self.key != self.declared:
            extra += (("copied", (self.key.card_id, self.key.attack_index)),)
        if self.fs.coins:
            extra += (("coins", tuple((name, tuple(side.value for side in flips.results)) for name, flips in self.fs.coins.items())),)
        if carry:
            frame = (
                ("reception", tuple(sorted((pid, int(value)) for pid, value in self.fs.reception.items()))),
                ("fired", self.fs.fired),
                ("guts", tuple(sorted((pid, int(value)) for pid, value in self.res.ko_prevention_able.items()))),
            )
            extra += (("frame", frame),)
        cont = codec.AttackContinuation((self.player, attacker.pokemon_id, self.declared.card_id, self.declared.attack_index), kind, extra)
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
        if run.failed or index >= len(run.program):
            break
        element = run.program[index]
        if element.phase is Phase.EFFECT:
            fire_pending(res, run.fs)
        elif element.phase is Phase.NEUTRAL and run.fs.pending:
            raise RuntimeError("ワザ全体のコイン・確認は、ダメージの要素より前に置く（エンジンの不具合）")
        res.trace.record(ElementStarted(run.fs.frame.id, index, type(element).__name__, element.phase.value))
        if element.run(run):
            if not res.dry_run:
                return True
            while run.suspended is not None:  # 先読み: 決定の答えを選んで続ける（答えのあとでもう一度決定を出す要素もある）
                decision, run.suspended = run.suspended, None
                element.resume(run, decision, res.oracle.choose(element.dry_choices(run, decision)))
        index += 1
    fire_pending(res, run.fs)
    return False


def opponent_effect_elements(program: tuple) -> tuple[str, ...]:
    """並びの中で、相手の対戦ポケモンに与えるダメージ以外の効果の要素の種類（並びの順番。v0.13 の ``AttackEffect.opponent_effect_elements``
    にあたる値を、ワザの実装の宣言ではなく並びから求める。G37 の理由の文に書く）。"""
    found: list[str] = []
    for element in program:
        kind = element.opponent_element
        if kind is not None and kind not in found:
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
    coins: int
    per: int

    @property
    def local_coins(self) -> int:
        return self.coins

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return flips.heads * self.per


@dataclass(frozen=True)
class HeadsOwnCounters:
    per: int
    local_coins: ClassVar[int] = 1

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        counters = run.attacker().damage // run.state.rules.damage_per_counter
        return counters * self.per if flips.results[0] is HEADS else 0


@dataclass(frozen=True)
class ExtraEnergy:
    energy_type: EnergyType
    per: int
    max_extra: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        attacker = run.attacker()
        attached = sum(1 for uid in attacker.energy if run.state.card_def(uid).provides is self.energy_type)
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

    @property
    def opponent_element(self) -> str | None:
        """相手の対戦ポケモンに与える、ダメージ以外の効果の要素の種類（``effects.ATTACK_ELEMENTS``。なければ None）。"""
        return None

    def run(self, run: AttackRun) -> bool:
        raise NotImplementedError

    def decides(self, kind: str) -> bool:
        """決定の種類 ``kind`` を出す要素か（再開する要素を決定の種類から探す。v0.16b から要素が答える）。"""
        return self.decision_kind is not None and self.decision_kind == kind

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        """決定の答えのあと。v0.16b から、``resume`` がもう一度決定を出してもよい（``run.suspended``。v0.13 の約束の 2 段階の決定）。"""
        raise NotImplementedError(f"{type(self).__name__} は決定を出さない")

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        """先読みで試す答え: 決定に合うすべての答え（選ぶ数・選ぶもの・順番。v0.15c）。"""
        return all_answers(decision)

    def on_declare(self, res: Resolution, player: int, attacker: PokemonInPlay) -> None:
        """ワザの宣言のあと・こんらんのコインの前の確認（v0.31）。既定は何もしない。"""
        return None

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
    low = max(decision.min_choices, minimum)
    return [answer for count in range(low, decision.max_choices + 1) for answer in itertools.permutations(decision.options, count)]


@dataclass(frozen=True)
class Coin(Element):
    """ワザ全体のコイン（ダメージと効果の両方を決める）。v0.31: ``count`` 枚（カツラのリザードの「やきはらう」は 3 枚）、または ``per_attached``
    のエネルギーカードがワザを使うポケモンについている数だけ（わるいリザードンの「れんぞくファイヤーボール」。0 枚なら投げない）。"""

    name: str
    count: int = 1
    per_attached: EnergyType | None = None
    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        count = self.count
        if self.per_attached is not None:
            count = len(E.attached_basic_energy(run.state, run.attacker(), self.per_attached))
        run.fs.coins[self.name] = run.flip(count) if count else CoinFlips(())
        return False


@dataclass(frozen=True)
class FailOnTails(Element):
    """コインを 1 枚投げ、「うら」ならワザは失敗する（v0.31。ファイヤーの「ゴッドバード」・わるいリザードの「ファイヤーボール」。p.323「12 ワザの
    失敗」: 失敗してもワザを使ったことになる）。結果はワザ全体のコイン ``name`` として、あとの要素も使う。

    ``only_damage``: 残りの要素が相手の対戦ポケモンへのダメージだけ（ゴッドバード）。そのポケモンがダメージの要素を無効にする状態（かたまる・
    バリアー）なら、このコインはそのダメージの量だけを決めるので、投げるかが決められない（v0.4b の ``prevented_coin_damage`` と同じ問い）。"""

    name: str = "coin"
    only_damage: bool = False
    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        if self.only_damage:
            from .kernel import first_void

            target = run.opponent_active()
            void = first_void(run.res, 1 - run.player, target)
            if void is not None:
                raise run.res.question("prevented_coin_damage", f"ポケモン {target.pokemon_id}",
                                       E.prevented_coin_damage_error(target.pokemon_id, void.implementation.kind))
        flips = run.flip(1)
        run.fs.coins[self.name] = flips
        if flips.results[0] is TAILS:
            run.fail("coin")
        return False


@dataclass(frozen=True)
class ReparalysisGuard(Element):
    """ワザ全体のコインの前に、マヒの再付与で回復する番が決まらない場合を確かめる（v0.13 の ``CoinBonusDamageAndParalyze``）。"""

    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        problem = paralysis_problem(run.state, 1 - run.player, run.opponent_active())
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
    phase: ClassVar[Phase] = Phase.DAMAGE

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        zero = False
        if self.requires is not None:
            discarded = run.fs.results.get(self.requires)
            if discarded is not None and discarded.outcome == LACKING_NONE:
                return False  # 「トラッシュできないとき、このワザのダメージはなくなる」（RUL-ENERGY-DISCARD-ATTACKS）
            zero = discarded is not None and discarded.outcome == LACKING_ZERO  # 「（トラッシュできない時、このワザのダメージは0になる）」
        coins = local_coins(self.base, run)
        if coins:
            owner = 1 - run.player if self.target == OPP else run.player
            receiver = run.opponent_active() if self.target == OPP else run.attacker()
            from .kernel import first_void

            void = first_void(run.res, owner, receiver)
            if void is not None:
                raise run.res.question("prevented_coin_damage", f"ポケモン {receiver.pokemon_id}",
                                       E.prevented_coin_damage_error(receiver.pokemon_id, void.implementation.kind))
        if self.local_gate is not None:
            gate_flips = run.flip(1)
            if self.coin_name is not None:
                run.fs.coins[self.coin_name] = gate_flips
            if gate_flips.results[0] is not self.local_gate:
                return False
        flips = run.flip(coins) if coins else None
        base = 0 if zero else self.base.value(run, flips)
        run.fs.results[self.name] = deal_damage(run.res, run.fs, self.target, base, weakness_resistance=self.weakness_resistance)
        return False


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
    phase: ClassVar[Phase] = Phase.EFFECT

    @property
    def opponent_element(self) -> str | None:
        return self.condition if self.target == OPP else None

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        if self.after_damage is not None:
            result = run.fs.results[self.after_damage]
            if result.dealt <= 0:
                raise run.res.question("effect_after_no_damage", f"ポケモン {result.pokemon_id}",
                                       E.effect_after_no_damage_error(str(run.key), result, self.condition))
        if self.target == SELF:
            owner, target = run.player, run.attacker()
        else:
            owner, target = 1 - run.player, run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target, owner)
            return False
        if self.reparalysis_check:
            problem = paralysis_problem(run.state, owner, target)
            if problem is not None:
                raise run.res.question("reparalysis_recovery_turn", problem.code, error=problem)
        if self.local_coin is not None:
            if run.fs.reception.get(target.pokemon_id) is False:
                final = run.fs.evaded.get(target.pokemon_id)
                raise run.res.question("evaded_effect_coin", f"ポケモン {target.pokemon_id}",
                                       None if final is None else E.evaded_effect_coin_error(target.pokemon_id, final))
            prevented_effect_coin(run, owner, target)  # v0.31: 「ワザをうけない」状態（バリアー）なら、効果だけを決めるコインを投げるか決まらない
            if run.flip(1).results[0] is not self.local_coin:
                return False
        if reaches(run.res, run.fs, owner, target, self.condition):
            APPLY_CONDITION[self.condition](run.state, owner, target, effect=str(run.key))
        return False


def prevented_effect_coin(run: AttackRun, owner: int, target: PokemonInPlay) -> None:
    """効果の要素のコインの前に、対象が効果の要素を無効にする状態（v0.31。バリアー）なら問い（HC3。コインはその効果だけを決めるので、投げるかが
    決められない。v0.4b の ``prevented_coin_damage`` と同じ形）。"""
    from .kernel import first_void

    void = first_void(run.res, owner, target, Window.BEFORE_EFFECT)
    if void is not None:
        raise run.res.question("prevented_effect_coin", f"ポケモン {target.pokemon_id}（{void.implementation.kind}）")


@dataclass(frozen=True)
class ForceSwitch(Element):
    """相手の対戦ポケモンをベンチにもどし、相手が選んだ控えと入れ替える（ふきとばし。v0.13 の ``DamageAndForceSwitch`` と同じ結果・ログ）。"""

    chooser: str = "opponent"  # v0.31: 選ぶのは相手（ふきとばし）か、ワザを使ったプレイヤー（"attacker"。キュウコンの「かどわかす」）
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = FORCED_SWITCH
    opponent_element: ClassVar[str] = E.FORCED_SWITCH_ELEMENT

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        p = run.state.players[opponent]
        target = p.active
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            self._skip(run, target, E.TARGET_KNOCKED_OUT)
            return False
        if not p.bench:
            self._skip(run, target, E.NO_BENCH)
            return False
        if not reaches(run.res, run.fs, opponent, target, E.FORCED_SWITCH_ELEMENT):
            return False
        chooser = run.player if self.chooser == "attacker" else opponent
        run.suspend(kind=FORCED_SWITCH, player=chooser, options=[pokemon.pokemon_id for pokemon in p.bench],
                    extra=(("target", target.pokemon_id),))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        opponent = 1 - run.player
        p = run.state.players[opponent]
        old = p.active
        target = run.carried.get("target")
        if old is None or old.pokemon_id != target:
            raise RuntimeError(f"入れ替えの対象 {target} が相手のバトル場にいない（エンジンの不具合）")
        index = next(i for i, pokemon in enumerate(p.bench) if pokemon.pokemon_id == choices[0])
        p.active, p.bench[index] = p.bench[index], old
        extra = {"chosen_by": "attacker"} if self.chooser == "attacker" else {}  # v0.31: かどわかす（ふきとばしのログの形は v0.30 と同じ）
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


@dataclass(frozen=True)
class Drain(Element):
    """相手にダメージを与えたら、自分のダメージカウンターをとりのぞく（メガドレイン・やどりぎのタネ）。``counters`` が None なら与えた
    ダメージの半分（カウンターの単位で切り上げ）。"""

    source: str
    counters: int | None = None
    phase: ClassVar[Phase] = Phase.EFFECT

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
            counters = (result.dealt // per + 1) // 2
        else:
            counters = self.counters
        before = attacker.damage
        removed = min(counters, before // per)
        attacker.damage = before - removed * per
        state.add_event("drain_heal", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                        dealt=result.dealt, drain_counters=counters, counters=removed, amount=removed * per, damage_before=before,
                        total_damage=attacker.damage)
        return False


@dataclass(frozen=True)
class SelfRetaliation(Element):
    """自分に「次の相手の番、相手のワザのダメージを受けたら返す」持続する効果（ほのおのかべ: ``amount``、こうらがえし: None = 受けたダメージ）。"""

    amount: int | None
    phase: ClassVar[Phase] = Phase.EFFECT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        # v0.31: この持続する効果は、効果を与えたワザを、効果を持つポケモンのカードのワザの位置（``attack_index``）で持つ。相手のワザを自分のワザと
        # して使ったときの効果は、その位置で表せない（書き出しの形を変えずには持てない）ので、エンジンの未対応として選べない
        return UNSUPPORTED, "番をまたぐ効果を、効果を持つポケモンのカードのワザの位置で記録するので、相手のワザとして使った効果を表せない"

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        basis = RETALIATION_FIXED if self.amount is not None else RETALIATION_RECEIVED
        if run.knocked_out(attacker):
            run.state.add_event("persistent_effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                persistent_effect=RETALIATION_KINDS[basis], effect=str(run.key), reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        effect = Retaliation(source_card=attacker.card, source_player=run.player, created_turn=run.state.turn_number,
                             active_turn=run.state.turn_number + 1, attack_index=run.key.attack_index, amount=self.amount, basis=basis)
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
    phase: ClassVar[Phase] = Phase.EFFECT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        # v0.31: この持続する効果は、効果を与えたワザを、効果を持つポケモンのカードのワザの位置（``attack_index``）で持つ。相手のワザを自分のワザと
        # して使ったときの効果は、その位置で表せない（書き出しの形を変えずには持てない）ので、エンジンの未対応として選べない
        return UNSUPPORTED, "番をまたぐ効果を、効果を持つポケモンのカードのワザの位置で記録するので、相手のワザとして使った効果を表せない"

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        turn = run.state.turn_number
        effect = NextTurnAttackDamage(source_card=attacker.card, source_player=run.player, created_turn=turn,
                                      active_turn=turn + NextTurnAttackDamage.turns_until_active, attack_index=run.key.attack_index,
                                      target_attack_index=self.target_attack_index, amount=self.amount)
        add_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key))
        return False


# v0.31: トラッシュできない（ついているエネルギーカードが足りない）ときの扱い（``DiscardOwnEnergy.when_lacking``）
LACKING_ERROR = "error"  # 今の対応カードでは起こらない（ワザに必要なエネルギーが足りているので）。起こったらエンジンの不具合
LACKING_FAIL = "fail"  # このワザは失敗する（カツラのリザードの「やきはらう」）
LACKING_ZERO = "zero"  # このワザのダメージは 0 になる（わるいリザードの「ファイヤーボール」など）
LACKING_NONE = "none"  # このワザのダメージ（効果）はなくなる（RUL-ENERGY-DISCARD-ATTACKS の最新の説明・じこさいせいの K3）
LACKING_CONDITION = "condition"  # 印刷の文面が「はがしてすてる」の形（ワザを使うための条件か効果かが決められない。HC1）
LACKING_CANNOT_USE = "cannot_use"  # 説明が「…トラッシュしなければ（はがしてすてなければ）、このワザは使えない」と書いている

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
    gate: tuple | None = None
    local_coin: CoinSide | None = None
    name: str = "discard"
    when_lacking: str = LACKING_ERROR
    timing: str = TIMING_EFFECT
    copy_need: int | None = None  # 相手のワザとして使うときに必要な枚数（``heads_of`` のときのいちばん多い数。None なら ``count``）
    deck_limit: bool = False  # ``any_number``: 選べる数は相手の山札の枚数まで（ファイヤーの「やまやき」。多ければ HC6）
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = DISCARD_ENERGY

    def _candidates(self, run: AttackRun, pokemon: PokemonInPlay | None = None) -> list[int]:
        pokemon = run.attacker() if pokemon is None else pokemon
        if self.energy_type is None:
            return [uid for uid in pokemon.energy if run.state.card_def(uid).category == "energy"]
        return E.attached_basic_energy(run.state, pokemon, self.energy_type)

    def _needed(self, run: AttackRun) -> int | None:
        if self.heads_of is not None:
            return run.heads(self.heads_of)
        return self.count

    def on_declare(self, res: Resolution, player: int, attacker: PokemonInPlay) -> None:
        if self.timing == TIMING_UNRESOLVED and attacker.conditions.confused:
            raise res.question("discard_energy_timing", f"ポケモン {attacker.pokemon_id}")

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
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        candidates = self._candidates(run)
        needed = self._needed(run)
        if needed is None:
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
            run.suspend(kind=DISCARD_ENERGY, player=run.player, options=candidates, min_choices=0, max_choices=len(candidates))
            return True
        run.suspend(kind=DISCARD_ENERGY, player=run.player, options=candidates, min_choices=needed, max_choices=needed)
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
        for energy in cards:
            attacker.energy.remove(energy)
            state.players[owner].discard.append(energy)
            state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy=energy)
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


@dataclass(frozen=True)
class RecoverEnergy(Element):
    """自分のトラッシュのエネルギーカードを ``max_cards`` 枚まで選んで手札に加える（エナジーへんかん。0 枚は原典で決められない。H4）。"""

    max_cards: int
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = RECOVER_ENERGY

    @staticmethod
    def _candidates(run: AttackRun) -> list[int]:
        return [uid for uid in run.state.players[run.player].discard if run.state.card_def(uid).category == "energy"]

    def run(self, run: AttackRun) -> bool:
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
class PlusDefenderEnergy:
    """ダメージの目安の数字 +「相手についているエネルギーカード」の枚数 × ``per``（ミュウツーの「サイコキネシス」）。"""

    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        target = run.opponent_active()
        return run.attack.damage + sum(1 for uid in target.energy if run.state.card_def(uid).category == "energy") * self.per


@dataclass(frozen=True)
class PlusOwnCounters:
    """ダメージの目安の数字 + 自分にのっているダメージカウンターの数 × ``per``（わるいブースターの「いかり」）。"""

    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return run.attack.damage + run.attacker().damage // run.state.rules.damage_per_counter * self.per


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

    def coin_count(self, run: AttackRun) -> int:
        return len(run.fs.results[self.discard].cards)

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return (0 if flips is None else flips.heads) * self.per


@dataclass(frozen=True)
class PerMilledEnergy:
    """山札からトラッシュの要素 ``mill`` でトラッシュしたカードの中の ``energy_type`` の基本エネルギーカードの数 × ``per``（カツラのブーバーの
    「マグマふんしゅつ」）。"""

    mill: str
    energy_type: EnergyType
    per: int
    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        cards = run.fs.results[self.mill].cards
        definitions = [run.state.card_def(uid) for uid in cards]
        return sum(1 for d in definitions if d.is_basic_energy and d.provides is self.energy_type) * self.per


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
        types = run.state.energy_types(run.attacker())
        have = types.count(self.energy_type)
        others = len(types) - have
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
    関係なく。"""

    base: Any
    pokemon_type: EnergyType | None = None
    weakness_resistance: bool = False
    gate: tuple | None = None
    name: str = "bench_damage"
    phase: ClassVar[Phase] = Phase.DAMAGE

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        if local_coins(self.base, run):
            raise RuntimeError("控えポケモンへのダメージの量を、要素の中のコインで決めるワザはない（エンジンの不具合）")
        opponent = 1 - run.player
        targets = [p for p in run.state.players[opponent].bench
                   if self.pokemon_type is None or run.state.card_def(p.card).pokemon_type is self.pokemon_type]
        for target in targets:
            deal_damage(run.res, run.fs, E.OPPONENT_BENCH, self.base.value(run, None), pokemon_id=target.pokemon_id,
                        weakness_resistance=self.weakness_resistance)
        return False


@dataclass(frozen=True)
class SelfPersistent(Element):
    """ワザを使ったポケモン自身に、次の相手の番にはたらく持続する効果を与える（v0.31。みちづれ ``DestinyBond``・バリアー ``AttackBarrier``・
    ちいさくなる ``DamageReduction``）。``requires`` のトラッシュの要素がトラッシュできなかったら与えない。"""

    kind: str
    amount: int | None = None
    requires: str | None = None
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        if self.requires is not None:
            discarded = run.fs.results.get(self.requires)
            if discarded is not None and discarded.outcome != "done":
                return False
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("persistent_effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                persistent_effect=self.kind, effect=str(run.key), reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        turn = run.state.turn_number
        common = {"source_card": attacker.card, "source_player": run.player, "created_turn": turn, "active_turn": turn + 1}
        if self.kind == DestinyBond.kind:
            effect = DestinyBond(**common)
        elif self.kind == AttackBarrier.kind:
            effect = AttackBarrier(**common)
        elif self.kind == DamageReduction.kind:
            effect = DamageReduction(**common, amount=self.amount)
        else:
            raise ValueError(f"知らない持続する効果の種類 {self.kind!r}")
        add_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key))
        return False


@dataclass(frozen=True)
class OpponentCannotAttack(Element):
    """コインが「おもて」なら、相手の対戦ポケモンは次の相手の番にワザを使えない（v0.31。イーブイの「しっぽをふる」。持続する効果 ``CannotAttack``。
    相手に与える効果なので「とうめい」・「ワザをうけない」状態を評価する）。"""

    local_coin: CoinSide | None = HEADS
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.ATTACK_LOCK_ELEMENT

    def run(self, run: AttackRun) -> bool:
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
    コインも投げない（内容の対象がない。p.309）。決定はポケモンごと（対戦ポケモン → 控えの並びの順）。"""

    each_bench: bool = False
    local_coin: CoinSide | None = None
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = DISCARD_OPPONENT_ENERGY
    opponent_element: ClassVar[str] = E.ENERGY_DISCARD_ELEMENT

    @staticmethod
    def _energy(run: AttackRun, pokemon: PokemonInPlay) -> list[int]:
        return [uid for uid in pokemon.energy if run.state.card_def(uid).category == "energy"]

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        p = run.state.players[opponent]
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

            if all(first_void(run.res, opponent, pokemon, Window.BEFORE_EFFECT) is not None for pokemon in targets):
                raise run.res.question("prevented_effect_coin", f"ポケモン {[pokemon.pokemon_id for pokemon in targets]}")
            if run.flip(1).results[0] is not self.local_coin:
                return False
        return self._next(run, [pokemon.pokemon_id for pokemon in targets])

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
            run.suspend(kind=DISCARD_OPPONENT_ENERGY, player=run.player, options=self._energy(run, target),
                        extra=(("target", pid), ("queue", tuple(queue))), carry=True)
            return True
        return False

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        opponent = 1 - run.player
        pid = run.carried["target"]
        queue = list(run.carried.get("queue", ()))
        found = run.state.find_pokemon(pid)
        if found is None or found[0] != opponent or choices[0] not in found[1].energy:
            raise RuntimeError(f"トラッシュに選んだカード {choices} が、相手のポケモン {pid} についていない（エンジンの不具合）")
        target = found[1]
        energy = choices[0]
        target.energy.remove(energy)
        run.state.players[opponent].discard.append(energy)
        attacker = run.attacker()
        run.state.add_event("discard_attached_energy", player=opponent, pokemon=target.card, pokemon_id=target.pokemon_id, energy=energy,
                            effect=str(run.key), attacker=run.player, attacker_pokemon_id=attacker.pokemon_id)
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

    @staticmethod
    def _candidates(run: AttackRun) -> list[int]:
        return [uid for uid in run.state.players[run.player].discard if run.state.card_def(uid).category == "trainer"]

    def run(self, run: AttackRun) -> bool:
        if self.requires is not None:
            discarded = run.fs.results.get(self.requires)
            if discarded is not None and discarded.outcome != "done":
                return False
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
    山札が足りなければ引けるだけ引く（効果で引くときの規定。p.312。v0.2b のマサキと同じ）。"""

    count: int
    gate: tuple | None = None
    requires: str | None = None
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        if self.requires is not None:
            discarded = run.fs.results.get(self.requires)
            if discarded is not None and discarded.outcome != "done":
                return False
        draw_cards(run.state, run.player, min(self.count, len(run.state.players[run.player].deck)))
        return False


@dataclass(frozen=True)
class AttachFromDiscard(Element):
    """自分のトラッシュに ``energy_type`` の基本エネルギーカードがあれば、最大 ``max_cards`` 枚を取り出して、自分（ワザを使ったポケモン）につける
    （v0.31。マチスのエレブーの「たいでん」）。なければ何もしない（「あれば」）。0 枚を選べるかは決められない（HC7。答えのときに止める）。"""

    energy_type: EnergyType
    max_cards: int
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = ATTACH_FROM_DISCARD

    def _candidates(self, run: AttackRun) -> list[int]:
        return [uid for uid in run.state.players[run.player].discard
                if run.state.card_def(uid).is_basic_energy and run.state.card_def(uid).provides is self.energy_type]

    def run(self, run: AttackRun) -> bool:
        candidates = self._candidates(run)
        if not candidates:
            return False
        run.suspend(kind=ATTACH_FROM_DISCARD, player=run.player, options=candidates, min_choices=0,
                    max_choices=min(self.max_cards, len(candidates)))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if not choices:
            raise UnsupportedError(
                "UNRESOLVED_ATTACH_FROM_DISCARD_ZERO",
                "トラッシュに「雷」エネルギーカードがあるときに 0 枚を選べるか（「最大2枚を取り出して」が 0 枚を含むか）は決められないので扱わない（HC7）。"
                "1 枚以上を選ぶ",
            )
        candidates = self._candidates(run)
        if any(uid not in candidates for uid in choices):
            raise RuntimeError(f"つけるカード {choices} が、トラッシュの「{self.energy_type.ja}」エネルギーカードではない（エンジンの不具合）")
        cards = tuple(uid for uid in run.state.players[run.player].discard if uid in choices)  # トラッシュの並びの順につける（選んだ順によらない）
        attacker = run.attacker()
        attach_from_discard(run.state, run.player, cards, attacker)
        run.state.add_event("attach_energy_from_discard", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                            effect=str(run.key), cards=cards)
        for uid in cards:
            E.after_energy_attached(run.state, run.player, attacker, uid)

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
                attacker.energy.remove(uid)
                state.players[run.player].discard.append(uid)
                state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                energy=uid, reason="no_bench")
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
        attacker.energy.remove(energy)
        if reaches(run.res, run.fs, run.player, target, E.ENERGY_ATTACH_ELEMENT):
            target.energy.append(energy)
            state.add_event("attack_attach_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy=energy, to_pokemon_id=target.pokemon_id)
            E.after_energy_attached(state, run.player, target, energy)
        else:
            state.players[run.player].discard.append(energy)  # 「とうめい」の「おもて」: エネルギーカードはトラッシュ（CR-TRANSPARENCY-ENERGY-BOMB）
            state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy=energy, reason="evaded", to_pokemon_id=target.pokemon_id)
        self._next(run, remaining)


@dataclass(frozen=True)
class MillOwnDeck(Element):
    """自分の山札の上から、カードを ``count`` 枚トラッシュする（v0.31。カツラのブーバーの「マグマふんしゅつ」）。山札が足りなければ決められない
    （HC6。宣言の前に止める）。"""

    count: int
    name: str = "mill"
    phase: ClassVar[Phase] = Phase.EFFECT

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
    「やまやき」）。枚数が相手の山札より多い答えは、トラッシュの要素の答えのときに止めている（HC6）。"""

    from_discard: str = "discard"
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        discarded = run.fs.results.get(self.from_discard)
        count = 0 if discarded is None else len(discarded.cards)
        if count == 0:
            return False
        opponent = 1 - run.player
        if len(run.state.players[opponent].deck) < count:
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

    def decides(self, kind: str) -> bool:
        return kind in (DISCARD_ENERGY, SELECT_POKEMON)

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                element="discard_energy", reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
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
            owner, attacker = state.find_pokemon(run.fs.frame.source_pid)
            if choices[0] not in E.attached_basic_energy(state, attacker, self.energy_type):
                raise RuntimeError(f"トラッシュに選んだカード {choices} が、ワザを使ったポケモンについていない（エンジンの不具合）")
            attacker.energy.remove(choices[0])
            state.players[owner].discard.append(choices[0])
            state.add_event("discard_energy", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy=choices[0])
            bench = state.players[1 - run.player].bench
            if not bench:
                return
            run.suspend(kind=SELECT_POKEMON, player=run.player, options=[p.pokemon_id for p in bench], carry=True)
            return
        deal_damage(run.res, run.fs, E.OPPONENT_BENCH, self.damage, pokemon_id=choices[0], weakness_resistance=False)


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
        effect = run.state.effects.attack_effect(definition.id, attack, definition.attacks)
        if effect is None:
            return UNSUPPORTED, "効果の実装が登録されていない"
        builder = BUILDERS.get(type(effect))
        if builder is None:
            return UNSUPPORTED, f"実装 {type(effect).__name__} に解決の基盤の要素の並びがない"
        copier = run.attacker()
        for element in builder(effect):
            problem = element.copy_problem(run, copier, self.clause)
            if problem is not None:
                return problem
        return None

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        source = run.opponent_active()
        definition = run.state.card_def(source.card)
        if not definition.attacks:
            return False
        statuses = {attack.index: self._status(run, definition, attack) for attack in definition.attacks}
        options = [index for index, status in statuses.items() if status is None or status[0] != ILLEGAL]
        if not any(status is None for status in statuses.values()):
            detail = "・".join(f"{definition.attacks[i].name_ja}: {status[1]}" for i, status in statuses.items())
            if any(status[0] == UNSUPPORTED for status in statuses.values()):
                # 処理できるワザがなく、そのうちエンジンが対応していないワザがある（ルールの問いではない）
                raise run.res.question("copied_attack_unsupported", f"{definition.id}（{detail}）")
            raise run.res.question("copied_attack", f"{definition.id}（{detail}）")
        unresolved = tuple(i for i in options if statuses[i] is not None and statuses[i][0] == UNRESOLVED)
        unsupported = tuple(i for i in options if statuses[i] is not None and statuses[i][0] == UNSUPPORTED)
        extra: tuple = (("copy_from", definition.id),)
        if unresolved:
            reason = "・".join(f"{definition.attacks[i].name_ja}: {statuses[i][1]}" for i in unresolved)
            extra += (("unresolved_choices", unresolved), ("unresolved_code", "UNRESOLVED_COPIED_ATTACK"),
                      ("unresolved_reason", f"相手のワザを自分のワザとして使うとき、処理が決められない（HC9。{reason}）"))
        if unsupported:
            extra += (("unsupported_choices", unsupported),)
        run.suspend(kind=SELECT_ATTACK, player=run.player, options=options, extra=extra)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        index = choices[0]
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


# ---------------------------------------------------------------- 登録表の実装 → 要素の並び（v0.13 の 24 種類と、v0.17 から加えた型）

BUILDERS: dict[type, Any] = {
    E.DamageOnly: lambda e: (Damage(OPP, Printed()),),
    E.CoinFlipDamage: lambda e: (Damage(OPP, HeadsTimes(e.coins, e.damage_per_heads)),),
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
    E.SleepOnHeadsWithoutDamage: lambda e: (Status(SLEEP, local_coin=HEADS),),
    E.DiscardEnergyThenSelfEffect: lambda e: (
        DiscardOwnEnergy(e.energy_type, when_lacking=LACKING_CONDITION, timing=TIMING_UNRESOLVED), SelfPersistent(e.effect_kind, requires="discard"),
    ),
    E.DamagePlusDefenderEnergy: lambda e: (Damage(OPP, PlusDefenderEnergy(e.per)),),
    E.DamagePlusOwnCounters: lambda e: (Damage(OPP, PlusOwnCounters(e.per)),),
    E.CopyOpponentAttackEffect: lambda e: (CopyOpponentAttack(e.clause),),
    E.ReduceDamageNextTurn: lambda e: (SelfPersistent(DamageReduction.kind, amount=e.amount),),
    E.DiscardFireThenMillOpponent: lambda e: (
        DiscardOwnEnergy(EnergyType.FIRE, any_number=True, deck_limit=True, when_lacking=LACKING_CONDITION, timing=TIMING_UNRESOLVED),
        MillOpponentDeck(),
    ),
    E.FailOnTailsDamage: lambda e: (FailOnTails(only_damage=True), Damage(OPP, Printed())),
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
    E.ThreeCoinPsychicPower: lambda e: (
        Coin("coin", count=3), Damage(OPP, Fixed(20), gate=("coin", 2)), Draw(1, gate=("coin", 1)), CopyOpponentAttack(gate=("coin", 3)),
    ),
    E.CannotAttackOnHeads: lambda e: (OpponentCannotAttack(HEADS),),
    E.DamageAndBenchTypeDamage: lambda e: (Damage(OPP, Printed()), BenchDamage(Fixed(e.bench_damage), pokemon_type=e.pokemon_type)),
}


def compile_attack(effect: E.AttackEffect) -> tuple[Element, ...]:
    """v0.13 のワザの実装から要素の並びを作る（部分型は使わない。実装の型が完全に一致するものだけ）。"""
    builder = BUILDERS.get(type(effect))
    if builder is None:
        raise UnsupportedByKernel(f"ワザの実装 {type(effect).__name__}（{effect.implementation_id}）はプロトタイプの対応表にない")
    return builder(effect)

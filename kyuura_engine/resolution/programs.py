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
from ..damage import DAMAGE_STEP_CHOOSER, DamageOrderRequired, step_orders
from ..decisions import (
    ATTACH_FROM_DECK, ATTACH_FROM_DISCARD, ATTACH_FROM_HAND, ATTACH_TO_BENCH, BENCH_FROM_DECK, DAMAGE_STEP_ORDER, DISCARD_ENERGY, DISCARD_OPPONENT_ENERGY,
    DISCARD_TO_DECK_TOP, FORCED_SWITCH, HAND_TO_DECK, MOVE_OPPONENT_ENERGY, RECOVER_ENERGY, RECOVER_TRAINER, REMOVE_COUNTERS, RETURN_ENERGY, SEARCH_DECK, SELECT_ATTACK,
    SELECT_COLOR, SELECT_OPPONENT_ATTACK, SELECT_POKEMON, SELECT_SPECIAL_CONDITION,
)
from ..decisions import ARRANGE_DECK_TOP, SELECT_DECK_OWNER, SELECT_HAND_CARD, SELECT_LOOK_COUNT
from ..errors import UnsupportedError
from ..evolution import place_evolution_card
from ..persistent import RETURN_IN_PLAY_TO_DECK, RETURN_IN_PLAY_TO_HAND, add_persistent_effect, max_hp_set, remove_persistent_effects, replace_persistent_effect
from ..state import (
    NEXT_TURN_MULTIPLY, NEXT_TURN_SET, RETALIATION_FIXED, RETALIATION_RECEIVED, AttackBarrier, AttackCoinCheck, CannotAttack,
    CannotAttackWhileSourceActive, CannotRetreat, CannotUseAttack, CannotUseOwnAttack, DamageReduction, DestinyBond, HalvedDamage, NextTurnAttackDamage, PreventDamage,
    MaxHpSet, ReducedDamageToSource, ResistanceChange, Retaliation, TrainerUseLock, WeaknessChange, ZeroDamageBelow, mark_returned_to_bench,
)
from ..zones import (
    attach_energy_from_hand, attach_from_deck, attach_from_discard, bench_from_deck, discard_attached_cards, discard_from_deck, draw_cards, promote_from_bench, put_discard_on_deck_top,
    return_discard_to_hand, return_hand_cards_to_deck, return_in_play_to_deck, return_in_play_to_hand, reveal_deck_to_hand, shuffle_deck, take_deck_top,
)
from ..zones import look_at_card

from . import catalog as C
from . import codec
from .events import ElementStarted, Suspended, Window
from .kernel import Resolution, check_simultaneous, deal_damage, fire_pending, reaches, track_ko, type_question, weakness_resistance_matters
from .questions import QUESTIONS

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

    def flip(self, count: int, *, by_heads: bool = False, player: int | None = None) -> CoinFlips:
        """コインを ``count`` 枚投げる。``by_heads``（v0.35）: 結果を「おもて」の数だけで使うコイン（先読みが「おもて」の数でまとめて試せる。
        ``coins.flip_coins``。実際の対戦の投げ方・乱数・ログは同じ）。並びの順番（1 枚目の面など）を使う要素は渡さない。

        ``player``（v0.40）: コインを投げるプレイヤー（既定はワザを使ったプレイヤー）。説明が「相手プレイヤーに…コインを投げさせ」と書くワザ（わるいスリーパーの
        「ベンチをあやつる」）は相手。乱数の使い方（1 枚 1 回 ``getrandbits(1)``）は同じで、ログ ``coin_flip`` の ``player`` だけが変わる（``card``・
        ``pokemon_id``・``effect`` はワザを使ったポケモンとワザ）。"""
        attacker = self.attacker()
        return flip_coins(self.state, self.player if player is None else player, count, source="attack", effect=str(self.key), card=attacker.card,
                          pokemon_id=attacker.pokemon_id, by_heads=by_heads)

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
        pending = frame.get("pending", ())
        if pending:
            from .kernel import restore_deferred

            self.fs.pending.extend(restore_deferred(self.res, self.fs, pending))
        for pid, value in frame.get("guts", ()):
            self.res.ko_prevention_able.setdefault(pid, bool(value))
        # v0.46: ワザが使われた時の特殊状態（くつろぐかおり）。決定の前の宣言で写した値（書いていなければ空。決定をまたいでも今の特殊状態で決め直さない）
        self.res.attack_status = frozenset(carried.get("attack_status", ()))

    def knocked_out(self, pokemon: PokemonInPlay) -> bool:
        """効果の対象が、このワザの処理の中で HP 以上になった（p.309「処理の対象がなくなってしまっている場合」。きぜつの処理はワザのあと）。
        v0.13 では、ワザの実装によって今のダメージで比べるものと、ダメージの要素の結果で見るものがあった（audit 4.3）。ここでは今のダメージで
        比べる（今の対応カードでは同じ答え）。"""
        return pokemon.damage >= E.max_hp(self.state, pokemon)  # v0.48: 今有効な最大HP

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
        if carry:
            frame = (
                ("reception", tuple(sorted((pid, int(value)) for pid, value in self.fs.reception.items()))),
                ("fired", self.fs.fired),
                ("guts", tuple(sorted((pid, int(value)) for pid, value in self.res.ko_prevention_able.items()))),
            )
            if self.fs.pending:
                # v0.34: まだ処理していない送る効果（「ダメージを受けたとき」の効果。ダメージの要素がすべて終わったあとに処理する。p.89）。持ち主・
                # 持つポケモン・効果の定義の名前・受けたダメージだけを運び、再開のときに場の効果から作り直す（``kernel.restore_deferred``）。
                # 送る効果がないときは v0.33 までと同じ形
                frame += (("pending", tuple((d.instance.owner, d.instance.pokemon_id, d.instance.definition.name, d.received)
                                            for d in self.fs.pending)),)
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
        if run.failed or index >= len(run.program):
            break
        element = run.program[index]
        if element.phase is Phase.EFFECT:
            if run.fs.pending and any(later.phase is Phase.DAMAGE for later in run.program[index + 1:]):
                # v0.38: 「ダメージを受けたとき」の効果がはたらいていて、このあとにダメージ以外の効果をはさんでダメージの要素がある（サイドンの「げきとつ」の
                # 入れ替え → 自分にも 20）。その効果を、ダメージの処理（自分へのダメージを含む）をすべてのせたあと・ダメージ以外の効果の前に処理する
                # （CR-COUNTERATTACK-TIMING・CR-FIRE-WALL-TIMING・CR-SHELL-ATTACK-TIMING）時点がなく、決められない（GK1）
                raise res.question("damage_trigger_timing", f"{[d.instance.name for d in run.fs.pending]}・{type(element).__name__} のあとのダメージの要素")
            fire_pending(res, run.fs)
        elif element.phase is Phase.NEUTRAL and run.fs.pending:
            if any(later.phase is Phase.DAMAGE for later in run.program[index + 1:]):
                raise RuntimeError("ダメージの要素を決めるワザ全体のコイン・確認は、ダメージの要素より前に置く（エンジンの不具合）")
            # v0.41: ダメージの要素のあとの、ダメージ以外の効果だけを決めるワザ全体のコイン（ナツメのモルフォンの「げんかくおんぱ」・v0.37 のニャースの
            # 「ねこにこばん」）。「ダメージを受けたとき」の効果は、そのワザのダメージの処理のあと・ダメージ以外の効果（効果を決めるコインを含む）の前に
            # 処理する（CR-COUNTERATTACK-TIMING・CR-FIRE-WALL-TIMING・CR-SHELL-ATTACK-TIMING）ので、コインの前に処理する。v0.40 までは、ここで
            # RuntimeError（内部エラー）になっていた（ねこにこばんをカイリキーの「はんげき」などに使うと止まった。docs/heal-counter-status-v0.41.md 3.5）
            fire_pending(res, run.fs)
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
        decided = [element for element in run.program if element.coin_dependent(self.name)]
        if count and decided and not any(element.has_target(run) for element in decided):
            # v0.38: このコインが決める要素のどれにも処理の対象がない（フリーザーの「ふぶき」で、自分にも相手にも控えポケモンがいない）。投げない（p.309。
            # v0.31 のスーパーデストロイ・v0.33 のかけぬけると同じ読み方）。結果のないコインの面は、どの要素も満たさない（``coin_is``）
            count = 0
        if count:
            # v0.34: このコインが決める要素（``coin_dependent``）がどれも、受ける相手の対戦ポケモンにとって無効なら、投げるかが決められない。
            # v0.38: 処理の対象がない要素（控えのいない側の控えへのダメージ）は、コインの結果で場を変えないので数えない（カツラのギャロップの「ふみあらす」を、
            # 控えのいない「ワザをうけない」相手に使うと、追加のダメージだけが残り、それも無効。v0.37 までの型では has_target を上書きする要素がなく、同じ）
            void_coin_question(run, [element for element in decided if element.has_target(run)])
        by_heads = self.count > 1 or self.per_attached is not None
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
    from .kernel import first_void

    owner, target = 1 - run.player, run.opponent_active()
    if run.fs.reception.get(target.pokemon_id) is False:
        final = run.fs.evaded.get(target.pokemon_id)
        raise run.res.question("evaded_effect_coin", f"ポケモン {target.pokemon_id}",
                               None if final is None else E.evaded_effect_coin_error(target.pokemon_id, final))
    if "effect" in roles:
        void = first_void(run.res, owner, target, Window.BEFORE_EFFECT)
        if void is not None:
            raise run.res.question("prevented_effect_coin", f"ポケモン {target.pokemon_id}（{void.implementation.kind}。ダメージと効果を決めるコイン）")
        return
    void = first_void(run.res, owner, target)
    if void is not None:
        raise run.res.question("prevented_coin_damage", f"ポケモン {target.pokemon_id}",
                               E.prevented_coin_damage_error(target.pokemon_id, void.implementation.kind))


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
    phase: ClassVar[Phase] = Phase.NEUTRAL

    def run(self, run: AttackRun) -> bool:
        index = next((i for i, element in enumerate(run.program) if element is self), None)
        if index is None:
            raise RuntimeError("ワザの失敗のコインの要素が、処理している要素の並びにない（エンジンの不具合）")
        void_coin_question(run, list(run.program[index + 1:]))
        flips = run.flip(self.count, by_heads=True)  # v0.35: すべて「おもて」か（「おもて」の数が枚数か）だけを使う
        run.fs.coins[self.name] = flips
        if any(side is TAILS for side in flips.results):
            run.fail("coin")
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
    phase: ClassVar[Phase] = Phase.DAMAGE

    def coin_receiver(self) -> str | None:
        return "damage" if self.target == OPP else None

    def has_target(self, run: AttackRun) -> bool:
        if self.names is None:
            return True
        _, receiver = receiver_of_target(run, self.target)
        return run.state.card_def(receiver.card).name_ja in self.names

    def decides(self, kind: str) -> bool:
        # v0.35: 同じ段階の変更効果の計算の順番の決定（``DAMAGE_STEP_ORDER``）。並びの中にダメージの要素が 2 つ以上あっても、続きの情報の
        # ``element``（要素の位置）で区別する（``flow._resume_attack``）
        return kind == DAMAGE_STEP_ORDER

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
        # v0.40: 相手プレイヤーが投げるコイン（``flipped_by_opponent``。ベンチをあやつる）
        flipper = 1 - run.player if getattr(self.base, "flipped_by_opponent", False) else None
        flips = run.flip(coins, by_heads=getattr(self.base, "by_heads", False), player=flipper) if coins else None
        base = 0 if zero else self.base.value(run, flips)
        return self._deal(run, base, {})

    def _deal(self, run: AttackRun, base: int, orders: dict[int, tuple[int, ...]]) -> bool:
        """基本となるダメージ ``base`` を与える。同じ段階の変更効果の計算の順番によって結果が変わるなら、順番の決定を出して止まる（v0.35）。"""
        try:
            run.fs.results[self.name] = deal_damage(run.res, run.fs, self.target, base, weakness_resistance=self.weakness_resistance,
                                                    orders=orders or None, order_decision=True, resistance=self.resistance)
        except DamageOrderRequired as need:
            suspend_step_order(run, self, need, base, orders)
            return True
        return False

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        base, orders = resume_step_order(run, self, decision, choices)
        self._deal(run, base, orders)


def suspend_step_order(run: AttackRun, element: Element, need: DamageOrderRequired, base: int, orders: dict[int, tuple[int, ...]]) -> None:
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
    used_later = {value for later in run.program[index + 1:] for value in _result_names(later)}
    if run.fs.applied or run.fs.evaded or any(name in used_later for name in run.fs.results if name != getattr(element, "name", None)):
        raise run.res.question("damage_step_order", f"ポケモン {run.fs.frame.source_pid}・{need.step} 段階の効果 {[m.label for m in need.modifiers]}"
                                                     "（前の要素の結果を決定のあとに運べない）")
    target = element.target
    owner, receiver = receiver_of_target(run, target)
    chooser = run.player if DAMAGE_STEP_CHOOSER[need.step] == "attacker" else owner
    permutations = step_orders(len(need.modifiers))
    described = tuple((m.label, m.source, m.operation, m.amount) for m in need.modifiers)
    # v0.45: 「抵抗力」の影響を受けないダメージ（スパイラルショット）だけ ``resistance`` を書く（v0.44 までの決定の形は変えない）
    resistance = (("resistance", False),) if getattr(element, "resistance", True) is False else ()
    run.suspend(kind=DAMAGE_STEP_ORDER, player=chooser, options=tuple(range(len(permutations))),
                extra=(("element", index), ("base", base), ("orders", tuple(sorted(orders.items()))), ("step", need.step), ("target", target),
                       ("receiver", receiver.pokemon_id), ("weakness_resistance", getattr(element, "weakness_resistance", True)),
                       *resistance, ("modifiers", described), ("permutations", permutations)),
                carry=True)


def resume_step_order(run: AttackRun, element: Element, decision: PendingDecision, choices: tuple[int, ...]) -> tuple[int, dict[int, tuple[int, ...]]]:
    """順番の決定の答えのあと（v0.35）: 続きの情報の基本となるダメージと、選んだ順番を加えた段階の順番を返す（コインを投げ直さない。ダメージは
    呼ぶ側がもう一度計算して与える）。決定を待つ間に場は変わらないので、受けるポケモン・その段階の変更効果が続きの情報と違えばエンジンの不具合。"""
    carried = run.carried
    step = carried["step"]
    permutations = tuple(tuple(order) for order in carried["permutations"])
    if decision.kind != DAMAGE_STEP_ORDER or len(choices) != 1 or not 0 <= choices[0] < len(permutations):
        raise RuntimeError(f"順番の決定の答え {choices!r} が、選べる順番の番号ではない（エンジンの不具合）")
    owner, receiver = receiver_of_target(run, element.target)
    if receiver.pokemon_id != carried["receiver"]:
        raise RuntimeError("順番の決定を待つ間に、ダメージを受けるポケモンが変わった（エンジンの不具合）")
    orders = {int(k): tuple(v) for k, v in carried.get("orders", ())}
    orders[step] = permutations[choices[0]]
    return carried["base"], orders


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
        if self.poison_damage is not None and not immune:
            current = target.conditions.poison
            if current is not None and current.damage != self.poison_damage:
                # v0.34: どく状態のポケモンが、どくのダメージの違う特殊などくを受ける（p.322 は特殊などく → 通常のどくの向きだけを書く。
                # v0.3a の 15。「とうめい」のコインより先に聞く。先読みがすべての結果を試すので、どちらでも宣言の前に止まる）
                raise run.res.question("special_poison_overwrite", f"ポケモン {target.pokemon_id}（どくのダメージ {current.damage} → {self.poison_damage}）")
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
        if condition == POISON and self.poison_damage is not None:
            poison(run.state, owner, target, effect=str(run.key), damage=self.poison_damage)
            return False
        APPLY_CONDITION[condition](run.state, owner, target, effect=str(run.key))
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
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = FORCED_SWITCH
    opponent_element: ClassVar[str] = E.FORCED_SWITCH_ELEMENT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        if self.required and not run.state.players[1 - run.player].bench:
            return (ILLEGAL if clause in (CANNOT_USE, FOLLOW_TEXT) else UNRESOLVED), "相手に控えポケモンがいない（ワザを使うための条件）"
        return None

    def run(self, run: AttackRun) -> bool:
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
        run.suspend(kind=FORCED_SWITCH, player=chooser, options=[pokemon.pokemon_id for pokemon in p.bench],
                    extra=(("target", target.pokemon_id),), carry=self.carry)
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
        mark_returned_to_bench(old)  # v0.48: 特殊能力で色を変えた記録に、ベンチにもどったことを残す（VS1）
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


@dataclass(frozen=True)
class Drain(Element):
    """相手にダメージを与えたら、自分のダメージカウンターをとりのぞく（メガドレイン・やどりぎのタネ）。``counters`` が None なら与えた
    ダメージの半分（カウンターの単位で切り上げ）。v0.32: ``full`` なら与えたぶん（与えたダメージ ÷ 10 個。きゅうけつ）。どれも、のっている数まで。"""

    source: str
    counters: int | None = None
    full: bool = False
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
            counters = result.dealt // per if self.full else (result.dealt // per + 1) // 2
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
                             multiplier=self.multiplier, on_heads=self.on_heads)
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
                                      target_attack_index=self.target_attack_index, amount=self.amount, operation=self.operation,
                                      includes_self_damage=self.includes_self_damage)
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
    # v0.45: トラッシュする数は「このワザに必要なエネルギーよりも多い ``energy_type`` のエネルギー」すべて（カツラのリザードンの「ファイヤーブレス」）。ついている
    # ``energy_type`` の基本エネルギーカードの枚数から、ワザに必要なエネルギーの ``energy_type`` の数を引いたもの（0 より少なければ 0。そのときはトラッシュせず、決定も
    # 出さない）。どのカードかはワザを使ったプレイヤーが選ぶ（その数ちょうど）
    excess_over_cost: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = DISCARD_ENERGY

    def _candidates(self, run: AttackRun, pokemon: PokemonInPlay | None = None) -> list[int]:
        pokemon = run.attacker() if pokemon is None else pokemon
        if self.energy_type is None:
            return [uid for uid in pokemon.energy if run.state.card_def(uid).category == "energy"]
        return E.attached_basic_energy(run.state, pokemon, self.energy_type)

    def _needed(self, run: AttackRun) -> int | None:
        if self.excess_over_cost:
            required = sum(1 for cost in run.attack.cost if cost is self.energy_type)
            return max(0, len(self._candidates(run)) - required)
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
    by_heads: ClassVar[bool] = True  # v0.35: 「おもて」の数だけを使う（先読みは「おもて」の数でまとめる。トラッシュした枚数だけ投げる）

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
    phase: ClassVar[Phase] = Phase.DAMAGE

    def targets(self, run: AttackRun) -> list[PokemonInPlay]:
        side = run.player if self.own else 1 - run.player
        bench = run.state.players[side].bench
        named = [p for p in bench if self.names is None or run.state.card_def(p.card).name_ja in self.names]
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

    def has_target(self, run: AttackRun) -> bool:
        return bool(self.targets(run))  # v0.38: 控えポケモンがいなければ、処理の対象がない

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        if local_coins(self.base, run):
            raise RuntimeError("控えポケモンへのダメージの量を、要素の中のコインで決めるワザはない（エンジンの不具合）")
        targets = self.targets(run)
        kind = E.SELF_BENCH if self.own else E.OPPONENT_BENCH
        if self.weakness_resistance is None:
            differs = [p.pokemon_id for p in targets
                       if weakness_resistance_matters(run.res, run.fs, kind, self.base.value(run, None), p.pokemon_id)]
            if differs:
                raise run.res.question("bench_damage_weakness_resistance", f"控えのポケモン {differs}")
        for target in targets:
            deal_damage(run.res, run.fs, kind, self.base.value(run, None), pokemon_id=target.pokemon_id,
                        weakness_resistance=bool(self.weakness_resistance))
        return False


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
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
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
        run.fs.results[self.name] = deal_damage(run.res, run.fs, E.SELF_BENCH if self.own else E.OPPONENT_BENCH, self.base.value(run, None),
                                                pokemon_id=choices[0], weakness_resistance=bool(self.weakness_resistance))


@dataclass(frozen=True)
class ChosenOpponentPokemonDamage(ChosenBenchDamage):
    """相手の場のポケモン（対戦ポケモン・控えポケモン）を 1 匹選び、そのポケモンにダメージ（v0.43。わるいゴルバットの「ふらふらとぶ」）。v0.33 の
    ``ChosenBenchDamage`` の選べるものに相手の対戦ポケモンを含めた形（コインはない。相手の場には対戦ポケモンが必ずいるので、選べるものは必ずある）。

    対戦ポケモンを選んだら p.320 のダメージの (1)（``OPPONENT_ACTIVE``。プラスパワー・ディフェンダーを計算する）、控えポケモンを選んだら (2)
    （``OPPONENT_BENCH``。プラスパワーは変えない）。決定の答えのあとの計算なので、同じ段階の変更効果の順番を選ぶ決定は出せない（順番で結果が変われば問い
    ``damage_step_order``。v0.35 の控えへのダメージと同じ）。"""

    local_coin: CoinSide | None = None

    def run(self, run: AttackRun) -> bool:
        if local_coins(self.base, run):
            raise RuntimeError("相手の場のポケモンへのダメージの量を、要素の中のコインで決めるワザはない（エンジンの不具合）")
        if self.own or self.required or self.weakness_resistance is not False:
            raise RuntimeError("相手の場のポケモンを選ぶダメージは、自分の場・使うための条件・弱点・抵抗力の問いのない形だけ（エンジンの不具合）")
        side = run.state.players[1 - run.player]
        if self.local_coin is not None:
            # v0.44: ロケット団のニャースの「こばんなげ」（コインの「おもて」なら選ぶ）。コインはダメージの要素だけを決める。相手に控えがいれば、どの控えも受けるので
            # 止めない。控えがなく、選べるのが相手の対戦ポケモンだけなら、相手の対戦ポケモンへのダメージの要素と同じ確かめ（v0.34 の ``void_coin_question``。
            # 「ダメージを受けない」「ワザをうけない」状態なら v0.4b の問い、「とうめい」で受けないと決まっていれば T19b）
            if not side.bench:
                void_coin_question(run, [Damage(OPP, self.base)])
            if run.flip(1).results[0] is not self.local_coin:
                return False
        options = [p.pokemon_id for p in side.in_play()]
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=options, carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        side = run.state.players[1 - run.player]
        if side.active is not None and choices[0] == side.active.pokemon_id:
            run.fs.results[self.name] = deal_damage(run.res, run.fs, E.OPPONENT_ACTIVE, self.base.value(run, None), weakness_resistance=False)
            return
        if choices[0] not in [p.pokemon_id for p in side.bench]:
            raise RuntimeError(f"選んだポケモン {choices} が、相手の場にいない（エンジンの不具合）")
        run.fs.results[self.name] = deal_damage(run.res, run.fs, E.OPPONENT_BENCH, self.base.value(run, None), pokemon_id=choices[0],
                                                weakness_resistance=False)


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
        elif self.kind == PreventDamage.kind:
            effect = PreventDamage(**common)  # v0.45: わるいカメックスの「ロケットタックル」（自分へのダメージのあとのコイン。HP 以上なら投げない）
        elif self.kind == ZeroDamageBelow.kind:
            effect = ZeroDamageBelow(**common, threshold=self.amount)  # v0.45: イワークの「かたくなる」（しきい値 ``amount``）
        elif self.kind == HalvedDamage.kind:
            effect = HalvedDamage(**common)  # v0.46: エリカのタマタマの「リフレクター」（半分（切りすて））
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

            if all(run.fs.reception.get(pokemon.pokemon_id) is False for pokemon in targets):
                # v0.33: 前のダメージの要素で「とうめい」の「おもて」になり、このワザで受けないと決まったポケモンだけへの効果のコイン（はかいでんぱ・
                # はかいビーム。T19b と同じ問い。v0.31 のスーパーデストロイは前にダメージの要素がないので起こらない）
                finals = [run.fs.evaded.get(pokemon.pokemon_id) for pokemon in targets]
                raise run.res.question("evaded_effect_coin", f"ポケモン {[pokemon.pokemon_id for pokemon in targets]}",
                                       E.evaded_effect_coin_error(targets[0].pokemon_id, finals[0]) if len(targets) == 1 and finals[0] is not None else None)
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
    reads_deck_order: ClassVar[bool] = True  # v0.40: 山札の上から引く

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
    # v0.45: ちょうど ``max_cards`` 枚（R団のサンダーの「プラズマ」の「あれば、1枚取り出して」。0 枚は選べない）。v0.31 の「たいでん」は「最大2枚」（0 枚は HC7）
    exact: bool = False
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = ATTACH_FROM_DISCARD

    def _candidates(self, run: AttackRun) -> list[int]:
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
        candidates = self._candidates(run)
        if not candidates:
            return False
        count = min(self.max_cards, len(candidates))
        run.suspend(kind=ATTACH_FROM_DISCARD, player=run.player, options=candidates, min_choices=count if self.exact else 0, max_choices=count)
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
    「やまやき」）。枚数が相手の山札より多い答えは、トラッシュの要素の答えのときに止めている（HC6）。"""

    from_discard: str = "discard"
    phase: ClassVar[Phase] = Phase.EFFECT
    reads_deck_order: ClassVar[bool] = True  # v0.40: 相手の山札の上からトラッシュする

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
        if effect.once_after_entering_play:
            # v0.44: 「このワザは、このカードが場に出てから、1回しか使えない」ワザ。使った記録はワザを持つカードのワザの位置（``PokemonInPlay.attacks_used_once``）
            # なので、まねたポケモンの記録を表せない（エンジンの未対応。v0.36 のドわすれと同じ扱い）
            return UNSUPPORTED, "場に出てから1回しか使えないワザの使った記録を、ワザを持つカードのワザの位置で持つので、まねたポケモンの記録を表せない"
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
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = BENCH_FROM_DECK

    def candidates(self, run: AttackRun) -> list[int]:
        if self.owner is not None:
            return E.deck_owner_basic_pokemon(run.state, run.player, self.owner)
        return E.bench_from_deck_candidates(run.state, run.player, self.names, self.pokemon_type)

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        if len(run.state.players[run.player].bench) >= run.state.rules.max_bench:
            return (ILLEGAL if clause in (CANNOT_USE, FOLLOW_TEXT) else UNRESOLVED), "自分のベンチに空きがない（ワザを使うための条件）"
        return None

    def run(self, run: AttackRun) -> bool:
        state = run.state
        if len(state.players[run.player].bench) >= state.rules.max_bench:
            raise RuntimeError(f"ベンチに空きがないのに、ワザ {run.key} の山札からベンチに出す処理に来た（使うための条件の確認の漏れ。エンジンの不具合）")
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False  # v0.45: 自分の山札への効果なので、相手の状態によらず投げる。「うら」なら何もしない（山札を切らない）
        candidates = self.candidates(run)
        if not candidates:
            attacker = run.attacker()
            extra = {} if self.pokemon_type is None else {"pokemon_type": self.pokemon_type.value}  # v0.34: タイプで選ぶとき
            if self.owner is not None:
                extra["owner"] = self.owner  # v0.45: 「(owner)のポケモン」で選ぶとき
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
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_POKEMON

    def run(self, run: AttackRun) -> bool:
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
    中（ダメージの量だけを決める）。エネルギーの数は ``state.energy_types`` の数（今の写しでは、ついている基本エネルギーカードの枚数と同じ）。"""

    per: int
    by_heads: ClassVar[bool] = True  # v0.35: 「おもて」の数だけを使う（先読みは「おもて」の数でまとめる。v0.34 の 13 枚からの上限の拒否を解消した）

    def coin_count(self, run: AttackRun) -> int:
        return len(run.state.energy_types(run.attacker()))

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
        for uid in attacker.energy:
            if not run.state.card_def(uid).is_basic_energy:
                # 2 つ以上のエネルギーを出す特殊エネルギーを加えるときは、数え方（カードの枚数ではなくエネルギーの数）を確かめる
                raise RuntimeError(f"ウォーターパンチのエネルギーの数え方を確かめていないエネルギーカード {uid}（エンジンの不具合）")
        return sum(1 for kind in run.state.energy_types(attacker) if kind is self.energy_type)

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
    phase: ClassVar[Phase] = Phase.EFFECT

    def copy_problem(self, run: AttackRun, copier: PokemonInPlay, clause: str | None) -> tuple[str, str] | None:
        # 番をまたぐ効果を、効果を持つポケモンのカードのワザの位置で記録する（v0.31 の SelfNextTurnAttackDamage と同じ）。相手のワザとして使ったときの
        # 「このカードは「あわあわ」を使えない」は、使ったポケモンのワザの位置で表せないので、エンジンの未対応
        return UNSUPPORTED, "番をまたぐ効果を、効果を持つポケモンのカードのワザの位置で記録するので、相手のワザとして使った効果を表せない"

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("persistent_effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id,
                                persistent_effect=CannotUseOwnAttack.kind, effect=str(run.key), reason=E.EFFECT_TARGET_KNOCKED_OUT)
            return False
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        turn = run.state.turn_number
        index = run.key.attack_index
        effect = CannotUseOwnAttack(source_card=attacker.card, source_player=run.player, created_turn=turn,
                                    active_turn=turn + CannotUseOwnAttack.turns_until_active, attack_index=index, target_attack_index=index)
        add_persistent_effect(run.state, run.player, attacker, effect, attack=str(run.key), target_attack_index=index)
        return False


@dataclass(frozen=True)
class OpponentAttackLock(Element):
    """相手の対戦ポケモンのワザを 1 つ、ワザを使ったプレイヤーが選び（決定 ``SELECT_OPPONENT_ATTACK``）、次の相手の番、そのポケモンはそのワザを使えない
    （v0.35。カスミのニョロモの「ドわすれ」。持続する効果 ``CannotUseAttack``）。相手に与える効果なので、選ぶ前に「ワザをうけない」状態・「とうめい」を
    評価する（受けないなら選ばない。v0.31 の ``DiscardOpponentEnergy`` と同じ順番）。選べるものは、そのポケモンのいちばん上のカードのワザの位置。"""

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
        if not reaches(run.res, run.fs, opponent, target, E.ATTACK_LOCK_ELEMENT):
            return False
        attacks = run.state.card_def(target.card).attacks
        if not attacks:
            raise RuntimeError(f"ワザのない相手の対戦ポケモン {target.pokemon_id}（今の写しにはない。エンジンの不具合）")
        run.suspend(kind=SELECT_OPPONENT_ATTACK, player=run.player, options=tuple(range(len(attacks))), extra=(("target", target.pokemon_id),),
                    carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        opponent = 1 - run.player
        target = run.opponent_active()
        if target.pokemon_id != run.carried["target"] or choices[0] not in decision.options:
            raise RuntimeError(f"ドわすれの決定の答え {choices!r} が、相手の対戦ポケモンのワザではない（エンジンの不具合）")
        attacker = run.attacker()
        turn = run.state.turn_number
        effect = CannotUseAttack(source_card=attacker.card, source_player=run.player, created_turn=turn,
                                 active_turn=turn + CannotUseAttack.turns_until_active, attack_index=run.key.attack_index,
                                 target_attack_index=choices[0])
        add_persistent_effect(run.state, opponent, target, effect, attack=str(run.key), target_attack_index=choices[0])


@dataclass(frozen=True)
class OpponentReducedDamage(Element):
    """相手の対戦ポケモンを、このワザを使ったポケモン（「このカード」）にワザでダメージを与えるとき、与えるダメージが ``amount`` へる状態にする（v0.34。
    カラカラの「なきつく」。持続する効果 ``ReducedDamageToSource``。相手に与える効果なので「とうめい」・「ワザをうけない」状態を評価する）。"""

    amount: int
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
        effect = ReducedDamageToSource(source_card=attacker.card, source_player=run.player, created_turn=turn, active_turn=turn + 1,
                                       amount=self.amount)
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
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.RETREAT_LOCK_ELEMENT

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
        if not reaches(run.res, run.fs, opponent, target, E.RETREAT_LOCK_ELEMENT):
            return False
        attacker = run.attacker()
        turn = run.state.turn_number
        effect = CannotRetreat(source_card=attacker.card, source_player=run.player, created_turn=turn,
                               active_turn=turn + CannotRetreat.turns_until_active)
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
        promote_from_bench(run.state, run.player, choices[0], effect=str(run.key))


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
        for choice in choices:
            run.fs.results[self.name] = deal_damage(run.res, run.fs, E.OPPONENT_BENCH, self.base.value(run, None), pokemon_id=choice,
                                                    weakness_resistance=self.weakness_resistance)

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
    名前の一部・収録の弾では見ない。v0.40: ``SCOPE_BOTH_IN_PLAY`` なら、お互いの場（``player`` の場 → 相手の場の順。数だけを使う）。"""
    if scope not in (SCOPE_OWN_BENCH, SCOPE_OWN_IN_PLAY, SCOPE_BOTH_IN_PLAY):
        raise ValueError(f"数える範囲 {scope!r}")
    p = state.players[player]
    if scope == SCOPE_BOTH_IN_PLAY:
        pokemon = [*p.in_play(), *state.players[1 - player].in_play()]
    else:
        pokemon = list(p.bench) if scope == SCOPE_OWN_BENCH else list(p.in_play())
    return [x for x in pokemon if names is None or state.card_def(x.card).name_ja in names]


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
        return run.state.rules.max_bench - len(run.state.players[run.player].bench)

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

    max_hp: int
    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.ATTACK_LOCK_ELEMENT

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if E.max_hp(run.state, target) > self.max_hp:  # v0.48: 今有効な最大HP（受けるとき）
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
        """v0.48: 相手の対戦ポケモンが、このワザの中で HP 以上になっていれば処理の対象がない（コインを投げない）。こんじょうを使えるなら G37（``Status.has_target`` と同じ）。"""
        target = run.opponent_active()
        if target is None:
            return False
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        return True

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
        if not reaches(run.res, run.fs, opponent, target, E.RETURN_IN_PLAY_TO_DECK_ELEMENT):
            return False
        from .kernel import knocked

        gone = knocked(run.res)
        if gone:
            raise run.res.question("return_in_play_to_deck_with_knockout", f"ポケモン {[pokemon.pokemon_id for _, pokemon in gone]}")
        return_in_play_to_deck(state, opponent, target, effect=str(run.key))
        remove_persistent_effects(state, opponent, target, RETURN_IN_PLAY_TO_DECK)
        shuffle_in_attack(run, self, opponent)
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
    if before < hp <= pokemon.damage:
        run.res.ko_prevention_able[pokemon.pokemon_id] = False


def _counter_transfer_protected(run: AttackRun, target: PokemonInPlay, detail: str) -> None:
    """相手の対戦ポケモンが、ダメージカウンターをのせる・取り替える効果を受けない（「ワザをうけない」状態。v0.31 のバリアー）なら、自分の側の処理をするかが
    決まらない（CX1）。「とうめい」は ``reaches`` で効果を受けるときに評価し、受けなければ同じ問いにする（呼ぶ側）。"""
    from .kernel import first_void

    void = first_void(run.res, 1 - run.player, target, Window.BEFORE_EFFECT)
    if void is not None:
        raise run.res.question("counter_transfer_protected", f"ポケモン {target.pokemon_id}（{void.implementation.kind}。{detail}）")


@dataclass(frozen=True)
class HealCounters(Element):
    """ダメージカウンターをとりのぞく（回復。GR-2000-P320-RECOVERY「ダメージの回復は、かならず「ダメージカウンターをとりのぞく」ことによっておこなう。すべての
    ダメージカウンターをとりのぞいたら、それ以上の回復はできない」）（v0.41）。

    - ``scope``: 対象。``HEAL_SELF``（ワザを使ったポケモン）・``HEAL_OWN_ALL``（自分の場のポケモン全員: バトル場 → ベンチの順）・``HEAL_BOTH_ALL``（ワザを使った
      プレイヤーの場 → 相手の場の順に、それぞれバトル場 → ベンチ）。どの順でも、とりのぞく数は変わらない（ポケモンごとに決まる）。順番はログの並びだけ
    - とりのぞく数: ``counters``（決まった数）か ``heads_of``（ワザ全体のコインの「おもて」の数。どのポケモンにも同じ数。ポケモンごとに投げ直さない）。それぞれ
      のっている数まで。0 個のポケモンからはとりのぞかない（効果を受けない。p.309）
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
    phase: ClassVar[Phase] = Phase.EFFECT

    def __post_init__(self) -> None:
        if (self.counters is None) == (self.heads_of is None):
            raise ValueError("とりのぞく数は counters か heads_of のどちらか一方で決める")
        if self.scope not in (E.HEAL_SELF, E.HEAL_OWN_ALL, E.HEAL_BOTH_ALL):
            raise ValueError(f"回復の対象 {self.scope!r} は未定義")

    @property
    def opponent_element(self) -> str | None:
        return E.HEAL_ELEMENT if self.scope == E.HEAL_BOTH_ALL else None

    def targets(self, run: AttackRun) -> list[tuple[int, PokemonInPlay]]:
        if self.scope == E.HEAL_SELF:
            return [(run.player, run.attacker())]
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
        count = self.counters if self.heads_of is None else run.heads(self.heads_of)
        per = state.rules.damage_per_counter
        for owner, pokemon in self.targets(run):
            if run.knocked_out(pokemon):
                continue
            removed = min(count, pokemon.damage // per)
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
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_SPECIAL_CONDITION

    @property
    def opponent_elements(self) -> tuple[str, ...]:
        return E.CHOSEN_CONDITIONS

    def coin_receiver(self) -> str | None:
        return "effect"

    def run(self, run: AttackRun) -> bool:
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
        problem = paralysis_problem(run.state, owner, target)
        if problem is not None:
            extra += (("unresolved_choices", (E.CHOSEN_CONDITIONS.index(PARALYSIS),)), ("unresolved_code", problem.code),
                      ("unresolved_reason", problem.message))
        run.suspend(kind=SELECT_SPECIAL_CONDITION, player=run.player, options=tuple(range(len(E.CHOSEN_CONDITIONS))), extra=extra, carry=True)
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
    """

    energy_type: EnergyType
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = ATTACH_FROM_DECK

    def candidates(self, run: AttackRun) -> list[int]:
        return E.deck_energy_candidates(run.state, run.player, self.energy_type)

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            raise RuntimeError(f"ワザ {run.key} を使ったポケモンが、山札からエネルギーをつける前に HP 以上（このワザにダメージの要素はない。エンジンの不具合）")
        candidates = self.candidates(run)
        if not candidates:
            self._none(run, attacker, "no_candidates")
            return False
        run.suspend(kind=ATTACH_FROM_DECK, player=run.player, options=candidates, min_choices=0, max_choices=1)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        attacker = run.attacker()
        if not choices:
            self._none(run, attacker, "declined")
            return
        card = choices[0]
        if card not in self.candidates(run):
            raise RuntimeError(f"つけるカード {choices} が、山札の「{self.energy_type.ja}」エネルギーカードではない（エンジンの不具合）")
        attach_from_deck(state, run.player, card, attacker)
        state.add_event("attach_energy_from_deck", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key), card=card)
        E.after_energy_attached(state, run.player, attacker, card)
        shuffle_in_attack(run, self, run.player)

    def _none(self, run: AttackRun, attacker: PokemonInPlay, reason: str) -> None:
        run.state.add_event("attach_energy_from_deck_none", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            energy_type=self.energy_type.value, reason=reason)
        shuffle_in_attack(run, self, run.player)


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
        return kind in (SEARCH_DECK, SELECT_POKEMON)

    def run(self, run: AttackRun) -> bool:
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        permitted = E.deck_evolution_permission_pairs(run.state, run.player)
        if permitted:
            # v0.44: トレーナー「サカキ」の許可だけで重ねられる組がある（GV1）。重ねられるかで選べるものが変わるので、決定を出す前に止める（v0.45 から停止コード
            # ``UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK``。v0.44 はコードのない問いで、自分の場のサカキのコイキングに許可があると内部エラーになっていた）
            raise run.res.question("evolution_permission_from_deck", f"山札の進化カードと場のポケモン {list(permitted)}")
        candidates = E.deck_evolution_candidates(run.state, run.player)
        if not candidates:
            run.state.add_event("evolve_from_deck_none", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key))
            shuffle_in_attack(run, self, run.player)
            return False
        blocked = tuple(card for card, targets in candidates.items()
                        if len(E.evolution_hp_problem_targets(run.state, card, targets)) == len(targets))
        # v0.43: 場に出たときに使える特殊能力を持つ進化カード（わるいカイリューの［てしたをよぶ］）を重ねると、ワザの最中に特殊能力を使う機会が来る（PW4）。
        # 選べるが選ぶと止める（``entry_power_choices``。答えのときに止める）
        entry = tuple(card for card in candidates if card not in blocked and E.applicable_entry_power(run.state, card, from_hand=False) is not None)
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
            run.suspend(kind=SELECT_POKEMON, player=run.player, options=targets, extra=extra)
            return
        card = decision.context_value("card")
        if card not in candidates or choices[0] not in candidates[card]:
            raise RuntimeError(f"つきのちからで重ねるポケモン {choices}（カード {card}）が、重ねられるポケモンではない（エンジンの不具合）")
        self._evolve(run, card, choices[0])

    def _evolve(self, run: AttackRun, card: int, pokemon_id: int) -> None:
        state = run.state
        owner, target = state.find_pokemon(pokemon_id)
        if target.damage >= E.evolution_hp(state, target, card):  # v0.48: 重ねたあとの最大HP
            raise RuntimeError(f"進化すると HP がダメージ以下になる組（カード {card}・ポケモン {pokemon_id}）を選んだ（選ぶと止める選択の漏れ。エンジンの不具合）")
        if reaches(run.res, run.fs, owner, target, E.EVOLVE_ELEMENT):
            place_evolution_card(state, owner, target, card, effect=str(run.key))
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
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        options = [p.pokemon_id for p in run.state.players[run.player].in_play()]
        run.suspend(kind=SELECT_POKEMON, player=run.player, options=options, min_choices=0, max_choices=len(options))
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
            return_in_play_to_hand(state, run.player, pokemon, effect=str(run.key))
            remove_persistent_effects(state, run.player, pokemon, RETURN_IN_PLAY_TO_HAND)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return combinations_answers(decision, range(1, decision.max_choices + 1))  # 0 匹は答えのときに止める（HC5）。もどす順は場の順


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
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SEARCH_DECK

    def run(self, run: AttackRun) -> bool:
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        candidates = E.deck_trainer_cards(run.state, run.player)
        if not candidates:
            run.state.add_event("reveal_from_deck_none", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key), category="trainer")
            shuffle_in_attack(run, self, run.player)
            return False
        run.suspend(kind=SEARCH_DECK, player=run.player, options=candidates, min_choices=0, max_choices=1)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        if choices:
            if choices[0] not in E.deck_trainer_cards(run.state, run.player):
                raise RuntimeError(f"おつかいで選んだカード {choices} が、山札のトレーナーカードではない（エンジンの不具合）")
            reveal_deck_to_hand(run.state, run.player, choices[0], effect=str(run.key))
        else:
            run.state.add_event("reveal_from_deck_declined", player=run.player, pokemon_id=run.fs.frame.source_pid, effect=str(run.key), category="trainer")
        shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        return card_id_answers(run.state, decision, (0, 1))


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
    phase: ClassVar[Phase] = Phase.EFFECT

    def has_target(self, run: AttackRun) -> bool:
        return not run.knocked_out(run.attacker())

    def run(self, run: AttackRun) -> bool:
        state = run.state
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.ko_prevention_conflict(attacker, run.player)
            return False
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        if not reaches(run.res, run.fs, run.player, attacker, E.RETURN_IN_PLAY_TO_HAND_ELEMENT):
            return False
        from .kernel import knocked

        gone = knocked(run.res)
        if gone:
            raise run.res.question("return_in_play_to_deck_with_knockout", f"手札にもどす。ポケモン {[p.pokemon_id for _, p in gone]}")
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
    """

    evolves_from: str
    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SEARCH_DECK

    def candidates(self, run: AttackRun) -> list[int]:
        return E.self_deck_evolution_cards(run.state, run.player, run.attacker(), evolves_from=self.evolves_from)

    def run(self, run: AttackRun) -> bool:
        state = run.state
        attacker = run.attacker()
        cards = [uid for uid in state.players[run.player].deck if state.card_def(uid).evolves_from == self.evolves_from]
        permitted = E.deck_evolution_permission_pairs(state, run.player, (attacker.pokemon_id,), cards)
        if permitted:
            raise run.res.question("evolution_permission_from_deck", f"山札の進化カードと場のポケモン {list(permitted)}")
        candidates = self.candidates(run)
        if not candidates:
            state.add_event("evolve_from_deck_none", player=run.player, pokemon_id=attacker.pokemon_id, effect=str(run.key))
            shuffle_in_attack(run, self, run.player)
            return False
        blocked = tuple(uid for uid in candidates if attacker.damage >= E.evolution_hp(state, attacker, uid))  # v0.48
        entry = tuple(uid for uid in candidates if uid not in blocked and E.applicable_entry_power(state, uid, from_hand=False) is not None)
        extra: tuple = ()
        if blocked:
            extra = (("unresolved_choices", blocked), ("unresolved_code", "UNRESOLVED_EVOLUTION_HP"), ("unresolved_reason", E.EVOLUTION_HP_REASON))
        if entry:
            extra += (("entry_power_choices", entry),)
        run.suspend(kind=SEARCH_DECK, player=run.player, options=candidates, min_choices=0, max_choices=1, extra=extra)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        attacker = run.attacker()
        if not choices:
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
            place_evolution_card(state, run.player, attacker, card, effect=str(run.key))
        shuffle_in_attack(run, self, run.player)

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        blocked = set(decision.context_value("unresolved_choices", ())) | set(decision.context_value("entry_power_choices", ()))
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

    def has_target(self, run: AttackRun) -> bool:
        return bool(run.state.players[1 - run.player].discard)

    def run(self, run: AttackRun) -> bool:
        if not self.has_target(run):
            return False
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
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
        return len(E.attached_basic_energy(run.state, run.attacker(), self.energy_type)) * self.per


@dataclass(frozen=True)
class HalfRemainingHp:
    """相手の対戦ポケモンの残りの HP の半分（ダメージカウンターの単位で切り上げ）（v0.45。ラッタの「いかりのまえば」。p.321 の 1 段階）。"""

    local_coins: ClassVar[int] = 0

    def value(self, run: AttackRun, flips: CoinFlips | None) -> int:
        return E.half_remaining_hp(run.state, run.opponent_active())


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
    """

    phase: ClassVar[Phase] = Phase.EFFECT
    opponent_element: ClassVar[str] = E.ENERGY_MOVE_ELEMENT

    def decides(self, kind: str) -> bool:
        return kind in (MOVE_OPPONENT_ENERGY, SELECT_POKEMON)

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        p = run.state.players[opponent]
        target = p.active
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if not p.bench:
            return False  # 「相手に控えがいない時、この効果はない」（はがさない）
        energies = E.opponent_active_basic_energy(run.state, run.player)
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
            if choices[0] not in E.opponent_active_basic_energy(state, run.player):
                raise RuntimeError(f"はがすカード {choices} が、相手の対戦ポケモンの基本エネルギーカードではない（エンジンの不具合）")
            run.suspend(kind=SELECT_POKEMON, player=run.player, options=[pokemon.pokemon_id for pokemon in p.bench],
                        extra=(("target", target.pokemon_id), ("energy", choices[0])), carry=True)
            return
        energy = run.carried["energy"]
        destination = next((pokemon for pokemon in p.bench if pokemon.pokemon_id == choices[0]), None)
        if energy not in target.energy or destination is None:
            raise RuntimeError(f"つけかえるカード {energy}・控えポケモン {choices} が正しくない（エンジンの不具合）")
        target.energy.remove(energy)
        base = {"player": opponent, "pokemon": target.card, "pokemon_id": target.pokemon_id, "energy": energy, "to_pokemon_id": destination.pokemon_id,
                "effect": str(run.key), "attacker": run.player, "attacker_pokemon_id": run.fs.frame.source_pid}
        if reaches(run.res, run.fs, opponent, destination, E.ENERGY_ATTACH_ELEMENT):
            destination.energy.append(energy)
            state.add_event("move_opponent_energy", **base, result="attached")
            E.after_energy_attached(state, opponent, destination, energy)
        else:
            p.discard.append(energy)  # 「とうめい」の「おもて」: はがしたカードは持ち主のトラッシュ（CR-TRANSPARENCY-ENERGY-BOMB と同じ読み方）
            state.add_event("move_opponent_energy", **base, result="evaded")

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
        return E.hand_basic_energy(run.state, run.player, self.energy_type)

    def has_target(self, run: AttackRun) -> bool:
        return bool(self._candidates(run)) and not run.knocked_out(run.attacker())

    def run(self, run: AttackRun) -> bool:
        if self.gate is not None and not run.coin_is(self.gate):
            return False
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.state.add_event("effect_skipped", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                                element="attach_from_hand", reason=E.EFFECT_TARGET_KNOCKED_OUT)
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
            attach_energy_from_hand(run.state, run.player, uid, attacker)
        run.state.add_event("attach_energy_from_hand", player=run.player, pokemon=attacker.card, pokemon_id=attacker.pokemon_id, effect=str(run.key),
                            cards=cards)
        for uid in cards:
            E.after_energy_attached(run.state, run.player, attacker, uid)

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
    phase: ClassVar[Phase] = Phase.EFFECT

    def decides(self, kind: str) -> bool:
        return kind in (SELECT_DECK_OWNER, SELECT_LOOK_COUNT, ARRANGE_DECK_TOP)

    def run(self, run: AttackRun) -> bool:
        run.suspend(kind=SELECT_DECK_OWNER, player=run.player, options=(run.player, 1 - run.player))
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        state = run.state
        if decision.kind == SELECT_DECK_OWNER:
            owner = choices[0]
            deck = state.players[owner].deck
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
            cards = tuple(deck[:count])
            state.add_event("look_at_deck_top", player=run.player, owner=owner, count=count, cards=cards, effect=str(run.key))
            if count == 1:
                state.add_event("arrange_deck_top", player=run.player, owner=owner, count=1, cards=cards, effect=str(run.key))
                return
            run.suspend(kind=ARRANGE_DECK_TOP, player=run.player, options=cards, min_choices=count, max_choices=count, extra=(("owner", owner),))
            return
        count = len(decision.options)
        if tuple(deck[:count]) != tuple(decision.options) or sorted(choices) != sorted(decision.options):
            raise RuntimeError(f"みらいよちの並べかえ {choices} が、見たカード {decision.options} の並べかえではない（エンジンの不具合）")
        deck[:count] = list(choices)
        state.add_event("arrange_deck_top", player=run.player, owner=owner, count=count, cards=tuple(choices), effect=str(run.key))

    def dry_choices(self, run: AttackRun, decision: PendingDecision) -> list[tuple[int, ...]]:
        if decision.kind == SELECT_LOOK_COUNT:
            return [(count,) for count in decision.options if count]  # 0 枚は答えのときに止める（GS1）
        return all_answers(decision)


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
    - 同じプレイヤー・同じ消える番の禁止が 2 つになることはない（1 番に使えるワザは 1 つ。起これば RuntimeError）
    """

    local_coin: CoinSide | None = None
    phase: ClassVar[Phase] = Phase.EFFECT

    def run(self, run: AttackRun) -> bool:
        if self.local_coin is not None and run.flip(1).results[0] is not self.local_coin:
            return False
        state = run.state
        opponent = 1 - run.player
        expires = state.turn_number + 1
        if any(lock.player == opponent and lock.expires_turn == expires for lock in state.trainer_locks):
            raise RuntimeError(f"プレイヤー {opponent} に、消える番 {expires} のトレーナーの使用の禁止がすでにある（エンジンの不具合）")
        lock = TrainerUseLock(player=opponent, source_player=run.player, source_card=run.attacker().card, effect=str(run.key),
                              created_turn=state.turn_number, expires_turn=expires)
        state.trainer_locks = state.trainer_locks + (lock,)
        state.add_event("trainer_lock_added", player=opponent, source_player=run.player, source_card=lock.source_card, effect=lock.effect,
                        expires_turn=expires)
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

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_COLOR
    opponent_element: ClassVar[str] = E.WEAKNESS_CHANGE_ELEMENT

    def run(self, run: AttackRun) -> bool:
        opponent = 1 - run.player
        target = run.opponent_active()
        if run.knocked_out(target):
            run.ko_prevention_conflict(target)
            return False
        if not reaches(run.res, run.fs, opponent, target, E.WEAKNESS_CHANGE_ELEMENT):
            return False
        if E.weakness_of(run.state, target) is None:
            raise run.res.question("change_absent_weakness_resistance", f"相手の対戦ポケモン {target.pokemon_id} に弱点がない")
        run.suspend(kind=SELECT_COLOR, player=run.player, options=E.NON_COLORLESS_CHOICES, extra=(("target", target.pokemon_id),), carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        target = run.opponent_active()
        if target is None or target.pokemon_id != run.carried.get("target"):
            raise RuntimeError(f"テクスチャー1の対象 {run.carried.get('target')} が相手のバトル場にいない（エンジンの不具合）")
        color = _color_choice(run, choices)
        turn = run.state.turn_number
        effect = WeaknessChange(source_card=run.attacker().card, source_player=run.player, created_turn=turn, active_turn=turn, color=color)
        replace_persistent_effect(run.state, 1 - run.player, target, effect, attack=str(run.key), color=color.value)


@dataclass(frozen=True)
class SelfResistanceColor(Element):
    """ワザを使ったポケモン自身の抵抗力の色を、ワザを使ったプレイヤーが選んだ無色以外の色に変える（v0.48。ポリゴンの「テクスチャー2」。持続する効果
    ``ResistanceChange``。数は変えない）。自分自身への持続する効果（v0.31 の ``SelfPersistent`` と同じく、「とうめい」は評価しない。ポリゴン・まねるワザを持つポケモンは
    「とうめい」を持たない）。今有効な抵抗力がない（相手のワザとして使ったポケモン）なら決まらない（PG1）。"""

    phase: ClassVar[Phase] = Phase.EFFECT
    decision_kind: ClassVar[str] = SELECT_COLOR

    def run(self, run: AttackRun) -> bool:
        attacker = run.attacker()
        if run.knocked_out(attacker):
            run.ko_prevention_conflict(attacker, run.player)
            return False
        if E.resistance_of(run.state, attacker)[0] is None:
            raise run.res.question("change_absent_weakness_resistance", f"ワザを使ったポケモン {attacker.pokemon_id} に抵抗力がない")
        run.suspend(kind=SELECT_COLOR, player=run.player, options=E.NON_COLORLESS_CHOICES, extra=(("target", attacker.pokemon_id),), carry=True)
        return True

    def resume(self, run: AttackRun, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        attacker = run.attacker()
        if attacker.pokemon_id != run.carried.get("target"):
            raise RuntimeError("テクスチャー2の対象がワザを使ったポケモンではない（エンジンの不具合）")
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
    E.ChooseOpponentPokemonDamage: lambda e: (ChosenOpponentPokemonDamage(Fixed(e.damage)),),
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
    E.DamageThenReduceDamageNextTurn: lambda e: (Damage(OPP, Printed()), SelfPersistent(DamageReduction.kind, amount=e.amount)),
    E.DiscardAttachedAndReturnSelfToDeck: lambda e: (ReturnSelfToDeck(local_coin=None, after_damage=None, discard_attached=True),),
    E.ReturnSelfToDeckThenSearchPokemon: lambda e: (
        ReturnSelfToDeck(local_coin=None, after_damage=None, shuffle=False), PromoteFromBench(), RevealPokemonFromDeck(e.excluded),
    ),
    # v0.39（docs/selfdestruct-spread-count-v0.39.md）。じばく・控えへのダメージ・場のポケモンの数でダメージが決まるワザ
    E.SelfDestruct: lambda e: (
        Damage(OPP, Printed()), Damage(SELF, Fixed(e.self_damage), name="self_damage"),
        BenchDamage(Fixed(e.bench_damage), weakness_resistance=False if e.weakness_resistance_stated else None),
        BenchDamage(Fixed(e.bench_damage), weakness_resistance=False if e.weakness_resistance_stated else None, own=True),
    ),
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
    E.DamageThenChosenStatusOnHeads: lambda e: (Damage(OPP, Printed()), ChosenStatus()),
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
    E.CoinChooseOpponentPokemonDamage: lambda e: (ChosenOpponentPokemonDamage(Fixed(e.damage), local_coin=HEADS),),
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
    E.DamageAndSelfDamagePerAttachedEnergyCard: lambda e: (
        Damage(OPP, Printed()), Damage(SELF, PerAttachedEnergyCards(e.energy_type, e.per_card), name="self_damage")),
    E.ZeroDamageBelowNextTurn: lambda e: (SelfPersistent(ZeroDamageBelow.kind, amount=e.threshold),),
    E.HalfRemainingHpDamage: lambda e: (Damage(OPP, HalfRemainingHp()),),
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
}


def compile_attack(effect: E.AttackEffect) -> tuple[Element, ...]:
    """v0.13 のワザの実装から要素の並びを作る（部分型は使わない。実装の型が完全に一致するものだけ）。"""
    builder = BUILDERS.get(type(effect))
    if builder is None:
        raise UnsupportedByKernel(f"ワザの実装 {type(effect).__name__}（{effect.implementation_id}）はプロトタイプの対応表にない")
    return builder(effect)

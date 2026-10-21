"""解決の核: 処理の枠・ダメージの要素の窓・送る効果・きぜつの原因（docs/event-model-v0.14.md 3 章・4 章）。

v0.13 の ``deal_attack_damage``・``attack_reaches``・``finish_damage_elements``・``_apply_counterattack``・``_apply_retaliation``・
``_ko_prevention_offer``・``_post_knockout_candidates`` が、それぞれ効果の種類を直接探していた処理を、次の共通の処理に置きかえます。

- 窓ごとに、場のポケモンの効果（``catalog``）から候補を集める（効果の種類で分岐しない。定義の項目で判定する）。
- 「ダメージを受けたとき」の効果は、受けた枠の送る効果の列に入れ、その枠の「ダメージの要素のあと」の窓で処理する（p.89）。
  窓を開く位置は、ワザの要素の分類から ``run_elements`` が決める（ワザの実装が呼ぶ必要がない）。
- 枠は、どの枠がどの枠を起こせるかの表（``events.SPAWNS``）で起こし、表にない連鎖は止める。
- ポケモンのダメージが HP 以上になった枠を記録し、きぜつの判定で、原因の枠が分かれていれば「同時のきぜつ」が決まらない
  場合（C18・W24・S37）として止める（効果の組み合わせごとの関数を書かない）。

状態を変える部品（ダメージの計算・コイン・特殊状態・持続する効果・ログ）は v0.13 のものをそのまま使い、ログの形と順番・乱数の
使い方は v0.13 と同じにします。
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from ..coins import CoinSide, flip_coins
from ..damage import ADD, HALVE_DOWN, HALVE_UP, MULTIPLY, SET, SET_IF_AT_LEAST, ZERO_IF_AT_LEAST, ZERO_IF_BELOW, DamageOrderRequired, DamageReductionRequired
from ..effects import (
    knocked_by_hp,
    calculate_with_stadium,
    stadium_coin_modifier,
    ATTACK_ELEMENTS,
    BENCH_TARGETS,
    COUNTERATTACK_TARGET_KNOCKED_OUT,
    DAMAGE_ELEMENT,
    OPPONENT_ACTIVE,
    OPPONENT_BENCH,
    RETALIATION_COIN_TAILS,
    RETALIATION_TARGET_KNOCKED_OUT,
    SELF,
    SELF_BENCH,
    AttackKey,
    DamageResult,
    EXCLUDE_DEFENDER_HELD,
    EXCLUDE_DEFENDER_SIDE,
    attack_damage_modifiers,
    counterattack_double_knockout_error,
    power_name_and_page,
    received_modifiers_log,
    received_power_damage,
    retaliation_double_knockout_error,
    TypeReadingsDiffer,
    definition_views,
    max_hp,
    resistance_of,
    same_for_type_readings,
    type_readings,
    weakness_of,
)
from ..conditions import confuse
from ..decisions import KNOCK_OUT_POWER, KO_PREVENTION, REACTION_SWITCH
from ..persistent import RETURN_IN_PLAY_TO_DECK, effect_attack_card, expires_at_turn_start, reduced_damage_to_source, remove_on_damage, remove_persistent_effects, tails_damage_guard
from ..zones import designate_face_down, return_in_play_to_deck, shuffle_deck
from ..errors import UnsupportedError
from .. import effects as E
from ..state import RETALIATION_FIXED
from ..history import VOID_ATTACK_BARRIER, VOID_DAMAGE_ONLY, VOID_DODGED, VOID_EFFECT_ONLY, VOID_EVADED, VOID_FLED, VOID_IMMUNE, note_received

from . import catalog as C
from .events import (
    DamageClass,
    SPAWN_REFUSALS,
    SPAWNS,
    Activated,
    CandidateFound,
    DamageApplied,
    DamageEvaded,
    DamageProposal,
    DamageVoided,
    Frame,
    FrameKind,
    FrameOpened,
    FrameState,
    KnockedOutRecorded,
    QuestionHit,
    Trace,
    Window,
    WindowOpened,
)
from .questions import OpenQuestion

if TYPE_CHECKING:
    from ..state import GameState, PokemonInPlay


class DryRunComplete(Exception):
    """先読みで、ワザの要素ときぜつの判定までを処理し終えた（決定は出さない）。"""


@dataclass(frozen=True)
class Deferred:
    """「ダメージを受けたとき」に候補になり、ダメージの要素のあとの窓で処理する効果（受けた枠の列に入る）。"""

    instance: C.EffectInstance
    frame: int  # ダメージを受けた枠
    received: int  # 受けたダメージ（最終ダメージ。HP で上限をつけない。こうらがえしの「同じダメージ」）


class Resolution:
    """1 つのコマンドの解決（状態に保存しない値）。

    - ``frames``: 開いた枠（id → ``FrameState``）
    - ``ko_prevention_able``: 「ダメージを受けるとき」の特殊状態の写し（こんじょう。v0.13 の ``AttackUse.ko_prevention_able``。返す効果の
      枠とも共有する）
    - ``knocked_by``: ダメージが HP 以上になった枠（場のポケモンの番号 → 枠の id）
    - ``dry_run``: 先読み（``preflight``）の中か。決定を出さず、``oracle`` が選ぶ
    - ``on_horizon``: 実際の処理が先読みの範囲（宣言からきぜつの判定まで）の終わりに来たら呼ぶ（v0.15c の ``preflight.after_real_run``）
    """

    def __init__(self, state: GameState, *, catalog: C.Catalog = C.DEFAULT_CATALOG, trace: Trace | None = None,
                 dry_run: bool = False, oracle: Any = None, on_horizon: Callable[[], None] | None = None,
                 dormant: frozenset[int] | None = None):
        self.state = state
        self.on_horizon = on_horizon
        self.catalog = catalog
        self.trace = trace if trace is not None else Trace()
        self.dry_run = dry_run
        self.oracle = oracle
        self.frames: dict[int, FrameState] = {}
        self.next_frame = 1
        self.ko_prevention_able: dict[int, bool] = {}
        self.knocked_by: dict[int, int] = {}
        # v0.31: ダメージによらず「きぜつ」するポケモン（「みちづれ」で、相手の対戦ポケモンも「きぜつ」する。場のポケモンの番号）。きぜつの判定・
        # 処理は、HP 以上のダメージのポケモンといっしょに扱う（``knocked``）
        self.forced: set[int] = set()
        # v0.46: ワザが使われた時（宣言）に「ねむり・マヒ・こんらん」状態だった、その時点の特殊状態で決める常にはたらく特殊能力（エリカのフシギソウの
        # ［くつろぐかおり］）を持つ場のポケモンの番号（``effects.status_at_attack_blocked``）。ワザの宣言で写し（``flow._attack_body``）、決定をまたぐときは
        # 続きの情報で運ぶ（``AttackRun.suspend``）。ワザの外（None）では今の特殊状態で決める
        self.attack_status: frozenset[int] | None = None
        # v0.56: このワザの中で、トレーナー「キョウ」の効果でどく状態にした場のポケモンの番号（KG1。``kernel.trainer_poison_after_damage``・``programs.Status``）
        self.trainer_poisoned: set[int] = set()
        # v0.57: このワザでクチバシティジムのコインを投げた結果（(スタジアムカード, 「おもて」か)。投げていなければ None）。ワザの宣言のあとに投げ（``flow._attack_body``）、
        # 決定をまたぐときは続きの情報の ``stadium_coin`` で運ぶ（投げ直さない）。「おもて」なら相手の対戦ポケモンへのダメージの要素に 6 段階の +10（``deal_damage``）
        self.stadium_coin: tuple[int, bool] | None = None
        # v0.61: ［ずらかる］（``effects.ReturnToDeckAtRemainingHp``）。``dormant`` はコマンドの始めに、残りHPが「10」で力が消えていた場のポケモンの番号（SC2 の比べのもと。
        # 渡さなければ、この解決を作った時点の状態から求める。コマンドの途中で作る解決（特殊能力・トレーナー・にげるのあと）は、コマンドの入口の状態から求めて渡す）。
        # ``scram_touched`` は、この解決のダメージで、力がはたらいたまま残りHPが「10」になった場のポケモンの番号（ダメージの処理のまとまりの途中で「10」を通ったか。SC1）
        self.dormant: frozenset[int] = E.dormant_scram(state) if dormant is None else dormant
        self.scram_touched: set[int] = set()
        # v0.61: 決定をまたいで運んだ、HP 以上になった場のポケモンのきぜつの原因（番号 → (原因の枠のプレイヤー, ダメージを与えたポケモン, ワザの分類か)）。決定の前の
        # ``knocked_by`` の枠は残らないので、［ファイナルビーム］の候補はこれで求める（``AttackRun.suspend``・``restore``）
        self.ko_carried: dict[int, tuple[int, int, bool]] = {}
        # v0.62（docs/history-attacks-v0.62.md 2 章）: このワザの宣言したワザ（``AttackKey``。ワザの外では None）。受けた記録（``history.note_received``）の B に書く
        # （処理したワザは枠の ``attack_key``）。``flow._attack_body``・``_resume_attack`` が置く
        self.attack_declared: AttackKey | None = None
        # v0.65（docs/reactive-decisions-v0.65.md 4 章）: ［にげこむ］の候補（(持ち主, ポケモンの番号, カード id, 特殊能力の位置, 自分のワザの中の返す効果のダメージか)。``receiving`` が
        # ダメージを受けるときの特殊状態で加え、``programs.offer_flee`` がダメージの要素のあとに聞く）と、使って入れ替えたポケモン（もとのポケモンの番号 → かわりに出たポケモンの
        # 番号。このワザの残りのダメージ以外の効果をどちらにも与えない。``reaches``）。決定をまたぐときは続きの情報で運ぶ（``AttackRun.suspend``）
        self.flee_offers: list[tuple[int, int, str, int, int]] = []
        self.fled: dict[int, int] = {}
        # v0.67（docs/secret-plan-preflight-v0.67.md 4 章）: このワザの要素が対象にして、おもてにしたら「たねポケモン」でなくトラッシュした、うらのカードの場のポケモン（番号 →
        # (持ち主, 場をはなれた場のポケモン)）。このワザの残りの要素では対象がいない（ダメージ・効果を与えない。効果を決めるコインも投げない）。決定をまたぐときは続きの情報で運ぶ
        self.secret_lost: dict[int, tuple[int, PokemonInPlay, bool]] = {}  # 番号 → (持ち主, 場をはなれた場のポケモン, バトル場にいたか)
        # v0.81（docs/pokemon-tools-stadiums-v0.81.md 5 章）: ワザの分類の枠（ワザ・返す効果）のダメージ（``deal_damage``）で HP 以上になった場のポケモン（番号 → (原因の枠の
        # プレイヤー, ダメージを与えたポケモン)）。ダメージカウンターの移動・こんらん・特殊能力のダメージでは記録しない。きあいのハチマキ・学習装置の候補（きぜつの判定の窓）と、
        # きあいのハチマキの処理の時点の問い（FB1）に使う。決定をまたぐときは続きの情報で運ぶ（``AttackRun.suspend``）
        self.damage_ko: dict[int, tuple[int, int]] = {}

    def open_frame(self, kind: FrameKind, *, parent: int | None, player: int, source_pid: int, attack_key: AttackKey) -> FrameState:
        if parent is not None:
            parent_kind = self.frames[parent].frame.kind
            if kind not in SPAWNS[parent_kind]:
                # 規定から起こらないはずの連鎖（返すダメージで返す効果など。v0.13 の S45）。回数の上限ではなく表で止める
                reason = SPAWN_REFUSALS.get((parent_kind, kind))
                raise RuntimeError(
                    f"枠 {parent_kind.value} から枠 {kind.value} は起こらないはず（events.SPAWNS。{reason + '。' if reason else ''}エンジンの不具合）"
                )
        frame = Frame(self.next_frame, kind, parent, player, source_pid, attack_key)
        self.next_frame += 1
        state = FrameState(frame)
        self.frames[frame.id] = state
        self.trace.record(FrameOpened(frame))
        return state

    def ancestors(self, frame_id: int) -> list[Frame]:
        out = []
        current: int | None = frame_id
        while current is not None:
            frame = self.frames[current].frame
            out.append(frame)
            current = frame.parent
        return out

    def horizon(self) -> None:
        """先読みの範囲の終わり（きぜつの判定の窓の候補を求めたあと。先読みはここで ``DryRunComplete``）。実際の処理だけが呼ぶ。"""
        if self.on_horizon is not None:
            self.on_horizon()

    def question(self, key: str, detail: str = "", error=None) -> OpenQuestion:
        self.trace.record(QuestionHit(key, detail))
        return OpenQuestion(key, detail, error)


def hp_of(state: GameState, pokemon: PokemonInPlay) -> int:
    """v0.48: 今有効な最大HP（``effects.max_hp``。カードの定義の HP に、きょだいか・［ガスのからだ］を当てはめた値）。"""
    return max_hp(state, pokemon)


def type_question(res: Resolution, error: TypeReadingsDiffer, what: str) -> OpenQuestion:
    """v0.48: 色の読み方（VS1。``effects.type_readings``）で結果が変わった。問い ``shift_color_duration`` で止める（先読みが集め、宣言の前に止まる）。"""
    return res.question("shift_color_duration", f"{what}（ポケモン {[p.pokemon_id for p in error.pokemons]}）")


def track_ko(res: Resolution, fs: FrameState, pokemon: PokemonInPlay, before: int) -> None:
    """ダメージで HP 以上になったら、その枠を記録する（きぜつの原因。4 章）。v0.61: 力がはたらいている［ずらかる］のポケモンの残りHPが「10」になったら、それも記録する
    （``note_scram``。ダメージの処理のまとまりの途中で「10」を通ったかを ``settle_scram`` が見る）。"""
    hp = hp_of(res.state, pokemon)
    if before < hp <= pokemon.damage:
        res.knocked_by[pokemon.pokemon_id] = fs.frame.id
        res.trace.record(KnockedOutRecorded(pokemon.pokemon_id, fs.frame.id))
    note_scram(res, pokemon)


def note_damage_ko(res: Resolution, fs: FrameState, pokemon: PokemonInPlay, before: int) -> None:
    """v0.81: ワザの分類の枠のダメージで ``pokemon`` が HP 以上になったら、その原因（枠のプレイヤー・ダメージを与えたポケモン）を記録する（``res.damage_ko``）。"""
    if fs.frame.damage_class is DamageClass.ATTACK and before < hp_of(res.state, pokemon) <= pokemon.damage:
        res.damage_ko[pokemon.pokemon_id] = (fs.frame.player, fs.frame.source_pid)


def focus_band_of(res: Resolution, pokemon: PokemonInPlay):
    """v0.81: ``pokemon`` が相手のワザの分類のダメージで HP 以上になり（``res.damage_ko``）、きあいのハチマキ（``effects.FocusBand``）がついているなら (ついているカード, 実装)。
    なければ None。"""
    cause = res.damage_ko.get(pokemon.pokemon_id)
    located = res.state.find_pokemon(pokemon.pokemon_id)
    if cause is None or located is None or cause[0] == located[0]:
        return None
    return E.tool_effect_of(res.state, pokemon, E.FocusBand)


def focus_band_timing(res: Resolution, pokemon: PokemonInPlay, what: str) -> None:
    """v0.81（FB1）: きあいのハチマキのコインを残りHPがなくなったすぐあとに投げるか、きぜつの判定の時に投げるかで結果が変わる場面（HP 以上になったあとに、同じワザの処理が
    このポケモンにダメージ・効果を与える・与えないを決める）なら止める。"""
    if focus_band_of(res, pokemon) is not None:
        raise res.question("focus_band_timing", f"ポケモン {pokemon.pokemon_id}・{what}")


# ---------------------------------------------------------------- ［ずらかる］（v0.61。docs/reactive-powers-trainer-damage-v0.61.md 4 章）


def note_scram(res: Resolution, pokemon: PokemonInPlay) -> None:
    """ダメージ・ダメージカウンターでのっている数が変わった ``pokemon`` が、力がはたらいている［ずらかる］を持ち、残りHPがちょうど「10」なら記録する（v0.61）。"""
    state = res.state
    for slot in E.powers_of(state, pokemon):
        if isinstance(slot.effect, E.ReturnToDeckAtRemainingHp) and E.scram_due(state, pokemon, slot) and E.scram_working(state, pokemon, slot):
            res.scram_touched.add(pokemon.pokemon_id)


def settle_scram(res: Resolution, *, rest: tuple | None = None) -> list[int]:
    """［ずらかる］を確かめる決まった時点（v0.61）: 残りHPがちょうど「10」で力がはたらいている場のポケモンを、山札にもどす（``fire_scram``）。もどした番号を返す。

    呼ぶ時点: ワザの処理のダメージの要素のまとまりのあと・ダメージ以外の要素のあと（``programs.run_elements``）・きぜつの判定の窓の始め（``flow._finish_attack``）・
    ［ファイナルビーム］のダメージのあと・特殊能力・エネルギー・トレーナー・にげる・ポケモンチェックのどくのあと。

    - 決まった時点のあいだに残りHPが「10」を通って変わった（「10」になったあと、同じまとまりでさらにダメージを受けた）なら、はたらく時点で結果が変わるので SC1
    - コマンドの始めに残りHPが「10」で力が消えていて、今もどった（``res.dormant``）なら SC2
    - ワザの途中（``rest`` がワザの残りの要素）なら、残りの要素がどれもポケモンによらないもの（``independent_of_pokemon``。スタジアムのトラッシュ）でなければ SC1。2 匹以上が
      同時にもどるなら、山札を切る順番が決まらないので SC1
    """
    state = res.state
    touched, res.scram_touched = res.scram_touched, set()
    due = []
    for owner, pokemon, slot in E.scram_slots(state):
        if not E.scram_due(state, pokemon, slot):
            if pokemon.pokemon_id in touched:
                raise res.question("scram_timing", f"ポケモン {pokemon.pokemon_id} の残りHPが「10」を通って変わった")
            continue
        if not E.scram_working(state, pokemon, slot):
            continue
        if pokemon.pokemon_id in res.dormant:
            raise res.question("scram_power_restored", f"ポケモン {pokemon.pokemon_id}")
        due.append((owner, pokemon, slot))
    if not due:
        return []
    if len(due) > 1:
        raise res.question("scram_timing", f"ポケモン {[p.pokemon_id for _, p, _ in due]} が同時にもどる")
    if rest and not all(getattr(element, "independent_of_pokemon", False) for element in rest):
        raise res.question("scram_timing", f"ポケモン {due[0][1].pokemon_id}・ワザの残りの要素 {[type(e).__name__ for e in rest]}")
    for owner, pokemon, slot in due:
        fire_scram(res, owner, pokemon, slot)
    return [pokemon.pokemon_id for _, pokemon, _ in due]


def fire_scram(res: Resolution, owner: int, pokemon: PokemonInPlay, slot) -> None:
    """［ずらかる］がはたらく（v0.61）: ログ ``scram`` → 場のポケモンを山札にもどす（``zones.return_in_play_to_deck``。出どころ ``power``）→ 持続する効果を消す → 山札を切る
    （先読みでは切らない）。きぜつではない。"""
    state = res.state
    key = str(slot.key)
    res.trace.record(Activated(Window.KO_CHECK, "scram", pokemon.pokemon_id, None))
    state.add_event("scram", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, power=key, remaining_hp=slot.effect.remaining_hp)
    return_in_play_to_deck(state, owner, pokemon, power=key)
    remove_persistent_effects(state, owner, pokemon, RETURN_IN_PLAY_TO_DECK)
    if not res.dry_run:
        shuffle_deck(state, owner, power=key)


def scram_restored_question(res: Resolution, gone) -> None:
    """きぜつの処理でかがくへんかガスの発生源が場をはなれると、残りHPが「10」で力が消えていた［ずらかる］の力がもどるなら SC2（v0.61。きぜつの判定の窓で、きぜつの処理の
    前に確かめる。先読みの範囲の中）。"""
    state = res.state
    gone_ids = {pokemon.pokemon_id for _, pokemon in gone}
    from ..continuous import goop_gas_effects, suppressors_of

    if goop_gas_effects(state):
        return  # まきちらせ!ベトベトガスはきぜつで消えない
    for _, pokemon, slot in E.scram_slots(state):
        if pokemon.pokemon_id in gone_ids or not E.scram_due(state, pokemon, slot) or E.scram_working(state, pokemon, slot):
            continue
        if not slot.effect.is_able(pokemon):
            continue
        sources = suppressors_of(state, slot.power)
        if sources and all(pid in gone_ids for pid in sources):
            raise res.question("scram_power_restored", f"ポケモン {pokemon.pokemon_id}（かがくへんかガスのポケモン {list(sources)} がきぜつする）")


# ---------------------------------------------------------------- ダメージの要素（窓: 適用の前 → 受けるとき → 適用 → 受けたとき）


def first_void(res: Resolution, owner: int, pokemon: PokemonInPlay, window: Window = Window.BEFORE_DAMAGE, *,
               held_by_receiver: bool = True) -> C.EffectInstance | None:
    """受けるポケモンのダメージの要素を無効にする効果（「ダメージを受けない」状態。かたまる）のうち、今はたらいているもの。v0.31: ``window`` に
    ``Window.BEFORE_EFFECT`` を渡すと、効果の要素を無効にする効果（「ワザをうけない」状態。バリアー）。

    v0.60: ``held_by_receiver`` が False なら、受けるポケモン自身が持っている効果（持続する効果・特殊能力）は除く（タケシのサンドパンの「スピードスター」。トレーナーの
    効果（見えない壁。プレイヤーの記録）は受けるポケモンの持っている効果ではないので残す）。"""
    for instance in C.in_window(res.state, window, owner, pokemon, res.catalog):
        if not held_by_receiver and instance.definition.origin is not C.Origin.TRAINER_EFFECT and instance.pokemon_id == pokemon.pokemon_id:
            continue
        if instance.definition.by_opponent and instance.definition.timing is C.Timing.VOID and owner == res.state.current_player:
            continue  # v0.80: 「相手のワザによる」（エフェクトガード）。受けるポケモンの持ち主のワザ（自分のワザの自分への効果）には当てはめない
        if instance.definition.timing is C.Timing.VOID and C.working(res.state, instance, pokemon):
            return instance
    return None


def note_receipt(res: Resolution, fs: FrameState, owner: int, pokemon: PokemonInPlay, **what) -> None:
    """v0.62: 相手のワザの要素が ``pokemon`` を対象にしたことを、受けた記録（``history.note_received``）に加える。ワザの枠（``FrameKind.ATTACK``）だけ（こんらんの枠・
    返す効果の枠は記録しない）。"""
    frame = fs.frame
    if frame.kind is not FrameKind.ATTACK or res.attack_declared is None:
        return
    note_received(res.state, attacker_player=frame.player, source=frame.source_pid, declared=res.attack_declared, processed=frame.attack_key,
                  owner=owner, pokemon=pokemon, **what)


def _void_reason(res: Resolution, owner: int, pokemon: PokemonInPlay) -> str:
    """v0.62: ダメージの要素を無効にした効果が、効果の要素も無効にする効果（「ワザをうけない」）か、ダメージだけを無効にする効果か。"""
    # v0.80: ダメージの要素を無効にした効果そのものが、効果の要素も無効にするか（エフェクトガードは効果の要素だけを無効にするので、「ダメージを受けない」状態と重なっても
    # ダメージだけの無効のまま）
    void = first_void(res, owner, pokemon)
    return VOID_ATTACK_BARRIER if void is not None and Window.BEFORE_EFFECT in void.definition.windows else VOID_DAMAGE_ONLY


def lost_pokemon(res: Resolution, owner: int, pokemon_id: int | None = None) -> PokemonInPlay | None:
    """v0.67: このワザで、おもてにしてトラッシュした持ち主 ``owner`` のうらのカードの場のポケモン（``pokemon_id`` を省けば、持ち主のバトル場にいたもの）。なければ None。"""
    for pid, (side, pokemon, was_active) in res.secret_lost.items():
        if side == owner and (pid == pokemon_id or (pokemon_id is None and was_active)):
            return pokemon
    return None


def designate(res: Resolution, fs: FrameState, owner: int, pokemon: PokemonInPlay, cause: str) -> PokemonInPlay | None:
    """v0.67: ワザの要素がダメージ・効果を与える場のポケモン ``pokemon`` がうらのカード（マチスの秘策）なら、その前におもてにする（``zones.designate_face_down``）。
    本当のカードが「たねポケモン」なら同じポケモンを返し、そうでなければトラッシュして ``res.secret_lost`` に加え None を返す（このワザの残りの要素では対象がいない）。
    うらでなければそのまま返す。"""
    if pokemon.pokemon_id in res.secret_lost:
        return None
    state = res.state
    if not state.is_face_down(pokemon):
        return pokemon
    was_active = state.players[owner].active is pokemon
    revealed = designate_face_down(state, owner, pokemon, by_player=fs.frame.player, cause=cause, can_lose=True)
    if revealed is None:
        res.secret_lost[pokemon.pokemon_id] = (owner, pokemon, was_active)
    return revealed


def receiver_of(res: Resolution, fs: FrameState, target: str, pokemon_id: int | None = None) -> tuple[int, PokemonInPlay]:
    state = res.state
    if target == OPPONENT_ACTIVE:
        active = state.players[1 - fs.frame.player].active
        if active is None and res.secret_lost:
            active = lost_pokemon(res, 1 - fs.frame.player)  # v0.67: おもてにしてトラッシュしたバトル場のうらのカード（対象がいない）
        return 1 - fs.frame.player, active
    if target == SELF:
        return fs.frame.player, state.find_pokemon(fs.frame.source_pid)[1]
    if target in (OPPONENT_BENCH, SELF_BENCH):
        # v0.31: 相手の控えポケモン（ワザの説明が選ばせる・決める場のポケモンの番号）。v0.33: 自分の控えポケモン（タケシのディグダの「ミニじしん」）
        side = 1 - fs.frame.player if target == OPPONENT_BENCH else fs.frame.player
        found = next((p for p in state.players[side].bench if p.pokemon_id == pokemon_id), None)
        if found is None and pokemon_id in res.secret_lost:
            found = res.secret_lost[pokemon_id][1]  # v0.67: おもてにしてトラッシュした控えのうらのカード（対象がいない）
        if found is None:
            raise RuntimeError(f"ダメージを受ける{'相手' if target == OPPONENT_BENCH else '自分'}の控えポケモン {pokemon_id!r} がいない（エンジンの不具合）")
        return side, found
    raise ValueError(f"ダメージを受けるポケモンの種類 {target!r} は未対応")


def weakness_resistance_matters(res: Resolution, fs: FrameState, target: str, base: int, pokemon_id: int) -> bool:
    """控えポケモン（``target`` は ``OPPONENT_BENCH``・``SELF_BENCH``）へのダメージで、弱点・抵抗力を計算するかどうかで最終ダメージが変わるか（v0.37。
    説明に「「弱点・抵抗力」に関係なく」のない控えへのダメージ。JS1）。状態を変えず、``deal_damage`` と同じ変更効果（``attack_damage_modifiers``）と
    計算（``calculate_attack_damage``）で 2 とおりを比べる。ダメージの要素が無効になる（「ワザをうけない」・「ダメージを受けない」）ポケモンは、どちらの
    読み方でも計算しないので変わらない。同じ段階の順番が要る計算は、``deal_damage`` が今までどおり止める（ここでは比べない）。"""
    state = res.state
    _, attacker = state.find_pokemon(fs.frame.source_pid)
    receiver_player, receiver = receiver_of(res, fs, target, pokemon_id)
    if first_void(res, receiver_player, receiver) is not None:
        return False
    modifiers = attack_damage_modifiers(state, attacker, receiver, attack=fs.frame.attack_key, bench=True, attack_status=res.attack_status)
    # v0.48: 今有効な値の定義（``effects.definition_views``）で比べる。色の読み方（VS1）が 2 つあれば、どの読み方でも弱点・抵抗力の計算で変わるかを見る（読み方で
    # 結果が変わることは、ダメージを与えるとき ``deal_damage`` が止める）
    try:
        for attacker_def in definition_views(state, attacker):
            for receiver_def in definition_views(state, receiver):
                finals = {calculate_with_stadium(state, base, attacker_def, receiver_def, modifiers, weakness_resistance=flag).final
                          for flag in (True, False)}
                if len(finals) > 1:
                    return True
    except (DamageOrderRequired, DamageReductionRequired):
        return False
    return False


def attack_modifiers_of(res: Resolution, frame, attacker: PokemonInPlay, receiver: PokemonInPlay, target: str, *, defender_effects: bool = True) -> list:
    """ワザの分類のダメージの要素 1 つの、場の変更効果（p.321 の 2・5〜8 段階。クチバシティジムのコインを除く）（v0.64。``deal_damage`` から分けた。先読みの
    「うら」が出るまで投げるコインの組（``resolution.unbounded``）が同じ関数を使う）。状態を変えず、乱数を使わない。"""
    exclude = None if defender_effects else EXCLUDE_DEFENDER_HELD
    return list(attack_damage_modifiers(res.state, attacker, receiver, attack=frame.attack_key, bench=target in BENCH_TARGETS,
                                        attack_status=res.attack_status, exclude=exclude))


def with_stadium_coin(res: Resolution, frame, target: str, modifiers: list) -> list:
    """v0.57: クチバシティジムの「おもて」（そのワザによって相手の対戦ポケモンに与えるダメージは「+10」。p.321 の 6 段階。控えへのダメージ・返す効果のダメージは
    そのまま）を加えた変更効果（v0.64。``deal_damage`` から分けた）。"""
    if res.stadium_coin is not None and res.stadium_coin[1] and target == OPPONENT_ACTIVE and frame.kind is FrameKind.ATTACK:
        return [*modifiers, stadium_coin_modifier(res.state, res.stadium_coin[0])]
    return modifiers


def compute_damage(state: GameState, attacker: PokemonInPlay, receiver: PokemonInPlay, base: int, modifiers, *, weakness_resistance: bool = True,
                   orders=None, resistance: bool = True, reduction: int | None = None):
    """p.321 の計算（v0.64。``deal_damage`` から分けた）。v0.48: ワザを使うポケモン・受けるポケモンの今有効な最大HP・タイプ（色）・弱点・抵抗力
    （``effects.definition_views``）。色の読み方（VS1）が 2 つあり、読み方で計算の結果が変わるなら ``TypeReadingsDiffer``（変わらなければ、読み方が 1 つのときと
    同じ計算）。順番の決定が要れば ``DamageOrderRequired``。状態を変えず、乱数を使わない。v0.81: ワザを使うポケモンにピントレンズがついていて、受けるのが相手の対戦ポケモンなら
    抵抗力を計算しない（``effects.attack_ignores_resistance``）。"""
    if resistance and E.attack_ignores_resistance(state, attacker, receiver) is not None:
        resistance = False
    return same_for_type_readings(state, (attacker, receiver), lambda views: calculate_with_stadium(state,
        base, views[0], views[1], modifiers, weakness_resistance=weakness_resistance, orders=orders, resistance=resistance, reduction=reduction))


class BenchGuardRequest(Exception):
    """v0.65: 控えポケモンが受けるダメージを計算したあと・のせる前に、［ベンチガード］を使うかを聞く決定が要る（``deal_damage`` の ``guard_suspend``）。呼ぶ側の要素が
    続きの情報を作って決定を出す（``programs.guarded_damages``）。状態は、計算までのもの（「とうめい」の写しなど。続きの情報で運ぶ）しか変えていない。"""

    def __init__(self, owner: int, receiver: int, final: int, options: tuple[int, ...], max_choices: int, unresolved: tuple[int, ...], code: str | None,
                 reason: str | None):
        super().__init__(f"［ベンチガード］の決定（ポケモン {receiver}・{final} ダメージ）")
        self.owner = owner
        self.receiver = receiver
        self.final = final
        self.options = options
        self.max_choices = max_choices
        self.unresolved = unresolved
        self.code = code
        self.reason = reason

    def extra(self) -> tuple:
        if not self.unresolved:
            return ()
        return (("unresolved_choices", self.unresolved), ("unresolved_code", self.code), ("unresolved_reason", self.reason))


def _bench_guard_unresolved(res: Resolution, fs: FrameState, attacker, owner: int, receiver, final: int, holders, target: str,
                            weakness_resistance: bool, resistance: bool) -> tuple[tuple[int, ...], str | None, str | None]:
    """v0.65: ［ベンチガード］の決定の、選ぶと止める選択（BG1・BG2）。BG2 はもとのポケモンが受けるダメージが 0 になるときで、受けるポケモンに「ダメージを受けるとき」の候補
    （送る効果・こんじょう）があるとき。BG1 は、かわりに受ける 10 を、そのサイドンが受けるダメージとして計算し直すと量が変わる（無効になる・弱点・抵抗力・受けるダメージを
    変える効果）とき。"""
    state = res.state
    frame = fs.frame
    options = tuple(p.pokemon_id for p, _ in holders)
    reacting = bool(deferred_receivers(res, frame, owner, receiver)) or any(
        instance.definition.decision_kind == KO_PREVENTION for instance in _receiving_candidates(res, frame, owner, receiver))
    if reacting and final // 10 <= 1:
        return options, E.BENCH_GUARD_ZERO_CODE, E.BENCH_GUARD_ZERO_REASON
    if reacting and len(options) >= final // 10:
        # 2 匹以上のサイドンで、もとのポケモンのダメージがすべて移る答えだけが止まる（選択ごとには表せない。今の写しでは控えに［ベンチガード］が 2 匹・ちょうど 20 など）
        raise res.question("bench_guard_zero_reaction", f"ポケモン {receiver.pokemon_id}・{final} ダメージ・サイドン {list(options)}")
    knocked_out = tuple(p.pokemon_id for p, _ in holders if E.knocked_by_hp(state, p))
    if knocked_out:
        # KD1。ほかのサイドンの BG1 の確かめより先（同じ決定に両方がいるときも、すでに HP 以上のサイドンだけを KD1 で止め、残りは下で確かめる）
        rest = [(p, slot) for p, slot in holders if p.pokemon_id not in knocked_out]
        others, _, _ = _bench_guard_unresolved(res, fs, attacker, owner, receiver, final, rest, target, weakness_resistance, resistance) if rest else ((), None, None)
        if others:
            return knocked_out + others, E.KNOCKED_OUT_REACTION_CODE, (E.KNOCKED_OUT_REACTION_REASON + f"。サイドン {list(others)} は "
                                                                         + E.BENCH_GUARD_RECOMPUTE_REASON)
        return knocked_out, E.KNOCKED_OUT_REACTION_CODE, E.KNOCKED_OUT_REACTION_REASON
    differs = []
    for holder, _ in holders:
        if first_void(res, owner, holder) is not None:
            differs.append(holder.pokemon_id)
            continue
        try:
            modifiers = with_stadium_coin(res, frame, target, attack_modifiers_of(res, frame, attacker, holder, target))
            again = compute_damage(state, attacker, holder, 10, modifiers, weakness_resistance=weakness_resistance, resistance=resistance).final
        except (TypeReadingsDiffer, DamageOrderRequired, DamageReductionRequired):
            again = None
        if again != 10:
            differs.append(holder.pokemon_id)
    if differs:
        return tuple(differs), E.BENCH_GUARD_RECOMPUTE_CODE, E.BENCH_GUARD_RECOMPUTE_REASON
    return (), None, None


def bench_guard_answer(res: Resolution, fs: FrameState, attacker, owner: int, receiver, final: int, target: str, *, weakness_resistance: bool,
                       resistance: bool, guard: tuple[int, ...] | None, guard_suspend: bool) -> tuple:
    """v0.65（docs/reactive-decisions-v0.65.md 5 章）: 控えポケモン ``receiver`` が ``final``（10 以上）のワザのダメージを受けるときの［ベンチガード］。使えるサイドンがいなければ ()。
    答え（``guard``。かわりに受けるサイドンの番号）があればそれを確かめて返す。先読みなら答えを選ぶ。``guard_suspend`` なら ``BenchGuardRequest``（呼ぶ側が決定を出す）。
    決定を出せない呼ぶ側では問い（コードのない問い。今の写しのワザの要素はどれも出せる）。"""
    holders = E.bench_guard_holders(res.state, owner, receiver)
    if not holders:
        if guard:
            raise RuntimeError(f"［ベンチガード］の答え {guard} に、使えるサイドンがいない（続きの情報の誤り）")
        return ()
    options = tuple(p.pokemon_id for p, _ in holders)
    limit = min(len(options), final // 10)
    unresolved, code, reason = _bench_guard_unresolved(res, fs, attacker, owner, receiver, final, holders, target, weakness_resistance, resistance)
    if guard is not None:
        if len(set(guard)) != len(guard) or len(guard) > limit or not set(guard) <= set(options) or set(guard) & set(unresolved):
            raise RuntimeError(f"［ベンチガード］の答え {guard} が、選べるもの {options}（最大 {limit}。止める {unresolved}）と合わない（続きの情報の誤り）")
        return tuple(guard)
    if res.dry_run:
        allowed = [p for p in options if p not in unresolved]
        answers = [answer for count in range(min(limit, len(allowed)) + 1) for answer in itertools.combinations(allowed, count)]
        return tuple(res.oracle.choose(answers))
    if not guard_suspend:
        raise res.question("bench_guard_element", f"ポケモン {receiver.pokemon_id}・{final} ダメージ")
    raise BenchGuardRequest(owner, receiver.pokemon_id, final, options, limit, unresolved, code, reason)


def deal_damage(res: Resolution, fs: FrameState, target: str, base: int, *, log_extra: dict | None = None, pokemon_id: int | None = None,
                weakness_resistance: bool = True, orders: dict[int, tuple[int, ...]] | None = None,
                order_decision: bool = False, resistance: bool = True, defender_effects: bool = True,
                guard: tuple[int, ...] | None = None, guard_suspend: bool = False, reduction: int | None = None) -> DamageResult:
    """ワザの分類のダメージの要素 1 つ（v0.13 の ``deal_attack_damage`` と同じ結果・ログ・乱数）。

    v0.31: ``target`` が ``OPPONENT_BENCH`` なら ``pokemon_id`` の相手の控えポケモン（プラスパワーは変えない。``attack_damage_modifiers`` の
    ``bench``）。v0.33: ``SELF_BENCH`` なら自分の控えポケモン（計算は相手の控えと同じ）。``weakness_resistance`` が False なら弱点・抵抗力を計算しない（「「弱点・抵抗力」に関係なく」。ログに ``ignore_weakness_resistance``）。

    v0.35: 同じ段階の変更効果の計算の順番によって結果が変わるとき（``damage.DamageOrderRequired``）、``order_decision`` なら、状態を変える前に
    その例外をそのまま投げる（呼ぶ側のダメージの要素が、順番を選ぶ決定を出し、選んだ順番を ``orders`` に渡してもう一度呼ぶ。``programs.Damage``）。
    ``order_decision`` でない呼ぶ側（控えへのダメージ・返す効果のダメージなど。今の対応カードでは起こらない）は、エンジンの未対応として止める
    （問い ``damage_step_order``・``UNSUPPORTED_DAMAGE_STEP_ORDER``）。順番を決定で選んだときは、ログ ``damage`` に ``step_orders``（(段階, その段階の
    変更効果の名前を計算した順に)）を残す。

    v0.45: ``resistance`` が False なら抵抗力（4 段階）だけを計算しない（「「抵抗力」の影響を受けない」。ログに ``ignore_resistance``）。8 段階の
    「決まった数より小さければ 0 にする」効果（「かたくなる」。``damage.ZERO_IF_BELOW``）を計算したら、ログに ``damage_zero_below``（(段階, 発生源のカード,
    しきい値)）を残す。

    v0.60（docs/coins-defense-rebellion-v0.60.md）:

    - ``defender_effects`` が False なら、受けるポケモン自身が持っている効果の影響を受けない（タケシのサンドパンの「スピードスター」の「相手の持っている「弱点・抵抗力・
      特殊能力・その他の効果」の影響を受けない」）: 弱点・抵抗力を計算せず、受けるポケモンの持っている要素を無効にする効果（かたまる・バリアー）・ダメージを変える効果
      （ディフェンダー・持続する効果・常にはたらく特殊能力）・ダメージを受ける前の置きかえ（とうめい・かげぶんしん）を当てはめない。ワザを使うポケモンの持っている効果・
      場のほかのポケモン・スタジアムの効果は当てはめる。ダメージを受けたあとの反応（はんげき・返す効果・こんじょう）は「このワザのダメージ」への影響ではないので、今までどおり
      （実装上の読み方）。受けるポケモンの持ち主の場のほかのポケモンの常にはたらく特殊能力を当てはめるかで最終ダメージが変わるなら SS1（コードのない問い。今の写しの
      ［くつろぐかおり］はバトル場にいる限りはたらくので、持っているのは受けるポケモン自身で、起こらない）
    - 受けるポケモンが「かげぶんしん」の効果（``state.TailsDamageGuard``）を持ち、相手のワザによるダメージ（最終ダメージが 0 より大きい）を受ける時、相手プレイヤー（ワザ・
      返す効果を使うプレイヤー）がコインを 1 枚投げ（``coin_flip`` の ``source`` は ``"persistent_effect"``。ログ ``damage_guard_check``）、「うら」ならそのダメージを
      受けない（``DamageResult.dodged``）。「おもて」ならダメージを受けて、効果は消える（``persistent.remove_on_damage``。理由 ``damaged``。どのダメージでも消える）
    """
    state = res.state
    frame = fs.frame
    _, attacker = state.find_pokemon(frame.source_pid)
    receiver_player, receiver = receiver_of(res, fs, target, pokemon_id)
    if receiver.pokemon_id in res.secret_lost or (state.is_face_down(receiver) and designate(res, fs, receiver_player, receiver, "damage") is None):
        # v0.67: うらのカード（マチスの秘策）は、ダメージを受ける時におもてにする。「たねポケモン」でなければトラッシュしたので、このダメージの要素の対象はいない
        return DamageResult(target, receiver_player, receiver.pokemon_id, False, None, False, lost=True)
    if res.fled and frame.kind is FrameKind.ATTACK and receiver.pokemon_id in res.fled.values():
        # v0.65: ［にげこむ］のあとに、そのワザの残りのダメージの要素がかわりに出たポケモンに来た（今の写しのワザの並びでは起こらない。コードのない問い）
        raise res.question("flee_then_damage", f"ポケモン {receiver.pokemon_id}")
    if not defender_effects and target != OPPONENT_ACTIVE:
        raise ValueError(f"相手の持っている効果を除くダメージは相手の対戦ポケモンへのダメージだけ（{target!r}）")
    res.trace.record(DamageProposal(frame.id, receiver.pokemon_id, receiver_player, target, base))
    res.trace.record(WindowOpened(Window.BEFORE_DAMAGE, frame.id))
    void = first_void(res, receiver_player, receiver, held_by_receiver=defender_effects)
    if void is not None:
        # 無効（p.321）。計算しない。ログは v0.13 の damage_prevented
        state.add_event(
            "damage_prevented",
            player=receiver_player,
            pokemon=receiver.card,
            pokemon_id=receiver.pokemon_id,
            target=target,
            effect=str(frame.attack_key),
            persistent_effect=void.implementation.kind,
            source_card=void.implementation.source_card,
        )
        res.trace.record(DamageVoided(frame.id, receiver.pokemon_id, void.name))
        note_receipt(res, fs, receiver_player, receiver, voided=(DAMAGE_ELEMENT, _void_reason(res, receiver_player, receiver)))
        return DamageResult(target, receiver_player, receiver.pokemon_id, True, None, receiver.damage >= hp_of(state, receiver))
    if target in BENCH_TARGETS:
        cry = reduced_damage_to_source(state, attacker)
        if cry is not None and cry.source_card == receiver.card:
            # v0.34: 「なきつく」を受けたポケモンのワザが、効果を与えたポケモン（「このカード」）が控えにいるときにダメージを与える。説明の「このカードに
            # ワザを使う時」に控えポケモンへのダメージを含むかは決められない（NK5）
            # v0.76: 「なきごえ」（期限が次の相手の番の終わりの部分型。説明は「このカードにダメージを与える時」）も、控えにいるこのカードへのダメージに当てはめるかは記録で
            # 決まらないので同じ問い（NK5）。理由の文（「なきつく」の文）は v0.75 までと同じにし、なきごえのときだけ補足に書く
            growl = f"「なきごえ」（このカードにダメージを与える時、そのダメージが「-{cry.amount}」）の効果。" if not expires_at_turn_start(cry) else ""
            raise res.question("reduced_damage_bench_target", f"{growl}ポケモン {attacker.pokemon_id} → 控えのポケモン {receiver.pokemon_id}")
    lens = E.attack_ignores_resistance(state, attacker, receiver) if weakness_resistance and resistance and defender_effects else None
    if lens is not None:
        resistance = False  # v0.81: ピントレンズ（相手の対戦ポケモンの「抵抗力」に関係なく。``compute_damage`` も同じ関数で決める。ログに ``resistance_ignored_by``）
    base_modifiers = attack_modifiers_of(res, frame, attacker, receiver, target, defender_effects=defender_effects)
    if not defender_effects:
        weakness_resistance = False
        speed_star_scope_question(res, frame.attack_key, attacker, receiver, base, base_modifiers, orders, resistance, reduction)
    modifiers = with_stadium_coin(res, frame, target, base_modifiers)
    if frame.kind is FrameKind.RETALIATION:
        calming_retaliation_question(res, fs, attacker, receiver, base, target, weakness_resistance, resistance)
    while True:
        try:
            calc = compute_damage(state, attacker, receiver, base, modifiers, weakness_resistance=weakness_resistance, orders=orders, resistance=resistance,
                                  reduction=reduction)
            break
        except TypeReadingsDiffer as differ:
            raise type_question(res, differ, f"ワザ {frame.attack_key} のダメージの計算（ワザを使うポケモンの色と受けるポケモンの弱点・抵抗力）") from None
        except DamageOrderRequired as need:
            # v0.35: p.321 の同じ段階に、順番によって結果が変わる効果が重なった（「つるぎのまい」・「きあいだめ」と「なきつく」など）。計算の順番は
            # DAMAGE_STEP_CHOOSER のプレイヤーが決める（p.321。SC15）。決定を出せる呼ぶ側（ダメージの要素）に返す。出せない呼ぶ側では v0.34 と同じ問いで止める
            if order_decision:
                raise
            raise res.question("damage_step_order", f"ポケモン {attacker.pokemon_id}・{need.step} 段階の効果 {[m.label for m in need.modifiers]}") from None
        except DamageReductionRequired as need:
            # v0.66（docs/optional-trainers-v0.66.md 2 章）: お上品攻撃の「のぞむなら、そのダメージを好きなだけ小さくしてよい」（5 段階）。0 より小さくすることで結果が
            # 変わるなら CA1。減らせるダメージがなければ（5 段階で 0 以下）決定を出さずに減らさない。決定を出せる呼ぶ側（ワザのダメージの要素）に返し、出せない呼ぶ側
            # （返す効果のダメージ）ではエンジンの未対応として止める
            if need.below_zero:
                raise res.question("charity_below_zero", f"ポケモン {attacker.pokemon_id}・5 段階のダメージ {need.value}") from None
            if len(need.choices) == 1:
                reduction = 0
                continue
            if order_decision and frame.kind is FrameKind.ATTACK:
                raise
            raise res.question("damage_reduction_decision", f"ポケモン {attacker.pokemon_id}・{frame.kind.value} の枠のダメージ {need.value}") from None
    if target == SELF:
        trainer_self_bonus_question(res, attacker, receiver, base, modifiers, calc.final, weakness_resistance, orders, resistance)
    if calc.final > 0 and defender_effects and not reaches(res, fs, receiver_player, receiver, DAMAGE_ELEMENT, amount=calc.final):
        fs.evaded[receiver.pokemon_id] = calc.final
        res.trace.record(DamageEvaded(frame.id, receiver.pokemon_id, calc.final))
        note_receipt(res, fs, receiver_player, receiver, voided=(DAMAGE_ELEMENT, VOID_EVADED))
        return DamageResult(target, receiver_player, receiver.pokemon_id, False, None, receiver.damage >= hp_of(state, receiver), evaded=True)
    if calc.final > 0 and defender_effects and receiver_player != frame.player and not damage_guard_passes(res, fs, receiver_player, receiver, calc.final):
        res.trace.record(DamageEvaded(frame.id, receiver.pokemon_id, calc.final))
        note_receipt(res, fs, receiver_player, receiver, voided=(DAMAGE_ELEMENT, VOID_DODGED))
        return DamageResult(target, receiver_player, receiver.pokemon_id, False, None, receiver.damage >= hp_of(state, receiver), dodged=True)
    # v0.65: ［ベンチガード］（控えポケモンが受けるダメージを計算したあと・のせる前。受けるときの候補（送る効果・こんじょうの写し）は、もとのポケモンが受ける量で集める）
    guarded = ()
    if target in BENCH_TARGETS and calc.final >= 10:
        guarded = bench_guard_answer(res, fs, attacker, receiver_player, receiver, calc.final, target, weakness_resistance=weakness_resistance,
                                     resistance=resistance, guard=guard, guard_suspend=guard_suspend)
    elif guard:
        raise RuntimeError(f"［ベンチガード］の答え {guard} が、控えポケモンの 10 以上のダメージではない（続きの情報の誤り）")
    final = calc.final - 10 * len(guarded)
    deferred: list[Deferred] = []
    by_opponent = receiver_player != frame.player
    if final > 0:
        res.trace.record(WindowOpened(Window.DAMAGE_RECEIVING, frame.id))
        deferred = receiving(res, fs, receiver_player, receiver, final)
    if final > 0 and receiver.damage >= hp_of(state, receiver):
        focus_band_timing(res, receiver, "HP 以上になったあとにさらにダメージを受ける")  # v0.81（FB1）
    before = receiver.damage
    receiver.damage += final
    fs.applied[receiver.pokemon_id] = final
    extra: dict[str, Any] = {}
    added = tuple((m.step, m.source, m.amount) for m in calc.modifiers if m.operation == ADD)
    if added:
        extra["modifiers"] = added
    replaced = tuple((m.step, m.source, m.amount) for m in calc.modifiers if m.operation == SET)
    if replaced:
        # v0.27: 「その数にする」効果（「つるぎのまい」の 2 段階）。加える数の modifiers と混ぜない（(段階, 発生源のカード, その数)）
        extra["damage_set"] = replaced
    multiplied = tuple((m.step, m.source, m.amount) for m in calc.modifiers if m.operation == MULTIPLY)
    if multiplied:
        # v0.35: 「数をかける」効果（「きあいだめ」の 2 段階）。(段階, 発生源のカード, かける数)
        extra["damage_multiplied"] = multiplied
    zeroed = tuple((m.step, m.source, m.amount) for m in calc.modifiers if m.operation == ZERO_IF_BELOW)
    if zeroed:
        # v0.45: 「決まった数より小さければ 0 にする」効果（「かたくなる」の 8 段階）。(段階, 発生源のカード, しきい値)
        extra["damage_zero_below"] = zeroed
    # v0.46: 常にはたらく特殊能力・「リフレクター」の計算（docs/continuous-powers-v0.46.md 3 章）。どれも計算したときだけ書く（v0.45 までのログの形は変えない）
    zeroed_large = tuple((m.step, m.source, m.amount) for m in calc.modifiers if m.operation == ZERO_IF_AT_LEAST)
    if zeroed_large:
        extra["damage_zero_at_least"] = zeroed_large  # ［なぞのかべ］。(段階, 発生源のカード, しきい値)
    capped = tuple((m.step, m.source, m.threshold, m.amount) for m in calc.modifiers if m.operation == SET_IF_AT_LEAST)
    if capped:
        extra["damage_set_if_at_least"] = capped  # ［ふしぎなバリアー］。(段階, 発生源のカード, しきい値, その数)
    halved = tuple((m.step, m.source, "up" if m.operation == HALVE_UP else "down") for m in calc.modifiers if m.operation in (HALVE_UP, HALVE_DOWN))
    if halved:
        extra["damage_halved"] = halved  # ［くつろぐかおり］（切り上げ）・「リフレクター」（切りすて）。(段階, 発生源のカード, 丸め)
    if calc.reduction:
        # v0.66: お上品攻撃で小さくした量（(段階, 発生源のカード, 減らした数)）。減らさなかったら書かない（v0.65 までのログの形は変えない）
        extra["damage_reduced"] = ((5, calc.reduced_by[0], calc.reduction),)
    if orders:
        # v0.35: 順番の決定で選んだ計算の順番（(段階, その段階の変更効果の名前を計算した順に)）
        extra["step_orders"] = tuple((step, tuple(m.label for m in calc.modifiers if m.step == step)) for step in sorted(orders))
    if calc.stopped_after_step_2:
        extra["stopped_after_step_2"] = True
    if target != OPPONENT_ACTIVE:
        extra.update(target=target, pokemon_id=receiver.pokemon_id, effect=str(frame.attack_key))
    if not defender_effects:
        extra["ignore_defender_effects"] = True  # v0.60: 「スピードスター」（弱点・抵抗力も計算しない）
    if not weakness_resistance:
        extra["ignore_weakness_resistance"] = True  # v0.31
    elif not resistance:
        extra["ignore_resistance"] = True  # v0.45
        if lens is not None:
            extra["resistance_ignored_by"] = lens  # v0.81: ピントレンズ
    if log_extra:
        extra.update(log_extra)
    if guarded:
        extra["bench_guard"] = tuple((pid, 10) for pid in guarded)  # v0.65: かわりに受けたサイドン（計算した最終ダメージは steps の最後。のせたのは amount）
    state.add_event(
        "damage",
        player=receiver_player,
        pokemon=receiver.card,
        amount=final,
        steps=calc.steps,
        weakness=calc.weakness_applied,
        resistance=calc.resistance_applied,
        total_damage=receiver.damage,
        **extra,
    )
    note_receipt(res, fs, receiver_player, receiver, damage=final)  # v0.62: 受けたダメージ（最終ダメージ。0 でも受けた要素として記録する）
    remove_on_damage(state, receiver_player, receiver, final)  # v0.60: 「かげぶんしん」はダメージを受けたら消える
    res.trace.record(DamageApplied(frame.id, frame.damage_class, frame.source_pid, receiver.pokemon_id, receiver_player, final,
                                   before, receiver.damage, by_opponent))
    track_ko(res, fs, receiver, before)
    note_damage_ko(res, fs, receiver, before)  # v0.81: きあいのハチマキ・学習装置（ワザの分類のダメージで HP 以上になった）
    for pid in guarded:
        # v0.65: ［ベンチガード］のサイドンが、そのダメージのうちの 10 をかわりに受ける（計算し直さない。BG1 で変わる場合は止めた）。かわりに受けた 10 で、もう一度［ベンチガード］・
        # 「ダメージを受けたとき」の効果の候補を集めない（どの順番でも、のる組み合わせは同じ。実装上の正規化）
        holder = state.find_pokemon(pid)[1]
        held = holder.damage
        holder.damage += 10
        state.add_event("bench_guard", player=receiver_player, pokemon=holder.card, pokemon_id=pid, from_pokemon_id=receiver.pokemon_id, amount=10,
                        total_damage=holder.damage, effect=str(frame.attack_key))
        note_receipt(res, fs, receiver_player, holder, damage=10)
        remove_on_damage(state, receiver_player, holder, 10)
        res.trace.record(DamageApplied(frame.id, frame.damage_class, frame.source_pid, pid, receiver_player, 10, held, holder.damage, by_opponent))
        track_ko(res, fs, holder, held)
        note_damage_ko(res, fs, holder, held)
    fs.pending.extend(deferred)
    if target == OPPONENT_ACTIVE and final > 0:
        trainer_poison_after_damage(res, attacker, receiver_player, receiver, fs)
    return DamageResult(target, receiver_player, receiver.pokemon_id, False, final, receiver.damage >= hp_of(state, receiver))


def damage_guard_passes(res: Resolution, fs: FrameState, owner: int, pokemon: PokemonInPlay, final: int) -> bool:
    """v0.60: 「かげぶんしん」（R団のストライク。``state.TailsDamageGuard``）。``pokemon``（持ち主 ``owner``）がこの効果を持っていれば、相手プレイヤー（``owner`` の相手。
    ワザ・返す効果を使うプレイヤー）がコインを 1 枚投げ、「おもて」なら True（ダメージを受ける）、「うら」なら False（そのダメージを受けない）。効果がなければ True（コインなし）。

    - 「ダメージを受ける時」は、相手のワザのダメージの要素で最終ダメージが 0 より大きいとき（呼ぶ側が確かめる。最終ダメージが 0 なら「ダメージを受けなかった」（p.319・p.321）
      ので投げない。v0.9 の T21 と同じ読み方）。要素を無効にする効果（かたまる・バリアー）・「とうめい」で受けないと決まったなら、その前に終わっている
    - ダメージ以外の効果は「そのまま」なので、受けないのはこのダメージの要素だけ（ワザ全体を無効にしない。``fs.evaded`` に入れない（T19b の「受けない」とは別））
    - 「とうめい」と同じポケモンに重なることは、今の対応カードでは起こらない（R団のストライクは「とうめい」を持たず、［へんしん］で写す特殊能力は TF1 で止まる）ので、
      重なったら ``RuntimeError``（順番を推測しない）
    - コインは効果ごとではなくダメージの要素ごとに投げる（同じワザでもう一度ダメージを受ける時も、効果が残っていればまた投げる）。「おもて」でダメージを受けたら効果は消える
      （``deal_damage`` が ``remove_on_damage`` を呼ぶ）ので、同じワザのあとのダメージには投げない"""
    guard = tails_damage_guard(pokemon)
    if guard is None:
        return True
    if pokemon.pokemon_id in fs.reception:
        raise RuntimeError(f"ポケモン {pokemon.pokemon_id} に「とうめい」と「かげぶんしん」が重なった（今の対応カードでは起こらない。エンジンの不具合）")
    state = res.state
    frame = fs.frame
    flips = flip_coins(state, 1 - owner, 1, source="persistent_effect", effect=str(frame.attack_key), card=pokemon.card, pokemon_id=pokemon.pokemon_id)
    received = flips.results[0] is CoinSide.HEADS
    state.add_event("damage_guard_check", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, flipped_by=1 - owner,
                    persistent_effect=guard.kind, source_card=guard.source_card, created_turn=guard.created_turn, effect=str(frame.attack_key),
                    amount=final, result=flips.results[0].value, received=received)
    return received


def speed_star_scope_question(res: Resolution, attack_key, attacker: PokemonInPlay, receiver: PokemonInPlay, base: int, modifiers, orders, resistance: bool,
                              reduction: int | None = None) -> None:
    """v0.60（SS1）: 「スピードスター」の「相手の持っている…その他の効果」が、相手の対戦ポケモン自身が持っている効果だけか、相手プレイヤーの場のほかのポケモンが持っている
    効果（常にはたらく特殊能力。エリカのフシギソウの［くつろぐかおり］の「すべてのワザのダメージ」）も含むかは、印刷の文面・kyuura の記録から決まらない（太字の「相手」の
    定義（p.320）は相手の対戦ポケモンだが、「相手の持っている」という言い方を扱う記録はない。v0.33 の CD4 と同じ理由で決めない）。2 つの読み方（``EXCLUDE_DEFENDER_HELD``・
    ``EXCLUDE_DEFENDER_SIDE``）で最終ダメージ（または順番の決定の要否）が変わるときだけ止める（問い ``speed_star_scope``。今の写しでは起こらないのでコードのない問い。
    当たったらエンジンの不具合として止まる。ワザのダメージを変える常にはたらく特殊能力で、バトル場以外ではたらくものを加えるときに見直す）。"""
    state = res.state
    side = attack_damage_modifiers(state, attacker, receiver, attack=attack_key, attack_status=res.attack_status, exclude=EXCLUDE_DEFENDER_SIDE)
    if tuple(side) == tuple(modifiers):
        return
    finals = set()
    for variant in (modifiers, side):
        finals.add(_finals_over_reductions(lambda r, v=variant: same_for_type_readings(state, (attacker, receiver), lambda views: calculate_with_stadium(state,
            base, views[0], views[1], v, weakness_resistance=False, orders=orders, resistance=resistance, reduction=r)), reduction))
    if len(finals) > 1:
        raise res.question("speed_star_scope", f"ポケモン {attacker.pokemon_id} → ポケモン {receiver.pokemon_id}")


def _finals_over_reductions(compute, reduction: int | None):
    """``compute(reduction)`` の最終ダメージ（v0.66。比べる問い（SS1）が使う）。お上品攻撃の減らす量がまだ決まっていなければ、選べる量ごとの最終ダメージの並び
    （どの量を選んでも 2 つの読み方で同じかを比べる）。順番の決定・色の読み方で求められなければ None。"""
    try:
        return compute(reduction).final
    except (TypeReadingsDiffer, DamageOrderRequired):
        return None
    except DamageReductionRequired as need:
        outcomes = []
        for choice in need.choices:
            try:
                outcomes.append(compute(choice).final)
            except (TypeReadingsDiffer, DamageOrderRequired):
                outcomes.append(None)
        return ("reduce", need.below_zero, tuple(outcomes))


def trainer_self_bonus_question(res: Resolution, attacker: PokemonInPlay, receiver: PokemonInPlay, base: int, modifiers, final: int,
                                weakness_resistance: bool, orders, resistance: bool) -> None:
    """v0.56（MS1。docs/trainer-decisions-turn-effects-v0.56.md 7 章）: トレーナー「カスミ」の「「カスミのポケモン」が使うワザが対戦ポケモンにダメージを与える時、…+20」を、
    ワザを使うポケモン自身（自分のバトル場の対戦ポケモン）へのダメージ（カスミのジュゴンの「とっしん」の「自分にも20ダメージ」）に当てはめるかは、印刷の文面（「対戦ポケモン」は
    お互いのバトル場のポケモン。控えポケモンだけを除くと書く）・kyuura の記録で決まらない。当てはめるかどうかで最終ダメージが変わるときだけ止める（問い ``trainer_self_bonus``）。
    当てはめない計算（``attack_damage_modifiers`` は自分へのダメージに +20 を入れない）の結果 ``final`` と、+20 を 6 段階に加えた計算を比べる。"""
    from ..damage import DamageModifier
    from ..effects import trainer_attack_damage_bonuses

    state = res.state
    bonuses = trainer_attack_damage_bonuses(state, attacker)
    if not bonuses:
        return
    extra = tuple(DamageModifier(step=6, amount=amount, label=state.card_def(record.source_card).name_ja, source=record.source_card) for record, amount in bonuses)
    try:
        alternative = same_for_type_readings(state, (attacker, receiver), lambda views: calculate_with_stadium(state,
            base, views[0], views[1], (*modifiers, *extra), weakness_resistance=weakness_resistance, orders=orders, resistance=resistance)).final
    except (TypeReadingsDiffer, DamageOrderRequired):
        alternative = None
    if alternative != final:
        raise res.question("trainer_self_bonus", f"ポケモン {attacker.pokemon_id} の自分へのダメージ（{final} か {alternative}）")


def trainer_poison_after_damage(res: Resolution, attacker: PokemonInPlay, owner: int, receiver: PokemonInPlay, fs: FrameState | None = None) -> None:
    """v0.56（docs/trainer-decisions-turn-effects-v0.56.md 5 章）: トレーナー「キョウ」の「この番に、「キョウのポケモン」が、ワザによって相手の対戦ポケモンにダメージを
    与えたら、ダメージを受けたポケモンを「どく」状態にする」。ワザのダメージの要素が相手の対戦ポケモンに 0 より大きいダメージをのせた直後に呼ぶ（``deal_damage``。無効・
    「とうめい」・最終ダメージ 0・控えポケモンへのダメージでは呼ばない）。

    - 「キョウのポケモン」は、ダメージを与える時点のワザを使うポケモンの今の姿の名前（``effects.trainer_poison_effects``）。相手のワザとして使うワザ（ちょうのうりょく）も、
      使ったのが「キョウのポケモン」なら当てはまる
    - どく状態にするのは ``conditions.poison``（通常のどく。［めんえき］で防ぐ。すでにどく状態なら重ならない。特殊などく状態なら通常のどくになる（v0.3a の #14））。何枚
      使っていても、1 つのダメージで 1 回（同じ結果）。トレーナーの効果なので「ワザをうけない」状態・「とうめい」は評価しない（ダメージをのせたあとなので、ダメージを受けて
      いる）
    - 受けたポケモンがこのダメージで HP 以上なら、きぜつするポケモンなのでどく状態にしない。ただし、そのポケモンがきぜつの判定で使える効果（こんじょう）を持つなら、
      「おもて」で残ったポケモンが受けるかが決まらない（G37 と同じ問い ``ko_prevention_attack_effect``。そのダメージにともなう効果を受けるか）
    - どく状態にしたポケモンを ``res.trainer_poisoned`` に記録する（同じワザのあとの要素がこのポケモンを受けるダメージの違うどく状態にするとき、順番が決まらない。KG1。
      ``programs.Status`` が聞く）"""
    from ..conditions import poison
    from ..effects import trainer_poison_effects

    state = res.state
    records = trainer_poison_effects(state, attacker)
    if not records:
        return
    if knocked_by_hp(state, receiver):
        for instance in C.in_window(state, Window.KO_CHECK, owner, receiver, res.catalog):
            if instance.definition.timing is C.Timing.OFFER and res.ko_prevention_able.get(receiver.pokemon_id) and not C.offer_stopped(state, instance, receiver):
                raise res.question("ko_prevention_attack_effect", f"ポケモン {receiver.pokemon_id}（トレーナー「{state.card_def(records[0].source_card).name_ja}」のどく）")
        return
    poison(state, owner, receiver, effect=records[0].card_id)
    if fs is not None and receiver.conditions.poison is not None and E.status_immunity(state, owner, receiver) is None:
        # v0.62: このワザのダメージにともなう、トレーナーの効果のどく（受けた記録の C に入れる。オニスズメの「オウムがえし」は、どくのような続く効果を返すときに止める）
        note_receipt(res, fs, owner, receiver, reached=E.POISON)
    if receiver.conditions.poison is not None:
        res.trainer_poisoned.add(receiver.pokemon_id)


def calming_retaliation_question(res: Resolution, fs: FrameState, attacker: PokemonInPlay, receiver: PokemonInPlay, base: int, target: str,
                                 weakness_resistance: bool, resistance: bool) -> None:
    """返す効果のダメージ（ほのおのかべ・こうらがえし・クロスカウンター。前の番のワザの効果）に、ワザが使われた時の特殊状態で決める常にはたらく特殊能力
    （［くつろぐかおり］の「ワザが使われた時、すでに…」）が当てはまりうるとき（v0.46。CP1）。返すダメージは「こうらがえし」などのワザによるダメージ
    （GR-2000-P321-ATTACK-DAMAGE）だが、「ワザが使われた時」が返す効果を与えた前の番のワザか、きっかけになったこの番のワザかは決まらず、前の番のワザのときの
    特殊状態は記録していない。場所・かがくへんかガスの条件を満たす特殊能力があり、特殊状態によって当てはめるかどうかで最終ダメージ（または順番の決定の要否）が
    変わるなら止める（問い ``calming_retaliation``）。変わらなければ（半分にしても同じ数・特殊能力がない）止めない。"""
    if calming_retaliation_differs(res.state, fs.frame.attack_key, attacker, receiver, base, target, weakness_resistance, resistance):
        raise res.question("calming_retaliation", f"返すダメージ {base}（ポケモン {attacker.pokemon_id} → ポケモン {receiver.pokemon_id}）")


def calming_retaliation_differs(state: GameState, attack_key, attacker: PokemonInPlay, receiver: PokemonInPlay, base: int, target: str,
                                weakness_resistance: bool, resistance: bool) -> bool:
    """CP1 の比べ（v0.64。``calming_retaliation_question`` から分けた。先読みの「うら」が出るまで投げるコインの組も同じ関数で比べる）。状態を変えず、乱数を使わない。"""
    from ..effects import status_at_attack_powers

    if not status_at_attack_powers(state):
        return False
    every = frozenset(p.pokemon_id for player in state.players for p in player.in_play())
    # v0.48: 色の読み方（VS1）が 2 つあるポケモンは、読み方の組ごとに比べる（どれかの組で当てはめるかどうかで変われば止める。読み方の違いそのものは deal_damage が VS1 で見る）
    readings = [(a, r) for a in definition_views(state, attacker) for r in definition_views(state, receiver)]
    by_reading: list[set] = [set() for _ in readings]
    for snapshot in (frozenset(), every):  # 当てはめる読み方・当てはめない読み方
        modifiers = attack_damage_modifiers(state, attacker, receiver, attack=attack_key, bench=target in BENCH_TARGETS, attack_status=snapshot)
        for outcomes, (attacker_def, receiver_def) in zip(by_reading, readings):
            try:
                outcomes.add(_finals_over_reductions(lambda r, a=attacker_def, d=receiver_def, m=modifiers: calculate_with_stadium(
                    state, base, a, d, m, weakness_resistance=weakness_resistance, resistance=resistance, reduction=r), None))
            except DamageOrderRequired:
                outcomes.add(None)
    return any(len(outcomes) > 1 for outcomes in by_reading)


def _receiving_candidates(res: Resolution, frame, owner: int, pokemon: PokemonInPlay):
    """「ダメージを受けるとき」の窓の候補のうち、枠のダメージの分類・相手のワザか・場所の条件に合うもの（v0.64。``receiving`` から分けた）。状態を変えない。"""
    state = res.state
    for instance in C.in_window(state, Window.DAMAGE_RECEIVING, owner, pokemon, res.catalog):
        definition = instance.definition
        if frame.damage_class not in definition.trigger_classes:
            continue
        if definition.by_opponent and owner == frame.player:
            continue
        if definition.active_only and state.players[owner].active is not pokemon:
            continue  # v0.42: バトル場で受けたときだけ（ぼうぎょかふん）
        if definition.opponent_turn_only and owner == state.current_player:
            continue  # v0.81: 相手の番に受けたときだけ（はんげきのツメ。返す効果のダメージを自分の番に受けたときは当たらない）
        yield instance


def deferred_receivers(res: Resolution, frame, owner: int, pokemon: PokemonInPlay) -> list:
    """``receiving`` が送る効果として集めるもの（``Timing.DEFER``・はたらいている・同じ定義は最初の 1 つ）と同じ候補（v0.64。状態・解決の記録・こんじょうの写しを
    変えない。先読みの「うら」が出るまで投げるコインの組が使う）。"""
    found: list = []
    for instance in _receiving_candidates(res, frame, owner, pokemon):
        definition = instance.definition
        if definition.timing is C.Timing.DEFER and C.working(res.state, instance, pokemon):
            if any(other.definition is definition for other in found):
                continue
            found.append(instance)
    return found


def receiving(res: Resolution, fs: FrameState, owner: int, pokemon: PokemonInPlay, received: int) -> list[Deferred]:
    """「ダメージを受けるとき」の窓: 受けるポケモンの効果のうち、この枠のダメージの分類・相手のワザかで候補になるものを集める。

    - 送る効果（``Timing.DEFER``。はんげき・返す効果）は、受けるときの状態ではたらいていれば候補（特殊状態は「すでに」の時点。
      ガス・はたらく番も今）。
    - 任意の効果（``Timing.OFFER``。こんじょう）は、受けるときの特殊状態を写す（ガスはきぜつの判定の時点で見る。v0.13 と同じ）。
    """
    state = res.state
    frame = fs.frame
    found: list[Deferred] = []
    for instance in _receiving_candidates(res, frame, owner, pokemon):
        definition = instance.definition
        if definition.timing is C.Timing.OFFER and definition.decision_kind == REACTION_SWITCH:
            # v0.65: ［にげこむ］。ダメージを受けるときの特殊状態（「すでに」）で使えるかを決め、使えるなら、ダメージの要素のあと・ダメージ以外の効果の前に聞く候補にする
            # （``programs.offer_flee``）。同じワザで同じポケモンが 2 回受けても候補は 1 つ（どちらの答えも同じ時点で聞くので、まとめても結果は同じ）
            if not C.blocked_by_status(instance, pokemon) and all(entry[1] != pokemon.pokemon_id for entry in res.flee_offers):
                key = instance.power_key
                res.flee_offers.append((owner, pokemon.pokemon_id, key.card_id, key.power_index, int(frame.kind is FrameKind.RETALIATION)))
                res.trace.record(CandidateFound(Window.DAMAGE_RECEIVING, definition.name, pokemon.pokemon_id, frame.id))
            continue
        if definition.timing is C.Timing.OFFER:
            # v0.13 と同じく、受けるたびに写しを書きかえる（同じポケモンが 1 つのコマンドで 2 回受けることは今の対応カードでは起こらない）
            res.ko_prevention_able[pokemon.pokemon_id] = not C.blocked_by_status(instance, pokemon)
            res.trace.record(CandidateFound(Window.DAMAGE_RECEIVING, definition.name, pokemon.pokemon_id, frame.id))
            continue
        if definition.timing is C.Timing.DEFER and C.working(state, instance, pokemon):
            if any(d.instance.definition is definition for d in found):
                continue  # 同じ定義の 2 つめ（同じカードに同じ種類の特殊能力が 2 つ）は v0.13 と同じく最初の 1 つ
            found.append(Deferred(instance, frame.id, received))
            res.trace.record(CandidateFound(Window.DAMAGE_RECEIVING, definition.name, pokemon.pokemon_id, frame.id))
    return found


def reaches(res: Resolution, fs: FrameState, owner: int, pokemon: PokemonInPlay, element: str, *, amount: int | None = None) -> bool:
    """受ける前の置きかえ（とうめい）の窓（v0.13 の ``attack_reaches`` と同じ結果・ログ・乱数）。1 つの枠で 1 匹 1 回（T4）。"""
    state = res.state
    frame = fs.frame
    if element not in ATTACK_ELEMENTS:
        raise ValueError(f"受ける要素の種類 {element!r} は未定義")
    if element != DAMAGE_ELEMENT and fs.pending:
        raise RuntimeError(f"効果の要素 {element} の前に、送る効果が残っている（窓の位置の誤り。エンジンの不具合）")
    window = Window.BEFORE_DAMAGE if element == DAMAGE_ELEMENT else Window.BEFORE_EFFECT
    if pokemon.pokemon_id in res.secret_lost or (state.is_face_down(pokemon) and designate(res, fs, owner, pokemon, element) is None):
        # v0.67: うらのカード（マチスの秘策）は、効果を受ける時におもてにする。「たねポケモン」でなければトラッシュしたので、この要素の対象はいない（ログは
        # ``secret_plan_revealed``・``secret_plan_discarded``。前にトラッシュしたなら、何も残さない）
        return False
    if element != DAMAGE_ELEMENT and res.fled and frame.kind is FrameKind.ATTACK and (
            pokemon.pokemon_id in res.fled or pokemon.pokemon_id in res.fled.values()):
        # v0.65: ［にげこむ］で入れ替えたポケモンは、そのワザによる「ダメージ以外の効果」を受けない（p.100 の最新の説明。v0.18b の記録の再利用）。かわりに出たポケモンにも、
        # その効果を移さない（もとの対象ではない）。コイン・「とうめい」の判定はしない
        fled = pokemon.pokemon_id in res.fled
        state.add_event("flee_effect_skipped", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, effect=str(frame.attack_key), element=element,
                        reason="fled" if fled else "replacement")
        if fled:
            note_receipt(res, fs, owner, pokemon, voided=(element, VOID_FLED))
        return False
    if element != DAMAGE_ELEMENT:
        # v0.31: 効果の要素を無効にする効果（「ワザをうけない」状態。バリアー）。「とうめい」より先（ダメージの要素の無効（first_void）と同じ順番）
        void = first_void(res, owner, pokemon, Window.BEFORE_EFFECT)
        if void is not None:
            state.add_event("effect_prevented", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, effect=str(frame.attack_key),
                            element=element, persistent_effect=void.implementation.kind, source_card=void.implementation.source_card)
            res.trace.record(DamageVoided(frame.id, pokemon.pokemon_id, void.name))
            reason = VOID_ATTACK_BARRIER if Window.BEFORE_DAMAGE in void.definition.windows else VOID_EFFECT_ONLY  # v0.80: エフェクトガード
            note_receipt(res, fs, owner, pokemon, voided=(element, reason))
            return False
    memo = fs.reception.get(pokemon.pokemon_id)
    if memo is None:
        instance = None
        for candidate in C.in_window(state, window, owner, pokemon, res.catalog):
            if candidate.definition.timing is C.Timing.REPLACE and C.working(state, candidate, pokemon):
                instance = candidate
                break
        if instance is None:
            _note_reached(res, fs, owner, pokemon, element)
            return True
        if any(pid != pokemon.pokemon_id for pid in fs.reception):
            raise res.question("multiple_evasion", f"枠 {frame.id}")
        res.trace.record(Activated(window, instance.name, pokemon.pokemon_id, frame.id))
        flips = flip_coins(state, owner, 1, source="power", effect=str(instance.power_key), card=pokemon.card, pokemon_id=pokemon.pokemon_id)
        evaded = flips.results[0] is CoinSide.HEADS
        memo = not evaded
        fs.reception[pokemon.pokemon_id] = memo
        state.add_event(
            "evade_check",
            player=owner,
            pokemon=pokemon.card,
            pokemon_id=pokemon.pokemon_id,
            power=str(instance.power_key),
            attacker=frame.player,
            attacker_pokemon_id=frame.source_pid,
            effect=str(frame.attack_key),
            element=element,
            result=flips.results[0].value,
            evaded=evaded,
        )
    if not memo:
        extra = {} if amount is None else {"amount": amount}
        state.add_event(
            "attack_evaded", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, effect=str(frame.attack_key), element=element, **extra
        )
        note_receipt(res, fs, owner, pokemon, voided=(element, VOID_EVADED))
    else:
        _note_reached(res, fs, owner, pokemon, element)
    return memo


def _note_reached(res: Resolution, fs: FrameState, owner: int, pokemon: PokemonInPlay, element: str) -> None:
    """v0.62: 効果の要素が届いた（受ける）ことを受けた記録に加える。ダメージの要素は ``deal_damage`` がのせたあとに記録する（ここでは何もしない）。特殊状態にする要素で、
    受けるポケモンが特殊状態にならない（［めんえき］）なら、受けなかった要素として記録する。"""
    if element == DAMAGE_ELEMENT:
        return
    if element in (E.POISON, E.SLEEP, E.PARALYSIS, E.CONFUSION) and E.status_immunity(res.state, owner, pokemon) is not None:
        note_receipt(res, fs, owner, pokemon, voided=(element, VOID_IMMUNE))
        return
    note_receipt(res, fs, owner, pokemon, reached=element)


# ---------------------------------------------------------------- ダメージの要素のあとの窓（送る効果）


def restore_deferred(res: Resolution, fs: FrameState, entries) -> list[Deferred]:
    """決定をまたいで運んだ送る効果（v0.34。``AttackRun.suspend`` の ``carry``）を、今の場の効果から作り直す。決定を待つ間は場が変わらないので、
    受けたときに候補になった効果（持ち主・持つポケモン・定義の名前）は今も同じポケモンにある。見つからない・2 つ以上なら、続きの情報の誤り。

    受けたときの「はたらいているか」（特殊状態の「すでに」・ガス・はたらく番）は受けたときに確かめたので、ここで確かめ直さない（``receiving``）。"""
    restored = []
    for owner, pokemon_id, name, received in entries:
        located = res.state.find_pokemon(pokemon_id)
        if located is None or located[0] != owner:
            raise RuntimeError(f"運んだ送る効果 {name} の持ち主 {owner} のポケモン {pokemon_id} が場にいない（続きの情報の誤り）")
        matches = [instance for instance in C.in_window(res.state, Window.DAMAGE_RECEIVING, owner, located[1], res.catalog)
                   if instance.definition.name == name and instance.definition.timing is C.Timing.DEFER]
        if len(matches) != 1:
            raise RuntimeError(f"運んだ送る効果 {name} が、ポケモン {pokemon_id} に {len(matches)} つある（続きの情報の誤り）")
        restored.append(Deferred(matches[0], fs.frame.id, received))
    return restored


def fire_pending(res: Resolution, fs: FrameState) -> None:
    """枠の「ダメージの要素のあと」の窓（p.89）: 送る効果を処理する。2 つ以上なら順番が原典で決まらない（C34・C35。起こらない）。"""
    if not fs.pending:
        return
    pending = tuple(fs.pending)
    fs.pending.clear()
    res.trace.record(WindowOpened(Window.AFTER_DAMAGE_ELEMENTS, fs.frame.id))
    if len(pending) + fs.fired > 1:
        # v0.31: 1 つのワザの中で、効果の要素をはさんで 2 回目にはたらいた「ダメージを受けたとき」の効果（わるいギャロップの「ひばしら」で
        # 対戦ポケモンと控えポケモンの両方の「はんげき」など）も、同じ問い（C34・C35）。``fs.fired`` は決定をまたいで運ぶ
        raise res.question("multiple_deferred_effects", f"{[d.instance.name for d in pending]}（この枠ですでに {fs.fired}）")
    fs.fired += len(pending)
    for deferred in pending:
        res.trace.record(Activated(Window.AFTER_DAMAGE_ELEMENTS, deferred.instance.name, deferred.instance.pokemon_id, fs.frame.id))
        ACTIONS[deferred.instance.definition.action](res, fs, deferred)


def _damage_source(res: Resolution, fs: FrameState, what: str) -> PokemonInPlay:
    found = res.state.find_pokemon(fs.frame.source_pid)
    if found is None or found[0] != fs.frame.player:
        raise RuntimeError(f"{what}を与える相手（ダメージを与えたポケモン {fs.frame.source_pid}）が場にいない（エンジンの不具合）")
    if found[1].damage >= hp_of(res.state, found[1]):
        focus_band_timing(res, found[1], f"HP 以上になったあとの{what}")  # v0.81（FB1）
    return found[1]


def power_damage_to_damage_source(res: Resolution, fs: FrameState, deferred: Deferred) -> None:
    """特殊能力のダメージを、ダメージを与えたポケモンに（はんげき。v0.13 の ``_apply_counterattack`` と同じ結果・ログ）。

    特殊能力の分類の枠を起こし、そのダメージは弱点・抵抗力・ダメージを変える効果・置きかえを通さない。特殊能力の分類のダメージでは、
    どの「ダメージを受けたとき」の効果も候補にならない（枠を起こさない）。"""
    state = res.state
    instance = deferred.instance
    attacker = _damage_source(res, fs, "特殊能力のダメージ")
    hp = hp_of(state, attacker)
    base = {
        "player": instance.owner,
        "pokemon": instance.card,
        "pokemon_id": instance.pokemon_id,
        "power": str(instance.power_key),
        "attacker": fs.frame.player,
        "attacker_pokemon": attacker.card,
        "attacker_pokemon_id": attacker.pokemon_id,
        "effect": str(fs.frame.attack_key),
    }
    if attacker.damage >= hp:
        state.add_event("counterattack_skipped", **base, reason=COUNTERATTACK_TARGET_KNOCKED_OUT)
        return
    if not instance.implementation.ignores_weakness_resistance:
        # v0.17b: 説明に「弱点・抵抗力」に関係なく、がない特殊能力のダメージ（わるいねぞう）に弱点・抵抗力を計算するかは原典で決まらない（Z9）。
        # 計算しない処理で結果が同じなのは、受けるポケモンの弱点・抵抗力が与えるポケモンのタイプでないときだけ（今の対応カードでは起こらない）
        # v0.48: 与えるポケモンの今有効な色（読み方のどれか）と、受けるポケモンの今有効な弱点・抵抗力（``effects.weakness_of``・``resistance_of``）で比べる
        source = state.find_pokemon(instance.pokemon_id)[1]
        against = {weakness_of(state, attacker), resistance_of(state, attacker)[0]} - {None}
        if any(color in against for color in type_readings(state, source)):
            raise res.question("power_damage_weakness_resistance", f"{instance.power_key} → ポケモン {attacker.pokemon_id}")
    if first_void(res, fs.frame.player, attacker) is not None:
        raise RuntimeError(f"ワザを使ったポケモン {attacker.pokemon_id} が自分の番に「ダメージを受けない」状態（エンジンの不具合）")
    child = res.open_frame(FrameKind.POWER_DAMAGE, parent=fs.frame.id, player=instance.owner, source_pid=instance.pokemon_id,
                           attack_key=fs.frame.attack_key)
    child.origin = instance
    before = attacker.damage
    # v0.46: 受けるポケモンの、受けるダメージ全体を書く常にはたらく特殊能力（エリカのミニリュウの［ふしぎなバリアー］は R団のカビゴン（たねポケモン）の
    # ［わるいねぞう］の 20 を 10 にする）。p.321 の計算（ワザによるダメージ）ではない。当てはめたときだけログに書く
    holder = state.find_pokemon(instance.pokemon_id)[1]
    amount, applied = received_power_damage(state, fs.frame.player, attacker, holder, instance.implementation.amount)
    attacker.damage += amount
    child.applied[attacker.pokemon_id] = amount
    extra = {} if not applied else {"amount_before": instance.implementation.amount, "received_modifiers": received_modifiers_log(applied)}
    state.add_event("counterattack", **base, amount=amount, total_damage=attacker.damage,
                    knocked_out=attacker.damage >= hp, **extra)
    remove_on_damage(state, fs.frame.player, attacker, amount)  # v0.60: 「かげぶんしん」はダメージを受けたら消える（特殊能力のダメージでも）
    track_ko(res, child, attacker, before)


def attack_damage_to_damage_source(res: Resolution, fs: FrameState, deferred: Deferred) -> None:
    """前の番のワザの効果のダメージを、ダメージを与えたポケモンに（ほのおのかべ・こうらがえし。v0.13 の ``_apply_retaliation`` と同じ
    結果・ログ）。返す効果の枠（ワザの分類）を起こし、そのダメージの要素を同じ ``deal_damage`` で処理する（弱点・抵抗力・ディフェンダー・
    とうめい・受けたポケモンのはんげき）。枠の中の送る効果は、その枠のダメージの要素のあとの窓で処理してから親にもどる。"""
    state = res.state
    instance = deferred.instance
    effect = instance.implementation
    attacker = _damage_source(res, fs, "返すダメージ")
    holder_found = state.find_pokemon(instance.pokemon_id)
    if holder_found is None or holder_found[0] != instance.owner:
        raise RuntimeError(f"返す効果を持つポケモン {instance.pokemon_id} が場にいない（エンジンの不具合）")
    key = AttackKey(effect_attack_card(state, effect), effect.attack_index)  # v0.49: 効果を与えたワザを印刷したカード（``attack_card``）
    if state.players[1 - instance.owner].active is not attacker:
        raise RuntimeError(f"返すダメージの相手が、ワザを使ったポケモン {attacker.pokemon_id} ではない（エンジンの不具合）")
    base = {
        "player": instance.owner,
        "pokemon": instance.card,
        "pokemon_id": instance.pokemon_id,
        "persistent_effect": effect.kind,
        "source_card": effect.source_card,
        "effect": str(key),
        "trigger": str(fs.frame.attack_key),
        "attacker": fs.frame.player,
        "attacker_pokemon": attacker.card,
        "attacker_pokemon_id": attacker.pokemon_id,
    }
    if attacker.damage >= hp_of(state, attacker):
        # 与える相手がいない（C15・W23）。v0.45: コインの条件のある効果（「クロスカウンター」）も、処理の対象がないのでコインを投げない（p.309。v0.38 の
        # ``has_target``・v0.42 の［ぼうぎょかふん］と同じ読み方）
        state.add_event("retaliation_skipped", **base, reason=RETALIATION_TARGET_KNOCKED_OUT)
        return
    scaled = {}
    if effect.scaled:
        # v0.45: 「クロスカウンター」（kyuura の最新の説明）: ダメージを受けたときにコインを投げ（効果を持つポケモンの持ち主。効果を与えたのはそのポケモンの
        # ワザなので ``source="attack"``・ワザの識別子）、「おもて」なら受けたダメージの ``multiplier`` 倍を与える。「うら」なら与えない（ログ
        # ``retaliation_skipped`` の理由 ``coin_tails``）。効果を与えたときにはコインを投げない
        scaled = {"multiplier": effect.multiplier}
        if effect.on_heads:
            flips = flip_coins(state, instance.owner, 1, source="attack", effect=str(key), card=instance.card, pokemon_id=instance.pokemon_id)
            if flips.results[0] is not CoinSide.HEADS:
                state.add_event("retaliation_skipped", **base, reason=RETALIATION_COIN_TAILS, received_damage=deferred.received)
                return
            scaled["coin"] = CoinSide.HEADS.value
    amount = effect.base_damage(deferred.received)
    if effect.basis == RETALIATION_FIXED:
        state.add_event("retaliation", **base, amount=amount)
    else:
        state.add_event("retaliation", **base, amount=amount, basis=effect.basis, received_damage=deferred.received, **scaled)
    child = res.open_frame(FrameKind.RETALIATION, parent=fs.frame.id, player=instance.owner, source_pid=instance.pokemon_id, attack_key=key)
    child.origin = instance
    deal_damage(res, child, OPPONENT_ACTIVE, amount, log_extra={"retaliation": True, "effect": str(key), "pokemon_id": attacker.pokemon_id})
    fire_pending(res, child)


def power_confusion_to_damage_source(res: Resolution, fs: FrameState, deferred: Deferred) -> None:
    """コインを投げ、「おもて」なら、ダメージを与えたポケモンをこんらん状態にする（v0.42。エリカのラフレシアの［ぼうぎょかふん］）。

    コインを投げるのは効果を持つポケモンの持ち主（``source="power"``、``effect`` は ``PowerKey``。とうめい（T33）・こんじょうと同じ）。特殊能力の効果なので、
    受けるポケモンの「ワザをうけない」状態・「とうめい」は評価しない。ダメージを与えたポケモンがすでに HP 以上なら、処理の対象がないので投げない（ログ
    ``power_confusion_skipped``。はんげきの C15・v0.38 の ``has_target`` と同じ読み方）。ログ ``power_confusion``（``result``・``confused``）。こんらんにするのは
    ``conditions.confuse``（ログ ``special_condition`` の ``effect`` は特殊能力の識別子）。"""
    state = res.state
    instance = deferred.instance
    source = _damage_source(res, fs, "こんらん")
    base = {
        "player": instance.owner,
        "pokemon": instance.card,
        "pokemon_id": instance.pokemon_id,
        "power": str(instance.power_key),
        "attacker": fs.frame.player,
        "attacker_pokemon": source.card,
        "attacker_pokemon_id": source.pokemon_id,
        "effect": str(fs.frame.attack_key),
    }
    if source.damage >= hp_of(state, source):
        state.add_event("power_confusion_skipped", **base, reason=COUNTERATTACK_TARGET_KNOCKED_OUT)
        return
    if state.players[fs.frame.player].active is not source:
        raise RuntimeError(f"ダメージを与えたポケモン {source.pokemon_id} がバトル場にいない（こんらん状態にできない。エンジンの不具合）")
    flips = flip_coins(state, instance.owner, 1, source="power", effect=str(instance.power_key), card=instance.card, pokemon_id=instance.pokemon_id)
    confused = flips.results[0] is CoinSide.HEADS
    state.add_event("power_confusion", **base, result=flips.results[0].value, confused=confused)
    if confused:
        confuse(state, fs.frame.player, source, effect=str(instance.power_key))


class EnergyDrainRequest(Exception):
    """v0.68: ［だつりょくえき］の「おもて」で、トラッシュするエネルギーカードを持ち主に選ばせる（呼ぶ側の ``programs.run_elements`` が決定 ``ENERGY_DRAIN_DISCARD`` を出し、
    答えのあとに ``apply_energy_drain`` で続ける）。コインはもう投げたので、答えのあとで投げ直さない。"""

    def __init__(self, entry: tuple[int, int, str, int, int], options: tuple[int, ...]):
        super().__init__(entry)
        self.entry = entry  # (持ち主, ポケモンの番号, カード id, 特殊能力の位置, ダメージを与えたポケモンの番号)
        self.options = options


def drain_energy_from_damage_source(res: Resolution, fs: FrameState, deferred: Deferred) -> None:
    """v0.68（docs/final-pmcg-cards-v0.68.md 3 章）: ［だつりょくえき］。コインを投げ、「おもて」なら、持ち主がダメージを与えたポケモンについているエネルギーカードを 1 枚選び、
    その持ち主のトラッシュに置く。

    - コインの前に、ダメージを与えたポケモンがすでに HP 以上なら DR8、エネルギーカードがついていなければ DR13 で止める（どちらも採用の仕様で決まらない。宣言の前に先読みが見つける）
    - コインは持ち主（``source="power"``、``effect`` は ``PowerKey``。ログ ``energy_drain_check``）。特殊能力の効果なので「ワザをうけない」状態・「とうめい」は関係しない
    - 「おもて」なら、先読みは答えのすべてを試し、実際の処理は ``EnergyDrainRequest`` で決定を出す（答えは ``apply_energy_drain``）"""
    state = res.state
    instance = deferred.instance
    source = _damage_source(res, fs, "エネルギーカードのトラッシュ")
    detail = f"{instance.power_key} → ポケモン {source.pokemon_id}"
    if source.damage >= hp_of(state, source):
        raise res.question("energy_drain_attacker_knocked_out", detail)
    if not source.energy:
        raise res.question("energy_drain_no_energy", detail)
    flips = flip_coins(state, instance.owner, 1, source="power", effect=str(instance.power_key), card=instance.card, pokemon_id=instance.pokemon_id)
    heads = flips.results[0] is CoinSide.HEADS
    state.add_event("energy_drain_check", player=instance.owner, pokemon=instance.card, pokemon_id=instance.pokemon_id, power=str(instance.power_key),
                    attacker=fs.frame.player, attacker_pokemon=source.card, attacker_pokemon_id=source.pokemon_id, effect=str(fs.frame.attack_key),
                    result=flips.results[0].value)
    if not heads:
        return
    key = instance.power_key
    entry = (instance.owner, instance.pokemon_id, key.card_id, key.power_index, source.pokemon_id)
    options = tuple(source.energy)
    if res.dry_run:
        apply_energy_drain(state, entry, res.oracle.choose([(card,) for card in options]))
        return
    raise EnergyDrainRequest(entry, options)


def apply_energy_drain(state: GameState, entry: tuple, choices: tuple[int, ...]) -> None:
    """v0.68: ［だつりょくえき］の答え。選んだエネルギーカードを、ダメージを与えたポケモンからはがして、そのカードの持ち主のトラッシュに置く（ログ ``energy_drain_discard``）。"""
    owner, pokemon_id, card_id, power_index, source_pid = entry
    located = state.find_pokemon(source_pid)
    if located is None or len(choices) != 1 or choices[0] not in located[1].energy:
        raise RuntimeError(f"［だつりょくえき］でトラッシュするエネルギーカード {choices} が、ポケモン {source_pid} についていない（エンジンの不具合）")
    holder, source = located
    card = choices[0]
    E.discard_energy_from_play(  # v0.82: 相手（だつりょくえきの持ち主）の特殊能力でトラッシュ（リサイクルエネルギー・エコロジム）
        state, source, (card,), cause=E.DISCARD_BY_POWER, by_player=owner,
        log=lambda: state.add_event("energy_drain_discard", player=owner, pokemon_id=pokemon_id, power=str(E.PowerKey(card_id, power_index)), attacker=holder,
                                    attacker_pokemon_id=source_pid, card=card))


def counters_to_damage_source_on_heads(res: Resolution, fs: FrameState, deferred: Deferred) -> None:
    """v0.81（docs/pokemon-tools-stadiums-v0.81.md 5 章）: はんげきのツメ（``effects.CounterClaw``）。持ち主がコインを 1 枚投げ（``source="trainer"``。ログ ``counter_claw``）、
    「おもて」なら相手の対戦ポケモン（ダメージを与えたワザを使ったプレイヤーのバトル場のポケモン）にダメージカウンターを ``counters`` 個のせ（ダメージではない。ログ
    ``tool_damage_counters``）、このカードをトラッシュする（ログ ``discard_attached_trainer`` の ``reason`` ``used``）。「うら」ならついたまま。

    - のせる前に、のせたカウンターでそのポケモンが HP 以上になり、同じワザでほかのポケモンも HP 以上で、どちらのきぜつを先に処理するかで勝ち負けが変わるなら、既存の C18
      （同時のきぜつか決まらない。［ファイナルビーム］と同じ確かめ）。先読みがコインのどちらの結果も試すので、宣言の前に止まる
    - のせたカウンターで HP 以上になったら、ワザのあとのきぜつの判定でまとめて処理する（きぜつの原因の枠はこのワザ。こんじょうは使えない）"""
    state = res.state
    instance = deferred.instance
    attached, effect = instance.implementation
    owner = instance.owner
    target_owner = 1 - owner
    target = state.players[target_owner].active
    base = {"player": owner, "pokemon": instance.card, "pokemon_id": instance.pokemon_id, "card": attached.card, "effect": str(fs.frame.attack_key)}
    flips = flip_coins(state, owner, 1, source="trainer", effect=state.cards[attached.card].card_id, card=attached.card, pokemon_id=instance.pokemon_id)
    heads = flips.results[0] is CoinSide.HEADS
    state.add_event("counter_claw", **base, result=flips.results[0].value)
    if not heads:
        return
    if target is None:
        raise RuntimeError("はんげきのツメの相手の対戦ポケモンがいない（エンジンの不具合）")
    amount = effect.counters * state.rules.damage_per_counter
    before = target.damage
    hp = hp_of(state, target)
    if before < hp <= before + amount:
        others = [(o, p) for o, p in knocked(res) if p is not target]
        if others:
            gone = others + [(target_owner, target)]
            taken = {player: sum(1 for o, p in gone if o != player and E.counts_as_knockout(state, p)) for player in (0, 1)}
            ends = [(taken[player] and taken[player] >= len(state.players[player].prizes))
                    or not [p for p in state.players[player].in_play() if all(p is not k for _, k in gone)] for player in (0, 1)]
            if any(ends):
                raise res.question("counterattack_double_knockout", f"はんげきのツメ {attached.card} → ポケモン {target.pokemon_id}",
                                   UnsupportedError("UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT",
                                                    f"はんげきのツメのダメージカウンター {effect.counters} 個でポケモン {target.pokemon_id} もきぜつする: ワザによるきぜつと、"
                                                    "それがはたらかせたどうぐの効果によるきぜつが「同時に「きぜつ」した」ことになるか（p.324）は決められず、どちらのきぜつを先に処理"
                                                    "するかで勝ち負けが変わる（C18 と同じ問い）"))
    target.damage += amount
    state.add_event("tool_damage_counters", **base, target_player=target_owner, target_pokemon=target.card, target_pokemon_id=target.pokemon_id,
                    counters=effect.counters, total_damage=target.damage)
    track_ko(res, fs, target, before)
    if before < hp <= target.damage:
        res.ko_prevention_able[target.pokemon_id] = False  # ダメージカウンターでは「こんじょう」を使えない（G3〜G7）
    holder = state.find_pokemon(instance.pokemon_id)
    if holder is None or attached not in holder[1].trainers:
        raise RuntimeError(f"はんげきのツメ {attached.card} が、ポケモン {instance.pokemon_id} についていない（エンジンの不具合）")
    E.discard_attached_tool(state, holder[1], attached, E.TOOL_USED)


ACTIONS: dict[str, Callable[[Resolution, FrameState, Deferred], None]] = {
    "power_damage_to_damage_source": power_damage_to_damage_source,
    "attack_damage_to_damage_source": attack_damage_to_damage_source,
    "power_confusion_to_damage_source": power_confusion_to_damage_source,  # v0.42
    "drain_energy_from_damage_source": drain_energy_from_damage_source,  # v0.68
    "counters_to_damage_source_on_heads": counters_to_damage_source_on_heads,  # v0.81
}


# ---------------------------------------------------------------- きぜつの判定（同時のきぜつ・任意の効果）・きぜつの処理（写し）


def knocked_out(state: GameState, forced: set[int] | frozenset[int] = frozenset()) -> list[tuple[int, PokemonInPlay]]:
    """HP 以上のダメージの場のポケモン（番でないプレイヤー → 番のプレイヤー、それぞれバトル場 → ベンチ。v0.13 と同じ順番）。v0.31: ``forced``
    （ダメージによらず「きぜつ」するポケモンの番号。「みちづれ」）も同じ順番で含める。"""
    current = state.current_player
    return [
        (owner, pokemon)
        for owner in (1 - current, current)
        for pokemon in state.players[owner].in_play()
        if pokemon.pokemon_id in forced or (not state.is_face_down(pokemon) and pokemon.damage >= hp_of(state, pokemon))  # v0.67: うらのカードはダメージなし
    ]


def knocked(res: Resolution) -> list[tuple[int, PokemonInPlay]]:
    """この解決で「きぜつ」するポケモン（HP 以上のダメージと、``res.forced``。v0.31）。"""
    return knocked_out(res.state, res.forced)


def check_simultaneous(res: Resolution) -> None:
    """HP 以上のポケモンの「HP 以上になった枠」が分かれていれば、同時のきぜつか（p.324）が決まらない場合として止める。

    同じ枠（1 つのワザ）の中のきぜつは同時（p.324。CONFIRMED）。分かれる枠に返す効果の枠（またはその中の枠）があれば W24・S37、
    特殊能力のダメージの枠があれば C18。記録のないポケモン（前のコマンドで HP 以上になった。決定のあと）は比べない。"""
    frames = {res.knocked_by[pokemon.pokemon_id] for _, pokemon in knocked(res) if pokemon.pokemon_id in res.knocked_by}
    if len(frames) < 2:
        return
    involved = {frame.id: frame for frame_id in frames for frame in res.ancestors(frame_id)}
    for kind, key, error in ((FrameKind.RETALIATION, "retaliation_double_knockout", _retaliation_error),
                             (FrameKind.POWER_DAMAGE, "counterattack_double_knockout", _counterattack_error)):
        found = [frame for frame in involved.values() if frame.kind is kind]
        if found:
            raise res.question(key, f"枠 {sorted(frames)}", error(res, res.frames[min(f.id for f in found)]))
    raise RuntimeError(f"原因の枠が分かれたきぜつ（枠 {sorted(frames)}）の問いが questions にない（エンジンの不具合）")


def _damage_target(res: Resolution, fs: FrameState) -> int:
    """返す効果・特殊能力のダメージの枠がダメージを与えた相手（起こした枠の、ダメージを与えたポケモン）。"""
    return res.frames[fs.frame.parent].frame.source_pid


def _retaliation_error(res: Resolution, fs: FrameState):
    """W24・S37 の理由の文（v0.13 と同じ文。``effects.retaliation_double_knockout_error``）。返すダメージは、この枠でのせた最終ダメージ。"""
    target = _damage_target(res, fs)
    if fs.origin is None or target not in fs.applied:
        return None  # 理由の文の値がない（questions の表の文を使う）
    return retaliation_double_knockout_error(fs.frame.source_pid, fs.origin.implementation, fs.applied[target], target, res.state)


def _counterattack_error(res: Resolution, fs: FrameState):
    """C18 の理由の文（v0.13 と同じ文。``effects.counterattack_double_knockout_error``）。"""
    target = _damage_target(res, fs)
    if target not in fs.applied:
        return None  # 理由の文の値がない（questions の表の文を使う）
    # v0.17b: 理由の文に、ダメージを与えた特殊能力の名前とページ（はんげきは v0.16 までと同じ文）
    return counterattack_double_knockout_error(fs.frame.source_pid, fs.applied[target], target, *power_name_and_page(res.state, fs.origin.power_key))


def ko_prevention_offers(res: Resolution) -> list[tuple[int, PokemonInPlay, C.EffectInstance]]:
    """きぜつの判定の窓: 任意の効果（こんじょう）の候補（v0.13 の ``_ko_prevention_offer`` と同じ答え）。"""
    state = res.state
    offers = []
    for owner, pokemon in knocked(res):
        for instance in C.in_window(state, Window.KO_CHECK, owner, pokemon, res.catalog):
            if instance.definition.timing is not C.Timing.OFFER or instance.definition.decision_kind != KO_PREVENTION:
                continue  # v0.61: ［ファイナルビーム］（KNOCK_OUT_POWER）は knock_out_power_offers
            able = res.ko_prevention_able.get(pokemon.pokemon_id)
            if able is None:
                if owner == state.current_player:
                    break  # 相手のワザのダメージで HP 以上になったのではない（G4・G5）
                raise RuntimeError(f"任意の効果を持つポケモン {pokemon.pokemon_id} が HP 以上なのに、ダメージを受けたときの写しがない（エンジンの不具合）")
            if able and not C.offer_stopped(state, instance, pokemon):
                offers.append((owner, pokemon, instance))
                res.trace.record(CandidateFound(Window.KO_CHECK, instance.name, pokemon.pokemon_id, None))
            break
    if len(offers) > 1:
        raise res.question("multiple_ko_prevention", f"{[o[1].pokemon_id for o in offers]}")
    return offers


def ko_cause(res: Resolution, pokemon_id: int) -> tuple[int, int, bool] | None:
    """HP 以上になった場のポケモンのきぜつの原因（v0.61）: (原因の枠のプレイヤー, ダメージを与えたポケモンの番号, ワザの分類の枠か)。この解決の枠（``knocked_by``）か、決定を
    またいで運んだ値（``ko_carried``）。どちらもなければ None。"""
    if pokemon_id in res.knocked_by:
        frame = res.frames[res.knocked_by[pokemon_id]].frame
        return frame.player, frame.source_pid, frame.damage_class is DamageClass.ATTACK
    return res.ko_carried.get(pokemon_id)


def knock_out_power_offers(res: Resolution) -> list[tuple[int, PokemonInPlay, C.EffectInstance, int | None]]:
    """きぜつの判定の窓: 相手のワザによって「きぜつ」する時に使えるダメージを与える特殊能力（［ファイナルビーム］。``KNOCK_OUT_POWER``）の候補 (持ち主, ポケモン, 効果,
    「きぜつ」させたポケモンの番号)（v0.61）。

    - 原因の枠がワザの分類（ワザ・返す効果のダメージ・ワザでのせたダメージカウンター）で、そのプレイヤーが持ち主の相手。特殊能力のダメージ・こんらん・自分のワザでは使えない
    - きぜつの判定の時点でねむり・マヒ・こんらんでない（「状態のまま「きぜつ」する時」）、かがくへんかガス・まきちらせ!ベトベトガス・ショックアイでない（``offer_stopped``）
    - 「きぜつ」させたポケモンが場にいる（いなければダメージを与える相手がいない）
    - 「みちづれ」で「きぜつ」するポケモンは原因の枠がない（「きぜつ」させたポケモンは None。呼ぶ側が HC2 と同じ問いで止める）"""
    state = res.state
    offers = []
    for owner, pokemon in knocked(res):
        for instance in C.in_window(state, Window.KO_CHECK, owner, pokemon, res.catalog):
            if instance.definition.decision_kind != KNOCK_OUT_POWER:
                continue
            if C.blocked_by_status(instance, pokemon) or C.offer_stopped(state, instance, pokemon):
                break
            if pokemon.pokemon_id in res.forced and pokemon.pokemon_id not in res.knocked_by:
                offers.append((owner, pokemon, instance, None))
                break
            cause = ko_cause(res, pokemon.pokemon_id)
            if cause is None or not cause[2] or cause[0] == owner:
                break
            located = state.find_pokemon(cause[1])
            if located is None:
                break
            offers.append((owner, pokemon, instance, cause[1]))
            res.trace.record(CandidateFound(Window.KO_CHECK, instance.name, pokemon.pokemon_id, None))
            break
    return offers


def focus_band_offers(res: Resolution) -> list[tuple[int, PokemonInPlay, Any, Any]]:
    """v0.81: きぜつの判定の窓で、きあいのハチマキがはたらく候補 (持ち主, ポケモン, ついているカード, 実装)。相手のワザの分類のダメージで HP 以上になった（``res.damage_ko``）
    ポケモンで、きあいのハチマキがついているもの。"""
    found = []
    for owner, pokemon in knocked(res):
        band = focus_band_of(res, pokemon)
        if band is not None:
            found.append((owner, pokemon, band[0], band[1]))
            res.trace.record(CandidateFound(Window.KO_CHECK, "focus_band", pokemon.pokemon_id, None))
    return found


def exp_all_offers(res: Resolution) -> list[tuple[int, PokemonInPlay, PokemonInPlay, Any]]:
    """v0.81: きぜつの判定の窓で、学習装置を使うかを聞く候補 (持ち主, きぜつする対戦ポケモン, 学習装置をつけたポケモン, ついているカード)。

    - 相手の番に（持ち主が番でないプレイヤー）、持ち主の対戦ポケモン（バトル場）が、相手のワザの分類のダメージで HP 以上になった（``res.damage_ko``）
    - 学習装置をつけたポケモンは、その対戦ポケモンと別で、同じ判定できぜつしない（つけ替えても結果が変わらないので聞かない。実装上の読み方）
    - 対戦ポケモンに、選べるエネルギーカード（基本エネルギーカード・レインボーエネルギー）がある（なければ選ぶものがないので聞かない）"""
    state = res.state
    gone = knocked(res)
    gone_ids = {pokemon.pokemon_id for _, pokemon in gone}
    found = []
    for owner, pokemon in gone:
        cause = res.damage_ko.get(pokemon.pokemon_id)
        if owner == state.current_player or state.players[owner].active is not pokemon or cause is None or cause[0] == owner:
            continue
        if not exp_all_options(state, pokemon):
            continue
        for holder in state.players[owner].in_play():
            if holder is pokemon or holder.pokemon_id in gone_ids:
                continue
            tool = E.tool_effect_of(state, holder, E.ExpAll)
            if tool is not None:
                found.append((owner, pokemon, holder, tool[0]))
                res.trace.record(CandidateFound(Window.KO_CHECK, "exp_all", holder.pokemon_id, None))
    return found


def exp_all_options(state: GameState, pokemon: PokemonInPlay) -> tuple[int, ...]:
    """v0.81: 学習装置でつけ替えるのを選べるカード（ついている順）: 基本エネルギーカードと、場のレインボーエネルギー（「基本エネルギーカード」に当たるかが決まらない。RB3）。"""
    rainbow = set(E.rainbow_cards_attached(state, [pokemon]))
    return tuple(uid for uid in pokemon.energy if state.card_def(uid).is_basic_energy or uid in rainbow)


def exp_all_unresolved(state: GameState, active: PokemonInPlay, holder: PokemonInPlay) -> tuple[tuple[int, ...], str | None, str | None]:
    """v0.81: 学習装置の決定のうち、選ぶと止めるカード・停止コード・理由（つけ替える先がクリスタルビームの効果を受けている（CB1）・レインボーエネルギー（RB3））。"""
    options = exp_all_options(state, active)
    if E.energy_attach_block(state, holder) is not None:
        error = E.attach_block_scope_error(holder, "学習装置のつけ替え")
        return options, error.code, error.message
    rainbow = tuple(uid for uid in options if uid in set(E.rainbow_cards_attached(state, [active])))
    if rainbow:
        error = E.rainbow_basic_error(rainbow)
        return rainbow, error.code, error.message
    return (), None, None


def knock_out_beam_problem(res: Resolution, owner: int, pokemon: PokemonInPlay, instance: C.EffectInstance, source_id: int) -> tuple[str, str] | None:
    """［ファイナルビーム］を使うを選んだときに止める理由（v0.61）: 数え方・弱点・抵抗力（RB1・BZ2・Z9。``effects.BeamOnKnockOut.use_problem``）と、ダメージで「きぜつ」させた
    ポケモンもきぜつし、どちらのきぜつが先かで勝ち負けが変わる場合（C18 と同じ問い。同時のきぜつかが決まらない。勝ち負けが決まらなければ、どちらの読み方でもサイドを取る順番・
    バトル場に出す順番は同じなので、同じきぜつの処理で扱う）。"""
    state = res.state
    source_owner, source = state.find_pokemon(source_id)
    effect = instance.implementation
    problem = effect.use_problem(state, pokemon, source)
    if problem is not None:
        return problem
    amount, _ = received_power_damage(state, source_owner, source, pokemon, effect.energy_count(state, pokemon) * effect.per)
    if amount <= 0 or source.damage + amount < hp_of(state, source):
        return None
    gone = knocked(res) + [(source_owner, source)]
    taken = {player: sum(1 for o, p in gone if o != player and E.counts_as_knockout(state, p)) for player in (0, 1)}
    ends = [(taken[player] and taken[player] >= len(state.players[player].prizes))
            or not [p for p in state.players[player].in_play() if all(p is not k for _, k in gone)] for player in (0, 1)]
    if any(ends):
        return ("UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT",
                (f"［ファイナルビーム］のダメージ {amount} でポケモン {source_id} もきぜつする: ワザによるきぜつと、それがはたらかせた特殊能力のダメージによるきぜつが"
                 "「同時に「きぜつ」した」ことになるか（p.324）は決められず、どちらのきぜつを先に処理するかで勝ち負けが変わる（C18 と同じ問い）"))
    return None


def capture_post_knockout(res: Resolution, knocked: list[tuple[int, PokemonInPlay]], *, record: bool = True) -> tuple[tuple[int, int, str, int], ...]:
    """きぜつの処理の窓（トラッシュの前）: きぜつしたときに使える効果（ふしちょう）を使えるかを、きぜつするときの状態で写す
    （v0.13 の ``_post_knockout_candidates`` と同じ答え）。

    v0.31: ``record`` が False なら、記録（窓・候補）を残さずに、問い（P19・P32）に当たるかだけを確かめる（ワザのあとのきぜつの判定の窓で、
    先読みの範囲の中で確かめるため。``flow._finish_attack``）。"""
    state = res.state
    if record:
        res.trace.record(WindowOpened(Window.KO_PROCESS, None))
    knocked_ids = {pokemon.pokemon_id for _, pokemon in knocked}
    candidates = []
    for owner, pokemon in knocked:
        for instance in C.in_window(state, Window.KO_PROCESS, owner, pokemon, res.catalog):
            if instance.definition.timing is not C.Timing.OFFER:
                continue
            if C.blocked_by_status(instance, pokemon):
                break  # ねむり・マヒ・こんらんのまま「きぜつ」する（P13〜P15）
            gas = C.suppressors(state, instance)
            tower = E.discard_to_hand_suppressor(state)
            towered = tower is not None and getattr(instance.implementation, "discard_to_hand_only", False)
            if gas and all(pid in knocked_ids for pid in gas) and not towered:
                raise res.question("post_knockout_gas_source_knocked", f"{pokemon.pokemon_id} と {gas}")
            # v0.75: ポケモンタワーで効果が消える特殊能力（ふしちょう）は、ガスの発生源がいっしょにきぜつしても、ガスで消えていても消えていなくても
            # 使っても状態が同じなので P19 に当たらず、機会を出さない（P19 の問いそのものは変えない。タワーがなければ今までどおり止める）
            if gas or C.offer_stopped(state, instance, pokemon):
                break  # v0.59: まきちらせ!ベトベトガス・「ショックアイ」（きぜつするときの状態で決める。P13〜P18 と同じ時点）
            if towered:
                # v0.74: ポケモンタワーで、ふしちょう（トラッシュから手札に加える。CR-PHOENIX-RETURN）の効果が消える。使っても状態は同じなので、機会を出さない
                # （きぜつ・トラッシュ・サイドは変えない）
                if record:
                    E.log_discard_to_hand_suppressed(state, owner, tower, power=str(instance.power_key), card=pokemon.card)
                break
            candidates.append((owner, pokemon.card, instance.power_key.card_id, instance.power_key.power_index))
            if record:
                res.trace.record(CandidateFound(Window.KO_PROCESS, instance.name, pokemon.pokemon_id, None))
            break
    if len(candidates) > 1:
        raise res.question("multiple_post_knockout", f"{candidates}")
    return tuple(candidates)

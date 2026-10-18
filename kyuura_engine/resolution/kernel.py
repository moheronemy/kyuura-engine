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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from ..coins import CoinSide, flip_coins
from ..damage import ADD, HALVE_DOWN, HALVE_UP, MULTIPLY, SET, SET_IF_AT_LEAST, ZERO_IF_AT_LEAST, ZERO_IF_BELOW, DamageOrderRequired
from ..effects import (
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
from ..persistent import effect_attack_card, reduced_damage_to_source
from ..state import RETALIATION_FIXED

from . import catalog as C
from .events import (
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
                 dry_run: bool = False, oracle: Any = None, on_horizon: Callable[[], None] | None = None):
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
    """ダメージで HP 以上になったら、その枠を記録する（きぜつの原因。4 章）。"""
    hp = hp_of(res.state, pokemon)
    if before < hp <= pokemon.damage:
        res.knocked_by[pokemon.pokemon_id] = fs.frame.id
        res.trace.record(KnockedOutRecorded(pokemon.pokemon_id, fs.frame.id))


# ---------------------------------------------------------------- ダメージの要素（窓: 適用の前 → 受けるとき → 適用 → 受けたとき）


def first_void(res: Resolution, owner: int, pokemon: PokemonInPlay, window: Window = Window.BEFORE_DAMAGE) -> C.EffectInstance | None:
    """受けるポケモンのダメージの要素を無効にする効果（「ダメージを受けない」状態。かたまる）のうち、今はたらいているもの。v0.31: ``window`` に
    ``Window.BEFORE_EFFECT`` を渡すと、効果の要素を無効にする効果（「ワザをうけない」状態。バリアー）。"""
    for instance in C.in_window(res.state, window, owner, pokemon, res.catalog):
        if instance.definition.timing is C.Timing.VOID and C.working(res.state, instance, pokemon):
            return instance
    return None


def receiver_of(res: Resolution, fs: FrameState, target: str, pokemon_id: int | None = None) -> tuple[int, PokemonInPlay]:
    state = res.state
    if target == OPPONENT_ACTIVE:
        return 1 - fs.frame.player, state.players[1 - fs.frame.player].active
    if target == SELF:
        return fs.frame.player, state.find_pokemon(fs.frame.source_pid)[1]
    if target in (OPPONENT_BENCH, SELF_BENCH):
        # v0.31: 相手の控えポケモン（ワザの説明が選ばせる・決める場のポケモンの番号）。v0.33: 自分の控えポケモン（タケシのディグダの「ミニじしん」）
        side = 1 - fs.frame.player if target == OPPONENT_BENCH else fs.frame.player
        found = next((p for p in state.players[side].bench if p.pokemon_id == pokemon_id), None)
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
    except DamageOrderRequired:
        return False
    return False


def deal_damage(res: Resolution, fs: FrameState, target: str, base: int, *, log_extra: dict | None = None, pokemon_id: int | None = None,
                weakness_resistance: bool = True, orders: dict[int, tuple[int, ...]] | None = None,
                order_decision: bool = False, resistance: bool = True) -> DamageResult:
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
    しきい値)）を残す。"""
    state = res.state
    frame = fs.frame
    _, attacker = state.find_pokemon(frame.source_pid)
    receiver_player, receiver = receiver_of(res, fs, target, pokemon_id)
    res.trace.record(DamageProposal(frame.id, receiver.pokemon_id, receiver_player, target, base))
    res.trace.record(WindowOpened(Window.BEFORE_DAMAGE, frame.id))
    void = first_void(res, receiver_player, receiver)
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
        return DamageResult(target, receiver_player, receiver.pokemon_id, True, None, receiver.damage >= hp_of(state, receiver))
    if target in BENCH_TARGETS:
        cry = reduced_damage_to_source(state, attacker)
        if cry is not None and cry.source_card == receiver.card:
            # v0.34: 「なきつく」を受けたポケモンのワザが、効果を与えたポケモン（「このカード」）が控えにいるときにダメージを与える。説明の「このカードに
            # ワザを使う時」に控えポケモンへのダメージを含むかは決められない（NK5）
            raise res.question("reduced_damage_bench_target", f"ポケモン {attacker.pokemon_id} → 控えのポケモン {receiver.pokemon_id}")
    modifiers = attack_damage_modifiers(state, attacker, receiver, attack=frame.attack_key, bench=target in BENCH_TARGETS, attack_status=res.attack_status)
    if res.stadium_coin is not None and res.stadium_coin[1] and target == OPPONENT_ACTIVE and frame.kind is FrameKind.ATTACK:
        # v0.57: クチバシティジムの「おもて」（そのワザによって相手の対戦ポケモンに与えるダメージは「+10」。p.321 の 6 段階。控えへのダメージ・返す効果のダメージは
        # そのまま）
        modifiers = [*modifiers, stadium_coin_modifier(state, res.stadium_coin[0])]
    if frame.kind is FrameKind.RETALIATION:
        calming_retaliation_question(res, fs, attacker, receiver, base, target, weakness_resistance, resistance)
    try:
        # v0.48: ワザを使うポケモン・受けるポケモンの今有効な最大HP・タイプ（色）・弱点・抵抗力（``effects.definition_views``。テクスチャー・［へんしょく］）。色の読み方
        # （VS1）が 2 つあり、読み方で計算の結果が変わるなら止める（変わらなければ、読み方が 1 つのときと同じ計算）
        calc = same_for_type_readings(state, (attacker, receiver), lambda views: calculate_with_stadium(state,
            base, views[0], views[1], modifiers, weakness_resistance=weakness_resistance, orders=orders, resistance=resistance))
    except TypeReadingsDiffer as differ:
        raise type_question(res, differ, f"ワザ {frame.attack_key} のダメージの計算（ワザを使うポケモンの色と受けるポケモンの弱点・抵抗力）") from None
    except DamageOrderRequired as need:
        # v0.35: p.321 の同じ段階に、順番によって結果が変わる効果が重なった（「つるぎのまい」・「きあいだめ」と「なきつく」など）。計算の順番は
        # DAMAGE_STEP_CHOOSER のプレイヤーが決める（p.321。SC15）。決定を出せる呼ぶ側（ダメージの要素）に返す。出せない呼ぶ側では v0.34 と同じ問いで止める
        if order_decision:
            raise
        raise res.question("damage_step_order", f"ポケモン {attacker.pokemon_id}・{need.step} 段階の効果 {[m.label for m in need.modifiers]}") from None
    if target == SELF:
        trainer_self_bonus_question(res, attacker, receiver, base, modifiers, calc.final, weakness_resistance, orders, resistance)
    if calc.final > 0 and not reaches(res, fs, receiver_player, receiver, DAMAGE_ELEMENT, amount=calc.final):
        fs.evaded[receiver.pokemon_id] = calc.final
        res.trace.record(DamageEvaded(frame.id, receiver.pokemon_id, calc.final))
        return DamageResult(target, receiver_player, receiver.pokemon_id, False, None, receiver.damage >= hp_of(state, receiver), evaded=True)
    deferred: list[Deferred] = []
    by_opponent = receiver_player != frame.player
    if calc.final > 0:
        res.trace.record(WindowOpened(Window.DAMAGE_RECEIVING, frame.id))
        deferred = receiving(res, fs, receiver_player, receiver, calc.final)
    before = receiver.damage
    receiver.damage += calc.final
    fs.applied[receiver.pokemon_id] = calc.final
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
    if orders:
        # v0.35: 順番の決定で選んだ計算の順番（(段階, その段階の変更効果の名前を計算した順に)）
        extra["step_orders"] = tuple((step, tuple(m.label for m in calc.modifiers if m.step == step)) for step in sorted(orders))
    if calc.stopped_after_step_2:
        extra["stopped_after_step_2"] = True
    if target != OPPONENT_ACTIVE:
        extra.update(target=target, pokemon_id=receiver.pokemon_id, effect=str(frame.attack_key))
    if not weakness_resistance:
        extra["ignore_weakness_resistance"] = True  # v0.31
    elif not resistance:
        extra["ignore_resistance"] = True  # v0.45
    if log_extra:
        extra.update(log_extra)
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
    res.trace.record(DamageApplied(frame.id, frame.damage_class, frame.source_pid, receiver.pokemon_id, receiver_player, calc.final,
                                   before, receiver.damage, by_opponent))
    track_ko(res, fs, receiver, before)
    fs.pending.extend(deferred)
    if target == OPPONENT_ACTIVE and calc.final > 0:
        trainer_poison_after_damage(res, attacker, receiver_player, receiver)
    return DamageResult(target, receiver_player, receiver.pokemon_id, False, calc.final, receiver.damage >= hp_of(state, receiver))


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


def trainer_poison_after_damage(res: Resolution, attacker: PokemonInPlay, owner: int, receiver: PokemonInPlay) -> None:
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
    if receiver.damage >= max_hp(state, receiver):
        for instance in C.in_window(state, Window.KO_CHECK, owner, receiver, res.catalog):
            if instance.definition.timing is C.Timing.OFFER and res.ko_prevention_able.get(receiver.pokemon_id) and not C.suppressors(state, instance):
                raise res.question("ko_prevention_attack_effect", f"ポケモン {receiver.pokemon_id}（トレーナー「{state.card_def(records[0].source_card).name_ja}」のどく）")
        return
    poison(state, owner, receiver, effect=records[0].card_id)
    if receiver.conditions.poison is not None:
        res.trainer_poisoned.add(receiver.pokemon_id)


def calming_retaliation_question(res: Resolution, fs: FrameState, attacker: PokemonInPlay, receiver: PokemonInPlay, base: int, target: str,
                                 weakness_resistance: bool, resistance: bool) -> None:
    """返す効果のダメージ（ほのおのかべ・こうらがえし・クロスカウンター。前の番のワザの効果）に、ワザが使われた時の特殊状態で決める常にはたらく特殊能力
    （［くつろぐかおり］の「ワザが使われた時、すでに…」）が当てはまりうるとき（v0.46。CP1）。返すダメージは「こうらがえし」などのワザによるダメージ
    （GR-2000-P321-ATTACK-DAMAGE）だが、「ワザが使われた時」が返す効果を与えた前の番のワザか、きっかけになったこの番のワザかは決まらず、前の番のワザのときの
    特殊状態は記録していない。場所・かがくへんかガスの条件を満たす特殊能力があり、特殊状態によって当てはめるかどうかで最終ダメージ（または順番の決定の要否）が
    変わるなら止める（問い ``calming_retaliation``）。変わらなければ（半分にしても同じ数・特殊能力がない）止めない。"""
    from ..effects import status_at_attack_powers

    state = res.state
    if not status_at_attack_powers(state):
        return
    every = frozenset(p.pokemon_id for player in state.players for p in player.in_play())
    # v0.48: 色の読み方（VS1）が 2 つあるポケモンは、読み方の組ごとに比べる（どれかの組で当てはめるかどうかで変われば止める。読み方の違いそのものは deal_damage が VS1 で見る）
    readings = [(a, r) for a in definition_views(state, attacker) for r in definition_views(state, receiver)]
    by_reading: list[set] = [set() for _ in readings]
    for snapshot in (frozenset(), every):  # 当てはめる読み方・当てはめない読み方
        modifiers = attack_damage_modifiers(state, attacker, receiver, attack=fs.frame.attack_key, bench=target in BENCH_TARGETS, attack_status=snapshot)
        for outcomes, (attacker_def, receiver_def) in zip(by_reading, readings):
            try:
                calc = calculate_with_stadium(state, base, attacker_def, receiver_def, modifiers, weakness_resistance=weakness_resistance,
                                               resistance=resistance)
                outcomes.add(calc.final)
            except DamageOrderRequired:
                outcomes.add(None)
    if any(len(outcomes) > 1 for outcomes in by_reading):
        raise res.question("calming_retaliation", f"返すダメージ {base}（ポケモン {attacker.pokemon_id} → ポケモン {receiver.pokemon_id}）")


def receiving(res: Resolution, fs: FrameState, owner: int, pokemon: PokemonInPlay, received: int) -> list[Deferred]:
    """「ダメージを受けるとき」の窓: 受けるポケモンの効果のうち、この枠のダメージの分類・相手のワザかで候補になるものを集める。

    - 送る効果（``Timing.DEFER``。はんげき・返す効果）は、受けるときの状態ではたらいていれば候補（特殊状態は「すでに」の時点。
      ガス・はたらく番も今）。
    - 任意の効果（``Timing.OFFER``。こんじょう）は、受けるときの特殊状態を写す（ガスはきぜつの判定の時点で見る。v0.13 と同じ）。
    """
    state = res.state
    frame = fs.frame
    found: list[Deferred] = []
    for instance in C.in_window(state, Window.DAMAGE_RECEIVING, owner, pokemon, res.catalog):
        definition = instance.definition
        if frame.damage_class not in definition.trigger_classes:
            continue
        if definition.by_opponent and owner == frame.player:
            continue
        if definition.active_only and state.players[owner].active is not pokemon:
            continue  # v0.42: バトル場で受けたときだけ（ぼうぎょかふん）
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
    if element != DAMAGE_ELEMENT:
        # v0.31: 効果の要素を無効にする効果（「ワザをうけない」状態。バリアー）。「とうめい」より先（ダメージの要素の無効（first_void）と同じ順番）
        void = first_void(res, owner, pokemon, Window.BEFORE_EFFECT)
        if void is not None:
            state.add_event("effect_prevented", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, effect=str(frame.attack_key),
                            element=element, persistent_effect=void.implementation.kind, source_card=void.implementation.source_card)
            res.trace.record(DamageVoided(frame.id, pokemon.pokemon_id, void.name))
            return False
    memo = fs.reception.get(pokemon.pokemon_id)
    if memo is None:
        instance = None
        for candidate in C.in_window(state, window, owner, pokemon, res.catalog):
            if candidate.definition.timing is C.Timing.REPLACE and C.working(state, candidate, pokemon):
                instance = candidate
                break
        if instance is None:
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
    return memo


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


ACTIONS: dict[str, Callable[[Resolution, FrameState, Deferred], None]] = {
    "power_damage_to_damage_source": power_damage_to_damage_source,
    "attack_damage_to_damage_source": attack_damage_to_damage_source,
    "power_confusion_to_damage_source": power_confusion_to_damage_source,  # v0.42
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
        if pokemon.damage >= hp_of(state, pokemon) or pokemon.pokemon_id in forced
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
            if instance.definition.timing is not C.Timing.OFFER:
                continue
            able = res.ko_prevention_able.get(pokemon.pokemon_id)
            if able is None:
                if owner == state.current_player:
                    break  # 相手のワザのダメージで HP 以上になったのではない（G4・G5）
                raise RuntimeError(f"任意の効果を持つポケモン {pokemon.pokemon_id} が HP 以上なのに、ダメージを受けたときの写しがない（エンジンの不具合）")
            if able and not C.suppressors(state, instance):
                offers.append((owner, pokemon, instance))
                res.trace.record(CandidateFound(Window.KO_CHECK, instance.name, pokemon.pokemon_id, None))
            break
    if len(offers) > 1:
        raise res.question("multiple_ko_prevention", f"{[o[1].pokemon_id for o in offers]}")
    return offers


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
            if gas and all(pid in knocked_ids for pid in gas):
                raise res.question("post_knockout_gas_source_knocked", f"{pokemon.pokemon_id} と {gas}")
            if gas:
                break
            candidates.append((owner, pokemon.card, instance.power_key.card_id, instance.power_key.power_index))
            if record:
                res.trace.record(CandidateFound(Window.KO_PROCESS, instance.name, pokemon.pokemon_id, None))
            break
    if len(candidates) > 1:
        raise res.question("multiple_post_knockout", f"{candidates}")
    return tuple(candidates)

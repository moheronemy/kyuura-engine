"""対戦の進行（公式ルール 2000.02.14版）。

使い方::

    state = new_game(deck0, deck1, seed=1)
    state = apply_command(state, PlaceStartingPokemon(player=0, active=..., bench=(...)))
    ...

- ``apply_command`` は渡された状態を変えず、新しい状態を返します。操作が不正なら例外を投げ、
  渡した状態はそのまま使えます。
- ``new_game`` と ``apply_command`` は、返す状態を必ず ``check_invariants`` で確かめます。
  カードの保存則などが破れていたら、状態を返さずに ``StateIntegrityError`` を投げます。
- 乱数（山札を切る・コインを投げる（v0.2d））は ``seed`` から作った乱数だけを使います。同じデッキ・
  同じ seed・同じ操作の列なら、同じ結果になります。コインの結果を操作で指定する方法はありません。
- ジャンケンの結果は外から受け取ります（``ReportJankenResult``）。

ページ番号は『ポケモンカードオフィシャルブック2000』[P43] の公式ルールのノンブルです。
"""

from __future__ import annotations

import dataclasses
import random
from typing import Callable, Sequence

from .cards import EVOLUTION_STAGES, CardPool, EnergyType, load_card_pool
from .conditions import (
    RETREAT,
    clear_special_conditions,
    paralysis_recovery_turn,
)
from .commands import (
    UNSUPPORTED_COMMANDS,
    check_command_fields,
    AttachEnergy,
    DiscardFromPlay,
    DrawMulliganCards,
    EndTurn,
    EvolvePokemon,
    PlaceStartingPokemon,
    PlayBasicToBench,
    PlayTrainer,
    PromoteActive,
    ReportJankenResult,
    ResolveDecision,
    Retreat,
    TakePrize,
    UseAttack,
    UsePokemonPower,
    UseStadium,
    RemoveDisguise,
    RevealFaceDown,
)
from .decisions import (
    ACCEPT_REQUEST,
    BENCH_GUARD,
    FORCED_SWITCH,
    SELECT_COLOR,
    NINJA_TRICK,
    REACTION_SWITCH,
    ENERGY_DRAIN_DISCARD,
    SPLIT_FROM_DECK,
    MAGMA_POOL_ENERGY,
    REACTION_ORDER,
    DISCARD_FROM_HAND,
    EVOLUTION_HEAL,
    SELECT_POKEMON,
    STADIUM_RETURN_BENCH,
    USE_DISCARD_TRAINER,
    push_trainer_decision,
    DAMAGE_STEP_ORDER,
    DAMAGE_REDUCTION,
    ESP_REDO,
    SECRET_PLAN_CARD,
    DECISION_PHASES,
    ENTRY_POWER,
    EXP_ALL_ENERGY,
    KNOCK_OUT_POWER,
    KO_PREVENTION,
    POST_KNOCKOUT_POWER,
    PROMOTE_ACTIVE,
    TAKE_PRIZE,
    phase_for,
)
from .effects import (
    retreat_guards,
    ATTACK_HAND_TRAINER_LOCK,
    BALLOON_BERRY_FAILED_RETREAT_CODE,
    AttachEnergyFromHand,
    DISCARD_BY_RETREAT,
    energy_discard_plan,
    return_discarded_energy,
    BALLOON_BERRY_FAILED_RETREAT_REASON,
    TOOL_RETREAT,
    discard_attached_tool,
    is_pokemon_tool_card,
    tool_effect_of,
    BalloonBerry,
    HAND_LOCK_TRAINERS,
    HAND_TRAINER_LOCK,
    LookDeckTopStadium,
    hand_lock_expiry,
    knocked_by_hp,
    AttackKey,
    AttackUse,
    bench_guard_outside_attack_check,
    discard_on_leaving_active,
    END_TURN,
    SELF_TRAINER_LOCK_TURNS,
    EntryPower,
    PowerKey,
    PowerUse,
    ReturnToHandOnKnockOut,
    TrainerUse,
    UseDiscardTrainer,
    RETREAT_OVERPAY_CODE,
    after_energy_attached,
    attach_from_hand_problem,
    blaine_attach_applies,
    blaine_effect_card,
    blaine_second_attach_error,
    double_attach_check,
    double_attach_rainbow_check,
    energy_attached_from_hand,
    energy_unit_count,
    applicable_entry_power,
    offer_entry_power,
    forced_entry_check, miracle_pending_problem, settle_miracle_energy, energy_attach_target_check, wild_growth_ambiguities, wild_growth_error,
    settle_color_effects,
    ko_prevention_power,
    retreat_cost,
    powers_of,
    POWER_REUSE_AFTER_DEVOLUTION_CODE,
    POWER_REUSE_AFTER_DEVOLUTION_REASON,
    power_reuse_after_devolution,
    power_use_record,
    form_problems,
    shapeshift_slot,
    current_form,
    form_def,
    FORM_TRANSFORM,
    TRANSFORM_POWER_CODE,
    TRANSFORM_POWER_REASON,
    ko_prevention_suppressed,
    PLAY_AS_POKEMON_RETREAT_CODE,
    PLAY_AS_POKEMON_RETREAT_REASON,
    PLAY_AS_POKEMON_SETUP_CODE,
    PLAY_AS_POKEMON_SETUP_REASON,
    play_as_pokemon_effect,
    play_as_pokemon_in_hand,
    trainer_use_blockers,
    TrainerCoinStadium,
    BenchLimitStadium,
    CoinReturnOwnerPokemonStadium,
    COIN_CHOICE_STAGES,
    EvolutionHealStadium,
    apply_evolution_heal,
    bench_entry_damage,
    borrow_unusable_reason,
    offer_evolution_heal,
    stadium_of,
    pay_stadium_trainer_cost,
    stadium_trainer_cost,
    definition_views,
    evolution_hp,
    max_hp,
    max_hp_drop_error,
    max_hp_drops,
    MaxHpOrderUndetermined,
    type_shift_power,
    SCRAM_TIMING_CODE,
    SCRAM_TIMING_REASON,
    SINKHOLE_TIMING_CODE,
    SINKHOLE_TIMING_REASON,
    BeamOnKnockOut,
    received_power_damage,
    retreat_trap_powers,
    scram_restored,
    scram_restored_error,
    scram_slots,
    scram_unsettled,
    scram_working,
)
from .continuous import goop_gas_effects, power_suppressed, suppressors_of
from .deck import deck_problems
from .evolution import DEVOLVED_THIS_TURN_CODE, evolution_block, place_evolution_card, skipped_stage1_basic
from .errors import DeckValidationError, HiddenPropertyRead, IllegalActionError, StateIntegrityError, UnsupportedError
from .persistent import (DISCARD_FROM_PLAY, KNOCK_OUT, SOURCE_LEFT_ACTIVE, cannot_retreat, effect_attack_card, end_turn, energy_attach_blocked, expires_at_turn_start, lasting, leave_lock,
                         powers_stopped, powers_use_prevented, remove_persistent_effects, remove_source_left_effects, require_can_leave, require_source_card_present)
from .rules import RULES_2000_02_14, RuleSet
from .stadiums import bench_has_room, bench_limit, stadium_in_play
from .state import (
    MARKER_AND_COUNTER_KINDS,
    MARKER_COLOR,
    Marker,
    PERSISTENT_EFFECT_TYPES,
    PERIOD_EFFECT_TYPES,
    SOURCE_LEAVES_ACTIVE,
    PeriodLeaveLock,
    ReceivedAttackDamageBonus,
    TRAINER_TURN_EFFECT_KINDS,
    EVOLUTION_BAN,
    OPPONENT_POWER_SUPPRESSION,
    ATTACK_POWER_SUPPRESSION,
    ATTACK_FIELD_POWER_SUPPRESSION,
    TrainerTurnEffect,
    AttackCoinCheck,
    CannotAttackWhileSourceActive,
    CannotRetreat,
    CannotUsePowers,
    PowersStopped,
    BenchProtection,
    CannotAttachEnergy,
    EnergyRole,
    CannotUseAttack,
    CannotUseOwnAttack,
    DamageReduction,
    HalvedDamage,
    DoubledDamage,
    NextTurnAttackDamage,
    ReducedDamageToSource,
    Retaliation,
    TERMINAL_PHASES,
    SET_ASIDE_FACE_DOWN_BENCH,
    SET_ASIDE_HAND,
    SET_ASIDE_KINDS,
    SET_ASIDE_QUIZ,
    SetAsideCards,
    Asleep,
    CardInstance,
    Confused,
    DataSource,
    GameState,
    Halt,
    Paralyzed,
    Phase,
    PlayerState,
    PokemonInPlay,
    Poison,
    SpecialConditions,
    TrainerInUse,
    StadiumInPlay,
    TrainerUseLock,
    ZeroDamageBelow,
    ZeroDamageAtLeast,
    BenchAttackDamageGuard,
    AttackEffectGuard,
    StatusImmunityWhileActive,
    StatusImmunityNextTurn,
    MaxHpSet,
    TailsDamageGuard,
    ResistanceChange,
    TypeShift,
    WeaknessChange,
    freeze_mapping,
    mark_returned_to_bench,
    turn_owner,
)
from .zones import DISGUISE_REVERT, attach_energy_from_hand, designate_face_down, discard_from_play, draw_cards, enter_play, place_stadium, remove_disguise, reveal_face_down, shuffle_deck
from . import zones as _zones
from . import cards as cards_module
from .coins import CoinSide, flip_coins

# v0.15a: v0.13 まで engine.py にあった確認と共通の手続きを、engine.py を読み込まない部品に移した（docs/integration-dependencies-v0.15a.md）。
# 範囲外のコマンドの処理が使う名前を、v0.13 の名前で読み込む（v0.16b でワザ・番の終わりの処理は解決の基盤だけになった）
from .checks import PLAYERS, decision_choices
from .checks import require_not_asleep_or_paralyzed as _require_not_asleep_or_paralyzed
from .checks import require_phase as _require_phase
from .checks import require_player as _require_player
from .checks import require_turn as _require_turn
from .procedures import CONTINUE_TURN, NEXT_TURN
from .procedures import halt as _halt
from .procedures import begin_turn as _begin_turn
from .procedures import confusion_check as _confusion_check
from .history import close_probe, open_probe
from . import resolution  # v0.15b: 効果の解決の基盤（engine.py を読み込まない）
from . import reactions  # v0.86: 手札からつけたエネルギー・進化・場に出したことへの反応と、決定をまたぐ続き
from . import movement  # v0.87: 場の移動（控え → バトル場・バトル場 → ベンチ・手札からの登場）への反応

# PLAYERS（checks）・NEXT_TURN（procedures）は v0.15a で共通の部品に移した（上で読み込む。engine.PLAYERS・engine.NEXT_TURN のまま使える）
# 決定の再開先（v0.16b: 解決の基盤が続ける 5 つと、engine.py が続けるトレーナーの決定）
DECISION_RESUMES = resolution.RESUMES | {"trainer", "power", "stadium", "reaction"}  # v0.42: 宣言して使う特殊能力の途中の決定（"power"）。v0.57: スタジアム（"stadium"）
# 対戦準備の段階（番はまだ始まっていない）
SETUP_PHASES = frozenset({Phase.SETUP_PLACEMENT, Phase.SETUP_MULLIGAN_DRAW, Phase.SETUP_FIRST_PLAYER})


# ---------------------------------------------------------------- 対戦の開始


def new_game(
    deck0: Sequence[str],
    deck1: Sequence[str],
    seed: int,
    *,
    rules: RuleSet = RULES_2000_02_14,
    pool: CardPool | None = None,
) -> GameState:
    """デッキを検査し、山札を切り、手札を 7 枚ずつ配り、切り直しまで済ませた状態を返す（p.308）。

    この後は ``PlaceStartingPokemon`` で両方のプレイヤーがポケモンを出す。
    ``seed`` は 0 以上の整数。切り直しの補償が原文で決められない場合は、``Phase.HALTED`` の状態を返す
    （例外は投げない。``state.phase`` を確かめること）。
    """
    pool = pool or load_card_pool()
    problems = [f"player {p}: {problem}" for p, deck in enumerate((deck0, deck1)) for problem in deck_problems(deck, pool, rules)]
    if problems:
        raise DeckValidationError(problems)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed は整数")
    if seed < 0:
        # random.Random は負の seed を絶対値として扱うので、-5 と 5 が同じ対戦になってしまう
        raise ValueError("seed は 0 以上の整数")

    cards: dict[int, CardInstance] = {}
    players = []
    for owner, deck in enumerate((deck0, deck1)):
        uids = []
        for card_id in deck:
            uid = len(cards)
            cards[uid] = CardInstance(uid=uid, card_id=card_id, owner=owner)
            uids.append(uid)
        players.append(PlayerState(deck=uids))

    used_ids = {c.card_id for c in cards.values()}
    state = GameState(
        rules=rules,
        card_data=DataSource(pool.source["repository"], pool.source["commit"], pool.source["path"]),
        seed=seed,
        rng=random.Random(seed),
        cards=freeze_mapping(cards),
        definitions=freeze_mapping({card_id: pool.get(card_id) for card_id in used_ids}),
        decklists=(tuple(deck0), tuple(deck1)),
        players=players,
        phase=Phase.SETUP_PLACEMENT,
        effects=pool.effects,
    )
    state.add_event("game_created", rules=rules.id, seed=seed, card_data_commit=pool.source["commit"])

    # デッキを切る（自分で切り、相手にも切ってもらう。その結果を乱数 1 回の並べ替えで表す）
    for player in PLAYERS:
        _shuffle_deck(state, player)
    _deal_opening_hands(state)
    _require_integrity(state)
    return state


def _shuffle_deck(state: GameState, player: int) -> None:
    shuffle_deck(state, player)  # v0.22 から zones（カードの効果で切る処理と共通。動き・乱数・ログは同じ）


def _draw(state: GameState, player: int, count: int) -> None:
    draw_cards(state, player, count)


def _hand_has_basic(state: GameState, player: int) -> bool:
    return any(state.card_def(uid).is_basic_pokemon for uid in state.players[player].hand)


def _deal_opening_hands(state: GameState) -> None:
    """手札 7 枚と切り直し（p.308「カードを7枚取る」）。

    - たねポケモンがなかったプレイヤーだけが、手札を見せて切り直す。来るまでくりかえす。
    - 相手は切り直し 1 回ごとに最大 2 枚引ける（サイドを置いた後。``DrawMulliganCards``）。
    - 両方ともたねポケモンがなかった場合は、どちらも引かない。

    両方が同時に切り直したあと、片方だけがさらに切り直した場合（回数が違う場合）に、相手が
    何枚引けるかは原文から決められない（kyuura docs/engine-readiness.md 4章）。その場合は
    推測で決めずに対戦を止める（Phase.HALTED）。
    """
    size = state.rules.opening_hand_size
    dealing = list(PLAYERS)
    for player in dealing:
        _draw(state, player, size)
    rounds: list[tuple[int, ...]] = []
    while True:
        lacking = tuple(p for p in dealing if not _hand_has_basic(state, p))
        if not lacking:
            break
        undecided = [p for p in lacking if play_as_pokemon_in_hand(state, p)]
        if undecided:
            # v0.47: たねポケモンがなく、なにかの化石・ピッピ人形がある手札で、切り直すのか、それを最初のポケモンとして出せるのかは決められない（PF1）。切り直す前に
            # 対戦を止める（v0.1 の切り直しの補償と同じ形。推測で決めない）
            state.phase = Phase.HALTED
            state.halt = Halt(code=PLAY_AS_POKEMON_SETUP_CODE, message=PLAY_AS_POKEMON_SETUP_REASON,
                              references=("P43 p.308", "NEO-2000-OFFICIAL-RULES", "mulligan", "docs/fossil-hidden-info-v0.47.md 3 章"))
            state.mulligan_rounds = tuple(rounds)
            state.add_event("halted", code=state.halt.code, players=tuple(undecided))
            return
        rounds.append(lacking)
        for player in lacking:
            p = state.players[player]
            p.mulligans += 1
            state.add_event("mulligan", player=player, revealed_hand=tuple(p.hand))
            p.deck.extend(p.hand)
            p.hand.clear()
            _shuffle_deck(state, player)
            _draw(state, player, size)
        dealing = list(lacking)
    state.mulligan_rounds = tuple(rounds)

    both_rounds = [r for r in rounds if len(r) == 2]
    single_rounds = [r for r in rounds if len(r) == 1]
    if both_rounds and single_rounds:
        state.phase = Phase.HALTED
        state.halt = Halt(
            code="UNRESOLVED_MULLIGAN_COMPENSATION",
            message=(
                "両方のプレイヤーが同時に切り直したあと、片方だけがさらに切り直した。"
                "この場合に相手が何枚引けるかは公式ルール 2000.02.14版の文面（p.308）から決められないので、v0.1 では対戦を止める。"
            ),
            references=("P43 p.308", "NEO-2000-OFFICIAL-RULES", "mulligan", "kyuura docs/engine-readiness.md 4章"),
        )
        state.add_event("halted", code=state.halt.code, mulligan_rounds=state.mulligan_rounds)
        return
    for (player,) in single_rounds:
        state.players[1 - player].mulligan_draws_remaining += 1


# ---------------------------------------------------------------- コマンドの入口


def apply_command(state: GameState, command) -> GameState:
    """コマンドを処理した新しい状態を返す。渡した ``state`` は変えない。

    - ルール上できない操作: ``IllegalActionError``
    - 未対応の操作・原典で決められない場合・終わった（止めた）対戦への操作: ``UnsupportedError`` /
      ``IllegalActionError``（GAME_OVER）
    - 処理の結果が不変条件を満たさない（エンジンの不具合か、渡した状態が壊れている）: ``StateIntegrityError``

    v0.16b: ワザ・番の終わり・きぜつのあとの決定は、効果の解決の基盤（``kyuura_engine/resolution``）だけが処理する（v0.13 の経路と、
    経路を選ぶ ``Route``・``apply_command_via`` は外した。docs/kernel-consolidation-v0.16b.md）。呼び方・戻り値・例外は変えていない。
    """
    return _apply(state, command, None)


def apply_command_with(state: GameState, command, *, preflight: str = "derived",
                       catalog: resolution.Catalog | None = None) -> GameState:
    """内部の入口（v0.16b。v0.15b の ``apply_command_via`` の、経路の引数のない形）: 解決の設定（宣言の前の先読みの方法 ``preflight``・
    効果の定義の対応表 ``catalog``）を指定してコマンドを処理する。比較・試験用。公開の ``apply_command`` と同じ約束（渡した状態を変えない・
    不変条件で確かめる）。"""
    return _apply(state, command, _context(state, preflight, catalog))


def apply_command_traced(state: GameState, command, *, preflight: str = "derived",
                         catalog: resolution.Catalog | None = None) -> tuple[GameState, resolution.Trace]:
    """内部の入口（v0.15b）: (新しい状態, 解決の記録) を返す。解決の記録（内部のトレース）は状態に保存しない（公開のログとは別のもの）。
    解決の基盤を通らないコマンド（範囲外のコマンド・トレーナーの決定への答え）なら、解決の記録は空。"""
    context = _context(state, preflight, catalog)
    return _apply(state, command, context), context.trace


def _context(state: GameState, preflight: str, catalog: resolution.Catalog | None) -> resolution.Context:
    """解決の設定（コマンドごとに作る。解決の記録はこの中に入る。``state`` はコマンドの入口に渡された状態で、変えない）。"""
    return resolution.Context(original=state, preflight=preflight, catalog=resolution.DEFAULT_CATALOG if catalog is None else catalog)


def _apply(state: GameState, command, context: resolution.Context | None) -> GameState:
    """コマンドの入口（確認・複製・不変条件）。ワザ・番の終わりは解決の基盤（``resolution.handle``）、決定への答えは ``_answer_decision``、
    範囲外のコマンドは ``engine.py`` の処理（``_HANDLERS``）。

    v0.67（docs/secret-plan-preflight-v0.67.md 6 章）: 相手のうらのカード（マチスの秘策）があるとき、このコマンドの処理が相手のうらのカードの本当のカードを使ったら
    （おもてにした・おもてにしたら残るかを見た。``zones.IDENTITY_CONSULTED``）、受け付けるか・拒否の理由が本当のカードによらないように、ありうるカードのすべてで同じ
    コマンドを確かめる（``_identity_independent``）。"""
    try:
        return _apply_checked(state, command, context)
    except HiddenPropertyRead as exc:
        # v0.67（FD1）: 決定への答えが、どの答えでもうらのカードの決まらない項目を読むなら（［へんしん］のメタモンの前にうらのカードしか出せないなど）、答えのない決定を
        # 残さずに、その前の状態で対戦を止める。ほかの答えがあれば、この答えを受け付けないだけ
        if (_zones.IDENTITY_CONSULTED is None and isinstance(command, (TakePrize, PromoteActive, ResolveDecision)) and state.decision is not None
                and not _decision_has_unstopped_answer(state, context)):
            halted = state.clone()
            _halt(halted, Halt(code=exc.code, message=f"どの答え（続け方）でも次の処理になるので、対戦を止める: {exc.message}",
                               references=("docs/secret-plan-preflight-v0.67.md",)))
            _require_integrity(halted)
            return halted
        raise


def _apply_checked(state: GameState, command, context: resolution.Context | None) -> GameState:
    """``_apply`` の本体（v0.67。うらのカードを置きかえて受け付けるかを確かめる）。"""
    acting = _acting_player(state, command)
    if _zones.IDENTITY_CONSULTED is not None or acting is None or not any(
            state.cards[uid].owner != acting for uid in state.face_down_cards):
        return _apply_once(state, command, context)
    saved = _zones.IDENTITY_CONSULTED
    _zones.IDENTITY_CONSULTED = []
    result = error = None
    try:
        result = _apply_once(state, command, context)
    except (IllegalActionError, UnsupportedError) as exc:
        error = exc
    finally:
        consulted = _zones.IDENTITY_CONSULTED
        _zones.IDENTITY_CONSULTED = saved
    if not consulted:
        if error is not None:
            raise error
        return result
    return _identity_independent(state, command, context, acting, result, error)


# v0.68（docs/final-pmcg-cards-v0.68.md 5 章）: 受け付けるかを確かめる処理の回数の上限。ありうるカードは公開の情報（対応しているカードの一覧）から作るので、指定された相手の
# うらのカードが 1 枚なら上限の中におさまり、2 枚以上なら超える（超えたら、受け付けるかを本当のカードによらないものにできないので受け付けない。エンジンの未対応）
_IDENTITY_TRIAL_LIMIT = 512
SECRET_PLAN_IDENTITIES_CODE = "UNSUPPORTED_SECRET_PLAN_IDENTITIES"


def _acting_player(state: GameState, command) -> int | None:
    """コマンドを出したプレイヤー（v0.67。決定への答えは決めるプレイヤー）。ない・決まらないなら None。"""
    player = getattr(command, "player", None)
    return player if player in PLAYERS else None


class _NeedBranch(BaseException):
    """v0.68: 確かめの処理が、まだ割り当てていない相手のうらのカードを指定した（ありうるカードを順に試す）。エンジンの処理が捕まえないように ``BaseException``。"""


class _OpaqueRead(BaseException):
    """v0.68: 確かめの処理が、「たねポケモンでない」とだけ割り当てたうらのカードの、ほかの項目を読んだ（そのカードについては、たねポケモンでないカードをひとつずつ試す）。"""

    def __init__(self, uid: int):
        super().__init__(uid)
        self.uid = uid


_NONBASIC = "?nonbasic"  # v0.68: 「たねポケモン」でない、とだけ決めたカード（トラッシュしたあとに項目を読まなければ、どのカードでも同じ結果）
_UNASSIGNED = "?unassigned"  # v0.68: まだ割り当てていない相手のうらのカード（読めば確かめの不具合）


class _OpaqueDefinition(cards_module.CardDefinition):
    """v0.68: 確かめの状態の、割り当てる前・「たねポケモンでない」とだけ決めたカードの定義。「たねポケモン」かのほかを読むと止まる。"""

    def __getattribute__(self, name: str):
        if name.startswith("_") or name in ("id", "__class__"):
            return super().__getattribute__(name)
        if name == "is_basic_pokemon" and super().__getattribute__("id") == _NONBASIC:
            return False
        raise _OpaqueRead(-1)

    def __eq__(self, other) -> bool:
        return self is other

    def __hash__(self) -> int:
        return id(self)


_OPAQUE = {key: _OpaqueDefinition(id=key, name_ja="", name_en=None, category="trainer", supported=True, unsupported_reasons=())
           for key in (_NONBASIC, _UNASSIGNED)}
_PUBLIC_POOLS: dict[int, object] = {}


def _public_pool(state: GameState):
    """v0.68: 公開の情報だけから決まる、ありうるカードの一覧（対応しているカードの一覧。デッキの中身・山札・手札を使わない）。効果の登録表ごとに 1 度作る。"""
    pool = _PUBLIC_POOLS.get(id(state.effects))
    if pool is None:
        from .cards import load_card_pool, pool_from_extract, read_extract

        default = load_card_pool()
        pool = default if default.effects is state.effects else pool_from_extract(read_extract(), state.effects)
        _PUBLIC_POOLS[id(state.effects)] = pool
    return pool


_IDENTITY_CANDIDATES: dict[int, tuple[str, ...]] = {}


def _behavior_key(pool, card_id: str):
    """v0.69: カードの処理を決めるもの（定義の id・英語の欄を除いたもの、効果の登録表のそのカードの登録）。同じなら、どの処理でも同じに扱われる。"""
    definition = pool.get(card_id)
    effects = pool.effects
    plain = dataclasses.replace(
        definition, id="", name_en=None, energy_text_en=None, trainer_text_en=None,
        attacks=tuple(dataclasses.replace(a, name_en=None, text_en=None) for a in definition.attacks),
        powers=tuple(dataclasses.replace(w, name_en=None, text_en=None) for w in definition.powers))
    entries = (tuple(effects.attack_entry(card_id, a.index) for a in definition.attacks),
               tuple(effects.power_entry(card_id, w.index) for w in definition.powers),
               effects.trainer_entry(card_id), effects.energy_entry(card_id))
    return plain, tuple(tuple(id(e) for e in group) if isinstance(group, tuple) else id(group) for group in entries)


def _identity_candidates(pool) -> tuple[str, ...]:
    """v0.69（docs/equivalent-non-pack-cards-v0.69.md 5 章）: 受け付けるかの確かめで試す、ありうるカード。処理が同じカード（``_behavior_key``。拡張パック以外の商品の
    同じカード ``effects.EQUIVALENT_CARDS`` など）は 1 枚で代表する（どれを割り当てても同じ結果なので、試す回数を対応しているカードの数で増やさない）。代表は、
    写しの表（``EQUIVALENT_CARDS``・``EQUIVALENT_BASIC_ENERGY``）の新しい id でないカード（同じなら id の小さいもの）。公開の情報（対応しているカードの一覧と効果の登録表）だけで決まる"""
    found = _IDENTITY_CANDIDATES.get(id(pool))
    if found is None:
        from .effects import EQUIVALENT_BASIC_ENERGY, EQUIVALENT_CARDS

        classes: dict[object, str] = {}
        for card_id in sorted(pool.playable_ids, key=lambda c: (c in EQUIVALENT_CARDS or c in EQUIVALENT_BASIC_ENERGY, c)):
            classes.setdefault(_behavior_key(pool, card_id), card_id)
        found = tuple(sorted(classes.values()))
        _IDENTITY_CANDIDATES[id(pool)] = found
    return found


class _IdentityOracle:
    """v0.68: 確かめの 1 回ぶんの割り当て。相手のうらのカード（``scope``）が効果の対象として指定された順に、``script`` のカードを割り当てる（同じカードには、複製した
    状態でも同じものを割り当てる）。``script`` を使い切ったら ``_NeedBranch`` で止まる（呼ぶ側が、次に試すカードを足してやり直す）。"""

    def __init__(self, scope: frozenset[int], script: tuple[str, ...]):
        self.scope = scope
        self.script = script
        self.order: list[int] = []
        self.assigned: dict[int, str] = {}

    def assign(self, state: GameState, uid: int) -> None:
        if uid not in self.scope:
            return
        if uid not in self.assigned:
            if len(self.order) >= len(self.script):
                raise _NeedBranch()
            self.order.append(uid)
            self.assigned[uid] = self.script[len(self.order) - 1]
        card_id = self.assigned[uid]
        if state.cards[uid].card_id != card_id:
            from types import MappingProxyType

            cards = dict(state.cards)
            cards[uid] = dataclasses.replace(cards[uid], card_id=card_id)
            state.cards = MappingProxyType(cards)


def _identity_trial_state(state: GameState, scope: frozenset[int]) -> GameState:
    """v0.68: 確かめの状態の複製（返す状態にはしない）。相手のうらのカードを割り当てる前の印にし、ありうるカードの定義を加える。"""
    from types import MappingProxyType

    trial = state.clone()
    cards = dict(trial.cards)
    for uid in scope:
        cards[uid] = dataclasses.replace(cards[uid], card_id=_UNASSIGNED)
    trial.cards = MappingProxyType(cards)
    trial.definitions = MappingProxyType({**_public_pool(state).definitions, **state.definitions, **_OPAQUE})
    return trial


def _identity_independent(state: GameState, command, context: resolution.Context | None, acting: int, result, error):
    """v0.67・v0.68（docs/final-pmcg-cards-v0.68.md 5 章）: 相手（``acting`` の相手）のうらのカードの本当のカードによらず、このコマンドを受け付けるか・同じ理由で拒否するかを
    確かめる。

    v0.67 は、ありうるカードをうらのカードの持ち主のデッキのカード（見えない情報）から作り、組の数の上限で拒否していた（デッキの中身で受け付けるかが変わった）。v0.68 から:

    - ありうるカードは公開の情報（対応しているカードの一覧。``_public_pool``）だけから作る。デッキ・山札・手札の中身は使わない
    - 試すのは、このコマンドが効果の対象として指定した（おもてにした）相手のうらのカードだけ（指定した順に、``zones.IDENTITY_ORACLE`` が割り当てる）。指定するまでの処理は
      うらのカードを読めない（FD1）ので、どのカードを指定するかは公開の情報で決まる
    - 「たねポケモン」でないカードは、おもてにするとトラッシュする。トラッシュしたあとにほかの項目を読まなければ、どのカードでも同じ結果なので 1 回だけ試し
      （``_NONBASIC``）、読んだら、たねポケモンでないカードをひとつずつ試す
    - どの割り当てでも受け付けるなら本当の結果を返し、どれかで拒否するなら、試した順で最初に拒否した割り当ての例外の種類とコードで拒否する（理由の文に、割り当てたカードを
      書かない）。試す回数が上限（``_IDENTITY_TRIAL_LIMIT``）を超えるなら ``UNSUPPORTED_SECRET_PLAN_IDENTITIES``。どちらも、試すカードの一覧が公開の情報だけで決まるので、
      本当のカード・デッキの中身によらない"""
    scope = frozenset(uid for uid in state.face_down_cards if state.cards[uid].owner != acting)
    pool = _public_pool(state)
    candidates = _identity_candidates(pool)
    basics = sorted(card_id for card_id in candidates if pool.get(card_id).is_basic_pokemon)
    nonbasics = sorted(card_id for card_id in candidates if not pool.get(card_id).is_basic_pokemon)
    trials = 0
    pending: list[tuple[str, ...]] = [()]
    saved_consulted, saved_oracle = _zones.IDENTITY_CONSULTED, _zones.IDENTITY_ORACLE
    _zones.IDENTITY_CONSULTED = []  # 確かめのあいだは記録しない（置きかえた状態の処理が、もう一度確かめない）
    try:
        while pending:
            script = pending.pop(0)
            trials += 1
            if trials > _IDENTITY_TRIAL_LIMIT:
                raise UnsupportedError(SECRET_PLAN_IDENTITIES_CODE,
                                       "相手のうらのカードを 2 枚以上、効果の対象にするコマンドは、受け付けるかを本当のカードによらないものにできない（試す回数が上限を超える。"
                                       "エンジンの未対応）")
            oracle = _IdentityOracle(scope, script)
            _zones.IDENTITY_ORACLE = oracle
            trial = _identity_trial_state(state, scope)
            try:
                _apply_once(trial, command, context and _context(trial, context.preflight, context.catalog), verify=False)
            except _NeedBranch:
                pending[0:0] = [script + (card_id,) for card_id in (*basics, _NONBASIC)]
            except _OpaqueRead:
                position = script.index(_NONBASIC) if _NONBASIC in script else None
                if position is None:
                    raise RuntimeError("確かめの処理が、割り当てる前の相手のうらのカードを、効果の対象として指定せずに読んだ（エンジンの不具合）") from None
                pending[0:0] = [script[:position] + (card_id,) + script[position + 1:] for card_id in nonbasics]
            except (IllegalActionError, UnsupportedError) as exc:
                cls = type(exc) if isinstance(exc, IllegalActionError) else UnsupportedError
                raise cls(exc.code, f"相手のうらのカード（マチスの秘策）がありうるカードのどれかのとき、このコマンドは受け付けられない（{exc.code}。本当のカードによらず同じ理由で"
                                    "受け付けない）") from None
    finally:
        _zones.IDENTITY_CONSULTED, _zones.IDENTITY_ORACLE = saved_consulted, saved_oracle
    if error is not None:
        raise RuntimeError(f"本当のカードで拒否したコマンドが、ありうるカードのすべてで受け付けられた（{error.code}。エンジンの不具合）")
    return result


def _apply_once(state: GameState, command, context: resolution.Context | None, *, verify: bool = True) -> GameState:
    """``_apply`` の本体（v0.67 で分けた）。``verify`` が偽なら、最後の不変条件の確かめをしない（うらのカードを置きかえた確かめの状態。カードの組がデッキと違う）。"""
    if isinstance(command, UNSUPPORTED_COMMANDS):
        raise UnsupportedError("UNSUPPORTED_ACTION", f"{type(command).__name__} は未対応")
    handler = _HANDLERS.get(type(command))
    if handler is None:
        raise IllegalActionError("UNKNOWN_COMMAND", f"知らないコマンド {command!r}")
    check_command_fields(command)
    if state.phase is Phase.GAME_OVER:
        raise IllegalActionError("GAME_OVER", "対戦は終わっている")
    if state.phase is Phase.SUDDEN_DEATH:
        raise UnsupportedError("SUDDEN_DEATH_NOT_IMPLEMENTED", "サドン・デス（延長戦）の開始は v0.1 では未実装")
    if state.phase is Phase.HALTED:
        raise UnsupportedError(state.halt.code, state.halt.message)
    new = state.clone()
    if _probes_receipts(state, command):
        open_probe(new)  # v0.62: ワザ以外で受けたこと（番でないプレイヤーの場のポケモンの、このコマンドの前後の比べ。``history``）
    ctx = context if context is not None else _context(state, "derived", None)
    order_stop = None
    try:
        if not _reveal_for_action(new, command, ctx):
            handler(new, command, ctx)
    except MaxHpOrderUndetermined as error:
        # v0.81a（MH2）: 処理の途中で、最大HPを決まった数にする効果と大きくする効果が同時にはたらく状態の最大HPを読んだ（その状態になる）。決められない姿と同じく、
        # このコマンドを受け付けない（答えのない決定は、その前の状態で止める）
        order_stop = (error.code, error.message)
    if order_stop is None:
        close_probe(new)
    if new.energy_roles:
        # v0.59（docs/energy-control-power-suppression-v0.59.md 3 章）: 場のポケモンについていなくなったエネルギーとしての役割の記録（マルマインの［エネエネ］）を消す
        # （ついていないあいだは印刷のポケモンのカード。実装上の判断）
        new.energy_roles = tuple(role for role in new.energy_roles if new.energy_role(role.card) is not None)
    if new.color_effects:
        # v0.88（docs/type-energy-colors-v0.88.md 2 章）: ［せんすい］の対象が場にいなくなった記録を消し、［エナジーコンバーター］のカードが場をはなれたら印を付ける
        settle_color_effects(new)
    if order_stop is None and new.phase not in (Phase.HALTED, Phase.GAME_OVER):
        # v0.85（docs/entry-powers-energy-lifecycle-v0.85.md 5 章）: つけているポケモンが「ひかる」「やさしい」でなくなったミラクルエネルギーをトラッシュする（コマンドの終わり。
        # 効果の途中の決定を待つ間に起こるのはエンジンの未対応。［きせきのかぜ］がはたらいていれば動かさず、MEW1 の決められない状態として受け付けない）
        pending = miracle_pending_problem(new)
        if pending is not None:
            raise UnsupportedError(*pending)
        if new.decision is None:
            settle_miracle_energy(new)
    # v0.49（docs/virtual-attacks-transformation-v0.49.md 5 章・7 章）: このコマンドで、決められない姿（TF1・TF2・DG1。``effects.form_problems``）が新しくできたら、
    # このコマンドを受け付けない。決定への答え・対戦準備の最後（ポケモンを表にする）で、どの答えでもできるなら、その前の状態で対戦を止める（``Phase.HALTED``。
    # 答えのない決定を残さない）
    fresh = order_stop or _fresh_form_problem(state, new)
    if fresh is not None:
        if isinstance(command, ReportJankenResult) or (
                isinstance(command, (TakePrize, PromoteActive, ResolveDecision)) and not _decision_has_unstopped_answer(state, context)):
            halted = state.clone()
            _halt(halted, Halt(code=fresh[0], message=f"どの答え（続け方）でも次の状態になるので、対戦を止める: {fresh[1]}",
                               references=("docs/virtual-attacks-transformation-v0.49.md",)))
            _require_integrity(halted)
            return halted
        raise UnsupportedError(*fresh)
    # v0.48（MH1。docs/effective-pokemon-properties-v0.48.md 5 章）: このコマンドで、ダメージ以外の原因で最大HPが下がり、のっているダメージ以下になった場のポケモンが
    # 残っていれば、きぜつの判定の時点が決まらないので、このコマンドを受け付けない（渡した状態は変えない）。ワザの中で下がったポケモンは、ワザのあとのきぜつの判定で
    # きぜつしている（ここに残らない）。コインの前に確かめるもの（にげる・ポケモンチェック）は、それぞれの処理が先に止める
    drops = max_hp_drops(state, new)
    if drops:
        raise max_hp_drop_error(drops, during_attack=new.decision is not None and new.decision.resume == "attack")
    if new.phase not in (Phase.HALTED, Phase.GAME_OVER):
        # v0.61（SC2。docs/reactive-powers-trainer-damage-v0.61.md 4 章）: このコマンドで、残りHPが「10」のまま消えていた［ずらかる］の力がもどった（なんでもなおし・ポケモン
        # いれかえ・かがくへんかガスのポケモンが場をはなれたなど）なら、このコマンドを受け付けない。コインの結果で変わるもの（にげる・ポケモンチェック・ワザ）は、それぞれの処理が先に止める
        restored = scram_restored(state, new)
        if restored:
            raise scram_restored_error(restored)
        # 残りHPが「10」で力がはたらく［ずらかる］が残っていれば、決まった時点で確かめていない経路（エンジンの不具合）。ワザの途中の決定を待つ間は、決定のあとの時点で確かめる
        if not (new.decision is not None and new.decision.resume == "attack") and scram_unsettled(new):
            raise RuntimeError(f"残りHPが「10」で［ずらかる］の力がはたらくポケモン {scram_unsettled(new)} が残っている（確かめる時点がない経路。エンジンの不具合）")
    if (new.trainer_in_use is not None and new.decision is not None and isinstance(command, (PlayTrainer, ResolveDecision))
            and new.effects.trainer_entry(new.cards[new.trainer_in_use.card].card_id).effect.changes_field):
        # v0.49（docs 7 章）: トレーナーの効果の途中の決定（入れ替える・進化させるトレーナーなど）で、どの答えの続きも受け付けられない状態（決められない姿・MH1）
        # になるなら、このコマンド（使う・前の段階の答え）を受け付けない。答えのない決定を、使用中のトレーナーを残したまま止めない
        dead_end = _trainer_dead_end(state, new, context)
        if dead_end is not None:
            raise UnsupportedError(*dead_end)
    if (new.decision is not None and new.decision.resume == reactions.RESUME and (state.decision is None or state.decision.id != new.decision.id)
            and new.phase not in (Phase.HALTED, Phase.GAME_OVER)):
        # v0.86（docs/entry-energy-evolution-reactions-v0.86.md 2 章）: 反応の決定（順番・使う機会・進化カード・入れ替え）のどの答えも受け付けられない（RA1・RA2 など）なら、答えのない
        # 決定を残さずに、このコマンドを受け付けない
        stop = _reaction_dead_end(new, context)
        if stop is not None:
            raise stop
    if verify:
        _require_integrity(new)
    return new


def _reaction_dead_end(state: GameState, context: resolution.Context | None) -> UnsupportedError | None:
    """v0.86: 反応の決定 ``state.decision`` のすべての答えを状態の複製の上で試し、どれも受け付けられなければ最初の拒否（``UnsupportedError``）を返す。受け付けられる答えがあれば None。"""
    from .resolution.programs import answer_count, iter_answers

    decision = state.decision
    if answer_count(decision) > _ALTERNATIVE_ANSWER_LIMIT:
        return None
    first = None
    for choices in iter_answers(decision):
        try:
            apply_command_with(state, ResolveDecision(decision.player, decision.id, tuple(choices)),
                               preflight=context.preflight if context else "derived", catalog=context.catalog if context else None)
            return None
        except UnsupportedError as error:
            first = first or error
        except IllegalActionError:
            continue
    return first


# v0.67: うらのカードがすると、その前におもてにする操作（「そのカードが「ワザ・特殊能力」を使う時や、「進化・にげる」をする時」）と、おもてにする理由（ログの ``cause``）
_FACE_DOWN_ACTIONS = {UseAttack: "attack", UsePokemonPower: "power", EvolvePokemon: "evolve", Retreat: "retreat"}


def _reveal_for_action(state: GameState, command, context: resolution.Context) -> bool:
    """v0.67（docs/secret-plan-preflight-v0.67.md 4 章）: うらのカードがワザ・特殊能力を使う・進化する・にげるコマンドなら、その前におもてにする（自分の番だけ。番・段階の
    確かめはおもてにする前）。本当のカードが「たねポケモン」なら、おもてにしたあと、そのコマンドをふつうに処理する（受け付けられなければコマンドごと拒否する。持ち主は
    本当のカードを知っている）ので False。「たねポケモン」でなければ、ついているカードといっしょにトラッシュし（コマンドの操作はおこらない）、空いたバトル場の勝ち負け・
    交代のあと番にもどって True（コマンドを受け付けた）。

    特殊能力の選ばせるもの（``source``・``target`` の場のポケモン・``energy`` のついているポケモン）がうらのカードなら、効果の対象として指定したのでおもてにする（「たねポケモン」
    でなければ、そのあとの処理を扱えないので ``UNSUPPORTED_SECRET_PLAN_LOST_TARGET``）。"""
    kind = _FACE_DOWN_ACTIONS.get(type(command))
    if kind is None or not state.face_down_cards:
        return False
    p = state.players[command.player] if command.player in PLAYERS else None
    if p is None:
        return False
    if isinstance(command, (UseAttack, Retreat)):
        subject = p.active
    elif isinstance(command, UsePokemonPower):
        subject = p.find_by_pokemon_id(command.pokemon)
    else:
        subject = p.find_by_pokemon_id(command.target)
    if subject is not None and state.is_face_down(subject):
        _require_turn(state, command.player)
        if state.decision is not None:
            raise IllegalActionError("DECISION_PENDING", "決定を待っている")
        if reveal_face_down(state, command.player, subject, cause=kind) is None:
            resolution.after_power(state, context, knock_outs=False)
            return True
    if isinstance(command, UsePokemonPower):
        for pid in (command.source, command.target):
            located = state.find_pokemon(pid) if type(pid) is int else None
            if located is not None and state.is_face_down(located[1]):
                designate_face_down(state, located[0], located[1], by_player=command.player, cause="power", can_lose=False)
        if command.energy is not None:
            holder = next(((owner, q) for owner, side in enumerate(state.players) for q in side.in_play() if command.energy in q.energy), None)
            if holder is not None:
                designate_face_down(state, holder[0], holder[1], by_player=command.player, cause="power", can_lose=False)
    return False


def _reveal_face_down(state: GameState, cmd: RevealFaceDown, context: resolution.Context) -> None:
    """うらにしてベンチに出したカード（マチスの秘策）を、自分の番におもてにする（v0.67。``RevealFaceDown``）。自分の番の ``Phase.MAIN`` だけ（決定を待つあいだ・処理の
    途中には割りこまない）。本当のカードが「たねポケモン」でなければ、ついているカードといっしょにトラッシュし（きぜつではない）、空いたバトル場の勝ち負け・交代のあと
    番にもどる（特殊能力のあとと同じ使用後の処理。``resolution.after_power``）。"""
    p = _require_turn(state, cmd.player)
    pokemon = p.find_by_pokemon_id(cmd.pokemon)
    if pokemon is None:
        if state.players[1 - cmd.player].find_by_pokemon_id(cmd.pokemon) is not None:
            raise IllegalActionError("POKEMON_NOT_YOURS", "相手の場のうらのカードはおもてにできない")
        raise IllegalActionError("POKEMON_NOT_IN_PLAY", f"場のポケモンの番号 {cmd.pokemon!r} は自分の場にいない")
    if not state.is_face_down(pokemon):
        raise IllegalActionError("NOT_FACE_DOWN", f"場のポケモン {pokemon.pokemon_id} はうらにしてベンチに出したカードではない")
    reveal_face_down(state, cmd.player, pokemon, cause="choice")
    resolution.after_power(state, context, knock_outs=False)


def _designate_answer(state: GameState, decision, choices: tuple[int, ...], effect) -> bool:
    """v0.67: トレーナー・特殊能力・スタジアムの効果の決定の答えが、うらのカード（マチスの秘策）を効果の対象として指定したら、おもてにする（p.277 の解説の「効果の対象として
    指定されないかぎり、裏のままでOK」の裏）。選んだ場のポケモン（選べるものが場のポケモンの決定）と、選んだカードがついている場のポケモン（エネルギーカード・トレーナー
    カード）が指定した対象。

    - 本当のカードが「たねポケモン」なら、おもてにしてそのまま続ける（False）
    - 「たねポケモン」でなく、効果が 1 匹だけを指定して、対象がいなくなったら効果が終わるもの（``effect.ends_on_lost_target``。入れ替えのトレーナー）なら、トラッシュして
      True（呼ぶ側は効果を終える）。ほかは ``UNSUPPORTED_SECRET_PLAN_LOST_TARGET``（そのあとの処理を扱えない。おもてにする前に止める）"""
    from .observation import OPTION_MEANINGS

    if not state.face_down_cards:
        return False
    meaning = OPTION_MEANINGS.get(decision.kind)
    designated = []
    for value in choices:
        if meaning == "pokemon":
            located = state.find_pokemon(value)
        elif meaning == "card":
            located = next(((owner, q) for owner, side in enumerate(state.players) for q in side.in_play()
                            if value in q.energy or any(t.card == value for t in q.trainers)), None)
        else:
            located = None
        if located is not None and all(q is not located[1] for _, q in designated):
            designated.append(located)
    lost = False
    can_lose = bool(getattr(effect, "ends_on_lost_target", False)) and len(designated) == 1
    for owner, pokemon in designated:
        if state.is_face_down(pokemon) and designate_face_down(state, owner, pokemon, by_player=decision.player, cause="effect",
                                                                can_lose=can_lose) is None:
            lost = True
    return lost


def _probes_receipts(state: GameState, command) -> bool:
    """v0.62（docs/history-attacks-v0.62.md 2 章）: このコマンドで、番でないプレイヤーの場のポケモンがワザ以外で受けたダメージ・効果を比べるか。ワザ（``UseAttack``）・番の
    終わり（``EndTurn``）・ワザとそのあとのきぜつの処理の決定への答え（再開先が解決の基盤のもの）は比べない（ワザの結果は受けた記録に、番の終わり・ポケモンチェックは
    どちらの番でもない）。"""
    if isinstance(command, (UseAttack, EndTurn)):
        return False
    if isinstance(command, (ResolveDecision, TakePrize, PromoteActive)):
        return state.decision is not None and state.decision.resume not in resolution.RESUMES
    return True


def _fresh_form_problem(before: GameState, after: GameState) -> tuple[str, str] | None:
    """``before`` になく ``after`` にある、決められない姿（v0.49。``effects.form_problems`` の (コード, 理由の文)）。なければ None。"""
    known = set(form_problems(before))
    return next((problem for problem in form_problems(after) if problem not in known), None)


# 答えがどれも止まるかを確かめる決定の答えの数の上限（v0.49）。超える決定は確かめずに、そのコマンドを受け付けないだけにする（今の対応カードでは、
# 姿が変わる決定はバトル場に出す決定・入れ替えの決定で、選べるものは控えポケモンの数まで）
_ALTERNATIVE_ANSWER_LIMIT = 256


def _decision_has_unstopped_answer(state: GameState, context: resolution.Context | None) -> bool:
    """保留中の決定に、決められない姿（v0.49）・最大HPの低下（MH1）にならない、受け付けられる答えがあるか。答えを 1 つずつ状態の複製の上で試す（状態を変えない）。
    答えの数が上限を超える決定は、あるとみなす（止めずに、そのコマンドを受け付けないだけ）。"""
    from .resolution.programs import answer_count, iter_answers

    decision = state.decision
    if decision is None:
        return True
    handler = _HANDLERS[ResolveDecision]  # バトル場に出す・サイドを取る決定も、決定への答え（``ResolveDecision``）で試す
    if answer_count(decision) > _ALTERNATIVE_ANSWER_LIMIT:
        return True  # v0.63: 答えの並びを作らずに数える（たたきつけろ!挑戦状の「好きなだけ」は答えが多い）
    for choices in iter_answers(decision):
        trial = state.clone()
        try:
            handler(trial, ResolveDecision(decision.player, decision.id, tuple(choices)), _context(state, context.preflight if context else "derived",
                                                                                              context.catalog if context else None))
        except (IllegalActionError, UnsupportedError):
            continue
        try:
            if _fresh_form_problem(state, trial) is None and not max_hp_drops(state, trial) and not scram_restored(state, trial):
                return True
        except HiddenPropertyRead:
            continue  # v0.67: うらのカードの決まらない項目を読む答え（FD1）は、受け付けられない答え
    return False


def _trainer_dead_end(before: GameState, after: GameState, context: resolution.Context | None) -> tuple[str, str] | None:
    """``after`` で待っているトレーナーの効果の途中の決定（使用中のトレーナーがある）に、トレーナーを終えるまで受け付けられない状態（``before`` になかった決められない姿・
    MH1）にならない答えの続きがなければ、止める (コード, 理由の文)（v0.49）。あれば None。答えを状態の複製の上で深さ優先で試し（状態を変えない）、続きが 1 つ見つかれば
    やめる。試す数が上限を超えたら、あるとみなす（止めない）。v0.48 までに起こる決定は、使うための条件の確認（``check_playable``）で続きがあることが決まっている
    （最初の答えで見つかる）。"""
    from .resolution.programs import iter_answers

    handler = _HANDLERS[ResolveDecision]
    budget = [_ALTERNATIVE_ANSWER_LIMIT]
    found: list[tuple[str, str]] = []
    options = _context(before, context.preflight if context else "derived", context.catalog if context else None)

    def reachable(state: GameState) -> bool:
        decision = state.decision
        for choices in iter_answers(decision):  # v0.63: 1 つずつ作る（上限で止めたら、残りの答えを作らない）
            budget[0] -= 1
            if budget[0] < 0:
                return True
            trial = state.clone()
            try:
                handler(trial, ResolveDecision(decision.player, decision.id, tuple(choices)), options)
            except UnsupportedError as error:
                found.append((error.code, error.message))
                continue
            except IllegalActionError:
                continue
            stop = _fresh_form_problem(before, trial)
            if stop is None and max_hp_drops(before, trial):
                error = max_hp_drop_error(max_hp_drops(before, trial))
                stop = (error.code, error.message)
            if stop is None and scram_restored(before, trial):
                error = scram_restored_error(scram_restored(before, trial))  # v0.61（SC2）
                stop = (error.code, error.message)
            if stop is not None:
                found.append(stop)
                continue
            if trial.trainer_in_use is None or trial.decision is None or reachable(trial):
                return True
        return False

    if reachable(after):
        return None
    return found[0] if found else ("UNRESOLVED_RULING", "トレーナーの効果の途中の決定に、受け付けられる答えの続きがない")


def _require_integrity(state: GameState) -> None:
    """返す状態がカードの保存則・場の形を満たすことを確かめる。満たさなければ返さない。"""
    problems = check_invariants(state)
    if problems:
        raise StateIntegrityError(problems)


def _require_in_hand(state: GameState, player: int, uid) -> None:
    if uid not in state.players[player].hand:
        raise IllegalActionError("CARD_NOT_IN_HAND", f"カード {uid!r} はプレイヤー {player} の手札にない")


# ---------------------------------------------------------------- 対戦準備


def _place_starting_pokemon(state: GameState, cmd: PlaceStartingPokemon) -> None:
    """手札からバトル場に 1 枚、ベンチに最大 5 枚（p.308「ポケモンを場に出す」）。"""
    _require_phase(state, Phase.SETUP_PLACEMENT)
    player = _require_player(cmd.player)
    p = state.players[player]
    if p.placed_starting_pokemon:
        raise IllegalActionError("ALREADY_PLACED", "対戦準備のポケモンはもう出している")
    chosen = (cmd.active, *cmd.bench)
    if len(set(chosen)) != len(chosen):
        raise IllegalActionError("DUPLICATE_CARD", "同じカードを 2 回選んでいる")
    if len(cmd.bench) > state.rules.max_setup_bench:
        raise IllegalActionError("SETUP_BENCH_LIMIT", f"対戦準備でベンチに出せるのは {state.rules.max_setup_bench} 枚まで")
    for uid in chosen:
        _require_in_hand(state, player, uid)
        if uid in play_as_pokemon_in_hand(state, player):
            # v0.47: 手札のなにかの化石・ピッピ人形（手札ではトレーナーカード）を、対戦準備で最初のポケモンとして出せるかは決められない（PF1）
            raise UnsupportedError(PLAY_AS_POKEMON_SETUP_CODE, f"カード {uid}（{state.card_def(uid).name_ja}）: {PLAY_AS_POKEMON_SETUP_REASON}")
        if not state.card_def(uid).is_basic_pokemon:
            raise IllegalActionError("NOT_BASIC_POKEMON", f"カード {uid} はたねポケモンではない")
    for uid in chosen:
        p.hand.remove(uid)
    p.active = _enter_play(state, cmd.active)
    p.bench = [_enter_play(state, uid) for uid in cmd.bench]
    p.placed_starting_pokemon = True
    state.add_event("place_starting_pokemon", player=player, active=cmd.active, bench=tuple(cmd.bench))

    if all(q.placed_starting_pokemon for q in state.players):
        # サイドカードをセットする: 山札の一番上から裏のまま 6 枚（p.308）
        for pl in PLAYERS:
            q = state.players[pl]
            q.prizes = q.deck[: state.rules.prize_count]
            del q.deck[: state.rules.prize_count]
            state.add_event("set_prizes", player=pl, count=len(q.prizes))
        _after_prizes(state)


def _enter_play(state: GameState, uid: int) -> PokemonInPlay:
    """カードを場のポケモンにする。場のポケモンの番号を新しく付ける（前に使った番号は使わない）。

    場に出た番（``played_turn``。対戦準備なら 0）を記録する。今の番に場に出したポケモンは、その番には進化できない
    （「その番の最初」には場にいなかった。p.310。v0.4a）。
    v0.32 から本体は ``zones.enter_play``（ワザの効果で山札からベンチに出す処理と共通）。
    """
    return enter_play(state, uid)


def _after_prizes(state: GameState) -> None:
    if any(p.mulligan_draws_remaining for p in state.players):
        state.phase = Phase.SETUP_MULLIGAN_DRAW
    else:
        state.phase = Phase.SETUP_FIRST_PLAYER


def _draw_mulligan_cards(state: GameState, cmd: DrawMulliganCards) -> None:
    """相手の切り直し 1 回ぶん、山札から最大 2 枚（1 枚・0 枚でもよい）引く（p.308）。"""
    _require_phase(state, Phase.SETUP_MULLIGAN_DRAW)
    player = _require_player(cmd.player)
    p = state.players[player]
    if p.mulligan_draws_remaining <= 0:
        raise IllegalActionError("NO_MULLIGAN_DRAW", "相手の切り直しのぶんの引く権利がない")
    limit = state.rules.mulligan_draw_max_per_mulligan
    if not 0 <= cmd.count <= limit:
        raise IllegalActionError("INVALID_DRAW_COUNT", f"引けるのは 0〜{limit} 枚")
    if cmd.count > len(p.deck):
        raise IllegalActionError("INVALID_DRAW_COUNT", "山札の枚数より多くは引けない")
    _draw(state, player, cmd.count)
    p.mulligan_draws_remaining -= 1
    state.add_event("mulligan_draw", player=player, count=cmd.count)
    if not any(q.mulligan_draws_remaining for q in state.players):
        state.phase = Phase.SETUP_FIRST_PLAYER


def _report_janken_result(state: GameState, cmd: ReportJankenResult) -> None:
    """ジャンケンに勝った人が先攻（p.308）。場のポケモンを表にしたら先攻の番が始まる（p.309）。"""
    _require_phase(state, Phase.SETUP_FIRST_PLAYER)
    winner = _require_player(cmd.winner)
    state.first_player = winner
    state.add_event("janken", winner=winner, first_player=winner)
    state.add_event("reveal_pokemon")
    _begin_turn(state, winner)


# ---------------------------------------------------------------- 番の進行


def _play_basic_to_bench(state: GameState, cmd: PlayBasicToBench, context: resolution.Context) -> None:
    """手札のたねポケモンをベンチに出す。ベンチは 5 匹まで。1 番に出す数の制限はない（p.309）。"""
    p = _require_turn(state, cmd.player)
    _require_in_hand(state, cmd.player, cmd.card)
    if not state.card_def(cmd.card).is_basic_pokemon:
        raise IllegalActionError("NOT_BASIC_POKEMON", f"カード {cmd.card} はたねポケモンではない")
    if len(p.bench) >= bench_limit(state, cmd.player):
        # v0.57: 場のスタジアムの「ベンチに出しておける控えポケモンの数」（せまいジム）を当てはめた数（``stadiums.bench_limit``。なければ共通のルールの 5 匹）
        raise IllegalActionError("BENCH_FULL", f"ベンチは {bench_limit(state, cmd.player)} 匹まで")
    p.hand.remove(cmd.card)
    pokemon = _enter_play(state, cmd.card)
    p.bench.append(pokemon)
    state.add_event("play_to_bench", player=cmd.player, card=cmd.card)
    # v0.87: はたらいている［ヒートプレート］があれば、爆発ジム・手札から場に出したときの特殊能力の機会と同じ時点の反応（順番は番のプレイヤー）として扱い、そのあと場を整える
    # （HP 以上になったポケモンのきぜつ。docs/movement-damage-reactions-v0.87.md 4.3 節）。なければ v0.86 までと同じ
    if movement.note_from_hand(state, cmd.player, pokemon, minefield=True, entry=True):
        reactions.run(state, movement.take(state) + ((reactions.SETTLE_EFFECTS,),), context, _REACTION_HOOKS)
        return
    # v0.57: 場のロケット団の爆発ジム（手札からたねポケモンのカードをベンチに出す時、持ち主がコインを投げ、「うら」なら 20 ダメージ。docs/stadiums-v0.57.md 5 章）
    bench_entry_damage(state, cmd.player, pokemon)
    if knocked_by_hp(state, pokemon):
        resolution.after_effects(state, context)  # v0.87: 爆発ジムのダメージで HP 以上（v0.86 までは起こらないとしていた。3.3 節）
        return
    # v0.86: 手札から場に出したときに使える特殊能力（エンテイの［おたけび］）。使うかは持ち主が決める（決定 ENTRY_POWER。再開先 "power"。docs/entry-energy-evolution-reactions-v0.86.md 4 章）
    if pokemon in p.bench:
        offer_entry_power(state, cmd.player, pokemon, from_hand=True)


def _evolve_pokemon(state: GameState, cmd: EvolvePokemon, context: resolution.Context) -> None:
    """手札の進化カードを、自分の場のポケモンに重ねて進化させる（p.309「場にいるポケモンを進化させる」・p.310。v0.4a）。

    v0.4a は、たねポケモン → 1 進化ポケモン。v0.4c で、1 進化ポケモン → 2 進化ポケモンも同じコマンド・同じ手順で
    扱う（p.319「場にいる「たねポケモン」または「進化ポケモン」に進化カードを重ねて進化させたとき」。重なりは 3 枚まで）。
    確かめること（どれも状態を変える前。拒否しても状態も乱数も変わらない）:

    - 自分の番（MAIN）。決定を待つ間（トレーナーの途中を含む）は進化させられない（p.310「進化させている最中は…」の
      裏返しで、ほかのことの最中にも進化はできない。``_require_turn``）
    - ``cmd.card`` が手札にあり、進化カード（``NOT_EVOLUTION_CARD``）。対応していない進化カード（ベイビィ・登録のない
      ワザやポケモンパワーを持つカード。2 進化の段階だからといって対応にはしない）は ``UNSUPPORTED_EVOLUTION``
      （デッキには入らないので、テストの盤面だけ）
    - ``cmd.target`` が自分の場のポケモンの番号（``TARGET_NOT_IN_PLAY``・``TARGET_NOT_YOURS``）。バトル場でもベンチでもよい
    - おたがいのプレイヤーの最初の番ではない（p.310。``FIRST_TURN_EVOLUTION``）
    - 進化カードの「○○○○から進化」の名前が、そのポケモン（いちばん上のカード）の名前と同じ（p.309・p.324「書かれて
      いない組み合わせでカードを重ねてはいけません」。``EVOLUTION_NAME_MISMATCH``）。たねポケモンに 2 進化カードを
      直接重ねること（ビードルにスピアー）も、名前が違うのでここで拒否する
    - そのポケモンが「その番の最初から場に出ていた」（p.310）: 今の番に場に出したポケモン（``PLAYED_THIS_TURN``）・
      今の番に進化したポケモン（別のポケモンとしてあつかわれ、その番の最初には場にいなかったことになる。
      ``EVOLVED_THIS_TURN``。v0.4c: 今の番に 1 進化したポケモンを同じ番に 2 進化させることもこれで拒否する）は
      進化させられない。制限は 1 匹ごとで、ほかのポケモンは進化させられる
    - 段階が合う（v0.4c。1 進化カードはたねポケモンに、2 進化カードは 1 進化ポケモンに重ねる。p.316・p.319 の
      「たね + 進化 + 進化」）。名前が合えば実際のカードの組では段階も合うので、カードのデータが名前と段階で食い違う
      テスト専用のカードだけで起こる（``EVOLUTION_STAGE_MISMATCH``。進化の重なりの不変条件を破る状態を作らない）
    - 進化したあとの HP が、のっているダメージ以下になる場合は、きぜつの扱いが原典で決められないので止める
      （``UNRESOLVED_EVOLUTION_HP``。v0.4a の対応カードでは HP が増え、v0.4c のコクーン → スピアーは HP が同じ 80
      なので、きぜつしていないポケモンでは起こらない）

    手順（p.310）: 1・2. 進化カードを手札から出して見せ、進化するポケモンの上に置く（下のカードはトラッシュしない。
    いちばん上のカードの内容がそのポケモンを表す）→ 3. 特殊状態と持続する効果から回復させる（``clear_special_conditions``
    の ``EVOLVE`` と、v0.4b の ``persistent.remove_persistent_effects`` の ``EVOLVE``。別々の処理）→ 4. マーカー・カウンター（ダメージカウンター以外）を取りのぞく
    （対応カードにない）→ 5. 進化によって引き起こされる特殊なことがら（対応カードにない）。

    受け継ぐもの: ダメージカウンター・エネルギーカード・ついているトレーナーカード（p.310）。場のポケモンの番号も変えない
    （エンジンの内部の識別子。docs/evolution-state-v0.4a.md）。下に重なったカード（2 進化ならたねポケモンと 1 進化
    ポケモンの 2 枚。下から順）と場に出た番（``played_turn``）もそのまま（v0.4c。docs/stage2-state-v0.4c.md）。
    ついているトレーナー（プラスパワー・ディフェンダー）の効果と有効期限は変わらない（カードの効果で、進化で消える
    「持続する効果」ではない。p.321 の 5・7 段階、p.322。SUPPORTED。docs/evolution-rules-v0.4a.md）。

    にげるの失敗の記録（``retreat_failed_turn``。v0.3c）: 進化したポケモンは別のポケモン（p.310）で、こんらんも消える
    （p.322）。p.311 の「一度「にげる」に失敗したこんらん状態のポケモン」をどちらの意味に読んでも、進化したポケモンは
    「にげる」を宣言できるので、記録を消す（SUPPORTED。ログ ``retreat_failure_cleared``）。特殊状態の解除とは別の処理。

    進化は乱数を使わず、決定も出さない。ログ ``evolve``（``player``・``pokemon_id``・進化前と進化後のカードの uid と
    カード id）。
    """
    p = _require_turn(state, cmd.player)
    _require_in_hand(state, cmd.player, cmd.card)
    definition = state.card_def(cmd.card)
    if definition.category != "pokemon" or definition.stage == "basic":
        raise IllegalActionError("NOT_EVOLUTION_CARD", f"カード {cmd.card}（{definition.name_ja}）は進化カードではない")
    if not definition.is_evolution_pokemon or not definition.supported:
        reasons = "; ".join(definition.unsupported_reasons) or f"{definition.stage} の進化は未実装"
        raise UnsupportedError("UNSUPPORTED_EVOLUTION", f"進化カード「{definition.name_ja}」は未対応（{reasons}）")
    target = p.find_by_pokemon_id(cmd.target)
    if target is None:
        if state.players[1 - cmd.player].find_by_pokemon_id(cmd.target) is not None:
            raise IllegalActionError("TARGET_NOT_YOURS", "相手の場のポケモンは進化させられない")
        raise IllegalActionError("TARGET_NOT_IN_PLAY", f"場のポケモンの番号 {cmd.target!r} は自分の場にいない")
    # v0.42: 番・名前・その番の最初から場にいたか・段階の確認は、ワザによる進化（つきのちから）と共通の ``evolution.evolution_block``（v0.41 までと同じ順番・
    # 同じコード・同じ文）
    block = evolution_block(state, target, definition)
    if block is not None:
        if block[0] == DEVOLVED_THIS_TURN_CODE:
            raise UnsupportedError(*block)  # v0.50: 今の番に退化したポケモン（DV2。ほかの確かめがすべて通ったあと）
        raise IllegalActionError(*block)
    # v0.48: 進化したあとの最大HP（重ねるカードの HP と、そのカードのはたらく常にはたらく特殊能力。``effects.evolution_hp``）。進化すると持続する効果（きょだいか）は
    # 消える。ナツメのゴースの［ガスのからだ］で大きくなっていた最大HPは、ナツメのゴーストに進化するともとにもどる（v0.4a の H1 と同じ問い。進化が原因の場合だけ）
    evolved_hp = evolution_hp(state, target, cmd.card)
    if target.damage >= evolved_hp:
        raise UnsupportedError(
            "UNRESOLVED_EVOLUTION_HP",
            f"進化すると HP（{evolved_hp}）がのっているダメージ（{target.damage}）以下になる。そのときにきぜつするか"
            "（いつきぜつの判定をするか）は『オフィシャルブック2000』（p.310・p.323）から決められないので扱わない",
        )

    # 1〜5. 手札から出して見せ、進化するポケモンの上に置き、特殊状態・持続する効果・にげるの失敗の記録を消す（v0.25 から、
    # 1 進化を飛ばして進化させるトレーナーの効果と共通の ``evolution.place_evolution_card``。動き・ログは v0.24 と同じ）
    # v0.85: かならずはたらく特殊能力（［あばれんぼう］）を処理できない（HC6）なら、場に出す前に止める
    forced_entry_check(state, cmd.player, cmd.card)
    before_name = form_def(state, target).name_ja
    place_evolution_card(state, cmd.player, target, cmd.card)
    if reactions.has_chain_reactions(state, cmd.player, target):
        # v0.86: ほかのポケモンの［れんさしんか］の機会がある進化。場に出たときの特殊能力の機会と同じ時点の反応として、番のプレイヤーが順番を決める（``reactions``。
        # docs/entry-energy-evolution-reactions-v0.86.md 3.2 節）。トキワシティジムの機会（進化させる時）は先に聞き、答えたあと続きで反応を処理する
        steps = reactions.evolution_steps(state, cmd.player, target, entry_from_hand=True)
        if offer_evolution_heal(state, cmd.player, target, before_name, then=("followup", 1, ())):
            reactions.attach_followup(state, steps)
            return
        reactions.run(state, steps, context, _REACTION_HOOKS)
        return
    # v0.57: 場のトキワシティジム（自分の「サカキのポケモン」を進化させる時、のぞむならダメージカウンターを 2 つとりのぞいてよい）。答えたあと、場に出たときの特殊能力の
    # 機会にもどる（``_resume_stadium``。docs/stadiums-v0.57.md 5 章）
    if offer_evolution_heal(state, cmd.player, target, before_name, then=("entry", 1, ())):
        return
    # v0.43: 手札から出した（場に出た）ときに 1 度だけ使える特殊能力（``effects.EntryPower``）があれば、使うかを持ち主に聞く
    # （決定 ENTRY_POWER。再開先 "power"。docs/declared-entry-powers-v0.43.md 3 章）
    offer_entry_power(state, cmd.player, target, from_hand=True)


def _attach_energy(state: GameState, cmd: AttachEnergy, context: resolution.Context) -> None:
    """エネルギーカードを 1 番に 1 枚、自分の場のポケモンにつける（p.310）。

    v0.6: この番に、ポケモンパワー（「あまごい」）の効果で手札からエネルギーをつけていて、通常の操作ではまだつけていなければ、
    この操作を受け付けるかは原典で決められない（p.310「ポケモンにつけることのできるエネルギーカードの数は、1回の自分の番ごとに
    1枚だけです」が、パワーでつけたカードも数えるのかが書かれていない。p.307・p.90。docs/rain-dance-v0.6.md の R13）。
    ほかの確認がすべて通ったあと、状態を変える前に ``UnsupportedError``（``UNRESOLVED_ATTACH_AFTER_POWER_ATTACH``）で止める。
    通常の操作でつけたあとの「あまごい」は受け付ける（どちらの読み方でも同じ。R12）。
    """
    p = _require_turn(state, cmd.player)
    _require_in_hand(state, cmd.player, cmd.energy)
    if state.card_def(cmd.energy).category != "energy":
        # v0.58: 特殊エネルギーカード（登録されたもの。デッキの検査で確かめている）もつけられる。エネルギーカードでないカードの拒否のコードは v0.57 までと同じ
        raise IllegalActionError("NOT_BASIC_ENERGY", f"カード {cmd.energy} は基本エネルギーカードではない")  # 理由の文も v0.57 と同じ（エネルギーカードではない）
    cards = (cmd.energy,) if cmd.energy2 is None else (cmd.energy, cmd.energy2)
    if cmd.energy2 is not None:
        # v0.59: カツラの効果で 2 枚をいっしょにつける（docs/energy-control-power-suppression-v0.59.md 4 章）
        _require_in_hand(state, cmd.player, cmd.energy2)
        if cmd.energy2 == cmd.energy:
            raise IllegalActionError("DUPLICATE_CHOICE", f"同じカード {cmd.energy} を 2 回つけようとした")
    # v0.59: 通常の操作でつけた枚数（カツラの効果で 2 枚つけたら 2）。2 回目の操作は、カツラの効果がはたらいていて、「炎」エネルギーカードを「カツラのポケモン」に
    # つける操作なら決められない（BL1。ほかの確認のあとで止める）。ほかは v0.58 までと同じ拒否
    second_attach = False
    if state.energy_attachments_this_turn >= state.rules.energy_attachments_per_turn:
        candidate = p.find_in_play(cmd.target)
        if not (state.energy_attachments_this_turn == state.rules.energy_attachments_per_turn and candidate is not None
                and blaine_attach_applies(state, cmd.player, candidate, cards)):
            raise IllegalActionError("ENERGY_ALREADY_ATTACHED", "エネルギーカードはこの番にもうつけた（1 番に 1 枚）")
        second_attach = True
    target = p.find_in_play(cmd.target)
    if target is None:
        if state.players[1 - cmd.player].find_in_play(cmd.target) is not None:
            raise IllegalActionError("TARGET_NOT_YOURS", "相手の場のポケモンにはつけられない")
        raise IllegalActionError("TARGET_NOT_IN_PLAY", f"{cmd.target!r} は自分の場のポケモンではない")
    if cmd.energy2 is not None:
        double_attach_check(state, cmd.player, target, cards)
    for card in cards:
        energy_attach_target_check(state, card, target)  # v0.85: ミラクルエネルギーのつける先（「ひかる」「やさしい」）・［きせきのかぜ］の間（MEW1）
    if energy_attach_blocked(state, target) is not None:
        # v0.59: カスミのメノクラゲの「クリスタルビーム」を受けた（次の相手の番、エネルギーカードをつけることができない）。カードを動かす前
        raise IllegalActionError("ENERGY_ATTACH_PREVENTED", f"ポケモン {target.pokemon_id} には、この番はエネルギーカードをつけることができない（相手のワザの効果）")
    if state.energy_attached_by_powers_this_turn > 0:
        raise UnsupportedError(
            "UNRESOLVED_ATTACH_AFTER_POWER_ATTACH",
            f"この番にポケモンパワーの効果で手札からエネルギーを {state.energy_attached_by_powers_this_turn} 枚つけたあとで、手札から"
            "エネルギーをつける（通常の操作）ことができるかは『オフィシャルブック2000』から決められない（p.310 の「1回の自分の番ごとに"
            "1枚だけ」にパワーでつけたカードを数えるかが書かれていない）ので扱わない",
        )
    if cmd.energy2 is not None:
        double_attach_rainbow_check(state, cards)  # v0.59: レインボーエネルギーを「炎」エネルギーカードとして 2 枚の 1 枚に選べるか（RB2）
    if second_attach:
        raise blaine_second_attach_error(state, target)  # v0.59: BL1
    for card in cards:
        problem = attach_from_hand_problem(state, cmd.player, card, target)
        if problem is not None:
            # v0.58: 特殊エネルギーの、手札から出してつけたときの効果が決められない（RB1・RB4）。カードを動かす前
            raise UnsupportedError(*problem)
    knocks_out = False
    pre_status = (int(target.conditions.asleep), int(target.conditions.paralyzed), int(target.conditions.confused))  # v0.86: 「つけるときすでに」
    for card in cards:
        attach_energy_from_hand(state, cmd.player, card, target)
    state.energy_attachments_this_turn += len(cards)
    extra = {} if cmd.energy2 is None else {"energy2": cmd.energy2, "trainer_card": blaine_effect_card(state, cmd.player)}
    state.add_event("attach_energy", player=cmd.player, energy=cmd.energy, target=cmd.target, **extra)
    steps = reactions.attach_steps(state, cmd.player, cmd.player, target, cards, pre_status)
    if steps is not None:
        # v0.86（docs/entry-energy-evolution-reactions-v0.86.md 2 章）: 手札からつけた事実への反応（特殊エネルギーのつけたときの効果・ほのおでかいふく・［エナジーしんか］・
        # ［いなびかり］・［かんでん］）が 2 つ以上ある・v0.86 の反応があるなら、``reactions`` が順番（番のプレイヤー）と決定をまたぐ続きを扱う。カツラの 2 枚は、つけたカードの順に
        # 1 枚ずつの事実（実装上の順番）
        reactions.run(state, steps, context, _REACTION_HOOKS)
        return
    for card in cards:
        # v0.58: 特殊エネルギーの、手札から出してつけたときの効果（きずぐすり配合・なんでもなおし配合・レインボー。GR-2000-P310-ATTACH-ENERGY）。場にあるカードの
        # 移動（エナジートランスなど）では呼ばない
        knocks_out = energy_attached_from_hand(state, cmd.player, card, target) or knocks_out
        after_energy_attached(state, cmd.player, target, card)  # v0.31: つけたときにはたらく特殊能力（ほのおでかいふく）
    if knocks_out:
        resolution.after_energy(state, context)  # v0.58: レインボーエネルギーの 10 ダメージで HP 以上になったら、きぜつの処理


# v0.93: 「バトル場をはなれられない」効果を受けたバトル場のポケモンの「にげる」・すてる操作の拒否（docs/active-leave-locks-v0.93.md 4 章）
LEAVE_ACTIVE_PREVENTED = "LEAVE_ACTIVE_PREVENTED"


def _retreat(state: GameState, cmd: Retreat, context: resolution.Context) -> None:
    """にげる（pp.310-311）。1 番に何度でも。控えがいなければ宣言できない。

    にげるエネルギーの数ぶん、そのポケモンについているエネルギーを選んでトラッシュし、控えと入れ替える。
    ベンチに戻ったポケモンの特殊状態はすべて消える（p.311・p.322）。どく状態でもにげられる。
    ねむり状態・マヒ状態のポケモンは「にげる」を宣言できない（p.311・p.322。v0.3b）。宣言できないので、エネルギーを
    トラッシュする前に拒否する（``POKEMON_ASLEEP``・``POKEMON_PARALYZED``）。「ポケモンいれかえ」はにげるではない
    （p.325）ので、この制限を受けない。

    こんらん状態（v0.3c。p.310〜311 の手順）: 1. 宣言 → 2. にげるエネルギーの数ぶんトラッシュ → 3. 持ち主がコインを 1 枚
    投げ、「うら」なら「にげる」は失敗（トラッシュしたエネルギーは取り戻せない）→ 4. 失敗でなければ控えと入れ替える。
    失敗したら入れ替えず（こんらん・ダメージ・ついているカードはそのまま）、そのポケモンは今の番ではもう「にげる」を宣言
    できない（``retreat_failed_turn``。番の終わりに消す）。番は終わらない。失敗は宣言した「にげる」の結果で、不正な
    コマンドではない（エネルギーのトラッシュとコインは状態に残る）。にげるエネルギーが 0 でもコインは投げる（手順 3 に
    例外がない）。入れ替える控え（手順 4 で選ぶ）はコマンドで先に指定するが、コインの結果で選べるものは変わらない。
    """
    p = _require_turn(state, cmd.player)
    active = p.active
    if not p.bench:
        raise IllegalActionError("NO_BENCH", "控えポケモンがいないので、にげるを宣言できない")
    _require_not_asleep_or_paralyzed(active, "「にげる」を宣言できない（p.311・p.322）")
    if state.card_def(active.card).play_role is not None:
        # v0.47: バトル場のなにかの化石・ピッピ人形が「にげる」ことができるか（にげるエネルギーの数）は決められない（PF2）。エネルギーのトラッシュ・こんらんのコインの前
        raise UnsupportedError(PLAY_AS_POKEMON_RETREAT_CODE, f"バトル場のポケモン {active.pokemon_id}: {PLAY_AS_POKEMON_RETREAT_REASON}")
    if leave_lock(state, cmd.player, active) is not None:
        # v0.93（docs/active-leave-locks-v0.93.md 4 章）: 「バトル場をはなれられない」効果（からまるいと・からみつく・ねばるみつ・くいつく・どくしばり）を受けた。「にげる」でバトル場を
        # はなれることもできないので、宣言を拒否する（エネルギーのトラッシュ・こんらんのコインの前。状態・乱数・ログは変わらない）。「にげる」だけを止める効果とは別のコード
        raise IllegalActionError(
            LEAVE_ACTIVE_PREVENTED, f"バトル場のポケモン {active.pokemon_id} は、バトル場をはなれられない（相手のワザの効果）ので「にげる」ことができない"
        )
    retreat_lock = cannot_retreat(state, active)
    if retreat_lock is not None:
        # v0.36: 「アイスバーン」・「わしづかみ」を受けた（次の相手の番に「にげる」ことができない）。ねむり・マヒと同じく宣言できないので、エネルギーの
        # トラッシュ・こんらんのコインの前に拒否する（状態・乱数・ログは変わらない）。「ポケモンいれかえ」などの入れ替えは制限しない（p.325）
        require_source_card_present(state, retreat_lock, active)  # v0.93: CJ1（かぶりつくの発生源の「このカード」が退化ではがれた）
        raise IllegalActionError(
            "RETREAT_PREVENTED", f"バトル場のポケモン {active.pokemon_id} は、この番は「にげる」ことができない（相手のワザの効果）"
        )
    guards = retreat_guards(state, cmd.player)
    if guards:
        # v0.87: 相手のバトル場の［とおせんぼ］（カビゴン）。「アイスバーン」と同じく宣言できないので、エネルギーのトラッシュ・こんらんのコインの前に拒否する
        _, holder, key, _ = guards[0]
        raise IllegalActionError(
            "RETREAT_PREVENTED", f"バトル場のポケモン {active.pokemon_id} は「にげる」ことができない（相手のバトル場のポケモン {holder.pokemon_id} の特殊能力 {key}）"
        )
    if active.retreat_failed_turn == state.turn_number:
        if active.conditions.confused:
            raise IllegalActionError(
                "RETREAT_ALREADY_FAILED",
                f"バトル場のポケモン {active.pokemon_id} は、この番にこんらんで「にげる」に失敗したので、もう宣言できない（p.311）",
            )
        # 失敗したあとにベンチに戻り（こんらんが消え）、同じ番にバトル場に戻ったポケモン。p.311 の「一度「にげる」に失敗した
        # こんらん状態のポケモン」に、こんらんでなくなったポケモンが含まれるかは原典で決められない
        raise UnsupportedError(
            "UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED",
            f"バトル場のポケモン {active.pokemon_id} は、この番にこんらんで「にげる」に失敗したあと、こんらんが消えている。"
            "p.311「一度「にげる」に失敗したこんらん状態のポケモンは、今の自分の番では、もう「にげる」を宣言することができません」が"
            "こんらんでなくなったポケモンにもかかるかは『オフィシャルブック2000』から決められないので扱わない",
        )
    index = p.bench_index(cmd.new_active)
    if index is None:
        raise IllegalActionError("NOT_ON_BENCH", f"{cmd.new_active!r} は自分のベンチにいない")
    # v0.46: トラッシュするエネルギーの数は、印刷の数に、はたらいている常にはたらく特殊能力（相手の［ねんちゃくえき］は決まって増やし、自分の［にげるサポート］は少なく
    # できる）を当てはめた範囲（``effects.retreat_cost``。最後に 0 で下限をつける）。特殊能力がなければ印刷の数ちょうど（v0.45 までと同じ）
    cost = retreat_cost(state, cmd.player)
    discard = tuple(cmd.discard)
    if len(set(discard)) != len(discard):
        raise IllegalActionError("DUPLICATE_CARD", "同じエネルギーを 2 回選んでいる")
    if any(uid not in active.energy for uid in discard):
        raise IllegalActionError("ENERGY_NOT_ATTACHED", "バトル場のポケモンについていないエネルギーを選んでいる")
    # v0.58: トラッシュするエネルギーは、選んだカードの出すエネルギーの個数で数える（基本エネルギーカードは 1 枚 1 個。無色2個エネルギーは 1 枚で 2 個で、分けて
    # トラッシュできない。レインボーエネルギーは 1 個）。カードの枚数では数えない
    units = energy_unit_count(state, discard, active)
    ambiguous = wild_growth_ambiguities(state, active)
    if ambiguous and any(uid in discard for uid, _ in ambiguous):
        # v0.85: トラッシュするカードに、［おいしげる］で「草」2 個になるかが決まらないカードがある。2 つの読み方でトラッシュしてよい数かが変わるなら止める（エネルギーの
        # トラッシュ・コインの前）
        alt = units + sum(2 - energy_unit_count(state, (uid,), active) for uid, _ in ambiguous if uid in discard)
        if cost.allows(units) != cost.allows(alt):
            raise wild_growth_error(state, active, [(uid, kind) for uid, kind in ambiguous if uid in discard], "・「にげる」のエネルギーの数")
    overpay = False
    if not cost.allows(units):
        # 余計なカードを除いても足りる選び方（どれか 1 枚を除いても正しい数以上になる）は誤り。どのカードを除いても足りなくなる選び方（無色2個エネルギーでにげる
        # エネルギー 1 を払う）は、余る個数を払ってよいかが決まらない（RT1。ほかの確認がすべて通ったあとに止める）
        overpay = units > cost.maximum and all(units - energy_unit_count(state, (uid,), active) < cost.minimum for uid in discard)
        if not overpay:
            wanted = f"{cost.maximum} 個" if cost.minimum == cost.maximum else f"{cost.minimum}〜{cost.maximum} 個"
            chosen = f"{len(discard)} 枚選んでいる" if units == len(discard) else f"{len(discard)} 枚・{units} 個選んでいる"
            raise IllegalActionError("WRONG_RETREAT_COST", f"にげるエネルギーは {wanted}（{chosen}）")
    if overpay:
        raise UnsupportedError(
            RETREAT_OVERPAY_CODE,
            f"「にげる」でトラッシュするエネルギーカード {list(discard)} の出すエネルギー {units} 個が、にげるエネルギーの数（{cost.minimum}〜{cost.maximum}）より多く、"
            "どのカードを除いても足りない（無色2個エネルギーは分けてトラッシュできない）。余るエネルギーをトラッシュして「にげる」ことができるかは、2000.02.14 版の"
            "公式ルール・kyuura の記録で決まらないので扱わない（RT1）",
        )
    if cost.floor_ambiguous(units):
        # v0.46: 少なくする数が印刷の数より多く、増やす数もある（自分のにげるの数が 0 のドードリオのベンチにドードリオ、相手のバトル場にわるいベトベトン）。先に少なくして
        # 0 で止めてから増やすのか、最後に下限をつけるのかで、トラッシュしてよい数が変わる。記録から決まらない（CP2）ので、読み方で答えが変わる数は扱わない（エネルギーを
        # トラッシュする前・コインの前。状態・乱数・ログは変わらない）
        raise UnsupportedError(
            "UNRESOLVED_RETREAT_COST_FLOOR",
            f"「にげる」でトラッシュするエネルギーの数（印刷の {cost.printed}、増やす {[a for _, _, a in cost.increases]}、少なくできる {[a for _, _, a in cost.reductions]}"
            + (f"、スタジアムで増やす {[a for _, a in cost.stadium_increases]}・へらす {[a for _, a in cost.stadium_reductions]}"
               if cost.stadium_increases or cost.stadium_reductions else "")
            + (f"、ふうせんのみ {list(cost.zeroed)}（すべてなくなる）" if cost.zeroed else "")
            + (f"、特殊能力 {[k for _, k in cost.power_zeroed]}（すべてなくなる）" if cost.power_zeroed else "")
            + (f"、マーカーで増やす {[a for _, a in cost.marker_increases]}" if cost.marker_increases else "") + "）を、"
            f"少なくしてから 0 で止めて増やすか、合わせてから 0 で止めるかで、{units if units != len(discard) else len(discard)} {'個' if units != len(discard) else '枚'}が足りるかが変わる。どちらの読み方かは kyuura の記録・印刷の文面から決められない"
            "ので扱わない（CP2）",
        )
    # v0.48（MH1）: トラッシュするエネルギーカード（［ガスのからだ］の「超」エネルギーカード）・ベンチにもどること（「きょだいか」の効果が消える・ベンチにもどった
    # ベトベトンの特殊状態が消えてかがくへんかガスがはたらく）で、最大HPがのっているダメージ以下に下がる場のポケモンがいれば、エネルギーのトラッシュ・こんらんの
    # コインの前に止める（コインの結果で受け付けるかが変わらないように、失敗と成功のどちらの結果も複製の上で確かめる）
    _retreat_max_hp_drop_check(state, cmd.player, discard, index)
    # v0.61（docs/reactive-powers-trainer-damage-v0.61.md 3 章）: 相手の［おとしあな］。こんらん状態の「にげる」と、入れ替えの前か後かで受けるダメージが変わる場合は SH1、
    # 2 つ以上の［おとしあな］の途中で［ずらかる］の残りHPが「10」を通る場合は SC1。どれもエネルギーのトラッシュ・コインの前に止める
    _sinkhole_check(state, cmd.player, active, index)
    if cost.zeroed and active.conditions.confused:
        # v0.81（BB1）: ふうせんのみの「「にげる」とき、このカードをトラッシュする」が、こんらんのコインの「うら」で失敗した「にげる」にも当てはまるかは決まらない。
        # コインの結果で受け付けるかを変えないよう、エネルギーのトラッシュ・コインの前に止める
        raise UnsupportedError(BALLOON_BERRY_FAILED_RETREAT_CODE, f"こんらん状態のポケモン {active.pokemon_id}（ふうせんのみ {list(cost.zeroed)}）: {BALLOON_BERRY_FAILED_RETREAT_REASON}")
    returns = energy_discard_plan(state, active, discard, cause=DISCARD_BY_RETREAT)  # v0.82: リサイクルエネルギー（トラッシュに置いたあと、ログ retreat のあとにもどす）
    for uid in discard:
        active.energy.remove(uid)
        p.discard.append(uid)
    # v0.46: 特殊能力で数が変わったときだけ、ログに数の範囲と特殊能力を書く（v0.45 までのログの形は変えない）
    cost_log = {} if not cost.modified else {"retreat_cost": (cost.minimum, cost.maximum), "retreat_cost_printed": cost.printed,
                                             "retreat_cost_increases": cost.increases, "retreat_cost_reductions": cost.reductions}
    if cost.stadium_increases or cost.stadium_reductions:
        # v0.57: 場のスタジアムで数が変わったときだけ、(スタジアムカード, 数（増やすなら正、へらすなら負）) を書く（特殊能力の記録とは分ける）
        cost_log["retreat_cost_stadium"] = tuple((card, amount) for card, amount in cost.stadium_increases) + tuple(
            (card, -amount) for card, amount in cost.stadium_reductions)
    if cost.zeroed:
        cost_log["retreat_cost_zeroed"] = cost.zeroed  # v0.81: ふうせんのみ（「にげる」ときに必要なエネルギーはすべてなくなる）
    if cost.power_zeroed:
        # v0.96: ［ZOOM］（(持つポケモンの番号, PowerKey の文字列)）。ふうせんのみの記録とは分ける（ふうせんのみだけがトラッシュされ、BB1 に当たる）
        cost_log["retreat_cost_power_zeroed"] = cost.power_zeroed
    if cost.marker_increases:
        cost_log["retreat_cost_markers"] = cost.marker_increases  # v0.90: ベトベトマーカー（(マーカーの種類, 増やす数)）
    if active.conditions.confused and not _confusion_check(state, cmd.player, active, action="retreat", effect="retreat"):
        # 「にげる」は失敗。トラッシュしたエネルギーは取り戻せず、入れ替えはしない（p.311 の手順 3・4。v0.3c）
        active.retreat_failed_turn = state.turn_number
        state.add_event(
            "retreat_failed", player=cmd.player, pokemon=active.card, pokemon_id=active.pokemon_id, discarded=discard, **cost_log,
        )
        return_discarded_energy(state, returns)
        return
    # ついているカード・ダメージはいっしょに移動する（p.311）
    require_can_leave(state, cmd.player, active)  # v0.93: 宣言の前に拒否した（ここに来たら確かめの漏れ）
    p.active, p.bench[index] = p.bench[index], active
    state.add_event("retreat", player=cmd.player, discarded=discard, old_active=active.card, new_active=cmd.new_active, **cost_log)
    return_discarded_energy(state, returns)
    # ベンチに戻ったら、特殊状態はすべて消える（p.311・p.322。v0.3a）
    clear_special_conditions(state, cmd.player, active, RETREAT)
    # ワザによる持続する効果も消える（p.311「…や、「持続する効果」は、すべて消えてなくなります」・p.322。v0.4b）。特殊状態とは別の処理
    remove_persistent_effects(state, cmd.player, active, RETREAT)
    remove_source_left_effects(state, cmd.player, active)  # v0.92: 発生源がバトル場をはなれたら消える効果（くろいまなざし・ヨーギラスのにらみつける）
    mark_returned_to_bench(active)  # v0.48: 特殊能力で色を変えた記録に、ベンチにもどったことを残す（VS1）
    discard_on_leaving_active(state, cmd.player, active)  # v0.65: バトル場をはなれた時にトラッシュするついているトレーナー（変わり身の術）
    balloon = tool_effect_of(state, active, BalloonBerry)
    if balloon is not None:
        discard_attached_tool(state, active, balloon[0], TOOL_RETREAT)  # v0.81: ふうせんのみ（「にげる」とき、このカードをトラッシュする）
    # v0.87（docs/movement-damage-reactions-v0.87.md 3 章）: 入れ替えの事実への反応（ベンチにもどったポケモンの［やけのこり］・控えから出たポケモンへの相手の［まきびし］）。
    # 反応があれば、相手の［おとしあな］も同じ時点の反応として扱い（順番は番のプレイヤー）、そのあと場を整える（きぜつ・交代・同じ番）。なければ v0.86 までと同じ
    movement.note_switch(state, cmd.player, active, p.active)
    moves = movement.take(state)
    if moves:
        if retreat_trap_powers(state, cmd.player):
            first = moves[0]
            moves = ((first[0], first[1], first[2] + ((reactions.SINKHOLE, cmd.player, active.pokemon_id, 1),), first[3]),) + moves[1:]
        reactions.run(state, moves + ((reactions.SETTLE_RETREAT, cmd.player, active.pokemon_id),), context, _REACTION_HOOKS)
        return
    resolution.after_retreat(state, context, cmd.player, active)  # v0.61: 相手の［おとしあな］（入れ替えのあと。きぜつ・交代・同じ番）


def _sinkhole_check(state: GameState, player: int, active: PokemonInPlay, index: int) -> None:
    """v0.61: 「にげる」の前に、相手の［おとしあな］で決められない場合を確かめる（状態・乱数・ログを変えない）。

    - SH1: はたらく［おとしあな］があり、にげるポケモンがこんらん状態（「にげる」に失敗したときにはたらくか決まらない）、または受けるダメージ（受けるダメージを変える常にはたらく
      特殊能力を当てはめた量）が、入れ替えの前（バトル場）と後（ベンチ）で違う
    - SC1: 2 つ以上の［おとしあな］で、入れ替えのあとに力がはたらく［ずらかる］を持つにげるポケモンの残りHPが、途中で「10」を通る（すべて投げてからか、1 つずつかで結果が変わる）"""
    traps = retreat_trap_powers(state, player)
    if not traps:
        return
    if active.conditions.confused:
        raise UnsupportedError(SINKHOLE_TIMING_CODE, f"こんらん状態のポケモン {active.pokemon_id} の「にげる」: {SINKHOLE_TIMING_REASON}")
    trial = state.clone()
    tp = trial.players[player]
    moved = tp.active
    tp.active, tp.bench[index] = tp.bench[index], moved
    clear_special_conditions(trial, player, moved, RETREAT)
    remove_persistent_effects(trial, player, moved, RETREAT)
    for owner, holder, slot in traps:
        before, _ = received_power_damage(state, player, active, holder, slot.effect.amount)
        trial_holder = trial.find_pokemon(holder.pokemon_id)[1]
        after, _ = received_power_damage(trial, player, moved, trial_holder, slot.effect.amount)
        if before != after:
            raise UnsupportedError(SINKHOLE_TIMING_CODE, f"ポケモン {active.pokemon_id} の受けるダメージ（バトル場 {before}・ベンチ {after}）: {SINKHOLE_TIMING_REASON}")
        bench_guard_outside_attack_check(trial, player, moved, after)  # v0.65: ベンチにもどったポケモンの［おとしあな］のダメージ（エンジンの未対応）
    if len(traps) > 1:
        amount = traps[0][2].effect.amount
        for _, pokemon, slot in scram_slots(trial):
            if pokemon is not moved or not scram_working(trial, pokemon, slot):
                continue
            remaining = max_hp(trial, pokemon) - pokemon.damage
            if any(remaining - amount * k == slot.effect.remaining_hp for k in range(1, len(traps))):
                raise UnsupportedError(SCRAM_TIMING_CODE, f"ポケモン {active.pokemon_id}・［おとしあな］{len(traps)} つ: {SCRAM_TIMING_REASON}")


def _retreat_max_hp_drop_check(state: GameState, player: int, discard: tuple[int, ...], index: int) -> None:
    """「にげる」で、最大HPがのっているダメージ以下に下がる場のポケモンがいれば止める（v0.48。MH1）。複製の上で、エネルギーをトラッシュした状態（こんらんで失敗した
    ときの結果）と、ベンチにもどした状態（成功したときの結果）を作り、``effects.max_hp_drops`` で比べる。渡した状態・乱数・ログは変えない。"""
    trial = state.clone()
    tp = trial.players[player]
    active = tp.active
    for uid in discard:
        active.energy.remove(uid)
        tp.discard.append(uid)
    drops = max_hp_drops(state, trial)
    if not drops:
        tp.active, tp.bench[index] = tp.bench[index], active
        clear_special_conditions(trial, player, active, RETREAT)
        remove_persistent_effects(trial, player, active, RETREAT)
        drops = max_hp_drops(state, trial)
        # v0.61（SC2）: ベンチにもどって特殊状態が消え、残りHPが「10」で消えていた［ずらかる］の力がもどる（こんらんのコインの前に止める）
        restored = scram_restored(state, trial)
        if restored and not drops:
            raise scram_restored_error(restored)
    if drops:
        raise max_hp_drop_error(drops)


# ---------------------------------------------------------------- トレーナー（v0.2b）


def _play_trainer(state: GameState, cmd: PlayTrainer, context: resolution.Context) -> None:
    """手札のトレーナーカードを使う（p.310「トレーナーカードを使う」）。

    - 自分の番（番の最初に引いたあと、ワザの前）に、1 番に何枚でも使える（p.309, p.310）。
      決定を待っている間（別のトレーナーの途中を含む）は使えない（p.310「その…起こることをすべて
      すませてからでないと、他のことはできません」）。
    - 効果の登録表に実装が登録されたトレーナーだけ使える。使うための条件・原典で決められない場合の
      確認（``TrainerEffect.check_playable``）を通ってから、手札から出す。
    - 手札から出して相手に見せ、名前を伝え（ログの ``play_trainer``）、説明にしたがう。説明が終わったら
      トラッシュする（``_finish_trainer``）。途中で決定を待つ間、カードは ``state.trainer_in_use`` にある。

    v0.57（docs/stadiums-v0.57.md）:

    - スタジアムカード（``effect.is_stadium``）は、手札から出したら場に出す（``_play_stadium``。トラッシュしない。古いスタジアムは持ち主のトラッシュ）
    - 場のリムーブ禁止ジムが当てはまるトレーナーは、このカードを除く手札が 2 枚以上なければ使えない（``INSUFFICIENT_CARDS_IN_HAND``。カード自身の使うための条件の確認の
      あと・手札から出す前）。手札から出したあと、カードの効果の前に 2 枚をトラッシュする（決定 ``DISCARD_FROM_HAND``。続きの情報の ``stadium_cost``）
    - 場の錯乱ジムがあれば、スタジアムカード以外のトレーナーを手札から出したあと（手順 1・2）、使うための条件を払う前に、使ったプレイヤーがコインを投げる。「うら」なら
      使えず、相手プレイヤーがかわりに使えるか聞く（``_chaos_tails``）
    """
    p = _require_turn(state, cmd.player)
    _require_in_hand(state, cmd.player, cmd.card)
    definition = state.card_def(cmd.card)
    if definition.category != "trainer":
        raise IllegalActionError("NOT_TRAINER", f"カード {cmd.card} はトレーナーカードではない")
    blockers = trainer_use_blockers(state, cmd.player)
    if blockers:
        # v0.46: 場にはたらいている［アレルギーかふん］（わるいラフレシア）があれば、誰もトレーナーカードを使えない。v0.47: プレイヤーに与えた期限のある禁止（ずつう・
        # こうしゅうは。``GameState.trainer_locks``）も同じ確かめ（2 つの記録をそれぞれの期間で判定する）。手札から出す前に拒否する（状態・乱数・ログは変わらない）。
        # ポケモンについているトレーナーの効果・使っている最中のトレーナーは止めない。ポケモンとして場に出すトレーナー（なにかの化石・ピッピ人形）も、トレーナー
        # カードを使うことなので止める。v0.57: スタジアムカードを手札から出すことも、トレーナーカードを使うことなので止める
        powers = [b[2] for b in blockers if b[0] == "power"]
        locks = [(b[2], b[3]) for b in blockers if b[0] == "lock"]  # v0.56: ワザ（ずつう・こうしゅうは）かトレーナー（ロケット団の実験の「うら」）
        detail = "・".join(([f"場のポケモン {powers} の特殊能力がはたらいている"] if powers else [])
                          + ([f"期限のある禁止（ワザ・トレーナー {[e for e, _ in locks]}）の効果（{[t for _, t in locks]} 番の終わりまで）"] if locks else []))
        raise IllegalActionError("TRAINER_PREVENTED", f"{detail}ので、トレーナーカードを使えない")
    effect = state.effects.trainer_effect(definition)
    if effect is None:
        problem = state.effects.trainer_problem(definition)
        raise UnsupportedError("UNSUPPORTED_TRAINER", f"「{definition.name_ja}」は未対応（{problem}）")
    use = TrainerUse(cmd.player, cmd.card, definition.id)
    effect.check_playable(state, use)
    extra_cost = stadium_trainer_cost(state, definition)
    if extra_cost is not None:
        needed = extra_cost[1].discard
        if len(p.hand) - 1 < needed:
            raise IllegalActionError(
                "INSUFFICIENT_CARDS_IN_HAND",
                f"場の「{state.card_def(extra_cost[0].card).name_ja}」があるので、「{definition.name_ja}」を使うには、このカードを除く手札から {needed} 枚をトラッシュする"
                f"（手札はこのカードを除いて {len(p.hand) - 1} 枚）")

    # 1・2. 手札から出して相手プレイヤーに見えるようにし、名前を伝える（p.310）
    p.hand.remove(cmd.card)
    state.trainer_in_use = TrainerInUse(cmd.player, cmd.card)
    state.add_event("play_trainer", player=cmd.player, card=cmd.card, trainer=definition.name_ja)
    if effect.is_stadium:
        _play_stadium(state, cmd.player, cmd.card, effect)
        return
    _start_trainer_use(state, use, effect, context)


def _start_trainer_use(state: GameState, use: TrainerUse, effect, context: resolution.Context) -> None:
    """手札から出した（v0.58: または外側のトレーナーの効果で相手のトラッシュから出した）トレーナーの使用を、カードの効果の前のスタジアムの段階から始める（v0.57 の
    ``_play_trainer`` の後半を分けた。動きは同じ）。``use.player`` は使うプレイヤー（費用・選ぶものはこのプレイヤーの手札・場）。

    - 場の錯乱ジムのコイン（使うための条件を払う前。1 回の使用で 1 回だけ。v0.58: 外側の使用（サイキックコントロール）のコインとは別に、内側の使用でも投げる）
    - 場のリムーブ禁止ジムの追加の条件（使うプレイヤーの手札から 2 枚。カードの効果の前）
    - 3・4. 使うための条件と、残りの説明にしたがう。決定を出したら、ここで止まり ``_resume_trainer`` から続ける"""
    definition = state.card_def(use.card)
    chaos = stadium_of(state, TrainerCoinStadium)
    if chaos is not None:
        stadium = chaos[0]
        heads = flip_coins(state, use.player, 1, source="stadium", effect=state.cards[stadium.card].card_id, card=stadium.card).results[0] is CoinSide.HEADS
        state.add_event("chaos_check", player=use.player, card=use.card, stadium_card=stadium.card, heads=heads)
        if not heads:
            _chaos_tails(state, use, effect, stadium, context)
            return
    extra_cost = stadium_trainer_cost(state, definition)
    if extra_cost is not None:
        push_trainer_decision(state, use, kind=DISCARD_FROM_HAND, player=use.player, options=tuple(state.players[use.player].hand),
                              min_choices=extra_cost[1].discard, max_choices=extra_cost[1].discard, context=(("stadium_cost", extra_cost[0].card),))
        return
    _resolve_trainer(state, effect, use, context)


def _resolve_trainer(state: GameState, effect, use: TrainerUse, context: resolution.Context) -> None:
    """トレーナーの説明にしたがう（p.310 の手順 3・4）。決定を出したら止まり、出さなければ使い終える（v0.57 で ``_play_trainer`` から分けた。動きは同じ）。"""
    outcome = effect.resolve(state, use)
    _after_trainer_step(state, effect, use, outcome, context)


def _after_trainer_step(state: GameState, effect, use: TrainerUse, outcome, context: resolution.Context) -> None:
    """トレーナーの ``resolve``・``resume`` のあと（v0.58 でまとめた）。外側のトレーナーの効果で別のカードを使う印（``UseDiscardTrainer``。サイキックコントロール）なら、
    内側の使用を始める。決定を出していなければ使い終える。"""
    if isinstance(outcome, UseDiscardTrainer):
        if state.decision is not None:
            raise RuntimeError("トレーナーの効果が決定を出したまま、別のトレーナーカードを使おうとした（エンジンの不具合）")
        _start_nested_trainer(state, use, outcome.card, context)
        return
    moves = movement.take(state)
    if moves:
        # v0.87: トレーナーの効果の入れ替え・手札から場に出させたことへの反応（［まきびし］・［やけのこり］・［ヒートプレート］）。トレーナーを使い終える前に処理する。効果が次の決定を
        # 出していれば（ワープポイントの 2 つめの入れ替え）、反応のあとに出し直す（``reactions.RESTORE``）。決定が出たら、その決定の続きに持たせる
        if isinstance(outcome, reactions.Followup):
            reactions.run(state, moves + tuple(outcome.steps), context, _REACTION_HOOKS)
            return
        if state.decision is not None:
            if state.decision.resume != "trainer":
                raise RuntimeError(f"トレーナーの効果が、再開先 {state.decision.resume!r} の決定を出したまま場を動かした（エンジンの不具合）")
            reactions.run(state, moves + (reactions.restore_step(_stash_decision(state)),), context, _REACTION_HOOKS)
            return
        if outcome is not None:
            _ends_turn(effect, outcome)
            raise RuntimeError("番を終えるトレーナーが場を動かした（今の対応カードにない組み合わせ。エンジンの不具合）")
        used = state.trainer_in_use
        reactions.run(state, moves + ((reactions.TRAINER, used.using_player, used.card, state.card_def(used.card).id),), context, _REACTION_HOOKS)
        return
    if isinstance(outcome, reactions.Followup):
        # v0.86: トレーナーの効果で場に出した・進化させたことへの反応の段（1 進化を飛ばす進化・相手に場に出させる効果・手札から出させる効果のあとの反応）。
        # 段の最後にこのトレーナーを使い終える段がある（実装が加える。決定が出たら、その決定の続きに持たせる）
        reactions.run(state, outcome.steps, context, _REACTION_HOOKS)
        return
    if state.decision is None:
        _finish_trainer(state, effect, context, end_turn=_ends_turn(effect, outcome))


def _start_nested_trainer(state: GameState, outer_use: TrainerUse, card: int, context: resolution.Context) -> None:
    """外側のトレーナー（ナツメのサイキックコントロール）の効果で、相手のトラッシュのトレーナーカード ``card`` を使い始める（v0.58。docs/stadium-reuse-special-energy-v0.58.md
    4 章）。外側の使用を ``trainer_stack`` に積み、カードを持ち主のトラッシュから使用中の場所に移す（同じ uid・持ち主のまま。複製しない・使うプレイヤーの手札に移さない）。
    ログは ``play_trainer``（``player`` は使うプレイヤー、``owner`` はカードの持ち主、``source_zone`` は ``"discard"``、``via`` は外側のカード）。そのあとは手札から使うとき
    と同じ（錯乱ジムのコイン・リムーブ禁止ジムの追加の条件・カードの効果）。"""
    outer = state.trainer_in_use
    owner = state.cards[card].owner
    if outer is None or outer.card != outer_use.card or card not in state.players[owner].discard:
        raise RuntimeError(f"外側のトレーナー {outer} の効果で使うカード {card} が、持ち主のトラッシュにない（エンジンの不具合）")
    definition = state.card_def(card)
    effect = state.effects.trainer_effect(definition)
    state.players[owner].discard.remove(card)
    state.trainer_stack = state.trainer_stack + (outer,)
    state.trainer_in_use = TrainerInUse(owner, card, user=None if outer_use.player == owner else outer_use.player, via=outer.card)
    state.add_event("play_trainer", player=outer_use.player, card=card, trainer=definition.name_ja, owner=owner, source_zone="discard", via=outer.card)
    _start_trainer_use(state, TrainerUse(outer_use.player, card, definition.id), effect, context)


def _play_stadium(state: GameState, player: int, card: int, effect) -> None:
    """手札から出したスタジアムカードを場に出す（v0.57。``zones.place_stadium``。古いスタジアムは持ち主のトラッシュ）。場に出た時の効果（せまいジム）があれば
    決定を出す（再開先 ``"stadium"``）。なければ番の続き（``Phase.MAIN``）。"""
    place_stadium(state, player, card)
    state.phase = Phase.MAIN
    effect.on_placed(state, state.stadium)


def _chaos_tails(state: GameState, use: TrainerUse, effect, stadium, context: resolution.Context) -> None:
    """錯乱ジムのコインが「うら」（v0.57。docs/stadiums-v0.57.md 7 章）: 使ったプレイヤーはそのカードを使えない（使うための条件を払わない）。相手プレイヤーがかわりに使えるか
    （``effects.borrow_unusable_reason``）を確かめ、使えるなら相手プレイヤーに聞く（決定 ``ACCEPT_REQUEST``。続きの情報の ``chaos``）。使えないなら、カードを持ち主の
    トラッシュにすてる（ログ ``chaos_not_borrowable``）。相手が使うことを選ぶと決められない（CH1 など）カード・決められない使うための条件は、選ぶと止める選択にする。"""
    borrower = 1 - use.player  # v0.58: 使うプレイヤーの相手（手札から使うなら持ち主の相手。外側のトレーナーの効果で使うなら、使うプレイヤーの相手 = カードの持ち主）
    borrowed = TrainerUse(borrower, use.card, use.card_id)
    unresolved: dict = {}
    try:
        reason = borrow_unusable_reason(state, effect, borrowed)
    except UnsupportedError as error:
        reason = None
        unresolved = {"unresolved_choices": (1,), "unresolved_code": error.code, "unresolved_reason": error.message}
    if reason is not None:
        state.add_event("chaos_not_borrowable", player=borrower, card=use.card, owner=use.player, reason=reason)
        _finish_trainer(state, effect, context, discard_only=True)
        return
    problem = effect.borrow_problem(state, borrowed)
    if problem is not None and not unresolved:
        unresolved = {"unresolved_choices": (1,), "unresolved_code": problem[0], "unresolved_reason": problem[1]}
    push_trainer_decision(state, use, kind=ACCEPT_REQUEST, player=borrower, options=(1,), min_choices=0, max_choices=1,
                          context=(("chaos", stadium.card),), **unresolved)


def _ends_turn(effect, outcome) -> bool:
    """v0.56: トレーナーの ``resolve``・``resume`` の戻り値が、番を終える印（``END_TURN``。ロケット団員の「うら」）か。``may_end_turn`` でない実装が返したらエンジンの不具合。"""
    if outcome is None:
        return False
    if outcome != END_TURN or not effect.may_end_turn:
        raise RuntimeError(f"トレーナーの実装 {type(effect).__name__} の戻り値 {outcome!r} が正しくない（エンジンの不具合）")
    return True


def _finish_trainer(state: GameState, effect, context: resolution.Context, *, end_turn: bool = False, discard_only: bool = False) -> None:
    """トレーナーを使い終えて、番の続きにもどる。

    - 使いすて（特に記述がないかぎり。p.310）: 使ったカードをトラッシュする。
    - つけて使うトレーナー（``effect.stays_in_play``。v0.2c）: 説明にしたがってポケモンについたので、
      トラッシュしない（``resolve`` が ``zones.attach_trainer`` で使用中から場に移した）。

    v0.49 までのトレーナーは、きぜつ・勝敗を起こさないので、使い終わったら自分の番（MAIN）にもどる。v0.50: 効果で自分のポケモンを退化させ、最大HPがのっている
    ダメージ以下になりうるトレーナー（``effect.may_knock_out``。退化スプレー）は、カードをトラッシュしてから（使用中のカードを残さない）、きぜつの処理・サイド・
    勝ち負け・バトル場に出す決定をする（``resolution.after_trainer``。続きは同じ番の ``Phase.MAIN``。docs/mew-devolution-spray-v0.50.md 4 章）。
    """
    used = state.trainer_in_use
    if discard_only:
        # v0.57: 錯乱ジムで使えなかった・使わなかったカード（効果を処理していない）。持ち主のトラッシュにすてて、番にもどる
        state.trainer_in_use = None
        state.players[used.player].discard.append(used.card)
        state.add_event("discard_trainer", player=used.player, card=used.card)
        _finish_outer_trainers(state)
        state.phase = Phase.MAIN
        return
    if effect.stays_in_play or effect.enters_play:
        # v0.47: ポケモンとして場に出すトレーナー（なにかの化石・ピッピ人形。``enters_play``）も、使い終わったら場にいる（トラッシュしない）
        if used is not None:
            raise RuntimeError(f"場に残るトレーナー {used.card} が、使い終わっても場にない（エンジンの不具合）")
    else:
        state.trainer_in_use = None
        state.players[used.player].discard.append(used.card)
        state.add_event("discard_trainer", player=used.player, card=used.card)
    _finish_outer_trainers(state)
    state.phase = Phase.MAIN
    if end_turn:
        # v0.56: 説明の「あなたの番は終わりになる」（ロケット団員の「うら」）。カードをトラッシュしてから、番の終わりの窓（期限 → ポケモンチェック → 次の番）に進む
        if effect.may_knock_out or effect.empties_active or effect.takes_prizes:
            raise RuntimeError(f"番を終えるトレーナー {type(effect).__name__} が、きぜつ・場をはなれる・サイドの処理も持つ（今の対応カードにない組み合わせ。エンジンの不具合）")
        # v0.63: 番を終えるのは使ったプレイヤー（``using_player``）。サイキックコントロールで相手のトラッシュから使ったカードは ``player`` が持ち主（相手）なので、
        # v0.62 まではここで NOT_YOUR_TURN になっていた（ロケット団員も同じ。docs/hidden-card-trainers-v0.63.md 8 章）
        resolution.end_turn_after_trainer(state, context, used.using_player, used.card)
        return
    if (effect.may_knock_out or effect.empties_active or effect.takes_prizes or any(p.active is None for p in state.players)
            or any(not state.is_face_down(x) and knocked_by_hp(state, x) for side in state.players for x in side.in_play())):
        # v0.87: トレーナーの効果の入れ替え・手札から場に出させたことへの反応のダメージ（［まきびし］・［ヒートプレート］・爆発ジム）で HP 以上になったポケモンも
        # v0.67: うらのカード（マチスの秘策）を効果の対象にしておもてにし、「たねポケモン」でなくトラッシュして、バトル場が空いたとき（ねむれ!ねむれ!・バトル場は穴だらけ!
        # など）も、使い終わってから勝ち負けの判定・バトル場に出す決定をする
        # v0.52: 自分のバトル場のポケモンを場からはなれさせうるトレーナー（``empties_active``。ポケモン回収）も、使い終わってから勝ち負けの判定・バトル場に出す決定をする
        # v0.56: 効果でサイドを取るトレーナー（``takes_prizes``。マチスの交渉）も、使い終わってから勝ち負けを判定する（効果の途中で対戦を終えない）
        resolution.after_trainer(state, context)


def _stash_decision(state: GameState) -> tuple:
    """v0.87: 待っている決定を、反応のあとに出し直す段の値にして状態から除く（``reactions.RESTORE``）。番号は出し直すときに新しくする。"""
    d = state.decision
    state.decision = None
    return (d.kind, d.player, d.options, d.min_choices, d.max_choices, d.resume, d.context)


def _finish_outer_trainers(state: GameState) -> None:
    """内側のトレーナーを使い終えたあと（v0.58）、その使用を待っていた外側のトレーナー（ナツメのサイキックコントロール。``trainer_stack``）を、内側から順に使い終える
    （持ち主のトラッシュにすてる。ログ ``discard_trainer``）。外側のトレーナーには、内側の使用のあとの説明はない。内側の効果のあとのきぜつ・勝ち負け・番の終わりは、
    外側のカードもトラッシュしてから（使用中のカードを残さない）。"""
    while state.trainer_stack:
        outer = state.trainer_stack[-1]
        state.trainer_stack = state.trainer_stack[:-1]
        if state.trainer_in_use is not None:
            raise RuntimeError(f"外側のトレーナー {outer} を使い終えるとき、使用中のトレーナー {state.trainer_in_use} が残っている（エンジンの不具合）")
        state.players[outer.player].discard.append(outer.card)
        state.add_event("discard_trainer", player=outer.player, card=outer.card)


def _resume_trainer(state: GameState, decision, choices: tuple[int, ...], context: resolution.Context) -> None:
    """トレーナーの効果の途中で出した決定の続き。決定がなくなったら、カードをトラッシュして番にもどる。

    v0.57: スタジアムがトレーナーの使用に加えた段階（錯乱ジムの相手プレイヤーへの問い ``chaos``・リムーブ禁止ジムの追加の条件 ``stadium_cost``）の答えは、カードの効果
    （``resume``）ではなくここで処理する。"""
    player, card, card_id = decision.context_value("use")
    entry = state.effects.trainer_entry(card_id)
    use = TrainerUse(player, card, card_id)
    if decision.context_value("chaos") is not None:
        # 錯乱ジム: 相手プレイヤーがかわりに使うか（選ばない = 使わない）
        borrower = decision.player
        state.add_event("chaos_answered", player=borrower, card=card, owner=player, accepted=bool(choices))
        if not choices:
            _finish_trainer(state, entry.effect, context, discard_only=True)
            return
        # v0.58: 持ち主・外側の使用（``via``）は変えず、使うプレイヤーだけを変える（外側のトレーナーの効果で使っているカードでは、借りるのが持ち主自身のことがある）
        current = state.trainer_in_use
        state.trainer_in_use = TrainerInUse(current.player, card, user=None if borrower == current.player else borrower, via=current.via)
        _resolve_trainer(state, entry.effect, TrainerUse(borrower, card, card_id), context)
        return
    if decision.context_value("stadium_cost") is not None:
        # リムーブ禁止ジム: 手札から選んだカードをトラッシュしてから、カードの効果にしたがう（カード自身の条件は効果の中で払う）
        pay_stadium_trainer_cost(state, player, tuple(choices), decision.context_value("stadium_cost"))
        _resolve_trainer(state, entry.effect, use, context)
        return
    outcome = entry.effect.resume(state, use, decision, choices)
    _after_trainer_step(state, entry.effect, use, outcome, context)


# ---------------------------------------------------------------- ポケモンパワー（特殊能力。v0.5）


def _use_pokemon_power(state: GameState, cmd: UsePokemonPower, context: resolution.Context) -> None:
    """自分の場のポケモンの特殊能力（ポケモンパワー）の使用を宣言し、説明にしたがって処理する（p.311「ポケモンの特殊能力を使う」・
    p.323「14 ポケモンの特殊能力」。v0.5）。

    - 使えるのは、使用を宣言して使う特殊能力だけ（自動的にはたらく・常にはたらいている特殊能力は宣言しない。p.311・p.323）。
      効果の登録表に実装が登録された特殊能力だけ（``EffectRegistry.power_effect``。登録がなければ ``UNSUPPORTED_POKEMON_POWER``）。
    - 自分の番（``Phase.MAIN``）だけ（``_require_turn``）。番の最初に引くまでは何もできず（p.309）、ワザを使ったら番は終わり（p.309）、
      決定を待つ間（トレーナー・ワザ・きぜつのあとの決定）はほかのことをしない（p.309・p.310・p.311）。v0.5 の対応カード（エナジート
      ランス）の説明は「自分の番の中で」。相手の番・ポケモンチェック（どちらの番でもない。p.323）に使う特殊能力は未対応。
    - 特殊能力を使うポケモンは、自分の場（バトル場・ベンチ）のポケモンの番号（``cmd.pokemon``）。「特に指示されていないかぎり、
      ベンチにいるポケモンも特殊能力を使うことができます」「エネルギーカードをつけていなくても」（p.311・p.323）。どの特殊能力が
      あるかは、いちばん上のカードで決める（進化したら進化前の特殊能力は使えない。p.310）。
    - 手順（p.311）: 1. 使うポケモンを示し、名前を伝えて宣言する（ログ ``pokemon_power``）→ 2. 使うための条件にしたがう（実装の
      ``check_usable``。したがえなければ使えない）→ 3. 説明にしたがって処理する（実装の ``resolve``）。確かめることはどれも宣言の
      前に済ませるので、拒否したら状態・乱数・ログは変わらない。
    - 使っても番は終わらない（``Phase.MAIN`` のまま。ワザのあとの処理（解決の基盤の ``flow._finish_attack``）を通らない）。「特に指示されていないかぎり、特殊能力は
      いつでも、何度でも使用を宣言することができます」（p.323）ので、回数を数えない（回数の制限のある特殊能力は未対応）。
    - v0.8: 常にはたらいている特殊能力（``effects.SuppressOtherPowers``。ベトベトンの「かがくへんかガス」）は宣言しないので、使おうと
      したら ``POWER_NOT_DECLARABLE``（v0.9 の自動的にはたらく特殊能力 ``effects.AttackImmunityOnHeads``（ゴーストの「とうめい」）も
      同じ。ワザを受けるときにワザの処理の中で評価する。``effects.attack_reaches``。v0.10 のダメージを受けたときに自動的にはたらく
      特殊能力 ``effects.CounterattackDamage``（カイリキーの「はんげき」）も同じ。``effects.deal_attack_damage``・
      ``effects.finish_damage_elements``）。宣言する特殊能力は、登録の確認のあと、
      パワーごとの確認（``check_usable``）の前に、今はたらいている「かがくへんかガス」に消されていないかを今の状態から求めて
      （``continuous.suppressors_of``）、消されていれば ``POWER_SUPPRESSED``（「使えず、その力も消える」。p.48・p.323）。p.311 の
      「そのとき使うことのできるもの」を、宣言の前に確かめる（宣言もない。状態・乱数・ログは変わらない）。自分の場・相手の場の
      どちらのかがくへんかガスでも同じ（p.48 の解説）。
    - v0.7 のダメージスワップ（``effects.MoveDamageCounter``）は、のせかえでポケモンがきぜつするなら ``check_usable`` で拒否するので、
      特殊能力の処理のあとにきぜつの処理（トラッシュ・サイド・交代）はない。もし処理のあとに HP 以上のダメージのポケモンがいれば、
      ``apply_command`` の不変条件（場のポケモンのダメージは HP より小さい）が ``StateIntegrityError`` にする。
    - v0.42（docs/power-decisions-v0.42.md）: 「自分の番ごとに1回」の特殊能力（``PowerEffect.once_per_turn``）は、宣言のときに使ったことを状態に記録する
      （``GameState.power_uses_this_turn``。コインの「うら」・決定の途中でも使ったことになる。ログから数えない）。2 回目は実装の ``check_usable`` が
      ``POWER_ALREADY_USED``（``effects.require_power_not_used``。特殊状態の確認のあと）。処理の途中で決定を出す特殊能力（ヒーリング・かおりのわな・
      ぶっしつこうかん）は、実装が ``decisions.push_power_decision``（再開先 ``"power"``）で止まり、答えのあと ``_resume_power`` が続ける。決定を待つ間は
      番のプレイヤーの番のまま（ほかのコマンドは受け付けない）。処理が終わったら（決定がなくなったら）、``resolution.after_power`` が場を整える:
      ダメージカウンターをのせて HP 以上になったポケモン（ゲンガーの「のろい」。きぜつの制限がない）のきぜつ・サイド・勝ち負け・ふしちょう・交代、
      自分を手札にもどして空いたバトル場（メノクラゲの「おくびょう」。きぜつではない）の勝ち負け・交代。そのあと番のプレイヤーの番にもどる
      （続き ``CONTINUE_TURN``。ワザのあとと違い、番は終わらない）。
    """
    p = _require_turn(state, cmd.player)
    user = p.find_by_pokemon_id(cmd.pokemon)
    if user is None:
        if state.players[1 - cmd.player].find_by_pokemon_id(cmd.pokemon) is not None:
            raise IllegalActionError("POKEMON_NOT_YOURS", "相手の場のポケモンの特殊能力は使えない")
        raise IllegalActionError("POKEMON_NOT_IN_PLAY", f"場のポケモンの番号 {cmd.pokemon!r} は自分の場にいない")
    # v0.49（docs/virtual-attacks-transformation-v0.49.md 2 章）: 特殊能力は、印刷したカード（``cmd.card``。None なら今の姿のカード。ふつうはいちばん上のカードで
    # v0.48 までと同じ）と位置で指す。ポケモンが今持つ特殊能力（``powers_of``。「ばける」でのせたカードの特殊能力と、その下のカードの「ばける」）の中から探す。
    # ［へんしん］で同じカードとしてあつかう相手のカードの特殊能力を持つかは決められない（TF1。宣言の前に止める）
    form = current_form(state, user)
    card = form.card if cmd.card is None else cmd.card
    slot = next((s for s in powers_of(state, user) if s.card == card and s.key.power_index == cmd.power), None)
    if slot is None:
        if form.kind == FORM_TRANSFORM and card == form.card and 0 <= cmd.power < len(state.card_def(card).powers):
            raise UnsupportedError(
                TRANSFORM_POWER_CODE,
                f"場のポケモン {user.pokemon_id} の［へんしん］で同じカードとしてあつかうカード {card} の特殊能力"
                f"「{state.card_def(card).powers[cmd.power].name_ja}」: {TRANSFORM_POWER_REASON}",
            )
        name = form_def(state, user).name_ja
        where = "" if cmd.card is None else f"（カード {cmd.card!r} の）"
        raise IllegalActionError("NO_POKEMON_POWER", f"場のポケモン {user.pokemon_id}（{name}）に{where} {cmd.power!r} 番目の特殊能力はない")
    definition = state.definitions[slot.key.card_id]
    power = slot.power
    effect = slot.effect
    if effect is None:
        problem = state.effects.power_problem(definition.id, power)
        raise UnsupportedError("UNSUPPORTED_POKEMON_POWER", f"特殊能力「{power.name_ja}」は未対応（{problem}）")
    if not effect.declared:
        raise IllegalActionError(
            "POWER_NOT_DECLARABLE",
            f"特殊能力「{power.name_ja}」は使用を宣言しない（常にはたらく・決められたときに自動的にはたらく特殊能力。p.311・p.323）",
        )
    suppressors = suppressors_of(state, power)
    if suppressors:
        names = "・".join(f"{pid}（{state.card_def(state.find_pokemon(pid)[1].card).name_ja}）" for pid in suppressors)
        raise IllegalActionError(
            "POWER_SUPPRESSED",
            f"場のポケモン {names}の特殊能力がはたらいているので、特殊能力「{power.name_ja}」は使えず、その力も消えている（p.48・p.323）",
        )
    goop = goop_gas_effects(state)
    if goop:
        # v0.59: まきちらせ!ベトベトガス（「おたがいの場のすべてのポケモンは特殊能力を使うことができず、その力も消える」）。かがくへんかガスと同じコード
        raise IllegalActionError(
            "POWER_SUPPRESSED",
            f"トレーナー「{state.card_def(goop[0].source_card).name_ja}」（カード {goop[0].source_card}）の効果がはたらいているので、特殊能力「{power.name_ja}」は"
            "使えず、その力も消えている",
        )
    if powers_stopped(state, user) is not None:
        # v0.86: わるいモココの「スタンウェーブ」（「次の自分の番が終わるまで、このワザを受けた相手は「特殊能力」を使うことができず、その効果も消える」）。かがくへんかガスと
        # 同じコード（使えず、その力も消えている）。止まるのはこのポケモンの特殊能力だけ
        raise IllegalActionError(
            "POWER_SUPPRESSED",
            f"場のポケモン {user.pokemon_id} は、相手のワザ（スタンウェーブ）の効果で特殊能力を使うことができず、その効果も消えている",
        )
    if power_suppressed(state, power, user):
        # v0.92: ワザで与えた期限のある抑止（ナツメのゲンガーの「やみのはどう」・オールクリアのワザを使っているあいだ）と、相手の場だけの「ふしぎなガス」（v0.87。使用の宣言を
        # 拒否していなかった。docs/power-suppression-lasting-locks-v0.92.md 8 章）。``continuous.power_suppressed`` の答えで、かがくへんかガス・まきちらせ!ベトベトガスと同じコード
        raise IllegalActionError(
            "POWER_SUPPRESSED",
            f"ワザの効果（特殊能力を使うことができず、その力も消える）がはたらいているので、場のポケモン {user.pokemon_id} の特殊能力「{power.name_ja}」は使えない",
        )
    if powers_use_prevented(state, user) is not None:
        # v0.59: わるいアーボックの「ショックアイ」（「次の相手の番の終わりまで、そのポケモンは特殊能力を使うことができない」）。宣言して使う特殊能力の使用だけを止める
        # （CR-CHEMICAL-GAS-USE-VS-POWER の読み方）。パワーごとの確認・宣言の前
        raise IllegalActionError(
            "POWER_USE_PREVENTED",
            f"場のポケモン {user.pokemon_id} は、相手のワザの効果で、次の相手の番の終わりまで特殊能力を使うことができない",
        )
    use = PowerUse(cmd.player, user.pokemon_id, slot.key, cmd.energy, cmd.source, cmd.target, card=None if slot.card == user.card else slot.card)
    effect.check_usable(state, use)
    if effect.once_per_turn and power_reuse_after_devolution(state, use):
        # v0.50: 今の番に退化してまたいちばん上になったカードで、退化の前（進化させる前）にこの番に使っていた（DV3。パワーごとの確かめがすべて通ったあと）
        raise UnsupportedError(POWER_REUSE_AFTER_DEVOLUTION_CODE, f"ポケモン {use.pokemon_id}: {POWER_REUSE_AFTER_DEVOLUTION_REASON}")

    # 1. 宣言（p.311）。2. の条件は check_usable で確かめた。3. 説明にしたがって処理する。v0.49: いちばん上のカードでないカード（「ばける」でのせたカード）の
    # 特殊能力なら、そのカード（``card``・``card_id``。表のカード）も書く
    extra = {} if use.card is None else {"card": use.card, "card_id": slot.key.card_id}
    state.add_event(
        "pokemon_power", player=cmd.player, pokemon=user.card, pokemon_id=user.pokemon_id, power=power.name_ja, power_index=cmd.power, **extra
    )
    if effect.once_per_turn:
        # v0.42: 「自分の番ごとに1回」の記録は宣言のとき（v0.31 のしぜんになおるは処理の中で記録していた。状態の結果は同じ）。v0.49: 印刷したカードで区別する
        state.power_uses_this_turn = state.power_uses_this_turn + (power_use_record(state, use),)
    attached = state.find_pokemon(use.target) if isinstance(effect, AttachEnergyFromHand) else None
    pre_status = None if attached is None else (int(attached[1].conditions.asleep), int(attached[1].conditions.paralyzed), int(attached[1].conditions.confused))
    outcome = effect.resolve(state, use)
    if attached is not None:
        # v0.86: あまごい（手札からつける特殊能力）でつけた事実への反応（［エナジーしんか］・［かんでん］。``reactions``）。特殊能力の処理のあとに続ける
        steps = reactions.attach_steps(state, cmd.player, attached[0], attached[1], (use.energy,), pre_status)
        if steps is not None:
            outcome = reactions.Followup(steps)
    _after_power_step(state, use, context, steps=outcome.steps if isinstance(outcome, reactions.Followup) else ())


def _after_power_step(state: GameState, use: PowerUse, context: resolution.Context, converted=None, *, steps: tuple = (), used: bool = True,
                      defer: bool = False) -> tuple | None:
    """特殊能力の処理（宣言・決定への答え）のあと（v0.42）: 決定を出していれば待つ（再開先 ``"power"`` だけ）。出していなければ、処理のあとの場を整える
    （``resolution.after_power``。きぜつ・空いたバトル場。なければ番のプレイヤーの ``Phase.MAIN``）。

    v0.43: トレーナーの効果の途中で場に出たポケモンの、場に出たときの特殊能力（``use.return_to``。1 進化を飛ばして進化させるトレーナーで場に出た 2 進化ポケモン）
    なら、そのあとトレーナーの処理（使い終えたカードをトラッシュ）にもどる。特殊能力の処理のあとにきぜつ・バトル場に出す決定が来る組み合わせは今の対応カードでは
    起こらない（そのトレーナーで場に出る、場に出たときの特殊能力を持つカードは、きぜつさせない特殊能力だけ）ので、来たらエンジンの不具合として止める。"""
    moves = movement.take(state)
    if moves and state.decision is not None:
        # v0.87: 特殊能力の効果の入れ替えへの反応のあとに、特殊能力の次の決定を出し直す
        if state.decision.resume != "power" or steps:
            raise RuntimeError(f"特殊能力 {use.key} が場を動かしたあと、再開先 {state.decision.resume!r} の決定・続きの段を出した（エンジンの不具合）")
        tail = moves + (reactions.restore_step(_stash_decision(state)),)
        if defer:
            return tail
        reactions.run(state, tail, context, _REACTION_HOOKS)
        return None
    if state.decision is not None:
        if state.decision.resume != "power":
            raise RuntimeError(f"特殊能力 {use.key} の処理の途中で、再開先 {state.decision.resume!r} の決定を出した（エンジンの不具合）")
        if steps:
            raise RuntimeError(f"特殊能力 {use.key} が決定を出したまま、続きの段を返した（エンジンの不具合）")
        return
    effect = state.effects.power_entry(use.key.card_id, use.key.power_index).effect
    if moves:
        # v0.87: 特殊能力の効果の入れ替え（かおりのわな・［かけつける］など）への反応（［まきびし］・［やけのこり］）を処理してから、使用後の処理（きぜつ・空いたバトル場）
        if converted is not None:
            raise RuntimeError(f"特殊能力 {use.key} が場を動かし、使用後の処理への指示も返した（エンジンの不具合）")
        steps = moves + ((reactions.SETTLE_POWER,),) + tuple(steps)
    else:
        resolution.after_power(state, context, knock_outs=effect.may_knock_out, converted=converted)
    # v0.86: 処理のあとの続き（docs/entry-energy-evolution-reactions-v0.86.md 2 章）: 反応の段（あまごい・［うか］のあとの反応）→ もどる先のトレーナーを使い終える（v0.43。
    # v0.85 までは、そのあいだにきぜつ・サイド・バトル場に出す決定が来ることを扱っていなかった。来たら、その決定の続きに持たせる）→ ［おたけび］の「使ったら、自分の番は終わる」
    tail = tuple(steps)
    if use.return_to is not None:
        kind, player, card, card_id = use.return_to
        current = state.trainer_in_use
        if kind != "trainer" or current is None or (current.using_player, current.card) != (player, card):  # v0.58: もどる先は使うプレイヤーと使用中のカード
            raise RuntimeError(f"特殊能力 {use.key} のもどる先 {use.return_to!r} が、使用中のトレーナー {state.trainer_in_use} ではない（エンジンの不具合）")
        tail += ((reactions.TRAINER, player, card, card_id),)
    if used and getattr(effect, "ends_turn", False):
        tail += ((reactions.END_TURN, use.player, str(use.key)),)
    if defer:
        # 決定への答えから呼ばれた: 答えた決定の続き（``followup``。使用中のトレーナーを使い終えるなど）とまとめて処理する（番を終える段はその最後。``reactions.merge``）
        return tail
    reactions.run(state, tail, context, _REACTION_HOOKS)
    return None


def _resume_power(state: GameState, decision, choices: tuple[int, ...], context: resolution.Context) -> tuple | None:
    """特殊能力の処理の途中で出した決定の続き（v0.42）。続きの情報（``"use"``）から実装を引き、``resume`` を呼ぶ（宣言・回数の記録・コインは繰り返さない）。
    v0.86: 処理のあとの段を返す（呼ぶ側が、答えた決定の続きとまとめて処理する）。"""
    player, pokemon_id, card_id, power_index = decision.context_value("use")
    definition = state.definitions[card_id]
    effect = state.effects.power_effect(definition.id, definition.powers[power_index])
    if effect is None:
        raise RuntimeError(f"特殊能力の決定の続きの特殊能力 {card_id}@power{power_index} が登録されていない（不変条件で拒否するはず。エンジンの不具合）")
    use = PowerUse(player, pokemon_id, PowerKey(card_id, power_index), return_to=decision.context_value("return_to"),
                   card=decision.context_value("power_card"))
    state.phase = Phase.MAIN
    if decision.kind == ENTRY_POWER:
        # v0.43: 場に出たときに使える特殊能力の使う機会。選ばなければ使わない（ログ entry_power_declined。もう使えない）。選んだら宣言して（ログ pokemon_power の
        # entry）、説明にしたがって処理する（そのあとの決定・使用後の処理は宣言する特殊能力と同じ）
        _, pokemon = state.find_pokemon(pokemon_id)
        name = definition.powers[power_index].name_ja
        if not choices:
            state.add_event("entry_power_declined", player=player, pokemon=pokemon.card, pokemon_id=pokemon_id, power=name, power_index=power_index)
            return _after_power_step(state, use, context, used=False, defer=True)
        state.add_event("pokemon_power", player=player, pokemon=pokemon.card, pokemon_id=pokemon_id, power=name, power_index=power_index,
                        entry=decision.context_value("entry"))
        outcome = effect.resolve(state, use)
        return _after_power_step(state, use, context, steps=outcome.steps if isinstance(outcome, reactions.Followup) else (), defer=True)
    converted = effect.resume(state, use, decision, choices)  # v0.59: ［エネエネ］は使用後の処理への指示（``SelfKnockOutToEnergy``）を返す。ほかは None
    if isinstance(converted, reactions.Followup):
        # v0.86: ［うか］で山札から進化したあとの反応（［れんさしんか］）の段
        return _after_power_step(state, use, context, steps=converted.steps, defer=True)
    return _after_power_step(state, use, context, converted, defer=True)


def _use_stadium(state: GameState, cmd: UseStadium, context: resolution.Context) -> None:
    """場のスタジアムカードの、自分の番に使ってよい効果を使う（v0.57。docs/stadiums-v0.57.md 4 章。タマムシシティジム・セキチクシティジム・ヤマブキシティジム）。

    - 自分の番（``Phase.MAIN``）だけ。カードの持ち主でないプレイヤーも使える（お互いのプレイヤーの場に出ているカード）
    - 確かめる順番: 番・段階 → 場のスタジアムがある（``NO_STADIUM``）→ 実装の ``check_activation``（使う効果がない ``STADIUM_NOT_USABLE``・選ばせるもの・回数・
      決められない場合）。どれも状態を変える前
    - 使う（ログ ``stadium_used``）→「自分の番ごとに1回」なら記録（``stadium_uses_this_turn``。「うら」でも使ったことになる。v0.74 から ``records_uses``。回数の書かれていない
      PRN-027 のラッキースタジアムも、同じ番の再使用（LK1）を確かめるために記録する）→ 実装の ``activate``。決定を出したら
      再開先 ``"stadium"``（``_resume_stadium``）で続ける。終わったら空いたバトル場（セキチクシティジムでバトル場のポケモンを山札にもどした）の勝ち負け・交代
      （``resolution.after_stadium``）。番は終わらない
    - トレーナーカードを手札から使うこと・特殊能力の使用ではない（かがくへんかガス・特殊状態は関係しない）。トレーナーの使用の禁止の対象かは STB1
    """
    _require_turn(state, cmd.player)
    found = stadium_in_play(state)
    if found is None:
        raise IllegalActionError("NO_STADIUM", "場にスタジアムカードがない")
    stadium, effect = found
    effect.check_activation(state, cmd.player, cmd.energy, stadium)
    state.add_event("stadium_used", player=cmd.player, card=stadium.card, owner=stadium.owner)
    if effect.records_uses:  # v0.74: 「自分の番ごとに1回」と、同じ番の再使用を確かめる効果（PRN-027 のラッキースタジアム）
        state.stadium_uses_this_turn = state.stadium_uses_this_turn + ((cmd.player, stadium.card),)
    effect.activate(state, cmd.player, cmd.energy, stadium)
    if state.decision is None:
        resolution.after_stadium(state, context)


def _resume_stadium(state: GameState, decision, choices: tuple[int, ...], context: resolution.Context) -> None:
    """場のスタジアムの効果の途中で出した決定の続き（v0.57。再開先 ``"stadium"``。段階 ``stage``）。

    - ``narrow``（せまいジムが場に出た時）・``fuchsia``（セキチクシティジムの「おもて」）: 場のスタジアムの実装の ``resume_stadium``。決定がなくなったら、空いたバトル場の
      勝ち負け・交代（``resolution.after_stadium``）
    - ``evolution_heal``（トキワシティジム）: 答え（``effects.apply_evolution_heal``）のあと、続き ``after_heal``（(``"entry"``, 手札から出したか, もどる先)）にもどる: 場に出たとき
      の特殊能力の機会（v0.43）→ もどる先がトレーナーなら、そのトレーナーを使い終える"""
    stage = decision.context_value("stage")
    card = decision.context_value("stadium")
    state.phase = Phase.MAIN
    if stage == "evolution_heal":
        found = state.find_pokemon(decision.context_value("pokemon"))
        if found is None:
            raise RuntimeError(f"トキワシティジムの決定のポケモン {decision.context_value('pokemon')} が場にいない（エンジンの不具合）")
        owner, pokemon = found
        apply_evolution_heal(state, owner, pokemon, card, bool(choices))
        tag, from_hand, return_to = decision.context_value("after_heal")
        if tag == "followup":
            return  # v0.86: 進化への反応（場に出たときの特殊能力・［れんさしんか］）ともどる先は、この決定の続き（``followup``）にある（``_answer_decision`` が続ける）
        return_to = tuple(return_to) or None
        if offer_entry_power(state, owner, pokemon, from_hand=bool(from_hand), return_to=return_to):
            return
        if return_to is not None:
            kind, _, trainer, card_id = return_to
            if kind != "trainer" or state.trainer_in_use is None or state.trainer_in_use.card != trainer:
                raise RuntimeError(f"トキワシティジムの続きのもどる先 {return_to!r} が、使用中のトレーナー {state.trainer_in_use} ではない（エンジンの不具合）")
            _finish_trainer(state, state.effects.trainer_entry(card_id).effect, context)
        return
    found = stadium_in_play(state)
    if found is None or found[0].card != card:
        raise RuntimeError(f"スタジアムの決定（{stage}）のスタジアム {card} が場にない（エンジンの不具合）")
    found[1].resume_stadium(state, found[0], decision, choices)
    if state.decision is None:
        resolution.after_stadium(state, context)


def _discard_from_play(state: GameState, cmd: DiscardFromPlay, context: resolution.Context) -> None:
    """自分の場のなにかの化石・ピッピ人形（進化カードがのっていないもの）を、自分の番の好きなときにトラッシュにすてる（v0.47。カードの文面「自分の番の好きなときに
    （自分のトラッシュに）すてることができる」。docs/fossil-hidden-info-v0.47.md 3 章）。

    - 自分の番（``Phase.MAIN``）だけ。トレーナーカードを使うことでも、特殊能力でもない（宣言しない。トレーナーの使用の禁止・かがくへんかガス・特殊状態は関係しない。
      説明に制限がない）
    - すてられるのは、いちばん上のカードが、ポケモンとして場に出したトレーナーカード（``PlayAsPokemon``。``discardable_from_play``）の場のポケモンだけ。進化カードが
      のっていれば（いちばん上が進化カード）すてられない（なにかの化石の「進化カードがのっていないときに限り」。ピッピ人形は進化カードを重ねられない）
    - ついているカードもいっしょにトラッシュする（``zones.discard_from_play``）。持続する効果は理由 ``discard_from_play`` で消す。きぜつではない（サイドはない）
    - バトル場が空いたら、特殊能力のあとと同じ使用後の処理（``resolution.after_power``。勝ち負けの判定（場にポケモンがいない。p.311）→ バトル場に出す決定）の
      あと、自分の番にもどる。確かめることはどれもトラッシュの前に済ませる（拒否したら状態・乱数・ログは変わらない）"""
    p = _require_turn(state, cmd.player)
    pokemon = p.find_by_pokemon_id(cmd.pokemon)
    if pokemon is None:
        if state.players[1 - cmd.player].find_by_pokemon_id(cmd.pokemon) is not None:
            raise IllegalActionError("POKEMON_NOT_YOURS", "相手の場のポケモンはすてられない")
        raise IllegalActionError("POKEMON_NOT_IN_PLAY", f"場のポケモンの番号 {cmd.pokemon!r} は自分の場にいない")
    effect = play_as_pokemon_effect(state, pokemon)
    if effect is None or not effect.discardable_from_play:
        name = state.card_def(pokemon.card).name_ja
        raise IllegalActionError(
            "NOT_DISCARDABLE",
            f"場のポケモン {pokemon.pokemon_id}（{name}）は、自分の番にすてられるカード（進化カードがのっていないなにかの化石・ピッピ人形）ではない",
        )
    if leave_lock(state, cmd.player, pokemon) is not None:
        # v0.93: バトル場の「バトル場をはなれられない」効果を受けたなにかの化石・ピッピ人形は、すててバトル場をはなれることもできない（「にげる」と同じく、すてる前に拒否する）
        raise IllegalActionError(LEAVE_ACTIVE_PREVENTED, f"バトル場のポケモン {pokemon.pokemon_id} は、バトル場をはなれられない（相手のワザの効果）のですてられない")
    discard_from_play(state, cmd.player, pokemon)
    remove_persistent_effects(state, cmd.player, pokemon, DISCARD_FROM_PLAY)
    resolution.after_power(state, context, knock_outs=False)


def _remove_disguise(state: GameState, cmd: RemoveDisguise) -> None:
    """タケシのキュウコンの「ばける」の「自分の番に、このカードの上にのっている「進化カード」をトラッシュして、このカードを「タケシのキュウコン」にもどしてもよい。」
    （v0.49。docs/virtual-attacks-transformation-v0.49.md 4 章）。

    - 自分の番（``Phase.MAIN``）だけ。自分の場（バトル場・ベンチ）の、「ばける」でのせたカードのあるポケモン（``PokemonInPlay.disguise``）だけ（なければ
      ``NOT_DISGUISED``）。特殊能力の使用の宣言・トレーナーカードの使用ではない（回数・使用の禁止は関係しない。「ばける」が使えなくなる特殊状態のポケモンは、
      のせたカードがもうない）
    - のせたカードを持ち主のトラッシュに置き、元の姿にもどす（``zones.remove_disguise``。ログ ``disguise_removed`` の ``reason`` は ``revert``）。ダメージ・エネルギー・
      ついているトレーナー・持続する効果・特殊状態・場のポケモンの番号は変えない。元の姿の最大HPがのっているダメージ以下になるなら、きぜつの判定の時点が決まらない
      ので受け付けない（MH1。``_apply``）"""
    p = _require_turn(state, cmd.player)
    pokemon = p.find_by_pokemon_id(cmd.pokemon)
    if pokemon is None:
        if state.players[1 - cmd.player].find_by_pokemon_id(cmd.pokemon) is not None:
            raise IllegalActionError("POKEMON_NOT_YOURS", "相手の場のポケモンの、のせたカードはトラッシュできない")
        raise IllegalActionError("POKEMON_NOT_IN_PLAY", f"場のポケモンの番号 {cmd.pokemon!r} は自分の場にいない")
    if pokemon.disguise is None:
        raise IllegalActionError("NOT_DISGUISED", f"場のポケモン {pokemon.pokemon_id} の上に「ばける」でのせたカードはない")
    remove_disguise(state, cmd.player, pokemon, reason=DISGUISE_REVERT)


# ---------------------------------------------------------------- 保留中の決定に答える・コマンドの振り分け


def _answer_decision(state: GameState, cmd, context: resolution.Context) -> None:
    """保留中の決定に答える（v0.86 から、答える決定の続き ``followup``（``reactions``）があれば、答えの処理が終わったあと（新しい決定が出たらその決定に持たせて）続ける）。"""
    decision = state.decision
    followup = () if decision is None else tuple(decision.context_value(reactions.FOLLOWUP, ()))
    prefix = _answer_decision_once(state, cmd, context)
    steps = reactions.merge(prefix or (), followup)
    if steps:
        reactions.run(state, steps, context, _REACTION_HOOKS)


def _answer_decision_once(state: GameState, cmd, context: resolution.Context) -> tuple | None:
    """保留中の決定に答える（``ResolveDecision``・v0.1 からある形の ``TakePrize``・``PromoteActive``）。確認（決定を待つ段階・決定する
    プレイヤー・決定の番号・選択）は ``checks.decision_choices``（v0.15 と同じ確認・同じ順番・同じコード）。確かめ終わった選択で、再開先が
    解決の基盤の再開先（``resolution.RESUMES``: ワザの途中・きぜつの判定・サイド・きぜつしたあとの特殊能力・バトル場に出す）なら解決の基盤、
    トレーナーの決定（``trainer``）なら ``_resume_trainer`` で続ける（決定そのものはログに残さない。選んだ結果を再開した処理がログに残す）。"""
    choices = decision_choices(state, cmd)
    decision = state.decision
    if decision.resume == reactions.RESUME:
        # v0.86: 反応の順番・使う機会・進化カード・入れ替えの決定（``reactions.answer``。続きの最初に処理する段を返す）
        state.decision = None
        state.phase = Phase.MAIN
        _designate_answer(state, decision, choices, None)
        return reactions.answer(state, decision, choices)
    if decision.resume in resolution.RESUMES:
        resolution.resume_decision(state, choices, context)
        return
    if decision.resume == "power":
        state.decision = None
        _designate_answer(state, decision, choices, None)  # v0.67: うらのカードを指定したら、おもてにする（「たねポケモン」でなければ扱えない）
        return _resume_power(state, decision, choices, context)  # v0.42（v0.86: 処理のあとの段を返す）
    if decision.resume == "stadium":
        state.decision = None
        _designate_answer(state, decision, choices, None)
        _resume_stadium(state, decision, choices, context)  # v0.57
        return
    if decision.resume != "trainer":
        raise RuntimeError(f"決定の再開先 {decision.resume!r} を続ける処理がない（不変条件で拒否するはず。エンジンの不具合）")
    state.decision = None
    if decision.context_value("chaos") is None and decision.context_value("stadium_cost") is None:
        entry = state.effects.trainer_entry(decision.context_value("use")[2])
        if _designate_answer(state, decision, choices, entry.effect):
            # v0.67: 指定したうらのカードをおもてにしたら「たねポケモン」でなくトラッシュした。対象がいないので効果は終わる（入れ替えのトレーナー）
            state.add_event("secret_plan_target_lost", player=decision.player, trainer_card=decision.context_value("use")[1])
            _finish_trainer(state, entry.effect, context)
            return
    _resume_trainer(state, decision, choices, context)


class _ReactionHooks:
    """v0.86: ``reactions.run`` が続きの段で呼ぶエンジンの処理（reactions は engine を読み込まない）。"""

    @staticmethod
    def finish_trainer(state: GameState, card_id: str, context: resolution.Context) -> None:
        _finish_trainer(state, state.effects.trainer_entry(card_id).effect, context)

    @staticmethod
    def end_turn(state: GameState, player: int, power: str, context: resolution.Context) -> None:
        resolution.end_turn_after_power(state, context, player, power)

    @staticmethod
    def settle_energy(state: GameState, context: resolution.Context) -> None:
        resolution.after_energy(state, context)

    @staticmethod
    def settle_power(state: GameState, context: resolution.Context) -> None:
        resolution.after_power(state, context, knock_outs=True)  # v0.87: 特殊能力の効果の入れ替えへの反応（［まきびし］）のダメージのきぜつ

    @staticmethod
    def settle_effects(state: GameState, context: resolution.Context) -> None:
        resolution.after_effects(state, context)  # v0.87: 手札からベンチに出したあと（［ヒートプレート］・爆発ジム）

    @staticmethod
    def settle_retreat(state: GameState, context: resolution.Context, player: int, retreated: int) -> None:
        resolution.settle_after_retreat(state, context, player, retreated)  # v0.87: 「にげる」の反応（［おとしあな］を含む）のあと


_REACTION_HOOKS = _ReactionHooks()


def _engine(handler: Callable[[GameState, object], None]) -> Callable[[GameState, object, resolution.Context], None]:
    """範囲外のコマンドの処理（解決の設定を使わない）。"""
    return lambda state, command, context: handler(state, command)


_HANDLERS: dict[type, Callable[[GameState, object, resolution.Context], None]] = {
    PlaceStartingPokemon: _engine(_place_starting_pokemon),
    DrawMulliganCards: _engine(_draw_mulligan_cards),
    ReportJankenResult: _engine(_report_janken_result),
    PlayBasicToBench: _play_basic_to_bench,  # v0.87: ［ヒートプレート］・爆発ジムのダメージのきぜつに解決の設定を使う
    AttachEnergy: _attach_energy,  # v0.58: レインボーエネルギーの 10 ダメージのあとのきぜつに解決の設定を使う
    Retreat: _retreat,  # v0.61: 相手の［おとしあな］のあとのきぜつ・交代に解決の設定を使う
    UseAttack: resolution.handle,  # ワザ（解決の基盤。v0.16b）
    EndTurn: resolution.handle,  # 番の終わり（解決の基盤。v0.16b）
    TakePrize: _answer_decision,
    PromoteActive: _answer_decision,
    ResolveDecision: _answer_decision,
    PlayTrainer: _play_trainer,  # v0.50: 使ったあとのきぜつ・交代（退化スプレー）に解決の設定を使う
    EvolvePokemon: _evolve_pokemon,  # v0.86: 進化への反応（［れんさしんか］）の続きに解決の設定を使う
    UsePokemonPower: _use_pokemon_power,  # v0.42: 処理のあとのきぜつ・交代に解決の設定（効果の定義の対応表）を使う
    DiscardFromPlay: _discard_from_play,  # v0.47: 空いたバトル場の勝ち負け・交代に解決の設定を使う
    RemoveDisguise: _engine(_remove_disguise),  # v0.49
    UseStadium: _use_stadium,  # v0.57: 空いたバトル場の勝ち負け・交代に解決の設定を使う
    RevealFaceDown: _reveal_face_down,  # v0.67: 空いたバトル場の勝ち負け・交代に解決の設定を使う
}


# ---------------------------------------------------------------- 検査用


def _face_down_pokemon_problems(state: GameState, player: int, pokemon) -> list[str]:
    """v0.67（docs/secret-plan-preflight-v0.67.md 7 章）: うらにしてベンチに出したカード（マチスの秘策）の場のポケモンの形。うらのあいだはダメージ・効果を受けない（受ける時に
    おもてにする）ので、ダメージ・特殊状態・持続する効果・ついているトレーナー・重なり・のせたカード・使った記録はない。ついていてよいのはエネルギーカードだけ（手札から
    つけることは効果ではない）。いちばん上のカードは持ち主の手札から出したカードで、本当のカードの定義（``printed_def``）はどの種類でもよい。"""
    problems = []
    where = f"うらのカード（場のポケモン {pokemon.pokemon_id}）"
    if pokemon.damage:
        problems.append(f"{where}にダメージ {pokemon.damage} がのっている")
    if pokemon.evolution_stack or pokemon.disguise is not None or pokemon.devolved_turn is not None or pokemon.evolved_turn is not None:
        problems.append(f"{where}に進化・退化・のせたカードの記録がある")
    if pokemon.conditions != SpecialConditions() or pokemon.persistent_effects or pokemon.trainers or pokemon.retreat_failed_turn is not None:
        problems.append(f"{where}に特殊状態・持続する効果・ついているトレーナー・にげるの失敗の記録がある")
    if pokemon.attacks_used_once or pokemon.evolution_permission_turn is not None or pokemon.type_shift is not None:
        problems.append(f"{where}に使ったワザ・進化の許可・［へんしょく］の記録がある")
    return problems


def _face_down_list_problems(state: GameState) -> list[str]:
    """v0.67: ``face_down_cards`` の並びのカードは、どれも場のポケモンのいちばん上のカード（重複しない）。"""
    tops = {pokemon.card for p in state.players for pokemon in p.in_play()}
    problems = []
    if len(set(state.face_down_cards)) != len(state.face_down_cards):
        problems.append(f"うらのカードの並び {state.face_down_cards} に同じカードが 2 回ある")
    for uid in state.face_down_cards:
        if uid not in tops:
            problems.append(f"うらのカード {uid} が場のポケモンのいちばん上のカードではない")
    return problems


def check_invariants(state: GameState) -> list[str]:
    """状態の不変条件の問題を返す。問題がなければ空のリスト。

    ``new_game`` と ``apply_command`` は、返す前に必ずこれで確かめる（StateIntegrityError）。

    - カードの保存則: 対戦のすべてのカード（``state.cards``）が、持ち主のゾーンのどこか 1 か所にだけある。
      未知の番号のカードはない。``new_game`` で作った対戦では、カードの組がデッキリストと同じ。
    - 場の形: 場のポケモンはポケモンのカード、ついているのは基本エネルギー、ダメージは 10 の倍数で HP 未満（v0.10: ワザの途中の
      決定を待つ間の、相手の「はんげき」で HP 以上になったワザを使ったポケモンだけを除く。``_counter_knocked_out_attacker_awaiting``。
      v0.11: 「こんじょう」を使うかの決定を待つ間の、その対象のポケモンと、同じワザで HP 以上になったワザを使ったポケモンを除く。
      ``_ko_prevention_awaiting``。v0.12: ワザの途中の決定を待つ間の、相手の「ほのおのかべ」で HP 以上になったワザを使ったポケモンも
      ``_counter_knocked_out_attacker_awaiting`` で除く）、
      ベンチは 5 匹まで、サイドはルールの枚数まで。
    - 「ふしちょう」を使うかの決定（v0.12。再開先 ``"post_knockout"``）を待つ間は、バトル場が空のプレイヤーがいてよい（きぜつの処理のあと、
      バトル場に出す前）。決定と、その前のサイドを取る決定の候補（``context`` の ``"post_knockout"``）は
      ``_post_knockout_decision_problems``・``_post_knockout_candidate_problems`` が確かめる。
    - 段階との対応: 番の途中は両方のバトル場にポケモンがいる。サイドを取る・バトル場に出す段階には、
      それを待っているプレイヤーがいる。終わった段階には結果か止めた理由がある。
    - 特殊状態（v0.3a）: 特殊状態があるのはバトル場のポケモンだけ。どくのダメージは 10 の倍数の正の数。
    - 進化（v0.4a）: 重なっているカードも場のカードとして数える（カードの保存則）。重なりの形・場に出た番・進化した番
      （``_evolution_problems``）。
    - ワザによる持続する効果（v0.4b）: 型・発生源・番・期限・置き場所（バトル場だけ）・重複・ログとの対応
      （``_persistent_effect_problems``）。持続する効果はカードではないので、カードの保存則には数えない。
    - 番の進行（v0.3a）: 番と番のあいだに、番の終わりとポケモンチェックがちょうど 1 回ずつ、この順にある。
      ポケモンチェックの途中の決定（続きが次の番）なら、今の番のあとに 1 回ずつ。番の途中なら、まだない。
    - ポケモンパワーで手札からつけたエネルギーの数（v0.6）: 今の番のログの ``power_attach_energy`` の数と同じ
      （``_power_attachment_problems``）。
    """
    problems: list[str] = []
    rules = state.rules
    seen: dict[int, str] = {}
    evolve_events = None  # 進化のログ（v0.4c。進化しているポケモンがいれば読む）
    if any(event["kind"] == "devolve" for event in state.log):
        # v0.50: 退化のログがあれば最初から読む（退化してたねポケモンにもどり、退化した番の記録が消されたポケモンも、ログと照らす）
        evolve_events = _evolve_events_by_pokemon(state)

    for uid, card in state.cards.items():
        if card.uid != uid or card.owner not in PLAYERS:
            problems.append(f"カードの表の {uid} 番が {card} になっている")

    def place(uid: int, player: int, zone: str) -> None:
        where = f"プレイヤー {player} の {zone}"
        if uid not in state.cards:
            problems.append(f"未知のカード {uid!r} が {where} にある")
            return
        if uid in seen:
            problems.append(f"カード {uid} が {seen[uid]} と {where} の 2 か所にある")
        seen[uid] = where
        if state.cards[uid].owner != player:
            problems.append(f"カード {uid} が持ち主でない {where} にある")

    for player, p in enumerate(state.players):
        for zone in ("deck", "hand", "prizes", "discard"):
            for uid in getattr(p, zone):
                place(uid, player, zone)
        for pokemon in p.in_play():
            place(pokemon.card, player, "場")
            stack = pokemon.evolution_stack
            for uid in stack if isinstance(stack, tuple) else ():
                place(uid, player, "場（進化しているポケモンの下のカード）")  # v0.4a
            if pokemon.disguise is not None:
                place(pokemon.disguise, player, "場（「ばける」でのせたカード）")  # v0.49
            for uid in pokemon.energy:
                place(uid, player, "場（ついているエネルギー）")
                if uid in state.cards and not state.card_def(uid).is_basic_energy and state.effects.energy_effect(state.card_def(uid)) is None \
                        and state.energy_role(uid) is None:
                    # v0.58: 登録された特殊エネルギーカードはつけられる。v0.59: ［エネエネ］でエネルギーとしてついているカード（``EnergyRole``）も
                    problems.append(f"エネルギーカードでない（登録のない特殊エネルギーの）カード {uid} がポケモンについている")
            problems.extend(_attached_trainer_problems(state, player, pokemon, place))
            if pokemon.card not in state.cards:
                continue
            definition = state.card_def(pokemon.card)
            if definition.category != "pokemon":
                problems.append(f"ポケモンでないカード {pokemon.card} が場にポケモンとしてある")
                continue
            if state.is_face_down(pokemon):
                problems.extend(_face_down_pokemon_problems(state, player, pokemon))  # v0.67: うらのカード（名前・HP などは読めない）
                continue
            if pokemon.damage < 0 or pokemon.damage % 10:
                problems.append(f"ポケモン {pokemon.card} のダメージ {pokemon.damage} が 10 の倍数でない")
            if knocked_by_hp(state, pokemon) and not (  # v0.48: 今有効な最大HP
                _counter_knocked_out_attacker_awaiting(state, player, pokemon) or _ko_prevention_awaiting(state, player, pokemon)
                or _attack_damage_awaiting(state, player, pokemon)
            ):
                problems.append(f"ポケモン {pokemon.card} が HP 以上のダメージで場に残っている")
            if (pokemon.evolution_stack or pokemon.devolved_turn is not None) and evolve_events is None:
                # 進化しているポケモン（v0.50 から、退化したことのあるポケモンも）がいるときだけ、ログを 1 回読む（v0.4c）
                evolve_events = _evolve_events_by_pokemon(state)
            problems.extend(_evolution_problems(state, player, pokemon, evolve_events))
            problems.extend(_condition_problems(state, player, p, pokemon))
            problems.extend(_persistent_effect_problems(state, player, p, pokemon))
            problems.extend(_once_attack_problems(state, player, pokemon))  # v0.44
            problems.extend(_evolution_permission_problems(state, player, pokemon))  # v0.44
            problems.extend(_type_shift_problems(state, player, pokemon))  # v0.48
            problems.extend(_disguise_problems(state, player, pokemon))  # v0.49
            problems.extend(_marker_problems(state, pokemon))  # v0.90
        limit = _bench_limit_or_default(state, player)
        if len(p.bench) > limit and not _narrow_cleanup_pending(state, player):
            # v0.57: ベンチの上限は場のスタジアム（せまいジム）を当てはめた数。場に出た時の、手札にもどすポケモンを選ぶ決定を待つ間だけ、そのプレイヤーは多くてよい
            problems.append(f"プレイヤー {player} のベンチが {len(p.bench)} 匹（{limit} 匹まで）")
        if len(p.prizes) > rules.prize_count:
            problems.append(f"プレイヤー {player} のサイドが {len(p.prizes)} 枚（{rules.prize_count} 枚まで）")
        if p.mulligan_draws_remaining < 0:
            problems.append(f"プレイヤー {player} の切り直しの補償の残りが負")
    if state.face_down_cards:
        problems.extend(_face_down_list_problems(state))  # v0.67
    # v0.57: 場のスタジアムカード（両方の場に出ているカードとして扱うが、実際のカードは 1 枚。持ち主のゾーンとして 1 回だけ数える）
    if state.stadium is not None:
        stadium = state.stadium
        if getattr(stadium, "owner", None) not in PLAYERS:
            problems.append(f"場のスタジアム {stadium!r} の持ち主が正しくない")
        else:
            place(stadium.card, stadium.owner, "場（スタジアム）")
    # 使っている最中のトレーナーカード（v0.2b）も、持ち主のゾーンの 1 つとして数える
    used = state.trainer_in_use
    if used is not None:
        if used.player not in PLAYERS:
            problems.append(f"使用中のトレーナーの持ち主 {used.player!r} が正しくない")
        else:
            place(used.card, used.player, "使用中のトレーナー")
            if used.card in state.cards and state.card_def(used.card).category != "trainer":
                problems.append(f"トレーナーカードでないカード {used.card} が使用中のトレーナーになっている")
    # v0.58: 内側のトレーナーを使い終わるのを待っている外側のトレーナー（ナツメのサイキックコントロール）も、持ち主のゾーンの 1 つとして数える
    for outer in state.trainer_stack:
        if outer.player not in PLAYERS:
            problems.append(f"外側のトレーナーの持ち主 {outer.player!r} が正しくない")
        else:
            place(outer.card, outer.player, "使用中のトレーナー（外側）")
    # v0.63: 一時的に置いておくカード（くすぐりマシーン・たたきつけろ!挑戦状・カツラのクイズ その3）も、持ち主のゾーンの 1 つとして数える（手札・山札・ベンチとは別の場所）
    for group in state.set_aside:
        if getattr(group, "owner", None) not in PLAYERS:
            problems.append(f"置いておくカード {group!r} の持ち主が正しくない")
            continue
        for uid in group.cards:
            place(uid, group.owner, f"置いておくカード（{group.kind}）")
    missing = set(state.cards) - set(seen)
    if missing:
        problems.append(f"どこにもないカード {sorted(missing)}")

    # 場のポケモンの番号: 付いていて、重ならず、まだ配っていない番号ではない
    pokemon_ids = [pokemon.pokemon_id for p in state.players for pokemon in p.in_play()]
    for pokemon_id in pokemon_ids:
        if type(pokemon_id) is not int or not 1 <= pokemon_id < state.next_pokemon_id:
            problems.append(f"場のポケモンの番号 {pokemon_id!r} が正しくない（次に付ける番号 {state.next_pokemon_id}）")
    if len(set(pokemon_ids)) != len(pokemon_ids):
        problems.append(f"場のポケモンの番号が重なっている {sorted(pokemon_ids)}")

    # new_game で作った対戦は、カードの組が対戦開始時のデッキリストと同じ
    if any(state.decklists):
        for owner in PLAYERS:
            ids = sorted(c.card_id for c in state.cards.values() if c.owner == owner)
            if ids != sorted(state.decklists[owner]):
                problems.append(f"プレイヤー {owner} のカードの組が対戦開始時のデッキと違う")

    phase = state.phase
    if not isinstance(phase, Phase):
        problems.append(f"段階 {phase!r} が Phase ではない")
        return problems
    problems.extend(_progress_problems(state))
    problems.extend(_power_attachment_problems(state))
    problems.extend(_turn_power_problems(state))  # v0.31
    problems.extend(_trainer_lock_problems(state))  # v0.47
    problems.extend(_trainer_effect_problems(state))  # v0.56
    problems.extend(_energy_role_problems(state))  # v0.59
    problems.extend(_color_effect_problems(state))  # v0.88
    problems.extend(_history_problems(state))  # v0.62
    problems.extend(_set_aside_problems(state))  # v0.63
    problems.extend(_face_up_prize_problems(state))  # v0.63
    problems.extend(_stadium_problems(state))  # v0.57
    problems.extend(_recall_problems(state))  # v0.49
    if phase in TERMINAL_PHASES:
        if state.decision is not None:
            problems.append("対戦が終わっているのに、決定が残っている")
        if state.trainer_in_use is not None or state.trainer_stack:
            problems.append("対戦が終わっているのに、使用中のトレーナーが残っている")
        if any(group.kind != SET_ASIDE_HAND for group in state.set_aside):
            problems.append("対戦が終わっているのに、トレーナーの効果の途中に置いたカード（挑戦状・クイズ）が残っている")
        if phase is Phase.HALTED and state.halt is None:
            problems.append("止めた理由がないまま HALTED になっている")
        if phase is not Phase.HALTED and state.result is None:
            problems.append("結果がないまま対戦が終わっている")
        return problems
    if state.result is not None or state.halt is not None:
        problems.append(f"結果か止めた理由があるのに {phase.value} になっている")
    if not 1 <= state.next_decision_id:
        problems.append(f"次の決定の番号 {state.next_decision_id!r} が正しくない")

    # v0.12: 「ふしちょう」を使うかの決定（きぜつの処理のあと、バトル場に出す前。再開先 "post_knockout"）を待つ間も、バトル場が空のことがある
    after_knockout = phase is Phase.DECISION and state.decision is not None and state.decision.resume == "post_knockout"
    # v0.38: ワザを使ったポケモンがワザの効果で場をはなれたあとのワザの途中の決定（キョウのポッポの「でんれい」）を待つ間も、そのプレイヤーのバトル場が
    # 空のことがある（かわりの対戦ポケモンを出す決定・控えがいないときの山札をさがす決定。``_returned_attacker``）
    left_play = phase is Phase.DECISION and state.decision is not None and _returned_attacker(state, state.decision) is not None
    for player, p in enumerate(state.players):
        if left_play and player == state.current_player:
            continue
        if p.placed_starting_pokemon and p.active is None and phase not in (Phase.TAKE_PRIZE, Phase.PROMOTE_ACTIVE) and not after_knockout:
            problems.append(f"プレイヤー {player} のバトル場にポケモンがいないまま {phase.value} になっている")
    if phase is Phase.MAIN:
        if state.current_player not in PLAYERS:
            problems.append(f"番のプレイヤー {state.current_player!r} が正しくない")
        if not 0 <= state.energy_attachments_this_turn <= rules.energy_attachments_per_turn + _blaine_double_attached(state):
            problems.append(f"この番にエネルギーをつけた回数 {state.energy_attachments_this_turn} が正しくない")
    if state.first_player is not None and phase not in SETUP_PHASES:
        # 番は先攻から 1 番ずつ交互に進む（p.309）。有効期限（「次の相手の番の終わり」= 今の番 + 1）の前提（v0.2e）
        if state.first_player not in PLAYERS or not isinstance(state.turn_number, int) or state.turn_number < 1:
            problems.append(f"先攻 {state.first_player!r}・番 {state.turn_number!r} が正しくない")
        elif state.current_player != turn_owner(state, state.turn_number):
            problems.append(f"{state.turn_number} 番はプレイヤー {turn_owner(state, state.turn_number)} の番なのに、番のプレイヤーが {state.current_player!r}")
    problems.extend(_decision_problems(state))
    problems.extend(_trainer_problems(state))
    if phase is Phase.SETUP_MULLIGAN_DRAW and not any(p.mulligan_draws_remaining for p in state.players):
        problems.append("切り直しの補償を引く段階なのに、引く権利のあるプレイヤーがいない")
    return problems


def _evolution_problems(state: GameState, player: int, pokemon: PokemonInPlay, evolve_events: dict | None = None) -> list[str]:
    """場のポケモンのカードの重なりと、場に出た番・進化した番（v0.4a。v0.4c で 2 進化まで。p.309・p.310・p.316・p.319・p.324）。

    - 重なり（``evolution_stack``）: 整数のタプルで、0〜2 枚（重なったカードは全部で 3 枚まで。p.319 の「1枚のたね
      ポケモンカードと、1または2枚の進化カードの合計2枚または3枚」。ベイビィ（C・D）は未対応）。重なりの長さで、
      下から順の段階が決まる: たね → 1 進化 → 2 進化。いちばん下はたねポケモン、そこから上の各カードは決まった段階で、
      その「○○○○から進化」の名前がすぐ下のカードの名前（すべての隣り合う 2 枚を確かめる。書かれていない組み合わせで
      重ねない。p.324）
    - 場に出た番（``played_turn``）: 0（対戦準備）〜今の番
    - 進化した番（``evolved_turn``。いまの姿に進化した番）: 進化していなければ None。進化していれば、場に出た番より後・
      今の番まで・持ち主の番・おたがいの最初の番（1・2 番）ではない（p.310）
    - 2 進化しているポケモン（v0.4c）: 1 進化した番は状態に持たない（``evolved_turn`` は 2 進化した番）。1 進化は
      場に出た番より後・2 進化した番より前（同じ番に二度は進化できない。p.310）の、3 番以降の持ち主の番なので、その
      ような番があることを確かめる（状態だけで確かめられる必要条件）
    - ログとの対応（v0.4c）: このポケモンの進化のログ ``evolve``（``evolve_events``。同じ ``pokemon_id``。番号は使い回さない
      ので、ほかのポケモンのログは混ざらない）は、重なりのいちばん上の側の移り変わり（下のカード → 上のカード）と
      順番どおりに対応し、番は場に出た番より後で、同じ番に二度進化しておらず（番が増えていく）、最後のログの番が
      ``evolved_turn``。``new_game`` から始めた対戦（ログが対戦の最初からある）では、すべての移り変わりにログがある。
      テスト専用に盤面を作った状態（``build_test_state``）は、作った重なりのログがないので、あるログだけを確かめる
    - 今の番に進化したポケモンに、進化のあとで付けられていない特殊状態が残っていない（進化で消える。p.310・p.322）
    """
    where = f"ポケモン {pokemon.pokemon_id}"
    stack = pokemon.evolution_stack
    if not isinstance(stack, tuple) or any(type(uid) is not int for uid in stack):
        return [f"{where} の重なっているカード {stack!r} が整数のタプルではない"]
    played, evolved = pokemon.played_turn, pokemon.evolved_turn
    if type(played) is not int or not 0 <= played <= state.turn_number:
        return [f"{where} の場に出た番 {played!r} が正しくない（0〜今の番 {state.turn_number}）"]
    if evolved is not None and type(evolved) is not int:
        return [f"{where} の進化した番 {evolved!r} が整数ではない"]
    if any(uid not in state.cards for uid in stack) or pokemon.card not in state.cards:
        return []  # 未知のカードはカードの保存則のほうで数える
    top = state.card_def(pokemon.card)
    problems = _devolution_state_problems(state, player, pokemon, evolve_events)  # v0.50
    if not stack:
        if not top.is_basic_pokemon:
            problems.append(f"{where} は進化していないのに、いちばん上のカード {pokemon.card}（{top.name_ja}）がたねポケモンではない")
        if evolved is not None:
            problems.append(f"{where} は進化していないのに、進化した番 {evolved} がある")
        if evolve_events is not None and evolve_events.get(pokemon.pokemon_id):
            # v0.50: 退化してたねポケモンにもどったポケモンも、進化・退化のログをさかのぼって確かめる
            problems.extend(_stack_history_problems(state, player, pokemon, (pokemon.card,), evolve_events[pokemon.pokemon_id]))
        return problems
    if len(stack) > len(EVOLUTION_STAGES) - 1:
        problems.append(f"{where} に {len(stack) + 1} 枚のカードが重なっている（2 進化までの 3 枚まで。p.319）")
    chain = (*stack, pokemon.card)
    events = () if evolve_events is None else evolve_events.get(pokemon.pokemon_id, ())
    for position, uid in enumerate(chain):
        definition = state.card_def(uid)
        if definition.category != "pokemon" or definition.stage not in EVOLUTION_STAGES:
            problems.append(
                f"{where} の重なりが正しくない（{len(chain)} 枚のカードの下から {position + 1} 枚目 {uid}（{definition.name_ja}）が"
                f" 進化の段階のポケモンのカードではない）"
            )
            continue
        if position == 0:
            if not definition.is_basic_pokemon:
                problems.append(f"{where} のいちばん下のカード {uid} がたねポケモンではない")
            continue
        below = state.card_def(chain[position - 1])
        if below.category != "pokemon" or below.stage not in EVOLUTION_STAGES:
            continue
        step = EVOLUTION_STAGES.index(definition.stage) - EVOLUTION_STAGES.index(below.stage)
        if step == 1:
            if definition.evolves_from != below.name_ja:
                problems.append(
                    f"{where} のカードの重なりが正しくない（{below.name_ja} の上に {definition.name_ja}。{definition.name_ja} は"
                    f" {definition.evolves_from!r} から進化）"
                )
        elif step == 2 and below.is_basic_pokemon:
            # v0.25: 1 進化を飛ばした重なり（たねポケモン + 2 進化。トレーナーの効果。docs/pokemon-breeder-v0.25.md）。系統は、2 進化カードの進化元の
            # 1 進化カード（写しのカードのデータ）の進化元の名前で確かめ、その移り変わりの進化のログ（evolve の trainer_card）を要る
            # （通常の操作ではできない重ね方なので、ログのない重なりは認めない。テストの盤面（build_test_state）でも同じ）
            if skipped_stage1_basic(definition) != below.name_ja:
                problems.append(
                    f"{where} の重なりが正しくない（たねポケモン {below.name_ja} の上に 2 進化の {definition.name_ja}。"
                    f"{definition.name_ja} の進化元の 1 進化（{definition.evolves_from!r}）の進化元は {list(definition.stage1_evolves_from)}）"
                )
            elif not any(e["kind"] == "evolve" and (e.get("from_card"), e.get("to_card")) == (chain[position - 1], uid) and "trainer_card" in e
                         for e in events):
                problems.append(
                    f"{where} の重なりが正しくない（たねポケモン {below.name_ja} の上に 2 進化の {definition.name_ja}。1 進化を飛ばして"
                    "重ねるトレーナーの進化のログ（evolve の trainer_card）がない）"
                )
        else:
            problems.append(
                f"{where} の重なりが正しくない（{len(chain)} 枚のカードの下から {position + 1} 枚目 {uid}（{definition.name_ja}）が"
                f" {definition.stage!r} で、すぐ下の {below.name_ja}（{below.stage}）の次の段階ではない）"
            )
    if evolved is None:
        problems.append(f"{where} は進化しているのに、進化した番がない")
        return problems
    # v0.44: トレーナー「サカキ」の許可（その番のログ ``evolution_permission``）のあるポケモンは、場に出た番・進化した番にも進化できる
    permitted = played == evolved and _evolution_permitted(state, pokemon.pokemon_id, evolved)
    if not (played < evolved or permitted) or evolved > state.turn_number:
        problems.append(f"{where} の進化した番 {evolved} が、場に出た番 {played} より後・今の番 {state.turn_number} までではない")
    elif evolved <= 2:
        problems.append(f"{where} がおたがいの最初の番（{evolved} 番）に進化している（p.310）")
    elif state.first_player in PLAYERS and turn_owner(state, evolved) != player and not _evolved_by_opponent_attack(state, pokemon, evolved):
        problems.append(f"{where} が持ち主の番でない {evolved} 番に進化している")
    elif len(stack) >= 2 and state.first_player in PLAYERS:
        # 2 進化（v0.4c）: 1 進化した番は、場に出た番・2 番より後で、2 進化した番より前の持ち主の番（同じ番には進化できない）
        if not any(turn_owner(state, turn) == player for turn in range(max(played, 2) + 1, evolved)) and not _evolution_permitted(
                state, pokemon.pokemon_id, evolved):
            problems.append(
                f"{where} は {evolved} 番に 2 進化しているが、場に出た番 {played} のあと {evolved} 番より前に、1 進化できる持ち主の番がない"
                "（同じ番に二度は進化できない。p.310）"
            )
    if evolve_events is not None:
        problems.extend(_evolution_log_problems(state, player, pokemon, chain, evolve_events.get(pokemon.pokemon_id, ())))
    if evolved == state.turn_number and pokemon.conditions.names() and pokemon.devolved_turn != state.turn_number:
        applied_after = False
        for event in _events_since_turn_start(state):
            if event.get("pokemon_id") != pokemon.pokemon_id:
                continue
            if event["kind"] == "evolve":
                break
            if event["kind"] == "special_condition":
                applied_after = True
        if not applied_after:
            problems.append(f"{where} は今の番に進化したのに、進化の前の特殊状態 {pokemon.conditions.names()} が残っている（p.310・p.322）")
    return problems


def _evolved_by_opponent_attack(state: GameState, pokemon, turn: int) -> bool:
    """v0.84: 場のポケモンが ``turn`` 番（持ち主の番でない番）に、相手のワザの効果で進化したか（「しんかのうた」）。いちばん上のカードを重ねた進化のログ
    ``evolve`` に、その番の ``effect`` があり、そのワザの登録された実装が ``evolves_opponent_pokemon`` のときだけ真（広げない）。"""
    for event in state.log:
        if (event["kind"] != "evolve" or event.get("pokemon_id") != pokemon.pokemon_id or event.get("turn") != turn
                or event.get("to_card") != pokemon.card):
            continue
        card_id, _, index = str(event.get("effect", "")).partition("#")
        entry = state.effects.attack_entry(card_id, int(index)) if index.isdigit() else None
        if entry is not None and getattr(entry.effect, "evolves_opponent_pokemon", False):
            return True
    return False


def _evolution_permitted(state: GameState, pokemon_id: int, turn: int, before=None) -> bool:
    """v0.44: 場のポケモン ``pokemon_id`` が、``turn`` 番にトレーナー「サカキ」の許可（ログ ``evolution_permission``）を受けていたか。``before`` が進化のログの
    イベントなら、そのイベントより前の許可だけを数える（許可のあとの進化だけが、場に出た番・進化した番の制限を外れる）。番の終わりに消える許可を、終わった番の
    進化について確かめるためにログを読む（エンジンは許可を状態の ``evolution_permission_turn`` で決め、ログから決めない）。"""
    for event in state.log:
        if before is not None and event is before:
            return False
        if event["kind"] == "evolution_permission" and event.get("pokemon_id") == pokemon_id and event.get("turn") == turn:
            return True
    return False


def _evolve_events_by_pokemon(state: GameState) -> dict[int, list]:
    """ログの進化のイベント ``evolve``（v0.50 から退化のイベント ``devolve`` も）を、場のポケモンの番号ごとに古い順に集める（v0.4c。不変条件で 1 回だけ読む）。"""
    events: dict[int, list] = {}
    for event in state.log:
        if event["kind"] in ("evolve", "devolve"):
            events.setdefault(event.get("pokemon_id"), []).append(event)
    return events


def _devolution_state_problems(state: GameState, player: int, pokemon: PokemonInPlay, events_by_pokemon: dict | None) -> list[str]:
    """v0.50: 退化した番（``PokemonInPlay.devolved_turn``）の整合。

    - なければ None。あれば整数で、場に出た番〜今の番（退化は、場に出たあとのワザ・トレーナーの効果。相手の番のミュウの「たいかビーム」でも退化する）
    - ログがあれば（``events_by_pokemon``）、このポケモンの番号の最後の退化のログ ``devolve`` の番と同じ。``new_game`` から始めた対戦では、退化した番があれば退化のログがある
    - 今の番に退化したポケモンに、退化のあとで付けられていない特殊状態が残っていない（退化で消える。p.324「19」）"""
    devolved = pokemon.devolved_turn
    where = f"ポケモン {pokemon.pokemon_id}"
    if devolved is None:
        if events_by_pokemon is not None and any(e["kind"] == "devolve" for e in events_by_pokemon.get(pokemon.pokemon_id, ())):
            return [f"{where} に退化のログがあるのに、退化した番がない"]
        return []
    if type(devolved) is not int or not pokemon.played_turn <= devolved <= state.turn_number:
        return [f"{where} の退化した番 {devolved!r} が、場に出た番 {pokemon.played_turn}〜今の番 {state.turn_number} ではない"]
    problems = []
    if events_by_pokemon is not None:
        devolves = [e for e in events_by_pokemon.get(pokemon.pokemon_id, ()) if e["kind"] == "devolve"]
        if devolves and devolves[-1]["turn"] != devolved:
            problems.append(f"{where} の最後の退化のログは {devolves[-1]['turn']} 番なのに、退化した番が {devolved}")
        elif not devolves and any(state.decklists):
            problems.append(f"{where} に退化した番 {devolved} があるのに、退化のログがない")
    if devolved == state.turn_number and pokemon.conditions.names():
        applied_after = False
        for event in _events_since_turn_start(state):
            if event.get("pokemon_id") != pokemon.pokemon_id:
                continue
            if event["kind"] in ("devolve", "evolve"):
                break
            if event["kind"] == "special_condition":
                applied_after = True
        if not applied_after:
            problems.append(f"{where} は今の番に退化したのに、退化の前の特殊状態 {pokemon.conditions.names()} が残っている（p.324）")
    return problems


def _evolution_log_problems(state: GameState, player: int, pokemon: PokemonInPlay, chain: tuple, events) -> list[str]:
    """進化しているポケモンの重なりと、そのポケモンの進化のログ ``evolve`` の対応（v0.4c。``_evolution_problems`` の説明）。v0.50: 退化のログ ``devolve`` があれば、
    進化と退化の履歴をさかのぼって重なりを組み立て直す（``_stack_history_problems``）。"""
    if any(e["kind"] == "devolve" for e in events):
        return _stack_history_problems(state, player, pokemon, chain, events)
    where = f"ポケモン {pokemon.pokemon_id}"
    transitions = len(chain) - 1
    if len(events) > transitions:
        return [f"{where} の進化のログが {len(events)} 回あるのに、重なりは {transitions} 回ぶん（{len(chain)} 枚）"]
    if any(state.decklists) and len(events) != transitions:
        # new_game から始めた対戦は、ログが対戦の最初からあるので、すべての進化にログがある
        return [f"{where} は {transitions} 回進化した重なり（{len(chain)} 枚）なのに、進化のログが {len(events)} 回"]
    problems = []
    previous_turn = pokemon.played_turn
    for offset, event in enumerate(events):
        index = len(chain) - len(events) + offset  # この進化でいちばん上になったカードの位置
        expected = (chain[index - 1], chain[index])
        if (event.get("from_card"), event.get("to_card")) != expected or event.get("player") != player:
            problems.append(
                f"{where} の進化のログ（{event.get('from_card')!r} → {event.get('to_card')!r}、プレイヤー {event.get('player')!r}）が、"
                f"重なり（{expected[0]} → {expected[1]}、プレイヤー {player}）と対応しない"
            )
        problems.extend(_skip_evolution_log_problems(state, player, where, event, expected))
        if event["turn"] < previous_turn or (event["turn"] == previous_turn and not _evolution_permitted(state, pokemon.pokemon_id, event["turn"], event)):
            problems.append(
                f"{where} が {event['turn']} 番に進化しているが、場に出た番・前の進化の番（{previous_turn} 番）より後ではない"
                "（同じ番に二度は進化できない。p.310）"
            )
        previous_turn = event["turn"]
    if events and events[-1]["turn"] != pokemon.evolved_turn:
        problems.append(f"{where} の最後の進化のログは {events[-1]['turn']} 番なのに、進化した番が {pokemon.evolved_turn}")
    return problems


def _stack_history_problems(state: GameState, player: int, pokemon: PokemonInPlay, chain: tuple, events) -> list[str]:
    """v0.50: 退化したことのあるポケモンの重なり（``chain``。下から順）と、そのポケモンの進化・退化のログ（``events``。古い順）の対応。

    - 今の重なりから、ログを新しい順にさかのぼる: 進化 ``evolve`` は、そのときいちばん上になったカード（``to_card``）が今いちばん上で、その下が進化前のカード（``from_card``）。
      退化 ``devolve`` は、はがしたあとのいちばん上（``to_card``）が今いちばん上で、はがしたカード（``removed``。上から順。最初が ``from_card``）を上に積みもどす。
      どちらも持ち主（``player``）が同じ。過去のログを消したり、確かめを弱めたりして通さない
    - ``new_game`` から始めた対戦では、さかのぼり終えた重なりは、場に出たたねポケモン 1 枚（すべての移り変わりにログがある）
    - 番: 進化の番は前の進化・退化・場に出た番より後（同じ番の 2 回目の進化はトレーナー「サカキ」の許可のときだけ。退化した番の進化はエンジンが止める（DV2）ので
      ない）。退化の番は前の移り変わりの番以降。最後の進化のログの番は、重なりがあれば進化した番（``evolved_turn``）
    - 1 進化を飛ばした進化のログ（``trainer_card``）は v0.25 と同じ確かめ（``_skip_evolution_log_problems``）"""
    where = f"ポケモン {pokemon.pokemon_id}"
    current = list(chain)
    problems: list[str] = []
    for event in reversed(events):
        if event.get("player") != player:
            return [f"{where} の{'進化' if event['kind'] == 'evolve' else '退化'}のログのプレイヤー {event.get('player')!r} が持ち主 {player} ではない"]
        if event["kind"] == "evolve":
            if len(current) < 2 or (event.get("from_card"), event.get("to_card")) != (current[-2], current[-1]):
                return [f"{where} の進化のログ（{event.get('from_card')!r} → {event.get('to_card')!r}）が、さかのぼった重なり {tuple(current)} と対応しない"]
            problems.extend(_skip_evolution_log_problems(state, player, where, event, (current[-2], current[-1])))
            current.pop()
        else:
            removed = tuple(event.get("removed") or ())
            if not removed or event.get("from_card") != removed[0] or event.get("to_card") != current[-1]:
                return [f"{where} の退化のログ（{event.get('from_card')!r} → {event.get('to_card')!r}、はがしたカード {removed!r}）が、さかのぼった重なり "
                        f"{tuple(current)} と対応しない"]
            current.extend(reversed(removed))
    if any(state.decklists) and len(current) != 1:
        problems.append(f"{where} の進化・退化のログをさかのぼった重なり {tuple(current)} が、場に出たたねポケモン 1 枚ではない")
    previous_turn, previous_kind = pokemon.played_turn, None
    for event in events:
        turn = event["turn"]
        if event["kind"] == "evolve":
            ok = turn > previous_turn or (turn == previous_turn and previous_kind != "devolve"
                                          and _evolution_permitted(state, pokemon.pokemon_id, turn, event))
            if not ok:
                problems.append(f"{where} が {turn} 番に進化しているが、前の移り変わり・場に出た番（{previous_turn} 番）より後ではない（p.310。退化した番の進化は DV2）")
        elif turn < previous_turn:
            problems.append(f"{where} が {turn} 番に退化しているが、前の移り変わり・場に出た番（{previous_turn} 番）より前")
        previous_turn, previous_kind = turn, event["kind"]
    evolves = [e for e in events if e["kind"] == "evolve"]
    if len(chain) > 1 and evolves and evolves[-1]["turn"] != pokemon.evolved_turn:
        problems.append(f"{where} の最後の進化のログは {evolves[-1]['turn']} 番なのに、進化した番が {pokemon.evolved_turn}")
    return problems


def _skip_evolution_log_problems(state: GameState, player: int, where: str, event, transition: tuple[int, int]) -> list[str]:
    """進化のログ ``evolve`` の ``trainer_card``（v0.25）: たねポケモンの上に 2 進化カードを重ねた（1 進化を飛ばした）移り変わりだけに
    あり、そのときの番に持ち主が使った、1 進化を飛ばして進化させるトレーナー（``TrainerEffect.skips_stage1_evolution``。
    docs/pokemon-breeder-v0.25.md）のカードの uid。通常の操作（``EvolvePokemon``）の移り変わりにはない。"""
    lower, upper = (state.card_def(uid) if uid in state.cards else None for uid in transition)
    skip = lower is not None and upper is not None and lower.is_basic_pokemon and upper.is_stage2_pokemon
    trainer = event.get("trainer_card")
    if not skip:
        if "trainer_card" in event:
            return [f"{where} の進化のログ（{transition[0]} → {transition[1]}）に trainer_card {trainer!r} があるが、1 進化を飛ばした進化ではない"]
        return []
    if type(trainer) is not int or trainer not in state.cards or state.cards[trainer].owner != player:
        return [f"{where} の 1 進化を飛ばした進化のログの trainer_card {trainer!r} が、持ち主 {player} のカードではない"]
    entry = state.effects.trainer_entry(state.cards[trainer].card_id)
    if entry is None or not entry.effect.skips_stage1_evolution:
        return [f"{where} の 1 進化を飛ばした進化のログの trainer_card {trainer}（{state.cards[trainer].card_id}）が、1 進化を飛ばして進化させるトレーナーではない"]
    return []


def _condition_problems(state: GameState, player: int, p: PlayerState, pokemon: PokemonInPlay) -> list[str]:
    """場のポケモンの特殊状態（v0.3a・v0.3b）。特殊状態になるのはバトル場のポケモンだけで、ベンチに戻ったら消える（p.311・p.322）。

    - どく（``poison``）: ``Poison`` で、ダメージは 10 の倍数の正の数
    - ねむり・マヒ・こんらん（``exclusive``。v0.3b・v0.3c）: ``Asleep``・``Paralyzed``・``Confused`` の 1 つだけ
      （重複しない。p.322）
    - マヒ状態になった番は 1 以上・今の番まで。回復する番（``conditions.paralysis_recovery_turn``）が今の番より前なら、
      そのポケモンチェックで回復していないので違反（期限の過ぎたマヒが残らない。p.323 の 4）
    - こんらん状態で「にげる」に失敗した記録（``retreat_failed_turn``。v0.3c）: なければ None。あれば今の番の番号で、
      持ち主が番のプレイヤー（「今の自分の番では」。p.311）。番の終わりに消すので、対戦準備の段階・ほかの番・
      番の終わりのあと（ポケモンチェックの途中の決定）には残らない
    """
    conditions = pokemon.conditions
    if not isinstance(conditions, SpecialConditions):
        return [f"ポケモン {pokemon.pokemon_id} の特殊状態 {conditions!r} が SpecialConditions ではない"]
    problems = []
    poison = conditions.poison
    if poison is not None and (not isinstance(poison, Poison) or type(poison.damage) is not int or poison.damage <= 0 or poison.damage % 10):
        problems.append(f"ポケモン {pokemon.pokemon_id} のどく状態 {poison!r} が正しくない（ダメージは 10 の倍数の正の数）")
    problems.extend(_retreat_failure_problems(state, player, pokemon))
    exclusive = conditions.exclusive
    if exclusive is not None and type(exclusive) not in (Asleep, Paralyzed, Confused):
        return problems + [f"ポケモン {pokemon.pokemon_id} のねむり・マヒ・こんらんの項目 {exclusive!r} が Asleep・Paralyzed・Confused ではない"]
    if isinstance(exclusive, Paralyzed):
        turn = exclusive.turn
        if type(turn) is not int or not 1 <= turn <= state.turn_number:
            problems.append(f"ポケモン {pokemon.pokemon_id} がマヒ状態になった番 {turn!r} が正しくない（1〜今の番 {state.turn_number}）")
        elif state.first_player in PLAYERS and paralysis_recovery_turn(state, player, turn) < state.turn_number:
            problems.append(
                f"ポケモン {pokemon.pokemon_id} のマヒ状態（{turn} 番から）は {paralysis_recovery_turn(state, player, turn)} 番の終わりの"
                f"ポケモンチェックで回復しているはずなのに、{state.turn_number} 番に残っている（p.323）"
            )
    if conditions.names() and pokemon is not p.active:
        problems.append(f"プレイヤー {player} のベンチのポケモン {pokemon.pokemon_id} が特殊状態 {conditions.names()} になっている（p.322）")
    return problems


def _persistent_effect_problems(state: GameState, player: int, p: PlayerState, pokemon: PokemonInPlay) -> list[str]:
    """場のポケモンが受けているワザによる持続する効果（``PokemonInPlay.persistent_effects``。v0.4b。p.322・p.323）。

    - ``PERSISTENT_EFFECT_TYPES``（v0.4b は ``PreventDamage`` だけ）の値のタプルで、番の項目は整数
    - 置き場所: バトル場のポケモンだけ（ベンチに戻ったら消える。p.311・p.322。v0.4b の効果は、のせるタイプの
      カウンター・マーカーではない）。対戦準備の段階にはない
    - ``PreventDamage``（「かたまる」）は自分自身に与える効果なので、発生源はこのポケモンのいまのカード・持ち主
      （進化したら消えるので、いちばん上のカードが変わったあとに残らない。p.310・p.323）
    - 番: 効果を与えた番（``created_turn``）は持ち主の番で、いまの姿になった番以後・今の番まで。はたらく番（``active_turn``）
      は次の相手の番（``created_turn + 1``。v0.27 の ``NextTurnAttackDamage`` は次の自分の番 ``created_turn + 2``。型の
      ``turns_until_active``）。期限が過ぎていない（今の番がはたらく番より後なら、その番の終わりに
      消しているはず。はたらく番の終わり（ログ ``turn_end``）のあとにも残らない）
    - 重複: 同じ種類の効果は 1 つまで（v0.4b の対応カードでは、前の効果が消えるまで次の「かたまる」を使えない）。v0.27 の
      ``NextTurnAttackDamage`` だけは、はたらく番の違う 2 つまで（はたらく番に「つるぎのまい」をもう一度使うと、その番の終わりまで、
      今の番にはたらく効果と次の自分の番にはたらく効果がある）。同じ種類・同じはたらく番の効果は、どの型でも 1 つまで
    - ログとの対応: 同じポケモン・種類・番の ``persistent_effect_added`` があり、そのあとに、この効果を消したはずの
      イベント（``persistent_effect_removed``・``evolve``・``retreat``・``switch``・``forced_switch``（v0.4d））がない
    - v0.12 の ``Retaliation``（「ほのおのかべ」）: ``PreventDamage`` と同じ確認（自分自身・持ち主の番・次の相手の番・期限・バトル場だけ）に
      加えて、``attack_index`` がこのカードのワザの位置で、そのワザに ``DamageAndRetaliation`` が登録され、``amount`` がその実装の値
      （v0.13: 「こうらがえし」（``ReturnReceivedDamage``）も同じ確認で、決め方 ``basis`` と量（None）を登録された実装と照らす）
    """
    effects = pokemon.persistent_effects
    where = f"ポケモン {pokemon.pokemon_id} の持続する効果"
    if not isinstance(effects, tuple) or any(type(e) not in PERSISTENT_EFFECT_TYPES for e in effects):
        return [f"{where} {effects!r} が {PERSISTENT_EFFECT_TYPES} の値のタプルではない"]
    if not effects:
        return []
    if state.phase in SETUP_PHASES:
        return [f"{where} が対戦準備の段階（{state.phase.value}）にある"]
    problems = []
    if pokemon is not p.active and not all(getattr(e, "bench_ok", False) for e in effects):
        # v0.59: 「ショックアイ」（``CannotUsePowers.bench_ok``）は、選んだ相手のベンチのポケモンも受ける
        problems.append(f"プレイヤー {player} のベンチのポケモン {pokemon.pokemon_id} に持続する効果が残っている（p.311・p.322）")
    kinds = [e.kind for e in effects]
    # v0.45: 期限のない効果（「スミをかける」の「それ以後」。``AttackCoinCheck.lasting``）は、効果を与えた番の違うものが同じポケモンに重なりうる（受けたポケモンが
    # バトル場にいる間に、もう一度受ける）。重なった状態でワザを使うときは AC13 で止める（``flow._attack_check_failed``）。同じ種類・同じはたらく番は 1 つまで
    # v0.92: 期間を明示した効果（``PERIOD_EFFECT_TYPES``）は、期間の重なる同じ種類の効果を持ちうる（p.323「持続する効果は重複することがある」。いやなおとを続けて受ける）。
    # 同じ種類・同じはたらき始める番は 1 つまで（下の ``timed``）
    single = [e.kind for e in effects if not isinstance(e, PERIOD_EFFECT_TYPES) and e.turns_until_active == 1 and not lasting(e)]
    timed = [(e.kind, e.active_turn) for e in effects]
    if len(set(single)) != len(single) or len(set(timed)) != len(timed):
        problems.append(f"{where} に同じ種類の効果が重なっている {kinds}")
    recent = _events_since_turn_start(state)
    turn_ended = any(event["kind"] == "turn_end" for event in recent)
    for effect in effects:
        fields = (effect.source_card, effect.source_player, effect.created_turn, effect.active_turn)
        if any(type(value) is not int for value in fields):
            problems.append(f"{where} {effect!r} の項目が整数ではない")
            continue
        giver = 1 - player if effect.on_opponent else player  # v0.31: 相手に与える効果（しっぽをふる）は、効果を与えたのは相手
        if effect.on_opponent:
            if effect.source_player != giver or effect.source_card not in state.cards or state.cards[effect.source_card].owner != giver:
                problems.append(f"{where} {effect!r} の発生源が、相手（プレイヤー {giver}）のカードではない")
        elif getattr(effect, "from_other", False):
            # v0.86: 「ほのおのまもり」（``BenchProtection``）は、効果を与えたワザを使った自分のほかのポケモン（その場をはなれても消えない）
            if effect.source_player != player or effect.source_card not in state.cards or state.cards[effect.source_card].owner != player:
                problems.append(f"{where} {effect!r} の発生源が、持ち主（プレイヤー {player}）のカードではない")
        elif effect.source_player != player or effect.source_card != pokemon.card:
            problems.append(f"{where} {effect!r} の発生源が、このポケモン（カード {pokemon.card}、プレイヤー {player}）ではない")
        if isinstance(effect, (DamageReduction, ReducedDamageToSource)) and (type(effect.amount) is not int or effect.amount <= 0 or effect.amount % 10):
            problems.append(f"{where} {effect!r} の減らす量が 10 の倍数の正の数ではない")
        if isinstance(effect, ZeroDamageBelow):
            problems.extend(_zero_damage_below_problems(state, pokemon, effect, where))  # v0.45
        if isinstance(effect, HalvedDamage):
            problems.extend(_halved_damage_problems(state, pokemon, effect, where))  # v0.46
        if isinstance(effect, DoubledDamage):
            problems.extend(_terms_problems(state, pokemon, effect, where, "doubled_terms", (DoubledDamage,)))  # v0.75
        if isinstance(effect, ZeroDamageAtLeast):
            problems.extend(_terms_problems(state, pokemon, effect, where, "threshold_terms", (ZeroDamageAtLeast, effect.threshold)))  # v0.84
        if isinstance(effect, (BenchAttackDamageGuard, AttackEffectGuard, StatusImmunityWhileActive, StatusImmunityNextTurn)):
            problems.extend(_terms_problems(state, pokemon, effect, where, "guard_terms", (type(effect),)))  # v0.84
        if isinstance(effect, StatusImmunityWhileActive) and (effect.given_by not in state.cards or state.cards[effect.given_by].owner != player):
            problems.append(f"{where} {effect!r} を与えたカード {effect.given_by!r} が、持ち主（プレイヤー {player}）のカードではない")  # v0.84
        if effect.active_turn != effect.created_turn + effect.turns_until_active:
            what = "次の番（次の相手の番）" if effect.turns_until_active == 1 else f"{effect.turns_until_active} 番あと（次の自分の番）"
            problems.append(f"{where} {effect!r} のはたらく番が、効果を与えた番の{what}ではない")
        if not pokemon.current_form_turn <= effect.created_turn <= state.turn_number:
            problems.append(
                f"{where} {effect!r} を与えた番が、いまの姿になった番 {pokemon.current_form_turn}〜今の番 {state.turn_number} ではない"
            )
        elif state.first_player in PLAYERS and turn_owner(state, effect.created_turn) != giver:
            whose = "持ち主" if giver == player else f"効果を与えたプレイヤー {giver}"  # v0.31: 相手に与える効果（しっぽをふる）は与えたプレイヤー
            problems.append(f"{where} {effect!r} を、{whose}の番でない {effect.created_turn} 番に与えている")
        if lasting(effect):
            pass  # v0.45: 期限のない効果（「スミをかける」の「それ以後」）。期限では消えない（バトル場をはなれる・進化で消える）
        elif expires_at_turn_start(effect):
            # v0.34: 期限が「次の自分の番の始め」（「なきつく」）。はたらく番の終わり（turn_end）のあとのポケモンチェックの間は残り、次の番の最初に消える
            if state.turn_number > effect.active_turn:
                problems.append(f"{where} {effect!r} が、はたらく番 {effect.active_turn} の次の番の始めを過ぎて残っている")
        elif state.turn_number > end_turn(effect) or (state.turn_number == end_turn(effect) and turn_ended):
            # v0.92: 期間を明示した効果は最後の番（``end_turn``）、ほかの型は v0.91 までと同じはたらく番（``persistent.end_turn``）
            problems.append(f"{where} {effect!r} が、はたらく最後の番 {end_turn(effect)} の終わりを過ぎて残っている")
        if isinstance(effect, Retaliation):
            problems.extend(_retaliation_problems(state, pokemon, effect, where))  # v0.12
        if isinstance(effect, NextTurnAttackDamage):
            problems.extend(_next_turn_attack_damage_problems(state, pokemon, effect, where))  # v0.27
        if isinstance(effect, (CannotUseOwnAttack, CannotUseAttack)):
            problems.extend(_attack_lock_problems(state, pokemon, effect, where))  # v0.35
        if isinstance(effect, (AttackCoinCheck, CannotRetreat, CannotAttackWhileSourceActive, CannotUsePowers, CannotAttachEnergy, PowersStopped, BenchProtection)):
            problems.extend(_given_by_attack_problems(state, pokemon, effect, where))  # v0.36（v0.40: すごむ。v0.59: ショックアイ・クリスタルビーム）
        if isinstance(effect, (WeaknessChange, ResistanceChange, MaxHpSet)):
            problems.extend(_effective_value_effect_problems(state, pokemon, effect, where))  # v0.48
        if isinstance(effect, TailsDamageGuard):
            problems.extend(_damage_guard_problems(state, pokemon, effect, where))  # v0.60
        if isinstance(effect, PERIOD_EFFECT_TYPES):
            problems.extend(_period_effect_problems(state, pokemon, effect, where))  # v0.92
        problems.extend(_persistent_effect_log_problems(state, pokemon, effect, where))
    return problems


def _retaliation_problems(state: GameState, pokemon: PokemonInPlay, effect: Retaliation, where: str) -> list[str]:
    """「ほのおのかべ」（v0.12）・「こうらがえし」（v0.13）の持続する効果の、ワザの位置と与えるダメージの決め方・量が、このポケモンの
    カードの登録されたワザと合うか（登録された実装の ``retaliation_terms``。「ほのおのかべ」は (``fixed``, 10)、「こうらがえし」は
    (``received_damage``, None)）。"""
    if type(effect.attack_index) is not int or (effect.amount is not None and type(effect.amount) is not int):
        return [f"{where} {effect!r} のワザの位置・与えるダメージが整数ではない"]
    definition = _effect_attack_definition(state, effect)  # v0.49: 効果を与えたワザを印刷したカード（``attack_card``。なければこのポケモンのカード）
    if definition is None:
        return [f"{where} {effect!r} のワザを印刷したカード {effect.attack_card!r} が正しくない（この対戦のカードでない・効果を与えたポケモンのカードと同じなら書かない）"]
    if not 0 <= effect.attack_index < len(definition.attacks):
        return [f"{where} {effect!r} のワザの位置が、カード {definition.id} のワザではない"]
    entry = state.effects.attack_entry(definition.id, effect.attack_index)
    terms = getattr(entry.effect, "retaliation_terms", None) if entry is not None else None
    # v0.45: 倍数・コインの条件のある効果（「クロスカウンター」）は (決め方, 量, 倍数, コインの条件)。``Retaliation.terms``
    if terms is None or terms() != effect.terms():
        return [f"{where} {effect!r} が、カード {definition.id} の {effect.attack_index} 番目のワザ（登録された実装）の効果と合わない"]
    return []


def _zero_damage_below_problems(state: GameState, pokemon: PokemonInPlay, effect: ZeroDamageBelow, where: str) -> list[str]:
    """「かたくなる」（v0.45）の持続する効果のしきい値が、効果を与えたワザ（ログ ``persistent_effect_added`` の ``effect``）の登録された実装の値
    （``threshold_terms``）と合うか。対応するログがなければ ``_persistent_effect_log_problems`` が見つける。"""
    if type(effect.threshold) is not int or effect.threshold <= 0 or effect.threshold % 10:
        return [f"{where} {effect!r} のしきい値が 10 の倍数の正の数ではない"]
    added = _persistent_effect_added_event(state, pokemon, effect)
    if added is None:
        return []
    card_id, _, index = str(added.get("effect", "")).partition("#")
    entry = state.effects.attack_entry(card_id, int(index)) if index.isdigit() else None
    terms = getattr(entry.effect, "threshold_terms", None) if entry is not None else None
    if terms is None or terms() != (ZeroDamageBelow, effect.threshold):
        return [f"{where} {effect!r} が、効果を与えたワザ {added.get('effect')!r}（登録された実装）の効果と合わない"]
    return []


def _terms_problems(state: GameState, pokemon: PokemonInPlay, effect, where: str, method: str, expected: tuple) -> list[str]:
    """持続する効果が、効果を与えたワザ（ログ ``persistent_effect_added`` の ``effect``）の登録された実装（``method`` の値が ``expected``）の効果と合うか（v0.75。
    「もろばバサミ」の ``doubled_terms``）。対応するログがなければ ``_persistent_effect_log_problems`` が見つける。"""
    added = _persistent_effect_added_event(state, pokemon, effect)
    if added is None:
        return []
    card_id, _, index = str(added.get("effect", "")).partition("#")
    entry = state.effects.attack_entry(card_id, int(index)) if index.isdigit() else None
    terms = getattr(entry.effect, method, None) if entry is not None else None
    if terms is None or terms() != expected:
        return [f"{where} {effect!r} が、効果を与えたワザ {added.get('effect')!r}（登録された実装）の効果と合わない"]
    return []


def _halved_damage_problems(state: GameState, pokemon: PokemonInPlay, effect: HalvedDamage, where: str) -> list[str]:
    """「リフレクター」（v0.46）の持続する効果が、効果を与えたワザ（ログ ``persistent_effect_added`` の ``effect``）の登録された実装（``halved_terms``）の効果と合うか。
    対応するログがなければ ``_persistent_effect_log_problems`` が見つける。"""
    added = _persistent_effect_added_event(state, pokemon, effect)
    if added is None:
        return []
    card_id, _, index = str(added.get("effect", "")).partition("#")
    entry = state.effects.attack_entry(card_id, int(index)) if index.isdigit() else None
    terms = getattr(entry.effect, "halved_terms", None) if entry is not None else None
    if terms is None or terms() != (HalvedDamage,):
        return [f"{where} {effect!r} が、効果を与えたワザ {added.get('effect')!r}（登録された実装）の効果と合わない"]
    return []


def _next_turn_attack_damage_problems(state: GameState, pokemon: PokemonInPlay, effect: NextTurnAttackDamage, where: str) -> list[str]:
    """「つるぎのまい」（v0.27）の持続する効果の、効果を与えたワザの位置・ダメージが変わるワザの位置・変えたあとのダメージが、このポケモンの
    カードの登録されたワザと合うか（登録された実装の ``next_turn_terms``。「つるぎのまい」は (1, 60)）。"""
    fields = (effect.attack_index, effect.target_attack_index, effect.amount)
    if any(type(value) is not int for value in fields):
        return [f"{where} {effect!r} のワザの位置・ダメージが整数ではない"]
    definition = _effect_attack_definition(state, effect)  # v0.49
    if definition is None:
        return [f"{where} {effect!r} のワザを印刷したカード {effect.attack_card!r} が正しくない（この対戦のカードでない・効果を与えたポケモンのカードと同じなら書かない）"]
    if not 0 <= effect.attack_index < len(definition.attacks):
        return [f"{where} {effect!r} のワザの位置が、カード {definition.id} のワザではない"]
    entry = state.effects.attack_entry(definition.id, effect.attack_index)
    terms = getattr(entry.effect, "next_turn_terms", None) if entry is not None else None
    expected = terms() if terms is not None else None
    # v0.35: 「数をかける」効果（「きあいだめ」）の実装は (変わるワザの位置, かける数, 変え方, 自分へのダメージにも) を返す。v0.27 の「つるぎのまい」は
    # (変わるワザの位置, その数) で、変え方は「その数にする」・自分へのダメージには当てはめない
    if expected is not None and len(expected) == 2:
        expected = (*expected, "set", False)
    if expected is None or expected != (effect.target_attack_index, effect.amount, effect.operation, effect.includes_self_damage):
        return [f"{where} {effect!r} が、カード {definition.id} の {effect.attack_index} 番目のワザ（登録された実装）の効果と合わない"]
    return []


def _attack_lock_problems(state: GameState, pokemon: PokemonInPlay, effect, where: str) -> list[str]:
    """v0.35: 「あわあわ」（``CannotUseOwnAttack``）・「ドわすれ」（``CannotUseAttack``）の持続する効果の、効果を与えたワザ（``source_card`` のカードの
    ``attack_index``。登録された実装の ``attack_lock_terms`` がこの効果の型と、自分のワザを使えなくするなら使えなくなるワザの位置を返す）と、使えなくなる
    ワザ（受けているポケモンのいちばん上のカードの ``target_attack_index``）が合うか。"""
    if type(effect.attack_index) is not int or type(effect.target_attack_index) is not int:
        return [f"{where} {effect!r} のワザの位置が整数ではない"]
    source = _effect_attack_definition(state, effect)  # v0.49: 効果を与えたワザを印刷したカード（``attack_card``。なければ効果を与えたポケモンのカード）
    if source is None:
        return [f"{where} {effect!r} のワザを印刷したカード {effect.attack_card!r} が正しくない（この対戦のカードでない・効果を与えたポケモンのカードと同じなら書かない）"]
    if not 0 <= effect.attack_index < len(source.attacks):
        return [f"{where} {effect!r} の効果を与えたワザの位置が、カード {source.id} のワザではない"]
    entry = state.effects.attack_entry(source.id, effect.attack_index)
    terms = getattr(entry.effect, "attack_lock_terms", None) if entry is not None else None
    if terms is None or terms()[0] is not type(effect) or (terms()[1] is not None and terms()[1] != effect.target_attack_index):
        return [f"{where} {effect!r} が、カード {source.id} の {effect.attack_index} 番目のワザ（登録された実装）の効果と合わない"]
    # v0.76: 「あわあわ」・「きあいずつき」（登録の位置が None）は効果を与えたワザ自身、ワンリキーの「きあいいっぱつ」は登録の位置（「どつく」）
    own_target = effect.attack_index if terms()[1] is None else terms()[1]
    if isinstance(effect, CannotUseOwnAttack) and effect.target_attack_index != own_target:
        return [f"{where} {effect!r} の使えなくなるワザが、効果を与えたワザの登録（このカードの {own_target} 番目のワザ）と違う"]
    # v0.49: 使えなくなるワザを印刷したカード（「あわあわ」は効果を与えたワザと同じカード、「ドわすれ」は ``target_attack_card``。なければこのポケモンのカード）
    if isinstance(effect, CannotUseOwnAttack):
        target = source
    else:
        target = state.card_def(pokemon.card) if effect.target_attack_card is None else state.definitions.get(effect.target_attack_card)
        if effect.target_attack_card is not None and (target is None or effect.target_attack_card == state.cards[pokemon.card].card_id):
            return [f"{where} {effect!r} の使えなくなるワザを印刷したカード {effect.target_attack_card!r} が正しくない（このポケモンのカードなら書かない）"]
    if not 0 <= effect.target_attack_index < len(target.attacks):
        return [f"{where} {effect!r} の使えなくなるワザの位置が、カード {target.id} のワザではない"]
    return []


def _disguise_problems(state: GameState, player: int, pokemon: PokemonInPlay) -> list[str]:
    """v0.49（形式 14）: 「ばける」でのせたカード（``PokemonInPlay.disguise``）の整合。

    - のせたカードは持ち主の進化カード（1 進化・2 進化のポケモンのカード）で、いちばん上のカードは「ばける」（``Shapeshift``）を持つ
    - のせたカードのあるポケモンは、ねむり・マヒ・こんらんではない（なったときにトラッシュされる）
    - ログに、このポケモンにこのカードをのせた ``disguise`` があり、そのあとに、このカードを外した ``disguise_removed`` がない（ログのない盤面（テストで直接作った
      盤面）は確かめない。``disguise`` のログがあるのに合わなければ問題）
    """
    card = pokemon.disguise
    if card is None:
        return []
    where = f"プレイヤー {player} のポケモン {pokemon.pokemon_id} の「ばける」でのせたカード {card!r}"
    if type(card) is not int or card not in state.cards:
        return [f"{where} が正しくない"]
    problems = []
    if not state.printed_def(card).is_evolution_pokemon:
        problems.append(f"{where} が進化カードではない")
    if shapeshift_slot(state, pokemon) is None:
        problems.append(f"{where} の下のカード {pokemon.card} が「ばける」を持たない")
    if pokemon.conditions.exclusive is not None:
        problems.append(f"{where} のあるポケモンが、ねむり・マヒ・こんらん状態（なったときにトラッシュされる）")
    events = [e for e in state.log if e["kind"] in ("disguise", "disguise_removed") and e.get("pokemon_id") == pokemon.pokemon_id]
    if events and (events[-1]["kind"] != "disguise" or events[-1].get("card") != card):
        problems.append(f"{where} が、ログの最後の「ばける」の記録 {events[-1]} と合わない")
    return problems


def _recall_problems(state: GameState) -> list[str]:
    """v0.49（形式 14）: 「思い出させる」の記録（``GameState.recalls``）は、今の番に番のプレイヤーが使ったもので、使ったトレーナーは持ち主のトラッシュ（使い終えた）か
    使用中にあり、今の番のログに、同じプレイヤー・対戦ポケモン・トレーナーの ``recall`` がちょうど 1 回ある。重ならない。番の終わりのあとには残らない。"""
    recalls = state.recalls
    if not isinstance(recalls, tuple):
        return [f"「思い出させる」の記録 {recalls!r} がタプルではない"]
    if not recalls:
        return []
    problems = []
    if len(set(recalls)) != len(recalls):
        problems.append(f"「思い出させる」の記録 {recalls} が重なっている")
    recent = _events_since_turn_start(state)
    if any(e["kind"] == "turn_end" for e in recent):
        problems.append(f"「思い出させる」の記録 {recalls} が、番の終わりのあとに残っている")
    for record in recalls:
        where = f"「思い出させる」の記録 {record}"
        if record.turn != state.turn_number or record.player != state.current_player:
            problems.append(f"{where} が、今の番の番のプレイヤーのものではない")
            continue
        if record.trainer not in state.cards or state.cards[record.trainer].owner != record.player:
            problems.append(f"{where} のトレーナーが、使ったプレイヤーのカードではない")
            continue
        used = state.trainer_in_use
        if record.trainer not in state.players[record.player].discard and not (used is not None and used.card == record.trainer):
            problems.append(f"{where} のトレーナーが、トラッシュにも使用中にもない")
        matching = [e for e in recent if e["kind"] == "recall" and e.get("player") == record.player and e.get("card") == record.trainer
                    and e.get("pokemon_id") == record.pokemon_id and e.get("pokemon") == record.card]
        if len(matching) != 1:
            problems.append(f"{where} に対応する、今の番のログ recall が {len(matching)} 回")
    return problems


def _trainer_stack_problems(state: GameState, used) -> list[str]:
    """v0.58（docs/stadium-reuse-special-energy-v0.58.md 4 章）: 外側のトレーナーの効果で使っている内側のトレーナーと、外側の使用の並び（``trainer_stack``）の整合。

    - 外側の使用があるのは、使用中のトレーナーが外側の効果で使っているカード（``via``）のときだけで、``via`` は並びの最後（すぐ外側）のカード。並びの各段も同じ
    - 外側のカードは、相手のトラッシュのトレーナーを使う効果（サイキックコントロール。``UseOpponentDiscardTrainer``）のカード
    - いちばん外側の使用は手札から使ったもの（``via`` なし）で、持ち主が番のプレイヤー（錯乱ジムで借りていれば使うプレイヤーは相手）
    - 外側の効果で使っているカードの持ち主は、外側の使うプレイヤーの相手（相手のトラッシュのカード）"""
    from .effects import UseOpponentDiscardTrainer

    problems: list[str] = []
    chain = (*state.trainer_stack, used)
    for i, item in enumerate(chain):
        if item.user is not None and (item.user not in PLAYERS or item.user == item.player):
            problems.append(f"使用中のトレーナー {item} の使うプレイヤーが正しくない（持ち主と同じ・知らないプレイヤー）")
        if i == 0:
            if item.via is not None:
                problems.append(f"いちばん外側のトレーナー {item} が、外側の効果で使っているカードになっている")
            if item.player != state.current_player:
                problems.append(f"いちばん外側のトレーナーの持ち主 {item.player} が、番のプレイヤー {state.current_player} ではない")
            continue
        outer = chain[i - 1]
        if item.via != outer.card:
            problems.append(f"内側のトレーナー {item} の外側のカード {item.via} が、外側の使用 {outer.card} と違う")
        entry = state.effects.trainer_entry(state.cards[outer.card].card_id) if outer.card in state.cards else None
        if entry is None or not isinstance(entry.effect, UseOpponentDiscardTrainer):
            problems.append(f"外側のトレーナー {outer} が、相手のトラッシュのトレーナーを使う効果のカードではない")
        if item.player != 1 - outer.using_player:
            problems.append(f"内側のトレーナー {item} の持ち主が、外側の使うプレイヤー {outer.using_player} の相手ではない")
    return problems


def _effect_attack_definition(state: GameState, effect):
    """持続する効果を与えたワザを印刷したカードの定義（v0.49。``persistent.effect_attack_card``）。``attack_card`` を書くのは、ワザの出どころが効果を与えたポケモンの
    いちばん上のカードと違うときだけ（同じなら書かない。v0.48 までの効果と同じ形）。この対戦のカードでなければ None。"""
    card_id = effect_attack_card(state, effect)
    if effect.attack_card is not None and effect.attack_card == state.cards[effect.source_card].card_id:
        return None
    return state.definitions.get(card_id)


def _given_by_attack_problems(state: GameState, pokemon: PokemonInPlay, effect, where: str) -> list[str]:
    """v0.36: 「すなかけ」・「えんまく」など（``AttackCoinCheck``）・「アイスバーン」・「わしづかみ」（``CannotRetreat``）の持続する効果が、それを与えたワザ
    （ログ ``persistent_effect_added`` の ``effect``。相手のワザとして使ったときは、使ったワザ。効果の ``source_card`` は使ったポケモン）の登録された実装の
    効果と合うか（``attack_check_terms``: (型, 「1回できえる」か)・``retreat_lock_terms``: 型）。対応するログがなければ ``_persistent_effect_log_problems``
    が見つける。"""
    if isinstance(effect, AttackCoinCheck) and (type(effect.single_use) is not bool or type(effect.lasting) is not bool):
        return [f"{where} {effect!r} の「1回できえる」・「それ以後」が真偽値ではない"]
    if isinstance(effect, AttackCoinCheck) and effect.single_use and effect.lasting:
        return [f"{where} {effect!r} が「1回できえる」と「それ以後」の両方を持つ（どの文面にもない組）"]
    added = _persistent_effect_added_event(state, pokemon, effect)
    if added is None:
        return []
    card_id, _, index = str(added.get("effect", "")).partition("#")
    entry = state.effects.attack_entry(card_id, int(index)) if index.isdigit() else None
    if isinstance(effect, AttackCoinCheck):
        terms = getattr(entry.effect, "attack_check_terms", None) if entry is not None else None
        # v0.45: 期限のない効果（「スミをかける」）の実装は (型, 「1回できえる」か, 「それ以後」か) を返す。v0.36 の実装は (型, 「1回できえる」か)
        expected = (AttackCoinCheck, effect.single_use, True) if effect.lasting else (AttackCoinCheck, effect.single_use)
    elif isinstance(effect, CannotAttackWhileSourceActive):
        # v0.40: 「すごむ」。登録された実装の ``conditional_lock_terms`` は (型, 最大 HP の上限)。受けているポケモン（いちばん上のカード。進化すると効果は消える）の
        # 最大 HP が上限以下（効果を与えたときに確かめた条件）
        # v0.48: 最大HPの条件は効果を与えたときに確かめたもので、今の最大HPでは確かめない（最大HPは［ガスのからだ］のエネルギー・「きょだいか」で、効果を与えた
        # あとにも変わる。説明は「このワザを受けた相手が「最大HPが50以下」のポケモンなら」で、受けたときの条件）
        terms = getattr(entry.effect, "conditional_lock_terms", None) if entry is not None else None
        expected = (CannotAttackWhileSourceActive, terms()[1]) if terms is not None else None
    elif isinstance(effect, CannotUsePowers):
        terms = getattr(entry.effect, "power_lock_terms", None) if entry is not None else None  # v0.59: ショックアイ
        expected = CannotUsePowers
    elif isinstance(effect, CannotAttachEnergy):
        terms = getattr(entry.effect, "attach_lock_terms", None) if entry is not None else None  # v0.59: クリスタルビーム
        expected = CannotAttachEnergy
    elif isinstance(effect, PowersStopped):
        terms = getattr(entry.effect, "stop_terms", None) if entry is not None else None  # v0.86: スタンウェーブ
        expected = (PowersStopped,)
    elif isinstance(effect, BenchProtection):
        terms = getattr(entry.effect, "protection_terms", None) if entry is not None else None  # v0.86: ほのおのまもり
        expected = (BenchProtection,)
    else:
        terms = getattr(entry.effect, "retreat_lock_terms", None) if entry is not None else None
        expected = CannotRetreat
    if (terms is None or terms() != expected or added.get("single_use", False) != getattr(effect, "single_use", False)
            or added.get("lasting", False) != getattr(effect, "lasting", False)):
        return [f"{where} {effect!r} が、効果を与えたワザ {added.get('effect')!r}（登録された実装）の効果と合わない"]
    return []


def _period_effect_problems(state: GameState, pokemon: PokemonInPlay, effect, where: str) -> list[str]:
    """v0.92: 期間を明示した持続する効果（``PERIOD_EFFECT_TYPES``。クモのす・くろいまなざし・ヨーギラスのにらみつける・いやなおと）の整合。

    - 与えたワザ（ログ ``persistent_effect_added`` の ``effect``。相手のワザとして使ったときは使ったワザ）の登録された実装の ``period_terms``（型・始まりと終わりの番の数・発生源が
      バトル場にいる間だけか・消える契機（いやなおとは増やす数も））と、効果の値が同じ
    - ログの ``end_turn``・``source_pokemon``・``while_source_active``・``ends_on``（いやなおとは ``amount``）が効果の値と同じ
    - 説明が「このカード…がバトル場をはなれたとき、この効果は消える」（``SOURCE_LEAVES_ACTIVE``）の効果は、発生源（場の番号）が今も持ち主のバトル場にいる（はなれたら、はなれた時点で
      消しているはず。``persistent.remove_source_left_effects``）
    対応するログがなければ ``_persistent_effect_log_problems`` が見つける。"""
    problems = []
    if SOURCE_LEAVES_ACTIVE in effect.ends_on:
        active = state.players[effect.source_player].active if effect.source_player in PLAYERS else None
        if active is None or active.pokemon_id != effect.source_pokemon:
            problems.append(f"{where} {effect!r} の発生源のポケモン {effect.source_pokemon} がバトル場をはなれたのに残っている（はなれたとき消える効果）")
    added = _persistent_effect_added_event(state, pokemon, effect)
    if added is None:
        return problems
    card_id, _, index = str(added.get("effect", "")).partition("#")
    entry = state.effects.attack_entry(card_id, int(index)) if index.isdigit() else None
    options = period_terms_options(entry.effect) if entry is not None else ()
    actual = (type(effect), effect.active_turn - effect.created_turn, None if effect.end_turn is None else effect.end_turn - effect.created_turn,
              effect.while_source_active, effect.ends_on)
    logged = (added.get("end_turn"), added.get("source_pokemon"), added.get("while_source_active", False), tuple(added.get("ends_on", ())))
    if isinstance(effect, ReceivedAttackDamageBonus):
        actual += (effect.amount,)
        logged += (added.get("amount"),)
    if isinstance(effect, PeriodLeaveLock):
        # v0.93: 「バトル場をはなれられない」効果は、きぜつの例外も登録と照らす（ログはあるときだけ ``knockout_exception``）
        actual += (effect.knockout_exception,)
        logged += (added.get("knockout_exception", False),)
    if actual not in options:
        problems.append(f"{where} {effect!r} が、効果を与えたワザ {added.get('effect')!r}（登録された実装）の期間・消える契機と合わない")
    expected_log = (effect.end_turn, effect.source_pokemon, effect.while_source_active, effect.ends_on) + ((effect.amount,) if isinstance(effect, ReceivedAttackDamageBonus) else ())
    if isinstance(effect, PeriodLeaveLock):
        expected_log += (effect.knockout_exception,)
    if logged != expected_log:
        problems.append(f"{where} {effect!r} が、与えたログの期間・発生源 {logged!r} と合わない")
    if isinstance(effect, PeriodLeaveLock) and effect.source_left:
        # v0.93: 発生源がはなれた印（くいつく）は、与えたあとのログ ``persistent_effect_source_left`` と合う
        marked = any(e["kind"] == "persistent_effect_source_left" and e.get("pokemon_id") == pokemon.pokemon_id and e.get("persistent_effect") == effect.kind
                     and e.get("created_turn") == effect.created_turn and e.get("source_pokemon") == effect.source_pokemon for e in state.log)
        if not marked:
            problems.append(f"{where} {effect!r} の発生源がはなれた印に、対応するログ persistent_effect_source_left がない")
    return problems


def period_terms_options(effect) -> tuple[tuple, ...]:
    """v0.92・v0.93: ワザの登録された実装が与えうる期間を明示した持続する効果の、型と期間・消える契機の組の並び（``period_terms``。2 つの効果を与えるワザ（わるいアリゲイツの
    「かぶりつく」）は ``period_terms_list``）。どちらもなければ ()。"""
    if hasattr(effect, "period_terms_list"):
        return tuple(effect.period_terms_list())
    if hasattr(effect, "period_terms"):
        return (effect.period_terms(),)
    return ()


def _effective_value_effect_problems(state: GameState, pokemon: PokemonInPlay, effect, where: str) -> list[str]:
    """v0.48: 「テクスチャー1」（``WeaknessChange``）・「テクスチャー2」（``ResistanceChange``）・「きょだいか」（``MaxHpSet``）の持続する効果が、与えたワザ（ログ
    ``persistent_effect_added`` の ``effect``。相手のワザとして使ったときは使ったワザ）の登録された実装（``color_terms``: 与えうる型の並び・``max_hp_terms``: (型, 数)）と合い、
    ログに書いた色・数と同じか。色は無色以外（「「無色」にはできない」）。対応するログがなければ ``_persistent_effect_log_problems`` が見つける。"""
    if isinstance(effect, MaxHpSet):
        if type(effect.amount) is not int or effect.amount <= 0 or effect.amount % 10:
            return [f"{where} {effect!r} の最大HPが 10 の倍数の正の数ではない"]
        attr, expected, value, logged_key = "max_hp_terms", (MaxHpSet, effect.amount), effect.amount, "amount"
    else:
        if not isinstance(effect.color, EnergyType) or effect.color is EnergyType.COLORLESS:
            return [f"{where} {effect!r} の色が、無色以外の色ではない"]
        attr, expected, value, logged_key = "color_terms", (type(effect),), effect.color.value, "color"
    added = _persistent_effect_added_event(state, pokemon, effect)
    if added is None:
        return []
    card_id, _, index = str(added.get("effect", "")).partition("#")
    entry = state.effects.attack_entry(card_id, int(index)) if index.isdigit() else None
    terms = getattr(entry.effect, attr, None) if entry is not None else None
    # v0.88: ``color_terms`` は与えうる型の並び（かっこいいポリゴンの「テクスチャーマジック」は弱点と抵抗力の両方）。``max_hp_terms`` は (型, 数) の 1 組
    matches = terms is not None and (expected[0] in terms() if attr == "color_terms" else terms() == expected)
    if not matches or added.get(logged_key) != value:
        return [f"{where} {effect!r} が、効果を与えたワザ {added.get('effect')!r}（登録された実装・ログの {logged_key}）と合わない"]
    return []


def _damage_guard_problems(state: GameState, pokemon: PokemonInPlay, effect, where: str) -> list[str]:
    """v0.60: 「かげぶんしん」の持続する効果（``TailsDamageGuard``）が、与えたワザ（ログ ``persistent_effect_added`` の ``effect``。相手のワザとして使ったときは使ったワザ）の
    登録された実装（``guard_terms``: 型）と合うか。消える契機（ダメージを受けた・バトル場をはなれた）は ``_persistent_effect_log_problems`` がログと照らす。"""
    added = _persistent_effect_added_event(state, pokemon, effect)
    if added is None:
        return []
    card_id, _, index = str(added.get("effect", "")).partition("#")
    entry = state.effects.attack_entry(card_id, int(index)) if index.isdigit() else None
    terms = getattr(entry.effect, "guard_terms", None) if entry is not None else None
    if terms is None or terms() is not TailsDamageGuard:
        return [f"{where} {effect!r} が、効果を与えたワザ {added.get('effect')!r}（登録された実装）の効果と合わない"]
    return []


def _type_shift_problems(state: GameState, player: int, pokemon: PokemonInPlay) -> list[str]:
    """v0.48（形式 13）: 特殊能力で色を変えた記録（``PokemonInPlay.type_shift``。モルフォンの［へんしょく］）の整合。

    - 型は ``TypeShift``。色は ``EnergyType``、使った番は、いまの姿になった番〜今の番で、持ち主の番。使ったときのいちばん上のカード（``source_card``）は今のいちばん上の
      カードで、そのカードに色を変える特殊能力（``effects.ShiftColor``）が登録されている（進化したら記録は消える）
    - ログとの対応: そのポケモンの最後の ``type_shift`` が、この記録の番・色。そのあとに、このポケモンがバトル場からベンチにもどったログ（``retreat``・``switch``・
      ``forced_switch``）があることと ``returned_to_bench`` が同じ（エンジンは記録をログから決めない。食い違っていないかだけを確かめる）"""
    shift = pokemon.type_shift
    if shift is None:
        return []
    where = f"ポケモン {pokemon.pokemon_id} の色を変えた記録"
    if not isinstance(shift, TypeShift) or not isinstance(shift.color, EnergyType) or type(shift.turn) is not int or type(shift.returned_to_bench) is not bool:
        return [f"{where} {shift!r} の形が正しくない"]
    problems = []
    if shift.source_card != pokemon.card:
        problems.append(f"{where} {shift!r} の使ったカードが、いちばん上のカード {pokemon.card} ではない")
    if type_shift_power(state, pokemon) is None:
        problems.append(f"{where} {shift!r} のポケモンに、色を変える特殊能力がない")
    if not pokemon.current_form_turn <= shift.turn <= state.turn_number:
        problems.append(f"{where} {shift!r} の番が、いまの姿になった番〜今の番ではない")
    elif state.first_player in PLAYERS and turn_owner(state, shift.turn) != player:
        problems.append(f"{where} {shift!r} の番 {shift.turn} が、持ち主の番ではない")
    benched = False
    for event in reversed(state.log):
        kind = event["kind"]
        if kind == "type_shift" and event.get("pokemon_id") == pokemon.pokemon_id:
            if event["turn"] != shift.turn or event.get("color") != shift.color.value:
                problems.append(f"{where} {shift!r} が、最後のログ type_shift（{event['turn']} 番・{event.get('color')}）と違う")
            if benched != shift.returned_to_bench:
                problems.append(f"{where} {shift!r} のベンチにもどったか（{shift.returned_to_bench}）が、ログ（{benched}）と違う")
            return problems
        if (kind == "retreat" and event.get("old_active") == pokemon.card) or (
                kind in ("switch", "forced_switch") and event.get("old_active_pokemon_id") == pokemon.pokemon_id):
            benched = True
    return problems + [f"{where} {shift!r} に対応するログ type_shift がない"]


def _marker_problems(state: GameState, pokemon: PokemonInPlay) -> list[str]:
    """v0.90（docs/markers-counters-v0.90.md 3 章。形式 24）: 場のポケモンにのっているマーカー・カウンター（``PokemonInPlay.markers``）の整合。

    - ``Marker`` のタプル。種類は ``MARKER_AND_COUNTER_KINDS``、のせたプレイヤーは 0・1、のせたワザのカードは対戦のカード、番は整数で、いまの姿になった番〜今の番（進化・退化で
      取りのぞくので、それより前の番のものは残らない）。対戦準備の段階にはない
    - 色を持つのは色マーカーだけで、色は無色以外の色。色マーカーは 1 つまで（のせ替える。2 つあると、どの色としてあつかうかが決まらない）。ほかの種類の数に上限は置かない
      （のろいマーカーは「2つ以上のっていても、効果は同じ」。ベトベトマーカー・ほねカウンターは「のっていなければ」・たべものカウンターは使うための条件で数が決まるが、状態の不正には
      しない）
    - ログとの対応: このポケモン（番号）の ``marker_added`` の数から ``marker_removed`` の ``count`` の合計を引いた数が、種類ごとに今の数と同じ。色マーカーの色は最後の
      ``marker_added`` の色（エンジンは記録をログから決めない。食い違っていないかだけを確かめる）"""
    markers = pokemon.markers
    where = f"ポケモン {pokemon.pokemon_id} のマーカー・カウンター"
    if not isinstance(markers, tuple) or any(type(m) is not Marker for m in markers):
        return [f"{where} {markers!r} が Marker のタプルではない"]
    if not markers:
        return []
    if state.phase in SETUP_PHASES:
        return [f"{where} が対戦準備の段階（{state.phase.value}）にある"]
    problems = []
    for marker in markers:
        if marker.kind not in MARKER_AND_COUNTER_KINDS:
            problems.append(f"{where} {marker!r} の種類が {MARKER_AND_COUNTER_KINDS} のどれでもない")
            continue
        if marker.player not in PLAYERS or type(marker.turn) is not int or type(marker.source_card) is not int or marker.source_card not in state.cards                 or not isinstance(marker.attack, str):
            problems.append(f"{where} {marker!r} の項目が正しくない")
            continue
        if not pokemon.current_form_turn <= marker.turn <= state.turn_number:
            problems.append(f"{where} {marker!r} の番が、いまの姿になった番〜今の番ではない（進化・退化で取りのぞくはず）")
        if (marker.kind == MARKER_COLOR) != isinstance(marker.color, EnergyType) or marker.color is EnergyType.COLORLESS:
            problems.append(f"{where} {marker!r} の色が正しくない（色を持つのは色マーカーだけ。無色以外）")
    colors = [m for m in markers if m.kind == MARKER_COLOR]
    if len(colors) > 1:
        problems.append(f"{where} に色マーカーが {len(colors)} つ（のせ替えるので 1 つまで）")
    if problems:
        return problems
    added: dict[str, int] = {}
    removed: dict[str, int] = {}
    last_color = None
    for event in state.log:
        if event.get("pokemon_id") != pokemon.pokemon_id:
            continue
        if event["kind"] == "marker_added":
            added[event["marker"]] = added.get(event["marker"], 0) + 1
            if event["marker"] == MARKER_COLOR:
                last_color = event.get("color")
        elif event["kind"] == "marker_removed":
            removed[event["marker"]] = removed.get(event["marker"], 0) + event["count"]
    for kind in MARKER_AND_COUNTER_KINDS:
        count = sum(1 for m in markers if m.kind == kind)
        if added.get(kind, 0) - removed.get(kind, 0) != count:
            problems.append(f"{where} の {kind} の数 {count} が、ログ（のせた {added.get(kind, 0)}・取りのぞいた {removed.get(kind, 0)}）と合わない")
    if colors and last_color != colors[0].color.value:
        problems.append(f"{where} の色マーカーの色 {colors[0].color.value} が、最後のログ marker_added の色 {last_color} と違う")
    return problems


def _persistent_effect_added_event(state: GameState, pokemon: PokemonInPlay, effect):
    """持続する効果を与えたログ（``persistent_effect_added``。同じポケモン・種類・番・発生源）。なければ None（v0.36）。"""
    for event in reversed(state.log):
        if (
            event["kind"] == "persistent_effect_added"
            and event.get("pokemon_id") == pokemon.pokemon_id
            and event.get("persistent_effect") == effect.kind
            and event["turn"] == effect.created_turn
            and event.get("active_turn") == effect.active_turn
            and event.get("source_card") == effect.source_card
        ):
            return event
    return None


def _persistent_effect_log_problems(state: GameState, pokemon: PokemonInPlay, effect, where: str) -> list[str]:
    """持続する効果が、それを与えたログ（``persistent_effect_added``）と対応し、そのあとに消したはずのイベントがないか（v0.4b）。"""
    for event in reversed(state.log):
        kind = event["kind"]
        if kind == "persistent_effect_added":
            if (
                event.get("pokemon_id") == pokemon.pokemon_id
                and event.get("persistent_effect") == effect.kind
                and event["turn"] == effect.created_turn
                and event.get("active_turn") == effect.active_turn
                and event.get("source_card") == effect.source_card
            ):
                return []
            continue
        if (
            kind == "persistent_effect_removed"
            and event.get("pokemon_id") == pokemon.pokemon_id
            and event.get("persistent_effect") == effect.kind
            # v0.27: 同じ効果（与えた番・はたらく番）を消したログ。「つるぎのまい」は、はたらく番にもう一度使うと、新しい効果を与えたあとに
            # 前の効果が期限で消える（同じ種類の別の効果を消したログが、新しい効果を与えたログのあとにある）
            and event.get("created_turn") == effect.created_turn
            and event.get("active_turn") == effect.active_turn
        ):
            return [f"{where} {effect!r} が、消したあと（ログ persistent_effect_removed）にも残っている"]
        if kind == "evolve" and event.get("pokemon_id") == pokemon.pokemon_id:
            return [f"{where} {effect!r} が、進化（ログ evolve）の前の効果のまま残っている（p.310・p.323）"]
        if (kind == "retreat" and event.get("old_active") == pokemon.card) or (
            kind in ("switch", "forced_switch") and event.get("old_active_pokemon_id") == pokemon.pokemon_id  # forced_switch は v0.4d
        ):
            return [f"{where} {effect!r} が、ベンチに戻った（ログ {kind}）あとにも残っている（p.311・p.322）"]
    return [f"{where} {effect!r} に対応するログ persistent_effect_added がない"]


def _trainer_lock_problems(state: GameState) -> list[str]:
    """v0.47（形式 12）: プレイヤーに与えた、期限のあるトレーナーカードの使用の禁止（``GameState.trainer_locks``。ずつう・こうしゅうは）の整合。

    - 型は ``TrainerUseLock``。使えなくなるプレイヤー ``player`` は与えたプレイヤー ``source_player`` の相手。与えた番は与えたプレイヤーの番で、消える番は与えた番 + 1
      （「次の相手の番の終わりまで」）。今の番は与えた番〜消える番（消える番の終わりに消す）。同じプレイヤー・同じ消える番の禁止は 1 つまで
    - 与えたワザ（``effect``。``AttackKey`` の文字列）の登録された実装が、禁止を与える実装（``lock_terms``）。``source_card`` は対戦のカード
    - ログとの対応: 今の番と前の番（禁止が残りうる範囲）のログで、与えた（``trainer_lock_added``）がまだ消していない（``trainer_lock_removed`` がない）禁止と、状態の
      禁止が同じ（状態だけにある・ログだけにある禁止がない）。エンジンは禁止をログから決めない（状態とログが食い違っていないかだけを確かめる）"""
    locks = state.trainer_locks
    if type(locks) is not tuple:
        return [f"期限のあるトレーナーの使用の禁止 {locks!r} がタプルではない"]
    problems: list[str] = []
    keys = []
    for lock in locks:
        if not isinstance(lock, TrainerUseLock):
            problems.append(f"期限のあるトレーナーの使用の禁止 {lock!r} の型が TrainerUseLock ではない")
            continue
        where = f"プレイヤー {lock.player!r} のトレーナーの使用の禁止（{lock.effect}）"
        trainer_origin = lock.origin == "trainer"  # v0.56: ロケット団の実験の「うら」（使ったプレイヤー自身。与えた番 + 2）
        if lock.origin == HAND_TRAINER_LOCK:
            problems += _hand_trainer_lock_problems(state, lock, where)
            keys.append((lock.player, lock.expires_turn, lock.origin))
            continue
        if lock.origin not in ("attack", "trainer", ATTACK_HAND_TRAINER_LOCK):
            problems.append(f"{where} の出どころ {lock.origin!r} が attack・trainer・hand・attack_hand ではない")
            continue
        if lock.player not in PLAYERS or lock.source_player != (lock.player if trainer_origin else 1 - lock.player):
            problems.append(f"{where} の与えたプレイヤー {lock.source_player!r} が、{'使えなくなるプレイヤー自身' if trainer_origin else '使えなくなるプレイヤーの相手'}ではない")
            continue
        if type(lock.created_turn) is not int:
            problems.append(f"{where} の与えた番 {lock.created_turn!r} が正しくない")
            continue
        # v0.57: トレーナーの禁止は、与えた番より後の使えなくなるプレイヤーの最初の番に消える（自分の番に使えば + 2。錯乱ジムで相手の番にかわりに使えば + 1。
        # ``effects.self_lock_expiry``）。ワザの禁止は次の相手の番（+ 1）
        borrowed = trainer_origin and state.first_player in PLAYERS and turn_owner(state, lock.created_turn) != lock.player
        span = (1 if borrowed else SELF_TRAINER_LOCK_TURNS) if trainer_origin else 1
        if lock.expires_turn != lock.created_turn + span:
            problems.append(f"{where} の消える番 {lock.expires_turn!r} が、与えた番 {lock.created_turn!r} + {span} ではない")
            continue
        if not lock.created_turn <= state.turn_number <= lock.expires_turn:
            problems.append(f"{where} が、与えた番 {lock.created_turn}〜消える番 {lock.expires_turn} の外の今の番 {state.turn_number} に残っている")
        if state.first_player in PLAYERS and turn_owner(state, lock.created_turn) != lock.source_player and not borrowed:
            problems.append(f"{where} を与えた番 {lock.created_turn} が、与えたプレイヤー {lock.source_player} の番ではない")
        if lock.source_card not in state.cards:
            problems.append(f"{where} のワザを使ったカード {lock.source_card!r} が対戦のカードではない")
        if trainer_origin:
            entry = state.effects.trainer_entry(lock.effect)
            if entry is None or not getattr(entry.effect, "tails_self_lock", False):
                problems.append(f"{where} を与えたトレーナー {lock.effect!r} の登録された実装が、使ったプレイヤーにトレーナーの使用を禁止する実装ではない")
            elif lock.source_card not in state.cards or state.cards[lock.source_card].card_id != lock.effect \
                    or state.cards[lock.source_card].owner != (1 - lock.player if borrowed else lock.player):  # v0.57: 借りて使ったカードの持ち主は相手
                problems.append(f"{where} の使ったトレーナーのカード {lock.source_card!r} が、使ったプレイヤーのそのカードではない")
        else:
            card_id, _, index = str(lock.effect).partition("#")
            entry = state.effects.attack_entry(card_id, int(index)) if index.isdigit() else None
            if entry is None or getattr(entry.effect, "lock_terms", None) is None:
                problems.append(f"{where} を与えたワザ {lock.effect!r} の登録された実装が、トレーナーの使用を禁止する実装ではない")
            elif getattr(entry.effect, "hand_only", False) != (lock.origin == ATTACK_HAND_TRAINER_LOCK):
                # v0.86: 手札から出して使うことだけを止める禁止（こうしゅうは。わるいモココ）と、ワザの実装の範囲が合う
                problems.append(f"{where} の出どころ {lock.origin!r} が、与えたワザ {lock.effect!r} の登録された実装の範囲と合わない")
        keys.append((lock.player, lock.expires_turn, lock.origin))
    if len(set(keys)) != len(keys):
        problems.append(f"同じプレイヤー・同じ消える番・同じ出どころのトレーナーの使用の禁止が重なっている {keys}")
    added: dict[tuple, dict] = {}
    removed: set[tuple] = set()
    starts = 0
    for event in reversed(state.log):
        kind = event["kind"]
        if kind == "turn_start":
            starts += 1
            if starts >= 3:  # v0.56: トレーナーの効果の禁止は与えた番 + 2 まで残るので、今の番と前の 2 つの番のログを見る（v0.55 までは前の番まで）
                break
        elif kind == "trainer_lock_added":
            added.setdefault((event.get("player"), event.get("expires_turn"), event.get("origin", "attack")), event)
        elif kind == "trainer_lock_removed":
            removed.add((event.get("player"), event.get("expires_turn"), event.get("origin", "attack")))
    live = {key for key in added if key not in removed and key[1] >= state.turn_number}
    if live != set(keys):
        problems.append(f"期限のあるトレーナーの使用の禁止 {sorted(keys)} が、ログで与えてまだ消していない禁止 {sorted(live)} と違う")
    for lock in locks:
        event = added.get((lock.player, lock.expires_turn, lock.origin)) if isinstance(lock, TrainerUseLock) else None
        if event is not None and (event.get("effect"), event.get("source_player"), event.get("source_card")) != (lock.effect, lock.source_player, lock.source_card):
            problems.append(f"プレイヤー {lock.player} のトレーナーの使用の禁止 {lock!r} が、与えたログ {event!r} と合わない")
    return problems


def _hand_trainer_lock_problems(state: GameState, lock: TrainerUseLock, where: str) -> list[str]:
    """v0.80: 「次の相手の番が終わるまで、あなたは手札から「トレーナーカード」を出して使うことができない」（ウツギはかせ・タイムカプセル・ポケモンギア。出どころ
    ``HAND_TRAINER_LOCK``）の整合: 使ったプレイヤー自身に与え（``source_player`` = ``player``）、消える番は与えた番より後の相手の最初の番（``hand_lock_expiry``）。今の番は与えた番〜
    消える番。与えたトレーナーの登録された実装が、この禁止を与える実装（``HAND_LOCK_TRAINERS`` の型）。使ったカードはそのカード id のカード（サイキックコントロールで使ったときは
    相手のカード）。"""
    problems = []
    if lock.player not in PLAYERS or lock.source_player != lock.player or type(lock.created_turn) is not int:
        return [f"{where} の与えたプレイヤー・与えた番が正しくない（使ったプレイヤー自身に与える）"]
    if state.first_player in PLAYERS and lock.expires_turn != hand_lock_expiry(state, lock.player, lock.created_turn):
        problems.append(f"{where} の消える番 {lock.expires_turn!r} が、与えた番 {lock.created_turn} より後の相手の最初の番ではない")
    if not lock.created_turn <= state.turn_number <= lock.expires_turn:
        problems.append(f"{where} が、与えた番 {lock.created_turn}〜消える番 {lock.expires_turn} の外の今の番 {state.turn_number} に残っている")
    entry = state.effects.trainer_entry(lock.effect)
    if entry is None or not isinstance(entry.effect, HAND_LOCK_TRAINERS):
        problems.append(f"{where} を与えたトレーナー {lock.effect!r} の登録された実装が、手札から使うことを禁止する実装ではない")
    card = state.cards.get(lock.source_card)
    if card is None or card.card_id != lock.effect:
        problems.append(f"{where} の使ったトレーナーのカード {lock.source_card!r} が、そのカード id のカードではない")
    return problems


def _trainer_effect_problems(state: GameState) -> list[str]:
    """v0.56（形式 16）: プレイヤーに与えた期限のあるトレーナーの効果（``GameState.trainer_effects``。カスミ・キョウ・見えない壁）の整合。

    - 型は ``TrainerTurnEffect``。種類は ``TRAINER_TURN_EFFECT_KINDS``。使ったプレイヤー ``player`` の番に与え（与えた番は ``player`` の番）、今の番は与えた番〜消える番
    - 登録: ``card_id`` のトレーナーの実装の ``turn_effect_terms()`` の種類と期限（消える番 − 与えた番）が状態の記録と同じ。``source_card`` はそのカード id の、使った
      プレイヤーのカード（トレーナーを使い終えたあとは持ち主のトラッシュにある。効果は場のカードに写していない）
    - ログとの対応: 今の番と前の番のログで、与えた（``trainer_effect_added``）がまだ消していない（``trainer_effect_removed`` がない）効果と、状態の効果が同じ。エンジンは
      効果をログから決めない"""
    records = state.trainer_effects
    if type(records) is not tuple:
        return [f"期限のあるトレーナーの効果 {records!r} がタプルではない"]
    problems: list[str] = []
    keys = []
    for record in records:
        if not isinstance(record, TrainerTurnEffect):
            problems.append(f"期限のあるトレーナーの効果 {record!r} の型が TrainerTurnEffect ではない")
            continue
        where = f"プレイヤー {record.player!r} のトレーナーの効果（{record.card_id}・{record.kind}）"
        if record.kind not in TRAINER_TURN_EFFECT_KINDS or record.player not in PLAYERS or type(record.created_turn) is not int:
            problems.append(f"{where} の種類・プレイヤー・与えた番が正しくない")
            continue
        if record.kind == ATTACK_POWER_SUPPRESSION:
            # v0.91: ワザを使っているあいだの特殊能力の抑止（ポリゴンの「オールクリア」）。登録はワザ（``card_id``・``attack_index``）の ``suppresses_powers_while_used``。与えた番に
            # 消え、ワザの処理の外（ワザの途中の決定を待つあいだ以外）には残らない（``flow.end_attack_power_suppression``）
            attack = state.effects.attack_entry(record.card_id, record.attack_index) if type(record.attack_index) is int else None
            if attack is None or not getattr(attack.effect, "suppresses_powers_while_used", False):
                problems.append(f"{where} のワザ {record.attack_index!r} が、ワザを使っているあいだ特殊能力を止めるワザではない")
            if record.pokemon_id is not None:
                problems.append(f"{where} にポケモンの番号 {record.pokemon_id!r} がある（退化スプレーHYPER の禁止だけ）")
            if record.created_turn != state.turn_number or record.expires_turn != state.turn_number:
                problems.append(f"{where} を与えた番 {record.created_turn}・消える番 {record.expires_turn} が今の番 {state.turn_number} ではない")
            if state.first_player in PLAYERS and turn_owner(state, record.created_turn) != record.player:
                problems.append(f"{where} を与えた番 {record.created_turn} が、ワザを使ったプレイヤーの番ではない")
            if state.decision is None or state.decision.resume != "attack":
                problems.append(f"{where} が、ワザの処理の外に残っている（ワザの処理のあとに消す）")
            card = state.cards.get(record.source_card)
            if card is None or card.owner != record.player:
                problems.append(f"{where} のワザを使ったポケモンのカード {record.source_card!r} が、ワザを使ったプレイヤーのカードではない")
            keys.append((record.player, record.source_card, record.expires_turn))
            continue
        if record.kind == ATTACK_FIELD_POWER_SUPPRESSION:
            # v0.92: ワザで与えた効果（ナツメのゲンガーの「やみのはどう」）。登録はワザ（``card_id``・``attack_index``）の ``field_effect_terms()``。``source_card``・``pokemon_id`` は
            # 実際にワザを使ったポケモンのいちばん上のカードと場の番号（与えたあとに場をはなれても消えないので、今の場所は確かめない）。与えた番〜消える番（与えた番 + 1）
            attack = state.effects.attack_entry(record.card_id, record.attack_index) if type(record.attack_index) is int else None
            terms = attack.effect.field_effect_terms() if attack is not None and hasattr(attack.effect, "field_effect_terms") else None
            if terms is None or terms[0] != record.kind or record.expires_turn != record.created_turn + terms[1]:
                problems.append(f"{where} のワザ {record.attack_index!r}・消える番 {record.expires_turn} が、登録の実装 {terms!r} と合わない")
            if type(record.pokemon_id) is not int:
                problems.append(f"{where} にワザを使ったポケモンの番号 {record.pokemon_id!r} がない")
            if state.first_player in PLAYERS and turn_owner(state, record.created_turn) != record.player:
                problems.append(f"{where} を与えた番 {record.created_turn} が、ワザを使ったプレイヤーの番ではない")
            card = state.cards.get(record.source_card)
            if card is None or card.owner != record.player:
                problems.append(f"{where} のワザを使ったポケモンのカード {record.source_card!r} が、ワザを使ったプレイヤーのカードではない")
            if not record.created_turn <= state.turn_number <= record.expires_turn:
                problems.append(f"{where} が、与えた番 {record.created_turn}〜消える番 {record.expires_turn} の外の今の番 {state.turn_number} に残っている")
            keys.append((record.player, record.source_card, record.expires_turn))
            continue
        if record.kind == OPPONENT_POWER_SUPPRESSION:
            # v0.87: ワザで与えた効果（ドガースの「ふしぎなガス」）。登録はワザ（``card_id``・``attack_index``）の ``field_effect_terms()``。``source_card`` はワザを使った
            # ポケモンのいちばん上のカード（ワザを使ったプレイヤーのカード。相手のワザとして使ったときはワザを印刷したカードと違う）
            attack = state.effects.attack_entry(record.card_id, record.attack_index) if type(record.attack_index) is int else None
            terms = attack.effect.field_effect_terms() if attack is not None and hasattr(attack.effect, "field_effect_terms") else None
            if terms is None or terms[0] != record.kind or record.expires_turn != record.created_turn + terms[1]:
                problems.append(f"{where} のワザ {record.attack_index!r}・消える番 {record.expires_turn} が、登録の実装 {terms!r} と合わない")
            if record.pokemon_id is not None:
                problems.append(f"{where} にポケモンの番号 {record.pokemon_id!r} がある（退化スプレーHYPER の禁止だけ）")
            if state.first_player in PLAYERS and turn_owner(state, record.created_turn) != record.player:
                problems.append(f"{where} を与えた番 {record.created_turn} が、ワザを使ったプレイヤーの番ではない")
            card = state.cards.get(record.source_card)
            if card is None or card.owner != record.player:
                problems.append(f"{where} のワザを使ったポケモンのカード {record.source_card!r} が、ワザを使ったプレイヤーのカードではない")
            if not record.created_turn <= state.turn_number <= record.expires_turn:
                problems.append(f"{where} が、与えた番 {record.created_turn}〜消える番 {record.expires_turn} の外の今の番 {state.turn_number} に残っている")
            keys.append((record.player, record.source_card, record.expires_turn))
            continue
        if record.attack_index is not None:
            problems.append(f"{where} にワザの位置 {record.attack_index!r} がある（ワザで与えた効果だけ）")
        entry = state.effects.trainer_entry(record.card_id)
        terms = entry.effect.turn_effect_terms() if entry is not None else None
        if terms is None or terms[0] != record.kind or record.expires_turn != record.created_turn + terms[1]:
            problems.append(f"{where} の種類・消える番 {record.expires_turn} が、登録の実装 {terms!r} と合わない")
        if not record.created_turn <= state.turn_number <= record.expires_turn:
            problems.append(f"{where} が、与えた番 {record.created_turn}〜消える番 {record.expires_turn} の外の今の番 {state.turn_number} に残っている")
        if record.kind == EVOLUTION_BAN:
            # v0.80: 退化スプレーHYPER の「同じ番に進化させることはできない」（退化させたポケモンの番号。使った番だけ。錯乱ジム・サイキックコントロールで使ったときは、
            # 番の持ち主・カードの持ち主が使ったプレイヤーでないことがある）
            card = state.cards.get(record.source_card)
            if type(record.pokemon_id) is not int or card is None or card.card_id != record.card_id:
                problems.append(f"{where} の退化させたポケモン {record.pokemon_id!r}・使ったカード {record.source_card!r} が正しくない")
            keys.append((record.player, record.source_card, record.expires_turn))
            continue
        if record.pokemon_id is not None:
            problems.append(f"{where} にポケモンの番号 {record.pokemon_id!r} がある（退化スプレーHYPER の禁止だけ）")
        if state.first_player in PLAYERS and turn_owner(state, record.created_turn) != record.player:
            problems.append(f"{where} を与えた番 {record.created_turn} が、使ったプレイヤーの番ではない")
        card = state.cards.get(record.source_card)
        if card is None or card.card_id != record.card_id or card.owner != record.player:
            problems.append(f"{where} の使ったトレーナーのカード {record.source_card!r} が、使ったプレイヤーのそのカードではない")
        keys.append((record.player, record.source_card, record.expires_turn))
    if len(set(keys)) != len(keys):
        problems.append(f"同じカードで与えた期限のあるトレーナーの効果が重なっている {keys}")
    added: dict[tuple, dict] = {}
    removed: set[tuple] = set()
    starts = 0
    for event in reversed(state.log):
        kind = event["kind"]
        if kind == "turn_start":
            starts += 1
            if starts >= 2:
                break
        elif kind == "trainer_effect_added":
            added.setdefault((event.get("player"), event.get("trainer_card"), event.get("expires_turn")), event)
        elif kind == "trainer_effect_removed":
            removed.add((event.get("player"), event.get("trainer_card"), event.get("expires_turn")))
    live = {key for key in added if key not in removed and key[2] >= state.turn_number}
    if live != set(keys):
        problems.append(f"期限のあるトレーナーの効果 {sorted(keys)} が、ログで与えてまだ消していない効果 {sorted(live)} と違う")
    for record in records:
        event = added.get((record.player, record.source_card, record.expires_turn)) if isinstance(record, TrainerTurnEffect) else None
        if event is not None and (event.get("effect_kind"), event.get("card_id")) != (record.kind, record.card_id):
            problems.append(f"プレイヤー {record.player} のトレーナーの効果 {record!r} が、与えたログ {event!r} と合わない")
        elif event is not None and record.kind == ATTACK_FIELD_POWER_SUPPRESSION and (event.get("pokemon_id"), event.get("attack_index")) != (record.pokemon_id, record.attack_index):
            problems.append(f"プレイヤー {record.player} のワザの効果 {record!r} の実際に使ったポケモン・ワザの位置が、与えたログ {event!r} と合わない")  # v0.92
    return problems


def _once_attack_problems(state: GameState, player: int, pokemon: PokemonInPlay) -> list[str]:
    """v0.44: 「このワザは、このカードが場に出てから、1回しか使えない」ワザを使った記録（``PokemonInPlay.attacks_used_once``）の整合。

    - (カードの uid, ワザの位置) の重ならない並びのタプル。カードはこのポケモンを作るカード（重なったカードを含む。進化したあとも、進化前のカードの記録は残る
      が、そのワザはもう使えない）で、その位置のワザの登録が ``once_after_entering_play``
    - 対戦準備の段階にはない（ワザは使えない）。記録のもとは状態で、ログの ``once_attack_recorded`` は記録（ここでは、そのポケモンの番号・カードのワザの位置の
      ログがあることだけを確かめる）
    """
    used = pokemon.attacks_used_once
    if not isinstance(used, tuple):
        return [f"ポケモン {pokemon.pokemon_id} の 1 回だけのワザの記録 {used!r} がタプルではない"]
    if not used:
        return []
    where = f"ポケモン {pokemon.pokemon_id} の 1 回だけのワザの記録 {used!r}"
    if state.phase in SETUP_PHASES:
        return [f"{where} が対戦準備の段階にある"]
    if len(set(used)) != len(used):
        return [f"{where} が重なっている"]
    problems = []
    cards = pokemon.cards()
    for entry in used:
        if not (isinstance(entry, tuple) and len(entry) == 2 and entry[0] in cards and type(entry[1]) is int):
            problems.append(f"{where} の {entry!r} が、このポケモンのカードのワザではない")
            continue
        definition = state.card_def(entry[0])
        if not 0 <= entry[1] < len(definition.attacks):
            problems.append(f"{where} の {entry!r} のワザの位置が正しくない")
            continue
        effect = state.effects.attack_effect(definition.id, definition.attacks[entry[1]], definition.attacks)
        if effect is None or not effect.once_after_entering_play:
            problems.append(f"{where} の {entry!r} が、場に出てから1回しか使えないワザではない")
        elif not any(e["kind"] == "once_attack_recorded" and e.get("pokemon_id") == pokemon.pokemon_id and e.get("pokemon") == entry[0]
                     and e.get("attack_index") == entry[1] for e in state.log):
            problems.append(f"{where} の {entry!r} に対応するログ once_attack_recorded がない")
    return problems


def _evolution_permission_problems(state: GameState, player: int, pokemon: PokemonInPlay) -> list[str]:
    """v0.44: トレーナー「サカキ」の進化の許可（``PokemonInPlay.evolution_permission_turn``）の整合。

    - なければ None。あれば今の番の番号で、持ち主が番のプレイヤー（「今の番」。自分の場のポケモンを選ぶ）。番の終わりに消すので、対戦準備の段階・番の終わりの
      あと（ログ ``turn_end``）には残らない
    - 今の番のログに、このポケモンの番号の ``evolution_permission`` がある（選んだあとに場をはなれて、もう一度場に出たポケモンには、新しい番号なので残らない）
    - いちばん上のカードが、許可を与えたトレーナー（ログの ``trainer``）の登録の実装の「(``owner``)のポケモン」（進化しても、進化先は「サカキの…から進化」の
      カード）。カードの名前・id を engine.py に書かない
    """
    turn = pokemon.evolution_permission_turn
    if turn is None:
        return []
    where = f"ポケモン {pokemon.pokemon_id} の「サカキ」の進化の許可 {turn!r}"
    if state.phase in SETUP_PHASES or type(turn) is not int:
        return [f"{where} が正しくない（{state.phase.value}）"]
    if turn != state.turn_number or player != state.current_player:
        return [f"{where} が今の番（{state.turn_number} 番、プレイヤー {state.current_player!r}）の持ち主の許可ではない（番の終わりに消す）"]
    recent = _events_since_turn_start(state)
    if any(event["kind"] == "turn_end" for event in recent):
        return [f"{where} が番の終わりのあとに残っている"]
    granted = next((event for event in recent if event["kind"] == "evolution_permission" and event.get("pokemon_id") == pokemon.pokemon_id), None)
    if granted is None or granted.get("trainer") not in state.cards:
        return [f"{where} に対応する、今の番のログ evolution_permission がない"]
    entry = state.effects.trainer_entry(state.card_def(granted["trainer"]).id)
    owner = None if entry is None else getattr(entry.effect, "owner", None)
    # v0.49: 選んだときの姿のカード（ログの form_card。［へんしん］で写したカード）の名前でもよい（そのあと相手の対戦ポケモンが入れかわると今の姿は変わる）
    named = state.card_def(granted["form_card"]).name_ja if granted.get("form_card") in state.cards else state.card_def(pokemon.card).name_ja
    if owner is None or not named.startswith(f"{owner}の"):
        return [f"{where} のポケモンが、許可を与えたトレーナー {granted['trainer']} の選ぶ「{owner}のポケモン」ではない"]
    return []


def _retreat_failure_problems(state: GameState, player: int, pokemon: PokemonInPlay) -> list[str]:
    """こんらん状態で「にげる」に失敗した記録（``PokemonInPlay.retreat_failed_turn``。v0.3c。p.311）の整合。

    v0.3d で、記録が今の番のログの ``retreat_failed``（同じ ``pokemon_id``）と対応することも確かめる（失敗していない
    ポケモンに記録が付いていない。特殊状態を消す処理（ポケモンいれかえなど）が記録を書きかえない前提の確認）。
    v0.4a で、その ``retreat_failed`` が、同じポケモンの進化（ログ ``evolve``）より後であることも確かめる（進化で記録を消す）。
    """
    failed = pokemon.retreat_failed_turn
    if failed is None:
        return []
    where = f"ポケモン {pokemon.pokemon_id} の「にげる」に失敗した番 {failed!r}"
    if state.phase in SETUP_PHASES or type(failed) is not int:
        return [f"{where} が正しくない（{state.phase.value}）"]
    if failed != state.turn_number or player != state.current_player:
        return [f"{where} が今の番（{state.turn_number} 番、プレイヤー {state.current_player!r}）の持ち主の記録ではない（番の終わりに消す）"]
    recent = _events_since_turn_start(state)
    if any(event["kind"] == "turn_end" for event in recent):
        return [f"{where} が番の終わりのあとに残っている"]
    for event in recent:  # 新しい順
        if event.get("pokemon_id") != pokemon.pokemon_id:
            continue
        if event["kind"] == "retreat_failed":
            return []
        if event["kind"] == "evolve":
            # 進化したポケモンは別のポケモンなので、進化の前の失敗の記録は消している（v0.4a。p.310）
            return [f"{where} が、進化（ログ evolve）の前の失敗の記録のまま残っている"]
    return [f"{where} に対応する、今の番の「にげる」の失敗（ログ retreat_failed）がない"]


def _counter_knocked_out_attacker_awaiting(state: GameState, player: int, pokemon: PokemonInPlay) -> bool:
    """v0.10: ワザの途中の決定（相手が答える「ふきとばし」の入れ替えなど）を待つ間だけ、そのワザを使ったポケモンは、相手の「はんげき」の
    ダメージで HP 以上になっていても場に残る（きぜつの処理はワザの要素をすべて処理したあと。p.309・p.89。docs/counterattack-v0.10.md
    の C16・C30）。ほかのポケモン・ほかの段階・決定のないときは、これまでどおり HP 以上のダメージで場に残ることを許さない。

    決定の続きの情報（``context`` の ``"use"``）がこのポケモンを指し、今の番のログで、最後のワザの宣言（``attack``）のあとに、このポケモンを
    HP 以上にした「はんげき」（``counterattack`` の ``knocked_out``）があることを確かめる（印や一覧を状態に加えない）。

    v0.12: 相手の R団のファイヤーの「ほのおのかべ」のダメージ（ログ ``damage`` の ``retaliation``。このポケモンの番号で、今のダメージ）で
    HP 以上になった場合も同じ（「ほのおのかべ」のダメージもダメージの処理のあと、効果の前。p.89 の「ふきとばし」の例。W23）。"""
    d = state.decision
    if state.phase is not Phase.DECISION or d is None or d.resume != "attack":
        return False
    use = d.context_value("use")
    if not isinstance(use, tuple) or len(use) < 2 or (use[0], use[1]) != (player, pokemon.pokemon_id):
        return False
    for event in _events_since_turn_start(state):  # 新しい順
        if event["kind"] == "attack":
            return False
        if event["kind"] == "counterattack" and event["attacker_pokemon_id"] == pokemon.pokemon_id and event["knocked_out"]:
            return True
        if (event["kind"] == "damage" and event.get("retaliation") and event.get("pokemon_id") == pokemon.pokemon_id
                and event.get("total_damage") == pokemon.damage):
            return True
        if (event["kind"] == "tool_damage_counters" and event.get("target_pokemon_id") == pokemon.pokemon_id
                and event.get("total_damage") == pokemon.damage):
            return True  # v0.81: 相手のはんげきのツメのダメージカウンター（「ダメージを受けたとき」の効果の窓。効果の前）
    return False


def _attack_damage_awaiting(state: GameState, player: int, pokemon: PokemonInPlay) -> bool:
    """v0.31: ワザの途中の決定（再開先 ``"attack"``）を待つ間だけ、同じワザのダメージの要素で HP 以上になったポケモンは場に残る（きぜつの処理は
    ワザの要素をすべて処理したあと。p.309）。v0.30 までの対応カードでは、ダメージのあとに決定を出すワザ（ふきとばし）は、相手がきぜつすれば
    決定を出さなかったので起こらなかった。v0.31 のワザ（れんぞくファイヤーボール・ひばしら・エナジーボムなど）は、相手がきぜつしても自分の
    エネルギーをトラッシュする・つけかえるので、その決定を待つ間に起こる。

    今の番のログで、最後のワザの宣言（``attack``）のあとに、このポケモン（持ち主・いちばん上のカード）が受けたワザのダメージ（``damage``）が
    あり、その ``total_damage`` が今のダメージと同じことを確かめる（印や一覧を状態に加えない）。ほかの段階・決定のないときは許さない。"""
    d = state.decision
    if state.phase is not Phase.DECISION or d is None or d.resume != "attack":
        return False
    for event in _events_since_turn_start(state):  # 新しい順
        if event["kind"] == "attack":
            return False
        if (event["kind"] in ("damage", "bench_guard") and event.get("player") == player and event.get("pokemon") == pokemon.card
                and event.get("total_damage") == pokemon.damage):
            return True  # v0.65: ［ベンチガード］でかわりに受けたダメージ（ログ bench_guard）も同じワザのダメージの要素
        if (event["kind"] == "shock_blast_damage" and event.get("target_player") == player and event.get("target_pokemon_id") == pokemon.pokemon_id
                and event.get("total_damage") == pokemon.damage):
            # v0.87: ［ショックボム］の特殊能力のダメージ（そのワザのダメージの要素のあとの窓。両方の対戦ポケモン。持つポケモン自身も受ける）で HP 以上になった
            return True
    return False


def _ko_prevention_awaiting(state: GameState, player: int, pokemon: PokemonInPlay) -> bool:
    """v0.11: 「こんじょう」を使うかの決定（``KO_PREVENTION``。再開先 ``"knock_out"``）を待つ間だけ、HP 以上のダメージのポケモンが場に
    残る（きぜつの判定から、実際のきぜつの処理までのあいだ。docs/ko-prevention-v0.11.md）。許すのは、

    - 決定の対象のポケモン（決定するプレイヤーの、選べるもののポケモン。形・ログは ``_ko_prevention_decision_problems`` が確かめる）と、
    - 同じワザで HP 以上になったワザを使ったポケモン（決定の ``"attack"`` が指すポケモンで、今の番の最後のワザの宣言のあとの、自分への
      ダメージ（``damage`` の ``target`` が ``self``）か「はんげき」（``counterattack``）で、今のダメージになっている）。

    ほかのポケモン・ほかの段階・決定のないときは、これまでどおり許さない。"""
    d = state.decision
    if state.phase is not Phase.DECISION or d is None or d.resume != "knock_out":
        return False
    if player == d.player and pokemon.pokemon_id in d.options:
        return True
    if d.kind in (KNOCK_OUT_POWER, EXP_ALL_ENERGY):
        return True  # v0.61: ［ファイナルビーム］（v0.81: 学習装置も）の決定を待つ間は、同じワザで HP 以上になったほかのポケモンも残る（答えのあとのきぜつの処理でまとめて処理する）
    attack = d.context_value("attack")
    if not isinstance(attack, tuple) or len(attack) != 4 or (attack[0], attack[1]) != (player, pokemon.pokemon_id):
        return False
    for event in _events_since_turn_start(state):  # 新しい順
        if event["kind"] == "attack":
            return False
        if (event["kind"] == "damage" and event.get("target") == "self" and event.get("pokemon_id") == pokemon.pokemon_id) or (
            event["kind"] == "counterattack" and event.get("attacker_pokemon_id") == pokemon.pokemon_id
        ) or (event["kind"] == "tool_damage_counters" and event.get("target_pokemon_id") == pokemon.pokemon_id) or (  # v0.81: はんげきのツメ
            event["kind"] == "shock_blast_damage" and event.get("target_pokemon_id") == pokemon.pokemon_id):  # v0.87: ［ショックボム］
            return event.get("total_damage") == pokemon.damage
    return False


def _knock_out_power_decision_problems(state: GameState, d) -> list[str]:
    """［ファイナルビーム］を使うかの決定（v0.61。``KNOCK_OUT_POWER``・再開先 ``"knock_out"``）の整合性: 選ぶ数（0〜1）・選べるもの（ポケモン 1 匹）、対象が決定するプレイヤーの
    HP 以上の場のポケモンで、今持つ特殊能力の ``"power"`` が［ファイナルビーム］（``BeamOnKnockOut``）、ねむり・マヒ・こんらんでなく、力が消えていない・使うことができない状態で
    ない。``"source"``（「きぜつ」させたポケモン）が相手の場にいる。今の番にワザの宣言がある。"""
    problems = []
    if d.resume != "knock_out":
        return [f"決定 {d.kind} の再開先 {d.resume!r} が合わない（knock_out_power・knock_out の組）"]
    if (d.min_choices, d.max_choices) != (0, 1) or len(d.options) != 1:
        return [f"［ファイナルビーム］の決定の選ぶ数 {d.min_choices}〜{d.max_choices}・選べるもの {d.options} が正しくない（0〜1 個・1 匹）"]
    power = d.context_value("power")
    source = d.context_value("source")
    found = state.find_pokemon(d.options[0])
    if found is None or found[0] != d.player:
        return [f"［ファイナルビーム］の決定の対象 {d.options} が、決定するプレイヤー {d.player} の場のポケモンではない"]
    pokemon = found[1]
    slot = next((slot for slot in powers_of(state, pokemon) if isinstance(power, tuple) and slot.key == PowerKey(*power)), None)
    if slot is None or not isinstance(slot.effect, BeamOnKnockOut):
        return [f"［ファイナルビーム］の決定の特殊能力 {power!r} が、ポケモン {pokemon.pokemon_id} の今持つ［ファイナルビーム］ではない"]
    # v0.100: ワザの効果で「きぜつ」するポケモン（続きの情報の ``effect_ko``。ダメージによらない）は、HP 以上のダメージを受けていなくてよい
    effect_ko = {entry[0] for entry in d.context_value("effect_ko", ())}
    if pokemon.damage < max_hp(state, pokemon) and pokemon.pokemon_id not in effect_ko:
        problems.append(f"［ファイナルビーム］の決定の対象のポケモン {pokemon.pokemon_id} が HP 以上のダメージを受けていない")
    if not slot.effect.is_able(pokemon):
        problems.append(f"［ファイナルビーム］の決定の対象のポケモン {pokemon.pokemon_id} がねむり・マヒ・こんらん（使えない）")
    if power_suppressed(state, slot.power, pokemon) or powers_use_prevented(state, pokemon) is not None:
        problems.append(f"［ファイナルビーム］の決定の対象のポケモン {pokemon.pokemon_id} の特殊能力が消えている・使うことができない")
    located = state.find_pokemon(source) if isinstance(source, int) else None
    if located is None or located[0] == d.player:
        problems.append(f"［ファイナルビーム］の決定の「きぜつ」させたポケモン {source!r} が、相手の場にいない")
    if not any(event["kind"] == "attack" for event in _events_since_turn_start(state)):
        problems.append("［ファイナルビーム］の決定の前に、今の番のワザの宣言がない")
    return problems


def _exp_all_decision_problems(state: GameState, d) -> list[str]:
    """学習装置の決定（v0.81。``EXP_ALL_ENERGY``・再開先 ``"knock_out"``）の整合性: 選ぶ数（0〜1）、決めるのは番でないプレイヤー、``"source"`` がそのプレイヤーの対戦ポケモンで HP 以上、
    ``"holder"`` がそのプレイヤーの別の場のポケモンで、``"tool"`` の学習装置がついている、選べるものが対戦ポケモンの選べるエネルギーカード、今の番にワザの宣言がある。"""
    from .effects import ExpAll
    from .resolution.kernel import exp_all_options

    if d.resume != "knock_out" or (d.min_choices, d.max_choices) != (0, 1):
        return [f"学習装置の決定の再開先 {d.resume!r}・選ぶ数 {d.min_choices}〜{d.max_choices} が正しくない（knock_out・0〜1 枚）"]
    if d.player != 1 - state.current_player:
        return [f"学習装置の決定を決めるのがプレイヤー {d.player}（番でないプレイヤー {1 - state.current_player} のはず）"]
    source = state.find_pokemon(d.context_value("source"))
    holder = state.find_pokemon(d.context_value("holder"))
    if source is None or source[0] != d.player or state.players[d.player].active is not source[1] or source[1].damage < max_hp(state, source[1]):
        return [f"学習装置の決定の対戦ポケモン {d.context_value('source')!r} が、決めるプレイヤーの HP 以上のバトル場のポケモンではない"]
    if holder is None or holder[0] != d.player or holder[1] is source[1]:
        return [f"学習装置の決定の学習装置をつけたポケモン {d.context_value('holder')!r} が、決めるプレイヤーの別の場のポケモンではない"]
    tool = tool_effect_of(state, holder[1], ExpAll)
    problems = []
    if tool is None or tool[0].card != d.context_value("tool"):
        problems.append(f"学習装置の決定の学習装置 {d.context_value('tool')!r} が、ポケモン {holder[1].pokemon_id} についていない")
    if tuple(d.options) != exp_all_options(state, source[1]):
        problems.append(f"学習装置の決定の選べるもの {d.options} が、対戦ポケモンのエネルギーカード {exp_all_options(state, source[1])} と合わない")
    if not any(event["kind"] == "attack" for event in _events_since_turn_start(state)):
        problems.append("学習装置の決定の前に、今の番のワザの宣言がない")
    return problems


def _ko_prevention_decision_problems(state: GameState, d) -> list[str]:
    """「こんじょう」を使うかの決定（v0.11。``KO_PREVENTION``・再開先 ``"knock_out"``）の整合性。

    - 種類と再開先の組、選ぶ数（0〜1）、選べるもの（ポケモン 1 匹）、決定するのはワザを使われた側（番でないプレイヤー）。v0.12 から、
      番のプレイヤーのワザを使ったポケモンが、相手の「ほのおのかべ」のダメージ（ログ ``damage`` の ``retaliation``）で HP 以上になった
      場合は、番のプレイヤーが決定する（対象はワザを使ったポケモン）。
    - ``"attack"``（ワザ）: 番のプレイヤーのバトル場のポケモンで、いちばん上のカードがそのカード。今の番にそのワザのログ ``attack`` が
      ちょうど 1 回。
    - 対象のポケモン: 決定するプレイヤーの場にいて、いちばん上のカードの ``"power"`` の位置に「こんじょう」（``PreventKnockOutOnHeads``）が
      登録され、HP 以上のダメージ、今ねむり・マヒ・こんらんでない（ダメージを受けたあとにワザの効果で特殊状態を変えるワザは、G37 で
      止めているので、今の特殊状態はダメージを受けたときと同じ）、かがくへんかガスに消されていない（G31）。
    - ログ: 今の番の最後のワザの宣言のあとに、対象のポケモンがワザのダメージを受けて今のダメージになった ``damage`` があり、そのあとに
      きぜつ・「こんじょう」の宣言や結果がない（同じきぜつの判定で 2 度決めさせない。G14）。
    """
    problems = []
    if d.kind != KO_PREVENTION or d.resume != "knock_out":
        return [f"決定 {d.kind} の再開先 {d.resume!r} が合わない（「こんじょう」の決定は ko_prevention・knock_out の組）"]
    if (d.min_choices, d.max_choices) != (0, 1) or len(d.options) != 1:
        problems.append(f"「こんじょう」の決定の選ぶ数 {d.min_choices}〜{d.max_choices}・選べるもの {d.options} が正しくない（0〜1 個・1 匹）")
    attack = d.context_value("attack")
    by_attacker = d.player == state.current_player  # v0.12: 「ほのおのかべ」のダメージで HP 以上になったワザを使ったポケモン
    if d.player not in PLAYERS or (by_attacker and not (isinstance(attack, tuple) and len(attack) == 4 and d.options == (attack[1],))):
        problems.append(
            f"「こんじょう」の決定をするのがプレイヤー {d.player}（ワザを使われた側 {1 - state.current_player!r}、または「ほのおのかべ」を"
            "受けたワザを使ったポケモンの持ち主のはず）"
        )
    power = d.context_value("power")
    if not (isinstance(attack, tuple) and len(attack) == 4 and isinstance(power, tuple) and len(power) == 2):
        return problems + [f"「こんじょう」の決定の続きの情報 {attack!r}・{power!r} が正しくない"]
    player, pokemon_id, card_id, attack_index = attack
    found = state.find_pokemon(pokemon_id)
    if player != state.current_player or found is None or found[0] != player or state.players[player].active is not found[1]:
        return problems + [f"「こんじょう」の決定のワザ {attack!r} が、番のプレイヤーのバトル場のポケモンのワザではない"]
    attacker = found[1]
    events = _events_since_turn_start(state)  # 新しい順
    attacks = [event for event in events if event["kind"] == "attack" and event.get("player") == player]
    if len(attacks) != 1 or attacks[0].get("pokemon") != attacker.card or attacks[0].get("attack_index") != attack_index:
        problems.append(f"「こんじょう」の決定のワザ {attack!r} に対応する、今の番のワザのログ attack がない（{len(attacks)} 回）")
    # v0.49: ワザのカード id は、ワザを印刷したカード（ログ attack の ``card_id``。ワザの出どころがいちばん上のカードと違うときだけ書く。なければいちばん上のカード）
    expected = attacks[0].get("card_id", state.cards[attacker.card].card_id) if len(attacks) == 1 else state.cards[attacker.card].card_id
    if expected != card_id:
        problems.append(f"「こんじょう」の決定のワザのカード id {card_id} が、ワザを使ったポケモン {pokemon_id} の使ったワザのカード {expected} と違う")
    target = state.find_pokemon(d.options[0]) if len(d.options) == 1 else None
    if target is None or target[0] != d.player:
        return problems + [f"「こんじょう」の決定の対象 {d.options} が、決定するプレイヤー {d.player} の場のポケモンではない"]
    pokemon = target[1]
    found_power = ko_prevention_power(state, pokemon)
    if found_power is None or found_power[0] != PowerKey(*power):
        return problems + [f"「こんじょう」の決定の特殊能力 {power!r} が、ポケモン {pokemon.pokemon_id} のいちばん上のカードの「こんじょう」ではない"]
    key, effect = found_power
    if pokemon.damage < max_hp(state, pokemon):
        problems.append(f"「こんじょう」の決定の対象のポケモン {pokemon.pokemon_id} が HP 以上のダメージを受けていない")
    if not effect.is_able(pokemon):
        problems.append(f"「こんじょう」の決定の対象のポケモン {pokemon.pokemon_id} がねむり・マヒ・こんらん（使えない。G25〜G27）")
    if ko_prevention_suppressed(state, pokemon, key):
        problems.append(f"「こんじょう」の決定の対象のポケモン {pokemon.pokemon_id} の特殊能力が、かがくへんかガスに消されている（G31）")
    received = None
    for event in events:
        if event["kind"] == "attack":
            break
        if event["kind"] in ("knock_out", "ko_prevention_declined", "ko_prevention_declared", "ko_prevented", "ko_prevention_failed"):
            problems.append(f"「こんじょう」の決定の前に、同じワザのあとの {event['kind']} がある（同じきぜつの判定で 2 度決めさせない）")
        if (received is None and event["kind"] == "damage" and event.get("player") == d.player and event.get("pokemon") == pokemon.card
                and event.get("target", "opponent_active") == "opponent_active" and bool(event.get("retaliation")) == by_attacker):
            received = event
    if received is None or received.get("total_damage") != pokemon.damage:
        problems.append(f"「こんじょう」の決定の対象のポケモン {pokemon.pokemon_id} が、今の番のワザのダメージで今のダメージになったログがない")
    return problems


def _post_knockout_candidate_problems(state: GameState, candidates) -> list[str]:
    """サイドを取る決定の ``context`` の ``"post_knockout"``（「ふしちょう」の候補。v0.12）の整合性。

    形（(持ち主, カードの uid, カード id, パワーの位置) が 1 つ）と、そのカードが持ち主のトラッシュにあり、そのパワーの位置に「ふしちょう」
    （``ReturnToHandOnKnockOut``）が登録され、直前のきぜつ（ログ ``knock_out``。サイドを取る決定の前の、きぜつ・取ったサイドの並び）の
    ポケモンのカードであること。特殊状態・かがくへんかガスはきぜつしたあとの状態からは確かめられない（ログの監査が組み立て直して確かめる）。
    """
    if not (isinstance(candidates, tuple) and len(candidates) == 1 and isinstance(candidates[0], tuple) and len(candidates[0]) == 4):
        return [f"「ふしちょう」の候補 {candidates!r} の形が正しくない（(持ち主, カード, カード id, パワーの位置) が 1 つ）"]
    owner, card, card_id, power_index = candidates[0]
    problems = _post_knockout_card_problems(state, owner, card, card_id, power_index)
    knocked = []
    for event in reversed(state.log):
        kind = event["kind"]
        if kind == "take_prize" and not knocked:
            continue
        if kind == "knock_out":
            knocked.append(event.get("pokemon"))
        elif _knockout_bookkeeping(event):
            continue
        else:
            break
    if card not in knocked:
        problems.append(f"「ふしちょう」の候補のカード {card} が、直前にきぜつしたポケモン {tuple(knocked)} のカードではない")
    return problems


def _post_knockout_card_problems(state: GameState, owner, card, card_id, power_index) -> list[str]:
    """「ふしちょう」の候補・決定のカードが、持ち主のトラッシュにあり、そのパワーの位置に「ふしちょう」が登録されたカードか（v0.12）。"""
    if owner not in PLAYERS or card not in state.cards or state.cards[card].owner != owner:
        return [f"「ふしちょう」のカード {card!r} の持ち主 {owner!r} が正しくない"]
    problems = []
    if card not in state.players[owner].discard:
        problems.append(f"「ふしちょう」のカード {card} が、持ち主 {owner} のトラッシュにない")
    definition = state.card_def(card)
    if definition.id != card_id or not isinstance(power_index, int) or not 0 <= power_index < len(definition.powers):
        return problems + [f"「ふしちょう」のパワー {card_id}@power{power_index!r} が、カード {card}（{definition.id}）のパワーではない"]
    effect = state.effects.power_effect(definition.id, definition.powers[power_index])
    if not isinstance(effect, ReturnToHandOnKnockOut):
        problems.append(f"「ふしちょう」のパワー {card_id}@power{power_index} に、きぜつしたときに使える特殊能力の実装が登録されていない")
    return problems


def _post_knockout_decision_problems(state: GameState, d) -> list[str]:
    """「ふしちょう」を使うかの決定（v0.12。``POST_KNOCKOUT_POWER``・再開先 ``"post_knockout"``）の整合性。

    - 種類と再開先の組、選ぶ数（0〜1）、選べるもの（カード 1 枚）。決定するのはそのカードの持ち主（番のプレイヤーでもよい。きぜつの
      原因を問わない）。
    - ``"power"``: そのカードの、そのパワーの位置に「ふしちょう」が登録されている。カードは持ち主のトラッシュにある。
    - 対戦は続いている（勝ち負けが決まる場合は決めさせない。解決の基盤の ``flow._next_prize_or_judge``）。かがくへんかガスに消されていない（P18）。
    - ログ: 最後のきぜつ（``knock_out``）のどれかがこのカードで、そのあとは取ったサイド（``take_prize``）だけ（同じきぜつで 2 度決めさせない。
      バトル場に出すのはこの決定のあと）。
    """
    if d.kind != POST_KNOCKOUT_POWER or d.resume != "post_knockout":
        return [f"決定 {d.kind} の再開先 {d.resume!r} が合わない（「ふしちょう」の決定は post_knockout_power・post_knockout の組）"]
    problems = []
    if (d.min_choices, d.max_choices) != (0, 1) or len(d.options) != 1:
        return [f"「ふしちょう」の決定の選ぶ数 {d.min_choices}〜{d.max_choices}・選べるもの {d.options} が正しくない（0〜1 個・カード 1 枚）"]
    power = d.context_value("power")
    if not (isinstance(power, tuple) and len(power) == 2):
        return [f"「ふしちょう」の決定の続きの情報 {power!r} が正しくない"]
    card = d.options[0]
    card_id, power_index = power
    problems.extend(_post_knockout_card_problems(state, d.player, card, card_id, power_index))
    if problems:
        return problems
    definition = state.card_def(card)
    if power_suppressed(state, definition.powers[power_index], owner=d.player):
        problems.append(f"「ふしちょう」の決定のカード {card} の特殊能力が、かがくへんかガスに消されている（P18）")
    knocked = []
    for event in reversed(state.log):
        kind = event["kind"]
        if kind == "take_prize" and not knocked:
            continue
        if kind == "knock_out":
            knocked.append(event.get("pokemon"))
        elif _knockout_bookkeeping(event):
            continue
        else:
            break
    if card not in knocked:
        problems.append(f"「ふしちょう」の決定のカード {card} が、直前にきぜつしたポケモン {tuple(knocked)} のカードではない（ログ）")
    return problems


def _power_decision_problems(state: GameState, d) -> list[str]:
    """宣言して使う特殊能力の処理の途中の決定（v0.42。再開先 ``"power"``）の整合性。

    - 続きの情報（``"use"`` = (プレイヤー, 場のポケモンの番号, カード id, 特殊能力の位置)）があり、プレイヤーは番のプレイヤー
    - 特殊能力を使ったポケモンはそのプレイヤーの場にいて、いちばん上のカードが続きの情報のカード id。その位置の特殊能力が、宣言して使う特殊能力として
      登録されている
    - 今の番のログの最後の特殊能力の宣言・ワザの宣言が、この特殊能力の宣言（決定を待つ間はほかのことをしない。ワザのあとではない）
    - 「自分の番ごとに1回」の特殊能力なら、使った記録（``power_uses_this_turn``）がある
    - 決定の形（決定するプレイヤー・種類・選ぶ数・選べるもの）は、実装の ``decision_problems``（トレーナーの決定と同じ考え方）
    """
    use = d.context_value("use")
    if not (isinstance(use, tuple) and len(use) == 4):
        return [f"特殊能力の決定の続きの情報 {use!r} が正しくない"]
    player, pokemon_id, card_id, power_index = use
    return_to = d.context_value("return_to")
    if return_to is not None and not (isinstance(return_to, tuple) and len(return_to) == 4 and return_to[0] == "trainer"):
        return [f"特殊能力の決定のもどる先 {return_to!r} が正しくない"]
    problems = []
    found = state.find_pokemon(pokemon_id)
    # v0.86: 番のプレイヤーのトレーナーの効果（エリカの香水）で手札から場に出させられた相手のポケモンの、場に出たときの特殊能力の使う機会は、持ち主（番でないプレイヤー）が決める
    # （もとの事実のログ ``trainer_bench_from_hand`` を、番のプレイヤーが使ったトレーナーで出したときだけ。ほかの決定に広げない）
    placed_by_opponent = (d.kind == ENTRY_POWER and found is not None and found[0] == player and player != state.current_player
                          and state.trainer_in_use is not None and state.trainer_in_use.using_player == state.current_player
                          and (_entry_fact_event(state, PowerUse(player, pokemon_id, PowerKey(card_id, power_index)), found[1]) or {}).get("kind")
                          == "trainer_bench_from_hand")
    # v0.96: その機会に使った特殊能力の処理の途中の決定（［ENGAGE］の、それぞれが手札をもどすかの決定）も、持ち主の番でないまま続く（``_opponent_entry_followup``）
    placed_by_opponent = placed_by_opponent or (d.kind != ENTRY_POWER and found is not None and found[0] == player
                                                and _opponent_entry_followup(state, player, pokemon_id, found[1]))
    if player != state.current_player and not placed_by_opponent:
        problems.append(f"特殊能力の決定の続きのプレイヤー {player!r} が、番のプレイヤー {state.current_player} ではない")
    if found is None or found[0] != player:
        return problems + [f"特殊能力の決定の続きのポケモン {pokemon_id!r} が、プレイヤー {player!r} の場にいない"]
    pokemon = found[1]
    # v0.49: 特殊能力を印刷したカード（``power_card``。なければいちばん上のカード）。いちばん上のカードでないのは「ばける」でのせたカードだけ
    power_card = d.context_value("power_card")
    if power_card is not None and (power_card == pokemon.card or power_card != pokemon.disguise):
        return problems + [f"特殊能力の決定の続きの特殊能力のカード {power_card!r} が、ポケモン {pokemon_id} の「ばける」でのせたカードではない"]
    definition = state.card_def(pokemon.card if power_card is None else power_card)
    if definition.id != card_id:
        return problems + [f"特殊能力の決定の続きのカード id {card_id!r} が、ポケモン {pokemon_id} の特殊能力のカード {definition.id} と違う"]
    if not (type(power_index) is int and 0 <= power_index < len(definition.powers)):
        return problems + [f"特殊能力の決定の続きの特殊能力の位置 {power_index!r} が正しくない"]
    effect = state.effects.power_effect(definition.id, definition.powers[power_index])
    if effect is None or not effect.declared:
        return problems + [f"特殊能力の決定の続きの特殊能力 {card_id}@power{power_index} が、宣言して使う特殊能力として登録されていない"]
    if d.kind == ENTRY_POWER:
        return problems + _entry_power_decision_problems(state, d, pokemon, effect, PowerUse(player, pokemon_id, PowerKey(card_id, power_index),
                                                                                              return_to=return_to))
    if return_to is not None and not isinstance(effect, EntryPower):
        problems.append(f"特殊能力 {card_id}@power{power_index} は場に出たときに使う特殊能力ではないのに、もどる先 {return_to!r} がある")
    last = next((e for e in _events_since_turn_start(state) if e["kind"] in ("pokemon_power", "attack")), None)
    if (last is None or last["kind"] != "pokemon_power" or (last.get("pokemon_id"), last.get("power_index")) != (pokemon_id, power_index)
            or last.get("card") != power_card):
        problems.append(f"特殊能力の決定（ポケモン {pokemon_id}）の前の、今の番の最後の宣言が、この特殊能力の宣言ではない")
    record = (pokemon_id, power_index) if power_card is None else (pokemon_id, power_index, power_card)
    if effect.once_per_turn and record not in state.power_uses_this_turn:
        problems.append(f"「自分の番ごとに1回」の特殊能力の決定（ポケモン {pokemon_id}）なのに、使った記録がない")
    if isinstance(effect, EntryPower) and last is not None and last["kind"] == "pokemon_power" and "entry" not in last:
        problems.append(f"場に出たときに使う特殊能力の決定（ポケモン {pokemon_id}）の前の宣言が、使う機会の答えの宣言（entry）ではない")
    if not problems:
        problems.extend(effect.decision_problems(state, PowerUse(player, pokemon_id, PowerKey(card_id, power_index), return_to=return_to,
                                                                 card=power_card), d))
    return problems


def _opponent_entry_followup(state: GameState, player: int, pokemon_id: int, pokemon) -> bool:
    """v0.96: 番のプレイヤーが使っているトレーナーの効果（エリカの香水）で手札から場に出させられた相手のポケモン ``pokemon`` の、場に出たときの特殊能力を使ったあとの決定か。
    今の番の最後の特殊能力の宣言が、このポケモンの機会への答え（``pokemon_power`` の ``entry``）で、その前のもとの事実が、使っているトレーナーで出した ``trainer_bench_from_hand``
    （そのあいだにワザ・ほかの宣言がない）。ほかの決定に広げない。"""
    trainer = state.trainer_in_use
    if player == state.current_player or trainer is None or trainer.using_player != state.current_player:
        return False
    declared = False
    for event in _events_since_turn_start(state):  # 新しい順
        kind = event["kind"]
        if kind == "attack":
            return False
        if not declared:
            if kind == "pokemon_power":
                if event.get("pokemon_id") != pokemon_id or not event.get("entry"):
                    return False
                declared = True
            continue
        if kind == "trainer_bench_from_hand" and event.get("card") == pokemon.card and event.get("trainer_card") == trainer.card \
                and not pokemon.evolution_stack:
            return True
    return False


def _entry_fact_event(state: GameState, use: PowerUse, pokemon) -> dict | None:
    """v0.86: 場に出たときに使える特殊能力の機会（``ENTRY_POWER``）のもとの事実のログ: 今の番の、このポケモンに今のいちばん上のカードを重ねた進化（``evolve``）か、手札から場に
    出した（``play_to_bench``・``trainer_bench_from_hand``・``trainer_hand_to_active``）ログ。そのあとにワザ・このポケモンの機会への答え（``pokemon_power`` の ``entry``・
    ``entry_power_declined``）があれば None（機会は 1 度だけ）。"""
    events = _events_since_turn_start(state)  # 新しい順
    for event in events:
        kind = event["kind"]
        if kind == "attack":
            return None
        if kind in ("pokemon_power", "entry_power_declined") and event.get("pokemon_id") == use.pokemon_id and (kind == "entry_power_declined" or event.get("entry")):
            return None
        if kind == "evolve" and event.get("pokemon_id") == use.pokemon_id and event.get("to_card") == pokemon.card:
            return event
        if kind in ("play_to_bench", "trainer_bench_from_hand", "trainer_hand_to_active") and event.get("card") == pokemon.card and not pokemon.evolution_stack:
            return event
    return None


def _entry_power_decision_problems(state: GameState, d, pokemon, effect, use: PowerUse) -> list[str]:
    """場に出たときに使える特殊能力の使う機会の決定（v0.43。``ENTRY_POWER``）の整合性。

    - 実装が ``EntryPower`` で、今の番のログの最後の宣言・進化（``pokemon_power``・``attack``・``evolve``）が、このポケモンに今のいちばん上のカードを重ねた進化
      （機会は場に出したすぐあと。答える前にほかのことをしない。ワザのあとではない）
    - 経路（``context`` の ``"entry"``）が進化のログと合う（手札から: ログに ``source_zone`` がない）。経路で機会があり、かがくへんかガスに消されていない
      （``effects.applicable_entry_power``）
    - 決定するのは持ち主、選べるものはそのポケモンの番号 1 つ、0〜1 個。使うことを選ぶと止める場合（``accept_problem``）と ``unresolved_choices`` が合う
    - もどる先（``"return_to"``）があるのは、トレーナーの効果で進化したとき（進化のログの ``trainer_card``）だけ
    """
    problems = []
    if not isinstance(effect, EntryPower):
        return [f"使う機会の決定（ポケモン {use.pokemon_id}）の特殊能力 {use.key} が、場に出たときに使う特殊能力ではない"]
    last = next((e for e in _events_since_turn_start(state) if e["kind"] in ("pokemon_power", "attack", "evolve")), None)
    if last is None or last["kind"] != "evolve" or last.get("pokemon_id") != use.pokemon_id or last.get("to_card") != pokemon.card:
        # v0.86: 同じ時点の反応（``reactions``。［れんさしんか］など）を先に処理したあとの機会と、手札から場に出したたねポケモン（［おたけび］）の機会。このポケモンの場に出した・
        # 進化した事実のあとにワザ・このポケモンの機会への答えがない
        last = _entry_fact_event(state, use, pokemon)
        if last is None:
            return problems + [f"使う機会の決定（ポケモン {use.pokemon_id}）の前の、今の番の最後の宣言・進化が、このポケモンの進化ではない"]
    route = d.context_value("entry")
    from_hand = "source_zone" not in last
    if route != ("hand" if from_hand else "play"):
        problems.append(f"使う機会の決定の経路 {route!r} が、進化のログ（{'手札から' if from_hand else last.get('source_zone')}）と合わない")
    on_bench = state.players[use.player].active is not pokemon
    zone = d.context_value("entry_zone")
    if zone is not None and (zone != "bench" or not on_bench or not effect.bench_only):
        # v0.84: 場所で機会が決まる特殊能力（［たすけだす］）だけが ``entry_zone`` を持ち、機会の決定を待つ間はそのポケモンは同じ場所（ベンチ）にいる
        problems.append(f"使う機会の決定の場所 {zone!r} が、ポケモン {use.pokemon_id} の場所（{'ベンチ' if on_bench else 'バトル場'}）・特殊能力と合わない")
    if effect.bench_only and zone != "bench":
        problems.append(f"ベンチで進化させたときに使う特殊能力 {use.key} の機会の決定に、場所（entry_zone）がない")
    if applicable_entry_power(state, pokemon.card, from_hand=from_hand, on_bench=on_bench) is None:
        problems.append(f"使う機会の決定（ポケモン {use.pokemon_id}）の特殊能力 {use.key} に、この経路で使う機会がない（経路・場所・かがくへんかガス）")
    if (d.player, d.options, d.min_choices, d.max_choices) != (use.player, (use.pokemon_id,), 0, 1):
        problems.append(f"使う機会の決定の形（{d.player}・{d.options}・{d.min_choices}〜{d.max_choices}）が、持ち主 {use.player}・({use.pokemon_id},)・0〜1 ではない")
    problem = effect.accept_problem(state, use)
    expected = (use.pokemon_id,) if problem is not None else ()
    if tuple(d.context_value("unresolved_choices", ())) != expected or (problem is not None and d.context_value("unresolved_code") != problem.code):
        problems.append(f"使う機会の決定の、選ぶと止める選択 {d.context_value('unresolved_choices', ())} が {expected} ではない")
    returns = use.return_to is not None or any(step[0] == reactions.TRAINER for step in d.context_value(reactions.FOLLOWUP, ()))  # v0.86: 続きのトレーナー
    if returns != ("trainer_card" in last):
        problems.append(f"使う機会の決定のもどる先 {use.return_to!r} が、進化のログ（トレーナー {last.get('trainer_card')!r}）と合わない")
    return problems


def _power_aftermath_problems(state: GameState) -> list[str]:
    """特殊能力の処理のあとの決定（v0.42。続き ``CONTINUE_TURN``。サイド・ふしちょう・交代）の前の、今の番の最後の宣言が特殊能力の宣言（ワザのあとではない）。
    v0.50: きぜつさせうるトレーナー（``TrainerEffect.may_knock_out``。退化スプレー）を使ったあとの決定も同じ続き。今の番の最後の宣言がそのトレーナーの使用
    （``play_trainer``）で、そのあとに ``timing`` が ``"trainer"`` のきぜつがある。"""
    last = next((e for e in _events_since_turn_start(state) if e["kind"] in ("pokemon_power", "attack", "discard_from_play", "play_trainer", "stadium_used",
                                                                              "attach_energy", "retreat", "play_to_bench")), None)
    turn_events = _events_since_turn_start(state)
    after_last = turn_events if last is None else turn_events[:turn_events.index(last)]
    if (last is None or last["kind"] != "attack") and any(e["kind"] == "secret_plan_discarded" and e.get("zone") == "active" for e in after_last):
        return []  # v0.67: おもてにしたバトル場のうらのカードが「たねポケモン」でなく、トラッシュして空いたバトル場（きぜつではない）に出す決定
    if last is not None and last["kind"] != "attack":
        since = _events_since_turn_start(state)[:_events_since_turn_start(state).index(last)]
        if any(e["kind"] == "scram" for e in since):
            return []  # v0.61: その操作のあとに［ずらかる］でバトル場のポケモンが山札にもどった（きぜつではない）あとの、バトル場に出す決定
        if last["kind"] == "retreat":
            # v0.61: 相手の［おとしあな］のダメージで、にげたポケモンがきぜつした（timing retreat）あとの、サイド・交代の決定
            if not any(e["kind"] == "knock_out" and e.get("timing") == "retreat" for e in since):
                return ["「にげる」のあとの決定（続き continue_turn）の前に、［おとしあな］のダメージによるきぜつ（timing retreat）・［ずらかる］がない"]
            return []
    movement_damage = ("spikes_damage", "hot_plate_damage", "stadium_damage")
    if last is not None and last["kind"] == "play_to_bench":
        # v0.87: 手札からベンチに出したたねポケモンが［ヒートプレート］・爆発ジムのダメージできぜつした（timing entry）あとの、サイド・交代の決定
        since = _events_since_turn_start(state)[:_events_since_turn_start(state).index(last)]
        if not any(e["kind"] == "knock_out" and e.get("timing") == "entry" for e in since) or not any(e["kind"] in movement_damage for e in since):
            return ["手札からベンチに出したあとの決定（続き continue_turn）の前に、登場への反応のダメージによるきぜつ（timing entry）がない"]
        return []
    if last is not None and last["kind"] == "attach_energy":
        # v0.58: 手札からつけたレインボーエネルギーの 10 ダメージできぜつした（timing energy）あとの、サイド・交代の決定
        since = _events_since_turn_start(state)[:_events_since_turn_start(state).index(last)]
        if not any(e["kind"] == "knock_out" and e.get("timing") == "energy" for e in since):
            return ["エネルギーをつけたあとの決定（続き continue_turn）の前に、つけたときの効果によるきぜつ（timing energy）がない"]
        return []
    if last is not None and last["kind"] == "stadium_used":
        # v0.57: 場のスタジアムの効果（セキチクシティジム）でバトル場のポケモンを山札にもどしたあとの、バトル場に出す決定
        since = _events_since_turn_start(state)[:_events_since_turn_start(state).index(last)]
        if not any(e["kind"] == "return_in_play_to_deck" and e.get("stadium_card") == last.get("card") for e in since):
            return ["スタジアムの効果のあとの決定（続き continue_turn）の前に、スタジアムの効果で場をはなれたポケモンがない"]
        return []
    if last is not None and last["kind"] == "play_trainer":
        uid = last.get("card")
        entry = state.effects.trainer_entry(state.cards[uid].card_id) if uid in state.cards else None
        since = _events_since_turn_start(state)[:_events_since_turn_start(state).index(last)]
        knocked = any(e["kind"] == "knock_out" and e.get("timing") == "trainer" for e in since)
        # v0.52: 自分のバトル場のポケモンを手札にもどすトレーナー（ポケモン回収。``empties_active``）のあとの、バトル場に出す決定
        # v0.73: スーパーポケモン回収（ついているカードといっしょに手札へ。``return_in_play_to_hand`` の ``zone``）
        emptied = any(e["kind"] in ("return_basic_to_hand", "return_in_play_to_hand") and e.get("zone") == "active" and e.get("trainer_card") == uid
                      for e in since)
        # v0.87: トレーナーの入れ替え・ベンチに出す効果で起こった場の移動への反応（［まきびし］・［ヒートプレート］）のダメージによるきぜつ
        moved = knocked and any(e["kind"] in movement_damage for e in since)
        if entry is None or not ((entry.effect.may_knock_out and knocked) or (entry.effect.empties_active and emptied) or moved):
            return [("トレーナーの使用のあとの決定（続き continue_turn）の前に、きぜつさせうるトレーナーの使用と、そのあとのきぜつ（timing trainer）・"
                     "バトル場のポケモンを場からはなれさせたトレーナーの使用がない")]
        return []
    if last is None or last["kind"] not in ("pokemon_power", "discard_from_play"):
        # v0.47: なにかの化石・ピッピ人形を場からすてて空いたバトル場（``discard_from_play``）も、同じ続きで出す
        return ["特殊能力の処理のあとの決定（続き continue_turn）の前の、今の番の最後の宣言が、特殊能力の宣言・場からすてる操作ではない"]
    return []


def _history_problems(state: GameState) -> list[str]:
    """v0.62（docs/history-attacks-v0.62.md 2 章）: 場のポケモンのワザの履歴（``PokemonInPlay.history``）の不変条件。

    - 履歴を読むワザのカードが対戦になければ、どのポケモンも記録を持たない（``history.history_needed``）
    - 記録の型は ``ATTACK_HISTORY_TYPES``。番は今の番以下で、2 つ前の番より古くない（番の最初に消す）
    - 記録は今の「このカード」のもの（いちばん上のカードが同じで、今の姿になった番より前でない。進化・退化で消す）
    - 使った記録は持ち主の番、受けた記録・ワザ以外で受けた記録は相手の番のもの。受けたワザを使ったのは相手。同じ種類の記録は 1 つの番に 1 つ
    - 使った記録の宣言したワザ・処理したワザ、受けた記録のワザは、効果の登録表にあるワザ。受けた要素の種類・受けなかった理由は決まったもの
    - v0.99: 受けた記録のバトル場で受けた分は、合計以下の 10 の倍数（場所の分からない記録の写しは None）"""
    from .effects import ATTACK_ELEMENTS, DAMAGE_ELEMENT
    from .history import KEPT_TURNS, VOID_REASONS, history_needed
    from .state import ATTACK_HISTORY_TYPES, AttackReceived, AttackUsed

    problems = []
    needed = None
    for owner, p in enumerate(state.players):
        for pokemon in p.in_play():
            if not pokemon.history:
                continue
            if needed is None:
                needed = history_needed(state)
            if not needed:
                problems.append(f"履歴を読むワザのない対戦で、ポケモン {pokemon.pokemon_id} がワザの履歴を持つ")
            seen = set()
            for record in pokemon.history:
                label = f"ポケモン {pokemon.pokemon_id} のワザの履歴 {record!r}"
                if type(record) not in ATTACK_HISTORY_TYPES:
                    problems.append(f"{label} の型が履歴の記録ではない")
                    continue
                if not state.turn_number - KEPT_TURNS <= record.turn <= state.turn_number:
                    problems.append(f"{label} の番が、今の番 {state.turn_number} から 2 つ前までにない")
                if record.card != pokemon.card or record.turn < pokemon.current_form_turn:
                    problems.append(f"{label} が今の「このカード」（カード {pokemon.card}・{pokemon.current_form_turn} 番から）のものではない")
                key = (type(record).__name__, record.turn)
                if key in seen:
                    problems.append(f"{label} と同じ種類の記録が同じ番にもう 1 つある")
                seen.add(key)
                expected_owner = owner if isinstance(record, AttackUsed) else 1 - owner
                if record.turn >= 1 and turn_owner(state, record.turn) != expected_owner:
                    problems.append(f"{label} の番が、{'持ち主' if expected_owner == owner else '相手'}の番ではない")
                keys = ()
                if isinstance(record, AttackUsed):
                    keys = (record.declared,) + (() if record.processed is None else (record.processed,))
                elif isinstance(record, AttackReceived):
                    keys = (record.declared, record.processed)
                    if record.player != 1 - owner or record.damage < 0 or record.damage % 10:
                        problems.append(f"{label} のワザを使ったプレイヤー・受けたダメージが正しくない")
                    if any(kind not in ATTACK_ELEMENTS for kind in record.reached) or any(
                            kind not in ATTACK_ELEMENTS or reason not in VOID_REASONS for kind, reason in record.voided):
                        problems.append(f"{label} の受けた要素・受けなかった理由が決まったものではない")
                    if record.damage and DAMAGE_ELEMENT not in record.reached:
                        problems.append(f"{label} のダメージがあるのに、受けた要素にダメージがない")
                    # v0.99: 受けた時にバトル場にいた分（None は場所の分からない記録の写し）は、合計以下の 10 の倍数
                    if record.active_damage is not None and (not 0 <= record.active_damage <= record.damage or record.active_damage % 10):
                        problems.append(f"{label} のバトル場で受けたダメージが、受けたダメージの合計以下の 10 の倍数ではない")
                for k in keys:
                    if state.effects.attack_entry(k[0], k[1]) is None:
                        problems.append(f"{label} のワザ {k!r} が効果の登録表にない")
    return problems + _turn_history_problems(state)


def _turn_history_problems(state: GameState) -> list[str]:
    """v0.100（docs/sketch-perish-song-history-v0.100.md 3 章）: プレイヤーの番ごとの記録（``GameState.turn_history``）の不変条件。

    - プレイヤーの記録を読むワザのカードが対戦になければ空（``history.turn_history_needed``）
    - 記録の型は ``TURN_HISTORY_TYPES``。番は 1 以上・今の番以下で、2 つ前の番より古くない。番の順
    - 使ったワザの記録（``TurnAttack``）は番ごとに 1 つ・その番のプレイヤーのもので、宣言したワザ・処理したワザは効果の登録表にあるワザ。ワザを使った場のポケモンの番号は付けた番号
    - 場にいたカードの記録（``TurnField``）は番ごとに 1 つ・その番でないプレイヤーのもので、カードはその持ち主の重ならない uid。うらのカードの数は 0 以上"""
    from .history import KEPT_TURNS, turn_history_needed
    from .state import TURN_HISTORY_TYPES, TurnAttack, TurnField

    if not state.turn_history:
        return []
    if not turn_history_needed(state):
        return ["プレイヤーの記録を読むワザのない対戦で、プレイヤーの番ごとの記録がある"]
    problems = []
    seen = set()
    last = 0
    for record in state.turn_history:
        label = f"プレイヤーの番ごとの記録 {record!r}"
        if type(record) not in TURN_HISTORY_TYPES:
            problems.append(f"{label} の型がプレイヤーの記録ではない")
            continue
        if not (max(1, state.turn_number - KEPT_TURNS) <= record.turn <= state.turn_number) or record.turn < last:
            problems.append(f"{label} の番が、今の番 {state.turn_number} から 2 つ前までにない・番の順ではない")
        last = record.turn
        key = (type(record).__name__, record.turn)
        if key in seen:
            problems.append(f"{label} と同じ種類の記録が同じ番にもう 1 つある")
        seen.add(key)
        if isinstance(record, TurnAttack):
            if record.player != turn_owner(state, record.turn) or not 1 <= record.pokemon_id < state.next_pokemon_id:
                problems.append(f"{label} のプレイヤー・場のポケモンの番号が正しくない")
            for k in (record.declared,) + (() if record.processed is None else (record.processed,)):
                if state.effects.attack_entry(k[0], k[1]) is None:
                    problems.append(f"{label} のワザ {k!r} が効果の登録表にない")
        elif isinstance(record, TurnField):
            if record.player != 1 - turn_owner(state, record.turn) or record.face_down < 0 or len(set(record.cards)) != len(record.cards):
                problems.append(f"{label} のプレイヤー・カード・うらのカードの数が正しくない")
            if any(uid not in state.cards or state.cards[uid].owner != record.player for uid in record.cards):
                problems.append(f"{label} のカードが、そのプレイヤーのカードではない")
    return problems


def _energy_role_problems(state: GameState) -> list[str]:
    """v0.59（docs/energy-control-power-suppression-v0.59.md 3 章）: エネルギーとしての役割の記録（``GameState.energy_roles``。マルマインの［エネエネ］）。

    - ``EnergyRole`` の値のタプルで、カードは重複しない。どのカードも、今は場のポケモンについている（ついていなくなった記録はコマンドの終わりに消している）
    - 印刷の定義がポケモンのカードで、持ち主が ``owner``。個数は 2、色は ``EnergyType``、番は今の番まで
    - ログ ``energy_conversion`` に、同じカード・色・個数・番の記録がある（エンジンはこの記録をログから決めない。状態とログが食い違っていないかだけを確かめる）"""
    roles = state.energy_roles
    if not isinstance(roles, tuple) or any(type(r) is not EnergyRole for r in roles):
        return [f"エネルギーとしての役割の記録 {roles!r} が EnergyRole の値のタプルではない"]
    problems = []
    if len({r.card for r in roles}) != len(roles):
        problems.append(f"エネルギーとしての役割の記録 {roles!r} にカードの重複がある")
    for role in roles:
        if role.card not in state.cards:
            problems.append(f"エネルギーとしての役割 {role!r} のカードがこの対戦のカードではない")
            continue
        if state.energy_role(role.card) is None:
            problems.append(f"エネルギーとしての役割 {role!r} のカードが場のポケモンについていない")
        if state.printed_def(role.card).category != "pokemon" or state.cards[role.card].owner != role.owner:
            problems.append(f"エネルギーとしての役割 {role!r} のカードが、持ち主 {role.owner} のポケモンのカードではない")
        if role.units != 2 or not isinstance(role.energy_type, EnergyType) or not 1 <= role.turn <= state.turn_number:
            problems.append(f"エネルギーとしての役割 {role!r} の個数・色・番が正しくない")
        logged = any(e["kind"] == "energy_conversion" and e.get("card") == role.card and e.get("energy_type") == role.energy_type.value
                     and e.get("units") == role.units and e["turn"] == role.turn for e in state.log)
        if not logged:
            problems.append(f"エネルギーとしての役割 {role!r} に対応するログ energy_conversion がない")
    return problems


def _color_effect_problems(state: GameState) -> list[str]:
    """v0.88（docs/type-energy-colors-v0.88.md 2 章）: 特殊能力で色を変える効果の記録（``GameState.color_effects``。［せんすい］・［エナジーコンバーター］）。

    - ``ColorEffect`` の値のタプルで、種類は ``COLOR_EFFECT_KINDS``、番は今の番（番の終わりに消すので、前の番の記録は残らない）、プレイヤーは 0・1
    - 発生源のカードの ``power_index`` 番目の特殊能力の登録が、その種類の効果を与える実装（``color_effect_kind``）で、色はその実装の選べる色
    - ［せんすい］は対象が発生源と同じで、発生源が使ったときと同じカードで場にいる（いなくなった記録はコマンドの終わりに消している）
    - ［エナジーコンバーター］は対象が基本エネルギーカードで、場をはなれた印がなければ場のポケモンについている（印はコマンドの終わりに付けている）
    - 今の番のログの ``color_effect_added`` の数から ``color_effect_removed`` の数を引いた数が、同じ (種類, 発生源, 対象, 色) の記録の数（ログから記録を決めない。食い違いだけを確かめる）"""
    from .effects import color_effect_power, energy_holder
    from .state import COLOR_EFFECT_KINDS, COLOR_ENERGY, COLOR_POKEMON_TYPE, ColorEffect

    records = state.color_effects
    if not isinstance(records, tuple) or any(type(r) is not ColorEffect for r in records):
        return [f"色を変える効果の記録 {records!r} が ColorEffect の値のタプルではない"]
    problems = []
    for record in records:
        where = f"色を変える効果 {record!r}"
        if record.kind not in COLOR_EFFECT_KINDS or record.player not in (0, 1) or record.turn != state.turn_number or not isinstance(record.color, EnergyType):
            problems.append(f"{where} の種類・プレイヤー・番・色が正しくない")
            continue
        if record.source_card not in state.cards:
            problems.append(f"{where} の発生源のカードがこの対戦のカードではない")
            continue
        card_id = state.cards[record.source_card].card_id
        powers = state.definitions[card_id].powers
        entry = state.effects.power_entry(card_id, record.power_index) if record.power_index < len(powers) else None
        if entry is None or getattr(entry.effect, "color_effect_kind", None) != record.kind or record.color not in entry.effect.color_choices():
            problems.append(f"{where} の特殊能力の登録が、その種類・色の効果を与える実装ではない")
        elif state.cards[record.source_card].owner != record.player:
            problems.append(f"{where} の発生源のカードの持ち主が、使ったプレイヤーではない")
        else:
            color_effect_power(state, record)
        found = state.find_pokemon(record.source)
        if record.kind == COLOR_POKEMON_TYPE:
            if record.target != record.source or found is None or record.source_card not in (found[1].card, found[1].disguise) or record.left_play:
                problems.append(f"{where} の対象が、使ったときと同じカードで場にいる発生源ではない")
        elif record.kind == COLOR_ENERGY:
            if record.target not in state.cards or not state.printed_def(record.target).is_basic_energy:
                problems.append(f"{where} の対象が基本エネルギーカードではない")
            elif not record.left_play and energy_holder(state, record.target) is None:
                problems.append(f"{where} の対象のカードが場をはなれたのに、場をはなれた印がない")
    if records:
        counts: dict = {}
        for event in _events_since_turn_start(state):
            if event["kind"] in ("color_effect_added", "color_effect_removed"):
                key = (event.get("color_effect"), event.get("pokemon_id"), event.get("target"), event.get("color"))
                counts[key] = counts.get(key, 0) + (1 if event["kind"] == "color_effect_added" else -1)
        for record in records:
            key = (record.kind, record.source, record.target, record.color.value)
            expected = sum(1 for r in records if (r.kind, r.source, r.target, r.color.value) == key)
            if counts.get(key, 0) != expected:
                problems.append(f"色を変える効果 {record!r} の数が、今の番のログの color_effect_added・color_effect_removed と合わない")
                break
    return problems


def _blaine_double_attached(state: GameState) -> int:
    """v0.59: この番に、カツラの効果で手札から 2 枚をいっしょにつけた通常の操作（ログ ``attach_energy`` の ``energy2``）があれば 1（つけた枚数の上限が 1 枚多い）。"""
    return 1 if any(e["kind"] == "attach_energy" and "energy2" in e for e in _events_since_turn_start(state)) else 0


def _events_since_turn_start(state: GameState) -> list:
    """最後の ``turn_start`` より後のログ（新しい順）。``turn_start`` がなければログ全体。"""
    recent = []
    for event in reversed(state.log):
        if event["kind"] == "turn_start":
            break
        recent.append(event)
    return recent


def _power_attachment_problems(state: GameState) -> list[str]:
    """この番にポケモンパワーで手札からつけたエネルギーの数（v0.6。``energy_attached_by_powers_this_turn``）。

    0 以上の整数で、今の番（最後の ``turn_start`` のあと）のログの ``power_attach_energy`` の数と同じ（番の最初に 0 にし、
    「あまごい」で 1 枚つけるごとに 1 増やすので）。対戦準備の段階（番がまだない）では 0。ログは記録で、エンジンはこの数を
    ログから決めない（ここでは、状態とログが食い違っていないかだけを確かめる）。
    """
    count = state.energy_attached_by_powers_this_turn
    if type(count) is not int or count < 0:
        return [f"この番にポケモンパワーでつけたエネルギーの数 {count!r} が正しくない"]
    logged = 0
    for event in reversed(state.log):
        if event["kind"] == "turn_start":
            break
        if event["kind"] == "power_attach_energy":
            logged += 1
    if count != logged:
        return [f"この番にポケモンパワーでつけたエネルギーの数 {count} が、今の番のログの power_attach_energy の数 {logged} と違う"]
    return []


def _turn_power_problems(state: GameState) -> list[str]:
    """v0.31（形式 10）: この番に使った「自分の番ごとに1回使える」特殊能力（``power_uses_this_turn``）と、「エナジーバーン」で「炎」エネルギーに
    なったエネルギーカード（``energy_burn``）の整合。

    - ``power_uses_this_turn``: (場のポケモンの番号, 特殊能力の位置) の重ならない並びで、今の番のログに、その番号・位置の ``pokemon_power`` があり、
      その特殊能力の実装が回数の制限のあるもの（``once_per_turn``）。今の番のそのような宣言のログの数と同じ。
    - ``energy_burn``: (場のポケモンの番号, エネルギーカードの uid) の重ならない並びで、今の番のログに、その番号の ``energy_burn``（uid を含む）がある。
      番の終わり（ログ ``turn_end``）のあとには残らない。
    """
    problems: list[str] = []
    uses = state.power_uses_this_turn
    burn = state.energy_burn
    if not isinstance(uses, tuple) or not isinstance(burn, tuple):
        return [f"この番の特殊能力の記録 {uses!r}・{burn!r} がタプルではない"]
    recent = _events_since_turn_start(state)
    limited = []
    # v0.50: 宣言のあとに、そのポケモンが進化・退化した（いちばん上のカードが変わった）なら、記録は使ったカードの記録（(番号, 位置, カード)。``evolution.retag_power_uses``）
    changed_after: set = set()
    retagged_events: set[int] = set()
    for event in recent:  # 新しい順
        if event["kind"] in ("evolve", "devolve"):
            changed_after.add(event.get("pokemon_id"))
        elif event["kind"] == "pokemon_power" and event.get("pokemon_id") in changed_after:
            retagged_events.add(id(event))
    for event in recent:
        retagged = id(event) in retagged_events
        if event["kind"] != "pokemon_power" or event.get("pokemon") not in state.cards:
            continue
        # 使ったときのいちばん上のカード（そのあと進化しても、使った記録は残る）。v0.49: ほかのカード（「ばける」でのせたカード）の特殊能力なら、そのカード
        # （ログの ``card``）で、記録は (番号, 位置, カード)
        power_card = event.get("card")
        if power_card is not None and power_card not in state.cards:
            continue
        definition = state.printed_def(event["pokemon"] if power_card is None else power_card)
        index = event.get("power_index")
        if isinstance(index, int) and 0 <= index < len(definition.powers):
            effect = state.effects.power_effect(definition.id, definition.powers[index])
            if getattr(effect, "once_per_turn", False):
                if power_card is None and retagged:
                    power_card = event["pokemon"]  # v0.50: 使ったいちばん上のカードの記録
                limited.append((event.get("pokemon_id"), index) if power_card is None else (event.get("pokemon_id"), index, power_card))
    if len(set(uses)) != len(uses) or sorted(limited) != sorted(uses):
        problems.append(f"この番に使った回数の制限のある特殊能力 {uses} が、今の番のそのような宣言のログ {limited} と合わない")
    burned = {(e.get("pokemon_id"), uid) for e in recent if e["kind"] == "energy_burn" for uid in e.get("energies", ())}
    if len(set(burn)) != len(burn) or not set(burn) <= burned:
        problems.append(f"「炎」エネルギーになったエネルギー {burn} が、今の番のログの energy_burn {sorted(burned)} と合わない")
    if burn and any(e["kind"] == "turn_end" for e in recent):
        problems.append(f"「炎」エネルギーになったエネルギー {burn} が、番の終わりのあとに残っている（自分の番の終わりにもとにもどる）")
    for pid, uid in burn:
        if uid not in state.cards or state.card_def(uid).category != "energy":
            # v0.58: 特殊エネルギーカード（無色2個エネルギーなど）も「エナジーバーン」で「炎」になる（「すべてのエネルギー」）
            problems.append(f"「炎」エネルギーになったカード {uid!r} がエネルギーカードではない")
    return problems


def _progress_problems(state: GameState) -> list[str]:
    """番の進行とポケモンチェックの整合（v0.3a）。ログの最後の 2 つの ``turn_start`` から後ろだけを見る。

    - 今の番の番号と番のプレイヤーが、最後の ``turn_start`` の番とプレイヤーと同じ（v0.4e）。
    - 前の番の始まりから今の番の始まりまでに、``turn_end`` → ``pokemon_check`` がちょうど 1 回ずつ（p.309。
      ポケモンチェックを二度しない・飛ばさない）。
    - 今の番の始まりのあと: 番の途中（ワザのあとのサイド・交代の決定を含む）ならどちらもない。ポケモンチェックの
      途中の決定（``context`` の ``then`` が ``NEXT_TURN``）なら 1 回ずつ（次の番はまだ始まっていない）。
      終わった対戦は、どちらでもよい（番の途中・ポケモンチェックの中のどちらでも勝敗は決まる）。
    """
    log = state.log
    starts: list[int] = []
    i = len(log) - 1
    while i >= 0 and len(starts) < 2:
        if log[i]["kind"] == "turn_start":
            starts.append(i)
        i -= 1
    if not starts:
        return []

    def marks(begin: int, end: int) -> list[str]:
        return [log[j]["kind"] for j in range(begin, end) if log[j]["kind"] in ("turn_end", "pokemon_check")]

    problems = []
    last_start = log[starts[0]]
    if last_start.get("turn") != state.turn_number or last_start.get("player") != state.current_player:
        # 番は 1 つずつ交互に進み、番の番号と番のプレイヤーは番の始まりで決まる（p.309。v0.4e。番の番号を偶数だけずらした
        # 状態は、番のプレイヤーの確認だけでは見つからなかった）
        problems.append(
            f"今の番 {state.turn_number!r}（プレイヤー {state.current_player!r}）が、最後の番の始まり（ログ turn_start の"
            f" {last_start.get('turn')!r} 番、プレイヤー {last_start.get('player')!r}）と違う"
        )
    if len(starts) == 2 and marks(starts[1] + 1, starts[0]) != ["turn_end", "pokemon_check"]:
        problems.append(f"番と番のあいだの番の終わり・ポケモンチェックが {marks(starts[1] + 1, starts[0])}（1 回ずつ、この順のはず）")
    tail = marks(starts[0] + 1, len(log))
    d = state.decision
    if state.phase in TERMINAL_PHASES:
        allowed = ([], ["turn_end", "pokemon_check"])
    elif d is not None and d.context_value("then") == NEXT_TURN:
        allowed = (["turn_end", "pokemon_check"],)
    else:
        allowed = ([],)
    if tail not in allowed:
        problems.append(f"{state.phase.value} なのに、今の番のあとの番の終わり・ポケモンチェックが {tail}")
    return problems


def _bench_limit_or_default(state: GameState, player: int) -> int:
    """ベンチの上限（v0.57。``stadiums.bench_limit``）。場のスタジアムの実装が引けない壊れた状態では、共通のルールの値（``_stadium_problems`` が見つける）。"""
    try:
        return bench_limit(state, player)
    except RuntimeError:
        return state.rules.max_bench


def _narrow_cleanup_pending(state: GameState, player: int) -> bool:
    """せまいジムが場に出た時の、手札にもどすポケモンを選ぶ決定（v0.57）を ``player`` が待っている・このあと待つか。"""
    d = state.decision
    return (d is not None and d.resume == "stadium" and d.context_value("stage") == "narrow"
            and player in (d.player, *d.context_value("remaining", ())))


def _stadium_problems(state: GameState) -> list[str]:
    """場のスタジアム（v0.57。``GameState.stadium``）と、この番に使った「自分の番ごとに1回」のスタジアムの効果（``stadium_uses_this_turn``）。

    - 場のスタジアム: ``StadiumInPlay``。カードは持ち主のカードで（保存則は ``check_invariants`` の本体）、トレーナーカードで、効果の登録表の実装がスタジアム。場に出した番は
      今の番まで。ログに、そのカードを場に出した ``stadium_placed`` があり、そのあとにトラッシュした ``stadium_discarded`` がない（ログのある対戦だけ）
    - 使った記録: (使ったプレイヤー, スタジアムカード) の重ならない並び。そのカードの実装が「自分の番ごとに1回」で、使ったのは番のプレイヤー。今の番のログの ``stadium_used``
      （同じプレイヤー・同じカード）の数と記録の数が同じ
    """
    problems: list[str] = []
    stadium = state.stadium
    if stadium is not None:
        where = f"場のスタジアム {stadium!r}"
        if not isinstance(stadium, StadiumInPlay):
            return [f"{where} の型が StadiumInPlay ではない"]
        if stadium.card not in state.cards:
            return [f"{where} のカードが対戦のカードではない"]
        definition = state.printed_def(stadium.card)
        entry = state.effects.trainer_entry(definition.id)
        if definition.category != "trainer" or entry is None or not entry.effect.is_stadium:
            problems.append(f"{where} のカード {definition.id} が、登録されたスタジアムカードではない")
        if type(stadium.placed_turn) is not int or not 0 <= stadium.placed_turn <= state.turn_number:
            problems.append(f"{where} の場に出した番 {stadium.placed_turn!r} が正しくない")
        if any(event["kind"] == "game_created" for event in state.log):
            placed = [i for i, e in enumerate(state.log) if e["kind"] == "stadium_placed" and e.get("card") == stadium.card]
            if not placed or any(e["kind"] == "stadium_discarded" and e.get("card") == stadium.card for e in state.log[placed[-1]:]):
                problems.append(f"{where} を場に出したログ stadium_placed がない（または、そのあとにトラッシュしたログがある）")
    uses = state.stadium_uses_this_turn
    if type(uses) is not tuple or len(set(uses)) != len(uses):
        return problems + [f"この番に使ったスタジアムの効果の記録 {uses!r} が正しくない"]
    recent = _events_since_turn_start(state)
    for record in uses:
        if not (isinstance(record, tuple) and len(record) == 2 and record[0] in PLAYERS and record[1] in state.cards):
            problems.append(f"スタジアムの効果の記録 {record!r} が正しくない")
            continue
        player, card = record
        entry = state.effects.trainer_entry(state.cards[card].card_id)
        if entry is None or not entry.effect.is_stadium or not entry.effect.records_uses:
            problems.append(f"スタジアムの効果の記録 {record} のカードが、使った記録を残すスタジアム（「自分の番ごとに1回」など。v0.74 の records_uses）ではない")
        if player != state.current_player:
            problems.append(f"スタジアムの効果の記録 {record} のプレイヤーが、番のプレイヤーではない")
        logged = sum(1 for e in recent if e["kind"] == "stadium_used" and e.get("player") == player and e.get("card") == card)
        if logged != 1:
            problems.append(f"スタジアムの効果の記録 {record} に対応する、今の番のログ stadium_used が {logged} 回")
    once_logged = [(e.get("player"), e.get("card")) for e in recent if e["kind"] == "stadium_used" and e.get("card") in state.cards
                   and getattr((state.effects.trainer_entry(state.cards[e["card"]].card_id) or E_NONE).effect, "records_uses", False)]
    if sorted(once_logged) != sorted(uses):
        problems.append(f"今の番のログの「自分の番ごとに1回」のスタジアムの使用 {once_logged} が、記録 {uses} と違う")
    return problems


class _NoEntry:
    effect = None


E_NONE = _NoEntry()


def _stadium_decision_problems(state: GameState, d) -> list[str]:
    """スタジアムの効果の途中の決定（v0.57。再開先 ``"stadium"``）の形。"""
    stage = d.context_value("stage")
    card = d.context_value("stadium")
    where = f"スタジアムの決定（{stage}）"
    if stage == "evolution_heal":
        found = state.find_pokemon(d.context_value("pokemon"))
        then = d.context_value("after_heal")
        terms = None if found is None else (stadium_of(state, EvolutionHealStadium))
        problems = []
        if found is None or terms is None or terms[0].card != card:
            return [f"{where} のポケモン・場のトキワシティジムが正しくない"]
        owner, pokemon = found
        if (d.kind, d.player, d.options, d.min_choices, d.max_choices) != (EVOLUTION_HEAL, owner, (pokemon.pokemon_id,), 0, 1):
            problems.append(f"{where} の形 {d.kind} {d.player} {d.options} が、持ち主への 0〜1 個の問いではない")
        if pokemon.damage <= 0:
            problems.append(f"{where} のポケモン {pokemon.pokemon_id} にダメージカウンターがない")
        if not (isinstance(then, tuple) and len(then) == 3 and then[0] == "entry"):
            problems.append(f"{where} の続き {then!r} が正しくない")
        return problems
    found = stadium_in_play(state) if state.stadium is not None else None
    if found is None or found[0].card != card:
        return [f"{where} のスタジアム {card!r} が場にない"]
    _, effect = found
    if stage == "narrow":
        problems = []
        if not isinstance(effect, BenchLimitStadium) or d.kind != STADIUM_RETURN_BENCH:
            problems.append(f"{where} の種類 {d.kind} と場のスタジアムが合わない")
        if d.options != tuple(p.pokemon_id for p in state.players[d.player].bench) or (d.min_choices, d.max_choices) != (1, 1):
            problems.append(f"{where} の選べるもの {d.options} が、プレイヤー {d.player} の控えポケモン 1 匹ではない")
        if len(state.players[d.player].bench) <= effect.limit:
            problems.append(f"{where} のプレイヤー {d.player} のベンチが上限より多くない")
        if any(len(state.players[p].bench) > effect.limit for p in PLAYERS if p not in (d.player, *d.context_value("remaining", ()))):
            problems.append(f"{where} の順番に入っていないプレイヤーのベンチが上限より多い")
        return problems
    if stage == "fuchsia":
        problems = []
        if not isinstance(effect, CoinReturnOwnerPokemonStadium) or d.kind != SELECT_POKEMON or d.player != state.current_player:
            problems.append(f"{where} の種類 {d.kind}・プレイヤー {d.player} が、番のプレイヤーのポケモンを選ぶ決定ではない")
        elif d.options != tuple(effect.targets(state, d.player)) or (d.min_choices, d.max_choices) != (1, 1):
            problems.append(f"{where} の選べるもの {d.options} が、自分の場の「{effect.owner}のポケモン」1 匹ではない")
        return problems
    if stage == LookDeckTopStadium.choice_stage:
        # v0.80: ラジオとうで見る枚数（決めるのは番のプレイヤー。この番にこのカードを使った記録とログ stadium_used がある）
        problems = []
        if not isinstance(effect, LookDeckTopStadium) or d.kind != effect.choice_kind or d.player != state.current_player:
            return [f"{where} の種類 {d.kind}・プレイヤー {d.player}・場のスタジアムが、番のプレイヤーのラジオとうの決定ではない"]
        options = effect.counts(state, d.player)
        if not state.players[d.player].deck or d.options != options or (d.min_choices, d.max_choices) != (1, 1):
            problems.append(f"{where} の選べるもの {d.options} が、見る枚数 {options} から 1 つではない")
        if (d.player, card) not in state.stadium_uses_this_turn:
            problems.append(f"{where} のプレイヤー {d.player} が、この番にスタジアム {card} を使った記録がない")
        return problems
    if stage in COIN_CHOICE_STAGES:
        # v0.74: エネルギースタジアム・キョウの忍者ジムの「おもて」のあと（段階と決定の種類は実装の ``choice_stage``・``choice_kind``）。決めるのは番のプレイヤー（使ったプレイヤー）
        # で、この番にこのカードを使った記録とログ stadium_used・「おもて」のコインがある。選べるものは実装の ``candidates``（ちょうど 1 枚）
        problems = []
        if getattr(effect, "choice_stage", None) != stage or d.kind != effect.choice_kind or d.player != state.current_player:
            return [f"{where} の種類 {d.kind}・プレイヤー {d.player}・場のスタジアムが、番のプレイヤーの段階 {stage} の決定ではない"]
        options = tuple(effect.candidates(state, d.player))
        if not options or d.options != options or (d.min_choices, d.max_choices) != (1, 1):
            problems.append(f"{where} の選べるもの {d.options}（{d.min_choices}〜{d.max_choices}）が、{options} から 1 枚ではない")
        if effect.needs_bench_room and not bench_has_room(state, d.player):
            problems.append(f"{where} のプレイヤー {d.player} のベンチに空きがない")
        if (d.player, card) not in state.stadium_uses_this_turn:
            problems.append(f"{where} のプレイヤー {d.player} が、この番にスタジアム {card} を使った記録がない")
        recent = list(reversed(_events_since_turn_start(state)))  # 古い順
        used = [i for i, e in enumerate(recent) if e["kind"] == "stadium_used" and e.get("player") == d.player and e.get("card") == card]
        coins = [e for e in recent[used[-1]:] if e["kind"] == "coin_flip" and e.get("source") == "stadium" and e.get("card") == card] if used else []
        if len(coins) != 1 or coins[0].get("result") != "heads":
            problems.append(f"{where} の前に、このスタジアムの「おもて」のコインが 1 枚ない")
        return problems
    return [f"{where} の段階が正しくない"]


def _decision_problems(state: GameState) -> list[str]:
    """保留中の決定と段階・場の形の整合性。"""
    problems: list[str] = []
    phase = state.phase
    d = state.decision
    if phase not in DECISION_PHASES:
        if d is not None:
            problems.append(f"{phase.value} なのに、決定が残っている")
        return problems
    if d is None:
        if phase is Phase.TAKE_PRIZE:
            problems.append("サイドを取る段階なのに、サイドを取るプレイヤーがいない")
        elif phase is Phase.PROMOTE_ACTIVE:
            problems.append("バトル場に出す段階なのに、出すプレイヤーがいない")
        else:
            problems.append("決定を待つ段階なのに、決定がない")
        return problems
    if phase_for(d.kind) is not phase:
        problems.append(f"決定の種類 {d.kind} と段階 {phase.value} が合わない")
    if d.player not in PLAYERS:
        problems.append(f"決定するプレイヤー {d.player!r} が正しくない")
        return problems
    if not 1 <= d.id < state.next_decision_id:
        problems.append(f"決定の番号 {d.id} が正しくない（次に付ける番号 {state.next_decision_id}）")
    # 選ぶ数の上限は選べるものの数を超えてよい（「2 匹まで選ぶ」で 1 匹しかいない場合）。下限は選べる数まで
    if len(set(d.options)) != len(d.options) or not 0 <= d.min_choices <= d.max_choices or d.min_choices > len(d.options):
        problems.append(f"決定の選べるもの {d.options} と選ぶ数 {d.min_choices}〜{d.max_choices} が合わない")
    if d.resume not in DECISION_RESUMES:
        problems.append(f"決定の再開先 {d.resume!r} がない")
    remaining = d.context_value("remaining", ())
    then = d.context_value("then")
    if (d.kind in (TAKE_PRIZE, PROMOTE_ACTIVE) or d.resume in (TAKE_PRIZE, PROMOTE_ACTIVE)) and d.resume != d.kind:
        # v0.1 からある種類の決定は、その種類の再開先で続ける（v0.4e。それまではポケモンチェックの中の決定だけ確かめていた）
        problems.append(f"決定 {d.kind} の再開先 {d.resume!r} が種類と合わない")
    if d.kind in (TAKE_PRIZE, PROMOTE_ACTIVE) and (d.min_choices, d.max_choices) != (1, 1):
        problems.append(f"決定 {d.kind} で選ぶ数が {d.min_choices}〜{d.max_choices}（サイド 1 枚・ポケモン 1 匹のはず。p.312・p.313）")
    if then is not None:
        # ポケモンチェックの中のきぜつのあとの決定（v0.3a）。サイド・交代（v0.12 から「ふしちょう」も）だけで、交代は 1 人だけ
        # （両方のバトル場が空になる場合は、出す順番が決まらないので止めている）。v0.42: 特殊能力の処理のあとの決定（続き CONTINUE_TURN。のろいのきぜつ・
        # おくびょうで空いたバトル場）も同じ種類だけで、交代は 1 人だけ（1 回の使用できぜつする・場をはなれるのは 1 匹）
        kinds = {TAKE_PRIZE: TAKE_PRIZE, PROMOTE_ACTIVE: PROMOTE_ACTIVE, POST_KNOCKOUT_POWER: "post_knockout"}
        if then not in (NEXT_TURN, CONTINUE_TURN) or kinds.get(d.kind) != d.resume:
            problems.append(f"決定 {d.kind} の続き {then!r} が正しくない")
        if d.kind == PROMOTE_ACTIVE and remaining:
            problems.append(f"{'ポケモンチェック' if then == NEXT_TURN else '特殊能力の処理'}のあとにバトル場に出すプレイヤーが複数いる {(d.player, *remaining)}")
        if then == CONTINUE_TURN:
            problems.extend(_power_aftermath_problems(state))
    if d.kind == TAKE_PRIZE:
        prizes = state.players[d.player].prizes
        queue = (d.player, *remaining)
        if d.options != tuple(range(len(prizes))):
            problems.append(f"サイドを取る決定の選べる位置 {d.options} が、サイドの枚数 {len(prizes)} と合わない")
        for player in PLAYERS:
            if queue.count(player) > len(state.players[player].prizes):
                problems.append(f"プレイヤー {player} がサイドを取る回数が、残りのサイドより多い")
        if any(player not in PLAYERS for player in remaining):
            problems.append(f"サイドを取るプレイヤーの並び {queue} が正しくない")
        else:
            problems.extend(_prize_queue_problems(state, queue))
        candidates = d.context_value("post_knockout")
        if candidates is not None:
            problems.extend(_post_knockout_candidate_problems(state, candidates))  # v0.12
    elif d.context_value("post_knockout") is not None:
        problems.append(f"サイドを取る決定でない {d.kind} に、「ふしちょう」の候補が書かれている")
    if d.kind == PROMOTE_ACTIVE:
        queue = (d.player, *remaining)
        for player in queue:
            if player not in PLAYERS or state.players[player].active is not None or not state.players[player].bench:
                problems.append(f"バトル場に出すプレイヤー {player} の場の形が正しくない")
        if len(queue) > 1 and queue != (1 - state.current_player, state.current_player):
            # 両方が出すときは、今が番でないプレイヤーが先（pp.323〜324。解決の基盤の flow._promotions_after_judge。v0.4e）
            problems.append(f"バトル場に出す順番 {queue} が、番でないプレイヤー {1 - state.current_player!r} からではない（pp.323〜324）")
        for player in PLAYERS:
            if player not in queue and state.players[player].active is None:
                problems.append(f"プレイヤー {player} のバトル場にポケモンがいないのに、出す順番に入っていない")
        if d.options != tuple(pokemon.pokemon_id for pokemon in state.players[d.player].bench):
            problems.append(f"バトル場に出す決定の選べるもの {d.options} が、ベンチのポケモンと合わない")
    if d.resume == "attack":
        problems.extend(_attack_decision_problems(state, d))
    if d.kind == KNOCK_OUT_POWER:
        problems.extend(_knock_out_power_decision_problems(state, d))  # v0.61
    elif d.kind == EXP_ALL_ENERGY:
        problems.extend(_exp_all_decision_problems(state, d))  # v0.81
    elif d.kind == KO_PREVENTION or d.resume == "knock_out":
        problems.extend(_ko_prevention_decision_problems(state, d))  # v0.11
    if d.kind == POST_KNOCKOUT_POWER or d.resume == "post_knockout":
        problems.extend(_post_knockout_decision_problems(state, d))  # v0.12
    if d.resume == "power":
        problems.extend(_power_decision_problems(state, d))  # v0.42
    if d.resume == "stadium":
        problems.extend(_stadium_decision_problems(state, d))  # v0.57
    if d.resume == reactions.RESUME:
        problems.extend(reactions.answer_problems(state, d))  # v0.86
    # 選べるもののうち原典で扱いを決められないもの（v0.2b）: 選べるものの中にあり、残りで答えられる
    unresolved = d.context_value("unresolved_choices", ())
    if unresolved:
        if not set(unresolved) <= set(d.options):
            problems.append(f"扱いを決められない選択 {unresolved} が、選べるもの {d.options} にない")
        # v0.43: 場に出たときの特殊能力の使う機会（ENTRY_POWER）は、使わない（0 個）がいつも答えになる（使うことを選ぶと止める場合も。_resume_power）
        # v0.57: トキワシティジムのとりのぞく機会（EVOLUTION_HEAL。VG1）・錯乱ジムで借りるかの問い（ACCEPT_REQUEST の続きの情報 chaos。CH1 など）も、選ばない（0 個）が
        # いつも答えになる（借りない・とりのぞかない）
        # v0.58: ナツメのサイキックコントロールで使うカード（USE_DISCARD_TRAINER）も、使わない（0 個。「使ってよい」）がいつも答えになる（CH1 など選ぶと止めるカード）
        # v0.61: ［ファイナルビーム］の使う機会（KNOCK_OUT_POWER。Z9・C18・RB1・BZ2 など使うと止める場合）も、使わない（0 個）がいつも答えになる
        # v0.65: 変わり身の術・［にげこむ］・［ベンチガード］の機会（NINJA_TRICK・REACTION_SWITCH・BENCH_GUARD。NT3・RX1・FL1・BG1・BG2・KD1 で使うと止める場合）も同じ
        # v0.66: ナツメのESPのやり直しの機会（ESP_REDO。ES1〜ES3 でやり直すと止める場合）も、やり直さない（0 個）がいつも答えになる
        # v0.67: マチスの秘策で出すカード（SECRET_PLAN_CARD。FD2 で出すと止める場合）も、出さない（0 個。「出してよい」）がいつも答えになる
        # v0.81: 学習装置（EXP_ALL_ENERGY。RB3・CB1 で選ぶと止める場合）も、つけ替えない（0 個）がいつも答えになる
        # v0.86: 反応の特殊能力の使う機会（REACTION_POWER。RB1・MEC1・DV2 で使うと止める場合）も、使わない（0 個）がいつも答えになる
        # v0.88: 「変えてよい」色の決定（SELECT_COLOR の選ぶ数 0〜1。テクスチャー2・テクスチャーマジックの抵抗力。抵抗力のないポケモンが相手のワザとして使うと色を選ぶと PG1）も、
        # 変えない（0 個）がいつも答えになる
        no_choice_answers = d.kind in (ENTRY_POWER, EVOLUTION_HEAL, USE_DISCARD_TRAINER, KNOCK_OUT_POWER, EXP_ALL_ENERGY, NINJA_TRICK, REACTION_SWITCH, BENCH_GUARD, ESP_REDO,
                                       SECRET_PLAN_CARD, reactions.REACTION_POWER) or (d.kind == ACCEPT_REQUEST and d.context_value("chaos") is not None) \
            or (d.kind == SELECT_COLOR and d.resume == "attack" and d.min_choices == 0) \
            or (d.kind == FORCED_SWITCH and d.resume == "attack" and d.min_choices == 0) \
            or (d.kind == ACCEPT_REQUEST and d.resume == "power" and d.min_choices == 0)
        # v0.94: ワザの任意の入れ替え（きつねび。RX1 で止める控え）も、入れ替えない（0 個）が答え。v0.96: 特殊能力の「のぞむなら」の決定（［ENGAGE］で手札をもどすか。
        # 手札 0 枚の「もどす」は EG1）も、もどさない（0 個）がいつも答えになる
        needed = 0 if no_choice_answers and d.min_choices == 0 else max(d.min_choices, 1)
        if len(set(d.options) - set(unresolved)) < needed:
            problems.append(f"決定 {d.kind} に、扱いを決められる選択が足りない（答えられない）")
    return problems


def _set_aside_problems(state: GameState) -> list[str]:
    """v0.63（docs/hidden-card-trainers-v0.63.md 2 章）: 一時的に置いておくカードのまとまり（``GameState.set_aside``）の形。

    - 種類・持ち主・使ったプレイヤー・置いた番・カード（重ならない 1 枚以上）・見られるプレイヤー（くすぐりマシーンはだれも見ない、挑戦状・クイズは持ち主だけ）
    - くすぐりマシーン（``SET_ASIDE_HAND``）: もどす番は置いた番より後で、対戦が続いていれば今の番より前ではない（期限の番の終わりに手札にもどす）。置いたトレーナーのカードは
      くすぐりマシーンの実装（``CoinSetAsideOpponentHandElseEndTurn``）で、持ち主は使ったプレイヤーの相手
    - 挑戦状・クイズ: トレーナーの効果の途中だけにある（使用中のトレーナーがそのカードで、その決定を待っている）。もどす番はない。挑戦状はたねポケモンのカード（山札から選んだ）で、
      持ち主のベンチと合わせてベンチの上限まで。持ち主ごとに 1 つ。クイズは使ったプレイヤーのワザを持つポケモンのカード 1 枚
    - ログ: 置いたログ（``set_aside_hand``・``face_down_bench``・``quiz_card_set``）があり、同じカードで、そのあとにもどした・表にしたログがない"""
    problems: list[str] = []
    if not isinstance(state.set_aside, tuple):
        return [f"置いておくカードの並び {state.set_aside!r} がタプルではない"]
    used = state.trainer_in_use
    waiting = used is not None and state.decision is not None and state.decision.resume == "trainer"
    seen_kinds: set = set()
    put_events = {"set_aside_hand": SET_ASIDE_HAND, "face_down_bench": SET_ASIDE_FACE_DOWN_BENCH, "quiz_card_set": SET_ASIDE_QUIZ}
    for group in state.set_aside:
        if not isinstance(group, SetAsideCards) or group.kind not in SET_ASIDE_KINDS or group.owner not in PLAYERS or group.user not in PLAYERS:
            problems.append(f"置いておくカード {group!r} の形が正しくない")
            continue
        cards = group.cards
        if not cards or not isinstance(cards, tuple) or len(set(cards)) != len(cards) or any(uid not in state.cards for uid in cards):
            problems.append(f"置いておくカード {group} のカードが正しくない")
            continue
        expected_visible = () if group.kind == SET_ASIDE_HAND else (group.owner,)
        if group.visible_to != expected_visible:
            problems.append(f"置いておくカード {group} の見られるプレイヤー {group.visible_to} が {expected_visible} ではない")
        if not 1 <= group.created_turn <= state.turn_number or group.trainer_card not in state.cards or state.cards[group.trainer_card].card_id != group.card_id:
            problems.append(f"置いておくカード {group} の置いた番・トレーナーのカードが正しくない")
            continue
        if group.kind == SET_ASIDE_HAND:
            entry = state.effects.trainer_entry(group.card_id)
            if entry is None or entry.effect.implementation_id != "coin_set_aside_opponent_hand_else_end_turn" or group.owner != 1 - group.user:
                problems.append(f"手札を置いておくまとまり {group} の出どころ（トレーナー・持ち主）が正しくない")
            ongoing = state.phase not in TERMINAL_PHASES
            if not isinstance(group.return_turn, int) or group.return_turn <= group.created_turn or (ongoing and group.return_turn < state.turn_number):
                problems.append(f"手札を置いておくまとまり {group} のもどす番 {group.return_turn!r} が正しくない（今の番 {state.turn_number}）")
            elif group.return_turn != next_turn_after(state, group.created_turn, group.owner):
                problems.append(f"手札を置いておくまとまり {group} のもどす番 {group.return_turn} が、置いた番のあとの持ち主の最初の番ではない")
        else:
            if group.return_turn is not None or not waiting or used.card != group.trainer_card or group.created_turn != state.turn_number:
                problems.append(f"トレーナーの効果の途中に置いたカード {group} が、そのトレーナーの決定を待つ間ではない")
            key = (group.kind, group.owner)
            if key in seen_kinds:
                problems.append(f"プレイヤー {group.owner} の {group.kind} のまとまりが 2 つある")
            seen_kinds.add(key)
            if group.kind == SET_ASIDE_FACE_DOWN_BENCH:
                if any(not state.card_def(uid).is_basic_pokemon for uid in cards):
                    problems.append(f"うらにしてベンチに出したカード {cards} に、たねポケモンでないカードがある")
                if len(state.players[group.owner].bench) + len(cards) > _bench_limit_or_default(state, group.owner):
                    problems.append(f"プレイヤー {group.owner} のベンチとうらにして出したカードが、ベンチの上限より多い")
            elif len(cards) != 1 or group.owner != group.user or not _quiz_card_accepted(state, group.card_id, cards[0]):
                problems.append(f"クイズで置いたカード {group} が、使ったプレイヤーのワザを持つポケモンのカード 1 枚ではない")
        put = [e for e in state.log if put_events.get(e["kind"]) == group.kind and e.get("player") == group.owner and e.get("trainer_card") == group.trainer_card
               and tuple(e.get("cards", (e.get("card"),))) == cards]
        if not put:
            problems.append(f"置いておくカード {group} を置いたログがない")
        else:
            after = state.log[state.log.index(put[-1]) + 1:]
            if any(e["kind"] in ("set_aside_returned", "face_down_revealed") and e.get("trainer_card") == group.trainer_card and e.get("player") == group.owner
                   and tuple(e.get("cards", ())) == cards for e in after):
                problems.append(f"置いておくカード {group} を、もどした・表にしたログのあとに、まだ置いている")
    return problems


def _quiz_card_accepted(state: GameState, card_id: str, card: int) -> bool:
    """v0.63・v0.80: クイズで置いてよいカードか（カツラのクイズ その3 はワザを持つポケモンのカード、その2 は手札のどのカードでも、ポケモン性格判定は進化カード。登録の実装の
    ``kinds`` で決め、カード id で分けない）。"""
    entry = state.effects.trainer_entry(card_id)
    kinds = getattr(entry.effect, "kinds", None) if entry is not None else None
    definition = state.card_def(card)
    if kinds == "card_kind":
        return True
    if kinds == "personality":
        return definition.is_evolution_pokemon
    return definition.category == "pokemon" and bool(definition.attacks)


def next_turn_after(state: GameState, turn: int, player: int) -> int:
    """v0.63: 番 ``turn`` より後の、プレイヤー ``player`` の最初の番（番は交互に進む）。"""
    following = turn + 1
    return following if turn_owner(state, following) == player else following + 1


def _face_up_prize_problems(state: GameState) -> list[str]:
    """v0.63: おもてのサイドの記録（``GameState.face_up_prizes``。ロケット団参上!）が、重ならず、どれもいまサイドにあるカードで、おもてにしたログ（``prizes_revealed``）の
    カードであること（あとからサイドに置かれたカードはおもてにならない）。"""
    face_up = state.face_up_prizes
    if not isinstance(face_up, tuple) or len(set(face_up)) != len(face_up):
        return [f"おもてのサイドの記録 {face_up!r} が重ならない並びではない"]
    if not face_up:
        return []
    problems = []
    prizes = {uid for p in state.players for uid in p.prizes}
    revealed = {uid for e in state.log if e["kind"] == "prizes_revealed" for uid in e["cards"]}
    revealed |= {e["card"] for e in state.log if e["kind"] == "prize_revealed"}  # v0.80: カードめくりゲーム
    for uid in face_up:
        if uid not in prizes:
            problems.append(f"おもてのサイドの記録のカード {uid} が、サイドにない")
        if uid not in revealed:
            problems.append(f"おもてのサイドの記録のカード {uid} を、おもてにしたログがない")
    return problems


def _knockout_bookkeeping(event) -> bool:
    """直前のきぜつをログの終わりから読むとき（サイドの並び・「ふしちょう」の候補）、きぜつのあとに続いてよい記録: きぜつで消えた持続する効果、v0.82 のきぜつでトラッシュに
    置かれたリサイクルエネルギーを持ち主の手札にもどしたこと、v0.88 のきぜつで場をはなれた［せんすい］の発生源の記録をコマンドの終わり（``effects.settle_color_effects``）に
    消したこと（``target_gone``）。v0.87 までの「ふしちょう」の確かめは、リサイクルエネルギーのもどしを読み飛ばしていなかった（docs/type-energy-colors-v0.88.md 8 章）。
    v0.92: きぜつで発生源がバトル場をはなれて消えた、相手のポケモンの持続する効果（くろいまなざし。理由 ``source_left_active``）も。v0.93: きぜつで発生源がはなれた印を
    付けた記録（くいつく。``persistent_effect_source_left``）も。"""
    kind = event["kind"]
    return (kind == "persistent_effect_removed" and event.get("reason") in (KNOCK_OUT, SOURCE_LEFT_ACTIVE)) \
        or kind == "persistent_effect_source_left" \
        or (kind == "energy_returned_to_hand" and event.get("cause") == "knock_out") \
        or (kind == "color_effect_removed" and event.get("reason") == "target_gone")


def _prize_queue_problems(state: GameState, queue: tuple[int, ...]) -> list[str]:
    """サイドを取るプレイヤーの並び（決定するプレイヤーと残り。v0.4e）が、直前のきぜつから決まるか。

    解決の基盤の ``flow._after_knockouts``: きぜつ 1 匹につき、きぜつしたポケモンの相手側のプレイヤーが 1 枚（p.323）。残りのサイドより多くは
    取らない。ログの終わりから、取ったサイド（``take_prize``）・きぜつ（``knock_out``。あいだの ``persistent_effect_removed`` は
    きぜつで消えた持続する効果）の順に読み、取ったサイドと今の並びをあわせたものが、きぜつから決まる「だれが何枚取るか」と
    同じかを確かめる。同時のきぜつ（p.324）で両方が取る順番は番のプレイヤーが選べる（p.325。エンジンは番のプレイヤーからに
    正規化している。v0.2f）ので、順番は確かめない（正規化と違う順番の状態も、ルール上は正しい）。ログにきぜつがない状態は、
    盤面を直接作ったテスト専用の状態（``new_game`` からの対戦では違反）だけ。
    """
    taken: list[int] = []
    knocked: list[int] = []
    seen_knock_out = False
    for event in reversed(state.log):
        kind = event["kind"]
        if kind == "take_prize" and not seen_knock_out:
            taken.append(event.get("player"))
        elif kind == "knock_out":
            seen_knock_out = True
            if event.get("counted", True):  # v0.47: カウントされないきぜつ（なにかの化石・ピッピ人形）では、相手はサイドを取らない
                knocked.append(event.get("player"))
        elif kind == "energy_conversion" and not seen_knock_out:
            continue  # v0.59: ［エネエネ］できぜつしたマルマインのカードを、きぜつのすぐあと（サイドの前）にエネルギーとしてつけた
        elif _knockout_bookkeeping(event):
            continue
        else:
            break
    if not knocked:
        if any(state.decklists):
            return [f"サイドを取る決定 {queue} の前に、きぜつ（ログ knock_out）がない"]
        return []
    taken.reverse()
    knocked.reverse()
    budget = {player: len(state.players[player].prizes) + taken.count(player) for player in PLAYERS}
    expected = []
    for owner in knocked:
        taker = 1 - owner if owner in PLAYERS else None
        if taker in budget and budget[taker] > 0:
            expected.append(taker)
            budget[taker] -= 1
    if sorted(expected) != sorted((*taken, *queue)):
        return [
            f"サイドを取るプレイヤーの並び {queue}（取ったあと {tuple(taken)}）が、きぜつしたポケモンの持ち主 {tuple(knocked)} から"
            f"決まるサイドを取るプレイヤー {tuple(expected)} と違う（きぜつしたポケモンの相手側のプレイヤーが取る。p.323・p.324）"
        ]
    return []


def _attack_decision_problems(state: GameState, d) -> list[str]:
    """ワザの効果の途中の決定（``resume`` が ``"attack"``。v0.2a。v0.4d で強めた）の整合性。

    どのワザの決定にも共通: 続きの情報（``context`` の ``"use"`` = (プレイヤー, 場のポケモンの番号, カード id, ワザの位置)）が
    あり、ワザが効果の登録表にある。ワザを使ったプレイヤーは番のプレイヤー（相手が決定していても番は変わらない。v0.4d）で、
    ワザを使ったポケモンはそのプレイヤーのバトル場にいて、いちばん上のカードが続きの情報のカード id。今の番に、そのポケモンの
    そのワザのログ ``attack`` がちょうど 1 回ある（ワザは 1 番に 1 回。決定はワザの途中なので、番の終わりのログはまだない）。
    そのあとで、効果ごとの形（決定するプレイヤー・種類・選べるもの）を、ワザの実装の ``decision_problems`` で確かめる。
    """
    use = d.context_value("use")
    if _returned_attacker(state, d) is not None:
        # v0.38: ワザを使ったポケモンが、そのワザの効果で場をはなれたあとの決定（キョウのポッポの「でんれい」のかわりの対戦ポケモン・山札をさがす）。
        # 場にいないので、場の確かめのかわりに今の番のログ（ワザの宣言 → そのポケモンを山札にもどしたログ）で確かめた（``_returned_attacker``）
        player, pokemon_id, card_id, attack_index = use
        if player != state.current_player:
            return [f"場をはなれたポケモンのワザの決定の続き {use!r} が、番のプレイヤー {state.current_player!r} のワザではない"]
        entry = state.effects.attack_entry(card_id, attack_index)
        return _carried_deferred_problems(state, d, player) + entry.effect.decision_problems(
            state, AttackUse(player, pokemon_id, AttackKey(card_id, attack_index)), d)
    if not (isinstance(use, tuple) and len(use) == 4 and state.find_pokemon(use[1]) is not None):
        return [f"ワザの決定の続きの情報 {use!r} が正しくない"]
    player, pokemon_id, card_id, attack_index = use
    entry = state.effects.attack_entry(card_id, attack_index)
    if entry is None:
        return [f"ワザの決定の続きのワザ {card_id}#{attack_index} が効果の登録表にない"]
    owner, attacker = state.find_pokemon(pokemon_id)
    if player != state.current_player or owner != player or state.players[player].active is not attacker:
        return [f"ワザの決定の続きの情報 {use!r} が、番のプレイヤー {state.current_player!r} のバトル場のポケモンのワザではない"]
    attacks = [
        event for event in _events_since_turn_start(state)
        if event["kind"] == "attack" and event.get("player") == player
    ]
    declared_card = attacks[0].get("pokemon") if len(attacks) == 1 else None
    # v0.84: ワザの途中で、ワザを使ったポケモン自身が山札から進化した（やさしいプクリンの「しんかのうた」の段階 0 で自分を進化させ、段階 1 の相手の決定を待つ）。宣言したカードは
    # 重なりの下にあり、宣言のあとにそのポケモンの進化のログ（``effect`` がこのワザ）がある
    evolved_in_attack = (declared_card is not None and declared_card != attacker.card and declared_card in attacker.cards() and any(
        e["kind"] == "evolve" and e.get("pokemon_id") == pokemon_id and e.get("effect") is not None
        for e in _events_since_turn_start(state)[:_events_since_turn_start(state).index(attacks[0])]))
    if len(attacks) != 1 or (declared_card != attacker.card and not evolved_in_attack) or attacks[0].get("attack_index") != attack_index:
        return [f"ワザの決定の続き {use!r} に対応する、今の番のワザのログ attack がない（{len(attacks)} 回）"]
    # v0.49: 続きのカード id は、ワザを印刷したカード（ログ attack の ``card_id``。ワザの出どころがワザを使ったポケモンのいちばん上のカードと違うときだけ書く。
    # なければいちばん上のカード（v0.84: ワザの途中で進化したなら、宣言したカード））
    expected = attacks[0].get("card_id", state.cards[declared_card].card_id if declared_card in state.cards else None)
    if card_id != expected:
        return [f"ワザの決定の続きのカード id {card_id} が、ワザを使ったポケモン {pokemon_id} の使ったワザのカード {expected} と違う"]
    problems = _carried_deferred_problems(state, d, player) + _carried_flee_problems(state, d)
    if d.kind in (NINJA_TRICK, REACTION_SWITCH, BENCH_GUARD, ENERGY_DRAIN_DISCARD, SPLIT_FROM_DECK) or (
            d.kind in (REACTION_ORDER, MAGMA_POOL_ENERGY) and (d.context_value("move_order") is not None or d.context_value("move_magma") is not None)):
        # v0.87: ［ぶんれつ］の決定（SPLIT_FROM_DECK）・ワザの途中の場の移動への反応の決定（同じ時点の反応の順番・［やけのこり］のカード）も、どのワザでも出しうる
        # v0.68: ［だつりょくえき］のトラッシュするカードの決定（ENERGY_DRAIN_DISCARD）も、どのワザでも出しうる
        # v0.65: ワザの途中の任意の決定（変わり身の術・［にげこむ］・［ベンチガード］）は、どのワザでも出しうる（効果ごとの decision_problems ではなく、共通に確かめる）
        return problems + _reaction_decision_problems(state, d, player)
    if d.kind == DAMAGE_STEP_ORDER:
        # v0.35: ダメージの計算の順番の決定は、どのワザのダメージの要素も出しうる（効果ごとの decision_problems ではなく、共通に確かめる）
        return problems + _damage_order_decision_problems(state, d, player, attacker)
    if d.kind == DAMAGE_REDUCTION:
        # v0.66: お上品攻撃の減らす量の決定も、どのワザのダメージの要素も出しうる
        return problems + _damage_reduction_decision_problems(state, d, player, attacker)
    if d.kind == ESP_REDO:
        # v0.66: ナツメのESPのやり直しの決定も、説明文のコインを投げるどのワザも出しうる
        return problems + _esp_redo_decision_problems(state, d, player, attacker)
    return problems + entry.effect.decision_problems(state, AttackUse(player, pokemon_id, AttackKey(card_id, attack_index)), d)


def _with_attack_power(state: GameState, context: dict, attacker: PokemonInPlay, key: AttackKey, target: str, collected) -> tuple:
    """v0.88: 決定の続きの情報に、ワザといっしょに使った特殊能力（［すいりょくはつでん］）があれば、相手の対戦ポケモンへのダメージの 2 段階の追加を加えた変更効果（``kernel.attack_modifiers_of`` と同じ）。"""
    from .effects import OPPONENT_ACTIVE, attack_power_modifier

    if not context.get("attack_power") or target != OPPONENT_ACTIVE:
        return tuple(collected)
    extra = attack_power_modifier(state, attacker, key)
    return tuple(collected) + (() if extra is None else (extra,))


def _damage_reduction_decision_problems(state: GameState, d, player: int, attacker: PokemonInPlay) -> list[str]:
    """v0.66（docs/optional-trainers-v0.66.md 2 章）: お上品攻撃の減らす量の決定（``DAMAGE_REDUCTION``）。決めるのはワザを使ったプレイヤー、選ぶのは 1 つ。受けるポケモンは
    相手の対戦ポケモンで、続きの情報の基本となるダメージ・前に選んだ順番から今の場で計算し直すと、減らす量の決定が要り（``damage.DamageReductionRequired``）、選べるものが
    その選べる量と同じ。ワザを使ったポケモンに、お上品攻撃（``reduces_attack_damage``）がついている。"""
    from .damage import DamageReductionRequired
    from .effects import (
        OPPONENT_ACTIVE,
        attack_damage_modifiers,
        attack_ignores_resistance,
        calculate_with_stadium,
        stadium_coin_modifier,
    )

    context = dict(d.context)
    base, target = context.get("base"), context.get("target")
    if d.player != player or (d.min_choices, d.max_choices) != (1, 1):
        return [f"減らす量の決定を決めるのがプレイヤー {d.player}・選ぶ数 {(d.min_choices, d.max_choices)}（ワザを使ったプレイヤー {player}・1 つのはず）"]
    if target != OPPONENT_ACTIVE or type(base) is not int:
        return [f"減らす量の決定の続きの情報（受けるポケモン {target!r}・基本となるダメージ {base!r}）が正しくない"]
    receiver = state.players[1 - player].active
    if receiver is None or receiver.pokemon_id != context.get("receiver"):
        return [f"減らす量の決定の受けるポケモン {context.get('receiver')!r} が、相手の対戦ポケモンではない"]
    reducers = tuple(t.card for t in attacker.trainers if state.effects.trainer_entry(state.cards[t.card].card_id).effect.reduces_attack_damage)
    if tuple(context.get("reducers", ())) != reducers[:len(tuple(context.get("reducers", ())))] or not reducers:
        return [f"減らす量の決定のお上品攻撃 {context.get('reducers')!r} が、ワザを使ったポケモンについているカード {reducers} と合わない"]
    copied = context.get("copied")
    use = d.context_value("use")
    key = AttackKey(*copied) if copied is not None else AttackKey(use[2], use[3])
    orders = {k: tuple(v) for k, v in context.get("orders", ())}
    collected = attack_damage_modifiers(state, attacker, receiver, attack=key, attack_status=frozenset(context.get("attack_status", ())))
    collected = _with_attack_power(state, context, attacker, key, target, collected)  # v0.88
    coin = context.get("stadium_coin")
    if coin is not None and coin[1]:
        collected = (*collected, stadium_coin_modifier(state, coin[0]))
    try:
        calculate_with_stadium(state, base, definition_views(state, attacker)[0], definition_views(state, receiver)[0], collected,
                               weakness_resistance=context.get("weakness_resistance", True), orders=orders,
                               resistance=context.get("resistance", True) and attack_ignores_resistance(state, attacker, receiver) is None)
    except DamageReductionRequired as need:
        if tuple(d.options) != need.choices or context.get("value") != need.value:
            return [f"減らす量の決定の選べるもの {d.options!r}（5 段階のダメージ {context.get('value')!r}）が、今の場の計算の {need.choices}（{need.value}）と違う"]
        return []
    except Exception as error:  # noqa: BLE001  順番の決定・色の読み方は、減らす量の決定より先に決まっている。計算し直せない理由は何でも不変条件の違反として返す
        return [f"減らす量の決定の続きの情報で計算し直せない（{error}）"]
    return ["減らす量の決定の続きの情報で計算し直すと、減らす量の決定は要らない"]


def _esp_redo_decision_problems(state: GameState, d, player: int, attacker: PokemonInPlay) -> list[str]:
    """v0.66（docs/optional-trainers-v0.66.md 3 章）: ナツメのESPのやり直しの決定（``ESP_REDO``）。決めるのはワザを使ったプレイヤー、選べるものは (1,)・0〜1 個。続きの情報の
    ``esp`` の ESP のカードが、ワザを使ったポケモンについているESPと同じで、最初の結果の枚数が投げた枚数と同じ。今の番のログの最後のコインの結果（``coin_flip``）が、最初の
    結果と同じ並び。"""
    from .effects import esp_cards

    esp = d.context_value("esp")
    if d.player != player or tuple(d.options) != (1,) or (d.min_choices, d.max_choices) != (0, 1):
        return [f"ESPのやり直しの決定の形（決める {d.player}・選べるもの {d.options}・{d.min_choices}〜{d.max_choices}）が正しくない"]
    if not (isinstance(esp, tuple) and len(esp) == 6):
        return [f"ESPのやり直しの続きの情報 {esp!r} が正しくない"]
    _index, count, _by_heads, flipper, original, cards = esp
    if tuple(cards) != esp_cards(state, attacker) or not cards:
        return [f"ESPのやり直しのカード {cards!r} が、ワザを使ったポケモンについているESP {esp_cards(state, attacker)} と違う"]
    if type(count) is not int or count < 1 or len(original) != count or flipper not in (0, 1):
        return [f"ESPのやり直しの最初の結果 {original!r}（{count!r} 枚・投げたプレイヤー {flipper!r}）が正しくない"]
    flips = [e for e in _events_since_turn_start(state) if e["kind"] == "coin_flip"][:count]  # 新しい順
    if tuple(e.get("result") for e in reversed(flips)) != tuple(original) or any(e.get("player") != flipper or e.get("source") != "attack" for e in flips):
        return [f"ESPのやり直しの最初の結果 {original!r} が、今の番の最後のワザのコイン {[e.get('result') for e in reversed(flips)]} と違う"]
    return []


def _reaction_decision_problems(state: GameState, d, player: int) -> list[str]:
    """v0.65（docs/reactive-decisions-v0.65.md 2 章）: ワザの途中の任意の決定の形。

    - 変わり身の術（``NINJA_TRICK``）: 決めるのはワザを受ける側（番でないプレイヤー）。続きの情報の位置は 0（ワザの要素の前）・変わり身の術は、そのプレイヤーのバトル場の
      ポケモンについている「バトル場をはなれた時にトラッシュする」カードと同じ。選べるものはそのプレイヤーの控えの番号・0〜1 個
    - ［にげこむ］（``REACTION_SWITCH``）: 決めるのは持ち主。そのポケモンが持ち主のバトル場にいて、今その特殊能力を持つ。選べるものは持ち主の控えの番号・0〜1 個
    - ［ベンチガード］（``BENCH_GUARD``）: 決めるのはダメージを受ける控えポケモンの持ち主。選べるものは、そのポケモン以外の、使える［ベンチガード］を持つ控えのポケモン（場の並び）・
      0〜min(数, 運んだダメージの並びの数で決まる上限) 個
    """
    from .effects import bench_guard_holders, ninja_tricks, powers_of

    problems: list[str] = []
    owner = d.player
    bench = tuple(p.pokemon_id for p in state.players[owner].bench)
    if d.kind == NINJA_TRICK:
        active = state.players[owner].active
        tricks = d.context_value("tricks")
        if owner != 1 - player or d.context_value("boundary") != 0:
            problems.append(f"変わり身の術の決定 {d.id} の決めるプレイヤー・位置が正しくない")
        if active is None or not tricks or tuple(tricks) != ninja_tricks(state, active):
            problems.append(f"変わり身の術の決定 {d.id} の変わり身の術 {tricks} が、プレイヤー {owner} のバトル場のポケモンについているものと違う")
        if d.options != bench or (d.min_choices, d.max_choices) != (0, 1):
            problems.append(f"変わり身の術の決定 {d.id} の選べるもの {d.options}（{d.min_choices}〜{d.max_choices}）が、控え {bench} の 0〜1 個ではない")
        return problems
    if d.kind == REACTION_SWITCH:
        entry = d.context_value("flee")
        if not (isinstance(entry, tuple) and len(entry) == 4) or entry[0] != owner:
            return [f"［にげこむ］の決定 {d.id} の続きの情報 {entry!r} が正しくない"]
        _, pid, card_id, power_index = entry
        active = state.players[owner].active
        if active is None or active.pokemon_id != pid or not any(slot.key == PowerKey(card_id, power_index) for slot in powers_of(state, active)):
            problems.append(f"［にげこむ］の決定 {d.id} のポケモン {pid} が、プレイヤー {owner} のバトル場にいない・特殊能力を持たない")
        if not isinstance(d.context_value("boundary"), int):
            problems.append(f"［にげこむ］の決定 {d.id} に、続ける要素の位置がない")
        if d.options != bench or (d.min_choices, d.max_choices) != (0, 1):
            problems.append(f"［にげこむ］の決定 {d.id} の選べるもの {d.options}（{d.min_choices}〜{d.max_choices}）が、控え {bench} の 0〜1 個ではない")
        return problems
    if d.kind == SPLIT_FROM_DECK:
        # v0.87: ［ぶんれつ］。決めるのは持ち主。そのポケモンが持ち主の場にいて、今その特殊能力を持つ。選べるものは山札の名前の合うたねポケモン（uid の小さい順）・0〜1 枚
        # （選べるカードがなければ 0〜0）。持ち主のベンチに空きがある
        from .effects import deck_named_basics

        entry = d.context_value("split")
        if not (isinstance(entry, tuple) and len(entry) == 5) or entry[0] != owner:
            return [f"［ぶんれつ］の決定 {d.id} の続きの情報 {entry!r} が正しくない"]
        _, pid, card_id, power_index, name = entry
        holder = state.find_pokemon(pid)
        if holder is None or holder[0] != owner or not any(slot.key == PowerKey(card_id, power_index) for slot in powers_of(state, holder[1])):
            problems.append(f"［ぶんれつ］の決定 {d.id} のポケモン {pid} が、プレイヤー {owner} の場にいない・特殊能力を持たない")
        options = tuple(deck_named_basics(state, owner, name))
        if d.options != options or (d.min_choices, d.max_choices) != (0, 1 if options else 0) or not isinstance(d.context_value("boundary"), int):
            problems.append(f"［ぶんれつ］の決定 {d.id} の選べるもの {d.options}（{d.min_choices}〜{d.max_choices}）が、山札の「{name}」{options} の 0〜1 枚ではない")
        if not bench_has_room(state, owner):
            problems.append(f"［ぶんれつ］の決定 {d.id} のプレイヤー {owner} のベンチに空きがない")
        return problems
    if d.kind in (REACTION_ORDER, MAGMA_POOL_ENERGY):
        # v0.87: ワザの途中の場の移動への反応の決定。順番は番のプレイヤー、［やけのこり］のカードは持ち主（反応ごとの形は ``reactions.answer_problems`` と同じ確かめ）
        from . import movement

        if not isinstance(d.context_value("boundary"), int) or not d.options:
            problems.append(f"場の移動への反応の決定 {d.id} に、続ける要素の位置・選べるものがない")
        if d.kind == REACTION_ORDER and owner != state.current_player:
            problems.append(f"同じ時点の反応の順番の決定 {d.id} を決めるのが番のプレイヤーではない")
        magma = d.context_value("move_magma")
        if d.kind == MAGMA_POOL_ENERGY:
            if not (isinstance(magma, tuple) and len(magma) == 7 and magma[0] == movement.MAGMA and magma[1] == owner):
                problems.append(f"［やけのこり］の決定 {d.id} の続きの情報 {magma!r} が正しくない")
            elif (d.min_choices, d.max_choices) != (1, 1):
                problems.append(f"［やけのこり］の決定 {d.id} の選ぶ数 {d.min_choices}〜{d.max_choices} が 1 枚ではない")
        return problems
    if d.kind == ENERGY_DRAIN_DISCARD:
        # v0.68: ［だつりょくえき］。決めるのは持ち主。そのポケモンが持ち主の場にいて、今その特殊能力を持つ。ダメージを与えたポケモンが場にいて、選べるものはそのポケモンに
        # ついているエネルギーカード（ついている順）のちょうど 1 個
        entry = d.context_value("drain")
        if not (isinstance(entry, tuple) and len(entry) == 5) or entry[0] != owner:
            return [f"［だつりょくえき］の決定 {d.id} の続きの情報 {entry!r} が正しくない"]
        _, pid, card_id, power_index, source_pid = entry
        holder = state.find_pokemon(pid)
        if holder is None or holder[0] != owner or not any(slot.key == PowerKey(card_id, power_index) for slot in powers_of(state, holder[1])):
            problems.append(f"［だつりょくえき］の決定 {d.id} のポケモン {pid} が、プレイヤー {owner} の場にいない・特殊能力を持たない")
        source = state.find_pokemon(source_pid)
        if source is None or source[0] == owner:
            return problems + [f"［だつりょくえき］の決定 {d.id} のダメージを与えたポケモン {source_pid} が、相手の場にいない"]
        if not isinstance(d.context_value("boundary"), int):
            problems.append(f"［だつりょくえき］の決定 {d.id} に、続ける要素の位置がない")
        if d.options != tuple(source[1].energy) or not d.options or (d.min_choices, d.max_choices) != (1, 1):
            problems.append(f"［だつりょくえき］の決定 {d.id} の選べるもの {d.options}（{d.min_choices}〜{d.max_choices}）が、ポケモン {source_pid} のエネルギーカードの 1 個ではない")
        return problems
    carried = d.context_value("bench_guard")
    if not (isinstance(carried, tuple) and len(carried) == 3 and carried[0]):
        return [f"［ベンチガード］の決定 {d.id} の続きの情報 {carried!r} が正しくない"]
    receiver_pid = carried[0][0][1]
    located = state.find_pokemon(receiver_pid)
    if located is None or located[0] != owner or not any(p is located[1] for p in state.players[owner].bench):
        return [f"［ベンチガード］の決定 {d.id} のダメージを受けるポケモン {receiver_pid} が、プレイヤー {owner} の控えにいない"]
    holders = tuple(p.pokemon_id for p, _ in bench_guard_holders(state, owner, located[1]))
    if d.options != holders or d.min_choices != 0 or not 1 <= d.max_choices <= len(holders) or not isinstance(d.context_value("element"), int):
        problems.append(f"［ベンチガード］の決定 {d.id} の選べるもの {d.options}（0〜{d.max_choices}）が、使えるサイドン {holders} と合わない")
    return problems


def _carried_flee_problems(state: GameState, d) -> list[str]:
    """v0.65: ワザの途中の決定が運ぶ、［にげこむ］のまだ聞いていない候補（``frame`` の ``flee``）と入れ替えたポケモン（``fled``。もと → かわり）。候補は場のポケモンの番号で、
    入れ替えたポケモンはどちらも、持ち主の場にいる（かわりのポケモンはこのワザの効果を受けないので、決定を待つ間は動かない）。"""
    frame = dict(d.context_value("frame") or ())
    problems: list[str] = []
    for entry in frame.get("flee", ()):
        if not (isinstance(entry, tuple) and len(entry) == 5) or state.find_pokemon(entry[1]) is None:
            problems.append(f"運んだ［にげこむ］の候補 {entry!r} が正しくない")
    for orig, new in frame.get("fled", ()):
        a, b = state.find_pokemon(orig), state.find_pokemon(new)
        if a is None or b is None or a[0] != b[0]:
            problems.append(f"運んだ［にげこむ］の入れ替え {orig} → {new} のポケモンが、同じ持ち主の場にいない")
    # v0.89: 先に選んだ個体（``chosen_targets`` の (名前, 番号) か (名前, 番号, 持ち主)）。名前は重ならない。持ち主を運ぶなら 0 か 1 で、その個体が場にいれば持ち主の場にいる
    # （場をはなれた個体は、あとの要素が何もしない。今の対戦ポケモン・同じ名前の別の個体にすり替えない）
    names = []
    for entry in d.context_value("chosen_targets") or ():
        if not (isinstance(entry, tuple) and len(entry) in (2, 3) and isinstance(entry[0], str) and (entry[1] is None or isinstance(entry[1], int))):
            problems.append(f"運んだ選んだ個体 {entry!r} の形が正しくない")
            continue
        names.append(entry[0])
        if len(entry) == 3:
            located = None if entry[1] is None else state.find_pokemon(entry[1])
            if entry[2] not in (0, 1) or (located is not None and located[0] != entry[2]):
                problems.append(f"運んだ選んだ個体 {entry!r} の持ち主が、そのポケモンの持ち主と違う")
    if len(names) != len(set(names)):
        problems.append(f"運んだ選んだ個体の名前 {names} が重なる")
    return problems


def _returned_attacker(state: GameState, d) -> dict | None:
    """v0.38: ワザの途中の決定（``resume`` が ``"attack"``）で、ワザを使ったポケモンがそのワザの効果で場をはなれているなら、そのポケモンを山札にもどした
    ログ（``return_in_play_to_deck``）。そうでなければ None。

    許すのは、続きのワザ（相手のワザを自分のワザとして使っていれば、そのワザ）の実装が ``leaves_play_before_decisions``（場をはなれたあとに決定を出す。
    キョウのポッポの「でんれい」）で、続きのポケモンが場になく、今の番にそのプレイヤーのワザの宣言がちょうど 1 回あり、そのあとに、そのポケモン
    （同じ番号・宣言と同じいちばん上のカード）を同じワザの効果で山札にもどしたログがちょうど 1 回あるときだけ（広げない）。"""
    use = d.context_value("use")
    if d.resume != "attack" or not (isinstance(use, tuple) and len(use) == 4) or state.find_pokemon(use[1]) is not None:
        return None
    player, pokemon_id, card_id, attack_index = use
    copied = d.context_value("copied")
    key = AttackKey(*copied) if isinstance(copied, tuple) and len(copied) == 2 else AttackKey(card_id, attack_index)
    entry, declared = state.effects.attack_entry(key.card_id, key.attack_index), state.effects.attack_entry(card_id, attack_index)
    if entry is None or declared is None or not entry.effect.leaves_play_before_decisions:
        return None
    events = list(reversed(_events_since_turn_start(state)))  # 古い順
    attacks = [i for i, event in enumerate(events) if event["kind"] == "attack" and event.get("player") == player]
    if len(attacks) != 1 or events[attacks[0]].get("attack_index") != attack_index:
        return None
    returned = [event for event in events[attacks[0] + 1:] if event["kind"] == "return_in_play_to_deck" and event.get("pokemon_id") == pokemon_id]
    # v0.49: 続きのカード id は、ワザを印刷したカード（ログ attack の ``card_id``。［へんしん］・「思い出させる」などで、いちばん上のカードと違うときだけ書く）
    if len(returned) != 1 or returned[0].get("player") != player or returned[0].get("effect") != str(key) \
            or returned[0].get("pokemon") != events[attacks[0]].get("pokemon") \
            or events[attacks[0]].get("card_id", state.cards[returned[0]["pokemon"]].card_id) != card_id:
        return None
    return returned[0]


def _damage_order_decision_problems(state: GameState, d, player: int, attacker: PokemonInPlay) -> list[str]:
    """v0.35: ワザのダメージの計算（p.321）の同じ段階の順番の決定（``DAMAGE_STEP_ORDER``。``resolution.programs.suspend_step_order``）。

    続きの情報の段階・受けるポケモン・基本となるダメージ・前に選んだ段階の順番から、今の場で変更効果を集め直し（``effects.attack_damage_modifiers``）、
    その段階の変更効果が続きの情報と同じで、その順番がまだ選ばれておらず、順番によって計算の結果が変わる（``damage.DamageOrderRequired``）ことと、
    決めるプレイヤー（2・5・6 段階はワザを使うプレイヤー、7・8 段階は受けるポケモンの持ち主。p.321）・選べるもの（並べかえの位置）・選ぶ数を確かめる。"""
    from .damage import DAMAGE_STEP_CHOOSER, DamageOrderRequired, step_orders
    from .effects import calculate_with_stadium
    from .effects import OPPONENT_ACTIVE, SELF, attack_damage_modifiers, attack_ignores_resistance

    context = dict(d.context)
    step, target, base = context.get("step"), context.get("target"), context.get("base")
    modifiers, permutations = context.get("modifiers"), context.get("permutations")
    orders = {k: tuple(v) for k, v in context.get("orders", ())}
    if step not in DAMAGE_STEP_CHOOSER or target not in (OPPONENT_ACTIVE, SELF) or type(base) is not int or not isinstance(modifiers, tuple):
        return [f"順番の決定の続きの情報（段階 {step!r}・受けるポケモン {target!r}・基本となるダメージ {base!r}）が正しくない"]
    if step in orders:
        return [f"順番の決定の段階 {step} の順番が、すでに選ばれている"]
    if tuple(tuple(order) for order in permutations or ()) != step_orders(len(modifiers)) or d.options != tuple(range(len(step_orders(len(modifiers))))):
        return [f"順番の決定の選べるもの {d.options!r} が、{len(modifiers)} つの変更効果の並べかえの位置ではない"]
    if (d.min_choices, d.max_choices) != (1, 1):
        return [f"順番の決定の選ぶ数 {(d.min_choices, d.max_choices)!r} が 1 つではない"]
    owner, receiver = (1 - player, state.players[1 - player].active) if target == OPPONENT_ACTIVE else (player, attacker)
    if receiver is None or receiver.pokemon_id != context.get("receiver"):
        return [f"順番の決定の受けるポケモン {context.get('receiver')!r} が、場の {target} ではない"]
    chooser = player if DAMAGE_STEP_CHOOSER[step] == "attacker" else owner
    if d.player != chooser:
        return [f"{step} 段階の順番を選ぶのがプレイヤー {d.player} で、{DAMAGE_STEP_CHOOSER[step]} のプレイヤー {chooser} ではない（p.321）"]
    copied = context.get("copied")
    use = d.context_value("use")
    key = AttackKey(*copied) if copied is not None else AttackKey(use[2], use[3])
    # v0.46: ワザが使われた時の特殊状態（くつろぐかおり）は、決定の続きの情報で運んだ値（書いていなければ空）
    collected = attack_damage_modifiers(state, attacker, receiver, attack=key, attack_status=frozenset(context.get("attack_status", ())))
    collected = _with_attack_power(state, context, attacker, key, target, collected)  # v0.88
    at_step = tuple(m for m in collected if m.step == step)
    if tuple((m.label, m.source, m.operation, m.amount) for m in at_step) != modifiers:
        return [f"順番の決定の {step} 段階の変更効果 {modifiers!r} が、今の場で集めた効果と違う"]
    try:
        calculate_with_stadium(state, base, definition_views(state, attacker)[0], definition_views(state, receiver)[0], collected,
                                weakness_resistance=context.get("weakness_resistance", True), orders=orders,
                                resistance=context.get("resistance", True) and attack_ignores_resistance(state, attacker, receiver) is None)
    except DamageOrderRequired as need:
        if need.step == step:
            return []
        return [f"順番の決定の段階 {step} が、計算で順番の要る段階 {need.step} と違う"]
    except ValueError as error:
        return [f"順番の決定の前に選んだ順番 {orders!r} が正しくない（{error}）"]
    return [f"{step} 段階の順番は、どの順番でも計算の結果が同じ（決定は要らない）"]


def _carried_deferred_problems(state: GameState, d, player: int) -> list[str]:
    """v0.34: ワザの途中の決定が運ぶ、まだ処理していない送る効果（続きの情報の ``frame`` の ``pending``。「ダメージを受けたとき」の効果）。

    1 つずつ (持ち主, 持つポケモンの番号, 効果の定義の名前, 受けたダメージ) で、持ち主の場のそのポケモンに、その名前の送る効果がちょうど 1 つあり
    （``resolution.catalog``）、相手のワザで受ける効果なら持ち主はワザを使ったプレイヤーでなく、今の番のワザの宣言のあとに、そのポケモンが受けた
    同じ量のダメージのログ ``damage`` がある（印や一覧を状態に加えず、ログで確かめる）。"""
    frame = d.context_value("frame")
    if frame is None:
        return []
    pending = dict(frame).get("pending", ())
    if not pending:
        return []
    from .resolution.kernel import REFLECT_SHIELD_RETURN, carried_instances

    problems: list[str] = []
    recent = _events_since_turn_start(state)  # 新しい順
    since_attack = recent[:next((i for i, e in enumerate(recent) if e["kind"] == "attack"), len(recent))]
    seen = set()
    for entry in pending:
        if not (isinstance(entry, tuple) and len(entry) == 4):
            problems.append(f"運んだ送る効果 {entry!r} の形が正しくない")
            continue
        owner, pokemon_id, name, received = entry
        if (pokemon_id, name) in seen:
            problems.append(f"運んだ送る効果 {name}（ポケモン {pokemon_id}）が 2 つ")
        seen.add((pokemon_id, name))
        located = state.find_pokemon(pokemon_id)
        if located is None or located[0] != owner:
            problems.append(f"運んだ送る効果 {name} の持ち主 {owner} のポケモン {pokemon_id} が場にいない")
            continue
        pokemon = located[1]
        matches = carried_instances(state, owner, pokemon, name)
        if len(matches) != 1:
            problems.append(f"運んだ送る効果 {name} が、ポケモン {pokemon_id} に {len(matches)} つある")
            continue
        if matches[0].definition.by_opponent and owner == player:
            problems.append(f"相手のワザで受ける送る効果 {name} の持ち主が、ワザを使ったプレイヤー {player}")
        if name == REFLECT_SHIELD_RETURN.name:
            # v0.84（A1）: 「リフレクトシールド」の「おもて」の 20。持ち主は受ける側（ワザを使ったプレイヤーでない）で、そのポケモンはダメージを受けていない。受けたダメージの
            # かわりに、コインの時点のダメージを与えたポケモンのダメージ（0 でもよい。与える時点と違えば RS1）を運び、今の番のワザの宣言のあとに、そのポケモンの「おもて」のログがある
            if owner == player or type(received) is not int or received < 0 or not any(
                    e["kind"] == "reflect_shield_check" and e.get("pokemon_id") == pokemon_id and e.get("reflected") for e in since_attack):
                problems.append(f"運んだ「リフレクトシールド」の 20（ポケモン {pokemon_id}・{received!r}）に対応する、今の番のワザの宣言のあとの「おもて」のログがない")
            continue
        if not (type(received) is int and received > 0) or not any(
                e["kind"] == "damage" and e.get("player") == owner and e.get("pokemon") == pokemon.card and e.get("amount") == received
                for e in since_attack):
            problems.append(f"運んだ送る効果 {name} の受けたダメージ {received!r} に対応する、今の番のワザの宣言のあとのログ damage がない")
    return problems


def _attached_trainer_problems(state: GameState, player: int, pokemon: PokemonInPlay, place) -> list[str]:
    """ポケモンについているトレーナーカード（v0.2c）。

    ついているトレーナーは、そのポケモンのいる場所にある（p.313）ので、ポケモンの持ち主の場のカードとして
    数える。効果の登録表に、場に残る実装（``stays_in_play``）が登録されたトレーナーだけがつく。
    有効期限が過ぎたもの（番の終わりにトラッシュしていないもの）は残らない（終わった対戦は除く）。
    """
    problems: list[str] = []
    tools = [attached.card for attached in pokemon.trainers if attached.card in state.cards and is_pokemon_tool_card(state, attached.card)]
    if len(tools) > 1:
        # v0.81: 「すでに「ポケモンのどうぐ」をつけているポケモンには、つけることができない」（1 匹に 1 枚まで。どうぐでないついているトレーナーはいっしょにつく）
        problems.append(f"ポケモン {pokemon.pokemon_id} に、ポケモンのどうぐが {len(tools)} 枚ついている（{tools}。1 匹に 1 枚まで）")
    for attached in pokemon.trainers:
        place(attached.card, player, "場（ついているトレーナー）")
        if attached.card not in state.cards:
            continue
        definition = state.card_def(attached.card)
        if definition.category != "trainer":
            problems.append(f"トレーナーカードでないカード {attached.card} がトレーナーとしてポケモンについている")
            continue
        if attached.player != player:
            problems.append(f"ついているトレーナー {attached.card} の使ったプレイヤー {attached.player} が、ポケモンの持ち主 {player} と違う")
        entry = state.effects.trainer_entry(definition.id)
        if entry is None or not entry.effect.stays_in_play:
            problems.append(f"ついているトレーナー {attached.card}（{definition.id}）に、場に残る実装が登録されていない")
        if state.phase in TERMINAL_PHASES:
            continue
        if attached.discard_at_end_of_turn is None:
            # v0.59: 有効期限のないついているトレーナー（タケシの保護。場をはなれるまでついたまま）。登録の実装の ``discard_turn_offset`` も None
            if entry is not None and entry.effect.discard_turn_offset is not None:
                problems.append(f"ついているトレーナー {attached.card} に有効期限がないが、登録の実装 {definition.id} は有効期限のあるトレーナー")
            continue
        if entry is not None and entry.effect.discard_turn_offset is None:
            problems.append(f"ついているトレーナー {attached.card} に有効期限があるが、登録の実装 {definition.id} は場をはなれるまでついたままのトレーナー")
        if attached.discard_at_end_of_turn < state.turn_number:
            problems.append(f"ついているトレーナー {attached.card} の有効期限（{attached.discard_at_end_of_turn} 番の終わり）が過ぎている")
        elif entry is not None and entry.effect.stays_in_play:
            # 有効期限は、使った番 + discard_turn_offset（v0.2e）。使った番は今の番より後ではなく、使ったプレイヤーの番
            offset = entry.effect.discard_turn_offset
            used_on = attached.discard_at_end_of_turn - offset
            if used_on > state.turn_number:
                problems.append(
                    f"ついているトレーナー {attached.card} の有効期限（{attached.discard_at_end_of_turn} 番の終わり）が、"
                    f"今の番 {state.turn_number} から {offset} 番より先"
                )
            elif state.first_player in PLAYERS and turn_owner(state, used_on) != attached.player:
                problems.append(
                    f"ついているトレーナー {attached.card} を使った番（{used_on} 番）が、使ったプレイヤー {attached.player} の番ではない"
                )
    return problems


def _trainer_problems(state: GameState) -> list[str]:
    """使用中のトレーナー（v0.2b）と、決定・段階の整合性。

    トレーナーカードが使用中なのは、そのトレーナーの効果が決定を待っている間だけ（決定がなければ、
    説明にしたがい終わってトラッシュしている）。共通の確認（使用中のトレーナー・続きの情報・番のプレイヤー）のあとで、
    決定の形（決定するプレイヤー・種類・選ぶ数・選べるもの）を、トレーナーの実装の ``decision_problems`` で確かめる（v0.4e。
    それまでは確かめておらず、相手の場のポケモンが選べるものに入った壊れた状態を見つけられなかった）。
    """
    problems: list[str] = []
    used = state.trainer_in_use
    d = state.decision
    waiting = d is not None and d.resume == "trainer"
    # v0.43: トレーナーの効果の途中で場に出たポケモンの特殊能力の決定（再開先 "power"。もどる先 "return_to" がこのトレーナー）を待つ間も、使用中のまま
    returning = d is not None and d.resume == "power" and d.context_value("return_to") is not None
    # v0.57: トレーナーの効果の途中で進化させたポケモンのトキワシティジムの決定（再開先 "stadium"。続き then のもどる先がこのトレーナー）を待つ間も、使用中のまま
    healing = d is not None and d.resume == "stadium" and d.context_value("stage") == "evolution_heal" and tuple((d.context_value("after_heal") or ((), (), ()))[2])
    if used is None:
        if state.trainer_stack:
            problems.append(f"外側のトレーナー {state.trainer_stack} があるのに、使用中の（内側の）トレーナーがない")
        if waiting:
            problems.append("トレーナーの決定を待っているのに、使用中のトレーナーがない")
        if returning:
            problems.append(f"特殊能力の決定のもどる先 {d.context_value('return_to')!r} があるのに、使用中のトレーナーがない")
        if healing:
            problems.append(f"トキワシティジムの決定のもどる先 {d.context_value('then')!r} があるのに、使用中のトレーナーがない")
        if d is not None and any(step[0] == reactions.TRAINER for step in d.context_value(reactions.FOLLOWUP, ())):
            problems.append("決定の続きにトレーナーを使い終える段があるのに、使用中のトレーナーがない")  # v0.86
        return problems
    problems.extend(_trainer_stack_problems(state, used))
    # v0.86: 続き（``reactions`` の ``followup``）の段にこのトレーナーを使い終える段がある決定（トレーナーの効果で場に出した・進化させたことへの反応、特殊能力のあとのきぜつ・サイド・
    # バトル場に出す決定）を待つ間も、使用中のまま
    followup = () if d is None else tuple(d.context_value(reactions.FOLLOWUP, ()))
    pending_finish = [step for step in followup if step[0] == reactions.TRAINER]
    if pending_finish:
        expected = (reactions.TRAINER, used.using_player, used.card, state.card_def(used.card).id)
        if tuple(pending_finish[0]) != expected:
            problems.append(f"決定の続きのトレーナーの段 {pending_finish[0]!r} が、使用中のトレーナー {expected} と違う")
        return problems
    if returning or healing:
        expected = ("trainer", used.using_player, used.card, state.card_def(used.card).id)
        back = tuple(d.context_value("return_to")) if returning else tuple(d.context_value("after_heal")[2])
        if back != expected:
            problems.append(f"決定のもどる先 {back!r} が、使用中のトレーナー {expected} と違う")
        return problems
    if not waiting:
        problems.append(f"使用中のトレーナー {used.card} があるのに、その効果の決定を待っていない")
        return problems
    if used.via is None and used.player != state.current_player:
        problems.append(f"使用中のトレーナーの持ち主 {used.player} が、番のプレイヤー {state.current_player} ではない")
    if used.via is None and used.user is not None and (used.user not in PLAYERS or used.user == used.player or stadium_of(state, TrainerCoinStadium) is None):
        # v0.57: 借りて使っているのは、場の錯乱ジムで、持ち主の相手プレイヤーだけ
        problems.append(f"使用中のトレーナー {used} を借りて使っているプレイヤーが正しくない（錯乱ジムで、持ち主の相手だけ）")
    use = d.context_value("use")
    if not (isinstance(use, tuple) and len(use) == 3):
        problems.append(f"トレーナーの決定の続きの情報 {use!r} が正しくない")
        return problems
    player, card, card_id = use
    stage = "chaos" if d.context_value("chaos") is not None else "stadium_cost" if d.context_value("stadium_cost") is not None else None
    if stage is not None:
        # v0.57: スタジアムがトレーナーの使用に加えた段階（錯乱ジムの問い・リムーブ禁止ジムの追加の条件）。続きの情報は持ち主の使用で、まだ借りていない
        # v0.58: 外側のトレーナーの効果で使っているカードは、使うプレイヤー（持ち主ではない）の使用
        starter = used.using_player if used.via is not None else used.player
        if (player, card) != (starter, used.card) or (used.via is None and used.user is not None):
            problems.append(f"スタジアムの段階 {stage} の続きの情報 {use!r} が、使用中のトレーナー {used} と違う")
        if stage == "chaos":
            if stadium_of(state, TrainerCoinStadium) is None or d.context_value("chaos") != state.stadium.card:
                problems.append("錯乱ジムの問いを待っているのに、場に錯乱ジムがない")
            if (d.kind, d.player, d.options, d.min_choices, d.max_choices) != (ACCEPT_REQUEST, 1 - starter, (1,), 0, 1):
                problems.append(f"錯乱ジムの問い {d.kind} {d.player} {d.options} が、相手プレイヤーへの問い（1 = 使う。0〜1 個）ではない")
        else:
            found = stadium_trainer_cost(state, state.card_def(card))
            if found is None or d.context_value("stadium_cost") != found[0].card:
                problems.append("リムーブ禁止ジムの追加の条件を待っているのに、場にリムーブ禁止ジムがない")
            elif (d.kind, d.player, d.options, d.min_choices, d.max_choices) != (
                    DISCARD_FROM_HAND, starter, tuple(state.players[starter].hand), found[1].discard, found[1].discard):
                problems.append(f"リムーブ禁止ジムの追加の条件の決定 {d.kind} {d.options} が、手札から {found[1].discard} 枚ではない")
        return problems
    if (player, card) != (used.using_player, used.card):
        problems.append(f"トレーナーの決定の続きの情報 {use!r} が、使用中のトレーナー {used} と違う")
    if card in state.cards and state.cards[card].card_id != card_id:
        problems.append(f"トレーナーの決定の続きのカード id {card_id} が、カード {card} と違う")
    entry = state.effects.trainer_entry(card_id)
    if entry is None:
        problems.append(f"トレーナーの決定の続きのカード {card_id} が効果の登録表にない")
        return problems
    if not problems:
        # 効果ごとの決定の形（決定するプレイヤー・種類・選ぶ数・選べるもの。v0.4e。ワザの決定の decision_problems と同じ考え方）
        problems.extend(entry.effect.decision_problems(state, TrainerUse(player, card, card_id), d))
    return problems

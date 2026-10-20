"""特殊状態（v0.3a〜v0.3c。p.322「10 ポケモンの特殊状態」）を付ける・消す処理。

v0.3a で「どく」、v0.3b で「ねむり」「マヒ」、v0.3c で「こんらん」を加えた。こんらんによるワザのコイン・20 ダメージ・
にげるのコインはエンジン（ワザは解決の基盤の ``resolution.flow``、にげるは ``engine._retreat``）が行う（ここにあるのは付ける処理と、
20 ダメージの量）。

- 特殊状態になるのはバトル場のポケモン（対戦ポケモン）だけ。ベンチのポケモンは特殊状態にならない（p.322）。
- 特殊状態のポケモンがバトル場をはなれたら（ベンチに戻ったら）、すべての特殊状態は消える（p.311・p.322）。
  にげる・ポケモンいれかえ（どちらも「ポケモンの入れ替え」。p.325）は、ここの ``clear_special_conditions`` を呼ぶ。
  きぜつしたポケモンは場からいなくなるので、特殊状態もいっしょになくなる（場のポケモンが持つため）。
- どく状態のポケモンが再びどく状態になる効果を受けても、二重のどく状態にはならない（p.322）。ねむり・マヒ・こんらんも同じ
  （p.322「ねむり状態が積み重なることはありません」「マヒ状態が積み重なることはありません」「こんらん状態が積み重なることは
  ありません」）。
- 「ねむり」「マヒ」「こんらん」は重複しない（p.322「特殊状態の重複」）。p.322 の例「マヒ状態のポケモンがねむり状態に
  なったら、マヒ状態から自動的に回復して、ねむり状態になります」のとおり、新しい状態が前の状態に置きかわる
  （``SpecialConditions.exclusive``。前の状態は ``REPLACED`` の理由で消えたとログに残す）。どくはほかの特殊状態と
  重複する（p.322）ので、ねむり・マヒになっても、ねむり・マヒが消えても、どくはそのまま。
- 特殊状態を与えたポケモンが場をはなれても、受けた特殊状態は消えない（p.322）。
- どくのダメージ（ポケモンチェックの 2）・ねむりのコイン（3）・マヒの回復（4）は、エンジンの ``_pokemon_check`` が行う
  （ここにあるのは、そこから呼ぶ「消す」処理と、マヒの回復する番の計算）。

ログ:

- ``special_condition``: 特殊状態にする効果を受けた（``player``・``pokemon``・``pokemon_id``・``condition``・
  ``effect``、どくなら ``damage``、マヒなら ``paralyzed_turn``（マヒ状態になった番）・``recovery_turn``（回復する番）。
  もうその状態だったときだけ ``already``）
- ``special_condition_prevented``（v0.46）: 特殊状態にする効果を受けたが、特殊状態にならない特殊能力（カビゴンの［めんえき］）で防いだ（``player``・``pokemon``・
  ``pokemon_id``・``condition``・どくなら ``damage``・``effect``・``power``）。状態は変わらない
- ``special_conditions_removed``: 特殊状態が消えた（``player``・``pokemon``・``pokemon_id``・``conditions``・``reason``）。
  ``reason`` は ``RETREAT``・``SWITCH``（v0.3a）、``SLEEP_COIN``・``PARALYSIS_END``・``REPLACED``（v0.3b）、``EVOLVE``（v0.4a）、
  ``FORCED_SWITCH``（v0.4d。相手のワザ「ふきとばし」でベンチにもどされた）
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .errors import UnsupportedError
from .state import ASLEEP, CONFUSED, NO_SPECIAL_CONDITIONS, Asleep, Confused, Paralyzed, Poison, turn_owner

if TYPE_CHECKING:
    from .state import GameState, PokemonInPlay

POISON = "poison"
SLEEP = "sleep"  # v0.3b
PARALYSIS = "paralysis"  # v0.3b
CONFUSION = "confusion"  # v0.3c
# こんらん状態のポケモンのワザがこんらんしたとき（コインが「うら」）、ワザを使ったポケモン自身が受けるダメージ（p.309 の
# 手順 5「もとのワザの内容に関わらず、ワザを使ったポケモン自身が20ダメージを受けます」・p.322。v0.3c）
CONFUSION_DAMAGE = 20
# 通常のどく（p.322「ポケモンチェックのたびに、「弱点」「抵抗力」に関係なく、10ダメージを受けます。」）
NORMAL_POISON = Poison(damage=10)

# 特殊状態が消えた理由（ログの ``reason``）
RETREAT = "retreat"  # にげる（p.311）
SWITCH = "switch"  # トレーナーの効果によるポケモンの入れ替え（ポケモンいれかえ。p.322・p.325）。v0.34 から、自分のワザの効果で自分のポケモンを入れ替えたとき（テレポート）も
SLEEP_COIN = "sleep_coin"  # ポケモンチェックの 3 のコインが「おもて」でねむりから回復した（p.322・p.323。v0.3b）
PARALYSIS_END = "paralysis_end"  # ポケモンチェックの 4 でマヒから自動的に回復した（p.322・p.323。v0.3b）
REPLACED = "replaced"  # ほかの「ねむり」「マヒ」「こんらん」になったので消えた（p.322「特殊状態の重複」。v0.3b）
EVOLVE = "evolve"  # 進化した（p.310 の進化の手順 3・p.322「特殊状態になっているポケモンが進化したら」。v0.4a）
# 相手のワザの効果でベンチにもどされた（バタフリーの「ふきとばし」。p.19・p.213「相手の対戦ポケモンをベンチにもどす」・
# p.311・p.322。v0.4d）。トレーナーの効果による入れ替え（SWITCH）とは理由を分ける
FORCED_SWITCH = "forced_switch"
# v0.50: 退化した（p.324「19 ポケモンの退化」。kyuura の GR-2000-P324-DEVOLUTION「退化したポケモンを、「どく」「ねむり」「マヒ」「こんらん」状態や、その他の
# 「持続する効果」から回復させます」。ミュウの「たいかビーム」・退化スプレー。``evolution.devolve``）。進化（EVOLVE）とは理由を分ける
DEVOLVE = "devolve"
# v0.55: トレーナーの効果で特殊状態を回復した（なんでもなおしの「特殊状態にあるポケモンの全ての特殊状態を回復する」。docs/instant-trainers-v0.55.md）。ベンチにもどる・進化・
# 退化とは理由を分ける。ワザによる持続する効果・ダメージ・にげるの失敗の記録は特殊状態ではないので消さない
CURED = "cured"


def _prevented(state: GameState, owner: int, pokemon: PokemonInPlay, condition: str, effect: str, **fields: object) -> bool:
    """v0.46: ``pokemon`` が特殊状態にならない（カビゴンの［めんえき］。はたらいているか ``effects.status_immunity``）なら、状態を変えずにログ
    ``special_condition_prevented``（``player``・``pokemon``・``pokemon_id``・``condition``・状態ごとの項目・``effect``・``power``）を残して True。付ける処理の共通の
    入口（どく・ねむり・マヒ・こんらんのすべての付ける関数）がはじめに呼ぶので、ワザ・特殊能力のどれで付けようとしても同じに防ぐ。すでにある特殊状態は消さない
    （防ぐのは新しく付けることだけ）。"""
    from .effects import status_immunity  # effects.py は conditions.py を読み込むので、使うときに読み込む

    if state.is_face_down(pokemon):
        # v0.67: うらのカード（マチスの秘策）は、効果を受ける時におもてにする（ワザの要素は ``kernel.reaches`` が先におもてにする。ここに来るのは、トレーナー・特殊能力の
        # 効果で特殊状態にするとき）。「たねポケモン」でなくトラッシュしたら、特殊状態にする対象はいない
        from .zones import designate_face_down

        if designate_face_down(state, owner, pokemon, by_player=state.current_player, cause=condition, can_lose=True) is None:
            return True
    key = status_immunity(state, owner, pokemon)
    if key is None:
        return False
    state.add_event("special_condition_prevented", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, condition=condition, **fields,
                    effect=effect, power=str(key))
    return True


def _end_disguise(state: GameState, owner: int, pokemon: PokemonInPlay, effect: str) -> None:
    """v0.49: タケシのキュウコンの「ばける」の「このカードが「ねむり・マヒ・こんらん」状態の時、この「ばける」の力は使えず、このカードは「タケシのキュウコン」に
    もどる。(のせてあった「進化カード」はトラッシュされる)」。ねむり・マヒ・こんらんにする 3 つの関数が、特殊状態を付けたあとに呼ぶ（［めんえき］で防いだら呼ばない）。
    のせたカードがなければ何もしない（どくでは呼ばない。説明に「どく」はない）。"""
    if pokemon.disguise is not None:
        from .zones import DISGUISE_SPECIAL_CONDITION, remove_disguise  # zones.py は state.py だけを読み込む。conditions.py の読み込みの順番に合わせて使うときに読む

        remove_disguise(state, owner, pokemon, reason=DISGUISE_SPECIAL_CONDITION, effect=effect)


def _require_active(state: GameState, owner: int, pokemon: PokemonInPlay, condition: str) -> None:
    # ベンチのポケモンは特殊状態にならない（p.322）ので、バトル場のポケモンでなければエンジンの不具合として止める
    if state.players[owner].active is not pokemon:
        raise RuntimeError(f"バトル場にいないポケモン {pokemon.pokemon_id} を {condition} 状態にしようとした（エンジンの不具合。p.322）")


def poison(state: GameState, owner: int, pokemon: PokemonInPlay, *, effect: str, damage: int = NORMAL_POISON.damage) -> None:
    """``owner`` の対戦ポケモン ``pokemon`` を、どく状態にする（p.322）。``damage`` はポケモンチェックで受けるダメージ（通常のどくは 10）。

    - もうどく状態なら、二重のどく状態にはならない（p.322「どく状態が積み重なることはありません」）。
    - p.322 は、特殊などく状態（ダメージが 20 など）のポケモンが通常のどく状態にする効果を受けたら、通常の
      どく状態になると書く（v0.3a の #14）。通常のどく状態にする効果（``damage`` 10）は、どちらの場合も結果が「通常のどく状態」
      なので、どく状態を ``NORMAL_POISON`` にする。
    - 特殊などく状態にする効果（v0.34。ニドキングの「どくどく」は 20）も「どく状態にかかる」（v0.3a の #13）ので、この関数でどく状態に
      する。もうどく状態のポケモンが、受けるダメージの違う特殊などく状態にする効果を受けたときの扱い（v0.3a の #15）は決まらないので、
      呼ぶ側（解決の基盤の ``Status``）がこの関数を呼ぶ前に止める。ここでは、受けるダメージが同じなら状態は変わらない（``already``）。
    - どくはほかの特殊状態と重複する（p.322）ので、ねむり・マヒはそのまま（v0.3b）。
    - ``effect``: どく状態にした効果の識別子（ワザなら ``AttackKey`` の文字列）。ログにだけ残す。
    """
    _require_active(state, owner, pokemon, POISON)
    if damage <= 0 or damage % 10:
        raise ValueError(f"どくで受けるダメージ {damage} は 10 の正の倍数")
    if _prevented(state, owner, pokemon, POISON, effect, damage=damage):
        return  # v0.46: ［めんえき］（特殊などくの上書きの確かめより先。防がれるなら状態は変わらない）
    current = pokemon.conditions.poison
    if damage != NORMAL_POISON.damage and current is not None and current.damage != damage:
        raise RuntimeError("受けるダメージの違うどく状態から特殊などく状態にする扱いは決まらない（v0.3a の #15。呼ぶ側が先に止める）")
    already = current is not None
    poisoned = NORMAL_POISON if damage == NORMAL_POISON.damage else Poison(damage=damage)
    pokemon.conditions = replace(pokemon.conditions, poison=poisoned)
    _log_applied(state, owner, pokemon, POISON, effect, already, damage=poisoned.damage)


def put_to_sleep(state: GameState, owner: int, pokemon: PokemonInPlay, *, effect: str) -> None:
    """``owner`` の対戦ポケモン ``pokemon`` を、ねむり状態にする（v0.3b。p.322「2. ねむり状態」）。

    - もうねむり状態なら、二重のねむり状態にはならない（p.322「ねむり状態が積み重なることはありません」）。
      ねむり状態は持つ情報がないので、状態は変わらない（ログに ``already``）。
    - マヒ状態なら、マヒ状態から自動的に回復して、ねむり状態になる（p.322「特殊状態の重複」の例）。こんらん状態でも、
      こんらんは消えてねむり状態になる（同じ規定。v0.3c）。
    - どく状態はそのまま（どくはほかの特殊状態と重複する。p.322）。
    """
    _require_active(state, owner, pokemon, SLEEP)
    if _prevented(state, owner, pokemon, SLEEP, effect):
        return  # v0.46: ［めんえき］
    already = _set_exclusive(state, owner, pokemon, ASLEEP)
    _log_applied(state, owner, pokemon, SLEEP, effect, already)
    _end_disguise(state, owner, pokemon, effect)


def confuse(state: GameState, owner: int, pokemon: PokemonInPlay, *, effect: str) -> None:
    """``owner`` の対戦ポケモン ``pokemon`` を、こんらん状態にする（v0.3c。p.322「4. こんらん状態」）。

    - もうこんらん状態なら、二重のこんらん状態にはならない（p.322「こんらん状態が積み重なることはありません」）。
      こんらん状態は持つ情報がないので、状態は変わらない（ログに ``already``）。
    - ねむり・マヒ状態なら、それは消えてこんらん状態になる（p.322「「ねむり」「マヒ」「こんらん」状態が重複することは
      ありません」と、マヒからねむりの例から。docs/confusion-v0.3c.md）。
    - どく状態はそのまま（p.322「こんらん状態のポケモンがどく状態になったら、そのポケモンは「どく」と「こんらん」の両方の
      状態になります」）。
    """
    _require_active(state, owner, pokemon, CONFUSION)
    if _prevented(state, owner, pokemon, CONFUSION, effect):
        return  # v0.46: ［めんえき］
    already = _set_exclusive(state, owner, pokemon, CONFUSED)
    _log_applied(state, owner, pokemon, CONFUSION, effect, already)
    _end_disguise(state, owner, pokemon, effect)


def paralysis_recovery_turn(state: GameState, owner: int, turn: int) -> int:
    """``turn`` 番にマヒ状態になった ``owner`` のポケモンが、自動的に回復する番（v0.3b）。

    「ポケモンのマヒ状態は、マヒ状態になった番の「次の自分（そのポケモンの持ち主）の番」の終わりのポケモンチェックで
    自動的に回復します」（p.323 の 4。p.322 にも同じ記述）。``turn`` より後の番のうち、持ち主（``owner``）の最初の番を
    返す（番の数を 1 つ足すとは決めない）。相手の番にマヒ状態になったら次の番、自分の番になったら 2 つ後の番になる。
    """
    recovery = turn + 1
    while turn_owner(state, recovery) != owner:
        recovery += 1
    return recovery


def paralysis_problem(state: GameState, owner: int, pokemon: PokemonInPlay) -> UnsupportedError | None:
    """``pokemon`` をいまマヒ状態にすると、原典で決められない場合なら、その理由（v0.3b）。

    マヒ状態のポケモンが再びマヒ状態になる効果を受けても、二重のマヒ状態にはならない（p.322）。ただし、そのとき
    回復する番が最初の「マヒ状態になった番」で決まるのか、あとの効果を受けた番で決まるのかは、原典に書かれていない。
    2 つの番から決まる回復の番が同じなら、どちらでも結果は同じなので扱える（状態は変えない）。違うなら決められない。

    v0.3b の対応カードでは起こらない（マヒにするワザは相手の対戦ポケモンにだけ効き、マヒ状態のポケモンは次の自分の
    番の終わりに回復するので、相手の番にマヒ状態のままでいることがない）。起こったら推測で処理せずに止める。
    """
    current = pokemon.conditions.exclusive
    if not isinstance(current, Paralyzed):
        return None
    before = paralysis_recovery_turn(state, owner, current.turn)
    after = paralysis_recovery_turn(state, owner, state.turn_number)
    if before == after:
        return None
    return UnsupportedError(
        "UNRESOLVED_REPARALYSIS_RECOVERY_TURN",
        f"マヒ状態のポケモン {pokemon.pokemon_id}（{current.turn} 番にマヒ状態になり、{before} 番の終わりに回復する）が、"
        f"{state.turn_number} 番に再びマヒ状態になる効果を受けた。二重のマヒ状態にはならない（p.322）が、回復する番を"
        "最初の番で決めるか、あとの番で決めるかは『オフィシャルブック2000』（p.322・p.323）から決められないので扱わない",
    )


def paralyze(state: GameState, owner: int, pokemon: PokemonInPlay, *, effect: str) -> None:
    """``owner`` の対戦ポケモン ``pokemon`` を、マヒ状態にする（v0.3b。p.322「3. マヒ状態」）。

    - マヒ状態になった番（``GameState.turn_number``）を ``Paralyzed.turn`` に持つ（回復する番を決めるため。
      ``paralysis_recovery_turn``）。
    - もうマヒ状態なら、二重のマヒ状態にはならない（p.322）。回復する番が変わらない場合だけ扱い、状態は変えない
      （ログに ``already``）。変わる場合は原典で決められないので ``UnsupportedError``（``paralysis_problem``）。
      コインを投げる効果は、投げる前に ``paralysis_problem`` を確かめておくこと。
    - ねむり状態なら、ねむり状態は消えてマヒ状態になる（p.322「「ねむり」「マヒ」「こんらん」状態が重複することは
      ありません」と、マヒからねむりの例から。docs/sleep-paralysis-v0.3b.md）。こんらん状態でも同じ（v0.3c）。
    - どく状態はそのまま（p.322）。
    """
    _require_active(state, owner, pokemon, PARALYSIS)
    if _prevented(state, owner, pokemon, PARALYSIS, effect):
        return  # v0.46: ［めんえき］（マヒの再付与の確かめより先。防がれるなら回復する番は変わらない）
    problem = paralysis_problem(state, owner, pokemon)
    if problem is not None:
        raise problem
    # もうマヒなら、最初の「マヒ状態になった番」のまま（回復する番が変わらないことは paralysis_problem で確かめた）
    already = _set_exclusive(state, owner, pokemon, Paralyzed(turn=state.turn_number))
    paralyzed = pokemon.conditions.exclusive
    _log_applied(
        state, owner, pokemon, PARALYSIS, effect, already,
        paralyzed_turn=paralyzed.turn, recovery_turn=paralysis_recovery_turn(state, owner, paralyzed.turn),
    )
    _end_disguise(state, owner, pokemon, effect)


def recover_from_sleep(state: GameState, owner: int, pokemon: PokemonInPlay) -> None:
    """ポケモンチェックの 3 のコインが「おもて」: ねむり状態から回復する（p.322・p.323）。どく状態はそのまま。"""
    if not pokemon.conditions.asleep:
        raise RuntimeError(f"ねむり状態でないポケモン {pokemon.pokemon_id} をねむりから回復させようとした（エンジンの不具合）")
    _remove_exclusive(state, owner, pokemon, SLEEP_COIN)


def wake_up(state: GameState, owner: int, pokemon: PokemonInPlay, effect: str) -> None:
    """v0.72: ワザの効果で、ねむり状態から回復させる（ナツメのルージュラ（GD6-012）の「めざめのキッス」の「相手を「ねむり」状態から、回復させる。」）。ねむりだけを消し、
    どく状態はそのまま（p.322 の重複の規定）。理由は ``CURED``（ログ ``special_conditions_removed`` の ``effect`` はワザ）。"""
    if not pokemon.conditions.asleep:
        raise RuntimeError(f"ねむり状態でないポケモン {pokemon.pokemon_id} をねむりから回復させようとした（エンジンの不具合）")
    _remove_exclusive(state, owner, pokemon, CURED, effect=effect)


def recover_from_paralysis(state: GameState, owner: int, pokemon: PokemonInPlay) -> None:
    """ポケモンチェックの 4: マヒ状態から自動的に回復する（p.322・p.323）。どく状態はそのまま。"""
    if not pokemon.conditions.paralyzed:
        raise RuntimeError(f"マヒ状態でないポケモン {pokemon.pokemon_id} をマヒから回復させようとした（エンジンの不具合）")
    _remove_exclusive(state, owner, pokemon, PARALYSIS_END)


def _set_exclusive(state: GameState, owner: int, pokemon: PokemonInPlay, value: Asleep | Paralyzed | Confused) -> bool:
    """ねむり・マヒ・こんらん（``SpecialConditions.exclusive``）を ``value`` にする共通の処理（v0.3d）。

    - もう同じ種類の状態なら、状態を変えずに True（二重にならない。p.322。ログの ``already``）を返す。
    - ほかの種類（ねむり・マヒ・こんらん）なら、それを ``REPLACED`` の理由で消してから ``value`` にする（p.322「特殊状態の
      重複」。前の状態の消えたログが、新しい状態のログより先に出る）。
    - どく（``SpecialConditions.poison``）は変えない（どくはほかの特殊状態と重複する。p.322）。
    """
    current = pokemon.conditions.exclusive
    if type(current) is type(value):
        return True
    if current is not None:
        _remove_exclusive(state, owner, pokemon, REPLACED)
    pokemon.conditions = replace(pokemon.conditions, exclusive=value)
    return False


def _log_applied(
    state: GameState, owner: int, pokemon: PokemonInPlay, condition: str, effect: str, already: bool, **fields: object
) -> None:
    """特殊状態を付けた（または、もうその状態だった）ログ ``special_condition``。項目の順は v0.3a〜v0.3c と同じ
    （``player``・``pokemon``・``pokemon_id``・``condition``・状態ごとの項目・``effect``・``already``）。"""
    extra = {"already": True} if already else {}
    state.add_event(
        "special_condition",
        player=owner,
        pokemon=pokemon.card,
        pokemon_id=pokemon.pokemon_id,
        condition=condition,
        **fields,
        effect=effect,
        **extra,
    )


def _remove_exclusive(state: GameState, owner: int, pokemon: PokemonInPlay, reason: str, **fields: object) -> None:
    """「ねむり」「マヒ」「こんらん」（``SpecialConditions.exclusive``）だけを消す。どく状態は残す（p.322 の重複の規定）。v0.72: ``fields`` はログに加える項目
    （ワザの効果で回復させたときの ``effect``。ほかの呼び出しは渡さない）。"""
    name = pokemon.conditions.exclusive.name
    pokemon.conditions = replace(pokemon.conditions, exclusive=None)
    state.add_event(
        "special_conditions_removed",
        player=owner,
        pokemon=pokemon.card,
        pokemon_id=pokemon.pokemon_id,
        conditions=(name,),
        reason=reason,
        **fields,
    )


def clear_special_conditions(state: GameState, owner: int, pokemon: PokemonInPlay, reason: str, **fields: object) -> None:
    """バトル場からベンチに戻ったポケモン・進化したポケモン（``reason`` が ``EVOLVE``。v0.4a）の特殊状態を、すべて消す
    （p.310・p.311・p.322）。特殊状態がなければ何もしない。にげるの失敗の記録（``retreat_failed_turn``）は特殊状態では
    ないので、ここでは変えない（進化で記録を消すのは ``engine._evolve_pokemon``）。ワザによる持続する効果（v0.4b）も特殊状態
    ではないので、ここでは変えない（``persistent.remove_persistent_effects`` を呼び出し側が別に呼ぶ）。

    「ベンチに戻ったら、そのポケモンの「どく」「ねむり」「マヒ」「こんらん」状態や、「持続する効果」は、すべて消えて
    なくなります」（p.311）。「どく」なら、どくマーカーを取りのぞくことにあたる（p.322）。ダメージカウンター・
    ついているカード・場のポケモンの番号はそのまま（p.311）。一度消えた特殊状態は、バトル場にもどっても復活しない（p.322）。
    """
    names = pokemon.conditions.names()
    if not names:
        return
    pokemon.conditions = NO_SPECIAL_CONDITIONS
    state.add_event(
        "special_conditions_removed",
        player=owner,
        pokemon=pokemon.card,
        pokemon_id=pokemon.pokemon_id,
        conditions=names,
        reason=reason,
        **fields,
    )

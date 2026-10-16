"""ゲーム状態を JSON にできる辞書にする（画面やほかの言語に渡すため・テストで比べるため）。

形式は 10 あります（``format_version``）。

- 1（既定）: v0.1 と同じ形。v0.1 の固定値のテストと互換性の参照データは、この形で比べる。
- 2: 1 に次を加えたもの（v0.2a）。``format_version``、``effects``（効果の登録表の id）、
  ``next_pokemon_id``、``next_decision_id``、``decision``（保留中の決定）、場のポケモンごとの ``pokemon_id``。
- 3: 2 に ``trainer_in_use``（使っている最中のトレーナーカード）を加えたもの（v0.2b）。
- 4: 3 に、場のポケモンごとの ``trainers``（ついているトレーナーカード）を加えたもの（v0.2c）。
- 5: 4 に、場のポケモンごとの ``special_conditions``（特殊状態。どくなら ``{"poison": {"damage": 10}}``、
  なければ ``{}``）を加えたもの（v0.3a）。v0.3b で、ねむり ``"sleep": {}``・マヒ ``"paralysis": {"turn": n}``
  （``n`` はマヒ状態になった番。回復する番はここから決まる）の項目を加えた。どくだけの状態・特殊状態のない状態の
  書き出しは v0.3a と同じ（項目の意味を変えていないので形式 6 にはしていない。知らない項目のある辞書は、読む側が
  拒否すること）。v0.3c で、こんらん ``"confusion": {}`` の項目を同じ理由で加えた。
- 6: 5 に、場のポケモンごとの ``retreat_failed_turn``（こんらん状態で「にげる」に失敗した番。なければ ``None``。
  そのポケモンは、その番の間「にげる」を宣言できない。p.311）を加えたもの（v0.3c）。
- 7: 6 に、場のポケモンごとの ``evolution_stack``（いちばん上のカードの下に重なっているポケモンのカード。下から順に
  ``{"card": uid, "card_id": id}``。進化していなければ ``[]``）・``played_turn``（場に出た番。対戦準備なら 0）・
  ``evolved_turn``（いまの姿に進化した番。進化していなければ ``None``）を加えたもの（v0.4a）。``card``・``card_id``・
  ``name``・``hp`` はいちばん上のカード（そのポケモンを表すカード。p.310）。v0.4c の 2 進化では ``evolution_stack`` が
  2 つ（たねポケモン・1 進化ポケモンの順）になるだけで、項目と意味は同じ（形式 8 のまま。docs/stage2-state-v0.4c.md）。
- 8: 7 に、場のポケモンごとの ``persistent_effects``（ワザによる持続する効果。v0.4b。p.322・p.323）を加えたもの。
  1 つにつき ``{"effect": 種類, "source_card": uid, "source_card_id": id, "source_player": プレイヤー,
  "created_turn": 効果を与えた番, "active_turn": はたらく番}``。v0.4b の種類は ``"prevent_damage"``（「かたまる」の
  「次の相手の番、このカードはダメージを受けない」。はたらく番の終わりに消える）だけ。なければ ``[]``。v0.12 で種類
  ``"retaliation"``（R団のファイヤーの「ほのおのかべ」の「次の相手の番、このカードが相手のワザによるダメージを受けたとき、…相手に
  10ダメージを与える」。はたらく番の終わりに消える）を加え、その種類だけ ``"attack_index"``（効果を与えたワザの位置）・``"amount"``
  （与えるダメージ）を加える（項目の意味を変えていないので形式 9 のまま。docs/architecture-v0.12.md 5 章）。v0.13 で種類
  ``"retaliation_received_damage"``（わるいカメールの「こうらがえし」の「…そのポケモンにも同じダメージを与える」。与えるダメージは
  受けたダメージで決まる）を加え、その種類は ``"attack_index"`` だけを加える（形式 9 のまま。docs/architecture-v0.13.md 5 章）。
  v0.27 で種類 ``"next_turn_attack_damage"``（ストライクの「つるぎのまい」の「次の自分の番、このカードが使う「きりさく」のダメージは「60」に
  なる」。はたらく番は次の自分の番（``created_turn`` + 2）で、その番の終わりに消える）を加え、その種類だけ ``"attack_index"``（効果を与えた
  ワザの位置）・``"target_attack_index"``（ダメージが変わるワザの位置）・``"amount"``（変えたあとのダメージ）を加える（項目の意味を変えて
  いないので形式 9 のまま。docs/scyther-v0.27.md）。
- 9: 8 に、``energy_attached_by_powers_this_turn``（この番に、ポケモンパワーの効果で手札から場のポケモンにつけたエネルギー
  カードの枚数。v0.6 のカメックスの「あまごい」。手札からつける通常の操作の回数 ``energy_attachments_this_turn`` とは別。
  番の最初に 0）を加えたもの（v0.6。docs/architecture-v0.6.md 5 章）。この数が 1 以上の番には、通常の操作が原典で決められない
  （``UNRESOLVED_ATTACH_AFTER_POWER_ATTACH``）ので、状態に持ち、書き出しで表す。形式 1〜8 は、この数が 0 でなければ
  ``ValueError``（0 なら形式 1〜8 の書き出しは v0.5 と同じ）。
- 10: 9 に、``power_uses_this_turn``（この番に使った「自分の番ごとに1回使える」特殊能力。[場のポケモンの番号, 特殊能力の位置] の並び。
  v0.31 のカツラのロコンの「しぜんになおる」。番の最初に空）と ``energy_burn``（この番に「炎」エネルギーになったエネルギーカード。
  [場のポケモンの番号, エネルギーカードの uid] の並び。v0.31 のリザードンの「エナジーバーン」。番の終わりに空）を加えたもの（v0.31。
  docs/held-cards-v0.31.md）。形式 1〜9 は、どちらかが空でなければ ``ValueError``（空なら形式 1〜9 の書き出しは v0.30 と同じ）。
  v0.31 の持続する効果の種類 ``"destiny_bond"``（みちづれ）・``"attack_barrier"``（バリアー）・``"damage_reduction"``（ちいさくなる。
  ``"amount"`` を加える）・``"cannot_attack"``（しっぽをふる。相手に与える効果で、``source_card``・``source_player`` は効果を与えたワザを
  使ったポケモンのカードとプレイヤー）は、v0.27 と同じく形式 8 の ``persistent_effects`` の種類の値を加えただけ（形式は変えない）。

形式 1・2 は、トレーナーを使っている最中（決定を待っている間）の状態を表せない（そのカードがどの
ゾーンにも出てこない）。その状態を形式 1・2 で書き出そうとすると ``ValueError`` にする（黙って
カードを落とさない）。同じように、形式 1〜3 はポケモンについているトレーナー（プラスパワーなど）を
表せないので、ついているトレーナーがあると ``ValueError`` にする。トレーナーを使う対戦では形式 4 を使う。
形式 1〜4 は特殊状態（v0.3a）を表せないので、特殊状態のポケモンがいると ``ValueError`` にする（形式 5 を使う）。
形式 1〜5 は「にげる」に失敗した記録（v0.3c）を表せないので、記録のあるポケモンがいると ``ValueError`` にする
（形式 6 を使う。記録は番の終わりに消えるので、その番の間だけ）。
形式 1〜6 は進化したポケモンのカードの重なり（v0.4a）を表せないので、進化したポケモンがいると ``ValueError`` にする
（形式 7 を使う）。形式 1〜7 はワザによる持続する効果（v0.4b）を表せないので、持続する効果を受けているポケモンがいると
``ValueError`` にする（形式 8 を使う。効果は次の相手の番の終わりに消えるので、その間だけ）。持続する効果のない状態の
形式 1〜7 の書き出しは v0.4a と同じ。進化していないポケモンの場に出た番（``played_turn``）は、どの形式にも入るログ（対戦準備の
``place_starting_pokemon``・``play_to_bench``、v0.32 からワザの効果で山札から出した ``bench_from_deck`` の番）から分かるので、形式 1〜6 の書き出しは v0.3d と同じ。
形式 1 は保留中の決定の中身を持たないので、ポケモンチェックの中のきぜつのあとの決定（続きが「ポケモンチェックの
残りをして次の番を始める」。決定の ``context`` の ``then``）を表せない。その状態を形式 1 で書き出そうとすると
``ValueError`` にする。同じように、ワザの途中の決定（``resume`` が ``"attack"``。v0.4d の「ふきとばし」で相手が選ぶ控え）も
形式 1 では ``ValueError`` にする（v0.4c までは、製品の登録表のワザはこの決定を出さなかった）。

ワザの途中の決定（v0.4d）は、形式 2 以上の ``decision``（``id``・``kind``・``player``（決定するプレイヤー。「ふきとばし」では
ワザを使われた側）・``options``（場のポケモンの番号）・``min_choices``・``max_choices``・``resume``（``"attack"``）・``context``
（``use`` = [プレイヤー, 場のポケモンの番号, カード id, ワザの位置]、``target`` = 入れ替える相手の対戦ポケモンの番号））と、
``current_player``（ワザを使ったプレイヤーのまま）・``turn_number`` で表せるので、新しい形式はない（形式 8 のまま）。

ワザのあとのきぜつの判定で「こんじょう」を使うかの決定（v0.11。``kind`` が ``"ko_prevention"``、``resume`` が ``"knock_out"``、
``min_choices`` 0・``max_choices`` 1、``options`` は対象のポケモンの番号、``context`` は ``attack`` = [プレイヤー, 場のポケモンの番号,
カード id, ワザの位置]・``power`` = [カード id, パワーの位置]）も、形式 2 以上の ``decision`` で表せるので、新しい形式はない（形式 9 の
まま）。決定を待つ間、対象のポケモンは HP 以上のダメージのまま場にいる（``players`` の場のポケモンの ``damage``）。コインは決定の
あとで投げるので、乱数の状態（``rng_state_sha256``）は決定を出したときのまま。形式 1 では ``ValueError``。

きぜつしたときに「ふしちょう」を使うかの決定（v0.12。``kind`` が ``"post_knockout_power"``、``resume`` が ``"post_knockout"``、
``min_choices`` 0・``max_choices`` 1、``options`` はトラッシュにあるそのカードの uid、``context`` は ``power`` = [カード id, パワーの位置]
（ポケモンチェックの中のきぜつなら ``then`` も））と、その前のサイドを取る決定の ``context`` の ``post_knockout``（= [[持ち主, カードの
uid, カード id, パワーの位置]]。候補があるときだけ）も、形式 2 以上の ``decision`` で表せるので、新しい形式はない（形式 9 のまま）。
形式 1 では ``ValueError``。

コインの結果（v0.2d）は、ログの ``coin_flip`` にだけ残る（状態に残る値はない）。ログはどの形式にも入るので、
コインのための新しい形式はない。この先のコインの結果を決める乱数の状態は ``rng_state_sha256``（指紋）。

どれも、エンジンの内部の完全な状態の写しで、隠れた情報（山札の順番・相手の手札・サイドの中身）を
すべて含みます。プレイヤー・観戦者に見せる形ではありません（その形はまだありません。
docs/architecture-v0.2a.md の「非公開の情報」）。乱数の状態は指紋だけで、そこから乱数はもどせません
（保存には ``rng.rng_state_to_json`` を使う）。
"""

from __future__ import annotations

from typing import Any

from .rng import rng_fingerprint
from .state import (
    RETALIATION_FIXED,
    RETALIATION_RECEIVED,
    AttackBarrier,
    AttackCoinCheck,
    Asleep,
    CannotAttack,
    CannotAttackWhileSourceActive,
    CannotRetreat,
    Confused,
    DamageReduction,
    DestinyBond,
    GameState,
    NEXT_TURN_MULTIPLY,
    CannotUseAttack,
    CannotUseOwnAttack,
    NextTurnAttackDamage,
    Paralyzed,
    PokemonInPlay,
    PreventDamage,
    ReducedDamageToSource,
    Retaliation,
)

FORMAT_VERSIONS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)


def _special_conditions(pokemon: PokemonInPlay) -> dict[str, Any]:
    """形式 5 の ``special_conditions``（p.322 の順: どく・ねむり・マヒ・こんらん）。"""
    conditions = pokemon.conditions
    data: dict[str, Any] = {}
    if conditions.poison is not None:
        data["poison"] = {"damage": conditions.poison.damage}
    if isinstance(conditions.exclusive, Asleep):
        data["sleep"] = {}
    elif isinstance(conditions.exclusive, Paralyzed):
        data["paralysis"] = {"turn": conditions.exclusive.turn}
    elif isinstance(conditions.exclusive, Confused):
        data["confusion"] = {}
    elif conditions.exclusive is not None:
        raise ValueError(f"書き出せない特殊状態 {conditions.exclusive!r}")
    return data


def _persistent_effect(state: GameState, effect) -> dict[str, Any]:
    """形式 8 の ``persistent_effects`` の 1 つ。v0.12 の ``"retaliation"``（「ほのおのかべ」）には、``attack_index``（効果を与えた
    ワザの位置）と ``amount``（与えるダメージの基本となるダメージ）を加える（ほかの種類の形は v0.4b と同じ。v0.3b の特殊状態の項目と同じく、
    種類の値を加えただけなので形式は変えない。知らない種類のある辞書は、読む側が拒否すること）。v0.13 の
    ``"retaliation_received_damage"``（「こうらがえし」。与えるダメージは受けたダメージと同じ）は ``attack_index`` だけを加える。v0.27 の
    ``"next_turn_attack_damage"``（「つるぎのまい」）は ``attack_index``・``target_attack_index``・``amount`` を加える。v0.31 の
    ``"damage_reduction"``（「ちいさくなる」）は ``amount`` を加え、``"destiny_bond"``・``"attack_barrier"``・``"cannot_attack"`` は共通の項目だけ。
    v0.34 の ``"reduced_damage_to_source"``（「なきつく」）は ``amount`` を加える。v0.35 の ``"next_turn_attack_damage_multiplier"``（「きあいだめ」。
    ``NextTurnAttackDamage`` の「数をかける」決め方）は ``attack_index``・``target_attack_index``・``amount``（かける数）・``includes_self_damage`` を、
    ``"cannot_use_own_attack"``（「あわあわ」）・``"cannot_use_attack"``（「ドわすれ」）は ``attack_index``・``target_attack_index`` を加える（どれも種類の
    値を加えただけで形式は変えない。v0.34 までの書き出しを読む側は、知らない種類として拒否すること）。v0.36 の ``"attack_coin_check"``（「すなかけ」・
    「えんまく」など。p.309 の手順 4 のコイン）は ``single_use``（「効果は1回できえる」）を加え、``"cannot_retreat"``（「アイスバーン」・「わしづかみ」）は共通の
    項目だけ（どちらも相手に与える効果。``source_card`` は効果を与えたワザを使ったポケモン。形式は変えない。v0.35 までの書き出しを読む側は、知らない種類として
    拒否すること）。v0.40 の ``"cannot_attack_while_source_active"``（「すごむ」。相手に与える効果。``source_card`` は効果を与えたワザを使ったポケモン
    （「このカード」））は共通の項目だけ（形式は変えない。v0.39 までの書き出しを読む側は、知らない種類として拒否すること）。"""
    data: dict[str, Any] = {
        "effect": effect.kind,
        "source_card": effect.source_card,
        "source_card_id": state.cards[effect.source_card].card_id,
        "source_player": effect.source_player,
        "created_turn": effect.created_turn,
        "active_turn": effect.active_turn,
    }
    if isinstance(effect, Retaliation):
        data["attack_index"] = effect.attack_index
        if effect.basis == RETALIATION_FIXED:
            data["amount"] = effect.amount
        elif effect.basis != RETALIATION_RECEIVED:
            raise ValueError(f"書き出せない持続する効果 {effect!r}")
        # v0.13: 受けたダメージで決まる種類（"retaliation_received_damage"。「こうらがえし」）は、量が効果を与えたときに決まって
        # いないので amount を書かない（受けたダメージはワザ 1 回の中の値で、状態に持たない）
    elif isinstance(effect, NextTurnAttackDamage):
        data["attack_index"] = effect.attack_index
        data["target_attack_index"] = effect.target_attack_index
        data["amount"] = effect.amount
        if effect.operation == NEXT_TURN_MULTIPLY:
            data["includes_self_damage"] = effect.includes_self_damage  # v0.35: 「きあいだめ」（種類 "next_turn_attack_damage_multiplier"）だけ
        elif effect.includes_self_damage:
            raise ValueError(f"書き出せない持続する効果 {effect!r}（「その数にする」効果の自分へのダメージ）")
    elif isinstance(effect, (CannotUseOwnAttack, CannotUseAttack)):
        data["attack_index"] = effect.attack_index  # v0.35: 「あわあわ」・「ドわすれ」
        data["target_attack_index"] = effect.target_attack_index
    elif isinstance(effect, (DamageReduction, ReducedDamageToSource)):
        data["amount"] = effect.amount  # v0.34: "reduced_damage_to_source"（「なきつく」）も減らす量を加える
    elif isinstance(effect, AttackCoinCheck):
        data["single_use"] = effect.single_use  # v0.36: 「すなかけ」（PMCG1-051）の「効果は1回できえる」
    elif not isinstance(effect, (PreventDamage, DestinyBond, AttackBarrier, CannotAttack, CannotRetreat, CannotAttackWhileSourceActive)):
        raise ValueError(f"書き出せない持続する効果 {effect!r}")
    return data


def _pokemon(state: GameState, pokemon: PokemonInPlay | None, format_version: int) -> dict[str, Any] | None:
    if pokemon is None:
        return None
    definition = state.card_def(pokemon.card)
    data = {
        "card": pokemon.card,
        "card_id": definition.id,
        "name": definition.name_ja,
        "hp": definition.hp,
        "damage": pokemon.damage,
        "energy": list(pokemon.energy),
    }
    if format_version >= 2:
        data["pokemon_id"] = pokemon.pokemon_id
    if format_version >= 4:
        data["trainers"] = [
            {
                "card": t.card,
                "card_id": state.cards[t.card].card_id,
                "player": t.player,
                "discard_at_end_of_turn": t.discard_at_end_of_turn,
            }
            for t in pokemon.trainers
        ]
    if format_version >= 5:
        data["special_conditions"] = _special_conditions(pokemon)
    if format_version >= 6:
        data["retreat_failed_turn"] = pokemon.retreat_failed_turn
    if format_version >= 7:
        data["evolution_stack"] = [{"card": uid, "card_id": state.cards[uid].card_id} for uid in pokemon.evolution_stack]
        data["played_turn"] = pokemon.played_turn
        data["evolved_turn"] = pokemon.evolved_turn
    if format_version >= 8:
        data["persistent_effects"] = [_persistent_effect(state, e) for e in pokemon.persistent_effects]
    return data


def _plain(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def state_to_dict(state: GameState, format_version: int = 1) -> dict[str, Any]:
    if format_version not in FORMAT_VERSIONS:
        raise ValueError(f"知らない形式 {format_version!r}（{FORMAT_VERSIONS}）")
    if state.trainer_in_use is not None and format_version < 3:
        raise ValueError(f"形式 {format_version} は、使っている最中のトレーナーカードを表せない（format_version=3 以上を使う）")
    if format_version < 4 and any(pokemon.trainers for p in state.players for pokemon in p.in_play()):
        raise ValueError(f"形式 {format_version} は、ポケモンについているトレーナーカードを表せない（format_version=4 を使う）")
    if format_version < 5 and any(pokemon.conditions.names() for p in state.players for pokemon in p.in_play()):
        raise ValueError(f"形式 {format_version} は、特殊状態（どく・ねむり・マヒ・こんらん）を表せない（format_version=5 以上を使う）")
    if format_version < 6 and any(pokemon.retreat_failed_turn is not None for p in state.players for pokemon in p.in_play()):
        raise ValueError(f"形式 {format_version} は、こんらん状態で「にげる」に失敗した記録を表せない（format_version=6 を使う）")
    if format_version < 7 and any(pokemon.evolution_stack for p in state.players for pokemon in p.in_play()):
        raise ValueError(f"形式 {format_version} は、進化したポケモンのカードの重なりを表せない（format_version=7 を使う）")
    if format_version < 8 and any(pokemon.persistent_effects for p in state.players for pokemon in p.in_play()):
        raise ValueError(f"形式 {format_version} は、ワザによる持続する効果を表せない（format_version=8 を使う）")
    if format_version < 9 and state.energy_attached_by_powers_this_turn != 0:
        raise ValueError(
            f"形式 {format_version} は、この番にポケモンパワーで手札からつけたエネルギーの枚数を表せない（format_version=9 を使う）"
        )
    if format_version < 10 and (state.power_uses_this_turn or state.energy_burn):
        raise ValueError(
            f"形式 {format_version} は、この番に使った回数の制限のある特殊能力・「炎」エネルギーになったエネルギーを表せない（format_version=10 を使う）"
        )
    if format_version == 1 and state.decision is not None and state.decision.context_value("then") is not None:
        raise ValueError("形式 1 は、ポケモンチェックの中のきぜつのあとの決定（続き）を表せない（format_version=2 以上を使う）")
    if format_version == 1 and state.decision is not None and state.decision.resume == "attack":
        # v0.4d: v0.1 の形には、ワザの途中の決定（「ふきとばし」で相手が選ぶ控えなど）の項目がない（段階 "decision" だけが残り、
        # 決定するプレイヤー・選べるもの・続きの情報が落ちる）。黙って落とさない
        raise ValueError("形式 1 は、ワザの途中の決定を表せない（format_version=2 以上を使う）")
    if format_version == 1 and state.decision is not None and state.decision.resume == "knock_out":
        # v0.11: v0.1 の形には、ワザのあとのきぜつの判定で「こんじょう」を使うかの決定（決定するプレイヤー・選べるもの・選ぶ数 0〜1・
        # 続きの情報）の項目がない。黙って落とさない
        raise ValueError("形式 1 は、「こんじょう」を使うかの決定を表せない（format_version=2 以上を使う）")
    if format_version == 1 and state.decision is not None and (
        state.decision.resume == "post_knockout" or state.decision.context_value("post_knockout") is not None
    ):
        # v0.12: v0.1 の形には、「ふしちょう」を使うかの決定（決定するプレイヤー・トラッシュのカード・選ぶ数 0〜1）の項目も、サイドを取る
        # 決定のあとに「ふしちょう」の決定が続くこと（context の post_knockout）を表す項目もない。黙って落とさない
        raise ValueError("形式 1 は、「ふしちょう」を使うかの決定（とその前のサイドを取る決定）を表せない（format_version=2 以上を使う）")
    data = {
        "rules": state.rules.id,
        "card_data": {"repository": state.card_data.repository, "commit": state.card_data.commit, "path": state.card_data.path},
        "seed": state.seed,
        # 乱数の状態（この先のコインの結果などを決める）。同じ値なら同じ乱数の続きになる
        "rng_state_sha256": rng_fingerprint(state.rng),
        "phase": state.phase.value,
        "turn_number": state.turn_number,
        "current_player": state.current_player,
        "first_player": state.first_player,
        "energy_attachments_this_turn": state.energy_attachments_this_turn,
        "pending_prizes": {str(k): v for k, v in sorted(state.pending_prizes.items())},
        "pending_promotions": list(state.pending_promotions),
        "mulligan_rounds": [list(r) for r in state.mulligan_rounds],
        "cards": {str(uid): {"card_id": c.card_id, "owner": c.owner} for uid, c in sorted(state.cards.items())},
        "players": [
            {
                "deck": list(p.deck),
                "hand": list(p.hand),
                "prizes": list(p.prizes),
                "discard": list(p.discard),
                "active": _pokemon(state, p.active, format_version),
                "bench": [_pokemon(state, b, format_version) for b in p.bench],
                "placed_starting_pokemon": p.placed_starting_pokemon,
                "mulligans": p.mulligans,
                "mulligan_draws_remaining": p.mulligan_draws_remaining,
            }
            for p in state.players
        ],
        "result": None
        if state.result is None
        else {
            "outcome": state.result.outcome,
            "winner": state.result.winner,
            "conditions": [list(c) for c in state.result.conditions],
        },
        "halt": None
        if state.halt is None
        else {"code": state.halt.code, "message": state.halt.message, "references": list(state.halt.references)},
        "log": [_plain(dict(event)) for event in state.log],
    }
    if format_version == 1:
        return data
    d = state.decision
    data.update({
        "format_version": format_version,
        "effects": state.effects.id,
        "next_pokemon_id": state.next_pokemon_id,
        "next_decision_id": state.next_decision_id,
        "decision": None if d is None else {
            "id": d.id,
            "kind": d.kind,
            "player": d.player,
            "options": list(d.options),
            "min_choices": d.min_choices,
            "max_choices": d.max_choices,
            "resume": d.resume,
            "context": {name: _plain(value) for name, value in d.context},
        },
    })
    if format_version == 2:
        return data
    used = state.trainer_in_use
    data["trainer_in_use"] = None if used is None else {
        "player": used.player,
        "card": used.card,
        "card_id": state.cards[used.card].card_id,
    }
    if format_version >= 9:
        data["energy_attached_by_powers_this_turn"] = state.energy_attached_by_powers_this_turn
    if format_version >= 10:
        data["power_uses_this_turn"] = [list(use) for use in state.power_uses_this_turn]
        data["energy_burn"] = [list(pair) for pair in state.energy_burn]
    return data

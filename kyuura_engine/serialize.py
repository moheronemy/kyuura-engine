"""ゲーム状態を JSON にできる辞書にする（画面やほかの言語に渡すため・テストで比べるため）。

形式は 8 つあります（``format_version``）。

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
  「次の相手の番、このカードはダメージを受けない」。はたらく番の終わりに消える）だけ。なければ ``[]``。

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
``place_starting_pokemon``・``play_to_bench`` の番）から分かるので、形式 1〜6 の書き出しは v0.3d と同じ。
形式 1 は保留中の決定の中身を持たないので、ポケモンチェックの中のきぜつのあとの決定（続きが「ポケモンチェックの
残りをして次の番を始める」。決定の ``context`` の ``then``）を表せない。その状態を形式 1 で書き出そうとすると
``ValueError`` にする。

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
from .state import Asleep, Confused, GameState, Paralyzed, PokemonInPlay

FORMAT_VERSIONS = (1, 2, 3, 4, 5, 6, 7, 8)


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
        data["persistent_effects"] = [
            {
                "effect": e.kind,
                "source_card": e.source_card,
                "source_card_id": state.cards[e.source_card].card_id,
                "source_player": e.source_player,
                "created_turn": e.created_turn,
                "active_turn": e.active_turn,
            }
            for e in pokemon.persistent_effects
        ]
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
    if format_version == 1 and state.decision is not None and state.decision.context_value("then") is not None:
        raise ValueError("形式 1 は、ポケモンチェックの中のきぜつのあとの決定（続き）を表せない（format_version=2 以上を使う）")
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
    return data

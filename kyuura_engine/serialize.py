"""ゲーム状態を JSON にできる辞書にする（画面やほかの言語に渡すため・テストで比べるため）。

形式は 2 つあります（``format_version``）。

- 1（既定）: v0.1 と同じ形。v0.1 の固定値のテストと互換性の参照データは、この形で比べる。
- 2: 1 に次を加えたもの（v0.2a）。``format_version``、``effects``（効果の登録表の id）、
  ``next_pokemon_id``、``next_decision_id``、``decision``（保留中の決定）、場のポケモンごとの ``pokemon_id``。

どちらも、エンジンの内部の完全な状態の写しで、隠れた情報（山札の順番・相手の手札・サイドの中身）を
すべて含みます。プレイヤー・観戦者に見せる形ではありません（その形はまだありません。
docs/architecture-v0.2a.md の「非公開の情報」）。乱数の状態は指紋だけで、そこから乱数はもどせません
（保存には ``rng.rng_state_to_json`` を使う）。
"""

from __future__ import annotations

from typing import Any

from .rng import rng_fingerprint
from .state import GameState, PokemonInPlay

FORMAT_VERSIONS = (1, 2)


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
    data = {
        "rules": state.rules.id,
        "card_data": {"repository": state.card_data.repository, "commit": state.card_data.commit, "path": state.card_data.path},
        "seed": state.seed,
        # 乱数の状態（今後のコイン・山札を切る処理の結果を決める）。同じ値なら同じ乱数の続きになる
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
        "format_version": 2,
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
    return data

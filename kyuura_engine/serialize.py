"""ゲーム状態を JSON にできる辞書にする（画面やほかの言語に渡すため・テストで比べるため）。

隠れた情報（山札の順番・相手の手札・サイドの中身）もすべて含みます。プレイヤーごとに
見せる情報を絞る処理は v0.1 にはありません。
"""

from __future__ import annotations

import hashlib
from typing import Any

from .state import GameState, PokemonInPlay


def _pokemon(state: GameState, pokemon: PokemonInPlay | None) -> dict[str, Any] | None:
    if pokemon is None:
        return None
    definition = state.card_def(pokemon.card)
    return {
        "card": pokemon.card,
        "card_id": definition.id,
        "name": definition.name_ja,
        "hp": definition.hp,
        "damage": pokemon.damage,
        "energy": list(pokemon.energy),
    }


def _plain(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def state_to_dict(state: GameState) -> dict[str, Any]:
    return {
        "rules": state.rules.id,
        "card_data": {"repository": state.card_data.repository, "commit": state.card_data.commit, "path": state.card_data.path},
        "seed": state.seed,
        # 乱数の状態（今後のコイン・山札を切る処理の結果を決める）。同じ値なら同じ乱数の続きになる
        "rng_state_sha256": hashlib.sha256(repr(state.rng.getstate()).encode("ascii")).hexdigest(),
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
                "active": _pokemon(state, p.active),
                "bench": [_pokemon(state, b) for b in p.bench],
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

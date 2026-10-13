"""ゾーンの間でカードを動かす処理のうち、エンジンの進行とカードの効果で共通のもの。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .state import AttachedTrainer, TrainerInUse

if TYPE_CHECKING:
    from .state import GameState, PokemonInPlay


def draw_cards(state: GameState, player: int, count: int) -> tuple[int, ...]:
    """自分の山札の一番上から ``count`` 枚を、1 枚ずつ手札に加える（p.312「カードを引く」）。

    ``count`` は山札の枚数以下であること。山札が足りないときにどうするか（番の最初なら負け、
    トレーナーなどの効果なら引けるだけ引く）は、呼ぶ側がその規定にしたがって決める（p.312）。
    引いたカードを返す。

    ログの ``"draw"`` の ``cards`` は、引いたプレイヤーにだけ見える情報（引いたカードを相手に見せる
    必要はない。p.312）。今のログは内部の完全な記録で、プレイヤーに見せる形ではない。
    """
    p = state.players[player]
    if not 0 <= count <= len(p.deck):
        raise RuntimeError(f"山札 {len(p.deck)} 枚から {count} 枚は引けない（エンジンの不具合）")
    drawn = p.deck[:count]
    del p.deck[:count]
    p.hand.extend(drawn)
    state.add_event("draw", player=player, cards=tuple(drawn))
    return tuple(drawn)


def attach_energy_from_hand(state: GameState, player: int, energy: int, pokemon: PokemonInPlay) -> None:
    """手札のエネルギーカード ``energy`` を、場のポケモン ``pokemon`` につける（同じ uid のまま、手札から取りのぞいて
    ``pokemon.energy`` の最後に加える。v0.6）。

    手札からつける通常の操作（p.310。``engine._attach_energy``）と、ポケモンパワーの効果で手札からつける処理（v0.6 の
    「あまごい」）で共通。カードを動かすだけで、つけてよいか（番・段階・1 番に 1 枚・カードの種類・対象）の確認、回数の記録、
    ログは呼ぶ側が行う（確認は、ここを呼ぶ前にすべて済ませる）。カードが手札にない・持ち主が違う・ポケモンの持ち主が違うなら、
    確認の漏れなので ``RuntimeError``（状態を変える前）。
    """
    p = state.players[player]
    if energy not in p.hand or state.cards[energy].owner != player or not any(x is pokemon for x in p.in_play()):
        raise RuntimeError(f"プレイヤー {player} の手札のカード {energy} を、自分の場のポケモンにつけられない（確認の漏れ。エンジンの不具合）")
    p.hand.remove(energy)
    pokemon.energy.append(energy)


def attach_trainer(state: GameState, player: int, card: int, pokemon: PokemonInPlay, discard_at_end_of_turn: int) -> AttachedTrainer:
    """使っている最中のトレーナーカードを、場のポケモンにつける（v0.2c。「つけて使う」トレーナー）。

    カードは ``state.trainer_in_use`` から、ついているポケモンの ``trainers`` に移る（同じカードが
    2 か所にある瞬間を作らない）。``discard_at_end_of_turn`` の番の終わりに、エンジンがトラッシュする。
    """
    if state.trainer_in_use != TrainerInUse(player, card):
        raise RuntimeError(f"使っている最中でないカード {card} をつけようとした（エンジンの不具合）")
    state.trainer_in_use = None
    attached = AttachedTrainer(card, player, discard_at_end_of_turn)
    pokemon.trainers.append(attached)
    state.add_event(
        "attach_trainer",
        player=player,
        card=card,
        pokemon=pokemon.card,
        pokemon_id=pokemon.pokemon_id,
        discard_at_end_of_turn=discard_at_end_of_turn,
    )
    return attached

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


def discard_hand(state: GameState, player: int) -> tuple[int, ...]:
    """自分の手札をすべて、同じ uid のまま手札の並びの順に自分のトラッシュに置く（v0.19。オーキドはかせの「あなたの手札をすべてトラッシュ
    する」。p.255）。トラッシュしたカードを返す（手札が 0 枚なら空）。

    使っている最中のトレーナーカードは手札にない（p.310 の手順 1 で手札から出している。``state.trainer_in_use``）ので、含まない。
    トラッシュにはカードの順番がない（p.312）。ログの ``"discard_hand"`` の ``cards`` は、トラッシュに置いたカードで、全員に見える
    （トラッシュは公開の情報）。v0.22 から、カードを動かすのは手札の一部をトラッシュする ``discard_from_hand`` と共通の
    ``_hand_to_discard``（動き・ログは v0.19 と同じ）。
    """
    discarded = _hand_to_discard(state, player, tuple(state.players[player].hand))
    state.add_event("discard_hand", player=player, cards=discarded)
    return discarded


def discard_from_hand(state: GameState, player: int, cards: tuple[int, ...]) -> tuple[int, ...]:
    """自分の手札のうち ``cards`` を、同じ uid のまま、手札の並びの順に自分のトラッシュに置く（v0.22。パソコン通信の「手札からカードを2枚
    選んでトラッシュしなければ、このカードは使えない」。p.260・p.310）。トラッシュしたカード（手札の並びの順）を返す。

    手札の一部を選んでトラッシュする処理で共通。選んでよいか（枚数・種類）の確認は呼ぶ側が、ここを呼ぶ前にすべて済ませる。答えの並びに
    よらず手札の並びの順に置く（トラッシュにはカードの順番がない。p.312。同じ選択なら同じ状態になる）。使っている最中のトレーナーカード
    は手札にないので選べない。ログの ``"discard_from_hand"`` の ``cards`` は全員に見える（トラッシュは表を上にして置く公開の情報。
    p.312）。オーキドはかせの ``discard_hand``（手札をすべて。ログの監査は手札の組み立て直しと同じことを確かめる）とは別のイベント。
    """
    p = state.players[player]
    if len(set(cards)) != len(cards) or any(uid not in p.hand for uid in cards):
        raise RuntimeError(f"プレイヤー {player} の手札のカード {cards} をトラッシュできない（確認の漏れ。エンジンの不具合）")
    discarded = _hand_to_discard(state, player, tuple(uid for uid in p.hand if uid in cards))
    state.add_event("discard_from_hand", player=player, cards=discarded)
    return discarded


def _hand_to_discard(state: GameState, player: int, cards: tuple[int, ...]) -> tuple[int, ...]:
    """手札の ``cards``（手札の並びの順）を、同じ uid のままトラッシュの最後に置く（ログは呼ぶ側）。"""
    p = state.players[player]
    if any(state.cards[uid].owner != player for uid in p.hand):
        raise RuntimeError(f"プレイヤー {player} の手札に持ち主の違うカードがある（エンジンの不具合）")
    for uid in cards:
        p.hand.remove(uid)
    p.discard.extend(cards)
    return cards


def search_deck_to_hand(state: GameState, player: int, card: int) -> None:
    """自分の山札のカード ``card`` を、同じ uid のまま手札の最後に加える（v0.22。パソコン通信の「あなたの山札からカードを1枚選び出し、
    手札に加える。」。p.260）。山札の残りの並びは変えない（切るのは呼ぶ側。``shuffle_deck``）。

    「カードを引く」（山札の一番上。p.312。``draw_cards``）ではない。選んでよいかの確認は呼ぶ側が済ませる。カードがそのプレイヤーの山札に
    ない・持ち主が違うなら、確認の漏れなので ``RuntimeError``（状態を変える前）。ログの ``"search_deck"`` の ``card`` は、選んだ
    プレイヤーにだけ見える情報（最新の説明に相手に見せる指示がない。p.312「特に指示されないかぎり、引いたカードを相手プレイヤーに見せる
    必要はありません」と同じ扱い。docs/computer-search-v0.22.md）。``player`` は全員に見える。v0.24 から、カードを動かすのは見せて
    手札に加える ``reveal_deck_to_hand`` と共通の ``_deck_to_hand``（動き・ログは v0.22 と同じ）。
    """
    _deck_to_hand(state, player, card)
    state.add_event("search_deck", player=player, card=card)


def reveal_deck_to_hand(state: GameState, player: int, card: int) -> None:
    """自分の山札のカード ``card`` を、相手に見せてから、同じ uid のまま手札の最後に加える（v0.24。ポケモン交換おじさんの「あなたの山札から
    「たねポケモン」または「進化カード」を1枚選び出し、相手プレイヤーに見せてから、手札に加える。」。p.259）。山札の残りの並びは変えない
    （切るのは呼ぶ側）。

    ``search_deck_to_hand``（パソコン通信。選んだカードは選んだプレイヤーだけが見る）とは、見せることだけが違う。ログの
    ``"reveal_from_deck"`` の ``card`` は全員に見える情報（見せる指示がある）。選べたほかの山札のカードはログに書かない。選んでよいかの確認は
    呼ぶ側が済ませる。
    """
    _deck_to_hand(state, player, card)
    state.add_event("reveal_from_deck", player=player, card=card)


def _deck_to_hand(state: GameState, player: int, card: int) -> None:
    """自分の山札の ``card`` を、同じ uid のまま手札の最後に加える（ログは呼ぶ側）。山札にない・持ち主が違うなら、確認の漏れなので
    ``RuntimeError``（状態を変える前）。"""
    p = state.players[player]
    if card not in p.deck or state.cards[card].owner != player:
        raise RuntimeError(f"プレイヤー {player} の山札のカード {card} を手札に加えられない（確認の漏れ。エンジンの不具合）")
    p.deck.remove(card)
    p.hand.append(card)


def return_hand_to_deck(state: GameState, player: int, card: int) -> None:
    """自分の手札のカード ``card`` を、相手に見せてから、同じ uid のまま自分の山札の一番下にもどす（v0.24。ポケモン交換おじさんの「手札から
    「たねポケモン」または「進化カード」を1枚選び、相手プレイヤーに見せてから、あなたの山札にもどす。」。p.259）。

    山札のどこにもどすかは書かれていない。このカードのあとで山札を選び出し、よく切る（どこにもどしても選べるものは同じ）ので、一番下
    （``deck`` の最後）にもどす（実装上の仮定。docs/pokemon-trader-v0.24.md の PT7）。ログの ``"return_to_deck"`` の ``card`` は全員に
    見える情報（見せる指示がある）。選んでよいかの確認は呼ぶ側が済ませる。手札にない・持ち主が違うなら ``RuntimeError``（状態を変える前）。
    """
    p = state.players[player]
    if card not in p.hand or state.cards[card].owner != player:
        raise RuntimeError(f"プレイヤー {player} の手札のカード {card} を山札にもどせない（確認の漏れ。エンジンの不具合）")
    p.hand.remove(card)
    p.deck.append(card)
    state.add_event("return_to_deck", player=player, card=card)


def shuffle_deck(state: GameState, player: int) -> None:
    """自分の山札を切る（乱数 ``state.rng`` で 1 回並べかえる。ログ ``"shuffle"``）。対戦の準備・切り直し（p.308。v0.1 から
    ``engine._shuffle_deck``）と、カードの効果で山札を切る処理（v0.22 のパソコン通信の「その後、その山札をよく切る。」。p.260）で共通。
    v0.21 までの ``engine._shuffle_deck`` の本体をそのまま関数にした（乱数の使い方・ログは同じ）。"""
    state.rng.shuffle(state.players[player].deck)
    state.add_event("shuffle", player=player)


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


def return_discard_to_hand(state: GameState, player: int, cards: tuple[int, ...]) -> None:
    """自分のトラッシュのカード ``cards`` を、同じ uid のまま 1 枚ずつ手札の最後に加える（v0.12。トラッシュから手札に加える処理で共通。
    v0.9 のゴースの「エナジーへんかん」（エネルギーカード）と、v0.12 の R団のファイヤーの「ふしちょう」（きぜつしたこのカード））。

    カードを動かすだけで、動かしてよいか（決定・特殊能力の条件・選んだカードの種類）の確認とログは呼ぶ側が行う（確認は、ここを呼ぶ前に
    すべて済ませる）。カードがそのプレイヤーのトラッシュにない・持ち主が違う・同じカードを 2 回渡したなら、確認の漏れなので
    ``RuntimeError``（状態を変える前）。トラッシュにはカードの順番がない（p.312）ので、残りのカードの並びは変えない。
    """
    p = state.players[player]
    if len(set(cards)) != len(cards) or any(uid not in p.discard or state.cards[uid].owner != player for uid in cards):
        raise RuntimeError(f"プレイヤー {player} のトラッシュのカード {cards} を手札に加えられない（確認の漏れ。エンジンの不具合）")
    for uid in cards:
        p.discard.remove(uid)
        p.hand.append(uid)


def discard_from_deck(state: GameState, player: int, count: int) -> tuple[int, ...]:
    """自分の山札の上から ``count`` 枚を、同じ uid のまま、上から順に自分のトラッシュに置く（v0.31。カツラのブーバーの「マグマふんしゅつ」・
    ファイヤーの「やまやき」（相手の山札））。トラッシュしたカードを返す。

    「カードを引く」（``draw_cards``）ではない。枚数が足りるかの確認とログは呼ぶ側が行う（足りない場合の処理は決められない。HC6。呼ぶ前に止める）。
    足りなければ確認の漏れなので ``RuntimeError``（状態を変える前）。トラッシュにはカードの順番がない（p.312）。
    """
    p = state.players[player]
    if not 0 <= count <= len(p.deck):
        raise RuntimeError(f"山札 {len(p.deck)} 枚から {count} 枚はトラッシュできない（確認の漏れ。エンジンの不具合）")
    cards = tuple(p.deck[:count])
    del p.deck[:count]
    p.discard.extend(cards)
    return cards


def attach_from_discard(state: GameState, player: int, cards: tuple[int, ...], pokemon: PokemonInPlay) -> None:
    """自分のトラッシュのエネルギーカード ``cards`` を、同じ uid のまま、場のポケモン ``pokemon`` の ``energy`` の最後に（この順に）つける（v0.31。
    マチスのエレブーの「たいでん」）。つけてよいかの確認とログは呼ぶ側が行う。トラッシュにない・持ち主が違う・同じカードを 2 回渡したなら
    ``RuntimeError``（状態を変える前）。"""
    p = state.players[player]
    if len(set(cards)) != len(cards) or any(uid not in p.discard or state.cards[uid].owner != player for uid in cards):
        raise RuntimeError(f"プレイヤー {player} のトラッシュのカード {cards} をつけられない（確認の漏れ。エンジンの不具合）")
    if pokemon not in p.in_play():
        raise RuntimeError(f"つける先のポケモン {pokemon.pokemon_id} がプレイヤー {player} の場にいない（エンジンの不具合）")
    for uid in cards:
        p.discard.remove(uid)
        pokemon.energy.append(uid)

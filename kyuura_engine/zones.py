"""ゾーンの間でカードを動かす処理のうち、エンジンの進行とカードの効果で共通のもの。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .state import AttachedTrainer, PokemonInPlay, TrainerInUse

if TYPE_CHECKING:
    from .state import GameState


def enter_play(state: GameState, uid: int) -> PokemonInPlay:
    """カードを場のポケモンにする。場のポケモンの番号を新しく付ける（前に使った番号は使わない）。

    場に出た番（``played_turn``。対戦準備なら 0）を記録する。今の番に場に出したポケモンは、その番には進化できない
    （「その番の最初」には場にいなかった。p.310。v0.4a）。v0.32 から、手札から出す（``engine._enter_play``。対戦準備・ベンチに出す）と、
    ワザの効果で山札から出す（``bench_from_deck``）で共通（v0.31 までの ``engine._enter_play`` の本体をそのまま関数にした）。
    """
    pokemon = PokemonInPlay(uid, pokemon_id=state.next_pokemon_id, played_turn=state.turn_number)
    state.next_pokemon_id += 1
    return pokemon


def bench_from_deck(state: GameState, player: int, card: int) -> PokemonInPlay:
    """自分の山札のたねポケモンのカード ``card`` を、同じ uid のまま、手札を通さずに自分のベンチの最後に出す（v0.32。ワザの「自分の山札から「○○」を
    1匹さがしてベンチに出す」。docs/bench-search-counter-drain-v0.32.md）。場のポケモンの番号・場に出た番は手札から出すときと同じ ``enter_play``。
    山札の残りの並びは変えない（切るのは呼ぶ側。``shuffle_deck``）。

    出してよいか（名前・決定）の確認とログは呼ぶ側が行う。カードがそのプレイヤーの山札にない・持ち主が違う・たねポケモンでない・ベンチに空きが
    ないなら、確認の漏れなので ``RuntimeError``（状態を変える前）。出した場のポケモンを返す。
    """
    p = state.players[player]
    if card not in p.deck or state.cards[card].owner != player or not state.card_def(card).is_basic_pokemon or len(p.bench) >= state.rules.max_bench:
        raise RuntimeError(f"プレイヤー {player} の山札のカード {card} をベンチに出せない（確認の漏れ。エンジンの不具合）")
    p.deck.remove(card)
    pokemon = enter_play(state, card)
    p.bench.append(pokemon)
    return pokemon


def return_in_play_to_deck(state: GameState, player: int, pokemon: PokemonInPlay, *, effect: str) -> tuple[int, ...]:
    """自分の場のポケモン ``pokemon`` と、ついているすべてのカードを、同じ uid のまま自分の山札の一番下にもどす（v0.36。キョウのドガースの「くもがくれ
    ガス」の「自分と、自分についているすべてのカードを山札にもどす」。docs/sand-attack-retreat-lock-v0.36.md 4 章）。

    - もどすカード: 重なったポケモンのカード（進化していれば、下から ``PokemonInPlay.cards()``）・エネルギーカード（ついている順）・トレーナーカード（ついている順）。
      山札のどこにもどすかは書かれていない。そのあと必ず山札を切る（``shuffle_deck``。呼ぶ側）ので一番下（実装上の仮定。v0.24 の PT7 と同じ）
    - 場をはなれたので、場のポケモンの番号は無効になり、ダメージカウンター・特殊状態はなくなる（p.322。カードではないので、どこにも置かない）。持続する
      効果を消すのは呼ぶ側（``persistent.remove_persistent_effects``。理由 ``return_in_play_to_deck``）。きぜつではない（サイドは取られない）
    - ログ ``return_in_play_to_deck``（``player``・``pokemon``（いちばん上のカード）・``pokemon_id``・``effect``（ワザ）・``cards``（もどしたカードすべて。場の
      カードなので公開）・``evolution_stack``・``energy``・``trainers``・``damage``（なくなったダメージ））

    もどしてよいかの確認は呼ぶ側が済ませる。場にいない・持ち主の違うカードがある（今の対応カードでは起こらない）なら ``RuntimeError``（状態を変える前）。
    もどしたカードを返す。
    """
    p = state.players[player]
    trainers = tuple(t.card for t in pokemon.trainers)
    cards = (*pokemon.cards(), *pokemon.energy, *trainers)
    on_bench = any(b is pokemon for b in p.bench)
    if (p.active is not pokemon and not on_bench) or any(state.cards[uid].owner != player for uid in cards):
        raise RuntimeError(f"プレイヤー {player} の場のポケモン {pokemon.pokemon_id} を山札にもどせない（確認の漏れ。エンジンの不具合）")
    if p.active is pokemon:
        p.active = None
    else:
        del p.bench[next(i for i, b in enumerate(p.bench) if b is pokemon)]
    p.deck.extend(cards)
    state.add_event("return_in_play_to_deck", player=player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, effect=effect, cards=cards,
                    evolution_stack=pokemon.evolution_stack, energy=tuple(pokemon.energy), trainers=trainers, damage=pokemon.damage)
    return cards


def return_in_play_to_hand(state: GameState, player: int, pokemon: PokemonInPlay, *, effect: str | None = None, power: str | None = None) -> tuple[int, ...]:
    """自分の場のポケモン ``pokemon`` と、ついているすべてのカードを、同じ uid のまま自分の手札にもどす（v0.42。docs/power-decisions-v0.42.md 4 章）。

    - もどすカード: 重なったポケモンのカード（進化していれば、下から ``PokemonInPlay.cards()``。重なったカード全体が 1 匹。v0.36 の RD2 と同じ読み方）・
      エネルギーカード（ついている順）・トレーナーカード（ついている順）。エリカのピクシーの「ようせいのきせき」（「そのポケモンと、それらについているすべての
      カードを手札にもどす」）。メノクラゲの「おくびょう」は、ついているカードを先にトラッシュする（``discard_attached_cards``。呼ぶ側）ので、もどるのは
      ポケモンのカードだけ。山札にもどす ``return_in_play_to_deck`` とは行き先が違う（切らない）
    - 場をはなれたので、場のポケモンの番号は無効になり、ダメージカウンター・特殊状態はなくなる（p.322。カードではないので、どこにも置かない）。持続する
      効果を消すのは呼ぶ側（``persistent.remove_persistent_effects``。理由 ``return_in_play_to_hand``）。きぜつではない（サイドは取られない）
    - ログ ``return_in_play_to_hand``（``player``・``pokemon``（いちばん上のカード）・``pokemon_id``・``effect``（ワザ）か ``power``（特殊能力）・``cards``
      （もどしたカードすべて。場のカードなので公開）・``evolution_stack``・``energy``・``trainers``・``damage``（なくなったダメージ））

    もどしてよいかの確認は呼ぶ側が済ませる。場にいない・持ち主の違うカードがある（今の対応カードでは起こらない）なら ``RuntimeError``（状態を変える前）。
    もどしたカードを返す。
    """
    p = state.players[player]
    trainers = tuple(t.card for t in pokemon.trainers)
    cards = (*pokemon.cards(), *pokemon.energy, *trainers)
    on_bench = any(b is pokemon for b in p.bench)
    if (p.active is not pokemon and not on_bench) or any(state.cards[uid].owner != player for uid in cards) or (effect is None) == (power is None):
        raise RuntimeError(f"プレイヤー {player} の場のポケモン {pokemon.pokemon_id} を手札にもどせない（確認の漏れ。エンジンの不具合）")
    if p.active is pokemon:
        p.active = None
    else:
        del p.bench[next(i for i, b in enumerate(p.bench) if b is pokemon)]
    p.hand.extend(cards)
    source = {"effect": effect} if effect is not None else {"power": power}
    state.add_event("return_in_play_to_hand", player=player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, **source, cards=cards,
                    evolution_stack=pokemon.evolution_stack, energy=tuple(pokemon.energy), trainers=trainers, damage=pokemon.damage)
    return cards


def discard_attached_cards(state: GameState, player: int, pokemon: PokemonInPlay, *, effect: str | None = None,
                           power: str | None = None) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """自分の場のポケモン ``pokemon`` についているすべてのカード（エネルギーカード・トレーナーカード）を、同じ uid のまま持ち主のトラッシュに置く
    （v0.38。ケーシィ（PMCG4-031）の「いなくなる」の「ついているカードをすべてトラッシュする」。docs/bench-switch-combined-v0.38.md 5 章）。

    - 「ついているカード」はエネルギーカードとトレーナーカード（p.310 の「つける」カード）。進化して重なったカードは、ポケモン自身（「このカード」）の
      カードで、ここでは動かさない（v0.36 の RD2 と同じ読み方。重なったカード全体が 1 匹）
    - トラッシュする順番はエネルギー（ついている順）→ トレーナー（ついている順）。トラッシュには順番がない（p.312）
    - ログ ``discard_attached_cards``（``player``・``pokemon``・``pokemon_id``・``effect``・``energy``・``trainers``。トラッシュは公開の情報）。ついている
      カードがなくてもログを残す（説明の処理をしたことを残す）。v0.42: 特殊能力（メノクラゲの「おくびょう」の「ついていたカードも全てはがしてすてる」）は
      ``effect`` の代わりに ``power``（特殊能力の識別子）

    トラッシュしてよいかの確認は呼ぶ側が済ませる。場にいない・持ち主の違うカードがある（今の対応カードでは起こらない）なら ``RuntimeError``（状態を
    変える前）。トラッシュした（エネルギー, トレーナー）を返す。
    """
    p = state.players[player]
    energy = tuple(pokemon.energy)
    trainers = tuple(t.card for t in pokemon.trainers)
    if (p.active is not pokemon and not any(b is pokemon for b in p.bench)) or any(state.cards[uid].owner != player for uid in (*energy, *trainers)) \
            or (effect is None) == (power is None):
        raise RuntimeError(f"プレイヤー {player} の場のポケモン {pokemon.pokemon_id} についているカードをトラッシュできない（確認の漏れ。エンジンの不具合）")
    pokemon.energy.clear()
    pokemon.trainers.clear()
    p.discard.extend((*energy, *trainers))
    source = {"effect": effect} if effect is not None else {"power": power}
    state.add_event("discard_attached_cards", player=player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, **source, energy=energy,
                    trainers=trainers)
    return energy, trainers


def promote_from_bench(state: GameState, player: int, pokemon_id: int, *, effect: str | None = None) -> PokemonInPlay:
    """自分のベンチのポケモン ``pokemon_id`` を、空いたバトル場に出す（ログ ``promote_active``）。きぜつのあとのバトル場に出す決定
    （``resolution.flow._resume_promote``。p.313）と、ワザの効果で場をはなれたあとの「ベンチから、かわりの対戦ポケモンを出す」（v0.38。キョウのポッポの
    「でんれい」。ログに ``effect``（ワザ）を加える）で共通。v0.37 までの ``_resume_promote`` の本体をそのまま関数にした（動き・ログは同じ）。

    バトル場が空いていない・ベンチにいない（確認の漏れ）なら ``RuntimeError``（状態を変える前）。出した場のポケモンを返す。
    """
    p = state.players[player]
    index = next((i for i, pokemon in enumerate(p.bench) if pokemon.pokemon_id == pokemon_id), None)
    if p.active is not None or index is None:
        raise RuntimeError(f"プレイヤー {player} のベンチのポケモン {pokemon_id} をバトル場に出せない（確認の漏れ。エンジンの不具合）")
    p.active = p.bench.pop(index)
    extra = {} if effect is None else {"effect": effect}
    state.add_event("promote_active", player=player, pokemon=p.active.card, **extra)
    return p.active


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


def discard_from_hand(state: GameState, player: int, cards: tuple[int, ...], *, power: str | None = None) -> tuple[int, ...]:
    """自分の手札のうち ``cards`` を、同じ uid のまま、手札の並びの順に自分のトラッシュに置く（v0.22。パソコン通信の「手札からカードを2枚
    選んでトラッシュしなければ、このカードは使えない」。p.260・p.310）。トラッシュしたカード（手札の並びの順）を返す。

    手札の一部を選んでトラッシュする処理で共通。選んでよいか（枚数・種類）の確認は呼ぶ側が、ここを呼ぶ前にすべて済ませる。答えの並びに
    よらず手札の並びの順に置く（トラッシュにはカードの順番がない。p.312。同じ選択なら同じ状態になる）。使っている最中のトレーナーカード
    は手札にないので選べない。ログの ``"discard_from_hand"`` の ``cards`` は全員に見える（トラッシュは表を上にして置く公開の情報。
    p.312）。オーキドはかせの ``discard_hand``（手札をすべて。ログの監査は手札の組み立て直しと同じことを確かめる）とは別のイベント。
    v0.42: 特殊能力（わるいユンゲラーの［ぶっしつこうかん］）でトラッシュしたときは、ログに ``power``（``PowerKey`` の文字列）を書く（トレーナーの
    使うための条件でトラッシュしたログは v0.41 と同じ形）。
    """
    p = state.players[player]
    if len(set(cards)) != len(cards) or any(uid not in p.hand for uid in cards):
        raise RuntimeError(f"プレイヤー {player} の手札のカード {cards} をトラッシュできない（確認の漏れ。エンジンの不具合）")
    discarded = _hand_to_discard(state, player, tuple(uid for uid in p.hand if uid in cards))
    extra = {} if power is None else {"power": power}
    state.add_event("discard_from_hand", player=player, cards=discarded, **extra)
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


def search_deck_to_hand(state: GameState, player: int, card: int, *, power: str | None = None) -> None:
    """自分の山札のカード ``card`` を、同じ uid のまま手札の最後に加える（v0.22。パソコン通信の「あなたの山札からカードを1枚選び出し、
    手札に加える。」。p.260）。山札の残りの並びは変えない（切るのは呼ぶ側。``shuffle_deck``）。

    「カードを引く」（山札の一番上。p.312。``draw_cards``）ではない。選んでよいかの確認は呼ぶ側が済ませる。カードがそのプレイヤーの山札に
    ない・持ち主が違うなら、確認の漏れなので ``RuntimeError``（状態を変える前）。ログの ``"search_deck"`` の ``card`` は、選んだ
    プレイヤーにだけ見える情報（最新の説明に相手に見せる指示がない。p.312「特に指示されないかぎり、引いたカードを相手プレイヤーに見せる
    必要はありません」と同じ扱い。docs/computer-search-v0.22.md）。``player`` は全員に見える。v0.24 から、カードを動かすのは見せて
    手札に加える ``reveal_deck_to_hand`` と共通の ``_deck_to_hand``（動き・ログは v0.22 と同じ）。
    """
    _deck_to_hand(state, player, card)
    extra = {} if power is None else {"power": power}  # v0.44: 特殊能力（サカキのペルシアンの［ボスをよぶ］）で選び出したとき
    state.add_event("search_deck", player=player, card=card, **extra)


def reveal_deck_to_hand(state: GameState, player: int, card: int, *, effect: str | None = None, power: str | None = None) -> None:
    """自分の山札のカード ``card`` を、相手に見せてから、同じ uid のまま手札の最後に加える（v0.24。ポケモン交換おじさんの「あなたの山札から
    「たねポケモン」または「進化カード」を1枚選び出し、相手プレイヤーに見せてから、手札に加える。」。p.259）。山札の残りの並びは変えない
    （切るのは呼ぶ側）。

    ``search_deck_to_hand``（パソコン通信。選んだカードは選んだプレイヤーだけが見る）とは、見せることだけが違う。ログの
    ``"reveal_from_deck"`` の ``card`` は全員に見える情報（見せる指示がある）。選べたほかの山札のカードはログに書かない。選んでよいかの確認は
    呼ぶ側が済ませる。v0.38: ワザの効果（キョウのポッポの「でんれい」）で見せるときは、ログに ``effect``（ワザ）を加える（トレーナーのログの形は
    v0.24 と同じ）。v0.43: 特殊能力（わるいハクリューの［しんかのひかり］）で見せるときは ``power``（``PowerKey`` の文字列）を加える。
    """
    _deck_to_hand(state, player, card)
    extra = {} if effect is None else {"effect": effect}
    if power is not None:
        extra["power"] = power
    state.add_event("reveal_from_deck", player=player, card=card, **extra)


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


def return_hand_cards_to_deck(state: GameState, player: int, cards: tuple[int, ...], *, effect: str) -> tuple[int, ...]:
    """自分の手札のカード ``cards`` を、相手に見せずに、同じ uid のまま手札の並びの順に自分の山札の一番下にもどす（v0.44。ナツメのバリヤードの「てじな」の
    「自分の手札から最大3枚のカードを選び、山札にもどす」・_____のラッキーの「ラッキーたまご」の「自分の手札からカードを2枚選び、山札にもどして、よく切る」）。

    どちらのワザも、このあと同じワザの中で山札を切る（呼ぶ側。``shuffle_in_attack``）ので、もどす位置（一番下）は実装上の仮定（v0.24 の PT7 と同じ。結果は
    変わらない）。見せる指示がないので、ログ ``hand_to_deck`` の ``cards`` は、もどしたプレイヤーにだけ見える情報（``draw`` の ``cards`` と同じ扱い。枚数は
    ``cards`` の長さで表し、別の項目に書かない。docs/architecture-v0.2b.md 9 章）。v0.24 のポケモン交換おじさんの ``return_to_deck``（見せる。1 枚）とは別の
    イベント。選んでよいかの確認は呼ぶ側が済ませる。手札にない・持ち主の違う・重なったカードなら ``RuntimeError``（状態を変える前）。もどしたカードを返す。"""
    p = state.players[player]
    if len(set(cards)) != len(cards) or any(uid not in p.hand or state.cards[uid].owner != player for uid in cards):
        raise RuntimeError(f"プレイヤー {player} の手札のカード {cards} を山札にもどせない（確認の漏れ。エンジンの不具合）")
    returned = tuple(uid for uid in p.hand if uid in cards)
    for uid in returned:
        p.hand.remove(uid)
    p.deck.extend(returned)
    state.add_event("hand_to_deck", player=player, cards=returned, effect=effect)
    return returned


def put_discard_on_deck_top(state: GameState, owner: int, card: int, *, effect: str, chooser: int) -> None:
    """プレイヤー ``owner`` のトラッシュのカード ``card`` を、同じ uid のまま ``owner`` の山札の一番上にのせる（v0.44。カツラのマンキーの「わるいいたずら」の
    「相手のトラッシュからカードを1枚選び出し、相手の山札の上にのせる」。選ぶのはワザを使ったプレイヤー ``chooser``）。山札は切らない（説明にない）。

    トラッシュは公開の情報で、山札の一番上にのせたカードはどちらのプレイヤーも知っているので、ログ ``put_discard_on_deck_top`` の ``card`` は公開
    （``player`` はカードの持ち主、``chooser`` は選んだプレイヤー）。選んでよいかの確認は呼ぶ側が済ませる。トラッシュにない・持ち主が違うなら
    ``RuntimeError``（状態を変える前）。"""
    p = state.players[owner]
    if card not in p.discard or state.cards[card].owner != owner:
        raise RuntimeError(f"プレイヤー {owner} のトラッシュのカード {card} を山札の上にのせられない（確認の漏れ。エンジンの不具合）")
    p.discard.remove(card)
    p.deck.insert(0, card)
    state.add_event("put_discard_on_deck_top", player=owner, card=card, effect=effect, chooser=chooser)


def take_deck_top(state: GameState, owner: int, *, effect: str, looker: int) -> tuple[int, str]:
    """プレイヤー ``owner`` の山札の一番上のカードを、トレーナーカードなら ``owner`` のトラッシュに、それ以外なら ``owner`` の手札に、同じ uid のまま動かす（v0.45。
    サカキのニャースの「てつだうふり」の「相手の山札の一番上のカードを見る。そのカードが「トレーナーカード」なら、そのカードをトラッシュする。それ以外なら、そのカードを
    相手の手札に加えさせる。」。見るのはワザを使ったプレイヤー ``looker``）。「カードを引く」（p.312）ではない（ログ ``draw`` ではない）。山札は切らない（説明にない）。

    見たカードは見たプレイヤーが知り、トラッシュ（公開）か持ち主の手札（持ち主も知る）に動くので、ログ ``take_deck_top`` の ``card`` は公開（``player`` はカードの
    持ち主、``destination`` は ``"discard"``・``"hand"``）。山札が 0 枚なら確認の漏れなので ``RuntimeError``（状態を変える前）。動かしたカードと行き先を返す。"""
    p = state.players[owner]
    if not p.deck:
        raise RuntimeError(f"プレイヤー {owner} の山札が 0 枚で、一番上のカードを動かせない（確認の漏れ。エンジンの不具合）")
    card = p.deck.pop(0)
    if state.card_def(card).category == "trainer":
        p.discard.append(card)
        destination = "discard"
    else:
        p.hand.append(card)
        destination = "hand"
    state.add_event("take_deck_top", player=owner, card=card, destination=destination, effect=effect, looker=looker)
    return card, destination


def shuffle_deck(state: GameState, player: int, *, effect: str | None = None, power: str | None = None) -> None:
    """自分の山札を切る（乱数 ``state.rng`` で 1 回並べかえる。ログ ``"shuffle"``）。対戦の準備・切り直し（p.308。v0.1 から
    ``engine._shuffle_deck``）と、カードの効果で山札を切る処理（v0.22 のパソコン通信の「その後、その山札をよく切る。」。p.260）で共通。
    v0.21 までの ``engine._shuffle_deck`` の本体をそのまま関数にした（乱数の使い方・ログは同じ）。

    ``effect``（v0.40）: v0.40 から加えたワザの効果で山札を切るとき（タケシのマンキーの「ひまつぶし」・マンキーの「いたずら」・キョウのズバットの「むれでおそう」・
    わるいカイリキーの「つまみだす」）のワザの識別子。渡したときだけログに ``effect`` を書く（``player`` は切る山札の持ち主。v0.39 までの呼び出しのログの形は
    同じ）。v0.43: 特殊能力の効果で山札を切るとき（わるいハクリューの［しんかのひかり］・わるいカイリューの［てしたをよぶ］）は ``power``（``PowerKey`` の
    文字列）を書く。"""
    state.rng.shuffle(state.players[player].deck)
    extra = {} if effect is None else {"effect": effect}
    if power is not None:
        extra["power"] = power
    state.add_event("shuffle", player=player, **extra)


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


def attach_from_deck(state: GameState, player: int, card: int, pokemon: PokemonInPlay) -> None:
    """自分の山札のエネルギーカード ``card`` を、同じ uid のまま、場のポケモン ``pokemon`` の ``energy`` の最後につける（v0.41。ロケット団のヤドンの
    「ひなたぼっこ」の「自分の山札から「超」エネルギーカードを1枚選び出し、このカードにつけてよい。」）。手札を通さない（手札からつける通常の操作
    ``attach_energy_from_hand`` ではない）。山札の残りの並びは変えない（切るのは呼ぶ側）。つけてよいかの確認とログは呼ぶ側が行う。山札にない・持ち主が
    違う・つける先がそのプレイヤーの場にいないなら ``RuntimeError``（状態を変える前）。"""
    p = state.players[player]
    if card not in p.deck or state.cards[card].owner != player:
        raise RuntimeError(f"プレイヤー {player} の山札のカード {card} をつけられない（確認の漏れ。エンジンの不具合）")
    if pokemon not in p.in_play():
        raise RuntimeError(f"つける先のポケモン {pokemon.pokemon_id} がプレイヤー {player} の場にいない（エンジンの不具合）")
    p.deck.remove(card)
    pokemon.energy.append(card)


# ---------------------------------------------------------------- v0.47（docs/fossil-hidden-info-v0.47.md）


def put_trainer_into_play(state: GameState, player: int, card: int) -> PokemonInPlay:
    """使っている最中のトレーナーカード ``card``（なにかの化石・ピッピ人形。「ポケモンとして場に出すことができる」）を、同じ uid のまま自分のベンチの最後に
    ポケモンとして出す（v0.47）。カードは ``state.trainer_in_use`` から場に移る（同じカードが 2 か所にある瞬間を作らない。v0.2c の ``attach_trainer`` と同じ形）。
    場のポケモンの番号・場に出た番は手札から出すたねポケモンと同じ ``enter_play``（その番には進化できない。p.310）。

    出してよいか（ベンチの空き・番）の確認は呼ぶ側が済ませる。使っている最中のカードでない・ベンチに空きがないなら ``RuntimeError``（状態を変える前）。
    ログ ``play_trainer_as_pokemon``（``player``・``card``・``pokemon_id``。場のカードなので公開）。出した場のポケモンを返す。"""
    p = state.players[player]
    if state.trainer_in_use != TrainerInUse(player, card) or len(p.bench) >= state.rules.max_bench:
        raise RuntimeError(f"プレイヤー {player} の使用中のカード {card} をポケモンとして場に出せない（確認の漏れ。エンジンの不具合）")
    state.trainer_in_use = None
    pokemon = enter_play(state, card)
    p.bench.append(pokemon)
    state.add_event("play_trainer_as_pokemon", player=player, card=card, pokemon_id=pokemon.pokemon_id)
    return pokemon


def discard_from_play(state: GameState, player: int, pokemon: PokemonInPlay) -> tuple[int, ...]:
    """自分の場のポケモン ``pokemon``（なにかの化石・ピッピ人形。「自分の番の好きなときに（自分のトラッシュに）すてることができる」）を、ついているすべてのカードと
    いっしょに、同じ uid のまま持ち主のトラッシュに置く（v0.47）。きぜつではない（サイドは取られない。ログ ``knock_out`` ではない）。

    - トラッシュするカード: ポケモンのカード（重なりのないカード 1 枚。重なりがあれば呼ばない）・エネルギーカード（ついている順）・トレーナーカード（ついている順。
      トレーナーはつけたプレイヤーのトラッシュ。きぜつの ``knock_out`` と同じ）。ダメージカウンター・特殊状態はなくなる（p.322。カードではない）。持続する効果を
      消すのは呼ぶ側（``persistent.remove_persistent_effects``。理由 ``discard_from_play``）
    - 空いたバトル場の勝ち負けの判定・バトル場に出す決定は呼ぶ側（``resolution.after_power`` と同じ使用後の処理）
    - ログ ``discard_from_play``（``player``・``pokemon``・``pokemon_id``・``cards``（トラッシュしたカードすべて。公開）・``energy``・``trainers``・``damage``）

    トラッシュしてよいかの確認は呼ぶ側が済ませる。場にいない・重なりがある・持ち主の違うカードがあるなら ``RuntimeError``（状態を変える前）。トラッシュしたカードを返す。"""
    p = state.players[player]
    on_bench = any(b is pokemon for b in p.bench)
    if (p.active is not pokemon and not on_bench) or pokemon.evolution_stack or any(state.cards[uid].owner != player for uid in (pokemon.card, *pokemon.energy)):
        raise RuntimeError(f"プレイヤー {player} の場のポケモン {pokemon.pokemon_id} をトラッシュできない（確認の漏れ。エンジンの不具合）")
    if p.active is pokemon:
        p.active = None
    else:
        del p.bench[next(i for i, b in enumerate(p.bench) if b is pokemon)]
    trainers = tuple(t.card for t in pokemon.trainers)
    p.discard.append(pokemon.card)
    p.discard.extend(pokemon.energy)
    for attached in pokemon.trainers:
        state.players[attached.player].discard.append(attached.card)
    cards = (pokemon.card, *pokemon.energy, *trainers)
    state.add_event("discard_from_play", player=player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, cards=cards, energy=tuple(pokemon.energy),
                    trainers=trainers, damage=pokemon.damage)
    return cards


def swap_prize_with_deck_top(state: GameState, player: int, position: int, *, power: str) -> None:
    """自分のサイドの位置 ``position`` のカードと、自分の山札の一番上のカードを、どちらも裏のまま入れかえる（v0.47。コラッタ（ロケット団）の［わるふざけ］の「自分の
    サイドカードから1枚を選び、自分の山札の一番上のカードと入れ替える」）。サイドの枚数・位置と、山札の枚数・ほかのカードの並びは変えない。見る・見せる指示がない
    ので、どちらのカードも誰にも見せない（ログ ``swap_prize_with_deck_top`` は位置だけで、カードを書かない）。山札は切らない（説明にない）。

    入れかえてよいかの確認は呼ぶ側が済ませる。位置がサイドにない・山札が 0 枚なら ``RuntimeError``（状態を変える前）。"""
    p = state.players[player]
    if not 0 <= position < len(p.prizes) or not p.deck:
        raise RuntimeError(f"プレイヤー {player} のサイドの位置 {position} と山札の一番上を入れかえられない（確認の漏れ。エンジンの不具合）")
    p.prizes[position], p.deck[0] = p.deck[0], p.prizes[position]
    state.add_event("swap_prize_with_deck_top", player=player, prize_position=position, power=power)


def look_at_card(state: GameState, viewer: int, owner: int, zone: str, position: int, *, effect: str | None = None, power: str | None = None) -> int:
    """プレイヤー ``viewer`` が、プレイヤー ``owner`` の ``zone``（``"deck"``: 山札の上から ``position`` 枚目（0 から）・``"prize"``: サイドの位置・``"hand"``: 手札の
    位置）のカードを見る（v0.47。マンキーの［スパイ］・マチスのイーブイの「おどろかす」）。カードは動かさない（「見たカードは元の場所に戻す」）。

    ログ ``look_at_card``（``player``（見たプレイヤー）・``owner``・``zone``・``position``・``card``）。``card`` は見たプレイヤーにだけ見える情報（手札のカードなら
    持ち主も知っている。``observation.visible_log``）。相手にも見せる（公開する）処理ではない。見たカードの uid を返す。"""
    p = state.players[owner]
    cards = {"deck": p.deck, "prize": p.prizes, "hand": p.hand}[zone]
    if not 0 <= position < len(cards) or (effect is None) == (power is None):
        raise RuntimeError(f"プレイヤー {owner} の {zone} の位置 {position} のカードを見られない（確認の漏れ。エンジンの不具合）")
    card = cards[position]
    source = {"effect": effect} if effect is not None else {"power": power}
    state.add_event("look_at_card", player=viewer, owner=owner, zone=zone, position=position, card=card, **source)
    return card

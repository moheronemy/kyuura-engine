"""ゾーンの間でカードを動かす処理のうち、エンジンの進行とカードの効果で共通のもの。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .errors import UnsupportedError
from .stadiums import bench_limit
from .state import (
    SET_ASIDE_FACE_DOWN_BENCH,
    SET_ASIDE_HAND,
    SET_ASIDE_QUIZ,
    AttachedTrainer,
    PokemonInPlay,
    SetAsideCards,
    StadiumInPlay,
    TrainerInUse,
)

if TYPE_CHECKING:
    from .state import GameState


def enter_play(state: GameState, uid: int) -> PokemonInPlay:
    """カードを場のポケモンにする。場のポケモンの番号を新しく付ける（前に使った番号は使わない）。

    場に出た番（``played_turn``。対戦準備なら 0）を記録する。今の番に場に出したポケモンは、その番には進化できない
    （「その番の最初」には場にいなかった。p.310。v0.4a）。v0.32 から、手札から出す（``engine._enter_play``。対戦準備・ベンチに出す）と、
    ワザの効果で山札から出す（``bench_from_deck``）で共通（v0.31 までの ``engine._enter_play`` の本体をそのまま関数にした）。v0.51 から、トラッシュから持ち主の
    ベンチに出す（``bench_from_discard``）も共通。
    """
    # effects.py は zones.py を読み込むので、使うときに読み込む
    from .effects import goop_gas_entry_check

    goop_gas_entry_check(state, uid, how="enter")  # v0.59: GG1（場に出す前。番号を付ける前）
    pokemon = PokemonInPlay(uid, pokemon_id=state.next_pokemon_id, played_turn=state.turn_number)
    state.next_pokemon_id += 1
    # v0.100（docs/sketch-perish-song-history-v0.100.md 3 章）: 番でないプレイヤーのポケモンがその番に場に出たら、プレイヤーの記録（``TurnField``）に加える（「スケッチ」の
    # 「前の相手の番、このカードが場に出ていなければ」。読むカードのない対戦では何もしない）
    from .history import note_entered

    note_entered(state, state.cards[uid].owner, pokemon)
    return pokemon


SECRET_PLAN_LOST_TARGET_CODE = "UNSUPPORTED_SECRET_PLAN_LOST_TARGET"  # v0.67: おもてにしたら「たねポケモン」でなくトラッシュする対象の、残りの処理を扱えない（エンジンの未対応）

# v0.67: コマンドを処理しているあいだに、そのコマンドのプレイヤーの相手のうらのカードの本当のカードを使った（おもてにする・おもてにしたら残るかを見た）か。
# ``engine._apply`` が処理のたびに空の並びを置き、うらのカードの持ち主を加える（``designate_face_down``）。並びがあれば、受け付けるかを本当のカードによらない
# ものにするため、ありうるカードのすべてで同じコマンドを確かめる（``engine._identity_independent``）。None なら記録しない（コマンドの外・確かめの中）
IDENTITY_CONSULTED: list[int] | None = None
# v0.68（docs/final-pmcg-cards-v0.68.md 5 章）: 受け付けるかを本当のカードによらないものにする確かめ（``engine._identity_independent``）の中だけ置く、相手のうらのカードに
# ありうるカードを割り当てるもの（``assign(state, uid)``）。確かめの状態では、相手のうらのカードは割り当てる前の印（読めば止まる）にしてあり、効果の対象として指定された
# ときに初めて、公開の情報だけから作ったありうるカード（デッキの中身を使わない）のどれかを割り当てる。None なら何もしない（ふつうの処理）
IDENTITY_ORACLE = None


def place_face_down(state: GameState, player: int, card: int, *, trainer: int) -> PokemonInPlay:
    """自分の手札のカード ``card`` を、同じ uid のまま、うらにして自分のベンチの最後に出す（v0.67。マチスの秘策の「手札からカードを1枚選び、うらにしてベンチに
    出してよい。そのカードは「たねポケモン」でなくてもよく、うらになっている限り、「たねポケモン」としてあつかわれる」。docs/secret-plan-preflight-v0.67.md 3 章）。

    - 場のポケモンは手札・山札・トラッシュから出すときと同じ ``enter_play``（新しい場のポケモンの番号・場に出た番は今の番。その番には進化できない。p.310）。
      ``enter_play`` の前に ``face_down_cards`` に加えるので、場に出すときの確かめ（まきちらせ!ベトベトガスの GG1）もうらのカードの定義（特殊能力なし）を見る
    - ログ ``secret_plan_placed``（``player``・``pokemon_id``・``trainer_card``・``card``）。``card`` は持ち主だけが見る（``observation.PRIVATE_FIELDS``）

    出してよいか（手札にある・ベンチの空き）の確認は呼ぶ側が済ませる。手札にない・持ち主が違う・ベンチに空きがないなら ``RuntimeError``（状態を変える前）。"""
    p = state.players[player]
    if card not in p.hand or state.cards[card].owner != player or len(p.bench) >= bench_limit(state, player):
        raise RuntimeError(f"プレイヤー {player} の手札のカード {card} をうらにしてベンチに出せない（確認の漏れ。エンジンの不具合）")
    p.hand.remove(card)
    state.face_down_cards = (*state.face_down_cards, card)
    pokemon = enter_play(state, card)
    p.bench.append(pokemon)
    state.add_event("secret_plan_placed", player=player, pokemon_id=pokemon.pokemon_id, trainer_card=trainer, card=card)
    return pokemon


def reveal_face_down(state: GameState, owner: int, pokemon: PokemonInPlay, *, cause: str, by_player: int | None = None) -> PokemonInPlay | None:
    """うらにしてベンチに出したカード（v0.67）をおもてにする。本当のカードが「たねポケモン」なら同じ場のポケモン（同じ番号・ついているカード・場に出た番）のまま
    返し、「たねポケモン」でなければ、そのカードとついているすべてのカードを持ち主のトラッシュに置いて None を返す（「(おもてにしたカードが「たねポケモン」で
    なかったなら、そのカードと、それについているすべてのカードをトラッシュする)」）。

    - 「たねポケモン」かは本当のカード（印刷の定義 ``printed_def``）の種類と段階で決める。なにかの化石・ピッピ人形はトレーナーカード（場に出す前の分類）なので
      「たねポケモン」ではない（うらのあいだの「たねポケモン」としてのあつかいとは別）。v0.114: ベイビィポケモンカードは「たねポケモン」（マチスの秘策はネオより前のカード。
      GR-2000-P325-PRE-NEO-BABY）。おもてにしたベイビィポケモンは、そのまま場に残る
    - おもてにすることは場に出すことではない（場に出たときの特殊能力の機会・場に出た番・場のポケモンの番号は変えない）
    - トラッシュはきぜつではない（サイドは取られない。ログ ``knock_out`` ではない。きぜつしたときの特殊能力はない）。うらのあいだは、ダメージ・特殊状態・持続する
      効果・重なり・のせたカードはない（不変条件）ので、置くのはカードだけ。ついているトレーナーはつけたプレイヤーのトラッシュ（きぜつと同じ）。空いたバトル場は呼ぶ側
    - ログ ``secret_plan_revealed``（``player``・``pokemon_id``・``card``・``card_id``・``cause``・``by_player``。公開）、トラッシュしたら続けて ``secret_plan_discarded``
      （``player``・``pokemon_id``・``cards``・``energy``・``trainers``・``zone``（``active``・``bench``）。公開）

    うらのカードでない・場にいないなら ``RuntimeError``。"""
    p = state.players[owner]
    on_bench = any(b is pokemon for b in p.bench)
    if not state.is_face_down(pokemon) or (p.active is not pokemon and not on_bench) or state.cards[pokemon.card].owner != owner:
        raise RuntimeError(f"プレイヤー {owner} の場のポケモン {pokemon.pokemon_id} はうらのカードではない（エンジンの不具合）")
    if IDENTITY_ORACLE is not None:
        IDENTITY_ORACLE.assign(state, pokemon.card)  # v0.68: 確かめの中で、指定を通らずにおもてにした（起こらないはず。割り当てる前の印なら止まる）
    state.face_down_cards = tuple(uid for uid in state.face_down_cards if uid != pokemon.card)
    extra = {} if by_player is None else {"by_player": by_player}
    state.add_event("secret_plan_revealed", player=owner, pokemon_id=pokemon.pokemon_id, card=pokemon.card, card_id=state.cards[pokemon.card].card_id,
                    cause=cause, **extra)
    if _secret_plan_keeps(state, pokemon.card):
        return pokemon
    if pokemon.evolution_stack or pokemon.disguise is not None or pokemon.persistent_effects or pokemon.damage:
        raise RuntimeError(f"うらのカード {pokemon.pokemon_id} に、重なり・のせたカード・持続する効果・ダメージがある（エンジンの不具合）")
    zone = "active" if p.active is pokemon else "bench"
    returns = _energy_plan(state, pokemon, pokemon.energy, "rule")  # v0.82: リサイクルエネルギー（場をはなれる前の場で決める）
    if p.active is pokemon:
        p.active = None
    else:
        del p.bench[next(i for i, b in enumerate(p.bench) if b is pokemon)]
    energy = tuple(pokemon.energy)
    trainers = tuple(t.card for t in pokemon.trainers)
    p.discard.append(pokemon.card)
    p.discard.extend(energy)
    for attached in pokemon.trainers:
        state.players[attached.player].discard.append(attached.card)
    state.add_event("secret_plan_discarded", player=owner, pokemon_id=pokemon.pokemon_id, cards=(pokemon.card, *energy, *trainers), energy=energy,
                    trainers=trainers, zone=zone)
    _left_active(state, owner, pokemon, zone == "active")
    _return_energy(state, returns)
    return None


def _secret_plan_keeps(state: GameState, card: int) -> bool:
    """v0.114: おもてにしたうらのカードの本当のカード（印刷の定義）が、マチスの秘策の説明の「たねポケモン」か（そのまま場に残る）。マチスの秘策はネオより前のカードなので、
    ベイビィポケモンカードもふくむ（GR-2000-P325-PRE-NEO-BABY。``effects.card_is_basic_in_text`` の ``TEXT_PRE_NEO``）。なにかの化石・ピッピ人形はトレーナーカード。"""
    from .effects import TEXT_PRE_NEO, card_is_basic_in_text

    return card_is_basic_in_text(state.printed_def(card), TEXT_PRE_NEO) is True


def designate_face_down(state: GameState, owner: int, pokemon: PokemonInPlay, *, by_player: int | None, cause: str,
                        can_lose: bool) -> PokemonInPlay | None:
    """効果の対象として指定された場のポケモン ``pokemon`` がうらのカード（v0.67）なら、おもてにする（「そのカードが「ダメージや効果」を受ける時も、そのカードを
    おもてにする」・p.277 の解説の「効果の対象として指定されないかぎり、裏のままでOK」）。うらでなければそのまま返す。

    - 本当のカードが「たねポケモン」なら、おもてにして同じポケモンを返す（呼ぶ側の処理はそのまま続ける）
    - 「たねポケモン」でなければ、``can_lose``（対象がいなくなったあとの残りの処理を呼ぶ側が扱える）ならおもてにしてトラッシュし None を返す。扱えない呼ぶ側では、
      状態を変える前に ``UnsupportedError``（``UNSUPPORTED_SECRET_PLAN_LOST_TARGET``。エンジンの未対応。理由の文に本当のカードを書かない）
    - ``by_player``（効果を使うプレイヤー）が持ち主でなければ、本当のカードを使ったことを ``IDENTITY_CONSULTED`` に記録する（相手は本当のカードを知らないので、受け付けるか
      を本当のカードによらないものにする。``engine._identity_independent``）"""
    if not state.is_face_down(pokemon):
        return pokemon
    if IDENTITY_CONSULTED is not None and by_player is not None and by_player != owner:
        IDENTITY_CONSULTED.append(owner)
    if IDENTITY_ORACLE is not None:
        IDENTITY_ORACLE.assign(state, pokemon.card)
    if not _secret_plan_keeps(state, pokemon.card) and not can_lose:
        raise UnsupportedError(SECRET_PLAN_LOST_TARGET_CODE,
                               f"うらにしてベンチに出したカード（場のポケモン {pokemon.pokemon_id}）を効果の対象にした。おもてにしたカードをトラッシュしたあとの、この効果の残りの処理を"
                               "扱えない（エンジンの未対応）")
    return reveal_face_down(state, owner, pokemon, cause=cause, by_player=by_player)


def bench_from_deck(state: GameState, player: int, card: int) -> PokemonInPlay:
    """自分の山札のたねポケモンのカード ``card`` を、同じ uid のまま、手札を通さずに自分のベンチの最後に出す（v0.32。ワザの「自分の山札から「○○」を
    1匹さがしてベンチに出す」。docs/bench-search-counter-drain-v0.32.md）。場のポケモンの番号・場に出た番は手札から出すときと同じ ``enter_play``。
    山札の残りの並びは変えない（切るのは呼ぶ側。``shuffle_deck``）。

    出してよいか（名前・決定）の確認とログは呼ぶ側が行う。カードがそのプレイヤーの山札にない・持ち主が違う・たねポケモンでない・ベンチに空きが
    ないなら、確認の漏れなので ``RuntimeError``（状態を変える前）。出した場のポケモンを返す。
    """
    p = state.players[player]
    if card not in p.deck or state.cards[card].owner != player or not state.card_def(card).is_baby_or_basic_pokemon or len(p.bench) >= bench_limit(state, player):
        # v0.114: どのカードを出してよいか（説明の「たねポケモン」の範囲・ベイビィポケモン）は呼ぶ側が決める。ここは場に出せるカードの種類（たね・ベイビィ）だけを確かめる
        raise RuntimeError(f"プレイヤー {player} の山札のカード {card} をベンチに出せない（確認の漏れ。エンジンの不具合）")
    p.deck.remove(card)
    pokemon = enter_play(state, card)
    p.bench.append(pokemon)
    return pokemon


def bench_from_discard(state: GameState, card: int, *, counters: int = 0) -> PokemonInPlay:
    """トラッシュのたねポケモンのカード ``card`` を、同じ uid のまま、手札・山札を通さずに持ち主のベンチの最後に出す（v0.51。ナツメのスリーパーの「よみがえらせる」・
    元気のかけら・ポケモンの笛。docs/discard-to-bench-v0.51.md 3 章）。

    - カードの持ち主・カードを置いていたトラッシュ・出すベンチは、いつも同じプレイヤー（カードの持ち主。カードは持ち主のトラッシュにしか置かれない）。効果を使った
      プレイヤー・選んだプレイヤーとは別に決まる（ポケモンの笛は、使ったプレイヤーが相手のトラッシュから選び、相手のベンチに出る）
    - 場のポケモンの番号・場に出た番は、手札・山札から出すときと同じ ``enter_play``（新しい番号。今の番に場に出たので、その番には進化できない。p.310）。トラッシュに
      置かれる前に場にいたときのもの（ダメージ・特殊状態・ついていたカード・持続する効果・使用の記録・場のポケモンの番号）はどれも引き継がない（カードだけを動かす）
    - ``counters``: ベンチに出す前に、場のポケモンにのせておくダメージカウンターの数（元気のかけらの「…のダメージカウンターをのせた状態でベンチに出す」）。0 なら
      のせない（よみがえらせるは「ベンチに出す。そして、…のせる」なので、出したあとに呼ぶ側がのせる）
    - 手札を通さず、山札を切らない（説明にない移動・シャッフルを加えない）

    出してよいか（カードの種類・決定・ベンチの空き）の確認とログは呼ぶ側が行う。カードが持ち主のトラッシュにない・トラッシュにある間のカードの定義がたねポケモンでない
    （なにかの化石・ピッピ人形はトラッシュではトレーナーカード）・持ち主のベンチに空きがない（``stadiums.bench_limit``）・のせる数が負なら、確認の漏れなので ``RuntimeError``
    （状態を変える前）。出した場のポケモンを返す。
    """
    owner = state.cards[card].owner if card in state.cards else None
    p = None if owner is None else state.players[owner]
    if p is None or card not in p.discard or not state.card_def(card).is_baby_or_basic_pokemon or len(p.bench) >= bench_limit(state, owner) or counters < 0:
        raise RuntimeError(f"トラッシュのカード {card}（持ち主 {owner}）を持ち主のベンチに出せない（確認の漏れ。エンジンの不具合）")
    p.discard.remove(card)
    pokemon = enter_play(state, card)
    pokemon.damage = counters * state.rules.damage_per_counter
    p.bench.append(pokemon)
    return pokemon


def _require_can_leave(state: GameState, player: int, pokemon: PokemonInPlay) -> None:
    """v0.93: バトル場のポケモンを動かす前の、「バトル場をはなれられない」効果の確かめの漏れ（``persistent.require_can_leave``。ベンチのポケモンは何もしない）。"""
    if state.players[player].active is pokemon:
        from .persistent import require_can_leave

        require_can_leave(state, player, pokemon)


def _left_active(state: GameState, player: int, pokemon: PokemonInPlay, was_active: bool) -> None:
    """v0.92: プレイヤー ``player`` の ``pokemon`` がバトル場をはなれた（``was_active``）なら、説明が「このカード…がバトル場をはなれたとき、この効果は消える」と書く効果の
    うち、発生源がこのポケモンのものを消す（``persistent.remove_source_left_effects``。受けているのはほかのポケモン）。ベンチからはなれたときは何もしない。"""
    if was_active:
        from .persistent import remove_source_left_effects

        remove_source_left_effects(state, player, pokemon)


def return_in_play_to_deck(state: GameState, player: int, pokemon: PokemonInPlay, *, effect: str | None = None, trainer: int | None = None,
                           stadium: int | None = None, power: str | None = None) -> tuple[int, ...]:
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

    v0.52: トレーナーの効果（フジろうじんの「自分の控えポケモンを1匹選び、そのカードとそれについているカード全てを自分の山札にもどす」）でも使う。そのときは
    ``effect`` の代わりに ``trainer``（使っているトレーナーのカードの uid。ログの ``trainer_card``）を渡す（どちらか一方。ワザのログの形は v0.51 と同じ）。

    v0.57: スタジアムの効果（セキチクシティジムの「自分の場にいる「キョウのポケモン」を1枚選び、そのポケモンと、それについているすべてのカードを山札にもどし」）
    では ``stadium``（場のスタジアムカードの uid。ログの ``stadium_card``）を渡す（``effect``・``trainer``・``stadium`` のちょうど一つ）。

    v0.60: 特殊能力の効果（カスミのギャラドスの［はんこう］の「このカードと、これについているすべてのカードを山札にもどし」）では ``power``（``PowerKey`` の文字列。ログの
    ``power``）を渡す（``effect``・``trainer``・``stadium``・``power`` のちょうど一つ）。
    """
    p = state.players[player]
    _ninja_trick_guard(state, pokemon)  # v0.65（NT2）
    trainers = tuple(t.card for t in pokemon.trainers)
    cards = (*pokemon.cards(), *pokemon.energy, *trainers)
    on_bench = any(b is pokemon for b in p.bench)
    sources = [value for value in (effect, trainer, stadium, power) if value is not None]
    if (p.active is not pokemon and not on_bench) or any(state.cards[uid].owner != player for uid in cards) or len(sources) != 1:
        raise RuntimeError(f"プレイヤー {player} の場のポケモン {pokemon.pokemon_id} を山札にもどせない（確認の漏れ。エンジンの不具合）")
    _require_can_leave(state, player, pokemon)  # v0.93
    if p.active is pokemon:
        p.active = None
    else:
        del p.bench[next(i for i, b in enumerate(p.bench) if b is pokemon)]
    p.deck.extend(cards)
    source = ({"effect": effect} if effect is not None else {"trainer_card": trainer} if trainer is not None
              else {"stadium_card": stadium} if stadium is not None else {"power": power})
    disguise = {} if pokemon.disguise is None else {"disguise": pokemon.disguise}  # v0.49: 「ばける」でのせていた進化カード（いっしょにもどす）
    state.add_event("return_in_play_to_deck", player=player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, **source, cards=cards,
                    evolution_stack=pokemon.evolution_stack, energy=tuple(pokemon.energy), trainers=trainers, damage=pokemon.damage, **disguise)
    _left_active(state, player, pokemon, not on_bench)
    return cards


def _energy_plan(state: GameState, pokemon: PokemonInPlay, cards, cause: str, by_player: int | None = None):
    """v0.82: ``effects.energy_discard_plan``（場からトラッシュに置くエネルギーカードのうち、そのあと手札にもどすもの。動かす前に呼ぶ）。"""
    from .effects import energy_discard_plan

    return energy_discard_plan(state, pokemon, cards, cause=cause, by_player=by_player)


def _return_energy(state: GameState, plan) -> None:
    """v0.82: ``effects.return_discarded_energy``（トラッシュに置いてログを残したあとに呼ぶ）。"""
    from .effects import return_discarded_energy

    return_discarded_energy(state, plan)


def return_basic_to_hand(state: GameState, player: int, pokemon: PokemonInPlay, *, trainer: int) -> tuple[int, tuple[int, ...]]:
    """自分の場のポケモン ``pokemon`` のいちばん下のカードを、同じ uid のまま自分の手札にもどし、のっている進化カード・エネルギーカードを自分のトラッシュに
    置く（v0.52。ポケモン回収（PMCG1-092）の「自分の場のポケモン1匹を手札に戻す。そのポケモンのダメージカウンター、エネルギーカード、進化カードは全てはがして
    すてる。」。docs/field-return-v0.52.md 3 章）。

    - 手札にもどすのは、重なりのいちばん下のカード（たねポケモンのカード。場のなにかの化石・ピッピ人形なら、そのトレーナーカード）だけ。進化していなければ
      いちばん上のカード。v0.114: ベイビィから進化したポケモンは、いちばん下のベイビィポケモンカード（ポケモン回収はネオより前のカードで、ベイビィポケモンカードはたねポケモン
      カードと同様、その上のたねポケモンカードは場にあるかぎり進化カード。GR-2000-P325-PRE-NEO-BABY）。その上のたねポケモンカードはトラッシュに置く
    - トラッシュに置くのは、重なった進化カード（いちばん下より上の ``PokemonInPlay.cards()``。v0.49 の「ばける」でのせた進化カード（``disguise``）も進化カード
      なので含める）とエネルギーカード（ついている順）。ダメージカウンター・特殊状態はカードではないので、どこにも置かずになくなる（p.322。場をはなれた）
    - ついているトレーナーカード（プラスパワー・ディフェンダー）は説明に書かれていないので、ここでは扱わない（呼ぶ側が SU1 で止める。ついていたら ``RuntimeError``）
    - ``return_in_play_to_hand``（v0.42。重なったカード・ついているカードすべてを手札へ）・``discard_attached_cards``（ついているカードだけをトラッシュ。進化カードは
      動かさない）とは動かし方が違うので、使わない
    - 場をはなれたので、場のポケモンの番号は無効になる。持続する効果を消すのは呼ぶ側（``persistent.remove_persistent_effects``。理由 ``return_in_play_to_hand``）。
      きぜつではない（サイドは取られない）。空いたバトル場をうめるのは呼ぶ側（トレーナーを使い終えたあとの ``resolution.after_trainer``）
    - ログ ``return_basic_to_hand``（``player``・``pokemon``（いちばん上のカード）・``pokemon_id``・``zone``（``"active"``・``"bench"``）・``trainer_card``・
      ``card``（手札にもどしたカード）・``discarded``（トラッシュに置いたカードすべて。進化カード → エネルギー）・``evolution_cards``・``energy``・``damage``
      （なくなったダメージ）。``disguise`` は「ばける」でのせていたときだけ。場のカードなので公開）

    もどしてよいかの確認は呼ぶ側が済ませる。場にいない・持ち主の違うカードがある・トレーナーがついている（確認の漏れ）なら ``RuntimeError``（状態を変える前）。
    (手札にもどしたカード, トラッシュに置いたカード) を返す。
    """
    p = state.players[player]
    stack = pokemon.cards()
    energy = tuple(pokemon.energy)
    on_bench = any(b is pokemon for b in p.bench)
    if (p.active is not pokemon and not on_bench) or pokemon.trainers or any(state.cards[uid].owner != player for uid in (*stack, *energy)):
        raise RuntimeError(f"プレイヤー {player} の場のポケモン {pokemon.pokemon_id} を手札にもどせない（確認の漏れ。エンジンの不具合）")
    _require_can_leave(state, player, pokemon)  # v0.93
    card, evolution_cards = stack[0], stack[1:]
    discarded = (*evolution_cards, *energy)
    returns = _energy_plan(state, pokemon, energy, "trainer", player)  # v0.82: リサイクルエネルギー
    zone = "active" if p.active is pokemon else "bench"
    if p.active is pokemon:
        p.active = None
    else:
        del p.bench[next(i for i, b in enumerate(p.bench) if b is pokemon)]
    p.hand.append(card)
    p.discard.extend(discarded)
    disguise = {} if pokemon.disguise is None else {"disguise": pokemon.disguise}
    state.add_event("return_basic_to_hand", player=player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, zone=zone, trainer_card=trainer, card=card,
                    discarded=discarded, evolution_cards=evolution_cards, energy=energy, damage=pokemon.damage, **disguise)
    _left_active(state, player, pokemon, zone == "active")
    _return_energy(state, returns)
    return card, discarded


def return_in_play_to_hand(state: GameState, player: int, pokemon: PokemonInPlay, *, effect: str | None = None, power: str | None = None,
                           trainer: int | None = None, stadium: int | None = None, log_zone: bool = False) -> tuple[int, ...]:
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

    v0.56: トレーナーの効果（ロケット団員の「そのポケモンと、それについているすべてのカードを持ち主の手札にもどす」。使ったプレイヤーの相手の控えポケモン）でもどすときは
    ``trainer``（使っているトレーナーのカードの uid。ログの ``trainer_card``）を渡す（``effect``・``power``・``trainer`` のちょうど一つ）。``player`` はポケモンの持ち主で、
    行き先はいつも持ち主の手札。

    v0.57: スタジアムの効果（せまいジムの「このカードが場に出た時、ベンチにポケモンが5匹いるプレイヤーは、その中から1匹を選び、そのカードと、それについている
    すべてのカードを手札にもどす」）では ``stadium``（場に出たスタジアムカードの uid。ログの ``stadium_card``）を渡す。

    v0.73: ``log_zone`` なら、ログに ``zone``（``"active"``・``"bench"``。もどす前にいた場所）を書く（スーパーポケモン回収。自分のバトル場のポケモンを手札にもどしうる
    トレーナーのあとのバトル場に出す決定を、不変条件がこの項目で確かめる。ほかの呼び出しのログの形は v0.72 と同じ）。
    """
    p = state.players[player]
    trainers = tuple(t.card for t in pokemon.trainers)
    _ninja_trick_guard(state, pokemon)  # v0.65（NT2）
    cards = (*pokemon.cards(), *pokemon.energy, *trainers)
    on_bench = any(b is pokemon for b in p.bench)
    sources = [value for value in (effect, power, trainer, stadium) if value is not None]
    if (p.active is not pokemon and not on_bench) or any(state.cards[uid].owner != player for uid in cards) or len(sources) != 1:
        raise RuntimeError(f"プレイヤー {player} の場のポケモン {pokemon.pokemon_id} を手札にもどせない（確認の漏れ。エンジンの不具合）")
    _require_can_leave(state, player, pokemon)  # v0.93
    if p.active is pokemon:
        p.active = None
    else:
        del p.bench[next(i for i, b in enumerate(p.bench) if b is pokemon)]
    p.hand.extend(cards)
    source = ({"effect": effect} if effect is not None else {"power": power} if power is not None else {"trainer_card": trainer} if trainer is not None
              else {"stadium_card": stadium})
    disguise = {} if pokemon.disguise is None else {"disguise": pokemon.disguise}  # v0.49: 「ばける」でのせていた進化カード（いっしょにもどす）
    if log_zone:
        source["zone"] = "bench" if on_bench else "active"
    state.add_event("return_in_play_to_hand", player=player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, **source, cards=cards,
                    evolution_stack=pokemon.evolution_stack, energy=tuple(pokemon.energy), trainers=trainers, damage=pokemon.damage, **disguise)
    _left_active(state, player, pokemon, not on_bench)
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
    returns = _energy_plan(state, pokemon, energy, "attack" if effect is not None else "power", player)  # v0.82: 自分のワザ・特殊能力
    pokemon.energy.clear()
    pokemon.trainers.clear()
    p.discard.extend((*energy, *trainers))
    source = {"effect": effect} if effect is not None else {"power": power}
    state.add_event("discard_attached_cards", player=player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, **source, energy=energy,
                    trainers=trainers)
    _return_energy(state, returns)
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
    from .persistent import remove_on_entering_active

    remove_on_entering_active(state, player, p.active)  # v0.114: バトル場に出てきたら消える効果（じっとみる）
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


def discard_from_hand(state: GameState, player: int, cards: tuple[int, ...], *, power: str | None = None, stadium: int | None = None) -> tuple[int, ...]:
    """自分の手札のうち ``cards`` を、同じ uid のまま、手札の並びの順に自分のトラッシュに置く（v0.22。パソコン通信の「手札からカードを2枚
    選んでトラッシュしなければ、このカードは使えない」。p.260・p.310）。トラッシュしたカード（手札の並びの順）を返す。

    手札の一部を選んでトラッシュする処理で共通。選んでよいか（枚数・種類）の確認は呼ぶ側が、ここを呼ぶ前にすべて済ませる。答えの並びに
    よらず手札の並びの順に置く（トラッシュにはカードの順番がない。p.312。同じ選択なら同じ状態になる）。使っている最中のトレーナーカード
    は手札にないので選べない。ログの ``"discard_from_hand"`` の ``cards`` は全員に見える（トラッシュは表を上にして置く公開の情報。
    p.312）。オーキドはかせの ``discard_hand``（手札をすべて。ログの監査は手札の組み立て直しと同じことを確かめる）とは別のイベント。
    v0.42: 特殊能力（わるいユンゲラーの［ぶっしつこうかん］）でトラッシュしたときは、ログに ``power``（``PowerKey`` の文字列）を書く（トレーナーの
    使うための条件でトラッシュしたログは v0.41 と同じ形）。v0.57: 場のスタジアムが加えた使うための条件（リムーブ禁止ジム）でトラッシュしたときは ``stadium``（スタジアム
    カードの uid。ログの ``stadium_card``）を書く。
    """
    p = state.players[player]
    if len(set(cards)) != len(cards) or any(uid not in p.hand for uid in cards):
        raise RuntimeError(f"プレイヤー {player} の手札のカード {cards} をトラッシュできない（確認の漏れ。エンジンの不具合）")
    discarded = _hand_to_discard(state, player, tuple(uid for uid in p.hand if uid in cards))
    extra = {} if power is None else {"power": power}
    if stadium is not None:
        extra["stadium_card"] = stadium
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


def return_hand_cards_to_deck(state: GameState, player: int, cards: tuple[int, ...], *, effect: str | None = None,
                              trainer: int | None = None, power: str | None = None) -> tuple[int, ...]:
    """自分の手札のカード ``cards`` を、相手に見せずに、同じ uid のまま手札の並びの順に自分の山札の一番下にもどす（v0.44。ナツメのバリヤードの「てじな」の
    「自分の手札から最大3枚のカードを選び、山札にもどす」・_____のラッキーの「ラッキーたまご」の「自分の手札からカードを2枚選び、山札にもどして、よく切る」）。

    どちらのワザも、このあと同じワザの中で山札を切る（呼ぶ側。``shuffle_in_attack``）ので、もどす位置（一番下）は実装上の仮定（v0.24 の PT7 と同じ。結果は
    変わらない）。見せる指示がないので、ログ ``hand_to_deck`` の ``cards`` は、もどしたプレイヤーにだけ見える情報（``draw`` の ``cards`` と同じ扱い。枚数は
    ``cards`` の長さで表し、別の項目に書かない。docs/architecture-v0.2b.md 9 章）。v0.24 のポケモン交換おじさんの ``return_to_deck``（見せる。1 枚）とは別の
    イベント。選んでよいかの確認は呼ぶ側が済ませる。手札にない・持ち主の違う・重なったカードなら ``RuntimeError``（状態を変える前）。もどしたカードを返す。

    v0.53: トレーナーの効果（エリカのお付きの使うための条件・メンテナンス。どちらも見せる指示がない）でもどすときは、ワザの ``effect`` のかわりに ``trainer``（使っている
    トレーナーのカードの uid。ログの ``trainer_card``）を渡す（ちょうど一方。ワザのログの形は v0.52 と同じ）。

    v0.96: 特殊能力の効果（アンノーン[E] の［ENGAGE］の「自分の手札をすべて山札にもどしてよい」。このあと同じ処理の中で山札を切る）は ``power``（ログの ``power``）を渡す
    （``effect``・``trainer``・``power`` のちょうど一つ。ワザ・トレーナーのログの形は v0.95 と同じ）。"""
    source = _effect_source("手札を山札にもどす効果", trainer, effect, power)
    returned = _hand_to_deck_bottom(state, player, cards)
    state.add_event("hand_to_deck", player=player, cards=returned, **source)
    return returned


def return_revealed_hand_cards_to_deck(state: GameState, player: int, cards: tuple[int, ...], *, trainer: int) -> tuple[int, ...]:
    """見せた手札（``reveal_hand`` のすぐあと）のカード ``cards`` を、同じ uid のまま手札の並びの順に自分の山札の一番下にもどす（v0.54。ミニスカートの「お互いの
    プレイヤーは手札を見せ合い、手札にあるトレーナーカードを全て山札に戻す」）。``return_hand_cards_to_deck`` と同じ動き（一番下にもどすのは、このあと必ず切るので
    実装上の仮定）で、もどしたカードは見せたカードなのでログ ``revealed_hand_to_deck`` の ``cards`` は公開。もどしてよいかの確認は呼ぶ側が済ませる。"""
    returned = _hand_to_deck_bottom(state, player, cards)
    state.add_event("revealed_hand_to_deck", player=player, cards=returned, trainer_card=trainer)
    return returned


def _hand_to_deck_bottom(state: GameState, player: int, cards: tuple[int, ...]) -> tuple[int, ...]:
    p = state.players[player]
    if len(set(cards)) != len(cards) or any(uid not in p.hand or state.cards[uid].owner != player for uid in cards):
        raise RuntimeError(f"プレイヤー {player} の手札のカード {cards} を山札にもどせない（確認の漏れ。エンジンの不具合）")
    returned = tuple(uid for uid in p.hand if uid in cards)
    for uid in returned:
        p.hand.remove(uid)
    p.deck.extend(returned)
    return returned


def reveal_hand(state: GameState, player: int, *, trainer: int) -> tuple[int, ...]:
    """プレイヤー ``player`` が自分の手札をすべて相手に見せる（v0.54。ミニスカートの「お互いのプレイヤーは手札を見せ合い」）。カードは動かさない。ログ ``reveal_hand``
    （``cards`` は見せた手札で公開。見せたのはこの時点の手札だけで、あとで手札に加わったカードは見せない）。見せたカードを返す。"""
    cards = tuple(state.players[player].hand)
    state.add_event("reveal_hand", player=player, cards=cards, trainer_card=trainer)
    return cards


def _effect_source(what: str, trainer: int | None, effect: str | None, power: str | None) -> dict:
    """v0.95: 効果の出どころのログの項目（トレーナー ``trainer_card``・ワザ ``effect``・特殊能力 ``power`` のちょうど一つ）。ちょうど一つでなければ ``RuntimeError``（状態を変える前）。"""
    given = [(name, value) for name, value in (("trainer_card", trainer), ("effect", effect), ("power", power)) if value is not None]
    if len(given) != 1:
        raise RuntimeError(f"{what}の出どころ（トレーナー trainer・ワザ effect・特殊能力 power）はちょうど一つ（エンジンの不具合）")
    return dict(given)


def look_at_hand(state: GameState, viewer: int, owner: int, *, trainer: int | None = None, effect: str | None = None,
                 power: str | None = None) -> tuple[int, ...]:
    """プレイヤー ``viewer`` が、プレイヤー ``owner`` の手札をすべて見る（v0.54。スパイ作戦の「相手プレイヤーの手札を見る」）。カードは動かさない。ログ ``look_at_hand``
    （``player`` は見たプレイヤー、``owner`` は手札の持ち主）の ``cards`` は、見たプレイヤーと持ち主にだけ見える（観戦者・ほかの人に見せる処理ではない。
    ``observation.visible_log``）。見たのはこの時点の手札だけ。見たカードを返す（手札が 0 枚なら空）。

    v0.95: ワザの効果（オタチの「さぐる」・ゴーストの「ポルターガイスト」など）は ``effect``（ログの ``effect``）、特殊能力の効果（ヨルノズクの［みやぶる］）は ``power``
    （ログの ``power``）を、トレーナーの ``trainer``（ログの ``trainer_card``）のかわりに渡す（ちょうど一つ。トレーナーのログの形は v0.94 と同じ）。1 回見るだけで、あとで
    観測の手札を公開しない（［おみとおし］のような続けて見せる効果ではない）。"""
    source = _effect_source("手札を見る効果", trainer, effect, power)
    cards = tuple(state.players[owner].hand)
    state.add_event("look_at_hand", player=viewer, owner=owner, cards=cards, **source)
    return cards


def put_discard_on_deck_top(state: GameState, owner: int, card: int, *, effect: str | None = None, trainer: int | None = None, chooser: int) -> None:
    """プレイヤー ``owner`` のトラッシュのカード ``card`` を、同じ uid のまま ``owner`` の山札の一番上にのせる（v0.44。カツラのマンキーの「わるいいたずら」の
    「相手のトラッシュからカードを1枚選び出し、相手の山札の上にのせる」。選ぶのはワザを使ったプレイヤー ``chooser``）。山札は切らない（説明にない）。

    トラッシュは公開の情報で、山札の一番上にのせたカードはどちらのプレイヤーも知っているので、ログ ``put_discard_on_deck_top`` の ``card`` は公開
    （``player`` はカードの持ち主、``chooser`` は選んだプレイヤー）。選んでよいかの確認は呼ぶ側が済ませる。トラッシュにない・持ち主が違うなら
    ``RuntimeError``（状態を変える前）。

    v0.53: トレーナーの効果（リサイクルの「自分のトラッシュから好きなカードを1枚選び、自分の山札の1番上に置く」）では、ワザの ``effect`` のかわりに ``trainer``（使っている
    トレーナーのカードの uid。ログの ``trainer_card``）を渡す（ちょうど一方。ワザのログの形は v0.52 と同じ）。"""
    p = state.players[owner]
    if (effect is None) == (trainer is None):
        raise RuntimeError("トラッシュのカードを山札の上にのせる効果の出どころ（ワザ effect・トレーナー trainer）はちょうど一方（エンジンの不具合）")
    if card not in p.discard or state.cards[card].owner != owner:
        raise RuntimeError(f"プレイヤー {owner} のトラッシュのカード {card} を山札の上にのせられない（確認の漏れ。エンジンの不具合）")
    p.discard.remove(card)
    p.deck.insert(0, card)
    source = {"effect": effect} if effect is not None else {"trainer_card": trainer}
    state.add_event("put_discard_on_deck_top", player=owner, card=card, **source, chooser=chooser)


def return_discard_to_deck(state: GameState, player: int, cards: tuple[int, ...], *, trainer: int) -> tuple[int, ...]:
    """自分のトラッシュのカード ``cards`` を、相手に見せてから、同じ uid のままトラッシュの並びの順に自分の山札の一番下にもどす（v0.53。夜の廃品回収の「あなたの
    トラッシュから、…を最大3枚選び、相手プレイヤーに見せてから、山札にもどす。その後、その山札をよく切る。」）。山札は切らない（呼ぶ側。``shuffle_deck``）。

    このあと同じ効果の中で山札を切るので、もどす位置（一番下）は実装上の仮定（v0.24 の PT7 と同じ。結果は変わらない）。トラッシュは公開の情報で、見せる指示もあるので、
    ログ ``discard_to_deck`` の ``cards`` は公開（``trainer_card`` は使っているトレーナーのカードの uid）。選んでよいかの確認は呼ぶ側が済ませる。トラッシュにない・持ち主が
    違う・同じカードを 2 回渡したなら ``RuntimeError``（状態を変える前）。もどしたカード（トラッシュの並びの順）を返す。"""
    p = state.players[player]
    if not cards or len(set(cards)) != len(cards) or any(uid not in p.discard or state.cards[uid].owner != player for uid in cards):
        raise RuntimeError(f"プレイヤー {player} のトラッシュのカード {cards} を山札にもどせない（確認の漏れ。エンジンの不具合）")
    returned = tuple(uid for uid in p.discard if uid in cards)
    for uid in returned:
        p.discard.remove(uid)
    p.deck.extend(returned)
    state.add_event("discard_to_deck", player=player, cards=returned, trainer_card=trainer)
    return returned


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


def shuffle_deck(state: GameState, player: int, *, effect: str | None = None, power: str | None = None, stadium: int | None = None,
                 shuffled_by: int | None = None) -> None:
    """自分の山札を切る（乱数 ``state.rng`` で 1 回並べかえる。ログ ``"shuffle"``）。対戦の準備・切り直し（p.308。v0.1 から
    ``engine._shuffle_deck``）と、カードの効果で山札を切る処理（v0.22 のパソコン通信の「その後、その山札をよく切る。」。p.260）で共通。
    v0.21 までの ``engine._shuffle_deck`` の本体をそのまま関数にした（乱数の使い方・ログは同じ）。

    ``effect``（v0.40）: v0.40 から加えたワザの効果で山札を切るとき（タケシのマンキーの「ひまつぶし」・マンキーの「いたずら」・キョウのズバットの「むれでおそう」・
    わるいカイリキーの「つまみだす」）のワザの識別子。渡したときだけログに ``effect`` を書く（``player`` は切る山札の持ち主。v0.39 までの呼び出しのログの形は
    同じ）。v0.43: 特殊能力の効果で山札を切るとき（わるいハクリューの［しんかのひかり］・わるいカイリューの［てしたをよぶ］）は ``power``（``PowerKey`` の
    文字列）を書く。v0.57: スタジアムの効果で山札を切るとき（セキチクシティジム）は ``stadium``（スタジアムカードの uid。ログの ``stadium_card``）を書く。
    v0.96: 山札の持ち主でないプレイヤーが切るとき（アンノーンL の［LAUGH］の「おたがいのプレイヤーは、それぞれ、相手の山札をよく切る」）は、切ったプレイヤーを ``shuffled_by``
    （ログの ``shuffled_by``）に書く（``player`` はいつも切る山札の持ち主。乱数の使い方は同じ）。"""
    state.rng.shuffle(state.players[player].deck)
    extra = {} if effect is None else {"effect": effect}
    if power is not None:
        extra["power"] = power
    if stadium is not None:
        extra["stadium_card"] = stadium
    if shuffled_by is not None:
        extra["shuffled_by"] = shuffled_by
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


def attach_trainer(state: GameState, player: int, card: int, pokemon: PokemonInPlay, discard_at_end_of_turn: int | None) -> AttachedTrainer:
    """使っている最中のトレーナーカードを、場のポケモンにつける（v0.2c。「つけて使う」トレーナー）。

    カードは ``state.trainer_in_use`` から、ついているポケモンの ``trainers`` に移る（同じカードが
    2 か所にある瞬間を作らない）。``discard_at_end_of_turn`` の番の終わりに、エンジンがトラッシュする。
    """
    if state.trainer_in_use != TrainerInUse(player, card):
        raise RuntimeError(f"使っている最中でないカード {card} をつけようとした（エンジンの不具合）")
    owner = next(i for i, side in enumerate(state.players) if any(q is pokemon for q in side.in_play()))
    designate_face_down(state, owner, pokemon, by_player=player, cause="trainer", can_lose=False)  # v0.67: つけるポケモンは効果の対象
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
    if state.trainer_in_use != TrainerInUse(player, card) or len(p.bench) >= bench_limit(state, player):
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
    _require_can_leave(state, player, pokemon)  # v0.93
    returns = _energy_plan(state, pokemon, pokemon.energy, "rule")  # v0.82: リサイクルエネルギー（場をはなれる前の場で決める）
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
    _left_active(state, player, pokemon, not on_bench)
    _return_energy(state, returns)
    return cards


def swap_prize_with_deck_top(state: GameState, player: int, position: int, *, power: str) -> None:
    """自分のサイドの位置 ``position`` のカードと、自分の山札の一番上のカードを、どちらも裏のまま入れかえる（v0.47。コラッタ（ロケット団）の［わるふざけ］の「自分の
    サイドカードから1枚を選び、自分の山札の一番上のカードと入れ替える」）。サイドの枚数・位置と、山札の枚数・ほかのカードの並びは変えない。見る・見せる指示がない
    ので、どちらのカードも誰にも見せない（ログ ``swap_prize_with_deck_top`` は位置だけで、カードを書かない）。山札は切らない（説明にない）。

    入れかえてよいかの確認は呼ぶ側が済ませる。位置がサイドにない・山札が 0 枚なら ``RuntimeError``（状態を変える前）。"""
    p = state.players[player]
    if not 0 <= position < len(p.prizes) or not p.deck:
        raise RuntimeError(f"プレイヤー {player} のサイドの位置 {position} と山札の一番上を入れかえられない（確認の漏れ。エンジンの不具合）")
    face_up = prize_left(state, p.prizes[position])  # v0.63: おもてのサイドが山札にもどったら、おもての記録から除く（山札の一番上に来たカードは裏）
    p.prizes[position], p.deck[0] = p.deck[0], p.prizes[position]
    extra = {"face_up_card": p.deck[0]} if face_up else {}  # v0.63: おもてだったカードは、動かす前から全員に見えている
    state.add_event("swap_prize_with_deck_top", player=player, prize_position=position, power=power, **extra)


def look_at_card(state: GameState, viewer: int, owner: int, zone: str, position: int, *, effect: str | None = None, power: str | None = None,
                 trainer: int | None = None) -> int:
    """プレイヤー ``viewer`` が、プレイヤー ``owner`` の ``zone``（``"deck"``: 山札の上から ``position`` 枚目（0 から）・``"prize"``: サイドの位置・``"hand"``: 手札の
    位置）のカードを見る（v0.47。マンキーの［スパイ］・マチスのイーブイの「おどろかす」）。カードは動かさない（「見たカードは元の場所に戻す」）。

    ログ ``look_at_card``（``player``（見たプレイヤー）・``owner``・``zone``・``position``・``card``）。``card`` は見たプレイヤーにだけ見える情報（手札のカードなら
    持ち主も知っている。``observation.visible_log``）。相手にも見せる（公開する）処理ではない。見たカードの uid を返す。

    v0.56: トレーナーの効果（カスミのわがままの「あなたのサイドカードから1枚を選び、おもてを見る」）で見るときは ``trainer``（ログの ``trainer_card``）を渡す（``effect``・
    ``power``・``trainer`` のちょうど一つ）。"""
    p = state.players[owner]
    cards = {"deck": p.deck, "prize": p.prizes, "hand": p.hand}[zone]
    if not 0 <= position < len(cards) or len([v for v in (effect, power, trainer) if v is not None]) != 1:
        raise RuntimeError(f"プレイヤー {owner} の {zone} の位置 {position} のカードを見られない（確認の漏れ。エンジンの不具合）")
    card = cards[position]
    source = {"effect": effect} if effect is not None else {"power": power} if power is not None else {"trainer_card": trainer}
    state.add_event("look_at_card", player=viewer, owner=owner, zone=zone, position=position, card=card, **source)
    return card


def place_disguise(state: GameState, player: int, pokemon: PokemonInPlay, card: int, *, power: str) -> None:
    """自分の手札の進化カード ``card`` を、同じ uid のまま、自分の場のポケモン ``pokemon`` の上にのせる（v0.49。タケシのキュウコンの「ばける」の「手札から「進化カード」を
    1枚選び、このカードの上にのせる」。docs/virtual-attacks-transformation-v0.49.md 4 章）。進化の重なり（``evolution_stack``）ではなく ``PokemonInPlay.disguise`` に置き、
    いちばん上のポケモンのカード（``card``）・場のポケモンの番号・場に出た番・進化した番は変えない（進化・退化ではない）。ログ ``disguise``（``player``・``pokemon``・
    ``pokemon_id``・``card``（のせたカード。手札から出したカードで公開）・``power``）。

    のせてよいかの確認は呼ぶ側が済ませる。手札にない・持ち主が違う・進化カードでない・もうのせている・場にいない（確認の漏れ）なら ``RuntimeError``（状態を変える前）。"""
    p = state.players[player]
    on_field = p.active is pokemon or any(b is pokemon for b in p.bench)
    if (card not in p.hand or state.cards[card].owner != player or not state.card_def(card).is_evolution_pokemon or pokemon.disguise is not None
            or not on_field):
        raise RuntimeError(f"プレイヤー {player} のカード {card} を場のポケモン {pokemon.pokemon_id} にのせられない（確認の漏れ。エンジンの不具合）")
    p.hand.remove(card)
    pokemon.disguise = card
    state.add_event("disguise", player=player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, card=card, power=power)


DISGUISE_REVERT = "revert"  # 自分の番にトラッシュしてもどした（``RemoveDisguise``）
DISGUISE_SPECIAL_CONDITION = "special_condition"  # ねむり・マヒ・こんらんになった（「「タケシのキュウコン」にもどる。(のせてあった「進化カード」はトラッシュされる)」）


def remove_disguise(state: GameState, player: int, pokemon: PokemonInPlay, *, reason: str, effect: str | None = None) -> int:
    """自分の場のポケモン ``pokemon`` の上に「ばける」でのせた進化カードを、持ち主のトラッシュに置き、のせる前の姿にもどす（v0.49）。``reason`` は
    ``DISGUISE_REVERT``・``DISGUISE_SPECIAL_CONDITION``。ログ ``disguise_removed``（``player``・``pokemon``・``pokemon_id``・``card``・``reason``、特殊状態にした効果が
    あれば ``effect``）。場のポケモンの番号・ダメージ・エネルギー・ついているトレーナー・持続する効果・特殊状態は変えない（進化・退化・ベンチにもどることではない）。

    のせたカードがない・場にいない（確認の漏れ）なら ``RuntimeError``（状態を変える前）。トラッシュしたカードを返す。"""
    p = state.players[player]
    card = pokemon.disguise
    on_field = p.active is pokemon or any(b is pokemon for b in p.bench)
    if card is None or not on_field or state.cards[card].owner != player or reason not in (DISGUISE_REVERT, DISGUISE_SPECIAL_CONDITION):
        raise RuntimeError(f"プレイヤー {player} の場のポケモン {pokemon.pokemon_id} の「ばける」でのせたカードをトラッシュできない（確認の漏れ。エンジンの不具合）")
    pokemon.disguise = None
    p.discard.append(card)
    extra = {} if effect is None else {"effect": effect}
    state.add_event("disguise_removed", player=player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, card=card, reason=reason, **extra)
    return card


# ---------------------------------------------------------------- v0.55（docs/instant-trainers-v0.55.md）。トレーナーの効果で、場のポケモンについているエネルギーカード・
# 山札の上のカード・相手の手札のカード・トラッシュのカードを動かす処理。どれも同じ uid・同じ持ち主のまま動かし（複製しない）、ログの ``trainer_card`` は使っている
# トレーナーのカードの uid。動かしてよいかの確認は呼ぶ側が済ませ、確認の漏れは状態を変える前に ``RuntimeError``。


def _attached_energy_cards(state: GameState, owner: int, pokemon: PokemonInPlay, cards: tuple[int, ...]) -> tuple[int, ...]:
    """``owner`` の場のポケモン ``pokemon`` についているエネルギーカード ``cards`` を、ついている順に並べたもの（v0.55）。場にいない・ついていない・持ち主が違う・同じカードを
    2 回渡したなら ``RuntimeError``。"""
    p = state.players[owner]
    if not any(x is pokemon for x in p.in_play()) or len(set(cards)) != len(cards) \
            or any(uid not in pokemon.energy or state.cards[uid].owner != owner for uid in cards):
        raise RuntimeError(f"プレイヤー {owner} の場のポケモン {pokemon.pokemon_id} についているエネルギーカード {cards} を動かせない（確認の漏れ。エンジンの不具合）")
    return tuple(uid for uid in pokemon.energy if uid in cards)


def discard_attached_energy_cards(state: GameState, owner: int, pokemon: PokemonInPlay, cards: tuple[int, ...], *, trainer: int, user: int) -> tuple[int, ...]:
    """トレーナーの効果で、``owner`` の場のポケモン ``pokemon`` についているエネルギーカード ``cards`` を、持ち主（``owner``）のトラッシュに置く（v0.55。エネルギー・
    リムーブ・超エネルギーリムーブ・いいきずぐすり・ポケモンセンターの「はがしてすてる」）。エネルギーの数（何個ぶんか）ではなく、カードを動かす。ログ
    ``trainer_discard_energy``（``player`` はカードの持ち主、``user`` はトレーナーを使ったプレイヤー。場のカードとトラッシュは公開の情報なので ``cards`` は公開）。
    ワザの効果のトラッシュ（``discard_energy``・``discard_attached_energy``）とは出どころが違うので、ログを分ける。トラッシュしたカード（ついていた順）を返す。"""
    moved = _attached_energy_cards(state, owner, pokemon, cards)
    from .effects import require_discard_not_voided

    require_discard_not_voided(state, pokemon, moved, cause="trainer", by_player=user)  # v0.101: ［KEEP］でなくなる効果は呼ぶ側が先に止める（確かめの漏れ）
    returns = _energy_plan(state, pokemon, moved, "trainer", user)  # v0.82: リサイクルエネルギー・エコロジム（相手が使ったトレーナー）
    for uid in moved:
        pokemon.energy.remove(uid)
    state.players[owner].discard.extend(moved)
    state.add_event("trainer_discard_energy", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, cards=moved, trainer_card=trainer, user=user)
    _return_energy(state, returns)
    return moved


def return_attached_energy_to_hand(state: GameState, owner: int, pokemon: PokemonInPlay, cards: tuple[int, ...], *, trainer: int) -> tuple[int, ...]:
    """トレーナーの効果で、自分（``owner``）の場のポケモン ``pokemon`` についているエネルギーカード ``cards`` を、自分の手札にもどす（v0.55。エネルギーサーキュレートの
    「はがし、手札に戻してよい」）。トラッシュ・つけなおし・手札からつける通常の操作ではない。ログ ``trainer_return_energy``（場にあったカードなので ``cards`` は公開）。
    手札にもどしたカード（ついていた順）を返す。"""
    moved = _attached_energy_cards(state, owner, pokemon, cards)
    for uid in moved:
        pokemon.energy.remove(uid)
    state.players[owner].hand.extend(moved)
    state.add_event("trainer_return_energy", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, cards=moved, trainer_card=trainer)
    return moved


def move_attached_energy(state: GameState, owner: int, source: PokemonInPlay, target: PokemonInPlay, *, trainer: int) -> tuple[int, ...]:
    """トレーナーの効果で、自分（``owner``）の場のポケモン ``source`` についているエネルギーカードをすべて、自分の場の別のポケモン ``target`` に、ついていた順のまま
    つけなおす（v0.55。ナツメの「それについているエネルギーカードをすべてはがす。そして、はがしたエネルギーカードすべてを、…別の「ナツメのポケモン」1匹につけなおす」）。
    すべてを 1 回で動かす（1 枚ずつの途中の状態を作らない）。手札からつける通常の操作の回数（``energy_attachments_this_turn``）・特殊能力でつけた枚数は変えない。
    ログ ``trainer_move_energy``（公開）。同じポケモン・場にいないなら ``RuntimeError``。動かしたカードを返す（0 枚もある）。"""
    if source is target:
        raise RuntimeError(f"エネルギーカードを、同じポケモン {source.pokemon_id} につけなおそうとした（確認の漏れ。エンジンの不具合）")
    moved = _attached_energy_cards(state, owner, source, tuple(source.energy))
    if not any(x is target for x in state.players[owner].in_play()):
        raise RuntimeError(f"つけなおす先のポケモン {target.pokemon_id} が、プレイヤー {owner} の場にいない（確認の漏れ。エンジンの不具合）")
    source.energy.clear()
    target.energy.extend(moved)
    state.add_event("trainer_move_energy", player=owner, from_pokemon_id=source.pokemon_id, to_pokemon_id=target.pokemon_id, cards=moved, trainer_card=trainer)
    return moved


def opponent_hand_card_to_deck(state: GameState, owner: int, card: int, *, looker: int, trainer: int | None = None, effect: str | None = None,
                               power: str | None = None) -> None:
    """トレーナーの効果で、プレイヤー ``owner`` の手札のカード ``card`` を、``owner`` の山札（一番下）にもどさせる（v0.55。ロケット団のおねーさんの「その中に
    トレーナーカードがあれば、1枚を選び、それを相手の山札にもどさせる」。選んだのは手札を見たプレイヤー ``looker``）。このあと同じ効果の中で山札を切るので、もどす位置は
    実装上の仮定（v0.24 の PT7 と同じ。結果は変わらない）。もどしたカードは、手札を見たプレイヤーと持ち主だけが知っている（ログ ``opponent_hand_to_deck`` の ``card`` は
    その 2 人だけに見える。``observation.PRIVATE_FIELDS``。手札の枚数が 1 枚へったことは公開）。

    v0.95: ワザの効果（わるいハッサムの「おどす」）は ``effect``、特殊能力の効果（ヨルノズクの［みやぶる］）は ``power`` を、``trainer`` のかわりに渡す（ちょうど一つ。
    ``look_at_hand`` と同じ）。手札にない・持ち主が違うカードなら ``RuntimeError``（状態を変える前）。"""
    source = _effect_source("相手の手札のカードを山札にもどす効果", trainer, effect, power)
    if card not in state.players[owner].hand or state.cards[card].owner != owner:
        raise RuntimeError(f"プレイヤー {owner} の手札のカード {card} を山札にもどせない（確認の漏れ。エンジンの不具合）")
    _hand_to_deck_bottom(state, owner, (card,))
    state.add_event("opponent_hand_to_deck", player=owner, card=card, looker=looker, **source)


def return_attached_trainer_to_deck(state: GameState, owner: int, pokemon: PokemonInPlay, card: int, *, effect: str, chooser: int) -> None:
    """プレイヤー ``owner`` の場のポケモン ``pokemon`` についているトレーナーカード ``card`` を、同じ uid のまま ``owner`` の山札（一番下）にもどす（v0.95。エイパムの「とりさる」の
    「相手の場のポケモンについている「トレーナーカード」を1枚選び、相手の山札にもどす」。選んだのはワザを使ったプレイヤー ``chooser``）。ポケモン・ほかのついているカードは
    動かさない（場をはなれるのはそのカードだけ）。このあと同じ効果の中で山札を切るので、もどす位置は実装上の仮定（PT7 と同じ。結果は変わらない）。

    ついているトレーナーは場の公開のカードなので、ログ ``attached_trainer_to_deck`` の ``card`` は公開（``player`` はカードとポケモンの持ち主、``chooser`` は選んだプレイヤー）。
    ついているトレーナーはどれもつけたプレイヤー（ポケモンの持ち主）のカード（``engine`` の不変条件）。ついていない・持ち主が違うなら ``RuntimeError``（状態を変える前）。
    ついているあいだの効果（ディフェンダー・ポケモンのどうぐなど）は、ついているカードから毎回求めるので、もどしたら残らない（v0.78 のごうだつのトラッシュと同じ）。"""
    attached = next((entry for entry in pokemon.trainers if entry.card == card), None)
    if attached is None or attached.player != owner or state.cards[card].owner != owner:
        raise RuntimeError(f"プレイヤー {owner} のポケモン {pokemon.pokemon_id} についているトレーナー {card} を山札にもどせない（確認の漏れ。エンジンの不具合）")
    pokemon.trainers.remove(attached)
    state.players[owner].deck.append(card)
    state.add_event("attached_trainer_to_deck", player=owner, card=card, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, effect=effect, chooser=chooser)


def return_attached_energy_to_deck(state: GameState, owner: int, pokemon: PokemonInPlay, card: int, *, effect: str, chooser: int) -> None:
    """プレイヤー ``owner`` の場のポケモン ``pokemon`` についているエネルギーカード ``card`` を、同じ uid のまま ``owner`` の山札（一番下）にもどす（v0.114。ムチュールの「サイコキッス」の
    「相手の場のポケモンについている「特殊エネルギーカード」を1枚選び、相手の山札にもどす」。選んだのはワザを使ったプレイヤー ``chooser``）。ポケモン・ほかのついているカードは動かさない
    （場をはなれるのはそのカードだけ）。トラッシュではない（トラッシュされたときの効果・リサイクルエネルギーの手札にもどる効果はない）。このあと同じ効果の中で山札を切るので、もどす位置は
    実装上の仮定（v0.95 の ``return_attached_trainer_to_deck`` と同じ。結果は変わらない）。

    ついているエネルギーは場の公開のカードなので、ログ ``attached_energy_to_deck`` の ``card`` は公開（``player`` はカードとポケモンの持ち主、``chooser`` は選んだプレイヤー）。エネルギー
    としての役割（［エネエネ］）の記録は、ついていないカードの記録として、コマンドの終わりに消える（``engine``）。ついていない・持ち主が違うなら ``RuntimeError``（状態を変える前）。"""
    if card not in pokemon.energy or state.cards[card].owner != owner:
        raise RuntimeError(f"プレイヤー {owner} のポケモン {pokemon.pokemon_id} についているエネルギーカード {card} を山札にもどせない（確認の漏れ。エンジンの不具合）")
    pokemon.energy.remove(card)
    state.players[owner].deck.append(card)
    state.add_event("attached_energy_to_deck", player=owner, card=card, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, effect=effect, chooser=chooser)


def take_looked_deck_cards(state: GameState, player: int, looked: int, cards: tuple[int, ...], *, trainer: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """自分の山札の上から見たカード（``look_at_deck_top`` の ``cards``。山札の上から順）のうち、``cards`` を手札に加え、残りをトラッシュする（v0.55。カスミのいかりの
    「その中から2枚を選んで手札に加え、残りをトラッシュする」）。見た部分より下の山札の並びは変えない（切らない）。手札に加えたカードは使ったプレイヤーだけが見る
    （ログ ``looked_to_hand`` の ``cards``。「カードを引く」ではない）。トラッシュしたカードは公開（ログ ``looked_to_discard``）。見たカードの範囲は呼ぶ側が決め、
    ``cards`` が見たカード（山札の上の ``looked`` 枚）にないなら ``RuntimeError``。(手札に加えたカード, トラッシュしたカード) を返す（どちらも山札の上からの順）。"""
    p = state.players[player]
    top = tuple(p.deck[:looked])
    if looked > len(p.deck) or len(set(cards)) != len(cards) or any(uid not in top for uid in cards):
        raise RuntimeError(f"山札の上の {looked} 枚 {top} から、カード {cards} を手札に加えられない（確認の漏れ。エンジンの不具合）")
    taken = tuple(uid for uid in top if uid in cards)
    rest = tuple(uid for uid in top if uid not in cards)
    del p.deck[:looked]
    p.hand.extend(taken)
    p.discard.extend(rest)
    state.add_event("looked_to_hand", player=player, cards=taken, trainer_card=trainer)
    state.add_event("looked_to_discard", player=player, cards=rest, trainer_card=trainer)
    return taken, rest


def discard_pile_to_deck(state: GameState, player: int, *, trainer: int) -> tuple[int, ...]:
    """自分のトラッシュのカードをすべて、トラッシュの並びの順に自分の山札の一番下にもどす（v0.55。トラッシュ交換の「それらをすべて山札にもどし」）。このあと同じ効果の中で
    山札を切るので、もどす位置は実装上の仮定。使っている最中のトレーナーはトラッシュにない（``trainer_in_use``）ので含まない。トラッシュは公開の情報なので、ログ
    ``discard_pile_to_deck`` の ``cards`` は公開（0 枚でも書く）。もどしたカードを返す。"""
    p = state.players[player]
    cards = tuple(p.discard)
    p.discard.clear()
    p.deck.extend(cards)
    state.add_event("discard_pile_to_deck", player=player, cards=cards, trainer_card=trainer)
    return cards


def deck_top_to_discard(state: GameState, player: int, count: int, *, trainer: int | None = None, power: str | None = None) -> tuple[int, ...]:
    """自分の山札の上から ``count`` 枚を、上から順に自分のトラッシュに置く（v0.55。トラッシュ交換の「数えた枚数のカードを山札の上から取って、トラッシュする」）。「カードを
    引く」ではない。山札が足りなければ確認の漏れ（``RuntimeError``。トラッシュ交換では、もどしたあとの山札は数えた枚数以上ある）。ログ ``deck_top_to_discard``（公開。0 枚でも
    書く）。トラッシュしたカードを返す。v0.86: 特殊能力の効果（エンテイの［おたけび］）なら ``power``（``PowerKey`` の文字列。ログの ``power``。``trainer`` とどちらか一方）。"""
    if (trainer is None) == (power is None):
        raise ValueError("山札の上からトラッシュする効果の出どころ（トレーナー・特殊能力）はどちらか一方")
    cards = discard_from_deck(state, player, count)
    source = {"trainer_card": trainer} if power is None else {"power": power}
    state.add_event("deck_top_to_discard", player=player, cards=cards, **source)
    return cards


# ---------------------------------------------------------------- v0.56（docs/trainer-decisions-turn-effects-v0.56.md 4 章）。どれも同じ uid・同じ持ち主のまま動かす


def hand_to_bench_by_effect(state: GameState, owner: int, cards: tuple[int, ...], *, chooser: int, trainer: int) -> tuple[PokemonInPlay, ...]:
    """プレイヤー ``owner`` の手札のたねポケモンのカード ``cards`` を、並びの順に ``owner`` のベンチの最後に出す（v0.56。エリカの香水の「相手の手札から「たねポケモン」を
    好きなだけ選び、相手のベンチに出させてよい」。選ぶのは使ったプレイヤー ``chooser``）。場のポケモンは手札から出すときと同じ ``enter_play`` で作る（新しい場のポケモンの
    番号・場に出た番は今の番。その番には進化できない）。1 枚ごとにログ ``trainer_bench_from_hand``（``player``（持ち主）・``card``・``pokemon_id``・``chooser``・``trainer_card``。
    場に出たカードなので公開）。出してよいか（たねポケモン・手札にある・ベンチの空き）の確認は呼ぶ側。漏れていれば ``RuntimeError``（状態を変える前）。"""
    p = state.players[owner]
    if len(set(cards)) != len(cards) or any(uid not in p.hand or state.cards[uid].owner != owner or not state.card_def(uid).is_baby_or_basic_pokemon for uid in cards) \
            or len(p.bench) + len(cards) > bench_limit(state, owner):
        raise RuntimeError(f"プレイヤー {owner} の手札のカード {cards} をベンチに出せない（確認の漏れ。エンジンの不具合）")
    placed = []
    for uid in cards:
        p.hand.remove(uid)
        pokemon = enter_play(state, uid)
        p.bench.append(pokemon)
        state.add_event("trainer_bench_from_hand", player=owner, card=uid, pokemon_id=pokemon.pokemon_id, chooser=chooser, trainer_card=trainer)
        placed.append(pokemon)
    return tuple(placed)


def hand_basic_to_active(state: GameState, player: int, card: int, *, trainer: int) -> tuple[PokemonInPlay, PokemonInPlay]:
    """自分のバトル場のポケモンをベンチの最後にもどし、手札のたねポケモンのカード ``card`` を直接バトル場に出す（v0.56。トレーナー「マチス」）。もとのバトル場のポケモンは
    場のポケモンごと（ついているカード・ダメージカウンター・重なり・番号）ベンチに移る。新しいポケモンは手札から出すときと同じ ``enter_play`` で作る（新しい場のポケモンの
    番号・場に出た番は今の番）。ログ ``trainer_hand_to_active``（``player``・``old_active``・``old_active_pokemon_id``・``card``・``pokemon_id``・``trainer_card``。公開）。
    ベンチにもどったポケモンの特殊状態・持続する効果を消すのは呼ぶ側（「にげる」・入れ替えと同じ規定）。確認（たねポケモン・手札にある・ベンチの空き・バトル場に
    ポケモンがいる）の漏れは ``RuntimeError``（状態を変える前）。(ベンチにもどったポケモン, 出したポケモン) を返す。"""
    p = state.players[player]
    old = p.active
    if old is None or card not in p.hand or state.cards[card].owner != player or not state.card_def(card).is_baby_or_basic_pokemon or len(p.bench) >= bench_limit(state, player):
        raise RuntimeError(f"プレイヤー {player} の手札のカード {card} をバトル場に出せない（確認の漏れ。エンジンの不具合）")
    _require_can_leave(state, player, old)  # v0.93
    p.hand.remove(card)
    new = enter_play(state, card)
    p.bench.append(old)
    p.active = new
    state.add_event("trainer_hand_to_active", player=player, old_active=old.card, old_active_pokemon_id=old.pokemon_id, card=card,
                    pokemon_id=new.pokemon_id, trainer_card=trainer)
    _left_active(state, player, old, True)
    return old, new


def hand_positions_to_deck(state: GameState, owner: int, positions: tuple[int, ...], *, chooser: int, trainer: int) -> tuple[int, ...]:
    """プレイヤー ``owner`` の手札の位置 ``positions``（0 から。おもてを見ないで選んだ位置）のカードを、手札の並びの順に ``owner`` の山札の一番下にもどす（v0.56。
    ロケット団のワナの「相手の手札から、おもてを見ないで最大3枚を選び、相手の山札にもどす」。選ぶのは使ったプレイヤー ``chooser``）。位置からカードを、動かす前に
    すべて決める（1 枚動かしたあとの位置で次を決めない）。もどす位置（一番下）は実装上の仮定（このあと必ず切る。v0.24 の PT7 と同じ）。ログ ``hand_positions_to_deck``
    （``player``（持ち主）・``chooser``・``positions``（公開）・``cards``（持ち主だけが見る）・``trainer_card``）。もどしたカードを返す。"""
    p = state.players[owner]
    if len(set(positions)) != len(positions) or any(not 0 <= i < len(p.hand) for i in positions):
        raise RuntimeError(f"プレイヤー {owner} の手札の位置 {positions} のカードをもどせない（確認の漏れ。エンジンの不具合）")
    ordered = tuple(sorted(positions))
    cards = tuple(p.hand[i] for i in ordered)
    returned = _hand_to_deck_bottom(state, owner, cards)
    state.add_event("hand_positions_to_deck", player=owner, chooser=chooser, positions=ordered, cards=returned, trainer_card=trainer)
    return returned


def take_prize_by_trainer(state: GameState, player: int, position: int, *, trainer: int) -> int:
    """自分のサイドの位置 ``position`` のカードを取って手札に加える（v0.56。マチスの交渉の「それぞれ自分のサイドカードから1枚を選び、取って手札に加える」）。きぜつで
    取るサイド（ログ ``take_prize``。解決の基盤の ``_resume_take_prize``）とは別のイベント ``trainer_take_prize``（``player``・``position``・``card``（取ったプレイヤー
    だけが見る。きぜつで取るサイドと同じ扱い）・``remaining``・``trainer_card``）。勝ち負けの判定は、トレーナーを使い終えてから呼ぶ側がする。取ったカードを返す。"""
    p = state.players[player]
    if not 0 <= position < len(p.prizes):
        raise RuntimeError(f"プレイヤー {player} のサイドの位置 {position} のカードを取れない（確認の漏れ。エンジンの不具合）")
    card = p.prizes.pop(position)
    face_up = prize_left(state, card)  # v0.63
    p.hand.append(card)
    state.add_event("trainer_take_prize", player=player, position=position, card=card, remaining=len(p.prizes), trainer_card=trainer,
                    **face_up_fields(face_up, "card"))
    return card


def swap_prize_with_hand(state: GameState, player: int, position: int, card: int, *, trainer: int) -> int:
    """自分のサイドの位置 ``position`` のカードと、自分の手札のカード ``card`` を入れかえる（v0.56。カスミのわがままの「あなたの手札からカードを1枚選び、見たカードと交換
    する」）。サイドの枚数・位置は変えない（サイドを取ることではない）。手札に来たカードは手札の最後、サイドに置いたカードはその位置（裏のまま）。ログ
    ``swap_prize_with_hand``（``player``・``position``（公開）・``to_prize``・``to_hand``（どちらも持ち主だけが見る）・``trainer_card``）。サイドに来たカードを返す。"""
    p = state.players[player]
    if not 0 <= position < len(p.prizes) or card not in p.hand:
        raise RuntimeError(f"プレイヤー {player} のサイドの位置 {position} と手札のカード {card} を入れかえられない（確認の漏れ。エンジンの不具合）")
    taken = p.prizes[position]
    face_up = prize_left(state, taken)  # v0.63: サイドに置いた手札のカードは裏（おもてにする指示がない）
    p.hand.remove(card)
    p.prizes[position] = card
    p.hand.append(taken)
    state.add_event("swap_prize_with_hand", player=player, position=position, to_prize=card, to_hand=taken, trainer_card=trainer,
                    **face_up_fields(face_up, "to_hand"))
    return taken


# ---------------------------------------------------------------- スタジアム（v0.57。docs/stadiums-v0.57.md 2 章）


def place_stadium(state: GameState, player: int, card: int) -> StadiumInPlay | None:
    """使っている最中のスタジアムカード ``card``（持ち主 ``player``）を、同じ uid のまま場（両方の場の境界線上）に出す（v0.57）。前に場に出ていたスタジアムが
    あれば、新しいスタジアムが場に出たので、それを持ち主のトラッシュにすてる（``discard_stadium``。印刷の文面「別のスタジアムカードが場に出た時、このカードを
    トラッシュする」・「新しいスタジアムカードが場に出た時、古いスタジアムカードはトラッシュされる」。同じ名前のスタジアムも別のカードなので同じ）。

    - 順番: 新しいスタジアムを場に出す（ログ ``stadium_placed``。``replaces`` は古いスタジアムのカード）→ 古いスタジアムをトラッシュする（ログ ``stadium_discarded``。
      理由 ``replaced``）。古いスタジアムの効果は、この時点で場からなくなる（効果を状態に写していないので、残らない）
    - カードは ``state.trainer_in_use`` から場に移る（同じカードが 2 か所にある瞬間を作らない。v0.2c の ``attach_trainer`` と同じ形）。使いすてのトレーナーとして
      トラッシュしない
    使っている最中のカードが ``card`` でなければ、確認の漏れなので ``RuntimeError``（状態を変える前）。トラッシュにすてた古いスタジアムを返す（なければ None）。"""
    if state.trainer_in_use != TrainerInUse(player, card):
        raise RuntimeError(f"使用中のトレーナー {state.trainer_in_use} が、場に出すスタジアム {card}（プレイヤー {player}）ではない（エンジンの不具合）")
    old = state.stadium
    state.trainer_in_use = None
    state.stadium = StadiumInPlay(owner=player, card=card, placed_turn=state.turn_number)
    state.add_event("stadium_placed", player=player, card=card, replaces=None if old is None else old.card)
    if old is not None:
        discard_stadium(state, old, reason="replaced", by_card=card)
    return old


def discard_stadium(state: GameState, stadium: StadiumInPlay, *, reason: str, by_card: int | None = None, effect: str | None = None) -> None:
    """場のスタジアム ``stadium``（または、新しいスタジアムを出す途中の古いスタジアム）を、同じ uid のまま持ち主のトラッシュにすてる（v0.57。スタジアムが場を
    はなれる共通の処理）。ログ ``stadium_discarded``（``player`` は持ち主・``card``・``reason``（``replaced``: 新しいスタジアムが場に出た）・``by_card``）。
    場から除く処理と、トラッシュに置く処理をここだけで行う（入れ替え・ワザや効果による明示的なトラッシュで共通。v0.57 の対応カードでトラッシュするのは入れ替えだけ。
    タケシのオコリザルの「おおあばれ」などは次の再利用の対象）。"""
    if state.stadium == stadium:
        state.stadium = None
    elif state.stadium is None or state.stadium.card == stadium.card:
        raise RuntimeError(f"すてるスタジアム {stadium} が場にない（エンジンの不具合）")
    state.players[stadium.owner].discard.append(stadium.card)
    extra = {} if by_card is None else {"by_card": by_card}
    if effect is not None:
        extra["effect"] = effect  # v0.58: ワザの効果でトラッシュした（タケシのゴローンの「ばくれつ」。``reason`` は ``attack``、``by_card`` はワザを使ったポケモンのカード）
    state.add_event("stadium_discarded", player=stadium.owner, card=stadium.card, reason=reason, **extra)


def discard_attached_energy_by_stadium(state: GameState, owner: int, pokemon: PokemonInPlay, card: int, *, stadium: int) -> None:
    """場のポケモン ``pokemon``（持ち主 ``owner``）についているエネルギーカード ``card`` を、同じ uid のまま持ち主のトラッシュにすてる（v0.57。タマムシシティジムの
    「自分の「エリカのポケモン」についているエネルギーカードを1枚トラッシュして」）。ログ ``stadium_discard_energy``（公開）。ついていなければ ``RuntimeError``。"""
    if card not in pokemon.energy or state.cards[card].owner != owner:
        raise RuntimeError(f"ポケモン {pokemon.pokemon_id} についていないカード {card} をトラッシュしようとした（エンジンの不具合）")
    returns = _energy_plan(state, pokemon, (card,), "stadium", owner)  # v0.82: リサイクルエネルギー
    pokemon.energy.remove(card)
    state.players[owner].discard.append(card)
    state.add_event("stadium_discard_energy", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, card=card, stadium_card=stadium)
    _return_energy(state, returns)


def return_attached_energy_by_stadium(state: GameState, owner: int, pokemon: PokemonInPlay, card: int, *, stadium: int) -> None:
    """場のポケモン ``pokemon``（持ち主 ``owner``）についているエネルギーカード ``card`` を、同じ uid のまま持ち主の手札に加える（v0.57。ヤマブキシティジムの
    「自分の「ナツメのポケモン」についている「基本エネルギーカード」をはがし、手札に加えてよい」）。ログ ``stadium_return_energy``（場のカードなので公開）。"""
    if card not in pokemon.energy or state.cards[card].owner != owner:
        raise RuntimeError(f"ポケモン {pokemon.pokemon_id} についていないカード {card} を手札にもどそうとした（エンジンの不具合）")
    pokemon.energy.remove(card)
    state.players[owner].hand.append(card)
    state.add_event("stadium_return_energy", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, card=card, stadium_card=stadium)


# ---------------------------------------------------------------- 見えないカード・一時的に置くカード（v0.63。docs/hidden-card-trainers-v0.63.md）


def face_up_fields(face_up: bool, *fields: str) -> dict:
    """v0.63: ログのイベントの、おもてだった（全員に見えていた）カードの項目の印（``observation.visible_event`` が、その項目を全員に見せる）。おもてでなければ空（ログの形は
    v0.62 と同じ）。"""
    return {"face_up": tuple(fields)} if face_up else {}


def prize_left(state: GameState, card: int) -> bool:
    """サイドのカード ``card`` がサイドをはなれるとき（取った・山札や手札と入れかえた）に呼ぶ（v0.63）。おもてのサイドの並び（``GameState.face_up_prizes``）から除き、
    おもてだったかを返す。サイドからカードを動かす処理（``take_prize_by_trainer``・``swap_prize_with_hand``・``swap_prize_with_deck_top``・解決の基盤の
    ``_resume_take_prize``）は、どれもこの関数を通る。"""
    if card not in state.face_up_prizes:
        return False
    state.face_up_prizes = tuple(uid for uid in state.face_up_prizes if uid != card)
    return True


def reveal_prizes(state: GameState, players: tuple[int, ...], *, trainer: int) -> None:
    """プレイヤー ``players`` のサイドのカードをすべておもてにする（v0.63。ロケット団参上!の「お互いのプレイヤーのサイドカード全てをおもてにして、お互いのプレイヤーに
    見えるようにする。(おもてになったサイドカードは、対戦が終わるまでそのまま)」）。カードは動かさない（サイドの位置・枚数は変えない）。

    - おもてにするのは、いまサイドにあるカード（カードごとに ``GameState.face_up_prizes`` に加える）。あとからサイドに置かれたカードは、おもてにする指示がないので裏の
      まま（くり返し使えば、そのときの裏のカードがおもてになる）
    - プレイヤーごとにログ ``prizes_revealed``（``player``・``positions``・``cards``（新しくおもてにしたカード。公開）・``trainer_card``）。新しくおもてにするカードが
      なくても書く（使ったことを残す）"""
    for player in players:
        prizes = state.players[player].prizes
        positions = tuple(i for i, uid in enumerate(prizes) if uid not in state.face_up_prizes)
        cards = tuple(prizes[i] for i in positions)
        state.face_up_prizes = state.face_up_prizes + cards
        state.add_event("prizes_revealed", player=player, positions=positions, cards=cards, trainer_card=trainer)


def reveal_prize(state: GameState, owner: int, position: int, *, trainer: int) -> int:
    """プレイヤー ``owner`` のサイドの位置 ``position`` のうらのカードを、おもてにする（v0.80。カードめくりゲームの「そのカードをおもてにして、…おもてにした「サイドカード」は、そのまま
    にしておく」）。カードは動かさない。``GameState.face_up_prizes`` に加える（サイドをはなれたら ``prize_left`` で除く。v0.63 のロケット団参上!と同じ記録）。ログ ``prize_revealed``
    （``player``・``position``・``card``（公開）・``trainer_card``）。位置にカードがない・もうおもてなら ``RuntimeError``。おもてにしたカードを返す。"""
    prizes = state.players[owner].prizes
    if not 0 <= position < len(prizes) or prizes[position] in state.face_up_prizes:
        raise RuntimeError(f"プレイヤー {owner} のサイドの位置 {position} のうらのカードをおもてにできない（確認の漏れ。エンジンの不具合）")
    card = prizes[position]
    state.face_up_prizes = state.face_up_prizes + (card,)
    state.add_event("prize_revealed", player=owner, position=position, card=card, trainer_card=trainer)
    return card


def look_at_prizes(state: GameState, viewer: int, owner: int, *, trainer: int) -> tuple[int, ...]:
    """プレイヤー ``viewer`` が、プレイヤー ``owner`` のサイドをすべて見る（v0.80。にせオーキドの発明の「相手の「サイドカード」を、すべて見る」）。カードは動かさない。ログ
    ``look_at_prizes``（``cards`` は見たプレイヤーだけ。サイドの持ち主も見ない）。見たカード（サイドの並び）を返す。"""
    cards = tuple(state.players[owner].prizes)
    state.add_event("look_at_prizes", player=viewer, owner=owner, cards=cards, trainer_card=trainer)
    return cards


def prizes_to_deck(state: GameState, owner: int, *, trainer: int, looker: int) -> tuple[int, ...]:
    """プレイヤー ``owner`` のサイドをすべて、同じ uid のまま ``owner`` の山札（一番下。このあと必ず切る）にもどす（v0.80。にせオーキドの発明の「それらをすべて相手の山札に
    もどし」）。サイドを取ることではない（きぜつ・サイドを取る処理・勝ち負けの判定をしない）。おもてのサイドの記録は ``prize_left`` で除く。ログ ``prizes_to_deck``（``count`` は
    公開・``cards`` は見たプレイヤー ``looker`` だけ）。もどしたカードを返す。"""
    p = state.players[owner]
    cards = tuple(p.prizes)
    for card in cards:
        prize_left(state, card)
    p.prizes.clear()
    p.deck.extend(cards)
    state.add_event("prizes_to_deck", player=owner, count=len(cards), cards=cards, looker=looker, trainer_card=trainer)
    return cards


def deck_top_to_prizes(state: GameState, owner: int, count: int, *, trainer: int) -> tuple[int, ...]:
    """プレイヤー ``owner`` の山札の上から ``count`` 枚を、おもてを見ないで、同じ uid のまま ``owner`` のサイドに置く（v0.80。にせオーキドの発明の「相手の山札の上から、
    もどした枚数ぶんのカードを、おもてを見ないで引いて、相手の「サイドカード」におく」）。「カードを引く」（p.312）ではない（手札に加えない）。だれも見ない（ログ
    ``deck_top_to_prizes`` は ``count`` だけ。カードを書かない）。山札が足りないなら ``RuntimeError``。置いたカードを返す。"""
    p = state.players[owner]
    if count > len(p.deck):
        raise RuntimeError(f"プレイヤー {owner} の山札 {len(p.deck)} 枚から {count} 枚をサイドに置けない（エンジンの不具合）")
    cards = tuple(p.deck[:count])
    del p.deck[:count]
    p.prizes.extend(cards)
    state.add_event("deck_top_to_prizes", player=owner, count=count, trainer_card=trainer)
    return cards


def _add_set_aside(state: GameState, group: SetAsideCards) -> None:
    if not group.cards:
        raise RuntimeError(f"置いておくカードのない {group}（エンジンの不具合）")
    state.set_aside = state.set_aside + (group,)


def set_aside_hand(state: GameState, owner: int, *, user: int, trainer: int, card_id: str, return_turn: int) -> tuple[int, ...]:
    """プレイヤー ``owner`` の手札をすべて、同じ uid のまま、うらにして置いておく（v0.63。くすぐりマシーンの「相手プレイヤーは、いま手札として持っているカードをすべて、
    うらにして置いておく。置いたカードは、相手プレイヤーの手札とはみなされない。(相手プレイヤーは、それらのカードを見ることも、使うこともできない)」）。

    - 手札から ``SET_ASIDE_HAND`` の場所に移す（手札に「使えない」印を付けて残さない）。だれも中身を見られない（``visible_to`` は空。持ち主も見られない）
    - ``return_turn``: その番の終わりに持ち主の手札にもどす（``return_set_aside``。``procedures.expire_at_turn_end``）
    - 手札が 0 枚なら置かない（まとまりを作らない）。ログ ``set_aside_hand``（``player`` は持ち主・``user``・``count``・``cards``（だれにも見せない）・``return_turn``・
      ``trainer_card``）は 0 枚でも書く。置いたカードを返す"""
    p = state.players[owner]
    cards = tuple(p.hand)
    p.hand.clear()
    if cards:
        _add_set_aside(state, SetAsideCards(SET_ASIDE_HAND, owner, cards, (), user, trainer, card_id, state.turn_number, return_turn))
    state.add_event("set_aside_hand", player=owner, user=user, count=len(cards), cards=cards, return_turn=return_turn, trainer_card=trainer)
    return cards


def set_aside_face_down_bench(state: GameState, owner: int, cards: tuple[int, ...], *, user: int, trainer: int, card_id: str) -> None:
    """プレイヤー ``owner`` の山札のたねポケモンのカード ``cards`` を、同じ uid のまま、うらにしてベンチに出す（v0.63。たたきつけろ!挑戦状の「それぞれの山札から
    好きなだけポケモンカード(進化カード以外)を選び出し、ベンチに出す。(お互いが出し終わるまで、ポケモンはうらにしておく)」）。

    - 山札から ``SET_ASIDE_FACE_DOWN_BENCH`` の場所に移す。場のポケモンにはしない（うらのあいだは名前・タイプ・ワザ・特殊能力・履歴がない。表にするとき
      ``reveal_face_down_bench`` が場に出す）。中身は持ち主だけが見る（``visible_to`` は持ち主）。枚数は見える
    - 出してよいか（たねポケモン・ベンチの空き・決定）の確かめは呼ぶ側。山札にない・持ち主が違う・空なら ``RuntimeError``（状態を変える前）
    - ログ ``face_down_bench``（``player``・``count``・``cards``（持ち主だけ）・``trainer_card``）"""
    p = state.players[owner]
    if not cards or len(set(cards)) != len(cards) or any(uid not in p.deck or state.cards[uid].owner != owner for uid in cards):
        raise RuntimeError(f"プレイヤー {owner} の山札のカード {cards} をうらにしてベンチに出せない（確認の漏れ。エンジンの不具合）")
    for uid in cards:
        p.deck.remove(uid)
    _add_set_aside(state, SetAsideCards(SET_ASIDE_FACE_DOWN_BENCH, owner, tuple(cards), (owner,), user, trainer, card_id, state.turn_number))
    state.add_event("face_down_bench", player=owner, count=len(cards), cards=tuple(cards), trainer_card=trainer)


def reveal_face_down_bench(state: GameState, group: SetAsideCards) -> tuple[PokemonInPlay, ...]:
    """うらにしてベンチに出したカード（``SET_ASIDE_FACE_DOWN_BENCH`` のまとまり ``group``）を表にして、置いた順に持ち主のベンチの最後に場のポケモンとして出す（v0.63）。
    場のポケモンの番号・場に出た番は手札・山札から出すときと同じ ``enter_play``（今の番に場に出たので、その番には進化できない）。ログ ``face_down_revealed``（``player``・
    ``cards``・``pokemon_ids``・``trainer_card``。公開）。ベンチの空きは、うらにして出したときに確かめた（そのあいだに場は変わらない）。空きがなければ ``RuntimeError``。"""
    p = state.players[group.owner]
    if group not in state.set_aside or group.kind != SET_ASIDE_FACE_DOWN_BENCH or len(p.bench) + len(group.cards) > bench_limit(state, group.owner):
        raise RuntimeError(f"うらにして出したカード {group} を表にして場に出せない（エンジンの不具合）")
    state.set_aside = tuple(g for g in state.set_aside if g is not group)
    placed = []
    for uid in group.cards:
        pokemon = enter_play(state, uid)
        p.bench.append(pokemon)
        placed.append(pokemon)
    state.add_event("face_down_revealed", player=group.owner, cards=group.cards, pokemon_ids=tuple(pk.pokemon_id for pk in placed),
                    trainer_card=group.trainer_card)
    return tuple(placed)


def set_aside_quiz_card(state: GameState, player: int, card: int, *, trainer: int, card_id: str) -> SetAsideCards:
    """自分の手札のポケモンのカード ``card`` を、同じ uid のまま、おもてを下にして置く（v0.63。カツラのクイズ その3の「あなたの手札から「ポケモン」のカードを1枚選び、
    おもてを下にして、置く」）。手札から ``SET_ASIDE_QUIZ`` の場所に移す（中身は置いたプレイヤーだけが見る）。ログ ``quiz_card_set``（``player``・``card``（置いた
    プレイヤーだけ）・``trainer_card``）。手札にない・持ち主が違うなら ``RuntimeError``。置いたまとまりを返す。"""
    p = state.players[player]
    if card not in p.hand or state.cards[card].owner != player:
        raise RuntimeError(f"プレイヤー {player} の手札にないカード {card} を置こうとした（エンジンの不具合）")
    p.hand.remove(card)
    group = SetAsideCards(SET_ASIDE_QUIZ, player, (card,), (player,), player, trainer, card_id, state.turn_number)
    _add_set_aside(state, group)
    state.add_event("quiz_card_set", player=player, card=card, trainer_card=trainer)
    return group


def return_set_aside(state: GameState, group: SetAsideCards, *, reason: str) -> tuple[int, ...]:
    """置いておいたカードのまとまり ``group`` を、同じ uid のまま、置いた順に持ち主の手札の最後にもどす（v0.63。くすぐりマシーンの期限・カツラのクイズ その3の
    「(置いたカードは、手札にもどす)」）。ログ ``set_aside_returned``（``player`` は持ち主・``cards``（持ち主だけ。クイズで表にしたカードは全員に見えている
    （``face_up``））・``reason``（``expired``・``quiz``）・``trainer_card``）。まとまりがなければ ``RuntimeError``。もどしたカードを返す。"""
    if group not in state.set_aside or group.kind == SET_ASIDE_FACE_DOWN_BENCH:
        raise RuntimeError(f"置いておいたカード {group} を手札にもどせない（エンジンの不具合）")
    state.set_aside = tuple(g for g in state.set_aside if g is not group)
    state.players[group.owner].hand.extend(group.cards)
    state.add_event("set_aside_returned", player=group.owner, cards=group.cards, reason=reason, trainer_card=group.trainer_card,
                    **face_up_fields(group.kind == SET_ASIDE_QUIZ, "cards"))
    return group.cards


def return_expired_set_aside(state: GameState) -> None:
    """v0.63: もどす番（``return_turn``）が今の番の、くすぐりマシーンで置いておいたカードを、置いた順に持ち主の手札にもどす（「次の相手の番の終わりまで」。番の終わりの
    窓。``procedures.expire_at_turn_end``）。勝敗が決まった番は番の終わりが来ないので、置いたまま残る（v0.2c のついているトレーナーと同じ）。"""
    for group in state.set_aside:
        if group.kind == SET_ASIDE_HAND and group.return_turn == state.turn_number:
            return_set_aside(state, group, reason="expired")


def _ninja_trick_guard(state: GameState, pokemon: PokemonInPlay) -> None:
    """v0.65（NT2。docs/reactive-decisions-v0.65.md 6 章）: 「バトル場をはなれた時、このカードをトラッシュする」カード（キョウ秘伝,変わり身の術。効果の登録表の
    ``discard_on_leaving_active``）がついているポケモンを、ついているカードといっしょに山札・手札にもどすなら、このカードをもどすかトラッシュするかが決まらないので止める
    （状態を変える前）。ワザの要素は、ここに来る前に問い ``ninja_trick_leaves_play`` で止める（先読みが宣言の前に見つける）。ここは特殊能力・トレーナー・スタジアムの経路の
    最後の確かめ。"""
    tricks = [t.card for t in pokemon.trainers if (entry := state.effects.trainer_entry(state.cards[t.card].card_id)) is not None
              and entry.effect.discard_on_leaving_active]
    if tricks:
        raise UnsupportedError(
            "UNRESOLVED_NINJA_TRICK_LEAVES_WITH_POKEMON",
            f"ポケモン {pokemon.pokemon_id}（変わり身の術 {tricks}）: キョウ秘伝,変わり身の術がついているポケモンを、ついているすべてのカードといっしょに山札・手札にもどす"
            "効果で、このカードもいっしょにもどすか、「そのポケモンがバトル場をはなれた時、このカードをトラッシュする」にしたがってトラッシュするかは、印刷の文面・kyuura の"
            "記録から決められないので扱わない（NT2）",
        )

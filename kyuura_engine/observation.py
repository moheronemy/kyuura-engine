"""プレイヤーに渡す観測（v0.47。docs/fossil-hidden-info-v0.47.md 5 章）。

ゲームの状態（``GameState``）とログ（``GameState.log``）は、引いたカード・山札とサイドの中身・相手の手札などの見えない情報を含む、内部の完全な記録
です（エンジンの処理と監査に使う）。この部品は、それをプレイヤー（または観戦者）に渡すときに、その人が見てよい情報だけを取り出します。画面・通信は
作らず、データの形と約束（だれに何が見えるか）だけを決めます。状態を変えず、乱数を使いません。

- ``observe(state, viewer)``: その時点の盤面の観測（``viewer`` は 0・1 のプレイヤー、``None`` は観戦者）。
  - 手札: 持ち主にだけカードが見える（ほかの人は枚数だけ）。相手の［おみとおし］（オムナイト）がはたらいているあいだは、全員に見える
    （``effects.hand_revealed_by``。はたらかなくなったら、その時点から見えない。前の観測で見えていた情報は、その観測の値として残る）
  - 山札・サイド: だれにも中身は見えない（枚数だけ。カードの uid も渡さない。uid の付け方はデッキリストの順で決まるので、uid から中身がわかる）
  - トラッシュ・場のポケモン（重なったカード・ついているカード・ダメージ・特殊状態・持続する効果）・使用中のトレーナー: 全員に見える。対戦準備で
    出したポケモンは、表にする（ログ ``reveal_pokemon``。最初の番の前）までは持ち主にだけ見える
  - 保留中の決定: 種類・決めるプレイヤー・選ぶ数は全員に見える。選べるものは決めるプレイヤーにだけ渡す。選べるものがカードなら、決めるプレイヤーに
    見えるカード（公開のゾーン・自分の手札・山札をさがす効果のその山札・見たカード）にだけカードの id を添える。位置で選ぶ決定（サイド・相手の手札・
    ［スパイ］の見る場所）は位置だけを渡す（選ぶ前に内容を漏らさない）
- ``visible_log(state, viewer)``: ログを、その人が見てよい項目だけにした写し。見えない項目は除き、``"hidden"`` に項目の名前と（並びなら）枚数を書く。
  イベントの種類ごとの見える範囲は ``PRIVATE_FIELDS``（見える人を決める関数）と ``PUBLIC_EVENTS`` に書く。どちらにもない種類は ``ValueError``
  （新しいイベントを加えたら、見える範囲を決めて表に加える。黙って全部を見せない）

内部の完全な記録（``GameState``・``GameState.log``・``state_to_dict``）を、観測のかわりにプレイヤーに渡さないでください。
"""

from __future__ import annotations

from typing import Any, Callable

from .decisions import (
    BENCH_FROM_DECK_OR_HAND,
    REVIVE_SOURCE,
    ARRANGE_DECK_TOP,
    ATTACH_FROM_DECK,
    ATTACH_FROM_DISCARD,
    ATTACH_FROM_HAND,
    ATTACH_TO_BENCH,
    BENCH_FROM_DECK,
    BENCH_FROM_DISCARD,
    DAMAGE_STEP_ORDER,
    DAMAGE_REDUCTION,
    ESP_REDO,
    OPTIONAL_DISCARD_ALL,
    JANKEN_HAND,
    OPTIONAL_DRAIN,
    SEARCH_DECK_OR_DISCARD,
    TAKE_LOOKED_POKEMON,
    SECRET_PLAN_CARD,
    SELECT_OPPONENT_PRIZE,
    TAKE_LOOKED_TRAINER,
    DISCARD_ENERGY,
    DISCARD_FROM_HAND,
    DISCARD_OPPONENT_ENERGY,
    DISCARD_TO_DECK,
    DISCARD_TO_DECK_TOP,
    ENTRY_POWER,
    REACTION_ORDER,
    REACTION_POWER,
    EVOLUTION_HEAL,
    STADIUM_RETURN_BENCH,
    USE_DISCARD_TRAINER,
    FORCED_SWITCH,
    HAND_TO_DECK,
    KNOCK_OUT_POWER,
    EXP_ALL_ENERGY,
    NINJA_TRICK,
    REACTION_SWITCH,
    BENCH_GUARD,
    ENERGY_DRAIN_DISCARD,
    MAGMA_POOL_ENERGY,
    SPLIT_FROM_DECK,
    KO_PREVENTION,
    MOVE_ENERGY,
    MOVE_OPPONENT_ENERGY,
    PEEK_CARD,
    POST_KNOCKOUT_POWER,
    PROMOTE_ACTIVE,
    RECOVER_ENERGY,
    RECOVER_POKEMON,
    RECOVER_TRAINER,
    REMOVE_COUNTERS,
    RETRIEVE_ENERGY,
    RETURN_ENERGY,
    RETURN_TO_DECK,
    SEARCH_DECK,
    SELECT_ATTACK,
    SELECT_COLOR,
    SELECT_DECK_OWNER,
    SELECT_DEVOLVE_COUNT,
    SELECT_DRAW_COUNT,
    TAKE_LOOKED_CARDS,
    DISCARD_STADIUM,
    EVOLUTION_SONG_POKEMON,
    OPPONENT_HAND_TO_DECK,
    SELECT_EXCHANGE_CARD,
    SELECT_COUNTER_COUNT,
    ACCEPT_REQUEST,
    HAND_TO_ACTIVE,
    OPPONENT_HAND_TO_BENCH,
    SELECT_HAND_POSITIONS,
    SWAP_WITH_PRIZE,
    SELECT_EVOLUTION_CARD,
    SELECT_HAND_CARD,
    SELECT_LOOK_COUNT,
    SELECT_OPPONENT_ATTACK,
    SELECT_POKEMON,
    SELECT_PRIZE_CARD,
    SELECT_SPECIAL_CONDITION,
    TAKE_PRIZE,
    CHALLENGE_BENCH,
    QUIZ_ANSWER,
    QUIZ_ATTACK,
    QUIZ_CARD,
    QUIZ_HEIGHT_ANSWER,
    value_range,
    SELECT_MARKER_COUNT,
    SELECT_ATTACHED_TRAINER,
    OPTIONAL_SHUFFLE,
    OPTIONAL_HEAL,
    SELECT_ATTACHED_SPECIAL_ENERGY,
    ALLOCATE_DAMAGE,
    HEAL_ALLOCATION,
    OPTIONAL_COIN,
    STADIUM_FROM_DISCARD,
    DECK_TOP_FROM_HAND,
    DAMAGE_OPTION,
)
from .effects import (
    JANKEN_HANDS,
    COLORS, attack_of, available_attacks, current_form, hand_revealed_by, max_hp, powers_of, resistance_of, type_readings, type_shift_determined, weakness_of,
    attached_units, card_color_readings,
)
from .interruption import public_record
from .serialize import basic_entry_record, super_transform_record, history_record, poison_mist_record, replacement_poison_record, turn_record
from .state import GameState, PokemonInPlay

VIEWERS = (0, 1, None)

# 決定の選べるものの意味（決定の種類 → 意味）。``"card"`` はカードの uid、``"pokemon"`` は場のポケモンの番号、``"position"`` は位置（サイド・手札。
# 見えないカードを位置で選ぶ）、``"peek_target"`` は［スパイ］の見る場所の番号（``context`` の ``"targets"`` の位置）、``"number"`` はそのほかの数
# （ワザの位置・順番の番号・枚数・プレイヤーなど）
OPTION_MEANINGS: dict[str, str] = {
    TAKE_PRIZE: "position", SELECT_PRIZE_CARD: "position", SELECT_HAND_CARD: "position",
    PEEK_CARD: "peek_target",
    PROMOTE_ACTIVE: "pokemon", SELECT_POKEMON: "pokemon", FORCED_SWITCH: "pokemon", KO_PREVENTION: "pokemon", KNOCK_OUT_POWER: "pokemon", ATTACH_TO_BENCH: "pokemon", NINJA_TRICK: "pokemon", REACTION_SWITCH: "pokemon", BENCH_GUARD: "pokemon",
    ENTRY_POWER: "pokemon",
    REACTION_POWER: "pokemon", REACTION_ORDER: "number",  # v0.86: 反応の特殊能力の使う機会（場のポケモンの番号）・同じ時点の反応の順番（待っている反応の位置）
    DISCARD_ENERGY: "card", RECOVER_ENERGY: "card", POST_KNOCKOUT_POWER: "card", DISCARD_FROM_HAND: "card", SEARCH_DECK: "card",
    RETURN_TO_DECK: "card", SELECT_EVOLUTION_CARD: "card", RETRIEVE_ENERGY: "card", DISCARD_OPPONENT_ENERGY: "card", RECOVER_TRAINER: "card",
    ATTACH_FROM_DISCARD: "card", BENCH_FROM_DECK: "card", ATTACH_FROM_DECK: "card", RETURN_ENERGY: "card", MOVE_ENERGY: "card",
    RECOVER_POKEMON: "card", HAND_TO_DECK: "card", DISCARD_TO_DECK_TOP: "card", MOVE_OPPONENT_ENERGY: "card", ATTACH_FROM_HAND: "card",
    ARRANGE_DECK_TOP: "card",
    DAMAGE_STEP_ORDER: "number", SELECT_ATTACK: "number", SELECT_OPPONENT_ATTACK: "number", SELECT_SPECIAL_CONDITION: "number",
    REMOVE_COUNTERS: "number", SELECT_DECK_OWNER: "number", SELECT_LOOK_COUNT: "number",
    SELECT_DEVOLVE_COUNT: "number",  # v0.50: 退化スプレーではがす枚数
    ENERGY_DRAIN_DISCARD: "card",  # v0.68: ［だつりょくえき］（場についているエネルギーカード。公開）
    MAGMA_POOL_ENERGY: "card",  # v0.87: ［やけのこり］でつけ替えるカード（場についているエネルギーカード。公開）
    SPLIT_FROM_DECK: "card",  # v0.87: ［ぶんれつ］で出す山札のカード（選べるものの数は決めるプレイヤーだけ。HIDDEN_COUNT_KINDS）
    BENCH_FROM_DISCARD: "card",  # v0.51: トラッシュ（公開）のたねポケモンのカード
    DISCARD_TO_DECK: "card",  # v0.53: 夜の廃品回収（トラッシュ（公開）のカード）
    SELECT_DRAW_COUNT: "number",  # v0.54: エリカで引く枚数
    TAKE_LOOKED_CARDS: "card",  # v0.55: カスミのいかり（見た山札の上のカード。決めるプレイヤーは見ている）
    OPPONENT_HAND_TO_DECK: "card",  # v0.55: ロケット団のおねーさん（見た相手の手札のトレーナーカード。決めるプレイヤーは見ている）
    SELECT_EXCHANGE_CARD: "card",  # v0.130: とりかえっこプリーズ（見た相手の手札のカード。決めるプレイヤーは見ている）
    SELECT_COUNTER_COUNT: "number",  # v0.55: いいきずぐすりでとりのぞく数
    SELECT_COLOR: "color",  # v0.48: ``effects.COLORS`` の位置（選べるものに色の名前を添える）
    # v0.56: 相手の答え（1 = オーケー）・見た相手の手札のたねポケモン・相手の手札の位置（おもてを見ない）・手札からバトル場に出すたねポケモン・サイドと交換する手札のカード
    ACCEPT_REQUEST: "number", OPPONENT_HAND_TO_BENCH: "card", SELECT_HAND_POSITIONS: "position", HAND_TO_ACTIVE: "card", SWAP_WITH_PRIZE: "card",
    # v0.57: せまいジムでトラッシュするベンチのポケモン・トキワシティジムでカウンターをとりのぞく進化したポケモン
    STADIUM_RETURN_BENCH: "pokemon", EVOLUTION_HEAL: "pokemon",
    # v0.58: ナツメのサイキックコントロールで使う相手のトラッシュのトレーナーカード（トラッシュは公開の情報）
    USE_DISCARD_TRAINER: "card",
    # v0.63: たたきつけろ!挑戦状で山札から選ぶたねポケモン（決めるプレイヤーが自分の山札をさがす）・カツラのクイズ その3で置く手札のポケモン・伝えるワザの位置・
    # 答えるカードの名前（``context`` の ``"names"`` の位置。選べるものに名前を添える）
    CHALLENGE_BENCH: "card", QUIZ_CARD: "card", QUIZ_ATTACK: "number", QUIZ_ANSWER: "name",
    # v0.129: カツラのクイズ その1で答える身長（値で答える決定。選べるものを並べず、範囲 ``value_range`` と単位 cm を見せる）
    QUIZ_HEIGHT_ANSWER: "value",
    # v0.66: お上品攻撃で減らす量・ナツメのESPのやり直し（1 = やり直す）・カスミの勝負のじゃんけんの手（選べるものに手の名前を添える。もう 1 人の手は続きの情報にあり、見せない）
    DAMAGE_REDUCTION: "number", ESP_REDO: "number", OPTIONAL_DISCARD_ALL: "number", JANKEN_HAND: "janken", OPTIONAL_DRAIN: "pokemon", SEARCH_DECK_OR_DISCARD: "card", TAKE_LOOKED_POKEMON: "card",
    # v0.67: マチスの秘策でうらにして出す手札のカード（決めるプレイヤーの手札）
    SECRET_PLAN_CARD: "card",
    # v0.80: カードめくりゲームで選ぶ相手のサイドの位置（裏のカード）・ポケモンギアで見た 7 枚から手札に加えるトレーナーカード
    SELECT_OPPONENT_PRIZE: "position", TAKE_LOOKED_TRAINER: "card",
    # v0.84: つきくずすでトラッシュする場のスタジアム（公開）・しんかのうたで進化させる自分の場のポケモン（選べるものの数・止める選択は決めるプレイヤーだけ）
    DISCARD_STADIUM: "card", EVOLUTION_SONG_POKEMON: "pokemon",
    # v0.81: 学習装置でつけ替える、きぜつする対戦ポケモンについているエネルギーカード（場のカード。公開）
    EXP_ALL_ENERGY: "card",
    # v0.90: ボーンキラー・ころがるで取りのぞくカウンターの数（のっている数は公開）
    SELECT_MARKER_COUNT: "number",
    SELECT_ATTACHED_TRAINER: "card",  # v0.95: とりさる（相手の場のポケモンについているトレーナーカード。公開）
    OPTIONAL_SHUFFLE: "number",  # v0.95: ［わるぢえ］で見た山札を切るか（山札の持ち主の番号。0 個は切らない）
    OPTIONAL_HEAL: "pokemon",  # v0.104: プリンの「かいふく」で取り除くか（ワザを使ったポケモンの番号。0 個は取り除かない）
    SELECT_ATTACHED_SPECIAL_ENERGY: "card",  # v0.114: サイコキッス（相手の場のポケモンについている特殊エネルギーカード。公開）
    ALLOCATE_DAMAGE: "number",  # v0.115: ウォーターボム・がんせきくだき・ロックブラストの配分（``context`` の ``"table"`` の位置。配る先・単位の数は場とコイン・トラッシュの公開の情報）
    # v0.118: ふしぎなかおり・ごくらくかふんのとりのぞく数の配分（``context`` の ``"table"`` の位置。とりのぞく先・のっているカウンターの数は場の公開の情報）
    HEAL_ALLOCATION: "number",
    OPTIONAL_COIN: "number",  # v0.118: エアロウイングでコインを投げるか（1 個: 投げる・0 個: 投げない）
    STADIUM_FROM_DISCARD: "card",  # v0.118: ［じくうへんかん］で場に出すトラッシュのスタジアムカード（公開）
    DECK_TOP_FROM_HAND: "card",  # v0.118: ［トランスポート］で山札の上に置く手札のカード（決めるプレイヤーの手札。選べる数も相手に見せない）
    DAMAGE_OPTION: "pokemon",  # v0.119: ［シェルアーマー］を使うか（1 個: 使う・0 個: 使わない。選べるものはダメージを受けるポケモン。公開）
    REVIVE_SOURCE: "number",  # v0.120: たまごの化石で手札から選ぶ（0）か山札を見る（1）か（選べるもの・数は決めるプレイヤーだけに見せる）
    BENCH_FROM_DECK_OR_HAND: "card",  # v0.120: たまごの化石で山札を見たあとにベンチに出す山札・手札の進化カード（決めるプレイヤーだけに見せる）
}
# 山札の中身を選べるものにする決定（決めるプレイヤーが、効果でその山札をさがす・見たカードを並べる）。選べるもののカードは、決めるプレイヤーに見える
# v0.73: 化石の発掘（山札とトラッシュ）・マスターボール（見た山札の上の 7 枚）も、決めるプレイヤーが自分の山札を見る
# v0.88: ［ぶんれつ］で出す山札のカード（SPLIT_FROM_DECK。決めるプレイヤーが自分の山札をさがす）も。v0.87 は入れておらず、決めるプレイヤーの観測の選べるものに、見えないカードの uid が
# あることになっていた（docs/type-energy-colors-v0.88.md 1 章）
DECK_REVEALING_KINDS = frozenset({SEARCH_DECK, BENCH_FROM_DECK, ATTACH_FROM_DECK, ARRANGE_DECK_TOP, TAKE_LOOKED_CARDS, CHALLENGE_BENCH, SEARCH_DECK_OR_DISCARD,
                                  TAKE_LOOKED_POKEMON, TAKE_LOOKED_TRAINER, SPLIT_FROM_DECK,
                                  BENCH_FROM_DECK_OR_HAND})  # v0.120: たまごの化石で山札を見たあとに選ぶカード（山札と手札）
# v0.63: 決めるプレイヤーでない人に、選ぶ数・選べるものの数を見せない決定（たたきつけろ!挑戦状の山札から選ぶ決定は山札のたねポケモンの数、カツラのクイズ その3の置く
# カード・伝えるワザの決定は手札のポケモンの数・置いたカードのワザの数を漏らすため。種類と決めるプレイヤーだけを見せる）
# v0.73: 化石の発掘（山札とトラッシュの「なにかの化石」）・マスターボール（見た 7 枚のうちのポケモン）も、選べるものの数が山札の中身を漏らすので見せない
# v0.74: 山札のたねポケモンをベンチに出す決定（キョウの忍者ジムの「キョウのたねポケモン」、v0.32 からのワザ・特殊能力の山札から出すたねポケモン）も、選べるものの数・選ぶ数が
# 山札の中身を漏らすので見せない（v0.73 までは、ワザ・特殊能力の BENCH_FROM_DECK の数を決めるプレイヤーでない人にも見せていた。意図した変更）
# v0.75: 山札のカードを選ぶ決定（SEARCH_DECK。カスミのメノクラゲの「くらげのむれ」は選べるものの数だけ選べる）・山札のエネルギーカードをつける決定（ATTACH_FROM_DECK。キングラーの
# 「しおまねき」は最大 3 枚）も、選べるものの数・選ぶ数が山札の中身を漏らすので見せない（v0.74 までは、トレーナー・ワザのこの 2 つの決定の数を決めるプレイヤーでない人にも
# 見せていた。意図した変更）
# v0.80: ポケモンギアの見た 7 枚のうちのトレーナーカード（TAKE_LOOKED_TRAINER）も、選べるものの数が山札の中身を漏らすので見せない
HIDDEN_COUNT_KINDS = frozenset({SPLIT_FROM_DECK, CHALLENGE_BENCH, QUIZ_CARD, QUIZ_ATTACK, SEARCH_DECK_OR_DISCARD, TAKE_LOOKED_POKEMON, BENCH_FROM_DECK, SEARCH_DECK, ATTACH_FROM_DECK,
                                TAKE_LOOKED_TRAINER,
                                # v0.81（docs/pokemon-tools-stadiums-v0.81.md 2 章）: 決めるプレイヤーの手札（相手の手札を見た決定は、見た相手の手札）から種類でしぼったカードを
                                # 選べるものにする決定も、選べるものの数・選ぶ数が見えない手札の中身を漏らすので見せない。エネルギーアンプの段階 1・ポケモン交換おじさん
                                # （RETURN_TO_DECK）、ポケモン育て屋さん・「ばける」（SELECT_EVOLUTION_CARD）、せいちょう（ATTACH_FROM_HAND）、マチス（HAND_TO_ACTIVE）、
                                # 元気のかたまり（DISCARD_FROM_HAND の手札のエネルギーカード）、ロケット団のおねーさん（OPPONENT_HAND_TO_DECK）、エリカの香水（OPPONENT_HAND_TO_BENCH）。
                                # 同じ種類の、手札すべてを選べるものにする決定（パソコン通信など）の数も、決めるプレイヤーでない人に見せなくなる（意図した変更）
                                RETURN_TO_DECK, SELECT_EVOLUTION_CARD, ATTACH_FROM_HAND, HAND_TO_ACTIVE, DISCARD_FROM_HAND, OPPONENT_HAND_TO_DECK,
                                OPPONENT_HAND_TO_BENCH,
                                # v0.83: 見た山札の上のカードから選ぶ決定（やさしいゴルダックの「みずかき」は見た 3 枚のうちの基本エネルギーカードの数が選べるもの・選ぶ数になる）。
                                # カスミのいかり（v0.55。見た 7 枚から 2 枚）・ひかるミュウの「フラッシュサーチ」の数も、決めるプレイヤーでない人に見せなくなる（意図した変更）
                                TAKE_LOOKED_CARDS,
                                # v0.84: しんかのうたの進化させるポケモンの決定（選ぶと止めるポケモン（``unresolved_choices``）が山札の中身で決まる）
                                EVOLUTION_SONG_POKEMON,
                                # v0.118: ［トランスポート］で山札の上に置く手札のカード（引いたあとの手札の中身・選べる数を、決めるプレイヤーでない人に見せない）
                                DECK_TOP_FROM_HAND,
                                # v0.120: たまごの化石の、手札から選ぶか山札を見るか（手札に選べるカードがあるかを漏らす）・山札を見たあとの山札と手札のカード
                                REVIVE_SOURCE, BENCH_FROM_DECK_OR_HAND})
# v0.63: 選べるものがサイドの位置（決めるプレイヤーのサイド）の決定。おもてのサイド（ロケット団参上!）の位置には、カードの id を添える
PRIZE_POSITION_KINDS = frozenset({TAKE_PRIZE, SELECT_PRIZE_CARD})
# v0.55: 決めるプレイヤーが効果で見た相手の手札のカードを選べるものにする決定（ロケット団のおねーさん）。選べるもののカードは、決めるプレイヤーに見える（相手の手札を
# 続けて見せる効果ではないので、観測の手札は公開しない）
LOOKED_HAND_KINDS = frozenset({OPPONENT_HAND_TO_DECK, OPPONENT_HAND_TO_BENCH, SELECT_EXCHANGE_CARD})  # v0.56: エリカの香水も見た相手の手札から選ぶ。v0.130: とりかえっこプリーズも


def _check_viewer(viewer) -> None:
    if viewer not in VIEWERS:
        raise ValueError(f"観測する人 {viewer!r} は 0・1（プレイヤー）か None（観戦者）")


def hand_visible_to(state: GameState, owner: int, viewer: int | None) -> bool:
    """プレイヤー ``owner`` の手札のカードが ``viewer`` に見えるか（持ち主か、相手の［おみとおし］がはたらいている）。"""
    return viewer == owner or bool(hand_revealed_by(state, owner))


def _card(state: GameState, uid: int) -> dict[str, Any]:
    return {"card": uid, "card_id": state.cards[uid].card_id}


def _printed_name(item) -> dict[str, Any]:
    """v0.131（docs/exeggutor-bilingual-names-v0.131.md 7 章）: 判定に使う名前（``name_ja``。提示する日本語名）と別の、写しの原文の名前・ワザ名（``printed_name_ja``。日本語と英語の
    併記を含む表示用の値）。利用者が指定した名前の扱いのカード・ワザだけが持ち、ほかは書かない（v0.130 までの形）。"""
    return {} if item.printed_name_ja is None else {"printed_name_ja": item.printed_name_ja}


def _seen_uid(state: GameState, uid: int, viewer: int | None) -> int | None:
    """v0.122（docs/unown-fossil-retreat-reactions-v0.122.md 7 章）: 場の外の記録（番の効果・色の効果）が指すカード ``uid`` を、``viewer`` に見える場所にあるときだけ返す（見えない
    手札・山札・うらのサイド・見られない置いておくカードなら None。カードの id は記録のとおり公開）。［げんしのゆめ］を使ったオムナイトが、その番のうちに［かせきか］で手札に
    もどる場面で、手札のカードの uid を相手・観戦者に渡さない。"""
    for owner, p in enumerate(state.players):
        if uid in p.hand:
            return uid if hand_visible_to(state, owner, viewer) else None
        if uid in p.deck:
            return None
        if uid in p.prizes:
            return uid if uid in state.face_up_prizes else None
    for group in state.set_aside:
        if uid in group.cards:
            return uid if viewer in group.visible_to else None
    return uid


def _deck(state: GameState, owner: int, viewer: int | None) -> dict[str, Any]:
    """v0.126（docs/flash-faceup-deck-v0.126.md 4 章）: 山札の観測。枚数は全員に見える。フラッシュでおもてにしたカードがあれば、

    - ``face_up_count``: おもてのカードの枚数（全員。おもてにした枚数と、そのあとの公開の移動から決まる。どのカードかは書かない）
    - ``face_up_top``: いちばん上がおもてなら、そのカードの id（全員。CR-FLASH-TOP-CARD-SEEN。uid は書かない（uid はデッキの並びからカードがわかり、手札に移ったあとも追えるので））
    - ``known_face_up``: 持ち主にだけ、自分の山札のおもてのカードの位置とカードの id（自分で並べたので知っている。新しく確かめたのではない。相手・観戦者には書かない。2 枚目より下を
      新しく確かめる要求は ``CheckFaceUpDeckCard``（FU2）で、ここでは見せない）
    おもてのカードがなければ、v0.125 までと同じ形（枚数だけ）。"""
    from . import faceup

    p = state.players[owner]
    view: dict[str, Any] = {"count": len(p.deck)}
    marked = faceup.face_up_in_deck(state, owner)
    if not marked:
        return view
    top = faceup.visible_top(state, owner)
    view["face_up_count"] = len(marked)
    view["face_up_top"] = None if top is None else {"card_id": state.cards[top].card_id}
    if viewer == owner:
        view["known_face_up"] = [{"position": i, "card_id": state.cards[uid].card_id} for i, uid in enumerate(p.deck) if uid in marked]
    return view


def _face_down_pokemon(state: GameState, pokemon: PokemonInPlay, owner: int, viewer: int | None) -> dict[str, Any]:
    """v0.67（docs/secret-plan-preflight-v0.67.md 7 章）: うらにしてベンチに出したカード（マチスの秘策）。全員に見えるのは、場のポケモンの番号・うらであること・ついている
    エネルギーカード（手札からつけた表のカード）・ダメージ（うらのあいだは 0）だけ。本当のカード（uid・カードの id・名前。uid はデッキの並びからカードがわかる）は持ち主
    だけに見える。HP・タイプ・弱点・抵抗力・ワザ・特殊能力・今の姿は、うらのあいだは決まらないので書かない（持ち主にも書かない。エンジンが読まない値）。"""
    view: dict[str, Any] = {
        "pokemon_id": pokemon.pokemon_id,
        "face_down": True,
        "damage": pokemon.damage,
        "energy": [_card(state, uid) for uid in pokemon.energy],
        "trainers": [_card(state, t.card) for t in pokemon.trainers],
        "special_conditions": list(pokemon.conditions.names()),
        "persistent_effects": [effect.kind for effect in pokemon.persistent_effects],
        "markers": [_marker(marker) for marker in pokemon.markers],  # v0.90
    }
    if viewer == owner:
        view["real"] = {**_card(state, pokemon.card), "name_ja": state.printed_def(pokemon.card).name_ja, **_printed_name(state.printed_def(pokemon.card))}
    return view


def _field_pokemon(state: GameState, pokemon: PokemonInPlay, owner: int, viewer: int | None) -> dict[str, Any]:
    """v0.67: 場のポケモンの観測（うらのカードは ``_face_down_pokemon``）。"""
    if state.is_face_down(pokemon):
        return _face_down_pokemon(state, pokemon, owner, viewer)
    return _pokemon(state, pokemon, viewer)


def _pokemon(state: GameState, pokemon: PokemonInPlay, viewer: int | None = None) -> dict[str, Any]:
    """場のポケモン。v0.48: ``hp`` は今有効な最大HP（``effects.max_hp``。［ガスのからだ］・「きょだいか」を当てはめた値。エンジンの処理と同じ値）。``pokemon_type``・
    ``weakness``・``resistance`` も今有効な値（テクスチャー・［へんしょく］）。［へんしょく］で変えた色が有効か決まらない（VS1）ときは ``pokemon_type`` は None で、
    ``pokemon_type_readings`` に 2 つの読み方（変えた色・カードの定義の色）を書く（エンジンは読み方で結果が変わる処理を止める）。``type_shift`` は記録そのもの。"""
    definition = state.card_def(pokemon.card)
    readings = type_readings(state, pokemon)
    resistance, resistance_value = resistance_of(state, pokemon)
    shift = pokemon.type_shift
    return {
        "pokemon_id": pokemon.pokemon_id,
        **_card(state, pokemon.card),
        "name_ja": definition.name_ja,
        **_printed_name(definition),
        "play_role": definition.play_role,
        "hp": max_hp(state, pokemon),
        "printed_hp": definition.hp,
        "pokemon_type": _color(readings[0]) if len(readings) == 1 else None,
        "pokemon_type_readings": [_color(color) for color in readings],
        "weakness": _color(weakness_of(state, pokemon)),
        "resistance": _color(resistance),
        "resistance_value": resistance_value,
        "type_shift": None if shift is None else {"color": shift.color.value, "turn": shift.turn, "returned_to_bench": shift.returned_to_bench,
                                                  "determined": type_shift_determined(state, pokemon)},
        "evolution_stack": [_card(state, uid) for uid in pokemon.evolution_stack],
        "damage": pokemon.damage,
        "energy": [_card(state, uid) for uid in pokemon.energy],
        # v0.88: ついているエネルギーが今出すエネルギー（1 個ずつ、使える色。エンジンの ``effects.attached_units`` と同じ値。こうごうせい・エナジーコンバーター・エナジーバーン・
        # ［おいしげる］を当てはめた最初の読み方）。色の読み方が決まらないカード（CE1・CE2）があれば ``energy_units_determined`` が偽（エンジンは読み方で結果が変わる処理を止める）
        "energy_units": [sorted(color.value for color in unit) for unit in attached_units(state, pokemon)],
        "energy_units_determined": all(len(card_color_readings(state, pokemon, uid)) == 1 for uid in pokemon.energy),
        "trainers": [_card(state, t.card) for t in pokemon.trainers],
        "special_conditions": list(pokemon.conditions.names()),
        "persistent_effects": [effect.kind for effect in pokemon.persistent_effects],
        # v0.90（docs/markers-counters-v0.90.md 3 章）: のっているマーカー・ダメージカウンター以外のカウンター（のせた順。種類と、色マーカーの色。場の表の情報）
        "markers": [_marker(marker) for marker in pokemon.markers],
        # v0.49（docs/virtual-attacks-transformation-v0.49.md 9 章）: 実際のカード（``card``・``card_id``・``name_ja``。いちばん上のポケモンのカード）と、今の姿
        # （``form``。［へんしん］で同じカードとしてあつかう相手のカード・「ばける」でのせたカード）・のせたカード（``disguise``）・今持つワザ（``attacks``。印刷した
        # カード・位置・持ち方・供給するポケモン・選ぶと止める理由のコード）・今持つ特殊能力（``powers``。印刷したカード・位置）を分けて書く。どれも表のカード
        "form": _form(state, pokemon, viewer),
        "disguise": None if pokemon.disguise is None else _card(state, pokemon.disguise),
        # v0.50（docs/mew-devolution-spray-v0.50.md 7 章）: 最後に退化した番（いまの姿になった番の決まり方の材料。退化していなければ None）。進化した番・場に出た番は
        # これまでどおり書かない（ログからわかる）
        "devolved_turn": pokemon.devolved_turn,
        # v0.62（docs/history-attacks-v0.62.md 9 章）: ワザの履歴（使ったワザ・受けたワザと受けた結果・ワザ以外で受けたこと）。どれも表の情報（使った・受けたワザ、場のダメージと
        # 効果）で、見えないカードを含まない。書き出しの最新の形式と同じ形（v0.99: 形式 25 の受けた記録の、ダメージを受けた場所 ``active_damage``。場所は場の表の情報）
        "history": [history_record(record) for record in pokemon.history],
        # v0.120: 進化元を重ねずに出し、場ではたねポケモンとしてあつかう進化カードの事実（場の表の情報。書き出しの最新の形式と同じ形。ないときは None）
        "basic_entry": None if pokemon.basic_entry is None else basic_entry_record(state, pokemon.basic_entry),
        # v0.124: ［すごいへんしん］で選んだ変身のもと（場の表の情報。書き出しの最新の形式と同じ形。ないときは None）
        "super_transform": None if pokemon.super_transform is None else super_transform_record(state, pokemon.super_transform),
        "attacks": [
            {"card": _seen_uid(state, option.card, viewer), "card_id": state.cards[option.card].card_id, "attack_index": option.attack_index, "name_ja": attack_of(state, option.key).name_ja,
             **_printed_name(attack_of(state, option.key)), "route": option.route,
             "provider": option.provider, "problem": None if option.problem is None else option.problem[0],
             # v0.120: 必要なエネルギーを満たすポケモン（［にんぎょうつかい］のスリーパー）・許可を与える特殊能力を持つポケモン。どちらも場の表の情報。ないときは書かない（v0.119 までの形）
             **({"payer": option.payer} if option.payer is not None else {}), **({"grantors": list(option.grantors)} if option.grantors else {})}
            for option in available_attacks(state, pokemon)
        ],
        # v0.124: 写した特殊能力の供給元のカード（処理のあいだ固定した姿のカードが見えない場所にもどったときは uid を書かない。``_seen_uid``）
        "powers": [{"card": _seen_uid(state, slot.card, viewer), "card_id": state.cards[slot.card].card_id, "power_index": slot.key.power_index, "name_ja": slot.power.name_ja}
                   for slot in powers_of(state, pokemon)],
    }


def _marker(marker) -> dict[str, Any]:
    """v0.90: マーカー・カウンター 1 つの観測（種類・のせたプレイヤー・のせたワザ・のせた番。色マーカーだけ色）。"""
    view: dict[str, Any] = {"kind": marker.kind, "player": marker.player, "effect": marker.attack, "turn": marker.turn}
    if marker.color is not None:
        view["color"] = marker.color.value
    return view


def _form(state: GameState, pokemon: PokemonInPlay, viewer: int | None = None) -> dict[str, Any]:
    """場のポケモンの今の姿（v0.49。``effects.current_form``）。``kind`` は ``printed``・``transform``・``disguise``（v0.124: ``super_transform``）。

    v0.124: 処理のあいだ固定した姿のカードが、見えない場所（手札・山札など）にもどっていれば、その uid を ``viewer`` に見せない（カードの id・名前・姿の決め方は場の表の情報）。
    ［すごいへんしん］の変身のもとは ``defender`` にポケモンの番号を書く（場の表の情報）。"""
    form = current_form(state, pokemon)
    return {"card": _seen_uid(state, form.card, viewer), "card_id": state.cards[form.card].card_id, "name_ja": state.card_def(form.card).name_ja,
            **_printed_name(state.card_def(form.card)), "kind": form.kind, "defender": form.defender}


def _color(color) -> str | None:
    return None if color is None else color.value


def _visible_to_decider(state: GameState, uid: int, viewer: int, kind: str) -> bool:
    """決定の選べるもののカード ``uid`` が、決めるプレイヤー ``viewer`` に見えるか。"""
    if kind in DECK_REVEALING_KINDS or kind in LOOKED_HAND_KINDS:
        return True  # 効果で山札をさがす・見たカードを並べる・見た相手の手札から選ぶ（選べるものは決めるプレイヤーが見ているカード）
    for owner, p in enumerate(state.players):
        if uid in p.discard:
            return True
        if uid in p.hand:
            return hand_visible_to(state, owner, viewer)
        if uid in p.prizes:
            return uid in state.face_up_prizes  # v0.63: おもてのサイド（ロケット団参上!）は全員に見える
        if uid in p.deck:
            return False
        for pokemon in p.in_play():
            if (uid == pokemon.card or uid == pokemon.disguise or uid in pokemon.evolution_stack or uid in pokemon.energy
                    or any(t.card == uid for t in pokemon.trainers)):
                return True
    if state.stadium is not None and state.stadium.card == uid:
        return True
    for group in state.set_aside:
        if uid in group.cards:
            return viewer in group.visible_to  # v0.63: 一時的に置いておくカードは、見られるプレイヤーにだけ
    used = state.trainer_in_use
    return used is not None and used.card == uid


def _decision(state: GameState, viewer: int | None) -> dict[str, Any] | None:
    d = state.decision
    if d is None:
        return None
    bounds = value_range(d)
    if bounds is not None:
        # v0.129: 値で答える決定（カツラのクイズ その1の身長）。選べるものを並べず、答えられる範囲と単位・伝えた名前（全員に伝えた情報。ログ quiz_name_hint）を全員に見せる。
        # 置いたカード・正解の値は見せない（続きの情報の quiz_card は観測に出さない）
        meaning = OPTION_MEANINGS.get(d.kind)
        if meaning != "value":
            raise ValueError(f"値で答える決定の種類 {d.kind!r} の意味が value ではない（OPTION_MEANINGS）")
        view = {"kind": d.kind, "player": d.player, "min_choices": d.min_choices, "max_choices": d.max_choices, "value_range": {"min": bounds[0], "max": bounds[1]}}
        if d.kind == QUIZ_HEIGHT_ANSWER:
            view["value_range"]["unit"] = "cm"
            view["name"] = d.context_value("name")
        if viewer == d.player:
            view["meaning"] = meaning
        return view
    view: dict[str, Any] = {"kind": d.kind, "player": d.player, "min_choices": d.min_choices, "max_choices": d.max_choices,
                            "option_count": len(d.options)}
    if d.kind == QUIZ_ANSWER:
        view["hint"] = d.context_value("hint")  # v0.63: 伝えたワザの名前（全員に伝えた情報。ログ quiz_hint）
    if viewer != d.player:
        if d.kind in HIDDEN_COUNT_KINDS:
            return {"kind": d.kind, "player": d.player}  # v0.63: 選ぶ数・選べるものの数も見せない
        return view  # 選べるもの（とその中身）は決めるプレイヤーだけに渡す
    meaning = OPTION_MEANINGS.get(d.kind)
    if meaning is None:
        raise ValueError(f"決定の種類 {d.kind!r} の選べるものの意味が決まっていない（OPTION_MEANINGS に加える）")
    options = []
    for value in d.options:
        option: dict[str, Any] = {"value": value}
        if meaning == "card" and _visible_to_decider(state, value, viewer, d.kind):
            option["card_id"] = state.cards[value].card_id
        elif meaning == "color":
            option["color"] = COLORS[value].value
        elif meaning == "name":
            option["name"] = d.context_value("names")[value]  # v0.63: カツラのクイズ その3で答えるカードの名前
        elif meaning == "janken":
            option["hand"] = JANKEN_HANDS[value]  # v0.66: カスミの勝負のじゃんけんの手（rock・scissors・paper）
        elif meaning == "position" and d.kind in PRIZE_POSITION_KINDS:
            prizes = state.players[d.player].prizes
            if 0 <= value < len(prizes) and prizes[value] in state.face_up_prizes:
                option["card_id"] = state.cards[prizes[value]].card_id  # v0.63: おもてのサイド（ロケット団参上!）は位置のカードが見えている
        if d.kind == QUIZ_ATTACK:
            option["attack_name"] = state.card_def(d.context_value("quiz_card")).attacks[value].name_ja  # v0.63: 置いたカードは決めるプレイヤーが見ている
        elif meaning == "peek_target":
            target = d.context_value("targets")[value]
            option["target"] = {"zone": target[0], "owner": target[1], **({} if target[0] == "deck" else {"position": target[2]})}
        if d.kind in (SELECT_ATTACK, SELECT_OPPONENT_ATTACK):
            # v0.49: 相手のワザを選ぶ決定の選べるものが指すワザ（印刷したカードの id・位置・名前。表のカード）
            key = _chosen_attack(state, d, value)
            if key is not None:
                option["attack"] = {"card_id": key[0], "attack_index": key[1], "name_ja": state.definitions[key[0]].attacks[key[1]].name_ja,
                                    **_printed_name(state.definitions[key[0]].attacks[key[1]])}
        options.append(option)
    view["options"] = options
    view["meaning"] = meaning
    return view


def _chosen_attack(state: GameState, d, value: int) -> tuple[str, int] | None:
    """相手のワザを選ぶ決定（ゆびをふる・ドわすれ）の選べるもの ``value`` が指すワザの (カードの id, 位置)（v0.49）。決定の続きの情報の並び（``copy_attacks``・
    ``lock_attacks``）があればその位置、なければ v0.48 までの形（``copy_from`` のカード・ドわすれの相手のいちばん上のカードのワザの位置）。"""
    keys = d.context_value("copy_attacks") or d.context_value("lock_attacks")
    if keys is not None:
        return tuple(keys[value])
    copy_from = d.context_value("copy_from")
    if copy_from is not None:
        return copy_from, value
    target = d.context_value("target")
    found = state.find_pokemon(target) if target is not None else None
    if found is None:
        return None
    return state.cards[found[1].card].card_id, value


def observe(state: GameState, viewer: int | None) -> dict[str, Any]:
    """``viewer``（0・1・``None`` は観戦者）に見える、その時点の盤面（モジュールの説明の範囲）。状態を変えない。"""
    _check_viewer(viewer)
    face_down = state.turn_number == 0  # 対戦準備で出したポケモンは、最初の番の前に表にする（ログ reveal_pokemon）
    players = []
    for owner, p in enumerate(state.players):
        visible_hand = hand_visible_to(state, owner, viewer)
        board_visible = not face_down or viewer == owner
        players.append({
            "player": owner,
            "hand": {
                "count": len(p.hand),
                "cards": [_card(state, uid) for uid in p.hand] if visible_hand else None,
                "revealed_by": [list(source) for source in hand_revealed_by(state, owner)],
            },
            "deck": _deck(state, owner, viewer),
            # v0.63: おもてのサイド（ロケット団参上!。全員に見える）は位置とカードを書く。裏のサイドは枚数だけ（uid も渡さない）
            "prizes": {"count": len(p.prizes),
                       "face_up": [{"position": i, **_card(state, uid)} for i, uid in enumerate(p.prizes) if uid in state.face_up_prizes]},
            # v0.63: 一時的に置いておくカード（手札・山札・ベンチとは別の場所）。枚数・出どころ・もどす番は全員に見え、カードは見られるプレイヤーにだけ
            "set_aside": [{"kind": g.kind, "count": len(g.cards), "cards": [_card(state, uid) for uid in g.cards] if viewer in g.visible_to else None,
                           "user": g.user, "trainer_card": g.trainer_card, "card_id": g.card_id, "return_turn": g.return_turn}
                          for g in state.set_aside if g.owner == owner],
            "discard": [_card(state, uid) for uid in p.discard],
            "active": (_field_pokemon(state, p.active, owner, viewer) if board_visible else {"face_down": True}) if p.active is not None else None,
            "bench": [_field_pokemon(state, b, owner, viewer) if board_visible else {"face_down": True} for b in p.bench],
        })
    used = state.trainer_in_use
    return {
        "viewer": viewer,
        "turn": state.turn_number,
        "current_player": state.current_player,
        "phase": state.phase.value,
        "players": players,
        "trainer_in_use": None if used is None else {"player": used.player, "user": used.using_player, **_card(state, used.card)},
        "trainer_locks": [{"player": lock.player, "source_player": lock.source_player, "effect": lock.effect, "expires_turn": lock.expires_turn,
                           "origin": lock.origin}
                          for lock in state.trainer_locks],
        # v0.56: トレーナーを使ったプレイヤーに与えた期限のある効果（カスミ・キョウ・見えない壁。公開の情報）
        # v0.122: 発生源のカードが見えない場所にもどっていれば、その uid は書かない（``_seen_uid``）
        "trainer_effects": [{"kind": e.kind, "player": e.player, "card": _seen_uid(state, e.source_card, viewer), "card_id": e.card_id, "expires_turn": e.expires_turn,
                             **({} if e.pokemon_id is None else {"pokemon_id": e.pokemon_id})}  # v0.80: 退化スプレーHYPER の禁止
                            for e in state.trainer_effects],
        # v0.57: 場に出ているスタジアム（両方の場の境界線上。公開の情報）と、この番にスタジアムの効果を使ったプレイヤー
        "stadium": None if state.stadium is None else {"owner": state.stadium.owner, "placed_turn": state.stadium.placed_turn,
                                                       **_card(state, state.stadium.card)},
        "stadium_uses_this_turn": [list(use) for use in state.stadium_uses_this_turn],
        # v0.88: 特殊能力で色を変える効果（［せんすい］・［エナジーコンバーター］。公開の情報。書き出しの形式 23 と同じ項目）
        "color_effects": [{"kind": e.kind, "player": e.player, "source": e.source, "card": _seen_uid(state, e.source_card, viewer),
                           "card_id": state.cards[e.source_card].card_id, "power_index": e.power_index,
                           "target": e.target, "color": e.color.value, "turn": e.turn, "left_play": e.left_play}
                          for e in state.color_effects],
        # v0.100（docs/sketch-perish-song-history-v0.100.md 7 章）: プレイヤーの番ごとの記録（使ったワザ・番でないプレイヤーの場にいたカード）。どちらも両方のプレイヤーが見た
        # 表の情報（うらのカードは数だけで、uid を書かない）。書き出しの形式 26 と同じ形
        "turn_history": [turn_record(record) for record in state.turn_history],
        # v0.119（docs/damage-reactions-poison-sleep-v0.119.md 5 章・6 章）: ［ポイズンミスト］の効果と、「ガスばくはつ」のかわりに出てくる対戦ポケモンへのまだ与えていないどく（どちらも場・
        # コインの表の情報。書き出しの形式 27 と同じ形）
        "poison_mists": [poison_mist_record(state, record) for record in state.poison_mists],
        "replacement_poisons": [replacement_poison_record(record) for record in state.replacement_poisons],
        "decision": _decision(state, viewer),
        "result": None if state.result is None else {"outcome": state.result.outcome, "winner": state.result.winner},
        # v0.127（docs/deferred-shortage-user-promos-v0.127.md 8 章）: 途中停止の状態だけ、その記録（全員に見える項目。ワザ・トレーナーを使い終えた盤面ではないことを示す）を加える
        **({"interruption": public_record(state.halt.interruption)} if state.halt is not None and state.halt.interruption is not None else {}),
    }


# ---------------------------------------------------------------- ログ


def _only_player(event, viewer) -> bool:
    return viewer is not None and viewer == event.get("player")


def _nobody(event, viewer) -> bool:
    return False


def _looked_card(event, viewer) -> bool:
    """見たプレイヤーと、手札のカードならその持ち主（自分の手札のどの位置のカードかを知っている）。"""
    return viewer is not None and (viewer == event.get("player") or (event.get("zone") == "hand" and viewer == event.get("owner")))


def _hand_looker_or_owner(event, viewer) -> bool:
    """v0.54: スパイ作戦で見た手札は、見たプレイヤーと手札の持ち主（自分の手札を知っている）に見える。"""
    return viewer is not None and viewer in (event.get("player"), event.get("owner"))


def _hand_owner_or_looker(event, viewer) -> bool:
    """v0.55: ロケット団のおねーさんで相手の山札にもどさせたカードは、手札の持ち主（``player``）と、手札を見て選んだプレイヤー（``looker``）に見える。"""
    return viewer is not None and viewer in (event.get("player"), event.get("looker"))


def _looker_only(event, viewer) -> bool:
    """v0.80: にせオーキドの発明で相手の山札にもどしたサイドは、サイドを見たプレイヤー（``looker``）だけに見える（サイドの持ち主は見ていない）。"""
    return viewer is not None and viewer == event.get("looker")


def _exchange_parties(event, viewer) -> bool:
    """v0.130: とりかえっこプリーズで選んだカード・交換したカードと所有者の変更は、交換にかかわる 2 人（使ったプレイヤー ``player`` と相手 ``opponent``・手札の持ち主 ``owner``）だけに
    見える（観戦者には見せない。2 人とも相手の手札を見て、選んだカードを知っている）。"""
    return viewer is not None and viewer in (event.get("player"), event.get("opponent"), event.get("owner"))


def _amount_unless_private(event, viewer) -> bool:
    """v0.95: 受けなかったダメージの量（``amount``）は、印 ``amount_private``（基本となるダメージが見た手札の中身で決まるワザ。``kernel._amount_privacy``）があれば対戦する
    プレイヤーだけに見える（観戦者には見せない）。印がなければ全員（v0.94 までと同じ）。"""
    return not event.get("amount_private") or viewer is not None


def _taken_deck_top(event, viewer) -> bool:
    """てつだうふり（v0.45）: トラッシュに置いたら公開。手札に加えたら、見たプレイヤーと持ち主。"""
    return event.get("destination") == "discard" or (viewer is not None and viewer in (event.get("looker"), event.get("player")))


# 見えない項目のあるイベント: 種類 → (見えない項目, その項目が見える人か)
PRIVATE_FIELDS: dict[str, tuple[tuple[str, ...], Callable[[Any, int | None], bool]]] = {
    "game_created": (("seed",), _nobody),  # seed から山札の並び・コインがわかる
    "draw": (("cards",), _only_player),
    "place_starting_pokemon": (("active", "bench"), _only_player),  # 表にする（reveal_pokemon）までは裏
    "take_prize": (("card",), _only_player),
    "search_deck": (("card",), _only_player),  # 見せる指示がない（v0.22 の CS14）
    "hand_to_deck": (("cards",), _only_player),  # 見せずに山札にもどす（v0.44・v0.46・v0.47）
    "hand_to_deck_top": (("card",), _only_player),  # v0.118: ［トランスポート］で見せずに山札の上に置く手札のカード
    "look_at_card": (("card",), _looked_card),  # v0.47 の［スパイ］・おどろかす
    "look_at_deck_top": (("cards",), _only_player),  # v0.47 のみらいよち（見る）
    "arrange_deck_top": (("cards",), _only_player),  # v0.47 のみらいよち（もどす並び）
    "take_deck_top": (("card",), _taken_deck_top),
    "trainer_take_none": (("reason",), _only_player),
    "gift_take_none": (("reason",), _only_player),  # v0.84: ［おくりもの］で山札を見て選ばなかった理由（山札にどうぐがなかったか）は、山札の中身の情報  # v0.53: 山札をさがして選べるカードがなかったか・選ばなかったかは、山札の中身の情報
    "look_at_hand": (("cards",), _hand_looker_or_owner),  # v0.54: スパイ作戦（見たプレイヤーと持ち主だけ。観戦者には見せない）
    "looked_to_hand": (("cards",), _only_player),  # v0.55: カスミのいかり（見た山札の上のカードから手札に加えたカード）
    "opponent_hand_to_deck": (("card",), _hand_owner_or_looker),  # v0.55: ロケット団のおねーさん（持ち主と、見て選んだプレイヤーだけ）
    # v0.56: ロケット団のワナ（おもてを見ないで選んだ位置は公開、もどしたカードは持ち主だけ）・マチスの交渉で取ったサイド（取ったプレイヤーだけ。きぜつで取るサイドと同じ）・
    # カスミのわがままで入れかえたカード（持ち主だけ。位置は公開）
    "hand_positions_to_deck": (("cards",), _only_player),
    "trainer_take_prize": (("card",), _only_player),
    "swap_prize_with_hand": (("to_prize", "to_hand"), _only_player),
    # v0.63: くすぐりマシーンで置いたカード（だれも見ない）・もどしたカード（持ち主だけ。クイズで表にしたカードは face_up で全員）・挑戦状でうらにして出したカード（持ち主だけ）・
    # 選ばなかった理由（山札の中身なので選ぶプレイヤーだけ）・クイズで置いたカード（置いたプレイヤーだけ）
    "set_aside_hand": (("cards",), _nobody),
    "set_aside_returned": (("cards",), _only_player),
    "face_down_bench": (("cards",), _only_player),
    "challenge_bench_skipped": (("reason",), _only_player),
    "quiz_card_set": (("card",), _only_player),
    # v0.67: マチスの秘策でうらにしてベンチに出したカード（持ち主だけ。おもてにしたら ``secret_plan_revealed`` で全員）
    "secret_plan_placed": (("card",), _only_player),
    # v0.80: にせオーキドの発明で見た相手のサイド（見たプレイヤーだけ）・山札にもどしたサイド（見たプレイヤーだけ。枚数は公開）・ポケモンマーチで出さなかった理由（山札の中身の情報）
    "look_at_prizes": (("cards",), _only_player),
    "prizes_to_deck": (("cards",), _looker_only),
    "trainer_bench_from_deck_declined": (("reason",), _only_player),
    # v0.83: やさしいゴルダックの「みずかき」で、見た山札の上から選ばなかった理由（選べるカードがなかった・選ばなかった。山札の上の中身の情報なので、見たプレイヤーだけ）
    "deck_top_take_declined": (("reason",), _only_player),
    # v0.95: 受けなかったダメージの量（「とうめい」・「かげぶんしん」・「リフレクトシールド」）。ゴーストの「ポルターガイスト」のように基本となるダメージが見た手札の中身で
    # 決まるワザなら、観戦者には量を見せない（のせたダメージはワザの結果で公開）。ほかのワザのログは全員に見える（v0.94 までは見えない項目のないイベント）
    "attack_evaded": (("amount",), _amount_unless_private),
    "damage_guard_check": (("amount",), _amount_unless_private),
    "reflect_shield_check": (("amount",), _amount_unless_private),
    "timed_damage_guard_check": (("amount",), _amount_unless_private),  # v0.109: ぬるぬる・かわす・ブリンク（同じ扱い）
    # v0.130（docs/trade-please-ownership-v0.130.md 8 章）: とりかえっこプリーズで選んだカード（選んだプレイヤーと手札の持ち主）・交換したカードと所有者の変更（交換した 2 人。観戦者には
    # 交換が成立したこと・番号・枚数だけ。uid・カードの id・出所を見せない）
    "exchange_selected": (("card", "card_id"), _exchange_parties),
    "cards_exchanged": (("given_card", "taken_card", "card_ids", "ownership"), _exchange_parties),
}
# 見えない項目のないイベント（どの項目も全員に見える。公開のゾーン・場・コイン・決まった結果）
PUBLIC_EVENTS = frozenset({
    # v0.126: フラッシュでおもてにした山札（並べたプレイヤー・枚数・いちばん上のカードの id。uid は書かない）・いちばん上のおもてのカードが変わった（カードの id・おもての枚数）
    "flash_face_up", "face_up_deck_top",
    # v0.124: ［すごいへんしん］で選んだ変身のもと・もどった理由、［わるいはどう］のコインの結果と追加（どれも場・コインの公開の情報）
    "super_transform", "super_transform_reverted", "dark_pulse",
    # v0.120: 進化元を重ねずにベンチに出したたねポケモンとしてあつかう進化カード（場に出たカード・出した場所・効果）・復活で出すカードがなかった（山札が 0 枚・選べるカードがなかった）・
    # しんかのほうしで選んだポケモン・たまごの化石で山札を見たこと（見たカードは書かない。どれも場・公開の情報）
    "bench_as_basic", "revive_none", "evolve_targets", "look_at_deck",
    # v0.88: 色を変える効果の追加・消去（［せんすい］・［エナジーコンバーター］）・ワザといっしょに使った特殊能力（［すいりょくはつでん］）・ワザで選んだ色・色を選べなかった・
    # テクスチャーで色を変えなかった（どれも場・公開の選択）
    "color_effect_added", "color_effect_removed", "attack_power", "attack_color_chosen", "attack_color_none", "color_change_declined",
    # v0.100: 「スケッチ」で前の相手の番にワザが使われていなかった・「ほろびのうた」の条件の確かめ・ワザの効果による「きぜつ」（どれも場の表の情報と使ったワザ）
    "sketch_none", "knock_out_condition", "effect_knock_out",
    # v0.101: ［KEEP］でエネルギーカードをトラッシュする効果がなくなった（場のカードなので公開）
    "energy_discard_voided",
    # v0.86: ［かんでん］のダメージ・［いなびかり］がはたらかなかった（相手の控えなし）・反応の特殊能力を使わなかった・［はしりさる］のコインの結果とはたらかなかった・
    # ダークドレインのポケモンごとのコインの結果・［おたけび］の番の終わり（どれも場・コイン・公開の結果）
    "conductivity", "lightning_burst_skipped", "reaction_power_declined", "bolt_check", "bolt_skipped", "pokemon_coin_results", "power_turn_end",
    # v0.115: びっくりサンダーの続けて投げたコインの面の並びと控えへの量・ダメージの配分（どれもコイン・場の公開の情報）
    "chained_coin_results", "damage_allocated",
    # v0.116: ついた時に発動するワザの持続効果がはたらいた（つけたカード・特殊状態）・ツイスターで手札にもどした、ついていたカード（どれも場の公開の情報）
    "attach_status_triggered", "attached_cards_to_hand",
    # v0.117: ［CHASE］のコインの結果・のせたダメージカウンター・のせなかった、おいうちのダメージ・与えなかった・無効にした、［ときわたり］のコインの結果、［でんせつのからだ］でトラッシュした
    # ついているトレーナーカード・トレーナーの効果を受けなかったポケモン（どれも場・コイン・公開の情報）
    "chase_check", "chase_counters", "chase_skipped", "pursuit_damage", "pursuit_skipped", "pursuit_prevented", "time_travel", "legend_body_discard",
    "trainer_effect_blocked",
    # v0.118: ワザといっしょに使った［XXXXX］の宣言・コインの結果と追加、エアロウイングで投げる・投げないの答え（どれも場・コインの公開の情報）
    "group_attack_power", "group_attack_power_coins", "optional_coin_chosen", "optional_coin_declined",
    # v0.122: ［ANGER］で数えた力を持つ個体のダメージカウンター、［WANT］・［かせきのみちびき］でトラッシュから手札に加えたカード（トラッシュは公開）、［かせきか］で選んだポケモン、
    # 相手に控えがいなくてはたらかなかった［つるでひっぱる］（どれも場・トラッシュの公開の情報）
    "group_attack_power_counters", "power_recover_from_discard", "fossilize_target", "vine_pull_skipped",
    # v0.87: 場の移動・ダメージへの反応（どれも場・コインの公開の情報）
    "spikes_damage", "hot_plate_damage", "movement_damage_skipped", "magma_pool", "magma_pool_none", "shock_blast_check", "shock_blast_damage",
    "shock_blast_skipped", "poison_fluid", "poison_fluid_skipped", "split_skipped", "split_declined",
    # v0.85: ［あばれんぼう］で山札の上からトラッシュしたカード（トラッシュは公開）・［ファイヤーブースト］で山札からつけた・［ファイヤーリチャージ］でトラッシュからつけた
    # カード（場は公開）・ミラクルエネルギーのトラッシュ・ぎゃくりゅうでトラッシュから山札にもどしたカード（トラッシュは公開）
    "power_discard_deck", "power_attach_from_deck", "power_attach_from_discard", "miracle_energy_discarded", "attack_discard_to_deck",
    # v0.82: 場からトラッシュに置かれて手札にもどしたエネルギーカード（場・トラッシュのカードは公開の情報）・のぞむならトラッシュしなかったこと
    "energy_returned_to_hand", "discard_energy_declined",
    # v0.83: おたがいのプレイヤーが選ぶワザ（引かなかった（山札の枚数は公開）・トラッシュから見せて手札に加えた・山札にもどした・選ばなかった（トラッシュは公開））と、
    # 「リフレクトシールド」（コイン・相手に与えたダメージ・与えなかった）
    "attack_draw_declined", "each_player_recover", "each_player_discard_to_deck", "each_player_declined",
    # v0.84: ［ふかふかなからだ］（コインの結果）・［たすけだす］のとりのぞき・［おくりもの］で山札を見なかった・ポケモン育て屋夫婦のポケモンごとのコイン・つきくずすで
    # トラッシュしなかった・バブルジャンプのつけ替え（場のカードの公開の情報）
    "power_sleep", "power_sleep_skipped", "tag_team_heal", "gift_declined", "breeder_couple_coins", "stadium_discard_declined",
    "reflect_shield_damage", "reflect_shield_skipped",
    # v0.81: ポケモンのどうぐ（きのみのとりのぞき・きあいのハチマキ・はんげきのツメ・学習装置。どれも場のカード・コインの結果で公開）
    "tool_heal", "focus_band", "counter_claw", "tool_damage_counters", "exp_all_declined", "tool_move_energy",
    "darkness_energy_damage", "darkness_energy_counters",  # v0.78: ポケモンチェックの悪エネルギー（場のカードの公開の情報）
    # v0.67: マチスの秘策（出さなかった・出せなかった理由・おもてにした本当のカード・トラッシュしたカード・指定した対象がいなくなった。どれも表の情報）
    "secret_plan_none", "secret_plan_declined", "secret_plan_revealed", "secret_plan_discarded", "secret_plan_target_lost",
    # v0.66: ナツメのESPのやり直し（投げたコインは表の情報）・カスミの勝負のじゃんけん（両方の手を決めたあとに見せる）・お上品攻撃の手札にもどす期限
    "esp_redo", "esp_redo_declined", "duel_janken", "return_attached_trainer",
    # v0.68: ［だつりょくえき］（コインの結果・場のエネルギーカードは表の情報）
    "energy_drain_check", "energy_drain_discard",
    # v0.61: ［ファイナルビーム］・［ずらかる］・［おとしあな］・バトル場は穴だらけ!（どれも表の情報）
    "knock_out_power_declined", "knock_out_power_declared", "knock_out_power_failed", "knock_out_power_damage", "scram", "sinkhole_check", "sinkhole_damage",
    "digger_result", "trainer_damage", "trainer_damage_prevented",
    # v0.62: オウムがえし（受けた記録は表の情報）
    "mirror_move_none", "reflect_received",
    "attach_energy", "energy_conversion", "bench_coin_results", "rebellion_check", "attach_energy_from_deck", "attach_energy_from_deck_none", "attach_energy_from_discard",
    "attach_energy_from_hand", "attach_trainer", "attack", "attack_attach_energy", "attack_check", "attack_failed", "attack_heal",
    "bench_from_deck", "bench_from_deck_declined", "bench_from_deck_none",
    "bench_from_discard", "bench_from_discard_declined", "bench_from_discard_none",  # v0.51: トラッシュと場は公開の情報
    "coin_flip", "confusion_check", "confusion_damage", "copy_attack",
    "counterattack", "counterattack_skipped", "damage", "damage_prevented", "deck_out", "destiny_bond", "devolve", "devolve_declined", "devolve_none",
    "discard_attached_cards",
    "discard_attached_energy", "discard_attached_trainer", "discard_energy", "discard_energy_failed", "discard_from_deck", "discard_from_hand",
    "bench_guard", "flee", "flee_declined", "flee_effect_skipped", "ninja_trick", "ninja_trick_declined", "discard_from_play", "discard_hand", "discard_trainer", "disguise", "disguise_removed", "drain_heal", "drain_heal_skipped", "drain_heal_declined", "attack_heal_declined", "effect_prevented", "effect_skipped",
    "end_turn_without_attack", "energy_burn", "entry_power_declined", "evade_check", "evolution_permission", "evolve", "evolve_from_deck_declined",
    "evolve_from_deck_none", "forced_switch", "forced_switch_skipped", "game_end", "halted", "janken", "knock_out", "ko_prevented",
    "ko_prevention_declared", "ko_prevention_declined", "ko_prevention_failed", "look_at_deck_top_none", "move_damage_counter", "move_energy",
    "move_opponent_energy", "mulligan", "mulligan_draw", "once_attack_recorded", "persistent_effect_added", "persistent_effect_removed",
    "persistent_effect_skipped", "place_damage_counters", "play_to_bench", "play_trainer", "play_trainer_as_pokemon", "poison_damage",
    "pokemon_check", "pokemon_power", "post_knockout_power_declared", "post_knockout_power_declined", "power_attach_energy", "power_confusion",
    "power_confusion_skipped", "power_damage", "power_heal", "promote_active", "put_discard_on_deck_top", "recover_energy", "recover_pokemon",
    "recall", "recover_pokemon_none", "recover_trainer", "remove_all_damage_counters", "remove_damage_counters", "retaliation", "retaliation_skipped",
    "retreat", "retreat_failed", "retreat_failure_cleared", "retrieve_energy", "return_energy_to_hand", "return_in_play_to_deck",
    "return_in_play_to_hand",
    "return_basic_to_hand",  # v0.52: ポケモン回収（場のカード → 手札・トラッシュ。手札にもどしたカードは場にあったので公開）
    "trainer_place_damage_counters",  # v0.71: ポケモンジム第1弾の元気のかけら（出したポケモンにのせたダメージカウンター）
    "reveal_hand", "revealed_hand_to_deck",  # v0.54: ミニスカート（見せ合った手札・見せた手札から山札にもどしたトレーナーカード）
    "trainer_draw_declined", "trainer_discard_declined", "look_at_deck_top_declined",  # v0.54: 引かない・トラッシュしない・見ない（山札・手札の枚数は公開）
    "discard_to_deck", "retrieve_trainer",  # v0.53: 夜の廃品回収（見せて山札にもどす）・ダウジングマシーン（トラッシュ → 手札）。トラッシュは公開の情報
    "milled_to_hand",  # v0.73: 熱血!（山札の上からトラッシュしたカードのうち手札に加えたもの。トラッシュから動いたので公開）
    # v0.95: とりさるで相手の山札にもどした、ついているトレーナーカード（場の公開のカード）・もやすで見たカードがトレーナーカードでなく、もとの山札の上にもどした（カードは書かない）・
    # ［わるぢえ］で見た山札を切らなかった（山札の並びは変わらない）
    "attached_trainer_to_deck", "deck_top_returned", "shuffle_declined",
    "hand_return_declined",  # v0.96: ［ENGAGE］で手札を山札にもどさなかった（手札・山札の枚数は公開）
    "return_to_deck", "return_to_hand", "reveal_from_deck", "reveal_from_deck_declined", "reveal_from_deck_none",
    "reveal_pokemon", "set_prizes", "shuffle", "sleep_check", "special_condition", "special_condition_prevented", "special_conditions_removed",
    "swap_damage_counters", "swap_prize_with_deck_top", "switch", "switch_declined", "trainer_lock_added", "trainer_lock_removed", "turn_end",
    "turn_start", "type_shift",
    # v0.55: 場のエネルギーカードをはがす（トラッシュ・手札・つけなおし）・入れ替えない・トラッシュと山札を入れ替える・見た山札の残りをトラッシュ（場・トラッシュは公開の情報）
    "trainer_discard_energy", "trainer_return_energy", "trainer_move_energy", "trainer_switch_skipped", "discard_pile_to_deck", "deck_top_to_discard",
    "looked_to_discard",
    # v0.56: 相手の手札からベンチに出させた・手札から直接バトル場に出した（場は公開）・相手の答え・期限のある効果・トレーナーの効果で番が終わった
    "trainer_bench_from_hand", "trainer_hand_to_active", "request_answered", "trainer_effect_added", "trainer_effect_removed", "trainer_turn_end",
    # v0.121: ワザで相手の手札からベンチに出した・出さなかった・出せるカードがなかった（場・選ばなかったことは公開）・ロックオンで「うら」でも失敗しなかった（コインは公開）
    "attack_bench_from_hand", "attack_bench_from_hand_declined", "attack_bench_from_hand_none", "attack_failure_waived",
    # v0.57: スタジアム（場に出す・トラッシュ・効果を使う・場のカードを動かす・ダメージ・コイン・錯乱ジムのコインと答え。場・トラッシュ・コインは公開の情報）
    "stadium_placed", "stadium_discarded", "stadium_discard_energy", "stadium_return_energy", "stadium_used", "stadium_damage", "evolution_heal",
    "evolution_heal_declined", "stadium_attack_coin", "chaos_check", "chaos_answered", "chaos_not_borrowable",
    # v0.132: 相手の［ちえくらべ］を使うかの答え・コインの判定・使えなかったトレーナーカードを山札の上に置いた（見せたカード・コイン・答えは公開の情報）
    "trainer_reaction_answered", "trainer_reaction_check", "trainer_blocked",
    # v0.133: 利用者の指定で、説明の数に足りないときにあるだけ処理した記録（必要な数・処理できる数・処理した数。山札の枚数・場のエネルギーカードは公開の情報）
    "user_rule_count_short",
    # v0.58: 特殊エネルギーをつけたときの効果（回復・ダメージ）・ばくれつのスタジアムがない場面・サイキックコントロールで使えるカードがない・使わなかった
    # （場・トラッシュは公開の情報）
    "energy_heal", "energy_damage", "stadium_discard_none", "discard_trainer_use_none", "discard_trainer_use_declined",
    # v0.63: おもてにしたサイド（全員に見えるようにした）・うらにして出したカードを表にした・クイズの伝えたワザ・答え・表にしたカード
    "prizes_revealed", "face_down_revealed", "quiz_hint", "quiz_answer", "quiz_reveal",
    # v0.129: カツラのクイズ その1の伝えた名前・答えた身長（整数 cm）・表にしたカード（正解か・図鑑番号・身長の参照値。表にしたあとの公開の情報）
    "quiz_name_hint", "quiz_height_answer", "quiz_height_reveal",
    # v0.74: ポケモンタワーで消えた効果・エネルギースタジアムで手札に加えた（見せた）カード・キョウの忍者ジムでベンチに出したカード（トラッシュ・場は公開の情報）
    "discard_to_hand_suppressed", "stadium_retrieve_energy", "stadium_bench_from_deck",
    # v0.75: エナジーサポートで、つける控えが「とうめい」で受けなかったので持ち主のトラッシュに置いたカード（トラッシュは公開の情報）
    "deck_energy_evaded",
    # v0.80: カードめくりゲーム（おもてにしたサイド・答え）・山札の上から置いたサイド（枚数だけ）・スロットゲーム（見せた 3 枚）・クイズの種類の答えと表にしたカード・ポケモンマーチで
    # ベンチに出したカード・いやしの野原（場は公開の情報）
    "prize_revealed", "prize_guess", "deck_top_to_prizes", "reveal_deck_top", "quiz_kind_answer", "quiz_kind_reveal", "trainer_bench_from_deck", "stadium_heal",
    # v0.90: マーカー・カウンターをのせた・取りのぞいた（場の表の情報）
    "marker_added", "marker_removed", "marker_removal_declined",
    # v0.91（docs/marker-check-field-reset-v0.91.md 4 章）: ポケモンチェックのくろこげマーカーのコインとダメージ
    "char_check", "char_damage",
    # v0.93（docs/active-leave-locks-v0.93.md 11 章）: 「バトル場をはなれられない」効果で起こらなかった部分・くいつくの発生源がはなれた印（場の表の情報）
    "leave_prevented", "persistent_effect_source_left",
    # v0.94（docs/switch-return-attacks-v0.94.md 9 章）: 任意の入れ替え（きつねび）で入れ替えなかった（場の表の情報。ワザを使ったプレイヤーの答え）
    "forced_switch_declined",
    # v0.110（docs/endure-armor-up-v0.110.md 8 章）: こらえる・こうてつかで「きぜつ」しなかった（のっているダメージ・残りHP・効果を与えた番は場の表の情報）
    "knockout_survived",
    # v0.114（docs/baby-rules-evolution-v0.114.md）: ベイビィポケモンのルールのコインの結果（コインは表の情報）・サイコキッスで相手の山札にもどした、ついている特殊エネルギーカード
    # （場の公開のカード）
    "baby_rule_coin", "attached_energy_to_deck",
    # v0.119（docs/damage-reactions-poison-sleep-v0.119.md）: ［ポイズンミスト］の効果の始まり・中断・終わり、「どくをだす」の効果がはたらいた・はたらかなかった、「ガスばくはつ」のかわりに
    # 出てくる対戦ポケモンへのどくの予定・きぜつ・どく・取りのぞき、［アレルギーほうし］で起こらなかったトラッシュのカードへの効果（どれも場・トラッシュ・コインの公開の情報）
    "poison_mist_added", "poison_mist_interrupted", "poison_mist_removed", "secrete_poison", "secrete_poison_skipped", "replacement_poison_pending",
    "replacement_poison_knocked", "replacement_poison", "replacement_poison_removed", "discard_protected",
})


def visible_event(event, viewer: int | None) -> dict[str, Any]:
    """ログのイベント 1 つを、``viewer`` に見える項目だけにした写し。"""
    kind = event["kind"]
    if kind in PRIVATE_FIELDS:
        fields, sees = PRIVATE_FIELDS[kind]
        if sees(event, viewer):
            return dict(event)
        # v0.63: おもてだった（全員に見えていた）カードの項目（``face_up``。おもてのサイドを取った・クイズで表にしたカードを手札にもどした）は全員に見せる
        fields = tuple(name for name in fields if name not in event.get("face_up", ()))
        if not fields:
            return dict(event)
        copy = {name: value for name, value in event.items() if name not in fields}
        copy["hidden"] = {name: (len(event[name]) if isinstance(event[name], (tuple, list)) else None) for name in fields if name in event}
        return copy
    if kind in PUBLIC_EVENTS:
        return dict(event)
    raise ValueError(f"ログのイベント {kind!r} の見える範囲が決まっていない（observation.PRIVATE_FIELDS・PUBLIC_EVENTS に加える）")


def _uid_field(name: str) -> bool:
    """v0.67: カードの uid を書く項目の名前か（``UID_FIELDS``・``…_card``・``…_cards``）。"""
    return name in UID_FIELDS or name.endswith(("_card", "_cards"))


# v0.67: カードの uid を書くログの項目（``_card``・``_cards`` で終わる名前のほか）。場のポケモンの番号は ``pokemon_id``・``…_pokemon_id`` に書く
UID_FIELDS = frozenset({"pokemon", "card", "cards", "old_active", "new_active", "target", "active", "bench", "energy", "discarded", "discarded_energy"})


def _mask_face_down(event: dict[str, Any], hidden: frozenset[int]) -> dict[str, Any]:
    """v0.67: 見る人の相手のうらのカード（``hidden``。今うらのもの）の uid を、カードの uid を書く項目から除いた写し（uid はデッキの並びからカードがわかる。おもてにしたら
    前のイベントの項目も見える）。"""
    masked = dict(event)
    for name, value in event.items():
        if not _uid_field(name):
            continue
        if type(value) is int and value in hidden:
            masked[name] = None
        elif isinstance(value, (tuple, list)) and any(type(v) is int and v in hidden for v in value):
            masked[name] = type(value)(None if type(v) is int and v in hidden else v for v in value)
    return masked


def visible_log(state: GameState, viewer: int | None) -> list[dict[str, Any]]:
    """ログを、``viewer``（0・1・``None`` は観戦者）に見える項目だけにした写しの並び。状態を変えない。v0.67: ``viewer`` の相手のうらのカード（マチスの秘策）の uid は
    見せない（``_mask_face_down``）。"""
    _check_viewer(viewer)
    hidden = frozenset(uid for uid in state.face_down_cards if state.cards[uid].owner != viewer)
    if not hidden:
        return [visible_event(event, viewer) for event in state.log]
    return [_mask_face_down(visible_event(event, viewer), hidden) for event in state.log]

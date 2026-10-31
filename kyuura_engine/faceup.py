"""表向きの山札（v0.126。docs/flash-faceup-deck-v0.126.md 4 章・6 章）。

フラッシュ（ES2-035）は、それぞれのプレイヤーが自分の山札の上から 5 枚を見て並べ替え、おもてを上にして山札の上にもどす。この部品は、その結果を 3 つに分けて持つ。

- **向き**（物理的な状態）: ``GameState.face_up_deck``。おもてを上にして置かれた、具体的なカードの uid の並び（置いた順）。番・プレイヤーへの持続効果ではない。カードが山札を
  はなれたら印を消す（``drop_left_marks``）。山札を切るときは、切る前に印をすべて消す（``clear_marks``。印刷・最新の説明の「おもてを下にもどしてから切る」）。
- **知っている情報**（観測で求める）: 並べ替えた本人は、自分の山札のおもてのカードの並びを知っている（自分で並べた。``known_face_up``）。いままでに公開されたカードの記憶は
  公開のログ（``flash_face_up``・``face_up_deck_top``）にある。
- **いま公開されている範囲**: いちばん上がおもてなら、そのカードは双方・観戦者に見える（CR-FLASH-TOP-CARD-SEEN）。2 枚目より下のおもてのカードは自動では見せない。新しく
  確かめる要求は ``CheckFaceUpDeckCard`` で識別し、FU2 で止める（下を見てはいけないと裁定したのではない。UQ-FLASH-FACE-UP-DECK）。

おもてのカードはいつも山札の上から続く並び（いちばん上から何枚か）になる（置くのはフラッシュだけで、上から引く・取りのぞく、下に置く操作は並びを保つ。上に置く・
並べ替える操作は止める）。``check_invariants`` が確かめる。

山札にかかわる処理が、おもてのカードの向き・見える範囲で結果や要る情報を変えるかを、コマンドの終わりに前後の状態とそのコマンドのログで確かめる（``command_problem``）。
読み方で分かれる操作は、研究の論点（UQ-FLASH-FACE-UP-DECK）の停止コードで止める。分類していない経路で印のある山札が変わったら、エンジンの未対応
（``UNSUPPORTED_FACE_UP_DECK_PATH``）で止める（資料の未解決と区別する）。コマンドはどれも状態の複製の上で処理するので、止めたら状態・乱数・ログは変わらない。
"""

from __future__ import annotations

from collections.abc import Iterable

from .errors import UnsupportedError
from .state import GameState

# FU1: フラッシュを使うとき、片方でも山札が 5 枚より少ない（0 枚をふくむ）。見られるだけ見て並べ替えるのか、その分を処理しないのか、使えないのか（UQ-STATED-COUNT-SHORT）
FLASH_DECK_SHORT_CODE = "UNRESOLVED_FLASH_DECK_SHORT"
FLASH_DECK_SHORT_REASON = (
    "お互いの山札の上から 5 枚を見て並べ替えるフラッシュを、山札が 5 枚より少ないプレイヤーがいるとき（片方だけ・両方・0 枚）に、見られるだけ見て並べ替えるのか、そのプレイヤーの分を"
    "処理しないのか、使えないのかは、最新の説明・kyuura の記録から決められないので扱わない（FU1。kyuura の UQ-STATED-COUNT-SHORT。見られるだけに丸めず、片方だけを処理しない）"
)
# FU2: おもてを上にした山札の、いちばん上より下のおもてのカードを新しく確かめる（UQ-FLASH-FACE-UP-DECK (a)）
FACE_UP_DECK_CHECK_CODE = "UNRESOLVED_FACE_UP_DECK_CHECK"
FACE_UP_DECK_CHECK_REASON = (
    "おもてを上にした山札の、いちばん上より下のおもてのカードを、ほかのプレイヤーが確かめてよいか（重なって見えないカードを確かめてよいか）は、最新の説明・kyuura の記録から"
    "決められないので扱わない（FU2。kyuura の UQ-FLASH-FACE-UP-DECK。確かめてはいけないと決めたのでもない）"
)
# FU3: いちばん上として見えないまま、おもてのカードを手札など見えない場所へ移す（上から 2 枚以上をまとめて引く・山札の途中から取る。UQ-FLASH-FACE-UP-DECK (a)・(d)）
FACE_UP_DECK_HIDDEN_TAKE_CODE = "UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE"
FACE_UP_DECK_HIDDEN_TAKE_REASON = (
    "いちばん上より下のおもてのカードを、いちばん上として見えないまま手札など見えない場所へ移す処理（上から 2 枚以上をまとめて引く・取る、山札の途中から取る）で、移す途中のおもての"
    "カードを相手が見られるかは、最新の説明・kyuura の記録から決められないので扱わない（FU3。kyuura の UQ-FLASH-FACE-UP-DECK。1 枚ずつ引いてすべて公開する読み方に決めない）"
)
# FU4: おもてのカードがある山札の上に、別のカードを置く（置いたカードの向き。UQ-FLASH-FACE-UP-DECK (c)）
FACE_UP_DECK_PLACE_TOP_CODE = "UNRESOLVED_FACE_UP_DECK_PLACE_TOP"
FACE_UP_DECK_PLACE_TOP_REASON = (
    "おもてのカードがある山札の上に別のカードを置く処理で、置いたカードの向き（おもてのカードが見えなくなるか）は、最新の説明・kyuura の記録から決められないので扱わない"
    "（FU4。kyuura の UQ-FLASH-FACE-UP-DECK。置いたカードをうらと決めない）"
)
# FU5: おもてのカードをふくむ山札の上を見て、もどす・並べ替える（もどす向き。UQ-FLASH-FACE-UP-DECK (e)・(f)）
FACE_UP_DECK_LOOK_RETURN_CODE = "UNRESOLVED_FACE_UP_DECK_LOOK_RETURN"
FACE_UP_DECK_LOOK_RETURN_REASON = (
    "おもてのカードをふくむ山札の上のカードを見て、山札にもどす・並べ替える処理（順番を変えずにもどす・並べ替える・もう一度フラッシュを使うときの 5 枚より下のおもてのカード）で、"
    "もどすカードの向きは、最新の説明・kyuura の記録から決められないので扱わない（FU5。kyuura の UQ-FLASH-FACE-UP-DECK）"
)
# FU6: おもてのカードを、向きのある見えない場所（サイド・山札の別の位置・置いておく場所）へ移す（移したあとの向き。UQ-FLASH-FACE-UP-DECK）
FACE_UP_DECK_MOVE_CODE = "UNRESOLVED_FACE_UP_DECK_MOVE"
FACE_UP_DECK_MOVE_REASON = (
    "山札のおもてのカードを、サイド・山札の別の位置・一時的に置いておく場所へ移す処理で、移したあとのカードの向きは、最新の説明・kyuura の記録から決められないので扱わない"
    "（FU6。kyuura の UQ-FLASH-FACE-UP-DECK。山札を切るときのほかは、おもてを下にもどすと書かれていない）"
)
# エンジンの未対応（研究の未解決ではない）: おもてのカードのある山札を変える処理で、ここで分類していない経路
FACE_UP_DECK_PATH_CODE = "UNSUPPORTED_FACE_UP_DECK_PATH"

REASONS = {
    FLASH_DECK_SHORT_CODE: FLASH_DECK_SHORT_REASON,
    FACE_UP_DECK_CHECK_CODE: FACE_UP_DECK_CHECK_REASON,
    FACE_UP_DECK_HIDDEN_TAKE_CODE: FACE_UP_DECK_HIDDEN_TAKE_REASON,
    FACE_UP_DECK_PLACE_TOP_CODE: FACE_UP_DECK_PLACE_TOP_REASON,
    FACE_UP_DECK_LOOK_RETURN_CODE: FACE_UP_DECK_LOOK_RETURN_REASON,
    FACE_UP_DECK_MOVE_CODE: FACE_UP_DECK_MOVE_REASON,
}

# 見えない場所のうち、向きを持たない場所（手札。持ち主が持つだけ）と、公開の場所（トラッシュ・場・スタジアム・使用中のトレーナー）。ほかの場所（サイド・山札・置いておく場所）
# は向きを持つ
PUBLIC_PLACES = frozenset({"discard", "in_play", "stadium", "trainer_in_use"})
HAND = "hand"

# 山札から手札に加えるときに、全員に見せたカードのログ（``reveal_from_deck`` の ``card`` は公開）。見せたカードは、どの読みでも全員が知る
SHOWN_EVENTS = frozenset({"reveal_from_deck"})

# 山札の上を見るログ（見たカードの uid を ``cards``・``card`` に書く。``look_at_card`` は ``zone`` が ``"deck"`` のときだけ）
LOOK_EVENTS = frozenset({"look_at_deck_top", "reveal_deck_top", "look_at_card"})


def stop(code: str, detail: str = "") -> UnsupportedError:
    """停止の例外（理由の文に、見えないカードの中身を書かない）。"""
    return UnsupportedError(code, (f"{detail}: " if detail else "") + REASONS[code])


def face_up_in_deck(state: GameState, owner: int) -> tuple[int, ...]:
    """``owner`` の山札のおもてのカードの uid（山札の上からの順）。"""
    if not state.face_up_deck:
        return ()
    marks = set(state.face_up_deck)
    return tuple(uid for uid in state.players[owner].deck if uid in marks)


def face_up_count(state: GameState, owner: int) -> int:
    return len(face_up_in_deck(state, owner))


def visible_top(state: GameState, owner: int) -> int | None:
    """``owner`` の山札のいちばん上がおもてなら、その uid（双方・観戦者に見える。CR-FLASH-TOP-CARD-SEEN）。うら・山札が 0 枚なら None。"""
    deck = state.players[owner].deck
    if deck and state.face_up_deck and deck[0] in state.face_up_deck:
        return deck[0]
    return None


def has_face_up(state: GameState, owner: int) -> bool:
    return bool(state.face_up_deck) and any(uid in state.face_up_deck for uid in state.players[owner].deck)


def face_up_below_top(state: GameState, owner: int, count: int) -> bool:
    """``owner`` の山札の上から ``count`` 枚のうち、いちばん上より下（2 枚目〜）に、おもてのカードがあるか。"""
    deck = state.players[owner].deck
    return bool(state.face_up_deck) and any(uid in state.face_up_deck for uid in deck[1:count])


def face_up_within(state: GameState, owner: int, count: int) -> bool:
    """``owner`` の山札の上から ``count`` 枚のうちに、おもてのカードがあるか。"""
    deck = state.players[owner].deck
    return bool(state.face_up_deck) and any(uid in state.face_up_deck for uid in deck[:count])


def require_no_face_up(state: GameState, owner: int, code: str, detail: str) -> None:
    """``owner`` の山札におもてのカードがあれば ``code`` で止める（効果の処理の前・コインの前に呼ぶ）。"""
    if has_face_up(state, owner):
        raise stop(code, detail)


def require_look_without_face_up(state: GameState, owner: int, count: int, detail: str) -> None:
    """山札の上から ``count`` 枚を見てもどす・並べ替える処理の前（FU5）。見る範囲におもてのカードがあれば止める。"""
    if face_up_within(state, owner, count):
        raise stop(FACE_UP_DECK_LOOK_RETURN_CODE, detail)


def require_draw_through_face_up(state: GameState, owner: int, count: int, detail: str = "") -> None:
    """山札の上から ``count`` 枚をまとめて手札など見えない場所へ移す処理の前（FU3）。2 枚目より下におもてのカードがあれば止める（いちばん上のおもては見えているので止めない）。"""
    if count >= 2 and face_up_below_top(state, owner, count):
        raise stop(FACE_UP_DECK_HIDDEN_TAKE_CODE, detail or f"プレイヤー {owner} の山札の上から {count} 枚")


def clear_marks(state: GameState, owner: int) -> int:
    """``owner`` の山札のおもての印をすべて消す（山札を切る前。おもてを下にもどす）。消した数。乱数は使わない。"""
    marked = face_up_in_deck(state, owner)
    if marked:
        gone = set(marked)
        state.face_up_deck = tuple(uid for uid in state.face_up_deck if uid not in gone)
    return len(marked)


def set_marks(state: GameState, owner: int, cards: Iterable[int]) -> None:
    """``owner`` の山札のカード ``cards`` をおもてにする（フラッシュ。今の山札にあるカードだけ）。"""
    deck = set(state.players[owner].deck)
    cards = tuple(cards)
    if any(uid not in deck for uid in cards):
        raise RuntimeError(f"おもてにするカード {cards} が、プレイヤー {owner} の山札にない（エンジンの不具合）")
    state.face_up_deck = tuple(uid for uid in state.face_up_deck if uid not in cards) + cards


def drop_left_marks(state: GameState) -> None:
    """山札をはなれたカードの印を消す（カードが山札をはなれたら、別のカードに印がずれないように、カードごとの印を消す）。"""
    if not state.face_up_deck:
        return
    in_decks = {uid for p in state.players for uid in p.deck}
    kept = tuple(uid for uid in state.face_up_deck if uid in in_decks)
    if kept != state.face_up_deck:
        state.face_up_deck = kept


def place_of(state: GameState, uid: int) -> str:
    """カード ``uid`` のいまの場所の種類（``command_problem`` の行き先の分類）。"""
    for p in state.players:
        if uid in p.hand:
            return HAND
        if uid in p.deck:
            return "deck"
        if uid in p.discard:
            return "discard"
        if uid in p.prizes:
            return "prizes"
        for pokemon in p.in_play():
            if (uid == pokemon.card or uid == pokemon.disguise or uid in pokemon.evolution_stack or uid in pokemon.energy
                    or any(t.card == uid for t in pokemon.trainers)):
                return "in_play"
    if state.stadium is not None and state.stadium.card == uid:
        return "stadium"
    used = state.trainer_in_use
    if (used is not None and used.card == uid) or any(t.card == uid for t in state.trainer_stack):
        return "trainer_in_use"
    if any(uid in group.cards for group in state.set_aside):
        return "set_aside"
    return "unknown"


def _looked(event) -> tuple[int, ...]:
    if event["kind"] == "look_at_card":
        return (event["card"],) if event.get("zone") == "deck" else ()
    return tuple(event.get("cards") or ())


def _look_owner(event) -> int | None:
    if event["kind"] == "reveal_deck_top":
        return event.get("player")
    if event["kind"] == "look_at_card" and event.get("zone") != "deck":
        return None
    return event.get("owner")


def _first_moves(events, gone: set[int]) -> dict[int, int]:
    """山札をはなれたカード ``gone`` が、そのコマンドのログで最初に出たイベントの位置（見る・並べかえるログは除く。カードが動いた順を決める）。"""
    found: dict[int, int] = {}
    for i, e in enumerate(events):
        if e["kind"] in LOOK_EVENTS or e["kind"] == "arrange_deck_top":
            continue
        named = [e.get("card")] + [uid for name in ("cards",) if isinstance(e.get(name), (list, tuple)) for uid in e[name]]
        for uid in named:
            if uid in gone and uid not in found:
                found[uid] = i
    return found


def command_problem(before: GameState, after: GameState) -> tuple[str, str] | None:
    """1 つのコマンドの前（``before``）・あと（``after``）と、そのコマンドのログで、おもてのカードのある山札が、読み方で結果・要る情報が分かれる変わり方をしたら (コード, 理由)。

    - フラッシュの並べ替え（ログ ``flash_face_up``）をした山札は、フラッシュの処理が確かめる（ここでは見ない）
    - 山札をはなれたおもてのカード: 公開の場所（トラッシュ・場など）か、見せてから手札に加えた（``reveal_from_deck``）なら、どの読みでも全員に見えるので受け付ける。手札なら、
      そのときいちばん上（見えていたカード）だったものだけ受け付ける（上のカードがすべて、先に別のログで 1 枚ずつ動いていれば、そのときのいちばん上）。そうでなければ FU3。向きのある見えない場所（サイド・山札の別の位置・置いておく場所）なら FU6
    - 切った山札（ログ ``shuffle``）は、切る前に印を消すので、残りの並びは見ない
    - 切っていない山札: 残ったカードの並びが変わらず、新しいカードはいちばん下にだけ加わる（上・途中に置いた → FU4、並びが変わった → FU5。どちらでもない → エンジンの未対応）
    - 見るログ（``look_at_deck_top``・``reveal_deck_top``・山札の ``look_at_card``）がおもてのカードをふくみ、コマンドの終わりに決定がなく（処理が終わった）、見たおもてのカードが
      切られずに山札に残る（見てもどした）なら、いちばん上だけを見たときのほかはエンジンの未対応（見てもどす処理は、効果の処理の前に FU5 で止める）
    """
    if not before.face_up_deck:
        return None
    events = after.log[len(before.log):]
    for owner in (0, 1):
        marked = face_up_in_deck(before, owner)
        if not marked:
            continue
        if any(e["kind"] == "flash_face_up" and e.get("owner") == owner for e in events):
            continue
        d0, d1 = before.players[owner].deck, after.players[owner].deck
        remaining = set(d1)
        shown = {e.get("card") for e in events if e["kind"] in SHOWN_EVENTS}
        moved_at = _first_moves(events, set(d0) - remaining)
        for uid in marked:
            if uid in remaining:
                continue
            place = place_of(after, uid)
            position = d0.index(uid)
            if place in PUBLIC_PLACES or (place == HAND and uid in shown):
                continue
            if place == HAND:
                # いちばん上だったカード。同じコマンドで上のカードが先に 1 枚ずつ別のログで動いた（てつだうふりのあとの番の最初のドローなど）なら、そのときのいちばん上
                above = d0[:position]
                if position == 0 or (uid in moved_at and all(moved_at.get(card, len(events)) < moved_at[uid] for card in above)
                                     and sum(1 for card in moved_at if moved_at[card] == moved_at[uid]) == 1):
                    continue
                return FACE_UP_DECK_HIDDEN_TAKE_CODE, f"プレイヤー {owner} の山札の上から {position + 1} 枚目のおもてのカード: " + FACE_UP_DECK_HIDDEN_TAKE_REASON
            return FACE_UP_DECK_MOVE_CODE, f"プレイヤー {owner} の山札の上から {position + 1} 枚目のおもてのカード（行き先 {place}）: " + FACE_UP_DECK_MOVE_REASON
        if any(e["kind"] == "shuffle" and e.get("player") == owner for e in events):
            continue
        kept = [uid for uid in d0 if uid in remaining]
        if list(d1[:len(kept)]) != kept:
            last_marked = max(d1.index(uid) for uid in marked if uid in remaining) if any(uid in remaining for uid in marked) else -1
            if any(uid not in set(d0) for uid in d1[:last_marked + 1]):
                return FACE_UP_DECK_PLACE_TOP_CODE, f"プレイヤー {owner} の山札: " + FACE_UP_DECK_PLACE_TOP_REASON
            if sorted(d1[:len(kept)]) == sorted(kept):
                return FACE_UP_DECK_LOOK_RETURN_CODE, f"プレイヤー {owner} の山札: " + FACE_UP_DECK_LOOK_RETURN_REASON
            return FACE_UP_DECK_PATH_CODE, f"プレイヤー {owner} の山札のおもてのカードのある並びが、分類していない形で変わった（エンジンの未対応）"
        if after.decision is not None:
            continue
        marked_set = set(marked)
        for e in events:
            if e["kind"] not in LOOK_EVENTS or _look_owner(e) != owner:
                continue
            looked = _looked(e)
            kept_face_up = [uid for uid in looked if uid in marked_set and uid in remaining]
            if not kept_face_up or (len(looked) == 1 and d0 and looked[0] == d0[0]):
                continue
            return FACE_UP_DECK_PATH_CODE, (f"プレイヤー {owner} の山札のおもてのカードを見た処理（ログ {e['kind']}）が、見たカードを山札に残した（見てもどす処理を効果の前に止めていない。"
                                            "エンジンの未対応）")
    return None


def settle(before: GameState, after: GameState) -> None:
    """コマンドの終わり: 山札をはなれたカードの印を消し、いちばん上のおもてのカード（公開）が変わった山札にログ ``face_up_deck_top``（公開。カードの id とおもての枚数だけで、
    uid は書かない）を書く。フラッシュの並べ替え（``flash_face_up`` が新しいいちばん上を書く）・山札を切って印を消した（``shuffle`` の ``face_up_cleared``）山札には書かない。"""
    if not before.face_up_deck and not after.face_up_deck:
        return
    tops = [visible_top(before, owner) for owner in (0, 1)]
    drop_left_marks(after)
    events = after.log[len(before.log):]
    for owner in (0, 1):
        now = visible_top(after, owner)
        if now == tops[owner]:
            continue
        if any(e["kind"] == "flash_face_up" and e.get("owner") == owner for e in events):
            continue
        if now is None and any(e["kind"] == "shuffle" and e.get("player") == owner and e.get("face_up_cleared") for e in events):
            continue
        after.add_event("face_up_deck_top", player=owner, card_id=None if now is None else after.cards[now].card_id, face_up_count=face_up_count(after, owner))


def prefix_problems(state: GameState) -> list[str]:
    """不変条件: 印が重ならず、どれも山札のカードで、それぞれの山札で上から続く並びになっている。"""
    marks = state.face_up_deck
    if not isinstance(marks, tuple) or len(set(marks)) != len(marks):
        return [f"おもての山札の記録 {marks!r} が重ならない並びではない"]
    if not marks:
        return []
    problems = []
    in_decks = {uid for p in state.players for uid in p.deck}
    for uid in marks:
        if uid not in in_decks:
            problems.append(f"おもての山札の記録のカード {uid} が、山札にない")
    for owner, p in enumerate(state.players):
        flags = [uid in marks for uid in p.deck]
        count = sum(flags)
        if count and flags[:count] != [True] * count:
            problems.append(f"プレイヤー {owner} の山札のおもてのカードが、上から続く並びになっていない")
        if count > 5:
            problems.append(f"プレイヤー {owner} の山札のおもてのカードが {count} 枚（フラッシュが置くのは 5 枚）")
    revealed = {e["owner"] for e in state.log if e["kind"] == "flash_face_up"}
    for owner, p in enumerate(state.players):
        if any(uid in marks for uid in p.deck) and owner not in revealed:
            problems.append(f"プレイヤー {owner} の山札におもてのカードがあるが、おもてにしたログ（flash_face_up）がない")
    return problems

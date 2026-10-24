"""場のポケモンのマーカー・ダメージカウンター以外のカウンター（v0.90。docs/markers-counters-v0.90.md 3 章）。

ワザの説明がのせる「…マーカー」「…カウンター」（ダメージカウンター以外）は、ダメージ（``PokemonInPlay.damage``）・特殊状態（``conditions``）・ついているカード・
ワザによる持続する効果（``persistent_effects``）・特殊能力の使用の記録とは別のものなので、別の項目（``PokemonInPlay.markers``。``state.Marker`` のタプル）に持ち、
のせる・数える・取りのぞく処理をここにまとめる。カード定義・印刷のデータは書きかえない。乱数は使わない。

消える契機（基準は 2000.02.14 版の公式ルール。2000 年 5 月の RUL-CHAR-MARKER は持ち込まない）:

- 進化（``EVOLVE``）: p.310 の進化の手順（GR-2000-P310-EVOLUTION「マーカー・カウンター（ダメージカウンター以外）をとりのぞく」）。``evolution.place_evolution_card``
- 退化（``DEVOLVE``）: p.324「19 ポケモンの退化」（GR-2000-P324-DEVOLUTION「…や、その他の「持続する効果」から回復する（退化前とは別のポケモンとしてあつかう）」）と、
  p.322（GR-2000-P322-PERSISTENT-EFFECTS。カウンター・マーカーをのせるタイプも持続する効果で、ベンチにもどったときだけを除く）。``evolution.devolve``
- 場をはなれた: 場のポケモンといっしょになくなる（p.322「場をはなれたら消える」）。ログは場をはなれたこと（きぜつ・山札や手札にもどる・トラッシュ）だけで、マーカーごとの
  ログは残さない
- ワザの説明で取りのぞいた（``USED``。ほねこんぼう・ボーンキラー・ころがる）・のせ替えた（``REPLACED``。ペイントの色マーカー、v0.91 のハイパーテクスチャーの選んだ個体の
  色マーカー）・ワザの効果で取りのぞいた（``CLEARED``。かんぜんかいふく、v0.91 のオールクリアのおたがいの場のポケモン全員のマーカーとカウンター）

にげる・入れ替え・バトル場に出す・番の終わりでは消えない（p.311 の「のっているマーカーやカウンターをいっしょに移動する」・p.322 の「カウンター・マーカーをのせるタイプは
除く」）。特殊状態・かがくへんかガスでも消えない（特殊能力の効果ではない）。発生源が場をはなれたことでも消えない（p.322）。ばける・［へんしん］は進化・退化ではないので
変えない。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .conditions import DEVOLVE, EVOLVE
from .state import MARKER_AND_COUNTER_KINDS, MARKER_COLOR, Marker

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .state import GameState, PokemonInPlay

USED = "used"  # ワザの説明で取りのぞいた（ほねこんぼうの「それを1つとりのぞいて」・ボーンキラー・ころがるの「のぞむなら…取りのぞき」）
REPLACED = "replaced"  # のせ替えた（ペイントの「すでに…のっているなら、それをとりのぞいて、新たに…のせ替える」・v0.91 のハイパーテクスチャーの「それをとりのぞき」）
CLEARED = "cleared"  # ワザの効果で取りのぞいた（かんぜんかいふくの「自分にのっているダメージカウンターやマーカーをすべて取りのぞき」・v0.91 のオールクリアの「マーカーとカウンターを、すべてとりのぞく」）
# 取りのぞく理由（ログ ``marker_removed`` の ``reason``。進化・退化の値は特殊状態の ``conditions.EVOLVE``・``DEVOLVE`` と同じ）
REMOVAL_REASONS = (EVOLVE, DEVOLVE, USED, REPLACED, CLEARED)


def markers_of(pokemon: PokemonInPlay, kind: str) -> tuple[Marker, ...]:
    """``pokemon`` にのっている種類 ``kind`` のマーカー・カウンター（のせた順）。"""
    if kind not in MARKER_AND_COUNTER_KINDS:
        raise ValueError(f"マーカー・カウンターの種類 {kind!r} は {MARKER_AND_COUNTER_KINDS} のどれか")
    return tuple(marker for marker in pokemon.markers if marker.kind == kind)


def marker_count(pokemon: PokemonInPlay, kind: str) -> int:
    """``pokemon`` にのっている種類 ``kind`` の数。"""
    return len(markers_of(pokemon, kind))


def has_marker(pokemon: PokemonInPlay, kind: str) -> bool:
    """``pokemon`` に種類 ``kind`` が 1 つ以上のっているか。"""
    return marker_count(pokemon, kind) > 0


def color_marker(pokemon: PokemonInPlay) -> Marker | None:
    """``pokemon`` の色マーカー（ペイントで 1 つまで。のせ替える）。なければ None。2 つ以上は、どの色としてあつかうかが決まらない状態で、不変条件（``engine._marker_problems``）が
    拒否する（ここに来たらエンジンの不具合）。"""
    found = markers_of(pokemon, MARKER_COLOR)
    if len(found) > 1:
        raise RuntimeError(f"ポケモン {pokemon.pokemon_id} に色マーカーが {len(found)} つ（のせ替えるので 1 つまで。エンジンの不具合）")
    return found[0] if found else None


def _log_added(state: GameState, owner: int, pokemon: PokemonInPlay, marker: Marker) -> None:
    extra = {} if marker.color is None else {"color": marker.color.value}
    state.add_event("marker_added", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, marker=marker.kind, **extra,
                    count=marker_count(pokemon, marker.kind), by_player=marker.player, source_card=marker.source_card, effect=marker.attack)


def add_marker(state: GameState, owner: int, pokemon: PokemonInPlay, marker: Marker) -> None:
    """``pokemon``（持ち主 ``owner``）に ``marker`` を 1 つのせる。ログ ``marker_added``（``player``（持ち主）・``pokemon``・``pokemon_id``・``marker``（種類）・
    色マーカーなら ``color``・``count``（のせたあとのその種類の数）・``by_player``（のせたプレイヤー）・``source_card``・``effect``（のせたワザ））。のせるかどうか（「のって
    いなければ」・使うための条件・「ワザをうけない」状態・「とうめい」）は呼ぶ側が先に決める。"""
    if marker.kind not in MARKER_AND_COUNTER_KINDS:
        raise ValueError(f"マーカー・カウンターの種類 {marker.kind!r} は {MARKER_AND_COUNTER_KINDS} のどれか")
    if (marker.kind == MARKER_COLOR) != (marker.color is not None):
        raise ValueError(f"色を持つのは色マーカーだけ（{marker!r}）")
    pokemon.markers = (*pokemon.markers, marker)
    _log_added(state, owner, pokemon, marker)


def replace_marker(state: GameState, owner: int, pokemon: PokemonInPlay, marker: Marker) -> None:
    """``pokemon`` にのっている ``marker`` と同じ種類をすべて取りのぞいて（``REPLACED``）、``marker`` をのせる（ペイントの色マーカー）。"""
    remove_markers(state, owner, pokemon, REPLACED, kinds=(marker.kind,), effect=marker.attack)
    add_marker(state, owner, pokemon, marker)


def remove_markers(state: GameState, owner: int, pokemon: PokemonInPlay, reason: str, *, kinds: Iterable[str] | None = None, count: int | None = None,
                   effect: str | None = None) -> int:
    """``pokemon`` にのっている ``kinds``（None ならすべての種類）のマーカー・カウンターを、種類ごとに ``count`` 個（None ならすべて。のせた順に古いものから）取りのぞき、
    取りのぞいた数を返す。種類ごとにログ ``marker_removed``（``player``（持ち主）・``pokemon``・``pokemon_id``・``marker``・色マーカーなら ``color``・``count``（取りのぞいた数）・
    ``remaining``（残りの数）・``reason``・ワザなら ``effect``）。取りのぞくものがなければ何もしない（ログも残さない）。``count`` がのっている数より多ければエンジンの不具合
    （数は呼ぶ側が使うための条件・決定で決める）。"""
    if reason not in REMOVAL_REASONS:
        raise ValueError(f"マーカー・カウンターを取りのぞく理由 {reason!r} は {REMOVAL_REASONS} のどれか")
    wanted = MARKER_AND_COUNTER_KINDS if kinds is None else tuple(kinds)
    total = 0
    for kind in wanted:
        present = markers_of(pokemon, kind)
        take = len(present) if count is None else count
        if take > len(present) or take < 0:
            raise RuntimeError(f"ポケモン {pokemon.pokemon_id} から種類 {kind} を {take} 個取りのぞけない（{len(present)} 個。エンジンの不具合）")
        if take == 0:
            continue
        removed = present[:take]
        kept = list(pokemon.markers)
        for marker in removed:
            kept.remove(marker)
        pokemon.markers = tuple(kept)
        colors = {marker.color for marker in removed}
        extra = {} if kind != MARKER_COLOR else {"color": removed[0].color.value if len(colors) == 1 else sorted(c.value for c in colors)}
        state.add_event("marker_removed", player=owner, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, marker=kind, **extra, count=take,
                        remaining=marker_count(pokemon, kind), reason=reason, **({} if effect is None else {"effect": effect}))
        total += take
    return total


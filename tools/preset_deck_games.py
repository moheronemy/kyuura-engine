"""v0.20: 固定のデッキ（``kyuura_engine.decks``）どうしを、正式な対戦開始（``new_game``・60 枚・サイド 6 枚）から決まった手順で対戦させ、
終わり方を分類し、各デッキの狙った動きが起こったかを数える（C 段階の道具。ふだんのテストは tests/test_preset_decks_v0_20.py が小さく走らせる）。

使い方::

    python3 tools/preset_deck_games.py --games 20 --out /tmp/preset.json   # 席を入れかえて 20 局ずつ（合計 40 局）

駆動の方法（docs/preset-decks-v0.20.md 5 章）:

- 対戦の手順は、既存の統合テストの決まった手順（``tests.v017_games.play_game`` と ``tests.test_dark_wartortle_games_v0_13.policy_command``。
  v0.2b〜v0.13 の手順を重ねたもの: ベンチに出す・エネルギーをつける・進化・トレーナー（マサキ・きずぐすり・ポケモンいれかえ・プラスパワー・
  ディフェンダー）・エナジートランス・ワザの選び方・拒否されたときの扱い）をそのまま使う。対戦相手の AI ではない。
- この道具が加える手順は 2 つだけ（どちらもデッキの考え方を確かめるための決まった手順で、強さを目指したものではない）:
  1. エネルギー: 元の手順は手札の最初のエネルギーをバトル場につける。ここでは、バトル場のポケモンのワザの必要なタイプが足りなければその
     タイプを、足りていればベンチのうちそのデッキで育てる系統（ジュゴンの系統・フシギダネの系統・パラスの系統）で足りないタイプを優先する。
  2. オーキドはかせ: その番のほかの操作が終わった（元の手順がワザか番の終わりを選んだ）ときだけ、山札が 7 枚以上・残りの手札が 2 枚以下で、
     かつ、残りの手札に「場のポケモンから次の番に進化できる進化カード」がないときに使う（進化先を捨てない判断）。
- 先攻・後攻は seed の偶奇（``janken_winner = seed % 2``）で、席（デッキ A がプレイヤー 0 か 1 か）は ``--games`` 局ずつ入れかえる。
- v0.21: ``--variant gust`` は、固定のデッキのディフェンダー 4 枚のうち 3 枚を突風 3 枚に置き換えた一時的な 60 枚どうしで対戦させる
  （``deck_cards``。公開の固定のデッキ ``kyuura_engine.decks`` は変えない。docs/gust-v0.21.md 6 章）。加える手順は突風だけ:
  その番のほかの操作が終わった（元の手順がワザか番の終わりを選んだ）とき、1 番に 1 回だけ考え、相手の控えポケモンのうち残りの HP が
  いちばん少ないもの（同じならにげるエネルギーが多く、ついているエネルギーが少ないもの、さらに同じなら並びの先）の残りの HP が、相手の
  対戦ポケモンより少なければ使い、決定ではそのポケモンを選ぶ。相手に控えがいなければ使わない（原典で決められない場合。GW5）。
  既定の ``--variant preset`` は v0.20 と同じ（突風のカードがないので、この手順は何もしない）。
- v0.22: ``--variant computer`` は、固定のデッキのディフェンダー 3 枚をパソコン通信 3 枚に置き換えた一時的な 60 枚どうし（``deck_cards``。
  docs/computer-search-v0.22.md 6 章）。加える手順はパソコン通信だけ: その番のほかの操作が終わったとき、1 番に 1 回だけ考え、このカードを
  除く手札が 2 枚以上・山札が 1 枚以上で、山札に「今の番に使えるカード」（場のポケモンから進化できる進化カード → ベンチが 2 匹未満なら
  たねポケモン → まだエネルギーをつけていない番に、バトル場のポケモンのワザに足りないタイプの基本エネルギー）があれば使う。トラッシュする
  2 枚は、手札のうち決まった順（ディフェンダー・プラスパワー → 3 枚目からのエネルギー → 場に進化元のいない進化カード → ほかのトレーナー →
  エネルギー → たねポケモン → 場に進化元のいる進化カード。同じなら手札の並び）で選ぶ。山札が 0 枚なら使わない（原典で決められない場合。CS6）。
- v0.23: ``--variant mixed`` は、固定のデッキのディフェンダー 4 枚を除き、突風 2 枚・パソコン通信 2 枚を加えた一時的な 60 枚どうし。
  ``--variant retrieval`` は、さらにきずぐすり 2 枚をエネルギー回収 2 枚に置き換える（docs/energy-retrieval-v0.23.md 6 章）。パソコン通信は、
  山札に突風があり手札になく、突風の手順が今の番に使う場面なら突風を選ぶ（突風のないデッキでは何もしない）。エネルギー回収は、1 番に 1 回
  だけ考え、このカードを除く手札が 1 枚以上・トラッシュに基本エネルギーカードがあり、その番にまだつけていなくて手札に基本エネルギーカードが
  ないときに使い、足りないタイプを先に選べるだけ選ぶ（0 枚は選ばない。ER9。トラッシュに基本エネルギーカードがなければ使わない。ER10）。
  この 2 つの変種では、決定ごとの持ち主・使用中のカード（``check_…``）と、トレーナーを使ってからトラッシュするまでのログ
  （``trainer_sequence_problems``）も確かめる。
- v0.24: ``--variant trader`` は、``retrieval`` の残りのきずぐすり 2 枚をポケモン交換おじさん 2 枚に置き換えた一時的な 60 枚どうし
  （docs/pokemon-trader-v0.24.md 7 章）。加える手順はポケモン交換おじさんだけ: その番のほかの操作が終わったとき、1 番に 1 回だけ考え、
  手札に余ったポケモンのカード（場に進化元のいない進化カード、またはベンチが 4 匹以上のときのたねポケモン）があり、今の番に欲しいもの
  （今の番に進化できる場のポケモンの進化カードで手札にないもの、またはベンチが 2 匹未満で手札にたねポケモンがないこと）があれば使う
  （山札の中身は見ない）。もどすのは余ったカード、選ぶのは欲しい進化カード → たねポケモン → なければもどしたカード（選び直し。PT10）。
  ``mixed``・``retrieval`` と同じく ``check_…``・``trainer_sequence_problems`` も確かめ、もどした・手に入れたカードの段階と、手に入れた
  カードのその後（進化・ベンチ）を数える（``trader_uses``）。
- v0.25: ``--variant breeder`` は、デッキ A（エビワラー・ジュゴン。2 進化ポケモンがいない）は ``trader`` のまま、デッキ B（フシギバナ・
  パラセクト）だけ ``trader`` のマサキ 2 枚をポケモン育て屋さん 2 枚に置き換えた一時的な 60 枚どうし（``DECK_SUBSTITUTIONS``。
  docs/pokemon-breeder-v0.25.md 8 章）。加える手順はポケモン育て屋さんだけ: その番のほかの操作が終わったとき（突風・エネルギー回収の
  手順のあと、ポケモン交換おじさん・パソコン通信・オーキドはかせの手順の前）、1 番に 1 回だけ考え、進化させられる組（自分の場のその番の
  最初から場に出ていたたねポケモンと、手札の系統の合う 2 進化カード）があれば使う。進化させるのはバトル場のポケモン → ついている
  エネルギーが多いもの、重ねるのは選べるもののうち手札の並びの先。``mixed`` などと同じく ``check_…``・``trainer_sequence_problems`` も
  確かめ、使った回数・進化させたポケモン・進化したあとの特殊能力（エナジートランス）・ワザを数える（``breeder_uses``）。

- v0.26: ``--deck-a``・``--deck-b`` で、固定のデッキの第1版（``hitmonchan-dewgong``・``venusaur-parasect``。既定）と第2版
  （``hitmonchan-dewgong-v2``・``venusaur-parasect-v2``。docs/preset-decks-v0.26.md）の組み合わせを選べる（知らない識別子は引数の誤り）。
  第2版は既定の ``--variant preset``（デッキをそのまま使う）だけで使える（ほかの変種は第1版のディフェンダー・きずぐすり・マサキを置き換える
  一時的なデッキなので、第2版には使わない）。手順は変えていない: 上の突風・パソコン通信・エネルギー回収・ポケモン交換おじさん・ポケモン
  育て屋さんの手順は、どの変種でもいつも同じ（そのカードが手札になければ何もしない）ので、第1版と第2版は同じ手順で対戦する。
  ``play(..., observe=True)`` は、変種によらず ``check_…``・``trainer_sequence_problems`` と使ったトレーナーごとの結果（``…_uses``）を
  記録する（数えるだけで、選ぶ操作は変えない。tools/preset_deck_comparison.py が使う）。

終わり方の分類: 通常の勝敗（``game_over``）・サドンデス（``sudden_death``。エンジンは次の対戦を始めない）・既知の未解決の裁定による停止
（``halted``。コード付き）・手数の上限・想定外の拒否（手順が想定していない ``IllegalActionError``・``UnsupportedError``。駆動の誤りか、規定の
確認が要る）・内部エラー（不変条件の違反・そのほかの例外）。原典で決められないとして拒否された操作（``UNRESOLVED_…``）のあと別の操作で
続けた回数は、終わり方とは別に数える。どれも集計から落とさない。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kyuura_engine import (  # noqa: E402
    AttachEnergy, EndTurn, IllegalActionError, Phase, PlayTrainer, ResolveDecision, UnsupportedError, UseAttack, preset_deck, preset_deck_ids,
)
from kyuura_engine.cards import EnergyType  # noqa: E402
from kyuura_engine.effects import SKIP_EVOLUTION_OK, skip_evolution_pairs  # noqa: E402
from tests.test_dark_wartortle_games_v0_13 import policy_command as base_policy  # noqa: E402
from tests.v017_games import play_game  # noqa: E402

DECK_A, DECK_B = "hitmonchan-dewgong", "venusaur-parasect"
PROFESSOR_OAK = "PMCG1-077"
GUST = "PMCG1-072"  # v0.21
COMPUTER_SEARCH = "PMCG1-090"  # v0.22
ENERGY_RETRIEVAL = "PMCG1-076"  # v0.23
POKEMON_TRADER = "PMCG1-093"  # v0.24
POKEMON_BREEDER = "PMCG1-094"  # v0.25
BILL = "PMCG1-074"
PLUSPOWER = "PMCG1-081"
DEFENDER = "PMCG1-079"
POTION = "PMCG1-071"
DECK_A2, DECK_B2 = "hitmonchan-dewgong-v2", "venusaur-parasect-v2"  # v0.26 の第2版
SCYTHER = "PMCG2-017"  # v0.27
RATTATA = "PMCG1-060"
TANGELA = "PMCG1-007"
VARIANTS = ("preset", "gust", "computer", "mixed", "retrieval", "trader", "breeder", "scyther", "scyther_grass")
# v0.27: 第2版だけに使う一時的なデッキ（デッキの識別子 → （取り除くカード, 加えるカード, 枚数）。並びの位置はそのまま。ほかのデッキはそのまま。
# 公開の固定のデッキは変えない）。scyther はデッキ A2 のコラッタ 2 枚をストライク 2 枚に（構成 A。闘・水のエネルギーなので「つるぎのまい」は
# 使えない）、scyther_grass はデッキ B2 のモンジャラ 2 枚をストライク 2 枚に（構成 B。草エネルギーで「つるぎのまい」「きりさく」を使える検証用）
V2_SUBSTITUTIONS = {
    "scyther": {DECK_A2: ((RATTATA, SCYTHER, 2),)},
    "scyther_grass": {DECK_B2: ((TANGELA, SCYTHER, 2),)},
}
# 一時的なデッキの置き換え（固定のデッキの（取り除くカード, 加えるカード, 枚数）を順に。並びの位置はそのまま。公開の固定のデッキは変えない）
SUBSTITUTIONS = {
    "gust": ((DEFENDER, GUST, 3),),  # v0.21
    "computer": ((DEFENDER, COMPUTER_SEARCH, 3),),  # v0.22
    "mixed": ((DEFENDER, GUST, 2), (DEFENDER, COMPUTER_SEARCH, 2)),  # v0.23: ディフェンダー 4 枚 → 突風 2 枚・パソコン通信 2 枚
    # v0.23: mixed からさらに、きずぐすり 2 枚 → エネルギー回収 2 枚
    "retrieval": ((DEFENDER, GUST, 2), (DEFENDER, COMPUTER_SEARCH, 2), (POTION, ENERGY_RETRIEVAL, 2)),
    # v0.24: retrieval からさらに、残りのきずぐすり 2 枚 → ポケモン交換おじさん 2 枚
    "trader": ((DEFENDER, GUST, 2), (DEFENDER, COMPUTER_SEARCH, 2), (POTION, ENERGY_RETRIEVAL, 2), (POTION, POKEMON_TRADER, 2)),
    # v0.25: 両方のデッキは trader と同じ。そのうえで DECK_SUBSTITUTIONS で、2 進化ポケモンのいるデッキ B だけマサキ 2 枚 → ポケモン育て屋さん 2 枚
    "breeder": ((DEFENDER, GUST, 2), (DEFENDER, COMPUTER_SEARCH, 2), (POTION, ENERGY_RETRIEVAL, 2), (POTION, POKEMON_TRADER, 2)),
}
# v0.25: デッキごとの置き換え（変種の置き換えのあと）。デッキ A（エビワラー・ジュゴン）には 2 進化ポケモンがいないので、ポケモン育て屋さんを入れない
DECK_SUBSTITUTIONS = {"breeder": {DECK_B: ((BILL, POKEMON_BREEDER, 2),)}}
OAK_MIN_DECK = 7
OAK_MAX_REST = 2
# そのデッキで育てる系統（エネルギーをベンチにつけるときに優先する。デッキの考え方。docs/preset-decks-v0.20.md）
GROWING = {"PMCG1-029", "PMCG1-030", "PMCG1-001", "PMCG1-008", "PMCG1-011", "PMCG2-003", "PMCG2-010"}
STEP_LIMIT = "決まった手数で終わらなかった"


def _card(state, uid):
    return state.cards[uid].card_id


def _missing_types(state, pokemon):
    """そのポケモンのいちばん重いワザに足りないエネルギーのタイプ（無色を除く）。"""
    attacks = state.card_def(pokemon.card).attacks
    if not attacks:
        return set()
    have = Counter(state.energy_types(pokemon))
    need = Counter(t for t in max(attacks, key=lambda a: len(a.cost)).cost if t is not EnergyType.COLORLESS)
    return {t for t, n in need.items() if have[t] < n}


def _has_pending_evolution(state, player, rest):
    p = state.players[player]
    names = {state.card_def(pk.card).name_ja for pk in p.in_play()}
    return any(state.card_def(u).is_evolution_pokemon and state.card_def(u).evolves_from in names for u in rest)


def deck_cards(deck_id, variant="preset"):
    """対戦に使う 60 枚。``gust`` は固定のデッキのディフェンダー 3 枚を突風 3 枚に（v0.21）、``computer`` はパソコン通信 3 枚に（v0.22）、
    ``mixed`` はディフェンダー 4 枚を突風 2 枚・パソコン通信 2 枚に（v0.23）、``retrieval`` はさらにきずぐすり 2 枚をエネルギー回収 2 枚に
    （v0.23）、``trader`` はさらに残りのきずぐすり 2 枚をポケモン交換おじさん 2 枚に（v0.24）、``breeder`` は ``trader`` のデッキ B
    （フシギバナ・パラセクト）だけさらにマサキ 2 枚をポケモン育て屋さん 2 枚に（v0.25。``DECK_SUBSTITUTIONS``）置き換えた一時的なデッキ（``SUBSTITUTIONS``。
    並びの位置はそのまま。公開の固定のデッキは変えない）。v0.27 の ``scyther``・``scyther_grass`` は第2版だけに使う（``V2_SUBSTITUTIONS``）。"""
    cards = preset_deck(deck_id).cards()
    if variant == "preset":
        return cards
    if variant in V2_SUBSTITUTIONS:
        # v0.27: 第2版のカードを置き換える一時的なデッキ（変種ごとに 1 つのデッキだけを置き換え、もう一方の第2版はそのまま）
        if deck_id not in (DECK_A2, DECK_B2):
            raise ValueError(f"変種 {variant!r} は第2版のデッキ（{DECK_A2}・{DECK_B2}）だけに使える（{deck_id!r}）")
        for removed, added, count in V2_SUBSTITUTIONS[variant].get(deck_id, ()):
            for _ in range(count):
                cards[cards.index(removed)] = added
        return cards
    if variant not in SUBSTITUTIONS:
        raise ValueError(f"知らない変種 {variant!r}（{VARIANTS}）")
    if deck_id not in (DECK_A, DECK_B):
        # v0.26: 変種は第1版のカードを置き換える一時的なデッキ。第2版（-v2）はそのまま（--variant preset）で使う
        raise ValueError(f"変種 {variant!r} は第1版のデッキ（{DECK_A}・{DECK_B}）だけに使える（{deck_id!r} は preset で使う）")
    for removed, added, count in SUBSTITUTIONS[variant] + DECK_SUBSTITUTIONS.get(variant, {}).get(deck_id, ()):
        for _ in range(count):
            cards[cards.index(removed)] = added
    return cards


def _remaining_hp(state, pokemon):
    return state.card_def(pokemon.card).hp - pokemon.damage


def _gust_target(state, options):
    """突風で呼ぶ相手の控えポケモン（決まった手順。強さを目指したものではない）。"""
    def key(pid):
        pokemon = state.find_pokemon(pid)[1]
        # v0.47: なにかの化石・ピッピ人形の「にげる」は決まらない（PF2。印刷の数がない）ので 0 として並べる（ほかのポケモンの並びは変わらない）
        return (_remaining_hp(state, pokemon), -(state.card_def(pokemon.card).retreat_cost or 0), len(pokemon.energy), options.index(pid))
    return min(options, key=key)


def _gust_worth(state, player):
    """突風の手順が使う場面か（"no_opponent_bench"・"no_better_target"・None（使う））。"""
    opponent = state.players[1 - player]
    if not opponent.bench:
        return "no_opponent_bench"  # 控えがいないときに使えるかは原典で決められない（GW5）ので使わない
    target = state.find_pokemon(_gust_target(state, [b.pokemon_id for b in opponent.bench]))[1]
    if _remaining_hp(state, target) >= _remaining_hp(state, opponent.active):
        return "no_better_target"
    return None


def _gust_command(state, player, tried, counts):
    """v0.21: 突風を使うなら、そのコマンド。1 番に 1 回だけ考える。"""
    p = state.players[player]
    gust = next((u for u in p.hand if _card(state, u) == GUST), None)
    marker = ("gust", state.turn_number)
    if gust is None or marker in tried:
        return None
    tried.add(marker)
    reason = _gust_worth(state, player)
    if reason is not None:
        counts[f"gust_kept_{reason}"] += 1
        return None
    counts["gust_played"] += 1
    return PlayTrainer(player, gust)


def _can_evolve_now(state, pokemon):
    """場のポケモンが今の番に進化できそうか（その番の最初から場にいる・最初の番でない。p.310。手順の目安で、エンジンの確認ではない）。"""
    return state.turn_number > 2 and pokemon.current_form_turn < state.turn_number


def _search_target(state, player):
    """v0.22: パソコン通信で山札から選ぶカードと理由（決まった手順）。なければ None。"""
    p = state.players[player]
    in_play = p.in_play()
    deck = sorted(p.deck)
    # v0.23: 山札に突風があり、手札になく、突風の手順が今の番に使う場面なら、突風を選ぶ（突風のないデッキでは何もしない）
    gusts = [u for u in deck if _card(state, u) == GUST]
    if gusts and not any(_card(state, u) == GUST for u in p.hand) and _gust_worth(state, player) is None:
        return gusts[0], "gust"
    names = {state.card_def(pk.card).name_ja for pk in in_play if _can_evolve_now(state, pk)}
    evolvers = [u for u in deck if state.card_def(u).is_evolution_pokemon and state.card_def(u).evolves_from in names]
    if evolvers:
        return evolvers[0], "evolution"
    if len(p.bench) < 2:
        basics = [u for u in deck if state.card_def(u).is_basic_pokemon]
        if basics:
            return basics[0], "basic"
    if state.energy_attachments_this_turn == 0:
        for t in sorted(_missing_types(state, p.active), key=lambda t: t.value):
            energies = [u for u in deck if state.card_def(u).is_basic_energy and state.card_def(u).provides == t]
            if energies:
                return energies[0], "energy"
    return None


def _discard_choice(state, player, options, count):
    """v0.22: パソコン通信でトラッシュする手札（決まった順。低い値から）。"""
    p = state.players[player]
    names = {state.card_def(pk.card).name_ja for pk in p.in_play()}
    energy_in_hand = sum(state.card_def(u).is_basic_energy for u in options)

    def rank(uid):
        d = state.card_def(uid)
        if d.id in (DEFENDER, PLUSPOWER):
            return 0
        if d.is_basic_energy:
            return 1 if energy_in_hand >= 3 else 4
        if d.is_evolution_pokemon:
            return 6 if d.evolves_from in names else 2
        if d.category == "trainer":
            return 3
        if d.is_basic_pokemon:
            return 1 if len(p.bench) >= 5 else 5
        return 7

    return tuple(sorted(options, key=lambda u: (rank(u), options.index(u)))[:count])


def _computer_command(state, player, tried, counts):
    """v0.22: パソコン通信を使うなら、そのコマンド。1 番に 1 回だけ考える。"""
    p = state.players[player]
    card = next((u for u in p.hand if _card(state, u) == COMPUTER_SEARCH), None)
    marker = ("computer", state.turn_number)
    if card is None or marker in tried:
        return None
    tried.add(marker)
    if len(p.hand) - 1 < 2:
        counts["computer_kept_small_hand"] += 1  # 使うための条件（このカードを除く手札 2 枚）を満たせない（p.310）
        return None
    if not p.deck:
        counts["computer_kept_empty_deck"] += 1  # 原典で決められない（CS6）ので使わない
        return None
    target = _search_target(state, player)
    if target is None:
        counts["computer_kept_no_target"] += 1
        return None
    counts["computer_played"] += 1
    return PlayTrainer(player, card)


MIXED_VARIANTS = ("mixed", "retrieval", "trader", "breeder")
TRAINER_EVENTS = {
    # v0.23: 使ってからトラッシュするまでのあいだに出てよいログ（その実装が出すものだけ）と、そのイベントの player が使ったプレイヤーか相手か
    GUST: {"switch": "opponent", "special_conditions_removed": "opponent", "persistent_effect_removed": "opponent"},
    COMPUTER_SEARCH: {"discard_from_hand": "user", "search_deck": "user", "shuffle": "user"},
    ENERGY_RETRIEVAL: {"discard_from_hand": "user", "retrieve_energy": "user"},
    POKEMON_TRADER: {"return_to_deck": "user", "reveal_from_deck": "user", "shuffle": "user"},  # v0.24
    # v0.25: 進化（と、進化で消える特殊状態・持続する効果・にげるの失敗の記録）だけ。v0.43: 進化させた 2 進化ポケモンの場に出たときの特殊能力（わるいカイリューの
    # ［てしたをよぶ］）の使う機会の答え（使わない・宣言）と、その処理（山札からベンチに出す・山札を切る）
    POKEMON_BREEDER: {"evolve": "user", "special_conditions_removed": "user", "persistent_effect_removed": "user",
                      "retreat_failure_cleared": "user", "entry_power_declined": "user", "pokemon_power": "user", "bench_from_deck": "user",
                      "shuffle": "user"},
}


def _check_trainer_state(state, counts):
    """v0.23: 決定のたびに、決定するプレイヤー・番のプレイヤー・使用中のカードが、決定の ``use``（使ったプレイヤー・カード）と同じか。MAIN に
    もどったら使用中のカードが残っていないか（ほかのトレーナーの決定・使用中のカードと混ざらないこと）。"""
    if state.phase is Phase.MAIN:
        counts["check_main"] += 1
        if state.trainer_in_use is not None:
            counts["check_in_use_left_in_main"] += 1
        return
    d = state.decision
    if state.phase is not Phase.DECISION or d.resume != "trainer":
        return
    user, card, card_id = d.context_value("use")
    used = state.trainer_in_use
    counts[f"check_decision_{card_id}_{d.kind}"] += 1
    if not (d.player == user == state.current_player):
        counts["check_decision_player_mismatch"] += 1
    if used is None or (used.player, used.card) != (user, card) or state.cards[card].card_id != card_id:
        counts["check_in_use_mismatch"] += 1


def trainer_sequence_problems(state):
    """v0.23: 突風・パソコン通信・エネルギー回収を使ってから（``play_trainer``）トラッシュするまで（``discard_trainer``）のログに、ほかのトレーナーの使用・
    その実装が出さないイベント・持ち主の違うイベントがないか。終わっていない使用（決定を待つ間）は、最後の状態の使用中のカードと同じか。"""
    problems, open_use = [], None
    for i, e in enumerate(state.log):
        kind = e["kind"]
        if open_use is not None:
            user, card, card_id = open_use
            if kind == "discard_trainer":
                if (e["player"], e["card"]) != (user, card):
                    problems.append(f"{i}: 使用中の {card_id}（{card}）でないカード {e['card']} をトラッシュ")
                open_use = None
                continue
            allowed = TRAINER_EVENTS[card_id]
            if kind not in allowed:
                problems.append(f"{i}: {card_id} の使用中に {kind}")
            elif e.get("player") != (user if allowed[kind] == "user" else 1 - user):
                problems.append(f"{i}: {card_id} の使用中の {kind} の player が {e.get('player')}")
            continue
        if kind == "play_trainer" and _card(state, e["card"]) in TRAINER_EVENTS:
            open_use = (e["player"], e["card"], _card(state, e["card"]))
    if open_use is not None:
        used = state.trainer_in_use
        if used is None or (used.player, used.card) != open_use[:2]:
            problems.append(f"終わっていない {open_use[2]} の使用が、使用中のカードと合わない")
    return problems


def _retrieval_command(state, player, tried, counts):
    """v0.23: エネルギー回収を使うなら、そのコマンド。1 番に 1 回だけ考え、このカードを除く手札が 1 枚以上・トラッシュに基本エネルギー
    カードがあり、その番にまだエネルギーをつけていなくて、手札に基本エネルギーカードがないときに使う（手に入れたエネルギーをその番につける
    ため。決まった手順）。トラッシュに基本エネルギーカードがなければ使わない（原典で決められない場合。ER10）。"""
    p = state.players[player]
    card = next((u for u in p.hand if _card(state, u) == ENERGY_RETRIEVAL), None)
    marker = ("retrieval", state.turn_number)
    if card is None or marker in tried:
        return None
    tried.add(marker)
    if len(p.hand) - 1 < 1:
        counts["retrieval_kept_small_hand"] += 1  # 使うための条件（このカードを除く手札 1 枚）を満たせない（p.310）
        return None
    if not any(state.card_def(u).is_basic_energy for u in p.discard):
        counts["retrieval_kept_no_target"] += 1  # 原典で決められない（ER10）ので使わない
        return None
    if state.energy_attachments_this_turn or any(state.card_def(u).is_basic_energy for u in p.hand):
        counts["retrieval_kept_energy_ready"] += 1
        return None
    counts["retrieval_played"] += 1
    return PlayTrainer(player, card)


def _retrieval_choice(state, player, options, count):
    """v0.23: エネルギー回収で手札に加える基本エネルギーカード（決まった手順。バトル場のポケモン → 育てる系統のベンチのポケモンのワザに足りない
    タイプを先に、同じならトラッシュの並び）。いつも選べるだけ選ぶ（0 枚は選ばない。ER9）。"""
    p = state.players[player]
    wanted = sorted(_missing_types(state, p.active), key=lambda t: t.value)
    for pk in p.bench:
        if _card(state, pk.card) in GROWING:
            wanted += [t for t in sorted(_missing_types(state, pk), key=lambda t: t.value) if t not in wanted]

    def rank(uid):
        t = state.card_def(uid).provides
        return (wanted.index(t) if t in wanted else len(wanted), options.index(uid))

    return tuple(sorted(options, key=rank)[:count])


def _is_pokemon_card(state, uid):
    d = state.card_def(uid)
    return d.is_basic_pokemon or d.is_evolution_pokemon


def _trade_wants(state, player):
    """v0.24: 今の番に欲しいもの（決まった手順）: 今の番に進化できる場のポケモンの名前のうち、手札にその進化カードがないもの、と、ベンチが
    2 匹未満で手札にたねポケモンがないか。"""
    p = state.players[player]
    hand = [state.card_def(u) for u in p.hand]
    names = {state.card_def(pk.card).name_ja for pk in p.in_play() if _can_evolve_now(state, pk)}
    want_evolution = names - {d.evolves_from for d in hand if d.is_evolution_pokemon}
    want_basic = len(p.bench) < 2 and not any(d.is_basic_pokemon for d in hand)
    return want_evolution, want_basic


def _trade_rank(state, player, uid):
    """v0.24: 山札にもどす手札の順（低い値から）: 場に進化元のいない進化カード（余った進化カード）0 → ベンチが 4 匹以上のときのたね 1 →
    たね 2 → 場に進化元のいる進化カード 3。"""
    p = state.players[player]
    names = {state.card_def(pk.card).name_ja for pk in p.in_play()}
    d = state.card_def(uid)
    if d.is_evolution_pokemon:
        return 0 if d.evolves_from not in names else 3
    return 1 if len(p.bench) >= 4 else 2


def _breeder_command(state, player, tried, counts):
    """v0.25: ポケモン育て屋さんを使うなら、そのコマンド。1 番に 1 回だけ考え、自分の場のたねポケモン（その番の最初から場に出ていたもの）と、
    手札にその系統の 2 進化カードの組があれば使う（``effects.skip_evolution_pairs`` の進化させられる組。決まった手順）。おたがいの最初の番は
    使わない（p.310）。"""
    p = state.players[player]
    card = next((u for u in p.hand if _card(state, u) == POKEMON_BREEDER), None)
    marker = ("breeder", state.turn_number)
    if card is None or marker in tried:
        return None
    tried.add(marker)
    if state.turn_number <= 2:
        counts["breeder_kept_first_turn"] += 1
        return None
    if not _breeder_targets(state, player):
        counts["breeder_kept_no_pair"] += 1
        return None
    counts["breeder_played"] += 1
    return PlayTrainer(player, card)


def _breeder_targets(state, player):
    """v0.25: 進化させられる組（場のポケモンの番号 → 重ねられる手札の 2 進化カード）。"""
    pairs = skip_evolution_pairs(state, player)
    return {pid: [uid for uid, status in entries if status == SKIP_EVOLUTION_OK] for pid, entries in pairs.items()
            if any(status == SKIP_EVOLUTION_OK for _, status in entries)}


def _breeder_target_choice(state, player, options):
    """v0.25: 進化させるたねポケモン（決まった手順）: バトル場のポケモン → ついているエネルギーが多いもの → 場の並び。"""
    active = state.players[player].active
    def key(pid):
        pokemon = state.find_pokemon(pid)[1]
        return (pokemon is not active, -len(pokemon.energy), options.index(pid))
    return min(options, key=key)


def _trader_command(state, player, tried, counts):
    """v0.24: ポケモン交換おじさんを使うなら、そのコマンド。1 番に 1 回だけ考え、手札に余ったポケモンのカード（``_trade_rank`` が 0・1）があり、
    今の番に欲しいもの（``_trade_wants``）があるときに使う（山札の中身は見ない。手に入らなければ、もどしたカードを選び直す）。"""
    p = state.players[player]
    card = next((u for u in p.hand if _card(state, u) == POKEMON_TRADER), None)
    marker = ("trader", state.turn_number)
    if card is None or marker in tried:
        return None
    tried.add(marker)
    surplus = [u for u in p.hand if u != card and _is_pokemon_card(state, u) and _trade_rank(state, player, u) <= 1]
    if not any(u != card and _is_pokemon_card(state, u) for u in p.hand):
        counts["trader_kept_no_pokemon_in_hand"] += 1  # 使うための条件を満たせない（p.259）
        return None
    if not surplus:
        counts["trader_kept_no_surplus"] += 1
        return None
    want_evolution, want_basic = _trade_wants(state, player)
    if not (want_evolution or want_basic):
        counts["trader_kept_no_want"] += 1
        return None
    counts["trader_played"] += 1
    return PlayTrainer(player, card)


def _trader_search_choice(state, player, options, returned):
    """v0.24: 山札から選ぶカードと理由（決まった手順）: 今の番に進化できる場のポケモンの進化カード → ベンチが 2 匹未満ならたね → なければ
    もどしたカード（選び直し）。"""
    want_evolution, want_basic = _trade_wants(state, player)
    for uid in options:
        d = state.card_def(uid)
        if d.is_evolution_pokemon and d.evolves_from in want_evolution:
            return uid, "evolution"
    if want_basic:
        for uid in options:
            if state.card_def(uid).is_basic_pokemon and uid != returned:
                return uid, "basic"
    return returned, "returned"


def make_policy(seen: dict, counts: Counter, *, checks: bool = False):
    """元の手順に、エネルギーのつけ方とオーキドはかせの使い方（v0.21 から突風の使い方も）を重ねる。``seen`` に最後に見た状態を残す
    （止まったときの報告のため）。``checks`` なら決定ごとの持ち主・使用中のカードを数える（v0.23 の混ぜた変種だけ。ほかの変種の数えは変えない）。"""

    def policy(state, *, janken_winner, cure, tried):
        seen["state"] = state
        if checks:
            _check_trainer_state(state, counts)
        d = state.decision
        if state.phase is Phase.DECISION and d.context_value("use", (None, None, None))[2] == GUST:
            # v0.21: 突風の決定は、使ったプレイヤー（番のプレイヤー）が相手の控えポケモンから選ぶ
            chosen = _gust_target(state, list(d.options))
            counts[f"gust_candidates_{len(d.options)}"] += 1
            if len(d.options) > 1:
                counts["gust_chose_among_many"] += 1
                if chosen != d.options[0]:
                    counts["gust_chose_not_first"] += 1
            return ResolveDecision(d.player, d.id, (chosen,))
        if state.phase is Phase.DECISION and d.context_value("use", (None, None, None))[2] == COMPUTER_SEARCH:
            # v0.22: パソコン通信の決定（どちらも使ったプレイヤー）。段階 1 は手札から 2 枚、段階 2 は山札から 1 枚
            if d.kind == "discard_from_hand":
                chosen = _discard_choice(state, d.player, list(d.options), d.max_choices)
                for uid in chosen:
                    counts[f"computer_discarded_{state.card_def(uid).category}"] += 1
                return ResolveDecision(d.player, d.id, chosen)
            target, reason = _search_target(state, d.player) or (d.options[0], "fallback")
            counts[f"computer_search_{reason}"] += 1
            return ResolveDecision(d.player, d.id, (target,))
        if state.phase is Phase.DECISION and d.context_value("use", (None, None, None))[2] == POKEMON_BREEDER:
            # v0.25: ポケモン育て屋さんの決定（どちらも使ったプレイヤー）。段階 1 は進化させるたねポケモン、段階 2 は重ねる手札の 2 進化カード
            if d.kind == "select_pokemon":
                chosen = _breeder_target_choice(state, d.player, list(d.options))
                pokemon = state.find_pokemon(chosen)[1]
                counts["breeder_target_" + ("active" if pokemon is state.players[d.player].active else "bench")] += 1
                return ResolveDecision(d.player, d.id, (chosen,))
            counts[f"breeder_card_{state.cards[d.options[0]].card_id}"] += 1
            return ResolveDecision(d.player, d.id, (d.options[0],))
        if state.phase is Phase.DECISION and d.context_value("use", (None, None, None))[2] == POKEMON_TRADER:
            # v0.24: ポケモン交換おじさんの決定（どちらも使ったプレイヤー）。段階 1 は手札のたねポケモン・進化カードから 1 枚、段階 2 は山札から 1 枚
            if d.kind == "return_to_deck":
                chosen = min(d.options, key=lambda u: (_trade_rank(state, d.player, u), d.options.index(u)))
                counts[f"trader_returned_{state.card_def(chosen).stage}"] += 1
                return ResolveDecision(d.player, d.id, (chosen,))
            target, reason = _trader_search_choice(state, d.player, list(d.options), d.context_value("returned"))
            counts[f"trader_search_{reason}"] += 1
            return ResolveDecision(d.player, d.id, (target,))
        if state.phase is Phase.DECISION and d.context_value("use", (None, None, None))[2] == ENERGY_RETRIEVAL:
            # v0.23: エネルギー回収の決定（どちらも使ったプレイヤー）。段階 1 は手札から 1 枚、段階 2 はトラッシュの基本エネルギーカードから最大 2 枚
            if d.kind == "discard_from_hand":
                chosen = _discard_choice(state, d.player, list(d.options), d.max_choices)
                for uid in chosen:
                    counts[f"retrieval_discarded_{state.card_def(uid).category}"] += 1
                return ResolveDecision(d.player, d.id, chosen)
            chosen = _retrieval_choice(state, d.player, list(d.options), d.max_choices)
            counts[f"retrieval_retrieved_{len(chosen)}_of_{len(d.options)}"] += 1
            return ResolveDecision(d.player, d.id, chosen)
        command = base_policy(state, janken_winner=janken_winner, cure=cure, tried=tried)
        if state.phase is not Phase.MAIN:
            return command
        player = state.current_player
        p = state.players[player]
        if isinstance(command, AttachEnergy):
            return _energy_command(state, player, command, counts)
        if isinstance(command, (UseAttack, EndTurn)):
            gust = _gust_command(state, player, tried, counts)
            if gust is not None:
                return gust
            retrieval = _retrieval_command(state, player, tried, counts)
            if retrieval is not None:
                return retrieval
            breeder = _breeder_command(state, player, tried, counts)
            if breeder is not None:
                return breeder
            trader = _trader_command(state, player, tried, counts)
            if trader is not None:
                return trader
            computer = _computer_command(state, player, tried, counts)
            if computer is not None:
                return computer
            oak = next((u for u in p.hand if _card(state, u) == PROFESSOR_OAK), None)
            if oak is not None:
                rest = [u for u in p.hand if u != oak]
                marker = ("oak", state.turn_number)
                if len(p.deck) < OAK_MIN_DECK:
                    if marker not in tried:
                        counts["oak_skipped_small_deck"] += 1
                        tried.add(marker)
                elif len(rest) > OAK_MAX_REST:
                    pass
                elif _has_pending_evolution(state, player, rest):
                    if marker not in tried:
                        counts["oak_kept_for_evolution"] += 1
                        tried.add(marker)
                else:
                    return PlayTrainer(player, oak)
        return command

    return policy


def _energy_command(state, player, command, counts):
    p = state.players[player]
    energies = [u for u in p.hand if state.card_def(u).is_basic_energy]
    by_type = {}
    for u in energies:
        by_type.setdefault(state.card_def(u).provides, u)
    for t in sorted(_missing_types(state, p.active), key=lambda t: t.value):
        if t in by_type:
            counts["attach_active_needed"] += 1
            return AttachEnergy(player, by_type[t], p.active.card)
    for pk in p.bench:
        if _card(state, pk.card) in GROWING:
            for t in sorted(_missing_types(state, pk), key=lambda t: t.value):
                if t in by_type:
                    counts["attach_bench_growing"] += 1
                    return AttachEnergy(player, by_type[t], pk.card)
    counts["attach_default"] += 1
    return command


def deck_stats(state, player, commands):
    """1 人のプレイヤー（デッキ）の、ログから数えた動き。"""
    c = Counter()
    starting_bench = next((len(e["bench"]) for e in state.log if e["kind"] == "place_starting_pokemon" and e["player"] == player), 0)
    c["bench_played"] = starting_bench + sum(1 for e in state.log if e["kind"] == "play_to_bench" and e["player"] == player)
    for e in state.log:
        if e.get("player") != player:
            continue
        kind = e["kind"]
        if kind == "attach_energy":
            c[f"attach_{state.card_def(e['energy']).provides.name}"] += 1
        elif kind == "evolve":
            c[f"evolve_{_card(state, e['to_card'])}"] += 1
        elif kind == "play_trainer":
            c[f"trainer_{_card(state, e['card'])}"] += 1
        elif kind == "attack":
            c[f"attack_{_card(state, e['pokemon'])}#{e['attack_index']}"] += 1
        elif kind == "move_energy":
            c["energy_trans"] += 1
        elif kind == "retreat":
            c["retreat"] += 1
        elif kind == "discard_hand":
            c["oak_discarded"] += len(e["cards"])
            c["oak_discarded_evolution"] += sum(state.card_def(u).is_evolution_pokemon for u in e["cards"])
            c["oak_discarded_energy"] += sum(state.card_def(u).is_basic_energy for u in e["cards"])
        elif kind == "take_prize":
            c["prizes_taken"] += 1
    c["turns_ended_without_attack"] = sum(1 for cmd in commands if isinstance(cmd, EndTurn) and cmd.player == player)
    p = state.players[player]
    leftover = [u for u in p.hand + p.deck + p.prizes]
    c["trainers_left"] = sum(state.card_def(u).category == "trainer" for u in leftover)
    c["trainers_left_in_hand"] = sum(state.card_def(u).category == "trainer" for u in p.hand)
    c["evolution_cards_left"] = sum(state.card_def(u).is_evolution_pokemon for u in leftover)
    return c


def gust_uses(state):
    """v0.21: 突風を使うたびの、ログから分かる結果（使った番・プレイヤー・入れ替えた相手・その番のワザ・新しい対戦ポケモンへのダメージ・きぜつ）。"""
    uses, log = [], state.log
    for i, e in enumerate(log):
        if e["kind"] != "play_trainer" or _card(state, e["card"]) != GUST:
            continue
        user, turn = e["player"], e["turn"]
        use = {"turn": turn, "user": user, "switched": False}
        uses.append(use)
        switch = log[i + 1] if i + 1 < len(log) and log[i + 1]["kind"] == "switch" else None
        if switch is None:
            continue
        new_card = switch["new_active"]  # ダメージ・きぜつのログはいちばん上のカードで指す（相手のポケモンは自分の番に進化しない）
        use.update(switched=switch["player"] == 1 - user, new_active=_card(state, switch["new_active"]),
                   old_active=_card(state, switch["old_active"]))
        rest = [x for x in log[i + 2:] if x["turn"] == turn]
        attack = next((k for k, x in enumerate(rest) if x["kind"] == "attack" and x["player"] == user), None)
        use["attacked_after"] = attack is not None
        if attack is not None:
            after = rest[attack + 1:]
            use["attack"] = f"{_card(state, rest[attack]['pokemon'])}#{rest[attack]['attack_index']}"
            use["hit_new_active"] = any(x["kind"] == "damage" and x["pokemon"] == new_card and x["amount"] > 0 for x in after)
            use["knocked_out_new_active"] = any(x["kind"] == "knock_out" and x["pokemon"] == new_card for x in after)
    return uses


def computer_uses(state):
    """v0.22: パソコン通信を使うたびの、ログから分かる結果（使った番・プレイヤー・トラッシュした 2 枚・選んだカード・切ったか・選んだカードを
    その番・あとの番に使ったか（進化・ベンチ・エネルギー・トレーナー））。"""
    uses, log = [], state.log
    spent = {}
    for i, e in enumerate(log):
        kind = e["kind"]
        for key in ("to_card", "energy", "card"):
            if kind in ("evolve", "attach_energy", "play_to_bench", "play_trainer") and key in e and e[key] not in spent:
                spent[e[key]] = (e["turn"], kind)
    for i, e in enumerate(log):
        if e["kind"] != "play_trainer" or _card(state, e["card"]) != COMPUTER_SEARCH:
            continue
        rest = log[i + 1:i + 6]
        use = {"turn": e["turn"], "user": e["player"]}
        discard = next((x for x in rest if x["kind"] == "discard_from_hand"), None)
        search = next((x for x in rest if x["kind"] == "search_deck"), None)
        if discard is not None:
            use["discarded"] = [_card(state, u) for u in discard["cards"]]
        if search is not None:
            card = search["card"]
            use.update(searched=_card(state, card), searched_category=state.card_def(card).category,
                       shuffled=any(x["kind"] == "shuffle" and x["player"] == e["player"] for x in rest))
            later = spent.get(card)
            if later is not None and later[0] >= e["turn"]:
                use["used_as"] = later[1]
                use["used_same_turn"] = later[0] == e["turn"]
        uses.append(use)
    return uses


def retrieval_uses(state):
    """v0.23: エネルギー回収を使うたびの、ログから分かる結果（使った番・プレイヤー・トラッシュした 1 枚・手札に加えた基本エネルギーカード・
    そのカードのあとの使い道（つけた番・その番か・ほかの効果でトラッシュしたか・最後まで手札か山札に残ったか））。"""
    uses, log = [], state.log
    for i, e in enumerate(log):
        if e["kind"] != "play_trainer" or _card(state, e["card"]) != ENERGY_RETRIEVAL:
            continue
        rest = log[i + 1:i + 5]
        use = {"turn": e["turn"], "user": e["player"]}
        discard = next((x for x in rest if x["kind"] == "discard_from_hand"), None)
        retrieve = next((x for x in rest if x["kind"] == "retrieve_energy"), None)
        if discard is not None:
            use["discarded"] = [_card(state, u) for u in discard["cards"]]
            use["discarded_basic_energy"] = sum(state.card_def(u).is_basic_energy for u in discard["cards"])
        if retrieve is not None:
            use["retrieved"] = [_card(state, u) for u in retrieve["cards"]]
            fates = []
            for uid in retrieve["cards"]:
                later = next((x for x in log[i + 1:] if x["kind"] in ("attach_energy", "discard_hand", "discard_from_hand")
                              and (x.get("energy") == uid or uid in (x.get("cards") or ()))), None)
                if later is None:
                    fates.append("kept")
                elif later["kind"] == "attach_energy":
                    fates.append("attached_same_turn" if later["turn"] == e["turn"] else "attached_later")
                else:
                    fates.append(f"discarded_by_{later['kind']}")
            use["fates"] = fates
        uses.append(use)
    return uses


def trader_uses(state):
    """v0.24: ポケモン交換おじさんを使うたびの、ログから分かる結果（使った番・プレイヤー・山札にもどしたカードと段階・山札から見せて手札に
    加えたカードと段階・もどしたカードと同じか・切ったか・手に入れたカードのあとの使い道（進化・ベンチ。その番か））。"""
    uses, log = [], state.log
    for i, e in enumerate(log):
        if e["kind"] != "play_trainer" or _card(state, e["card"]) != POKEMON_TRADER:
            continue
        rest = log[i + 1:i + 6]
        use = {"turn": e["turn"], "user": e["player"]}
        returned = next((x["card"] for x in rest if x["kind"] == "return_to_deck"), None)
        taken = next((x["card"] for x in rest if x["kind"] == "reveal_from_deck"), None)
        if returned is not None:
            use.update(returned=_card(state, returned), returned_stage=state.card_def(returned).stage)
        if taken is not None:
            use.update(taken=_card(state, taken), taken_stage=state.card_def(taken).stage, took_back=taken == returned,
                       shuffled=any(x["kind"] == "shuffle" and x["player"] == e["player"] for x in rest))
            later = next((x for x in log[i + 1:] if (x["kind"] == "evolve" and x["to_card"] == taken)
                          or (x["kind"] == "play_to_bench" and x["card"] == taken)), None)
            if later is not None:
                use["used_as"] = later["kind"]
                use["used_same_turn"] = later["turn"] == e["turn"]
        uses.append(use)
    return uses


def breeder_uses(state):
    """v0.25: ポケモン育て屋さんを使うたびの、ログから分かる結果（使った番・プレイヤー・進化させたポケモン（たねポケモン → 2 進化カード）・
    バトル場か・その番と次の自分の番までのそのポケモンの特殊能力（エナジートランス）・ワザ・きぜつ）。"""
    uses, log = [], state.log
    for i, e in enumerate(log):
        if e["kind"] != "play_trainer" or _card(state, e["card"]) != POKEMON_BREEDER:
            continue
        use = {"turn": e["turn"], "user": e["player"]}
        evolve = next((x for x in log[i + 1:i + 6] if x["kind"] == "evolve" and x.get("trainer_card") == e["card"]), None)
        if evolve is not None:
            pid, top = evolve["pokemon_id"], evolve["to_card"]
            use.update(pokemon_id=pid, from_card=evolve["from_card_id"], to_card=evolve["to_card_id"])
            after = [x for x in log[i + 1:] if x["turn"] <= e["turn"] + 2]
            use["powers_same_turn"] = sum(1 for x in after if x["kind"] == "pokemon_power" and x.get("pokemon_id") == pid and x["turn"] == e["turn"])
            use["attacked_same_turn"] = any(x["kind"] == "attack" and x.get("pokemon") == top and x["turn"] == e["turn"] for x in after)
            use["attacked_next_own_turn"] = any(x["kind"] == "attack" and x.get("pokemon") == top and x["turn"] == e["turn"] + 2 for x in after)
            use["knocked_out_by_next_own_turn"] = any(x["kind"] == "knock_out" and x.get("pokemon") == top for x in after)
        uses.append(use)
    return uses


def play(deck_ids, seed, *, max_steps=8000, keep_state=False, variant="preset", observe=False):
    """1 局を進め、終わり方と動きを返す。``keep_state`` なら最後の状態を ``"state"`` に入れる（テストの監査のため。JSON にはしない）。
    ``observe``（v0.26）なら、変種によらず決定ごとの確かめ（``check_…``）・トレーナーのログの並び・トレーナーごとの結果を記録する（数えるだけ）。"""
    seen, counts = {}, Counter()
    decks = tuple(deck_cards(d, variant) for d in deck_ids)
    mixed = variant in MIXED_VARIANTS or observe
    result = {"seed": seed, "decks": list(deck_ids), "first": seed % 2}
    if variant != "preset":
        result["variant"] = variant
    commands = []
    try:
        state, commands, observed = play_game(decks, seed, policy=make_policy(seen, counts, checks=mixed), max_steps=max_steps)
        outcome = state.phase.value
        if state.phase is Phase.HALTED:
            outcome = "halted"
            result["halt_code"] = next((e["code"] for e in reversed(state.log) if e["kind"] == "halted"), None)
    except AssertionError as error:
        state, observed = seen.get("state"), Counter()
        outcome = "step_limit" if str(error) == STEP_LIMIT else "internal_error"
        result["error"] = str(error)[:500]
    except (IllegalActionError, UnsupportedError) as error:
        state, observed = seen.get("state"), Counter()
        outcome = "unexpected_rejection"
        result["error"] = f"{error.code}: {error}"[:500]
    except Exception as error:  # noqa: BLE001  内部エラーも集計から落とさない
        state, observed = seen.get("state"), Counter()
        outcome = "internal_error"
        result["error"] = "".join(traceback.format_exception_only(type(error), error))[:500]
    result["outcome"] = outcome
    result["steps"] = len(commands)
    result["observed"] = dict(observed)
    result["unresolved_rejections"] = {k: v for k, v in observed.items() if "UNRESOLVED_" in k}
    result["policy"] = dict(counts)
    if state is not None:
        result["turns"] = state.turn_number
        if state.result is not None:
            result["winner_deck"] = deck_ids[state.result.winner] if state.result.winner is not None else None
            result["conditions"] = [c[1] for c in state.result.conditions]
        result["per_deck"] = {deck_ids[p]: dict(deck_stats(state, p, commands)) for p in (0, 1)}
        if variant in ("gust",) + MIXED_VARIANTS or observe:
            result["gust_uses"] = gust_uses(state)
        if variant in ("computer",) + MIXED_VARIANTS or observe:
            result["computer_uses"] = computer_uses(state)
        if variant in ("retrieval", "trader", "breeder") or observe:
            result["retrieval_uses"] = retrieval_uses(state)
        if variant in ("trader", "breeder") or observe:
            result["trader_uses"] = trader_uses(state)
        if variant == "breeder" or observe:
            result["breeder_uses"] = breeder_uses(state)
        if mixed:
            result["trainer_sequence_problems"] = trainer_sequence_problems(state)
    if keep_state:
        result["state"] = state
        result["commands"] = commands
    return result


def run(games, *, start=0, max_steps=8000, keep_state=False, variant="preset", decks=(DECK_A, DECK_B)):
    """席を入れかえて ``games`` 局ずつ（seed は start から）。``decks``（v0.26）はデッキ A・B の識別子（既定は第1版どうし）。"""
    a, b = decks
    for deck_id in decks:
        deck_cards(deck_id, variant)  # 知らない識別子・第2版に使えない変種は、1 局も始める前に拒否する（0 局の成功として扱わない）
    results = []
    for seat in ((a, b), (b, a)):
        for seed in range(start, start + games):
            results.append(play(seat, seed, max_steps=max_steps, keep_state=keep_state, variant=variant))
    return results


def summarize(results):
    # v0.26: デッキの識別子は結果から（最初の局の席の順。既定は第1版の DECK_A・DECK_B で、v0.25 までと同じ並び）
    decks = list(dict.fromkeys(d for r in results for d in r["decks"])) or [DECK_A, DECK_B]
    s = {"games": len(results), "outcomes": Counter(), "halt_codes": Counter(), "unresolved_rejections": Counter(),
         "wins": Counter(), "end_conditions": Counter(), "per_deck": {d: Counter() for d in decks},
         "policy": Counter(), "games_with": {d: Counter() for d in decks}}
    for r in results:
        s["outcomes"][r["outcome"]] += 1
        if r.get("halt_code"):
            s["halt_codes"][r["halt_code"]] += 1
        s["unresolved_rejections"].update(r["unresolved_rejections"])
        if r.get("winner_deck"):
            s["wins"][r["winner_deck"]] += 1
        s["end_conditions"].update(r.get("conditions", []))
        s["policy"].update(r["policy"])
        for deck, stats in r.get("per_deck", {}).items():
            s["per_deck"][deck].update(stats)
            for key, value in stats.items():
                if value:
                    s["games_with"][deck][key] += 1
        if "gust_uses" in r:
            gust = s.setdefault("gust", {"uses": Counter(), "games_with_use": 0, "examples_attack_after": []})
            gust["games_with_use"] += bool(r["gust_uses"])
            for use in r["gust_uses"]:
                gust["uses"].update({"played": 1, "switched": use["switched"], "attacked_after": use.get("attacked_after", False),
                                     "hit_new_active": use.get("hit_new_active", False),
                                     "knocked_out_new_active": use.get("knocked_out_new_active", False)})
                if use.get("hit_new_active") and len(gust["examples_attack_after"]) < 5:
                    gust["examples_attack_after"].append({"seed": r["seed"], "decks": r["decks"], **use})
        if "computer_uses" in r:
            comp = s.setdefault("computer", {"uses": Counter(), "games_with_use": 0, "searched": Counter(), "searched_category": Counter(),
                                             "used_as": Counter(), "examples": []})
            comp["games_with_use"] += bool(r["computer_uses"])
            for use in r["computer_uses"]:
                comp["uses"].update({"played": 1, "discarded_two": len(use.get("discarded", ())) == 2, "searched": "searched" in use,
                                     "shuffled": use.get("shuffled", False), "used_later": "used_as" in use,
                                     "used_same_turn": use.get("used_same_turn", False)})
                if "searched" in use:
                    comp["searched"][use["searched"]] += 1
                    comp["searched_category"][use["searched_category"]] += 1
                if "used_as" in use:
                    comp["used_as"][use["used_as"]] += 1
                if use.get("used_same_turn") and len(comp["examples"]) < 5:
                    comp["examples"].append({"seed": r["seed"], "decks": r["decks"], **use})
        if "retrieval_uses" in r:
            ret = s.setdefault("retrieval", {"uses": Counter(), "games_with_use": 0, "retrieved_count": Counter(), "retrieved": Counter(),
                                             "fates": Counter(), "discarded": Counter(), "examples": []})
            ret["games_with_use"] += bool(r["retrieval_uses"])
            for use in r["retrieval_uses"]:
                ret["uses"].update({"played": 1, "discarded_one": len(use.get("discarded", ())) == 1,
                                    "discarded_basic_energy": use.get("discarded_basic_energy", 0) > 0, "retrieved": "retrieved" in use})
                ret["retrieved_count"][len(use.get("retrieved", ()))] += 1
                ret["retrieved"].update(use.get("retrieved", ()))
                ret["fates"].update(use.get("fates", ()))
                ret["discarded"].update(use.get("discarded", ()))
                if "attached_same_turn" in use.get("fates", ()) and len(ret["examples"]) < 5:
                    ret["examples"].append({"seed": r["seed"], "decks": r["decks"], **use})
        if "trader_uses" in r:
            tr = s.setdefault("trader", {"uses": Counter(), "games_with_use": 0, "returned_stage": Counter(), "taken_stage": Counter(),
                                         "used_as": Counter(), "examples": []})
            tr["games_with_use"] += bool(r["trader_uses"])
            for use in r["trader_uses"]:
                tr["uses"].update({"played": 1, "returned": "returned" in use, "taken": "taken" in use, "took_back": use.get("took_back", False),
                                   "shuffled": use.get("shuffled", False), "used_same_turn": use.get("used_same_turn", False)})
                tr["returned_stage"][use.get("returned_stage")] += 1
                tr["taken_stage"][use.get("taken_stage")] += 1
                tr["used_as"][use.get("used_as", "not_used")] += 1
                if use.get("used_same_turn") and len(tr["examples"]) < 5:
                    tr["examples"].append({"seed": r["seed"], "decks": r["decks"], **use})
        if "breeder_uses" in r:
            br = s.setdefault("breeder", {"uses": Counter(), "games_with_use": 0, "evolutions": Counter(), "examples": []})
            br["games_with_use"] += bool(r["breeder_uses"])
            for use in r["breeder_uses"]:
                br["uses"].update({"played": 1, "evolved": "to_card" in use, "power_same_turn": use.get("powers_same_turn", 0) > 0,
                                   "attacked_same_turn": use.get("attacked_same_turn", False),
                                   "attacked_next_own_turn": use.get("attacked_next_own_turn", False),
                                   "knocked_out_by_next_own_turn": use.get("knocked_out_by_next_own_turn", False)})
                br["evolutions"][f"{use.get('from_card')}->{use.get('to_card')}"] += 1
                if len(br["examples"]) < 5:
                    br["examples"].append({"seed": r["seed"], "decks": r["decks"], **use})
        if "trainer_sequence_problems" in r:
            mixed = s.setdefault("mixed", {"games_with_both": 0, "games_with_sequence_problems": 0, "searched_gust": 0,
                                           "searched_gust_played_same_turn": 0, "examples_searched_gust": [], "checks": Counter()})
            mixed["games_with_both"] += bool(r["gust_uses"]) and bool(r["computer_uses"])
            mixed["games_with_sequence_problems"] += bool(r["trainer_sequence_problems"])
            mixed["checks"].update({k: v for k, v in r["policy"].items() if k.startswith("check_")})
            for use in r["computer_uses"]:
                if use.get("searched") == GUST:
                    mixed["searched_gust"] += 1
                    if use.get("used_same_turn"):
                        mixed["searched_gust_played_same_turn"] += 1
                        if len(mixed["examples_searched_gust"]) < 5:
                            mixed["examples_searched_gust"].append({"seed": r["seed"], "decks": r["decks"], **use})
    return json.loads(json.dumps(s))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--games", type=int, default=20, help="席ごとの局数（合計はこの 2 倍。1 以上）")
    parser.add_argument("--start", type=int, default=0, help="最初の seed")
    parser.add_argument("--max-steps", type=int, default=8000)
    parser.add_argument("--out", type=Path, help="1 局ごとの結果と集計を書き出す JSON")
    parser.add_argument("--variant", choices=VARIANTS, default="preset",
                        help="gust: ディフェンダー 3 枚を突風 3 枚に（v0.21）、computer: パソコン通信 3 枚に（v0.22）置き換えた一時的なデッキ。"
                             "mixed: ディフェンダー 4 枚を突風 2 枚・パソコン通信 2 枚に置き換えた一時的なデッキ（v0.23）。"
                             "retrieval: mixed からさらにきずぐすり 2 枚をエネルギー回収 2 枚に置き換えた一時的なデッキ（v0.23）。"
                             "trader: retrieval からさらに残りのきずぐすり 2 枚をポケモン交換おじさん 2 枚に置き換えた一時的なデッキ（v0.24）。"
                             "breeder: trader のデッキ B（フシギバナ・パラセクト）だけ、さらにマサキ 2 枚をポケモン育て屋さん 2 枚に置き換えた一時的なデッキ（v0.25）。"
                             "scyther: 第2版のデッキ A2 のコラッタ 2 枚をストライク 2 枚に、scyther_grass: 第2版のデッキ B2 のモンジャラ 2 枚を"
                             "ストライク 2 枚に置き換えた一時的なデッキ（v0.27。第2版だけに使う）")
    parser.add_argument("--deck-a", choices=preset_deck_ids(), default=DECK_A,
                        help="デッキ A の識別子（v0.26。既定は第1版。第2版は hitmonchan-dewgong-v2）")
    parser.add_argument("--deck-b", choices=preset_deck_ids(), default=DECK_B,
                        help="デッキ B の識別子（v0.26。既定は第1版。第2版は venusaur-parasect-v2）")
    args = parser.parse_args(argv)
    if args.games < 1:
        parser.error("--games は 1 以上")
    if args.deck_a == args.deck_b:
        parser.error("--deck-a と --deck-b は別のデッキにする")
    try:
        for deck_id in (args.deck_a, args.deck_b):
            deck_cards(deck_id, args.variant)
    except ValueError as error:
        parser.error(str(error))
    began = time.time()
    results = run(args.games, start=args.start, max_steps=args.max_steps, variant=args.variant, decks=(args.deck_a, args.deck_b))
    summary = summarize(results)
    summary["elapsed"] = round(time.time() - began, 1)
    if args.out:
        args.out.write_text(json.dumps({"summary": summary, "games": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    keys = ("games", "outcomes", "halt_codes", "unresolved_rejections", "wins", "end_conditions", "elapsed") + tuple(
        k for k in ("gust", "computer", "mixed", "retrieval", "trader", "breeder") if k in summary)
    print(json.dumps({k: summary[k] for k in keys}, ensure_ascii=False))
    return 0 if summary["outcomes"].get("internal_error", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

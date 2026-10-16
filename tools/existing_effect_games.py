"""v0.28・v0.29: 既存の効果の型の登録だけで加えたポケモン（v0.28 の 10 枚・v0.29 の 14 枚）と、v0.30 のエネルギーをトラッシュしてダメージを
与えるワザで加えたポケモン（5 枚）の検証用デッキの対戦（docs/existing-effect-pokemon-v0.28.md 5 章・docs/existing-effect-pokemon-v0.29.md 4.2・
docs/discard-energy-attacks-v0.30.md 6 章）。

C 段階の道具（ふだんのテストは tests/test_existing_effect_games_v0_28.py・tests/test_existing_effect_games_v0_29.py・
tests/test_discard_energy_games_v0_30.py が数局だけ走らせる）。対戦相手の AI ではなく、カードの強さ・採用価値・
釣り合いを判断する道具でもない。勝敗は、対戦が通常の終わり方をしたかの確かめにだけ使う。

使い方::

    python3 tools/existing_effect_games.py --seeds 10 --out <作業用の場所>/existing.json   # 3 組 × 2 席 × 10 seed = 60 局
    python3 tools/existing_effect_games.py --batch v0.29 --seeds 10 --out <作業用の場所>/existing29.json   # v0.29 の 3 組（60 局）
    python3 tools/existing_effect_games.py --batch v0.30 --seeds 10 --out <作業用の場所>/existing30.json   # v0.30 の 3 組（60 局）

検証用デッキ（``DECKS``。公開の固定のデッキ ``kyuura_engine.decks`` には入れない。どれも対応済みのカードと基本エネルギーだけの 60 枚）:

- ``W28``（水・無色）: ラプラス 3・ヒトデマン 3・スターミー 2・トサキント 3・アズマオウ 2・シェルダー 3・ラッキー 2、トレーナー 12（マサキ・
  ポケモンいれかえ・きずぐすり・プラスパワー・ディフェンダー・突風 2 枚ずつ）、水エネルギー 30。
- ``G28``（草・超・無色）: カイロス 4・タマタマ 4・プリン 4・スリープ 4、トレーナーは ``W28`` と同じ 12、草エネルギー 16・超エネルギー 16。
- 組（``PAIRINGS``）: ``W28`` 対 ``G28``（新しいカードどうし）・``W28`` 対 ``B2``（第2版のフシギバナ・パラセクト）・``G28`` 対 ``A2``（第2版の
  エビワラー・ジュゴン）。どれも同じ seed で、席を入れかえて 1 局ずつ（先攻・後攻は seed の偶奇）。
- v0.29（``--batch v0.29``。``PAIRINGS_V0_29``）: ``GW29``（草・水）: アーボ・ズバット・ナゾノクサ・ドガース・タケシのズバット・ニョロモ・
  カスミのトサキント 3 枚ずつ、トレーナーは ``W28`` と同じ 12、草エネルギー 16・水エネルギー 11。``LF29``（雷・闘・無色）: ビリリダマ・マチスの
  コイル・マチスのビリリダマ・ワンリキー・タケシのイシツブテ・ミニリュウ・タケシのベロリンガ 3 枚ずつ、同じトレーナー 12、雷エネルギー 14・
  闘エネルギー 13。組は ``GW29`` 対 ``LF29``・``GW29`` 対 ``B2``・``LF29`` 対 ``A2``。v0.28 のデッキに v0.29 のカードは入っていないので、
  v0.28 の組の結果は v0.28 と同じ。
- v0.30（``--batch v0.30``。``PAIRINGS_V0_30``）: ``F30``（炎）: ヒトカゲ 4・リザード 3・ガーディ（第1弾。v0.2a から）4・ウインディ 3・ブーバー 3・
  第4弾ロケット団のポニータ 4、トレーナーは ``W28`` と同じ 12、炎エネルギー 27。組は ``F30`` 対 ``B2``（第2版のフシギバナ・パラセクト）・``F30`` 対
  ``A2``（第2版のエビワラー・ジュゴン）・``F30`` 対 ``G28``。v0.28・v0.29 のデッキに v0.30 のカードは入っていないので、その組の結果は変わらない。

手順: tools/preset_deck_games.py の ``make_policy``（v0.26 から変えていない手順。決定ごとの持ち主・使用中のカードの確かめ ``check_…`` も数える）に、
v0.28・v0.29 のカード（``TARGETS``）のワザの選び方だけを重ねる（``make_policy``）。バトル場がそのカードで、元の手順がワザか番の終わりを選んだとき、払えるワザ
（この番に拒否されたワザを除く）のうち、その局でそのカードがまだ使った回数の少ないワザを選ぶ（同じなら、ダメージの目安の数字が大きいもの →
位置の小さいもの）。ダメージを与えないワザ（さいみんじゅつ・こもりうた・ちょうおんぱ・まるまる・からをとじる・じこさいせい）も使うための手順で、
強さを目指したものではない。そのほかの判断（エネルギー・進化・トレーナー・にげる・決定への答え）は元の手順のまま。

終わり方の分類は tools/preset_deck_games.py と同じ（通常の勝敗・サドンデス・既知の未解決の裁定による停止・手数の上限・想定外の拒否・内部エラー）。
原典で決められないとして拒否された操作（``UNRESOLVED_…``）のあと別の操作で続けた回数は、終わり方とは別に数える。監査（``audit``）は、
受け付けた操作の列を ``new_game`` からやり直してログが同じか・不変条件・ログの監査・書き出しの監査・トレーナーのログの並び・決定ごとの確かめ。
v0.28 のカードの動きはログだけから数える（``card_uses``。選ぶ操作を変えない）。
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
    EndTurn, IllegalActionError, Phase, ResolveDecision, UnsupportedError, UseAttack, UsePokemonPower, apply_command, check_invariants, new_game,
    preset_deck,
)
from kyuura_engine.cards import EnergyType, can_pay_cost  # noqa: E402
from kyuura_engine.decisions import ATTACH_FROM_DISCARD, DISCARD_ENERGY, SELECT_ATTACK  # noqa: E402
from kyuura_engine.persistent import attack_barrier, cannot_attack, destiny_bond  # noqa: E402
from tests.log_audit import log_problems, serialization_problems  # noqa: E402
from tests.v017_games import play_game  # noqa: E402
from tools import preset_deck_games as driver  # noqa: E402

LAPRAS, STARMIE, GOLDEEN, SEAKING, PINSIR = "PMCG3-022", "PMCG1-026", "PMCG2-021", "PMCG2-022", "PMCG2-018"
EXEGGCUTE, JIGGLYPUFF, CHANSEY, DROWZEE, SHELLDER = "PMCG2-006", "PMCG2-035", "PMCG1-068", "PMCG1-045", "PMCG3-012"
V0_28 = (LAPRAS, STARMIE, GOLDEEN, SEAKING, PINSIR, EXEGGCUTE, JIGGLYPUFF, CHANSEY, DROWZEE, SHELLDER)
# v0.29（kyuura データの採用。どれもたねポケモン）
POLIWAG, ROCKET_EKANS, ROCKET_ZUBAT, ROCKET_ODDISH, ROCKET_KOFFING = "PMCG1-024", "PMCG4-001", "PMCG4-002", "PMCG4-003", "PMCG4-005"
ROCKET_VOLTORB, ROCKET_MACHOP, ROCKET_DRATINI, BROCKS_ZUBAT, MISTYS_GOLDEEN = "PMCG4-027", "PMCG4-040", "PMCG4-051", "PMCG5-001", "PMCG5-026"
LT_SURGES_MAGNEMITE, LT_SURGES_VOLTORB, BROCKS_GEODUDE, BROCKS_LICKITUNG = "PMCG5-037", "PMCG5-038", "PMCG5-046", "PMCG5-061"
V0_29 = (POLIWAG, ROCKET_EKANS, ROCKET_ZUBAT, ROCKET_ODDISH, ROCKET_KOFFING, ROCKET_VOLTORB, ROCKET_MACHOP, ROCKET_DRATINI, BROCKS_ZUBAT,
         MISTYS_GOLDEEN, LT_SURGES_MAGNEMITE, LT_SURGES_VOLTORB, BROCKS_GEODUDE, BROCKS_LICKITUNG)
# v0.30（エネルギーをトラッシュしてダメージを与えるワザ。リザードはヒトカゲから、ウインディはガーディから進化）
CHARMANDER, CHARMELEON, ARCANINE, MAGMAR, ROCKET_PONYTA = "PMCG1-014", "PMCG1-017", "PMCG1-019", "PMCG1-020", "PMCG4-013"
V0_30 = (CHARMANDER, CHARMELEON, ARCANINE, MAGMAR, ROCKET_PONYTA)
GROWLITHE = "PMCG1-018"
# v0.31（v0.30 で保留した 22 枚と、進化元として加えた 7 枚。docs/held-cards-v0.31.md）
NINETALES, CHARIZARD, ZAPDOS, GASTLY1, MEWTWO, CLEFABLE = "PMCG1-022", "PMCG1-021", "PMCG1-042", "PMCG1-044", "PMCG1-050", "PMCG2-044"
MOLTRES, SLOWPOKE, DARK_RAPIDASH, DARK_CHARMELEON, DARK_FLAREON, DARK_CHARIZARD = "PMCG3-009", "PMCG3-027", "PMCG4-014", "PMCG4-015", "PMCG4-016", "PMCG4-017"
DARK_GOLDUCK, DARK_ELECTRODE, MISTYS_GOLDUCK, LT_SURGES_ELECTABUZZ = "PMCG4-022", "PMCG4-028", "PMCG5-032", "PMCG5-041"
BLAINES_CHARMANDER, BLAINES_CHARMELEON, BLAINES_MAGMAR, BLAINES_NINETALES, BLAINES_ARCANINE = "PMCG6-025", "PMCG6-029", "PMCG6-031", "PMCG6-033", "PMCG6-034"
LT_SURGES_RAICHU = "PMCG6-041"
V0_31_TARGETS = (NINETALES, CHARIZARD, ZAPDOS, GASTLY1, MEWTWO, CLEFABLE, MOLTRES, SLOWPOKE, DARK_RAPIDASH, DARK_CHARMELEON, DARK_FLAREON,
                 DARK_CHARIZARD, DARK_GOLDUCK, DARK_ELECTRODE, MISTYS_GOLDUCK, LT_SURGES_ELECTABUZZ, BLAINES_CHARMANDER, BLAINES_CHARMELEON,
                 BLAINES_MAGMAR, BLAINES_NINETALES, BLAINES_ARCANINE, LT_SURGES_RAICHU)
CLEFAIRY, EEVEE, PSYDUCK, MISTYS_PSYDUCK, BLAINES_VULPIX, BLAINES_GROWLITHE, LT_SURGES_PIKACHU = (
    "PMCG1-067", "PMCG2-037", "PMCG4-019", "PMCG5-021", "PMCG6-026", "PMCG6-027", "PMCG5-036")
V0_31_DEPENDENCIES = (CLEFAIRY, EEVEE, PSYDUCK, MISTYS_PSYDUCK, BLAINES_VULPIX, BLAINES_GROWLITHE, LT_SURGES_PIKACHU)
V0_31 = V0_31_TARGETS + V0_31_DEPENDENCIES
VULPIX = "PMCG1-015"
TARGETS = V0_28 + V0_29 + V0_30 + V0_31  # ワザの選び方を重ね、動きを数えるカード
STARYU = "PMCG1-025"
GRASS, FIRE, WATER, LIGHTNING, PSYCHIC, FIGHTING = "PMCG1-097", "PMCG1-098", "PMCG1-099", "PMCG1-100", "PMCG1-101", "PMCG1-102"
SWITCH = "PMCG1-073"
TRAINERS = ((driver.BILL, 2), (SWITCH, 2), (driver.POTION, 2), (driver.PLUSPOWER, 2), (driver.DEFENDER, 2), (driver.GUST, 2))
# 検証用デッキ（(カード id, 枚数) の並び）。第2版の固定のデッキはそのまま使う
DECKS = {
    "W28": ((LAPRAS, 3), (STARYU, 3), (STARMIE, 2), (GOLDEEN, 3), (SEAKING, 2), (SHELLDER, 3), (CHANSEY, 2), *TRAINERS, (WATER, 30)),
    "G28": ((PINSIR, 4), (EXEGGCUTE, 4), (JIGGLYPUFF, 4), (DROWZEE, 4), *TRAINERS, (GRASS, 16), (PSYCHIC, 16)),
    "GW29": ((ROCKET_EKANS, 3), (ROCKET_ZUBAT, 3), (ROCKET_ODDISH, 3), (ROCKET_KOFFING, 3), (BROCKS_ZUBAT, 3), (POLIWAG, 3), (MISTYS_GOLDEEN, 3),
             *TRAINERS, (GRASS, 16), (WATER, 11)),
    "LF29": ((ROCKET_VOLTORB, 3), (LT_SURGES_MAGNEMITE, 3), (LT_SURGES_VOLTORB, 3), (ROCKET_MACHOP, 3), (BROCKS_GEODUDE, 3), (ROCKET_DRATINI, 3),
             (BROCKS_LICKITUNG, 3), *TRAINERS, (LIGHTNING, 14), (FIGHTING, 13)),
    "F30": ((CHARMANDER, 4), (CHARMELEON, 3), (GROWLITHE, 4), (ARCANINE, 3), (MAGMAR, 3), (ROCKET_PONYTA, 4), *TRAINERS, (FIRE, 27)),
    # v0.31: 炎（第1弾・ロケット団・化石の秘密）。リザードンのエナジーバーンのために水・超を少し入れる
    "R31": ((CHARMANDER, 4), (CHARMELEON, 2), (CHARIZARD, 2), (DARK_CHARMELEON, 2), (DARK_CHARIZARD, 2), (VULPIX, 3), (NINETALES, 2),
            (ROCKET_PONYTA, 3), (DARK_RAPIDASH, 2), (EEVEE, 3), (DARK_FLAREON, 2), (MOLTRES, 2), *TRAINERS, (FIRE, 17), (WATER, 2)),
    # v0.31: カツラのポケモン（闇からの挑戦）
    "K31": ((BLAINES_CHARMANDER, 4), (BLAINES_CHARMELEON, 3), (BLAINES_VULPIX, 4), (BLAINES_NINETALES, 3), (BLAINES_GROWLITHE, 4),
            (BLAINES_ARCANINE, 3), (BLAINES_MAGMAR, 3), *TRAINERS, (FIRE, 24)),
    # v0.31: 雷・超（第1弾・ロケット団・リーダーズスタジアム・闇からの挑戦）
    "E31": ((ZAPDOS, 2), (LT_SURGES_ELECTABUZZ, 3), (LT_SURGES_PIKACHU, 3), (LT_SURGES_RAICHU, 2), (ROCKET_VOLTORB, 3), (DARK_ELECTRODE, 2),
            (GASTLY1, 3), (MEWTWO, 2), *TRAINERS, (LIGHTNING, 16), (PSYCHIC, 12)),
    # v0.31: 超・水・無色（化石の秘密・ジャングル・ロケット団・リーダーズスタジアム）
    "P31": ((SLOWPOKE, 3), (CLEFAIRY, 3), (CLEFABLE, 2), (PSYDUCK, 3), (DARK_GOLDUCK, 2), (MISTYS_PSYDUCK, 3), (MISTYS_GOLDUCK, 2),
            *TRAINERS, (PSYCHIC, 15), (WATER, 15)),
}
PRESETS = {"A2": driver.DECK_A2, "B2": driver.DECK_B2}
PAIRINGS = (("W28", "G28"), ("W28", "B2"), ("G28", "A2"))
PAIRINGS_V0_29 = (("GW29", "LF29"), ("GW29", "B2"), ("LF29", "A2"))
PAIRINGS_V0_30 = (("F30", "B2"), ("F30", "A2"), ("F30", "G28"))
PAIRINGS_V0_31 = (("R31", "K31"), ("E31", "P31"), ("R31", "P31"), ("K31", "E31"))
BATCHES = {"v0.28": PAIRINGS, "v0.29": PAIRINGS_V0_29, "v0.30": PAIRINGS_V0_30, "v0.31": PAIRINGS_V0_31}
CHECK_FAILURES = ("check_decision_player_mismatch", "check_in_use_mismatch", "check_in_use_left_in_main")
# ワザの結果として数えるログ（v0.28・v0.29 のカードのワザの中に出たもの）
RESULT_EVENTS = ("special_condition", "persistent_effect_added", "discard_energy", "remove_all_damage_counters", "drain_heal",
                 "damage_prevented", "confusion_damage", "attack_evaded",
                 # v0.31
                 "discard_energy_failed", "discard_attached_energy", "attack_heal", "recover_trainer", "attach_energy_from_discard",
                 "attack_attach_energy", "discard_from_deck", "copy_attack", "attack_failed", "effect_prevented", "effect_skipped", "draw",
                 "forced_switch", "destiny_bond")


def _attacker(state, command):
    return state.players[command.player].active


def _copier(state, command):
    effect = state.effects.attack_effect(state.card_def(_attacker(state, command).card).id,
                                         state.card_def(_attacker(state, command).card).attacks[command.attack_index],
                                         state.card_def(_attacker(state, command).card).attacks)
    return type(effect).__name__ in ("CopyOpponentAttackEffect", "ThreeCoinPsychicPower")


def _defender(state, command):
    return state.players[1 - command.player].active


# v0.31: 原典で決められない場合・エンジンの未対応で止まったワザを、場から確かめる関数（tests/v017_games.py の ``extra_stop``。止まるのが正しいなら True）
V031_STOPS = {
    "UNRESOLVED_DISCARD_ENERGY_TIMING": lambda st, c: _attacker(st, c).conditions.confused,  # HC1
    "UNRESOLVED_EXTRA_ENERGY_COLORLESS": lambda st, c: st.card_def(_attacker(st, c).card).id == PSYDUCK and c.attack_index == 1,  # HC4
    "UNRESOLVED_PREVENTED_EFFECT_COIN": lambda st, c: attack_barrier(st, _defender(st, c)) is not None,  # HC3
    "UNRESOLVED_DESTINY_BOND_KNOCKOUT": lambda st, c: destiny_bond(st, _defender(st, c)) is not None,  # HC2
    "ATTACK_PREVENTED": lambda st, c: cannot_attack(st, _attacker(st, c)) is not None,  # しっぽをふる
    "UNRESOLVED_DISCARD_DECK_SHORT": lambda st, c: (  # HC6: マグマふんしゅつ（自分の山札 5 枚未満）・やまやき（相手の山札 0 枚）
        (st.card_def(_attacker(st, c).card).id, c.attack_index) == (BLAINES_MAGMAR, 1) and len(st.players[c.player].deck) < 5
        or (st.card_def(_attacker(st, c).card).id, c.attack_index) == (MOLTRES, 0) and not st.players[1 - c.player].deck),
    "NO_DAMAGE_COUNTERS": lambda st, c: st.card_def(_attacker(st, c).card).id == SLOWPOKE and _attacker(st, c).damage == 0,  # ぼーっとする
    "UNRESOLVED_COPIED_ATTACK": lambda st, c: _copier(st, c),  # HC9
    "UNSUPPORTED_COPIED_ATTACK": lambda st, c: _copier(st, c),
    # 試す結果の数が上限（4,096）を超える（れんぞくファイヤーボール・エナジーボム・ほうでん・やまやきで、ついているエネルギーが多いとき）
    "UNSUPPORTED_PREFLIGHT_LIMIT": lambda st, c: len(_attacker(st, c).energy) >= 6,
}


def deck_cards(label):
    """60 枚のカード id の並び。検証用デッキは ``DECKS`` の順、第2版は公開の固定のデッキのまま。"""
    if label in PRESETS:
        return preset_deck(PRESETS[label]).cards()
    if label not in DECKS:
        raise ValueError(f"知らないデッキ {label!r}（{sorted(DECKS) + sorted(PRESETS)}）")
    cards = [card for card, count in DECKS[label] for _ in range(count)]
    if len(cards) != 60:
        raise ValueError(f"{label} は {len(cards)} 枚")
    return cards


def _uses_so_far(state, player, card_id):
    """その局でプレイヤーが ``card_id`` のポケモンで宣言したワザの回数（ワザの位置ごと）。"""
    used = Counter()
    for e in state.log:
        if e["kind"] == "attack" and e["player"] == player and state.cards[e["pokemon"]].card_id == card_id:
            used[e["attack_index"]] += 1
    return used


def _v031_decision(state, counts):
    """v0.31 のカードのワザの決定への答え（元の手順は 1 つ目の選べるもの 1 つを選ぶので、2 枚以上を選ぶ決定・選ばなくてもよい決定に答えられない）。
    原典で決められない選択・エンジンの未対応の選択（``context`` の ``unresolved_choices``・``unsupported_choices``）は選ばない。"""
    d = state.decision
    if d is None or d.resume != "attack":
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_31:
        return None
    blocked = set(d.context_value("unresolved_choices", ())) | set(d.context_value("unsupported_choices", ()))
    options = [o for o in d.options if o not in blocked]
    if d.kind == SELECT_ATTACK:
        counts["v031_select_attack"] += 1
        return ResolveDecision(d.player, d.id, (options[counts["v031_select_attack"] % len(options)],))
    if d.kind == ATTACH_FROM_DISCARD:
        count = d.max_choices  # たいでん: つけられるだけつける（0 枚は HC7）
    elif d.kind == DISCARD_ENERGY and d.min_choices == 0:
        count = 1  # やまやき（好きなだけ。0 枚は HC5）・ひばしら（のぞむなら）: 1 枚
    else:
        count = max(d.min_choices, min(1, d.max_choices))
    counts[f"v031_decision_{d.kind}_{count}"] += 1
    return ResolveDecision(d.player, d.id, tuple(options[:count]))


def _v031_power(state, tried, counts):
    """v0.31 の宣言する特殊能力を使う手順: カツラのロコンの「しぜんになおる」（ダメージがあり、この番にまだ使っていない）・リザードンの「エナジーバーン」
    （炎でないエネルギーがついていて、その番にまだ使っていない）。使えない特殊状態のときは使わない（拒否を起こさない）。"""
    player = state.current_player
    p = state.players[player]
    for pokemon in p.in_play():
        card_id = state.card_def(pokemon.card).id
        blocked = pokemon is p.active and (pokemon.conditions.asleep or pokemon.conditions.paralyzed or pokemon.conditions.confused)
        if blocked:
            continue
        if card_id == BLAINES_VULPIX and pokemon.damage > 0 and (pokemon.pokemon_id, 0) not in state.power_uses_this_turn:
            counts["v031_power_natural_cure"] += 1
            return UsePokemonPower(player, pokemon.pokemon_id, 0)
        marker = ("energy_burn", pokemon.pokemon_id)
        if card_id == CHARIZARD and marker not in tried and any(state.energy_type_of(pokemon, u) is not EnergyType.FIRE for u in pokemon.energy):
            tried.add(marker)
            counts["v031_power_energy_burn"] += 1
            return UsePokemonPower(player, pokemon.pokemon_id, 0)
    return None


def make_policy(seen: dict, counts: Counter):
    """tools/preset_deck_games.py の手順（``checks=True``）に、v0.28〜v0.31 のカードのワザの選び方を重ねる（モジュールの説明）。v0.31 からは、
    v0.31 のカードのワザの決定への答え（``_v031_decision``）と、宣言する特殊能力の使用（``_v031_power``）も重ねる。v0.31 のカードのない局では
    何もしないので、v0.28〜v0.30 の組の結果は変わらない。"""
    base = driver.make_policy(seen, counts, checks=True)

    def policy(state, *, janken_winner, cure, tried):
        command = base(state, janken_winner=janken_winner, cure=cure, tried=tried)
        if state.phase is Phase.DECISION:
            return _v031_decision(state, counts) or command
        if state.phase is Phase.MAIN and isinstance(command, (UseAttack, EndTurn)):
            power = _v031_power(state, tried, counts)
            if power is not None:
                return power
        if state.phase is not Phase.MAIN or not isinstance(command, (UseAttack, EndTurn)) or "attack" in tried:
            return command
        player = state.current_player
        active = state.players[player].active
        card_id = state.cards[active.card].card_id
        if card_id not in TARGETS:
            return command
        attacks = state.card_def(active.card).attacks
        provided = state.energy_types(active)
        usable = [a.index for a in attacks if can_pay_cost(a.cost, provided) and ("attack_index", a.index) not in tried]
        if not usable:
            return command
        used = _uses_so_far(state, player, card_id)
        if card_id in V0_31 and all(used[i] >= 2 for i in usable) and any(used[a.index] == 0 and a.index not in usable for a in attacks):
            # v0.31: エネルギーをトラッシュするワザ（やまやき・メラメラなど）を使い続けると、エネルギーがたまらず、もう一つのワザが使えるようにならない。
            # 使えるワザをどれも 2 回以上使い、まだ使っていないワザが必要なエネルギーの不足で使えないときは、この番はワザを使わずに番を終える
            counts[f"v031_wait_{card_id}"] += 1
            return EndTurn(player)
        choice = min(usable, key=lambda i: (used[i], -(attacks[i].damage or 0), i))
        chosen = UseAttack(player, choice)
        if chosen != command:
            counts[f"coverage_choice_{card_id}#{choice}"] += 1
        return chosen

    return policy


def play(labels, seed, *, max_steps=8000, keep_state=False):
    """1 局を進め、終わり方と動きを返す（終わり方の分類は tools/preset_deck_games.py の ``play`` と同じ）。"""
    seen, counts = {}, Counter()
    decks = tuple(deck_cards(label) for label in labels)
    result = {"seed": seed, "decks": list(labels), "first": seed % 2}
    commands = []
    try:
        state, commands, observed = play_game(decks, seed, policy=make_policy(seen, counts), max_steps=max_steps, extra_stop=V031_STOPS)
        outcome = state.phase.value
        if state.phase is Phase.HALTED:
            outcome = "halted"
            result["halt_code"] = next((e["code"] for e in reversed(state.log) if e["kind"] == "halted"), None)
    except AssertionError as error:
        state, observed = seen.get("state"), Counter()
        outcome = "step_limit" if str(error) == driver.STEP_LIMIT else "internal_error"
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
            result["winner_deck"] = labels[state.result.winner] if state.result.winner is not None else None
            result["conditions"] = [c[1] for c in state.result.conditions]
        result["card_uses"] = card_uses(state)
        result["trainer_sequence_problems"] = driver.trainer_sequence_problems(state)
    result["audit"] = audit(result, state, commands)
    if keep_state:
        result["state"] = state
        result["commands"] = commands
    return result


def audit(result, state, commands):
    """監査の失敗の数（失敗がなければ空）。やり直しと監査は、終わりまで進んだ局（通常の勝敗・サドンデス・停止）だけ。"""
    failures = Counter()
    if state is None or result["outcome"] not in ("game_over", "sudden_death", "halted"):
        return {"not_audited": 1}
    current = new_game(*(deck_cards(label) for label in result["decks"]), result["seed"])
    for command in commands:
        current = apply_command(current, command)
    failures["replay_mismatch"] += [dict(e) for e in current.log] != [dict(e) for e in state.log]
    failures["invariants"] += bool(check_invariants(state))
    failures["log"] += bool(log_problems(state))
    failures["serialization"] += bool(serialization_problems(state))
    failures["trainer_sequence"] += bool(result.get("trainer_sequence_problems"))
    for key in CHECK_FAILURES:
        failures[key] += result["policy"].get(key, 0)
    return {k: v for k, v in failures.items() if v}


def card_uses(state):
    """ログから数えた v0.28〜v0.30 のカードの動き（カード id ごと）。

    - ``in_play``: 場に出した枚数（対戦準備・ベンチに出す）。``evolved_to``: そのカードに進化した回数（``evolve`` の ``to_card``）
    - ``attack#i``: ワザの宣言の回数（こんらんのコインで「うら」だったワザも数える）。``confused_failed#i``: そのうちこんらんの 20 になったもの
    - ``damage#i``: そのワザで相手に与えたダメージのログ（``damage_prevented`` は数えない）。``self_damage#i``: 自分へのダメージのログ
    - ``base#i=N``: 相手へのダメージの基本となるダメージ（p.321 の 1 段階。「みずでっぽう」の追加・コインのダメージの「おもて」の数を見る）
    - ``<ログの種類>#i``: そのワザの中に出た結果のログ（``RESULT_EVENTS``。特殊状態は ``special_condition_<状態>#i``）。v0.30 のワザの
      エネルギーのトラッシュは ``discard_energy#i``、トラッシュのあとダメージのログが続いたものは ``discard_then_damage#i``
    - ``protected_by_own_effect``: 自分のワザ（まるまる・からをとじる）の効果で、相手のワザのダメージを受けなかった回数（``damage_prevented``）。
      ``effect_removed_<理由>``: そのカードの持続する効果が消えた回数（``expired``・``retreat``・``switch``・``knock_out`` など）
    - ``knocked_out``: きぜつした回数
    - v0.31: ``energy_burn``（エナジーバーン）・``power_heal``（しぜんになおる）・``power_heal_on_attach``（ほのおでかいふく）: 特殊能力のログの数
    """
    card = {uid: c.card_id for uid, c in state.cards.items()}
    uses = {cid: Counter() for cid in TARGETS}
    current = None  # (カード id, ワザの位置)
    discarded = False
    for e in state.log:
        kind = e["kind"]
        if kind == "place_starting_pokemon":
            for uid in (e["active"], *e["bench"]):
                if card[uid] in uses:
                    uses[card[uid]]["in_play"] += 1
        elif kind == "play_to_bench" and card[e["card"]] in uses:
            uses[card[e["card"]]]["in_play"] += 1
        elif kind == "evolve" and card[e["to_card"]] in uses:
            uses[card[e["to_card"]]]["evolved_to"] += 1
        elif kind == "knock_out" and card.get(e.get("pokemon")) in uses:
            uses[card[e["pokemon"]]]["knocked_out"] += 1
        elif kind == "damage_prevented" and card[e["pokemon"]] in uses and e.get("source_card") == e["pokemon"]:
            uses[card[e["pokemon"]]]["protected_by_own_effect"] += 1  # 「まるまる」「からをとじる」の効果で、相手のワザのダメージを受けなかった
        elif kind == "persistent_effect_removed" and card[e["pokemon"]] in uses:
            uses[card[e["pokemon"]]][f"effect_removed_{e['reason']}"] += 1
        elif kind in ("energy_burn", "power_heal") and card[e["pokemon"]] in uses:
            # v0.31: 特殊能力（エナジーバーン・しぜんになおる・ほのおでかいふく（つけたカード ``trigger`` があるもの））
            uses[card[e["pokemon"]]]["power_heal_on_attach" if "trigger" in e else kind] += 1
        if kind == "attack":
            discarded = False
            current = (card[e["pokemon"]], e["attack_index"]) if card[e["pokemon"]] in uses else None
            if current is not None:
                uses[current[0]][f"attack#{current[1]}"] += 1
        elif kind in ("turn_end", "turn_start"):
            current = None
        elif current is not None:
            cid, index = current
            if kind == "confusion_damage":
                uses[cid][f"confused_failed#{index}"] += 1
            elif kind == "damage" and not e.get("retaliation") and e.get("target") == "self":
                uses[cid][f"self_damage#{index}"] += 1
            elif kind == "damage" and not e.get("retaliation") and "target" not in e:
                uses[cid][f"damage#{index}"] += 1
                uses[cid][f"base#{index}={e['steps'][0][1]}"] += 1
            elif kind == "special_condition" and e.get("effect") == f"{cid}#{index}":
                uses[cid][f"special_condition_{e['condition']}#{index}"] += 1
            elif kind in RESULT_EVENTS and kind != "special_condition":
                uses[cid][f"{kind}#{index}"] += 1
            if kind == "discard_energy":
                discarded = True
            elif discarded and ((kind == "damage" and "target" not in e and not e.get("retaliation"))
                                or (kind == "damage_prevented" and e["target"] == "opponent_active") or kind == "attack_evaded"):
                uses[cid][f"discard_then_damage#{index}"] += 1  # v0.30: トラッシュのあとに、そのワザのダメージの要素
                discarded = False
    return {cid: dict(c) for cid, c in uses.items() if c}


def summarize(games):
    """1 組（または全体）の集計。終わり方・停止のコード・``UNRESOLVED_…`` のあと続けた回数・監査の失敗・対象のカードの動きの合計と局数。"""
    s = {"games": len(games), "outcomes": Counter(r["outcome"] for r in games), "halt_codes": Counter(r["halt_code"] for r in games
                                                                                                     if r.get("halt_code")),
         "unresolved_rejections": Counter(), "audit_failures": Counter(), "end_conditions": Counter(), "wins": Counter(),
         "cards": {}, "games_with": {}}
    for r in games:
        s["unresolved_rejections"].update(r["unresolved_rejections"])
        s["audit_failures"].update(r["audit"])
        s["end_conditions"].update(r.get("conditions", []))
        if r.get("winner_deck"):
            s["wins"][r["winner_deck"]] += 1
        for cid, counts in r.get("card_uses", {}).items():
            s["cards"].setdefault(cid, Counter()).update(counts)
            s["games_with"].setdefault(cid, Counter()).update({k: 1 for k, v in counts.items() if v})
    return json.loads(json.dumps(s))


def run(seeds, *, max_steps=8000, pairings=PAIRINGS):
    results = {}
    for a, b in pairings:
        games = [play(seat, seed, max_steps=max_steps) for seat in ((a, b), (b, a)) for seed in seeds]
        results[f"{a}-{b}"] = {"games": games, "summary": summarize(games)}
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--batch", choices=sorted(BATCHES), default="v0.28", help="組の一覧（v0.28・v0.29・v0.30 のどれかの 3 組、v0.31 の 4 組）")
    parser.add_argument("--seeds", type=int, default=10, help="組ごと・席ごとの seed の数（1 組の局数はこの 2 倍。1 以上）")
    parser.add_argument("--start", type=int, default=0, help="最初の seed")
    parser.add_argument("--max-steps", type=int, default=8000)
    parser.add_argument("--out", type=Path, help="1 局ごとの記録と集計を書き出す JSON")
    args = parser.parse_args(argv)
    if args.seeds < 1:
        parser.error("--seeds は 1 以上")
    seeds = range(args.start, args.start + args.seeds)
    began = time.time()
    results = run(seeds, max_steps=args.max_steps, pairings=BATCHES[args.batch])
    total = summarize([g for v in results.values() for g in v["games"]])
    elapsed = round(time.time() - began, 1)
    if args.out:
        args.out.write_text(json.dumps({"batch": args.batch, "seeds": [args.start, args.start + args.seeds], "elapsed": elapsed, "runs": results, "total": total},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
    brief = {name: {k: v["summary"][k] for k in ("games", "outcomes", "halt_codes", "unresolved_rejections", "audit_failures")}
             for name, v in results.items()}
    print(json.dumps({"elapsed": elapsed, "runs": brief, "total_cards": total["cards"]}, ensure_ascii=False))
    bad = sum(total["outcomes"].get(k, 0) for k in ("internal_error", "unexpected_rejection", "step_limit"))
    bad += sum(total["audit_failures"].values())
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

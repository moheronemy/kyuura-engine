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
    AttachEnergy, EndTurn, IllegalActionError, Phase, PlayTrainer, ResolveDecision, UnsupportedError, UseAttack, preset_deck,
)
from kyuura_engine.cards import EnergyType  # noqa: E402
from tests.test_dark_wartortle_games_v0_13 import policy_command as base_policy  # noqa: E402
from tests.v017_games import play_game  # noqa: E402

DECK_A, DECK_B = "hitmonchan-dewgong", "venusaur-parasect"
PROFESSOR_OAK = "PMCG1-077"
GUST = "PMCG1-072"  # v0.21
COMPUTER_SEARCH = "PMCG1-090"  # v0.22
PLUSPOWER = "PMCG1-081"
DEFENDER = "PMCG1-079"
VARIANTS = ("preset", "gust", "computer")
REPLACEMENT = {"gust": GUST, "computer": COMPUTER_SEARCH}
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
    """対戦に使う 60 枚。``gust`` は固定のデッキのディフェンダー 3 枚を突風 3 枚に（v0.21）、``computer`` はパソコン通信 3 枚に（v0.22）置き換えた
    一時的なデッキ（並びの位置はそのまま。公開の固定のデッキは変えない）。"""
    cards = preset_deck(deck_id).cards()
    if variant == "preset":
        return cards
    if variant not in REPLACEMENT:
        raise ValueError(f"知らない変種 {variant!r}（{VARIANTS}）")
    for _ in range(3):
        cards[cards.index(DEFENDER)] = REPLACEMENT[variant]
    return cards


def _remaining_hp(state, pokemon):
    return state.card_def(pokemon.card).hp - pokemon.damage


def _gust_target(state, options):
    """突風で呼ぶ相手の控えポケモン（決まった手順。強さを目指したものではない）。"""
    def key(pid):
        pokemon = state.find_pokemon(pid)[1]
        return (_remaining_hp(state, pokemon), -state.card_def(pokemon.card).retreat_cost, len(pokemon.energy), options.index(pid))
    return min(options, key=key)


def _gust_command(state, player, tried, counts):
    """v0.21: 突風を使うなら、そのコマンド。1 番に 1 回だけ考える。"""
    p = state.players[player]
    gust = next((u for u in p.hand if _card(state, u) == GUST), None)
    marker = ("gust", state.turn_number)
    if gust is None or marker in tried:
        return None
    tried.add(marker)
    opponent = state.players[1 - player]
    if not opponent.bench:
        counts["gust_kept_no_opponent_bench"] += 1  # 控えがいないときに使えるかは原典で決められない（GW5）ので使わない
        return None
    target = state.find_pokemon(_gust_target(state, [b.pokemon_id for b in opponent.bench]))[1]
    if _remaining_hp(state, target) >= _remaining_hp(state, opponent.active):
        counts["gust_kept_no_better_target"] += 1
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


def make_policy(seen: dict, counts: Counter):
    """元の手順に、エネルギーのつけ方とオーキドはかせの使い方（v0.21 から突風の使い方も）を重ねる。``seen`` に最後に見た状態を残す
    （止まったときの報告のため）。"""

    def policy(state, *, janken_winner, cure, tried):
        seen["state"] = state
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


def play(deck_ids, seed, *, max_steps=8000, keep_state=False, variant="preset"):
    """1 局を進め、終わり方と動きを返す。``keep_state`` なら最後の状態を ``"state"`` に入れる（テストの監査のため。JSON にはしない）。"""
    seen, counts = {}, Counter()
    decks = tuple(deck_cards(d, variant) for d in deck_ids)
    result = {"seed": seed, "decks": list(deck_ids), "first": seed % 2}
    if variant != "preset":
        result["variant"] = variant
    commands = []
    try:
        state, commands, observed = play_game(decks, seed, policy=make_policy(seen, counts), max_steps=max_steps)
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
        if variant == "gust":
            result["gust_uses"] = gust_uses(state)
        if variant == "computer":
            result["computer_uses"] = computer_uses(state)
    if keep_state:
        result["state"] = state
        result["commands"] = commands
    return result


def run(games, *, start=0, max_steps=8000, keep_state=False, variant="preset"):
    """席を入れかえて ``games`` 局ずつ（seed は start から）。"""
    results = []
    for seat in ((DECK_A, DECK_B), (DECK_B, DECK_A)):
        for seed in range(start, start + games):
            results.append(play(seat, seed, max_steps=max_steps, keep_state=keep_state, variant=variant))
    return results


def summarize(results):
    s = {"games": len(results), "outcomes": Counter(), "halt_codes": Counter(), "unresolved_rejections": Counter(),
         "wins": Counter(), "end_conditions": Counter(), "per_deck": {DECK_A: Counter(), DECK_B: Counter()},
         "policy": Counter(), "games_with": {DECK_A: Counter(), DECK_B: Counter()}}
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
    return json.loads(json.dumps(s))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--games", type=int, default=20, help="席ごとの局数（合計はこの 2 倍）")
    parser.add_argument("--start", type=int, default=0, help="最初の seed")
    parser.add_argument("--max-steps", type=int, default=8000)
    parser.add_argument("--out", type=Path, help="1 局ごとの結果と集計を書き出す JSON")
    parser.add_argument("--variant", choices=VARIANTS, default="preset",
                        help="gust: ディフェンダー 3 枚を突風 3 枚に（v0.21）、computer: パソコン通信 3 枚に（v0.22）置き換えた一時的なデッキ")
    args = parser.parse_args(argv)
    began = time.time()
    results = run(args.games, start=args.start, max_steps=args.max_steps, variant=args.variant)
    summary = summarize(results)
    summary["elapsed"] = round(time.time() - began, 1)
    if args.out:
        args.out.write_text(json.dumps({"summary": summary, "games": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    keys = ("games", "outcomes", "halt_codes", "unresolved_rejections", "wins", "end_conditions", "elapsed") + tuple(
        k for k in ("gust", "computer") if k in summary)
    print(json.dumps({k: summary[k] for k in keys}, ensure_ascii=False))
    return 0 if summary["outcomes"].get("internal_error", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

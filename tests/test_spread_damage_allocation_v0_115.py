"""v0.115（docs/spread-damage-allocation-v0.115.md）: 場・ベンチへのダメージ、対象ごとのコイン、ダメージの配分のポケモン 13 枚（ワザ 22）。ヤンヤンマ（neo2-011）・わるいライチュウ（neo2-021）・
サナギラス（neo2-036）・バンギラス（neo2-042）・ゴローン（neo3-039）・わるいエーフィ（neo4-067）・わるいサナギラス（neo4-076）・わるいバンギラス（neo4-079）・タケシのイワーク（GD1-010）・
シードラ（ES3-016）・ゴローン（ES3-029）・ゴローニャ（PR1-054）・イシツブテ（NIP1X-004）。

根拠は kyuura データの採用（kyuura ``e519b99`` の data/cards.json の日本語の印刷の文面。13 枚を指す LD-・CC-・UQ-・エラッタはなく、バンギラスは CR-UNOWN-DF-SOURCE-TYPE の関連するカード）と、
既存の規定と読み方の記録（p.309・p.320・p.321・v0.2d のコインを投げるプレイヤー・v0.35 の「おもて」の数でまとめる先読み・v0.38 の ``has_target``・v0.39 の GS1・v0.56 の控えへのコイン・
v0.60 の TS1・v0.65 の［ベンチガード］・v0.66 のESP・v0.67 の FD1・v0.89 の対象の選び方・v0.97 の［DARK df］・v0.105 の山札からの進化）。英語の欄・現代のルール・後年の裁定は持ち込まない。
公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない
（対戦は tools/existing_effect_games.py の ``--batch v0.115``）。
"""

from __future__ import annotations

import json
import pathlib
import re
import unittest
from collections import Counter
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS,
    EndTurn,
    ResolveDecision,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    ALLOCATE_DAMAGE,
    DISCARD_ENERGY,
    ESP_REDO,
    FORCED_SWITCH,
    SEARCH_DECK,
    SELECT_POKEMON,
)
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.observation import OPTION_MEANINGS, PUBLIC_EVENTS
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.preflight import MAX_BRANCHES
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import (
    MARKER_COLOR,
    CannotAttackNextOwnTurn,
    CannotUseOwnAttack,
)
from tests import helpers as H
from tests import test_variable_coins_search_attachments_v0_113 as V113
from tests.helpers import apply_kernel, build_test_state
from tests.log_audit import LATEST_FORMAT
from tests.release_catalog import cards_after, cards_before
from tests.test_coin_groups_damage_order_v0_35 import traced
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_unown_family_powers_v0_96 import TURN, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "spread-damage-allocation-v0.115.md"
COMMIT = "e519b99e2adcc6c2cd0998569ae5ee1101de6e89"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, FR, L, PS, G, F = H.WATER, H.FIRE, H.LIGHTNING, H.PSYCHIC, H.GRASS, H.FIGHTING
DARK, DCE = H.DARKNESS_ENERGY_NEO1, H.DOUBLE_COLORLESS_ENERGY
YANMA, DARK_RAICHU, PUPITAR, TYRANITAR, GRAVELER_N3 = "neo2-011", "neo2-021", "neo2-036", "neo2-042", "neo3-039"
DARK_ESPEON, DARK_PUPITAR, DARK_TYRANITAR, BROCKS_ONIX = "neo4-067", "neo4-076", "neo4-079", "GD1-010"
SEADRA_ES3, GRAVELER_ES3, GOLEM_PR1, GEODUDE_NIP = "ES3-016", "ES3-029", "PR1-054", "NIP1X-004"
V0115 = (YANMA, DARK_RAICHU, PUPITAR, TYRANITAR, GRAVELER_N3, DARK_ESPEON, DARK_PUPITAR, DARK_TYRANITAR, BROCKS_ONIX, SEADRA_ES3, GRAVELER_ES3, GOLEM_PR1,
         GEODUDE_NIP)
LARVITAR, DARK_LARVITAR, GEODUDE_N3, EEVEE, HORSEA_ES3 = "neo2-034", "neo4-073", "neo3-037", "PMCG2-037", "ES3-015"
UNOWN_D, MEW_SHIELD = "neo2-025", "PR1-005"
BELOW = {DARK_RAICHU: [H.PIKACHU], PUPITAR: [LARVITAR], TYRANITAR: [LARVITAR, PUPITAR], GRAVELER_N3: [GEODUDE_N3], DARK_ESPEON: [EEVEE],
         DARK_PUPITAR: [DARK_LARVITAR], DARK_TYRANITAR: [DARK_LARVITAR, DARK_PUPITAR], SEADRA_ES3: [HORSEA_ES3], GRAVELER_ES3: [GEODUDE_N3],
         GOLEM_PR1: [GEODUDE_N3, GRAVELER_ES3], H.BROCKS_RHYDON: [H.BROCKS_RHYHORN], H.HAUNTER: [H.GASTLY], H.BUZZAP_ELECTRODE: [H.VOLTORB],
         H.CLEFABLE: [H.CLEFAIRY], V113.ALAKAZAM: V113.BELOW[V113.ALAKAZAM]}
EXPECTED = {
    (YANMA, 0): E.CoinSpreadDamageThenOpponentSwitch(10), (YANMA, 1): E.DamageIgnoringDefenderEffects(),
    (DARK_RAICHU, 0): E.DamageThenChainedCoinsBenchDamage(20, 10),
    (PUPITAR, 0): E.DAMAGE_ONLY, (PUPITAR, 1): E.SpreadDamageExceptType(EnergyType.FIGHTING, 10),
    (TYRANITAR, 0): E.CoinFlipDamage(2, 30), (TYRANITAR, 1): E.DamageThenCoinPerBothBenches(30),
    (GRAVELER_N3, 0): E.DamageAndOwnBenchDamage(10), (GRAVELER_N3, 1): E.DamageIgnoringResistance(),
    (DARK_ESPEON, 0): E.CoinBonusDamage(10), (DARK_ESPEON, 1): E.EnergyCardsSpreadDamage(10),
    (DARK_PUPITAR, 0): E.DamageAndSelfDamageThenLockSelf(10), (DARK_PUPITAR, 1): E.CoinSpreadDamageThenEvolveNamedFromDeck(10, "わるいバンギラス", "わるいサナギラス"),
    (DARK_TYRANITAR, 0): E.CoinsPerOwnEnergyCardsDamageThenMillOpponent(EnergyType.FIGHTING, 20), (DARK_TYRANITAR, 1): E.ReducedDamageThenChosenBenchDamage(30, 30),
    (BROCKS_ONIX, 0): E.ParalyzeOnHeads(), (BROCKS_ONIX, 1): E.ChosenBenchTargetsThenSelfCannotAttack(2, 20),
    (SEADRA_ES3, 0): E.DamageThenAllocateExtraEnergyToBench(EnergyType.WATER, 10, 2),
    (GRAVELER_ES3, 0): E.DamageThenCoinsAllocateToBench(2, 10),
    (GOLEM_PR1, 0): E.DAMAGE_ONLY, (GOLEM_PR1, 1): E.DiscardEnergyUpToThenAllocateToOpponentPokemon(EnergyType.FIGHTING, 5, 20),
    (GEODUDE_NIP, 0): E.DamageThenChosenOpponentPokemonDamage(10),
}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, *, bench=(H.RATTATA,), opponent=None, opponent_bench=(H.RATTATA,), hand=(), opponent_hand=(), deck=None, discard=(), opponent_deck=None, current=0,
          turn=TURN):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": list(deck if deck is not None else [W] * 10), "discard": list(discard), "prizes": 6}
    them = {"active": opponent or mon(H.RATTATA), "bench": list(opponent_bench), "hand": list(opponent_hand),
            "deck": list(opponent_deck if opponent_deck is not None else [W] * 10), "discard": [], "prizes": 6}
    return build_test_state([me, them], turn_number=turn, current_player=current)


def esp_board(provider, energy, *, opponent=None, extra_bench=(), opponent_bench=(H.RATTATA,)):
    """ナツメのフーディン（バトル場。``energy``）のベンチに、超の色マーカーをのせた ``provider``（［サイコリンク］でワザを供給する「超」ポケモン）を置き、手札のナツメのESPを通常の操作で
    フーディンにつけた盤面（v0.113 の ``esp_board`` と同じ手順。進化したポケモンの重なりはこのモジュールの ``mon``）。"""
    from kyuura_engine import PlayTrainer

    state = board(mon(V113.ALAKAZAM, energy),
                  bench=(mon(provider, markers=[(MARKER_COLOR, EnergyType.PSYCHIC)]), *extra_bench), opponent=opponent or mon(H.HITMONCHAN),
                  opponent_bench=opponent_bench, hand=(V113.ESP_CARD,))
    played = apply_kernel(state, PlayTrainer(0, V113.uid(state, V113.ESP_CARD)))
    return answer(played, (played.players[0].active.pokemon_id,))


attack, answer, same_answers, flips, bases, pid = V113.attack, V113.answer, V113.same_answers, V113.flips, V113.bases, V113.pid


def damages(before, after):
    """そのワザのダメージのログ（受けるポケモンの番号（バトル場は ``pokemon`` の uid から）・受けるものの種類・基本となるダメージ・のせた量）。"""
    found = []
    for e in new_events(before, after, "damage"):
        receiver = e.get("pokemon_id")
        if receiver is None:
            receiver = next((p.pokemon_id for side in after.players for p in side.in_play() if p.card == e["pokemon"]),
                            next((p.pokemon_id for side in before.players for p in side.in_play() if p.card == e["pokemon"]), None))
        found.append((receiver, e.get("target", "opponent_active"), dict(e["steps"]).get("1 基本となる計算"), e["amount"]))
    return found


def bench_ids(state, player):
    return [p.pokemon_id for p in state.players[player].bench]


def preflight_branches(state, command, mode="derived_full"):
    """先読みが試した結果の数（``PreflightResult.branches``。色マーカーのある盤面も書き出さずに数える。v0.35 の ``traced`` は形式 10 で比べるので使わない）。"""
    from kyuura_engine.engine import apply_command_traced
    from kyuura_engine.resolution.events import PreflightResult

    _, trace = apply_command_traced(state, command, preflight=mode)
    return [r.branches for r in trace.of(PreflightResult)]


# ---------------------------------------------------------------- 1〜3 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_pool_and_registrations(self):
        extract = read_extract()
        self.assertEqual(tuple(extract["pool_v0_115"]), V0115)
        self.assertEqual(cards_after(extract, "0.114"), set(V0115))
        self.assertTrue(set(V0115).isdisjoint(cards_before(extract, "0.115")))
        pool = load_card_pool()
        self.assertEqual({c for c in V0115 if not pool.get(c).supported}, set())
        registered = {(key.card_id, key.attack_index): DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect
                      for key in DEFAULT_EFFECTS.attack_keys() if key.card_id in V0115}
        self.assertEqual(registered, EXPECTED)
        self.assertEqual({key.card_id for key in DEFAULT_EFFECTS.power_keys()} & set(V0115), set())  # 特殊能力の追加はない
        for (card, index), effect in EXPECTED.items():
            attack_ = pool.get(card).attacks[index]
            entry = DEFAULT_EFFECTS.attack_entry(card, index)
            with self.subTest(card=card, index=index):
                self.assertEqual(effect.check(attack_), [])
                self.assertEqual(DEFAULT_EFFECTS.attack_problem(card, attack_, pool.get(card).attacks), None)
                if attack_.text_ja is None:
                    self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (None, None, None))  # 説明文のないワザは出典を作らない
                else:
                    self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (attack_.text_ja, attack_.text_ja, "kyuura data/cards.json"))

    def test_card_data_as_copied(self):
        """段階・進化元・タイプは写しのまま（わるいバンギラスは闘、バンギラスは悪。「わるい」の名前でタイプを決めない）。欠けているレベル・図鑑番号は補わない。"""
        pool = load_card_pool()
        self.assertEqual({c: (pool.get(c).stage, pool.get(c).evolves_from, pool.get(c).pokemon_type) for c in (TYRANITAR, DARK_TYRANITAR, DARK_PUPITAR, GOLEM_PR1)},
                         {TYRANITAR: ("stage2", "サナギラス", EnergyType.DARKNESS), DARK_TYRANITAR: ("stage2", "わるいサナギラス", EnergyType.FIGHTING),
                          DARK_PUPITAR: ("stage1", "ヨーギラス", EnergyType.FIGHTING), GOLEM_PR1: ("stage2", "ゴローン", EnergyType.FIGHTING)})
        extract = {c["id"]: c for c in read_extract()["cards"]}
        self.assertEqual({c: extract[c]["data_gaps"] for c in V0115 if extract[c]["data_gaps"]},
                         {BROCKS_ONIX: ["jp_print.level"], SEADRA_ES3: ["pokemon.dex", "jp_print.level"], GRAVELER_ES3: ["pokemon.dex", "jp_print.level"],
                          GOLEM_PR1: ["pokemon.dex", "jp_print.level"], GEODUDE_NIP: ["pokemon.dex", "jp_print.level"]})
        sources = Counter(extract[c]["ja_text_source"].split("/")[2] for c in V0115)
        self.assertEqual(sources, {"nazonobasho.com": 4, "wiki.pokemonwiki.com": 4, "pcg-search.com": 5})

    def test_texts_accepted_exactly(self):
        """がんせきおとしの書き方は全文 1 通りだけを加えた（ほかの言い換えは受け付けない）。がんせきくだきは写しの「抵抗カ」の書き方だけを受け付ける（写しを直さない）。しめつけるは
        既存の ParalyzeOnHeads（形の確かめだけ）なので、全文がマヒの印刷の文面と同じことを、ここで別に確かめる。"""
        import dataclasses

        pool = load_card_pool()
        rock_fall = pool.get(GRAVELER_N3).attacks[1]
        self.assertEqual(rock_fall.text_ja, E.ROCK_FALL_RESISTANCE_TEXT)
        for other in ("このワザは、相手の「弱点・抵抗力」に関係なく、ダメージを与える。", "このワザは、「抵抗力」に関係なく、ダメージを与える。"):
            self.assertTrue(E.DamageIgnoringResistance().check(dataclasses.replace(rock_fall, text_ja=other)))
        smash = pool.get(GRAVELER_ES3).attacks[0]
        self.assertIn("「弱点・抵抗カ」", smash.text_ja)
        self.assertTrue(E.DamageThenCoinsAllocateToBench(2, 10).check(dataclasses.replace(smash, text_ja=smash.text_ja.replace("抵抗カ", "抵抗力"))))
        bind = pool.get(BROCKS_ONIX).attacks[0]
        self.assertEqual((bind.text_ja, bind.damage), (E.PARALYZE_HEADS_TEXT, 20))

    def test_adoption_records_and_research_links(self):
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        for card in V0115:
            record = sources[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["recorded_on"], record["external_checks"], record["issues"]),
                                 ("kyuura_data", "adopted", COMMIT, "2026-10-28", [], []))
                self.assertEqual(record["kyuura_records"], ["CR-UNOWN-DF-SOURCE-TYPE"] if card == TYRANITAR else [])
        self.assertEqual(sum(len(sources[c]["play_text"]) for c in V0115), 20)
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        printed = set(links["latest_descriptions"]["adopted_printed_text"])
        self.assertEqual({t for t in printed if t.split("/")[0] in V0115}, {f"{c}/{t}" for c in V0115 for t in sources[c]["play_text"]})
        for code, ruling in (("UNRESOLVED_DISCARD_UP_TO_ZERO", "RKB1"), ("UNRESOLVED_CHOSEN_ACTIVE_EXTRA_DAMAGE", "SLD1")):
            entry = links["stop_codes"][code]
            self.assertEqual((entry["engine_rulings"][0]["ruling_id"], entry["kyuura_disposition"]), (ruling, "not_in_kyuura"))
        applied = next(r for r in links["applied_rule_records"] if r["kyuura_record"] == "CR-UNOWN-DF-SOURCE-TYPE")
        self.assertEqual((applied["kind"], applied["kyuura_status"], applied["engine"][0]["ruling_id"]), ("ruling", "SUPPORTED", "SA-R1"))


# ---------------------------------------------------------------- 4.1 節: 複数の対象へのダメージ


class ShockWaveTest(unittest.TestCase):
    """しょうげきは: 1 枚のコイン。「おもて」なら相手の場の全員に弱点・抵抗力に関係なく 10 → 相手が選ぶ控えと入れ替え。「うら」なら入れ替えもない。"""

    def test_heads_damages_everyone_then_opponent_switches(self):
        state = board(mon(YANMA, (G,)), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA, H.PIKACHU))
        asked = attack(state, 0, HD)
        self.assertEqual(sorted(r for r, *_ in damages(state, asked)), sorted([state.players[1].active.pokemon_id, *bench_ids(state, 1)]))
        self.assertTrue(all(base == 10 for _, _, base, _ in damages(state, asked)))
        self.assertTrue(all(e.get("ignore_weakness_resistance") for e in new_events(state, asked, "damage")))
        self.assertEqual((asked.decision.kind, asked.decision.player, asked.decision.options), (FORCED_SWITCH, 1, tuple(bench_ids(state, 1))))
        switched = same_answers(self, asked, (bench_ids(state, 1)[1],))
        self.assertEqual(switched.players[1].active.pokemon_id, bench_ids(state, 1)[1])
        audited(self, switched)

    def test_tails_and_no_bench(self):
        state = board(mon(YANMA, (G,)), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA,))
        tails = attack(state, 0, TL)
        self.assertEqual((damages(state, tails), new_events(state, tails, "forced_switch", "forced_switch_skipped"), tails.decision), ([], [], None))
        lonely = board(mon(YANMA, (G,)), opponent=mon(H.CHANSEY), opponent_bench=())
        heads = attack(lonely, 0, HD)
        self.assertEqual([r for r, *_ in damages(lonely, heads)], [lonely.players[1].active.pokemon_id])
        self.assertEqual([e["reason"] for e in new_events(lonely, heads, "forced_switch_skipped")], [E.NO_BENCH])

    def test_knocked_out_active_is_not_switched(self):
        """相手の対戦ポケモンがこのダメージで HP 以上なら入れ替えない（p.309。v0.4d と同じ）。「その後」はダメージを与えたことを条件にしない（Z23 の文面ではない）。"""
        state = board(mon(YANMA, (G,)), opponent=mon(H.RATTATA, damage=30), opponent_bench=(H.RATTATA,))
        heads = attack(state, 0, HD)
        self.assertEqual([e["reason"] for e in new_events(state, heads, "forced_switch_skipped")], [E.TARGET_KNOCKED_OUT])


class SandstormTest(unittest.TestCase):
    """すなあらし: おたがいの場の、今のタイプが「闘」でないポケモン全員に 10（バトル場・控え・使い手自身も）。"""

    def test_type_filter_on_both_sides(self):
        state = board(mon(PUPITAR, (F, F)), bench=(H.RATTATA, H.MACHOP), opponent=mon(H.HITMONCHAN), opponent_bench=(H.RATTATA, H.MACHOP))
        after = attack(state, 1)
        rattatas = {pid(state, H.RATTATA, 0), pid(state, H.RATTATA, 1)}
        self.assertEqual({r for r, *_ in damages(state, after)}, rattatas)  # 闘のサナギラス・エビワラー・ワンリキーは受けない
        self.assertEqual({(t, b) for _, t, b, _ in damages(state, after)}, {("opponent_bench", 10), ("self_bench", 10)})
        audited(self, after)

    def test_attacker_itself_when_not_fighting(self):
        """色マーカーで超になったサナギラス自身も受ける（ワザによる自分へのダメージ）。相手の対戦ポケモンが闘でなければ受ける。"""
        state = board(mon(PUPITAR, (F, F), markers=[(MARKER_COLOR, EnergyType.PSYCHIC)]), bench=(), opponent=mon(H.RATTATA), opponent_bench=())
        after = attack(state, 1)
        self.assertEqual(sorted(t for _, t, _, _ in damages(state, after)), ["opponent_active", "self"])

    def test_face_down_card_type_is_not_read(self):
        """うらのカード（マチスの秘策）のタイプは読めない（FD1。おもてにしない）。"""
        from tests.test_counts_coins_compositions_v0_106 import placed_face_down

        theirs = board(mon(PUPITAR, (F, F)), bench=(), opponent=mon(H.HITMONCHAN), opponent_bench=(), opponent_hand=(H.LT_SURGES_SECRET_PLAN, H.RATTATA), current=1,
                       turn=TURN - 1)
        placed = placed_face_down(theirs, H.RATTATA, player=1)
        state = apply_kernel(placed, EndTurn(1))
        self.assertEqual(len(state.face_down_cards), 1)
        rejects(self, state, UseAttack(0, 1), "UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY")


class PsychoSplashTest(unittest.TestCase):
    """サイコスプラッシュ: 相手の場のエネルギーカードをつけているポケモン全員に、その個体のカードの枚数 × 10（エネルギーの個数ではない）。"""

    def test_each_receiver_counts_its_own_cards(self):
        state = board(mon(DARK_ESPEON, (PS, W, W)), opponent=mon(H.RATTATA, (W, DCE)),
                      opponent_bench=(mon(H.PIKACHU, (L,)), H.RATTATA, mon(H.MACHOP, (F, F, F))))
        after = attack(state, 1)
        found = {r: (t, b) for r, t, b, _ in damages(state, after)}
        ids = bench_ids(state, 1)
        self.assertEqual(found, {state.players[1].active.pokemon_id: ("opponent_active", 20), ids[0]: ("opponent_bench", 10), ids[2]: ("opponent_bench", 30)})
        self.assertNotIn(ids[1], found)  # 0 枚のポケモンは説明の対象ではない
        audited(self, after)

    def test_buzzap_card_counts_as_one_card(self):
        """相手の［エネエネ］でエネルギーとしてついたマルマインのカード（エネルギー 2 個ぶん）も 1 枚（相手の番に通常の操作で使い、番を終えてから、自分の番にサイコスプラッシュ）。"""
        from kyuura_engine.effects import COLORS

        state = board(mon(DARK_ESPEON, (PS, W, W)), bench=(), opponent=mon(H.HITMONCHAN, (F,)), opponent_bench=(mon(H.BUZZAP_ELECTRODE), H.RATTATA),
                      current=1, turn=TURN - 1)
        electrode = next(p for p in state.players[1].bench if state.cards[p.card].card_id == H.BUZZAP_ELECTRODE)
        declared = apply_kernel(state, UsePokemonPower(1, electrode.pokemon_id, 0))
        colored = answer(declared, (state.players[1].active.pokemon_id,))
        converted = answer(colored, (COLORS.index(EnergyType.FIGHTING),))
        taken = answer(converted, (0,))  # 自分がサイドを取る（マルマインは「きぜつ」した）
        mine = apply_kernel(taken, EndTurn(1))
        hitmonchan = mine.players[1].active
        self.assertEqual((len(hitmonchan.energy), E.attached_energy_cards(mine, hitmonchan)), (2, 2))
        self.assertEqual(E.energy_unit_count(mine, hitmonchan.energy, hitmonchan), 3)  # エネルギーは 3 個（エネルギーの個数ではなくカードの枚数で数える）
        after = attack(mine, 1)
        self.assertEqual([(t, b) for _, t, b, _ in damages(mine, after)], [("opponent_active", 20)])


class MountainSmashTest(unittest.TestCase):
    """やまくだき: 闘エネルギーカードの枚数ぶんのコイン → 20H → 相手の山札の上から H 枚（同じ H）。"""

    def test_cards_not_units_and_same_heads(self):
        state = board(mon(DARK_TYRANITAR, (F, F, DCE, F)), opponent=mon(H.CHANSEY), opponent_deck=[W] * 6)
        after = attack(state, 0, HD, TL, HD)
        self.assertEqual(flips(state, after), ["heads", "tails", "heads"])  # 無色2個エネルギーは闘エネルギーカードではない
        self.assertEqual(bases(state, after), [40])
        milled = [e for e in new_events(state, after, "discard_from_deck") if e["player"] == 1]
        self.assertEqual([len(e["cards"]) for e in milled], [2])  # 同じ「おもて」の数 2（そのあと相手は番の始めに 1 枚引く）

    def test_damage_prevented_still_mills(self):
        """ダメージが無効（かたまる）でも山札のトラッシュは残る（コインを投げる）。HP を超えるからといって H を小さくしない。"""
        state = board(mon(DARK_TYRANITAR, (F, F)), opponent=mon(H.CHANSEY, prevent_damage=TURN - 1), opponent_deck=[W] * 6)
        after = attack(state, 0, HD, HD)
        self.assertEqual((new_events(state, after, "damage"), len(new_events(state, after, "damage_prevented"))), ([], 1))
        self.assertEqual([len(e["cards"]) for e in new_events(state, after, "discard_from_deck") if e["player"] == 1], [2])
        weak = board(mon(DARK_TYRANITAR, (F, F)), opponent=mon(H.RATTATA, damage=30), opponent_deck=[W] * 6)
        knocked = attack(weak, 0, HD, HD)
        self.assertEqual((bases(weak, knocked), [len(e["cards"]) for e in new_events(weak, knocked, "discard_from_deck") if e["player"] == 1]), ([40], [2]))

    def test_short_deck(self):
        """0 枚（闘エネルギーカードのない使い手。相手のワザとして使ったとき）は CopiedUseTest。"""
        short = board(mon(DARK_TYRANITAR, (F, F, F)), opponent=mon(H.CHANSEY), opponent_deck=[W] * 2)
        rejects(self, short, UseAttack(0, 0), "UNRESOLVED_DISCARD_DECK_SHORT")  # HC6（「おもて」3 枚のとき足りない。先読みが宣言の前に見つける）


class HurlTest(unittest.TestCase):
    """ぶんなげる: 相手に控えがいれば 30 と選んだ控え 1 匹にも 30（50 + 30 ではない）。いなければ 50。"""

    def test_with_and_without_bench(self):
        state = board(mon(DARK_TYRANITAR, (F, F, F, W)), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA, H.PIKACHU))
        asked = attack(state, 1)
        self.assertEqual((bases(state, asked), asked.decision.kind, asked.decision.options), ([30], SELECT_POKEMON, tuple(bench_ids(state, 1))))
        picked = same_answers(self, asked, (bench_ids(state, 1)[1],))
        self.assertEqual(damages(asked, picked), [(bench_ids(state, 1)[1], "opponent_bench", 30, 30)])
        alone = board(mon(DARK_TYRANITAR, (F, F, F, W)), opponent=mon(H.CHANSEY), opponent_bench=())
        self.assertEqual(bases(alone, attack(alone, 1)), [50])


class EarthMoveTest(unittest.TestCase):
    """ちていいどう: 相手の控えから異なる最大 2 匹に各 20（0 匹は GS1）→ 次の自分の番、使ったポケモンはワザ（すべて）を使えない。"""

    def test_distinct_targets_and_full_lock(self):
        state = board(mon(BROCKS_ONIX, (F, F, F)), opponent_bench=(H.RATTATA, H.PIKACHU, H.MACHOP))
        asked = attack(state, 1)
        self.assertEqual((asked.decision.kind, asked.decision.min_choices, asked.decision.max_choices), (SELECT_POKEMON, 0, 2))
        with self.assertRaises(IllegalActionError):
            answer(asked, (bench_ids(state, 1)[0],) * 2)  # 同じポケモンを 2 回選べない（ロックブラストの重なりとは別）
        zero = rejects(self, asked, lambda s: ResolveDecision(0, s.decision.id, ()), "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE")
        self.assertIn("GS1", str(zero))
        picked = same_answers(self, asked, tuple(bench_ids(state, 1)[:2]))
        self.assertEqual([(t, b) for _, t, b, _ in damages(asked, picked)], [("opponent_bench", 20)] * 2)
        locks = [e for e in picked.players[0].active.persistent_effects]
        self.assertEqual([type(e) for e in locks], [CannotAttackNextOwnTurn])
        audited(self, picked)

    def test_without_bench_only_locks(self):
        state = board(mon(BROCKS_ONIX, (F, F, F)), opponent_bench=())
        after = attack(state, 1)
        self.assertEqual((damages(state, after), [type(e) for e in after.players[0].active.persistent_effects]), ([], [CannotAttackNextOwnTurn]))

    def test_bullet_tackle_locks_only_itself(self):
        """だんがんタックル（既存の型）は自分に 10・次の自分の番に同じワザだけ使えない（ちていいどうのすべてのワザとは別）。相手がダメージを受けなくても自分へのダメージと禁止は残る。"""
        state = board(mon(DARK_PUPITAR, (F, F)), opponent=mon(H.CHANSEY, prevent_damage=TURN - 1))
        after = attack(state, 0)
        self.assertEqual(bases(state, after, "self"), [10])
        self.assertEqual([type(e) for e in after.players[0].active.persistent_effects], [CannotUseOwnAttack])


class BindTest(unittest.TestCase):
    """しめつける（既存の ParalyzeOnHeads）: 目安 20 → コインの「おもて」でマヒ（数・状態・順番を確かめる）。"""

    def test_damage_then_coin_then_paralysis(self):
        state = board(mon(BROCKS_ONIX, (F, F)), opponent=mon(H.CHANSEY))
        heads = attack(state, 0, HD)
        kinds = [e["kind"] for e in new_events(state, heads, "damage", "coin_flip", "special_condition")]
        self.assertEqual(kinds, ["damage", "coin_flip", "special_condition"])
        self.assertEqual((bases(state, heads), type(heads.players[1].active.conditions.exclusive).__name__), ([20], "Paralyzed"))
        tails = attack(state, 0, TL)
        self.assertIsNone(tails.players[1].active.conditions.exclusive)


# ---------------------------------------------------------------- 4.2 節: 対象ごとのコイン


class MowDownTest(unittest.TestCase):
    """なぎたおす: おたがいの控え全員に相手側から 1 枚ずつ。「おもて」が出た個体に 30（面と個体の対応。HT と TH は違う）。"""

    def board(self, **extra):
        return board(mon(TYRANITAR, (DARK, DARK, W, W)), bench=(H.RATTATA, H.PIKACHU), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA, H.MACHOP), **extra)

    def test_order_and_face_to_target(self):
        state = self.board()
        theirs, ours = bench_ids(state, 1), bench_ids(state, 0)
        ht = attack(state, 1, HD, TL, TL, HD)
        th = attack(state, 1, TL, HD, HD, TL)
        result = new_events(state, ht, "pokemon_coin_results")[0]
        self.assertEqual((result["targets"], result["owners"]), (tuple(theirs + ours), (1, 1, 0, 0)))  # 相手の控え → 自分の控え
        self.assertEqual({(r, t) for r, t, _, _ in damages(state, ht) if t != "opponent_active"}, {(theirs[0], "opponent_bench"), (ours[1], "self_bench")})
        self.assertEqual({(r, t) for r, t, _, _ in damages(state, th) if t != "opponent_active"}, {(theirs[1], "opponent_bench"), (ours[0], "self_bench")})
        self.assertEqual(flips(state, ht), ["heads", "tails", "tails", "heads"])  # 投げたのはワザを使ったプレイヤー
        self.assertTrue(all(e["player"] == 0 for e in new_events(state, ht, "coin_flip")))
        audited(self, ht)

    def test_dark_df_on_both_sides(self):
        """バンギラス（悪）のダメージは、自分の控えのアンノーンD の［DARK df］でも、相手の控えのアンノーンD でも「-30」（CR-UNOWN-DF-SOURCE-TYPE）。わるいバンギラス（闘）は「悪」でない。"""
        state = board(mon(TYRANITAR, (DARK, DARK, W, W)), bench=(UNOWN_D,), opponent=mon(H.CHANSEY), opponent_bench=(UNOWN_D,))
        after = attack(state, 1, HD, HD)
        self.assertEqual(sorted((t, b, a) for _, t, b, a in damages(state, after) if t != "opponent_active"), [("opponent_bench", 30, 0), ("self_bench", 30, 0)])

    def test_bench_guard_resumes_with_the_same_faces(self):
        """相手の控えの［ベンチガード］の決定のあとも、対象と面は同じ（コインを投げ直さない・対象を変えない）。"""
        state = board(mon(TYRANITAR, (DARK, DARK, W, W)), bench=(H.RATTATA,), opponent=mon(H.CHANSEY),
                      opponent_bench=(H.RATTATA, mon(H.BROCKS_RHYDON)))
        asked = attack(state, 1, HD, TL, HD)
        self.assertEqual(asked.decision.kind, "bench_guard")
        resumed = same_answers(self, asked, ())
        self.assertEqual(flips(state, resumed), ["heads", "tails", "heads"])  # 投げ直さない
        theirs, ours = bench_ids(state, 1), bench_ids(state, 0)
        self.assertEqual(sorted((r, t, b) for r, t, b, _ in damages(asked, resumed)), sorted([(theirs[0], "opponent_bench", 30), (ours[0], "self_bench", 30)]))

    def test_bench_guard_preflight_branches(self):
        """相手の控えにタケシのサイドン（［ベンチガード］）がいると、ほかの相手の控えはそれぞれ「うら」・「おもて」で守らない・守るの 3 通り（サイドン自身は 2 通り）。相手の控え 5 匹
        （サイドン 1）・自分の控え 0 匹で 2 × 3^4 = 162。自分の控えが 5 匹なら 162 × 2^5 = 5,184 で上限を超える（UNSUPPORTED_PREFLIGHT_LIMIT。docs 5 章に実測を記録。時間がかかるので
        このテストでは数えない）。"""
        state = board(mon(TYRANITAR, (DARK, DARK, W, W)), bench=(), opponent=mon(H.CHANSEY), opponent_bench=(mon(H.BROCKS_RHYDON),) + (H.RATTATA,) * 4)
        self.assertEqual(preflight_branches(state, UseAttack(0, 1)), [162])

    def test_transparency_order_stops(self):
        """「とうめい」の控えのあとに対象がいれば TS1（受けるときのコインと本文のコインをひとまとめにしない）。"""
        state = board(mon(TYRANITAR, (DARK, DARK, W, W)), bench=(H.RATTATA,), opponent=mon(H.CHANSEY), opponent_bench=(mon(H.HAUNTER),))
        rejects(self, state, UseAttack(0, 1), "UNRESOLVED_BENCH_COIN_TRANSPARENCY_ORDER")
        last = board(mon(TYRANITAR, (DARK, DARK, W, W)), bench=(), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA, mon(H.HAUNTER)))
        self.assertEqual(len(flips(last, attack(last, 1, HD, HD, HD))), 2)

    def test_no_bench_no_coins_and_ten_targets_preflight(self):
        alone = board(mon(TYRANITAR, (DARK, DARK, W, W)), bench=(), opponent=mon(H.CHANSEY), opponent_bench=())
        self.assertEqual(flips(alone, attack(alone, 1)), [])
        full = board(mon(TYRANITAR, (DARK, DARK, W, W)), bench=(H.RATTATA,) * 5, opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA,) * 5)
        _, branches = traced(full, UseAttack(0, 1), "derived_full")
        self.assertEqual(branches, [1024])  # 10 匹の面の並びすべて（「おもて」の数でまとめない）。上限 4,096 以下


# ---------------------------------------------------------------- 4.4 節: 条件つきで続けて投げるコインとESP


class SurpriseThunderTest(unittest.TestCase):
    """びっくりサンダー: 目安 30 → T（1 枚。控えに 0）・HT（2 枚。10）・HH（2 枚。20）。"""

    def test_three_sequences(self):
        state = board(mon(DARK_RAICHU, (L, L, L)), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA, H.PIKACHU))
        for coins, amount in (((TL,), None), ((HD, TL), 10), ((HD, HD), 20)):
            with self.subTest(coins=coins):
                after = attack(state, 0, *coins)
                self.assertEqual(flips(state, after), [c.value for c in coins])
                self.assertEqual(bases(state, after), [30])
                bench = [b for _, t, b, _ in damages(state, after) if t == "opponent_bench"]
                self.assertEqual(bench, [] if amount is None else [amount, amount])
                self.assertEqual(new_events(state, after, "chained_coin_results")[0]["results"], tuple(c.value for c in coins))

    def test_no_extra_random_bits_and_three_branches(self):
        """1 枚目が「うら」なら 2 枚目を投げない（乱数を使わない）。先読みの結果は T・HT・HH の 3 つ（いつも 2 枚投げる 4 つではない）。"""
        state = board(mon(DARK_RAICHU, (L, L, L)), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA,))
        after = attack(state, 0, TL)
        self.assertEqual(len([e for e in after.log if e["kind"] == "coin_flip"]) - len([e for e in state.log if e["kind"] == "coin_flip"]), 1)
        _, branches = traced(state, UseAttack(0, 0), "derived_full")
        self.assertEqual(branches, [3])
        self.assertEqual(P.ContinueOnHeads(2).complete((HD, TL)), True)
        self.assertEqual([P.ContinueOnHeads(2).complete(s) for s in ((HD,), (TL, HD), (HD, HD, HD), ())], [False, False, False, False])

    def test_no_bench_and_all_protected(self):
        alone = board(mon(DARK_RAICHU, (L, L, L)), opponent=mon(H.CHANSEY), opponent_bench=())
        self.assertEqual((flips(alone, attack(alone, 0)), bases(alone, attack(alone, 0))), ([], [30]))
        walled = board(mon(DARK_RAICHU, (L, L, L)), opponent=mon(H.CHANSEY), opponent_bench=(mon(H.RATTATA, trainers=[(H.DEFENDER, TURN)]),))
        self.assertEqual(len(flips(walled, attack(walled, 0, HD, HD))), 2)  # 1 匹でもダメージを受けうるなら投げる（ディフェンダーは無効にしない）

    def test_esp_redo_flips_the_whole_chain_again(self):
        """ナツメのフーディンが、超の色マーカーのあるわるいライチュウのワザを［サイコリンク］で使い、通常の操作でつけたESPでやり直す。まとまりを投げ終えたあとに 1 回だけ聞き、やり直すなら
        最初から投げ直す（HT → T なら 1 枚、→ HH なら 2 枚）。相手の対戦ポケモンへの 30 はやり直さない。"""
        state = esp_board(DARK_RAICHU, (L, L, L), opponent=mon(H.CHANSEY))
        card = V113.provider_card(state, DARK_RAICHU)
        asked = attack(state, 0, HD, TL, card=card)
        self.assertEqual(asked.decision.kind, ESP_REDO)
        self.assertEqual(dict(asked.decision.context)["esp"][6], ("chain", 2))
        self.assertEqual(len(new_events(state, asked, "damage")), 1)  # 相手の対戦ポケモンへの目安のダメージはもう与えた
        for redo, coins, amount, count in (((), (), 10, 0), ((1,), (TL,), None, 1), ((1,), (HD, HD), 20, 2), ((1,), (HD, TL), 10, 2)):
            with self.subTest(redo=redo, coins=coins):
                after = same_answers(self, asked, redo, *coins)
                self.assertEqual(len(new_events(asked, after, "coin_flip")), count)
                self.assertEqual(len([e for e in new_events(asked, after, "damage") if (e.get("target") or "opponent_active") == "opponent_active"]), 0)
                bench = [b for _, t, b, _ in damages(asked, after) if t == "opponent_bench"]
                self.assertEqual(bench, [] if amount is None else [amount])
                redone = new_events(asked, after, "esp_redo")
                if redo:
                    self.assertEqual((redone[0]["original"], redone[0]["redone"]), (("heads", "tails"), tuple(c.value for c in coins)))
                audited(self, after)
        before = snap(asked)
        for player, choices in ((1, ()), (0, (2,)), (0, (1, 1))):
            with self.assertRaises(IllegalActionError):
                apply_kernel(asked, ResolveDecision(player, asked.decision.id, choices))
        self.assertEqual(snap(asked), before)

    def test_mow_down_esp_keeps_faces_on_targets_and_measured_branches(self):
        """なぎたおすのESPのやり直しは、同じ対象の並びに同じ枚数を投げ直す。先読みの分岐は 2^n ×（1 + 2^n）（やり直さない・やり直す）で、おたがいの控えが 6 匹なら上限を超える
        （UNSUPPORTED_PREFLIGHT_LIMIT。上限を増やさない。docs 5 章）。"""
        state = esp_board(TYRANITAR, (DARK, DARK, W, W), opponent=mon(H.CHANSEY))
        card = V113.provider_card(state, TYRANITAR)
        asked = attack(state, 1, HD, TL, card=card)
        self.assertEqual(asked.decision.kind, ESP_REDO)
        redone = same_answers(self, asked, (1,), TL, HD)
        result = new_events(asked, redone, "pokemon_coin_results")[0]
        self.assertEqual(result["results"], ("tails", "heads"))
        self.assertEqual({r for r, t, _, _ in damages(asked, redone) if t != "opponent_active"}, {result["targets"][1]})
        self.assertEqual(preflight_branches(state, UseAttack(0, 1, card=card)), [4 * (1 + 4)])
        many = esp_board(TYRANITAR, (DARK, DARK, W, W), opponent=mon(H.CHANSEY), extra_bench=(H.RATTATA,) * 3, opponent_bench=(H.RATTATA,) * 2)
        self.assertEqual(len(many.players[0].bench) + len(many.players[1].bench), 6)
        self.assertGreater(2 ** 6 * (1 + 2 ** 6), MAX_BRANCHES)
        rejects(self, many, UseAttack(0, 1, card=V113.provider_card(many, TYRANITAR)), "UNSUPPORTED_PREFLIGHT_LIMIT")


# ---------------------------------------------------------------- 4.3 節: 配分


class AllocationTest(unittest.TestCase):
    def test_table_sizes(self):
        self.assertEqual(len(E.damage_allocations(5, 6)), 252)
        self.assertEqual(sum(len(E.damage_allocations(n, 6)) for n in range(6)), 462)
        self.assertEqual(E.damage_allocations(2, 2), ((2, 0), (1, 1), (0, 2)))
        self.assertTrue(all(sum(row) == 5 for row in E.damage_allocations(5, 6)))
        self.assertEqual(len(set(E.damage_allocations(5, 6))), 252)

    def test_water_bomb_counts_extra_water_units(self):
        """多い「水」エネルギーの個数（2 つまで）。必要なエネルギー（水水）を除く。無色2個エネルギーは水ではない。"""
        for energy, units in (((W, W), 0), ((W, W, W), 1), ((W, W, W, W), 2), ((W, W, W, W, W), 2), ((W, W, DCE), 0)):
            state = board(mon(SEADRA_ES3, energy), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA, H.PIKACHU))
            after = attack(state, 0)
            with self.subTest(energy=energy):
                self.assertEqual(bases(state, after), [20])
                if units:
                    self.assertEqual((after.decision.kind, dict(after.decision.context)["allocation"][1]), (ALLOCATE_DAMAGE, units))
                else:
                    self.assertIsNone(after.decision)

    def test_water_bomb_concentrate_spread_and_atomic_answers(self):
        state = board(mon(SEADRA_ES3, (W, W, W, W)), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA, H.PIKACHU))
        asked = attack(state, 0)
        table = dict(asked.decision.context)["table"]
        self.assertEqual((table, asked.decision.options, OPTION_MEANINGS[ALLOCATE_DAMAGE]), (((2, 0), (1, 1), (0, 2)), (0, 1, 2), "number"))
        ids = bench_ids(state, 1)
        concentrated = same_answers(self, asked, (0,))
        self.assertEqual(damages(asked, concentrated), [(ids[0], "opponent_bench", 20, 20)])
        spread = same_answers(self, asked, (1,))
        self.assertEqual(sorted(damages(asked, spread)), sorted([(ids[0], "opponent_bench", 10, 10), (ids[1], "opponent_bench", 10, 10)]))
        self.assertEqual(new_events(asked, spread, "damage_allocated")[0]["counts"], (1, 1))
        before = snap(asked)
        for player, choices in ((1, (0,)), (0, ()), (0, (3,)), (0, (0, 1)), (0, (0, 0))):
            with self.assertRaises(IllegalActionError):
                apply_kernel(asked, ResolveDecision(player, asked.decision.id, choices))
        self.assertEqual(snap(asked), before)
        audited(self, asked)
        audited(self, spread)

    def test_rock_smash_coins_before_allocation(self):
        """がんせきくだき: 控えがいれば 2 枚（「おもて」の数でまとめる）→ 確定した「おもて」の数を配る。控えがいなければ投げない。控えがみなダメージを受けないなら v0.56 と同じ問い。"""
        state = board(mon(GRAVELER_ES3, (F, F, W)), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA, H.PIKACHU))
        asked = attack(state, 0, HD, TL)
        self.assertEqual((flips(state, asked), dict(asked.decision.context)["allocation"][1]), (["heads", "tails"], 1))
        self.assertIsNone(attack(state, 0, TL, TL).decision)
        alone = board(mon(GRAVELER_ES3, (F, F, W)), opponent=mon(H.CHANSEY), opponent_bench=())
        self.assertEqual(flips(alone, attack(alone, 0)), [])

    def test_rock_blast_repeated_choices_are_added_together(self):
        """ロックブラスト: トラッシュした N 枚ぶん、相手の場のポケモンを重ねて選べる。同じポケモンの回数は合算し、1 回だけ 20 × 回数を与える（ディフェンダーは 1 回だけ引く。
        1 回ずつ別のダメージにすると 0 になる）。"""
        state = board(mon(GOLEM_PR1, (F, F, F, F)), opponent=mon(H.CHANSEY, trainers=[(H.DEFENDER, TURN)]), opponent_bench=(H.RATTATA,))
        asked = attack(state, 1)
        self.assertEqual((asked.decision.kind, asked.decision.min_choices, asked.decision.max_choices), (DISCARD_ENERGY, 0, 4))
        discarded = answer(asked, asked.decision.options[:3])
        self.assertEqual(dict(discarded.decision.context)["allocation"], ((discarded.players[1].active.pokemon_id, *bench_ids(state, 1)), 3, 20))
        table = dict(discarded.decision.context)["table"]
        stacked = same_answers(self, discarded, (table.index((3, 0)),))
        self.assertEqual(damages(discarded, stacked), [(discarded.players[1].active.pokemon_id, "opponent_active", 60, 40)])  # 60 − 20（ディフェンダー 1 回）
        audited(self, stacked)

    def test_rock_blast_zero_and_without_cards(self):
        state = board(mon(GOLEM_PR1, (F, F, F)), opponent=mon(H.CHANSEY))
        asked = attack(state, 1)
        zero = rejects(self, asked, lambda s: ResolveDecision(0, s.decision.id, ()), P.UP_TO_DISCARD_ZERO_CODE)
        self.assertIn("RKB1", str(zero))
        rainbow = board(mon(GOLEM_PR1, (V113.RAINBOW, V113.RAINBOW, V113.RAINBOW)), opponent=mon(H.CHANSEY))
        rejects(self, rainbow, UseAttack(0, 1), "UNRESOLVED_RAINBOW_ENERGY_TYPE")  # RB1（レインボーエネルギーが「闘」エネルギーカードに当たるか）

    def test_rock_blast_preflight_branches_and_limit(self):
        """先読みは、トラッシュの枚数の組（ポケモンごと・カード id ごと）ごとに、すべての配分を試す。同じ id の闘エネルギーカード 5 枚以上・相手の場 6 匹なら 6 + 21 + 56 + 126 + 252 = 461。
        印刷の違う闘エネルギーカード（PMCG1-102・IP2-012・NIP1-006）が 3・3・2 枚なら 4,176 通りで上限 4,096 を超え、UNSUPPORTED_PREFLIGHT_LIMIT（上限を増やさない。docs 5 章）。"""
        same = board(mon(GOLEM_PR1, (F,) * 6), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA,) * 5)
        self.assertEqual(preflight_branches(same, UseAttack(0, 1)), [461])
        mixed = board(mon(GOLEM_PR1, (F, F, F, "IP2-012", "IP2-012", "IP2-012", "NIP1-006", "NIP1-006")), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA,) * 5)
        rejects(self, mixed, UseAttack(0, 1), "UNSUPPORTED_PREFLIGHT_LIMIT")

    def test_allocation_resumes_after_saving(self):
        state = board(mon(GOLEM_PR1, (F, F, F, F, F, F)), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA,) * 5)
        asked = attack(state, 1)
        discarded = answer(asked, asked.decision.options[:5])
        self.assertEqual(len(discarded.decision.options), 252)
        written = state_to_dict(discarded, format_version=26)["decision"]["context"]
        self.assertEqual(written["allocation"][1], 5)
        same_answers(self, discarded, (100,))


# ---------------------------------------------------------------- 6 章: そのほかのワザ


class ExplosiveEvolutionTest(unittest.TestCase):
    """ばくれつしんか: コインの「おもて」で相手の場の全員に 10 → 山札の「わるいバンギラス」を必ず重ねる（見たら切る）。「うら」なら山札を見ない。"""

    def test_heads_damage_then_named_evolution(self):
        state = board(mon(DARK_PUPITAR, (W, W, W)), opponent_bench=(H.RATTATA,), deck=[DARK_TYRANITAR, H.RATTATA, W, W])
        asked = attack(state, 1, HD)
        self.assertEqual(len(damages(state, asked)), 2)
        options = asked.decision.options
        self.assertEqual((asked.decision.kind, (asked.decision.min_choices, asked.decision.max_choices)), (SEARCH_DECK, (1, 1)))
        self.assertEqual({asked.cards[u].card_id for u in options}, {DARK_TYRANITAR})
        evolved = same_answers(self, asked, options[:1])
        self.assertEqual(evolved.cards[evolved.players[0].active.card].card_id, DARK_TYRANITAR)
        self.assertEqual(len(new_events(asked, evolved, "shuffle")), 1)
        audited(self, evolved)

    def test_tails_and_no_candidates(self):
        state = board(mon(DARK_PUPITAR, (W, W, W)), deck=[DARK_TYRANITAR, W])
        tails = attack(state, 1, TL)
        self.assertEqual((damages(state, tails), new_events(state, tails, "shuffle"), tails.decision), ([], [], None))
        empty = board(mon(DARK_PUPITAR, (W, W, W)), deck=[W, W])
        asked = attack(empty, 1, HD)
        self.assertEqual((asked.decision.kind, asked.decision.options, asked.decision.max_choices), (SEARCH_DECK, (), 0))  # 選べるもののない決定（A3）
        done = answer(asked, ())
        self.assertEqual(len(new_events(asked, done, "shuffle")), 1)

    def test_normal_tyranitar_is_not_a_candidate(self):
        """名前の完全一致（わるいバンギラス）。バンギラス（neo2-042）・ほかの進化カードは選べない（NB2 で広く止めない）。"""
        state = board(mon(DARK_PUPITAR, (W, W, W)), deck=[TYRANITAR, W])
        asked = attack(state, 1, HD)
        self.assertEqual(asked.decision.options, ())


class RockSlideTest(unittest.TestCase):
    """いしなだれ: 目安 10 → 相手の場のポケモンを 1 匹選び、そのポケモンにも 10。相手の対戦ポケモンは選べるが選ぶと止める（SLD1）。"""

    def test_bench_choice_and_active_question(self):
        state = board(mon(GEODUDE_NIP, (F, W)), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA,))
        asked = attack(state, 0)
        active = state.players[1].active.pokemon_id
        self.assertEqual((asked.decision.options, dict(asked.decision.context)["unresolved_choices"]), ((active, *bench_ids(state, 1)), (active,)))
        error = rejects(self, asked, lambda s: ResolveDecision(0, s.decision.id, (active,)), E.CHOSEN_ACTIVE_EXTRA_DAMAGE_CODE)
        self.assertIn("SLD1", str(error))
        picked = same_answers(self, asked, tuple(bench_ids(state, 1)))
        self.assertEqual(damages(asked, picked), [(bench_ids(state, 1)[0], "opponent_bench", 10, 10)])

    def test_no_bench_stops_before_declaration(self):
        state = board(mon(GEODUDE_NIP, (F, W)), opponent=mon(H.CHANSEY), opponent_bench=())
        rejects(self, state, UseAttack(0, 0), E.CHOSEN_ACTIVE_EXTRA_DAMAGE_CODE)


class CopiedUseTest(unittest.TestCase):
    """相手のワザとして使う（ピクシーの「ゆびをふる」。決定 ``select_attack``）: エネルギーの枚数・自分の控え・山札・禁止は、実際に使ったポケモンで決める（印刷したカードでない）。"""

    def copier(self, defender, deck=None):
        return board(mon(H.CLEFABLE, (PS, PS, PS)), bench=(H.RATTATA,), opponent=defender, opponent_bench=(H.RATTATA,), opponent_deck=[W] * 6, deck=deck)

    def test_mountain_smash_counts_the_copier_cards(self):
        """ピクシーには闘エネルギーカードがない: 0 枚のコイン・基本となるダメージ 0・相手の山札のトラッシュなし（文面にない失敗を足さない）。"""
        state = self.copier(mon(DARK_TYRANITAR, (F, F, F)))
        asked = attack(state, 0)
        self.assertEqual(asked.decision.kind, "select_attack")
        copied = answer(asked, (0,))
        self.assertEqual((flips(asked, copied), bases(asked, copied), new_events(asked, copied, "discard_from_deck", "attack_failed")), ([], [0], []))
        audited(self, copied)

    def test_explosive_evolution_has_no_candidate_for_the_copier(self):
        """ピクシーには「わるいバンギラス」を重ねられない: 「おもて」なら相手の場の全員に 10 のあと、山札を見て選べるもののない決定（A3）→ 切る。"""
        state = self.copier(mon(DARK_PUPITAR, (F,)), deck=[DARK_TYRANITAR, W, W])
        asked = attack(state, 0)
        chosen = answer(asked, (1,), HD)
        self.assertEqual(len(damages(asked, chosen)), 2)
        self.assertEqual((chosen.decision.kind, chosen.decision.options), (SEARCH_DECK, ()))
        done = answer(chosen, ())
        self.assertEqual(len(new_events(chosen, done, "shuffle")), 1)
        self.assertEqual(done.cards[done.players[0].active.card].card_id, H.CLEFABLE)

    def test_earth_move_locks_the_copier(self):
        """ちていいどうの禁止は、実際に使ったポケモン（ピクシー）に与える。"""
        state = self.copier(mon(BROCKS_ONIX, (F, F, F)))
        asked = attack(state, 0)
        chosen = answer(asked, (1,))
        picked = answer(chosen, chosen.decision.options[:1])
        self.assertEqual([type(e) for e in picked.players[0].active.persistent_effects], [CannotAttackNextOwnTurn])


class BabyAndShieldTest(unittest.TestCase):
    """ベイビィのルールのコインと本文のコインは別（ルールのコインが先・ESPのやり直しの対象ではない）。ベイビィが場にいるだけで止めない。ミュウの［ニュートラルシールド］は、相手の進化ポケモン
    （バンギラス）のワザを受けない（すなあらしの控えへのダメージも）。"""

    def test_baby_rule_coin_before_text_coin(self):
        state = board(mon(YANMA, (G,)), opponent=mon("neo1-042"), opponent_bench=(H.RATTATA,))
        after = attack(state, 0, HD, HD)
        sources = [e["source"] for e in new_events(state, after, "coin_flip")]
        self.assertEqual(sources, ["baby_rule", "attack"])

    def test_neutral_shield_stops_evolved_damage(self):
        state = board(mon(TYRANITAR, (DARK, DARK, W, W)), bench=(H.RATTATA,), opponent=mon(H.CHANSEY), opponent_bench=(mon(MEW_SHIELD),))
        after = attack(state, 1, HD, HD)
        self.assertEqual([e["persistent_effect"] for e in new_events(state, after, "damage_prevented")], ["neutral_shield"])
        # 受けうる対象がミュウだけ（自分の控えがいない）なら、コインは無効な内容だけを決める（v0.4b の問い。投げずに止める）
        only = board(mon(TYRANITAR, (DARK, DARK, W, W)), bench=(), opponent=mon(H.CHANSEY), opponent_bench=(mon(MEW_SHIELD),))
        rejects(self, only, UseAttack(0, 1), "UNRESOLVED_PREVENTED_COIN_DAMAGE")


# ---------------------------------------------------------------- 7・8 章: 保存・観測・監査


class SaveAndObservationTest(unittest.TestCase):
    def test_format_unchanged_and_public_logs(self):
        self.assertEqual((max(FORMAT_VERSIONS), LATEST_FORMAT), (26, 26))
        self.assertTrue({"chained_coin_results", "damage_allocated"} <= PUBLIC_EVENTS)
        state = board(mon(SEADRA_ES3, (W, W, W, W)), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA, H.PIKACHU))
        asked = attack(state, 0)
        written = state_to_dict(asked, format_version=26)["decision"]
        self.assertEqual(written["kind"], ALLOCATE_DAMAGE)
        audited(self, asked)

    def test_invariants_reject_a_wrong_table(self):
        from kyuura_engine.engine import check_invariants

        state = board(mon(SEADRA_ES3, (W, W, W, W)), opponent=mon(H.CHANSEY), opponent_bench=(H.RATTATA, H.PIKACHU))
        asked = attack(state, 0)
        broken = asked.clone()
        d = broken.decision
        object.__setattr__(d, "context", tuple((k, ((2, 0), (0, 2)) if k == "table" else v) for k, v in d.context))
        self.assertTrue(any("配分の表" in p for p in check_invariants(broken)))


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v115_problems``）は、エンジンの登録・計算を読まずに、処理したワザの印刷の文面と、ログから組み立てた場・コイン・カードの動き・基本となるダメージで
    確かめる。エンジンの処理を一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の局。開発用の seed 50・51。正式な対戦の seed 0〜3 とは別）で、監査がそれを見つける。"""

    GAMES = ((("W115", "T115"), 50), (("W115", "E115"), 50), (("R115", "E115"), 50), (("E115", "R115"), 50), (("D115", "R115"), 50), (("R115", "W115"), 51),
             (("W115", "R115"), 50))

    @classmethod
    def problems_for(cls, patcher, *needles):
        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        found = []
        with patcher:
            for labels, seed in cls.GAMES:
                try:
                    result = games.play(labels, seed, keep_state=True)
                except Exception as error:  # noqa: BLE001  誤らせた処理が不変条件で止まっても、監査とは別の理由（ここでは数えない）
                    found.append(f"stopped: {error}") if "stopped" in needles else None
                    continue
                if result.get("state") is not None:
                    found += [p for p in log_problems(result["state"]) if any(n in p for n in needles)]
        return found

    def test_the_unpatched_games_pass_the_audit(self):
        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        used = set()
        for labels, seed in self.GAMES:
            result = games.play(labels, seed, keep_state=True)
            with self.subTest(labels=labels, seed=seed):
                self.assertIn(result["outcome"], ("game_over", "sudden_death"))
                self.assertEqual((result["audit"], log_problems(result["state"])), ({}, []))
            used |= {k[len("attack_"):] for k, v in result["v115"].items() if k.startswith("attack_") and v}
        self.assertTrue({"neo2-042#1", "neo2-021#0", "neo4-067#1", "neo4-079#0", "ES3-016#0", "PR1-054#1", "ES3-029#0"} <= used)

    def test_audit_finds_wrong_targets_and_coins(self):
        """なぎたおすで「うら」の個体に与えた・びっくりサンダーで「うら」のあとにも投げた。"""
        original = P.CoinPerBenchPokemon.run

        def tails_targets(self, run):
            real_flip = run.flip

            def flipped(count, **kw):
                result = real_flip(count, **kw)
                return P.CoinFlips(tuple(TL if s is HD else HD for s in result.results))
            run.flip = flipped
            try:
                return original(self, run)
            finally:
                del run.flip

        self.assertTrue(self.problems_for(mock.patch.object(P.CoinPerBenchPokemon, "run", tails_targets), "対象ごとの面", "「おもて」の対象"))
        self.assertTrue(self.problems_for(mock.patch.object(P.ContinueOnHeads, "next_count", lambda self, results: 0 if len(results) >= 2 else 1),
                                          "T・HT・HH", "ESPのやり直し"))

    def test_audit_finds_wrong_counts(self):
        """サイコスプラッシュで相手の対戦ポケモンの枚数を控えに使い回した・やまくだきで「おもて」の数より 1 枚多くトラッシュした・配分の単位を 1 つ多くした・同じポケモンへの単位を
        1 回ずつ別に与えた。"""
        reuse = {E.EnergyCardsSpreadDamage: lambda e: (
            P.Damage(P.OPP, P.EnergyCardsOfReceiver(e.per), weakness_resistance=False, energy_cards=True),
            P.BenchDamage(P.DefenderEnergyCardsTimes(e.per), energy_cards=True))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, reuse), "そのポケモンのエネルギーカード"))
        original_mill = P.MillOpponentDeck.run

        def one_more(self, run):
            if self.heads_of is not None and run.heads(self.heads_of):
                coins = run.fs.coins[self.heads_of]
                run.fs.coins[self.heads_of] = P.CoinFlips(coins.results + (HD,))
                try:
                    return original_mill(self, run)
                finally:
                    run.fs.coins[self.heads_of] = coins
            return original_mill(self, run)

        self.assertTrue(self.problems_for(mock.patch.object(P.MillOpponentDeck, "run", one_more), "相手の山札の上からトラッシュした"))
        with mock.patch.object(E.DamageThenAllocateExtraEnergyToBench, "decision_problems", lambda self, state, use, decision: []), \
                mock.patch.object(E.DiscardEnergyUpToThenAllocateToOpponentPokemon, "decision_problems", lambda self, state, use, decision: []):
            self.assertTrue(self.problems_for(mock.patch.object(P.ExtraTypedUnits, "count", lambda self, run: 2), "得た単位"))
            original_resume = P.AllocateDamage.resume

            def per_unit(self, run, decision, choices):
                ids, units, per = run.carried["allocation"]
                table = tuple(tuple(row) for row in run.carried["table"])
                targets = self.candidates(run)
                entries = [(P.target_kind(run, owner, pokemon), pokemon.pokemon_id, per, False) for (owner, pokemon), count in zip(targets, table[choices[0]])
                           for _ in range(count)]
                run.state.add_event("damage_allocated", player=run.player, pokemon=run.attacker().card, pokemon_id=run.attacker().pokemon_id,
                                    effect=str(run.key), targets=tuple(ids), counts=table[choices[0]], per=per, units=units)
                P.guarded_damages(run, self, entries, record=True)

            self.assertTrue(self.problems_for(mock.patch.object(P.AllocateDamage, "resume", per_unit), "2 回以上", "単位 ×"))
            del original_resume


class DocumentTest(unittest.TestCase):
    def test_document_records(self):
        text = DOC.read_text(encoding="utf-8")
        for word in ("RKB1", "SLD1", "SA-R1", "GS1", "HC6", "TS1", "T27", "ES0", "UNSUPPORTED_PREFLIGHT_LIMIT", "ContinueOnHeads", "ALLOCATE_DAMAGE", "抵抗カ",
                     "CR-UNOWN-DF-SOURCE-TYPE", "1,276", "(101, 42, 59)", "485", "## 12. 検証", "lockstep", "単体のテストだけ", "エンジンは画像を見ていない"):
            self.assertIn(word, text)
        for card in V0115:
            self.assertIn(card, text)
        v0114 = (ROOT / "docs" / "baby-rules-evolution-v0.114.md").read_text(encoding="utf-8")
        self.assertIn("6,353 件のうち失敗 5（3 モジュール）", v0114)  # v0.114 の全体のテストの記録はそのまま
        # 題の範囲と README の「今のエンジンの版」は版を上げるたびに変わるので、v0.115 以後の範囲であることと、v0.115 の項（0.115.0）があることを確かめる
        status = (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(int(re.search(r"^# 実装状況（v0\.1〜v0\.(\d+)）", status, re.MULTILINE).group(1)), 115)
        self.assertIn("## v0.115: 場・ベンチへのダメージ、対象ごとのコイン、ダメージの配分", status)
        self.assertRegex((ROOT / "README.md").read_text(encoding="utf-8"), r"\n- v0\.115（(今のエンジンの版。)?`kyuura_engine` の版は 0\.115\.0）: 場・ベンチへのダメージ")
        self.assertIn("### v0.115: 場・ベンチへのダメージ", (ROOT / "docs" / "rules-2000-02-14.md").read_text(encoding="utf-8"))
        self.assertIn("## v0.115: 場・ベンチへのダメージ", (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

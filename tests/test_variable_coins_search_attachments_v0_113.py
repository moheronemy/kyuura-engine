"""v0.113（docs/variable-coins-search-attachments-v0.113.md）: 可変枚数のコインと、山札の検索・つける・場全体のトラッシュの 6 枚（ワザ 11）。ピッピ（neo1-063）・デンリュウ（neo3-028）・
ヤミカラス（neo3-043）・ヘルガー（neo3-044）・わるいバクフーン（neo4-022）・ロケット団のニャース（PR1-078）。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面。6 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録（GR-2000-P309-ATTACK-PROCEDURE・
GR-2000-P320-DAMAGE-FIGURE・p.323 のワザの失敗・v0.35 の「おもて」の数でまとめる先読み・v0.38 の ``has_target``・v0.39 の ``counted_pokemon``・v0.44 の FC1・v0.31 の HC5・v0.58 の RB1・RB2・
v0.66 のESP・v0.67 の FD1・v0.75 のエナジーサポート・v0.82 の場からのトラッシュ・v0.84 の A3・v0.85 のせいでんき・v0.89 のエネルギーの個数・v0.112 の ``Coin.per_own_typed``）。英語の欄・
現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、
``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.113``）。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import unittest
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import (
    EnergyType,
    load_card_pool,
    pool_from_extract,
    read_extract,
)
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    ATTACH_FROM_DECK,
    ATTACH_FROM_DISCARD,
    BENCH_FROM_DECK,
    DISCARD_ENERGY,
    ESP_REDO,
    SEARCH_DECK,
    SELECT_ATTACK,
    SELECT_POKEMON,
)
from kyuura_engine.engine import check_invariants
from kyuura_engine.errors import SECRET_PLAN_HIDDEN_CODE, IllegalActionError
from kyuura_engine.observation import observe
from kyuura_engine.persistent import add_persistent_effect
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.preflight import MAX_BRANCHES
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import MARKER_COLOR, CannotAttachEnergy
from tests import helpers as H
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.log_audit import LATEST_FORMAT
from tests.release_catalog import cards_after, cards_before
from tests.test_coin_groups_damage_order_v0_35 import traced
from tests.test_counts_coins_compositions_v0_106 import placed_face_down
from tests.test_energy_coins_draw_v0_112 import barrier_turn
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_type_energy_colors_v0_88 import convert, porygon2
from tests.test_unown_family_powers_v0_96 import TURN, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "variable-coins-search-attachments-v0.113.md"
COMMIT = "73a169063463bbf7bcaa3137d70cbf9721d11534"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, F, L, PS, G = H.WATER, H.FIRE, H.LIGHTNING, H.PSYCHIC, H.GRASS
DARK, METAL, DCE, RAINBOW = H.DARKNESS_ENERGY_NEO1, H.METAL_ENERGY_NEO1, H.DOUBLE_COLORLESS_ENERGY, H.RAINBOW_ENERGY
CLEFAIRY_N1, AMPHAROS, MURKROW, HOUNDOOM, DARK_TYPHLOSION, ROCKET_MEOWTH = "neo1-063", "neo3-028", "neo3-043", "neo3-044", "neo4-022", "PR1-078"
V0113 = (CLEFAIRY_N1, AMPHAROS, MURKROW, HOUNDOOM, DARK_TYPHLOSION, ROCKET_MEOWTH)
V0113_ATTACKS = [AttackKey(card, index) for card in V0113 for index in range(1 if card == ROCKET_MEOWTH else 2)]
MURKROW_N1 = "neo1-055"  # ほかのヤミカラスのカード（だましうち・...）
ALAKAZAM, ESP_CARD = "PMCG6-053", "PMCG6-087"  # ナツメのフーディン（［サイコリンク］）・ナツメのESP
TENTACRUEL_SI = "SI-016"
KOGAS_KOFFING = "PMCG6-015"  # キョウのドガース（くもがくれガス: ダメージを与えた後、コインで自分を山札にもどす）
CHANSEY = H.CHANSEY
BELOW = {AMPHAROS: ["neo1-038", "neo1-041"], HOUNDOOM: ["neo2-039"], DARK_TYPHLOSION: ["neo4-016", "neo4-020"], H.CLEFABLE: [H.CLEFAIRY],
         ALAKAZAM: ["PMCG6-043", "PMCG6-047"], TENTACRUEL_SI: ["PMCG3-011"], H.MACHAMP: [H.MACHOP, H.MACHOKE]}

SQUAREDANCE_TEXT = ("おたがいの場にいるポケモンの数ぶんコインを投げ、「おもて」の数以下の枚数の「基本エネルギーカード」を自分の山札から選び出し、相手プレイヤーに見せてから、手札に加える。"
                    "その後、その山札をよく切る。")
ATTRACT_TEXT = "コインを3枚投げ、「おもて」の数ぶんの「雷」エネルギーカードを自分の山札から選び出し、自分の場の「雷」ポケモンそれぞれに、好きなようにつける。その後、その山札をよく切る。"
GIGAVOLT_TEXT = "コインを投げて「おもて」なら、20ダメージを追加する。「うら」なら、相手を「マヒ」状態にする。"
CALL_TEXT = "自分の山札から「ヤミカラス」を1枚選び出し、ベンチに出す。その後、その山札をよく切る。(自分のベンチに空きがないとき、このワザは失敗する。)"
FLOCK_TEXT = "自分のベンチの「ヤミカラス」の数ぶんコインを投げ、「おもて」の数×10のダメージを追加する。"
DARK_FLAME_TEXT = ("自分についている「炎」エネルギーカードを1枚トラッシュする。その後、自分のトラッシュに「悪」エネルギーカードがあれば、1枚を選び出し、自分につける。"
                   "(トラッシュできないとき、このワザは失敗する。)")
BLACK_FANG_TEXT = "自分についている「悪」エネルギーの数ぶんコインを投げ、「おもて」の数×10のダメージを追加する。"
RUSHING_TEXT = "自分の場の「炎」エネルギーカードを、好きなだけトラッシュする。その後、トラッシュした枚数ぶんコインを投げ、「おもて」の数×40のダメージ。"
COMEBACK_TEXT = "お互いの場にいるポケモン全員の数だけコインを投げ、相手に「おもて」の数×10のダメージ。その後、自分に「うら」の数×10のダメージ。"
# 依頼で示された固定データの日本語。(タイプ, HP, 段階, 進化元, (名前, 必要なエネルギー, 目安, 説明), ...)
QUOTED = {
    CLEFAIRY_N1: ("colorless", 50, "basic", None, ("おうふくビンタ", ("colorless",) * 2, "10×", "コインを2枚投げ、「おもて」の数×10のダメージ。"),
                  ("みんなでおどる", ("colorless",) * 3, None, SQUAREDANCE_TEXT)),
    AMPHAROS: ("lightning", 90, "stage2", "モココ", ("ゆうでん", ("lightning",), "20", ATTRACT_TEXT),
               ("ギガボルト", ("lightning", "lightning", "lightning", "colorless"), "40+", GIGAVOLT_TEXT)),
    MURKROW: ("darkness", 40, "basic", None, ("なかまをよぶ", ("colorless",), None, CALL_TEXT), ("むれでつつく", ("colorless",) * 2, "10+", FLOCK_TEXT)),
    HOUNDOOM: ("darkness", 70, "stage1", "デルビル", ("ダークフレイム", ("fire",), "20", DARK_FLAME_TEXT),
               ("くろいキバ", ("darkness", "colorless", "colorless"), "30+", BLACK_FANG_TEXT)),
    DARK_TYPHLOSION: ("fire", 80, "stage2", "わるいマグマラシ", ("つめできりさく", ("colorless",), "20", None), ("ファイヤーラッシュ", ("fire",), "40×", RUSHING_TEXT)),
    ROCKET_MEOWTH: ("colorless", 40, "basic", None, ("だいぎゃくてん？", ("colorless",), None, COMEBACK_TEXT)),
}
EXPECTED = {
    (CLEFAIRY_N1, 0): E.CoinFlipDamage(2, 10), (CLEFAIRY_N1, 1): E.CoinsPerPokemonInPlaySearchBasicEnergy(),
    (AMPHAROS, 0): E.DamageThenCoinsAttachTypedEnergyFromDeck(EnergyType.LIGHTNING, 3), (AMPHAROS, 1): E.CoinBonusOnHeadsElseParalyze(20),
    (MURKROW, 0): E.PutNamedBasicFromDeckOntoBenchOrFail(("ヤミカラス",)), (MURKROW, 1): E.CoinsPerOwnBenchNamedBonusDamage(("ヤミカラス",), 10),
    (HOUNDOOM, 0): E.DiscardEnergyThenDamageThenAttachFromDiscard(EnergyType.FIRE, EnergyType.DARKNESS),
    (HOUNDOOM, 1): E.CoinsPerOwnTypedEnergyBonusDamage(EnergyType.DARKNESS, 10),
    (DARK_TYPHLOSION, 0): E.DAMAGE_ONLY, (DARK_TYPHLOSION, 1): E.DiscardFieldEnergyThenCoinsDamage(EnergyType.FIRE, 40),
    (ROCKET_MEOWTH, 0): E.CoinsPerPokemonInPlayHeadsDamageTailsSelfDamage(10, 10),
}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, *, bench=(H.RATTATA,), opponent=None, opponent_bench=(H.RATTATA,), hand=(), deck=None, discard=(), opponent_deck=None, current=0, turn=TURN):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": list(deck if deck is not None else [W] * 10), "discard": list(discard), "prizes": 6}
    them = {"active": opponent or mon(H.RATTATA), "bench": list(opponent_bench), "hand": [], "deck": list(opponent_deck if opponent_deck is not None else [W] * 10),
            "discard": [], "prizes": 6}
    return build_test_state([me, them], turn_number=turn, current_player=current)


def attack(state, index=0, *coins, card=None):
    command = UseAttack(state.current_player, index) if card is None else UseAttack(state.current_player, index, card=card)
    return apply_kernel(with_coin_results(state, *coins) if coins else state, command)


def answer(state, choices, *coins):
    d = state.decision
    return apply_kernel(with_coin_results(state, *coins) if coins else state, ResolveDecision(d.player, d.id, tuple(choices)))


def same_answers(test, state, choices, *coins):
    """待っている決定のある状態を clone・deepcopy・pickle しても、同じ答え（と同じコインの結果）で同じ結果になる。"""
    expected = answer(state, choices, *coins)
    for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
        test.assertEqual(snap(answer(other, choices, *coins)), snap(expected))
    return expected


def flips(before, after, key=None):
    return [e["result"] for e in new_events(before, after, "coin_flip") if e.get("source") == "attack" and (key is None or e.get("effect") == key)]


def bases(before, after, target="opponent_active"):
    """そのワザのダメージの要素の基本となるダメージ（ログの ``steps`` の 1 段階）。"""
    found = []
    for e in new_events(before, after, "damage"):
        if (e.get("target") or "opponent_active") == target:
            steps = dict(e.get("steps", ()))
            found.append(steps.get("1 基本となる計算"))
    return found


def pid(state, card_id, player=0):
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card_id)


def uid(state, card_id, player=0, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def kinds(before, after, *names):
    return [e["kind"] for e in new_events(before, after, *names)]


def esp_board(provider, energy=(W, W), *, deck=None, discard=(), opponent=None, extra_bench=()):
    """ナツメのフーディン（バトル場。``energy``）のベンチに、超の色マーカーをのせた ``provider``（［サイコリンク］でワザを供給する「超」ポケモン）を置き、手札のナツメのESPを
    ``PlayTrainer``・``ResolveDecision`` でフーディンにつけた盤面（通常の登録・操作。ESPの関数を差しかえない）。"""
    state = board(mon(ALAKAZAM, energy), bench=(mon(provider, markers=[(MARKER_COLOR, EnergyType.PSYCHIC)]), *extra_bench),
                  opponent=opponent or mon(H.HITMONCHAN), hand=(ESP_CARD,), deck=deck, discard=discard)
    played = apply_kernel(state, PlayTrainer(0, uid(state, ESP_CARD)))
    if (played.decision.kind, played.decision.options) != (SELECT_POKEMON, (played.players[0].active.pokemon_id,)):
        raise AssertionError(f"ナツメのESPのつける先 {played.decision}")
    return answer(played, (played.players[0].active.pokemon_id,))


def provider_card(state, card_id):
    return next(p.card for p in state.players[0].bench if state.cards[p.card].card_id == card_id)


def without_context(state, key):
    """待っている決定の続きの情報から ``key`` を除いた状態（v0.112 までの続きの形を作る。修正前の再現のため）。"""
    broken = state.clone()
    d = broken.decision
    object.__setattr__(d, "context", tuple(item for item in d.context if item[0] != key))
    return broken


# ---------------------------------------------------------------- 1〜2 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        """6 枚・11 のワザの名前・必要なエネルギー・目安・説明と、タイプ・HP・段階・進化元は依頼の日本語・固定データと同じ（目安なしは null）。特殊能力・ルール文は 0。"""
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_113"]), V0113)
        self.assertEqual(len(V0113_ATTACKS), 11)
        for card, (color, hp, stage, below, *attacks) in QUOTED.items():
            definition = pool.definitions[card]
            with self.subTest(card=card):
                self.assertEqual((definition.pokemon_type.value, definition.hp, definition.stage, definition.evolves_from, definition.powers),
                                 (color, hp, stage, below, ()))
                self.assertEqual(len(definition.attacks), len(attacks))
                self.assertIn(card, pool.playable_ids)
            for index, (name, cost, display, text) in enumerate(attacks):
                printed = definition.attacks[index]
                entry = DEFAULT_EFFECTS.attack_entry(card, index)
                with self.subTest(card=card, index=index):
                    self.assertEqual((printed.name_ja, tuple(t.value for t in printed.cost), printed.damage_display, printed.text_ja), (name, cost, display, text))
                    self.assertEqual(entry.effect, EXPECTED[(card, index)])
                    if text is None:
                        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (name, None, None, None))
                    else:
                        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (name, text, text, "kyuura data/cards.json"))
                    self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, printed, definition.attacks))
        for below in ("neo1-041", "neo2-039", "neo4-020", MURKROW_N1):
            self.assertIn(below, pool.playable_ids)  # 対応済みの進化元（モココ・デルビル・わるいマグマラシ）とほかのヤミカラス

    def test_separate_cards_sources_and_data_gaps(self):
        """6 枚とも別々に登録する（同じカードの組はない）。データの欠けは PR1-078 のレベルだけで、補わない。転記元はピッピが nazonobasho.com、neo3・neo4 の 4 枚が Pokemon Wiki、
        PR1-078 が pcg-search.com（同じ転記元との一致を独立した照合にしない）。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        self.assertEqual({card: cards[card]["same_card_group"] for card in V0113}, dict.fromkeys(V0113))
        self.assertEqual({card: cards[card]["data_gaps"] for card in V0113}, {**{card: [] for card in V0113}, ROCKET_MEOWTH: ["jp_print.level"]})
        self.assertEqual({card: cards[card]["ja_text_source"].split("/")[2] for card in V0113},
                         {CLEFAIRY_N1: "nazonobasho.com", AMPHAROS: "wiki.pokemonwiki.com", MURKROW: "wiki.pokemonwiki.com", HOUNDOOM: "wiki.pokemonwiki.com",
                          DARK_TYPHLOSION: "wiki.pokemonwiki.com", ROCKET_MEOWTH: "pcg-search.com"})
        self.assertEqual({card: cards[card]["jp_en_differences"] for card in V0113}, {card: [] for card in V0113})
        self.assertEqual({card: cards[card]["pokemon"]["rules_text"] for card in V0113}, dict.fromkeys(V0113))

    def test_programs_and_shared_values(self):
        """要素の並び。お互いの場のポケモンの数のコインは、ピッピとロケット団のニャースで同じ値（``programs.FIELD_POKEMON``）を共有する。"""
        lightning, darkness, fire = EnergyType.LIGHTNING, EnergyType.DARKNESS, EnergyType.FIRE
        programs = {key: P.BUILDERS[type(effect)](effect) for key, effect in EXPECTED.items()}
        self.assertEqual(P.FIELD_POKEMON, (P.SCOPE_BOTH_IN_PLAY, None))
        self.assertEqual(programs[(CLEFAIRY_N1, 0)], (P.Damage(P.OPP, P.HeadsTimes(2, 10)),))
        self.assertEqual(programs[(CLEFAIRY_N1, 1)], (P.Coin("coin", per_pokemon=P.FIELD_POKEMON),
                                                      P.RevealTrainerFromDeck(local_coin=None, category="basic_energy", heads_of="coin")))
        self.assertEqual(programs[(AMPHAROS, 0)], (P.Damage(P.OPP, P.Printed()), P.Coin("coin", count=3), P.AttachFromDeckByHeads(lightning, "coin")))
        self.assertEqual(programs[(AMPHAROS, 1)], (P.Coin("coin"), P.Damage(P.OPP, P.PrintedPlusBonus("coin", 20)),
                                                   P.Status(P.PARALYSIS, gate=("coin", P.TAILS), reparalysis_check=True)))
        self.assertEqual(programs[(MURKROW, 0)], (P.BenchFromDeck(("ヤミカラス",), when_full=P.BENCH_FULL_FAIL),))
        self.assertEqual(programs[(MURKROW, 1)], (P.Coin("coin", per_pokemon=(P.SCOPE_OWN_BENCH, ("ヤミカラス",))), P.Damage(P.OPP, P.PrintedPlusHeadsOfCoin("coin", 10))))
        self.assertEqual(programs[(HOUNDOOM, 0)], (P.DiscardOwnEnergy(fire, count=1, when_lacking=P.LACKING_FAIL), P.Damage(P.OPP, P.Printed()),
                                                   P.AttachFromDiscard(darkness, 1, exact=True, typed_cards=True)))
        self.assertEqual(programs[(HOUNDOOM, 1)], (P.Coin("coin", per_own_typed=darkness), P.Damage(P.OPP, P.PrintedPlusHeadsOfCoin("coin", 10))))
        self.assertEqual(programs[(DARK_TYPHLOSION, 1)], (P.DiscardFieldEnergyAnyNumber(fire), P.Damage(P.OPP, P.HeadsOfDiscarded("discard", 40))))
        self.assertEqual(programs[(ROCKET_MEOWTH, 0)], (P.Coin("coin", per_pokemon=P.FIELD_POKEMON), P.Damage(P.OPP, P.HeadsOfCoin("coin", 10)),
                                                        P.Damage(P.SELF, P.TailsOfCoin("coin", 10), name="self_damage")))
        self.assertIs(programs[(CLEFAIRY_N1, 1)][0].per_pokemon, programs[(ROCKET_MEOWTH, 0)][0].per_pokemon)
        # コインが決める要素と受けるもの: 検索・つける・自分へのダメージは相手への要素ではない（相手の状態で止めない）。相手へのダメージ・マヒは相手への要素
        search, attach = programs[(CLEFAIRY_N1, 1)][1], programs[(AMPHAROS, 0)][2]
        self.assertEqual((search.coin_dependent("coin"), search.coin_receiver(), attach.coin_dependent("coin"), attach.coin_receiver()), (True, None, True, None))
        self.assertEqual([e.coin_receiver() for e in programs[(ROCKET_MEOWTH, 0)][1:]], ["damage", None])
        self.assertEqual([e.coin_receiver() for e in programs[(AMPHAROS, 1)][1:]], ["damage", "effect"])
        self.assertEqual({key: effect.opponent_effect_elements for key, effect in EXPECTED.items() if effect.opponent_effect_elements}, {(AMPHAROS, 1): (P.PARALYSIS,)})
        self.assertEqual(MAX_BRANCHES, 4096)

    def test_terms_are_bound_to_the_texts(self):
        """新しい型の確かめは全文・色・枚数・係数・名前を結び付ける。取り違えた登録と、意味の違う既存の型を拒否する。既存の型が形だけで同じ文面を受け付ける場合（v0.35 の
        ``CoinsPerAttachedTypeBonusDamage`` はくろいキバの書き方を受け付ける）は、登録の型をテストで固定する（形の確かめを意味の証明にしない）。"""
        pool = load_card_pool()
        printed = {key: pool.definitions[key[0]].attacks[key[1]] for key in EXPECTED}
        for key, effect in EXPECTED.items():
            with self.subTest(key=key):
                self.assertEqual(effect.check(printed[key]), [])
        wrong = {
            (CLEFAIRY_N1, 1): (E.CoinsPerPokemonInPlayHeadsDamageTailsSelfDamage(10, 10), E.RevealBasicEnergyFromDeck()),
            (AMPHAROS, 0): (E.DamageThenCoinsAttachTypedEnergyFromDeck(EnergyType.FIRE, 3), E.DamageThenCoinsAttachTypedEnergyFromDeck(EnergyType.LIGHTNING, 2),
                            E.AttachFromDeckUpToNamedCount(EnergyType.LIGHTNING, "デンリュウ")),
            (AMPHAROS, 1): (E.CoinBonusOnHeadsElseParalyze(10), E.CoinBonusDamageAndParalyze(20)),
            (MURKROW, 0): (E.PutNamedBasicFromDeckOntoBenchOrFail(("ニャース",)), E.PutBasicFromDeckOntoBench(("ヤミカラス",))),
            (MURKROW, 1): (E.CoinsPerOwnBenchNamedBonusDamage(("ニャース",), 10), E.CoinsPerOwnBenchNamedBonusDamage(("ヤミカラス",), 20)),
            (HOUNDOOM, 0): (E.DiscardEnergyThenDamageThenAttachFromDiscard(EnergyType.FIRE, EnergyType.FIRE),
                            E.DiscardEnergyThenDamageThenAttachFromDiscard(EnergyType.WATER, EnergyType.DARKNESS)),
            (HOUNDOOM, 1): (E.CoinsPerOwnTypedEnergyBonusDamage(EnergyType.WATER, 10), E.CoinsPerOwnTypedEnergyBonusDamage(EnergyType.DARKNESS, 20)),
            (DARK_TYPHLOSION, 1): (E.DiscardFieldEnergyThenCoinsDamage(EnergyType.FIRE, 30), E.DiscardFieldEnergyThenCoinsDamage(EnergyType.WATER, 40),
                                   E.DiscardAllThenCoinDamage(EnergyType.FIRE, 40)),
            (ROCKET_MEOWTH, 0): (E.CoinsPerPokemonInPlayHeadsDamageTailsSelfDamage(10, 20), E.CoinsHeadsDamageTailsSelfDamage(2, 10, 10)),
        }
        for key, effects in wrong.items():
            for effect in effects:
                with self.subTest(key=key, effect=effect):
                    self.assertTrue(effect.check(printed[key]))
        self.assertEqual(E.CoinsPerAttachedTypeBonusDamage(EnergyType.DARKNESS, 10).check(printed[(HOUNDOOM, 1)]), [])  # 形だけの確かめ（v0.35。数え方の問いが違う）
        for bad in (lambda: E.CoinBonusOnHeadsElseParalyze(15), lambda: E.CoinsPerOwnBenchNamedBonusDamage(("a", "b"), 10),
                    lambda: E.PutNamedBasicFromDeckOntoBenchOrFail(()), lambda: E.DiscardEnergyThenDamageThenAttachFromDiscard(EnergyType.COLORLESS, EnergyType.DARKNESS),
                    lambda: E.CoinsPerOwnTypedEnergyBonusDamage(EnergyType.COLORLESS, 10), lambda: E.DiscardFieldEnergyThenCoinsDamage(EnergyType.FIRE, 0),
                    lambda: E.DamageThenCoinsAttachTypedEnergyFromDeck(EnergyType.LIGHTNING, 0), lambda: E.CoinsPerPokemonInPlayHeadsDamageTailsSelfDamage(10, 5),
                    lambda: P.Coin("c", count=2, per_own_typed=EnergyType.DARKNESS, per_pokemon=P.FIELD_POKEMON), lambda: P.Coin("c", per_pokemon=("field", None)),
                    lambda: P.Coin("c", per_pokemon=(P.SCOPE_OWN_BENCH, ())), lambda: P.RevealTrainerFromDeck(heads_of="coin"),
                    lambda: P.RevealTrainerFromDeck(local_coin=None, required=True, heads_of="coin"), lambda: P.BenchFromDeck(("a",), when_full="skip"),
                    lambda: P.AttachFromDiscard(None, 1, typed_cards=True), lambda: P.DiscardFieldEnergyAnyNumber(EnergyType.FIRE, include_bench=False),
                    lambda: P.DiscardFieldEnergyAnyNumber(EnergyType.FIRE, max_cards=2)):
            with self.assertRaises(ValueError):
                bad()

    def test_unregistered_without_the_v0_113_entries(self):
        """今回の登録だけを除くと、ちょうど 6 枚が未対応にもどる（ほかのカードは失われない）。過去の版の切り出しに入らない。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V0113_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V0113))
        self.assertEqual(set(V0113) & set(cards_before(read_extract(), "0.113")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.112")) & set(cards_before(read_extract(), "0.114")), set(V0113))

    def test_adoption_records(self):
        """6 件の採用の記録（kyuura 73a1690・外部照合なし・kyuura の記録なし）。処理に使う文面は説明文のある 10 のワザの印刷の文面（つめできりさくは書かない）。新しい停止コードはない。"""
        sources = json.loads((ROOT / "kyuura_engine/data/card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine/data/research_links.json").read_text(encoding="utf-8"))
        texts = {card: [i for i, a in enumerate(QUOTED[card][4:]) if a[3] is not None] for card in V0113}
        for card in V0113:
            record = sources[card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"], record["external_checks"], record["issues"],
                                  record["recorded_on"]), ("kyuura_data", "adopted", COMMIT, [], [], [], "2026-10-28"))
                self.assertEqual(record["play_text"], {f"attack/{i}": "kyuura_printed_text" for i in texts[card]})
        self.assertIn("CC-PMCG6-063-P229", sources[ROCKET_MEOWTH]["notes"])
        self.assertEqual(sorted(k for k in links["latest_descriptions"]["adopted_printed_text"] if k.split("/")[0] in V0113),
                         sorted(f"{card}/attack/{i}" for card in V0113 for i in texts[card]))
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (237, 238))


# ---------------------------------------------------------------- 3 章: コインの枚数の生成元と結果の共有


class CoinSourceTest(unittest.TestCase):
    def test_field_count_both_sides_one_per_pokemon(self):
        """お互いの場のポケモンの数（バトル場とベンチ。進化して重なったカード・ついているカードを別の 1 匹にしない）。2 進化のデンリュウ 1 匹・エネルギー 4 枚でも 1。"""
        state = board(mon(ROCKET_MEOWTH, (W,)), bench=(mon(AMPHAROS, (L, L, L, W)), H.RATTATA), opponent=mon(CHANSEY), opponent_bench=(H.RATTATA,))
        done = attack(state, 0, HD, TL, HD, TL, TL)
        self.assertEqual(len(flips(state, done)), 5)
        self.assertEqual((bases(state, done), bases(state, done, "self")), ([20], [30]))
        audited(self, done)

    def test_face_down_and_trainer_pokemon_count_without_reading_identity(self):
        """うらのカード（マチスの秘策）・場でポケモンとしてあつかうなにかの化石も 1 匹。数だけなので正体を読まず、FD1 で止めない（相手のうらのカードも同じ）。"""
        state = board(mon(CLEFAIRY_N1, (W, W, W)), bench=(H.MYSTERIOUS_FOSSIL,), opponent=mon(CHANSEY), opponent_bench=(),
                      hand=(H.LT_SURGES_SECRET_PLAN, H.RATTATA))
        state = placed_face_down(state, H.RATTATA)
        self.assertTrue(any(state.is_face_down(p) for p in state.players[0].bench))
        asked = attack(state, 1, HD, TL, TL, HD)
        self.assertEqual((len(flips(state, asked)), asked.decision.kind, asked.decision.max_choices), (4, SEARCH_DECK, 2))

    def test_named_bench_count(self):
        """むれでつつく: 自分のベンチの、今の姿の名前が「ヤミカラス」のポケモンだけ（ほかのヤミカラスのカード neo1-055 も。自分のバトル場・相手の場・名前の違うポケモンは数えない）。
        0 匹なら投げず、目安の 10 は残る（ワザの失敗ではない）。"""
        state = board(mon(MURKROW, (W, W)), bench=(mon(MURKROW), mon(MURKROW_N1), H.RATTATA), opponent=mon(CHANSEY), opponent_bench=(mon(MURKROW),))
        done = attack(state, 1, HD, TL)
        self.assertEqual((flips(state, done), bases(state, done)), (["heads", "tails"], [20]))
        none = board(mon(MURKROW, (W, W)), bench=(H.RATTATA,), opponent=mon(CHANSEY), opponent_bench=(mon(MURKROW),))
        done = attack(none, 1)
        self.assertEqual((flips(none, done), bases(none, done), kinds(none, done, "attack_failed")), ([], [10], []))

    def test_named_count_with_a_face_down_bench_card_is_fd1(self):
        """名前を数えるとき、範囲（自分のベンチ）に名前の読めないうらのカードがあれば既存の FD1 で止める（数だけの場合とは分ける）。範囲の外（相手の場）のうらのカードでは止めない。"""
        state = board(mon(MURKROW, (W, W)), bench=(mon(MURKROW),), opponent=mon(CHANSEY), hand=(H.LT_SURGES_SECRET_PLAN, H.RATTATA))
        state = placed_face_down(state, H.RATTATA)
        rejects(self, state, UseAttack(0, 1), SECRET_PLAN_HIDDEN_CODE)

    def test_dark_energy_units_not_cards(self):
        """くろいキバ: 実際に使ったポケモンの「悪」エネルギーの個数（悪エネルギー 1 枚は 1 個。ほかの色・無色2個エネルギーは数えない）。［エナジーコンバーター］で「悪」にした水エネルギー
        カードは「悪」エネルギーカードではないが「悪」1 個（個数とカードの枚数が分かれる例）。基本となるダメージは 30 + 10H（つけている悪エネルギーの +10 は 5 段階で別）。"""
        state = board(mon(HOUNDOOM, (DARK, W, DCE)), opponent=mon(CHANSEY))
        done = attack(state, 1, HD)
        self.assertEqual((len(flips(state, done)), bases(state, done)), (1, [40]))
        state = board(mon(HOUNDOOM, (DARK, W, W)), bench=(porygon2(),), opponent=mon(CHANSEY))
        houndoom = state.players[0].active
        changed = convert(state, houndoom, houndoom.energy[1], EnergyType.DARKNESS)
        self.assertEqual((sum(1 for u in changed.players[0].active.energy if E.off_field_typed_energy_card(changed, u, EnergyType.DARKNESS)),
                          E.typed_unit_count(changed, changed.players[0].active, EnergyType.DARKNESS)), (1, 2))
        done = attack(changed, 1, HD, HD)
        self.assertEqual((len(flips(changed, done)), bases(changed, done)), (2, [50]))
        audited(self, done)

    def test_color_questions_and_wild_growth(self):
        """くろいキバの「悪」の個数は既存の数え方（v0.89 の ``typed_units_for``）。レインボーエネルギーは既存の 6 色（v0.78 で 8 色に広げていない ``BASIC_ENERGY_COLORS``）なので「悪」に数えず、
        RB1 にも当たらない（読み方を変えていない）。「草」でないので［おいしげる］の問いは当てはめない。"""
        rainbow = board(mon(HOUNDOOM, (DARK, RAINBOW, W)), opponent=mon(CHANSEY))
        self.assertEqual(len(flips(rainbow, attack(rainbow, 1, TL))), 1)
        with mock.patch.object(P, "wild_growth_question", side_effect=AssertionError("おいしげるを聞いた")):
            state = board(mon(HOUNDOOM, (DARK, W, W)), bench=(mon("neo1-014", (G, G), evolved_from=["neo1-002", "neo1-009"]),), opponent=mon(CHANSEY))
            self.assertEqual(len(flips(state, attack(state, 1, TL))), 1)

    def test_copies_count_the_actual_user(self):
        """ゆびをふる（ピクシー）で使うと、くろいキバは実際に使ったピクシーの「悪」を数える。お互いの場の数（だいぎゃくてん？）は使い手によらない場全体。"""
        state = board(mon(H.CLEFABLE, (DARK, W, W)), opponent=mon(HOUNDOOM, (DARK, DARK, DARK)))
        asked = attack(state, 0)
        self.assertEqual(asked.decision.kind, SELECT_ATTACK)
        done = answer(asked, (1,), HD)
        self.assertEqual((len(flips(asked, done)), bases(asked, done)), (1, [40]))
        state = board(mon(H.CLEFABLE, (W, W, W)), bench=(H.RATTATA, H.RATTATA), opponent=mon(ROCKET_MEOWTH))  # 相手のベンチにもコラッタ 1 匹（お互いの場で 5 匹）
        asked = attack(state, 0)
        done = answer(asked, (0,), HD, TL, TL, TL, TL)
        self.assertEqual((len(flips(asked, done)), bases(asked, done), bases(asked, done, "self")), (5, [10], [40]))

    def test_preflight_groups_by_heads_and_modes_agree(self):
        """「おもて」の数だけを使うコインは、先読みで N + 1 通りにまとめる（まとめない先読みと同じ答え。結果の数は少ないか同じ）。3 つの方法で同じ結果。実際の対戦は 1 枚ずつ投げる。"""
        cases = {
            "みんなでおどる": (board(mon(CLEFAIRY_N1, (W, W, W)), bench=(H.RATTATA, H.RATTATA), opponent=mon(CHANSEY), deck=[W, W, F] + [H.RATTATA] * 6), 1),
            "ゆうでん": (board(mon(AMPHAROS, (L,)), bench=(mon(H.PIKACHU),), opponent=mon(CHANSEY), deck=[L, L, L] + [W] * 7), 0),
            "むれでつつく": (board(mon(MURKROW, (W, W)), bench=(mon(MURKROW), mon(MURKROW_N1)), opponent=mon(CHANSEY)), 1),
            "くろいキバ": (board(mon(HOUNDOOM, (DARK, DARK, W)), opponent=mon(CHANSEY)), 1),
            "ファイヤーラッシュ": (board(mon(DARK_TYPHLOSION, (F, F)), bench=(mon(H.CHARMANDER, (F,)),), opponent=mon(CHANSEY)), 1),
            "だいぎゃくてん？": (board(mon(ROCKET_MEOWTH, (W,)), bench=(H.RATTATA, H.RATTATA), opponent=mon(CHANSEY), opponent_bench=(H.RATTATA, H.RATTATA)), 0),
        }
        for name, (state, index) in cases.items():
            with self.subTest(name=name):
                grouped, grouped_branches = traced(state, UseAttack(0, index))
                ungrouped, ungrouped_branches = traced(state, UseAttack(0, index), grouped=False)
                self.assertEqual(grouped, ungrouped)
                self.assertLessEqual(grouped_branches[0], ungrouped_branches[0])
                results = [snap(apply_kernel(state, UseAttack(0, index), preflight=mode)) for mode in ("derived", "derived_full", "legacy")]
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0], results[2])


# ---------------------------------------------------------------- 4.1 ピッピ


class SquaredanceTest(unittest.TestCase):
    def state(self, deck):
        return board(mon(CLEFAIRY_N1, (W, W, W)), bench=(H.RATTATA,), opponent=mon(CHANSEY), opponent_bench=(H.RATTATA,), deck=deck)

    def test_up_to_heads_and_only_chosen_cards_are_shown(self):
        """N = 4・H = 2: 0〜2 枚の基本エネルギーカード（特殊エネルギーは入らない）を選び、選んだカードだけを見せて手札に加え、1 回切る。0 枚は「以下」の 0 枚（せいでんきと同じ読み方）。"""
        state = self.state([W, F, DCE, RAINBOW] + [H.RATTATA] * 6)
        asked = attack(state, 1, HD, TL, HD, TL)
        d = asked.decision
        basics = tuple(u for u in state.players[0].deck if state.card_def(u).is_basic_energy)
        self.assertEqual((d.kind, d.options, d.min_choices, d.max_choices), (SEARCH_DECK, basics, 0, 2))
        one = same_answers(self, asked, basics[:1])
        self.assertEqual([e["card"] for e in new_events(asked, one, "reveal_from_deck")], [basics[0]])
        self.assertEqual((kinds(asked, one, "shuffle"), basics[0] in one.players[0].hand), (["shuffle"], True))
        none = answer(asked, ())
        self.assertEqual((kinds(asked, none, "reveal_from_deck", "reveal_from_deck_declined", "shuffle")), ["reveal_from_deck_declined", "shuffle"])
        audited(self, one)

    def test_zero_heads_still_shuffles(self):
        """H = 0 なら選ぶカードがないので決定を出さないが、末尾の「その後、その山札をよく切る」にしたがって 1 回切る（せいでんきの数 0 と同じ。エネルギーアークの読み方は移さない）。"""
        state = self.state([W] * 10)
        done = attack(state, 1, TL, TL, TL, TL)
        self.assertEqual((done.decision, kinds(state, done, "shuffle", "reveal_from_deck")), (None, ["shuffle"]))

    def test_decision_without_candidates_and_cap_not_reduced(self):
        """H が正なら、山札に選べるカードがなくても決定を出して答えを待つ。最大の枚数は H のままで、選べるカードの数に合わせない（山札の中身で進み方を変えない）。"""
        empty = self.state([DCE, H.RATTATA, H.RATTATA])
        asked = attack(empty, 1, HD, HD, TL, TL)
        self.assertEqual((asked.decision.kind, asked.decision.options, asked.decision.max_choices), (SEARCH_DECK, (), 2))
        self.assertEqual(kinds(asked, answer(asked, ()), "reveal_from_deck_declined", "shuffle"), ["reveal_from_deck_declined", "shuffle"])
        one = self.state([W, H.RATTATA])
        asked = attack(one, 1, HD, HD, HD, TL)
        self.assertEqual((len(asked.decision.options), asked.decision.max_choices), (1, 3))

    def test_hidden_candidates_and_invalid_answers(self):
        """相手・観戦者には決定の種類と決めるプレイヤーだけ（選べるカードの数・最大の枚数を見せない）。H より多い・選べないカード・重複の答えは拒否し、状態・乱数・ログ・決定を変えない。"""
        state = self.state([W, W, F] + [H.RATTATA] * 6)
        asked = attack(state, 1, HD, TL, TL, TL)
        for viewer in (1, None):
            self.assertEqual(observe(asked, viewer)["decision"], {"kind": SEARCH_DECK, "player": 0})
        before = snap(asked)
        d = asked.decision
        for choices in (d.options[:2], (asked.players[0].deck[-1],), (d.options[0], d.options[0])):
            with self.assertRaises(IllegalActionError):
                apply_kernel(asked, ResolveDecision(0, d.id, choices))
        self.assertEqual(snap(asked), before)


# ---------------------------------------------------------------- 4.2 デンリュウ


class AttractCurrentTest(unittest.TestCase):
    def state(self, deck=None, *, bench=None, active=None, **kw):
        return board(active or mon(AMPHAROS, (L,)), bench=bench if bench is not None else (mon(H.PIKACHU), H.RATTATA), opponent=mon(CHANSEY),
                     deck=deck if deck is not None else [L, L, L, W, W, W], **kw)

    def test_damage_first_then_coins_choose_exactly_heads_and_distribute(self):
        """目安 20 のダメージ（説明の最初に省略）→ コイン 3 枚 → H 枚ちょうどの「雷」エネルギーカード → 1 枚ずつつける先（自分の場の今の色が「雷」のポケモン。バトル場もベンチも）→
        すべて決めてからつけ、1 回切る。決める間、カードは山札にある。"""
        state = self.state()
        asked = attack(state, 0, HD, HD, TL)
        self.assertEqual(kinds(state, asked, "damage", "coin_flip")[:2], ["damage", "coin_flip"])
        d = asked.decision
        lightning = tuple(u for u in state.players[0].deck if state.card_def(u).provides is EnergyType.LIGHTNING)
        self.assertEqual((d.kind, d.options, d.min_choices, d.max_choices), (ATTACH_FROM_DECK, lightning, 2, 2))
        target = same_answers(self, asked, lightning[:2])
        options = (pid(state, AMPHAROS), pid(state, H.PIKACHU))
        self.assertEqual((target.decision.kind, target.decision.options, target.decision.context_value("card")), (SELECT_POKEMON, options, lightning[0]))
        self.assertTrue(all(card in target.players[0].deck for card in lightning[:2]))
        second = same_answers(self, target, (options[0],))
        done = same_answers(self, second, (options[1],))
        self.assertEqual([(e["pokemon_id"], e["card"]) for e in new_events(second, done, "attach_energy_from_deck")], [(options[0], lightning[0]), (options[1], lightning[1])])
        self.assertEqual(kinds(asked, done, "shuffle"), ["shuffle"])
        self.assertEqual(done.energy_attachments_this_turn, state.energy_attachments_this_turn)  # 手札からつける通常の操作に数えない
        audited(self, done)

    def test_several_cards_to_one_pokemon(self):
        """「好きなように」: 1 匹に 2 枚以上をつけてもよい（バトル場のデンリュウに 3 枚）。"""
        state = self.state()
        asked = attack(state, 0, HD, HD, HD)
        step = answer(asked, asked.decision.options[:3])
        for _ in range(3):
            step = answer(step, (pid(state, AMPHAROS),))
        self.assertEqual(len(step.players[0].active.energy), 4)

    def test_targets_follow_the_current_type(self):
        """つける先は今有効な色で決める（名前・印刷のタイプで固定しない）。雷の色マーカーをのせたコラッタは選べ、雷でないポケモンは選べない。"""
        state = self.state(bench=(mon(H.RATTATA, markers=[(MARKER_COLOR, EnergyType.LIGHTNING)]), mon(H.SQUIRTLE)))
        asked = attack(state, 0, HD, TL, TL)
        target = answer(asked, asked.decision.options[:1])
        self.assertEqual(target.decision.options, (pid(state, AMPHAROS), pid(state, H.RATTATA)))

    def test_face_down_target_stops_only_when_chosen(self):
        """うらのカード（マチスの秘策）はタイプが読めないので、選べるが選ぶと止める（FD1。状態を変えない）。ほかのつける先を選べば続く。"""
        state = self.state(bench=(mon(H.PIKACHU),), hand=(H.LT_SURGES_SECRET_PLAN, H.RATTATA))
        state = placed_face_down(state, H.RATTATA)
        hidden = next(p.pokemon_id for p in state.players[0].bench if state.is_face_down(p))
        asked = attack(state, 0, HD, TL, TL)
        target = answer(asked, asked.decision.options[:1])
        self.assertIn(hidden, target.decision.options)
        self.assertEqual(target.decision.context_value("unresolved_choices"), (hidden,))
        rejects(self, target, ResolveDecision(0, target.decision.id, (hidden,)), SECRET_PLAN_HIDDEN_CODE)
        self.assertEqual(len(answer(target, (pid(state, H.PIKACHU),)).players[0].bench[0].energy), 1)

    def test_zero_heads_no_target_and_no_candidates(self):
        """H = 0: 選ぶカードはなく 1 回切る（``no_heads``）。つけられる「雷」ポケモンがいない（公開の情報）: コインも投げず 1 回切る（``no_target``）。山札に「雷」エネルギーカードがない:
        決定を出して 0 枚の答えを待ち（山札の中身を進み方で漏らさない）、1 回切る（``no_candidates``。p.309）。どれもワザの失敗ではない。"""
        state = self.state()
        done = attack(state, 0, TL, TL, TL)
        self.assertEqual([e["reason"] for e in new_events(state, done, "attach_energy_from_deck_none")], ["no_heads"])
        self.assertEqual(kinds(state, done, "shuffle"), ["shuffle"])
        nobody = board(mon(H.CLEFABLE, (W,)), opponent=mon(AMPHAROS, (L,)))
        asked = attack(nobody, 0)
        done = answer(asked, (0,))
        self.assertEqual((flips(asked, done), [e["reason"] for e in new_events(asked, done, "attach_energy_from_deck_none")]), ([], ["no_target"]))
        empty = self.state([W, W, W])
        asked = attack(empty, 0, HD, TL, TL)
        self.assertEqual((asked.decision.kind, asked.decision.options, asked.decision.min_choices, asked.decision.max_choices), (ATTACH_FROM_DECK, (), 0, 1))
        done = answer(asked, ())
        self.assertEqual(([e["reason"] for e in new_events(asked, done, "attach_energy_from_deck_none")], kinds(asked, done, "shuffle", "attack_failed")),
                         (["no_candidates"], ["shuffle"]))
        for viewer in (1, None):
            self.assertEqual(observe(asked, viewer)["decision"], {"kind": ATTACH_FROM_DECK, "player": 0})

    def test_short_deck_is_fc1_but_enough_cards_are_normal(self):
        """0 < 山札の「雷」エネルギーカードの枚数 < H は FC1（説明の枚数より少ない。UQ-STATED-COUNT-SHORT）。コインの結果で受け付けるかを変えない約束なので、足りない「おもて」の数が
        ありうる山札（1・2 枚）では宣言の前に止める。3 枚以上なら、どの結果でも H 枚を選べる（エネルギーアークの「コインの枚数より少なければ止める」を一律に移したのではなく、0 枚は
        止めない）。"""
        for count in (1, 2):
            with self.subTest(count=count):
                rejects(self, self.state([L] * count + [W] * 5), UseAttack(0, 0), QUESTIONS["stated_cards_short"].code)
        self.assertEqual(attack(self.state([L] * 3 + [W] * 5), 0, HD, HD, HD).decision.kind, ATTACH_FROM_DECK)
        self.assertEqual(attack(self.state([W] * 5), 0, HD, HD, HD).decision.options, ())

    def test_rainbow_in_the_deck_is_rb2_when_needed_or_chosen(self):
        """山札のレインボーエネルギーは RB2: 「雷」エネルギーカードが H 枚以上あれば選べるが選ぶと止める。足りないならレインボーを選ばないと H 枚にならないので止める。"""
        state = self.state([L, L, L, RAINBOW])
        asked = attack(state, 0, HD, TL, TL)
        rainbow = uid(state, RAINBOW, zone="deck")
        self.assertIn(rainbow, asked.decision.options)
        rejects(self, asked, ResolveDecision(0, asked.decision.id, (rainbow,)), QUESTIONS["rainbow_attach_type"].code)
        rejects(self, self.state([L, L, RAINBOW]), UseAttack(0, 0), QUESTIONS["rainbow_attach_type"].code)

    def test_blocked_and_knocked_out_targets(self):
        """エネルギーカードをつけることができない（クリスタルビーム）ポケモンは選べない。相手の［はんげき］でこのワザの中で HP 以上になったデンリュウも選べない（p.309。ベンチの雷は選べる）。
        つけられるポケモンがいなければコインを投げない。"""
        state = self.state()
        beam = state.clone()
        beam.turn_number = TURN - 1  # 相手の番に与えた効果（ログの番と合わせる。自然な対戦で起こらない盤面を作るため）
        add_persistent_effect(beam, 0, beam.players[0].active, CannotAttachEnergy(beam.players[1].active.card, 1, TURN - 1, TURN), attack=f"{H.MISTYS_TENTACOOL}#0")
        beam.turn_number = TURN
        asked = attack(beam, 0, HD, TL, TL)
        self.assertEqual(answer(asked, asked.decision.options[:1]).decision.options, (pid(state, H.PIKACHU),))
        countered = board(mon(AMPHAROS, (L,), damage=80), bench=(mon(H.PIKACHU),), opponent=mon(H.MACHAMP), deck=[L, L, L, W])
        asked = attack(countered, 0, HD, TL, TL)
        self.assertEqual(answer(asked, asked.decision.options[:1]).decision.options, (pid(countered, H.PIKACHU),))
        alone = board(mon(AMPHAROS, (L,), damage=80), bench=(H.RATTATA,), opponent=mon(H.MACHAMP), deck=[L, L, L, W])
        done = attack(alone, 0)
        self.assertEqual((flips(alone, done), [e["reason"] for e in new_events(alone, done, "attach_energy_from_deck_none")]), ([], ["no_target"]))

    def test_invalid_answers_and_saves(self):
        """不正な答え（枚数の違い・山札にないカード・選べないつける先）は状態・乱数・ログ・決定を変えない。カード・つける先の決定の続きは clone・deepcopy・pickle から同じ。"""
        state = self.state()
        asked = attack(state, 0, HD, HD, TL)
        before = snap(asked)
        for choices in (asked.decision.options[:1], asked.decision.options[:3], (state.players[0].deck[-1],)):
            with self.assertRaises(IllegalActionError):
                apply_kernel(asked, ResolveDecision(0, asked.decision.id, choices))
        self.assertEqual(snap(asked), before)
        target = answer(asked, asked.decision.options[:2])
        before = snap(target)
        with self.assertRaises(IllegalActionError):
            apply_kernel(target, ResolveDecision(0, target.decision.id, (pid(state, H.RATTATA),)))
        self.assertEqual(snap(target), before)
        self.assertEqual(check_invariants(target), [])


class GigavoltTest(unittest.TestCase):
    def test_heads_bonus_tails_paralysis_from_one_coin(self):
        """1 枚の共有のコインをダメージの計算の前に投げる。「おもて」なら基本となるダメージ 60（マヒなし）、「うら」なら 40 とマヒ（v0.8 の「おもて」で追加してマヒとは別の意味）。"""
        state = board(mon(AMPHAROS, (L, L, L, W)), opponent=mon(CHANSEY))
        heads = attack(state, 1, HD)
        self.assertEqual((kinds(state, heads, "coin_flip", "damage"), bases(state, heads), heads.players[1].active.conditions.paralyzed), (["coin_flip", "damage"], [60], False))
        tails = attack(state, 1, TL)
        self.assertEqual((bases(state, tails), tails.players[1].active.conditions.paralyzed), ([40], True))
        audited(self, tails)

    def test_prevented_damage_and_barrier(self):
        """相手が「ダメージを受けない」状態でも、コインはマヒも決めるので投げる（「うら」ならマヒ）。「ワザをうけない」状態（バリアー）ならどちらも無効なので HC3 で止める。相手がこのワザで
        HP 以上なら「うら」でもマヒにしない（p.309）。"""
        guarded = board(mon(AMPHAROS, (L, L, L, W)), opponent=mon(CHANSEY, prevent_damage=TURN - 1))
        tails = attack(guarded, 1, TL)
        self.assertEqual((flips(guarded, tails), tails.players[1].active.conditions.paralyzed), (["tails"], True))
        rejects(self, barrier_turn(mon(AMPHAROS, (L, L, L, W))), UseAttack(0, 1), QUESTIONS["prevented_effect_coin"].code)
        knocked = board(mon(AMPHAROS, (L, L, L, W)), opponent=mon(H.RATTATA))
        tails = attack(knocked, 1, TL)
        self.assertEqual(kinds(knocked, tails, "special_condition"), [])


# ---------------------------------------------------------------- 4.3 ヤミカラス


class CallForFamilyTest(unittest.TestCase):
    def test_one_named_basic_from_the_deck_then_shuffle(self):
        """山札の名前が「ヤミカラス」のたねポケモン（neo3-043・neo1-055）から 1 枚ちょうど（省略できない）。ベンチに出して 1 回切る。"""
        state = board(mon(MURKROW, (W,)), opponent=mon(CHANSEY), deck=[MURKROW, MURKROW_N1, H.RATTATA, W])
        asked = attack(state, 0)
        d = asked.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices, sorted(state.cards[u].card_id for u in d.options)), (BENCH_FROM_DECK, 1, 1, sorted([MURKROW, MURKROW_N1])))
        done = answer(asked, d.options[:1])
        self.assertEqual((len(done.players[0].bench), kinds(asked, done, "bench_from_deck", "shuffle")), (2, ["bench_from_deck", "shuffle"]))
        audited(self, done)

    def test_no_candidates_is_not_a_failure(self):
        """山札にヤミカラスがないのは処理の対象がない（p.309。出さずに切る）で、ワザの失敗とは別の理由。"""
        state = board(mon(MURKROW, (W,)), opponent=mon(CHANSEY), deck=[H.RATTATA, W])
        done = attack(state, 0)
        self.assertEqual(kinds(state, done, "bench_from_deck_none", "attack_failed", "shuffle"), ["bench_from_deck_none", "shuffle"])

    def test_full_bench_fails_after_the_declaration(self):
        """ベンチに空きがないときは、宣言を受け付けてからのワザの失敗（p.323。使ったことになり、番が終わる。山札を見ない・切らない）。v0.32 の「なかまをよぶ」（ワザを使うための条件）とは
        別の扱いで、英語の欄の Can't use は持ち込まない。"""
        state = board(mon(MURKROW, (W,)), bench=[H.RATTATA] * 5, opponent=mon(CHANSEY), deck=[MURKROW, W])
        done = attack(state, 0)
        self.assertEqual(([e["reason"] for e in new_events(state, done, "attack_failed")], kinds(state, done, "shuffle", "bench_from_deck"), done.turn_number),
                         (["bench_full"], [], TURN + 1))
        old = board(mon(H.NIDORAN_F, (G, G)), bench=[H.RATTATA] * 5, opponent=mon(CHANSEY))
        rejects(self, old, UseAttack(0, 1), "BENCH_FULL", error=IllegalActionError)


    def test_copies_with_a_full_bench(self):
        """ゆびをふる（ピッピ。「ワザに必要なエネルギー以外はワザの説明にしたがう」）で使うと、説明どおりワザの失敗。ピクシーの「ほかに必要な条件…がたりないときには使えない」では、
        失敗とする条件がそれに当たるかが決まらない（既存の HC9。選ぶと止める）。"""
        state = board(mon(H.CLEFAIRY, (W, W, W)), bench=[H.RATTATA] * 5, opponent=mon(MURKROW, (W,)), deck=[MURKROW, W])
        asked = attack(state, 1)
        done = answer(asked, (0,))
        self.assertEqual(([e["reason"] for e in new_events(asked, done, "attack_failed")], kinds(asked, done, "bench_from_deck", "shuffle")), (["bench_full"], []))
        pixie = board(mon(H.CLEFABLE, (W,)), bench=[H.RATTATA] * 5, opponent=mon(MURKROW, (W,)), deck=[MURKROW, W])
        asked = attack(pixie, 0)
        self.assertEqual(asked.decision.context_value("unresolved_choices"), (0,))
        rejects(self, asked, ResolveDecision(0, asked.decision.id, (0,)), "UNRESOLVED_COPIED_ATTACK")


# ---------------------------------------------------------------- 4.4 ヘルガー


class DarkFlameTest(unittest.TestCase):
    def test_discard_then_damage_then_attach_a_darkness_energy_card(self):
        """炎のトラッシュ（ワザの効果。決定 1 枚）→ 目安 20 のダメージ → トラッシュの悪エネルギー（特殊エネルギーカードのまま）を 1 枚つける。つけた悪エネルギーの +10 はこの 20 に加わらない
        （ダメージの計算の時点でついていない）。つけた悪エネルギーは次のワザで +10。"""
        state = board(mon(HOUNDOOM, (F, W)), opponent=mon(CHANSEY), discard=(DARK, W))
        asked = attack(state, 0)
        self.assertEqual((asked.decision.kind, asked.decision.min_choices), (DISCARD_ENERGY, 1))
        attach = answer(asked, asked.decision.options)
        dark = uid(state, DARK, zone="discard")
        self.assertEqual((attach.decision.kind, attach.decision.options, attach.decision.min_choices), (ATTACH_FROM_DISCARD, (dark,), 1))
        done = same_answers(self, attach, (dark,))
        self.assertEqual(kinds(state, done, "discard_energy", "damage", "attach_energy_from_discard"), ["discard_energy", "damage", "attach_energy_from_discard"])
        damage = next(e for e in new_events(state, done, "damage"))
        self.assertEqual((damage["amount"], dark in done.players[0].active.energy, done.card_def(dark).is_basic_energy), (20, True, False))
        audited(self, done)

    def test_no_fire_card_fails_without_damage(self):
        """炎エネルギーカードをトラッシュできないときは、日本語の「このワザは失敗する」（p.323。ダメージも与えない。つけない）。ゆびをふる（ピッピ。「ワザに必要なエネルギー以外は
        ワザの説明にしたがう」）で使うと起こる。ピクシーの「ほかに必要な条件…がたりないときには使えない」では、失敗するワザがその条件に当たるかが決まらない既存の HC9。"""
        state = board(mon(H.CLEFAIRY, (W, W, W)), opponent=mon(HOUNDOOM, (F,)), discard=(DARK,))
        asked = attack(state, 1)
        done = answer(asked, (0,))
        self.assertEqual(([e["reason"] for e in new_events(asked, done, "attack_failed")], kinds(asked, done, "damage", "attach_energy_from_discard")), (["discard"], []))
        pixie = board(mon(H.CLEFABLE, (W,)), opponent=mon(HOUNDOOM, (F,)), discard=(DARK,))
        asked = attack(pixie, 0)
        rejects(self, asked, ResolveDecision(0, asked.decision.id, (0,)), "UNRESOLVED_COPIED_ATTACK")

    def test_without_a_darkness_card_only_the_attach_is_skipped(self):
        """トラッシュに「悪」エネルギーカードがなければ、つけるのを省く（ワザの失敗・使うための条件ではない）。鋼エネルギー・無色2個エネルギー・基本エネルギーは「悪」ではない。ミラクル
        エネルギーは場の外で色がない。"""
        state = board(mon(HOUNDOOM, (F,)), opponent=mon(CHANSEY), discard=(METAL, DCE, W, H.MIRACLE_ENERGY))
        asked = attack(state, 0)
        done = answer(asked, asked.decision.options)
        self.assertEqual((done.decision, kinds(asked, done, "damage", "attack_failed", "attach_energy_from_discard")), (None, ["damage"]))
        self.assertEqual([E.off_field_typed_energy_card(state, u, EnergyType.DARKNESS) for u in state.players[0].discard], [False] * 4)

    def test_rainbow_in_the_discard_is_rb2(self):
        """トラッシュのレインボーエネルギーが「「悪」エネルギーカード」に当たるかは RB2（既存の ``AttachFromDiscard`` と同じく、トラッシュにあれば止める）。"""
        rejects(self, board(mon(HOUNDOOM, (F,)), opponent=mon(CHANSEY), discard=(DARK, RAINBOW)), UseAttack(0, 0), QUESTIONS["rainbow_attach_type"].code)

    def test_counterattack_knockout_or_attach_block_skips_the_attach(self):
        """相手の［はんげき］でヘルガーがこのワザの中で HP 以上なら、つけない（p.309。ログ ``effect_skipped``）。"""
        state = board(mon(HOUNDOOM, (F,), damage=60), opponent=mon(H.MACHAMP), discard=(DARK,))
        asked = attack(state, 0)
        done = answer(asked, asked.decision.options)
        self.assertEqual(([e["reason"] for e in new_events(asked, done, "effect_skipped")], kinds(asked, done, "attach_energy_from_discard")), ([E.EFFECT_TARGET_KNOCKED_OUT], []))


class BlackFangTest(unittest.TestCase):
    def test_prevented_damage_is_the_existing_question(self):
        """コインは相手へのダメージの量だけを決めるので、相手が「ダメージを受けない」状態なら v0.4b の問い（N = 0 なら投げないので止めない）。"""
        rejects(self, board(mon(HOUNDOOM, (DARK, W, W)), opponent=mon(CHANSEY, prevent_damage=TURN - 1)), UseAttack(0, 1), QUESTIONS["prevented_coin_damage"].code)
        # ゆびをふる（ピッピ。「ワザに必要なエネルギー以外はワザの説明にしたがう」）で、「悪」のないピッピが使うと N = 0（投げない・止めない。目安の 30 は無効）
        state = board(mon(H.CLEFAIRY, (W, W, W)), opponent=mon(HOUNDOOM, (DARK, W, W), prevent_damage=TURN - 1))
        asked = attack(state, 1)
        done = answer(asked, (1,))
        self.assertEqual((flips(asked, done), kinds(asked, done, "damage")), ([], []))


# ---------------------------------------------------------------- 4.5 わるいバクフーン


class RushingFlamesTest(unittest.TestCase):
    def test_field_wide_selection_actual_count_and_heads(self):
        """自分の場全体（使い手 → ベンチ）の「炎」エネルギーカードから好きなだけ選んでトラッシュし、実際にトラッシュした枚数 N だけコインを投げ、基本となるダメージ 40H。H = 0 は 0
        （与えなかった。ワザの失敗ではない）。"""
        state = board(mon(DARK_TYPHLOSION, (F, F, W)), bench=(mon(H.CHARMANDER, (F,)), mon(H.PIKACHU, (L,))), opponent=mon(CHANSEY))
        asked = attack(state, 1)
        fires = tuple(u for p in state.players[0].in_play() for u in p.energy if state.card_def(u).provides is EnergyType.FIRE)
        self.assertEqual((asked.decision.kind, asked.decision.options, asked.decision.min_choices, asked.decision.max_choices), (DISCARD_ENERGY, fires, 0, 3))
        done = answer(asked, fires, HD, TL, HD)
        self.assertEqual((len(new_events(asked, done, "discard_energy")), flips(asked, done), bases(asked, done)), (3, ["heads", "tails", "heads"], [80]))
        none = answer(asked, fires[:1], TL)
        self.assertEqual((bases(asked, none), kinds(asked, none, "attack_failed")), ([0], []))
        audited(self, done)

    def test_zero_with_candidates_is_hc5(self):
        """選べるカードがあるときの 0 枚は HC5（「のぞむなら」のない「好きなだけ」。選ぶと止める。状態は変えない）。1 枚以上は選べる。"""
        state = board(mon(DARK_TYPHLOSION, (F,)), opponent=mon(CHANSEY))
        asked = attack(state, 1)
        rejects(self, asked, ResolveDecision(0, asked.decision.id, ()), "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO")

    def test_no_candidates_means_no_coins(self):
        """選べるカードがない（ゆびをふるのピクシーの場に「炎」エネルギーカードがない）なら、決定を出さず、0 枚でコインを投げない（p.309）。"""
        state = board(mon(H.CLEFABLE, (W,)), opponent=mon(DARK_TYPHLOSION, (F,)))
        asked = attack(state, 0)
        done = answer(asked, (1,))
        self.assertEqual((done.decision, flips(asked, done), bases(asked, done)), (None, [], [0]))

    def test_own_discards_are_not_returned_by_ecogym(self):
        """自分のワザでトラッシュした自分のカードは、エコロジム（相手の効果でトラッシュしたときだけ）で手札にもどさない。数えるのはトラッシュした枚数。"""
        state = board(mon(DARK_TYPHLOSION, (F, F)), opponent=mon(CHANSEY), hand=(H.ECOGYM,))
        state = apply_kernel(state, PlayTrainer(0, uid(state, H.ECOGYM)))
        asked = attack(state, 1)
        done = answer(asked, asked.decision.options, HD, HD)
        self.assertEqual((len(done.players[0].discard), bases(asked, done)), (2, [80]))


# ---------------------------------------------------------------- 4.6 ロケット団のニャース


class MiraculousComebackTest(unittest.TestCase):
    def test_heads_to_the_opponent_tails_to_self_from_one_set(self):
        """N 枚 1 組の H で相手に 10H、同じ組の T = N − H で自分に 10T（目安なし。固定の目安を足さない）。"""
        state = board(mon(ROCKET_MEOWTH, (W,)), opponent=mon(CHANSEY))
        done = attack(state, 0, HD, HD, TL, HD)
        self.assertEqual((bases(state, done), bases(state, done, "self")), ([30], [10]))
        zero = attack(state, 0, TL, TL, TL, TL)
        self.assertEqual((bases(state, zero), bases(state, zero, "self")), ([0], [40]))
        audited(self, done)

    def test_void_opponent_damage_keeps_self_damage(self):
        """相手へのダメージが無効（「ダメージを受けない」）でも、自分へのダメージは残るのでコインを投げる（v0.34 の ``void_coin_question``）。自分へのダメージは既存のワザの自分への
        ダメージの経路で、HP 以上ならきぜつの処理へ。"""
        state = board(mon(ROCKET_MEOWTH, (W,)), opponent=mon(CHANSEY, prevent_damage=TURN - 1))
        done = attack(state, 0, TL, TL, TL, TL)
        self.assertEqual((len(flips(state, done)), bases(state, done, "self")), (4, [40]))
        self.assertTrue(any(e["kind"] == "knock_out" for e in new_events(state, done)))


# ---------------------------------------------------------------- 5 章: ESP（通常の登録・操作の経路）と続きの情報


class EspRealPathTest(unittest.TestCase):
    """ナツメのフーディンの［サイコリンク］で、超の色マーカーをのせたベンチのポケモンのワザを使い、ナツメのESPのやり直しを聞く（ESPの関数・解決の部品を差しかえない。正式な対戦の使用実績では
    ない）。"""

    def test_v0_112_tentacle_grip_is_reachable(self):
        """v0.112 の訂正: 超の色マーカーのドククラゲ（SI-016）を供給元にすると、フーディンの「水」2 個で 2 枚のコイン → ESPの決定（決定の前は 0 枚）→ やり直さない（「おもて」1）で 2 枚、
        両方「おもて」にやり直すと 4 枚。"""
        state = esp_board(TENTACRUEL_SI)
        asked = attack(state, 0, HD, TL, card=provider_card(state, TENTACRUEL_SI))
        self.assertEqual((asked.decision.kind, new_events(state, asked, "draw")), (ESP_REDO, []))
        kept = same_answers(self, asked, ())
        self.assertEqual(len(next(e for e in new_events(asked, kept, "draw") if e["player"] == 0)["cards"]), 2)
        redone = same_answers(self, asked, (1,), HD, HD)
        self.assertEqual(len(next(e for e in new_events(asked, redone, "draw") if e["player"] == 0)["cards"]), 4)

    def test_comeback_uses_the_final_heads_and_tails_for_both(self):
        """だいぎゃくてん？: ESPでやり直したら、相手（10H）と自分（10T）の両方に同じ確定した組を使う（別々に投げ直さない）。"""
        state = esp_board(ROCKET_MEOWTH, opponent=mon(CHANSEY))
        asked = attack(state, 0, HD, TL, TL, TL, card=provider_card(state, ROCKET_MEOWTH))
        self.assertEqual((asked.decision.kind, new_events(state, asked, "damage")), (ESP_REDO, []))
        redone = same_answers(self, asked, (1,), HD, HD, HD, TL)
        self.assertEqual((bases(asked, redone), bases(asked, redone, "self")), ([30], [10]))
        kept = answer(asked, ())
        self.assertEqual((bases(asked, kept), bases(asked, kept, "self")), ([10], [30]))

    def test_rushing_flames_carries_the_discarded_cards(self):
        """ファイヤーラッシュ: トラッシュのあとダメージの要素の中のコインでESPを聞く。答えのあとにもう一度処理するダメージの要素が読むトラッシュの結果を、続きの情報 ``discarded_results`` で
        運ぶ（運ばない v0.112 までの続きの形では ``KeyError: 'discard'`` の内部エラーになっていた）。"""
        state = esp_board(DARK_TYPHLOSION, energy=(F, F, W))
        asked = attack(state, 1, card=provider_card(state, DARK_TYPHLOSION))
        esp = answer(asked, asked.decision.options, HD, TL)
        self.assertEqual((esp.decision.kind, dict(esp.decision.context)["discarded_results"]), (ESP_REDO, (("discard", tuple(asked.decision.options), "done"),)))
        redone = same_answers(self, esp, (1,), HD, HD)
        self.assertEqual(bases(esp, redone), [80])
        with self.assertRaises(KeyError):
            answer(without_context(esp, "discarded_results"), (1,), HD, HD)

    def test_existing_discharge_and_smokescreen_no_longer_crash(self):
        """同じ続きの情報で直した既存のワザ: マチスのエレブーの「ほうでん」（トラッシュの結果）・キョウのドガースの「くもがくれガス」（ダメージの結果。既存の ``damage_results``）。修正前の
        続きの形では ``KeyError``。"""
        state = esp_board(H.LT_SURGES_ELECTABUZZ, energy=(L, L, W))
        esp = attack(state, 1, HD, TL, card=provider_card(state, H.LT_SURGES_ELECTABUZZ))
        self.assertEqual(bases(esp, same_answers(self, esp, (1,), HD, HD)), [60])
        with self.assertRaises(KeyError):
            answer(without_context(esp, "discarded_results"), (1,), HD, HD)
        state = esp_board(KOGAS_KOFFING, energy=(PS, G, W, L))
        esp = attack(state, 1, HD, card=provider_card(state, KOGAS_KOFFING))
        self.assertEqual(esp.decision.kind, ESP_REDO)
        self.assertIn("damage_results", dict(esp.decision.context))
        same_answers(self, esp, (1,), HD)
        with self.assertRaises(KeyError):
            answer(without_context(esp, "damage_results"), (1,), HD)

    def test_invalid_esp_answers_leave_everything_unchanged(self):
        state = esp_board(ROCKET_MEOWTH, opponent=mon(CHANSEY))
        asked = attack(state, 0, HD, TL, TL, TL, card=provider_card(state, ROCKET_MEOWTH))
        before = snap(asked)
        for player, choices in ((1, ()), (0, (2,)), (0, (1, 1))):
            with self.assertRaises(IllegalActionError):
                apply_kernel(asked, ResolveDecision(player, asked.decision.id, choices))
        self.assertEqual(snap(asked), before)


class SaveAndFormatTest(unittest.TestCase):
    def test_format_unchanged_and_new_decisions_are_written(self):
        """新しい状態の項目はなく、書き出しの形式は 26 のまま（監査の ``LATEST_FORMAT`` も 26）。新しい続きの情報（``heads``・``cards``・``assigned``・``card``・``discarded_results``）は
        決定の ``context`` の値で、形式 26 で書き出せ（書き出し・観測・不変条件の確かめが通る）、clone・deepcopy・pickle から同じ答えで同じ続きになる（各テストの ``same_answers``）。"""
        from kyuura_engine.serialize import state_to_dict

        self.assertEqual((max(FORMAT_VERSIONS), LATEST_FORMAT), (26, 26))
        state = board(mon(AMPHAROS, (L,)), bench=(mon(H.PIKACHU),), opponent=mon(CHANSEY), deck=[L, L, L, W])
        card = attack(state, 0, HD, HD, TL)
        target = answer(card, card.decision.options[:2])
        for waiting in (card, target):
            written = state_to_dict(waiting, format_version=26)["decision"]
            self.assertEqual(written["context"]["heads"], 2)
            audited(self, waiting)
        self.assertEqual(state_to_dict(target, format_version=26)["decision"]["context"]["cards"], list(card.decision.options[:2]))


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v113_problems``）は、エンジンの登録・計算を読まずに、処理したワザの印刷の文面から読んだ数・色・名前・係数と、ログから組み立てた場・コイン・
    カードの動き・基本となるダメージで確かめる。エンジンの処理を一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の局。v0.113 の 11 のワザがどれも出る組と開発用の
    seed。正式な対戦の seed 0〜3 とは別）で、監査がそれを見つける。"""

    GAMES = ((("P113", "T113"), 102), (("L113", "D113"), 103), (("D113", "T113"), 106))

    @classmethod
    def problems_for(cls, patcher, *needles):
        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        found = []
        with patcher:
            for labels, seed in cls.GAMES:
                result = games.play(labels, seed, keep_state=True)
                if result.get("state") is not None:
                    found += [p for p in log_problems(result["state"]) if any(n in p for n in needles)]
                found += [k for k, v in result["policy"].items() if k.startswith("v113") and k.endswith("_mismatch") and v and any(n in k for n in needles)]
        return found

    def test_the_unpatched_games_pass_the_audit(self):
        from tests.log_audit import log_problems
        from tools import existing_effect_games as games

        used, checked = set(), set()
        for labels, seed in self.GAMES:
            result = games.play(labels, seed, keep_state=True)
            with self.subTest(labels=labels, seed=seed):
                self.assertEqual((result["outcome"], result["audit"], log_problems(result["state"])), ("game_over", {}, []))
                self.assertEqual({k: v for k, v in result["policy"].items() if k.startswith("v113") and k.endswith(("_mismatch", "_no_accepted_answer"))}, {})
            used |= {k[len("attack_"):] for k, v in result["v113"].items() if k.startswith("attack_") and v}
            checked |= {k for k, v in result["policy"].items() if k.startswith("v113") and k.endswith("_checked") and v}
        self.assertEqual(used, {str(key) for key in V0113_ATTACKS})
        self.assertEqual(len(checked), 8)

    def test_audit_finds_wrong_coin_sources(self):
        """お互いの場の数を自分の場だけにした・ベンチの名前をバトル場も数えた・「悪」の個数を基本エネルギーカードの枚数にした・相手と自分のダメージを別のコインにした。"""
        original_run = P.Coin.run

        def own_side(self, run):
            if self.per_pokemon == P.FIELD_POKEMON:
                count = len(run.state.players[run.player].in_play())
                run.fs.coins[self.name] = run.flip(count, by_heads=True) if count else P.CoinFlips(())
                return False
            return original_run(self, run)

        self.assertTrue(self.problems_for(mock.patch.object(P.Coin, "run", own_side), "お互いの場のポケモンの数", "squaredance", "comeback"))
        flock = {E.CoinsPerOwnBenchNamedBonusDamage: lambda e: (P.Coin("coin", per_pokemon=(P.SCOPE_OWN_IN_PLAY, e.names)), P.Damage(P.OPP, P.PrintedPlusHeadsOfCoin("coin", e.per)))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, flock), "自分のベンチの", "flock"))
        cards = {E.CoinsPerOwnTypedEnergyBonusDamage: lambda e: (P.Coin("coin", per_attached=e.energy_type), P.Damage(P.OPP, P.PrintedPlusHeadsOfCoin("coin", e.per)))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, cards), "エネルギーの個数", "black_fang"))
        separate = {E.CoinsPerPokemonInPlayHeadsDamageTailsSelfDamage: lambda e: (
            P.Coin("coin", per_pokemon=P.FIELD_POKEMON), P.Damage(P.OPP, P.HeadsOfCoin("coin", e.per)), P.Coin("coin2", per_pokemon=P.FIELD_POKEMON),
            P.Damage(P.SELF, P.TailsOfCoin("coin2", e.self_per), name="self_damage"))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, separate), "お互いの場のポケモンの数", "comeback"))

    def test_audit_finds_wrong_cards_and_damage(self):
        """みんなでおどるで「おもて」の数より多く選べるようにした・ゆうでんで「おもて」の数より少なくつけた・ファイヤーラッシュの係数を変えた・ダークフレイムでつけてからダメージを与えた・
        ギガボルトの「おもて」の追加を変えた。"""
        original_search, original_resume, original_attach = P.RevealTrainerFromDeck.run, P.RevealTrainerFromDeck.resume, P.AttachFromDeckByHeads.run

        def more(self, run):
            if self.heads_of is not None and run.heads(self.heads_of):
                run.suspend(kind=SEARCH_DECK, player=run.player, options=self.candidates(run), min_choices=0, max_choices=run.heads(self.heads_of) + 1)
                return True
            return original_search(self, run)

        def reveal_all(self, run, decision, choices):
            for card in sorted(choices):  # 数を確かめずに見せて手札に加える（誤らせた処理）
                P.reveal_deck_to_hand(run.state, run.player, card, effect=str(run.key))
            P.shuffle_in_attack(run, self, run.player)

        # 決定の形の不変条件（``decision_problems``）も、ここでは確かめないようにする（監査が別に見つけることを確かめる）
        with mock.patch.object(P.RevealTrainerFromDeck, "resume", lambda self, run, d, c: reveal_all(self, run, d, c) if self.heads_of else original_resume(self, run, d, c)),                 mock.patch.object(E.CoinsPerPokemonInPlaySearchBasicEnergy, "decision_problems", lambda self, state, use, decision: []):
            self.assertTrue(self.problems_for(mock.patch.object(P.RevealTrainerFromDeck, "run", more), "以下の自分の基本エネルギーカード", "squaredance"))

        def fewer(self, run):
            coins = run.fs.coins[self.heads_of]
            heads = sum(1 for side in coins.results if side is HD)
            if heads >= 2:
                run.fs.coins[self.heads_of] = P.CoinFlips((HD,) + (TL,) * (len(coins.results) - 1))
                try:
                    return original_attach(self, run)
                finally:
                    run.fs.coins[self.heads_of] = coins
            return original_attach(self, run)

        self.assertTrue(self.problems_for(mock.patch.object(P.AttachFromDeckByHeads, "run", fewer), "と合わない", "attract"))
        rushing = {E.DiscardFieldEnergyThenCoinsDamage: lambda e: (P.DiscardFieldEnergyAnyNumber(e.energy_type), P.Damage(P.OPP, P.HeadsOfDiscarded("discard", 30)))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, rushing), "トラッシュした", "rushing"))
        early = {E.DiscardEnergyThenDamageThenAttachFromDiscard: lambda e: (
            P.DiscardOwnEnergy(e.discard_type, count=1, when_lacking=P.LACKING_FAIL), P.AttachFromDiscard(e.attach_type, 1, exact=True, typed_cards=True),
            P.Damage(P.OPP, P.Printed()))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, early), "ダメージのあとの自分のトラッシュ", "dark_flame"))
        # ギガボルトの「おもて」は、この 3 局ではどれも相手を HP 以上にする（「おもて」でマヒにする誤りは観測できない）ので、「おもて」の追加の量を誤らせる
        bonus = {E.CoinBonusOnHeadsElseParalyze: lambda e: (P.Coin("coin"), P.Damage(P.OPP, P.PrintedPlusBonus("coin", e.bonus + 10)),
                                                           P.Status(P.PARALYSIS, gate=("coin", P.TAILS), reparalysis_check=True))}
        self.assertTrue(self.problems_for(mock.patch.dict(P.BUILDERS, bonus), "「おもて」で、基本となるダメージ"))


class DocumentTest(unittest.TestCase):
    def test_document_names_the_shared_parts(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("per_pokemon", "FIELD_POKEMON", "counted_pokemon", "per_own_typed", "typed_units_for", "heads_of", "AttachFromDeckByHeads", "DiscardFieldEnergyAnyNumber",
                       "BENCH_FULL_FAIL", "typed_cards", "off_field_typed_energy_card", "discarded_results", "damage_results", "coin_group", "has_target", "HC5", "FC1", "RB2",
                       "FD1", "GR-2000-P320-DAMAGE-FIGURE", "GR-2000-P309-ATTACK-PROCEDURE", "RUL-ENERGY-DISCARD-ATTACKS", "CC-PMCG6-063-P229", "v113_problems", "v113_uses",
                       "c6fb94f", "9e8ca5c", "73a1690"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()

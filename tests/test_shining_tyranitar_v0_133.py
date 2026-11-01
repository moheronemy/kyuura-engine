"""v0.133（docs/shining-tyranitar-v0.133.md）: ひかるバンギラス（neo4-082）のマウンテンクラッシュ・はかいのほのお（利用者の指定）。

- 登録・記録（2〜3 章）: 写しの組・数・利用者が指定した規則の記録（印刷の文面のまま・原文との差・解決済みにしない論点）・採用の記録・研究の対応表・検査
- マウンテンクラッシュ（4 章）: 30 が先・「うら」まで（山札 0 枚でも）・min(H, 山札)・山札切れは番の最初・防護を山札に流用しない・ESP・コピー
- はかいのほのお（5 章）: 炎 0 枚の宣言の拒否・「おもて」0 の成功・自分のトラッシュ → ダメージ → 相手のトラッシュ・相手の不足・防護・特殊エネルギー・コピー・ESP
- 先読み・保存・不正な答え・観測（6〜7 章）、ログの監査とわざと誤らせたログ（8 章）

盤面は 1 か所の規定を確かめるために直接作ったもので、``new_game`` からの自然な対戦の結果ではない（正式な対戦は 10 章）。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import pickle
import unittest
from unittest import mock

from kyuura_engine import checks
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import EndTurn, ResolveDecision, UseAttack
from kyuura_engine.decisions import (
    DISCARD_ENERGY,
    DISCARD_OPPONENT_ENERGY,
    ESP_REDO,
    SELECT_ATTACK,
)
from kyuura_engine.deck import deck_problems
from kyuura_engine.engine import apply_command, check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import visible_log
from kyuura_engine.resolution import programs as P
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import Phase
from scripts import check_card_sources as cs
from tests import helpers as HP
from tests.helpers import build_test_state, with_coin_bits
from tests.log_audit import (
    observation_problems,
    serialization_problems,
    v133_problems,
    v133_snapshot,
)
from tests.release_catalog import cards_after

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "shining-tyranitar-v0.133.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
TYR = "neo4-082"
D, F, FI, W, P_ = HP.DARKNESS_ENERGY_NEO1, HP.FIRE, HP.FIGHTING, HP.WATER, HP.PSYCHIC
DCE = "PMCG1-096"  # 無色2個エネルギー（特殊エネルギー。1 枚のエネルギーカード）
MC, DF = (D, FI, FI), (D, F, F, F)
MEWTWO = HP.MEWTWO


def run(heads: int) -> tuple[CoinSide, ...]:
    return (HD,) * heads + (TL,)


def fingerprint(state):
    return (repr(state_to_dict(state, format_version=max(FORMAT_VERSIONS))), state.rng.getstate(), len(state.log))


def board(energy=MC, *, deck=5, opponent_energy=(W, W), opponent=None, prevent_damage=False):
    spec = {"card": opponent or HP.CHANSEY, "energy": list(opponent_energy)}
    if prevent_damage:
        spec["prevent_damage"] = 2  # 2 番に「かたまる」などで受けた効果（3 番の相手のワザのダメージを受けない）
    return build_test_state([{"active": {"card": TYR, "energy": list(energy)}, "deck": [F] * 10, "prizes": 6},
                             {"active": spec, "deck": [W] * deck, "prizes": 6}])


def attack(state, index, *coins, player=0, **extra):
    return apply_command(with_coin_bits(state, *coins) if coins else state, UseAttack(player, index, **extra))


def answer(state, choices, *coins):
    d = state.decision
    return apply_command(with_coin_bits(state, *coins) if coins else state, ResolveDecision(d.player, d.id, tuple(choices)))


def finish(state):
    """待っている決定に、先頭からちょうど最小の枚数で答えて進める（ESPのやり直しは「やり直さない」）。"""
    while state.decision is not None and state.phase is Phase.DECISION:
        d = state.decision
        state = answer(state, () if d.kind == ESP_REDO else d.options[:d.min_choices])
    return state


def since(before, after, *kinds):
    return [e for e in after.log[len(before.log):] if not kinds or e["kind"] in kinds]


def audited(test, state, snapshots=None):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])
    test.assertEqual(v133_problems(state, snapshots), [])


def snapshots_for(state, index):
    return {len(state.log): v133_snapshot(state, UseAttack(state.current_player, index))}


# ---------------------------------------------------------------- 2〜3 章: 登録・記録


class RegistrationTest(unittest.TestCase):
    def test_pool_counts_deck_limit_and_no_card_branch(self):
        extract = read_extract()
        self.assertEqual(extract["pool_v0_133"], [TYR])
        self.assertEqual(cards_after(extract, "0.132") - cards_after(extract, "0.133"), {TYR})
        pool = load_card_pool()
        self.assertIn(TYR, pool.playable_ids)
        self.assertEqual(len(pool.playable_ids - cards_after(extract, "0.133")), 1374)
        self.assertEqual(pool.get(TYR).deck_limit, 1)  # 「デッキに1枚まで」（v0.82 の deck_limit。同じ名前で数える）
        base = [W] * 58
        self.assertFalse([p for p in deck_problems(base + [TYR, HP.CHANSEY], pool) if "TOO_MANY" in p or "ひかるバンギラス" in p])
        self.assertTrue([p for p in deck_problems(base + [TYR, TYR], pool) if "ひかるバンギラス" in p])
        for path in [ROOT / "kyuura_engine" / "engine.py", *sorted((ROOT / "kyuura_engine" / "resolution").glob("*.py"))]:
            self.assertNotIn(TYR, path.read_text(encoding="utf-8"), path.name)

    def test_entries_and_text_checks(self):
        definition = load_card_pool().get(TYR)
        crush, fire = (E.DEFAULT_EFFECTS.attack_entry(TYR, i) for i in (0, 1))
        self.assertIsInstance(crush.effect, E.DamageThenMillOpponentUntilTailsUpToDeck)
        self.assertIsInstance(fire.effect, E.CoinsPerOwnTypedCardsDiscardThenDamageThenOpponentEnergy)
        for entry, attack_def, text in ((crush, definition.attacks[0], E.MOUNTAIN_CRUSH_TEXT), (fire, definition.attacks[1], E.DESTRUCTIVE_FIRE_TEXT)):
            self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (attack_def.text_ja, text, "kyuura data/cards.json"))
            self.assertEqual(entry.effect.check(attack_def), [])
            self.assertTrue(entry.effect.check(dataclasses.replace(attack_def, text_ja=text + "x")))  # 文面が違えば受け付けない
            self.assertTrue(dataclasses.replace(entry.effect, attack_rule="OTHER").check(attack_def))  # 記録のない規則
        self.assertEqual([type(e).__name__ for e in P.BUILDERS[type(fire.effect)](fire.effect)],
                         ["OwnTypedEnergyCardsRequired", "Coin", "DiscardOwnTypedEnergyByHeads", "Damage", "DiscardOpponentEnergyUpToHeads"])
        self.assertEqual([type(e).__name__ for e in P.BUILDERS[type(crush.effect)](crush.effect)], ["Damage", "MillOpponentDeckUntilTailsUpTo"])

    def test_user_rule_records(self):
        definition = load_card_pool().get(TYR)
        crush, fire = E.USER_SPECIFIED_RULES[f"{TYR}/attack/0"], E.USER_SPECIFIED_RULES[f"{TYR}/attack/1"]
        self.assertEqual((crush.rule, crush.printed_text, crush.play_text, crush.issues), (E.USER_MOUNTAIN_CRUSH_RULE, definition.attacks[0].text_ja,
                                                                                            definition.attacks[0].text_ja, ("UQ-STATED-COUNT-SHORT",)))
        self.assertEqual((fire.rule, fire.printed_text, fire.play_text, fire.issues), (E.USER_DESTRUCTIVE_FIRE_RULE, definition.attacks[1].text_ja,
                                                                                         definition.attacks[1].text_ja, ("UQ-DESTRUCTIVE-FIRE-FAILURE", "UQ-STATED-COUNT-SHORT")))
        text = DOC.read_text(encoding="utf-8")
        for record in (crush, fire):
            self.assertEqual((record.specified_by, record.source), ("user", E.USER_TYRANITAR_RULE_SOURCE))
            self.assertIn("公式の裁定", record.not_recorded_as)
            self.assertTrue(record.text_difference)
            self.assertIn(f"「{record.instruction}」", text)
            self.assertIn("広げない", record.scope)
        # v0.130・v0.132 の記録は変えていない（差の欄は既定の空）
        self.assertEqual([E.USER_SPECIFIED_RULES[k].text_difference for k in ("PR1-027/trainer", "neo1-049/power/0")], ["", ""])

    def test_adoption_and_research_records(self):
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"][TYR]
        self.assertEqual(sources["play_text"], {"attack/0": "kyuura_printed_text", "attack/1": "kyuura_printed_text"})
        self.assertEqual(sources["user_specified_rule"], {"attack/0": E.USER_TYRANITAR_RULE_SOURCE, "attack/1": E.USER_TYRANITAR_RULE_SOURCE})
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        latest = links["latest_descriptions"]
        for target in (f"{TYR}/attack/0", f"{TYR}/attack/1"):
            self.assertIn(target, latest["adopted_printed_text"])  # 文面は印刷の採用
            self.assertEqual(latest["user_specified_rules"][target], E.USER_TYRANITAR_RULE_SOURCE)  # 規則は別に数える
        cases = {(c["kyuura_issue"], c["card_id"], c["target"]): c["engine"] for c in links["kyuura_cases_without_engine_ruling"]["cases"]}
        self.assertEqual(cases[("UQ-STATED-COUNT-SHORT", TYR, "attack/0")], {"user_specified_rule": f"{TYR}/attack/0"})
        self.assertEqual(cases[("UQ-STATED-COUNT-SHORT", TYR, "attack/1")], {"user_specified_rule": f"{TYR}/attack/1"})
        self.assertEqual(cases[("UQ-DESTRUCTIVE-FIRE-FAILURE", TYR, "attack/1")], {"user_specified_rule": f"{TYR}/attack/1"})
        self.assertEqual(cases[("UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY", TYR, "attack/1")],
                         {"stop_codes": ["UNRESOLVED_RAINBOW_ENERGY_TYPE", "UNRESOLVED_BUZZAP_ENERGY_CARD_TYPE"]})
        self.assertEqual(links["counts"]["engine_stop_codes"], 316)  # 新しい停止コードはない
        self.assertFalse([c for c in cases.values() if c == {"unregistered": True}])  # 未登録の事例はなくなった
        # 他のカードの不足の止め方（FC1・DU1・TW1・HC6）は今までどおり
        self.assertEqual(cases[("UQ-STATED-COUNT-SHORT", "ES2-005", "attack/0")], {"stop_codes": ["UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT"]})

    def test_source_check_finds_broken_records(self):
        registry, card = E.DEFAULT_EFFECTS, read_extract_card(TYR)
        record = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"][TYR]
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        self.assertEqual(cs.user_specified_rule_problems(TYR, TYR, record, card, registry, links), [])
        broken = dict(record, user_specified_rule={"attack/0": E.USER_TYRANITAR_RULE_SOURCE})
        self.assertTrue(cs.user_specified_rule_problems(TYR, TYR, broken, card, registry, links))
        moved = dict(record, play_text={"attack/0": E.USER_TYRANITAR_RULE_SOURCE, "attack/1": "kyuura_printed_text"})
        self.assertTrue(cs.user_specified_rule_problems(TYR, TYR, moved, card, registry, links))  # 規則を文面の区分と偽る
        rules = dict(E.USER_SPECIFIED_RULES)
        rules[f"{TYR}/attack/0"] = dataclasses.replace(rules[f"{TYR}/attack/0"], text_difference="")
        with mock.patch.object(E, "USER_SPECIFIED_RULES", rules):
            self.assertTrue(any("text_difference" in p for p in cs.user_specified_rule_problems(TYR, TYR, record, card, registry, links)))

    def test_other_shortage_types_keep_their_stops(self):
        """「足りなければあるだけ」はこの 2 つの対象だけ: ほかの型の要素は v0.133 の要素にならない。"""
        new = (P.MillOpponentDeckUntilTailsUpTo, P.DiscardOpponentEnergyUpToHeads, P.OwnTypedEnergyCardsRequired, P.DiscardOwnTypedEnergyByHeads)
        mine = (E.DamageThenMillOpponentUntilTailsUpToDeck, E.CoinsPerOwnTypedCardsDiscardThenDamageThenOpponentEnergy)
        for key in E.DEFAULT_EFFECTS.attack_keys():
            effect = E.DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect
            if type(effect) in P.BUILDERS and not isinstance(effect, mine):
                self.assertFalse([e for e in P.BUILDERS[type(effect)](effect) if isinstance(e, new)], key)
        tornado = P.BUILDERS[E.CoinsDiscardOpponentEnergyElseFail](E.CoinsDiscardOpponentEnergyElseFail(2))
        self.assertIs(type(tornado[-1]), P.DiscardOpponentEnergyByHeads)  # たつまきは FC1 のまま


def read_extract_card(card_id):
    return next(c for c in read_extract()["cards"] if c["id"] == card_id)


# ---------------------------------------------------------------- 4 章: マウンテンクラッシュ


class MountainCrushTest(unittest.TestCase):
    def test_heads_against_deck_sizes(self):
        for deck, heads, milled, short in ((5, 0, 0, False), (5, 3, 3, False), (5, 5, 5, False), (2, 5, 2, True), (0, 3, 0, True)):
            with self.subTest(deck=deck, heads=heads):
                state = board(deck=deck)
                done = attack(state, 0, *run(heads))
                coins = [e for e in since(state, done, "coin_flip") if e.get("effect") == f"{TYR}#0"]
                self.assertEqual([e["result"] for e in coins], ["heads"] * heads + ["tails"])  # 山札の枚数で打ち切らない（0 枚でも投げる）
                discards = [uid for e in since(state, done, "discard_from_deck") for uid in e["cards"]]
                self.assertEqual(discards, list(state.players[1].deck[:milled]))  # 山札の上から
                shorts = since(state, done, E.USER_RULE_COUNT_SHORT_EVENT)
                self.assertEqual([(e["required"], e["available"], e["processed"]) for e in shorts], [(heads, deck, deck)] if short else [])
                audited(self, done, snapshots_for(state, 0))

    def test_damage_first_and_deck_out_only_at_draw(self):
        state = board(deck=2)
        done = attack(state, 0, *run(4))
        kinds = [e["kind"] for e in since(state, done)]
        self.assertLess(kinds.index("damage"), kinds.index("coin_flip"))  # 30（悪エネルギーで 40）が先
        self.assertEqual(since(state, done, "damage")[0]["steps"][0][1], 30)
        # 山札がなくなった時点では負けない: 番が終わり、相手の番の最初に引くときに山札切れ
        self.assertLess(kinds.index(E.USER_RULE_COUNT_SHORT_EVENT), kinds.index("turn_end"))
        self.assertLess(kinds.index("turn_start"), kinds.index("deck_out"))
        self.assertEqual(done.phase, Phase.GAME_OVER)
        self.assertEqual(done.result.winner, 0)
        audited(self, done, snapshots_for(state, 0))

    def test_damage_protection_is_not_applied_to_the_deck(self):
        state = board(deck=5, prevent_damage=True)
        done = attack(state, 0, *run(2))
        self.assertEqual(done.players[1].active.damage, 0)  # ダメージは防いだ
        self.assertEqual(len(since(state, done, "discard_from_deck")[0]["cards"]), 2)  # 山札のトラッシュは起こる
        audited(self, done, snapshots_for(state, 0))

    def test_effect_protection_is_not_applied_to_the_deck(self):
        barrier = barrier_board()
        done = attack(barrier, 0, *run(2))
        self.assertTrue(since(barrier, done, "damage_prevented", "effect_prevented") or done.players[1].active.damage == 0)
        self.assertEqual(sum(len(e["cards"]) for e in since(barrier, done, "discard_from_deck")), 2)
        audited(self, done)

    def test_esp_short_to_enough_and_back(self):
        from tests.test_variable_coins_search_attachments_v0_113 import (
            esp_board,
            mon,
            provider_card,
        )

        state = esp_board(TYR, MC, opponent=mon(HP.CHANSEY, (W,)))
        size = len(state.players[1].deck)
        for first, second, milled in ((size + 2, 1, 1), (1, size + 3, size)):
            with self.subTest(first=first, second=second):
                asked = attack(state, 0, *run(first), card=provider_card(state, TYR))
                self.assertEqual(asked.decision.kind, ESP_REDO)
                done = answer(asked, (1,), *run(second))
                self.assertEqual(len(since(asked, done, "damage")), 0)  # ダメージはくり返さない
                self.assertEqual(sum(len(e["cards"]) for e in since(asked, done, "discard_from_deck")), milled)
                shorts = since(asked, done, E.USER_RULE_COUNT_SHORT_EVENT)
                self.assertEqual([e["required"] for e in shorts], [second] if second > size else [])
                audited(self, done)
        kept = answer(attack(state, 0, *run(size + 2), card=provider_card(state, TYR)), ())
        self.assertEqual([e["required"] for e in kept.log if e["kind"] == E.USER_RULE_COUNT_SHORT_EVENT], [size + 2])

    def test_copy_mills_the_copiers_opponent(self):
        state = build_test_state([{"active": {"card": HP.CLEFAIRY, "energy": [W, W, W]}, "deck": [F] * 10, "prizes": 6},
                                  {"active": {"card": TYR, "energy": list(DF)}, "deck": [W] * 3, "prizes": 6}])
        asked = attack(state, metronome_index(state), HD, HD, TL)
        self.assertEqual((asked.decision.kind, asked.decision.options), (SELECT_ATTACK, (0,)))  # はかいのほのおは選べない（炎 0 枚）
        done = answer(asked, (0,), HD, HD, HD, HD, TL)
        self.assertEqual(sum(len(e["cards"]) for e in since(state, done, "discard_from_deck") if e["player"] == 1), 3)
        audited(self, done)

    def test_confusion_coin_is_not_an_attack_coin(self):
        """こんらんのひかるバンギラス: こんらんのコイン（``source`` confusion）のあとに 30 とワザのコイン。「うら」ならワザは失敗し、ワザのコインはない（監査はこんらんのコインを数えない）。"""
        state = build_test_state([{"active": {"card": TYR, "energy": list(MC), "confusion": True}, "deck": [F] * 10, "prizes": 6},
                                  {"active": {"card": HP.CHANSEY, "energy": [W]}, "deck": [W] * 5, "prizes": 6}])
        done = attack(state, 0, HD, HD, TL)
        coins = since(state, done, "coin_flip")
        self.assertEqual([(e["source"], e["result"]) for e in coins], [("confusion", "heads"), ("attack", "heads"), ("attack", "tails")])
        self.assertEqual(sum(len(e["cards"]) for e in since(state, done, "discard_from_deck")), 1)
        audited(self, done, snapshots_for(state, 0))
        failed = attack(state, 0, TL)
        self.assertEqual([e["source"] for e in since(state, failed, "coin_flip")], ["confusion"])
        self.assertEqual(since(state, failed, "discard_from_deck"), [])
        audited(self, failed, snapshots_for(state, 0))

    def test_capped_classes(self):
        classes = P.capped_classes(3)
        self.assertEqual((classes.representatives, classes.bound), ((0, 1, 2, 3), 3))
        self.assertEqual([classes.index_of_heads(h) for h in (0, 2, 3, 4, 9)], [0, 2, 3, 3, 3])
        with self.assertRaises(RuntimeError):
            P.capped_classes(-1)


def metronome_index(state):
    return next(i for i, a in enumerate(state.card_def(state.players[0].active.card).attacks) if a.name_ja == "ゆびをふる")


def barrier_board():
    """相手（プレイヤー 1）のミュウツーが 2 番に「バリアー」を使い、3 番（プレイヤー 0 の番）にワザのダメージや効果を受けない盤面（通常の操作で作る）。"""
    state = build_test_state([{"active": {"card": TYR, "energy": list(MC) + [F, F, F]}, "deck": [F] * 10, "prizes": 6},
                              {"active": {"card": MEWTWO, "energy": [P_, P_, P_, W]}, "deck": [W] * 5, "prizes": 6}], current_player=1, turn_number=2)
    index = next(i for i, a in enumerate(state.card_def(state.players[1].active.card).attacks) if a.name_ja == "バリアー")
    done = finish(attack(state, index, player=1))
    assert done.current_player == 0 and done.phase is Phase.MAIN, done.phase
    return done


# ---------------------------------------------------------------- 5 章: はかいのほのお


class DestructiveFireTest(unittest.TestCase):
    def test_no_fire_cards_is_rejected_without_change(self):
        state = board((D, W, W, W))
        attacker = state.players[0].active
        problem = E.DEFAULT_EFFECTS.attack_entry(TYR, 1).effect.usage_problem(state, attacker)
        self.assertEqual(problem.code, E.NO_TYPED_ENERGY_CARDS_CODE)
        before = fingerprint(state)
        # 必要なエネルギーとは別の確かめであることだけを見る
        with mock.patch.object(checks, "attack_cost_payable", return_value=True), self.assertRaises(IllegalActionError) as caught:
            attack(state, 1)
        self.assertEqual(caught.exception.code, E.NO_TYPED_ENERGY_CARDS_CODE)
        self.assertEqual(fingerprint(state), before)

    def test_ambiguous_color_defers_to_existing_stop(self):
        state = board((D, HP.RAINBOW_ENERGY, HP.RAINBOW_ENERGY, HP.RAINBOW_ENERGY))
        self.assertIsNone(E.typed_energy_card_usage_problem(state, state.players[0].active, E.EnergyType.FIRE))
        before = fingerprint(state)
        with self.assertRaises(UnsupportedError) as caught:
            attack(state, 1)
        self.assertEqual(caught.exception.code, "UNRESOLVED_RAINBOW_ENERGY_TYPE")
        self.assertEqual(fingerprint(state), before)

    def test_zero_heads_succeeds(self):
        state = board(DF)
        done = attack(state, 1, TL, TL, TL)
        self.assertEqual(done.phase, Phase.MAIN)
        self.assertEqual(since(state, done, "discard_energy", "discard_attached_energy", E.USER_RULE_COUNT_SHORT_EVENT), [])
        self.assertEqual([(e["steps"][0][1], e["amount"]) for e in since(state, done, "damage")], [(50, 60)])  # 50 は基本となる数（悪エネルギーで 60）
        audited(self, done, snapshots_for(state, 1))

    def test_order_and_opponent_counts(self):
        for fire, heads, opp, opp_discards in ((3, 1, 3, 1), (3, 2, 2, 2), (3, 3, 1, 1), (3, 3, 0, 0), (4, 2, 3, 2)):
            with self.subTest(fire=fire, heads=heads, opp=opp):
                state = board((D,) + (F,) * fire, opponent_energy=(W,) * opp)
                done = finish(attack(state, 1, *((HD,) * heads + (TL,) * (fire - heads))))
                kinds = [e["kind"] for e in since(state, done) if e["kind"] in ("discard_energy", "damage", "discard_attached_energy")]
                self.assertEqual(kinds, ["discard_energy"] * heads + ["damage"] + ["discard_attached_energy"] * opp_discards)
                self.assertEqual(len([u for u in done.players[0].active.energy if done.cards[u].card_id == F]), fire - heads)
                shorts = since(state, done, E.USER_RULE_COUNT_SHORT_EVENT)
                self.assertEqual([(e["required"], e["available"], e["processed"]) for e in shorts], [(heads, opp, opp)] if heads > opp else [])
                audited(self, done, snapshots_for(state, 1))

    def test_choices_keep_all_combinations(self):
        state = board((D, F, F, F, F), opponent_energy=(W, W, W, DCE))
        asked = attack(state, 1, HD, HD, TL, TL)
        d = asked.decision
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices, len(d.options)), (DISCARD_ENERGY, 0, 2, 2, 4))
        self.assertEqual(len(P.DiscardOwnTypedEnergyByHeads(E.EnergyType.FIRE, heads_of="coin").dry_choices(mock.Mock(state=asked, attacker=lambda: asked.players[0].active), d)), 1)
        mine = answer(asked, (d.options[1], d.options[3]))
        e = mine.decision
        self.assertEqual((e.kind, e.min_choices, len(e.options)), (DISCARD_OPPONENT_ENERGY, 2, 4))
        dce = next(u for u in e.options if mine.cards[u].card_id == DCE)
        done = answer(mine, (dce, e.options[0]))  # 特殊エネルギーも 1 枚のエネルギーカード
        self.assertNotIn(dce, done.players[1].active.energy)
        self.assertEqual(len(done.players[1].active.energy), 2)
        self.assertEqual({u for x in since(asked, mine, "discard_energy") for u in (x["energy"],)}, {d.options[1], d.options[3]})
        audited(self, done)

    def test_damage_only_protection(self):
        state = board(DF, opponent_energy=(W, W), prevent_damage=True)
        done = finish(attack(state, 1, HD, HD, TL))
        self.assertEqual(done.players[1].active.damage, 0)
        self.assertEqual(len(since(state, done, "discard_energy")), 2)
        self.assertEqual(len(since(state, done, "discard_attached_energy")), 2)  # 効果は受ける
        audited(self, done, snapshots_for(state, 1))

    def test_effect_protection_keeps_own_discard(self):
        state = barrier_board()
        done = finish(attack(state, 1, HD, HD, TL))
        self.assertEqual(len([e for e in since(state, done, "coin_flip") if e.get("effect") == f"{TYR}#1"]), 3)  # コインは投げる
        self.assertEqual(len(since(state, done, "discard_energy")), 2)  # 自分の炎は捨てる
        self.assertEqual(since(state, done, "discard_attached_energy"), [])  # 相手のトラッシュは防がれる
        self.assertEqual(done.players[1].active.damage, 0)
        audited(self, done)

    def test_copy_counts_the_copiers_cards(self):
        state = build_test_state([{"active": {"card": HP.CLEFAIRY, "energy": [F, W, W]}, "deck": [F] * 10, "prizes": 6},
                                  {"active": {"card": TYR, "energy": list(DF)}, "deck": [W] * 3, "prizes": 6}])
        asked = attack(state, metronome_index(state), HD, TL, TL, TL)
        self.assertEqual(asked.decision.options, (0, 1))
        done = finish(answer(asked, (1,), HD))
        coins = [e for e in since(asked, done, "coin_flip") if e.get("effect") == f"{TYR}#1"]
        self.assertEqual(len(coins), 1)  # まねるピッピの「炎」エネルギーカード 1 枚
        own = since(asked, done, "discard_energy")
        self.assertEqual([state.cards[e["energy"]].owner for e in own], [0])
        self.assertEqual(len(since(asked, done, "discard_attached_energy")), 1)
        audited(self, done)

    def test_esp_replaces_only_the_coins(self):
        from tests.test_variable_coins_search_attachments_v0_113 import (
            esp_board,
            mon,
            provider_card,
        )

        state = esp_board(TYR, DF, opponent=mon(HP.CHANSEY, (W,)))
        asked = attack(state, 1, HD, HD, TL, card=provider_card(state, TYR))
        self.assertEqual(asked.decision.kind, ESP_REDO)
        self.assertEqual(since(state, asked, "discard_energy", "damage"), [])  # トラッシュ・ダメージはやり直しの答えのあと
        for redo, coins, own in (((), (), 2), ((1,), (TL, TL, TL), 0), ((1,), (HD, HD, HD), 3)):
            with self.subTest(redo=redo, coins=coins):
                done = finish(answer(asked, redo, *coins))
                self.assertEqual(len(since(asked, done, "discard_energy")), own)
                self.assertEqual(len(since(asked, done, "damage")), 1)
                self.assertEqual(len(since(asked, done, "discard_attached_energy")), min(own, 1))
                audited(self, done)


# ---------------------------------------------------------------- 7 章: 保存・不正な答え・観測


class PersistenceAndAnswersTest(unittest.TestCase):
    def setUp(self):
        self.state = attack(board(DF, opponent_energy=(W, W, W)), 1, HD, HD, TL)

    def test_save_and_restore_at_the_decision(self):
        d = self.state.decision
        expected = state_to_dict(finish(answer(self.state, d.options[:2])), max(FORMAT_VERSIONS))
        for restored in (pickle.loads(pickle.dumps(self.state)), copy.deepcopy(self.state), self.state.clone()):
            self.assertEqual(state_to_dict(restored, max(FORMAT_VERSIONS)), state_to_dict(self.state, max(FORMAT_VERSIONS)))
            for version in [v for v in FORMAT_VERSIONS if v >= 2]:  # 形式 1 はワザの途中の決定を表せない（既存の制限）
                data = state_to_dict(restored, version)
                self.assertEqual(data["decision"]["kind"], DISCARD_ENERGY)  # 古い形式でも決定を落とさない
            self.assertEqual(state_to_dict(finish(answer(restored, d.options[:2])), max(FORMAT_VERSIONS)), expected)
        mine = answer(self.state, d.options[:2])
        heads = dict(mine.decision.context)["heads"]
        self.assertEqual(heads, 2)  # 決定をまたいで「おもて」の数を持つ
        self.assertEqual(state_to_dict(mine, 33)["decision"]["context"]["heads"], 2)

    def test_invalid_answers_are_rejected_without_change(self):
        d = self.state.decision
        for command in (ResolveDecision(1, d.id, d.options[:2]), ResolveDecision(0, d.id + 1, d.options[:2]), ResolveDecision(0, d.id, d.options[:1]),
                        ResolveDecision(0, d.id, d.options[:3]), ResolveDecision(0, d.id, (999, d.options[0])), ResolveDecision(0, d.id, (d.options[0], d.options[0])),
                        EndTurn(0)):
            with self.subTest(command=command):
                before = fingerprint(self.state)
                with self.assertRaises(IllegalActionError):
                    apply_command(self.state, command)
                self.assertEqual(fingerprint(self.state), before)
        mine = answer(self.state, d.options[:2])
        e = mine.decision
        before = fingerprint(mine)
        with self.assertRaises(IllegalActionError):
            apply_command(mine, ResolveDecision(0, e.id, tuple(u for u in mine.players[0].active.energy)[:2]))  # 自分のカードは相手のトラッシュに選べない
        self.assertEqual(fingerprint(mine), before)

    def test_observation(self):
        done = finish(attack(board(DF, opponent_energy=(W,)), 1, HD, HD, HD))
        self.assertEqual(observation_problems(self.state), [])
        self.assertEqual(observation_problems(done), [])
        for viewer in (0, 1, None):
            shown = [e for e in visible_log(done, viewer) if e["kind"] == E.USER_RULE_COUNT_SHORT_EVENT]
            self.assertEqual([(e["required"], e["available"], e["processed"]) for e in shown], [(3, 1, 1)])


# ---------------------------------------------------------------- 8 章: 監査


class AuditTamperingTest(unittest.TestCase):
    def setUp(self):
        self.crush_before = board(deck=2)
        self.crush = attack(self.crush_before, 0, *run(3))
        self.fire_before = board(DF, opponent_energy=(W,))
        self.fire = finish(attack(self.fire_before, 1, HD, HD, TL))

    @staticmethod
    def tampered(state, change):
        s = state.clone()
        log = [dict(e) for e in s.log]
        change(log)
        s.log = log
        return s

    def index(self, state, kind, start=0):
        return next(i for i, e in enumerate(state.log) if i >= start and e["kind"] == kind)

    def test_real_logs_pass(self):
        self.assertEqual(v133_problems(self.crush, snapshots_for(self.crush_before, 0)), [])
        self.assertEqual(v133_problems(self.fire, snapshots_for(self.fire_before, 1)), [])

    def test_each_tampering_is_found(self):
        crush, fire = self.crush, self.fire
        start = len(self.crush_before.log)
        mill, short = self.index(crush, "discard_from_deck", start), self.index(crush, E.USER_RULE_COUNT_SHORT_EVENT, start)
        coin, damage = self.index(crush, "coin_flip", start), self.index(crush, "damage", start)
        fstart = len(self.fire_before.log)
        own, fdamage, opp = self.index(fire, "discard_energy", fstart), self.index(fire, "damage", fstart), self.index(fire, "discard_attached_energy", fstart)
        fshort = self.index(fire, E.USER_RULE_COUNT_SHORT_EVENT, fstart)
        cases = {
            "crush: no short record": (crush, lambda log: log.pop(short), 0),
            "crush: extra card": (crush, lambda log: log[mill].update(cards=tuple(log[mill]["cards"]) + (crush.players[1].discard[0],)), 0),
            "crush: coin before damage": (crush, lambda log: log.insert(damage, log.pop(coin)), 0),
            "crush: capped coins": (crush, lambda log: log.__setitem__(coin + 2, dict(log[coin + 2], result="tails")), 0),
            "crush: immediate deck out": (crush, lambda log: log.insert(short + 1, {"kind": "deck_out", "turn": 3, "player": 1}), 0),
            "crush: lost a card": (crush, lambda log: log[mill].update(cards=tuple(log[mill]["cards"])[:1]), 0),
            "fire: missing own discard": (fire, lambda log: log.pop(own), 1),
            "fire: damage before own discard": (fire, lambda log: log.insert(own, log.pop(fdamage)), 1),
            "fire: opponent discard before damage": (fire, lambda log: log.insert(fdamage, log.pop(opp)), 1),
            "fire: no short record": (fire, lambda log: log.pop(fshort), 1),
            "fire: wrong coin": (fire, lambda log: log.__setitem__(self.index(fire, "coin_flip", fstart), dict(log[self.index(fire, "coin_flip", fstart)], result="tails")), 1),
        }
        for label, (state, change, index) in cases.items():
            with self.subTest(label):
                before = self.crush_before if state is crush else self.fire_before
                self.assertTrue(v133_problems(self.tampered(state, change), snapshots_for(before, index)), label)

    def test_development_game_passes_and_tampering_is_found(self):
        """開発用の seed（91。正式な対戦には数えない）の X133 対 W28 の実際の対戦が、やり直しの状態の数を渡した監査を通り、ログを誤らせると見つかる。"""
        from tests.log_audit import log_problems
        from tools import existing_effect_games as G

        result = G.play(("X133", "W28"), 91, keep_state=True)
        self.assertEqual(result["audit"], {})
        state = result["state"]
        self.assertTrue(result["v133"].get("crush") or result["v133"].get("fire"))
        self.assertEqual(log_problems(state), [])
        mills = [i for i, e in enumerate(state.log) if e["kind"] == "discard_from_deck" and str(e.get("effect", "")).startswith(TYR)]
        discards = [i for i, e in enumerate(state.log) if e["kind"] == "discard_energy" and str(e.get("effect", "")).startswith(TYR)]
        self.assertTrue(mills or discards)
        target = (mills or discards)[0]
        self.assertTrue(v133_problems(self.tampered(state, lambda log: log.pop(target))))

    def test_snapshot_mismatch_is_found(self):
        wrong = {len(self.crush_before.log): (0, 9, 0, 2)}  # 宣言の前の山札が 9 枚なら 3 枚トラッシュのはず
        self.assertTrue(v133_problems(self.crush, wrong))
        zero = {len(self.fire_before.log): (0, 5, 0, 1)}  # 炎 0 枚で受け付けた
        self.assertTrue(v133_problems(self.fire, zero))


class DocumentTest(unittest.TestCase):
    def test_document_states_the_limits(self):
        text = DOC.read_text(encoding="utf-8")
        for phrase in ("利用者の指定", "公式の裁定ではない", "UQ-STATED-COUNT-SHORT", "UQ-DESTRUCTIVE-FIRE-FAILURE", "UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY", "HC9",
                       "kyuura への報告事項", "4,096", "512"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()

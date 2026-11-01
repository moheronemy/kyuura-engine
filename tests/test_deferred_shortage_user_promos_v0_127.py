"""v0.127（docs/deferred-shortage-user-promos-v0.127.md）: 枚数不足の途中停止と、利用者指定の簡略ルールのプロモ 3 枚。

- 途中停止の基盤（5 章）: 共通の数量処理のチェック地点だけが、実際のコインとそこまでの処理を残した終端の状態を返す（従来の拒否と分ける）
- ファイヤー（ドライアップ）・怪電波マシーン（7 章）: H ≤ N の通常の経路、H > N の途中停止（DU1・TW1）、使う前の停止（TW2）
- 利用者が指定した簡略ルール（4 章）: _のピカチュウの誕生日の条件・ハマちゃんのヤドキングの発話の条件を省く（公式の裁定ではない）
- 先読み・ナツメのESP（6 章）、保存・不変条件・監査（8 章）

盤面は 1 か所の規定を確かめるために直接作ったもので、``new_game`` からの自然な対戦の結果ではない（正式な対戦は 12 章）。
"""

from __future__ import annotations

import copy
import json
import pathlib
import pickle
import unittest
from types import MappingProxyType
from unittest import mock

from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import (
    EndTurn,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UseAttack,
)
from kyuura_engine.decisions import (
    DISCARD_OPPONENT_ENERGY,
    ESP_REDO,
    RETURN_ENERGY,
    SELECT_POKEMON,
)
from kyuura_engine.engine import apply_command, check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.interruption import DeferredShortage, check_quantity
from kyuura_engine.observation import observe
from kyuura_engine.resolution import programs as P
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import Phase
from scripts import check_card_sources as cs
from tests import helpers as HP
from tests.helpers import build_test_state, with_coin_bits
from tests.log_audit import log_problems, observation_problems, serialization_problems
from tests.release_catalog import cards_after

ROOT = pathlib.Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
LINKS_PATH = ROOT / "kyuura_engine" / "data" / "research_links.json"
DOC = ROOT / "docs" / "deferred-shortage-user-promos-v0.127.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
MOLTRES, MOLTRES_QSG, TWM, PIKACHU, PIKACHU_B, SLOWKING = "ES2-005", "QSG-055", "neo4-108", "PR1-044", "PR1-090", "PR1-072"
NEW_CARDS = (MOLTRES, MOLTRES_QSG, TWM, PIKACHU, PIKACHU_B, SLOWKING)
SLOWPOKE, CHANSEY, MAGIKARP, SNORLAX = "PMCG3-027", HP.CHANSEY, HP.MAGIKARP, HP.SNORLAX
FIRE, WATER, LIGHTNING, PSYCHIC = HP.FIRE, HP.WATER, HP.LIGHTNING, HP.PSYCHIC
CODES = {"DU1": E.DRY_UP_SHORT_CODE, "TW1": E.THOUGHT_WAVE_SHORT_CODE, "TW2": E.THOUGHT_WAVE_WITHOUT_TARGET_CODE}


def run(heads: int) -> tuple[CoinSide, ...]:
    return (HD,) * heads + (TL,)


def fingerprint(state):
    return (repr(state_to_dict(state, format_version=max(FORMAT_VERSIONS))), state.rng.getstate(), len(state.log))


def dry_board(water=2, *, bench=(), hand=()):
    """ファイヤー（炎 2 個）対 ラッキー（「水」エネルギーカード ``water`` 枚）。``bench`` は相手の控えのラッキーの「水」の枚数。"""
    return build_test_state([
        {"active": {"card": MOLTRES, "energy": [FIRE, FIRE]}, "hand": list(hand), "deck": [FIRE] * 10, "prizes": 6},
        {"active": {"card": CHANSEY, "energy": [WATER] * water}, "bench": [{"card": CHANSEY, "energy": [WATER] * n} for n in bench], "deck": [WATER] * 10, "prizes": 6},
    ])


def declare(state, coins=()):
    return apply_command(with_coin_bits(state, *coins) if coins else state, UseAttack(state.current_player, 0))


def choose(state, pokemon_id, coins=()):
    d = state.decision
    return apply_command(with_coin_bits(state, *coins) if coins else state, ResolveDecision(d.player, d.id, (pokemon_id,)))


def dry_up(state, heads, target=None):
    asked = declare(state)
    return choose(asked, target if target is not None else asked.players[1].active.pokemon_id, run(heads))


def twm_board(energy=2, *, opponent_energy=None):
    return build_test_state([
        {"active": {"card": CHANSEY, "energy": [FIRE]}, "hand": [TWM], "deck": [FIRE] * 10, "prizes": 6},
        {"active": {"card": CHANSEY, "energy": opponent_energy if opponent_energy is not None else [WATER] * energy}, "deck": [WATER] * 10, "prizes": 6},
    ])


def play_twm(state, heads):
    card = HP.uids(state, 0, "hand", TWM)[0]
    return apply_command(with_coin_bits(state, *run(heads)), PlayTrainer(0, card))


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


# ---------------------------------------------------------------- 2〜3 章: 登録・写し・記録


class RegistrationTest(unittest.TestCase):
    def test_pool_and_counts(self):
        extract = read_extract()
        self.assertEqual(extract["pool_v0_127"], list(NEW_CARDS))
        playable = load_card_pool().playable_ids
        self.assertLessEqual(set(NEW_CARDS), playable)
        # 6 枚を外すと基点の 1,362 枚（v0.129: 後の版で加えたカード pool_v0_129 も外す。v0.130: 後の版のカードは cards_after でまとめて外す）
        self.assertEqual(len(playable - set(NEW_CARDS) - cards_after(extract, "0.127")), 1362)
        self.assertNotIn("neo4-082", playable)  # 10 章: ひかるバンギラスは登録しない
        registry = E.DEFAULT_EFFECTS
        attacks = [k for k in registry.attack_keys() if k.card_id in NEW_CARDS]
        self.assertEqual(len(attacks), 8)
        self.assertEqual([c for c in NEW_CARDS if registry.trainer_entry(c) is not None], [TWM])
        self.assertFalse([k for k in registry.power_keys() if k.card_id in NEW_CARDS])

    def test_entries(self):
        registry = E.DEFAULT_EFFECTS
        for card in (MOLTRES, MOLTRES_QSG):
            entry = registry.attack_entry(card, 0)
            self.assertIsInstance(entry.effect, E.ChooseOpponentThenDiscardTypedEnergyUntilTails)
            self.assertEqual((entry.name_ja, entry.play_text_ja, entry.source), ("ドライアップ", E.DRY_UP_LATEST_TEXT, f"LD-{card}-ATK0"))
            self.assertEqual(entry.text_ja, load_card_pool().get(card).attacks[0].text_ja)
            self.assertIs(registry.attack_entry(card, 1).effect, E.DAMAGE_ONLY)
        self.assertEqual(registry.attack_entry(MOLTRES, 0).effect, registry.attack_entry(MOLTRES_QSG, 0).effect)  # 効果の値は同じ（出典は id ごと）
        self.assertEqual(registry.attack_entry(PIKACHU_B, 0), registry.attack_entry(PIKACHU, 0))  # 登録の値を共有（採用の記録は id ごと）
        trainer = registry.trainer_entry(TWM)
        self.assertIsInstance(trainer.effect, E.CoinsUntilTailsReturnOpponentActiveEnergyThenEndTurn)
        self.assertEqual((trainer.text_ja, trainer.play_text_ja, trainer.source), (E.THOUGHT_WAVE_MACHINE_TEXT, E.THOUGHT_WAVE_MACHINE_TEXT, "kyuura data/cards.json"))
        self.assertEqual(load_card_pool().get(TWM).trainer_text_ja, E.THOUGHT_WAVE_MACHINE_TEXT)

    def test_programs(self):
        self.assertEqual(P.BUILDERS[E.ChooseOpponentThenDiscardTypedEnergyUntilTails](E.ChooseOpponentThenDiscardTypedEnergyUntilTails()),
                         (P.ChooseEffectTarget(side=E.TARGET_SIDE_OPPONENT, scope=E.TARGET_IN_PLAY, chooser=E.CHOOSER_ATTACKER),
                          P.DiscardChosenTypedEnergyUntilTails(energy_type=E.EnergyType.WATER)))
        # 利用者の簡略ルールの型は、既存の型と同じ要素の並びに展開する
        self.assertEqual(P.BUILDERS[E.UserSimplifiedCoinBonusDamage](E.UserSimplifiedCoinBonusDamage(50)), P.BUILDERS[E.CoinBonusDamage](E.CoinBonusDamage(50)))
        self.assertEqual(P.BUILDERS[E.UserSimplifiedStatusSelfAndOpponent](E.UserSimplifiedStatusSelfAndOpponent()),
                         P.BUILDERS[E.StatusSelfAndOpponent](E.StatusSelfAndOpponent(E.CONFUSION)))
        self.assertEqual(P.BUILDERS[E.UserSimplifiedDamageOnly](E.UserSimplifiedDamageOnly()), P.BUILDERS[E.DamageOnly](E.DamageOnly()))

    def test_research_cases_are_bound_to_stop_codes(self):
        links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
        cases = {(c["kyuura_issue"], c["card_id"], c["target"]): c["engine"] for c in links["kyuura_cases_without_engine_ruling"]["cases"]}
        self.assertEqual(cases[("UQ-STATED-COUNT-SHORT", MOLTRES, "attack/0")], {"stop_codes": [CODES["DU1"]]})
        self.assertEqual(cases[("UQ-STATED-COUNT-SHORT", MOLTRES_QSG, "attack/0")], {"stop_codes": [CODES["DU1"]]})
        self.assertEqual(cases[("UQ-STATED-COUNT-SHORT", TWM, "trainer")], {"stop_codes": [CODES["TW1"]]})
        self.assertEqual(cases[("UQ-CARD-USE-WITHOUT-TARGET", TWM, "trainer")], {"stop_codes": [CODES["TW2"]]})
        self.assertEqual(cases[("UQ-STATED-COUNT-SHORT", "neo4-082", "attack/0")], {"unregistered": True})
        for short, code in CODES.items():
            self.assertEqual(links["stop_codes"][code]["engine_rulings"], [{"version": "v0.127", "document": "docs/deferred-shortage-user-promos-v0.127.md", "ruling_id": short}])
        section = links["latest_descriptions"]
        self.assertEqual((section["registered"][f"{MOLTRES}/attack/0"], section["registered"][f"{MOLTRES_QSG}/attack/0"]), ("LD-ES2-005-ATK0", "LD-QSG-055-ATK0"))
        self.assertEqual(section["kyuura_records_not_registered"], [])
        self.assertEqual(section["user_simplified_text"], {key: E.USER_SIMPLIFICATION_SOURCE for key in E.USER_SIMPLIFICATIONS})
        self.assertFalse(set(section["user_simplified_text"]) & set(section["adopted_printed_text"]))


# ---------------------------------------------------------------- 4 章: 利用者が指定した簡略ルール


class UserSimplificationRecordTest(unittest.TestCase):
    def test_records(self):
        self.assertEqual(set(E.USER_SIMPLIFICATIONS), {"PR1-044/attack/0", "PR1-090/attack/0", "PR1-072/attack/0", "PR1-072/attack/1"})
        pool = load_card_pool()
        for key, record in E.USER_SIMPLIFICATIONS.items():
            card, _, index = key.split("/")
            with self.subTest(key=key):
                entry = E.DEFAULT_EFFECTS.attack_entry(card, int(index))
                self.assertEqual(record.printed_text, pool.get(card).attacks[int(index)].text_ja)  # kyuura の印刷の文面のまま
                self.assertEqual((entry.text_ja, entry.play_text_ja, entry.source), (record.printed_text, record.play_text, E.USER_SIMPLIFICATION_SOURCE))
                self.assertNotEqual(record.printed_text, record.play_text)
                self.assertEqual((record.specified_by, record.specified_on), ("user", "2026-11-01"))
                self.assertTrue(record.omitted and record.processing and record.instruction)
                self.assertIn(f"「{record.play_text}」", DOC.read_text(encoding="utf-8"))
        self.assertEqual(E.USER_INSTRUCTIONS[E.USER_BIRTHDAY_COIN_ONLY], "のピカチュウについては誕生日の確認をせずに通常のコイントスのみ")
        self.assertEqual(E.USER_INSTRUCTIONS[E.USER_SPOKEN_CONDITION_IGNORED], "ハマちゃんのヤドキングに関しては発話要件を無視して実装")
        self.assertIn("誕生日", E.USER_SIMPLIFICATIONS["PR1-044/attack/0"].omitted)
        self.assertNotIn("誕生日", E.BIRTHDAY_PLAY_TEXT)  # 「いつも誕生日」と書かない（条件を省く）
        self.assertNotIn("つぶや", E.TROUBLED_PLAY_TEXT)

    def test_types_only_accept_their_records(self):
        pool = load_card_pool()
        pikachu, slowking = pool.get(PIKACHU).attacks[0], pool.get(SLOWKING).attacks
        self.assertEqual(E.UserSimplifiedCoinBonusDamage(50).check(pikachu), [])
        self.assertTrue(E.UserSimplifiedCoinBonusDamage(60).check(pikachu))  # 型の値が記録と違う
        self.assertTrue(E.CoinBonusDamage(50).check(pikachu))  # 既存の型は誕生日の条件つきの文面を受け付けない（簡略化を一般の型に紛れ込ませない）
        self.assertEqual(E.UserSimplifiedStatusSelfAndOpponent().check(slowking[0]), [])
        self.assertTrue(E.UserSimplifiedStatusSelfAndOpponent(E.SLEEP).check(slowking[0]))
        self.assertTrue(E.StatusSelfAndOpponent(E.CONFUSION).check(slowking[0]))
        self.assertEqual(E.UserSimplifiedDamageOnly().check(slowking[1]), [])
        other = pool.get(HP.PIKACHU).attacks[1]  # 記録のない別のワザ
        for effect in (E.UserSimplifiedCoinBonusDamage(50), E.UserSimplifiedStatusSelfAndOpponent(), E.UserSimplifiedDamageOnly()):
            self.assertTrue(effect.check(other), type(effect).__name__)

    def test_check_rejects_a_confused_adoption(self):
        """原文と処理の文面・根拠の種類を取り違えた採用の記録・登録を、検査が拒否する。"""
        sources, links = cs.load_sources(), cs.load_links()
        cards = {c["id"]: c for c in read_extract()["cards"]}
        entry = E.DEFAULT_EFFECTS.attack_entry(PIKACHU, 0)
        key = "PR1-044/attack/0"
        adopted = set(links["latest_descriptions"]["adopted_printed_text"])
        self.assertEqual(cs.user_simplification_problems("x", key, entry, cards[PIKACHU], "attack/0", links, adopted), [])
        swapped = mock.Mock(effect=entry.effect, source=entry.source, text_ja=entry.play_text_ja, play_text_ja=entry.text_ja)  # 原文と処理の文面を入れかえた
        self.assertTrue(cs.user_simplification_problems("x", key, swapped, cards[PIKACHU], "attack/0", links, adopted))
        self.assertTrue(cs.user_simplification_problems("x", key, entry, cards[PIKACHU], "attack/0", links, adopted | {key}))  # 印刷の文面の採用と偽る
        wrong_value = mock.Mock(effect=E.UserSimplifiedCoinBonusDamage(60), source=entry.source, text_ja=entry.text_ja, play_text_ja=entry.play_text_ja)
        self.assertTrue(cs.user_simplification_problems("x", key, wrong_value, cards[PIKACHU], "attack/0", links, adopted))
        no_record = dict(E.USER_SIMPLIFICATIONS)
        del no_record[key]
        with mock.patch.object(E, "USER_SIMPLIFICATIONS", MappingProxyType(no_record)):
            self.assertTrue(cs.user_simplification_problems("x", key, entry, cards[PIKACHU], "attack/0", links, adopted))
        broken = copy.deepcopy(sources)
        broken["cards"][PIKACHU]["play_text"]["attack/0"] = "kyuura_printed_text"  # 利用者の指定を印刷の文面の採用と書いた
        self.assertTrue([p for p in cs.problems(broken) if PIKACHU in p])


class PromoTest(unittest.TestCase):
    """4.2 節: 誕生日・発話の条件を省いた通常のワザ。日付・発話の入力はない。"""

    def pikachu_board(self, card=PIKACHU, opponent=CHANSEY):
        return build_test_state([{"active": {"card": card, "energy": [LIGHTNING, LIGHTNING]}, "deck": [LIGHTNING] * 5, "prizes": 6},
                                 {"active": opponent, "deck": [WATER] * 5, "prizes": 6}])

    def damage(self, before, after):
        return [e["amount"] for e in after.log[len(before.log):] if e["kind"] == "damage"]

    def test_birthday_coin_every_day(self):
        for card in (PIKACHU, PIKACHU_B):
            for side, expected in ((HD, 80), (TL, 30)):
                with self.subTest(card=card, side=side):
                    state = self.pikachu_board(card)
                    after = apply_command(with_coin_bits(state, side), UseAttack(0, 0))
                    coins = [e for e in after.log[len(state.log):] if e["kind"] == "coin_flip"]
                    self.assertEqual([(c["source"], c["result"], c["count"]) for c in coins], [("attack", side.value, 1)])
                    self.assertEqual(self.damage(state, after), [expected])
                    audited(self, after)
        with mock.patch("datetime.date") as dates:  # 日付・時計を読まない
            after = apply_command(with_coin_bits(self.pikachu_board(), HD), UseAttack(0, 0))
            dates.today.assert_not_called()
        self.assertEqual(self.damage(self.pikachu_board(), after), [80])

    def test_birthday_weakness_and_esp_copy(self):
        state = self.pikachu_board(opponent=MAGIKARP)  # 弱点 雷 ×2
        after = apply_command(with_coin_bits(state, TL), UseAttack(0, 0))
        self.assertEqual(self.damage(state, after), [60])
        from tests.test_variable_coins_search_attachments_v0_113 import (
            esp_board,
            mon,
            provider_card,
        )

        esp = esp_board(PIKACHU, (LIGHTNING, LIGHTNING), opponent=mon(MAGIKARP))  # ナツメのフーディン（超）が［サイコリンク］で使う（ESPのやり直しの対象。コイキングは超に弱点・抵抗力なし）
        asked = apply_command(with_coin_bits(esp, TL), UseAttack(0, 0, card=provider_card(esp, PIKACHU)))
        self.assertEqual(asked.decision.kind, ESP_REDO)
        redone = apply_command(with_coin_bits(asked, HD), ResolveDecision(0, asked.decision.id, (1,)))
        self.assertEqual(self.damage(asked, redone), [80])  # 使い手がほかのポケモンでも同じ簡略化（持ち主・日付で分けない）

    def slowking_board(self, energy=(PSYCHIC, PSYCHIC), opponent=MAGIKARP, confused=False):
        return build_test_state([{"active": {"card": SLOWKING, "evolved_from": SLOWPOKE, "energy": list(energy), "confusion": confused}, "deck": [PSYCHIC] * 5, "prizes": 6},
                                 {"active": opponent, "deck": [WATER] * 5, "prizes": 6}])

    def test_troubled_confuses_both_without_speech(self):
        state = self.slowking_board()
        after = apply_command(state, UseAttack(0, 0))
        self.assertTrue(after.players[0].active.conditions.confused and after.players[1].active.conditions.confused)
        self.assertEqual(self.damage(state, after), [])
        self.assertEqual([e["player"] for e in after.log[len(state.log):] if e["kind"] == "special_condition"], [0, 1])  # 自分 → 相手
        smack = apply_command(state, UseAttack(0, 1))
        self.assertEqual(self.damage(state, smack), [20])
        audited(self, after)

    def test_normal_rules_remain(self):
        immune = self.slowking_board(opponent=SNORLAX)  # ［めんえき］: 相手への効果は防がれても、自分はこんらん
        after = apply_command(immune, UseAttack(0, 0))
        self.assertTrue(after.players[0].active.conditions.confused)
        self.assertFalse(after.players[1].active.conditions.confused)
        self.assertIn("special_condition_prevented", [e["kind"] for e in after.log[len(immune.log):]])
        with self.assertRaises(IllegalActionError):
            apply_command(self.slowking_board(energy=()), UseAttack(0, 0))  # コストは通常どおり
        confused = self.slowking_board(confused=True)
        failed = apply_command(with_coin_bits(confused, TL), UseAttack(0, 1))  # こんらんの宣言の前のコインは通常どおり
        kinds = [e["kind"] for e in failed.log[len(confused.log):]]
        self.assertIn("confusion_check", kinds)
        self.assertIn("confusion_damage", kinds)  # 自分にダメージ（ワザは処理しない）
        self.assertEqual(self.damage(confused, failed), [])

    def test_copied_troubled_confuses_the_user_not_the_provider(self):
        from tests import test_variable_coins_search_attachments_v0_113 as V113

        with mock.patch.dict(V113.BELOW, {SLOWKING: [SLOWPOKE]}):  # 控えのハマちゃんのヤドキングはヤドンから進化している
            state = V113.esp_board(SLOWKING, (PSYCHIC, PSYCHIC), opponent=V113.mon(MAGIKARP))
        provider_card = V113.provider_card
        after = apply_command(state, UseAttack(0, 0, card=provider_card(state, SLOWKING)))
        provider = next(p for p in after.players[0].bench if after.cards[p.card].card_id == SLOWKING)
        self.assertTrue(after.players[0].active.conditions.confused)
        self.assertFalse(provider.conditions.names())
        self.assertTrue(after.players[1].active.conditions.confused)


# ---------------------------------------------------------------- 5〜6 章: 途中停止の基盤・先読み


class FoundationTest(unittest.TestCase):
    def test_checkpoint_only_raises_on_shortage(self):
        fields = {"code": "UNRESOLVED_X", "message": "m", "references": (), "source": "s", "player": 0, "target_owner": 1, "target": 1,
                  "element": "discard_water_energy_cards", "pending": ("p",)}
        self.assertIsNone(check_quantity(required=2, available=2, **fields))
        self.assertIsNone(check_quantity(required=0, available=0, **fields))
        with self.assertRaises(DeferredShortage) as caught:
            check_quantity(required=3, available=2, **fields)
        self.assertNotIsInstance(caught.exception, UnsupportedError)
        with self.assertRaises(RuntimeError):
            check_quantity(required=3, available=2, **{**fields, "element": "other"})  # 途中停止を許す要素だけ

    def test_terminal_state_keeps_coins_and_rng(self):
        state = declare(dry_board(2))
        before = fingerprint(state)
        coins = run(3)
        rigged = with_coin_bits(state, *coins)
        expected_rng = copy.deepcopy(rigged.rng)
        for _ in coins:
            expected_rng.getrandbits(1)
        after = apply_command(rigged, ResolveDecision(0, state.decision.id, (state.players[1].active.pokemon_id,)))
        self.assertEqual(fingerprint(state), before)  # 渡した状態は変えない
        self.assertIs(after.phase, Phase.HALTED)
        record = after.halt.interruption
        self.assertEqual((record.code, record.required, record.available, record.element, record.in_transit), (CODES["DU1"], 3, 2, "discard_water_energy_cards", ()))
        self.assertEqual(after.rng.getstate(), expected_rng.getstate())  # 実際のコインの乱数の位置
        self.assertEqual([e["result"] for e in after.log if e["kind"] == "coin_flip"], ["heads", "heads", "heads", "tails"])
        self.assertEqual(len(after.players[1].active.energy), 2)  # トラッシュしていない
        self.assertEqual(after.log[-1]["kind"], "halted")
        self.assertIsNone(after.decision)
        audited(self, after)

    def test_conventional_rejection_changes_nothing(self):
        state = twm_board(0)
        before = fingerprint(state)
        with self.assertRaises(UnsupportedError) as caught:
            play_twm(state, 3)
        self.assertEqual(caught.exception.code, CODES["TW2"])
        self.assertEqual(fingerprint(state), before)

    def test_every_command_is_rejected_after_interruption(self):
        halted = play_twm(twm_board(2), 5)
        self.assertIsNotNone(halted.halt.interruption)
        commands = [EndTurn(0), UseAttack(0, 0), PlayTrainer(0, halted.trainer_in_use.card), Retreat(0, (), 1), ResolveDecision(0, 1, ()), EndTurn(1)]
        for command in commands:
            with self.subTest(command=type(command).__name__), self.assertRaises((UnsupportedError, IllegalActionError)):
                apply_command(halted, command)
        for copy_ in (halted.clone(), copy.deepcopy(halted), pickle.loads(pickle.dumps(halted))):
            self.assertEqual(fingerprint(copy_), fingerprint(halted))
            self.assertEqual(copy_.halt, halted.halt)
            with self.assertRaises(UnsupportedError):
                apply_command(copy_, EndTurn(0))

    def test_format_32_and_observation(self):
        halted = dry_up(dry_board(1), 2)
        data = state_to_dict(halted, format_version=32)
        self.assertEqual(data["halt"]["interruption"]["required"], 2)
        self.assertEqual(data["user_simplifications"], [])
        self.assertEqual(max(FORMAT_VERSIONS), 33)  # v0.130: 形式 33（所有者の変更）を加えた。形式 32 の項目は変わらない
        for version in (1, 9, 31):
            with self.assertRaises(ValueError):
                state_to_dict(halted, format_version=version)
        plain = dry_board(1)
        self.assertEqual({k: v for k, v in state_to_dict(plain, format_version=32).items() if k not in ("user_simplifications", "format_version")},
                         {k: v for k, v in state_to_dict(plain, format_version=31).items() if k != "format_version"})
        for viewer in (0, 1, None):
            seen = observe(halted, viewer)
            self.assertEqual(seen["phase"], "halted")
            self.assertEqual(seen["interruption"]["code"], CODES["DU1"])
        self.assertNotIn("interruption", observe(plain, 0))
        promos = build_test_state([{"active": PIKACHU, "deck": [LIGHTNING] * 5, "prizes": 6}, {"active": SLOWKING, "deck": [WATER] * 5, "prizes": 6}])
        self.assertEqual(state_to_dict(promos, format_version=32)["user_simplifications"], ["PR1-044/attack/0", "PR1-072/attack/0", "PR1-072/attack/1"])

    def test_invariants_are_not_relaxed(self):
        halted = play_twm(twm_board(1), 3)
        self.assertEqual(check_invariants(halted), [])
        record = halted.halt.interruption
        tampered = {
            "必要な数": lambda s: setattr(s, "halt", __import__("dataclasses").replace(s.halt, interruption=__import__("dataclasses").replace(record, required=1))),
            "在途のカード": lambda s: setattr(s, "halt", __import__("dataclasses").replace(s.halt, interruption=__import__("dataclasses").replace(record, in_transit=()))),
            "あとのログ": lambda s: setattr(s, "log", s.log + (MappingProxyType({"kind": "turn_end", "turn": s.turn_number, "player": 0}),)),
            "使用中のカードの片付け": lambda s: (setattr(s, "trainer_in_use", None), s.players[0].discard.append(record.in_transit[0])),
            "もどした": lambda s: (s.players[1].hand.append(s.players[1].active.energy.pop())),
        }
        for name, change in tampered.items():
            with self.subTest(name=name):
                broken = copy.deepcopy(halted)
                change(broken)
                self.assertTrue(check_invariants(broken), name)
        normal = copy.deepcopy(halted)
        normal.halt = __import__("dataclasses").replace(normal.halt, interruption=None)  # 通常の停止で使用中のカードが残るのは今までどおり誤り
        self.assertIn("対戦が終わっているのに、使用中のトレーナーが残っている", check_invariants(normal))

    def test_shortage_classes(self):
        for available in (0, 1, 2, 5):
            classes = P.shortage_classes(available)
            self.assertEqual(classes.representatives, tuple(range(available + 2)))
            for heads in range(available + 12):
                self.assertEqual(classes.index_of_heads(heads), min(heads, available + 1))

    def test_representatives_match_small_full_enumeration(self):
        """N = 2 で、実際の「おもて」の数 0〜8 の結果の分類が、代表（0, 1, 2, 3）の分類と同じ（3 以上はどれも同じ途中停止）。"""
        def outcome(heads):
            done = dry_up(dry_board(2), heads)
            if done.decision is not None:
                return ("decision", done.decision.kind, done.decision.min_choices, len(done.decision.options))
            if done.halt is not None:
                r = done.halt.interruption
                return ("interrupted", r.code, r.element, r.available, r.pending, r.in_transit)
            return ("done", len(done.players[1].active.energy))
        representatives = {h: outcome(h) for h in range(4)}
        for heads in range(9):
            self.assertEqual(outcome(heads), representatives[min(heads, 3)])
        self.assertEqual(representatives[0], ("done", 2))
        self.assertEqual(representatives[2], ("done", 0))
        self.assertEqual(representatives[1][:2], ("decision", DISCARD_OPPONENT_ENERGY))
        self.assertEqual(representatives[3][0], "interrupted")


# ---------------------------------------------------------------- 7 章: ドライアップ・怪電波マシーン


class DryUpTest(unittest.TestCase):
    def test_boundaries(self):
        for water in (1, 2, 5):
            for heads in (0, water, water + 1, water + 9):
                with self.subTest(water=water, heads=heads):
                    done = dry_up(dry_board(water), heads)
                    if heads == 0:
                        self.assertEqual((done.phase, len(done.players[1].active.energy)), (Phase.MAIN, water))
                    elif heads == water:
                        self.assertIsNone(done.halt)
                        trashed = [e for e in done.log if e["kind"] == "discard_attached_energy"]
                        self.assertEqual(len(trashed), water)
                    else:
                        record = done.halt.interruption
                        self.assertEqual((record.required, record.available), (heads, water))
                        self.assertEqual(len(done.players[1].active.energy), water)
                        self.assertEqual(done.turn_number, 3)
                    audited(self, done)

    def test_exact_choice_keeps_every_combination(self):
        asked = dry_up(dry_board(4), 2)
        d = asked.decision
        self.assertEqual((d.kind, d.player, d.min_choices, d.max_choices, len(d.options)), (DISCARD_OPPONENT_ENERGY, 0, 2, 2, 4))
        import itertools

        for answer in itertools.combinations(d.options, 2):
            done = apply_command(asked, ResolveDecision(0, d.id, answer))
            self.assertEqual(sorted(set(asked.players[1].active.energy) - set(done.players[1].active.energy)), sorted(answer))
        for wrong in ((d.options[0],), d.options[:3], ()):
            with self.assertRaises(IllegalActionError):
                apply_command(asked, ResolveDecision(0, d.id, wrong))

    def test_target_is_fixed_before_coins_and_zero_water_target(self):
        state = dry_board(0, bench=(3,))
        asked = declare(state)
        self.assertEqual(asked.decision.kind, SELECT_POKEMON)
        self.assertEqual(len(asked.decision.options), 2)  # 水のない対戦ポケモンも選べる（黙って除かない）
        active = asked.players[1].active.pokemon_id
        nothing = choose(asked, active, run(0))
        self.assertEqual(nothing.phase, Phase.MAIN)
        stopped = choose(asked, active, run(1))
        self.assertEqual((stopped.halt.interruption.target, stopped.halt.interruption.available), (active, 0))
        self.assertEqual(len(stopped.players[1].bench[0].energy), 3)  # 控えに選び直さない
        bench = asked.players[1].bench[0].pokemon_id
        self.assertEqual(choose(asked, bench, run(3)).phase, Phase.MAIN)

    def test_ambiguous_water_target_is_selectable_but_stops(self):
        state = build_test_state([
            {"active": {"card": MOLTRES, "energy": [FIRE, FIRE]}, "deck": [FIRE] * 10, "prizes": 6},
            {"active": {"card": CHANSEY, "energy": [WATER]}, "bench": [{"card": CHANSEY, "energy": [HP.RAINBOW_ENERGY]}], "deck": [WATER] * 10, "prizes": 6}])
        asked = declare(state)
        bench = asked.players[1].bench[0].pokemon_id
        self.assertEqual(asked.decision.context_value("unresolved_choices"), (bench,))
        with self.assertRaises(UnsupportedError):
            choose(asked, bench, run(1))

    def test_esp_redo_is_asked_before_the_shortage(self):
        from tests.test_variable_coins_search_attachments_v0_113 import (
            esp_board,
            mon,
            provider_card,
        )

        state = esp_board(MOLTRES, (FIRE, FIRE), opponent=mon(CHANSEY, (WATER, WATER)))
        asked = apply_command(state, UseAttack(0, 0, card=provider_card(state, MOLTRES)))
        flipped = choose(asked, asked.players[1].active.pokemon_id, run(3))
        self.assertEqual((flipped.phase, flipped.decision.kind), (Phase.DECISION, ESP_REDO))  # 最初の H = 3 > N = 2 でも止めない
        redone = apply_command(with_coin_bits(flipped, *run(1)), ResolveDecision(0, flipped.decision.id, (1,)))
        self.assertEqual((redone.decision.kind, redone.decision.min_choices), (DISCARD_OPPONENT_ENERGY, 1))
        kept = apply_command(flipped, ResolveDecision(0, flipped.decision.id, ()))
        self.assertEqual((kept.halt.interruption.required, kept.log[-2]["kind"]), (3, "esp_redo_declined"))
        again = apply_command(with_coin_bits(flipped, *run(4)), ResolveDecision(0, flipped.decision.id, (1,)))
        self.assertEqual((again.halt.interruption.required, again.log[-2]["kind"]), (4, "esp_redo"))
        for done in (redone, kept, again):
            audited(self, done)

    def test_dry_choices_cover_card_kinds(self):
        asked = dry_up(dry_board(12), 5)  # 同じ基本エネルギーカード 12 枚: 先読みは 1 つの組だけ（上限に当たらない）
        element = P.DiscardChosenTypedEnergyUntilTails()
        answers = element.dry_choices(mock.Mock(state=asked), asked.decision)
        self.assertEqual(len(answers), 1)
        self.assertEqual(len(answers[0]), 5)


class ThoughtWaveMachineTest(unittest.TestCase):
    def test_normal_paths_end_the_turn(self):
        for heads in (0, 2):
            with self.subTest(heads=heads):
                state = twm_board(2)
                done = play_twm(state, heads)
                self.assertEqual((done.phase, done.current_player), (Phase.MAIN, 1))  # 番を終えた（H = 0 でも）
                self.assertIn(HP.uids(state, 0, "hand", TWM)[0], done.players[0].discard)
                self.assertEqual(len(done.players[1].active.energy), 2 - heads)
                returned = [e for e in done.log if e["kind"] == "trainer_return_energy"]
                self.assertEqual([len(e["cards"]) for e in returned], [heads] if heads else [])
                self.assertTrue(all(e["player"] == 1 and e["user"] == 0 for e in returned))
                audited(self, done)

    def test_choice_returns_to_opponent_hand(self):
        state = twm_board(3)
        asked = play_twm(state, 1)
        d = asked.decision
        self.assertEqual((d.kind, d.player, d.min_choices, len(d.options)), (RETURN_ENERGY, 0, 1, 3))
        done = apply_command(asked, ResolveDecision(0, d.id, (d.options[2],)))
        self.assertIn(d.options[2], done.players[1].hand)  # 相手の手札（トラッシュではない）
        self.assertNotIn(d.options[2], done.players[1].discard)
        self.assertEqual(done.current_player, 1)

    def test_shortage_keeps_the_trainer_in_transit(self):
        state = twm_board(1)
        card = HP.uids(state, 0, "hand", TWM)[0]
        halted = play_twm(state, 2)
        record = halted.halt.interruption
        self.assertEqual((record.code, record.required, record.available, record.in_transit), (CODES["TW1"], 2, 1, (card,)))
        self.assertEqual(halted.trainer_in_use.card, card)
        self.assertNotIn(card, halted.players[0].discard)
        self.assertEqual((halted.turn_number, halted.current_player, len(halted.players[1].active.energy)), (state.turn_number, 0, 1))
        self.assertNotIn("turn_end", [e["kind"] for e in halted.log])
        audited(self, halted)

    def test_special_energy_counts_as_one_card(self):
        state = twm_board(opponent_energy=[HP.RAINBOW_ENERGY])
        done = play_twm(state, 1)
        self.assertEqual(len(done.players[1].active.energy), 0)
        self.assertIsNone(done.halt)


# ---------------------------------------------------------------- 8 章: 監査


class AuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools import existing_effect_games as games

        cls.interrupted = games.play(("F127", "W28"), 93, keep_state=True)  # 開発用の seed（正式な対戦の seed 0〜3 とは別）
        cls.normal = games.play(("P127", "W28"), 90, keep_state=True)

    def test_real_games_pass(self):
        self.assertEqual(self.interrupted["outcome"], "interrupted")
        self.assertEqual(self.interrupted["audit"], {})
        self.assertEqual(log_problems(self.interrupted["state"]), [])
        self.assertEqual(self.normal["outcome"], "game_over")
        self.assertEqual(self.normal["audit"], {})
        self.assertGreater(self.normal["v127"]["birthday_heads"] + self.normal["v127"]["birthday_tails"], 0)

    def test_tampered_logs_are_found(self):
        done = self.interrupted["state"]
        last_attack = max(i for i, e in enumerate(done.log) if e["kind"] in ("attack", "play_trainer"))
        changes = {
            "あとの番の終わり": lambda log: log + (MappingProxyType({"kind": "turn_end", "turn": done.turn_number, "player": done.current_player}),),
            "途中停止の印を消した": lambda log: log[:-1] + (MappingProxyType({k: v for k, v in log[-1].items() if k != "interrupted"}),),
            "コインを打ち切った": lambda log: tuple(e for i, e in enumerate(log) if not (i > last_attack and e["kind"] == "coin_flip" and e["result"] == "heads"
                                                                                     and i == max(j for j, x in enumerate(log) if x["kind"] == "coin_flip" and x["result"] == "heads"))),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                tampered = done.clone()
                tampered.log = change(done.log)
                self.assertTrue(log_problems(tampered) or check_invariants(tampered), name)


class DocumentTest(unittest.TestCase):
    def test_documents(self):
        doc = DOC.read_text(encoding="utf-8")
        for short, code in CODES.items():
            self.assertIn(f"**{short}**（`{code}`", doc)
        self.assertIn("**途中停止は公式の裁定の解決ではありません。**", doc)
        self.assertIn("**プロモ 3 枚の処理は、利用者が指定した簡略ルールです。**", doc)
        self.assertIn(E.DRY_UP_LATEST_TEXT, doc)
        self.assertRegex((ROOT / "README.md").read_text(encoding="utf-8"), r"\n- v0\.127（(今のエンジンの版。)?`kyuura_engine` の版は 0\.127\.0）: 枚数不足の途中停止")
        self.assertIn("## v0.127: 枚数不足の途中停止と、利用者指定の簡略ルールのプロモ 3 枚\n", (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8"))
        self.assertIn("### v0.127: 枚数不足の途中停止と、利用者指定の簡略ルール", (ROOT / "docs" / "rules-2000-02-14.md").read_text(encoding="utf-8"))
        self.assertIn("## v0.127: 利用者指定の簡略ルールと途中停止", (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

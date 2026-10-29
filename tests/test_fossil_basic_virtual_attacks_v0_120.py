"""v0.120（docs/fossil-basic-virtual-attacks-v0.120.md）: 化石の復活と仮想ワザの供給。

2 章（A0）: ナツメのESPのついたナツメのフーディンが、［サイコリンク］でカスミのコダックの「ちょうのうりょく」を使い、「おもて」3 枚で相手のコインのあるワザ（ラッキーの「まるまる」）を
自分のワザとして使う盤面。v0.119 では、宣言の前の先読みが、コピー先のコインを今の写しでは起こらないはずの ES0（コードのない問い）として内部エラー（``RuntimeError``）にしていた。
盤面は ``build_test_state`` と通常の ``PlayTrainer``・``ResolveDecision`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない。
"""

from __future__ import annotations

import copy
import pickle
import unittest

from kyuura_engine import effects as E
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import ESP_REDO, SELECT_ATTACK
from kyuura_engine.errors import UnsupportedError
from kyuura_engine.resolution.questions import QUESTIONS
from tests import helpers as H
from tests.test_neo_trainer_components_v0_80 import new_events
from tests.test_unown_family_powers_v0_96 import snap
from tests.test_variable_coins_search_attachments_v0_113 import (
    answer,
    attack,
    board,
    esp_board,
    mon,
    provider_card,
)

HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, PS = H.WATER, H.PSYCHIC
ALAKAZAM = "PMCG6-053"  # ナツメのフーディン（［サイコリンク］）
MISTYS_PSYDUCK = "PMCG5-021"  # カスミのコダック（ちょうのうりょく: コイン 3 枚。「おもて」3 枚で相手のワザを自分のワザとして使う）
CHANSEY = "PMCG1-068"  # ラッキー（まるまる: コイン 1 枚・すてみタックル）
HITMONCHAN = "PMCG1-058"  # エビワラー（コインのないワザ 2 つ）
EC1 = E.ESP_COPIED_COINS_CODE


def a0_board(opponent=CHANSEY, *, esp=True):
    """超・水のついたナツメのフーディンのベンチに、超の色マーカーをのせたカスミのコダック。``esp`` ならナツメのESPを通常の操作でフーディンにつけた盤面。"""
    if esp:
        return esp_board(MISTYS_PSYDUCK, energy=(PS, W), opponent=mon(opponent))
    from kyuura_engine.cards import EnergyType
    from kyuura_engine.state import MARKER_COLOR

    return board(mon(ALAKAZAM, (PS, W)), bench=(mon(MISTYS_PSYDUCK, markers=[(MARKER_COLOR, EnergyType.PSYCHIC)]),), opponent=mon(opponent))


def psychic_power(state, *coins):
    return attack(state, 0, *coins, card=provider_card(state, MISTYS_PSYDUCK))


def coin_flips(before, after):
    return [e["result"] for e in new_events(before, after, "coin_flip") if e.get("source") == "attack"]


class EspCopiedAttackCoinsTest(unittest.TestCase):
    """A0（docs 2 章）: コピー元（ちょうのうりょく）のコインとコピー先（まるまる）のコイン。"""

    def test_declaration_reaches_the_first_redo_decision(self):
        """v0.119 では宣言の前の先読みが RuntimeError にした盤面。今は宣言を受け付け、ちょうのうりょくの 3 枚のあとにESPのやり直しを聞く（v0.66 の時点。止める選択はない）。"""
        state = a0_board()
        asked = psychic_power(state, HD, HD, HD)
        d = asked.decision
        self.assertEqual((d.kind, d.options, d.min_choices, d.max_choices), (ESP_REDO, (1,), 0, 1))
        self.assertIsNone(d.context_value("unresolved_code"))
        self.assertIsNone(d.context_value("esp_asked"))  # ESPのやり直しの決定には書かない（答えのあとに処理している並びのワザを記録し直す）
        self.assertEqual(coin_flips(state, asked), ["heads"] * 3)

    def test_copied_coin_redo_stops_and_declining_continues(self):
        """やり直す・やり直さないのどちらでも、ワザを選ぶ決定は聞いたことを続きの情報 ``esp_asked`` で運ぶ。コピー先のまるまるのコインのあとにもう一度聞くが、やり直すは選ぶと止める（EC1）。
        やり直さないはいつも答えで、まるまるのコインを 1 回だけ使う。"""
        asked = psychic_power(a0_board(), HD, HD, HD)
        for first, coins in (((), ()), ((1,), (HD, HD, HD))):
            with self.subTest(first=first):
                select = answer(asked, first, *coins)
                d = select.decision
                self.assertEqual(d.kind, SELECT_ATTACK)
                self.assertEqual(d.context_value("esp_asked"), ((MISTYS_PSYDUCK, 0),))
                second = answer(select, (0,), HD)  # まるまる
                d = second.decision
                self.assertEqual((d.kind, d.options, d.min_choices, d.max_choices), (ESP_REDO, (1,), 0, 1))
                self.assertEqual((d.context_value("unresolved_code"), d.context_value("unresolved_choices"), d.context_value("copied")),
                                 (EC1, (1,), (CHANSEY, 0)))
                self.assertIn("EC1", d.context_value("unresolved_reason"))
                with self.assertRaises(UnsupportedError) as raised:
                    answer(second, (1,), HD)
                self.assertEqual(raised.exception.code, EC1)
                done = answer(second, ())
                self.assertIsNone(done.decision)
                self.assertEqual(coin_flips(select, done), ["heads"])  # まるまるのコインは 1 回だけ
                self.assertEqual([e["kind"] for e in new_events(second, done, "esp_redo_declined")], ["esp_redo_declined"])
                self.assertTrue(any(e["kind"] == "persistent_effect_added" for e in new_events(second, done)))  # 「おもて」のまるまる
                for other in (second.clone(), copy.deepcopy(second), pickle.loads(pickle.dumps(second))):
                    self.assertEqual(snap(answer(other, ())), snap(done))
                for other in (select.clone(), copy.deepcopy(select), pickle.loads(pickle.dumps(select))):
                    self.assertEqual(snap(answer(answer(other, (0,), HD), ())), snap(done))

    def test_neighbours(self):
        """隣の例: ESPがなければワザを選ぶ決定まで進み、コインのまるまるでもESPの決定はない。相手のワザにコインがない（エビワラー）なら、ESPの決定 → ワザの選択で終わる。
        「おもて」が 3 枚でなければ、コピーしない（2 枚は 20 ダメージ）。"""
        plain = psychic_power(a0_board(esp=False), HD, HD, HD)
        self.assertEqual((plain.decision.kind, plain.decision.options), (SELECT_ATTACK, (0, 1)))
        self.assertIsNone(plain.decision.context_value("esp_asked"))
        rolled = answer(plain, (0,), HD)
        self.assertIsNone(rolled.decision)
        hitmonchan = answer(psychic_power(a0_board(HITMONCHAN), HD, HD, HD), ())
        self.assertEqual(hitmonchan.decision.kind, SELECT_ATTACK)
        self.assertIsNone(answer(hitmonchan, (0,)).decision)
        asked = psychic_power(a0_board(), HD, HD, TL)
        two = answer(asked, ())
        self.assertIsNone(two.decision)
        self.assertEqual([dict(e["steps"])["1 基本となる計算"] for e in new_events(asked, two, "damage")], [20])  # ラッキーの抵抗力で 0 になる
        self.assertEqual([e["kind"] for e in new_events(asked, two, "copy_attack")], [])

    def test_same_attack_second_toss_stays_codeless(self):
        """同じワザの説明文のコインを 2 回に分けて投げる並び（ES0）は、今もコードのない問い（今の写しでは起こらない）。EC1 とは別の問い。"""
        self.assertIsNone(QUESTIONS["esp_separate_coin_tosses"].code)
        self.assertEqual(EC1, "UNRESOLVED_ESP_COPIED_ATTACK_COINS")


if __name__ == "__main__":
    unittest.main()

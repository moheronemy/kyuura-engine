"""v0.117（docs/retreat-return-active-powers-v0.117.md 2 章）: マチスの秘策の相手のうらのカードを 1 枚だけ指定するコマンドの確かめ（A0）。

v0.116 までは、うらのカード 1 枚の確かめの回数（割り当てのない最初の実行 1・たね・ベイビィの代表 510・「たねポケモンでない」の代表 1 = 512）が上限 ``_IDENTITY_TRIAL_LIMIT``（512）
ちょうどで、たねの代表が 1 つ増えると、1 枚だけを指定するコマンドも ``UNSUPPORTED_SECRET_PLAN_IDENTITIES`` になっていた。v0.117 から、1 枚だけを指定するコマンドは分岐の作りから
決まる回数（``engine._single_identity_budget``。公開の情報だけで決まる）ですべて確かめ、上限 512 は 2 枚目の割り当てが要るコマンドだけに使う。盤面は v0.68 の利用者の再現例
（マチスの秘策でうらにしたディグダ 3 枚。山札の中身だけが違うデッキ A・B）と、うらのカード 1 枚の盤面。
"""

from __future__ import annotations

import time
import unittest
from unittest import mock

from kyuura_engine import (
    EndTurn,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
    apply_command,
    engine,
    zones,
)
from kyuura_engine.errors import UnsupportedError
from kyuura_engine.observation import observe
from tests import helpers as H
from tests.helpers import build_test_state
from tests.test_final_pmcg_cards_v0_68 import (
    DIGLETT,
    DODUO,
    FIGHTING,
    FIRE,
    GUST,
    HITMONCHAN,
    LT_SURGES_SECRET_PLAN,
    RATTATA,
    full,
    secret_plan_board,
)

MEWTWO_PR1 = "PR1-022"  # テレキネシス（相手の場のポケモン 1 匹を選ぶ。v0.116）


def one_face_down_board(opponent=None):
    """マチスの秘策でうらにしたディグダ 1 枚だけの盤面（プレイヤー 0 のベンチ）。相手（プレイヤー 1）の番。"""
    state = build_test_state([
        {"active": {"card": HITMONCHAN, "energy": [FIGHTING, FIGHTING]}, "hand": [LT_SURGES_SECRET_PLAN, DIGLETT], "prizes": [FIRE] * 6,
         "deck": [RATTATA] + [FIRE] * 44},
        {"active": opponent or {"card": HITMONCHAN, "energy": [FIGHTING]}, "hand": [GUST], "prizes": [FIRE] * 6, "deck": [FIRE] * 49},
    ], turn_number=5, current_player=0)
    plan = next(u for u in state.players[0].hand if state.cards[u].card_id == LT_SURGES_SECRET_PLAN)
    state = apply_command(state, PlayTrainer(0, plan))
    diglett = next(u for u in state.players[0].hand if state.cards[u].card_id == DIGLETT)
    state = apply_command(state, ResolveDecision(0, state.decision.id, (diglett,)))
    return apply_command(state, EndTurn(0))


class Trials:
    """確かめの 1 回ぶんの割り当て（``_IdentityOracle``）を作った数と、その割り当て（script）。"""

    def __init__(self):
        self.scripts: list[tuple[str, ...]] = []
        self._init = engine._IdentityOracle.__init__

    def __enter__(self):
        trials = self

        def counting(oracle, scope, script):
            trials.scripts.append(script)
            trials._init(oracle, scope, script)

        self._patch = mock.patch.object(engine._IdentityOracle, "__init__", counting)
        self._patch.__enter__()
        return self

    def __exit__(self, *exc):
        return self._patch.__exit__(*exc)

    @property
    def count(self) -> int:
        return len(self.scripts)


def representatives(state):
    pool = engine._public_pool(state)
    candidates = engine._identity_candidates(pool)
    basics = [c for c in candidates if pool.get(c).is_baby_or_basic_pokemon]
    return candidates, basics, [c for c in candidates if c not in basics]


def gust_decision(state):
    gust = next(u for u in state.players[1].hand if state.cards[u].card_id == GUST)
    return apply_command(state, PlayTrainer(1, gust))


class SingleIdentityTest(unittest.TestCase):
    def test_budget_follows_the_branch_structure(self):
        """1 枚の回数は、最初の実行 1 + たね・ベイビィの代表 + 「たねポケモンでない」1 + たねでない代表（展開）。どれも公開の情報（対応しているカードの一覧）から決まる。"""
        state = secret_plan_board()
        candidates, basics, nonbasics = representatives(state)
        self.assertEqual(engine._single_identity_budget(basics, nonbasics), 2 + len(candidates))
        self.assertEqual(engine._IDENTITY_TRIAL_LIMIT, 512)  # 2 枚目の割り当てが要るコマンドの上限は変えない
        self.assertEqual(representatives(secret_plan_board(DODUO)), (candidates, basics, nonbasics))  # 山札の中身によらない

    def test_gust_on_one_of_three_face_down_cards(self):
        """場にうらのカードが 3 枚あり、突風（PlayTrainer → 選ぶ答え ResolveDecision）で 1 枚だけを指定する。山札の中身だけが違うデッキ A・B で、どちらも受け付け、回数（最初の実行・
        たね・ベイビィの代表・「たねポケモンでない」）と相手に見える情報が同じ。展開は起こらない（たねでない代表をトラッシュしたあとに読む処理がない）。"""
        _, basics, _ = representatives(secret_plan_board())
        seen = []
        for extra in (None, DODUO):
            with self.subTest(extra=extra):
                state = secret_plan_board(extra)
                self.assertEqual(sum(1 for uid in state.face_down_cards if state.cards[uid].owner == 0), 3)
                with Trials() as played:
                    asked = gust_decision(state)
                target = asked.decision.options[0]
                with Trials() as answered:
                    after = apply_command(asked, ResolveDecision(1, asked.decision.id, (target,)))
                self.assertEqual(after.players[0].active.pokemon_id, target)
                for trials in (played, answered):
                    self.assertEqual(trials.count, 1 + len(basics) + 1)
                    self.assertEqual(trials.scripts[0], ())
                    self.assertEqual({len(s) for s in trials.scripts}, {0, 1})  # 2 枚目は割り当てない
                seen.append((played.scripts, answered.scripts, observe(asked, 1), observe(after, 1)["players"][0]["bench"]))
        self.assertEqual(seen[0], seen[1])

    def test_one_more_basic_representative_still_fits(self):
        """v0.116 の境界: たねの代表が 1 つ増えると、v0.116 の上限 512 では 1 枚だけを指定する突風も止まった（変える前のコードで、同じ突風に対して 513 回目で
        UNSUPPORTED_SECRET_PLAN_IDENTITIES になることを確かめた。docs 2 章）。今は回数が 1 つ増えるだけで受け付ける。回数が分岐の作りの数より 1 少ない上限なら、最初の実行も
        数えているので足りない（エンジンの不具合として止まり、状態・確かめの記録はもどる）。"""
        state = secret_plan_board()
        pool = engine._public_pool(state)
        original = engine._identity_candidates
        twin = next(c for c in sorted(pool.playable_ids) if c not in original(pool) and pool.get(c).is_basic_pokemon)  # 処理の同じカードで代表されていたたね
        _, basics, _ = representatives(state)
        self.assertGreater(1 + (len(basics) + 1) + 1, engine._IDENTITY_TRIAL_LIMIT)  # v0.116 の上限を超える回数でも、1 枚なら確かめる
        asked = gust_decision(state)
        answer = ResolveDecision(1, asked.decision.id, (asked.decision.options[0],))
        with mock.patch.object(engine, "_identity_candidates", lambda p: tuple(sorted(original(p) + (twin,)))):
            with Trials() as trials:
                apply_command(asked, answer)
            self.assertEqual(trials.count, 1 + (len(basics) + 1) + 1)
            before = full(asked)
            needed = trials.count
            with mock.patch.object(engine, "_single_identity_budget", lambda b, n: needed - 1), self.assertRaises(RuntimeError):
                apply_command(asked, answer)
            self.assertEqual(full(asked), before)
            self.assertEqual((zones.IDENTITY_CONSULTED, zones.IDENTITY_ORACLE), (None, None))
            with mock.patch.object(engine, "_single_identity_budget", lambda b, n: needed):
                apply_command(asked, answer)

    def test_nonbasic_expansion_tries_every_nonbasic_representative(self):
        """「たねポケモンでない」とだけ決めたカードを、トラッシュしたあとに読んだら（今のカードの処理にはないので、読む処理を一時的に足した本当の突風の答え）、たねでない代表を
        ひとつずつ試す。回数は分岐の作りの数（2 + 代表の数）ちょうどで、山札の中身によらず受け付ける。"""
        original_reveal = zones.reveal_face_down

        def reading_reveal(state, owner, pokemon, **kw):
            card = pokemon.card
            kept = original_reveal(state, owner, pokemon, **kw)
            if kept is None:
                _ = state.card_def(card).hp  # トラッシュしたカードのほかの項目を読む
            return kept

        results = []
        for extra in (None, DODUO):
            state = secret_plan_board(extra)
            candidates, _, nonbasics = representatives(state)
            asked = gust_decision(state)
            with Trials() as trials, mock.patch.object(zones, "reveal_face_down", reading_reveal):
                after = apply_command(asked, ResolveDecision(1, asked.decision.id, (asked.decision.options[0],)))
            self.assertEqual(trials.count, 2 + len(candidates))
            expanded = [s for s in trials.scripts if s and s[0] in nonbasics]
            self.assertEqual(sorted(s[0] for s in expanded), sorted(nonbasics))
            results.append((trials.scripts, after.players[0].active.pokemon_id))
        self.assertEqual(results[0], results[1])

    def test_attack_that_chooses_the_one_face_down_card(self):
        """うらのカード 1 枚の場で、テレキネシス（ワザ。宣言の前の先読みが選べるポケモンのすべてを試す）を宣言し、そのうらのカードを選ぶ。どちらも 1 枚だけを指定するので受け付ける。
        代表的な回数と時間を記録する（docs 2 章）。"""
        state = one_face_down_board({"card": MEWTWO_PR1, "energy": [H.PSYCHIC] * 3})
        _, basics, _ = representatives(state)
        began = time.time()
        with Trials() as declared:
            asked = apply_command(state, UseAttack(1, 1))
        face_down = next(p.pokemon_id for p in asked.players[0].bench if asked.is_face_down(p))
        with Trials() as answered:
            apply_command(asked, ResolveDecision(1, asked.decision.id, (face_down,)))
        self.assertEqual((declared.count, answered.count), (1 + len(basics) + 1, 1 + len(basics) + 1))
        self.assertLess(time.time() - began, 120)

    def test_two_designations_keep_the_existing_refusal(self):
        """うらのカード 3 枚の場のテレキネシス: 先読みが選べるポケモンのすべてを試すので、2 枚目の割り当てが要る（v0.68 からの上限 512 の範囲。エンジンの未対応のまま）。拒否は状態・
        確かめの記録を変えず、山札の中身によらない。"""
        results = []
        for extra in (None, DODUO):
            state = secret_plan_board(extra, opponent={"card": MEWTWO_PR1, "energy": [H.PSYCHIC] * 3}, turn_number=5)
            before = full(state)
            with Trials() as trials, self.assertRaises(UnsupportedError) as caught:
                apply_command(state, UseAttack(1, 1))
            self.assertEqual(full(state), before)
            self.assertEqual((zones.IDENTITY_CONSULTED, zones.IDENTITY_ORACLE), (None, None))
            self.assertTrue(any(len(s) >= 2 for s in trials.scripts))
            self.assertEqual(trials.count, engine._IDENTITY_TRIAL_LIMIT)
            results.append((caught.exception.code, caught.exception.message, trials.scripts))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0][0], "UNSUPPORTED_SECRET_PLAN_IDENTITIES")


if __name__ == "__main__":
    unittest.main()

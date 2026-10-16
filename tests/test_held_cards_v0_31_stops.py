"""v0.31: 原典で決められない場合に止める処理（停止コード 15。docs/held-cards-v0.31.md 5 章）の、止まる場合と隣の止まらない場合。

- HC1〜HC10: v0.31 のカードで新しく起こる問い（kyuura に論点がない。研究の対応表の ``not_in_kyuura``）
- T27・C34/C35・G40・P19・P32: v0.30 まで起こらなかった（コードのない）問い。控えポケモン・複数のポケモンにダメージ・効果を与えるワザ（やきはらう）で
  起こるようになったので停止コードにした（kyuura の論点 UQ- はそのまま。分類は変えていない）
- ``UNSUPPORTED_COPIED_ATTACK``: 裁定の問いではなく、エンジンが相手のワザとして使えない（番をまたぐ効果を自分のワザとして与える）ワザ

止めるのは状態を変える前（宣言のときは ``UnsupportedError`` で、渡した状態・ログ・乱数は変わらない。決定の答えのときは決定を待ったまま）。宣言の前に
止めるものは、コインの結果によらない（先読みがすべての結果を試す）。成功を仮定するテストは書かない（CLAUDE.md の「ルールの扱い」）。
"""

from __future__ import annotations

import unittest

from kyuura_engine import EngineError, ResolveDecision, UnsupportedError, UseAttack, UsePokemonPower
from kyuura_engine.resolution import PREFLIGHT_MODES
from tests.helpers import (
    BASE_GASTLY,
    BLAINES_ARCANINE,
    BLAINES_CHARMELEON,
    BLAINES_MAGMAR,
    BLAINES_VULPIX,
    BULBASAUR,
    CHARIZARD,
    CLEFABLE,
    CLEFAIRY,
    DARK_WARTORTLE,
    FIGHTING,
    FIRE,
    GASTLY,
    GIOVANNIS_MACHAMP,
    GIOVANNIS_MACHOKE,
    GIOVANNIS_MACHOP,
    GRASS,
    GRIMER,
    HAUNTER,
    HITMONCHAN,
    IVYSAUR,
    LIGHTNING,
    LT_SURGES_ELECTABUZZ,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MAGMAR,
    MEWTWO,
    MISTYS_PSYDUCK,
    MOLTRES,
    MUK,
    PSYCHIC,
    PSYDUCK,
    RATTATA,
    ROCKET_SQUIRTLE,
    ROCKETS_MOLTRES,
    VENUSAUR,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.test_held_cards_v0_31 import first, mon, play
from tests.test_held_cards_v0_31_mechanisms import snapshot

TURN = 7
COINS = ((H,) * 6, (T,) * 6, (H, T) * 3)


def board(active, opponent=None, *, bench=(), opponent_bench=(RATTATA,), discard=(), deck=None, opponent_deck=None, opponent_prizes=6):
    me = {"active": active, "bench": list(bench), "discard": list(discard)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (FIGHTING,)), "bench": list(opponent_bench), "prizes": opponent_prizes}
    if opponent_deck is not None:
        them["deck"] = list(opponent_deck)
    return build_test_state([me, them], turn_number=TURN)


class StopTestCase(unittest.TestCase):
    def assert_stops(self, state, command, code, *, coins=COINS):
        """宣言（または特殊能力の使用）を、コインの結果・先読みの方法によらず ``code`` で止め、状態・ログ・乱数を変えない。"""
        for sides in coins:
            seeded = with_coin_results(state, *sides)
            for mode in PREFLIGHT_MODES:
                before = snapshot(seeded)
                with self.subTest(coins=sides[:3], mode=mode):
                    with self.assertRaises(UnsupportedError) as ctx:
                        apply_kernel(seeded, command, preflight=mode)
                    self.assertEqual(ctx.exception.code, code)
                    self.assertEqual(snapshot(seeded), before)

    def assert_proceeds(self, state, command, *, coins=COINS):
        for sides in coins:
            for mode in PREFLIGHT_MODES:
                with self.subTest(coins=sides[:3], mode=mode):
                    apply_kernel(with_coin_results(state, *sides), command, preflight=mode)

    def assert_answer_stops(self, state, answer, code):
        """決定の答えを ``code`` で止め、決定は待ったまま（状態・ログ・乱数を変えない）。"""
        d = state.decision
        before = snapshot(state)
        with self.assertRaises(UnsupportedError) as ctx:
            apply_kernel(state, ResolveDecision(d.player, d.id, tuple(answer)))
        self.assertEqual(ctx.exception.code, code)
        self.assertEqual(snapshot(state), before)


class HeldCardStopTest(StopTestCase):
    def test_hc1_discard_timing_when_confused(self):
        """HC1: 「はがしてすてる」（トラッシュが条件か効果か決められない）ワザを、こんらん状態で使うときだけ止める（「うら」でトラッシュするかが変わる）。
        こんらんでなければ、どちらの読み方でも結果は同じなので止めない。ほのおのあらし（RUL-ENERGY-DISCARD-ATTACKS の範囲。効果）は止めない。"""
        for card, index, energy in ((BASE_GASTLY, 1, (PSYCHIC, PSYCHIC)), (MEWTWO, 1, (PSYCHIC, PSYCHIC)), (CHARIZARD, 0, (FIRE,) * 4),
                                    ("PMCG1-042", 1, (LIGHTNING,) * 4), ("PMCG3-027", 1, (PSYCHIC, PSYCHIC)), (MOLTRES, 0, (FIRE,))):
            with self.subTest(card=card):
                self.assert_stops(board(mon(card, energy, confusion=True)), UseAttack(0, index), "UNRESOLVED_DISCARD_ENERGY_TIMING")
                self.assert_proceeds(board(mon(card, energy)), UseAttack(0, index))
        self.assert_proceeds(board(mon(BLAINES_ARCANINE, (FIRE,) * 4, confusion=True)), UseAttack(0, 1))

    def test_hc2_destiny_bond_ending_the_game(self):
        """HC2: みちづれで相手の対戦ポケモンも「きぜつ」するとき、勝ち負けが決まる（サイドを取りきる・場にポケモンがいなくなる）場合は、同時のきぜつか
        決められないので、相手のワザの宣言の前に止める。決まらない場合は両方がサイドを取る（tests/test_held_cards_v0_31_mechanisms.py）。"""
        state = build_test_state([
            {"active": mon(BASE_GASTLY, (PSYCHIC, PSYCHIC)), "bench": [RATTATA]},
            {"active": mon(MAGMAR, (FIRE, FIRE)), "bench": [RATTATA], "prizes": 1},
        ], turn_number=TURN)
        state = play(state, UseAttack(0, 1), [first()])
        self.assert_stops(state, UseAttack(1, 0), "UNRESOLVED_DESTINY_BOND_KNOCKOUT", coins=((H,),))
        state = build_test_state([
            {"active": mon(BASE_GASTLY, (PSYCHIC, PSYCHIC)), "bench": [RATTATA]},
            {"active": mon(MAGMAR, (FIRE, FIRE)), "prizes": 6},
        ], turn_number=TURN)
        state = play(state, UseAttack(0, 1), [first()])
        self.assert_stops(state, UseAttack(1, 0), "UNRESOLVED_DESTINY_BOND_KNOCKOUT", coins=((H,),))  # 相手の場にポケモンがいなくなる
        state = build_test_state([
            {"active": mon(BASE_GASTLY, (PSYCHIC, PSYCHIC)), "bench": [RATTATA]},
            {"active": mon(MAGMAR, (FIRE, FIRE)), "bench": [RATTATA], "prizes": 2},
        ], turn_number=TURN)
        self.assert_proceeds(play(state, UseAttack(0, 1), [first()]), UseAttack(1, 0), coins=((H,),))

    def test_hc3_effect_coin_against_barrier(self):
        """HC3: 「ワザをうけない」状態（バリアー）のポケモンへの効果だけを決めるコイン（うたう・さいみんガス）を投げるかは決められない。バリアーが
        なければ止めない。"""
        for card, index, energy in ((CLEFAIRY, 0, (FIRE,)), (BASE_GASTLY, 0, (PSYCHIC,))):
            state = build_test_state([
                {"active": mon(MEWTWO, (PSYCHIC, PSYCHIC)), "bench": [RATTATA]},
                {"active": mon(card, energy), "bench": [RATTATA]},
            ], turn_number=TURN)
            barrier = play(state, UseAttack(0, 1), [first()])
            with self.subTest(card=card):
                self.assert_stops(barrier, UseAttack(1, index), "UNRESOLVED_PREVENTED_EFFECT_COIN")
                no_barrier = play(state, UseAttack(0, 0))  # サイコキネシスで番を終える（バリアーはない）
                self.assert_proceeds(no_barrier, UseAttack(1, index))

    def test_hc4_extra_water_with_colorless(self):
        """HC4: 第4弾のコダックの「みずでっぽう」（水無）で、多い水エネルギーの数が読み方（無色を水で払うか）で変わるときだけ止める。"""
        for energy in ((WATER, WATER), (WATER, WATER, FIRE), (WATER, WATER, WATER, FIRE, FIRE)):
            with self.subTest(energy=energy):
                self.assert_stops(board(mon(PSYDUCK, energy)), UseAttack(0, 1), "UNRESOLVED_EXTRA_ENERGY_COLORLESS")
        for energy in ((WATER, FIRE), (WATER, FIRE, FIRE)):
            self.assert_proceeds(board(mon(PSYDUCK, energy)), UseAttack(0, 1))

    def test_hc5_any_number_zero(self):
        """HC5: 「好きなだけはがしてすてる」（やまやき）で 0 枚を選べるかは決められない（答えのときに止める。決定は待ったまま）。1 枚なら進む。"""
        state = play(board(mon(MOLTRES, (FIRE, FIRE))), UseAttack(0, 0))
        self.assert_answer_stops(state, (), "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO")
        play(state, ResolveDecision(0, state.decision.id, (state.decision.options[0],)))

    def test_hc6_deck_short(self):
        """HC6: 山札の上から決まった枚数をトラッシュする効果で、山札が足りない場合（マグマふんしゅつの自分の山札 5 枚未満、やまやきの相手の山札 0 枚・
        選んだ枚数より少ない）。"""
        self.assert_stops(board(mon(BLAINES_MAGMAR, (FIRE,) * 3), deck=[FIRE] * 4), UseAttack(0, 1), "UNRESOLVED_DISCARD_DECK_SHORT")
        self.assert_proceeds(board(mon(BLAINES_MAGMAR, (FIRE,) * 3), deck=[FIRE] * 5), UseAttack(0, 1))
        self.assert_stops(board(mon(MOLTRES, (FIRE, FIRE)), opponent_deck=[]), UseAttack(0, 0), "UNRESOLVED_DISCARD_DECK_SHORT")
        state = play(board(mon(MOLTRES, (FIRE, FIRE)), opponent_deck=[WATER]), UseAttack(0, 0))
        self.assertEqual(state.decision.max_choices, 2)
        self.assert_answer_stops(state, tuple(state.decision.options), "UNRESOLVED_DISCARD_DECK_SHORT")
        play(state, ResolveDecision(0, state.decision.id, (state.decision.options[0],)))

    def test_hc7_attach_from_discard_zero(self):
        """HC7: たいでんで、トラッシュに雷があるときに 0 枚を選べるかは決められない（答えのときに止める）。雷がなければ決定を出さない（止めない）。"""
        state = play(board(mon(LT_SURGES_ELECTABUZZ, (LIGHTNING,)), discard=(LIGHTNING,)), UseAttack(0, 0))
        self.assert_answer_stops(state, (), "UNRESOLVED_ATTACH_FROM_DISCARD_ZERO")
        self.assert_proceeds(board(mon(LT_SURGES_ELECTABUZZ, (LIGHTNING,)), discard=(FIRE,)), UseAttack(0, 0))

    def test_hc8_power_heal_without_damage(self):
        """HC8: しぜんになおるを、ダメージカウンターがのっていないときに使えるか（自分の番ごとに 1 回を使ったことになるか）は決められない。"""
        state = board(mon(BLAINES_VULPIX, (FIRE,)))
        pid = state.players[0].active.pokemon_id
        self.assert_stops(state, UsePokemonPower(0, pid, 0), "UNRESOLVED_POWER_HEAL_WITHOUT_DAMAGE", coins=((H,),))
        self.assert_proceeds(board(mon(BLAINES_VULPIX, (FIRE,), damage=10)), UsePokemonPower(0, pid, 0), coins=((H,),))

    def test_hc9_copied_attack(self):
        """HC9: 相手のワザを自分のワザとして使うとき、選べるワザがすべて処理を決められない（カスミのコダック（条件を書いていない）が、トラッシュが条件か
        効果か決められないリザードンの「ほのおのうず」しかない相手）なら、宣言の前に止める。処理できるワザがあれば止めない。ピクシー（ほかに必要な条件が
        たりなければ使えない）は「ほのおのうず」を選べない（ワザがないのと同じく何もしない）。"""
        charizard = mon(CHARIZARD, (FIRE,), evolved_from=["PMCG1-014", "PMCG1-017"])
        self.assert_stops(board(mon(MISTYS_PSYDUCK, (PSYCHIC,)), opponent=charizard), UseAttack(0, 0), "UNRESOLVED_COPIED_ATTACK")
        self.assert_proceeds(board(mon(MISTYS_PSYDUCK, (PSYCHIC,)), opponent=mon(HITMONCHAN)), UseAttack(0, 0))

    def test_hc10_energy_burn_and_energy_trans(self):
        """HC10: エナジーバーンで「炎」になった草エネルギーカードを、エナジートランス（「草」エネルギーをつけかえる）でつけかえられるかは決められない。
        エナジーバーンを使っていない草エネルギーカードはつけかえられる。"""
        state = build_test_state([
            {"active": mon(CHARIZARD, (GRASS, GRASS, FIRE)), "bench": [mon(VENUSAUR, (GRASS,), evolved_from=[BULBASAUR, IVYSAUR])]},
            {"active": mon(HITMONCHAN)},
        ], turn_number=TURN)
        charizard, venusaur = state.players[0].active, state.players[0].bench[0]
        grass = charizard.energy[0]
        burned = apply_kernel(state, UsePokemonPower(0, charizard.pokemon_id, 0))
        self.assert_stops(burned, UsePokemonPower(0, venusaur.pokemon_id, 0, energy=grass, source=charizard.pokemon_id, target=venusaur.pokemon_id),
                          "UNRESOLVED_ENERGY_BURN_TRANSFER", coins=((H,),))
        self.assert_proceeds(state, UsePokemonPower(0, venusaur.pokemon_id, 0, energy=grass, source=charizard.pokemon_id,
                                                    target=venusaur.pokemon_id), coins=((H,),))

    def test_unsupported_copied_attack(self):
        """エンジンが相手のワザとして使えないワザ（番をまたぐ効果を、ワザを使ったポケモンに与える「ほのおのかべ」「こうらがえし」「つるぎのまい」）は、
        選ぶと ``UNSUPPORTED_COPIED_ATTACK``（ルールの問いではない）。ほかに処理できるワザがなければ宣言の前に止める。"""
        self.assert_stops(board(mon(CLEFABLE, (FIRE,)), opponent=mon(ROCKETS_MOLTRES, (FIRE,))), UseAttack(0, 0), "UNSUPPORTED_COPIED_ATTACK")
        state = play(board(mon(CLEFABLE, (FIRE,)), opponent=mon(DARK_WARTORTLE, (WATER,), evolved_from=ROCKET_SQUIRTLE)), UseAttack(0, 0))
        self.assertEqual(state.decision.context_value("unsupported_choices"), (1,))
        self.assert_answer_stops(state, (1,), "UNSUPPORTED_COPIED_ATTACK")
        play(state, ResolveDecision(0, state.decision.id, (0,)))


class SpreadDamageStopTest(StopTestCase):
    """やきはらう（相手と相手の控え全員にダメージ）で起こるようになった、v0.30 までのコードのない問い。1 匹だけなら止めない（今までどおり処理する）。"""

    def scorch(self, opponent, bench, *, attacker_damage=0):
        return board(mon(BLAINES_CHARMELEON, (FIRE, FIRE, FIRE), damage=attacker_damage), opponent=opponent, opponent_bench=bench)

    def test_t27_two_transparency(self):
        haunter = mon(HAUNTER, (PSYCHIC,), evolved_from=GASTLY)
        self.assert_stops(self.scorch(haunter, (mon(HAUNTER, (), evolved_from=GASTLY),)), UseAttack(0, 1), "UNRESOLVED_TRANSPARENCY_COIN_ORDER")
        self.assert_proceeds(self.scorch(haunter, (RATTATA,)), UseAttack(0, 1))

    def test_c34_two_counterattacks(self):
        machamp = mon(MACHAMP, (FIGHTING,), evolved_from=[MACHOP, MACHOKE])
        self.assert_stops(self.scorch(machamp, (mon(MACHAMP, (), evolved_from=[MACHOP, MACHOKE]),)), UseAttack(0, 1),
                          "UNRESOLVED_MULTIPLE_DAMAGE_TRIGGERS")
        self.assert_proceeds(self.scorch(machamp, (RATTATA,)), UseAttack(0, 1))

    def test_g40_two_ko_preventions(self):
        guts = {"evolved_from": [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], "damage": 90}
        self.assert_stops(self.scorch(mon(GIOVANNIS_MACHAMP, (FIGHTING,), **guts), (mon(GIOVANNIS_MACHAMP, (), **guts),)), UseAttack(0, 1),
                          "UNRESOLVED_KO_PREVENTION_ORDER", coins=((H,) * 6,))
        self.assert_proceeds(self.scorch(mon(GIOVANNIS_MACHAMP, (FIGHTING,), **guts), (RATTATA,)), UseAttack(0, 1), coins=((H,) * 6,))

    def test_p32_two_phoenixes(self):
        moltres = {"damage": 50}
        self.assert_stops(self.scorch(mon(ROCKETS_MOLTRES, (FIRE,), **moltres), (mon(ROCKETS_MOLTRES, (), **moltres), RATTATA)), UseAttack(0, 1),
                          "UNRESOLVED_POST_KNOCKOUT_POWERS_ORDER", coins=((H,) * 6,))
        self.assert_proceeds(self.scorch(mon(ROCKETS_MOLTRES, (FIRE,), **moltres), (RATTATA,)), UseAttack(0, 1), coins=((H,) * 6,))

    def test_p19_gas_source_knocked_out_together(self):
        muk = {"evolved_from": GRIMER}
        self.assert_stops(self.scorch(mon(ROCKETS_MOLTRES, (FIRE,), damage=50), (mon(MUK, (), damage=60, **muk), RATTATA)), UseAttack(0, 1),
                          "UNRESOLVED_PHOENIX_GAS_SOURCE_KNOCKOUT", coins=((H,) * 6,))
        self.assert_proceeds(self.scorch(mon(ROCKETS_MOLTRES, (FIRE,), damage=50), (mon(MUK, (), **muk), RATTATA)), UseAttack(0, 1),
                             coins=((H,) * 6,))


class CoverageTest(unittest.TestCase):
    def test_every_new_code_has_a_test_here(self):
        """v0.31 で加えた停止コード（研究の対応表の v0.31 の行）は、どれもこのファイルで止まる場合を確かめる。"""
        import json
        import pathlib
        import re

        links = json.loads((pathlib.Path(__file__).resolve().parent.parent / "kyuura_engine" / "data" / "research_links.json").read_text("utf-8"))
        new = {code for code, entry in links["stop_codes"].items() if any(r["version"] == "v0.31" for r in entry["engine_rulings"])
               or "kyuura_index_engine_key" in entry}
        text = pathlib.Path(__file__).read_text("utf-8")
        found = set(re.findall(r'"(UNRESOLVED_[A-Z_]+)"', text))
        self.assertEqual(len(new), 15)
        self.assertTrue(new <= found, new - found)
        self.assertIn("UNSUPPORTED_COPIED_ATTACK", text)
        self.assertTrue(issubclass(UnsupportedError, EngineError))


if __name__ == "__main__":
    unittest.main()

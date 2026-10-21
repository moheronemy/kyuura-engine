"""v0.82: ポケモンチェックの 1 のきのみどうしの順番（docs/energy-discard-return-v0.82.md 2 章）。

v0.81a は、悪エネルギーの効果がないとききのみをまとめて処理し、受け付けられない状態の確かめ（``state_stop_after``）をまとめた前後だけで行っていた。きのみの回復で
かがくへんかガスがもどる（ほかのポケモンの特殊能力が消え、最大HPが下がる）と、ほかのきのみより先か後かで MH1 になるかが変わる。順番は公式ルール 2000.02.14版と記録から
決まらない（GR-2000-P323-POKEMON-CHECK。ポケモンチェックはどちらの番でもない。p.323）ので、結果が変わるなら BY1 で止める。

カードはどれも前の版で登録したもの（kyuura データの採用・過去の原典照合）。ガイドブックは読んでいない。
"""

from __future__ import annotations

import unittest

from kyuura_engine import Phase, procedures
from tests import helpers as H
from tests.test_berry_maxhp_fixes_v0_81a import (
    BY1,
    MH1,
    MIRACLE_BERRY,
    check_board,
    end,
    gas_muk,
    halted_before_change,
)
from tests.test_neo_trainer_components_v0_80 import audited, mon, snapshot

GOLD_BERRY = "neo1-079"
P = H.PSYCHIC


def gastly(damage, *, gold=True):
    """ナツメのゴース（［ガスのからだ］。印刷の HP 40 + 「超」1 枚で 50）。"""
    return mon(H.SABRINAS_GASTLY, (P,), damage=damage, trainers=[(GOLD_BERRY, None)] if gold else [])


def muk(*, miracle=True):
    return gas_muk(confusion=True, trainers=[(MIRACLE_BERRY, None)] if miracle else [])


class BerryVersusBerryOrderTest(unittest.TestCase):
    """こんらん状態のベトベトン（ガスが消えている）にきせきのみ、ベンチのナツメのゴース（HP 50・ダメージ 40）におうごんのみ。きせきのみが先ならガスがもどってゴースの
    HP が 40 になり、ダメージ 40 で MH1。おうごんのみが先ならダメージ 0 になってから HP 40 で、止めない。結果が変わるので BY1（v0.81a はまとめた前後だけを比べて進めていた）。"""

    def test_interacting_berries_stop_with_by1(self):
        state = check_board(muk(), mon(H.RATTATA), my_bench=(gastly(40),))
        before = snapshot(state)
        after = end(state)
        self.assertEqual(snapshot(state), before)
        halted_before_change(self, state, after, BY1)
        self.assertIn(MH1, after.halt.message)

    def test_without_the_miracle_berry_the_gold_berry_heals_forty(self):
        state = check_board(muk(miracle=False), mon(H.RATTATA), my_bench=(gastly(40),))
        after = end(state)
        self.assertIs(after.phase, Phase.MAIN)
        ghost = after.players[0].bench[0]
        self.assertEqual((ghost.damage, ghost.trainers), (0, []))
        audited(self, after)

    def test_without_the_gold_berry_it_is_mh1(self):
        state = check_board(muk(), mon(H.RATTATA), my_bench=(gastly(40, gold=False),))
        after = end(state)
        halted_before_change(self, state, after, MH1)

    def test_damage_below_the_lowered_hp_proceeds(self):
        """ダメージ 30 なら、おうごんのみははたらかず、ガスがもどっても HP 40 より小さいので、どちらの順番でも同じ（止めない）。"""
        state = check_board(muk(), mon(H.RATTATA), my_bench=(gastly(30),))
        after = end(state)
        self.assertIs(after.phase, Phase.MAIN)
        ghost = after.players[0].bench[0]
        self.assertEqual(ghost.damage, 30)
        self.assertEqual(after.players[0].active.conditions.names(), ())
        audited(self, after)

    def test_berries_that_do_not_interact_proceed(self):
        """ガスを持たないポケモンのきせきのみと、おうごんのみ（たがいの結果を変えない）は、まとめて処理して止めない。"""
        state = check_board(mon(H.RATTATA, confusion=True, trainers=[(MIRACLE_BERRY, None)]), mon(H.RATTATA), my_bench=(gastly(40),))
        after = end(state)
        self.assertIs(after.phase, Phase.MAIN)
        self.assertEqual(after.players[0].bench[0].damage, 0)
        self.assertEqual(after.players[0].active.conditions.names(), ())
        audited(self, after)


    def test_too_many_interacting_berries_halt_as_unsupported(self):
        """順番を比べるきのみが上限より多ければ、比べずに止める（エンジンの未対応。上限を 0 にして確かめる）。"""
        state = check_board(muk(), mon(H.RATTATA), my_bench=(gastly(40),))
        saved = procedures.MAX_INFLUENTIAL_BERRIES
        procedures.MAX_INFLUENTIAL_BERRIES = 0
        try:
            after = end(state)
        finally:
            procedures.MAX_INFLUENTIAL_BERRIES = saved
        halted_before_change(self, state, after, procedures.BERRY_ORDER_LIMIT_CODE)


if __name__ == "__main__":
    unittest.main()

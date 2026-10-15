"""ワザのダメージの要素の結果（``DamageResult``。v0.4d）と、与えたダメージによる回復（メガドレイン）の境界の監査（v0.4e）。

``effects.deal_attack_damage`` の結果を、受けるポケモン（相手の対戦ポケモン・自分）× 計算（0・弱点・抵抗力・プラスパワー・
ディフェンダー・防いだ）× きぜつ（ちょうど HP・HP を超える）の表で確かめる。1 つの規定（p.321 の計算と結果の値）を確かめる
テストなので、盤面は ``build_test_state`` で直接作り、関数を直接呼ぶ（呼んだ状態は複製。v0.16b から、解決の基盤のワザの枠を
``resolution.open_attack`` で開いて呼ぶ。``deal_attack_damage`` は解決の基盤の ``kernel.deal_damage`` に委ねる）。

根拠: p.319（「与えたダメージ」は最終ダメージで、HP で上限を付けない。0 なら「ダメージを与えなかった」）、p.321（計算の順番。
「ダメージを受けない」状態ならダメージを与える要素は無効）、p.257（プラスパワー・ディフェンダーは自分へのダメージにも効く）、
p.90（自分へのダメージの弱点・抵抗力。v0.3d。SUPPORTED）、p.19（メガドレインの最新の説明「相手にダメージを与えたら、その半分
（切り上げ）のダメージカウンターを、自分からとりのぞく。」）、p.320（のっている数より多くはとりのぞかない）。
kyuura NEO-2000-OFFICIAL-RULES。docs/damage-drain-v0.4d.md・docs/integration-audit-v0.4e.md 5 章。
"""

import unittest

from kyuura_engine import UseAttack, apply_command, check_invariants
from kyuura_engine.effects import OPPONENT_ACTIVE, SELF, deal_attack_damage
from kyuura_engine.resolution import open_attack
from kyuura_engine.rng import rng_fingerprint

from tests.helpers import (
    BUTTERFREE, CATERPIE, DEFENDER, DIGLETT, FIGHTING, GRASS, HITMONCHAN, MACHOP, METAPOD, PLUSPOWER, RATTATA, build_test_state,
)

TURN = 7
PP = (PLUSPOWER, TURN)  # 今の番に使ったプラスパワー（今の番の終わりにトラッシュ）
DEF_OWN = (DEFENDER, TURN + 1)  # 今の番に自分が使ったディフェンダー
DEF_OPP = (DEFENDER, TURN)  # 前の相手の番に相手が使ったディフェンダー（今の番の終わりにトラッシュ）


def deal(attacker, target, *, receiver=None, base, prevent=False):
    """ワンリキー（闘）のワザ（けたぐり）として、``target`` に ``base`` の基本となるダメージを与えた結果と、前後の状態。"""
    receiver = receiver or {"card": HITMONCHAN}
    if prevent:
        receiver = {**receiver, "prevent_damage": TURN - 1}
    state = build_test_state([
        {"active": {"card": MACHOP, "energy": [FIGHTING], **attacker}},
        {"active": receiver},
    ], turn_number=TURN)
    work = state.clone()
    use = open_attack(work, 0)  # v0.16b: 解決の基盤のワザの枠（v0.13 の約束の補助関数は、枠の中でだけ使える）
    result = deal_attack_damage(work, use, target, base)
    return state, work, result


class DamageResultTableTest(unittest.TestCase):
    CASES = (
        # (名前, ワザを使うポケモン, 受けるポケモン, 受ける種類, 基本となるダメージ, 防ぐ, 期待する最終ダメージ, きぜつ)
        ("基本 0（2 段階で終わる）", {}, None, OPPONENT_ACTIVE, 0, False, 0, False),
        ("ふつう", {}, None, OPPONENT_ACTIVE, 20, False, 20, False),
        ("弱点 ×2", {}, {"card": RATTATA}, OPPONENT_ACTIVE, 10, False, 20, False),
        ("弱点でちょうど HP", {}, {"card": RATTATA, "damage": 10}, OPPONENT_ACTIVE, 10, False, 20, True),
        ("弱点で HP を超える（上限を付けない）", {}, {"card": RATTATA}, OPPONENT_ACTIVE, 30, False, 60, True),
        ("抵抗力で 0", {}, {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD]}, OPPONENT_ACTIVE, 20, False, 0, False),
        ("抵抗力で 10", {}, {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD]}, OPPONENT_ACTIVE, 40, False, 10, False),
        ("プラスパワー", {"trainers": [PP]}, None, OPPONENT_ACTIVE, 20, False, 30, False),
        ("ディフェンダー", {}, {"card": HITMONCHAN, "trainers": [DEF_OPP]}, OPPONENT_ACTIVE, 20, False, 0, False),
        ("ディフェンダーで負（0 にする）", {}, {"card": HITMONCHAN, "trainers": [DEF_OPP]}, OPPONENT_ACTIVE, 10, False, 0, False),
        ("プラスパワー + ディフェンダー", {"trainers": [PP]}, {"card": HITMONCHAN, "trainers": [DEF_OPP]}, OPPONENT_ACTIVE, 20, False, 10, False),
        ("防いだ", {}, {"card": METAPOD, "evolved_from": CATERPIE}, OPPONENT_ACTIVE, 20, True, None, False),
        ("防いだ（HP 近くのダメージ）", {}, {"card": METAPOD, "evolved_from": CATERPIE, "damage": 60}, OPPONENT_ACTIVE, 30, True, None, False),
        ("防いだ（プラスパワーも計算しない）", {"trainers": [PP]}, {"card": METAPOD, "evolved_from": CATERPIE}, OPPONENT_ACTIVE, 20, True, None, False),
        ("自分へ", {}, None, SELF, 10, False, 10, False),
        ("自分へ + プラスパワー（p.257）", {"trainers": [PP]}, None, SELF, 10, False, 20, False),
        ("自分へ + ディフェンダー（p.257）", {"trainers": [DEF_OWN]}, None, SELF, 10, False, 0, False),
        ("自分へ + 両方", {"trainers": [PP, DEF_OWN]}, None, SELF, 30, False, 20, False),
        ("自分へちょうど HP", {"damage": 40}, None, SELF, 10, False, 10, True),
        ("自分へ HP を超える", {"damage": 40}, None, SELF, 30, False, 30, True),
    )

    def test_table(self):
        for name, attacker, receiver, target, base, prevent, amount, knocked_out in self.CASES:
            with self.subTest(case=name):
                state, work, result = deal(attacker, target, receiver=receiver, base=base, prevent=prevent)
                owner = 0 if target == SELF else 1
                hit = work.players[owner].active
                before = state.players[owner].active
                self.assertEqual((result.target, result.player, result.pokemon_id), (target, owner, hit.pokemon_id))
                self.assertEqual((result.prevented, result.amount, result.knocked_out), (prevent, amount, knocked_out))
                self.assertEqual(result.dealt, amount or 0)  # p.319: 防いだ・0 は「ダメージを与えなかった」
                self.assertEqual(hit.damage, before.damage + (amount or 0))
                self.assertEqual(result.knocked_out, hit.damage >= work.card_def(hit.card).hp)
                event = dict(work.log[-1])
                if prevent:
                    self.assertEqual((event["kind"], event["pokemon_id"]), ("damage_prevented", hit.pokemon_id))
                    self.assertNotIn("amount", event)
                else:
                    self.assertEqual((event["kind"], event["amount"], event["total_damage"]), ("damage", amount, hit.damage))
                self.assertEqual(rng_fingerprint(work.rng), rng_fingerprint(state.rng))  # ダメージの計算は乱数を使わない
                self.assertEqual(full_damage(state), full_damage(state.clone()))  # 渡した状態は変わらない（複製に与えた）

    def test_prevented_is_never_knocked_out_by_the_element(self):
        """防いだ要素では、受けたポケモンのダメージは変わらない（場にいるポケモンのダメージは HP 未満なので、きぜつはいつも False）。"""
        for damage in (0, 30, 60):
            _, work, result = deal({}, OPPONENT_ACTIVE, receiver={"card": METAPOD, "evolved_from": CATERPIE, "damage": damage}, base=80, prevent=True)
            self.assertEqual((result.prevented, result.knocked_out, work.players[1].active.damage), (True, False, damage))


def full_damage(state):
    return [(pokemon.pokemon_id, pokemon.damage) for p in state.players for pokemon in p.in_play()]


# メガドレイン（40）で与えるダメージ: (名前, 受けるポケモン, バタフリーにつけるもの, 与えたダメージ（None は防いだ）, 相手がきぜつする)
DRAIN_TARGETS = (
    ("ふつう 40", {"card": HITMONCHAN}, [], 40, False),
    ("プラスパワー 50", {"card": HITMONCHAN}, [PP], 50, False),
    ("ディフェンダー 20", {"card": HITMONCHAN, "trainers": [DEF_OPP]}, [], 20, False),
    ("両方 30", {"card": HITMONCHAN, "trainers": [DEF_OPP]}, [PP], 30, False),
    ("ディフェンダー 2 枚 0", {"card": HITMONCHAN, "trainers": [DEF_OPP, DEF_OPP]}, [], 0, False),
    ("プラスパワー + ディフェンダー 2 枚 10", {"card": HITMONCHAN, "trainers": [DEF_OPP, DEF_OPP]}, [PP], 10, False),
    ("弱点 80（HP 30 を超える）", {"card": DIGLETT}, [], 80, True),
    ("弱点 + プラスパワー 90", {"card": DIGLETT}, [PP], 90, True),
    ("弱点 + ディフェンダー 60", {"card": DIGLETT, "trainers": [DEF_OPP]}, [], 60, True),
    ("HP 30 に 40", {"card": RATTATA}, [], 40, True),
    ("防いだ", {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1}, [], None, False),
)
OWN_DAMAGE = (0, 10, 20, 30, 40, 60)


class MegaDrainTableTest(unittest.TestCase):
    """メガドレイン（p.19）: 与えたダメージ × 自分にのっているダメージの表。とりのぞく数は min(与えたダメージのカウンターの数の
    半分の切り上げ, のっている数)。与えなかった（防いだ・最終ダメージ 0）なら回復しない（ログ drain_heal もない）。相手がきぜつしても
    回復する（「与えたダメージ」は HP で上限を付けない。p.319。SUPPORTED）。乱数を使わない。"""

    def test_table(self):
        for name, receiver, attachments, dealt, knocked_out in DRAIN_TARGETS:
            for own in OWN_DAMAGE:
                with self.subTest(target=name, own=own):
                    state = build_test_state([
                        {"active": {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS] * 4, "damage": own,
                                    "trainers": attachments}, "bench": [RATTATA]},
                        {"active": receiver, "bench": [RATTATA]},
                    ], turn_number=TURN)
                    attacker = state.players[0].active.pokemon_id
                    after = apply_command(state, UseAttack(0, 1))
                    events = [dict(e) for e in after.log[len(state.log):]]
                    heals = [e for e in events if e["kind"] == "drain_heal"]
                    healed = after.find_pokemon(attacker)[1].damage
                    if not dealt:
                        self.assertEqual(heals, [])
                        self.assertEqual(healed, own)
                    else:
                        drain = (dealt // 10 + 1) // 2
                        removed = min(drain, own // 10)
                        self.assertEqual(len(heals), 1)
                        self.assertEqual((heals[0]["dealt"], heals[0]["drain_counters"], heals[0]["counters"], heals[0]["amount"]),
                                         (dealt, drain, removed, removed * 10))
                        self.assertEqual((heals[0]["damage_before"], heals[0]["total_damage"], healed), (own, own - removed * 10, own - removed * 10))
                    self.assertEqual(any(e["kind"] == "knock_out" and e["player"] == 1 for e in events), knocked_out)
                    self.assertEqual(rng_fingerprint(after.rng), rng_fingerprint(state.rng))
                    self.assertEqual(check_invariants(after), [])


if __name__ == "__main__":
    unittest.main()

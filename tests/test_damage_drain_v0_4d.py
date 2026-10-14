"""与えたダメージの結果（``DamageResult``）と、与えたダメージに応じた回復（v0.4d）: バタフリー（PMCG2-007）の「メガドレイン」。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES）。分類は docs/damage-drain-v0.4d.md。

- p.19（バタフリー）: メガドレイン（草草草草）40。最新の説明「相手にダメージを与えたら、その半分（切り上げ）の
  ダメージカウンターを、自分からとりのぞく。」
- p.319:「最終的なダメージが0やマイナスの数字になることがあります。その場合、そのポケモンは「0ダメージを受けた（与えた）」
  「マイナスのダメージを受けた（与えた）」のではなく、「ダメージを受けなかった（与えなかった）」ことになります。」
  「HPが30のポケモンに対して50ダメージを与えるワザを使ったとき、「与えたダメージ」はあくまでも50です。HPが30しかない
  からといって、「与えたダメージ」が30になるのではありません。」「ダメージはかならず10の倍数なので、ダメージカウンター1個
  につき、10ダメージを受けていることを表します。」
- p.320:「ポケモンからすべてのダメージカウンターを取りのぞいてしまったら、もうそれ以上の回復はできません。」
- p.321: ダメージ計算の順番（弱点・抵抗力・プラスパワー（5）・ディフェンダー（7））。「ダメージを受けない」状態なら、
  そのポケモンにダメージを与えるワザの要素は無効
- p.309 の手順 5: こんらんしたワザは、もとのワザの内容に関わらず自分に 20

盤面を直接作るテスト（``build_test_state``）は 1 か所の規定を確かめるためのもので、自然な対戦の結果ではない。抵抗力 草の
ポケモンは対応カードにないので、ガーディの記録を写して抵抗力だけ変えたテスト専用のカード（実在のカードではない）を使う。
"""

import copy
import unittest

from kyuura_engine import EndTurn, Phase, PlayTrainer, ResolveDecision, UseAttack, apply_command, check_invariants, state_to_dict
from kyuura_engine.cards import pool_from_extract, read_extract
from kyuura_engine.effects import (
    DEFAULT_EFFECTS, OPPONENT_ACTIVE, SELF, AttackKey, DamageAndDrain, DamageResult, deal_attack_damage,
)
from kyuura_engine.rng import rng_fingerprint

from kyuura_engine.resolution import open_attack
from tests.helpers import (
    BUTTERFREE, CATERPIE, DEFENDER, DIGLETT, GRASS, GROWLITHE, H, METAPOD, PLUSPOWER, PONYTA, RATTATA, T, build_test_state,
    with_coin_results,
)

MEGA_DRAIN = 1
MEGA_DRAIN_LATEST = "相手にダメージを与えたら、その半分（切り上げ）のダメージカウンターを、自分からとりのぞく。"
GRASS4 = [GRASS, GRASS, GRASS, GRASS]
RESISTANT = "TEST-GRASS-RESIST"  # テスト専用: ガーディの記録の抵抗力を 草 -30 にしたカード（実在しない）


def full(state):
    return state_to_dict(state, format_version=8)


def run(state, command):
    new = apply_command(state, command)
    return new, [dict(e) for e in new.log[len(state.log):]]


def butterfree(**extra):
    return {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": GRASS4, **extra}


def resistant_pool():
    extract = copy.deepcopy(read_extract())
    record = copy.deepcopy(next(c for c in extract["cards"] if c["id"] == GROWLITHE))
    record["id"] = RESISTANT
    record["pokemon"]["resistances"] = [{"type": "grass", "operator": "-", "value": 30}]
    extract["cards"].append(record)
    return pool_from_extract(extract, DEFAULT_EFFECTS)


def board(mine=None, *, opponent=None, opponent_bench=(RATTATA,), hand=(), turn=7, prizes=6, pool=None, opponent_hand=(),
          current_player=0):
    return build_test_state([
        {"active": mine or butterfree(), "bench": [PONYTA], "hand": list(hand), "prizes": prizes},
        {"active": opponent or GROWLITHE, "bench": list(opponent_bench), "hand": list(opponent_hand)},
    ], current_player=current_player, turn_number=turn, pool=pool)


def defended(opponent, **kwargs):
    """6 番にプレイヤー 1 が対戦ポケモンにディフェンダーをつけ、7 番（プレイヤー 0 の番）を返す（つけるのは正式なコマンド）。"""
    state = board(opponent=opponent, opponent_hand=(DEFENDER,), turn=6, current_player=1, **kwargs)
    state = apply_command(state, PlayTrainer(1, state.players[1].hand[0]))
    state = apply_command(state, ResolveDecision(1, state.decision.id, (state.players[1].active.pokemon_id,)))
    return apply_command(state, EndTurn(1))


def mega_drain(state, *, pluspower=False):
    """プラスパワーを手札からつけてから（``pluspower``）、メガドレインを使う。ワザのログ（attack 以降）を返す。"""
    if pluspower:
        state = apply_command(state, PlayTrainer(0, next(u for u in state.players[0].hand if state.cards[u].card_id == PLUSPOWER)))
    return run(state, UseAttack(0, MEGA_DRAIN))


def heal_event(events):
    heals = [e for e in events if e["kind"] == "drain_heal"]
    assert len(heals) <= 1, heals
    return heals[0] if heals else None


# ---------------------------------------------------------------- ダメージの結果（8 章）


class DamageResultTest(unittest.TestCase):
    """``deal_attack_damage`` が返す結果: 計算した最終ダメージ・防いだこと・受けたポケモン・きぜつするか。ログ・ダメージの値は
    v0.4c と同じ（戻り値を使わない呼び出し側は変わらない）。"""

    def use(self, state):
        # v0.16b: 解決の基盤のワザの枠（v0.13 の約束の補助関数は、枠の中でだけ使える）
        use = open_attack(state, 0, attack_index=MEGA_DRAIN)
        self.assertEqual(use.key, AttackKey(BUTTERFREE, MEGA_DRAIN))
        return use

    def test_normal_damage(self):
        state = board()
        target = state.players[1].active
        result = deal_attack_damage(state, self.use(state), OPPONENT_ACTIVE, 40)
        self.assertEqual(result, DamageResult(OPPONENT_ACTIVE, 1, target.pokemon_id, False, 40, False))
        self.assertEqual(result.dealt, 40)
        event = dict(state.log[-1])
        self.assertEqual(set(event), {"kind", "turn", "player", "pokemon", "amount", "steps", "weakness", "resistance", "total_damage"})

    def test_amount_is_not_capped_by_hp(self):
        """HP の残りが 10 でも、最終ダメージ（与えたダメージ）は 40（p.319）。きぜつすることは別の項目で分かる。"""
        state = board(opponent={"card": RATTATA, "damage": 20})
        result = deal_attack_damage(state, self.use(state), OPPONENT_ACTIVE, 40)
        self.assertEqual((result.amount, result.dealt, result.knocked_out), (40, 40, True))

    def test_zero_is_calculated_but_not_dealt(self):
        """計算した結果の 0（p.319「与えなかった」）は ``amount`` 0。防いだときの None（計算していない）と区別する。"""
        state = board()
        result = deal_attack_damage(state, self.use(state), OPPONENT_ACTIVE, 0)
        self.assertEqual((result.prevented, result.amount, result.dealt), (False, 0, 0))
        self.assertTrue(state.log[-1]["stopped_after_step_2"])

    def test_prevented_is_not_calculated(self):
        state = board(opponent={"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": 6})
        result = deal_attack_damage(state, self.use(state), OPPONENT_ACTIVE, 40)
        self.assertEqual((result.prevented, result.amount, result.dealt, result.knocked_out), (True, None, 0, False))
        self.assertEqual(state.log[-1]["kind"], "damage_prevented")
        self.assertNotIn("amount", state.log[-1])

    def test_self_damage_result(self):
        state = board(butterfree(damage=50))
        result = deal_attack_damage(state, self.use(state), SELF, 20)
        self.assertEqual((result.target, result.player, result.pokemon_id, result.knocked_out),
                         (SELF, 0, state.players[0].active.pokemon_id, True))


# ---------------------------------------------------------------- メガドレイン（7・9・10 章・16.3）


class MegaDrainTest(unittest.TestCase):
    def test_registration(self):
        entry = DEFAULT_EFFECTS.attack_entry(BUTTERFREE, MEGA_DRAIN)
        self.assertIsInstance(entry.effect, DamageAndDrain)
        self.assertEqual((entry.name_ja, entry.play_text_ja, entry.source), ("メガドレイン", MEGA_DRAIN_LATEST, "P43 p.19"))
        attack = board().card_def(board().players[0].active.card).attacks[MEGA_DRAIN]
        self.assertEqual((attack.damage, [c.value for c in attack.cost]), (40, ["grass"] * 4))

    def test_base_damage_then_heal(self):
        """40 を与え、半分の 20（2 個）をとりのぞく。ダメージ → 回復 → ワザのあと（番の終わり）の順。乱数は使わない。"""
        state = board(butterfree(damage=30))
        fingerprint = rng_fingerprint(state.rng)
        new, events = mega_drain(state)
        self.assertEqual([e["kind"] for e in events][:4], ["attack", "damage", "drain_heal", "turn_end"])
        heal = heal_event(events)
        self.assertEqual({k: v for k, v in heal.items() if k not in ("kind", "turn")}, {
            "player": 0, "pokemon": state.players[0].active.card, "pokemon_id": state.players[0].active.pokemon_id,
            "effect": f"{BUTTERFREE}#1", "dealt": 40, "drain_counters": 2, "counters": 2, "amount": 20, "damage_before": 30,
            "total_damage": 10,
        })
        self.assertEqual((new.players[0].active.damage, new.players[1].active.damage), (10, 40))
        self.assertEqual(rng_fingerprint(new.rng), fingerprint)

    def test_dealt_damage_table(self):
        """回復するカウンターの数 = 与えたダメージ（最終ダメージ）の半分を、カウンター（10）の単位で切り上げ（p.19・p.319）。
        与えたダメージは、弱点・抵抗力・プラスパワー・ディフェンダーを計算したもの（p.321）。基本の 40 だけを見ない。"""
        pool = resistant_pool()
        cases = [
            # (説明, 盤面を作る関数, プラスパワー, 与えたダメージ, 半分の切り上げ)
            ("抵抗力 −30: 10", lambda: board(butterfree(damage=60), opponent=RESISTANT, pool=pool), False, 10, 1),
            ("ディフェンダー −20: 20", lambda: defended(GROWLITHE, mine=butterfree(damage=60)), False, 20, 1),
            ("抵抗力 −30 + プラスパワー +10: 20", lambda: board(butterfree(damage=60), opponent=RESISTANT, hand=(PLUSPOWER,), pool=pool), True, 20, 1),
            ("プラスパワー +10・ディフェンダー −20: 30", lambda: defended(GROWLITHE, mine=butterfree(damage=60), hand=(PLUSPOWER,)), True, 30, 2),
            ("基本: 40", lambda: board(butterfree(damage=60)), False, 40, 2),
            ("プラスパワー +10: 50", lambda: board(butterfree(damage=60), hand=(PLUSPOWER,)), True, 50, 3),
            ("弱点 ×2・ディフェンダー −20: 60", lambda: defended(DIGLETT, mine=butterfree(damage=60), opponent_bench=(RATTATA,)), False, 60, 3),
            ("弱点 ×2: 80", lambda: board(butterfree(damage=60), opponent=DIGLETT), False, 80, 4),
            ("弱点 ×2・プラスパワー +10: 90", lambda: board(butterfree(damage=60), opponent=DIGLETT, hand=(PLUSPOWER,)), True, 90, 5),
        ]
        for name, make, pluspower, dealt, counters in cases:
            with self.subTest(name=name):
                new, events = mega_drain(make(), pluspower=pluspower)
                damage = next(e for e in events if e["kind"] == "damage")
                self.assertEqual(damage["amount"], dealt)
                heal = heal_event(events)
                self.assertEqual((heal["dealt"], heal["drain_counters"], heal["counters"], heal["amount"]),
                                 (dealt, counters, counters, counters * 10))
                self.assertEqual(heal["total_damage"], 60 - counters * 10)
                self.assertEqual(check_invariants(new), [])

    def test_no_damage_dealt_no_heal(self):
        """最終ダメージが 0 以下（抵抗力 −30・ディフェンダー −20: 40 − 30 − 20 = −10）なら「ダメージを与えなかった」（p.319）ので、
        回復しない（ログ drain_heal もない）。"""
        new, events = mega_drain(defended(RESISTANT, mine=butterfree(damage=30), pool=resistant_pool()))
        self.assertEqual(next(e for e in events if e["kind"] == "damage")["amount"], 0)
        self.assertIsNone(heal_event(events))
        self.assertEqual(new.players[0].active.damage, 30)

    def test_prevented_damage_no_heal(self):
        """「ダメージを受けない」状態の相手: ダメージの要素は無効（p.321）。ダメージを与えていないので回復しない（SUPPORTED）。
        ワザは使ったことになり、番は終わる。"""
        state = board(butterfree(damage=30), opponent={"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": 6})
        new, events = mega_drain(state)
        # 番の終わりに、効果がはたらく番（7 番）の終わりがきた持続する効果が消える（v0.4b）
        self.assertEqual([e["kind"] for e in events][:4], ["attack", "damage_prevented", "persistent_effect_removed", "turn_end"])
        self.assertIsNone(heal_event(events))
        self.assertEqual((new.players[0].active.damage, new.current_player), (30, 1))

    def test_heal_is_capped_by_the_counters_on_butterfree(self):
        """のっているダメージカウンターより多くはとりのぞかない（p.320）。回復できる 2 個に対し、0 個 → 0、1 個 → 1、3 個 → 2。
        0 個でもダメージを与えたので、ログ drain_heal（counters 0）を残す。"""
        for damage, removed in ((0, 0), (10, 1), (20, 2), (30, 2)):
            with self.subTest(damage=damage):
                new, events = mega_drain(board(butterfree(damage=damage)))
                heal = heal_event(events)
                self.assertEqual((heal["drain_counters"], heal["counters"], heal["amount"], heal["damage_before"], heal["total_damage"]),
                                 (2, removed, removed * 10, damage, damage - removed * 10))
                self.assertEqual(new.players[0].active.damage, damage - removed * 10)

    def test_overkill_uses_the_dealt_damage_not_the_remaining_hp(self):
        """相手の残りの HP が 10 でも、与えたダメージは 40（p.319）。回復は 20（2 個）で、10（1 個）ではない。回復はワザの要素で、
        きぜつはワザのあとにまとめて判定する（回復 → きぜつ → サイド → 交代）。"""
        state = board(butterfree(damage=50), opponent={"card": RATTATA, "damage": 20})
        new, events = mega_drain(state)
        self.assertEqual([e["kind"] for e in events], ["attack", "damage", "drain_heal", "knock_out"])
        heal = heal_event(events)
        self.assertEqual((heal["dealt"], heal["counters"], heal["total_damage"]), (40, 2, 30))
        self.assertEqual((new.phase, new.decision.player), (Phase.TAKE_PRIZE, 0))

    def test_winning_with_mega_drain(self):
        """最後のサイドを取ったら勝ち（p.311）。回復はその前に済んでいる。"""
        state = board(butterfree(damage=40), opponent={"card": RATTATA, "damage": 20}, prizes=1)
        new, _ = mega_drain(state)
        done, events = run(new, ResolveDecision(0, new.decision.id, (0,)))
        self.assertEqual((done.phase, done.result.winner), (Phase.GAME_OVER, 0))
        self.assertEqual(done.players[0].active.damage, 20)

    def test_heal_targets_butterfree_only(self):
        """回復するのはワザを使ったバタフリー（場のポケモンの番号）だけ。ベンチのポケモンのダメージは変わらない。"""
        state = build_test_state([
            {"active": butterfree(damage=20), "bench": [{"card": PONYTA, "damage": 20}]},
            {"active": GROWLITHE, "bench": [RATTATA]},
        ], turn_number=7)
        new, events = mega_drain(state)
        self.assertEqual(heal_event(events)["pokemon_id"], state.players[0].active.pokemon_id)
        self.assertEqual((new.players[0].active.damage, new.players[0].bench[0].damage), (0, 20))

    def test_heal_happens_once(self):
        new, events = mega_drain(board(butterfree(damage=30)))
        self.assertEqual(sum(e["kind"] == "drain_heal" for e in new.log), 1)
        self.assertEqual(sum(e["kind"] == "damage" for e in new.log), 1)

    def test_not_enough_energy(self):
        state = board(butterfree(energy=[GRASS, GRASS, GRASS]))
        before = full(state)
        with self.assertRaises(Exception) as ctx:
            apply_command(state, UseAttack(0, MEGA_DRAIN))
        self.assertEqual(ctx.exception.code, "INSUFFICIENT_ENERGY")
        self.assertEqual(full(state), before)


class ConfusedMegaDrainTest(unittest.TestCase):
    def test_heads_drains(self):
        """こんらん状態でも、コインが「おもて」ならメガドレインをいつもどおり処理する（p.309 の手順 5・6）。"""
        state = board(butterfree(damage=30, confusion=True))
        new, events = run(with_coin_results(state, H), UseAttack(0, MEGA_DRAIN))
        self.assertEqual([e["kind"] for e in events][:5], ["attack", "coin_flip", "confusion_check", "damage", "drain_heal"])
        self.assertEqual(new.players[0].active.damage, 10)

    def test_tails_no_damage_no_heal(self):
        """「うら」ならワザがこんらんし、自分に 20（バタフリーは 草・弱点 炎なので 20）。相手へのダメージも回復もない。"""
        state = board(butterfree(damage=30, confusion=True))
        new, events = run(with_coin_results(state, T), UseAttack(0, MEGA_DRAIN))
        self.assertEqual([e["kind"] for e in events][:4], ["attack", "coin_flip", "confusion_check", "confusion_damage"])
        self.assertFalse(any(e["kind"] in ("damage", "drain_heal") for e in events))
        self.assertEqual((new.players[0].active.damage, new.players[1].active.damage), (50, 0))

    def test_rng_is_reproducible(self):
        outcomes = set()
        for _ in range(3):
            state = board(butterfree(damage=30, confusion=True), turn=7)
            new = apply_command(state, UseAttack(0, MEGA_DRAIN))
            outcomes.add((str(full(new)), rng_fingerprint(new.rng)))
        self.assertEqual(len(outcomes), 1)


if __name__ == "__main__":
    unittest.main()

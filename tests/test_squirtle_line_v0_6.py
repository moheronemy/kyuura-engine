"""ゼニガメ（PMCG1-023）→ カメール（PMCG1-027）→ カメックス（PMCG1-032）の進化とワザ（v0.6）: あわ・からにこもる・かみつく・
ハイドロポンプ。カメックスのポケモンパワー「あまごい」は tests/test_rain_dance_v0_6.py。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES）。照合の記録は
kyuura_engine/data/card_verification.json（300dpi。カードの図版の説明文は 600dpi）。

- p.87 ゼニガメ LV.8／HP40（ポケモンカード第1弾）: 水・あわ（水）10・からにこもる（水無）・にげる 1・弱点 雷。最新の説明
  「●あわ コインを投げて「おもて」なら、相手を「マヒ」状態にする。」「●からにこもる コインを投げて「おもて」なら、次の相手の番、
  このカードはダメージを受けない。（ダメージ以外の効果は受ける）」。解説「10ダメージを与えて、コイントスが表なら相手の対戦ポケモン
  をマヒ状態にします」
- p.88 カメール LV.22／HP70（ポケモンカード第1弾）: ゼニガメから進化・からにこもる（水無）・かみつく（水無無）40（説明文なし）・
  にげる 1・弱点 雷。同じページの上のカメール（サザンアイランド）の解説「水エネルギー5個までなら、進化したあとの「カメックス」の
  「ハイドロポンプ」で活用できる」「「カメックス」に進化して「ハイドロポンプ」を使えば、同じ水エネルギー4個で50ダメージ」
- p.90 カメックス LV.52／HP100（ポケモンカード第1弾）: カメールから進化・ハイドロポンプ（水水水）40+・にげる 3・弱点 雷。最新の説明
  「ワザに必要なエネルギーよりも多く「水」エネルギーがついているとき、多い「水」エネルギー1個につき、10ダメージを追加する。
  ダメージ追加は2個ぶんまで。」
- p.320: 目安の「+」は、書かれている数字よりダメージが大きくなることがある（説明にしたがう）。p.321: 説明にしたがった数が 1 段階
  （基本となるダメージ）で、そのあと弱点（3）・抵抗力（4）・プラスパワー（5）・ディフェンダー（7）
- からにこもるの印刷の文面「…次の相手の番に受けるダメージが0になる。」にはしたがわず、最新の説明（v0.4b の「かたまる」と同じ）に
  したがう（docs/persistent-damage-v0.4b.md）

盤面を直接作るテスト（``build_test_state``）は 1 か所の規定を確かめるためのもの。
"""

import dataclasses
import unittest

from kyuura_engine import EndTurn, EvolvePokemon, UseAttack, UsePokemonPower, apply_command, check_invariants, state_to_dict
from kyuura_engine.cards import EnergyType, load_card_pool, read_verification
from kyuura_engine.effects import DEFAULT_EFFECTS, ExtraEnergyDamage, ParalyzeOnHeads, PreventDamageOnHeads

from tests.helpers import (
    BLASTOISE, DEFENDER, FIRE, GROWLITHE, H, HITMONCHAN, PIKACHU, PLUSPOWER, RATTATA, SQUIRTLE, T, WARTORTLE, WATER, build_test_state,
    with_coin_results,
)

TURN = 7
HYDRO_LATEST = "ワザに必要なエネルギーよりも多く「水」エネルギーがついているとき、多い「水」エネルギー1個につき、10ダメージを追加する。ダメージ追加は2個ぶんまで。"
WITHDRAW_LATEST = "コインを投げて「おもて」なら、次の相手の番、このカードはダメージを受けない。（ダメージ以外の効果は受ける）"


def run(state, command):
    new = apply_command(state, command)
    return new, [dict(e) for e in new.log[len(state.log):]]


def kinds(events):
    return [e["kind"] for e in events]


def damages(events):
    return [(e["player"], e["amount"]) for e in events if e["kind"] == "damage"]


def board(active, *, opponent=HITMONCHAN, bench=(RATTATA,), hand=(), turn=TURN):
    return build_test_state([{"active": active, "bench": list(bench), "hand": list(hand)}, {"active": opponent, "bench": [RATTATA]}],
                            turn_number=turn)


def blastoise(energy, **extra):
    return {"card": BLASTOISE, "evolved_from": [SQUIRTLE, WARTORTLE], "energy": list(energy), **extra}


def wartortle(energy, **extra):
    return {"card": WARTORTLE, "evolved_from": SQUIRTLE, "energy": list(energy), **extra}


class CardValuesTest(unittest.TestCase):
    def test_squirtle_and_wartortle(self):
        """p.87・p.88 で照合した値。kyuura の記録と同じ（からにこもるの文面だけ、印刷の文面と最新の説明が違う）。"""
        pool = load_card_pool()
        s, w = pool.get(SQUIRTLE), pool.get(WARTORTLE)
        self.assertEqual((s.name_ja, s.is_basic_pokemon, s.hp, s.pokemon_type, s.weakness, s.resistance, s.retreat_cost, s.powers),
                         ("ゼニガメ", True, 40, EnergyType.WATER, EnergyType.LIGHTNING, None, 1, ()))
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage) for a in s.attacks],
                         [("あわ", ["water"], 10), ("からにこもる", ["water", "colorless"], None)])
        self.assertEqual((w.name_ja, w.evolves_from, w.hp, w.pokemon_type, w.weakness, w.resistance, w.retreat_cost, w.powers),
                         ("カメール", "ゼニガメ", 70, EnergyType.WATER, EnergyType.LIGHTNING, None, 1, ()))
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage, a.text_ja) for a in w.attacks],
                         [("からにこもる", ["water", "colorless"], None, "コインを投げて「おもて」なら、次の相手の番に受けるダメージが0になる。"),
                          ("かみつく", ["water", "colorless", "colorless"], 40, None)])
        self.assertTrue(all(pool.is_playable(c) for c in (SQUIRTLE, WARTORTLE, BLASTOISE)))
        records = read_verification()["cards"]
        self.assertEqual((records[SQUIRTLE]["page"], records[WARTORTLE]["page"], records[BLASTOISE]["page"]), (87, 88, 90))
        self.assertEqual(records[SQUIRTLE]["latest_description_ja"]["1"], WITHDRAW_LATEST)
        self.assertEqual(records[WARTORTLE]["latest_description_ja"], WITHDRAW_LATEST)
        self.assertEqual(records[BLASTOISE]["latest_description_ja"], HYDRO_LATEST)

    def test_registrations(self):
        """あわは ``ParalyzeOnHeads``（キャタピーの「いとをはく」と同じ実装）、からにこもるは ``PreventDamageOnHeads``（「かたまる」と同じ
        実装）、かみつくは効果のないワザ、ハイドロポンプは ``ExtraEnergyDamage(水, 10, 2)``。"""
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(SQUIRTLE, 0).effect, ParalyzeOnHeads())
        for card_id, index, page in ((SQUIRTLE, 1, 87), (WARTORTLE, 0, 88)):
            entry = DEFAULT_EFFECTS.attack_entry(card_id, index)
            self.assertEqual((entry.effect, entry.play_text_ja, entry.source), (PreventDamageOnHeads(), WITHDRAW_LATEST, f"P43 p.{page}"))
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(WARTORTLE, 1).effect.implementation_id, "damage_only")
        hydro = DEFAULT_EFFECTS.attack_entry(BLASTOISE, 0)
        self.assertEqual((hydro.effect, hydro.play_text_ja, hydro.source),
                         (ExtraEnergyDamage(energy_type=EnergyType.WATER, per_energy=10, max_extra=2), HYDRO_LATEST, "P43 p.90"))

    def test_extra_energy_damage_checks_the_data(self):
        """``ExtraEnergyDamage`` は、目安に「+」があり、必要なエネルギーがすべて同じタイプ（多い数が払い方で変わらない）のワザだけを
        登録できる。値の範囲も確かめる。"""
        effect = DEFAULT_EFFECTS.attack_entry(BLASTOISE, 0).effect
        attack = load_card_pool().get(BLASTOISE).attacks[0]
        self.assertEqual(effect.check(attack), [])
        self.assertTrue(effect.check(dataclasses.replace(attack, damage_modifier=None)))
        self.assertTrue(effect.check(dataclasses.replace(attack, cost=(EnergyType.WATER, EnergyType.COLORLESS))))
        self.assertTrue(effect.check(dataclasses.replace(attack, text_ja=None)))
        for bad in ({"per_energy": 0}, {"per_energy": 15}, {"max_extra": 0}, {"max_extra": True}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ExtraEnergyDamage(**{"energy_type": EnergyType.WATER, "per_energy": 10, "max_extra": 2, **bad})


class SquirtleAttackTest(unittest.TestCase):
    def test_bubble(self):
        """あわ: 相手に 10、そのあとコイン 1 枚。「おもて」なら相手をマヒ状態に、「うら」なら何もしない（p.87・p.320）。"""
        for side, paralyzed in ((H, True), (T, False)):
            with self.subTest(side=side):
                state = with_coin_results(board({"card": SQUIRTLE, "energy": [WATER]}), side)
                new, events = run(state, UseAttack(0, 0))
                self.assertEqual(damages(events), [(1, 10)])
                self.assertEqual([e["result"] for e in events if e["kind"] == "coin_flip"], [side.value])
                self.assertEqual(new.players[1].active.conditions.paralyzed, paralyzed)

    def test_bubble_knock_out_flips_no_coin(self):
        """相手の対戦ポケモンがあわのダメージできぜつしたら、マヒ状態にする対象がいないのでコインを投げない（p.309・p.323）。"""
        state = board({"card": SQUIRTLE, "energy": [WATER]}, opponent={"card": HITMONCHAN, "damage": 60})
        new, events = run(state, UseAttack(0, 0))
        self.assertNotIn("coin_flip", kinds(events))
        self.assertIn("knock_out", kinds(events))

    def test_withdraw(self):
        """からにこもる（ゼニガメ・カメール）: ダメージの目安なし。「おもて」なら持続する効果 ``PreventDamage``（次の相手の番、ダメージを
        受けない）。相手のワザのダメージは計算せずに ``damage_prevented``。「うら」なら何もしない。"""
        for active in ({"card": SQUIRTLE, "energy": [WATER, WATER]}, wartortle([WATER, FIRE])):
            for side in (H, T):
                with self.subTest(card=active["card"], side=side):
                    state = with_coin_results(board(active, opponent={"card": PIKACHU, "energy": [WATER, WATER]}), side)
                    attack = 1 if active["card"] == SQUIRTLE else 0
                    new, events = run(state, UseAttack(0, attack))
                    self.assertEqual(damages(events), [])
                    effects = new.players[0].active.persistent_effects
                    self.assertEqual([e.kind for e in effects], ["prevent_damage"] if side is H else [])
                    answered, events = run(new, UseAttack(1, 0))  # ピカチュウの「かじる」10
                    if side is H:
                        self.assertEqual([e["kind"] for e in events if e["kind"] in ("damage", "damage_prevented")], ["damage_prevented"])
                    else:
                        self.assertEqual(damages(events), [(0, 20)])  # かじる 10。ゼニガメ・カメールの弱点 雷 ×2
                    self.assertEqual(check_invariants(answered), [])

    def test_bite(self):
        """かみつく（カメール）: 水無無で 40（説明文なし）。足りなければ使えない。"""
        new, events = run(board(wartortle([WATER, FIRE, FIRE])), UseAttack(0, 1))
        self.assertEqual(damages(events), [(1, 40)])
        with self.assertRaises(Exception) as ctx:
            apply_command(board(wartortle([FIRE, FIRE, FIRE])), UseAttack(0, 1))
        self.assertEqual(ctx.exception.code, "INSUFFICIENT_ENERGY")


class HydroPumpTest(unittest.TestCase):
    def test_extra_water_energy(self):
        """ついている「水」エネルギーの数から必要な数（3）を引いた数（2 まで）× 10 を、目安の 40 に加える（p.90 の最新の説明。p.88 の解説
        「同じ水エネルギー4個で50ダメージ」「水エネルギー5個までなら…活用できる」）。水でないエネルギーは数えない。相手（エビワラー）は
        弱点・抵抗力なし。"""
        for energy, expected in (([WATER] * 3, 40), ([WATER] * 4, 50), ([WATER] * 5, 60), ([WATER] * 6, 60), ([WATER] * 7, 60),
                                 ([WATER] * 3 + [FIRE], 40), ([WATER] * 3 + [FIRE, FIRE], 40), ([WATER] * 4 + [FIRE], 50)):
            with self.subTest(energy=energy):
                _, events = run(board(blastoise(energy)), UseAttack(0, 0))
                self.assertEqual(damages(events), [(1, expected)])
                self.assertNotIn("coin_flip", kinds(events))  # 乱数を使わない

    def test_damage_steps(self):
        """追加したダメージは 1 段階（基本となるダメージ）で、弱点（ガーディ: 水 ×2）・プラスパワー（+10。5 段階）・ディフェンダー
        （-20。7 段階）はそのあと（p.321）。相手のディフェンダーは、相手の前の番（6）に使い、今の番（7）の終わりにトラッシュするもの。"""
        for spec, opponent, expected in (
            (blastoise([WATER] * 4), GROWLITHE, 100),  # (40 + 10) × 2
            (blastoise([WATER] * 5, trainers=[(PLUSPOWER, TURN)]), HITMONCHAN, 70),  # 60 + 10
            (blastoise([WATER] * 5), {"card": HITMONCHAN, "trainers": [(DEFENDER, TURN)]}, 40),  # 60 - 20
            (blastoise([WATER] * 5, trainers=[(PLUSPOWER, TURN)]), {"card": GROWLITHE, "trainers": [(DEFENDER, TURN)]}, 110),
        ):
            with self.subTest(expected=expected):
                state = build_test_state([{"active": spec}, {"active": opponent}], turn_number=TURN)
                _, events = run(state, UseAttack(0, 0))
                self.assertEqual(damages(events), [(1, expected)])

    def test_prevented_damage(self):
        """「ダメージを受けない」状態（からにこもるの「おもて」）の相手には、計算せずに ``damage_prevented``（p.321。コインがないので
        v0.4b の UNRESOLVED_PREVENTED_COIN_DAMAGE には当たらない）。"""
        state = board(blastoise([WATER] * 5), opponent={"card": SQUIRTLE, "prevent_damage": TURN - 1})
        new, events = run(state, UseAttack(0, 0))
        self.assertEqual(damages(events), [])
        self.assertIn("damage_prevented", kinds(events))
        self.assertEqual(new.players[1].active.damage, 0)

    def test_confused_blastoise(self):
        """こんらん状態のカメックスは、ワザの宣言のあとでコイン（p.309 の手順 5）。「うら」ならハイドロポンプの処理をせず、自分に 20
        （こんらんのダメージ。弱点・抵抗力だけ）。「おもて」ならいつもどおり。"""
        state = board(blastoise([WATER] * 4, confusion=True))
        _, events = run(with_coin_results(state, T), UseAttack(0, 0))
        self.assertEqual([e["amount"] for e in events if e["kind"] == "confusion_damage"], [20])
        self.assertEqual(damages(events), [])
        _, events = run(with_coin_results(state, H), UseAttack(0, 0))
        self.assertEqual(damages(events), [(1, 50)])

    def test_rain_dance_then_hydro_pump(self):
        """同じ番に、あまごいでつけた「水」エネルギーも数える（必要なエネルギー・多いエネルギーは、ワザを使うときについているもので決める。
        p.320）。水 3 → あまごいで 2 枚 → 60。"""
        state = board(blastoise([WATER] * 3), hand=(WATER, WATER))
        me = state.players[0]
        for water in list(me.hand):
            state = apply_command(state, UsePokemonPower(0, me.active.pokemon_id, 0, water, None, me.active.pokemon_id))
        _, events = run(state, UseAttack(0, 0))
        self.assertEqual(damages(events), [(1, 60)])


class EvolutionChainTest(unittest.TestCase):
    def test_squirtle_to_wartortle_to_blastoise(self):
        """ゼニガメ → カメール → カメックス（p.310。1 進化と 2 進化は別の番）。重なりは下から順、エネルギーと場のポケモンの番号は
        そのまま（v0.4a・v0.4c）。"""
        state = board({"card": SQUIRTLE, "energy": [WATER]}, hand=(WARTORTLE, BLASTOISE), turn=5)
        pid = state.players[0].active.pokemon_id
        hand = {state.cards[u].card_id: u for u in state.players[0].hand}
        state = apply_command(state, EvolvePokemon(0, hand[WARTORTLE], pid))
        with self.assertRaises(Exception) as ctx:
            apply_command(state, EvolvePokemon(0, hand[BLASTOISE], pid))
        self.assertEqual(ctx.exception.code, "EVOLVED_THIS_TURN")
        state = apply_command(apply_command(state, EndTurn(0)), EndTurn(1))
        state = apply_command(state, EvolvePokemon(0, hand[BLASTOISE], pid))
        active = state.players[0].active
        self.assertEqual((active.pokemon_id, state.cards[active.card].card_id, [state.cards[u].card_id for u in active.evolution_stack]),
                         (pid, BLASTOISE, [SQUIRTLE, WARTORTLE]))
        self.assertEqual(len(active.energy), 1)
        self.assertEqual(state_to_dict(state, format_version=9)["players"][0]["active"]["card_id"], BLASTOISE)
        self.assertEqual(check_invariants(state), [])


if __name__ == "__main__":
    unittest.main()

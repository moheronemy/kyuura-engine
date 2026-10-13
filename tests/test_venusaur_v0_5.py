"""フシギバナ（PMCG1-011。v0.5）とポケモンパワー「エナジートランス」: カードの照合・つけかえ・拒否・特殊状態・必要なエネルギーの
計算し直し・進化・にげる・ポケモンいれかえ・きぜつ・ログ。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES）。

- p.16: 見出し「フシギソウから進化 フシギバナ LV.67／HP100」「ポケモンカード第1弾」。図版: 2 進化・草・【特殊能力】エナジートランス・
  ソーラービーム（草草草草）60・にげる 2・弱点 炎・抵抗力なし。「特殊能力」欄の最新の説明「この力は、自分の番の中で何度でも使える。
  自分の場にいるポケモンについている「草」エネルギーを、自分の場にいる別のポケモンにつけかえる。このカードが「ねむり・マヒ・
  こんらん」状態のとき、この力は使えない。」。解説「すでに場に出ているので、その移動で10ダメージを受けることはありません」
  （つけかえは手札からエネルギーをつけることではない。SUPPORTED）
- p.323: 「使用を宣言して使う特殊能力もあります。」の例に、同じ最新の説明
- p.310: 手札からエネルギーをつけるのは 1 番に 1 回。進化しても、ついているエネルギーはそのまま
- p.311: にげるときは、にげるエネルギーの数だけトラッシュする。特に指示されていないかぎり、ベンチのポケモンも特殊能力を使える
- p.320: ワザに必要なエネルギー（ついているエネルギーで払えるか）
- p.313・p.323: きぜつしたら、ついているカードもトラッシュ

1 回の使用で 1 枚をつけかえるのは実装上の仮定（最新の説明は枚数を書かないが「何度でも使える」ので、何枚移しても 1 枚ずつ移した
結果と同じ。docs/energy-transfer-v0.5.md）。盤面を直接作るテスト（``build_test_state``）は 1 か所の規定を確かめるためのもの。
"""

import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, Phase, PlayTrainer, ResolveDecision, Retreat, UseAttack, UsePokemonPower,
    apply_command, check_invariants,
)
from kyuura_engine.cards import load_card_pool, read_extract, read_verification
from kyuura_engine.rng import rng_fingerprint

from tests.helpers import (
    BULBASAUR, BUTTERFREE, CATERPIE, FIRE, GRASS, GROWLITHE, HITMONCHAN, IVYSAUR, METAPOD, RATTATA, SWITCH, VENUSAUR, build_test_state,
)
from tests.test_pokemon_powers_v0_5 import (
    ENERGY_TRANS_PRINTED, assert_rejected, board, ivysaur, kinds, run, transfer, uid_of, venusaur,
)

SOLARBEAM_COST = ["grass"] * 4


def find(state, card_id, player=0):
    return next(pk for pk in state.players[player].in_play() if state.cards[pk.card].card_id == card_id)


class VenusaurCardTest(unittest.TestCase):
    def test_card_values(self):
        """p.16 で照合した値（300dpi・図版は 400dpi）: 「フシギソウから進化」の 2 進化、HP 100、草、弱点 炎（×2）、抵抗力なし、
        にげる 2、ポケモンパワー 1 つ、ワザ 1 つ（説明文なし）。"""
        pool = load_card_pool()
        d = pool.get(VENUSAUR)
        self.assertTrue(d.supported and pool.is_playable(VENUSAUR) and d.is_stage2_pokemon)
        self.assertEqual((d.name_ja, d.evolves_from, d.hp, d.pokemon_type.value, d.weakness.value, d.resistance, d.retreat_cost),
                         ("フシギバナ", "フシギソウ", 100, "grass", "fire", None, 2))
        self.assertEqual([(w.name_ja, w.text_ja) for w in d.powers], [("エナジートランス", ENERGY_TRANS_PRINTED)])
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage, a.damage_modifier, a.text_ja) for a in d.attacks],
                         [("ソーラービーム", SOLARBEAM_COST, 60, None, None)])
        self.assertEqual((pool.get(IVYSAUR).name_ja, pool.get(IVYSAUR).evolves_from, pool.get(BULBASAUR).name_ja), ("フシギソウ", "フシギダネ", "フシギダネ"))
        self.assertEqual(read_extract()["pool_v0_5"], [BULBASAUR, IVYSAUR, VENUSAUR])
        self.assertNotIn(VENUSAUR, read_extract()["reference_only"])  # v0.4e までは参照カードだった
        record = read_verification()["cards"][VENUSAUR]
        self.assertEqual(record["mismatches"][0]["field"], "pokemon.powers[0].text.ja")


# ---------------------------------------------------------------- つけかえ


class EnergyTransMoveTest(unittest.TestCase):
    def test_moves_the_same_card(self):
        """同じ uid のエネルギーカードを、移動元から移動先へ移す（複製しない・なくさない・トラッシュしない・持ち主は変わらない）。
        手札からつけた回数（``energy_attachments_this_turn``）・乱数は変えない。ログは ``pokemon_power`` → ``move_energy``。"""
        for attached in (0, 1):
            with self.subTest(energy_attachments_this_turn=attached):
                state = board(energy_attachments_this_turn=attached)
                me = state.players[0]
                v, b = me.active, me.bench[0]
                energy = v.energy[1]
                new, events = run(state, transfer(state, energy, v, b))
                p = new.players[0]
                self.assertEqual((p.active.energy, p.bench[0].energy), (v.energy[:1], [*b.energy, energy]))
                self.assertEqual((new.cards[energy].owner, new.cards[energy].card_id), (0, GRASS))
                self.assertNotIn(energy, (*p.hand, *p.discard, *p.deck, *p.prizes))
                self.assertEqual(sorted(new.cards), sorted(state.cards))
                self.assertEqual(new.energy_attachments_this_turn, attached)
                self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(state.rng))
                self.assertEqual(kinds(events), ["pokemon_power", "move_energy"])
                declared, moved = events
                self.assertEqual({k: declared[k] for k in ("player", "pokemon", "pokemon_id", "power", "power_index", "turn")},
                                 {"player": 0, "pokemon": v.card, "pokemon_id": v.pokemon_id, "power": "エナジートランス", "power_index": 0,
                                  "turn": state.turn_number})
                self.assertEqual({k: v_ for k, v_ in moved.items() if k != "kind"},
                                 {"player": 0, "pokemon": v.card, "pokemon_id": v.pokemon_id, "power": "PMCG1-011@power0",
                                  "energy": energy, "from_pokemon_id": v.pokemon_id, "to_pokemon_id": b.pokemon_id,
                                  "turn": state.turn_number})
                self.assertNotIn("attach_energy", kinds(events))
                self.assertEqual(check_invariants(new), [])

    def test_every_pair_of_own_pokemon(self):
        """移動元・移動先は自分の場のポケモン（バトル場・ベンチ。フシギバナ自身を含む）で、移動先は移動元と別のポケモン。
        フシギバナはバトル場でもベンチでも使える（p.311「特に指示されていないかぎり、ベンチにいるポケモンも」）。"""
        for venusaur_on_bench in (False, True):
            others = [{"card": BULBASAUR, "energy": [GRASS]}, ivysaur(energy=[GRASS, GRASS]), {"card": RATTATA, "energy": [GRASS]}]
            v = venusaur(energy=[GRASS, GRASS])
            state = board(active=others[0], bench=[v, *others[1:]]) if venusaur_on_bench else board(active=v, bench=others)
            me = state.players[0]
            pokemon = me.in_play()
            checked = 0
            for source in pokemon:
                for target in pokemon:
                    if source is target:
                        continue
                    with self.subTest(venusaur_on_bench=venusaur_on_bench, source=source.pokemon_id, target=target.pokemon_id):
                        new = apply_command(state, transfer(state, source.energy[0], source, target))
                        moved = {pk.pokemon_id: list(pk.energy) for pk in new.players[0].in_play()}
                        self.assertEqual(moved[source.pokemon_id], source.energy[1:])
                        self.assertEqual(moved[target.pokemon_id], [*target.energy, source.energy[0]])
                        checked += 1
            self.assertEqual(checked, 12)

    def test_any_venusaur_can_be_the_user(self):
        """フシギバナが 2 匹いれば、どちらの特殊能力でも同じつけかえができる（1 回の番の中で複数のポケモンが宣言してよい。p.311）。"""
        state = board(active=venusaur(energy=[GRASS]), bench=[venusaur(energy=[GRASS]), {"card": BULBASAUR}], turn=7)
        me = state.players[0]
        first, second, bulbasaur = me.in_play()
        results = []
        for user in (first, second):
            new, events = run(state, transfer(state, first.energy[0], first, bulbasaur, user=user))
            results.append([list(pk.energy) for pk in new.players[0].in_play()])
            self.assertEqual(events[0]["pokemon_id"], user.pokemon_id)
        self.assertEqual(results[0], results[1])
        both = apply_command(state, transfer(state, first.energy[0], first, bulbasaur, user=first))
        both = apply_command(both, transfer(both, second.energy[0], both.players[0].bench[0], both.players[0].bench[1], user=second))
        self.assertEqual([len(pk.energy) for pk in both.players[0].in_play()], [0, 0, 2])

    def test_moving_back_and_forth(self):
        """同じエネルギーを、同じ番に何度でも動かせる（行って戻ると、もとの場所に戻る。ログは 2 回）。"""
        state = board()
        me = state.players[0]
        v, b = me.active, me.bench[0]
        energy = v.energy[0]
        there = apply_command(state, transfer(state, energy, v, b))
        back = apply_command(there, transfer(there, energy, there.players[0].bench[0], there.players[0].active))
        self.assertEqual(sorted(back.players[0].active.energy), sorted(v.energy))
        self.assertEqual(back.players[0].bench[0].energy, b.energy)
        self.assertEqual(sum(e["kind"] == "move_energy" for e in back.log), 2)

    def test_user_needs_no_energy(self):
        """エネルギーカードをつけていないフシギバナも使える（p.311・p.323「エネルギーカードをつけていなくても」）。"""
        state = board(active=venusaur(), bench=[{"card": BULBASAUR, "energy": [GRASS]}, {"card": RATTATA}])
        me = state.players[0]
        new = apply_command(state, transfer(state, me.bench[0].energy[0], me.bench[0], me.bench[1]))
        self.assertEqual([len(pk.energy) for pk in new.players[0].in_play()], [0, 0, 1])

    def test_attaching_from_hand_is_a_separate_action(self):
        """手札からつける（1 番に 1 回。p.310）のとは別: つけかえたあとも手札からつけられ、手札からつけたあともつけかえられる。
        手札からもう一度つけるのは、つけかえのあとでも ``ENERGY_ALREADY_ATTACHED``。"""
        state = board(hand=[GRASS, GRASS])
        me = state.players[0]
        moved = apply_command(state, transfer(state, me.active.energy[0], me.active, me.bench[0]))
        attached = apply_command(moved, AttachEnergy(0, uid_of(moved, 0, GRASS), moved.players[0].active.card))
        self.assertEqual(attached.energy_attachments_this_turn, 1)
        again = apply_command(attached, transfer(attached, attached.players[0].active.energy[0], attached.players[0].active,
                                                 attached.players[0].bench[0]))
        self.assertEqual(again.energy_attachments_this_turn, 1)
        assert_rejected(self, again, AttachEnergy(0, uid_of(again, 0, GRASS), again.players[0].active.card), "ENERGY_ALREADY_ATTACHED")


# ---------------------------------------------------------------- 拒否


class EnergyTransRejectionTest(unittest.TestCase):
    def test_choices_must_be_valid(self):
        """選ばせるもの（エネルギー・移動元・移動先）が足りない・正しくなければ、状態を変えずに拒否する。"""
        state = board(active=venusaur(energy=[GRASS, FIRE]), bench=[{"card": BULBASAUR, "energy": [GRASS]}, {"card": RATTATA}],
                      hand=[GRASS], opponent={"card": GROWLITHE, "energy": [GRASS]}, discard=[GRASS])
        me, opponent = state.players
        v, b, r = me.in_play()
        grass, fire = v.energy
        user = v.pokemon_id
        hand_grass = me.hand[0]
        cases = [
            (UsePokemonPower(0, user), "POWER_CHOICE_MISSING"),
            (UsePokemonPower(0, user, 0, grass, v.pokemon_id, None), "POWER_CHOICE_MISSING"),
            (UsePokemonPower(0, user, 0, grass, None, b.pokemon_id), "POWER_CHOICE_MISSING"),
            (UsePokemonPower(0, user, 0, None, v.pokemon_id, b.pokemon_id), "POWER_CHOICE_MISSING"),
            (UsePokemonPower(0, user, 0, grass, 999, b.pokemon_id), "SOURCE_NOT_IN_PLAY"),
            (UsePokemonPower(0, user, 0, grass, v.pokemon_id, 0), "TARGET_NOT_IN_PLAY"),
            # 相手の場のポケモンについている「草」エネルギー・相手の場のポケモンへのつけかえ
            (UsePokemonPower(0, user, 0, opponent.active.energy[0], opponent.active.pokemon_id, b.pokemon_id), "SOURCE_NOT_YOURS"),
            (UsePokemonPower(0, user, 0, grass, v.pokemon_id, opponent.active.pokemon_id), "TARGET_NOT_YOURS"),
            (UsePokemonPower(0, user, 0, grass, v.pokemon_id, v.pokemon_id), "SAME_POKEMON"),
            # 移動元についていないエネルギー（ほかのポケモン・手札・トラッシュ・ポケモンのカード・ない uid）
            (UsePokemonPower(0, user, 0, b.energy[0], v.pokemon_id, r.pokemon_id), "ENERGY_NOT_ATTACHED"),
            (UsePokemonPower(0, user, 0, hand_grass, v.pokemon_id, b.pokemon_id), "ENERGY_NOT_ATTACHED"),
            (UsePokemonPower(0, user, 0, me.discard[0], v.pokemon_id, b.pokemon_id), "ENERGY_NOT_ATTACHED"),
            (UsePokemonPower(0, user, 0, b.card, v.pokemon_id, r.pokemon_id), "ENERGY_NOT_ATTACHED"),
            (UsePokemonPower(0, user, 0, 9999, v.pokemon_id, b.pokemon_id), "ENERGY_NOT_ATTACHED"),
            # 「草」エネルギーだけをつけかえる（炎エネルギーは動かせない）
            (UsePokemonPower(0, user, 0, fire, v.pokemon_id, b.pokemon_id), "WRONG_ENERGY_TYPE"),
        ]
        for command, code in cases:
            with self.subTest(command=command, code=code):
                assert_rejected(self, state, command, code)


# ---------------------------------------------------------------- 特殊状態（使うポケモン・移動元・移動先）


# 使うポケモン（バトル場のフシギバナ）の特殊状態の 8 通り（どくはほかと重なる。ねむり・マヒ・こんらんは重ならない。p.322）
USER_STATES = [
    ({}, None),
    ({"poison": 10}, None),
    ({"sleep": True}, "POKEMON_ASLEEP"),
    ({"paralysis": 6}, "POKEMON_PARALYZED"),  # 相手の番（6 番）にマヒ状態になった（盤面は 7 番）
    ({"confusion": True}, "POKEMON_CONFUSED"),
    ({"poison": 10, "sleep": True}, "POKEMON_ASLEEP"),
    ({"poison": 10, "paralysis": 7}, "POKEMON_PARALYZED"),  # 自分の番（7 番）にマヒ状態になった（盤面を直接作った）
    ({"poison": 10, "confusion": True}, "POKEMON_CONFUSED"),
]


class SpecialConditionTest(unittest.TestCase):
    def test_user_conditions(self):
        """このカード（フシギバナ）がねむり・マヒ・こんらんなら使えない（p.16・p.323 の最新の説明）。どくだけなら使える（説明に
        挙げられていない。p.323「特に記述されていないかぎり、…いつでも、何度でも」）。ワザ・にげるの制限（ねむり・マヒだけ・
        こんらんはコイン）を流用していない。"""
        for conditions, code in USER_STATES:
            with self.subTest(conditions=conditions):
                state = board(active=venusaur(energy=[GRASS, GRASS], **conditions))
                me = state.players[0]
                command = transfer(state, me.active.energy[0], me.active, me.bench[0])
                if code is None:
                    new = apply_command(state, command)
                    self.assertEqual(new.players[0].active.conditions, me.active.conditions)  # 特殊状態は変えない
                    self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(state.rng))  # こんらんのコインはない
                else:
                    assert_rejected(self, state, command, code)

    def test_condition_of_another_pokemon_does_not_matter(self):
        """使うポケモンがベンチのフシギバナ（特殊状態にならない。p.322）なら、バトル場のポケモンがどの特殊状態でも使え、そのポケモンを
        移動元・移動先にできる（説明が制限するのは「このカード」だけ）。"""
        for conditions, _ in USER_STATES:
            for role in ("source", "target"):
                with self.subTest(conditions=conditions, role=role):
                    active = {"card": BULBASAUR, "energy": [GRASS], **conditions}
                    state = board(active=active, bench=[venusaur(energy=[GRASS])])
                    me = state.players[0]
                    a, v = me.active, me.bench[0]
                    source, target = (a, v) if role == "source" else (v, a)
                    new = apply_command(state, transfer(state, source.energy[0], source, target, user=v))
                    self.assertEqual(new.players[0].active.conditions, a.conditions)
                    self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(state.rng))

    def test_asleep_venusaur_and_a_second_venusaur(self):
        """バトル場のフシギバナがねむりでも、ベンチの別のフシギバナは使える（使えないのは「このカード」）。バトル場のねむりの
        フシギバナについている「草」エネルギーも、移動元にできる。"""
        state = board(active=venusaur(energy=[GRASS, GRASS], sleep=True), bench=[venusaur(), {"card": BULBASAUR}], turn=7)
        me = state.players[0]
        asleep, awake, bulbasaur = me.in_play()
        assert_rejected(self, state, transfer(state, asleep.energy[0], asleep, bulbasaur, user=asleep), "POKEMON_ASLEEP")
        new = apply_command(state, transfer(state, asleep.energy[0], asleep, bulbasaur, user=awake))
        self.assertEqual(len(new.players[0].bench[1].energy), 1)


# ---------------------------------------------------------------- 必要なエネルギーの計算し直し


class CostRecomputationTest(unittest.TestCase):
    def test_attack_cost(self):
        """ワザに必要なエネルギーは、ワザを使うときについているエネルギーで決まる（p.320）。つけかえで払えるようになり、
        つけかえで払えなくなる。"""
        state = board(active=venusaur(energy=[GRASS] * 3), opponent=HITMONCHAN)
        me = state.players[0]
        assert_rejected(self, state, UseAttack(0, 0), "INSUFFICIENT_ENERGY")
        ready = apply_command(state, transfer(state, me.bench[0].energy[0], me.bench[0], me.active))
        attacked, events = run(ready, UseAttack(0, 0))
        self.assertEqual([(e["kind"], e.get("amount")) for e in events if e["kind"] == "damage"], [("damage", 60)])
        away = apply_command(ready, transfer(ready, ready.players[0].active.energy[0], ready.players[0].active, ready.players[0].bench[0]))
        assert_rejected(self, away, UseAttack(0, 0), "INSUFFICIENT_ENERGY")

    def test_retreat_cost(self):
        """にげるときにトラッシュするのは、そのときバトル場のポケモンについているエネルギー（p.311）。つけかえたエネルギーで払え、
        移したエネルギーは選べない。トラッシュしたエネルギーはトラッシュに置く。"""
        state = board(active=venusaur(energy=[GRASS]))
        me = state.players[0]
        v, b = me.active, me.bench[0]
        assert_rejected(self, state, Retreat(0, (v.energy[0],), b.card), "WRONG_RETREAT_COST")
        moved = apply_command(state, transfer(state, b.energy[0], b, v))
        retreated = apply_command(moved, Retreat(0, (v.energy[0], b.energy[0]), b.card))
        self.assertEqual(retreated.players[0].active.pokemon_id, b.pokemon_id)
        self.assertEqual(retreated.players[0].discard[-2:], [v.energy[0], b.energy[0]])
        self.assertEqual(retreated.players[0].bench[0].energy, [])
        away = apply_command(state, transfer(state, v.energy[0], v, b))
        assert_rejected(self, away, Retreat(0, (v.energy[0], b.energy[0]), b.card), "ENERGY_NOT_ATTACHED")


# ---------------------------------------------------------------- 進化・入れ替え・きぜつ


class EvolutionInterplayTest(unittest.TestCase):
    def test_energy_moved_before_evolution_stays(self):
        """つけかえたエネルギーは、そのポケモンが進化してもついたまま（p.310）。"""
        state = board(bench=[{"card": BULBASAUR}], hand=[IVYSAUR])
        me = state.players[0]
        moved = apply_command(state, transfer(state, me.active.energy[0], me.active, me.bench[0]))
        evolved = apply_command(moved, EvolvePokemon(0, uid_of(moved, 0, IVYSAUR), me.bench[0].pokemon_id))
        self.assertEqual(evolved.players[0].bench[0].energy, [me.active.energy[0]])
        self.assertEqual(evolved.cards[evolved.players[0].bench[0].card].card_id, IVYSAUR)

    def test_venusaur_can_use_the_power_in_the_turn_it_evolved(self):
        """フシギソウから進化したその番に、フシギバナの特殊能力を使える（進化した番に使えないという規定はない。p.310・p.311）。
        進化の前（フシギソウ）は特殊能力がない（NO_POKEMON_POWER）。"""
        state = board(active=ivysaur(energy=[GRASS, GRASS]), hand=[VENUSAUR], turn=5)
        me = state.players[0]
        command = transfer(state, me.active.energy[0], me.active, me.bench[0], user=me.active)
        assert_rejected(self, state, command, "NO_POKEMON_POWER")
        evolved = apply_command(state, EvolvePokemon(0, uid_of(state, 0, VENUSAUR), me.active.pokemon_id))
        new = apply_command(evolved, command)
        self.assertEqual(len(new.players[0].bench[0].energy), 2)

    def test_switch_and_retreat_keep_the_energy(self):
        """ポケモンいれかえ・にげるで入れ替わっても、つけかえたエネルギーはついたまま。ベンチに移ったフシギバナも続けて使える。"""
        state = board(bench=[{"card": BULBASAUR, "energy": [GRASS]}], hand=[SWITCH])
        me = state.players[0]
        moved = apply_command(state, transfer(state, me.bench[0].energy[0], me.bench[0], me.active))
        switched = apply_command(moved, PlayTrainer(0, uid_of(moved, 0, SWITCH)))
        if switched.phase is Phase.DECISION:
            switched = apply_command(switched, ResolveDecision(0, switched.decision.id, (me.bench[0].pokemon_id,)))
        p = switched.players[0]
        self.assertEqual((p.active.pokemon_id, p.bench[0].pokemon_id), (me.bench[0].pokemon_id, me.active.pokemon_id))
        self.assertEqual(len(p.bench[0].energy), 3)
        again = apply_command(switched, transfer(switched, p.bench[0].energy[0], p.bench[0], p.active))
        self.assertEqual([len(pk.energy) for pk in again.players[0].in_play()], [1, 2])

    def test_forced_switch_keeps_the_energy(self):
        """相手のバタフリーの「ふきとばし」でベンチに移ったフシギバナは、ついたエネルギーのまま（強制交代はエネルギーを変えない。
        v0.4d）。次の自分の番に、ベンチから使える。"""
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}
        state = build_test_state([
            {"active": venusaur(energy=[GRASS] * 3), "bench": [{"card": BULBASAUR}]},
            {"active": butterfree, "bench": [RATTATA]},
        ], current_player=1, turn_number=8)
        v = state.players[0].active
        attacked = apply_command(state, UseAttack(1, 0))
        self.assertIs(attacked.phase, Phase.DECISION)
        self.assertEqual(attacked.decision.player, 0)  # 入れ替わるポケモンは相手（フシギバナの側）が選ぶ
        switched = apply_command(attacked, ResolveDecision(0, attacked.decision.id, (state.players[0].bench[0].pokemon_id,)))
        self.assertEqual((switched.current_player, switched.turn_number), (0, 9))
        p = switched.players[0]
        self.assertEqual((p.bench[0].pokemon_id, p.bench[0].energy, p.bench[0].damage), (v.pokemon_id, v.energy, 20))
        new = apply_command(switched, transfer(switched, v.energy[0], p.bench[0], p.active))
        self.assertEqual(new.players[0].active.energy, [v.energy[0]])

    def test_moved_energy_is_discarded_with_the_knocked_out_pokemon(self):
        """つけかえたエネルギーは、ついているポケモンがきぜつしたら、そのポケモンといっしょにトラッシュ（p.313・p.323）。
        ほかのポケモンについているエネルギーはそのまま。"""
        state = board(active={"card": BULBASAUR}, bench=[venusaur(energy=[GRASS, GRASS])], opponent={"card": GROWLITHE, "energy": [FIRE, FIRE]},
                      opponent_bench=[RATTATA], turn=7)
        me = state.players[0]
        b, v = me.active, me.bench[0]
        moved = apply_command(state, transfer(state, v.energy[0], v, b))
        theirs = apply_command(moved, EndTurn(0))
        attacked = apply_command(theirs, UseAttack(1, 0))  # ガーディの「ほのお」20。フシギダネ（HP 40）の弱点は炎なので 40
        knocked = [e for e in attacked.log[len(theirs.log):] if e["kind"] == "knock_out"]
        self.assertEqual([e["pokemon"] for e in knocked], [b.card])
        self.assertIn(v.energy[0], attacked.players[0].discard)
        self.assertEqual(find(attacked, VENUSAUR).energy, [v.energy[1]])


if __name__ == "__main__":
    unittest.main()

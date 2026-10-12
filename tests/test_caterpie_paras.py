"""キャタピー（PMCG1-002）の「いとをはく」とパラス（PMCG2-003）の「ひっかく」「キノコのほうし」（v0.3b）。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura のカードの記録 PMCG1-002・PMCG2-003、NEO-2000-OFFICIAL-RULES）:

- p.17 のキャタピー（LV.13/HP40、第1弾）: 草、いとをはく（草）10、にげる 1、弱点 炎。最新の説明「●いとをはく コインを投げて
  「おもて」なら、相手を「マヒ」状態にする。」。解説「マヒ状態にされたポケモンは、ワザを使うことも逃げることもできません」
- p.38 のパラス（LV.8/HP40、第2弾ポケモンジャングル）: 草、ひっかく（無無）20（説明なし）、キノコのほうし（草草）ダメージの
  目安の数字なし、にげる 1、弱点 炎。最新の説明「●キノコのほうし 相手を「ねむり」状態にする。」。解説「相手の対戦ポケモンを
  確実にねむり状態にできるのですが、ダメージを与えることはできません」
- p.320: ダメージの目安に「×」がなければ、説明の最初の「相手に○○ダメージ。」が省略されている（シードラの「あわ」の例:
  10 ダメージ → コイン → マヒ）。p.309: ワザの説明の順番に処理し、対象がいなくなった内容は無視する
- p.257: プラスパワーは「このカードをつけているポケモンのワザが、対戦ポケモンにダメージを与えるとき」に +10

ねむり・マヒの規定そのものは test_sleep_paralysis.py・test_pokemon_check_v0_3b.py。
"""

import unittest

from kyuura_engine import (
    EndTurn, EngineError, PlayTrainer, ResolveDecision, Retreat, UseAttack, apply_command, check_invariants, load_card_pool,
    state_to_dict,
)
from kyuura_engine.cards import read_extract, read_verification
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackKey, DamageOnly, ParalyzeOnHeads, PutToSleep
from kyuura_engine.rng import copy_rng, rng_fingerprint
from kyuura_engine.state import ASLEEP, NO_SPECIAL_CONDITIONS, Paralyzed, SpecialConditions

from tests.helpers import (
    CATERPIE, DEFENDER, DIGLETT, FIGHTING, FIRE, GRASS, GROWLITHE, H, PARAS, PLUSPOWER, PONYTA, RATTATA, T, WEEDLE,
    build_test_state, with_coin_results,
)

STRING_SHOT = 0
SCRATCH, SPORE = 0, 1


def full(state):
    return state_to_dict(state, format_version=5)


def kinds(events):
    return [e["kind"] for e in events]


def hand(state, player, card_id):
    return [u for u in state.players[player].hand if state.cards[u].card_id == card_id]


def vs(attacker, defender, *coins, energy=(GRASS,), damage=0, hand_cards=(), their_hand=(), their_bench=(RATTATA,)):
    state = build_test_state([
        {"active": {"card": attacker, "energy": list(energy)}, "bench": [PONYTA], "hand": list(hand_cards)},
        {"active": {"card": defender, "damage": damage}, "bench": list(their_bench), "hand": list(their_hand)},
    ])
    return with_coin_results(state, *coins) if coins else state


def use(state, index, player=0):
    start = len(state.log)
    new = apply_command(state, UseAttack(player, index))
    return new, [dict(e) for e in new.log[start:]]


class RegistrationTest(unittest.TestCase):
    def test_registered_attacks(self):
        records = read_verification()["cards"]
        for card_id, index, implementation, name, page in (
            (CATERPIE, STRING_SHOT, ParalyzeOnHeads, "いとをはく", 17),
            (PARAS, SPORE, PutToSleep, "キノコのほうし", 38),
        ):
            with self.subTest(card_id=card_id):
                entry = DEFAULT_EFFECTS.attack_entry(card_id, index)
                self.assertIsInstance(entry.effect, implementation)
                self.assertEqual((entry.name_ja, entry.source), (name, f"P43 p.{page}"))
                record = records[card_id]
                self.assertEqual((record["status"], record["page"], record["pdf_page"]), ("一致", page, page + 2))
                self.assertEqual(entry.play_text_ja, record["latest_description_ja"])
                self.assertEqual(entry.text_ja, entry.play_text_ja)  # kyuura の説明文は最新の説明と同じ
                self.assertTrue(load_card_pool().is_playable(card_id))
        scratch = DEFAULT_EFFECTS.attack_entry(PARAS, SCRATCH)
        self.assertIsInstance(scratch.effect, DamageOnly)
        self.assertEqual((scratch.name_ja, scratch.text_ja, scratch.source), ("ひっかく", None, None))
        self.assertEqual(read_extract()["pool_v0_3b"], [CATERPIE, PARAS])

    def test_card_data_matches_the_book(self):
        pool = load_card_pool()
        caterpie, paras = pool.get(CATERPIE), pool.get(PARAS)
        self.assertEqual((caterpie.name_ja, caterpie.hp, caterpie.pokemon_type.value, caterpie.retreat_cost, caterpie.weakness.value,
                          caterpie.resistance), ("キャタピー", 40, "grass", 1, "fire", None))
        (string_shot,) = caterpie.attacks
        self.assertEqual((string_shot.name_ja, [c.value for c in string_shot.cost], string_shot.damage, string_shot.damage_modifier),
                         ("いとをはく", ["grass"], 10, None))
        self.assertEqual((paras.name_ja, paras.hp, paras.pokemon_type.value, paras.retreat_cost, paras.weakness.value, paras.resistance),
                         ("パラス", 40, "grass", 1, "fire", None))
        scratch, spore = paras.attacks
        self.assertEqual((scratch.name_ja, [c.value for c in scratch.cost], scratch.damage, scratch.text_ja),
                         ("ひっかく", ["colorless", "colorless"], 20, None))
        self.assertEqual((spore.name_ja, [c.value for c in spore.cost], spore.damage, spore.damage_display, spore.text_ja),
                         ("キノコのほうし", ["grass", "grass"], None, None, "相手を「ねむり」状態にする。"))

    def test_wrong_registrations_are_detected(self):
        """登録の誤り（効果のない・ダメージのあるワザに、ねむりの実装をつけるなど）は check で見つかる。"""
        pool = load_card_pool()
        spore, scratch = pool.get(PARAS).attacks[SPORE], pool.get(PARAS).attacks[SCRATCH]
        string_shot = pool.get(CATERPIE).attacks[STRING_SHOT]
        self.assertEqual(PutToSleep().check(spore), [])
        self.assertTrue(PutToSleep().check(scratch))  # ダメージの目安がある・説明文がない
        self.assertTrue(PutToSleep().check(string_shot))  # ダメージの目安がある
        self.assertEqual(ParalyzeOnHeads().check(string_shot), [])
        self.assertTrue(ParalyzeOnHeads().check(spore))  # ダメージの目安の数字がない
        self.assertTrue(ParalyzeOnHeads().check(scratch))  # 説明文がない
        self.assertTrue(DamageOnly().check(spore))  # ダメージ 0 のワザとして登録できない
        unregistered = DEFAULT_EFFECTS.without_attacks("test-no-spore", [AttackKey(PARAS, SPORE)])
        self.assertIsNotNone(unregistered.attack_problem(PARAS, spore))


# ---------------------------------------------------------------- キャタピー


class StringShotTest(unittest.TestCase):
    def test_heads_damage_then_coin_then_paralysis(self):
        """相手に 10 → コイン 1 枚 → 「おもて」ならマヒ（p.309・p.320 の順。あわの例と同じ形）。"""
        state = vs(CATERPIE, GROWLITHE, H)
        new, events = use(state, STRING_SHOT)
        self.assertEqual(kinds(events)[:4], ["attack", "damage", "coin_flip", "special_condition"])
        damage, coin = events[1], events[2]
        self.assertEqual((damage["player"], damage["amount"]), (1, 10))
        self.assertEqual((coin["player"], coin["source"], coin["effect"], coin["count"], coin["result"]), (0, "attack", "PMCG1-002#0", 1, "heads"))
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(exclusive=Paralyzed(turn=3)))
        self.assertEqual(new.players[1].active.damage, 10)
        self.assertEqual(check_invariants(new), [])

    def test_tails_only_damage(self):
        new, events = use(vs(CATERPIE, GROWLITHE, T), STRING_SHOT)
        self.assertEqual(kinds(events)[:4], ["attack", "damage", "coin_flip", "turn_end"])
        self.assertEqual((new.players[1].active.conditions, new.players[1].active.damage), (NO_SPECIAL_CONDITIONS, 10))

    def test_weakness_applies_to_the_damage(self):
        """ディグダ（弱点 草）: 10 × 2 = 20（p.321 の 3 段階）。HP30 なのできぜつしない。"""
        new, events = use(vs(CATERPIE, DIGLETT, H), STRING_SHOT)
        damage = next(e for e in events if e["kind"] == "damage")
        self.assertEqual((damage["amount"], damage["weakness"]), (20, True))
        self.assertTrue(new.players[1].active.conditions.paralyzed)

    def test_knocked_out_target_no_coin(self):
        """いとをはくの 10 で相手がきぜつしたら、マヒにする内容は対象がいないので無視する。コインも投げない（p.309・p.323）。"""
        state = vs(CATERPIE, RATTATA, H, damage=20)
        fingerprint = rng_fingerprint(state.rng)
        new, events = use(state, STRING_SHOT)
        self.assertEqual(kinds(events)[:3], ["attack", "damage", "knock_out"])
        self.assertNotIn("coin_flip", kinds(events))
        self.assertEqual(rng_fingerprint(new.rng), fingerprint)

    def test_paralysis_does_not_depend_on_the_damage(self):
        """マヒにするのは効果。ディフェンダーでダメージが 0 でも「おもて」ならマヒ（どくばりと同じ。p.320・p.321）。"""
        state = vs(CATERPIE, GROWLITHE, their_hand=[DEFENDER])
        state = apply_command(state, EndTurn(0))
        state = apply_command(state, PlayTrainer(1, hand(state, 1, DEFENDER)[0]))
        state = apply_command(state, ResolveDecision(1, state.decision.id, (state.players[1].active.pokemon_id,)))
        state = apply_command(state, EndTurn(1))
        new, events = use(with_coin_results(state, H), STRING_SHOT)
        damage = next(e for e in events if e["kind"] == "damage")
        self.assertEqual(damage["amount"], 0)
        self.assertEqual(new.players[1].active.conditions.exclusive, Paralyzed(turn=5))

    def test_requires_one_grass_energy(self):
        for energy in ((), (FIRE,), (FIGHTING,)):
            with self.subTest(energy=energy):
                state = vs(CATERPIE, GROWLITHE, H, energy=energy)
                before, fingerprint = full(state), rng_fingerprint(state.rng)
                with self.assertRaises(EngineError) as ctx:
                    apply_command(state, UseAttack(0, STRING_SHOT))
                self.assertEqual(ctx.exception.code, "INSUFFICIENT_ENERGY")
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))

    def test_reproducible(self):
        state = vs(CATERPIE, GROWLITHE)
        a, b = apply_command(state, UseAttack(0, STRING_SHOT)), apply_command(state.clone(), UseAttack(0, STRING_SHOT))
        self.assertEqual(full(a), full(b))
        expected = copy_rng(state.rng)
        heads = expected.getrandbits(1)
        self.assertEqual(a.players[1].active.conditions.paralyzed, bool(heads))


# ---------------------------------------------------------------- パラス


class SporeTest(unittest.TestCase):
    def test_no_damage_element(self):
        """キノコのほうしはダメージを与えない（ダメージ 0 ではない）。damage のログがなく、ダメージの計算もしない。プラスパワー
        （ワザがダメージを与えるとき +10。p.257）も関係しない。コインも投げない（ポケモンチェックのねむりのコインは別）。"""
        state = vs(PARAS, GROWLITHE, T, energy=(GRASS, GRASS), hand_cards=[PLUSPOWER])
        state = apply_command(state, PlayTrainer(0, hand(state, 0, PLUSPOWER)[0]))
        new, events = use(state, SPORE)
        self.assertEqual(kinds(events)[:2], ["attack", "special_condition"])
        self.assertNotIn("damage", kinds(events))
        self.assertEqual(new.players[1].active.damage, 0)
        self.assertEqual([e["source"] for e in events if e["kind"] == "coin_flip"], ["pokemon_check"])
        attack = events[0]
        self.assertEqual((attack["attack"], attack["attack_index"]), ("キノコのほうし", SPORE))
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(exclusive=ASLEEP))

    def test_spore_against_weakness_and_resistance_has_no_damage(self):
        """弱点・抵抗力の計算もない（ダメージがないので）。ディグダ（弱点 草）でもダメージ 0 のまま。"""
        new, events = use(vs(PARAS, DIGLETT, T, energy=(GRASS, GRASS)), SPORE)
        self.assertNotIn("damage", kinds(events))
        self.assertEqual(new.players[1].active.damage, 0)

    def test_requires_two_grass_energy(self):
        for energy in ((GRASS,), (GRASS, FIRE), (FIRE, FIRE)):
            with self.subTest(energy=energy):
                state = vs(PARAS, GROWLITHE, energy=energy)
                with self.assertRaises(EngineError) as ctx:
                    apply_command(state, UseAttack(0, SPORE))
                self.assertEqual(ctx.exception.code, "INSUFFICIENT_ENERGY")

    def test_scratch_is_plain_damage(self):
        """ひっかく（無無）20: 説明のないワザ（p.309 の手順 6）。草・炎のどちらでも払える。"""
        new, events = use(vs(PARAS, GROWLITHE, energy=(FIRE, FIRE)), SCRATCH)
        self.assertEqual(kinds(events)[:3], ["attack", "damage", "turn_end"])
        self.assertEqual((events[1]["amount"], new.players[1].active.conditions), (20, NO_SPECIAL_CONDITIONS))

    def test_sleep_recovery_after_spore(self):
        """ねむりにした番の終わりのポケモンチェックで、相手がコインを投げる（「おもて」なら回復）。"""
        new, events = use(vs(PARAS, GROWLITHE, H, energy=(GRASS, GRASS)), SPORE)
        self.assertEqual(new.players[1].active.conditions, NO_SPECIAL_CONDITIONS)
        removed = next(e for e in events if e["kind"] == "special_conditions_removed")
        self.assertEqual((removed["player"], removed["reason"]), (1, "sleep_coin"))

    def test_reproducible(self):
        state = vs(PARAS, GROWLITHE, energy=(GRASS, GRASS))
        results = {state_to_dict(apply_command(state.clone(), UseAttack(0, SPORE)), format_version=5)["rng_state_sha256"] for _ in range(3)}
        self.assertEqual(len(results), 1)
        expected = copy_rng(state.rng)
        heads = expected.getrandbits(1)
        new = apply_command(state, UseAttack(0, SPORE))
        self.assertEqual(new.players[1].active.conditions.asleep, not heads)

    def test_weedle_and_paras_give_poison_and_sleep(self):
        """どくばり（どく）のあとにキノコのほうし（ねむり）: 両方の状態になる（p.322「どく状態は、他の特殊状態と重複します」）。"""
        state = build_test_state([
            {"active": {"card": WEEDLE, "energy": [GRASS]}, "bench": [{"card": PARAS, "energy": [GRASS, GRASS]}]},
            {"active": {"card": GROWLITHE, "energy": [FIRE]}, "bench": [RATTATA]},
        ])
        state = with_coin_results(state, H)
        state = apply_command(state, UseAttack(0, 0))  # どくばり「おもて」
        state = apply_command(state, EndTurn(1))
        # プレイヤー 0 はビードルをにがしてパラスを出す（にげる 1）
        weedle = state.players[0].active
        state = apply_command(state, Retreat(0, (weedle.energy[0],), state.players[0].bench[0].card))
        state = with_coin_results(state, T)
        new, _ = use(state, SPORE)
        self.assertEqual(new.players[1].active.conditions.names(), ("poison", "sleep"))
        self.assertEqual(new.players[1].active.damage, 10 + 10 + 10 + 10)  # どくばり 10 + どく 10 × 3


if __name__ == "__main__":
    unittest.main()

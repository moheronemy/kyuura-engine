"""こんらん状態のポケモンのワザ（v0.3c）とロコン（PMCG1-015）の「あやしいひかり」。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES。rule_differences.json の
confusion_attack の「2000年2月」の行。カードの記録 PMCG1-015）:

- p.67 のロコン（LV.11/HP50、第1弾）。最新の説明「●あやしいひかり コインを投げて「おもて」なら、相手を「こんらん」状態に
  する。」
- p.309「バトル場にいるポケモンのワザを使う」の手順: 1 ワザを使えなくなる効果 → 2 必要なエネルギー → 3 宣言 → 4 ワザを
  失敗させたり内容を変える効果 → 5「ワザを使うポケモンがこんらん状態なら、以下のように、ワザがこんらんするかどうかを
  チェックします」「ワザを使うポケモン側のプレイヤーは、コインを1枚投げます。「うら」が出たら、ワザがこんらんします。ワザが
  こんらんすると、もとのワザの内容に関わらず、ワザを使ったポケモン自身が20ダメージを受けます」→ 6 ワザの説明にしたがって処理
- p.322「4. こんらん状態」: 「「おもて」が出たときは、ワザにこんらん状態による影響は出ません。「うら」が出たら、そのワザの
  内容がどのようなものであっても、ワザを使ったポケモン自身に、20ダメージを与えます」「このダメージは「弱点・抵抗力」の影響を
  受けます」
- p.321「9」: 3「ワザを使うポケモンのタイプが、ワザを受けるポケモンの「弱点」となるタイプなら、ダメージを2倍」、4 抵抗力。
  計算の結果 0 やマイナスなら「ダメージを受けなかった」
- p.323「12 ワザの失敗」: 「ワザが失敗した場合でも、そのポケモンは、そのワザを使ったことになります」。「16」きぜつ・サイド
- p.257 のプラスパワー・ディフェンダーの最新の説明（「ワザが…ダメージを与える時」「ワザによるダメージを受けるとき」）

分類（CONFIRMED・SUPPORTED・UNRESOLVED）は docs/confusion-attacks-v0.3c.md。
"""

import copy
import unittest

from kyuura_engine import (
    EndTurn, EngineError, Phase, PlayTrainer, ResolveDecision, TakePrize, UnsupportedError, UseAttack, apply_command,
    check_invariants, load_card_pool, state_to_dict,
)
from kyuura_engine.cards import pool_from_extract, read_extract, read_verification
from kyuura_engine.damage import calculate_confusion_damage
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackEntry, AttackKey, ConfuseOnHeads, SelfDamageOnTails
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.rules import RULES_2000_02_14
from kyuura_engine.state import ASLEEP, CONFUSED, NO_SPECIAL_CONDITIONS, Paralyzed, Poison, SpecialConditions

from tests.helpers import (
    CATERPIE, CHARMANDER, DEFENDER, DIGLETT, DODUO, FIGHTING, FIRE, GRASS, GROWLITHE, H, LIGHTNING, PARAS, PIKACHU,
    PLUSPOWER, PONYTA, RATTATA, STARYU, T, VULPIX, WEEDLE, build_test_state, with_coin_results,
)

CONFUSE_RAY = 0
SELF_WEAK = "TEST-VULPIX-WEAK-TO-FIRE"
SELF_RESISTANT = "TEST-VULPIX-RESISTS-FIRE"
SELF_BOTH = "TEST-VULPIX-WEAK-AND-RESISTS-FIRE"


def full(state):
    return state_to_dict(state, format_version=6)


def kinds(events):
    return [e["kind"] for e in events]


def hand(state, player, card_id):
    return [u for u in state.players[player].hand if state.cards[u].card_id == card_id]


def confused(attacker=VULPIX, *sides, energy=(FIRE, FIRE), damage=0, defender=GROWLITHE, defender_spec=None, bench=(PONYTA,),
             their_bench=(RATTATA,), prizes=6, their_prizes=6, hand_cards=(), poisoned=False, pool=None, effects=None):
    """プレイヤー 0（3 番の番）の対戦ポケモン ``attacker`` がこんらん状態。"""
    spec = {"card": attacker, "energy": list(energy), "damage": damage, "confusion": True}
    if poisoned:
        spec["poison"] = 10
    state = build_test_state([
        {"active": spec, "bench": list(bench), "hand": list(hand_cards), "prizes": prizes},
        {"active": {"card": defender, **(defender_spec or {})}, "bench": list(their_bench), "prizes": their_prizes},
    ], pool=pool, effects=effects)
    return with_coin_results(state, *sides) if sides else state


def attack(state, index=CONFUSE_RAY, player=0):
    start = len(state.log)
    new = apply_command(state, UseAttack(player, index))
    return new, [dict(e) for e in new.log[start:]]


def assert_unchanged_rejection(test, state, command, code, error=EngineError):
    before, fingerprint = full(state), rng_fingerprint(state.rng)
    with test.assertRaises(error) as ctx:
        apply_command(state, command)
    test.assertEqual(ctx.exception.code, code)
    test.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))


def play_all(state, card_id, player=0, target=None):
    for card in hand(state, player, card_id):
        state = apply_command(state, PlayTrainer(player, card))
        if state.decision is not None:  # ディフェンダー: つけるポケモンを選ぶ
            pokemon_id = target if target is not None else state.players[player].active.pokemon_id
            state = apply_command(state, ResolveDecision(player, state.decision.id, (pokemon_id,)))
    return state


def self_typed_pool():
    """ロコンの記録を写して、弱点・抵抗力を自分のタイプ（炎）にしたテスト専用のカード（実在しない）。"""
    extract = copy.deepcopy(read_extract())
    source = next(c for c in extract["cards"] if c["id"] == VULPIX)
    weak = copy.deepcopy(source)
    weak["id"] = SELF_WEAK
    weak["pokemon"]["weaknesses"] = [{"type": "fire", "operator": "×", "value": 2}]
    resistant = copy.deepcopy(source)
    resistant["id"] = SELF_RESISTANT
    resistant["pokemon"]["weaknesses"] = []
    resistant["pokemon"]["resistances"] = [{"type": "fire", "operator": "-", "value": 30}]
    both = copy.deepcopy(source)
    both["id"] = SELF_BOTH
    both["pokemon"]["weaknesses"] = [{"type": "fire", "operator": "×", "value": 2}]
    both["pokemon"]["resistances"] = [{"type": "fire", "operator": "-", "value": 30}]
    extract["cards"] += [weak, resistant, both]
    text = source["pokemon"]["attacks"][0]["text"]["ja"]
    effects = DEFAULT_EFFECTS.with_attacks("test-self-typed-vulpix", {
        AttackKey(card, CONFUSE_RAY): AttackEntry(ConfuseOnHeads(), "あやしいひかり", text_ja=text) for card in (SELF_WEAK, SELF_RESISTANT, SELF_BOTH)
    })
    return pool_from_extract(extract, effects), effects


# ---------------------------------------------------------------- ロコンの登録と照合（3 章）


class VulpixRegistrationTest(unittest.TestCase):
    def test_registered_attack(self):
        """p.67: 「ワザ」欄「●あやしいひかり コインを投げて「おもて」なら、相手を「こんらん」状態にする。」（照合の記録）。"""
        entry = DEFAULT_EFFECTS.attack_entry(VULPIX, CONFUSE_RAY)
        self.assertIsInstance(entry.effect, ConfuseOnHeads)
        self.assertEqual((entry.name_ja, entry.source, entry.effect.implementation_id), ("あやしいひかり", "P43 p.67", "confuse_on_heads"))
        record = read_verification()["cards"][VULPIX]
        self.assertEqual((record["page"], record["pdf_page"], record["status"]), (67, 69, "一致"))
        self.assertEqual(entry.play_text_ja, record["latest_description_ja"])
        self.assertEqual(entry.text_ja, load_card_pool().get(VULPIX).attacks[CONFUSE_RAY].text_ja)
        self.assertEqual(len(load_card_pool().get(VULPIX).attacks), 1)

    def test_card_data_matches_the_book(self):
        """p.67 の見出し「たねポケモン ロコン LV.11／HP50」と図版（炎、炎炎 10、にげる 1、弱点 水、抵抗力なし）。"""
        vulpix = load_card_pool().get(VULPIX)
        self.assertTrue(vulpix.supported and vulpix.is_basic_pokemon)
        self.assertEqual((vulpix.hp, vulpix.pokemon_type.value, vulpix.weakness.value, vulpix.resistance, vulpix.retreat_cost),
                         (50, "fire", "water", None, 1))
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage, a.damage_modifier) for a in vulpix.attacks],
                         [("あやしいひかり", ["fire", "fire"], 10, None)])

    def test_wrong_registrations_are_detected(self):
        pool = load_card_pool()
        doduo_attack = pool.get(DODUO).attacks[0]  # みだれづき（「×」）
        effects = DEFAULT_EFFECTS.with_attacks("test-bad", {
            AttackKey(DODUO, 0): AttackEntry(ConfuseOnHeads(), "みだれづき", text_ja=doduo_attack.text_ja),
            AttackKey(PARAS, 1): AttackEntry(ConfuseOnHeads(), "キノコのほうし", text_ja=pool.get(PARAS).attacks[1].text_ja),
            AttackKey(GROWLITHE, 0): AttackEntry(ConfuseOnHeads(), "ほのお"),
        })
        self.assertIn("「×」", effects.attack_problem(DODUO, doduo_attack))
        self.assertIn("10 の倍数", effects.attack_problem(PARAS, pool.get(PARAS).attacks[1]))
        self.assertIn("説明文のない", effects.attack_problem(GROWLITHE, pool.get(GROWLITHE).attacks[0]))


# ---------------------------------------------------------------- あやしいひかり（3 章）


class ConfuseRayTest(unittest.TestCase):
    def board(self, *sides, defender=GROWLITHE, damage=0, their_hand=(), energy=(FIRE, FIRE)):
        state = build_test_state([
            {"active": {"card": VULPIX, "energy": list(energy)}, "bench": [PONYTA]},
            {"active": {"card": defender, "damage": damage}, "bench": [RATTATA], "hand": list(their_hand)},
        ])
        return with_coin_results(state, *sides) if sides else state

    def test_damage_then_coin_in_the_order_written(self):
        """相手に 10（省略された「相手の対戦ポケモンに10ダメージ。」。p.320）→ コイン → こんらん。コインは使う側が投げる。"""
        new, events = attack(self.board(H))
        self.assertEqual(kinds(events)[:4], ["attack", "damage", "coin_flip", "special_condition"])
        flip = events[2]
        self.assertEqual((flip["player"], flip["source"], flip["effect"], flip["count"]), (0, "attack", "PMCG1-015#0", 1))
        self.assertEqual(new.players[1].active.damage, 10)
        self.assertEqual((new.phase, new.current_player, new.turn_number), (Phase.MAIN, 1, 4))

    def test_tails_does_nothing_more(self):
        new, events = attack(self.board(T))
        self.assertEqual(kinds(events)[:3], ["attack", "damage", "coin_flip"])
        self.assertNotIn("special_condition", kinds(events))
        self.assertEqual(new.players[1].active.conditions, NO_SPECIAL_CONDITIONS)

    def test_weakness_applies_to_the_damage(self):
        """ロコン（炎）→ パラス（弱点 炎）: 10 × 2 = 20（p.321 の 3）。"""
        new, events = attack(self.board(T, defender=PARAS))
        damage = next(e for e in events if e["kind"] == "damage")
        self.assertEqual((damage["amount"], damage["weakness"]), (20, True))

    def test_knocked_out_target_flips_no_coin(self):
        """相手の対戦ポケモンがこのワザのダメージできぜつしたら、こんらんにする内容は対象がいないので無視する（p.309・p.323）。"""
        state = self.board(defender=RATTATA, damage=20)
        new, events = attack(state)
        self.assertNotIn("coin_flip", kinds(events))
        self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(state.rng))
        self.assertEqual(new.phase, Phase.TAKE_PRIZE)

    def test_confusion_is_an_effect_not_damage(self):
        """ディフェンダー（p.257）でダメージが 0 になっても、「おもて」ならこんらん状態にする（効果はダメージではない）。"""
        state = build_test_state([
            {"active": {"card": VULPIX, "energy": [FIRE, FIRE]}, "bench": [PONYTA]},
            {"active": GROWLITHE, "bench": [RATTATA], "hand": [DEFENDER]},
        ], current_player=1, turn_number=4)
        state = play_all(state, DEFENDER, player=1)
        state = apply_command(state, EndTurn(1))
        new, events = attack(with_coin_results(state, H))
        damage = next(e for e in events if e["kind"] == "damage")
        self.assertEqual(damage["amount"], 0)
        self.assertTrue(new.players[1].active.conditions.confused)

    def test_insufficient_energy_flips_no_coin(self):
        assert_unchanged_rejection(self, self.board(H, energy=(FIRE,)), UseAttack(0, CONFUSE_RAY), "INSUFFICIENT_ENERGY")


# ---------------------------------------------------------------- こんらん状態のポケモンのワザ（5 章）


class ConfusedAttackOrderTest(unittest.TestCase):
    def test_coin_after_the_declaration(self):
        """手順 3 の宣言（ログ ``attack``）のあとで、手順 5 のこんらんのコイン（``source: "confusion"``）を投げる。
        「おもて」ならワザにこんらんの影響はなく、手順 6 でワザの説明のコイン（``source: "attack"``）を投げる。"""
        new, events = attack(confused(VULPIX, H, H))
        self.assertEqual(kinds(events)[:6], ["attack", "coin_flip", "confusion_check", "damage", "coin_flip", "special_condition"])
        confusion_flip, check, attack_flip = events[1], events[2], events[4]
        vulpix = new.players[0].active
        self.assertEqual({k: confusion_flip[k] for k in ("player", "source", "effect", "card", "pokemon_id", "count", "result")},
                         {"player": 0, "source": "confusion", "effect": "PMCG1-015#0", "card": vulpix.card,
                          "pokemon_id": vulpix.pokemon_id, "count": 1, "result": "heads"})
        self.assertEqual({k: check[k] for k in ("player", "pokemon", "pokemon_id", "action", "result", "succeeded")},
                         {"player": 0, "pokemon": vulpix.card, "pokemon_id": vulpix.pokemon_id, "action": "attack",
                          "result": "heads", "succeeded": True})
        self.assertEqual((attack_flip["source"], attack_flip["effect"]), ("attack", "PMCG1-015#0"))
        self.assertTrue(vulpix.conditions.confused)  # ワザを使ってもこんらんは消えない
        self.assertEqual(vulpix.damage, 0)

    def test_tails_replaces_the_whole_attack(self):
        """「うら」: もとのワザの内容に関わらず（相手へのダメージ・効果・ワザ自身のコインはない）、自分に 20。ワザは使った
        ことになり、番が終わる（p.309・p.322・p.323）。乱数はこんらんのコイン 1 枚だけ。"""
        state = confused(VULPIX, T)
        new, events = attack(state)
        self.assertEqual(kinds(events)[:6], ["attack", "coin_flip", "confusion_check", "confusion_damage", "turn_end", "pokemon_check"])
        self.assertEqual(sum(e["kind"] == "coin_flip" for e in events), 1)
        self.assertNotIn("damage", kinds(events))
        own = events[3]
        vulpix = new.players[0].active
        self.assertEqual({k: own[k] for k in ("player", "pokemon", "pokemon_id", "effect", "amount", "steps", "weakness",
                                              "resistance", "total_damage")},
                         {"player": 0, "pokemon": vulpix.card, "pokemon_id": vulpix.pokemon_id, "effect": "PMCG1-015#0",
                          "amount": 20, "steps": (("こんらん", 20),), "weakness": False, "resistance": False, "total_damage": 20})
        self.assertFalse(events[2]["succeeded"])
        self.assertEqual((new.players[1].active.damage, new.players[1].active.conditions), (0, NO_SPECIAL_CONDITIONS))
        self.assertEqual((vulpix.damage, vulpix.conditions), (20, SpecialConditions(exclusive=CONFUSED)))
        self.assertEqual(vulpix.energy, state.players[0].active.energy)  # エネルギーはトラッシュしない
        self.assertEqual((new.phase, new.current_player, new.turn_number), (Phase.MAIN, 1, 4))
        self.assertEqual(check_invariants(new), [])

    def test_every_registered_attack(self):
        """登録しているワザの種類ごとに、「おもて」なら手順 6 の処理、「うら」なら 20 ダメージだけ。"""
        cases = [
            # (ポケモン, ワザ, エネルギー, 「おもて」のあとのコイン, 「おもて」で相手が受けるダメージ, 「おもて」で相手の状態)
            (GROWLITHE, 0, (FIRE, FIRE), (), 20, NO_SPECIAL_CONDITIONS),
            (DODUO, 0, (FIRE,), (H, T), 10, NO_SPECIAL_CONDITIONS),
            (PIKACHU, 1, (LIGHTNING, FIRE), (H,), 30, NO_SPECIAL_CONDITIONS),
            (WEEDLE, 0, (GRASS,), (H,), 20, SpecialConditions(poison=Poison(10))),  # どくばり 10 + ポケモンチェックのどく 10
            (CATERPIE, 0, (GRASS,), (H,), 10, SpecialConditions(exclusive=Paralyzed(3))),
            (PARAS, 1, (GRASS, GRASS), (T,), 0, SpecialConditions(exclusive=ASLEEP)),
            (VULPIX, 0, (FIRE, FIRE), (H,), 10, SpecialConditions(exclusive=CONFUSED)),
        ]
        for attacker, index, energy, after, to_opponent, condition in cases:
            with self.subTest(attacker=attacker, side="heads"):
                new, events = attack(confused(attacker, H, *after, energy=energy), index)
                flips = [e for e in events if e["kind"] == "coin_flip"]
                self.assertEqual(flips[0]["source"], "confusion")
                self.assertTrue(all(f["source"] in ("attack", "pokemon_check") for f in flips[1:]))
                self.assertNotIn("confusion_damage", kinds(events))
                self.assertEqual(new.players[1].active.damage, to_opponent)
                self.assertEqual(new.players[1].active.conditions, condition)
            with self.subTest(attacker=attacker, side="tails"):
                state = confused(attacker, T, energy=energy)
                new, events = attack(state, index)
                self.assertEqual([e["source"] for e in events if e["kind"] == "coin_flip"], ["confusion"])
                self.assertNotIn("damage", kinds(events))
                self.assertNotIn("special_condition", kinds(events))
                self.assertEqual((new.players[1].active.damage, new.players[1].active.conditions), (0, NO_SPECIAL_CONDITIONS))
                self.assertEqual(new.players[0].active.damage, 20)
                self.assertEqual((new.current_player, new.turn_number), (1, 4))

    def test_pikachu_heads_then_its_own_self_damage(self):
        """でんげき（v0.2f）: こんらんの「おもて」のあと、ワザの説明のコインが「うら」なら自分にも 10（ワザによるダメージ、
        ``damage`` のログ）。こんらんの 20（``confusion_damage``）とは別。"""
        new, events = attack(confused(PIKACHU, H, T, energy=(LIGHTNING, FIRE)), 1)
        self.assertEqual([e["source"] for e in events if e["kind"] == "coin_flip"], ["confusion", "attack"])
        own = [e for e in events if e["kind"] == "damage" and e.get("target") == "self"]
        self.assertEqual([e["amount"] for e in own], [10])
        self.assertNotIn("confusion_damage", kinds(events))
        self.assertEqual(new.players[0].active.damage, 10)

    def test_poison_and_confusion_attacker(self):
        """どく + こんらんのポケモンが「うら」: 自分に 20、番の終わりのポケモンチェックでどくの 10。どちらも消えない。"""
        new, events = attack(confused(VULPIX, T, poisoned=True))
        self.assertEqual(kinds(events)[3:7], ["confusion_damage", "turn_end", "pokemon_check", "poison_damage"])
        vulpix = new.players[0].active
        self.assertEqual((vulpix.damage, vulpix.conditions), (30, SpecialConditions(poison=Poison(10), exclusive=CONFUSED)))

    def test_rejected_commands_flip_no_coin(self):
        """ワザの宣言が成り立たない操作は、こんらんのコインを投げる前に拒否する（状態も乱数も変えない）。"""
        assert_unchanged_rejection(self, confused(VULPIX, T, energy=(FIRE,)), UseAttack(0, CONFUSE_RAY), "INSUFFICIENT_ENERGY")
        assert_unchanged_rejection(self, confused(VULPIX, T), UseAttack(0, 1), "INVALID_ATTACK")
        assert_unchanged_rejection(self, confused(VULPIX, T), UseAttack(1, 0), "NOT_YOUR_TURN")
        # 未対応のワザ（ヒトカゲの「ひのこ」）も、こんらんのコインで「うら」なら 20 ダメージになるが、宣言の前に拒否する
        assert_unchanged_rejection(self, confused(CHARMANDER, T, energy=(FIRE, FIRE)), UseAttack(0, 1), "UNSUPPORTED_ATTACK", UnsupportedError)
        state = apply_command(confused(VULPIX, T), UseAttack(0, CONFUSE_RAY))
        assert_unchanged_rejection(self, state, UseAttack(0, CONFUSE_RAY), "NOT_YOUR_TURN")  # 番は終わっている

    def test_unresolved_attack_is_stopped_before_the_confusion_coin(self):
        """ワザの説明の処理が原典で決められない場合（自分の弱点・抵抗力のタイプのポケモンの「でんげき」。v0.2f）は、こんらんの
        コインの前に止める（「うら」なら決められなくてもよい、と投げてから決めない）。"""
        extract = copy.deepcopy(read_extract())
        source = next(c for c in extract["cards"] if c["id"] == PIKACHU)
        weak = copy.deepcopy(source)
        weak["id"] = "TEST-PIKACHU-WEAK-TO-LIGHTNING"
        weak["pokemon"]["weaknesses"] = [{"type": "lightning", "operator": "×", "value": 2}]
        extract["cards"].append(weak)
        text = source["pokemon"]["attacks"][1]["text"]["ja"]
        effects = DEFAULT_EFFECTS.with_attacks("test", {AttackKey(weak["id"], 1): AttackEntry(SelfDamageOnTails(10), "でんげき", text_ja=text)})
        pool = pool_from_extract(extract, effects)
        for side in (H, T):
            with self.subTest(side=side):
                state = confused(weak["id"], side, energy=(LIGHTNING, FIRE), pool=pool, effects=effects)
                assert_unchanged_rejection(self, state, UseAttack(0, 1), "UNRESOLVED_SELF_DAMAGE_WEAKNESS_RESISTANCE", UnsupportedError)


# ---------------------------------------------------------------- 20 ダメージ（6 章）


class ConfusionDamageTest(unittest.TestCase):
    def tails(self, attacker, **kwargs):
        new, events = attack(confused(attacker, T, **kwargs))
        return new, events, next(e for e in events if e["kind"] == "confusion_damage")

    def test_weakness_and_resistance(self):
        """「このダメージは「弱点・抵抗力」の影響を受けます」（p.322。CONFIRMED）。ダメージを与えるのも受けるのも同じポケモン
        なので、自分のタイプが自分の弱点なら 2 倍、抵抗力なら −30（p.321 の 3・4 の当てはめ。SUPPORTED）。"""
        pool, effects = self_typed_pool()
        cases = {
            VULPIX: (20, [20], False, False),  # 炎・弱点 水: 関係しない
            SELF_WEAK: (40, [20, 40], True, False),
            SELF_RESISTANT: (0, [20, -10], False, True),  # 0 以下は「ダメージを受けなかった」（p.321）
            SELF_BOTH: (10, [20, 40, 10], True, True),  # 弱点 → 抵抗力の順（p.321）
        }
        for card, (amount, steps, weakness, resistance) in cases.items():
            with self.subTest(card=card):
                new, _, own = self.tails(card, pool=pool, effects=effects)
                self.assertEqual((own["amount"], [v for _, v in own["steps"]], own["weakness"], own["resistance"]),
                                 (amount, steps, weakness, resistance))
                self.assertEqual(new.players[0].active.damage, amount)
                calc = calculate_confusion_damage(pool.get(card), RULES_2000_02_14, 20)
                self.assertEqual(calc.final, amount)

    def test_the_opponent_type_does_not_matter(self):
        """こんらんのダメージの発生源は、ワザを使ったポケモン自身。相手（ヒトデマン、水 = ロコンの弱点）のタイプは関係しない。"""
        _, _, own = self.tails(VULPIX, defender=STARYU)
        self.assertEqual((own["amount"], own["weakness"]), (20, False))
        _, _, own = self.tails(DIGLETT, energy=(FIGHTING,))  # 闘・弱点 草・抵抗力 雷
        self.assertEqual((own["amount"], own["weakness"], own["resistance"]), (20, False, False))

    def test_opponent_attached_cards_do_not_matter(self):
        """相手の対戦ポケモンについているディフェンダーは、こんらんのダメージに関係しない（受けるのは自分のポケモン）。止めない。"""
        state = build_test_state([
            {"active": {"card": VULPIX, "energy": [FIRE, FIRE], "confusion": True}, "bench": [PONYTA]},
            {"active": GROWLITHE, "bench": [RATTATA], "hand": [DEFENDER]},
        ], current_player=1, turn_number=4)
        state = play_all(state, DEFENDER, player=1)
        state = apply_command(state, EndTurn(1))
        new, events = attack(with_coin_results(state, T))
        self.assertEqual(next(e for e in events if e["kind"] == "confusion_damage")["amount"], 20)

    def test_knock_out_thresholds(self):
        """HP ちょうど・こえる → きぜつ（p.323）。1 つ足りなければ残る。ロコンは HP50。"""
        for damage, knocked in ((20, False), (30, True), (40, True)):
            with self.subTest(damage=damage):
                new, events, own = self.tails(VULPIX, damage=damage)
                self.assertEqual(own["total_damage"], damage + 20)
                self.assertEqual("knock_out" in kinds(events), knocked)

    def test_self_knock_out_gives_the_opponent_a_prize(self):
        """こんらんで自分のポケモンがきぜつしたら、相手側のプレイヤー（番でないプレイヤー）がサイドを取り、自分が新しい
        対戦ポケモンを出す。そのあと番が終わる（p.309・p.323）。"""
        state = confused(VULPIX, T, damage=30)
        vulpix = state.players[0].active
        new, events, _ = self.tails(VULPIX, damage=30)
        ko = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual((ko["player"], ko["pokemon"], ko["discarded_energy"]), (0, vulpix.card, tuple(vulpix.energy)))
        self.assertIsNone(new.find_pokemon(vulpix.pokemon_id))
        self.assertEqual((new.phase, new.decision.player), (Phase.TAKE_PRIZE, 1))
        new = apply_command(new, TakePrize(1, 0))
        self.assertEqual((new.phase, new.decision.player), (Phase.PROMOTE_ACTIVE, 0))
        new = apply_command(new, ResolveDecision(0, new.decision.id, (new.decision.options[0],)))
        self.assertEqual((new.phase, new.current_player, len(new.players[1].prizes)), (Phase.MAIN, 1, 5))
        self.assertEqual(check_invariants(new), [])

    def test_self_knock_out_ends_the_game(self):
        """相手が最後のサイドを取れば相手の勝ち。控えがいなければ、新しい対戦ポケモンを出せないので相手の勝ち（p.311・p.323）。"""
        new, _, _ = self.tails(VULPIX, damage=30, their_prizes=1)
        new = apply_command(new, TakePrize(1, 0))
        self.assertEqual((new.phase, new.result.winner, new.result.conditions), (Phase.GAME_OVER, 1, ((1, "ALL_PRIZES_TAKEN"),)))
        new, _, _ = self.tails(VULPIX, damage=30, bench=())
        new = apply_command(new, TakePrize(1, 0))
        self.assertEqual((new.phase, new.result.winner, new.result.conditions),
                         (Phase.GAME_OVER, 1, ((1, "OPPONENT_CANNOT_FIELD_ACTIVE"),)))


class UnresolvedModifierTest(unittest.TestCase):
    """こんらんのダメージが「ワザによるダメージ」（p.321「8」）かは原典に書かれていないので、ワザを使うポケモンについている
    プラスパワー（5 段階）・ディフェンダー（7 段階）を計算するかは決められない（UNRESOLVED）。コインを投げる前に止める。"""

    def test_pluspower_or_defender_on_the_confused_pokemon(self):
        for card in (PLUSPOWER, DEFENDER):
            for side in (H, T):
                with self.subTest(card=card, side=side):
                    state = play_all(confused(VULPIX, hand_cards=[card]), card)
                    self.assertEqual(len(state.players[0].active.trainers), 1)
                    state = with_coin_results(state, side)
                    assert_unchanged_rejection(self, state, UseAttack(0, CONFUSE_RAY), "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", UnsupportedError)

    def test_without_confusion_the_same_board_attacks(self):
        """こんらんでなければ、プラスパワーのついたロコンはワザを使える（止めるのはこんらんのダメージのためだけ）。"""
        state = build_test_state([
            {"active": {"card": VULPIX, "energy": [FIRE, FIRE]}, "bench": [PONYTA], "hand": [PLUSPOWER]},
            {"active": GROWLITHE, "bench": [RATTATA]},
        ])
        state = with_coin_results(play_all(state, PLUSPOWER), T)
        new, events = attack(state)
        self.assertEqual(next(e for e in events if e["kind"] == "damage")["amount"], 20)


if __name__ == "__main__":
    unittest.main()

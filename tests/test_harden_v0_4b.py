"""ワザによる持続する効果と「かたまる」（v0.4b。docs/persistent-effects-v0.4b.md・docs/harden-v0.4b.md・
docs/persistent-damage-v0.4b.md）。

根拠のページ（『ポケモンカードオフィシャルブック2000』[P43]、kyuura NEO-2000-OFFICIAL-RULES）:

- p.18（トランセル）・p.21（コクーン）の最新の説明「コインを投げて「おもて」なら、次の相手の番、このカードはダメージを
  受けない。（ダメージ以外の効果は受ける）」。印刷の文面（kyuura の写し）は「…次の相手の番にうけるダメージが0になる。」
- p.236 のワザ解説（ラッキー「まるまる」。同じタイプのワザに「かたまる」）: 効果の対象はワザを使ったポケモン自身、
  効果の持続は次の相手の番の最後、ベンチにもどると効果は消える、どく状態のダメージは相手の番ではないので受ける
- p.321「ワザを使ったとき、それを受けたポケモンが「ダメージを受けない」状態だったら、そのポケモンにダメージを与える
  「ワザの要素」は無効になります。ただし、そのポケモン以外へダメージを与える「ワザの要素」は、有効です。また、ダメージ
  以外の効果をもたらす「ワザの要素」も有効です。」
- p.322・p.323（持続する効果: ベンチにもどったら・場をはなれたら・進化したら消える、復活しない、特殊状態と重複する）
- p.311（ベンチに戻ったら「持続する効果」はすべて消える）、p.323（ポケモンチェックはどちらの番でもないので、「次の相手の
  番にダメージを受けない」ポケモンも、ポケモンチェックの中のダメージは受ける）
- p.310（進化の手順 3: 持続する効果から回復）

盤面を直接作るテスト（``build_test_state``）のうち、効果を与えた番にベンチに戻る・進化する・きぜつするものは、自然な対戦
では起こらない（「かたまる」はワザなので、使った番はすぐに終わり、効果がはたらくのは相手の番だけ）。それぞれのテストの
説明に「（盤面を直接作った。自然な対戦では起こらない）」と書く。
"""

import copy
import pickle
import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, Phase, PlayTrainer, PreventDamage, ResolveDecision, Retreat,
    TakePrize, UnsupportedError, UseAttack, apply_command, check_invariants, state_to_dict,
)
from kyuura_engine.cards import load_card_pool, read_verification
from kyuura_engine.effects import DEFAULT_EFFECTS, ParalyzeOnHeads, PoisonOnHeads, PreventDamageOnHeads
from kyuura_engine.persistent import damage_prevention
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.serialize import FORMAT_VERSIONS

from tests.helpers import (
    CATERPIE, DEFENDER, DEWGONG, DODUO, FIRE, GRASS, GROWLITHE, H, HITMONCHAN, FIGHTING, KAKUNA, LIGHTNING, METAPOD, PARAS, PIKACHU,
    PLUSPOWER, PONYTA, RATTATA, SWITCH, T, VULPIX, WATER, WEEDLE, build_test_state, with_coin_results,
)

HARDEN_PRINTED = "コインを投げて「おもて」なら、次の相手の番にうけるダメージが0になる。"
HARDEN_LATEST = "コインを投げて「おもて」なら、次の相手の番、このカードはダメージを受けない。（ダメージ以外の効果は受ける）"
STAGE1 = {METAPOD: CATERPIE, KAKUNA: WEEDLE}


def full(state):
    return state_to_dict(state, format_version=8)


def run(state, command):
    new = apply_command(state, command)
    return new, [dict(e) for e in new.log[len(state.log):]]


def kinds(events):
    return [e["kind"] for e in events]


def uid_of(state, player, card_id, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def assert_rejected(test, state, command, code, error=IllegalActionError):
    """拒否され、渡した状態（持続する効果も）も乱数も変わらない。"""
    before, fingerprint = full(state), rng_fingerprint(state.rng)
    with test.assertRaises(error) as ctx:
        apply_command(state, command)
    test.assertEqual(ctx.exception.code, code)
    test.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))


def stage1(card=METAPOD, *, energy=(GRASS, GRASS), **extra):
    """キャタピー（コクーンならビードル）から進化したトランセル（コクーン）。"""
    return {"card": card, "evolved_from": STAGE1[card], "energy": list(energy), **extra}


def my_turn(active, *, opponent=None, turn=3, bench=(PONYTA,), hand=(), opponent_bench=(RATTATA,), prizes=6, **kwargs):
    """プレイヤー 0 の番 ``turn``（奇数）の盤面。"""
    return build_test_state([
        {"active": active, "bench": list(bench), "hand": list(hand), "prizes": prizes},
        {"active": opponent or RATTATA, "bench": list(opponent_bench)},
    ], current_player=0, turn_number=turn, **kwargs)


def protected(attacker, *, card=METAPOD, turn=4, mine=None, hand=(), prizes=6, **kwargs):
    """プレイヤー 0 の対戦ポケモン（既定はトランセル）が前の番（``turn`` − 1）に「かたまる」の「おもて」を出し、今の番
    （``turn``。プレイヤー 1 の番）に「ダメージを受けない」状態の盤面。プレイヤー 1 の対戦ポケモンは ``attacker``。"""
    spec = {**(mine or stage1(card)), "prevent_damage": turn - 1}
    return build_test_state([
        {"active": spec, "bench": [PONYTA], "prizes": prizes},
        {"active": attacker, "bench": [RATTATA], "hand": list(hand)},
    ], current_player=1, turn_number=turn, **kwargs)


def unprotected(attacker, *, card=METAPOD, turn=4, mine=None, **kwargs):
    """``protected`` と同じ盤面で、持続する効果がないもの（比べるため）。"""
    return build_test_state([
        {"active": mine or stage1(card), "bench": [PONYTA]},
        {"active": attacker, "bench": [RATTATA]},
    ], current_player=1, turn_number=turn, **kwargs)


# ---------------------------------------------------------------- 登録とカード


class HardenRegistrationTest(unittest.TestCase):
    def test_both_cards_are_registered_with_the_verified_latest_description(self):
        """トランセル（p.18）・コクーン（p.21）の 2 つのワザを、カードごとに照合した説明・出典で登録する。"""
        records = read_verification()["cards"]
        expected = {
            (METAPOD, 0): (PreventDamageOnHeads, "かたまる", HARDEN_PRINTED, HARDEN_LATEST, "P43 p.18"),
            (METAPOD, 1): (ParalyzeOnHeads, "しびれごな", "コインを投げて「おもて」なら、相手を「マヒ」状態にする。",
                           "コインを投げて「おもて」なら、相手を「マヒ」状態にする。", "P43 p.18"),
            (KAKUNA, 0): (PreventDamageOnHeads, "かたまる", HARDEN_PRINTED, HARDEN_LATEST, "P43 p.21"),
            (KAKUNA, 1): (PoisonOnHeads, "どくのこな", "コインを投げて「おもて」なら、相手を「どく」状態にする。",
                          "コインを投げて「おもて」なら、相手を「どく」状態にする。", "P43 p.21"),
        }
        for (card_id, index), (cls, name, printed, latest, source) in expected.items():
            with self.subTest(card=card_id, attack=index):
                entry = DEFAULT_EFFECTS.attack_entry(card_id, index)
                self.assertIs(type(entry.effect), cls)
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (name, printed, latest, source))
                record = records[card_id]
                self.assertEqual(record["status"], "不一致あり")  # 印刷の文面と最新の説明が違う（かたまる）
                self.assertEqual(record["latest_description_ja"][str(index)], latest)
        # 説明（最新の説明）が、すでに登録したワザと一字一句同じ: キャタピーの「いとをはく」（p.17）・ビードルの「どくばり」（p.19）
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(METAPOD, 1).play_text_ja, DEFAULT_EFFECTS.attack_entry(CATERPIE, 0).play_text_ja)
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(KAKUNA, 1).play_text_ja, DEFAULT_EFFECTS.attack_entry(WEEDLE, 0).play_text_ja)

    def test_cards_are_supported_stage1_pokemon(self):
        pool = load_card_pool()
        for card_id, (evolves_from, hp, retreat) in {METAPOD: ("キャタピー", 70, 2), KAKUNA: ("ビードル", 80, 2)}.items():
            definition = pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertTrue(definition.supported and definition.is_stage1_pokemon and pool.is_playable(card_id))
                self.assertEqual((definition.evolves_from, definition.hp, definition.retreat_cost), (evolves_from, hp, retreat))
                self.assertEqual([a.damage for a in definition.attacks], [None, 20])  # かたまるにはダメージの目安の数字がない

    def test_check_rejects_an_attack_with_damage(self):
        """「かたまる」の実装は、ダメージの目安のあるワザには登録できない（ダメージの要素がないワザ）。"""
        pool = load_card_pool()
        self.assertTrue(PreventDamageOnHeads().check(pool.get(METAPOD).attacks[1]))
        self.assertEqual(PreventDamageOnHeads().check(pool.get(METAPOD).attacks[0]), [])

    def test_effect_value_is_frozen(self):
        effect = PreventDamage(1, 0, 3, 4)
        self.assertEqual(effect.kind, "prevent_damage")
        with self.assertRaises(Exception):
            effect.active_turn = 5


# ---------------------------------------------------------------- 「かたまる」を使う


class HardenTest(unittest.TestCase):
    def test_heads_gives_the_effect_for_the_next_opponent_turn(self):
        """「おもて」: 次の相手の番（今の番 + 1）にはたらく効果を自分に与え、番は終わる（p.18・p.21・p.236・p.309）。"""
        for card in (METAPOD, KAKUNA):
            with self.subTest(card=card):
                state = my_turn(stage1(card))
                new, events = run(with_coin_results(state, H), UseAttack(0, 0))
                me = new.players[0].active
                self.assertEqual(me.persistent_effects, (PreventDamage(me.card, 0, 3, 4),))
                self.assertEqual(kinds(events), ["attack", "coin_flip", "persistent_effect_added", "turn_end", "pokemon_check",
                                                 "turn_start", "draw"])
                flip, added = events[1], events[2]
                self.assertEqual((flip["source"], flip["effect"], flip["result"]), ("attack", f"{card}#0", "heads"))
                self.assertEqual(
                    {k: added[k] for k in ("player", "pokemon", "pokemon_id", "persistent_effect", "source_card", "source_player",
                                           "active_turn", "effect", "turn")},
                    {"player": 0, "pokemon": me.card, "pokemon_id": me.pokemon_id, "persistent_effect": "prevent_damage",
                     "source_card": me.card, "source_player": 0, "active_turn": 4, "effect": f"{card}#0", "turn": 3},
                )
                self.assertEqual((new.turn_number, new.current_player, me.damage), (4, 1, 0))
                self.assertIs(damage_prevention(new, me), me.persistent_effects[0])  # 次の相手の番（4 番）にはたらく

    def test_tails_gives_nothing_but_the_attack_is_used(self):
        """「うら」: 効果はなく（説明にない）、ワザは使ったことになり番は終わる。コインはログに残り、乱数は 1 枚ぶん進む。"""
        for card in (METAPOD, KAKUNA):
            with self.subTest(card=card):
                state = my_turn(stage1(card))
                new, events = run(with_coin_results(state, T), UseAttack(0, 0))
                self.assertEqual(new.players[0].active.persistent_effects, ())
                self.assertEqual(kinds(events), ["attack", "coin_flip", "turn_end", "pokemon_check", "turn_start", "draw"])
                self.assertEqual(events[1]["result"], "tails")
                self.assertEqual(new.turn_number, 4)

    def test_rejections_before_the_coin(self):
        """使えないワザは、コインを投げる前に拒否する（状態も乱数も変わらない。p.309 の手順 1・2）。"""
        assert_rejected(self, my_turn(stage1(energy=(GRASS,))), UseAttack(0, 0), "INSUFFICIENT_ENERGY")
        assert_rejected(self, my_turn(stage1(sleep=True), turn=5), UseAttack(0, 0), "POKEMON_ASLEEP")
        assert_rejected(self, my_turn(stage1(paralysis=4), turn=5), UseAttack(0, 0), "POKEMON_PARALYZED")
        assert_rejected(self, my_turn(stage1(), turn=3), UseAttack(0, 2), "INVALID_ATTACK")

    def test_confused_heads_then_harden_coin(self):
        """こんらん状態: 宣言のあとでこんらんのコイン（p.309 の手順 5）。「おもて」なら「かたまる」のコイン（手順 6）。"""
        state = my_turn(stage1(confusion=True), turn=5)
        for harden, expected in ((H, 1), (T, 0)):
            with self.subTest(harden=harden):
                new, events = run(with_coin_results(state, H, harden), UseAttack(0, 0))
                flips = [e for e in events if e["kind"] == "coin_flip"]
                self.assertEqual([(f["source"], f["result"]) for f in flips], [("confusion", "heads"), ("attack", harden.value)])
                self.assertEqual(len(new.players[0].active.persistent_effects), expected)

    def test_confused_tails_does_not_flip_the_harden_coin(self):
        """こんらんのコインが「うら」: ワザがこんらんし、自分に 20（弱点・抵抗力だけ）。「かたまる」のコインは投げず、効果もない。"""
        state = my_turn(stage1(confusion=True), turn=5)
        new, events = run(with_coin_results(state, T), UseAttack(0, 0))
        self.assertEqual([e["source"] for e in events if e["kind"] == "coin_flip"], ["confusion"])
        self.assertNotIn("persistent_effect_added", kinds(events))
        self.assertEqual((new.players[0].active.damage, new.players[0].active.persistent_effects), (20, ()))

    def test_same_seed_same_result(self):
        """同じ状態・同じ乱数なら同じ結果（コインは対戦の乱数だけで決まる）。"""
        state = my_turn(stage1(), seed=7)
        first, second = apply_command(state, UseAttack(0, 0)), apply_command(state.clone(), UseAttack(0, 0))
        self.assertEqual(full(first), full(second))


# ---------------------------------------------------------------- ダメージを受けない（p.321）


class DamagePreventionTest(unittest.TestCase):
    CASES = [  # (ワザを使うポケモン, ワザの位置, 効果がないときのダメージ)
        ({"card": PIKACHU, "energy": [LIGHTNING]}, 0, 10),  # かじる 10
        ({"card": RATTATA, "energy": [FIRE]}, 0, 20),  # かみつく 20
        ({"card": PONYTA, "energy": [FIRE, FIRE]}, 1, 60),  # ほのおのしっぽ 30、トランセルの弱点（炎）で 2 倍
        ({"card": DEWGONG, "evolved_from": "PMCG1-029", "evolved_turn": 4, "energy": [WATER, WATER, WATER]}, 0, 50),  # オーロラビーム 50
    ]

    def test_damage_element_is_invalid(self):
        """「ダメージを受けない」状態のポケモンにダメージを与えるワザの要素は無効（p.321）。ダメージを計算せず（8 段階のどれかで
        0 にするのではない）、ダメージは変わらず、ログは ``damage`` ではなく ``damage_prevented``。効果がなければ同じワザで
        ダメージを受ける（比べるため）。"""
        for attacker, index, normal in self.CASES:
            with self.subTest(attacker=attacker["card"], attack=index):
                control, events = run(unprotected(attacker), UseAttack(1, index))
                self.assertEqual(control.players[0].active.damage, normal)
                self.assertIn("damage", kinds(events))
                new, events = run(protected(attacker), UseAttack(1, index))
                self.assertEqual(new.players[0].active.damage, 0)
                self.assertNotIn("damage", kinds(events))
                prevented = next(e for e in events if e["kind"] == "damage_prevented")
                me = new.players[0].active
                self.assertEqual(
                    {k: prevented[k] for k in ("player", "pokemon", "pokemon_id", "target", "effect", "persistent_effect", "source_card")},
                    {"player": 0, "pokemon": me.card, "pokemon_id": me.pokemon_id, "target": "opponent_active",
                     "effect": f"{attacker['card']}#{index}", "persistent_effect": "prevent_damage", "source_card": me.card},
                )
                self.assertNotIn("amount", prevented)  # 計算しないので、防いだダメージの量はない

    def test_resistance_case(self):
        """抵抗力のあるポケモンでも同じ（盤面を直接作った: ドードーが「ダメージを受けない」状態。自然な対戦では起こらない）。"""
        attacker = {"card": HITMONCHAN, "energy": [FIGHTING, FIGHTING, FIGHTING]}  # スペシャルパンチ 40、ドードーの抵抗力 闘 −30
        mine = {"card": DODUO}
        control, _ = run(unprotected(attacker, mine=mine), UseAttack(1, 1))
        self.assertEqual(control.players[0].active.damage, 10)
        new, events = run(protected(attacker, mine=mine), UseAttack(1, 1))
        self.assertEqual((new.players[0].active.damage, kinds(events).count("damage_prevented")), (0, 1))

    def test_pluspower_and_defender_are_not_calculated(self):
        """自然な流れ: 3 番にディフェンダーをつけて「かたまる」の「おもて」、4 番に相手がプラスパワーをつけてワザを使う。
        ダメージの要素が無効なので、5 段階（プラスパワー）・7 段階（ディフェンダー）も計算しない。カードはそれぞれの有効期限
        （4 番の終わり）にトラッシュされ、持続する効果も 4 番の終わりに消える（別々の処理）。効果がなければ 20 + 10 − 20 = 10。"""
        def play(harden_coin):
            state = build_test_state([
                {"active": stage1(), "bench": [PONYTA], "hand": [DEFENDER]},
                {"active": {"card": RATTATA, "energy": [FIRE]}, "bench": [RATTATA], "hand": [PLUSPOWER]},
            ], current_player=0, turn_number=3)
            state, _ = run(state, PlayTrainer(0, uid_of(state, 0, DEFENDER)))
            state, _ = run(state, ResolveDecision(0, state.decision.id, (state.players[0].active.pokemon_id,)))
            state, _ = run(with_coin_results(state, harden_coin), UseAttack(0, 0))
            state, _ = run(state, PlayTrainer(1, uid_of(state, 1, PLUSPOWER)))
            return run(state, UseAttack(1, 0))

        control, events = play(T)
        damage = next(e for e in events if e["kind"] == "damage")
        self.assertEqual((damage["amount"], control.players[0].active.damage), (10, 10))
        new, events = play(H)
        self.assertEqual(new.players[0].active.damage, 0)
        order = [e["kind"] for e in events if e["kind"] in ("damage_prevented", "discard_attached_trainer", "persistent_effect_removed", "turn_end")]
        self.assertEqual(order, ["damage_prevented", "discard_attached_trainer", "discard_attached_trainer", "persistent_effect_removed", "turn_end"])
        self.assertEqual(new.players[0].active.trainers, [])
        self.assertEqual(new.players[0].active.persistent_effects, ())

    def test_self_damage_element_is_still_valid(self):
        """ピカチュウの「でんげき」: 相手（ダメージを受けない）への要素は無効、コインと自分への 10 の要素は有効（p.321）。"""
        new, events = run(with_coin_results(protected({"card": PIKACHU, "energy": [LIGHTNING, LIGHTNING]}), T), UseAttack(1, 1))
        self.assertEqual([e["kind"] for e in events if e["kind"] in ("damage_prevented", "coin_flip", "damage")],
                         ["damage_prevented", "coin_flip", "damage"])
        self.assertEqual((new.players[0].active.damage, new.players[1].active.damage), (0, 10))

    def test_coin_damage_against_prevention_is_unresolved(self):
        """ドードーの「みだれづき」（コインでダメージの量を決める要素だけ）: 要素が無効になるとき、そのコインを投げるかは決め
        られない（乱数の続きが変わる）。こんらん状態でも、こんらんのコインの前に止める。状態も乱数も変わらない。"""
        assert_rejected(self, protected({"card": DODUO, "energy": [FIRE]}), UseAttack(1, 0), "UNRESOLVED_PREVENTED_COIN_DAMAGE", UnsupportedError)
        assert_rejected(self, protected({"card": DODUO, "energy": [FIRE], "confusion": True}), UseAttack(1, 0),
                        "UNRESOLVED_PREVENTED_COIN_DAMAGE", UnsupportedError)
        # 効果のないポケモンには、今までどおり使える
        new, events = run(with_coin_results(unprotected({"card": DODUO, "energy": [FIRE]}), H, H), UseAttack(1, 0))
        self.assertEqual(new.players[0].active.damage, 20)

    def test_effect_is_over_after_the_opponent_turn(self):
        """自然な流れ: 3 番「かたまる」の「おもて」→ 4 番 相手のワザは無効 → 5 番 何もしない → 6 番 相手のワザでダメージを受ける。"""
        state = build_test_state([
            {"active": stage1(), "bench": [PONYTA]},
            {"active": {"card": RATTATA, "energy": [FIRE]}, "bench": [RATTATA]},
        ], current_player=0, turn_number=3)
        state, _ = run(with_coin_results(state, H), UseAttack(0, 0))
        state, events = run(state, UseAttack(1, 0))
        self.assertEqual((state.players[0].active.damage, kinds(events).count("damage_prevented")), (0, 1))
        state, _ = run(state, EndTurn(0))
        state, events = run(state, UseAttack(1, 0))
        self.assertEqual((state.players[0].active.damage, kinds(events).count("damage_prevented")), (20, 0))


# ---------------------------------------------------------------- ダメージ以外の効果は受ける


class AdditionalEffectsTest(unittest.TestCase):
    """「（ダメージ以外の効果は受ける）」（最新の説明）・p.321「ダメージ以外の効果をもたらす「ワザの要素」も有効」。
    ダメージが無効になっても、効果の要素のコインを省かず、「おもて」なら特殊状態にする。"""

    CASES = [  # (ワザを使うポケモン, ワザの位置, 「おもて」で付く特殊状態)
        ({"card": WEEDLE, "energy": [GRASS]}, 0, "poison"),  # どくばり
        ({"card": CATERPIE, "energy": [GRASS]}, 0, "paralysis"),  # いとをはく
        ({"card": DEWGONG, "evolved_from": "PMCG1-029", "evolved_turn": 4, "energy": [WATER, WATER, WATER, WATER]}, 1, "paralysis"),  # れいとうビーム
        ({"card": VULPIX, "energy": [FIRE, FIRE]}, 0, "confusion"),  # あやしいひかり
        ({"card": KAKUNA, "evolved_from": WEEDLE, "evolved_turn": 4, "energy": [GRASS, GRASS]}, 1, "poison"),  # どくのこな
        ({"card": METAPOD, "evolved_from": CATERPIE, "evolved_turn": 4, "energy": [GRASS, GRASS]}, 1, "paralysis"),  # しびれごな
    ]

    def test_effect_coin_is_flipped_and_condition_applied(self):
        for attacker, index, condition in self.CASES:
            for coin in (H, T):
                with self.subTest(attacker=attacker["card"], coin=coin):
                    state = protected(attacker)
                    new, events = run(with_coin_results(state, coin), UseAttack(1, index))
                    me = new.players[0].active
                    self.assertFalse(any(e["kind"] == "damage" and e["player"] == 0 for e in events))
                    # ワザのダメージは 0。どく状態になったら、番の終わり（効果が消える）のあとのポケモンチェックで 10（p.323）
                    poisoned = coin is H and condition == "poison"
                    self.assertEqual((me.damage, kinds(events).count("poison_damage")), (10, 1) if poisoned else (0, 0))
                    applied = [e for e in events if e["kind"] == "special_condition"]
                    self.assertEqual([e["kind"] for e in events if e["kind"] in ("damage_prevented", "coin_flip", "special_condition")],
                                     ["damage_prevented", "coin_flip"] + (["special_condition"] if coin is H else []))
                    if coin is H:
                        self.assertEqual(applied[0]["condition"], condition)
                        self.assertIn(condition, me.conditions.names())
                    else:
                        self.assertEqual(me.conditions.names(), ())

    def test_sleep_attack_without_damage(self):
        """パラスの「キノコのほうし」（ダメージの要素がない）: ダメージの要素がないので ``damage_prevented`` もなく、ねむりになる。"""
        # キノコのほうしにコインはない。最初のコインはポケモンチェックのねむりのコイン（「うら」ならねむりのまま）
        new, events = run(with_coin_results(protected({"card": PARAS, "energy": [GRASS, GRASS]}), T), UseAttack(1, 1))
        self.assertNotIn("damage_prevented", kinds(events))
        self.assertTrue(new.players[0].active.conditions.asleep)

    def test_damage_only_attack_changes_nothing_else(self):
        new, events = run(protected({"card": RATTATA, "energy": [FIRE]}), UseAttack(1, 0))
        me = new.players[0].active
        self.assertEqual((me.damage, me.conditions.names(), me.energy and len(me.energy)), (0, (), 2))
        self.assertEqual([e["kind"] for e in events if e["kind"] in ("damage", "damage_prevented", "coin_flip", "special_condition")],
                         ["damage_prevented"])

    def test_near_knock_out_coin_is_not_skipped(self):
        """効果がなければ HP 以上のダメージできぜつし、どくの要素は対象がいないのでコインを投げない（v0.3a）。効果があれば
        ダメージの要素は無効で、きぜつしないので、コインを投げてどく状態にする。番の終わりに効果が消えたあと、ポケモン
        チェックのどくのダメージ（どちらの番でもない。p.323）できぜつする（重なったカードもトラッシュ、サイドは 1 枚）。"""
        weedle = {"card": WEEDLE, "energy": [GRASS]}
        control, events = run(with_coin_results(unprotected(weedle, mine=stage1(damage=60)), H), UseAttack(1, 0))
        self.assertEqual(kinds(events).count("coin_flip"), 0)
        self.assertIn("knock_out", kinds(events))
        state = protected(weedle, mine=stage1(damage=60))
        metapod = state.players[0].active
        new, events = run(with_coin_results(state, H), UseAttack(1, 0))
        order = [e["kind"] for e in events if e["kind"] in ("damage_prevented", "coin_flip", "special_condition",
                                                            "persistent_effect_removed", "turn_end", "poison_damage", "knock_out")]
        self.assertEqual(order, ["damage_prevented", "coin_flip", "special_condition", "persistent_effect_removed", "turn_end",
                                 "poison_damage", "knock_out"])
        removed = next(e for e in events if e["kind"] == "persistent_effect_removed")
        self.assertEqual(removed["reason"], "expired")
        knock = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual((knock["pokemon"], knock["evolution_stack"], knock["timing"]), (metapod.card, metapod.evolution_stack, "pokemon_check"))
        self.assertEqual(new.phase, Phase.TAKE_PRIZE)
        self.assertEqual(new.decision.player, 1)
        self.assertTrue(set(metapod.cards()) <= set(new.players[0].discard))

    def test_rng_is_reproducible(self):
        state = protected({"card": WEEDLE, "energy": [GRASS]}, seed=11)
        self.assertEqual(full(apply_command(state, UseAttack(1, 0))), full(apply_command(state.clone(), UseAttack(1, 0))))


# ---------------------------------------------------------------- ポケモンチェック（p.323）


class PokemonCheckTest(unittest.TestCase):
    def test_poison_damage_is_not_prevented(self):
        """どく状態のコクーンが「かたまる」の「おもて」。直後のポケモンチェック（どちらの番でもない。p.323）では、どくの
        ダメージを受ける（効果はまだはたらいていない）。次の相手の番の終わりに効果が消え、そのあとのポケモンチェックでも受ける。"""
        state = my_turn(stage1(KAKUNA, poison=10), turn=5)
        new, events = run(with_coin_results(state, H), UseAttack(0, 0))
        order = [e["kind"] for e in events if e["kind"] in ("persistent_effect_added", "turn_end", "pokemon_check", "poison_damage")]
        self.assertEqual(order, ["persistent_effect_added", "turn_end", "pokemon_check", "poison_damage"])
        me = new.players[0].active
        self.assertEqual((me.damage, len(me.persistent_effects)), (10, 1))
        new, events = run(new, EndTurn(1))
        order = [e["kind"] for e in events if e["kind"] in ("persistent_effect_removed", "turn_end", "pokemon_check", "poison_damage")]
        self.assertEqual(order, ["persistent_effect_removed", "turn_end", "pokemon_check", "poison_damage"])
        self.assertEqual((new.players[0].active.damage, new.players[0].active.persistent_effects), (20, ()))

    def test_poison_knock_out_while_the_effect_remains(self):
        """どくでのきぜつ（直後のポケモンチェック）: 効果は場をはなれたので消える（p.322。ログ reason knock_out）。重なった
        カード・エネルギーはトラッシュ、持続する効果はカードではないのでトラッシュに何も足さない。サイドは相手が 1 枚。"""
        state = my_turn(stage1(KAKUNA, poison=10, damage=70), turn=5)
        kakuna = state.players[0].active
        before_discard = len(state.players[0].discard)
        new, events = run(with_coin_results(state, H), UseAttack(0, 0))
        order = [e["kind"] for e in events if e["kind"] in ("persistent_effect_added", "poison_damage", "knock_out", "persistent_effect_removed")]
        self.assertEqual(order, ["persistent_effect_added", "poison_damage", "knock_out", "persistent_effect_removed"])
        removed = next(e for e in events if e["kind"] == "persistent_effect_removed")
        self.assertEqual((removed["reason"], removed["pokemon_id"]), ("knock_out", kakuna.pokemon_id))
        self.assertEqual(len(new.players[0].discard), before_discard + 4)  # コクーン・ビードル・草エネルギー 2 枚
        self.assertEqual((new.phase, new.decision.player), (Phase.TAKE_PRIZE, 1))
        self.assertEqual(check_invariants(new), [])


# ---------------------------------------------------------------- 期限


class ExpiryTest(unittest.TestCase):
    def setUp(self):
        self.start = build_test_state([
            {"active": stage1(), "bench": [PONYTA], "hand": [GRASS]},
            {"active": {"card": RATTATA}, "bench": [RATTATA], "hand": [FIRE, FIRE]},
        ], current_player=0, turn_number=3)

    def test_lifetime(self):
        """3 番に与えた効果: 3 番の終わり・ポケモンチェックでは消えない → 4 番（相手の番）の間はたらく → 4 番の終わりに
        1 回だけ消える（ポケモンチェックの前）→ 5 番（自分の番）以降はない。"""
        state, events = run(with_coin_results(self.start, H), UseAttack(0, 0))
        effect = state.players[0].active.persistent_effects[0]
        self.assertNotIn("persistent_effect_removed", kinds(events))
        self.assertEqual((state.turn_number, effect.active_turn), (4, 4))
        state, _ = run(state, AttachEnergy(1, uid_of(state, 1, FIRE), state.players[1].active.card))  # 番の途中
        self.assertIs(damage_prevention(state, state.players[0].active), effect)
        state, events = run(state, EndTurn(1))
        self.assertEqual([e["kind"] for e in events][:4], ["end_turn_without_attack", "persistent_effect_removed", "turn_end", "pokemon_check"])
        self.assertEqual(state.players[0].active.persistent_effects, ())
        for _ in range(3):  # 二重に消さない
            state, events = run(state, EndTurn(state.current_player))
            self.assertNotIn("persistent_effect_removed", kinds(events))
        removed = [dict(e) for e in state.log if e["kind"] == "persistent_effect_removed"]
        self.assertEqual(len(removed), 1)
        self.assertEqual({k: removed[0][k] for k in ("reason", "created_turn", "active_turn", "turn")},
                         {"reason": "expired", "created_turn": 3, "active_turn": 4, "turn": 4})

    def test_game_over_during_the_effect(self):
        """効果がはたらく番に勝敗が決まったら、番の終わりは来ない（効果は終わった状態に残る。余計な処理・コインはない）。
        相手のピカチュウの「でんげき」: トランセルへの要素は無効、コインが「うら」なら自分に 10 できぜつ → 最後のサイド。"""
        state = protected({"card": PIKACHU, "energy": [LIGHTNING, LIGHTNING], "damage": 30}, prizes=1)
        state, _ = run(with_coin_results(state, T), UseAttack(1, 1))
        self.assertEqual((state.phase, state.decision.player), (Phase.TAKE_PRIZE, 0))
        state, events = run(state, TakePrize(0, 0))
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertNotIn("turn_end", kinds(events))
        self.assertNotIn("coin_flip", kinds(events))
        self.assertEqual(len(state.players[0].active.persistent_effects), 1)
        self.assertEqual(check_invariants(state), [])
        self.assertEqual(len(full(state)["players"][0]["active"]["persistent_effects"]), 1)


# ---------------------------------------------------------------- 解除（ベンチ・進化・きぜつ）


class RemovalTest(unittest.TestCase):
    """どれも盤面を直接作った（効果を与えた番に、そのポケモンが行動する）。自然な対戦では起こらない。"""

    def test_retreat_removes_and_it_does_not_come_back(self):
        """にげる（p.311「ベンチに戻ったら…「持続する効果」は、すべて消えてなくなります」）。ダメージ・エネルギー・重なり・
        場のポケモンの番号はそのまま。バトル場に戻っても復活しない（p.322）。"""
        state = my_turn(stage1(energy=(GRASS, GRASS, GRASS), damage=20, prevent_damage=3), bench=({"card": PONYTA, "energy": [FIRE]},))
        metapod = state.players[0].active
        new, events = run(state, Retreat(0, tuple(metapod.energy[:2]), state.players[0].bench[0].card))
        self.assertEqual([e["kind"] for e in events], ["retreat", "persistent_effect_removed"])
        self.assertEqual(events[1]["reason"], "retreat")
        benched = new.players[0].bench[0]
        self.assertEqual((benched.pokemon_id, benched.damage, benched.energy, benched.evolution_stack, benched.persistent_effects),
                         (metapod.pokemon_id, 20, metapod.energy[2:], metapod.evolution_stack, ()))
        back, events = run(new, Retreat(0, (new.players[0].active.energy[0],), benched.card))
        self.assertEqual(back.players[0].active.persistent_effects, ())
        self.assertNotIn("persistent_effect_removed", kinds(events))

    def test_failed_retreat_keeps_the_effect(self):
        """こんらんで「にげる」に失敗したら、ベンチに戻っていないので消えない。"""
        state = my_turn(stage1(confusion=True, prevent_damage=5), turn=5)
        new, events = run(with_coin_results(state, T), Retreat(0, tuple(state.players[0].active.energy), state.players[0].bench[0].card))
        self.assertIn("retreat_failed", kinds(events))
        self.assertNotIn("persistent_effect_removed", kinds(events))
        self.assertEqual(len(new.players[0].active.persistent_effects), 1)

    def test_switch_removes(self):
        """ポケモンいれかえ（p.322「通常、「持続する効果」を受けたポケモンがベンチにもどったら…消えてなくなります」）。"""
        state = my_turn(stage1(prevent_damage=3), hand=(SWITCH,))
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, SWITCH)))
        new, events = run(state, ResolveDecision(0, state.decision.id, (state.players[0].bench[0].pokemon_id,)))
        self.assertEqual([e["kind"] for e in events][:2], ["switch", "persistent_effect_removed"])
        self.assertEqual(events[1]["reason"], "switch")
        self.assertEqual(new.players[0].bench[0].persistent_effects, ())

    def test_evolution_removes_but_keeps_attached_trainers(self):
        """進化（p.310 の手順 3・p.323）: 特殊状態と持続する効果はそれぞれ消え（別の処理）、ディフェンダーは受け継ぐ（p.310）。
        キャタピー（たね）に効果を置いた（「かたまる」を持たないカード。盤面を直接作った）。"""
        state = my_turn({"card": CATERPIE, "energy": [GRASS], "poison": 10, "prevent_damage": 3}, hand=(DEFENDER, METAPOD))
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, DEFENDER)))
        state, _ = run(state, ResolveDecision(0, state.decision.id, (state.players[0].active.pokemon_id,)))
        caterpie = state.players[0].active
        new, events = run(state, EvolvePokemon(0, uid_of(state, 0, METAPOD), caterpie.pokemon_id))
        self.assertEqual([e["kind"] for e in events], ["evolve", "special_conditions_removed", "persistent_effect_removed"])
        self.assertEqual(events[2]["reason"], "evolve")
        metapod = new.players[0].active
        self.assertEqual((metapod.pokemon_id, metapod.persistent_effects, metapod.conditions.names()), (caterpie.pokemon_id, (), ()))
        self.assertEqual(metapod.trainers, caterpie.trainers)

    def test_knock_out_by_self_damage_and_confusion(self):
        """自分へのダメージ・こんらんの 20 できぜつ: 効果も消える（p.322）。効果を与えた番には、効果ははたらかない（はたらく
        のは次の相手の番）ので、ダメージは受ける。"""
        cases = [
            (my_turn({"card": PIKACHU, "energy": [LIGHTNING, LIGHTNING], "damage": 30, "prevent_damage": 3}, opponent=GROWLITHE), (T,), UseAttack(0, 1)),
            (my_turn(stage1(confusion=True, damage=50, prevent_damage=5), turn=5), (T,), UseAttack(0, 0)),
        ]
        for state, coins, command in cases:
            with self.subTest(card=state.cards[state.players[0].active.card].card_id):
                new, events = run(with_coin_results(state, *coins), command)
                order = [e["kind"] for e in events if e["kind"] in ("knock_out", "persistent_effect_removed")]
                self.assertEqual(order, ["knock_out", "persistent_effect_removed"])
                self.assertEqual(next(e for e in events if e["kind"] == "persistent_effect_removed")["reason"], "knock_out")

    def test_removed_only_once_when_triggers_overlap(self):
        """進化で消えたあとに「にげる」でベンチに戻っても、もう一度は消さない。"""
        state = my_turn({"card": CATERPIE, "energy": [GRASS, GRASS, GRASS], "prevent_damage": 3}, hand=(METAPOD,))
        state, _ = run(state, EvolvePokemon(0, uid_of(state, 0, METAPOD), state.players[0].active.pokemon_id))
        state, events = run(state, Retreat(0, tuple(state.players[0].active.energy[:2]), state.players[0].bench[0].card))
        self.assertNotIn("persistent_effect_removed", kinds(events))
        # もとの効果がはたらくはずだった番（4 番）の終わりにも、もう一度は消さない（期限切れの処理は残っている効果だけを見る）
        for _ in range(2):
            state, events = run(state, EndTurn(state.current_player))
            self.assertNotIn("persistent_effect_removed", kinds(events))
        self.assertEqual(state.turn_number, 5)
        self.assertEqual(sum(1 for e in state.log if e["kind"] == "persistent_effect_removed"), 1)


# ---------------------------------------------------------------- 進化とトランセル・コクーン


class EvolutionWithHardenTest(unittest.TestCase):
    def test_evolve_then_harden_in_the_same_turn(self):
        """キャタピー → トランセル、ビードル → コクーン（p.309・p.310）。どく状態は進化で消え、進化した番にワザを使える。"""
        for basic, stage in ((CATERPIE, METAPOD), (WEEDLE, KAKUNA)):
            with self.subTest(card=stage):
                state = my_turn({"card": basic, "energy": [GRASS, GRASS], "poison": 10}, hand=(stage,))
                state, events = run(state, EvolvePokemon(0, uid_of(state, 0, stage), state.players[0].active.pokemon_id))
                self.assertEqual(kinds(events), ["evolve", "special_conditions_removed"])
                new, _ = run(with_coin_results(state, H), UseAttack(0, 0))
                me = new.players[0].active
                self.assertEqual((me.persistent_effects[0].created_turn, me.evolved_turn), (3, 3))

    def test_played_this_turn_cannot_evolve(self):
        state = my_turn(RATTATA, hand=(CATERPIE, METAPOD))
        from kyuura_engine import PlayBasicToBench
        state, _ = run(state, PlayBasicToBench(0, uid_of(state, 0, CATERPIE)))
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, METAPOD), state.players[0].bench[-1].pokemon_id), "PLAYED_THIS_TURN")

    def test_knock_out_of_evolved_pokemon_trashes_the_stack_and_one_prize(self):
        """効果が消えたあとの相手の番に、相手のワザできぜつ: 下のキャタピーもトラッシュし、サイドは 1 枚（p.313・p.323）。"""
        state = build_test_state([
            {"active": stage1(damage=50), "bench": [PONYTA]},
            {"active": {"card": PONYTA, "energy": [FIRE, FIRE]}, "bench": [RATTATA]},
        ], current_player=1, turn_number=4)
        metapod = state.players[0].active
        new, events = run(state, UseAttack(1, 1))  # ほのおのしっぽ 30 ×2（弱点 炎）
        knock = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual(knock["evolution_stack"], metapod.evolution_stack)
        self.assertTrue(set(metapod.cards()) <= set(new.players[0].discard))
        self.assertEqual((new.decision.kind, new.decision.player), ("take_prize", 1))


# ---------------------------------------------------------------- 書き出し・複製


class SerializationTest(unittest.TestCase):
    def test_format_8(self):
        state = protected({"card": RATTATA, "energy": [FIRE]})
        me = state.players[0].active
        data = full(state)["players"][0]["active"]
        self.assertEqual(data["persistent_effects"], [{
            "effect": "prevent_damage", "source_card": me.card, "source_card_id": METAPOD, "source_player": 0,
            "created_turn": 3, "active_turn": 4,
        }])
        self.assertEqual(full(state)["players"][0]["bench"][0]["persistent_effects"], [])
        # v0.4b では 8 が最後。v0.6 で形式 9（あまごいで手札からつけた枚数）を加えた。持続する効果の項目は形式 9 でも同じ
        self.assertEqual(FORMAT_VERSIONS[-1], 9)
        self.assertEqual(state_to_dict(state, format_version=9)["players"], full(state)["players"])

    def test_older_formats_refuse_effects(self):
        state = protected({"card": RATTATA, "energy": [FIRE]})
        for version in range(1, 8):
            with self.subTest(format_version=version), self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)

    def test_without_effects_older_formats_are_unchanged(self):
        """持続する効果のない状態は、形式 1〜7 で今までどおり書き出せ、形式 8 は形式 7 に空の ``persistent_effects`` を加えたもの。"""
        state = unprotected({"card": RATTATA, "energy": [FIRE]})
        for version in (5, 6):  # 進化しているトランセルは形式 7 から
            with self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        seven, eight = state_to_dict(state, format_version=7), full(state)
        self.assertEqual(eight.pop("format_version"), 8)
        self.assertEqual(seven.pop("format_version"), 7)
        for p in eight["players"]:
            for pokemon in [p["active"], *p["bench"]]:
                self.assertEqual(pokemon.pop("persistent_effects"), [])
        self.assertEqual(seven, eight)

    def test_clone_deepcopy_pickle(self):
        state = protected({"card": RATTATA, "energy": [FIRE]})
        for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(full(copied), full(state))
            self.assertEqual(copied.players[0].active.persistent_effects, state.players[0].active.persistent_effects)
        # 複製した状態で効果が消えても、元の状態は変わらない
        new = apply_command(state, UseAttack(1, 0))
        self.assertEqual((len(state.players[0].active.persistent_effects), new.players[0].active.persistent_effects), (1, ()))


# ---------------------------------------------------------------- 不変条件


class PersistentEffectInvariantTest(unittest.TestCase):
    def problems_after(self, change):
        state = protected({"card": RATTATA, "energy": [FIRE]})
        self.assertEqual(check_invariants(state), [])
        change(state)
        return "\n".join(check_invariants(state))

    def effect(self, state):
        return state.players[0].active.persistent_effects[0]

    def test_detects_broken_states(self):
        cases = {
            "ベンチ": lambda s: (setattr(s.players[0].bench[0], "persistent_effects", s.players[0].active.persistent_effects)),
            "重なっている": lambda s: setattr(s.players[0].active, "persistent_effects", (self.effect(s),) * 2),
            "次の番": lambda s: setattr(s.players[0].active, "persistent_effects", (PreventDamage(s.players[0].active.card, 0, 3, 5),)),
            "発生源": lambda s: setattr(s.players[0].active, "persistent_effects", (PreventDamage(s.players[0].bench[0].card, 0, 3, 4),)),
            "整数": lambda s: setattr(s.players[0].active, "persistent_effects", (PreventDamage(s.players[0].active.card, 0, True, 4),)),
            "タプル": lambda s: setattr(s.players[0].active, "persistent_effects", ("prevent_damage",)),
            "persistent_effect_added がない": lambda s: setattr(s, "log", ()),
            "持ち主の番でない": lambda s: setattr(s.players[0].active, "persistent_effects", (PreventDamage(s.players[0].active.card, 0, 4, 5),)),
            "消したあと": lambda s: s.add_event("persistent_effect_removed", player=0, pokemon=s.players[0].active.card,
                                             pokemon_id=s.players[0].active.pokemon_id, persistent_effect="prevent_damage",
                                             source_card=s.players[0].active.card, created_turn=3, active_turn=4, reason="expired"),
            "進化": lambda s: s.add_event("evolve", player=0, pokemon_id=s.players[0].active.pokemon_id, from_card=0, from_card_id="x",
                                          to_card=0, to_card_id="x"),
            "ベンチに戻った": lambda s: s.add_event("switch", player=0, old_active=0, new_active=0,
                                              old_active_pokemon_id=s.players[0].active.pokemon_id, new_active_pokemon_id=0),
            "終わりを過ぎて": lambda s: s.add_event("turn_end", player=1),
        }
        for expected, change in cases.items():
            with self.subTest(case=expected):
                self.assertIn(expected, self.problems_after(change))

    def test_effects_are_not_cards(self):
        """持続する効果はカードではない: カードの数・トラッシュは変わらない（カードの保存則）。"""
        state = my_turn(stage1())
        new = apply_command(with_coin_results(state, H), UseAttack(0, 0))
        self.assertEqual(len(new.cards), len(state.cards))
        self.assertEqual(check_invariants(new), [])


# ---------------------------------------------------------------- 原子性


class AtomicityTest(unittest.TestCase):
    def test_rejections_do_not_touch_the_effect_or_rng(self):
        """効果があるときの不正な操作・原典で決められない操作は、効果も乱数も変えない（盤面を直接作った）。"""
        state = my_turn(stage1(prevent_damage=3, energy=(GRASS,)), hand=(FIRE,))
        assert_rejected(self, state, UseAttack(0, 0), "INSUFFICIENT_ENERGY")
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, FIRE), state.players[0].active.pokemon_id), "NOT_EVOLUTION_CARD")
        assert_rejected(self, state, Retreat(0, (), state.players[0].bench[0].card), "WRONG_RETREAT_COST")
        assert_rejected(self, protected({"card": DODUO, "energy": [FIRE]}), UseAttack(1, 0), "UNRESOLVED_PREVENTED_COIN_DAMAGE", UnsupportedError)

    def test_pending_decision_rejects_other_commands(self):
        state = my_turn(stage1(prevent_damage=3), hand=(SWITCH,))
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, SWITCH)))
        assert_rejected(self, state, UseAttack(0, 0), "WRONG_PHASE")
        self.assertEqual(len(state.players[0].active.persistent_effects), 1)


if __name__ == "__main__":
    unittest.main()

"""ゴースト（化石の秘密。PMCG3-030）のポケモンパワー「とうめい」（v0.9。docs/transparency-v0.9.md の T1〜T42・A4）。

最新の説明（p.160・p.159・p.323）: 「このカードがワザによってダメージや効果を受けるとき、コインを投げて「おもて」なら、このカードは
そのダメージと効果を受けない。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は消える。」。p.159 の特殊能力解説（自動的に
はたらく・バトル場でもベンチでも・ワザを失敗させる効果ではない・自分を対象とした「ワザによるダメージや効果」にだけ有効・
「ふきとばし」の例）と p.160 の解説（コイントスはゴースト側のプレイヤー）にしたがう。

盤面は ``build_test_state`` で直接作る（1 つの規定を確かめるテスト）。自然な対戦は tests/test_haunter_games_v0_9.py、ゴースとワザは
tests/test_haunter_line_v0_9.py。ワザによるダメージを受けること・ワザの効果を受けること・ワザの使用が成り立つことを区別して確かめる
（ゴーストが受けなくても、ワザは使ったことになり、ワザを使う側への要素は処理する。T17・T18）。乱数は、コインのログの数と、
状態の乱数がいくつ進んだか（``rng_draws``）の両方で確かめる。
"""

import copy
import dataclasses
import itertools
import pickle
import unittest
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS,
    EndTurn,
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    PlayTrainer,
    PowerKey,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    apply_command,
    check_invariants,
    load_card_pool,
    power_suppressors,
    state_to_dict,
    working_evasion_power,
)
from kyuura_engine.conditions import SLEEP
from kyuura_engine.effects import (
    DAMAGE_ELEMENT,
    SELF,
    AttackEffect,
    AttackEntry,
    AttackImmunityOnHeads,
    AttackKey,
    AttackUse,
    ConfuseOnHeads,
    DamageAndSelfSleep,
    ParalyzeOnHeads,
    PoisonOnHeads,
    attack_reaches,
    deal_attack_damage,
    evasion_power,
)
from kyuura_engine.resolution import codec, open_attack, programs
from kyuura_engine.resolution.questions import OpenQuestion
from kyuura_engine.rng import copy_rng, rng_fingerprint
from kyuura_engine.state import Asleep
from tests.helpers import (
    ABRA,
    ALAKAZAM,
    BASE_HAUNTER,
    BULBASAUR,
    BUTTERFREE,
    CATERPIE,
    DEFENDER,
    DEWGONG,
    DODUO,
    FIGHTING,
    FIRE,
    GASTLY,
    GRASS,
    GRIMER,
    HAUNTER,
    IVYSAUR,
    KADABRA,
    KAKUNA,
    LIGHTNING,
    MACHOP,
    METAPOD,
    MUK,
    PARAS,
    PIKACHU,
    PLUSPOWER,
    PONYTA,
    POTION,
    PSYCHIC,
    RATTATA,
    SEEL,
    STARMIE,
    STARYU,
    V0_69_CARDS,
    WEEDLE,
    H,
    T,
    build_test_state,
    coin_events,
    no_base_haunter_pool,
    uids,
    with_coin_results,
)
from tests.test_effect_preflight_v0_3d import ATTACKS, EVOLVED_FROM, energy_for

TURN = 7
TRANSPARENCY = PowerKey(HAUNTER, 0)
POWER = str(TRANSPARENCY)


def haunter(**extra):
    return {"card": HAUNTER, "evolved_from": GASTLY, **extra}


def board(attacker, defender=None, *, bench0=(), bench1=(), hand0=(), turn=TURN, effects=None):
    """プレイヤー 0（番のプレイヤー）がワザを使う。プレイヤー 1 のバトル場に、既定でゴースト（とうめい）。"""
    return build_test_state([
        {"active": attacker, "bench": list(bench0) or [PONYTA], "hand": list(hand0)},
        {"active": defender or haunter(), "bench": list(bench1) or [RATTATA]},
    ], turn_number=turn, effects=effects)


def rng_draws(before, after, limit=12):
    """``before`` から ``after`` までに状態の乱数が進んだ回数（エンジンのコインは 1 枚につき ``getrandbits(1)`` を 1 回）。"""
    probe = copy_rng(before.rng)
    for count in range(limit + 1):
        if rng_fingerprint(probe) == rng_fingerprint(after.rng):
            return count
        probe.getrandbits(1)
    raise AssertionError("乱数の進み方が分からない")


def run(state, command, *sides):
    """コインの結果を決めてコマンドを処理する。(新しい状態, 新しいログ, 進んだ乱数の回数)。"""
    start = with_coin_results(state, *sides) if sides else state
    new = apply_command(start, command)
    assert check_invariants(new) == []
    return new, [dict(e) for e in new.log[len(start.log):]], rng_draws(start, new)


def kinds(events):
    return [e["kind"] for e in events]


def power_coins(events):
    return [e for e in events if e["kind"] == "coin_flip" and e["source"] == "power"]


def written(state):
    return state_to_dict(state, format_version=9)


def applied(events, pokemon_id):
    """ワザで付いた特殊状態（ログから。ワザのあとのポケモンチェックで、ねむりの回復・どくのダメージが続くので、最後の状態では見ない）。"""
    return [e["condition"] for e in events if e["kind"] == "special_condition" and e["pokemon_id"] == pokemon_id]


def damage_to(events, state, player):
    """ワザで相手（``player``）のバトル場のポケモンに与えたダメージのログの量（ポケモンチェックのどくのダメージは含めない）。"""
    uid = state.players[player].active.card
    return [e["amount"] for e in events if e["kind"] == "damage" and e["pokemon"] == uid]


class BasicTest(unittest.TestCase):
    """T1〜T6・T9〜T13・T16・T33・T37・T38。"""

    rattata = {"card": RATTATA, "energy": [FIRE]}

    def test_heads_the_haunter_does_not_receive_the_damage(self):
        """p.160「「おもて」なら、このカードはそのダメージと効果を受けない」（T5）。コインはゴースト側のプレイヤー（T33）が 1 枚。
        ダメージのログはなく、受けなかった最終ダメージを attack_evaded に残す。"""
        state = board(self.rattata)
        new, events, draws = run(state, UseAttack(0, 0), H)
        self.assertEqual(draws, 1)
        self.assertEqual(kinds(events)[:4], ["attack", "coin_flip", "evade_check", "attack_evaded"])
        coin, check, evaded = events[1:4]
        target = state.players[1].active
        self.assertEqual((coin["player"], coin["source"], coin["effect"], coin["pokemon_id"], coin["result"]),
                         (1, "power", POWER, target.pokemon_id, "heads"))
        self.assertEqual((check["player"], check["pokemon_id"], check["power"], check["attacker"], check["attacker_pokemon_id"],
                          check["effect"], check["element"], check["result"], check["evaded"]),
                         (1, target.pokemon_id, POWER, 0, state.players[0].active.pokemon_id, f"{RATTATA}#0", "damage", "heads", True))
        self.assertEqual((evaded["element"], evaded["amount"], evaded["pokemon_id"]), ("damage", 20, target.pokemon_id))
        self.assertNotIn("damage", kinds(events))
        self.assertEqual(new.players[1].active.damage, 0)

    def test_tails_the_haunter_receives_the_damage(self):
        """「うら」なら、いつもどおり受ける（T6）。コインは 1 枚。"""
        new, events, draws = run(board(self.rattata), UseAttack(0, 0), T)
        self.assertEqual(draws, 1)
        self.assertEqual(kinds(events)[:4], ["attack", "coin_flip", "evade_check", "damage"])
        self.assertFalse(events[2]["evaded"])
        self.assertNotIn("attack_evaded", kinds(events))
        self.assertEqual(new.players[1].active.damage, 20)

    def test_the_power_is_gone_while_asleep_paralyzed_or_confused(self):
        """p.160「このカードが「ねむり・マヒ・こんらん」状態のとき、この力は消える」（T9〜T11）。コインを投げない（T16）。"""
        for condition in ({"sleep": True}, {"paralysis": TURN - 1}, {"confusion": True}):
            with self.subTest(condition=condition):
                state = board(self.rattata, haunter(**condition))
                new, events, _ = run(state, UseAttack(0, 0))
                self.assertEqual(power_coins(events), [])
                self.assertNotIn("evade_check", kinds(events))
                self.assertEqual(new.players[1].active.damage, 20)
                self.assertIsNone(working_evasion_power(state, state.players[1].active.pokemon_id))

    def test_poison_does_not_stop_the_power(self):
        """説明が挙げるのはねむり・マヒ・こんらんだけ（T12。SUPPORTED）。"""
        state = board(self.rattata, haunter(poison=10))
        new, events, draws = run(state, UseAttack(0, 0), H)
        self.assertEqual(len(power_coins(events)), 1)
        self.assertEqual(damage_to(events, state, 1), [])
        self.assertEqual(new.players[1].active.damage, 10)  # ポケモンチェックのどく（ワザによるダメージではない。T35）

    def test_the_power_works_again_after_recovering_from_sleep(self):
        """ねむりから回復したら、また、はたらく（T13）。ねむりのゴーストはコインを投げずに受け、ポケモンチェックの「おもて」で回復し、
        次の自分の番のワザでは判定する。"""
        state = board(self.rattata, haunter(sleep=True))
        asleep, events, _ = run(state, UseAttack(0, 0), H)  # H はポケモンチェックのねむりのコイン
        self.assertEqual([e["source"] for e in coin_events(asleep, len(state.log))], ["pokemon_check"])
        self.assertEqual(asleep.players[1].active.damage, 20)
        self.assertIsNone(asleep.players[1].active.conditions.exclusive)
        back = apply_command(asleep, EndTurn(1))
        new, events, draws = run(back, UseAttack(0, 0), H)
        self.assertEqual((draws, len(power_coins(events))), (1, 1))
        self.assertEqual(new.players[1].active.damage, 20)

    def test_works_right_after_evolving(self):
        """ゴースから進化したら、すぐにはたらく（いちばん上のカードで決める。p.310。T38）。ゴースは特殊能力を持たない。"""
        state = build_test_state([
            {"active": self.rattata, "bench": [PONYTA]}, {"active": GASTLY, "bench": [RATTATA], "hand": [HAUNTER]},
        ], turn_number=TURN)
        gastly, events, _ = run(state, UseAttack(0, 0))
        self.assertEqual(power_coins(events), [])
        self.assertEqual(gastly.players[1].active.damage, 20)
        evolved = apply_command(gastly, EvolvePokemon(1, uids(gastly, 1, "hand", HAUNTER)[0], gastly.players[1].active.pokemon_id))
        self.assertEqual(working_evasion_power(evolved, evolved.players[1].active.pokemon_id), TRANSPARENCY)
        mine = apply_command(evolved, EndTurn(1))
        new, events, draws = run(mine, UseAttack(0, 0), H)
        self.assertEqual((draws, len(power_coins(events))), (1, 1))
        self.assertEqual(new.players[1].active.damage, 20)  # 進化の前に受けたダメージはそのまま（p.310）

    def test_cannot_be_declared(self):
        """自動的にはたらく特殊能力で、使用を宣言しない（p.159・p.323。T1・T37）。宣言は POWER_NOT_DECLARABLE で、状態・乱数・ログは
        変わらない。"""
        state = build_test_state([{"active": haunter(energy=[PSYCHIC]), "bench": [GASTLY]}, {"active": RATTATA}], turn_number=TURN)
        before, fingerprint, log = written(state), rng_fingerprint(state.rng), state.log
        for command in (UsePokemonPower(0, state.players[0].active.pokemon_id, 0),
                        UsePokemonPower(0, state.players[0].active.pokemon_id, 0, None, None, state.players[0].bench[0].pokemon_id)):
            with self.assertRaises(IllegalActionError) as ctx:
                apply_command(state, command)
            self.assertEqual(ctx.exception.code, "POWER_NOT_DECLARABLE")
        self.assertEqual((written(state), rng_fingerprint(state.rng)), (before, fingerprint))
        self.assertIs(state.log, log)

    def test_registration(self):
        """登録は宣言しない ``AttackImmunityOnHeads``。第1弾のゴースト（PMCG1-047。同じ名前の別のカード）は特殊能力を持たない（v0.44 まで参照カード。
        v0.45 で対応にした。ワザの登録を除いた登録表では対応にならない）。"""
        entry = DEFAULT_EFFECTS.power_entry(HAUNTER, 0)
        self.assertEqual(entry.effect, AttackImmunityOnHeads())
        self.assertFalse(entry.effect.declared)
        pool = load_card_pool()
        self.assertEqual(pool.get(BASE_HAUNTER).name_ja, pool.get(HAUNTER).name_ja)
        self.assertEqual(pool.get(BASE_HAUNTER).powers, ())
        self.assertTrue(pool.is_playable(BASE_HAUNTER))
        self.assertFalse(no_base_haunter_pool().is_playable(BASE_HAUNTER))

    def test_public_query(self):
        """``working_evasion_power``（v0.9 の公開の問い合わせ）は状態を変えず、乱数を使わない。場にいない番号は ValueError。"""
        state = board(self.rattata, bench1=[haunter(), GASTLY])
        before, fingerprint = written(state), rng_fingerprint(state.rng)
        active, bench_haunter, gastly = state.players[1].active, state.players[1].bench[0], state.players[1].bench[1]
        self.assertEqual(working_evasion_power(state, active.pokemon_id), TRANSPARENCY)
        self.assertEqual(working_evasion_power(state, bench_haunter.pokemon_id), TRANSPARENCY)  # ベンチでも（T7）
        self.assertIsNone(working_evasion_power(state, gastly.pokemon_id))
        self.assertIsNone(working_evasion_power(state, state.players[0].active.pokemon_id))
        with self.assertRaises(ValueError):
            working_evasion_power(state, 999)
        self.assertEqual((written(state), rng_fingerprint(state.rng)), (before, fingerprint))


class OneCoinPerAttackTest(unittest.TestCase):
    """1 つのワザにつき 1 匹 1 回（T4。SUPPORTED）。最初に受ける要素でコインを投げ、その結果がそのワザのダメージと効果のすべてに
    当てはまる（T5・T6・T28・T32）。ワザのコインと「とうめい」のコインは、要素の順番どおり（T19・T40）。"""

    def check(self, state, index, sides, *, power_coins_expected=1):
        new, events, draws = run(state, UseAttack(0, index), *sides)
        self.assertEqual(len(power_coins(events)), power_coins_expected)
        self.assertEqual(len(coin_events(new, len(state.log))), draws)
        return new, events

    def test_nightmare_damage_then_sleep(self):
        """ゴーストの「あくむ」（10 とねむり）をゴーストに: 「おもて」ならダメージもねむりも受けない、「うら」なら両方。コインは 1 枚。"""
        state = board(haunter(energy=[PSYCHIC, PSYCHIC]))
        ghost = state.players[1].active.pokemon_id
        evaded, events = self.check(state, 0, (H,))
        self.assertEqual([(e["element"], e.get("amount")) for e in events if e["kind"] == "attack_evaded"], [("damage", 10), ("sleep", None)])
        self.assertEqual((evaded.players[1].active.damage, applied(events, ghost)), (0, []))
        hit, events = self.check(state, 0, (T, T))  # 2 枚目はポケモンチェックのねむりのコイン
        self.assertEqual((damage_to(events, state, 1), applied(events, ghost)), ([10], ["sleep"]))
        self.assertTrue(hit.players[1].active.conditions.asleep)

    def test_poison_powder_damage_then_poison(self):
        """フシギソウの「どくのこな」（20 とどく。コインなし）: A4-1 の例。"""
        state = board({"card": IVYSAUR, "evolved_from": BULBASAUR, "energy": [GRASS] * 3})
        ghost = state.players[1].active.pokemon_id
        evaded, events = self.check(state, 1, (H,))
        self.assertEqual([e["element"] for e in events if e["kind"] == "attack_evaded"], ["damage", "poison"])
        self.assertEqual((evaded.players[1].active.damage, evaded.players[1].active.conditions.poison), (0, None))
        hit, events = self.check(state, 1, (T,))
        self.assertEqual((damage_to(events, state, 1), applied(events, ghost)), ([20], ["poison"]))
        self.assertEqual(hit.players[1].active.damage, 30)  # ポケモンチェックのどくの 10 を含む

    def test_whirlwind_damage_then_switch(self):
        """バタフリーの「ふきとばし」: 入れ替えはバトル場のゴーストへの効果（p.159。T23。CONFIRMED）。「おもて」なら入れ替わらず、決定も
        出ない。「うら」なら相手が決定し、決定のあと（resume）にコインを投げ直さない。"""
        state = board({"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}, bench1=[GASTLY])
        haunter_id = state.players[1].active.pokemon_id
        evaded, events = self.check(state, 0, (H,))
        self.assertEqual([e["element"] for e in events if e["kind"] == "attack_evaded"], ["damage", "forced_switch"])
        self.assertIsNone(evaded.decision)
        self.assertEqual(evaded.players[1].active.pokemon_id, haunter_id)
        waiting, _ = self.check(state, 0, (T,))
        self.assertEqual((waiting.decision.kind, waiting.decision.player), ("forced_switch", 1))
        switched = apply_command(waiting, ResolveDecision(1, waiting.decision.id, (waiting.decision.options[0],)))
        self.assertEqual(rng_fingerprint(switched.rng), rng_fingerprint(waiting.rng))
        self.assertEqual(power_coins(switched.log[len(waiting.log):]), [])
        self.assertEqual([pk.pokemon_id for pk in switched.players[1].bench], [haunter_id])
        self.assertEqual(switched.players[1].bench[0].damage, 20)

    def test_whirlwind_choosing_a_bench_haunter_needs_no_coin(self):
        """p.159「「ふきとばし」は、相手の対戦ポケモンへの効果です。ベンチのポケモンへの効果ではないので、ゴーストがベンチにいて、
        ［とうめい］の効果がはたらいていても、自分でゴーストを選択してバトル場に出すことができます」（T23）。"""
        state = board({"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}, defender=GASTLY,
                      bench1=[haunter()])
        waiting, events, _ = run(state, UseAttack(0, 0))
        self.assertEqual(power_coins(events), [])
        bench_haunter = state.players[1].bench[0].pokemon_id
        switched = apply_command(waiting, ResolveDecision(1, waiting.decision.id, (bench_haunter,)))
        self.assertEqual(switched.players[1].active.pokemon_id, bench_haunter)
        self.assertEqual(power_coins(switched.log[len(waiting.log):]), [])

    def test_sticky_goo_attacker_coin_first(self):
        """ロケット団のベトベターの「ねばりつく」（コインで 20 を追加してマヒ）: ワザのコインがダメージの量と効果を決め、そのあとダメージを
        受けるときに「とうめい」のコイン（T19・T40）。「おもて」ならダメージもマヒも受けない。"""
        state = board({"card": GRIMER, "energy": [GRASS, GRASS]})
        for sides, damage, paralyzed in (((H, H), 0, False), ((H, T), 30, True), ((T, H), 0, False), ((T, T), 10, False)):
            with self.subTest(sides=sides):
                new, events = self.check(state, 1, sides)
                self.assertEqual([(e["source"], e["result"]) for e in events if e["kind"] == "coin_flip"],
                                 [("attack", sides[0].value), ("power", sides[1].value)])
                self.assertEqual((new.players[1].active.damage, new.players[1].active.conditions.paralyzed), (damage, paralyzed))

    def test_fury_attack_attacker_coins_first(self):
        """ドードーの「みだれづき」（コイン 2 枚の「おもて」の数 × 10）: ワザのコインのあと「とうめい」（T40）。「おもて」が 0 枚なら最終
        ダメージが 0 で、ダメージを受けなかったのでコインを投げない（p.321。T21）。"""
        state = board({"card": DODUO, "energy": [FIRE]})
        new, events = self.check(state, 0, (H, H, H))
        self.assertEqual([e["source"] for e in events if e["kind"] == "coin_flip"], ["attack", "attack", "power"])
        self.assertEqual(next(e for e in events if e["kind"] == "attack_evaded")["amount"], 20)
        zero, events = self.check(state, 0, (T, T), power_coins_expected=0)
        self.assertEqual(next(e for e in events if e["kind"] == "damage")["amount"], 0)

    def test_thundershock_power_coin_before_the_attackers_self_damage(self):
        """ピカチュウの「でんげき」（30・「うら」なら自分にも 10）: ダメージの要素で「とうめい」のコイン、そのあとワザの自分へのダメージの
        コイン（T19）。ゴーストが受けなくても、ワザを使う側への要素は処理する（p.159「相手のワザを失敗させる効果ではありません」。T18）。"""
        state = board({"card": PIKACHU, "energy": [LIGHTNING, LIGHTNING]})
        evaded, events = self.check(state, 1, (H, T))
        self.assertEqual([e["source"] for e in events if e["kind"] == "coin_flip"], ["power", "attack"])
        self.assertEqual((evaded.players[1].active.damage, evaded.players[0].active.damage), (0, 10))
        hit, _ = self.check(state, 1, (T, H))
        self.assertEqual((hit.players[1].active.damage, hit.players[0].active.damage), (30, 0))

    def test_effects_without_damage(self):
        """ダメージのない特殊状態のワザ（パラスの「キノコのほうし」・ロケット団のベトベターの「どくガス」）: 効果を受けるときにコイン
        （T22。CONFIRMED）。"""
        for attacker, index, condition in (({"card": PARAS, "energy": [GRASS, GRASS]}, 1, "sleep"),
                                           ({"card": GRIMER, "energy": [GRASS]}, 0, "poison")):
            with self.subTest(attacker=attacker["card"]):
                state = board(attacker)
                ghost = state.players[1].active.pokemon_id
                evaded, events = self.check(state, index, (H,))
                self.assertEqual([(e["element"], e.get("amount")) for e in events if e["kind"] == "attack_evaded"], [(condition, None)])
                self.assertEqual(next(e for e in events if e["kind"] == "evade_check")["element"], condition)
                target = evaded.players[1].active
                self.assertEqual((target.conditions.exclusive, target.conditions.poison, applied(events, ghost)), (None, None, []))
                hit, events = self.check(state, index, (T,))
                self.assertEqual(applied(events, ghost), [condition])


class DamageCalculationTest(unittest.TestCase):
    """弱点・抵抗力・ディフェンダー・プラスパワーを計算して最終ダメージが決まってから、受けるかを決める（T20・T21・T29・T39）。"""

    def test_resistance_to_zero_means_no_coin(self):
        """ワンリキーの「けたぐり」（闘 20）は、ゴーストの抵抗力（闘 −30）で 0。「ダメージを受けなかった」（p.321）のでコインを投げない
        （T21）。ダメージの要素はいつもどおり 0 で記録する。"""
        new, events, draws = run(board({"card": MACHOP, "energy": [FIGHTING]}), UseAttack(0, 0))
        self.assertEqual((draws, power_coins(events)), (0, []))
        self.assertEqual(next(e for e in events if e["kind"] == "damage")["amount"], 0)

    def test_defender_to_zero_means_no_coin(self):
        """ディフェンダー（トレーナーの効果。受ける。T29）で 20 − 20 = 0 ならコインを投げない（T39）。"""
        defended = haunter(trainers=[(DEFENDER, TURN)])
        new, events, draws = run(board({"card": RATTATA, "energy": [FIRE]}, defended), UseAttack(0, 0))
        self.assertEqual((draws, power_coins(events)), (0, []))

    def test_defender_to_zero_then_the_effect_needs_the_coin(self):
        """ダメージが 0 なら、同じワザの効果（どく）を受けるときに 1 回投げる（A4-1）。"""
        state = board({"card": IVYSAUR, "evolved_from": BULBASAUR, "energy": [GRASS] * 3}, haunter(trainers=[(DEFENDER, TURN)]))
        evaded, events, _ = run(state, UseAttack(0, 1), H)
        self.assertEqual([e["element"] for e in events if e["kind"] in ("evade_check", "attack_evaded")], ["poison", "poison"])
        self.assertIsNone(evaded.players[1].active.conditions.poison)
        hit, events, _ = run(state, UseAttack(0, 1), T)
        self.assertIsNotNone(hit.players[1].active.conditions.poison)

    def test_pluspower_is_part_of_the_calculation(self):
        """プラスパワー（p.321 の 5 段階）を加えた最終ダメージを受けない（attack_evaded の量は 30）。"""
        state = board({"card": RATTATA, "energy": [FIRE]}, hand0=[PLUSPOWER])
        state = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        _, events, _ = run(state, UseAttack(0, 0), H)
        self.assertEqual(next(e for e in events if e["kind"] == "attack_evaded")["amount"], 30)

    def test_damage_prevented_state_is_checked_first(self):
        """「ダメージを受けない」状態（持続する効果）なら、ダメージの要素は無効で、受けるかを評価しない（T42。ゴーストに持続する効果を
        与えるワザは対応カードにないので、盤面を直接作った）。"""
        _, events, draws = run(board({"card": RATTATA, "energy": [FIRE]}, haunter(prevent_damage=TURN - 1)), UseAttack(0, 0))
        self.assertEqual((draws, power_coins(events)), (0, []))
        self.assertIn("damage_prevented", kinds(events))


class AttackSucceedsTest(unittest.TestCase):
    """ワザは成り立つ（p.159「相手のワザを失敗させる効果ではありません」・p.309。T17・T18・T31・T41。A4-2）。"""

    def test_the_attack_is_used_and_the_turn_ends(self):
        """「おもて」でも、ワザは使ったことになり（ログ attack）、エネルギーはついたまま、番は終わる。"""
        state = board({"card": RATTATA, "energy": [FIRE]})
        new, events, _ = run(state, UseAttack(0, 0), H)
        self.assertEqual(kinds(events)[0], "attack")
        self.assertIn("turn_end", kinds(events))
        self.assertEqual((new.turn_number, new.current_player), (TURN + 1, 1))
        self.assertEqual(new.players[0].active.energy, state.players[0].active.energy)

    def test_drain_needs_dealt_damage(self):
        """バタフリーの「メガドレイン」・フシギダネの「やどりぎのタネ」: 受けなかったらダメージを与えていないので回復しない（T41）。"""
        for attacker, index, healed in (
            ({"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS] * 4, "damage": 30}, 1, 20),
            ({"card": BULBASAUR, "energy": [GRASS, GRASS], "damage": 30}, 0, 10),
        ):
            with self.subTest(attacker=attacker["card"]):
                state = board(attacker)
                evaded, events, _ = run(state, UseAttack(0, index), H)
                self.assertEqual(evaded.players[0].active.damage, 30)
                self.assertNotIn("drain_heal", kinds(events))
                hit, events, _ = run(state, UseAttack(0, index), T)
                self.assertEqual(hit.players[0].active.damage, 30 - healed)

    def test_knock_out_only_by_received_damage(self):
        """受けなかったダメージはのらないので、それできぜつしない。受けたらいつもどおり（きぜつはワザの要素をすべて処理したあと。T31）。"""
        state = board({"card": RATTATA, "energy": [FIRE]}, haunter(damage=30))
        evaded, events, _ = run(state, UseAttack(0, 0), H)
        self.assertNotIn("knock_out", kinds(events))
        self.assertEqual(evaded.players[1].active.damage, 30)
        hit, events, _ = run(state, UseAttack(0, 0), T)
        self.assertIn("knock_out", kinds(events))

    def test_whirlwind_heads_on_a_damaged_haunter(self):
        """受けなかったダメージでは、きぜつしたことにならない（T31）。「おもて」なら入れ替えも受けない（「対象がいない」にしない）。"""
        state = board({"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}, haunter(damage=30))
        new, events, _ = run(state, UseAttack(0, 0), H)
        self.assertEqual([e["element"] for e in events if e["kind"] == "attack_evaded"], ["damage", "forced_switch"])
        self.assertNotIn("forced_switch_skipped", kinds(events))
        self.assertEqual((new.players[1].active.damage, new.players[1].active.pokemon_id), (30, state.players[1].active.pokemon_id))

    def test_whirlwind_after_a_knock_out_needs_no_second_coin(self):
        """「ふきとばし」のダメージ（「うら」で受けた）できぜつしたら、入れ替えの対象がいない（p.309）。コインは 1 枚のまま。"""
        state = board({"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}, haunter(damage=30))
        new, events, draws = run(state, UseAttack(0, 0), T)
        self.assertEqual(len(power_coins(events)), 1)
        self.assertIn("forced_switch_skipped", kinds(events))


class NotAnAttackTest(unittest.TestCase):
    """ワザによるダメージや効果でないものには、はたらかない（T29・T30・T34・T35）。"""

    def test_pokemon_check_poison(self):
        """ポケモンチェックの「どく」のダメージは「ワザによるダメージ」ではない（p.321・p.323。T35）。"""
        state = board({"card": RATTATA, "energy": [FIRE]}, haunter(poison=10, trainers=[(DEFENDER, TURN)]))
        new, events, _ = run(state, UseAttack(0, 0))
        self.assertEqual(power_coins(events), [])
        self.assertEqual(next(e for e in events if e["kind"] == "poison_damage")["pokemon_id"], state.players[1].active.pokemon_id)

    def test_confusion_damage_to_itself(self):
        """こんらんのゴーストの「うら」の 20（ワザの説明の処理ではない。こんらんで力も消えている。T11・T34）。ゴーストは弱点がないので 20。"""
        state = build_test_state([{"active": haunter(energy=[PSYCHIC, PSYCHIC], confusion=True), "bench": [GASTLY]},
                                  {"active": RATTATA}], turn_number=TURN)
        new, events, _ = run(state, UseAttack(0, 0), T)
        self.assertEqual(next(e for e in events if e["kind"] == "confusion_damage")["amount"], 20)
        self.assertEqual(power_coins(events), [])

    def test_trainers_and_powers(self):
        """トレーナー（きずぐすり）・特殊能力（ダメージスワップ）によるダメージや効果は受ける（p.159。T29・T30）。"""
        state = build_test_state([
            {"active": {"card": ALAKAZAM, "evolved_from": [ABRA, KADABRA], "damage": 20}, "bench": [haunter(damage=20)], "hand": [POTION]},
            {"active": RATTATA},
        ], turn_number=TURN)
        alakazam, ghost = state.players[0].active, state.players[0].bench[0]
        swapped = apply_command(state, UsePokemonPower(0, alakazam.pokemon_id, 0, None, alakazam.pokemon_id, ghost.pokemon_id))
        self.assertEqual(swapped.players[0].bench[0].damage, 30)
        healed = apply_command(swapped, PlayTrainer(0, uids(swapped, 0, "hand", POTION)[0]))
        if healed.decision is not None:
            healed = apply_command(healed, ResolveDecision(0, healed.decision.id, (ghost.pokemon_id,)))
        self.assertEqual(healed.players[0].bench[0].damage, 10)
        self.assertEqual(power_coins(healed.log[len(state.log):]), [])
        self.assertEqual(rng_fingerprint(healed.rng), rng_fingerprint(state.rng))


class SelfHit(AttackEffect):
    """テスト専用: ワザを使うポケモン自身に 10 ダメージ（p.320 のダメージの (3)）。ゴーストが自分のワザで自分を対象とする場合（T8・T24）
    を確かめるため（対応カードにない）。"""

    implementation_id = "test_self_hit"

    def check(self, attack):
        return []

    def resolve(self, state, use):
        deal_attack_damage(state, use, SELF, 10)


class DirectReceptionTest(unittest.TestCase):
    """``attack_reaches`` を直接呼ぶ（対応カードのワザでは起こらない場合。T7・T8・T24〜T27）。

    v0.16b: v0.13 の約束の補助関数は解決の基盤のワザの枠に委ねるので、``resolution.open_attack`` で枠を開いた ``AttackUse`` で呼ぶ
    （1 つの枠 = 1 つのワザ）。"""

    def board(self):
        return build_test_state([{"active": {"card": RATTATA, "energy": [FIRE]}, "bench": [haunter()]},
                                 {"active": haunter(), "bench": [haunter(), GASTLY]}], turn_number=TURN)

    def use(self, state, player=0):
        return open_attack(state, player)

    def test_bench_haunter_flips(self):
        """ベンチのゴーストもはたらく（p.159「バトル場でもベンチでもはたらきます」。T7・T25）。"""
        state = with_coin_results(self.board(), H)
        bench = state.players[1].bench[0]
        self.assertFalse(attack_reaches(state, self.use(state), 1, bench, DAMAGE_ELEMENT, amount=20))
        self.assertEqual([(e["player"], e["pokemon_id"]) for e in coin_events(state)], [(1, bench.pokemon_id)])

    def test_own_attack_flips_for_the_owner(self):
        """自分のワザでも、自分を対象とする要素にはたらく（p.159「相手の対戦ポケモン、自分の対戦ポケモンのワザにかぎらず」。T8）。
        コインはゴースト側のプレイヤー（T33）。"""
        state = with_coin_results(self.board(), T)
        mine = state.players[0].bench[0]
        self.assertTrue(attack_reaches(state, self.use(state), 0, mine, DAMAGE_ELEMENT, amount=20))
        self.assertEqual([e["player"] for e in coin_events(state)], [0])

    def test_each_haunter_flips_once_per_attack(self):
        """同じワザの同じポケモンは 1 回だけ（T4）。新しいワザ（新しい枠）では投げ直す。ゴースは投げない。

        1 つのワザで 2 匹目の「とうめい」を評価すると、コインの順番が原典で決められない（T27。docs/transparency-v0.9.md・CLAUDE.md
        「1 つのワザで複数の「とうめい」のポケモンが受ける場合のコインの順番（T27）は原典で決められません」）ので、解決の基盤は 2 匹目の前に
        止める（コードのない問い ``multiple_evasion``。今の対応カードでは起こらないので、コマンドの入口で ``RuntimeError``）。v0.16b: v0.15 までの
        補助関数（v0.13 の ``attack_reaches``）は 2 匹目も評価していた（対応カードでは起こらない）。解決の基盤の検出にそろえた。"""
        state = with_coin_results(self.board(), H, T, H)
        use = self.use(state)
        active, bench, gastly = state.players[1].active, state.players[1].bench[0], state.players[1].bench[1]
        self.assertFalse(attack_reaches(state, use, 1, active, DAMAGE_ELEMENT, amount=20))
        self.assertTrue(attack_reaches(state, use, 1, gastly, DAMAGE_ELEMENT, amount=20))  # ゴースは「とうめい」を持たない
        self.assertFalse(attack_reaches(state, use, 1, active, "sleep"))  # 同じワザの同じポケモンは投げ直さない（T4）
        self.assertEqual(len(coin_events(state)), 1)
        self.assertEqual(use.reception, {active.pokemon_id: False})
        with self.assertRaises(OpenQuestion) as caught:
            attack_reaches(state, use, 1, bench, DAMAGE_ELEMENT, amount=20)  # 2 匹目の「とうめい」（T27）
        self.assertEqual(caught.exception.key, "multiple_evasion")
        self.assertEqual(len(coin_events(state)), 1)  # 2 匹目のコインは投げない
        self.assertTrue(attack_reaches(state, self.use(state), 1, bench, DAMAGE_ELEMENT, amount=20))  # 新しいワザ（2 枚目 T）
        self.assertFalse(attack_reaches(state, self.use(state), 1, active, DAMAGE_ELEMENT, amount=20))  # 新しいワザ（3 枚目 H）
        self.assertEqual(len(coin_events(state)), 3)

    def test_not_working_is_not_recorded(self):
        """はたらいていなければ記録しない（あとの要素で、そのときの状態から求める）。未定義の要素の種類は ValueError。"""
        state = with_coin_results(self.board(), H)
        use = self.use(state)
        active = state.players[1].active
        active.conditions = dataclasses.replace(active.conditions, exclusive=Asleep())
        self.assertTrue(attack_reaches(state, use, 1, active, DAMAGE_ELEMENT, amount=20))
        self.assertEqual((use.reception, coin_events(state)), ({}, []))
        with self.assertRaises(ValueError):
            attack_reaches(state, use, 1, active, "energy")
        self.assertIsNone(evasion_power(state, active))

    def test_attack_use_memo_is_not_state(self):
        """記録はワザ 1 回の中だけの値で、比較・ハッシュ・書き出しに含めない（状態に持たない。書き出しの形式は 9 のまま）。v0.16b: 記録は
        解決の基盤の枠が持ち（``AttackUse.reception`` はそれを読む）、``AttackUse`` は枠への入口を比較・ハッシュ・表示に含めない。"""
        a = self.use(self.board())
        b = AttackUse(a.player, a.pokemon_id, a.key)
        a.reception[3] = False
        self.assertEqual(a.runtime.reception, {3: False})
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))
        self.assertNotIn("reception", repr(a))

    def test_own_attack_targeting_itself(self):
        """テスト専用の効果で、ゴーストが自分のワザで自分にダメージ（T8・T24）: 「おもて」なら受けない。コインは自分（ゴースト側）。"""
        text = load_card_pool().get(HAUNTER).attacks[0].text_ja
        effects = DEFAULT_EFFECTS.with_attacks("test-self-hit", {AttackKey(HAUNTER, 0): AttackEntry(SelfHit(), "あくむ", text_ja=text,
                                                                                                    play_text_ja=text)})
        state = build_test_state([{"active": haunter(energy=[PSYCHIC, PSYCHIC]), "bench": [GASTLY]}, {"active": RATTATA}],
                                 turn_number=TURN, effects=effects)
        evaded, events, _ = run(state, UseAttack(0, 0), H)
        self.assertEqual([(e["player"], e["source"]) for e in events if e["kind"] == "coin_flip"], [(0, "power")])
        self.assertEqual(evaded.players[0].active.damage, 0)
        hit, _, _ = run(state, UseAttack(0, 0), T)
        self.assertEqual(hit.players[0].active.damage, 10)


class ChemicalGasTest(unittest.TestCase):
    """かがくへんかガスがはたらいていれば「とうめい」の力は消える（p.48・p.323。T14・T15。A4-3）。v0.8 の抑止の判定
    （``continuous.suppressors_of``）をそのまま使う。"""

    rattata = {"card": RATTATA, "energy": [FIRE]}
    muk = {"card": MUK, "evolved_from": GRIMER}

    def test_either_players_muk_suppresses(self):
        for bench0, bench1 in (([self.muk], ()), ((), [self.muk])):
            with self.subTest(attacker_side=bool(bench0)):
                state = board(self.rattata, bench0=bench0, bench1=bench1)
                ghost = state.players[1].active.pokemon_id
                self.assertIsNone(working_evasion_power(state, ghost))
                self.assertTrue(power_suppressors(state, ghost))
                new, events, draws = run(state, UseAttack(0, 0))
                self.assertEqual((draws, power_coins(events)), (0, []))
                self.assertEqual(new.players[1].active.damage, 20)

    def test_declaring_under_the_gas_is_not_declarable(self):
        """宣言しない特殊能力の確認（POWER_NOT_DECLARABLE）は、消されているか（POWER_SUPPRESSED）より先（v0.8 の順番）。"""
        state = build_test_state([{"active": haunter(), "bench": [self.muk]}, {"active": RATTATA}], turn_number=TURN)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        self.assertEqual(ctx.exception.code, "POWER_NOT_DECLARABLE")

    def test_confused_muk_attacking_lets_the_power_work(self):
        """こんらんのベトベトンの力は消えている（v0.8 の G9〜G11）ので、ゴーストの「とうめい」ははたらく。ベトベトンの「ヘドロこうげき」
        （ダメージ → ワザのコイン → どく）は T19b で止まる（こんらんのコインの前）。こんらんでなければ、かがくへんかガスで「とうめい」は
        消えていて止めない。"""
        muk = {**self.muk, "energy": [GRASS] * 3}
        confused = board({**muk, "confusion": True})
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(confused, UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, "UNRESOLVED_EVADED_EFFECT_COIN")
        state = board(muk)
        new, events, draws = run(state, UseAttack(0, 0), H)
        self.assertEqual([e["source"] for e in events if e["kind"] == "coin_flip"], ["attack"])
        self.assertEqual((damage_to(events, state, 1), applied(events, state.players[1].active.pokemon_id)), ([30], ["poison"]))

    def test_the_power_works_again_after_the_muk_is_knocked_out(self):
        """ベトベトンが場をはなれたら、また、はたらく（T15。v0.8 の G26）。"""
        state = board(self.rattata, {**self.muk, "damage": 60}, bench1=[haunter()])
        ghost = state.players[1].bench[0].pokemon_id
        self.assertIsNone(working_evasion_power(state, ghost))
        new = apply_command(state, UseAttack(0, 0))
        while new.decision is not None:
            options = new.decision.options
            choice = ghost if ghost in options else options[0]
            new = apply_command(new, ResolveDecision(new.decision.player, new.decision.id, (choice,)))
        self.assertEqual(new.players[1].active.pokemon_id, ghost)
        self.assertEqual(working_evasion_power(new, ghost), TRANSPARENCY)
        mine = apply_command(new, EndTurn(1))
        hit, events, draws = run(mine, UseAttack(0, 0), H)
        self.assertEqual((draws, len(power_coins(events))), (1, 1))


# 「ダメージ → ワザを使う側のコイン → 相手を特殊状態にする」ワザ（T19b。UNRESOLVED_EVADED_EFFECT_COIN）
EFFECT_COIN_TYPES = (PoisonOnHeads, ParalyzeOnHeads, ConfuseOnHeads)
EVOLUTIONS = {METAPOD: (CATERPIE,), KAKUNA: (WEEDLE,), DEWGONG: (SEEL,), STARMIE: (STARYU,), **EVOLVED_FROM,  # v0.28: スターミー
              "PMCG1-034": ("PMCG1-031",), "PMCG2-011": ("PMCG2-005",),  # v0.32: ギャラドス（コイキングから）・ウツドン（マダツボミから）
              "PMCG3-016": ("PMCG4-019",),  # v0.33: 化石の秘密のゴルダック（第4弾のコダックから）
              "PMCG1-039": ("PMCG1-036",), "PMCG3-006": ("PMCG1-006",),  # v0.39: 第1弾のレアコイル（コイルから）・化石の秘密のマタドガス（ドガースから）
              "PMCG6-014": ("PMCG6-005",),  # v0.40: キョウのゴルバット（キョウのズバットから）
              "PMCG4-048": ("PMCG2-036",),  # v0.41: わるいペルシアン（ニャースから）
              "PMCG3-028": ("PMCG3-027",),  # v0.42: ヤドラン（化石の秘密のヤドンから）
              "PMCG5-050": ("PMCG5-043",),  # v0.60: タケシのサンドパン（タケシのサンドから）
              # v0.70: 拡張パック以外の商品の進化カード（ニョロゾ・カスミのスターミー・カメール・モココ・エーフィ）
              "ES1-017": ("ES1-016",), "QSG-015": ("QSG-014",), "GD2-014": ("GD2-013",), "IP2-003": ("IP2-016",), "NIP2-026": ("NIP2-018",),
              "PF2-004": ("ES1-032",)}


class EvadedEffectCoinTest(unittest.TestCase):
    """T19b（UNRESOLVED）: 「とうめい」がはたらいているゴーストに、ダメージ（0 より大きい）→ ワザのコイン → 特殊状態のワザを使うと、
    ワザの宣言の前（こんらんのコインの前）に止める。状態・乱数・ログは変わらない。"""

    def keys(self):
        # v0.69 の拡張パック以外の商品の同じカードの新しい id（tests/helpers.py の V0_69_CARDS）は元のカードと同じ登録なので数えない
        # （同じ登録であることは tests/test_equivalent_non_pack_cards_v0_69.py が確かめる）
        return sorted((k for k in DEFAULT_EFFECTS.attack_keys() if isinstance(DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect,
                                                                                EFFECT_COIN_TYPES) and k.card_id not in V0_69_CARDS), key=str)

    def test_every_registered_attack_stops_before_any_coin(self):
        keys = self.keys()
        names = sorted(DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).name_ja for k in keys)
        self.assertEqual(names, sorted(["どくばり", "いとをはく", "しびれごな", "あわ", "れいとうビーム", "ねんりき", "あやしいひかり", "あやしいひかり",
                                        "どくのこな", "どくばり", "ヘドロこうげき", "したでなめる",
                                        "しめつける",  # v0.17a: モンジャラの「しめつける」（ParalyzeOnHeads）
                                        # v0.28: ラプラス・スリープの「あやしいひかり」（ConfuseOnHeads）、スターミーの「スターフリーズ」・カイロスの
                                        # 「まんりきばさみ」（ParalyzeOnHeads）。既存の型の登録だけなので、同じ T19b で止まる
                                        "あやしいひかり", "あやしいひかり", "スターフリーズ", "まんりきばさみ",
                                        # v0.29: アーボの「どくばり」・ドガースの「どくガス」・タケシのズバットの「どくのきば」（PoisonOnHeads）、ミニリュウの
                                        # 「まきつく」・マチスのコイルの「でんきショック」（ParalyzeOnHeads）。既存の型の登録だけなので、同じ T19b で止まる
                                        "どくばり", "どくガス", "どくのきば", "まきつく", "でんきショック",
                                        # v0.31: カツラのロコンの「しっぽでまどわす」（ConfuseOnHeads。既存の型の登録だけなので、同じ T19b で止まる）
                                        "しっぽでまどわす",
                                        # v0.32: 第2弾のナゾノクサ・コンパンの「しびれごな」・ギャラドスの「バブルこうせん」（ParalyzeOnHeads）、ウツドンの「どくのこな」
                                        # （PoisonOnHeads）。既存の型の登録だけなので、同じ T19b で止まる
                                        "しびれごな", "しびれごな", "バブルこうせん", "どくのこな",
                                        # v0.33: 化石の秘密のゴルダックの「ねんりき」（ParalyzeOnHeads）・マチスのコイル（PMCG5-039）の「こんらんでんぱ」
                                        # （ConfuseOnHeads）。既存の型の登録だけなので、同じ T19b で止まる（はかいでんぱ・はかいビームの T19b は
                                        # tests/test_cd4_opponent_energy_coins_v0_33.py）
                                        "ねんりき", "こんらんでんぱ",
                                        # v0.34: エレブー（PMCG1-041）の「でんきショック」（ParalyzeOnHeads。既存の型の登録だけなので、同じ T19b で止まる。
                                        # docs/barrier-resume-coin-bonus-v0.34.md）
                                        "でんきショック",
                                        # v0.36: ブーバー（化石の秘密。PMCG3-008）の「スモッグ」（PoisonOnHeads。既存の型の登録だけなので、同じ T19b で止まる。
                                        # docs/sand-attack-retreat-lock-v0.36.md）
                                        "スモッグ",
                                        # v0.37: 化石の秘密のベトベターの「ベトベト」・化石の秘密のアーボの「まきつく」（ParalyzeOnHeads。既存の型の登録だけなので、
                                        # 同じ T19b で止まる。docs/fifteen-reused-effects-v0.37.md）
                                        "ベトベト", "まきつく",
                                        # v0.38: フリーザーの「フリーズドライ」・サカキのニドリーナの「のしかかり」・ケーシィ（ロケット団）の「ねんりき」
                                        # （ParalyzeOnHeads。既存の型の登録だけなので、同じ T19b で止まる。docs/bench-switch-combined-v0.38.md）
                                        "フリーズドライ", "のしかかり", "ねんりき",
                                        # v0.39: 第1弾のコイル・レアコイルの「でんじは」（ParalyzeOnHeads）・化石の秘密のマタドガスの「スモッグ」（PoisonOnHeads）。
                                        # 既存の型の登録だけなので、同じ T19b で止まる（docs/selfdestruct-spread-count-v0.39.md）
                                        "でんじは", "でんじは", "スモッグ",
                                        # v0.40: キョウのゴルバットの「ひどいおんぱ」（ConfuseOnHeads。既存の型の登録だけなので、同じ T19b で止まる。
                                        # docs/count-condition-switch-return-v0.40.md）
                                        "ひどいおんぱ",
                                        # v0.41: わるいペルシアンの「どくのつめ」（PoisonOnHeads。既存の型の登録だけなので、同じ T19b で止まる。
                                        # docs/heal-counter-status-v0.41.md）
                                        "どくのつめ",
                                        # v0.42: ヤドランの「ねんりき」（ParalyzeOnHeads。既存の型の登録だけなので、同じ T19b で止まる。
                                        # docs/power-decisions-v0.42.md）
                                        "ねんりき",
                                        # v0.46: カビゴン（PMCG2-047）の「のしかかり」（ParalyzeOnHeads。既存の型の登録だけなので、同じ T19b で止まる。
                                        # docs/continuous-powers-v0.46.md）
                                        "のしかかり",
                                        # v0.48: ロケット団のポリゴンの「サイケこうせん」（ConfuseOnHeads。既存の型の登録だけなので、同じ T19b で止まる。
                                        # docs/effective-pokemon-properties-v0.48.md）
                                        "サイケこうせん",
                                        # v0.60: タケシのサンドパンの「とげボール」（PoisonOnHeads。既存の型の登録だけなので、同じ T19b で止まる。
                                        # docs/coins-defense-rebellion-v0.60.md）
                                        "とげボール",
                                        # v0.61: わるいギャラドスの「れいとうビーム」（ParalyzeOnHeads。既存の型の登録だけなので、同じ T19b で止まる。
                                        # docs/reactive-powers-trainer-damage-v0.61.md）
                                        "れいとうビーム",
                                        # v0.62: ベロリンガの「まきつくベロ」（ParalyzeOnHeads。既存の型の登録だけ。docs/history-attacks-v0.62.md）
                                        "まきつくベロ",
                                        # v0.70: 拡張パック以外の商品のポケモン 82 枚のうち、ParalyzeOnHeads・PoisonOnHeads・ConfuseOnHeads のワザ 24（既存の型の登録だけなので、同じ
                                        # T19b で止まる。docs/non-pack-effect-reuse-v0.70.md）。サワムラー（ES2-026）の「まわしげり」はゴースト（抵抗力 闘）への最終ダメージが 0
                                        "あやしいおんぱ", "あわ", "のしかかり", "あわ", "れいとうパンチ", "まわしげり", "バブルこうせん", "でんきしっぽ", "どくのしる",
                                        "でんきショック", "どくガス", "こんらんガス", "あわ", "スモッグ", "どくばり", "でんきショック", "あやしいひかり", "サイケこうせん",
                                        "れいとうパンチ", "あわ", "のしかかり", "れいとうパンチ", "のしかかり", "おおごえでなく",
                                        # v0.72: 拡張パック以外の商品のポケモン 43 枚のうち、PoisonOnHeads・ParalyzeOnHeads のワザ 7（既存の型の登録だけなので、同じ T19b で止まる。
                                        # docs/status-coins-effect-reuse-v0.72.md）。イワーク（ES2-024・QSG-037）の「しめつける」はゴースト（抵抗力 闘）への最終ダメージが 0
                                        "どくばり", "どくばり", "でんきショック", "でんきショック", "しめつける", "しめつける", "しびれごな",
                                        # v0.75: カツラのガーディ（GD5-006）の「のしかかり」（ParalyzeOnHeads。既存の型の登録だけなので、同じ T19b で止まる。
                                        # docs/search-energy-pokemon-v0.75.md）
                                        "のしかかり",
                                        # v0.76: マリル（PRN-028）の「とびのる」・パウワウ（ES2-006・QSG-017）の「れいとうビーム」・ピカチュウ（IP1-040）の「でんきショック」
                                        # （ParalyzeOnHeads）・コンパン（ES3-004）の「サイケこうせん」（ConfuseOnHeads）。既存の型の登録だけなので、同じ T19b で止まる
                                        # （docs/persistent-attack-modifiers-v0.76.md）
                                        "とびのる", "れいとうビーム", "れいとうビーム", "でんきショック", "サイケこうせん",
                                        # v0.77: neo 期の拡張パックのポケモンの「しびれごな」「へびにらみ」「バブルこうせん」「こおらせる」「ねんりき」（ParalyzeOnHeads）・
                                        # 「サイケこうせん」「つのでまどわす」「ふしぎなこな」（ConfuseOnHeads）・「どくばり」2（PoisonOnHeads）。既存の型の登録だけなので、
                                        # 同じ T19b で止まる（docs/neo-existing-effects-v0.77.md）
                                        "しびれごな", "へびにらみ", "バブルこうせん", "こおらせる", "ねんりき", "サイケこうせん", "つのでまどわす", "ふしぎなこな",
                                        "どくばり", "どくばり"]))
        for key in keys:
            for confused in (False, True):
                attacker = {"card": key.card_id, "energy": energy_for(key.card_id, key.attack_index), **({"confusion": True} if confused else {})}
                if key.card_id in EVOLUTIONS:
                    attacker["evolved_from"] = list(EVOLUTIONS[key.card_id])
                state = board(attacker)
                before, fingerprint, log = written(state), rng_fingerprint(state.rng), state.log
                with self.subTest(key=str(key), confused=confused):
                    if key.card_id == MUK and not confused:
                        # ベトベトン自身のかがくへんかガスで「とうめい」の力が消えている（T14）ので止めない（ChemicalGasTest）
                        self.assertIsNone(working_evasion_power(state, state.players[1].active.pokemon_id))
                        self.assertEqual(power_coins(apply_command(state, UseAttack(0, key.attack_index)).log), [])
                        continue
                    if key.card_id in ("PMCG5-050", "ES2-026", "ES2-024", "QSG-037", "neo1-052"):  # v0.72: イワークの「しめつける」10 も最終ダメージが 0。v0.77: グライガー（闘）の「どくばり」10 も
                        # v0.60: タケシのサンドパン（闘）の「とげボール」30 は、ゴースト（抵抗力 闘 -30）への最終ダメージが 0 なので「ダメージを受けなかった」（T21）。
                        # 「とうめい」はダメージの要素ではたらかず、受けないと決まっていないので、そのあとのどくのコインを投げる（T19b に当たらない。「おもて」なら、
                        # どくの要素を受ける前に「とうめい」のコインを投げる）。v0.70: サワムラー（闘）の「まわしげり」30 も同じ（マヒのコイン）
                        after = apply_command(state, UseAttack(0, key.attack_index))
                        self.assertTrue(any(e["kind"] == "damage" and e["amount"] == 0 for e in after.log[len(state.log):]))
                        continue
                    with self.assertRaises(UnsupportedError) as ctx:
                        apply_command(state, UseAttack(0, key.attack_index))
                    self.assertEqual(ctx.exception.code, "UNRESOLVED_EVADED_EFFECT_COIN")
                    self.assertEqual((written(state), rng_fingerprint(state.rng)), (before, fingerprint))
                    self.assertIs(state.log, log)


class CoinIndependenceTest(unittest.TestCase):
    """相手の対戦ポケモンがゴーストのとき、受け付けるか・拒否のコードが、コインの結果（こんらん 1 枚 + ワザ 2 枚まで + 「とうめい」1 枚の
    16 通り）で変わらない（v0.3d の CoinIndependenceTest と同じ確かめ方。tests/test_effect_preflight_v0_3d.py）。止めるのは T19b の
    場合だけで、その条件をエンジンとは別に求めて比べる。"""

    def test_acceptance_does_not_depend_on_the_coins(self):
        coins = list(itertools.product((H, T), repeat=4))
        defender_states = [{}, {"poison": 10}, {"sleep": True}, {"confusion": True}, {"defender": True}, {"damage": 40}]
        checked = stopped = 0
        for (card, index), confused, defender_state, gas in itertools.product(ATTACKS, (False, True), defender_states, (False, True)):
            turn = 5 + 2 * len(EVOLVED_FROM.get(card, ()))  # ゴーストが進化した番（相手の 4 番）がある盤面
            attacker = {"card": card, "energy": energy_for(card, index), **({"confusion": True} if confused else {})}
            if card in EVOLVED_FROM:
                attacker["evolved_from"] = list(EVOLVED_FROM[card])
            spec = dict(defender_state)
            if spec.pop("defender", False):
                spec["trainers"] = [(DEFENDER, turn)]
            defender = haunter(**spec)
            state = build_test_state([
                {"active": attacker, "bench": [{"card": MUK, "evolved_from": GRIMER}] if gas else [PONYTA]},
                {"active": defender, "bench": [RATTATA]},
            ], turn_number=turn)
            results = set()
            for sides in coins:
                try:
                    new = apply_command(with_coin_results(state, *sides), UseAttack(0, index))
                    self.assertEqual(check_invariants(new), [])
                    results.add("accepted")
                except EngineError as error:
                    results.add(error.code)
            effect = DEFAULT_EFFECTS.attack_entry(card, index).effect
            definition = load_card_pool().get(card)
            final = (definition.attacks[index].damage or 0) - (20 if defender_state.get("defender") else 0)
            # かがくへんかガス: ベンチのベトベトン・ワザを使うベトベトン（こんらんでなければ）。ゴーストのねむり・こんらん（T9〜T14）
            gassed = gas or (card == MUK and not confused)
            working = not gassed and not ({"sleep", "confusion"} & set(defender_state))
            expected = "UNRESOLVED_EVADED_EFFECT_COIN" if isinstance(effect, EFFECT_COIN_TYPES) and working and final > 0 else "accepted"
            if isinstance(effect, DamageAndSelfSleep) and (working or final <= 0):
                # v0.17b（Z23）: たおれこむのダメージが「とうめい」で受けない（コインのどれかの結果）・ディフェンダーで 0 なら、自分をねむりにするかが
                # 決まらないので宣言の前に止める（docs/rocket-snorlax-v0.17b.md 5 章）
                expected = "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE"
            with self.subTest(card=card, index=index, confused=confused, defender=defender_state, gas=gas):
                self.assertEqual(results, {expected})
            stopped += expected != "accepted"
            checked += 1
        self.assertEqual(checked, len(ATTACKS) * 2 * len(defender_states) * 2)
        self.assertGreater(stopped, 0)


class AtomicityTest(unittest.TestCase):
    """拒否と、処理の途中の内部の誤り（注入した）では、渡した状態・乱数・ログは変わらない（``apply_command`` は複製して処理する）。
    受け付けた処理は、自動的にはたらく特殊能力のコインを正しく消費する。"""

    def assert_unchanged(self, state, command, error_type, *patches, apply=apply_command):
        before, fingerprint, log = written(state), rng_fingerprint(state.rng), state.log
        with contextlib_exit(patches):
            with self.assertRaises(error_type) as ctx:
                apply(state, command)
        if patches:  # 注入した誤りそのものが出たこと（差しかえた所を処理が通った。v0.16d: ほかの誤りで通らないように確かめる）
            self.assertIn("注入した誤り", str(ctx.exception))
        self.assertEqual((written(state), rng_fingerprint(state.rng)), (before, fingerprint))
        self.assertIs(state.log, log)

    def test_internal_error_after_the_power_coin(self):
        """「とうめい」のコインを投げたあとの処理（ねむりにする・入れ替えの決定・ダメージのログ）で内部の誤りが起きても、渡した状態は
        変わらない。

        v0.16b: v0.13 の経路を外したので、解決の基盤の同じ所（特殊状態を付ける ``programs.APPLY_CONDITION``・決定を出す
        ``codec.push_decision``・ログ ``attack_evaded``）に誤りを注入する（v0.15 までは v0.13 の経路の ``effects.put_to_sleep``・
        ``effects.push_attack_decision``）。"""
        def boom(*args, **kwargs):
            raise RuntimeError("注入した誤り")

        nightmare = with_coin_results(board(haunter(energy=[PSYCHIC, PSYCHIC])), T)
        self.assert_unchanged(nightmare, UseAttack(0, 0), RuntimeError, mock.patch.dict(programs.APPLY_CONDITION, {SLEEP: boom}))
        whirlwind = with_coin_results(board({"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}), T)
        self.assert_unchanged(whirlwind, UseAttack(0, 0), RuntimeError, mock.patch.object(codec, "push_decision", boom))
        heads = with_coin_results(board({"card": RATTATA, "energy": [FIRE]}), H)
        original = type(heads).add_event

        def add_event(self, kind, **data):
            if kind == "attack_evaded":
                raise RuntimeError("注入した誤り")
            return original(self, kind, **data)

        self.assert_unchanged(heads, UseAttack(0, 0), RuntimeError, mock.patch.object(type(heads), "add_event", add_event))

    def test_accepted_command_does_not_change_the_input(self):
        state = with_coin_results(board({"card": RATTATA, "energy": [FIRE]}), H)
        before, fingerprint, log = written(state), rng_fingerprint(state.rng), state.log
        new = apply_command(state, UseAttack(0, 0))
        self.assertEqual((written(state), rng_fingerprint(state.rng)), (before, fingerprint))
        self.assertIs(state.log, log)
        self.assertEqual(rng_draws(state, new), 1)


class contextlib_exit:
    """テスト専用: いくつかの ``mock.patch`` をまとめて使う。"""

    def __init__(self, patches):
        self.patches = patches

    def __enter__(self):
        for patch in self.patches:
            patch.__enter__()

    def __exit__(self, *exc):
        for patch in reversed(self.patches):
            patch.__exit__(*exc)
        return False


class SaveRestoreTest(unittest.TestCase):
    """保存（pickle・deepcopy・形式 9 の書き出し）と復元のあとも同じに進む。「とうめい」の記録（``AttackUse.reception``）は状態に
    持たないので、書き出しの形式は 9 のまま（形式 10 を加えていない）。"""

    def test_restored_state_gives_the_same_result(self):
        state = with_coin_results(board({"card": IVYSAUR, "evolved_from": BULBASAUR, "energy": [GRASS] * 3}), H)
        for restored in (pickle.loads(pickle.dumps(state)), copy.deepcopy(state)):
            a, b = apply_command(state, UseAttack(0, 1)), apply_command(restored, UseAttack(0, 1))
            self.assertEqual(written(a), written(b))
            self.assertEqual(a.log, b.log)

    def test_restored_decision_resumes_without_another_coin(self):
        """「ふきとばし」の「うら」で決定を待つ状態を保存・復元して答えても、コインを投げ直さない（受けると決まってから決定を出すので、
        決定の続きに記録は要らない）。"""
        state = with_coin_results(board({"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}), T)
        waiting = apply_command(state, UseAttack(0, 0))
        data = written(waiting)
        self.assertNotIn("reception", repr(data))
        self.assertEqual(data["decision"]["kind"], "forced_switch")
        for restored in (waiting, pickle.loads(pickle.dumps(waiting)), copy.deepcopy(waiting)):
            done = apply_command(restored, ResolveDecision(1, restored.decision.id, (restored.decision.options[0],)))
            self.assertEqual(rng_fingerprint(done.rng), rng_fingerprint(waiting.rng))
            self.assertEqual(written(done), written(apply_command(waiting, ResolveDecision(1, waiting.decision.id,
                                                                                            (waiting.decision.options[0],)))))
        with self.assertRaises(ValueError):
            state_to_dict(waiting, format_version=1)  # ワザの途中の決定は形式 1 で書き出せない（v0.4d）


if __name__ == "__main__":
    unittest.main()

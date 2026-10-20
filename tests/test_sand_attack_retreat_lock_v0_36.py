"""v0.36: p.309 の手順 4 のコイン（すなかけ・えんまくなど）・「にげる」ことができない効果・自分を山札にもどす効果と、11 枚
（docs/sand-attack-retreat-lock-v0.36.md）。

共通の処理の境界（``AttackCheckTest``・``RetreatLockTest``・``DeckReturnTest``）と、カードごとの処理（``ExistingEffectTest``）と、まねるワザ
（``CopyTest``）と、不変条件・書き出し（``IntegrityTest``）と、カードごとの登録の確かめ（``CardDataTest``）と、すべてのワザの先読みの方法ごとの一致
（``PreflightParityTest``）に分けた。

根拠はどれも kyuura データの採用（kyuura の印刷の文面。``card_sources.json``）と、既存の記録の再利用: p.309 のワザを使う手順 1〜6（手順 4「ワザを
失敗させたりワザの内容を変えてしまう効果」→ 手順 5 こんらん。docs/confusion-v0.3c.md 1 章の引用）、p.323「12 ワザの失敗」、p.322・p.323 の持続する効果の
消える契機（docs/persistent-effects-v0.4b.md）、p.311 のにげるの手順、p.325「「にげる」がおこなえない状態のポケモンでも、「そのポケモンを入れ替える」と
指示されたときは、入れ替えをおこないます」、p.311・p.313・p.323 のバトル場に出す・勝ち負け、v0.17b の Z23、v0.13 の CR-SHELL-ATTACK-KO-ATTACKER-OWN-EFFECTS。
ガイドブックは読んでいない。
"""

from __future__ import annotations

import copy
import pathlib
import pickle
import unittest
from collections import Counter

from kyuura_engine import (
    EndTurn,
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UseAttack,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, read_extract
from kyuura_engine.persistent import attack_coin_checks, cannot_retreat
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import AttackCoinCheck, CannotRetreat
from scripts import check_card_sources as cs
from scripts.extract_kyuura_cards import PREVIOUS_KYUURA_COMMIT as ADOPTED_COMMIT  # v0.69: 採用したときのデータのコミット（採用の記録は書き換えない）
from tests.helpers import (
    kyuura_records_since_v0_69,
    CLEFABLE,
    CLEFAIRY,
    DARK_JOLTEON,
    DEFENDER,
    DODUO,
    EEVEE,
    ERIKAS_BELLSPROUT,
    EXEGGCUTE,
    EXEGGUTOR,
    FIGHTING,
    FIRE,
    FOSSIL_MAGMAR,
    GRASS,
    HITMONCHAN,
    HORSEA,
    KOGAS_KOFFING,
    KOGAS_PIDGEY,
    LIGHTNING,
    LT_SURGES_FEAROW,
    LT_SURGES_SPEAROW,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MAGMAR,
    METAPOD,
    MISTYS_HORSEA,
    MISTYS_SEEL,
    PLUSPOWER,
    PSYCHIC,
    RATTATA,
    SANDSHREW,
    SANDSLASH,
    SWITCH,
    V0_36_POKEMON,
    WATER,
    CATERPIE,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import serialization_problems
from tests.test_barrier_resume_coin_bonus_v0_34 import assert_stops, coins, events, full, kinds, play, with_barrier

ROOT = pathlib.Path(__file__).resolve().parent.parent
TURN = 7
DOC = ROOT / "docs" / "sand-attack-retreat-lock-v0.36.md"
BELOW = {SANDSLASH: SANDSHREW, DARK_JOLTEON: EEVEE, LT_SURGES_FEAROW: LT_SURGES_SPEAROW, CLEFABLE: CLEFAIRY, MACHAMP: [MACHOP, MACHOKE],
         METAPOD: CATERPIE, EXEGGUTOR: EXEGGCUTE}
# 手順 4 のコインの効果を与えるワザ（カード id, ワザの位置）と、「効果は1回できえる」か
ATTACK_CHECKS = {(SANDSHREW, 0): True, (FOSSIL_MAGMAR, 0): False, (HORSEA, 0): False, (MISTYS_HORSEA, 1): False, (KOGAS_PIDGEY, 1): False,
                 (DARK_JOLTEON, 0): False, (MISTYS_SEEL, 1): False, (KOGAS_KOFFING, 0): False}
RETREAT_LOCKS = ((MISTYS_SEEL, 0), (LT_SURGES_FEAROW, 1))
# ワザを使うのに足りるエネルギー
ENERGY = {SANDSHREW: (FIGHTING,), SANDSLASH: (FIGHTING, FIGHTING), FOSSIL_MAGMAR: (FIRE, FIRE), HORSEA: (WATER,), MISTYS_HORSEA: (WATER, WATER),
          KOGAS_PIDGEY: (WATER, WATER, WATER), DARK_JOLTEON: (LIGHTNING, LIGHTNING, LIGHTNING), MISTYS_SEEL: (WATER, WATER),
          LT_SURGES_FEAROW: (WATER, WATER, WATER), KOGAS_KOFFING: (GRASS, GRASS), ERIKAS_BELLSPROUT: (GRASS,)}
# 登録の実装の型（カード id, ワザの位置）
EXPECTED = {
    (SANDSHREW, 0): (E.DamageThenAttackCoinCheck, {"single_use": True}),
    (SANDSLASH, 0): (E.DamageOnly, {}),
    (SANDSLASH, 1): (E.CoinFlipDamage, {"coins": 3, "damage_per_heads": 20}),
    (FOSSIL_MAGMAR, 0): (E.DamageThenAttackCoinCheck, {"single_use": False}),
    (FOSSIL_MAGMAR, 1): (E.PoisonOnHeads, {}),
    (HORSEA, 0): (E.DamageThenAttackCoinCheck, {"single_use": False}),
    (MISTYS_HORSEA, 0): (E.DamageOnly, {}),
    (MISTYS_HORSEA, 1): (E.DamageThenAttackCoinCheck, {"single_use": False}),
    (KOGAS_PIDGEY, 0): (E.DamageOnly, {}),
    (KOGAS_PIDGEY, 1): (E.DamageThenAttackCoinCheck, {"single_use": False}),
    (DARK_JOLTEON, 0): (E.DamageThenAttackCoinCheck, {"single_use": False}),
    (DARK_JOLTEON, 1): (E.DamageThenParalyzeOrSelfDamage, {"self_damage": 10}),
    (MISTYS_SEEL, 0): (E.DamageThenRetreatLock, {}),
    (MISTYS_SEEL, 1): (E.DamageThenAttackCoinCheck, {"single_use": False}),
    (LT_SURGES_FEAROW, 0): (E.CoinFlipDamage, {"coins": 5, "damage_per_heads": 10}),
    (LT_SURGES_FEAROW, 1): (E.DamageThenRetreatLock, {}),
    (KOGAS_KOFFING, 0): (E.DamageThenAttackCoinCheck, {"single_use": False}),
    (KOGAS_KOFFING, 1): (E.DamageThenReturnSelfToDeckOnHeads, {}),
    (ERIKAS_BELLSPROUT, 0): (E.DamageAndSelfDamage, {"self_damage": 10}),
}
# pcg-search.com の対象の版（サイトの一覧の番号）
EDITIONS = {SANDSHREW: "051/096", SANDSLASH: "034/048", FOSSIL_MAGMAR: "008/048", HORSEA: "018/048", MISTYS_HORSEA: "029/096", KOGAS_PIDGEY: "065/098",
            DARK_JOLTEON: "030/065", MISTYS_SEEL: "027/096", LT_SURGES_FEAROW: "060/096", KOGAS_KOFFING: "015/098", ERIKAS_BELLSPROUT: "011/096"}


def mon(card, energy=None, **extra):
    spec = {"card": card, "energy": list(ENERGY.get(card, ()) if energy is None else energy), **extra}
    if BELOW.get(card) is not None and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), hand=(), opponent_hand=(), turn=TURN):
    me = {"active": active, "bench": list(bench), "hand": list(hand)}
    them = {"active": opponent or mon(HITMONCHAN, (FIGHTING, FIGHTING)), "bench": list(opponent_bench), "hand": list(opponent_hand)}
    return build_test_state([me, them], turn_number=turn)


def snapshot(state):
    return full(state), rng_fingerprint(state.rng), [dict(e) for e in state.log]


def given(attack=(SANDSHREW, 0), opponent=None, *, sides=(), **kw):
    """プレイヤー 0 の ``attack`` で、プレイヤー 1 の対戦ポケモンに効果を与えたあと、プレイヤー 1 の番（TURN + 1）にする。(与える前, 与えたあと)。
    ``sides`` はそのあいだに投げるコイン（ポケモンチェックのねむりなど）の結果。"""
    state = board(mon(attack[0]), opponent, **kw)
    return state, play(with_coin_results(state, *sides) if sides else state, UseAttack(0, attack[1]))


def in_hand(state, player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)


def retreat(state, player):
    """``player`` のバトル場のポケモンの「にげる」（にげるエネルギーの数ぶん、ついている順にトラッシュし、ベンチの最初と入れ替える）。"""
    active = state.players[player].active
    cost = state.card_def(active.card).retreat_cost
    return Retreat(player, tuple(active.energy[:cost]), state.players[player].bench[0].card)


def attack_with(state, player, index, *sides, mode="derived"):
    return apply_kernel(with_coin_results(state, *sides), UseAttack(player, index), preflight=mode)


class AttackCheckTest(unittest.TestCase):
    """p.309 の手順 4 のコイン（``AttackCoinCheck``）。効果を与えるワザの中ではコインを投げず、効果を受けたポケモンがワザを使うときに投げる。"""

    def test_each_attack_gives_the_effect_to_the_defending_pokemon(self):
        """8 つのワザがどれも、ダメージのあとに相手の対戦ポケモンへ効果を与える（はたらく番は次の相手の番。発生源はワザを使ったポケモン）。このワザの中では
        コインを投げない。サンドの「すなかけ」だけが「1回できえる」（説明の文面で登録を確かめた）。"""
        for (card, index), single_use in ATTACK_CHECKS.items():
            with self.subTest(card=card, index=index):
                state, done = given((card, index))
                since = len(state.log)
                [added] = events(done, since, "persistent_effect_added")
                target = state.players[1].active
                self.assertEqual((added["pokemon_id"], added["persistent_effect"], added["active_turn"], added["single_use"], added["source_card"]),
                                 (target.pokemon_id, AttackCoinCheck.kind, TURN + 1, single_use, state.players[0].active.card))
                self.assertEqual(kinds(done, since)[:3], ["attack", "damage", "persistent_effect_added"])
                self.assertEqual(coins(done, since), [])
                [effect] = done.players[1].active.persistent_effects
                self.assertEqual((type(effect), effect.single_use, effect.created_turn), (AttackCoinCheck, single_use, TURN))

    def test_heads_continues_and_tails_fails_the_attack(self):
        """効果を受けたプレイヤーが、ワザの宣言のあと（ログ ``attack`` のすぐあと）にコインを 1 枚投げる（``source: attack_check``）。「おもて」なら
        ワザの内容を処理し、「うら」ならワザは失敗する（``attack_failed`` の reason ``attack_check``。ワザの要素はない。ワザは使ったことになり、
        番は終わる。p.323「12 ワザの失敗」）。"""
        _, done = given((KOGAS_KOFFING, 0))
        since = len(done.log)
        heads = attack_with(done, 1, 0, H)
        self.assertEqual(kinds(heads, since)[:4], ["attack", "coin_flip", "attack_check", "damage"])
        flip = events(heads, since, "coin_flip")[0]
        self.assertEqual((flip["player"], flip["source"], flip["result"]), (1, "attack_check", "heads"))
        tails = attack_with(done, 1, 0, T)
        self.assertEqual(kinds(tails, since)[:4], ["attack", "coin_flip", "attack_check", "attack_failed"])
        self.assertEqual(events(tails, since, "attack_failed")[0]["reason"], "attack_check")
        self.assertEqual(events(tails, since, "damage"), [])
        self.assertEqual((tails.turn_number, tails.current_player), (TURN + 2, 0))  # 番は終わった
        self.assertEqual(tails.players[0].active.damage, done.players[0].active.damage)

    def test_check_comes_before_the_attack_coins(self):
        """手順 4 のコインは、ワザの説明のコイン（ドードーの「みだれづき」2 枚）より先。「うら」ならワザの説明のコインは投げない。"""
        _, done = given((SANDSHREW, 0), mon(DODUO, (FIRE, FIRE)))
        since = len(done.log)
        heads = attack_with(done, 1, 0, H, H, T)
        self.assertEqual([(e["source"], e["result"]) for e in events(heads, since, "coin_flip")],
                         [("attack_check", "heads"), ("attack", "heads"), ("attack", "tails")])
        tails = attack_with(done, 1, 0, T)
        self.assertEqual([e["source"] for e in events(tails, since, "coin_flip")], ["attack_check"])

    def test_single_use_effect_is_removed_by_the_check(self):
        """サンドの「すなかけ」（「「すなかけ」の効果は1回できえる」）は、手順 4 のコインを投げたら（「おもて」でも「うら」でも）消える（理由 ``used``）。
        ほかの文面の効果は、その番の終わりに期限で消える（``expired``）。"""
        _, sand = given((SANDSHREW, 0))
        _, smoke = given((HORSEA, 0))
        for side in (H, T):
            with self.subTest(side=side):
                after = attack_with(sand, 1, 0, side)
                removed = events(after, len(sand.log), "persistent_effect_removed")
                self.assertEqual([e["reason"] for e in removed], ["used"])
                self.assertEqual(kinds(after, len(sand.log))[:4], ["attack", "coin_flip", "attack_check", "persistent_effect_removed"])
                after = attack_with(smoke, 1, 0, side)
                self.assertEqual([e["reason"] for e in events(after, len(smoke.log), "persistent_effect_removed")], ["expired"])

    def test_effect_only_on_the_next_opponent_turn(self):
        """効果を受けたポケモンがその番にワザを使わなければ、コインは投げず、その番の終わりに消える。そのあとの番（次の自分の番を含む）にワザを使っても
        コインはない（「次の番に」「次の相手の番に」）。"""
        for card, index in ((SANDSHREW, 0), (HORSEA, 0)):
            with self.subTest(card=card):
                _, done = given((card, index))
                passed = apply_kernel(done, EndTurn(1))
                self.assertEqual([e["reason"] for e in events(passed, len(done.log), "persistent_effect_removed")], ["expired"])
                self.assertEqual(coins(passed, len(done.log)), [])
                back = apply_kernel(passed, EndTurn(0))
                later = attack_with(back, 1, 0)
                self.assertEqual([e for e in events(later, len(back.log), "coin_flip") if e["source"] == "attack_check"], [])

    def test_rejected_declarations_do_not_flip(self):
        """宣言できないワザ（エネルギー不足・ねむり・マヒ）は、手順 4 の前に拒否する（コイン・状態・乱数・ログは変わらない）。"""
        _, done = given((HORSEA, 0))
        before = snapshot(done)
        with self.assertRaises(IllegalActionError) as raised:
            apply_kernel(done, UseAttack(1, 1))  # スペシャルパンチ（闘闘無）。エネルギー不足
        self.assertEqual(raised.exception.code, "INSUFFICIENT_ENERGY")
        self.assertEqual(snapshot(done), before)
        for condition, code in (({"sleep": True}, "POKEMON_ASLEEP"), ({"paralysis": TURN}, "POKEMON_PARALYZED")):
            with self.subTest(code=code):
                _, held = given((HORSEA, 0), mon(HITMONCHAN, (FIGHTING, FIGHTING), **condition), sides=(T,))  # ねむりのコイン「うら」（さめない）
                before = snapshot(held)
                with self.assertRaises(IllegalActionError) as raised:
                    apply_kernel(held, UseAttack(1, 0))
                self.assertEqual(raised.exception.code, code)
                self.assertEqual(snapshot(held), before)

    def test_confused_pokemon_stops_before_the_coin(self):
        """こんらん状態のポケモンが効果を受けてワザを使うとき、手順 4 で失敗したあとに手順 5 のこんらんのコインをするかは決められない（AC6）ので、どの
        先読みの方法でも、手順 4 のコインの前に ``UNRESOLVED_ATTACK_CHECK_CONFUSION`` で止める（状態・乱数・ログは変わらない）。"""
        _, done = given((HORSEA, 0), mon(HITMONCHAN, (FIGHTING, FIGHTING), confusion=True))
        assert_stops(self, done, UseAttack(1, 0), "UNRESOLVED_ATTACK_CHECK_CONFUSION")

    def test_question_in_the_heads_branch_stops_before_the_declaration(self):
        """「おもて」の先のワザの内容で原典で決められない場合に当たるなら、「うら」ならワザが失敗するだけでも、宣言の前に止める（受け付けるかが手順 4 の
        コインの結果で変わらない）。えんまくを受けたキョウのドガースの「くもがくれガス」で、相手の対戦ポケモンが HP 以上になる（RD9）。"""
        state = board(mon(HORSEA, damage=20), mon(KOGAS_KOFFING, (GRASS, GRASS)))
        smoked = play(state, UseAttack(0, 0))
        self.assertTrue(attack_coin_checks(smoked, smoked.players[1].active))
        assert_stops(self, smoked, UseAttack(1, 1), "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT")

    def test_effect_is_removed_by_switch_retreat_and_evolution(self):
        """効果を受けたポケモンがベンチにもどる（ポケモンいれかえ・にげる）・進化すると消える（p.311・p.322・p.323）。そのあとワザを使ってもコインはない。"""
        _, done = given((HORSEA, 0), hand=(), opponent_hand=(SWITCH,))
        switched = apply_kernel(done, PlayTrainer(1, done.players[1].hand[0]), )
        if switched.decision is not None:
            switched = apply_kernel(switched, ResolveDecision(1, switched.decision.id, (switched.decision.options[0],)))
        self.assertEqual([e["reason"] for e in events(switched, len(done.log), "persistent_effect_removed")], ["switch"])
        _, done = given((HORSEA, 0))
        retreated = apply_kernel(done, retreat(done, 1))
        self.assertEqual([e["reason"] for e in events(retreated, len(done.log), "persistent_effect_removed")], ["retreat"])
        _, done = given((HORSEA, 0), mon(EEVEE, (LIGHTNING,)), opponent_hand=(DARK_JOLTEON,))
        evolved = apply_kernel(done, EvolvePokemon(1, in_hand(done, 1, DARK_JOLTEON), done.players[1].active.pokemon_id))
        self.assertEqual([e["reason"] for e in events(evolved, len(done.log), "persistent_effect_removed")], ["evolve"])
        after = attack_with(evolved, 1, 0)
        self.assertEqual([e for e in events(after, len(evolved.log), "coin_flip") if e["source"] == "attack_check"], [])

    def test_effect_stays_when_the_giver_leaves_play(self):
        """効果を与えたポケモンがきぜつしても、効果は消えない（p.322「与えたポケモンが場をはなれても消えない」）。「おもて」でワザが成功してタッツーを
        きぜつさせたあと、サイドを取る決定を待つ間も、効果を受けたポケモンは効果を持つ。"""
        horsea = board(mon(HORSEA, damage=30), mon(HITMONCHAN, (FIGHTING, FIGHTING)))
        smoked = play(horsea, UseAttack(0, 0))
        knocked = attack_with(smoked, 1, 0, H)
        self.assertEqual(knocked.decision.kind, "take_prize")  # このあと相手がバトル場に出す
        self.assertEqual([type(e) for e in knocked.players[1].active.persistent_effects], [AttackCoinCheck])
        self.assertEqual(check_invariants(knocked), [])

    def test_effect_is_removed_when_the_pokemon_is_knocked_out(self):
        """効果を受けたポケモンが、はたらく番にきぜつすると消える（理由 ``knock_out``。p.322「場をはなれたら」）。「おもて」で成功したエリカのマダツボミの
        「へなへなタックル」の自分への 10 で、えんまくの 10 を受けてダメージ 40 になったマダツボミ（HP 50）がきぜつする。"""
        _, done = given((HORSEA, 0), mon(ERIKAS_BELLSPROUT, damage=30))
        after = attack_with(done, 1, 0, H)
        self.assertEqual([e["reason"] for e in events(after, len(done.log), "persistent_effect_removed")], ["knock_out"])

    def test_effect_still_given_to_a_pokemon_that_takes_no_damage(self):
        """「ダメージを受けない」状態（かたまる）の相手でも、ダメージ以外の効果の要素は有効（p.321。v0.4b の規定）なので、えんまくの効果は与える。"""
        state = board(mon(HORSEA), mon(METAPOD, (GRASS,), prevent_damage=TURN - 1))
        done = play(state, UseAttack(0, 0))
        self.assertEqual(len(events(done, len(state.log), "damage_prevented")), 1)
        self.assertEqual([e["persistent_effect"] for e in events(done, len(state.log), "persistent_effect_added")], [AttackCoinCheck.kind])

    def test_coin_is_not_flipped_again_on_resume(self):
        """手順 4 のコインの「おもて」のあと、ワザの途中の決定（ゆびをふるのワザを選ぶ）で止まり、保存・複製から再開しても、手順 4 のコインを投げ直さない
        （ワザ 1 回につき 1 回。宣言のあとの処理は決定のあとにくり返さない）。"""
        state = board(mon(HORSEA), mon(CLEFAIRY, (PSYCHIC, PSYCHIC, PSYCHIC)))
        smoked = play(state, UseAttack(0, 0))
        waiting = attack_with(smoked, 1, 1, H)
        self.assertEqual(waiting.decision.kind, "select_attack")
        self.assertEqual(len(events(waiting, len(smoked.log), "attack_check")), 1)
        answer = ResolveDecision(1, waiting.decision.id, (waiting.decision.options[0],))
        results = [apply_kernel(s, answer) for s in (waiting, waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting)))]
        self.assertEqual(len({str(snapshot(r)) for r in results}), 1)
        self.assertEqual(len(events(results[0], len(smoked.log), "attack_check")), 1)

    def test_not_given_to_a_knocked_out_or_protected_pokemon(self):
        """相手がこのワザで HP 以上になったら効果を与えない（p.309）。相手が「ワザをうけない」状態（バリアー）なら、効果の要素は無効（ログ
        ``effect_prevented``。v0.31 の既存の処理）。「アイスバーン」も同じ。"""
        state = board(mon(KOGAS_PIDGEY), mon(HITMONCHAN, (FIGHTING, FIGHTING), damage=60))
        done = play(state, UseAttack(0, 1), [lambda d: d.options[:1]])
        self.assertEqual(events(done, len(state.log), "persistent_effect_added"), [])
        self.assertTrue(events(done, len(state.log), "knock_out"))
        for card, index, element in ((HORSEA, 0, "attack_check"), (MISTYS_SEEL, 0, "retreat_lock")):
            with self.subTest(card=card):
                barrier = with_barrier(mon(card))
                done = play(barrier, UseAttack(1, index))
                [prevented] = events(done, len(barrier.log), "effect_prevented")
                self.assertEqual((prevented["element"], prevented["persistent_effect"]), (element, "attack_barrier"))
                self.assertEqual([e["persistent_effect"] for e in events(done, len(barrier.log), "persistent_effect_added")], [])


class RetreatLockTest(unittest.TestCase):
    """「にげる」ことができない効果（``CannotRetreat``。アイスバーン・わしづかみ）。"""

    def test_effect_is_given_and_retreat_is_rejected_before_any_cost(self):
        """2 つのワザがどれも、ダメージのあとに相手の対戦ポケモンへ効果を与える（はたらく番は次の相手の番）。その番の「にげる」は、エネルギーのトラッシュ・
        こんらんのコインの前に ``RETREAT_PREVENTED`` で拒否する（状態・乱数・ログは変わらない）。こんらん状態でも同じ（コインを投げない）。"""
        for card, index in RETREAT_LOCKS:
            for confused in (False, True):
                with self.subTest(card=card, confused=confused):
                    extra = {"confusion": True} if confused else {}
                    state, done = given((card, index), mon(HITMONCHAN, (FIGHTING, FIGHTING), **extra))
                    [added] = events(done, len(state.log), "persistent_effect_added")
                    self.assertEqual((added["persistent_effect"], added["active_turn"]), (CannotRetreat.kind, TURN + 1))
                    before = snapshot(done)
                    with self.assertRaises(IllegalActionError) as raised:
                        apply_kernel(done, retreat(done, 1))
                    self.assertEqual(raised.exception.code, "RETREAT_PREVENTED")
                    self.assertEqual(snapshot(done), before)

    def test_switch_is_not_restricted_and_clears_the_effect(self):
        """ポケモンいれかえ（「にげる」ではない入れ替え）は制限しない（p.325）。ベンチにもどったら効果は消え（``switch``）、そのあとバトル場にもどっても
        にげられる。"""
        _, done = given((MISTYS_SEEL, 0), opponent_hand=(SWITCH,))
        switched = apply_kernel(done, PlayTrainer(1, done.players[1].hand[0]))
        if switched.decision is not None:
            switched = apply_kernel(switched, ResolveDecision(1, switched.decision.id, (switched.decision.options[0],)))
        self.assertEqual([e["reason"] for e in events(switched, len(done.log), "persistent_effect_removed")], ["switch"])
        self.assertIsNone(cannot_retreat(switched, switched.players[1].bench[0]))

    def test_expires_and_evolution_clears(self):
        """効果はその番の終わりに消え、次の番からはにげられる。進化すると消える（p.310・p.323）。効果を与えた番の残り（ワザなので番は終わる）・効果を
        与えたプレイヤーの次の番には、はたらいていない。"""
        _, done = given((MISTYS_SEEL, 0))
        self.assertIsNotNone(cannot_retreat(done, done.players[1].active))
        passed = apply_kernel(apply_kernel(done, EndTurn(1)), EndTurn(0))
        self.assertIsNone(cannot_retreat(passed, passed.players[1].active))
        apply_kernel(passed, retreat(passed, 1))
        _, done = given((MISTYS_SEEL, 0), mon(EEVEE, (LIGHTNING,)), opponent_hand=(DARK_JOLTEON,))
        evolved = apply_kernel(done, EvolvePokemon(1, in_hand(done, 1, DARK_JOLTEON), done.players[1].active.pokemon_id))
        self.assertEqual([e["reason"] for e in events(evolved, len(done.log), "persistent_effect_removed")], ["evolve"])
        apply_kernel(evolved, retreat(evolved, 1))

    def test_attack_switch_is_not_restricted(self):
        """ワザの効果の入れ替え（ナッシーの「テレポート」。「にげる」ではない）は制限しない（p.325）。入れ替えたらベンチにもどったので効果は消える。"""
        _, done = given((MISTYS_SEEL, 0), mon(EXEGGUTOR, (PSYCHIC,)))
        waiting = attack_with(done, 1, 0)
        switched = apply_kernel(waiting, ResolveDecision(1, waiting.decision.id, (waiting.decision.options[0],)))
        self.assertTrue(events(switched, len(done.log), "switch"))
        self.assertIn("switch", [e["reason"] for e in events(switched, len(done.log), "persistent_effect_removed")])

    def test_attacks_are_not_restricted(self):
        """ワザは制限しない（「にげる」ことだけができない）。"""
        _, done = given((LT_SURGES_FEAROW, 1))
        attacked = attack_with(done, 1, 0)
        self.assertTrue(events(attacked, len(done.log), "damage"))


class DeckReturnTest(unittest.TestCase):
    """キョウのドガースの「くもがくれガス」（``ReturnSelfToDeck``）。"""

    def koffing(self, *, opponent=None, bench=(RATTATA,), **extra):
        return board(mon(KOGAS_KOFFING, **extra), opponent or mon(HITMONCHAN, (FIGHTING, FIGHTING)), bench=bench)

    def test_tails_keeps_the_pokemon_in_play(self):
        state = self.koffing()
        done = attack_with(state, 0, 1, T)
        self.assertEqual(kinds(done, len(state.log))[:3], ["attack", "damage", "coin_flip"])
        self.assertEqual(events(done, len(state.log), "return_in_play_to_deck"), [])
        self.assertEqual(done.players[0].active.card, state.players[0].active.card)

    def test_heads_returns_the_pokemon_and_attached_cards_after_damage(self):
        """ダメージ → コイン → 山札にもどす → 山札を切る（説明の順番）。もどすのはポケモンとついているすべてのカード（エネルギー・トレーナー）。ダメージ
        カウンター・特殊状態（どく）・持続する効果はなくなる（場をはなれた。p.322。持続する効果は理由 ``return_in_play_to_deck``）。きぜつではない（サイドは
        取られない・ログ ``knock_out`` はない）。バトル場が空くので、ワザを使ったプレイヤーがベンチから出す決定（p.313）。出したら番が終わる。"""
        state = self.koffing(damage=20, poison=10, trainers=[(PLUSPOWER, TURN), (DEFENDER, TURN + 1)])
        koffing = state.players[0].active
        attached = (koffing.card, *koffing.energy, *(t.card for t in koffing.trainers))
        deck_before = list(state.players[0].deck)
        done = attack_with(state, 0, 1, H)
        since = len(state.log)
        self.assertEqual(kinds(done, since)[:5], ["attack", "damage", "coin_flip", "return_in_play_to_deck", "shuffle"])
        [moved] = events(done, since, "return_in_play_to_deck")
        self.assertEqual((sorted(moved["cards"]), moved["damage"], moved["effect"]), (sorted(attached), 20, f"{KOGAS_KOFFING}#1"))
        self.assertEqual(sorted(done.players[0].deck), sorted(deck_before + list(attached)))
        self.assertEqual(events(done, since, "knock_out"), [])
        self.assertEqual(events(done, since, "take_prize"), [])
        self.assertIsNone(done.players[0].active)
        d = done.decision
        self.assertEqual((d.kind, d.player, d.options), ("promote_active", 0, tuple(p.pokemon_id for p in done.players[0].bench)))
        self.assertIsNone(done.find_pokemon(koffing.pokemon_id))
        promoted = apply_kernel(done, ResolveDecision(0, d.id, (d.options[0],)))
        self.assertEqual((promoted.turn_number, promoted.current_player), (TURN + 1, 1))
        self.assertEqual(promoted.players[0].active.damage, 0)

    def test_persistent_effects_are_removed(self):
        """ワザを使ったポケモンが持っていた持続する効果は、山札にもどったら消える（理由 ``return_in_play_to_deck``。p.322）。"""
        state = board(mon(HORSEA), mon(KOGAS_KOFFING, (GRASS, GRASS)), turn=TURN)
        smoked = play(state, UseAttack(0, 0))  # キョウのドガースが「えんまく」を受ける
        done = attack_with(smoked, 1, 1, H, H)  # 手順 4 のコイン「おもて」→ くもがくれガスのコイン「おもて」
        removed = events(done, len(smoked.log), "persistent_effect_removed")
        self.assertEqual([e["reason"] for e in removed], ["return_in_play_to_deck"])
        self.assertEqual(kinds(done, len(smoked.log)).index("return_in_play_to_deck") + 1,
                         kinds(done, len(smoked.log)).index("persistent_effect_removed"))

    def test_without_bench_the_attacker_loses(self):
        """控えがいなければ、バトル場に出せないので負け（p.311。相手の勝利条件「相手がバトル場にポケモンを出せない」）。"""
        state = self.koffing(bench=())
        done = attack_with(state, 0, 1, H)
        self.assertEqual((done.result.outcome, done.result.winner, done.result.conditions), ("win", 1, ((1, "OPPONENT_CANNOT_FIELD_ACTIVE"),)))

    def test_knockout_in_the_same_attack_stops_before_the_declaration(self):
        """同じワザで相手の対戦ポケモンが HP 以上になりうるなら、バトル場に出す時点ときぜつの処理の順番が決まらない（RD9）ので、コインの結果によらず
        宣言の前に ``UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT`` で止める（どの先読みの方法でも。状態は変わらない）。"""
        assert_stops(self, self.koffing(opponent=mon(HITMONCHAN, (FIGHTING, FIGHTING), damage=50)), UseAttack(0, 1),
                     "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT")
        assert_stops(self, self.koffing(opponent=mon(HITMONCHAN, (FIGHTING, FIGHTING), damage=50), bench=()), UseAttack(0, 1),
                     "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT")

    def test_no_damage_reuses_z23(self):
        """「ダメージを与えた後」の効果で、ダメージを与えなかった（「ダメージを受けない」状態）ときは、v0.17b の Z23 と同じ問い
        （``UNRESOLVED_EFFECT_AFTER_NO_DAMAGE``）で宣言の前に止める（新しいコードにしない）。"""
        state = self.koffing(opponent=mon(METAPOD, (GRASS,), prevent_damage=TURN - 1))
        assert_stops(self, state, UseAttack(0, 1), "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE")

    def test_attacker_knocked_out_by_a_damage_trigger_is_not_returned(self):
        """ワザを使ったポケモンが相手の「はんげき」ですでに HP 以上なら、自分への効果（山札にもどす）は処理しない（コインも投げない。
        CR-SHELL-ATTACK-KO-ATTACKER-OWN-EFFECTS の読み方）。ワザのあとにふつうにきぜつし、相手がサイドを取る。"""
        state = self.koffing(opponent=mon(MACHAMP, (FIGHTING,)), damage=40)
        done = attack_with(state, 0, 1, H)
        since = len(state.log)
        self.assertEqual([e for e in events(done, since, "coin_flip") if e["source"] == "attack"], [])
        self.assertEqual(events(done, since, "return_in_play_to_deck"), [])
        self.assertEqual([e["player"] for e in events(done, since, "knock_out")], [0])

    def test_promotion_decision_owner_and_invalid_answers(self):
        """バトル場に出す決定は、ワザを使ったプレイヤーが、自分のベンチのポケモンから選ぶ。相手の答え・ベンチにいないポケモンの答えは拒否する（状態は
        変わらない）。"""
        waiting = attack_with(self.koffing(bench=(RATTATA, RATTATA)), 0, 1, H)
        d = waiting.decision
        self.assertEqual((d.player, len(d.options)), (0, 2))
        before = snapshot(waiting)
        for answer, code in ((ResolveDecision(1, d.id, (d.options[0],)), "NOT_YOUR_DECISION"),
                             (ResolveDecision(0, d.id, (waiting.players[1].active.pokemon_id,)), None)):
            with self.subTest(code=code), self.assertRaises(IllegalActionError) as raised:
                apply_kernel(waiting, answer)
            if code is not None:
                self.assertEqual(raised.exception.code, code)
            self.assertEqual(snapshot(waiting), before)

    def test_save_and_restore_while_waiting_for_the_promotion(self):
        """バトル場に出す決定を待つ状態を複製・保存しても、再開の結果は同じ（コインを投げ直さない）。"""
        waiting = attack_with(self.koffing(), 0, 1, H)
        answer = ResolveDecision(0, waiting.decision.id, (waiting.decision.options[0],))
        results = [snapshot(apply_kernel(s, answer)) for s in (waiting, waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting)))]
        self.assertEqual(len({str(r) for r in results}), 1)
        self.assertEqual(serialization_problems(waiting), [])

    def test_card_conservation(self):
        """どのカードも 1 か所にだけある（山札・手札・トラッシュ・サイド・場）。"""
        done = attack_with(self.koffing(trainers=[(PLUSPOWER, TURN)]), 0, 1, H)
        for p in done.players:
            places = list(p.deck) + list(p.hand) + list(p.discard) + list(p.prizes)
            for pokemon in p.in_play():
                places += [*pokemon.cards(), *pokemon.energy, *(t.card for t in pokemon.trainers)]
            self.assertEqual(len(places), len(set(places)))
        total = sum(len(p.deck) + len(p.hand) + len(p.discard) + len(p.prizes) + sum(
            len(pokemon.cards()) + len(pokemon.energy) + len(pokemon.trainers) for pokemon in p.in_play()) for p in done.players)
        self.assertEqual(total, len(done.cards))


class ExistingEffectTest(unittest.TestCase):
    """既存の型で登録したワザ（みだれひっかき・スモッグ・サンダーアタック・マシンガンドリル・へなへなタックル）。"""

    def test_thunder_attack_shares_one_coin(self):
        """わるいサンダースの「サンダーアタック」: 1 枚のコインで「おもて」ならマヒ（自分へのダメージなし）、「うら」なら自分に 10（マヒなし）。投げ直さない。"""
        state = board(mon(DARK_JOLTEON))
        heads = attack_with(state, 0, 1, H)
        self.assertEqual(len(coins(heads, len(state.log))), 1)
        self.assertTrue(heads.players[1].active is None or heads.players[1].active.conditions.paralyzed)
        self.assertEqual([e for e in events(heads, len(state.log), "damage") if e.get("target") == "self"], [])
        tails = attack_with(state, 0, 1, T)
        self.assertEqual(len(coins(tails, len(state.log))), 1)
        self.assertEqual([e["amount"] for e in events(tails, len(state.log), "damage") if e.get("target") == "self"], [10])
        self.assertFalse(tails.players[1].active.conditions.paralyzed)

    def test_coin_damage_attacks(self):
        """サンドパンの「みだれひっかき」はコイン 3 枚の「おもて」の数 × 20、マチスのオニドリルの「マシンガンドリル」はコイン 5 枚の「おもて」の数 × 10。"""
        for card, index, sides, per in ((SANDSLASH, 1, (H, T, H), 20), (LT_SURGES_FEAROW, 0, (H, H, T, H, T), 10)):
            with self.subTest(card=card):
                state = board(mon(card), mon(HITMONCHAN, (FIGHTING, FIGHTING)))
                done = attack_with(state, 0, index, *sides)
                self.assertEqual(len(coins(done, len(state.log))), len(sides))
                [damage] = [e for e in events(done, len(state.log), "damage") if e.get("target") is None]
                self.assertEqual(damage["steps"][0][1], sides.count(H) * per)

    def test_smog_and_tackle(self):
        """化石の秘密のブーバーの「スモッグ」は「おもて」ならどく、エリカのマダツボミの「へなへなタックル」は自分にも 10。"""
        state = board(mon(FOSSIL_MAGMAR))
        self.assertIsNotNone(attack_with(state, 0, 1, H).players[1].active.conditions.poison)
        self.assertIsNone(attack_with(state, 0, 1, T).players[1].active.conditions.poison)
        state = board(mon(ERIKAS_BELLSPROUT))
        done = attack_with(state, 0, 0)
        self.assertEqual([e["amount"] for e in events(done, len(state.log), "damage") if e.get("target") == "self"], [10])

    def test_evolution_sources_match_names_exactly(self):
        """進化元は印刷の「○○から進化」と名前が完全に一致するたねポケモン（サンド・イーブイ・マチスのオニスズメ）。収録の弾で制限しない。"""
        for evolved, basic in ((SANDSLASH, SANDSHREW), (DARK_JOLTEON, EEVEE), (LT_SURGES_FEAROW, LT_SURGES_SPEAROW)):
            with self.subTest(card=evolved):
                state = board(mon(basic, played_turn=1), hand=(evolved,))
                done = apply_kernel(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].active.pokemon_id))
                self.assertEqual(done.card_def(done.players[0].active.card).id, evolved)


class CopyTest(unittest.TestCase):
    """相手のワザを自分のワザとして使う効果（ピッピ・ピクシーの「ゆびをふる」）で、v0.36 のワザを使う。"""

    def copy(self, copier, defender, choice, *sides):
        energy = (PSYCHIC, PSYCHIC, PSYCHIC)
        state = board(mon(copier, energy), defender)
        waiting = play(state, UseAttack(0, {CLEFAIRY: 1, CLEFABLE: 0}[copier]))  # ゆびをふるの位置
        return state, apply_kernel(with_coin_results(waiting, *sides), ResolveDecision(0, waiting.decision.id, (choice,)))

    def test_copied_smokescreen_and_ice_gives_the_effect_with_the_copier_as_source(self):
        """まねた「えんまく」「すなかけ」「アイスバーン」は、ワザを使ったポケモン（ピッピ）を発生源として効果を与える（どのワザで与えたかはログの
        ``effect``）。「すなかけ」は「1回できえる」のまま。不変条件は効果を与えたワザの登録で確かめる。"""
        for defender, choice, kind, single_use in ((mon(KOGAS_KOFFING), 0, AttackCoinCheck.kind, False),
                                                   (mon(SANDSHREW), 0, AttackCoinCheck.kind, True),
                                                   (mon(MISTYS_SEEL), 0, CannotRetreat.kind, None)):
            with self.subTest(defender=defender["card"]):
                state, done = self.copy(CLEFAIRY, defender, choice)
                [added] = events(done, len(state.log), "persistent_effect_added")
                self.assertEqual((added["persistent_effect"], added["source_card"], added["effect"]),
                                 (kind, state.players[0].active.card, f"{defender['card']}#{choice}"))
                self.assertEqual(added.get("single_use"), single_use)
                self.assertEqual(check_invariants(done), [])

    def test_copied_obscuring_gas_returns_the_copier_and_its_stack(self):
        """ピクシー（ピッピから進化）がまねた「くもがくれガス」の「おもて」: ピクシーと下のピッピ・ついているエネルギーを、ピクシーの持ち主の山札にもどす。"""
        state, done = self.copy(CLEFABLE, mon(KOGAS_KOFFING, damage=0), 1, H)
        clefable = state.players[0].active
        [moved] = events(done, len(state.log), "return_in_play_to_deck")
        self.assertEqual(sorted(moved["cards"]), sorted([*clefable.cards(), *clefable.energy]))
        self.assertEqual(moved["evolution_stack"], clefable.evolution_stack)
        self.assertEqual(done.decision.kind, "promote_active")

    def test_copying_amnesia_is_unsupported(self):
        """v0.36: 「ドわすれ」をまねるのはエンジンの未対応（v0.35 は内部エラーだった。``OpponentAttackLock.copy_problem``）。"""
        from tests.helpers import MISTYS_POLIWAG

        state = board(mon(CLEFAIRY, (PSYCHIC, PSYCHIC, PSYCHIC)), mon(MISTYS_POLIWAG, (WATER, WATER)))
        assert_stops(self, state, UseAttack(0, 1), "UNSUPPORTED_COPIED_ATTACK")


class IntegrityTest(unittest.TestCase):
    """不変条件・書き出し。"""

    def test_serialization(self):
        """形式 10（と 8 以上）に効果の種類 ``attack_coin_check``（``single_use``）・``cannot_retreat`` が出る。形式 1〜7 は ``ValueError``。"""
        _, smoked = given((SANDSHREW, 0))
        data = state_to_dict(smoked, format_version=10)
        [effect] = data["players"][1]["active"]["persistent_effects"]
        self.assertEqual((effect["effect"], effect["single_use"]), ("attack_coin_check", True))
        _, locked = given((MISTYS_SEEL, 0))
        [effect] = state_to_dict(locked, format_version=10)["players"][1]["active"]["persistent_effects"]
        self.assertEqual(set(effect), {"effect", "source_card", "source_card_id", "source_player", "created_turn", "active_turn"})
        for version in range(1, 8):
            with self.subTest(version=version), self.assertRaises(ValueError):
                state_to_dict(locked, format_version=version)
        self.assertEqual(serialization_problems(smoked), [])

    def test_invariants_reject_broken_effects(self):
        """不変条件は、効果を与えたワザの登録と合わない「1回できえる」・ベンチに残った効果・期限の過ぎた効果を拒否する。"""
        import dataclasses

        _, smoked = given((HORSEA, 0))
        broken = smoked.clone()
        target = broken.players[1].active
        target.persistent_effects = (dataclasses.replace(target.persistent_effects[0], single_use=True),)
        self.assertTrue(any("登録された実装" in p for p in check_invariants(broken)))
        moved = smoked.clone()
        moved.players[1].active, moved.players[1].bench[0] = moved.players[1].bench[0], moved.players[1].active
        self.assertTrue(any("ベンチ" in p for p in check_invariants(moved)))

    def test_rejections_do_not_change_the_state_in_any_mode(self):
        """拒否（にげる・こんらんのワザ・くもがくれガスの RD9）は、どの先読みの方法でも、状態・乱数・ログを変えない。"""
        _, locked = given((MISTYS_SEEL, 0), mon(HITMONCHAN, (FIGHTING, FIGHTING), confusion=True))
        for mode in PREFLIGHT_MODES:
            before = snapshot(locked)
            with self.subTest(mode=mode), self.assertRaises(EngineError):
                apply_kernel(locked, retreat(locked, 1), preflight=mode)
            self.assertEqual(snapshot(locked), before)


class CardDataTest(unittest.TestCase):
    """11 枚の登録・写し・採用の記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_eleven_requested_cards(self):
        """対象は依頼の 11 枚。写しの組 pool_v0_36 は 11 枚で、どれも対戦に使える。同じ名前の別のカード（第1弾のブーバー・第2弾のマダツボミ・第1弾の
        ドガース）とは別の id。"""
        self.assertEqual(len(V0_36_POKEMON), 11)
        self.assertEqual(list(read_extract()["pool_v0_36"]), list(V0_36_POKEMON))
        for card in V0_36_POKEMON:
            with self.subTest(card=card):
                self.assertTrue(self.pool.is_playable(card))
        self.assertNotEqual(FOSSIL_MAGMAR, MAGMAR)
        self.assertEqual(self.pool.get(FOSSIL_MAGMAR).name_ja, self.pool.get(MAGMAR).name_ja)
        self.assertNotEqual([a.name_ja for a in self.pool.get(FOSSIL_MAGMAR).attacks], [a.name_ja for a in self.pool.get(MAGMAR).attacks])

    def test_every_attack_is_registered_with_the_expected_type(self):
        """19 のワザがどれも登録され、型と値が表のとおり。名前・文面は写しと同じで、処理に使う文面は kyuura の印刷の文面。特殊能力を持つカードはない。"""
        seen = set()
        for card in V0_36_POKEMON:
            definition = self.pool.get(card)
            self.assertEqual(definition.powers, ())
            for attack in definition.attacks:
                key = (card, attack.index)
                seen.add(key)
                entry = E.DEFAULT_EFFECTS.attack_entry(card, attack.index)
                kind, values = EXPECTED[key]
                with self.subTest(key=key):
                    self.assertIs(type(entry.effect), kind)
                    for name, value in values.items():
                        self.assertEqual(getattr(entry.effect, name), value)
                    self.assertEqual(entry.name_ja, attack.name_ja)
                    self.assertEqual(entry.text_ja, attack.text_ja)
                    self.assertEqual(entry.play_text_ja, attack.text_ja)
                    if attack.text_ja is not None:
                        self.assertEqual(entry.source, "kyuura data/cards.json")
        self.assertEqual(seen, set(EXPECTED))

    def test_text_variants_are_not_mixed(self):
        """手順 4 のコインの効果は、説明の文面で「1回できえる」かを決める（名前が同じ「すなかけ」でも、サンドとキョウのポッポは別の設定）。文面と合わない
        設定の登録は拒否する。"""
        sand = self.pool.get(SANDSHREW).attacks[0]
        pidgey = self.pool.get(KOGAS_PIDGEY).attacks[1]
        self.assertEqual(sand.name_ja, pidgey.name_ja)
        self.assertEqual(E.DamageThenAttackCoinCheck(single_use=True).check(sand), [])
        self.assertTrue(E.DamageThenAttackCoinCheck(single_use=False).check(sand))
        self.assertEqual(E.DamageThenAttackCoinCheck(single_use=False).check(pidgey), [])
        self.assertTrue(E.DamageThenAttackCoinCheck(single_use=True).check(pidgey))
        self.assertTrue(E.DamageThenRetreatLock().check(sand))

    def test_adoption_records(self):
        """採用の記録（kyuura データ・写しの元のコミット）と、pcg-search.com の同じ版のページとの照合（違いは句読点・かなと漢字・サイトの欠けだけで、
        処理に影響しない）。ガイドブックの項目はない。"""
        sources = cs.load_sources()
        self.assertEqual(cs.problems(), [])
        for card in V0_36_POKEMON:
            record = sources["cards"][card]
            with self.subTest(card=card):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"]),
                                 (cs.KYUURA_DATA, cs.ADOPTED, ADOPTED_COMMIT, kyuura_records_since_v0_69(card)))  # v0.69: 研究の基準を上げて加わった kyuura の記録（tests/helpers.py の V0_69_KYUURA_RECORDS_ADDED）
                [check] = record["external_checks"]
                self.assertEqual((check["site"], check["edition"]["list_number"], check["checked_on"]), ("pcg-search.com", EDITIONS[card], "2026-10-16"))
                self.assertFalse(any(d["affects_behavior"] for d in check["differences"]))
        changed = {card for card in V0_36_POKEMON if sources["cards"][card]["external_checks"][0]["differences"]}
        self.assertEqual(changed, {SANDSLASH, FOSSIL_MAGMAR, DARK_JOLTEON})

    def test_document_lists_every_card_and_unresolved_id(self):
        text = DOC.read_text(encoding="utf-8")
        for card in V0_36_POKEMON:
            self.assertIn(card, text)
        for ruling in ("AC6", "RD9", "UNRESOLVED_ATTACK_CHECK_CONFUSION", "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT"):
            self.assertIn(ruling, text)


class PreflightParityTest(unittest.TestCase):
    """19 のワザと、手順 4 のコインのあるワザ・にげるの拒否で、先読みの方法（``derived``・``derived_full``・``legacy``）の結果が同じ。"""

    def test_every_attack(self):
        for (card, index) in EXPECTED:
            for sides in ((H,) * 6, (T,) * 6):
                with self.subTest(card=card, index=index, sides=sides[0]):
                    state = board(mon(card), mon(HITMONCHAN, (FIGHTING, FIGHTING)))
                    results = set()
                    for mode in PREFLIGHT_MODES:
                        try:
                            results.add(str(snapshot(attack_with(state, 0, index, *sides, mode=mode))))
                        except EngineError as error:
                            results.add((type(error).__name__, error.code, str(error)))
                    self.assertEqual(len(results), 1)

    def test_attack_check_branches(self):
        _, done = given((KOGAS_KOFFING, 0), mon(DODUO, (FIRE, FIRE)))
        for sides in ((H, H, H), (H, T, T), (T,)):
            with self.subTest(sides=sides):
                results = {str(snapshot(attack_with(done, 1, 0, *sides, mode=mode))) for mode in PREFLIGHT_MODES}
                self.assertEqual(len(results), 1)


class CountsTest(unittest.TestCase):
    def test_counts(self):
        """登録したワザは 19（説明文のあるワザ 16）。v0.36 の型は 3 つで、v0.13 の止める関数の型（``VERIFIED``）に入れていない。"""
        from kyuura_engine.resolution import v013_checks

        keys = [k for k in E.DEFAULT_EFFECTS.attack_keys() if k.card_id in V0_36_POKEMON]
        self.assertEqual(len(keys), 19)
        self.assertEqual(sum(1 for k in keys if E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).text_ja), 16)
        types = Counter(type(E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect).__name__ for k in keys)
        self.assertEqual(types["DamageThenAttackCoinCheck"], 8)
        self.assertEqual(types["DamageThenRetreatLock"], 2)
        self.assertEqual(types["DamageThenReturnSelfToDeckOnHeads"], 1)
        for cls in (E.DamageThenAttackCoinCheck, E.DamageThenRetreatLock, E.DamageThenReturnSelfToDeckOnHeads):
            self.assertNotIn(cls, v013_checks.VERIFIED)


if __name__ == "__main__":
    unittest.main()

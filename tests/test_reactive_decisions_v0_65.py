"""v0.65: キョウ秘伝,変わり身の術・カスミのドククラゲ［にげこむ］・タケシのサイドン［ベンチガード］と、ワザの最中の任意の決定（docs/reactive-decisions-v0.65.md）。

根拠は kyuura データの採用（kyuura の印刷の文面。kyuura_engine/data/card_sources.json の PMCG6-083・PMCG5-033・PMCG5-055）と、［にげこむ］の処理に使う文面の
v0.18b の記録（docs/unresolved-research-v0.18b.md 4.1。p.100 の［にげこむ］の最新の説明と解説を 2026-10-14 に読んだ記録の再利用。v0.65 で誌面を読み直していない）。
決められない場合は NT1〜NT3・RX1・FL1・BG1・BG2・KD1 で止める（どれも kyuura の未解決の一覧にない）。コインは ``with_coin_bits`` で決める。
"""

from __future__ import annotations

import pickle
import unittest

import kyuura_engine.effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.commands import (
    AttachEnergy,
    EndTurn,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UseAttack,
)
from kyuura_engine.decisions import BENCH_GUARD, NINJA_TRICK, REACTION_SWITCH
from kyuura_engine.effects import DEFAULT_EFFECTS
from kyuura_engine.engine import check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe
from kyuura_engine.serialize import state_to_dict
from tests.helpers import (
    BROCKS_DIGLETT,
    BROCKS_RHYDON,
    BROCKS_RHYHORN,
    DARK_ARBOK,
    DEFENDER,
    FIGHTING,
    FOSSIL_MAGNETON,
    GRASS,
    HITMONCHAN,
    KOFFING,
    KOGAS_KOFFING,
    KOGAS_NINJA_TRICK,
    LIGHTNING,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MAGNEMITE,
    MISTYS_TENTACOOL,
    MISTYS_TENTACRUEL,
    MUK,
    RAINBOW_ENERGY,
    RATTATA,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_bits,
)
from tests.log_audit import observation_problems, serialization_problems

DARK_VILEPLUME, DARK_GLOOM, ROCKET_ODDISH, DITTO, FOSSIL_GEODUDE = "PMCG4-010", "PMCG4-006", "PMCG4-003", "PMCG3-042", "PMCG3-034"
BELOW = {DARK_VILEPLUME: [ROCKET_ODDISH, DARK_GLOOM], MISTYS_TENTACRUEL: MISTYS_TENTACOOL, BROCKS_RHYDON: BROCKS_RHYHORN, MACHAMP: [MACHOP, MACHOKE], FOSSIL_MAGNETON: MAGNEMITE, MUK: "PMCG4-004",
         DARK_ARBOK: "PMCG4-001"}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def table(active, opponent, *, bench=(), opponent_bench=(), hand=(), opponent_hand=(), turn=7, player=0):
    return build_test_state([{"active": active, "bench": list(bench), "hand": list(hand), "deck": [GRASS] * 10, "prizes": 3},
                             {"active": opponent, "bench": list(opponent_bench), "hand": list(opponent_hand), "deck": [FIGHTING] * 10, "prizes": 3}],
                            turn_number=turn, current_player=player)


def events(state, since, kind):
    return [dict(e) for e in state.log[since:] if e["kind"] == kind]


def kinds(state, since):
    return [e["kind"] for e in state.log[since:]]


def written(state):
    return state_to_dict(state, format_version=21), [dict(e) for e in state.log], repr(state.rng.getstate())


def clean(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def flee_board(**extra):
    """番のプレイヤー（0）のエビワラー（闘闘無）が、カスミのドククラゲ（控えにコラッタ）に「スペシャルパンチ」（40）を使う盤面。"""
    opponent = extra.pop("opponent", mon(MISTYS_TENTACRUEL, (WATER, WATER)))
    return table(extra.pop("active", mon(HITMONCHAN, (FIGHTING, FIGHTING, FIGHTING))), opponent, bench=[RATTATA],
                 opponent_bench=extra.pop("opponent_bench", [RATTATA]), **extra)


def trick_board(**extra):
    """番のプレイヤー（0）がキョウのドガースに変わり身の術をつけて番を終え、相手（1）のエビワラーの番にする。"""
    state = table(extra.pop("active", mon(KOGAS_KOFFING, (GRASS,))), extra.pop("opponent", mon(HITMONCHAN, (FIGHTING, FIGHTING, FIGHTING))),
                  bench=extra.pop("bench", [RATTATA]), opponent_bench=[RATTATA], hand=[KOGAS_NINJA_TRICK], **extra)
    uid = next(u for u in state.players[0].hand if state.cards[u].card_id == KOGAS_NINJA_TRICK)
    state = apply_kernel(state, PlayTrainer(0, uid))
    return apply_kernel(state, EndTurn(0)), uid


def guard_board(bench, *, active=None, opponent=None, opponent_bench=(RATTATA,)):
    """番のプレイヤー（0）のタケシのディグダ（闘闘）が「ミニじしん」（自分の控え全員に 10）を使う盤面。``bench`` は自分の控え。"""
    return table(active or mon(BROCKS_DIGLETT, (FIGHTING, FIGHTING)), opponent or mon(HITMONCHAN), bench=list(bench), opponent_bench=list(opponent_bench))


class RegistrationTest(unittest.TestCase):
    def test_counts(self):
        """対応ポケモン 348 → 350、トレーナー 89 → 90、エネルギー 10（450 枚）。ワザの登録 591 → 593、特殊能力 54 → 56、トレーナーの登録 89 → 90。"""
        pool = load_card_pool()
        playable = [pool.get(c) for c in pool.definitions if pool.is_playable(c)]
        by = {k: sum(1 for d in playable if d.category == k) for k in ("pokemon", "trainer", "energy")}
        self.assertEqual(by, {"pokemon": 350, "trainer": 90, "energy": 10})
        self.assertEqual((len(DEFAULT_EFFECTS._attacks), len(DEFAULT_EFFECTS._powers), len(DEFAULT_EFFECTS._trainers)), (593, 56, 90))
        for card in (KOGAS_NINJA_TRICK, MISTYS_TENTACRUEL, BROCKS_RHYDON):
            self.assertTrue(pool.is_playable(card), card)

    def test_types(self):
        self.assertIsInstance(DEFAULT_EFFECTS.trainer_entry(KOGAS_NINJA_TRICK).effect, E.NinjaTrick)
        self.assertIsInstance(DEFAULT_EFFECTS.power_entry(MISTYS_TENTACRUEL, 0).effect, E.FleeAfterAttackDamage)
        self.assertIsInstance(DEFAULT_EFFECTS.power_entry(BROCKS_RHYDON, 0).effect, E.TakeBenchDamageInstead)
        self.assertIsInstance(DEFAULT_EFFECTS.attack_entry(MISTYS_TENTACRUEL, 0).effect, E.DamageThenPoisonOrConfuse)
        self.assertIsInstance(DEFAULT_EFFECTS.attack_entry(BROCKS_RHYDON, 0).effect, E.FailOnTailsDamage)

    def test_flee_text_source(self):
        """［にげこむ］の処理に使う文面は、v0.18b の記録（p.100 の最新の説明）。印刷の文面（kyuura の写し）とは違い、出典はこのリポジトリの記録（kyuura が p.100 を確かめた
        記録としない）。研究の対応表では kyuura に記録がないもの（registered_without_kyuura_record）。"""
        import json
        import pathlib

        entry = DEFAULT_EFFECTS.power_entry(MISTYS_TENTACRUEL, 0)
        self.assertEqual(entry.play_text_ja, E.FLEE_PLAY_TEXT)
        self.assertNotEqual(entry.play_text_ja, entry.text_ja)
        self.assertEqual(entry.source, E.ENGINE_RECORD_FLEE_SOURCE)
        root = pathlib.Path(__file__).resolve().parent.parent
        doc = (root / "docs" / "unresolved-research-v0.18b.md").read_text(encoding="utf-8")
        self.assertIn(E.FLEE_PLAY_TEXT, doc)
        links = json.loads((root / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        self.assertIn(f"{MISTYS_TENTACRUEL}/power/0", links["latest_descriptions"]["registered_without_kyuura_record"])

    def test_powers_are_not_declarable(self):
        """［にげこむ］・［ベンチガード］は決められたときにしか使えない（宣言する特殊能力。UsePokemonPower では POWER_NOT_USABLE_NOW）。"""
        from kyuura_engine.commands import UsePokemonPower

        state = table(mon(MISTYS_TENTACRUEL, (WATER,)), mon(HITMONCHAN), bench=[mon(BROCKS_RHYDON)])
        for pid in (state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id):
            with self.assertRaises(IllegalActionError) as raised:
                apply_kernel(state, UsePokemonPower(0, pid, 0))
            self.assertEqual(raised.exception.code, "POWER_NOT_USABLE_NOW")

    def test_no_card_id_branches(self):
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent / "kyuura_engine"
        for path in [root / "engine.py", *sorted((root / "resolution").glob("*.py"))]:
            text = path.read_text(encoding="utf-8")
            for card in (KOGAS_NINJA_TRICK, MISTYS_TENTACRUEL, BROCKS_RHYDON):
                self.assertNotIn(card, text, path.name)


class FleeTest(unittest.TestCase):
    """［にげこむ］: 相手のワザのダメージを受けたあと・ダメージ以外の効果の前に、ドククラゲの持ち主が使うかを決める。"""

    def test_offer_and_switch(self):
        state = flee_board()
        new = apply_kernel(state, UseAttack(0, 1))
        decision = new.decision
        self.assertEqual((decision.kind, decision.player, decision.min_choices, decision.max_choices), (REACTION_SWITCH, 1, 0, 1))
        self.assertEqual(decision.options, (state.players[1].bench[0].pokemon_id,))
        self.assertEqual(new.players[1].active.damage, 40)
        clean(self, new)
        since = len(new.log)
        done = apply_kernel(new, ResolveDecision(1, decision.id, decision.options))
        self.assertEqual(kinds(done, since)[:2], ["flee", "switch"])
        self.assertEqual(done.players[1].bench[-1].card, state.players[1].active.card)
        self.assertEqual(done.players[1].bench[-1].damage, 40)  # 受けたダメージはそのまま（ダメージを防ぐ効果ではない）
        self.assertEqual(done.current_player, 1)  # ワザのあとの番の終わり
        clean(self, done)

    def test_decline_and_effects(self):
        """くさいガス（ダメージ → コイン → どく・こんらん）: 使えば、コインを投げず効果も受けない（入れ替わって出たポケモンも受けない）。使わなければコインと効果。"""
        state = flee_board(active=mon(KOFFING, (GRASS, GRASS)))
        new = apply_kernel(with_coin_bits(state, H), UseAttack(0, 0))
        self.assertEqual(new.decision.kind, REACTION_SWITCH)
        since = len(new.log)
        used = apply_kernel(new, ResolveDecision(1, new.decision.id, new.decision.options))
        self.assertNotIn("coin_flip", kinds(used, since))
        self.assertNotIn("special_condition", kinds(used, since))
        self.assertIsNone(used.players[1].active.conditions.poison)
        declined = apply_kernel(new, ResolveDecision(1, new.decision.id, ()))
        self.assertEqual(kinds(declined, since)[:3], ["flee_declined", "coin_flip", "special_condition"])
        self.assertIsNotNone(declined.players[1].active.conditions.poison)

    def test_save_restore_and_invalid_answer(self):
        state = flee_board()
        new = apply_kernel(with_coin_bits(state, H, T, H), UseAttack(0, 1))
        restored = pickle.loads(pickle.dumps(new))
        before = written(new)
        for bad in ((999,), (new.decision.options[0], new.decision.options[0])):
            with self.assertRaises(IllegalActionError):
                apply_kernel(new, ResolveDecision(1, new.decision.id, bad))
            self.assertEqual(written(new), before)
        with self.assertRaises(IllegalActionError):
            apply_kernel(new, ResolveDecision(0, new.decision.id, ()))  # 決めるのはドククラゲの持ち主
        self.assertEqual(written(new), before)
        for answer in ((), new.decision.options):
            command = ResolveDecision(1, new.decision.id, answer)
            self.assertEqual(written(apply_kernel(new, command)), written(apply_kernel(restored, command)))

    def test_unbounded_coins_then_flee(self):
        """れんぞくいしなげ（「うら」が出るまで投げる）のあと［にげこむ］: 先読みの有限の組に入れ替えの答えが加わっても、宣言を受け付け、コインを投げ直さない。"""
        state = flee_board(active=mon(FOSSIL_GEODUDE, (FIGHTING, FIGHTING)))
        new = apply_kernel(with_coin_bits(state, H, H, H, T), UseAttack(0, 0))
        self.assertEqual(new.decision.kind, REACTION_SWITCH)
        self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage")], [30])
        flips = len(events(new, len(state.log), "coin_flip"))
        done = apply_kernel(new, ResolveDecision(1, new.decision.id, new.decision.options))
        self.assertEqual(len(events(done, len(state.log), "coin_flip")), flips)
        zero = apply_kernel(with_coin_bits(state, T), UseAttack(0, 0))
        self.assertIsNone(zero.decision)  # 0 ダメージ（ダメージを受けていない）では聞かない

    def test_knocked_out_is_kd1(self):
        """KD1: そのダメージで HP 以上になったドククラゲの［にげこむ］は、使うを選ぶと止める（使わないことはできる。そのあと、ワザのあとにきぜつ）。"""
        state = flee_board(opponent=mon(MISTYS_TENTACRUEL, (WATER,), damage=30))
        new = apply_kernel(state, UseAttack(0, 1))
        d = new.decision
        self.assertEqual((d.kind, d.context_value("unresolved_code")), (REACTION_SWITCH, "UNRESOLVED_REACTION_BY_KNOCKED_OUT_POKEMON"))
        clean(self, new)
        before = written(new)
        with self.assertRaises(UnsupportedError) as raised:
            apply_kernel(new, ResolveDecision(1, d.id, d.options))
        self.assertEqual(raised.exception.code, "UNRESOLVED_REACTION_BY_KNOCKED_OUT_POKEMON")
        self.assertEqual(written(new), before)
        done = apply_kernel(new, ResolveDecision(1, d.id, ()))
        self.assertIn("knock_out", kinds(done, len(new.log)))

    def test_not_offered(self):
        """使えない: ダメージを受けたときねむり・マヒ・こんらん・かがくへんかガス・控えがいない・ダメージが 0。"""
        cases = {
            "confused": flee_board(opponent=mon(MISTYS_TENTACRUEL, (WATER,), confusion=True)),
            "asleep": flee_board(opponent=mon(MISTYS_TENTACRUEL, (WATER,), sleep=True)),
            "gas": flee_board(opponent_bench=[RATTATA, mon(MUK)]),
            "no_bench": flee_board(opponent_bench=[]),
        }
        for name, state in cases.items():
            new = apply_kernel(state, UseAttack(0, 1))
            self.assertFalse(new.decision is not None and new.decision.kind == REACTION_SWITCH, name)
            self.assertNotIn("flee", kinds(new, len(state.log)), name)
        # ディフェンダーで 0 になったダメージは受けていない
        zero = flee_board(active=mon(HITMONCHAN, (FIGHTING,)), opponent=mon(MISTYS_TENTACRUEL, (WATER,), trainers=[(DEFENDER, 7)]))
        new = apply_kernel(zero, UseAttack(0, 0))
        self.assertEqual([e["amount"] for e in events(new, len(zero.log), "damage")], [0])
        self.assertIsNone(new.decision)

    def test_own_attack_flee_constant(self):
        """自分のワザの返す効果のダメージで候補になったドククラゲの［にげこむ］は、使うを選ぶと止める（FL1）。"""
        self.assertEqual(E.FLEE_OWN_ATTACK_CODE, "UNRESOLVED_FLEE_DURING_OWN_ATTACK")


class NinjaTrickTest(unittest.TestCase):
    """変わり身の術: 相手のワザの宣言のあと・ワザの要素の前に、バトル場のキョウのポケモンと控えを入れ替えてよい。"""

    def test_play_requires_kogas_active(self):
        state = table(mon(RATTATA), mon(HITMONCHAN), hand=[KOGAS_NINJA_TRICK], bench=[mon(KOGAS_KOFFING)])
        uid = state.players[0].hand[0]
        with self.assertRaises(UnsupportedError) as raised:
            apply_kernel(state, PlayTrainer(0, uid))
        self.assertEqual(raised.exception.code, "UNRESOLVED_TRAINER_WITHOUT_TARGET")
        tricked, card = trick_board()
        self.assertEqual([t.card for t in tricked.players[0].active.trainers], [card])
        self.assertIsNone(tricked.players[0].active.trainers[0].discard_at_end_of_turn)  # 番の終わりではトラッシュしない

    def test_switch_before_damage(self):
        state, card = trick_board()
        new = apply_kernel(state, UseAttack(1, 1))
        d = new.decision
        self.assertEqual((d.kind, d.player, d.options), (NINJA_TRICK, 0, (state.players[0].bench[0].pokemon_id,)))
        self.assertEqual(kinds(new, len(state.log)), ["attack"])  # ワザの要素の前
        clean(self, new)
        since = len(new.log)
        done = apply_kernel(new, ResolveDecision(0, d.id, d.options))
        self.assertEqual(kinds(done, since)[:3], ["ninja_trick", "switch", "discard_attached_trainer"])
        damage = events(done, since, "damage")
        self.assertEqual([e["pokemon"] for e in damage], [state.players[0].bench[0].card])  # 入れ替わって出たポケモンが受ける
        self.assertIn(card, done.players[0].discard)
        self.assertEqual(len(events(done, since, "attack")), 0)  # 宣言をやり直さない

    def test_decline_keeps_trick(self):
        state, card = trick_board()
        new = apply_kernel(state, UseAttack(1, 0))
        done = apply_kernel(new, ResolveDecision(0, new.decision.id, ()))
        self.assertIn("ninja_trick_declined", kinds(done, len(new.log)))
        self.assertEqual([t.card for t in done.players[0].active.trainers], [card])

    def test_discarded_when_leaving_active(self):
        """にげる・ポケモンいれかえでバトル場をはなれたら、変わり身の術をトラッシュする（reason left_active）。"""
        state, card = trick_board()
        state = apply_kernel(state, EndTurn(1))
        retreat = apply_kernel(state, Retreat(0, (state.players[0].active.energy[0],), state.players[0].bench[0].card))
        self.assertIn(card, retreat.players[0].discard)
        self.assertEqual([e["reason"] for e in events(retreat, len(state.log), "discard_attached_trainer")], ["left_active"])

    def test_save_restore_and_invalid(self):
        state, _ = trick_board()
        new = apply_kernel(state, UseAttack(1, 1))
        restored = pickle.loads(pickle.dumps(new))
        before = written(new)
        with self.assertRaises(IllegalActionError):
            apply_kernel(new, ResolveDecision(0, new.decision.id, (999,)))
        self.assertEqual(written(new), before)
        for answer in ((), new.decision.options):
            command = ResolveDecision(0, new.decision.id, answer)
            self.assertEqual(written(apply_kernel(new, command)), written(apply_kernel(restored, command)))

    def test_knock_out_after_switch(self):
        """入れ替わって出たコラッタ（HP 30）がスペシャルパンチ（40）できぜつ → サイドを取る決定 → 持ち主がバトル場に出す（変わり身の術はもうない）。"""
        state, _ = trick_board()
        new = apply_kernel(state, UseAttack(1, 1))
        done = apply_kernel(new, ResolveDecision(0, new.decision.id, new.decision.options))
        self.assertEqual([e["pokemon"] for e in events(done, len(new.log), "knock_out")], [state.players[0].bench[0].card])
        self.assertEqual(done.decision.kind, "take_prize")
        clean(self, done)

    def test_nt3_trainer_ban(self):
        """NT3: だれもトレーナーカードを使えない（わるいラフレシアの［アレルギーかふん］）とき、ついている変わり身の術で入れ替えるかは決められない。使うを選ぶと止める。"""
        banned = table(mon(KOGAS_KOFFING, (GRASS,), trainers=[(KOGAS_NINJA_TRICK, None)]), mon(HITMONCHAN, (FIGHTING, FIGHTING, FIGHTING)),
                       bench=[RATTATA], opponent_bench=[mon(DARK_VILEPLUME)], turn=8, player=1)
        new = apply_kernel(banned, UseAttack(1, 1))
        d = new.decision
        self.assertEqual((d.kind, d.context_value("unresolved_code")), (NINJA_TRICK, "UNRESOLVED_NINJA_TRICK_UNDER_TRAINER_BAN"))
        with self.assertRaises(UnsupportedError):
            apply_kernel(new, ResolveDecision(0, d.id, d.options))
        apply_kernel(new, ResolveDecision(0, d.id, ()))

    def test_rx1_transformed_attacker(self):
        """RX1: ［へんしん］のメタモンのワザに変わり身の術で入れ替えると、メタモンの今の姿が変わる。その答えは止める。"""
        tricked = table(mon(KOGAS_KOFFING, (GRASS,), trainers=[(KOGAS_NINJA_TRICK, None)]), mon(DITTO, (FIGHTING,)),
                        bench=[RATTATA], opponent_bench=[RATTATA], turn=8, player=1)
        new = apply_kernel(tricked, UseAttack(1, 0))  # メタモンはキョウのドガースの「えんまく」
        d = new.decision
        self.assertEqual((d.kind, d.context_value("unresolved_code")), (NINJA_TRICK, "UNRESOLVED_REACTIVE_SWITCH_TRANSFORMED_ATTACKER"))
        with self.assertRaises(UnsupportedError):
            apply_kernel(new, ResolveDecision(0, d.id, d.options))
        apply_kernel(new, ResolveDecision(0, d.id, ()))

    def test_nt1_confusion_coin(self):
        """NT1: ワザを使うポケモンがこんらん状態（手順 5 のコイン）で、相手に変わり身の術がある。宣言の前に止め、状態・乱数・ログを変えない。"""
        state, _ = trick_board()
        from kyuura_engine.conditions import confuse

        confused = state.clone()
        confuse(confused, 1, confused.players[1].active, effect="test")
        before = written(confused)
        with self.assertRaises(UnsupportedError) as raised:
            apply_kernel(confused, UseAttack(1, 0))
        self.assertEqual(raised.exception.code, "UNRESOLVED_NINJA_TRICK_ATTACK_COIN_ORDER")
        self.assertEqual(written(confused), before)

    def test_nt2_returned_with_pokemon(self):
        """NT2: 変わり身の術のついたキョウのドガースが「くもがくれガス」（山札にもどる）を使う。"""
        state, _ = trick_board()
        state = apply_kernel(state, EndTurn(1))
        grass = next(u for u in state.players[0].hand if state.cards[u].card_id == GRASS)
        state = apply_kernel(state, AttachEnergy(0, grass, state.players[0].active.card))
        with self.assertRaises(UnsupportedError) as raised:
            apply_kernel(state, UseAttack(0, 1))
        self.assertEqual(raised.exception.code, "UNRESOLVED_NINJA_TRICK_LEAVES_WITH_POKEMON")


class BenchGuardTest(unittest.TestCase):
    """［ベンチガード］: 自分の控えポケモンがダメージを受けるたびに、ベンチのサイドンがそのうちの 10 をかわりに受けてよい。"""

    def test_ten_damage(self):
        state = guard_board([RATTATA, mon(BROCKS_RHYDON)])
        new = apply_kernel(state, UseAttack(0, 1))
        d = new.decision
        rhydon = state.players[0].bench[1]
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (BENCH_GUARD, 0, (rhydon.pokemon_id,), 0, 1))
        clean(self, new)
        since = len(new.log)
        used = apply_kernel(new, ResolveDecision(0, d.id, d.options))
        damage = events(used, since, "damage")
        self.assertEqual(damage[0]["amount"], 0)
        self.assertEqual(damage[0]["bench_guard"], ((rhydon.pokemon_id, 10),))
        self.assertEqual([e["amount"] for e in events(used, since, "bench_guard")], [10])
        self.assertEqual(used.players[0].bench[1].damage, 20)  # かわりに受けた 10 と、自分が受けた 10（自分のダメージにはサイドン自身は使えない）
        declined = apply_kernel(new, ResolveDecision(0, d.id, ()))
        self.assertEqual(declined.players[0].bench[0].damage, 10)

    def test_twenty_and_two_rhydons(self):
        """20 ダメージ（化石の秘密のレアコイルの「じばく」の控えへの 20）: サイドン 2 匹で 10 ずつ（もとのポケモンは 0）。選ぶ数の上限は min(サイドンの数, ダメージ ÷ 10)。"""
        state = table(mon(FOSSIL_MAGNETON, (LIGHTNING,) * 4), mon(HITMONCHAN),
                      bench=[RATTATA], opponent_bench=[RATTATA, mon(BROCKS_RHYDON), mon(BROCKS_RHYDON)])
        new = apply_kernel(state, UseAttack(0, 1))
        d = new.decision
        _, first, second = state.players[1].bench
        self.assertEqual((d.kind, d.player, d.options, d.max_choices), (BENCH_GUARD, 1, (first.pokemon_id, second.pokemon_id), 2))
        since = len(new.log)
        both = apply_kernel(new, ResolveDecision(1, d.id, d.options))
        self.assertEqual(events(both, since, "damage")[0]["amount"], 0)
        self.assertEqual(sorted(e["pokemon_id"] for e in events(both, since, "bench_guard")), sorted((first.pokemon_id, second.pokemon_id)))
        # 次のサイドンへの 20 では、もう 1 匹のサイドンだけを選べる（上限 1）
        self.assertEqual((both.decision.kind, both.decision.options, both.decision.max_choices), (BENCH_GUARD, (second.pokemon_id,), 1))
        with self.assertRaises(IllegalActionError):
            apply_kernel(new, ResolveDecision(1, d.id, (first.pokemon_id, first.pokemon_id)))

    def test_zero_damage_not_offered(self):
        """ディフェンダーで 0 になる控えのダメージ（10 − 20）では聞かない（ダメージを受けていない）。"""
        state = guard_board([mon(RATTATA, trainers=[(DEFENDER, 8)]), mon(BROCKS_RHYDON)])
        new = apply_kernel(state, UseAttack(0, 1))
        self.assertIsNone(new.decision)
        self.assertEqual([e["amount"] for e in events(new, len(state.log), "damage")][1], 0)

    def test_shock_eye_blocks_use(self):
        """ショックアイ（「特殊能力を使うことができない」）を受けたサイドンは、次の相手の番の終わりまで［ベンチガード］を使えない。"""
        state = table(mon(DARK_ARBOK, (GRASS, GRASS)), mon(BROCKS_DIGLETT, (FIGHTING, FIGHTING)), opponent_bench=[mon(BROCKS_RHYDON), RATTATA])
        rhydon = state.players[1].bench[0]
        new = apply_kernel(state, UseAttack(0, 0))
        new = apply_kernel(new, ResolveDecision(0, new.decision.id, (rhydon.pokemon_id,)))
        self.assertEqual(new.current_player, 1)
        after = apply_kernel(new, UseAttack(1, 1))  # ミニじしん: 控えのコラッタに 10。サイドンは使えない
        self.assertIsNone(after.decision)
        self.assertEqual(events(after, len(new.log), "bench_guard"), [])

    def test_suppressed_by_gas(self):
        state = guard_board([RATTATA, mon(BROCKS_RHYDON), mon(MUK)])
        new = apply_kernel(state, UseAttack(0, 1))
        self.assertIsNone(new.decision)
        self.assertEqual(events(new, len(state.log), "bench_guard"), [])

    def test_bg1_defender_on_rhydon(self):
        """BG1: かわりに受ける 10 をサイドンが受けるダメージとして計算し直すと量が変わる（ディフェンダー）。そのサイドンを選ぶと止める。使わないことはできる。"""
        state = guard_board([RATTATA, mon(BROCKS_RHYDON, trainers=[(DEFENDER, 8)])])
        new = apply_kernel(state, UseAttack(0, 1))
        d = new.decision
        self.assertEqual(d.context_value("unresolved_code"), "UNRESOLVED_BENCH_GUARD_RECOMPUTE")
        before = written(new)
        with self.assertRaises(UnsupportedError) as raised:
            apply_kernel(new, ResolveDecision(0, d.id, d.options))
        self.assertEqual(raised.exception.code, "UNRESOLVED_BENCH_GUARD_RECOMPUTE")
        self.assertEqual(written(new), before)
        apply_kernel(new, ResolveDecision(0, d.id, ()))

    def test_bg2_zero_damage_reaction(self):
        """BG2: どくのきり（相手の控え全員に 10）で、控えのカイリキー（はんげき）のダメージが 0 になる答えは止める。"""
        state = table(mon(DARK_ARBOK, (GRASS, GRASS, GRASS)), mon(HITMONCHAN), opponent_bench=[mon(MACHAMP), mon(BROCKS_RHYDON)])
        new = apply_kernel(state, UseAttack(0, 1))
        d = new.decision
        self.assertEqual((d.kind, d.player), (BENCH_GUARD, 1))
        self.assertEqual(d.context_value("unresolved_code"), "UNRESOLVED_BENCH_GUARD_ZERO_DAMAGE_REACTION")
        before = written(new)
        with self.assertRaises(UnsupportedError) as raised:
            apply_kernel(new, ResolveDecision(1, d.id, d.options))
        self.assertEqual(raised.exception.code, "UNRESOLVED_BENCH_GUARD_ZERO_DAMAGE_REACTION")
        self.assertEqual(written(new), before)
        done = apply_kernel(new, ResolveDecision(1, d.id, ()))
        self.assertIn("counterattack", kinds(done, len(new.log)))

    def test_bg3_knocked_out_holder(self):
        state = guard_board([mon(BROCKS_RHYDON, damage=70), RATTATA])  # サイドンが先に 10 を受けて 80（HP 以上）。そのあとのコラッタの 10
        new = apply_kernel(state, UseAttack(0, 1))
        d = new.decision
        self.assertEqual(d.kind, BENCH_GUARD)
        self.assertEqual(d.context_value("unresolved_code"), "UNRESOLVED_REACTION_BY_KNOCKED_OUT_POKEMON")
        with self.assertRaises(UnsupportedError) as raised:
            apply_kernel(new, ResolveDecision(0, d.id, d.options))
        self.assertEqual(raised.exception.code, "UNRESOLVED_REACTION_BY_KNOCKED_OUT_POKEMON")
        done = apply_kernel(new, ResolveDecision(0, d.id, ()))
        self.assertTrue(any(e["kind"] == "knock_out" for e in done.log[len(new.log):]))

    def test_save_restore(self):
        state = guard_board([RATTATA, RATTATA, mon(BROCKS_RHYDON)])
        new = apply_kernel(state, UseAttack(0, 1))
        restored = pickle.loads(pickle.dumps(new))
        for answer in ((), new.decision.options):
            command = ResolveDecision(0, new.decision.id, answer)
            a, b = apply_kernel(new, command), apply_kernel(restored, command)
            self.assertEqual(written(a), written(b))
            if a.decision is not None and a.decision.kind == BENCH_GUARD:  # 2 匹目の控えへのダメージで、もう一度聞く
                again = ResolveDecision(0, a.decision.id, ())
                self.assertEqual(written(apply_kernel(a, again)), written(apply_kernel(b, again)))

    def test_outside_attack_is_unsupported(self):
        """ワザでないダメージ（レインボーエネルギーを控えにつけた 10）で［ベンチガード］を使える場面はエンジンの未対応（状態を変える前に止める）。"""
        state = table(mon(RATTATA), mon(HITMONCHAN), bench=[RATTATA, mon(BROCKS_RHYDON)], hand=[RAINBOW_ENERGY])
        uid = state.players[0].hand[0]
        before = written(state)
        with self.assertRaises((UnsupportedError, IllegalActionError)) as raised:
            apply_kernel(state, AttachEnergy(0, uid, state.players[0].bench[0].card))
        self.assertEqual(raised.exception.code, "UNSUPPORTED_BENCH_GUARD_OUTSIDE_ATTACK")
        self.assertEqual(written(state), before)


class AttackTest(unittest.TestCase):
    def test_lariat_and_jellyfish_poison(self):
        """ラリアット（70。コインの「うら」なら失敗）・クラゲどく（30。コイン「おもて」でどく、「うら」でこんらん）。"""
        state = table(mon(BROCKS_RHYDON, (FIGHTING,) * 4), mon(HITMONCHAN))
        heads = apply_kernel(with_coin_bits(state, H), UseAttack(0, 0))
        self.assertEqual([e["amount"] for e in events(heads, len(state.log), "damage")], [70])
        tails = apply_kernel(with_coin_bits(state, T), UseAttack(0, 0))
        self.assertEqual(events(tails, len(state.log), "damage"), [])
        self.assertEqual(len(events(tails, len(state.log), "attack_failed")), 1)
        state = table(mon(MISTYS_TENTACRUEL, (WATER,) * 4), mon(HITMONCHAN))
        heads = apply_kernel(with_coin_bits(state, H), UseAttack(0, 0))
        self.assertIsNotNone(heads.players[1].active.conditions.poison)
        tails = apply_kernel(with_coin_bits(state, T), UseAttack(0, 0))
        self.assertTrue(tails.players[1].active.conditions.confused)


class ObservationTest(unittest.TestCase):
    def test_reaction_decisions_are_observable(self):
        state = flee_board()
        new = apply_kernel(state, UseAttack(0, 1))
        view = observe(new, 1)
        self.assertEqual(view["decision"]["kind"], REACTION_SWITCH)
        self.assertEqual(observation_problems(new), [])


class GamesTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.65 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.65 の 4 組を 3 seed ずつ（席を入れかえて 24 局）。監査の失敗・想定外の拒否・内部エラー・手数の上限がなく、変わり身の術・［にげこむ］・［ベンチガード］・
        ラリアット・クラゲどくが使われる（勝敗は判断に使わない）。"""
        from tools import existing_effect_games as games

        results = games.run(range(3), pairings=games.PAIRINGS_V0_65)
        totals = {}
        for run_ in results.values():
            for game in run_["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                if game["outcome"] == "halted":
                    self.assertEqual(game["halt_code"], "UNRESOLVED_MULLIGAN_COMPENSATION")
                for key, count in game.get("v065", {}).items():
                    totals[key] = totals.get(key, 0) + count
        for key in ("ninja_trick", "flee", "flee_declined", "bench_guard", "lariat", "jellyfish_poison", "trick_discarded_left_active"):
            self.assertGreater(totals.get(key, 0), 0, key)


if __name__ == "__main__":
    unittest.main()

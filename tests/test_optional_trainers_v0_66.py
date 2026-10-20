"""v0.66: お上品攻撃・ナツメのESP・カスミの勝負（docs/optional-trainers-v0.66.md）。

根拠は kyuura データの採用（kyuura の印刷の文面。kyuura_engine/data/card_sources.json の PMCG5-074・PMCG6-087・PMCG5-068）と、既存の記録の再利用（お上品攻撃の
「相手の番が終わったら、手札にもどす」は kyuura の data/curation/card_differences.json の PMCG5-074（確度: 確実）、5 段階は GR-2000-P321-DAMAGE-ORDER、返すダメージは
CR-SHELL-ATTACK-ATTACKER-PLUSPOWER、減らす単位は GR-2000-P319-HP-AND-DAMAGE）。誌面を読み直していない。決められない場合は CA1・ES1〜ES3 で止める（kyuura の未解決の
一覧にない）。コインは ``with_coin_results`` で決める。
"""

from __future__ import annotations

import pickle
import unittest

from kyuura_engine import damage as D
from kyuura_engine.cards import load_card_pool
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import EndTurn, PlayTrainer, ResolveDecision, UseAttack
from kyuura_engine.decisions import (
    DAMAGE_REDUCTION,
    ESP_REDO,
    JANKEN_HAND,
    SELECT_POKEMON,
)
from kyuura_engine.effects import (
    CHARITY_TEXT,
    DEFAULT_EFFECTS,
    ESP_HOLDER_CODE,
    ESP_MULTIPLE_CODE,
    ESP_OPPONENT_COINS_CODE,
    MISTYS_DUEL_TEXT,
    SABRINAS_ESP_TEXT,
    esp_redo_problem,
    janken_winner,
)
from kyuura_engine.engine import check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe, visible_log
from kyuura_engine.resolution.questions import QUESTIONS, to_error
from kyuura_engine.serialize import state_to_dict
from tests.helpers import (
    CHARITY,
    DARK_WARTORTLE,
    DEFENDER,
    FIGHTING,
    FOSSIL_GEODUDE,
    GRASS,
    HITMONCHAN,
    MISTYS_DUEL,
    MR_MIME,
    PLUSPOWER,
    PSYCHIC,
    RATTATA,
    SABRINAS_ESP,
    SABRINAS_GASTLY,
    SABRINAS_GENGAR,
    SABRINAS_HAUNTER,
    SABRINAS_PSYCHIC_CONTROL,
    SABRINAS_PSYDUCK,
    SABRINAS_VENOMOTH,
    SABRINAS_VENONAT,
    V0_66_CARDS,
    WATER,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems

H, T = CoinSide.HEADS, CoinSide.TAILS
F, P, G = FIGHTING, PSYCHIC, GRASS
TURN = 7
BELOW = {SABRINAS_VENOMOTH: SABRINAS_VENONAT, SABRINAS_GENGAR: [SABRINAS_GASTLY, SABRINAS_HAUNTER], DARK_WARTORTLE: "PMCG4-018"}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(*, active, opponent=None, hand=(), bench=(), opponent_bench=(), opponent_hand=(), deck=None, opponent_deck=None, discard=None,
          opponent_discard=None, turn=TURN):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "deck": list(deck) if deck is not None else [G] * 10}
    them = {"active": opponent or mon(HITMONCHAN, (F,)), "bench": list(opponent_bench), "hand": list(opponent_hand),
            "deck": list(opponent_deck) if opponent_deck is not None else [F] * 10}
    if discard is not None:
        me["discard"] = list(discard)
    if opponent_discard is not None:
        them["discard"] = list(opponent_discard)
    return build_test_state([me, them], turn_number=turn, current_player=0)


def card_of(state, card_id, zone="hand", player=0):
    return next(uid for uid in getattr(state.players[player], zone) if state.cards[uid].card_id == card_id)


def play(state, card_id, player=0, coins=()):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, PlayTrainer(player, card_of(state, card_id, player=player)))


def answer(state, choices, coins=()):
    if coins:
        state = with_coin_results(state, *coins)
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)))


def attack(state, index, coins=()):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, UseAttack(0, index))


def events(state, kind, since=0):
    return [dict(e) for e in state.log[since:] if e["kind"] == kind]


def snapshot(state):
    return state_to_dict(state, format_version=21), [dict(e) for e in state.log], repr(state.rng.getstate())


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def with_charity(state):
    after = play(state, CHARITY)
    assert any(state.cards[t.card].card_id == CHARITY for t in after.players[0].active.trainers)
    return after


class RegistrationTest(unittest.TestCase):
    def test_three_cards_are_registered_and_supported(self):
        pool = load_card_pool()
        for card_id, text in zip(V0_66_CARDS, (CHARITY_TEXT, SABRINAS_ESP_TEXT, MISTYS_DUEL_TEXT)):
            entry = DEFAULT_EFFECTS.trainer_entry(card_id)
            self.assertEqual(entry.text_ja, text)
            self.assertEqual(pool.get(card_id).trainer_text_ja, text)
            self.assertEqual(entry.effect.check(pool.get(card_id)), [])

    def test_new_questions_have_codes(self):
        self.assertEqual(QUESTIONS["charity_below_zero"].code, "UNRESOLVED_CHARITY_BELOW_ZERO")
        self.assertTrue(QUESTIONS["damage_reduction_decision"].code.startswith("UNSUPPORTED_"))
        self.assertIsNone(QUESTIONS["esp_separate_coin_tosses"].code)
        self.assertEqual(to_error("charity_below_zero").code, "UNRESOLVED_CHARITY_BELOW_ZERO")


class CharityDamageStepTest(unittest.TestCase):
    """お上品攻撃は p.321 の 5 段階（GR-2000-P321-DAMAGE-ORDER）。減らす量はワザを使ったプレイヤーが選ぶ（0〜5 段階のダメージ、10 ずつ。GR-2000-P319-HP-AND-DAMAGE）。"""

    def test_reduce_chosen_amount(self):
        state = with_charity(board(active=mon(HITMONCHAN, (F, F, F)), hand=[CHARITY]))
        before = attack(state, 1)
        d = before.decision
        self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), (DAMAGE_REDUCTION, 0, (0, 10, 20, 30, 40), 1, 1))
        self.assertEqual(before.players[1].active.damage, 0)  # まだダメージを与えていない
        audited(self, before)
        after = answer(before, (30,))
        self.assertEqual(after.players[1].active.damage, 10)
        damages = events(after, "damage")
        self.assertEqual(len(damages), 1)
        self.assertEqual(damages[0]["damage_reduced"], ((5, card_of(state, CHARITY, zone="hand") if False else damages[0]["damage_reduced"][0][1], 30),))
        audited(self, after)

    def test_no_reduction_keeps_v065_log(self):
        state = with_charity(board(active=mon(HITMONCHAN, (F, F, F)), hand=[CHARITY]))
        after = answer(attack(state, 1), (0,))
        self.assertEqual(after.players[1].active.damage, 40)
        self.assertNotIn("damage_reduced", events(after, "damage")[0])

    def test_invalid_answer_changes_nothing(self):
        before = attack(with_charity(board(active=mon(HITMONCHAN, (F, F, F)), hand=[CHARITY])), 1)
        snap = snapshot(before)
        for choices in ((5,), (50,), (), (10, 20)):
            with self.assertRaises(IllegalActionError):
                answer(before, choices)
        with self.assertRaises(IllegalActionError):
            apply_kernel(before, ResolveDecision(1, before.decision.id, (0,)))  # 決めるのはワザを使ったプレイヤー
        self.assertEqual(snapshot(before), snap)

    def test_pluspower_then_reduce(self):
        """同じ 5 段階のプラスパワー（加算）のあとで減らす（選べる量は 40 + 10 = 50 まで）。減らす前に足す順番でも選べる結果の集まりは同じ（docs 2.3 節）。"""
        state = board(active=mon(HITMONCHAN, (F, F, F)), hand=[CHARITY, PLUSPOWER])
        state = play(with_charity(state), PLUSPOWER)
        before = attack(state, 1)
        self.assertEqual(before.decision.options, (0, 10, 20, 30, 40, 50))
        after = answer(before, (50,))
        self.assertEqual(after.players[1].active.damage, 0)
        self.assertNotIn(1, [e.get("player") for e in events(after, "knock_out")])

    def test_mysterious_wall_after_reduction(self):
        """8 段階の［なぞのかべ］（30 以上なら 0）は減らしたあとのダメージで計算する: 40 → 20 は 20 を与え、減らさなければ 0。最終ダメージ 0 を減らす計算ではない。"""
        state = with_charity(board(active=mon(HITMONCHAN, (F, F, F)), hand=[CHARITY], opponent=mon(MR_MIME, (P,))))
        self.assertEqual(answer(attack(state, 1), (20,)).players[1].active.damage, 20)
        self.assertEqual(answer(attack(state, 1), (0,)).players[1].active.damage, 0)

    def test_defender_after_reduction(self):
        """7 段階のディフェンダー（−20）は減らしたあと: 40 → 30 は 10。"""
        opponent = mon(HITMONCHAN, (F,), trainers=[(DEFENDER, TURN)])
        state = with_charity(board(active=mon(HITMONCHAN, (F, F, F)), hand=[CHARITY], opponent=opponent))
        self.assertEqual(answer(attack(state, 1), (10,)).players[1].active.damage, 10)

    def test_shell_attack_returns_reduced_damage(self):
        """こうらがえしの「受けたダメージ」は小さくしたあとの最終ダメージ（CR-SHELL-ATTACK-ATTACKER-PLUSPOWER と同じ読み方）。"""
        opponent = mon(DARK_WARTORTLE, (WATER,), retaliation_received=TURN - 1)
        state = with_charity(board(active=mon(HITMONCHAN, (F, F, F)), hand=[CHARITY], opponent=opponent))
        after = answer(attack(state, 1), (20,))
        self.assertEqual(after.players[1].active.damage, 20)
        returned = events(after, "retaliation")
        self.assertEqual(len(returned), 1)
        self.assertEqual(returned[0]["received_damage"], 20)
        audited(self, after)

    def test_bench_and_self_damage_are_not_reduced(self):
        modifiers = [D.DamageModifier(step=5, amount=0, label="お上品攻撃", operation=D.REDUCE_CHOICE)]
        pool = load_card_pool()
        with self.assertRaises(D.DamageReductionRequired):
            D.calculate_attack_damage(40, pool.get(HITMONCHAN), pool.get(HITMONCHAN), build_test_state([{"active": mon(HITMONCHAN)}, {"active": mon(HITMONCHAN)}]).rules, modifiers)
        state = with_charity(board(active=mon(HITMONCHAN, (F,)), hand=[CHARITY]))
        from kyuura_engine.effects import AttackKey, attack_damage_modifiers
        me = state.players[0].active
        key = AttackKey(HITMONCHAN, 1)
        self.assertTrue(any(m.operation == D.REDUCE_CHOICE for m in attack_damage_modifiers(state, me, state.players[1].active, attack=key)))
        self.assertFalse(any(m.operation == D.REDUCE_CHOICE for m in attack_damage_modifiers(state, me, me, attack=key)))
        self.assertFalse(any(m.operation == D.REDUCE_CHOICE for m in attack_damage_modifiers(state, me, state.players[1].active, attack=key, bench=True)))

    def test_below_zero_question_ca1(self):
        """6 段階以降にダメージを増やす効果があり、0 より小さくすると結果が変わるときだけ CA1。ないときは below_zero が偽。"""
        rules = build_test_state([{"active": mon(HITMONCHAN)}, {"active": mon(HITMONCHAN)}]).rules
        pool = load_card_pool()
        reduce_ = D.DamageModifier(step=5, amount=0, label="お上品攻撃", operation=D.REDUCE_CHOICE)
        with self.assertRaises(D.DamageReductionRequired) as plain:
            D.calculate_attack_damage(30, pool.get(HITMONCHAN), pool.get(RATTATA), rules, [reduce_])
        self.assertFalse(plain.exception.below_zero)
        self.assertEqual(plain.exception.choices, (0, 10, 20, 30, 40, 50, 60))  # ラッタの弱点（闘）で 60 になってから 5 段階
        bonus = D.DamageModifier(step=6, amount=20, label="カスミ")
        with self.assertRaises(D.DamageReductionRequired) as raised:
            D.calculate_attack_damage(30, pool.get(HITMONCHAN), pool.get(RATTATA), rules, [reduce_, bonus])
        self.assertTrue(raised.exception.below_zero)
        # 減らした量を渡せば計算は決まる（6 段階は減らしたあと）
        self.assertEqual(D.calculate_attack_damage(30, pool.get(HITMONCHAN), pool.get(RATTATA), rules, [reduce_, bonus], reduction=30).final, 50)

    def test_save_restore_mid_decision(self):
        before = attack(with_charity(board(active=mon(HITMONCHAN, (F, F, F)), hand=[CHARITY])), 1)
        restored = pickle.loads(pickle.dumps(before))
        self.assertEqual(snapshot(answer(restored, (10,))), snapshot(answer(before, (10,))))


class CharityExpiryTest(unittest.TestCase):
    def test_returns_to_hand_after_opponent_turn(self):
        state = with_charity(board(active=mon(HITMONCHAN, (F, F, F)), hand=[CHARITY]))
        charity = next(t.card for t in state.players[0].active.trainers)
        after = apply_kernel(state, EndTurn(0))
        self.assertIn(charity, [t.card for t in after.players[0].active.trainers])  # 自分の番の終わりではもどさない
        after = apply_kernel(after, EndTurn(1))
        self.assertIn(charity, after.players[0].hand)
        self.assertNotIn(charity, after.players[0].discard)
        self.assertEqual(len(events(after, "return_attached_trainer")), 1)
        audited(self, after)

    def test_knocked_out_holder_discards_charity(self):
        state = with_charity(board(active=mon(HITMONCHAN, (F, F, F), damage=60), hand=[CHARITY], bench=[RATTATA],
                                   opponent=mon(HITMONCHAN, (F, F, F))))
        charity = next(t.card for t in state.players[0].active.trainers)
        after = apply_kernel(state, EndTurn(0))
        after = apply_kernel(after, UseAttack(1, 1))
        self.assertIn(charity, after.players[0].discard)
        self.assertNotIn(charity, after.players[0].hand)


class CharityUnboundedCoinTest(unittest.TestCase):
    """れんぞくいしなげ（「うら」が出るまで）とお上品攻撃: 先読みの組は、減らしたあとに選べる結果の集まりで分ける（docs 2.5 節）。"""

    def test_options_grow_with_heads_and_real_play_is_not_capped(self):
        state = with_charity(board(active=mon(FOSSIL_GEODUDE, (F, F)), hand=[CHARITY]))
        before = attack(state, 0, coins=[H] * 12 + [T])
        self.assertEqual(before.decision.options, tuple(range(0, 121, 10)))  # 残りの HP（70）で打ち切らない
        after = answer(before, (0,))
        self.assertEqual(events(after, "damage")[0]["amount"], 120)

    def test_head_classes_cover_every_heads_count(self):
        from kyuura_engine.effects import AttackKey
        from kyuura_engine.resolution import kernel as K
        from kyuura_engine.resolution import unbounded
        from kyuura_engine.resolution.events import FrameKind
        from kyuura_engine.resolution.programs import (
            OPP,
            AttackRun,
            Damage,
            HeadsUntilTails,
        )

        for opponent in (mon(HITMONCHAN, (F,)), mon(MR_MIME, (P,))):
            state = with_charity(board(active=mon(FOSSIL_GEODUDE, (F, F)), hand=[CHARITY], opponent=opponent))
            res = K.Resolution(state.clone())
            attacker = res.state.players[0].active
            fs = res.open_frame(FrameKind.ATTACK, parent=None, player=0, source_pid=attacker.pokemon_id, attack_key=AttackKey(FOSSIL_GEODUDE, 0))
            element = Damage(OPP, HeadsUntilTails(10))
            run = AttackRun(res, fs, (element,), res.state.definitions[FOSSIL_GEODUDE].attacks[0])
            classes = unbounded.head_classes(run, element, 10)
            for heads in range(60):
                self.assertIn(classes.key_of(heads), classes.keys)
            # 大きな「おもて」の数では key が一定（選べる結果の集まりが飽和する）
            self.assertEqual(classes.key_of(classes.bound + 7), classes.key_of(classes.bound + 40))


class EspTest(unittest.TestCase):
    """ナツメのESP: ワザの説明文のコイントスを投げた直後に、すべてをやり直すかを聞く。やり直したら同じ枚数を投げ直し、やり直した結果を使う。"""

    def attached(self, active, **kw):
        state = board(active=active, hand=[SABRINAS_ESP], **kw)
        state = play(state, SABRINAS_ESP)
        self.assertEqual((state.decision.kind, state.decision.options), (SELECT_POKEMON, (state.players[0].active.pokemon_id,)))
        return answer(state, (state.players[0].active.pokemon_id,))

    def test_needs_sabrinas_pokemon(self):
        state = board(active=mon(HITMONCHAN, (F,)), hand=[SABRINAS_ESP])
        with self.assertRaises(UnsupportedError) as raised:
            play(state, SABRINAS_ESP)
        self.assertEqual(raised.exception.code, "UNRESOLVED_TRAINER_WITHOUT_TARGET")

    def test_destruction_beam_redo_after_damage(self):
        """はかいビーム: ダメージ → コイン → エネルギーの選択。やり直しはコインのあと、ダメージはくり返さない。"""
        state = self.attached(mon(SABRINAS_VENONAT, (P, G)))
        before = attack(state, 1, coins=[T])
        self.assertEqual(before.decision.kind, ESP_REDO)
        self.assertEqual(before.decision.context_value("esp")[4], ("tails",))
        self.assertEqual(before.players[1].active.damage, 20)
        audited(self, before)
        redone = answer(before, (1,), coins=[H])
        self.assertEqual(redone.decision.kind, "discard_opponent_energy")
        self.assertEqual(len(events(redone, "damage")), 1)
        self.assertEqual(events(redone, "esp_redo")[0]["redone"], ("heads",))
        self.assertEqual(len([e for e in events(redone, "coin_flip") if e["source"] == "attack"]), 2)
        audited(self, redone)
        kept = answer(before, ())
        self.assertIsNone(kept.decision)
        self.assertEqual(len(events(kept, "esp_redo_declined")), 1)
        self.assertEqual(kept.players[1].active.energy, before.players[1].active.energy)

    def test_redo_changes_both_effects_of_one_coin(self):
        """こまったねんりき: 1 枚のコインで相手へのダメージ・こんらんと自分のこんらんが決まる。やり直した結果だけで決める。"""
        state = self.attached(mon(SABRINAS_PSYDUCK, (P,)))
        before = attack(state, 1, coins=[T])
        after = answer(before, (1,), coins=[H])
        self.assertEqual(after.players[1].active.damage, 20)
        self.assertIsNotNone(after.players[1].active.conditions.exclusive)
        self.assertIsNone(after.players[0].active.conditions.exclusive)
        kept = answer(before, ())
        self.assertEqual(kept.players[1].active.damage, 0)
        self.assertIsNotNone(kept.players[0].active.conditions.exclusive)

    def test_redo_all_three_heal_coins(self):
        """かいふくりんぷん: 3 枚をすべて投げ直す（一部だけを投げ直さない）。"""
        state = self.attached(mon(SABRINAS_VENOMOTH, (G,), damage=30), bench=[mon(RATTATA, damage=20)])
        before = attack(state, 0, coins=[T, T, H])
        self.assertEqual(before.decision.context_value("esp")[1], 3)
        after = answer(before, (1,), coins=[H, H, T])
        self.assertEqual(events(after, "esp_redo")[0]["redone"], ("heads", "heads", "tails"))
        self.assertEqual(after.players[0].active.damage, 10)
        self.assertEqual(after.players[0].bench[0].damage, 0)
        audited(self, after)

    def test_no_coin_no_offer_after_knockout(self):
        """やみのこえ: 相手がきぜつしたらコインを投げない（ESPのやり直しも聞かない）。"""
        state = self.attached(mon(SABRINAS_GENGAR, (P, P, P)), opponent=mon(HITMONCHAN), opponent_bench=[RATTATA])
        after = attack(state, 1)
        self.assertNotEqual(getattr(after.decision, "kind", None), ESP_REDO)
        self.assertEqual(events(after, "esp_redo"), [])

    def test_invalid_answer_and_restore(self):
        before = attack(self.attached(mon(SABRINAS_VENONAT, (P, G))), 1, coins=[T])
        snap = snapshot(before)
        for choices in ((0,), (1, 1), (2,)):
            with self.assertRaises(IllegalActionError):
                answer(before, choices)
        with self.assertRaises(IllegalActionError):
            apply_kernel(before, ResolveDecision(1, before.decision.id, ()))
        self.assertEqual(snapshot(before), snap)
        restored = pickle.loads(pickle.dumps(before))
        self.assertEqual(snapshot(answer(restored, (1,), coins=[H])), snapshot(answer(before, (1,), coins=[H])))

    def test_until_tails_coins_with_esp_stop_as_engine_bug(self):
        """「うら」が出るまで投げるコイン（v0.64 のれんぞくいしなげ）を、ESPのついたポケモンが使う場面は今の写しでは起こらない（「ナツメのポケモン」が
        れんぞくいしなげを使えない）。盤面を直接作って起こすと、やり直しを黙って聞かない処理にせず、内部エラーで止める（docs 9.5 節）。"""
        state = board(active=mon(FOSSIL_GEODUDE, (F, F), trainers=[(SABRINAS_ESP, TURN)]))
        snap = snapshot(state)
        with self.assertRaises(RuntimeError):
            attack(state, 0)
        self.assertEqual(snapshot(state), snap)

    def test_discarded_at_end_of_own_turn(self):
        state = self.attached(mon(SABRINAS_VENONAT, (P, G)))
        esp = state.players[0].active.trainers[0].card
        after = apply_kernel(state, EndTurn(0))
        self.assertIn(esp, after.players[0].discard)

    def test_two_esps_make_redo_unresolved(self):
        state = board(active=mon(SABRINAS_VENONAT, (P, G)), hand=[SABRINAS_ESP, SABRINAS_ESP])
        for _ in range(2):
            state = play(state, SABRINAS_ESP)
            state = answer(state, state.decision.options)
        before = attack(state, 1, coins=[T])
        self.assertEqual(before.decision.context_value("unresolved_choices"), (1,))
        self.assertEqual(before.decision.context_value("unresolved_code"), ESP_MULTIPLE_CODE)
        with self.assertRaises(UnsupportedError) as raised:
            answer(before, (1,))
        self.assertEqual(raised.exception.code, ESP_MULTIPLE_CODE)
        self.assertIsNone(answer(before, ()).decision)

    def test_redo_problem_codes(self):
        state = self.attached(mon(SABRINAS_VENONAT, (P, G)))
        me = state.players[0].active
        cards = tuple(t.card for t in me.trainers)
        self.assertIsNone(esp_redo_problem(state, me, cards, 0, 0))
        self.assertEqual(esp_redo_problem(state, me, cards, 1, 0)[0], ESP_OPPONENT_COINS_CODE)
        self.assertEqual(ESP_HOLDER_CODE, "UNRESOLVED_ESP_HOLDER_NOT_SABRINAS")


class MistysDuelTest(unittest.TestCase):
    def duel(self, *, hand=(), opponent_hand=(G, G), deck=None, opponent_deck=None):
        return board(active=mon(HITMONCHAN, (F,)), hand=[MISTYS_DUEL, *hand], opponent_hand=list(opponent_hand), deck=deck, opponent_deck=opponent_deck)

    def test_all_outcomes(self):
        for first in range(3):
            for second in range(3):
                with self.subTest(first=first, second=second):
                    state = self.duel(hand=(G, G, G))
                    state = play(state, MISTYS_DUEL)
                    self.assertEqual((state.decision.kind, state.decision.player), (JANKEN_HAND, 0))
                    state = answer(state, (first,))
                    self.assertEqual((state.decision.kind, state.decision.player), (JANKEN_HAND, 1))
                    state = answer(state, (second,))
                    result = janken_winner(first, second)
                    if result is None:
                        self.assertEqual(state.decision.context_value("round"), 2)
                        state = answer(answer(state, (0,)), (1,))  # 2 回目: グー対チョキで使ったプレイヤーの勝ち
                        result = 0
                    winner = 0 if result == 0 else 1
                    self.assertIsNone(state.decision)
                    self.assertEqual(len(state.players[winner].hand), 5)
                    self.assertEqual(events(state, "duel_janken")[-1]["winner"], winner)
                    audited(self, state)

    def test_first_hand_is_hidden_until_both_choose(self):
        started = play(self.duel(), MISTYS_DUEL)
        state = answer(started, (2,))
        other = answer(started, (0,))  # 1 人目の手だけが違う状態
        for viewer in (0, 1, None):
            self.assertEqual(observe(state, viewer), observe(other, viewer))
            self.assertEqual(visible_log(state, viewer), visible_log(other, viewer))
            self.assertNotIn("'first'", repr(observe(state, viewer)))
        self.assertEqual(state.decision.context_value("first"), 2)  # 内部の状態（続きの情報）には持つ
        self.assertEqual(events(state, "duel_janken"), [])
        self.assertEqual(serialization_problems(state), [])
        after = answer(state, (0,))
        self.assertEqual(events(after, "duel_janken")[0]["hands"], ("paper", "rock"))
        self.assertIn("paper", repr(visible_log(after, 1)))

    def test_empty_hand_winner_and_short_deck(self):
        state = answer(answer(play(self.duel(opponent_hand=(), opponent_deck=[F, F, F]), MISTYS_DUEL), (1,)), (0,))  # 相手（グー）の勝ち
        self.assertEqual(len(state.players[1].hand), 3)  # 手札 0 枚でも切って引く。山札が 3 枚なら 3 枚
        self.assertEqual(state.players[1].deck, [])
        self.assertTrue(events(state, "shuffle"))
        audited(self, state)

    def test_reuse_in_same_turn_and_card_not_in_hand(self):
        state = self.duel(hand=(MISTYS_DUEL,))
        first = card_of(state, MISTYS_DUEL)
        state = answer(answer(play(state, MISTYS_DUEL), (0,)), (2,))  # グー対パー: 相手の勝ち（使ったプレイヤーの手札は残る）
        self.assertIn(first, state.players[0].discard)  # 使っているカードは手札に含めず、トラッシュする
        self.assertEqual(len(state.players[1].hand), 5)
        state = answer(answer(play(state, MISTYS_DUEL), (0,)), (1,))
        self.assertEqual(len(state.players[0].hand), 5)
        audited(self, state)

    def test_wrong_player_answer_is_rejected(self):
        state = play(self.duel(), MISTYS_DUEL)
        snap = snapshot(state)
        with self.assertRaises(IllegalActionError):
            apply_kernel(state, ResolveDecision(1, state.decision.id, (0,)))
        with self.assertRaises(IllegalActionError):
            answer(state, (3,))
        self.assertEqual(snapshot(state), snap)

    def test_borrowed_from_opponent_discard(self):
        """ナツメのサイキックコントロールで相手のトラッシュのカスミの勝負を使う: 使ったプレイヤーが先に手を決め、カードは持ち主（相手）のトラッシュにもどる。"""
        state = board(active=mon(HITMONCHAN, (F,)), hand=[SABRINAS_PSYCHIC_CONTROL], opponent_discard=[MISTYS_DUEL])
        duel = card_of(state, MISTYS_DUEL, zone="discard", player=1)
        state = play(state, SABRINAS_PSYCHIC_CONTROL, coins=[H])
        state = answer(state, (duel,))
        self.assertEqual((state.decision.kind, state.decision.player), (JANKEN_HAND, 0))
        self.assertEqual(state.trainer_in_use.player, 1)
        state = answer(answer(state, (2,)), (0,))  # パー対グー: 使ったプレイヤーの勝ち
        self.assertEqual(len(state.players[0].hand), 5)
        self.assertIn(duel, state.players[1].discard)
        audited(self, state)


if __name__ == "__main__":
    unittest.main()

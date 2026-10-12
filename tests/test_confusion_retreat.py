"""こんらん状態のポケモンの「にげる」（v0.3c）。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES。rule_differences.json の
confusion_retreat の「2000年2月」の行）:

- pp.310〜311「バトル場にいる対戦ポケモンをにがす」の手順: 1「対戦ポケモンが「にげる」ことを宣言します」2「…「にげるときに
  トラッシュするエネルギーの数」ぶんのエネルギーを…選んで、トラッシュします。トラッシュできないときは、「にげる」を宣言する
  ことはできません」3「「にげる」をおこなうポケモンがこんらん状態なら、それによって「にげる」が失敗するかどうかを以下のように
  チェックします」「「にげる」を宣言したポケモン側のプレイヤーは、コインを1枚投げます。「うら」なら、「にげる」は失敗です」
  「「にげる」が失敗したからといって、トラッシュしたエネルギーカードを取り戻すことはできません」4「自分の控えポケモンを1匹
  選び、対戦ポケモンと入れ替えます」「「にげる」が失敗したとき、この入れ替えをおこなってはいけません」
- p.311: 「自分のベンチに控えポケモンがいないときには、「にげる」を宣言することはできません」「「にげる」の宣言は、1回の自分の
  番の中で、何度でもすることができます」「1匹のポケモンが何回「にげる」を宣言してもかまいません」「一度「にげる」に失敗した
  こんらん状態のポケモンは、今の自分の番では、もう「にげる」を宣言することができません」「次の自分の番になれば、再び「にげる」を
  宣言することができます」「ベンチに戻ったら、そのポケモンの「どく」「ねむり」「マヒ」「こんらん」状態や、「持続する効果」は、
  すべて消えてなくなります」
- p.325「21 ポケモンの入れ替え」: ポケモンいれかえは「にげる」ではない

分類（CONFIRMED・SUPPORTED・UNRESOLVED）は docs/retreat-confusion-v0.3c.md。
"""

import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, EngineError, IllegalActionError, Phase, PlayTrainer, ResolveDecision, Retreat, UnsupportedError,
    UseAttack, apply_command, check_invariants, state_to_dict,
)
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import CONFUSED, NO_SPECIAL_CONDITIONS, Poison, SpecialConditions

from tests.helpers import (
    BILL, DIGLETT, FIGHTING, FIRE, GROWLITHE, H, HITMONCHAN, PLUSPOWER, PONYTA, RATTATA, SWITCH, T, VULPIX,
    build_test_state, with_coin_results,
)


def full(state):
    return state_to_dict(state, format_version=6)


def kinds(events):
    return [e["kind"] for e in events]


def hand(state, player, card_id):
    return [u for u in state.players[player].hand if state.cards[u].card_id == card_id]


def confused(*sides, card=VULPIX, energy=(FIRE, FIRE), bench=(PONYTA, GROWLITHE), hand_cards=(), poisoned=False, deck=None):
    """プレイヤー 0（3 番の番）の対戦ポケモン ``card`` がこんらん状態。控えはポニータ・ガーディ。"""
    spec = {"card": card, "energy": list(energy), "confusion": True}
    if poisoned:
        spec["poison"] = 10
    player0 = {"active": spec, "bench": list(bench), "hand": list(hand_cards)}
    if deck is not None:
        player0["deck"] = list(deck)
    state = build_test_state([player0, {"active": GROWLITHE, "bench": [RATTATA]}])
    return with_coin_results(state, *sides) if sides else state


def retreat(state, count=None, player=0, to=0):
    """対戦ポケモンについているエネルギーの先頭 ``count`` 枚（省略時はにげるエネルギーの数）をトラッシュして、控えの ``to`` 番目と入れ替える。"""
    p = state.players[player]
    if count is None:
        count = state.card_def(p.active.card).retreat_cost
    command = Retreat(player, tuple(p.active.energy[:count]), p.bench[to].card)
    start = len(state.log)
    new = apply_command(state, command)
    return new, [dict(e) for e in new.log[start:]]


def assert_unchanged_rejection(test, state, command, code, error=EngineError):
    before, fingerprint = full(state), rng_fingerprint(state.rng)
    with test.assertRaises(error) as ctx:
        apply_command(state, command)
    test.assertEqual(ctx.exception.code, code)
    test.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))


def switch_to(state, pokemon_id, player=0):
    state = apply_command(state, PlayTrainer(player, hand(state, player, SWITCH)[0]))
    return apply_command(state, ResolveDecision(player, state.decision.id, (pokemon_id,)))


# ---------------------------------------------------------------- コインと結果（7 章）


class ConfusedRetreatTest(unittest.TestCase):
    def test_heads_retreats(self):
        """エネルギーをトラッシュ → コイン → 「おもて」なら入れ替える。ベンチに戻ったポケモンのこんらんは消える（p.311）。番は続く。"""
        state = confused(H)
        vulpix, ponyta = state.players[0].active, state.players[0].bench[0]
        energy = vulpix.energy[0]
        new, events = retreat(state)
        self.assertEqual(kinds(events), ["coin_flip", "confusion_check", "retreat", "special_conditions_removed"])
        flip, check = events[0], events[1]
        self.assertEqual({k: flip[k] for k in ("player", "source", "effect", "card", "pokemon_id", "count", "result")},
                         {"player": 0, "source": "confusion", "effect": "retreat", "card": vulpix.card,
                          "pokemon_id": vulpix.pokemon_id, "count": 1, "result": "heads"})
        self.assertEqual({k: check[k] for k in ("player", "pokemon", "pokemon_id", "action", "result", "succeeded")},
                         {"player": 0, "pokemon": vulpix.card, "pokemon_id": vulpix.pokemon_id, "action": "retreat",
                          "result": "heads", "succeeded": True})
        self.assertEqual((events[2]["discarded"], events[2]["old_active"], events[2]["new_active"]), ((energy,), vulpix.card, ponyta.card))
        self.assertIs(new.players[0].active, new.find_pokemon(ponyta.pokemon_id)[1])
        back = new.find_pokemon(vulpix.pokemon_id)[1]
        self.assertEqual((back.conditions, back.retreat_failed_turn), (NO_SPECIAL_CONDITIONS, None))
        self.assertIn(energy, new.players[0].discard)
        self.assertEqual((new.phase, new.current_player), (Phase.MAIN, 0))
        self.assertEqual(check_invariants(new), [])

    def test_tails_fails_and_keeps_the_trashed_energy_in_the_discard(self):
        """「うら」なら失敗: トラッシュしたエネルギーは取り戻せず、入れ替えない。こんらん・ダメージはそのまま。番は続く。"""
        state = confused(T, poisoned=True)
        vulpix = state.players[0].active
        energy, remaining = vulpix.energy[0], vulpix.energy[1:]
        new, events = retreat(state)
        self.assertEqual(kinds(events), ["coin_flip", "confusion_check", "retreat_failed"])
        self.assertFalse(events[1]["succeeded"])
        failed = events[2]
        self.assertEqual({k: failed[k] for k in ("player", "pokemon", "pokemon_id", "discarded")},
                         {"player": 0, "pokemon": vulpix.card, "pokemon_id": vulpix.pokemon_id, "discarded": (energy,)})
        active = new.players[0].active
        self.assertEqual(active.pokemon_id, vulpix.pokemon_id)
        self.assertEqual(active.energy, list(remaining))
        self.assertEqual(new.players[0].discard[-1], energy)
        self.assertEqual(active.conditions, SpecialConditions(poison=Poison(10), exclusive=CONFUSED))
        self.assertEqual(active.retreat_failed_turn, 3)
        self.assertEqual([p.card for p in new.players[0].bench], [p.card for p in state.players[0].bench])
        self.assertEqual((new.phase, new.current_player, new.turn_number), (Phase.MAIN, 0, 3))
        self.assertEqual(check_invariants(new), [])

    def test_retreat_costs_zero_one_and_two(self):
        """にげるエネルギーが 0 でもコインを投げる（手順 3 に例外はない）。2 なら 2 枚とも失われる。"""
        for card, energy, cost in ((DIGLETT, (), 0), (VULPIX, (FIRE,), 1), (HITMONCHAN, (FIGHTING, FIGHTING, FIGHTING), 2)):
            for side in (H, T):
                with self.subTest(card=card, side=side):
                    state = confused(side, card=card, energy=energy)
                    discard_before = len(state.players[0].discard)
                    new, events = retreat(state)
                    self.assertEqual(kinds(events)[:2], ["coin_flip", "confusion_check"])
                    self.assertEqual(len(new.players[0].discard) - discard_before, cost)
                    self.assertEqual(new.players[0].active.card == state.players[0].active.card, side is T)
                    self.assertEqual(check_invariants(new), [])

    def test_not_confused_retreat_flips_no_coin(self):
        """こんらんでなければコインはない（v0.1 と同じ処理・ログ）。"""
        state = build_test_state([{"active": {"card": VULPIX, "energy": [FIRE]}, "bench": [PONYTA]}, {"active": GROWLITHE}])
        new, events = retreat(state)
        self.assertEqual(kinds(events), ["retreat"])
        self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(state.rng))

    def test_illegal_retreats_are_rejected_before_any_energy_or_coin(self):
        """宣言できない・エネルギーをトラッシュできない「にげる」は、エネルギーもコインも使わずに拒否する。"""
        state = confused(T)
        vulpix = state.players[0].active
        bench_card = state.players[0].bench[0].card
        no_bench = confused(T, bench=())
        cases = [
            (no_bench, Retreat(0, (no_bench.players[0].active.energy[0],), 999), "NO_BENCH"),
            (state, Retreat(0, (), bench_card), "WRONG_RETREAT_COST"),
            (state, Retreat(0, tuple(vulpix.energy), bench_card), "WRONG_RETREAT_COST"),
            (state, Retreat(0, (vulpix.energy[0], vulpix.energy[0]), bench_card), "DUPLICATE_CARD"),
            (state, Retreat(0, (state.players[1].active.card,), bench_card), "ENERGY_NOT_ATTACHED"),
            (state, Retreat(0, (vulpix.energy[0],), vulpix.card), "NOT_ON_BENCH"),
            (state, Retreat(1, (), state.players[1].bench[0].card), "NOT_YOUR_TURN"),
        ]
        for board, command, code in cases:
            with self.subTest(code=code, command=command):
                assert_unchanged_rejection(self, board, command, code)
        # にげるエネルギーが足りない（エビワラーはにげる 2、エネルギー 1）: トラッシュできないので宣言できない
        short = confused(T, card=HITMONCHAN, energy=(FIGHTING,))
        assert_unchanged_rejection(self, short, Retreat(0, tuple(short.players[0].active.energy), short.players[0].bench[0].card),
                                   "WRONG_RETREAT_COST")

    def test_pluspower_does_not_stop_retreat(self):
        """ダメージを変えるカードがついていても、「にげる」のコインにはダメージがないので止めない。カードもいっしょに移動する。"""
        state = confused(hand_cards=[PLUSPOWER])
        state = apply_command(state, PlayTrainer(0, hand(state, 0, PLUSPOWER)[0]))
        new, events = retreat(with_coin_results(state, H))
        self.assertEqual(kinds(events)[:3], ["coin_flip", "confusion_check", "retreat"])
        back = new.players[0].bench[0]
        self.assertEqual((back.card, len(back.trainers)), (state.players[0].active.card, 1))


# ---------------------------------------------------------------- 失敗したあと（7 章: 再宣言の制限）


class AfterFailureTest(unittest.TestCase):
    def failed(self, *more, **kwargs):
        state, _ = retreat(confused(T, *more, **kwargs))
        self.assertEqual(state.players[0].active.retreat_failed_turn, 3)
        return state

    def test_cannot_declare_again_this_turn(self):
        """「一度「にげる」に失敗したこんらん状態のポケモンは、今の自分の番では、もう「にげる」を宣言することができません」
        （p.311。CONFIRMED）。エネルギーが足りていても、コインの前に拒否する（状態も乱数も変えない）。"""
        state = self.failed(H)
        vulpix = state.players[0].active
        for to in (0, 1):
            command = Retreat(0, (vulpix.energy[0],), state.players[0].bench[to].card)
            assert_unchanged_rejection(self, state, command, "RETREAT_ALREADY_FAILED", IllegalActionError)

    def test_the_rest_of_the_turn_goes_on(self):
        """失敗しても番は終わらない。エネルギーをつける・トレーナーを使う・ワザを使う（こんらんのコインをもう一度投げる）ことはできる。"""
        state = self.failed(H, T, hand_cards=[FIRE, BILL])
        state = apply_command(state, AttachEnergy(0, hand(state, 0, FIRE)[0], state.players[0].active.card))
        state = apply_command(state, PlayTrainer(0, hand(state, 0, BILL)[0]))
        start = len(state.log)
        new = apply_command(state, UseAttack(0, 0))
        events = [dict(e) for e in new.log[start:]]
        self.assertEqual([(e["source"], e["effect"]) for e in events if e["kind"] == "coin_flip"][:1], [("confusion", "PMCG1-015#0")])
        self.assertEqual((new.current_player, new.turn_number), (1, 4))

    def test_record_is_cleared_at_the_end_of_turn_and_retreat_is_allowed_next_turn(self):
        """「次の自分の番になれば、再び「にげる」を宣言することができます」（p.311。CONFIRMED）。記録は番の終わりに消す。"""
        state = self.failed()
        state = apply_command(state, EndTurn(0))
        self.assertTrue(all(p.retreat_failed_turn is None for player in state.players for p in player.in_play()))
        state = apply_command(state, EndTurn(1))
        self.assertEqual((state.current_player, state.turn_number), (0, 5))
        self.assertTrue(state.players[0].active.conditions.confused)  # こんらんは自然には回復しない
        new, events = retreat(with_coin_results(state, H))
        self.assertEqual(kinds(events), ["coin_flip", "confusion_check", "retreat", "special_conditions_removed"])

    def test_failure_is_per_pokemon_not_per_player(self):
        """制限は失敗したポケモンにだけかかる（プレイヤー単位の「この番はもうにげられない」ではない）。ポケモンいれかえで
        控えと入れ替え（p.325。「にげる」ではないので制限されない）、新しい対戦ポケモンは「にげる」を宣言できる。"""
        state = self.failed(hand_cards=[SWITCH, FIRE])
        vulpix = state.players[0].active
        ponyta = state.players[0].bench[0]
        state = switch_to(state, ponyta.pokemon_id)
        back = state.find_pokemon(vulpix.pokemon_id)[1]
        self.assertEqual((back.conditions, back.retreat_failed_turn), (NO_SPECIAL_CONDITIONS, 3))  # 記録は番の終わりまで残る
        self.assertEqual(check_invariants(state), [])
        # ポニータ（にげる 1。こんらんではない）にエネルギーをつけて、ガーディと入れ替える
        state = apply_command(state, AttachEnergy(0, hand(state, 0, FIRE)[0], ponyta.card))
        new, events = retreat(state, to=1)
        self.assertEqual(kinds(events), ["retreat"])
        self.assertEqual(new.players[0].active.card, state.players[0].bench[1].card)

    def test_failed_pokemon_back_in_the_battle_field_is_unresolved(self):
        """失敗したあとにベンチに戻り（こんらんが消え）、同じ番にバトル場に戻ったポケモンが「にげる」を宣言できるかは
        原典で決められない（p.311 の「一度「にげる」に失敗したこんらん状態のポケモン」にこんらんでなくなったポケモンが含まれるか）。
        ``UnsupportedError``（UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED）で止める。状態も乱数も変えない。"""
        state = self.failed(hand_cards=[SWITCH, SWITCH])
        vulpix = state.players[0].active
        state = switch_to(state, state.players[0].bench[0].pokemon_id)
        state = switch_to(state, vulpix.pokemon_id)
        active = state.players[0].active
        self.assertEqual((active.pokemon_id, active.conditions, active.retreat_failed_turn), (vulpix.pokemon_id, NO_SPECIAL_CONDITIONS, 3))
        command = Retreat(0, (active.energy[0],), state.players[0].bench[0].card)
        assert_unchanged_rejection(self, state, command, "UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED", UnsupportedError)
        # 次の番には記録が消えるので、ふつうに「にげる」を宣言できる
        state = apply_command(apply_command(state, EndTurn(0)), EndTurn(1))
        new, events = retreat(state)
        self.assertEqual(kinds(events), ["retreat"])

    def test_switch_after_failure_is_allowed(self):
        """ポケモンいれかえは「にげる」ではない（p.325）ので、失敗のあとでも使える。こんらんは消え、コインは投げない。"""
        state = self.failed(hand_cards=[SWITCH])
        fingerprint = rng_fingerprint(state.rng)
        new = switch_to(state, state.players[0].bench[1].pokemon_id)
        self.assertEqual(rng_fingerprint(new.rng), fingerprint)
        self.assertEqual(new.players[0].active.card, state.players[0].bench[1].card)

    def test_serialization_of_the_record(self):
        """形式 6 だけが記録を書き出せる。形式 1〜5 は黙って落とさず ``ValueError``（形式 5 はこんらんを書けても記録は書けない）。"""
        state = self.failed()
        data = state_to_dict(state, format_version=6)
        self.assertEqual(data["players"][0]["active"]["retreat_failed_turn"], 3)
        self.assertEqual([b["retreat_failed_turn"] for b in data["players"][0]["bench"]], [None, None])
        for version in (1, 2, 3, 4, 5):
            with self.subTest(version=version), self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        after = apply_command(state, EndTurn(0))
        self.assertIn("confusion", state_to_dict(after, format_version=5)["players"][0]["active"]["special_conditions"])


if __name__ == "__main__":
    unittest.main()

"""カイリキー（ポケモンカード第1弾。PMCG1-057）のポケモンパワー「はんげき」（v0.10。docs/counterattack-v0.10.md の C1〜C43・A4）。

最新の説明（p.192）: 「このカードが相手のワザによってダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）ダメージを
与えたポケモンに、「弱点・抵抗力」に関係なく、10ダメージ。ダメージを受けるとき、すでにこのカードが「ねむり・マヒ・こんらん」状態
だったなら、この力は、はたらかない。」。p.192 の解説（相手の番に効果が発生する特殊能力・受けるたびに・ワザを使ったポケモンに）、p.89 の
「こうらがえし」のワザ解説（同じ形の発動条件のダメージを与えるタイミング: 相手のワザによるダメージの処理のあと、ダメージ以外の効果の
前。「そのダメージできぜつしなければ」あとの効果）、p.138・p.245 の同じ形の特殊能力の解説（特殊能力によるダメージ。ディフェンダーで
防げない・「ワザによるダメージ」を条件にする特殊能力をはたらかせない）、p.319（ダメージを与えたポケモン・0 ダメージ・どく）、
p.320（ダメージカウンターの移動）、p.321（8 ワザによるダメージと効果）、p.323（自動的にはたらく特殊能力・きぜつ）、p.324（同時のきぜつ）
にしたがう。

盤面は ``build_test_state`` で直接作る（1 つの規定を確かめるテスト）。自然な対戦は tests/test_machamp_games_v0_10.py、ワンリキー・
ゴーリキーのワザは tests/test_machamp_line_v0_10.py。乱数は、コインのログの数と、状態の乱数がいくつ進んだか（``rng_draws``）の両方で
確かめる（「はんげき」は乱数を使わない）。
"""

import copy
import dataclasses
import itertools
import pickle
import unittest
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS, EndTurn, EngineError, IllegalActionError, PowerKey, ResolveDecision, UnsupportedError, UseAttack,
    UsePokemonPower, apply_command, check_invariants, load_card_pool, state_to_dict, working_counterattack_power,
)
from kyuura_engine.conditions import POISON
from kyuura_engine.decisions import FORCED_SWITCH, push_attack_decision
from kyuura_engine.effects import (
    DAMAGE_ELEMENT, SELF, AttackEffect, AttackEntry, AttackKey, AttackUse, CoinFlipDamage, CoinHeadsDamagePerOwnCounter, CounterattackDamage,
    DamageProfile,
    attack_reaches, counterattack_power, deal_attack_damage, finish_damage_elements,
)
from kyuura_engine.resolution import catalog as C
from kyuura_engine.resolution import codec, open_attack, programs
from kyuura_engine.resolution.events import Window
from kyuura_engine.resolution.kernel import Deferred
from kyuura_engine.resolution.questions import OpenQuestion
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import Asleep, GameState, Phase

from tests.helpers import (
    ABRA, ALAKAZAM, BULBASAUR, BUTTERFREE, CATERPIE, DEFENDER, DIGLETT, DODUO, FIGHTING, FIRE, GASTLY, GIOVANNIS_MACHAMP, GRASS, GRIMER,
    H, HAUNTER, HITMONCHAN, KADABRA, LIGHTNING, MACHAMP, MACHOKE, MACHOP, METAPOD, MUK, PARAS, PIKACHU, PONYTA,
    PSYCHIC, RATTATA, T, WEEDLE, apply_kernel, build_test_state, coin_events, with_coin_results,
)
from tests.test_effect_preflight_v0_3d import ATTACKS, EVOLVED_FROM, energy_for
from tests.test_transparency_v0_9 import contextlib_exit, rng_draws

TURN = 7
STRIKES_BACK = PowerKey(MACHAMP, 0)
POWER = str(STRIKES_BACK)
LATEST = ("このカードが相手のワザによってダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）ダメージを与えたポケモンに、"
          "「弱点・抵抗力」に関係なく、10ダメージ。ダメージを受けるとき、すでにこのカードが「ねむり・マヒ・こんらん」状態だったなら、"
          "この力は、はたらかない。")
PRINTED = ("カイリキーがダメージをうけたときには、かならず10ダメージを相手にあたえる。このダメージは、弱点・抵抗力の影響を受けず、"
           "常に「10」である。「ねむり・マヒ・こんらん」状態のときにはつかえない。")


def machamp(**extra):
    return {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], **extra}


def board(attacker, defender=None, *, bench0=(), bench1=(), hand0=(), turn=TURN, effects=None):
    """プレイヤー 0（番のプレイヤー）がワザを使う。プレイヤー 1 のバトル場に、既定でカイリキー（はんげき）。"""
    return build_test_state([
        {"active": attacker, "bench": list(bench0) or [PONYTA], "hand": list(hand0)},
        {"active": defender or machamp(), "bench": list(bench1) or [RATTATA]},
    ], turn_number=turn, effects=effects)


def run(state, command, *sides):
    """コインの結果を決めてコマンドを処理する。(新しい状態, 新しいログ, 進んだ乱数の回数)。"""
    start = with_coin_results(state, *sides) if sides else state
    new = apply_command(start, command)
    assert check_invariants(new) == []
    return new, [dict(e) for e in new.log[len(start.log):]], rng_draws(start, new)


def kinds(events):
    return [e["kind"] for e in events if e["kind"] not in ("turn_end", "pokemon_check", "turn_start", "draw")]


def counters(events):
    return [e for e in events if e["kind"] in ("counterattack", "counterattack_skipped")]


def written(state):
    return state_to_dict(state, format_version=9)


HITMONCHAN_JAB = {"card": HITMONCHAN, "energy": [FIGHTING] * 3}  # ジャブ 20・スペシャルパンチ 40（闘闘無）。HP 70


class BasicTest(unittest.TestCase):
    """C1〜C3・C10〜C12・C17・C42。"""

    def test_counter_after_the_opponents_attack_damage(self):
        """相手のワザのダメージ（20）を受けたら、ワザを使ったポケモンに 10（C2・C3・C10・C11）。順番は ワザ → ダメージ → はんげき →
        番の終わり。乱数は使わない（ログ coin_flip なし・状態の乱数も進まない）。カイリキーの持ち主は番のプレイヤーではない（相手の番に
        はたらく。p.192 の解説）。"""
        state = board(HITMONCHAN_JAB)
        new, events, draws = run(state, UseAttack(0, 0))
        self.assertEqual(kinds(events), ["attack", "damage", "counterattack"])
        counter = counters(events)[0]
        attacker = state.players[0].active
        self.assertEqual(
            {k: counter[k] for k in ("player", "pokemon", "pokemon_id", "power", "attacker", "attacker_pokemon", "attacker_pokemon_id",
                                     "effect", "amount", "total_damage", "knocked_out")},
            {"player": 1, "pokemon": state.players[1].active.card, "pokemon_id": state.players[1].active.pokemon_id, "power": POWER,
             "attacker": 0, "attacker_pokemon": attacker.card, "attacker_pokemon_id": attacker.pokemon_id, "effect": f"{HITMONCHAN}#0",
             "amount": 10, "total_damage": 10, "knocked_out": False},
        )
        self.assertEqual((new.players[0].active.damage, new.players[1].active.damage), (10, 20))
        self.assertEqual((draws, coin_events(new, len(state.log))), (0, []))
        self.assertEqual(new.current_player, 1)  # ワザを使ったので番は終わった（はんげきは番を止めない）

    def test_counter_even_if_the_machamp_is_knocked_out(self):
        """カイリキーがそのダメージできぜつしても与える（「（それによってこのカードが「きぜつ」しても、）」。C17）。与えたあとで、ワザの
        あとのきぜつ・サイド・交代（p.323）。カイリキーの持ち主（相手）が交代する。"""
        state = board(HITMONCHAN_JAB, machamp(damage=80))
        new, events, _ = run(state, UseAttack(0, 1))
        self.assertEqual(kinds(events), ["attack", "damage", "counterattack", "knock_out"])
        self.assertEqual(new.players[0].active.damage, 10)
        self.assertEqual((new.decision.kind, new.decision.player), ("take_prize", 0))
        self.assertIsNone(new.players[1].active)

    def test_weakness_and_resistance_do_not_apply(self):
        """弱点（ピカチュウの闘 ×2）・抵抗力（ゴーストの闘 −30・バタフリーの闘 −30・ドードーの闘 −30）に関係なく 10（C12）。"""
        cases = (
            ({"card": PIKACHU, "energy": [LIGHTNING]}, 0),
            ({"card": HAUNTER, "evolved_from": GASTLY, "energy": [PSYCHIC, PSYCHIC]}, 0),
            ({"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}, 0),
            ({"card": DODUO, "energy": [FIRE]}, 0),
        )
        for attacker, index in cases:
            with self.subTest(attacker=attacker["card"]):
                new, events, _ = run(board(attacker), UseAttack(0, index), H, H)
                [counter] = counters(events)
                self.assertEqual((counter["amount"], new.players[0].active.damage), (10, 10))

    def test_defender_on_the_attacker_does_not_reduce(self):
        """ワザを使ったポケモンについているディフェンダー（ワザによるダメージを 20 へらす。p.257）は、「はんげき」の 10 をへらさない
        （特殊能力によるダメージ。p.138「［ショックボム］によるダメージは、「ディフェンダー」で防ぐこともできません」・p.245。C13・C37）。"""
        attacker = {**HITMONCHAN_JAB, "trainers": [(DEFENDER, TURN + 1)]}
        new, events, _ = run(board(attacker), UseAttack(0, 0))
        [counter] = counters(events)
        self.assertEqual((counter["amount"], new.players[0].active.damage), (10, 10))
        self.assertEqual(len(new.players[0].active.trainers), 1)  # ディフェンダーは次の相手の番の終わりまでついたまま

    def test_large_damage_still_gives_10(self):
        """受けたダメージの量によらず 10（ユンゲラーのちょうねんりき 50 × 弱点 2 = 100。C10・C42）。「こうらがえし」（同じダメージ）とは違う。"""
        kadabra = {"card": KADABRA, "evolved_from": ABRA, "energy": [PSYCHIC] * 3}
        new, events, _ = run(board(kadabra), UseAttack(0, 1))
        self.assertEqual([e["amount"] for e in events if e["kind"] == "damage"], [100])
        self.assertEqual(counters(events)[0]["amount"], 10)
        self.assertEqual(new.players[0].active.damage, 10)

    def test_each_attack_triggers_again(self):
        """ワザを受けるたびに（p.192 の解説「ダメージを受けるたびに」）。2 回のワザで 2 回。"""
        state = board(HITMONCHAN_JAB, bench1=[RATTATA])
        first = apply_command(state, UseAttack(0, 0))
        second = apply_command(apply_command(first, EndTurn(1)), UseAttack(0, 0))
        self.assertEqual(sum(1 for e in second.log if e["kind"] == "counterattack"), 2)
        self.assertEqual(second.players[0].active.damage, 20)

    def test_cannot_be_declared(self):
        """自動的にはたらく特殊能力は使用を宣言しない（p.311・p.323。C1）。``POWER_NOT_DECLARABLE``。状態・乱数・ログは変わらない。"""
        state = build_test_state([{"active": machamp(), "bench": [RATTATA]}, {"active": RATTATA}], turn_number=TURN)
        before, fingerprint, log = written(state), rng_fingerprint(state.rng), state.log
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        self.assertEqual(ctx.exception.code, "POWER_NOT_DECLARABLE")
        self.assertEqual((written(state), rng_fingerprint(state.rng)), (before, fingerprint))
        self.assertIs(state.log, log)

    def test_registration(self):
        """登録（PowerKey("PMCG1-057", 0)）は、照合した印刷の文面・最新の説明（p.192）と同じ。実装は宣言しない ``CounterattackDamage(10)``。"""
        entry = DEFAULT_EFFECTS.power_entry(MACHAMP, 0)
        self.assertEqual(entry.effect, CounterattackDamage(amount=10))
        self.assertFalse(entry.effect.declared)
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), ("はんげき", PRINTED, LATEST, "P43 p.192"))
        self.assertEqual(DEFAULT_EFFECTS.describe()["powers"][POWER],
                         {"implementation": "counterattack_damage", "name_ja": "はんげき", "source": "P43 p.192"})
        with self.assertRaises(ValueError):
            CounterattackDamage(amount=5)

    def test_public_query(self):
        """公開の問い合わせ ``working_counterattack_power``: はたらいていれば PowerKey、ねむりなら None、場にいない番号は ValueError。"""
        state = board(HITMONCHAN_JAB, bench1=[machamp()])
        active, bench = state.players[1].active, state.players[1].bench[0]
        self.assertEqual((working_counterattack_power(state, active.pokemon_id), working_counterattack_power(state, bench.pokemon_id)),
                         (STRIKES_BACK, STRIKES_BACK))
        self.assertIsNone(working_counterattack_power(state, state.players[0].active.pokemon_id))
        asleep = board(HITMONCHAN_JAB, machamp(sleep=True))
        self.assertIsNone(working_counterattack_power(asleep, asleep.players[1].active.pokemon_id))
        with self.assertRaises(ValueError):
            working_counterattack_power(state, 999)

    def test_other_machamp_is_not_strikes_back(self):
        """名前に「カイリキー」を含む別のカード（サカキのカイリキー。PMCG6-061）は「はんげき」を持たない（v0.10 では参照カード。v0.11 で
        こんじょう（``PreventKnockOutOnHeads``）を登録して対戦に使えるようにした。tests/test_guts_v0_11.py）。登録はカード id（PowerKey）で
        引く（名前では引かない）。"""
        pool = load_card_pool()
        self.assertTrue(pool.is_playable(GIOVANNIS_MACHAMP))
        self.assertEqual([p.name_ja for p in pool.get(GIOVANNIS_MACHAMP).powers], ["こんじょう"])
        self.assertNotIsInstance(DEFAULT_EFFECTS.power_entry(GIOVANNIS_MACHAMP, 0).effect, CounterattackDamage)
        self.assertTrue(pool.is_playable(MACHAMP))


class SourceTest(unittest.TestCase):
    """どのダメージではたらくか（C3〜C9・C14・C40）。"""

    def test_own_attack_does_not_trigger(self):
        """自分のワザ（テスト専用の効果: カイリキーが自分のワザで自分に 10）ではたらかない（「相手のワザによって」。C4）。"""
        text = load_card_pool().get(MACHAMP).attacks[0].text_ja
        effects = DEFAULT_EFFECTS.with_attacks("test-self-hit", {AttackKey(MACHAMP, 0): AttackEntry(SelfHit(), "ちきゅうなげ", text_ja=text)})
        state = build_test_state([{"active": machamp(energy=[FIGHTING] * 4), "bench": [RATTATA]}, {"active": RATTATA}],
                                 turn_number=TURN, effects=effects)
        new, events, _ = run(state, UseAttack(0, 0))
        self.assertEqual(new.players[0].active.damage, 10)
        self.assertEqual(counters(events), [])

    def test_confusion_damage_does_not_trigger(self):
        """こんらんのカイリキーがワザを使い「うら」で自分に 20（× 弱点なし）。相手のワザではなく、こんらんでもある（C4・C6・C21）。"""
        state = build_test_state([{"active": machamp(energy=[FIGHTING] * 4, confusion=True), "bench": [RATTATA]}, {"active": RATTATA}],
                                 turn_number=TURN)
        new, events, _ = run(state, UseAttack(0, 0), T)
        self.assertEqual([e["kind"] for e in events if e["kind"] == "confusion_damage"], ["confusion_damage"])
        self.assertEqual(counters(events), [])

    def test_opponent_confused_attack_does_not_reach(self):
        """相手のこんらんしたワザ（「うら」）は、カイリキーにダメージを与えない（こんらんで自分に 20）ので、はたらかない（C40）。"""
        new, events, _ = run(board({**HITMONCHAN_JAB, "confusion": True}), UseAttack(0, 0), T)
        self.assertEqual(counters(events), [])
        self.assertEqual(new.players[1].active.damage, 0)

    def test_poison_damage_does_not_trigger(self):
        """どくのカイリキーが、ポケモンチェックで受けるどくのダメージ（ポケモン以外のものから受けるダメージ。p.319・p.321。C6）では
        はたらかない。"""
        state = board({"card": RATTATA, "energy": [FIRE]}, machamp(poison=10))
        new, events, _ = run(state, EndTurn(0))
        self.assertEqual([e["kind"] for e in events if e["kind"] == "poison_damage"], ["poison_damage"])
        self.assertEqual(counters(events), [])

    def test_damage_swap_does_not_trigger(self):
        """ダメージスワップでカウンターをのせられても、「ダメージを受けた」ことにならない（p.320。C7）。"""
        alakazam = {"card": ALAKAZAM, "evolved_from": [ABRA, KADABRA], "damage": 20}
        state = build_test_state([{"active": alakazam, "bench": [machamp()]}, {"active": RATTATA}], turn_number=TURN)
        target = state.players[0].bench[0]
        new, events, _ = run(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0, None,
                                                    state.players[0].active.pokemon_id, target.pokemon_id))
        self.assertEqual((new.players[0].active.damage, new.players[0].bench[0].damage), (10, 10))  # フーディンに 10 を返さない
        self.assertEqual(kinds(events), ["pokemon_power", "move_damage_counter"])
        self.assertEqual(counters(events), [])

    def test_counter_damage_does_not_trigger_another_counter(self):
        """相手のカイリキーのワザ（ちきゅうなげ）を受けたカイリキーの「はんげき」の 10 は特殊能力によるダメージで、ワザを使ったカイリキーの
        「はんげき」ははたらかない（p.138・p.245・p.321。C5・C13・C14）。連鎖しない。"""
        state = build_test_state([{"active": machamp(energy=[FIGHTING] * 4), "bench": [RATTATA]}, {"active": machamp(), "bench": [RATTATA]}],
                                 turn_number=TURN)
        new, events, _ = run(state, UseAttack(0, 0))
        self.assertEqual(kinds(events), ["attack", "damage", "counterattack"])
        self.assertEqual((new.players[0].active.damage, new.players[1].active.damage), (10, 60))

    def test_zero_damage_does_not_trigger(self):
        """最終ダメージが 0（ディフェンダー 10 − 20・みだれづきの「うら」2 枚・からてチョップの 0 以下）なら「ダメージを受けなかった」
        （p.319 の例「ダメージを受けたら、それを与えたポケモンを『マヒ』状態にする」）。はたらかない（C8・A4-3）。"""
        defended = machamp(trainers=[(DEFENDER, TURN)])
        cases = (
            (board({"card": DIGLETT, "energy": [FIGHTING]}, defended), UseAttack(0, 0), ()),
            (board({"card": DODUO, "energy": [FIRE]}), UseAttack(0, 0), (T, T)),
            (board({"card": MACHOKE, "evolved_from": MACHOP, "damage": 50, "energy": [FIGHTING] * 3}), UseAttack(0, 0), ()),
        )
        for state, command, sides in cases:
            with self.subTest(attacker=state.cards[state.players[0].active.card].card_id):
                new, events, _ = run(state, command, *sides)
                self.assertEqual([e["amount"] for e in events if e["kind"] == "damage"], [0])
                self.assertEqual(counters(events), [])

    def test_effect_only_attack_does_not_trigger(self):
        """ダメージのないワザ（キノコのほうし・どくガス）でははたらかない（C8。効果だけ）。"""
        cases = ((board({"card": PARAS, "energy": [GRASS, GRASS]}), UseAttack(0, 1)), (board({"card": GRIMER, "energy": [GRASS]}), UseAttack(0, 0)))
        for state, command in cases:
            new, events, _ = run(state, command)
            self.assertEqual(counters(events), [])
            self.assertEqual(new.players[0].active.damage, 0)

    def test_bench_machamp_works(self):
        """ベンチのカイリキーの力もはたらいている（p.311・p.323「特に記述されていないかぎり、ベンチにいるポケモンも特殊能力を使うことが
        できます」。最新の説明に場所の制限がない。C9）。対応カードにベンチにダメージを与えるワザはないので、関数で確かめる。"""
        state = board(HITMONCHAN_JAB, bench1=[machamp()])
        self.assertEqual(counterattack_power(state, state.players[1].bench[0])[0], STRIKES_BACK)


class SelfHit(AttackEffect):
    """テスト専用: ワザを使うポケモン自身に 10 ダメージ（p.320 のダメージの (3)）。カイリキーが自分のワザで自分にダメージを与える場合
    （C4）を確かめるため（対応カードにない）。"""

    implementation_id = "test_self_hit"

    def check(self, attack):
        return []

    def damage_profile(self, state, use):
        return DamageProfile(self_damage=(10,))

    def resolve(self, state, use):
        deal_attack_damage(state, use, SELF, 10)


class ConditionTest(unittest.TestCase):
    """C19〜C23・C26。"""

    def test_asleep_paralyzed_confused_do_not_work(self):
        for condition in ({"sleep": True}, {"paralysis": TURN - 1}, {"confusion": True}):
            with self.subTest(condition=condition):
                new, events, draws = run(board(HITMONCHAN_JAB, machamp(**condition)), UseAttack(0, 0))
                self.assertEqual(counters(events), [])
                self.assertEqual(new.players[0].active.damage, 0)

    def test_poison_does_not_stop_it(self):
        """どくは挙げられていない（C22）。"""
        new, events, _ = run(board(HITMONCHAN_JAB, machamp(poison=10)), UseAttack(0, 0))
        self.assertEqual(len(counters(events)), 1)

    def test_condition_given_by_the_same_attack_after_the_damage(self):
        """そのワザの効果（いとをはくの「おもて」でマヒ・あくむでねむり）でダメージのあとに特殊状態になっても、ダメージを受けたときには
        なっていない（「すでに」）のではたらく。「はんげき」は特殊状態の効果より先（p.89。C23・C28）。"""
        caterpie = {"card": CATERPIE, "energy": [GRASS]}
        new, events, _ = run(board(caterpie), UseAttack(0, 0), H)
        self.assertEqual(kinds(events)[:5], ["attack", "damage", "counterattack", "coin_flip", "special_condition"])
        self.assertTrue(new.players[1].active.conditions.paralyzed)
        nightmare = {"card": HAUNTER, "evolved_from": GASTLY, "energy": [PSYCHIC, PSYCHIC]}
        _, events, _ = run(board(nightmare), UseAttack(0, 0))
        self.assertEqual(kinds(events)[:4], ["attack", "damage", "counterattack", "special_condition"])

    def test_works_again_after_recovering(self):
        """ポケモンチェックでねむりから回復したら、次のワザではたらく（C26）。"""
        state = board(HITMONCHAN_JAB, machamp(sleep=True))
        first = apply_command(with_coin_results(state, H), UseAttack(0, 0))  # ポケモンチェックのねむりのコイン「おもて」で回復
        self.assertFalse(first.players[1].active.conditions.asleep)
        second = apply_command(apply_command(first, EndTurn(1)), UseAttack(0, 0))
        self.assertEqual(sum(1 for e in second.log if e["kind"] == "counterattack"), 1)

    def test_evaluated_when_receiving_not_at_declaration(self):
        """はたらくかは、ダメージを受けるときの状態で決める（関数で確かめる。``deal_attack_damage`` の中でねむりにすると加えない）。
        v0.16b: 解決の基盤のワザの枠（``resolution.open_attack``）で、送る効果の列（``runtime.pending``）を見る。"""
        state = board(HITMONCHAN_JAB)
        use = open_attack(state, 0)
        target = state.players[1].active
        target.conditions = dataclasses.replace(target.conditions, exclusive=Asleep())
        deal_attack_damage(state, use, "opponent_active", 20)
        self.assertEqual(use.runtime.pending, ())


class GasTest(unittest.TestCase):
    """かがくへんかガス（v0.8）で消える（p.48・p.323。C24・C25）。v0.8 の ``continuous.suppressors_of`` をそのまま使う。"""

    muk = {"card": MUK, "evolved_from": GRIMER}

    def test_either_players_muk_suppresses(self):
        for bench0, bench1 in (([self.muk], ()), ((), [self.muk])):
            with self.subTest(attacker_side=bool(bench0)):
                state = board(HITMONCHAN_JAB, bench0=bench0, bench1=bench1)
                self.assertIsNone(working_counterattack_power(state, state.players[1].active.pokemon_id))
                new, events, _ = run(state, UseAttack(0, 0))
                self.assertEqual(counters(events), [])

    def test_muk_attacking_suppresses_unless_its_gas_is_gone(self):
        """ベトベトンがワザ（ヘドロこうげき）を使うと、自分のかがくへんかガスで消えている。こんらんのベトベトン（ガスが消えている。G9〜G11）
        なら、こんらんの「おもて」のあと、はたらく（ワザのコインより先）。"""
        attacker = {**self.muk, "energy": [GRASS] * 3}
        _, events, _ = run(board(attacker), UseAttack(0, 0), T)
        self.assertEqual(counters(events), [])
        _, events, _ = run(board({**attacker, "confusion": True}), UseAttack(0, 0), H, T)
        self.assertEqual(kinds(events)[:6], ["attack", "coin_flip", "confusion_check", "damage", "counterattack", "coin_flip"])

    def test_works_again_after_the_muk_is_knocked_out(self):
        """ベトベトンが場をはなれたら、また、はたらく（C25）。"""
        state = board(HITMONCHAN_JAB, {**self.muk, "damage": 60}, bench1=[machamp()])
        new = apply_command(state, UseAttack(0, 0))
        while new.decision is not None:
            options = new.decision.options
            pick = new.players[1].bench[0].pokemon_id if new.decision.kind == "promote_active" else options[0]
            new = apply_command(new, ResolveDecision(new.decision.player, new.decision.id, (pick,)))
        self.assertEqual(new.cards[new.players[1].active.card].card_id, MACHAMP)
        hit = apply_command(apply_command(new, EndTurn(1)), UseAttack(0, 0))
        self.assertEqual(sum(1 for e in hit.log if e["kind"] == "counterattack"), 1)


class OrderTest(unittest.TestCase):
    """解決の順番（p.89 のワザ解説。C27〜C29・C15・C16）: ワザのダメージの処理（相手へのダメージ・自分へのダメージ）→ はんげき →
    ダメージ以外の効果 → きぜつ・サイド・交代。"""

    def test_after_the_self_damage_of_the_attack(self):
        """じごくぐるま（相手に 60 → 自分に 20）: 自分へのダメージのあとに「はんげき」（ダメージの処理のあと。C29）。"""
        machoke = {"card": MACHOKE, "evolved_from": MACHOP, "energy": [FIGHTING] * 4}
        new, events, _ = run(board(machoke), UseAttack(0, 1))
        self.assertEqual(kinds(events), ["attack", "damage", "damage", "counterattack"])
        self.assertEqual(new.players[0].active.damage, 30)

    def test_thundershock_tails(self):
        """でんげき「うら」（相手に 30 → コイン → 自分に 10）: 自分へのダメージのあとに「はんげき」。"""
        pikachu = {"card": PIKACHU, "energy": [LIGHTNING, LIGHTNING]}
        new, events, _ = run(board(pikachu), UseAttack(0, 1), T)
        self.assertEqual(kinds(events), ["attack", "damage", "coin_flip", "damage", "counterattack"])
        self.assertEqual(new.players[0].active.damage, 20)

    def test_before_the_effect_coin(self):
        """どくばり（相手に 10 → コイン → どく）: 「はんげき」はワザのコインより先（C28）。"""
        weedle = {"card": WEEDLE, "energy": [GRASS]}
        _, events, _ = run(board(weedle), UseAttack(0, 0), H)
        self.assertEqual(kinds(events)[:5], ["attack", "damage", "counterattack", "coin_flip", "special_condition"])

    def test_before_the_forced_switch(self):
        """ふきとばし（相手に 20 → 入れ替える）: 「はんげき」を与えてから入れ替えの決定（p.89「「こうらがえし」の状態によるダメージを
        与えた後に「ふきとばし」の効果で」）。"""
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}
        waiting, events, _ = run(board(butterfree), UseAttack(0, 0))
        self.assertEqual(kinds(events), ["attack", "damage", "counterattack"])
        self.assertEqual((waiting.decision.kind, waiting.decision.player), (FORCED_SWITCH, 1))
        done = apply_command(waiting, ResolveDecision(1, waiting.decision.id, (waiting.decision.options[0],)))
        self.assertEqual(done.players[0].active.damage, 10)

    def test_drain_removes_the_counter_damage(self):
        """メガドレイン（相手に 40 → 半分の 2 個とりのぞく）: 「はんげき」の 10 のあとに回復するので、回復で 10 がとりのぞかれる（C28）。"""
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS] * 4}
        new, events, _ = run(board(butterfree), UseAttack(0, 1))
        self.assertEqual(kinds(events), ["attack", "damage", "counterattack", "drain_heal"])
        heal = next(e for e in events if e["kind"] == "drain_heal")
        self.assertEqual((heal["damage_before"], heal["counters"], heal["total_damage"]), (10, 1, 0))
        seed = {"card": BULBASAUR, "energy": [GRASS, GRASS]}
        new, events, _ = run(board(seed), UseAttack(0, 0))
        self.assertEqual(kinds(events), ["attack", "damage", "counterattack", "drain_heal"])
        self.assertEqual(new.players[0].active.damage, 0)

    def test_drain_after_a_counter_knock_out_is_skipped(self):
        """「はんげき」でワザを使ったポケモンが HP 以上になったら、あとの自分への効果（回復）は処理しない（p.89「そのダメージで
        きぜつしなければ」。C16）。ログ drain_heal_skipped。ワザを使ったポケモンはきぜつし、カイリキーの持ち主がサイドを取る。"""
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "damage": 60, "energy": [GRASS] * 4}
        new, events, _ = run(board(butterfree, bench0=[RATTATA]), UseAttack(0, 1))
        self.assertEqual(kinds(events), ["attack", "damage", "counterattack", "drain_heal_skipped", "knock_out"])
        self.assertTrue(counters(events)[0]["knocked_out"])
        self.assertEqual((new.decision.kind, new.decision.player), ("take_prize", 1))

    def test_whirlwind_after_a_counter_knock_out(self):
        """「はんげき」でワザを使ったポケモンがきぜつしても、入れ替えの対象（相手の対戦ポケモン）はいるので入れ替える（p.309。C16）。
        きぜつの処理は入れ替えのあと（ワザのあと）。"""
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "damage": 60, "energy": [GRASS, GRASS]}
        waiting, events, _ = run(board(butterfree, bench0=[RATTATA]), UseAttack(0, 0))
        self.assertEqual(waiting.decision.kind, FORCED_SWITCH)
        done = apply_command(waiting, ResolveDecision(1, waiting.decision.id, (waiting.decision.options[0],)))
        later = [e["kind"] for e in done.log[len(waiting.log):]]
        self.assertEqual(later[:2], ["forced_switch", "knock_out"])
        self.assertEqual((done.decision.kind, done.decision.player), ("take_prize", 1))

    def test_attacker_already_knocked_out_by_its_own_damage(self):
        """じごくぐるまの自分への 20 でワザを使ったポケモンがすでに HP 以上なら、対象がいないので「はんげき」は与えない（p.309。C15）。
        ログ counterattack_skipped（reason knocked_out）。カイリキーもきぜつするなら 1 つのワザによる同時のきぜつ（p.324）。"""
        machoke = {"card": MACHOKE, "evolved_from": MACHOP, "damage": 60, "energy": [FIGHTING] * 4}
        new, events, _ = run(board(machoke, machamp(damage=40), bench0=[RATTATA]), UseAttack(0, 1))
        self.assertEqual(kinds(events), ["attack", "damage", "damage", "counterattack_skipped", "knock_out", "knock_out"])
        self.assertEqual(counters(events)[0]["reason"], "knocked_out")
        self.assertEqual([e.get("simultaneous") for e in events if e["kind"] == "knock_out"], [True, True])


class KnockOutTest(unittest.TestCase):
    """きぜつ・サイド・交代・勝ち負け（A4-1・A4-6。C17・C18・C30〜C33・C38）。"""

    def finish(self, state):
        """決定にいつも最初の選べるもので答えて、決定がなくなるまで進める。"""
        while state.decision is not None:
            d = state.decision
            state = apply_command(state, ResolveDecision(d.player, d.id, (d.options[0],)))
        return state

    def test_machamp_knocked_out_and_the_attacker_survives(self):
        """カイリキーだけがきぜつ（はんげきの 10 では残る）: ワザを使ったプレイヤーがサイドを 1 枚取り、カイリキーの持ち主が交代する。"""
        state = board(HITMONCHAN_JAB, machamp(damage=80))
        new = self.finish(apply_command(state, UseAttack(0, 1)))
        self.assertEqual([len(p.prizes) for p in new.players], [5, 6])
        self.assertEqual(new.players[0].active.damage, 10)
        self.assertEqual(new.cards[new.players[1].active.card].card_id, RATTATA)

    def test_machamp_knocked_out_by_the_last_prize(self):
        """カイリキーのきぜつで最後のサイドを取ったら、ワザを使ったプレイヤーの勝ち（p.311）。はんげきは与えたあと。"""
        state = build_test_state([{"active": HITMONCHAN_JAB, "bench": [PONYTA], "prizes": 1},
                                  {"active": machamp(damage=80), "bench": [RATTATA]}], turn_number=TURN)
        new = self.finish(apply_command(state, UseAttack(0, 1)))
        self.assertEqual((new.phase, new.result.winner), (Phase.GAME_OVER, 0))
        self.assertIn("counterattack", [e["kind"] for e in new.log])

    def test_counter_knocks_out_the_attacker(self):
        """「はんげき」だけでワザを使ったポケモンがきぜつ（カイリキーは残る）: カイリキーの持ち主がサイドを取り（きぜつしたポケモンの相手側
        のプレイヤー。p.323。C38）、ワザを使ったプレイヤーが交代する。"""
        state = board({**HITMONCHAN_JAB, "damage": 60}, bench0=[RATTATA])
        new, events, _ = run(state, UseAttack(0, 0))
        self.assertEqual(kinds(events), ["attack", "damage", "counterattack", "knock_out"])
        done = self.finish(new)
        self.assertEqual([len(p.prizes) for p in done.players], [6, 5])
        self.assertEqual(done.cards[done.players[0].active.card].card_id, RATTATA)

    def test_counter_knock_out_without_a_bench_loses(self):
        """「はんげき」できぜつし、ワザを使ったプレイヤーに出せるポケモンがいない: そのプレイヤーの負け（p.311・p.323）。"""
        state = build_test_state([{"active": {**HITMONCHAN_JAB, "damage": 60}}, {"active": machamp(), "bench": [RATTATA]}], turn_number=TURN)
        new = self.finish(apply_command(state, UseAttack(0, 0)))
        self.assertEqual((new.phase, new.result.winner), (Phase.GAME_OVER, 1))

    def test_counter_knock_out_takes_the_last_prize(self):
        """「はんげき」のきぜつでカイリキーの持ち主が最後のサイドを取ったら、その持ち主の勝ち（番のプレイヤーでなくても。p.311）。"""
        state = build_test_state([{"active": {**HITMONCHAN_JAB, "damage": 60}, "bench": [PONYTA]},
                                  {"active": machamp(), "bench": [RATTATA], "prizes": 1}], turn_number=TURN)
        new = self.finish(apply_command(state, UseAttack(0, 0)))
        self.assertEqual((new.phase, new.result.winner), (Phase.GAME_OVER, 1))

    def test_both_knocked_out_by_counter_is_unresolved(self):
        """ワザでカイリキーがきぜつし、「はんげき」でワザを使ったポケモンがきぜつする（「はんげき」がなければきぜつしない）: 同時のきぜつか
        決められない（p.324。C18・A4-6）。ワザの宣言の前（こんらんのコインの前）に止める。状態・乱数・ログは変わらない。勝者を推測で
        決めない（両方が最後のサイドを取る盤面・出せるポケモンがいない盤面も同じに止める）。"""
        boards = (
            board({**HITMONCHAN_JAB, "damage": 60}, machamp(damage=80), bench0=[RATTATA]),
            build_test_state([{"active": {**HITMONCHAN_JAB, "damage": 60}, "prizes": 1}, {"active": machamp(damage=80), "prizes": 1}],
                             turn_number=TURN),
            board({**HITMONCHAN_JAB, "damage": 60, "confusion": True}, machamp(damage=80), bench0=[RATTATA]),
        )
        for state in boards:
            before, fingerprint, log = written(state), rng_fingerprint(state.rng), state.log
            with self.assertRaises(UnsupportedError) as ctx:
                apply_command(state, UseAttack(0, 1))
            self.assertEqual(ctx.exception.code, "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")
            self.assertEqual((written(state), rng_fingerprint(state.rng)), (before, fingerprint))
            self.assertIs(state.log, log)

    def test_both_knocked_out_by_one_attack_is_simultaneous(self):
        """じごくぐるまで、カイリキーと自分（自分への 20）がきぜつ: 1 つのワザによる同時のきぜつ（p.324。「はんげき」は与えない）。両方が
        最後のサイドを取ったらサドン・デス（p.311）。"""
        machoke = {"card": MACHOKE, "evolved_from": MACHOP, "damage": 60, "energy": [FIGHTING] * 4}
        state = build_test_state([{"active": machoke, "prizes": 1}, {"active": machamp(damage=40), "prizes": 1}], turn_number=TURN)
        new = self.finish(apply_command(state, UseAttack(0, 1)))
        self.assertEqual(new.phase, Phase.SUDDEN_DEATH)
        self.assertIn("counterattack_skipped", [e["kind"] for e in new.log])

    def test_unresolved_regardless_of_the_coins(self):
        """でんげき（「うら」なら自分へのダメージで先にきぜつ、「おもて」なら「はんげき」できぜつ）: どちらのコインでも止める（コインの
        結果で受け付けるかが変わらない）。"""
        pikachu = {"card": PIKACHU, "damage": 30, "energy": [LIGHTNING, LIGHTNING]}
        for sides in ((H,), (T,)):
            with self.assertRaises(UnsupportedError) as ctx:
                apply_command(with_coin_results(board(pikachu, machamp(damage=70), bench0=[RATTATA]), *sides), UseAttack(0, 1))
            self.assertEqual(ctx.exception.code, "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")


class CoinIndependenceTest(unittest.TestCase):
    """相手の対戦ポケモンがカイリキーのとき、受け付けるか・拒否のコードが、コインの結果（こんらん 1 枚 + ワザ 2 枚まで）で変わらない
    （v0.3d の CoinIndependenceTest と同じ確かめ方）。止めるのは C18 の場合だけで、その条件をエンジンとは別に求めて比べる。"""

    def test_acceptance_does_not_depend_on_the_coins(self):
        coins = list(itertools.product((H, T), repeat=3))
        machamp_states = [{}, {"sleep": True}, {"damage": 70}, {"damage": 90}, {"damage": 90, "defender": True}]
        checked = stopped = 0
        for (card, index), confused, machamp_state, near in itertools.product(ATTACKS, (False, True), machamp_states, (False, True)):
            turn = 7 + 2 * len(EVOLVED_FROM.get(card, ()))
            definition = load_card_pool().get(card)
            attacker = {"card": card, "energy": energy_for(card, index), **({"confusion": True} if confused else {})}
            if near:
                attacker["damage"] = definition.hp - 10  # 「はんげき」の 10 できぜつする
            if card in EVOLVED_FROM:
                attacker["evolved_from"] = list(EVOLVED_FROM[card])
            spec = dict(machamp_state)
            if spec.pop("defender", False):
                spec["trainers"] = [(DEFENDER, turn)]
            state = build_test_state([
                {"active": attacker, "bench": [PONYTA], "discard": []}, {"active": machamp(**spec), "bench": [RATTATA]},
            ], turn_number=turn)
            results = set()
            for sides in coins:
                try:
                    new = apply_command(with_coin_results(state, *sides), UseAttack(0, index))
                    self.assertEqual(check_invariants(new), [])
                    results.add("accepted")
                except EngineError as error:
                    results.add(error.code)
            expected = self.expected(state, card, index, machamp_state, near, confused)
            with self.subTest(card=card, index=index, confused=confused, machamp=machamp_state, near=near):
                self.assertEqual(len(results), 1, results)
                if expected:
                    self.assertEqual(results, {"UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT"})
                else:
                    self.assertNotIn("UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT", results)
            stopped += expected
            checked += 1
        self.assertEqual(checked, len(ATTACKS) * 2 * len(machamp_states) * 2)
        self.assertGreater(stopped, 0)

    @staticmethod
    def expected(state, card, index, machamp_state, near, confused):
        """エンジンとは別に求める: カイリキーがねむりでなく、かがくへんかガスがはたらいておらず（ワザを使うのがこんらんでないベトベトン
        なら、そのガスがはたらいている）、どれかのコインの結果でカイリキーがきぜつし、ワザを使ったポケモンが自分へのダメージではきぜつせず
        「はんげき」できぜつしうる。カイリキーの弱点は超（×2）、抵抗力なし。"""
        if machamp_state.get("sleep") or not near or (card == MUK and not confused):
            return False
        attack = load_card_pool().get(card).attacks[index]
        if attack.damage is None:
            return False
        bases = {
            "×": [heads * attack.damage for heads in range(3)], "+": [attack.damage, attack.damage + 20],
            "-": [attack.damage - 10 * ((load_card_pool().get(card).hp - 10) // 10)],
        }.get(attack.damage_modifier, [attack.damage])
        implementation = DEFAULT_EFFECTS.attack_entry(card, index).effect
        if isinstance(implementation, CoinFlipDamage):  # v0.11: ハリケーンパンチはコイン 4 枚（みだれづき・ダブルニードルは 2 枚）
            bases = [heads * implementation.damage_per_heads for heads in range(implementation.coins + 1)]
        if isinstance(implementation, CoinHeadsDamagePerOwnCounter):  # v0.11: いかりのスーパーパンチ（自分のカウンターの数 × 20）
            bases = [0, (load_card_pool().get(card).hp - 10) // 10 * implementation.damage_per_counter]
        if card == "PMCG1-032":  # ハイドロポンプ（必要な数ちょうどの水エネルギー）
            bases = [attack.damage]
        weak = 2 if load_card_pool().get(card).pokemon_type.value == "psychic" else 1
        reduce = 20 if machamp_state.get("defender") else 0
        hp_left = 100 - machamp_state.get("damage", 0)
        if not any(b > 0 and b * weak - reduce >= hp_left for b in bases):
            return False
        effect = DEFAULT_EFFECTS.attack_entry(card, index).effect
        # 自分へのダメージの候補（でんげき 0・10、じごくぐるま 20）。あと 10 で HP の状態なので、自分へのダメージがあれば先にきぜつ
        own = effect.damage_profile(state, AttackUse(0, state.players[0].active.pokemon_id, AttackKey(card, index))).self_damage
        return any(o == 0 for o in own)


class AtomicityTest(unittest.TestCase):
    """拒否と、処理の途中の内部の誤り（注入した）では、渡した状態・乱数・ログは変わらない（``apply_command`` は複製して処理する）。"""

    def assert_unchanged(self, state, command, error_type, *patches, apply=apply_command):
        before, fingerprint, log = written(state), rng_fingerprint(state.rng), state.log
        with contextlib_exit(patches):
            with self.assertRaises(error_type):
                apply(state, command)
        self.assertEqual((written(state), rng_fingerprint(state.rng)), (before, fingerprint))
        self.assertIs(state.log, log)

    def test_internal_error_after_the_counter(self):
        """「はんげき」のダメージをのせたあと（ログ・回復・入れ替えの決定・特殊状態）で内部の誤りが起きても、渡した状態は変わらない。

        v0.16b: v0.13 の経路を外したので、解決の基盤の同じ所（ログ ``counterattack``・回復のログ ``drain_heal``・決定を出す
        ``codec.push_decision``・特殊状態を付ける ``programs.APPLY_CONDITION``）に誤りを注入する（v0.15 までは v0.13 の経路の
        ``effects._remove_attacker_counters``・``effects.push_attack_decision``・``effects.poison``）。"""
        def boom(*args, **kwargs):
            raise RuntimeError("注入した誤り")

        def failing_event(kind):
            original = GameState.add_event

            def add_event(self, event_kind, **data):
                if event_kind == kind:
                    raise RuntimeError("注入した誤り")
                return original(self, event_kind, **data)

            return mock.patch.object(GameState, "add_event", add_event)

        self.assert_unchanged(board(HITMONCHAN_JAB), UseAttack(0, 0), RuntimeError, failing_event("counterattack"))
        drain = board({"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS] * 4})
        self.assert_unchanged(drain, UseAttack(0, 1), RuntimeError, failing_event("drain_heal"))
        whirlwind = board({"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]})
        self.assert_unchanged(whirlwind, UseAttack(0, 0), RuntimeError, mock.patch.object(codec, "push_decision", boom))
        poison = with_coin_results(board({"card": WEEDLE, "energy": [GRASS]}), H)
        self.assert_unchanged(poison, UseAttack(0, 0), RuntimeError, mock.patch.dict(programs.APPLY_CONDITION, {POISON: boom}))

    def test_invalid_commands_do_not_change_anything(self):
        """不正なコマンド（宣言・エネルギーの足りないワザ・番でないプレイヤー）は、状態・乱数・ログを変えない。"""
        state = board({"card": HITMONCHAN, "energy": [FIGHTING]})
        for command, error in ((UsePokemonPower(1, state.players[1].active.pokemon_id, 0), IllegalActionError),
                               (UseAttack(0, 1), IllegalActionError), (UseAttack(1, 0), IllegalActionError)):
            with self.subTest(command=command):
                self.assert_unchanged(state, command, error)

    def test_accepted_command_does_not_change_the_input(self):
        state = board(HITMONCHAN_JAB)
        before, fingerprint, log = written(state), rng_fingerprint(state.rng), state.log
        new = apply_command(state, UseAttack(0, 0))
        self.assertEqual((written(state), rng_fingerprint(state.rng)), (before, fingerprint))
        self.assertIs(state.log, log)
        self.assertEqual(rng_draws(state, new), 0)


class DirectTest(unittest.TestCase):
    """ワザの処理の部品を直接呼ぶ（対応カードのワザでは起こらない場合。C34・C35・ガード）。

    v0.16b: v0.13 の約束の補助関数は解決の基盤のワザの枠に委ねるので、``resolution.open_attack`` で枠を開いた ``AttackUse`` で呼び、
    まだ与えていない「はんげき」は枠の送る効果の列（``runtime.pending``。``kernel.Deferred``）で見る（v0.15 までは
    ``AttackUse.counterattacks``）。"""

    def use(self, state):
        return open_attack(state, 0)

    def pending_targets(self, use):
        return [deferred.instance.pokemon_id for deferred in use.runtime.pending]

    def test_pending_is_applied_at_the_end_of_the_damage_elements(self):
        state = board(HITMONCHAN_JAB)
        use = self.use(state)
        deal_attack_damage(state, use, "opponent_active", 20)
        self.assertEqual(self.pending_targets(use), [state.players[1].active.pokemon_id])
        self.assertEqual(state.players[0].active.damage, 0)  # ダメージの要素の中では与えない
        finish_damage_elements(state, use)
        self.assertEqual((self.pending_targets(use), state.players[0].active.damage), ([], 10))
        finish_damage_elements(state, use)  # 2 回呼んでも与えない
        self.assertEqual(state.players[0].active.damage, 10)

    def test_two_pending_counters_are_not_ordered(self):
        """1 つのワザで 2 つ以上の「はんげき」（複数のポケモンが受けるワザ）は、順番が決められない（C34・C35）。今の対応カードでは
        起こらないので、エンジンの不具合として止める（解決の基盤はコードのない問い ``multiple_deferred_effects`` として見つけ、コマンドの
        入口で ``RuntimeError`` にする。``questions.to_error``）。"""
        state = board(HITMONCHAN_JAB, bench1=[machamp()])
        use = self.use(state)
        fs = use.runtime.run.fs
        for target in (state.players[1].active, state.players[1].bench[0]):
            (instance,) = [i for i in C.in_window(state, Window.DAMAGE_RECEIVING, 1, target, C.DEFAULT_CATALOG)
                           if i.definition.timing is C.Timing.DEFER]
            fs.pending.append(Deferred(instance, fs.frame.id, 20))
        with self.assertRaises(OpenQuestion) as caught:
            finish_damage_elements(state, use)
        self.assertEqual(caught.exception.key, "multiple_deferred_effects")
        from kyuura_engine.resolution.questions import to_error
        with self.assertRaisesRegex(RuntimeError, "C34・C35"):
            to_error(caught.exception.key)

    def test_effects_and_decisions_need_the_counter_first(self):
        """まだ与えていない「はんげき」があるまま、効果の要素（``attack_reaches``）・決定（``push_attack_decision``）に進むとエンジンの不具合
        として止める（順番を黙って変えない。p.89）。ダメージの要素どうしの間は止めない。"""
        state = board(HITMONCHAN_JAB)
        use = self.use(state)
        deal_attack_damage(state, use, "opponent_active", 20)
        self.assertTrue(attack_reaches(state, use, 1, state.players[1].active, DAMAGE_ELEMENT, amount=10))
        with self.assertRaises(RuntimeError):
            attack_reaches(state, use, 1, state.players[1].active, "sleep")
        with self.assertRaises(RuntimeError):
            push_attack_decision(state, use, kind=FORCED_SWITCH, player=1, options=[state.players[1].bench[0].pokemon_id])

    def test_damage_not_received_does_not_trigger(self):
        """受けなかったダメージ（このワザで「受けない」と決まったポケモン。「とうめい」の記録）・「ダメージを受けない」状態で無効になった
        ダメージの要素では、はたらかない（ダメージを受けていない。p.319・p.321。C8・C36）。カイリキーは「とうめい」を持たないので、ワザ 1 回の
        記録（``AttackUse.reception``）を置いて確かめる。"""
        state = board(HITMONCHAN_JAB)
        use = self.use(state)
        target = state.players[1].active
        use.reception[target.pokemon_id] = False
        result = deal_attack_damage(state, use, "opponent_active", 20)
        self.assertTrue(result.evaded)
        self.assertEqual((self.pending_targets(use), target.damage), ([], 0))
        prevented = board(HITMONCHAN_JAB, machamp(prevent_damage=TURN - 1))
        use = self.use(prevented)
        self.assertTrue(deal_attack_damage(prevented, use, "opponent_active", 20).prevented)
        self.assertEqual(self.pending_targets(use), [])

    def test_memo_is_not_state(self):
        """まだ与えていない「はんげき」はワザ 1 回の中だけの値で、比較・ハッシュ・書き出しに含めない（書き出しの形式は 9 のまま）。v0.16b:
        値は解決の基盤の枠が持ち、``AttackUse`` は枠への入口（``runtime``）を比較・ハッシュ・表示に含めない。"""
        state = board(HITMONCHAN_JAB)
        a = self.use(state)
        deal_attack_damage(state, a, "opponent_active", 20)
        self.assertEqual(len(a.runtime.pending), 1)
        b = AttackUse(a.player, a.pokemon_id, a.key)
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))
        self.assertNotIn("runtime", repr(a))


class InvariantTest(unittest.TestCase):
    """HP 以上のダメージで場に残れるのは、ワザの途中の決定を待つ間の、そのワザで「はんげき」を受けて HP 以上になったワザを使ったポケモン
    だけ（きぜつの処理はワザのあと。C16・C30）。ほかは今までどおり不変条件の違反。"""

    def waiting(self):
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "damage": 60, "energy": [GRASS, GRASS]}
        return apply_command(board(butterfree, bench0=[RATTATA]), UseAttack(0, 0))

    def test_only_the_counter_knocked_out_attacker_may_wait(self):
        state = self.waiting()
        self.assertEqual(state.players[0].active.damage, 70)
        self.assertEqual(check_invariants(state), [])
        broken = state.clone()
        broken.players[1].active.damage = 100  # カイリキーを HP 以上にする
        self.assertTrue(any("HP 以上" in p for p in check_invariants(broken)))
        no_log = state.clone()
        no_log.log = tuple(e for e in state.log if e["kind"] != "counterattack")
        self.assertTrue(any("HP 以上" in p for p in check_invariants(no_log)))
        bench = state.clone()
        bench.players[0].bench[0].damage = 30  # ベンチのコラッタ（HP 30）
        self.assertTrue(any("HP 以上" in p for p in check_invariants(bench)))

    def test_double_knock_out_guard_after_the_preflight(self):
        """宣言の前の確認を外しても、「はんげき」できぜつするところで止める（黙って同時のきぜつにしない）。渡した状態は変わらない。

        v0.16b: v0.13 の経路（確認を外すと、「はんげき」を与えるところで ``RuntimeError``）を外したので、解決の基盤で確かめる。解決の基盤は、
        先読み（``preflight.derived``・``preflight.legacy``）を外しても、実際の処理のきぜつの判定で同じ検出（原因の枠が分かれたきぜつ）を
        するので、宣言の前と同じコード（``UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT``）で止める（tests/test_kernel_integration_v0_15.py の
        ``KernelGuardTest`` と同じ考え方）。"""
        state = board({**HITMONCHAN_JAB, "damage": 60}, machamp(damage=80), bench0=[RATTATA])
        before, fingerprint = written(state), rng_fingerprint(state.rng)
        with mock.patch("kyuura_engine.resolution.preflight.derived", lambda *args, **kwargs: None), \
                mock.patch("kyuura_engine.resolution.preflight.legacy", lambda *args, **kwargs: None):
            for mode in ("derived_full", "legacy"):
                with self.subTest(mode=mode), self.assertRaises(UnsupportedError) as ctx:
                    apply_kernel(state, UseAttack(0, 1), preflight=mode)
                self.assertEqual(ctx.exception.code, "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")
        self.assertEqual((written(state), rng_fingerprint(state.rng)), (before, fingerprint))


class SaveRestoreTest(unittest.TestCase):
    """保存（pickle・deepcopy・形式 9 の書き出し）と復元のあとも同じに進む（はんげきの記録は状態に持たない）。"""

    def test_restored_state_gives_the_same_result(self):
        for state, command in ((board(HITMONCHAN_JAB), UseAttack(0, 0)),
                               (board({**HITMONCHAN_JAB, "damage": 60}, bench0=[RATTATA]), UseAttack(0, 0)),
                               (board({"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS] * 4}), UseAttack(0, 1))):
            for restored in (pickle.loads(pickle.dumps(state)), copy.deepcopy(state)):
                a, b = apply_command(state, command), apply_command(restored, command)
                self.assertEqual(written(a), written(b))
                self.assertEqual(a.log, b.log)

    def test_restored_decision_resumes_after_the_counter(self):
        """ふきとばしの決定を待つ状態（「はんげき」は与えたあと）を保存・復元して答えても、「はんげき」を二度与えない。"""
        state = board({"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]})
        waiting = apply_command(state, UseAttack(0, 0))
        self.assertNotIn("counterattack", repr(written(waiting)["decision"]))
        for restored in (waiting, pickle.loads(pickle.dumps(waiting)), copy.deepcopy(waiting)):
            done = apply_command(restored, ResolveDecision(1, restored.decision.id, (restored.decision.options[0],)))
            self.assertEqual(sum(1 for e in done.log if e["kind"] == "counterattack"), 1)
            self.assertEqual(done.players[0].active.damage, 10)

    def test_format_is_still_9(self):
        from kyuura_engine.serialize import FORMAT_VERSIONS

        self.assertEqual(max(FORMAT_VERSIONS), 9)
        new = apply_command(board(HITMONCHAN_JAB), UseAttack(0, 0))
        self.assertEqual(written(new)["format_version"], 9)
        with self.assertRaises(ValueError):
            state_to_dict(new, format_version=10)


if __name__ == "__main__":
    unittest.main()

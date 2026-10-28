"""サカキのカイリキー（ジム拡張第2弾 闇からの挑戦。PMCG6-061）のポケモンパワー「こんじょう」（v0.11。docs/guts-v0.11.md の G1〜G42・A4〜A6、
docs/ko-prevention-v0.11.md）。

最新の説明（p.193）: 「この力は、相手のワザによるダメージで、このカードが「きぜつ」するとき、使える。コインを投げて「おもて」なら、この
カードは「きぜつ」せず、このカードの残りHPが「10」になる。ダメージを受けるとき、すでにこのカードが「ねむり・マヒ・こんらん」状態だった
なら、この力は使えない。」。p.193 の解説（きぜつするだけのダメージを受けてもコイントスで表ならきぜつしない・何回も・ワザのダメージできぜつ
した場合にのみ・どくのダメージでは効果がない）、p.311（使用を宣言するかはプレイヤーが決める・決められたときにしか宣言できないもの・宣言 →
条件 → 処理の手順・宣言したらすべてすませる）、p.309（ワザを使っている最中に特殊能力の使用を宣言してはいけない・処理の対象がいなくなった
内容は無視）、p.319〜p.324（ダメージ・ワザによるダメージ・きぜつ・サイド・同時のきぜつ）、p.100（にげこむの解説「使うかどうかを相手
プレイヤーに言ってから使います。…もどらなくてもOK」）にしたがう。

盤面は ``build_test_state`` で直接作る（1 つの規定を確かめるテスト）。自然な対戦は tests/test_giovanni_games_v0_11.py、サカキのワンリキー・
ゴーリキー・カイリキーのワザは tests/test_giovanni_machamp_line_v0_11.py。乱数は、コインのログの数と、状態の乱数がいくつ進んだか
（``rng_draws``）の両方で確かめる。

既定の盤面: 番のプレイヤー 0（7 番）がワザを使う。プレイヤー 1 のバトル場にサカキのカイリキー（HP 100。サカキのワンリキー → サカキの
ゴーリキーと進化したもの）、ベンチにコラッタ。
"""

import copy
import inspect
import pickle
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS, EndTurn, EngineError, IllegalActionError, PlayTrainer, PowerKey, PromoteActive, ResolveDecision, TakePrize,
    UnsupportedError, UseAttack, UsePokemonPower, apply_command, check_invariants, load_card_pool, state_to_dict,
)
from kyuura_engine import effects as effects_module
from kyuura_engine.decisions import KO_PREVENTION
from kyuura_engine.effects import (
    ATTACK_ELEMENTS, DAMAGE_ELEMENT, SELF, AttackEffect, AttackEntry, AttackKey, DamageProfile, PreventKnockOutOnHeads,
    available_ko_prevention_power, deal_attack_damage, damage_opponent_active, ko_prevention_power,
)
from kyuura_engine.resolution import programs
from kyuura_engine.resolution.kernel import Resolution, ko_prevention_offers
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import Phase

from tests.helpers import (
    ABRA, ALAKAZAM, BUTTERFREE, CATERPIE, DEFENDER, FIGHTING, GIOVANNIS_MACHAMP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHOP, GRASS,
    GRIMER, H, HITMONCHAN, KADABRA, LIGHTNING, MACHAMP, MACHOKE, MACHOP, METAPOD, MUK, PIKACHU, PONYTA, PSYCHIC, RATTATA, SWITCH,
    T, VULPIX, FIRE, build_test_state, coin_events, with_coin_results,
)
from tests.test_transparency_v0_9 import rng_draws

TURN = 7
GUTS = PowerKey(GIOVANNIS_MACHAMP, 0)
POWER = str(GUTS)
LATEST = ("この力は、相手のワザによるダメージで、このカードが「きぜつ」するとき、使える。コインを投げて「おもて」なら、このカードは「きぜつ」"
          "せず、このカードの残りHPが「10」になる。ダメージを受けるとき、すでにこのカードが「ねむり・マヒ・こんらん」状態だったなら、この力は"
          "使えない。")
PRINTED = ("この力は、相手のワザによるダメージで、このカードが「きぜつ」する時、使える。コインを投げて「おもて」なら、このカードは「きぜつ」"
           "せず、このカードの残りHPは「10」になる。ダメージを受ける時、すでにこのカードが「ねむり・マヒ・こんらん」状態だったなら、この力は"
           "使えない。")
GUTS_KINDS = ("ko_prevention_declined", "ko_prevention_declared", "ko_prevented", "ko_prevention_failed")
SPECIAL_PUNCH = {"card": HITMONCHAN, "energy": [FIGHTING] * 3}  # エビワラー: ジャブ 20（0）・スペシャルパンチ 40（1）。HP 70
NO_BENCH = ()


def gmachamp(**extra):
    return {"card": GIOVANNIS_MACHAMP, "evolved_from": [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], **extra}


def board(attacker, defender=None, *, bench0=(), bench1=None, hand0=(), hand1=(), prizes0=6, prizes1=6, turn=TURN, effects=None):
    """プレイヤー 0（番のプレイヤー）がワザを使う。プレイヤー 1 のバトル場に、既定でサカキのカイリキー（こんじょう）。"""
    return build_test_state([
        {"active": attacker, "bench": list(bench0) or [PONYTA], "hand": list(hand0), "prizes": prizes0},
        {"active": defender or gmachamp(), "bench": [RATTATA] if bench1 is None else list(bench1), "hand": list(hand1), "prizes": prizes1},
    ], turn_number=turn, effects=effects)


def run(state, command, *sides):
    """コインの結果を決めてコマンドを処理する。(新しい状態, 新しいログ, 進んだ乱数の回数)。"""
    start = with_coin_results(state, *sides) if sides else state
    new = apply_command(start, command)
    assert check_invariants(new) == []
    return new, [dict(e) for e in new.log[len(start.log):]], rng_draws(start, new)


def answer(state, use, *sides):
    """「こんじょう」を使うかの決定に答える（use なら対象のポケモンを選ぶ。選ばなければ使わない）。"""
    d = state.decision
    return run(state, ResolveDecision(d.player, d.id, d.options[:1] if use else ()), *sides)


def kinds(events):
    return [e["kind"] for e in events if e["kind"] not in ("turn_end", "pokemon_check", "turn_start", "draw")]


def guts(events):
    return [e for e in events if e["kind"] in GUTS_KINDS]


def written(state, version=9):
    return state_to_dict(state, format_version=version)


def unchanged(test, before, after):
    """拒否の前後で、状態（形式 9 の書き出し。ログ・乱数の指紋を含む）が同じ。"""
    test.assertEqual(written(after), written(before))
    test.assertEqual(rng_fingerprint(after.rng), rng_fingerprint(before.rng))


class SelfHit(AttackEffect):
    """テスト専用: ワザを使うポケモン自身に ``amount`` ダメージ（p.320 のダメージの (3)）。サカキのカイリキーが自分のワザで自分に
    ダメージを与える場合（G4）を確かめるため（対応カードにない）。"""

    implementation_id = "test_self_hit"

    def __init__(self, amount=20):
        self.amount = amount

    def check(self, attack):
        return []

    def damage_profile(self, state, use):
        return DamageProfile(self_damage=(self.amount,))

    def resolve(self, state, use):
        deal_attack_damage(state, use, SELF, self.amount)


class FixedDamage(AttackEffect):
    """テスト専用: 相手の対戦ポケモンに ``amount`` の基本となるダメージ（説明のあるワザの代わりに、効果のないダメージを与えるため）。"""

    implementation_id = "test_fixed_damage"

    def __init__(self, amount):
        self.amount = amount

    def check(self, attack):
        return []

    def damage_profile(self, state, use):
        return DamageProfile(opponent=(self.amount,))

    def resolve(self, state, use):
        damage_opponent_active(state, use, self.amount)


def replaced_attack(card_id, index, effect):
    attack = load_card_pool().get(card_id).attacks[index]
    return DEFAULT_EFFECTS.with_attacks("test-v0.11", {AttackKey(card_id, index): AttackEntry(effect, attack.name_ja, text_ja=attack.text_ja)})


class RegistrationTest(unittest.TestCase):
    """G1・G41（登録と、決められたとき以外の使用）。"""

    def test_registered_as_a_declared_power(self):
        """「使える」と書かれた特殊能力（p.193）を、宣言して使う特殊能力（declared）として登録している（自動的にはたらく「はたらく」とは
        別。G1）。実装がしたがうのは最新の説明（p.6・p.193）、照合は kyuura の写しの印刷の文面。"""
        entry = DEFAULT_EFFECTS.power_entry(GIOVANNIS_MACHAMP, 0)
        self.assertIsInstance(entry.effect, PreventKnockOutOnHeads)
        self.assertTrue(entry.effect.declared)
        self.assertEqual(entry.effect.remaining_hp, 10)
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), ("こんじょう", PRINTED, LATEST, "P43 p.193"))
        pool = load_card_pool()
        self.assertTrue(pool.is_playable(GIOVANNIS_MACHAMP))
        self.assertEqual([p.name_ja for p in pool.get(GIOVANNIS_MACHAMP).powers], ["こんじょう"])

    def test_use_pokemon_power_is_rejected_outside_the_timing(self):
        """自分の番に UsePokemonPower で使おうとしたら POWER_NOT_USABLE_NOW（「相手のワザによるダメージで…きぜつするとき、使える」。
        p.311「決められたときにしか使用を宣言できないもの」）。バトル場・ベンチ・ダメージのあるとき、どれも状態・ログ・乱数を変えない。"""
        for spec in ({"active": gmachamp(energy=[FIGHTING]), "bench": [RATTATA]},
                     {"active": RATTATA, "bench": [gmachamp(damage=90)]}):
            state = build_test_state([spec, {"active": RATTATA}], turn_number=TURN)
            pid = next(pk.pokemon_id for pk in state.players[0].in_play() if state.cards[pk.card].card_id == GIOVANNIS_MACHAMP)
            with self.subTest(spec=spec):
                with self.assertRaises(IllegalActionError) as raised:
                    apply_command(state, UsePokemonPower(0, pid, 0))
                self.assertEqual(raised.exception.code, "POWER_NOT_USABLE_NOW")

    def test_gas_is_checked_before_the_timing(self):
        """かがくへんかガスがはたらいていれば、決められたときかより先に POWER_SUPPRESSED（v0.8 の確かめる順番。API の約束）。"""
        state = build_test_state([{"active": gmachamp(), "bench": [{"card": MUK, "evolved_from": GRIMER}]}, {"active": RATTATA}],
                                 turn_number=TURN)
        with self.assertRaises(IllegalActionError) as raised:
            apply_command(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        self.assertEqual(raised.exception.code, "POWER_SUPPRESSED")

    def test_not_strikes_back(self):
        """サカキのカイリキーは「はんげき」を持たない（第1弾のカイリキーとは別のカード。ダメージを受けても与えない）。"""
        new, events, _ = run(board(SPECIAL_PUNCH), UseAttack(0, 1))
        self.assertEqual(kinds(events), ["attack", "damage"])
        self.assertEqual(new.players[0].active.damage, 0)


class OfferTest(unittest.TestCase):
    """G2・G10〜G13・G15・G32（使うかを決めさせる時点・決定の形）。D1 の致死量・致死量未満・ダメージ 0。D5 の選択前の状態。"""

    def test_lethal_attack_damage_offers_the_decision(self):
        """相手のワザ（スペシャルパンチ 40）で HP 以上（80 + 40 = 120）になったら、ワザの要素をすべて処理したあとのきぜつの判定で、
        きぜつの処理（トラッシュ・サイド・交代）の前に、持ち主（プレイヤー 1）に使うかを決めさせる（G2・G10・G12・G15・G32）。
        決定は KO_PREVENTION（選ぶ数 0〜1。選ばない = 使わない）。コインはまだ投げていない（乱数は進んでいない。G13）。番のプレイヤーは
        ワザを使ったプレイヤーのまま。HP 以上のダメージのまま場に残るのは、この決定を待つ間だけ（不変条件）。"""
        state = board(SPECIAL_PUNCH, gmachamp(damage=80))
        target = state.players[1].active
        new, events, draws = run(state, UseAttack(0, 1))
        self.assertEqual(kinds(events), ["attack", "damage"])
        self.assertEqual((draws, coin_events(new, len(state.log))), (0, []))
        d = new.decision
        self.assertEqual((new.phase, d.kind, d.player, d.options, d.min_choices, d.max_choices, d.resume),
                         (Phase.DECISION, KO_PREVENTION, 1, (target.pokemon_id,), 0, 1, "knock_out"))
        self.assertEqual(dict(d.context), {"attack": (0, state.players[0].active.pokemon_id, HITMONCHAN, 1), "power": (GIOVANNIS_MACHAMP, 0)})
        self.assertEqual((new.current_player, new.turn_number), (0, TURN))
        self.assertEqual(new.players[1].active.damage, 120)
        self.assertEqual((len(new.players[0].prizes), new.players[1].discard), (6, []))
        self.assertEqual(written(new)["decision"]["kind"], "ko_prevention")
        with self.assertRaises(ValueError):
            state_to_dict(new, format_version=1)  # 形式 1 は決定の中身を表せない（黙って落とさない）

    def test_exactly_hp_offers(self):
        """ダメージがちょうど HP（60 + 40 = 100）でもきぜつするので決めさせる（p.323「HP以上のダメージを受けると」）。"""
        new, _, _ = run(board(SPECIAL_PUNCH, gmachamp(damage=60)), UseAttack(0, 1))
        self.assertEqual(new.decision.kind, KO_PREVENTION)

    def test_below_lethal_does_not_offer(self):
        """HP 未満（50 + 40 = 90）ならきぜつしないので、決定もコインもない（D1）。"""
        new, events, draws = run(board(SPECIAL_PUNCH, gmachamp(damage=50)), UseAttack(0, 1))
        self.assertEqual((guts(events), draws, new.current_player), ([], 0, 1))
        self.assertEqual(new.players[1].active.damage, 90)

    def test_zero_damage_does_not_offer(self):
        """最終ダメージが 0（ジャブ 20 − ディフェンダー 20）なら「ダメージを受けなかった」（p.319）ので、HP 90 のままきぜつしない（D1）。"""
        state = board(SPECIAL_PUNCH, gmachamp(damage=90, trainers=[(DEFENDER, TURN)]))
        new, events, _ = run(state, UseAttack(0, 0))
        self.assertEqual(guts(events), [])
        self.assertEqual(new.players[1].active.damage, 90)

    def test_offer_is_after_every_attack_element(self):
        """ワザの要素（相手へのダメージ・コイン・自分へのダメージ）をすべて処理してから決めさせる（p.309「ワザを使っている最中に、…特殊能力の
        使用を宣言してはいけません」。G2・G32）。でんげき（30。「うら」なら自分にも 10）: 決定の前に、ワザのコインも自分へのダメージも
        処理している。"""
        pikachu = {"card": PIKACHU, "energy": [LIGHTNING] * 2}
        new, events, draws = run(board(pikachu, gmachamp(damage=70)), UseAttack(0, 1), T)
        self.assertEqual(kinds(events), ["attack", "damage", "coin_flip", "damage"])
        self.assertEqual((draws, new.decision.kind, new.players[0].active.damage), (1, KO_PREVENTION, 10))


class UseTest(unittest.TestCase):
    """G11・G13・G14・G17〜G24（使う・使わない・コイン・残り HP）。D1・D4 の成功・失敗。"""

    def setUp(self):
        self.state, _, _ = run(board(SPECIAL_PUNCH, gmachamp(damage=80)), UseAttack(0, 1))
        self.pid = self.state.players[1].active.pokemon_id

    def test_heads_is_not_knocked_out_and_has_10_hp(self):
        """使う → 宣言（ko_prevention_declared）→ 持ち主のコイン 1 枚（source power）→「おもて」（ko_prevented）。ダメージは HP − 10 = 90
        （残り HP 10。ダメージカウンター 9 個。G18・G20・G21）。きぜつせず（トラッシュ・サイドなし。G32・G33）、番は終わる。"""
        new, events, draws = answer(self.state, True, H)
        self.assertEqual(kinds(events), ["ko_prevention_declared", "coin_flip", "ko_prevented"])
        declared, coin, prevented = events[0], events[1], events[2]
        self.assertEqual({k: declared[k] for k in ("player", "pokemon_id", "power", "total_damage", "hp")},
                         {"player": 1, "pokemon_id": self.pid, "power": POWER, "total_damage": 120, "hp": 100})
        self.assertEqual((coin["source"], coin["player"], coin["effect"], coin["pokemon_id"], coin["result"]), ("power", 1, POWER, self.pid, "heads"))
        self.assertEqual({k: prevented[k] for k in ("player", "pokemon_id", "power", "result", "damage_before", "total_damage", "remaining_hp")},
                         {"player": 1, "pokemon_id": self.pid, "power": POWER, "result": "heads", "damage_before": 120, "total_damage": 90,
                          "remaining_hp": 10})
        machamp = new.players[1].active
        self.assertEqual((machamp.pokemon_id, machamp.damage, len(machamp.evolution_stack)), (self.pid, 90, 2))
        self.assertEqual((draws, len(new.players[0].prizes), new.players[1].discard), (1, 6, []))
        self.assertEqual((new.phase, new.current_player, new.turn_number), (Phase.MAIN, 1, TURN + 1))

    def test_tails_is_knocked_out(self):
        """「うら」なら何もしない（ko_prevention_failed）で、ふつうにきぜつする（トラッシュ・サイド・交代。G19・G34）。"""
        new, events, draws = answer(self.state, True, T)
        self.assertEqual(kinds(events), ["ko_prevention_declared", "coin_flip", "ko_prevention_failed", "knock_out"])
        self.assertEqual(events[2]["total_damage"], 120)
        self.assertEqual(draws, 1)
        self.assertIsNone(new.players[1].active)
        self.assertEqual((new.decision.kind, new.decision.player), ("take_prize", 0))
        self.assertEqual(sorted(new.cards[u].card_id for u in new.players[1].discard),
                         sorted([GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHAMP]))

    def test_decline_is_knocked_out_without_a_coin(self):
        """使わない（選ばない）: 宣言しない（ko_prevention_declined）。コインを投げない（乱数を使わない）で、ふつうにきぜつする（G10・G11）。"""
        new, events, draws = answer(self.state, False)
        self.assertEqual(kinds(events), ["ko_prevention_declined", "knock_out"])
        self.assertEqual((draws, coin_events(new, len(self.state.log))), (0, []))
        self.assertEqual((new.decision.kind, new.decision.player), ("take_prize", 0))

    def test_not_asked_twice(self):
        """使わなかった・「うら」だったあと、同じきぜつの判定で再び決めさせない（G14）。"""
        for use, sides in ((False, ()), (True, (T,))):
            new, events, _ = answer(self.state, use, *sides)
            self.assertEqual(len(guts(events)), 1 if not use else 2)
            self.assertNotEqual(new.decision.kind, KO_PREVENTION)

    def test_overkill_still_leaves_10_hp(self):
        """HP を大きく超えるダメージ（ユンゲラーのちょうねんりき 50 × 弱点 2 = 100。90 + 100 = 190）でも「おもて」なら残り HP 10（G23）。"""
        kadabra = {"card": KADABRA, "evolved_from": ABRA, "energy": [PSYCHIC] * 3}
        state, events, _ = run(board(kadabra, gmachamp(damage=90)), UseAttack(0, 1))
        self.assertEqual((events[-1]["amount"], state.players[1].active.damage), (100, 190))
        new, events, _ = answer(state, True, H)
        self.assertEqual((events[2]["damage_before"], new.players[1].active.damage), (190, 90))

    def test_damage_was_received(self):
        """ダメージを受けたことは変わらない（ダメージを無効にするのではない。G21・G22）: ワザの damage のログは最終ダメージのまま。
        受けたダメージで回復するワザ（メガドレイン 40。与えたダメージの半分）は、与えたダメージで回復する。"""
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS] * 4, "damage": 30}
        state, events, _ = run(board(butterfree, gmachamp(damage=70)), UseAttack(0, 1))
        self.assertEqual([e["kind"] for e in events if e["kind"] in ("damage", "drain_heal")], ["damage", "drain_heal"])
        self.assertEqual((state.players[0].active.damage, state.decision.kind), (10, KO_PREVENTION))
        new, _, _ = answer(state, True, H)
        self.assertEqual((new.players[0].active.damage, new.players[1].active.damage), (10, 90))

    def test_reuse_on_a_later_attack(self):
        """「何回もきぜつをまぬがれることができるかもしれません」（p.193 の解説）: 使った回数を数えない。残り HP 10 で次の相手の番を迎え、
        また致死量のワザを受けたら、また使える（G9・G24）。"""
        state = board(SPECIAL_PUNCH, gmachamp(damage=80))
        state, _, _ = run(state, UseAttack(0, 1))
        state, _, _ = answer(state, True, H)
        state, _, _ = run(state, EndTurn(1))  # 9 番（プレイヤー 0）
        self.assertEqual((state.current_player, state.players[1].active.damage), (0, 90))
        state, events, _ = run(state, UseAttack(0, 0))  # ジャブ 20 → 110
        self.assertEqual(state.decision.kind, KO_PREVENTION)
        new, events, _ = answer(state, True, H)
        self.assertEqual((events[2]["damage_before"], new.players[1].active.damage), (110, 90))
        self.assertEqual(len([e for e in new.log if e["kind"] == "ko_prevented"]), 2)


class SourceTest(unittest.TestCase):
    """G3〜G7（ダメージの発生源）。D2。"""

    def test_own_attack_self_damage_does_not_offer(self):
        """自分のワザ（テスト専用: サカキのカイリキーが自分に 20）で HP 以上になっても使えない（「相手のワザによるダメージで」。G4）。"""
        effects = replaced_attack(GIOVANNIS_MACHAMP, 0, SelfHit(20))
        state = build_test_state([{"active": gmachamp(damage=90, energy=[FIGHTING] * 4), "bench": [RATTATA]}, {"active": RATTATA}],
                                 turn_number=TURN, effects=effects)
        new, events, _ = run(state, UseAttack(0, 0))
        self.assertEqual(guts(events), [])
        self.assertEqual([e["kind"] for e in events if e["kind"] == "knock_out"], ["knock_out"])
        self.assertEqual((new.decision.kind, new.decision.player), ("take_prize", 1))

    def test_confusion_damage_does_not_offer(self):
        """こんらんのサカキのカイリキーがワザを使い「うら」で自分に 20（ワザがこんらんしたダメージ。相手のワザではない・こんらんでもある。
        G4・G27）。"""
        state = build_test_state([{"active": gmachamp(damage=90, energy=[FIGHTING] * 4, confusion=True), "bench": [RATTATA]},
                                  {"active": RATTATA}], turn_number=TURN)
        new, events, _ = run(state, UseAttack(0, 0), T)
        self.assertEqual(guts(events), [])
        self.assertIn("knock_out", kinds(events))

    def test_strikes_back_damage_does_not_offer(self):
        """「はんげき」（特殊能力によるダメージ。v0.10 の C13）でサカキのカイリキーが HP 以上になっても使えない（G5・G39）。ハリケーンパンチ
        （「おもて」2 枚で 60 − ディフェンダー 2 枚 40 = 20）を第1弾のカイリキーに使い、「はんげき」10 で 90 + 10 = 100。"""
        attacker = gmachamp(damage=90, energy=[FIGHTING] * 4)
        defender = {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], "trainers": [(DEFENDER, TURN), (DEFENDER, TURN)]}
        new, events, _ = run(board(attacker, defender), UseAttack(0, 0), H, H, T, T)
        self.assertEqual(kinds(events)[-3:], ["damage", "counterattack", "knock_out"])
        self.assertEqual(guts(events), [])
        self.assertEqual((new.decision.kind, new.decision.player), ("take_prize", 1))

    def test_damage_swap_cannot_knock_out(self):
        """ダメージスワップ（ダメージカウンターの移動。ダメージを受けたことにならない。p.320）は、きぜつさせる移動を WOULD_KNOCK_OUT で
        拒否する（v0.7。p.153）ので、こんじょうを使う場面にならない（G6）。"""
        state = build_test_state([
            {"active": {"card": ALAKAZAM, "evolved_from": [ABRA, KADABRA]}, "bench": [gmachamp(damage=90), {"card": RATTATA, "damage": 10}]},
            {"active": RATTATA},
        ], turn_number=TURN)
        rattata, machamp = state.players[0].bench[1], state.players[0].bench[0]
        with self.assertRaises(IllegalActionError) as raised:
            apply_command(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0, source=rattata.pokemon_id, target=machamp.pokemon_id))
        self.assertEqual(raised.exception.code, "WOULD_KNOCK_OUT")

    def test_poison_damage_does_not_offer(self):
        """ポケモンチェックのどく（ワザによるダメージではない。p.321）で HP 以上になっても使えない（p.193 の解説「どくのダメージによる場合
        などには効果ありません」。G7）。"""
        state = board(SPECIAL_PUNCH, gmachamp(damage=90, poison=10))
        new, events, _ = run(state, EndTurn(0))
        self.assertEqual(guts(events), [])
        knock = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual(knock["timing"], "pokemon_check")
        self.assertEqual((new.decision.kind, new.decision.player), ("take_prize", 0))

    def test_offer_needs_this_attacks_damage(self):
        """HP 以上の「こんじょう」のポケモンに、このワザのダメージを受けた記録がなければ、エンジンの不具合として止める（推測で決めない）。
        盤面を直接作った（自然な対戦では、番の途中に HP 以上のポケモンは場にいない）。v0.16b: きぜつの判定の窓の候補を求める解決の基盤の
        関数（``kernel.ko_prevention_offers``。v0.15 までは v0.13 の経路の ``engine._ko_prevention_offer``）で確かめる。"""
        state = board(SPECIAL_PUNCH, gmachamp(damage=100))
        with self.assertRaises(RuntimeError):
            ko_prevention_offers(Resolution(state))


class ConditionAndGasTest(unittest.TestCase):
    """G25〜G31（特殊状態・かがくへんかガス）。D3。"""

    def test_asleep_paralyzed_confused_cannot_use(self):
        """ダメージを受けるとき、すでにねむり・マヒ・こんらんなら使えない（決定なし。ふつうにきぜつ。G25〜G27・G29）。"""
        for condition in ({"sleep": True}, {"paralysis": TURN - 1}, {"confusion": True}):
            with self.subTest(condition=condition):
                new, events, draws = run(board(SPECIAL_PUNCH, gmachamp(damage=80, **condition)), UseAttack(0, 1))
                self.assertEqual(guts(events), [])
                self.assertEqual((draws, new.decision.kind), (0, "take_prize"))

    def test_poisoned_can_use(self):
        """どくは挙げられていない（G28）。「おもて」なら残り HP 10 のまま、どくも残る（きぜつしていない。p.322）。"""
        state, _, _ = run(board(SPECIAL_PUNCH, gmachamp(damage=80, poison=10)), UseAttack(0, 1))
        self.assertEqual(state.decision.kind, KO_PREVENTION)
        state = with_coin_results(state, H)
        d = state.decision
        new = apply_command(state, ResolveDecision(1, d.id, d.options))
        # 番の終わりのポケモンチェックで、どく 10 → 100 できぜつする（どくのダメージでは使えない。G7・G38）
        self.assertIsNone(new.players[1].active)
        self.assertEqual([e["kind"] for e in new.log if e["kind"] in GUTS_KINDS], ["ko_prevention_declared", "ko_prevented"])
        self.assertEqual(next(e for e in new.log if e["kind"] == "knock_out")["timing"], "pokemon_check")

    def test_recovered_condition_can_use(self):
        """特殊状態が回復したあと（ねむりのポケモンチェックで「おもて」）に受けたダメージでは使える（D3 の特殊状態の回復）。"""
        state = board(SPECIAL_PUNCH, gmachamp(damage=80, sleep=True))
        state, events, _ = run(state, EndTurn(0), H)  # 7 番の終わりのポケモンチェック: ねむりのコイン「おもて」で回復
        self.assertTrue(any(e["kind"] == "sleep_check" for e in events))
        self.assertIsNone(state.players[1].active.conditions.exclusive)
        state, _, _ = run(state, EndTurn(1))
        state, _, _ = run(state, UseAttack(0, 1))
        self.assertEqual(state.decision.kind, KO_PREVENTION)

    def test_gas_suppresses(self):
        """はたらいているかがくへんかガスがあれば使えない（決定なし。G31）。ワザを使った側・使われた側のどちらのベトベトンでも（p.48）。
        ベトベトンがねむり・マヒ・こんらんならガスは消えていて、使える（v0.8 の continuous.suppressors_of。抑止の判定を複製しない）。"""
        muk = {"card": MUK, "evolved_from": GRIMER}
        for bench0, bench1 in (([muk], None), ((), [muk])):
            with self.subTest(bench0=bench0, bench1=bench1):
                new, events, _ = run(board(SPECIAL_PUNCH, gmachamp(damage=80), bench0=bench0, bench1=bench1), UseAttack(0, 1))
                self.assertEqual(guts(events), [])
                self.assertEqual(new.decision.kind, "take_prize")
        # ガスが消えている: ワザを使う側のバトル場のベトベトンがこんらん（テスト専用の効果でヘドロこうげきを 40 のダメージだけにする）
        effects = replaced_attack(MUK, 0, FixedDamage(40))
        attacker = {"card": MUK, "evolved_from": GRIMER, "energy": [GRASS] * 3, "confusion": True}
        new, _, _ = run(board(attacker, gmachamp(damage=80), effects=effects), UseAttack(0, 0), H)
        self.assertEqual(new.decision.kind, KO_PREVENTION)

    def test_public_query(self):
        """公開の問い合わせ ``available_ko_prevention_power``: 持っていて、ねむり・マヒ・こんらんでなく、ガスに消されていなければ PowerKey。
        場所は見ない（ベンチでも。G8）。場にいない番号は ValueError。"""
        state = board(SPECIAL_PUNCH, gmachamp(), bench1=[gmachamp(), RATTATA])
        active, bench = state.players[1].active, state.players[1].bench[0]
        self.assertEqual(available_ko_prevention_power(state, active.pokemon_id), GUTS)
        self.assertEqual(available_ko_prevention_power(state, bench.pokemon_id), GUTS)
        self.assertIsNone(available_ko_prevention_power(state, state.players[1].bench[1].pokemon_id))
        for condition in ({"sleep": True}, {"confusion": True}):
            asleep = board(SPECIAL_PUNCH, gmachamp(**condition))
            self.assertIsNone(available_ko_prevention_power(asleep, asleep.players[1].active.pokemon_id))
        gassed = board(SPECIAL_PUNCH, gmachamp(), bench0=[{"card": MUK, "evolved_from": GRIMER}])
        self.assertIsNone(available_ko_prevention_power(gassed, gassed.players[1].active.pokemon_id))
        self.assertEqual(ko_prevention_power(gassed, gassed.players[1].active)[0], GUTS)  # 持っていることは変わらない
        with self.assertRaises(ValueError):
            available_ko_prevention_power(state, 999)

    def test_bench_location_is_not_restricted(self):
        """場所は見ない（最新の説明に場所の制限がない。p.311・p.323「ベンチにいるポケモンも特殊能力を使うことができます」。G8）。ベンチに
        ワザのダメージを与えるワザは対応カードにないので、きぜつの判定の関数で確かめる（盤面を直接作った。自然な対戦では起こらない）。"""
        state = board(SPECIAL_PUNCH, RATTATA, bench1=[gmachamp(damage=110)])
        bench = state.players[1].bench[0]
        res = Resolution(state)  # v0.16b: 解決の基盤のきぜつの判定の窓（v0.15 までは engine._ko_prevention_offer）
        res.ko_prevention_able[bench.pokemon_id] = True
        self.assertEqual([(owner, pokemon, instance.power_key) for owner, pokemon, instance in ko_prevention_offers(res)], [(1, bench, GUTS)])
        res.ko_prevention_able[bench.pokemon_id] = False  # ダメージを受けたときにねむり・マヒ・こんらんだった
        self.assertEqual(ko_prevention_offers(res), [])


class KnockOutAndPrizeTest(unittest.TestCase):
    """G32〜G40（きぜつ・サイド・交代・勝ち負け）。D4。"""

    def test_last_pokemon_heads_and_tails(self):
        """ベンチがいない（最後のポケモン）: 「おもて」なら場に残り対戦は続く。「うら」ならきぜつし、サイドを取ったあと、出せるポケモンが
        いないので負け（p.311・p.323。G36）。"""
        state, _, _ = run(board(SPECIAL_PUNCH, gmachamp(damage=80), bench1=NO_BENCH), UseAttack(0, 1))
        heads, _, _ = answer(state, True, H)
        self.assertEqual((heads.phase, heads.current_player), (Phase.MAIN, 1))
        tails, _, _ = answer(state, True, T)
        tails, _, _ = run(tails, TakePrize(0, 0))
        self.assertEqual((tails.phase, tails.result.winner), (Phase.GAME_OVER, 0))

    def test_bench_promotion_after_tails(self):
        """ベンチがいれば、「うら」のあとサイド → 相手がバトル場に出す（G35）。「おもて」なら交代はない。"""
        state, _, _ = run(board(SPECIAL_PUNCH, gmachamp(damage=80)), UseAttack(0, 1))
        tails, _, _ = answer(state, True, T)
        tails, _, _ = run(tails, TakePrize(0, 0))
        self.assertEqual((tails.decision.kind, tails.decision.player), ("promote_active", 1))
        tails, _, _ = run(tails, PromoteActive(1, tails.players[1].bench[0].card))
        self.assertEqual((tails.phase, tails.current_player), (Phase.MAIN, 1))
        heads, events, _ = answer(state, True, H)
        self.assertNotIn("promote_active", [e["kind"] for e in events])

    def test_last_prize(self):
        """最後のサイドを取るはずのワザ: 「おもて」ならサイドを取らず、勝ちにならない。「うら」なら最後のサイドを取って勝つ（G33・G35）。"""
        state, _, _ = run(board(SPECIAL_PUNCH, gmachamp(damage=80), prizes0=1), UseAttack(0, 1))
        heads, _, _ = answer(state, True, H)
        self.assertEqual((heads.phase, len(heads.players[0].prizes)), (Phase.MAIN, 1))
        tails, _, _ = answer(state, True, T)
        tails, _, _ = run(tails, TakePrize(0, 0))
        self.assertEqual((tails.phase, tails.result.winner), (Phase.GAME_OVER, 0))

    def test_attacker_is_also_knocked_out(self):
        """ワザを使ったポケモンも自分へのダメージで HP 以上（ゴーリキーのじごくぐるま: 相手に 60・自分に 20）: 決定を待つ間は両方が HP 以上で
        場に残る（不変条件の狭い例外）。「おもて」ならワザを使ったポケモンだけがきぜつ（同時ではない。サイドはプレイヤー 1 が 1 枚）。「うら」
        なら両方が同時にきぜつ（p.324。サイドは両方が 1 枚ずつ、番のプレイヤーから）。G38。"""
        machoke = {"card": MACHOKE, "evolved_from": MACHOP, "energy": [FIGHTING] * 4, "damage": 60}
        state, events, _ = run(board(machoke, gmachamp(damage=40)), UseAttack(0, 1))
        self.assertEqual((state.decision.kind, state.players[0].active.damage, state.players[1].active.damage), (KO_PREVENTION, 80, 100))
        heads, events, _ = answer(state, True, H)
        knocks = [e for e in events if e["kind"] == "knock_out"]
        self.assertEqual([(e["player"], e.get("simultaneous")) for e in knocks], [(0, None)])
        self.assertEqual((heads.decision.kind, heads.decision.player), ("take_prize", 1))
        tails, events, _ = answer(state, True, T)
        knocks = [e for e in events if e["kind"] == "knock_out"]
        self.assertEqual([(e["player"], e.get("simultaneous")) for e in knocks], [(1, True), (0, True)])
        self.assertEqual((tails.decision.kind, tails.decision.player, dict(tails.decision.context)["remaining"]), ("take_prize", 0, (1,)))

    def test_attacker_knocked_out_by_its_own_attack_only(self):
        """サカキのゴーリキーのいちかばちか「うら」: 相手にはダメージを与えず、自分に 100（自分のワザによるきぜつ。こんじょうは関係しない。
        ワザを使ったポケモンが先にきぜつの候補になる場合）。"""
        machoke = {"card": GIOVANNIS_MACHOKE, "evolved_from": GIOVANNIS_MACHOP, "energy": [FIGHTING]}
        new, events, _ = run(board(machoke, gmachamp(damage=90)), UseAttack(0, 0), T)
        self.assertEqual(guts(events), [])
        self.assertEqual(new.players[1].active.damage, 90)
        self.assertEqual((new.decision.kind, new.decision.player), ("take_prize", 1))

    def test_c18_is_unchanged(self):
        """C18（v0.10）: サカキのカイリキーのハリケーンパンチで第1弾のカイリキーがきぜつしうるうえ、その「はんげき」でサカキのカイリキーが
        きぜつしうるなら、ワザの宣言の前に UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT で止める（「はんげき」は特殊能力のダメージなので、
        こんじょうはこの問いを解決しない。G39）。状態・乱数は変わらない。"""
        attacker = gmachamp(damage=90, energy=[FIGHTING] * 4)
        state = board(attacker, {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], "damage": 40})
        with self.assertRaises(UnsupportedError) as raised:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual(raised.exception.code, "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")


class G37Test(unittest.TestCase):
    """G30・G37: 「こんじょう」を使える相手が、ダメージで HP 以上になりうるうえ、同じワザで相手に効果（特殊状態・入れ替え）を与えるワザは、
    「おもて」で「きぜつ」しなかったポケモンがその効果を受けるかが原典で決められないので、ワザの宣言の前（こんらんのコインの前）に止める。"""

    CODE = "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT"

    def assert_stopped(self, state, command):
        with self.assertRaises(UnsupportedError) as raised:
            apply_command(state, command)
        self.assertEqual(raised.exception.code, self.CODE)
        # 拒否は状態を変えない（apply_command は複製してから処理する）。どのコインの結果でも同じ（コインの前に止める）
        for sides in ((H,), (T,), (H, H), (T, T)):
            with self.assertRaises(UnsupportedError):
                apply_command(with_coin_results(state, *sides), command)

    def test_effect_after_lethal_damage_is_stopped(self):
        caterpie = {"card": CATERPIE, "energy": [GRASS]}  # いとをはく 10・「おもて」ならマヒ
        self.assert_stopped(board(caterpie, gmachamp(damage=90)), UseAttack(0, 0))
        machoke = {"card": GIOVANNIS_MACHOKE, "evolved_from": GIOVANNIS_MACHOP, "energy": [FIGHTING] * 3}  # じごくがため 20+（「おもて」40）
        self.assert_stopped(board(machoke, gmachamp(damage=60)), UseAttack(0, 1))  # 「おもて」の 40 で HP 以上になりうる
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS] * 2}  # ふきとばし 20・入れ替え
        self.assert_stopped(board(butterfree, gmachamp(damage=80)), UseAttack(0, 0))
        confused_vulpix = {"card": VULPIX, "energy": [FIRE] * 2, "confusion": True}  # あやしいひかり。こんらんのコインの前に止める
        self.assert_stopped(board(confused_vulpix, gmachamp(damage=90)), UseAttack(0, 0))

    def test_not_stopped_when_not_lethal_or_not_usable(self):
        """HP 以上にならない・「こんじょう」を使えない（ねむり・かがくへんかガス）なら止めない（使えないなら v0.4d どおり、きぜつして効果は
        与えない）。"""
        caterpie = {"card": CATERPIE, "energy": [GRASS]}
        new, _, _ = run(board(caterpie, gmachamp(damage=80)), UseAttack(0, 0), H)
        self.assertTrue(new.players[1].active.conditions.paralyzed)
        new, events, _ = run(board(caterpie, gmachamp(damage=90, sleep=True)), UseAttack(0, 0), H)
        self.assertEqual((guts(events), new.decision.kind), ([], "take_prize"))
        self.assertNotIn("special_condition", [e["kind"] for e in events])
        new, events, _ = run(board(caterpie, gmachamp(damage=90), bench0=[{"card": MUK, "evolved_from": GRIMER}]), UseAttack(0, 0), H)
        self.assertEqual((guts(events), new.decision.kind), ([], "take_prize"))

    def test_declared_elements_match_the_implementations(self):
        """``opponent_effect_elements`` を宣言した実装の組と、相手の対戦ポケモンに効果（ダメージ以外の要素）を与える実装の組が同じ（宣言の
        書き忘れで G37 を見落とさない）。要素の種類も同じ。v0.16b: 標準の実装は ``resolve`` を持たない（解決の基盤の要素の並びで処理する）
        ので、効果を与えるかは、登録されたワザの実装の要素の並び（``programs.opponent_effect_elements``）から求める（v0.15 までは実装の
        ``resolve`` の中の ``attack_reaches`` の呼び出しを読んでいた）。"""
        declared, found = {}, {}
        registered = [DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect for k in DEFAULT_EFFECTS.attack_keys()]
        for name, cls in inspect.getmembers(effects_module, inspect.isclass):
            if not issubclass(cls, AttackEffect) or cls is AttackEffect:
                continue
            if isinstance(cls.opponent_effect_elements, property):
                # v0.41: 要素が登録の値で決まる型（エリカのナゾノクサの「へんなこな」の ``DamageThenStatusByCoin``）は、登録した実装の宣言で数える
                values = [set(effect.opponent_effect_elements) for effect in registered if type(effect) is cls]
                if values:
                    declared[name] = set().union(*values)
            elif cls.opponent_effect_elements:
                declared[name] = set(cls.opponent_effect_elements)
        for key in DEFAULT_EFFECTS.attack_keys():
            effect = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index).effect
            elements = set(programs.opponent_effect_elements(programs.compile_attack(effect)))
            if elements:
                # v0.72: 要素が登録の値で決まる型（StatusByCoinWithoutDamage のマヒとねむり（めまわし）・こんらんとねむり（ぐるぐる））は、登録したワザの要素を合わせて数える
                # （宣言の側の合わせ方と同じ。v0.71 までは、その型の登録の要素がどれも同じだった）
                found.setdefault(type(effect).__name__, set()).update(elements)
        self.assertEqual(declared, found)
        self.assertTrue(all(elements <= set(ATTACK_ELEMENTS) - {DAMAGE_ELEMENT} for elements in declared.values()))
        # v0.17a で ConfuseOnHeadsWithoutDamage（ねこノミ。こんらん）を加えた。v0.31 で、相手の対戦ポケモンに効果を与える 6 つの型を加えた
        # （相手のエネルギーのトラッシュ・「ワザを使えない」持続する効果・入れ替え・ねむり・マヒ。docs/held-cards-v0.31.md）。v0.33 で 2 つ
        self.assertEqual(sorted(declared), sorted([
            "CoinBonusDamageAndParalyze", "ConfuseOnHeads", "ConfuseOnHeadsWithoutDamage", "DamageAndForceSwitch", "ParalyzeOnHeads",
            "PoisonOnHeads", "PoisonOpponent", "PoisonWithoutDamage", "PutToSleep", "SleepOpponent",
            # v0.31
            "CannotAttackOnHeads", "CoinDiscardOpponentEnergyEach", "DamageThenDiscardEachEnergy", "DamageThenParalyzeOrSelfDamage",
            "SleepOnHeadsWithoutDamage", "SwitchOpponentActive",
            # v0.33（相手のエネルギーのトラッシュ・マヒ。docs/cd4-opponent-energy-coins-v0.33.md）
            "DamageThenDiscardOpponentEnergy", "DamageAndParalyzeOnHeadsElseFail",
            # v0.34（1 枚のコインでどくかこんらん・特殊などく・与えるダメージがへる持続する効果。docs/barrier-resume-coin-bonus-v0.34.md）
            "DamageThenPoisonOrConfuse", "DamageAndSpecialPoison", "ReduceDamageToSelf",
            # v0.35（相手の選んだワザを使えなくする持続する効果「ドわすれ」。docs/coin-groups-damage-order-v0.35.md）
            "LockOpponentAttack",
            # v0.36（手順 4 のコインの持続する効果・「にげる」ことができない持続する効果。docs/sand-attack-retreat-lock-v0.36.md）
            "DamageThenAttackCoinCheck", "DamageThenRetreatLock",
            # v0.37（ダメージのないコインのどく・マヒと、なきつくと同じ与えるダメージがへる持続する効果。docs/fifteen-reused-effects-v0.37.md）
            "PoisonOnHeadsWithoutDamage", "ParalyzeOnHeadsWithoutDamage", "DamageThenReduceDamageToSelf",
            # v0.38（コインで相手が選ぶ入れ替え・入れ替えのあと自分にもダメージ・1 枚のコインでどくかマヒ・自分にもダメージのあとコインでどく。
            # docs/bench-switch-combined-v0.38.md）
            "DamageThenForceSwitchOnHeads", "DamageThenForceSwitchThenSelfDamage", "DamageThenPoisonOrParalyze", "DamageAndSelfDamageThenPoisonOnHeads",
            # v0.39（コインで特殊などく・同じコインでどくと控えへのダメージ。docs/selfdestruct-spread-count-v0.39.md）
            "DamageThenSpecialPoisonOnHeads", "CoinPoisonAndBenchDamage",
            # v0.40（条件つきでワザを使えなくする持続する効果・入れ替えてからダメージ・相手の対戦ポケモンを山札にもどす。
            # docs/count-condition-switch-return-v0.40.md）
            "AttackLockWhileSourceActive", "SwitchOpponentThenDamage", "ReturnOpponentActiveToDeck",
            # v0.41（相手の特殊状態・「にげる」ことができない持続する効果・入れ替え・回復・ダメージカウンターをのせる／取り替える効果。
            # docs/heal-counter-status-v0.41.md）
            "DamageThenConfuseBoth", "DamageThenStatusByCoin", "DamageThenChosenStatusOnHeads", "CoinDamageAndConfuseElseSelfConfuse",
            "DamageThenConfuseOnAnyHeads", "DamageThenSleepOnHeads", "DamageThenRetreatLockOnHeads", "SwitchOpponentActiveOnHeads",
            "HealAllPokemonBothSides", "MoveOwnCountersToOpponent", "SwapCountersOnHeads",
            # v0.42（相手のポケモンのカウンターをとりのぞく・残り HP が決まった数になるようにカウンターをのせる。docs/power-decisions-v0.42.md）
            "HealChosenOpponentThenDraw", "PlaceCountersToRemainingHpOnHeads",
            # v0.44（きぜつしていなければ入れ替え・1 枚のコインでどくとマヒ・コインで特殊などく。docs/search-evolution-once-attacks-v0.44.md）
            "DamageThenSwitchOpponentIfNotKnockedOut", "DamageThenPoisonAndParalyzeOnHeads", "SpecialPoisonOnHeadsWithoutDamage",
            # v0.45（次の相手の番から消えない手順 4 の効果・2 枚とも「おもて」でどくとこんらん・自分がどくなら相手もどく・コインで入れ替えて
            # 新しい対戦ポケモンをどく・相手の対戦ポケモンのエネルギーを控えにつけかえる。docs/conditional-damage-energy-v0.45.md）
            "DamageThenLastingAttackCoinCheckOnHeads", "DamageThenPoisonAndConfuseOnAllHeads", "DamageIfSelfStatusThenOpponentStatus",
            "CoinSwitchOpponentThenStatus", "DamageThenMoveOpponentEnergyToBench",
            # v0.48（相手の対戦ポケモンの弱点の色を変える・1 枚のコインでどくとこんらん・ダメージカウンターがのっている相手のポケモンにのせる・
            # 2 枚とも「おもて」で相手の対戦ポケモンを山札にもどす。docs/effective-pokemon-properties-v0.48.md）
            "ChangeOpponentWeakness", "DamageThenPoisonAndConfuseOnHeads", "PlaceCountersOnDamagedOpponentPokemon", "DamageThenCoinsReturnOpponentToDeck",
            # v0.50（自分・相手のポケモンの進化カードをはがして手札にもどす「たいかビーム」。docs/mew-devolution-spray-v0.50.md）
            "DevolveChosenPokemon",
            # v0.51（自分・相手のトラッシュのたねポケモンを持ち主のベンチに出し、ダメージカウンターをのせる「よみがえらせる」。docs/discard-to-bench-v0.51.md）
            "BenchBasicFromEitherDiscard",
            # v0.52（自分と相手の対戦ポケモンを山札にもどす「つれさる」。docs/field-return-v0.52.md）
            "ReturnBothActivesToDeck",
            # v0.59（選んだ相手のポケモンが特殊能力を使えなくなる「ショックアイ」・どくと控えへのダメージ「どくのきり」・エネルギーカードをつけられなくなる
            # 「クリスタルビーム」。docs/energy-control-power-suppression-v0.59.md）
            "ChooseOpponentPokemonDamageAndPowerLock", "DamagePoisonAndBenchDamage", "DamageThenAttachLockOnHeads",
            # v0.62（受けたマヒを与えるオニスズメの「オウムがえし」・相手を手札にもどすピジョットの「ハリケーン」。docs/history-attacks-v0.62.md）
            "ReflectReceivedDamageAndEffects", "DamageThenReturnOpponentToHand",
            # v0.70（ダメージのない「ぐるぐる」。DamageThenStatusByCoin と同じ Status の要素。docs/non-pack-effect-reuse-v0.70.md）
            "StatusByCoinWithoutDamage",
            # v0.72（ダメージを与えた後に自分と相手を特殊状態にする・ダメージのないどくとねむり・ねむりから回復させる・ダメージを与えた後に入れ替える。
            # docs/status-coins-effect-reuse-v0.72.md）
            "DamageThenStatusSelfAndOpponent", "PoisonAndSleepWithoutDamage", "DamageThenWakeOpponent", "DamageThenForceSwitchAfterDamage",
            # v0.76（なきごえ・かなしばり・にらみつける。docs/persistent-attack-modifiers-v0.76.md）
            "ReduceDamageToSelfNextOpponentTurn", "LockOpponentAttackOnHeads", "AttackLockWhileSourceActiveOnHeads",
            # v0.78（ダメージの前に相手のトレーナーをトラッシュする「ごうだつ」・ダメージのない「おいつめる」。docs/darkness-metal-energy-v0.78.md）
            "DiscardOpponentTrainersThenDamage", "RetreatLockWithoutDamage",
            # v0.79（1 枚のコインでマヒと相手の控えへのダメージ・1 枚のコインでダメージとこんらん・相手の場のトレーナーをすべてトラッシュする。
            # docs/shared-checks-pokemon-reuse-v0.79.md）
            "DamageThenParalyzeAndOpponentBenchOnHeads", "CoinBonusDamageAndConfuse", "CoinDiscardAllOpponentTrainers",
            # v0.83（相手のエネルギーカードをトラッシュする「やきつくす」・選んだ特殊状態の「ミラクルリーフ」・「おもて」の数で特殊状態が決まる「フラッシュアイ」・
            # 1 枚のコインでこんらんかねむりの「ふしぎなほのお」・ねむりと控えの回復の「ヒプノシャワー」。docs/shining-gentle-pokemon-v0.83.md）
            "DiscardEnergyThenSpreadThenCoinDiscardEach", "CoinsPerDefenderEnergyChosenStatus", "ThreeCoinsStatusByHeads",
            "DiscardEnergyThenCoinConfuseElseSleep", "DamageSleepThenHealBothBench",
        # v0.84: やさしいサンダースの「サンダーニードル」（「おもて」の数で相手をマヒ。docs/light-powers-evolution-v0.84.md）
        "CoinsTimesDamageThenParalyzeIfAtLeast",
        # v0.85: ベイリーフの「あまいかおり」（「うら」なら相手の場のポケモンからダメージカウンターをとりのぞく。回復の要素。ダメージがないので G37 には当たらない。
        # docs/entry-powers-energy-lifecycle-v0.85.md）
        "CoinChosenSideHealAttack",
        # v0.86: スイクンの「オーロラウェーブ」（2 枚のコインでマヒかねむり）・わるいモココの「スタンウェーブ」（相手の対戦ポケモンの特殊能力を止める持続する効果）
        # （docs/entry-energy-evolution-reactions-v0.86.md 7 章）
        "DamageThenParalyzeOrSleepByTwoCoins", "DamageThenStopDefenderPowers",
        # v0.87: カビゴンの「ねころぶ」（「おもて」なら相手もねむり）・フォレトスの「こうそくスピン」（相手の入れ替え）（docs/movement-damage-reactions-v0.87.md 3 章・8 章）。
        # ドガースの「ふしぎなガス」は相手プレイヤーの場に与える期限のある効果で、相手の対戦ポケモンへの要素ではない（宣言しない）
        "DamageThenSelfSleepThenSleepOpponentOnHeads", "DamageThenSwitchBothActives",
        # v0.88: かっこいいポリゴンの「テクスチャーマジック」（相手の対戦ポケモンの弱点の色を変える。docs/type-energy-colors-v0.88.md 6.5 節）
        "ChangeWeaknessAndResistanceOptional",
        # v0.89: レアコイルの「マイクロウェーブ」（選んだ個体のエネルギーカードのトラッシュ）・ベロリンガの「きずをなめる」（おたがいの場から選ぶ回復。docs/selected-target-damage-v0.89.md）
        "ChooseOpponentPokemonDamageThenDiscardEnergyOnHeads", "CoinChooseEitherPokemonHeal",
        # v0.90: ベトベターの「ベトベトえき」・ルージュラの「あくまののろい」・ドーブルの「ペイント」（相手にマーカーをのせる）・ガラガラの「ほねこんぼう」（マヒ。
        # docs/markers-counters-v0.90.md）
        "MarkOpponentIfAbsent", "CoinMarkOpponent", "CoinPaintOpponent", "DamageThenRemoveOwnMarkerParalyzeOnHeads",
        # v0.91: マグマラシの「やきこがす」・エレブーの「ひらいしん」・ポリゴンの「ハイパーテクスチャー」（相手にマーカーをのせる）・「オールクリア」（相手の場のトレーナー・特殊状態・
        # その他の効果・マーカー。docs/marker-check-field-reset-v0.91.md）
        "DamageThenCoinMarkOpponentIfAbsent", "ChooseOpponentPokemonMarkIfAbsent", "ChooseOpponentPokemonReplaceColorMarker", "AllClear",
        # v0.92: イトマルの「こわいかお」（ワザとにげるの禁止）・クモのす・くろいまなざし・ヨーギラスの「にらみつける」（期間を明示した禁止）・いやなおと（受けるダメージの +20）・
        # きゅうけつどく（どく）・やみのはどう（おたがいの場の特殊能力。相手の対戦ポケモンも受ける。docs/power-suppression-lasting-locks-v0.92.md）
        "CoinAttackAndRetreatLock", "PeriodLockAttack", "ReceivedAttackDamageBonusAttack", "DamageDrainThenPoison", "DamageThenFieldPowerSuppression",
        # v0.93: からまるいと・からみつく・くいつく・こおりつかせる（期間を明示した禁止）・ねばるみつ（はなれられない効果）・どくしばり（どくと、はなれられない効果）・からめとる（入れ替えと
        # 新しく出てきたポケモンのマヒ）・かぶりつく（にげるの禁止と手順 4 のコイン。docs/active-leave-locks-v0.93.md）
        "DamageThenPeriodLock", "CoinBonusDamageThenLeaveLock", "DamageThenPoisonThenLeaveLockOnHeads", "SwitchOpponentThenParalyzeNewOnHeads",
        "DamageThenRetreatLockAndAttackCoinCheck",
        # v0.94: このゆびとまれ・ほえる・ふんだりけったり・きつねび（相手の入れ替え）・フローラルスピン（ねむり）・すくいなげ（相手を手札にもどす・入れ替え。docs/switch-return-attacks-v0.94.md）
        "SwitchOpponentActiveRequiringBench", "ForceSwitchOnHeadsWithoutDamage", "CoinBonusDamageElseForceSwitch", "OptionalSwitchOpponentThenDamage",
        "DamageThenStatusOnHeadsElseSelfSwitch", "CoinReturnOpponentToHandElseForceSwitch",
        # v0.95: とりさる（相手の場のポケモンについているトレーナーカードを山札にもどす。ついているポケモンへの効果。docs/private-looks-deck-movement-v0.95.md）
        "ReturnOpponentAttachedTrainerToDeck",
        # v0.100: ほろびのうた（相手をダメージによらず「きぜつ」させる効果。docs/sketch-perish-song-history-v0.100.md）
        "KnockOutIfAsleepAndReceived",
        # v0.104: やさしいうた（相手の対戦ポケモンからとりのぞく効果とねむり。docs/healing-pokemon-v0.104.md）。あまいみつは自分の場から選ぶので、相手に効果を与えない
        "HealBothActivesThenSleep",
        # v0.105: プレゼント（「おもて」の数で相手の対戦ポケモンからとりのぞく効果。docs/recovery-evolution-coin-branches-v0.105.md）。ハイパーリバース・サイコリーフの回復は自分からとりのぞく
        "ThreeCoinDamageOrOpponentHeal",
        # v0.107: とげでつつく（失敗のコインのあとのどく）・へんずつう（コインの「おもて」で相手のこんらん）。とつぜんじばく・そらをとぶは相手の対戦ポケモンへの効果を持たない（自分への
        # ダメージ・控えへのダメージ・自分への防護）。docs/coin-failure-status-flight-v0.107.md
        "FailOnTailsDamageThenPoison", "DamageThenConfuseOpponentOrSelf",
        # v0.108: マイナスイオン・あまえる（使うワザのダメージを減らす効果）・かみくだく（受けるワザのダメージを増やす効果）・もうどく（どく）・たたきおこす（相手の特殊状態の回復）。
        # docs/damage-modifiers-condition-bonuses-v0.108.md
        "DamageThenDealtDamageReduction", "DealtDamageReductionWithoutDamage", "DamageThenReceivedAttackDamageBonus", "PlusIfDefenderPoisonedThenPoison",
        "PlusIfDefenderStatusThenCure",
        # v0.112: ふしょくえき（「おもて」で相手をマヒ。「うら」の自分のワザの制限は相手への効果ではない）
        "DamageParalyzeOnHeadsElseLockSelf",
        # v0.113: ギガボルト（「うら」で相手をマヒ）。ゆうでん（自分の場につける）・ダークフレイム（自分のトラッシュ・自分につける）・ファイヤーラッシュ（自分の場のトラッシュ）・
        # だいぎゃくてん？（自分へのダメージ）・みんなでおどる・なかまをよぶは相手の対戦ポケモンへの効果を持たない。docs/variable-coins-search-attachments-v0.113.md
        "CoinBonusOnHeadsElseParalyze",
        # v0.114: モクモク（場の特殊能力の停止。やみのはどうと同じ）・サイコキッス（相手の特殊エネルギーカードを山札に）・なげキッス（相手の場の選んだポケモンにダメージカウンター）。
        # パチパチ（ダメージだけ）・いっしょにあそぼ（自分のベンチ）は相手の対戦ポケモンへの効果を持たない。docs/baby-rules-evolution-v0.114.md 6 章
        "DamageThenFieldPowerSuppressionUntilOwnNextTurn", "CoinReturnOpponentSpecialEnergyToDeck", "PlaceCountersOnChosenOpponentPokemon",
        # v0.115: しょうげきは（「おもて」でダメージのあとに相手が選ぶ控えと入れ替え）。ほかの 12 の型（ダメージ・控えへのダメージ・配分・自分の禁止・自分の進化・相手の山札）は相手の対戦
        # ポケモンへの効果を持たない。docs/spread-damage-allocation-v0.115.md 6 章
        "CoinSpreadDamageThenOpponentSwitch",
        # v0.116: クロスアタック（こんらん）・しこみどく・エナジーショック（ついた時に発動するどく・マヒの持続効果）・やみのしょくしゅ（進化の禁止）・とりかこむ（ねむりか、にげるの禁止）・
        # エナジーサイクル・エナジーコントロール（相手の場のエネルギーの付け替え）・げんしのしずく（相手の場の進化ポケモンの退化）・ツイスター（付属カードを手札に）・トランスダメージ（相手に
        # ダメージカウンターをのせかえる）。バトンタッチ・はらだいこ・よびもどす・さいせい・エナジーさいせいは、自分・自分の場・相手のトラッシュとベンチへの効果で、相手の対戦ポケモンへの効果を
        # 持たない。docs/energy-movement-attachment-devolution-v0.116.md 6 章
        "CoinsTimesDamageThenConfuseIfAtLeast", "DamageThenStatusOnEnergyAttach", "DamageThenEvolutionLock", "DamageThenSleepOnHeadsElseRetreatLock",
        "CoinMoveOpponentEnergyCardToBenchOrFail", "FailOnTailsMoveOpponentFieldEnergy", "CoinDevolveOpponentEvolvedToDeck", "DamageThenCoinReturnAttachedCardsToHand",
        "DiscardAllEnergyThenMoveAllSelfCountersToOpponent",
        # v0.117: いかく（ドわすれと同じワザの禁止）・サイキックダメージ（ダメージカウンター）・おいうち（「にげる」ときの持続効果）。docs/retreat-return-active-powers-v0.117.md 4 章・8 章
        "LockOpponentAttackIfBasic", "CoinsCountersOnOpponent", "DamageThenPursuitOnRetreat"]))


class DecisionTest(unittest.TestCase):
    """D5（選択中のほかの操作・不正な決定・保存して再開・乱数の再現・コインの前に結果を見せない）・D6（原子性）・決定の再開位置。"""

    def setUp(self):
        self.state, _, _ = run(board(SPECIAL_PUNCH, gmachamp(damage=80), hand0=[SWITCH], hand1=[SWITCH]), UseAttack(0, 1))
        self.d = self.state.decision

    def test_other_operations_are_rejected_while_waiting(self):
        """決定を待つ間は、決定に答えるコマンドだけ（p.311「宣言したら、それによって起こることをすべてすませてからでないと、他のことは
        できません」・p.309）。拒否は状態・ログ・乱数を変えない。"""
        pid = self.d.options[0]
        for command in (EndTurn(0), EndTurn(1), UseAttack(0, 0), UseAttack(1, 0), UsePokemonPower(1, pid, 0),
                        PlayTrainer(1, self.state.players[1].hand[0]), PlayTrainer(0, self.state.players[0].hand[0]), TakePrize(0, 0),
                        PromoteActive(1, self.state.players[1].bench[0].card)):
            with self.subTest(command=command):
                with self.assertRaises(EngineError):
                    apply_command(self.state, command)
        unchanged(self, self.state, self.state)

    def test_invalid_answers(self):
        """決定するのは持ち主（プレイヤー 1）。番号・選べるもの・選ぶ数が違えば拒否し、状態・乱数は変わらない（D5・D6）。"""
        pid = self.d.options[0]
        attacker = self.state.players[0].active.pokemon_id
        for command, code in ((ResolveDecision(0, self.d.id, (pid,)), "NOT_YOUR_DECISION"),
                              (ResolveDecision(1, self.d.id + 1, (pid,)), "WRONG_DECISION"),
                              (ResolveDecision(1, self.d.id, (attacker,)), None),
                              (ResolveDecision(1, self.d.id, (pid, pid)), None)):
            with self.subTest(command=command):
                before = self.state.clone()
                with self.assertRaises(IllegalActionError) as raised:
                    apply_command(self.state, command)
                if code is not None:
                    self.assertEqual(raised.exception.code, code)
                unchanged(self, before, self.state)

    def test_save_and_resume(self):
        """決定を待つ状態を保存（pickle・deepcopy・clone）して再開しても、同じコイン・同じ結果（G13。B6）。形式 9 の書き出しに決定の中身が
        あり、乱数の状態は決定を出したときのまま。"""
        reference, _, _ = answer(self.state, True)
        for restored in (pickle.loads(pickle.dumps(self.state)), copy.deepcopy(self.state), self.state.clone()):
            with self.subTest(kind=type(restored)):
                self.assertEqual(written(restored), written(self.state))
                again, _, _ = answer(restored, True)
                self.assertEqual(written(again), written(reference))

    def test_coin_is_not_known_before_answering(self):
        """コインは答えのあと（宣言のあと）に投げる: 決定を出した時点では乱数を使っておらず、決定の中身（選べるもの・続きの情報）にコインの
        結果はない。どちらに答えても、答える前の状態は同じ（G12・G13。D5 の情報の公開）。"""
        self.assertEqual(set(dict(self.d.context)), {"attack", "power"})
        self.assertFalse([e for e in self.state.log if e["kind"] == "coin_flip"])
        heads, _, _ = answer(self.state, True, H)
        tails, _, _ = answer(self.state, True, T)
        self.assertNotEqual(heads.players[1].active, tails.players[1].active)

    def test_resume_position(self):
        """答えのあとは、きぜつの処理から続ける: ワザ・ダメージ・番の終わりを繰り返さない（番の終わりとポケモンチェックは 1 回ずつ）。"""
        new, events, _ = answer(self.state, True, H)
        self.assertEqual([e["kind"] for e in events].count("turn_end"), 1)
        self.assertEqual([e["kind"] for e in new.log].count("attack"), 1)
        self.assertEqual([e["kind"] for e in new.log].count("damage"), 1)

    def test_answering_is_deterministic(self):
        """同じ状態・同じ答えなら、同じ結果（乱数は状態の乱数だけ。G13・C3）。"""
        self.assertEqual(written(answer(self.state, True)[0]), written(answer(self.state, True)[0]))
        self.assertEqual(written(answer(self.state, False)[0]), written(answer(self.state, False)[0]))


if __name__ == "__main__":
    unittest.main()

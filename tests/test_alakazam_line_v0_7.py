"""ケーシィ（PMCG1-043）→ ユンゲラー（PMCG1-046）→ フーディン（PMCG1-049）の進化とワザ（v0.7）: ねんりき・じこさいせい・ちょうねんりき・
あやしいひかり。フーディンのポケモンパワー「ダメージスワップ」は tests/test_damage_swap_v0_7.py。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES）。照合の記録は
kyuura_engine/data/card_verification.json（300dpi。カードの図版の説明文は 600dpi）。裁定は docs/alakazam-line-v0.7.md（K1〜K10）。

- p.149 ケーシィ LV.10／HP30（ポケモンカード第1弾）: 超・ねんりき（超）10・にげる 0・弱点 超。最新の説明「●ねんりき コインを投げて
  「おもて」なら、相手を「マヒ」状態にする。」（kyuura の写しは「コインを投げて、「おもて」なら、…」で読点が 1 つ多い。照合用）
- p.151 ユンゲラー LV.38／HP60（ポケモンカード第1弾）: ケーシィから進化・じこさいせい（超超）・ちょうねんりき（超超無）50（説明文
  なし）・にげる 3・弱点 超。最新の説明「●じこさいせい 自分についている「超」エネルギーカードを1枚トラッシュして、自分にのっている
  ダメージカウンターを、すべてとりのぞく。トラッシュできないとき、このワザの効果はなくなる。」（印刷の文面は「…1枚はがしてすてる
  ことによってダメージカウンターを全てとりのぞく。」）
- p.153 フーディン LV.42／HP80（ポケモンカード第1弾）: ユンゲラーから進化・あやしいひかり（超超超）30・にげる 3・弱点 超。最新の説明
  「●あやしいひかり コインを投げて「おもて」なら、相手を「こんらん」状態にする。」（ロコン（p.67）と同じ）
- p.309: ワザの説明の内容は書いてある順番に処理する。処理の対象がいなくなったら、その内容は無視する
- p.319・p.320: ダメージカウンター 1 個 = 10。ダメージの回復はとりのぞくことで行い、すべてとりのぞいたらそれ以上回復しない
- p.322: こんらんの 20 は「弱点・抵抗力」の影響を受ける（超を弱点に持つ超のポケモンは 40）

盤面を直接作るテスト（``build_test_state``）は 1 か所の規定を確かめるためのもの。
"""

import dataclasses
import unittest

from kyuura_engine import (
    EvolvePokemon,
    IllegalActionError,
    Phase,
    ResolveDecision,
    UseAttack,
    UsePokemonPower,
    apply_command,
    check_invariants,
    state_to_dict,
)
from kyuura_engine.cards import EnergyType, load_card_pool, read_verification
from kyuura_engine.effects import (
    DEFAULT_EFFECTS,
    AttackKey,
    ConfuseOnHeads,
    DamageOnly,
    DiscardEnergyAndRemoveAllCounters,
    ParalyzeOnHeads,
)
from kyuura_engine.resolution import open_attack
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    ABRA,
    ALAKAZAM,
    GROWLITHE,
    HITMONCHAN,
    KADABRA,
    PSYCHIC,
    RATTATA,
    WATER,
    H,
    T,
    build_test_state,
    coin_results,
    with_coin_results,
)
from tests.log_audit import serialization_problems

TURN = 7
RECOVER_PRINTED = "自分の「超」エネルギーカードを1枚はがしてすてることによってダメージカウンターを全てとりのぞく。"
RECOVER_LATEST = ("自分についている「超」エネルギーカードを1枚トラッシュして、自分にのっているダメージカウンターを、すべてとりのぞく。"
                  "トラッシュできないとき、このワザの効果はなくなる。")
PSYSHOCK_PRINTED = "コインを投げて、「おもて」なら、相手を「マヒ」状態にする。"
PSYSHOCK_LATEST = "コインを投げて「おもて」なら、相手を「マヒ」状態にする。"
CONFUSE_RAY = "コインを投げて「おもて」なら、相手を「こんらん」状態にする。"


def run(state, command):
    new = apply_command(state, command)
    return new, [dict(e) for e in new.log[len(state.log):]]


def kinds(events):
    return [e["kind"] for e in events]


def damage_amounts(events):
    return [(e["player"], e["amount"]) for e in events if e["kind"] == "damage"]


def board(active, *, opponent=GROWLITHE, bench=(RATTATA,), hand=(), turn=TURN):
    return build_test_state([{"active": active, "bench": list(bench), "hand": list(hand)}, {"active": opponent, "bench": [RATTATA]}],
                            turn_number=turn)


def kadabra(energy=(PSYCHIC, PSYCHIC), **extra):
    return {"card": KADABRA, "evolved_from": ABRA, "energy": list(energy), **extra}


def alakazam(energy=(PSYCHIC,) * 3, **extra):
    return {"card": ALAKAZAM, "evolved_from": [ABRA, KADABRA], "energy": list(energy), **extra}


def full(state):
    return state_to_dict(state, format_version=9)


# ---------------------------------------------------------------- カードの値と登録


class CardValuesTest(unittest.TestCase):
    def test_abra_and_kadabra(self):
        """p.149・p.151 で照合した値。"""
        pool = load_card_pool()
        abra, kad = pool.get(ABRA), pool.get(KADABRA)
        self.assertTrue(abra.supported and abra.is_basic_pokemon and pool.is_playable(ABRA))
        self.assertTrue(kad.supported and kad.is_stage1_pokemon and pool.is_playable(KADABRA))
        self.assertEqual((abra.name_ja, abra.hp, abra.pokemon_type, abra.weakness, abra.resistance, abra.retreat_cost, abra.powers),
                         ("ケーシィ", 30, EnergyType.PSYCHIC, EnergyType.PSYCHIC, None, 0, ()))
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage, a.text_ja) for a in abra.attacks],
                         [("ねんりき", ["psychic"], 10, PSYSHOCK_PRINTED)])
        self.assertEqual((kad.name_ja, kad.evolves_from, kad.hp, kad.pokemon_type, kad.weakness, kad.resistance, kad.retreat_cost, kad.powers),
                         ("ユンゲラー", "ケーシィ", 60, EnergyType.PSYCHIC, EnergyType.PSYCHIC, None, 3, ()))
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage, a.text_ja) for a in kad.attacks],
                         [("じこさいせい", ["psychic", "psychic"], None, RECOVER_PRINTED),
                          ("ちょうねんりき", ["psychic", "psychic", "colorless"], 50, None)])

    def test_registrations(self):
        """登録は照合した説明文（kyuura の写し）・最新の説明・出典と同じ。ロコンの「あやしいひかり」と名前が同じでも、フーディンの位置の
        別の登録。"""
        for key, effect, name, printed, latest, page in (
            (AttackKey(ABRA, 0), ParalyzeOnHeads(), "ねんりき", PSYSHOCK_PRINTED, PSYSHOCK_LATEST, 149),
            (AttackKey(KADABRA, 0), DiscardEnergyAndRemoveAllCounters(energy_type=EnergyType.PSYCHIC), "じこさいせい", RECOVER_PRINTED,
             RECOVER_LATEST, 151),
            (AttackKey(ALAKAZAM, 0), ConfuseOnHeads(), "あやしいひかり", CONFUSE_RAY, CONFUSE_RAY, 153),
        ):
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
                self.assertEqual((entry.effect, entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                                 (effect, name, printed, latest, f"P43 p.{page}"))
                record = read_verification()["cards"][key.card_id]
                self.assertEqual((record["page"], record["pdf_page"]), (page, page + 2))
        entry = DEFAULT_EFFECTS.attack_entry(KADABRA, 1)
        self.assertEqual((entry.effect, entry.name_ja, entry.text_ja), (DamageOnly(), "ちょうねんりき", None))
        self.assertIsNot(DEFAULT_EFFECTS.attack_entry(ALAKAZAM, 0), DEFAULT_EFFECTS.attack_entry("PMCG1-015", 0))
        records = read_verification()["cards"]
        self.assertEqual([m["field"] for m in records[ABRA]["mismatches"]], ["pokemon.attacks[0].text.ja"])
        self.assertEqual([m["field"] for m in records[KADABRA]["mismatches"]], ["pokemon.attacks[0].text.ja"])
        self.assertEqual(records[KADABRA]["latest_description_ja"], RECOVER_LATEST)

    def test_recover_checks_the_data(self):
        """``DiscardEnergyAndRemoveAllCounters.check``: ダメージの目安のあるワザ・説明文のないワザ・必要なエネルギーに「超」がないワザは登録
        できない（トラッシュできない場合が起こりうる形を登録しない）。"""
        effect = DiscardEnergyAndRemoveAllCounters(energy_type=EnergyType.PSYCHIC)
        recover, super_psy = load_card_pool().get(KADABRA).attacks
        self.assertEqual(effect.check(recover), [])
        self.assertTrue(effect.check(super_psy))
        self.assertTrue(effect.check(dataclasses.replace(recover, text_ja=None)))
        self.assertTrue(effect.check(dataclasses.replace(recover, cost=(EnergyType.COLORLESS, EnergyType.COLORLESS))))


# ---------------------------------------------------------------- ケーシィ


class AbraAttackTest(unittest.TestCase):
    def test_psyshock(self):
        """ねんりき: 相手に 10（目安の数字。p.320 で説明の最初の「相手に10ダメージ。」が省略されている）→ コイン →「おもて」ならマヒ。"""
        for coin, paralyzed in ((H, True), (T, False)):
            with self.subTest(coin=coin):
                state = board({"card": ABRA, "energy": [PSYCHIC]})
                new, events = run(with_coin_results(state, coin), UseAttack(0, 0))
                self.assertEqual(damage_amounts(events), [(1, 10)])
                self.assertEqual(coin_results(new, len(state.log)), [coin.value])
                self.assertEqual(bool(new.players[1].active.conditions.paralyzed), paralyzed)

    def test_weakness_resistance_and_knock_out(self):
        """弱点（エビワラー: 超 ×2 → 20）・抵抗力（コラッタ: 超 -30 → 0。ダメージ 0 でもマヒは効果なので「おもて」ならマヒ）。相手が
        きぜつしたらコインを投げない（p.309）。"""
        state = board({"card": ABRA, "energy": [PSYCHIC]}, opponent=HITMONCHAN)
        _, events = run(with_coin_results(state, T), UseAttack(0, 0))
        self.assertEqual(damage_amounts(events), [(1, 20)])
        state = board({"card": ABRA, "energy": [PSYCHIC]}, opponent=RATTATA)
        new, events = run(with_coin_results(state, H), UseAttack(0, 0))
        self.assertEqual(damage_amounts(events), [(1, 0)])
        self.assertTrue(new.players[1].active.conditions.paralyzed)
        state = board({"card": ABRA, "energy": [PSYCHIC]}, opponent={"card": HITMONCHAN, "damage": 50})
        new, events = run(state, UseAttack(0, 0))
        self.assertEqual((coin_results(new, len(state.log)), rng_fingerprint(new.rng)), ([], rng_fingerprint(state.rng)))
        self.assertIn("knock_out", kinds(events))

    def test_confused_abra_takes_forty(self):
        """こんらんの「うら」の 20 は、自分の弱点（超 ×2）で 40（p.322「このダメージは「弱点・抵抗力」の影響を受けます」。v0.3c の計算）。
        HP 30 のケーシィはきぜつする。"""
        state = board({"card": ABRA, "energy": [PSYCHIC], "confusion": True}, bench=(RATTATA,))
        _, events = run(with_coin_results(state, T), UseAttack(0, 0))
        self.assertEqual([e["amount"] for e in events if e["kind"] == "confusion_damage"], [40])
        self.assertIn("knock_out", kinds(events))


# ---------------------------------------------------------------- ユンゲラー


class KadabraRecoverTest(unittest.TestCase):
    def test_recover(self):
        """じこさいせい: ワザを使ったプレイヤーが、ついている「超」エネルギーカードから 1 枚選んでトラッシュし（決定 ``DISCARD_ENERGY``）、
        ダメージカウンターをすべてとりのぞく（K1・K2・K5）。ダメージの要素はない（``damage`` のログなし）。コインを投げない。"""
        state = board(kadabra(energy=(PSYCHIC, WATER, PSYCHIC, PSYCHIC), damage=40))
        k = state.players[0].active
        pending, events = run(state, UseAttack(0, 0))
        d = pending.decision
        psychics = [u for u in k.energy if state.card_def(u).provides is EnergyType.PSYCHIC]
        self.assertEqual((pending.phase, d.kind, d.player, d.options, d.min_choices, d.max_choices, d.resume),
                         (Phase.DECISION, "discard_energy", 0, tuple(psychics), 1, 1, "attack"))
        self.assertEqual(kinds(events), ["attack"])
        self.assertEqual(pending.players[0].active.damage, 40)  # 決定の前は何もしていない
        done, events = run(pending, ResolveDecision(0, d.id, (psychics[1],)))
        self.assertEqual(kinds(events)[:2], ["discard_energy", "remove_all_damage_counters"])
        self.assertEqual((events[0]["energy"], events[1]["counters"], events[1]["amount"], events[1]["total_damage"]), (psychics[1], 4, 40, 0))
        me = done.players[0]
        self.assertEqual(me.discard, [psychics[1]])
        self.assertEqual(me.active.damage, 0)
        self.assertEqual(sorted(me.active.energy), sorted(u for u in k.energy if u != psychics[1]))
        self.assertNotIn("damage", kinds(events))
        self.assertEqual((done.current_player, rng_fingerprint(done.rng)), (1, rng_fingerprint(state.rng)))
        self.assertEqual(done.players[1].active.damage, 0)

    def test_recover_without_damage(self):
        """ダメージカウンターがなくても使える（説明に使うための条件がない。p.309。SUPPORTED。K4）。エネルギーはトラッシュし、とりのぞくのは
        0 個。"""
        state = board(kadabra(damage=0))
        pending = apply_command(state, UseAttack(0, 0))
        done, events = run(pending, ResolveDecision(0, pending.decision.id, (pending.decision.options[0],)))
        self.assertEqual((events[1]["counters"], len(done.players[0].active.energy), done.players[0].discard),
                         (0, 1, [pending.decision.options[0]]))

    def test_invalid_choices_change_nothing(self):
        """決定に合わない答え（選べないカード・2 枚・同じカード 2 回・0 枚・相手・違う決定の番号）は、状態・ログ・乱数を変えない。"""
        state = board(kadabra(energy=(PSYCHIC, WATER, PSYCHIC), damage=20))
        pending = apply_command(state, UseAttack(0, 0))
        d = pending.decision
        water = next(u for u in pending.players[0].active.energy if pending.card_def(u).provides is EnergyType.WATER)
        for command, code in (
            (ResolveDecision(0, d.id, (water,)), "INVALID_CHOICE"),
            (ResolveDecision(0, d.id, (pending.players[0].deck[0],)), "INVALID_CHOICE"),
            (ResolveDecision(0, d.id, tuple(d.options)), "INVALID_CHOICE_COUNT"),
            (ResolveDecision(0, d.id, (d.options[0], d.options[0])), "INVALID_CHOICE_COUNT"),
            (ResolveDecision(0, d.id, ()), "INVALID_CHOICE_COUNT"),
            (ResolveDecision(1, d.id, (d.options[0],)), "NOT_YOUR_DECISION"),
            (ResolveDecision(0, d.id + 1, (d.options[0],)), "WRONG_DECISION"),
            (UseAttack(0, 1), "WRONG_PHASE"),
        ):
            with self.subTest(code=code, command=command):
                before, fingerprint, log = full(pending), rng_fingerprint(pending.rng), pending.log
                with self.assertRaises(IllegalActionError) as ctx:
                    apply_command(pending, command)
                self.assertEqual(ctx.exception.code, code)
                self.assertEqual((full(pending), rng_fingerprint(pending.rng)), (before, fingerprint))
                self.assertIs(pending.log, log)

    def test_confused_kadabra(self):
        """こんらん状態のユンゲラー: コインが「うら」なら決定を出さず、ワザの処理をしない（p.309 の手順 5）。自分に 20（弱点 超で 40）。
        「おもて」なら決定を出す。"""
        state = board(kadabra(damage=10, confusion=True))
        tails, events = run(with_coin_results(state, T), UseAttack(0, 0))
        self.assertIsNone(tails.decision)
        self.assertEqual([e["amount"] for e in events if e["kind"] == "confusion_damage"], [40])
        self.assertEqual((tails.find_pokemon(state.players[0].active.pokemon_id)[1].damage, tails.players[0].discard), (50, []))
        heads = apply_command(with_coin_results(state, H), UseAttack(0, 0))
        self.assertEqual(heads.decision.kind, "discard_energy")

    def test_pending_decision_serialization_and_invariants(self):
        """決定を待つ状態: 進化したユンゲラーがいるので形式 1〜6 は ``ValueError``、7〜9 は書き出せる。決定の形が壊れていれば不変条件
        （``decision_problems``）で見つかる。"""
        state = board(kadabra(energy=(PSYCHIC, PSYCHIC, PSYCHIC), damage=20))
        pending = apply_command(state, UseAttack(0, 0))
        self.assertEqual(serialization_problems(pending), [])
        self.assertEqual(state_to_dict(pending, format_version=9)["decision"]["kind"], "discard_energy")
        for version in range(1, 7):
            with self.subTest(format_version=version), self.assertRaises(ValueError):
                state_to_dict(pending, format_version=version)
        d = pending.decision
        for name, broken in (
            ("種類", dataclasses.replace(d, kind="forced_switch")),
            ("決定するプレイヤー", dataclasses.replace(d, player=1)),
            ("選ぶ数", dataclasses.replace(d, max_choices=2)),
            ("選べるもの（足りない）", dataclasses.replace(d, options=d.options[:-1])),
            ("選べるもの（場にないカード）", dataclasses.replace(d, options=(*d.options[:-1], pending.players[0].deck[0]))),
        ):
            with self.subTest(change=name):
                bad = pending.clone()
                bad.decision = broken
                self.assertTrue(check_invariants(bad))
        self.assertEqual(check_invariants(pending), [])

    def test_pending_decision_survives_copies(self):
        """決定を待つ状態を clone・deepcopy・pickle で写しても、同じ決定で同じ続きになる（保存・復元）。"""
        import copy
        import pickle
        state = board(kadabra(energy=(PSYCHIC, PSYCHIC, PSYCHIC), damage=30))
        pending = apply_command(state, UseAttack(0, 0))
        choice = (pending.decision.options[2],)
        expected = full(apply_command(pending, ResolveDecision(0, pending.decision.id, choice)))
        for copied in (pending.clone(), copy.deepcopy(pending), pickle.loads(pickle.dumps(pending))):
            self.assertEqual(full(copied), full(pending))
            self.assertEqual(full(apply_command(copied, ResolveDecision(0, copied.decision.id, choice))), expected)

    def test_unreachable_case_stops_loudly(self):
        """「トラッシュできないとき」は、必要なエネルギー（超超）を基本エネルギーでしか払えない今の対応カードでは起こらない（K3）。実装を
        直接呼んで起こしたら、黙って処理せずに ``RuntimeError``（状態を変える前）。

        v0.16d: v0.16b から、じこさいせいの処理は解決の基盤の要素（v0.29 までは ``programs.DiscardEnergyHealAll``、v0.30 から ``programs.DiscardOwnEnergy``・``HealAllCounters``）で、実装の ``resolve`` は解決の基盤の
        ワザの枠の中でだけ使える。枠の外で呼ぶと「枠の外」の ``RuntimeError`` になり、K3 の確かめにならない（v0.16b〜v0.16c のこのテストは
        その理由で通っていた）ので、``resolution.open_attack`` で枠を開いて呼び、K3 の理由の文を確かめる。"""
        state = board(kadabra(energy=(WATER, WATER), damage=20))
        effect = DEFAULT_EFFECTS.attack_entry(KADABRA, 0).effect
        before = full(state)
        use = open_attack(state, 0)
        self.assertEqual(use.key, AttackKey(KADABRA, 0))
        with self.assertRaisesRegex(RuntimeError, "「超」エネルギーカードがない"):
            effect.resolve(state, use)
        self.assertEqual(full(state), before)
        self.assertIsNone(state.decision)

    def test_super_psy(self):
        """ちょうねんりき: 説明文なしの 50（弱点 超のエビワラーには 100 できぜつ）。"""
        state = board(kadabra(energy=(PSYCHIC, PSYCHIC, WATER)))
        _, events = run(state, UseAttack(0, 1))
        self.assertEqual(damage_amounts(events), [(1, 50)])
        state = board(kadabra(energy=(PSYCHIC, PSYCHIC, WATER)), opponent=HITMONCHAN)
        _, events = run(state, UseAttack(0, 1))
        self.assertEqual(damage_amounts(events), [(1, 100)])
        self.assertIn("knock_out", kinds(events))


# ---------------------------------------------------------------- フーディン


class AlakazamAttackTest(unittest.TestCase):
    def test_confuse_ray(self):
        """あやしいひかり: 相手に 30 → コイン →「おもて」ならこんらん（ロコンと同じ実装。相手がきぜつしたらコインを投げない）。"""
        for coin, confused in ((H, True), (T, False)):
            with self.subTest(coin=coin):
                state = board(alakazam())
                new, events = run(with_coin_results(state, coin), UseAttack(0, 0))
                self.assertEqual(damage_amounts(events), [(1, 30)])
                self.assertEqual(bool(new.players[1].active.conditions.confused), confused)
        state = board(alakazam(), opponent={"card": HITMONCHAN, "damage": 10})  # HP 70。弱点 超で 60 → 70 できぜつ
        new, events = run(state, UseAttack(0, 0))
        self.assertEqual(damage_amounts(events), [(1, 60)])
        self.assertEqual(coin_results(new, len(state.log)), [])
        self.assertIn("knock_out", kinds(events))


# ---------------------------------------------------------------- 進化


class EvolutionChainTest(unittest.TestCase):
    def test_abra_to_kadabra_to_alakazam(self):
        """ケーシィ → ユンゲラー → フーディン（別々の番。p.310）。ダメージはそのまま。パワーを使えるのはいちばん上がフーディンのときだけ
        （ユンゲラーはパワーを持たない。p.310）。"""
        state = board({"card": ABRA, "damage": 20, "energy": [PSYCHIC]}, bench=({"card": RATTATA, "damage": 10},), hand=(KADABRA, ALAKAZAM),
                      turn=5)
        a = state.players[0].active
        r = state.players[0].bench[0]
        state = apply_command(state, EvolvePokemon(0, state.players[0].hand[0], a.pokemon_id))
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, UsePokemonPower(0, a.pokemon_id, 0, None, r.pokemon_id, a.pokemon_id))
        self.assertEqual(ctx.exception.code, "NO_POKEMON_POWER")
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, EvolvePokemon(0, state.players[0].hand[0], a.pokemon_id))
        self.assertEqual(ctx.exception.code, "EVOLVED_THIS_TURN")
        from kyuura_engine import EndTurn
        state = apply_command(apply_command(state, EndTurn(0)), EndTurn(1))
        state = apply_command(state, EvolvePokemon(0, state.players[0].hand[0], a.pokemon_id))
        top = state.players[0].active
        self.assertEqual((state.cards[top.card].card_id, top.damage, len(top.evolution_stack)), (ALAKAZAM, 20, 2))
        state = apply_command(state, UsePokemonPower(0, a.pokemon_id, 0, None, r.pokemon_id, a.pokemon_id))
        self.assertEqual((state.players[0].active.damage, state.players[0].bench[0].damage), (30, 0))
        self.assertEqual(check_invariants(state), [])


if __name__ == "__main__":
    unittest.main()

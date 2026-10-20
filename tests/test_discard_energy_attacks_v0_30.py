"""v0.30: エネルギーをトラッシュしてダメージを与えるワザの共通の実装（``effects.DiscardEnergyThenDamage``。要素の並び
``programs.DiscardOwnEnergy`` → ``Damage``）と、それで加えたポケモン 5 枚（docs/discard-energy-attacks-v0.30.md）。

- ヒトカゲ（PMCG1-014）: ひっかく（無）10（v0.2a から登録）・ひのこ（炎無）30
- リザード（PMCG1-017。ヒトカゲから進化）: きりさく（無無無）30・かえんほうしゃ（炎炎無）50
- ウインディ（PMCG1-019。ガーディから進化）: かえんほうしゃ（炎炎無）50・とっしん（炎炎無無）80「自分にも30ダメージ。」
- ブーバー（PMCG1-020）: ほのおパンチ（炎炎）30・かえんほうしゃ（炎炎無）50
- 第4弾ロケット団のポニータ（PMCG4-013。第1弾のポニータ PMCG1-016 とは別のカード）: ひのこ（炎無）30

根拠（ガイドブックは読んでいない）:

- 写しの元 ecb2d69 の kyuura の data/cards.json（2026-10-15 からのカードデータの方針）と、pcg-search.com の同じ版のページとの照合
  （kyuura_engine/data/card_sources.json）。
- 第1弾の 4 つのワザ（印刷の文面「自分の「炎」エネルギーカードを1枚はがしてすてる。」）の処理に使う文面は、kyuura の
  RUL-ENERGY-DISCARD-ATTACKS（rule_history.json の errata。確実）の最新の説明「自分についている「炎」エネルギーカードを1枚トラッシュする。
  トラッシュできないとき、このワザのダメージはなくなる。」（記録の cards はウインディだけ。ほかは記録の「炎エネルギーカードをトラッシュする
  タイプのワザ（「かえんほうしゃ」など）は、すべて同じ処理になります。」の範囲として当てはめた。研究の対応表の errata_scope）。記録は、
  トラッシュがワザを使うための条件でなく「ワザの効果」で、宣言 → こんらんの確認 → ワザの内容の処理でトラッシュすると書く。
- 第4弾のポニータのひのこは kyuura の印刷の文面（「このカードについている「炎」エネルギーカードを1枚トラッシュする。(トラッシュできない時、
  このワザのダメージは0になる)」）。
- 一般の規定（既存の記録の再利用）: p.309 のワザの手順（宣言の条件は必要なエネルギー・こんらんで「うら」ならワザの内容を処理しない・特に指示
  されていないかぎりエネルギーをトラッシュしない。kyuura の GR-2000-P309-ATTACK-PROCEDURE）、p.320 の要素、p.321 のダメージの計算。
  トラッシュするカードを選ぶ決定は v0.7 の「じこさいせい」と同じ形（1 枚しかなくても出す。K2）、トラッシュできない場合は今の対応カードで
  起こらないので不具合として止める（K3）。

盤面を直接作るテスト（``build_test_state``）は 1 か所の規定を確かめるためのもの。正式な対戦開始からの対戦は
tests/test_discard_energy_games_v0_30.py。
"""

from __future__ import annotations

import copy
import dataclasses
import pickle
import unittest

from kyuura_engine import (
    EvolvePokemon,
    IllegalActionError,
    Phase,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    apply_command,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, pool_from_extract, read_extract
from kyuura_engine.resolution import PREFLIGHT_MODES, open_attack, programs, v013_checks
from kyuura_engine.rng import rng_fingerprint
from scripts import check_card_sources as cs
from tests.helpers import (
    ARCANINE,
    CATERPIE,
    CHARMANDER,
    CHARMELEON,
    DEFENDER,
    FIRE,
    GASTLY,
    GRASS,
    GROWLITHE,
    HAUNTER,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MAGMAR,
    METAPOD,
    PLUSPOWER,
    PONYTA,
    RATTATA,
    ROCKET_PONYTA,
    ROCKETS_MOLTRES,
    V0_30_POKEMON,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import serialization_problems
from tests.test_preflight_v0_15c import preflight_results

TURN = 7
RUL = "RUL-ENERGY-DISCARD-ATTACKS"
PRINTED = cs.PRINTED_TEXT_SOURCE
FIRE_PRINTED = "自分の「炎」エネルギーカードを1枚はがしてすてる。"
FIRE_LATEST = "自分についている「炎」エネルギーカードを1枚トラッシュする。トラッシュできないとき、このワザのダメージはなくなる。"
PONYTA_PRINTED = "このカードについている「炎」エネルギーカードを1枚トラッシュする。(トラッシュできない時、このワザのダメージは0になる)"
DISCARD_FIRE = E.DiscardEnergyThenDamage(EnergyType.FIRE)
# v0.31: 第4弾のポニータのひのこは、トラッシュできないとき印刷の文面のとおりダメージを 0 にする（相手のワザとして使われると起こる）
DISCARD_FIRE_ZERO = E.DiscardEnergyThenDamage(EnergyType.FIRE, when_lacking="zero")
# (カード id, ワザの位置) → (名前, 実装, 処理に使う文面, 出典)。出典が None のワザは説明文がない（DamageOnly）
EXPECTED = {
    (CHARMANDER, 0): ("ひっかく", E.DAMAGE_ONLY, None, None),
    (CHARMANDER, 1): ("ひのこ", DISCARD_FIRE, FIRE_LATEST, RUL),
    (CHARMELEON, 0): ("きりさく", E.DAMAGE_ONLY, None, None),
    (CHARMELEON, 1): ("かえんほうしゃ", DISCARD_FIRE, FIRE_LATEST, RUL),
    (ARCANINE, 0): ("かえんほうしゃ", DISCARD_FIRE, FIRE_LATEST, RUL),
    (ARCANINE, 1): ("とっしん", E.DamageAndSelfDamage(30), "自分にも30ダメージ。", PRINTED),
    (MAGMAR, 0): ("ほのおパンチ", E.DAMAGE_ONLY, None, None),
    (MAGMAR, 1): ("かえんほうしゃ", DISCARD_FIRE, FIRE_LATEST, RUL),
    (ROCKET_PONYTA, 0): ("ひのこ", DISCARD_FIRE_ZERO, PONYTA_PRINTED, PRINTED),
}
# エネルギーをトラッシュしてダメージを与えるワザ: (カード id, ワザの位置, 進化元, ダメージの目安)
DISCARD_ATTACKS = [
    (CHARMANDER, 1, None, 30),
    (CHARMELEON, 1, CHARMANDER, 50),
    (ARCANINE, 0, GROWLITHE, 50),
    (MAGMAR, 1, None, 50),
    (ROCKET_PONYTA, 0, None, 30),
]


def full(state):
    return state_to_dict(state, format_version=9)


def snapshot(state):
    return full(state), rng_fingerprint(state.rng), len(state.log)


def events(state, since=0):
    return [dict(e) for e in state.log[since:]]


def kinds(state, since=0):
    return [e["kind"] for e in events(state, since)]


def attacker(card=CHARMANDER, energy=(FIRE, FIRE), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    below = next((base for c, _, base, _ in DISCARD_ATTACKS if c == card), None)
    if below is not None and "evolved_from" not in spec:
        spec["evolved_from"] = below
    return spec


def board(active, opponent=GROWLITHE, *, bench=(RATTATA,), hand=(), turn=TURN, effects=None, pool=None):
    return build_test_state([{"active": active, "bench": list(bench), "hand": list(hand)}, {"active": opponent, "bench": [RATTATA]}],
                            turn_number=turn, effects=effects, pool=pool)


def zone_cards(state) -> list[int]:
    """すべてのゾーンのカード（保存則を確かめる）。"""
    found = []
    for player in state.players:
        found += player.deck + player.hand + player.prizes + player.discard
        for pokemon in player.in_play():
            found += [*pokemon.cards(), *pokemon.energy, *(t.card for t in pokemon.trainers)]
    return found


def fire_uids(state, pid):
    _, pokemon = state.find_pokemon(pid)
    return [u for u in pokemon.energy if state.card_def(u).provides is EnergyType.FIRE]


def use_and_discard(state, attack_index=1, *, choice=0):
    """ワザを使い、トラッシュするカードの決定に ``choice`` 番目の選べるもので答える。"""
    pending = apply_command(state, UseAttack(0, attack_index))
    return pending, apply_command(pending, ResolveDecision(0, pending.decision.id, (pending.decision.options[choice],)))


# ---------------------------------------------------------------- 登録・パラメーター


class RegistrationTest(unittest.TestCase):
    def test_registrations(self):
        """5 枚のワザの登録（位置・名前・実装・パラメーター・照合用の写しの文面・処理に使う文面・出典）。5 枚とも対応で、デッキに入れられる。"""
        pool = load_card_pool()
        for (card_id, index), (name, effect, play_text, source) in EXPECTED.items():
            with self.subTest(card=card_id, attack=index):
                entry = E.DEFAULT_EFFECTS.attack_entry(card_id, index)
                attack = pool.get(card_id).attacks[index]
                self.assertEqual((entry.name_ja, attack.name_ja, entry.effect), (name, name, effect))
                self.assertEqual(entry.text_ja, attack.text_ja)
                self.assertEqual((entry.play_text_ja, entry.source), (play_text, source))
                self.assertTrue(attack.supported)
        for card_id in V0_30_POKEMON:
            with self.subTest(card=card_id):
                self.assertTrue(pool.get(card_id).supported)
                self.assertTrue(pool.is_playable(card_id))
                self.assertEqual(len(pool.get(card_id).attacks), len([k for k in EXPECTED if k[0] == card_id]))
                self.assertEqual(pool.get(card_id).powers, ())
        # v0.31 でキュウコン（第1弾）のだいもんじ（同じ印刷の文面。RUL-ENERGY-DISCARD-ATTACKS の範囲）を加えた
        self.assertEqual(sum(isinstance(e.effect, E.DiscardEnergyThenDamage) for e in
                             (E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index) for k in E.DEFAULT_EFFECTS.attack_keys())), 7)  # v0.69 で PR1-089（ブーバー。PMCG1-020 の登録の写し）を加えた

    def test_printed_texts_are_kept_for_matching(self):
        """印刷の文面（写し）は照合にだけ使い、処理は最新の説明（RUL-）にしたがう。第1弾の 4 つは同じ印刷の文面。"""
        pool = load_card_pool()
        for card_id, index, _, _ in DISCARD_ATTACKS:
            text = pool.get(card_id).attacks[index].text_ja
            self.assertEqual(text, PONYTA_PRINTED if card_id == ROCKET_PONYTA else FIRE_PRINTED)

    def test_program(self):
        """要素の並びは、トラッシュ（v0.7 のじこさいせいと共通の要素）→ 相手の対戦ポケモンへの印刷のダメージ。じこさいせいの並びは
        トラッシュ → すべてとりのぞく（v0.29 までの 1 つの要素を 2 つに分けた。処理・ログは同じ）。v0.31 から、トラッシュできないときの扱い
        （``when_lacking``。最新の説明の「なくなる」・ポニータの「0になる」・じこさいせいの K3「効果はなくなる」）と、それを見る後の要素の
        ``requires`` を要素に書く（相手のワザを自分のワザとして使う効果で、トラッシュできない場合が起こるようになった）。"""
        self.assertEqual(programs.BUILDERS[E.DiscardEnergyThenDamage](DISCARD_FIRE),
                         (programs.DiscardOwnEnergy(EnergyType.FIRE, when_lacking=programs.LACKING_NONE),
                          programs.Damage(programs.OPP, programs.Printed(), requires="discard")))
        self.assertEqual(programs.BUILDERS[E.DiscardEnergyThenDamage](DISCARD_FIRE_ZERO)[0].when_lacking, programs.LACKING_ZERO)
        recover = E.DiscardEnergyAndRemoveAllCounters(EnergyType.PSYCHIC)
        self.assertEqual(programs.BUILDERS[E.DiscardEnergyAndRemoveAllCounters](recover),
                         (programs.DiscardOwnEnergy(EnergyType.PSYCHIC, when_lacking=programs.LACKING_NONE),
                          programs.HealAllCounters(requires="discard")))
        # v0.17 から加えた型は v0.13 の約束（resolve・resume）を上書きせず、v0.13 の止める関数で確かめる型にも入れない
        self.assertNotIn(E.DiscardEnergyThenDamage, v013_checks.VERIFIED)
        self.assertNotIn("resolve", vars(E.DiscardEnergyThenDamage))
        self.assertNotIn("resume", vars(E.DiscardEnergyThenDamage))

    def test_check_rejects_mismatched_attacks(self):
        """``check``: ダメージの目安が 10 の倍数の正の数・説明文がある・必要なエネルギーにトラッシュするタイプがある・目安に「×」などがない。
        合わない登録のカードは未対応（効果のないワザとして扱わない）。"""
        ember = load_card_pool().get(CHARMANDER).attacks[1]
        self.assertEqual(DISCARD_FIRE.check(ember), [])
        cases = [
            (dataclasses.replace(ember, text_ja=None), "説明文のないワザ"),
            (dataclasses.replace(ember, damage=None), "10 の倍数の正の数ではない"),
            (dataclasses.replace(ember, damage=25), "10 の倍数の正の数ではない"),
            (dataclasses.replace(ember, damage_modifier="×"), "「×」"),
            (dataclasses.replace(ember, cost=tuple(c for c in ember.cost if c is not EnergyType.FIRE)), "必要なエネルギーに「炎」がない"),
        ]
        for attack, expected in cases:
            with self.subTest(expected=expected):
                self.assertTrue(any(expected in p for p in DISCARD_FIRE.check(attack)), DISCARD_FIRE.check(attack))
        self.assertTrue(any("「水」がない" in p for p in E.DiscardEnergyThenDamage(EnergyType.WATER).check(ember)))
        # 炎以外のエネルギーのワザには当てはめない（kyuura の記録の未解決の問い）。必要なエネルギーに「水」があるワザでも拒否する
        water_cost = dataclasses.replace(ember, cost=(EnergyType.WATER, EnergyType.COLORLESS))
        self.assertTrue(any("炎エネルギーのワザの説明" in p for p in E.DiscardEnergyThenDamage(EnergyType.WATER).check(water_cost)))
        # きりさく（説明文なし）に登録すると、リザードは未対応になる
        slash = load_card_pool().get(CHARMELEON).attacks[0]
        registry = E.DEFAULT_EFFECTS.with_attacks("test-bad-slash", {E.AttackKey(CHARMELEON, 0): E.AttackEntry(DISCARD_FIRE, "きりさく")})
        self.assertIsNotNone(registry.attack_problem(CHARMELEON, slash))
        self.assertFalse(pool_from_extract(read_extract(), registry).get(CHARMELEON).supported)

    def test_same_name_cards_are_distinct(self):
        """第4弾ロケット団のポニータ（ひのこ）と第1弾のポニータ（けりとばす・ほのおのしっぽ。v0.2a から）は別のカード。ウインディの
        かえんほうしゃとリザード・ブーバーのかえんほうしゃは、同じ名前で別のカードのワザ（登録はカードごと）。"""
        pool = load_card_pool()
        self.assertEqual(pool.get(PONYTA).name_ja, pool.get(ROCKET_PONYTA).name_ja)
        self.assertEqual([a.name_ja for a in pool.get(PONYTA).attacks], ["けりとばす", "ほのおのしっぽ"])
        self.assertEqual(E.DEFAULT_EFFECTS.attack_entry(PONYTA, 1).effect, E.DAMAGE_ONLY)
        self.assertEqual(E.DEFAULT_EFFECTS.attack_entry(ROCKET_PONYTA, 0).effect, DISCARD_FIRE_ZERO)
        self.assertEqual(pool.get(ROCKET_PONYTA).hp, 50)
        self.assertEqual(pool.get(PONYTA).hp, 40)


# ---------------------------------------------------------------- トラッシュとダメージ


class DiscardThenDamageTest(unittest.TestCase):
    def test_each_attack_discards_one_fire_then_damages(self):
        """5 つのワザ: 宣言ではトラッシュせず（決定を出すだけ）、選んだ「炎」エネルギーカードを 1 枚トラッシュしてから、ダメージの目安の
        ダメージ（弱点・抵抗力のないガーディへ）。余分なエネルギーは残る。カードの保存則・番の終わりも確かめる。"""
        for card_id, index, _, damage in DISCARD_ATTACKS:
            with self.subTest(card=card_id):
                energy = (FIRE, WATER, FIRE, FIRE)
                state = board(attacker(card_id, energy), opponent={"card": GROWLITHE})
                pid = state.players[0].active.pokemon_id
                fires = fire_uids(state, pid)
                pending = apply_command(state, UseAttack(0, index))
                d = pending.decision
                self.assertEqual((pending.phase, d.kind, d.player, d.options, d.min_choices, d.max_choices, d.resume),
                                 (Phase.DECISION, "discard_energy", 0, tuple(fires), 1, 1, "attack"))
                self.assertEqual(kinds(pending, len(state.log)), ["attack"])
                self.assertEqual((pending.players[0].discard, pending.players[1].active.damage), ([], 0))
                done = apply_command(pending, ResolveDecision(0, d.id, (fires[1],)))
                new = events(done, len(pending.log))
                self.assertEqual([e["kind"] for e in new][:2], ["discard_energy", "damage"])
                self.assertEqual((new[0]["energy"], new[0]["pokemon_id"], new[0]["effect"]), (fires[1], pid, f"{card_id}#{index}"))
                self.assertEqual(new[1]["amount"], damage)
                me = done.players[0]
                self.assertEqual(me.discard, [fires[1]])
                self.assertEqual(sorted(me.active.energy), sorted(u for u in state.players[0].active.energy if u != fires[1]))
                self.assertEqual(done.players[1].active.damage, damage)
                self.assertEqual(sorted(zone_cards(done)), sorted(state.cards))
                self.assertEqual((done.current_player, done.phase), (1, Phase.MAIN))
                self.assertEqual(check_invariants(done), [])

    def test_single_fire_card_still_needs_a_decision(self):
        """「炎」が 1 枚だけでも決定を出す（K2 と同じ実装上の仮定）。ほかのタイプのエネルギーは選べるものに入らず、残る。"""
        state = board(attacker(CHARMANDER, (WATER, FIRE)))
        pending, done = use_and_discard(state)
        fire = fire_uids(state, state.players[0].active.pokemon_id)
        self.assertEqual(pending.decision.options, tuple(fire))
        self.assertEqual([state.card_def(u).provides for u in done.players[0].active.energy], [EnergyType.WATER])
        self.assertEqual(done.players[0].discard, fire)

    def test_declaration_needs_only_the_attack_cost(self):
        """宣言の条件は必要なエネルギーだけ（p.309）。足りなければ、トラッシュの前に拒否し、状態・乱数・ログを変えない（「炎」がない・
        数が足りない）。"""
        for energy in ((FIRE,), (WATER, WATER), (GRASS, WATER)):
            with self.subTest(energy=energy):
                state = board(attacker(CHARMANDER, energy))
                before = snapshot(state)
                with self.assertRaises(IllegalActionError) as ctx:
                    apply_command(state, UseAttack(0, 1))
                self.assertEqual(ctx.exception.code, "INSUFFICIENT_ENERGY")
                self.assertEqual(snapshot(state), before)

    def test_invalid_answers_change_nothing(self):
        """決定に合わない答え（ほかのタイプのエネルギー・ついていないカード・2 枚・同じカード 2 回・0 枚・相手・違う決定の番号・ほかの操作）は、
        状態・乱数・ログを変えない。そのあと正しい答えで続けられる。"""
        state = board(attacker(CHARMANDER, (FIRE, WATER, FIRE)))
        pending = apply_command(state, UseAttack(0, 1))
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
            (UseAttack(0, 0), "WRONG_PHASE"),
        ):
            with self.subTest(code=code, command=command):
                before = snapshot(pending)
                with self.assertRaises(IllegalActionError) as ctx:
                    apply_command(pending, command)
                self.assertEqual(ctx.exception.code, code)
                self.assertEqual(snapshot(pending), before)
        done = apply_command(pending, ResolveDecision(0, d.id, (d.options[1],)))
        self.assertEqual(done.players[0].discard, [d.options[1]])

    def test_commands_do_not_change_the_given_state(self):
        """``apply_command`` は渡された状態を変えない（宣言と決定への答えの両方）。決定を待つ状態は写しても同じ続きになる。"""
        state = board(attacker(CHARMANDER, (FIRE, FIRE, FIRE)))
        before = full(state)
        pending = apply_command(state, UseAttack(0, 1))
        self.assertEqual(full(state), before)
        waiting = full(pending)
        choice = (pending.decision.options[2],)
        expected = full(apply_command(pending, ResolveDecision(0, pending.decision.id, choice)))
        self.assertEqual(full(pending), waiting)
        for copied in (pending.clone(), copy.deepcopy(pending), pickle.loads(pickle.dumps(pending))):
            self.assertEqual(full(apply_command(copied, ResolveDecision(0, copied.decision.id, choice))), expected)

    def test_pending_decision_invariants_and_serialization(self):
        """決定を待つ状態は形式 1〜9 のどれでも書き出せる（進化していないヒトカゲ。形式 1 には決定の項目がないが、ワザの途中の決定は
        ``ValueError``）。決定の形が壊れていれば不変条件で見つかる。"""
        state = board(attacker(CHARMANDER, (FIRE, FIRE, FIRE)))
        pending = apply_command(state, UseAttack(0, 1))
        self.assertEqual(serialization_problems(pending), [])
        self.assertEqual(check_invariants(pending), [])
        d = pending.decision
        for name, broken in (
            ("種類", dataclasses.replace(d, kind="forced_switch")),
            ("決定するプレイヤー", dataclasses.replace(d, player=1)),
            ("選ぶ数", dataclasses.replace(d, max_choices=2)),
            ("選べるもの（足りない）", dataclasses.replace(d, options=d.options[:-1])),
            ("選べるもの（ついていないカード）", dataclasses.replace(d, options=(*d.options[:-1], pending.players[0].deck[0]))),
        ):
            with self.subTest(change=name):
                bad = pending.clone()
                bad.decision = broken
                self.assertTrue(any("ひのこ" in p for p in check_invariants(bad)), check_invariants(bad))

    def test_rams_self_damage(self):
        """ウインディのとっしん（既存の DamageAndSelfDamage(30)。kyuura の印刷の文面）: 相手に 80 → 自分に 30。エネルギーはトラッシュしない。"""
        state = board(attacker(ARCANINE, (FIRE, FIRE, FIRE, FIRE)), opponent={"card": GROWLITHE})
        done = apply_command(state, UseAttack(0, 1))
        damage = [(e["player"], e.get("target"), e["amount"]) for e in events(done, len(state.log)) if e["kind"] == "damage"]
        self.assertEqual(damage, [(1, None, 80), (0, "self", 30)])
        self.assertEqual((done.players[0].discard, len(done.players[0].active.energy)), ([], 4))

    def test_attacks_without_text(self):
        """説明文のないワザ（ひっかく 10・きりさく 30・ほのおパンチ 30）は決定を出さず、エネルギーをトラッシュしない。"""
        for card_id, index, energy, damage in ((CHARMANDER, 0, (FIRE,), 10), (CHARMELEON, 0, (WATER,) * 3, 30), (MAGMAR, 0, (FIRE, FIRE), 30)):
            with self.subTest(card=card_id):
                state = board(attacker(card_id, energy))
                done = apply_command(state, UseAttack(0, index))
                self.assertIsNone(done.decision)
                self.assertEqual((done.players[1].active.damage, done.players[0].discard), (damage, []))


# ---------------------------------------------------------------- ダメージの計算と、相手がダメージを受けない場合


def resistant_pool():
    """テスト専用: 炎に抵抗力（−30）のあるガーディ（今の対応カードに、炎に抵抗力のあるポケモンはいない。実在のカードではない）。"""
    extract = copy.deepcopy(read_extract())
    growlithe = next(c for c in extract["cards"] if c["id"] == GROWLITHE)
    resistant = copy.deepcopy(growlithe)
    resistant["id"] = "TEST-GROWLITHE-RESISTS-FIRE"
    resistant["pokemon"]["weaknesses"] = []
    resistant["pokemon"]["resistances"] = [{"type": "fire", "operator": "-", "value": 30}]
    extract["cards"].append(resistant)
    return pool_from_extract(extract)


class DamageCalculationTest(unittest.TestCase):
    def damage_after(self, state, choice=0):
        pending, done = use_and_discard(state, choice=choice)
        new = events(done, len(pending.log))
        return done, new

    def test_weakness_and_knock_out(self):
        """弱点 炎のキャタピー（HP 40）: 30 × 2 = 60 できぜつ。トラッシュはダメージの前、きぜつ・サイドはワザのあと。"""
        done, new = self.damage_after(board(attacker(CHARMANDER), CATERPIE))
        self.assertEqual([e["kind"] for e in new][:3], ["discard_energy", "damage", "knock_out"])
        self.assertEqual(new[1]["amount"], 60)
        self.assertEqual(len(done.players[0].discard), 1)

    def test_pluspower_and_defender(self):
        """プラスパワー（+10。p.321 の 5 段階）・ディフェンダー（−20。7 段階）は今までどおり計算する。"""
        cases = [
            (attacker(CHARMANDER, trainers=[(PLUSPOWER, TURN)]), GROWLITHE, 40),
            (attacker(CHARMANDER), {"card": GROWLITHE, "trainers": [(DEFENDER, TURN)]}, 10),
            (attacker(CHARMANDER, trainers=[(PLUSPOWER, TURN)]), {"card": CATERPIE, "trainers": [(DEFENDER, TURN)]}, 50),  # (30×2+10)−20
        ]
        for spec, opponent, expected in cases:
            with self.subTest(expected=expected):
                _, new = self.damage_after(board(spec, opponent))
                self.assertEqual([e["amount"] for e in new if e["kind"] == "damage"], [expected])
                self.assertEqual(new[0]["kind"], "discard_energy")

    def test_resistance_to_zero_still_discards(self):
        """抵抗力で最終ダメージが 0 でも、トラッシュはすんでいる（ダメージより先の効果。「ダメージを与えた後」の効果ではないので Z23 に
        かかわらず、宣言の前に止めない）。"""
        pool = resistant_pool()
        state = board(attacker(CHARMANDER), "TEST-GROWLITHE-RESISTS-FIRE", pool=pool)
        done, new = self.damage_after(state)
        self.assertEqual([e["kind"] for e in new][:2], ["discard_energy", "damage"])
        self.assertEqual((new[1]["amount"], done.players[1].active.damage, len(done.players[0].discard)), (0, 0, 1))

    def test_prevented_damage_still_discards(self):
        """「ダメージを受けない」状態（かたまる）の相手: ダメージの要素は無効（``damage_prevented``）でも、トラッシュはすんでいる。"""
        state = board(attacker(CHARMANDER), {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1})
        done, new = self.damage_after(state)
        self.assertEqual([e["kind"] for e in new][:2], ["discard_energy", "damage_prevented"])
        self.assertEqual((done.players[1].active.damage, len(done.players[0].discard)), (0, 1))

    def test_transparency(self):
        """「とうめい」（化石の秘密のゴースト）: 判定とコインはトラッシュのあと・ダメージの前。「おもて」なら受けず、「うら」なら受ける。
        どちらでもトラッシュはすんでいる。"""
        for side, damage in ((H, 0), (T, 30)):
            with self.subTest(coin=side):
                state = with_coin_results(board(attacker(CHARMANDER), {"card": HAUNTER, "evolved_from": GASTLY}), side)
                done, new = self.damage_after(state)
                names = [e["kind"] for e in new]
                self.assertEqual(names[0], "discard_energy")
                self.assertLess(names.index("discard_energy"), names.index("evade_check"))
                self.assertEqual(("attack_evaded" in names, done.players[1].active.damage, len(done.players[0].discard)),
                                 (side == H, damage, 1))

    def test_confusion_tails_skips_the_discard(self):
        """こんらんで「うら」なら、ワザの内容（トラッシュ・ダメージ）を処理しない（p.309 の手順 5。RUL- の記録の流れ）。決定を出さず、
        自分に 20（弱点 水なので炎のこんらんの 20 はそのまま）。「おもて」なら決定を出す。"""
        state = board(attacker(CHARMANDER, confusion=True))
        tails = apply_command(with_coin_results(state, T), UseAttack(0, 1))
        self.assertIsNone(tails.decision)
        self.assertNotIn("discard_energy", kinds(tails, len(state.log)))
        self.assertEqual((tails.players[0].discard, len(tails.players[0].active.energy)), ([], 2))
        self.assertEqual([e["amount"] for e in events(tails, len(state.log)) if e["kind"] == "confusion_damage"], [20])
        heads = apply_command(with_coin_results(state, H), UseAttack(0, 1))
        self.assertEqual(heads.decision.kind, "discard_energy")

    def test_counterattack(self):
        """カイリキーの「はんげき」（特殊能力のダメージ 10）は、ワザのダメージの要素のあと。トラッシュはその前。"""
        state = board(attacker(CHARMANDER), {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE]})
        done, new = self.damage_after(state)
        self.assertEqual([e["kind"] for e in new][:3], ["discard_energy", "damage", "counterattack"])
        self.assertEqual(done.players[0].active.damage, 10)


# ---------------------------------------------------------------- 宣言の前の確かめ（既存の裁定で止める場面）と先読みの方法


class PreflightTest(unittest.TestCase):
    def stop_cases(self):
        machamp = {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], "damage": 70}  # HP 100。ひのこ 30 できぜつ
        moltres = {"card": ROCKETS_MOLTRES, "damage": 30, "retaliation": TURN - 1}  # HP 60。ほのおのかべ（10 を返す）
        return [
            ("C18: はんげき", attacker(CHARMANDER, damage=40), machamp, "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT"),
            ("W24: ほのおのかべ", attacker(CHARMANDER, damage=40), moltres, "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT"),
        ]

    def test_existing_rulings_stop_before_declaration(self):
        """ワザのダメージでの相手のきぜつと、相手の効果の 10 での自分のきぜつがそろいうる場合は、既存の裁定（C18・W24）で、宣言の前
        （トラッシュするカードの決定の前）に止める。トラッシュする決定のすべての答えを試すので、先読みの方法（derived・derived_full・
        比べる方法 legacy）のどれでも、コインの結果によらず止まり、状態・乱数・ログを変えない。"""
        for name, spec, opponent, code in self.stop_cases():
            for mode in PREFLIGHT_MODES:
                for side in (H, T):
                    with self.subTest(case=name, mode=mode, coin=side):
                        state = with_coin_results(board(spec, opponent), side)
                        before = snapshot(state)
                        with self.assertRaises(UnsupportedError) as ctx:
                            apply_kernel(state, UseAttack(0, 1), preflight=mode)
                        self.assertEqual(ctx.exception.code, code)
                        self.assertEqual(snapshot(state), before)

    def test_preflight_modes_agree(self):
        """止めない場面では、先読みの方法によらず、決定を待つ状態と、答えたあとの状態が同じ（「とうめい」のコインの両方・こんらんのコインの
        両方・はんげき・ディフェンダー）。"""
        boards = [
            board(attacker(CHARMANDER, (FIRE, FIRE, FIRE))),
            board(attacker(CHARMANDER), {"card": HAUNTER, "evolved_from": GASTLY}),
            board(attacker(CHARMANDER, confusion=True)),
            board(attacker(CHARMANDER), {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE]}),
            board(attacker(MAGMAR, (FIRE, FIRE, FIRE)), {"card": GROWLITHE, "trainers": [(DEFENDER, TURN)]}),
        ]
        for i, state in enumerate(boards):
            for coins in ((H, H), (T, T), (H, T), (T, H)):
                with self.subTest(board=i, coins=coins):
                    results = []
                    for mode in PREFLIGHT_MODES:
                        pending = apply_kernel(with_coin_results(state, *coins), UseAttack(0, 1), preflight=mode)
                        if pending.decision is None:
                            results.append((full(pending), None))
                            continue
                        choice = (pending.decision.options[-1],)
                        done = apply_kernel(pending, ResolveDecision(0, pending.decision.id, choice), preflight=mode)
                        results.append((full(pending), full(done)))
                    self.assertTrue(all(result == results[0] for result in results))

    def test_branch_count_is_bounded_by_attached_fire(self):
        """先読みで試す結果の数は、トラッシュの答え（ついている「炎」の枚数 n）×「とうめい」のコイン 2 + こんらんの「うら」1 で、60 枚の
        デッキで上限（4,096）に届かない（docs/preflight-consolidation-v0.16c.md 3 章の上界の見直し）。"""
        for n in (1, 2, 20):
            for confused in (False, True):
                spec = attacker(CHARMANDER, (FIRE,) * n + ((WATER,) if n == 1 else ()), **({"confusion": True} if confused else {}))
                state = with_coin_results(board(spec, {"card": HAUNTER, "evolved_from": GASTLY}), H, H)
                for mode in ("derived", "derived_full"):
                    with self.subTest(n=n, confused=confused, mode=mode):
                        (result,) = preflight_results(state, UseAttack(0, 1), mode)
                        self.assertEqual((result.strategy, result.branches), ("full", 2 * n + confused))


class UnreachableTest(unittest.TestCase):
    def test_no_fire_to_discard_follows_the_play_text(self):
        """「トラッシュできないとき」は、自分のワザとして使うときは必要なエネルギーから起こらない。v0.30 では起こらないのでエンジンの不具合
        （``RuntimeError``）にしていた。v0.31 の相手のワザを自分のワザとして使う効果（必要なエネルギーはいらない）で起こるようになったので、
        処理に使う文面のとおりに扱う: 最新の説明（RUL-ENERGY-DISCARD-ATTACKS）の「ダメージはなくなる」はダメージの要素を処理しない、第4弾のポニータ
        の印刷の文面の「ダメージは0になる」は基本となるダメージを 0 にして計算する（p.321 の 2 段階で計算を終える）。どちらもトラッシュはなく、
        ログ ``discard_energy_failed`` に扱いを残す。枠を直接開いて起こす（ゆびをふるの経路は tests/test_held_cards_v0_31.py）。"""
        for card_id, index, _, _ in DISCARD_ATTACKS:
            with self.subTest(card=card_id):
                state = board(attacker(card_id, (WATER, WATER, WATER)))
                effect = E.DEFAULT_EFFECTS.attack_entry(card_id, index).effect
                use = open_attack(state, 0, attack_index=index)
                self.assertEqual(use.key, E.AttackKey(card_id, index))
                since = len(state.log)
                effect.resolve(state, use)
                (failed,) = [e for e in events(state, since) if e["kind"] == "discard_energy_failed"]
                zero = card_id == ROCKET_PONYTA
                self.assertEqual((failed["outcome"], failed["needed"], failed["attached"]), ("zero" if zero else "none", 1, 0))
                self.assertNotIn("discard_energy", kinds(state, since))
                damages = [e for e in events(state, since) if e["kind"] == "damage"]
                self.assertEqual([(e["amount"], e.get("stopped_after_step_2")) for e in damages], [(0, True)] if zero else [])
                self.assertEqual(state.players[1].active.damage, 0)
                self.assertIsNone(state.decision)


# ---------------------------------------------------------------- 進化


class EvolutionTest(unittest.TestCase):
    def test_evolution_by_name(self):
        """ヒトカゲ → リザード、ガーディ（第1弾。v0.2a から）→ ウインディは、通常の進化の操作で成り立つ（進化元は名前の完全一致）。
        進化したあと、エネルギーはそのまま、かえんほうしゃを使える。"""
        for base, evolved in ((CHARMANDER, CHARMELEON), (GROWLITHE, ARCANINE)):
            with self.subTest(evolved=evolved):
                state = board({"card": base, "energy": [FIRE, FIRE, FIRE]}, hand=[evolved])
                pid = state.players[0].active.pokemon_id
                new = apply_command(state, EvolvePokemon(0, state.players[0].hand[0], pid))
                me = new.players[0].active
                self.assertEqual((new.cards[me.card].card_id, me.pokemon_id, len(me.energy)), (evolved, pid, 3))
                index = 1 if evolved == CHARMELEON else 0
                pending = apply_command(new, UseAttack(0, index))
                done = apply_command(pending, ResolveDecision(0, pending.decision.id, (pending.decision.options[0],)))
                self.assertEqual((done.players[1].active.damage, len(done.players[0].discard)), (50, 1))

    def test_evolution_onto_another_name_is_rejected(self):
        """名前の合わない進化は拒否する（リザードをガーディ・第4弾のポニータに、ウインディをヒトカゲに）。状態を変えない。"""
        for base, evolved in ((GROWLITHE, CHARMELEON), (ROCKET_PONYTA, CHARMELEON), (CHARMANDER, ARCANINE), (PONYTA, ARCANINE)):
            with self.subTest(base=base, evolved=evolved):
                state = board({"card": base, "energy": [FIRE]}, hand=[evolved])
                before = snapshot(state)
                with self.assertRaises(IllegalActionError) as ctx:
                    apply_command(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].active.pokemon_id))
                self.assertEqual(ctx.exception.code, "EVOLUTION_NAME_MISMATCH")
                self.assertEqual(snapshot(state), before)


if __name__ == "__main__":
    unittest.main()

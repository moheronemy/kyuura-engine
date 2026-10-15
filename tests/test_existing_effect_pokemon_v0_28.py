"""v0.28: 既存の効果の型の登録だけで加えたポケモン 10 枚（docs/existing-effect-pokemon-v0.28.md）。

新しい型・要素・状態・決定はない。このファイルは、登録の誤り（ワザの位置・名前・型・パラメーター）と、カードごとに違うパラメーターが処理に
届いていることだけを確かめる。型そのものの境界（コインの結果・特殊状態の重なり・「ダメージを受けない」状態・きぜつの時点など）は、型を加えた版の
テストが確かめている（ParalyzeOnHeads・PutToSleep: v0.3b、ConfuseOnHeads: v0.3c、PreventDamageOnHeads: v0.4b、DamageAndRemoveCounters: v0.5、
ExtraEnergyDamage: v0.6、DiscardEnergyAndRemoveAllCounters: v0.7、DamageAndSelfDamage: v0.10、ConfuseOnHeadsWithoutDamage: v0.17a）。

根拠の誌面（『オフィシャルブック2000』[P43]。照合の記録は kyuura_engine/data/card_verification.json）: ラプラス p.116・スターミー p.112・トサキント p.108・
アズマオウ p.109・カイロス p.58・タマタマ p.49・プリン p.225・ラッキー p.235・スリープ p.164・シェルダー p.103。一般の規定は p.309（ワザの手順）・
p.310（進化）・p.320（ワザの要素）・p.321（ダメージの計算）・p.322（特殊状態・持続する効果）。kyuura の記録 id: NEO-2000-OFFICIAL-RULES
（10 枚のカードの LD-・CC- は kyuura にない。research_links.json の registered_without_kyuura_record・engine_verified_without_kyuura_record）。
"""

from __future__ import annotations

import unittest

from kyuura_engine import EvolvePokemon, IllegalActionError, ResolveDecision, UnsupportedError, UseAttack, apply_command, state_to_dict
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, read_extract, read_verification
from kyuura_engine.resolution import programs
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    CHANSEY, DROWZEE, EXEGGCUTE, FIRE, GASTLY, GIOVANNIS_MACHAMP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHOP, GOLDEEN, GRASS, H, HAUNTER,
    JIGGLYPUFF, LAPRAS, MACHAMP, MACHOKE, MACHOP, PINSIR, PSYCHIC, RATTATA, SEAKING, SHELLDER, STARMIE, STARYU, T, V0_28_POKEMON, WATER,
    apply_kernel, build_test_state, coin_events, with_coin_results,
)

WATER_TYPE = EnergyType.WATER
# (カード id, ワザの位置) → (名前, 実装, 出典)。出典が None のワザは説明文がない（DamageOnly）
EXPECTED = {
    (LAPRAS, 0): ("みずでっぽう", E.ExtraEnergyDamage(energy_type=WATER_TYPE, per_energy=10, max_extra=2), "P43 p.116"),
    (LAPRAS, 1): ("あやしいひかり", E.ConfuseOnHeads(), "P43 p.116"),
    (STARMIE, 0): ("じこさいせい", E.DiscardEnergyAndRemoveAllCounters(energy_type=WATER_TYPE), "P43 p.112"),
    (STARMIE, 1): ("スターフリーズ", E.ParalyzeOnHeads(), "P43 p.112"),
    (GOLDEEN, 0): ("つのでつく", E.DAMAGE_ONLY, None),
    (SEAKING, 0): ("つのでつく", E.DAMAGE_ONLY, None),
    (SEAKING, 1): ("たきのぼり", E.DAMAGE_ONLY, None),
    (PINSIR, 0): ("まんりきばさみ", E.ParalyzeOnHeads(), "P43 p.58"),
    (PINSIR, 1): ("ハサミギロチン", E.DAMAGE_ONLY, None),
    (EXEGGCUTE, 0): ("さいみんじゅつ", E.PutToSleep(), "P43 p.49"),
    (EXEGGCUTE, 1): ("やどりぎのタネ", E.DamageAndRemoveCounters(counters=1), "P43 p.49"),
    (JIGGLYPUFF, 0): ("こもりうた", E.PutToSleep(), "P43 p.225"),
    (JIGGLYPUFF, 1): ("はたく", E.DAMAGE_ONLY, None),
    (CHANSEY, 0): ("まるまる", E.PreventDamageOnHeads(), "P43 p.235"),
    (CHANSEY, 1): ("すてみタックル", E.DamageAndSelfDamage(self_damage=80), "P43 p.235"),
    (DROWZEE, 0): ("はたく", E.DAMAGE_ONLY, None),
    (DROWZEE, 1): ("あやしいひかり", E.ConfuseOnHeads(), "P43 p.164"),
    (SHELLDER, 0): ("ちょうおんぱ", E.ConfuseOnHeadsWithoutDamage(), "P43 p.103"),
    (SHELLDER, 1): ("からをとじる", E.PreventDamageOnHeads(), "P43 p.103"),
}
PAGES = {LAPRAS: 116, STARMIE: 112, GOLDEEN: 108, SEAKING: 109, PINSIR: 58, EXEGGCUTE: 49, JIGGLYPUFF: 225, CHANSEY: 235, DROWZEE: 164,
         SHELLDER: 103}


def board(attacker, defender, turn_number=7, **kwargs):
    return build_test_state([{"active": attacker}, {"active": defender}], turn_number=turn_number, **kwargs)


def snapshot(state):
    return state_to_dict(state, format_version=9), rng_fingerprint(state.rng), len(state.log)


def events(state, since, kind):
    return [dict(e) for e in state.log[since:] if e["kind"] == kind]


def attack_coins(state, since):
    """ワザの説明のコイン（``source="attack"``）。ワザで番が終わったあとのポケモンチェックのねむりのコインは数えない。"""
    return [e for e in coin_events(state, since) if e["source"] == "attack"]


def conditions_given(state, since):
    """ワザで与えた特殊状態（ログ ``special_condition``。ポケモンチェックで回復していても残る記録）。"""
    return [e["condition"] for e in events(state, since, "special_condition")]


class RegistrationTest(unittest.TestCase):
    """登録表・分類・照合の記録（位置・名前・型・パラメーター・出典のずれを見つける）。"""

    def test_every_attack_is_registered_with_the_expected_effect(self):
        """10 枚のすべてのワザが、決めた位置・名前・実装（型とパラメーター）・出典で登録されていて、ほかの位置の登録はない。"""
        pool = load_card_pool()
        registered = {(k.card_id, k.attack_index) for k in E.DEFAULT_EFFECTS.attack_keys() if k.card_id in V0_28_POKEMON}
        self.assertEqual(registered, set(EXPECTED))
        for card_id in V0_28_POKEMON:
            definition = pool.get(card_id)
            self.assertTrue(definition.supported, definition.unsupported_reasons)
            self.assertEqual(definition.powers, ())
            self.assertEqual({(card_id, a.index) for a in definition.attacks}, {k for k in EXPECTED if k[0] == card_id})
            for attack in definition.attacks:
                with self.subTest(card=card_id, attack=attack.index):
                    name, effect, source = EXPECTED[(card_id, attack.index)]
                    entry = E.DEFAULT_EFFECTS.attack_entry(card_id, attack.index)
                    self.assertEqual((attack.name_ja, entry.name_ja), (name, name))
                    self.assertIs(type(entry.effect), type(effect))
                    self.assertEqual(entry.effect, effect)  # パラメーター（エネルギーの種類・数）まで同じ
                    self.assertEqual(entry.source, source)
                    self.assertEqual(entry.play_text_ja is None, source is None)
                    self.assertEqual(entry.text_ja, attack.text_ja)
                    self.assertIsNone(E.DEFAULT_EFFECTS.attack_problem(card_id, attack))
                    self.assertTrue(attack.supported)

    def test_pool_and_verification_records(self):
        """写しの組 pool_v0_28 は 10 枚。照合の記録はページ（p.n = PDF n+2）と確認日を持つ。"""
        self.assertEqual(read_extract()["pool_v0_28"], list(V0_28_POKEMON))
        records = read_verification()["cards"]
        for card_id, page in PAGES.items():
            record = records[card_id]
            self.assertEqual((record["page"], record["pdf_page"], record["checked_on"]), (page, page + 2, "2026-10-15"))
            self.assertIn(record["status"], ("一致", "不一致あり"))
        # タマタマの「やどりぎのタネ」は、誌面の表記（ひらがなの「たね」）との違いを記録し、登録の照合は kyuura の写しの名前で行う
        names = [m for m in records[EXEGGCUTE]["mismatches"] if m["field"] == "pokemon.attacks[1].name.ja"]
        self.assertEqual([(m["kyuura"], m["official_book_2000"][:7]) for m in names], [("やどりぎのタネ", "やどりぎのたね")])

    def test_evolution_cards_keep_their_printed_lineage(self):
        """スターミーはヒトデマン（v0.1 から対応）から、アズマオウはトサキントから進化する 1 進化（p.112・p.109 の「○○から進化」）。"""
        pool = load_card_pool()
        for card_id, basic in ((STARMIE, STARYU), (SEAKING, GOLDEEN)):
            definition = pool.get(card_id)
            self.assertEqual((definition.stage, definition.evolves_from), ("stage1", pool.get(basic).name_ja))
            self.assertTrue(pool.get(basic).is_basic_pokemon and pool.is_playable(basic))

    def test_checks_reject_wrong_types_and_parameters(self):
        """型の確認（check）が、取りちがえた登録を拒否する: ダメージのある・ないワザの取りちがえ、エネルギーの種類の取りちがえ。
        既存の検査をゆるめていない（v0.28 で check を変えていない）。"""
        pool = load_card_pool()
        attack = {key: pool.get(key[0]).attacks[key[1]] for key in EXPECTED}
        wrong = (
            (E.ConfuseOnHeads(), attack[(SHELLDER, 0)]),  # ダメージの目安のないワザに、ダメージのあるこんらんの型
            (E.ConfuseOnHeadsWithoutDamage(), attack[(LAPRAS, 1)]),  # ダメージの目安のあるワザに、ダメージのないこんらんの型
            (E.ConfuseOnHeadsWithoutDamage(), attack[(DROWZEE, 1)]),
            (E.PutToSleep(), attack[(JIGGLYPUFF, 1)]),
            (E.DAMAGE_ONLY, attack[(PINSIR, 0)]),  # 説明文のあるワザを効果のないワザに
            (E.DAMAGE_ONLY, attack[(LAPRAS, 0)]),  # 「+」のあるワザを効果のないワザに
            (E.ExtraEnergyDamage(energy_type=EnergyType.PSYCHIC, per_energy=10, max_extra=2), attack[(LAPRAS, 0)]),
            (E.DiscardEnergyAndRemoveAllCounters(energy_type=EnergyType.PSYCHIC), attack[(STARMIE, 0)]),
            (E.PreventDamageOnHeads(), attack[(CHANSEY, 1)]),
            (E.DamageAndSelfDamage(self_damage=80), attack[(CHANSEY, 0)]),
        )
        for effect, data in wrong:
            with self.subTest(effect=type(effect).__name__, attack=data.name_ja):
                self.assertTrue(effect.check(data))

    def test_programs_keep_damage_and_no_damage_statuses_apart(self):
        """ダメージのある特殊状態のワザ（Damage → Status）と、ダメージのないワザ（Status だけ）の要素の並び。"""
        def program(key):
            return programs.compile_attack(E.DEFAULT_EFFECTS.attack_entry(*key).effect)

        with_damage = ((LAPRAS, 1), (STARMIE, 1), (PINSIR, 0), (DROWZEE, 1))
        without_damage = ((SHELLDER, 0), (EXEGGCUTE, 0), (JIGGLYPUFF, 0))
        for key in with_damage:
            self.assertEqual([type(e) for e in program(key)], [programs.Damage, programs.Status], key)
            self.assertEqual(program(key)[1].local_coin, H)
        for key in without_damage:
            self.assertEqual([type(e) for e in program(key)], [programs.Status], key)
        self.assertEqual(program((SHELLDER, 0))[0].local_coin, H)
        self.assertIsNone(program((EXEGGCUTE, 0))[0].local_coin)
        self.assertEqual(program((CHANSEY, 1))[1], programs.Damage(programs.SELF, programs.Fixed(80), name="self_damage"))
        self.assertEqual(program((LAPRAS, 0)), (programs.Damage(programs.OPP, programs.ExtraEnergy(WATER_TYPE, 10, 2)),))


class StatusAttackTest(unittest.TestCase):
    """特殊状態のワザ: ダメージのあるワザはダメージのログ → ワザのコイン（あれば）→ 特殊状態、ダメージのないワザはダメージのログがない
    （p.320）。ねむりのワザにはコインがない（p.49・p.225 の最新の説明）。"""

    CASES = (
        # (攻撃するポケモン, ワザの位置, ダメージ（ワンリキー。HP 50・弱点 超）, ワザのコインの数, 特殊状態)
        ({"card": LAPRAS, "energy": [WATER, WATER]}, 1, 10, 1, "confusion"),
        ({"card": STARMIE, "evolved_from": STARYU, "energy": [WATER, WATER, WATER]}, 1, 20, 1, "paralysis"),
        ({"card": PINSIR, "energy": [GRASS, GRASS]}, 0, 20, 1, "paralysis"),
        ({"card": DROWZEE, "energy": [PSYCHIC, PSYCHIC]}, 1, 20, 1, "confusion"),  # 超の 10 がワンリキーの弱点（超）で 20
        ({"card": SHELLDER, "energy": [WATER]}, 0, None, 1, "confusion"),
        ({"card": EXEGGCUTE, "energy": [PSYCHIC]}, 0, None, 0, "sleep"),
        ({"card": JIGGLYPUFF, "energy": [FIRE]}, 0, None, 0, "sleep"),
    )

    def test_damage_coin_and_condition(self):
        for attacker, index, damage, coins, condition in self.CASES:
            with self.subTest(card=attacker["card"], attack=index):
                state = board(attacker, MACHOP)
                new = apply_command(with_coin_results(state, H, T), UseAttack(0, index))  # 2 枚目はポケモンチェックのねむりのコイン
                since = len(state.log)
                self.assertEqual([e["amount"] for e in events(new, since, "damage")], [] if damage is None else [damage])
                self.assertEqual(len(attack_coins(new, since)), coins)
                self.assertEqual(conditions_given(new, since), [condition])
                self.assertEqual(new.players[1].active.damage, damage or 0)
                kinds = [e["kind"] for e in new.log[since:]]
                if damage is not None:  # ダメージ → ワザのコイン → 特殊状態（p.320 の順番）
                    self.assertLess(kinds.index("damage"), kinds.index("coin_flip"))
                    self.assertLess(kinds.index("coin_flip"), kinds.index("special_condition"))

    def test_tails_gives_no_condition(self):
        for attacker, index, damage, coins, condition in self.CASES:
            if not coins:
                continue
            with self.subTest(card=attacker["card"], attack=index):
                state = board(attacker, MACHOP)
                new = apply_command(with_coin_results(state, T), UseAttack(0, index))
                self.assertEqual(conditions_given(new, len(state.log)), [])
                self.assertEqual(new.players[1].active.damage, damage or 0)


class LaprasTest(unittest.TestCase):
    """みずでっぽう（水。10+。p.116）: 必要なエネルギー（水 1）より多い「水」エネルギー 1 個につき 10 を、2 個ぶんまで基本となるダメージに加える。"""

    def test_extra_water_and_cap(self):
        for energy, base in (([WATER], 10), ([WATER, WATER], 20), ([WATER] * 3, 30), ([WATER] * 4, 30), ([WATER] * 5, 30),
                             ([WATER, FIRE, FIRE, PSYCHIC], 10), ([WATER, WATER, GRASS], 20)):
            with self.subTest(energy=energy):
                state = board({"card": LAPRAS, "energy": energy}, RATTATA)
                new = apply_command(state, UseAttack(0, 0))
                (damage,) = events(new, len(state.log), "damage")
                self.assertEqual(damage["steps"][0], ("1 基本となる計算", base))
                self.assertEqual(damage["amount"], base)

    def test_weakness_after_the_extra_damage(self):
        """追加したダメージが基本となるダメージで、そのあと弱点（p.321 の 3 段階）。スリープ（弱点 超）ではなく、水が弱点のポケモンがいないので、
        プラスパワー（5 段階）で順番を確かめる。"""
        from tests.helpers import PLUSPOWER
        state = board({"card": LAPRAS, "energy": [WATER] * 3, "trainers": [(PLUSPOWER, 7)]}, RATTATA)
        new = apply_command(state, UseAttack(0, 0))
        (damage,) = events(new, len(state.log), "damage")
        self.assertEqual((damage["steps"][0][1], damage["amount"]), (30, 40))


class StarmieTest(unittest.TestCase):
    """じこさいせい（水水。p.112）: ついている「水」エネルギーカードから 1 枚を選んでトラッシュし、ダメージカウンターをすべてとりのぞく。"""

    def test_only_water_energy_can_be_discarded(self):
        starmie = {"card": STARMIE, "evolved_from": STARYU, "energy": [WATER, FIRE, WATER, PSYCHIC], "damage": 40}
        state = board(starmie, RATTATA)
        new = apply_command(state, UseAttack(0, 0))
        attacker = new.players[0].active
        waters = tuple(u for u in attacker.energy if new.cards[u].card_id == WATER)
        self.assertEqual((new.decision.kind, new.decision.player, new.decision.options), ("discard_energy", 0, waters))
        done = apply_command(new, ResolveDecision(0, new.decision.id, (waters[1],)))
        attacker = done.players[0].active
        self.assertEqual(attacker.damage, 0)
        self.assertEqual(sorted(done.cards[u].card_id for u in attacker.energy), sorted([WATER, FIRE, PSYCHIC]))
        self.assertIn(waters[1], done.players[0].discard)
        self.assertEqual([e["counters"] for e in events(done, len(state.log), "remove_all_damage_counters")], [4])

    def test_other_energy_cannot_be_chosen(self):
        state = board({"card": STARMIE, "evolved_from": STARYU, "energy": [WATER, FIRE, WATER], "damage": 20}, RATTATA)
        new = apply_command(state, UseAttack(0, 0))
        fire = next(u for u in new.players[0].active.energy if new.cards[u].card_id == FIRE)
        before = snapshot(new)
        with self.assertRaises(IllegalActionError):
            apply_command(new, ResolveDecision(0, new.decision.id, (fire,)))
        self.assertEqual(snapshot(new), before)


class ChanseyTest(unittest.TestCase):
    """すてみタックル（無無無無。80。p.235）: 相手に 80、そのあと自分にも 80（ワザによるダメージ。自分のタイプ（無色）と自分の弱点・抵抗力で計算。
    v0.3d）。まるまる（無無。p.235）: 「おもて」なら次の相手の番「ダメージを受けない」。"""

    def chansey(self, **extra):
        return {"card": CHANSEY, "energy": [WATER] * 4, **extra}

    def test_self_damage_is_80(self):
        state = board(self.chansey(), {"card": MACHOP, "damage": 0})
        new = apply_command(state, UseAttack(0, 1))
        logged = events(new, len(state.log), "damage")
        self.assertEqual([(e.get("target"), e["amount"]) for e in logged], [(None, 80), ("self", 80)])
        self.assertEqual(new.players[0].active.damage, 80)

    def test_self_damage_reaches_the_preflight(self):
        """自分への 80 が宣言の前の確かめ（先読み）にも入る: カイリキー（HP 100。はんげき）にダメージ 20 のとき、80 でカイリキーがきぜつし、
        ラッキー（HP 120）はダメージ 30 + 自分への 80 = 110、はんげきの 10 で 120 になりうるので C18（UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT）で
        宣言の前に止まる（自分への 80 を数えなければ 40 で止まらない）。ダメージ 20 なら 110 でとどまり、受け付ける。どの先読みの方法でも同じ。"""
        machamp = {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], "damage": 20}
        stopped = board(self.chansey(damage=30), machamp)
        accepted = board(self.chansey(damage=20), machamp)
        for mode in ("derived", "derived_full", "legacy"):
            with self.subTest(preflight=mode):
                before = snapshot(stopped)
                with self.assertRaises(UnsupportedError) as ctx:
                    apply_kernel(stopped, UseAttack(0, 1), preflight=mode)
                self.assertEqual(ctx.exception.code, "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")
                self.assertEqual(snapshot(stopped), before)
                new = apply_kernel(accepted, UseAttack(0, 1), preflight=mode)
                self.assertEqual(new.players[0].active.damage, 110)
                self.assertEqual(new.decision.kind, "take_prize")

    def test_scrunch_heads_gives_the_prevent_damage_effect(self):
        for side, added in ((H, 1), (T, 0)):
            state = board({"card": CHANSEY, "energy": [WATER, WATER]}, RATTATA)
            new = apply_command(with_coin_results(state, side), UseAttack(0, 0))
            effects = events(new, len(state.log), "persistent_effect_added")
            self.assertEqual(len(effects), added)
            self.assertEqual(events(new, len(state.log), "damage"), [])


class EvolutionTest(unittest.TestCase):
    """通常の進化（p.310）: 進化元の名前が合うポケモンにだけ重ねる。v0.28 で進化の処理は変えていない。"""

    def state(self, hand, active, bench=()):
        return build_test_state([{"active": active, "bench": list(bench), "hand": list(hand)}, {"active": RATTATA}], turn_number=3)

    def test_starmie_and_seaking_evolve_from_their_basics(self):
        state = self.state([STARMIE, SEAKING], STARYU, [GOLDEEN])
        staryu, goldeen = state.players[0].in_play()
        hand = {state.cards[u].card_id: u for u in state.players[0].hand}
        new = apply_command(state, EvolvePokemon(0, hand[STARMIE], staryu.pokemon_id))
        new = apply_command(new, EvolvePokemon(0, hand[SEAKING], goldeen.pokemon_id))
        self.assertEqual([new.cards[p.card].card_id for p in new.players[0].in_play()], [STARMIE, SEAKING])

    def test_names_must_match(self):
        state = self.state([STARMIE, SEAKING], STARYU, [GOLDEEN, SHELLDER])
        staryu, goldeen, shellder = state.players[0].in_play()
        hand = {state.cards[u].card_id: u for u in state.players[0].hand}
        for card_id, target in ((STARMIE, goldeen), (SEAKING, staryu), (STARMIE, shellder)):
            with self.subTest(card=card_id, target=state.cards[target.card].card_id):
                before = snapshot(state)
                with self.assertRaises(IllegalActionError) as ctx:
                    apply_command(state, EvolvePokemon(0, hand[card_id], target.pokemon_id))
                self.assertEqual(ctx.exception.code, "EVOLUTION_NAME_MISMATCH")
                self.assertEqual(snapshot(state), before)

    def test_first_turn_and_played_this_turn(self):
        """おたがいの最初の番・その番に場に出したたねポケモンは進化できない（p.310。v0.4a の規定のまま）。"""
        state = build_test_state([{"active": STARYU, "hand": [STARMIE]}, {"active": RATTATA}], turn_number=1)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].active.pokemon_id))
        self.assertEqual(ctx.exception.code, "FIRST_TURN_EVOLUTION")
        state = build_test_state([{"active": {"card": GOLDEEN, "played_turn": 3}, "hand": [SEAKING]}, {"active": RATTATA}], turn_number=3)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].active.pokemon_id))
        self.assertEqual(ctx.exception.code, "PLAYED_THIS_TURN")


class KnownUnresolvedTest(unittest.TestCase):
    """既知の未解決の境界は、既存の型と同じ問い・同じ停止コードで止まる（新しい問い・コードはない）。"""

    def test_transparency_stops_damage_then_coin_statuses(self):
        """「とうめい」のゴーストに、ダメージ → ワザのコイン → 特殊状態 のワザは T19b（UNRESOLVED_EVADED_EFFECT_COIN）で宣言の前に止まる（v0.9）。
        ダメージのないちょうおんぱは止まらない（ねこノミと同じ。T19・T22）。"""
        haunter = {"card": HAUNTER, "evolved_from": GASTLY}
        for attacker, index in (({"card": LAPRAS, "energy": [WATER, WATER]}, 1), ({"card": PINSIR, "energy": [GRASS, GRASS]}, 0),
                                ({"card": DROWZEE, "energy": [PSYCHIC, PSYCHIC]}, 1),
                                ({"card": STARMIE, "evolved_from": STARYU, "energy": [WATER] * 3}, 1)):
            with self.subTest(card=attacker["card"]):
                state = board(attacker, haunter)
                before = snapshot(state)
                with self.assertRaises(UnsupportedError) as ctx:
                    apply_command(state, UseAttack(0, index))
                self.assertEqual(ctx.exception.code, "UNRESOLVED_EVADED_EFFECT_COIN")
                self.assertEqual(snapshot(state), before)
        state = board({"card": SHELLDER, "energy": [WATER]}, haunter)
        new = apply_command(with_coin_results(state, H, T), UseAttack(0, 0))  # ワザのコイン「おもて」→「とうめい」のコイン「うら」
        self.assertEqual(conditions_given(new, len(state.log)), ["confusion"])

    def test_guts_with_status_effect_stops(self):
        """「こんじょう」を使えるサカキのカイリキーが、ダメージで HP 以上になりうるうえ同じワザでマヒ・こんらんを受ける場合は G37
        （UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT）で止まる（v0.11）。ダメージのないワザ（こもりうた）は効果だけなので止まらない。"""
        gmachamp = {"card": GIOVANNIS_MACHAMP, "evolved_from": [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], "damage": 90}
        for attacker, index in (({"card": PINSIR, "energy": [GRASS, GRASS]}, 0), ({"card": LAPRAS, "energy": [WATER, WATER]}, 1)):
            with self.subTest(card=attacker["card"]):
                state = board(attacker, gmachamp)
                with self.assertRaises(UnsupportedError) as ctx:
                    apply_command(state, UseAttack(0, index))
                self.assertEqual(ctx.exception.code, "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT")
        state = board({"card": JIGGLYPUFF, "energy": [FIRE]}, gmachamp)
        new = apply_command(state, UseAttack(0, 0))
        self.assertEqual(conditions_given(new, len(state.log)), ["sleep"])


if __name__ == "__main__":
    unittest.main()

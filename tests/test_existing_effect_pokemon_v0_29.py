"""v0.29: 既存の効果の型の登録だけで加えたポケモン 14 枚（kyuura データの採用。docs/existing-effect-pokemon-v0.29.md）。

新しい型・要素・状態・決定・停止コードはない。このファイルは、登録の誤り（ワザの位置・名前・型・パラメーター・処理に使う文面の根拠）と、カードごとに
違うパラメーター（コインの枚数・「おもて」1 枚あたりのダメージ・追加するエネルギーの上限）が処理に届いていること、ダメージのある特殊状態のワザと
ダメージのない特殊状態のワザの区別を確かめる。型そのものの境界は、型を加えた版のテストが確かめている（CoinFlipDamage: v0.2d・v0.4b・v0.4c、
PoisonOnHeads: v0.3a、ParalyzeOnHeads・PutToSleep: v0.3b、ExtraEnergyDamage: v0.6、PoisonWithoutDamage: v0.8、ConfuseOnHeadsWithoutDamage: v0.17a）。

根拠: 2026-10-15 からのカードデータの方針（docs/card-data-policy.md）で、kyuura の data/cards.json（写しの元 ecb2d69）を基本データとして採用し、
pcg-search.com の同じ版のページと照合した（kyuura_engine/data/card_sources.json。ガイドブックは読んでいない）。研究の基準のコミット（3f34908）に、
14 枚を指す kyuura の記録（LD-・CC-・CR-・UQ-・エラッタ）はない。処理に使う文面は kyuura の印刷の文面。一般の規定は p.309（ワザの手順）・p.320（ワザの
要素）・p.321（ダメージの計算）・p.322（特殊状態）で、既存の型の照合の記録（NEO-2000-OFFICIAL-RULES）を使う。
"""

from __future__ import annotations

import unittest

from kyuura_engine import EvolvePokemon, IllegalActionError, Retreat, UnsupportedError, UseAttack, apply_command, state_to_dict
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, read_extract, read_verification
from kyuura_engine.resolution import programs
from kyuura_engine.rng import rng_fingerprint
from scripts import check_card_sources as cs
from tests.helpers import (
    BROCKS_GEODUDE, BROCKS_LICKITUNG, BROCKS_ZUBAT, CATERPIE, DRATINI, FIGHTING, FIRE, GASTLY, GRASS, H, HAUNTER, LIGHTNING, LT_SURGES_MAGNEMITE,
    LT_SURGES_VOLTORB, MACHOKE, MACHOP, METAPOD, MISTYS_GOLDEEN, POLIWAG, PSYCHIC, RATTATA, ROCKET_DRATINI, ROCKET_EKANS, ROCKET_KOFFING,
    ROCKET_MACHOP, ROCKET_ODDISH, ROCKET_VOLTORB, ROCKET_ZUBAT, T, V0_29_POKEMON, VOLTORB, WATER, build_test_state, coin_events,
    with_coin_results,
)

PRINTED = cs.PRINTED_TEXT_SOURCE
# (カード id, ワザの位置) → (名前, 実装, 出典)。出典が None のワザは説明文がない（DamageOnly）。説明文のあるワザの出典は kyuura の印刷の文面
EXPECTED = {
    (POLIWAG, 0): ("みずでっぽう", E.ExtraEnergyDamage(energy_type=EnergyType.WATER, per_energy=10, max_extra=2), PRINTED),
    (ROCKET_EKANS, 0): ("かみつく", E.DAMAGE_ONLY, None),
    (ROCKET_EKANS, 1): ("どくばり", E.PoisonOnHeads(), PRINTED),
    (ROCKET_ZUBAT, 0): ("ぶつかる", E.DAMAGE_ONLY, None),
    (ROCKET_ZUBAT, 1): ("かみつく", E.DAMAGE_ONLY, None),
    (ROCKET_ODDISH, 0): ("ねむりごな", E.PutToSleep(), PRINTED),
    (ROCKET_ODDISH, 1): ("どくのこな", E.PoisonWithoutDamage(), PRINTED),
    (ROCKET_KOFFING, 0): ("たいあたり", E.DAMAGE_ONLY, None),
    (ROCKET_KOFFING, 1): ("どくガス", E.PoisonOnHeads(), PRINTED),
    (ROCKET_VOLTORB, 0): ("スピードボール", E.DAMAGE_ONLY, None),
    (ROCKET_MACHOP, 0): ("パンチ", E.DAMAGE_ONLY, None),
    (ROCKET_MACHOP, 1): ("キック", E.DAMAGE_ONLY, None),
    (ROCKET_DRATINI, 0): ("まきつく", E.ParalyzeOnHeads(), PRINTED),
    (BROCKS_ZUBAT, 0): ("つばさでうつ", E.DAMAGE_ONLY, None),
    (BROCKS_ZUBAT, 1): ("どくのきば", E.PoisonOnHeads(), PRINTED),
    (MISTYS_GOLDEEN, 0): ("みだれづき", E.CoinFlipDamage(coins=2, damage_per_heads=10), PRINTED),
    (MISTYS_GOLDEEN, 1): ("ちょうおんぱ", E.ConfuseOnHeadsWithoutDamage(), PRINTED),
    (LT_SURGES_MAGNEMITE, 0): ("でんきショック", E.ParalyzeOnHeads(), PRINTED),
    (LT_SURGES_MAGNEMITE, 1): ("たいあたり", E.DAMAGE_ONLY, None),
    (LT_SURGES_VOLTORB, 0): ("スピンボール", E.CoinFlipDamage(coins=1, damage_per_heads=20), PRINTED),
    (LT_SURGES_VOLTORB, 1): ("ダブルスピン", E.CoinFlipDamage(coins=2, damage_per_heads=20), PRINTED),
    (BROCKS_GEODUDE, 0): ("いしなげ", E.CoinFlipDamage(coins=3, damage_per_heads=10), PRINTED),
    (BROCKS_LICKITUNG, 0): ("ベロではたく", E.DAMAGE_ONLY, None),
    (BROCKS_LICKITUNG, 1): ("たたきつける", E.CoinFlipDamage(coins=2, damage_per_heads=30), PRINTED),
}
# pcg-search.com の照合した版（収録・一覧の番号）。kyuura のカード id とサイトの番号は別の番号
EDITIONS = {
    POLIWAG: ("第1弾 拡張パック", "026/096"),
    ROCKET_EKANS: ("第4弾 拡張パック「ロケット団」", "001/065"),
    ROCKET_ZUBAT: ("第4弾 拡張パック「ロケット団」", "003/065"),
    ROCKET_ODDISH: ("第4弾 拡張パック「ロケット団」", "005/065"),
    ROCKET_KOFFING: ("第4弾 拡張パック「ロケット団」", "010/065"),
    ROCKET_VOLTORB: ("第4弾 拡張パック「ロケット団」", "028/065"),
    ROCKET_MACHOP: ("第4弾 拡張パック「ロケット団」", "042/065"),
    ROCKET_DRATINI: ("第4弾 拡張パック「ロケット団」", "051/065"),
    BROCKS_ZUBAT: ("ジム拡張第1弾「リーダーズスタジアム」", "002/096"),
    MISTYS_GOLDEEN: ("ジム拡張第1弾「リーダーズスタジアム」", "032/096"),
    LT_SURGES_MAGNEMITE: ("ジム拡張第1弾「リーダーズスタジアム」", "038/096"),  # 037/096 は同じ名前の別のカード（HP30・はかいでんぱ）
    LT_SURGES_VOLTORB: ("ジム拡張第1弾「リーダーズスタジアム」", "040/096"),
    BROCKS_GEODUDE: ("ジム拡張第1弾「リーダーズスタジアム」", "050/096"),  # 049/096 は同じ名前の別のカード（HP40・たすけをよぶ）
    BROCKS_LICKITUNG: ("ジム拡張第1弾「リーダーズスタジアム」", "056/096"),
}
# 各ワザに必要なエネルギー（コストの「無色」は、ほかの種類で払う）
ENERGY = {
    (POLIWAG, 0): [WATER], (ROCKET_EKANS, 0): [GRASS], (ROCKET_EKANS, 1): [GRASS, GRASS], (ROCKET_ZUBAT, 0): [GRASS],
    (ROCKET_ZUBAT, 1): [GRASS, GRASS], (ROCKET_ODDISH, 0): [GRASS], (ROCKET_ODDISH, 1): [GRASS], (ROCKET_KOFFING, 0): [GRASS],
    (ROCKET_KOFFING, 1): [GRASS, GRASS], (ROCKET_VOLTORB, 0): [LIGHTNING], (ROCKET_MACHOP, 0): [FIGHTING] * 2,
    (ROCKET_MACHOP, 1): [FIGHTING] * 3, (ROCKET_DRATINI, 0): [WATER] * 2, (BROCKS_ZUBAT, 0): [GRASS], (BROCKS_ZUBAT, 1): [GRASS, GRASS],
    (MISTYS_GOLDEEN, 0): [WATER], (MISTYS_GOLDEEN, 1): [WATER], (LT_SURGES_MAGNEMITE, 0): [LIGHTNING],
    (LT_SURGES_MAGNEMITE, 1): [LIGHTNING] * 2, (LT_SURGES_VOLTORB, 0): [LIGHTNING], (LT_SURGES_VOLTORB, 1): [LIGHTNING] * 2,
    (BROCKS_GEODUDE, 0): [FIGHTING], (BROCKS_LICKITUNG, 0): [WATER] * 2, (BROCKS_LICKITUNG, 1): [WATER] * 3,
}


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
    return [e["condition"] for e in events(state, since, "special_condition")]


def attacker(key, **extra):
    return {"card": key[0], "energy": ENERGY[key], **extra}


class RegistrationTest(unittest.TestCase):
    """登録表・分類・採用の記録（位置・名前・型・パラメーター・出典のずれを見つける）。"""

    def test_every_attack_is_registered_with_the_expected_effect(self):
        """14 枚のすべてのワザが、決めた位置・名前・実装（型とパラメーター）・出典で登録されていて、ほかの位置の登録・特殊能力はない。どれもたねポケモン。"""
        pool = load_card_pool()
        registered = {(k.card_id, k.attack_index) for k in E.DEFAULT_EFFECTS.attack_keys() if k.card_id in V0_29_POKEMON}
        self.assertEqual(registered, set(EXPECTED))
        self.assertEqual(len(EXPECTED), 24)
        for card_id in V0_29_POKEMON:
            definition = pool.get(card_id)
            self.assertTrue(definition.supported and pool.is_playable(card_id), definition.unsupported_reasons)
            self.assertTrue(definition.is_basic_pokemon)
            self.assertEqual(definition.powers, ())
            self.assertFalse(any(k.card_id == card_id for k in E.DEFAULT_EFFECTS.power_keys()))
            self.assertEqual({(card_id, a.index) for a in definition.attacks}, {k for k in EXPECTED if k[0] == card_id})
            for attack in definition.attacks:
                with self.subTest(card=card_id, attack=attack.index):
                    name, effect, source = EXPECTED[(card_id, attack.index)]
                    entry = E.DEFAULT_EFFECTS.attack_entry(card_id, attack.index)
                    self.assertEqual((attack.name_ja, entry.name_ja), (name, name))
                    self.assertIs(type(entry.effect), type(effect))
                    self.assertEqual(entry.effect, effect)  # パラメーター（コインの枚数・1 枚あたりのダメージ・エネルギーの種類と上限）まで同じ
                    self.assertEqual(entry.source, source)
                    # 処理に使う文面は kyuura の印刷の文面そのもの（kyuura に最新の説明・エラッタがない。docs/card-data-policy.md）
                    self.assertEqual(entry.play_text_ja, attack.text_ja)
                    self.assertEqual(entry.text_ja, attack.text_ja)
                    self.assertEqual(entry.play_text_ja is None, source is None)
                    self.assertIsNone(E.DEFAULT_EFFECTS.attack_problem(card_id, attack, definition.attacks))
                    self.assertTrue(attack.supported)

    def test_parameters_follow_the_card_data(self):
        """コインの枚数・「おもて」1 枚あたりのダメージは、写しのダメージの目安（「×」）と説明文の枚数のとおり。追加するエネルギーは「水」で上限 2。"""
        pool = load_card_pool()
        coins_in_text = {"1": 1, "2": 2, "3": 3}
        for key, (_, effect, _) in EXPECTED.items():
            attack = pool.get(key[0]).attacks[key[1]]
            if isinstance(effect, E.CoinFlipDamage):
                with self.subTest(key=key):
                    self.assertEqual((attack.damage_modifier, attack.damage), ("×", effect.damage_per_heads))
                    number = attack.text_ja.split("コインを")[1][0]
                    self.assertEqual(coins_in_text[number], effect.coins)
        poliwag = pool.get(POLIWAG).attacks[0]
        self.assertEqual((poliwag.damage, poliwag.damage_modifier, poliwag.cost), (10, "+", (EnergyType.WATER,)))
        self.assertIn("追加は2つまで", poliwag.text_ja)

    def test_adoption_records(self):
        """写しの組 pool_v0_29 は 14 枚。登録の根拠は kyuura データの採用の記録（card_sources.json）だけで、過去の原典照合の記録
        （card_verification.json）には入れていない。外部照合は pcg-search.com の同じ収録・同じ一覧の番号の版（違いなし）。"""
        self.assertEqual(read_extract()["pool_v0_29"], list(V0_29_POKEMON))
        verification = read_verification()
        sources = cs.load_sources()
        for card_id in V0_29_POKEMON:
            with self.subTest(card=card_id):
                self.assertNotIn(card_id, verification["cards"])
                self.assertEqual(cs.registration_basis(card_id, verification, sources), cs.KYUURA_DATA)
                record = sources["cards"][card_id]
                texts = {f"attack/{k[1]}" for k, v in EXPECTED.items() if k[0] == card_id and v[2] is not None}
                self.assertEqual(record["play_text"], {t: cs.PRINTED_TEXT for t in texts})
                [check] = record["external_checks"]
                self.assertEqual((check["edition"]["expansion"], check["edition"]["list_number"]), EDITIONS[card_id])
                self.assertTrue(check["url"].startswith("https://pcg-search.com/card/1st/"))
                self.assertEqual((check["result"], check["differences"]), ("match", []))
                for field in ("pokemon.hp", "pokemon.types", "pokemon.weaknesses", "pokemon.resistances", "pokemon.retreat_cost"):
                    self.assertIn(field, check["checked_fields"])

    def test_same_name_cards_are_different_ids(self):
        """同じ名前の別のカード（第1弾のワンリキー・ビリリダマ・ミニリュウ）と取り違えていない: ワザが違い、登録も別。"""
        pool = load_card_pool()
        for new, old in ((ROCKET_MACHOP, MACHOP), (ROCKET_VOLTORB, VOLTORB), (ROCKET_DRATINI, DRATINI)):
            with self.subTest(card=pool.get(new).name_ja):
                self.assertEqual(pool.get(new).name_ja, pool.get(old).name_ja)
                self.assertNotEqual([a.name_ja for a in pool.get(new).attacks], [a.name_ja for a in pool.get(old).attacks])

    def test_checks_reject_wrong_types_and_parameters(self):
        """型の確認（check）が、取りちがえた登録を拒否する（v0.29 で check を変えていない）。"""
        pool = load_card_pool()
        attack = {key: pool.get(key[0]).attacks[key[1]] for key in EXPECTED}
        wrong = (
            (E.CoinFlipDamage(coins=1, damage_per_heads=10), attack[(LT_SURGES_VOLTORB, 0)]),  # 1 枚あたり 20 のワザに 10
            (E.CoinFlipDamage(coins=2, damage_per_heads=20), attack[(BROCKS_LICKITUNG, 1)]),  # 1 枚あたり 30 のワザに 20
            (E.CoinFlipDamage(coins=2, damage_per_heads=20), attack[(LT_SURGES_MAGNEMITE, 1)]),  # 「×」のないワザ
            (E.DAMAGE_ONLY, attack[(MISTYS_GOLDEEN, 0)]),  # 「×」のあるワザを効果のないワザに
            (E.DAMAGE_ONLY, attack[(POLIWAG, 0)]),  # 「+」のあるワザを効果のないワザに
            (E.DAMAGE_ONLY, attack[(ROCKET_EKANS, 1)]),  # 説明文のあるワザを効果のないワザに
            (E.ExtraEnergyDamage(energy_type=EnergyType.GRASS, per_energy=10, max_extra=2), attack[(POLIWAG, 0)]),
            (E.PutToSleep(), attack[(ROCKET_EKANS, 1)]),  # ダメージの目安のあるワザに、ダメージのないねむりの型
            (E.PoisonWithoutDamage(), attack[(ROCKET_KOFFING, 1)]),  # ダメージの目安のある「どくガス」に、ダメージのないどくの型
            (E.PoisonOnHeads(), attack[(ROCKET_ODDISH, 1)]),  # ダメージの目安のない「どくのこな」に、ダメージのあるどくの型
            (E.ConfuseOnHeads(), attack[(MISTYS_GOLDEEN, 1)]),  # ダメージの目安のないワザに、ダメージのあるこんらんの型
            (E.ParalyzeOnHeads(), attack[(ROCKET_ODDISH, 0)]),
        )
        for effect, data in wrong:
            with self.subTest(effect=type(effect).__name__, attack=data.name_ja):
                self.assertTrue(effect.check(data))

    def test_programs_keep_damage_and_no_damage_statuses_apart(self):
        """ダメージのある特殊状態のワザ（Damage → Status）と、ダメージのないワザ（Status だけ）の要素の並び。コインのダメージは要素 1 つ。"""
        def program(key):
            return programs.compile_attack(E.DEFAULT_EFFECTS.attack_entry(*key).effect)

        with_damage = ((ROCKET_EKANS, 1), (ROCKET_KOFFING, 1), (BROCKS_ZUBAT, 1), (ROCKET_DRATINI, 0), (LT_SURGES_MAGNEMITE, 0))
        without_damage = ((ROCKET_ODDISH, 0), (ROCKET_ODDISH, 1), (MISTYS_GOLDEEN, 1))
        for key in with_damage:
            self.assertEqual([type(e) for e in program(key)], [programs.Damage, programs.Status], key)
            self.assertEqual(program(key)[1].local_coin, H)
        for key in without_damage:
            self.assertEqual([type(e) for e in program(key)], [programs.Status], key)
        self.assertEqual(program((MISTYS_GOLDEEN, 1))[0].local_coin, H)
        self.assertIsNone(program((ROCKET_ODDISH, 0))[0].local_coin)
        self.assertIsNone(program((ROCKET_ODDISH, 1))[0].local_coin)
        self.assertEqual(program((POLIWAG, 0)), (programs.Damage(programs.OPP, programs.ExtraEnergy(EnergyType.WATER, 10, 2)),))
        for key in ((MISTYS_GOLDEEN, 0), (LT_SURGES_VOLTORB, 0), (LT_SURGES_VOLTORB, 1), (BROCKS_GEODUDE, 0), (BROCKS_LICKITUNG, 1)):
            self.assertEqual([type(e) for e in program(key)], [programs.Damage], key)


class CoinDamageTest(unittest.TestCase):
    """コインのダメージ（p.320 の「×」）: コインを決めた枚数だけ投げ、「おもて」の数 × 1 枚あたりのダメージが p.321 の 1 段階。"""

    def test_every_number_of_heads(self):
        for key, (_, effect, _) in EXPECTED.items():
            if not isinstance(effect, E.CoinFlipDamage):
                continue
            for heads in range(effect.coins + 1):
                results = [H] * heads + [T] * (effect.coins - heads)
                with self.subTest(key=key, heads=heads):
                    state = board(attacker(key), RATTATA)
                    new = apply_command(with_coin_results(state, *results), UseAttack(0, key[1]))
                    since = len(state.log)
                    self.assertEqual(len(attack_coins(new, since)), effect.coins)
                    (damage,) = events(new, since, "damage")
                    self.assertEqual(damage["steps"][0], ("1 基本となる計算", heads * effect.damage_per_heads))

    def test_prevented_defender_is_unresolved(self):
        """「ダメージを受けない」状態（かたまる）の相手には、コインがダメージの量だけを決めるので、コインの前に止める（既存の問い・既存の停止コード
        UNRESOLVED_PREVENTED_COIN_DAMAGE。v0.4b。新しいコードはない）。"""
        for key in ((MISTYS_GOLDEEN, 0), (LT_SURGES_VOLTORB, 0), (BROCKS_GEODUDE, 0), (BROCKS_LICKITUNG, 1)):
            with self.subTest(key=key):
                state = board(attacker(key), {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": 6})
                before = snapshot(state)
                with self.assertRaises(UnsupportedError) as ctx:
                    apply_command(state, UseAttack(0, key[1]))
                self.assertEqual(ctx.exception.code, "UNRESOLVED_PREVENTED_COIN_DAMAGE")
                self.assertEqual(snapshot(state), before)


class FixedDamageTest(unittest.TestCase):
    """説明文のないワザ: ダメージの目安の数字が p.321 の 1 段階（基本となるダメージ）。コインは投げない。"""

    def test_base_damage_is_the_printed_number(self):
        pool = load_card_pool()
        for key, (_, effect, _) in EXPECTED.items():
            if effect is not E.DAMAGE_ONLY:
                continue
            with self.subTest(key=key):
                state = board(attacker(key), RATTATA)
                new = apply_command(state, UseAttack(0, key[1]))
                since = len(state.log)
                (damage,) = events(new, since, "damage")
                self.assertEqual(damage["steps"][0], ("1 基本となる計算", pool.get(key[0]).attacks[key[1]].damage))
                self.assertEqual(coin_events(new, since), [])


class PoliwagTest(unittest.TestCase):
    """ニョロモのみずでっぽう（水。10+）: 必要なエネルギー（水 1）より多い「水」エネルギー 1 個につき 10 を、2 個ぶんまで基本となるダメージに加える
    （カメックス・ラプラスと同じ ExtraEnergyDamage。印刷の文面と型の対応は card_sources.json の notes）。"""

    def test_extra_water_and_cap(self):
        for energy, base in (([WATER], 10), ([WATER, WATER], 20), ([WATER] * 3, 30), ([WATER] * 4, 30),
                             ([WATER, FIRE, PSYCHIC], 10), ([WATER, WATER, GRASS], 20)):
            with self.subTest(energy=energy):
                state = board({"card": POLIWAG, "energy": energy}, RATTATA)
                new = apply_command(state, UseAttack(0, 0))
                (damage,) = events(new, len(state.log), "damage")
                self.assertEqual(damage["steps"][0], ("1 基本となる計算", base))

    def test_needs_water(self):
        """必要なエネルギーは「水」1 個（p.309 の手順 2）。ほかの種類だけでは使えない。"""
        state = board({"card": POLIWAG, "energy": [FIRE, FIRE]}, RATTATA)
        before = snapshot(state)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, "INSUFFICIENT_ENERGY")
        self.assertEqual(snapshot(state), before)


class StatusAttackTest(unittest.TestCase):
    """特殊状態のワザ: ダメージのあるワザはダメージのログ → ワザのコイン → 特殊状態、ダメージのないワザはダメージのログがない（p.320）。
    ねむりごな・どくのこなにはコインがない。"""

    CASES = (
        # (ワザ, 相手（ワンリキー。HP 50・弱点 超）へのダメージ, ワザのコインの数, 特殊状態)
        ((ROCKET_EKANS, 1), 20, 1, "poison"),
        ((ROCKET_KOFFING, 1), 20, 1, "poison"),
        ((BROCKS_ZUBAT, 1), 20, 1, "poison"),
        ((ROCKET_DRATINI, 0), 10, 1, "paralysis"),
        ((LT_SURGES_MAGNEMITE, 0), 10, 1, "paralysis"),
        ((ROCKET_ODDISH, 0), None, 0, "sleep"),
        ((ROCKET_ODDISH, 1), None, 0, "poison"),
        ((MISTYS_GOLDEEN, 1), None, 1, "confusion"),
    )

    def test_damage_coin_and_condition(self):
        for key, damage, coins, condition in self.CASES:
            with self.subTest(key=key):
                state = board(attacker(key), MACHOP)
                new = apply_command(with_coin_results(state, H, T), UseAttack(0, key[1]))  # 2 枚目はポケモンチェックのねむりのコイン
                since = len(state.log)
                self.assertEqual([e["amount"] for e in events(new, since, "damage")], [] if damage is None else [damage])
                self.assertEqual(len(attack_coins(new, since)), coins)
                self.assertEqual(conditions_given(new, since), [condition])
                kinds = [e["kind"] for e in new.log[since:]]
                if damage is not None:  # ダメージ → ワザのコイン → 特殊状態（p.320 の順番）
                    self.assertLess(kinds.index("damage"), kinds.index("coin_flip"))
                    self.assertLess(kinds.index("coin_flip"), kinds.index("special_condition"))

    def test_tails_gives_no_condition(self):
        for key, damage, coins, _ in self.CASES:
            if not coins:
                continue
            with self.subTest(key=key):
                state = board(attacker(key), MACHOP)
                new = apply_command(with_coin_results(state, T), UseAttack(0, key[1]))
                self.assertEqual(conditions_given(new, len(state.log)), [])


class RetreatAndEvolutionTest(unittest.TestCase):
    """にげるエネルギーが 0 のズバット・タケシのズバット（p.311）と、名前で決まる進化（p.310）。v0.29 でにげる・進化の処理は変えていない。"""

    def test_zero_retreat_cost(self):
        for card_id in (ROCKET_ZUBAT, BROCKS_ZUBAT):
            with self.subTest(card=card_id):
                state = build_test_state([{"active": card_id, "bench": [RATTATA]}, {"active": RATTATA}], turn_number=3)
                bench = state.players[0].bench[0]
                new = apply_command(state, Retreat(0, (), bench.card))
                self.assertEqual(new.cards[new.players[0].active.card].card_id, RATTATA)
                self.assertEqual(new.players[0].discard, state.players[0].discard)

    def test_rocket_machop_evolves_into_machoke_by_name(self):
        """第1弾のゴーリキー（「ワンリキーから進化」）は、ロケット団のワンリキーにも重ねられる（進化の条件はカードの名前。p.310）。"""
        state = build_test_state([{"active": ROCKET_MACHOP, "hand": [MACHOKE]}, {"active": RATTATA}], turn_number=3)
        new = apply_command(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].active.pokemon_id))
        self.assertEqual(new.cards[new.players[0].active.card].card_id, MACHOKE)


class KnownUnresolvedTest(unittest.TestCase):
    """既知の未解決の境界は、既存の型と同じ問い・同じ停止コードで止まる（新しい問い・コードはない）。"""

    def test_transparency_stops_damage_then_coin_statuses(self):
        """「とうめい」のゴーストに、ダメージ → ワザのコイン → 特殊状態 のワザは T19b（UNRESOLVED_EVADED_EFFECT_COIN）で宣言の前に止まる（v0.9）。
        ダメージのないちょうおんぱは止まらない（ねこノミ・シェルダーのちょうおんぱと同じ。T19・T22）。"""
        haunter = {"card": HAUNTER, "evolved_from": GASTLY}
        for key in ((ROCKET_EKANS, 1), (ROCKET_KOFFING, 1), (BROCKS_ZUBAT, 1), (ROCKET_DRATINI, 0), (LT_SURGES_MAGNEMITE, 0)):
            with self.subTest(key=key):
                state = board(attacker(key), haunter)
                before = snapshot(state)
                with self.assertRaises(UnsupportedError) as ctx:
                    apply_command(state, UseAttack(0, key[1]))
                self.assertEqual(ctx.exception.code, "UNRESOLVED_EVADED_EFFECT_COIN")
                self.assertEqual(snapshot(state), before)
        state = board(attacker((MISTYS_GOLDEEN, 1)), haunter)
        new = apply_command(with_coin_results(state, H, T), UseAttack(0, 1))  # ワザのコイン「おもて」→「とうめい」のコイン「うら」
        self.assertEqual(conditions_given(new, len(state.log)), ["confusion"])


if __name__ == "__main__":
    unittest.main()

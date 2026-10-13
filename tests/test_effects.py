"""効果の登録表（v0.2a、M5）。

ワザを使えるのは、効果の登録表に（カード id, ワザの位置）で実装が登録されているときだけ。
説明文が空であることは実装がある証拠にならない。説明文があっても、実装が登録されていれば使える。
"""

import copy
import pickle
import unittest

from kyuura_engine import (
    DeckValidationError, UnsupportedError, UseAttack, apply_command, deck_problems, expand_decklist, load_card_pool,
    new_game, state_to_dict,
)
from kyuura_engine.cards import pool_from_extract, read_extract
from kyuura_engine.effects import DAMAGE_ONLY, DEFAULT_EFFECTS, AttackEffect, AttackEntry, AttackKey, PowerKey

from tests.helpers import (
    CHARMANDER, DIGLETT, FIGHTING, FIRE, FIRE_DECK, GROWLITHE, MACHOP, PONYTA, VENUSAUR, WATER_FIGHTING_DECK, active,
    build_test_state,
)


class RecordingEffect(AttackEffect):
    """テスト専用の実装: ダメージを与えず、呼ばれたことをログに残すだけ（製品のコードには登録しない）。"""

    implementation_id = "test_recording"

    def resolve(self, state, use):
        state.add_event("test_effect", player=use.player, pokemon_id=use.pokemon_id, key=str(use.key))


RECORDING = RecordingEffect()


def extract_with_other_diglett():
    """ディグダの記録を、別のカード id の別のカードとして加えた写し（同じ名前のワザを持つ別のカード）。"""
    extract = copy.deepcopy(read_extract())
    other = copy.deepcopy(next(c for c in extract["cards"] if c["id"] == DIGLETT))
    other["id"] = "TEST-OTHER-DIGLETT"
    extract["cards"].append(other)
    extract["pool_v0_1"].append(other["id"])
    return extract


class DefaultRegistryTest(unittest.TestCase):
    def test_every_v0_1_attack_is_registered_explicitly_as_damage_only(self):
        # v0.2d でコインを投げるワザのドードー（pool_v0_2d）が対戦に使えるようになったので、v0.1 の組で確かめる
        # （ドードーは tests/test_coin_attacks.py）
        pool = load_card_pool()
        for card_id in sorted(set(pool.playable_ids) & set(read_extract()["pool_v0_1"])):
            for attack in pool.get(card_id).attacks:
                entry = DEFAULT_EFFECTS.attack_entry(card_id, attack.index)
                self.assertIsNotNone(entry, (card_id, attack.index))
                self.assertIs(entry.effect, DAMAGE_ONLY)
                self.assertEqual(entry.name_ja, attack.name_ja)
                self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card_id, attack))

    def test_every_registered_key_matches_the_card_data(self):
        """登録表のどの登録も、写しのカードのワザを指していて、データと合う（位置のずれがない）。"""
        pool = load_card_pool()
        for key in DEFAULT_EFFECTS.attack_keys():
            attack = pool.get(key.card_id).attacks[key.attack_index]
            self.assertIsNone(DEFAULT_EFFECTS.attack_problem(key.card_id, attack), key)

    def test_every_registration_is_backed_by_a_verification_record(self):
        """登録したワザのカードは、『オフィシャルブック2000』と照合した記録がある（照合してから登録する）。"""
        from kyuura_engine.cards import read_verification

        records = read_verification()["cards"]
        for key in DEFAULT_EFFECTS.attack_keys():
            self.assertIn(records.get(key.card_id, {}).get("status"), ("一致", "不一致あり"), key)

    def test_attacks_with_text_follow_the_verified_latest_description(self):
        """説明文のあるワザの登録（v0.2d から）は、照合した説明文・最新の説明・出典を持ち、照合の記録と合う。

        説明文のないワザ（DamageOnly）の登録は、どれも None のまま。
        """
        from kyuura_engine.cards import read_verification

        records = read_verification()["cards"]
        pool = load_card_pool()
        with_text = []
        for key in DEFAULT_EFFECTS.attack_keys():
            entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
            attack = pool.get(key.card_id).attacks[key.attack_index]
            self.assertEqual(entry.text_ja, attack.text_ja, key)
            if attack.text_ja is None:
                self.assertEqual((entry.play_text_ja, entry.source), (None, None), key)
                continue
            with_text.append(key)
            record = records[key.card_id]
            latest = record["latest_description_ja"]
            if isinstance(latest, dict):  # 説明文のあるワザが 2 つあるカード（v0.4b）は、ワザの位置ごと
                latest = latest[str(key.attack_index)]
            self.assertEqual(entry.play_text_ja, latest, key)
            self.assertEqual(entry.source, f"P43 p.{record['page']}", key)
            self.assertEqual(record["pdf_page"], record["page"] + 2)
        # ピカチュウの「でんげき」（p.125。v0.2f）、ドードーの「みだれづき」（p.231。v0.2d）
        # ビードルの「どくばり」（p.19。v0.3a）、キャタピーの「いとをはく」（p.17）・パラスの「キノコのほうし」（p.38。v0.3b）、
        # ロコンの「あやしいひかり」（p.67。v0.3c）、ジュゴンの「れいとうビーム」（p.102）・パラセクトの「キノコのほうし」（p.39。v0.4a）、
        # トランセルの「かたまる」・「しびれごな」（p.18）・コクーンの「かたまる」・「どくのこな」（p.21。v0.4b）、
        # スピアーの「ダブルニードル」・「どくばり」（p.21。v0.4c）、バタフリーの「ふきとばし」・「メガドレイン」（p.19。v0.4d）、
        # フシギダネの「やどりぎのタネ」（p.13）・フシギソウの「どくのこな」（p.14。v0.5）、
        # ゼニガメの「あわ」・「からにこもる」（p.87）・カメールの「からにこもる」（p.88）・カメックスの「ハイドロポンプ」（p.90。v0.6）、
        # ケーシィの「ねんりき」（p.149）・ユンゲラーの「じこさいせい」（p.151）・フーディンの「あやしいひかり」（p.153。v0.7）、
        # ベトベトンの「ヘドロこうげき」（p.48）・ロケット団のベトベターの「どくガス」「ねばりつく」（p.45。v0.8）、
        # 化石の秘密のゴースの「したでなめる」「エナジーへんかん」（p.158）・ゴーストの「あくむ」（p.160。v0.9）
        self.assertEqual(with_text, [AttackKey("PMCG1-001", 0), AttackKey("PMCG1-002", 0), AttackKey("PMCG1-003", 0), AttackKey("PMCG1-003", 1),
                                     AttackKey("PMCG1-004", 0), AttackKey("PMCG1-008", 1), AttackKey("PMCG1-009", 0), AttackKey("PMCG1-009", 1),
                                     AttackKey("PMCG1-012", 0), AttackKey("PMCG1-012", 1), AttackKey("PMCG1-015", 0),
                                     AttackKey("PMCG1-023", 0), AttackKey("PMCG1-023", 1), AttackKey("PMCG1-027", 0),
                                     AttackKey("PMCG1-030", 1), AttackKey("PMCG1-032", 0), AttackKey("PMCG1-035", 1),
                                     AttackKey("PMCG1-043", 0), AttackKey("PMCG1-046", 0), AttackKey("PMCG1-049", 0),
                                     AttackKey("PMCG1-061", 0), AttackKey("PMCG2-003", 1), AttackKey("PMCG2-007", 0), AttackKey("PMCG2-007", 1),
                                     AttackKey("PMCG2-010", 0), AttackKey("PMCG3-007", 0), AttackKey("PMCG3-029", 0),
                                     AttackKey("PMCG3-029", 1), AttackKey("PMCG3-030", 0), AttackKey("PMCG4-004", 0),
                                     AttackKey("PMCG4-004", 1)])

    def test_pool_and_game_use_the_same_registry(self):
        state = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 1)
        self.assertIs(load_card_pool().effects, DEFAULT_EFFECTS)
        self.assertIs(state.effects, DEFAULT_EFFECTS)
        for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(copied.effects.attack_keys(), DEFAULT_EFFECTS.attack_keys())


class UnregisteredTest(unittest.TestCase):
    def test_attack_with_text_is_not_registered(self):
        charmander = load_card_pool().get(CHARMANDER)
        ember = charmander.attacks[1]
        self.assertIn("登録されていない", DEFAULT_EFFECTS.attack_problem(CHARMANDER, ember))
        self.assertFalse(charmander.supported)

    def test_attack_without_text_is_refused_if_not_registered(self):
        """説明文がなくても、登録がなければ使えない（説明文が空なことは実装がある証拠にならない）。"""
        effects = DEFAULT_EFFECTS.without_attacks("test-no-machop", [AttackKey(MACHOP, 0)])
        pool = pool_from_extract(read_extract(), effects)
        machop = pool.get(MACHOP)
        self.assertIsNone(machop.attacks[0].text_ja)
        self.assertFalse(machop.attacks[0].supported)
        self.assertFalse(pool.is_playable(MACHOP))
        deck = expand_decklist({MACHOP: 4, FIGHTING: 56})
        self.assertTrue(any(p.startswith("UNSUPPORTED_CARD") for p in deck_problems(deck, pool)))
        with self.assertRaises(DeckValidationError):
            new_game(deck, FIRE_DECK, 0, pool=pool)
        # 対戦の中でも、その対戦の登録表に登録がなければ使えない
        state = build_test_state([{"active": {"card": MACHOP, "energy": [FIGHTING]}}, {"active": GROWLITHE}], effects=effects)
        before = state_to_dict(state)
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_ATTACK")
        self.assertEqual(state_to_dict(state), before)

    def test_unsupported_card_in_deck_is_rejected(self):
        deck = expand_decklist({CHARMANDER: 1, PONYTA: 4, FIRE: 55})
        self.assertTrue(any("ひのこ" in p and "登録されていない" in p for p in deck_problems(deck)))


class RegisteredWithTextTest(unittest.TestCase):
    def test_attack_with_text_is_supported_when_an_implementation_is_registered(self):
        """説明文があっても、実装が登録されていれば使える。処理は登録した実装が行う（説明文から推測しない）。"""
        # v0.2d から、説明文のあるワザの登録には、照合した説明文（kyuura の写しの値）を書く
        ember_text = load_card_pool().get(CHARMANDER).attacks[1].text_ja
        effects = DEFAULT_EFFECTS.with_attacks(
            "test-ember", {AttackKey(CHARMANDER, 1): AttackEntry(RECORDING, "ひのこ", text_ja=ember_text)})
        pool = pool_from_extract(read_extract(), effects)
        self.assertTrue(pool.get(CHARMANDER).attacks[1].supported)
        self.assertTrue(pool.get(CHARMANDER).supported)
        state = build_test_state([{"active": {"card": CHARMANDER, "energy": [FIRE, FIRE]}}, {"active": GROWLITHE}], effects=effects)
        state = apply_command(state, UseAttack(0, 1))
        self.assertEqual([e["kind"] for e in state.log[-6:-4]], ["attack", "test_effect"])
        self.assertEqual(state.log[-5]["key"], "PMCG1-014#1")
        self.assertEqual(active(state, 1).damage, 0)  # 登録した実装はダメージを与えない（説明文の「30」は使わない）

    def test_attack_with_text_cannot_be_registered_as_damage_only(self):
        """効果のあるワザを、効果のないワザ（DamageOnly）として登録しても使えない（登録の誤りを見つける）。"""
        ember = load_card_pool().get(CHARMANDER).attacks[1]
        effects = DEFAULT_EFFECTS.with_attacks(
            "test-bad", {AttackKey(CHARMANDER, 1): AttackEntry(DAMAGE_ONLY, "ひのこ", text_ja=ember.text_ja)})
        self.assertIn("説明文のあるワザを、効果のないワザとして登録している", effects.attack_problem(CHARMANDER, ember))
        self.assertIsNone(effects.attack_effect(CHARMANDER, ember))

    def test_registered_name_must_match_the_data(self):
        """登録したワザ名がデータと違えば使えない（データの並びが変わったときに気づく）。"""
        effects = DEFAULT_EFFECTS.with_attacks("test-name", {AttackKey(PONYTA, 0): AttackEntry(DAMAGE_ONLY, "けとばす")})
        attack = load_card_pool().get(PONYTA).attacks[0]
        self.assertIn("ワザ名", effects.attack_problem(PONYTA, attack))


class SameNameDifferentCardTest(unittest.TestCase):
    """同じ名前のワザでも、カードが違えば別の登録（ワザ名は識別子ではない）。"""

    def test_registration_is_by_card_and_position(self):
        extract = extract_with_other_diglett()
        pool = pool_from_extract(extract)
        other = pool.get("TEST-OTHER-DIGLETT")
        self.assertEqual([a.name_ja for a in other.attacks], [a.name_ja for a in pool.get(DIGLETT).attacks])
        self.assertTrue(pool.get(DIGLETT).supported)
        self.assertFalse(other.supported)  # 同じ名前のワザだが、このカードには登録がない

        effects = DEFAULT_EFFECTS.with_attacks("test-other", {
            AttackKey("TEST-OTHER-DIGLETT", 0): AttackEntry(RECORDING, "あなをほる"),
            AttackKey("TEST-OTHER-DIGLETT", 1): AttackEntry(DAMAGE_ONLY, "どろかけ"),
        })
        pool = pool_from_extract(extract, effects)
        original = pool.get(DIGLETT).attacks[0]
        copy_attack = pool.get("TEST-OTHER-DIGLETT").attacks[0]
        self.assertIs(effects.attack_effect(DIGLETT, original), DAMAGE_ONLY)
        self.assertIs(effects.attack_effect("TEST-OTHER-DIGLETT", copy_attack), RECORDING)


class RegistryImmutabilityTest(unittest.TestCase):
    def test_with_and_without_do_not_change_the_original(self):
        keys = DEFAULT_EFFECTS.attack_keys()
        DEFAULT_EFFECTS.with_attacks("x", {AttackKey(CHARMANDER, 1): AttackEntry(RECORDING, "ひのこ")})
        DEFAULT_EFFECTS.without_attacks("y", keys)
        self.assertEqual(DEFAULT_EFFECTS.attack_keys(), keys)
        # v0.1 の 13 + ヒトカゲの「ひっかく」（v0.2a）+ ドードーの「みだれづき」（v0.2d）+ ピカチュウの 2 つ（v0.2f）
        # + ビードルの「どくばり」（v0.3a）+ キャタピーの「いとをはく」・パラスの「ひっかく」「キノコのほうし」（v0.3b）
        # + ロコンの「あやしいひかり」（v0.3c）+ パラセクトの 2 つ・ジュゴンの 2 つ（v0.4a）+ トランセルの 2 つ・コクーンの 2 つ（v0.4b）
        # + スピアーの 2 つ（v0.4c）+ バタフリーの 2 つ（v0.4d）+ フシギダネの 1 つ・フシギソウの 2 つ・フシギバナの 1 つ（v0.5）
        # + ゼニガメの 2 つ・カメールの 2 つ・カメックスの 1 つ（v0.6）+ ケーシィの 1 つ・ユンゲラーの 2 つ・フーディンの 1 つ（v0.7）
        # + ロケット団のベトベターの 2 つ・ベトベトンの 1 つ（v0.8）+ 化石の秘密のゴースの 2 つ・ゴーストの 1 つ（v0.9）
        self.assertEqual(len(keys), 53)
        # ポケモンパワー（v0.5）の登録も同じく変わらない（with_powers・without_powers は新しい登録表を返す）
        powers = DEFAULT_EFFECTS.power_keys()
        DEFAULT_EFFECTS.without_powers("z", powers)
        DEFAULT_EFFECTS.with_powers("w", {PowerKey(CHARMANDER, 0): DEFAULT_EFFECTS.power_entry(VENUSAUR, 0)})
        self.assertEqual(DEFAULT_EFFECTS.power_keys(), powers)
        # フシギバナの「エナジートランス」（v0.5）・カメックスの「あまごい」（v0.6）・フーディンの「ダメージスワップ」（v0.7）
        # v0.8 でベトベトンの「かがくへんかガス」（PMCG3-007）、v0.9 でゴーストの「とうめい」（PMCG3-030）を加えた
        self.assertEqual(powers, (PowerKey(VENUSAUR, 0), PowerKey("PMCG1-032", 0), PowerKey("PMCG1-049", 0), PowerKey("PMCG3-007", 0),
                                  PowerKey("PMCG3-030", 0)))


if __name__ == "__main__":
    unittest.main()

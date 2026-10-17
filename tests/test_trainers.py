"""トレーナーカード（v0.2b）: 登録表・PlayTrainer・マサキ・きずぐすり・ポケモンいれかえ。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES）:

- p.254: 3 枚のカードのページ（図版・「最新の説明」・解説）。p.6: カードの記述は「最新の説明」
- p.309: 番の最初に引く前・ワザの最中はトレーナーを使えない
- p.310「トレーナーカードを使う」: 使う順番、1 番に何枚でも、使いすて（トラッシュ）、使っている最中はほかのことができない
- p.311・p.312: 番の最初に引けなければ負け。効果で引くときは山札が足りなくても負けにならず、引けるだけ引く
- p.312: 「カードを引く」は自分の山札の一番上から。「場」はバトル場とベンチ
- p.319・p.320: ダメージカウンター 1 個は 10 ダメージ。すべてとりのぞいたら、それ以上は回復しない
- p.311・p.325: にげるは 1 番に何度でも。にげるは「ポケモンの入れ替え」の一つ。移動するポケモンのカード・カウンターはいっしょに移動する

原典で決められない場合は、成功を仮定せず、UnsupportedError で止まること（状態を変えないこと）を確かめる。
盤面を直接作る build_test_state は 1 か所の規定を確かめるテストだけに使う。正式な対戦開始からの
テストは test_trainer_games.py。
"""

import copy
import json
import pickle
import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, IllegalActionError, Phase, PlayBasicToBench, PlayTrainer, ResolveDecision, Retreat,
    UnsupportedError, UseAttack, apply_command, check_invariants, load_card_pool, state_to_dict,
)
from kyuura_engine.cards import classify_record, pool_from_extract, read_extract, read_verification
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackEntry, AttackKey, DAMAGE_ONLY, TrainerEffect, TrainerEntry
from kyuura_engine.rng import rng_fingerprint, rng_from_json, rng_state_to_json
from kyuura_engine.state import TrainerInUse

from tests.helpers import (
    BILL, CLEFAIRY_DOLL, GIOVANNI, RECALL, DEVOLUTION_SPRAY, REVIVE, POKEMON_FLUTE, COMPUTER_SEARCH, MYSTERIOUS_FOSSIL, DEFENDER, ENERGY_RETRIEVAL, FIRE, POKEMON_BREEDER, POKEMON_TRADER, GROWLITHE, GUST, MACHOP, PLUSPOWER, PONYTA, POTION, PROFESSOR_OAK, RATTATA, SEEL, STARYU, SUPER_POTION, SWITCH, WATER, active,
    build_test_state,
)


def full(state):
    """トレーナーの使用中も表せる状態の辞書（形式 3）。"""
    return state_to_dict(state, format_version=3)


def hand_uid(state, player, card_id):
    return next(u for u in state.players[player].hand if state.cards[u].card_id == card_id)


def ids(pokemons):
    return [pokemon.pokemon_id for pokemon in pokemons]


class RejectsMixin:
    def assert_rejected(self, state, command, code, error=IllegalActionError):
        before = full(state)
        with self.assertRaises(error) as ctx:
            apply_command(state, command)
        self.assertEqual(ctx.exception.code, code, command)
        self.assertEqual(full(state), before)  # 拒否しても状態は変わらない
        return ctx.exception


# ---------------------------------------------------------------- 登録表


class TrainerRegistryTest(unittest.TestCase):
    """トレーナーの実装はカード id で登録する。名前・説明文の有無では決めない。"""

    def test_default_registry_has_exactly_the_registered_cards(self):
        # v0.2c でプラスパワーを加え、登録表の id を変えた（v0.2b の 3 枚は同じ実装のまま）。
        # v0.2d はワザ（ドードーの「みだれづき」）を加えたので id が変わった。v0.2e でディフェンダーを加えた。
        # トレーナーの登録は v0.2e から v0.18 まで同じ。v0.19 でオーキドはかせ、v0.21 で突風、v0.22 でパソコン通信、v0.23 でエネルギー回収、v0.24 でポケモン交換おじさん、v0.25 でポケモン育て屋さん、v0.44 でサカキ、v0.47 でピッピ人形・なにかの化石、v0.49 で思い出させる、v0.50 で退化スプレー、v0.51 で元気のかけら・ポケモンの笛を加えた（登録表の id は
        # v0.17・v0.18 と同じく変えていない）
        self.assertEqual(DEFAULT_EFFECTS.trainer_ids(),
                         (POTION, GUST, SWITCH, BILL, ENERGY_RETRIEVAL, PROFESSOR_OAK, REVIVE, DEFENDER, PLUSPOWER, POKEMON_FLUTE, DEVOLUTION_SPRAY, COMPUTER_SEARCH, CLEFAIRY_DOLL,
                          POKEMON_TRADER, POKEMON_BREEDER, MYSTERIOUS_FOSSIL, RECALL, GIOVANNI))
        # v0.2f・v0.3a・v0.3b・v0.3c・v0.4a・v0.4b・v0.4c・v0.4d はワザ（ピカチュウ・ビードル・キャタピーとパラス・ロコン・
        # パラセクトとジュゴン・トランセルとコクーン・スピアー・バタフリー）を加えた。v0.5 はワザとポケモンパワー（フシギダネ・
        # フシギソウ・フシギバナ）を加えた。v0.6 はワザとポケモンパワー（ゼニガメ・カメール・カメックス）を加えた。v0.7 はワザと
        # ポケモンパワー（ケーシィ・ユンゲラー・フーディン）を加えた。v0.8 はワザとポケモンパワー（ロケット団のベトベター・ベトベトン）を加えた。
        # v0.9 はワザとポケモンパワー（化石の秘密のゴース・ゴースト）を加えた。v0.10 はワザとポケモンパワー（ゴーリキー・カイリキー）を加えた
        # v0.11 はワザとポケモンパワー（サカキのワンリキー・ゴーリキー・カイリキー）、v0.12 はワザとポケモンパワー（R団のファイヤー）を加えた
        # v0.13 はワザ（第4弾のゼニガメ・わるいカメール）を加えた
        self.assertEqual(DEFAULT_EFFECTS.id, "kyuura-engine-0.13")
        implementations = {DEFAULT_EFFECTS.trainer_entry(c).effect.implementation_id for c in DEFAULT_EFFECTS.trainer_ids()}
        self.assertEqual(implementations, {"draw_cards", "remove_damage_counters", "switch_with_bench", "attached_attack_bonus",
                                           "attached_damage_reduction", "discard_hand_and_draw", "switch_opponent_with_bench",
                                           "discard_from_hand_then_search_deck", "discard_from_hand_then_retrieve_energy",
                                           "trade_pokemon_with_deck", "evolve_basic_to_stage2",
                                           "evolution_permission_for_owner_pokemon",  # v0.44 のサカキ
                                           "play_as_pokemon",  # v0.47 のなにかの化石・ピッピ人形
                                           "recall_pre_evolution_attacks",  # v0.49 の思い出させる
                                           "devolve_own_pokemon",  # v0.50 の退化スプレー
                                           "bench_basic_from_own_discard_with_counters", "bench_basic_from_opponent_discard"})  # v0.51 の元気のかけら・ポケモンの笛

    def test_registered_trainers_are_playable_and_match_the_data(self):
        pool = load_card_pool()
        for card_id in DEFAULT_EFFECTS.trainer_ids():
            definition = pool.get(card_id)
            entry = DEFAULT_EFFECTS.trainer_entry(card_id)
            self.assertEqual(definition.category, "trainer")
            self.assertTrue(definition.supported, card_id)
            self.assertTrue(pool.is_playable(card_id))
            self.assertEqual((entry.name_ja, entry.text_ja), (definition.name_ja, definition.trainer_text_ja))

    def test_every_registration_follows_the_verified_latest_description(self):
        """登録した実装がしたがう文面（play_text_ja）は、照合した「最新の説明」と同じ（v0.2b の 3 枚は p.254）。

        2026-10-15 からの方針（docs/card-data-policy.md）で kyuura データの採用の記録（card_sources.json）によって登録したトレーナーは、
        ガイドブックの照合の記録を求めず、採用の記録の play_text と合うことを scripts/check_card_sources.py が確かめる。登録の根拠の記録は
        どちらか一方だけ。
        """
        from scripts import check_card_sources as card_sources

        verification = read_verification()
        records = verification["cards"]
        sources = card_sources.load_sources()
        for card_id in DEFAULT_EFFECTS.trainer_ids():
            basis = card_sources.registration_basis(card_id, verification, sources)
            self.assertIn(basis, (card_sources.GUIDEBOOK_RECORD, card_sources.KYUURA_DATA), card_id)
            if basis == card_sources.KYUURA_DATA:
                self.assertIn("trainer", sources["cards"][card_id]["play_text"], card_id)
                continue
            record = records[card_id]
            entry = DEFAULT_EFFECTS.trainer_entry(card_id)
            self.assertIn(record["status"], ("一致", "不一致あり"))
            self.assertEqual(record["pdf_page"], record["page"] + 2)
            self.assertEqual(entry.play_text_ja, record["latest_description_ja"], card_id)
            # 出典のページは照合したページ（v0.2b の 3 枚は p.254、v0.2c のプラスパワーは p.257）
            self.assertEqual(entry.source, f"P43 p.{record['page']}")
        self.assertEqual(records[POTION]["page"], 254)
        self.assertEqual(records[PLUSPOWER]["page"], 257)
        # きずぐすりは kyuura の写し（第1弾の印刷の転記）と最新の説明が違う。処理は最新の説明（1匹・2個）
        self.assertNotEqual(DEFAULT_EFFECTS.trainer_entry(POTION).text_ja, DEFAULT_EFFECTS.trainer_entry(POTION).play_text_ja)

    def test_unregistered_trainer_is_unsupported(self):
        definition = load_card_pool().get(SUPER_POTION)
        self.assertEqual(definition.category, "trainer")
        self.assertFalse(definition.supported)
        self.assertIn("登録されていない", definition.unsupported_reasons[0])
        self.assertIsNone(DEFAULT_EFFECTS.trainer_effect(definition))

    def test_registration_is_by_card_id_not_name(self):
        """同じ名前・同じ文面でも、カード id が違えば登録はない（ジムシリーズなどの再録は別のカード）。"""
        record = copy.deepcopy(next(c for c in read_extract()["cards"] if c["id"] == POTION))
        record["id"] = "TEST-OTHER-POTION"
        definition = classify_record(record)
        self.assertEqual(definition.name_ja, "きずぐすり")
        self.assertFalse(definition.supported)

    def test_changed_data_text_disables_the_registration(self):
        """データの文面が登録したときに照合したものと違えば使えない（参照コミットを上げたときに気づく）。"""
        record = copy.deepcopy(next(c for c in read_extract()["cards"] if c["id"] == BILL))
        record["trainer"]["text"]["ja"] = "山札からカードを3枚引いて、手札に加える。"
        definition = classify_record(record)
        self.assertFalse(definition.supported)
        self.assertIn("文面", definition.unsupported_reasons[0])

    def test_text_presence_is_not_evidence(self):
        """説明文があってもなくても、登録がなければ使えない。"""
        record = copy.deepcopy(next(c for c in read_extract()["cards"] if c["id"] == BILL))
        record["id"] = "TEST-NO-TEXT"
        record["trainer"]["text"] = {"ja": None, "en": None}
        self.assertFalse(classify_record(record).supported)

    def test_with_and_without_keep_the_other_kind_and_the_original(self):
        attacks = DEFAULT_EFFECTS.attack_keys()
        trainers = DEFAULT_EFFECTS.trainer_ids()
        added = DEFAULT_EFFECTS.with_attacks("x", {AttackKey("PMCG1-014", 1): AttackEntry(DAMAGE_ONLY, "ひのこ")})
        self.assertEqual(added.trainer_ids(), trainers)  # ワザを加えてもトレーナーの登録は残る
        removed = DEFAULT_EFFECTS.without_trainers("y", [POTION])
        # PLUSPOWER は v0.2c、DEFENDER は v0.2e、PROFESSOR_OAK は v0.19、GUST は v0.21、COMPUTER_SEARCH は v0.22、ENERGY_RETRIEVAL は v0.23、POKEMON_TRADER は v0.24、POKEMON_BREEDER は v0.25、GIOVANNI は v0.44、CLEFAIRY_DOLL・MYSTERIOUS_FOSSIL は v0.47、RECALL は v0.49
        self.assertEqual(removed.trainer_ids(),
                         (GUST, SWITCH, BILL, ENERGY_RETRIEVAL, PROFESSOR_OAK, REVIVE, DEFENDER, PLUSPOWER, POKEMON_FLUTE, DEVOLUTION_SPRAY, COMPUTER_SEARCH, CLEFAIRY_DOLL, POKEMON_TRADER,
                          POKEMON_BREEDER, MYSTERIOUS_FOSSIL, RECALL, GIOVANNI))
        self.assertEqual(removed.attack_keys(), attacks)
        self.assertEqual(DEFAULT_EFFECTS.trainer_ids(), trainers)  # 元は変わらない
        self.assertEqual(DEFAULT_EFFECTS.attack_keys(), attacks)

    def test_registry_is_per_game_and_test_effects_stay_out_of_the_default(self):
        """テスト用の実装は、テスト用の登録表（その対戦の state.effects）にだけ入る。"""

        class Nothing(TrainerEffect):
            implementation_id = "test_nothing"

            def resolve(self, state, use):
                state.add_event("test_nothing", card=use.card)

        effects = DEFAULT_EFFECTS.with_trainers("test-super-potion", {
            SUPER_POTION: TrainerEntry(Nothing(), "いいきずぐすり", load_card_pool().get(SUPER_POTION).trainer_text_ja, "テスト", "テスト"),
        })
        pool = pool_from_extract(read_extract(), effects)
        self.assertTrue(pool.get(SUPER_POTION).supported)
        self.assertIsNone(DEFAULT_EFFECTS.trainer_entry(SUPER_POTION))
        self.assertFalse(load_card_pool().get(SUPER_POTION).supported)
        state = build_test_state([{"active": GROWLITHE, "hand": [SUPER_POTION]}, {"active": STARYU}], effects=effects)
        card = state.players[0].hand[0]
        new = apply_command(state, PlayTrainer(0, card))
        self.assertEqual([e["kind"] for e in new.log[-3:]], ["play_trainer", "test_nothing", "discard_trainer"])
        # 同じ盤面でも、既定の登録表の対戦では使えない
        default_state = build_test_state([{"active": GROWLITHE, "hand": [SUPER_POTION]}, {"active": STARYU}])
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(default_state, PlayTrainer(0, default_state.players[0].hand[0]))
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_TRAINER")


# ---------------------------------------------------------------- PlayTrainer


class PlayTrainerTest(RejectsMixin, unittest.TestCase):
    """PlayTrainer の検査（p.309・p.310）。"""

    def setUp(self):
        self.state = build_test_state([
            {"active": {"card": GROWLITHE, "damage": 20}, "bench": [PONYTA], "hand": [BILL, POTION, SWITCH, FIRE, SUPER_POTION]},
            {"active": STARYU, "hand": [BILL]},
        ])
        self.bill, self.potion, self.switch, self.fire, self.super_potion = self.state.players[0].hand
        self.their_bill = self.state.players[1].hand[0]

    def test_normal_use_moves_the_card_to_the_discard(self):
        new = apply_command(self.state, PlayTrainer(0, self.bill))
        self.assertEqual(new.phase, Phase.MAIN)
        self.assertNotIn(self.bill, new.players[0].hand)
        self.assertEqual(new.players[0].discard, [self.bill])
        self.assertIsNone(new.trainer_in_use)
        self.assertEqual([e["kind"] for e in new.log[-3:]], ["play_trainer", "draw", "discard_trainer"])
        self.assertEqual(new.log[-3]["trainer"], "マサキ")  # 名前を相手プレイヤーに伝える（p.310 の手順 2）

    def test_not_your_turn(self):
        self.assert_rejected(self.state, PlayTrainer(1, self.their_bill), "NOT_YOUR_TURN")

    def test_opponents_card(self):
        self.assert_rejected(self.state, PlayTrainer(0, self.their_bill), "CARD_NOT_IN_HAND")

    def test_invalid_uid(self):
        self.assert_rejected(self.state, PlayTrainer(0, 9999), "CARD_NOT_IN_HAND")
        self.assert_rejected(self.state, PlayTrainer(0, -1), "CARD_NOT_IN_HAND")
        self.assert_rejected(self.state, PlayTrainer(0, True), "BAD_COMMAND")
        self.assert_rejected(self.state, PlayTrainer(5, self.bill), "INVALID_PLAYER")

    def test_not_a_trainer(self):
        self.assert_rejected(self.state, PlayTrainer(0, self.fire), "NOT_TRAINER")
        self.assert_rejected(self.state, PlayTrainer(0, active(self.state, 0).card), "CARD_NOT_IN_HAND")

    def test_unregistered_trainer(self):
        """実装を登録していないトレーナーは、効果がないものとして使わずに拒否する。"""
        error = self.assert_rejected(self.state, PlayTrainer(0, self.super_potion), "UNSUPPORTED_TRAINER", UnsupportedError)
        self.assertIn("いいきずぐすり", str(error))

    def test_wrong_phase(self):
        state = build_test_state([{"active": GROWLITHE, "hand": [BILL]}, {"active": STARYU}])
        state.phase = Phase.SETUP_FIRST_PLAYER  # 対戦準備の段階（MAIN 以外）では使えない
        self.assert_rejected(state, PlayTrainer(0, state.players[0].hand[0]), "WRONG_PHASE")

    def test_cannot_play_while_a_decision_is_pending(self):
        """トレーナーを使っている最中は、別のトレーナーを使えない（p.310）。"""
        pending = apply_command(self.state, PlayTrainer(0, self.potion))
        self.assertEqual(pending.phase, Phase.DECISION)
        self.assert_rejected(pending, PlayTrainer(0, self.bill), "WRONG_PHASE")
        self.assert_rejected(pending, PlayTrainer(0, self.potion), "WRONG_PHASE")

    def test_used_card_cannot_be_used_again(self):
        new = apply_command(self.state, PlayTrainer(0, self.bill))
        self.assert_rejected(new, PlayTrainer(0, self.bill), "CARD_NOT_IN_HAND")

    def test_many_trainers_in_one_turn(self):
        """トレーナーカードは 1 回の自分の番で何枚でも使える（p.310）。"""
        state = apply_command(self.state, PlayTrainer(0, self.bill))
        state = apply_command(state, PlayTrainer(0, self.potion))
        state = apply_command(state, ResolveDecision(0, state.decision.id, (active(state, 0).pokemon_id,)))
        state = apply_command(state, PlayTrainer(0, self.switch))
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].bench[0].pokemon_id,)))
        self.assertEqual(state.phase, Phase.MAIN)
        self.assertEqual(state.players[0].discard, [self.bill, self.potion, self.switch])
        self.assertEqual(state.current_player, 0)

    def test_finished_game_rejects_trainers(self):
        state = build_test_state([{"active": GROWLITHE, "hand": [BILL]}, {"active": STARYU}])
        from kyuura_engine.state import GameResult

        state.phase = Phase.GAME_OVER
        state.result = GameResult("win", 0, ((0, "ALL_PRIZES_TAKEN"),))
        self.assertEqual(check_invariants(state), [])
        self.assert_rejected(state, PlayTrainer(0, state.players[0].hand[0]), "GAME_OVER")

    def test_halted_game_rejects_trainers(self):
        state = build_test_state([{"active": GROWLITHE, "hand": [BILL]}, {"active": STARYU}])
        from kyuura_engine.state import Halt

        state.phase = Phase.HALTED
        state.halt = Halt("UNRESOLVED_MULLIGAN_COMPENSATION", "テスト", ())
        self.assert_rejected(state, PlayTrainer(0, state.players[0].hand[0]), "UNRESOLVED_MULLIGAN_COMPENSATION", UnsupportedError)


# ---------------------------------------------------------------- マサキ


class BillTest(RejectsMixin, unittest.TestCase):
    """マサキ（PMCG1-074）: 山札からカードを2枚引いて、手札に加える（p.254）。山札が足りないときは p.312。"""

    def bill_state(self, deck, their_deck=None):
        return build_test_state([
            {"active": GROWLITHE, "hand": [BILL], "deck": deck},
            {"active": STARYU, "deck": their_deck if their_deck is not None else [WATER] * 5},
        ])

    def test_draws_the_top_two_cards_of_own_deck_in_order(self):
        state = self.bill_state([PONYTA, RATTATA, FIRE, FIRE])
        top = state.players[0].deck[:2]
        their_deck = list(state.players[1].deck)
        fingerprint = rng_fingerprint(state.rng)
        new = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        self.assertEqual(new.players[0].hand, top)  # 一番上から順に手札の後ろへ
        self.assertEqual(new.players[0].deck, state.players[0].deck[2:])
        self.assertEqual(new.players[1].deck, their_deck)  # 相手の山札からは引かない
        self.assertEqual(rng_fingerprint(new.rng), fingerprint)  # 乱数を使わない
        self.assertEqual(new.log[-2]["cards"], tuple(top))

    def test_deck_of_exactly_two(self):
        state = self.bill_state([PONYTA, RATTATA])
        new = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        self.assertEqual(len(new.players[0].hand), 2)
        self.assertEqual(new.players[0].deck, [])
        self.assertEqual(new.phase, Phase.MAIN)  # 最後の 1 枚を引いて山札がなくなっても負けではない（p.312）
        self.assertIsNone(new.result)

    def test_deck_of_one_draws_one(self):
        """カードが足りないときは、引けるだけ引く。負けにはならない（p.312）。"""
        state = self.bill_state([PONYTA])
        new = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        self.assertEqual(len(new.players[0].hand), 1)
        self.assertEqual(new.players[0].deck, [])
        self.assertEqual(new.phase, Phase.MAIN)

    def test_empty_deck_draws_nothing_and_is_not_a_loss(self):
        """山札にカードがなくても、トレーナーの効果で引くときは負けにならない（p.312）。"""
        state = self.bill_state([])
        bill = state.players[0].hand[0]
        new = apply_command(state, PlayTrainer(0, bill))
        self.assertEqual(new.players[0].hand, [])
        self.assertEqual(new.players[0].discard, [bill])
        self.assertEqual(new.log[-2]["cards"], ())
        self.assertEqual(new.phase, Phase.MAIN)
        self.assertIsNone(new.result)

    def test_deck_out_happens_only_at_the_start_of_the_turn(self):
        """マサキで山札がなくなっても負けではない。次の自分の番の最初に引けなければ負け（p.309, p.312）。"""
        state = self.bill_state([PONYTA, RATTATA])
        state = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        state = apply_command(state, EndTurn(0))
        self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 1))
        state = apply_command(state, EndTurn(1))
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertEqual(state.result.winner, 1)
        self.assertEqual(state.result.conditions, ((1, "OPPONENT_DECK_EMPTY"),))

    def test_cards_are_conserved(self):
        state = self.bill_state([PONYTA, RATTATA, FIRE])
        new = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        before = sorted(state.players[0].deck + state.players[0].hand)
        after = sorted(new.players[0].deck + new.players[0].hand + new.players[0].discard)
        self.assertEqual(before, after)
        self.assertEqual(check_invariants(new), [])


# ---------------------------------------------------------------- きずぐすり


class PotionTest(RejectsMixin, unittest.TestCase):
    """きずぐすり（PMCG1-071）: 最新の説明「あなたの場にいるポケモンを1匹選び、そのポケモンにのっている
    ダメージカウンターを、2個とりのぞく。」（p.254）。2個のっていたら2個とる（p.254 の解説）。"""

    def potion_state(self, active_damage=0, bench=(), their_active_damage=30):
        state = build_test_state([
            {"active": {"card": GROWLITHE, "damage": active_damage, "energy": [FIRE]}, "bench": list(bench), "hand": [POTION]},
            {"active": {"card": STARYU, "damage": their_active_damage}, "bench": [{"card": SEEL, "damage": 20}]},
        ])
        return state, state.players[0].hand[0]

    def heal(self, state, potion, pokemon_id):
        state = apply_command(state, PlayTrainer(0, potion))
        self.assertEqual(state.phase, Phase.DECISION)
        return apply_command(state, ResolveDecision(0, state.decision.id, (pokemon_id,)))

    def test_counter_amounts(self):
        """1個 → 全部、2個 → 全部、3個以上 → 2個（とりのぞく数は選べない）。1個は 10 ダメージ（p.319）。"""
        for damage, expected in ((10, 0), (20, 0), (30, 10), (50, 30)):
            with self.subTest(damage=damage):
                state, potion = self.potion_state(active_damage=damage)
                new = self.heal(state, potion, active(state, 0).pokemon_id)
                self.assertEqual(active(new, 0).damage, expected)
                self.assertEqual(new.log[-2]["counters"], (damage - expected) // 10)
                self.assertEqual(new.phase, Phase.MAIN)

    def test_active_and_bench_can_be_chosen(self):
        """「場」はバトル場とベンチ（p.312）。"""
        state, potion = self.potion_state(active_damage=20, bench=[{"card": PONYTA, "damage": 30}])
        decision = apply_command(state, PlayTrainer(0, potion)).decision
        self.assertEqual(decision.options, (active(state, 0).pokemon_id, state.players[0].bench[0].pokemon_id))
        self.assertEqual(decision.player, 0)
        self.assertEqual(decision.kind, "select_pokemon")
        new = self.heal(state, potion, state.players[0].bench[0].pokemon_id)
        self.assertEqual(new.players[0].bench[0].damage, 10)
        self.assertEqual(active(new, 0).damage, 20)  # 1匹だけ（ほかのポケモンには分けない）

    def test_target_keeps_card_id_energy_and_pokemon_id(self):
        state, potion = self.potion_state(active_damage=30)
        before = active(state, 0)
        new = self.heal(state, potion, before.pokemon_id)
        after = active(new, 0)
        self.assertEqual((after.card, after.pokemon_id, after.energy), (before.card, before.pokemon_id, before.energy))

    def test_opponents_and_unknown_pokemon_are_invalid(self):
        state, potion = self.potion_state(active_damage=30)
        pending = apply_command(state, PlayTrainer(0, potion))
        d = pending.decision
        for wrong in (active(state, 1).pokemon_id, state.players[1].bench[0].pokemon_id, 999, 0, -1):
            self.assert_rejected(pending, ResolveDecision(0, d.id, (wrong,)), "INVALID_CHOICE")
        self.assert_rejected(pending, ResolveDecision(0, d.id, ()), "INVALID_CHOICE_COUNT")
        self.assert_rejected(pending, ResolveDecision(0, d.id, (d.options[0], d.options[0])), "INVALID_CHOICE_COUNT")

    def test_no_damaged_pokemon_is_unresolved(self):
        """自分の場にダメージカウンターののったポケモンがいないときに使えるかは原典で決められない。
        効果がないものとして使わず、UnsupportedError で止める（カードは手札に残る）。"""
        state, potion = self.potion_state(active_damage=0, bench=[PONYTA])
        self.assert_rejected(state, PlayTrainer(0, potion), "UNRESOLVED_POTION_WITHOUT_DAMAGE", UnsupportedError)

    def test_undamaged_target_is_unresolved(self):
        """ダメージのないポケモンを選べるかは原典で決められない。選ぶと UnsupportedError（決定は残る）。"""
        state, potion = self.potion_state(active_damage=0, bench=[{"card": PONYTA, "damage": 10}])
        pending = apply_command(state, PlayTrainer(0, potion))
        d = pending.decision
        self.assertEqual(d.context_value("unresolved_choices"), (active(state, 0).pokemon_id,))
        self.assert_rejected(pending, ResolveDecision(0, d.id, (active(state, 0).pokemon_id,)),
                             "UNRESOLVED_POTION_UNDAMAGED_TARGET", UnsupportedError)
        new = apply_command(pending, ResolveDecision(0, d.id, (state.players[0].bench[0].pokemon_id,)))
        self.assertEqual(new.players[0].bench[0].damage, 0)

    def test_card_is_in_use_during_the_decision_then_discarded(self):
        state, potion = self.potion_state(active_damage=20)
        pending = apply_command(state, PlayTrainer(0, potion))
        self.assertEqual(pending.trainer_in_use, TrainerInUse(0, potion))
        self.assertNotIn(potion, pending.players[0].hand)
        self.assertNotIn(potion, pending.players[0].discard)
        self.assertEqual(check_invariants(pending), [])
        self.assertEqual(full(pending)["trainer_in_use"], {"player": 0, "card": potion, "card_id": POTION})
        with self.assertRaises(ValueError):  # 形式 1・2 では使用中のカードを表せない（黙って落とさない）
            state_to_dict(pending)
        with self.assertRaises(ValueError):
            state_to_dict(pending, format_version=2)
        done = apply_command(pending, ResolveDecision(0, pending.decision.id, (active(state, 0).pokemon_id,)))
        self.assertIsNone(done.trainer_in_use)
        self.assertEqual(done.players[0].discard, [potion])
        self.assertIsNone(full(done)["trainer_in_use"])


# ---------------------------------------------------------------- ポケモンいれかえ


class SwitchTest(RejectsMixin, unittest.TestCase):
    """ポケモンいれかえ（PMCG1-073）: 最新の説明「あなたの控えポケモンを1匹選び、あなたの対戦ポケモンと
    入れ替える。」（p.254）。にげるではない（p.325）。にげるは 1 番に何度でも（p.311）。"""

    def switch_state(self, bench):
        state = build_test_state([
            {"active": {"card": GROWLITHE, "damage": 30, "energy": [FIRE, FIRE]}, "bench": list(bench), "hand": [SWITCH]},
            {"active": STARYU, "bench": [SEEL]},
        ])
        return state, state.players[0].hand[0]

    def switch(self, state, card, pokemon_id):
        state = apply_command(state, PlayTrainer(0, card))
        return apply_command(state, ResolveDecision(0, state.decision.id, (pokemon_id,)))

    def test_no_bench_is_unresolved(self):
        """控えポケモンがいないときに使えるかは原典で決められない（にげるの「控えがいなければ宣言できない」は
        にげるの規定で、トレーナーには書かれていない）。UnsupportedError で止める。"""
        state, card = self.switch_state([])
        self.assert_rejected(state, PlayTrainer(0, card), "UNRESOLVED_SWITCH_WITHOUT_BENCH", UnsupportedError)

    def test_bench_of_one(self):
        state, card = self.switch_state([{"card": PONYTA, "damage": 10, "energy": [FIRE]}])
        old_active, benched = active(state, 0), state.players[0].bench[0]
        pending = apply_command(state, PlayTrainer(0, card))
        self.assertEqual(pending.decision.options, (benched.pokemon_id,))
        new = apply_command(pending, ResolveDecision(0, pending.decision.id, (benched.pokemon_id,)))
        self.assertEqual(active(new, 0).pokemon_id, benched.pokemon_id)
        self.assertEqual(ids(new.players[0].bench), [old_active.pokemon_id])
        self.assertEqual(new.phase, Phase.MAIN)

    def test_bench_of_many_and_everything_moves_with_the_pokemon(self):
        """ついているカード・ダメージカウンターはいっしょに移動する（p.311）。にげるエネルギーは払わない。"""
        state, card = self.switch_state([PONYTA, {"card": RATTATA, "damage": 10, "energy": [FIRE]}, MACHOP])
        old_active = active(state, 0)
        chosen = state.players[0].bench[1]
        new = self.switch(state, card, chosen.pokemon_id)
        new_active = active(new, 0)
        self.assertEqual((new_active.card, new_active.pokemon_id, new_active.energy, new_active.damage),
                         (chosen.card, chosen.pokemon_id, chosen.energy, chosen.damage))
        moved = new.players[0].bench[1]  # 元のバトル場のポケモンは、選んだ控えの場所に入る
        self.assertEqual((moved.card, moved.pokemon_id, moved.energy, moved.damage),
                         (old_active.card, old_active.pokemon_id, old_active.energy, old_active.damage))
        self.assertEqual(ids(new.players[0].bench), [state.players[0].bench[0].pokemon_id, old_active.pokemon_id,
                                                     state.players[0].bench[2].pokemon_id])
        self.assertEqual(new.players[0].discard, [card])  # トラッシュしたのはポケモンいれかえだけ（エネルギーは払わない）
        self.assertEqual(new.log[-2]["kind"], "switch")
        self.assertEqual(check_invariants(new), [])

    def test_invalid_targets(self):
        state, card = self.switch_state([PONYTA])
        pending = apply_command(state, PlayTrainer(0, card))
        d = pending.decision
        for wrong in (active(state, 0).pokemon_id, active(state, 1).pokemon_id, state.players[1].bench[0].pokemon_id, 99):
            self.assert_rejected(pending, ResolveDecision(0, d.id, (wrong,)), "INVALID_CHOICE")

    def test_retreat_before_and_after_switch(self):
        """にげるは 1 番に何度でもできる（p.311）。ポケモンいれかえはにげるの回数と関係しない。"""
        state, card = self.switch_state([{"card": PONYTA, "energy": [FIRE]}, RATTATA])
        # にげてから（ガーディのにげるエネルギーは 1 個）、ポケモンいれかえ
        self.assertEqual(state.card_def(active(state, 0).card).retreat_cost, 1)
        state = apply_command(state, Retreat(0, (active(state, 0).energy[0],), state.players[0].bench[0].card))
        rattata = state.players[0].bench[1]
        self.assertEqual(state.cards[rattata.card].card_id, RATTATA)
        state = self.switch(state, card, rattata.pokemon_id)
        # ポケモンいれかえのあとで、もう一度にげる（コラッタのにげるエネルギーは 0 個）
        self.assertEqual(active(state, 0).pokemon_id, rattata.pokemon_id)
        new = apply_command(state, Retreat(0, (), state.players[0].bench[0].card))
        self.assertEqual(new.phase, Phase.MAIN)
        self.assertEqual([e["kind"] for e in new.log if e["kind"] in ("retreat", "switch")], ["retreat", "switch", "retreat"])
        self.assertEqual(len(new.players[0].discard), 2)  # にげるで払ったエネルギー 1 枚と、ポケモンいれかえ
        self.assertIn(card, new.players[0].discard)


# ---------------------------------------------------------------- 決定（PendingDecision）との統合


class TrainerDecisionTest(RejectsMixin, unittest.TestCase):
    """トレーナーの決定は v0.2a の保留中の決定（ResolveDecision・pokemon_id）を使う。"""

    def setUp(self):
        self.state = build_test_state([
            {"active": {"card": GROWLITHE, "damage": 30}, "bench": [{"card": PONYTA, "damage": 20}], "hand": [POTION, SWITCH, FIRE, RATTATA]},
            {"active": STARYU, "bench": [SEEL]},
        ])
        self.potion, self.switch_card, self.fire, self.rattata = self.state.players[0].hand
        self.pending = apply_command(self.state, PlayTrainer(0, self.potion))
        self.target = active(self.state, 0).pokemon_id

    def test_other_player_cannot_answer(self):
        self.assert_rejected(self.pending, ResolveDecision(1, self.pending.decision.id, (self.target,)), "NOT_YOUR_DECISION")

    def test_unrelated_commands_are_rejected_while_waiting(self):
        p = self.pending.players[0]
        for command in (EndTurn(0), UseAttack(0, 0), AttachEnergy(0, self.fire, p.active.card),
                        PlayBasicToBench(0, self.rattata), Retreat(0, (), p.bench[0].card), PlayTrainer(0, self.switch_card)):
            with self.subTest(command=type(command).__name__):
                self.assert_rejected(self.pending, command, "WRONG_PHASE")

    def test_double_submission_and_stale_ids(self):
        d = self.pending.decision
        done = apply_command(self.pending, ResolveDecision(0, d.id, (self.target,)))
        self.assert_rejected(done, ResolveDecision(0, d.id, (self.target,)), "WRONG_PHASE")  # もう決定はない
        # 次のトレーナーの決定に、古い決定の番号で答えることはできない
        switching = apply_command(done, PlayTrainer(0, self.switch_card))
        self.assertGreater(switching.decision.id, d.id)
        self.assert_rejected(switching, ResolveDecision(0, d.id, (switching.decision.options[0],)), "WRONG_DECISION")
        self.assert_rejected(switching, ResolveDecision(0, switching.decision.id + 1, (switching.decision.options[0],)), "WRONG_DECISION")

    def test_resume_after_clone_deepcopy_pickle_and_rng_json(self):
        command = ResolveDecision(0, self.pending.decision.id, (self.target,))
        expected = full(apply_command(self.pending, command))
        copies = [self.pending.clone(), copy.deepcopy(self.pending), pickle.loads(pickle.dumps(self.pending))]
        restored = self.pending.clone()
        restored.rng = rng_from_json(json.loads(json.dumps(rng_state_to_json(self.pending.rng))))
        copies.append(restored)
        for copied in copies:
            self.assertEqual(full(copied), full(self.pending))
            self.assertEqual(full(apply_command(copied, command)), expected)

    def test_decision_state_is_json_ready(self):
        data = full(self.pending)
        self.assertEqual(data["decision"]["resume"], "trainer")
        self.assertEqual(data["decision"]["context"]["use"], [0, self.potion, POTION])
        self.assertEqual(data["format_version"], 3)
        json.dumps(data)

    def test_broken_trainer_state_is_detected(self):
        """使用中のトレーナーと決定が合わない状態は、不変条件で見つける（二重の存在・消失）。"""
        broken = self.pending.clone()
        broken.trainer_in_use = None
        self.assertTrue(any("どこにもない" in p for p in check_invariants(broken)))
        self.assertTrue(any("使用中のトレーナーがない" in p for p in check_invariants(broken)))
        doubled = self.pending.clone()
        doubled.players[0].hand.append(self.potion)
        self.assertTrue(any("2 か所" in p for p in check_invariants(doubled)))
        other = self.pending.clone()
        other.trainer_in_use = TrainerInUse(0, self.switch_card)
        other.players[0].hand.remove(self.switch_card)
        other.players[0].hand.append(self.potion)
        self.assertTrue(any("使用中のトレーナー" in p for p in check_invariants(other)))
        idle = self.state.clone()
        idle.players[0].hand.remove(self.potion)
        idle.trainer_in_use = TrainerInUse(0, self.potion)
        self.assertTrue(any("決定を待っていない" in p for p in check_invariants(idle)))
        not_trainer = self.state.clone()
        not_trainer.players[0].hand.remove(self.fire)
        not_trainer.trainer_in_use = TrainerInUse(0, self.fire)
        self.assertTrue(any("トレーナーカードでない" in p for p in check_invariants(not_trainer)))


if __name__ == "__main__":
    unittest.main()

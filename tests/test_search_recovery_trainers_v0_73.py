"""v0.73: 拡張パック以外の商品の、検索・回収・ドローのトレーナー 18 枚（docs/search-recovery-trainers-v0.73.md）。

18 枚（10 の処理）: 元気のかたまり（GD5-019・ES2-034）・熱血!（GD5-021）・マスターボール（GD6-023・ES2-036・QSG-058・NIP1-021・NIP2-022）・化石の発掘（ES1-035）・
月の石（ES1-036）・ポケモン再転送（ES3-035）・スーパーポケモン回収（IP1-009・IP2-029）・マサキの転送装置（IP1-020・IP2-021）・超エネルギー回収（PR1-009）・
パソコン大暴走！（PR1-026・PR1-041）。どれも kyuura データの採用（採用したデータのコミット 7d3f4ca）。処理に使う文面は kyuura の印刷の文面、超エネルギー回収だけは kyuura の
エラッタの記録 ERR-SUPER-ENERGY-RETRIEVAL（記録の cards は pcg-search.com の id 1stp009）の notes が引用する最新の説明（『オフィシャルブック2000』p.292 の引用。エンジンは
ガイドブックを読み直していない）。kyuura の日本語の文面は pcg-search.com の転記なので、外部照合はしていない。英語版の文面・現代のルール・2002 年のサポーターの規定で、日本語版の
条件を補わない。

新しい停止コードは 5: MR1（元気のかたまり）・ML1（マスターボールの山札 7 枚未満）・SR1・SR2（超エネルギー回収。エネルギー回収の ER10・ER9 と同じ形の別のカードの問い）・
FV1（熱血!とレインボーエネルギー）。熱血!の山札 3 枚未満は v0.31 の HC6（同じ問い）、ポケモン再転送の対象なしは v0.53 の ST1（同じ問い）。
"""

from __future__ import annotations

import json
import pathlib
import unittest

from kyuura_engine import (
    EndTurn,
    IllegalActionError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    check_invariants,
    observe,
    state_to_dict,
    visible_log,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    BENCH_FROM_DISCARD,
    DISCARD_FROM_HAND,
    DISCARD_TO_DECK_TOP,
    PROMOTE_ACTIVE,
    RETRIEVE_ENERGY,
    SEARCH_DECK,
    SEARCH_DECK_OR_DISCARD,
    SELECT_DRAW_COUNT,
    SELECT_POKEMON,
    TAKE_LOOKED_POKEMON,
    USE_DISCARD_TRAINER,
)
from kyuura_engine.observation import HIDDEN_COUNT_KINDS, OPTION_MEANINGS, PUBLIC_EVENTS
from kyuura_engine.serialize import FORMAT_VERSIONS
from tests.helpers import (
    BILLS_TELEPORTER,
    BILLS_TELEPORTER_IP2,
    CLEFAIRY_DOLL,
    COMPUTER_ERROR,
    COMPUTER_ERROR_041,
    DEFENDER,
    ERIKA,
    FERVOR,
    FIRE,
    FOSSIL_EXCAVATION,
    MASTER_BALL,
    MASTER_BALL_ES2,
    MASTER_BALL_NIP1,
    MASTER_BALL_NIP2,
    MASTER_BALL_QSG,
    MAX_REVIVE,
    MAX_REVIVE_ES2,
    MOON_STONE,
    MYSTERIOUS_FOSSIL,
    POKEMON_RETRIEVER,
    SABRINAS_PSYCHIC_CONTROL,
    SUPER_ENERGY_RETRIEVAL,
    SUPER_SCOOP_UP,
    SUPER_SCOOP_UP_IP2,
    V0_73_CARDS,
    WATER,
    apply_kernel,
    assert_stop_code_counts_since,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "search-recovery-trainers-v0.73.md"
LINKS = ROOT / "kyuura_engine" / "data" / "research_links.json"
H, T = CoinSide.HEADS, CoinSide.TAILS
TURN = 7
DCE, RAINBOW = "PMCG1-096", "PMCG4-065"
HITMONCHAN, MACHOKE, RATTATA, RATICATE, PIDGEY, PIDGEOTTO, DODUO, VULPIX = (
    "PMCG1-058", "PMCG1-055", "PMCG1-060", "PMCG1-062", "PMCG1-059", "PMCG1-066", "PMCG1-061", "PMCG1-015")
MR1 = "UNRESOLVED_MAX_REVIVE_WITHOUT_TARGET"
ML1 = "UNRESOLVED_MASTER_BALL_SHORT_DECK"
SR1 = "UNRESOLVED_SUPER_ENERGY_RETRIEVAL_WITHOUT_TARGET"
SR2 = "UNRESOLVED_SUPER_ENERGY_RETRIEVAL_ZERO_CHOICE"
FV1 = "UNRESOLVED_FERVOR_RAINBOW_ENERGY"
HC6 = "UNRESOLVED_DISCARD_DECK_SHORT"
ST1 = "UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET"
NEW_CODES = (MR1, ML1, SR1, SR2, FV1)
TYPES = {
    MAX_REVIVE: E.DiscardEnergyThenBenchBasicFromDiscard, MAX_REVIVE_ES2: E.DiscardEnergyThenBenchBasicFromDiscard,
    FERVOR: E.DiscardDeckTopThenReturnTypeEnergy,
    MASTER_BALL: E.LookTopTakePokemonThenShuffle, MASTER_BALL_ES2: E.LookTopTakePokemonThenShuffle, MASTER_BALL_QSG: E.LookTopTakePokemonThenShuffle,
    MASTER_BALL_NIP1: E.LookTopTakePokemonThenShuffle, MASTER_BALL_NIP2: E.LookTopTakePokemonThenShuffle,
    FOSSIL_EXCAVATION: E.SearchNamedFromDeckOrDiscard, MOON_STONE: E.SearchDeckTrainer, POKEMON_RETRIEVER: E.TakeFromDiscardTrainer,
    SUPER_SCOOP_UP: E.CoinReturnOwnPokemonWithAttachedToHand, SUPER_SCOOP_UP_IP2: E.CoinReturnOwnPokemonWithAttachedToHand,
    BILLS_TELEPORTER: E.CoinDrawTrainer, BILLS_TELEPORTER_IP2: E.CoinDrawTrainer,
    SUPER_ENERGY_RETRIEVAL: E.SuperEnergyRetrieval, COMPUTER_ERROR: E.EachPlayerMayDrawThenEndTurn, COMPUTER_ERROR_041: E.EachPlayerMayDrawThenEndTurn,
}
SHARED = {MASTER_BALL_ES2: MASTER_BALL, MASTER_BALL_QSG: MASTER_BALL, MASTER_BALL_NIP2: MASTER_BALL_NIP1, SUPER_SCOOP_UP_IP2: SUPER_SCOOP_UP,
          BILLS_TELEPORTER_IP2: BILLS_TELEPORTER, COMPUTER_ERROR_041: COMPUTER_ERROR}


def board(hand=(), *, deck=None, discard=(), bench=(RATTATA,), active=HITMONCHAN, prizes=6, opponent=None, opponent_deck=None, seed=0):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "discard": list(discard), "prizes": prizes}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": HITMONCHAN, "bench": [RATTATA], **(opponent or {})}
    if opponent_deck is not None:
        them["deck"] = list(opponent_deck)
    return build_test_state([me, them], turn_number=TURN, current_player=0, seed=seed)


def uid_of(state, card_id, zone="hand", player=0):
    return next(uid for uid in getattr(state.players[player], zone) if state.cards[uid].card_id == card_id)


def uids_of(state, card_id, zone, player=0):
    return [uid for uid in getattr(state.players[player], zone) if state.cards[uid].card_id == card_id]


def play(state, card_id, player=0, *coins):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, PlayTrainer(player, uid_of(state, card_id, player=player)))


def answer(state, choices):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)))


def snapshot(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


def since_play(state):
    start = max(i for i, e in enumerate(state.log) if e["kind"] == "play_trainer")
    return state.log[start:]


def kinds(state):
    return [e["kind"] for e in since_play(state)]


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def assert_stops(test, state, command, code, error=UnsupportedError):
    before = snapshot(state)
    with test.assertRaises(error) as caught:
        apply_kernel(state, command)
    test.assertEqual(caught.exception.code, code)
    test.assertEqual(snapshot(state), before)  # 状態・ログ・乱数は変わらない


def coin_flips(state):
    return [e for e in since_play(state) if e["kind"] == "coin_flip"]


def names(state, uids):
    return [state.card_def(uid).name_ja for uid in uids]


# ---------------------------------------------------------------- 登録・資料


class RegistrationTest(unittest.TestCase):
    def test_pool_registrations_types_and_texts(self):
        pool = load_card_pool()
        extract = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text())
        self.assertEqual(extract["pool_v0_73"], list(V0_73_CARDS))
        for card_id in V0_73_CARDS:
            with self.subTest(card_id=card_id):
                definition = pool.definitions[card_id]
                self.assertEqual(definition.category, "trainer")
                self.assertTrue(pool.is_playable(card_id))
                entry = E.DEFAULT_EFFECTS.trainer_entry(card_id)
                self.assertIs(type(entry.effect), TYPES[card_id])
                self.assertEqual(entry.name_ja, definition.name_ja)
                self.assertEqual(entry.text_ja, definition.trainer_text_ja)
                self.assertEqual(entry.effect.check(definition), [])
                if card_id == SUPER_ENERGY_RETRIEVAL:
                    # 処理に使う文面はエラッタ（印刷の文面とは別）。出典は記録の id
                    self.assertNotEqual(entry.play_text_ja, entry.text_ja)
                    self.assertEqual(entry.play_text_ja, E.SUPER_ENERGY_RETRIEVAL_PLAY_TEXT)
                    self.assertEqual(entry.play_text_ja, entry.effect.play_text)
                    self.assertEqual(entry.source, "ERR-SUPER-ENERGY-RETRIEVAL")
                else:
                    self.assertEqual((entry.play_text_ja, entry.source), (definition.trainer_text_ja, "kyuura data/cards.json"))

    def test_counts_from_the_registry(self):
        pool = load_card_pool()
        registry = E.DEFAULT_EFFECTS
        extract = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text())
        later = set(extract["pool_v0_74"]) | set(extract["pool_v0_75"]) | set(extract["pool_v0_76"]) | set(extract["pool_v0_77"])  # v0.76 の 24 枚も除く。 v0.74 の 13 枚（スタジアム）・v0.75 の 15 枚を除いて比べる
        playable = pool.playable_ids - later
        categories = [pool.get(c).category for c in playable]
        self.assertEqual((len(extract["cards"]) - len(later), len(playable)), (774, 774))
        self.assertEqual((categories.count("pokemon"), categories.count("trainer"), categories.count("energy")), (546, 198, 30))
        self.assertEqual((len(registry.attack_keys()), len(registry.power_keys()), len([c for c in registry.trainer_ids() if c not in later]), len(registry.energy_ids())),
                         (1072, 74, 198, 12))  # v0.77 で neo 期の拡張パックのポケモン 50 枚（ワザ 77）を加えた（トレーナー 2 枚はあとの版として除く）  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた

    @unittest.skipUnless((ROOT.parent / "kyuura" / ".git").exists(), "../kyuura がない")
    def test_non_pack_unsupported_count(self):
        """kyuura data/engine_targets.json（7d3f4ca）の対象のうち、拡張パック以外の商品で対応していないカードは 280 枚（v0.72 は 298 枚）。"""
        import subprocess

        def show(path):
            return json.loads(subprocess.check_output(["git", "-C", str(ROOT.parent / "kyuura"), "show", f"7d3f4ca76c084774efb4ac6a1d3a943387e183c3:{path}"]))

        groups = {c["id"]: c["product_group"] for c in show("data/cards.json")["cards"]}
        pool = load_card_pool()
        targets = show("data/engine_targets.json")["cards"]
        extract = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text())
        later = set(extract["pool_v0_74"]) | set(extract["pool_v0_75"]) | set(extract["pool_v0_76"]) | set(extract["pool_v0_77"])  # v0.76 の 24 枚も除く。 v0.74 の 13 枚・v0.75 の 15 枚は未対応として数える（v0.73 の時点の数）
        self.assertEqual(sum(1 for x in targets if groups[x["id"]] != "expansion_pack" and x["id"] not in pool.playable_ids - later), 280)
        self.assertTrue(all(groups[c] != "expansion_pack" for c in V0_73_CARDS))

    def test_same_data_cards_share_one_entry_but_the_two_master_ball_groups_do_not(self):
        for new, original in SHARED.items():
            with self.subTest(card=new):
                self.assertIs(E.DEFAULT_EFFECTS.trainer_entry(new), E.DEFAULT_EFFECTS.trainer_entry(original))
        self.assertEqual(dict(E.SAME_DATA_CARDS_V0_73), SHARED)
        pool = load_card_pool()
        self.assertNotEqual(pool.definitions[MASTER_BALL].trainer_text_ja, pool.definitions[MASTER_BALL_NIP1].trainer_text_ja)
        self.assertIsNot(E.DEFAULT_EFFECTS.trainer_entry(MASTER_BALL), E.DEFAULT_EFFECTS.trainer_entry(MASTER_BALL_NIP1))
        with self.assertRaises(RuntimeError):  # 違う登録はまとめない
            E._with_shared_trainers(E.DEFAULT_EFFECTS, {MASTER_BALL_NIP1: MASTER_BALL})
        with self.assertRaises(RuntimeError):  # すでに登録のある id には加えない
            E._with_trainers(E.DEFAULT_EFFECTS, {MASTER_BALL: E.DEFAULT_EFFECTS.trainer_entry(MASTER_BALL)})

    def test_registration_checks_reject_mismatches(self):
        pool = load_card_pool()
        cases = [
            (MAX_REVIVE, E.DiscardEnergyThenBenchBasicFromDiscard(E.MAX_REVIVE_TEXT, bench_full_unusable=True)),  # その版には使えない場合がない
            (MAX_REVIVE_ES2, E.DiscardEnergyThenBenchBasicFromDiscard(E.MAX_REVIVE_BENCH_FULL_TEXT)),  # その版には書いてある
            (MAX_REVIVE, E.DiscardEnergyThenBenchBasicFromDiscard(E.MAX_REVIVE_TEXT, discard=1)),
            (FERVOR, E.DiscardDeckTopThenReturnTypeEnergy(E.FERVOR_TEXT, count=2)),
            (FERVOR, E.DiscardDeckTopThenReturnTypeEnergy(E.FERVOR_TEXT, energy_type=EnergyType.WATER)),
            (MASTER_BALL, E.LookTopTakePokemonThenShuffle(E.MASTER_BALL_TEXT, look=6)),
            (MASTER_BALL_NIP1, E.LookTopTakePokemonThenShuffle(E.MASTER_BALL_TEXT)),  # 文面が違う
            (FOSSIL_EXCAVATION, E.SearchNamedFromDeckOrDiscard(E.FOSSIL_EXCAVATION_TEXT, E.CardFilter("trainer", name="ピッピ人形"))),
            (MOON_STONE, E.SearchDeckTrainer(E.MOON_STONE_TEXT, E.CardFilter("pokemon", evolution_only=True), 1, optional=True, reveal=True)),  # 色がない
            (MOON_STONE, E.SearchDeckTrainer(E.MOON_STONE_TEXT, E.CardFilter("pokemon", evolution_only=True, pokemon_type=EnergyType.GRASS), 1,
                                             optional=True, reveal=True)),
            (MOON_STONE, E.SearchDeckTrainer(E.MOON_STONE_TEXT, E._MOON_STONE_TARGET, 1, optional=False, reveal=True)),  # 「てよい」がある
            (POKEMON_RETRIEVER, E.TakeFromDiscardTrainer(E.POKEMON_RETRIEVER_TEXT, E.CardFilter("pokemon", evolution_only=True), 1, E.TO_HAND)),
            (SUPER_SCOOP_UP, E.CoinReturnOwnPokemonWithAttachedToHand(E.BILLS_TELEPORTER_TEXT)),
            (BILLS_TELEPORTER, E.CoinDrawTrainer(E.BILLS_TELEPORTER_TEXT, count=3)),
            (SUPER_ENERGY_RETRIEVAL, E.SuperEnergyRetrieval(discard=1, retrieve=4)),
            (SUPER_ENERGY_RETRIEVAL, E.SuperEnergyRetrieval(discard=2, retrieve=4, play_text=E.SUPER_ENERGY_RETRIEVAL_PLAY_TEXT.replace("「基本エネルギーカード」", "エネルギーカード"))),
            (SUPER_ENERGY_RETRIEVAL, E.SuperEnergyRetrieval(discard=2, retrieve=4, play_text=E.SUPER_ENERGY_RETRIEVAL_PLAY_TEXT.split("ただし")[0])),
            (COMPUTER_ERROR, E.EachPlayerMayDrawThenEndTurn(E.COMPUTER_ERROR_TEXT, 3)),
        ]
        for card_id, effect in cases:
            with self.subTest(card=card_id, effect=type(effect).__name__):
                self.assertNotEqual(effect.check(pool.definitions[card_id]), [])

    def test_card_filter_pokemon_type_and_exact_name(self):
        """v0.73 の CardFilter: ポケモンのタイプ（進化カード自身のタイプ）と名前の完全一致。意味のない組み合わせは作るときに拒否する。"""
        pool = load_card_pool()
        moon = E._MOON_STONE_TARGET
        self.assertTrue(moon.matches(pool.definitions[RATICATE]))  # 無色の 1 進化
        self.assertTrue(moon.matches(pool.definitions[PIDGEOTTO]))
        self.assertFalse(moon.matches(pool.definitions[RATTATA]))  # 無色のたねポケモン（進化カードではない）
        self.assertFalse(moon.matches(pool.definitions[MACHOKE]))  # 闘の 1 進化
        self.assertFalse(moon.matches(pool.definitions[DCE]))
        fossil = E.CardFilter("trainer", name="なにかの化石")
        self.assertTrue(fossil.matches(pool.definitions[MYSTERIOUS_FOSSIL]))  # 山札・トラッシュではトレーナーカード
        self.assertFalse(fossil.matches(pool.definitions[CLEFAIRY_DOLL]))
        for bad in ({"kind": "pokemon", "energy_type": EnergyType.COLORLESS}, {"kind": "basic_energy", "pokemon_type": EnergyType.FIRE},
                    {"kind": "trainer", "evolution_only": True}, {"kind": "any", "name": "なにかの化石", "name_prefix": "なにか"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                E.CardFilter(**bad)

    def test_new_decisions_and_events_are_in_the_observation_tables(self):
        for kind in (SEARCH_DECK_OR_DISCARD, TAKE_LOOKED_POKEMON):
            self.assertEqual(OPTION_MEANINGS[kind], "card")
            self.assertIn(kind, HIDDEN_COUNT_KINDS)  # 選べるものの数が山札の中身を漏らす
        self.assertIn("milled_to_hand", PUBLIC_EVENTS)

    def test_stop_codes_and_documents(self):
        links = json.loads(LINKS.read_text(encoding="utf-8"))
        assert_stop_code_counts_since(self, links, 156, 158)
        for code in NEW_CODES:
            with self.subTest(code=code):
                entry = links["stop_codes"][code]
                self.assertEqual(entry["kyuura_disposition"], "not_in_kyuura")
                self.assertEqual(entry["engine_rulings"][0]["document"], "docs/search-recovery-trainers-v0.73.md")
        self.assertEqual(links["latest_descriptions"]["errata_text"]["PR1-009/trainer"], "ERR-SUPER-ENERGY-RETRIEVAL")
        self.assertEqual(links["latest_descriptions"]["errata_card_ids"]["PR1-009"],
                         {"record": "ERR-SUPER-ENERGY-RETRIEVAL", "record_card": "1stp009", "page": "p.292"})
        text = DOC.read_text(encoding="utf-8")
        for word in (*NEW_CODES, "MR1", "ML1", "SR1", "SR2", "FV1", "HC6", "ST1", "1stp009", "未確認"):
            self.assertIn(word, text)

    @unittest.skipUnless((ROOT.parent / "kyuura" / ".git").exists(), "../kyuura がない")
    def test_research_check_rejects_a_wrong_id_quote_or_condition(self):
        """超エネルギー回収のエラッタの対応（errata_card_ids）・引用の確かめは、id・ページ・文面がちがえば失敗する（狭く広げた検査）。"""
        from scripts import check_research_links as crl

        kyuura = ROOT.parent / "kyuura"
        links = json.loads(LINKS.read_text(encoding="utf-8"))
        self.assertEqual(crl.check(kyuura, links=links), [])

        def broken(change):
            copy = json.loads(json.dumps(links))
            change(copy["latest_descriptions"])
            return crl.check(kyuura, links=copy)

        self.assertTrue(broken(lambda s: s["errata_card_ids"]["PR1-009"].update(record_card="1stp010")))
        self.assertTrue(broken(lambda s: s["errata_card_ids"]["PR1-009"].update(page="p.257")))
        self.assertTrue(broken(lambda s: s.pop("errata_card_ids")))
        registry = E._with_shared_trainers(E.DEFAULT_EFFECTS, {})
        wrong = E.TrainerEntry(E.SuperEnergyRetrieval(discard=2, retrieve=4), "超エネルギー回収", E.SUPER_ENERGY_RETRIEVAL_TEXT,
                               E.SUPER_ENERGY_RETRIEVAL_PLAY_TEXT.split("ただし")[0], E.SUPER_ENERGY_RETRIEVAL_SOURCE)
        registry._trainers["PR1-009"] = wrong
        self.assertTrue(crl.check(kyuura, links=links, registry=registry))


# ---------------------------------------------------------------- 元気のかたまり


class MaxReviveTest(unittest.TestCase):
    def test_discards_two_energy_cards_then_benches_a_basic_without_counters(self):
        state = board([MAX_REVIVE, DCE, FIRE, DEFENDER], discard=[DODUO, RATICATE, WATER])
        state = play(state, MAX_REVIVE)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (DISCARD_FROM_HAND, 2, 2))
        self.assertEqual(names(state, d.options), ["無色2個エネルギー", "炎エネルギー"])  # トレーナーカードでは払えない。無色2個エネルギーは 1 枚
        audited(self, state)
        state = answer(state, d.options)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (BENCH_FROM_DISCARD, 1, 1))
        self.assertEqual(names(state, d.options), ["ドードー"])  # 進化カード・エネルギーカードは選べない
        audited(self, state)
        doduo = d.options[0]
        state = answer(state, (doduo,))
        benched = state.players[0].bench[-1]
        self.assertEqual((benched.card, benched.damage, benched.played_turn), (doduo, 0, TURN))  # 同じ uid。カウンターなし。場に出た番は今の番
        self.assertEqual(kinds(state), ["play_trainer", "discard_from_hand", "bench_from_discard", "discard_trainer"])
        self.assertEqual(state.phase, Phase.MAIN)
        audited(self, state)

    def test_cost_needs_two_energy_cards_other_than_this_card(self):
        state = board([MAX_REVIVE, FIRE, DEFENDER, HITMONCHAN], discard=[DODUO])
        assert_stops(self, state, PlayTrainer(0, uid_of(state, MAX_REVIVE)), "INSUFFICIENT_ENERGY_CARDS_IN_HAND", IllegalActionError)

    def test_bench_full_is_illegal_only_on_the_es2_printing(self):
        full = (RATTATA, PIDGEY, DODUO, VULPIX, RATTATA)
        es2 = board([MAX_REVIVE_ES2, FIRE, WATER], discard=[DODUO], bench=full)
        assert_stops(self, es2, PlayTrainer(0, uid_of(es2, MAX_REVIVE_ES2)), "BENCH_FULL", IllegalActionError)
        es2_no_cost = board([MAX_REVIVE_ES2, FIRE], discard=[DODUO], bench=full)
        assert_stops(self, es2_no_cost, PlayTrainer(0, uid_of(es2_no_cost, MAX_REVIVE_ES2)), "BENCH_FULL", IllegalActionError)  # トラッシュの前に拒否
        gd5 = board([MAX_REVIVE, FIRE, WATER], discard=[DODUO], bench=full)
        assert_stops(self, gd5, PlayTrainer(0, uid_of(gd5, MAX_REVIVE)), MR1)  # その版には使えない場合が書かれていない

    def test_no_basic_in_discard_stops_on_both_printings(self):
        for card_id in (MAX_REVIVE, MAX_REVIVE_ES2):
            with self.subTest(card=card_id):
                state = board([card_id, FIRE, WATER], discard=[RATICATE, MYSTERIOUS_FOSSIL])  # なにかの化石はトラッシュではトレーナーカード
                assert_stops(self, state, PlayTrainer(0, uid_of(state, card_id)), MR1)

    def test_invalid_bench_answer_keeps_the_paid_cost(self):
        state = play(board([MAX_REVIVE, FIRE, WATER], discard=[DODUO, RATICATE]), MAX_REVIVE)
        state = answer(state, state.decision.options)
        raticate = uid_of(state, RATICATE, "discard")
        with self.assertRaises(IllegalActionError):
            answer(state, (raticate,))
        self.assertEqual(state.decision.kind, BENCH_FROM_DISCARD)
        self.assertEqual(len(state.players[0].hand), 0)  # トラッシュしたエネルギーカードはもどらない
        state = answer(state, state.decision.options)  # 拒否のあとも続けられる
        audited(self, state)


# ---------------------------------------------------------------- 熱血!


class FervorTest(unittest.TestCase):
    def test_returns_only_fire_energy_among_the_milled_cards(self):
        state = board([FERVOR], deck=[FIRE, WATER, FIRE, HITMONCHAN, WATER], discard=[FIRE])
        old_fire = uid_of(state, FIRE, "discard")
        top = list(state.players[0].deck[:3])
        rest = list(state.players[0].deck[3:])
        state = play(state, FERVOR)
        self.assertEqual(kinds(state), ["play_trainer", "deck_top_to_discard", "milled_to_hand", "discard_trainer"])
        milled = since_play(state)[1]["cards"]
        self.assertEqual(list(milled), top)
        returned = [uid for uid in top if state.cards[uid].card_id == FIRE]
        self.assertEqual(list(since_play(state)[2]["cards"]), returned)
        self.assertTrue(all(uid in state.players[0].hand for uid in returned))
        self.assertIn(old_fire, state.players[0].discard)  # 前からトラッシュにあった炎は加えない
        self.assertIn(top[1], state.players[0].discard)  # 水はトラッシュに残る
        self.assertEqual(state.players[0].deck, rest)  # 切らない
        audited(self, state)

    def test_no_fire_among_the_three_still_mills(self):
        state = play(board([FERVOR], deck=[WATER, DCE, HITMONCHAN, FIRE]), FERVOR)
        self.assertEqual(since_play(state)[2]["cards"], ())  # 無色2個エネルギーは「炎」エネルギーカードではない
        self.assertEqual(len(state.players[0].deck), 1)
        audited(self, state)

    def test_short_deck_stops_as_hc6_and_rainbow_stops_as_fv1(self):
        short = board([FERVOR], deck=[FIRE, FIRE])
        assert_stops(self, short, PlayTrainer(0, uid_of(short, FERVOR)), HC6)
        empty = board([FERVOR], deck=[])
        assert_stops(self, empty, PlayTrainer(0, uid_of(empty, FERVOR)), HC6)
        in_deck = board([FERVOR], deck=[WATER, WATER, WATER, RAINBOW])  # 上の 3 枚に入っていなくても、持ち主には分からない
        assert_stops(self, in_deck, PlayTrainer(0, uid_of(in_deck, FERVOR)), FV1)
        in_prizes = board([FERVOR], deck=[WATER, WATER, WATER], prizes=[RAINBOW, FIRE])
        assert_stops(self, in_prizes, PlayTrainer(0, uid_of(in_prizes, FERVOR)), FV1)


# ---------------------------------------------------------------- マスターボール


class MasterBallTest(unittest.TestCase):
    def deck(self):
        # 上から 7 枚: 炎・ポッポ・水・ピッピ人形・ラッタ・炎・炎、8 枚目のコラッタは選べない
        return [FIRE, PIDGEY, WATER, CLEFAIRY_DOLL, RATICATE, FIRE, FIRE, RATTATA, WATER]

    def test_only_pokemon_among_the_top_seven_and_one_is_mandatory(self):
        for card_id in (MASTER_BALL, MASTER_BALL_NIP1):
            with self.subTest(card=card_id):
                state = play(board([card_id], deck=self.deck()), card_id)
                d = state.decision
                self.assertEqual((d.kind, d.min_choices, d.max_choices), (TAKE_LOOKED_POKEMON, 1, 1))
                self.assertEqual(names(state, d.options), ["ポッポ", "ラッタ"])  # ピッピ人形（トレーナー）・8 枚目のコラッタは選べない
                looked = since_play(state)[-1]
                self.assertEqual((looked["kind"], looked["count"]), ("look_at_deck_top", 7))
                opponent_view = observe(state, 1)["decision"]
                self.assertNotIn("option_count", opponent_view)  # 数を見せない
                self.assertNotIn("cards", [e for e in visible_log(state, 1) if e["kind"] == "look_at_deck_top"][-1])
                audited(self, state)
                with self.assertRaises(IllegalActionError):
                    answer(state, ())  # あるのに選ばない答えはない
                raticate = d.options[1]
                state = answer(state, (raticate,))
                self.assertIn(raticate, state.players[0].hand)
                self.assertEqual(kinds(state), ["play_trainer", "look_at_deck_top", "reveal_from_deck", "shuffle", "discard_trainer"])
                self.assertEqual(len(state.players[0].deck), 8)  # 残りは山札に残す（トラッシュしない）
                reveal = [e for e in visible_log(state, 1) if e["kind"] == "reveal_from_deck"][-1]
                self.assertEqual(reveal["card"], raticate)  # 選んだカードは見せる
                audited(self, state)

    def test_no_pokemon_in_the_top_seven_shuffles_without_a_decision(self):
        state = play(board([MASTER_BALL], deck=[FIRE] * 7 + [RATTATA]), MASTER_BALL)
        self.assertIsNone(state.decision)
        self.assertEqual(kinds(state), ["play_trainer", "look_at_deck_top", "trainer_take_none", "shuffle", "discard_trainer"])
        audited(self, state)

    def test_short_deck_stops_as_ml1(self):
        for deck in ([PIDGEY] * 6, []):
            with self.subTest(size=len(deck)):
                state = board([MASTER_BALL], deck=deck)
                assert_stops(self, state, PlayTrainer(0, uid_of(state, MASTER_BALL)), ML1)


# ---------------------------------------------------------------- 化石の発掘・月の石・ポケモン再転送


class FossilMoonRetrieverTest(unittest.TestCase):
    def test_fossil_from_deck_or_discard_then_always_shuffle(self):
        state = board([FOSSIL_EXCAVATION], deck=[FIRE, MYSTERIOUS_FOSSIL, CLEFAIRY_DOLL], discard=[MYSTERIOUS_FOSSIL, CLEFAIRY_DOLL])
        state = play(state, FOSSIL_EXCAVATION)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (SEARCH_DECK_OR_DISCARD, 0, 1))
        in_deck, in_discard = uid_of(state, MYSTERIOUS_FOSSIL, "deck"), uid_of(state, MYSTERIOUS_FOSSIL, "discard")
        self.assertEqual(d.options, (in_deck, in_discard))  # ピッピ人形は選べない
        self.assertNotIn("option_count", observe(state, 1)["decision"])
        audited(self, state)
        from_discard = answer(state, (in_discard,))
        self.assertIn(in_discard, from_discard.players[0].hand)
        self.assertEqual(kinds(from_discard), ["play_trainer", "retrieve_trainer", "shuffle", "discard_trainer"])
        audited(self, from_discard)
        from_deck = answer(state, (in_deck,))
        self.assertEqual(kinds(from_deck), ["play_trainer", "reveal_from_deck", "shuffle", "discard_trainer"])
        audited(self, from_deck)
        none = answer(state, ())
        self.assertEqual(kinds(none), ["play_trainer", "trainer_take_none", "shuffle", "discard_trainer"])
        audited(self, none)

    def test_fossil_excavation_without_target_still_shuffles(self):
        state = play(board([FOSSIL_EXCAVATION], deck=[FIRE, CLEFAIRY_DOLL]), FOSSIL_EXCAVATION)
        self.assertEqual(kinds(state), ["play_trainer", "trainer_take_none", "shuffle", "discard_trainer"])
        audited(self, state)

    def test_moon_stone_selects_colorless_evolution_cards_only(self):
        state = play(board([MOON_STONE], deck=[RATTATA, RATICATE, PIDGEOTTO, MACHOKE, FIRE]), MOON_STONE)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (SEARCH_DECK, 0, 1))
        self.assertEqual(sorted(names(state, d.options)), ["ピジョン", "ラッタ"])
        state = answer(state, (uid_of(state, PIDGEOTTO, "deck"),))
        self.assertEqual(kinds(state), ["play_trainer", "reveal_from_deck", "shuffle", "discard_trainer"])
        audited(self, state)

    def test_pokemon_retriever_puts_an_evolution_card_on_top_without_shuffling(self):
        state = board([POKEMON_RETRIEVER], deck=[FIRE, WATER], discard=[RATTATA, RATICATE, FIRE])
        state = play(state, POKEMON_RETRIEVER)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (DISCARD_TO_DECK_TOP, 1, 1))
        self.assertEqual(names(state, d.options), ["ラッタ"])
        state = answer(state, d.options)
        self.assertEqual(state.players[0].deck[0], d.options[0])
        self.assertEqual(kinds(state), ["play_trainer", "put_discard_on_deck_top", "discard_trainer"])  # 切らない・コインなし
        audited(self, state)
        none = board([POKEMON_RETRIEVER], discard=[RATTATA, FIRE])
        assert_stops(self, none, PlayTrainer(0, uid_of(none, POKEMON_RETRIEVER)), ST1)


# ---------------------------------------------------------------- スーパーポケモン回収・マサキの転送装置


class ScoopUpAndTeleporterTest(unittest.TestCase):
    def test_tails_does_nothing(self):
        state = play(board([SUPER_SCOOP_UP]), SUPER_SCOOP_UP, 0, T)
        self.assertEqual(kinds(state), ["play_trainer", "coin_flip", "discard_trainer"])
        audited(self, state)

    def test_heads_returns_a_bench_pokemon_with_all_attached_cards(self):
        bench = {"card": RATICATE, "evolved_from": RATTATA, "damage": 30, "energy": [FIRE, DCE], "trainers": [(DEFENDER, TURN + 1)]}
        state = play(board([SUPER_SCOOP_UP], bench=[bench]), SUPER_SCOOP_UP, 0, H)
        d = state.decision
        active, benched = state.players[0].active, state.players[0].bench[0]
        self.assertEqual((d.kind, d.options), (SELECT_POKEMON, (active.pokemon_id, benched.pokemon_id)))
        cards = (*benched.cards(), *benched.energy, *(t.card for t in benched.trainers))
        state = answer(state, (benched.pokemon_id,))
        self.assertEqual(state.players[0].bench, [])
        self.assertTrue(all(uid in state.players[0].hand for uid in cards))  # 同じ uid のまま全部手札へ
        self.assertEqual(len(coin_flips(state)), 1)  # 答えのあとで投げ直さない
        self.assertNotIn("knock_out", kinds(state))  # きぜつではない
        self.assertEqual(state.players[0].prizes and len(state.players[1].prizes), 6)
        audited(self, state)

    def test_returning_the_active_promotes_from_the_bench(self):
        state = play(board([SUPER_SCOOP_UP], active={"card": HITMONCHAN, "energy": [FIRE]}), SUPER_SCOOP_UP, 0, H)
        active = state.players[0].active
        state = answer(state, (active.pokemon_id,))
        self.assertEqual(state.decision.kind, PROMOTE_ACTIVE)
        self.assertEqual([e for e in state.log if e["kind"] == "return_in_play_to_hand"][-1]["zone"], "active")
        audited(self, state)
        state = answer(state, state.decision.options)
        self.assertEqual(state.phase, Phase.MAIN)
        audited(self, state)

    def test_returning_the_last_pokemon_loses(self):
        state = play(board([SUPER_SCOOP_UP], bench=()), SUPER_SCOOP_UP, 0, H)
        state = answer(state, (state.players[0].active.pokemon_id,))
        self.assertEqual(state.phase, Phase.GAME_OVER)  # 代わりのポケモンを出せないので負け（p.311）
        self.assertEqual(state.result.winner, 1)
        audited(self, state)

    def test_bills_teleporter_draws_four_on_heads(self):
        heads = play(board([BILLS_TELEPORTER], deck=[FIRE] * 6), BILLS_TELEPORTER, 0, H)
        self.assertEqual((len(heads.players[0].hand), len(heads.players[0].deck)), (4, 2))
        audited(self, heads)
        short = play(board([BILLS_TELEPORTER], deck=[FIRE] * 2), BILLS_TELEPORTER, 0, H)
        self.assertEqual((len(short.players[0].hand), len(short.players[0].deck)), (2, 0))  # 引けるだけ（負けではない）
        self.assertEqual(short.phase, Phase.MAIN)
        tails = play(board([BILLS_TELEPORTER], deck=[FIRE] * 6), BILLS_TELEPORTER, 0, T)
        self.assertEqual(len(tails.players[0].hand), 0)
        self.assertEqual(kinds(tails), ["play_trainer", "coin_flip", "discard_trainer"])


# ---------------------------------------------------------------- 超エネルギー回収


class SuperEnergyRetrievalTest(unittest.TestCase):
    def test_discards_any_two_then_retrieves_up_to_four_basic_energy(self):
        state = board([SUPER_ENERGY_RETRIEVAL, FIRE, DEFENDER, HITMONCHAN], discard=[FIRE, WATER, FIRE, WATER, FIRE, DCE, RAINBOW])
        state = play(state, SUPER_ENERGY_RETRIEVAL)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (DISCARD_FROM_HAND, 2, 2))
        hand_fire = uid_of(state, FIRE)
        state = answer(state, (hand_fire, uid_of(state, DEFENDER)))
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (RETRIEVE_ENERGY, 0, 4))
        self.assertNotIn(hand_fire, d.options)  # トラッシュしたカードは選べない
        self.assertEqual(sorted(names(state, d.options)), ["水エネルギー"] * 2 + ["炎エネルギー"] * 3)  # 特殊エネルギーは選べない
        audited(self, state)
        with self.assertRaises(UnsupportedError) as caught:
            answer(state, ())
        self.assertEqual(caught.exception.code, SR2)
        self.assertEqual(state.decision.kind, RETRIEVE_ENERGY)  # 決定は待ったまま
        state = answer(state, d.options[:4])
        self.assertEqual(len([uid for uid in state.players[0].hand if state.card_def(uid).is_basic_energy]), 4)
        audited(self, state)

    def test_cost_and_no_target(self):
        state = board([SUPER_ENERGY_RETRIEVAL, FIRE], discard=[WATER])
        assert_stops(self, state, PlayTrainer(0, uid_of(state, SUPER_ENERGY_RETRIEVAL)), "INSUFFICIENT_CARDS_IN_HAND", IllegalActionError)
        none = board([SUPER_ENERGY_RETRIEVAL, FIRE, WATER], discard=[DCE, RAINBOW])
        assert_stops(self, none, PlayTrainer(0, uid_of(none, SUPER_ENERGY_RETRIEVAL)), SR1)

    def test_energy_retrieval_keeps_its_own_codes(self):
        """エネルギー回収（PMCG1-076）の ER10・ER9 のコードは変わらない（同じ形の別のカードの問い）。"""
        self.assertEqual(E.DiscardFromHandThenRetrieveEnergy.WITHOUT_TARGET[0], "UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET")
        self.assertEqual(E.DiscardFromHandThenRetrieveEnergy.ZERO_CHOICE[0], "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE")


# ---------------------------------------------------------------- パソコン大暴走！


class ComputerErrorTest(unittest.TestCase):
    def test_each_player_draws_in_order_then_the_users_turn_ends(self):
        state = play(board([COMPUTER_ERROR], deck=[FIRE] * 8, opponent_deck=[WATER] * 3), COMPUTER_ERROR)
        d = state.decision
        self.assertEqual((d.kind, d.player, d.options), (SELECT_DRAW_COUNT, 0, (0, 1, 2, 3, 4, 5)))
        state = answer(state, (5,))
        d = state.decision
        self.assertEqual((d.kind, d.player, d.options), (SELECT_DRAW_COUNT, 1, (0, 1, 2, 3)))  # 相手は自分の山札の枚数まで
        audited(self, state)
        drawn = [e for e in visible_log(state, 1) if e["kind"] == "draw" and e["player"] == 0][-1]
        self.assertNotIn("cards", drawn)  # 引いたカードは見せない（枚数は公開）
        state = answer(state, (2,))
        self.assertEqual((len(state.players[0].hand), len(state.players[1].hand)), (5, 3))  # 相手は番の最初に 1 枚引く
        self.assertEqual((state.turn_number, state.current_player), (TURN + 1, 1))
        turn_end = [e for e in state.log if e["kind"] == "trainer_turn_end"]
        self.assertEqual(turn_end[-1]["player"], 0)
        audited(self, state)

    def test_both_decline_still_ends_the_turn_and_empty_decks_get_no_decision(self):
        state = play(board([COMPUTER_ERROR], deck=[FIRE] * 3, opponent_deck=[WATER] * 3), COMPUTER_ERROR)
        state = answer(state, (0,))
        state = answer(state, (0,))
        self.assertEqual(state.turn_number, TURN + 1)
        audited(self, state)
        empty = play(board([COMPUTER_ERROR_041], deck=[], opponent_deck=[]), COMPUTER_ERROR_041)
        self.assertIsNone(empty.decision if empty.phase == Phase.MAIN else None)
        self.assertEqual([e["reason"] for e in empty.log if e["kind"] == "trainer_draw_declined"], ["empty_deck", "empty_deck"])
        self.assertIn("trainer_turn_end", [e["kind"] for e in empty.log])
        self.assertEqual(empty.phase, Phase.GAME_OVER)  # 相手は番の最初に引けないので負け（p.309・p.312）

    def test_erika_still_does_not_end_the_turn(self):
        state = play(board([ERIKA], deck=[FIRE] * 5, opponent_deck=[WATER] * 5), ERIKA)
        state = answer(state, (1,))
        state = answer(state, (1,))
        self.assertEqual((state.turn_number, state.phase), (TURN, Phase.MAIN))

    def test_used_via_psychic_control_ends_the_actual_users_turn(self):
        state = board([SABRINAS_PSYCHIC_CONTROL], deck=[FIRE] * 5, opponent={"discard": [COMPUTER_ERROR]}, opponent_deck=[WATER] * 5)
        state = play(state, SABRINAS_PSYCHIC_CONTROL, 0, H)
        self.assertEqual(state.decision.kind, USE_DISCARD_TRAINER)
        state = answer(state, state.decision.options)
        state = answer(state, (1,))  # 使ったプレイヤー（プレイヤー 0）
        state = answer(state, (0,))  # 相手
        self.assertEqual((state.turn_number, state.current_player), (TURN + 1, 1))
        self.assertIn(uid_of(state, COMPUTER_ERROR, "discard", 1), state.players[1].discard)  # 持ち主のトラッシュにもどる
        audited(self, state)

    def test_written_state_and_clone_at_the_opponents_decision(self):
        """相手の決定を待つ状態は最新の形式で書き出せ（書き出しの監査）、複製に同じ答えを渡すと同じ結果になる（決定の続きの情報は状態だけにある）。"""
        state = play(board([COMPUTER_ERROR], deck=[FIRE] * 6, opponent_deck=[WATER] * 6), COMPUTER_ERROR)
        state = answer(state, (2,))
        written = state_to_dict(state, format_version=max(FORMAT_VERSIONS))
        self.assertEqual(written["decision"]["kind"], SELECT_DRAW_COUNT)
        self.assertEqual(serialization_problems(state), [])
        a, b = answer(state, (1,)), answer(state.clone(), (1,))
        self.assertEqual(snapshot(a), snapshot(b))


class EndTurnSanityTest(unittest.TestCase):
    def test_endturn_still_works_after_a_v0_73_trainer(self):
        state = play(board([BILLS_TELEPORTER], deck=[FIRE] * 6), BILLS_TELEPORTER, 0, T)
        state = apply_kernel(state, EndTurn(0))
        self.assertEqual(state.turn_number, TURN + 1)


if __name__ == "__main__":
    unittest.main()

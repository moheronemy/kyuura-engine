"""2 進化（v0.4c）: たねポケモン → 1 進化ポケモン → 2 進化ポケモン。ビードル → コクーン → スピアー。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES・first_turn_evolution・
status_on_evolve）。分類（CONFIRMED・SUPPORTED・UNRESOLVED）は docs/stage2-evolution-v0.4c.md、カードの照合は
docs/beedrill-v0.4c.md、状態の持ち方は docs/stage2-state-v0.4c.md。

- p.309「場にいるポケモンを進化させる」: 手札の「○○○○から進化」の進化カードを、その名前のポケモンに重ねる
- p.310: 進化の条件（その番の最初から場に出ていた・おたがいの最初の番は不可・その番に進化したポケモンは別のポケモンで
  もう一度は進化できない・1 回の番に複数のポケモンを進化させてよい）、手順 1〜5、受け継ぐもの（エネルギー・つけて使う
  トレーナー・ダメージカウンター）
- p.313: 進化ポケモンは場をはなれたら、構成していたカードにもどる
- p.316: 1 進化はたねポケモンから、2 進化は 1 進化ポケモンから進化する
- p.319:「進化ポケモン」は「1枚のたねポケモンカードと、1または2枚の進化カードの合計2枚または3枚」（B.「たねポケモン
  カード」+「進化カード」+「進化カード」）。場にいる「たねポケモン」または「進化ポケモン」に進化カードを重ねて進化させる
- p.322・p.323: 特殊状態・持続する効果は進化したら消える。きぜつしたらついているカードもトラッシュ、サイドは 1 匹ぶん
- p.324: 書かれていない組み合わせでカードを重ねてはいけない
- p.21（スピアー）: ダブルニードル（最新の説明「コインを2枚投げ、「おもて」の数×30のダメージ。」）・どくばり
  （「コインを投げて「おもて」なら、相手を「どく」状態にする。」）

盤面を直接作るテスト（``build_test_state``）は 1 か所の規定を確かめるためのもので、自然な対戦の結果ではない。とくに、
持続する効果を受けた番に進化する・ワザを使う前に進化した番に特殊状態を受けるなどの盤面は、自然な対戦では起こらない
ので、説明に「（盤面を直接作った。自然な対戦では起こらない）」と書く。正式な対戦開始からの試験は
tests/test_stage2_games_v0_4c.py。
"""

import copy
import json
import pickle
import unittest
from types import MappingProxyType

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, Phase, PlaceStartingPokemon, PlayBasicToBench, PlayTrainer,
    ResolveDecision, Retreat, UnsupportedError, UseAttack, apply_command, check_invariants, new_game, state_to_dict,
)
from kyuura_engine.cards import EVOLUTION_STAGES, load_card_pool, pool_from_extract, read_extract, read_verification
from kyuura_engine.conditions import poison
from kyuura_engine.deck import deck_problems
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackEntry, AttackKey, CoinFlipDamage, PoisonOnHeads, SelfDamageOnTails
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import NO_SPECIAL_CONDITIONS, Halt

from tests.helpers import (
    BEEDRILL, CATERPIE, DEFENDER, DEWGONG, DIGLETT, FIGHTING, FIRE, GRASS, GROWLITHE, H, HITMONCHAN, KAKUNA, MACHOP, METAPOD, PARAS,
    PARASECT, PLUSPOWER, PONYTA, RATTATA, SEEL, SWITCH, T, CHARIZARD, WATER, WEEDLE, build_test_state, coin_events, NO_CHARIZARD_EFFECTS,
    no_charizard_pool,
    expand_decklist, with_coin_results,
)

TWINEEDLE_PRINTED = "コインを2枚投げて「おもて」の出た数×30のダメージ。"
TWINEEDLE_LATEST = "コインを2枚投げ、「おもて」の数×30のダメージ。"
POISON_STING = "コインを投げて「おもて」なら、相手を「どく」状態にする。"


def full(state):
    return state_to_dict(state, format_version=8)


def run(state, command):
    new = apply_command(state, command)
    return new, [dict(e) for e in new.log[len(state.log):]]


def kinds(events):
    return [e["kind"] for e in events]


def uid_of(state, player, card_id, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def card_ids(state, uids):
    return [state.cards[u].card_id for u in uids]


def assert_rejected(test, state, command, code, error=IllegalActionError):
    """拒否され、渡した状態（手札・重なり・進化した番・特殊状態・持続する効果・ログ）も乱数も変わらない。"""
    before, fingerprint, log = full(state), rng_fingerprint(state.rng), state.log
    with test.assertRaises(error) as ctx:
        apply_command(state, command)
    test.assertEqual(ctx.exception.code, code)
    test.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
    test.assertIs(state.log, log)


def kakuna(**extra):
    """ビードルから進化したコクーン（進化した番の既定は、今の番より前の持ち主の番）。"""
    return {"card": KAKUNA, "evolved_from": WEEDLE, **extra}


def beedrill(**extra):
    """ビードル → コクーン → スピアーと 2 進化したスピアー（盤面を直接作る。1 進化した番は状態に持たない）。"""
    return {"card": BEEDRILL, "evolved_from": [WEEDLE, KAKUNA], **extra}


def board(active=None, *, bench=(), hand=(BEEDRILL,), opponent=None, opponent_bench=(RATTATA,), turn=5, player=0, prizes=6,
          opponent_prizes=6, **kwargs):
    """プレイヤー ``player`` の番 ``turn`` の盤面（先攻はプレイヤー 0）。既定は 3 番に進化したコクーンと手札のスピアー。"""
    mine = {"active": active or kakuna(energy=[GRASS, GRASS, GRASS]), "bench": list(bench), "hand": list(hand), "prizes": prizes}
    theirs = {"active": opponent or GROWLITHE, "bench": list(opponent_bench), "prizes": opponent_prizes}
    specs = [mine, theirs] if player == 0 else [theirs, mine]
    return build_test_state(specs, current_player=player, turn_number=turn, **kwargs)


def evolve(state, player=0, card_id=BEEDRILL, target=None):
    target = state.players[player].active.pokemon_id if target is None else target
    return run(state, EvolvePokemon(player, uid_of(state, player, card_id), target))


def test_pool(*cards):
    """テスト専用のカード（スピアーの記録を写して変えたもの。実在のカードではない）を加えたカードの組と効果の登録表。

    ``cards`` は (カード id, 記録を変える関数, ワザの登録（位置 → AttackEntry。None ならスピアーと同じ実装）)。"""
    extract = copy.deepcopy(read_extract())
    source = next(c for c in extract["cards"] if c["id"] == BEEDRILL)
    entries = {}
    for card_id, change, attacks in cards:
        record = copy.deepcopy(source)
        record["id"] = card_id
        change(record)
        extract["cards"].append(record)
        extract["pool_v0_4c"].append(card_id)
        attacks = attacks or {index: DEFAULT_EFFECTS.attack_entry(BEEDRILL, index) for index in (0, 1)}
        for index, entry in attacks.items():
            entries[AttackKey(card_id, index)] = entry
    effects = DEFAULT_EFFECTS.with_attacks("test-stage2", entries)
    return pool_from_extract(extract, effects), effects


def protected_opponent(mine=None, harden=H):
    """自然な流れ: 6 番にプレイヤー 1 のコクーンが「かたまる」（コインは ``harden``）を使い、7 番（プレイヤー 0 の番）を返す。
    「おもて」なら 7 番の間、相手のコクーンは「ダメージを受けない」状態（p.21・p.321）。プレイヤー 0 のスピアーは
    5 番に 2 進化したものとして置く（盤面を直接作った）。"""
    state = build_test_state([
        {"active": mine or beedrill(energy=[GRASS, GRASS, GRASS]), "bench": [PONYTA]},
        {"active": kakuna(energy=[GRASS, GRASS]), "bench": [RATTATA]},
    ], current_player=1, turn_number=6)
    state, _ = run(with_coin_results(state, harden), UseAttack(1, 0))
    assert (state.turn_number, state.current_player) == (7, 0)
    return state


# ---------------------------------------------------------------- カード（docs/beedrill-v0.4c.md）


class BeedrillCardTest(unittest.TestCase):
    def test_card_values(self):
        """p.21 で照合した値: 「コクーンから進化」の 2 進化、HP 80、草、弱点 炎（×2）、抵抗力 闘 −30、にげる 0、
        ポケモンパワーなし、ワザ 2 つ（ダブルニードル 無無無 30×、どくばり 草草草 40）。"""
        pool = load_card_pool()
        d = pool.get(BEEDRILL)
        self.assertTrue(d.supported and pool.is_playable(BEEDRILL))
        self.assertTrue(d.is_stage2_pokemon and d.is_evolution_pokemon and not d.is_stage1_pokemon and not d.is_basic_pokemon)
        self.assertEqual((d.name_ja, d.evolves_from, d.hp, d.pokemon_type.value, d.weakness.value, d.resistance.value,
                          d.resistance_value, d.retreat_cost),
                         ("スピアー", "コクーン", 80, "grass", "fire", "fighting", 30, 0))
        self.assertEqual(pool.get(KAKUNA).name_ja, d.evolves_from)
        attacks = [(a.name_ja, [c.value for c in a.cost], a.damage, a.damage_modifier, a.text_ja) for a in d.attacks]
        self.assertEqual(attacks, [
            ("ダブルニードル", ["colorless"] * 3, 30, "×", TWINEEDLE_PRINTED),
            ("どくばり", ["grass"] * 3, 40, None, POISON_STING),
        ])
        self.assertEqual(EVOLUTION_STAGES, ("basic", "stage1", "stage2"))

    def test_registered_attacks_follow_the_verified_latest_description(self):
        """ダブルニードルは CoinFlipDamage（コイン 2 枚・「おもて」1 枚 30）、どくばりは PoisonOnHeads。照合した説明文
        （kyuura の写し）・最新の説明・出典（p.21）と、照合の記録（ワザの位置ごと）が合う。"""
        twineedle = DEFAULT_EFFECTS.attack_entry(BEEDRILL, 0)
        self.assertEqual(twineedle.effect, CoinFlipDamage(coins=2, damage_per_heads=30))
        self.assertEqual((twineedle.name_ja, twineedle.text_ja, twineedle.play_text_ja, twineedle.source),
                         ("ダブルニードル", TWINEEDLE_PRINTED, TWINEEDLE_LATEST, "P43 p.21"))
        sting = DEFAULT_EFFECTS.attack_entry(BEEDRILL, 1)
        self.assertEqual(sting.effect, PoisonOnHeads())
        self.assertEqual((sting.name_ja, sting.text_ja, sting.play_text_ja, sting.source), ("どくばり", POISON_STING, POISON_STING, "P43 p.21"))
        record = read_verification()["cards"][BEEDRILL]
        self.assertEqual((record["status"], record["page"], record["pdf_page"]), ("不一致あり", 21, 23))
        self.assertEqual(record["latest_description_ja"], {"0": TWINEEDLE_LATEST, "1": POISON_STING})
        self.assertEqual(record["card_image_text_ja"]["0"], TWINEEDLE_PRINTED)
        self.assertEqual([m["field"] for m in record["mismatches"]], ["pokemon.attacks[0].text.ja"])

    def test_poison_sting_is_registered_for_beedrill_not_shared_with_weedle(self):
        """ビードルの「どくばり」（p.19。草 1・10）とは別のワザ: スピアーのカード id とワザの位置で登録し、エネルギーと
        ダメージはスピアーのカードの定義（草 3・40）。ビードルの登録を外してもスピアーのどくばりは使える。"""
        pool = load_card_pool()
        weedle, mine = pool.get(WEEDLE).attacks[0], pool.get(BEEDRILL).attacks[1]
        self.assertEqual(weedle.name_ja, mine.name_ja)
        self.assertEqual(([c.value for c in weedle.cost], weedle.damage), (["grass"], 10))
        self.assertEqual(([c.value for c in mine.cost], mine.damage), (["grass"] * 3, 40))
        self.assertIsNot(DEFAULT_EFFECTS.attack_entry(WEEDLE, 0), DEFAULT_EFFECTS.attack_entry(BEEDRILL, 1))
        effects = DEFAULT_EFFECTS.without_attacks("test-no-weedle", [AttackKey(WEEDLE, 0)])
        without = pool_from_extract(read_extract(), effects)
        self.assertFalse(without.is_playable(WEEDLE))
        self.assertTrue(without.is_playable(BEEDRILL))

    def test_stage2_is_not_supported_as_a_whole(self):
        """2 進化の段階を扱えるようになっても、カードごとの条件（ワザの登録・ポケモンパワーなし・進化元の名前）は変わらない。
        実装を登録していないポケモンパワーを持つ 2 進化は未対応のまま。ワザの登録がないスピアーはデッキに入らない。バタフリー
        は v0.4c では写しに入れていなかった（ワザが未実装。docs/architecture-v0.4c.md の v0.4d の準備）。v0.4d で 2 つのワザを
        登録して写し（pool_v0_4d）に加えた（tests/test_butterfree_v0_4d.py）。v0.4e まではフシギバナ（ポケモンパワー・登録の
        ないワザ）で確かめていた。v0.5 でフシギバナのパワーとワザを登録して対応にしたので、カメックス（登録のないポケモン
        パワー「あまごい」）で確かめていた（2 進化だから一括で対応にしたのではない。tests/test_venusaur_v0_5.py）。v0.6 でカメックスの
        パワーとワザを登録して対応にしたので、フーディン（登録のないポケモンパワー「ダメージスワップ」）で確かめていた。v0.7 で
        フーディンのパワーとワザを登録して対応にしたので、リザードン（登録のないポケモンパワー「エナジーバーン」）で確かめる。v0.31 で
        リザードンのパワーとワザを登録して対応にしたので、その 2 つの登録を除いた登録表で分類したカードの組で確かめる（2 進化だから一括で
        対応にしたのではなく、登録で決まる）。"""
        pool = load_card_pool()
        self.assertTrue(pool.get(CHARIZARD).is_stage2_pokemon)
        self.assertTrue(pool.is_playable(CHARIZARD))
        without = no_charizard_pool()
        self.assertFalse(without.is_playable(CHARIZARD))
        self.assertIn("ポケモンパワー", " ".join(without.get(CHARIZARD).unsupported_reasons))
        effects = DEFAULT_EFFECTS.without_attacks("test-no-sting", [AttackKey(BEEDRILL, 1)])
        unregistered = pool_from_extract(read_extract(), effects)
        self.assertFalse(unregistered.is_playable(BEEDRILL))
        self.assertIn("どくばり", " ".join(unregistered.get(BEEDRILL).unsupported_reasons))
        deck = expand_decklist({WEEDLE: 4, KAKUNA: 4, BEEDRILL: 4, GRASS: 48})
        self.assertEqual(deck_problems(deck, load_card_pool()), [])
        self.assertTrue(any(BEEDRILL in problem for problem in deck_problems(deck, unregistered)))
        extract = read_extract()
        self.assertEqual(extract["pool_v0_4c"], [BEEDRILL])
        self.assertEqual(extract["pool_v0_4d"], ["PMCG2-007"])  # バタフリー（v0.4d）

    def test_stage2_without_a_name_or_baby_is_unsupported(self):
        """「○○○○から進化」の名前のない 2 進化、ベイビィ（p.319 の C・D）は未対応（テスト専用のカード）。"""
        def nameless(record):
            record["pokemon"]["evolves_from"] = None

        def baby(record):
            record["pokemon"]["stage"] = "baby"
            record["pokemon"]["evolves_from"] = None
        pool, _ = test_pool(("TEST-NAMELESS-STAGE2", nameless, None), ("TEST-BABY", baby, None))
        self.assertIn("2 進化なのに進化元の名前がない", pool.get("TEST-NAMELESS-STAGE2").unsupported_reasons)
        self.assertTrue(any("ベイビィ" in r for r in pool.get("TEST-BABY").unsupported_reasons))
        self.assertFalse(pool.is_playable("TEST-NAMELESS-STAGE2") or pool.is_playable("TEST-BABY"))


# ---------------------------------------------------------------- 進化の条件（p.309・p.310。20.1）


class Stage2EvolveTest(unittest.TestCase):
    def test_weedle_kakuna_beedrill_over_two_turns(self):
        """例 A（合法）: 3 番にビードル → コクーン、同じ番のスピアーは拒否（例 B。``EVOLVED_THIS_TURN``。p.310 の
        「その番に進化したポケモンをもう一度進化させることはできません」）、次の自分の番（5 番）にコクーン → スピアー。"""
        state = board({"card": WEEDLE, "energy": [GRASS]}, hand=(KAKUNA, BEEDRILL), turn=3)
        weedle = state.players[0].active
        state, events = evolve(state, card_id=KAKUNA)
        self.assertEqual(kinds(events), ["evolve"])
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, BEEDRILL), weedle.pokemon_id), "EVOLVED_THIS_TURN")
        for player in (0, 1):
            state, _ = run(state, EndTurn(player))
        self.assertEqual((state.turn_number, state.current_player), (5, 0))
        kakuna_card = state.players[0].active.card
        beedrill_card = uid_of(state, 0, BEEDRILL)
        state, events = evolve(state)
        self.assertEqual(kinds(events), ["evolve"])
        self.assertEqual(
            {k: events[0][k] for k in ("player", "pokemon_id", "from_card", "from_card_id", "to_card", "to_card_id", "turn")},
            {"player": 0, "pokemon_id": weedle.pokemon_id, "from_card": kakuna_card, "from_card_id": KAKUNA,
             "to_card": beedrill_card, "to_card_id": BEEDRILL, "turn": 5},
        )
        after = state.players[0].active
        self.assertEqual((after.card, after.evolution_stack, after.cards()), (beedrill_card, (weedle.card, kakuna_card),
                                                                             (weedle.card, kakuna_card, beedrill_card)))
        self.assertEqual((after.pokemon_id, after.played_turn, after.evolved_turn), (weedle.pokemon_id, 0, 5))
        self.assertEqual([e["turn"] for e in state.log if e["kind"] == "evolve"], [3, 5])
        self.assertEqual(check_invariants(state), [])

    def test_bench_and_several_pokemon_in_one_turn(self):
        """バトル場・ベンチのどちらでも進化できる。制限は 1 匹ごとで、同じ番にほかのポケモンは進化させられる（p.310
        「1 回の自分の番に、何匹のポケモンを進化させてもかまいません」）。"""
        state = board(bench=[kakuna(), WEEDLE], hand=(BEEDRILL, BEEDRILL, BEEDRILL, KAKUNA))
        active, bench_kakuna, bench_weedle = state.players[0].in_play()
        state, _ = evolve(state, target=active.pokemon_id)
        state, _ = evolve(state, target=bench_kakuna.pokemon_id)
        state, _ = evolve(state, card_id=KAKUNA, target=bench_weedle.pokemon_id)
        self.assertEqual(card_ids(state, [p.card for p in state.players[0].in_play()]), [BEEDRILL, BEEDRILL, KAKUNA])
        self.assertEqual(card_ids(state, state.players[0].bench[0].cards()), [WEEDLE, KAKUNA, BEEDRILL])
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, BEEDRILL), bench_weedle.pokemon_id), "EVOLVED_THIS_TURN")
        self.assertEqual(check_invariants(state), [])

    def test_first_turn_of_each_player(self):
        """おたがいの最初の番（1・2 番）には進化できない（p.310）。名前を見る前に拒否する。"""
        for turn, player in ((1, 0), (2, 1)):
            with self.subTest(turn=turn):
                state = board(WEEDLE, hand=(KAKUNA, BEEDRILL), turn=turn, player=player)
                for card_id in (KAKUNA, BEEDRILL):
                    assert_rejected(self, state, EvolvePokemon(player, uid_of(state, player, card_id), state.players[player].active.pokemon_id),
                                    "FIRST_TURN_EVOLUTION")

    def test_played_this_turn_and_moving_between_active_and_bench(self):
        """今の番に場に出したビードルは進化できない。バトル場とベンチを行き来しても場に出た番は変わらない（p.313。
        場をはなれていない）ので、ベンチのコクーンをにげるでバトル場に出しても 2 進化できる。"""
        state = board(RATTATA, bench=[kakuna(energy=[GRASS])], hand=(WEEDLE, KAKUNA, BEEDRILL))
        state, _ = run(state, PlayBasicToBench(0, uid_of(state, 0, WEEDLE)))
        weedle = state.players[0].bench[-1]
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, KAKUNA), weedle.pokemon_id), "PLAYED_THIS_TURN")
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, BEEDRILL), weedle.pokemon_id), "EVOLUTION_NAME_MISMATCH")
        state = board(RATTATA, bench=[kakuna(played_turn=1, evolved_turn=3)], hand=(BEEDRILL,), turn=5)
        state, _ = run(state, Retreat(0, (), state.players[0].bench[0].card))  # コラッタのにげるは 0
        moved = state.players[0].active
        self.assertEqual((moved.played_turn, moved.evolved_turn), (1, 3))
        state, _ = evolve(state)
        self.assertEqual((state.players[0].active.played_turn, state.players[0].active.evolved_turn), (1, 5))

    def test_name_must_match(self):
        """「コクーンから進化」のスピアーはコクーンにだけ重ねる（p.309・p.324）。ビードル（たねポケモン。たね → 2 進化の直接の
        進化）・キャタピー・トランセル・スピアー・パラス・パラセクトには重ねられない。コクーンにコクーン、コクーンに
        トランセルも重ねられない。"""
        state = board(kakuna(), bench=[WEEDLE, CATERPIE, {"card": METAPOD, "evolved_from": CATERPIE}, beedrill()],
                      hand=(BEEDRILL, KAKUNA, METAPOD), turn=7, opponent_bench=(PARAS,))
        kakuna_pk, weedle, caterpie, metapod, other_beedrill = state.players[0].in_play()
        for card_id, target in ((BEEDRILL, weedle), (BEEDRILL, caterpie), (BEEDRILL, metapod), (BEEDRILL, other_beedrill),
                                (KAKUNA, kakuna_pk), (METAPOD, kakuna_pk), (KAKUNA, other_beedrill)):
            with self.subTest(card=card_id, target=state.cards[target.card].card_id):
                assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, card_id), target.pokemon_id), "EVOLUTION_NAME_MISMATCH")
        parasect = board({"card": PARASECT, "evolved_from": PARAS})
        assert_rejected(self, parasect, EvolvePokemon(0, uid_of(parasect, 0, BEEDRILL), parasect.players[0].active.pokemon_id),
                        "EVOLUTION_NAME_MISMATCH")

    def test_stage_must_match(self):
        """名前は合うが段階が合わない組み合わせ（テスト専用のカード。実在のカードの組では名前で拒否される）: ビードルから
        進化する 2 進化、コクーンから進化する 1 進化は ``EVOLUTION_STAGE_MISMATCH``（p.316・p.319）。不変条件を破る状態を
        作らない。"""
        def stage2_from_weedle(record):
            record["name"]["ja"] = "テストニード"
            record["pokemon"]["evolves_from"] = {"ja": "ビードル", "en": None}

        def stage1_from_kakuna(record):
            record["name"]["ja"] = "テストピアー"
            record["pokemon"]["stage"] = "stage1"
        pool, effects = test_pool(("TEST-STAGE2-FROM-WEEDLE", stage2_from_weedle, None), ("TEST-STAGE1-FROM-KAKUNA", stage1_from_kakuna, None))
        self.assertTrue(pool.is_playable("TEST-STAGE2-FROM-WEEDLE") and pool.is_playable("TEST-STAGE1-FROM-KAKUNA"))
        state = board(WEEDLE, bench=[kakuna()], hand=("TEST-STAGE2-FROM-WEEDLE", "TEST-STAGE1-FROM-KAKUNA"), pool=pool, effects=effects)
        weedle, kakuna_pk = state.players[0].in_play()
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, "TEST-STAGE2-FROM-WEEDLE"), weedle.pokemon_id), "EVOLUTION_STAGE_MISMATCH")
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, "TEST-STAGE1-FROM-KAKUNA"), kakuna_pk.pokemon_id), "EVOLUTION_STAGE_MISMATCH")

    def test_unsupported_stage2_cards(self):
        """対応していない 2 進化カード（未対応のポケモンパワーを持つリザードン（v0.4e まではフシギバナ、v0.5 ではカメックス、v0.6 では
        フーディン。どれも対応にした）・ワザの登録がないスピアー。デッキには入らないので、テストの盤面だけ）は ``UNSUPPORTED_EVOLUTION``。
        v0.31 でリザードンも対応にしたので、その登録を除いた登録表とカードの組の盤面で確かめる。"""
        state = board(hand=(CHARIZARD,), effects=NO_CHARIZARD_EFFECTS, pool=no_charizard_pool())
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, CHARIZARD), state.players[0].active.pokemon_id),
                        "UNSUPPORTED_EVOLUTION", UnsupportedError)
        effects = DEFAULT_EFFECTS.without_attacks("test-no-twineedle", [AttackKey(BEEDRILL, 0)])
        state = board(pool=pool_from_extract(read_extract(), effects), effects=effects)
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, BEEDRILL), state.players[0].active.pokemon_id),
                        "UNSUPPORTED_EVOLUTION", UnsupportedError)

    def test_stage2_cannot_be_played_as_a_basic_pokemon(self):
        """1 進化のない 2 進化: スピアーはたねポケモンではないので、ベンチにも、対戦準備のバトル場・ベンチにも出せない
        （p.308・p.309）。対戦準備の段階では進化もできない。"""
        state = board(hand=(BEEDRILL,))
        assert_rejected(self, state, PlayBasicToBench(0, uid_of(state, 0, BEEDRILL)), "NOT_BASIC_POKEMON")
        deck = expand_decklist({WEEDLE: 4, KAKUNA: 4, BEEDRILL: 4, GRASS: 48})
        for seed in range(300):
            setup = new_game(deck, deck, seed)
            hand = setup.players[0].hand
            beedrills = [u for u in hand if setup.cards[u].card_id == BEEDRILL]
            weedles = [u for u in hand if setup.cards[u].card_id == WEEDLE]
            if beedrills and weedles and setup.phase is Phase.SETUP_PLACEMENT:
                break
        else:
            self.fail("手札にスピアーのある対戦が見つからない")
        assert_rejected(self, setup, PlaceStartingPokemon(0, beedrills[0]), "NOT_BASIC_POKEMON")
        assert_rejected(self, setup, PlaceStartingPokemon(0, weedles[0], (beedrills[0],)), "NOT_BASIC_POKEMON")
        assert_rejected(self, setup, EvolvePokemon(0, beedrills[0], 1), "WRONG_PHASE")

    def test_other_rejections(self):
        """相手のポケモン・場にいない番号・番でないプレイヤー・手札にないカード。どれも状態も乱数も変えない。"""
        state = board(opponent=kakuna(evolved_turn=4), hand=(BEEDRILL,))
        target = state.players[0].active.pokemon_id
        beedrill_card = uid_of(state, 0, BEEDRILL)
        cases = [
            (EvolvePokemon(0, beedrill_card, state.players[1].active.pokemon_id), "TARGET_NOT_YOURS"),
            (EvolvePokemon(0, beedrill_card, 999), "TARGET_NOT_IN_PLAY"),
            (EvolvePokemon(1, beedrill_card, target), "NOT_YOUR_TURN"),
            (EvolvePokemon(0, state.players[0].deck[0], target), "CARD_NOT_IN_HAND"),
            (EvolvePokemon(0, state.players[0].active.card, target), "CARD_NOT_IN_HAND"),
        ]
        for command, code in cases:
            with self.subTest(code=code):
                assert_rejected(self, state, command, code)

    def test_pending_decision_game_over_and_halted(self):
        """決定を待つ間（ポケモンいれかえの途中）・終わった対戦・止めた対戦では 2 進化できない。"""
        state = board(bench=[PONYTA], hand=(BEEDRILL, SWITCH))
        target = state.players[0].active.pokemon_id
        pending, _ = run(state, PlayTrainer(0, uid_of(state, 0, SWITCH)))
        self.assertEqual(pending.phase, Phase.DECISION)
        assert_rejected(self, pending, EvolvePokemon(0, uid_of(pending, 0, BEEDRILL), target), "WRONG_PHASE")
        halted = state.clone()
        halted.phase, halted.halt = Phase.HALTED, Halt("UNRESOLVED_TEST", "テスト", ())
        assert_rejected(self, halted, EvolvePokemon(0, uid_of(state, 0, BEEDRILL), target), "UNRESOLVED_TEST", UnsupportedError)
        won = board(beedrill(energy=[GRASS, GRASS, GRASS]), bench=[kakuna()], hand=(BEEDRILL,), opponent_bench=(), prizes=1, turn=7)
        won, _ = run(with_coin_results(won, H, H), UseAttack(0, 0))  # ダブルニードル 60 でガーディ（HP 60）がきぜつ
        won, _ = run(won, ResolveDecision(0, won.decision.id, (0,)))
        self.assertEqual((won.phase, won.result.winner), (Phase.GAME_OVER, 0))
        assert_rejected(self, won, EvolvePokemon(0, uid_of(won, 0, BEEDRILL), won.players[0].bench[0].pokemon_id), "GAME_OVER")

    def test_same_hp_evolution_and_the_unresolved_hp_case(self):
        """コクーン（HP 80）→ スピアー（HP 80）: 最大 HP が変わらなくても進化でき、ダメージ 70 はそのまま（HP の残り 10）。
        進化したあとの HP がのっているダメージ以下になる場合（HP 70 にしたテスト専用のスピアー）は、v0.4a からの未解決
        （``UNRESOLVED_EVOLUTION_HP``）のまま止める。"""
        new, _ = evolve(board(kakuna(damage=70)))
        after = new.players[0].active
        self.assertEqual((after.damage, new.card_def(after.card).hp), (70, 80))
        self.assertEqual(check_invariants(new), [])

        def low_hp(record):
            record["pokemon"]["hp"] = 70
        pool, effects = test_pool(("TEST-LOW-HP-BEEDRILL", low_hp, None))
        state = board(kakuna(damage=70), hand=("TEST-LOW-HP-BEEDRILL",), pool=pool, effects=effects)
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, "TEST-LOW-HP-BEEDRILL"), state.players[0].active.pokemon_id),
                        "UNRESOLVED_EVOLUTION_HP", UnsupportedError)


# ---------------------------------------------------------------- 3 枚の重なり（20.2）


class ThreeCardStructureTest(unittest.TestCase):
    def evolved(self):
        state = board(kakuna(damage=20, energy=[GRASS, GRASS, GRASS]), bench=[PONYTA])
        return evolve(state)[0]

    def test_stack_order_and_definitions(self):
        """重なりは下から ビードル・コクーン、いちばん上がスピアー。名前・HP・タイプ・弱点・抵抗力・にげる・ワザは
        いちばん上のカードの定義（p.310 の手順 2）。"""
        state = self.evolved()
        me = state.players[0].active
        self.assertEqual(card_ids(state, me.evolution_stack), [WEEDLE, KAKUNA])
        self.assertEqual(card_ids(state, me.cards()), [WEEDLE, KAKUNA, BEEDRILL])
        self.assertEqual(me.cards()[-1], me.card)
        top = state.card_def(me.card)
        self.assertEqual((top.name_ja, top.hp, top.retreat_cost, [a.name_ja for a in top.attacks]),
                         ("スピアー", 80, 0, ["ダブルニードル", "どくばり"]))
        data = full(state)["players"][0]["active"]
        self.assertEqual((data["card_id"], data["name"], data["hp"], data["damage"]), (BEEDRILL, "スピアー", 80, 20))

    def test_only_beedrill_attacks_can_be_used(self):
        """ワザの位置 0 はスピアーのダブルニードル（コクーンの「かたまる」ではない）、位置 1 はどくばり（コクーンの
        「どくのこな」ではない）。位置 2 はない。"""
        state = self.evolved()
        new, events = run(with_coin_results(state, H, T), UseAttack(0, 0))
        attack = next(e for e in events if e["kind"] == "attack")
        self.assertEqual((attack["attack"], len(coin_events(new, len(state.log)))), ("ダブルニードル", 2))
        self.assertNotIn("persistent_effect_added", kinds(events))
        new, events = run(with_coin_results(state, T), UseAttack(0, 1))
        damage = next(e for e in events if e["kind"] == "damage")
        self.assertEqual((next(e for e in events if e["kind"] == "attack")["attack"], damage["amount"]), ("どくばり", 40))
        assert_rejected(self, state, UseAttack(0, 2), "INVALID_ATTACK")

    def test_weakness_resistance_and_retreat_switch_to_beedrill(self):
        """コクーン（抵抗力なし・にげる 2）がスピアー（抵抗力 闘 −30・にげる 0）になると、ワンリキーのけたぐり 20 は
        0 になり、エネルギーをトラッシュせずににげられる。弱点（炎）はどちらも同じ。"""
        def hit(defender, attacker, energy):
            state = build_test_state([
                {"active": defender, "bench": [PONYTA]},
                {"active": {"card": attacker, "energy": energy}, "bench": [RATTATA]},
            ], current_player=1, turn_number=6)
            new, _ = run(state, UseAttack(1, 0))
            return new.players[0].active.damage
        self.assertEqual(hit(kakuna(), MACHOP, [FIGHTING]), 20)
        self.assertEqual(hit(beedrill(), MACHOP, [FIGHTING]), 0)
        self.assertEqual(hit(beedrill(), GROWLITHE, [FIRE, FIRE]), 40)  # ほのお 20 × 2
        state = self.evolved()
        new, events = run(state, Retreat(0, (), state.players[0].bench[0].card))
        self.assertEqual(kinds(events), ["retreat"])
        self.assertEqual(len(new.players[0].bench[0].energy), 3)
        kakuna_state = board(kakuna(energy=[GRASS]), bench=[PONYTA])
        assert_rejected(self, kakuna_state, Retreat(0, (), kakuna_state.players[0].bench[0].card), "WRONG_RETREAT_COST")

    def test_copies_are_independent(self):
        state = self.evolved()
        for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            with self.subTest(copied=type(copied)):
                self.assertEqual(full(copied), full(state))
                self.assertEqual(rng_fingerprint(copied.rng), rng_fingerprint(state.rng))
                copied.players[0].active.evolution_stack = copied.players[0].active.evolution_stack[:1]
                copied.players[0].active.energy.append(999)
                self.assertEqual(len(state.players[0].active.evolution_stack), 2)
                self.assertNotIn(999, state.players[0].active.energy)

    def test_copies_with_a_pending_decision_and_after_a_knock_out(self):
        """決定を待つ間（スピアーのダブルニードルで相手のスピアーがきぜつし、サイドを取る決定）と、2 進化ポケモンのきぜつの
        あと（3 枚がトラッシュ）の状態も、clone・deepcopy・pickle で同じ状態・同じ乱数の続きになり、同じ決定を選べば
        同じ結果になる。"""
        state = board(beedrill(energy=[GRASS, GRASS, GRASS]), opponent=beedrill(damage=30), opponent_bench=(RATTATA,), turn=7)
        knocked = state.players[1].active
        pending, _ = run(with_coin_results(state, H, H), UseAttack(0, 0))
        self.assertEqual((pending.phase, pending.decision.kind), (Phase.TAKE_PRIZE, "take_prize"))
        self.assertTrue(set(knocked.cards()) <= set(pending.players[1].discard))
        results = set()
        for copied in (pending.clone(), copy.deepcopy(pending), pickle.loads(pickle.dumps(pending))):
            with self.subTest(copied=type(copied)):
                self.assertEqual((full(copied), rng_fingerprint(copied.rng)), (full(pending), rng_fingerprint(pending.rng)))
                after, _ = run(copied, ResolveDecision(0, copied.decision.id, (0,)))
                results.add(json.dumps(full(after), sort_keys=True, ensure_ascii=False))
        self.assertEqual(len(results), 1)

    def test_serialization_keeps_format_8(self):
        """形式 7・8 は重なりを下から順のリストで書く（2 つになるだけで、項目と意味は v0.4a と同じ）。形式 1〜6 は重なりを
        表せないので ValueError。2 進化のために新しい形式（9）は加えていない（v0.6 で加えた形式 9 は、あまごいで手札からつけた
        枚数のためのもので、重なりの項目は形式 7〜9 で同じ）。"""
        state = self.evolved()
        me = state.players[0].active
        for version in (7, 8, 9):
            with self.subTest(version=version):
                data = state_to_dict(state, format_version=version)
                pokemon = data["players"][0]["active"]
                self.assertEqual(pokemon["evolution_stack"], [{"card": me.evolution_stack[0], "card_id": WEEDLE},
                                                              {"card": me.evolution_stack[1], "card_id": KAKUNA}])
                self.assertEqual((pokemon["card"], pokemon["card_id"], pokemon["played_turn"], pokemon["evolved_turn"]),
                                 (me.card, BEEDRILL, 0, 5))
                self.assertEqual(json.loads(json.dumps(data)), data)
        for version in range(1, 7):
            with self.subTest(version=version):
                with self.assertRaises(ValueError):
                    state_to_dict(state, format_version=version)
        self.assertEqual(max(FORMAT_VERSIONS), 15)  # v0.4c では 8。9 は v0.6（energy_attached_by_powers_this_turn）、10 は v0.31、11 は v0.44、12 は v0.47、13 は v0.48、14 は v0.49、15 は v0.50

    def test_attach_energy_to_a_card_below_is_rejected(self):
        """場のポケモンはいちばん上のカードの uid で指す（v0.1 からのコマンド）。下の 2 枚は場のポケモンではない。"""
        state = board(hand=(BEEDRILL, GRASS))
        state, _ = evolve(state)
        for below in state.players[0].active.evolution_stack:
            assert_rejected(self, state, AttachEnergy(0, uid_of(state, 0, GRASS), below), "TARGET_NOT_IN_PLAY")
        new, _ = run(state, AttachEnergy(0, uid_of(state, 0, GRASS), state.players[0].active.card))
        self.assertEqual(len(new.players[0].active.energy), 4)


# ---------------------------------------------------------------- 受け継ぐもの（p.310。20.3）


class InheritanceTest(unittest.TestCase):
    def test_damage_energy_identity_and_played_turn(self):
        state = board(kakuna(damage=30, energy=[GRASS, WATER, GRASS], played_turn=1, evolved_turn=3))
        before = state.players[0].active
        new, _ = evolve(state)
        after = new.players[0].active
        self.assertEqual((after.damage, after.energy, after.pokemon_id, after.played_turn, after.evolution_stack[:1]),
                         (30, before.energy, before.pokemon_id, 1, before.evolution_stack))
        self.assertEqual(after.evolution_stack[1], before.card)

    def test_pluspower_and_defender_stay_attached_and_work(self):
        """プラスパワー（自分の番の終わりまで）・ディフェンダー（次の相手の番の終わりまで）をつけたコクーンを 2 進化させても、
        カード・効果・有効期限は変わらない（p.310。SUPPORTED。v0.4a の E8'）。ダブルニードル 60 + 10 = 70。相手の番の
        オーロラビーム 50 − 20 = 30（ジュゴンの水はスピアーの弱点ではない）。"""
        state = board(kakuna(energy=[GRASS, GRASS, GRASS]), hand=(BEEDRILL, PLUSPOWER, DEFENDER),
                      opponent={"card": DEWGONG, "evolved_from": SEEL, "evolved_turn": 4, "energy": [WATER, WATER, WATER]})
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, PLUSPOWER)))
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, DEFENDER)))
        state, _ = run(state, ResolveDecision(0, state.decision.id, (state.players[0].active.pokemon_id,)))
        attached = state.players[0].active.trainers
        self.assertEqual([t.discard_at_end_of_turn for t in attached], [5, 6])
        state, events = evolve(state)
        self.assertEqual(kinds(events), ["evolve"])
        self.assertEqual(state.players[0].active.trainers, attached)
        state, events = run(with_coin_results(state, H, H), UseAttack(0, 0))
        damage = next(e for e in events if e["kind"] == "damage")
        self.assertEqual((damage["amount"], state.players[1].active.damage), (70, 70))  # ジュゴンは HP 80
        self.assertIn(attached[0].card, state.players[0].discard)  # プラスパワーは 5 番の終わりにトラッシュ
        self.assertEqual(state.players[0].active.trainers, attached[1:])
        state, events = run(state, UseAttack(1, 0))
        self.assertEqual(next(e for e in events if e["kind"] == "damage")["amount"], 30)
        self.assertIn(attached[1].card, state.players[0].discard)  # ディフェンダーは 6 番の終わりにトラッシュ
        self.assertEqual(state.players[0].active.trainers, [])


# ---------------------------------------------------------------- 特殊状態（p.310・p.322。20.4）


STATES = {
    "none": {},
    "poison": {"poison": 10},
    "sleep": {"sleep": True},
    "paralysis": {"paralysis": 4},
    "confusion": {"confusion": True},
    "poison+sleep": {"poison": 10, "sleep": True},
    "poison+paralysis": {"poison": 10, "paralysis": 4},
    "poison+confusion": {"poison": 10, "confusion": True},
}


class SpecialConditionsTest(unittest.TestCase):
    def test_every_state_is_cleared(self):
        """8 つの状態のどのコクーンを 2 進化させても、特殊状態はすべて消える（p.310 の手順 3・p.322）。ダメージは消えない。
        コインは投げない。ログは v0.4a と同じ形（``special_conditions_removed``・``reason`` は ``evolve``）。どくも消える
        ので、番の終わりのポケモンチェックでダメージはない。ねむり・マヒが消えたのでワザを使える。（マヒは前の相手の番
        （4 番）に受けた盤面。こんらん・ねむり・マヒのコクーンは、盤面を直接作った）"""
        for name, spec in STATES.items():
            with self.subTest(state=name):
                state = board(kakuna(damage=10, energy=[GRASS, GRASS, GRASS], **spec))
                names = state.players[0].active.conditions.names()
                new, events = evolve(state)
                after = new.players[0].active
                self.assertEqual((after.conditions, after.damage), (NO_SPECIAL_CONDITIONS, 10))
                if names:
                    self.assertEqual(kinds(events), ["evolve", "special_conditions_removed"])
                    removed = events[1]
                    self.assertEqual((removed["conditions"], removed["reason"], removed["pokemon"], removed["pokemon_id"]),
                                     (names, "evolve", after.card, after.pokemon_id))
                else:
                    self.assertEqual(kinds(events), ["evolve"])
                self.assertEqual(check_invariants(new), [])
                attacked, attack_events = run(with_coin_results(new, T), UseAttack(0, 1))  # どくばり（コインは「うら」）
                self.assertIn("attack", kinds(attack_events))
                self.assertNotIn("poison_damage", kinds(attack_events))
                self.assertEqual(attacked.players[0].active.damage, 10)

    def test_condition_given_after_evolving_in_the_same_turn_is_allowed(self):
        """進化したあとで受けた特殊状態は、不変条件で拒否しない（盤面を直接作った: 進化のあとで、どく状態にする処理を
        直接呼ぶ。自然な対戦では、進化した番に自分のポケモンが特殊状態になる対応カードはない）。進化の前の特殊状態が
        残っていれば違反。"""
        state, _ = evolve(board(kakuna(poison=10)))
        poisoned_after = state.clone()
        poison(poisoned_after, 0, poisoned_after.players[0].active, effect="test")
        self.assertEqual(check_invariants(poisoned_after), [])
        broken = state.clone()
        broken.players[0].active.conditions = board(kakuna(poison=10)).players[0].active.conditions
        self.assertTrue(any("進化の前の特殊状態" in p for p in check_invariants(broken)))


# ---------------------------------------------------------------- 持続する効果（p.310・p.323。20.5）


class PersistentEffectsTest(unittest.TestCase):
    def test_evolution_removes_prevent_damage_but_keeps_energy_and_trainers(self):
        """「かたまる」の ``PreventDamage`` を受けたコクーンを 2 進化させると、効果は消える（ログ ``persistent_effect_removed``、
        ``reason`` は ``evolve``）。エネルギー・ディフェンダーは受け継ぐ。効果を与えた番（5 番）が過ぎても、もう一度は
        消さない（盤面を直接作った: 効果を与えた番に進化する。「かたまる」はワザなので、自然な対戦では使った番に進化
        できない）。"""
        state = board(kakuna(energy=[GRASS, GRASS], prevent_damage=5), hand=(BEEDRILL, DEFENDER))
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, DEFENDER)))
        state, _ = run(state, ResolveDecision(0, state.decision.id, (state.players[0].active.pokemon_id,)))
        before = state.players[0].active
        new, events = evolve(state)
        self.assertEqual(kinds(events), ["evolve", "persistent_effect_removed"])
        self.assertEqual((events[1]["reason"], events[1]["persistent_effect"], events[1]["pokemon_id"]),
                         ("evolve", "prevent_damage", before.pokemon_id))
        after = new.players[0].active
        self.assertEqual((after.persistent_effects, after.energy, after.trainers), ((), before.energy, before.trainers))
        for player in (0, 1):
            new, events = run(new, EndTurn(player))
            self.assertNotIn("persistent_effect_removed", kinds(events))
        self.assertEqual(sum(1 for e in new.log if e["kind"] == "persistent_effect_removed"), 1)

    def test_without_an_effect_nothing_is_removed(self):
        _, events = evolve(board())
        self.assertNotIn("persistent_effect_removed", kinds(events))

    def test_expired_effect_is_not_removed_again_by_evolution(self):
        """自然な流れ: 5 番にコクーンの「かたまる」（おもて）→ 6 番に相手のワザは無効 → 6 番の終わりに効果が消える（期限）→
        7 番に 2 進化しても、もう消すものはない。"""
        state = board(kakuna(energy=[GRASS, GRASS]), opponent={"card": GROWLITHE, "energy": [FIRE, FIRE]})
        state, _ = run(with_coin_results(state, H), UseAttack(0, 0))
        state, events = run(state, UseAttack(1, 0))
        self.assertIn("damage_prevented", kinds(events))
        self.assertEqual([e["reason"] for e in events if e["kind"] == "persistent_effect_removed"], ["expired"])
        state, events = evolve(state)
        self.assertEqual(kinds(events), ["evolve"])
        self.assertEqual(state.players[0].active.damage, 0)


# ---------------------------------------------------------------- にげるの失敗の記録（p.310・p.311）


class RetreatFailureTest(unittest.TestCase):
    def failed(self):
        """こんらん状態のコクーンが「にげる」に失敗した（コインが「うら」）盤面（こんらんは盤面を直接作った）。"""
        state = board(kakuna(energy=[GRASS, GRASS, GRASS], confusion=True), bench=[PONYTA], hand=(BEEDRILL, SWITCH, SWITCH))
        active = state.players[0].active
        state, _ = run(with_coin_results(state, T), Retreat(0, tuple(active.energy[:2]), state.players[0].bench[0].card))
        self.assertEqual(state.players[0].active.retreat_failed_turn, 5)
        return state

    def test_stage2_evolution_clears_the_record(self):
        """2 進化でも、進化したポケモンは別のポケモン（p.310）なので記録を消す（v0.4a の R1。SUPPORTED）。特殊状態の解除
        とは別の処理で、ログ ``retreat_failure_cleared``（``reason`` は ``evolve``）。場のポケモンの番号は同じ。そのあと
        スピアー（にげる 0）は「にげる」を宣言でき、コインは投げない。"""
        state = self.failed()
        pokemon_id = state.players[0].active.pokemon_id
        new, events = evolve(state)
        self.assertEqual(kinds(events), ["evolve", "special_conditions_removed", "retreat_failure_cleared"])
        self.assertEqual((events[2]["pokemon_id"], events[2]["reason"]), (pokemon_id, "evolve"))
        after = new.players[0].active
        self.assertEqual((after.retreat_failed_turn, after.conditions, after.pokemon_id), (None, NO_SPECIAL_CONDITIONS, pokemon_id))
        retreated, events = run(new, Retreat(0, (), new.players[0].bench[0].card))
        self.assertNotIn("coin_flip", kinds(events))
        self.assertEqual(retreated.players[0].bench[0].pokemon_id, pokemon_id)

    def test_unresolved_case_is_kept_without_evolution(self):
        """失敗 → ポケモンいれかえでベンチへ → 進化しないでバトル場に戻ると、v0.3c からの未解決
        （``UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED``）のまま。ベンチで 2 進化すれば記録が消え、戻って「にげる」を
        宣言できる。"""
        state = self.failed()
        kakuna_id = state.players[0].active.pokemon_id
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, SWITCH)))
        state, _ = run(state, ResolveDecision(0, state.decision.id, (state.players[0].bench[0].pokemon_id,)))
        back, _ = run(state, PlayTrainer(0, uid_of(state, 0, SWITCH)))
        back, _ = run(back, ResolveDecision(0, back.decision.id, (kakuna_id,)))
        assert_rejected(self, back, Retreat(0, (back.players[0].active.energy[0],), back.players[0].bench[0].card),
                        "UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED", UnsupportedError)
        state, events = evolve(state, target=kakuna_id)
        self.assertEqual(kinds(events), ["evolve", "retreat_failure_cleared"])
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, SWITCH)))
        state, _ = run(state, ResolveDecision(0, state.decision.id, (kakuna_id,)))
        retreated, _ = run(state, Retreat(0, (), state.players[0].bench[0].card))
        self.assertEqual(retreated.players[0].bench[0].pokemon_id, kakuna_id)


# ---------------------------------------------------------------- ダブルニードル（p.21。12・20.6）


class TwineedleTest(unittest.TestCase):
    def attack(self, coins, *, opponent=GROWLITHE, mine=None, hand=(), **kwargs):
        state = board(mine or beedrill(energy=[GRASS, GRASS, GRASS]), hand=hand, opponent=opponent, turn=7, **kwargs)
        for card_id in hand:
            state, _ = run(state, PlayTrainer(0, uid_of(state, 0, card_id)))
        return run(with_coin_results(state, *coins), UseAttack(0, 0))

    def test_heads_count(self):
        """コイン 2 枚（``flip_coins``。ワザの説明の処理の中）、「おもて」の数 × 30。「おもて」が 0 枚なら 0 で、2 段階までで
        計算を終える（ダメージを与えなかった。ワザの失敗ではない: ワザは使ったことになり、番は終わる）。"""
        for coins, amount in (((T, T), 0), ((H, T), 30), ((T, H), 30), ((H, H), 60)):
            with self.subTest(coins=coins):
                new, events = self.attack(coins, opponent=HITMONCHAN)  # HP 70。草の弱点・抵抗力はない
                flips = [e for e in events if e["kind"] == "coin_flip"]
                self.assertEqual([(e["source"], e["effect"], e["player"]) for e in flips], [("attack", f"{BEEDRILL}#0", 0)] * 2)
                damage = next(e for e in events if e["kind"] == "damage")
                self.assertEqual((damage["amount"], new.players[1].active.damage), (amount, amount))
                self.assertEqual(damage.get("stopped_after_step_2", False), amount == 0)
                self.assertEqual(kinds(events)[:2], ["attack", "coin_flip"])
                self.assertIn("turn_end", kinds(events))
                self.assertEqual(new.current_player, 1)

    def test_weakness_and_resistance(self):
        """弱点（ディグダ。草 ×2）と抵抗力（草 −30 のテスト専用のたねポケモン。対応カードに草の抵抗力を持つものはない）。"""
        state = board(beedrill(energy=[GRASS, GRASS, GRASS]), opponent=DIGLETT, turn=7)
        new, events = run(with_coin_results(state, H, T), UseAttack(0, 0))
        self.assertEqual(next(e for e in events if e["kind"] == "damage")["amount"], 60)  # 30 × 2 ≥ HP 30 できぜつ
        self.assertIn("knock_out", kinds(events))

        def grass_resistant(record):
            record["name"]["ja"] = "テストていこう"
            record["pokemon"]["stage"] = "basic"
            record["pokemon"]["evolves_from"] = None
            record["pokemon"]["resistances"] = [{"type": "grass", "operator": "-", "value": 30}]
        pool, effects = test_pool(("TEST-GRASS-RESISTANT", grass_resistant, None))
        for coins, amount in (((H, T), 0), ((H, H), 30)):
            with self.subTest(coins=coins):
                state = board(beedrill(energy=[GRASS, GRASS, GRASS]), opponent="TEST-GRASS-RESISTANT", turn=7, pool=pool, effects=effects)
                new, events = run(with_coin_results(state, *coins), UseAttack(0, 0))
                self.assertEqual(next(e for e in events if e["kind"] == "damage")["amount"], amount)

    def test_pluspower(self):
        """プラスパワー（5 段階）: 1 枚「おもて」で 30 + 10。「おもて」が 0 枚なら 2 段階までで終えるので 0（v0.2d と同じ）。"""
        new, events = self.attack((H, T), hand=(PLUSPOWER,))
        self.assertEqual(next(e for e in events if e["kind"] == "damage")["amount"], 40)
        new, events = self.attack((T, T), hand=(PLUSPOWER,))
        self.assertEqual(next(e for e in events if e["kind"] == "damage")["amount"], 0)

    def test_defender(self):
        """自然な流れ: 6 番に相手がディフェンダーをつけ、7 番にスピアーのダブルニードル 60 − 20 = 40。"""
        state = build_test_state([
            {"active": beedrill(energy=[GRASS, GRASS, GRASS]), "bench": [PONYTA]},
            {"active": GROWLITHE, "bench": [RATTATA], "hand": [DEFENDER]},
        ], current_player=1, turn_number=6)
        state, _ = run(state, PlayTrainer(1, uid_of(state, 1, DEFENDER)))
        state, _ = run(state, ResolveDecision(1, state.decision.id, (state.players[1].active.pokemon_id,)))
        state, _ = run(state, EndTurn(1))
        new, events = run(with_coin_results(state, H, H), UseAttack(0, 0))
        self.assertEqual(next(e for e in events if e["kind"] == "damage")["amount"], 40)

    def test_knock_out_and_prize(self):
        new, events = self.attack((H, H), opponent={"card": GROWLITHE, "damage": 10})
        self.assertIn("knock_out", kinds(events))
        self.assertEqual((new.decision.kind, new.decision.player), ("take_prize", 0))
        new, _ = run(new, ResolveDecision(0, new.decision.id, (0,)))
        self.assertEqual(len(new.players[0].prizes), 5)

    def test_confused_beedrill(self):
        """こんらん（p.309 の手順 5）: こんらんのコインが先。「おもて」ならダブルニードルのコイン 2 枚。「うら」ならワザの
        処理（コイン 2 枚）はせず、自分に 20（弱点・抵抗力だけ。草は自分の弱点・抵抗力ではない）。"""
        state = board(beedrill(energy=[GRASS, GRASS, GRASS], confusion=True), turn=7)
        new, events = run(with_coin_results(state, H, H, T), UseAttack(0, 0))
        flips = [e for e in events if e["kind"] == "coin_flip"]
        self.assertEqual([e["source"] for e in flips], ["confusion", "attack", "attack"])
        self.assertEqual(new.players[1].active.damage, 30)
        new, events = run(with_coin_results(state, T, H, H), UseAttack(0, 0))
        self.assertEqual([e["source"] for e in events if e["kind"] == "coin_flip"], ["confusion"])
        self.assertEqual((new.players[0].active.damage, new.players[1].active.damage), (20, 0))
        self.assertIn("confusion_damage", kinds(events))

    def test_rng_is_reproducible(self):
        """同じ seed・複製・pickle で同じコインの結果（乱数は ``GameState.rng`` だけ）。コインは 1 枚 1 回。"""
        results = set()
        state = board(beedrill(energy=[GRASS, GRASS, GRASS]), turn=7, seed=12)
        for copied in (state, state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state)),
                       board(beedrill(energy=[GRASS, GRASS, GRASS]), turn=7, seed=12)):
            new, events = run(copied, UseAttack(0, 0))
            results.add((tuple(e["result"] for e in events if e["kind"] == "coin_flip"), new.players[1].active.damage,
                         rng_fingerprint(new.rng)))
        self.assertEqual(len(results), 1)


class PreventedTargetTest(unittest.TestCase):
    """「かたまる」で「ダメージを受けない」状態の相手（p.321。v0.4b の未解決裁定を受け継ぐ。13）。"""

    def test_twineedle_against_a_protected_target_is_unresolved(self):
        """コインでダメージの量を決める要素だけのワザ（``CoinFlipDamage``）なので、v0.4b の ``UNRESOLVED_PREVENTED_COIN_DAMAGE``
        がダブルニードルにも当てはまる。拒否の前にコイン（こんらんのコインも）を投げず、状態も乱数も変わらない。"""
        state = protected_opponent()
        self.assertEqual(len(state.players[1].active.persistent_effects), 1)
        assert_rejected(self, state, UseAttack(0, 0), "UNRESOLVED_PREVENTED_COIN_DAMAGE", UnsupportedError)
        confused = protected_opponent(beedrill(energy=[GRASS, GRASS, GRASS], confusion=True))
        assert_rejected(self, confused, UseAttack(0, 0), "UNRESOLVED_PREVENTED_COIN_DAMAGE", UnsupportedError)

    def test_normal_targets_and_expired_effects(self):
        """「かたまる」が「うら」なら通常どおり使える。効果が期限（相手の番の次の番（7 番）の終わり）で消えたら、9 番には
        使える。カード全体が使えないわけではない。"""
        new, events = run(with_coin_results(protected_opponent(harden=T), H, H), UseAttack(0, 0))
        self.assertEqual(new.players[1].active.damage, 60)
        state = protected_opponent()
        state, _ = run(state, EndTurn(0))
        state, _ = run(state, EndTurn(1))
        self.assertEqual((state.turn_number, state.players[1].active.persistent_effects), (9, ()))
        new, events = run(with_coin_results(state, H, T), UseAttack(0, 0))
        self.assertEqual(new.players[1].active.damage, 30)

    def test_poison_sting_against_a_protected_target(self):
        """どくばり: 相手へのダメージの要素は無効（``damage_prevented``）、ダメージ以外の効果の要素（コイン・どく）は有効
        （p.321・コクーンの最新の説明「（ダメージ以外の効果は受ける）」。v0.4b と同じ）。"""
        for coin, poisoned in ((H, True), (T, False)):
            with self.subTest(coin=coin):
                new, events = run(with_coin_results(protected_opponent(), coin), UseAttack(0, 1))
                self.assertEqual([e["kind"] for e in events if e["kind"] in ("damage_prevented", "damage", "coin_flip", "special_condition")],
                                 ["damage_prevented", "coin_flip"] + (["special_condition"] if poisoned else []))
                target = new.players[1].active
                self.assertEqual(target.conditions.poison is not None, poisoned)
                expected = 10 if poisoned else 0  # どくのダメージはポケモンチェックで受ける（p.323。効果は見ない）
                self.assertEqual(target.damage, expected)


# ---------------------------------------------------------------- どくばり（p.21。14・20.6）


class PoisonStingTest(unittest.TestCase):
    def attack(self, coins, *, opponent=GROWLITHE, energy=(GRASS, GRASS, GRASS)):
        state = board(beedrill(energy=list(energy)), opponent=opponent, turn=7)
        return state, *run(with_coin_results(state, *coins), UseAttack(0, 1))

    def test_damage_then_coin_then_poison(self):
        """相手に 40 → コイン → 「おもて」ならどく（ワザの要素の順。p.309・p.320）。番の終わりのポケモンチェックでどくの 10。"""
        for coin, poisoned in ((H, True), (T, False)):
            with self.subTest(coin=coin):
                _, new, events = self.attack((coin,))
                order = [e["kind"] for e in events if e["kind"] in ("damage", "coin_flip", "special_condition", "poison_damage")]
                self.assertEqual(order, ["damage", "coin_flip"] + (["special_condition", "poison_damage"] if poisoned else []))
                self.assertEqual(next(e for e in events if e["kind"] == "damage")["amount"], 40)
                self.assertEqual(new.players[1].active.damage, 50 if poisoned else 40)
                self.assertEqual(new.players[1].active.conditions.poison is not None, poisoned)

    def test_energy_cost(self):
        """どくばりは草 3 個。ダブルニードルは無色 3 個なので、ほかの色でも使える。"""
        state = board(beedrill(energy=[GRASS, GRASS, FIRE]), turn=7)
        assert_rejected(self, state, UseAttack(0, 1), "INSUFFICIENT_ENERGY")
        run(with_coin_results(state, T, T), UseAttack(0, 0))

    def test_knock_out_skips_the_coin(self):
        """相手がこのワザのダメージできぜつしたら、どくにする内容は対象がいないので、コインを投げない（v0.3a と同じ）。"""
        _, new, events = self.attack((H,), opponent={"card": GROWLITHE, "damage": 20})
        self.assertIn("knock_out", kinds(events))
        self.assertNotIn("coin_flip", kinds(events))

    def test_already_poisoned_is_not_doubled(self):
        _, new, _ = self.attack((H,), opponent={"card": GROWLITHE, "poison": 10})
        self.assertEqual(new.players[1].active.damage, 50)  # 40 + どく 10（二重にならない）

    def test_poison_knock_out_at_the_pokemon_check(self):
        """どくばり 40 で 50、ポケモンチェックのどく 10 で 60 ≥ HP 60 → きぜつ。プレイヤー 0 がサイドを取る。"""
        _, new, events = self.attack((H,), opponent={"card": GROWLITHE, "damage": 10})
        knock_out = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual((knock_out["timing"], knock_out["player"]), ("pokemon_check", 1))
        self.assertEqual((new.decision.kind, new.decision.player), ("take_prize", 0))


# ---------------------------------------------------------------- 2 進化ポケモンのきぜつ（p.313・p.323。15・20.7）


class Stage2KnockOutTest(unittest.TestCase):
    def assert_trashed(self, state, before, owner=0):
        """3 枚・エネルギー・ついているトレーナーが 1 回ずつトラッシュにあり、場には残らず、番号は使われない。"""
        discard = state.players[owner].discard
        for uid in (*before.cards(), *before.energy, *(t.card for t in before.trainers)):
            self.assertEqual(discard.count(uid), 1, uid)
        self.assertEqual(card_ids(state, before.cards()), [WEEDLE, KAKUNA, BEEDRILL])
        self.assertIsNone(state.find_pokemon(before.pokemon_id))

    def test_knocked_out_by_an_opponent_attack(self):
        """相手のワザできぜつ: ビードル・コクーン・スピアー・エネルギー・ディフェンダーをすべてトラッシュし、相手はサイドを
        1 枚だけ取る。ベンチのポケモンを出して対戦は続く。ログの ``knock_out`` に下の 2 枚（下から順）。"""
        state = board(beedrill(damage=70, energy=[GRASS, GRASS]), bench=[PONYTA], hand=(DEFENDER,),
                      opponent={"card": GROWLITHE, "energy": [FIRE, FIRE]})
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, DEFENDER)))
        state, _ = run(state, ResolveDecision(0, state.decision.id, (state.players[0].active.pokemon_id,)))
        before = state.players[0].active
        state, _ = run(state, EndTurn(0))
        new, events = run(state, UseAttack(1, 0))  # 20 × 2 − 20 = 20。70 + 20 = 90 ≥ 80
        self.assert_trashed(new, before)
        knock_out = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual((knock_out["pokemon"], knock_out["evolution_stack"], knock_out["discarded_trainers"],
                          knock_out["discarded_energy"]), (before.card, before.evolution_stack, (before.trainers[0].card,), tuple(before.energy)))
        new, _ = run(new, ResolveDecision(1, new.decision.id, (0,)))
        self.assertEqual(len(new.players[1].prizes), 5)  # 重なったカードが 3 枚でもサイドは 1 枚
        self.assertEqual(new.phase, Phase.PROMOTE_ACTIVE)
        next_id = new.next_pokemon_id
        new, _ = run(new, ResolveDecision(0, new.decision.id, (new.players[0].bench[0].pokemon_id,)))
        self.assertEqual((new.next_pokemon_id, check_invariants(new)), (next_id, []))
        self.assertNotIn(before.pokemon_id, [p.pokemon_id for pl in new.players for p in pl.in_play()])

    def test_knocked_out_by_confusion_with_a_persistent_effect(self):
        """こんらんの 20 で自分がきぜつ。持続する効果はカードではないので、トラッシュに何も加えず、ログで消す（``knock_out``）。
        （盤面を直接作った: 効果を与えた番に、スピアーが受けている。スピアーは「かたまる」を持たない）"""
        state = board(beedrill(damage=60, energy=[GRASS, GRASS, GRASS], confusion=True, prevent_damage=7), bench=[PONYTA], turn=7)
        before = state.players[0].active
        new, events = run(with_coin_results(state, T), UseAttack(0, 0))
        self.assert_trashed(new, before)
        self.assertEqual(len(new.players[0].discard), len(state.players[0].discard) + 6)  # 3 枚 + エネルギー 3 枚
        order = [e["kind"] for e in events if e["kind"] in ("confusion_damage", "knock_out", "persistent_effect_removed")]
        self.assertEqual(order, ["confusion_damage", "knock_out", "persistent_effect_removed"])
        self.assertEqual(next(e for e in events if e["kind"] == "persistent_effect_removed")["reason"], "knock_out")
        self.assertEqual((new.decision.kind, new.decision.player), ("take_prize", 1))

    def test_knocked_out_by_poison(self):
        """ポケモンチェックのどくできぜつ（``timing`` は ``pokemon_check``）。3 枚ともトラッシュ。"""
        state = board(beedrill(damage=70, poison=10, energy=[GRASS]), bench=[PONYTA], hand=(), turn=7)
        before = state.players[0].active
        new, events = run(state, EndTurn(0))
        knock_out = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual((knock_out["timing"], knock_out["evolution_stack"]), ("pokemon_check", before.evolution_stack))
        self.assert_trashed(new, before)
        self.assertEqual(new.decision.player, 1)

    def test_knocked_out_by_self_damage(self):
        """ワザによる自分へのダメージできぜつ（対応カードに自分へのダメージのワザを持つ 2 進化はないので、「でんげき」と同じ
        説明のワザを持つテスト専用の 2 進化カードで確かめる。きぜつの処理は ``_finish_attack`` で共通）。"""
        text = "コインを投げて「うら」なら、自分にも10ダメージ。"

        def self_damage(record):
            record["name"]["ja"] = "テストスピアー"
            attack = record["pokemon"]["attacks"][0]
            attack["name"]["ja"] = "テストでんげき"
            attack["damage"] = {"base": 30, "modifier": None, "display": "30"}
            attack["text"]["ja"] = text
        entry = AttackEntry(SelfDamageOnTails(self_damage=10), "テストでんげき", text_ja=text, play_text_ja=text, source="test")
        pool, effects = test_pool(("TEST-SELF-DAMAGE-STAGE2", self_damage, {0: entry, 1: DEFAULT_EFFECTS.attack_entry(BEEDRILL, 1)}))
        state = board(kakuna(damage=70, energy=[GRASS, GRASS, GRASS]), bench=[PONYTA], hand=("TEST-SELF-DAMAGE-STAGE2",),
                      pool=pool, effects=effects)
        state, _ = evolve(state, card_id="TEST-SELF-DAMAGE-STAGE2")
        before = state.players[0].active
        new, events = run(with_coin_results(state, T), UseAttack(0, 0))
        self.assertTrue(set(before.cards()) <= set(new.players[0].discard))
        self.assertEqual(len(before.cards()), 3)
        self.assertIn("knock_out", kinds(events))
        self.assertEqual(check_invariants(new), [])

    def test_beedrill_knocks_out_an_opponent_beedrill(self):
        """ダブルニードル・どくばりで相手のスピアーがきぜつ: 相手の 3 枚をトラッシュし、サイドは 1 枚。相手の最後の
        ポケモンなら対戦が終わる。"""
        for index, coins, damage in ((0, (H, H), 30), (1, (H,), 40)):
            with self.subTest(attack=index):
                state = board(beedrill(energy=[GRASS, GRASS, GRASS]), opponent=beedrill(damage=damage), opponent_bench=(), turn=7)
                before = state.players[1].active
                new, events = run(with_coin_results(state, *coins), UseAttack(0, index))
                self.assertEqual(kinds(events).count("knock_out"), 1)
                self.assertNotIn("special_condition", kinds(events))
                self.assert_trashed(new, before, owner=1)
                new, _ = run(new, ResolveDecision(0, new.decision.id, (0,)))
                self.assertEqual((new.phase, new.result.winner, len(new.players[0].prizes)), (Phase.GAME_OVER, 0, 5))


# ---------------------------------------------------------------- 不変条件（16）


class Stage2InvariantTest(unittest.TestCase):
    def state(self, **spec):
        return build_test_state([
            {"active": beedrill(**spec), "bench": [WEEDLE], "hand": [WEEDLE, KAKUNA, METAPOD, CATERPIE, BEEDRILL]},
            {"active": GROWLITHE},
        ], turn_number=7)

    def assert_problem(self, state, text):
        problems = check_invariants(state)
        self.assertTrue(any(text in problem for problem in problems), problems)

    def rebuild(self, chain):
        """バトル場のスピアーを、下から ``chain`` の順に重ね直す（"weedle_below"・"kakuna_below"・"top" はもとの 3 枚、カード
        id は手札のカード）。使わなかったもとのカードは手札に入れて、カードの数を合わせる。"""
        state = self.state()
        hand = state.players[0].hand
        active = state.players[0].active
        own = {"weedle_below": active.evolution_stack[0], "kakuna_below": active.evolution_stack[1], "top": active.card}
        resolved = []
        for item in chain:
            if item in own:
                resolved.append(own.pop(item))
            else:
                uid = uid_of(state, 0, item)
                hand.remove(uid)
                resolved.append(uid)
        hand.extend(own.values())
        active.evolution_stack, active.card = tuple(resolved[:-1]), resolved[-1]
        return state

    def test_valid_states(self):
        self.assertEqual(check_invariants(self.state()), [])
        self.assertEqual(check_invariants(self.state(evolved_turn=7, played_turn=1)), [])
        self.assertEqual(check_invariants(self.rebuild(("weedle_below", "kakuna_below", "top"))), [])

    def test_wrong_stacks(self):
        """たねに 2 進化・1 進化だけ・2 進化だけ・違う名前・1 進化の上に 1 進化・2 進化の上に 1 進化・2 進化の上に 2 進化・
        たねの上にたね・4 枚を見つける（いちばん上だけでなく、隣り合うすべての 2 枚と段階を確かめる）。"""
        cases = {
            "たねに 2 進化": (("weedle_below", "top"), "重なりが正しくない"),
            "1 進化だけ": ((KAKUNA,), "たねポケモンではない"),
            "2 進化だけ": (("top",), "たねポケモンではない"),
            "違う名前（キャタピー・コクーン）": ((CATERPIE, "kakuna_below", "top"), "重なりが正しくない"),
            "1 進化の上に 1 進化": (("weedle_below", "kakuna_below", KAKUNA), "重なりが正しくない"),
            "1 進化の上に別の 1 進化": (("weedle_below", "kakuna_below", METAPOD), "重なりが正しくない"),
            "2 進化の上に 1 進化": (("weedle_below", "top", KAKUNA), "重なりが正しくない"),
            "2 進化の上に 2 進化": (("weedle_below", "top", BEEDRILL), "重なりが正しくない"),
            "たねの上にたね": (("weedle_below", WEEDLE), "重なりが正しくない"),
            "4 枚": (("weedle_below", "kakuna_below", "top", BEEDRILL), "4 枚のカードが重なっている"),
            "たねが上": (("kakuna_below", "weedle_below"), "たねポケモンではない"),
        }
        for name, (chain, text) in cases.items():
            with self.subTest(case=name):
                self.assert_problem(self.rebuild(chain), text)
        self.assert_problem(self.rebuild(("weedle_below", "kakuna_below", "top", BEEDRILL)), "重なりが正しくない")

    def test_duplicates_and_conservation(self):
        state = self.state()
        twice = state.clone()
        twice.players[0].active.evolution_stack = (state.players[0].active.evolution_stack[0],) * 2
        twice.players[0].hand.append(state.players[0].active.evolution_stack[1])
        self.assert_problem(twice, "2 か所")
        lost = state.clone()
        lost.players[0].active.evolution_stack = lost.players[0].active.evolution_stack[1:]
        self.assert_problem(lost, "どこにもないカード")
        ids = state.clone()
        ids.players[0].bench[0].pokemon_id = ids.players[0].active.pokemon_id
        self.assert_problem(ids, "番号が重なっている")

    def test_turns_without_the_log(self):
        """状態だけで確かめられること: 2 進化した番の前に、場に出た番・2 番より後の持ち主の番（1 進化した番）がある。"""
        for spec in ({"evolved_turn": 3}, {"evolved_turn": 5, "played_turn": 3}, {"evolved_turn": 7, "played_turn": 5}):
            with self.subTest(spec=spec):
                self.assert_problem(self.state(**spec), "1 進化できる持ち主の番がない")
        self.assertEqual(check_invariants(self.state(evolved_turn=7, played_turn=3)), [])

    def test_turns_with_the_log(self):
        """ログ ``evolve`` との対応: 同じ番に 2 回進化したログ・重なりと違うカードのログ・重なりより多いログを見つける
        （状態だけでは、5 番に 1 進化と 2 進化をした場合を見つけられない）。"""
        state = board({"card": WEEDLE, "energy": [GRASS]}, hand=(KAKUNA, BEEDRILL), turn=5)
        state, _ = evolve(state, card_id=KAKUNA)
        for player in (0, 1):
            state, _ = run(state, EndTurn(player))
        state, _ = evolve(state)
        self.assertEqual(check_invariants(state), [])

        def edited(change):
            broken = state.clone()
            events = [dict(e) for e in broken.log]
            change(broken, events)
            broken.log = tuple(MappingProxyType(e) for e in events)
            return broken

        def same_turn(broken, events):
            first = next(e for e in events if e["kind"] == "evolve")
            first["turn"] = 7
        self.assert_problem(edited(same_turn), "同じ番に二度は進化できない")

        def wrong_card(broken, events):
            next(e for e in events if e["kind"] == "evolve")["to_card"] = broken.players[0].active.card
        self.assert_problem(edited(wrong_card), "対応しない")

        def extra(broken, events):
            events.append({**next(e for e in events if e["kind"] == "evolve")})
        self.assert_problem(edited(extra), "進化のログが 3 回")

        def last_turn(broken, events):
            broken.players[0].active.evolved_turn = 5
        self.assert_problem(edited(last_turn), "最後の進化のログは 7 番")


# ---------------------------------------------------------------- 原子性（20.8）


class AtomicityTest(unittest.TestCase):
    def test_rejected_stage2_evolutions_change_nothing(self):
        """不正な 2 進化は、手札・カード・重なり・進化した番・特殊状態・持続する効果・乱数・ログを変えない（どく・こんらん・
        「かたまる」の効果を受けたコクーンは、盤面を直接作った）。"""
        # v0.31: リザードンを対応にしたので、その登録を除いた登録表とカードの組の盤面（tests/helpers.py の NO_CHARIZARD_EFFECTS）
        state = board(kakuna(poison=10, confusion=True, prevent_damage=5), hand=(BEEDRILL, KAKUNA, CHARIZARD), effects=NO_CHARIZARD_EFFECTS,
                      pool=no_charizard_pool())
        target = state.players[0].active.pokemon_id
        for command, code, error in (
            (EvolvePokemon(0, uid_of(state, 0, KAKUNA), target), "EVOLUTION_NAME_MISMATCH", IllegalActionError),
            # 未対応の 2 進化（v0.4e まではフシギバナ、v0.5 ではカメックス、v0.6 ではフーディン。v0.7 でフーディンを対応にしたので、
            # 未対応のポケモンパワーを持つリザードン）
            (EvolvePokemon(0, uid_of(state, 0, CHARIZARD), target), "UNSUPPORTED_EVOLUTION", UnsupportedError),
            (EvolvePokemon(1, uid_of(state, 0, BEEDRILL), target), "NOT_YOUR_TURN", IllegalActionError),
            (EvolvePokemon(0, uid_of(state, 0, BEEDRILL), state.players[1].active.pokemon_id), "TARGET_NOT_YOURS", IllegalActionError),
        ):
            with self.subTest(code=code):
                assert_rejected(self, state, command, code, error)
        self.assertEqual(state.players[0].active.conditions.names(), ("poison", "confusion"))
        self.assertEqual(len(state.players[0].active.persistent_effects), 1)
        # たねポケモンに 2 進化（ビードルにスピアー）
        weedle = board({"card": WEEDLE, "poison": 10}, hand=(BEEDRILL,))
        assert_rejected(self, weedle, EvolvePokemon(0, uid_of(weedle, 0, BEEDRILL), weedle.players[0].active.pokemon_id),
                        "EVOLUTION_NAME_MISMATCH")
        # 同じ番の再進化。進化のあとで受けた特殊状態も消さない（盤面を直接作った）
        same_turn = board({"card": WEEDLE, "energy": [GRASS]}, hand=(KAKUNA, BEEDRILL), turn=3)
        same_turn, _ = evolve(same_turn, card_id=KAKUNA)
        poison(same_turn, 0, same_turn.players[0].active, effect="test")
        assert_rejected(self, same_turn, EvolvePokemon(0, uid_of(same_turn, 0, BEEDRILL), same_turn.players[0].active.pokemon_id),
                        "EVOLVED_THIS_TURN")

    def test_successful_evolution_does_not_change_the_input(self):
        state = board(kakuna(confusion=True, prevent_damage=5))
        before, fingerprint = full(state), rng_fingerprint(state.rng)
        evolve(state)
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))


if __name__ == "__main__":
    unittest.main()

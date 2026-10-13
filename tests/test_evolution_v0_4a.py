"""進化（v0.4a）: たねポケモン → 1 進化ポケモン。パラス → パラセクト、パウワウ → ジュゴン。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES・status_on_evolve・
first_turn_evolution）。分類（CONFIRMED・SUPPORTED・UNRESOLVED）は docs/evolution-rules-v0.4a.md、カードの照合は
docs/evolution-cards-v0.4a.md、状態の持ち方は docs/evolution-state-v0.4a.md。

- p.309「場にいるポケモンを進化させる」: 手札の「○○○○から進化」の進化カードを、その名前のポケモンに重ねる
- p.310: 進化の手順 1〜5（下のカードはトラッシュしない・特殊状態と持続する効果から回復・マーカーを取りのぞく）、
  「その番の最初から場に出ていた」ポケモンだけ、おたがいの最初の番には進化できない、別のポケモンとしてあつかわれる、
  同じ番にもう一度は進化できない、エネルギー・つけて使うトレーナー・ダメージカウンターは受け継ぐ、複数を進化させて
  よい、特殊状態のポケモンも進化させてよい
- p.313・p.319: 進化ポケモンは重なったカードで構成され、場をはなれたら構成していたカードにもどる
- p.321: 5・7 段階（ついているカードの効果）と 2・8 段階（ポケモンが持っている効果）を分ける
- p.322・p.323: 特殊状態・持続する効果は進化したら消える。持続する効果の例はワザ（すなかけ・まるまる）
- p.324: 書かれていない組み合わせでカードを重ねてはいけない
- p.39（パラセクト）・p.102（ジュゴン）: カードのページ
"""

import copy
import json
import pickle
import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, Phase, PlaceStartingPokemon, PlayBasicToBench,
    PlayTrainer, ResolveDecision, Retreat, UnsupportedError, UseAttack, apply_command, check_invariants, new_game,
    state_to_dict,
)
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract, read_verification
from kyuura_engine.conditions import poison
from kyuura_engine.deck import deck_problems
from kyuura_engine.effects import DAMAGE_ONLY, DEFAULT_EFFECTS, AttackEntry, AttackKey, PutToSleep
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import NO_SPECIAL_CONDITIONS, Halt, Poison, SpecialConditions

from tests.helpers import (
    DEFENDER, DEWGONG, DIGLETT, FIRE, GRASS, GROWLITHE, H, PARAS, PARASECT, PLUSPOWER, PONYTA, RATTATA, SEEL,
    SWITCH, T, CHARIZARD, WATER, build_test_state, expand_decklist, with_coin_results,
)

SPORE = "相手を「ねむり」状態にする。"
ICE_BEAM = "コインを投げて「おもて」なら、相手を「マヒ」状態にする。"


def full(state):
    return state_to_dict(state, format_version=7)


def kinds(events):
    return [e["kind"] for e in events]


def run(state, command):
    new = apply_command(state, command)
    return new, [dict(e) for e in new.log[len(state.log):]]


def uid_of(state, player, card_id, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def assert_rejected(test, state, command, code, error=IllegalActionError):
    """拒否され、渡した状態も乱数も変わらない（進化カードは手札、進化元はそのまま）。"""
    before, fingerprint = full(state), rng_fingerprint(state.rng)
    with test.assertRaises(error) as ctx:
        apply_command(state, command)
    test.assertEqual(ctx.exception.code, code)
    test.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))


def board(active=PARAS, *, bench=(), hand=(PARASECT,), opponent=None, opponent_bench=(RATTATA,), turn=3, player=0, prizes=6,
          **kwargs):
    """プレイヤー ``player`` の番 ``turn`` の盤面（先攻はプレイヤー 0）。既定はパラス（対戦準備から場にいる）と手札のパラセクト。"""
    mine = {"active": active, "bench": list(bench), "hand": list(hand), "prizes": prizes}
    theirs = {"active": opponent or GROWLITHE, "bench": list(opponent_bench)}
    specs = [mine, theirs] if player == 0 else [theirs, mine]
    return build_test_state(specs, current_player=player, turn_number=turn, **kwargs)


def evolve(state, player=0, card_id=PARASECT, target=None):
    target = state.players[player].active.pokemon_id if target is None else target
    return run(state, EvolvePokemon(player, uid_of(state, player, card_id), target))


def test_pool(*cards, attacks=None):
    """テスト専用のカード（パラセクトの記録を写して変えたもの）を加えたカードの組と、効果の登録表。"""
    extract = copy.deepcopy(read_extract())
    source = next(c for c in extract["cards"] if c["id"] == PARASECT)
    entries = {}
    for card_id, change in cards:
        record = copy.deepcopy(source)
        record["id"] = card_id
        change(record)
        extract["cards"].append(record)
        extract["pool_v0_4a"].append(card_id)
        entries[AttackKey(card_id, 0)] = AttackEntry(PutToSleep(), "キノコのほうし", text_ja=SPORE, play_text_ja=SPORE, source="P43 p.39")
        entries[AttackKey(card_id, 1)] = AttackEntry(DAMAGE_ONLY, "きりさく")
    effects = DEFAULT_EFFECTS.with_attacks("test-evolution", entries)
    return pool_from_extract(extract, effects), effects


# ---------------------------------------------------------------- カード（docs/evolution-cards-v0.4a.md）


class EvolutionCardsTest(unittest.TestCase):
    def test_parasect_and_dewgong(self):
        """p.39・p.102 で照合した値。1 進化で、進化元の名前・HP・タイプ・弱点・抵抗力・にげる・ワザがデータと同じ。"""
        pool = load_card_pool()
        expected = {
            PARASECT: ("パラセクト", "パラス", 60, "grass", "fire", 1, [("キノコのほうし", "put_to_sleep"), ("きりさく", "damage_only")], 39),
            DEWGONG: ("ジュゴン", "パウワウ", 80, "water", "lightning", 3,
                      [("オーロラビーム", "damage_only"), ("れいとうビーム", "paralyze_on_heads")], 102),
        }
        records = read_verification()["cards"]
        for card_id, (name, base, hp, kind, weakness, retreat, attacks, page) in expected.items():
            with self.subTest(card=card_id):
                d = pool.get(card_id)
                self.assertTrue(pool.is_playable(card_id))
                self.assertTrue(d.is_stage1_pokemon and not d.is_basic_pokemon)
                self.assertEqual((d.name_ja, d.evolves_from, d.hp, d.pokemon_type.value, d.weakness.value, d.resistance, d.retreat_cost),
                                 (name, base, hp, kind, weakness, None, retreat))
                for index, (attack_name, implementation) in enumerate(attacks):
                    entry = DEFAULT_EFFECTS.attack_entry(card_id, index)
                    self.assertEqual((d.attacks[index].name_ja, entry.effect.implementation_id), (attack_name, implementation))
                self.assertEqual((records[card_id]["status"], records[card_id]["page"]), ("一致", page))
        # 説明文は照合した最新の説明（パラスのキノコのほうし・キャタピーのいとをはくと同じ文面）
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(PARASECT, 0).play_text_ja, SPORE)
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(DEWGONG, 1).play_text_ja, ICE_BEAM)
        self.assertEqual(pool.get(PARAS).name_ja, "パラス")
        self.assertEqual(pool.get(SEEL).name_ja, "パウワウ")

    def test_unsupported_evolution_cards(self):
        """実装を登録していないポケモンパワーを持つ 2 進化・ワザの登録がない 1 進化は、デッキに入れられない（効果がないもの
        として扱わない）。"""
        pool = load_card_pool()
        # v0.4a〜v0.4e はフシギバナで確かめていた。v0.4a は理由の最初が「2 進化」、v0.4c で 2 進化の段階を扱えるようにしてからは
        # ポケモンパワー（と登録のないワザ）だった。v0.5 でフシギバナ（エナジートランス・ソーラービーム）を対応にしたので、実装を
        # 登録していないポケモンパワー「あまごい」を持つ 2 進化のカメックスで確かめていた（tests/test_venusaur_v0_5.py）。v0.6 で
        # カメックスを対応にしたので、登録していないポケモンパワー「ダメージスワップ」を持つ 2 進化のフーディンで確かめていた。v0.7 で
        # フーディンを対応にしたので、登録していないポケモンパワー「エナジーバーン」を持つ 2 進化のリザードンで確かめる
        self.assertFalse(pool.get(CHARIZARD).supported)
        self.assertIn("ポケモンパワー", pool.get(CHARIZARD).unsupported_reasons[0])
        effects = DEFAULT_EFFECTS.without_attacks("test-no-dewgong", [AttackKey(DEWGONG, 1)])
        unregistered = pool_from_extract(read_extract(), effects)
        self.assertFalse(unregistered.is_playable(DEWGONG))
        deck = expand_decklist({SEEL: 4, DEWGONG: 2, WATER: 54})
        self.assertTrue(any("UNSUPPORTED_CARD" in problem for problem in deck_problems(deck, unregistered)))
        self.assertEqual(deck_problems(deck, pool), [])


# ---------------------------------------------------------------- 17.1 進化の条件（p.309・p.310）


class EvolveTest(unittest.TestCase):
    def test_evolve_the_active_pokemon(self):
        """パラスがパラセクトになる: いちばん上のカードが変わり、パラスのカードは下に残る（トラッシュしない）。番は続く。"""
        state = board(active={"card": PARAS, "energy": [GRASS]})
        paras = state.players[0].active
        parasect = uid_of(state, 0, PARASECT)
        fingerprint = rng_fingerprint(state.rng)
        new, events = evolve(state)
        evolved = new.players[0].active
        self.assertEqual((evolved.card, evolved.evolution_stack, evolved.pokemon_id), (parasect, (paras.card,), paras.pokemon_id))
        self.assertEqual((evolved.played_turn, evolved.evolved_turn, evolved.current_form_turn), (0, 3, 3))
        self.assertEqual(evolved.cards(), (paras.card, parasect))
        self.assertNotIn(parasect, new.players[0].hand)
        self.assertNotIn(paras.card, new.players[0].discard)
        self.assertEqual(kinds(events), ["evolve"])
        e = events[0]
        self.assertEqual((e["player"], e["pokemon_id"], e["from_card"], e["from_card_id"], e["to_card"], e["to_card_id"], e["turn"]),
                         (0, paras.pokemon_id, paras.card, PARAS, parasect, PARASECT, 3))
        self.assertEqual(rng_fingerprint(new.rng), fingerprint)  # 進化は乱数を使わない
        self.assertEqual((new.phase, new.current_player, new.turn_number, new.decision), (Phase.MAIN, 0, 3, None))
        self.assertEqual(new.card_def(evolved.card).name_ja, "パラセクト")
        self.assertEqual(check_invariants(new), [])

    def test_evolve_a_bench_pokemon_and_several_in_one_turn(self):
        """ベンチのポケモンも進化できる。1 回の番に複数のポケモンを進化させてよい（p.310）。"""
        state = board(active=SEEL, bench=[PARAS, PARAS], hand=[PARASECT, PARASECT, DEWGONG])
        for target in [b.pokemon_id for b in state.players[0].bench] + [state.players[0].active.pokemon_id]:
            card_id = DEWGONG if target == state.players[0].active.pokemon_id else PARASECT
            state, _ = run(state, EvolvePokemon(0, uid_of(state, 0, card_id), target))
        p = state.players[0]
        self.assertEqual([state.cards[pk.card].card_id for pk in p.in_play()], [DEWGONG, PARASECT, PARASECT])
        self.assertEqual([state.cards[pk.evolution_stack[0]].card_id for pk in p.in_play()], [SEEL, PARAS, PARAS])
        self.assertEqual(p.hand, [])

    def test_first_turn_of_each_player(self):
        """おたがいのプレイヤーの最初の番（先攻の 1 番・後攻の 2 番）には進化できない（p.310。kyuura first_turn_evolution）。"""
        for turn, player in ((1, 0), (2, 1)):
            with self.subTest(turn=turn):
                state = board(turn=turn, player=player)
                assert_rejected(self, state, EvolvePokemon(player, uid_of(state, player, PARASECT), state.players[player].active.pokemon_id),
                                "FIRST_TURN_EVOLUTION")
        # 先攻の 2 回目の番（3 番）・後攻の 2 回目の番（4 番）にはできる
        for turn, player in ((3, 0), (4, 1)):
            with self.subTest(turn=turn):
                new, _ = evolve(board(turn=turn, player=player), player=player)
                self.assertEqual(new.cards[new.players[player].active.card].card_id, PARASECT)

    def test_pokemon_played_this_turn_cannot_evolve(self):
        """今の番に場に出したポケモンは「その番の最初」には場にいなかったので進化できない（p.310）。前の番に出していればよい。"""
        state = board(active=SEEL, hand=[PARASECT, PARAS])
        state, _ = run(state, PlayBasicToBench(0, uid_of(state, 0, PARAS)))
        played = state.players[0].bench[0]
        self.assertEqual(played.played_turn, 3)
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, PARASECT), played.pokemon_id), "PLAYED_THIS_TURN")
        new, _ = evolve(board(active={"card": PARAS, "played_turn": 1}))
        self.assertEqual(new.players[0].active.played_turn, 1)
        # バトル場とベンチを行き来しても場をはなれていないので、場に出た番は変わらない（p.313）
        state = board(active={"card": SEEL, "energy": [WATER]}, bench=[{"card": PARAS, "played_turn": 1}])
        state, _ = run(state, Retreat(0, (state.players[0].active.energy[0],), state.players[0].bench[0].card))
        self.assertEqual(state.players[0].active.played_turn, 1)
        new, _ = evolve(state)
        self.assertEqual(new.players[0].active.evolved_turn, 3)

    def test_pokemon_evolved_this_turn_cannot_evolve_again(self):
        """今の番に進化したポケモンは別のポケモンで、その番の最初には場にいなかったことになる（p.310）。v0.4a の対応カードに
        2 進化はないので、パラセクトから進化するテスト専用のカードで確かめる（状態を変える前に拒否）。"""
        def from_parasect(record):
            record["name"]["ja"] = "テストセクト"
            record["pokemon"]["evolves_from"] = {"ja": "パラセクト", "en": None}
        pool, effects = test_pool(("TEST-FROM-PARASECT", from_parasect))
        state = board(hand=[PARASECT, "TEST-FROM-PARASECT"], pool=pool, effects=effects)
        state, _ = evolve(state)
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, "TEST-FROM-PARASECT"), state.players[0].active.pokemon_id),
                        "EVOLVED_THIS_TURN")

    def test_name_must_match(self):
        """「○○○○から進化」の名前のポケモンにだけ重ねる（p.309・p.324）。パラス以外をパラセクトに、パウワウ以外を
        ジュゴンにできない。進化したパラセクトに、もう 1 枚のパラセクトは重ねられない。"""
        state = board(active=SEEL, bench=[PARAS, DIGLETT], hand=[PARASECT, DEWGONG, PARASECT])
        seel, paras, diglett = state.players[0].in_play()
        for card_id, target in ((PARASECT, seel), (PARASECT, diglett), (DEWGONG, paras)):
            with self.subTest(card=card_id, target=state.cards[target.card].card_id):
                assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, card_id), target.pokemon_id), "EVOLUTION_NAME_MISMATCH")
        evolved = build_test_state([{"active": {"card": PARASECT, "evolved_from": PARAS}, "hand": [PARASECT]}, {"active": GROWLITHE}])
        assert_rejected(self, evolved, EvolvePokemon(0, uid_of(evolved, 0, PARASECT), evolved.players[0].active.pokemon_id),
                        "EVOLUTION_NAME_MISMATCH")

    def test_rejected_commands(self):
        """不正な進化は、状態も乱数も変えない（カードは手札に、進化元は場に残る）。"""
        state = board(hand=[PARASECT, PARAS, GRASS, SWITCH, CHARIZARD], opponent=PARAS)
        target = state.players[0].active.pokemon_id
        parasect = uid_of(state, 0, PARASECT)
        opponent = state.players[1].active
        cases = [
            (EvolvePokemon(0, uid_of(state, 0, PARAS), target), "NOT_EVOLUTION_CARD", IllegalActionError),  # たねポケモン
            (EvolvePokemon(0, uid_of(state, 0, GRASS), target), "NOT_EVOLUTION_CARD", IllegalActionError),
            (EvolvePokemon(0, uid_of(state, 0, SWITCH), target), "NOT_EVOLUTION_CARD", IllegalActionError),
            # 未対応の 2 進化（v0.4e まではフシギバナ、v0.5 ではカメックス、v0.6 ではフーディン。v0.7 でフーディンを対応にしたので、
            # 未対応のポケモンパワーを持つリザードン）
            (EvolvePokemon(0, uid_of(state, 0, CHARIZARD), target), "UNSUPPORTED_EVOLUTION", UnsupportedError),
            (EvolvePokemon(0, state.players[0].deck[0], target), "CARD_NOT_IN_HAND", IllegalActionError),
            (EvolvePokemon(0, parasect, opponent.pokemon_id), "TARGET_NOT_YOURS", IllegalActionError),  # 相手のパラス
            (EvolvePokemon(0, parasect, 999), "TARGET_NOT_IN_PLAY", IllegalActionError),
            (EvolvePokemon(0, parasect, 0), "TARGET_NOT_IN_PLAY", IllegalActionError),
            (EvolvePokemon(1, parasect, target), "NOT_YOUR_TURN", IllegalActionError),
            (EvolvePokemon(2, parasect, target), "INVALID_PLAYER", IllegalActionError),
            (EvolvePokemon(0, parasect, True), "BAD_COMMAND", IllegalActionError),
        ]
        for command, code, error in cases:
            with self.subTest(command=command, code=code):
                assert_rejected(self, state, command, code, error)

    def test_target_is_the_pokemon_id_not_a_card_uid(self):
        """``target`` は場のポケモンの番号として読む。カードの uid（パラスのカード）を渡しても、その番号の場のポケモンが
        いなければ拒否する（uid と番号は別の数なので、たまたま同じ数の番号の場のポケモンがいれば、そのポケモンを指す）。"""
        state = board(active={"card": SEEL, "energy": [WATER] * 6}, bench=[PARAS], hand=[PARASECT])
        paras = state.players[0].bench[0]
        self.assertNotIn(paras.card, [pk.pokemon_id for p in state.players for pk in p.in_play()])
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, PARASECT), paras.card), "TARGET_NOT_IN_PLAY")
        new, _ = run(state, EvolvePokemon(0, uid_of(state, 0, PARASECT), paras.pokemon_id))
        self.assertEqual(new.cards[new.players[0].bench[0].card].card_id, PARASECT)

    def test_unregistered_stage1_card(self):
        """登録表にワザの実装がない 1 進化カード（テストの盤面だけで起こる）は ``UNSUPPORTED_EVOLUTION``。"""
        effects = DEFAULT_EFFECTS.without_attacks("test-no-dewgong", [AttackKey(DEWGONG, 1)])
        pool = pool_from_extract(read_extract(), effects)
        state = board(active=SEEL, hand=[DEWGONG], pool=pool, effects=effects)
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, DEWGONG), state.players[0].active.pokemon_id),
                        "UNSUPPORTED_EVOLUTION", UnsupportedError)

    def test_evolution_cards_cannot_be_played_as_basic_pokemon(self):
        """進化カードは、手札からバトル場・ベンチに直接出せない（対戦準備でも）。たねポケモンではない（p.308・p.309）。"""
        state = board(hand=[PARASECT])
        assert_rejected(self, state, PlayBasicToBench(0, uid_of(state, 0, PARASECT)), "NOT_BASIC_POKEMON")
        deck = expand_decklist({PARAS: 4, PARASECT: 4, GRASS: 52})
        for seed in range(200):
            setup = new_game(deck, deck, seed)
            hand = setup.players[0].hand
            parasects = [u for u in hand if setup.cards[u].card_id == PARASECT]
            basics = [u for u in hand if setup.cards[u].card_id == PARAS]
            if parasects and basics and setup.phase is Phase.SETUP_PLACEMENT:
                break
        else:
            self.fail("手札にパラセクトのある対戦が見つからない")
        assert_rejected(self, setup, PlaceStartingPokemon(0, parasects[0]), "NOT_BASIC_POKEMON")
        assert_rejected(self, setup, PlaceStartingPokemon(0, basics[0], (parasects[0],)), "NOT_BASIC_POKEMON")
        assert_rejected(self, setup, EvolvePokemon(0, parasects[0], 1), "WRONG_PHASE")

    def test_no_evolution_while_a_decision_is_pending_or_after_the_game(self):
        """決定を待つ間（ポケモンいれかえの途中）は進化できない。終わった対戦・止めた対戦も受け付けない。"""
        state = board(bench=[PONYTA], hand=[PARASECT, SWITCH])
        target = state.players[0].active.pokemon_id
        pending, _ = run(state, PlayTrainer(0, uid_of(state, 0, SWITCH)))
        self.assertEqual(pending.phase, Phase.DECISION)
        assert_rejected(self, pending, EvolvePokemon(0, uid_of(pending, 0, PARASECT), target), "WRONG_PHASE")
        halted = state.clone()
        halted.phase, halted.halt = Phase.HALTED, Halt("UNRESOLVED_TEST", "テスト", ())
        assert_rejected(self, halted, EvolvePokemon(0, uid_of(state, 0, PARASECT), target), "UNRESOLVED_TEST", UnsupportedError)
        # 勝敗が決まった対戦: 相手の最後のサイドを取って終わらせる
        won = board(active={"card": GROWLITHE, "energy": [FIRE, FIRE]}, bench=[PARAS], hand=[PARASECT],
                    opponent={"card": DIGLETT, "damage": 20}, opponent_bench=(), prizes=1)
        won, _ = run(won, UseAttack(0, 0))
        won, _ = run(won, ResolveDecision(0, won.decision.id, (0,)))
        self.assertEqual(won.phase, Phase.GAME_OVER)
        assert_rejected(self, won, EvolvePokemon(0, uid_of(won, 0, PARASECT), won.players[0].bench[0].pokemon_id), "GAME_OVER")

    def test_damage_at_or_above_the_new_hp_is_unresolved(self):
        """進化したあとの HP がのっているダメージ以下になる場合、きぜつの扱いが原典で決められないので止める（v0.4a の
        対応カードでは HP が増えるので起こらない。HP 30 にしたテスト専用のパラセクトで確かめる）。"""
        def low_hp(record):
            record["pokemon"]["hp"] = 30
        pool, effects = test_pool(("TEST-LOW-HP-PARASECT", low_hp))
        state = board(active={"card": PARAS, "damage": 30}, hand=["TEST-LOW-HP-PARASECT"], pool=pool, effects=effects)
        assert_rejected(self, state, EvolvePokemon(0, uid_of(state, 0, "TEST-LOW-HP-PARASECT"), state.players[0].active.pokemon_id),
                        "UNRESOLVED_EVOLUTION_HP", UnsupportedError)
        state = board(active={"card": PARAS, "damage": 20}, hand=["TEST-LOW-HP-PARASECT"], pool=pool, effects=effects)
        new, _ = evolve(state, card_id="TEST-LOW-HP-PARASECT")
        self.assertEqual(new.players[0].active.damage, 20)


# ---------------------------------------------------------------- 17.3 受け継ぐもの（p.310）


class InheritanceTest(unittest.TestCase):
    def test_damage_energy_and_identity(self):
        """ダメージカウンター・エネルギー（uid と順番）・場のポケモンの番号・場に出た番を受け継ぐ。HP はパラセクトの 60。"""
        state = board(active={"card": PARAS, "damage": 30, "energy": [GRASS, WATER, GRASS], "played_turn": 1})
        before = state.players[0].active
        new, _ = evolve(state)
        after = new.players[0].active
        self.assertEqual((after.damage, after.energy, after.pokemon_id, after.played_turn), (30, before.energy, before.pokemon_id, 1))
        self.assertEqual(new.card_def(after.card).hp - after.damage, 30)  # パラスなら HP 40 で残り 10
        self.assertEqual(state_to_dict(new, format_version=7)["players"][0]["active"]["hp"], 60)

    def test_pluspower_stays_attached_and_works(self):
        """プラスパワーはついたまま（p.310）、有効期限も変わらず、進化したポケモンのワザで +10（p.257・p.321 の 5 段階。
        カードの効果で、進化で消える「持続する効果」ではない。SUPPORTED）。番の終わりにトラッシュ。"""
        state = board(active={"card": PARAS, "energy": [GRASS, GRASS, GRASS]}, hand=[PARASECT, PLUSPOWER], opponent=GROWLITHE)
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, PLUSPOWER)))
        attached = state.players[0].active.trainers
        state, _ = evolve(state)
        self.assertEqual(state.players[0].active.trainers, attached)
        new, events = run(state, UseAttack(0, 1))  # きりさく 30 + 10
        damage = next(e for e in events if e["kind"] == "damage")
        self.assertEqual((damage["amount"], len(damage["modifiers"])), (40, 1))
        self.assertEqual(new.players[1].active.damage, 40)
        self.assertIn(attached[0].card, new.players[0].discard)  # 自分の番の終わりにトラッシュ

    def test_defender_stays_attached_until_the_next_opponent_turn(self):
        """ディフェンダーをつけたパラスを進化させても、カード・効果（−20。p.321 の 7 段階）・有効期限（次の相手の番の終わり）
        は変わらない（SUPPORTED）。"""
        state = board(active={"card": PARAS, "energy": [GRASS]}, hand=[PARASECT, DEFENDER],
                      opponent={"card": GROWLITHE, "energy": [FIRE, FIRE]})
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, DEFENDER)))
        state, _ = run(state, ResolveDecision(0, state.decision.id, (state.players[0].active.pokemon_id,)))
        attached = state.players[0].active.trainers
        self.assertEqual(attached[0].discard_at_end_of_turn, 4)
        state, _ = evolve(state)
        self.assertEqual(state.players[0].active.trainers, attached)
        state, _ = run(state, EndTurn(0))
        new, events = run(state, UseAttack(1, 0))  # ほのお 20 → 弱点（炎）×2 = 40 → ディフェンダー −20 = 20
        damage = next(e for e in events if e["kind"] == "damage")
        self.assertEqual(damage["amount"], 20)
        self.assertIn(attached[0].card, new.players[0].discard)  # 4 番の終わりにトラッシュ
        self.assertEqual(new.players[0].active.trainers, [])


# ---------------------------------------------------------------- 17.4 特殊状態（p.310・p.322）


STATES = {
    "none": {},
    "poison": {"poison": 10},
    "sleep": {"sleep": True},
    "poison+sleep": {"poison": 10, "sleep": True},
    "paralysis": {"paralysis": 2},
    "poison+paralysis": {"poison": 10, "paralysis": 2},
    "confusion": {"confusion": True},
    "poison+confusion": {"poison": 10, "confusion": True},
}


class SpecialConditionsTest(unittest.TestCase):
    def test_every_state_is_cleared(self):
        """8 つの状態のどれから進化しても、特殊状態はすべて消える（p.310 の手順 3・p.322。kyuura status_on_evolve の
        2000年の行）。ダメージカウンターは消えない。コインは投げない。ねむり・マヒから進化すればワザを使える。"""
        for name, spec in STATES.items():
            with self.subTest(state=name):
                state = board(active={"card": PARAS, "damage": 10, "energy": [GRASS, GRASS], **spec})
                names = state.players[0].active.conditions.names()
                new, events = evolve(state)
                after = new.players[0].active
                self.assertEqual((after.conditions, after.damage), (NO_SPECIAL_CONDITIONS, 10))
                removed = [e for e in events if e["kind"] == "special_conditions_removed"]
                if names:
                    self.assertEqual(kinds(events), ["evolve", "special_conditions_removed"])
                    self.assertEqual((removed[0]["conditions"], removed[0]["reason"], removed[0]["pokemon"]), (names, "evolve", after.card))
                else:
                    self.assertEqual(kinds(events), ["evolve"])
                self.assertNotIn("coin_flip", kinds(events))
                self.assertEqual(check_invariants(new), [])
                # キノコのほうし（ねむり・マヒが消えたので使える）。番の終わりの相手のねむりのコインは「うら」にしておく
                attacked, attack_events = run(with_coin_results(new, T), UseAttack(0, 0))
                self.assertIn("attack", kinds(attack_events))
                self.assertTrue(attacked.players[1].active.conditions.asleep)
                self.assertEqual(attacked.players[0].active.damage, 10)  # どくも消えたので、ポケモンチェックでダメージはない


# ---------------------------------------------------------------- 17.5 にげるの失敗の記録（p.310・p.311）


class RetreatFailureTest(unittest.TestCase):
    def failed(self):
        """こんらん状態のパラスが「にげる」に失敗した（コインが「うら」）盤面。"""
        state = board(active={"card": PARAS, "energy": [GRASS, GRASS], "confusion": True}, bench=[PONYTA], hand=[PARASECT, SWITCH, SWITCH])
        state = with_coin_results(state, T)
        active = state.players[0].active
        state, _ = run(state, Retreat(0, (active.energy[0],), state.players[0].bench[0].card))
        self.assertEqual(state.players[0].active.retreat_failed_turn, 3)
        return state

    def test_evolving_clears_the_record(self):
        """失敗のあと同じ番に進化すると、こんらんが消え、記録も消える（進化したポケモンは別のポケモン。p.310。p.311 の主語を
        どちらに読んでも宣言できる。SUPPORTED）。そのあと「にげる」を宣言でき、コインは投げない。"""
        state = self.failed()
        new, events = evolve(state)
        after = new.players[0].active
        self.assertEqual((after.retreat_failed_turn, after.conditions), (None, NO_SPECIAL_CONDITIONS))
        self.assertEqual(kinds(events), ["evolve", "special_conditions_removed", "retreat_failure_cleared"])
        cleared = events[-1]
        self.assertEqual((cleared["pokemon_id"], cleared["reason"]), (after.pokemon_id, "evolve"))
        retreated, events = run(new, Retreat(0, (after.energy[0],), new.players[0].bench[0].card))
        self.assertNotIn("coin_flip", kinds(events))
        self.assertEqual(retreated.players[0].bench[0].pokemon_id, after.pokemon_id)

    def test_no_record_no_clearing_event(self):
        for spec in ({}, {"confusion": True}):
            with self.subTest(spec=spec):
                new, events = evolve(board(active={"card": PARAS, **spec}))
                self.assertNotIn("retreat_failure_cleared", kinds(events))
                self.assertIsNone(new.players[0].active.retreat_failed_turn)

    def test_evolving_on_the_bench_after_the_confusion_was_cleared(self):
        """失敗 → ポケモンいれかえでベンチへ（こんらんは消え、記録は残る）→ ベンチで進化（記録が消える）→ ポケモンいれかえで
        バトル場へ → 「にげる」を宣言できる。進化しないで戻った場合は、v0.3c からの未解決（UNRESOLVED_RETREAT_AFTER_
        CONFUSION_CLEARED）のまま。"""
        state = self.failed()
        paras_id = state.players[0].active.pokemon_id
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, SWITCH)))
        state, _ = run(state, ResolveDecision(0, state.decision.id, (state.players[0].bench[0].pokemon_id,)))
        benched = state.find_pokemon(paras_id)[1]
        self.assertEqual((benched.retreat_failed_turn, benched.conditions), (3, NO_SPECIAL_CONDITIONS))
        not_evolved, _ = run(state, PlayTrainer(0, uid_of(state, 0, SWITCH)))
        not_evolved, _ = run(not_evolved, ResolveDecision(0, not_evolved.decision.id, (paras_id,)))
        assert_rejected(self, not_evolved, Retreat(0, (not_evolved.players[0].active.energy[0],), not_evolved.players[0].bench[0].card),
                        "UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED", UnsupportedError)
        state, events = evolve(state, target=paras_id)
        self.assertEqual(kinds(events), ["evolve", "retreat_failure_cleared"])
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, SWITCH)))
        state, _ = run(state, ResolveDecision(0, state.decision.id, (paras_id,)))
        retreated, _ = run(state, Retreat(0, (state.players[0].active.energy[0],), state.players[0].bench[0].card))
        self.assertEqual(retreated.players[0].bench[0].pokemon_id, paras_id)

    def test_invariant_detects_a_record_left_after_evolving(self):
        """進化で記録を消さない不具合は、不変条件（記録はログの retreat_failed と対応し、進化より後）で見つかる。"""
        state, _ = evolve(self.failed())
        state.players[0].active.retreat_failed_turn = 3
        self.assertTrue(any("進化（ログ evolve）の前" in problem for problem in check_invariants(state)))


# ---------------------------------------------------------------- 17.6 進化したあとのワザ・カードの定義（p.310）


class EvolvedPokemonTest(unittest.TestCase):
    def test_paras_attacks_are_no_longer_available(self):
        """進化前のワザは使えない。ワザの位置はパラセクトのカードのもの（0 はキノコのほうし、1 はきりさく）。"""
        state = board(active={"card": PARAS, "energy": [GRASS, GRASS]})
        before, _ = run(state, UseAttack(0, 0))  # パラスの 0 番はひっかく（20）
        self.assertEqual(before.players[1].active.damage, 20)
        state, _ = evolve(state)
        after, events = run(with_coin_results(state, T), UseAttack(0, 0))  # パラセクトの 0 番はキノコのほうし（ダメージなし・ねむり）
        attack = next(e for e in events if e["kind"] == "attack")
        self.assertEqual(attack["attack"], "キノコのほうし")
        self.assertEqual((after.players[1].active.damage, after.players[1].active.conditions.asleep), (0, True))
        self.assertNotIn("damage", kinds(events))
        assert_rejected(self, state, UseAttack(0, 1), "INSUFFICIENT_ENERGY")  # きりさくは無色 3

    def test_slash_and_weakness(self):
        """きりさく 30。弱点はワザを使うポケモン（パラセクト。草）のタイプで見る（ディグダは草 ×2。p.321）。"""
        state = board(active={"card": PARAS, "energy": [GRASS, GRASS, GRASS]}, opponent=DIGLETT)
        state, _ = evolve(state)
        new, events = run(state, UseAttack(0, 1))
        damage = next(e for e in events if e["kind"] == "damage")
        self.assertEqual((damage["amount"], damage["weakness"]), (60, True))
        self.assertEqual(new.players[1].active, None)  # ディグダ（HP 30）はきぜつ
        state = board(active={"card": PARASECT, "evolved_from": PARAS, "energy": [GRASS, GRASS, GRASS]},
                      opponent={"card": GROWLITHE, "energy": [FIRE]}, hand=[], turn=5)
        self.assertEqual(run(state, UseAttack(0, 1))[0].players[1].active.damage, 30)

    def test_hp_and_retreat_cost_come_from_the_top_card(self):
        """HP・にげるエネルギーはいちばん上のカードのもの。パウワウ（HP 60・にげる 1）→ ジュゴン（HP 80・にげる 3）。"""
        state = board(active={"card": SEEL, "damage": 50, "energy": [WATER, WATER, WATER]}, bench=[PONYTA], hand=[DEWGONG])
        state, _ = evolve(state, card_id=DEWGONG)
        dewgong = state.players[0].active
        self.assertEqual(state.card_def(dewgong.card).hp, 80)
        assert_rejected(self, state, Retreat(0, (dewgong.energy[0],), state.players[0].bench[0].card), "WRONG_RETREAT_COST")
        new, _ = run(state, Retreat(0, tuple(dewgong.energy), state.players[0].bench[0].card))
        self.assertEqual(new.players[0].bench[0].pokemon_id, dewgong.pokemon_id)

    def test_ice_beam(self):
        """れいとうビーム: 相手に 30 → コインが「おもて」なら相手をマヒに（キャタピーのいとをはくと同じ実装）。"""
        for side in (H, T):
            with self.subTest(side=side):
                state = board(active={"card": DEWGONG, "evolved_from": SEEL, "energy": [WATER] * 4}, hand=[], opponent=SEEL, turn=5)
                new, events = run(with_coin_results(state, side), UseAttack(0, 1))
                self.assertEqual(new.players[1].active.damage, 30)
                self.assertEqual(new.players[1].active.conditions.paralyzed, side is H)

    def test_confused_evolved_pokemon(self):
        """進化したあとにこんらん状態になったポケモン（盤面を作る）: こんらんのコインが「うら」なら、自分（パラセクト。草・弱点 炎）
        に 20（弱点・抵抗力は関係しない）。HP 以上ならきぜつし、重なったカードもトラッシュ。"""
        state = board(active={"card": PARASECT, "evolved_from": PARAS, "damage": 40, "energy": [GRASS, GRASS], "confusion": True},
                      bench=[PONYTA], hand=[], turn=5)
        evolved = state.players[0].active
        new, events = run(with_coin_results(state, T), UseAttack(0, 0))
        confusion = next(e for e in events if e["kind"] == "confusion_damage")
        self.assertEqual((confusion["amount"], confusion["weakness"]), (20, False))
        self.assertTrue(set(evolved.cards()) <= set(new.players[0].discard))
        knock_out = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual((knock_out["pokemon"], knock_out["evolution_stack"]), (evolved.card, evolved.evolution_stack))


# ---------------------------------------------------------------- 17.7 進化したポケモンのきぜつ（p.313・p.319・p.323）


class EvolvedKnockOutTest(unittest.TestCase):
    def test_knocked_out_by_an_attack(self):
        """相手のワザできぜつ: パラセクト・パラス・エネルギー・ディフェンダーをすべてトラッシュし、相手はサイドを 1 枚だけ
        取る（きぜつしたのは 1 匹）。ベンチのポケモンを出して対戦は続く。"""
        state = board(active={"card": PARASECT, "evolved_from": PARAS, "damage": 50, "energy": [GRASS]}, bench=[PONYTA],
                      hand=[DEFENDER], opponent={"card": GROWLITHE, "energy": [FIRE, FIRE]}, turn=5)
        evolved = state.players[0].active
        state, _ = run(state, PlayTrainer(0, uid_of(state, 0, DEFENDER)))
        state, _ = run(state, ResolveDecision(0, state.decision.id, (evolved.pokemon_id,)))
        defender = state.players[0].active.trainers[0].card
        state, _ = run(state, EndTurn(0))
        new, events = run(state, UseAttack(1, 0))  # 20 → ×2 → −20 = 20。50 + 20 = 70 ≥ 60
        discard = new.players[0].discard
        for uid in (*evolved.cards(), *evolved.energy, defender):
            self.assertEqual(discard.count(uid), 1)
        self.assertIsNone(new.find_pokemon(evolved.pokemon_id))
        knock_out = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual((knock_out["pokemon"], knock_out["evolution_stack"], knock_out["discarded_trainers"]),
                         (evolved.card, evolved.evolution_stack, (defender,)))
        self.assertEqual((new.phase, new.decision.player, len(new.players[1].prizes)), (Phase.TAKE_PRIZE, 1, 6))
        new, _ = run(new, ResolveDecision(1, new.decision.id, (0,)))
        self.assertEqual(len(new.players[1].prizes), 5)  # 重なったカードが 2 枚でもサイドは 1 枚
        self.assertEqual(new.phase, Phase.PROMOTE_ACTIVE)
        new, _ = run(new, ResolveDecision(0, new.decision.id, (new.players[0].bench[0].pokemon_id,)))
        self.assertEqual(check_invariants(new), [])

    def test_last_pokemon_knocked_out_ends_the_game(self):
        state = board(active={"card": GROWLITHE, "energy": [FIRE, FIRE]}, hand=[], opponent={"card": PARASECT, "evolved_from": PARAS,
                      "damage": 50}, opponent_bench=(), turn=5)
        new, _ = run(state, UseAttack(0, 0))
        new, _ = run(new, ResolveDecision(0, new.decision.id, (0,)))
        self.assertEqual((new.phase, new.result.winner), (Phase.GAME_OVER, 0))
        self.assertEqual(len(new.players[0].prizes), 5)
        self.assertEqual(sorted(state.cards[u].card_id for u in new.players[1].discard), sorted([PARAS, PARASECT]))

    def test_knocked_out_by_poison(self):
        """進化したあとにどく状態になったポケモン（盤面を作る）が、ポケモンチェックのどくできぜつ。重なったカードもトラッシュ。"""
        state = board(active={"card": PARASECT, "evolved_from": PARAS, "damage": 50, "poison": 10}, bench=[PONYTA], hand=[], turn=5)
        evolved = state.players[0].active
        new, events = run(state, EndTurn(0))
        knock_out = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual((knock_out["timing"], knock_out["evolution_stack"]), ("pokemon_check", evolved.evolution_stack))
        self.assertTrue(set(evolved.cards()) <= set(new.players[0].discard))
        self.assertEqual(new.decision.player, 1)

    def test_not_evolved_knock_out_log_is_unchanged(self):
        """進化していないポケモンのきぜつのログは v0.3d と同じ形（evolution_stack の項目がない）。"""
        state = board(active={"card": GROWLITHE, "energy": [FIRE, FIRE]}, hand=[], opponent={"card": PARAS, "damage": 30})
        new, events = run(state, UseAttack(0, 0))
        knock_out = next(e for e in events if e["kind"] == "knock_out")
        self.assertNotIn("evolution_stack", knock_out)


# ---------------------------------------------------------------- 17.2 カードの重なり・複製・書き出し


class StackAndSerializationTest(unittest.TestCase):
    def evolved(self):
        state = board(active={"card": PARAS, "damage": 20, "energy": [GRASS]}, hand=[PARASECT])
        return evolve(state)[0]

    def test_copies_are_independent(self):
        state = self.evolved()
        for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            with self.subTest(copied=type(copied)):
                self.assertEqual(full(copied), full(state))
                self.assertEqual(copied.players[0].active.evolution_stack, state.players[0].active.evolution_stack)
                copied.players[0].active.evolution_stack = ()
                copied.players[0].active.energy.append(999)
                self.assertEqual(len(state.players[0].active.evolution_stack), 1)
                self.assertNotIn(999, state.players[0].active.energy)

    def test_format_7(self):
        state = self.evolved()
        active = state.players[0].active
        data = state_to_dict(state, format_version=7)
        pokemon = data["players"][0]["active"]
        self.assertEqual(data["format_version"], 7)
        self.assertEqual((pokemon["card"], pokemon["card_id"], pokemon["name"], pokemon["hp"]), (active.card, PARASECT, "パラセクト", 60))
        self.assertEqual(pokemon["evolution_stack"], [{"card": active.evolution_stack[0], "card_id": PARAS}])
        self.assertEqual((pokemon["played_turn"], pokemon["evolved_turn"], pokemon["damage"]), (0, 3, 20))
        self.assertEqual(json.loads(json.dumps(data)), data)
        self.assertIn(7, FORMAT_VERSIONS)

    def test_older_formats_refuse_evolved_pokemon(self):
        """形式 1〜6 は重なりを表せないので、黙って落とさずに ValueError。進化していない状態は今までどおり書き出せる。"""
        state = self.evolved()
        for version in range(1, 7):
            with self.subTest(version=version):
                with self.assertRaises(ValueError):
                    state_to_dict(state, format_version=version)
        plain = board()
        for version in range(1, 8):
            state_to_dict(plain, format_version=version)
        six, seven = state_to_dict(plain, format_version=6), state_to_dict(plain, format_version=7)
        for data in (six, seven):
            data.pop("format_version")
        for p6, p7 in zip(six["players"], seven["players"]):
            for pokemon in [p7["active"], *p7["bench"]]:
                self.assertEqual((pokemon.pop("evolution_stack"), pokemon.pop("evolved_turn")), ([], None))
                pokemon.pop("played_turn")
        self.assertEqual(six, seven)  # 形式 7 は形式 6 に項目を加えただけ

    def test_knocked_out_evolved_pokemon_can_be_written_in_older_formats(self):
        """進化したポケモンがきぜつしてトラッシュに移れば、重なりはもうない（カードはトラッシュの uid として書ける）。"""
        state = board(active={"card": GROWLITHE, "energy": [FIRE, FIRE]}, hand=[],
                      opponent={"card": PARASECT, "evolved_from": PARAS, "damage": 50}, turn=5)
        new, _ = run(state, UseAttack(0, 0))
        state_to_dict(new, format_version=6)


# ---------------------------------------------------------------- 14.3 不変条件


class EvolutionInvariantTest(unittest.TestCase):
    def evolved(self, **spec):
        return build_test_state([{"active": {"card": PARASECT, "evolved_from": PARAS, **spec}, "bench": [SEEL]}, {"active": GROWLITHE}],
                                turn_number=5)

    def assert_problem(self, state, text):
        problems = check_invariants(state)
        self.assertTrue(any(text in problem for problem in problems), problems)

    def test_valid_states(self):
        self.assertEqual(check_invariants(self.evolved()), [])
        self.assertEqual(check_invariants(self.evolved(evolved_turn=3, played_turn=1)), [])

    def test_card_conservation(self):
        state = self.evolved()
        below = state.players[0].active.evolution_stack[0]
        duplicate = state.clone()
        duplicate.players[0].hand.append(below)
        self.assert_problem(duplicate, "2 か所")
        top_twice = state.clone()
        top_twice.players[0].active.evolution_stack = (state.players[0].active.card,)
        self.assert_problem(top_twice, "2 か所")
        missing = state.clone()
        missing.players[0].active.evolution_stack = ()
        self.assert_problem(missing, "どこにもないカード")
        self.assert_problem(missing, "たねポケモンではない")
        unknown = state.clone()
        unknown.players[0].active.evolution_stack = (999,)
        self.assert_problem(unknown, "未知のカード")

    def test_wrong_stacks(self):
        state = self.evolved()
        seel = state.players[0].bench[0]
        wrong_base = state.clone()  # パラセクトの下にパウワウ（ベンチのパウワウと入れ替えて数を合わせる）
        wrong_base.players[0].active.evolution_stack, wrong_base.players[0].bench[0].card = (seel.card,), state.players[0].active.evolution_stack[0]
        self.assert_problem(wrong_base, "重なりが正しくない")
        three = state.clone()  # 3 枚（v0.4a は 1 進化まで）
        three.players[0].active.evolution_stack = (*state.players[0].active.evolution_stack, seel.card)
        three.players[0].bench = []
        self.assert_problem(three, "3 枚のカード")
        basic_on_basic = state.clone()
        basic_on_basic.players[0].bench = []
        basic_on_basic.players[0].active.card, basic_on_basic.players[0].active.evolution_stack = seel.card, (state.players[0].active.evolution_stack[0],)
        basic_on_basic.players[0].hand.append(state.players[0].active.card)
        self.assert_problem(basic_on_basic, "重なりが正しくない")

    def test_turn_fields(self):
        for spec, text in (
            ({"evolved_turn": 7}, "進化した番 7"),  # 今の番（5）より後
            ({"evolved_turn": 1}, "最初の番"),
            ({"evolved_turn": 4}, "持ち主の番でない"),
            ({"evolved_turn": 3, "played_turn": 3}, "場に出た番 3 より後"),
            ({"played_turn": 9}, "場に出た番 9"),
        ):
            with self.subTest(spec=spec):
                self.assert_problem(self.evolved(**spec), text)
        state = self.evolved()
        state.players[0].active.evolved_turn = None
        self.assert_problem(state, "進化した番がない")
        plain = build_test_state([{"active": PARAS}, {"active": GROWLITHE}])
        plain.players[0].active.evolved_turn = 3
        self.assert_problem(plain, "進化していないのに、進化した番")
        plain.players[0].active.evolved_turn = None
        plain.players[0].active.evolution_stack = "x"
        self.assert_problem(plain, "整数のタプルではない")

    def test_conditions_left_after_evolving(self):
        """今の番に進化したポケモンに、進化の前の特殊状態が残っていれば違反。進化のあとで付けられたものはよい。"""
        state, _ = evolve(board(active={"card": PARAS, "poison": 10}))
        broken = state.clone()
        broken.players[0].active.conditions = SpecialConditions(poison=Poison(10))
        self.assert_problem(broken, "進化の前の特殊状態")
        poisoned_after = state.clone()
        poison(poisoned_after, 0, poisoned_after.players[0].active, effect="test")
        self.assertEqual(check_invariants(poisoned_after), [])

    def test_pokemon_ids_stay_unique(self):
        state = self.evolved()
        state.players[0].bench[0].pokemon_id = state.players[0].active.pokemon_id
        self.assert_problem(state, "番号が重なっている")


# ---------------------------------------------------------------- 原子性（17.8）


class EvolutionAtomicityTest(unittest.TestCase):
    def test_successful_evolution_does_not_change_the_input(self):
        state = board(active={"card": PARAS, "energy": [GRASS], "confusion": True})
        before, fingerprint = full(state), rng_fingerprint(state.rng)
        evolve(state)
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))

    def test_attach_energy_to_the_card_below_is_rejected(self):
        """場のポケモンはいちばん上のカードの uid で指す（v0.1 からのコマンド）。下のカードの uid は場のポケモンではない。"""
        state, _ = evolve(board(hand=[PARASECT, GRASS]))
        below = state.players[0].active.evolution_stack[0]
        assert_rejected(self, state, AttachEnergy(0, uid_of(state, 0, GRASS), below), "TARGET_NOT_IN_PLAY")
        new, _ = run(state, AttachEnergy(0, uid_of(state, 0, GRASS), state.players[0].active.card))
        self.assertEqual(len(new.players[0].active.energy), 1)


if __name__ == "__main__":
    unittest.main()
